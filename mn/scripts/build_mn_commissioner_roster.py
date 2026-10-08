#!/usr/bin/env python3
"""Minnesota's 447 county commissioners, from the Secretary of State's own
election results, every name dated to the election that seated it.

WHAT THIS PUBLISHES AND WHAT IT DOES NOT. The Secretary of State publishes the
results of every county commissioner contest it administers as a plain text
file per election day (`cntyRaces.txt`, under
electionresultsfiles.sos.mn.gov/<YYYYMMDD>/). Minnesota elects commissioners to
staggered four-year terms, and after the 2022 redistricting every seat was on
the ballot that November, so the 2022 and 2024 generals between them name a
winner for 445 of the 447 districts the shipped geometry draws. A winner is a
fact with a date on it. It is NOT a statement of who holds the seat today: a
commissioner who has resigned, died, or been replaced by appointment since
still shows here as the person who won. So every record names its election,
and the card and the county page say so in words — the posture Adam opened for
Michigan's certified-returns route on 2026-09-22
(mi/scripts/build_mi_returns_roster.py), and the one Clark, Union and
Williamson have shipped under in Illinois.

THE NEWEST CONTEST FOR A SEAT WINS, and specials are what make that matter. A
vacancy is filled by a special election, and the results files carry them
("Special Election for County Commissioner District 6"), so a seat that turned
over in 2023 or 2025 names the special's winner rather than the 2022 one.
Measured on the files this builder reads (2026-10-06), nine specials have run
since November 2022.

FOUR WAYS A CONTEST IS NOT A WINNER, each measured before it was written down.
  (1) A PRIMARY. A regular commissioner primary runs in August of an even year
      and its contest carries the SAME office name as the general, and a
      special primary is sometimes labelled "(Special Primary)" and sometimes
      NOT (Hennepin District 6 on 30 April 2024 is unlabelled; its special
      general followed on 14 May). What separates them in these files is the
      WRITE-IN line: every general carries one and no primary does, measured
      on every file since 2022 (is_general, below). A first draft used the
      date, the candidate count and a 120-day window instead and still had to
      HOLD two August 2026 specials as undecidable; the write-in line decides
      both, as primaries.
  (2) NOT YET CANVASSED. An election night file is unofficial. A contest counts
      only once CANVASS_DAYS have passed since election day; the county
      canvassing board meets within ten days.
  (3) A WRITE-IN WINS. The file names every write-in vote as one candidate,
      WRITE-IN, so a seat won by write-in names nobody here, and the record
      says so rather than printing "WRITE-IN" as a person.
  (4) A TIE. The file cannot say who won a tie (Minnesota breaks it by lot);
      the record names nobody and says why.

WHY THE ELECTION DAYS ARE PROBED RATHER THAN LISTED. The results site's own
election index is on electionresults.sos.mn.gov, which is fronted by a Radware
bot manager (its pages load `validate.perfdrive.com`); this builder never reads
that host. The files host is a plain IIS server whose robots.txt answers 404,
so every Tuesday from the 2022 general to today is asked for its
`cntyRaces.txt` and a 404 means no county contests that day. ONE BLIND SPOT IS
KNOWN AND STATED: a county-administered special is sometimes filed under a
directory named for the date AND the county (`2023050960`, Polk's special
primary of 9 May 2023), which a date probe never asks for. Such a seat shows
its last general's winner until the next general — which the card's wording
already covers, since every name is dated to the election that seated it.

A SECOND PUBLISHER CHECKS THE FIRST. Five county governments publish a name on
their own commissioner-district layer (Anoka, Dakota, Isanti, Ramsey and
St. Louis — the five the commissioner-district builder already reads as
boundary witnesses). Each of their 33 names is compared with the results-file
winner for the same district and every difference is printed. Measured
2026-10-06: 30 of 33 agree exactly, two more are one person written two ways
(Dakota's "William Droste" is the results' "Bill Droste"; St. Louis's "Mike
Jugovich" is "Michael A Jugovich"), and ONE IS A DIFFERENT PERSON: Ramsey
District 3's 2024 winner is Trista MatasCastillo and Ramsey County's own map
names Garrison McMurtrey — the county-run special this builder's date probe
cannot see, exactly the blind spot named above. Where the surnames differ the
record carries `countySays` beside the winner, and the card prints both
sentences, each saying whose it is; the results winner is not overwritten,
because the county's column can itself be a stale snapshot (Coles County,
Illinois) and two publishers disagreeing is the thing a reader should see.

Usage:
    python3 mn/scripts/build_mn_commissioner_roster.py          # fetch and write
    python3 mn/scripts/build_mn_commissioner_roster.py --check  # offline gate
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import require_robots_once  # noqa: E402

FILES_HOST = "https://electionresultsfiles.sos.mn.gov"
RESULTS_FILE = FILES_HOST + "/%s/cntyRaces.txt"
COUNTY_TABLE = FILES_HOST + "/%s/Cntytbl.txt"
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 60
PACE_SECONDS = 0.5

# The 2022 general is the floor: every seat was elected then or since, after
# the 2022 redistricting put every district on that ballot.
FIRST_ELECTION = datetime.date(2022, 11, 8)
CANVASS_DAYS = 21

DISTRICTS_FILE = os.path.join(INSTANCE, "data", "app", "mn-commissioner-districts.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-county-commissioners.json")

EXPECT_SEATS = 447
# Seats the results files name nobody for, with the reason. An entry that
# becomes named, or a new unnamed seat with no entry, fails the build — so
# this table cannot rot in either direction.
KNOWN_UNNAMED = {
    "Swift|2": "no contest for this district appears in any results file "
                  "the Secretary of State published since the 2022 general",
    "Kanabec|2": "won by write-in votes in the 2024 general (measured "
                 "2026-10-06); the results name write-ins only as WRITE-IN",
}
MIN_NAMED = EXPECT_SEATS - len(KNOWN_UNNAMED)

# The five county layers that carry a name: (url, district field, name field).
COUNTY_NAME_WITNESSES = {
    "Anoka": ("https://gisservices.co.anoka.mn.us/anoka_gis/rest/services/"
              "OpenData_Political/MapServer/4", "COMDIST", "COMMISH"),
    "Dakota": ("https://gis2.co.dakota.mn.us/arcgis/rest/services/"
               "DCGIS_OL_PoliticalAdministrative/MapServer/8", "DIST_ID", "COMMNAME"),
    "Isanti": ("https://gis.co.isanti.mn.us/arcgis/rest/services/Elections/"
               "CommissionerDistricts_Public/FeatureServer/0", "DISTRICT", "COMMISSIONER"),
    "Ramsey": ("https://gis.ramseycountymn.gov/server/rest/services/Boundary/"
               "BOUND_CommissionerDistrict2022_ViewOnly/FeatureServer/25",
               "District", "Name"),
    "St. Louis": ("https://gis.stlouiscountymn.gov/server2/rest/services/"
                  "GeneralUse/Open_Data/MapServer/21", "DISTRICTID", "REPNAME1"),
}

OFFICE_RE = re.compile(r"^(Special Election for )?County Commissioner District (\d+)"
                       r"( \(Special Primary\))?$")


def fail(msg):
    raise SystemExit("build-mn-commissioner-roster: FATAL: %s" % msg)


def seats_from_geometry():
    """(county, district) -> county FIPS, from the shipped boundary file, so
    the roster can never name a district the map does not draw."""
    with open(DISTRICTS_FILE, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    seats = {}
    for feat in feats:
        p = feat["properties"]
        seats[(p["county"], int(p["district"]))] = p["countyFips"]
    if len(seats) != EXPECT_SEATS:
        fail("the shipped geometry draws %d districts, expected %d"
             % (len(seats), EXPECT_SEATS))
    return seats


def county_names(seats, session):
    """The results files number counties 1..87 (01 Aitkin .. 87 Yellow
    Medicine), which is FIPS (2n - 1). The mapping is derived from the
    geometry's own FIPS and then HELD to the Secretary of State's own county
    table (Cntytbl.txt), compared without case because that table writes
    "Mcleod" and "Lac Qui Parle"."""
    by_fips = {fips: county for (county, _), fips in seats.items()}
    names = {(int(fips) + 1) // 2: county for fips, county in by_fips.items()}
    url = COUNTY_TABLE % FIRST_ELECTION.strftime("%Y%m%d")
    require_robots_once(url, USER_AGENT)
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    rows = [l.split(";") for l in resp.content.decode("latin-1").splitlines() if l.strip()]
    if len(rows) != 87:
        fail("the county table has %d rows, expected 87" % len(rows))
    for row in rows:
        ours = names.get(int(row[0]))
        if ours is None or ours.lower() != row[1].strip().lower():
            fail("county %s is %r in the results files and %r in the geometry"
                 % (row[0], row[1], ours))
    return names


def fetch_elections(session, today):
    """{date: text} for every Tuesday from FIRST_ELECTION to today whose
    results directory carries a county races file."""
    require_robots_once(RESULTS_FILE % FIRST_ELECTION.strftime("%Y%m%d"), USER_AGENT)
    out = {}
    day = FIRST_ELECTION
    while day <= today:
        url = RESULTS_FILE % day.strftime("%Y%m%d")
        resp = session.get(url, headers={"User-Agent": USER_AGENT},
                           timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            out[day] = resp.content.decode("latin-1")
        elif resp.status_code != 404:
            fail("%s answered HTTP %d — a probe that cannot tell an empty day "
                 "from a failure must stop" % (url, resp.status_code))
        time.sleep(PACE_SECONDS)
        day += datetime.timedelta(days=7)
    if FIRST_ELECTION not in out:
        fail("the 2022 general's results file is missing — every seat rests on it")
    return out


def contests(elections, names):
    """Every commissioner contest, as dicts, oldest election first."""
    found = []
    for day in sorted(elections):
        groups = {}
        for line in elections[day].splitlines():
            if not line.strip():
                continue
            f = line.split(";")
            if len(f) < 16:
                fail("%s: a line with %d fields: %r" % (day, len(f), line[:120]))
            m = OFFICE_RE.match(f[4].strip())
            if not m:
                continue
            key = (int(f[1]), f[4].strip())
            groups.setdefault(key, []).append(f)
        for (cty, office), rows in sorted(groups.items()):
            m = OFFICE_RE.match(office)
            county = names.get(cty)
            if county is None:
                fail("%s: county number %d is not one of Minnesota's 87" % (day, cty))
            cands = [(r[7].strip(), int(r[13])) for r in rows]
            found.append({
                "date": day, "county": county, "district": int(m.group(2)),
                "special": bool(m.group(1)), "labelled_primary": bool(m.group(3)),
                "office": office, "candidates": cands,
            })
    return found


def winner(contest):
    cands = sorted(contest["candidates"], key=lambda c: -c[1])
    if len(cands) > 1 and cands[0][1] == cands[1][1]:
        return None, "the published result is a tie, which Minnesota breaks by lot"
    if cands[0][0].upper() == "WRITE-IN":
        return None, "the seat was won by write-in votes, which the results do not name"
    return cands[0][0], None


def is_general(contest):
    """A general carries a WRITE-IN line and a primary does not.

    Measured on every county races file from 2022-08-09 to 2026-08-11: all
    289 of 2022's and 227 of 2024's November commissioner contests carry one,
    every special general does, and no contest a later file shows to have been
    a primary does — Hennepin District 6 on 30 April 2024 and Anoka District 1
    on 13 August 2024, both unlabelled, the regular August contests, and both
    labelled special primaries. So the write-in line, not the office name or
    the date, says which kind of contest a row is."""
    return (not contest["labelled_primary"]
            and any(n.upper() == "WRITE-IN" for n, _ in contest["candidates"]))


def choose(all_contests, today):
    """seat -> the newest general that has been canvassed."""
    chosen, held = {}, []
    for c in sorted(all_contests, key=lambda c: c["date"]):
        if not is_general(c):
            continue
        age = (today - c["date"]).days
        if age < CANVASS_DAYS:
            held.append((c, "not yet canvassed (%d days old)" % age))
            continue
        chosen[(c["county"], c["district"])] = c
    return chosen, held


def build(seats, chosen):
    out = {}
    for (county, dist), fips in sorted(seats.items()):
        key = "%s-%d" % (fips, dist)
        c = chosen.get((county, dist))
        rec = {"county": county, "district": dist}
        if c is None:
            why = KNOWN_UNNAMED.get("%s|%d" % (county, dist))
            if why is None:
                fail("%s County District %d has no counting contest and no "
                     "KNOWN_UNNAMED entry" % (county, dist))
            rec["unnamed"] = why
        else:
            name, why = winner(c)
            rec["election"] = c["date"].isoformat()
            rec["special"] = c["special"]
            if name:
                rec["name"] = name
            else:
                rec["unnamed"] = why
            rec["sourceUrl"] = RESULTS_FILE % c["date"].strftime("%Y%m%d")
        out[key] = rec
    return out


def check(roster, seats):
    problems = []
    if len(roster) != EXPECT_SEATS:
        problems.append("%d records, expected %d" % (len(roster), EXPECT_SEATS))
    want = {"%s-%d" % (fips, d) for (_, d), fips in seats.items()}
    if set(roster) != want:
        problems.append("the roster's districts differ from the shipped geometry's: "
                        "%d missing, %d extra" % (len(want - set(roster)),
                                                  len(set(roster) - want)))
    named = 0
    for key, rec in roster.items():
        label = "%s|%d" % (rec.get("county"), rec.get("district"))
        if rec.get("name"):
            named += 1
            if not rec.get("election") or not rec.get("sourceUrl"):
                problems.append("%s names somebody without the election that seated them" % key)
            if label in KNOWN_UNNAMED:
                problems.append("KNOWN_UNNAMED records %s and it is now named — drop the entry" % label)
        elif not rec.get("unnamed"):
            problems.append("%s names nobody and says nothing about why" % key)
        elif "election" not in rec and label not in KNOWN_UNNAMED:
            problems.append("%s names nobody, has no election and no KNOWN_UNNAMED entry" % key)
    for label in KNOWN_UNNAMED:
        county, dist = label.split("|")
        if (county, int(dist)) not in seats:
            problems.append("KNOWN_UNNAMED names %s, which the geometry does not draw" % label)
    if named < MIN_NAMED:
        problems.append("%d seats named, floor %d" % (named, MIN_NAMED))
    return problems, named


def compare_with_counties(session, roster):
    """Print each county layer's name beside the results-file winner."""
    import requests  # noqa: PLC0415
    by_seat = {(r["county"], r["district"]): r for r in roster.values()}
    agree = total = forms = 0
    for county, (url, dfield, nfield) in COUNTY_NAME_WITNESSES.items():
        q = (url + "/query?where=1%3D1&outFields=" + dfield + "," + nfield
             + "&returnGeometry=false&f=json")
        try:
            require_robots_once(q, USER_AGENT)
            doc = session.get(q, headers={"User-Agent": USER_AGENT},
                              timeout=REQUEST_TIMEOUT).json()
        except (requests.RequestException, ValueError) as exc:
            print("  witness %s: unreadable (%s)" % (county, exc))
            continue
        if "error" in doc:
            print("  witness %s: error envelope %r" % (county, doc["error"]))
            continue
        for feat in doc.get("features") or []:
            a = feat["attributes"]
            m = re.search(r"\d+", str(a.get(dfield)))
            if not m:
                continue
            theirs = (a.get(nfield) or "").strip()
            ours = (by_seat.get((county, int(m.group(0)))) or {}).get("name") or ""
            total += 1
            rec = by_seat.get((county, int(m.group(0))))
            if _norm(theirs) == _norm(ours):
                agree += 1
            elif theirs and _surname(theirs) == _surname(ours):
                forms += 1
                print("  witness %s District %s: same person, another form — "
                      "county %r, results %r" % (county, m.group(0), theirs, ours))
            elif theirs and rec is not None:
                rec["countySays"] = {"name": theirs, "publisher": county + " County",
                                     "sourceUrl": url}
                print("  witness %s District %s: DIFFERENT PERSON — county says "
                      "%r, results say %r; the record carries both"
                      % (county, m.group(0), theirs, ours))
    print("county name witnesses: %d of %d agree exactly, %d more are the same "
          "surname" % (agree, total, forms))


