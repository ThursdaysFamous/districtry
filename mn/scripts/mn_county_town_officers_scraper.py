#!/usr/bin/env python3
"""The town officers Minnesota counties publish for their own towns, read from
each county's own list: the board of supervisors, the clerk and the treasurer,
by name, office, the year the term ends where the list prints one, and the
telephone and the e-mail address the list prints beside each officer.

WHY THIS EXISTS. mn/scripts/build_mn_town_boards.py names the boards of the 704
towns that hold their town election in November, from the Secretary of State's
results files. The other towns vote in March, run their own elections, and
appear in no file the state publishes (gap mn-township-officers). A town clerk
certifies the town's officers to the county auditor, and on 2026-10-15 a survey
of all 87 county websites (mn/data/source/mn-county-township-officer-survey.json)
found 42 counties that publish that list. This reads them.

WHAT IS KEPT AND WHAT IS NOT. These lists print each officer's home address,
telephone and e-mail beside the name. A parser takes the office, the name, a
term year, the telephone and the e-mail; the address is never read into the
output. The telephone ships as the list prints it, whosever line it is,
under Adam's ruling of 2026-10-17 ("if the official government source uses
personal phone numbers, we publish those"), with the label the list prints
beside it ("cell", "home"); a number printed without an area code ships
without one, never with a guessed one. The e-mail ships the same way, under
his choice of the same day ("E-mails too"), lower-cased and otherwise as the
list prints it, one per officer. An address a page hides behind Cloudflare's
e-mail protection (Aitkin's town pages) is shown as a reader's browser shows
it, by `uncloak`, before anything reads the page. A parser hands
`numbers()` and `emails()` only the column or line where its list prints an
officer's telephone or e-mail, and each returns only text with a telephone's
or an address's shape, so a street address sharing that line never reaches a
record; `check_record` refuses a name carrying a digit, an "@", or a street
word, so a column that slips cannot carry an address through. A number
marked as a fax is not read, and `settle_numbers` and `settle_emails` leave
out a number or an e-mail printed beside two or more people or printed more
often than beside the officers who carry it: those are a town's or an
office's, not the person's. `settle_emails` also leaves out a mailbox named
for the town itself or for another office, and the addresses of an officer
whose mail link sends somewhere other than the address it shows.

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
import collections
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
        # every document read for the county being parsed, which
        # `settle_numbers` searches for a number printed more than once
        self.docs = []

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
                data = fh.read()
            self.docs.append(data)
            return data, url
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
            self.docs.append(resp.content)
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


# ---------------------------------------------------------------- telephones
#
# A parser hands `numbers()` only the cell or line where its list prints an
# officer's telephone, and `numbers()` returns only what has a telephone's
# shape plus the label word printed beside it. The street address, the town
# and the ZIP code that share those lines never reach a record, and neither
# does the e-mail, which `emails()` reads on its own (below).

# A number as the lists print it: with an area code, bracketed or not, or
# with none (several lists print seven digits), and an extension. One list
# prints a ten-digit number with one hyphen, after the area code.
NUMBER = (r"(?:(?:\(\d{3}\)\s*-?\s*|\d{3}[-. ]?)?\d{3}[-. ]\d{4}|\d{3}-\d{7})"
          r"(?:\s*(?:ext\.?|x)\s*\d{1,5})?")
NUMBER_RE = re.compile(r"(?<![\d-])%s(?![\d-])" % NUMBER, re.I)

FAX = "fax"
# A label word as a list prints it, and the label this file ships. "(c)"
# typed into a word processor arrives as "©", which Polk's list prints after
# a number exactly where its other entries print "(c)" or "(h)". "Phone" says
# no more than that it is a telephone, so it ships no label.
LABEL_OF = {"c": "cell", "©": "cell", "cell": "cell", "h": "home", "home": "home",
            "w": "work", "work": "work", "b": "business", "business": "business",
            "o": "office", "office": "office", "mobile": "mobile",
            "f": FAX, "fax": FAX, "phone": "", "ph": "", "tel": ""}
_WORDS = r"(?:cell|home|work)(?:\s*phone)?|business|office|mobile|fax|phone|tel|ph"
# before the number: "Cell:", "cell#", "home phone", "C:", "F:"; a single
# letter only with its colon, so an initial is never read as a label
LABEL_BEFORE = re.compile(r"(?:^|[\s,;/(|])(?:(%s)\s*[:#.]?|([chwbof])\s*:)\s*$" % _WORDS, re.I)
# after it: "(c)", "( C)", "(Cell)", "- Cell", "cell", "©"; a word followed by
# a colon is the next number's label, not this one's
LABEL_AFTER = re.compile(r"^\s*(?:[-–]\s*)?(?:\(\s*(%s|[chwbof])\s*\)|(%s)(?!\s*[:#])(?![\w@.])|(©))"
                         % (_WORDS, _WORDS), re.I)


def _label(match):
    word = next(g for g in match.groups() if g)
    return LABEL_OF[re.sub(r"\s*phone$", "", word.lower()) or "phone"]


def numbers(text, label=None):
    """Every telephone number in `text`, as the list prints it with its
    spacing tidied, led by the label the list prints beside it on the
    `label` side ("before", "after", or None for a list that labels none).
    A number the list marks as a fax, on either side, is left out."""
    text = re.sub(r"\s+", " ", str(text).replace("\xa0", " "))
    found = list(NUMBER_RE.finditer(text))
    out = []
    for i, m in enumerate(found):
        before = LABEL_BEFORE.search(text[found[i - 1].end() if i else 0:m.start()])
        after = LABEL_AFTER.match(text[m.end():found[i + 1].start() if i + 1 < len(found) else None])
        if (before and _label(before) == FAX) or (after and _label(after) == FAX):
            continue
        hit = before if label == "before" else after if label == "after" else None
        kind = _label(hit) if hit else ""
        out.append((kind + " " if kind else "") + m.group(0).strip())
    return out


def add_numbers(rec, found):
    """Put numbers on a record, in the order its list prints them, for
    `settle_numbers` to sort into `phone` and `phonesExtra`."""
    if rec is not None and found:
        rec.setdefault("_numbers", []).extend(found)


def number_key(number):
    """A number reduced to its last seven digits, its extension and label
    dropped: a seven-digit number and the same line with its area code are
    one line."""
    m = NUMBER_RE.search(number)
    digits = re.sub(r"\D", "", re.sub(r"(?i)\s*(?:ext\.?|x)\s*\d+$", "", m.group(0) if m else number))
    return digits[-7:]


# ---------------------------------------------------------------- e-mail
#
# Since Adam's choice of 2026-10-17 ("E-mails too"), the e-mail address a
# list prints beside one officer ships on that officer's record, whosever
# mailbox it is. A parser hands `emails()` only the cell or line where its
# list prints an officer's e-mail, as it does for telephones, and
# `settle_emails` keeps one address per officer and leaves out any address
# that belongs to a town or an office rather than to the person.

# An address as a list prints it: one whitespace-free token, one "@", and a
# domain ending in a top-level name.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMAIL_SHAPE = re.compile(r"^%s$" % EMAIL_RE.pattern)
# The words a list prints before an address to say what it is.
EMAIL_LABELS = {"email", "e-mail", "email:", "e-mail:", "mail", "mail:", "e:"}


def emails(text):
    """Every e-mail address in `text`, lower-cased and otherwise exactly as
    the list prints it. An address with a bare lower-case word printed hard
    against it, before or after with no comma or semicolon between, is left
    out: it may be one address printed with a space in it, and part of an
    address would send mail to a stranger."""
    toks = str(text).replace("\xa0", " ").split()
    out = []
    for i, tok in enumerate(toks):
        if "@" not in tok:
            continue
        lead = re.match(r"^(?:e-?mail:)", tok, re.I)
        core = tok[lead.end():] if lead else tok
        core = core.strip("<>()[]{}\"").rstrip(",;:.")
        if not EMAIL_SHAPE.match(core):
            continue
        prev = toks[i - 1] if i and not lead else ""
        nxt = toks[i + 1] if i + 1 < len(toks) and not re.search(r"[,;]$", tok) else ""
        if (re.fullmatch(r"[a-z][a-z'-]*", prev) and prev.lower() not in EMAIL_LABELS) or \
                re.fullmatch(r"[a-z][a-z'-]*", nxt):
            continue
        core = core.lower()
        if core not in out:
            out.append(core)
    return out


def add_emails(rec, found):
    """Put addresses on a record, in the order its list prints them, for
    `settle_emails` to choose from."""
    if rec is not None and found:
        rec.setdefault("_emails", []).extend(found)


def government_mailbox(address):
    """An address on a government's own domain (a .gov or .mn.us domain, or
    one naming a township), which an officer's record keeps over a personal
    one when the list prints both."""
    domain = address.rsplit("@", 1)[-1]
    return bool(re.search(r"\.gov$|\.mn\.us$", domain) or re.search(r"township|twp|townof", domain))


def mailbox_offices(address):
    """The town offices an address names in its own name ("clerk.lakeview@",
    "sup1.lakeview@", "lakeview_treasurer@"); a chair is a supervisor."""
    found = set()
    for word in re.findall(r"[a-z]+", address.split("@")[0].lower()):
        if "clerk" in word:
            found.add("clerk")
        if "treas" in word:
            found.add("treasurer")
        if word.startswith(("supervisor", "supv", "chair")) or re.fullmatch(r"sup[a-e]?", word):
            found.add("supervisor")
    return found


def mailbox_of(address, town, office):
    """Whose mailbox an address is by its own name, where the name says:
    "office" for the office the officer beside it holds, "other office" for
    a different office's, "town" for the town's own (the town's name, or the
    initials of its words, with or without "township", "twp" or "town of",
    and nothing else), and None for anything else: a person's own address,
    or a name that says nothing."""
    named = mailbox_offices(address)
    if named:
        return "office" if any(o in office.lower() for o in named) else "other office"
    letters = re.sub(r"[^a-z]", "", address.split("@")[0].lower())
    words = re.findall(r"[a-z]+", town.lower())
    for key in ("".join(words), "".join(w[0] for w in words) if len(words) > 1 else ""):
        if key and key in letters and \
                not re.sub(r"township|twp|townof|town|of|mn", "", letters.replace(key, "", 1)):
            return "town"
    return None


MAILTO_RE = re.compile(r"^\s*mailto:", re.I)


def mailto_address(href):
    """The one address a mailto link sends to, lower-cased, or None when the
    link names none or more than one."""
    target = urllib.parse.unquote(MAILTO_RE.sub("", href).split("?")[0]).strip()
    return target.lower() if EMAIL_SHAPE.match(target) else None


# Cloudflare's e-mail protection prints "[email protected]" in place of an
# address and carries the address in hex: in a `data-cfemail` attribute on
# the element shown, and after "/cdn-cgi/l/email-protection#" in the link
# around it. A reader's browser shows the address; `uncloak` does the same.
# Measured 2026-10-17: Aitkin's 40 town pages are the only documents of the
# 29 counties' that use it.
CF_HREF_RE = re.compile(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)$")


def cf_decode(hexstr):
    """The address in one of Cloudflare's hex strings, or None when it does
    not decode to one address. The first byte is the key every later byte
    is XORed with (the fleet's reading, as in
    scripts/will_county_board_scraper.py), and the bytes are UTF-8."""
    try:
        raw = bytes.fromhex(hexstr)
        text = bytes(b ^ raw[0] for b in raw[1:]).decode("utf-8").strip()
    except (ValueError, IndexError):
        return None
    return text if EMAIL_SHAPE.match(text) else None


def uncloak(page):
    """A parsed page with Cloudflare's protected addresses shown as a
    reader's browser shows them: each element carrying `data-cfemail`
    becomes the address it hides, and a protected link becomes a mailto link
    to the address its own target hides, so everything below reads it like
    any other mail link, `mail_disagreements` included. A link whose target
    does not decode becomes a mailto link to nothing, which that check
    counts as a disagreement, so the address it shows is not carried."""
    for el in page.find_all(attrs={"data-cfemail": True}):
        el.replace_with(cf_decode(el["data-cfemail"]) or "")
    for a in page.find_all("a", href=CF_HREF_RE):
        a["href"] = "mailto:" + (cf_decode(CF_HREF_RE.search(a["href"]).group(1)) or "")
    return page


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


def pdf_word_rows(data, ytol=3):
    """The words of each line `pdf_lines` returns, in the same order, as
    (x0, word) pairs: for a list whose cells run into each other."""
    import pymupdf  # noqa: PLC0415
    doc = pymupdf.open(stream=data, filetype="pdf")
    out = []
    for page in doc:
        rows = {}
        for w in page.get_text("words"):
            rows.setdefault(round((w[1] + w[3]) / 2 / ytol), []).append(w)
        for key in sorted(rows):
            out.append([(w[0], w[4]) for w in sorted(rows[key], key=lambda w: w[0])])
    return out


def by_column(words, edges, slack=5):
    """A line's words joined under the column each starts in: the rightmost
    column edge at or left of the word. Words left of every edge (a row's
    own label) are left out."""
    out = {}
    for x, word in words:
        left = [e for e in edges if e <= x + slack]
        if left:
            e = max(left)
            out[e] = (out.get(e, "") + " " + word).strip()
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
    """A parsed page, with any address Cloudflare protects shown (`uncloak`)."""
    from bs4 import BeautifulSoup  # noqa: PLC0415
    return uncloak(BeautifulSoup(data, "html.parser"))


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


def cells_from(cells, x0, x1=None):
    """The text of the cells whose left edge is at or right of `x0` (and left
    of `x1`), kept apart so a label in one cell is never read as another's."""
    return " | ".join(t for x, t in cells if x >= x0 and (x1 is None or x < x1))


