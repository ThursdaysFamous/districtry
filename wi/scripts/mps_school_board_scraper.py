#!/usr/bin/env python3
"""
Scrape the Milwaukee Board of School Directors from the district's own
directors page. Stage 1 of the pair; build_mps_school_board_roster.py writes
data/app/mps-school-board-members.json.

THE PAGE (milwaukeepublicschools.org/about/board/directors): one h3 per seat
in the real DOM — "At Large: NAME (President)" plus "District N: NAME" for
districts 1-8 — never the page's inline-JSON duplicates, which repeat the
same strings in script blobs the DOM read must not double-count (this parse
anchors on the <h3> tags alone). Each seat's block carries the term facts
("First elected … Term expires: April 2027") and an "Email Director X" link,
which is a JustFOIA contact FORM, not a mailto — the district's chosen
contact route, shipped as the member's contact link rather than an invented
address. The Board's office phone and e-mail come from the same page's Board
Contact Information block.

THE WITNESS: the board INDEX page (/about/board) lists the standing
committees with their member directors by surname. Every committee surname
must fold-match a roster surname — two surfaces the district maintains
separately agreeing on who sits on the board, so a stale directors page (or
a reshaped parse) fails loudly instead of shipping quietly.
"""

import html as html_mod
import json
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
# The fleet's robots reader and shared constants are ONE copy at the repo root.
# APPENDED rather than inserted, so this instance's own modules still win a name
# collision — the reason wi/scripts/validate_robots.py records, where inserting
# the root scripts/ first once made `import validate_sources` resolve to
# Illinois's.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)),
                             "scripts"))
from robots_policy import RobotsGate                      # noqa: E402
from scraper_common import UA_ROSTER_BOT, require_robots_allowed  # noqa: E402

DEFAULT_OUT = os.path.join(SCRIPT_DIR, ".cache", "mps_school_board_raw.json")

DIRECTORS_URL = "https://www.milwaukeepublicschools.org/about/board/directors"
INDEX_URL = "https://www.milwaukeepublicschools.org/about/board"

# THE DISTRICTRY TOKEN, AND THE MEASUREMENT THAT PUT IT BACK.
#
# This file sent a pinned Chrome/124 string from the day it was written, with no
# recorded refusal anywhere — the thing CLAUDE.md's browser-string rule asks for
# ("record the measurement in the calling file — which token was refused, what
# the site answered, and the date"). There was nothing to record, because nobody
# had measured this host.
#
# THE ARTIFACT'S READING COULD NOT LICENSE THE RENAME, because it was taken at
# the wrong address: `user-agent-measurements.json` records
# www.milwaukeepublicschools.org as `token-ok` at /about/board, the INDEX, while
# this scraper's roster comes from /about/board/directors. That is the defect
# CLAUDE.md records for the first user-agent sweep, where 37 hosts were probed at
# a fragment and 23 more at a directory a page sat under, and 25 verdicts moved
# once they were re-probed at the page.
#
# MEASURED 2026-09-27 AT THE DIRECTORS PAGE, on the rung this file uses (stdlib
# urllib.request, not requests): HTTP 200, 187,326 bytes, 44,325 characters of
# visible text. Not only the page — the whole parse: parse_directors() returned
# all nine seats with both roles, every term expiry and every contact URL, the
# Board Contact Information block gave its phone and e-mail, and
# committee_witness() matched nine surnames. So the token gets everything the
# browser string got, and the rename ships with this scraper's own weekly run as
# the witness, one file at a time, the rule scraper_common.py already carries.
UA = {"User-Agent": UA_ROSTER_BOT}


