"""Shared reading helpers for the per-county Wisconsin town-board parsers.

WHAT THIS PACKAGE IS FOR. A Wisconsin town is governed by a town board — a
chairperson and two or more supervisors — and no state agency aggregates who
sits on them. Measured 2026-10-15, 50 of the 72 counties publish that list
themselves, most as the county clerk's yearly Official Directory (a PDF), a few
as one web page per town. Each county lays its directory out differently, so
each county gets one small module here exposing:

    COUNTY_FIPS   three-digit county FIPS, as a string ("019")
    COUNTY_NAME   the county's name as the card prints it ("Clark")
    SOURCES       list of urls the module reads (the first is the one cited)
    CLIENT        "token" (default) or "chrome", the client the host serves;
                  "chrome" only where the token was MEASURED refused
    def scrape(ctx) -> dict
        returns {"towns": {town name: [{"name", "role",
                                         "phone"?, "phonesExtra"?}, ...]},
                 "edition": str or None}

and `wi_town_board_scraper.py` runs every module with failure isolation.

WHAT A MODULE MAY RETURN, AND WHAT IT MUST NEVER RETURN. A name, the role the
county prints ("Chairperson", "Supervisor #1"), and the telephone numbers the
county prints beside that officer — nothing else. These directories print home
addresses, telephone numbers and e-mail addresses beside the names. The
telephone numbers ship, whosever line they are, because the county prints them
for the public (Adam, 2026-10-17: "if the official government source uses
personal phone numbers, we publish those"): the first in `phone`, any further
ones in `phonesExtra`, each with the label the county gives it ("cell
715-555-0100"; a one-letter label is written out as the word). The rest stays
out:

  * A home address is never read into a record. A module reads numbers only
    through the readers below, each of which reads numbers and their labels
    and nothing else of a line: `phones_in()` reads a part of a line (after
    the officer's name, or cut off by a dot leader) only when it holds
    nothing but telephone numbers, their labels and an e-mail address;
    `tail_phones()` reads the end of a part from a label that names a
    person's own line ("Cell:", "(H)") onward; `lead_phones()` reads the
    numbers that open a part, up to the last of them; and `end_phones()`
    reads the one number that ends a line which is the officer's own entry.
    The text around what they read (an address, a town hall, a shop) is not
    read, and a number printed inside an address is lost rather than an
    address kept.
  * A number printed more than once anywhere in what a module read — for
    two officers, for an officer and the town hall, or where no officer is
    named — is an office's line and not the person's, and so is a number a
    web page links as tel: to a different number than it shows; `normalize()`
    takes both off every officer who carries them (`shared_numbers`,
    `tel_disagreements`), across every document the module read for its
    county.
  * A fax number, a number marked confidential, and a number whose label
    names a place rather than a person ("Shop:", "Town Hall:") never ship.
  * E-mail addresses are not read, as before.

A module that cannot tell a name from an address must drop the row rather than
guess. Nothing is ever invented to fill a gap: a number printed without an area
code ships exactly as printed, never with one added, and a town whose block
cannot be read is left out and the builder reports it.

THE CLIENT RULE (CLAUDE.md, "Browser user-agent strings"). Every host is asked
with this project's token first. `ctx.fetch` reads robots.txt with the SAME
headers it then crawls with, so a module that declares CLIENT = "chrome" reads
the policy as Chrome too; that declaration must carry, in the module, the date
and the answer the token got.
"""

import html as H
import io
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "scripts"))
from scraper_common import (UA_CHROME_WIN_126, UA_HINTS_CHROME_126,  # noqa: E402
                            UA_ROSTER_BOT, require_robots_once)

UA_TOKEN = {"User-Agent": UA_ROSTER_BOT}
UA_CHROME = {
    "User-Agent": UA_CHROME_WIN_126,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
}
UA_CHROME.update({k: v for k, v in UA_HINTS_CHROME_126.items()
                  if k.lower().startswith("sec-ch-ua")})

LABEL = "wi_town_board_scraper"

# Words that open a role in these directories, longest first so "Town Board
# Chair" wins over "Chair". A module maps its county's spelling onto one of the
# two ROLE values below with `norm_role`.
_CHAIR = re.compile(r"\b(town\s+board\s+)?(chair(wo)?(man|person)?)\b", re.I)
_SUPV = re.compile(r"\b(supervisor|supv\.?|super\.?)\b", re.I)


