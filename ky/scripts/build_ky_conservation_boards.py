#!/usr/bin/env python3
"""
Build ky/data/app/ky-conservation-boards.json: the supervisors of the
conservation district (two in Logan County) in each of Kentucky's 120
counties, read from the Division of Conservation's sheet for each district,
for the County card.

    python3 ky/scripts/build_ky_conservation_boards.py            # read, parse, write
    python3 ky/scripts/build_ky_conservation_boards.py --check    # offline
    python3 ky/scripts/build_ky_conservation_boards.py --watch    # has any name changed?

The work is scripts/conservation_boards.py, which says what is read, what is
carried and what the checks prove. This file says where Kentucky publishes
its boards and how to read the publication.

THE SOURCE. The Energy and Environment Cabinet's Division of Conservation
publishes a one-page PDF for each of the state's 121 conservation districts,
120 files linked from its Conservation Districts page (INDEX below), Logan
County's one file holding both its North and South districts. The page says
each file gives "the district's address, phone number, employees, email
addresses, DOC assigned field staff, KACD area, and the seven elected
supervisors". Each sheet heads a column "Supervisors & Term Ending:" with
seven lines, a name and the year that member's term ends ("Julie Ann Day
(2026)"), beside a second column of staff. Each sheet is changed on its own:
the 120 read on 2026-10-16 were last changed between 24 February and 16
October 2026, and the card shows each sheet's own date, read from the file's
metadata. Read that day, every district lists seven seats, three ending in
2026 and four in 2028 as the statute below sets them, with 843 names and four
seats marked "Vacant" (Morgan, Scott, Todd and Trimble).

WHAT IT GIVES AND WHAT IT DOES NOT. Each supervisor's name and the year the
term ends; carried exactly as printed. No officers (the word chair appears on
no sheet), no start dates, nothing to say whether a seat was filled by
election or by the Commission's appointment, and no contact details for
supervisors.

HOW THE BOARDS ARE CHOSEN, from the Kentucky Revised Statutes, read
2026-10-16: a district's voters elect all seven supervisors for four-year
terms at the November general election, three in 2022 and 2026 and four in
2024 and 2028, and terms begin on 1 January; where no more nominating
petitions are filed than there are seats, the state Soil and Water
Conservation Commission declares the nominees elected without an election,
and it fills a vacancy for the rest of the term (KRS 262.240(1)). Two seats
are appointed only when a district is first organized (KRS 262.200(2)). A
supervisor may hold no other city, county or state elective office (KRS
262.200(2)). Of the 119 counties whose 2024 results the State Board of
Elections posts in a readable form, 34 put the race on the ballot; the others'
supervisors were declared elected, and no posted record names them except
these sheets.

WHAT IS KNOWN TO DISAGREE, measured on 2026-10-16 on a sample of 14 districts
against the Commission's minutes and the posted results: Fayette's sheet
(26 February) still lists a supervisor the July 2026 minutes replace;
Jefferson's lists "Alexis McFadden" where the Commission approved "Katrina
McFadden"; Daviess's 2028 class disagrees with the 2024 results and nothing
posted explains it; Boone's lists "Michael Wison" (inferred: Wilson). The
sheets are followed as printed, because they are the Division's own record of
who holds each seat.

TURNOVER. Three seats in each district turn over on 1 January 2027 after the
election of 3 November 2026; WATCH.md carries the re-read in January 2027.

TERMS OF USE. The Division's page footer reads "(c) 2022 Commonwealth of
Kentucky. All rights reserved."; the kentucky.gov disclaimer it links covers
only links and accuracy. The sheets carry no notice. Names are printed
exactly as the sheets print them, and every card cites its district's sheet.

PRIVACY. Only the supervisor column is read. The sheets also carry the
district office's address and telephone, staff names and e-mail addresses
and the Division's field representative; the index page carries each
district's e-mail address, 71 of 120 on free mail providers, some likely
personal. None of it is copied.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ky-conservation-boards): the state publishes its 121 boards, 847 seats, as
120 separately updated PDF sheets with no officers, no start dates and no record
of how each seat was filled; no posted record names the nominees the
Commission declares elected without an election, which was most counties'
whole class in 2024; the State Board's certified results carry no
conservation race, and 67 of the 2022 county reports it posts are scans with
no text; the Commission's minutes, which record vacancy appointments, are
posted months after each meeting; and four of 14 sampled sheets disagree with
the minutes or the results.
"""

import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import conservation_boards as cb  # noqa: E402

INDEX = "https://eec.ky.gov/Natural-Resources/Conservation/Pages/Conservation-Districts.aspx"

LINK_RE = re.compile(r'href\s*=\s*"([^"]*/Conservation(?: |%20)Districts/[^"]+\.pdf)"', re.I)
FILE_COUNTY_RE = re.compile(r"^(.+?) County\b")
HEADING_RE = re.compile(r"^\s*(\S.*?\bConservation District)\s*$")
SUPERVISOR_RE = re.compile(r"^\s*(\S.*?)\s*\((20\d\d)\)")


def links(body, url):
    out, seen = [], set()
    for href in LINK_RE.findall(body):
        full = cb.quote_url(urllib.parse.urljoin(url, html.unescape(href)))
        if full in seen:
            continue
        seen.add(full)
        name = urllib.parse.unquote(full.rsplit("/", 1)[1])
        m = FILE_COUNTY_RE.match(name)
        if not m:
            raise RuntimeError("a district sheet whose file name names no county: %s" % full)
        out.append((full, m.group(1)))
    return out


def parse(url, body, county):
    text = cb.pdf_text(body)
    dated = cb.pdf_date(body)
    boards = []
    cur = None
    for line in text.split("\n"):
        m = HEADING_RE.match(line)
        if m:
            cur = {"county": county, "name": cb.clean(m.group(1)), "members": []}
            if cb.county_key(county) not in cb.county_key(cur["name"]):
                raise RuntimeError("%s: the sheet linked as %s County's is headed %r"
                                   % (url, county, cur["name"]))
            if dated:
                cur["dated"] = dated
            boards.append(cur)
            continue
        m = SUPERVISOR_RE.match(line)
        if m and cur is not None:
            name = cb.clean(m.group(1))
            if "|" in name or "@" in name:
                raise RuntimeError("%s: a supervisor line runs into the staff column: %r"
                                   % (url, line.strip()))
            cur["members"].append({"vacant": True, "termEnds": m.group(2)}
                                  if name.casefold() == "vacant"
                                  else {"name": name, "termEnds": m.group(2)})
    if not boards:
        raise RuntimeError("%s: no district heading in the sheet" % url)
    return boards


SPEC = cb.Spec(
    tag="ky",
    label="build_ky_conservation_boards",
    user_agent="districtry/1.0 (+https://districtry.com/ky/)",
    parse=parse,
    seats=lambda board: 7,
    member_keys=("termEnds",),
    index=INDEX,
    links=links,
    multi={"Logan": 2},
    card_claims=(
        "elect all seven supervisors",
        "declares them elected without an election",
    ),
)

if __name__ == "__main__":
    cb.main(SPEC, __doc__)
