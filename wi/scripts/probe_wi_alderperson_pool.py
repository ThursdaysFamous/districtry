#!/usr/bin/env python3
"""
Ask every Wisconsin municipality that has aldermanic districts and no roster
whether it publishes one, and write the answer down.

WHY THIS EXISTS
----------------
`wi-alderpersons.json` names alderpersons in 31 of the 159 municipalities the
aldermanic layer draws. The other 128 get a card that names their district and
nobody in it, and that is this instance's largest reader-facing hole.

The 31 got there by taking cities one at a time, writing a parser for each. Nine
more sit in `wi_alderperson_scraper.py`'s queue comment with an address a sweep
scored. That leaves 119 municipalities nobody has measured AT ALL, and the order
they would be worked in is a guess about which of them publishes anything.

So the order changes to something that discriminates: WHETHER THE MUNICIPALITY
PUBLISHES A DISTRICT-KEYED ROSTER. That cannot be read off a list, so this file
measures it for all 128 at once, without writing a single parser, and prints
them ranked by what it found. It is Michigan's `probe_mi_county_boards.py`
shape, which exists for the same reason one level up.

NOTHING IS DISCOVERED, AND THAT IS THE FINDING WORTH HAVING
------------------------------------------------------------
This probe permutes no hostname and runs no search. Every address it reads comes
from `wi/data/app/wi-municipal-clerks.json`, which carries a `url` per
municipality on 545 of its 608 records -- the WEC clerk directory's own `web`
column, parsed and shipped since 2026-09-03. The nine addresses in the scraper's
queue comment were found by a sweep; the other 119 have had a published address
sitting in this repository the whole time.

That is the Schuyler lesson (`CLAUDE.md`: when a clerk domain does not resolve,
CHECK THE SCRAPERS) pointed the other way: before sweeping for an address, check
what the repository already ships.

THE JOIN IS ARITHMETIC AND THE RECORD SAID IT COULD NOT BE
-----------------------------------------------------------
The aldermanic layer is keyed by 5-digit COUSUBFP and the clerk roster by
7-digit Census place GEOID, and `build_wi_municipal_clerks.py` records that "the
two Census numbering systems are unrelated and each card can look up only the
key its own layer hands it".

That is TRUE OF TOWNS, which was what it measured: a town has no place record at
all, which is why its town half needed a second TIGERweb call keyed by cousub
GEOID. It is FALSE of cities and villages, which are coextensive MCDs carrying
one code in both layers. Measured 2026-09-29 over all 159 aldermanic
municipalities: `"55" + COUSUBFP` is a place GEOID in the clerk roster for 159
of 159, and the two sources name the same municipality on every one.

The arithmetic join also settles three cases a NAME join cannot -- Pewaukee,
Superior and Waukesha each have a city AND a village of the same name in the
same county, so a name match is ambiguous on exactly the three and the code
is not. `check_join()` re-derives that identity on every run and RAISES rather
than falling back to names, because a silent fallback is how the three would
come to be filed under each other.

WHAT IT RECORDS ABOUT ROBOTS
-----------------------------
robots.txt is read before the first page fetch of a host, as the client that
fetches, through the fleet's one reader (`scripts/robots_policy.py`). A record
is written for the host whose page is READ and for every host REJECTED, because
Michigan paid for the other arrangement: Gogebic and Marquette were recorded as
candidates on one day and found to disallow this client on the next, and the two
readings could not be compared because only one had been written down.

Each record carries the URL, the status, the allow/deny answer, the verdict's
own `why` (a byte count and the rule that decided, both of which move when a
file does) and the date it was READ -- per record, not taken from the artifact's
top-level `measured`, because `--only` writes one municipality into a file whose
other rows were read on another day.

A host that states a Crawl-delay gets a queue of its own through `HostPacer`, so
one slow host does not pace the other 127.

WHAT A VERDICT MEANS
---------------------
  candidate            a council page was read and it names people AND districts
  people-no-district   it names people and no district key is visible
  no-council-page      nothing on the site looked like a council or board page
  robots-refused       robots.txt disallows this client the path
  challenge            202, a managed challenge, or a WAF -- an access control,
                       never worked around
  unreachable          no answer, or an error
  no-url               WEC publishes no website for this municipality

`candidate` is NOT a promise that a parser will work; it is the claim that one is
worth writing. The verdict is deliberately coarse: this probe measures whether
to look, and looking is the tranche's job.

Usage:
    python3 wi/scripts/probe_wi_alderperson_pool.py            # sweep all
    python3 wi/scripts/probe_wi_alderperson_pool.py --only 05900
    python3 wi/scripts/probe_wi_alderperson_pool.py --limit 10
    python3 wi/scripts/probe_wi_alderperson_pool.py --check    # offline re-audit
    python3 wi/scripts/probe_wi_alderperson_pool.py --selftest  # offline, fixtures
"""

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from robots_policy import RobotsGate, HostPacer  # noqa: E402
from scraper_common import UA_ROSTER_BOT  # noqa: E402

