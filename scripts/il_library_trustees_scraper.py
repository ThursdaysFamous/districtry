#!/usr/bin/env python3
"""Trustees for the statewide library layer's cards, from each library's own site.

il_library_contacts_scraper.py closed most of the statewide-library-officials
gap and named the half it could not: "IT STILL NAMES NO TRUSTEE, and that is an
access control rather than a hole in the source" — L2's Staff List and Annual
Certification both answer 403 behind a sign-in, and neither is worked around.
So the trustees have to come from the only other publisher there is, which is
each library itself.

THE POOL IS 176 LIBRARIES, not 373 and not 487. A library whose Annual
Financial Report already names a board needs nothing from here, and one that
publishes no website cannot be read at all; what is left is the card that names
no board and links a site — measured on the shipped files, 176 of the layer's
382 distinct libraries. That number is DERIVED on every run from those same
files rather than written down, so a library that starts filing an AFR leaves
this pool by itself.

ROBOTS FIRST, THROUGH THE ONE READER. Every host is asked through
scripts/robots_policy.py as the client that fetches, before its first request,
and a stated Crawl-delay is honoured per host through HostPacer. A refusal is
recorded as a refusal and nothing is fetched from that host: measured
2026-09-25 over the pool, Bloomington Public Library and Lincoln Library both
serve `Disallow`, and Bloomington is the host that carries ANOTHER library's
board (see the contracting trap below), so that trap is currently moot and the
guard against it is kept anyway.

WHAT IS READ, IN THREE HOPS AT MOST. The library's home page; a link on it whose
text or path names a board; and, where the home page names none, at most two
same-origin About-shaped pages, because a home page with no board link is not a
library that publishes no board. Nothing is fetched beyond that.

THE TRAP THAT DECIDES THE DESIGN. Two of the pool's libraries contract with a
neighbour and publish that neighbour's site as their own — Golden Prairie's is
bloomingtonlibrary.org, Milan-Blackhawk's is rockislandlibrary.org — and
rockislandlibrary.org has ONE board page, which is Rock Island's board and not
Milan-Blackhawk's. Taking the board a page publishes would therefore ship the
wrong people under the right name, which is the failure this project's honesty
rules exist to prevent. So a board ships only from a page that NAMES the library
it is being attributed to, and where two board sections are found the section
heading has to name it.

WHAT THE PARSER DOES NOT DO. It does not read a PDF, does not follow a "Read
more", and does not guess. Measured across the pages fetched on 2026-09-25, a
page that lists its trustees does so in one of five shapes, all of them handled
here and all of them in --selftest; anything else yields nothing and the library
is reported unread rather than filled in. Freeport, Harrisburg and Jerseyville
are the measured examples: each has a board page, each hides the list behind a
"Read more" or renders it in script, and each ships nobody.

Usage:
    python3 il_library_trustees_scraper.py [--out FILE] [--limit N] [--selftest]
"""

import argparse
import datetime
import html
import html.parser
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robots_policy import RobotsGate, HostPacer          # noqa: E402
from scraper_common import fetch_stdlib, make_fail       # noqa: E402

USER_AGENT = "districtry/1.0 (+https://districtry.com/il/)"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

fail = make_fail("il-library-trustees")

# ---------------------------------------------------------------- the page ---

BLOCKS = {"p", "div", "li", "td", "th", "tr", "h1", "h2", "h3", "h4", "h5",
          "h6", "section", "article", "header", "footer", "dt", "dd",
          "figcaption", "blockquote", "address", "span", "strong", "b", "em",
          "a", "label"}
HEADS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# `nav` only. `aside` and `footer` were dropped too in one draft and Alpha Park
# Public Library District's seven trustees went with them -- that site lists
# them inside <aside class="subteaser-list">, which is content, not navigation.
DROP = {"script", "style", "noscript", "svg", "head", "select", "option",
        "textarea", "nav"}


class _Blocks(html.parser.HTMLParser):
    """Visible text, one record per block element, headings kept as headings."""

    def __init__(self):
        html.parser.HTMLParser.__init__(self, convert_charrefs=True)
        self.out, self._buf, self._stack, self._drop = [], [], [], 0

    def _flush(self):
        text = re.sub(r"\s+", " ", "".join(self._buf)).replace(" ", " ").strip()
        if text:
            kind = next((k for k in reversed(self._stack) if k in HEADS), None)
            self.out.append((kind or (self._stack[-1] if self._stack else "text"), text))
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in DROP:
            self._drop += 1
            return
        if self._drop:
            return
        if tag in ("br", "hr"):
            self._flush()
            return
        if tag in BLOCKS:
            self._flush()
            self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag in DROP:
            self._drop = max(0, self._drop - 1)
            return
        if self._drop:
            return
        if tag in BLOCKS:
            self._flush()
            if tag in self._stack:
                while self._stack:
                    if self._stack.pop() == tag:
                        break

    def handle_data(self, data):
        if not self._drop:
            self._buf.append(data)

    def close(self):
        html.parser.HTMLParser.close(self)
        self._flush()


def blocks(body):
    reader = _Blocks()
    try:
        reader.feed(body)
        reader.close()
    except Exception:                                           # noqa: BLE001
        pass                    # a malformed page yields what it parsed
    return reader.out


# -------------------------------------------------------------- the reading ---

BOARD_HEAD = re.compile(r"(?i)\b(board of (?:library )?trustees|library board"
                        r"|board of directors|board members|our board"
                        r"|library trustees|board of library directors"
                        r"|trustees|the board)\b|^\s*members\s*$", re.I)
# A heading that names a board and still introduces no roster. STOP_HEAD's
# wider vocabulary ENDS a section; excluding a heading from OPENING one on
# "contact" cost Gridley Public Library District its six trustees, which sit
# directly under "Contact the Library Board".
NOT_A_ROSTER = re.compile(r"(?i)\b(staff|agendas?|minutes|by-?laws|policies|"
                          r"documents?|meetings?|budget|newsletter|past|former|"
                          r"emeritus|honorary|history|history of)\b")
