#!/usr/bin/env python3
"""
Stage 1 of the Macon County Board roster pipeline: scrape the county's board
members page into raw JSON for build_macon_board_roster.py.

THE DOMAIN IS maconcounty.illinois.gov. maconcountyil.gov — which this project
shipped as Macon's card link until 2026-08-07 — HAS NO DNS RECORD AT ALL. Not a
redirect, not a 404: no address associated with the hostname. Worth stating at
the top of this file because the wrong domain is the kind of thing that gets
copied forward, and it was live on a card for three days.

PAGE SHAPE. One paragraph per member, in a Fusion/Avada column grid:

    <p><strong>Karl Coleman</strong> D-1<br />
       C 521-4688<br />
       <a href="mailto: kcoleman@maconcounty.illinois.gov">Email</a><br />
       Term Expires: 11-30-26</p>

PARTY AND DISTRICT ARE ONE TOKEN — "D-1" is a Democrat in District 1, "R-4" a
Republican in District 4. That is the whole reason this page is usable: it is
the only place Macon publishes which district a member sits for, and the
county's own GIS carries no district numbers at all (see
build_macon_board_district_labels.py).

THE ROLE IS INSIDE THE NAME for the two who hold one — the page renders
"Chairman Kevin Greenfield" and "Vice Chairman Linda Little" in the same
<strong> as the name. Split off here, because "Chairman Kevin Greenfield" is not
a name and would ship as one.

PHONES ARE SEVEN DIGITS, and they ship that way. The county publishes "C
521-4688" with no area code; Macon County is entirely in area code 217, and
prefixing it would look helpful and be a guess — a member's mobile can be from
anywhere, and a wrong prefix reaches a stranger rather than failing visibly.
Published as published, with the H/C labels the county gives them, which at
least tells a reader which number is which. Recorded as a gap rather than
silently improved.

E-MAIL HREFS CARRY A LEADING SPACE on several rows ("mailto: kcoleman@…"),
which is stripped — that is whitespace in an href, not a different address, and
no judgement is involved.

Usage:
    python3 macon_county_board_scraper.py [output.json]
"""

import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_CHROME_WIN_126,
    require_robots_once,
)

SOURCE_URL = ("https://maconcounty.illinois.gov/departments/county-board/"
              "macon-county-board-members/")
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 60

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
# <p><strong>NAME</strong> PARTY-DISTRICT<br /> …rest… </p>
BLOCK_RE = re.compile(r"<p>\s*<strong>(.*?)</strong>\s*([DRI])-(\d+)\s*<br\s*/?>(.*?)</p>",
                      re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
LABELLED_PHONE_RE = re.compile(r"\b([HC])\s*(\d{3}-\d{4})\b")
BARE_PHONE_RE = re.compile(r"(?<![-\d])(\d{3}-\d{4})(?![-\d])")
EMAIL_RE = re.compile(r"mailto:\s*([^\"?\s>]+)", re.I)
TERM_RE = re.compile(r"Term Expires:\s*([\d]{1,2}-[\d]{1,2}-[\d]{2,4})", re.I)
ROLE_RE = re.compile(r"^\s*(Vice\s+Chairman|Chairman|Vice\s+Chair|Chair)\s+(?=[A-Z])", re.I)

PARTY = {"D": "Democrat", "R": "Republican", "I": "Independent"}
PHONE_LABEL = {"H": "home", "C": "cell"}


def text_of(fragment):
    return re.sub(r"\s+", " ",
                  html.unescape(TAG_RE.sub(" ", fragment or ""))).replace("\xa0", " ").strip()


def parse(page):
    page = SCRIPT_RE.sub(" ", page)
    body = page[page.find("<body"):] or page
    records, seen = [], set()
    for m in BLOCK_RE.finditer(body):
        raw_name = text_of(m.group(1))
        role = None
        role_m = ROLE_RE.match(raw_name)
        if role_m:
            role = re.sub(r"\s+", " ", role_m.group(1)).title()
            raw_name = raw_name[role_m.end():].strip()
        if not raw_name or raw_name in seen:
            continue
        seen.add(raw_name)
        rest = m.group(4)
        rec = {"district": str(int(m.group(3))), "name": raw_name,
               "party": PARTY.get(m.group(2).upper(), m.group(2))}
        if role:
            rec["role"] = role
        flat = text_of(rest)
        labelled = LABELLED_PHONE_RE.findall(flat)
        if labelled:
            rec["phones"] = [{"label": PHONE_LABEL.get(k.upper(), k.lower()),
                              "number": n} for k, n in labelled]
        else:
            bare = BARE_PHONE_RE.findall(flat)
            if bare:
                rec["phones"] = [{"number": n} for n in bare]
        email = EMAIL_RE.search(rest)
        if email:
            rec["email"] = html.unescape(email.group(1)).strip()
        term = TERM_RE.search(flat)
        if term:
            rec["term_expires"] = term.group(1)
        records.append(rec)
    return records


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "macon_county_board_raw.json"
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-macon-county-board-scraper")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    records = parse(resp.text)
    if not records:
        print("macon-scraper: FAIL — parsed 0 members. Check the DOMAIN first: the "
              "county is at maconcounty.illinois.gov; maconcountyil.gov has no DNS "
              "record at all.", file=sys.stderr)
        sys.exit(1)
    payload = {"source_url": SOURCE_URL, "records": records}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    by_district = {}
    for r in records:
        by_district.setdefault(r["district"], 0)
        by_district[r["district"]] += 1
    print("macon-scraper: wrote %s — %d members across %d districts %s, "
          "%d phones, %d e-mails, %d with a term, %d role(s)"
          % (out_path, len(records), len(by_district),
             dict(sorted(by_district.items())),
             sum(1 for r in records if r.get("phones")),
             sum(1 for r in records if r.get("email")),
             sum(1 for r in records if r.get("term_expires")),
             sum(1 for r in records if r.get("role"))))


if __name__ == "__main__":
    main()
