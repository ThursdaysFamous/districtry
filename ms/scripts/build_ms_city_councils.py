#!/usr/bin/env python3
"""Build ms/data/app/ms-city-councils.json: the mayor and the council or board
of aldermen of each Mississippi city of 25,000 people or more, seat by seat, as
each city's own website names them.

WHICH CITIES. The fifteen incorporated places the 2020 census counts at 25,000
or more, from Jackson (153,701) down to Brandon (25,138); the next is
Starkville at 24,360. A fetching build asks the Census Bureau's 2020 place
layer for every Mississippi place of 25,000 or more and stops unless the answer
is exactly the fifteen in CITIES, so a city cannot be missed or listed twice.

THE SOURCE IS EACH CITY'S OWN WEBSITE, AND NOTHING ELSE. Fourteen of the
fifteen print their mayor and every member by seat. Greenville does not: when
its site was read on 2026-10-16, its "City Council" menu item opened the city
clerk's page, which names no member, the site's own sitemap of 34 pages held
no council page, and its mayor's page described a term that began on
1 January 2020 without saying who holds the office now. So Greenville's record
names nobody and says why (NOT_PUBLISHED). The Mississippi Municipal League's
member page for Greenville lists a mayor and six council members by title,
with no ward and no date; those are not the city's own words, and they are not
used.

WHO WAS CHECKED AGAINST WHAT, 2026-10-16. Most of these cities elected their
mayor and council on 3 June 2025 for the term that began on 1 July 2025. The
Secretary of State posts each city's recapitulation of that election, or the
order that dispensed with it where one person qualified for each office, and
ten were read (Jackson, Gulfport, Southaven, Hattiesburg, Tupelo, Meridian,
Pearl, Horn Lake, Oxford, Brandon): each names the same people for the same
seats as the city's own page, except Gulfport Ward 2, which a special election
filled after the member elected in 2025 resigned. Biloxi, Olive Branch,
Clinton and Madison were checked against their own swearing-in news or
minutes from July and August 2025 instead. Those filings are scans and are not
read by this builder; the city's page is, because a recapitulation is who won
in June 2025 and the city's page is who the city says sits now.

HOW A PAGE IS READ. Its visible text, one line per block element, scripts and
styles left out (page_lines). A SEAT LABEL is a line that is nothing but a
seat: "Ward 3", "WARD 3", "Ward III", "Alderman Ward 3", "Alderman-at-Large",
"At Large", ", Ward I", "Pro-Tem, Ward VI". A longer line that mentions a ward
("an advocate for the growth and prosperity of Ward 2", "Ward 1 Councilman")
is never one. Each city's page prints its members in one of four shapes,
measured 2026-10-16 and declared per city in CITIES:
    "name, seat"   one line, the name then the seat (Jackson)
    "seat - name"  one line, the seat, a dash, the name (Hattiesburg)
    "name / seat"  the name on the line before the seat label
    "seat / name"  the name on the line after it, a lone dash skipped
                   (Southaven prints one between them)
The mayor is found by a pattern of its own per city, on the mayor's page where
the city has one (MAYOR in CITIES).

THE GATES. A city's seats must be exactly the seats it declares: its wards
numbered 1 to N and, where it has one, its at-large seat. A seat may appear
more than once on a page (Hattiesburg prints its council twice), and every
reading of it that looks like a name must be the same name. A name must look
like a person's: two to six words of letters, with initials, a nickname in
quotes, a hyphen or an apostrophe, and a "Jr.", "Sr." or Roman numeral after
it, and no digit, @, possessive or word such as Ward, Council, Mayor, Email or
City. A reading that fails that test is not a name and is set aside (a menu
item under a seat label, such as Biloxi's "Mayor" above "CAO"), but a seat
with no reading left stops the build. A seat the page shows as "Vacant" is
carried as vacant rather than as a person called Vacant. No city may name one
person for two seats. A failure stops the build and names the city and the
seat, never the text around it.

WHAT IS CARRIED, AND WHAT NEVER IS. The seat, the name and, where the city's
page prints them inside a person's own entry, that person's telephone numbers
and e-mail address. Until 2026-10-17 neither was carried, because whether a
number or an address printed beside a member is the office's or the member's
own was not established; that day Adam ruled for the whole fleet, "if the
official government source uses personal phone numbers, we publish those",
and later the same day extended the ruling to e-mail, so that a personal
e-mail address a government page prints beside an official is published too.
So a number or an address the city's own page prints inside one person's
entry is carried on that person, whichever kind it is.

TELEPHONE NUMBERS. Measured 2026-10-17, the pages that print a number inside a
member's entry are Olive Branch's (the mayor and every alderman, under "Phone:"),
Madison's (six of its seven aldermen), Horn Lake's (the mayor and every
alderman, and one alderman's second number under "Mobile:"), Oxford's (six of
its seven aldermen, each number labelled "Home", "Work" or "Cell", two of them
with two) and Brandon's (every alderman, under "Tel:"); each of those five
declares `phones` in CITIES, and the other ten pages print no number inside a
member's entry. A label that says which line a number is goes in front of it as the
card prints it ("home 662-555-0100"); one that says only that it is a
telephone ("Phone:", "Tel:") is left off. A number is carried only when it is
printed ONCE on the city's pages that are read, inside one person's entry: a
number printed for two people, or anywhere else on those pages (City Hall's
line in a footer, or the mayor's office line Oxford prints on its mayor's page
as well as beside the mayor), is the office's, and is not carried. A fax
number is never carried.

E-MAIL ADDRESSES. Measured 2026-10-17, 61 people in nine cities carry one:
Olive Branch's and Horn Lake's mayors and every one of their aldermen,
Gulfport's and Tupelo's seven council members each, Madison's, Pearl's and
Brandon's seven aldermen each, and Hattiesburg's and Meridian's five council
members each; each of those nine declares `emails` in CITIES. Jackson,
Southaven, Biloxi, Clinton and Oxford print none inside a member's entry
(Biloxi prints its addresses above its members and Oxford after them, and
both of Oxford's are office mailboxes). Most are at the city's own domain.
Horn Lake's are named for the seat ("ward 1") rather than the person, and are
carried because each is printed beside one member; Madison's, and one of
Gulfport's, are at domains other than the city's. An address is carried only
when it is printed inside one person's entry and nowhere else on the city's
pages that are read, and is not an office's mailbox (OFFICE_MAILBOXES: info,
cityhall, clerk, council and the like): an address printed for two people, or
printed again in a footer or on the mayor's page, is the office's, and is not
carried. Addresses are compared without regard to case, and one is carried as
the page first prints it. A mayor carries an address only where the council
page prints the mayor's entry (Olive Branch and Horn Lake); a mayor's own page
is read for the name, and to count what it prints again, never for an address
to carry. The build stops on a person with two addresses of their own (the
card shows one); on an address among the members that the page hides behind a
script (Cloudflare's e-mail protection), which this reader does not undo,
although builders elsewhere in the fleet do (Illinois's since 2026-08-08): no
page read here on 2026-10-17 hides one, so the stop leaves the first one to a
person; and on a link among the members with no text of its own unless the
same entry prints that address as text, because whose an untexted link is
cannot be read.
Hattiesburg prints each member's address in a card of its own below its list
of members, so it is read card by card: a card must carry exactly one seat
line, and the name above that line must be the one the list gives the seat.

What is never read into the file, written or printed, not even in an error
message: a street address (Oxford's page prints one inside each alderman's
entry, which may be a home). An error names only the city and the seat, never
a number or an e-mail address. No staff member (a city clerk, a council clerk,
an assistant to the mayor) is named, and no staff member's number or address
is carried: Gulfport's page prints its clerks' contacts above the members,
and Hattiesburg's prints them above the members' cards, outside every
member's entry.

NAMES THE PAGE PRINTS IN CAPITALS ARE RE-CASED (Gulfport, Tupelo, Pearl and
Tupelo's mayor): each word is capitalised, initials and Roman numerals are
kept, "Jr." and "Sr." are written so, a hyphenated name is capitalised on both
sides, and "Mc" and "O'" take a capital after them. A name the page prints in
mixed case is kept exactly as printed.

robots.txt. Every host's robots.txt is read, with the client that crawls,
before the first fetch from it, and every page is checked against it, not
only the first on each host (one RobotsGate per run). Measured 2026-10-16:
jacksonms.gov asks for a Crawl-delay of 3 seconds, which is honoured; no
other host asks for one, and the build waits at least one second between two
requests to one host. The Census Bureau's TIGERweb host serves no robots.txt
(allow all).

THE READ DATE. Each city carries the date its pages were read. No weekly job
reads them again yet (a new workflow needs the operator's word), so the City
card says when they were read.

Usage:
    python3 ms/scripts/build_ms_city_councils.py              # fetch + write
    python3 ms/scripts/build_ms_city_councils.py --pages DIR --read-date YYYY-MM-DD
        # read saved copies named <slug>-council.htm / <slug>-mayor.htm
    python3 ms/scripts/build_ms_city_councils.py --save-pages DIR   # fetch, keep copies
    python3 ms/scripts/build_ms_city_councils.py --check      # offline gate on the shipped file
    python3 ms/scripts/build_ms_city_councils.py --selftest   # the page readers on fixtures
"""