def generic(lines, header, name_side="after", term=None, term_ahead=0,
            office_anywhere=True, stop=STOP_RE, phone_x=None, phone_label=None,
            phone_below=False, email_x=None, email_below=False):
    """The shape most lists share: a town header, then one line per officer
    carrying an office word and a name.

    header(texts) -> town name or None, and may leave the line to be read as
    an officer too by returning (town, True). name_side says whether the name
    follows the office or precedes it. term, a compiled regex with one group,
    is looked for on the officer's own line and on the next term_ahead lines.
    phone_x is the left edge of the column a list prints each officer's
    telephone in: the numbers in it on the officer's own line are the
    officer's, and with phone_below so are the ones under it until the next
    officer or town. phone_label is the side the list prints a label on.
    email_x is (left, right) of the cells a list prints each officer's
    e-mail in, read the same way, with email_below for the lines under the
    officer's own.
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
            if phone_x is not None:
                add_numbers(rec, numbers(cells_from(cells, phone_x), phone_label))
            if email_x is not None:
                add_emails(rec, emails(cells_from(cells, *email_x)))
            continue
        if phone_below and last is not None:
            add_numbers(last, numbers(cells_from(cells, phone_x), phone_label))
        if email_below and last is not None:
            add_emails(last, emails(cells_from(cells, *email_x)))
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
    # the telephone ends each officer's line, after the city, state and ZIP.
    # The e-mail the list prints is a town's, under the town's name, and not
    # an officer's, so it is not read.
    return (generic(lines, caps_header(), phone_x=440), first_date(pdf_text(data)),
            [final])


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
    # The telephone column, read from x 440: one number on the officer's own
    # line, and a second, where an officer gives one, on the line under it.
    # The e-mail is the last line of the officer's block in the name column
    # (x 285), under the street and the city.
    towns, cur, last, dial = {}, None, None, None
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
                dial = None
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
            dial = last
            add_numbers(dial, numbers(cells_from(cells, 440)))
            m = re.search(r"TERM EXP\.?\s*(20\d\d)", " ".join(texts))
            if m:
                last["termEnds"] = m.group(1)
            continue
        add_numbers(dial, numbers(cells_from(cells, 440)))
        add_emails(dial, emails(cells_from(cells, 280, 440)))
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
    # the township section ends where the city listing begins. The telephone
    # ends each officer's line, seven digits with a "(w)", "(c)" or "(h)"
    # after some, and a second number sits under it on the e-mail line, whose
    # "e-mail:" opens the address column.
    return (generic(lines, header, office_anywhere=False, phone_x=440, phone_label="after",
                    phone_below=True, email_x=(190, None), email_below=True), None, [final])


@county("Carlton", 15)
def carlton(f):
    url = "https://www.co.carlton.mn.us/DocumentCenter/View/6572"
    data, final = f.get(url)
    rx = re.compile(r"^Township of (.+)$")

    def header(texts):
        m = rx.match(texts[0])
        return town_key(m.group(1)) if m else None
    # the e-mail column, between the name and the term
    towns = generic(pdf_lines(data), header, term=re.compile(r"(?:^|\s)(20[2-3]\d)$"),
                    office_anywhere=False, email_x=(330, 560))
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
                # the telephone column, between the office and the term
                add_numbers(rec, numbers(cells_from(cells, 250, 355)))
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
    # two telephone columns, "PHONE" and "PHONE (2)", between the e-mail and
    # the term; the e-mail is printed after the state and ZIP code, often in
    # the same cell, and only its address is taken from it
    towns = generic(pdf_lines(data), header, term=re.compile(r"\b(20[2-3]\d)\s*$"),
                    office_anywhere=False, phone_x=440, email_x=(240, 440))
    return towns, None, [final]


@county("Waseca", 10)
def waseca(f):
    url = "https://www.wasecacounty.gov/DocumentCenter/View/219/ELECTED-OFFICIALS"
    data, final = f.get(url)
    rx = re.compile(r"^(.+?) Township$")

    def header(texts):
        m = rx.match(texts[0])
        return town_key(m.group(1)) if m else None
    # the telephone is the last column; a number marked "(FAX)" is not read.
    # The e-mail follows the name in the name's own cell ("Name - address").
    towns = generic(pdf_lines(data), header, name_side="before",
                    term=re.compile(r"^(20[2-3]\d)\b"), phone_x=690, email_x=(130, 300))
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
    # each officer's telephone opens the cell that goes on to the street
    # address; only the number is taken from it
    towns = generic(pdf_lines(data), header, term=re.compile(r"\b(20[2-3]\d)\s*$"),
                    office_anywhere=False, phone_x=255)
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
        # the telephone column, after the name and before the address; a
        # number the town's own column prints under its name is the town's,
        # and is not read, nor is an e-mail it prints there. The officer's
        # e-mail has a column of its own, after the telephone.
        add_numbers(rec, numbers(cells_from(cells, 200, 420), "after"))
        add_emails(rec, emails(cells_from(cells, 265, 425)))
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
        # the last cell carries the telephone and then the term, so only its
        # first number is read: one term is printed with a digit missing,
        # which gives it a seven-digit telephone's shape
        add_numbers(rec, numbers(cells_from(cells, 700))[:1])
        towns.setdefault(town_key(m.group(1)), []).append(rec)
    return towns, None, [final]


@county("Roseau", 20)
def roseau(f):
    url = ("https://www.roseaucountymn.gov/Documents/Community/Township/"
           "2026Township%20Officers.pdf")
    data, final = f.get(url)
    lines = pdf_lines(data)
    words = pdf_word_rows(data)
    towns, cur, offices, phoned, named = {}, None, None, True, False
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
                named = False
                continue
        if cur is None:
            continue
        if all(office_of(t) for t in texts) and len(texts) >= 3:
            offices = [(x, office_of(t)) for x, t in cells]
            # a row of offices after the names is a town whose heading was
            # not read; its numbers and e-mails belong to nobody here
            phoned = bool(cur)
            named = named and not cur
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
                phoned = False
                named = True
            continue
        head = texts[0].lower() if texts else ""
        if cur and head.startswith("phone") and not phoned:
            phoned = True
            # "Phone #", then each officer's numbers under the officer's
            # name, several where an officer gives several, read word by word
            # because a long cell runs into the next column; a "Fax:" is not
            # read
            col = {r["_x"]: r for r in cur}
            for x, text in by_column(words[k], list(col)).items():
                add_numbers(col[x], numbers(text))
            continue
        if cur and named and any("@" in w for _, w in words[k]):
            # "Email:", then each officer's address under the officer's name;
            # the label and the addresses sometimes land on separate lines,
            # so any line of the town's block carrying an address is read
            col = {r["_x"]: r for r in cur}
            for x, text in by_column(words[k], list(col)).items():
                add_emails(col[x], emails(text))
            continue
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
    words = pdf_word_rows(data)
    # every block, township, city or county, opens with its name repeated
    # across the columns (a city, state and ZIP code shared by a whole board
    # repeats too, and carries digits)
    starts = [k for k, cells in enumerate(lines)
              if len(cells) >= 3 and len(set(t for _, t in cells)) == 1
              and not re.search(r"\d|@", cells[0][1])]
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
        # Under each name, in its own column: the address, the telephone, a
        # second telephone where the officer gives one, and the e-mail, down
        # to the next block. A column shifts a line when a cell above it
        # wraps, so the numbers and the e-mail are read by column, not by line.
        col = {x: rec for (x, _), rec in zip(lines[k + 2], recs)}
        end = min([j for j in starts if j > k] + [len(lines)])
        for j in range(k + 3, end):
            for x, text in by_column(words[j], list(col)).items():
                add_numbers(col[x], numbers(text))
                add_emails(col[x], emails(text))
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
    words = pdf_word_rows(data)
    header = None
    towns, under = {}, {}
    for k, cells in enumerate(lines):
        texts = [t for _, t in cells]
        if len(texts) >= 4 and all(office_of(t) for t in texts):
            header = [(x, office_of(t)) for x, t in cells]
            under = {}
            continue
        if header and len(cells) >= 3 and cells[0][0] < 40 and \
                re.match(r"^[A-Z][A-Za-z .']+\*?$", texts[0]) and \
                all(looks_like_name(t) for t in texts[1:]):
            recs, under = [], {}
            for x, t in cells[1:]:
                col = nearest(x, header, tol=60)
                if col:
                    recs.append(row(col[1][0], col[1][1], t))
                    under[x] = recs[-1]
            towns[town_key(texts[0].rstrip("*"))] = recs
            continue
        if cells and cells[0][0] < 40:
            under = {}  # a town whose row is not read lends its numbers to nobody
            continue
        # Under the names, rows headed "home phone" and "cell phone" carry
        # each officer's numbers in the officer's column; the first column's
        # number is printed hard against the row's heading, so the words are
        # placed by where each starts.
        kind = re.match(r"^(home|cell) phone\b", texts[0]) if texts else None
        if kind and under:
            for x, text in by_column(words[k], list(under)).items():
                add_numbers(under[x], [kind.group(1) + " " + n for n in numbers(text)])
        # and a row headed "email" carries each officer's address, the same way
        if texts and texts[0].startswith("email") and under:
            for x, text in by_column(words[k], list(under)).items():
                add_emails(under[x], emails(text))
    return towns, "2025", [final]


@county("Le Sueur", 10)
def le_sueur(f):
    url = "https://www.lesueurcounty.gov/DocumentCenter/View/7197"
    data, final = f.get(url)
    towns, cur, prev = {}, None, None
    for left, pos, seat, name, rest in pdf_columns(data, [140, 200, 228, 325]):
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
        # the last column is the telephone, on the officer's own line
        add_numbers(cur[-1], numbers(rest))
    return towns, first_date(pdf_text(data)), [final]


@county("Norman", 15)
def norman(f):
    url = "https://www.normanmn.gov/Documents%20Center/Department/Township%20Officers.pdf"
    data, final = f.get(url)
    lines, words = pdf_lines(data), pdf_word_rows(data)
    # Under each name, in its column: the end of term, the address, the
    # telephone ("C:", "H:" or "O:" before some; an "F:" fax is not read)
    # and the e-mail, down to the next row of names. The telephone and the
    # e-mail are read; the address is not.
    towns, cur, header, last, under = {}, None, None, [], {}
    for k, cells in enumerate(lines):
        texts = [t for _, t in cells]
        if "Mayor" in texts:
            break  # the cities follow the townships, under a Mayor header
        if len(texts) >= 3 and all(office_of(t) for t in texts):
            header = [(x, office_of(t)) for x, t in cells]
            under = {}
            continue
        if header is None:
            continue
        if len(cells) == 1 and cells[0][0] < 60 and re.match(r"^[A-Z][A-Za-z .']+$", texts[0]):
            cur = towns.setdefault(town_key(texts[0]), [])
            last, under = [], {}
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
            last, under = [], {}
            for x, t in cells:
                col = nearest(x, header, tol=80)
                if col:
                    rec = row(col[1][0], col[1][1], t)
                    cur.append(rec)
                    last.append(rec)
                    under[x] = rec
            continue
        for x, text in by_column(words[k], list(under)).items():
            add_numbers(under[x], numbers(text, "before"))
            add_emails(under[x], emails(text))
    m = re.search(r"Township Officers\s+(20\d\d)\b", pdf_text(data))
    return towns, (m.group(1) if m else None), [final]


@county("Clay", 15)
def clay(f):
    # One table per township: a row of offices, a row of names, then "Term
    # Limit: 2027" under some of them (the year the term ends), then the
    # officers' mailing addresses, which are not read.  The e-mail link beside
    # a table ("Email ... Township") is the town's own address, not an
    # officer's, and is not read either.
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
    # name, position, a telephone and an e-mail, both read.  A place with a
    # Mayor or Council row is a city and is left out whole.
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
    for place, first, last, position, phone, email in ((c + ["", ""])[:6] for c in rows):
        if place in cities:
            continue
        hit = office_of(position)
        if not hit or hit[0].startswith("Deputy"):
            continue
        rec = row(hit[0], hit[1], first + " " + last)
        add_numbers(rec, numbers(phone))
        # the address as the cell shows it; a mailto link that sends mail
        # somewhere else is caught by `settle_emails`
        add_emails(rec, emails(email))
        towns.setdefault(town_key(place), []).append(rec)
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
    # telephone (most of them seven digits), the term as "2024-2027", an
    # address and an e-mail under an "Email" heading.  Office, name,
    # telephone, the term's last year and the e-mail are read; the address
    # is not.
    data, final = f.get("https://www.redlakecounty.gov/Documents/Government/"
                        "Township%20Officers%202025.xlsx")
    rows = xlsx_rows(data)
    mail = next((r.index(c) for r in rows for c in r if str(c).strip().lower() == "email"), None)
    towns, cur = {}, None
    for r in rows:
        place, office, name, phone, term = (str(c).strip() for c in (r + [""] * 5)[:5])
        hit = office_cell(office)
        if place and hit and hit[0] == "Supervisor (chair)":
            # Some towns carry a letter after the name ("Equality A").
            cur = towns.setdefault(re.sub(r"\s+[A-E]$", "", town_key(place)), [])
        if cur is None or not hit or not name:
            continue
        m = re.search(r"20[2-3]\d\s*-\s*(20[2-3]\d)", term)
        cur.append(row(hit[0], hit[1], name, m.group(1) if m else None))
        add_numbers(cur[-1], numbers(phone))
        if mail is not None and mail < len(r):
            add_emails(cur[-1], emails(r[mail]))
    title = " ".join(str(c) for r in rows[:3] for c in r)
    m = re.search(r"TOWNSHIP OFFICERS\s+(20\d\d)", title)
    return towns, (m.group(1) if m else None), [final]


@county("Itasca", 30)
def itasca(f):
    # One sheet: township on a town's first row, the town hall's address and
    # an "Upd. 1/27/26" note down the next column; then position, the date the
    # term ends ("Appt." for an appointed clerk), first and last name, a
    # telephone and an e-mail, both read; the town hall's address is not.
    data, final = f.get("https://www.itascacountymn.gov/DocumentCenter/View/12319/Township-Officials")
    rows = xlsx_rows(data)
    mail = 7 if rows and len(rows[0]) > 7 and str(rows[0][7]).strip().lower() == "email" else None
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
            add_numbers(cur[-1], numbers(r[6]))
            if mail is not None:
                add_emails(cur[-1], emails(r[mail]))
    # Each town carries its own "Upd." date, so each town is dated by its own.
    return towns, updated, [final]


@county("Polk", 40)
def polk(f):
    # Columns: township, clerk, the clerk's term, treasurer, the treasurer's
    # term, chair and supervisors ("Name - Chairperson"), the supervisor's
    # term, then the supervisors' addresses.  A town's name stands on its
    # first line; "November" / "Election" notes sit under it.  Under each
    # clerk's and treasurer's name, in the same column, come the address, the
    # telephone and the e-mail; a supervisor's telephone sits in the last
    # column under that supervisor's address, and the supervisor's e-mail in
    # the supervisor's own column under the name.  Only the telephones, with
    # the "(c)", "©", "(h)" or "- Cell" printed after, and the e-mails are
    # read from those cells; the addresses are not.
    data, final = f.get("https://www.co.polk.mn.us/DocumentCenter/View/3712/Township-Officers-2026")
    towns, cur, dial = {}, None, {}

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
            dial = {}
            for col, office, name, term in ((1, "Clerk", clerk, cterm), (3, "Treasurer", treas, tterm)):
                name = re.sub(r"^Appointed\s+", "", name)
                if looks_like_name(name):
                    cur.append(row(office, None, name, term_of(term)))
                    dial[col] = cur[-1]
        if cur is None:
            continue
        sup = re.sub(r"^Appointed\s+", "", sup.strip())
        if sup and "@" not in sup:
            # a supervisor's line: the numbers from here down are this
            # supervisor's, or nobody's if the name is not read
            dial.pop(7, None)
        m = re.match(r"^(.+?)\s*-\s*(Chairperson|Chair|Supervisor)\b", sup)
        name = m.group(1) if m else sup
        if name and looks_like_name(name) and not re.search(r"@|\d", sup) \
                and len(name.split()) >= 2:
            office = "Supervisor (chair)" if m and m.group(2).startswith("Chair") else "Supervisor"
            cur.append(row(office, None, name, term_of(sterm)))
            dial[7] = cur[-1]
        for col, rec in dial.items():
            add_numbers(rec, numbers(cols[col], "after"))
            # the supervisor's e-mail is under the name (column 5), not in
            # the telephone's column
            add_emails(rec, emails(cols[5 if col == 7 else col]))
    return towns, "2026", [final]


@county("Meeker", 15)
def meeker(f):
    # Each township is three supervisor lines ("2025-2028 A Name, Ch., then
    # the supervisor's address", with the supervisor's telephone in the
    # PHONE column before it and the supervisor's e-mail after it); the first
    # carries the clerk and treasurer ("2026-2027 Name (phone)") and the
    # second the town's name, and the clerk's and treasurer's addresses and
    # e-mails run down their own columns under them.  The name before the
    # first comma, the seat letter, "Ch.", each term's last year, the
    # telephones and the e-mails are read; the addresses are not.  The cities
    # follow under a CITY header.
    data, final = f.get("https://www.meekercountymn.gov/DocumentCenter/View/8143/"
                        "Township--City-Officers-Listing-Feb-2-2026")
    # A supervisor cell starts with its term, its seat letter or both (one
    # town prints the letter on a line of its own), never with neither: a
    # bare "Name, ..." cell is an address.
    sup_re = re.compile(r"^(?:(?:\d{4}-(\d{4}) )([A-E] )?|([A-E] ))#?"
                        r"([^,(]+(?:\([^)]*\)[^,]*)?),\s*(Ch\.)?")
    off_re = re.compile(r"^(?:\d{4}-(\d{4})|N/A) #?([A-Z][^()]+?)\s*\(\d{3}\)")
    town_re = re.compile(r"^(?:\d+ )?([A-Z][A-Z .]{2,}?)[*& ]*$")
    towns, block, pending = {}, None, None
    for cells in pdf_lines(data):
        texts = []
        for _, t in cells:  # a term or "N/A" printed apart from its name
            if texts and re.match(r"^(?:\d{4}-\d{4}|N/A)$", texts[-1]):
                texts[-1] += " " + t
            else:
                texts.append(t)
        if texts and texts[0].startswith("CITY"):
            break
        offs = [(m, t) for m, t in ((off_re.match(t), t) for t in texts) if m]
        if len(offs) == 2:
            block = []
            for office, (m, t) in zip(("Clerk", "Treasurer"), offs):
                block.append(row(office, None, m.group(2), m.group(1)))
                # the telephone that ends the cell, after the name
                add_numbers(block[-1], numbers(t[m.end() - 5:]))
        if block is None:
            continue
        sup = None
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
                add_numbers(block[-1], numbers(cells_from(cells, 100, 180)))
                sup = block[-1]
        # The supervisor's e-mail ends the supervisor's cell or stands in the
        # column after it (x 429). That column's line sits a point or two
        # below the supervisor's, so it is sometimes read as a line of its
        # own, directly under the supervisor's; it is that supervisor's when
        # the supervisor's own line carried none.
        found = emails(cells_from(cells, 180, 505))
        if sup is not None:
            add_emails(sup, found)
            pending = None if found else sup
        elif found and all(420 <= x < 510 for x, _ in cells):
            add_emails(pending, found)
            pending = None
        # the clerk's and the treasurer's e-mails, in their own columns
        add_emails(block[0], emails(cells_from(cells, 505, 680)))
        add_emails(block[1], emails(cells_from(cells, 680, 860)))
    m = re.search(r"Last Updated\s+\w+\s+(\d{1,2}),\s*(20\d\d)", pdf_text(data))
    return towns, ("%s-02-%02d" % (m.group(2), int(m.group(1))) if m else None), [final]


@county("Watonwan", 10)
def watonwan(f):
    # One table per township, headed by the town's name: "Name-Office", then
    # an address, which is not read, and a telephone under a "Phone" header,
    # which is.
    data, final = f.get("https://www.co.watonwan.mn.us/122/Township-Officials")
    towns = {}
    for table in soup(data).find_all("table"):
        title = table.find_previous(string=re.compile(r"\S")).strip()
        recs = towns.setdefault(town_key(title), [])
        trs = table.find_all("tr")
        head = [c.get_text(" ", strip=True).lower() for c in trs[0].find_all(["td", "th"])] if trs else []
        dial = head.index("phone") if "phone" in head else None
        for tr in trs[1:]:
            tds = tr.find_all(["td", "th"])
            cell = tds[0] if tds else None
            m = re.match(r"^(.+?)\s*-\s*([A-Za-z/ ]+)$", cell.get_text(" ", strip=True)) if cell else None
            hit = office_cell(m.group(2)) if m else None
            if hit:
                recs.append(row(hit[0], hit[1], m.group(1)))
                if dial is not None and dial < len(tds):
                    add_numbers(recs[-1], numbers(tds[dial].get_text(" ", strip=True)))
    return towns, None, [final]


@county("Wadena", 12)
def wadena(f):
    # One table naming each township's clerk, with the clerk's telephone in
    # the third column.
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
                add_numbers(towns[town_key(r[0])][0], numbers(r[2] if len(r) > 2 else ""))
    return towns, None, [final]


def page_lines(data):
    """A page's visible text, one line per line it shows.  A link to an
    e-mail address whose text is a word ("E-mail") shows the address it
    sends to on a line of its own after that word, where the page prints
    it."""
    page = soup(data)
    for t in page(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    for a in page.find_all("a", href=MAILTO_RE):
        address = mailto_address(a["href"])
        if address and "@" not in a.get_text(" "):
            a.insert_after("\n%s\n" % address)
    return [re.sub(r"[ \t\xa0]+", " ", ln).strip() if not re.search(r"\s{2,}\S", ln.strip())
            else ln.strip() for ln in page.get_text("\n").splitlines() if ln.strip()]


def names_someone(line):
    """True when a line opens with a person's name ahead of a telephone: a
    second officer's line under one office's label, whose number is that
    officer's and not the one above."""
    m = NUMBER_RE.search(line)
    if not m:
        return False
    lead = re.sub(r"(?i)\b(?:%s)\b|[#:()\-.,]" % _WORDS, " ", line[:m.start()])
    lead = re.sub(r"\s+", " ", lead).strip()
    return looks_like_name(lead) and len(lead.split()) >= 2