APP = os.path.join(REPO_ROOT, "wi", "data", "app")
DISTRICTS = os.path.join(APP, "aldermanic-districts.json")
ROSTER = os.path.join(APP, "wi-alderpersons.json")
CLERKS = os.path.join(APP, "wi-municipal-clerks.json")
OUT = os.path.join(REPO_ROOT, "wi", "data", "source", "alderperson-pool.json")

# A council page's own address. Ranked: the more specific the path, the better,
# because a municipality's front page often NAMES its alderpersons in a sidebar
# while the page that lists them with their districts is one click in.
COUNCIL_PATH = re.compile(
    r"(common[-_ ]?council|city[-_ ]?council|village[-_ ]?board|"
    r"alder(?:person|man|men)|town[-_ ]?board|board[-_ ]?of[-_ ]?trustees|"
    r"elected[-_ ]?officials|mayor[-_ ]?and[-_ ]?council|your[-_ ]?government)",
    re.I)

# Text that says a page lists a body's members rather than its meeting agendas.
COUNCIL_TEXT = re.compile(
    r"(common council|city council|village board|alderperson|alderman|"
    r"alderwoman|board of trustees|village trustee|elected officials)", re.I)

# A district key on a members page. Wisconsin numbers aldermanic districts and
# some municipalities number by WARD instead (the Viroqua shape the scraper
# already records), so both count.
DISTRICT_KEY = re.compile(
    r"\b(?:district|aldermanic district|ward)s?\s*#?\s*\d+\b|"
    r"\b\d+(?:st|nd|rd|th)\s+(?:aldermanic\s+)?(?:district|ward)\b", re.I)

# Two capitalised words in a row, which is what a person's name looks like on a
# members page. Deliberately crude: this probe decides whether to LOOK.
NAME_SHAPE = re.compile(r"\b[A-Z][a-z]{1,20}\s+[A-Z][a-z']{1,20}\b")

# THIS VANTAGE FAILING TO REACH A HOST IS NOT THE HOST REFUSING US, and the
# first full sweep recorded two municipalities the wrong way round: Medford and
# Stoughton both read `robots-refused` on
# "ProxyError ... Tunnel connection failed: 502 Bad Gateway", which is this
# sandbox's egress and not one word from either city.
#
# `robots_policy` is RIGHT to answer disallow on an unreadable robots.txt -- RFC
# 9309 files a 5xx that way and it cannot tell a proxy failure from a host
# failure, so the FETCH correctly does not happen either way. What was wrong is
# what the artifact CLAIMED: a refusal attributed to a publisher who never made
# one. So the fetch is unchanged and the verdict is not.
PROXY_FAILURE = re.compile(
    r"(ProxyError|Tunnel connection failed|connect_rejected|"
    r"Unable to connect to proxy|ProxySchemeUnknown)", re.I)

CHALLENGE_SERVER = re.compile(r"(cloudflare|sucuri|incapsula|awselb)", re.I)
CHALLENGE_BODY = re.compile(
    r"(enable javascript and cookies|checking your browser|"
    r"just a moment|cf-browser-verification|please wait while we|"
    r"ddos protection by|<meta[^>]+http-equiv=[\"']?refresh)", re.I)

TAG = re.compile(r"<[^>]+>")
SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)


# --------------------------------------------------------------------------
# the pool
# --------------------------------------------------------------------------

