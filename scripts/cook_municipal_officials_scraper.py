#!/usr/bin/env python3
"""
Suburban Cook County Municipal Officials Scraper (County Clerk DOEO API)
=======================================================================
Extracts every suburban Cook municipality's governing body — village
president / mayor, trustees, ward alderpersons, clerk, treasurer — from the
Cook County Clerk's own Directory of Elected Officials.

Why this source: the Clerk's DOEO web app
(cookcountyclerkil.gov/elections/directory-elected-officials) is backed by an
open, unauthenticated JSON API on the same domain, which is the county's
canonical record of who currently holds each local office. It is the only
verified source covering ALL suburban Cook municipalities with full governing
bodies (not just the mayor) plus office contact — Chicago's own council is
the app's separate `ward` layer, and the county's Socrata copies of this
directory (vw2r-zys4 / jsup-zs8y) have been frozen since 2014, so they are
deliberately NOT used.

Six endpoints, all of them bulk:
  /api/Jurisdiction/GetByJurisdictionType?id=MUNIS      -> 128 of the 129 municipalities
  /api/ElectedOfficial/GetByJurisdictionType?id=MUNIS   -> municipality-wide officers
  /api/ElectedOfficial/GetByJurisdictionType?id=MUNIW   -> ward/district seats
  /api/ElectedOfficial/GetByJurisdictionType?id=CHIWD   -> City of Chicago citywide
  /api/ElectedOfficial/GetByJurisdictionType?id=CHICA   -> Chicago's 50 ward seats
  /api/ElectedOfficial/GetByJurisdictionType?id=TWNSP   -> the 129th: the Town of
     Cicero, which the Clerk files as "Cicero Township" because town and township
     are one coterminous government (see CICERO_JURISDICTION). MUNIS's 128 are
     107 Villages + 21 Cities and not one Town — Cicero was silently absent from
     this roster until 2026-08-19 because nothing read the township type. The
     same feed carries every OTHER Cook township's governing officials
     (Supervisor/Clerk/Assessor/Trustees/Highway Commissioner), which ride the
     payload raw as `township_officials` for build_township_officials.py — the
     township-card roster (a Part 5 concept, 2026-08-19).
MUNIW's `Jurisdiction` carries the seat's district inline ("City of Berwyn,
Ward 1"), which is parsed out here so the ward-boundary layer can join later
without a re-scrape.

CHICAGO (jurisdiction type CHIWD) closes the suburban-parity asymmetry the
guidebook recorded: a Berwyn click named its mayor while a Chicago click named
nobody. The directory covers all of Cook — only its address SEARCH is
suburban-only — and publishes Chicago's three citywide elected officers (Mayor,
City Clerk, City Treasurer) with the same contact and term fields as every
suburb.

Chicago's 50 ward seats are a SEPARATE type (CHICA), scraped here for ONE
reason: the term fields. The `ward` layer names the alderperson from the City's
own live roster (htai-wnw4), which carries contact but publishes no term data
at all, so the Clerk is the only verified source for when a Chicago ward seat
is next on the ballot. These records still carry `ward_seats_elsewhere` — the
builder turns that into the Municipality card's "elected by ward" pointer, so
the 50 names appear on the Ward card and never swamp the Municipality card.
Their `Jurisdiction` is "Chicago, 1st Ward" (ordinal-first, and without the
legal form CHIWD spells out), so it is normalized to "City of Chicago" +
"Ward 1" to group with the citywide records and match every other seat's
district wording. This is the API's own structure, not an inference.

Library Trustees are excluded: they sit on library district boards (the app's
separate `library-district` layer), not the municipal governing body. They are
distinguishable structurally as well as by office name — their sole address
carries AddressTypeId 4 (library) rather than 3 (village/city hall).

The site is Cloudflare-fronted. Plain requests with a browser User-Agent is
the verified-working rung (2026-07); --engine playwright is available if that
tightens, matching the ladder in cpd_district_scraper.py.

This is the build-time half of the usual two-stage roster pattern; the raw
output is resolved into data/app/municipal-officials.json by
scripts/build_municipal_officials_roster.py.

Usage:
    python3 cook_municipal_officials_scraper.py --out cook_municipal_officials.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
- Contact fields (phone/email/address/website) are MUNICIPALITY-level in this
  source — every official of a municipality carries the same village-hall
  values, and the per-person PersonPhone/PersonEmail columns are empty for all
  1,134 records. They are emitted under the municipality, never as a person's
  own contact, so the card cannot imply a direct line that does not exist.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_124  # noqa: E402  (shared machinery — do not fork)

BASE = "https://www.cookcountyclerkil.gov/api"
JURISDICTIONS_URL = BASE + "/Jurisdiction/GetByJurisdictionType?id=MUNIS&language=en"
OFFICIALS_URL = BASE + "/ElectedOfficial/GetByJurisdictionType?id=MUNIS&language=en"
WARD_OFFICIALS_URL = BASE + "/ElectedOfficial/GetByJurisdictionType?id=MUNIW&language=en"
CHICAGO_OFFICIALS_URL = BASE + "/ElectedOfficial/GetByJurisdictionType?id=CHIWD&language=en"
CHICAGO_WARD_OFFICIALS_URL = BASE + "/ElectedOfficial/GetByJurisdictionType?id=CHICA&language=en"
TOWNSHIP_OFFICIALS_URL = BASE + "/ElectedOfficial/GetByJurisdictionType?id=TWNSP&language=en"
# CHICA names the jurisdiction per seat ("Chicago, 1st Ward"); the citywide
# type spells out the legal form ("City of Chicago"). Group them under the
# latter so both land in one roster entry, on the GEOID the app joins.
CHICAGO_JURISDICTION = "City of Chicago"
# THE ONE MUNICIPALITY THE CLERK FILES AS A TOWNSHIP. The Town of Cicero
# (~85,000 residents, Cook's sixth-largest municipality) appears NOWHERE in
# MUNIS — the Clerk's directory files it under jurisdiction type TWNSP as
# "Cicero Township", because Cicero is an incorporated TOWN coterminous with
# its township: one government, whose President, Clerk and Trustees the
# directory lists beside the township offices (Supervisor, Assessor,
# Collector) under a single jurisdiction (code CICTW). Verified 2026-08-19
# three ways: MUNIS's 128 entries are 107 Villages + 21 Cities and no Towns;
# TWNSP's Cicero records match the town's own officials page
# (thetownofcicero.com/government/town-officials/) name for name, office for
# office, exactly 4 trustees on both; and Cicero is the ONLY township in the
# feed carrying a President — everywhere else the executive is a Supervisor.
# The override renames the jurisdiction to the legal form the Census and the
# town itself use, which is what the builder's GEOID join (-> 1714351)
# resolves; jurisdiction_override exists for exactly this normalization (see
# its comment), and "Town of Cicero" is the government's own published name,
# not an invention.
CICERO_API_JURISDICTION = "Cicero Township"
CICERO_JURISDICTION = "Town of Cicero"
# The offices that ARE the town's government, in card order (head first).
# An include list rather than an exclude list, deliberately: the other TWNSP
# offices are either party posts or another body's board (below), and a new
# office appearing on Cicero should get a human look before it ships — it is
# WARNED about, never silently carried or silently dropped.
CICERO_OFFICES = ("President", "Trustee", "Clerk", "Supervisor", "Assessor",
                  "Collector", "Treasurer")
# Democratic/Republican Township Committeeperson are PARTY offices, not the
# governing body — and their directory records are the one place this API
# carries personal contact (a gmail/yahoo in Addresses[0].Email where every
# government record carries the town hall block), so excluding them is a
# privacy guard as well as a scope call. Library Trustees sit on the library
# board, not the corporate authorities — they ship on the library-district
# card via build_cicero_library_trustees.py, from this same fetch.
CICERO_EXCLUDED_OFFICES = {"Democratic Township Committeeperson",
                           "Republican Township Committeeperson",
                           "Library Trustee"}
DIRECTORY_URL = "https://www.cookcountyclerkil.gov/elections/directory-elected-officials"

HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
    "Accept": "application/json, text/plain, */*",
}
REQUEST_TIMEOUT = 60

# Library district boards are a different body on a different layer.
EXCLUDED_OFFICES = {"Library Trustee"}
# The one head-of-government office per municipality (villages elect a
# President, cities a Mayor). Verified 2026-07: exactly one per municipality
# across all 128.
HEAD_OFFICES = {"Mayor", "President"}

# Minimums that prove the fetch returned the whole directory rather than a
# truncated or challenge-page response. Deliberate under-tolerances against
# the 2026-07 live values (128 municipalities / 879 governing records / 156
# ward seats) — a real shrink still fails, normal turnover does not.
MIN_JURISDICTIONS = 120
MIN_OFFICIALS = 800
MIN_WARD_OFFICIALS = 140
# Chicago publishes exactly three citywide elected officers (Mayor, Clerk,
# Treasurer). A shrink here means the type stopped carrying them.
MIN_CHICAGO_OFFICIALS = 3
# Chicago has 50 wards, and the whole council is elected on one cycle, so this
# type is either complete or broken. The county-wide `members` floor can't
# catch a loss here — 50 seats out of ~1,085 stays above it — so this is the
# guard that does.
MIN_CHICAGO_WARD_OFFICIALS = 45
# Cicero's government is President + Clerk + Supervisor + Assessor +
# Collector + 4 Trustees = 9 records (live 2026-08-19). One vacancy must not
# freeze the whole Cook refresh (this floor failing fails the entire scrape,
# which the workflow turns into the standing Cook issue), so it sits one
# under — but a collapse to a couple of records means the TWNSP feed or the
# filter broke, and the shipped roster should stand.
MIN_CICERO_OFFICIALS = 8
# The whole TWNSP feed: 30 jurisdictions x (governing offices + 2 party
# committeepersons) + Cicero's library board = 284 records live 2026-08-19.
# build_township_officials.py consumes it raw and carries its own per-office
# and per-township guards; this floor only proves the fetch returned the
# whole type rather than a truncated response.
MIN_TOWNSHIP_RECORDS = 250


def fetch_json_requests(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-cook-municipal-officials-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_json_playwright(url):
    """Escalation rung: run the request inside a real browser context.

    Only needed if Cloudflare starts challenging plain clients; the API is
    same-origin to the directory page, so a browser fetch() inherits the
    clearance cookie the page load earns.
    """
    require_robots_once(DIRECTORY_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-cook-municipal-officials-scraper")
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-cook-municipal-officials-scraper")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(DIRECTORY_URL, wait_until="domcontentloaded", timeout=90000)
            payload = page.evaluate(
                "async (u) => { const r = await fetch(u, "
                "{headers: {'Accept': 'application/json'}}); "
                "if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); }",
                url,
            )
        finally:
            browser.close()
    return json.loads(payload)


def fetch_json(url, engine):
    if engine == "playwright":
        return fetch_json_playwright(url)
    if engine == "requests":
        return fetch_json_requests(url)
    # auto: cheapest rung that works
    try:
        return fetch_json_requests(url)
    except Exception as exc:  # noqa: BLE001 - any transport/challenge failure escalates
        print("requests rung failed for %s (%s) — escalating to playwright" % (url, exc),
              file=sys.stderr)
        return fetch_json_playwright(url)


def envelope_data(payload, url):
    """The API wraps every response as {status, message, data:[...]}."""
    if isinstance(payload, dict) and "data" in payload:
        if payload.get("status") is False:
            print("FATAL: API reported failure for %s: %s"
                  % (url, payload.get("message")), file=sys.stderr)
            sys.exit(1)
        data = payload["data"]
    else:
        data = payload
    if not isinstance(data, list):
        print("FATAL: expected a list of records from %s — response shape changed" % url,
              file=sys.stderr)
        sys.exit(1)
    return data


def clean(value):
    """Trim to a real value or None — never an empty string, never a guess."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def full_name(rec):
    first = clean(rec.get("FirstName"))
    nickname = clean(rec.get("Nickname"))
    parts = [first]
    # A nickname stands in for the given name, so it reads after it —
    # 'Theodore J. "Teddy" Polashek', not 'Theodore J. Polashek "Teddy"'.
    if nickname and first and nickname.lower() != first.lower():
        parts.append('"%s"' % nickname)
    elif nickname and not first:
        parts.append('"%s"' % nickname)
    parts.extend([clean(rec.get("MiddleName")), clean(rec.get("LastName"))])
    name = " ".join(p for p in parts if p)
    suffix = clean(rec.get("Suffix"))
    if suffix:
        name = "%s %s" % (name, suffix)
    return name or None