def label_pairs(lines, term=False):
    """Officers from a page that prints each office as a line of its own
    ("Clerk", "Supervisor (A)", "Township Treasurer:") with the officer's
    name on the next line, the name ending where a telephone, a run of
    spaces or an address begins.  With `term`, a "6/2027" line before the
    next office is read as the month and year the term expires.

    The officer's telephone is read from the rest of the name's line and
    from the next five lines, stopping at the next office's label or at a
    line that opens with someone else's name; the label printed before a
    number ("cell#") is kept, and the addresses on those lines are not
    read."""
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
        add_numbers(out[-1], numbers(lines[i + 1][len(name):], "before"))
        add_emails(out[-1], emails(lines[i + 1][len(name):]))
        for nxt in lines[i + 2:i + 7]:
            if office_cell(re.sub(r"^Township\s+", "", nxt)) or names_someone(nxt):
                break
            add_numbers(out[-1], numbers(nxt, "before"))
            add_emails(out[-1], emails(nxt))
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
    # Each town's page prints every officer as one block: the office, the
    # name, the officer's address (not read), a telephone and an e-mail
    # address hidden by Cloudflare's e-mail protection. `soup` shows that
    # address as a reader's browser does (`uncloak`), so it is read and
    # settled under the same rules as every other county's.
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