def load_pool():
    """The municipalities with aldermanic districts and no roster, with the
    website their own clerk directory publishes."""
    feats = json.load(open(DISTRICTS))["features"]
    roster = json.load(open(ROSTER))
    clerks = json.load(open(CLERKS))

    muni = {}
    for f in feats:
        p = f["properties"]
        key = p["COUSUBFP"]
        muni.setdefault(key, {"cousubfp": key, "name": p.get("MCD_NAME"),
                              "ctv": p.get("CTV"), "districts": 0})
        muni[key]["districts"] += 1

    check_join(muni, clerks)

    pool = []
    for key, rec in sorted(muni.items()):
        if key in roster:
            continue
        clerk = clerks["55" + key]
        row = dict(rec, geoid="55" + key,
                   county=clerk.get("county"), url=clerk.get("url") or None)
        pool.append(row)
    pool.sort(key=lambda r: (-r["districts"], r["name"] or ""))
    return pool


def check_join(muni, clerks):
    """'55' + COUSUBFP is the municipality's place GEOID, for every one.

    RAISES rather than falling back to a name join. `build_wi_municipal_clerks`
    records that the two Census numbering systems are unrelated -- true of TOWNS,
    which have no place record, and false of cities and villages, which are
    coextensive MCDs carrying one code in both layers. A name join is ambiguous
    on exactly three (Pewaukee, Superior and Waukesha each have a city and a
    village of the same name in one county) and this one is not, so a silent
    fallback is how those three would come to be filed under each other.
    """
    bad = []
    for key, rec in sorted(muni.items()):
        clerk = clerks.get("55" + key)
        if clerk is None:
            bad.append("%s (%s): no clerk record at place GEOID 55%s"
                       % (rec["name"], key, key))
            continue
        if (clerk.get("municipality") or "").strip().upper() != (
                rec["name"] or "").strip().upper():
            bad.append("%s (%s): place GEOID 55%s names %r"
                       % (rec["name"], key, key, clerk.get("municipality")))
    if bad:
        raise RuntimeError(
            "the COUSUBFP-to-place-GEOID identity no longer holds on %d of %d "
            "municipalities, so this probe cannot say whose website it is "
            "reading:\n  %s" % (len(bad), len(muni), "\n  ".join(bad[:10])))
    return len(muni)


# --------------------------------------------------------------------------
# reading one municipality
# --------------------------------------------------------------------------

def robots_record(url, verdict, allowed):
    """What this client read at one host's robots.txt, in a form a later run can
    DIFF against. `status` alone cannot settle a disagreement between two runs;
    `why` carries the byte count and the rule that decided, both of which move
    when a file does. `read` is per record because --only writes one row into a
    file whose others were read on another day."""
    return {"url": url, "status": verdict.status, "allowed": bool(allowed),
            "why": (verdict.why or "")[:300], "read": time.strftime("%Y-%m-%d")}


def is_challenge(resp):
    """An access control, named rather than worked around."""
    if resp.status_code == 202:
        return "HTTP 202, which is never a document"
    if resp.headers.get("cf-mitigated"):
        return "Cloudflare managed challenge (cf-mitigated)"
    if resp.headers.get("X-Sucuri-ID") or CHALLENGE_SERVER.search(
            resp.headers.get("Server", "")):
        if CHALLENGE_BODY.search(resp.text[:4000]):
            return "challenge behind %r" % resp.headers.get("Server", "")[:40]
    if 300 <= resp.status_code < 400 and CHALLENGE_BODY.search(resp.text[:4000]):
        return "HTTP %d carrying a JavaScript challenge" % resp.status_code
    return None


def visible_text(html):
    """Roughly what a reader sees. A challenge page is short; a members page is
    not, which is why `probe_user_agents.py` judges by visible text rather than
    by searching for the word captcha -- that search reported sixteen real pages
    as challenges, one of them a 7.7 MB supervisor list."""
    return TAG.sub(" ", SCRIPT_STYLE.sub(" ", html or ""))


# A path segment that names the BODY, in descending order of how specifically.
# `your-government` is a section heading a whole CMS sits under; `city-council`
# is the body itself. Ranked, because the first draft ranked by path DEPTH and
# La Crosse's deepest matches were Refuse-Recycling, Treasurer, Parks-Recreation
# and Fire -- department pages under a /Your-Government/ section -- while the
# council page it never reached was two segments up.
BODY_SEGMENT = [
    (re.compile(r"alder(person|man|men|women)", re.I), 6),
    (re.compile(r"(common|city|village|town)[-_ ]?council", re.I), 5),
    (re.compile(r"(village|town)[-_ ]?board|board[-_ ]?of[-_ ]?trustees", re.I), 5),
    (re.compile(r"council[-_ ]?members?|board[-_ ]?members?", re.I), 5),
    (re.compile(r"elected[-_ ]?officials", re.I), 4),
    (re.compile(r"mayor[-_ ]?and[-_ ]?council", re.I), 4),
    (re.compile(r"\bcouncil\b|\btrustees?\b", re.I), 3),
    (re.compile(r"your[-_ ]?government|government", re.I), 1),
]

