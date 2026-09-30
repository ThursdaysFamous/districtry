#!/usr/bin/env python3
"""
Stage 1 of the Adams County Board roster pipeline: read the county's own
CERTIFIED ELECTION CANVASSES into raw JSON for build_adams_county_board_roster.py.

WHY THE CANVASSES. Adams publishes a board page and this project cannot read
it: adamscountyil.gov is a flat Akamai WAF deny (403 AkamaiGHost, invariant
across every UA, protocol and path tried, and refused identically from a second
network), and the Internet Archive never captured the board page. That block was
re-measured on 2026-08-20 and is not the Coles case — the TLS chain is complete,
so no AIA fetch changes anything. What the county DOES publish machine-readably
is its election returns, on platinumelectionresults.com, and that is the whole
reason this file exists.

THE FINDING THAT OPENED IT, 2026-08-22. The gap record for this county said the
vendor route was "closed, proven rather than untried" — and it was, for the
vendor pair it actually tested: il-adams.pollresults.net returns a NotFound
shell and il-adams.accessliberty.com 404s. Nobody tested the THIRD vendor.
platinumelectionresults.com carries Adams as county id 54, with text-layer
canvasses for the 2018 general, the 2019 consolidated, the 2020 primary, the
2024 primary, the 2024 general and the 2025 consolidated. The vendor's own
front page lists only the EIGHT counties in the current election, which is the
number this project had on file; its history covers seventeen. Test carriage by
CONTENT, not by a county list — the rule this county is the second proof of.

WHAT THIS CAN AND CANNOT NAME. Adams elects 21 members from 7 districts, three
per district (ISBE's county-board structure table, cited for structure only),
and it staggers them: the 2018 general elected TWO per district under an
explicit "(Vote for not more than TWO)", the 2020 primary ONE per district
under "(Vote for ONE)". On four-year terms that makes 2022 a two-seat cycle and
2024 a one-seat cycle, so today's board is the fourteen seated in November 2022
plus the seven seated in November 2024.

The 2024 general is available and is parsed here. THE NOVEMBER 2022 GENERAL IS
NOT PUBLISHED ANYWHERE THIS PROJECT CAN READ — platinum returns an empty
one-page PDF for Adams for 2022 (and for 2021 and 2023), Clarity 404s the
county outright, and the county's own results page is behind the same WAF as
its board page. So this pipeline names ONE of each district's three members and
says so on the card. It is deliberately built to notice if that changes: the
scraper fetches the 2022 slug every run, and reports it as EMPTY rather than
skipping it, so the day the county backfills it the weekly run surfaces
fourteen new members instead of silently continuing to ship seven.

SEAT COUNT IS NOT PRINTED IN A GENERAL CANVASS and is therefore never assumed.
Where the county prints "(Vote for not more than N)" that N is parsed. Where it
prints nothing — as in 2024 — the parser treats the contest as single-seat and
GUARDS that reading: in a vote-for-one contest each candidate's percentage is a
share of the same ballots, so the field sums to at most ~100, while a
vote-for-two field sums to ~200 (Adams's own 2018 District 1 reads 57% + 51%).
A no-"Vote for" contest whose percentages sum past MULTI_SEAT_PCT_SUM is
refused rather than half-read.

Usage:
    python3 scripts/adams_county_board_scraper.py [-o raw.json]
"""

import argparse
import io
import json
import re
import sys

import pymupdf
import requests
from scraper_common import require_robots_once, UA_CHROME_WIN_126_FULL, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

# platinumelectionresults.com's county id for Adams. Verified by reading the
# county name out of page 1 of every report fetched — never trusted from the id.
COUNTY_ID = 54
REPORT_URL = "https://platinumelectionresults.com/history/reports/summary/{slug}/{cid}"
RESULTS_HOME = "https://platinumelectionresults.com/history"

# The general elections that can seat a member of the CURRENT board, newest
# first. Primaries and consolidated elections never seat a county board member
# here, and reading a primary winner as a member is the error this project
# refuses to make (the Clark rule). 2022 is listed even though the vendor
# currently returns an empty file for it — see the module docstring.
SEATING_ELECTIONS = [
    {"slug": "2024_ge", "year": 2024, "label": "November 2024 general"},
    {"slug": "2022_ge", "year": 2022, "label": "November 2022 general"},
]

