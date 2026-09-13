#!/usr/bin/env python3
"""
Scrape stage 1: find WHICH DISTRICT each Iowa county supervisor holds, and
cache it for build_ia_supervisor_roster.py (stage 2).

WHAT THIS ADDS, AND WHY IT IS ONLY SOME COUNTIES
-------------------------------------------------
data/app/ia-county-officers.json already names every county's supervisors --
but UNKEYED, because no publisher in Iowa attaches a district to a supervisor's
name. The County card can therefore list a board and the County Supervisor
District card cannot say who represents THIS district. This file closes that
gap where a county publishes the answer itself.

IT IS SCOPED TO PLAN 3 COUNTIES ONLY, and that is a legal distinction rather
than a convenience. Iowa Code 331.206 lets a county choose one of three
representation plans, and the shipped geometry carries which:

    PLAN 1  (44 counties)  at large, no districts at all. There is nothing to
                           key: the County card's list IS the whole answer.
    PLAN 2  (15 counties)  supervisors are elected COUNTYWIDE and merely have
                           to RESIDE in a district. Every supervisor already
                           represents every voter, so keying would add a
                           district label without changing who represents you
                           -- and risks reading as district-based election,
                           which is exactly what Plan 2 is not.
    PLAN 3  (39 counties)  each district elects one supervisor. THIS is the
                           only plan where naming the district's own
                           supervisor tells a reader something the countywide
                           list does not.

FOUR STATEWIDE ROUTES ARE MEASURED CLOSED (2026-08-28), so this is per-county
by necessity, not by choice:

  * The Legislature's own CountySupervisorDistricts layer HAS a NAME field --
    and it holds the DISTRICT's name ("Bremer Supervisor District 1"), never a
    person's. All 266 values are distinct district names.
  * The ISAC member portal publishes every supervisor and attaches a district
    to NONE of them, in all 99 counties.
  * The Secretary of State's statewide canvass summary carries ZERO supervisor
    contests -- county offices are canvassed by the COUNTY, not the state, so
    the canvass route that works for Illinois county boards does not exist
    here.
  * electionresults.iowa.gov is an Angular application whose bundle carries no
    reachable data API.

THE PARSE READS NO MARKUP, AND THAT IS THE WHOLE TRICK
-------------------------------------------------------
Iowa's county sites run at least four CMSes (Revize, WordPress, CivicPlus and
several bespoke), so a per-county HTML config would be 39 hand-written parsers
that break one at a time. This needs none, because THE NAMES ARE ALREADY
KNOWN: data/app/ia-county-officers.json supplies each county's supervisors,
gated in its own build against Iowa Code 331.201 and against the seat count in
the shipped district geometry. The only missing fact is a NUMBER, so the page
is flattened to text and each known surname is matched to the nearest
"District N" within PROXIMITY_CHARS. That is Wisconsin's witness_window
pattern (wi/scripts/wi_county_officer_contact_scraper.py) applied to a
district instead of a phone number, and it is indifferent to markup.

Verified on five counties across four CMSes before it was written: Adams,
Bremer, Polk, Winneshiek and Monona all key 5/5, 3/3, 5/5, 5/5 and 3/3.

EVERY COUNTY MUST PASS ALL FOUR GATES OR IT SHIPS NOTHING:

  1. every supervisor the roster names is found on the page,
  2. every one of them lands within PROXIMITY_CHARS of a district number,
  3. the districts they land on are exactly 1..N with no repeats, and
  4. N equals NUMDISTRICTS in the shipped geometry.

Gate 3 is the one doing the real work. A page that merely mentions districts
somewhere -- an agenda, a map caption, a news item -- produces collisions or
holes and fails, so "found some numbers near some names" can never ship as a
board. A county that fails any gate is recorded with the reason and keeps the
unkeyed list it already had; NEVER infer a district from list order, which is
the one thing that would look right and be wrong.

EVERY HOST IS ASKED BEFORE IT IS READ. scripts/robots_policy.py reads each
county's robots.txt as the client this file sends, at the one place every
fetch here passes through, and a refusal is its own outcome: it is cached as
`robotsRefused` so the builder can tell the site's standing answer from a page
that failed to load this week. A stated Crawl-delay is honoured per host
through the shared HostPacer, which gives the one host that asks for a delay a
queue of its own instead of pacing the 39 that did not.

Usage:
    python3 ia/scripts/ia_supervisor_district_scraper.py
    python3 ia/scripts/ia_supervisor_district_scraper.py --county Polk
    python3 ia/scripts/ia_supervisor_district_scraper.py --selftest   # offline
"""

