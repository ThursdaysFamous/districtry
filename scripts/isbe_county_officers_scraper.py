#!/usr/bin/env python3
"""
Illinois State Board of Elections County Officers Book (stage 1)
===============================================================
Extract every officer the state's own County Officers directory publishes —
name, title as printed, party, e-mail, phone, fax and mailing address, for all
102 counties at once — out of elections.il.gov's coofficers.pdf and into raw
JSON for scripts/build_county_board_chairs.py.

WHY THIS SOURCE EXISTS IN THIS REPO. The app already answers "which county am
I in" everywhere in Illinois and names that county's CLERK on the card, from
ISBE's election-authority directory (scripts/il_county_clerk_scraper.py). It
cannot name that county's BOARD CHAIR unless the county has been researched
one at a time, which is the whole expansion programme — every chair the app
names today arrived with its own county's scraper. This document names a chair
in all 102 in one fetch. That is the only thing it is good for, and the two
paragraphs below are the limits that make it safe to use at all.

WHAT THIS DOCUMENT IS NOT — MEASURED, NOT ASSUMED.

  1. IT IS NOT A ROSTER. "County Board Member" occurs ZERO times in the 107
     pages and the word "District" occurs ZERO times. The single occurrence of
     "Board Member" is in the preface, listing which offices' terms expire in
     2026. It is an OFFICERS directory: one row per office, and the board's
     only row is its chair. Nothing here can ever populate a county-board
     layer's districts, and no future edit should try.

  2. IT IS A DATED SNAPSHOT, AND ITS CHAIR COLUMN GOES STALE. Every page's
     footer carries the document's own "Last Updated" stamp (Monday, December
     15, 2025 in the edition this parser was written against) and the builder
     ships that date on every record so a card can say when it was true. It
     matters because it is measurably behind: on 2026-08-20, 16 of the 56
     counties whose boards this app already ships from the county's own source
     named a DIFFERENT chair, and in all eight checked live that day — Ogle,
     Grundy, Marshall, Iroquois, Logan, Shelby, Greene, Moultrie — the person
     ISBE names does not appear anywhere on the county's current board page,
     while the app's does. So this file is a FALLBACK for unresearched counties,
     never an override of a county's own publication. build_county_board_chairs
     cross-checks every record against the rosters already shipped and marks
     the disagreements rather than hiding them.

FETCH POSTURE. One GET of a static file; no form, no token, no JavaScript.
Note that the ASPX application on the same host (the clerk directory) 403s
GitHub's runner network while answering a developer machine — see
il_county_clerk_scraper.py's posture note — so if this ever starts failing in
CI with a 403 while working locally, that is the same edge block and not a
change in the document. `--pdf <path>` parses a copy already on disk, which is
both the offline development path and the escape hatch for that block.

HOW THE PAGE IS READ, and why by word POSITION rather than by line. Each
county owns one page laid out as a two-column table with a nested contact
block, and pymupdf's flattened text interleaves the columns: a phone number
lands between a street and its city, and the "Fax:" of one officer is emitted
inside the next officer's header. Every column, however, starts at a fixed x
(measured across all 103 county pages of the 2025-12-15 edition):

    x ~ 12    county name, once per page
    x ~ 23    office title            |  x ~ 204  officer name  |  x = 342 party
    x ~ 29    street, then "City, IL ZIP"
    x = 362   "Email:" / "Phone:" / "Fax:"    x ~ 390  the value

so a record is one HEADER line (the only kind carrying words in the name
column) plus every following line until the next header. Two edges are load
bearing and both are in the geometry constants below: a party can be wider
than its column ("(Non Partisan)" runs to x=362, the label column's x), which
is why party is read only on header lines; and the phone line and the city
line share a y band, which is why lines are split by x and not by text order.

WHAT THE PARSER DOES NOT REPAIR. Union County's Recorder row prints
"Stephanie" in the TITLE cell and "Cox Meisenheimer" in the name cell — a
mangled cell in the source, not a parse failure. Records whose title is
outside the vocabulary below are emitted with `titleUnknown` set and named in
a WARN line; they are never silently renamed, dropped, or guessed at.

Usage:
    python3 isbe_county_officers_scraper.py --out isbe-county-officers.json
    python3 isbe_county_officers_scraper.py --pdf coofficers.pdf --out raw.json
"""

