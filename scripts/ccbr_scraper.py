#!/usr/bin/env python3
"""
Cook County Board of Review Commissioner Scraper
================================================
Extracts the three elected Commissioners (name + district + on-page contact
info + commissioner-page link) from the Board of Review's own site at
cookcountyboardofreview.com.

Why scrape rather than call an API: the Board of Review's three districts ship
in the app as pre-built PA 102-0012 geometry (data/app/ccbr-districts.json),
but the shapefile carries no officeholder fields and no queryable open dataset
names the commissioners (confirmed 2026-07-20 — the county's electedOfficials
GIS table covers the Board of Commissioners, not the Board of Review). The
commissioners are only published as rendered HTML on the Board's own site.
This scraper is the build-time step that produces a raw JSON, resolved into
data/app/ccbr-roster.json by scripts/build_ccbr_roster.py (same two-stage
pattern as scripts/ccpsa_scraper.py + scripts/build_ccpsa_roster.py).

The site is a plain Drupal build with no Cloudflare JS challenge — a plain
requests client gets the full rendered HTML — so this scraper stays
browserless (requests + BeautifulSoup), matching the ccpsa_scraper.py
template.

Commissioner page URLs are discovered from the site's own "Commissioner Menu"
block rather than hardcoded, so a post-election name/URL change (the paths are
name-derived, e.g. /GeorgeCardenas) can't silently break the scrape: a new
commissioner shows up in the menu with a new path and is followed from there.

District extraction: the three pages word their district inconsistently —
"First District" (ordinal-first), "serves as Commissioner for District 2"
(digit-after), "3rd District" (numeric-ordinal) were all live wordings on
2026-07-20 — so both orderings are matched, words and numerals.

Usage:
    python3 ccbr_scraper.py --out ccbr_commissioners.json

Notes on data honesty (per project conventions):
- If a field can't be found on a page, it is stored as null / empty list,
  never guessed or fabricated. In particular a district email is NOT inferred
  from the other districts' BORDistrict<N>info@ pattern — District 2 published
  no email on 2026-07-20 (contact form only) and its record honestly omits it.
- Every record includes `source_url` and `scraped_at` for traceability.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from scraper_common import require_robots_once, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

BASE = "https://www.cookcountyboardofreview.com"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 30
POLITE_DELAY_S = 1.0

WORD_TO_NUM = {
    "first": 1, "second": 2, "third": 3,
    "1st": 1, "2nd": 2, "3rd": 3,
    "one": 1, "two": 2, "three": 3,
}

# Both live wordings, most-specific first: "First District"/"3rd District"
# (ordinal before the noun) and "District 2"/"District Two" (noun first).
DISTRICT_BEFORE = re.compile(
    r"\b(first|second|third|1st|2nd|3rd)\s+district\b", re.IGNORECASE)
DISTRICT_AFTER = re.compile(
    r"\bdistrict\s+(1|2|3|one|two|three)\b", re.IGNORECASE)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}")

# A COMMISSIONER'S PHONE IS THE ONE IN THE SENTENCE THAT ALSO CARRIES THEIR
# DISTRICT INBOX, and taking anything else has now been wrong twice.
#
# Scoping to <main> (below) already keeps the sitewide footer's switchboard and
# fax out. It does nothing about numbers in BODY COPY, and every commissioner
# page has some. Measured 2026-08-22 across all three:
#
#   District 1  "Contact Commissioner Cardenas at (312) 603-2676 or
#               BORDistrict1info@cookcountyil.gov"           <- the real one
#               "please call the Riverside Township office at 708-447-7700"
#                                                            <- another body's office
#   District 2  "Please Call (773) 853-0799 to Register to Attend this Event"
#                                                            <- an event RSVP line
#   District 3  "Text EZJOIN to 872-345-4747"                <- an SMS shortcode
#               "contact my office ... or by phone at 312-603-5540"  <- the real one
#
# Taking the FIRST number in document order, which this scraper did until
# 2026-08-22, shipped the SMS shortcode as District 3's office phone and would
# have shipped the event line as District 2's (PR #425, caught in review and
# closed). Both parse perfectly and mean something else — the Coles lesson in a
# different costume.
#
# The positive rule below is what the site itself does on both pages that
# publish a contact: the phone and the district inbox sit in one sentence. It
# yields the right number for Districts 1 and 3 and NOTHING for District 2,
# which is correct — that page publishes a contact form instead, and a district
# with no published phone must show none rather than borrow one.
DISTRICT_INBOX_RE = re.compile(r"\bBORdistrict\d\w*@", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# Defence in depth: constructions that put a number in a sentence WITHOUT it
# being a number to call. Checked even inside an inbox sentence, because a
# future page edit could put a shortcode next to an address.
NOT_A_PHONE_CUE_RE = re.compile(
    r"\btext\b[^.]{0,40}\bto\b\s*$|\bregister\b[^.]{0,30}$|\bfax\b\s*:?\s*$",
    re.IGNORECASE)


def contact_phones(text):
    """Phones presented as THIS commissioner's contact, in document order.

    `text` is the page's main-region text. Returns [] when the page publishes
    no district-inbox sentence carrying a number, which is a real answer and
    not a scrape failure."""
    found = []
    for sentence in SENTENCE_SPLIT_RE.split(text):
        if not DISTRICT_INBOX_RE.search(sentence):
            continue
        for m in PHONE_RE.finditer(sentence):
            if NOT_A_PHONE_CUE_RE.search(sentence[:m.start()]):
                continue
            found.append(m.group(0))
    return list(dict.fromkeys(found))


def fetch(url, session):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-ccbr-scraper")
    resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def discover_commissioners(home_html):
    """[(name, absolute_url)] from the homepage's Commissioner Menu block.

    Keys on the Drupal block id (block-commissionermenu) so nav restyles that
    keep the menu block keep the scrape working; entries whose text doesn't
    contain "Commissioner" are skipped (defensive against menu additions).
    """
    soup = BeautifulSoup(home_html, "html.parser")
    block = soup.find(id=re.compile(r"block-commissionermenu", re.IGNORECASE))
    if block is None:
        # Fallback: any nav link whose text starts with "Commissioner " —
        # weaker, but survives a block-id rename.
        block = soup
    out = []
    seen = set()
    for a in block.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        if not re.match(r"commissioner\s+\S", text, re.IGNORECASE):
            continue
        name = re.sub(r"^commissioner\s+", "", text, flags=re.IGNORECASE).strip()
        url = urljoin(BASE, a["href"])
        if not name or url in seen:
            continue
        seen.add(url)
        out.append((name, url))
    return out


def extract_district(page_text):
    m = DISTRICT_BEFORE.search(page_text)
    if m:
        return WORD_TO_NUM.get(m.group(1).lower())
    m = DISTRICT_AFTER.search(page_text)
    if m:
        token = m.group(1).lower()
        return int(token) if token.isdigit() else WORD_TO_NUM.get(token)
    return None


def scrape_commissioner(name, url, session):
    record = {
        "name": name,
        "url": url,
        "district_number": None,
        "emails": [],
        "phones": [],
        "source_url": url,
        "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    html = fetch(url, session)
    soup = BeautifulSoup(html, "html.parser")
    # Contact extraction is scoped to the page's MAIN content region: the
    # sitewide footer carries the Board's main line (312-603-5542) on every
    # page, and attributing it to a commissioner who publishes no number of
    # their own would be a small dishonesty (District 2 published no direct
    # contact as of 2026-07-20 — its record should say so, not borrow the
    # switchboard). Falls back to the whole page if Drupal's <main> vanishes.
    content = soup.find("main") or soup
    emails = []
    for a in content.find_all("a", href=re.compile(r"^mailto:", re.IGNORECASE)):
        emails.append(a["href"].split(":", 1)[1].split("?")[0].strip())
    text = " ".join(content.get_text(" ", strip=True).split())
    emails.extend(EMAIL_RE.findall(text))
    record["emails"] = list(dict.fromkeys(e for e in emails if e))
    # Both lists ship: `phones` is every number in the main region, kept so a
    # reviewer can see what was rejected and why, and `contact_phones` is the
    # subset the builder is allowed to use.
    record["phones"] = list(dict.fromkeys(PHONE_RE.findall(text)))
    record["contact_phones"] = contact_phones(text)
    record["district_number"] = extract_district(text)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="ccbr_commissioners.json")
    args = parser.parse_args()

    session = requests.Session()
    home = fetch(BASE + "/", session)
    commissioners = discover_commissioners(home)
    if not commissioners:
        print("FATAL: no commissioner links found in the Commissioner Menu", file=sys.stderr)
        sys.exit(1)

    records = []
    for name, url in commissioners:
        try:
            records.append(scrape_commissioner(name, url, session))
        except Exception as e:  # noqa: BLE001 — record the failure, never fabricate
            records.append({"name": name, "url": url, "error": str(e)})
        time.sleep(POLITE_DELAY_S)

    with open(args.out, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    ok = [r for r in records if not r.get("error")]
    resolved = [r for r in ok if r.get("district_number")]
    print("scraped %d commissioner pages (%d ok, %d with a district) -> %s"
          % (len(records), len(ok), len(resolved), args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
