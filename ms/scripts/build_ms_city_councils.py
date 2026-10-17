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

WHAT IS CARRIED, AND WHAT NEVER IS. The seat and the name, and nothing else.
Most of these pages print more beside each member: an e-mail address on most,
a telephone on some, a biography on a few. Whether a printed telephone or
address is an office line or the member's own is not established for any of
them, so none of it is read into the file. No staff member (a city clerk, a
council clerk, an assistant to the mayor) is named.

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
# after one.
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
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$")},
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
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$")},
    {"geoid": "2854040", "name": "Olive Branch", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.obms.us/230/Board-of-Aldermen",
     "mayor_page": None,
     "members": "name / seat",
     "mayor": ("council", "before", r"^Mayor$")},
    {"geoid": "2874840", "name": "Tupelo", "body": "City Council",
     "wards": 7, "at_large": 0,
     "council": "https://www.tupeloms.gov/my-government/city-council",
     "mayor_page": "https://www.tupeloms.gov/my-government/mayor",
     "members": "name / seat",
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$")},
    {"geoid": "2846640", "name": "Meridian", "body": "City Council",
     "wards": 5, "at_large": 0,
     "council": "https://meridianms.org/government/city-council/",
     "mayor_page": "https://meridianms.org/government/mayor/",
     "members": "seat / name",
     "mayor": ("mayor", "line", r"^A Message from Mayor (?P<name>.+)$")},
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
     "mayor": ("mayor", "before", r"^Mayor$")},
    {"geoid": "2855760", "name": "Pearl", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.cityofpearl.com/government/board-of-aldermen/",
     "mayor_page": "https://www.cityofpearl.com/government/mayors-office/",
     "members": "name / seat",
     "mayor": ("mayor", "line", r"^Mayor (?P<name>.+)$")},
    {"geoid": "2833700", "name": "Horn Lake", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.hornlake.org/government",
     "mayor_page": None,
     "members": "seat / name",
     "mayor": ("council", "after", r"^Mayor$")},
    {"geoid": "2854840", "name": "Oxford", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://www.oxfordms.net/board-of-aldermen",
     "mayor_page": "https://www.oxfordms.net/departments/mayor-s-office",
     "members": "name / seat",
     "mayor": ("mayor", "before", r"^,?\s*Mayor$")},
    {"geoid": "2808300", "name": "Brandon", "body": "Board of Aldermen",
     "wards": 6, "at_large": 1,
     "council": "https://brandonms.org/government/board-of-aldermen/",
     "mayor_page": "https://brandonms.org/government/office-of-the-mayor/",
     "members": "name / seat",
     "mayor": ("mayor", "line", r"^(?P<name>.+), Mayor$")},
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
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.skip = 0
        self.buf = []
        self.lines = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        if tag in BLOCK_TAGS:
            self.flush()

    def handle_startendtag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.flush()

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        if tag in BLOCK_TAGS:
            self.flush()

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
def member_readings(lines, shape):
    """Every (seat, raw text) pair the page offers in its declared shape."""
    out = []
    if shape == "name, seat":
        for ln in lines:
            m = NAME_COMMA_SEAT.match(ln)
            if m:
                out.append((seat_of(m.group("seat")), m.group("name")))
    elif shape == "seat - name":
        for ln in lines:
            m = SEAT_DASH_NAME.match(ln)
            if m:
                out.append((seat_of(m.group("seat")), m.group("name")))
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
                out.append((seat, lines[j]))
    else:
        raise ValueError("unknown shape %r" % shape)
    return [(s, t) for s, t in out if s]


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


def mayor_readings(lines, how, pattern):
    rx = re.compile(pattern, re.I)
    out = []
    for i, ln in enumerate(lines):
        m = rx.match(ln)
        if not m:
            continue
        if how == "line":
            out.append(m.group("name"))
        else:
            step = -1 if how == "before" else 1
            j = i + step
            while 0 <= j < len(lines) and SEPARATOR.match(lines[j]):
                j += step
            if 0 <= j < len(lines):
                out.append(lines[j])
    return out


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


def expected_seats(c):
    seats = ["Ward %d" % n for n in range(1, c["wards"] + 1)]
    if c["at_large"]:
        seats = ["At Large"] + seats
    return seats


def read_city(c, council_html, mayor_html, read_date):
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
    lines = page_lines(council_html)
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
        rec = read_city(c, council, mayor, read_date or date.today().isoformat())
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
    problems = []
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
        keys = []
        for s in rec.get("seats", []):
            allowed = {"seat", "name"} if s.get("name") else {"seat", "vacant"}
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
        if len(keys) != len(set(keys)):
            problems.append("%s: one name for two seats" % c["name"])
        allowed_rec = {"name", "body", "seats", "councilUrl", "mayorUrl", "read"}
        if set(rec) - allowed_rec:
            problems.append("%s: carries %s" % (c["name"], sorted(set(rec) - allowed_rec)))
    if problems:
        for p in problems:
            print("FAIL " + p)
        return 1
    named = sum(1 for r in data.values() for s in r.get("seats", []) if s.get("name"))
    print("OK ms-city-councils.json: %d cities, %d people named, %d city names nobody"
          % (len(data), named, sum(1 for r in data.values() if not r.get("seats"))))
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
    if fails:
        for f in fails:
            print("FAIL " + f)
        return 1
    print("OK selftest: seat labels, re-casing, the name test, the four page shapes, five "
          "refusals, the seat labels a page prints")
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
