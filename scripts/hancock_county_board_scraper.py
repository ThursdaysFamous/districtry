#!/usr/bin/env python3
"""
Scrape Hancock County's County Board roster into intermediate JSON.

Hancock publishes its fifteen members as five plain WordPress columns, one per
district, each an <h2> naming the district IN WORDS followed by a <ul> of
members with a party letter:

    <h2>District One</h2>
    <ul><li>Joe Boyles (R)</li><li>Wayne Bollin (R)</li>
        <li>Michelle Merritt (R)</li></ul>

TWO THINGS THIS PARSER DOES NOT DO, both deliberate.

It does NOT read the page's <meta name="description">, which repeats the first
district's members verbatim. Taking the first "District One" in the document
finds that meta tag, not the body, and a parser anchored there would ship three
members and call it a board. The body is found by scanning for the LAST
occurrence.

It does NOT assume the districts sit in five identical columns. District Four's
block opens with a nested panel-grid left over from an older page builder, so
the members are gathered between one <h2> and the next rather than by walking a
column structure.

The page carries a party letter per member and nothing else — no e-mail, no
phone, no term. That is what the county publishes, so that is what ships.

Usage:
    python3 scripts/hancock_county_board_scraper.py [output.json]
"""

import os
import html as html_mod
import json
import re
import sys
import time

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    make_fail,
    UA_ROSTER_BOT,
    output_path,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import require_robots_once  # noqa: E402  (shared machinery)

SOURCE_URL = "https://hancockcounty-il.gov/county-board-members/"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

MAX_PER_DISTRICT = 6   # Hancock seats 3; a parse above this is a bug, not a board
WORD_TO_NUM = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5"}
HEADING_RE = re.compile(r"(?is)<h2[^>]*>\s*District\s+([A-Za-z]+)\s*</h2>")
ITEM_RE = re.compile(r"(?is)<li[^>]*>(.*?)</li>")
# "Joe Boyles (R)" -> name, party. The party letter is optional so a member
# listed without one is still read rather than silently dropped.
MEMBER_RE = re.compile(r"^(?P<name>.+?)\s*(?:\((?P<party>[A-Za-z]{1,3})\)\s*)?$")
TAG_RE = re.compile(r"<[^>]+>")


def clean(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


fail = make_fail("hancock-board-scraper")


def fetch(url):
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                                label="il-hancock-county-board-scraper")
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.text
            last = "HTTP %d" % r.status_code
            if 400 <= r.status_code < 500 and r.status_code not in (429,):
                break
        except requests.RequestException as exc:
            last = str(exc)
        time.sleep(2 ** attempt)
    fail("could not fetch %s (%s)" % (url, last))


def parse(page):
    # The <meta name="description"> repeats District One's members, so anchor on
    # the LAST heading run rather than the first — see the module docstring.
    heads = list(HEADING_RE.finditer(page))
    if not heads:
        fail("no <h2>District …</h2> headings on %s" % SOURCE_URL)
    body_start = heads[0].start()
    for h in heads:
        if h.group(1).upper() in WORD_TO_NUM and page.count(h.group(0)) > 1:
            body_start = page.rfind(h.group(0))
            break
    heads = [h for h in HEADING_RE.finditer(page) if h.start() >= body_start]

    roster = {}
    for idx, h in enumerate(heads):
        word = h.group(1).upper()
        if word not in WORD_TO_NUM:
            continue
        dnum = WORD_TO_NUM[word]
        end = heads[idx + 1].start() if idx + 1 < len(heads) else len(page)
        # Take only the FIRST non-empty <ul> after the heading, not everything
        # up to the next one. The last district has no following <h2>, so an
        # unbounded region runs to the end of the document and swallows the
        # site's footer navigation as members — District Five parsed 35 people
        # that way, most of them menu links. Each district is exactly one
        # <h2> + one <ul>, so bounding on that is both correct and tighter.
        region = page[h.end():end]
        block = None
        for cand in re.finditer(r"(?is)<ul[^>]*>(.*?)</ul>", region):
            if ITEM_RE.search(cand.group(1)) and clean(cand.group(1)):
                block = cand.group(1)
                break
        if block is None:
            continue
        members = []
        for item in ITEM_RE.finditer(block):
            text = clean(item.group(1))
            if not text:
                continue
            m = MEMBER_RE.match(text)
            name = clean(m.group("name"))
            if not name:
                continue
            entry = {"name": name}
            if m.group("party"):
                entry["party"] = m.group("party").upper()
            if not any(x["name"] == name for x in members):
                members.append(entry)
        if len(members) > MAX_PER_DISTRICT:
            fail("district %s parsed %d members — the page shape changed and "
                 "this is almost certainly navigation, not a board"
                 % (dnum, len(members)))
        if members:
            roster.setdefault(dnum, []).extend(members)
    return roster


def main():
    out_path = output_path("hancock-board-raw.json")
    roster = parse(fetch(SOURCE_URL))
    total = sum(len(v) for v in roster.values())
    payload = {"sourceUrl": SOURCE_URL, "districts": roster}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
    print("hancock-board-scraper: %d districts, %d members -> %s"
          % (len(roster), total, out_path))


if __name__ == "__main__":
    main()
