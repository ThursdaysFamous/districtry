#!/usr/bin/env python3
"""
Scrape Grundy County's own board page into raw roster records.

Stage 1 of the two-stage pipeline (scripts/build_grundy_board_roster.py is
stage 2). The county's revize-CMS directory lists all EIGHTEEN members — six
per district across three districts — one <h2> block each, with a
description line "Party, Board Member Since YYYY, District N", a committee
list (as <li> items or &bull; lines; per-committee Chair/Vice-Chair suffixes
ride the item text verbatim), a tel: phone link and a mailto: e-mail link.
The Board Chairman is stated as his own list item ("County Board Chairman"
on Drew Muffler's row) — read, never inferred.

FETCH POSTURE: open. Plain server-rendered HTML.

Usage:
    python3 grundy_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_COMPACT,
    require_robots_once,
)

LIST_URL = "https://www.grundycountyil.gov/government/county_board.php"
UA = {"User-Agent": UA_ROSTER_COMPACT}

# "Democrat, Board Member Since 2005, District 3" — with the page's own
# variance absorbed: a missing space after the party comma (Harold Vota) and
# a lowercase "since" (Nathanael Greene).
HEAD_RE = re.compile(
    r"(Democrat|Republican|Independent\w*)\s*,\s*Board Member [Ss]ince\s+(\d{4})\s*,"
    r"\s*District\s+(\d)")
DESC_RE = re.compile(r'class="rz-business-desc">(.*?)</span>', re.S)
LI_RE = re.compile(r"<li>(.*?)</li>", re.S)
BULL_RE = re.compile(r"&bull;((?:\s|&nbsp;)*[^<]+)")
TEL_RE = re.compile(r'href="tel:(\d{10})"')
MAILTO_RE = re.compile(r'href="mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"')
CHAIRMAN_ITEM = "County Board Chairman"


def clean_item(s):
    s = html_mod.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).replace("\xa0", " ").strip()


def main():
    require_robots_once(LIST_URL, UA["User-Agent"], headers=UA,
                        label="il-grundy-county-board-scraper")
    r = requests.get(LIST_URL, headers=UA, timeout=60)
    r.raise_for_status()

    records = []
    for chunk in r.text.split("<h2>")[1:]:
        name = clean_item(chunk.split("</h2>")[0])
        desc_m = DESC_RE.search(chunk)
        if not name or not desc_m:
            continue
        desc = desc_m.group(1)
        head = HEAD_RE.search(clean_item(desc))
        items = [clean_item(x) for x in LI_RE.findall(desc)]
        items += [clean_item(x) for x in BULL_RE.findall(desc)]
        items = [x for x in items if x]
        role = None
        if CHAIRMAN_ITEM in items:
            role = "Chairman"
            items = [x for x in items if x != CHAIRMAN_ITEM]
        tel = TEL_RE.search(chunk)
        mail = MAILTO_RE.search(chunk)
        records.append({
            "name": name,
            "party": head.group(1) if head else None,
            "since": int(head.group(2)) if head else None,
            "district": int(head.group(3)) if head else None,
            "role": role,
            "committees": items,
            "phone": ("(%s) %s-%s" % (tel.group(1)[:3], tel.group(1)[3:6],
                                      tel.group(1)[6:])) if tel else None,
            "email": mail.group(1).lower() if mail else None,
        })

    if not records:
        print("grundy-board-scraper: FAIL — zero rows parsed from %s (markup change?)"
              % LIST_URL, file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": LIST_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("grundy-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