# A link to a FILE, not a page. Beaver Dam's front page links
# /DocumentCenter/View/377/Aldermanic-District-Map, which matches every council
# pattern and is a PDF: the first draft fetched it, ran an HTML classifier over
# 281 KB of binary and recorded the city as publishing no council page.
DOCUMENT_PATH = re.compile(
    r"(/documentcenter/|/document/|\.pdf$|\.docx?$|\.xlsx?$|\.csv$)", re.I)


def link_rank(url):
    """How specifically does this url name the governing body? 0 = not at all.

    Scored on the LAST path segment first and the whole path second, so a
    members page under /city-council/ outranks a department page under
    /your-government/.
    """
    path = urllib.parse.urlparse(url).path
    if DOCUMENT_PATH.search(path):
        return 0
    segs = [x for x in path.split("/") if x]
    last = segs[-1] if segs else ""
    best = 0
    for pat, weight in BODY_SEGMENT:
        if pat.search(last):
            best = max(best, weight * 2)      # the page's own name counts double
        elif pat.search(path):
            best = max(best, weight)
    return best


def council_links(root, html):
    """Links on a front page that look like the body's own members page."""
    out = {}
    for m in re.finditer(r'href=["\']([^"\'#]+)', html or ""):
        href = m.group(1).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        full = urllib.parse.urljoin(root, href)
        if urllib.parse.urlparse(full).netloc != urllib.parse.urlparse(root).netloc:
            continue
        if not COUNCIL_PATH.search(urllib.parse.urlparse(full).path):
            continue
        clean = full.split("?")[0]
        rank = link_rank(clean)
        if rank:
            out[clean] = rank
    return [u for u, _ in sorted(out.items(), key=lambda kv: (-kv[1], len(kv[0])))][:6]


def classify(html, chrome=None):
    """Does this page name people, and does it key them to districts?

    `chrome` is the name shapes the site's FRONT page shows, subtracted here.
    Without that subtraction a nav-heavy CMS reads as a roster: Watertown's
    /page/alderpersons-and-judge and /page/elected-officials each scored 234 name
    shapes and they are THE SAME 234, because both pages' served HTML is the site
    menu and nothing else. Measured 2026-09-29, that page is 5,949 visible
    characters and La Crosse's City-Council page 3,911, neither containing one
    alderperson: both platforms render the roster client-side, so a static fetch
    sees the chrome. `own_names` is what separates a roster from a menu.
    """
    text = visible_text(html)
    names = set(NAME_SHAPE.findall(text))
    keys = len(set(k.lower() for k in DISTRICT_KEY.findall(text)))
    own = names - set(chrome or ())
    return {"visible_chars": len(text), "name_shapes": len(names),
            "own_names": len(own), "district_keys": keys,
            "reads_as_council": bool(COUNCIL_TEXT.search(text))}


