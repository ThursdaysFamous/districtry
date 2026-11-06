#!/usr/bin/env python3
"""
Read one election's precinct-by-precinct results for the Illinois counties
whose clerks publish through Platinum Technology Resource's results site, and
write them as JSON for build_il_county_election_results.py.

THE SOURCE. https://platinumelectionresults.com serves eight Illinois county
clerks (Clinton, DeKalb, Franklin, Henry, Marion, Pike, Randolph and Wayne,
read 2026-11-06). Six of them are counties whose precinct lines the Illinois
map draws, and those six are read here, each by the site's own number for it:

    DeKalb 66, Franklin 21, Henry 76, Pike 103, Randolph 13, Wayne 14

For each county three addresses are read, the ones the site's own pages use:
  /data/<n>                         the "Data List" page, whose precinct menu
                                    gives each precinct's number and name
  /turnouts/precincts/<n>           each precinct's registered voters and
                                    ballots cast
  /reports/township/<n>/pd/<ids>    the "Precinct Detail" CSV the Data List
                                    page builds when every precinct is picked:
                                    one row per precinct, race and candidate
  /reports/township/<n>/rs/<ids>    the "Race Summary" CSV for the same
                                    precincts, the site's own totals, which the
                                    precinct rows must add up to

That is four requests per county, paced two seconds apart. robots.txt at that
host is not a file (the site answers the path with its home page, 395 KB of
HTML on 2026-11-06), which RFC 9309 reads as no rules, and the shared reader
records that reading on every run. The site served this project's own token,
on the stdlib client, on 2026-11-06.

WHAT THESE NUMBERS ARE. Unofficial until each county's canvass; every page
says "Unofficial Results". The builder stamps the file with the time it was
read and `certified: false`.

THE ROWS ARE CHECKED, NOT TRUSTED: every precinct in the menu must have a
turnout row and results rows; each race's precinct counts must add up, choice
by choice, to the Race Summary's; and the precinct ballots must add up to the
county's own total on its turnout page. A county that fails any check fails
the run.

Usage:
    python3 scripts/il_platinum_election_results_scraper.py -o /tmp/platinum_raw.json
"""

import argparse
import csv
import datetime
import html
import io
import json
import re
import sys
import time
import urllib.request

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,
                            require_robots_once)

fail = make_fail("il-platinum-election-results-scraper")

BASE = "https://platinumelectionresults.com"
PACE_SECONDS = 2.0
COUNTIES = [("dekalb", "DeKalb", 66), ("franklin", "Franklin", 21), ("henry", "Henry", 76),
            ("pike", "Pike", 103), ("randolph", "Randolph", 13), ("wayne", "Wayne", 14)]

OPTION_RE = re.compile(r'<option[^>]*value="(\d+)"[^>]*>([^<]*)</option>')
TURNOUT_ROW_RE = re.compile(
    r'<div class="p-2[^"]*col-12">([^<]+)</div>\s*'
    r'<div class="p-2[^"]*text-right">([\d,]+)</div>\s*'
    r'<div class="p-2[^"]*text-right">([\d,]+)</div>\s*'
    r'<div class="p-2[^"]*"><div id="twnp_(\d+)"></div></div>')
COUNTY_TOTAL_RE = re.compile(r"Total Ballots Cast:\s*([\d,]+)")

_last = [0.0]


def get(url):
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    wait = PACE_SECONDS - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers=dict(UA_HEADERS_ROSTER_BOT))
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read()
    finally:
        _last[0] = time.time()
    return body.decode("utf-8-sig", "replace")


def num(text):
    return int(str(text).replace(",", "").strip() or 0)


def clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def read_county(tag, name, n):
    page = get("%s/data/%d" % (BASE, n))
    precincts = [(pid, clean(label)) for pid, label in OPTION_RE.findall(page) if int(pid) > 20000]
    if len(precincts) < 10:
        fail("%s: the Data List page names %d precincts" % (name, len(precincts)))
    ids = ",".join(pid for pid, _ in precincts)
    names = dict(precincts)

    tpage = get("%s/turnouts/precincts/%d" % (BASE, n))
    turnout = {}
    for label, reg, cast, pid in TURNOUT_ROW_RE.findall(tpage):
        if pid in names:
            turnout[names[pid]] = [num(reg), num(cast)]
    missing = [names[p] for p in names if names[p] not in turnout]
    if missing:
        fail("%s: no turnout row for %s" % (name, ", ".join(missing[:5])))
    cpage = get("%s/turnouts/county/%d" % (BASE, n))
    m = COUNTY_TOTAL_RE.search(clean(cpage))
    if not m:
        fail("%s: the county page gives no ballots-cast total" % name)
    county_ballots = num(m.group(1))
    if sum(v[1] for v in turnout.values()) != county_ballots:
        fail("%s: precinct ballots add to %d, the county page says %d"
             % (name, sum(v[1] for v in turnout.values()), county_ballots))

    detail = list(csv.DictReader(io.StringIO(get("%s/reports/township/%d/pd/%s" % (BASE, n, ids)))))
    summary = list(csv.DictReader(io.StringIO(get("%s/reports/township/%d/rs/%s" % (BASE, n, ids)))))
    if not detail:
        fail("%s: the Precinct Detail CSV has no rows" % name)

    races = {}
    order = []
    for row in detail:
        rno = row["Race No"].strip()
        if rno not in races:
            races[rno] = {"raceNo": rno, "name": clean(row["Race Name"]), "district": clean(row["District Name"]),
                          "voteFor": num(row["Vote For"] or 1), "choices": [], "precincts": {}}
            order.append(rno)
        race = races[rno]
        cand = clean(row["Name"])
        if cand not in race["choices"]:
            race["choices"].append(cand)
        pname = clean(row["Precinct Name"])
        if pname not in turnout:
            fail("%s race %s: precinct %r is not in the precinct menu" % (name, rno, pname))
        race["precincts"].setdefault(pname, {})[cand] = num(row["Votes"])

    sums = {}
    for row in summary:
        # the summary numbers its races by sequence, not by the detail's race
        # number, so the two are joined on the race's own name
        rname = clean(row.get("Race Name", ""))
        cand = clean(row.get("Candidate[Name]", ""))
        # it repeats each race's total once per precinct picked, so a race whose
        # repeated rows disagree is a summary this script does not understand
        if rname and cand:
            v = num(row.get("Candidate[Votes]", 0))
            if sums.get(rname, {}).get(cand, v) != v:
                fail("%s: the Race Summary gives %r two totals for %r" % (name, rname, cand))
            sums.setdefault(rname, {})[cand] = v
    if not sums:
        fail("%s: the Race Summary CSV has no rows (columns %r)" % (name, list(summary[0].keys()) if summary else []))
    contests = []
    for rno in order:
        race = races[rno]
        for cand in race["choices"]:
            got = sum(p.get(cand, 0) for p in race["precincts"].values())
            # the summary cuts a two-line name (a ticket) at its line break,
            # so "(Darren Bailey" there is "(Darren Bailey (Aaron B. Del Mar" here
            given = sums.get(race["name"], {})
            hits = [k for k in given if cand == k or cand.startswith(k + " ")]
            want = given[hits[0]] if len(hits) == 1 else None
            if want is None or got != want:
                fail("%s race %s %r: precincts add to %d for %r, the Race Summary says %r"
                     % (name, rno, race["name"], got, cand, want))
        race["precincts"] = dict((p, [counts.get(c, 0) for c in race["choices"]])
                                 for p, counts in race["precincts"].items())
        contests.append(race)
    print("%s: %d precincts, %d races, %d ballots" % (name, len(turnout), len(contests), county_ballots),
          file=sys.stderr)
    return {"county": tag, "name": name, "site": n,
            "source": "%s/turnouts/county/%d" % (BASE, n),
            "publisher": "%s County Clerk" % name,
            "ballots": county_ballots, "turnout": turnout, "contests": contests}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--only", help="comma-separated county tags (default: all six)")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    read = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    counties = [read_county(*c) for c in COUNTIES if not only or c[0] in only]
    with open(args.out, "w") as fh:
        json.dump({"read": read, "host": BASE, "counties": counties}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