class Ctx:
    """What a module is handed: fetchers bound to its declared client.

    One second between requests to one host — these are county web servers,
    and a directory module rarely needs more than one or two reads."""

    def __init__(self, client="token", verbose=True):
        if client not in ("token", "chrome"):
            raise ValueError("CLIENT must be 'token' or 'chrome'")
        self.headers = UA_CHROME if client == "chrome" else UA_TOKEN
        self.verbose = verbose
        self._last = {}
        # every document the module read, and the text it was read as, so
        # `read_text` can count a number across all of them
        self.read = {}
        self._texts = {}
        # numbers a page links as tel: to a different number than it shows
        self.tel_disagree = set()

    def _pace(self, host):
        last = self._last.get(host)
        if last is not None:
            wait = 1.1 - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
        self._last[host] = time.time()

    def fetch_bytes(self, url, tries=3, timeout=90):
        if url in self.read:
            # a module reading one document two ways (its text and its
            # words) is given the bytes it already has, not a second request
            return self.read[url]
        host = urllib.parse.urlsplit(url).hostname or url
        try:
            require_robots_once(url, self.headers["User-Agent"],
                                headers=self.headers, label=LABEL)
        except SystemExit:
            raise RuntimeError("robots.txt declined for %s; nothing fetched"
                               % host)
        last = None
        for _ in range(tries):
            self._pace(host)
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    final = r.geturl()
                    fhost = urllib.parse.urlsplit(final).hostname
                    if fhost and fhost != host:
                        # urllib followed a redirect to another host without
                        # asking that host's policy; ask it now, before the
                        # body is used, and refuse the body if it declines
                        try:
                            require_robots_once(final, self.headers["User-Agent"],
                                                headers=self.headers, label=LABEL)
                        except SystemExit:
                            raise RuntimeError("robots.txt declined for %s "
                                               "(redirect target)" % fhost)
                    data = r.read()
                    self.read[url] = data
                    return data
            except RuntimeError:
                raise
            except Exception as exc:          # noqa: BLE001 — retried, then reported
                last = exc
        raise RuntimeError("%s: %s" % (url, last))

    def fetch_text(self, url, **kw):
        page = self.fetch_bytes(url, **kw).decode("utf-8", "replace")
        self._texts.setdefault(url, html_text(page))
        self.tel_disagree |= tel_disagreements(page)
        return page

    def pdf_text(self, url, layout=False, x_tolerance=3, **kw):
        """Every page's text, joined with form feeds. `layout=True` keeps
        pdfplumber's column positions, which a two-column directory needs;
        a smaller `x_tolerance` restores spaces a PDF draws as gaps."""
        text = pdf_text(self.fetch_bytes(url, **kw), layout=layout,
                        x_tolerance=x_tolerance)
        self._texts.setdefault(url, text)
        return text

    def pdf_pages(self, url, **kw):
        import pdfplumber
        data = self.fetch_bytes(url, **kw)
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        self._texts.setdefault(url, "\n\f\n".join(pages))
        return pages

    def pdf_words(self, url, **kw):
        """[(page index, [word dicts with x0, x1, top, bottom, text])]."""
        import pdfplumber
        data = self.fetch_bytes(url, **kw)
        out = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, p in enumerate(pdf.pages):
                out.append((i, p.extract_words(keep_blank_chars=False,
                                               use_text_flow=False)))
        return out

    def docx_text(self, url, **kw):
        text = docx_text(self.fetch_bytes(url, **kw))
        self._texts.setdefault(url, text)
        return text

    def read_text(self):
        """The text of every document the module read, one after another —
        as the module read it where it used one of the readers above, else as
        `document_text` reads it. What `shared_numbers` counts numbers in."""
        return "\n\f\n".join(self._texts.get(url) or document_text(data)
                               for url, data in self.read.items())


def pdf_text(data, layout=False, x_tolerance=3):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n\f\n".join((p.extract_text(layout=layout,
                                               x_tolerance=x_tolerance) or "")
                               for p in pdf.pages)


def _main_digits(s):
    """The digits of a telephone number without its extension or a leading
    country code 1."""
    s = re.split(r"(?i)[,;pw#]|\s*(?:ext\.?|extension|x)\s*(?=[#\d])", s,
                 maxsplit=1)[0]
    d = re.sub(r"\D", "", s)
    return d[1:] if len(d) == 11 and d.startswith("1") else d


