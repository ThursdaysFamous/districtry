#!/usr/bin/env python3
"""The town officers Minnesota counties publish for their own towns, read from
each county's own list: the board of supervisors, the clerk and the treasurer,
by name, office and (where the list prints one) the year the term ends.

WHY THIS EXISTS. mn/scripts/build_mn_town_boards.py names the boards of the 704
towns that hold their town election in November, from the Secretary of State's
results files. The other towns vote in March, run their own elections, and
appear in no file the state publishes (gap mn-township-officers). A town clerk
certifies the town's officers to the county auditor, and on 2026-10-15 a survey
of all 87 county websites (mn/data/source/mn-county-township-officer-survey.json)
found 42 counties that publish that list. This reads them.

WHAT IS KEPT AND WHAT IS NOT. These lists print each officer's home address,
telephone and e-mail beside the name. NONE OF THAT IS READ INTO THE OUTPUT: a
parser takes the office, the name and a term year and nothing else, and
`check_record` refuses a name carrying a digit, an "@", or a street word, so a
column that slips cannot carry an address through. The officers are private
people who hold a small public office; the office and the name are what a
reader asks for, and the rest stays on the county's page.

A LIST IS A DATED STATEMENT, NOT A LIVE ONE. Each county's list carries the
date it prints ("Updated as of 10/09/2026") where it prints one, and every town
read from it carries that date and the day this file read it, so the card can
say how old the list is.

ONE PARSER PER COUNTY. The 42 lists are 42 layouts — one-line rows, two-line
rows, tables, per-town pages, workbooks — so each county has a parse function
of its own over a small shared vocabulary (`pdf_lines`, `office_of`,
`tidy_name`). A county whose parse finds fewer towns than its floor fails ITSELF
and keeps its last-good record (the preservation ruling of 2026-09-19); the
others are written.

ROBOTS AND PACING. Every host is asked for its robots.txt before the first
fetch, through `scraper_common.require_robots_once`, and again at every
redirect hop, because several county sites redirect to a new domain. A host
that states a Crawl-delay is held to it. A refusal stops the fetch for that
county and is recorded as `robots-refused`, never worked around.

Usage:
    python3 mn/scripts/mn_county_town_officers_scraper.py            # fetch all
    python3 mn/scripts/mn_county_town_officers_scraper.py Beltrami   # one county
    python3 mn/scripts/mn_county_town_officers_scraper.py --cache DIR  # reuse saved bytes
"""

import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import requests  # noqa: E402

from scraper_common import require_robots_once  # noqa: E402
import robots_policy  # noqa: E402

USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
OUT_FILE = os.path.join(INSTANCE, "data", "source", "mn-county-town-officers.json")
TIMEOUT = 60
ATTEMPTS = 3


# ---------------------------------------------------------------- fetching

class Fetcher(object):
    """GET with robots.txt read at every host and redirect hop, a Crawl-delay
    held per host, and a few retries for the connection resets several county
    hosts answered with on 2026-10-15 and 2026-10-16."""

    def __init__(self, cache=None):
        self.session = requests.Session()
        self.gate = robots_policy.RobotsGate(None, USER_AGENT)
        self.last = {}
        self.cache = cache
        self.read = {}

    def _pace(self, url):
        host = urllib.parse.urlsplit(url).netloc
        delay = self.gate.crawl_delay(url) or 0
        wait = self.last.get(host, 0) + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        self.last[host] = time.time()

    def _cached(self, url):
        if not self.cache:
            return None
        path = os.path.join(self.cache, hashlib.sha256(url.encode()).hexdigest()[:24])
        return path

    def get(self, url):
        """The bytes at `url` and the final URL, following redirects by hand."""
        path = self._cached(url)
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                return fh.read(), url
        start = url
        for _ in range(6):
            require_robots_once(url, USER_AGENT)
            resp = None
            for attempt in range(ATTEMPTS):
                self._pace(url)
                try:
                    resp = self.session.get(url, headers={"User-Agent": USER_AGENT},
                                            timeout=TIMEOUT, allow_redirects=False)
                    break
                except requests.RequestException as exc:
                    if attempt == ATTEMPTS - 1:
                        raise
                    print("  retry %s after %s" % (url, type(exc).__name__),
                          file=sys.stderr)
                    time.sleep(4 * (attempt + 1))
            if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("location"):
                url = urllib.parse.urljoin(url, resp.headers["location"])
                continue
            if resp.status_code != 200:
                raise RuntimeError("HTTP %d from %s" % (resp.status_code, url))
            if path:
                with open(path, "wb") as fh:
                    fh.write(resp.content)
            self.read[start] = url
            return resp.content, url
        raise RuntimeError("more than five redirects from %s" % start)


# ---------------------------------------------------------------- vocabulary

OFFICES = [
    # (pattern at the start of a cell, canonical office). Order matters: the
    # longer phrase first, so "Deputy Clerk" is not read as "Clerk".
    (r"clerk\s*[-/&]\s*treas(?:urer)?", "Clerk-Treasurer"),
    (r"deputy\s+clerk", "Deputy Clerk"),
    (r"deputy\s+treas(?:urer)?", "Deputy Treasurer"),
    (r"vice[\s-]*chair(?:man|person|woman)?", "Supervisor (vice chair)"),
    (r"chair(?:man|person|woman)?(?:\s*/\s*supervisor)?", "Supervisor (chair)"),
    (r"supervisors?", "Supervisor"),
    (r"chm", "Supervisor (chair)"),
    (r"supv\.?", "Supervisor"),
    (r"clerk", "Clerk"),
    (r"treas(?:urer)?", "Treasurer"),
]
OFFICE_RE = [(re.compile(r"^\s*(%s)(?![@\w]|\.\w)\.?\s*(?:([A-E1-5])\b(?![a-z']))?[\s:,-]*" % p, re.I), o)
             for p, o in OFFICES]


def office_of(text):
    """(canonical office, seat label or None, rest of the text) when `text`
    begins with an office word, else None."""
    for rx, office in OFFICE_RE:
        m = rx.match(text)
        if m:
            seat = m.group(2)
            if seat and office.startswith("Supervisor"):
                return office, seat.upper(), text[m.end():].strip()
            return office, None, text[m.end():].strip() if not seat else (
                seat + text[m.end():]).strip()
    return None


STREET_WORDS = re.compile(
    r"\b(?:ave|avenue|st|street|rd|road|dr|drive|ln|lane|hwy|highway|blvd|"
    r"cir|ct|trl|trail|box|po|cr|csah|twp|township|nw|ne|sw|se|mn)\b\.?$", re.I)


