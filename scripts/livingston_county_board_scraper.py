#!/usr/bin/env python3
"""
Stage 1 of the Livingston County Board roster pipeline: scrape the county's
board-members directory into raw JSON for build_livingston_county_board_roster.py.

The directory is a Revize "business_directory" listing — one block per member,
carrying the district as a category chip, the name and party in an <h2>, the
term expiry in a description span, and an e-mail as a mailto link. Everything
this parses comes out of that block; nothing is inferred from position on the
page.

TWO THINGS THE PAGE GETS WRONG THAT THIS MUST NOT PROPAGATE:

1. It lists an explicit "Vacancy" row. That is a real, useful fact about the
   board, but it is NOT a person — emitting it would put an officeholder named
   "Vacancy" on a card. Vacancies are counted and reported, never named.

2. Street addresses in the directory are RESIDENCES (one is an apartment
   number), not offices. They are deliberately not collected, the same call the
   McHenry roster made.

Also note, for anyone re-reading the county's prose: the board page states the
2002 reapportionment gave "eight member elected from each district", while the
live directory shows six seats per district. The directory is what ships. The
same page is where build_livingston_board_districts.py takes the district
composition from — that composition is separately corroborated 30-for-30 against
TIGER township names, which is exactly why it is trusted where the seat count
is not.

Usage:
    python3 livingston_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_X11_120,
    require_robots_once,
)

SOURCE_URL = "https://www.livingstoncountyil.gov/government/county_board_members.php"
# The county site 202s a bare client; a browser UA is enough (no challenge).
HEADERS = {
    "User-Agent": UA_CHROME_X11_120,
}
REQUEST_TIMEOUT = 60

BLOCK_SPLIT = re.compile(r'(?=<ul class="category-list">)')
DISTRICT_RE = re.compile(r"<li>\s*District\s*(\d+)\s*</li>", re.I)
NAME_RE = re.compile(r"<h2>(.*?)</h2>", re.S)
EMAIL_RE = re.compile(r'mailto:([^"?\s]+)"')
TERM_RE = re.compile(r"Term Expires:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})")
SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

# Party appears as a parenthesised abbreviation. Normalised to the single-letter
# badge the neighbouring counties' cards already show (Winnebago and Madison both
# publish "R"/"D"), so one card style does not change shape across a county line.
PARTY = {"rep": "R", "rep.": "R", "republican": "R",
         "dem": "D", "dem.": "D", "democrat": "D", "democratic": "D",
         "ind": "I", "ind.": "I", "independent": "I"}
ROLE_RE = re.compile(r"\b(Board Chair(?:man|person)?|Vice[- ]Chair(?:man|person)?)\b", re.I)
VACANT_RE = re.compile(r"^\s*vacan(?:t|cy)\s*$", re.I)


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def parse(page):
    page = SCRIPT_RE.sub("", page)
    records = []
    for block in BLOCK_SPLIT.split(page)[1:]:
        d = DISTRICT_RE.search(block)
        n = NAME_RE.search(block)
        if not (d and n):
            continue
        raw = text_of(n.group(1))
        rec = {"district": d.group(1), "raw_name": raw}

        role = ROLE_RE.search(raw)
        if role:
            label = role.group(1).strip()
            rec["role"] = "Board Chair" if label.lower().startswith("board") else "Vice Chair"
            raw = ROLE_RE.sub("", raw).strip()

        party = re.search(r"\(([^)]{1,12})\)", raw)
        if party:
            key = party.group(1).strip().lower()
            if key in PARTY:
                rec["party"] = PARTY[key]
            raw = re.sub(r"\([^)]{1,12}\)", "", raw)

        name = re.sub(r"\s+", " ", raw).strip(" ,-")
        if VACANT_RE.match(name):
            rec["vacant"] = True
            rec["name"] = None
        else:
            rec["name"] = name or None

        email = EMAIL_RE.search(block)
        if email:
            rec["email"] = html.unescape(email.group(1)).strip()
        term = TERM_RE.search(block)
        if term:
            rec["term_expires"] = term.group(1)
        records.append(rec)
    return records


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "livingston_county_board_raw.json"
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-livingston-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)
    if not records:
        print("livingston-scraper: FAIL — parsed 0 member blocks; the directory "
              "markup changed", file=sys.stderr)
        sys.exit(1)
    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    filled = [r for r in records if r.get("name")]
    print("livingston-scraper: wrote %s — %d blocks, %d named, %d vacant, %d e-mails"
          % (out_path, len(records), len(filled),
             sum(1 for r in records if r.get("vacant")),
             sum(1 for r in records if r.get("email"))))


if __name__ == "__main__":
    main()