def tel_disagreements(page):
    """The numbers a web page links as tel: to a different number than the
    link shows: both the number shown and the number linked, so that neither
    ships (a page that dials one number while showing another cannot say
    which is the officer's)."""
    out = set()
    for href, inner in re.findall(
            r"(?is)<a\b[^>]*?href\s*=\s*[\"']tel:([^\"']*)[\"'][^>]*>(.*?)</a>",
            page or ""):
        shown = html_text(inner)
        m = _TEL.search(_DASHES.sub("-", shown))
        if not m:
            continue
        linked = _main_digits(urllib.parse.unquote(H.unescape(href)))
        seen = _main_digits(m.group(0))
        if linked == seen or (len(seen) == 7 and linked.endswith(seen)):
            continue
        out.update(k for k in (number_key(linked), number_key(m.group(0))) if k)
    return out


def document_text(data):
    """The text of a fetched document, whatever it is: a PDF's pages, a
    .docx's paragraphs, or a web page's visible text."""
    if b"%PDF" in data[:1024]:
        return pdf_text(data)
    if data[:2] == b"PK":
        try:
            return docx_text(data)
        except KeyError:
            return ""
    return html_text(data.decode("utf-8", "replace"))


def docx_text(data):
    """Paragraph text of a .docx, one paragraph per line, table cells tab-joined.
    Read straight out of the zip so no library is needed."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:tc>", "\t", xml)
    xml = re.sub(r"</w:p>|</w:tr>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<w:br/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return H.unescape(text)


def html_text(page):
    """A page's visible text, one block per line."""
    page = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|td|th|dt|dd)>", "\n", page)
    page = re.sub(r"<[^>]+>", " ", page)
    page = H.unescape(page)
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in page.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def clean(s):
    return re.sub(r"\s+", " ", H.unescape(s or "")).strip(" ,;:-–—")


def norm_role(label):
    """'Chairperson' / 'Supervisor' plus any seat the county prints, so the
    card says what the county says: 'Supervisor #1', 'Supervisor II'. Returns
    None for a role that is neither (clerk, treasurer, assessor, constable)."""
    text = clean(label)
    if re.search(r"\bvice\b", text, re.I):
        return None
    if _CHAIR.search(text):
        return "Chairperson"
    m = _SUPV.search(text)
    if m:
        seat = text[m.end():].strip(" .:")
        seat = re.sub(r"^(no\.?|number)\s*", "#", seat, flags=re.I)
        seat = re.match(r"^(#?\s*\d+|[IVX]+\b|1st|2nd|3rd|4th|first|second|"
                        r"third|fourth)", seat, re.I)
        return "Supervisor" + ((" " + seat.group(1).replace(" ", ""))
                               if seat else "")
    return None


_ADDRESS_HINT = re.compile(
    r"\d{3}[-. )]\s*\d{3}[-. ]\d{4}|@|\b\d{5}(-\d{4})?\b|\bP\.?\s?O\.?\s+Box\b|"
    r"^\s*(N|W|E|S)?\d{2,6}\s+\w", re.I)


def looks_like_person(name):
    """A conservative test that a parsed string is a name and not an address,
    a phone number or a heading. A module drops any row this rejects."""
    name = clean(name)
    # a slash is a second duty printed after a seat ("Supervisor 2/Animal
    # Control"), never part of a name
    if not name or len(name) > 60 or "/" in name or _ADDRESS_HINT.search(name):
        return False
    # Words that are never part of a name. Street words that are also
    # surnames (Hall, Lane, Street, Drive, Box) are deliberately absent: an
    # address is caught by its house number, ZIP or PO Box above, and the
    # word list dropped a real supervisor, Donald Hall (Greenfield, Monroe).
    if re.search(r"\b(town|village|city|county|rd|ave|ln|"
                 r"wi|wisconsin|vacant|clerk|treasurer|"
                 r"assessor|constable|chair|supervisor|term|expires|phone|"
                 r"fax|email|e-mail|meeting|hours)\b", name, re.I):
        return False
    words = name.replace(".", " ").split()
    return 2 <= len(words) <= 6 and any(w[:1].isupper() for w in words)


