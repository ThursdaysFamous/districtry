#!/usr/bin/env python3
"""
Scrape Marshall County's board roster out of the county's annual
"Offices & Committees" PDF.

Stage 1 of the two-stage pipeline (scripts/build_marshall_board_roster.py is
stage 2). Marshall publishes its board only inside a wide landscape table in
that PDF — the county's HTML directory lists names and districts but no
contact — and, usefully, the SAME table carries each district's whole-township
composition in its heading:

    DISTRICT #1 - Henry, Hopewell, LaPrairie, Saratoga, Whitefield

That composition is what the shipped board boundary is dissolved from
(scripts/build_marshall_board_districts.py), and because it lives in the same
document as the roster, the weekly drift check De Witt and Washington get
works here too — unlike Cass, whose composition sits in a separate PDF the
roster page merely links.

WHY POSITIONAL PARSING. The table's columns are Official / Title / Address /
City / Phone / Email / Cell-Work / Term, and a member's name runs one to four
words while the APPT-date suffix ("TODD PERONA APPT 10/12/23") pads it further.
Flattening a row to text and splitting on whitespace therefore cannot tell
where the name ends and the title begins. Words are banded by y and split by
the measured x boundaries instead — the Lee and LaSalle recipe, same reason.

ADDRESS AND CITY ARE READ AND DISCARDED. Both columns hold the member's
RESIDENCE (street plus its town). The fleet does not collect member residences
(the Madison precedent — a residence is not an office a resident can visit), so
those two columns are located precisely in order to be dropped, and nothing
downstream ever sees them.

BOTH NUMBER COLUMNS SHIP. The table has a Phone column and a column headed
"Cell/Work". Until 2026-10-17 a member got one number: the Phone column's, or
the Cell/Work column's when Phone was empty. Since Adam's ruling that day ("if
the official government source uses personal phone numbers, we publish those")
a member who has both gets both: the Phone column's number first, as printed,
then the Cell/Work number in `phonesExtra`. Every Cell/Work number is led by
"cell or work", because that is what the county's heading says and it does not
say which of the two a number is. Measured on 2026-10-17: 3 members print a
Phone number, 11 a Cell/Work number, 2 both, and no number is printed twice in
the document. The same column position holds "Fax" on the county officers'
table above the board, so the column is read only under a "Cell/Work" heading
inside the board section, and a fax number can never ship as a member's.

FETCH POSTURE: open. Plain requests with a browser UA returns the PDF.

Usage:
    python3 marshall_county_board_scraper.py [output.json]
    python3 marshall_county_board_scraper.py --pdf local.pdf [output.json]
"""

import json
import re
import sys
import time

from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    fetch, require_robots_once, UA_ROSTER_BOT,
)

try:
    import pdfplumber
except ImportError:                                    # pragma: no cover
    pdfplumber = None

SOURCE_URL = ("https://marshallcountyillinois.gov/wp-content/uploads/2026/01/"
              "2026-New-County-Board-Roster-.pdf")
ROSTER_PAGE = "https://marshallcountyillinois.gov/directory/county-board/"
UA = {"User-Agent": UA_ROSTER_BOT}

# Column left edges in PDF points, measured against the 2026 revision's header
# row (Official 24 / Title 142 / Address 213 / City 294 / Phone 328 /
# Email 381 / Cell-Work 517 / Term ~572).
COL_TITLE, COL_ADDRESS, COL_CITY = 138.0, 208.0, 290.0
COL_PHONE, COL_EMAIL, COL_CELL, COL_TERM = 324.0, 376.0, 512.0, 568.0

DISTRICT_RE = re.compile(r"DISTRICT\s*#\s*(\d+)\s*[-–]\s*(.+)$", re.I)
SECTION_RE = re.compile(r"COUNTY BOARD MEMBERS", re.I)
END_RE = re.compile(r"COMMITTEE ASSIGNMENTS", re.I)
HEADER_RE = re.compile(r"^\s*Official:", re.I)
# The heading the board section prints over the column at COL_CELL, and the
# label every number read from that column carries.
CELL_WORK_HEADING_RE = re.compile(r"^Cell\s*[/-]\s*Work:?$", re.I)
CELL_WORK_LABEL = "cell or work"
PHONE_RE = re.compile(r"(\d{3})\D?(\d{3})\D?(\d{4})")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# "TODD PERONA APPT 10/12/23" / "JUSTIN MEIERKORD Appt 09/19/21)"
APPT_RE = re.compile(r"\s*Appt\.?\s*[\d/]+\)?\s*$", re.I)
ROLE_RE = re.compile(r"^(Chairperson|Vice\s*Chairperson|Member)$", re.I)