def tidy_name(raw):
    """The name as the county prints it, with spacing and trailing punctuation
    cleaned and an all-capitals name put in ordinary case."""
    name = re.sub(r"\S+@\S+", " ", str(raw))  # an e-mail printed beside the name
    name = re.sub(r"\s+", " ", name).strip(" ,;:-*")
    name = re.sub(r"\s*\((?:appt|appointed|app't|apptd)\.?\)\s*$", "", name, flags=re.I)
    if name.isupper() and len(name) > 3:
        name = name_case(name)
    return name


def name_case(raw):
    out = []
    for word in raw.split():
        parts = []
        for piece in word.split("-"):
            low = piece.lower()
            if len(piece) <= 1:
                parts.append(piece.upper())
            elif len(piece) == 2 and piece.endswith("."):
                parts.append(piece.upper())
            elif low.startswith("mc") and len(piece) > 3:
                parts.append("Mc" + piece[2:].capitalize())
            elif low in ("ii", "iii", "iv"):
                parts.append(piece.upper())
            elif low.startswith("o'") and len(piece) > 2:
                parts.append("O'" + piece[2:].capitalize())
            else:
                parts.append(piece.capitalize())
        out.append("-".join(parts))
    return " ".join(out)


def check_record(county, town, rec):
    name = rec["name"]
    bad = None
    if not name or len(name) < 3:
        bad = "empty"
    elif re.search(r"\d|@|https?:|www\.", name):
        bad = "carries a digit, an address or a link"
    elif STREET_WORDS.search(name):
        bad = "ends in a street or place word"
    elif len(name.split()) < 2 or not re.search(r"[a-z]", name.split()[-1] + name.split()[0]):
        bad = "is not a whole name"
    elif re.match(r"^[A-Z]\.?$", name.split()[-1]) and not re.search(r"\b(?:Jr|Sr)", name):
        bad = "ends in an initial, so the surname was cut"
    elif re.search(r"\b(?:appointed|vacant|none|tbd|open|elected|interim)\b", name, re.I):
        bad = "is a status, not a name"
    elif len(name.split()) > 6:
        bad = "too many words"
    elif office_of(name):
        bad = "is an office word"
    if bad:
        raise ValueError("%s, %s: %s %r %s" % (county, town, rec["office"], name, bad))


def row(office, seat, name, term=None):
    rec = {"office": office, "name": tidy_name(name)}
    if seat:
        rec["seat"] = seat
    if term:
        rec["termEnds"] = str(term)
    return rec


def town_key(raw):
    """A town's name as a list prints it, reduced to the name itself."""
    name = re.sub(r"\s+", " ", raw).strip(" :*-–")
    name = re.sub(r"^(?:town(?:ship)?\s+of\s+)", "", name, flags=re.I)
    name = re.sub(r"\s+(?:town(?:ship)?|twp\.?)\b.*$", "", name, flags=re.I)
    return name.strip(" :*-–")


# ---------------------------------------------------------------- documents

def pdf_lines(data, gap=12, ytol=3):
    """Every line of a PDF as a list of (x0, text) cells, split where the gap
    between two words is wider than `gap` points. Pages are concatenated."""
    import pymupdf  # noqa: PLC0415
    doc = pymupdf.open(stream=data, filetype="pdf")
    out = []
    for page in doc:
        words = page.get_text("words")
        rows = {}
        for w in words:
            key = round((w[1] + w[3]) / 2 / ytol)
            rows.setdefault(key, []).append(w)
        for key in sorted(rows):
            ws = sorted(rows[key], key=lambda w: w[0])
            cells, cur, lastx = [], None, None
            for w in ws:
                if cur is None or w[0] - lastx > gap:
                    cur = [w[0], w[4]]
                    cells.append(cur)
                else:
                    cur[1] += " " + w[4]
                lastx = w[2]
            out.append([(c[0], c[1]) for c in cells])
    return out


def pdf_columns(data, cuts, ytol=3):
    """Every line of a PDF split into fixed columns at the x positions in
    `cuts`, for a table whose column gaps are too narrow to split on."""
    import pymupdf  # noqa: PLC0415
    doc = pymupdf.open(stream=data, filetype="pdf")
    out = []
    for page in doc:
        rows = {}
        for w in page.get_text("words"):
            rows.setdefault(round((w[1] + w[3]) / 2 / ytol), []).append(w)
        for key in sorted(rows):
            cols = [""] * (len(cuts) + 1)
            for w in sorted(rows[key], key=lambda w: w[0]):
                k = sum(1 for c in cuts if w[0] >= c)
                cols[k] = (cols[k] + " " + w[4]).strip()
            out.append(cols)
    return out


def nearest(x, columns, tol=40):
    """The column whose x is nearest `x`, within `tol` points."""
    best = min(columns, key=lambda c: abs(c[0] - x)) if columns else None
    return best if best and abs(best[0] - x) <= tol else None


