#!/usr/bin/env python3
"""Minnesota's elected soil and water conservation district (SWCD) supervisors,
from the Secretary of State's own election results, every name dated to the
election that seated it; each district's office from BWSR's directory.

THE NAMES ARE ELECTION WINNERS, as build_mn_commissioner_roster.py's are and
for the same reason. The Secretary of State's county races file for each
election day (`cntyRaces.txt`) carries every "Soil and Water Supervisor
District N" contest, keyed by the same `swcdist` code the precinct layer
carries, so a contest joins the map's polygons without a name match. The
newest canvassed general for a seat names its winner. A winner is dated and is
not a statement about who sits today; the card says so. Primaries, uncanvassed
files, write-in wins and ties are handled exactly as the commissioner builder
handles them, and its fetch is reused rather than copied, so the two cannot
come to read the results host differently.

WHAT A SEAT IS. In an at-large SWCD every voter in the district elects every
supervisor, and "District N" is the nomination district the candidate must
live in; in the seven by-district SWCDs (build_mn_swcd_districts.py) it is the
supervisor district itself, and its code differs from its neighbours'. Either
way a seat is (code, N), and the roster lists each SWCD's seats so a card can
name the whole board — which, at large, is who represents the reader.

THE OFFICE AND SOME SUPERVISORS' CONTACTS ARE BWSR'S, AND DATED. BWSR's "Soil
and Water Conservation District Directory" (the newest copy found, under
sites/default/files/2022-06/ but headed 21 February 2023) prints each
district's office address and, for each board member, a phone, sometimes an
e-mail, and a street address. The street address is a home address and is
never read into the output. A phone or e-mail printed on a supervisor's own
line is that supervisor's and ships on the seat whose election winner has the
same name in the same SWCD (Adam, 2026-10-17: a government source printing an
official's own number beside them is published); a supervisor the directory
lists and the results do not is not added, because the directory is older
than the 2024 general. An office telephone is shipped only where the header
line carries one number: where it also says "Fax" the column order is not
stated and is not guessed at.

Usage:
    python3 mn/scripts/build_mn_swcd_supervisors.py          # fetch and write
    python3 mn/scripts/build_mn_swcd_supervisors.py --check  # offline gate
"""

import argparse
import datetime
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, FLEET_SCRIPTS)

import build_mn_commissioner_roster as cr  # noqa: E402  (results fetch, general test)
from scraper_common import require_robots_once  # noqa: E402

USER_AGENT = cr.USER_AGENT
DIRECTORY_URL = "https://bwsr.state.mn.us/sites/default/files/2022-06/SWCD_Dir.pdf"
DIRECTORY_DATE = "2023-02-21"
DISTRICTS_FILE = os.path.join(INSTANCE, "data", "app", "mn-swcd-districts.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-swcd-supervisors.json")

EXPECT_SWCDS = 88
OFFICE_RE = re.compile(r"^(Special Election for )?Soil and Water Supervisor District (\d+)"
                       r"(?: \((?:East|West|North|South)\))?( \(Special Primary\))?$")
PHONE_RE = re.compile(r"\(?\d{3}\)?[-. ]?\d{3}-\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?", re.I)
HEADER_RE = re.compile(r"^(?P<name>[A-Z][A-Za-z .,'-]*?(?: County)? (?:SWCD|CD|Conservation District))"
                       r"\s+(?P<rest>.*)$")
PAGE_FURNITURE = ("Soil and Water Conservation District Directory",
                  "Please Note:", "MN Board of Water and Soil Resources")

# Seats no canvassed general since the 2022 general names, with the reason. An
# entry a result now names, or a new such seat with no entry, fails the build.
_NO_RESULT = ("no general election for this seat appears in any results file the "
             "Secretary of State published since the 2022 general (measured 2026-10-26)")
NO_CONTEST = {
    "Beltrami|5": _NO_RESULT,
    "Renville|5": _NO_RESULT,
    "Swift|3": _NO_RESULT,
}


def fail(msg):
    raise SystemExit("build-mn-swcd-supervisors: FATAL: %s" % msg)


def norm(text):
    return re.sub(r"[^a-z]", "", (text or "").lower().replace("county", ""))


