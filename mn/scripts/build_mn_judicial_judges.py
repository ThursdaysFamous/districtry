#!/usr/bin/env python3
"""
Build data/app/mn-judicial-judges.json — the district court judges sitting in
each of Minnesota's ten judicial districts, from two dated snapshots read once
in a person's browser, cross-checked against the Secretary of State's results.

WHY SNAPSHOTS. www.mncourts.gov serves a Cloudflare managed challenge to every
scripted client this project has (measured 2026-10-01, gap mn-judicial-roster),
and the Governor's judicial pages send the same client to a Radware ShieldSquare
bot check. Neither is worked around. On 2026-11-25 Adam allowed a one-off read
of a public page in his own Chrome; both sites loaded there with no check page,
and what they printed is committed in mn/data/source/:

  mn-judicial-directory-2026-11-25.txt  the court's Judicial Officer Directory,
                                        held to the SHA-256 in its own header
  mn-judicial-notices-2026-11-25.json   the Governor's appointment and vacancy
                                        notices, 2025-09-26 to 2026-11-06

No weekly job reads either site; this builder runs offline on the snapshots
except for the Secretary of State's results files, which answer this client.

THE DIRECTORY IS BEHIND, SO THE NOTICES CORRECT IT, AND ONLY WHERE THEY SAY SO.
On the day it was read the directory still listed six judges the Governor had
named replacements for. For each appointment notice:
  - successor listed and predecessor listed: the court shows the successor
    sitting, so the predecessor is dropped (Cashman, Kulick in the Seventh);
  - successor not listed, predecessor listed: the predecessor stays, with a
    note naming the appointee and the date (nothing says the seat changed hands
    yet; the directory still shows the predecessor);
  - neither listed: the appointee is added with a note saying the directory
    does not list them yet.
A retirement notice puts a note on that judge; a vacancy whose judge is gone
becomes a note on the district.

THE THIRD WITNESS IS THE BALLOT. judicialdst.txt for the 2022, 2024 and 2026
generals names the winner of every seat elected in that time (terms are six
years, so that is every seat not filled by appointment since). Every judge the
card names must be a seat winner or an appointee in the notices, except the
names in LISTED_ONLY. A 2026 winner who is neither listed nor appointed won an
open seat and takes office on the first Monday of January; the card says so.

Run:  python3 mn/scripts/build_mn_judicial_judges.py
"""

import datetime
import hashlib
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

from scraper_common import make_fail, require_robots_once  # noqa: E402

fail = make_fail("build-mn-judicial-judges")

SOURCE = os.path.join(INSTANCE, "data", "source")
DIRECTORY = os.path.join(SOURCE, "mn-judicial-directory-2026-11-25.txt")
NOTICES = os.path.join(SOURCE, "mn-judicial-notices-2026-11-25.json")
DISTRICTS = os.path.join(INSTANCE, "data", "app", "mn-judicial-districts.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-judicial-judges.json")

DIRECTORY_URL = "https://mncourts.gov/about-the-courts/judicialdirectory"
RESULTS = "https://electionresultsfiles.sos.mn.gov/%s/judicialdst.txt"
GENERALS = ("20221108", "20241105", "20261103")
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
TITLES = {"CJ": "Chief Judge", "ACJ": "Assistant Chief Judge", "": None}
MIN_JUDGES = 285       # 293 listed on 2026-11-25, two dropped, two added
SLACK = 3              # a district may sit this far from its authorized count
                       # (measured 2026-11-25: Seventh +2, Second +3, Tenth -1)

# Listed by the court and found neither on a 2022-2026 general ballot nor in
# the notices read (2025-09-26 on). Each must still be listed and still lack a
# witness, or the build fails so this table is corrected.
LISTED_ONLY = {
    (1, "Zachary Lyngaas"): "2026-11-25: not a 2022, 2024 or 2026 seat winner; no appointment notice in the window read",
    (10, "Gregory G. Galler"): "2026-11-25: not a 2022, 2024 or 2026 seat winner; no appointment notice in the window read",
}


def tokens(name):
    name = re.sub(r"['’]", "", name)  # O'Brien and O’Brien are one surname
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    name = re.sub(r",?\s+(jr|sr|ii|iii|iv)\.?$", "", name.strip())
    return [t for t in re.split(r"[^a-z]+", name) if t]


