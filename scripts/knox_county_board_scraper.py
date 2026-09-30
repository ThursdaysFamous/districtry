#!/usr/bin/env python3
"""Stage 1 of the Knox County Board roster pipeline: read the county's own board MINUTES.

WHY THE MINUTES. Knox's board page lists all fifteen members with district and
contact details and this project may not read it: knoxcountyil.gov answers 403
to every client, and the Internet Archive never captured the page. What ANSWERS
this client is the same website's DOCUMENTS, served from its Revize CMS at
cms2.revize.com/revize/knoxcounty/. Every set of minutes opens with a roll call
that names EVERY SEAT BY DISTRICT, which is the roster this county was recorded
as not having.

THAT HOST REFUSES US, AND THIS DOCSTRING SAID IT DID NOT. The sentence above
read "with no block of any kind" from the day this file was written, and
CLAUDE.md repeated it; the claim was about the PAGES answering and nobody had
read the policy. Measured 2026-09-30 with the client below, cms2.revize.com
serves a 414-byte robots.txt whose `*` group ends in `Disallow: /`, the longest
match for /revize/knoxcounty/. So this scrape declines at the gate now and
fetches nothing. The refusal is the CMS VENDOR'S and is published at the
vendor's own host, which is what makes it bind here — the reverse of the
Kendall/McHenry/Joliet case, where one vendor's default is published at each
GOVERNMENT'S host, binds for that reason, and must never be cited as something
that government chose. Knox's shipped roster keeps its last-good records: a
refusal stops the FETCH and never unpublishes what we already have (Adam's
ruling of 2026-09-19). The county's own host allows us and publishes no roster
this scrape can read, so there is no second route to move to.

  "The Meeting was called to order by County Board Chair Jared Hawkinson and
   upon roll call the following Members reported present:
        District 1  Tracy Robertson
        District 2  Erin Pugh
        ...
   And those absent:
        District 2  Jennifer Fredrick"

ABSENT MEMBERS ARE MEMBERS. The absent list is parsed exactly like the present
list — a seat is not vacated by missing a meeting, and reading only the present
block would have shipped fourteen of fifteen seats and called Knox complete.

WHAT THIS DOES NOT PROVIDE: party, term, phone and e-mail. The minutes publish
none of them, and the page that does cannot be read. Nothing is inferred; the
card carries the county's switchboard the way Clark's does.

THE ARCHIVE IS SPARSE AND FLAT. Minutes live at the CMS root as
"Board Minutes <Month> <Year>.pdf" — not under the Documents/ tree the packets
use — and only a handful of recent months exist. So this walks months
newest-first from the current date and takes the first that parses, rather than
assuming any particular file is present.

Usage:
    python3 scripts/knox_county_board_scraper.py [-o raw.json]
"""

import os
import argparse
import datetime
import io
import json
import re
import sys
import urllib.parse

import pymupdf
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import require_robots_once  # noqa: E402  (shared machinery)

CMS_ROOT = "https://cms2.revize.com/revize/knoxcounty/"
MINUTES_TEMPLATE = "Board Minutes {month} {year}.pdf"
# The card's citation, never fetched here — this scraper reads the minutes
# PDFs on CMS_ROOT. It was pinned at /departments/county_board/ until
# 2026-09-03, which had become a 404: Knox keeps its board pages at the
# site ROOT, not under /departments/. Nothing noticed because nothing
# fetches this, and the weekly run stayed green while the card sent every
# reader who clicked it to a missing page.
#
# It is also worth what it says about the host. This county is recorded as
# refusing every request, and it does refuse a `requests` session — but a
# stdlib client is served normally, the Kendall/McHenry shape. That page
# names all fifteen members under their five district headings, so the
# roster route this scraper takes through the minutes may not be the only
# one available. Measuring that is its own change, not this one.
BOARD_PAGE = "https://www.knoxcountyil.gov/county_board/county_board_members.php"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# How far back to walk before giving up. The archive held five files in August
# 2026, the oldest ~14 months old.
MAX_MONTHS_BACK = 30

EXPECTED_SEATS = 15
EXPECTED_DISTRICTS = 5

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/126.0 Safari/537.36")}
TIMEOUT = 90

