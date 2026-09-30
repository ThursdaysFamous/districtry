#!/usr/bin/env python3
"""
Scrape Mason County's own County Directory into the shared municipal-officials
intermediate JSON.

THE SOURCE IS A GOOGLE SHEET THE COUNTY CLERK PUBLISHES, and that is the whole
reason this scraper can exist. Mason's roster used to be a scan that no parser
could read (see build_mason_board_roster.py). On 2026-08-04 the Clerk's
elections office shared the county's directory as a live spreadsheet, readable
by anyone with the link — so the same document that had to be transcribed by
hand now exports as CSV. This reads the "Municipalities" tab, which carries all
nine of the county's municipalities with their FULL governing body: president
or mayor, clerk, treasurer, and every trustee or alderman, each with a term
year and, where the county has one, a phone number.

NO RESIDENCE DATA LEAVES THIS SCRAPER, NOT EVEN THE TOWN. Every row in the
directory carries the official's HOME address, and one Mason County Board
member's row reads "SECURED ADDRESS" — she is in an address-confidentiality
program. build_mason_board_roster.py already extends the fleet's no-home-
addresses rule one column further for exactly that reason: shipping the town
for everyone else would make the protected row the one that stands out. The
same rule is applied here and asserted below, because the municipal tab has
the same column and the same people's neighbours in it.

DEPARTMENT HEADS ARE SKIPPED, per the fleet posture — Havana's directory
lists a City Attorney, Public Works Director, Chief of Police, Deputy Chief of
Police and Fire Marshal, none of which is an elected municipal officer.

VACANCIES ARE COUNTED AND NEVER NAMED. The directory writes "Vacant" in the
name column (a Forest City trustee, two Havana staff posts). Those rows are
recorded as vacancies on the municipality rather than shipped as a person.

COLUMNS MOVE, SO NOTHING IS READ BY POSITION. The sheet's phone column is
simply left empty on rows where the county has no number, which slides the term
year left into it — row-by-row, not consistently. Every value is therefore
classified by SHAPE (a phone matches the phone pattern, a term is a 4-digit
year, the rest is a note), which is what the Marshall scraper learned to do
with the same class of document.

Usage:
    python3 scripts/mason_municipal_officials_scraper.py --out /tmp/mason.json
    python3 scripts/mason_municipal_officials_scraper.py --csv local.csv --out ...
"""

import argparse
import csv
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import HEADERS, REQUEST_TIMEOUT  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import require_robots_once  # noqa: E402  (shared machinery)

COUNTY = "Mason"
SHEET_ID = "1pffRO68CZLhQkVmFKlmDy_J1YyaDlYDkS2TATLpeNkQ"
SHEET_TAB = "Municipalities"
SHEET_URL = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq"
             "?tqx=out:csv&sheet=%s" % (SHEET_ID, SHEET_TAB.replace(" ", "%20")))
OFFICIALS_PAGE = "https://masoncountyil.gov/county-clerk/"
SOURCE_NOTE = ('Mason County Clerk & Recorder, "Mason County Directory" '
               "(Municipalities tab), the county's own published spreadsheet, "
               "shared by the Clerk's elections office 2026-08-04")

# A gviz request for a tab name it does not recognise does NOT fail — it
# silently returns the FIRST tab. That would hand this scraper the County Board
# tab and it would find no municipalities, so the fetch asserts the sheet it got
# is the one it asked for.
TAB_FINGERPRINT = re.compile(r"(?i)village of|city of")

MUNI_RE = re.compile(r"(?i)^(Village|City|Town) of ([A-Z][A-Za-z.'\- ]+?)"
                     r"(?:\s+\d.*)?$")
HEADER_RE = re.compile(r"(?i)^name$")
PHONE_RE = re.compile(r"^[-(]?\d{3}[)/.\- ]\s*\d{3}[-./ ]\d{4}")
YEAR_RE = re.compile(r"^(20\d{2})$")
VACANT_RE = re.compile(r"(?i)^vacant$")
WARD_RE = re.compile(r"(?i)^(alderman|alderperson|alderwoman|trustee)\s*,?\s*"
                     r"(\d+)(?:st|nd|rd|th)\s+ward")

HEAD_OFFICES = {"mayor", "president", "village president"}
BOARD_OFFICES = {"trustee", "alderman", "alderperson", "alderwoman"}
OFFICER_OFFICES = {"clerk", "treasurer", "village clerk", "city clerk",
                   "city treasurer", "village treasurer", "collector"}
# Appointed staff the directory lists beside the elected body. Skipped rather
# than shipped: none is a municipal officer, and two of them are police.
SKIP_OFFICES = ("attorney", "public works", "chief of police", "police",
                "fire marshal", "zoning", "economic development", "engineer",
                "superintendent", "supervisor", "administrator", "coordinator",
                "director", "maintenance", "water", "sewer", "building")


