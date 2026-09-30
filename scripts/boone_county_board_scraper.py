#!/usr/bin/env python3
"""
Scrape Boone County's own board page into raw roster records.

Stage 1 of the two-stage pipeline (scripts/build_boone_board_roster.py is
stage 2). The county's revize-CMS page lists all TWELVE members — four per
district across three districts — each as a table cell whose mailto link
carries the name and e-mail, with a "Term Expires: <Month> <Year>" line, a
home address (never collected) and a tel: phone link. District sections are
headed by class="subheader" spans; the page currently opens with one member
(Karl Johnson) ABOVE the section headers whose cell carries its own inline
"District N" line instead — the parser honors that per-cell tag over the
section in effect. The page states exactly one role tag ("Vice-Chairman" on
Rodney Riley) and names no Chairman; roles are captured verbatim and never
inferred from position, so the leading placement earns no title.

FETCH POSTURE: open. Plain server-rendered HTML.

Usage:
    python3 boone_county_board_scraper.py [output.json]   # default: stdout
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

LIST_URL = "https://www.boonecountyil.gov/government/county_board_members.php"
UA = {"User-Agent": UA_ROSTER_COMPACT}

# Section header between member tables: <span class="subheader">District N
SUBHEADER_RE = re.compile(
    r'class="subheader"[^>]*>(?:\s|&nbsp;|<[^>]+>)*District\s+(\d)', re.I)
# Per-cell inline district (the pre-section member's cell): >District N<
INLINE_DISTRICT_RE = re.compile(r'>(?:\s|&nbsp;)*District\s+(\d)\s*<')
MAILTO_RE = re.compile(
    r'href="mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"[^>]*>([^<]+)</a>')
TEL_RE = re.compile(r'href="tel:(\d{10})"')
TERM_RE = re.compile(r'Term Expires:\s*([A-Za-z]+\s+(\d{4}))')
# Role tags as the page states them; captured verbatim, never inferred.
ROLE_RE = re.compile(r'>(?:\s|&nbsp;)*((?:Vice[- ])?Chair(?:man|woman|person)?)\s*<')


def main():
    require_robots_once(LIST_URL, UA["User-Agent"], headers=UA,
                        label="il-boone-county-board-scraper")
    r = requests.get(LIST_URL, headers=UA, timeout=60)
    r.raise_for_status()

    records = []
    section = None
    # Split on cell starts; a chunk is one <td> cell plus the markup after it
    # up to the next cell — which is where a following section subheader
    # lives, so it is scanned AFTER the cell's member is extracted.
    for chunk in r.text.split("<td"):
        cell = chunk.split("</td>")[0]
        m = MAILTO_RE.search(cell)
        if m:
            email = m.group(1).lower()
            name = html_mod.unescape(m.group(2)).replace("\xa0", " ").strip()
            inline = INLINE_DISTRICT_RE.search(cell)
            district = int(inline.group(1)) if inline else section
            role = ROLE_RE.search(cell)
            term = TERM_RE.search(cell)
            tel = TEL_RE.search(cell)
            records.append({
                "name": name,
                "district": district,
                "role": html_mod.unescape(role.group(1)) if role else None,
                "term_expires": term.group(1) if term else None,
                "term_year": int(term.group(2)) if term else None,
                "phone": ("%s-%s-%s" % (tel.group(1)[:3], tel.group(1)[3:6],
                                        tel.group(1)[6:])) if tel else None,
                "email": email,
            })
        for h in SUBHEADER_RE.finditer(chunk):
            section = int(h.group(1))

    if not records:
        print("boone-board-scraper: FAIL — zero rows parsed from %s (markup change?)"
              % LIST_URL, file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": LIST_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("boone-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
