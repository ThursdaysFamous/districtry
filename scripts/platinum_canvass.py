#!/usr/bin/env python3
"""Read a county's certified canvass off platinumelectionresults.com.

WHY THIS IS SHARED CODE. Three counties now read their rosters out of this
vendor's summary reports — Adams's board members by district, and Union's and
Williamson's commissioners countywide — and each one needed the same two
readings to be got right. Both are easy to get wrong in a way that LOOKS right,
so they live here once instead of three times.

READING ONE: WHERE A CONTEST ENDS. Every contest in these reports is anchored by
a "Number of Precincts:" line, with its title on the lines above and its
candidate rows below. A parser that slices from one BOARD contest to the next
board contest swallows everything in between: on Adams's own 2024 file that put
three judicial races inside District 7. Slicing to the next ANCHOR is the whole
fix, and it is why this returns contests rather than text.

READING TWO: WHAT COUNTS AS A CANDIDATE. A candidate row is exactly four
consecutive lines — name, party, votes, percent. "NO CANDIDATE", "No Candidate
Filed" and "WRITE-IN" match that shape perfectly and are not people; a
zero-vote row is not a winner. Both are dropped here so no caller has to
remember to.

WHAT THIS DELIBERATELY DOES NOT DO: decide who won. Seat counts are a property
of the county, not of the report — these are SUMMARY canvasses, and a contest
carries no "elected" flag — so callers rank by votes and apply their own
county's seat count. See build_knox_board_districts.py for what happens when a
count is assumed instead of checked.
"""

import io
import os
import re
import sys

import pymupdf
import requests

# The shared header set, imported rather than restated. This module is read
# by scrapers in this same directory, so scripts/ is already importable for
# every caller; the insert keeps it importable when it is run on its own.
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import UA_HEADERS_ROSTER_BOT  # noqa: E402  (shared machinery)

REPORT_URL = "https://platinumelectionresults.com/history/reports/summary/{slug}/{cid}"
RESULTS_HOME = "https://platinumelectionresults.com/history"

# A report smaller than this is the vendor's empty one-page placeholder — it
# serves those for elections a carried county did not publish through it.
MIN_REAL_REPORT_BYTES = 10000

# OUR OWN IDENTITY, MEASURED RATHER THAN ASSUMED (2026-10-01). This file
# used to send a Chrome string. Every page it fetches was re-read with
# scraper_common's districtry token on this file's own HTTP stack and
# answered in full, so the browser string was claiming a client this
# project does not run for no measured gain. A site that measurably
# refuses the token gets the browser rung back, per host, with the
# measurement written here.
HEADERS = dict(UA_HEADERS_ROSTER_BOT)
TIMEOUT = 90

ANCHOR = "Number of Precincts:"
PARTY_RE = re.compile(r"^(DEM|REP|NON)$", re.IGNORECASE)
VOTES_RE = re.compile(r"^[\d,]+$")
PCT_RE = re.compile(r"^(\d+)%$")
NON_CANDIDATE_RE = re.compile(
    r"^\s*(NO\s+CANDIDATE(\s+FILED)?|WRITE[\s-]?IN)\s*$", re.IGNORECASE)
# The county name is on page 1, and its FORM VARIES BY YEAR: recent reports
# write "UNION COUNTY, ILLINOIS" while 2016's writes a bare "Union County"
# on its own line above the election date. Both are matched; a report whose
# name cannot be read is skipped by callers rather than trusted.
COUNTY_RE = re.compile(r"^\s*([A-Za-z][A-Za-z .'-]*?County)\s*(?:,\s*ILLINOIS)?\s*$",
                       re.IGNORECASE | re.MULTILINE)
PRECINCTS_RE = re.compile(r"^\d+$")


def report_url(slug, cid):
    return REPORT_URL.format(slug=slug, cid=cid)


def fetch_report(slug, cid, session=None):
    """-> (text, size) for a real report; (None, size) for anything else.

    THE PDF CHECK IS NOT DEFENSIVE PADDING. An election the vendor has not run
    yet answers 302 and REDIRECTS to its county-selection page — 395 KB of HTML,
    comfortably over any size floor. Accepting that as a report is how Union's
    build first failed: it read the redirect target and reported no county name.
    A report is PDF bytes or it is not a report.
    """
    get = (session or requests).get
    resp = get(report_url(slug, cid), headers=HEADERS, timeout=TIMEOUT)
    if resp.status_code != 200:
        return None, 0
    data = resp.content
    ctype = (resp.headers.get("content-type") or "").lower()
    if "pdf" not in ctype and not data.startswith(b"%PDF"):
        return None, len(data)
    if len(data) < MIN_REAL_REPORT_BYTES:
        return None, len(data)
    with pymupdf.open(stream=io.BytesIO(data), filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc), len(data)