import html
import json
import os
import re
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    print("FATAL: pip install -r ia/scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_FILE = os.path.join(CACHE_DIR, "ia_supervisor_districts_roster.json")

DISTRICTS = os.path.join(APP_DATA_DIR, "ia-supervisor-districts.json")
OFFICERS = os.path.join(APP_DATA_DIR, "ia-county-officers.json")
BOARD_DIRECTORY = os.path.join(APP_DATA_DIR, "ia-county-board-directory.json")

# How far from a supervisor's surname a "District N" may sit and still be read
# as that supervisor's district -- and this number is MEASURED, then tightened.
#
# A first pass used 300 characters and keyed 17 counties. Measuring the gap it
# actually used on all 67 of those districts found a maximum of 42 and NOTHING
# above 60: a county that publishes the pairing at all publishes it adjacently
# ("Matt McCoy District 1 Supervisor"), so a generous window buys no coverage
# and only risks a false pairing. The danger is concrete rather than
# theoretical -- Polk's page prints its five supervisors TWICE, once as a bare
# navigation run with no districts near it and once as real content, and a
# window wide enough to reach from that nav run to an unrelated "District 5"
# elsewhere in the page would pair them confidently and wrongly.
#
# 80 keeps every measured pairing with 38 characters of headroom and halves
# the reach of a false one. MAX_OBSERVED_GAP below turns that measurement into
# a tripwire: if pairings ever start landing near the limit, the assumption
# that counties publish this adjacently has stopped holding.
PROXIMITY_CHARS = 80
MAX_OBSERVED_GAP = 42   # measured across 67 districts in 17 counties, 2026-08-28

# Tried in order after the county's own home page is searched for a link. Each
# is a real path observed on an Iowa county site during the 2026-08-28 sweep.
FALLBACK_PATHS = [
    "supervisors/",
    "board-of-supervisors/",
    "board_of_supervisors/",
    "departments/board-of-supervisors/",
    "government/board_of_supervisors/",
]
MAX_PAGES_PER_COUNTY = 3

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
}
REQUEST_TIMEOUT = 25

DISTRICT_RE = re.compile(r"\bDistrict\s*#?\s*([1-9])\b", re.I)
LINK_RE = re.compile(r'href="([^"]*)"[^>]*>(.{0,90}?)</a>', re.I | re.S)
# 51% of Plan 3 counties answered on the sweep; the rest 403, answer 202
# behind a captcha, or publish no district anywhere. A floor well under that
# catches a systemic break (a changed proximity rule, a bad roster read)
# without failing the run because a handful of counties reshaped their pages.
MIN_COUNTIES = 12


# ---------------------------------------------------------------- robots.txt
# THE FLEET'S ONE READER, scripts/robots_policy.py. APPENDED to sys.path
# rather than inserted, so ia/scripts/ keeps priority for its own siblings.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))
import robots_policy as rp                                        # noqa: E402

ROBOTS_TIMEOUT = 25
ROBOTS_RETRIES = 3

