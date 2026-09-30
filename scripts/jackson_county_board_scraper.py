#!/usr/bin/env python3
"""
Stage 1 of the Jackson County Board roster pipeline: scrape the county's own
board page and its staff-directory entries into raw JSON for
build_jackson_county_board.py.

FOURTEEN MEMBERS, TWO PER DISTRICT, and the county publishes them in two places
that this reads together on purpose.

  * THE BOARD PAGE groups members under headings — "District 1 Board Members",
    "District 2 Board Members" — with a card per member carrying a name and a
    job title.
  * EACH MEMBER'S DIRECTORY ENTRY (/m/directory/employee?eid=N) repeats the
    district as its own field and adds the county e-mail address and the term
    length.

THE TRAP, AND IT IS WHY THE HEADING IS THE AUTHORITY: a member's job title is
their DISTRICT for twelve of the fourteen and their OFFICE for the other two.
C. J. Calandro's card reads "Chair" and Andrew Erbes's reads "Vice Chair" — the
district appears nowhere on either card. A parser that keys on the job title
therefore drops the two most prominent members of the board and reports twelve
seats for a fourteen-seat county. The grouping heading is what states the
district; the job title is read only to badge a role.

The directory entry's own district field is then compared against the heading
and any disagreement FAILS the run rather than picking a winner — two county
surfaces that disagree about which district a member sits in is exactly the
thing a human should look at.

WHAT SHIPS: name, district, the county e-mail address, and the Chair's and Vice
Chair's roles. WHAT DOES NOT: the term length (the directory publishes "2 Year
Term" / "4 Year Term" but never a start or end date, so a term that cannot be
placed in time is not a fact worth rendering), and no phone or address, because
the directory publishes neither per member.

Usage:
    python3 scripts/jackson_county_board_scraper.py [-o raw.json]
"""

import argparse
import html
import json
import re
import sys
import time

import requests
from scraper_common import require_robots_once, make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://jacksoncounty-il.gov/158/County-Board"
BASE = "https://jacksoncounty-il.gov"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

EXPECT_DISTRICTS = 7
EXPECT_MEMBERS = 14

# A staff-directory widget: a heading naming the district, then its member cards.
WIDGET_RE = re.compile(
    r'<div class="widgetHeader">.*?<h3>.*?District\s+(\d+)\s+Board Members.*?</h3>.*?'
    r'</div>(.*?)(?=<div class="widgetHeader">|</body>)', re.S | re.I)
CARD_RE = re.compile(r'<li class="widgetItem h-card">(.*?)</li>', re.S)
NAME_RE = re.compile(r'<h4[^>]*class="[^"]*p-name[^"]*"[^>]*>(.*?)</h4>', re.S)
TITLE_RE = re.compile(r'<div class="field p-job-title">(.*?)</div>', re.S)
EID_RE = re.compile(r'/m/directory/employee\?eid=(\d+)')
CHAIR_RE = re.compile(r"^\s*chair(man|person|woman)?\s*$", re.I)
VICE_RE = re.compile(r"^\s*vice[\s-]*chair(man|person|woman)?\s*$", re.I)
MAILTO_RE = re.compile(r'href="mailto:([^"?]+)"', re.I)
EMP_DISTRICT_RE = re.compile(r"District\s+(\d+)")


fail = make_fail("jackson-board-scraper")


def get(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-jackson-county-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scrape_board(page):
    records = []
    for widget in WIDGET_RE.finditer(page):
        dnum, body = widget.group(1), widget.group(2)
        for card in CARD_RE.finditer(body):
            frag = card.group(1)
            name = NAME_RE.search(frag)
            if not name:
                continue
            title = TITLE_RE.search(frag)
            title = clean(title.group(1)) if title else ""
            eid = EID_RE.search(frag)
            entry = {"name": clean(name.group(1)), "district": dnum, "title": title}
            if CHAIR_RE.match(title):
                entry["role"] = "Chair"
            elif VICE_RE.match(title):
                entry["role"] = "Vice Chair"
            if eid:
                entry["eid"] = eid.group(1)
            records.append(entry)
    return records


def enrich(rec):
    """The member's own directory entry: e-mail, plus the district it states."""
    if not rec.get("eid"):
        return rec
    page = get("%s/m/directory/employee?eid=%s" % (BASE, rec["eid"]))
    mail = MAILTO_RE.search(page)
    if mail:
        rec["email"] = html.unescape(mail.group(1)).strip()
    text = clean(page)
    idx = text.find(rec["name"])
    hit = EMP_DISTRICT_RE.search(text, idx if idx >= 0 else 0)
    if hit:
        rec["directoryDistrict"] = hit.group(1)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    records = scrape_board(get(BOARD_URL))
    if len(records) != EXPECT_MEMBERS:
        fail("the board page yielded %d member(s), expected %d — its grouped "
             "staff-directory widgets have changed shape" % (len(records), EXPECT_MEMBERS))
    for rec in records:
        enrich(rec)
        time.sleep(0.2)

    records.sort(key=lambda r: (int(r["district"]), r["name"]))
    payload = {"source": BOARD_URL, "records": records}
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("jackson-board-scraper: %d member(s) across %d district(s) -> %s"
              % (len(records), len({r["district"] for r in records}), args.output),
              file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
