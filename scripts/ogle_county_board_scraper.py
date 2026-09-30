#!/usr/bin/env python3
"""
Stage 1 of the Ogle County Board roster pipeline: scrape the county's staff
directory into raw JSON for build_ogle_county_board_roster.py.

The directory is a Revize "staff_directory" table with four columns — County
Board District, Name, Email, Phone — one row per member, 24 rows for 8 districts
of 3. Everything this parses comes out of a row's own cells; nothing is inferred
from position on the page.

WHAT THE NAME CELL CARRIES. Three things run together in one cell:

    Zachary S. Oltmanns (R)
    Patricia Nordman - Vice Chairman (R)
    Bruce Larson - Chairman (R)

so the party is unpacked from its trailing parenthesis and the leadership role
from the " - " segment, leaving the name. Order matters: the role sits BEFORE
the party, so the party is stripped first.

THE ROSTER IS FRESHER THAN THE COUNTY'S OWN YEARBOOK, which is why this page is
the source rather than the annual PDF. The 2025-2027 clerk's yearbook prints
District 8's second 2028-term seat as VACANT; this directory names Megan Poole
in it. A yearbook is a snapshot, the directory is maintained.

Ogle publishes no district geometry, so the other half of this county's card —
data/app/ogle-county-board-districts.json — is built separately from the
precinct composition its reapportionment resolution adopts
(scripts/build_ogle_board_districts.py). That half changes once a decade; this
one is weekly.

Usage:
    python3 ogle_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_WIN_126,
    require_robots_once,
)

SOURCE_URL = "https://www.oglecountyil.gov/staff_directory/county_board_members.php"
# The county site serves a bare client fine; a browser UA is used anyway so a
# future bot filter degrades to a clear HTTP error rather than a silent stub.
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 60

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
DISTRICT_RE = re.compile(r"District\s*#?\s*(\d+)", re.I)
EMAIL_RE = re.compile(r"mailto:([^\"?\s>]+)", re.I)
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)

# Normalised to the single-letter badge the neighbouring counties' cards show.
PARTY = {"r": "R", "rep": "R", "republican": "R",
         "d": "D", "dem": "D", "democrat": "D", "democratic": "D",
         "i": "I", "ind": "I", "independent": "I"}
ROLE_RE = re.compile(r"\b(Vice[-\s]?Chair(?:man|person|woman)?|Chair(?:man|person|woman)?)\b", re.I)


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def parse(page):
    page = SCRIPT_RE.sub(" ", page)
    records = []
    for row in ROW_RE.findall(page):
        cells = CELL_RE.findall(row)
        if len(cells) < 2:
            continue
        d = DISTRICT_RE.search(text_of(cells[0]))
        if not d:
            continue
        raw = text_of(cells[1])
        if not raw:
            continue
        rec = {"district": d.group(1).lstrip("0") or "0", "raw_name": raw}

        # party first — it trails the role, so removing it leaves a clean " - role"
        party = re.search(r"\(([^)]{1,14})\)\s*$", raw)
        if party:
            key = re.sub(r"[^a-z]", "", party.group(1).lower())
            if key in PARTY:
                rec["party"] = PARTY[key]
            raw = raw[:party.start()].strip()

        role = ROLE_RE.search(raw)
        if role and " - " in raw:
            label = role.group(1).strip().lower()
            rec["role"] = "Vice Chair" if label.startswith("vice") else "Board Chair"
            raw = raw.split(" - ", 1)[0].strip()

        name = re.sub(r"\s+", " ", raw).strip(" ,-")
        rec["name"] = name or None

        blob = " ".join(cells[2:])
        email = EMAIL_RE.search(blob)
        if email:
            rec["email"] = html.unescape(email.group(1)).strip()
        phone = PHONE_RE.search(text_of(blob))
        if phone:
            rec["phone"] = re.sub(r"\s+", " ", phone.group(0)).strip()
        records.append(rec)
    return records


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "ogle_county_board_raw.json"
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-ogle-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)
    if not records:
        print("ogle-scraper: FAIL — parsed 0 directory rows; the table markup changed",
              file=sys.stderr)
        sys.exit(1)
    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("ogle-scraper: wrote %s — %d members across %d districts, %d phones, "
          "%d e-mails, %d role(s)"
          % (out_path, len(records), len({r["district"] for r in records}),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("role"))))


if __name__ == "__main__":
    main()