def person(name, role, phones=(), shared=()):
    """One board member's record. `phones` are strings from `phones_in()` in
    the county's order; a number in `shared` (`shared_numbers()`) is the
    town's line and is left off, and a number printed twice is kept once."""
    name = clean(name)
    # a sentence's full stop left on a surname ("Bruce Elmer."), never an
    # initial's ("Roger B.")
    name = re.sub(r"(?<=[a-z]{2})\.$", "", name)
    out = {"name": name, "role": role}
    keep, seen = [], set()
    for p in phones or ():
        key = number_key(p)
        if not key or key in seen or key in shared:
            continue
        seen.add(key)
        keep.append(clean_phone(p))
    if keep:
        out["phone"] = keep[0]
    if len(keep) > 1:
        out["phonesExtra"] = keep[1:]
    return out


def phones_of(rec):
    """The numbers a record carries, `phone` first, in the county's order."""
    return [p for p in [rec.get("phone")] + list(rec.get("phonesExtra") or [])
            if p]


_LEADER = re.compile(r"\s*\.{3,}.*$")
_EMAIL = re.compile(r"\S+@\S+")
# an e-mail address as some directories set it, with a space before its
# last dot ("name@town .com"): what `phone_only` passes over
_EMAIL_SET = re.compile(r"\S+\s?@\s?\S+(?:\s+\.\s*(?:com|net|org|gov|us|edu|"
                        r"info|biz)\b)?", re.I)
_PHONE = re.compile(r"\(?\d{3}\)?[-. ]?\d{3}[-. ]\d{4}")

# ---- telephone numbers -------------------------------------------------
#
# A number as these directories print it: "(715) 555-0100", "715-555-0100",
# "715.555.0100", "715 555-0100", "715 555 0100", "715- 555-0100", or
# "555-0100" with no area code, which ships exactly as printed: an area code is
# never added, because
# a mobile can be issued anywhere and a wrong guess reaches a stranger. Never
# inside a longer run of digits, so a ZIP+4 ("54806-1234") or a span of years
# ("2026-2027") is not read as one.
_DASHES = re.compile("[‐-―−]")
_EXT = r"(?:\s*,?\s*(?:ext\.?|extension|x)\s*#?\s*\d{1,5})"
_TEL = re.compile(
    r"(?<![\w\-])"
    r"(?:(?:\(\d{3}\)\s*[-.]?\s*|\d{3}\s?[-./ ]\s?)?\d{3}\s?[-.]\s?\d{4}"
    # "608 555 0100": spaces alone are read only with the area code
    r"|\d{3} \d{3} \d{4})" + _EXT + r"?"
    r"(?![\w\-])", re.I)
# The label a directory prints beside a number, and the word it ships as. A
# label that maps to "" says only that this is a telephone; one that maps to
# None names a place, never a person, and its number is not taken.
_LABELS = {
    "cell": "cell", "cellular": "cell", "cell phone": "cell", "c": "cell",
    "mobile": "mobile", "m": "mobile",
    "home": "home", "home phone": "home", "h": "home",
    "res": "residence", "residence": "residence", "personal": "personal",
    "work": "work", "work phone": "work", "w": "work",
    "business": "business", "bus": "business", "b": "business",
    "office": "office", "office phone": "office", "o": "office",
    "phone": "", "ph": "", "p": "", "tel": "", "telephone": "",
    "phone number": "", "telephone number": "",
}
_FAX = ("fax", "f", "telephone/fax", "phone/fax", "ph/fax", "tel/fax",
        "fax/phone")
_WORDS = "|".join(re.escape(w).replace(r"\ ", r"\s+")
                  for w in sorted(set(_LABELS) | set(_FAX), key=len, reverse=True))
# a label just before a number ("Cell: ", "(H) ", "Home Phone #")
_BEFORE = re.compile(r"(?:\(\s*(?P<b>%s)\s*\)|\b(?P<w>%s))\.?\s*(?:#|no\.)?"
                     r"\s*[:\-–]?\s*$" % (_WORDS, _WORDS), re.I)
# a label just after one ("715-555-0100 (C)", "715-555-0100 cell")
_AFTER = re.compile(r"^\s*(?:\(\s*(?P<b>%s)\s*\)|[-–~/]?\s*(?P<w>cell|cellular|"
                    r"home|work|office|mobile|fax)\b\.?)" % _WORDS, re.I)
# the words a part of a line may hold beside its numbers and still be read
# ("E-mail: N/A" says there is no e-mail address)
_FILLER = re.compile(r"(?i)\b(?:or|and|e-?mail|ext|extension|x|n/a|none|%s)\b"
                     % _WORDS)


def clean_phone(s):
    s = _DASHES.sub("-", s or "")
    return re.sub(r"\s+", " ", s).strip(" ,;:")