def verdict_for(ev):
    """What was learned, decided by WHERE the refusal happened.

    A refusal, challenge or error ON THE ROOT is decisive: nothing was read, so
    nothing can be said about what the municipality publishes. The SAME answer on
    one sub-page is not, and the first draft of this function treated them alike:
    La Crosse's front page answered 200 with 114 KB, six council links were found
    on it, one of those links 403'd, and the municipality was recorded
    `unreachable` — a host that had just served this client a page. A verdict must
    describe the whole read, not the last thing that went wrong in it.

    `challenge` and `robots-refused` are separated for the same reason they are
    separated everywhere else in this fleet: a `Disallow: /` is a policy the
    publisher stated, and an HTTP 202 in front of robots.txt is an access control
    with no policy behind it. Antigo is the second and was reported as the first.
    """
    # FIRST, because a vantage failure can look like any of the others: a
    # tunnel that never opened is recorded as neither a refusal nor an absence.
    for k in ("root_robots_refused", "root_error", "root_challenge"):
        if ev.get(k) and PROXY_FAILURE.search(str(ev[k])):
            return "proxy-blocked"
    if ev.get("root_challenge"):
        return "challenge"
    if ev.get("root_robots_refused"):
        return "robots-refused"
    if ev.get("root_error"):
        return "unreachable"
    if not ev.get("pages"):
        return "no-council-page"
    best = max(ev["pages"],
               key=lambda p: (p["district_keys"], p.get("own_names", 0)))
    if best["district_keys"] >= 2 and best.get("own_names", 0) >= 2:
        return "candidate"
    # A department page on a nav-heavy CMS reads as council (its chrome names
    # the council) and shows 130-190 two-capitalised-word shapes that are menu
    # items. So the page's own PATH has to name the body, which is the one
    # signal navigation chrome cannot fake.
    if best.get("own_names", 0) >= 3 and best["reads_as_council"] \
            and best.get("rank", 0) >= 6:
        return "people-no-district"
    # A page that NAMES the body, answered 200, and carries nothing its own
    # front page does not: the roster is rendered client-side, or it is behind
    # another click. That is a different fact from "this municipality publishes
    # no council page", and it is the one a tranche needs -- it says the page
    # exists and a static fetch cannot read it.
    if best.get("rank", 0) >= 6 and best["district_keys"] == 0 \
            and best.get("own_names", 0) <= 1:
        return "roster-not-in-html"
    return "no-council-page"


def probe_one(row, session_factory):
    import requests

    out = dict(row, verdict="no-url", robots=[], pages=[], notes=[])
    if not row.get("url"):
        out["notes"].append("the clerk directory publishes no website")
        return out

    session = session_factory()
    gate = RobotsGate(session, UA_ROSTER_BOT)
    pacer = HostPacer(gate)
    root = row["url"] if row["url"].startswith("http") else "https://" + row["url"]
    ev = {"pages": []}

    def get(url, is_root=False):
        """robots FIRST, every time, as the client that fetches.

        `is_root` is what separates "this municipality could not be read" from
        "one of its pages could not be" — see verdict_for.
        """
        def note(kind, detail):
            ev.setdefault(kind if is_root else "page_" + kind, detail)
            if not is_root:
                out["notes"].append("%s at %s: %s" % (kind, url, detail))

        try:
            ok, why = gate.allows(url)
            v = gate.verdict(url)
        except Exception as exc:                       # noqa: BLE001
            out["notes"].append("robots read failed for %s: %s" % (url, exc))
            return None
        out["robots"].append(robots_record(url, v, ok))
        if not ok:
            # robots.txt behind an access control is a CHALLENGE, not a policy:
            # nobody at the municipality stated it. The fetch still stops.
            if v.status == "challenge":
                note("root_challenge", why)
            else:
                note("root_robots_refused", why)
            return None
        try:
            with pacer.hold(url):
                r = session.get(url, timeout=30, allow_redirects=True)
        except Exception as exc:                       # noqa: BLE001
            note("root_error", str(exc)[:200])
            return None
        ch = is_challenge(r)
        if ch:
            note("root_challenge", ch)
            return None
        if r.status_code >= 400:
            note("root_error", "HTTP %d" % r.status_code)
            return None
        ctype = (r.headers.get("Content-Type") or "").lower()
        if ctype and "html" not in ctype and "xml" not in ctype:
            # a PDF's bytes through an HTML classifier answer confidently and
            # wrongly -- Beaver Dam's district map scored 281 KB and one name
            out["notes"].append("not html at %s: %s" % (url, ctype[:60]))
            return None
        return r

    home = get(root, is_root=True)
    if home is not None:
        out["final_url"] = home.url
        chrome = set(NAME_SHAPE.findall(visible_text(home.text)))
        for link in council_links(home.url, home.text):
            page = get(link)
            if page is None:
                continue
            rec = classify(page.text, chrome)
            rec["url"] = page.url
            rec["rank"] = link_rank(page.url)
            ev["pages"].append(rec)
            if rec["district_keys"] >= 2 and rec["own_names"] >= 2:
                break
        if not ev["pages"]:
            # the front page itself may be the members page on a small village
            rec = classify(home.text)   # no chrome to subtract from itself
            rec["url"] = home.url
            rec["rank"] = link_rank(home.url)
            if rec["reads_as_council"]:
                ev["pages"].append(rec)

    for k, field in (("root_robots_refused", "robotsRefused"),
                     ("root_challenge", "challenge"),
                     ("root_error", "error"),
                     ("page_root_error", "pageError"),
                     ("page_root_challenge", "pageChallenge"),
                     ("page_root_robots_refused", "pageRobotsRefused")):
        if ev.get(k):
            out[field] = ev[k]
    out["pages"] = ev["pages"]
    out["verdict"] = verdict_for(ev)
    return out