import argparse
import gzip
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from robots_policy import RobotsGate  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/ms/)"
HEADERS = {"User-Agent": USER_AGENT}
OUT = os.path.join(INSTANCE, "data", "app", "ms-city-councils.json")

POPULATION_FLOOR = 25000
CENSUS_PLACES = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                 "tigerWMS_Census2020/MapServer/26/query")
MIN_DELAY_S = 1.0

# The fifteen cities, largest first. `wards` and `at_large` are each city's own
# statement of its form where it prints one, and its seat labels where it does
# not (measured 2026-10-16). `members` is the shape its page prints them in;
# `mayor` is (page, how, pattern): "line" takes the pattern's name group from a
# line, "before" the line before a line the pattern matches, "after" the line
# after one. On the ten cities whose council page prints a telephone number
# or an e-mail address inside a person's own entry (measured 2026-10-17),
# `phones` and `emails` are the fewest named people the page must give a
# number, or an address, of their own: about two thirds of the count measured
# that day, which is given beside each. `end` matches the line where the
# page's last entry ends. Hattiesburg prints each member's address in a card
# of its own below its list of members, so it declares `cards` instead of
# `end`: the class the page gives each card, and the card's seat line.
CITIES = [
    {"geoid": "2836000", "name": "Jackson", "body": "City Council",
     "wards": 7, "at_large": 0,
     "council": "https://jacksonms.gov/government/city-council/",
     "mayor_page": "https://jacksonms.gov/government/mayor-office/",
     "members": "name, seat",
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$")},
    {"geoid": "2829700", "name": "Gulfport", "body": "City Council",
     "wards": 7, "at_large": 0,
     "council": "https://www.gulfport-ms.gov/government/city_council.php",
     "mayor_page": "https://www.gulfport-ms.gov/government/office_of_the_mayor/index.php",
     "members": "name / seat",
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$"),
     "end": r"^Share this page$", "emails": 5},    # addresses: all 7 members
    {"geoid": "2869280", "name": "Southaven", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://southaven.org/462/Board-of-Aldermen",
     "mayor_page": "https://southaven.org/155/Mayors-Office",
     "members": "seat / name",
     "mayor": ("mayor", "before", r"^Mayor$")},
    {"geoid": "2806220", "name": "Biloxi", "body": "City Council",
     "wards": 7, "at_large": 0,
     "council": "https://biloxi.ms.us/departments/city-council/",
     "mayor_page": "https://biloxi.ms.us/departments/mayor/",
     "members": "seat / name",
     "mayor": ("mayor", "after", r"^Mayor$")},
    {"geoid": "2831020", "name": "Hattiesburg", "body": "City Council",
     "wards": 5, "at_large": 0,
     "council": "https://www.hattiesburgms.com/council/",
     "mayor_page": "https://www.hattiesburgms.com/tobybarker/",
     "members": "seat - name",
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$"),
     "cards": ("tmm_member", r"^Ward (?P<ward>\d{1,2}) Council(?:wo)?man$"),
     "emails": 4},                                  # addresses: all 5 members
    {"geoid": "2854040", "name": "Olive Branch", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.obms.us/230/Board-of-Aldermen",
     "mayor_page": None,
     "members": "name / seat",
     "mayor": ("council", "before", r"^Mayor$"),
     "end": r"^Board of Aldermen$", "phones": 6, "emails": 6},  # both: the mayor and all 7
    {"geoid": "2874840", "name": "Tupelo", "body": "City Council",
     "wards": 7, "at_large": 0,
     "council": "https://www.tupeloms.gov/my-government/city-council",
     "mayor_page": "https://www.tupeloms.gov/my-government/mayor",
     "members": "name / seat",
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$"),
     "end": r"^City Council.s Agendas and Minutes$", "emails": 5},  # addresses: all 7
    {"geoid": "2846640", "name": "Meridian", "body": "City Council",
     "wards": 5, "at_large": 0,
     "council": "https://meridianms.org/government/city-council/",
     "mayor_page": "https://meridianms.org/government/mayor/",
     "members": "seat / name",
     "mayor": ("mayor", "line", r"^A Message from Mayor (?P<name>.+)$"),
     "end": r"^Archives$", "emails": 4},            # addresses: all 5 members
    {"geoid": "2829180", "name": "Greenville", "body": "City Council",
     "wards": 6, "at_large": 0,
     "council": "https://greenvillems.org/government/",
     "mayor_page": None,
     "members": None,
     "mayor": None},
    {"geoid": "2814420", "name": "Clinton", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://clintonms.org/people/",
     "mayor_page": None,
     "members": "seat / name",
     "mayor": ("council", "line", r"^Mayor (?P<name>.+)$")},
    {"geoid": "2844520", "name": "Madison", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://madisonthecity.com/government/aldermen/",
     "mayor_page": "https://madisonthecity.com/government/mayor/",
     "members": "name / seat",
     "mayor": ("mayor", "before", r"^Mayor$"),
     "end": r"^Ward Line Map$", "phones": 4, "emails": 5},  # numbers: 6 of the 7; addresses: all 7
    {"geoid": "2855760", "name": "Pearl", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.cityofpearl.com/government/board-of-aldermen/",
     "mayor_page": "https://www.cityofpearl.com/government/mayors-office/",
     "members": "name / seat",
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$"),
     "end": r"^City Calendar$", "emails": 5},       # addresses: all 7 aldermen
    {"geoid": "2833700", "name": "Horn Lake", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.hornlake.org/government",
     "mayor_page": None,
     "members": "seat / name",
     "mayor": ("council", "after", r"^Mayor$"),
     "end": r"^Emergencies\b", "phones": 6, "emails": 6},  # both: the mayor and all 7
    {"geoid": "2854840", "name": "Oxford", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.oxfordms.net/board-of-aldermen",
     "mayor_page": "https://www.oxfordms.net/departments/mayor-s-office",
     "members": "name / seat",
     "mayor": ("mayor", "before", r"^,?\s*Mayor$"),
     "end": r"^The Mayor and the Board are elected\b", "phones": 4},  # numbers: 6 of the 7
    {"geoid": "2808300", "name": "Brandon", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://brandonms.org/government/board-of-aldermen/",
     "mayor_page": "https://brandonms.org/government/office-of-the-mayor/",
     "members": "name / seat",
     "mayor": ("mayor", "line", r"^(?P<name>.+), Mayor$"),
     "end": r"^Ward Map$", "phones": 5, "emails": 5},  # both: all 7 aldermen
]

# A city whose own website names no mayor or member, with the date that was
# measured and the reason in words the card prints.
NOT_PUBLISHED = {
    "2829180": {
        "measured": "2026-10-16",
        "why": ("Greenville's own website does not name its mayor or its council "
                "members: its City Council page is the city clerk's page, which "
                "names no member, and its mayor's page describes a term that "
                "began in January 2020"),
    },
}

SHAPES = ("name, seat", "seat - name", "name / seat", "seat / name")

# ---------------------------------------------------------------------------
# Page text
# ---------------------------------------------------------------------------
SKIP_TAGS = {"script", "style", "noscript", "svg", "head", "template"}
BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr",
              "td", "th", "section", "article", "span", "a", "strong", "b", "em",
              "header", "footer", "dt", "dd", "figcaption", "label", "button"}


class _Text(HTMLParser):
    """The page's visible text, one line per block element. Beside it, `mail`
    holds (line, address, has text, card) for every mailto: link: the line its
    text starts on, or for a link with no text of its own (an icon) the line
    after it; `hidden` holds the line of every address the page hides behind
    a script (Cloudflare's e-mail protection), which this reader does not
    undo; and with
    `card`, a class name, `cards` holds the (first line, stop) of every div
    carrying that class, and `card` in a mark is the card it is inside."""

    def __init__(self, card=None):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.skip = 0
        self.buf = []
        self.lines = []
        self.mail = []
        self.hidden = []
        self.link = None
        self.card = card
        self.cards = []
        self.depth = 0
        self.card_first = None

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        if tag in BLOCK_TAGS:
            self.flush()
        if self.skip:
            return
        a = dict(attrs)
        if tag == "div" and self.card:
            if self.depth:
                self.depth += 1
            elif self.card in (a.get("class") or "").split():
                self.depth, self.card_first = 1, len(self.lines)
        href = (a.get("href") or "").strip()
        if tag == "a" and href.lower().startswith("mailto:"):
            self.link = (len(self.lines), mailto_address(href))
        if "/cdn-cgi/l/email-protection" in href or "data-cfemail" in a:
            self.hidden.append(len(self.lines))

    def handle_startendtag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.flush()

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        if tag in BLOCK_TAGS:
            self.flush()
        if self.skip:
            return
        if tag == "a" and self.link:
            start, address = self.link
            self.link = None
            self.mail.append((start, address, len(self.lines) > start,
                              len(self.cards) if self.depth else None))
        if tag == "div" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.cards.append((self.card_first, len(self.lines)))

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)

    def flush(self):
        s = re.sub(r"\s+", " ", "".join(self.buf).replace("\xa0", " ")).strip()
        if s:
            self.lines.append(s)
        self.buf = []


