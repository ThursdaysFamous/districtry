#!/usr/bin/env python3
"""
Scrape LaSalle County's own board directory into raw roster records.

Stage 1 of the two-stage pipeline (scripts/build_lasalle_board_roster.py is
stage 2), mirroring the DuPage pair. REWRITTEN 2026-08-17: the county migrated
off CivicPlus — Directory.aspx?DID=39 now 302-redirects to the new platform's
/m/directory/department?did=39, which is still plain server-rendered HTML that
answers a plain requests client. Each member is a <li class="list-group-item">
block carrying the member's name link (/m/directory/employee?eid=n), a title
div ("District N, Board Member" — one row says "Board Members", so the plural
is accepted — or "Chairman of the Board"), a plain mailto: with the
district-office address (district<N>@lasallecountyil.gov — the old CivicPlus
spam-wrapper is gone), and a per-member phone. NAMES ARE NOW DISPLAY-ORDER
("Stephen Aubry", not "Aubry, Stephen"), so the old comma-flip is gone too —
it would mangle "William J. Brown, Jr.".

WHY THIS SCRAPER EXISTS — the county's board-boundary GIS is the SUPERSEDED
2011-2021 map, frozen 2015-08-25, and its officeholder columns disagree with
this directory on 18 of 29 seats (the 2026-07-31 validation-pass finding). The
directory is the county's roster of record for the 2022-2031 board; the
boundary comes separately from scripts/build_lasalle_board_districts.py.

The Board Chairman is elected COUNTYWIDE (verified: the Nov 2024 general
canvass carries a county-wide COUNTY BOARD CHAIRMAN contest) and is emitted
with district=null, role="Chair". A "(Vice Chairman)" tag beside a member's
name is carried as role="Vice Chair" on that member's own district row.

Usage:
    python3 lasalle_county_board_scraper.py [output.json]   # default: stdout
"""

import json
import re
import time
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_COMPACT,
    require_robots_once,
)

BASE = "https://lasallecountyil.gov"
LIST_URL = BASE + "/m/directory/department?did=39"
UA = {"User-Agent": UA_ROSTER_COMPACT}

BLOCK_SPLIT = '<li class="list-group-item'
NAME_RE = re.compile(
    r'href="(?P<path>/m/directory/employee\?eid=(?P<eid>\d+))"[^>]*>\s*(?P<name>[^<]+?)\s*</a>')
TITLE_RE = re.compile(r'<div class="d-sm-block d-none">\s*(?P<title>[^<]+?)\s*</div>')
TAG_RE = re.compile(r'\((?P<tag>[^)]*(?:Vice|Chair)[^)]*)\)', re.I)
EMAIL_RE = re.compile(r'href="mailto:(?P<email>[^"?]+)"')
PHONE_RE = re.compile(r'(\d{3})[.\- ](\d{3})[.\- ](\d{4})')
DISTRICT_RE = re.compile(r'District\s+(\d+)', re.I)


FETCH_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 4


def fetch(url):
    """GET with a bounded retry.

    THERE WAS NO RETRY HERE, and a single bad response failed the whole weekly
    run for sixteen days (2026-08-02 to 08-18) while the page itself was fine:
    re-running the same scraper by hand on 08-18 parsed all 30 rows on the first
    try. The county's site answers this project differently from different
    callers — the same posture measured on Brown, Pike and Greene in
    il_county_commissioners_scraper.py, whose fetch() carries this retry and
    documents why. One flaky afternoon must not freeze a roster.
    """
    last = None
    for attempt in range(FETCH_ATTEMPTS):
        try:
            require_robots_once(url, UA["User-Agent"], headers=UA,
                                label="il-lasalle-county-board-scraper")
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            return r.text
        except requests.RequestException as exc:
            last = exc
            if attempt + 1 < FETCH_ATTEMPTS:
                time.sleep(RETRY_PAUSE_SECONDS)
    raise SystemExit("lasalle-board-scraper: FAIL — %s unreachable after %d "
                     "attempts (%s)" % (url, FETCH_ATTEMPTS, last))


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def main():
    html = fetch(LIST_URL)
    records = []
    for block in html.split(BLOCK_SPLIT)[1:]:
        nm = NAME_RE.search(block)
        tm = TITLE_RE.search(block)
        if not nm or not tm:
            continue
        name = clean(nm.group("name"))
        title = clean(tm.group("title"))
        district = None
        role = "Member"
        if "chairman of the board" in title.lower():
            role = "Chair"
        else:
            dm = DISTRICT_RE.search(title)
            if not dm or "board member" not in title.lower():
                continue  # a staff row that merely mentions the board
            district = int(dm.group(1))
        tag_m = TAG_RE.search(block)
        tag = clean(tag_m.group("tag")) if tag_m else ""
        if role == "Member" and "vice" in tag.lower():
            role = "Vice Chair"
        email = None
        em = EMAIL_RE.search(block)
        if em:
            email = em.group("email").strip()
        phone = None
        pm = PHONE_RE.search(re.sub(r"<[^>]+>", " ", block))
        if pm:
            phone = "%s-%s-%s" % pm.groups()
        records.append({
            "name": name,
            "district": district,
            "role": role,
            "phone": phone,
            "email": email,
            "url": BASE + nm.group("path"),
        })

    if not records:
        # SAY WHAT ARRIVED, DO NOT GUESS WHY. This message used to read
        # "(markup change?)" and that guess cost real time on 2026-08-18: the
        # markup had not changed at all, and the guess sent the reader to the
        # parser instead of to the response. Status, size and title are what
        # distinguish a redesigned page from a challenge screen or an error
        # page, and they cost nothing to print.
        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
        print("lasalle-board-scraper: FAIL — zero rows parsed from %s. The "
              "response was %d bytes, titled %r. A full page with a new title "
              "means the markup moved; a short one, or a title naming a "
              "challenge or an error, means this caller was refused rather "
              "than the page changed."
              % (LIST_URL, len(html),
                 clean(title.group(1))[:80] if title else "(no <title>)"),
              file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": LIST_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("lasalle-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