def pdf_text(data):
    import pymupdf  # noqa: PLC0415
    doc = pymupdf.open(stream=data, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def soup(data):
    from bs4 import BeautifulSoup  # noqa: PLC0415
    return BeautifulSoup(data, "html.parser")


def first_date(text):
    """The first date a list prints, as ISO, or None."""
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b", text)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return datetime.date(y, mo, d).isoformat()
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------- counties
#
# Each parse function takes the Fetcher and returns (towns, as_of, urls):
# towns maps the town's name as printed to its officer records.

PARSERS = {}


def county(name, floor):
    def wrap(fn):
        PARSERS[name] = (fn, floor)
        return fn
    return wrap


def looks_like_name(text):
    return bool(text) and not re.search(r"\d|@|\[|\(", text) and not office_of(text) \
        and len(text.split()) <= 5


def alpha_prefix(text):
    """The leading words of a cell before its first digit: the surname a list
    printed against the street number without a column gap."""
    m = re.match(r"^([A-Za-z][A-Za-z.'\-]*(?: [A-Za-z][A-Za-z.'\-]*)?)\s+\d", text)
    return m.group(1) if m else None


def name_after(texts, i, rest):
    """The name that follows an office: the rest of the office's own cell, or
    the next cell, joined with the one after it when a list prints first and
    last names in separate columns."""
    if rest:
        name = rest
        nxt = texts[i + 1] if i + 1 < len(texts) else ""
        if len(name.split()) == 1 and looks_like_name(nxt) and len(nxt.split()) <= 2:
            name += " " + nxt
        return name
    if i + 1 >= len(texts):
        return ""
    name = texts[i + 1]
    nxt = texts[i + 2] if i + 2 < len(texts) else ""
    if len(name.split()) == 1 and looks_like_name(nxt) and len(nxt.split()) <= 2:
        name += " " + nxt
    elif len(name.split()) == 1 and alpha_prefix(nxt):
        name += " " + alpha_prefix(nxt)
    elif re.match(r"^[A-Za-z]", name) and alpha_prefix(name) and len(name.split()) > 2:
        name = alpha_prefix(name)
    return name


TERM_RE = re.compile(r"\b(20[2-3]\d)\b")


STOP_RE = re.compile(r"^\*?\s*(?:CITY OF\b|CITIES\b|City of [A-Z]|COUNTY OFFICIALS|SCHOOL DIST|"
                     r"Soil\b|SOIL\b|Watershed|WATERSHED|Hospital|HOSPITAL|Unorganized|UNORGANIZED)")


def generic(lines, header, name_side="after", term=None, term_ahead=0,
            office_anywhere=True, stop=STOP_RE):
    """The shape most lists share: a town header, then one line per officer
    carrying an office word and a name.

    header(texts) -> town name or None, and may leave the line to be read as
    an officer too by returning (town, True). name_side says whether the name
    follows the office or precedes it. term, a compiled regex with one group,
    is looked for on the officer's own line and on the next term_ahead lines.
    """
    towns, cur, last = {}, None, None
    ahead = 0
    for cells in lines:
        texts = [t.strip() for _, t in cells if t.strip()]
        if not texts:
            continue
        if stop and stop.match(texts[0]):
            cur = last = None
            continue
        hit = header(texts)
        if hit:
            town, also = hit if isinstance(hit, tuple) else (hit, False)
            cur = towns.setdefault(town, [])
            last = None
            if not also:
                continue
        if cur is None:
            continue
        found = None
        span = range(len(texts)) if office_anywhere else range(1)
        for i in span:
            h = office_of(texts[i])
            if h and (name_side == "after" or i > 0):
                found = (i, h)
                break
        if found:
            i, (office, seat, rest) = found
            if name_side == "after":
                name = name_after(texts, i, rest)
            else:
                name = texts[i - 1]
            rec = row(office, seat, name)
            if term:
                m = term.search(" ".join(texts[i + 1:]))
                if m:
                    rec["termEnds"] = m.group(1)
            cur.append(rec)
            last, ahead = rec, term_ahead
            continue
        if term and last is not None and ahead > 0 and "termEnds" not in last:
            m = term.search(" ".join(texts))
            if m:
                last["termEnds"] = m.group(1)
            ahead -= 1
    return towns


def caps_header(suffix=r"TOWNSHIP:?"):
    rx = re.compile(r"^\*?([A-Z][A-Z .'\-]+?)\s+" + suffix + r"(?:\s|$)")

    def header(texts):
        m = rx.match(texts[0])
        if m:
            return town_key(m.group(1)).title()
        return None
    return header


@county("Beltrami", 30)
def beltrami(f):
    url = "https://www.beltramicountymn.gov/media/e4vfs1jr/town-officers.pdf"
    data, final = f.get(url)
    lines = pdf_lines(data)
    return generic(lines, caps_header()), first_date(pdf_text(data)), [final]


@county("Benton", 12)
def benton(f):
    """A three-column table: the town and its meeting notes on the left, the
    office and the name in the middle, the term under the phone on the right.
    A two-word town name wraps ("SAUK RAPIDS" / "TOWNSHIP:"), and a town that
    runs onto a new page repeats its name with "(CONTINUED)"."""
    url = "https://www.bentoncountymn.gov/DocumentCenter/View/7294"
    data, final = f.get(url)
    lines = pdf_lines(data)
    left_rx = re.compile(r"^([A-Z][A-Z .']+?)\s*(?:TOWNSHIP|TWP)?\s*(?:\(CONTINUED\))?:?$")
    towns, cur, last = {}, None, None
    for k, cells in enumerate(lines):
        left = [t for x, t in cells if x < 150]
        rest = [t for x, t in cells if x >= 150]
        if left:
            first = left[0]
            # a cell that both names the town and starts the office column
            m = re.match(r"^([A-Z][A-Z .']+?)\s+(?:TOWNSHIP|TWP)(?:\s*\(CONTINUED\))?:\s*(.*)$", first)
            nxt = [t for x, t in lines[k + 1] if x < 150] if k + 1 < len(lines) else []
            name = None
            if m:
                name = m.group(1)
                if m.group(2):
                    rest = [m.group(2)] + rest
            elif re.match(r"^(?:TOWNSHIP|TWP)\b", nxt[0] if nxt else "") or \
                    (nxt and nxt[0].startswith("(CONTINUED")):
                mm = left_rx.match(first)
                if mm and not first.startswith(("MEETINGS", "TOWNSHIP", "DATE")):
                    name = mm.group(1)
            if name:
                cur = towns.setdefault(town_key(name).title(), [])
        if cur is None:
            continue
        texts = [t.strip() for t in rest if t.strip()]
        if not texts:
            continue
        h = office_of(texts[0])
        if h:
            office, seat, after = h
            last = row(office, seat, name_after(texts, 0, after))
            cur.append(last)
            m = re.search(r"TERM EXP\.?\s*(20\d\d)", " ".join(texts))
            if m:
                last["termEnds"] = m.group(1)
            continue
        m = re.search(r"TERM EXP\.?\s*(20\d\d)", " ".join(texts))
        if m and last is not None and "termEnds" not in last:
            last["termEnds"] = m.group(1)
    return towns, None, [final]


@county("Brown", 16)
def brown(f):
    url = "https://www.co.brown.mn.us/DocumentCenter/View/3614"
    data, final = f.get(url)
    # "*ALBIN TOWNSHIP – Mail Ballot", "*November Election – LINDEN TOWNSHIP";
    # the word TOWNSHIP is sometimes not in the text layer ("*STARK")
    rx = re.compile(r"^\*?(?:[^–]*Election[^–]*–\s*)?([A-Z][A-Z .']{2,}?)"
                    r"(?:\s*TOWNSHIP)?\s*(?:–.*)?$")

    def header(texts):
        m = rx.match(texts[0])
        if m and not office_of(texts[0]) and "OFFICIALS" not in texts[0]:
            return town_key(m.group(1)).title()
        return None
    lines = pdf_lines(data)
    # the township section ends where the city listing begins
    return generic(lines, header, office_anywhere=False), None, [final]


@county("Carlton", 15)
def carlton(f):
    url = "https://www.co.carlton.mn.us/DocumentCenter/View/6572"
    data, final = f.get(url)
    rx = re.compile(r"^Township of (.+)$")

    def header(texts):
        m = rx.match(texts[0])
        return town_key(m.group(1)) if m else None
    towns = generic(pdf_lines(data), header, term=re.compile(r"(?:^|\s)(20[2-3]\d)$"),
                    office_anywhere=False)
    return towns, first_date(pdf_text(data)), [final]


@county("Stevens", 10)
def stevens(f):
    url = "https://www.co.stevens.mn.us/DocumentCenter/View/5016"
    data, final = f.get(url)
    lines = pdf_lines(data)
    towns, cur = {}, None
    for cells in lines:
        texts = [t.strip() for _, t in cells if t.strip()]
        if not texts:
            continue
        if re.match(r"^CITY OF\b|^CITIES\b", texts[0]):
            cur = None
            break
        if len(texts) == 1 and re.match(r"^[A-Z][A-Z .'\-]+$", texts[0]) \
                and not office_of(texts[0]) and "COUNTY" not in texts[0]:
            cur = towns.setdefault(town_key(texts[0]).title(), [])
            continue
        if cur is not None and len(texts) >= 2:
            h = office_of(texts[1])
            if h:
                rec = row(h[0], h[1], texts[0])
                m = re.search(r"(20[2-3]\d)\s*$", " ".join(texts[2:]))
                if m:
                    rec["termEnds"] = m.group(1)
                cur.append(rec)
    return towns, None, [final]


@county("Chippewa", 12)
def chippewa(f):
    url = "https://www.chippewacountymn.gov/DocumentCenter/View/4462/2026-Town-Board-List"
    data, final = f.get(url)

    def header(texts):
        t = texts[0]
        if len(texts) == 1 and re.match(r"^[A-Z][A-Z .'\-]+$", t) and \
                not re.search(r"COUNTY|OFFICE|TOWNSHIP OFFICERS", t):
            return town_key(t).title()
        return None
    towns = generic(pdf_lines(data), header, term=re.compile(r"\b(20[2-3]\d)\s*$"),
                    office_anywhere=False)
    return towns, None, [final]


@county("Waseca", 10)
def waseca(f):
    url = "https://www.wasecacounty.gov/DocumentCenter/View/219/ELECTED-OFFICIALS"
    data, final = f.get(url)
    rx = re.compile(r"^(.+?) Township$")

    def header(texts):
        m = rx.match(texts[0])
        return town_key(m.group(1)) if m else None
    towns = generic(pdf_lines(data), header, name_side="before",
                    term=re.compile(r"^(20[2-3]\d)\b"))
    m = re.search(r"Current as of\s*:?\s*(\d{1,2})-([A-Za-z]{3})-(\d{2})", pdf_text(data))
    as_of = None
    if m:
        as_of = datetime.datetime.strptime("%s-%s-%s" % m.groups(), "%d-%b-%y").date().isoformat()
    return towns, as_of, [final]


@county("Steele", 12)
def steele(f):
    url = ("https://steelecountymn.gov/Documents/Your%20Government/"
           "Township%20Officials/26TWPOFF.pdf")
    data, final = f.get(url)

    def header(texts):
        if len(texts) >= 2 and re.match(r"^[A-Z][A-Z .']+$", texts[0]) and \
                re.match(r"^[\d-]+$", texts[1]) and not office_of(texts[0]):
            return town_key(texts[0]).title()
        return None
    towns = generic(pdf_lines(data), header, term=re.compile(r"\b(20[2-3]\d)\s*$"),
                    office_anywhere=False)
    return towns, None, [final]


@county("Lincoln", 12)
def lincoln(f):
    url = ("https://www.co.lincoln.mn.us/Documents/Lincoln%20County%20Information/"
           "Cities%20and%20Townships/Township%20Board%20Listing.pdf")
    data, final = f.get(url)
    towns, cur = {}, None
    office_rx = re.compile(r"(?:^|\s)(Chairman|Chair|Vice Chair|Supervisor|Clerk/Treasurer|"
                           r"Clerk|Treasurer|Deputy Clerk)\s*$")
    for cells in pdf_lines(data):
        if not cells:
            continue
        x0, t0 = cells[0]
        texts = [t for _, t in cells]
        start = 0
        if x0 < 100 and "@" not in t0 and not re.search(r"\d", t0) and len(texts) > 1 \
                and looks_like_name(texts[1]):
            cur = towns.setdefault(town_key(re.sub(r"\s+Twp\.?$", "", t0)), [])
            start = 1
        if cur is None:
            continue
        hit = None
        for k, t in enumerate(texts):
            m = office_rx.search(t)
            if m:
                hit = (k, m.group(1))
        if not hit:
            continue
        name = None
        for t in texts[start:hit[0]]:
            cand = tidy_name(t)
            if looks_like_name(cand) and len(cand.split()) >= 2:
                name = cand
                break
        if not name:
            continue
        office, seat, _ = office_of(hit[1])
        rec = row(office, seat, name)
        m = re.search(r"\b(20[2-3]\d)\s*$", texts[-1])
        if m:
            rec["termEnds"] = m.group(1)
        cur.append(rec)
    m = re.search(r"(20\d\d) Township Listing", pdf_text(data))
    return towns, (m.group(1) if m else None), [final]


@county("Morrison", 25)
def morrison(f):
    url = "https://morrisoncountymn.gov/DocumentCenter/View/1146/2026-Elected-Officials"
    data, final = f.get(url)
    towns = {}
    for cells in pdf_lines(data):
        texts = [t for _, t in cells]
        if len(texts) < 4:
            continue
        m = re.match(r"^(.+?) Township\b", texts[0])
        if not m or texts[1] not in ("March", "November"):
            continue
        h = office_of(texts[2])
        if not h:
            continue
        rec = row(h[0], h[1], texts[3])
        t = re.search(r"\b20[2-3]\d-(20[2-3]\d)\s*$", " ".join(texts[4:]))
        if t:
            rec["termEnds"] = t.group(1)
        towns.setdefault(town_key(m.group(1)), []).append(rec)
    return towns, None, [final]


@county("Roseau", 20)
def roseau(f):
    url = ("https://www.roseaucountymn.gov/Documents/Community/Township/"
           "2026Township%20Officers.pdf")
    data, final = f.get(url)
    lines = pdf_lines(data)
    towns, cur, offices = {}, None, None
    for k, cells in enumerate(lines):
        texts = [t for _, t in cells]
        # A town's heading is a lone word at the left margin, and the
        # "November Election" / "MB" note beside it sometimes lands on the
        # same text line and sometimes on the next.
        if cells[0][0] < 40 and re.match(r"^[A-Z][A-Za-z .']+$", texts[0]) \
                and texts[0] not in ("Email:",) and not texts[0].startswith("*") \
                and k + 1 < len(lines):
            beside = " ".join(texts[1:])
            nxt = " ".join(t for _, t in lines[k + 1])
            if all(re.match(r"^(?:(?:November|March) Election|MB)$", t) for t in texts[1:]) \
                    and ("Election" in beside or "Election" in nxt or "MB" in beside):
                cur = towns.setdefault(town_key(texts[0]), [])
                offices = None
                continue
        if cur is None:
            continue
        if all(office_of(t) for t in texts) and len(texts) >= 3:
            offices = [(x, office_of(t)) for x, t in cells]
            continue
        if offices and not cur and all(
                looks_like_name(tidy_name(t.lstrip("* "))) or t.startswith("*") for t in texts):
            for x, t in cells:
                col = nearest(x, offices)
                if not col:
                    continue
                office, seat, _ = col[1]
                if t.startswith("*") and office == "Supervisor":
                    office = "Supervisor (chair)"
                cur.append(row(office, seat, t.lstrip("* ")))
                cur[-1]["_x"] = x
            continue
        head = texts[0].lower() if texts else ""
        if cur and (head.startswith("term expires") or head.startswith("current term")):
            # "term expires 2028" names the year a term ends; "Current Term
            # 2025-2028" a range whose second year is the end.  A bare
            # "Current Term 2028" could be either end and is not read.
            line = " | ".join(texts)
            if head.startswith("term expires"):
                years = re.findall(r"20[2-3]\d", line)
            else:
                years = re.findall(r"20[2-3]\d\s*-\s*(20[2-3]\d)", line)
            if len(years) == len(cur):
                for rec, year in zip(sorted(cur, key=lambda r: r["_x"]), years):
                    rec["termEnds"] = year
    for recs in towns.values():
        for rec in recs:
            rec.pop("_x", None)
    m = re.search(r"Listing as of ([A-Z][a-z]+) (\d{4})", pdf_text(data))
    return towns, (m.group(2) + "-" + "%02d" % (datetime.datetime.strptime(m.group(1), "%B").month)
                   if m else None), [final]


@county("Marshall", 40)
def marshall(f):
    url = ("https://www.marshallcountymn.gov/Residents%20Visitors/"
           "Township%20City%20and%20County%20Officials%20List%20May%202026.pdf")
    data, final = f.get(url)
    lines = pdf_lines(data)
    towns = {}
    for k in range(len(lines) - 2):
        texts = [t for _, t in lines[k]]
        if len(texts) < 3 or len(set(texts)) != 1:
            continue
        head = " | ".join(t for _, t in lines[k + 1])
        if "TOWNSHIP" not in head:
            continue
        offices = re.findall(r"TOWNSHIP (SUPERVISOR-SEAT [A-C]|SUPERVISOR|TREASURER|CLERK-TREASURER|"
                             r"CLERK/TREASURER|CLERK)", head)
        names = [t for _, t in lines[k + 2]]
        if len(offices) != len(names):
            print("  Marshall %s: %d offices, %d names; skipped" % (texts[0], len(offices),
                                                                    len(names)), file=sys.stderr)
            continue
        recs = []
        for o, n in zip(offices, names):
            m = re.match(r"SUPERVISOR-SEAT ([A-C])", o)
            office = "Supervisor" if m or o == "SUPERVISOR" else office_of(o)[0]
            recs.append(row(office, m.group(1) if m else None, n))
        towns[town_key(texts[0]).title()] = recs
    m = re.search(r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, 20\d\d)\b",
                  pdf_text(data))
    as_of = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat() if m else None
    return towns, as_of, [final]


