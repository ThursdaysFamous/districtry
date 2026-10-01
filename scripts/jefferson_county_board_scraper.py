#!/usr/bin/env python3
"""
Stage 1 of the Jefferson County Board roster pipeline: scrape the county's board
page into raw JSON for build_jefferson_board_roster.py.

PAGE SHAPE. A four-column table — DISTRICT, COUNTY BOARD MEMBER, PHONE, EMAIL —
one row per district, thirteen rows. Every cell's text is wrapped in font spans,
so the parse strips tags and reads the cell text rather than matching markup.

    <td>1</td>
    <td>Draege, Steve (Vice Chair)</td>
    <td>618-231-2100</td>
    <td><a href="mailto:district1@jeffersoncounty.illinois.gov">…</a></td>

THE PAGE IS AT THE SITE ROOT, NOT UNDER /government/. jeffersoncounty.illinois.gov
/government/county_board/index.php — the path the site's own navigation links —
returns 404; /county_board/index.php is the live page. Worth stating because the
404 page renders the full navigation and looks like a real page, so a scraper
pointed at the wrong one would parse zero rows and could be mistaken for a
layout change. The zero-row guard below is what catches that.

NAMES ARE PRINTED SURNAME-FIRST, every row: "Draege, Steve", "McDermott, Joey".
That is the third source in this fleet found doing it in one week — after
Stephenson's Dakota clerk and LaSalle's Village of Dana — so the inversion is
NOT reimplemented here. build_jefferson_board_roster.py imports uninvert_name()
from build_municipal_officials_roster.py, which carries the guard that makes it
safe (a suffix like "Roy Williams, Jr." must never become "Jr. Roy Williams").
Shared machinery, not forked, per the build_county_outline precedent.

ROLES RIDE THE NAME CELL in parentheses — "(Chairman)", "(Vice Chair)" — and are
split off before the name is read, because "Draege, Steve (Vice Chair)" is not a
name and inverting it whole would produce nonsense.

EVERY DISTRICT'S E-MAIL IS A ROLE ADDRESS (district1@…, district2@…), not a
personal one. That is what the county publishes and it is what ships: it reaches
whoever holds the seat, which is arguably better than a personal address for a
civic map, and it means a change of member does not silently strand mail.

Usage:
    python3 jefferson_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
    output_path,
)

SOURCE_URL = "https://jeffersoncounty.illinois.gov/county_board/index.php"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
EMAIL_RE = re.compile(r"mailto:\s*([^\"?\s>]+)", re.I)
PHONE_RE = re.compile(r"\d{3}-\d{3}-\d{4}")
TAG_RE = re.compile(r"<[^>]+>")
ROLE_RE = re.compile(r"\(([^)]*)\)")


def text_of(fragment):
    text = html.unescape(TAG_RE.sub(" ", fragment or ""))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def parse(page):
    page = SCRIPT_RE.sub(" ", page)
    records = []
    for row in ROW_RE.findall(page):
        raw_cells = CELL_RE.findall(row)
        cells = [text_of(c) for c in raw_cells]
        if len(cells) < 4:
            continue
        district = cells[0].strip()
        if not re.fullmatch(r"\d{1,2}", district):
            continue                      # the header row, and anything else
        name_cell = cells[1]
        role = None
        found = ROLE_RE.search(name_cell)
        if found:
            role = found.group(1).strip() or None
            name_cell = ROLE_RE.sub("", name_cell)
        name = re.sub(r"\s+", " ", name_cell).strip().rstrip(",").strip()
        if not name:
            continue
        rec = {"district": str(int(district)), "name": name}
        if role:
            rec["role"] = role
        phone = PHONE_RE.search(cells[2])
        if phone:
            rec["phone"] = phone.group(0)
        email = EMAIL_RE.search(" ".join(raw_cells[3:]))
        if email:
            rec["email"] = html.unescape(email.group(1)).strip()
        records.append(rec)
    return records


def main():
    out_path = output_path("jefferson_county_board_raw.json")
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-jefferson-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)
    if not records:
        print("jefferson-scraper: FAIL — parsed 0 member rows. Check the URL "
              "first: the county's own navigation links /government/county_board/"
              "index.php, which 404s while rendering a full-looking page; the "
              "live roster is at %s" % SOURCE_URL, file=sys.stderr)
        sys.exit(1)
    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("jefferson-scraper: wrote %s — %d members across %d districts, "
          "%d phones, %d e-mails, %d role(s)"
          % (out_path, len(records), len({r["district"] for r in records}),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("role"))))


if __name__ == "__main__":
    main()