def page_lines(html):
    """The visible text of a page, one line per block element."""
    t = _Text()
    t.feed(html)
    t.close()
    t.flush()
    return t.lines


# An e-mail address as these pages print and link it.
EMAIL = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}"
EMAIL_TEXT = re.compile(r"(?<![A-Za-z0-9._%+\-])" + EMAIL + r"(?![A-Za-z0-9\-])")
OWN_EMAIL = re.compile(r"^" + EMAIL + r"$")
# The mailbox (the part before the @, without dots, hyphens and underscores)
# of an address that is the office's wherever it is printed: city hall's, a
# clerk's, or the whole board's. A seat's own mailbox (Horn Lake's are named
# for each ward) is not here: it reaches the member who holds the seat.
OFFICE_MAILBOXES = {"info", "cityhall", "city", "contact", "contactus", "office",
                    "admin", "webmaster", "clerk", "cityclerk", "council",
                    "citycouncil", "aldermen", "board", "boardofaldermen"}


def mailto_address(href):
    """The address a mailto: link opens, without its ?subject= or the like."""
    return urllib.parse.unquote(href.split(":", 1)[1].split("?", 1)[0]).strip()


def office_mailbox(address):
    return re.sub(r"[._\-]", "", address.split("@", 1)[0].lower()) in OFFICE_MAILBOXES


def page_text(html, card=None):
    """(lines, marks, cards, hidden) for a page: its lines as page_lines reads
    them; every place it prints an e-mail address, as (line, address, has
    text, card), a link and an address printed as text each counting once;
    the (first line, stop) of every card carrying the class `card`; and the
    lines where the page hides an address behind a script."""
    t = _Text(card)
    t.feed(html)
    t.close()
    t.flush()
    marks = list(t.mail)
    for i, ln in enumerate(t.lines):
        k = next((k for k, (first, stop) in enumerate(t.cards) if first <= i < stop), None)
        for m in EMAIL_TEXT.finditer(ln):
            marks.append((i, m.group(0), True, k))
    return t.lines, marks, t.cards, t.hidden


# ---------------------------------------------------------------------------
# Seats and names
# ---------------------------------------------------------------------------
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
         "viii": 8, "ix": 9, "x": 10}
SEAT_LINE = re.compile(
    r"^,?\s*(?:pro[\s-]?tem\s*,?\s*)?"
    r"(?:(?:alderm[ae]n|alderwoman|council\s*(?:wo)?m[ae]n|council\s+member)[\s-]+)?"
    r"(?:(?P<at>at[\s-]+large)|ward\s+(?P<ward>\d{1,2}|[ivx]{1,4}))\s*$", re.I)
NAME_COMMA_SEAT = re.compile(r"^(?P<name>.+?),\s*(?P<seat>ward\s+(?:\d{1,2}|[ivx]{1,4}))$", re.I)
SEAT_DASH_NAME = re.compile(r"^(?P<seat>ward\s+(?:\d{1,2}|[ivx]{1,4}))\s*[-–—]\s*(?P<name>.+)$", re.I)
SEPARATOR = re.compile(r"^[-–—|:·•]+$")


def seat_of(text):
    """'Ward N' or 'At Large' for a line that is nothing but a seat, else None."""
    m = SEAT_LINE.match(text.strip())
    if not m:
        return None
    if m.group("at"):
        return "At Large"
    w = m.group("ward").lower()
    n = int(w) if w.isdigit() else ROMAN.get(w)
    return "Ward %d" % n if n else None


SUFFIX = re.compile(r",?\s+(?P<sfx>jr\.?|sr\.?|ii|iii|iv|v)\s*$", re.I)
NAME_CHARS = re.compile(r"^[^\W\d_][\w.'’‘\"“”\- ]*$", re.U)
STOPWORDS = {
    "ward", "wards", "council", "councilman", "councilwoman", "councilmember",
    "alderman", "alderwoman", "aldermen", "mayor", "mayors", "city", "board",
    "email", "e-mail", "phone", "fax", "office", "district", "large", "member",
    "members", "send", "map", "maps", "contact", "department", "departments",
    "the", "of", "and", "for", "staff", "clerk", "vice", "president",
    "pro-tem", "agenda", "agendas", "meeting", "meetings", "minutes", "view",
    "click", "here", "print", "home", "search", "menu", "government", "cao",
}


def split_suffix(name):
    m = SUFFIX.search(name)
    if not m:
        return name.strip().rstrip(","), None
    return name[:m.start()].strip().rstrip(","), m.group("sfx")


def is_vacant(text):
    return text.strip().strip(".").lower() in ("vacant", "vacancy", "seat vacant")


def name_problem(text):
    """Why `text` is not a person's name, or None when it looks like one."""
    s = text.strip().rstrip(",")
    if not s or len(s) > 60:
        return "length"
    if re.search(r"\d|@|\?|!|/|:|\(|\)", s):
        return "digit or symbol"
    if re.search(r"['’]s\b", s, re.I) and not re.search(r"['’]s\w", s, re.I):
        return "possessive"
    core, _ = split_suffix(s)
    if not NAME_CHARS.match(core):
        return "characters"
    words = core.replace(",", " ").split()
    if not 2 <= len(words) <= 6:
        return "word count"
    for w in words:
        bare = w.strip("\"'‘’“”.").lower()
        if bare in STOPWORDS:
            return "word %r" % bare
    return None


def _case_word(w):
    if re.match(r"^(?:[A-Z]\.)+$", w):          # initials: F.B.
        return w
    if "-" in w:
        return "-".join(_case_word(p) for p in w.split("-"))
    m = re.match(r"^([\"'‘“]*)(.*?)([\"'’”]*)$", w)
    lead, core, tail = m.group(1), m.group(2), m.group(3)
    if not core:
        return w
    low = core.lower()
    if low.startswith("mc") and len(core) > 2:
        out = "Mc" + core[2].upper() + low[3:]
    elif re.match(r"^o['’]\w", low):
        out = "O" + core[1] + core[2].upper() + low[3:]
    else:
        out = core[0].upper() + low[1:]
    return lead + out + tail


def display_name(text):
    """The name as the card prints it: kept as printed unless the page prints
    it in capitals, which are re-cased word by word."""
    s = re.sub(r"\s+", " ", text.strip()).rstrip(",")
    core, sfx = split_suffix(s)
    if any(c.islower() for c in core):
        return s
    out = " ".join(_case_word(w) for w in core.split(" "))
    if sfx:
        low = sfx.lower().rstrip(".")
        sfx_out = {"jr": "Jr.", "sr": "Sr."}.get(low, sfx.upper())
        out += ", " + sfx_out
    return out


def name_key(text):
    """A comparison key: letters only, lower case, suffix and quotes dropped."""
    core, _ = split_suffix(text.strip())
    s = unicodedata.normalize("NFKD", core)
    s = re.sub(r"[^A-Za-z ]", "", s).lower()
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------
def member_anchors(lines, shape):
    """Every (seat, first line, last line, raw text) the page offers in its
    declared shape, in page order: the lines are where the seat and the name
    are printed, so a person's own entry is what follows them."""
    out = []
    if shape == "name, seat":
        for i, ln in enumerate(lines):
            m = NAME_COMMA_SEAT.match(ln)
            if m:
                out.append((seat_of(m.group("seat")), i, i, m.group("name")))
    elif shape == "seat - name":
        for i, ln in enumerate(lines):
            m = SEAT_DASH_NAME.match(ln)
            if m:
                out.append((seat_of(m.group("seat")), i, i, m.group("name")))
    elif shape in ("name / seat", "seat / name"):
        step = -1 if shape == "name / seat" else 1
        for i, ln in enumerate(lines):
            seat = seat_of(ln)
            if not seat:
                continue
            j = i + step
            while 0 <= j < len(lines) and SEPARATOR.match(lines[j]):
                j += step
            if 0 <= j < len(lines):
                out.append((seat, min(i, j), max(i, j), lines[j]))
    else:
        raise ValueError("unknown shape %r" % shape)
    return [a for a in out if a[0]]