GOODHUE_LAYER = ("https://services5.arcgis.com/zCDVc272xQCnwjzc/arcgis/rest/services/"
                 "Township_Election_Management/FeatureServer/0")
# The layer's officer fields, in the order a ballot lists the offices. Each
# officer also has an `_address` and a `_city_state_zip` field, which are
# home addresses and are never asked for.
GOODHUE_OFFICES = (
    ("chairperson", "Supervisor (chair)"),
    ("supervisor_1", "Supervisor"),
    ("supervisor_2", "Supervisor"),
    ("Clerk", "Clerk"),
    ("deputy_clerk", "Deputy Clerk"),
    ("treasurer", "Treasurer"),
)


@county("Goodhue", 18)
def goodhue(f):
    # Each township's page on goodhuecountymn.gov links "Certified Listing of
    # Township Officers", which since 2026 is an ArcGIS Online lookup app
    # (item e717f54f7886413894555873171a982b) rather than a PDF per town.
    # The app's own web map (5056563fc35a416e9f2fd4dd77bd201c) reads one
    # public feature layer, so that layer is read here as the app reads it,
    # with only the fields its pop-up shows: name, telephone, e-mail and
    # the year the term expires. Measured 2026-10-26: 22 features, 21 towns
    # and an empty Red Wing row (a city, with no town officers). Each town
    # is dated to its own last edit. The deputy clerk field is labelled
    # "Holden TWP Only" in the app and is read wherever it is filled.
    index, final = f.get("https://goodhuecountymn.gov/about/townships/")
    pages = {}
    # The index links each town by its photo, so the town is read off the
    # link's own path ("/about/townships/belle_creek/").
    for a in soup(index).find_all("a", href=re.compile(r"^/about/townships/[a-z_]+/$")):
        slug = a["href"].rstrip("/").rsplit("/", 1)[1]
        pages[slug.replace("_", " ").title()] = urllib.parse.urljoin(final, a["href"])
    fields = ["field_37", "EditDate"]
    for key, _office in GOODHUE_OFFICES:
        base = "Clerk_Name" if key == "Clerk" else (
            "deputy_clerk_name_holden_twp_on" if key == "deputy_clerk" else key + "_name")
        low = key.lower()
        fields += [base, low + "_phone_number", low + "_email_address", low + "_term_expires"]
    query = "%s/query?%s" % (GOODHUE_LAYER, urllib.parse.urlencode({
        "where": "1=1", "outFields": ",".join(fields), "returnGeometry": "false",
        "orderByFields": "OBJECTID", "f": "json"}))
    data, _ = f.get(query)
    doc = json.loads(data.decode("utf-8"))
    if "error" in doc or "features" not in doc:
        raise RuntimeError("Goodhue's officer layer answered %r" % (doc.get("error") or doc)[:200])
    towns, as_of, urls = {}, {}, {"": final}
    for feature in doc["features"]:
        a = feature["attributes"]
        town = town_key(a.get("field_37") or "").title()
        if not town:
            continue
        recs = towns.setdefault(town, [])
        for key, office in GOODHUE_OFFICES:
            low = key.lower()
            base = "Clerk_Name" if key == "Clerk" else (
                "deputy_clerk_name_holden_twp_on" if key == "deputy_clerk" else key + "_name")
            name = (a.get(base) or "").strip()
            if not name:
                continue
            rec = row(office, None, name, TERM_RE.search(a.get(low + "_term_expires") or "")
                      and TERM_RE.search(a.get(low + "_term_expires")).group(1))
            add_numbers(rec, numbers(a.get(low + "_phone_number") or ""))
            add_emails(rec, emails(a.get(low + "_email_address") or ""))
            recs.append(rec)
        if a.get("EditDate"):
            as_of[town] = datetime.datetime.fromtimestamp(
                a["EditDate"] / 1000, datetime.timezone.utc).date().isoformat()
        if town in pages:
            urls[town] = pages[town]
    return towns, as_of, urls


