#!/usr/bin/env python3
"""Scrape stage 1: which supervisor chairs each Iowa county board.

WHY THIS EXISTS AT ALL, WHEN THE GAP RECORD SAID IT COULD NOT BE DONE
---------------------------------------------------------------------
`ia-board-chair` was closed on 2026-09-05 with a measurement and a
conclusion, and the measurement was right while the conclusion was wrong. The
measurement: of 22 sampled counties the word `chair` appeared on 10, a chair
with an adjacent plausible NAME on 5, and FOUR OF THOSE FIVE were furniture --
`Contact Information`, `Term Expires`, `its activities`, `Supervisor Office`.
The conclusion: "there is no gate that separates those five hits."

There is. This app already ships 350 supervisor names across 92 counties in
`ia-county-officers.json`, and all four of those strings fail membership in
their own county's list. A ROSTER IS A GATE, and it was sitting in the repo.

WHY ROSTER MEMBERSHIP IS NOT ENOUGH EITHER, WHICH COST A SECOND ATTEMPT
-----------------------------------------------------------------------
A roster-gated sweep with a +/-60-character text window returned Keokuk's
DARYL WOOD, who is the vice-chairman. Two defects, and both are load-bearing:

  1. The window was SYMMETRIC, so it reached backwards past the chairman's own
     name into the previous person's role. This is the Franklin trap from the
     Illinois work -- a grid whose roles sit beside a different row's name --
     and a flattened read walks into it every time.
  2. Matching was EXACT SUBSTRING, so the roster's `Mr. Mike Hadley` could
     never meet the page's `Michael C. Hadley`.

So this file pairs a role with a name STRUCTURALLY, in three tests that each
catch a case the others do not:

  CONTAINMENT  Walk the parsed DOM up from the name to the smallest element
               that also holds a role word, and refuse it if that element
               holds any OTHER supervisor. A table row, a member card, a list
               item -- whatever the county's markup calls a record.
  DIRECTION    Containment says no other SUPERVISOR shares the box. It says
               nothing about anyone else, and Shelby County publishes an EMS
               board reading `Tim Plumb, Chairman Bryce Schaben,
               Vice-Chairman`, where a chair word sits ONE character from a
               supervisor's name and belongs to the man before it. So a role
               word standing BEFORE a name is refused when a person-shaped
               phrase stands before IT.
  PROXIMITY    The role must be within GAP_CAP characters of the name. Inside
               a one-supervisor container there is no other person's role to
               steal, which is what makes a distance test safe here and unsafe
               in the flattened form that failed. It is what stops Scott
               County's 3,385-character navigation menu, and Winnebago's
               `Dr. Twyla Osterkamp, Chairperson` -- the chair of a different
               body entirely -- from donating a role to whoever shares a page.

A FOURTH test is not structural at all and no structural test can replace it:
the page has to be the BOARD's page. See OTHERBODYRX below -- it is what the
independent-witness check caught, on the one county of 38 that came out wrong.

MEASURED 2026-09-05 over all 98 counties in `ia-county-board-directory.json`, and
re-measured after two further refusals were added (a chair QUALIFIED by another
body, and a pairing whose own term dates have expired), which cost exactly one
county -- Mahaska, whose page says "Term: 2017 - 2020":
38 yield exactly one chair before that exclusion, 36 after it, and 35 once the
two refusals above are applied, 39 none, 17 unreachable, 7 have no roster to gate
with -- 98, and the arithmetic is the check: Mahaska moved from the one column
to the none column, so a split that still reads 38 there sums to 97 and is a
count taken before the refusal it describes. ZERO counties yield two candidates.

RE-MEASURED 2026-09-06, WHEN THIS SCRAPE FINALLY GOT A ROBOTS GATE and the
split moved: 34 one, 35 none, 20 unreachable, 2 robots-refused, 7 no-roster --
still 98, and the same arithmetic is still the check. Only ONE county left the
one column: Cherokee, whose page this app had been reading and whose
robots.txt refuses `districtry` on every path. The other counted change is a
relabelling, not a loss -- three hosts whose robots.txt was unreachable moved
from none to unreachable, because RFC 9309 makes us abstain rather than guess. The widest accepted pairing is 28
characters (Muscatine's `Danny Chick Supervisor - 1st District (Chair)`, two
under the cap); the tightest REJECTED one is 84, exactly three times that, so
GAP_CAP at 30 sits in the middle of a wide gap and is not a knob to turn when
a county stops resolving. An earlier draft of this paragraph said 25 and named
Clarke, which was the widest pairing in the sweep BEFORE the directional rule
existed; Muscatine only became acceptable when direction was added, and the
sentence was never re-derived from the sweep that shipped.

Usage:
    python3 ia/scripts/ia_county_chair_scraper.py [--county NAME ...]
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "app")
CACHE_DIR = os.path.join(HERE, ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_county_chairs.json")
DIRECTORY = os.path.join(DATA, "ia-county-board-directory.json")
OFFICERS = os.path.join(DATA, "ia-county-officers.json")

sys.path.insert(0, HERE)          # robots_gate is a sibling, not a package
from robots_gate import RobotsGate  # noqa: E402

HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)",
           "Accept": "text/html,application/xhtml+xml"}
# One gate for the whole run, shared across the worker pool (it locks its own
# fetches). Set in main(); None only when a caller imports this module.
GATE = None
TIMEOUT = 25
WORKERS = 6
MAX_PAGES = 8
GAP_CAP = 30          # widest true pairing measured 28; tightest false one 84

# Paths tried when a county's own home page links nothing usable.
PATHS = ["board-of-supervisors/", "supervisors/",
         "government/board-of-supervisors/", "board_of_supervisors/",
         "departments/board-of-supervisors/"]
LINKRX = re.compile(r"board[\s_-]*of[\s_-]*supervisors|supervisors", re.I)
# A link whose LABEL says "supervisors" is very often a news item ABOUT them:
# Story County spent its whole page budget on CivicAlerts and Calendar entries
# and never reached its own board page.
NEWSRX = re.compile(r"civicalerts|calendar|/news|/event|agenda|minutes|archive"
                    r"|\?AID=|\?EID=|\.pdf|\.jpg|\.png|/rss|facebook|twitter", re.I)
# A BOARDS-AND-COMMISSIONS PAGE IS NOT THE BOARD'S PAGE, and this exclusion is
# the one every structural test above passed straight through. Des Moines
# County publishes `.../board_of_supervisors/boards_commissions/`, on which
# `Tom Broeker, Chair` is his chairmanship of ANOTHER body -- the county's own
# minutes of 25 August 2026 open "with Chair Shane McCampbell, Vice-Chair Tom
# Broeker". Containment, direction and proximity all read that pairing as
# clean, because as a pairing it IS clean; what is wrong is the page. Two of
# 38 counties rested on such a page alone (Des Moines, whose answer was wrong,
# and Worth, whose answer its own minutes confirm) and both are dropped:
# losing a right answer is the safe direction, keeping a wrong one is not.
OTHERBODYRX = re.compile(r"boards?[_\-/]?(and[_\-]?)?commission|committee|appointment", re.I)

VOID = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col",
        "embed", "source", "track", "wbr", "param"}
DROP = {"script", "style", "noscript", "svg", "head"}

# VICE IS MATCHED AND MASKED FIRST, ALWAYS: "Vice Chairman" contains "Chairman".
VICE = re.compile(r"vice[\s\-‐-―]*chair(?:person|man|woman)?"
                  r"|chair(?:person|man|woman)?[\s\-‐-―]*pro[\s\-‐-―]*tem(?:pore)?",
                  re.I)
CHAIR = re.compile(r"\bchair(?:person|man|woman)?\b", re.I)

SUFFIX = re.compile(r"^(jr|sr|ii|iii|iv|v|phd|md|dds|esq)\.?$", re.I)
HONOR = re.compile(r"^(mr|mrs|ms|miss|dr|hon|rev|sen|rep)\.?$", re.I)

# Words that LOOK like a name and are not one. This list FAILS SAFE IN BOTH
# DIRECTIONS, which is the only reason a hand-kept list is allowed to decide
# anything here: a word missing from it makes furniture read as a person and
# REJECTS a county, while a real surname can never appear in it, so it can
# never make a person read as furniture. A lost county is a gap; a wrong
# pairing is a false statement on a card.
FURNITURE = set("""board county supervisor supervisors district districts term
terms expires expire email e-mail phone fax cell office offices hours mail box
po representative representatives appointment appointments contact information
member members committee committees the of and at large ward precinct meeting
meetings minutes agenda agendas courthouse street avenue road drive suite city
town iowa present absent chair chairs chairman chairperson chairwoman vice
secretary treasurer auditor recorder sheriff attorney assessor engineer
january february march april may june july august september october november
december monday tuesday wednesday thursday friday saturday sunday elected read
more view details click here home page menu skip main content navigation
search toggle dropdown login site map departments government services
residents business how do i""".split())
NAMEISH = re.compile(r"\b([A-Z][a-z]{1,})(?:\s+[A-Z]\.?)?\s+([A-Z][A-Za-z'’\-]{1,})\b")

# A CHAIR OF SOMETHING ELSE, ON THE BOARD'S OWN PAGE. OTHERBODYRX below
# excludes a boards-and-commissions PAGE, and that is a URL test, so it cannot
# see a committee named INSIDE the board's own page. Both of these are
# accepted without this refusal, at a gap of 2, with every structural test
# passing: "Budget Committee Chair: Kevin Weber", and a "Regional Planning
# Commission" heading sitting above "Kevin Weber, Chair".
#
# THE WINDOW IS THE WHOLE DESIGN, AND THE FIRST VERSION OF THIS GOT IT WRONG.
# Testing the whole CONTAINER for a committee word dropped EIGHT of 36
# counties, five of them because the container lists the supervisor's own
# REPRESENTATIVE APPOINTMENTS a line below their name -- Benton's and
# Clayton's chairs sit on the Conservation Board, Jackson's on an ATV
# Committee, and every one of those is the right chair with their committee
# assignments printed after it. A committee word in the box is not evidence
# that the chair word belongs to the committee; a committee word QUALIFYING
# the chair word is. So the test runs over the text from a little before the
# NAME through the end of the role, which is where a qualifier can live, and
# never over what follows.
OTHERBODY_LEAD = 45           # chars before the name a body's heading can sit in
                              # ON A FLAT PARENT THIS WINDOW READS THE PREVIOUS
                              # PERSON. The 45 chars are cut from the PARENT
                              # element when that parent is <= OTHERBODY_SCOPE_CAP,
                              # so where a county lists supervisors as siblings
                              # with no per-member container, the text before a
                              # name can be the END of the member above it -- a
                              # trailing "Budget Committee" line there refuses a
                              # real chair. It errs toward REFUSING, which is the
                              # safe direction and why it is recorded here rather
                              # than tuned: a narrower window would start
                              # accepting chairs of other bodies, which is the
                              # error this whole test exists to prevent.
OTHERBODY_SCOPE_CAP = 600     # a record or a section, never a page
OTHERBODY_TEXT = re.compile(
    r"\bcommittee\b|\bcommission\b|\bauthority\b|\bconservation\b|\bE\.?M\.?S\.?\b"
    r"|\bboard\s+of\s+(?!supervisors\b)\w+", re.I)

# A TERM THAT ENDED BEFORE THIS YEAR MEANS THE BLOCK IS STALE, whatever the
# roster says. Mahaska publishes "Chair: Mark Groenendyk Term: 2017 - 2020":
# Groenendyk is still a sitting supervisor, so the roster gate is satisfied
# and the pairing is clean -- and the page's own dates say it was last
# maintained two board terms ago, which is precisely the state in which a
# chair line goes on naming somebody who has since handed the gavel on.
# Refusing loses a possibly-right answer, which is the safe direction and the
# same call Worth County's exclusion made.
TERM_RANGE = re.compile(r"\b(20\d{2})\s*(?:-|\u2013|\u2014|to|through)\s*(20\d{2})\b", re.I)
# TWO KNOWN BLIND SPOTS, RECORDED RATHER THAN WIDENED UNMEASURED. This catches
# "Term expires 12/31/2024" and "Term ends 2024" and does NOT catch the
# month-name form, "Term ends December 31, 2024". A county writing it that way
# is read as carrying no term at all, which means it is ACCEPTED rather than
# refused -- the unsafe direction -- so this is the one of the two worth
# closing. It is left alone here because widening it can only ADD refusals and
# adding refusals without re-running the 98-county sweep is how a county goes
# dark for a reason nobody measured; close it in the same change that re-sweeps.
TERM_END = re.compile(r"term\s*(?:expires?|ends?)\s*:?\s*(?:\d{1,2}[-/])?(?:\d{1,2}[-/])?(20\d{2})", re.I)


def stale_term(segment):
    """-> the latest term year in `segment` when every one of them is past.

    Scoped to the pairing for the same reason OTHERBODY_TEXT is: Mahaska
    prints three supervisors' terms in one paragraph, and only the one
    attached to the accepted name says anything about the accepted line.
    """
    yrs = [int(m.group(2)) for m in TERM_RANGE.finditer(segment)]
    yrs += [int(m.group(1)) for m in TERM_END.finditer(segment)]
    if not yrs:
        return None
    this_year = datetime.date.today().year
    return max(yrs) if max(yrs) < this_year else None

# Only forms this sweep actually produced get an entry, and every join that
# uses one is PRINTED on every run (the Vermilion rule).
DIMINUTIVES = {
    "mike": "michael", "mick": "michael", "bob": "robert", "rob": "robert",
    "bill": "william", "will": "william", "dave": "david", "jim": "james",
    "dick": "richard", "rick": "richard", "steve": "steven",
    "chuck": "charles", "tony": "anthony", "ed": "edward", "ken": "kenneth",
    "larry": "lawrence", "terry": "terrence", "dan": "daniel",
    "danny": "daniel", "jack": "john", "tom": "thomas", "greg": "gregory",
    "jeff": "jeffrey", "joe": "joseph", "pat": "patrick", "sam": "samuel",
    "ron": "ronald", "don": "donald", "doug": "douglas", "phil": "philip",
    "randy": "randall", "matt": "matthew", "nick": "nicholas",
    "andy": "andrew", "tim": "timothy", "barb": "barbara", "deb": "deborah",
    "sue": "susan", "liz": "elizabeth", "beth": "elizabeth",
    "kathy": "katherine", "cathy": "catherine", "peggy": "margaret",
    "jen": "jennifer", "chris": "christopher", "sandy": "sandra",
}


class Node(object):
    __slots__ = ("tag", "kids", "parent")

    def __init__(self, tag, parent=None):
        self.tag, self.kids, self.parent = tag, [], parent

    def text(self):
        out, stack = [], [self]
        while stack:
            n = stack.pop()
            if isinstance(n, str):
                out.append(n)
            else:
                stack.extend(reversed(n.kids))
        return re.sub(r"\s+", " ", " ".join(out)).strip()

    def walk(self):
        yield self
        for k in self.kids:
            if isinstance(k, Node):
                for d in k.walk():
                    yield d


class Tree(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP:
            self.skip += 1
            return
        if self.skip or tag in VOID:
            return
        n = Node(tag, self.cur)
        self.cur.kids.append(n)
        self.cur = n

    def handle_endtag(self, tag):
        if tag in DROP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag in VOID:
            return
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.cur.kids.append(data)


def parse_html(page):
    t = Tree()
    try:
        t.feed(page)
    except Exception:
        pass          # a malformed page yields the tree built so far, not a crash
    return t.root


def mask_vice(s):
    return VICE.sub(lambda m: " " * len(m.group(0)), s)


def split_name(raw):
    """-> (first, surname), honorifics and suffixes removed."""
    toks = [t for t in re.split(r"[\s,]+", (raw or "").strip()) if t]
    toks = [t for t in toks if not HONOR.match(t)]
    while toks and SUFFIX.match(toks[-1]):
        toks.pop()
    if len(toks) < 2:
        return (None, toks[0].strip(".") if toks else None)
    return (toks[0].strip("."), toks[-1].strip("."))


def first_match(a, b):
    """-> (ok, how): exact | initial | prefix | diminutive."""
    if not a or not b:
        return (False, None)
    a, b = a.lower().strip("."), b.lower().strip(".")
    if a == b:
        return (True, "exact")
    if len(a) == 1 or len(b) == 1:
        return (a[0] == b[0], "initial" if a[0] == b[0] else None)
    if DIMINUTIVES.get(a, a) == DIMINUTIVES.get(b, b):
        return (True, "diminutive")
    lo, hi = sorted((a, b), key=len)
    if len(lo) >= 3 and hi.startswith(lo):
        return (True, "prefix")
    return (False, None)


def name_occurrences(text, surname):
    """Every `First [M.] Surname` in text -> [(first, span)].

    THE MIDDLE GROUP ACCEPTS INITIALS ONLY, and that is a correctness fix
    rather than a tightening. Allowing a capitalised WORD there let a surname
    reach backwards across a role: in `John D. Maxwell Chair Jean Dickson`,
    the pattern for Dickson matched from "Maxwell" with "Chair Jean" as middle
    tokens, the first-name test then rejected it, and a container holding TWO
    supervisors reported ONE -- the direction that ships a wrong pairing. A
    spelled-out middle name is consequently missed, which loses a county
    rather than mis-naming one.
    """
    rx = re.compile(r"\b([A-Z][A-Za-z'’\-]{1,})"
                    r"((?:\s+[A-Z]\.?(?=\s)){0,2})"
                    r"\s+" + re.escape(surname) + r"\b")
    return [(m.group(1), m.span()) for m in rx.finditer(text)]


def looks_like_a_person(seg):
    for m in NAMEISH.finditer(seg or ""):
        if (m.group(1).lower() not in FURNITURE
                and m.group(2).lower().strip(".,;:") not in FURNITURE):
            return m.group(0)
    return None


def get(url, cache=None):
    if cache is not None:
        key = os.path.join(cache, hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
        if os.path.exists(key):
            with open(key, encoding="utf-8") as f:
                raw = f.read()
            head, _, body = raw.partition("\n")
            return (int(head) if head.isdigit() else head, body)
    if GATE is not None:
        allowed, why = GATE.allows(url)
        if not allowed:
            # The page is never requested either way, but WHICH no it is
            # matters and must not be flattened. A host that SERVED a file
            # saying no has stated a policy; one whose robots.txt was
            # unreachable (the HTTP 202 captcha shape, a reset, a 500) has
            # stated nothing, and RFC 9309 makes us abstain rather than
            # assume. Recording the second as a refusal would put words in a
            # county's mouth; recording the first as an outage would invite a
            # re-probe with different headers, which is the wrong answer to a
            # site that has said no.
            stated = why.startswith("robots.txt served")
            return ("%s: %s" % ("robots-refused" if stated
                                else "robots-unknown", why), "")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        out = (r.status_code, r.text if r.status_code == 200 else "")
    except Exception as e:
        out = (type(e).__name__, "")
    if cache is not None:
        with open(key, "w", encoding="utf-8") as f:
            f.write("%s\n%s" % (out[0], out[1]))
    return out


def pages_for(base, cache=None):
    """The county's home page, its supervisor-ish links, then guessed paths."""
    out, seen = [], set()
    code, home = get(base, cache)
    if home:
        out.append((base, home))
        seen.add(base.rstrip("/"))
        cand = []
        for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', home, re.I | re.S):
            href, label = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
            if not (LINKRX.search(href) or LINKRX.search(label)):
                continue
            u = urljoin(base, href)
            if urlparse(u).netloc != urlparse(base).netloc or NEWSRX.search(u):
                continue
            if OTHERBODYRX.search(u):
                continue
            if u.rstrip("/") in seen:
                continue
            seen.add(u.rstrip("/"))
            # a link whose own PATH names the board outranks one that only
            # mentions it in link text
            cand.append((0 if LINKRX.search(urlparse(u).path) else 1, u))
        for _, u in sorted(cand)[:MAX_PAGES - 1]:
            c, t = get(u, cache)
            if t:
                out.append((u, t))
    for p in PATHS:
        if len(out) >= MAX_PAGES:
            break
        u = urljoin(base, p)
        if u.rstrip("/") in seen:
            continue
        seen.add(u.rstrip("/"))
        c, t = get(u, cache)
        if t:
            out.append((u, t))
    return out, code