def number_key(s):
    """The last seven digits of a number, its extension left off, so a line
    printed with and without its area code compares equal."""
    s = re.sub(r"(?i)" + _EXT + r"\s*$", "", clean_phone(s))
    digits = re.sub(r"\D", "", s)
    return digits[-7:] if len(digits) >= 7 else None


def numbers_in(text):
    """The key of every telephone number in `text`, a fax or a town hall's
    line included: what `shared_numbers` counts."""
    return [number_key(m.group(0))
            for m in _TEL.finditer(_DASHES.sub("-", text or ""))]


def name_on(name, line):
    """True when an officer's name is printed on a line, word for word."""
    words = clean(name).split()
    return bool(words) and re.search(
        r"(?<!\w)" + r"\s*".join(re.escape(w) for w in words) + r"(?!\w)",
        _DASHES.sub("-", line or ""), re.I) is not None


def _phone_line(line):
    """A line holding nothing but telephone numbers, their labels and an
    e-mail address, dot leaders aside."""
    parts = leader_parts(line)
    return bool(parts) and all(phone_only(p) or not re.search(r"[A-Za-z0-9]", p)
                               for p in parts) and any(phone_only(p) for p in parts)


# what marks a line as a home address (a house number opening it, a PO
# box, a ZIP code), and the words that mark an address as a place's
_HOME_ADDRESS = re.compile(r"^\W*[NSEW]?\d{1,6}[A-Z]?\s+\w|\bP\.?\s?O\.?\s+Box\b|"
                           r"(?<![\d-])\d{5}(?:-\d{4})?(?![\d-])", re.I)
_PLACE_WORDS = re.compile(r"(?i)\b(?:hall|garage|shop|office|building|station|"
                          r"center|centre)\b")


def shared_numbers(text, owners=()):
    """The numbers that are an office's line rather than a person's: every
    number printed more than once in `text` (a county's whole directory, or
    every page read for it), unless each place it is printed names one and
    the same officer in `owners` — a chair whose own number the county prints
    again beside his name as weed commissioner is still his. A place is the
    line the number is on, or, for a line holding nothing but numbers, the
    entry it sits in: the nearest line above naming an officer, across no
    more than an address and an e-mail line ("Chairman ...... Al Thompson" /
    "608-555-0100"), and for a home address line carrying a number, the
    line directly above it when that line names an officer.
    A number printed for two officers, for an officer and the town hall, or
    where no officer is named, never ships on a person."""
    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    where = {}
    for i, ln in enumerate(lines):
        for k in numbers_in(ln):
            if k:
                where.setdefault(k, []).append(i)
    owners = sorted({clean(o) for o in owners if o})

    def named(i):
        return [o for o in owners if name_on(o, lines[i])]

    def above(i):
        # the officer whose entry a numbers-only line belongs to: the nearest
        # line above it that names one, passing only address, e-mail and
        # other number lines; another office or another name ends the search
        for j in range(i - 1, max(-1, i - 5), -1):
            on = named(j)
            if on:
                return on
            if OTHER_OFFICE.search(_EMAIL.sub(" ", lines[j])) or (
                    not _phone_line(lines[j])
                    and looks_like_person(strip_contact(lines[j]))):
                return []
        return []

    def address_owner(i):
        # a line holding a home address and a number, directly under the
        # line naming the officer it belongs to ("District 2 ..... JIM
        # ASHBACH" / "N1234 County Rd, Ellsworth ..... (715) 555-0100"); a
        # town hall's, a shop's or an office's address line is never one
        ln = lines[i]
        if (i == 0 or OTHER_OFFICE.search(_EMAIL.sub(" ", ln))
                or _PLACE_WORDS.search(ln) or not _HOME_ADDRESS.search(ln)):
            return []
        return named(i - 1)

    shared = set()
    for k, rows in where.items():
        if len(rows) < 2:
            continue
        holders = set()
        for i in rows:
            on = named(i)
            if not on:
                on = above(i) if _phone_line(lines[i]) else address_owner(i)
            if len(on) != 1:
                holders = None
                break
            holders.add(on[0])
        if holders is None or len(holders) != 1:
            shared.add(k)
    return shared


