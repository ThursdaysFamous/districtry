#!/usr/bin/env python3
"""
Scrape the 51 NYC City Council members from council.nyc.gov/districts/
(METRO_EXPANSION_PLAYBOOK §9). Stage 1 of the pipeline.

Note on source: the playbook named Legistar's People.aspx, but its "Web Site"
column (the only place the district number appears) is populated for only ~24 of
51 members. council.nyc.gov/districts/ lists all 51 with the member name in each
district card's photo alt text and the district number in the card's URL, so it
is the complete, reliable source. Writes an intermediate JSON with source_url +
scraped_at; build_council_roster.py resolves it into data/app/council-members.json.

Usage:
    python3 scripts/council_scraper.py [--out PATH]
"""

import json
import os
import re
import sys
import time
import urllib.request

URL = "https://council.nyc.gov/districts/"
UA = "Mozilla/5.0 (compatible; districtry-nyc/1.0; +https://districtry.com/ny/)"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "council_raw.json")


def clean_name(alt):
    # photo alts read "Christopher Marte Head Shot" / "... Headshot" / "... Photo"
    name = re.sub(r"\s*(head\s*shot|headshot|photo|portrait)\s*$", "", alt, flags=re.I).strip()
    return name or None


# The District Office block on a council district page runs into a second
# ("Legislative Office") address, a phone/fax number or label, and assorted
# contact boilerplate. OFFICE_END marks where the street address ends. The old
# regex instead ran to the first "..., NY 1XXXX" ZIP, which bled through every
# page whose district office omits the ZIP (D2), drops "NY" (D43 "Brooklyn
# 11204"), spells out the state (D14 "Bronx, New York 10453"), or lists no
# street at all (D48) — swallowing the phone, fax, and the whole Legislative
# Office address into one run-on line.
OFFICE_END = re.compile(
    r"(?:"
    r"\bLegislative\s+Office\b"
    r"|\bSend\s*Email\b|\bEmail\b"
    r"|\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"   # a phone / fax number, anywhere
    r"|\bTelephone\b|\bPhone\b|\bFax\b|\bTel\b"
    r")", re.I)
# A NYC ZIP (all five digits, "1XXXX"). Used to end the address at its own ZIP so
# a trailing parenthetical or note (D17 "(Intersection…)", D40 "If you need…")
# doesn't ride along, and a page-typo sixth digit (D4 "100170") is dropped.
ZIP_RE = re.compile(r"1\d{4}")


def district_office(url):
    """Extract the clean 'District Office' street address from a member's page.

    Returns None (never a guess) when the page lists no street address — e.g.
    District 48, whose District Office block is a phone number only.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — the office is an enhancement, never fatal
        return None
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    m = re.search(r"District Office\s+(.+)", text)
    if not m:
        return None
    tail = m.group(1)
    # 1) Bound the block before the phone/fax/second-office noise, so the ZIP we
    #    key off next is the district office's own — never the Legislative one's.
    end = OFFICE_END.search(tail)
    if end:
        tail = tail[:end.start()]
    # 2) If that block carries a ZIP, end the address right after it.
    z = ZIP_RE.search(tail)
    if z:
        tail = tail[:z.end()]
    addr = re.sub(r"\s{2,}", " ", tail).strip(" ,;.-")
    # A real street address carries a house number and a street name; reject a
    # bare phone number or stray fragment so the card never shows contact noise.
    if len(addr) < 6 or not re.search(r"\d", addr) or not re.search(r"[A-Za-z]{3}", addr):
        return None
    return addr


def parse(html):
    parts = re.split(r'href="https://council\.nyc\.gov/district-(\d+)/"', html)
    roster = {}
    for i in range(1, len(parts) - 1, 2):
        num = str(int(parts[i]))
        seg = parts[i + 1][:1500]
        name = None
        for alt in re.findall(r'alt="([^"]+)"', seg):
            alt = alt.strip()
            if alt and not re.search(r"email|phone|address|logo|icon|seal", alt, re.I):
                name = clean_name(alt)
                if name:
                    break
        if name and num not in roster:
            roster[num] = name
    return roster


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    roster = parse(html)
    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    records = {}
    for district, name in roster.items():
        url = "https://council.nyc.gov/district-%s/" % district
        records[district] = {
            "name": name,
            "office": district_office(url),  # None if the page omits it — never guessed
            "source_url": url,
            "scraped_at": scraped_at,
        }
        time.sleep(0.2)  # courteous to council.nyc.gov across 51 pages

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"members": records}, f, indent=2, ensure_ascii=False)
    print("wrote %s: %d council members" % (out_path, len(records)), file=sys.stderr)


if __name__ == "__main__":
    main()