# Traverse publishes its list as one scanned page with no text layer
# ("TOWNSHIP OFFICERS AND TERMS", scanned 2026-03-18).  It was read by eye on
# 2026-10-26 and is transcribed here, one line per officer: office, name,
# telephone (printed beside the clerk only) and the term's year.  The list is
# used only while the image the county serves is the one transcribed; any
# other image fails the county, its last-good towns are kept, and the new
# image is read and this table replaced.  "2026/2028" (Arthur's Supervisor 2)
# names no single year and is dropped; the asterisk after Folsom's David
# Duffield is unexplained on the page and is not carried.
TRAVERSE_IMAGE = "20260318120532_00001-scaled.jpg"
TRAVERSE_SHA256 = "ded392a1b79aea973979b6ad51e9b06771c0f99c6654ac2c7175f1c906ddd1e8"
TRAVERSE_LIST = """
Arthur|Sup. 1|Ed Hiedeman||2028
Arthur|Clerk|Maison Gibson|(320) 305-9381|2026
Arthur|Treas.|Mike O'Neill||2028
Arthur|Sup. 3|Kristopher Anderson||2026
Arthur|Sup. 2|Dale Zych||
Clifton|Sup. 3|Chad Bruns||2028
Clifton|Clerk|Steven Deal|320-563-4137|2026
Clifton|Treas.|Karen Lupkes||2028
Clifton|Sup. 1|Jeff Young||2028
Clifton|Sup. 2|Kevin Deal||2026
Croke|Sup. 1|Philip Brink||2026
Croke|Clerk/Treas|Alexis Doll|320-808-9434|2028
Croke|Sup. 2|Dale Schwagel||2028
Croke|Sup. 3|Tom Frisch||2028
Dollymount|Sup. 1|Steven Fridgen||2026
Dollymount|Clerk|Steven Rinke|320-563-8784|2026
Dollymount|Treas.|Brian Rinke||2028
Dollymount|Sup. 2|Dean Frisch||2026
Dollymount|Sup. 3|David M Tritz||2028
Folsom|Sup. 2|David Duffield||2026
Folsom|Clerk|Dennis Duffield|320-695-2256|2026
Folsom|Treas.|Peggy Duffield||2028
Folsom|Sup. 3|David Metz||2028
Folsom|Sup. 1|Mike Smith||2026
Lake Valley|Sup. 1|Steve Johnson||2028
Lake Valley|Clerk|Glenn Koch|320-815-8344|2028
Lake Valley|Treas.|Mary Peyton||2026
Lake Valley|Sup. 2|Curt Braun||2028
Lake Valley|Sup. 3|Tyler Klugman||2026
Leonardsville|Sup. 3|Randy Tritz||2028
Leonardsville|Clerk|Adam Jipson|320-808-4295|2028
Leonardsville|Treas.|Matthew Kleindl||2026
Leonardsville|Sup. 1|Aaron Fuhrman||2026
Leonardsville|Sup. 2|Mark Andrews||2026
Monson|Sup. C|Troy Fridgen||2026
Monson|Clerk|Jacqueline McClernon|218-770-6964|2028
Monson|Treas.|Kim Fridgen||2026
Monson|Sup. B|DeWayne Groneberg||2028
Monson|Sup. A|Delane Anderson||2026
Parnell|Sup. 2|Joe Murphy||2026
Parnell|Clerk/Treas.|Tina Syverson|320-905-1951|2028
Parnell|Sup. 1|Chad M. Arens||2028
Parnell|Sup. 3|Lowell Syverson||2026
Redpath|Sup. 2|Cory Morrow||2028
Redpath|Clerk|Stephan Berger|320-304-3867|2026
Redpath|Treas.|Brad Krenz||2028
Redpath|Sup. 1|Chadd Berger||2028
Redpath|Sup. 3|Keith Buss||2026
Tara|Sup. A|Dave Bauer||2028
Tara|Clerk|Robert Groebner|320-287-2061|2028
Tara|Treas.|Richard Sanasack||2026
Tara|Sup. C|Terry Stueve||2026
Tara|Sup. B|Scott Gilsdorf||2026
Taylor|Sup. 2|Dean Holtz||2026
Taylor|Clerk|Norma Holtz|320-563-4288|2028
Taylor|Treas.|Jeff Krump||2026
Taylor|Sup. 3|Jeffrey Muehler||2026
Taylor|Sup. 1|Alan Bruce||2028
Tintah|Sup. B|Michael Corey||2026
Tintah|Clerk|Jacob McClernon|320-287-9875|2028
Tintah|Treas.|Christine Morgan||2026
Tintah|Sup. C|Michael Porter||2028
Tintah|Sup. A|Jesse Morgan||2026
Walls|Sup. 3|Pat Peyton||2028
Walls|Clerk|Gail Thiel|320-808-5790|2026
Walls|Treas.|Robert Thiel||2028
Walls|Sup. 1|Kevin Pederson||2026
Walls|Sup. 2|Mitch Findlay||2028
Windsor|Sup. 2|Robert Schmitz||2028
Windsor|Clerk|Roger A. Schwagel|320-563-8517|
Windsor|Treas.|Ann Harter||2028
Windsor|Sup. 3|Joe Reinart||2028
Windsor|Sup. 1|Brandon Smith||2026
"""


