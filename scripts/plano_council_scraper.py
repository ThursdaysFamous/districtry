#!/usr/bin/env python3
"""Read the City of Plano's own council page into a municipal-officials enrichment payload.

WHY A CITY SCRAPER AND NOT A COUNTY ONE. Kendall County's Clerk publishes a
yearbook, and this project already reads it — but that document goes only as
deep as the mayor and clerk for every municipality, so Plano's entry in
municipal-officials.json carries a head, a clerk and a treasurer and no council
at all. Plano's four wards are drawn on the ward layer from the county's
January 2022 data, so the card could say which ward a reader is in and could
name nobody in it. That is the plano-ward-officials gap, and its 2026-09-06
re-measure put the answer plainly: the roster half is a build, not a search.

WHAT THE PAGE PUBLISHES. www.cityofplanoil.com/153/Mayor-City-Council names all
eight council members, two per ward across four wards, each as a mailto anchor
whose link text is the person's name followed by ", Ward N". So the name, the
direct e-mail and the ward come out of one pattern and no position is inferred.
That matters here because the block is laid out in TWO COLUMNS and reads
interleaved — Nadeau (1), DeBolt (3), Swoboda (1), Wickens (3) — which would
misplace six of eight seats if the ward were taken from order rather than from
each member's own line.

THE MAYOR IS DELIBERATELY NOT READ, and the reason is on the page. Its mayor
block says "Elected in 2021" while the Kendall County Clerk's directory has
Rennels last elected 2025, so an adjacent field is stale even though the site is
maintained (its sidebar carries 2026 meeting videos). The county's entry already
names the mayor with the later date and is left standing; this payload supplies
the council and nothing else. The page also names a City Administrator, who is
appointed rather than elected and so is not a seat this roster carries.

THE E-MAIL DOMAIN IS NOT THE WEBSITE'S, and that is measured rather than
assumed: the site is cityofplanoil.com and all eight addresses are on
cityofplanoil.gov. Both resolve, and the .gov carries MX (Proofpoint
Essentials, checked 2026-09-11), so the addresses route. scripts/undeliverable.py
re-checks that on every run.

FETCH POSTURE. The site answers this project's own districtry token with
HTTP 200 (measured 2026-09-11, 120,442 bytes), so no browser string is needed
here. Its robots.txt disallows /admin, /activedit, /support, /OJA and the search,
calendar and map endpoints, and names Baiduspider and Yandex separately; the
`User-agent: *` group this scraper follows permits /153/Mayor-City-Council.

Usage:
    python3 scripts/plano_council_scraper.py --out /tmp/plano_council.json
"""

import argparse
import datetime
import html
import json
import re
import sys

import requests

SITE = "https://www.cityofplanoil.com"
OFFICIALS_PAGE = SITE + "/153/Mayor-City-Council"
JURISDICTION = "City of Plano"
COUNTY = "Kendall"

# City Hall — the office for every seat on this council, read from a constant
# rather than per-seat so a page change cannot promote a personal address into
# the office block (the Madison/Peoria rule). The page publishes no home
# address, so there is nothing here to refuse today; the constant is what keeps
# that true tomorrow. Both values agree with the Kendall County Clerk's
# yearbook entry this roster already carries, which is a second witness.
OFFICE = {
    "office_address": "17 E. Main Street",
    "office_city": "Plano",
    "office_state": "IL",
    "office_zip": "60545",
    "office_phone": "630-552-8275",
    "office_email": None,
}

WARDS = 4
SEATS_PER_WARD = 2
MIN_SEATS = 8
MIN_EMAILS = 8             # every seat on the page carries one; a drop is a regression

HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/il/)"}
TIMEOUT = 60

# name + e-mail + ward, from one anchor and the text that follows it. The ward
# is never taken from reading order — see the two-column note in the docstring.
SEAT_RE = re.compile(
    r'<a\s[^>]*href="mailto:([^"]+)"[^>]*>(.*?)</a>\s*,\s*Ward\s*(\d+)',
    re.I | re.S)


def clean(value):
    if not value:
        return None
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value)))
    value = " ".join(value.replace("\xa0", " ").split())
    return value or None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--html", help="parse a local copy instead of fetching")
    args = ap.parse_args()

    if args.html:
        with open(args.html, encoding="utf-8") as fh:
            body = fh.read()
    else:
        resp = requests.get(OFFICIALS_PAGE, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        body = resp.text
    scraped_at = (datetime.datetime.now(datetime.timezone.utc)
                  .strftime("%Y-%m-%dT%H:%M:%SZ"))

    records, warnings, seen = [], [], set()
    for email, name, ward in SEAT_RE.findall(body):
        person = clean(name)
        address = clean(email)
        if not person or not address:
            warnings.append("a seat anchor carried no name or no address — dropped")
            continue
        key = (person.lower(), int(ward))
        if key in seen:
            continue
        seen.add(key)
        records.append(dict(
            OFFICE,
            jurisdiction=JURISDICTION,
            office="Alderman",
            district="Ward %d" % int(ward),
            name=person,
            person_phone=None,
            person_email=address,
            source_url=OFFICIALS_PAGE,
            scraped_at=scraped_at,
        ))

    by_ward = {}
    for record in records:
        by_ward.setdefault(record["district"], []).append(record)
    emails = sum(1 for r in records if r["person_email"])

    problems = []
    if len(records) != MIN_SEATS:
        problems.append("%d seats, expected %d" % (len(records), MIN_SEATS))
    if len(by_ward) != WARDS:
        problems.append("%d ward(s), expected %d" % (len(by_ward), WARDS))
    # EVERY WARD MUST SEAT TWO. A city that quietly went to one per ward is a
    # real change worth a human look, and a parser that lost half the column is
    # the likelier cause — either way this must not ship four seats as eight.
    uneven = sorted(w for w, seats in by_ward.items() if len(seats) != SEATS_PER_WARD)
    if uneven:
        problems.append("not %d seats in %s" % (SEATS_PER_WARD, ", ".join(uneven)))
    if emails < MIN_EMAILS:
        problems.append("%d e-mail(s) < floor %d" % (emails, MIN_EMAILS))
    for warning in warnings:
        print("  warning: %s" % warning, file=sys.stderr)
    if problems:
        raise SystemExit("plano-council: " + "; ".join(problems)
                         + " — refusing to write")

    payload = {
        "county": COUNTY,
        "kind": "municipal-enrichment",
        "directory_url": OFFICIALS_PAGE,
        "officials_page": OFFICIALS_PAGE,
        "scraped_at": scraped_at,
        "municipalities": [{"name": JURISDICTION, "source_url": OFFICIALS_PAGE,
                            "scraped_at": scraped_at}],
        "officials": records,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print("scraped Plano: %d seats across %d wards, %d with a direct e-mail -> %s"
          % (len(records), len(by_ward), emails, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