def _surname(name):
    return _norm(name.split()[-1]) if name.split() else ""


def _norm(name):
    name = re.sub(r"\b[A-Z]\.\s*", "", name)   # middle initials
    return re.sub(r"[^a-z]", "", name.lower())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped roster to the shipped geometry")
    args = ap.parse_args()
    seats = seats_from_geometry()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as f:
            roster = json.load(f)
        problems, named = check(roster, seats)
        if problems:
            for p in problems:
                print("build-mn-commissioner-roster: FAIL: " + p)
            raise SystemExit(1)
        print("build-mn-commissioner-roster --check: OK — %d of %d seats named, "
              "each dated to the election that seated it" % (named, len(roster)))
        return
    import requests  # noqa: PLC0415
    session = requests.Session()
    today = datetime.date.today()
    names = county_names(seats, session)
    elections = fetch_elections(session, today)
    print("results files with county contests: %s"
          % ", ".join(d.isoformat() for d in sorted(elections)))
    all_contests = contests(elections, names)
    chosen, held = choose(all_contests, today)
    for c, why in held:
        print("  held: %s %s County District %d — %s"
              % (c["date"], c["county"], c["district"], why))
    roster = build(seats, chosen)
    for r in roster.values():
        if not r.get("name"):
            print("  unnamed: %s County District %d — %s"
                  % (r["county"], r["district"], r["unnamed"]))
    problems, named = check(roster, seats)
    if problems:
        for p in problems:
            print("build-mn-commissioner-roster: FAIL: " + p)
        raise SystemExit(1)
    specials = sum(1 for r in roster.values() if r.get("special"))
    by_year = {}
    for r in roster.values():
        if r.get("election"):
            by_year[r["election"]] = by_year.get(r["election"], 0) + 1
    print("seats by the election that names them: %s"
          % ", ".join("%s %d" % kv for kv in sorted(by_year.items())))
    compare_with_counties(session, roster)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("wrote %s: %d seats, %d named, %d from special elections"
          % (os.path.relpath(OUT_FILE, os.path.dirname(INSTANCE)), len(roster),
             named, specials))


if __name__ == "__main__":
    main()
