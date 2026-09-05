#!/usr/bin/env python3
"""
Scrape the office and board of Boone County's five park and library districts
out of the County Clerk's Year Book.

WHY THIS EXISTS. il/data/app/boone-{park,library}-districts.json ship the five
districts' BOUNDARIES, dissolved from the county's own parcel fabric
(scripts/build_parcel_fabric_districts.py). The cards name the district and
stop — no trustee, no office address, no telephone — which is the largest
card-order gap this county has, recorded as `boone-park-library-contact`. The
same Clerk who publishes the tax-code roster that drew those lines publishes
the people and the office on the same pages the district NAMES were taken
from, so nothing here needs a new publisher; it needs a parser.

THE JOIN KEY IS ALREADY EXACT. build_parcel_fabric_districts.py ships each
district under this booklet's own heading verbatim — BELVIDERE PARK DISTRICT,
ROCKFORD PARK DISTRICT, IDA PUBLIC LIBRARY, CHERRY VALLEY DISTRICT LIBRARY,
NORTH SUBURBAN DISTRICT LIBRARY — because the names came from here in the
first place. So the heading IS the key, and the builder refuses to write if
the two files ever stop naming the same five bodies.

SOURCE AND FETCH POSTURE are boone_municipal_officials_scraper.py's, imported
rather than copied: the edition is discovered from the index page's LINK TEXT
because this county's filenames lie (the 2024 edition is served as
"BCC-2022 Yearbook-2024 Final 08272024.pdf"), and that logic must have exactly
one implementation or the two scrapers will pin to different years without
anyone noticing.

-----------------------------------------------------------------------------
THE ONE THING THAT WILL BREAK A COPIED PARSER: THIS BOOKLET'S LEADER LINES
RUN IN BOTH DIRECTIONS, INSIDE A SINGLE BODY.

A "leader line" is a name and a fact joined by a run of dots. Measured on the
2026 edition, the five bodies use FOUR different orderings, two of them on
adjacent lines of the same block:

    Jen Jacky......................................Executive Director   NAME, then ROLE
    Daniel Noble, President ................................... 2029    NAME+ROLE, then YEAR
    President ...................................... Angie Williams     ROLE, then NAME
    Executive Director: Jay Sandine                                     ROLE: NAME, no leader

Belvidere Park District prints the first two; Ida Public Library prints the
third for all five of its officers; the three Winnebago-seated bodies print
the fourth. A parser that assumes the name comes first reads Ida's board as
five people called "President", "1st Vice President" and so on. A parser that
assumes it comes second reads Belvidere's director as a person called
"Executive Director" — and, worse, silently drops Jen Jacky.

SO THE SIDE IS DECIDED BY CONTENT: whichever side of the leader is a ROLE is
the role, and the other side is the name. A year on the tail means the head is
"Name, Role". If BOTH sides parse as a role, or NEITHER does, the line is
DROPPED with a warning naming it — never guessed at. Position is used for
nothing.

THE SECOND TRAP IS THE LEADER CHARACTER ITSELF. Most lines use ASCII full
stops; two of the five bodies use U+2026 HORIZONTAL ELLIPSIS instead, and one
line mixes them:

    Gary Thacker, Treasurer.......................................2027

A `\\.{3,}` split reads that as a single unsplittable token and loses the
county's own treasurer. Both characters are leaders here.

THIRD: A ROW CAN CARRY NO LEADER AT ALL. Ida's four remaining trustees are a
comma list that WRAPS ("Trustees: Corey Beard, Wendy Frank, Dr. Derek Prado,"
/ "Maegen English"), so a continuation line has to be joined onto its opener
before anything is split. And "Dr. Derek Prado" carries a title INSIDE the
name, which a leading-title stripper would eat.

-----------------------------------------------------------------------------
THE YEARBOOK OWNS THE OFFICE. IT DOES NOT OWN EVERY BOARD, AND THE GAP RECORD
THAT ASKED FOR THIS ASSUMED IT DID.

`boone-park-library-contact` says the trustees are "all of it already printed
in the Clerk's own yearbook". Measured against the bodies' own publications,
that holds for exactly one of the five, and the correction is the reason this
scraper reads more than one source:

  BELVIDERE PARK DISTRICT   the district publishes FIVE commissioners and its
                            own seat count in words — "our community-elected,
                            five member Board of Commissioners" — and the
                            booklet lists four of them. Its staff listing also
                            corroborates the director and the four staff
                            dropped below. This page was TWICE recorded as not
                            existing before the sitemap was read, and its fifth
                            commissioner was then LOST TO A PARSE BUG that
                            published a vacancy in her place; see OWN_BOARDS
                            and fetch_belvidere_park_board.
  IDA PUBLIC LIBRARY        the yearbook's board is SUPERSEDED. Its own board
                            page names a different one, and the page states the
                            mechanism: an "Annual Meeting of Board w/Officer
                            Elections" on 07/28/26, three weeks AFTER the
                            2026 edition's own 7.7.26 date. Angie Williams is
                            no longer president (Tillema moved up from 1st vice
                            president, Pierce from 2nd), two trustees have left,
                            two have joined, and one seat is OPEN.
  ROCKFORD PARK DISTRICT    the yearbook prints no board; the district
                            publishes five commissioners with telephone numbers
                            and term years, on its PLAIN /board page — an
                            earlier version fetched a `?format=json` URL the
                            site's robots.txt disallows, on a false claim that
                            the page was empty without it. See OWN_BOARDS.
  NORTH SUBURBAN            the yearbook prints no board; the library publishes
                            seven trustees and their terms as a linked PDF. The
                            card cites that DOCUMENT and its Last-Modified date
                            rather than the page that links it, and the scraper
                            warns if it predates the last April consolidated
                            election — a page shows its own drift week to week,
                            a PDF can sit unchanged through an election.
  CHERRY VALLEY             the yearbook prints no board; the library
                            publishes seven trustees with a term year and an
                            individual address each. THIS ONE WAS FIRST
                            RECORDED AS "NOBODY PUBLISHES IT", off a single
                            HTTP 502 — see the Cherry Valley note in
                            OWN_BOARDS for why that was not a measurement.

A SNAPSHOT IS COMPLETE BY CONSTRUCTION AND THAT IS THE EVIDENCE AGAINST IT.
The yearbook prints nine names for Ida and four for Belvidere Park because an
annual booklet prints the board it was handed; the library's own page prints
eight and the word "Open", and the park district's own page prints FIVE. The
booklet says nothing about either difference — not because it is careless but
because a list has no way to show a change. The absence of a vacancy is evidence
of a snapshot rather than of a full board, the same reasoning that keeps
Michigan's statewide commissioner columns out of `mi/data/app`. So the rule here
is the Coles rule: GEOMETRY FROM WHATEVER PROVES THE LINES, PEOPLE FROM WHATEVER
THE BODY MAINTAINS AS PEOPLE — and all five boards come from the bodies
themselves, with the yearbook keeping the office it does own.

AND A VACANCY IS NEVER ARITHMETIC. `vacancies` is counted from a body's own word
for an empty seat — Ida's list prints "Trustee: Open" — and from nothing else. A
roster that comes up SHORT of the seat count a body states is a parse miss or a
body that stopped listing someone, and it is reported as that and refused by the
builder's floor. This rule cost a shipped falsehood to learn: an earlier build
derived Belvidere Park's vacancies as seats minus rows parsed, and a markup
quirk that hid one commissioner became a card announcing "1 of 5 seats is
vacant" about a district whose own page names five.

WHERE BOTH NAME THE SAME PERSON the booklet's TERM-EXPIRY YEAR rides along,
because it is a fact about that person which the body's own page does not
print. A person only one source names never gains the other's fields.

Each board source is fetched and parsed independently and a failure costs that
one board. **The yearbook is never a fallback for a board it is known to be
stale about**: substituting it on a fetch failure would ship a wrong
officeholder precisely when nobody is looking. A body whose board cannot
be read ships with none, and the card carries a sentence written for that body
saying so — measured in the builder, never a hardcoded guess in the app. As of
this build no body is in that state.

ONE TYPO IS CORRECTED, WITH THE CORRECTION NAMED. The yearbook prints Ida's
director as `mindlyl@idapubliclibrary.org`; the library's own contact page
prints `mindyl@` — an `l` transposed into the yearbook. Unlike this county's
Belvidere telephone disagreement, where two publishers differ and nothing
settles which is right, the library owns its own mailbox, so the library's
spelling ships and the disagreement is printed every run. Ida's office contact
is its own published `Board@idapubliclibrary.org` rather than any personal
address.

-----------------------------------------------------------------------------
WHAT IS DELIBERATELY NOT COLLECTED.

STAFF BELOW THE DIRECTOR. Belvidere Park District's "Organization:" block
prints a Park Attorney and three Superintendents. They are employees of the
district, not its governing body, and the fleet's card convention asks for the
representative(s) and then the office — so the board and the head of the
agency ship and the department heads do not. This is a scope decision, not a
parsing limit: those four lines parse cleanly and are dropped on purpose, and
the count is printed every run so the decision stays visible.

A BOARD FOR THE THREE WINNEBAGO-SEATED BODIES, FROM THE YEARBOOK. Rockford
Park District, Cherry Valley District Library and North Suburban District
Library each print an office, a telephone, a website and a director there, and
no board. That is the COUNTY'S limit and not this parser's: Boone's yearbook
names Boone's officials, and those three boards are elected in Winnebago. All
three publish their own, which is where they are read from instead.

HOW A SEAT IS SELECTED. The booklet prints roles and term years and never says
whether a board is elected or appointed, and Illinois runs both kinds — a
district library's board is elected, a municipal library's is appointed. So
nothing here claims either. The role ships exactly as printed.

A ZIP CODE IDA DOES NOT PRINT. Ida Public Library's address line is
"320 N. State St. - Belvidere, Illinois", with no ZIP where the other four
carry one. It ships without one. The county's own line is the whole of what
is known and inventing 61008 from the town name would be a guess about a
postal boundary, however likely.
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from boone_municipal_officials_scraper import (  # noqa: E402
    HEADERS,
    INDEX_PAGE,
    REQUEST_TIMEOUT,
    clean,
    discover_yearbook_url,
    fetch_pdf,
    format_phone,
)

try:
    import pdfplumber
except ImportError:  # pragma: no cover - surfaced by main()
    pdfplumber = None


# The five bodies, keyed by the yearbook heading the geometry files also use.
#
#   kind            which data/app geometry file this entry joins onto.
#   board_expected  whether the YEARBOOK carries a governing body for it, so a
#                   body that stops publishing one is a warning rather than a
#                   silent empty list. It is False for the three Winnebago-
#                   seated bodies because Boone's booklet names Boone's
#                   officials — a limit of the county, not of this parser.
#   board_source    which publication the shipped BOARD is taken from:
#                     "yearbook" — the county's booklet is the only source
#                     "own"      — the body maintains its own, read below
#                     None       — nobody this client can read names one
#   own_seats       the seat count the body's own page STATES in words. Used
#                   only to check the parse, never to invent an empty seat: a
#                   count that disagrees is a warning, not a padded list.
BODIES = {
    "BELVIDERE PARK DISTRICT": {
        "kind": "park", "board_expected": True, "board_source": "own",
        "own_seats": 5,
    },
    "ROCKFORD PARK DISTRICT": {
        "kind": "park", "board_expected": False, "board_source": "own",
        "own_seats": 5,
    },
    "IDA PUBLIC LIBRARY": {
        "kind": "library", "board_expected": True, "board_source": "own",
        "own_seats": 9,
    },
    "CHERRY VALLEY DISTRICT LIBRARY": {
        "kind": "library", "board_expected": False, "board_source": "own",
        "own_seats": None,
    },
    "NORTH SUBURBAN DISTRICT LIBRARY": {
        "kind": "library", "board_expected": False, "board_source": "own",
        "own_seats": None,
    },
}

# Where a body's own board lives. `note` is what the card tells a reader when
# the board cannot be read at all.
OWN_BOARDS = {
    "BELVIDERE PARK DISTRICT": {
        # THIS PAGE WAS TWICE RECORDED AS NOT EXISTING, and both times the
        # method was at fault rather than the district. The first pass filtered
        # the front page's hrefs for board|trustee|commission and found only an
        # election notice; the second read the nav's visible labels and found
        # "Park District Board and Meetings" but no matching href, because this
        # site's menu is rendered from a script the text extraction flattens.
        # The SITEMAP has it at /about-us/board/ — three requests and no
        # guessing. ENUMERATE, DO NOT FILTER: a link this project cannot see is
        # not a page that is not there.
        #
        # It matters because the page states the seat count in words — "our
        # community-elected, five member Board of Commissioners" — and NAMES
        # ALL FIVE, where the county's yearbook names four: the yearbook is an
        # annual snapshot and the district's own page is current. (An earlier
        # version of this comment said the page listed four and cited a "Legal
        # Notice — Board Vacancy"; both were wrong. The four/five gap was a
        # PARSE MISS in this scraper — one member's address is split across a
        # <span>, which the old visible-text reader dropped — and it published
        # a vacancy that does not exist. Vacancies are never arithmetic here;
        # only a body's own word for one counts.)
        "url": "https://www.belviderepark.org/about-us/board/",
        "label": "Belvidere Township Park District Board of Commissioners",
        "seats_phrase": r"([a-z]+)[ -]member Board of Commissioners",
    },
    "IDA PUBLIC LIBRARY": {
        "url": "https://idapubliclibrary.org/library-board/",
        "label": "Ida Public Library Board of Trustees",
    },
    "ROCKFORD PARK DISTRICT": {
        # THE PLAIN PAGE, AND AN EARLIER VERSION FETCHED A URL THE SITE
        # DISALLOWS. It read `/board?format=json`, justified in a comment
        # claiming the served HTML "carries only navigation, and the board is
        # rendered client-side". Both halves were wrong. rockfordparkdistrict
        # .org/robots.txt carries `Disallow:/*?format=json` under
        # `User-agent: *` — robots.txt is an honesty rule in this repo, not a
        # technical obstacle, and no user agent is ever renamed to get past
        # one. And a plain GET of /board returns ~300 KB whose text carries
        # "Meet Our Board Martesha Brown President Phone: … Term Expires: 2027"
        # and every other commissioner; the same parse over it yields all five.
        # The false claim came from reading ONE stripped rendering of the page
        # and generalising, without checking the raw HTML — the same mistake
        # this scraper's other three traps are all versions of.
        "url": "https://www.rockfordparkdistrict.org/board",
        "label": "Rockford Park District Board of Commissioners",
    },
    "CHERRY VALLEY DISTRICT LIBRARY": {
        # A plain "Board Members / Email / Term Ends" table, one row per
        # trustee, with an individual address at the library's own domain.
        #
        # THIS RECORD NEARLY SHIPPED AS "NO BOARD READABLE" ON THE STRENGTH OF
        # ONE HTTP 502. The first sweep of the five bodies hit cherryvalleylib
        # .org while it was returning 502, took that as the measurement, and
        # wrote a card note telling readers this district's board is not named
        # here — for a library that publishes it, with e-mail addresses and term
        # years. A 502 is a load balancer having a bad second; it is not the
        # persistent misconfiguration this project documents for Coles and
        # Gallatin, and it is not evidence about what a site publishes. RETRY
        # BEFORE RECORDING AN ABSENCE, and the fetcher below does.
        "url": "https://cherryvalleylib.org/governance/",
        "label": "Cherry Valley Public Library District Board of Trustees",
    },
    "NORTH SUBURBAN DISTRICT LIBRARY": {
        # A PDF the library's own administration page links as "Current Board
        # of Trustees and Terms". Discovered from that page by LINK TEXT, not
        # by filename — the file lives under /wp-content/uploads/2022/03/ and
        # is re-uploaded in place, so its path says 2022 while its content is
        # current (Last-Modified June 2025, terms running to 2029). Reading
        # the year out of that path is exactly the Boone-yearbook filename
        # trap in a second costume.
        "url": "https://www.northsuburbanlibrary.org/about-us/administration/",
        "link_text": r"Current Board of Trustees",
        "label": "North Suburban Library District Board of Trustees",
    },
}

# The library's own pages carry two contacts the yearbook gets wrong or does
# not have: its administration page pairs each director with an address, and its
# board page publishes a BOARD mailbox that belongs to nobody in particular.
# Both are READ rather than remembered — an earlier draft hardcoded the
# corrected director address as a constant, which is a fact this repo would go
# on asserting long after the library changed it.
IDA_CONTACT_PAGE = "https://idapubliclibrary.org/contact/"
IDA_BOARD_EMAIL_RE = re.compile(r"\bBoard@idapubliclibrary\.org\b", re.I)
# The yearbook prints the director's address with a transposed letter. The pair
# is kept only to RECOGNISE it, so the disagreement is reported rather than
# silently overwritten; the shipped value comes from the library either way.
IDA_YEARBOOK_TYPO = "mindlyl@idapubliclibrary.org"

# A heading is the booklet's own all-caps body name. Used only to END a block:
# the five openers are matched literally, so a wrapped heading (the Housing
# Authority's runs over two lines) costs nothing.
HEADING_RE = re.compile(r"^[A-Z][A-Z&'.–— .-]{6,}$")

# Both leader characters, in any mixture. See the docstring.
LEADER_RE = re.compile(r"[.…]{3,}")

# A term year on the tail of a leader line. The booklet occasionally leaves a
# stray leader dot glued to the year ("......... .2029"), so one is tolerated.
YEAR_RE = re.compile(r"^\.?\s*((?:19|20)\d{2})\.?$")

# Governing-body and agency-head roles this parser will ship, longest first so
# "1st Vice President" wins over "Vice President" and "President".
BOARD_ROLES = [
    "1st Vice President", "2nd Vice President", "3rd Vice President",
    "Vice President", "Vice-President", "Vice Chairman", "Vice Chair",
    "President", "Chairman", "Chairperson", "Chair",
    "Secretary-Treasurer", "Secretary", "Treasurer",
    "Commissioner", "Trustee", "Member",
]
HEAD_ROLES = [
    "Executive Director", "Assistant Director", "Interim Director", "Director",
]

# Parsed cleanly and dropped on purpose — see "WHAT IS DELIBERATELY NOT
# COLLECTED". A role matching one of these is counted and reported, never
# shipped.
STAFF_ROLE_RE = re.compile(
    r"^(?:Park Attorney|Attorney|Superintendent\b.*|Manager\b.*|"
    r"Head of\b.*|Coordinator\b.*)$", re.I)

ADDRESS_RE = re.compile(r"^(.+?)\s*[•·]\s*(.+)$")
PHONE_LINE_RE = re.compile(r"\b(?:Phone|Fax)\b", re.I)
PHONE_RE = re.compile(r"\(?(\d{3})\)?[ .-]*(\d{3})[ .-]*(\d{4})")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WEBSITE_RE = re.compile(r"\b((?:www\.|https?://)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
                        r"(?:/[^\s]*)?)")
TRUSTEE_LIST_RE = re.compile(r"^(Trustees?|Board Members?|Members?)\s*:\s*(.*)$", re.I)
# "Commissioners:" / "Organization:" open a sub-block rather than naming
# anyone. The second switches the parser into the staff section.
SUBHEAD_RE = re.compile(r"^(Commissioners?|Board|Officers?|Organization|Staff)\s*:?$", re.I)
STAFF_SUBHEAD_RE = re.compile(r"^(Organization|Staff)\s*:?$", re.I)
# A footer page number, and the "<Body> - cont." continuation header.
PAGE_NUM_RE = re.compile(r"^\d{1,3}$")
CONT_RE = re.compile(r"–\s*cont\.?$|-\s*cont\.?$", re.I)


def match_role(text):
    """-> the canonical role this text IS, or None if it is not purely a role.

    Purely: the whole string, allowing a trailing colon. "President" is a role;
    "Daniel Noble, President" is not (it is a name carrying one) and neither is
    "Park Attorney for the District".
    """
    if not text:
        return None
    bare = text.strip().rstrip(":").strip()
    for role in HEAD_ROLES + BOARD_ROLES:
        if bare.lower() == role.lower():
            return role
    if STAFF_ROLE_RE.match(bare):
        return bare
    return None


def split_name_role(text):
    """'Daniel Noble, President' -> ('Daniel Noble', 'President').

    Separators seen in this booklet: a comma, an en dash, and a bare space
    ("Ed Branom Vice President"). The bare-space case is only taken when the
    TAIL is a known role, so an ordinary surname is never eaten.
    """
    text = clean(text) or ""
    for sep in (",", "–", "-"):
        if sep in text:
            head, _, tail = text.partition(sep)
            role = match_role(tail)
            if role and clean(head):
                return clean(head), role
    for role in HEAD_ROLES + BOARD_ROLES:
        suffix = " " + role
        if text.lower().endswith(suffix.lower()) and clean(text[: -len(suffix)]):
            return clean(text[: -len(suffix)]), role
    return text or None, None


def looks_like_name(text):
    """A conservative person-name test, used only to REFUSE a bad parse."""
    if not text:
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 60:
        return False
    if EMAIL_RE.search(t) or WEBSITE_RE.search(t) or PHONE_RE.search(t):
        return False
    if re.search(r"\d", t):
        return False
    # A BACKSTOP FOR THE GREEDY-MATCH CLASS, which this parser has now hit on
    # two different pages: a pattern that runs past its subject produces a
    # plausible-looking string like "Meet Our Board Martesha Brown President".
    # Real names in these five bodies run one to four words (the longest is
    # "Deborah Dunnavan-Moreau"), and none ends in an office.
    if len(t.split()) > 4:
        return False
    # A bare office is never a person. This caught the third greedy-match bug
    # on this job — a non-greedy pattern that returned "President" as the name
    # of all seven Cherry Valley trustees, which every count guard passed.
    if match_role(t):
        return False
    # A full stop mid-name closes a sentence unless it belongs to an honorific
    # or an initial — the backstop for a bio bleeding into the next row.
    words = t.split()
    for word in words[:-1]:
        if word.endswith(".") and len(word.rstrip(".")) > 2 \
                and word.rstrip(".").lower() not in HONORIFICS:
            return False
    if match_role(t.split(" ", 1)[-1]) and len(t.split()) > 1:
        return False
    return bool(re.match(r"^[A-Za-z][A-Za-z.'’– -]*[A-Za-z.]$", t))


def page_lines(pdf_bytes):
    """-> [(page_number, line_text)] for the whole booklet, in reading order.

    Plain text extraction is enough here and coordinates are deliberately NOT
    used: unlike the ward block boone_municipal_officials_scraper.py reads,
    these blocks are a single column, so there is no second column whose x a
    threshold could get wrong between editions.
    """
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required (pip install -c "
                           "scripts/requirements.txt pdfplumber)")
    import io
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            for line in (page.extract_text() or "").splitlines():
                text = clean(line)
                if text:
                    out.append((number, text))
    return out


def collect_blocks(lines, warnings):
    """-> {heading: [line, ...]} for the five bodies, each up to its terminator.

    A block ends at the next all-caps heading. Page furniture in between — the
    footer page number and the "<Body> - cont." continuation header — is
    dropped rather than treated as content, so a body that spans a page break
    (Belvidere Park does) keeps its tail.
    """
    blocks = {}
    current = None
    for _, text in lines:
        if text in BODIES:
            current = text
            blocks.setdefault(current, [])
            continue
        if current is None:
            continue
        if PAGE_NUM_RE.match(text):
            continue
        if CONT_RE.search(text):
            continue
        if HEADING_RE.match(text):
            current = None
            continue
        blocks[current].append(text)
    missing = [h for h in BODIES if h not in blocks]
    if missing:
        warnings.append("the yearbook no longer carries a heading for: %s — "
                        "the booklet was reorganised, or a district was renamed"
                        % ", ".join(sorted(missing)))
    return blocks


def parse_block(heading, block_lines, warnings, staff_dropped):
    """-> one body's office + people, parsed by content."""
    spec = BODIES[heading]
    office = {"address": None, "city": None, "phone": None, "fax": None,
              "email": None, "website": None}
    people = []
    pending_email_for = None
    in_staff = False

    # Join a wrapped trustee list onto its opener before anything is split.
    joined = []
    for text in block_lines:
        if joined and joined[-1].rstrip().endswith(",") and TRUSTEE_LIST_RE.match(joined[-1]):
            joined[-1] = joined[-1].rstrip() + " " + text
            continue
        joined.append(text)

    for text in joined:
        if STAFF_SUBHEAD_RE.match(text):
            in_staff = True
            continue
        if SUBHEAD_RE.match(text):
            continue

        # --- the office block -------------------------------------------
        addr = ADDRESS_RE.match(text)
        if addr and office["address"] is None and not PHONE_LINE_RE.search(text) \
                and "@" not in text and not WEBSITE_RE.search(text):
            office["address"] = clean(addr.group(1))
            office["city"] = clean(addr.group(2))
            continue
        if PHONE_LINE_RE.search(text):
            for label, key in (("Phone", "phone"), ("Fax", "fax")):
                m = re.search(label + r"\s*:?\s*" + PHONE_RE.pattern, text, re.I)
                if m and office[key] is None:
                    office[key] = format_phone(m)
            continue
        site = WEBSITE_RE.search(text)
        mail = EMAIL_RE.search(text)
        if site or (mail and re.match(r"^(?:E-?mail)\s*:", text, re.I)):
            if site and office["website"] is None:
                office["website"] = site.group(1)
            if mail and office["email"] is None:
                office["email"] = mail.group(0)
            # A website/e-mail line carries nothing else in this booklet.
            continue

        # --- a bare e-mail under the person it belongs to ----------------
        if mail and clean(text) == mail.group(0):
            if pending_email_for is not None:
                people[pending_email_for]["email"] = mail.group(0)
                pending_email_for = None
            elif office["email"] is None:
                office["email"] = mail.group(0)
            continue

        # --- a wrapped or inline trustee list ----------------------------
        listed = TRUSTEE_LIST_RE.match(text)
        if listed:
            label = listed.group(1).rstrip("s").title()
            for name in [clean(p) for p in listed.group(2).split(",")]:
                if not name:
                    continue
                if not looks_like_name(name):
                    warnings.append("%s: dropped %r from the %s list — it does "
                                    "not read as a person's name"
                                    % (heading, name, listed.group(1)))
                    continue
                people.append({"name": name, "role": label, "term": None,
                               "email": None, "staff": in_staff})
            pending_email_for = None
            continue

        # --- a leader line, in whichever direction it runs ---------------
        parts = [clean(p) for p in LEADER_RE.split(text)]
        parts = [p for p in parts if p]
        if len(parts) == 2:
            head, tail = parts
            year = YEAR_RE.match(tail)
            if year:
                name, role = split_name_role(head)
                term = year.group(1)
            else:
                head_role, tail_role = match_role(head), match_role(tail)
                if head_role and not tail_role:
                    name, role, term = tail, head_role, None
                elif tail_role and not head_role:
                    name, role, term = head, tail_role, None
                else:
                    warnings.append(
                        "%s: could not tell name from role in %r — %s"
                        % (heading, text,
                           "both sides read as a role" if head_role
                           else "neither side does"))
                    continue
            if not looks_like_name(name):
                warnings.append("%s: dropped %r — %r does not read as a "
                                "person's name" % (heading, text, name))
                continue
            if in_staff or (role and STAFF_ROLE_RE.match(role)):
                staff_dropped.append("%s: %s (%s)" % (heading, name, role))
                pending_email_for = None
                continue
            people.append({"name": name, "role": role, "term": term,
                           "email": None, "staff": False})
            pending_email_for = len(people) - 1
            continue

        # --- "Role: Name", the no-leader form ----------------------------
        if ":" in text:
            head, _, tail = text.partition(":")
            role = match_role(head)
            name = clean(tail)
            if role and looks_like_name(name):
                if in_staff or STAFF_ROLE_RE.match(role):
                    staff_dropped.append("%s: %s (%s)" % (heading, name, role))
                    pending_email_for = None
                    continue
                people.append({"name": name, "role": role, "term": None,
                               "email": None, "staff": False})
                pending_email_for = len(people) - 1
                continue

        pending_email_for = None

    board = [p for p in people if p["role"] not in HEAD_ROLES]
    heads = [p for p in people if p["role"] in HEAD_ROLES]
    if spec["board_expected"] and not board:
        warnings.append("%s: the yearbook published a board for this body and "
                        "now publishes none — the block was reorganised, or the "
                        "parser stopped reading it" % heading)
    if not spec["board_expected"] and board:
        warnings.append("%s: the yearbook now publishes a board for a body it "
                        "did not before — check whether the seat is Boone's to "
                        "report before shipping it" % heading)
    return {
        "district": heading,
        "kind": spec["kind"],
        "office": office,
        "heads": heads,
        "board": board,
        "board_published": bool(board),
    }