def normalize(towns, ctx):
    """What a module returned, as it ships: rows that are not a board member
    dropped, and each member's numbers kept only where they are the
    member's own — a number `shared_numbers` finds anywhere in what the
    module read (`ctx.read_text()`) is taken off every member who carries
    it, and so is a number a page links as tel: to a different number than
    it shows (`tel_disagreements`). Returns (towns, rows dropped, numbers
    taken off)."""
    owners = [p.get("name") for ps in towns.values() for p in ps]
    shared = shared_numbers(ctx.read_text(), owners) | ctx.tel_disagree
    out, dropped, taken = {}, 0, 0
    for town, people in towns.items():
        keep = []
        for p in people:
            if not p.get("role") or not looks_like_person(p.get("name")):
                dropped += 1
                continue
            rec = person(p["name"], p["role"], phones_of(p), shared)
            taken += len(phones_of(p)) - len(phones_of(rec))
            keep.append(rec)
        if keep:
            out[clean(town)] = keep
    return out, dropped, taken


def phone_only(part):
    """True when a part of a line holds at least one telephone number and
    nothing else but labels, an e-mail address and punctuation, so reading
    its numbers cannot read an address, a town hall or a shop with them."""
    part = _DASHES.sub("-", part or "")
    if not _TEL.search(part):
        return False
    rest = _EMAIL_SET.sub(" ", _TEL.sub(" ", part))
    return not re.search(r"[A-Za-z0-9]", _FILLER.sub(" ", rest))


def _label(hit):
    if not hit:
        return None
    return re.sub(r"\s+", " ", (hit.group("b") or hit.group("w")).lower())


def _specific(label):
    return label is not None and (label in _FAX or _LABELS.get(label) != "")


def phones_in(part):
    """The telephone numbers in a part of a line that `phone_only` accepts,
    each as "label number" with the county's label written out, or the number
    alone where the county gives no label. A fax number is left out, and the
    whole part is left out when it holds anything but numbers and labels."""
    part = re.sub(r"\s+", " ", _DASHES.sub("-", part or ""))
    if not phone_only(part):
        return []
    hits = list(_TEL.finditer(part))
    gaps = [part[(hits[i - 1].end() if i else 0):h.start()]
            for i, h in enumerate(hits)] + [part[hits[-1].end():]]
    before = [_label(_BEFORE.search(g)) for g in gaps[:-1]]
    after = [_label(_AFTER.match(g)) for g in gaps[1:]]
    # A part labels its numbers on one side: "H 555-0100 C 555-0101" or
    # "555-0100 (H) 555-0101 (C)". The side is the one that labels the
    # first number (or, failing that, the last); a lone number takes
    # whichever side says more than "phone".
    if len(hits) == 1:
        labels = [before[0] if _specific(before[0]) or not _specific(after[0])
                  else after[0]]
    elif _specific(before[0]) or not _specific(after[-1]):
        labels = before
    else:
        labels = after
    out = []
    for h, label in zip(hits, labels):
        if label in _FAX:
            continue
        word = _LABELS.get(label, "") if label else ""
        number = clean_phone(h.group(0))
        number = re.sub(r"(?i)\s*,?\s*(?:ext\.?|extension|x)\s*#?\s*(\d{1,5})$",
                        r" ext. \1", number)
        out.append((word + " " + number) if word else number)
    return out


def leader_parts(line):
    """A line cut at its dot leaders (". . . ." too) and bullets: "Name ......
    715-555-0100" and "address ...... cell 715-555-0101" each become two
    parts."""
    return [p for p in re.split(r"\s*(?:\.{2,}|(?:\.\s+){2,}\.?|…+|•)\s*",
                                line or "")
            if p.strip()]


def phone_line_numbers(line):
    """The numbers on a line that holds nothing but numbers and their labels,
    in the order printed (one string each), or [] for any other line."""
    return line_phones(line) if _phone_line(line) else []


# A label that names a person's own line, which is what lets a number be
# read off the end of a part that holds an address first ("... WI 54806
# Cell: (715) 555-0100", "... (cell) 715-555-0100"). "Phone" alone is not
# one: on a town hall's address line it is the town's.
_TAIL_WORDS = (r"cell(?:ular)?(?:\s+phone)?|mobile|home(?:\s+phone)?|"
               r"residence|personal|work(?:\s+phone)?|business")
_TAIL_LABEL = re.compile(r"\(\s*(?:c|h|w|b|m|res|bus|%s)\s*\)|\b(?:%s)\b"
                         % (_TAIL_WORDS, _TAIL_WORDS), re.I)