# --------------------------------------------------------------------------
# sweep, report, check
# --------------------------------------------------------------------------

def session_factory():
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = UA_ROSTER_BOT
    s.headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
    return s


def sweep(pool, workers=6):
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool_ex:
        futures = {pool_ex.submit(probe_one, r, session_factory): r for r in pool}
        for fut in concurrent.futures.as_completed(futures):
            row = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:                   # noqa: BLE001
                rows.append(dict(row, verdict="unreachable",
                                 error="probe raised: %s" % str(exc)[:200],
                                 robots=[], pages=[], notes=[]))
            print("  %-22s %-18s %d districts"
                  % (rows[-1]["name"], rows[-1]["verdict"],
                     rows[-1]["districts"]), file=sys.stderr)
    rows.sort(key=lambda r: (-r["districts"], r["name"] or ""))
    return rows


ORDER = ["candidate", "people-no-district", "roster-not-in-html",
         "no-council-page", "challenge", "robots-refused", "unreachable",
         "proxy-blocked", "no-url"]


def report(rows):
    import collections
    by = collections.Counter(r["verdict"] for r in rows)
    seats = collections.Counter()
    for r in rows:
        seats[r["verdict"]] += r["districts"]
    print("\n%d municipalities, %d districts between them"
          % (len(rows), sum(r["districts"] for r in rows)))
    for v in ORDER:
        if by[v]:
            print("  %-20s %3d municipalities, %4d districts"
                  % (v, by[v], seats[v]))
    if by["proxy-blocked"]:
        print("\n  %d municipality/-ies could not be reached from THIS vantage "
              "(the proxy, not the site) and are unmeasured, not refused:\n    %s"
              % (by["proxy-blocked"],
                 ", ".join(sorted(r["name"] for r in rows
                                  if r["verdict"] == "proxy-blocked"))))
    print("\nCandidates, largest first:")
    for r in rows:
        if r["verdict"] != "candidate":
            continue
        best = max(r["pages"], key=lambda p: (p["district_keys"], p["name_shapes"]))
        print("  %-24s %2d districts  %s" % (r["name"], r["districts"], best["url"]))


def check(rows):
    """Offline re-audit: every row still describes the tree.

    A municipality that has since gained a roster, or lost its districts, is an
    ORPHAN -- the `ACCEPTED_DROPS` property, so the artifact cannot go on
    describing a pool that has moved under it.
    """
    roster = json.load(open(ROSTER))
    feats = json.load(open(DISTRICTS))["features"]
    live = {f["properties"]["COUSUBFP"] for f in feats}
    problems = []
    for r in rows:
        if r["cousubfp"] in roster:
            problems.append("%s (%s) now has a roster — retire its row"
                            % (r["name"], r["cousubfp"]))
        if r["cousubfp"] not in live:
            problems.append("%s (%s) no longer has aldermanic districts"
                            % (r["name"], r["cousubfp"]))
        if r["verdict"] not in ORDER:
            problems.append("%s: unknown verdict %r" % (r["name"], r["verdict"]))
    blocked = [r["name"] for r in rows if r["verdict"] == "proxy-blocked"]
    if blocked:
        # NOT a failure: a note, printed every run, because these rows say
        # nothing about the municipality and must be re-measured from a vantage
        # that can reach them (a CI runner) before any tranche reads them.
        print("  NOTE %d row(s) are proxy-blocked and say nothing about the "
              "municipality — re-measure from CI: %s"
              % (len(blocked), ", ".join(sorted(blocked))))
    missing = live - roster.keys() - {r["cousubfp"] for r in rows}
    for k in sorted(missing):
        problems.append("COUSUBFP %s has districts, no roster and no row" % k)
    return problems