# THE WEEKLY RUN DIED ON 2026-09-14 FOR A REASON NO STATUS CODE NAMES: the
# county's own URL answered HTTP 200 with 12,136 bytes of text/html where the
# roster PDF lives. Re-probed 2026-09-15 the same URL serves the PDF normally
# (200, 201,717 bytes, %PDF-), so the document did not move — the site briefly
# returned a page instead of the file. The %PDF guard below was right to refuse
# and is kept: a scraper that parsed that HTML would have shipped nothing or
# nonsense. What was missing is a RETRY, and the shared fetch() could not
# supply it, because its ladder retries 429 and 5xx and a 200 carrying the
# wrong body is neither. So the non-PDF body is itself the retry condition
# here, and the guard becomes the verdict only after the attempts are spent.
PDF_ATTEMPTS = 3
PDF_RETRY_GAP_S = 4.0


def fetch_pdf(url, attempts=PDF_ATTEMPTS):
    # THE COUNTY'S RULES ARE READ BEFORE THE PDF, with the identity this fetch
    # sends. marshallcountyillinois.gov had been recorded as answering every
    # client with a managed challenge; re-measured from a GitHub runner on
    # 2026-10-01, the vantage the weekly job crawls from, it serves a 185-byte
    # policy whose binding group matches none of the paths read here — the
    # roster PDF's own path included — on all three reads of a deliberate
    # re-measurement fifteen seconds apart.
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="marshall-board-scraper")
    last = None
    for attempt in range(attempts):
        resp = fetch(url, UA, timeout=90)
        if resp.content.startswith(b"%PDF"):
            return resp.content
        last = "%d bytes of %s" % (len(resp.content),
                                   resp.headers.get("content-type"))
        if attempt + 1 < attempts:
            time.sleep(PDF_RETRY_GAP_S * (attempt + 1))
    raise RuntimeError("%s did not return a PDF after %d attempts (last: %s)"
                       % (url, attempts, last))


# Words on one visual row are not perfectly aligned: the Vice Chairperson's
# name sits at y=361.56 while his title sits at 362.02. Fixed-width bins
# (round(top/4)) put those in DIFFERENT bins and silently dropped him from the
# roster — 11 members instead of 12, with nothing failing. Rows are therefore
# CLUSTERED by proximity instead, which has no boundary to straddle.
ROW_TOLERANCE_PT = 3.0


def rows_of(page):
    """Words grouped into rows by vertical proximity, each sorted left to right."""
    words = sorted(page.extract_words(), key=lambda w: (w["top"], w["x0"]))
    row, anchor = [], None
    for w in words:
        if anchor is None or abs(w["top"] - anchor) <= ROW_TOLERANCE_PT:
            if anchor is None:
                anchor = w["top"]
            row.append(w)
        else:
            yield sorted(row, key=lambda x: x["x0"])
            row, anchor = [w], w["top"]
    if row:
        yield sorted(row, key=lambda x: x["x0"])


def cell(row, lo, hi):
    return " ".join(w["text"] for w in row if lo <= w["x0"] < hi).strip()


def tidy_word(word):
    """Title-case an ALL-CAPS surname without flattening the ones that carry an
    internal capital — MCLAUGHLIN and MCGLASSON must not become Mclaughlin and
    Mcglasson. Only the Mc/Mac/O' families are re-capitalized, because those are
    the ones a blanket .capitalize() provably gets wrong; anything else is left
    as the county wrote it rather than guessed at."""
    if not word.isupper():
        return word
    m = re.match(r"^(MC|MAC|O')([A-Z][A-Z']*)$", word)
    if m:
        head = m.group(1).capitalize() if m.group(1) != "O'" else "O'"
        return head + m.group(2).capitalize()
    return word.capitalize()