def swcd_key(name):
    """'Otter Tail, East SWCD' -> 'easttottertail'-style key matching the
    precinct layer's 'Otter Tail East'; 'St Louis, North SWCD' -> 'North St.
    Louis'. Returns (key, display name)."""
    base = re.sub(r"\s+(SWCD|CD|Conservation District)$", "", name).strip()
    m = re.match(r"^(.+), (East|West|North|South)$", base)
    if m:
        place = m.group(1).replace("St Louis", "St. Louis")
        display = "%s %s SWCD" % (m.group(2), place)
        return norm(place + m.group(2)), display
    display = re.sub(r" CD$", " Conservation District", name.replace("St Louis", "St. Louis"))
    return norm(base), display


def layer_key(swcd):
    """The precinct layer's label for an SWCD as a key: 'North St. Louis' and
    'Otter Tail East' both put the direction in a different place, so the
    direction word is moved to the end."""
    m = re.match(r"^(North|South|East|West) (.+)$", swcd)
    if m:
        swcd = "%s %s" % (m.group(2), m.group(1))
    return norm(swcd)


def read_directory(session):
    """{key: {"name", "office", "phone", "members": [{name, phone, email}]}}"""
    import pypdf  # noqa: PLC0415
    require_robots_once(DIRECTORY_URL, USER_AGENT)
    resp = session.get(DIRECTORY_URL, headers={"User-Agent": USER_AGENT},
                       timeout=cr.REQUEST_TIMEOUT)
    resp.raise_for_status()
    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if "February 21, 2023" not in text:
        fail("the directory no longer says it is the edition of 21 February 2023; "
             "re-read it and update DIRECTORY_DATE")
    lines = [l.rstrip() for l in text.splitlines()]
    lines = [l for l in lines if l.strip() and not l.strip().startswith(PAGE_FURNITURE)
             and not re.match(r"^\s*Page \d+\s*$", l)]
    out, cur, section = {}, None, None
    for line in lines:
        m = HEADER_RE.match(line.strip())
        # a district's header carries its office address; a staff member's
        # line ("Carrie Schultz SWCD Assistant Manager ...") carries none
        if m and re.search(r"\bMN \d{5}", m.group("rest") or ""):
            key, display = swcd_key(m.group("name"))
            rest = m.group("rest")
            first_phone = PHONE_RE.search(rest)
            address = (rest[:first_phone.start()] if first_phone else rest).strip(" ,")
            address = re.sub(r"\s+(N/A|none)\s*$", "", re.sub(r"\s+Fax\s*$", "", address))
            phones = PHONE_RE.findall(rest)
            cur = {"name": display, "office": re.sub(r"\s{2,}", " ", address),
                   "phone": phones[0].strip() if len(phones) == 1 and "Fax" not in rest
                   else None,
                   "members": []}
            out[key] = cur
            section = None
            continue
        if cur is None:
            continue
        stripped = line.strip()
        if stripped.startswith("Board Members"):
            section = "board"
            continue
        if stripped.startswith("Staff") or stripped.startswith("Board Meeting"):
            section = None if stripped.startswith("Staff") else section
            continue
        if section != "board":
            continue
        name = re.split(r"\s{2,}", stripped, 1)[0].strip()
        if not re.match(r"^[A-Z][A-Za-z.'-]+(?: [A-Za-z.'-]+)+$", name):
            continue
        rest = stripped[len(name):]
        # The phone printed before the home address; the address is dropped.
        phone = PHONE_RE.search(rest)
        email = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", rest)
        cur["members"].append({
            "name": name,
            "phone": phone.group(0).strip() if phone else None,
            "email": email.group(0) if email else None,
        })
    return out


