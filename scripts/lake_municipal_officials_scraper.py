#!/usr/bin/env python3
"""
Lake County Municipal Contact Scraper (County GIS Municipalities service)
========================================================================
Extracts every Lake County municipality's hall address, phone, e-mail, and
official website from the county's own Municipalities feature service.

WHY THIS SHIPS NO NAMES — the rule-4 honesty floor
--------------------------------------------------
Lake County publishes NO municipal officeholder roster anywhere county-side.
Verified twice (2026-07-27): the county/Clerk site's elected-officials pages
cover only the 19 county board members and 8 countywide officers; Lake County
GIS has no officials dataset and no municipal ward layers; and the Lake County
Municipal League publishes no member-municipality directory. That is a firm
negative finding, not an unexplored gap.

So this county takes rung 4 of the source ladder
(docs/EXPANSION_GUIDE.md §3.4): the card answers WHICH municipality
governs the point, WHERE its hall is, HOW to reach it, and links the
municipality's own site — and names nobody, because no verifiable county
source names anyone. Every record here carries `name: null` deliberately; the
builder turns that into a contact-only entry (depth 0), which loses to any
county that publishes a head or a board for the same cross-county
municipality.

Upgrading this county means either a Lake source starting to publish a roster,
or a deliberate decision to scrape 50+ heterogeneous municipal sites — which
the ladder explicitly rejects as a source of record.

The service is open ArcGIS REST (no key, no bot wall). TYPE 'I' is an
incorporated municipality; the single 'U' row is the county's unincorporated
remainder polygon and is excluded — an unincorporated point must keep the
app's honest identity-only card, never a "government" entry.

Usage:
    python3 lake_municipal_officials_scraper.py --out lake_municipal_officials.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
- Contact is MUNICIPALITY-level, emitted under the municipality.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_124  # noqa: E402  (shared machinery — do not fork)

SERVICE_URL = (
    "https://services3.arcgis.com/HESxeTbDliKKvec2/arcgis/rest/services"
    "/Municipalities/FeatureServer/0"
)
QUERY_URL = SERVICE_URL + "/query"
# Human-facing provenance for the card's source link.
DIRECTORY_URL = "https://data-lakecountyil.opendata.arcgis.com/"

HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
}
REQUEST_TIMEOUT = 90

OUT_FIELDS = "ORG_NAME,NAME,TYPE,ADDR,ADDR2,CITY,ZIP,PHONE,EMAIL,URL"
INCORPORATED = "I"

# Deliberate under-tolerance against the verified 2026-07 live value (55
# incorporated rows — more than the 52 Census places that touch Lake, because
# the county maps every municipality reaching into it).
MIN_MUNICIPALITIES = 48


def fetch_features():
    params = {
        "where": "1=1",
        "outFields": OUT_FIELDS,
        "returnGeometry": "false",
        "f": "json",
    }
    require_robots_once(QUERY_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-lake-municipal-officials-scraper")
    resp = requests.get(QUERY_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    # An ArcGIS error is served as HTTP 200 with an error body — treat it as a
    # failed fetch, never as an empty roster (docs/EXPANSION_GUIDE.md §6.3).
    if isinstance(payload, dict) and payload.get("error"):
        print("FATAL: service returned an error body: %s" % payload["error"], file=sys.stderr)
        sys.exit(1)
    features = (payload or {}).get("features")
    if not isinstance(features, list) or not features:
        print("FATAL: no features returned from %s — service shape changed" % QUERY_URL,
              file=sys.stderr)
        sys.exit(1)
    return [f.get("attributes") or {} for f in features]


def clean(value):
    """Trim to a real value or None. The service pads empties with a space."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text or text in {"0", "-"}:
        return None
    return text


def clean_phone(value):
    """"(847) 395-1000" -> "847-395-1000"; anything else is left alone."""
    text = clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return text
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def street_of(attrs):
    line1 = clean(attrs.get("ADDR"))
    line2 = clean(attrs.get("ADDR2"))
    if line1 and line2:
        return "%s, %s" % (line1, line2)
    return line1 or line2


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="lake_municipal_officials.json")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    features = fetch_features()

    records = []
    for attrs in features:
        if clean(attrs.get("TYPE")) != INCORPORATED:
            continue
        jurisdiction = clean(attrs.get("ORG_NAME")) or clean(attrs.get("NAME"))
        if not jurisdiction:
            continue
        records.append({
            "jurisdiction": jurisdiction,
            # No county source names Lake's municipal officers — see the module
            # docstring. This null is the finding, not a parse failure.
            "office": None,
            "district": None,
            "name": None,
            "office_address": street_of(attrs),
            "office_city": clean(attrs.get("CITY")),
            "office_state": "IL" if clean(attrs.get("CITY")) else None,
            "office_zip": clean(attrs.get("ZIP")),
            "office_phone": clean_phone(attrs.get("PHONE")),
            "office_email": clean(attrs.get("EMAIL")),
            "website": clean(attrs.get("URL")),
            "source_url": SERVICE_URL,
            "scraped_at": scraped_at,
        })

    if len(records) < MIN_MUNICIPALITIES:
        print("FATAL: parsed %d municipalities (expected >= %d) — partial response"
              % (len(records), MIN_MUNICIPALITIES), file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Lake",
        "directory_url": DIRECTORY_URL,
        "scraped_at": scraped_at,
        "officials": records,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    with_phone = sum(1 for r in records if r["office_phone"])
    with_url = sum(1 for r in records if r["website"])
    print("scraped %d municipalities (contact only — Lake publishes no officeholder "
          "names): %d with phone, %d with website -> %s"
          % (len(records), with_phone, with_url, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
