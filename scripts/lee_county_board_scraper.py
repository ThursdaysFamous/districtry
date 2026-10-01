#!/usr/bin/env python3
"""
Scrape the Lee County Board's Member Contact List into the intermediate JSON
build_lee_county_board_roster.py consumes.

SOURCE. The county's /419/Member-Contact-List is not an HTML page — the CMS
serves a PDF at that URL — and it is the only place Lee publishes the board's
membership. The County Board landing page names the Chair and Vice-Chair and
nobody else, so this document is the roster of record. It carries, per member:
district, name, political party, the year that seat is next up for election,
and a county e-mail address. Header stamped "Revised 04/24/26".

WHY POSITIONAL PARSING. pypdf's line extraction reads this document as two
separate blocks — twenty name rows, then twenty e-mail addresses in a DIFFERENT
order — because the e-mail column is a distinct text object. Pairing those by
sequence would silently mis-assign addresses; pairing them by matching an
initial against a surname would be an inference the document does not make. The
words carry x/y positions, so the row is recoverable exactly as printed:
pdfplumber, banded by y, split by x. That is the LaSalle recipe, for the same
reason LaSalle needed it.

The pairing matters concretely. Nineteen of the twenty addresses are
first-initial + surname, and the twentieth is the Chair's: Robert Olson's
address is `leecochair@countyoflee.org`, which no name-matching rule would ever
produce. Read by row, it is simply what his row says.

FETCH POSTURE: open. Plain `requests` with a browser UA gets the PDF; there is
no challenge.

Usage:
    python3 lee_county_board_scraper.py --out lee_county_board_raw.json
    python3 lee_county_board_scraper.py --out out.json --pdf local.pdf
"""

import argparse
import collections
import datetime
import io
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

SOURCE_URL = "https://www.leecountyil.com/419/Member-Contact-List"
BOARD_PAGE = "https://www.leecountyil.com/291/County-Board"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REQUEST_TIMEOUT = 120

# Column boundaries in PDF points, measured against the 2026-04-24 revision.
# Generous windows: the district digit sits at x~38, names start at x~69, party
# at x~193, the election year at x~286 and the e-mail at x~340.
COL_DISTRICT = (20, 60)
COL_NAME = (60, 185)
COL_PARTY = (185, 275)
COL_YEAR = (275, 330)
COL_EMAIL = (330, 600)

# One member's name sits 3pt below the rest of its row, so bands are merged at a
# tolerance rather than requiring exact tops.
ROW_BAND_PT = 8

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
YEAR_RE = re.compile(r"^(20\d{2})$")
DISTRICT_RE = re.compile(r"^(\d{1,2})$")

MIN_MEMBERS = 20
MIN_DISTRICTS = 4