@county("Pennington", 12)
def pennington(f):
    url = "https://co.pennington.mn.us/images/2025/Township%20Officers%20-%202025.pdf"
    data, final = f.get(url)
    lines = pdf_lines(data)
    header = None
    towns = {}
    for cells in lines:
        texts = [t for _, t in cells]
        if len(texts) >= 4 and all(office_of(t) for t in texts):
            header = [(x, office_of(t)) for x, t in cells]
            continue
        if header and len(cells) >= 3 and cells[0][0] < 40 and \
                re.match(r"^[A-Z][A-Za-z .']+\*?$", texts[0]) and \
                all(looks_like_name(t) for t in texts[1:]):
            recs = []
            for x, t in cells[1:]:
                col = nearest(x, header, tol=60)
                if col:
                    recs.append(row(col[1][0], col[1][1], t))
            towns[town_key(texts[0].rstrip("*"))] = recs
    return towns, "2025", [final]


@county("Le Sueur", 10)
def le_sueur(f):
    url = "https://www.lesueurcounty.gov/DocumentCenter/View/7197"
    data, final = f.get(url)
    towns, cur, prev = {}, None, None
    for left, pos, seat, name, *_ in pdf_columns(data, [140, 200, 228, 325]):
        h = office_of(pos) if pos else None
        if not h:
            continue
        office = h[0]
        # a block starts with its first supervisor after the last block's
        # treasurer; the town is printed in the left column on that line
        if left and re.match(r"^[A-Z][a-z]+(?: [A-Z][a-z]+)*$", left) and \
                (prev is None or prev.startswith(("Treasurer", "Clerk-Treasurer"))):
            cur = towns.setdefault(left, [])
        prev = office
        if cur is None or not name:
            continue
        cur.append(row(office, seat.strip() or None if office == "Supervisor" else None, name))
    return towns, first_date(pdf_text(data)), [final]