def member_readings(lines, shape):
    """Every (seat, raw text) pair the page offers in its declared shape."""
    return [(seat, raw) for seat, _, _, raw in member_anchors(lines, shape)]


def printed_seats(lines):
    """Every seat a page prints a label for, in any of the four shapes. The
    monthly source check reads Greenville's page with it, to see the day it
    starts naming its council: measured 2026-10-17 on the pages read the day
    before, Greenville's printed no seat label at all and each of the other
    fourteen cities' pages printed every one of its seats."""
    found = set()
    for ln in lines:
        for rx in (NAME_COMMA_SEAT, SEAT_DASH_NAME):
            m = rx.match(ln)
            if m and seat_of(m.group("seat")):
                found.add(seat_of(m.group("seat")))
        if seat_of(ln):
            found.add(seat_of(ln))
    return sorted(found)


def mayor_anchors(lines, how, pattern):
    """Every (first line, last line, raw text) where the mayor's pattern
    matches, in page order."""
    rx = re.compile(pattern, re.I)
    out = []
    for i, ln in enumerate(lines):
        m = rx.match(ln)
        if not m:
            continue
        if how == "line":
            out.append((i, i, m.group("name")))
        else:
            step = -1 if how == "before" else 1
            j = i + step
            while 0 <= j < len(lines) and SEPARATOR.match(lines[j]):
                j += step
            if 0 <= j < len(lines):
                out.append((min(i, j), max(i, j), lines[j]))
    return out


def mayor_readings(lines, how, pattern):
    return [raw for _, _, raw in mayor_anchors(lines, how, pattern)]


def settle(city, seat, readings):
    """One name, or VACANT, from every reading of one seat; raises otherwise."""
    names = {}
    vacant = False
    for raw in readings:
        if is_vacant(raw):
            vacant = True
            continue
        if name_problem(raw):
            continue
        names.setdefault(name_key(raw), raw)
    if vacant and not names:
        return None
    if vacant and names:
        raise SystemExit("%s %s: the page shows the seat both vacant and held" % (city, seat))
    if not names:
        raise SystemExit("%s %s: no reading of this seat looks like a name" % (city, seat))
    if len(names) > 1:
        raise SystemExit("%s %s: the page names %d different people for this seat"
                         % (city, seat, len(names)))
    return display_name(next(iter(names.values())))


# ---------------------------------------------------------------------------
# Telephones
# ---------------------------------------------------------------------------
# A North American number as these pages print it: 662-555-0100,
# (662) 555-0100, 601.555.0100.
NUMBER = r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]\d{4}"
NUMBER_RE = re.compile(r"(?<!\d)" + NUMBER + r"(?!\d)")
# A line that is a number and nothing else, after a label or not.
PHONE_LINE = re.compile(r"^(?:(?P<label>[A-Za-z][A-Za-z ]{0,19}?)\s*:\s*)?(?P<number>"
                        + NUMBER + r")$")
# A label on a line of its own, its number on the next line.
LABEL_LINE = re.compile(r"^(?P<label>[A-Za-z][A-Za-z ]{0,19}?)\s*:$")
# Something a reader could take for a telephone number: seven digits with a
# separator, which a line PHONE_LINE does not read must not hold.
LOOSE_NUMBER = re.compile(r"\d{3}[\s.\-]\d{4}")
# A page's own label for a number: the word the card prints in front of it, or
# None for a label that says only that it is a telephone. A label not here
# stops the build, so a new one is read by a person first.
PHONE_LABELS = {"phone": None, "telephone": None, "tel": None,
                "home": "home", "work": "work", "cell": "cell", "mobile": "mobile",
                "office": "office", "business": "business"}
# A fax number is read past and never carried.
FAX_LABELS = {"fax"}
# How a carried number is written: the label word, if any, and the number.
OWN_PHONE = re.compile(r"^(?:(?:%s) )?%s$" % (
    "|".join(sorted(set(w for w in PHONE_LABELS.values() if w))), NUMBER))


def digits(text):
    return re.sub(r"\D", "", text)


def entry_numbers(city, seat, block):
    """The numbers printed in one person's entry, in page order, each written
    as the card prints it: the page's label in front where it says which line
    the number is, then the number as printed. Raises on a line holding what
    looks like a number in a form this reader does not read, or on a label it
    does not know; the message names the city and the seat, never the line."""
    out = []
    i = 0
    while i < len(block):
        ln = block[i]
        label = number = None
        m = PHONE_LINE.match(ln)
        lm = LABEL_LINE.match(ln)
        if m:
            label, number = m.group("label"), m.group("number")
            i += 1
        elif lm and i + 1 < len(block) and PHONE_LINE.match(block[i + 1]) \
                and not PHONE_LINE.match(block[i + 1]).group("label"):
            label, number = lm.group("label"), PHONE_LINE.match(block[i + 1]).group("number")
            i += 2
        else:
            if LOOSE_NUMBER.search(ln):
                raise SystemExit("%s %s: a line in this person's entry holds a number in "
                                 "a form this reader does not read" % (city, seat))
            i += 1
            continue
        key = label.strip().lower() if label else "phone"
        if key in FAX_LABELS:
            continue
        if key not in PHONE_LABELS:
            raise SystemExit("%s %s: a number in this person's entry carries a label "
                             "this reader does not know" % (city, seat))
        word = PHONE_LABELS[key]
        number = re.sub(r"\s+", " ", number.strip())
        out.append(word + " " + number if word else number)
    return out


def entry_windows(c, lines, by_name):
    """[(seat, key, first, last, stop)], in page order, for every named person
    the council page prints: `first` and `last` are the lines that print their
    seat and name, and their entry runs from `first` up to `stop`, the next
    person's first line or, for the last person, the line the city's `end`
    matches. The mayor has an entry only where the city reads its mayor from
    the council page. `by_name` maps each named person's key to their seat.
    Raises when the page prints one person twice, since whose entry is whose
    could not then be read, or when the end is not found."""
    anchors = []
    for seat, first, last, raw in member_anchors(lines, c["members"]):
        if not name_problem(raw) and name_key(raw) in by_name:
            anchors.append((first, last, seat, name_key(raw)))
    page, how, pattern = c["mayor"]
    if page == "council":
        for first, last, raw in mayor_anchors(lines, how, pattern):
            if not name_problem(raw) and name_key(raw) in by_name:
                anchors.append((first, last, "Mayor", name_key(raw)))
    anchors.sort()
    seen = set()
    for first, last, seat, key in anchors:
        if key in seen:
            raise SystemExit("%s %s: the page prints this person twice, so whose entry is "
                             "whose cannot be read" % (c["name"], seat))
        seen.add(key)
    out = []
    for k, (first, last, seat, key) in enumerate(anchors):
        if k + 1 < len(anchors):
            stop = anchors[k + 1][0]
        else:
            stop = next((j for j in range(last + 1, len(lines))
                         if re.match(c["end"], lines[j], re.I)), None)
            if stop is None:
                raise SystemExit("%s: the line that ends its list of members is not found"
                                 % c["name"])
        out.append((seat, key, first, last, stop))
    return out


def read_phones(c, lines, mayor_lines, windows, say=None):
    """{name key: [numbers]} for the people of a city that declares `phones`.

    A person's numbers are the ones printed in their entry after the lines
    that print their seat and name (entry_windows). A number is carried only
    when it is printed once on the pages read (the council page and, where it
    is read, the mayor's): a number printed for two people, or anywhere else
    on them, is the office's."""
    printed = {}
    for ln in lines + (mayor_lines or []):
        for m in NUMBER_RE.finditer(ln):
            printed[digits(m.group(0))] = printed.get(digits(m.group(0)), 0) + 1
    out, offices = {}, 0
    for seat, key, first, last, stop in windows:
        numbers = entry_numbers(c["name"], seat, lines[last + 1:stop])
        own = [n for n in numbers if printed.get(digits(n)) == 1]
        offices += len(numbers) - len(own)
        if own:
            out[key] = own
    if len(out) < c["phones"]:
        raise SystemExit("%s: %d of its named people carry a number of their own, fewer "
                         "than the %d its page gave when measured"
                         % (c["name"], len(out), c["phones"]))
    if say:
        say("%-13s %d people carry %d numbers of their own; %d more numbers printed in an "
            "entry are printed elsewhere on the pages too, so are the office's"
            % (c["name"], len(out), sum(len(v) for v in out.values()), offices))
    return out


