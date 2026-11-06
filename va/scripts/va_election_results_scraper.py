#!/usr/bin/env python3
"""
Read one Virginia election's precinct-by-precinct results from the Department
of Elections, and write them as JSON for build_va_election_results.py.

THE SOURCE. The Department publishes election night results at
https://enr.elections.virginia.gov/results/public/virginia/elections/<slug>
(the 3 November 2026 general election is 2026-November-General). That page is
an application that reads the election from its own API,
/results/public/api/elections/virginia/<slug>, and the API lists the reports
the page offers for download under publicReportCategories. The one named
"Election Results" is a comma-separated file of every contest by precinct,
served from /cdn/results/<jurisdictionId>/<blobName>. The blob name carries a
new identifier each time the Department publishes, so it is read from the API
on every run, never stored. Read 2026-11-06 (published 5 November 23:21 UTC).
enr.elections.virginia.gov answers robots.txt with HTTP 404 (no policy, allow
all), read first with the client below. (www.elections.virginia.gov, the
Department's main site, disallows *.csv; this script never fetches from it.)

THE FILE. Nineteen columns, one row per choice per precinct: CandidateId,
CandidateName, TOTAL_VOTES, Party, WriteInVote, LocalityCode, LocalityName,
PrecinctId, PrecinctName, DistrictId, DistrictType, DistrictName, OfficeId,
OfficeTitle, ElectionId, ElectionType, ElectionDate, ElectionName,
NumberOfSeats. A write-in line leaves TOTAL_VOTES empty and carries its votes
in WriteInVote; a few write-in lines carry them in TOTAL_VOTES instead, so a
row's votes are TOTAL_VOTES where it is filled and WriteInVote where not. The
text is Windows-1252 (a candidate's accented name is one byte). One precinct
id carries a trailing space, which is removed.

EVERY VOTE IS IN A PRECINCT. The election's count groups (Early Voting,
Election Day, Mailed Absentee, Provisional, Post-Election) are each reported
with isFromVirtualPrecinct false, and the file has no central absentee
precinct, so every count belongs to the precinct it names.

THE ROWS ARE CHECKED, NOT TRUSTED: the header must be exactly the nineteen
columns above, every row must carry nineteen fields, name the election's date,
a locality, a precinct and an office, carry whole numbers for its votes and
seats, and fill at least one of the two vote columns. A file that fails any
check fails the run.

WHAT THESE NUMBERS ARE. Unofficial until certified. Each county's and city's
electoral board ascertains its results within ten days of the election
(Code of Virginia 24.2-671) and the State Board of Elections meets by the
first Monday in December to ascertain the results of the November election
(24.2-679). The API's isOfficialResults is recorded, and the builder stamps
every file with the time it was read and `certified: false`.

Usage:
    python3 va/scripts/va_election_results_scraper.py --election 2026-November-General --date 2026-11-03 -o /tmp/va_results_raw.json
    python3 va/scripts/va_election_results_scraper.py ... --from-file results.csv
"""

import argparse
import csv
import datetime
import io
import json
import os
import re
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import make_fail, require_robots_once  # noqa: E402

fail = make_fail("va-election-results-scraper")

HOST = "https://enr.elections.virginia.gov"
USER_AGENT = "districtry/1.0 (+https://districtry.com/va/)"
REQUEST_TIMEOUT = 120
REPORT_NAME = "Election Results"
HEADER = ["CandidateId", "CandidateName", "TOTAL_VOTES", "Party", "WriteInVote", "LocalityCode",
          "LocalityName", "PrecinctId", "PrecinctName", "DistrictId", "DistrictType",
          "DistrictName", "OfficeId", "OfficeTitle", "ElectionId", "ElectionType",
          "ElectionDate", "ElectionName", "NumberOfSeats"]
MIN_ROWS = 30000
MIN_LOCALITIES = 130


def page_url(election):
    return "%s/results/public/virginia/elections/%s" % (HOST, election)


def api_url(election):
    return "%s/results/public/api/elections/virginia/%s" % (HOST, election)


def get(url):
    import requests  # noqa: PLC0415
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        fail("%s answered HTTP %d" % (url, resp.status_code))
    return resp