# A report smaller than this is the vendor's empty one-page placeholder (its
# 2022 file for Adams is 2,070 bytes). Measured against the real reports, the
# smallest of which is the 2018 general at 34 KB.
MIN_REAL_REPORT_BYTES = 10000

# Percentage sum above which a contest with no printed "(Vote for ...)" line
# cannot be read as single-seat. A vote-for-one field sums to <=100 plus
# rounding; Adams's own vote-for-two contests sum near 200.
MULTI_SEAT_PCT_SUM = 115

UA = UA_CHROME_WIN_126_FULL
TIMEOUT = 60

# "COUNTY BOARD 1", "COUNTY BOARD DISTRICT 2" and "COUNTY BOARD #3" are all the
# same county writing the same thing three ways — District 1 loses the word
# "DISTRICT" in the 2024 general while districts 2-7 keep it, and the primaries
# use "#". The district number is read from the trailing digits, never from the
# label's shape.
CONTEST_TITLE_RE = re.compile(r"^COUNTY BOARD (?:DISTRICT\s*|#\s*)?(\d+)$", re.IGNORECASE)
BOARD_OFFICE_RE = re.compile(r"^FOR MEMBER(?:SHIP)? (?:OF|TO) THE (?:COUNTY )?BOARD", re.IGNORECASE)
VOTE_FOR_RE = re.compile(r"\(Vote for (?:not more than )?(ONE|TWO|THREE|\d+)\)", re.IGNORECASE)
WORD_NUMBERS = {"ONE": 1, "TWO": 2, "THREE": 3}

# A candidate row is four consecutive lines: name, party, votes, percent.
PARTY_RE = re.compile(r"^(DEM|REP|NON)$", re.IGNORECASE)
VOTES_RE = re.compile(r"^[\d,]+$")
PCT_RE = re.compile(r"^(\d+)%$")

# The county prints a placeholder where a party fielded nobody. It is not a
# person and must never become a roster row.
NON_CANDIDATE_RE = re.compile(r"^\s*(NO CANDIDATE(\s+FILED)?|WRITE[ -]?IN)\s*$", re.IGNORECASE)

ANCHOR = "Number of Precincts:"


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, UA, headers={"User-Agent": UA},
                        label="il-adams-county-board-scraper")
    return fetch_with_retry(url, {"User-Agent": UA}, timeout=TIMEOUT)


