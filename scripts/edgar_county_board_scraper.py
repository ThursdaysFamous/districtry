#!/usr/bin/env python3
"""
Stage 1 of the Edgar County Board roster pipeline: scrape the county's own
board page into raw JSON for build_edgar_county_board.py, and RE-READ the
district composition out of the Clerk's live results feed in the same run.

TWO SOURCES, TWO JOBS — the Crawford shape. The people come from
edgarcountyillinois.COM, which publishes the board as seven one-line entries,
"District #3: Andy Patrick (R)". READ THAT DOMAIN TWICE: the county also runs
edgarcountyillinois.GOV, and the .gov does not carry the board page — it links
across to the .com for it. This is the Morgan trap in a milder form, and the
URL below is the one that has the roster.

The DISTRICTS come from il-edgar.pollresults.net, the Clerk's own results
system, whose certified result set is embedded in the page as JSON. That is
one of the three documents the shipped boundaries' composition was proven from
(build_edgar_boundaries.py), and re-reading it weekly is the re-precincting /
redistricting tripwire.

WHY THE PAGE IS THE ROSTER AND THE RETURNS ARE THE GEOMETRY — this county
makes the case better than any so far. The 2022 and 2024 canvasses elected
PHILLIP R. LUDINGTON in District 6. The county's board page names SAMANTHA
McCARTY there, and the Clerk's own 2026 primary confirms it by carrying a "6TH
DISTRICT MEMBER 2-YEAR UNEXPIRED TERM" contest — a seat filled mid-term, which
no canvass of a completed term could ever show. A roster taken from the
returns alone would name the wrong person for District 6 today.

WHAT THE BOARD PAGE PUBLISHES, and what it does not: name, district and party
for all seven. No e-mail, no phone, no term, and NO BOARD CHAIRMAN — the
committees table beneath the roster has a CHAIRMAN column, but that is the
chair OF EACH COMMITTEE and reading it as the board's chair would be a
fabrication. None of those ship.

A 200 WITHOUT THE ROSTER IS A FAILED FETCH, NOT AN EMPTY BOARD, and that
distinction is why this file was rewritten on 2026-09-18. The 17 September run
came back with zero members, the builder refused, and the roster froze for a
week under the reading that the page had been rebuilt and the parse had broken.
Measured on the 18th: the page was unchanged, the then-current pattern read all
seven off it, and a dispatch of the untouched workflow went green — so the
runner had been served a body that was not the board page, at HTTP 200, where
raise_for_status() sees nothing wrong. The scraper believed it and wrote an
empty payload.

Three things follow, and none of them is a browser string or a new engine rung.
The transport goes through scraper_common.fetch(), the fleet's ladder, rather
than the hand-rolled requests.get() this file used alone among its siblings.
The ROSTER BLOCK is the positive control: the body must carry the page's own
"Board Members" heading, and a body that does not is refetched rather than
parsed. And a scrape that still finds nothing REFUSES, naming which case it is
— no block means we were not served this page, a block with no member line
means the markup really did change and this pattern needs rewriting. The
builder's floor already stopped the bad data; what was missing was any way to
read the cause out of the run.

THE PATTERN READS THE BLOCK'S VISIBLE TEXT, not its markup. The old one
required a literal </strong> between the district label and the name, which is
how the page is written today and is incidental to it; scoping to the block
first means the surrounding tags can move without costing a run, and the
committees table below cannot contribute a false member (measured: zero
matches outside the block).

Usage:
    python3 scripts/edgar_county_board_scraper.py [-o raw.json]
"""

import argparse
import html
import json
import re
import sys
import time

from scraper_common import fetch, make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://edgarcountyillinois.com/county-board/"
RESULTS_URL = "https://il-edgar.pollresults.net/"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

# The page's own "Board Members" heading and the block under it, ending at the
# next heading ("Committees"). This is the positive control as much as the
# scope: a body that does not carry it is not the board page.
BOARD_BLOCK_RE = re.compile(
    r"<h[1-3][^>]*>\s*Board\s+Members\s*</h[1-3]>(.{0,4000}?)(?:<h[1-3]\b|\Z)",
    re.S | re.I)