def fetch(election):
    """The election's API record, and the results file it names."""
    meta_url = api_url(election)
    require_robots_once(meta_url, USER_AGENT)
    meta = get(meta_url).json()
    found = []
    for cat in meta.get("publicReportCategories") or []:
        for rep in cat.get("reports") or []:
            if rep.get("reportName") == REPORT_NAME:
                found.append(rep["blobName"])
    if len(found) != 1:
        fail("the election lists %d reports named %r, expected one" % (len(found), REPORT_NAME))
    jurisdiction = meta.get("jurisdictionId")
    if not jurisdiction or not re.fullmatch(r"[0-9a-f-]{36}", jurisdiction):
        fail("the election names no jurisdiction id: %r" % jurisdiction)
    url = "%s/cdn/results/%s/%s" % (HOST, jurisdiction, quote(found[0]))
    return get(url).content, url, meta


def whole(text, where):
    if not re.fullmatch(r"\d+", text):
        fail("%s: %r is not a whole number" % (where, text))
    return int(text)


def parse(blob, date):
    text = blob.decode("cp1252")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    if header != HEADER:
        fail("the header is %r, expected %r" % (header, HEADER))
    rows = []
    for n, f in enumerate(reader, 2):
        if not any(x.strip() for x in f):
            continue
        where = "line %d" % n
        if len(f) != len(HEADER):
            fail("%s has %d fields" % (where, len(f)))
        r = dict(zip(HEADER, (x.strip() for x in f)))
        if r["ElectionDate"] != date:
            fail("%s: election date %r, expected %s" % (where, r["ElectionDate"], date))
        for col in ("LocalityCode", "LocalityName", "PrecinctId", "OfficeId", "OfficeTitle",
                    "DistrictType", "CandidateName"):
            if not r[col]:
                fail("%s: an empty %s" % (where, col))
        if not re.fullmatch(r"\d{3}", r["LocalityCode"]):
            fail("%s: locality code %r" % (where, r["LocalityCode"]))
        if not re.fullmatch(r"\d{3,6}", r["PrecinctId"]):
            fail("%s: precinct id %r" % (where, r["PrecinctId"]))
        if r["TOTAL_VOTES"]:
            votes = whole(r["TOTAL_VOTES"], where)
        elif r["WriteInVote"]:
            votes = whole(r["WriteInVote"], where)
        else:
            fail("%s: neither vote column is filled" % where)
        rows.append([r["LocalityCode"], r["LocalityName"], r["PrecinctId"], r["PrecinctName"],
                     r["DistrictType"], r["DistrictName"], r["OfficeId"], r["DistrictId"],
                     r["OfficeTitle"], whole(r["NumberOfSeats"], where), r["CandidateId"],
                     r["CandidateName"], r["Party"], votes])
    if len(rows) < MIN_ROWS:
        fail("%d rows, expected at least %d" % (len(rows), MIN_ROWS))
    localities = {r[0] for r in rows}
    if len(localities) < MIN_LOCALITIES:
        fail("%d localities, expected at least %d" % (len(localities), MIN_LOCALITIES))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--election", required=True, help="the election's name in the results address, "
                    "e.g. 2026-November-General")
    ap.add_argument("--date", required=True, help="the election's date, YYYY-MM-DD")
    ap.add_argument("--from-file", help="read this results file instead of downloading it")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        fail("--date must be YYYY-MM-DD")
    if not re.fullmatch(r"[A-Za-z0-9-]+", args.election):
        fail("--election must be letters, digits and hyphens")

    if args.from_file:
        with open(args.from_file, "rb") as fh:
            blob = fh.read()
        source, meta = page_url(args.election), {}
    else:
        blob, source, meta = fetch(args.election)
        if meta.get("electionDate") != args.date:
            fail("the election's date is %r, expected %s" % (meta.get("electionDate"), args.date))
    rows = parse(blob, args.date)
    raw = {
        "source": source,
        "page": page_url(args.election),
        "read": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
                        .isoformat().replace("+00:00", "Z"),
        "published": meta.get("publishDate"),
        "official": meta.get("isOfficialResults"),
        "columns": ["localityCode", "locality", "precinctId", "precinct", "districtType",
                    "district", "officeId", "districtId", "office", "seats", "candidateId",
                    "choice", "party", "votes"],
        "rows": rows,
    }
    with open(args.output, "w") as fh:
        json.dump(raw, fh, separators=(",", ":"), ensure_ascii=False)
    print("read %d rows across %d localities from %s"
          % (len(rows), len({r[0] for r in rows}), source), file=sys.stderr)


if __name__ == "__main__":
    main()
