#!/usr/bin/env python3
"""
Read one election's precinct-by-precinct results from the Kane County Clerk's
results site, and write them as JSON for build_il_county_election_results.py.

THE SOURCE. https://electionresults.kanecountyil.gov/<election date>/ has a
Contests page (the county's own totals for every contest) and a Precincts page
listing every precinct, each linking its own page
(`Precincts/AU0001/`) with that precinct's registered voters, ballots cast and
one table per contest on its ballot. For the 3 November 2026 general election
that is 292 precinct pages, read here one by one, one second apart, so a read
takes about five minutes. robots.txt at that host is read first with this
project's own token, which the site served on 2026-11-06.

WHAT THESE NUMBERS ARE. Unofficial until the county canvass; every page says
"Unofficial Results" and when it was current. The builder stamps the file with
that time and `certified: false`.

THE ROWS ARE CHECKED, NOT TRUSTED: every precinct on the list must have a page
whose heading names it; every contest's precinct counts must add up, choice by
choice, to the Contests page's totals; and the precinct ballots must add up to
the county's ballots cast. Any failure fails the run.

Usage:
    python3 scripts/il_kane_election_results_scraper.py --election 2026-11-03 -o /tmp/kane_raw.json
"""

import argparse
import datetime
import html
import json
import re
import sys
import time
import urllib.request

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,
                            require_robots_once)

fail = make_fail("il-kane-election-results-scraper")

BASE = "https://electionresults.kanecountyil.gov/"
PACE_SECONDS = 1.0

PRECINCT_LINK_RE = re.compile(r'href="([A-Z]{2}\d{4})/"')
CONTEST_RE = re.compile(r'<div class="c"[^>]*\bc="(\d+)"[^>]*>(.*?)</table>', re.S)
H2_RE = re.compile(r"<h2>(.*?)</h2>", re.S)
ROW_RE = re.compile(r'<tr>\s*<td class="b">(.*?)</td>\s*<td>([\d,]+)</td>', re.S)
REG_RE = re.compile(r"Registered Voters:\s*<b>([\d,]+)</b>")
CAST_RE = re.compile(r"Ballots Cast:\s*<b>([\d,]+)</b>")
AS_OF_RE = re.compile(r"Current as of ([^<]+)</i>")

_last = [0.0]


def get(url):
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    wait = PACE_SECONDS - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers=dict(UA_HEADERS_ROSTER_BOT))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", "replace")
            break
        except Exception as e:  # one slow page is retried, a dead site fails the run
            if attempt == 2:
                fail("%s: %s" % (url, e))
            time.sleep(5)
    _last[0] = time.time()
    return body


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def num(text):
    return int(text.replace(",", ""))


def contests_of(page, where):
    out = []
    for cid, block in CONTEST_RE.findall(page):
        h2 = H2_RE.search(block)
        if not h2:
            fail("%s: contest %s has no heading" % (where, cid))
        rows = [(clean(n), num(v)) for n, v in ROW_RE.findall(block)]
        if not rows:
            fail("%s: contest %s (%s) has no rows" % (where, cid, clean(h2.group(1))))
        out.append((cid, clean(h2.group(1)), rows))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--election", required=True, help="the election's date, as the site's paths write it")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    root = BASE + args.election + "/"

    summary = get(root + "Contests/")
    as_of = AS_OF_RE.search(summary)
    county_cast = num(CAST_RE.search(summary).group(1))
    totals = {}
    names = {}
    order = []
    for cid, name, rows in contests_of(summary, "Contests page"):
        totals[cid] = dict(rows)
        names[cid] = name
        order.append(cid)
    if len(order) < 20:
        fail("the Contests page lists %d contests" % len(order))

    listing = get(root + "Precincts/")
    precincts = sorted(set(PRECINCT_LINK_RE.findall(listing)))
    if len(precincts) < 250:
        fail("the Precincts page lists %d precincts" % len(precincts))

    turnout = {}
    contests = dict((cid, {"raceNo": cid, "name": names[cid], "choices": [r for r in totals[cid]],
                           "precincts": {}}) for cid in order)
    for i, p in enumerate(precincts):
        page = get(root + "Precincts/" + p + "/")
        if ("for Precinct " + p) not in page:
            fail("precinct %s: the page does not name it" % p)
        turnout[p] = [num(REG_RE.search(page).group(1)), num(CAST_RE.search(page).group(1))]
        for cid, name, rows in contests_of(page, "precinct " + p):
            if cid not in contests:
                fail("precinct %s: contest %s (%s) is not on the Contests page" % (p, cid, name))
            got = dict(rows)
            extra = [n for n in got if n not in totals[cid]]
            if extra:
                fail("precinct %s, %s: choices %r are not on the Contests page" % (p, name, extra))
            contests[cid]["precincts"][p] = [got.get(n, 0) for n in contests[cid]["choices"]]
        if (i + 1) % 50 == 0:
            print("read %d of %d precincts" % (i + 1, len(precincts)), file=sys.stderr)

    if sum(v[1] for v in turnout.values()) != county_cast:
        fail("precinct ballots add to %d, the Contests page says %d"
             % (sum(v[1] for v in turnout.values()), county_cast))
    out = []
    for cid in order:
        c = contests[cid]
        for n, choice in enumerate(c["choices"]):
            got = sum(v[n] for v in c["precincts"].values())
            if got != totals[cid][choice]:
                fail("%s, %s: precincts add to %d, the Contests page says %d"
                     % (c["name"], choice, got, totals[cid][choice]))
        if not c["precincts"]:
            fail("%s is on no precinct's page" % c["name"])
        out.append(c)

    read = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {"read": read, "currentAsOf": as_of.group(1).strip() if as_of else None,
           "counties": [{"county": "kane", "name": "Kane", "source": root + "Contests/",
                         "publisher": "Kane County Clerk", "ballots": county_cast,
                         "turnout": turnout, "contests": out}]}
    with open(args.out, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("Kane: %d precincts, %d contests, %d ballots" % (len(turnout), len(out), county_cast), file=sys.stderr)


if __name__ == "__main__":
    main()