# ---------------------------------------------------------------------------
# Each body's own board, where it maintains one

def _get(url, warnings, what, retries=2):
    """Fetch, retrying a 5xx before believing it.

    A single 502 is what nearly wrote "this district publishes no board" into a
    card about a library that publishes one — see the Cherry Valley note in
    OWN_BOARDS. A gateway error is transient by definition and is retried; a 404
    or a refusal is the site's answer and is taken at once.
    """
    import requests
    import time
    last = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                                allow_redirects=True)
            if resp.status_code >= 500 and attempt < retries:
                last = "HTTP %d" % resp.status_code
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < retries and _is_transient(exc):
                time.sleep(2 * (attempt + 1))
                continue
            break
    warnings.append("%s: could not read %s after %d attempt(s) (%s) — that "
                    "board ships with no members rather than falling back to a "
                    "source known to be out of date"
                    % (what, url, retries + 1, last))
    return None


def _is_transient(exc):
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        return status >= 500
    return True  # a connection/timeout error, not the site's answer


def _visible_text(markup):
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", markup)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return clean(html_mod.unescape(text)) or ""


WORD_NUMBERS = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


# An honorific keeps its full stop inside a name ("Dr. Derek Prado", "Michael
# P. Dunn"); any longer word ending in one closes a sentence.
HONORIFICS = {"dr", "mr", "mrs", "ms", "st", "jr", "sr", "rev", "hon", "prof"}