# One member per line in the block's VISIBLE text: "District #3: Andy Patrick (R)".
MEMBER_RE = re.compile(
    r"District\s*#?\s*(\d+)\s*:\s*([^()<>]{2,60}?)\s*\((R|D|I|G|L)\)",
    re.I)
# A street address would carry a number then a street word. The page prints
# bare names today; this is the tripwire if that ever changes, because home
# addresses never ship (the Madison/Peoria rule).
STREET_RE = re.compile(
    r"\d+\s+\w+\s+(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|blvd|hwy)\b",
    re.I)


fail = make_fail("edgar-board-scraper")


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def get(url):
    """Through the fleet's ladder: 429/5xx retried honouring Retry-After,
    401/403/404 raised at once. Edgar hand-rolled this until 2026-09-18."""
    return fetch(url, HEADERS, timeout=TIMEOUT).text


def get_board_page(attempts=3):
    """The board page's roster block, refetched while the body lacks it.

    See the module docstring: raise_for_status() cannot tell a 200 carrying the
    board from a 200 carrying something else, and the second is what froze this
    roster for a week. The heading is the county's own, so asking for it costs
    nothing and answers the question the run log could not.
    """
    last = None
    for attempt in range(attempts):
        resp = fetch(BOARD_URL, HEADERS, timeout=TIMEOUT)
        match = BOARD_BLOCK_RE.search(resp.text)
        if match:
            return clean(match.group(1))
        last = "HTTP %d, %d bytes, no 'Board Members' heading" % (
            resp.status_code, len(resp.content))
        if attempt + 1 < attempts:
            time.sleep(2.0 * (attempt + 1))
    fail("%s answered %d time(s) without the board roster on it (last: %s) — "
         "that is a body this client was not meant to get rather than a board "
         "with no members, so nothing is parsed from it. Check what the page "
         "serves before touching this parser." % (BOARD_URL, attempts, last))


def scrape_members(block):
    """[{name, district, party}] from the roster block's visible text."""
    records = []
    seen = set()
    for match in MEMBER_RE.finditer(block):
        district, name, party = match.group(1), clean(match.group(2)), match.group(3).upper()
        if not name or district in seen:
            continue
        if STREET_RE.search(name):
            fail("the board page now prints what looks like a street address (%r) — "
                 "home addresses never ship; tighten this parser rather than the "
                 "rule" % name)
        seen.add(district)
        records.append({"name": name, "district": district, "party": party})
    if not records:
        fail("the roster block is on the page and no member line parsed from "
             "it — the county has changed how it writes them, so rewrite "
             "MEMBER_RE against the block rather than assuming a bad fetch. "
             "The block reads: %r" % block[:300])
    records.sort(key=lambda r: int(r["district"]))
    return records


def scrape_composition(page):
    """{district: [precinct, ...]} from the certified result set embedded in
    the Clerk's live results page."""
    match = re.search(r"var electionData = (\{.*?\});\s*\n", page, re.S)
    if not match:
        fail("the Clerk's results page no longer embeds its result set as JSON — "
             "the composition check cannot run, and it is this county's only "
             "automatic redistricting warning")
    data = json.loads(match.group(1))
    election = data.get("Election") or {}
    out = {}
    for race in data.get("Races") or []:
        name = (race.get("RaceName") or "").upper()
        if "COUNTY BOARD" not in name:
            continue
        hit = re.search(r"BOARD (\d+)(?:ST|ND|RD|TH) DISTRICT", name)
        if not hit:
            continue
        precincts = ([p["PrecinctName"] for p in race.get("Reporting") or []] +
                     [p["PrecinctName"] for p in race.get("NotReporting") or []])
        out.setdefault(hit.group(1), set()).update(precincts)
    return ({d: sorted(v) for d, v in out.items()},
            {"description": election.get("Description"),
             "date": (election.get("ElectionDate") or "")[:10],
             "officeTitle": election.get("OfficeTitle")})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    members = scrape_members(get_board_page())
    composition, election = scrape_composition(get(RESULTS_URL))
    payload = {"source": BOARD_URL, "resultsUrl": RESULTS_URL,
               "election": election, "composition": composition,
               "records": members}
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("edgar-board-scraper: %d member(s), %d district(s) re-read from the "
              "%s -> %s" % (len(members), len(composition),
                            election.get("description"), args.output), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