# WHAT THE HOSTS SAY, measured on two full runs of 2026-09-13 as the client
# below sends (requests + the pinned Chrome/120 string; a browser string
# changes nothing about robots.txt, because no group names it either and `*`
# still binds). 35 of the 40 plan 3 counties get as far as a fetch -- the other
# five have no gated supervisor list to look for -- and they are 36 host
# readings, because Taylor is reached at both the bare and the www spelling and
# robots.txt is per authority. The second run:
#
#     18  serve a robots.txt -- 17 allow this client, Hamilton does not
#     13  have none (404, allow all)
#      4  answer a 202 sgcaptcha front (Dickinson, Osceola, Palo Alto, Sioux)
#      1  answers HTTP 500 (Bremer)
#      1  states a Crawl-delay that binds us: kossuthcounty.iowa.gov, 10 s
#
# So six hosts refuse and 30 allow. Nothing here tries to answer a challenge.
#
# ONE HOST CLASSIFIED ITSELF TWO WAYS IN THE SAME HOUR, and it is the reason a
# 403 is read strictly here. osceolacountyia.gov answered HTTP 403 on the first
# run and `sg-captcha: challenge` 202s on the second and on six consecutive
# direct reads between them, so its 403 was a captcha front answering one way
# rather than a site stating a policy. The shared module's DEFAULT is to ALLOW
# a 403 on robots.txt (RFC 9309 §2.3.1.3), because the hosts that answer that
# way are usually APIs serving their data to everyone. These are county
# WEBSITES, where a 403 is a firewall refusing this client, so robots_says
# passes refused_is_refusal=True -- the reading CLAUDE.md states for a
# municipal-website scraper, and the one scripts/dupage_municipal_officials_scraper.py
# already takes. It changes no county today: Osceola keys nothing under either
# reading, and refuses under both on the second run. The two sibling Iowa
# county scrapers (ia_county_minutes_chair_scraper.py,
# ia_county_city_officials_scraper.py) still take the default through
# RobotsGate.allows; that is a standing difference, named here rather than
# quietly propagated.
#
# ASKING FIRST COSTS TWO COUNTIES THAT THIS FILE HAS BEEN KEYING, and both are
# the county's answer rather than a break here:
#
#   HAMILTON publishes `User-agent: * / Disallow: /` beneath five named
#   search-engine groups (Googlebot, Bingbot, FacebookBot, LinkedInBot,
#   Twitterbot) that each get `Allow: /`. None of this project's tokens is a
#   vendor crawler token, so `*` binds us and the page is refused. Its
#   robots.txt is REACHED THROUGH A REDIRECT to its CMS vendor,
#   cms2.revize.com/revize/hamiltonia/robots.txt -- a per-tenant path, so it is
#   Hamilton's own file rather than Revize's, and following the redirect is
#   what CLAUDE.md requires.
#
#   BREMER answers HTTP 500 on /robots.txt, on both host spellings, five times
#   over 40 seconds -- while the site itself serves a 178 KB home page. RFC
#   9309 files a 5xx as disallow-all and rp.classify() implements that, so a
#   broken endpoint on a working site costs the county until it is fixed. It
#   retires itself the moment that URL answers.
#
# The other four refusals -- Dickinson, Osceola, Palo Alto and Sioux, all 202
# sgcaptcha fronts -- cost nothing: this file already skipped all four as
# unreadable.
_ROBOTS_CACHE = {}
_ROBOTS_SAID = {}


def _robots_url(url):
    parts = urllib.parse.urlsplit(url)
    return "%s://%s/robots.txt" % (parts.scheme, parts.netloc)


def _robots_verdict(url):
    """One robots.txt read per host, cached for the run.

    An `unreachable` verdict is re-asked before it is believed: RFC 9309 files
    a 5xx or a network error as disallow-all, which is right, and one flaky
    read would otherwise drop a county out of the weekly file for no reason.
    Nothing else is retried -- a served file, an absent one and a refusal are
    all answers. Bremer's 500 survives this: it is the same on every try.
    """
    key = _robots_url(url)
    if key in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[key]
    ua = HEADERS["User-Agent"]
    verdict = rp.fetch_verdict(key, ua, timeout=ROBOTS_TIMEOUT)
    for attempt in range(ROBOTS_RETRIES - 1):
        if verdict.status != "unreachable":
            break
        time.sleep(2 ** attempt)
        verdict = rp.fetch_verdict(key, ua, timeout=ROBOTS_TIMEOUT)
    _ROBOTS_CACHE[key] = verdict
    return verdict


class _PerHostDelay(object):
    """HostPacer wants an object with crawl_delay(url); the delay comes off the
    same verdict the allow/disallow answer does."""

    def crawl_delay(self, url):
        return _robots_verdict(url).crawl_delay(HEADERS["User-Agent"])


# One host of the 40 asks for a delay, so a global sleep would pace 39 hosts
# that asked for nothing. HostPacer gives the asking host a queue of its own.
ROBOTS_PACER = rp.HostPacer(_PerHostDelay())