def seats_from_geometry():
    with open(DISTRICTS_FILE, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    swcds = {}
    for feat in feats:
        p = feat["properties"]
        s = swcds.setdefault(p["swcd"], {"county": p["county"], "codes": {},
                                         "byDistrict": p["district"] is not None})
        s["codes"][p["code"]] = p["district"]
    if len(swcds) != EXPECT_SWCDS:
        fail("the shipped geometry holds %d SWCDs, expected %d" % (len(swcds), EXPECT_SWCDS))
    return swcds


def swcd_contests(elections):
    found = []
    for day in sorted(elections):
        groups = {}
        for line in elections[day].splitlines():
            f = line.split(";")
            if len(f) < 16:
                continue
            m = OFFICE_RE.match(f[4].strip())
            if not m:
                continue
            groups.setdefault((f[5].strip(), f[4].strip()), []).append(f)
        for (code, office), rows in sorted(groups.items()):
            m = OFFICE_RE.match(office)
            found.append({
                "date": day, "code": code, "district": int(m.group(2)),
                "special": bool(m.group(1)), "labelled_primary": bool(m.group(3)),
                "office": office,
                "candidates": [(r[7].strip(), int(r[13])) for r in rows],
            })
    return found


def same_person(a, b):
    na, nb = (a or "").split(), (b or "").split()
    if not na or not nb:
        return False
    if norm(a) == norm(b):
        return True
    return norm(na[-1]) == norm(nb[-1]) and na[0][0].lower() == nb[0][0].lower()


def build(swcds, contests, directory, today):
    """A seat is (SWCD, N). A contest is joined to its SWCD through its code,
    and to its seat through N, not through the code: Fillmore elected at large
    in 2022, every contest filed under one code, and by district from 2024, so
    its 2022 winners hold supervisor districts 1 and 2 under a code that now
    names district 5. Keying on the code would put them on the wrong ground."""
    code_to_swcd = {code: s for s, info in swcds.items() for code in info["codes"]}
    stray = sorted({c["code"] for c in contests} - set(code_to_swcd))
    if stray:
        fail("results name SWCD codes the map does not draw: %s" % stray)
    chosen, held = {}, []
    for c in sorted(contests, key=lambda c: c["date"]):
        if not cr.is_general(c):
            continue
        age = (today - c["date"]).days
        if age < cr.CANVASS_DAYS:
            held.append((c, age))
            continue
        chosen[(code_to_swcd[c["code"]], c["district"])] = c
    out, unmatched_dir, no_contest = {}, [], []
    for swcd, info in sorted(swcds.items()):
        d = directory.get(layer_key(swcd))
        if d is None:
            unmatched_dir.append(swcd)
        if info["byDistrict"]:
            numbers = {n: code for code, n in info["codes"].items()}
        else:
            only = next(iter(info["codes"]))
            seen = [n for (s, n) in chosen if s == swcd]
            numbers = {n: only for n in range(1, max([5] + seen) + 1)}
        extra = sorted(n for (s, n) in chosen if s == swcd and n not in numbers)
        if extra:
            fail("%s: results name supervisor districts %s the map does not draw"
                 % (swcd, extra))
        seats = []
        for num in sorted(numbers):
            seat = {"district": num, "code": numbers[num]}
            c = chosen.get((swcd, num))
            if c is None:
                why = NO_CONTEST.get("%s|%d" % (swcd, num))
                if why is None:
                    fail("%s District %d has no canvassed general since the 2022 "
                         "general and no NO_CONTEST entry" % (swcd, num))
                no_contest.append("%s|%d" % (swcd, num))
                seat["unnamed"] = why
                seats.append(seat)
                continue
            name, why = cr.winner(c)
            seat.update({"election": c["date"].isoformat(), "special": c["special"],
                         "sourceUrl": cr.RESULTS_FILE % c["date"].strftime("%Y%m%d")})
            if name:
                seat["name"] = name
                member = next((m for m in (d or {}).get("members", [])
                               if same_person(m["name"], name)), None)
                if member and (member["phone"] or member["email"]):
                    contact = {"asOf": DIRECTORY_DATE, "sourceUrl": DIRECTORY_URL}
                    if member["phone"]:
                        contact["phone"] = member["phone"]
                    if member["email"]:
                        contact["email"] = member["email"]
                    seat["contact"] = contact
            else:
                seat["unnamed"] = why
            seats.append(seat)
        rec = {"county": info["county"], "byDistrict": info["byDistrict"], "seats": seats}
        if d:
            rec["name"] = d["name"]
            office = {"address": d["office"], "asOf": DIRECTORY_DATE,
                      "sourceUrl": DIRECTORY_URL}
            if d["phone"]:
                office["phone"] = d["phone"]
            rec["office"] = office
        out[swcd] = rec
    stale = sorted(set(NO_CONTEST) - set(no_contest))
    if stale:
        fail("NO_CONTEST names %s, which a result now names — drop the entry" % stale)
    return out, held, unmatched_dir


def check(roster, swcds):
    problems = []
    if set(roster) != set(swcds):
        problems.append("the roster's SWCDs differ from the shipped geometry's")
    named = total = 0
    for swcd, rec in roster.items():
        codes = swcds.get(swcd, {}).get("codes", {})
        if not rec.get("seats"):
            problems.append("%s lists no seat" % swcd)
        for seat in rec.get("seats", []):
            total += 1
            if seat.get("code") not in codes:
                problems.append("%s seat %s carries a code the map does not draw" % (swcd, seat))
            if rec.get("byDistrict") and codes.get(seat.get("code")) != seat.get("district"):
                problems.append("%s seat %s is not its supervisor district's" % (swcd, seat))
            if seat.get("name"):
                named += 1
                if not seat.get("election") or not seat.get("sourceUrl"):
                    problems.append("%s names somebody without the election" % swcd)
            elif not seat.get("unnamed"):
                problems.append("%s seat %s names nobody and says nothing" % (swcd, seat))
        if rec.get("byDistrict"):
            have = {s["code"] for s in rec.get("seats", [])}
            if have != set(codes):
                problems.append("%s is elected by district and its seats do not cover "
                                "every district" % swcd)
        for seat in rec.get("seats", []):
            text = json.dumps(seat)
            if re.search(r"\d+ [A-Z0-9][^\"]* (St|Ave|Rd|Ln|Dr|Lane|Street|Avenue|Road)\b", text):
                problems.append("%s seat carries what looks like a street address" % swcd)
    return problems, named, total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped roster to the shipped geometry")
    args = ap.parse_args()
    swcds = seats_from_geometry()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as f:
            roster = json.load(f)
        problems, named, total = check(roster, swcds)
        if problems:
            for p in problems:
                print("build-mn-swcd-supervisors: FAIL: " + p)
            raise SystemExit(1)
        print("build-mn-swcd-supervisors --check: OK — %d SWCDs, %d of %d seats named, "
              "each dated to the election that seated it" % (len(roster), named, total))
        return
    import requests  # noqa: PLC0415
    session = requests.Session()
    today = datetime.date.today()
    require_robots_once(cr.RESULTS_FILE % cr.FIRST_ELECTION.strftime("%Y%m%d"), USER_AGENT)
    elections = cr.fetch_elections(session, today)
    print("results files with county contests: %s"
          % ", ".join(d.isoformat() for d in sorted(elections)))
    contests = swcd_contests(elections)
    directory = read_directory(session)
    roster, held, unmatched = build(swcds, contests, directory, today)
    for c, age in held:
        print("  held: %s code %s District %d — not yet canvassed (%d days old)"
              % (c["date"], c["code"], c["district"], age))
    if unmatched:
        print("  no directory entry: %s" % ", ".join(unmatched))
    for swcd, rec in sorted(roster.items()):
        n = len(rec["seats"])
        if not rec["byDistrict"] and n != 5:
            print("  %s lists %d at-large seats" % (swcd, n))
        for seat in rec["seats"]:
            if not seat.get("name"):
                print("  unnamed: %s District %d — %s" % (swcd, seat["district"], seat["unnamed"]))
    problems, named, total = check(roster, swcds)
    if problems:
        for p in problems:
            print("build-mn-swcd-supervisors: FAIL: " + p)
        raise SystemExit(1)
    contacts = sum(1 for r in roster.values() for s in r["seats"] if s.get("contact"))
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("wrote %s: %d SWCDs, %d of %d seats named, %d with a contact from BWSR's "
          "directory" % (os.path.relpath(OUT_FILE, os.path.dirname(INSTANCE)),
                         len(roster), named, total, contacts))


if __name__ == "__main__":
    main()