def chairs_in(page, roster):
    """-> [{roster, page_form, how, gap_chars, ...}] for one page."""
    root = parse_html(page)
    nodes = [n for n in root.walk() if isinstance(n, Node)]
    txt = {id(n): n.text() for n in nodes}
    msk = {id(n): mask_vice(txt[id(n)]) for n in nodes}
    surnames = {}
    for r in roster:
        f, s = split_name(r["name"])
        if s:
            surnames.setdefault(s, []).append((f, r["name"]))

    def occ(t):
        hits = []
        for s, entries in surnames.items():
            for first, full in entries:
                for pf, span in name_occurrences(t, s):
                    if first_match(pf, first)[0]:
                        hits.append((full, pf + " " + s, first_match(pf, first)[1], span))
        return hits

    found = []
    for n in nodes:
        if n.tag == "#root":
            continue
        here = occ(txt[id(n)])
        if not here or len({h[0] for h in here}) != 1:
            continue
        if any(isinstance(k, Node) and occ(txt[id(k)]) for k in n.kids):
            continue                       # a child holds it: that child is smaller
        up, depth = n, 0
        while up is not None and up.tag != "#root":
            spans = [x.span() for x in CHAIR.finditer(msk[id(up)])]
            if spans:
                t = txt[id(up)]
                allh = occ(t)
                if len({h[0] for h in allh}) == 1:
                    mine = [h for h in allh if h[0] == here[0][0]] or here
                    best = None
                    for (a, b) in spans:
                        for ns in [h[3] for h in mine]:
                            if a >= ns[1]:            # role AFTER name
                                g, between, before = a - ns[1], t[ns[1]:a], None
                            else:                     # role BEFORE name
                                g, between = ns[0] - b, t[b:ns[0]]
                                before = t[max(0, a - 40):a]
                            if g > GAP_CAP or looks_like_a_person(between):
                                continue
                            if before is not None and looks_like_a_person(before):
                                continue
                            if best is None or g < best[0]:
                                # (gap, evidence, span-start, span-end) — the
                                # two spans are what the refusals window on
                                best = (g, t[max(0, ns[0] - 10):b + 40],
                                        min(ns[0], a), max(ns[1], b))
                    if best is not None:
                        # BOTH refusals below read from the same scoped
                        # window. The lead window is cut from the PARENT where the
                        # parent is small, because a body's name is as often a
                        # SIBLING heading as it is inline: `<h3>Regional
                        # Planning Commission</h3><p>Kevin Weber, Chair</p>`
                        # keeps the heading out of the accepted container
                        # entirely. Only backwards, and only when the parent is
                        # record-sized -- widening to a page reaches a nav that
                        # names every commission in the county.
                        scope, shift = t, 0
                        par = up.parent
                        if par is not None and par.tag != "#root":
                            pt = txt[id(par)]
                            at = pt.find(t)
                            if len(pt) <= OTHERBODY_SCOPE_CAP and at >= 0:
                                scope, shift = pt, at
                        lo = max(0, shift + best[2] - OTHERBODY_LEAD)
                        if OTHERBODY_TEXT.search(scope[lo:shift + best[3]]):
                            best = None      # a chair of some OTHER body
                    if best is not None:
                        # The term sits just AFTER the pairing -- and, like the
                        # body heading, often OUTSIDE the accepted container:
                        # Mahaska's accepted box ends at the name, with "Term:
                        # 2017 - 2020" in the parent beside it, so testing the
                        # container alone let it through on the live page while
                        # refusing the same markup synthetically. Same scope.
                        if stale_term(scope[shift + best[2]:shift + best[3] + 40]) is not None:
                            best = None
                    if best is not None:
                        found.append({
                            "roster": here[0][0], "page_form": here[0][1],
                            "how": here[0][2], "gap_chars": best[0],
                            "container_tag": up.tag, "evidence": best[1].strip(),
                        })
                        break
            up, depth = up.parent, depth + 1
    return found