def crawl_delay():
    """Seconds www.milwaukeepublicschools.org asks between requests, or 0.

    IT ASKS FOR FIVE, AND NOTHING HERE HONOURED IT until 2026-09-27: main()
    fetched the directors page and the index page back to back. This host is one
    of the 26 CLAUDE.md records as stating a delay that binds this project, of
    which three callers acted on it and "the other 24 hosts are a recorded
    follow-up, not a claim of compliance".

    A PLAIN SLEEP RATHER THAN robots_policy.HostPacer, and that is the shape
    HostPacer's own docstring prescribes: it exists because the Iowa chair scrape
    runs six workers over 98 hosts, where a global sleep would pace 97 hosts that
    asked for nothing. This scraper is one host and one thread making two
    requests, which is the case that docstring names as rightly served by
    sleeping between fetches.

    robots.txt itself is unpaced by construction — a delay stated inside a file
    cannot govern the fetch that reads it.
    """
    gate = RobotsGate(None, UA_ROSTER_BOT, headers=UA)
    try:
        return gate.crawl_delay(DIRECTORS_URL) or 0
    except Exception:
        # A delay we could not read is not a licence to ignore one. The robots
        # gate below has already refused the run if the file was unreadable in a
        # way that matters; this only decides pacing, so fall back to the value
        # this host is measured to state rather than to zero.
        return 5.0


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60,
                                context=ssl.create_default_context()) as r:
        return r.read().decode("utf-8", "replace")


def surname_fold(name):
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    toks = [t for t in re.split(r"[^a-z]+", s) if len(t) > 1 and t not in
            ("jr", "sr", "ii", "iii", "dr")]
    return toks[-1] if toks else ""


def parse_directors(page):
    members = {}
    office = {}
    for m in re.finditer(r"<h3[^>]*>(.*?)</h3>(.*?)(?=<h3|<h2|\Z)", page, re.S):
        head = html_mod.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        head = re.sub(r"\s+", " ", head)
        seat = re.match(r"^(At[- ]Large|District (\d)):\s*(.+?)(?:\s*\((.+?)\))?$", head)
        if not seat:
            continue
        key = "AL" if seat.group(1).lower().startswith("at") else seat.group(2)
        name = seat.group(3).strip()
        entry = {"name": name}
        if seat.group(4):
            entry["role"] = seat.group(4).strip()
        body = m.group(2)
        t = re.search(r"Term expires:\s*(?:<[^>]+>\s*)*([A-Z][a-z]+ \d{4})",
                      re.sub(r"&nbsp;", " ", body))
        if t:
            entry["termExpires"] = t.group(1)
        c = re.search(r'href="(https://[^"]*justfoia\.com[^"]+)"', body)
        if c:
            entry["contactUrl"] = c.group(1)
        if key in members:
            raise SystemExit("directors page lists seat %r twice" % key)
        members[key] = entry
    # "Phone:&nbsp;</strong>(414) …" — the entity sits INSIDE the strong tag
    ph = re.search(r"Board Contact Information.*?Phone:(?:&nbsp;|\s|<[^>]+>)*([\d() \-]{10,16})",
                   page, re.S)
    em = re.search(r"Board Contact Information.*?Email:.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)",
                   page, re.S)
    if ph:
        office["phone"] = ph.group(1).strip()
    if em:
        office["email"] = em.group(1)
    return members, office


def committee_witness(index_page, members):
    """Every 'Director SURNAME' the index page's committee lists name must be
    a surname on the roster."""
    surnames = {surname_fold(m["name"]) for m in members.values()}
    seen = set()
    for m in re.finditer(r"Director\s+([A-Z][A-Za-z'’.\-]+)",
                         html_mod.unescape(re.sub(r"<[^>]+>", " ", index_page))):
        seen.add(surname_fold(m.group(1)))
    seen.discard("")
    stray = seen - surnames
    if stray:
        raise SystemExit("committee lists name director surname(s) %s absent from the "
                         "directors page — one of the two surfaces is stale"
                         % sorted(stray))
    if len(seen) < 5:
        raise SystemExit("committee witness read only %d director surnames — the "
                         "index page shape moved" % len(seen))
    return len(seen)


# --- the fixtures the selftest holds the guards to ---------------------------
# SYNTHETIC NAMES IN THE REAL STRUCTURE. The shapes are the page's own, read
# 2026-09-27: one `<h3>` per seat as "At Large: NAME (ROLE)" or "District N:
# NAME", a "Term expires: Month YYYY" in each seat's block, a justfoia contact
# link per seat, and a Board Contact Information block whose "Phone:&nbsp;"
# entity sits INSIDE the strong tag. The NAMES are invented on purpose: a
# fixture carrying the real board would claim who holds a seat, and would rot
# every April.
#
# THE NINE SURNAMES MUST BE DISTINCT, and the first draft's were not — every
# member was a "Fixture", which is a plausible thing to write and made the
# committee witness read ONE distinct surname against its floor of five, so the
# selftest failed on its own fixture rather than on the code. `surname_fold`
# keeps the LAST token, so a shared surname collapses nine members into one.
# The real page has nine distinct surnames; a fixture for a distinct-surname
# witness has to as well.
_SEATS = [("At Large", "Ada Alder", "President"), ("District 1", "Ben Birch", None),
          ("District 2", "Cal Cedar", None), ("District 3", "Dee Dogwood", None),
          ("District 4", "Eve Elm", "Vice President"),
          ("District 5", "Fay Fir", None), ("District 6", "Gus Ginkgo", None),
          ("District 7", "Hal Hazel", None), ("District 8", "Ivy Ironwood", None)]