STOP_HEAD = re.compile(r"(?i)\b(staff|agendas?|minutes|hours|contact|policies|"
                       r"navigation|meetings?|by-?laws|budget|donate|events|"
                       r"news|friends|foundation|history|services|catalog|"
                       r"employment|volunteer|newsletter|faq|director)\b")

ROLES = (r"president|vice[\s-]?president|1st vice[\s-]?president|"
         r"2nd vice[\s-]?president|secretary\s*[/&-]\s*treasurer|"
         r"secretary|treasurer|trustee|board member|member|"
         r"chair(?:man|person|woman)?|vice[\s-]?chair(?:man|person|woman)?|"
         r"at[\s-]?large")
ROLE_ONLY = re.compile(r"(?i)^(?:board\s+)?(%s)\b[\s,.:–—-]*$" % ROLES)
ROLE_LEAD = re.compile(r"(?i)^(?:board\s+)?(%s)\s*[:\-–—]\s*(.+)$" % ROLES)
ROLE_TAIL = re.compile(r"(?i)^(.+?)\s*[,\-–—]\s*(?:board\s+)?(%s)\b[\s,.:]*$" % ROLES)

# A term, election or date a library prints beside a trustee's name.
TERM_TAIL = re.compile(r"(?i)[\s,;–—-]*\(?\b(term\s+)?(expires?|expiration|"
                       r"thru|through|until)\b.*$")
ELECTED_TAIL = re.compile(r"(?i)[\s,;–—-]*\b(re-?elected|elected|appointed|"
                          r"since|joined|seated)\b.*$")
YEAR_TAIL = re.compile(r"[\s,;–—-]*\(?\b(19|20)\d\d\s*([-–—/]\s*(19|20)?\d\d)?\)?\s*$")
DATE_TAIL = re.compile(r"[\s,;–—-]*\(?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\)?\s*$")

# A word a person here is never named with, so a navigation label or a section
# title cannot be read as a name. MEASURED against all 13,094 names the fleet
# ships: every entry below rejects ZERO of them. The words a first draft also
# carried — ward, link, page, close, street, skip, more, and every month, season
# and weekday — cost 60 real people (Trevor Ward is a trustee on the first board
# page this parser was written against), so they are not here. The four that DO
# collide (public, village, vacant, phone) collide only with records that are not
# names either, which is the behaviour wanted.
NOT_NAME = {
    "library", "libraries", "board", "trustee", "trustees", "district", "home",
    "about", "us", "news", "events", "services", "resources", "hours",
    "contact", "search", "catalog", "calendar", "policies", "policy",
    "agenda", "agendas", "minutes", "meeting", "meetings", "bylaws", "bylaw",
    "navigation", "staff", "director", "directors", "president", "secretary",
    "treasurer", "member", "members", "public", "email", "e-mail", "phone",
    "address", "city", "county", "township", "town", "village", "illinois",
    "il", "open", "closed", "kids", "teens", "adult", "adults", "children",
    "youth", "books", "ebooks", "digital", "online", "account", "renew",
    "reserve", "room", "rooms", "programs", "program", "genealogy",
    "computers", "wifi", "printing", "notary", "museum", "pass", "passes",
    "story", "storytime", "term", "terms", "expires", "appointed", "elected",
    "vacant", "vacancy", "site", "map", "login", "log", "sign", "main",
    "content", "menu", "view", "click", "here", "links", "facebook",
    "twitter", "instagram", "youtube", "copyright", "rights", "reserved",
    "privacy", "accessibility", "translate", "espanol", "español", "chair",
    "vice", "officers", "general", "committee", "committees", "annual",
    "report", "reports", "welcome", "notice", "notices", "information",
    "learn", "reading",
    # Job titles a board page prints as a block of its own. Measured the same
    # way: together they reject ONE of the fleet's 13,094 names, and that one is
    # the literal "VILLAGE ADMINISTRATOR", which is not a name either.
    "officer", "foia", "administrator", "custodian", "clerk", "librarian",
    "assistant", "manager", "bookkeeper", "attorney", "counsel", "emeritus",
    "superintendent", "coordinator", "supervisor", "liaison", "position",
    "postition", "mailing", "documents", "document", "meet",
}

# A word that can open a label and never a person's name. MEASURED across the
# 2,129 distinct first tokens of the fleet's 13,094 names: not one of these
# begins any of them. It is a FIRST-token rule rather than a stoplist because
# each of these words is fine inside a later token; what it catches is banner
# text that passes every other test, including the fleet's own names gate,
# which accepts both "No Overdue Fines" and "Strategic Plan" as names. On this
# page the parser is the only guard against them.
NOT_FIRST = {"no", "not", "the", "and", "or", "all", "any", "our", "your",
             "new", "free", "every", "each", "send", "view", "read", "learn",
             "click", "this", "that", "these", "those", "strategic", "current",
             "former", "past", "full", "half", "one", "two", "three"}


NAME_TOKEN = re.compile(r"^(?:[A-Z][A-Za-z'’’.-]*|[A-Z]\.|\"[A-Z][^\"]*\")$")
PARTICLE = {"van", "von", "de", "del", "della", "der", "di", "da", "la", "le",
            "du", "st.", "st", "mc", "o'", "ter", "ten", "bin", "al"}
SUFFIX = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v", "md", "m.d.",
          "phd", "ph.d.", "ed.d.", "esq", "esq.", "cpa", "rn", "dds"}

LABEL_KINDS = {"strong", "b", "p", "div", "td", "th", "span", "em", "li"}
LABEL_MAX = 44