@county("Norman", 15)
def norman(f):
    url = "https://www.normanmn.gov/Documents%20Center/Department/Township%20Officers.pdf"
    data, final = f.get(url)
    towns, cur, header, last = {}, None, None, []
    for cells in pdf_lines(data):
        texts = [t for _, t in cells]
        if "Mayor" in texts:
            break  # the cities follow the townships, under a Mayor header
        if len(texts) >= 3 and all(office_of(t) for t in texts):
            header = [(x, office_of(t)) for x, t in cells]
            continue
        if header is None:
            continue
        if len(cells) == 1 and cells[0][0] < 60 and re.match(r"^[A-Z][A-Za-z .']+$", texts[0]):
            cur = towns.setdefault(town_key(texts[0]), [])
            last = []
            continue
        if cur is None:
            continue
        if texts[0].startswith("End of Term"):
            for (x, t), rec in zip(cells, last):
                m = re.search(r"/(20[2-3]\d)", t)
                if m:
                    rec["termEnds"] = m.group(1)
            last = []
            continue
        if all(looks_like_name(t) and len(t.split()) >= 2 for t in texts):
            last = []
            for x, t in cells:
                col = nearest(x, header, tol=80)
                if col:
                    rec = row(col[1][0], col[1][1], t)
                    cur.append(rec)
                    last.append(rec)
    m = re.search(r"Township Officers\s+(20\d\d)\b", pdf_text(data))
    return towns, (m.group(1) if m else None), [final]