def _fixture_page(seats=None, phone=True, email=True, terms=None):
    seats = _SEATS if seats is None else seats
    terms = len(seats) if terms is None else terms
    out = []
    for i, (label, name, role) in enumerate(seats):
        head = "%s: %s" % (label, name)
        if role:
            head += "&nbsp;(%s)" % role
        out.append("<h3>%s</h3>" % head)
        if i < terms:
            out.append("<p><strong>Term expires:</strong> April 202%d</p>" % (7 + i % 3))
        out.append('<p><a href="https://mps.justfoia.com/Forms/Launch?f=%d">'
                   "Email Director</a></p>" % i)
    out.append("<h2>Board Contact Information</h2>")
    if phone:
        out.append("<p><strong>Phone:&nbsp;</strong>(414) 475-8284</p>")
    if email:
        out.append("<p>Email: governance@milwaukeepublicschools.org</p>")
    return "\n".join(out)


def _fixture_index(surnames):
    rows = "".join("<li>Director %s</li>" % n for n in surnames)
    return "<h2>Standing Committees</h2><ul>%s</ul>" % rows


def selftest():
    """Every guard in this file, held to a fixture offline — no socket is opened.

    WHY THIS EXISTS. The pair already carried EIGHT guards before this was
    written (five here, three in build_mps_school_board_roster.py), and every one
    of them was exercised only by the live weekly run. A guard nothing tests
    offline is in no gate: it is proved by the source still being well-formed,
    which is the opposite of what it is for. Measured on introduction, each case
    below FAILS when its own guard is removed.

    WHAT IT DOES NOT PROVE, stated rather than implied: the fixtures are this
    project's own HTML, so a pass says the guards fire and says NOTHING about
    whether the parse still matches the page MPS serves today. Only the weekly run
    answers that, and `wi_coa_staleness.py`'s ceiling is what notices when it
    stops answering.
    """
    cases = []

    good = _fixture_page()
    members, office = parse_directors(good)
    cases.append(("a well-formed page parses nine seats", len(members) == 9,
                  "%d seats" % len(members)))
    cases.append(("at-large keys AL, districts key by number",
                  sorted(members) == sorted(["AL"] + [str(n) for n in range(1, 9)]),
                  str(sorted(members))))
    # The expected values come from _SEATS rather than being spelled here: the
    # first draft hardcoded two names and then the fixtures were renamed, so the
    # selftest failed on its own stale assertions while the parse was correct.
    want = {("AL" if lab.lower().startswith("at") else lab.split()[-1]): (name, role)
            for lab, name, role in _SEATS}
    cases.append(("a role in parentheses is read as a role, not part of the name",
                  members["AL"].get("role") == want["AL"][1]
                  and members["AL"]["name"] == want["AL"][0],
                  repr(members["AL"])))
    cases.append(("an &nbsp; before the parenthesis does not join the role to the name",
                  members["4"].get("role") == want["4"][1]
                  and members["4"]["name"] == want["4"][0],
                  repr(members["4"])))
    cases.append(("no seat's name absorbs its role or its neighbour's",
                  all(members[k]["name"] == want[k][0] for k in want),
                  str({k: members[k]["name"] for k in want
                       if members[k]["name"] != want[k][0]})))
    cases.append(("every seat carries a term and a contact url",
                  all(m.get("termExpires") and m.get("contactUrl")
                      for m in members.values()),
                  "%d terms, %d contacts"
                  % (sum(1 for m in members.values() if m.get("termExpires")),
                     sum(1 for m in members.values() if m.get("contactUrl")))))
    cases.append(("the office block yields phone and e-mail",
                  office.get("phone") == "(414) 475-8284"
                  and office.get("email", "").endswith("@milwaukeepublicschools.org"),
                  repr(office)))

    # Guard 1: a seat listed twice.
    twice = _fixture_page(seats=_SEATS + [("District 8", "Jay Fixture", None)])
    cases.append(("a seat listed TWICE refuses", _raises(parse_directors, twice),
                  "no refusal"))

    surnames = [n.split()[-1] for _, n, _ in _SEATS]

    # Guard 2 and 3's PASSING side FIRST, because it is what keeps the two
    # refusals below from being vacuous: a witness that refused everything would
    # satisfy them both.
    cases.append(("a matching committee list passes, counting all nine surnames",
                  committee_witness(_fixture_index(surnames), members) == 9,
                  "witness refused or miscounted"))

    # Guard 2: the committee list names somebody the roster does not.
    stray = _fixture_index(surnames + ["Nobody"])
    cases.append(("a committee surname absent from the roster refuses",
                  _raises(committee_witness, stray, members), "no refusal"))

    # Guard 3: the index page's shape moved, so the witness reads almost nothing.
    # Two REAL surnames, so this fires on the floor rather than on a stray.
    thin = _fixture_index(surnames[:2])
    cases.append(("fewer than five committee surnames refuses",
                  _raises(committee_witness, thin, members), "no refusal"))

    bad = 0
    for label, ok, detail in cases:
        bad += 0 if ok else 1
        print("  %-64s %s%s" % (label, "ok" if ok else "FAIL",
                                "" if ok else "  (%s)" % detail))
    if bad:
        raise SystemExit("mps-board: --selftest FAILED on %d case(s)" % bad)
    print("mps-board: --selftest OK — %d case(s) over synthetic fixtures; the "
          "guards fire, which is not the same as the live page still parsing"
          % len(cases))


