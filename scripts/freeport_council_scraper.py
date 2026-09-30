#!/usr/bin/env python3
"""
Freeport city government (the city's own site)
=============================================
Supplies the ONE municipality Stephenson County's village directory leaves out,
and it is the one that matters most: Freeport is the county seat and, at ~23,600
people, holds well over half the county's municipal population. The county page
(stephenson_municipal_officials_scraper.py) covers the other ten villages;
without this payload the biggest city in the county would be the only one whose
card named nobody.

The builder applies this as an --enrich payload. Enrichment normally only fills
per-seat contact the county left empty, but for a municipality the county source
omits entirely it inserts the whole entry — the same path Lockport and
Wilmington already take in Will County.

SOURCE. cityoffreeport.org runs WordPress with an `lsvr_person` post type and an
`elected-officials` category, so the MEMBERSHIP of the governing body is a REST
query rather than a scrape of a hand-maintained list — a seat that changes hands
leaves the category the moment the city updates it. Each person's page then
carries a schema.org `Person` JSON-LD block with name, jobTitle, email and
telephone, which is a machine-readable contract the city publishes deliberately.
The subtitle element is read as a fallback for jobTitle; in practice the two
have always agreed.

WHY NOT THE CITY'S WARD FEATURESERVER. Freeport publishes a `Wards2022_Public`
layer (services2.arcgis.com/1Wpk33n06s235zfI) whose features carry an
`Alderperson` field, and it looks like the tidier source. It is STALE: measured
2026-07-31 its data was last edited 2024-05-21, so it still named the 2nd Ward's
previous alderman, who left at the April 2025 election. The WordPress directory
had the current holder. Boundary geometry from that layer would still be usable
if ward polygons are ever added; the officeholder field must not be.

WHAT IS DELIBERATELY NOT COLLECTED. Each bio's opening paragraph is the member's
RESIDENCE ("2212 Farmdale Ln."), published as a residency disclosure rather than
as a way to reach them. It is not collected, matching the call made for LaSalle,
Madison, McHenry, Livingston, Sangamon, Winnebago and Stephenson. The ward
e-mail and the phone the city prints beside it ARE collected: those are the
contact channels the city tells constituents to use for that seat.

FETCH POSTURE: open. Plain `requests` with a browser UA gets 200 from both the
REST API and the person pages; there is no challenge.

Usage:
    python3 freeport_council_scraper.py --out freeport_council.json
"""

import argparse
import datetime
import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_WIN_126,
    require_robots_once,
)

SITE = "https://cityoffreeport.org"
CATEGORY_SLUG = "elected-officials"
CAT_URL = SITE + "/wp-json/wp/v2/lsvr_person_cat?slug=" + CATEGORY_SLUG
PEOPLE_URL = SITE + "/wp-json/wp/v2/lsvr_person?lsvr_person_cat=%s&per_page=100"
# The city's own directory record for City Hall, which is the office address for
# every seat below. Read rather than hardcoded so a move shows up here.
CITY_HALL_URL = SITE + "/directory2/freeport-illinois-city-hall/"
OFFICIALS_PAGE = SITE + "/people2/"

JURISDICTION = "City of Freeport"
CITY_NAME = "Freeport"
COUNTY = "Stephenson"

HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 60

LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
SUBTITLE_RE = re.compile(r'<p class="post__subtitle">\s*(.*?)\s*</p>', re.S)
ADDRESS_RE = re.compile(r'<p class="post__addressmap-address">\s*(.*?)\s*</p>', re.S)
HALL_PHONE_RE = re.compile(r'post__contact-item--phone.*?<a href="tel:([^"]+)"', re.S)
TAG_RE = re.compile(r"<[^>]+>")
# "314 W. Stephenson Freeport, IL 61032" — the city's record runs the street and
# the city together with no comma between them, so the state and ZIP come off
# the tail first and the CITY NAME ITSELF is what separates the rest.
STATE_ZIP_RE = re.compile(r"^(.*?),?\s*([A-Z]{2})\s*(\d{5})(?:-\d{4})?$")

# "1st Ward Alderman", "2nd Ward Alderwoman", "7th Ward Alderman".
WARD_RE = re.compile(r"^(\d+)(?:st|nd|rd|th)?\s+Ward\s+"
                     r"(Alder(?:man|woman|person))\s*$", re.I)
# "Alderwoman-At-Large" (the city hyphenates it; other spellings tolerated).
AT_LARGE_RE = re.compile(r"^(Alder(?:man|woman|person))[\s-]*at[\s-]*large\s*$", re.I)
CITYWIDE_RE = re.compile(r"^(?:City\s+)?(Mayor|Clerk|Treasurer)\s*$", re.I)

# Freeport elects a mayor, an alderperson at large, and one alderperson per ward
# (7 wards since the 2022 remap), plus a city clerk. The floors sit one under
# the full council so an ordinary vacancy does not fail the run, but losing the
# category wholesale does.
MIN_OFFICIALS = 8
MIN_SEATS = 6


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment or ""))).strip()