def own_address(c, seat, inside, count):
    """The one address of a person's own among the marks `inside` their entry
    or card, or None. An address is theirs when every place the pages read
    print it (`count`, by lower-case address) is inside, and its mailbox is not
    an office's; it is carried as the page first prints it there, a link
    before text on the same line. Raises on a link that opens no address
    this reader reads, and on two addresses of the person's own, since the
    card shows one; the message names the city and the seat, never the
    address. Returns (address, how many addresses inside were the office's)."""
    found = {}
    for line, address, texted, card in sorted(inside, key=lambda m: (m[0], not m[2])):
        if not OWN_EMAIL.match(address):
            raise SystemExit("%s %s: a link in this person's entry opens an address this "
                             "reader does not read" % (c["name"], seat))
        found.setdefault(address.lower(), []).append(address)
    own = [forms[0] for low, forms in found.items()
           if count.get(low) == len(forms) and not office_mailbox(low)]
    if len(own) > 1:
        raise SystemExit("%s %s: the page prints two addresses of this person's own, and "
                         "the card shows one" % (c["name"], seat))
    return (own[0] if own else None), len(found) - len(own)


def address_count(marks, mayor_marks):
    count = {}
    for m in list(marks) + list(mayor_marks):
        count[m[1].lower()] = count.get(m[1].lower(), 0) + 1
    return count


def read_emails(c, marks, hidden, mayor_marks, windows, say=None):
    """{name key: address} for a city that declares `emails` and an `end`: a
    person's address is in their entry (entry_windows), from the lines that
    print their seat and name, which may be a link themselves, up to the
    next person's. An address printed for two people, or anywhere else on
    the pages read, is the office's. Raises where the page hides an address
    among its members behind a script. A link with no text of its own (an
    icon, or Gulfport's empty link beside one member's address) is read
    only where the entry it falls in also prints its address with text,
    since which entry an icon belongs to cannot be read from the page's
    lines; otherwise it stops the build."""
    if not windows:
        raise SystemExit("%s: no member's entry is found" % c["name"])
    top, bottom = windows[0][2], windows[-1][4]
    if any(top <= line <= bottom for line in hidden):
        raise SystemExit("%s: the page hides an address among its members behind a script, "
                         "which this reader does not undo" % c["name"])
    for line, address, texted, _ in marks:
        if texted or not top <= line <= bottom:
            continue
        w = next((w for w in windows if w[2] <= line < w[4]), None)
        if not w or not any(t and w[2] <= ln < w[4] and a.lower() == address.lower()
                            for ln, a, t, _ in marks):
            raise SystemExit("%s: the page links an address among its members with no text "
                             "of its own, so whose it is cannot be read" % c["name"])
    count = address_count(marks, mayor_marks)
    out, offices = {}, 0
    for seat, key, first, last, stop in windows:
        own, office = own_address(c, seat, [m for m in marks if first <= m[0] < stop], count)
        offices += office
        if own:
            out[key] = own
    return emails_floor(c, out, offices, say)


def read_card_emails(c, lines, marks, cards, hidden, mayor_marks, by_seat, say=None):
    """{name key: address} for a city that declares `cards`: each member's
    address is in a card of its own. A card is a member's when it prints one
    seat line, and the name on its lines above that is the name the page
    gives that seat; a card printing no seat line is read past, and one
    printing two, or another person's name, stops the build. An address is
    the member's own when every place the pages read print it is inside
    their card. `by_seat` maps each named seat to its person's key."""
    seat_rx = c["cards"][1]
    count = address_count(marks, mayor_marks)
    out, seen, offices = {}, set(), 0
    for k, (first, stop) in enumerate(cards):
        body = lines[first:stop]
        hits = [(i, m) for i, m in ((i, re.match(seat_rx, ln, re.I)) for i, ln in enumerate(body))
                if m]
        if not hits:
            continue
        if len(hits) > 1:
            raise SystemExit("%s: a card on the page prints two seats" % c["name"])
        i, m = hits[0]
        seat = "Ward %d" % int(m.group("ward"))
        if seat not in by_seat:
            raise SystemExit("%s %s: a card prints a seat the page names nobody for"
                             % (c["name"], seat))
        if seat in seen:
            raise SystemExit("%s %s: two cards print this seat" % (c["name"], seat))
        seen.add(seat)
        if name_key(" ".join(body[:i])) != by_seat[seat]:
            raise SystemExit("%s %s: the card for this seat names someone other than the "
                             "person the page names for it" % (c["name"], seat))
        if any(first <= line < stop for line in hidden):
            raise SystemExit("%s %s: the card hides this person's address behind a script, "
                             "which this reader does not undo" % (c["name"], seat))
        own, office = own_address(c, seat, [mk for mk in marks if mk[3] == k], count)
        offices += office
        if own:
            out[by_seat[seat]] = own
    return emails_floor(c, out, offices, say)


def emails_floor(c, out, offices, say):
    if len(out) < c["emails"]:
        raise SystemExit("%s: %d of its named people carry an address of their own, fewer "
                         "than the %d its page gave when measured"
                         % (c["name"], len(out), c["emails"]))
    if say:
        say("%-13s %d people carry an address of their own; %d more addresses printed in an "
            "entry are printed elsewhere on the pages too, or are an office's mailbox, so are "
            "the office's" % (c["name"], len(out), offices))
    return out


def expected_seats(c):
    seats = ["Ward %d" % n for n in range(1, c["wards"] + 1)]
    if c["at_large"]:
        seats = ["At Large"] + seats
    return seats


def read_city(c, council_html, mayor_html, read_date, say=None):
    """The city's record from its pages; raises on any gate."""
    rec = {"name": c["name"], "body": c["body"], "councilUrl": c["council"]}
    if c.get("mayor_page"):
        rec["mayorUrl"] = c["mayor_page"]
    if c["geoid"] in NOT_PUBLISHED:
        np = NOT_PUBLISHED[c["geoid"]]
        rec["read"] = np["measured"]
        rec["unnamed"] = np["why"]
        return rec
    rec["read"] = read_date
    rec["seats"] = []
    lines, marks, cards, hidden = page_text(council_html, (c.get("cards") or (None,))[0])
    by_seat = {}
    for seat, raw in member_readings(lines, c["members"]):
        by_seat.setdefault(seat, []).append(raw)
    want = expected_seats(c)
    extra = sorted(set(by_seat) - set(want))
    if extra:
        raise SystemExit("%s: the page prints seats the city does not declare: %s"
                         % (c["name"], ", ".join(extra)))
    page, how, pattern = c["mayor"]
    mlines = page_lines(mayor_html) if page == "mayor" else lines
    mayor = settle(c["name"], "Mayor", mayor_readings(mlines, how, pattern))
    rec["seats"].append({"seat": "Mayor", "name": mayor} if mayor
                        else {"seat": "Mayor", "vacant": True})
    for seat in want:
        if seat not in by_seat:
            raise SystemExit("%s %s: the page does not print this seat" % (c["name"], seat))
        name = settle(c["name"], seat, by_seat[seat])
        rec["seats"].append({"seat": seat, "name": name} if name
                            else {"seat": seat, "vacant": True})
    keys = [name_key(s["name"]) for s in rec["seats"] if s.get("name")]
    if len(keys) != len(set(keys)):
        raise SystemExit("%s: one name is carried for two seats" % c["name"])
    if "phones" in c or "emails" in c:
        mlines, mmarks = page_text(mayor_html)[:2] if mayor_html else ([], [])
        named = [s for s in rec["seats"] if s.get("name")]
        numbers, addresses = {}, {}
        if "cards" in c:
            addresses = read_card_emails(c, lines, marks, cards, hidden, mmarks,
                                         {s["seat"]: name_key(s["name"]) for s in named}, say)
        else:
            windows = entry_windows(c, lines, {name_key(s["name"]): s["seat"] for s in named})
            if "phones" in c:
                numbers = read_phones(c, lines, mlines, windows, say)
            if "emails" in c:
                addresses = read_emails(c, marks, hidden, mmarks, windows, say)
        for s in named:
            own = numbers.get(name_key(s["name"]))
            if own:
                s["phone"] = own[0]
                if len(own) > 1:
                    s["phonesExtra"] = own[1:]
            if addresses.get(name_key(s["name"])):
                s["email"] = addresses[name_key(s["name"])]
    return rec


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
class Fetcher(object):
    def __init__(self):
        self.gate = RobotsGate(None, USER_AGENT, headers=HEADERS)
        self.last = {}
        self.said = set()

    def get(self, url):
        host = urllib.parse.urlsplit(url).hostname or ""
        ok, why = self.gate.allows(url)
        if host not in self.said:
            print("robots.txt %s: %s" % (host, why), file=sys.stderr)
            self.said.add(host)
        if not ok:
            raise SystemExit("%s refuses this client (%s); nothing is fetched from it"
                             % (url, why))
        delay = max(MIN_DELAY_S, self.gate.crawl_delay(url) or 0)
        wait = self.last.get(host, 0) + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
        finally:
            self.last[host] = time.time()
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return body.decode("utf-8", "replace")