# A field label or a contact value sits BETWEEN two trustees rather than after
# the list, so neither counts toward the run of unreadable blocks that ends a
# section. Gilman-Danforth District Library prints "Position:", "Phone:",
# "Email Address:" and their three values under each trustee's own heading —
# four unreadable blocks, exactly the tolerance — so the reader stopped after
# the first of six.
FIELD_LABEL = re.compile(r"^[A-Za-z][A-Za-z /&'-]{0,22}:$")
CONTACT_VALUE = re.compile(r"(@[a-z0-9.-]+\.[a-z]{2,}|"
                           r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", re.I)

MIN_MEMBERS = 3
# An Illinois library board seats seven (75 ILCS 16/30-45 for a district, 75
# ILCS 5/4-1 for a municipal library) or nine where a city charter says so.
# Anything past twelve means the reader ran past the list it was reading, so
# the library is reported rather than shipped.
MAX_MEMBERS = 12


def strip_tail(text):
    text = text.strip()
    for pattern in (TERM_TAIL, ELECTED_TAIL, DATE_TAIL, YEAR_TAIL):
        text = pattern.sub("", text).strip()
    return text.strip(" ,;:–—-·|").strip()


def is_name(text):
    text = strip_tail(text)
    if not text or len(text) > 46 or any(ch.isdigit() for ch in text):
        return False
    if any(ch in text for ch in "@/()[]<>"):
        return False
    tokens = text.split()
    if not 2 <= len(tokens) <= 5:
        return False
    if tokens[0].strip(".,\"'").lower() in NOT_FIRST:
        return False
    for token in tokens:
        bare = token.strip(".,\"'").lower()
        if bare in NOT_NAME:
            return False
        if bare in SUFFIX or bare in PARTICLE:
            continue
        if not NAME_TOKEN.match(token):
            return False
    return True


def classify(text):
    """('name', v) | ('role', v) | ('pair', name, role) | None."""
    text = text.strip().strip("·|").strip()
    if not text:
        return None
    lead = ROLE_LEAD.match(text)
    if lead:
        candidate = strip_tail(lead.group(2))
        if is_name(candidate):
            return ("pair", candidate, lead.group(1).strip())
        return ("role", lead.group(1).strip())
    only = ROLE_ONLY.match(text)
    if only:
        return ("role", only.group(1).strip())
    tail = ROLE_TAIL.match(text)
    if tail:
        candidate = strip_tail(tail.group(1))
        if is_name(candidate):
            return ("pair", candidate, tail.group(2).strip())
    if is_name(text):
        return ("name", strip_tail(text))
    return None


def _label(text):
    return text.strip().strip(":：·|").strip()


def board_markers(bl):
    """Every block that opens a board list — a heading, or a short LABEL.

    Clover Public Library District separates its trustees from its staff with a
    bold `Library Board Members:` and no heading at all, so a reader that knows
    only headings either takes the whole mixed list — shipping the Director as a
    trustee — or refuses a page that does separate them. A label gets level 9,
    so any real heading closes it.
    """
    out = []
    for i, (kind, text) in enumerate(bl):
        if kind in HEADS:
            if BOARD_HEAD.search(text) and not NOT_A_ROSTER.search(text):
                out.append((i, int(kind[1])))
            continue
        if kind in LABEL_KINDS and len(text) <= LABEL_MAX:
            label = _label(text)
            if BOARD_HEAD.match(label) and not NOT_A_ROSTER.search(label) \
                    and not ROLE_ONLY.match(label):
                out.append((i, 9))
    return out


def read_section(bl, start, level, anchor_only=frozenset()):
    """The typed tokens under one board marker, junk dropped, run bounded."""
    tokens, i, quiet = [], start + 1, 0
    while i < len(bl):
        kind, text = bl[i]
        i += 1
        if kind not in HEADS and kind in LABEL_KINDS and len(text) <= LABEL_MAX:
            label = _label(text)
            # A short label naming another body ends this one: Clover's
            # trustees are followed by `FOIA Officer`, Breese's staff by the
            # board. A role label is not a stop — it belongs to a person.
            if STOP_HEAD.search(label) and not ROLE_ONLY.match(label) \
                    and classify(text) is None:
                break
            if level >= 9 and BOARD_HEAD.match(label) and i - 1 != start:
                break
        if kind in HEADS:
            if int(kind[1]) <= level or STOP_HEAD.search(text):
                break
            inner = classify(text)
            if inner is not None and inner[0] != "role":
                quiet = 0
                tokens.append(inner)   # Auburn puts each trustee in an <h3>
                continue
            quiet = 0
            continue                   # a sub-heading (Officers, Members)
        if kind == "a" and strip_tail(text).lower() in anchor_only:
            # A LINK LABEL IS NOT A TRUSTEE. Herrin City Library's board page
            # links "Strategic Plan" and Marion Carnegie's "Send Brief", both
            # of which read as two capitalised words; measured across the 401
            # trustees this reader found, those two were the ONLY candidates
            # whose text appears nowhere on the page outside an <a>, and both
            # were labels. A name that is also linked (a mailto on the
            # trustee's own name) appears in its own block too and is kept.
            continue
        got = classify(text)
        if got is None:
            if FIELD_LABEL.match(text) or CONTACT_VALUE.search(text):
                continue
            quiet += 1
            if quiet >= 4 and tokens:
                break
            continue
        quiet = 0
        tokens.append(got)
    return tokens


def pair_members(tokens):
    """Walk the name/role stream into (name, role) members, in page order."""
    out, i, count = [], 0, len(tokens)
    while i < count:
        token = tokens[i]
        if token[0] == "pair":
            out.append((token[1], token[2]))
            i += 1
            continue
        if token[0] == "name":
            if i + 1 < count and tokens[i + 1][0] == "role":
                out.append((token[1], tokens[i + 1][1]))
                i += 2
                continue
            out.append((token[1], None))
            i += 1
            continue
        if i + 1 < count and tokens[i + 1][0] == "name":
            out.append((tokens[i + 1][1], token[1]))
            i += 2
            continue
        i += 1
    seen, unique = set(), []
    for name, role in out:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, role))
    return unique


# ----------------------------------------------------------- attribution ---

GENERIC = {"public", "library", "libraries", "district", "memorial",
           "township", "area", "county", "the", "of", "and", "free",
           "community", "regional", "village", "city", "town", "municipal",
           "branch", "center", "centre"}


def distinctive(name):
    """The tokens of a library's name that identify THIS library."""
    return [t for t in re.split(r"[^A-Za-z]+", name.lower())
            if t and t not in GENERIC and len(t) > 2]


def page_title(body):
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
    if not match:
        return ""
    return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()