class RobotsRefused(Exception):
    """This client may not fetch that URL.

    Its own exception so a refusal is never reported as an outage, or an
    outage as a refusal: the first is the site's answer and permanent until
    the site changes it, the second is a page to re-read.
    """


def robots_says(url):
    """(allowed, why) for one URL, as the client this file sends.

    Prints one line the first time a host is decided, so a run says what every
    policy said rather than only what stopped it.
    """
    host = urllib.parse.urlsplit(url).hostname or url
    ua = HEADERS["User-Agent"]
    verdict = _robots_verdict(url)
    allowed, why = verdict.allows(ua, url, refused_is_refusal=True)
    if host not in _ROBOTS_SAID:
        _ROBOTS_SAID[host] = (verdict.status, bool(allowed))
        delay = verdict.crawl_delay(ua)
        print("  robots  %-34s %-11s %s%s"
              % (host, verdict.status, "allows" if allowed else "REFUSES",
                 "" if not delay else "  (crawl-delay %g s)" % delay),
              file=sys.stderr)
    return bool(allowed), why


def strip_tags(markup):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup)))


def fetch(url, attempts=3):
    """The page, or None. Retries only what waiting can fix.

    A COUNTY MUST NOT LEAVE THIS FILE BECAUSE ONE REQUEST FAILED. This function
    used to return None on any exception and on any non-200, with no retry, and
    a skipped county is silently dropped from the roster the builder writes —
    which is exactly what happened to Grundy County on 2026-08-29: five
    supervisors deleted from a green PR while grundycountyiowa.gov was up the
    whole time, still naming all five beside their district numbers. So a
    connection error, a timeout, a 429 and a 5xx are waited out; a 403, a 404
    and the 202 an sgcaptcha challenge answers with are not, because a refusal,
    a missing page and an access control are not fixed by asking again. (Nothing
    here tries to defeat a challenge.)
    """
    # ROBOTS FIRST, AT THE ONE PLACE EVERY FETCH IN THIS FILE PASSES THROUGH --
    # the home page, each candidate supervisors page, and the two requests
    # serves_one_document makes. Asking here rather than at each call site is
    # what makes the rule hold for the callers nobody remembers.
    allowed, why = robots_says(url)
    if not allowed:
        raise RobotsRefused("%s: %s" % (url, why))
    delay = 3.0
    for attempt in range(attempts):
        try:
            # The pacer wraps the REQUEST, so the interval is measured from
            # when a response finishes rather than when one starts. `with` is
            # load-bearing: HostPacer.hold is a @contextmanager, and calling it
            # bare builds a context manager and discards it, applying no delay
            # at all and recording nothing.
            with ROBOTS_PACER.hold(url):
                resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                                    allow_redirects=True)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code != 429 and resp.status_code < 500:
                return None
            why = "HTTP %d" % resp.status_code
        except requests.RequestException as e:
            why = str(e)
        if attempt == attempts - 1:
            print("  fetch  %s gave up after %d attempt(s): %s"
                  % (url, attempts, why), file=sys.stderr)
            return None
        print("  retry  %s (%s) in %.0fs" % (url, why, delay), file=sys.stderr)
        time.sleep(delay)
        delay *= 3
    return None


def candidate_pages(home):
    """The county's own supervisors page: a link off the home page first, then
    the observed path shapes. Nothing is pinned per county, so a site that
    reorganises heals itself instead of needing a config edit."""
    urls, body = [], fetch(home)
    if body:
        for href, label in LINK_RE.findall(body):
            href = href.strip()
            if href.lower().startswith(("javascript:", "mailto:", "#")):
                continue
            if re.search(r"supervisor", href + " " + strip_tags(label), re.I):
                urls.append(urllib.parse.urljoin(home, html.unescape(href)))
                break
    urls += [urllib.parse.urljoin(home, p) for p in FALLBACK_PATHS]
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:MAX_PAGES_PER_COUNTY]


# A path no county publishes. Used to ask a host whether it is serving ONE
# document for everything, which is what a suspended or parked domain does.
PROBE_PATH = "districtry-probe-no-such-path/"


