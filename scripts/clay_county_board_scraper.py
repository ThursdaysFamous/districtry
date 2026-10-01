#!/usr/bin/env python3
"""
Stage 1 of the Clay County Board roster pipeline: scrape the county's own two
board pages into raw JSON for build_clay_county_board.py.

TWO PAGES, TWO JOBS. claycounty.illinois.gov/county-board/members/ is the
county's maintained member list — an Elementor team widget per member (the
Alexander pattern: the widget, not any hand-built nav, is the maintained
list), each carrying a name, a position line that states the district
("County Board - District K", or "County Board Chair - District C" for the
one member whose position also carries the office), and a phone. The phone is
printed TWICE per card (an image-overlay copy and a content copy) and this
scraper requires the two to agree rather than picking one.

claycounty.illinois.gov/county-board/ carries the other half: the Chairman
and Vice Chairman by name ("Board Chairman – Joe Goodman", "Vice Chairman –
Barbara McGrew"), and the Districts section stating the county's whole
composition letter by letter — the same composition
scripts/build_clay_boundaries.py was built from. Re-scraping that section
every week IS this county's redistricting tripwire; the builder compares it
against the shipped composition and fails on any disagreement (the Wayne
shape: one county source publishes both the people and the lines, so one
weekly run re-verifies both).

A NAME TRAP TO KNOW ABOUT, handled in the builder: the board page writes the
Vice Chairman as "Barbara McGrew" while the members page — the roster source —
prints her card as "Barb Mcgrew". The role is joined by surname and the join
is printed on every run; the shipped name is the members page's, exactly as
the county prints it there.

WHAT THE PAGES PUBLISH, and what they do not: a name, a district letter, a
phone, and the two officer roles. No e-mail, no party, no term — none is
invented.

Usage:
    python3 scripts/clay_county_board_scraper.py [-o raw.json]
"""

import argparse
import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    make_fail, require_robots_once, UA_ROSTER_BOT,
)

MEMBERS_URL = "https://claycounty.illinois.gov/county-board/members/"
BOARD_URL = "https://claycounty.illinois.gov/county-board/"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

TEAM_ITEM_RE = re.compile(r'class="eael-team-item\b', re.I)
NAME_RE = re.compile(r'<h2 class="eael-team-member-name">(.*?)</h2>', re.S)
POSITION_RE = re.compile(r'<h3 class="eael-team-member-position">(.*?)</h3>', re.S)
PHONE_RE = re.compile(r'<b>\s*Phone:\s*</b>\s*([0-9().\-\s]+?)\s*<', re.I)
POSITION_PARSE_RE = re.compile(r'^County Board(?P<role>\s+Chair)?\s*-\s*District\s+(?P<district>[A-N])$',
                               re.I)

CHAIR_RE = re.compile(r'Board Chairman\s*</strong>\s*</em>\s*&#8211;\s*([^<]+)<', re.I)
VICE_RE = re.compile(r'Vice Chairman\s*</strong>\s*</em>\s*&#8211;\s*([^<]+)<', re.I)
DISTRICT_LINE_RE = re.compile(
    r'<p><strong>District\s+([A-N])\s*&#8211;\s*</strong>(.*?)</p>', re.I | re.S)


fail = make_fail("clay-board-scraper")


def get(url):
    # THE COUNTY'S RULES ARE READ BEFORE ITS FIRST PAGE, with the identity this
    # fetch sends. claycounty.illinois.gov had been recorded as answering every
    # client with a managed challenge; re-measured from a GitHub runner on
    # 2026-10-01, the vantage the weekly job crawls from, it serves a 181-byte
    # policy whose binding group matches none of the paths read here, on all
    # three reads of a deliberate re-measurement fifteen seconds apart.
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="clay-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scrape_members(page):
    starts = [m.start() for m in TEAM_ITEM_RE.finditer(page)]
    members = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(page)
        block = page[start:end]
        name_m = NAME_RE.search(block)
        pos_m = POSITION_RE.search(block)
        if not name_m or not pos_m:
            continue
        name = clean(name_m.group(1))
        position = clean(pos_m.group(1))
        parsed = POSITION_PARSE_RE.match(position)
        if not parsed:
            fail("member %r carries position %r, which does not parse as "
                 "'County Board[ Chair] - District A-N' — the page changed shape"
                 % (name, position))
        phones = [re.sub(r"\s+", " ", p).strip() for p in PHONE_RE.findall(block)]
        if not phones:
            fail("member %r has no phone on their card — the county has always "
                 "printed one; the page changed shape" % name)
        if len(set(phones)) != 1:
            fail("member %r carries two different phone numbers (%s) — the "
                 "card's two copies disagree" % (name, ", ".join(sorted(set(phones)))))
        members.append({
            "name": name,
            "district": parsed.group("district").upper(),
            "chairOnCard": bool(parsed.group("role")),
            "phone": phones[0],
        })
    return members


def scrape_board(page):
    chair_m = CHAIR_RE.search(page)
    vice_m = VICE_RE.search(page)
    if not chair_m or not vice_m:
        fail("the county-board page no longer names a Board Chairman and Vice "
             "Chairman in the Chairman tab — the page changed shape")
    districts = []
    for m in DISTRICT_LINE_RE.finditer(page):
        names = clean(m.group(2))
        precincts = [p.strip() for p in re.split(r"\s*&\s*", names) if p.strip()]
        districts.append({"district": m.group(1).upper(), "precincts": precincts})
    if not districts:
        fail("the county-board page's Districts section parsed to nothing — "
             "the page changed shape")
    return {
        "chair": clean(chair_m.group(1)),
        "viceChair": clean(vice_m.group(1)),
        "districts": districts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    parser.add_argument("-o", "--output", default="clay_board_raw.json")
    args = parser.parse_args()

    members = scrape_members(get(MEMBERS_URL))
    board = scrape_board(get(BOARD_URL))

    payload = {
        "membersUrl": MEMBERS_URL,
        "boardUrl": BOARD_URL,
        "members": members,
        "chair": board["chair"],
        "viceChair": board["viceChair"],
        "districts": board["districts"],
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print("clay-board-scraper: %d member cards, chair %r, vice chair %r, %d "
          "district lines -> %s"
          % (len(members), board["chair"], board["viceChair"],
             len(board["districts"]), args.output))


if __name__ == "__main__":
    main()
