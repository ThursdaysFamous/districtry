#!/usr/bin/env python3
"""
Stage 1 of the Stephenson County Board roster pipeline: scrape the county board
page into raw JSON for build_stephenson_county_board_roster.py.

PAGE SHAPE. One HTML table, one row per district (lettered B-I — there is no
District A), five cells: the district label, a photo, member one, member two,
another photo. Each member cell carries the name inside a mailto link, then a
phone and a "Term through YYYY" line. The Chairman and Vice Chairman are named
ABOVE the table, in their own block, and are matched back to their seats by name.

TWO THINGS ON THIS PAGE THAT MUST NOT BE PROPAGATED:

1. AN E-MAIL THAT BELONGS TO SOMEONE ELSE. District C's Patrick Busker is linked
   to tmckenna@stephensoncountyil.gov — his predecessor's address. Publishing it
   would put a real, wrong person's inbox on a card under Busker's name. Every
   mailto is therefore checked against its own link text, and an address whose
   local part does not contain the member's surname is DROPPED and counted. This
   is not a hypothetical guard: as of 2026-07-30 it fires on exactly one seat.

2. AN EXPLICIT "Vacant" SEAT. District G's second seat reads "Vacant" with no
   link. That is a real fact about the board but not a person; vacancies are
   counted, never named — the same call the Livingston scraper made.

Term years are scraped and kept in the raw file for auditing but, matching every
other county in the fleet, are not carried onto the card.

Usage:
    python3 stephenson_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

SOURCE_URL = "https://stephensoncountyil.gov/government/county_board/index.php"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60

ANCHOR_RE = re.compile(r'<a[^>]+href="mailto:\s*([^"?\s]+)"[^>]*>(.*?)</a>', re.S | re.I)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
DISTRICT_RE = re.compile(r"District\s+([A-K])\b")
PHONE_RE = re.compile(r"\d{3}-\s?\d{3}-\s?\d{4}")
TERM_RE = re.compile(r"Term through\s*(\d{4})", re.I)
VACANT_RE = re.compile(r"\bvacan(?:t|cy)\b", re.I)
# "Vice Chairman" first, or the alternation matches the "Chairman" inside it and
# both officers resolve to the same role. The dash is the literal &mdash; ENTITY
# in this page's markup, not the character, so both spellings are accepted.
OFFICER_RE = re.compile(
    r"(Vice\s*Chairman|Chairman)\s*(?:&mdash;|&ndash;|[—–-])\s*"
    r"<a[^>]+href=\"mailto:\s*([^\"?\s]+)\"[^>]*>(.*?)</a>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def surname(name):
    parts = [p for p in re.sub(r"\([^)]*\)", " ", name or "").split() if p]
    return re.sub(r"[^a-z]", "", parts[-1].lower()) if parts else ""


def email_belongs(email, name):
    """The mailto must look like this member's own address."""
    sur = surname(name)
    return bool(sur) and sur in email.split("@")[0].lower()


def parse(page):
    officers = {}
    for role, email, label in OFFICER_RE.findall(page):
        key = "Vice Chairman" if role.lower().startswith("vice") else "Chairman"
        officers[key] = {"name": text_of(label), "email": email.strip()}

    start = page.find('id="FreeportDistricts"')
    table = page[start:page.find("</table>", start)] if start >= 0 else page
    records, vacancies = [], []
    for row in ROW_RE.findall(table):
        cells = CELL_RE.findall(row)
        if not cells:
            continue
        d = DISTRICT_RE.search(text_of(cells[0]))
        if not d:
            continue
        district = d.group(1)
        for cell in cells[1:]:
            body = text_of(cell)
            found = ANCHOR_RE.search(cell)
            if not found:
                if VACANT_RE.search(body):
                    vacancies.append(district)
                continue
            name = text_of(found.group(2))
            if not name:
                continue
            email = found.group(1).strip()
            tail = text_of(cell[found.end():])
            phone = PHONE_RE.search(tail)
            term = TERM_RE.search(tail)
            rec = {"district": district, "name": name}
            if phone:
                rec["phone"] = re.sub(r"\s+", "", phone.group(0))
            if term:
                rec["term_through"] = term.group(1)
            if email_belongs(email, name):
                rec["email"] = email
            else:
                # kept for the audit trail, never emitted as this member's contact
                rec["rejected_email"] = email
            records.append(rec)
    return officers, records, vacancies


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "stephenson_county_board_raw.json"
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-stephenson-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    officers, records, vacancies = parse(resp.text)
    if not records:
        print("stephenson-scraper: FAIL — parsed 0 member cells; the board table "
              "markup changed", file=sys.stderr)
        sys.exit(1)
    payload = {"source_url": SOURCE_URL, "officers": officers,
               "vacancies": vacancies, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    rejected = [r for r in records if r.get("rejected_email")]
    print("stephenson-scraper: wrote %s — %d members across %d districts, %d phones, "
          "%d e-mails (%d rejected as another member's), %d vacant seat(s), officers %s"
          % (out_path, len(records), len({r["district"] for r in records}),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("email")), len(rejected),
             len(vacancies), ", ".join(sorted(officers)) or "none"))
    for r in rejected:
        print("   note: District %s %s links %s, which is not their address — dropped"
              % (r["district"], r["name"], r["rejected_email"]), file=sys.stderr)


if __name__ == "__main__":
    main()