import argparse
import datetime
import hashlib
import io
import json
import re
import sys

import pymupdf
import requests
from scraper_common import make_fail, require_robots_allowed, UA_CHROME_WIN_124  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = "https://elections.il.gov/Downloads/ElectionOperations/PDF/coofficers.pdf"
SOURCE_PAGE = "https://elections.il.gov/ElectionOperations/CountyOfficials.aspx"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
}
REQUEST_TIMEOUT = 60
FETCH_ATTEMPTS = 3

# --- page geometry, measured against the 2025-12-15 edition ----------------
FIRST_COUNTY_PAGE = 2          # 0 cover, 1 preface
COUNTY_NAME_X_MAX = 20.0       # the county heading starts at x ~ 12
LEFT_COLUMN_X_MAX = 200.0      # title on a header line, street on the others
NAME_COLUMN_X_MIN = 200.0
NAME_COLUMN_X_MAX = 335.0
PARTY_X_MIN = 335.0            # header lines only — "(Non Partisan)" is wide
LABEL_X_MIN = 355.0            # "Email:" / "Phone:" / "Fax:" and their values
BODY_Y_MIN = 45.0              # above this is the running head
BODY_Y_MAX = 740.0             # below this is the footer
LINE_TOLERANCE = 2.0           # two words are one line within this many points

# The section after the counties: six city boards of election commissioners
# plus Peoria County's. Different shape, different offices, not county rows.
END_SECTION_MARKER = "Boards of Election Commission"

FOOTER_PAGE_RE = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)")
LAST_UPDATED_RE = re.compile(
    r"Last Updated\s*\n?\s*([A-Z][a-z]+day,\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4})")
LABEL_RE = re.compile(r"^(Email|Phone|Fax):\s*(.*)$")
PHONE_RE = re.compile(r"^\(?(\d{3})\)?[\s.-]*(\d{3})[\s.-]*(\d{4})$")

# Illinois has 102 counties and the document is organised one per page. Both
# numbers are pinned: a short parse is a broken parse, not a smaller state.
EXPECTED_COUNTIES = 102
MIN_RECORDS_PER_COUNTY = 8

# Every title the 2025-12-15 edition prints, with its count. Not a filter —
# the parser emits whatever it finds — but anything outside it is flagged for
# a human, because a new office is news and a mangled cell looks the same.
KNOWN_TITLES = {
    "County Clerk", "Circuit Clerk", "Treasurer", "Sheriff", "State's Attorney",
    "Republican Party Chair", "Democratic Party Chair", "Recorder", "Coroner",
    "Regional Supt. of Schools", "Regional Supt. Of Schools",
    "Supervisor of Assessments", "Chair, County Board", "Chair, County Comm.",
    "Auditor", "Assessor", "County Board President", "Chief Executive Officer",
    "Chief Medical Examiner", "County Death Investigator",
    "County Election Commission Chair", "Executive Director",
}


fail = make_fail("isbe-county-officers")


def warn(msg):
    print("isbe-county-officers: WARN — %s" % msg, file=sys.stderr)