def pdf_text(data):
    with pymupdf.open(stream=io.BytesIO(data), filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def county_name(text):
    """Page 1 names the county. Read it rather than trusting the id."""
    m = re.search(r"([A-Za-z][A-Za-z .'-]*?County)\s*,?\s*ILLINOIS", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def split_contests(text):
    """Split a summary canvass into one block per contest.

    Every contest in these reports is anchored by a "Number of Precincts:" line;
    the lines immediately above it are its title and office, and the candidate
    rows run from below "Precincts Reporting: <n>" to the next anchor's title.
    Slicing to the next ANCHOR rather than to the next board contest is the
    whole difference between reading District 7 and reading District 7 plus
    three judicial contests — measured, on this county's own 2024 file.
    """
    lines = [ln.strip() for ln in text.split("\n")]
    anchors = [i for i, ln in enumerate(lines) if ln == ANCHOR]
    blocks = []
    for pos, idx in enumerate(anchors):
        # Header: the non-empty lines above the anchor, back to the previous
        # anchor's candidate rows. Two or three lines in practice (title,
        # office, sometimes a "(Vote for ...)" line).
        head = []
        j = idx - 1
        while j >= 0 and len(head) < 4:
            ln = lines[j]
            if ln and not ln.startswith("Page ") and not PCT_RE.match(ln):
                head.append(ln)
            elif PCT_RE.match(ln):
                break
            j -= 1
        head.reverse()
        end = anchors[pos + 1] if pos + 1 < len(anchors) else len(lines)
        blocks.append({"head": head, "body": lines[idx:end]})
    return blocks


def parse_candidates(body):
    rows = []
    for i in range(len(body) - 3):
        name, party, votes, pct = body[i], body[i + 1], body[i + 2], body[i + 3]
        if not PARTY_RE.match(party) or not VOTES_RE.match(votes):
            continue
        m = PCT_RE.match(pct)
        if not m:
            continue
        if not name or name == ANCHOR or name.startswith("Page "):
            continue
        rows.append({
            "name": name,
            "party": party.upper(),
            "votes": int(votes.replace(",", "")),
            "pct": int(m.group(1)),
        })
    return rows


def board_contests(text, fail):
    """Every county-board contest in one canvass, keyed by district number.

    A district can carry MORE THAN ONE contest in the same election and that is
    not an error: Adams's own 2018 general holds District 4's two-seat full-term
    contest and, further down the ballot, a separate "COUNTY BOARD #4 / FOR
    MEMBERSHIP TO THE BOARD (Vote for ONE)" — an unexpired term. Each district
    therefore maps to a LIST. An earlier draft keyed one contest per district
    and refused the 2018 file outright; the refusal was correct and the shape
    was wrong.
    """
    found = {}
    for block in split_contests(text):
        head = block["head"]
        district = None
        office_seen = False
        seats = None
        for ln in head:
            m = CONTEST_TITLE_RE.match(ln)
            if m:
                district = int(m.group(1))
            if BOARD_OFFICE_RE.match(ln):
                office_seen = True
                m2 = VOTE_FOR_RE.search(ln)
                if m2:
                    tok = m2.group(1).upper()
                    seats = WORD_NUMBERS.get(tok) or int(tok)
            else:
                m2 = VOTE_FOR_RE.search(ln)
                if m2 and office_seen:
                    tok = m2.group(1).upper()
                    seats = WORD_NUMBERS.get(tok) or int(tok)
        if district is None or not office_seen:
            continue
        rows = [r for r in parse_candidates(block["body"])
                if not NON_CANDIDATE_RE.match(r["name"]) and r["votes"] > 0
                and r["party"] in ("DEM", "REP")]
        if not rows:
            continue
        if seats is None:
            total = sum(r["pct"] for r in rows)
            if total > MULTI_SEAT_PCT_SUM:
                fail("Adams District %d: no '(Vote for ...)' line and the field's "
                     "percentages sum to %d%%, which is a multi-seat contest this "
                     "parser must not read as single-seat" % (district, total))
            seats = 1
        rows.sort(key=lambda r: -r["votes"])
        title = next((ln for ln in head if BOARD_OFFICE_RE.match(ln)), "")
        found.setdefault(district, []).append({
            "seats": seats,
            "office": title,
            "candidates": rows,
        })
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    problems = []

    def fail(msg):
        problems.append(msg)
        raise SystemExit("adams-scraper: " + msg)

    elections = []
    for spec in SEATING_ELECTIONS:
        url = REPORT_URL.format(slug=spec["slug"], cid=COUNTY_ID)
        record = dict(spec)
        record["url"] = url
        try:
            resp = fetch(url)
        except Exception as exc:                                  # noqa: BLE001
            record["status"] = "unreachable"
            record["detail"] = str(exc)
            elections.append(record)
            continue
        data = resp.content
        record["bytes"] = len(data)
        if len(data) < MIN_REAL_REPORT_BYTES:
            # The vendor's placeholder. Recorded, never treated as "no contests".
            record["status"] = "empty"
            elections.append(record)
            continue
        text = pdf_text(data)
        name = county_name(text)
        if not name or not name.lower().startswith("adams"):
            fail("%s returned a report for %r, not Adams County" % (url, name))
        record["status"] = "ok"
        record["county"] = name
        record["districts"] = {str(d): v for d, v in
                               sorted(board_contests(text, fail).items())}
        elections.append(record)

    out = {
        "source": "platinumelectionresults.com",
        "resultsHome": RESULTS_HOME,
        "countyId": COUNTY_ID,
        "elections": elections,
        "problems": problems,
    }
    text = json.dumps(out, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        ok = sum(1 for e in elections if e.get("status") == "ok")
        print("adams-scraper: wrote %s (%d of %d canvasses readable)"
              % (args.out, ok, len(elections)), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
