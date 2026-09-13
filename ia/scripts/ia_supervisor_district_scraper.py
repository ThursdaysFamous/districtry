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

Usage:
    python3 ia/scripts/ia_supervisor_district_scraper.py
    python3 ia/scripts/ia_supervisor_district_scraper.py --county Polk
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
    delay = 3.0
    for attempt in range(attempts):
        try:
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
    (sha256 d5bf5dc6f2d9..., measured 2026-09-13). A 200 is a 200, so nothing
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


def main():
    only = None
    argv = sys.argv[1:]
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
    out, skipped = {}, []

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
            # Before recording a reason ABOUT THE COUNTY, check whether the host
            # is answering everything with one document. See serves_one_document.
            if serves_one_document(home):
                reason = ("the county site answers every path with one document "
                          "(suspended or parked) -- not a page that stopped "
                          "naming districts")
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

    if not only and len(out) < MIN_COUNTIES:
        raise SystemExit(
            "only %d Plan 3 counties keyed (floor %d) -- that is a systemic "
            "break (the proximity rule, the roster read, or a blocked network), "
            "not a handful of counties reshaping their pages"
            % (len(out), MIN_COUNTIES))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
    print("wrote %s -- %d of %d Plan 3 counties keyed, %d skipped"
          % (OUT_FILE, len(out), len(targets), len(skipped)), file=sys.stderr)


if __name__ == "__main__":
    main()