def last_sentence(text):
    """-> the tail of `text` after its final sentence-ending full stop."""
    cut = 0
    for match in re.finditer(r"(\S+)\.\s", text):
        word = match.group(1).strip("(\"'").lower()
        if len(word) <= 2 or word in HONORIFICS:
            continue
        cut = match.end()
    return text[cut:]


def fetch_belvidere_park_board(warnings):
    """-> ([member], vacancies, seats) from the district's own board page.

    READ FROM THE MARKUP, NOT FROM THE VISIBLE TEXT — and this cost a shipped
    falsehood before it was fixed. The first version anchored each row on an
    `@belviderepark.org` address found in `_visible_text()`, which replaces
    tags with spaces. Carrie Lenzen's address is marked up as
    `<span ...>clenzen</span>@belviderepark.org` (Outlook paste residue), so
    the visible text reads "clenzen @belviderepark.org", the anchor never
    fired, and she was dropped. THE MISS THEN BECAME A CLAIM: seats came from
    the page's own "five member Board of Commissioners" sentence and vacancies
    were computed as seats minus rows parsed, so a parser bug published "1 of 5
    seats is vacant" about a district whose own page names five commissioners.
    Each member is now taken from their own block — `<h3>Name</h3>` then
    `<p><em>Role</em>…<a href="mailto:…">`, in the RAW HTML — so markup inside
    a name or an address cannot hide a seat.

    A VACANCY IS NEVER ARITHMETIC. It ships only where the body states one in
    words, the way Ida's list prints "Trustee: Open". A roster SHORT of the
    seat count the body states is a parse failure or a body that has stopped
    listing someone, and either way it is reported and refused — see the
    caller, which will not let a short board through.
    """
    conf = OWN_BOARDS["BELVIDERE PARK DISTRICT"]
    resp = _get(conf["url"], warnings, "BELVIDERE PARK DISTRICT")
    if resp is None:
        return [], 0, None
    markup = resp.text
    seats = None
    phrase = re.search(conf["seats_phrase"], _visible_text(markup), re.I)
    if phrase:
        seats = WORD_NUMBERS.get(phrase.group(1).lower())
    if seats is None:
        warnings.append("BELVIDERE PARK DISTRICT: %s no longer states its seat "
                        "count in words — the roster still ships, but nothing "
                        "can check it for completeness" % conf["url"])

    block = markup[markup.find("Board of Commissioners"):]
    # ONE REGEX CANNOT READ THIS PAGE: five members are marked up four ways.
    # Noble and Thacker put the link after `</em>`; Marquardt puts it INSIDE
    # the `<em>`; Lenzen wraps both her name and her address's local part in
    # `<span>`s (Outlook paste residue); Nord's link and its label disagree.
    # A single pattern over the whole shape drops whichever variants it did
    # not anticipate — the first version lost Lenzen, the second lost
    # Marquardt — so each member's chunk is cut out on `<h3>` boundaries and
    # read on its own, where the only structural assumptions are "the heading
    # is the name" and "the first mailto is the address".
    chunks = re.split(r"(?i)(?=<h3[\s>])", block)
    members = []
    for chunk in chunks[1:]:
        head = re.search(r"(?is)<h3[^>]*>(.*?)</h3>", chunk)
        if not head:
            continue
        name = clean(html_mod.unescape(re.sub(r"(?s)<[^>]+>", "", head.group(1))))
        if not name or not looks_like_name(name):
            continue
        # The role is the run before the first line break or link inside the
        # emphasis that follows the heading.
        em = re.search(r"(?is)<em[^>]*>(.*?)</em>", chunk)
        raw_role = em.group(1) if em else ""
        raw_role = re.split(r"(?i)<br\s*/?>|<a[\s>]", raw_role)[0]
        role = clean(html_mod.unescape(re.sub(r"(?s)<[^>]+>", "", raw_role)))
        if not role or "commissioner" not in role.lower():
            continue
        # "Commissioner / President" -> the office; a bare "Commissioner" stays.
        office = role.split("/", 1)[1].strip() if "/" in role else role
        member = {"name": name, "role": office or "Commissioner",
                  "term": None, "email": None}
        link = re.search(r'(?is)<a\s+href="mailto:([^"]+)"[^>]*>(.*?)</a>', chunk)
        href = clean(link.group(1)) if link else None
        shown = clean(html_mod.unescape(
            re.sub(r"(?s)<[^>]+>", "", link.group(2)))) if link else None
        # THE LINK AND ITS LABEL CAN DISAGREE, and on this page one does: the
        # Vice-President's row is
        # `<a href="mailto:amygrafton@…">amynord@…</a>`. One publisher, one
        # element, two addresses, and nothing on the site settles which is
        # current — so NEITHER ships, the same call this county's record
        # already made about a telephone digit two publishers disagreed on. A
        # bouncing address on a card is a broken promise; her name, office and
        # the district's own contact address still ship.
        if href and shown and href.lower() != shown.lower():
            warnings.append(
                "BELVIDERE PARK DISTRICT: %s's row links %s and displays %s — "
                "one page, two addresses, nothing settles which is current, so "
                "neither ships" % (name, href, shown))
        elif href:
            member["email"] = href
        members.append(member)
    if not members:
        warnings.append("BELVIDERE PARK DISTRICT: no commissioner blocks parsed "
                        "from %s — the page's markup changed" % conf["url"])
    # No vacancy is ever derived here; see the docstring.
    return members, 0, seats