def fetch_pdf():
    """The document's bytes, or a loud failure. Never a partial file."""
    # ISBE refuses this project: www.elections.il.gov/robots.txt is a
    # BOM'd `User-agent: * / Disallow: /`, Last-Modified 2025-06-12, measured
    # 2026-09-25. The full record is in scripts/il_county_clerk_scraper.py's
    # main() and in scripts/robots_policy.py's `_parse`, whose BOM defect is why
    # a year-old refusal read as a permission. Nothing is fetched from this host;
    # files already built from it keep their records (CLAUDE.md, Adam 2026-09-19).
    require_robots_allowed(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                           label="isbe-county-officers")
    last = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            response = requests.get(SOURCE_URL, headers=HEADERS,
                                    timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                raise RuntimeError("HTTP %d" % response.status_code)
            body = response.content
            if not body.startswith(b"%PDF"):
                raise RuntimeError(
                    "response is not a PDF (starts %r) — an edge challenge page "
                    "answers 200 with HTML" % body[:16])
            return body
        except Exception as exc:  # noqa: BLE001 — every rung is reported
            last = exc
            print("isbe-county-officers: attempt %d/%d failed (%s)"
                  % (attempt, FETCH_ATTEMPTS, exc), file=sys.stderr)
    fail("could not fetch %s — last error: %s. If this is CI and a browser "
         "reaches the file, it is the elections.il.gov edge block (see the "
         "module docstring); re-run with --pdf on a retrieved copy."
         % (SOURCE_URL, last))


def page_lines(page):
    """[(y, [word, ...]), ...] in reading order, words carrying their x.

    A "line" here is a y band, not a text block: the phone value and the city
    line are printed at the same height in different columns, and the caller
    splits them apart by x.
    """
    words = sorted(page.get_text("words"), key=lambda w: (round(w[1], 1), w[0]))
    lines, current, top = [], [], None
    for word in words:
        if top is not None and abs(word[1] - top) > LINE_TOLERANCE:
            lines.append((top, current))
            current = []
            top = None
        if top is None:
            top = word[1]
        current.append(word)
    if current:
        lines.append((top, current))
    return lines


def joined(words):
    return " ".join(word[4] for word in words).strip()


def printed_page_number(page, index):
    """The page number the document prints on itself, for citation."""
    match = FOOTER_PAGE_RE.search(page.get_text())
    return int(match.group(1)) if match else index - 1


def parse_last_updated(doc, last_page):
    """The stamp every page carries, required to be unanimous.

    The whole point of shipping this document's date is that the date is
    trustworthy; 104 pages that disagree about it means the file is a splice
    of two editions and nothing here should be shipped until a human looks.
    """
    stamps = set()
    for index in range(FIRST_COUNTY_PAGE, last_page):
        match = LAST_UPDATED_RE.search(doc[index].get_text())
        if not match:
            fail("page %d carries no 'Last Updated' stamp — the footer this "
                 "file dates itself from is gone" % (index + 1))
        stamps.add(re.sub(r"\s+", " ", match.group(1)))
    if len(stamps) != 1:
        fail("pages disagree about the document date: %s" % sorted(stamps))
    text = stamps.pop()
    try:
        iso = datetime.datetime.strptime(text, "%A, %B %d, %Y").date().isoformat()
    except ValueError:
        fail("could not read %r as a date — the footer's format changed" % text)
    return iso, text


def clean_phone(value):
    match = PHONE_RE.match((value or "").strip())
    return "-".join(match.groups()) if match else (value or "").strip() or None


def parse_page(page, index):
    """(county name, [record, ...]) for one county page."""
    county, records, current = None, [], None
    printed = printed_page_number(page, index)
    for top, words in page_lines(page):
        if top < BODY_Y_MIN or top > BODY_Y_MAX:
            continue
        if words[0][0] < COUNTY_NAME_X_MAX:
            county, current = joined(words), None
            continue
        name_words = [w for w in words
                      if NAME_COLUMN_X_MIN <= w[0] < NAME_COLUMN_X_MAX]
        if name_words:
            # A header line: title | name | party, one officer's identity.
            title = joined([w for w in words if w[0] < LEFT_COLUMN_X_MAX])
            party = joined([w for w in words if w[0] >= PARTY_X_MIN])
            current = {
                "title": title or None,
                "name": joined(name_words),
                "party": party.strip("()") or None,
                "email": None,
                "phone": None,
                "fax": None,
                "addressLines": [],
                "page": printed,
            }
            if title and title not in KNOWN_TITLES:
                current["titleUnknown"] = True
            records.append(current)
            continue
        if current is None:
            continue
        label = LABEL_RE.match(joined([w for w in words if w[0] >= LABEL_X_MIN]))
        if label:
            key, value = label.group(1).lower(), label.group(2).strip()
            if value and value.lower() != "n/a":
                current[key] = clean_phone(value) if key != "email" else value
        street = joined([w for w in words if w[0] < LEFT_COLUMN_X_MAX])
        if street and street.lower() != "n/a":
            current["addressLines"].append(street)
    return county, records


def parse_document(doc):
    """{county name: {page, officers}}, and the index the county pages end at.

    A county is usually one page and sometimes two: Will has more offices than
    fit (a Chief Executive Officer and an Auditor besides the usual eleven) and
    runs onto a second page under a repeated heading. A repeat on the NEXT page
    is that continuation and is merged; a repeat anywhere else means the pages
    are out of order, which is a broken document rather than a long county.
    """
    counties, seen_on, last_page = {}, {}, doc.page_count
    for index in range(FIRST_COUNTY_PAGE, doc.page_count):
        text = doc[index].get_text()
        if END_SECTION_MARKER in text:
            last_page = index
            break
        if not text.strip():
            fail("page %d has no text layer — this document has always shipped "
                 "real text; an image-only edition needs a human, not OCR "
                 "bolted on here" % (index + 1))
        county, records = parse_page(doc[index], index)
        if not county:
            fail("page %d names no county" % (index + 1))
        for record in records:
            if not record["name"]:
                fail("%s has an officer row with no name" % county)
        if county in counties:
            if seen_on[county] != index - 1:
                fail("county %r appears on pages %d and %d, which do not "
                     "adjoin — the document's page order changed"
                     % (county, seen_on[county] + 1, index + 1))
            counties[county]["officers"].extend(records)
        else:
            counties[county] = {"page": records[0]["page"] if records else None,
                                "officers": records}
        seen_on[county] = index
    for county, entry in counties.items():
        if len(entry["officers"]) < MIN_RECORDS_PER_COUNTY:
            fail("%s yielded %d officer rows (floor %d) — the column geometry "
                 "has moved" % (county, len(entry["officers"]),
                                MIN_RECORDS_PER_COUNTY))
    if len(counties) != EXPECTED_COUNTIES:
        fail("parsed %d counties, expected %d — Illinois has 102 and the "
             "document publishes them one page each, Will County over two"
             % (len(counties), EXPECTED_COUNTIES))
    return counties, last_page


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="isbe-county-officers.json")
    parser.add_argument("--pdf", help="parse a local copy instead of fetching")
    args = parser.parse_args()

    if args.pdf:
        with open(args.pdf, "rb") as handle:
            body = handle.read()
        origin = args.pdf
    else:
        body = fetch_pdf()
        origin = SOURCE_URL

    digest = hashlib.sha256(body).hexdigest()
    doc = pymupdf.open(stream=io.BytesIO(body), filetype="pdf")
    counties, last_page = parse_document(doc)
    document_date, document_date_text = parse_last_updated(doc, last_page)

    officers = [rec for entry in counties.values() for rec in entry["officers"]]
    unknown = sorted({rec["title"] for rec in officers if rec.get("titleUnknown")})
    for title in unknown:
        warn("title %r is outside the known vocabulary — a new office, or a "
             "mangled cell like Union County's Recorder row" % title)

    payload = {
        "sourceUrl": SOURCE_URL,
        "sourcePage": SOURCE_PAGE,
        "sourceDocument": "Illinois State Board of Elections, County Officers",
        "origin": origin,
        "fetchedAt": datetime.datetime.now(datetime.timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "documentDate": document_date,
        "documentDateText": document_date_text,
        "pdfSha256": digest,
        "pdfBytes": len(body),
        "pageCount": doc.page_count,
        "countyPages": last_page - FIRST_COUNTY_PAGE,
        "counties": counties,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print("isbe-county-officers: %d counties, %d officer rows, updated %s "
          "(sha256 %s…) -> %s"
          % (len(counties), len(officers), document_date_text, digest[:12],
             args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