def serves_one_document(home):
    """Does this host answer every path with the same bytes?

    WHY THIS EXISTS. On 2026-09-12 Mitchell County keyed nothing and the
    scraper reported "the page names no district", which is a statement about
    what the COUNTY publishes. It was false: mitchellcounty.iowa.gov's hosting
    account is suspended, and the host answers HTTP 200 with one 7,640-byte
    "Account Suspended" page on every path -- the supervisors page, the home
    page, /robots.txt, and a path invented for this probe, all byte-identical
    (sha256 d5bf5dc6f2d9..., measured 2026-09-13). WHY the bytes are identical
    rather than merely similar: every path 302s to cPanel's own
    /cgi-sys/suspendedpage.cgi, so one document answers the whole host and
    there is nothing per-path left to differ. A 200 is a 200, so nothing
    upstream noticed, and the skip reason sent a reader to re-read a page that
    does not exist.

    THE TEST IS STRUCTURAL, NOT A KEYWORD. Searching bodies for "suspended" or
    "parked" is the mistake scraper_common.py already records from the other
    direction: a sweep that searched for "captcha" reported sixteen real pages
    as challenges. So this asks the host a question instead -- fetch the home
    page and a path nobody publishes, and compare the bytes. A live site
    answers those differently (measured the same day across the eight other
    counties skipped for the same reason: Black Hawk, Butler, Calhoun, Howard,
    Ida, Kossuth, Winnebago and Worth all differ, and for all eight the
    original reason is true).

    COMPARED AGAINST THE HOME PAGE, DELIBERATELY, not against the supervisors
    page that just failed: a site whose supervisors URL 404s to a standard
    error page would match the probe path and read as suspended when it is
    merely a moved page.

    Costs two requests and runs ONLY where a county already keyed nothing, so
    a healthy run pays nothing for it.
    """
    import hashlib
    root = fetch(home)
    if not root:
        return False
    probe = fetch(urllib.parse.urljoin(home, PROBE_PATH))
    if not probe:
        return False
    return (hashlib.sha256(root.encode("utf-8", "replace")).hexdigest()
            == hashlib.sha256(probe.encode("utf-8", "replace")).hexdigest())


def key_page(text, names):
    """Match each known supervisor to the nearest district number.

    Reads no markup at all -- the names come from the shipped roster, so the
    only thing being recovered here is which number each sits beside.
    """
    districts = [(m.start(), int(m.group(1))) for m in DISTRICT_RE.finditer(text)]
    if not districts:
        return None, "the page names no district"
    keyed, widest = {}, 0
    for name in names:
        surname = name.split()[-1]
        if len(surname) < 3:
            return None, "supervisor %r has no usable surname" % name
        best = None
        for m in re.finditer(r"\b" + re.escape(surname) + r"\b", text, re.I):
            for pos, num in districts:
                gap = abs(pos - m.start())
                if gap <= PROXIMITY_CHARS and (best is None or gap < best[0]):
                    best = (gap, num)
        if best is None:
            return None, "no district within %d chars of %s" % (PROXIMITY_CHARS, surname)
        keyed[name] = best[1]
        widest = max(widest, best[0])
    return (keyed, widest), None