def fetch_ida_board(warnings):
    """-> ([member], vacancies, seats) from the library's own board page.

    The page prints one flat run — "President: Jenny Tillema Vice President:
    Steve Pierce ... Trustee: Open" — so members are read as ROLE: NAME pairs
    between the "Library Board Members" heading and the address the run ends
    at. "Open" is the library saying a seat is VACANT, which is the one thing
    the county's annual snapshot can never say, and it is counted rather than
    dropped: a nine-seat board shipping eight names has to say why.
    """
    conf = OWN_BOARDS["IDA PUBLIC LIBRARY"]
    resp = _get(conf["url"], warnings, "IDA PUBLIC LIBRARY")
    if resp is None:
        return [], 0, None
    text = _visible_text(resp.text)
    start = text.find("Library Board Members")
    if start < 0:
        warnings.append("IDA PUBLIC LIBRARY: no 'Library Board Members' heading "
                        "on %s — the page was rebuilt" % conf["url"])
        return [], 0, None
    end = text.find("Board Meetings", start)
    block = text[start:end if end > start else start + 900]
    # The roles are the delimiters and the names are what lies BETWEEN them.
    # Matching "role: name" in one pass does not work here, because the run has
    # no punctuation between one member and the next role: a name pattern
    # greedy enough for "Jon Mark Bolthouse" also swallows "Jenny Tillema Vice
    # President", which reads as five seats on a nine-seat board. The seat
    # count the page states in words is what caught that, and it stays a guard.
    labels = list(re.finditer(
        r"((?:Library Board\s+)?(?:1st|2nd|3rd)?\s*(?:Vice\s+)?"
        r"(?:President|Secretary|Treasurer|Trustee))\s*:\s*", block))
    members, vacancies = [], 0
    for index, label in enumerate(labels):
        role = clean(re.sub(r"^Library Board\s+", "", label.group(1))) or "Trustee"
        stop = labels[index + 1].start() if index + 1 < len(labels) else len(block)
        segment = clean(block[label.end():stop]) or ""
        # "Trustee: Open" is the library saying the seat is VACANT — the one
        # thing an annual snapshot can never say. It runs straight into the
        # page's next sentence ("Open Comments, questions, and feedback..."),
        # so it is tested on the FIRST word rather than on the segment.
        if re.match(r"(?i)^open\b", segment):
            vacancies += 1
            continue
        name_match = re.match(r"([A-Z][A-Za-z.'’-]*(?:\s+[A-Z][A-Za-z.'’-]*){0,3})",
                              segment)
        name = clean(name_match.group(1)) if name_match else None
        if not name or not looks_like_name(name):
            warnings.append("IDA PUBLIC LIBRARY: dropped %r under %r — it does "
                            "not read as a person's name" % (segment[:40], role))
            continue
        members.append({"name": name, "role": role, "term": None, "email": None})
    return members, vacancies, len(members) + vacancies