def fetch_pdf(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-lee-county-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError("%s did not return a PDF (got %d bytes of %s) — the "
                           "CMS may have replaced the document with a page"
                           % (url, len(resp.content), resp.headers.get("Content-Type")))
    return resp.content


def rows_from(pdf_bytes, warnings, vacancies):
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required "
                           "(pip install -c scripts/requirements.txt pdfplumber)")
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if not pdf.pages:
            raise RuntimeError("the roster PDF has no pages")
        words = []
        for page in pdf.pages:
            words.extend(page.extract_words(use_text_flow=False, keep_blank_chars=False))

    # Clustered by PROXIMITY, not by rounding into fixed buckets. One member's
    # name is set 3pt lower than the rest of its row, and a fixed band boundary
    # fell right between them — which produced a nameless row and a 19-member
    # payload the floor below rejected. Rounding is the wrong tool for "same
    # line": two words 1pt apart can round to different buckets.
    bands = []
    for word in sorted(words, key=lambda w: w["top"]):
        if bands and word["top"] - bands[-1][0] <= ROW_BAND_PT:
            bands[-1][1].append(word)
        else:
            bands.append((word["top"], [word]))
    bands = [words_in for _top, words_in in bands]

    records = []
    for band in bands:
        cells = collections.defaultdict(list)
        for word in sorted(band, key=lambda w: w["x0"]):
            x = word["x0"]
            for name, (lo, hi) in (("district", COL_DISTRICT), ("name", COL_NAME),
                                   ("party", COL_PARTY), ("year", COL_YEAR),
                                   ("email", COL_EMAIL)):
                if lo <= x < hi:
                    cells[name].append(word["text"])
                    break
        district = " ".join(cells.get("district", []))
        if not DISTRICT_RE.match(district.strip()):
            continue  # header, title and footer bands
        name = " ".join(cells.get("name", [])).strip()
        email = " ".join(cells.get("email", [])).strip()
        year = " ".join(cells.get("year", [])).strip()
        party = " ".join(cells.get("party", [])).strip()
        if not name:
            # A district row printed with NO name is a vacant seat, not a parse
            # miss — measured 2026-08-02, when the county published District 3
            # with a row carrying the district number and nothing else (y=357.6
            # in the PDF: a lone "3", no party, no term, no address). Dropping it
            # cost a seat and tripped the 20-member floor, which is the floor
            # working; but "19 members" and "19 members and a vacancy" are
            # different claims about the board, and only the second is true.
            # Counted here and named nowhere, the Livingston/Stephenson posture.
            warnings.append("district %s row carries no name — recorded as a "
                            "VACANT seat, not dropped" % district)
            vacancies.append(str(int(district)))
            continue
        if email and not EMAIL_RE.match(email):
            warnings.append("%s: %r is not an e-mail address — dropped rather than "
                            "shipped as one" % (name, email))
            email = ""
        if year and not YEAR_RE.match(year):
            warnings.append("%s: %r is not an election year — dropped" % (name, year))
            year = ""
        records.append({
            "district": str(int(district)),
            "name": name,
            "party": party or None,
            "next_election": year or None,
            "email": email or None,
        })
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    warnings, vacancies = [], []
    try:
        pdf_bytes = open(args.pdf, "rb").read() if args.pdf else fetch_pdf(SOURCE_URL)
        records = rows_from(pdf_bytes, warnings, vacancies)
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    districts = sorted({r["district"] for r in records} | set(vacancies), key=int)
    problems = []
    # The floor counts SEATS, not names: a vacancy is still a seat the county
    # apportioned, and the board did not shrink because one is unfilled. Counting
    # names here would make an ordinary vacancy indistinguishable from the parse
    # regression this floor exists to catch.
    seats = len(records) + len(vacancies)
    if seats < MIN_MEMBERS:
        problems.append("%d seats (%d named + %d vacant) < floor %d"
                        % (seats, len(records), len(vacancies), MIN_MEMBERS))
    if len(districts) < MIN_DISTRICTS:
        problems.append("%d districts < floor %d" % (len(districts), MIN_DISTRICTS))
    # A row whose e-mail landed in the wrong column would show up as a member
    # with none, which is the failure this document's two-block layout invites.
    without_email = [r["name"] for r in records if not r["email"]]
    if len(without_email) > 2:
        problems.append("%d members carry no e-mail (%s) — the column split "
                        "probably moved" % (len(without_email), ", ".join(without_email[:4])))
    if problems:
        for problem in problems:
            print("  FAIL: %s" % problem, file=sys.stderr)
        print("FATAL: refusing to write a payload that lost coverage", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for record in records:
        record["source_url"] = SOURCE_URL
        record["scraped_at"] = scraped_at
    payload = {
        "county": "Lee",
        "source_url": SOURCE_URL,
        "board_page": BOARD_PAGE,
        "scraped_at": scraped_at,
        "members": records,
        # Empty list when the board is full, so the builder needs no special
        # case and the field never has to be guessed at from a count mismatch.
        "vacancies": vacancies,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    per = collections.Counter(r["district"] for r in records)
    vacant_note = ""
    if vacancies:
        vacant_note = (" + %d VACANT seat(s) in district %s"
                       % (len(vacancies), ", ".join(sorted(set(vacancies), key=int))))
    print("scraped %d members%s across %d districts (%s), %d with e-mail -> %s"
          % (len(records), vacant_note, len(districts),
             ", ".join("D%s=%d" % (d, per[d]) for d in districts),
             sum(1 for r in records if r["email"]), args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
