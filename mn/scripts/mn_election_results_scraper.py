#!/usr/bin/env python3
"""
Read one Minnesota election's precinct-by-precinct results from the Secretary
of State, and write them as JSON for build_mn_election_results.py.

THE SOURCE. The Secretary of State publishes every election's results as
semicolon-separated text files under
https://electionresultsfiles.sos.mn.gov/<YYYYMMDD>/ (the 3 November 2026
general election is 20261103, read 2026-11-05). Three of them are read:

  allracesbyprecinct.txt  every federal, state, judicial, county, soil and
                          water, and constitutional-amendment contest, one row
                          per candidate per precinct
  localPrct.txt           every municipal, school district and hospital
                          district contest and question, in the same layout
  pctstats.txt            each precinct's registered voters at 7 a.m., its
                          election-day registrations and the number who voted

The layout of all three is the office's own "View layout of text files" page
(electionresults.sos.mn.gov/Results/MediaFileLayout/Index?erselectionId=201,
"Last revised 06/03/2026"): State; County ID; Precinct ID; Office ID; Office
Name; District; Candidate Order Code; Candidate Name; Suffix; Incumbent Code;
Party Abbreviation; precincts reporting; precincts voting for the office; Votes
for Candidate; percentage; Total votes for Office in area. That page sits on
the results site, which a Radware bot manager fronts, and this script never
reads it; the files host is a plain IIS server whose robots.txt answers 404
(no policy, allow all), read first with the client below.

THE FILES ARE WINDOWS-1252, with CRLF line ends (measured on the 2026 files:
accented names such as "Hernández" are single bytes 0xE1, 0xE9, 0xED, 0xF3,
0xF6), so they are decoded that way rather than as UTF-8.

THE ROWS ARE CHECKED, NOT TRUSTED: every results row must carry sixteen fields,
a two-digit county id between 01 and 87, a four-digit precinct id and whole
numbers for the votes, and every precinct a results row names must be one
pctstats.txt lists. A file that fails any check fails the run.

WHAT THESE NUMBERS ARE. Unofficial until canvassed. County canvassing boards
meet between the third and tenth day after the election and the State
Canvassing Board on the third Tuesday after it (Minn. Stat. 204C.33), and the
office updates these files until then. The builder stamps every file with the
time it was read and `certified: false`.

Usage:
    python3 mn/scripts/mn_election_results_scraper.py --election 20261103 -o /tmp/mn_results_raw.json
    python3 mn/scripts/mn_election_results_scraper.py --election 20261103 --from-dir DIR -o ...
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

from scraper_common import make_fail, require_robots_once  # noqa: E402

fail = make_fail("mn-election-results-scraper")

FILES_HOST = "https://electionresultsfiles.sos.mn.gov"
FILES = ("allracesbyprecinct.txt", "localPrct.txt", "pctstats.txt")
# The same client every Minnesota results builder sends this host
# (build_mn_commissioner_roster.py and its siblings).
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 120
PACE_SECONDS = 1.0
MIN_RESULT_ROWS = {"allracesbyprecinct.txt": 100000, "localPrct.txt": 10000}
EXPECTED_PRECINCTS_MIN = 4000


def fetch(election, from_dir):
    texts = {}
    if from_dir:
        for name in FILES:
            with open(os.path.join(from_dir, name), "rb") as fh:
                texts[name] = fh.read().decode("cp1252")
        return texts
    import requests  # noqa: PLC0415
    session = requests.Session()
    for i, name in enumerate(FILES):
        url = "%s/%s/%s" % (FILES_HOST, election, name)
        require_robots_once(url, USER_AGENT)
        if i:
            time.sleep(PACE_SECONDS)
        resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            fail("%s answered HTTP %d" % (url, resp.status_code))
        texts[name] = resp.content.decode("cp1252")
    return texts


def whole(text, where):
    if not re.fullmatch(r"\d+", text):
        fail("%s: %r is not a whole number" % (where, text))
    return int(text)


def parse_stats(text):
    stats = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        f = line.split(";")
        where = "pctstats.txt line %d" % n
        if len(f) != 12 or f[0] != "MN":
            fail("%s has %d fields" % (where, len(f)))
        key = (f[1], f[2])
        if key in stats:
            fail("%s repeats precinct %s-%s" % (where, f[1], f[2]))
        stats[key] = {
            "name": f[3].strip(),
            "reported": f[4] == "1",
            "registered7am": whole(f[5], where),
            "registeredToday": whole(f[6], where),
            "voted": whole(f[11], where),
        }
    if len(stats) < EXPECTED_PRECINCTS_MIN:
        fail("pctstats.txt lists %d precincts, expected at least %d"
             % (len(stats), EXPECTED_PRECINCTS_MIN))
    return stats


def parse_results(name, text, stats):
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        f = line.split(";")
        where = "%s line %d" % (name, n)
        if len(f) != 16 or f[0] != "MN":
            fail("%s has %d fields" % (where, len(f)))
        if not (re.fullmatch(r"\d\d", f[1]) and 1 <= int(f[1]) <= 87):
            fail("%s: county id %r" % (where, f[1]))
        if not re.fullmatch(r"\d{4}", f[2]):
            fail("%s: precinct id %r" % (where, f[2]))
        if (f[1], f[2]) not in stats:
            fail("%s: precinct %s-%s is not in pctstats.txt" % (where, f[1], f[2]))
        rows.append({
            "county": f[1], "precinct": f[2], "officeId": f[3], "office": f[4].strip(),
            "district": f[5].strip(), "order": f[6], "candidate": f[7].strip(),
            "party": f[10].strip(), "votes": whole(f[13], where),
            "officeVotes": whole(f[15], where),
        })
    if len(rows) < MIN_RESULT_ROWS[name]:
        fail("%s has %d rows, expected at least %d" % (name, len(rows), MIN_RESULT_ROWS[name]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--election", required=True, help="the election's directory, YYYYMMDD")
    ap.add_argument("--from-dir", help="read the three files from this directory instead")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"\d{8}", args.election):
        fail("--election must be YYYYMMDD")

    texts = fetch(args.election, args.from_dir)
    stats = parse_stats(texts["pctstats.txt"])
    raw = {
        "source": "%s/%s/" % (FILES_HOST, args.election),
        "read": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
                        .isoformat().replace("+00:00", "Z"),
        "stats": [dict(v, county=k[0], precinct=k[1]) for k, v in sorted(stats.items())],
        "results": parse_results("allracesbyprecinct.txt", texts["allracesbyprecinct.txt"], stats),
        "local": parse_results("localPrct.txt", texts["localPrct.txt"], stats),
    }
    with open(args.output, "w") as fh:
        json.dump(raw, fh, separators=(",", ":"), ensure_ascii=False)
    print("read %d precincts, %d statewide-file rows and %d local rows from %s"
          % (len(raw["stats"]), len(raw["results"]), len(raw["local"]), raw["source"]),
          file=sys.stderr)


if __name__ == "__main__":
    main()