def fail(msg):
    print("mason-municipal: FATAL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def fetch_csv(path=None):
    if path:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    require_robots_once(SHEET_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-mason-municipal-officials-scraper")
    resp = requests.get(SHEET_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def classify(cells):
    """Split a row's trailing cells into (phone, term_expires, notes).

    Shape, never position — see the header. The first phone-shaped cell is the
    phone, the first bare 4-digit year is the term, everything else is a note.
    """
    phone = term = None
    notes = []
    for cell in cells:
        value = cell.strip()
        if not value or value == "-":
            continue
        if phone is None and PHONE_RE.match(value):
            phone = value
            continue
        year = YEAR_RE.match(value)
        if term is None and year:
            term = year.group(1)
            continue
        notes.append(value)
    return phone, term, notes


def scrape(text):
    rows = [[c.strip() for c in row] for row in csv.reader(io.StringIO(text))]
    if not any(TAB_FINGERPRINT.search(" ".join(r)) for r in rows[:40]):
        fail("the %r tab did not come back — a gviz request for an unknown tab "
             "silently returns the first sheet, and this is not it" % SHEET_TAB)

    municipalities, officials = [], []
    vacancies = {}
    current = None
    for row in rows:
        cells = [c for c in row if c]
        if not cells:
            continue
        first = cells[0]

        muni = MUNI_RE.match(first)
        if muni:
            current = "%s of %s" % (muni.group(1).title(), muni.group(2).strip())
            if current not in municipalities:
                municipalities.append(current)
                vacancies[current] = 0
            continue
        if current is None or HEADER_RE.match(first) or len(cells) < 2:
            continue

        office_raw = first.rstrip(":").strip()
        lowered = office_raw.lower()
        if any(skip in lowered for skip in SKIP_OFFICES):
            continue

        name = cells[1].strip()
        if VACANT_RE.match(name):
            vacancies[current] += 1
            continue
        if not name or name.lower() in ("name", "-"):
            continue

        ward = None
        ward_match = WARD_RE.match(office_raw)
        if ward_match:
            office = ward_match.group(1).title()
            ward = ward_match.group(2)
        else:
            office = office_raw.title()
        key = office.lower()
        if key not in HEAD_OFFICES and key not in BOARD_OFFICES and key not in OFFICER_OFFICES:
            continue

        # cells[2] is the HOME ADDRESS column and is never read past this point.
        phone, term, notes = classify(cells[3:])
        record = {
            "jurisdiction": current,
            "office": office,
            "name": name,
            "district": ward,
            "party": None,
            "appointed": any("appoint" in n.lower() for n in notes),
            "term_expires": term,
            "person_phone": phone,
            "source_url": OFFICIALS_PAGE,
            "source_note": SOURCE_NOTE,
        }
        officials.append(record)

    return municipalities, officials, vacancies


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", help="parse a local CSV instead of fetching")
    args = ap.parse_args()

    municipalities, officials, vacancies = scrape(fetch_csv(args.csv))

    if len(municipalities) < 9:
        fail("found %d municipalities, expected at least 9 — Mason has nine "
             "incorporated places and the directory covers all of them"
             % len(municipalities))
    heads = [o for o in officials if o["office"].lower() in HEAD_OFFICES]
    if len(heads) < len(municipalities):
        missing = sorted(set(municipalities) - {h["jurisdiction"] for h in heads})
        fail("no head of government for %s" % ", ".join(missing))
    if len(officials) < 60:
        fail("only %d officials parsed — the directory carries a full board for "
             "every municipality, so this is a parse failure" % len(officials))

    # The residence rule, asserted rather than assumed. Nothing in this payload
    # may carry an address or a home town: one Mason official's address is
    # legally protected, and a town-for-everyone-else roster would single her
    # out. See build_mason_board_roster.py.
    blob = json.dumps(officials).lower()
    for banned in ("address", "\"city\"", "residence", "home"):
        if banned in blob:
            fail("a residence field reached the payload (%r) — Mason ships no "
                 "address and no home town for anyone" % banned)

    payload = {
        "county": COUNTY,
        "officials_page": OFFICIALS_PAGE,
        "source_note": SOURCE_NOTE,
        "municipalities": sorted(municipalities),
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")
    total_vacant = sum(vacancies.values())
    print("scraped %s: %d municipalities, %d officials (%d heads%s) -> %s"
          % (COUNTY, len(municipalities), len(officials), len(heads),
             ", %d vacant seat(s) counted and not named" % total_vacant
             if total_vacant else "", args.out))


if __name__ == "__main__":
    main()
