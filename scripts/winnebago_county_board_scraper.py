#!/usr/bin/env python3
"""
Stage 1 of the Winnebago County Board contact pipeline: scrape the county's
board page for the phone and e-mail its GIS layer declares and never fills.

WHY THIS EXISTS. The board card already resolves from WinGIS
(ElectedOfficials/26), which carries the district, member and party 20/20 — so
Winnebago shipped as rule-4 branch 1 with no roster at all. But that layer also
declares ADDRESS, CITYZIP, PHONEHOME and PHONEBUSIN and populates every one of
them on 0 of 20 rows, while the county's own board page prints a phone and an
official @board.wincoil.gov address for every district. That gap was recorded as
`winnebago-board-contact` with the note that it "closes with work, not data".
This is the work.

THE E-MAIL IS BASE64, NOT TEXT. The page is Joomla and wraps every address in
<joomla-hidden-mail text="QUJvb2tlckBib2FyZC53aW5jb2lsLmdvdg=="> as spam
obfuscation; the visible text is the string "This email address is being
protected from spambots." Reading the rendered text would collect that sentence
for twenty people. The base64 `text` attribute is the address.

WHAT IS DELIBERATELY NOT COLLECTED: the street address. The page prints one per
member and they are RESIDENCES (rural route numbers, an apartment) rather than
county offices — the same call build_mchenry_county_board_roster.py,
livingston and sangamon all made. The e-mail is collected precisely because it
is NOT personal: @board.wincoil.gov is an office address the county issues.

Term-end is parsed only to cross-check party against the GIS; it is not carried
into the card, matching the recorded fleet call that term-end is not card
material.

Usage:
    python3 winnebago_county_board_scraper.py [output.json]
"""

import base64
import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

SOURCE_URL = "https://wincoil.gov/government/county-board"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 60

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
# Each member sits under a heading that links their district's map PDF. That
# link is the only reliable block delimiter on the page — the surrounding
# markup is generated Joomla page-builder divs with churn-prone ids.
BLOCK_RE = re.compile(
    r'(?=<h3[^>]*><a href="/images/government/county-board/District_Maps/)')
DISTRICT_RE = re.compile(r">District (\d+)</a>")
NAME_RE = re.compile(r"<strong>(.*?)</strong>", re.S)
MAIL_RE = re.compile(r'<joomla-hidden-mail[^>]*\stext="([^"]+)"')
PHONE_RE = re.compile(r'href="tel:(\d+)"')
PARTY_TERM_RE = re.compile(r"<br />\s*([RDI])-(\d{4})")

# 20 single-member districts.
MIN_DISTRICTS = 18
MIN_EMAILS = 18
MIN_PHONES = 16


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def decode_mail(encoded):
    try:
        return base64.b64decode(encoded).decode("utf-8").strip() or None
    except (ValueError, UnicodeDecodeError):
        return None


def clean_phone(digits):
    digits = re.sub(r"\D", "", digits or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def parse(page):
    body = SCRIPT_RE.sub("", page)
    records = []
    seen = set()
    for block in BLOCK_RE.split(body)[1:]:
        district = DISTRICT_RE.search(block)
        name = NAME_RE.search(block)
        if not (district and name):
            continue
        key = district.group(1)
        if key in seen:
            continue  # the page repeats a heading in its nav; first wins
        seen.add(key)
        rec = {"district": key, "name": text_of(name.group(1)).strip(" ,")}
        mail = MAIL_RE.search(block)
        if mail:
            address = decode_mail(mail.group(1))
            if address and "@" in address:
                rec["email"] = address
        phone = PHONE_RE.search(block)
        if phone:
            number = clean_phone(phone.group(1))
            if number:
                rec["phone"] = number
        party_term = PARTY_TERM_RE.search(block)
        if party_term:
            rec["party"] = party_term.group(1)
            rec["term"] = party_term.group(2)
        records.append(rec)
    return records


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "winnebago_county_board_raw.json"
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-winnebago-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)

    emails = sum(1 for r in records if r.get("email"))
    phones = sum(1 for r in records if r.get("phone"))
    problems = []
    if len(records) < MIN_DISTRICTS:
        problems.append("%d districts (< %d)" % (len(records), MIN_DISTRICTS))
    if emails < MIN_EMAILS:
        problems.append("%d e-mails (< %d) — the joomla-hidden-mail shape changed"
                        % (emails, MIN_EMAILS))
    if phones < MIN_PHONES:
        problems.append("%d phones (< %d)" % (phones, MIN_PHONES))
    if problems:
        print("winnebago-board-scraper: FATAL — %s" % "; ".join(problems), file=sys.stderr)
        sys.exit(1)

    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("winnebago-board-scraper: wrote %s — %d districts, %d e-mails, %d phones, "
          "%d parties" % (out_path, len(records), emails, phones,
                          sum(1 for r in records if r.get("party"))))


if __name__ == "__main__":
    main()