# the word just before such a label names a place, not a person ("Town Cell
# Phone:", "Shop cell")
_PLACE_BEFORE = re.compile(
    r"(?i)\b(?:town|village|city|county|hall|office|shop|garage|fire|"
    r"station|clerk|treasurer|board|department|dept|building|center|centre|"
    r"library|school|church|company|co|inc|llc)\W*$")


# a part that says a number is withheld is never read by the readers below,
# which read a number beside other text ("Phone: Confidential" holds none,
# and `phones_in` refuses any part holding such a word)
_WITHHELD = re.compile(r"(?i)\b(?:confidential|unlisted|withheld|unpublished|"
                       r"not\s+published|do\s+not\s+(?:publish|call))\b")


def tail_phones(part):
    """The numbers at the END of a part that holds something else first (an
    address), read from the label onward only, and only where that label
    names a person's line and the word before it does not name a place. The
    text before the label is not read."""
    part = re.sub(r"\s+", " ", _DASHES.sub("-", part or ""))
    if _WITHHELD.search(part):
        return []
    for m in _TAIL_LABEL.finditer(part):
        rest = part[m.start():]
        if (m.start() and phone_only(rest)
                and not _PLACE_BEFORE.search(part[:m.start()])):
            return phones_in(rest)
    return []


# a label set after its number, as `phones_in` reads one: a word, or any
# label in brackets ("715-555-0100 Cell", "715-555-0100 (H)")
_AFTER_WORD = (r"(?:\s*(?:\(\s*(?:%s)\s*\)|[-–~/]?\s*(?:cell|cellular|home|work|"
               r"office|mobile|fax)\b\.?))?" % _WORDS)
_LEAD = re.compile(
    r"^\s*(?:(?:%s)\b\.?\s*[:\-–]?\s*)?%s%s"
    r"(?:\s*(?:or|and|/|,|;)?\s*(?:(?:%s)\b\.?\s*[:\-–]?\s*)?%s%s)*"
    % (_WORDS, _TEL.pattern, _AFTER_WORD, _WORDS, _TEL.pattern, _AFTER_WORD),
    re.I)


def lead_phones(part):
    """The numbers at the START of a part that holds something else after
    them (a table row's address column: "715-555-0100 Cell 1234 Main St"),
    read up to the last number and its label only. What follows is not
    read."""
    part = re.sub(r"\s+", " ", _DASHES.sub("-", part or ""))
    if _WITHHELD.search(part):
        return []
    m = _LEAD.match(part)
    return phones_in(m.group(0)) if m else []


def end_phones(part):
    """The number that ENDS a part holding the officer's own address first
    ("..., Couderay, WI 54862. 715-555-0100", "... WI 54862 - 715-555-0100"),
    read on its own with the label before it, if any. Only for a line that
    is the officer's own entry (it opens with the officer's office or name),
    never for an address under a heading, which can be a town hall's; the
    text before the number is not read."""
    part = re.sub(r"\s+", " ", _DASHES.sub("-", part or "")).strip()
    if _WITHHELD.search(part):
        return []
    # "WI 54862 -715-555-0100": the dash is a separator, not part of it
    part = re.sub(r"(?<=\s)-(?=\d)", "- ", part)
    tail = tail_phones(part)
    if tail:
        return tail
    hits = list(_TEL.finditer(part))
    if not hits or part[hits[-1].end():].strip(" .,;"):
        return []
    before = part[:hits[-1].start()]
    if before and (not re.search(r"[\s.,;:\-–]$", before)
                   or _PLACE_BEFORE.search(before.rstrip(" .,;:-–"))):
        return []
    return phones_in(part[hits[-1].start():])


def line_phones(line):
    """The numbers in every leader-part of a line: a part holding nothing
    but numbers is read whole (`phones_in`); a part holding an address is
    read only from a person's label at its end onward (`tail_phones`)."""
    out = []
    for part in leader_parts(line):
        out.extend(phones_in(part) or tail_phones(part))
    return out


def phones_after_name(line, name):
    """The numbers on the line that carries an officer's name, read from the
    text AFTER the name only ("Name – (715) 555-0100 ...... 123 Main St.",
    "Name email ....... 715-555-0100"), each leader-part read only when it
    holds nothing but numbers. Nothing is read when the name cannot be found
    on the line exactly, rather than guessing where it ends."""
    text = _DASHES.sub("-", line or "")
    words = clean(name).split()
    if not words:
        return []
    m = re.search(r"\s*".join(re.escape(w) for w in words), text, re.I)
    if not m:
        return []
    return line_phones(text[m.end():])


