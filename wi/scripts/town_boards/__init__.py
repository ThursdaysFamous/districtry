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
        returns {"towns": {town name: [{"name", "role"}, ...]},
                 "edition": str or None}

and `wi_town_board_scraper.py` runs every module with failure isolation.

WHAT A MODULE MAY RETURN, AND WHAT IT MUST NEVER RETURN. Names and the role the
county prints ("Chairperson", "Supervisor #1") — nothing else. These
directories print home addresses, home telephone numbers and personal e-mail
addresses beside the names, and none of that ships: a town supervisor's house is
not their office. A module that cannot tell a name from an address must drop the
row rather than guess. Nothing is ever invented to fill a gap; a town whose
block cannot be read is left out and the builder reports it.

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

    def _pace(self, host):
        last = self._last.get(host)
        if last is not None:
            wait = 1.1 - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
        self._last[host] = time.time()

    def fetch_bytes(self, url, tries=3, timeout=90):
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
                    return r.read()
            except RuntimeError:
                raise
            except Exception as exc:          # noqa: BLE001 — retried, then reported
                last = exc
        raise RuntimeError("%s: %s" % (url, last))

    def fetch_text(self, url, **kw):
        return self.fetch_bytes(url, **kw).decode("utf-8", "replace")

    def pdf_text(self, url, layout=False, **kw):
        """Every page's text, joined with form feeds. `layout=True` keeps
        pdfplumber's column positions, which a two-column directory needs."""
        return pdf_text(self.fetch_bytes(url, **kw), layout=layout)

    def pdf_pages(self, url, **kw):
        import pdfplumber
        data = self.fetch_bytes(url, **kw)
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return [p.extract_text() or "" for p in pdf.pages]

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
        return docx_text(self.fetch_bytes(url, **kw))


def pdf_text(data, layout=False):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n\f\n".join((p.extract_text(layout=layout) or "") for p in pdf.pages)


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


def person(name, role):
    name = clean(name)
    # a sentence's full stop left on a surname ("Bruce Elmer."), never an
    # initial's ("Roger B.")
    name = re.sub(r"(?<=[a-z]{2})\.$", "", name)
    return {"name": name, "role": role}


_LEADER = re.compile(r"\s*\.{3,}.*$")
_EMAIL = re.compile(r"\S+@\S+")
_PHONE = re.compile(r"\(?\d{3}\)?[-. ]?\d{3}[-. ]\d{4}")


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


def role_then_name(block, stop_re=None):
    """People from a block laid out as a role line followed by the name line
    ("Chairperson" / "Mitchel Malm ....... 715-255-8447"). A role line that also
    carries the name after it ("Chairperson: Mitchel Malm") is read too. Only the
    chair and supervisors are returned; `stop_re` ends the block early (a later
    section of the page that is not the board)."""
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
                people.append(person(rest, role))
            elif i + 1 < len(lines):
                nxt = strip_contact(lines[i + 1])
                if looks_like_person(nxt):
                    people.append(person(nxt, role))
                    i += 1
        i += 1
    return people
