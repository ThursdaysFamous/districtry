#!/usr/bin/env python3
"""
Scrape Woodford County's own board directory into raw roster records.

Stage 1 of the two-stage pipeline (scripts/build_woodford_board_roster.py is
stage 2), mirroring the LaSalle pair. The county board is FIFTEEN members,
five elected at large from each of THREE districts (Ordinance 2020/21 #005) —
the directory groups the member rows under accordion section headers reading
"District 1/2/3", so the district comes from the SECTION a row sits in, not
from the row's title (every title is the bare "County Board Member").

MARKUP CHANGE, 2026-08-10. The county replaced its CivicPlus directory
(Directory.aspx?DID=22, which this scraper read from 2026-07-31) with a new
CMS: the old URL now 302s to /m/directory/department?did=22 and the page is
Bootstrap markup — <li class="list-group-item"> rows, each with an employee
link (/m/directory/employee?eid=n), a plain `mailto:` and a plain `tel:`.
Two things got BETTER and are worth recording so a future reader does not
"restore" the old code: the e-mail is now published as an ordinary mailto
rather than reassembled by a spam-wrapper script (var w = "twilcoxen";
var x = "woodfordcountyil.gov"), and the phone is a tel: href rather than
text to be pattern-matched out of the row. The roster itself is unchanged —
same fifteen members, same addresses, same numbers — only the markup and the
per-member URLs moved.

NO CHAIRMAN IS EMITTED: the chair is elected every two years from within the
body and the directory does not mark who holds it, so marking one would be a
guess. The card renders fifteen members by district and links the directory.

Usage:
    python3 woodford_county_board_scraper.py [output.json]   # default: stdout
"""

import json
import re
import sys
import time

import requests
from scraper_common import require_robots_once, UA_ROSTER_COMPACT, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

BASE = "https://www.woodford-county.org"
LIST_URL = BASE + "/m/directory/department?did=22"
UA = {"User-Agent": UA_ROSTER_COMPACT}

# Each district is a sub-department accordion whose title link carries its own
# did; the members of that district follow it until the next such header.
DISTRICT_HEADER_RE = re.compile(
    r'href="/m/directory/department\?did=\d+"[^>]*>\s*District\s+(\d+)\s*</a>', re.I)
ROW_RE = re.compile(r'<li class="list-group-item\b.*?</li>', re.S | re.I)
NAME_RE = re.compile(
    r'href="/m/directory/employee\?eid=(?P<eid>\d+)"[^>]*>\s*(?P<name>[^<]+?)\s*</a>', re.I)
TITLE_RE = re.compile(r'>\s*(County Board[^<]*)</div>', re.I)
EMAIL_RE = re.compile(r'href="mailto:\s*([^"?\s]+@[^"?\s]+)"', re.I)
PHONE_RE = re.compile(r'\(?(\d{3})\)?[.\- ]\s*(\d{3})[.\- ](\d{4})')

FETCH_ATTEMPTS = 3


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="il-woodford-county-board-scraper")
    return fetch_with_retry(url, UA, timeout=60, attempts=FETCH_ATTEMPTS).text


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def display_name(directory_name):
    """'Wilcoxen, Timothy' -> 'Timothy Wilcoxen' (the card renders given-name-first).

    The new CMS already lists names given-name-first, so this is a no-op there;
    it stays because the old directory listed them surname-first and a CMS can
    always change its mind again.
    """
    parts = [p.strip() for p in directory_name.split(",", 1)]
    if len(parts) == 2 and parts[1]:
        return "%s %s" % (parts[1], parts[0])
    return directory_name.strip()


def main():
    html = fetch(LIST_URL)

    # Slice the page into district sections; each row inherits its section.
    sections = []
    headers = list(DISTRICT_HEADER_RE.finditer(html))
    if not headers:
        print("woodford-board-scraper: FAIL — no 'District N' section headers on %s "
              "(markup change?)" % LIST_URL, file=sys.stderr)
        sys.exit(1)
    for i, h in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(html)
        sections.append((int(h.group(1)), html[h.start():end]))

    records = []
    skipped = 0
    for district, segment in sections:
        for row in ROW_RE.finditer(segment):
            block = row.group(0)
            nm = NAME_RE.search(block)
            if not nm:
                continue
            name = clean(nm.group("name"))
            tm = TITLE_RE.search(block)
            title = clean(tm.group(1)) if tm else ""
            if not name or "County Board Member" not in title:
                # A non-member row inside a district section (staff, a vacancy
                # placeholder) — count it so a title change is visible rather
                # than silently thinning the roster.
                skipped += 1
                continue
            em = EMAIL_RE.search(block)
            email = em.group(1).strip() if em else None
            phone = None
            pm = PHONE_RE.search(re.sub(r"<[^>]+>", " ", block))
            if pm:
                phone = "%s-%s-%s" % pm.groups()
            records.append({
                "name": display_name(name),
                "district": district,
                "phone": phone,
                "email": email,
                "url": BASE + "/m/directory/employee?eid=" + nm.group("eid"),
            })

    if skipped:
        print("woodford-board-scraper: NOTE — skipped %d row(s) whose title was not "
              "'County Board Member'" % skipped, file=sys.stderr)

    if not records:
        print("woodford-board-scraper: FAIL — zero rows parsed from %s (markup change?)"
              % LIST_URL, file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": LIST_URL, "records": records}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("woodford-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