def fetch_rockford_board(warnings):
    """-> [member] from the district's own board page.

    Each commissioner prints as "Name Role Phone: NNN-NNN-NNNN E-Mail > Term
    Expires: YYYY", and a member with no office (Rockford seats five and gives
    four of them a title) prints with the role simply absent. So the parser
    anchors on "Phone:" and "Term Expires:", which every member has, and treats
    the role as optional — anchoring on the role would silently drop the two
    commissioners who hold none.
    """
    conf = OWN_BOARDS["ROCKFORD PARK DISTRICT"]
    resp = _get(conf["url"], warnings, "ROCKFORD PARK DISTRICT")
    if resp is None:
        return []
    text = _visible_text(resp.text)
    text = re.sub(r"#block-[^{]*\{[^}]*\}", " ", text)
    text = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^}]*\})*\}", " ", text)
    start = text.find("Meet Our Board")
    if start < 0:
        warnings.append("ROCKFORD PARK DISTRICT: no 'Meet Our Board' block on "
                        "%s — the page was rebuilt" % conf["url"])
        return []
    block = text[start + len("Meet Our Board"):start + 1400]
    # As on Ida's page, the CONTACT BLOCK is the delimiter and the name is what
    # lies before it — a single greedy pattern reads "Meet Our Board Martesha
    # Brown President" as one person's name, because nothing punctuates the run.
    contacts = list(re.finditer(
        r"Phone:\s*(\d{3}-\d{3}-\d{4})\s*(?:E-?Mail\s*>?\s*)?"
        r"Term Expires:\s*((?:19|20)\d{2})", block))
    members, cursor = [], 0
    for contact in contacts:
        segment = clean(block[cursor:contact.start()]) or ""
        cursor = contact.end()
        name, role = split_name_role(segment)
        if not name or not looks_like_name(name):
            warnings.append("ROCKFORD PARK DISTRICT: dropped %r — it does not "
                            "read as a person's name" % segment[:50])
            continue
        members.append({"name": name, "role": role or "Commissioner",
                        "term": contact.group(2), "email": None,
                        "phone": contact.group(1)})
    return members