def same_person(a, b):
    """Same surname and the same first three letters of the first name.
    Iverson and Iverson Landrum share a first token and a token of surname."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb or ta[0][:3] != tb[0][:3]:
        return False
    return ta[-1] == tb[-1] or ta[-1] in tb[1:] or tb[-1] in ta[1:]


def surname_key(name):
    return tokens(name)[-1:] + tokens(name)


def read_directory():
    with open(DIRECTORY, encoding="utf-8") as fh:
        raw = fh.read()
    want = re.search(r"^# sha256: ([0-9a-f]{64})$", raw, re.M)
    body = "".join(l for l in raw.splitlines(True) if not l.startswith("#"))
    if not want or hashlib.sha256(body.encode("utf-8")).hexdigest() != want.group(1):
        fail("%s does not match the SHA-256 in its own header" % DIRECTORY)
    by = {d: [] for d in range(1, 11)}
    for line in body.splitlines():
        district, title, name, county = line.split("|")
        if not district:
            continue  # the four senior judges the card names no district for
        if title not in TITLES:
            fail("unknown title code %r on %r" % (title, line))
        by[int(district)].append({"name": name, "title": title, "county": county, "notes": []})
    return by


def read_results():
    import requests  # noqa: PLC0415
    session = requests.Session()
    seats = {}
    for day in GENERALS:
        url = RESULTS % day
        require_robots_once(url, USER_AGENT)
        resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
        resp.raise_for_status()
        rows = {}
        for line in resp.content.decode("latin-1").splitlines():
            f = line.split(";")
            if len(f) < 14 or f[10] == "WI":
                continue
            m = re.match(r"Judge - (\d+)\w\w District Court (\d+)$", f[4])
            if not m:
                fail("unrecognised office %r in %s" % (f[4], url))
            rows.setdefault((int(m.group(1)), int(m.group(2))), []).append((int(f[13]), f[7]))
        for seat, cands in rows.items():
            seats[seat] = (day, max(cands)[1])
    if len(seats) < 280:
        fail("only %d district court seats in three generals; expected about 284" % len(seats))
    return seats


def find(judges, name):
    hits = [j for j in judges if same_person(j["name"], name)]
    if len(hits) > 1:
        fail("%r matches %d listed judges" % (name, len(hits)))
    return hits[0] if hits else None


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return "%s %d, %d" % (d.strftime("%B"), d.day, d.year)  # the site's own date style


def main():
    by = read_directory()
    notices = json.load(open(NOTICES, encoding="utf-8"))
    authorized = {f["properties"]["district"]: f["properties"]["authorizedJudges"]
                  for f in json.load(open(DISTRICTS))["features"]}
    district_notes = {d: [] for d in by}
    appointees = set()

    for a in notices["appointments"]:
        judges = by[a["district"]]
        appointees.add((a["district"], a["appointee"]))
        prefix = a.get("replaces_prefix")
        if prefix and any(" ".join(tokens(j["name"])).startswith(" ".join(tokens(prefix))) for j in judges):
            fail("%s replaced someone read only as %r, and a listed judge fits it; read the notice in full"
                 % (a["appointee"], prefix))
        successor = find(judges, a["appointee"])
        predecessor = find(judges, a["replaces"]) if a.get("replaces") else None
        if successor and predecessor:
            judges.remove(predecessor)
        elif predecessor:
            predecessor["notes"].append("The Governor appointed %s on %s to replace this judge."
                                        % (a["appointee"], long_date(a["date"])))
        elif not successor:
            judges.append({"name": a["appointee"], "title": "", "county": None, "notes": [
                "Appointed by the Governor on %s. The court's directory does not list this judge yet."
                % long_date(a["date"])]})

    for v in notices["vacancies"]:
        judge = find(by[v["district"]], v["seat_of"])
        if judge:
            judge["notes"].append("The Governor's office announced on %s that this judge is %s. %s"
                                  % (long_date(v["date"]), "retiring" if v["reason"] == "retirement"
                                     else "leaving", v["stage"]))
        else:
            district_notes[v["district"]].append("One seat is vacant: %s left it on %s. %s"
                                                 % (v["seat_of"], v["reason"], v["stage"]))
    if sorted({v["district"] for v in notices["vacancies"]}) != notices["current_vacancies"]["districts"]:
        fail("the vacancy notices and the Governor's current-vacancies list name different districts")

    seats = read_results()
    witnessed = unwitnessed = 0
    for d, judges in by.items():
        for j in judges:
            if any(k[0] == d and same_person(j["name"], w) for k, (_day, w) in seats.items()) or \
               any(ad == d and same_person(j["name"], an) for ad, an in appointees):
                witnessed += 1
                if (d, j["name"]) in LISTED_ONLY:
                    fail("%s is witnessed now; take it out of LISTED_ONLY" % j["name"])
            elif (d, j["name"]) in LISTED_ONLY:
                unwitnessed += 1
            else:
                fail("%s (district %d) is neither a seat winner nor in the notices" % (j["name"], d))
    if unwitnessed != len(LISTED_ONLY):
        fail("LISTED_ONLY names %d judges and %d are listed without a witness" % (len(LISTED_ONLY), unwitnessed))

    year = int(GENERALS[-1][:4]) + 1
    jan = datetime.date(year, 1, 1)
    first_monday = jan + datetime.timedelta(days=(7 - jan.weekday()) % 7)
    for (d, seat), (day, winner) in sorted(seats.items()):
        if day == GENERALS[-1] and not find(by[d], winner) and \
                not any(ad == d and same_person(winner, an) for ad, an in appointees):
            district_notes[d].append("%s won seat %d on %s and takes office on %s."
                                     % (winner, seat, long_date("%s-%s-%s" % (day[:4], day[4:6], day[6:])),
                                        long_date(first_monday.isoformat())))

    out, total = {}, 0
    order = {"CJ": 0, "ACJ": 1, "": 2}
    for d in sorted(by):
        judges = sorted(by[d], key=lambda j: (order[j["title"]], surname_key(j["name"])))
        if abs(len(judges) - authorized[d]) > SLACK:
            fail("district %d names %d judges against %d authorized" % (d, len(judges), authorized[d]))
        total += len(judges)
        rows = []
        for j in judges:
            row = {"name": j["name"]}
            if TITLES[j["title"]]:
                row["role"] = TITLES[j["title"]]
            if j["county"]:
                row["chambers"] = j["county"] + " County"
            if j["notes"]:
                row["note"] = " ".join(j["notes"])
            rows.append(row)
        out[str(d)] = {"judges": rows, "notes": district_notes[d], "read": notices["read"],
                       "sourceUrl": DIRECTORY_URL}
    if total < MIN_JUDGES:
        fail("only %d judges; floor is %d" % (total, MIN_JUDGES))
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote %s: %d judges in 10 districts; %d witnessed by a ballot or a notice, %d listed only"
          % (os.path.relpath(OUT_FILE), total, witnessed, unwitnessed))


if __name__ == "__main__":
    main()