# A host many libraries use is not a host they SHARE: each has its own page
# on it. MEASURED 2026-09-25 across the directory's 331 websites, seven hosts
# carry more than one library and two of them are platforms of this kind —
# facebook.com (ten libraries) and sites.google.com (two).
PLATFORM_HOSTS = {"facebook.com", "m.facebook.com", "sites.google.com",
                  "wordpress.com", "blogspot.com", "weebly.com", "wixsite.com",
                  "google.com", "libib.com", "square.site"}


def host_of(url):
    netloc = urllib.parse.urlsplit(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def shared_hosts(contacts):
    """host -> the libraries that publish it, for hosts more than one does.

    MEASURED 2026-09-25: five library-to-library pairs, only one of which was
    on record. bloomingtonlibrary.org (Bloomington + Golden Prairie) was;
    annawanil.org, marshallillibrary.com, pekinpubliclibrary.org and
    silvislibrary.org were not, and Marshall Area against Marshall Public is
    the pair a name test cannot split, because both names carry "marshall".
    """
    claims = {}
    for library, record in contacts.items():
        url = (record or {}).get("url")
        if not url:
            continue
        host = host_of(url)
        if not host or host in PLATFORM_HOSTS:
            continue
        claims.setdefault(host, set()).add(library)
    return {h: names for h, names in claims.items() if len(names) > 1}


def squash(text):
    """Lower-case letters and digits only, so a host and a name can be compared."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def claim_score(library, host, title, headings):
    """How strongly this page's own words identify THIS library.

    Compared between claimants rather than thresholded, because the question is
    never "does this page mention the library" — it is "of the libraries that
    publish this host, which one is this board's". pekinpubliclibrary.org is
    Pekin Public Library's own site and South Pekin Public Library's only
    listed website, and the host settles it: it contains Pekin's whole name and
    not South Pekin's. marshallillibrary.com contains neither name and the
    section heading carries one of them in full.
    """
    name = squash(library)
    if not name:
        return 0
    score = 0
    if name in squash(host):
        score += 3
    if name in squash(title):
        score += 2
    if any(name in squash(head) for head in headings):
        score += 2
    if score:
        return score
    # THE LOWER TIER, and Silvis Public Library is why it exists.
    # silvislibrary.org carries Silvis's eight trustees and Rock River Library
    # District's seven under two IDENTICAL "Board of Trustees" labels, so the
    # whole-name test scores both at nothing and the page reads as unsettled.
    # One distinctive word settles it: "silvis" is in the host and in the
    # section heading, and neither "rock" nor "river" is anywhere.
    words = "%s %s %s" % (host, title, " ".join(headings))
    return sum(1 for token in distinctive(library) if token in words.lower())


def names_this_library(library, haystack):
    """Do this page's own words carry a word that identifies THIS library?

    The looser test, for a host no other library publishes: there the page
    cannot be a neighbour's, and all that is being ruled out is a page about
    something else entirely — a county board, a Friends group, a school.
    """
    tokens = distinctive(library)
    if not tokens:
        return True          # a name with no distinctive word cannot be told apart
    low = haystack.lower()
    return any(token in low for token in tokens)


def read_board(body, library, url="", rivals=()):
    """(members, heading, note) — members is [] when the page names no board.

    THE CONTRACTING TRAP, and the two guards against it. Milan-Blackhawk Area
    Public Library District publishes rockislandlibrary.org as its website, and
    that site has one board page naming Rock Island's board; nothing in the
    page's structure says so, only the names on it do. So a board is attributed
    only where the page's own words — its host, its title or the section heading
    — name the library it is being attributed to. And where the host is one
    ANOTHER library also publishes, the heading alone has to settle it, with a
    word that belongs to this library and not to the other claimant, because
    Marshall Area and Marshall Public both answer to "marshall".
    """
    bl = blocks(body)
    title = page_title(body)
    # Text that appears on this page ONLY inside an <a>. See read_section.
    seen_kinds = {}
    for kind, text in bl:
        seen_kinds.setdefault(strip_tail(text).lower(), set()).add(kind)
    anchor_only = frozenset(t for t, kinds in seen_kinds.items() if kinds == {"a"})
    best, best_head = [], None
    found = []
    for i, level in board_markers(bl):
        members = pair_members(read_section(bl, i, level, anchor_only))
        if not members:
            continue
        found.append((bl[i][1], members))
        if len(members) > len(best):
            best, best_head = members, bl[i][1]
    if not best:
        return [], None, "no board list on the page"
    headings = [head for head, _members in found]
    # SEVERAL SECTIONS IS USUALLY ONE BOARD, NOT TWO. Four libraries in the
    # pool list their officers under one heading and the rest of the board
    # under another — Fairview Heights' "2025-2026 Officers & Trustees" beside
    # its "Trustees", Odell's "Board of Trustees" beside its "Trustees" — and
    # reading only the longer section ships part of a board as the whole of it.
    # So the sections are UNIONED in page order, and it is the shared-host
    # check below, not the section count, that guards against a page carrying
    # somebody else's board. Two sections naming the same people (Pankhurst's
    # page repeats its six under a second heading) collapse in the dedupe.
    if len(found) > 1 and not rivals:
        merged, seen = [], set()
        for _head, members in found:
            for name, role in members:
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                merged.append((name, role))
        if len(merged) <= MAX_MEMBERS:
            best = merged
    if len(best) < MIN_MEMBERS:
        return [], best_head, "only %d name(s) read, below the floor of %d" % (
            len(best), MIN_MEMBERS)
    if len(best) > MAX_MEMBERS:
        return [], best_head, "%d names read, past the ceiling of %d — the " \
            "reader ran past the list" % (len(best), MAX_MEMBERS)
    if rivals:
        host = host_of(url)
        mine = claim_score(library, host, title, headings)
        theirs = max(claim_score(other, host, title, headings) for other in rivals)
        if mine <= theirs:
            return [], best_head, "%s also publishes this host (%s) and the " \
                "page's own words do not say this board is %s's (%d against " \
                "%d)" % (", ".join(sorted(rivals)), host or "?", library,
                         mine, theirs)
        if len(found) == 1:
            # One list, and the page's own words already said whose it is.
            # Pekin Public Library's page heads its four trustees "Members" and
            # its HOST carries Pekin's whole name; asking the heading to say it
            # again withheld a board from a library reading its own site.
            return best, best_head, None
        # NO UNION ON A SHARED HOST. Silvis's page carries two boards under two
        # identical labels; merging them would have produced a fifteen-name
        # board, caught here only by the ceiling and not caught at all at five
        # names plus four. So each SECTION is scored on its own heading, and the
        # answer is the one section this library outscores every rival on.
        keep, seen = [], set()
        for head, members in found:
            if claim_score(library, "", "", [head]) <= max(
                    claim_score(other, "", "", [head]) for other in rivals):
                continue
            key = frozenset(name.lower() for name, _role in members)
            if key in seen:
                continue
            seen.add(key)
            keep.append((head, members))
        if len(keep) != 1:
            return [], best_head, "%s also publishes this host (%s) and %d of " \
                "its %d board list(s) name this library, so which is this " \
                "board is not settled" % (", ".join(sorted(rivals)), host,
                                          len(keep), len(found))
        head, members = keep[0]
        if not MIN_MEMBERS <= len(members) <= MAX_MEMBERS:
            return [], head, "%d name(s) under %r, outside %d..%d" % (
                len(members), head, MIN_MEMBERS, MAX_MEMBERS)
        return members, head, None
    words = "%s %s %s" % (host_of(url), title, " ".join(headings))
    if not names_this_library(library, words):
        return [], best_head, "the page does not name this library (host %r, " \
            "title %r) — it may be a neighbour's board" % (host_of(url), title[:60])
    return best, best_head, None


# ------------------------------------------------------------------ fetch ---

BOARD_LINK = re.compile(r"(?i)\b(board of (?:library )?trustees|library board"
                        r"|board of directors|board members|our board"
                        r"|library trustees|trustees|the board)\b")
ABOUT_LINK = re.compile(r"(?i)\b(about|governance|administration|library info"
                        r"|who we are|library board)\b")


def page_links(body, base):
    out = []
    for href, text in re.findall(r'(?is)<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', body):
        label = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        out.append((label, urllib.parse.urljoin(base, html.unescape(href))))
    return out


def board_page_links(body, base):
    seen, hits = set(), []
    for label, url in page_links(body, base):
        path = urllib.parse.urlsplit(url).path
        if BOARD_LINK.search(label) or BOARD_LINK.search(path):
            if url not in seen:
                seen.add(url)
                hits.append((label[:70], url))
    return hits


def about_page_links(body, base, origin):
    seen, hits = set(), []
    for label, url in page_links(body, base):
        if urllib.parse.urlsplit(url).netloc != origin:
            continue
        path = urllib.parse.urlsplit(url).path
        if ABOUT_LINK.search(label) or ABOUT_LINK.search(path):
            if url not in seen:
                seen.add(url)
                hits.append((label[:70], url))
    return hits


RETRY_STATUS = (429, 500, 502, 503, 504)
RETRY_AFTER_CAP = 30.0


def get(gate, pacer, url, attempts=3):
    """One page, paced, with a 429 or 5xx retried rather than believed.

    A RATE LIMIT IS NOT A VERDICT, which is the lesson
    scripts/validate_card_links.py already records — "429 is now treated as
    rate-limiting (back off, retry, and say the probe may have caused it)
    rather than as a block". It matters more here than there: several of these
    170-odd libraries sit on shared hosting, and a first draft that took a 429
    at face value lost four libraries whose sites had answered fine forty
    minutes earlier, to rate limits this scraper's own earlier pass had almost
    certainly caused.

    THE STACK STAYS STDLIB. scraper_common.fetch already retries a 429
    correctly and does it on `requests`, which user-agent-measurements.json
    records seven hosts refusing while serving the same token to the stdlib
    client. Swapping stacks to gain the backoff would change which hosts answer
    at all, so the backoff is added around the stack that was measured.
    """
    last = None
    for attempt in range(attempts):
        try:
            with pacer.hold(url):
                body = fetch_stdlib(url, headers={"User-Agent": USER_AGENT},
                                    timeout=45)
            return body.decode("utf-8", "replace") if isinstance(body, bytes) else body
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_STATUS or attempt == attempts - 1:
                raise
            after = (exc.headers.get("Retry-After") or "").strip() \
                if exc.headers else ""
            delay = min(float(after), RETRY_AFTER_CAP) if after.isdigit() \
                else 3.0 * (attempt + 1)
            last = exc
            time.sleep(delay)
    raise last


# ------------------------------------------------------------------- pool ---

def library_pool(app_dir=APP_DIR):
    """(name, governance type, website) for every card that names no board.

    DERIVED, never written down. A library that starts filing an Annual
    Financial Report leaves this pool on the next run with nothing edited, and
    one whose website disappears from the directory leaves it the same way.

    THE DENOMINATOR IS THE 72 COUNTIES `statewideLibraryEntry` DISPATCHES, not
    every county that draws a library. Sixteen others — Cook, Will, DuPage,
    Lake, Kane, McHenry, Kendall, Kankakee, Madison, DeKalb, Rock Island,
    Peoria, Macon, Stark, Woodford, Grundy — have their own dispatch entries
    reading their own roster files, and `withLibraryOfficials` is what stamps
    this one, so a library only those counties draw could be read here and
    would render nowhere. A first draft globbed every `*-library-districts.json`
    and would have shipped such a record for the builder's orphan check to
    fail on. This reads the dispatch table through the same function
    build_il_library_trustees.py checks against, so the two cannot disagree
    about which cards this route reaches.
    """
    from il_library_district_officials_scraper import (
        shipped_cards, statewide_library_counties)

    cards, _where = shipped_cards(statewide_library_counties())
    with open(os.path.join(app_dir, "il-library-district-officials.json"),
              encoding="utf-8") as handle:
        filings = json.load(handle)["libraries"]
    with open(os.path.join(app_dir, "il-library-contacts.json"),
              encoding="utf-8") as handle:
        contacts = json.load(handle)["libraries"]
    filed = {name for name, rec in filings.items() if rec.get("board")}
    pool = []
    for name in sorted(cards):
        if name in filed:
            continue
        url = (contacts.get(name) or {}).get("url")
        if url:
            pool.append((name, cards[name], url))
    if len(cards) < 200:
        fail("only %d library cards found on the statewide dispatch table — the "
             "layer draws hundreds, so the pool would be silently short"
             % len(cards))
    return pool


def scrape(limit=None, app_dir=APP_DIR, verbose=True):
    gate = RobotsGate(None, USER_AGENT)
    pacer = HostPacer(gate)
    pool = library_pool(app_dir)
    with open(os.path.join(app_dir, "il-library-contacts.json"),
              encoding="utf-8") as handle:
        rivals = shared_hosts(json.load(handle)["libraries"])
    if verbose and rivals:
        print("hosts more than one library publishes: %d" % len(rivals))
        for host in sorted(rivals):
            print("   %-32s %s" % (host, ", ".join(sorted(rivals[host]))))
    if limit:
        pool = pool[:limit]
    out = {}
    for index, (library, governance, url) in enumerate(pool, 1):
        record = {"type": governance, "website": url}
        out[library] = record

        def say(verdict, extra=""):
            if verbose:
                print("%3d/%d %-44s %-22s %s" % (index, len(pool), library[:44],
                                                 verdict, extra[:60]), flush=True)

        try:
            allowed, why = gate.allows(url)
        except Exception as exc:                                # noqa: BLE001
            record["verdict"] = "robots-unreadable"
            record["detail"] = repr(exc)[:200]
            say("ROBOTS UNREADABLE", repr(exc))
            continue
        record["robots"] = why
        if not allowed:
            # A refusal stops the FETCH and is recorded as a refusal, never as
            # an absent source (CLAUDE.md, Adam's ruling of 2026-09-19).
            record["verdict"] = "robots-refused"
            say("ROBOTS REFUSED", why)
            continue
        signal = gate.content_signal(url)
        if signal:
            record["contentSignal"] = signal
        origin = urllib.parse.urlsplit(url).netloc
        try:
            home = get(gate, pacer, url)
        except Exception as exc:                                # noqa: BLE001
            record["verdict"] = "site-unreachable"
            record["detail"] = repr(exc)[:200]
            say("SITE UNREACHABLE", repr(exc))
            continue
        hits = board_page_links(home, url)
        via = "home page"
        if not hits:
            # A home page with no board link is not a library that publishes no
            # board — one measured sample had four of sixteen in that state.
            for label, about in about_page_links(home, url, origin)[:2]:
                try:
                    if not gate.allows(about)[0]:
                        continue
                    deeper = board_page_links(get(gate, pacer, about), about)
                except Exception:                               # noqa: BLE001
                    continue
                if deeper:
                    hits, via = deeper, "About page %r" % label
                    break
        if not hits:
            record["verdict"] = "no board page found"
            say("no board page")
            continue
        label, board_url = hits[0]
        try:
            if not gate.allows(board_url)[0]:
                record["verdict"] = "robots-refused"
                record["detail"] = "the board page itself: %s" % board_url
                say("ROBOTS REFUSED", board_url)
                continue
            page = get(gate, pacer, board_url)
        except Exception as exc:                                # noqa: BLE001
            record["verdict"] = "board-page-unreachable"
            record["detail"] = repr(exc)[:200]
            record["boardUrl"] = board_url
            say("BOARD PAGE UNREACHABLE", repr(exc))
            continue
        record["boardUrl"] = board_url
        record["boardLink"] = label
        record["via"] = via
        members, heading, note = read_board(
            page, library, board_url,
            sorted(rivals.get(host_of(board_url), set()) - {library}))
        if not members:
            record["verdict"] = "board page names nobody"
            record["detail"] = note
            say("nobody", note or "")
            continue
        record["verdict"] = "read"
        record["heading"] = heading
        record["board"] = [{"name": n, "role": r} if r else {"name": n}
                           for n, r in members]
        say("READ %d" % len(members), "%s — %s" % (heading or "", board_url))
    return out


# --------------------------------------------------------------- selftest ---

# One fixture per shape MEASURED on a real board page, named for the library it
# came from, plus the two the reader must refuse. The pages themselves are not
# committed; these reproduce the structure that decided each rule.
CASES = [
    # Breese Public Library: name then role, under a heading, with the STAFF
    # list immediately above it in the identical shape.
    ("breese", "Breese Public Library",
     "https://breeselibrary.org/about/",
     """<title>About | Breese Public Library</title>
        <h2>Library Staff</h2>
        <p><strong>Jenna Astroth</strong></p><p>Library Director</p>
        <p><strong>Diane Holtgrave</strong></p><p>Assistant Librarian</p>
        <h2>Library Board Members</h2>
        <p><strong>Angie Becker</strong></p><p>President</p>
        <p><strong>Allison Netemeyer</strong></p><p>Vice President</p>
        <p><strong>Judy Kampwerth</strong></p><p>Treasurer</p>
        <p><strong>Gwen Fischer</strong></p><p>Secretary</p>
        <h2>Meeting Agendas</h2><p><a href="/a">01-21-2025</a></p>""",
     ["Angie Becker", "Allison Netemeyer", "Judy Kampwerth", "Gwen Fischer"]),
    # Albion Public Library: role then name, then bare names after a rule.
    ("albion", "Albion Public Library",
     "https://www.albion.lib.il.us/board-of-trustees",
     """<title>Meet the Board — Albion Public Library</title>
        <h2>Albion Public Library Board of Trustees</h2><h3>Email Trustees</h3>
        <strong>President</strong><div>Melissa Felling</div>
        <strong>Treasurer</strong><div>Trevor Ward</div>
        <div>_______</div><div>Dianne Berger</div><div>Shelby Harris</div>""",
     ["Melissa Felling", "Trevor Ward", "Dianne Berger", "Shelby Harris"]),
    # Carbondale Public Library: "Role: Name, term expires <date>" per list item.
    ("carbondale", "Carbondale Public Library",
     "https://carbondalepubliclibrary.org/aboutus/board-of-trustees/",
     """<title>Board of Trustees – Carbondale Public Library</title>
        <h1>Board of Trustees</h1><h2>Trustee Members</h2><ul>
        <li>President: Chastity Mays, term expires 6/30/2028</li>
        <li>Vice President: Frances A. Anterola, term expires 6/30/2026</li>
        <li>Member: Roland C. Person, term expires 6/30/2026</li></ul>""",
     ["Chastity Mays", "Frances A. Anterola", "Roland C. Person"]),
    # Auburn Public Library District: each trustee is an <h3>.
    ("auburn", "Auburn Public Library District",
     "https://auburnpubliclibraryil.org/library-board",
     """<title>Library Board - Auburn Public Library</title>
        <h2>Library Board</h2><h3>Auburn Public Library District Board of Trustees</h3>
        <h3>Lacy Strader</h3><strong>Position:</strong><p>President</p>
        <strong>Mailing Address:</strong><p>338 W Jefferson St, Auburn IL 62615</p>
        <h3>Monica Garrett</h3><strong>Position:</strong><p>Vice President</p>
        <h3>Dan Dixon</h3><strong>Position:</strong><p>Treasurer</p>""",
     ["Lacy Strader", "Monica Garrett", "Dan Dixon"]),
    # Clover Public Library District: board and staff on one page, separated by
    # a bold LABEL and no heading at all.
    ("clover", "Clover Public Library District",
     "https://cloverlibrarywoodhull.com/library-board/",
     """<title>Library Board &amp; Staff</title>
        <h3>Board and Staff Members</h3>
        <strong>Library Staff</strong><p>:</p>
        <p>Linda Kiely, Library Clerk</p><p>Chris Youngren, Custodian</p>
        <strong>Library Board Members</strong><p>:</p>
        <p>Darcie Berry, President</p><p>Alissa Gelaude, Vice President</p>
        <p>Karen Pfeiffer, Trustee</p>
        <strong>FOIA Officer</strong><a href="/d">Library Director, Primary</a>""",
     ["Darcie Berry", "Alissa Gelaude", "Karen Pfeiffer"]),
    # Centralia Regional Library District: an election clause after the name.
    ("centralia", "Centralia Regional Library District",
     "https://www.centralialibrary.org/about-us/board-of-trustees/",
     """<title>Board of Trustees</title><h1>Board of Trustees</h1>
        <strong>Members</strong><p>:</p>
        <p>President: Julie Boltz, elected April 2025, term expires April 30, 2031,</p>
        <p>Vice-President: Karen Bounds, elected April 2023, term expires April 30, 2029,</p>
        <p>Todd Glispie, elected, April 2021, term expires April 30, 2027,</p>""",
     ["Julie Boltz", "Karen Bounds", "Todd Glispie"]),
    # Fairview Heights Public Library: the officers under one heading and the
    # rest of the board under another. ONE board, two sections.
    ("split sections", "Fairview Heights Public Library",
     "https://fairviewheightslibrary.org/board-of-trustees/",
     """<title>Board of Trustees</title>
        <h4>2025-2026 Officers &amp; Trustees</h4>
        <p>Deborah Smith, President</p><p>Donna Bullock, Vice President</p>
        <p>Linda Spencer, Secretary</p><p>Karie Sheils, Treasurer</p>
        <h4>Trustees</h4>
        <p>Carolyn Clark</p><p>Rochelle Hobson</p><p>Patti Hopkins</p>
        <p>Laurinda Hardy</p><p>Bill Poletti</p>""",
     ["Deborah Smith", "Donna Bullock", "Linda Spencer", "Karie Sheils",
      "Carolyn Clark", "Rochelle Hobson", "Patti Hopkins", "Laurinda Hardy",
      "Bill Poletti"]),
    # Du Quoin Public Library: a marketing banner in the same <div> shape sits
    # directly under the last trustee. "No Overdue" passes every other test,
    # and the fleet's own names gate accepts it.
    ("banner under the list", "Du Quoin Public Library",
     "https://duquoin.lib.il.us/board-of-trustees",
     """<title>Board of Trustees - Du Quoin Public Library</title>
        <h2>Board of Trustees</h2>
        <div>Leanna Gray</div><div>President</div>
        <div>Carol Downs</div><div>Board Member</div>
        <div>Andrea Helmer</div><div>Board Member</div>
        <div>No Overdue</div><div>Fines</div><div>Daily</div><div>Deliveries</div>""",
     ["Leanna Gray", "Carol Downs", "Andrea Helmer"]),
    # Herrin City Library: a LINKED "Strategic Plan" beside the trustees. Of the
    # 398 trustees measured, exactly two candidates appeared nowhere on their
    # page outside an <a>, and both were labels of this kind.
    ("linked label", "Herrin City Library",
     "https://herrincitylibrary.org/library-board/",
     """<title>Library Board | Herrin City Library</title>
        <h2>Library Board of Trustees</h2>
        <p><a href="/plan.pdf">Strategic Plan</a></p>
        <p>Barbara Guebert</p><p>Kathleen Jones</p><p>Jennifer Sarver</p>""",
     ["Barbara Guebert", "Kathleen Jones", "Jennifer Sarver"]),
]

# The refusals and the two shared hosts that must NOT be refused. These matter
# more than the reads: a wrong name under the right library is the failure this
# project's honesty rules exist to prevent, and a board withheld from a library
# reading its own site is the cost of over-correcting for it.
SHARED_HOST_READS = [
    # marshallillibrary.com carries both Marshalls and names this one in the
    # section heading; the host names neither.
    ("shared host, heading names it", "Marshall Public Library",
     "http://www.marshallillibrary.com/mpl-board-of-trustees",
     ("Marshall Area Public Library District",),
     """<title>MPL Board of Trustees</title>
        <h3>Marshall Public Library Board of Trustees</h3>
        <p>John Tarble, President</p><p>Herman Wallace, Vice President</p>
        <p>Janet Hasten, Secretary</p><p>Jennifer Smitley, Treasurer</p>""",
     ["John Tarble", "Herman Wallace", "Janet Hasten", "Jennifer Smitley"]),
    # pekinpubliclibrary.org is Pekin's own site and South Pekin's only listed
    # website. The heading says nothing; the HOST carries Pekin's whole name
    # and not South Pekin's.
    ("shared host, host names it", "Pekin Public Library",
     "https://pekinpubliclibrary.org/library-board/",
     ("South Pekin Public Library",),
     """<title>Library Board</title><h2>Members</h2>
        <p>Carrie Allen, President</p><p>Randy Turner, Vice President</p>
        <p>Leslie Leitner, Secretary</p><p>Gary Gillis, Treasurer</p>""",
     ["Carrie Allen", "Randy Turner", "Leslie Leitner", "Gary Gillis"]),
]

REFUSALS = [
    # Milan-Blackhawk contracts with Rock Island and publishes ITS site. The
    # page has one board and it is the wrong one.
    ("contracted host", "Milan-Blackhawk Area Public Library District",
     "http://rockislandlibrary.org/board-of-trustees", (),
     """<title>Board of Trustees | Rock Island Public Library</title>
        <h1>Board of Trustees</h1>
        <p>Jane Doe, President</p><p>John Roe, Vice President</p>
        <p>Mary Poe, Secretary</p><p>Peter Coe, Treasurer</p>""",
     "does not name this library"),
    # Bloomington's page carries BOTH its own board and Golden Prairie's.
    ("two boards on one page", "Golden Prairie Public Library District",
     "http://www.bloomingtonlibrary.org/gppld-board", ("Bloomington Public Library",),
     """<title>Board of Trustees | Bloomington Public Library</title>
        <h2>BPL Board of Trustees</h2>
        <p>Ann Alpha, President</p><p>Bob Beta, Vice President</p>
        <p>Cal Gamma, Secretary</p><p>Dee Delta, Treasurer</p>
        <h2>GPPLD Board of Trustees</h2>
        <p>Eve Epsilon, President</p><p>Fay Zeta, Secretary</p>""",
     "also publishes this host"),
]


def selftest():
    checks = problems = 0
    for slug, library, url, page, expect in CASES:
        members, heading, note = read_board(page, library, url)
        got = [name for name, _role in members]
        checks += 1
        if got != expect:
            problems += 1
            print("  FAIL %-12s expected %s\n              got      %s (%s)"
                  % (slug, expect, got, note or heading))
        # Every fixture that names a role must carry it through.
        for name, role in members:
            checks += 1
            if role is not None and not ROLE_ONLY.match(role + ":"):
                problems += 1
                print("  FAIL %-12s %r is not a role" % (slug, role))
    for slug, library, url, rivals, page, expect in SHARED_HOST_READS:
        members, heading, note = read_board(page, library, url, rivals)
        checks += 1
        got = [name for name, _role in members]
        if got != expect:
            problems += 1
            print("  FAIL %-12s a shared host is not a wrong attribution: "
                  "expected %s\n              got      %s (%s)"
                  % (slug, expect, got, note or heading))
    for slug, library, url, rivals, page, want in REFUSALS:
        members, _heading, note = read_board(page, library, url, rivals)
        checks += 1
        if members:
            problems += 1
            print("  FAIL %-12s should have been refused, read %s"
                  % (slug, [n for n, _r in members]))
        elif want not in (note or ""):
            problems += 1
            print("  FAIL %-12s refused for the wrong reason: %s" % (slug, note))
    # The staff list above Breese's board must never reach it.
    members, _h, _n = read_board(CASES[0][2], CASES[0][1])
    checks += 1
    if any(name == "Jenna Astroth" for name, _r in members):
        problems += 1
        print("  FAIL breese shipped the Library Director as a trustee")
    # The floor and the ceiling.
    two = """<title>X Public Library</title><h1>Board of Trustees</h1>
             <p>Ann Alpha, President</p><p>Bob Beta, Secretary</p>"""
    checks += 1
    if read_board(two, "X Public Library")[0]:
        problems += 1
        print("  FAIL a two-name board passed the floor of %d" % MIN_MEMBERS)
    many = "<title>X Public Library</title><h1>Board of Trustees</h1>" + "".join(
        "<p>Person%s Number%s, Trustee</p>" % (chr(65 + i), chr(65 + i))
        for i in range(MAX_MEMBERS + 2))
    checks += 1
    if read_board(many, "X Public Library")[0]:
        problems += 1
        print("  FAIL a %d-name board passed the ceiling of %d"
              % (MAX_MEMBERS + 2, MAX_MEMBERS))
    # is_name, in both directions, on values measured in the fleet's own rosters.
    for value in ("Trevor Ward", "Mark St. Eve", "Roland C. Person",
                  "April Hoste", "Jackie Winter", "Thomas P. Stagg"):
        checks += 1
        if not is_name(value):
            problems += 1
            print("  FAIL %r is a real name this reader rejects" % value)
    for value in ("FOIA Officer", "Library Board", "Learn More", "About Us",
                  "Meeting Room", "Library Director", "Adult Services",
                  "Board Minutes", "Summer Reading", "121 E. Washington St."):
        checks += 1
        if is_name(value):
            problems += 1
            print("  FAIL %r reads as a person's name" % value)
    print("il-library-trustees selftest: %s — %d check(s)%s"
          % ("FAIL" if problems else "OK", checks,
             ", %d problem(s)" % problems if problems else ""))
    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="write the scrape to this file")
    parser.add_argument("--limit", type=int, help="read only the first N libraries")
    parser.add_argument("--selftest", action="store_true",
                        help="offline: run the parser against its fixtures")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    libraries = scrape(limit=args.limit)
    payload = {
        "generated": datetime.datetime.now(datetime.timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "libraries": libraries,
    }
    text = json.dumps(payload, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        read = sum(1 for r in libraries.values() if r.get("verdict") == "read")
        print("\nwrote %s — %d of %d library(ies) read a board"
              % (args.out, read, len(libraries)))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