@county("Traverse", 15)
def traverse(f):
    page_url = "https://traversecountymn.gov/departments/departments/county-commissioners/township-officers/"
    html, final = f.get(page_url)
    src = next((i["src"] for i in soup(html).find_all("img", src=True)
                if i["src"].endswith(TRAVERSE_IMAGE)), None)
    if not src:
        raise ValueError("Traverse: the page no longer shows the transcribed scan; "
                         "read the new image and replace TRAVERSE_LIST")
    data, _ = f.get(urllib.parse.urljoin(final, src))
    f.docs.pop()  # an image has no text to count numbers in
    if hashlib.sha256(data).hexdigest() != TRAVERSE_SHA256:
        raise ValueError("Traverse: the scan's bytes changed; read it again and "
                         "replace TRAVERSE_LIST and TRAVERSE_SHA256")
    towns = {}
    for line in TRAVERSE_LIST.strip().splitlines():
        town, office, name, phone, term = line.split("|")
        m = re.match(r"^Sup\.?\s*([1-5A-E])\.?$", office)
        hit = ("Supervisor", m.group(1)) if m else office_cell(office)
        rec = row(hit[0], hit[1], name, term or None)
        towns.setdefault(town, []).append(rec)
        add_numbers(rec, numbers(phone))
    return towns, "2026-03-18", [final]


