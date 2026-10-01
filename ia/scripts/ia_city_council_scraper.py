#!/usr/bin/env python3
"""
Scrape stage 1: the mayor and council of Iowa's fourteen cities above 25,000
that name nobody on this app today, cached for build_ia_city_councils.py.

WHY THESE FOURTEEN, AND WHY THEY ARE A DIFFERENT FILE FROM THE OTHER FIVE
--------------------------------------------------------------------------
Iowa has 18 incorporated cities over 25,000 (Census 2020). Four already name
their councils here: Des Moines and Waterloo through the `city-ward` layer,
Cedar Rapids and one other through their own builders. The remaining FOURTEEN
published nobody, which is the whole of what this instance was missing at the
local-government level of the done standard's Covered test.

`ia_city_officials_scraper.py` is five SMALL cities and cannot grow to hold
these. Its gates are global: `SEATS_PER_CITY = 6`, exactly one plain `Mayor`,
and an e-mail for every member. Not one of those holds across the fourteen --
Davenport seats ten, Sioux City five, Council Bluffs publishes no member
e-mail at all, and two cities do not name their mayor on the page their own
navigation calls the council page. Loosening those guards to admit fourteen
cities would retire the guards that protect the five. So the declarations are
PER CITY here, and every one of them is a measurement of that city's page
taken 2026-10-01, not a target.

NINE CONVENTIONS FOR FOURTEEN CITIES, AND THE PLATFORM PREDICTS NONE OF THEM
-----------------------------------------------------------------------------
Ankeny, Marshalltown, Urbandale, Sioux City and Council Bluffs all run the
same content system and need FIVE different parsers: Ankeny writes the name on
one line and the role on the next, Marshalltown writes `Name, Seat`,
Urbandale writes both inside an anchor's text and nowhere in the page's prose,
Sioux City writes name-then-role with no contact at all, and Council Bluffs
writes name then role TWICE and hides every address behind a form. Davenport
writes `Seat, Name`, the reverse of Marshalltown. Cedar Falls writes
`Name-Seat` for its wards and `At Large-Name` for its at-large members, in one
list, which is the reverse of itself. So each city carries its shape
explicitly in CITIES below, and a city whose page changes shape fails its own
seat gate rather than quietly returning nothing.

That is the township scraper's lesson applied before it could be paid for
again: a parser written against one of two wrappers returns a clean,
confident, half-empty answer for the other.

THREE CITIES PUBLISH THEIR MEMBERS' HOME ADDRESSES. NONE OF THEM SHIPS.
------------------------------------------------------------------------
Bettendorf, Dubuque and Ottumwa each print a residential street address under
the member's name -- it is how those cities have always published a ward
representative, and it is not ours to republish. The parser reads NAME, ROLE,
PHONE, E-MAIL and TERM and nothing else, and `looks_like_address` refuses any
value that reads as a street address even in a field that should not hold one.
The refusal is not a formality: on these three pages the address sits BETWEEN
the role and the phone, so a parser that took "the next line after the role"
would ship it.

A PHONE EVERY MEMBER SHARES IS THE OFFICE'S, NOT THEIRS
---------------------------------------------------------
Council Bluffs' council directory prints (712) 890-5261 beside all five
members: that is the council office's number, repeated. Shipping it as each
member's own would tell a reader they had five people's direct lines. So a
phone that is identical across every member a page names is dropped, and the
drop is printed. The same page's mayor directory prints a different number per
person, which is why this is a rule about what a page states rather than a
rule about a city.

NOT EVERY PERSON ON A COUNCIL PAGE IS ON THE COUNCIL
------------------------------------------------------
Ames' council seats a mayor, six elected members and an EX-OFFICIO member from
Iowa State University, whose own page gives their role as exactly
`Ex-Officio`. Council Bluffs' mayor directory lists the Assistant to the
Mayor. Iowa City's table is followed by its student liaisons. A card answering
"who represents you" must not name any of them, so each city declares the
roles it elects and anything else is dropped WITH ITS NAME PRINTED -- never
silently, because a role that stops matching looks exactly like a person who
left.

TWO CITIES DO NOT NAME THEIR MAYOR AND THAT IS MEASURED, NOT ASSUMED
----------------------------------------------------------------------
Davenport's council page names ten aldermen and no mayor, and its own Mayor's
Office page names no mayor either (measured 2026-10-01: the page carries the
office's address and telephone and no person). Cedar Falls' council page names
its seven council members and not the mayor, and the `/67/Mayor` path a reader
would guess answers 404. So those two carry `mayor=False`, their seat counts
exclude a mayor, and the gap is recorded rather than filled from somewhere
this project has not read.

GUESSING A URL ON THESE PLATFORMS IS WORSE THAN USELESS
---------------------------------------------------------
Every URL here was taken from the city's own page or navigation, because the
guessed ones misfire in ways a 404 check would not catch:
`councilbluffs-ia.gov/121/Mayor` and `cedarfalls.com/67/Mayor` answer 404,
Marion's guessed staff-directory path answers 403, and
`urbandale.org/327/Mayor` REDIRECTS TO `iowasexoffender.gov`. Ames' eight
member pages are not guessed either -- they are read out of the links on Ames'
own council page.

THREE CITIES ANSWER ONLY A BROWSER CLIENT, AND THE ROBOTS READ FOLLOWS SUIT
----------------------------------------------------------------------------
Eleven of the fourteen serve `districtry/1.0` a full page. Iowa City, Marion
and West Des Moines refuse it and answer Chrome/126 with its client hints
(measured 2026-10-01, four rungs each: the Iowa token and Chrome on both HTTP
stacks). For those three the ROBOTS.TXT IS READ WITH THE SAME CHROME CLIENT
that will crawl, which is the fleet's consistency rule and not an escalation:
which client crawls is decided by the measurement, and the policy read
follows that choice rather than leading it. No city here is probed with a
second client after the first one served it.

Usage:
    python3 ia/scripts/ia_city_council_scraper.py
    python3 ia/scripts/ia_city_council_scraper.py --selftest
"""

import html as html_mod
import json
import os
import re
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                                    # robots_gate sibling
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from robots_gate import RobotsGate                          # noqa: E402
import scraper_common as SC                                 # noqa: E402

