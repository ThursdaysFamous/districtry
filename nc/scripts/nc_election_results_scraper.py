#!/usr/bin/env python3
"""
Read one North Carolina election's precinct-by-precinct results from the State
Board of Elections, and write them as JSON for build_nc_election_results.py.

THE SOURCE. The State Board publishes every election's results by precinct as
one zipped tab-separated file, results_pct_<YYYYMMDD>.zip, under
https://dl.ncsbe.gov/ENRS/<YYYY_MM_DD>/ (the 3 November 2026 general election
is ENRS/2026_11_03/results_pct_20261103.zip, linked from the Board's "Election
Results Data" page and read 2026-11-06, Last-Modified 5 November 21:45 GMT). It
holds every contest on any ballot in the state, one row per choice per
reporting unit, in fifteen columns: County, Election Date, Precinct, Contest
Group ID, Contest Type, Contest Name, Choice, Choice Party, Vote For, Election
Day, Early Voting, Absentee by Mail, Provisional, Total Votes, Real Precinct.
dl.ncsbe.gov answers robots.txt with HTTP 404 (no policy, allow all), read
first with the client below.

A REPORTING UNIT IS NOT ALWAYS A PRECINCT. "Real Precinct" is Y for a precinct
and N for the units a county counts on its own: ABSENTEE, PROVISIONAL,
TRANSFER and, in some counties, each one-stop early voting site. Those are kept
and marked, and the builder counts them in each race's total but in no
precinct's colour.

THE TEXT IS ASCII apart from NUL bytes, which the file writes as the Choice
Party of a choice that has none, and as the Choice of a seat nobody filed for
(6,137 on the 2026 file); they are removed, and a choice left empty must carry
no votes.

THE ROWS ARE CHECKED, NOT TRUSTED: the header must be exactly the fifteen
columns above, every row must carry fifteen fields, a Real Precinct of Y or N,
a Contest Type of S (a state-run contest) or C (a county-run one) and whole
numbers for the votes, and every row must name the election's date. A file
that fails any check fails the run.

WHAT THESE NUMBERS ARE. Unofficial until canvassed. County boards of elections
canvass on the tenth day after the election and the State Board certifies on
the third Tuesday after it (G.S. 163-182.5), and the Board refreshes this file
until then. The builder stamps every file with the time it was read and
`certified: false`.

Usage:
    python3 nc/scripts/nc_election_results_scraper.py --election 20261103 -o /tmp/nc_results_raw.json
    python3 nc/scripts/nc_election_results_scraper.py --election 20261103 --from-file results_pct_20261103.zip -o ...
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import make_fail, require_robots_once  # noqa: E402

fail = make_fail("nc-election-results-scraper")

FILES_HOST = "https://dl.ncsbe.gov"
USER_AGENT = "districtry/1.0 (+https://districtry.com/nc/)"
REQUEST_TIMEOUT = 120
HEADER = ["County", "Election Date", "Precinct", "Contest Group ID", "Contest Type",
          "Contest Name", "Choice", "Choice Party", "Vote For", "Election Day",
          "Early Voting", "Absentee by Mail", "Provisional", "Total Votes", "Real Precinct"]
MIN_ROWS = 50000
MIN_COUNTIES = 100


def url_for(election):
    return "%s/ENRS/%s_%s_%s/results_pct_%s.zip" % (
        FILES_HOST, election[:4], election[4:6], election[6:], election)


def fetch(election, from_file):
    if from_file:
        with open(from_file, "rb") as fh:
            return fh.read(), None
    import requests  # noqa: PLC0415
    url = url_for(election)
    require_robots_once(url, USER_AGENT)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        fail("%s answered HTTP %d" % (url, resp.status_code))
    return resp.content, resp.headers.get("Last-Modified")


def whole(text, where):
    if not re.fullmatch(r"\d+", text):
        fail("%s: %r is not a whole number" % (where, text))
    return int(text)


def parse(blob, election):
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        fail("the download is not a zip file")
    names = [n for n in zf.namelist() if n.lower().endswith(".txt")]
    if len(names) != 1:
        fail("the zip holds %d text files, expected one: %r" % (len(names), zf.namelist()))
    text = zf.read(names[0]).replace(b"\x00", b"").decode("ascii")
    lines = text.splitlines()
    if lines[0].split("\t") != HEADER:
        fail("the header is %r, expected %r" % (lines[0].split("\t"), HEADER))
    date = "%s/%s/%s" % (election[4:6], election[6:], election[:4])
    rows = []
    for n, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        f = line.split("\t")
        where = "%s line %d" % (names[0], n)
        if len(f) != 15:
            fail("%s has %d fields" % (where, len(f)))
        if f[1] != date:
            fail("%s: election date %r, expected %s" % (where, f[1], date))
        if f[4] not in ("S", "C"):
            fail("%s: contest type %r" % (where, f[4]))
        if f[14] not in ("Y", "N"):
            fail("%s: real precinct %r" % (where, f[14]))
        if not f[0].strip() or not f[2].strip() or not f[5].strip():
            fail("%s: an empty county, precinct or contest" % where)
        votes = [whole(x, where) for x in f[9:14]]
        # A line with no choice is a seat nobody filed for (Hyde County's
        # Currituck Township commissioner and Mesic's mayor in 2026), printed
        # with no votes; one carrying votes is not something the file explains.
        if not f[6].strip() and votes[4]:
            fail("%s: %d votes for a choice with no name" % (where, votes[4]))
        if sum(votes[:4]) != votes[4]:
            fail("%s: the four vote columns add up to %d, Total Votes is %d"
                 % (where, sum(votes[:4]), votes[4]))
        rows.append([f[0].strip(), f[2].strip(), f[3].strip(), f[4], f[5].strip(), f[6].strip(),
                     f[7].strip(), whole(f[8], where), votes[4], f[14] == "Y"])
    if len(rows) < MIN_ROWS:
        fail("%d rows, expected at least %d" % (len(rows), MIN_ROWS))
    counties = {r[0] for r in rows}
    if len(counties) < MIN_COUNTIES:
        fail("%d counties, expected %d" % (len(counties), MIN_COUNTIES))
    return names[0], rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--election", required=True, help="the election's date, YYYYMMDD")
    ap.add_argument("--from-file", help="read this zip instead of downloading it")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"\d{8}", args.election):
        fail("--election must be YYYYMMDD")

    blob, modified = fetch(args.election, args.from_file)
    name, rows = parse(blob, args.election)
    raw = {
        "source": url_for(args.election),
        "read": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
                        .isoformat().replace("+00:00", "Z"),
        "lastModified": modified,
        "columns": ["county", "precinct", "groupId", "type", "contest", "choice", "party",
                    "voteFor", "votes", "real"],
        "rows": rows,
    }
    with open(args.output, "w") as fh:
        json.dump(raw, fh, separators=(",", ":"), ensure_ascii=False)
    print("read %d rows across %d counties from %s (%s)"
          % (len(rows), len({r[0] for r in rows}), raw["source"], name), file=sys.stderr)


if __name__ == "__main__":
    main()
