#!/usr/bin/env python3
"""
Build nc/data/app/nc-conservation-boards.json: the supervisors of the soil
and water conservation district that covers each of North Carolina's 100
counties, read from the state's District Directory, for the County card.

    python3 nc/scripts/build_nc_conservation_boards.py            # read, parse, write
    python3 nc/scripts/build_nc_conservation_boards.py --check    # offline
    python3 nc/scripts/build_nc_conservation_boards.py --watch    # has any name changed?

The work is scripts/conservation_boards.py, which says what is read, what is
carried and what the checks prove. This file says where North Carolina
publishes its boards and how to read the publication.

THE SOURCE. The District Directory of the Division of Soil and Water
Conservation (NC Department of Agriculture and Consumer Services), one PDF at
https://www.ncagr.gov/divisions/soil-water/district-directory/open, linked from
the division's District Directory page, which says it includes "district
supervisors, staff, and meeting information". Read on 2026-10-16 it was 242
pages printed from the division's own database on 29 September 2026 (every
page's footer carries that date, which the card shows), with three sections
per county: its supervisors, its district staff and its federal staff. Only
the supervisor sections are read. The address appears to serve whichever
edition is current (inferred: it ends "/open" and names no edition).

WHAT IT GIVES. For each supervisor: first and last name, office on the board
(chair, vice chair, secretary-treasurer and so on), whether the seat is
elected or appointed, the term ("22-26" or "24-28"), a training number and the
month and year the member started. Carried: the name exactly as printed, the
office, elected or appointed, and the term. Not carried: the training number,
the start date and the notes on earlier service that 18 rows carry.

HOW THE BOARDS ARE CHOSEN, as the division's About Districts page states it
(read 2026-10-16): five supervisors, three elected without party labels at the
regular election of county officers and two appointed by the state Soil and
Water Conservation Commission on the board's recommendation, each for four
years. The state has 96 districts: 95 follow county lines, and the Albemarle
district covers Camden, Chowan, Currituck, Pasquotank and Perquimans
counties with 17 supervisors, which the directory lists county by county,
each county with its own chair (Camden 3, Chowan 4, Currituck 3, Pasquotank 3,
Perquimans 4). Each of those counties' cards names the members listed for
it and says the district covers all five. Three other districts carry a name
of their own: Brown Creek (Anson County), Fishing Creek (Halifax) and New
River (Ashe).

SIX SEATS ARE LISTED WITH NO NAME: a row with a training number, elected or
appointed and a term, and no name and no "Vacant" label (Bertie, Columbus,
Davidson, Davie, Person and Warren on 2026-10-16). The card shows each as a
seat with no name listed, never as a vacancy, because the directory does not
say the seat is vacant.

WHAT IS KNOWN TO BE OUT OF DATE, measured on 2026-10-16 against the State
Board of Elections' precinct results: of the 197 named winners of the 2022
supervisor elections, 169 are listed in an elected 2022-2026 seat, 8 in an
appointed seat and 20 not at all; of the 100 winners of 2024, 93 are listed
in an elected 2024-2028 seat. The directory is followed as printed, because
the state's own record of who now holds a seat is the directory and the
Commission's appointment papers, and the results say only who won.

TURNOVER. Every county elects two supervisors on 3 November 2026, and the
terms of the 96 appointed seats marked 2022-2026 end then too. The directory
will be out of date until the division prints a new edition; WATCH.md carries
the re-read.

TERMS OF USE. ncagr.gov's footer links the nc.gov "Disclaimer & Terms of
Use": "Unless otherwise noted on an individual document, the State of North
Carolina grants permission to copy and distribute non-image files, documents,
and information for non-commercial use, provided they are copied and
distributed without alteration and appropriately cite to the source." The
directory carries no notice of its own. Names are printed exactly as the
directory prints them, and every card cites the directory.

PRIVACY. The supervisor sections carry no contact details. The staff sections
carry staff e-mail addresses and telephone numbers, some of them mobile
numbers, and the PDF's own metadata names the member of staff who printed it;
none of that is read. The Commission's appointment papers, which record the
changes between editions, reproduce each nominee's nomination form with a
home address, personal e-mail, telephone, age, occupation and education; they
are not read at all.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
nc-conservation-boards): the state's only list of who holds these seats is a
242-page PDF printed from a database the public cannot query; a seat listed
with no name carries nothing to say whether it is vacant; the State Board of
Elections publishes who won the elected seats and nothing names the appointed
ones outside the directory and the Commission's papers; those papers publish
nominees' home contact details beside their names; one month's appointment
papers (July 2026) are linked from the Commission's meetings page and answer
404; and the state association's site (ncaswcd.org) did not answer on
2026-10-16.
"""

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import conservation_boards as cb  # noqa: E402

DIRECTORY = "https://www.ncagr.gov/divisions/soil-water/district-directory/open"

# The Albemarle district's supervisors by county, as the directory lists them
# on 2026-10-16. Every other district has five.
ALBEMARLE = {"Camden": 3, "Chowan": 4, "Currituck": 3, "Pasquotank": 3, "Perquimans": 4}

