#!/usr/bin/env python3
"""
Build ia/data/app/ia-cc-trustees.json: the trustee elected from each director
district of Iowa's community colleges, keyed by the same `ddkey`
("<merged area>-<district>") the CC Director District layer draws.

Input is ia_cc_trustee_scraper.py's output (ia/scripts/.cache/ia_cc_trustees.json).

WHAT IS HELD, PER COLLEGE
--------------------------
A college's seats ship only if the page named EXACTLY the districts its board
has: 1..N, where N is the highest district its own plan draws in
`ia-cc-director-districts.json`. Des Moines Area's plan omits District 2 while
its board page names a District 2 trustee, which is why the set is 1..N rather
than the drawn set: a trustee with no drawn district still ships, keyed by the
seat, and simply has no polygon to answer at. A page naming one district too
few or too many is a page that changed shape, and that college is NOT written
from it.

A COLLEGE THAT FAILS KEEPS ITS LAST-GOOD SEATS (Adam's ruling of 2026-09-19:
a failed read stops the fetch and never unpublishes what we already have). It
carries its own `asOf`, the date its page was last actually read, so a card
never prints a read date for a page that was not read this week. A college
with no last-good record and no good read is left out and printed.

Every name is checked to look like a name (no digits, no "@"), every e-mail
like an e-mail, and no field may read as a street address: Hawkeye's page
prints each trustee's home address beside their name and none of it ships.

Northeast Iowa names its trustees by school district and not by number, and
four of its nine list Dubuque Community, so its page alone cannot key a seat.
Since 2026-10-26 each of its trustees is matched to a district from election
records (PAIRED below): a trustee must live in the district that elects them
(Iowa Code 260C.11), so a sitting trustee who won a district, filed for it or
was sworn in for it lives in it. The page still supplies every name, role and
e-mail; the table supplies only the district, joined by surname, and the
college ships with no seats at all if the two stop agreeing. Without that
table it would ship as a list under `undistricted` and the card would say why
it names no one for a district.

Usage:
    python3 ia/scripts/build_ia_cc_trustees.py
    python3 ia/scripts/build_ia_cc_trustees.py --check
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.join(HERE, "..")
RAW = os.path.join(HERE, ".cache", "ia_cc_trustees.json")
OUT = os.path.join(IA, "data", "app", "ia-cc-trustees.json")
DISTRICTS = os.path.join(IA, "data", "app", "ia-cc-director-districts.json")
COLLEGES = os.path.join(IA, "data", "app", "ia-community-colleges.json")

UNDISTRICTED = {"1"}        # Northeast Iowa: trustees listed by school district

# Which district each of a college's trustees holds, from election records,
# for a college whose page names its trustees without saying (see the module
# docstring). Each name is the surname the page prints; at most one district
# is placed by elimination, and every other has its own record.
PAIRED = {
    "1": {
        "readOn": "2026-10-26",
        "districts": {
            "1": "Runyon", "2": "Gunderson", "3": "Anderson", "4": "Sherman",
            "5": "Finley", "6": "McAndrew", "7": "Norton", "8": "Knight",
            "9": "Fisch",
        },
        "byElimination": "3",
        "evidence": {
            # The Secretary of State's certified results for the 2025
            # city-school election (state election 124196, read per county
            # from electionresults.iowa.gov), whose winners took office in
            # December 2025. The contest's counties match the layer's drawn
            # district in every case.
            "1": "won District 1 on 2025-11-04 (Brenda Sue Runyon)",
            "2": "won District 2 on 2025-11-04",
            "4": "won District 4 on 2025-11-04",
            "6": "won District 6 on 2025-11-04",
            "7": "won District 7, to fill a vacancy, on 2025-11-04",
            "9": "won District 9 on 2025-11-04",
            # Delaware County's 2023 city-school candidate list
            # (delawarecountyelections.iowa.gov/files/candidate_list/
            # 2023_cityschool_election_22343.pdf): the only candidate for the
            # four-year District 5 term, under the 2023 plan this layer draws.
            "5": "the only candidate for District 5 on 2023-11-07 (John E. Finley)",
            # The college's own release of 2023-11-20 (nicc.edu/news/article/
            # 20231120-board-of-trustees-takes-action-on-president.php).
            "8": "sworn in as the District 8 trustee on 2023-11-20",
            "3": "the one district no record places anyone else in",
        },
    },
}
MIN_COLLEGES = 14           # every districted college, or nothing is written
STREET = re.compile(
    r"\b\d{1,6}\s+\w+(?:\s+\w+){0,3}\s+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|"
    r"Lane|Ct|Court|Blvd|Way|Pl|Place|Cir|Circle|Hwy|Highway|Trl|Ter)\b\.?", re.I)
NAME_OK = re.compile(r"^[A-Za-z][A-Za-z .'’-]+$")
EMAIL_OK = re.compile(r"^[\w.+'-]+@[\w-]+(?:\.[\w-]+)+$")
PHONE_OK = re.compile(r"^\(?\d{3}\)?[ .-]\d{3}-\d{4}$")


def fail(msg):
    print("build-ia-cc-trustees: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def board_sizes():
    """merged area -> highest director district its plan draws."""
    sizes = {}
    for f in json.load(open(DISTRICTS))["features"]:
        p = f["properties"]
        area = str(p["collegedistrict"])
        sizes[area] = max(sizes.get(area, 0), int(p["district"]))
    return sizes


def college_names():
    """merged area -> the college name the community-college layer ships."""
    names = {}
    for f in json.load(open(DISTRICTS))["features"]:
        p = f["properties"]
        names[str(p["collegedistrict"])] = p["name"]
    return names


def record_problems(r):
    out = []
    if r.get("vacant"):
        return [] if set(r) == {"vacant"} else ["a vacant seat carries other fields"]
    name = r.get("name", "")
    if not NAME_OK.match(name):
        out.append("name %r does not read as a name" % name)
    if "email" in r and not EMAIL_OK.match(r["email"]):
        out.append("e-mail %r does not read as an address" % r["email"])
    if "phone" in r and not PHONE_OK.match(r["phone"]):
        out.append("telephone %r does not read as one number" % r["phone"])
    if "termEnds" in r and not re.fullmatch(r"20\d\d", r["termEnds"]):
        out.append("term end %r is not a year" % r["termEnds"])
    for k, v in r.items():
        if isinstance(v, str) and STREET.search(v):
            out.append("field %s reads as a street address" % k)
    allowed = {"name", "role", "email", "phone", "termEnds", "profileUrl"}
    extra = set(r) - allowed
    if extra:
        out.append("unexpected field(s) %s" % sorted(extra))
    return out


def pair_college(area, people):
    """Seats for a college whose page names no districts, from PAIRED; None
    when the table and the page disagree (printed), so the college keeps its
    last-good record instead."""
    rec = PAIRED[area]
    by_surname = {}
    for r in people:
        by_surname.setdefault(r["name"].split()[-1].lower(), []).append(r)
    seats, probs = {}, []
    for d, surname in rec["districts"].items():
        got = by_surname.get(surname.lower(), [])
        if len(got) != 1:
            probs.append("district %s: the page names %d trustee(s) called %s" % (d, len(got), surname))
            continue
        seats[d] = dict(got[0])
    if len(rec["districts"]) != len(people):
        probs.append("the page names %d trustees, the table pairs %d" % (len(people), len(rec["districts"])))
    if set(rec["evidence"]) != set(rec["districts"]):
        probs.append("a paired district carries no evidence")
    if probs:
        print("build-ia-cc-trustees: area %s NOT PAIRED: %s" % (area, "; ".join(probs)), file=sys.stderr)
        return None
    return {d: seats[d] for d in sorted(seats, key=int)}


def check_college(area, c, size):
    """Problems with one scraped college; empty means it may ship."""
    if "undistricted" in c:
        people = c.get("undistricted") or []
        probs = [p for r in people for p in record_problems(r)]
        if len(people) != size:
            probs.append("names %d trustees for a %d-seat board" % (len(people), size))
        return probs
    seats = c.get("seats") or {}
    want = {str(n) for n in range(1, size + 1)}
    probs = []
    if set(seats) != want:
        probs.append("names districts %s, wanted 1..%d" % (sorted(seats, key=int), size))
    for d, r in seats.items():
        probs += ["district %s: %s" % (d, p) for p in record_problems(r)]
    named = [r["name"] for r in seats.values() if "name" in r]
    if len(set(named)) != len(named):
        probs.append("one name holds two seats")
    return probs


def build(raw, previous, today):
    sizes = board_sizes()
    names = college_names()
    colleges, seats = {}, {}
    carried, dropped = [], []
    prev_colleges = (previous or {}).get("colleges", {})
    for area in sorted(sizes, key=int):
        got = raw.get("colleges", {}).get(area)
        probs = check_college(area, got, sizes[area]) if got else ["page not read"]
        if probs:
            if area in prev_colleges:
                colleges[area] = prev_colleges[area]
                carried.append((area, probs))
            else:
                dropped.append((area, probs))
            continue
        entry = {"college": names[area], "sourceUrl": got["sourceUrl"], "asOf": today}
        if area in UNDISTRICTED:
            paired = pair_college(area, got["undistricted"]) if area in PAIRED else None
            if paired is not None:
                entry["seats"] = paired
                entry["districtsFrom"] = "elections"
                entry["districtsReadOn"] = PAIRED[area]["readOn"]
            elif area in prev_colleges:
                colleges[area] = prev_colleges[area]
                carried.append((area, ["the page and the pairing table disagree"]))
                continue
            else:
                entry["undistricted"] = got["undistricted"]
        else:
            entry["seats"] = {d: got["seats"][d] for d in sorted(got["seats"], key=int)}
        # A college whose page says exactly what it said last time keeps the
        # date it was first read that way: a date that moved every week would
        # open a bot PR every week for no change, and an older date understates
        # a read rather than claiming one that did not happen.
        old = prev_colleges.get(area)
        if old and {k: v for k, v in entry.items() if k != "asOf"} == \
                {k: v for k, v in old.items() if k != "asOf"}:
            entry["asOf"] = old["asOf"]
        # The same holds the week a pairing first keys a page that has not
        # changed: the districts are new, the read is not.
        elif old and old.get("undistricted") == got.get("undistricted") and "districtsFrom" in entry:
            entry["asOf"] = old["asOf"]
        colleges[area] = entry
    for area, c in colleges.items():
        for d, r in (c.get("seats") or {}).items():
            seats["%s-%s" % (area, d)] = r
    return {"colleges": colleges, "seats": dict(sorted(seats.items(), key=lambda kv: [int(x) for x in kv[0].split("-")]))}, carried, dropped


def check_shipped():
    d = json.load(open(OUT))
    sizes = board_sizes()
    probs = []
    for area, c in d["colleges"].items():
        probs += ["area %s: %s" % (area, p) for p in check_college(area, c, sizes[area])]
        for k in ("college", "sourceUrl", "asOf"):
            if k not in c:
                probs.append("area %s carries no %s" % (area, k))
        for dn, r in (c.get("seats") or {}).items():
            if d["seats"].get("%s-%s" % (area, dn)) != r:
                probs.append("seat %s-%s disagrees with its college's list" % (area, dn))
    keys = {"%s-%s" % (a, dn) for a, c in d["colleges"].items() for dn in (c.get("seats") or {})}
    if set(d["seats"]) != keys:
        probs.append("the seats index and the colleges' lists differ")
    for area, rec in PAIRED.items():
        c = d["colleges"].get(area) or {}
        if "seats" in c and {k: r["name"].split()[-1] for k, r in c["seats"].items()} != rec["districts"]:
            probs.append("area %s: the shipped seats and the pairing table disagree" % area)
    districted = [a for a in d["colleges"] if "seats" in d["colleges"][a]]
    if len(districted) < MIN_COLLEGES:
        probs.append("%d districted colleges, floor %d" % (len(districted), MIN_COLLEGES))
    if probs:
        fail("; ".join(probs))
    named = sum(1 for r in d["seats"].values() if "name" in r)
    print("build-ia-cc-trustees: OK — %d colleges, %d seats, %d named" % (
        len(d["colleges"]), len(d["seats"]), named))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        check_shipped()
        return
    raw = json.load(open(RAW))
    previous = json.load(open(OUT)) if os.path.exists(OUT) else None
    today = datetime.date.today().isoformat()
    out, carried, dropped = build(raw, previous, today)
    for area, probs in carried:
        print("build-ia-cc-trustees: area %s KEPT FROM LAST GOOD READ (%s): %s" % (
            area, out["colleges"][area].get("asOf"), "; ".join(probs)), file=sys.stderr)
    for area, probs in dropped:
        print("build-ia-cc-trustees: area %s LEFT OUT, no last-good record: %s" % (
            area, "; ".join(probs)), file=sys.stderr)
    districted = [x for x in out["colleges"] if "seats" in out["colleges"][x]]
    if len(districted) < MIN_COLLEGES:
        fail("%d districted colleges, floor %d; nothing written" % (len(districted), MIN_COLLEGES))
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    named = sum(1 for r in out["seats"].values() if "name" in r)
    print("build-ia-cc-trustees: wrote %s — %d colleges, %d seats, %d named, %d vacant" % (
        os.path.relpath(OUT), len(out["colleges"]), len(out["seats"]), named,
        sum(1 for r in out["seats"].values() if r.get("vacant"))))


if __name__ == "__main__":
    main()