CACHE_DIR = os.path.join(HERE, ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_city_councils.json")

IA_TOKEN = "districtry/1.0 (+https://districtry.com/ia/)"
TOKEN_HEADERS = {"User-Agent": IA_TOKEN,
                 "Accept": "text/html,application/xhtml+xml"}

# Keyed by 7-digit TIGER place GEOID, the key the City card already reads.
#
#   shape   -- which parser below reads this city's page
#   seats   -- what the city's OWN page publishes, counted 2026-10-01
#   mayor   -- does that page name the mayor
#   client  -- `token` or `chrome`, measured per host
#   roles   -- the elected roles this city publishes; anything else is dropped
CITIES = [
    {"geoid": "1901855", "name": "Ames", "shape": "ames", "seats": 7,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.cityofames.org/My-Government/Mayor-and-City-Council"},
    {"geoid": "1902305", "name": "Ankeny", "shape": "name_then_role", "seats": 6,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.ankenyiowa.gov/456/Mayor-City-Council"},
    {"geoid": "1906355", "name": "Bettendorf", "shape": "role_then_name", "seats": 8,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.bettendorf.org/government/mayor___council/index.php"},
    {"geoid": "1911755", "name": "Cedar Falls", "shape": "link_dash_either", "seats": 7,
     "mayor": False, "client": "token", "roles": ("council",),
     "url": "https://www.cedarfalls.com/1106/City-Council-Members"},
    {"geoid": "1916860", "name": "Council Bluffs", "shape": "name_then_role", "seats": 6,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.councilbluffs-ia.gov/m/directory/department?did=64",
     "also": ["https://www.councilbluffs-ia.gov/m/directory/department?did=9"]},
    {"geoid": "1919000", "name": "Davenport", "shape": "seat_comma_name", "seats": 10,
     "mayor": False, "client": "token", "roles": ("council",),
     "url": "https://www.davenportiowa.com/government/mayor_council/city_council"},
    {"geoid": "1922395", "name": "Dubuque", "shape": "dubuque", "seats": 7,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.cityofdubuque.org/990/Mayor-City-Council"},
    {"geoid": "1938595", "name": "Iowa City", "shape": "staff_table", "seats": 7,
     "mayor": True, "client": "chrome", "roles": ("mayor", "council"),
     "url": "https://www.icgov.org/government/city-council"},
    {"geoid": "1949485", "name": "Marion", "shape": "role_then_name", "seats": 7,
     "mayor": True, "client": "chrome", "roles": ("mayor", "council"),
     "url": "https://www.cityofmarion.org/about-us/mayor-city-council/council-profiles"},
    {"geoid": "1949755", "name": "Marshalltown", "shape": "name_comma_seat", "seats": 8,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.marshalltown-ia.gov/154/Mayor-City-Council"},
    {"geoid": "1960465", "name": "Ottumwa", "shape": "role_then_name", "seats": 6,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.ottumwa.us/government/mayor_and_city_council_new.php"},
    {"geoid": "1973335", "name": "Sioux City", "shape": "name_then_role", "seats": 5,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.sioux-city.org/247/City-Council"},
    {"geoid": "1979950", "name": "Urbandale", "shape": "link_name_role", "seats": 6,
     "mayor": True, "client": "token", "roles": ("mayor", "council"),
     "url": "https://www.urbandale.org/326/Mayor-City-Council"},
    {"geoid": "1983910", "name": "West Des Moines", "shape": "staff_table", "seats": 6,
     "mayor": True, "client": "chrome", "roles": ("mayor", "council"),
     "url": "https://www.wdm.iowa.gov/government/mayor-city-council/biographies"},
]

# ------------------------------------------------------------------ vocabulary
#
# A ROLE STRING IS CLASSIFIED, NOT MATCHED WHOLE. The fourteen cities write
# fourteen vocabularies -- `Councilmember`, `Council Member`, `City
# Councilmember`, `Councilor`, `Alderman`, `Council Member At-Large`,
# `Mayor Pro Tem`, `Mayor Shudak` (Council Bluffs puts the mayor's SURNAME in
# the title field) -- so `classify` reduces each to `mayor`, `council` or
# None, and None is what gets dropped and printed.
MAYOR_WORD = re.compile(r"(?i)\bmayor\b")
PRO_TEM = re.compile(r"(?i)\bpro[-\s]?tem(pore)?\b")
COUNCIL_WORD = re.compile(r"(?i)\b(council\s*(member|man|woman|person)?|councilm\w+"
                          r"|councilor|alderm\w+|at[-\s]?large|ward)\b")
SEAT = re.compile(r"(?i)\b(?:(?P<ord>\d+)(?:st|nd|rd|th)?\s*ward"
                  r"|ward\s*(?P<ward>\w+)"
                  r"|district\s*(?P<district>[A-Z0-9]+)"
                  r"|(?P<atlarge>at[-\s]?large))\b")
# A NAME MAY CARRY A GENERATIONAL SUFFIX AFTER A COMMA, and one here does:
# Ottumwa's `Bill Hoffman, Jr.` Without the suffix arm that one council member
# parsed as nothing at all and Ottumwa shipped five of six seats.
SUFFIX = r"(?:,\s*(?:Jr|Sr|II|III|IV)\.?)?"
NAME = re.compile(r"^[A-Z][\w.'’-]*(?:\s+[\w.'’“”\"-]+){1,3}"
                  + SUFFIX + r"$", re.U)
# An ALL-CAPS name, which one of these pages writes as a heading.
CAPS_NAME = re.compile(r"^[A-Z][A-Z.'’-]*(?:\s+[A-Z][A-Z.'’-]*){1,3}"
                       + SUFFIX + r"$")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}")
PHONE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
TERM = re.compile(r"(?i)term\s*(?:expires?|ending)?\s*:?\s*"
                  r"(?:dec\w*\.?\s*31,?\s*)?(\d{1,2}/\d{1,2}/\d{2,4}|\d{4})")
# An address is refused wherever it appears. Both halves matter: a leading
# house number with a street word, and a city/state/ZIP tail. Bettendorf
# writes `6859 Little Cabin Rd.`, Dubuque `2341 Coventry Park, #207`, Ottumwa
# `922 North Green Street,` on its own line with `Ottumwa, IA 52501` beneath.
#
# THE WORD BOUNDARY BEFORE THE STREET WORD IS LOAD-BEARING. Without it this
# pattern reads `3rd Ward` as a street address -- `3` as the house number,
# `Wa` as the street name and the trailing `rd` as the street type -- so every
# ward seat in Marshalltown, Cedar Falls, Davenport and Dubuque was refused as
# an address and four cities parsed one member each. Caught by this file's own
# fixtures the minute the refusal was tightened.
ADDRESS = re.compile(
    r"(?i)(^\s*\d+[\w-]*\s+[\w.'-]+(\s+[\w.'-]+)*\s*,?\s*\b(st|street|ave|avenue|rd|road"
    r"|dr|drive|ln|lane|ct|court|pl|place|blvd|boulevard|way|ter|terrace|cir|circle"
    r"|pkwy|parkway|hwy|highway|trail|trl|park)\b"
    r"|\b[A-Z][a-z]+,\s*(IA|Iowa)\s*\d{5}\b"
    r"|\bP\.?\s*O\.?\s*Box\s*\d+)")
# Lines a roster block carries that are not a person: an alphabet index letter
# or a set of initials (Council Bluffs prints `SG` above Steve Gorman), and
# the platform's own furniture.
NOISE = re.compile(r"(?i)^(?:[A-Z]{1,3}|more information|read bio|email|print|contact"
                   r"|phone|telephone|staff|title|profile\b.*|term expires|show / hide nav"
                   r"|download a pdf.*|members?|overview|contact us|directory)$")


# A LINE CARRYING A COUNCIL WORD IS OFTEN NOT A ROLE AT ALL, and on these
# fourteen pages that is the single biggest source of false people. Measured
# against the real pages 2026-10-01, a parser without this shipped `Our City`
# as the Mayor of Ankeny (the masthead link above `Mayor & City Council`),
# `About Us` as a Marion council member (above `Council Meeting`), `Upcoming
# Meetings` as a member of Ankeny's council (above `City Council Special
# Meeting`), and `Suite 102` and `Physical Address` as Council Bluffs
# councilmembers (above the office's own `Council Bluffs, IA 51503`). Every
# one of those is a navigation label or an address block sitting directly
# above something a role test matched.
NOT_A_ROLE = re.compile(r"(?i)(\bmeeting|\bagenda|\bminutes|\bsession|\brecap|\bchambers"
                        r"|\bmap\b|\bpage\b|\bgoals\b|\bvision\b|\bprofiles?\b"
                        r"|\bwards\b|&|\bet\s|\bIA\s*\d{5})")
# A PERSON'S NAME CARRIES NO DIGIT and is not one of the platform's own
# labels. `Suite 102` and `Ward 1` both satisfy a bare capitalised-words
# pattern; neither is anybody.
NOT_A_NAME = re.compile(r"(?i)(\d|^(our|about|the|city|contact|physical|mailing|upcoming"
                        r"|quick|skip|home|search|font|share|print|activate|website"
                        r"|create|select|translate|additional|view|read|download"
                        r"|back|last|show|more|members?|staff|title|phone|email"
                        r"|telephone|term|overview|directory|employment)\b)")


# A title on a council page that is NOT an elected seat. Each one is on a
# page this scraper reads: Ames' Iowa State ex-officio, Council Bluffs'
# Assistant to the Mayor, Iowa City's student liaisons.
NOT_ELECTED = re.compile(r"(?i)\b(ex[-\s]?officio|assistant|secretary|clerk|liaison"
                         r"|attorney|manager|administrator|intern|student|director"
                         r"|engineer|chief|treasurer)\b")


# A CAPITALISED NAME THIS FUNCTION MUST NOT GUESS AT. Mc and Mac are PREFIX
# tests -- in all-caps text `MCGREW` is one word, so a whole-word `\bmc\b`
# matches nothing and the refusal never fires, which is what a first draft
# did. The particles are whole-word tests, because `DE` as a prefix refuses
# DEAN and `VAN` refuses VANCE. VANDER and VANDE are named as prefixes
# because both are ordinary Iowa surnames written solid.
#
# THIS LIST IS WHAT THIS PROJECT HAS MET AND IS NOT A PROOF OF COVERAGE: a
# capitalised name carrying some other part a rule gets wrong will ship
# miscased, and the remedy is an explicit label with the page that spells it,
# not a wider guess. Today exactly ONE name on ONE of the fourteen pages
# reaches this function at all.
AMBIGUOUS_CAPS = re.compile(r"(?i)['\u2019]|\b(mc|mac|vander|vande)[a-z]"
                            r"|\b(van|von|de|la|le|du|des|st|ter)\b")


def person_case(name):
    """Display form for a name a page writes in CAPITALS as a heading.

    ONE PAGE NEEDS THIS AND THE FUNCTION REFUSES EVERY NAME IT CANNOT GET
    RIGHT. Bettendorf heads its mayor's block `MAYOR ROBERT S. GALLAGHER`
    while writing all seven council members in mixed case on the same page, so
    the capitals are that heading's styling rather than the name. No rule
    renders `O'BRIEN`, `MCGREW` or `VANDER HART` correctly -- the shared
    title_case helper's own docstring says as much about apostrophes -- so
    this REFUSES on those and the city then needs the name stated explicitly
    with the page that spells it, which is what Hardin County's precinct
    labels already do. Shipping `Mcgrew` for McGrew misspells somebody's name
    on a card, and a card is where a reader would see it.
    """
    if AMBIGUOUS_CAPS.search(name):
        raise SystemExit(
            "%r is published in capitals and carries a part no rule re-cases "
            "correctly. State this person's name explicitly, with the page that "
            "spells it, rather than deriving it." % name)
    out = []
    for word in name.split():
        if re.match(r"^[A-Z]\.?$", word) or re.match(r"(?i)^(jr|sr|ii|iii|iv)\.?,?$", word):
            out.append(word)                      # an initial or a suffix
            continue
        out.append("-".join(part.capitalize() for part in word.split("-")))
    return " ".join(out)


def split_role_name(line):
    """`MAYOR ROBERT S. GALLAGHER` -> ("Mayor", "Robert S. Gallagher").

    TWO OF THESE FOURTEEN CITIES PUT THE OFFICE AND THE PERSON ON ONE LINE:
    Dubuque writes `Council Member David T. Resnick` for every seat, and
    Bettendorf writes its seven council members as a role heading above a name
    and then heads its MAYOR'S block with both together, in capitals. So this
    returns None where the line is a role alone (`COUNCIL MEMBER - AT LARGE`),
    which is how one parser reads both of that page's shapes -- without it
    Bettendorf shipped seven of eight seats and named no mayor.
    """
    m = re.match(r"(?i)^\s*(mayor\s+pro[-\s]?tem(?:pore)?|mayor|council\s*member"
                 r"|councilmember|councilor|alderman|alderwoman)\b(?P<rest>.*)$", line)
    if not m:
        return None
    role = m.group(1).strip()
    rest = m.group("rest").strip(" -\u2013\u2014:,")
    if not rest:
        return None
    # WHAT FOLLOWS THE OFFICE IS OFTEN THE SEAT, NOT A PERSON. Bettendorf's
    # seven council members are headed `COUNCIL MEMBER - AT LARGE` and
    # `COUNCIL MEMBER - 1ST WARD`, so a splitter that took the remainder as a
    # name invented a councilmember called At Large and dropped a real one.
    # The seat and role tests come FIRST for that reason.
    if classify(rest) or role_like(rest) or seat_of(rest):
        return None
    if CAPS_NAME.match(rest):
        rest = person_case(rest)
    elif not NAME.match(rest):
        return None
    if NOT_A_NAME.search(rest) or looks_like_address(rest):
        return None
    if role.isupper():
        role = role.title()
    return role, rest


def classify(role):
    """`mayor`, `council`, or None for a role string this card must not ship.

    THE OFFICE IS THE LEADING WORDS AND THE SEAT IS WHAT FOLLOWS, which is why
    the mayor test comes first and reads the START of the string. Iowa City
    publishes its mayor's role as `Mayor, At-Large`, and a council test that
    merely searched for `At-Large` anywhere classified the mayor of the
    seventh-largest city in Iowa as a council member -- caught by this file's
    own fixture before it shipped, where the city's seat gate would then have
    failed on a mayor the page plainly names.
    """
    if not role:
        return None
    if NOT_ELECTED.search(role) or NOT_A_ROLE.search(role) or looks_like_address(role):
        return None
    if PRO_TEM.search(role):
        return "council"
    if re.match(r"(?i)^\s*(the\s+)?mayor\b", role):
        return "mayor"
    if COUNCIL_WORD.search(role):
        return "council"
    if MAYOR_WORD.search(role):
        return "mayor"
    return None


def role_like(line):
    """Does this line read as somebody's TITLE, elected or not?

    The parsers use this and `finish` uses `classify`, deliberately: a parser
    that only recognised elected titles would make a city's staff INVISIBLE
    rather than dropped, and an invisible non-member reads exactly like a
    member who left. So every title is found and `finish` decides, printing
    each name it drops.
    """
    if not line or len(line) > 60 or NOT_A_ROLE.search(line) or looks_like_address(line):
        return False
    return bool(classify(line) or NOT_ELECTED.search(line))


def name_like(line):
    """Is this line plausibly a PERSON'S name rather than a page's furniture?"""
    return bool(line and NAME.match(line) and not NOT_A_NAME.search(line)
                and not NOISE.match(line) and not looks_like_address(line)
                and not role_like(line))


def seat_of(role):
    """The ward, district or at-large seat a role string names, or None."""
    m = SEAT.search(role or "")
    if not m:
        return None
    if m.group("atlarge"):
        return "At-Large"
    if m.group("ord"):
        return "Ward %s" % m.group("ord")
    if m.group("ward"):
        w = m.group("ward")
        words = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                 "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
        return "Ward %s" % words.get(w.lower(), w)
    if m.group("district"):
        return "District %s" % m.group("district").upper()
    return None


def looks_like_address(value):
    return bool(ADDRESS.search(value or ""))


def text_lines(page):
    """Tags to text, with <br>, <hr> and block ends becoming line breaks first.

    The same order `ia_city_officials_scraper.py` settled on, and for the same
    reason: strip tags first and a member's name, phone and e-mail collapse
    into one unsplittable string on every page that separates them with <br>.
    A mailto anchor is rewritten to `text address` BEFORE tags are stripped.
    """
    t = re.sub(r"(?is)<(script|style|nav|footer|select|option)[^>]*>.*?</\1>", " ", page)
    t = re.sub(r'<a[^>]*href="mailto:([^"?]+)[^"]*"[^>]*>(.*?)</a>', r" \2 \1 ", t,
               flags=re.I | re.S)
    t = re.sub(r"<br\s*/?>|<hr\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|h[1-6]|div|li|td|tr|strong|span|b|em|a|dt|dd|th)>", "\n", t,
               flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_mod.unescape(t).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in t.split("\n") if line.strip()]


def anchors(page):
    """(href, visible text) for every anchor, text collapsed to one line."""
    out = []
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.I | re.S):
        text = html_mod.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        out.append((m.group(1), re.sub(r"\s+", " ", text).strip()))
    return out


def _contact(lines, start, stop):
    """Phone, e-mail and term from a member's own block, addresses refused."""
    rec = {}
    window = [ln for ln in lines[start:stop] if not looks_like_address(ln)]
    joined = " ".join(window)
    for key, pattern in (("phone", PHONE), ("email", EMAIL)):
        found = pattern.search(joined)
        if found and not looks_like_address(found.group(0)):
            rec[key] = found.group(0)
    term = TERM.search(joined)
    if term:
        rec["termEnds"] = term.group(1)
    return rec


def _from_hits(lines, hits):
    """Build records from (line index, name, role) hits, each bounded by the next.

    Every member's contact scan stops at the NEXT member, so nothing below the
    roster can donate a detail to somebody -- the Riverside footer lesson.
    The LAST member is bounded by the smallest gap this page itself states
    between consecutive members, which is a distance the page gives rather
    than a window a reader picked.
    """
    if not hits:
        return []
    gaps = [hits[n + 1][0] - hits[n][0] for n in range(len(hits) - 1)]
    reach = min(gaps) if gaps else 1
    out = []
    for n, (i, name, role) in enumerate(hits):
        stop = hits[n + 1][0] if n + 1 < len(hits) else min(len(lines), i + reach)
        rec = {"name": name, "role": role}
        rec.update(_contact(lines, i, stop))
        out.append(rec)
    return out


# ------------------------------------------------------------------- parsers

def parse_name_then_role(page):
    """Ankeny, Sioux City, Council Bluffs: a name line, then its role line.

    The role may repeat (Council Bluffs prints it twice), so the role is taken
    from the FIRST non-noise line after the name that classifies as one.
    """
    lines = text_lines(page)
    hits = []
    for i, line in enumerate(lines):
        if not name_like(line):
            continue
        for k in range(i + 1, min(len(lines), i + 3)):
            if role_like(lines[k]):
                hits.append((i, line, lines[k]))
                break
    return _from_hits(lines, hits)


def parse_role_then_name(page):
    """Bettendorf, Marion, Ottumwa: a role heading, then the name beneath it."""
    lines = text_lines(page)
    hits = []
    for i, line in enumerate(lines):
        if not role_like(line):
            continue
        # The office and the person may share the line -- Bettendorf's mayor.
        together = split_role_name(line)
        if together:
            hits.append((i, together[1], together[0]))
            continue
        for k in range(i + 1, min(len(lines), i + 3)):
            cand = lines[k]
            if name_like(cand):
                hits.append((k, cand, line))
                break
    return _from_hits(lines, hits)


def parse_name_comma_seat(page):
    """Marshalltown: `Mike Ladehoff, Mayor` / `Greg Nichols, 3rd Ward`."""
    return _comma(page, name_first=True)


def parse_seat_comma_name(page):
    """Davenport: `Ward 3, Paul Vasquez` / `At-Large, Kyle Gripp` -- the reverse."""
    return _comma(page, name_first=False)


def _comma(page, name_first):
    lines = text_lines(page)
    hits = []
    for i, line in enumerate(lines):
        if "," not in line or len(line) > 70:
            continue
        left, _, right = line.partition(",")
        left, right = left.strip(), right.strip()
        name, role = (left, right) if name_first else (right, left)
        if not name_like(name) or not role_like(role):
            continue
        hits.append((i, name, role))
    return _from_hits(lines, hits)


def parse_staff_table(page):
    """Iowa City, West Des Moines: `Surname, First` / `Role, Seat` / phone / e-mail.

    The name is published SURNAME FIRST and is flipped, with the flip printed
    by the builder: a card reading `Teague, Bruce` is the table's key order,
    not how anyone is addressed.
    """
    lines = text_lines(page)
    hits = []
    for i, line in enumerate(lines):
        if "," not in line or len(line) > 50 or looks_like_address(line):
            continue
        surname, _, first = line.partition(",")
        surname, first = surname.strip(), first.strip()
        if not surname or not first or role_like(line):
            continue
        if not re.match(r"^[A-Z][\w.'’-]+$", surname) or not re.match(
                r"^[A-Z][\w.'’-]*(?: [A-Z][\w.'’-]*)?$", first):
            continue
        if i + 1 >= len(lines) or not role_like(lines[i + 1]):
            continue
        hits.append((i, "%s %s" % (first, surname), lines[i + 1]))
    return _from_hits(lines, hits)


def parse_link_name_role(page):
    """Urbandale: every seat only inside an anchor's text, `Bob Andeweg - Mayor`.

    The page's prose names nobody at all -- it says "the Mayor and the five
    Councilmembers are the official governing body" and stops -- so the
    anchors are the roster.
    """
    out = []
    for href, text in anchors(page):
        if not re.match(r"^/\d+/", href):
            continue
        parts = re.split(r"\s+[-–—]\s+", text)
        if len(parts) != 2:
            continue
        name, role = parts[0].strip(), parts[1].strip()
        if name_like(name) and role_like(role):
            out.append({"name": name, "role": role})
    return out


def parse_link_dash_either(page):
    """Cedar Falls: `Gil Schultz-1st Ward` AND `At Large-Kelly Dunn`, one list.

    The page writes the seat on the right for its five wards and on the LEFT
    for its two at-large members, so the side is decided per row by which half
    classifies as a role. A parser fixing the side returns five of seven.
    """
    out = []
    for href, text in anchors(page):
        if not re.match(r"^/\d+/", href):
            continue
        parts = re.split(r"\s*[—–]\s*|\s+-\s+", text)
        if len(parts) != 2:
            continue
        a, b = parts[0].strip(), parts[1].strip()
        if role_like(b) and name_like(a):
            name, role = a, b
        elif role_like(a) and name_like(b):
            name, role = b, a
        else:
            continue
        if not looks_like_address(text):
            out.append({"name": name, "role": role})
    return out


def parse_dubuque(page):
    """Dubuque: `Mayor Brad M. Cavanagh` / `Council Member David T. Resnick`.

    The role and the name share one line and the SEAT is on the next
    (`At-Large Representative`, `Ward One Representative`), with the member's
    HOME ADDRESS on the two lines after that. So the seat is read from the
    following line and the address refusal does the rest.
    """
    lines = text_lines(page)
    hits = []
    for i, line in enumerate(lines):
        together = split_role_name(line)
        if not together:
            continue
        role, name = together
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if seat_of(nxt):
            role = "%s, %s" % (role, nxt.strip())
        hits.append((i, name, role))
    return _from_hits(lines, hits)


def parse_ames(page, member_pages):
    """Ames: the council page LINKS one page per member, and the role is there.

    The eight member links are read off the council page rather than guessed
    (`My-Government/Mayor-and-City-Council/<Name>`), and each member's own
    page carries the name, the seat, the Capitol-style telephone and an
    e-mail. The eighth is the Iowa State ex-officio, whose role reads exactly
    `Ex-Officio` and whom `classify` drops.
    """
    out = []
    for url, body in member_pages:
        lines = text_lines(body)
        # THE SLUG AND THE HEADING DISAGREE ON PUNCTUATION, so both sides are
        # reduced to letters before being compared. `Bronwyn-Beatty-Hansen`
        # against the heading `Bronwyn Beatty-Hansen` is one hyphen out, and a
        # literal comparison lost that council member: Ames parsed six of seven
        # seats, which its own seat gate caught and a reader never would have.
        def norm(text):
            return re.sub(r"[^a-z]", "", text.lower())
        want = norm(re.sub(r"(?i)^mayor[-\s]+", "",
                           url.rstrip("/").rsplit("/", 1)[-1]))
        for i, line in enumerate(lines):
            if norm(line) != want:
                continue
            role = ""
            for k in range(i + 1, min(len(lines), i + 3)):
                if role_like(lines[k]):
                    role = re.sub(r"(?i)\s*1st term:?\s*$", "", lines[k]).strip()
                    break
            if not role:
                break
            rec = {"name": line.strip(), "role": role}
            rec.update(_contact(lines, i, min(len(lines), i + 12)))
            out.append(rec)
            break
    return out


def ames_member_links(page, base):
    """The member pages Ames' own council page links, in page order."""
    out, seen = [], set()
    for href, _text in anchors(page):
        if base not in href:
            continue
        tail = href.split(base, 1)[1].strip("/")
        if not tail or "/" in tail or "?" in tail:
            continue
        if re.search(r"(?i)(vision|goals|meetings|agendas|minutes)", tail):
            continue
        if href not in seen:
            seen.add(href)
            out.append(href)
    return out


PARSERS = {
    "name_then_role": parse_name_then_role,
    "role_then_name": parse_role_then_name,
    "name_comma_seat": parse_name_comma_seat,
    "seat_comma_name": parse_seat_comma_name,
    "staff_table": parse_staff_table,
    "link_name_role": parse_link_name_role,
    "link_dash_either": parse_link_dash_either,
    "dubuque": parse_dubuque,
}


# ------------------------------------------------------------------- shaping

def finish(city, records):
    """Classify, drop what the city does not elect, and apply the page's own gates."""
    kept, dropped = [], []
    for rec in records:
        kind = classify(rec["role"])
        if kind not in city["roles"]:
            dropped.append("%s (%s)" % (rec["name"], rec["role"]))
            continue
        out = {"name": rec["name"], "role": rec["role"], "kind": kind}
        seat = seat_of(rec["role"])
        if seat:
            out["seat"] = seat
        for field in ("phone", "email", "termEnds"):
            if rec.get(field) and not looks_like_address(rec[field]):
                out[field] = rec[field]
        kept.append(out)

    # One name, one record. The duplicate check is the Waterloo lesson: a page
    # that names each member twice does not always spell the second naming the
    # same way, and a plausible seat count never catches it.
    seen, unique = set(), []
    for rec in kept:
        if rec["name"].lower() in seen:
            continue
        seen.add(rec["name"].lower())
        unique.append(rec)

    # A PHONE EVERY MEMBER SHARES IS THE OFFICE'S. Council Bluffs prints one
    # council-office number beside all five members; shipped per member it
    # would read as five direct lines.
    phones = [r.get("phone") for r in unique if r.get("phone")]
    if len(phones) > 1 and len(set(phones)) == 1 and len(phones) == len(unique):
        for rec in unique:
            rec.pop("phone", None)
        print("  %-16s one phone for every member (%s) — the office's, dropped"
              % (city["name"], phones[0]), file=sys.stderr)

    return unique, dropped


def check(city, records):
    if len(records) != city["seats"]:
        raise SystemExit(
            "%s: parsed %d officials, its page publishes %d. That is either the page "
            "changing shape or the city changing its council, and both need reading "
            "before anything ships." % (city["name"], len(records), city["seats"]))
    mayors = [r for r in records if r["kind"] == "mayor"]
    want = 1 if city["mayor"] else 0
    if len(mayors) != want:
        raise SystemExit(
            "%s: found %d mayor records, its page publishes %d. Two cities here name "
            "no mayor on their council page and carry mayor=False with the "
            "measurement; a change either way needs reading."
            % (city["name"], len(mayors), want))
    for rec in records:
        for field, value in rec.items():
            if isinstance(value, str) and looks_like_address(value):
                raise SystemExit(
                    "%s: %s's %s reads as a street address (%r). Three of these cities "
                    "publish their members' home addresses and none of them ships."
                    % (city["name"], rec["name"], field, value))


# ----------------------------------------------------------------- self-test
def _selftest():
    """Every parser arm, on fixtures that reproduce each page's own trap.

    A fixture that does not reproduce the trap proves nothing, so each arm
    carries the thing that broke a draft: the reversed comma, the two-way
    dash, the home address between the role and the phone, the repeated role
    line, the shared office phone, the ex-officio, and the staff below the
    roster.
    """
    failures, ran = [], []

    def ck(cond, msg):
        ran.append(msg)
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    def names(recs):
        return [r["name"] for r in recs]

    # 1. NAME THEN ROLE, with the role repeated and one office phone for all --
    #    the Council Bluffs shape, plus staff the city does not elect.
    cb = ("<div><p>Cole Button</p><p>City Councilmember</p><p>City Councilmember</p>"
          "<p>Email</p><p>(712) 890-5261</p>"
          "<p>SG</p><p>Steve Gorman</p><p>City Councilmember</p>"
          "<p>City Councilmember</p><p>Email</p><p>(712) 890-5261</p>"
          "<p>AG</p><p>Alli Grimm</p><p>Assistant to the Mayor</p>"
          "<p>Assistant to the Mayor</p><p>Email</p><p>(712) 890-5265</p></div>")
    recs = parse_name_then_role(cb)
    kept, dropped = finish({"name": "CB", "roles": ("mayor", "council")}, recs)
    ck(names(kept) == ["Cole Button", "Steve Gorman"],
       "name-then-role: two councilmembers, initials lines skipped (got %r)" % names(kept))
    ck(any("Alli Grimm" in d for d in dropped),
       "name-then-role: the Assistant to the Mayor is dropped and named")
    ck(all("phone" not in r for r in kept),
       "name-then-role: the one shared office phone is nobody's own")

    # 2. ROLE THEN NAME, with a HOME ADDRESS between the role and the phone --
    #    the Bettendorf and Ottumwa shape. The address must reach no field.
    bett = ("<div><p>COUNCIL MEMBER - AT LARGE</p><p>Frank Baden</p>"
            "<p>5063 56th Ave. Ct.</p><p>(563) 344-2442</p>"
            "<p>fbaden@example.gov</p><p>Term Expires 12/31/27</p>"
            "<p>COUNCIL MEMBER - 1ST WARD</p><p>Jerry Sechser</p>"
            "<p>1304 Broadlawn Ave.</p><p>(563) 359-1534</p>"
            "<p>jsechser@example.gov</p><p>Term Expires 12/31/29</p></div>")
    recs = parse_role_then_name(bett)
    kept, _ = finish({"name": "Bettendorf", "roles": ("mayor", "council")}, recs)
    ck(names(kept) == ["Frank Baden", "Jerry Sechser"],
       "role-then-name: both members parsed (got %r)" % names(kept))
    ck(all(not looks_like_address(v) for r in kept for v in r.values()),
       "role-then-name: no field holds the home address")
    ck(kept[0].get("phone") == "(563) 344-2442" and kept[0].get("email") == "fbaden@example.gov",
       "role-then-name: phone and e-mail still reach the member past the address")
    ck(kept[1].get("seat") == "Ward 1",
       "role-then-name: the ward is read off the role (got %r)" % kept[1].get("seat"))

    # 3. THE COMMA, BOTH WAYS ROUND. Marshalltown writes `Name, Seat` and
    #    Davenport `Seat, Name`; one parser for both returns half of each.
    mtown = ("<div><p>Mike Ladehoff, Mayor</p><p>, term ending 12/31/29</p>"
             "<p>Greg Nichols, 3rd Ward</p><p>, term ending 12/31/29</p></div>")
    recs = parse_name_comma_seat(mtown)
    ck(names(recs) == ["Mike Ladehoff", "Greg Nichols"],
       "name,seat: parsed in the city's own order (got %r)" % names(recs))
    ck(parse_seat_comma_name(mtown) == [],
       "name,seat: the reversed parser finds nobody here, which is why both exist")
    daven = ("<div><p>At-Large, Kyle Gripp</p><p>Ward 1, Rick Dunn</p>"
             "<p>Ward 8, Matt Lienen</p></div>")
    recs = parse_seat_comma_name(daven)
    ck(names(recs) == ["Kyle Gripp", "Rick Dunn", "Matt Lienen"],
       "seat,name: parsed in the city's own order (got %r)" % names(recs))
    ck(parse_name_comma_seat(daven) == [],
       "seat,name: the forward parser finds nobody here")

    # 4. THE TWO-WAY DASH -- Cedar Falls writes the seat on the right for its
    #    wards and on the LEFT for its at-large members, in one list. A parser
    #    fixing the side returns five of seven.
    cf = ('<div><a href="/1105/Gil-Schultz1st-Ward">Gil Schultz—1st Ward</a>'
          '<a href="/873/At-LargeKelly-Dunn">At Large—Kelly Dunn</a>'
          '<a href="/69/Tom-Nagle3rd-Ward">Tom Nagle—3rd Ward</a></div>')
    recs = parse_link_dash_either(cf)
    ck(names(recs) == ["Gil Schultz", "Kelly Dunn", "Tom Nagle"],
       "two-way dash: both directions read (got %r)" % names(recs))
    ck([r.get("role") for r in recs][1] == "At Large",
       "two-way dash: the at-large row's role is the LEFT half")

    # 5. URBANDALE names nobody in its prose; the anchors are the roster.
    urb = ('<div><p>The Mayor and the five Councilmembers are the governing body.</p>'
           '<a href="/330/Bob-Andeweg---Mayor">Bob Andeweg - Mayor</a>'
           '<a href="/935/Blake-Rozendaal---Councilmember">Blake Rozendaal - Councilmember</a>'
           '<a href="/339/Boards-Commissions">Boards &amp; Commissions</a></div>')
    recs = parse_link_name_role(urb)
    ck(names(recs) == ["Bob Andeweg", "Blake Rozendaal"],
       "link name-role: the two seats, not the committee link (got %r)" % names(recs))

    # 6. THE STAFF TABLE is SURNAME FIRST, and the student liaisons below it
    #    are not on the council -- the Iowa City shape.
    ic = ("<div><p>Staff</p><p>Title</p><p>Phone</p><p>Email</p>"
          "<p>Teague, Bruce</p><p>Mayor, At-Large</p><p>(319) 536-1200</p>"
          "<p>bteague@example.gov</p>"
          "<p>Bergus, Laura</p><p>Councilor, District A</p><p>(319) 541-9677</p>"
          "<p>lbergus@example.gov</p>"
          "<p>Doe, Jane</p><p>USG Student Liaison</p><p>(319) 555-0000</p></div>")
    recs = parse_staff_table(ic)
    kept, dropped = finish({"name": "Iowa City", "roles": ("mayor", "council")}, recs)
    ck(names(kept) == ["Bruce Teague", "Laura Bergus"],
       "staff table: surnames flipped, liaison excluded (got %r)" % names(kept))
    ck(kept[1].get("seat") == "District A",
       "staff table: the lettered district is read (got %r)" % kept[1].get("seat"))
    ck(kept[0]["kind"] == "mayor",
       "staff table: `Mayor, At-Large` classifies as the mayor")

    # 7. DUBUQUE shares the role and name on one line, puts the seat beneath,
    #    and the home address beneath THAT.
    dbq = ("<div><p>Mayor Brad M. Cavanagh</p><p>565 Fenelon Place</p>"
           "<p>Dubuque, Iowa 52001</p><p>Phone: 563.690.6502</p>"
           "<p>bcavanagh@example.gov</p><p>Term Expires: Dec. 31, 2029</p>"
           "<p>Council Member Tyson J. Leyendecker</p><p>Ward One Representative</p>"
           "<p>1760 Overview Court</p><p>Dubuque, Iowa 52003</p>"
           "<p>Phone: 563.690.6505</p><p>tleyendecker@example.gov</p></div>")
    recs = parse_dubuque(dbq)
    kept, _ = finish({"name": "Dubuque", "roles": ("mayor", "council")}, recs)
    ck(names(kept) == ["Brad M. Cavanagh", "Tyson J. Leyendecker"],
       "dubuque: both parsed off the shared role/name line (got %r)" % names(kept))
    ck(kept[1].get("seat") == "Ward 1",
       "dubuque: `Ward One Representative` becomes Ward 1 (got %r)" % kept[1].get("seat"))
    ck(all(not looks_like_address(v) for r in kept for v in r.values()),
       "dubuque: neither home address reaches any field")

    # 8. AMES' EX-OFFICIO. Their own page gives the role as exactly
    #    `Ex-Officio`, and a card answering who represents you must not name
    #    the university's delegate.
    def ames_page(name, role):
        return ("<div><p>Municipal Code</p><p>%s</p><p>%s</p><p>Telephone</p>"
                "<p>515-232-2501</p><p>Email</p><p>x@example.gov</p></div>"
                % (name, role))
    pages = [("https://example.gov/My-Government/Mayor-and-City-Council/Tim-Gartin",
              ames_page("Tim Gartin", "Ward Two Representative 1st Term:")),
             ("https://example.gov/My-Government/Mayor-and-City-Council/Mayor-John-Haila",
              ames_page("John Haila", "Mayor")),
             ("https://example.gov/My-Government/Mayor-and-City-Council/Trey-Anderson",
              ames_page("Trey Anderson", "Ex-Officio"))]
    recs = parse_ames("", pages)
    ck(names(recs) == ["Tim Gartin", "John Haila", "Trey Anderson"],
       "ames: all three member pages read (got %r)" % names(recs))
    kept, dropped = finish({"name": "Ames", "roles": ("mayor", "council")}, recs)
    ck(names(kept) == ["Tim Gartin", "John Haila"],
       "ames: the Iowa State ex-officio is not on the card (got %r)" % names(kept))
    ck(any("Trey Anderson" in d for d in dropped),
       "ames: and the drop is printed rather than silent")
    ck(kept[0].get("seat") == "Ward 2",
       "ames: `Ward Two Representative` becomes Ward 2 (got %r)" % kept[0].get("seat"))
    links = ames_member_links(
        '<a href="/My-Government/Mayor-and-City-Council/Tim-Gartin">x</a>'
        '<a href="/My-Government/Mayor-and-City-Council/City-Council-Goals">y</a>'
        '<a href="/My-Government/Mayor-and-City-Council/Mayor-John-Haila">z</a>',
        "/My-Government/Mayor-and-City-Council")
    ck(links == ["/My-Government/Mayor-and-City-Council/Tim-Gartin",
                 "/My-Government/Mayor-and-City-Council/Mayor-John-Haila"],
       "ames: member links read off the page, the Goals page not among them")

    # 9. THE TWO DISCRIMINATORS THE REAL PAGES FOUND, gated directly rather
    #    than only through their effect. Both were measured on 2026-10-01
    #    against the fourteen cities' own pages, and each cost four cities a
    #    correct parse before it was fixed.
    for ward in ("3rd Ward", "1st Ward", "5TH WARD", "At-Large"):
        ck(not looks_like_address(ward),
           "address refusal: %r is a seat, not a street (a missing word "
           "boundary read the trailing `rd` as a road)" % ward)
    for addr in ("6859 Little Cabin Rd.", "922 North Green Street,",
                 "2341 Coventry Park, #207", "Ottumwa, IA 52501",
                 "565 Fenelon Place", "P.O. Box 811"):
        ck(looks_like_address(addr),
           "address refusal: %r is still refused" % addr)
    ck(split_role_name("COUNCIL MEMBER - AT LARGE") is None,
       "combined line: a seat after the office is NOT a person")
    ck(split_role_name("MAYOR ROBERT S. GALLAGHER") == ("Mayor", "Robert S. Gallagher"),
       "combined line: the capitals heading yields the office and the person (got %r)"
       % (split_role_name("MAYOR ROBERT S. GALLAGHER"),))
    ck(split_role_name("Council Member David T. Resnick") ==
       ("Council Member", "David T. Resnick"),
       "combined line: Dubuque's shape reads the same way")
    try:
        person_case("SEAN O'BRIEN")
        ck(False, "capitals: an apostrophe name must refuse rather than guess")
    except SystemExit:
        ck(True, "capitals: an apostrophe name refuses rather than shipping a misspelling")
    try:
        person_case("ANN MCGREW")
        ck(False, "capitals: a Mc name must refuse rather than ship `Mcgrew`")
    except SystemExit:
        ck(True, "capitals: a Mc name refuses rather than shipping `Mcgrew`")
    ck(NAME.match("Bill Hoffman, Jr.") is not None,
       "suffix: `Bill Hoffman, Jr.` is a name (Ottumwa shipped five of six without it)")
    for furniture in ("Our City", "About Us", "Upcoming Meetings", "Suite 102",
                      "Physical Address", "Contact Us"):
        ck(not name_like(furniture),
           "furniture: %r is not a person (it shipped as one before this test)"
           % furniture)
    for notrole in ("Mayor & City Council", "Council Meeting",
                    "City Council Special Meeting", "City Council Wards"):
        ck(classify(notrole) is None,
           "furniture: %r is a page label, not a role" % notrole)

    # 10. THE SEAT GATE AND THE MAYOR GATE both refuse rather than ship short.
    try:
        check({"name": "X", "seats": 6, "mayor": True},
              [{"name": "A", "role": "Council Member", "kind": "council"}])
        ck(False, "seat gate: a short parse must raise")
    except SystemExit:
        ck(True, "seat gate: a short parse raises rather than shipping")
    try:
        check({"name": "X", "seats": 1, "mayor": False},
              [{"name": "A", "role": "Mayor", "kind": "mayor"}])
        ck(False, "mayor gate: a mayor where the page names none must raise")
    except SystemExit:
        ck(True, "mayor gate: a mayor where the page names none raises")
    try:
        check({"name": "X", "seats": 1, "mayor": True},
              [{"name": "A", "role": "Mayor", "kind": "mayor",
                "phone": "565 Fenelon Place"}])
        ck(False, "address gate: an address in a field must raise")
    except SystemExit:
        ck(True, "address gate: an address in any field raises")

    # 11. THE ROLE VOCABULARY, across all fourteen cities' spellings. Council
    #     Bluffs writes the mayor's title with their SURNAME in it.
    for role, want in (("Mayor", "mayor"), ("Mayor Shudak", "mayor"),
                       ("Mayor, At-Large", "mayor"), ("Mayor Pro Tem", "council"),
                       ("Councilmember", "council"), ("Council Member", "council"),
                       ("City Councilmember", "council"), ("Councilor, District B", "council"),
                       ("COUNCIL MEMBER - AT LARGE", "council"), ("3rd Ward", "council"),
                       ("At Large", "council"), ("Ex-Officio", None),
                       ("Assistant to the Mayor", None), ("City Clerk", None),
                       ("USG Student Liaison", None)):
        ck(classify(role) == want,
           "vocabulary: %r classifies as %r (got %r)" % (role, want, classify(role)))

    print("%d checks, %d failed" % (len(ran), len(failures)))
    return 1 if failures else 0


# ----------------------------------------------------------------------- main
def fetch(session, gate, url, client):
    allowed, why = gate.allows(url)
    if not allowed:
        return None, why
    if client == "chrome":
        headers = dict(SC.UA_HINTS_CHROME_126)
        headers["User-Agent"] = SC.UA_CHROME_WIN_126
        return SC.fetch_stdlib(url, headers=headers), None
    r = session.get(url, headers=TOKEN_HEADERS, timeout=45)
    r.raise_for_status()
    return r.text, None


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    session = requests.Session()
    # ONE GATE PER CLIENT, because which group of a robots.txt binds depends on
    # the client that will crawl. The three Chrome-only cities have their
    # policy read with the Chrome client, which is the consistency rule.
    gates = {"token": RobotsGate(session, IA_TOKEN),
             "chrome": RobotsGate(session, SC.UA_CHROME_WIN_126)}
    payload, refused = {}, []

    for city in CITIES:
        gate = gates[city["client"]]
        body, why = fetch(session, gate, city["url"], city["client"])
        if body is None:
            refused.append((city["name"], why))
            print("  %-16s NOT FETCHED — %s" % (city["name"], why), file=sys.stderr)
            continue

        if city["shape"] == "ames":
            base = "/My-Government/Mayor-and-City-Council"
            pages = []
            for href in ames_member_links(body, base):
                full = href if href.startswith("http") else \
                    "https://www.cityofames.org" + href
                page, why = fetch(session, gate, full, city["client"])
                if page is not None:
                    pages.append((full, page))
            records = parse_ames(body, pages)
        else:
            records = PARSERS[city["shape"]](body)
            for extra in city.get("also", []):
                page, why = fetch(session, gate, extra, city["client"])
                if page is None:
                    print("  %-16s NOT FETCHED (%s) — %s" % (city["name"], extra, why),
                          file=sys.stderr)
                    continue
                records += PARSERS[city["shape"]](page)

        members, dropped = finish(city, records)
        check(city, members)
        for name in dropped:
            print("  %-16s not on the council, dropped: %s" % (city["name"], name),
                  file=sys.stderr)

        payload[city["geoid"]] = {
            "city": city["name"], "sourceUrl": city["url"],
            "namesMayor": city["mayor"], "members": members}
        print("  %-16s %d seats, %d e-mails, %d phones, %d with a seat named"
              % (city["name"], len(members),
                 sum(1 for m in members if m.get("email")),
                 sum(1 for m in members if m.get("phone")),
                 sum(1 for m in members if m.get("seat"))), file=sys.stderr)

    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")
    print("ia-city-councils: %d cities cached to %s (%d refused by robots.txt)"
          % (len(payload), OUT_PATH, len(refused)), file=sys.stderr)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    main()
