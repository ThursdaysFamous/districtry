#!/usr/bin/env python3
"""
Stage 1 of the Richland County Board roster pipeline: scrape the county's own
board page into raw JSON for build_richland_county_board.py, and RE-READ the
county's own GIS layer inventory in the same run.

TWO SOURCES, TWO JOBS. The people come from richlandcounty.illinois.gov's
County Board page, which publishes each member as a card carrying a name, a
title line ("County Board - District 3", or "Chairman - District 6") and a
county e-mail address. The GEOMETRY's provenance comes from
richlandil.wthgis.com, the county's own GIS, whose "County Board Districtrs"
and "Voter Precincts" layers are what the shipped boundaries were composed from
(build_richland_boundaries.py) — so re-reading their feature lists weekly is
this county's redistricting and re-precincting tripwire. Nothing on the board
page would ever show either moving.

THE TRAP THIS COUNTY SETS, and the reason the parser is scoped rather than
greedy: the same page carries a COMMITTEES section above the roster, and every
committee prints "Chair:" and "Members:" lines. Those name board members
(fine), but they also name people who are not on the board at all — the 708
Mental Health Committee lists five community members, the ETSB lists seven
people of whom two are board members. A parser that read names off the whole
page would ship a fourteen-member board for a seven-seat county. The roster
lives inside <div class="row boardMembers">, and this reads only that block —
the same lesson Alexander's stale nav menu taught from the other direction:
read the county's MAINTAINED list, not every name on the page.

WHAT THE BOARD PAGE PUBLISHES, and what it does not: name, district, a county
e-mail per member, and the Chairman's title. No party, no term, no phone, and
no home address — so none of those ship.

Usage:
    python3 scripts/richland_county_board_scraper.py [-o raw.json]
"""

import argparse
import html
import json
import re
import sys

import requests
from scraper_common import require_robots_once, make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://richlandcounty.illinois.gov/county-board/"
GIS_URL = "https://richlandil.wthgis.com/"
GIS_INDEX = ("https://richlandil.wthgis.com/tgis/Index.ashx"
             "?action=layerIndex&dsid=%d&name=x")
GIS_FEATURE = ("https://richlandil.wthgis.com/tgis/getftr.aspx"
               "?D=%d&F=%d&Z=0")
GIS_DISTRICTS_DSID = 10698
GIS_PRECINCTS_DSID = 1283
EXPECTED_DISTRICTS = 7
EXPECTED_PRECINCTS = 21

TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

# The roster block, and nothing above it. See the docstring. The block runs from
# its own marker to the page's contact sidebar, which is the next thing on the
# page; if that sidebar is ever dropped the block simply runs to the end of the
# document, which is still BELOW the committee lists and so still excludes them.
ROSTER_START_RE = re.compile(r'<div class="row boardMembers">', re.I)
ROSTER_END_RE = re.compile(r'class="department-sidebar', re.I)
CARD_RE = re.compile(r'<div class="card">(.*?)</div>\s*</div>', re.S)
NAME_RE = re.compile(r"<p>(.*?)</p>", re.S)
TITLE_RE = re.compile(r'<p class="title">(.*?)</p>', re.S)
DISTRICT_RE = re.compile(r"District\s*#?\s*(\d+)", re.I)
CHAIR_RE = re.compile(r"\bchair(?:man|person|woman)?\b", re.I)
MAILTO_RE = re.compile(r'href="mailto:([^"?]+)"', re.I)
# THE FEATURE NAMES ARE READ ONE AT A TIME, ON PURPOSE. The viewer's bulk
# endpoint (index.ashx?action=getFtrs) returns the whole layer as one
# delimiter-free run of "<listIndex><featureId><name>" — so "…Olney Precinct
# 11020Olney Precinct 10…" is "Olney Precinct 1", then list index 10, feature
# 20, "Olney Precinct 10". Any regex over that blob parses cleanly and reads
# wrongly: the first draft of this scraper returned "Olney Precinct 1" three
# times and lost 10 and 11 entirely. The per-feature endpoint labels its value,
# so it cannot be misread, and 28 requests once a week is a cheap price for a
# reading that is right.
GIS_COUNT_RE = re.compile(r"<small>\s*(\d+)\s+records?\s*</small>", re.I)
GIS_VALUE_RE = re.compile(r"class=ftrval>(.*?)</td>", re.S)


fail = make_fail("richland-board-scraper")


def get(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-richland-county-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scrape_members(page):
    start = ROSTER_START_RE.search(page)
    if not start:
        fail("the county's board page no longer carries a "
             '<div class="row boardMembers"> block — refusing to read names off '
             "the whole page, which also lists committee members who do not sit "
             "on the board")
    tail = page[start.end():]
    end = ROSTER_END_RE.search(tail)
    block = tail[:end.start()] if end else tail
    records = []
    for card in CARD_RE.finditer(block):
        body = card.group(1)
        title_hit = TITLE_RE.search(body)
        if not title_hit:
            continue
        title = clean(title_hit.group(1))
        district_hit = DISTRICT_RE.search(title)
        if not district_hit:
            continue
        names = [clean(n) for n in NAME_RE.findall(body)]
        names = [n for n in names if n and n != title]
        if not names:
            continue
        entry = {"name": names[0], "district": district_hit.group(1), "title": title}
        if CHAIR_RE.search(title):
            entry["role"] = "Chairman"
        mail = MAILTO_RE.search(body)
        if mail:
            entry["email"] = html.unescape(mail.group(1)).strip()
        records.append(entry)
    records.sort(key=lambda r: (int(r["district"]), r["name"]))
    return records


def gis_layer(dsid, label):
    """{count, features} for one of the county's own GIS layers."""
    hit = GIS_COUNT_RE.search(get(GIS_INDEX % dsid))
    if not hit:
        fail("the county's GIS no longer reports a record count for its %s layer "
             "(dsid %d) — the redistricting tripwire cannot run" % (label, dsid))
    count = int(hit.group(1))
    names = []
    # Feature ids are dense from 0 but not necessarily in list order, so this
    # walks a little past the count and stops once every record is named.
    for fid in range(count + 5):
        if len(names) >= count:
            break
        value = GIS_VALUE_RE.search(get(GIS_FEATURE % (dsid, fid)))
        if value:
            names.append(clean(value.group(1)))
    if len(names) != count:
        fail("the county's GIS reports %d %s features and named %d of them"
             % (count, label, len(names)))
    return {"dsid": dsid, "count": count, "features": sorted(names)}


def scrape_gis():
    return {"url": GIS_URL,
            "districtLayer": gis_layer(GIS_DISTRICTS_DSID, "board-district"),
            "precinctLayer": gis_layer(GIS_PRECINCTS_DSID, "voter-precinct")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    members = scrape_members(get(BOARD_URL))
    gis = scrape_gis()
    payload = {"source": BOARD_URL, "gis": gis, "records": members}
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("richland-board-scraper: %d member(s); county GIS reports %d board "
              "district(s) and %d precinct(s) -> %s"
              % (len(members), gis["districtLayer"]["count"],
                 gis["precinctLayer"]["count"], args.output), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