RENVILLE_COLUMNS = {"town": 739, "title": 637, "name": 537, "address": 420,
                    "city": 310, "state": 251, "zip": 213, "phone": 179, "term": 113}



@county("Renville", 24)
def renville(f):
    # The auditor-treasurer's "City and Township Officials" listing, a table
    # set sideways (Faribault's layout) whose cells are placed by where each
    # line sits across the page: township, title, name, home address (never
    # read), city, state, ZIP code, telephone and the term's last year or
    # "Appointed".  The last two pages are the county's cities, whose rows
    # name "<Name> City" and are not township officers.  The page's address
    # serves the PDF itself; the document link the county's township page
    # carried until September 2026 answers with an empty file.
    import pymupdf  # noqa: PLC0415
    data, final = f.get("https://www.renvillecountymn.gov/vidoc/city-and-township-officials/")
    if data[:4] != b"%PDF":
        raise ValueError("Renville: the officials listing is no longer a PDF")
    towns = {}
    for page in pymupdf.open(stream=data, filetype="pdf"):
        rows = {}
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                if tuple(round(v) for v in line["dir"]) != (0, -1):
                    continue
                text = " ".join(sp["text"] for sp in line["spans"]).strip()
                if not text:
                    continue
                y = line["bbox"][3]
                col = min(RENVILLE_COLUMNS, key=lambda c: abs(RENVILLE_COLUMNS[c] - y))
                if col == "address":
                    continue
                rows.setdefault(round(line["bbox"][0] / 4), {})[col] = text
        for key in sorted(rows):
            r = rows[key]
            town, title, name = r.get("town", ""), r.get("title", ""), r.get("name", "")
            if not name or town in ("", "Township") or re.search(r"\bCity$", town):
                continue
            m = re.match(r"^Supervisor\s*-\s*([A-E])$", title)
            hit = ("Supervisor", m.group(1)) if m else office_cell(title)
            if not hit:
                raise ValueError("Renville, %s: an office it does not know: %r" % (town, title))
            office, seat = hit[0], hit[1]
            # A seat letter printed after the name ("Wayne Stahnke A").
            m = re.match(r"^(.*\S)\s+([A-E])$", name)
            if m and office.startswith("Supervisor") and not seat:
                name, seat = m.group(1), m.group(2)
            term = r.get("term", "")
            rec = row(office, seat, name, term if re.match(r"^20\d\d$", term) else None)
            towns.setdefault(town_key(town), []).append(rec)
            add_numbers(rec, numbers(" | ".join(r.get(c, "") for c in ("zip", "phone"))))
    # The listing prints no date; the file's own creation date is when it was
    # made (2026-09-17 for "City-Township-Officials-Listing_Sept-2026.pdf").
    m = re.match(r"D:(20\d\d)(\d\d)(\d\d)",
                 pymupdf.open(stream=data, filetype="pdf").metadata.get("creationDate") or "")
    return towns, ("%s-%s-%s" % m.groups() if m else None), [final]


@county("Faribault", 15)
def faribault(f):
    # A table set sideways on the page: each row is a column of text lines
    # reading upwards.  Cells, in order: township, title, name, then home
    # and township mailing addresses, which are not read, and a telephone,
    # which is (it is printed in the last cell, sometimes run into the
    # township's city and ZIP code, so only its telephone-shaped text is
    # taken).
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
                add_numbers(towns[town_key(cells[0])][-1], numbers(" | ".join(cells[3:])))
    # The page carries no date; the file's own title ("Township Officers 2025
    # BD.xlsx", from the spreadsheet it was printed from) names the year.
    m = re.search(r"Township Officers (20\d\d)", pymupdf.open(stream=data, filetype="pdf").metadata.get("title") or "")
    return towns, (m.group(1) if m else None), [final]


# ---------------------------------------------------------------- settling

