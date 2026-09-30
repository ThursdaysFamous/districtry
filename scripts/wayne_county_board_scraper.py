#!/usr/bin/env python3
"""
Stage 1 of the Wayne County Board roster pipeline: scrape the county's own
board page — waynecountyil.gov/wayne-county-board/ — into raw JSON for
build_wayne_county_board.py.

ONE PAGE PUBLISHES BOTH THE PEOPLE AND THE COMPOSITION build_wayne_boundaries.py
was dissolved from, in one text block per district: a "DISTRICT N:" heading, an
italic list of the precincts that make it up, and one line per member (a
Chairman or Vice Chairman gets a trailing ", <role>"). Re-scraping the precinct
list here every week IS this county's redistricting tripwire — the builder
compares it against the shipped composition and fails on any disagreement, the
same shape as Richland's GIS re-read, except this county publishes the
composition and the roster on the same page rather than on two systems.

THE ONE THING THIS PAGE CANNOT TRIP: District 7's list here names only Merriam
and Golden Gate. Fairfield 1 and Fairfield 2 are not on this page at all — they
are placed in District 7 by the county's certified 2024 General canvass, a
different source entirely (see build_wayne_boundaries.py). A page that stops
naming five precincts for six OTHER districts is caught; a change to Fairfield's
district would not be, because nothing here re-reads the canvass. That gap is
accepted and stated rather than closed by a weekly canvass re-fetch, which
would be a much heavier and slower-moving check for one county's one seat.

WHAT THE PAGE PUBLISHES, and what it does not: a name, an optional Chairman or
Vice Chairman role, per member. No e-mail, no phone, no party, no term —
nothing here invents any of them.

Usage:
    python3 scripts/wayne_county_board_scraper.py [-o raw.json]
"""

import argparse
import html
import json
import re
import sys

import requests
from scraper_common import require_robots_once, make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://waynecountyil.gov/wayne-county-board/"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

# The whole roster lives in one heading ("WAYNE COUNTY BOARD MEMBERS:") plus
# one text-editor widget carrying all seven district paragraphs — no
# committee section or other roster-shaped text sits nearby on this page, so
# the block is found by the heading and read to the next section boundary.
ROSTER_START_RE = re.compile(r"WAYNE COUNTY BOARD MEMBERS", re.I)
ROSTER_END_RE = re.compile(r'e-con-inner"', re.I)
DISTRICT_BLOCK_RE = re.compile(
    r"<strong>\s*DISTRICT\s*(\d+)\s*:\s*</strong>\s*(?:<br\s*/?>)?\s*"
    r"<em>(.*?)</em>\s*(?:<br\s*/?>)?\s*(.*?)</p>", re.I | re.S)
CHAIR_RE = re.compile(r"\bchair(?:man|person|woman)?\b", re.I)
VICE_CHAIR_RE = re.compile(r"\bvice[\s-]*chair", re.I)


fail = make_fail("wayne-board-scraper")


def get(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-wayne-county-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def split_precincts(text):
    """'Berry, Garden Hill, Keith, Orchard, Indian Prairie and Hickory Hill'
    -> ['Berry', 'Garden Hill', 'Keith', 'Orchard', 'Indian Prairie',
    'Hickory Hill']. The county writes a bare 'and' before the last item and
    no Oxford comma; this splits on both without assuming either."""
    text = clean(text)
    text = re.sub(r"\s+and\s+", ", ", text)
    return [p.strip() for p in text.split(",") if p.strip()]


def scrape_members(page):
    start = ROSTER_START_RE.search(page)
    if not start:
        fail("the county's board page no longer carries a 'WAYNE COUNTY BOARD "
             "MEMBERS' heading")
    tail = page[start.end():]
    end = ROSTER_END_RE.search(tail)
    block = tail[:end.start()] if end else tail
    districts = []
    for m in DISTRICT_BLOCK_RE.finditer(block):
        dnum = m.group(1)
        precincts = split_precincts(m.group(2))
        member_lines = [clean(x) for x in re.split(r"<br\s*/?>", m.group(3), flags=re.I)]
        member_lines = [x for x in member_lines if x]
        members = []
        for line in member_lines:
            role = None
            if VICE_CHAIR_RE.search(line):
                role = "Vice Chairman"
            elif CHAIR_RE.search(line):
                role = "Chairman"
            name = re.sub(r",?\s*(?:vice[\s-]*chair(?:man|person|woman)?|"
                          r"chair(?:man|person|woman)?)\s*$", "", line, flags=re.I).strip(" ,")
            if not name:
                continue
            entry = {"name": name}
            if role:
                entry["role"] = role
            members.append(entry)
        districts.append({"district": dnum, "precincts": precincts, "members": members})
    districts.sort(key=lambda d: int(d["district"]))
    return districts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    districts = scrape_members(get(BOARD_URL))
    payload = {"source": BOARD_URL, "districts": districts}
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        total = sum(len(d["members"]) for d in districts)
        print("wayne-board-scraper: %d district(s), %d member(s) -> %s"
              % (len(districts), total, args.output), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