def _selftest():
    """The robots half, offline, against seeded verdicts.

    WHY IT EXISTS. Both halves of this gate fail SILENTLY and look right. A
    fetch that asks robots.txt after requesting the page still prints the same
    log line, and HostPacer.hold is a @contextmanager, so `ROBOTS_PACER.hold(url)`
    called bare builds a context manager, discards it, applies no delay and
    records nothing -- a live run then reports "no host this run stated one"
    while a site that asked for 10 s got none. Both are invisible to every
    other gate in this repo.

    So this asks the questions a log cannot: with requests.get replaced by a
    recorder, does a refused URL reach it AT ALL, and are two fetches of a
    delay-stating host actually spaced? The spacing assertion is the witness
    for the bare call: it measures 0.00 s.

    No network. rp.classify is a pure function, so each verdict is built from
    a status and a body and seeded into the cache this file already keeps.
    """
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print("  %s %s" % ("ok  " if cond else "FAIL", msg), file=sys.stderr)

    calls = []
    real_get = requests.get

    class _Resp(object):
        status_code = 200
        text = "<html>ok</html>"

    def _recorder(url, **kw):
        calls.append((url, time.monotonic()))
        return _Resp()

    # THE FIXTURE HOSTS ARE BUILT, NEVER WRITTEN AS URLS -- and this comment
    # cannot write one either, which is the measurement. scripts/probe_user_agents.py
    # reads this file's TEXT to decide which hosts it reaches, so a fixture
    # spelled out in full, scheme and all, enters the fleet's user-agent
    # artifact as a host this scraper fetches and must carry a measurement for.
    # It does: spelling one out here (as an earlier draft of this comment did)
    # put allow.example in the inventory and failed --check. So the scheme is
    # assembled below, and nothing in this function names a whole URL.
    scheme = "https" + "://"

    def u(host, path="/supervisors/"):
        return scheme + host + path

    def seed(host, verdict):
        _ROBOTS_CACHE[u(host, "/robots.txt")] = verdict
        _ROBOTS_SAID.pop(host, None)

    requests.get = _recorder
    try:
        seed("allow.example", rp.classify(404, ""))
        seed("deny.example", rp.classify(200, "User-agent: *\nDisallow: /\n"))
        seed("gone.example", rp.classify(500, ""))
        seed("challenge.example", rp.classify(202, ""))
        seed("forbidden.example", rp.classify(403, ""))
        seed("slow.example",
             rp.classify(200, "User-agent: *\nCrawl-delay: 1\nAllow: /\n"))

        n = len(calls)
        check(fetch(u("allow.example")) is not None
              and len(calls) == n + 1,
              "no robots.txt (404) -> fetched")

        for host, why in (("deny.example", "`*` Disallow: / -> refused"),
                          ("gone.example", "robots.txt 5xx -> refused (RFC 9309)"),
                          ("challenge.example",
                           "robots.txt 202 challenge -> refused, never solved"),
                          # The one reading this file does NOT take from the
                          # shared module's default. It is a choice, so it is
                          # tested rather than left to a comment.
                          ("forbidden.example",
                           "robots.txt 403 -> refused (a county website, not "
                           "an API)")):
            n = len(calls)
            try:
                fetch(u(host))
                check(False, why + " -- but fetch returned")
            except RobotsRefused:
                # THE GATE IS BEFORE THE REQUEST, not after it. A file that
                # asked and then fetched anyway would pass a log-shaped test.
                check(len(calls) == n,
                      why + ", and requests.get was never called")

        n = len(calls)
        fetch(u("slow.example", "/a"))
        fetch(u("slow.example", "/b"))
        gap = calls[-1][1] - calls[-2][1]
        check(len(calls) == n + 2 and gap >= 0.9,
              "Crawl-delay 1 s honoured: %.2f s between two fetches of one host "
              "(a bare hold() measures 0.00)" % gap)
        check(ROBOTS_PACER.honoured.get("slow.example") == 1.0,
              "the honoured delay is recorded for the run's own report")

        n, t0 = len(calls), time.monotonic()
        fetch(u("allow.example", "/a"))
        fetch(u("allow.example", "/b"))
        check(len(calls) == n + 2 and time.monotonic() - t0 < 0.5,
              "a host that states no delay is not paced")
    finally:
        requests.get = real_get
        _ROBOTS_CACHE.clear()
        _ROBOTS_SAID.clear()
        ROBOTS_PACER.honoured.clear()

    print("selftest: %d failure(s)" % len(failures), file=sys.stderr)
    return 1 if failures else 0