def county_name(text):
    """The county the report is FOR, read from page 1 rather than from the id."""
    m = COUNTY_RE.search(text or "")
    return m.group(1).strip() if m else None


def contests(text):
    """Every contest in one canvass: [{title, precincts, reporting, candidates}].

    `title` is the header lines joined by " | " — these reports split a contest's
    jurisdiction, office and "(Vote for ...)" note across separate lines, and
    which line carries what varies by county and by year, so callers match a
    regex against the whole header rather than against a fixed field.
    """
    lines = [ln.strip() for ln in (text or "").split("\n")]
    anchors = [i for i, ln in enumerate(lines) if ln == ANCHOR]
    out = []
    for pos, idx in enumerate(anchors):
        head = []
        j = idx - 1
        while j >= 0 and len(head) < 4:
            ln = lines[j]
            if PCT_RE.match(ln):
                break                      # previous contest's last candidate row
            if ln and not ln.startswith("Page "):
                head.append(ln)
            j -= 1
        head.reverse()
        end = anchors[pos + 1] if pos + 1 < len(anchors) else len(lines)
        body = lines[idx:end]
        precincts = None
        if idx + 1 < len(lines) and PRECINCTS_RE.match(lines[idx + 1]):
            precincts = int(lines[idx + 1])
        candidates = []
        for k in range(len(body) - 3):
            name, party, votes, pct = body[k], body[k + 1], body[k + 2], body[k + 3]
            if not (PARTY_RE.match(party) and VOTES_RE.match(votes)):
                continue
            m = PCT_RE.match(pct)
            if not m or not name or name == ANCHOR or name.startswith("Page "):
                continue
            if NON_CANDIDATE_RE.match(name):
                continue
            count = int(votes.replace(",", ""))
            if count <= 0:
                continue
            candidates.append({"name": " ".join(name.split()),
                               "party": party.upper(),
                               "votes": count,
                               "pct": int(m.group(1))})
        candidates.sort(key=lambda c: -c["votes"])
        out.append({"title": " | ".join(head), "precincts": precincts,
                    "candidates": candidates})
    return out


def name_case(raw):
    """Title-case a canvass name without inventing punctuation.

    The canvasses print names in capitals ("DAVID DL MCCLEARY"). Casing them is
    unavoidable; adding periods, expanding initials or guessing an internal
    capital is not, so none of that happens here. "Mc" is the one exception and
    it is a rule rather than a guess: McCleary, never Mccleary. Prefixes this
    file cannot decide (De-, Van-, O') are left alone deliberately — Adams's own
    2018 canvass carries a DEMOSS whom local reporting spells DeMoss, and
    guessing which is right is exactly the error the honesty rules forbid.
    """
    out = []
    for word in str(raw).split():
        parts = []
        for piece in word.split("-"):
            if not piece:
                parts.append(piece)
                continue
            # QUOTED NICKNAMES keep their quotes and still get cased on the
            # LETTERS: Williamson's canvass prints JAMES "JIM" MARLO, and
            # capitalize() on a token whose first character is a quote lowercases
            # the whole thing — "jim". The quotes are peeled off, the inside is
            # cased by the rules below, and they are put back exactly as printed.
            lead = ""
            trail = ""
            while piece and not piece[0].isalnum():
                lead += piece[0]
                piece = piece[1:]
            while piece and not piece[-1].isalnum():
                trail = piece[-1] + trail
                piece = piece[:-1]
            if not piece:
                parts.append(lead + trail)
                continue
            up = piece.upper()
            if len(up) > 3 and up.startswith("MC"):
                parts.append(lead + "Mc" + up[2:].capitalize() + trail)
            elif len(piece) == 1:
                parts.append(lead + up + trail)
            elif len(up) == 2 and not set(up) & set("AEIOUY"):
                # RUN-TOGETHER INITIALS, which this county actually publishes:
                # District 6 is "DAVID DL MCCLEARY" in the general canvass and
                # "DAVID D.L. MCCLEARY" in the primary. Capitalising it as a
                # word gives "Dl", which reads as a name and is not one. A
                # two-letter token with no vowel is initials; one with a vowel
                # (Jo, Al, Ed) is a name and is left alone. The periods the
                # primary prints are NOT added back — the seating canvass is
                # what this row cites, and punctuation is not ours to invent.
                parts.append(lead + up + trail)
            else:
                parts.append(lead + piece.capitalize() + trail)
        out.append("-".join(parts))
    return " ".join(out)

