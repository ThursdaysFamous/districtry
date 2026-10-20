#!/usr/bin/env python3
"""
Build sc/data/app/sc-conservation-boards.json: the commissioners of the
conservation district in each of South Carolina's 46 counties, read from the
Department of Natural Resources' page for each district, for the County card.

    python3 sc/scripts/build_sc_conservation_boards.py            # read, parse, write
    python3 sc/scripts/build_sc_conservation_boards.py --check    # offline
    python3 sc/scripts/build_sc_conservation_boards.py --watch    # has any name changed?

The work is scripts/conservation_boards.py, which says what is read, what is
carried and what the checks prove. This file says where South Carolina
publishes its boards and how to read the publication.

THE SOURCE. The Department of Natural Resources' Soil and Water Conservation
Districts page (INDEX below) links one page per county district, 46 in all,
each with a table headed "Commissioners and Staff": a row per person with the
name, position and "Expiration of Term", the term cell carrying the date and
"(E)" for elected or "(A)" for appointed. Read on 2026-10-16 every page lists
five commissioners: 225 named and five seats marked "Vacant" (Beaufort,
Dorchester, Florence and Richland, each an elected seat, and Union, an
appointed one). Rows with no term are staff, and one is McCormick's associate
commissioner, who is not a member of the board (S.C. Code section 48-9-1220
and 48-9-1210 make the board three elected and two appointed commissioners);
none of those is carried. The pages print no date.

HOW THE PAGES ARE READ. They are written by hand and differ in the parts a
reader keys on, measured on 2026-10-16: four put every row inside <thead>
(Berkeley, Cherokee, Dillon and Lee), Marion has neither <thead> nor <tbody>,
Aiken's column headings sit in <tbody>, Spartanburg's fourth commissioner row
has no opening <tr>, and Pickens has an empty one. So every row of the one
table is read wherever it sits, a cell with no open row opens one as a browser
would, and a row is a commissioner's exactly when its third cell is a date
followed by "(E)" or "(A)". Positions are printed as published except six
spellings, mapped in ROLES ("Comissioner", "Secratary/Treasurer" and four
more), and the dates come in five shapes, two-digit and four-digit years.

HOW THE BOARDS ARE CHOSEN, from the South Carolina Code, Title 48, Chapter 9,
read 2026-10-16: three commissioners are elected, without party labels, at
the general election by the county election commission, and take office the
following February first (section 48-9-1220), which is why every elected
term printed but one ends on 31 January; two are appointed by the board,
the governing body of the Department of Natural Resources (sections 48-9-30
and 48-9-1210); each term is four years, and a commissioner holds office
until a successor has been elected or appointed and has qualified, while a
vacancy in an elected seat may be filled by the board's appointment on the
unanimous recommendation of the remaining commissioners (section 48-9-1230).
The commissioners choose their own chair (section 48-9-1240).

TERMS THAT HAVE ENDED. On 2026-10-16, 34 printed terms had passed, 33 of them
appointed seats and one elected (Florence's, 02/11/23). Under section
48-9-1230 a commissioner whose term has ended holds office until a successor
qualifies, so the card shows such a member as serving with the date the term
ended, and never as a vacancy. Whether a page is simply out of date the law
cannot say. Three appointed rows carry an elected seat's 31 January 2027
(Florence's vice chairman, Marlboro's vice chairwoman and Oconee's
chairwoman), and Oconee's page marks two seats elected and three appointed;
section 48-9-1230's appointment to an elected seat's unexpired term is the
likely reason (inferred), and the card prints each mark as the page does.

TURNOVER. 90 of the 137 elected seats end on 31 January 2027, after the
election of 3 November 2026; WATCH.md carries the re-read in February 2027.

TERMS OF USE. Each page's footer reads "(c) 2020 All rights reserved", which
belongs to the site's template. The department's privacy statement cites the
South Carolina Family Privacy Protection Act (S.C. Code section 30-2-50),
which bars using personal information obtained from the department for
commercial solicitation; nothing here solicits anyone. Names are printed
exactly as the pages print them, and every card cites its county's page.

PRIVACY. Only the commissioners' rows are read, and from them only the name,
position and term. The pages also carry the district office's address,
telephone and e-mail address, staff names and, on some, e-mail addresses
named after a member of staff at a consumer mail provider; none of it is
copied.

RETRIES. The department's server reset six of 47 connections on 2026-10-16,
each right after the TLS handshake began, and every page answered on a second
try; the shared reader tries twice more, 10 and 30 seconds apart.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
sc-conservation-boards): the state publishes the boards as 46 hand-edited web
pages with no date, whose markup differs page to page; 34 printed terms had
passed with nothing saying whether the member still serves; an appointed
mark on an elected seat's term is not explained; no page or list says when a
vacancy was filled or by whom; and the county election commissions publish
the elected seats' results separately, county by county.
"""

