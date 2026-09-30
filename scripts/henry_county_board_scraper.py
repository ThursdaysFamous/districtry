#!/usr/bin/env python3
"""
Scrape Henry County's own staff directory into raw board-roster records.

Stage 1 of the two-stage pipeline (scripts/build_henry_board_roster.py is
stage 2). The county's CivicPlus directory publishes the board as two
department listings — "District 1" (DID=39) and "District 2" (DID=40), ten
members each, matching the 20 seats the county board page states. Each
member is a list-group item carrying a name link, a mailto e-mail (direct,
not spam-wrapped — 20/20 published) and, where the member publishes one, a
phone. No role is stated anywhere in the directory — the county elects its
chair from within the body and the listing does not mark who holds it, so
no chair is tagged (the Woodford posture).

The district is the LISTING fetched, not a parsed field — the county keyed
its directory by district, so the assignment is the county's own.

FETCH POSTURE: open, but RATE LIMITED. Plain server-rendered CivicPlus HTML,
no challenge — the county answers a bare client fine. What it does do is throttle:
the first CI run of this workflow (2026-08-02) died on `429 Client Error: Too
Many Requests` against DID=40, the SECOND of the two district listings, having
fetched the first a fraction of a second earlier. A weekly job that gives up the
moment a county's CMS asks it to slow down is a job that fails on the county's
terms rather than its own, so the fetch below backs off and retries, honouring
Retry-After when the server sends one, and paces the two listings apart.

Usage:
    python3 henry_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys
import time

import requests
from scraper_common import require_robots_once, UA_ROSTER_COMPACT, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

DISTRICT_LISTS = {
    1: "https://www.henrycty.com/Directory.aspx?DID=39",
    2: "https://www.henrycty.com/Directory.aspx?DID=40",
}
UA = {"User-Agent": UA_ROSTER_COMPACT}
REQUEST_TIMEOUT = 60
FETCH_ATTEMPTS = 5
# Between the two district listings. Small, but the 429 arrived on back-to-back
# requests, so not zero.
PACING_SECONDS = 2.0


def fetch(url):
    """GET with backoff on throttling — the loop scraper_common.fetch was
    modeled on (the 2026-08-02 back-to-back-429 story), now called from its
    one shared home. 429 and 5xx are retried; a 404 is not — that would be
    the directory moving, which no amount of waiting fixes."""
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="il-henry-county-board-scraper")
    return fetch_with_retry(url, UA, timeout=REQUEST_TIMEOUT,
                            attempts=FETCH_ATTEMPTS).text

NAME_RE = re.compile(
    r'href="/m/directory/employee\?eid=\d+"[^>]*>\s*([^<]+?)\s*</a>')
MAILTO_RE = re.compile(
    r'href="mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"')
PHONE_RE = re.compile(r">\s*(\d{3}-\d{3}-\d{4})\s*<")


def tidy_name(name):
    """Collapse doubled spaces; recase an ALL-CAPS name to title case (two of
    the twenty are published in caps — a data-entry artifact, not a style)."""
    name = re.sub(r"\s+", " ", html_mod.unescape(name)).strip()
    if name and name == name.upper():
        name = " ".join(w.capitalize() for w in name.split(" "))
    return name


def main():
    records = []
    for index, (district, url) in enumerate(sorted(DISTRICT_LISTS.items())):
        if index:
            time.sleep(PACING_SECONDS)
        page = fetch(url)
        for item in page.split('<li class="list-group-item')[1:]:
            item = item.split("</li>")[0]
            nm = NAME_RE.search(item)
            if not nm:
                continue
            em = MAILTO_RE.search(item)
            ph = PHONE_RE.search(item)
            records.append({
                "name": tidy_name(nm.group(1)),
                "district": district,
                "email": em.group(1).lower() if em else None,
                "phone": ph.group(1) if ph else None,
            })

    if not records:
        print("henry-board-scraper: FAIL — zero rows parsed (markup change?)",
              file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": DISTRICT_LISTS[1].split("?")[0],
                      "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("henry-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