def _selftest():
    fails = []
    ran = []

    def ck(name, cond, extra=""):
        # COUNTED, never stated: a hand-written total is one edit from being
        # wrong about its own file, which is the defect this repository keeps
        # finding in its own prose.
        ran.append(name)
        print(("  ok   " if cond else "  FAIL ") + name + (" — " + extra if extra else ""))
        if not cond:
            fails.append(name)

    ck("a members page with districts and names reads as a candidate",
       verdict_for({"pages": [{"district_keys": 8, "own_names": 8,
                               "reads_as_council": True, "rank": 10}]}) == "candidate")
    ck("names with no district key, on a page that names the body, is "
       "people-no-district",
       verdict_for({"pages": [{"district_keys": 0, "own_names": 6,
                               "reads_as_council": True, "rank": 10}]})
       == "people-no-district")
    ck("the same counts on a DEPARTMENT page are navigation chrome, not a roster",
       verdict_for({"pages": [{"district_keys": 0, "own_names": 0, "name_shapes": 188,
                               "reads_as_council": True, "rank": 1}]})
       == "no-council-page")
    ck("a challenge on the root is never read as an absence",
       verdict_for({"root_challenge": "HTTP 202", "pages": []}) == "challenge")
    ck("a robots refusal on the root outranks an empty page set",
       verdict_for({"root_robots_refused": "Disallow: /", "pages": []})
       == "robots-refused")
    ck("no pages at all is no-council-page",
       verdict_for({"pages": []}) == "no-council-page")
    # Medford and Stoughton, measured on the first full sweep: both read
    # `robots-refused` on a proxy tunnel that never opened, which attributes a
    # refusal to a publisher who never made one.
    ck("a proxy tunnel that never opened is not the city refusing us",
       verdict_for({"root_robots_refused": "robots.txt unreachable: ProxyError: "
                    "Tunnel connection failed: 502 Bad Gateway", "pages": []})
       == "proxy-blocked")
    ck("nor is it the city being unreachable",
       verdict_for({"root_error": "ProxyError('Unable to connect to proxy')",
                    "pages": []}) == "proxy-blocked")
    ck("a REAL robots refusal is still a refusal",
       verdict_for({"root_robots_refused":
                    "robots.txt served (210 bytes): Disallow: / is the longest "
                    "match for /", "pages": []}) == "robots-refused")
    ck("a real HTTP 403 from the site is still unreachable",
       verdict_for({"root_error": "HTTP 403", "pages": []}) == "unreachable")
    # Watertown, measured: /page/alderpersons-and-judge answered 200 and its
    # 234 name shapes are the SAME 234 its front page shows -- the site menu.
    ck("a council page carrying only its own site menu is roster-not-in-html",
       verdict_for({"pages": [{"district_keys": 0, "own_names": 0,
                               "name_shapes": 234, "reads_as_council": True,
                               "rank": 12}]}) == "roster-not-in-html")
    ck("chrome is subtracted, so a menu shared with the front page is not a roster",
       classify("<p>Jane Doe John Roe</p>",
                chrome={"Jane Doe", "John Roe"})["own_names"] == 0)
    ck("a name the council page alone carries is its own",
       classify("<p>Jane Doe Ann Smith</p>", chrome={"Jane Doe"})["own_names"] == 1)
    # the La Crosse defect: its front page served 114 KB and one council link
    # 403'd, and the first draft called the whole municipality unreachable
    ck("a sub-page error does not make a readable municipality unreachable",
       verdict_for({"page_root_error": "HTTP 403",
                    "pages": [{"district_keys": 6, "own_names": 9,
                               "reads_as_council": True, "rank": 10}]})
       == "candidate")
    ck("a sub-page error with nothing read is still no-council-page",
       verdict_for({"page_root_error": "HTTP 403", "pages": []})
       == "no-council-page")
    # Antigo: robots.txt itself answered 202, which nobody at the city stated
    ck("a challenge in front of robots.txt is not a stated policy",
       verdict_for({"root_challenge": "robots.txt answered HTTP 202",
                    "pages": []}) == "challenge")

    ck("a district key is found in prose",
       len(DISTRICT_KEY.findall("Alderperson, District 3 and District 4")) == 2)
    ck("an ordinal district is found too",
       bool(DISTRICT_KEY.search("Representing the 5th Aldermanic District")))
    ck("a ward key counts, because some municipalities number by ward",
       bool(DISTRICT_KEY.search("Trustee, Ward 2")))
    ck("a name shape needs two capitalised words",
       NAME_SHAPE.findall("Kevin Schmidt") == ["Kevin Schmidt"])

    ck("a council link is ranked above the front page",
       council_links("https://x.org/", '<a href="/government/common-council/members">m</a>')
       == ["https://x.org/government/common-council/members"])
    # the La Crosse defect: ranking by path DEPTH put four department pages
    # under /Your-Government/ ahead of the council page two segments up
    ck("the council page outranks a deeper department page",
       council_links("https://x.org/",
                     '<a href="/Your-Government/Departments/Refuse/Collection">r</a>'
                     '<a href="/Your-Government/City-Council">c</a>')[0]
       == "https://x.org/Your-Government/City-Council")
    # the Beaver Dam defect: a PDF matched every council pattern and was fetched
    ck("a DocumentCenter file is not a council page",
       council_links("https://x.org/",
                     '<a href="/DocumentCenter/View/377/Aldermanic-District-Map">m</a>')
       == [])
    ck("a .pdf is not a council page",
       link_rank("https://x.org/city-council/members.pdf") == 0)
    ck("a page naming the body outranks one merely under /government/",
       link_rank("https://x.org/gov/city-council")
       > link_rank("https://x.org/your-government/departments/fire"))
    ck("an off-site link is never followed",
       council_links("https://x.org/", '<a href="https://y.org/city-council">c</a>') == [])
    ck("a mailto is not a page",
       council_links("https://x.org/", '<a href="mailto:a@x.org">mail</a>') == [])

    ck("script text is not visible text",
       "hidden" not in visible_text("<script>var a='hidden'</script><p>shown</p>"))

    # the join identity, on the shipped files
    try:
        n = check_join({f["properties"]["COUSUBFP"]:
                        {"name": f["properties"].get("MCD_NAME")}
                        for f in json.load(open(DISTRICTS))["features"]},
                       json.load(open(CLERKS)))
        ck("'55' + COUSUBFP names the same municipality on every one", True,
           "%d municipalities" % n)
    except RuntimeError as exc:
        ck("'55' + COUSUBFP names the same municipality on every one", False,
           str(exc)[:160])

    print("\n%s — %d assertion(s), %d failure(s)"
          % ("FAIL" if fails else "OK", len(ran), len(fails)))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--only", action="append", help="a COUSUBFP; repeatable")
    ap.add_argument("--limit", type=int, help="probe the N largest only")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--check", action="store_true",
                    help="offline: re-audit the artifact against the tree")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if args.check:
        if not os.path.exists(OUT):
            print("probe-wi-alderperson-pool: no %s yet — nothing to check"
                  % os.path.relpath(OUT, REPO_ROOT))
            return 0
        rows = json.load(open(OUT))["municipalities"]
        problems = check(rows)
        for p in problems:
            print("  FAIL " + p)
        print("probe-wi-alderperson-pool: %s — %d row(s)"
              % ("FAIL" if problems else "OK", len(rows)))
        return 1 if problems else 0

    pool = load_pool()
    if args.only:
        pool = [r for r in pool if r["cousubfp"] in set(args.only)]
    if args.limit:
        pool = pool[:args.limit]
    print("probing %d municipality/-ies (%d districts), %d with no published url"
          % (len(pool), sum(r["districts"] for r in pool),
             sum(1 for r in pool if not r.get("url"))), file=sys.stderr)

    rows = sweep(pool, args.workers)

    if args.only or args.limit:
        existing = {}
        if os.path.exists(OUT):
            existing = {r["cousubfp"]: r
                        for r in json.load(open(OUT))["municipalities"]}
        for r in rows:
            existing[r["cousubfp"]] = r
        rows = sorted(existing.values(),
                      key=lambda r: (-r["districts"], r["name"] or ""))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({
            "_comment": "Which Wisconsin municipalities with aldermanic "
                        "districts publish a district-keyed roster. Written by "
                        "wi/scripts/probe_wi_alderperson_pool.py; every address "
                        "comes from wi-municipal-clerks.json's own url field, "
                        "nothing is discovered, and each row's robots records "
                        "carry the date THEY were read.",
            "measured": time.strftime("%Y-%m-%d"),
            "userAgent": UA_ROSTER_BOT,
            "municipalities": rows,
        }, f, indent=1, sort_keys=True)
        f.write("\n")
    report(rows)
    print("\nwrote %s" % os.path.relpath(OUT, REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