@county("Clay", 15)
def clay(f):
    # One table per township: a row of offices, a row of names, then "Term
    # Limit: 2027" under some of them (the year the term ends), then the
    # officers' mailing addresses, which are not read.
    data, final = f.get("https://claycountymn.gov/277/Townships")
    page = soup(data)
    towns = {}
    for table in page.find_all("table"):
        title = table.find_previous(string=re.compile(r"^\s*[A-Z][A-Za-z .']+ Township\s*$"))
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                for tr in table.find_all("tr")]
        if not title or len(rows) < 2 or not all(office_of(t) for t in rows[0] if t):
            continue
        terms = rows[2] if len(rows) > 2 and any(t.startswith("Term") for t in rows[2]) else []
        recs = towns.setdefault(town_key(title), [])
        for i, (head, name) in enumerate(zip(rows[0], rows[1])):
            if not head or not name:
                continue
            office, seat, _ = office_of(head)
            m = TERM_RE.search(terms[i]) if i < len(terms) else None
            recs.append(row(office, seat, name, m.group(1) if m else None))
    return towns, None, [final]


@county("Kanabec", 12)
def kanabec(f):
    # One table of townships and cities together: town, first name, last
    # name, position, then a telephone and an e-mail that are not read.  A
    # place with a Mayor or Council row is a city and is left out whole.
    data, final = f.get("https://www.kanabeccounty.org/community/township_information/index.php")
    page = soup(data)
    rows = []
    for tr in page.find_all("tr"):
        cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True).replace("\xa0", " "))
                 for td in tr.find_all("td")]
        if len(cells) >= 4 and cells[0] and cells[0] != "TOWNSHIP":
            rows.append(cells)
    cities = {c[0] for c in rows if re.match(r"^(?:Mayor|Council)", c[3])}
    towns = {}
    for place, first, last, position in (c[:4] for c in rows):
        if place in cities:
            continue
        hit = office_of(position)
        if not hit or hit[0].startswith("Deputy"):
            continue
        towns.setdefault(town_key(place), []).append(
            row(hit[0], hit[1], first + " " + last))
    m = re.search(r"\b(20\d\d) TOWNSHIP & CITY OFFICERS", page.get_text(" "))
    return towns, (m.group(1) if m else None), [final]


def xlsx_rows(data):
    import io  # noqa: PLC0415
    import openpyxl  # noqa: PLC0415
    book = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    return [["" if c is None else c for c in r] for r in book.worksheets[0].iter_rows(values_only=True)]


def office_cell(text):
    """office_of, also reading "Town Clerk" and a trailing "(Chair)"."""
    text = re.sub(r"^Town\s+", "", str(text).strip())
    hit = office_of(text)
    if hit and hit[0] == "Supervisor" and re.search(r"\(chair", hit[2], re.I):
        hit = ("Supervisor (chair)", hit[1], "")
    return hit


@county("Red Lake", 8)
def red_lake(f):
    # One sheet: township in the first column on a town's first row only,
    # with "B" or "March elections" notes under it; then office, name, a
    # telephone, the term as "2024-2027", an address and an e-mail.  Only
    # office, name and the term's last year are read.
    data, final = f.get("https://www.redlakecounty.gov/Documents/Government/"
                        "Township%20Officers%202025.xlsx")
    rows = xlsx_rows(data)
    towns, cur = {}, None
    for r in rows:
        place, office, name, _phone, term = (str(c).strip() for c in (r + [""] * 5)[:5])
        hit = office_cell(office)
        if place and hit and hit[0] == "Supervisor (chair)":
            # Some towns carry a letter after the name ("Equality A").
            cur = towns.setdefault(re.sub(r"\s+[A-E]$", "", town_key(place)), [])
        if cur is None or not hit or not name:
            continue
        m = re.search(r"20[2-3]\d\s*-\s*(20[2-3]\d)", term)
        cur.append(row(hit[0], hit[1], name, m.group(1) if m else None))
    title = " ".join(str(c) for r in rows[:3] for c in r)
    m = re.search(r"TOWNSHIP OFFICERS\s+(20\d\d)", title)
    return towns, (m.group(1) if m else None), [final]


@county("Itasca", 30)
def itasca(f):
    # One sheet: township on a town's first row, the town hall's address and
    # an "Upd. 1/27/26" note down the next column; then position, the date the
    # term ends ("Appt." for an appointed clerk), first and last name, and a
    # telephone and e-mail that are not read.
    data, final = f.get("https://www.itascacountymn.gov/DocumentCenter/View/12319/Township-Officials")
    rows = xlsx_rows(data)
    towns, cur, updated, key = {}, None, {}, None
    for r in rows[1:]:
        r = (r + [""] * 8)[:8]
        place = str(r[0]).strip()
        if place.startswith("Upd"):
            d = first_date(place)
            if d and key:
                updated[key] = d
            place = ""
        if place:
            key = town_key(place)
            cur = towns.setdefault(key, [])
        hit = office_cell(r[2])
        if cur is None or not hit or hit[0].startswith("Deputy"):
            continue
        name = (str(r[4]).strip() + " " + str(r[5]).strip()).strip()
        name = re.sub(r"\s*\([^)]*\)", "", name)  # a nickname in brackets
        term = r[3].year if isinstance(r[3], datetime.datetime) else None
        if name:
            cur.append(row(hit[0], hit[1], name, term))
    # Each town carries its own "Upd." date, so each town is dated by its own.
    return towns, updated, [final]


@county("Polk", 40)
def polk(f):
    # Columns: township, clerk, the clerk's term, treasurer, the treasurer's
    # term, chair and supervisors ("Name - Chairperson"), the supervisor's
    # term, then each officer's address, which is not read.  A town's name
    # stands on its first line; "November" / "Election" notes sit under it.
    data, final = f.get("https://www.co.polk.mn.us/DocumentCenter/View/3712/Township-Officers-2026")
    towns, cur = {}, None

    # The year beside each name is not labelled, and the list carries years
    # that have passed (a treasurer's 2024 on a 2026 list) beside ones six
    # years out, so it is not read as the year a term ends.
    def term_of(text):
        return None

    for cols in pdf_columns(data, [95, 200, 235, 362, 398, 532, 566]):
        town, clerk, cterm, treas, tterm, sup, sterm = cols[:7]
        if "TOWNSHIP" in town or "POLK COUNTY" in " ".join(cols):
            continue
        if town and not re.match(r"^(?:November|March|Election)", town) and looks_like_name(clerk):
            cur = towns.setdefault(town_key(town), [])
            for office, name, term in (("Clerk", clerk, cterm), ("Treasurer", treas, tterm)):
                name = re.sub(r"^Appointed\s+", "", name)
                if looks_like_name(name):
                    cur.append(row(office, None, name, term_of(term)))
        if cur is None:
            continue
        sup = re.sub(r"^Appointed\s+", "", sup.strip())
        m = re.match(r"^(.+?)\s*-\s*(Chairperson|Chair|Supervisor)\b", sup)
        name = m.group(1) if m else sup
        if name and looks_like_name(name) and not re.search(r"@|\d", sup) \
                and len(name.split()) >= 2:
            office = "Supervisor (chair)" if m and m.group(2).startswith("Chair") else "Supervisor"
            cur.append(row(office, None, name, term_of(sterm)))
    return towns, "2026", [final]


