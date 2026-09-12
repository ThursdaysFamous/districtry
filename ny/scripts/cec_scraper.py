#!/usr/bin/env python3
"""
Scrape Community Education Council (CEC) members from schools.nyc.gov
(METRO_EXPANSION_PLAYBOOK §9, §6c). Stage 1 of the pipeline.

CEC = the parent-elected councils, one per community school district (1–32).
Each council's "Current Members" page lists ~9–11 members. schools.nyc.gov is
WAF-sensitive, so this uses Playwright (a real browser) per §6c "Playwright from
day one". The DOE occasionally reorganizes these pages, so the council-page URL
map (COUNCIL_URLS) is intended to be confirmed/adjusted by the operator on first
run. NOTE (2026): the DOE decentralized CEC member listings across 32
independent council sites (cec3.org, cec14.org, DOE Google Sites, ...) with no
uniform URL and no NYC Open Data dataset, so the discovery walk below finds
nothing and build_cec_roster.py keeps the empty
placeholder (the CEC card degrades to the council page and names no one — never
guessed). Writes an intermediate JSON with source_url + scraped_at per member.

Usage:
    python3 scripts/cec_scraper.py [--out PATH]        # needs playwright + chromium
"""

import json
import os
import re
import sys
import time

DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "cec_raw.json")
# Landing page listing the 32 district councils; the scraper follows each
# council's "Current Members" link from here. Operator: confirm this resolves.
INDEX_URL = "https://www.schools.nyc.gov/get-involved/families/education-councils/community-education-councils/cec"
UA = "Mozilla/5.0 (compatible; districtry-nyc/1.0; +https://districtry.com/ny/)"


def scrape():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; CEC scrape skipped (empty placeholder kept).", file=sys.stderr)
        return {}

    councils = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(user_agent=UA).new_page()
        try:
            page.goto(INDEX_URL, wait_until="domcontentloaded", timeout=45000)
            # collect links that look like a per-district CEC council page
            hrefs = page.eval_on_selector_all(
                "a[href*='community-education-council'], a[href*='cec']",
                "els => els.map(e => e.href)",
            )
            seen = set()
            for href in hrefs:
                m = re.search(r"(?:council|cec)[-_ ]?(\d{1,2})\b", href, re.I)
                if not m:
                    continue
                district = str(int(m.group(1)))
                if district in seen or not (1 <= int(district) <= 32):
                    continue
                seen.add(district)
                try:
                    page.goto(href, wait_until="domcontentloaded", timeout=45000)
                    text = page.inner_text("body")
                except Exception:
                    continue
                # members typically appear under a "Current Members" heading
                members = []
                block = text.split("Current Members", 1)[-1] if "Current Members" in text else ""
                for line in block.splitlines():
                    line = line.strip()
                    # a plausible "Firstname Lastname[, Role]" line
                    if re.match(r"^[A-Z][A-Za-z.'\-]+ [A-Z][A-Za-z.'\- ]+$", line) and len(line) <= 60:
                        members.append({"name": line})
                    if len(members) >= 15:
                        break
                if members:
                    councils[district] = {"members": members, "source_url": href}
        finally:
            browser.close()
    return councils


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT
    councils = scrape()
    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for c in councils.values():
        for m in c["members"]:
            m["scraped_at"] = scraped_at
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"councils": councils}, f, indent=2, ensure_ascii=False)
    print("wrote %s: %d councils with members" % (out_path, len(councils)), file=sys.stderr)


if __name__ == "__main__":
    main()