def census_places(fetcher):
    """{geoid: name} of every Mississippi place the 2020 census counts at
    POPULATION_FLOOR or more."""
    url = CENSUS_PLACES + "?" + urllib.parse.urlencode({
        "where": "STATE='28' AND POP100>=%d" % POPULATION_FLOOR,
        "outFields": "GEOID,BASENAME,POP100", "returnGeometry": "false", "f": "json"})
    data = json.loads(fetcher.get(url))
    if "error" in data:
        raise SystemExit("the Census place layer answered an error: %s" % data["error"])
    return {f["attributes"]["GEOID"]: f["attributes"]["BASENAME"] for f in data["features"]}


def slug(name):
    return name.lower().replace(" ", "-")


def build(pages_dir=None, save_dir=None, read_date=None):
    fetcher = None if pages_dir else Fetcher()
    if fetcher:
        found = census_places(fetcher)
        mine = {c["geoid"]: c["name"] for c in CITIES}
        if found != mine:
            raise SystemExit("the 2020 census's places of %d or more are not CITIES: "
                             "missing %s, extra %s" % (
                                 POPULATION_FLOOR,
                                 sorted(set(found) - set(mine)),
                                 sorted(set(mine) - set(found))))
        print("census: the %d places of %d or more are exactly CITIES"
              % (len(found), POPULATION_FLOOR), file=sys.stderr)
    out = {}
    for c in CITIES:
        council = mayor = ""
        if c["geoid"] not in NOT_PUBLISHED:
            urls = {"council": c["council"]}
            if c["mayor"][0] == "mayor":
                urls["mayor"] = c["mayor_page"]
            texts = {}
            for kind, url in urls.items():
                path = os.path.join(pages_dir or save_dir or "", "%s-%s.htm" % (slug(c["name"]), kind))
                if pages_dir:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        texts[kind] = fh.read()
                else:
                    texts[kind] = fetcher.get(url)
                    if save_dir:
                        with open(path, "w", encoding="utf-8") as fh:
                            fh.write(texts[kind])
            council, mayor = texts["council"], texts.get("mayor", "")
        rec = read_city(c, council, mayor, read_date or date.today().isoformat(),
                        say=lambda line: print(line, file=sys.stderr))
        out[c["geoid"]] = rec
        if "seats" not in rec:
            print("%-13s %-17s names nobody (NOT_PUBLISHED)" % (c["name"], c["body"]),
                  file=sys.stderr)
            continue
        named = sum(1 for s in rec["seats"] if s.get("name"))
        print("%-13s %-17s %d of %d seats named" % (
            c["name"], c["body"], named, 1 + len(expected_seats(c))), file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# The offline gate
# ---------------------------------------------------------------------------
def check(path=OUT):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    problems, addresses = [], []
    if sorted(data) != sorted(c["geoid"] for c in CITIES):
        problems.append("the file's cities are not CITIES")
    for c in CITIES:
        rec = data.get(c["geoid"])
        if not rec:
            continue
        if rec.get("name") != c["name"] or rec.get("body") != c["body"]:
            problems.append("%s: name or body differs from CITIES" % c["name"])
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(rec.get("read", ""))):
            problems.append("%s: no read date" % c["name"])
        if c["geoid"] in NOT_PUBLISHED:
            # A city whose site names nobody carries the reason and no seats.
            allowed_rec = {"name", "body", "councilUrl", "mayorUrl", "read", "unnamed"}
            if set(rec) - allowed_rec:
                problems.append("%s: carries %s" % (c["name"], sorted(set(rec) - allowed_rec)))
            if rec.get("unnamed") != NOT_PUBLISHED[c["geoid"]]["why"] or \
                    rec.get("read") != NOT_PUBLISHED[c["geoid"]]["measured"]:
                problems.append("%s: not published, yet the record differs" % c["name"])
            continue
        seats = [s.get("seat") for s in rec.get("seats", [])]
        if seats != ["Mayor"] + expected_seats(c):
            problems.append("%s: seats %s, not the declared %s"
                            % (c["name"], seats, ["Mayor"] + expected_seats(c)))
        keys, carried, with_numbers, with_addresses = [], [], 0, 0
        for s in rec.get("seats", []):
            allowed = {"seat", "name", "phone", "phonesExtra", "email"} if s.get("name") \
                else {"seat", "vacant"}
            if set(s) - allowed:
                problems.append("%s %s: carries %s" % (c["name"], s.get("seat"),
                                                       sorted(set(s) - allowed)))
            if s.get("name"):
                why = name_problem(s["name"])
                if why:
                    problems.append("%s %s: not a name (%s)" % (c["name"], s["seat"], why))
                keys.append(name_key(s["name"]))
            elif s.get("vacant") is not True:
                problems.append("%s %s: neither named nor vacant" % (c["name"], s.get("seat")))
            # A person's address and numbers: the problem names the city and
            # the seat, never the address or the number.
            if "email" in s:
                if "emails" not in c:
                    problems.append("%s %s: carries an address, and this city's page is not "
                                    "read for addresses" % (c["name"], s.get("seat")))
                if not isinstance(s["email"], str) or not OWN_EMAIL.match(s["email"]):
                    problems.append("%s %s: an address not written as one (not printed)"
                                    % (c["name"], s.get("seat")))
                elif office_mailbox(s["email"]):
                    problems.append("%s %s: an office's mailbox is carried as a person's own"
                                    % (c["name"], s.get("seat")))
                else:
                    addresses.append(s["email"].lower())
                with_addresses += 1
            if "phonesExtra" in s and "phone" not in s:
                problems.append("%s %s: a second number with no first" % (c["name"], s.get("seat")))
            if "phone" not in s:
                continue
            numbers = [s["phone"]] + (s["phonesExtra"] if isinstance(s.get("phonesExtra"), list)
                                      else [None] if "phonesExtra" in s else [])
            if "phonesExtra" in s and len(numbers) < 2:
                problems.append("%s %s: an empty list of second numbers" % (c["name"], s.get("seat")))
            if "phones" not in c:
                problems.append("%s %s: carries a number, and this city's page is not read "
                                "for numbers" % (c["name"], s.get("seat")))
            for n in numbers:
                if not isinstance(n, str) or not OWN_PHONE.match(n):
                    problems.append("%s %s: a number not written as a label word and a "
                                    "number (not printed)" % (c["name"], s.get("seat")))
                else:
                    carried.append(digits(n))
            with_numbers += 1
        if len(keys) != len(set(keys)):
            problems.append("%s: one name for two seats" % c["name"])
        if len(carried) != len(set(carried)):
            problems.append("%s: one number is carried twice, so it is the office's" % c["name"])
        if "phones" in c and with_numbers < c["phones"]:
            problems.append("%s: %d named people carry a number of their own, fewer than %d"
                            % (c["name"], with_numbers, c["phones"]))
        if "emails" in c and with_addresses < c["emails"]:
            problems.append("%s: %d named people carry an address of their own, fewer than %d"
                            % (c["name"], with_addresses, c["emails"]))
        allowed_rec = {"name", "body", "seats", "councilUrl", "mayorUrl", "read"}
        if set(rec) - allowed_rec:
            problems.append("%s: carries %s" % (c["name"], sorted(set(rec) - allowed_rec)))
    if len(addresses) != len(set(addresses)):
        problems.append("one address is carried for two people, so it is the office's")
    if problems:
        for p in problems:
            print("FAIL " + p)
        return 1
    seats = [s for r in data.values() for s in r.get("seats", [])]
    named = sum(1 for s in seats if s.get("name"))
    phoned = [s for s in seats if s.get("phone")]

    def cities_with(field):
        return sum(1 for r in data.values() if any(s.get(field) for s in r.get("seats", [])))
    print("OK ms-city-councils.json: %d cities, %d people named, %d of them with a number of "
          "their own in %d cities (%d numbers), %d with an address of their own in %d cities, "
          "%d city names nobody"
          % (len(data), named, len(phoned), cities_with("phone"),
             sum(1 + len(s.get("phonesExtra", [])) for s in phoned),
             len(addresses), cities_with("email"),
             sum(1 for r in data.values() if not r.get("seats"))))
    return 0


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest():
    fails = []

    def ok(label, got, want):
        if got != want:
            fails.append("%s: got %r, want %r" % (label, got, want))

    for text, want in [("Ward 3", "Ward 3"), ("WARD 7", "Ward 7"), ("Ward III", "Ward 3"),
                       ("Alderman Ward 2", "Ward 2"), ("Alderman-at-Large", "At Large"),
                       ("Alderman-At-Large", "At Large"), ("At Large", "At Large"),
                       (", Ward I", "Ward 1"), ("Pro-Tem, Ward VI", "Ward 6"),
                       (", Alderman At-Large", "At Large"), ("Alderman at Large", "At Large"),
                       ("Ward 1 Councilman", None), ("Ward Maps", None),
                       ("an advocate for the prosperity of Ward 2", None)]:
        ok("seat_of %r" % text, seat_of(text), want)
    for text, want in [("F.B. ‘RUSTY’ WALKER, IV", "F.B. ‘Rusty’ Walker, IV"),
                       ("B.J. SELLERS, JR.", "B.J. Sellers, Jr."),
                       ("ELLA HOLMES-HINES", "Ella Holmes-Hines"),
                       ("LARRY MCKINNEY", "Larry McKinney"), ("PAT O'BRIEN", "Pat O'Brien"),
                       ("TJ McSparrin", "TJ McSparrin"), ("Andrew “FoFo” Gilich",
                                                          "Andrew “FoFo” Gilich")]:
        ok("display_name %r" % text, display_name(text), want)
    for text, bad in [("Ashby M. Foote", False), ("Andrew “FoFo” Gilich", False),
                      ("F.B. ‘RUSTY’ WALKER, IV", False), ("Mary Hawkins Butler", False),
                      ("John Horhn's New Initiatives", True), ("Office", True), ("CAO", True),
                      ("City Council", True), ("Send Email", True), ("601-555-0100", True),
                      ("Todd Jordan is a lifelong resident of Tupelo. He is", True),
                      ("someone@city.gov", True), ("Ward Maps", True)]:
        ok("name_problem %r" % text, name_problem(text) is not None, bad)

    def html(lines):
        return "<html><body>" + "".join("<p>%s</p>" % ln for ln in lines) + "</body></html>"

    c = {"geoid": "1", "name": "Testville", "body": "Board of Aldermen", "wards": 2,
         "at_large": 1, "council": "https://example.invalid/", "mayor_page": None,
         "members": "seat / name", "mayor": ("council", "after", r"^Mayor$")}
    page = html(["Mayor", "Pat Doe", "Alderman at Large", "-", "Lee Roe",
                 "Ward 1", "Kim Poe", "Ward 2", "Vacant", "Ward 1", "Kim Poe"])
    rec = read_city(c, page, "", "2026-10-17")
    ok("seat / name record", rec["seats"],
       [{"seat": "Mayor", "name": "Pat Doe"}, {"seat": "At Large", "name": "Lee Roe"},
        {"seat": "Ward 1", "name": "Kim Poe"}, {"seat": "Ward 2", "vacant": True}])
    c2 = dict(c, members="name / seat", mayor=("council", "before", r"^,?\s*Mayor$"))
    rec = read_city(c2, html(["Pat Doe", ", Mayor", "Lee Roe", "Alderman-At-Large",
                              "Kim Poe", "Ward I", "Jo Moe", "Pro-Tem, Ward II"]),
                    "", "2026-10-17")
    ok("name / seat names", [s.get("name") for s in rec["seats"]],
       ["Pat Doe", "Lee Roe", "Kim Poe", "Jo Moe"])
    c3 = dict(c, at_large=0, members="name, seat", mayor=("council", "line", r"^Mayor (?P<name>.+)$"))
    rec = read_city(c3, html(["Mayor Pat Doe", "Mayor Doe's Initiatives",
                              "Kim Poe, Ward 1", "Jo Moe, Ward 2"]), "", "2026-10-17")
    ok("name, seat names", [s.get("name") for s in rec["seats"]], ["Pat Doe", "Kim Poe", "Jo Moe"])
    c4 = dict(c3, members="seat - name")
    rec = read_city(c4, html(["Mayor Pat Doe", "Ward 1 – Kim Poe", "Ward 2 – Jo Moe",
                              "Kim", "Poe", "Ward 1 Councilman"]), "", "2026-10-17")
    ok("seat - name names", [s.get("name") for s in rec["seats"]], ["Pat Doe", "Kim Poe", "Jo Moe"])
    ok("printed_seats", printed_seats(page_lines(html(
        ["Mayor", "Kim Poe, Ward 1", "Ward 2 – Jo Moe", "Alderman at Large", "Lee Roe",
         "Ward 1 Councilman", "City Clerk", "Ward Maps"]))), ["At Large", "Ward 1", "Ward 2"])
    ok("printed_seats on a page naming no seat", printed_seats(page_lines(html(
        ["City Clerk", "Ward Maps", "an advocate for the prosperity of Ward 2"]))), [])
    for label, lines in [
            ("two people for one seat", ["Mayor Pat Doe", "Kim Poe, Ward 1", "Jo Moe, Ward 2",
                                         "Al Foe, Ward 1"]),
            ("a missing seat", ["Mayor Pat Doe", "Kim Poe, Ward 1"]),
            ("an undeclared seat", ["Mayor Pat Doe", "Kim Poe, Ward 1", "Jo Moe, Ward 2",
                                    "Al Foe, Ward 3"]),
            ("one name for two seats", ["Mayor Pat Doe", "Kim Poe, Ward 1", "Kim Poe, Ward 2"]),
            ("no mayor", ["Kim Poe, Ward 1", "Jo Moe, Ward 2"])]:
        try:
            read_city(c3, html(lines), "", "2026-10-17")
            fails.append("%s: was not refused" % label)
        except SystemExit:
            pass
    # Telephones: a label that says which line goes in front, one that says
    # only "phone" does not, a fax is read past, and a number printed again
    # elsewhere on the pages (here City Hall's, in the footer) is the office's.
    cp = dict(c2, end=r"^City Hall$", phones=3)
    phone_page = html(["Pat Doe", ", Mayor", "Phone:", "601-555-0100",
                       "Lee Roe", "Alderman-At-Large", "lee@example.invalid", "Home: 601-555-0101",
                       "Kim Poe", "Ward I", "1 Main Street", "Testville, Mississippi 39000",
                       "Work: (601) 555-0102", "Cell: 601.555.0103", "Fax: 601-555-0199",
                       "Jo Moe", "Pro-Tem, Ward II", "Tel:", "601-555-0104",
                       "City Hall", "601-555-0104"])
    cp_mayor = dict(cp, mayor=("council", "before", r"^,?\s*Mayor$"))
    rec = read_city(cp_mayor, phone_page, "", "2026-10-17")
    ok("numbers on each person", [(s["seat"], s.get("phone"), s.get("phonesExtra"))
                                  for s in rec["seats"]],
       [("Mayor", "601-555-0100", None), ("At Large", "home 601-555-0101", None),
        ("Ward 1", "work (601) 555-0102", ["cell 601.555.0103"]), ("Ward 2", None, None)])
    # The mayor read from a separate page has no entry on the council page,
    # and a number printed there as well is not carried.
    rec = read_city(dict(cp, mayor=("mayor", "line", r"^Mayor (?P<name>.+)$"), phones=2),
                    html(["Lee Roe", "Alderman-At-Large", "Home: 601-555-0101",
                          "Kim Poe", "Ward I", "Cell: 601-555-0103",
                          "Jo Moe", "Ward II", "Home: 601-555-0105", "City Hall"]),
                    html(["Mayor Pat Doe", "601-555-0105"]), "2026-10-17")
    ok("a number the mayor's page prints too", [(s["seat"], s.get("phone")) for s in rec["seats"]],
       [("Mayor", None), ("At Large", "home 601-555-0101"), ("Ward 1", "cell 601-555-0103"),
        ("Ward 2", None)])
    for label, lines, spec in [
            ("a number in a form not read", ["Pat Doe", ", Mayor", "Lee Roe", "Alderman-At-Large",
                                             "Call 555-0101 any time", "Kim Poe", "Ward I",
                                             "Jo Moe", "Ward II", "City Hall"], 0),
            ("a label not known", ["Pat Doe", ", Mayor", "Lee Roe", "Alderman-At-Large",
                                   "Pager: 601-555-0101", "Kim Poe", "Ward I",
                                   "Jo Moe", "Ward II", "City Hall"], 0),
            ("no line that ends the list", ["Pat Doe", ", Mayor", "Lee Roe", "Alderman-At-Large",
                                            "Kim Poe", "Ward I", "Jo Moe", "Ward II"], 0),
            ("fewer people with a number than the floor",
             ["Pat Doe", ", Mayor", "Lee Roe", "Alderman-At-Large", "Home: 601-555-0101",
              "Kim Poe", "Ward I", "Jo Moe", "Ward II", "City Hall"], 2),
            ("one person printed twice", ["Pat Doe", ", Mayor", "Lee Roe", "Alderman-At-Large",
                                          "Kim Poe", "Ward I", "Jo Moe", "Ward II",
                                          "Kim Poe", "Ward I", "City Hall"], 0)]:
        try:
            read_city(dict(cp_mayor, phones=spec), html(lines), "", "2026-10-17")
            fails.append("%s: was not refused" % label)
        except SystemExit as e:
            if re.search(r"\d{3}[\s.\-]\d{4}|Main Street", str(e)):
                fails.append("%s: the message prints a number or an address" % label)
    ok("OWN_PHONE", [bool(OWN_PHONE.match(t)) for t in
                     ["601-555-0100", "home (601) 555-0100", "cell 601.555.0100",
                      "pager 601-555-0100", "Home 601-555-0100", "601-555-0100 ext. 4", "555-0100"]],
       [True, True, True, False, False, False, False])
    # Addresses, read by entry: a link, a linked name and an address printed as
    # text are each a person's own when nothing else on the pages prints them;
    # one printed for two people, after the list or on the mayor's page is the
    # office's, and so is an office's mailbox wherever it is printed.
    def mail(addr, text=None):
        return "<a href='mailto:%s'>%s</a>" % (addr, addr if text is None else text)
    ce = dict(cp_mayor, phones=0, emails=3)
    mail_page = html(["Staff: " + mail("clerk@example.invalid"),
                      "Pat Doe", ", Mayor", mail("Pat.Doe@Example.invalid?subject=Hello", "Email"),
                      "Lee Roe", "Alderman-At-Large", "lee@example.invalid",
                      mail("board@example.invalid", "The board"),
                      mail("kim@example.invalid", "Kim Poe"), "Ward I",
                      mail("kim@example.invalid"), mail("shared@example.invalid", "Email"),
                      "Jo Moe", "Pro-Tem, Ward II", mail("jo@example.invalid", "Email"),
                      mail("shared@example.invalid", "Email"),
                      "City Hall", "jo@example.invalid"])
    rec = read_city(ce, mail_page.replace(
        "<p>lee@example.invalid</p>", "<p><a href='mailto:lee@example.invalid'></a></p>"
        "<p>lee@example.invalid</p>"), "", "2026-10-17")
    ok("addresses on each person", [(s["seat"], s.get("email")) for s in rec["seats"]],
       [("Mayor", "Pat.Doe@Example.invalid"), ("At Large", "lee@example.invalid"),
        ("Ward 1", "kim@example.invalid"), ("Ward 2", None)])
    rec = read_city(dict(ce, mayor=("mayor", "line", r"^Mayor (?P<name>.+)$"), emails=1),
                    html(["Lee Roe", "Alderman-At-Large", mail("lee@example.invalid"),
                          "Kim Poe", "Ward I", mail("kim@example.invalid", "Email"),
                          "Jo Moe", "Ward II", "City Hall"]),
                    html(["Mayor Pat Doe", "Write to " + mail("lee@example.invalid")]), "2026-10-17")
    ok("an address the mayor's page prints too", [(s["seat"], s.get("email")) for s in rec["seats"]],
       [("Mayor", None), ("At Large", None), ("Ward 1", "kim@example.invalid"), ("Ward 2", None)])
    entries = ["Pat Doe", ", Mayor", "Lee Roe", "Alderman-At-Large", "Kim Poe", "Ward I",
               "Jo Moe", "Ward II", "City Hall"]
    for label, insert, floor, why in [
            ("two addresses of one person's own", [mail("lee@example.invalid"),
                                                   mail("lee.roe@example.invalid")], 0,
             "two addresses of this person's own"),
            ("a link that opens no address", [mail("Lee Roe", "Email")], 0,
             "opens an address this reader does not read"),
            ("a link with no text of its own", ["<a href='mailto:lee@example.invalid'>"
                                                "<img alt='Email' src='x.png'/></a>"], 0,
             "no text of its own"),
            ("a link with no text beside another address",
             ["<a href='mailto:lee@example.invalid'></a>", mail("lee.roe@example.invalid")], 0,
             "no text of its own"),
            ("an address hidden behind a script",
             ["<a href='/cdn-cgi/l/email-protection#0a'>[email protected]</a>"], 0,
             "behind a script"),
            ("fewer people with an address than the floor", [mail("lee@example.invalid")], 2,
             "fewer than the 2")]:
        try:
            read_city(dict(ce, emails=floor),
                      html(entries[:4] + insert + entries[4:]), "", "2026-10-17")
            fails.append("%s: was not refused" % label)
        except SystemExit as e:
            if why not in str(e):
                fails.append("%s: refused for another reason: %s" % (label, e))
            if "@" in str(e):
                fails.append("%s: the message prints an address" % label)
    # Addresses, read by card: a card is matched to its seat's person by the
    # name it prints above its seat line, and an icon's link is the card's.
    def card(first, last, job, *links):
        return ("<div class='member'><div><span>%s</span> <span>%s</span></div>"
                "<div>%s</div><div>%s</div></div>" % (first, last, job, "".join(
                    "<a href='mailto:%s' title='Email'><img alt='Email' src='x.png'/></a>" % a
                    for a in links)))
    cc = dict(c4, cards=("member", r"^Ward (?P<ward>\d{1,2}) Council(?:wo)?man$"), emails=2)
    top = "<p>Mayor Pat Doe</p><p>Ward 1 – Kim Poe</p><p>Ward 2 – Jo Moe</p>"
    cards = (card("Kim", "Poe", "Ward 1 Councilman", "kim@example.invalid") +
             card("Jo", "Moe", "Ward 2 Councilwoman", "jo@example.invalid", "clerk@example.invalid") +
             "<div class='member'><div>Council Clerk</div></div>" + "<p>%s</p>" % mail("clerk@example.invalid"))
    rec = read_city(cc, "<html><body>" + top + cards + "</body></html>", "", "2026-10-17")
    ok("addresses on each card", [(s["seat"], s.get("email")) for s in rec["seats"]],
       [("Mayor", None), ("Ward 1", "kim@example.invalid"), ("Ward 2", "jo@example.invalid")])
    for label, body, why in [
            ("a card naming another person",
             card("Jo", "Moe", "Ward 1 Councilman", "kim@example.invalid") +
             card("Kim", "Poe", "Ward 2 Councilman", "jo@example.invalid"),
             "names someone other than"),
            ("two cards for one seat",
             card("Kim", "Poe", "Ward 1 Councilman", "kim@example.invalid") +
             card("Kim", "Poe", "Ward 1 Councilman", "kim2@example.invalid"),
             "two cards print this seat"),
            ("fewer cards with an address than the floor",
             card("Kim", "Poe", "Ward 1 Councilman", "kim@example.invalid"), "fewer than the 2")]:
        try:
            read_city(cc, "<html><body>" + top + body + "</body></html>", "", "2026-10-17")
            fails.append("%s: was not refused" % label)
        except SystemExit as e:
            if why not in str(e):
                fails.append("%s: refused for another reason: %s" % (label, e))
            if "@" in str(e) or re.search(r"Kim|Jo Moe", str(e)):
                fails.append("%s: the message prints an address or a name" % label)
    ok("OWN_EMAIL", [bool(OWN_EMAIL.match(t)) for t in
                     ["kim@example.invalid", "Kim.Poe@Example.Invalid", "a@b.co",
                      "mailto:kim@example.invalid", "kim@example", "kim @example.invalid",
                      "kim@example.invalid?subject=x", "kim@example.invalid, jo@example.invalid"]],
       [True, True, True, False, False, False, False, False])
    ok("office_mailbox", [office_mailbox(t) for t in
                          ["info@x.gov", "City.Hall@x.gov", "city-clerk@x.gov", "Award1@x.gov",
                           "mayor@x.gov", "kim@x.gov"]],
       [True, True, True, False, False, False])
    if fails:
        for f in fails:
            print("FAIL " + f)
        return 1
    print("OK selftest: seat labels, re-casing, the name test, the four page shapes, five "
          "refusals, the seat labels a page prints, each person's numbers and five refusals "
          "of them, each person's address read by entry and by card and nine refusals of "
          "them")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pages", help="read saved pages from this directory instead of fetching")
    ap.add_argument("--save-pages", help="fetch, and keep a copy of every page read here")
    ap.add_argument("--read-date", help="the date the saved pages were read (with --pages)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.check:
        return check(a.out)
    if a.pages and not a.read_date:
        ap.error("--pages needs --read-date, the day those pages were read")
    data = build(a.pages, a.save_pages, a.read_date)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print("wrote %s" % os.path.relpath(a.out, REPO), file=sys.stderr)
    return check(a.out)


if __name__ == "__main__":
    sys.exit(main())
