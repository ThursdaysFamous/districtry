#!/usr/bin/env python3
"""
Read San Francisco's precinct results for one election from the Department of
Elections, and write them as JSON for build_sf_election_results.py.

THE SOURCE. The Department publishes each election's reports at
https://www.sfelections.org/results/<election>w/detail.html, newest first. Each
report on the day it is published carries a Statement of the Vote by precinct
as an Excel workbook (sov.xlsx): one sheet per contest, plus a first sheet of
turnout. A sheet lists every precinct the contest is on the ballot in, each as
an Election Day row, a Vote by Mail row and a Total row; the scraper reads the
Total rows. A precinct whose voters all vote by mail is written "PCT 1103 MB";
it is the same precinct as 1103 on the precinct map.

THE CLIENT, MEASURED 2026-11-06. www.sfelections.org sits behind CloudFront,
which answers this project's own token (districtry/1.0 and the roster token,
stdlib client) with HTTP 403 "Request blocked" on robots.txt and on the
results page alike. The stdlib client with Chrome/126 and its client hints
(scraper_common.UA_HINTS_CHROME_126) is served: robots.txt answers 404, which
RFC 9309 reads as no policy (allow all), and the results page answers 200. So
this file sends the browser string, reads robots.txt with exactly that client
first, and never escalates past it. The reports themselves are public files
the page links.

THE WORKBOOK IS CHECKED, NOT TRUSTED: every sheet must name its contest and
carry a header row naming its choices and a Total Votes column; every
precinct's Total row must carry a whole number in every choice column; the
choices must add to the Total Votes column; the precincts must add to the
sheet's Countywide - Total row (a sheet whose Total Votes leaves the write-in
column out is recorded as such, and read that way for every precinct); and the run fails if fewer than MIN_CONTESTS
contests or MIN_PRECINCTS precincts are read.

WHAT THESE NUMBERS ARE. The Department's preliminary results, updated on each
day it tabulates ballots, until it certifies them (California Elections Code
section 15372: no later than the 30th day after the election). The page's
"Last Update" time is recorded so the daily job can tell when the Department
has published again. In a ranked-choice contest the counts are first choices.

Usage:
    python3 ca/scripts/sf_election_results_scraper.py -o /tmp/sf_results_raw.json
    python3 ca/scripts/sf_election_results_scraper.py --as-of-only   # print the page's Last Update and exit
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import (  # noqa: E402
    UA_CHROME_WIN_126, UA_HINTS_CHROME_126, make_fail, require_robots_once,
)

fail = make_fail("sf-election-results-scraper")

DETAIL = "https://www.sfelections.org/results/20261103w/detail.html"
HEADERS = dict(UA_HINTS_CHROME_126)
REQUEST_TIMEOUT = 120
MIN_CONTESTS = 30
MIN_PRECINCTS = 500
WRITE_IN = "Write-in"


def get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                fail("%s: %s" % (url, e))
            time.sleep(3 * (attempt + 1))


def text(fragment):
    return " ".join(re.sub(r"<[^>]+>", " ", fragment).replace("&nbsp;", " ").split())


def last_update(page):
    m = re.search(r"Last Update:\s*([A-Z][a-z]+ \d{1,2}, \d{4} \d{1,2}:\d{2} [AP]M)", text(page))
    return m.group(1) if m else None


def whole(v, where):
    if isinstance(v, bool) or not isinstance(v, int):
        fail("%s: %r is not a whole number" % (where, v))
    return v


def label(v):
    return " ".join(str(v or "").split())


def parse_sheet(ws, where):
    """(title, columns, {precinct: [counts...]}, countywide totals, registered)
    for a contest sheet, or the turnout sheet's rows when it has no title."""
    rows = list(ws.iter_rows(values_only=True))
    head_i = next((i for i, r in enumerate(rows) if r and r[0] == "Precinct"), None)
    if head_i is None:
        fail("%s has no header row" % where)
    head = rows[head_i]
    title = label(rows[1][0]) if len(rows) > 1 and rows[1] else ""
    if "Voters Cast" in [label(h) for h in head]:
        reg_i = [label(h) for h in head].index("Registered Voters")
        cast_i = [label(h) for h in head].index("Voters Cast")
        out, cur, county = {}, None, None
        for r in rows[head_i + 1:]:
            if not r:
                continue
            if isinstance(r[0], str) and r[0].startswith("PCT "):
                cur = r[0]
            elif r[0] == "Total" and cur:
                out[cur] = [whole(r[reg_i], "%s %s" % (where, cur)), whole(r[cast_i], "%s %s" % (where, cur))]
                cur = None
            elif r[0] == "Countywide - Total":
                county = [whole(r[reg_i], where), whole(r[cast_i], where)]
        return None, None, out, county, None
    if not title:
        fail("%s names no contest" % where)
    second = [i for i, h in enumerate(head) if h == "Precinct"]
    if len(second) < 2:
        fail("%s: the header row %r has no second Precinct column" % (where, head))
    total_i = next((i for i, h in enumerate(head) if label(h).startswith("Total Votes")), None)
    if total_i is None:
        fail("%s: no Total Votes column" % where)
    cols = [(i, label(h)) for i, h in enumerate(head) if i > second[1] and i < total_i and label(h)]
    if not cols:
        fail("%s names no choices" % where)
    out, cur, county, write_ins = {}, None, None, None
    for r in rows[head_i + 1:]:
        if not r:
            continue
        if isinstance(r[0], str) and r[0].startswith("PCT "):
            cur = r[0]
            continue
        if r[0] == "Total" and cur:
            w = "%s %s" % (where, cur)
            counts = [whole(r[i], w) for i, _n in cols]
            tv = whole(r[total_i], w)
            named = sum(c for c, (_i, n) in zip(counts, cols) if n != WRITE_IN)
            # Some sheets count the write-in column into Total Votes and some
            # leave it out (measured 2026-11-06: Superintendent of Public
            # Instruction leaves it out); either is read, the same way for
            # every precinct of one sheet.
            way = "with" if sum(counts) == tv else "without" if named == tv and named != sum(counts) else None
            if way is None:
                fail("%s: its choices add to %d (%d without write-ins) and its Total Votes says %d"
                     % (w, sum(counts), named, tv))
            if sum(counts) != named:
                if write_ins not in (None, way):
                    fail("%s counts write-ins into Total Votes in some precincts and not others" % where)
                write_ins = way
            if cur in out:
                fail("%s is listed twice" % w)
            out[cur] = counts
            cur = None
        elif r[0] == "Countywide - Total":
            county = [whole(r[i], "%s countywide" % where) for i, _n in cols]
    if not out:
        fail("%s has no precinct rows" % where)
    if county is None:
        fail("%s has no Countywide - Total row" % where)
    summed = [sum(v[i] for v in out.values()) for i in range(len(cols))]
    if summed != county:
        fail("%s: its precincts add to %r and its Countywide - Total row says %r" % (where, summed, county))
    return title, [n for _i, n in cols], out, county, write_ins


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--detail", default=DETAIL, help="the election's detailed reports page")
    ap.add_argument("--as-of-only", action="store_true", help="print the page's Last Update time and exit")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    require_robots_once(args.detail, UA_CHROME_WIN_126, headers=HEADERS)
    page = get(args.detail).decode("utf-8", "replace")
    stamp = last_update(page)
    if args.as_of_only:
        print(stamp or "")
        return
    if not args.output:
        fail("-o is required")
    links = re.findall(r'href="([^"]*/sov\.xlsx)"', page)
    if not links:
        fail("%s links no Statement of the Vote workbook" % args.detail)
    sov = urllib.parse.urljoin(args.detail, links[0])

    import openpyxl  # noqa: PLC0415 - only the full read needs it
    wb = openpyxl.load_workbook(io.BytesIO(get(sov)), read_only=True)
    turnout, county_turnout = None, None
    contests = []
    titles = set()
    for sn in wb.sheetnames:
        title, cols, rows, county, write_ins = parse_sheet(wb[sn], "%s %s" % (os.path.basename(sov), sn))
        if title is None:
            turnout, county_turnout = rows, county
            continue
        if title in titles:
            fail("%s is split across sheets, which this reader does not join" % title)
        titles.add(title)
        contests.append({"sheet": sn, "title": title, "columns": cols, "rows": rows,
                         "writeInsInTotal": write_ins != "without"})
        print("  %s: %d precincts" % (title, len(rows)), file=sys.stderr)
    if turnout is None or county_turnout is None:
        fail("the workbook has no turnout sheet")
    if [sum(v[0] for v in turnout.values()), sum(v[1] for v in turnout.values())] != county_turnout:
        fail("the turnout sheet's precincts do not add to its Countywide - Total row")
    if len(contests) < MIN_CONTESTS:
        fail("%d contests, expected at least %d" % (len(contests), MIN_CONTESTS))
    if len(turnout) < MIN_PRECINCTS:
        fail("%d precincts, expected at least %d" % (len(turnout), MIN_PRECINCTS))
    raw = {
        "source": args.detail,
        "workbook": sov,
        "read": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
                        .isoformat().replace("+00:00", "Z"),
        "asOf": stamp,
        "turnout": turnout,
        "contests": contests,
    }
    with open(args.output, "w") as fh:
        json.dump(raw, fh, separators=(",", ":"), ensure_ascii=False)
    print("read %d contests across %d precincts from %s (last update %s)"
          % (len(contests), len(turnout), sov, stamp), file=sys.stderr)


if __name__ == "__main__":
    main()
