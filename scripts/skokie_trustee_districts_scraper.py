#!/usr/bin/env python3
"""
Skokie trustee districts + per-trustee e-mail (the village's own site)
=====================================================================
Supplies the one thing the Cook County Clerk's directory does not publish for
Skokie: which of its six trustees represent DISTRICTS, and which two are
elected at-large.

THE DISAGREEMENT THIS RESOLVES
------------------------------
Cook County GIS carries four "Skokie District" ward polygons (last edited
2024-07), but the Clerk's Directory of Elected Officials lists all six Skokie
trustees as municipality-wide, with no district on any of them. A Skokie point
therefore resolved a district polygon with no seat-holder joined to it — the
recorded "Skokie disagreement".

The village itself settles it. Skokie's "2025 Electoral Changes" page states
that beginning with the April 2025 Consolidated Election, "Four geographic
election districts now exist, with voters in each district electing one
trustee. In addition, two trustees are elected at-large." So the GIS is
current and the Clerk's roster is the incomplete side — it publishes the right
six people without their district assignments. This scraper reads the
assignments from the village's own Board of Trustees page, which labels each
trustee "Trustee (District N)" or "Trustee (At-Large)" and links a per-person
e-mail.

Skokie is the ONLY municipality in the app with ward geometry and no districted
seats in the roster — verified against every municipality in
data/app/municipal-ward-coverage.json — so this is a single-village fix, not
the first of a family. The builder now warns if another one ever appears.

THE CLERK REMAINS THE ROSTER OF RECORD. This contributes the district and the
e-mail only: the builder matches each trustee by name and fills fields the
county left empty, never adding, renaming, or re-roling a seat-holder. Note
that two trustees share the surname Levy (Kimani and Lissa), which the
builder's matcher separates on given name and would refuse outright rather
than guess.

Usage:
    python3 skokie_trustee_districts_scraper.py --out skokie_trustee_districts.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_124, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://www.skokie.org/486/Board-of-Trustees"
ELECTORAL_CHANGES_URL = "https://www.skokie.org/1379/2025-Electoral-Changes"

HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 60

JURISDICTION = "Village of Skokie"
# "Trustee (District 4)" / "Trustee (At-Large)" — the label under each name.
ROLE_RE = re.compile(r"^Trustee\s*\((?P<seat>District\s*\d+|At[\s-]*Large)\)$", re.I)
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w{2,}")

# Skokie's published structure: four district trustees + two at-large.
EXPECTED_DISTRICTS = 4
EXPECTED_AT_LARGE = 2


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-skokie-trustee-districts-scraper")
    return fetch_with_retry(url, HEADERS, timeout=REQUEST_TIMEOUT).text


def text_lines(html_text):
    body = re.sub(r"(?is)<(script|style|nav|footer)\b.*?</\1>", " ", html_text)
    out = []
    for line in re.sub(r"(?s)<[^>]+>", "\n", body).splitlines():
        line = " ".join(line.replace("\xa0", " ").split())
        if line:
            out.append(line)
    return out


def clean(value):
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def normalize_seat(seat):
    """"District 4" -> "District 4"; "At-Large" -> None (not a district)."""
    if re.match(r"^at[\s-]*large$", seat.strip(), re.I):
        return None
    match = re.search(r"\d+", seat)
    return "District %s" % match.group(0) if match else None


def page_emails(html_text):
    """Every trustee address on the page, lowercased and de-duplicated."""
    seen = []
    for address in EMAIL_RE.findall(html_text):
        address = address.lower()
        if address not in seen:
            seen.append(address)
    return seen


def local_letters(address):
    return re.sub(r"[^a-z]", "", address.split("@")[0].lower())


def email_for(name, addresses):
    """The one address that belongs to this trustee, or None.

    Surname alone is NOT enough: Skokie seats two trustees named Levy, and
    matching on surname would hand Lissa's row Kimani's address — the same
    first-match-wins failure the 2026-07-28 name-collision sweep chased out of
    the joins. Surname narrows, the given name disambiguates, and anything
    still ambiguous returns None rather than a plausible wrong address.
    """
    tokens = [t.lower() for t in re.split(r"[^A-Za-z]+", name or "") if t]
    if not tokens:
        return None
    surname, given = tokens[-1], tokens[:-1]
    candidates = [a for a in addresses if surname in local_letters(a)]
    if len(candidates) == 1:
        return candidates[0]
    narrowed = [a for a in candidates
                if any(g in local_letters(a) for g in given)]
    return narrowed[0] if len(narrowed) == 1 else None


def scrape(scraped_at, html_text=None):
    if html_text is None:
        html_text = fetch(BOARD_URL)
    lines = text_lines(html_text)
    addresses = page_emails(html_text)

    records = []
    for i, line in enumerate(lines):
        match = ROLE_RE.match(line)
        if not match or i == 0:
            continue
        name = clean(lines[i - 1])
        if not name or not re.match(r"^[A-Z][A-Za-z.'’\- ]+$", name):
            continue
        district = normalize_seat(match.group("seat"))
        records.append({
            "jurisdiction": JURISDICTION,
            "office": "Trustee",
            # None for the two at-large trustees: they hold no district, and
            # the card must not imply one.
            "district": district,
            "name": name,
            "person_phone": None,
            "person_email": email_for(name, addresses),
            "source_url": BOARD_URL,
            "scraped_at": scraped_at,
        })
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="skokie_trustee_districts.json")
    parser.add_argument("--html", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html_text = None
    if args.html:
        with open(args.html, encoding="utf-8", errors="replace") as f:
            html_text = f.read()
    records = scrape(scraped_at, html_text)

    districts = [r for r in records if r["district"]]
    at_large = [r for r in records if not r["district"]]
    if len(districts) != EXPECTED_DISTRICTS or len(at_large) != EXPECTED_AT_LARGE:
        print("FATAL: parsed %d district + %d at-large trustees, expected %d + %d — the "
              "village's page changed, or its board structure did (either needs a human)"
              % (len(districts), len(at_large), EXPECTED_DISTRICTS, EXPECTED_AT_LARGE),
              file=sys.stderr)
        sys.exit(1)
    seats = sorted(r["district"] for r in districts)
    if len(set(seats)) != EXPECTED_DISTRICTS:
        print("FATAL: districts are not distinct (%s)" % ", ".join(seats), file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Cook",
        "kind": "municipal-enrichment",
        "directory_url": ELECTORAL_CHANGES_URL,
        "scraped_at": scraped_at,
        "officials": records,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    with_email = sum(1 for r in records if r["person_email"])
    print("scraped Skokie: %d district trustees + %d at-large, %d with e-mail -> %s"
          % (len(districts), len(at_large), with_email, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