def clean(value):
    value = re.sub(r"\s+", " ", (value or "")).strip()
    return value or None


def get(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-freeport-council-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp


def person_ld(page):
    """The schema.org Person block, or None if the page carries no such block."""
    for match in LD_RE.finditer(page):
        try:
            obj = json.loads(match.group(1))
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("@type") == "Person":
            return obj
    return None


def city_hall(warnings):
    """-> the office block fields, read from the city's own City Hall record."""
    page = get(CITY_HALL_URL).text
    address = ADDRESS_RE.search(page)
    phone = HALL_PHONE_RE.search(page)
    street = city = state = zipcode = None
    if address:
        whole = text_of(address.group(1))
        parts = STATE_ZIP_RE.match(whole)
        if parts:
            street, state, zipcode = clean(parts.group(1)), parts.group(2), parts.group(3)
            # Split the city off the street by its own name, the only separator
            # the record gives. If it isn't there, the city stays None and the
            # street ships whole — the builder then renders "<street>, IL 61032",
            # which is still a correct address, just a denser one.
            tail = re.search(r"[,\s]+(%s)$" % re.escape(CITY_NAME), street or "", re.I)
            if tail:
                city = tail.group(1)
                street = clean(street[:tail.start()])
            else:
                warnings.append("City Hall address '%s' does not end in the city "
                                "name — shipped as one line" % whole)
        else:
            street = clean(whole)
            warnings.append("City Hall address '%s' carries no state/ZIP — "
                            "shipped whole" % whole)
    else:
        warnings.append("no address block on the City Hall record — office "
                        "address omitted")
    return {
        "office_address": street,
        "office_city": city,
        "office_state": state,
        "office_zip": zipcode,
        "office_phone": clean(phone.group(1)) if phone else None,
        "office_email": None,
        "website": SITE + "/",
    }


def classify(job_title, warnings, who):
    """'2nd Ward Alderwoman' -> ('Alderwoman', 'Ward 2')."""
    title = clean(job_title) or ""
    ward = WARD_RE.match(title)
    if ward:
        return ward.group(2).title(), "Ward %s" % int(ward.group(1))
    at_large = AT_LARGE_RE.match(title)
    if at_large:
        return at_large.group(1).title(), "At Large"
    citywide = CITYWIDE_RE.match(title)
    if citywide:
        # "City Clerk" ships as "City Clerk"; "Mayor" as "Mayor".
        return title.title(), None
    # Never guessed into a known office: the builder classifies an unknown title
    # under officers and says so, which is the visible outcome we want.
    warnings.append("%s: unrecognised office '%s' — shipped verbatim" % (who, title))
    return title or None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    warnings = []
    try:
        terms = get(CAT_URL).json()
        if not terms:
            raise RuntimeError("no '%s' person category on the site — the city's "
                               "directory was reorganised" % CATEGORY_SLUG)
        people = get(PEOPLE_URL % terms[0]["id"]).json()
        office = city_hall(warnings)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    records = []
    for person in people:
        link = person.get("link")
        listed = text_of(person.get("title", {}).get("rendered"))
        try:
            page = get(link).text
        except Exception as exc:  # noqa: BLE001 - one page must not sink the rest
            warnings.append("%s (%s) could not be fetched: %s" % (listed, link, exc))
            continue
        block = person_ld(page) or {}
        subtitle = SUBTITLE_RE.search(page)
        job_title = clean(block.get("jobTitle")) or (
            text_of(subtitle.group(1)) if subtitle else None)
        if not job_title:
            warnings.append("%s (%s) publishes no office — skipped rather than "
                            "shipped with a guessed one" % (listed, link))
            continue
        name = clean(block.get("name")) or listed
        title, district = classify(job_title, warnings, name)
        records.append(dict(office, jurisdiction=JURISDICTION, office=title,
                            district=district, name=name,
                            person_phone=clean(block.get("telephone")),
                            person_email=clean(block.get("email")),
                            source_url=link, scraped_at=scraped_at))

    seats = sum(1 for r in records if r["district"])
    for warning in warnings:
        print("  warning: %s" % warning, file=sys.stderr)
    problems = []
    if len(records) < MIN_OFFICIALS:
        problems.append("%d officials < floor %d" % (len(records), MIN_OFFICIALS))
    if seats < MIN_SEATS:
        problems.append("%d council seats < floor %d" % (seats, MIN_SEATS))
    if not any((r["office"] or "").lower() == "mayor" for r in records):
        problems.append("no mayor in the elected-officials category")
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

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
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped Freeport: %d officials (%d council seats, %d with e-mail, "
          "%d with a phone) -> %s"
          % (len(records), seats, sum(1 for r in records if r["person_email"]),
             sum(1 for r in records if r["person_phone"]), args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
