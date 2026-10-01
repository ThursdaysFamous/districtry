#!/usr/bin/env python3
"""
Stage 1 of the Montgomery County Board roster pipeline: scrape the county's
board page into raw JSON for build_montgomery_board_roster.py.

PAGE SHAPE. A WPBakery page, not a table. Each district is an `ot_custom_heading`
h3 reading "DISTRICT N", and the members who follow it — until the next such
heading — each sit in their own paragraph:

    <p><strong>Doug Donaldson</strong><br />
       <em>Board Chairman</em><br />        (only where a role is held)
       217-710-0775<br />                   (one or two numbers)
       <a href="mailto:doug.donaldson@montgomerycountyil.gov">Send Message</a></p>

So the parse is: split the page on the district headings, then read the
paragraphs in each slice. Nothing is inferred from document order beyond "a
member belongs to the heading above it", which is the page's own structure.

WHAT THE COUNTY PUBLISHES, AND IT IS A LOT. All fourteen members carry a direct
phone; four carry a second number; every one carries a county e-mail address.
This is a richer per-seat contact set than most counties in the fleet, and it is
why the board card can lead with the member rather than with a link to the body.

TWO NUMBERS ARE TWO NUMBERS. Where the county prints a second line, both are
kept, in the order printed. They are not labelled home/cell on the page and are
not labelled here — guessing which is which would be inventing a fact about
someone's phone.

ONE PUBLISHED E-MAIL LOOKS WRONG, AND SHIPS ANYWAY. District 5's Cody Gudgel is
listed at cody.gudel@montgomerycountyil.gov — "gudel", where every other address
on the page is firstname.lastname. It is very likely the county's typo. It is
carried EXACTLY as published regardless: correcting it would mean inventing an
address string, which could belong to nobody or to somebody else, and this
project does not invent contact details. The run prints a NOTE naming it so the
discrepancy is visible rather than silently propagated, and it goes back to the
county as a bug report. (Compare the Jefferson precinct file's Dodds overlap,
shipped as drawn and reported: a defect you can see is worth more than a repair
you cannot source.)

MEMBERS CHANGE FASTER THAN THE COUNTY'S PDF. The Clerk also publishes a
"County Board Districts/Members" PDF revised 12/2024, which is where the DISTRICT
COMPOSITION comes from (see build_montgomery_boundaries.py). Do not take the
roster from it: checked 2026-08-06, it still named Bill Bergen (District 5) and
Andy Ritchie (District 7) where this page has Cody Gudgel and Roy Schieferdecker.
The page is the fresher of the county's own two sources, so the page is scraped.

Usage:
    python3 montgomery_county_board_scraper.py [output.json]
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

SOURCE_URL = "https://montgomerycountyil.gov/county-board/"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
# The heading carries the district and nothing else. Matched on the h3 rather
# than on the words "DISTRICT N" anywhere, so a mention in the page's prose
# ("two elected from each of seven districts") can never open a new section.
HEADING_RE = re.compile(r"<h3[^>]*>\s*DISTRICT\s+(\d+)\s*</h3>", re.I)
MEMBER_RE = re.compile(r"<p>\s*<strong>(.*?)</strong>(.*?)</p>", re.S | re.I)
EMAIL_RE = re.compile(r"mailto:\s*([^\"?\s>]+)", re.I)
PHONE_RE = re.compile(r"\d{3}-\d{3}-\d{4}")
ROLE_RE = re.compile(r"<em>(.*?)</em>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

# The address every other member's e-mail follows. Used only to NOTE the odd one
# out — never to rewrite it. See the module docstring.
EMAIL_SHAPE_RE = re.compile(r"^([a-z]+)\.([a-z]+)@montgomerycountyil\.gov$", re.I)


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def parse(page):
    page = SCRIPT_RE.sub(" ", page)
    headings = list(HEADING_RE.finditer(page))
    if not headings:
        return []
    records = []
    for i, match in enumerate(headings):
        district = str(int(match.group(1)))
        end = headings[i + 1].start() if i + 1 < len(headings) else len(page)
        for member in MEMBER_RE.finditer(page[match.end():end]):
            name = text_of(member.group(1))
            body = member.group(2)
            if not name:
                continue
            rec = {"district": district, "name": name}
            role = ROLE_RE.search(body)
            if role:
                rec["role"] = text_of(role.group(1))
            phones = PHONE_RE.findall(text_of(body))
            if phones:
                rec["phone"] = phones[0]
                if len(phones) > 1:
                    rec["phones_extra"] = phones[1:]
            email = EMAIL_RE.search(body)
            if email:
                rec["email"] = html.unescape(email.group(1)).strip()
            records.append(rec)
    return records


def surname_mismatches(records):
    """Members whose published e-mail does not match their published surname.

    Reported, never corrected — the point is to make a county typo visible to a
    human, not to guess what the address should have been.
    """
    odd = []
    for rec in records:
        email = rec.get("email")
        if not email:
            continue
        shape = EMAIL_SHAPE_RE.match(email)
        if not shape:
            odd.append((rec["name"], email, "not firstname.lastname@montgomerycountyil.gov"))
            continue
        surname = rec["name"].split()[-1].lower()
        if shape.group(2).lower() != surname:
            odd.append((rec["name"], email,
                        "local part says %r, the county spells the surname %r"
                        % (shape.group(2), rec["name"].split()[-1])))
    return odd


def main():
    out_path = output_path("montgomery_county_board_raw.json")
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-montgomery-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)
    if not records:
        print("montgomery-scraper: FAIL — parsed 0 members; the page's district "
              "headings or member paragraphs changed shape", file=sys.stderr)
        sys.exit(1)

    for name, email, why in surname_mismatches(records):
        print("montgomery-scraper: NOTE — %s is published at %s (%s). Carried "
              "exactly as the county publishes it; not corrected here."
              % (name, email, why), file=sys.stderr)

    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("montgomery-scraper: wrote %s — %d members across %d districts, "
          "%d phones (%d with a second number), %d e-mails, %d role(s)"
          % (out_path, len(records), len({r["district"] for r in records}),
             sum(1 for r in records if r.get("phone")),
             sum(1 for r in records if r.get("phones_extra")),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("role"))))


if __name__ == "__main__":
    main()