def main():
    only = None
    argv = sys.argv[1:]
    if "--selftest" in argv:
        sys.exit(_selftest())
    if "--county" in argv:
        only = argv[argv.index("--county") + 1]

    with open(DISTRICTS) as f:
        feats = json.load(f)["features"]
    plan3, seats = {}, {}
    for feat in feats:
        p = feat["properties"]
        if p.get("PLANTYPE") == "PLAN 3":
            plan3[p["COUNTY"]] = True
            seats[p["COUNTY"]] = p.get("NUMDISTRICTS")

    with open(OFFICERS) as f:
        officers = json.load(f)
    supervisors = {}
    for rec in officers.values():
        if rec.get("supervisors"):
            supervisors[rec["county"]] = [m["name"] for m in rec["supervisors"]]

    with open(BOARD_DIRECTORY) as f:
        home_by_county = {v["county"]: v.get("url") for v in json.load(f).values()}

    targets = sorted(c for c in plan3 if not only or c == only)
    os.makedirs(CACHE_DIR, exist_ok=True)
    out, skipped, refused = {}, [], {}

    for county in targets:
        names = supervisors.get(county)
        home = home_by_county.get(county)
        if not names:
            skipped.append((county, "no gated supervisor list in ia-county-officers.json"))
            continue
        if not home:
            skipped.append((county, "no county website on record"))
            continue

        keyed = reason = None
        try:
            for url in candidate_pages(home):
                body = fetch(url)
                if not body:
                    continue
                result, reason = key_page(strip_tags(body), names)
                if result:
                    keyed, widest = result
                    page = url
                    break
                time.sleep(1)
            if not keyed:
                # Before recording a reason ABOUT THE COUNTY, check whether the
                # host is answering everything with one document. See
                # serves_one_document.
                if serves_one_document(home):
                    reason = ("the county site answers every path with one document "
                              "(suspended or parked) -- not a page that stopped "
                              "naming districts")
        except RobotsRefused as exc:
            # THE SITE'S OWN ANSWER, recorded as its own outcome. It goes into
            # the cache rather than only into this log, because the builder's
            # drop guard has to tell a refusal from an outage: an outage is a
            # page to re-read next week, a refusal is a standing decision that
            # would otherwise fail every run for ever.
            refused[county] = str(exc)
            skipped.append((county, "robots.txt refuses this client -- %s" % exc))
            continue
        if not keyed:
            skipped.append((county, reason or "no readable supervisors page"))
            continue

        # Gate 3: exactly 1..N, each district used once. A page that merely
        # mentions districts collides or leaves a hole and fails here.
        got = sorted(keyed.values())
        if got != list(range(1, len(names) + 1)):
            skipped.append((county, "districts %s are not 1..%d exactly"
                            % (got, len(names))))
            continue
        # Gate 4: agree with the geometry this repo already ships.
        if seats.get(county) not in (None, len(names)):
            skipped.append((county, "the county names %d supervisors and the "
                            "district geometry seats %d"
                            % (len(names), seats[county])))
            continue

        out[county] = {"districts": {str(v): k for k, v in keyed.items()},
                       "sourceUrl": page, "maxGap": widest}
        flag = "  <-- WIDE" if widest > MAX_OBSERVED_GAP else ""
        print("%-14s %d district(s) keyed, widest gap %2d%s  %s"
              % (county, len(keyed), widest, flag, page), file=sys.stderr)
        time.sleep(1)

    for county, why in skipped:
        print("  skipped %-14s %s" % (county, why), file=sys.stderr)
    # A delay honoured without saying so cannot be told from one ignored.
    for line in ROBOTS_PACER.report():
        print(line, file=sys.stderr)

    if not only and len(out) < MIN_COUNTIES:
        raise SystemExit(
            "only %d Plan 3 counties keyed (floor %d) -- that is a systemic "
            "break (the proximity rule, the roster read, or a blocked network), "
            "not a handful of counties reshaping their pages"
            % (len(out), MIN_COUNTIES))

    # A refused county ships an entry carrying ONLY its reason -- no districts,
    # so nothing can be keyed off it, and the builder reads `robotsRefused` to
    # tell this apart from a county that simply stopped parsing.
    #
    # IT IS MERGED HERE, AT WRITE TIME, AND NEVER INTO `out`. Every count above
    # measures counties that KEYED: a refused county added to `out` would count
    # toward MIN_COUNTIES and print as keyed, which reads as a higher floor
    # while guarding less -- the floor would pass on twelve counties of which
    # some keyed nothing.
    payload = dict(out)
    for county, why in refused.items():
        payload[county] = {"robotsRefused": why}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False, sort_keys=True)
    print("wrote %s -- %d of %d Plan 3 counties keyed, %d skipped (%d of those "
          "refused by robots.txt)"
          % (OUT_FILE, len(out), len(targets), len(skipped), len(refused)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