def block_head(text, start, header):
    """-> the table body after `header`, so the first row's name is not glued
    to the column titles ("...Term Ends Michelle Forster")."""
    at = text.find(header, start)
    if at < 0:
        return None
    return text[at + len(header):at + len(header) + 1200]


def fetch_cherry_valley_board(warnings):
    """-> [member] from the library's own governance page.

    The table flattens to "Name, Role address year" per trustee, so the ADDRESS
    is the delimiter — it sits between the role and the term and every row has
    one. Reading name/role/term without it would have to guess where one row
    ends and the next begins, which is the greedy-match failure this parser hit
    twice on other pages.
    """
    conf = OWN_BOARDS["CHERRY VALLEY DISTRICT LIBRARY"]
    resp = _get(conf["url"], warnings, "CHERRY VALLEY DISTRICT LIBRARY",
                retries=3)
    if resp is None:
        return []
    text = _visible_text(resp.text)
    start = text.find("Board Members")
    if start < 0:
        warnings.append("CHERRY VALLEY DISTRICT LIBRARY: no 'Board Members' "
                        "table on %s — the page was rebuilt" % conf["url"])
        return []
    block = block_head(text, start, "Board Members Email Term Ends")
    if block is None:
        block = text[start:start + 1200]
    # The ADDRESS + TERM pair is the delimiter and "Name, Role" is what lies
    # before it — for the third time on this job, a name pattern written to
    # match directly returns the wrong span. A non-greedy one took only the
    # last token ("President" as a person's name for all seven trustees) and a
    # greedy one would run back through the previous row.
    contacts = list(re.finditer(
        r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\s+((?:19|20)\d{2})",
        block))
    members, cursor = [], 0
    for contact in contacts:
        segment = clean(block[cursor:contact.start()]) or ""
        cursor = contact.end()
        name, role = split_name_role(segment)
        if not name or not looks_like_name(name):
            warnings.append("CHERRY VALLEY DISTRICT LIBRARY: dropped %r — it "
                            "does not read as a person's name" % segment[:50])
            continue
        members.append({"name": name, "role": role or "Trustee",
                        "term": contact.group(2), "email": contact.group(1)})
    return members


def _http_date(value):
    """-> an aware datetime for an HTTP Last-Modified header, or None."""
    if not value:
        return None
    try:
        from email.utils import parsedate_to_datetime
        stamp = parsedate_to_datetime(value)
    except Exception:  # noqa: BLE001 - a malformed header is simply unusable
        return None
    if stamp is None:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _last_consolidated_election(today):
    """-> the date of the most recent Illinois consolidated election.

    10 ILCS 5/2A-1.1(b): the FIRST TUESDAY IN APRIL of odd-numbered years.
    Library-district and park-district boards are elected there, so it is the
    line a roster document has to be newer than.

    THIS WAS WRITTEN AS "the first Tuesday AFTER THE FIRST MONDAY in April" —
    the general-election rule, not this one — and the two agree in every
    odd year EXCEPT when April 1 is itself a Tuesday. That is 2025, whose
    consolidated election was April 1 and which this helper placed on April 8:
    a week-wide hole, in exactly the cycle the shipped documents sit in.
    """
    import datetime as _dt

    def april_election(year):
        first = _dt.date(year, 4, 1)
        # weekday(): Monday 0 … Tuesday 1
        return first + _dt.timedelta(days=(1 - first.weekday()) % 7)

    year = today.year if today.year % 2 else today.year - 1
    day = april_election(year)
    return day if day <= today else april_election(year - 2)