def primary_address(rec):
    addresses = rec.get("Addresses") or []
    if not addresses:
        return {}
    addr = addresses[0]
    street = clean(addr.get("Address1"))
    line2 = clean(addr.get("Address2"))
    if street and line2:
        street = "%s, %s" % (street, line2)
    return {
        "address": street,
        "city": clean(addr.get("City")),
        "state": clean(addr.get("State")),
        "zip": clean(addr.get("Zip")),
        "phone": clean(addr.get("Phone")) or clean(rec.get("Phone")),
        "email": clean(addr.get("Email")) or clean(rec.get("Email")),
        "website": clean(addr.get("URL")),
        "address_type_id": addr.get("AddressTypeId"),
    }


def split_ward_jurisdiction(jurisdiction):
    """Split a seat's jurisdiction into (municipality, district).

    Two wordings in this API, both normalized to the "Ward 1" form the rest of
    the pipeline and the app's ward join expect:
      "City of Berwyn, Ward 1"  -> ("City of Berwyn", "Ward 1")   [MUNIW]
      "Chicago, 1st Ward"       -> ("Chicago", "Ward 1")          [CHICA]
    """
    text = jurisdiction or ""
    ordinal = re.match(r"^(.*?),\s*(\d+)(?:st|nd|rd|th)\s+(Ward|District)\s*$", text, re.I)
    if ordinal:
        return clean(ordinal.group(1)), "%s %s" % (ordinal.group(3).title(), ordinal.group(2))
    match = re.match(r"^(.*?),\s*((?:Ward|District)\s+.+)$", text)
    if not match:
        return clean(text), None
    return clean(match.group(1)), clean(match.group(2))