def one_county(fips, meta, officers, cache=None):
    roster = (officers.get("19" + fips) or {}).get("supervisors") or []
    if not roster:
        return {"fips": fips, "county": meta["county"], "verdict": "no-roster"}
    pages, code = pages_for(meta["url"], cache)
    pages = [(u, b) for u, b in pages if not OTHERBODYRX.search(u)]
    if not pages:
        # A ROBOTS REFUSAL IS NOT AN OUTAGE and must not be counted as one:
        # "unreachable" is a fact about the network and invites a re-probe
        # with different headers, which is exactly the wrong response to a
        # site that has said no. The entry stays in the directory either way.
        refused = str(code).startswith("robots-refused")   # stated, not merely silent
        return {"fips": fips, "county": meta["county"],
                "verdict": "robots-refused" if refused else "unreachable",
                "code": str(code)}
    hits = []
    for url, body in pages:
        for h in chairs_in(body, roster):
            h["url"] = url
            hits.append(h)
    who = sorted({h["roster"] for h in hits})
    if len(who) != 1:
        return {"fips": fips, "county": meta["county"],
                "verdict": "many" if who else "none", "who": who}
    best = min(hits, key=lambda h: h["gap_chars"])
    return {"fips": fips, "county": meta["county"], "verdict": "one",
            "chair": who[0], "pageName": best["page_form"], "match": best["how"],
            "gapChars": best["gap_chars"], "evidence": best["evidence"],
            "sourceUrl": best["url"], "witnesses": len(hits)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--county", action="append", default=[])
    ap.add_argument("--cache", action="store_true",
                    help="reuse pages already fetched into .cache/pages")
    args = ap.parse_args()
    cache = None
    if args.cache:
        cache = os.path.join(CACHE_DIR, "pages")
        os.makedirs(cache, exist_ok=True)

    global GATE
    GATE = RobotsGate(requests.Session(), HEADERS["User-Agent"])

    directory = json.load(open(DIRECTORY, encoding="utf-8"))
    officers = json.load(open(OFFICERS, encoding="utf-8"))
    items = sorted(directory.items())
    if args.county:
        want = {c.lower() for c in args.county}
        items = [(k, v) for k, v in items if v["county"].lower() in want]

    print("ia-county-chair-scraper: %d counties" % len(items), flush=True)
    rows, counts = [], {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(lambda kv: one_county(kv[0], kv[1], officers, cache), items):
            rows.append(r)
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
            if r["verdict"] == "one":
                extra = "= %s" % r["chair"]
                if r["match"] != "exact":
                    extra += "   (%s join: page %r)" % (r["match"], r["pageName"])
                print("  %-15s %-11s %s" % (r["county"], r["verdict"], extra), flush=True)
    print("\n  " + "  ".join("%s %d" % kv for kv in sorted(counts.items())))
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, sort_keys=True)
    print("  wrote %s" % OUT_PATH)


if __name__ == "__main__":
    main()
