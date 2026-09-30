#!/usr/bin/env python3
"""
Scrape the Rock Island County Board roster into the intermediate JSON
build_rock_island_county_board_roster.py consumes.

SOURCE. The county's /263/County-Board page carries a CivicPlus staff-directory
widget, one `<li class="widgetItem h-card">` per member, with microformat
classes: `p-name` holds "Name (D)", `p-job-title` holds "Member - District 7"
(sometimes with a role suffix, e.g. "Member - District 5 - Vice-Chairman"), and
`p-note` holds the term. The markup is machine-readable by design, so this is a
class parse rather than a text-shape guess.

THE CHAIRMAN IS NOT IN THE WIDGET. He is named in a prose block above it, with
his own phone and e-mail — and he ALSO appears in the widget as the member for
his district. Rock Island elects its chair from among the 19 district members
(the same shape as DeKalb and Carroll), so the chair is tagged on his district
row rather than shipped as a separate countywide seat, and the prose block is
read only to learn which member holds the gavel.

WHY THE BOUNDARY IS NOT SCRAPED HERE. The county draws its 19 single-member
districts on its own GIS (services9.arcgis.com/6FnscPPlUa9DXXOk, Other_Layers
layer 4), so index.html loads the geometry live and this file supplies only the
people. The GIS carries a NAME column and populates it on 0 of 19 — a schema is
not data, which is why this scraper exists at all.

FETCH POSTURE: open. Plain `requests` with a browser UA gets the page.

Usage:
    python3 rock_island_county_board_scraper.py --out rock_island_board_raw.json
"""

import argparse
import collections
import datetime
import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_WIN_126,
    require_robots_once,
)

SOURCE_URL = "https://www.rockislandcountyil.gov/263/County-Board"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 90

ITEM_RE = re.compile(r'<li class="widgetItem h-card">(.*?)</li>', re.S | re.I)
NAME_RE = re.compile(r'class="[^"]*p-name[^"]*"[^>]*>(.*?)</h4>', re.S | re.I)
TITLE_RE = re.compile(r'class="[^"]*p-job-title[^"]*"[^>]*>(.*?)</div>', re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

PARTY_RE = re.compile(r"\(([DR])\)\s*$")
DISTRICT_RE = re.compile(r"District\s+(\d+)", re.I)
# "Member - District 5 - Vice-Chairman" — the trailing segment, when present and
# not the district itself, is the member's board role.
ROLE_RE = re.compile(r"District\s+\d+\s*[-–]\s*(.+?)\s*$", re.I)
TERM_RE = re.compile(r"Current Term:\s*(\d{4})\s*[-–]\s*(\d{4})", re.I)
# The prose block above the widget: "County Board Chairman" then the name.
CHAIR_RE = re.compile(r"County Board Chairman\s*</strong>\s*<br\s*/?>\s*(.*?)\s*<", re.S | re.I)

PARTY_NAMES = {"D": "Democrat", "R": "Republican"}

MIN_MEMBERS = 18
MIN_DISTRICTS = 18


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip()
    return value or None


def parse(page, warnings):
    chair_match = CHAIR_RE.search(page)
    chair_name = None
    if chair_match:
        chair_name = clean(PARTY_RE.sub("", text_of(chair_match.group(1))))
    else:
        warnings.append("no 'County Board Chairman' prose block — the chair will "
                        "ship untagged rather than guessed")

    records, seen = [], set()
    for block in ITEM_RE.findall(page):
        name_match = NAME_RE.search(block)
        title_match = TITLE_RE.search(block)
        if not name_match or not title_match:
            continue
        raw_name = text_of(name_match.group(1))
        title = text_of(title_match.group(1))
        district_match = DISTRICT_RE.search(title)
        if not district_match:
            continue  # committee chairs and staff rows carry no district
        party_match = PARTY_RE.search(raw_name)
        name = clean(PARTY_RE.sub("", raw_name))
        if not name:
            continue
        district = str(int(district_match.group(1)))
        # The page lists the chairman twice — once in the prose block and once as
        # his district's member. Deduped on (district, name) so he is not counted
        # as two seats.
        key = (district, name.lower())
        if key in seen:
            continue
        seen.add(key)
        role = None
        role_match = ROLE_RE.search(title)
        if role_match:
            role = clean(role_match.group(1))
        if chair_name and name.lower() == chair_name.lower():
            role = "Board Chairman"
        term = TERM_RE.search(block)
        records.append({
            "district": district,
            "name": name,
            "party": PARTY_NAMES.get(party_match.group(1)) if party_match else None,
            "role": role,
            "term_start": term.group(1) if term else None,
            "term_end": term.group(2) if term else None,
        })
    return records, chair_name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--html", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    warnings = []
    try:
        if args.html:
            page = open(args.html, encoding="utf-8", errors="replace").read()
        else:
            require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                                label="il-rock-island-county-board-scraper")
            resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            page = resp.text
        records, chair_name = parse(page, warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    districts = sorted({r["district"] for r in records}, key=int)
    dupes = [d for d, n in collections.Counter(r["district"] for r in records).items() if n > 1]
    chairs = [r["name"] for r in records if r["role"] == "Board Chairman"]
    problems = []
    if len(records) < MIN_MEMBERS:
        problems.append("%d members < floor %d" % (len(records), MIN_MEMBERS))
    if len(districts) < MIN_DISTRICTS:
        problems.append("%d districts < floor %d" % (len(districts), MIN_DISTRICTS))
    # Every Rock Island district elects exactly one member (the GIS says MEMBERS=1
    # on all 19), so two names against one district means the dedupe missed and a
    # card would list a seat-holder who does not hold that seat.
    if dupes:
        problems.append("districts with more than one member: %s" % ", ".join(sorted(dupes, key=int)))
    if len(chairs) > 1:
        problems.append("%d members tagged Board Chairman" % len(chairs))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for record in records:
        record["source_url"] = SOURCE_URL
        record["scraped_at"] = scraped_at
    payload = {
        "county": "Rock Island",
        "source_url": SOURCE_URL,
        "scraped_at": scraped_at,
        "chair": chair_name,
        "members": records,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d members across %d districts, %d with party, chair %s -> %s"
          % (len(records), len(districts), sum(1 for r in records if r["party"]),
             chairs[0] if chairs else "unresolved", args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