def fetch_north_suburban_board(warnings):
    """-> [member] from the PDF the library's own page links.

    The link is found by its TEXT ("Current Board of Trustees and Terms") and
    never by filename: the file sits under /wp-content/uploads/2022/03/ and is
    re-uploaded in place, so its path claims 2022 while its content runs to
    2029. That is the Boone-yearbook filename trap wearing a different hat, and
    it is the reason this project reads link text everywhere it can.
    """
    import io as io_mod
    conf = OWN_BOARDS["NORTH SUBURBAN DISTRICT LIBRARY"]
    page = _get(conf["url"], warnings, "NORTH SUBURBAN DISTRICT LIBRARY")
    if page is None:
        return []
    import urllib.parse
    href = None
    for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page.text,
                             re.S | re.I):
        label = clean(re.sub(r"(?s)<[^>]+>", "", html_mod.unescape(match.group(2))))
        if label and re.search(conf["link_text"], label, re.I):
            href = urllib.parse.urljoin(page.url, html_mod.unescape(match.group(1)))
            break
    if not href:
        warnings.append("NORTH SUBURBAN DISTRICT LIBRARY: no %r link on %s — "
                        "the administration page was rebuilt"
                        % (conf["link_text"], conf["url"]))
        return []
    doc = _get(href, warnings, "NORTH SUBURBAN DISTRICT LIBRARY")
    if doc is None:
        return []
    if not doc.content.startswith(b"%PDF"):
        warnings.append("NORTH SUBURBAN DISTRICT LIBRARY: %s is not a PDF" % href)
        return []
    # WHAT A DOCUMENT SOURCE OWES THAT A PAGE DOES NOT: a date, and a rule for
    # when it is too old. A page is re-read weekly and shows its own drift; a
    # PDF can sit unchanged through an election and still parse perfectly. So
    # its Last-Modified is carried onto every member and checked against the
    # last CONSOLIDATED ELECTION — Illinois library-district trustees are
    # elected in April of odd-numbered years, so a roster document that
    # predates the most recent one describes a board that may no longer exist.
    # That is a real test rather than an arbitrary number of months.
    modified = doc.headers.get("Last-Modified")
    stamp = _http_date(modified)
    if stamp is None:
        warnings.append("NORTH SUBURBAN DISTRICT LIBRARY: %s carries no usable "
                        "Last-Modified (%r) — its age cannot be checked"
                        % (href, modified))
    else:
        cutoff = _last_consolidated_election(datetime.now(timezone.utc).date())
        if stamp.date() < cutoff:
            warnings.append(
                "NORTH SUBURBAN DISTRICT LIBRARY: %s was last modified %s, "
                "BEFORE the %s consolidated election — trustees are elected in "
                "April of odd years, so this document may name a board that no "
                "longer sits" % (href, stamp.date().isoformat(), cutoff.isoformat()))
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required")
    members = []
    with pdfplumber.open(io_mod.BytesIO(doc.content)) as pdf:
        for page_obj in pdf.pages:
            for line in (page_obj.extract_text() or "").splitlines():
                line = clean(line) or ""
                match = re.match(r"^(.+?)\s+((?:19|20)\d{2})$", line)
                if not match:
                    continue
                name, role = split_name_role(match.group(1))
                if not looks_like_name(name):
                    continue
                members.append({"name": name, "role": role or "Trustee",
                                "term": match.group(2), "email": None})
    if not members:
        warnings.append("NORTH SUBURBAN DISTRICT LIBRARY: %s carried no "
                        "'<name> <year>' rows — the document's shape changed"
                        % href)
    # The DOCUMENT is what these names come from, so the card cites the document
    # and its date — not the administration page that merely links it.
    return members, href, (stamp.date().isoformat() if stamp else None)


def apply_own_boards(bodies, warnings):
    """Replace or supply each board from whoever maintains it. See the module
    docstring: the yearbook is never a fallback for a board it is known to be
    stale about."""
    by_name = {b["district"]: b for b in bodies}
    fetchers = {
        "BELVIDERE PARK DISTRICT": fetch_belvidere_park_board,
        "IDA PUBLIC LIBRARY": fetch_ida_board,
        "ROCKFORD PARK DISTRICT": fetch_rockford_board,
        "NORTH SUBURBAN DISTRICT LIBRARY": fetch_north_suburban_board,
        "CHERRY VALLEY DISTRICT LIBRARY": fetch_cherry_valley_board,
    }
    for heading, spec in BODIES.items():
        body = by_name.get(heading)
        if body is None:
            continue
        body["vacancies"] = 0
        body["seats"] = None
        if spec["board_source"] == "yearbook":
            body["boardSource"] = {
                "label": "Boone County Clerk & Recorder Year Book",
                "url": body.get("_sourceUrl"),
            }
            continue
        if spec["board_source"] is None:
            body["board"] = []
            body["boardSource"] = None
            continue
        conf = OWN_BOARDS[heading]
        fetched = fetchers[heading](warnings)
        # Three fetcher shapes. A bare list; (members, vacancies, seats) where
        # the body STATES its own seat count and STATES its own vacancies in
        # words (a fetcher never derives one from the other — see below); or
        # (members, document_url, document_date) where the names come from a
        # DOCUMENT rather than a page, so the card can cite the document and
        # say when it was last changed.
        doc_url = doc_date = None
        if isinstance(fetched, tuple) and len(fetched) == 3 and \
                isinstance(fetched[1], (str, type(None))):
            members, doc_url, doc_date = fetched
        elif isinstance(fetched, tuple):
            members, body["vacancies"], body["seats"] = fetched
        else:
            members = fetched

        # WHERE BOTH PUBLISHERS NAME THE SAME PERSON, the yearbook's TERM YEAR
        # rides along — it is a fact about that person that the body's own page
        # does not print, and carrying it is not a composite claim about a role.
        # A person only ONE source names never gains the other's fields.
        yearbook = {m["name"]: m for m in body["board"]}
        for member in members:
            counterpart = yearbook.get(member["name"])
            if counterpart and not member.get("term") and counterpart.get("term"):
                member["term"] = counterpart["term"]

        if members and yearbook:
            changed = sorted(set(yearbook).symmetric_difference(
                {m["name"] for m in members}))
            if changed:
                warnings.append(
                    "%s: the county's yearbook and the body's own board page "
                    "disagree on %d name(s) (%s) — the body's own page ships, "
                    "because it is what the body maintains and the booklet is "
                    "an annual snapshot"
                    % (heading, len(changed), ", ".join(changed)))

        if not members:
            body["board"] = []
            body["boardSource"] = None
            continue
        # A SHORT BOARD IS A PARSE FAILURE UNTIL THE BODY SAYS OTHERWISE. This
        # is the rule that a shipped falsehood bought: Belvidere Park's fetcher
        # used to compute `vacancies = seats - len(members)`, so when a markup
        # quirk hid Carrie Lenzen the card announced "1 of 5 seats is vacant"
        # about a district whose own page names five commissioners. Arithmetic
        # cannot tell a missing person from a missing seat. Only a body's own
        # word can — Ida's list prints "Trustee: Open" — so `vacancies` is
        # counted from that token and from nothing else, and any OTHER
        # shortfall against the seat count the body states is reported as what
        # it is. The builder's per-body floor is what stops it shipping.
        stated = body["seats"] if body["seats"] is not None else spec.get("own_seats")
        if stated is not None:
            accounted = len(members) + (body["vacancies"] or 0)
            if accounted < stated:
                warnings.append(
                    "%s: parsed %d member(s) plus %d stated vacancy(ies) "
                    "against the %d seats this body states — that is a PARSE "
                    "MISS or a body that stopped listing someone, NEVER a "
                    "vacancy; no empty seat is claimed from the difference"
                    % (heading, len(members), body["vacancies"] or 0, stated))
            elif accounted > stated:
                warnings.append(
                    "%s: parsed %d seat(s) against the %d this body states — "
                    "the page's shape moved, or the board grew"
                    % (heading, accounted, stated))
        body["board"] = members
        source = {"label": conf["label"], "url": doc_url or conf["url"]}
        if doc_date:
            source["modified"] = doc_date
        body["boardSource"] = source


# What the card tells a reader about a board nobody readable publishes. Written
# per body and MEASURED rather than asserted: the app used to carry one
# hardcoded sentence naming Winnebago, which is true of Cherry Valley and would
# be a fabrication the day a Boone-seated body lost its board page.
BOARD_ABSENT_NOTES = {
    "CHERRY VALLEY DISTRICT LIBRARY":
        "This district's board is not named here. The County Clerk's yearbook "
        "lists Boone County's own officials and this library district is seated "
        "in Winnebago County, and the library's own site could not be read.",
}
BOARD_ABSENT_DEFAULT = ("This district's board is not named here — no source "
                        "this site can read publishes it.")