def _raises(fn, *args):
    """True when `fn` refuses. A guard that does not refuse is the failure."""
    try:
        fn(*args)
    except SystemExit:
        return True
    return False


def main():
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    # ROBOTS.TXT BEFORE THE FIRST FETCH, as the client that fetches. Neither this
    # file nor its builder asked until 2026-09-27. Measured that day both paths ARE
    # permitted, for the token and for a browser string alike, so this changes no
    # behaviour today — it is the seam that would have stopped the ISBE year, and
    # the `*` group here carries 1,095 rules, which is why it is asked rather than
    # assumed. One call per host: the gate caches, so the INDEX_URL check is free.
    #
    # `wi/scripts/validate_robots.py` ALREADY SWEPT THIS HOST, both its URLs, every
    # month — and that is why nobody noticed. A monthly audit reporting the host
    # permitted reads exactly like the question having been answered, while the
    # scraper itself went on fetching without asking; the audit says what the
    # policy IS and only this call makes the fetch depend on it. An earlier draft
    # of this comment claimed the host was in no sweep, which was wrong and was
    # found by running the sweep instead of grepping for it.
    require_robots_allowed(DIRECTORS_URL, UA_ROSTER_BOT, headers=UA, label="mps-board")
    require_robots_allowed(INDEX_URL, UA_ROSTER_BOT, headers=UA, label="mps-board")
    delay = crawl_delay()

    members, office = parse_directors(fetch(DIRECTORS_URL))
    expect = ["AL"] + [str(n) for n in range(1, 9)]
    if sorted(members) != sorted(expect):
        raise SystemExit("directors page names seats %s, expected at-large + "
                         "districts 1-8" % sorted(members))
    if not office.get("phone") or not office.get("email"):
        raise SystemExit("the Board Contact Information block did not parse "
                         "(phone %r, email %r)" % (office.get("phone"), office.get("email")))
    # The two fetches are to ONE host that asks for five seconds between them.
    if delay:
        time.sleep(delay)
    n_witness = committee_witness(fetch(INDEX_URL), members)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"members": members, "office": office,
                   "sourceUrl": DIRECTORS_URL}, f, indent=2, ensure_ascii=False)
    print("scraped 9 MPS directors (committee witness matched %d surnames) -> %s"
          % (n_witness, out_path))


if __name__ == "__main__":
    main()