# A line that opens another office ends the lines a board member's numbers
# are read from. Board roles end it too (see `role_then_name`).
OTHER_OFFICE = re.compile(
    r"(?i)^\W*(?:town\s+)?(?:clerk|treasurer|assessor|constable|deputy|"
    r"zoning|building|road|patrol|polling|municipal\s+judge|judge|weed|fire|"
    r"attorney|engineer|inspector|administrator|plan|county\s+board|"
    r"chair\w*|supervisor\w*|supv\b|vice|website|meeting|town\s+hall|"
    r"office\s+hours|elected|appointed)\b")


# a line holding nothing but a label, whose number is on the next line
# ("Phone" / "(920) 555-0100", "Fax" / "(920) 555-0101")
_LABEL_LINE = re.compile(r"(?i)^\(?\s*(?:%s)\s*\)?\.?\s*(?:#|no\.)?\s*:?\s*$" % _WORDS)


def following_phones(lines, start, limit=4, stop_re=None):
    """Numbers on the lines after an officer's name line, `lines[start:]`: a
    line is read only through `line_phones`, and the run stops at the next
    office, the next name, or after `limit` lines, so a number is never
    carried over from the officer below. A line holding only a label is read
    with the line after it, so "Fax" over a number keeps that number off."""
    out = []
    label = ""
    for ln in lines[start:start + limit]:
        # an e-mail address can open with an office ("chair@town...")
        if (OTHER_OFFICE.search(_EMAIL.sub(" ", ln))
                or (stop_re and re.search(stop_re, ln))):
            break
        if _LABEL_LINE.match(ln):
            label = ln
            continue
        if label:
            ln, label = label + " " + ln, ""
        if not _phone_line(ln) and looks_like_person(strip_contact(ln)):
            break
        out.extend(line_phones(ln))
    return out


def strip_contact(line):
    """A directory line with its dot leader, telephone numbers and e-mail
    addresses taken off, leaving whatever text came first (normally a name)."""
    line = _LEADER.sub("", line)
    line = _EMAIL.sub(" ", line)
    line = _PHONE.sub(" ", line)
    return clean(line)


def split_blocks(text, header_re):
    """[(town name, block text)] for every match of `header_re`, whose group
    1 is the town's name; each block runs to the next header."""
    hits = list(re.finditer(header_re, text))
    out = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        out.append((clean(m.group(1)), text[m.end():end]))
    return out


def role_then_name(block, stop_re=None, follow=True):
    """People from a block laid out as a role line followed by the name line
    ("Chairperson" / "Mitchel Malm ....... 715-255-8447"). A role line that also
    carries the name after it ("Chairperson: Mitchel Malm") is read too. Only the
    chair and supervisors are returned; `stop_re` ends the block early (a later
    section of the page that is not the board).

    Each person's numbers are read from the text after the office on an
    office line that has no name on it, from the text after the name on the
    name line and, unless `follow` is False, from the lines after it up to the
    next office or name (`following_phones`). Which of them are the town's own
    line is decided across the whole directory by `normalize`."""
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    people = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if stop_re and re.search(stop_re, ln):
            break
        head = strip_contact(ln)
        m = re.match(r"^((?:town\s+board\s+)?(?:chair\w*|supervisor\w*|supv\.?)"
                     r"(?:\s*(?:#|no\.?)?\s*(?:\d+|[IVX]+\b))?)\s*[:\-–]?\s*(.*)$",
                     head, re.I)
        role = norm_role(m.group(1)) if m else None
        if role:
            rest = clean(m.group(2))
            if rest and looks_like_person(rest):
                phones = phones_after_name(ln, rest)
                if follow:
                    phones += following_phones(lines, i + 1, stop_re=stop_re)
                people.append(person(rest, role, phones))
            elif i + 1 < len(lines):
                nxt = strip_contact(lines[i + 1])
                if looks_like_person(nxt):
                    # a number printed after the office on its own line
                    # ("Supervisor ...... 262-555-0100" / "Lyle Boucher
                    # email") is the officer's below it
                    phones = phones_after_name(ln, m.group(1))
                    phones += phones_after_name(lines[i + 1], nxt)
                    if follow:
                        phones += following_phones(lines, i + 2, stop_re=stop_re)
                    people.append(person(nxt, role, phones))
                    i += 1
        i += 1
    return people