def doc_text(data):
    """The visible text of a document, for counting where a number is
    printed: a PDF's text, a workbook's cells, a page's text without its
    scripts and styles (a tel: link's target is not text, so a linked
    number is counted once)."""
    if data[:4] == b"%PDF":
        return pdf_text(data)
    if data[:2] == b"PK":
        return "\n".join(" | ".join(str(c) for c in r) for r in xlsx_rows(data))
    page = soup(data)
    for t in page(["script", "style"]):
        t.decompose()
    return page.get_text("\n")


def tel_disagreements(data):
    """The keys of every number a page shows in a tel: link that dials a
    different number."""
    if data[:4] == b"%PDF" or data[:2] == b"PK":
        return set()
    bad = set()
    for a in soup(data).find_all("a", href=re.compile(r"^\s*tel:", re.I)):
        dials = re.sub(r"\D", "", re.split(r"[;,]|ext", a["href"], flags=re.I)[0])
        for m in NUMBER_RE.finditer(a.get_text(" ").replace("\xa0", " ")):
            shown = re.sub(r"\D", "", re.sub(r"(?i)\s*(?:ext\.?|x)\s*\d+$", "", m.group(0)))
            if not dials.endswith(shown) or (len(shown) == 10 and dials[-10:] != shown):
                bad |= {number_key(m.group(0)), dials[-7:]}
    return bad


def settle_numbers(towns, docs):
    """Sort each record's numbers into `phone` and `phonesExtra`, in the
    order its list prints them, and return how many were left out and why.

    Left out: a number printed beside two or more different people, or
    printed in the county's documents more often than beside the officers
    who carry it (a town hall's, a town's own contact line, or another
    office's), since either is a line that belongs to an office rather
    than to the person; and every number of an officer whose telephone
    link dials a different number from the one it shows."""
    printed = collections.Counter()
    bad = set()
    for data in docs:
        text = re.sub(r"\s+", " ", doc_text(data).replace("\xa0", " "))
        for m in NUMBER_RE.finditer(text):
            printed[number_key(m.group(0))] += 1
        bad |= tel_disagreements(data)
    people = collections.defaultdict(set)
    attached = collections.Counter()
    for recs in towns.values():
        for rec in recs:
            for n in rec.get("_numbers", []):
                people[number_key(n)].add(re.sub(r"[^a-z]", "", rec["name"].lower()))
                attached[number_key(n)] += 1
    shared = {k for k, names in people.items() if len(names) > 1}
    elsewhere = {k for k in attached if printed[k] > attached[k]}
    left = collections.Counter()
    for recs in towns.values():
        for rec in recs:
            found = rec.pop("_numbers", [])
            if any(number_key(n) in bad for n in found):
                left["a telephone link dials another number"] += len(found)
                continue
            keep, seen = [], set()
            for n in found:
                k = number_key(n)
                if k in shared:
                    left["printed beside two or more people"] += 1
                elif k in elsewhere:
                    left["printed again away from the officer"] += 1
                elif k not in seen:
                    seen.add(k)
                    keep.append(n)
            if keep:
                rec["phone"] = keep[0]
                if keep[1:]:
                    rec["phonesExtra"] = keep[1:]
    return left


def doc_emails(data):
    """Every e-mail address a document prints, lower-cased, once for each
    time it is printed.  In a page an address shown as a link's text is
    counted once, not again for the link's target, and a link whose text is
    a word ("E-mail") prints the address it sends to."""
    if data[:4] == b"%PDF" or data[:2] == b"PK":
        return [m.group(0).lower() for m in EMAIL_RE.finditer(doc_text(data))]
    page = soup(data)
    for t in page(["script", "style"]):
        t.decompose()
    out = [m.group(0).lower() for m in EMAIL_RE.finditer(page.get_text("\n"))]
    for a in page.find_all("a", href=MAILTO_RE):
        address = mailto_address(a["href"])
        if address and "@" not in a.get_text(" "):
            out.append(address)
    return out


def mail_disagreements(data):
    """Every address a page shows as a link's text where the link sends mail
    to a different address, and the address it sends to."""
    if data[:4] == b"%PDF" or data[:2] == b"PK":
        return set()
    bad = set()
    for a in soup(data).find_all("a", href=MAILTO_RE):
        shown = [m.group(0).lower() for m in EMAIL_RE.finditer(a.get_text(" "))]
        target = mailto_address(a["href"])
        if shown and shown != [target]:
            bad |= set(shown) | ({target} if target else set())
    return bad


def settle_emails(towns, docs):
    """Give each record one `email` from the addresses its list prints
    beside the officer, and return how many were left out and why.

    Left out, the same way as a telephone: an address printed beside two or
    more different people, or printed in the county's documents more often
    than beside the officers who carry it (a town's or an office's mailbox),
    since either belongs to an office rather than to the person; and every
    address of an officer whose mail link sends to a different address from
    the one it shows.  Left out as well, by what the address's own name says
    (`mailbox_of`): the town's own mailbox, which is the town's general
    address and not the officer's, and a mailbox named for a different
    office from the one the officer holds, which is printed on the wrong
    row.  A mailbox named for the officer's own office ("clerk@" beside the
    clerk) is how the list says to reach that officer, and is kept.  Where a
    list prints two addresses for one officer, the record keeps one: an
    address on a government's own domain over any other, otherwise the first
    the list prints."""
    printed = collections.Counter()
    bad = set()
    for data in docs:
        printed.update(doc_emails(data))
        bad |= mail_disagreements(data)
    people = collections.defaultdict(set)
    attached = collections.Counter()
    for recs in towns.values():
        for rec in recs:
            for e in rec.get("_emails", []):
                people[e].add(re.sub(r"[^a-z]", "", rec["name"].lower()))
                attached[e] += 1
    shared = {e for e, names in people.items() if len(names) > 1}
    elsewhere = {e for e in attached if printed[e] > attached[e]}
    left = collections.Counter()
    for town, recs in towns.items():
        for rec in recs:
            found = rec.pop("_emails", [])
            if any(e in bad for e in found):
                left["a mail link sends to another address"] += len(set(found))
                continue
            keep = []
            for e in found:
                if e in keep:
                    continue
                if e in shared:
                    left["printed beside two or more people"] += 1
                elif e in elsewhere:
                    left["printed again away from the officer"] += 1
                elif mailbox_of(e, town, rec["office"]) == "town":
                    left["the town's own mailbox"] += 1
                elif mailbox_of(e, town, rec["office"]) == "other office":
                    left["named for another office"] += 1
                else:
                    keep.append(e)
            if keep:
                rec["email"] = ([e for e in keep if government_mailbox(e)] or keep)[0]
                if len(keep) > 1:
                    left["a second address for the same officer"] += len(keep) - 1
    return left


# ---------------------------------------------------------------- main

def run_county(name, f):
    fn, floor = PARSERS[name]
    f.docs = []
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
    # Counts only: a number or an e-mail, like an address, is never printed
    # in a log.
    left = settle_numbers(towns, f.docs)
    left_mail = settle_emails(towns, f.docs)
    recs = [r for t in towns.values() for r in t]
    print("  %s: %d of %d officers carry a telephone, %d a second one; %s" % (
        name, sum(1 for r in recs if r.get("phone")), len(recs),
        sum(1 for r in recs if r.get("phonesExtra")),
        "; ".join("%d left out, %s" % (n, why) for why, n in sorted(left.items()))
        or "none left out"), file=sys.stderr)
    print("  %s: %d of %d officers carry an e-mail; %s" % (
        name, sum(1 for r in recs if r.get("email")), len(recs),
        "; ".join("%d left out, %s" % (n, why) for why, n in sorted(left_mail.items()))
        or "none left out"), file=sys.stderr)
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