def tidy_name(caps):
    name = APPT_RE.sub("", caps).strip()
    return " ".join(tidy_word(w) for w in name.split())


def main():
    args = sys.argv[1:]
    pdf_path = None
    if "--pdf" in args:
        i = args.index("--pdf")
        pdf_path = args[i + 1]
        args = args[:i] + args[i + 2:]
    if pdfplumber is None:
        print("marshall-board-scraper: FAIL — pdfplumber is required "
              "(pip install -c scripts/requirements.txt pdfplumber)", file=sys.stderr)
        sys.exit(1)

    if pdf_path:
        with open(pdf_path, "rb") as f:
            data = f.read()
    else:
        data = fetch_pdf(SOURCE_URL)

    import io
    records, compositions = [], {}
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        # How many times each number is printed in the whole document: one
        # printed for two or more officials is an office line, and is never
        # added to a member as a second number.
        printed = {}
        for page in pdf.pages:
            for groups in PHONE_RE.findall(page.extract_text() or ""):
                printed["-".join(groups)] = printed.get("-".join(groups), 0) + 1
        in_board, district, cell_heading = False, None, None
        for page in pdf.pages:
            for row in rows_of(page):
                line = " ".join(w["text"] for w in row).strip()
                if SECTION_RE.search(line):
                    in_board, cell_heading = True, None
                    continue
                if in_board and END_RE.search(line):
                    in_board = False
                    continue
                if not in_board:
                    continue
                if HEADER_RE.match(line):
                    cell_heading = cell(row, COL_CELL, COL_TERM)
                    continue
                m = DISTRICT_RE.search(line)
                if m:
                    district = m.group(1)
                    compositions[district] = m.group(2).strip()
                    continue
                if district is None:
                    continue
                name = cell(row, 0, COL_TITLE)
                title = cell(row, COL_TITLE, COL_ADDRESS)
                if not name or not ROLE_RE.match(title):
                    continue
                # Address and City are located here ONLY so they are dropped:
                # both are the member's residence. See the module header.
                phone = cell(row, COL_PHONE, COL_EMAIL)
                email = cell(row, COL_EMAIL, COL_CELL)
                cellwork = cell(row, COL_CELL, COL_TERM)
                term = cell(row, COL_TERM, 10 ** 6)

                # The Phone column's numbers first, as printed; then the
                # Cell/Work column's, under the county's heading, and only
                # where the board section's heading over that column says
                # Cell/Work (the same position is "Fax" elsewhere).
                numbers = [(None, "-".join(g)) for g in PHONE_RE.findall(phone)]
                if cell_heading and CELL_WORK_HEADING_RE.match(cell_heading):
                    numbers += [(CELL_WORK_LABEL, "-".join(g))
                                for g in PHONE_RE.findall(cellwork)]
                labelled, taken = [], set()
                for label, number in numbers:
                    if number in taken:
                        continue
                    if labelled and printed.get(number, 0) > 1:
                        continue  # an office line, not this member's own
                    taken.add(number)
                    labelled.append("%s %s" % (label, number) if label else number)
                em = EMAIL_RE.search(email)
                role = None
                if re.match(r"^Vice", title, re.I):
                    role = "Vice-Chairperson"
                elif re.match(r"^Chairperson", title, re.I):
                    role = "Chairperson"
                records.append({
                    "name": tidy_name(name),
                    "district": district,
                    "role": role,
                    "phone": labelled[0] if labelled else None,
                    "phonesExtra": labelled[1:],
                    "email": em.group(0).lower() if em else None,
                    "termExpires": int(term) if re.fullmatch(r"\d{4}", term) else None,
                    "composition": compositions.get(district),
                })

    if not records:
        print("marshall-board-scraper: FAIL — zero member rows parsed; the PDF's "
              "column layout may have changed (see the measured x boundaries)",
              file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": SOURCE_URL, "rosterPage": ROSTER_PAGE,
                      "records": records}, indent=2, ensure_ascii=False)
    if args:
        with open(args[0], "w", encoding="utf-8") as f:
            f.write(out)
        print("marshall-board-scraper: %d records -> %s" % (len(records), args[0]))
    else:
        print(out)


if __name__ == "__main__":
    main()
