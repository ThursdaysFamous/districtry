#!/usr/bin/env python3
"""
Scrape Iroquois County's board roster into raw board-roster records.

Stage 1 of the two-stage pipeline (scripts/build_iroquois_board_roster.py is
stage 2). The county publishes its board as ONE table with a header row the
parse keys on — Name / District / Home Town / Phone / Term Expires / E-Mail —
sixteen members across four districts, four each. A short leadership table
above it names the Chairman and Vice Chairman, both of whom also hold a
district seat, so their roles are attached to their own district rows rather
than becoming separate entries.

Two source quirks the parse handles:

  * DISTRICTS ARE ROMAN NUMERALS ("III", "IV") while the county's GIS keys its
    board polygons by INTEGER, so the join would silently find nothing without
    a conversion. Only I-IV are accepted; anything else fails the build rather
    than guessing.
  * E-MAILS ARE CLOUDFLARE-OBFUSCATED — the address is not in the markup at
    all, only a hex `data-cfemail` blob whose first byte is an XOR key. That is
    a scraping-deterrence measure on a PUBLICLY PUBLISHED contact, not an
    access control: the county prints these addresses for residents to use, and
    every visitor's browser performs exactly this decode on page load.

FETCH POSTURE: apex domain only, with a browser User-Agent. The `www.` host
403s and the bare default UA is refused; neither is a hard block.

Usage:
    python3 iroquois_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_X11_128,
    require_robots_once,
)

SOURCE_URL = "https://iroquoiscountyil.gov/offices/county-board"
UA = {"User-Agent": UA_CHROME_X11_128}

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}
ROLE_RE = re.compile(r"^(Chairman|Vice\s*-?\s*Chairman)$", re.I)
PHONE_RE = re.compile(r"(\d{3})\D{0,3}(\d{3})\D?(\d{4})")


def clean(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(
        re.sub(r"(?s)<[^>]+>", " ", fragment or ""))).strip()


def cf_decode(blob):
    """Cloudflare e-mail obfuscation: hex bytes, the first is the XOR key."""
    try:
        data = bytes.fromhex(blob)
    except ValueError:
        return None
    if len(data) < 2:
        return None
    key = data[0]
    try:
        addr = "".join(chr(b ^ key) for b in data[1:])
    except ValueError:
        return None
    return addr if re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", addr) else None


def cell_email(cell_html):
    m = re.search(r'data-cfemail="([0-9a-fA-F]+)"', cell_html)
    if m:
        return (cf_decode(m.group(1)) or "").lower() or None
    m = re.search(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", cell_html)
    return m.group(1).lower() if m else None


def normalize_phone(raw):
    m = PHONE_RE.search(raw or "")
    if not m:
        return None
    return "-".join(m.groups())


def tidy_name(raw):
    """The table prints "Alt , Charles" — surname first, with a stray space
    before the comma. Emit the natural order the cards render."""
    name = re.sub(r"\s+,", ",", clean(raw))
    if "," in name:
        last, first = name.split(",", 1)
        name = "%s %s" % (first.strip(), last.strip())
    return re.sub(r"\s+", " ", name).strip()


def rows_of(page):
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        cells = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)
        yield [clean(c) for c in cells], cells


def main():
    require_robots_once(SOURCE_URL, UA["User-Agent"], headers=UA,
                        label="il-iroquois-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=UA, timeout=60)
    resp.raise_for_status()
    page = resp.text

    roles, records = {}, []
    in_members = False
    for text_cells, raw_cells in rows_of(page):
        if not text_cells:
            continue
        header = [c.lower() for c in text_cells]
        if "district" in header and "name" in header:
            in_members = True
            continue
        if "position" in header and "name" in header:
            in_members = False
            continue
        if not in_members:
            # leadership table: Name | Position | Phone | E-Mail
            if len(text_cells) >= 2 and ROLE_RE.match(text_cells[1]):
                role = "Vice-Chairman" if text_cells[1].lower().startswith("vice") else "Chairman"
                roles[tidy_name(text_cells[0]).lower()] = role
            continue
        if len(text_cells) < 6:
            continue
        name = tidy_name(text_cells[0])
        roman = text_cells[1].strip().upper()
        if not name or roman not in ROMAN:
            continue
        records.append({
            "name": name,
            "district": ROMAN[roman],
            "districtRoman": roman,
            "homeTown": text_cells[2] or None,
            "phone": normalize_phone(text_cells[3]),
            "termExpires": text_cells[4] or None,
            "email": cell_email(raw_cells[5]) if len(raw_cells) > 5 else None,
        })

    for rec in records:
        role = roles.get(rec["name"].lower())
        rec["role"] = role
    unmatched = [n for n in roles if not any(r["name"].lower() == n for r in records)]
    for n in unmatched:
        print("iroquois-board-scraper: WARN — leadership table names %r, who holds "
              "no district seat in the member table" % n, file=sys.stderr)

    if not records:
        print("iroquois-board-scraper: FAIL — zero member rows parsed (markup change?)",
              file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": SOURCE_URL, "records": records},
                     indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("iroquois-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