@county("Meeker", 15)
def meeker(f):
    # Each township is three supervisor lines ("2025-2028 A Name, Ch., then
    # the supervisor's address"); the first carries the clerk and treasurer
    # ("2026-2027 Name (phone)") and the second the town's name.  Only the
    # name before the first comma, the seat letter, "Ch." and each term's
    # last year are read.  The cities follow under a CITY header.
    data, final = f.get("https://www.meekercountymn.gov/DocumentCenter/View/8143/"
                        "Township--City-Officers-Listing-Feb-2-2026")
    # A supervisor cell starts with its term, its seat letter or both (one
    # town prints the letter on a line of its own), never with neither: a
    # bare "Name, ..." cell is an address.
    sup_re = re.compile(r"^(?:(?:\d{4}-(\d{4}) )([A-E] )?|([A-E] ))#?"
                        r"([^,(]+(?:\([^)]*\)[^,]*)?),\s*(Ch\.)?")
    off_re = re.compile(r"^(?:\d{4}-(\d{4})|N/A) #?([A-Z][^()]+?)\s*\(\d{3}\)")
    town_re = re.compile(r"^(?:\d+ )?([A-Z][A-Z .]{2,}?)[*& ]*$")
    towns, block = {}, None
    for cells in pdf_lines(data):
        texts = []
        for _, t in cells:  # a term or "N/A" printed apart from its name
            if texts and re.match(r"^(?:\d{4}-\d{4}|N/A)$", texts[-1]):
                texts[-1] += " " + t
            else:
                texts.append(t)
        if texts and texts[0].startswith("CITY"):
            break
        offs = [m for m in (off_re.match(t) for t in texts) if m]
        if len(offs) == 2:
            block = []
            for office, m in zip(("Clerk", "Treasurer"), offs):
                block.append(row(office, None, m.group(2), m.group(1)))
        if block is None:
            continue
        for t in texts:
            m = town_re.match(t)
            if m and t is texts[0] and cells[0][0] < 40:
                towns[town_key(m.group(1).title())] = block
            m = sup_re.match(t)
            if m:
                office = "Supervisor (chair)" if m.group(5) else "Supervisor"
                nm = re.sub(r"\s*\([^)]*\)", "", m.group(4))
                seat = (m.group(2) or m.group(3) or "").strip() or None
                block.append(row(office, seat, nm, m.group(1)))
    m = re.search(r"Last Updated\s+\w+\s+(\d{1,2}),\s*(20\d\d)", pdf_text(data))
    return towns, ("%s-02-%02d" % (m.group(2), int(m.group(1))) if m else None), [final]


@county("Watonwan", 10)
def watonwan(f):
    # One table per township, headed by the town's name: "Name-Office", then
    # an address and a telephone that are not read.
    data, final = f.get("https://www.co.watonwan.mn.us/122/Township-Officials")
    towns = {}
    for table in soup(data).find_all("table"):
        title = table.find_previous(string=re.compile(r"\S")).strip()
        recs = towns.setdefault(town_key(title), [])
        for tr in table.find_all("tr")[1:]:
            cell = tr.find(["td", "th"])
            m = re.match(r"^(.+?)\s*-\s*([A-Za-z/ ]+)$", cell.get_text(" ", strip=True)) if cell else None
            hit = office_cell(m.group(2)) if m else None
            if hit:
                recs.append(row(hit[0], hit[1], m.group(1)))
    return towns, None, [final]


@county("Wadena", 12)
def wadena(f):
    # One table naming each township's clerk, beside a telephone not read.
    data, final = f.get("https://www.co.wadena.mn.us/273/Wadena-County-Townships")
    towns = {}
    for table in soup(data).find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                for tr in table.find_all("tr")]
        if not rows or rows[0][:2] != ["Township", "Clerk"]:
            continue
        for r in rows[1:]:
            if len(r) >= 2 and r[0] and r[1]:
                towns[town_key(r[0])] = [row("Clerk", None, r[1])]
    return towns, None, [final]