ROLL_START = re.compile(r"following\s+Members\s+reported\s+present\s*:", re.I)
ABSENT = re.compile(r"And\s+those\s+absent\s*:", re.I)
# The roll call ends where the meeting's other attendees begin.
ROLL_END = re.compile(r"Also\s+present\s+were|Department\s+Heads\s+present", re.I)
# The flag is SCOPED to the phrase deliberately. A whole-pattern re.I makes
# [A-Z] match lowercase too, so the name ran on into the sentence and gave
# "Jared Hawkinson and upon" — the chair check caught it, which is the check
# working. The name half stays case-SENSITIVE so it stops at the first
# lowercase word.
CHAIR = re.compile(r"(?i:County\s+Board\s+Chair(?:man)?)\s+"
                   r"([A-Z][A-Za-z.'\u2019-]+(?:\s+[A-Z][A-Za-z.'\u2019-]+){1,3})")

# "District 3" then the member's name, WHICH MAY BE ON THE SAME LINE OR THE
# NEXT — the minutes use both inside one roll call:
#
#     District 1
#     Tracy Robertson
#     District 2        Erin Pugh
#
# The name is deliberately narrow: capitalised words or a quoted nickname, never
# digits, so a stray "District 4 6:01 p.m." cannot become a person. The word
# "District" is excluded from name tokens EXPLICITLY, because without that the
# match runs past a name into the next seat's header and yields "Tracy Robertson
# District" — measured, on this county's own June 2026 minutes.
_NAME_WORD = r"(?!District\b)(?:[A-Z][A-Za-z.'\u2019-]+|[\u201c\"][A-Za-z.'\u2019-]+[\u201d\"])"
SEAT = re.compile(r"District\s+([1-9])\b\s*"
                  r"(" + _NAME_WORD + r"(?:\s+" + _NAME_WORD + r"){1,3})")


def fetch(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-knox-county-board-scraper")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    if "pdf" not in (r.headers.get("content-type") or "").lower():
        return None
    return r.content


def pdf_text(data):
    with pymupdf.open(stream=io.BytesIO(data), filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def parse_roll(text, fail):
    m = ROLL_START.search(text)
    if not m:
        return None
    end = ROLL_END.search(text, m.end())
    block = text[m.end(): end.start() if end else m.end() + 4000]
    absent_at = ABSENT.search(block)
    present_block = block[:absent_at.start()] if absent_at else block
    absent_block = block[absent_at.end():] if absent_at else ""

    seats = []
    seen = set()
    for chunk, present in ((present_block, True), (absent_block, False)):
        for sm in SEAT.finditer(chunk):
            district = int(sm.group(1))
            name = " ".join(sm.group(2).split())
            # A name repeated across both blocks is a parse error, not two seats.
            if (district, name) in seen:
                continue
            seen.add((district, name))
            seats.append({"district": district, "name": name, "present": present})
    return seats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", help="write raw JSON here (default: stdout)")
    ap.add_argument("--today", help="YYYY-MM-DD; pin the walk's starting month (testing)")
    args = ap.parse_args()

    def fail(msg):
        raise SystemExit("knox-scraper: " + msg)

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.date.today())
    tried = []
    for back in range(MAX_MONTHS_BACK):
        y, m = today.year, today.month - back
        while m <= 0:
            m += 12
            y -= 1
        name = MINUTES_TEMPLATE.format(month=MONTHS[m - 1], year=y)
        url = CMS_ROOT + urllib.parse.quote(name)
        tried.append(name)
        data = fetch(url)
        if not data:
            continue
        text = pdf_text(data)
        seats = parse_roll(text, fail)
        if not seats:
            continue
        chair_m = CHAIR.search(text)
        chair = " ".join(chair_m.group(1).split()) if chair_m else None
        districts = sorted({s["district"] for s in seats})
        if len(seats) != EXPECTED_SEATS:
            fail("%s: roll call yielded %d seats, expected %d — %r"
                 % (name, len(seats), EXPECTED_SEATS, seats))
        if districts != list(range(1, EXPECTED_DISTRICTS + 1)):
            fail("%s: districts %r, expected 1-%d" % (name, districts, EXPECTED_DISTRICTS))
        if chair and not any(s["name"] == chair for s in seats):
            fail("%s: chair %r is not among the members on the roll call" % (name, chair))
        out = {
            "source": url,
            "document": name,
            "meetingMonth": "%s %d" % (MONTHS[m - 1], y),
            "boardPage": BOARD_PAGE,
            "chair": chair,
            "seats": seats,
            "triedBeforeThis": tried[:-1],
        }
        body = json.dumps(out, indent=2, sort_keys=True)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(body + "\n")
            print("knox-scraper: %s — %d seats across %d districts%s"
                  % (name, len(seats), len(districts),
                     (", chair %s" % chair) if chair else ""), file=sys.stderr)
        else:
            print(body)
        return
    fail("no readable minutes in the last %d months (tried %r)"
         % (MAX_MONTHS_BACK, tried))


if __name__ == "__main__":
    main()