def normalise_websites(bodies, warnings):
    """Make each office website an absolute URL, and prove it answers.

    The yearbook prints bare hosts ("www.belviderepark.org"). The card's link
    helper accepts only an absolute http(s) URL and returns null otherwise, so a
    bare host is a footer link that SILENTLY does not render — the card looks
    finished and the reader has nowhere to go. Normalising is not enough on its
    own: a scheme this project chose rather than measured is a guess, so each
    URL is fetched once and shipped only if a server answered.

    ANY HTTP STATUS COUNTS AS ANSWERING, including Cherry Valley's 502. A
    status is the site's own problem and it is still the right address; only a
    DNS or connection failure means there is nothing to link to.
    """
    import requests
    for body in bodies:
        site = body["office"].get("website")
        if not site:
            continue
        url = site if re.match(r"(?i)^https?://", site) else "https://" + site
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                                allow_redirects=True)
            body["office"]["website"] = url
            if resp.status_code >= 400:
                warnings.append("%s: %s answers HTTP %d — shipped anyway, "
                                "because a status is the site's own problem and "
                                "the address is still right"
                                % (body["district"], url, resp.status_code))
        except Exception as exc:  # noqa: BLE001
            body["office"].pop("website", None)
            warnings.append("%s: dropped the website %s — nothing answered at "
                            "all (%s), so the card links nothing rather than a "
                            "dead address" % (body["district"], url, exc))


def apply_board_notes(bodies):
    for body in bodies:
        if body["board"]:
            body["boardNote"] = None
            continue
        body["boardNote"] = BOARD_ABSENT_NOTES.get(body["district"],
                                                   BOARD_ABSENT_DEFAULT)


def apply_ida_contacts(bodies, warnings):
    """Ida's contacts come from the library, which owns its own mailboxes.

    Two things the yearbook cannot give. Its office e-mail is a PERSON's work
    address printed under the body's heading, where the library publishes a
    standing `Board@` mailbox that survives any one trustee; and it prints the
    director's own address with a transposed letter. Both are read off the
    library's own pages rather than carried as constants — a corrected address
    hardcoded here is a fact this repo would keep asserting long after the
    library changed it.

    The yearbook's typo is still RECOGNISED, so the disagreement is reported
    every run instead of being quietly overwritten. Unlike this county's
    Belvidere telephone disagreement, where two publishers differ and nothing
    settles which is right, a library owns its own mailbox.
    """
    body = {b["district"]: b for b in bodies}.get("IDA PUBLIC LIBRARY")
    if body is None:
        return

    # Read the yearbook's own value BEFORE anything overwrites it — the first
    # draft compared against the board mailbox it had just written in, so the
    # typo report stopped firing while the typo was still there.
    printed = body["office"].get("email")

    board_page = _get(OWN_BOARDS["IDA PUBLIC LIBRARY"]["url"], warnings,
                      "IDA PUBLIC LIBRARY")
    board_mail = None
    if board_page is not None:
        found = IDA_BOARD_EMAIL_RE.search(_visible_text(board_page.text))
        board_mail = found.group(0) if found else None
    if board_mail:
        body["office"]["email"] = board_mail
    else:
        warnings.append("IDA PUBLIC LIBRARY: the library's board page no longer "
                        "publishes a standing board mailbox — the office keeps "
                        "whatever the yearbook printed, which is a person's own "
                        "work address")

    contact = _get(IDA_CONTACT_PAGE, warnings, "IDA PUBLIC LIBRARY")
    if contact is None:
        return
    text = _visible_text(contact.text)
    for index, head in enumerate(body["heads"]):
        at = text.find(head["name"])
        if at < 0:
            warnings.append("IDA PUBLIC LIBRARY: %s is not on %s — the "
                            "yearbook and the library disagree about who runs "
                            "it, or the page was rebuilt"
                            % (head["name"], IDA_CONTACT_PAGE))
            continue
        # THE LIBRARY'S TITLE FOR ITS OWN STAFF WINS. The yearbook prints
        # "Executive Director" and the library's contact page prints "Mindy
        # Long, Library Director" — its own words about its own officer, on the
        # page it maintains. Same rule as the address below it: a body owns
        # what it calls its people.
        title = re.match(r"\s*,?\s*([A-Z][A-Za-z .-]{3,40}?)\s*[;:(]",
                         text[at + len(head["name"]):at + len(head["name"]) + 80])
        if title:
            published = clean(title.group(1))
            if published and published != head["role"]:
                warnings.append("IDA PUBLIC LIBRARY: the yearbook calls %s "
                                "%r and the library's own page calls them %r "
                                "— the library's title ships"
                                % (head["name"], head["role"], published))
                head["role"] = published
        found = EMAIL_RE.search(text[at:at + 400])
        if not found:
            continue
        head["email"] = found.group(0)
        # The yearbook printed ONE address under this body's heading and it is
        # the DIRECTOR's, so only the director's row can supersede it. Reporting
        # it per head made the assistant director's address read as a correction
        # of the director's, which is a second wrong claim rather than a check.
        if index == 0 and printed == IDA_YEARBOOK_TYPO \
                and found.group(0) != printed:
            warnings.append(
                "IDA PUBLIC LIBRARY: the yearbook prints %s's address as %s; "
                "the library's own contact page prints %s. The library owns "
                "the mailbox, so its spelling ships."
                % (head["name"], IDA_YEARBOOK_TYPO, found.group(0)))


def scrape(pdf_bytes, source_url, warnings, own_boards=True):
    lines = page_lines(pdf_bytes)
    blocks = collect_blocks(lines, warnings)
    staff_dropped = []
    bodies = []
    for heading in BODIES:
        if heading not in blocks:
            continue
        body = parse_block(heading, blocks[heading], warnings, staff_dropped)
        body["_sourceUrl"] = source_url
        bodies.append(body)
    if own_boards:
        apply_own_boards(bodies, warnings)
        apply_ida_contacts(bodies, warnings)
        normalise_websites(bodies, warnings)
    apply_board_notes(bodies)
    for body in bodies:
        body.pop("_sourceUrl", None)
    return {
        "source": "Boone County Clerk & Recorder, Boone County Year Book",
        "sourceUrl": source_url,
        "officialsPage": INDEX_PAGE,
        "scrapedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bodies": bodies,
        "staffDropped": staff_dropped,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/source/boone-district-officials.json")
    ap.add_argument("--pdf", help="parse a local PDF instead of fetching")
    ap.add_argument("--no-own-boards", action="store_true",
                    help="yearbook only — skip each body's own board page "
                         "(for isolating a parse regression, never for a build)")
    args = ap.parse_args()

    warnings = []
    if args.pdf:
        source_url = discover_yearbook_url([])
        pdf_bytes = open(args.pdf, "rb").read()
    else:
        source_url = discover_yearbook_url(warnings)
        pdf_bytes = fetch_pdf(source_url)

    payload = scrape(pdf_bytes, source_url, warnings,
                     own_boards=not args.no_own_boards)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    for body in payload["bodies"]:
        source = (body.get("boardSource") or {}).get("label") or "-- none --"
        print("  %-32s office=%s phone=%-12s heads=%d board=%d%s  board from: %s"
              % (body["district"],
                 "yes" if body["office"]["address"] else "NO",
                 body["office"]["phone"] or "NO",
                 len(body["heads"]), len(body["board"]),
                 (" +%d vacant" % body["vacancies"]) if body.get("vacancies") else "",
                 source))
    if payload["staffDropped"]:
        print("  staff parsed and deliberately not shipped (%d): %s"
              % (len(payload["staffDropped"]), "; ".join(payload["staffDropped"])))
    for warning in payload["warnings"]:
        print("  WARN %s" % warning)
    print("boone-district-officials: %d bodies -> %s"
          % (len(payload["bodies"]), args.out))


if __name__ == "__main__":
    main()