def page_lines(data):
    page = soup(data)
    for t in page(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    return [re.sub(r"[ \t\xa0]+", " ", ln).strip() if not re.search(r"\s{2,}\S", ln.strip())
            else ln.strip() for ln in page.get_text("\n").splitlines() if ln.strip()]


def label_pairs(lines, term=False):
    """Officers from a page that prints each office as a line of its own
    ("Clerk", "Supervisor (A)", "Township Treasurer:") with the officer's
    name on the next line, the name ending where a telephone, a run of
    spaces or an address begins.  With `term`, a "6/2027" line before the
    next office is read as the month and year the term expires."""
    out = []
    for i, line in enumerate(lines[:-1]):
        label = re.sub(r"^Township\s+", "", line).rstrip(": ")
        hit = office_cell(label)
        if not hit or len(label) > 40:
            continue
        seat = hit[1]
        m = re.match(r"^\(([A-E1-5])\)$", hit[2])
        if hit[2] and not m:
            continue
        seat = seat or (m.group(1) if m else None)
        name = re.split(r"\s{2,}|\s*\(?\d|\s+-\s+", lines[i + 1])[0].strip()
        if not (looks_like_name(name) and len(name.split()) >= 2):
            continue
        year = None
        if term:
            for nxt in lines[i + 2:i + 8]:
                if office_cell(nxt):
                    break
                t = re.match(r"^\d{1,2}/(20[2-3]\d)$", nxt)
                if t:
                    year = t.group(1)
                    break
        out.append(row(hit[0], seat, name, year))
    return out


def per_page(f, index_url, link_re, term=False):
    """A county that gives each township a page of its own, linked from one
    index: every link matching `link_re` is read, and its link text names
    the town."""
    data, final = f.get(index_url)
    links, seen = [], set()
    page = soup(data)
    base = page.find("base", href=True)
    base = urllib.parse.urljoin(final, base["href"]) if base else final
    for a in page.find_all("a", href=True):
        href = urllib.parse.urljoin(base, a["href"])
        if re.search(link_re, href) and href not in seen and a.get_text(strip=True):
            seen.add(href)
            links.append((a.get_text(" ", strip=True), href))
    # The index is the list's address; each town's own page is where its
    # names were read, kept beside it under the town's name.
    towns, urls = {}, {"": final}
    for text, href in links:
        body, page_url = f.get(href)
        recs = label_pairs(page_lines(body), term=term)
        if recs:
            key = town_key(re.sub(r"\s+\d+-\d+$", "", text))
            towns[key] = recs
            urls[key] = page_url
    return towns, urls


@county("Aitkin", 30)
def aitkin(f):
    towns, urls = per_page(f, "https://www.aitkincountymn.gov/towns/", r"/towns/towns-[\w-]+-twp\.php$")
    return towns, None, urls


@county("Cottonwood", 15)
def cottonwood(f):
    towns, urls = per_page(f, "https://www.cottonwoodcountymn.gov/government/township_officials/index.php",
                           r"/township_officials/(?!index)[\w-]+\.php$")
    return towns, None, urls


@county("Dodge", 10)
def dodge(f):
    # Each page prints a "Term Expires" column as month and year.
    towns, urls = per_page(f, "https://www.co.dodge.mn.us/government/townships.php",
                           r"/government/\w+_township\.php$", term=True)
    return towns, None, urls


@county("Grant", 14)
def grant(f):
    towns, urls = per_page(f, "https://www.grantcountymn.gov/580/County-Township-Boards",
                           r"/\d+/[A-Z][\w-]+-\d+-\d+$")
    return towns, None, urls


@county("Otter Tail", 55)
def otter_tail(f):
    towns, urls = per_page(f, "https://ottertailcounty.gov/townships/",
                           r"ottertailcounty\.gov/township/[\w-]+/?$")
    return towns, None, urls


@county("Faribault", 15)
def faribault(f):
    # A table set sideways on the page: each row is a column of text lines
    # reading upwards.  Cells, in order: township, title, name, then home
    # and township mailing addresses and a telephone, which are not read.
    import pymupdf  # noqa: PLC0415
    data, final = f.get("https://www.faribaultcountymn.gov/DocumentCenter/View/250/Township-Officers")
    towns = {}
    for page in pymupdf.open(stream=data, filetype="pdf"):
        rows = {}
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                if tuple(round(v) for v in line["dir"]) != (0, -1):
                    continue
                text = " ".join(sp["text"] for sp in line["spans"]).strip()
                rows.setdefault(round(line["bbox"][0] / 4), []).append((-line["bbox"][3], text))
        for key in sorted(rows):
            cells = [t for _, t in sorted(rows[key])]
            if len(cells) < 3 or cells[0] == "Township":
                continue
            hit = office_cell(cells[1])
            if hit:
                name = re.sub(r"\s*\([^)]*\)", "", cells[2])
                towns.setdefault(town_key(cells[0]), []).append(row(hit[0], hit[1], name))
    # The page carries no date; the file's own title ("Township Officers 2025
    # BD.xlsx", from the spreadsheet it was printed from) names the year.
    m = re.search(r"Township Officers (20\d\d)", pymupdf.open(stream=data, filetype="pdf").metadata.get("title") or "")
    return towns, (m.group(1) if m else None), [final]


# ---------------------------------------------------------------- main

def run_county(name, f):
    fn, floor = PARSERS[name]
    towns, as_of, urls = fn(f)
    # A record whose name fails the check is DROPPED and printed rather than
    # shipped: a column that slipped (an interim officer whose office wraps to
    # the next line beside an address) loses one name, never prints a street.
    total = dropped = 0
    for town in list(towns):
        keep = []
        for rec in towns[town]:
            total += 1
            try:
                check_record(name, town, rec)
                keep.append(rec)
            except ValueError as exc:
                dropped += 1
                print("  dropped: %s" % re.sub(r"'[^']*'", "'…'", str(exc)), file=sys.stderr)
        towns[town] = keep
    towns = {t: recs for t, recs in towns.items() if recs}
    if total and dropped > max(2, total // 20):
        raise ValueError("%s: %d of %d records failed the name check" % (name, dropped, total))
    if len(towns) < floor:
        raise ValueError("%s: %d towns read, floor %d" % (name, len(towns), floor))
    out = {"towns": towns, "asOf": as_of, "urls": urls}
    if isinstance(urls, dict):  # a county with a page per town
        out["urls"] = [urls[""]]
        out["townUrls"] = {t: u for t, u in urls.items() if t in towns}
    if isinstance(as_of, dict):  # a list that dates each town on its own
        out["asOf"] = None
        out["townAsOf"] = {t: d for t, d in as_of.items() if t in towns and d}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("counties", nargs="*")
    ap.add_argument("--cache")
    ap.add_argument("--show", action="store_true",
                    help="print each town's offices and names, for review")
    ap.add_argument("--out", default=OUT_FILE)
    args = ap.parse_args(argv)
    if args.cache:
        os.makedirs(args.cache, exist_ok=True)
    f = Fetcher(args.cache)
    names = args.counties or sorted(PARSERS)
    try:
        with open(args.out) as fh:
            prior = json.load(fh)
    except (OSError, ValueError):
        prior = {"counties": {}}
    today = datetime.date.today().isoformat()
    out = dict(prior)
    out.setdefault("counties", {})
    for name in names:
        try:
            got = run_county(name, f)
        except SystemExit as exc:  # a robots refusal raises SystemExit
            print("%s: robots-refused (%s); last-good kept" % (name, exc), file=sys.stderr)
            continue
        except Exception as exc:  # noqa: BLE001 — one county never stops the rest
            print("%s: FAILED %s: %s; last-good kept" % (name, type(exc).__name__, exc),
                  file=sys.stderr)
            continue
        got["read"] = today
        out["counties"][name] = got
        n = sum(len(v) for v in got["towns"].values())
        print("%s: %d towns, %d officers, as of %s" % (name, len(got["towns"]), n,
                                                       got["asOf"]), file=sys.stderr)
        if args.show:
            for town, recs in sorted(got["towns"].items()):
                print("  %s: %s" % (town, "; ".join(
                    "%s%s=%s%s" % (r["office"], (" " + r["seat"]) if r.get("seat") else "",
                                   r["name"], (" (" + r["termEnds"] + ")") if r.get("termEnds") else "")
                    for r in recs)))
    out["counties"] = dict(sorted(out["counties"].items()))
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
