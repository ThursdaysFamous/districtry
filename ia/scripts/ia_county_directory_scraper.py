#!/usr/bin/env python3
"""
Fetch every Iowa county's own official website URL from the Iowa State
Association of Counties' member directory (iowacounties.org), and cache the
result for build_ia_county_board_directory.py.

WHY ISAC AND NOT A GUESSED DOMAIN PATTERN
------------------------------------------
Iowa counties do not share one domain convention: Story and Johnson are
`<name>countyiowa.gov`, Black Hawk is `blackhawkcounty.iowa.gov`, Jones is
`jonescountyiowa.gov`. Guessing a pattern would silently ship a dead or wrong
link for whichever counties don't follow it. ISAC (the counties' own trade
association, https://www.iowacounties.org/) publishes a "County Directory"
with one detail page per county, and each page states the county's own
website under a labelled "Website:" field (verified 2026-08-27 against
Story County's entry: "<b>Website:</b> <a href=...>https://www.storycountyiowa.gov/</a>"),
alongside the courthouse address and supervisor meeting day where published.
This is a single, verifiable, per-county-attributed source rather than a
derived guess.

Usage:
    python3 ia/scripts/ia_county_directory_scraper.py
"""

import json
import os
import re
import sys
import time
import urllib.parse

import requests
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_county_directory.json")

INDEX_URL = "https://www.iowacounties.org/member-resources/county-directory/"
DETAIL_BASE = "https://member-portal.iowacounties.org/countydirectory/directory/"

HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)"}

EXPECT_COUNTIES = 99


def fetch(url):
    require_robots_once(url, HEADERS["User-Agent"],
                        headers=HEADERS, label="ia-ia-county-directory-scraper")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def county_slugs():
    html = fetch(INDEX_URL)
    slugs = sorted(set(re.findall(
        r"https://member-portal\.iowacounties\.org/countydirectory/directory/([A-Za-z0-9%\.\-]+)",
        html,
    )))
    if len(slugs) != EXPECT_COUNTIES:
        raise RuntimeError(
            "ISAC index listed %d county directory slugs, expected %d"
            % (len(slugs), EXPECT_COUNTIES)
        )
    return slugs


WEBSITE_RE = re.compile(r"<b>\s*Website:\s*</b>\s*<a\s+href=\"([^\"]+)\"", re.IGNORECASE)
COURTHOUSE_RE = re.compile(r"<b>\s*([^<]*Courthouse[^<]*)\s*</b>", re.IGNORECASE)
MEETING_RE = re.compile(r"<b>\s*Supervisor Meetings:\s*</b>\s*([^<]+)", re.IGNORECASE)


def parse_detail(html, slug):
    m = WEBSITE_RE.search(html)
    website = m.group(1).strip() if m else None
    courthouse = None
    cm = COURTHOUSE_RE.search(html)
    if cm:
        courthouse = cm.group(1).strip()
    meeting = None
    mm = MEETING_RE.search(html)
    if mm:
        meeting = mm.group(1).strip()
    return {"slug": slug, "website": website, "courthouse_name": courthouse, "supervisor_meetings": meeting}


def main():
    slugs = county_slugs()
    print("ISAC index: %d county directory pages" % len(slugs), file=sys.stderr)

    records = []
    missing = []
    for i, slug in enumerate(slugs):
        url = DETAIL_BASE + slug
        html = fetch(url)
        rec = parse_detail(html, slug)
        county_name = urllib.parse.unquote(slug).replace("%27", "'")
        rec["county_slug_name"] = county_name
        if not rec["website"]:
            missing.append(county_name)
        records.append(rec)
        if (i + 1) % 20 == 0:
            print("  ...%d/%d" % (i + 1, len(slugs)), file=sys.stderr)
        time.sleep(0.15)

    if missing:
        raise RuntimeError(
            "%d of %d ISAC county pages carried no Website: field: %s"
            % (len(missing), len(slugs), missing)
        )

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, indent=1)
    print("wrote %d county website records -> %s" % (len(records), OUT_PATH), file=sys.stderr)


if __name__ == "__main__":
    main()