HEADER_RE = re.compile(r"^\s*SWCD County:\s+(\S.*?)(?:\s{2,}|$)")
PAGE_RE = re.compile(r"^\s*Page \d+ of \d+")
FOOTER_DATE_RE = re.compile(r"Page \d+ of \d+\s+[A-Z][a-z]+day, ([A-Z][a-z]+ \d{1,2}, \d{4})")
UID_RE = re.compile(r"\b\d{2}-\d{3}\b")
CHOSEN_RE = re.compile(r"\b(Elected|Appointed)\b")
TERM_RE = re.compile(r"\b(\d{2})-(\d{2})\b")
YEAR_END_RE = re.compile(r"\b(19|20)\d\d\s*$")
OFFICE_RE = re.compile(r"^(Chair|Chairman|Chairwoman|Vice[ -]Chair(man|woman)?|Secretary|Treasurer|"
                       r"Secretary[ -/]Treasurer|Financial Officer)$")
SECTION_TITLE_RE = re.compile(r"^(.+?)\s+-\s+(.+)$")


def iso(printed):
    return datetime.datetime.strptime(printed, "%B %d, %Y").date().isoformat()


def sections(text):
    """[(title, county, lines)] for every SUPERVISOR INFO section, the title
    being the line printed above the section's "SWCD County:" header."""
    lines = text.split("\n")
    out = []
    title = county = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = HEADER_RE.match(line)
        if m:
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            title = lines[j].strip() if j >= 0 else None
            county = m.group(1).strip()
        if "SUPERVISOR INFO" in line:
            body = []
            k = i + 1
            while k < len(lines) and not PAGE_RE.match(lines[k]):
                body.append(lines[k])
                k += 1
            out.append((title, county, body))
            i = k
        i += 1
    return out


def members(county, body):
    """The supervisors one section lists. A row is two lines: the first name,
    office, training number, elected or appointed and start year, then the
    last name, term and start month; notes on earlier service may follow."""
    rows = [r for r in body if r.strip()
            and not r.strip().startswith(("First / Middle", "Last Name / Suffix"))]
    out = []
    r = 0
    while r < len(rows):
        first_line = rows[r]
        chosen = CHOSEN_RE.search(first_line)
        uid = UID_RE.search(first_line)
        if not (chosen and (uid or YEAR_END_RE.search(first_line))):
            raise RuntimeError("%s: a supervisor line this reader cannot read: %r"
                               % (county, first_line.strip()))
        left = first_line[:uid.start()] if uid else first_line[:chosen.start()]
        parts = [p for p in re.split(r"\s{2,}", left.strip()) if p]
        if len(parts) == 1 and OFFICE_RE.match(parts[0]):
            parts = ["", parts[0]]
        first = parts[0] if parts else ""
        office = " ".join(parts[1:])
        if r + 1 >= len(rows):
            raise RuntimeError("%s: a supervisor's row ends before its term: %r"
                               % (county, first_line.strip()))
        second = rows[r + 1]
        term = TERM_RE.search(second)
        if not term:
            raise RuntimeError("%s: a supervisor's second line carries no term: %r"
                               % (county, second.strip()))
        last = second[:term.start()].strip()
        r += 2
        while r < len(rows) and not CHOSEN_RE.search(rows[r]):
            r += 1
        member = {}
        name = cb.clean("%s %s" % (first, last))
        if name:
            member["name"] = name
        else:
            member["unlisted"] = True
        if office:
            member["role"] = cb.clean(office)
        member["chosen"] = chosen.group(1).lower()
        member["term"] = "20%s-20%s" % term.groups()
        out.append(member)
    return out


def parse(url, body, county):
    text = cb.pdf_text(body)
    printed = sorted({iso(d) for d in FOOTER_DATE_RE.findall(text)})
    dated = printed[-1] if printed else cb.pdf_date(body)
    boards = []
    for title, where, rows in sections(text):
        if not where:
            raise RuntimeError("a supervisor section with no county above it")
        m = SECTION_TITLE_RE.match(title or "")
        if m and cb.county_key(m.group(2)) == cb.county_key(where):
            name = m.group(1)
        else:
            name = title or where
        boards.append({
            "county": where,
            "name": "%s Soil and Water Conservation District" % name,
            "members": members(where, rows),
            "dated": dated,
            "_district": name,
        })
    # A district the directory lists in county sections covers them all.
    covers = {}
    for b in boards:
        covers.setdefault(b["_district"], []).append(b["county"])
    for b in boards:
        counties = sorted(covers[b["_district"]])
        if len(counties) > 1:
            b["counties"] = counties
            b["note"] = ("The %s district covers %s counties, and the state's directory lists "
                         "its supervisors county by county; these are the ones it lists for "
                         "%s County." % (b["_district"], join(counties), b["county"]))
        del b["_district"]
    return boards


def join(names):
    return ", ".join(names[:-1]) + " and " + names[-1]


def seats(board):
    if board.get("counties"):
        return ALBEMARLE.get(board["county"], 0)
    return 5


SPEC = cb.Spec(
    tag="nc",
    label="build_nc_conservation_boards",
    user_agent="districtry/1.0 (+https://districtry.com/nc/)",
    parse=parse,
    seats=seats,
    member_keys=("role", "chosen", "term"),
    documents=(DIRECTORY,),
    card_claims=(
        "three elected by the county's voters without party labels",
        "two appointed by the state Soil and Water Conservation Commission",
    ),
)

if __name__ == "__main__":
    cb.main(SPEC, __doc__)
