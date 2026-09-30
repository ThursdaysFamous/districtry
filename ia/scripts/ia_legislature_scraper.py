#!/usr/bin/env python3
"""
Scrape the Iowa Legislature's own per-legislator profile pages for the
office fields Open States cannot supply. Companion to
build_ia_legislature_roster.py, which merges this enrichment onto its Open
States base.

WHY THIS EXISTS (measured 2026-08-27): the Open States ia.csv carries
capitol_address / capitol_voice / district_address / district_voice EMPTY
for every one of Iowa's current members (sampled) — the upstream YAML has
no offices block for them — while each member's own profile page at
legis.iowa.gov/legislators/legislator?personID=<id> carries a small
label/value table with their Capitol phone and legislative e-mail (and,
for some members, the Capitol's own business address).

UNLIKE WISCONSIN'S SAME-SHAPED SCRAPER, there is no single listing page
carrying every member's contact block — legis.iowa.gov/legislators/senate
and /house are bare name/district/party directories with no office info at
all (measured: grepping the fetched senate listing page for office/phone/
email markup turns up only nav-menu text). Every member needs its OWN page
fetch. The personIDs come from the Open States CSV's own `links` column —
…/legislator?personID=<id> is already one of the URLs Open States lists
for every member — so no separate ID-discovery step is needed.

THE LABEL TEXT IS NOT UNIFORM (measured across a 9-member sample): "Capitol
Phone:" on some pages, "Capitol Office Phone:" on others — the parser
matches on substring ("Phone" / "Email" / "Address" appearing in the
label), never an exact string.

TWO FIELDS ARE REFUSED BY CONSTRUCTION, not filtered afterwards:
"Occupation" (a personal/bio field, not an office fact) and "Service
Began" (a date, not an address/phone/email) appear on some pages and are
never captured — the parser only recognizes Email/Phone/Address-labeled
rows, so an unrecognized label is silently skipped rather than
accidentally published. The "Business Address" field, when present, is
the Capitol's own mailing address (1007 E Grand Ave, Des Moines, IA 50319
— confirmed identical across every member observed carrying it), never a
personal address; Iowa's site does not appear to publish district-office
addresses at all, unlike Wisconsin's — the builder asserts this on the
built payload (see build_ia_legislature_roster.py).
"""

import csv
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(SCRIPT_DIR, ".cache", "ia_legislature_offices.json")
OPEN_STATES_URL = "https://data.openstates.org/people/current/ia.csv"
PROFILE_URL = "https://www.legis.iowa.gov/legislators/legislator?personID=%s"

CHAMBERS = {"upper": 45, "lower": 93}  # floor: min profile pages successfully parsed per chamber

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

ROW_RE = re.compile(
    r"<tr><td class=\"col_1\"><label>([^<]+)</label></td><td>(.*?)</td></tr>", re.S
)


def fetch(url):
    ctx = ssl.create_default_context()
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="ia-ia-legislature-scraper")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return r.read().decode("utf-8", "replace")


def strip_tags(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def person_ids_by_chamber():
    """{chamber: [(district, personID), ...]} from the Open States CSV's own
    links column — no separate listing-page scrape needed."""
    text = fetch(OPEN_STATES_URL)
    rows = list(csv.DictReader(io.StringIO(text)))
    out = {"upper": [], "lower": []}
    for r in rows:
        chamber = (r.get("current_chamber") or "").strip()
        district = (r.get("current_district") or "").strip()
        if chamber not in out or not district:
            continue
        m = re.search(r"personID=(\d+)", r.get("links") or "")
        if m:
            out[chamber].append((district, m.group(1)))
    return out


def parse_profile(html):
    """Return {email, phones, address} from a legislator's profile table.
    Only Email/Phone/Address-labeled rows are ever captured; anything else
    (Occupation, Service Began, ...) is skipped by construction."""
    entry = {}
    for label, value in ROW_RE.findall(html):
        label_l = label.lower()
        text = strip_tags(value)
        if not text:
            continue
        if "email" in label_l:
            m = re.search(r"mailto:([^\"'>]+)", value)
            entry["email"] = m.group(1) if m else text
        elif "phone" in label_l:
            entry.setdefault("phones", []).append(text)
        elif "address" in label_l:
            entry["address"] = text
        # everything else (Occupation, Service Began, ...) is never captured
    return entry


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    ids = person_ids_by_chamber()
    payload = {"upper": {}, "lower": {}}
    for chamber, pairs in ids.items():
        for district, pid in pairs:
            try:
                html = fetch(PROFILE_URL % pid)
            except Exception as exc:
                print("WARNING: personID %s (district %s, %s) fetch failed: %s"
                      % (pid, district, chamber, exc), file=sys.stderr)
                continue
            entry = parse_profile(html)
            if entry:
                payload[chamber][district] = entry
            time.sleep(0.2)  # a polite, serial client against a small state site

    for chamber, floor in CHAMBERS.items():
        n = len(payload[chamber])
        if n < floor:
            raise SystemExit(
                "%s: parsed %d profile pages (floor %d) — the site reshaped, "
                "or too many fetches failed" % (chamber, n, floor)
            )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped offices: senate(upper) %d, house(lower) %d -> %s"
          % (len(payload["upper"]), len(payload["lower"]), out_path))


if __name__ == "__main__":
    main()