def official_record(rec, scraped_at, source_url, ward_seat=False,
                    ward_seats_elsewhere=False, jurisdiction_override=None):
    if ward_seat:
        jurisdiction, district = split_ward_jurisdiction(rec.get("Jurisdiction"))
    else:
        jurisdiction, district = clean(rec.get("Jurisdiction")), None
    # Only where a type names the same municipality differently than the rest
    # of the directory (CHICA's "Chicago" vs "City of Chicago") — never to
    # rename a jurisdiction into one the source didn't publish.
    if jurisdiction_override:
        jurisdiction = jurisdiction_override
    addr = primary_address(rec)
    return {
        "jurisdiction": jurisdiction,
        "office": clean(rec.get("Office")),
        "district": district,
        "name": full_name(rec),
        "appointed": bool(rec.get("Appointed")),
        "last_elected": clean(rec.get("LastElected")),
        "next_election": clean(rec.get("NextElection")),
        # Municipality-level contact — see the module docstring.
        "office_address": addr.get("address"),
        "office_city": addr.get("city"),
        "office_state": addr.get("state"),
        "office_zip": addr.get("zip"),
        "office_phone": addr.get("phone"),
        "office_email": addr.get("email"),
        "website": addr.get("website"),
        "address_type_id": addr.get("address_type_id"),
        # True where this API publishes the jurisdiction's legislative seats
        # under a different type (Chicago: citywide CHIWD vs ward CHICA), so
        # the card points at the Ward layer instead of implying no council.
        "ward_seats_elsewhere": ward_seats_elsewhere,
        "source_url": source_url,
        "scraped_at": scraped_at,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="cook_municipal_officials.json")
    parser.add_argument("--engine", choices=("auto", "requests", "playwright"),
                        default="auto",
                        help="fetch rung; auto tries requests then playwright")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    jurisdictions = envelope_data(fetch_json(JURISDICTIONS_URL, args.engine), JURISDICTIONS_URL)
    officials = envelope_data(fetch_json(OFFICIALS_URL, args.engine), OFFICIALS_URL)
    ward_officials = envelope_data(fetch_json(WARD_OFFICIALS_URL, args.engine), WARD_OFFICIALS_URL)
    chicago_officials = envelope_data(fetch_json(CHICAGO_OFFICIALS_URL, args.engine),
                                      CHICAGO_OFFICIALS_URL)
    chicago_ward_officials = envelope_data(fetch_json(CHICAGO_WARD_OFFICIALS_URL, args.engine),
                                           CHICAGO_WARD_OFFICIALS_URL)
    township_officials = envelope_data(fetch_json(TOWNSHIP_OFFICIALS_URL, args.engine),
                                       TOWNSHIP_OFFICIALS_URL)

    if len(jurisdictions) < MIN_JURISDICTIONS:
        print("FATAL: only %d municipalities returned (expected >= %d) — partial response"
              % (len(jurisdictions), MIN_JURISDICTIONS), file=sys.stderr)
        sys.exit(1)
    if len(officials) < MIN_OFFICIALS:
        print("FATAL: only %d municipal officials returned (expected >= %d) — partial response"
              % (len(officials), MIN_OFFICIALS), file=sys.stderr)
        sys.exit(1)
    if len(ward_officials) < MIN_WARD_OFFICIALS:
        print("FATAL: only %d ward officials returned (expected >= %d) — partial response"
              % (len(ward_officials), MIN_WARD_OFFICIALS), file=sys.stderr)
        sys.exit(1)
    if len(chicago_officials) < MIN_CHICAGO_OFFICIALS:
        print("FATAL: only %d City of Chicago officials returned (expected >= %d)"
              % (len(chicago_officials), MIN_CHICAGO_OFFICIALS), file=sys.stderr)
        sys.exit(1)
    if len(chicago_ward_officials) < MIN_CHICAGO_WARD_OFFICIALS:
        print("FATAL: only %d Chicago ward seats returned (expected >= %d)"
              % (len(chicago_ward_officials), MIN_CHICAGO_WARD_OFFICIALS), file=sys.stderr)
        sys.exit(1)
    if len(township_officials) < MIN_TOWNSHIP_RECORDS:
        print("FATAL: only %d township records returned (expected >= %d) — partial response"
              % (len(township_officials), MIN_TOWNSHIP_RECORDS), file=sys.stderr)
        sys.exit(1)

    # Cicero, out of the township feed — see CICERO_JURISDICTION above. The
    # governing records go FIRST President, then the rest in CICERO_OFFICES
    # order, so the builder's records[0] hall-contact read lands on the head
    # (all nine carry the same town-hall block today; the ordering is
    # determinism, not correctness). Library trustees are carved off for
    # build_cicero_library_trustees.py; anything neither included nor excluded
    # is a new office on the town's ballot and earns a WARN for a human look.
    cicero_all = [rec for rec in township_officials
                  if clean(rec.get("Jurisdiction")) == CICERO_API_JURISDICTION]
    cicero_gov, cicero_library = [], []
    for rec in cicero_all:
        office = clean(rec.get("Office"))
        if office in CICERO_EXCLUDED_OFFICES:
            if office == "Library Trustee":
                cicero_library.append(rec)
            continue
        if office not in CICERO_OFFICES:
            print("WARN: Cicero carries unrecognized office %r (%s) — neither "
                  "included nor excluded; skipped pending a human look"
                  % (office, clean(rec.get("LastName"))), file=sys.stderr)
            continue
        cicero_gov.append(rec)
    cicero_gov.sort(key=lambda r: CICERO_OFFICES.index(clean(r.get("Office"))))
    if len(cicero_gov) < MIN_CICERO_OFFICIALS:
        print("FATAL: only %d Town of Cicero governing records in the TWNSP feed "
              "(expected >= %d) — the township type changed shape, or Cicero "
              "moved; the shipped roster should stand"
              % (len(cicero_gov), MIN_CICERO_OFFICIALS), file=sys.stderr)
        sys.exit(1)

    municipalities = [{
        "tax_code": clean(j.get("TaxCode")),
        "jurisdiction_code": clean(j.get("JurisdictionCode")),
        "name": clean(j.get("LongDescription")) or clean(j.get("ShortDescription")),
        "source_url": JURISDICTIONS_URL,
        "scraped_at": scraped_at,
    } for j in jurisdictions]

    records = []
    for rec in officials:
        if clean(rec.get("Office")) in EXCLUDED_OFFICES:
            continue
        records.append(official_record(rec, scraped_at, OFFICIALS_URL))
    for rec in ward_officials:
        if clean(rec.get("Office")) in EXCLUDED_OFFICES:
            continue
        records.append(official_record(rec, scraped_at, WARD_OFFICIALS_URL, ward_seat=True))
    for rec in chicago_officials:
        if clean(rec.get("Office")) in EXCLUDED_OFFICES:
            continue
        records.append(official_record(rec, scraped_at, CHICAGO_OFFICIALS_URL,
                                       ward_seats_elsewhere=True))
    # After the citywide records, deliberately: the builder takes a
    # municipality's office block and website from its FIRST record, and City
    # Hall belongs on the Municipality card, not a ward office.
    for rec in chicago_ward_officials:
        if clean(rec.get("Office")) in EXCLUDED_OFFICES:
            continue
        records.append(official_record(rec, scraped_at, CHICAGO_WARD_OFFICIALS_URL,
                                       ward_seat=True, ward_seats_elsewhere=True,
                                       jurisdiction_override=CHICAGO_JURISDICTION))
    for rec in cicero_gov:
        records.append(official_record(rec, scraped_at, TOWNSHIP_OFFICIALS_URL,
                                       jurisdiction_override=CICERO_JURISDICTION))

    payload = {
        "county": "Cook",
        "directory_url": DIRECTORY_URL,
        "scraped_at": scraped_at,
        "municipalities": municipalities,
        "officials": records,
        # Raw API records, deliberately: build_cicero_library_trustees.py is
        # their only consumer and does its own field selection + guards there.
        "cicero_library_trustees": cicero_library,
        # The whole TWNSP feed, also raw and for the same reason:
        # build_township_officials.py is its only consumer and carries the
        # office include-list, the committeeperson/privacy exclusions, the
        # AddressTypeId assertion and the GEOID join itself.
        "township_officials": township_officials,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    heads = sum(1 for r in records if r["office"] in HEAD_OFFICES)
    seats = sum(1 for r in records if r["district"])
    chicago = sum(1 for r in records if r["ward_seats_elsewhere"])
    chicago_wards = sum(1 for r in records
                        if r["ward_seats_elsewhere"] and r["district"])
    print("scraped %d municipalities + the Town of Cicero, %d governing-body "
          "officials (%d heads of government, %d ward/district seats, "
          "%d Chicago records of which %d ward seats, %d Cicero + %d library "
          "trustees) -> %s"
          % (len(municipalities), len(records), heads, seats,
             chicago, chicago_wards, len(cicero_gov), len(cicero_library),
             args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