import datetime
import html
import os
import re
import sys
import urllib.parse
from html.parser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import conservation_boards as cb  # noqa: E402

INDEX = "https://dnr.sc.gov/conservation/index.html"

LINK_RE = re.compile(r'<a\b[^>]*?href\s*=\s*"(districtsdnr/[a-z]+\.html)"[^>]*>(.*?)</a>',
                     re.I | re.S)
TERM_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4}) \(([EA])\)$")

# Spellings mapped to the word the other pages use, measured 2026-10-16.
ROLES = {
    "Comissioner": "Commissioner",
    "Secratary/Treasurer": "Secretary/Treasurer",
    "Secretary /Treasurer": "Secretary/Treasurer",
    "Chairwomen": "Chairwoman",
    "Chairwomen/Secretary/Treasurer": "Chairwoman and Secretary/Treasurer",
    "Vice-Chairman": "Vice Chairman",
}


def links(body, url):
    out, seen = [], set()
    for href, text in LINK_RE.findall(body):
        county = cb.clean(html.unescape(re.sub(r"<[^>]+>", " ", text)))
        full = urllib.parse.urljoin(url, html.unescape(href))
        if full not in seen:
            seen.add(full)
            out.append((full, county))
    return out


class Page(HTMLParser):
    """The district's heading (the first <h2> in #mainContent) and the rows of
    the one table there, each a list of (tag, text) cells."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.depth = 0
        self.heading = None
        self.in_h2 = False
        self.h2 = []
        self.tables = 0
        self.in_table = False
        self.rows = []
        self.row = None
        self.cell = None
        self.cell_tag = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.depth == 0:
            if tag == "div" and a.get("id") == "mainContent":
                self.depth = 1
            return
        if tag == "div":
            self.depth += 1
        elif tag == "h2" and self.heading is None:
            self.in_h2 = True
        elif tag == "table":
            self.tables += 1
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.end_row()
            self.row = []
        elif self.in_table and tag in ("td", "th"):
            if self.row is None:
                self.row = []
            self.cell = []
            self.cell_tag = tag
        elif self.in_table and tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def end_cell(self):
        if self.cell is not None:
            self.row.append((self.cell_tag, cb.clean("".join(self.cell))))
            self.cell = None

    def end_row(self):
        self.end_cell()
        if self.row:
            self.rows.append(self.row)
        self.row = None

    def handle_endtag(self, tag):
        if self.depth == 0:
            return
        if tag == "div":
            self.depth -= 1
        elif tag == "h2" and self.in_h2:
            self.in_h2 = False
            self.heading = cb.clean("".join(self.h2))
        elif self.in_table and tag in ("td", "th"):
            self.end_cell()
        elif self.in_table and tag == "tr":
            self.end_row()
        elif tag == "table" and self.in_table:
            self.end_row()
            self.in_table = False

    def handle_data(self, data):
        if self.in_h2:
            self.h2.append(data)
        elif self.cell is not None:
            self.cell.append(data)


def term_end(match):
    month, day, year = int(match.group(1)), int(match.group(2)), match.group(3)
    year = int(year) + (2000 if len(year) == 2 else 0)
    return datetime.date(year, month, day).isoformat()


def parse(url, body, county):
    page = Page()
    page.feed(body.decode("utf-8", "replace"))
    page.close()
    if page.tables != 1:
        raise RuntimeError("%s: %d tables where the page has one" % (url, page.tables))
    if not page.heading:
        raise RuntimeError("%s: no district heading" % url)
    members = []
    for row in page.rows:
        cells = [text for tag, text in row if tag == "td"]
        if len(cells) != 3:
            continue
        name, role, term = cells
        m = TERM_RE.match(term)
        if not m:
            continue
        member = {"vacant": True} if name.casefold() == "vacant" else {"name": name}
        if role:
            member["role"] = ROLES.get(role, role)
        member["chosen"] = "elected" if m.group(4) == "E" else "appointed"
        member["termEnds"] = term_end(m)
        members.append(member)
    return [{"county": county, "name": page.heading, "members": members}]


SPEC = cb.Spec(
    tag="sc",
    label="build_sc_conservation_boards",
    user_agent="districtry/1.0 (+https://districtry.com/sc/)",
    parse=parse,
    seats=lambda board: 5,
    member_keys=("role", "chosen", "termEnds"),
    index=INDEX,
    links=links,
    card_claims=(
        "three elected by the county's voters without party labels",
        "two appointed by the board of the state Department of Natural Resources",
        "serves until a successor takes office",
    ),
)

if __name__ == "__main__":
    cb.main(SPEC, __doc__)
