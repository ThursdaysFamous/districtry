#!/usr/bin/env python3
"""
Ask every Michigan county that has no commissioner roster yet whether it
publishes one, and write the answer down.

WHY THIS EXISTS
----------------
mi-commissioner-members.json names commissioners in 16 of Michigan's 83
counties. Three tranches got there by taking the next six counties BY
POPULATION, writing a parser for each, and recording the ones that refused in
mi_commissioner_scraper.py's PROBES table. That order has stopped doing any
work: tranche 1 spanned 1.79M to 175K, tranche 3 only 109K to 83K, and the 59
counties still untried hold 1,824,640 people between them -- 18.1% of
Michigan's 10,077,331 (Census 2020), where each county buys under 1%.

So the order changes to something that still discriminates: WHETHER THE COUNTY
PUBLISHES A DISTRICT-KEYED ROSTER AT ALL. That cannot be read off a list, so
this file measures it for all 59 at once, without writing a single parser, and
prints them ranked by what it found.

WHAT IT RECORDS ABOUT ROBOTS, AND WHY (closed 2026-09-19)
----------------------------------------------------------
Until this date it wrote a robots status for every host it REJECTED and none
for the host it ACCEPTED. Tranche 5 found Gogebic and Marquette serving a
robots.txt that disallows this client, one day after this probe recorded both
as `candidate` having read robots first, and the two readings could not be
compared because only one of them was written down. The Internet Archive holds
no snapshot of either host's robots.txt since 2026-09-01, so whether those
files changed is not established and never will be — that pair is lost, and
closing this only stops the next one.

Every county row now carries `robots`, with a record for the accepted `host`
and one for the accepted `board` page, each holding the URL, the status, the
allow/deny answer, the verdict's own `why` and the date it was READ. Rejected
hosts carry the same record beside their existing reason.

TWO THINGS MAKE IT DIFFABLE RATHER THAN DECORATIVE. The `why` is kept because
the STATUS ALONE CANNOT SETTLE A DISAGREEMENT: both of the contradictory
Gogebic readings would have said `served`, while robots_policy builds `why` as
"robots.txt served (N bytes): <the rule that decided>" — a byte count and a
rule, both of which move when a file does. And the date is per RECORD rather
than taken from the artifact's top-level `measured`, because `--county` and
`--limit` write one county into a file whose other rows were read on another
day.

THE HOST AND THE BOARD PAGE ARE SEPARATE READINGS on purpose: one file can
allow `/` and disallow the path a board page sits under, so a single answer per
county would be true of one URL and asserted of another.

`--refresh-robots` fills the field for the counties already recorded, reading
robots.txt and no page: 33 readings across the 25 counties on 2026-09-19, which
cost 24 FETCHES, because RobotsGate reads each host's file once and nine of the
ten board pages sit on the host already read. It is unpaced by construction and
that is not an oversight: the gate fetches robots.txt on its own session, and a
Crawl-delay stated inside a file cannot govern the fetch that reads it.

THE FIRST FILL ALREADY FOUND TWO COUNTIES WHOSE RECORDED REASON IS NO LONGER
THE ONE THAT GOVERNS, which is what the field is for.

  IOSCO   www.iosco.org now answers HTTP 403 on robots.txt, which the strict
          reading this file takes for a county WEBSITE makes a refusal. Its
          record says `no-board-page`, and the 2026-09-18 sweep could only
          have reached that verdict by being ALLOWED, so the policy has moved
          since. Read three times on both host spellings, identical each time,
          and the 403 carries `server: cloudflare` and the site's own
          `cf-ray` — it is the host refusing this client and not this
          sandbox's egress proxy, which answered 200 to the CONNECT.
  TUSCOLA tuscolacounty.com serves a 26-byte robots.txt that disallows this
          client. Its record says `challenge`, which came from its OTHER host,
          so the recorded reason was true and incomplete.

Neither is a re-probe and neither changes a verdict here: a robots reading and
a roster verdict are different questions, and the refresh deliberately touches
no verdict, evidence, score or board_url. What it changes is what a
re-examination of the 25 should expect — two of them are shut by policy, not
by an absent page.

WHAT A VERDICT MEANS, AND WHAT IT DOES NOT
-------------------------------------------
The strongest verdict here is `candidate`, and it means A PARSER IS WORTH
WRITING -- never that the county will ship. Washtenaw is the standing
counter-example and it is already in PROBES: its page carries District 1-9 and
names all nine commissioners, and it still ships nothing, because the names sit
in free prose in seven different sentence shapes with no name field, and
District 8's bio does not begin with the name at all. A probe that called that
`candidate` would be right. Only a parser settles a county.

So every verdict carries its EVIDENCE -- how many district tokens, how many
name-shaped strings, how many mailto and tel links -- and the ranking is by
evidence rather than by a yes. A county with nine districts and nine mailto
links is a better bet than one with nine districts and none; both are
`candidate` and neither is a promise.

HOW A HOST IS FOUND
--------------------
Michigan has no reachable statewide directory of county websites. The state's
own michigan.gov answers HTTP 403 on robots.txt, which is a refusal under the
strict reading county websites take here; micounties.org answers HTTP 202 on
robots.txt, which is a challenge and an access control; and Wikidata's SPARQL
endpoint and /w/ API are both disallowed in its robots.txt. All three were
measured 2026-09-15 and none was worked around.

What is left is permutation over candidate host names, and the honest way to
use it is to GATE IT ON COUNTIES WHOSE ANSWER IS ALREADY KNOWN. The generator
below is held to the 24 counties already measured -- the 16 that ship and the
8 in PROBES -- and finds the real host for 24 of 24. check_generator() runs
that gate on every invocation and refuses to sweep if it ever stops finding
them all.

THE LIMIT OF THAT GATE IS STATED RATHER THAN IMPLIED. The form list was
derived FROM those 24 hosts, so 24 of 24 proves the generator covers every
form Michigan counties have been OBSERVED to use -- not that it finds a form
nobody has used yet. `no-host` therefore means "not found by these candidates",
which is a fact about this sweep and never about the county. Bare three-letter
stems were dropped after measurement: cli.com, van.org, mar.us and luc.net all
resolve, none to a county, and dropping them cut the candidate set from 182 per
county to about 61 while still finding all 24.

THE CATCH-ALL TRAP, WHICH THIS SWEEP WOULD OTHERWISE WALK INTO
---------------------------------------------------------------
Tranche 3 found lapeercountyweb.org: it resolves, answers HTTP 200, and is a
different organisation whose site is a CATCH-ALL -- its root, its /government
path and a deliberately nonexistent path all return the same 175,315 bytes with
the same md5. A sweep that took "resolves and answers 200" as proof of a
county's website would have recorded that host for Lapeer and then parsed
somebody else's page.

So every resolving host is asked for a path that CANNOT exist before it is
believed, and a host that answers that path with a real body is recorded
`catch-all` and dropped. A host is only accepted as the county's when its own
front page names the county.

THE CLIENT
-----------
UA_ROSTER_BOT, the districtry token, exactly as mi_commissioner_scraper.py
sends it -- no browser string anywhere in this file. Every host's robots.txt is
read through scripts/robots_policy.py (via the robots_gate shim) BEFORE its
first page fetch, with the STRICT reading of a 401/403 that county websites take
(refused_is_refusal=True): on a website that status is a firewall refusing this
client, and fetching anyway is walking past a no. A stated Crawl-delay is
honoured PER HOST by HostPacer, so one slow county does not pace the other 58.

DNS resolution is not a fetch and asks nobody's robots.txt; stage 1 resolves
names and stops. Nothing is fetched from a host until its file has been read.

USAGE
------
    python3 mi/scripts/probe_mi_county_boards.py            # sweep, write artifact
    python3 mi/scripts/probe_mi_county_boards.py --check    # offline re-audit
    python3 mi/scripts/probe_mi_county_boards.py --county Marquette
"""
import argparse
import json
import os
import re
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robots_gate import RobotsGate, HostPacer                      # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The fleet's own roster token (scripts/scraper_common.py's UA_ROSTER_BOT).
# Copied rather than imported, the same way mi_commissioner_scraper.py,
# mi_detroit_council_scraper.py, wi/scripts/wi_wec_probe.py and
# ia/scripts/ia_supervisor_district_scraper.py each carry their own copy with
# this note: instance scripts resolve imports inside their own tree, and
# scripts/validate_workflow_deps.py fails a sys.path reach across trees.
# robots_gate.py is the one sanctioned exception, because that gate lists
# robots_policy in FLEET_SHARED.
#
# THIS FILE DID REACH ACROSS, from the day it was written until 2026-09-19, and
# nothing caught it: the gate only reads the scripts a WORKFLOW runs, and no
# workflow ran this one. Wiring `--check` into smoke-test.yml is what asked the
# question. A rule enforced only where a gate happens to look is a rule three
# files were keeping by hand.
UA_ROSTER_BOT = "districtry.com roster bot (civic data; contact via site)"

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
DISTRICTS = os.path.join(INSTANCE, "data", "app", "mi-commissioner-districts.json")
ROSTER = os.path.join(INSTANCE, "data", "app", "mi-commissioner-members.json")
SCRAPER = os.path.join(HERE, "mi_commissioner_scraper.py")
ARTIFACT = os.path.join(INSTANCE, "data", "source", "mi-county-board-probe.json")

TIMEOUT = 25
DNS_WORKERS = 32
HOST_WORKERS = 6

# The 24 counties whose real host is already known: the 16 that ship a roster
# and the 8 recorded in PROBES. check_generator() holds the candidate
# generator to these on every run.
KNOWN_HOSTS = {
    "Kalamazoo": "www.kalcounty.gov",      "Kent": "www.kentcountymi.gov",
    "Macomb": "bocmacomb.org",             "Muskegon": "co.muskegon.mi.us",
    "Saginaw": "www.saginawcountymi.gov",  "Wayne": "www.waynecountymi.gov",
    "Berrien": "www.berriencounty.org",    "Calhoun": "www.calhouncountymi.gov",
    "Jackson": "www.mijackson.org",        "Monroe": "www.co.monroe.mi.us",
    "St. Clair": "www.stclaircounty.org",  "Eaton": "www.eatoncounty.org",
    "Grand Traverse": "www.gtcountymi.gov", "Lapeer": "lapeercountymi.gov",
    "Lenawee": "www.lenawee.mi.us",        "Midland": "midlandcountymi.gov",
    "Oakland": "www.oakgov.com",           "Genesee": "www.geneseecountymi.gov",
    "Ingham": "www.ingham.org",            "Ottawa": "www.miottawa.org",
    "Livingston": "www.livgov.com",        "Allegan": "www.allegancounty.org",
    "Bay": "www.baycountymi.gov",          "Washtenaw": "www.washtenaw.org",
}

# Stem -> the TLDs that stem is ever OBSERVED with across those 24. Bare
# three-letter stems are deliberately absent; see the module docstring.
def _forms(name):
    flat = re.sub(r"[^a-z]", "", name.lower())
    words = [w for w in re.split(r"[^a-z]+", name.lower()) if w]
    ab = flat[:3]
    ini = "".join(w[0] for w in words) if len(words) > 1 else None
    spec = [
        (flat,               (".org", ".gov", ".mi.us")),
        (flat + "county",    (".org", ".gov", ".com", ".net", ".us")),
        (flat + "countymi",  (".gov", ".org", ".com")),
        # HYPHENATED AND SHORT-SUFFIX FORMS. The first sweep recorded Clinton
        # as `no-board-page`; its real site is clinton-county.org and its board
        # page is /413/Board-of-Commissioners with all 7 districts. The
        # generator simply had no hyphenated form, so the county was written
        # down as publishing nothing when it publishes a full board -- the
        # exact failure this file's docstring warns `no-host` can be. Measured
        # 2026-09-15 by re-probing the 23 counties that did not yield: 14 had a
        # form the generator never tried.
        (flat + "-county",   (".org", ".gov", ".com", ".net", ".us")),
        ("county-of-" + flat, (".org", ".com")),
        (flat + "co",        (".org", ".gov", ".com", ".net", ".us")),
        ("co" + flat,        (".org", ".gov", ".mi.us", ".com")),
        ("mi" + flat,        (".org", ".gov", ".com")),
        ("boc" + flat,       (".org", ".com")),
        (ab + "gov",         (".com", ".org", ".gov")),
        (ab + "county",      (".gov", ".org", ".com")),
        (ab + "countymi",    (".gov",)),
    ]
    if ini:
        spec += [(ini + "county", (".gov", ".org")), (ini + "countymi", (".gov", ".org")),
                 (ini + "gov", (".com", ".org")), (ini, (".org", ".gov"))]
    out = set()
    for stem, tlds in spec:
        for tld in tlds:
            for pre in ("www.", ""):
                out.add(pre + stem + tld)
    for pre in ("www.", ""):
        out.add(pre + "co." + flat + ".mi.us")
    return sorted(out)


def check_generator():
    """Refuse to sweep if the generator stops finding the 24 known hosts."""
    missed = [(c, h) for c, h in KNOWN_HOSTS.items() if h not in set(_forms(c))]
    if missed:
        raise SystemExit(
            "probe-mi-county-boards: FAIL — the candidate generator no longer "
            "finds %d of %d known hosts (%s). Widen _forms() before sweeping; a "
            "`no-host` verdict from a generator that cannot find the counties we "
            "already have is not a measurement."
            % (len(missed), len(KNOWN_HOSTS),
               ", ".join("%s=%s" % m for m in missed)))
    return len(KNOWN_HOSTS)


# ---------------------------------------------------------------- the frontier

def probes_fips(src):
    """The county FIPS in mi_commissioner_scraper.py's PROBES table, read from
    that table's own span and COUNT-CHECKED.

    THE PREVIOUS READER DEPENDED ON KEY ORDER IN A HAND-WRITTEN LITERAL, and
    got the right answer only because the two tables in that one file disagree
    about it. Measured 2026-09-21: all 48 COUNTIES entries are written "fips"
    first, all 10 PROBES entries "county" first, and the reader was a regex
    over the WHOLE source requiring county-then-fips. So it matched PROBES
    exactly and COUNTIES not at all -- correct, and by coincidence, with the
    order it needed in the minority style.

    Writing one PROBES entry the way every COUNTIES entry in the same file is
    written -- a semantically identical reorder of two keys -- dropped that
    county out of the set, put it in the frontier, and made --check FAIL with
    "re-run the sweep". Proven on Gogebic, whose robots.txt disallows this
    client: the gate's own advice would have been a fetch we may not make.
    Four of the ten PROBES counties disallow us that way.

    The table is not imported, deliberately: mi_commissioner_scraper.py pulls
    requests and robots_gate at module scope, and this probe's workflow
    declares neither. So the span is located by name, either key order is
    accepted, and the parse must account for every entry in it -- the three
    per-entry keys have to agree on the count and the FIPS have to be
    distinct. A reader that can quietly return a short set is the defect; a
    looser regex alone would leave it.
    """
    start = src.index("\nPROBES = (")
    blk = src[start:src.index("\n)", start)]
    fips = re.findall(r'"fips":\s*"(\d{3})"', blk)
    tally = {k: len(re.findall(r'"%s":' % k, blk)) for k in ("fips", "county", "seats")}
    if len(set(tally.values())) != 1 or len(fips) != len(set(fips)) or not fips:
        raise SystemExit(
            "probe-mi-county-boards: FAIL — cannot read PROBES reliably. "
            "Found %d FIPS (%d distinct) against per-entry key counts %s. "
            "Every entry needs one fips, one county and one seats, and no two "
            "entries may share a FIPS. Fix the table rather than this reader: "
            "a county missing from this set lands in the frontier and the "
            "gate then tells you to re-sweep a host that may refuse us."
            % (len(fips), len(set(fips)), tally))
    return set(fips)


def frontier():
    """Counties with no roster and no PROBES entry, with seats and population
    read from the shipped district geometry rather than a hand-kept table."""
    geo = json.load(open(DISTRICTS))
    feats = geo["features"] if isinstance(geo, dict) else geo
    pop, seats, name = {}, {}, {}
    for f in feats:
        p = f["properties"]
        fips = p["CountyFIPS"]
        pop[fips] = pop.get(fips, 0) + (p.get("Population") or 0)
        seats[fips] = seats.get(fips, 0) + 1
        name[fips] = p["County"].replace(" County", "")
    built = set(json.load(open(ROSTER)))
    probed = probes_fips(open(SCRAPER).read())
    rows = [{"fips": f, "county": name[f], "seats": seats[f], "pop": pop[f]}
            for f in pop if f not in built and f not in probed]
    rows.sort(key=lambda r: -r["pop"])
    return rows, len(built), len(probed), sum(pop.values())


# ------------------------------------------------------------------- stage one

def _resolve(host, attempts=3):
    """DNS WITH RETRIES, because a flaky lookup silently deletes a county's
    real host from its own candidate list.

    Marquette is the measured case. Sweep 1 read its board from
    co.marquette.mi.us; sweep 2 returned `no-board-page` and that host appears
    in neither the confirmed nor the rejected list, because its lookup failed
    once. validate_card_links.py already carries this rule for the same reason
    -- a flaky parallel lookup there reported two live sites as having no DNS
    record.

    THE FIRST VERSION OF THIS RETRY COULD NOT RETRY, and the docstring claimed
    it did. socket.gethostbyname raises gaierror for EVERY resolution failure,
    both EAI_NONAME (-2, the name does not exist) and EAI_AGAIN (-3, a dropped
    packet or a timeout), and the handler returned on the bare `except
    socket.gaierror` under a comment calling it "a real NXDOMAIN". So the arm
    that sleeps and loops was unreachable for the one failure mode the retry
    was written for, `attempts` was dead, and every no-host verdict still
    carried the flakiness the commit said it had removed. Driven with a stubbed
    resolver on 2026-09-18: EAI_AGAIN gave 1 lookup and None in 0.00s, as did
    EAI_NONAME. THE ERRNO IS WHAT SEPARATES THEM and it has to be read.

    Nor was Marquette's sweep-3 recovery caused by this retry, since the retry
    never ran: it came from the confirm cap going 3 to 6 in the same commit.

    socket.setdefaulttimeout() is NOT set here, deliberately. It governs
    socket operations and not gethostbyname, which goes through the system
    resolver, so the 4-second bound an earlier version implied never existed.
    The retry pause is the only timing this function actually controls."""
    for i in range(attempts):
        try:
            return host, socket.gethostbyname(host)
        except socket.gaierror as exc:
            if exc.errno == socket.EAI_NONAME:
                return host, None          # the name genuinely does not exist
            if i == attempts - 1:
                return host, None
            time.sleep(0.4 * (i + 1))
        except Exception:                                         # noqa: BLE001
            if i == attempts - 1:
                return host, None
            time.sleep(0.4 * (i + 1))
    return host, None


def resolve_candidates(county):
    """DNS only. Resolution is not a fetch and asks nobody's robots.txt."""
    cands = _forms(county)
    with ThreadPoolExecutor(max_workers=DNS_WORKERS) as ex:
        got = [(h, ip) for h, ip in ex.map(_resolve, cands) if ip]
    # Prefer the spellings the fleet already sees most: a .gov or .mi.us host,
    # then one whose stem carries the whole county name, then the rest.
    def rank(pair):
        h = pair[0]
        return (0 if h.endswith((".gov", ".mi.us")) else 1,
                0 if "county" in h or h.count(".") > 2 else 1,
                len(h))
    return sorted(got, key=rank)


# ------------------------------------------------------------------- stage two

IMPOSSIBLE = "/districtry-probe-no-such-path-6f21e0a4/"

# A WAF CHALLENGE IS AN ACCESS CONTROL AND MUST BE RECORDED AS ONE, never as a
# fact about the county's content. Measured 2026-09-18: www.tuscolacounty.org
# answers HTTP 307 in 1,303 bytes behind `Server: Sucuri/Cloudproxy` with
# "Javascript is required. Please enable javascript before you are allowed to
# see this page." The probe was right not to read it and WRONG about why --
# it recorded `names-another`, "answers 200 and never names Tuscola", which
# says the county publishes something it does not.
CHALLENGE_SERVER = re.compile(r"sucuri|cloudproxy|cloudflare", re.I)
CHALLENGE_BODY = re.compile(
    r"javascript is required|enable javascript before|sucuri_cloudproxy"
    r"|cf-browser-verification|challenge-platform|_cf_chl", re.I)


def is_challenge(resp):
    if resp.status_code == 202:
        return "HTTP 202, which is never a document"
    if resp.headers.get("X-Sucuri-ID") or CHALLENGE_SERVER.search(
            resp.headers.get("Server", "")):
        if CHALLENGE_BODY.search(resp.text[:4000]):
            return "%s challenge (server %r)" % (
                "Sucuri" if resp.headers.get("X-Sucuri-ID") else "WAF",
                resp.headers.get("Server", "")[:40])
    if resp.headers.get("cf-mitigated"):
        return "Cloudflare managed challenge (cf-mitigated)"
    if 300 <= resp.status_code < 400 and CHALLENGE_BODY.search(resp.text[:4000]):
        return "HTTP %d carrying a JavaScript challenge" % resp.status_code
    return None


def robots_record(url, verdict, allowed):
    """What this client read at one host's robots.txt, in a form a later run can
    DIFF against.

    `status` alone cannot settle a disagreement: Gogebic and Marquette served
    `served` on the day this probe called them candidates AND on the day the
    scraper found `Disallow: /` in the same files, so two runs recording only
    the status would agree while contradicting each other. What separates them
    is `why`, which robots_policy.Verdict builds as "robots.txt served (N
    bytes): <the rule that decided>" — a byte count and a rule, both of which
    move when a file does.

    `read` is per RECORD and not taken from the artifact's top-level `measured`,
    because --county and --limit write one county into a file whose other rows
    were measured on another day.
    """
    return {"url": url, "status": verdict.status, "allowed": bool(allowed),
            "why": (verdict.why or "")[:300], "read": time.strftime("%Y-%m-%d")}


def confirm_host(session, gate, pacer, host, county, notes):
    """Is this host the county's own site, or somebody else's?

    Three ways a resolving host is NOT the answer, all measured rather than
    assumed: robots refuses it, it answers the same body to an impossible path
    as to its root (the lapeercountyweb.org catch-all), or its front page never
    names the county."""
    root = "https://%s/" % host
    verdict = gate.verdict(root)
    allowed, _why = verdict.allows(UA_ROSTER_BOT, root, refused_is_refusal=True)
    # THE VERDICT IS RETURNED ON EVERY PATH, including the ones that reject the
    # host, so the caller can record what was read rather than only what was
    # decided. See robots_record() for why the status alone is not enough.
    robots = robots_record(root, verdict, allowed)
    if not allowed:
        notes.append("%s robots %s — not fetched" % (host, verdict.status))
        return None, "robots-refused", verdict.status, robots
    # RETRY A TRANSPORT FAILURE AND A FAILED NAME TEST, BUT NEVER A CHALLENGE.
    # Measured 2026-09-18: sweep 4 rejected isabellacounty.org as
    # `names-another` while four consecutive fetches return 239,364 bytes that
    # DO name Isabella, md5-identical — so a single body is not evidence that a
    # county's site is somebody else's, and that rejection recorded Michigan's
    # fifth-largest untried county as having no host at all. 135 of this run's
    # rejections were transport failures and none was retried.
    r = None
    for attempt in range(3):
        try:
            with pacer.hold(root):
                r = session.get(root, timeout=TIMEOUT)
        except Exception as exc:                                  # noqa: BLE001
            if attempt == 2:
                notes.append("%s unreachable after 3 tries (%s)"
                             % (host, type(exc).__name__))
                return None, "unreachable", str(exc)[:120], robots
            time.sleep(0.6 * (attempt + 1))
            continue
        why = is_challenge(r)
        if why:
            notes.append("%s answers a %s — an access control, not read and "
                         "not worked around" % (host, why))
            return None, "challenge", why, robots
        if r.status_code >= 400:
            notes.append("%s HTTP %d on /" % (host, r.status_code))
            return None, "http-%d" % r.status_code, None, robots
        if county.lower().replace(".", "") in r.text.lower().replace(".", ""):
            break
        if attempt == 2:
            notes.append("%s answers HTTP %d in %d bytes and never names %s on "
                         "any of 3 fetches — not taken as the county's own site"
                         % (host, r.status_code, len(r.content), county))
            return None, "names-another", None, robots
        time.sleep(0.6 * (attempt + 1))
    body = r.text
    try:
        with pacer.hold(root):
            bad = session.get(root.rstrip("/") + IMPOSSIBLE, timeout=TIMEOUT)
        if bad.status_code == 200 and len(bad.content) > 400 and \
                abs(len(bad.content) - len(r.content)) < 64:
            notes.append("%s is a CATCH-ALL — an impossible path returns "
                         "%d bytes against the root's %d, so a 200 here proves "
                         "nothing" % (host, len(bad.content), len(r.content)))
            return None, "catch-all", None, robots
    except Exception:                                             # noqa: BLE001
        pass
    return (root, body), "confirmed", None, robots


# ----------------------------------------------------------------- stage three

# THE COUNTY BOARD, not any board. `board members` alone is too loose: it
# matches every advisory body a county runs, and those bodies are frequently
# SEATED ONE PER COMMISSIONER DISTRICT, so their pages carry real districts
# beside real names and score exactly like a roster. Measured 2026-09-15, that
# sent the Bay sweep to
# baycountymi.gov/health_community/department_on_aging/advisory_board_members.php
# and scored it 7/7 districts with 13 name-pairs -- a confident, well-evidenced
# reading of the wrong body. So the hint requires the office by name.
BOARD_HINT = re.compile(
    r"board[\s_\-]*of[\s_\-]*commission"
    r"|county[\s_\-]*board"
    r"|commissioners?\b"
    r"|\bboc\b",
    re.I)

# "COMMISSIONER" IS NOT UNIQUE TO THE COUNTY BOARD EITHER, and in Michigan that
# is not a quibble: a county elects a DRAIN COMMISSIONER under MCL 280 and may
# run a ROAD COMMISSION, both separate offices with their own pages. Ranking by
# the word alone sent the same sweep to
# baycountymi.gov/departments/drain_commissioner/index.php, which reported
# `no-districts` -- the right family of answer for entirely the wrong reason,
# which is worse than a wrong answer because it reads as a measurement.
NOT_THE_BOARD = re.compile(
    r"drain|road[\s_\-]*commission|soil|water[\s_\-]*resource|equaliz"
    r"|planning[\s_\-]*commission|parks?[\s_\-]*commission|canvass"
    r"|zoning|apportionment[\s_\-]*commission|election[\s_\-]*commission"
    # advisory and subordinate bodies, which a county seats BY district
    r"|advisory|aging|veteran|librar|health[\s_\-]*board|mental|airport"
    r"|brownfield|\bdda\b|land[\s_\-]*bank|housing|transit|medical[\s_\-]*care"
    r"|construction[\s_\-]*code|jury|retirement|drug|substance",
    re.I)


def board_links(root, body):
    """Board-ish links in the front page's own HTML.

    Eaton's front page links its apportionment MAP (a PDF in /DocumentCenter/)
    with board wording in the link text, and a sweep that took the first
    board-ish link scored the county 0/15 districts off a PDF. SKIP_PATH drops
    it. Measured 2026-09-15."""
    from urllib.parse import urljoin
    out, seen = [], set()
    host = root.split("/")[2]
    for m in re.finditer(r'<a\b[^>]*href="([^"#?]+)"[^>]*>(.*?)</a>', body, re.S | re.I):
        href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        if not BOARD_HINT.search(href) and not BOARD_HINT.search(text):
            continue
        if NOT_THE_BOARD.search(href) or NOT_THE_BOARD.search(text):
            continue
        url = urljoin(root, href)
        if host not in url or url.rstrip("/") == root.rstrip("/") or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


SKIP_PATH = re.compile(
    r"\.(pdf|docx?|xlsx?|pptx?|jpe?g|png|gif|zip|csv|xml)$"
    r"|/DocumentCenter/|/Archive|agenda|minutes|/news|calendar|vacanc", re.I)


def sitemap_pages(session, gate, pacer, root):
    """The site's OWN index of its pages, which is the only route that reaches
    a page the front page never links.

    EATON IS WHY THIS EXISTS. Its board page is /295/Board-of-Commissioners and
    its front page's HTML links it nowhere: the only board-ish href in 123,443
    bytes is a PDF apportionment map, because the government menu is built
    client-side. Front-page discovery alone recorded `no-board-page` for a
    county whose fifteen commissioners this project already ships. Measured
    2026-09-15, eatoncounty.org/sitemap.xml carries 918 locs and exactly one
    board-ish, the right one; www.washtenaw.org/sitemap.xml carries 228 and four.

    A CMS THAT ANSWERS 404 WITH A WHOLE PAGE IS NOT A SITEMAP:
    baycountymi.gov returns 177,411 bytes under HTTP 404, so the status is what
    decides and never the body's size."""
    from urllib.parse import urljoin
    out = []
    for name in ("sitemap.xml", "sitemap_index.xml"):
        url = urljoin(root, name)
        if not gate.verdict(url).allows(UA_ROSTER_BOT, url, refused_is_refusal=True):
            continue
        try:
            with pacer.hold(url):
                r = session.get(url, timeout=TIMEOUT)
        except Exception:                                         # noqa: BLE001
            continue
        if r.status_code >= 400 or "<loc>" not in r.text:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
        for child in [l for l in locs if l.lower().endswith(".xml")][:4]:
            if not gate.verdict(child).allows(UA_ROSTER_BOT, child,
                                              refused_is_refusal=True):
                continue
            try:
                with pacer.hold(child):
                    cr = session.get(child, timeout=TIMEOUT)
                if cr.status_code < 400:
                    locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", cr.text)
            except Exception:                                     # noqa: BLE001
                pass
        host = root.split("/")[2]
        out = [l for l in locs
               if BOARD_HINT.search(l) and not SKIP_PATH.search(l)
               and not NOT_THE_BOARD.search(l) and host in l]
        if out:
            break
    return out


def rank_pages(urls):
    """A page naming MEMBERS outranks one naming DISTRICTS: Bay's districts
    page is seven map links and names nobody."""
    def key(u):
        blob = u.lower()
        return (0 if re.search(r"member|commissioner|directory|who", blob) else 1,
                1 if re.search(r"district|map|apportion", blob) else 0,
                len(u))
    return sorted({u for u in urls if not SKIP_PATH.search(u)
                   and not NOT_THE_BOARD.search(u)}, key=key)[:8]


# ------------------------------------------------------------------ stage four

TAG = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
           "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
           "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
           "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
           "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
           "twenty-first": 21}
# A name is two-to-four capitalised words. Deliberately loose: this counts
# name-SHAPED strings as evidence and never extracts a name. Nothing in this
# file ever writes a person's name into a roster.
NAMEISH = re.compile(r"\b[A-Z][a-z]{1,15}(?:\s+[A-Z]\.?)?\s+[A-Z][a-z'\-]{1,18}\b")
STOPWORDS = ("Board Of", "County Board", "Board Meeting", "Read More",
             "Contact Us", "Skip To", "Public Comment", "Meeting Agenda",
             "Privacy Policy", "Site Map", "County Commissioner",
             "Commissioner District", "Annual Report", "Home Page",
             "Business Hours", "Office Hours", "Section Name",
             "Quick Links", "Main Office", "Learn More", "View All")


def classify(html_body, seats):
    """Report EVIDENCE, never a name and never a promise.

    Berrien writes its districts ordinally, so a `District N` regex alone finds
    nothing there -- both spellings are counted."""
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", TAG.sub(" ", html_body)))
    nums = set(int(n) for n in re.findall(r"\bDistrict\s+#?(\d{1,2})\b", txt, re.I))
    for word, n in ORDINAL.items():
        if re.search(r"\b%s\s+district\b" % word, txt, re.I):
            nums.add(n)
    nums = {n for n in nums if 1 <= n <= max(seats, 21)}
    names = {m.group(0) for m in NAMEISH.finditer(txt)
             if not any(s.lower() in m.group(0).lower() for s in STOPWORDS)}
    mailto = len(set(re.findall(r'mailto:([^"?\s>]+)', html_body, re.I)))
    cfmail = len(re.findall(r"data-cfemail", html_body, re.I))
    tel = len(set(re.findall(r'href="tel:([0-9+\-() .]{7,})"', html_body, re.I)))
    # Do the names sit NEAR the districts? A page listing districts in one
    # block and staff in another is not a district-keyed roster.
    #
    # AND THE SAME NAME BESIDE EVERY DISTRICT IS CHROME, NOT A ROSTER. Bay's
    # districts page scored 7 near-pairs of 7 seats on `Center Ave`, `Bay City`
    # and `Contact Us` — its address block and nav, repeating identically in
    # every window. Measured 2026-09-15, and Bay is in PROBES as not-keyable,
    # so a probe that called it a candidate was wrong in the expensive
    # direction. A name-shaped string appearing beside more than half the
    # districts is dropped before any pair is counted.
    # SEGMENTS ARE KEYED BY DISTRICT NUMBER, NOT BY OCCURRENCE, and that
    # distinction is the whole rule. Two earlier versions both discarded real
    # commissioners as furniture, each for its own reason, and both still
    # passed the settled counties while understating them -- which is how a
    # denser page would have read as `not-keyable`.
    #
    # A fixed window around each district token OVERLAPS its neighbours on a
    # dense page, so one name falls in two windows. Segmenting from each token
    # to the next fixed that and exposed the second cause: a page names the
    # same district MORE THAN ONCE -- Eaton carries a district nav list above
    # its member list -- so a name appears in two segments of the SAME
    # district. Measured 2026-09-15 on Eaton, a real 15-member roster: fixed
    # windows left 4 near-pairs of 26 names, per-occurrence segments left 2 of
    # 17, and keying by number leaves the roster intact.
    marks = list(re.finditer(r"\bDistrict\s+#?(\d{1,2})\b", txt, re.I))
    per_number = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else min(len(txt), m.end() + 180)
        seg = txt[m.start():min(end, m.start() + 400)]
        found = {x.group(0) for x in NAMEISH.finditer(seg)
                 if not any(st.lower() in x.group(0).lower() for st in STOPWORDS)}
        per_number.setdefault(int(m.group(1)), set()).update(found)
    windows = list(per_number.values())
    # A COMMISSIONER BELONGS TO ONE DISTRICT, so a name-shaped string sitting
    # under more than one district NUMBER is not a district-keyed name. On
    # these pages it is always page furniture: Bay's `Center Ave`, `Bay City`
    # and `Business Hours` are its address block and nav, repeating under every
    # district, and an earlier threshold of "more than half the districts" let
    # `Business Hours` through on 3 of 7 and scored Bay -- whose board pages
    # name nobody -- as a candidate.
    seen_in = {}
    for w in windows:
        for nm in w:
            seen_in[nm] = seen_in.get(nm, 0) + 1
    chrome = {nm for nm, c in seen_in.items() if len(windows) >= 3 and c > 1}
    near = sum(1 for w in windows if w - chrome)
    distinct_near = len(set().union(*windows) - chrome) if windows else 0
    return {"districts_found": sorted(nums), "district_count": len(nums),
            "seats": seats, "names_seen": len(names), "near_pairs": near,
            "distinct_near": distinct_near, "chrome_dropped": len(chrome),
            "mailto": mailto, "cfemail": cfmail, "tel": tel,
            "text_bytes": len(txt)}


def verdict_for(ev):
    """A DISTRICT-KEYED ROSTER NAMES ABOUT ONE PERSON PER DISTRICT, and that
    ratio is the discriminator rather than the mere presence of a name.

    Measured 2026-09-15 across the four counties whose answer is settled:

        Eaton      15 districts, 15 named   1.00   ships 15
        Lapeer      7 districts,  7 named   1.00   ships 7
        Washtenaw   9 districts,  9 named   1.00   names present, in free prose
        Bay         7 districts,  1 named   0.14   board pages name NOBODY

    An earlier rule asked only whether the count was zero, and Bay's single
    stray name on its districts page -- seven map links and no roster -- passed
    it. The 0.6 floor sits in a gap between 1.00 and 0.14, so it is read off
    that spread rather than tuned until a case passed; nothing here is a gate
    being loosened to get a county through."""
    if ev is None:
        return "no-board-page"
    if ev["district_count"] == 0:
        return "no-districts"
    if ev["names_seen"] < 2:
        return "not-keyable"
    if ev["near_pairs"] < max(2, 0.6 * ev["district_count"]):
        return "not-keyable"
    if ev["district_count"] >= max(2, ev["seats"] - 2):
        return "candidate"
    return "partial"


def score(ev):
    """Rank candidates by how much a parser would have to work with.
    Contact details count because the card renders them."""
    if not ev:
        return -1
    cover = ev["district_count"] / float(ev["seats"] or 1)
    return round(100 * min(cover, 1.0)
                 + 10 * min(ev["near_pairs"] / float(ev["seats"] or 1), 1.0)
                 + 5 * (1 if (ev["mailto"] or ev["cfemail"]) else 0)
                 + 3 * (1 if ev["tel"] else 0), 1)


# ----------------------------------------------------------------- the sweep

def ua_session():
    # Module-scope in this file until 2026-09-19. --check, --prune and
    # --refresh-robots never build a session, and --check is what CI runs, so
    # the import belongs in the one function that needs it: the CI step then
    # needs no pip line at all, rather than one the step before it happens to
    # have run.
    import requests

    s = requests.Session()
    s.headers["User-Agent"] = UA_ROSTER_BOT
    s.headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
    return s


def probe_county(row):
    session = ua_session()
    gate = RobotsGate(session, UA_ROSTER_BOT)
    pacer = HostPacer(gate)
    notes, rejected = [], []
    out = dict(row, host=None, board_url=None, verdict="no-host",
               evidence=None, score=-1, notes=notes, rejected=rejected,
               robots={})

    resolved = resolve_candidates(row["county"])
    out["resolved"] = len(resolved)
    if not resolved:
        notes.append("no candidate host resolves — a fact about these %d "
                     "candidates, not about the county" % len(_forms(row["county"])))
        return out

    # EVERY CONFIRMED HOST IS TRIED, NOT THE FIRST. The ranking prefers a .gov,
    # and for Washtenaw that is washtenaw.gov, which confirms as the county and
    # carries no board link at all, while the county's real board page is on
    # www.washtenaw.org. Stopping at the first confirmed host recorded
    # `no-board-page` for a county whose page this project has already read.
    # Measured 2026-09-15.
    confirmed, best = [], None
    for host, _ip in resolved[:12]:
        page, why, detail, robots = confirm_host(
            session, gate, pacer, host, row["county"], notes)
        if page:
            confirmed.append((host, page, robots))
        else:
            rejected.append({"host": host, "why": why, "detail": detail,
                             "robots": robots})
        # NO CAP ON CONFIRMED HOSTS UNTIL A BOARD PAGE IS FOUND. Capping at
        # three meant a county's real host could be crowded out by other
        # spellings that also confirm and carry nothing, which is the second
        # half of the Marquette regression: marquettecounty.org, its www
        # form and marquette.org all confirmed and none carries a board
        # page. Confirming is cheap; it is the board-page fetches that cost.
        if len(confirmed) >= 6:
            break
    if not confirmed:
        kinds = {r["why"] for r in rejected}
        out["verdict"] = ("robots-refused" if kinds == {"robots-refused"}
                          else "no-confirmed-host")
        return out
    out["host"] = confirmed[0][0]
    # THE HOST THIS PROBE ACCEPTED, recorded at last. Until 2026-09-19 only the
    # REJECTED hosts carried a robots reading, so the one host a later run would
    # want to compare against was the one nothing was written down about.
    out["robots"]["host"] = confirmed[0][2]

    for host, (root, body), _robots in confirmed:
        pages = rank_pages(sitemap_pages(session, gate, pacer, root)
                           + board_links(root, body))
        if not pages:
            notes.append("%s: neither its sitemap nor its front page names "
                         "a board page" % host)
        for url in pages:
            v = gate.verdict(url)
            page_ok, _why = v.allows(UA_ROSTER_BOT, url, refused_is_refusal=True)
            if not page_ok:
                notes.append("%s robots %s — not fetched" % (url, v.status))
                continue
            # The BOARD page is a second reading and is kept separately: a host
            # can serve robots.txt that allows / and disallows the path a board
            # page sits under, and the two answers then differ for one county.
            board_robots = robots_record(url, v, page_ok)
            try:
                with pacer.hold(url):
                    r = session.get(url, timeout=TIMEOUT)
            except Exception as exc:                              # noqa: BLE001
                notes.append("%s (%s)" % (url, type(exc).__name__))
                continue
            if r.status_code >= 400:
                continue
            ev = classify(r.text, row["seats"])
            if best is None or score(ev) > score(best[1]):
                best = (url, ev, host, board_robots)
        if best and verdict_for(best[1]) == "candidate":
            break
    if best:
        out["board_url"], out["evidence"], out["host"] = best[0], best[1], best[2]
        out["robots"]["board"] = best[3]
        # The accepted BOARD page can sit on a different host from confirmed[0],
        # which is the Washtenaw case, so the host reading is re-taken from the
        # host that actually supplied it rather than left pointing elsewhere.
        for host, _page, robots in confirmed:
            if host == best[2]:
                out["robots"]["host"] = robots
                break
        out["verdict"] = verdict_for(best[1])
        out["score"] = score(best[1])
    else:
        # AN ACCESS CONTROL OUTRANKS AN ABSENCE. Tuscola is the measured case:
        # sweep 3 read its board from tuscolacounty.org, which now answers a
        # Sucuri challenge, while tuscolacounty.com confirms as the county and
        # carries no board page. Reporting `no-board-page` would say Tuscola
        # publishes no board page, when it publishes one this client can no
        # longer read — the same class of error as calling the challenge
        # `names-another`. So a challenge anywhere among the rejected hosts
        # wins when nothing else yielded a board page.
        blocked = [r for r in rejected if r["why"] == "challenge"]
        if blocked:
            out["verdict"] = "challenge"
            notes.append("%d host(s) answered an access control and no other "
                         "confirmed host carries a board page, so this is "
                         "recorded as blocked rather than as the county "
                         "publishing nothing" % len(blocked))
        else:
            out["verdict"] = "no-board-page"
            notes.append("no confirmed host carries a board page this client "
                         "can read")
    delays = getattr(pacer, "honoured", None)
    if delays:
        notes.append("crawl-delay honoured: %s" % delays)
    return out


def sweep(rows):
    results = []
    with ThreadPoolExecutor(max_workers=HOST_WORKERS) as ex:
        for i, res in enumerate(ex.map(probe_county, rows), 1):
            results.append(res)
            print("  [%2d/%d] %-15s %-18s %s"
                  % (i, len(rows), res["county"], res["verdict"],
                     res["host"] or ""), flush=True)
    return results


def report(results, meta):
    order = sorted(results, key=lambda r: (-r["score"], -r["pop"]))
    print("\n=== ORDERED BY WHETHER THE COUNTY PUBLISHES A ROSTER ===")
    print("%-16s %-5s %-15s %5s  %s" % ("county", "seats", "verdict", "score", "evidence"))
    for r in order:
        ev = r["evidence"] or {}
        eb = ("%d/%d districts, %d near-pairs, %d mailto, %d tel"
              % (ev.get("district_count", 0), r["seats"], ev.get("near_pairs", 0),
                 ev.get("mailto", 0) + ev.get("cfemail", 0), ev.get("tel", 0))
              ) if ev else ""
        print("%-16s %-5d %-15s %5s  %s" % (r["county"], r["seats"], r["verdict"],
                                            r["score"] if r["score"] >= 0 else "-", eb))
    tally = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print("\nverdicts: %s" % ", ".join("%s %d" % kv for kv in sorted(tally.items())))
    cand = [r for r in order if r["verdict"] == "candidate"]
    print("candidates: %d counties, %d seats, %s people"
          % (len(cand), sum(r["seats"] for r in cand),
             format(sum(r["pop"] for r in cand), ",")))
    print("\nA `candidate` means A PARSER IS WORTH WRITING and never that the "
          "county will ship.\nWashtenaw would score as one and is already in "
          "PROBES: districts and names both\npresent, the names in free prose "
          "with no field to read them from.")


def refresh_robots(rows):
    """Re-read robots.txt for every host already in the artifact, and nothing else.

    THE FIELD IS USELESS EMPTY. `robots` was added on 2026-09-19 and the 25
    recorded counties predate it, so `--check` could only require it of rows
    written afterwards — which is a gate that passes on the file it exists to
    guard. This fills them, at the cheapest request there is: robots.txt and no
    page, one file per host, which is the request every client in this project
    makes first anyway.

    IT DOES NOT RE-PROBE. No verdict, evidence, score or board_url is touched,
    because a robots reading is not a reason to re-decide whether a county
    publishes a roster; the two are separate questions and merging them here
    would turn a 24-fetch refresh into a full sweep.

    A reading that DISAGREES with the recorded one is printed rather than
    swallowed, since that is the whole point of writing it down.
    """
    if not os.path.exists(ARTIFACT):
        print("probe-mi-county-boards: FAIL — no artifact to refresh", file=sys.stderr)
        return 1
    with open(ARTIFACT) as fh:
        data = json.load(fh)
    session = ua_session()
    gate = RobotsGate(session, UA_ROSTER_BOT)
    read = changed = filled = 0
    for rec in data["counties"]:
        for kind, url in (("host", "https://%s/" % rec["host"] if rec.get("host") else None),
                          ("board", rec.get("board_url"))):
            if not url:
                continue
            verdict = gate.verdict(url)
            allowed, _why = verdict.allows(UA_ROSTER_BOT, url, refused_is_refusal=True)
            fresh = robots_record(url, verdict, allowed)
            read += 1
            was = (rec.get("robots") or {}).get(kind)
            if not was:
                filled += 1
            elif (was["status"] != fresh["status"]
                  or was["allowed"] != fresh["allowed"]
                  or was["why"] != fresh["why"]):
                changed += 1
                print("  %-14s %-6s CHANGED since %s\n      was: %s %s %s\n      now: %s %s %s"
                      % (rec["county"], kind, was["read"],
                         was["status"], was["allowed"], was["why"][:90],
                         fresh["status"], fresh["allowed"], fresh["why"][:90]))
            rec.setdefault("robots", {})[kind] = fresh
        print("  %-14s %s" % (rec["county"], (rec.get("robots") or {}).get(
            "host", {}).get("status", "no host")), flush=True)
    with open(ARTIFACT, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write("\n")
    # A FILL IS NOT A COMPARISON. On the first run every record is new, so
    # "0 disagreed" would be true and would mean nothing; the two are counted
    # apart so the line cannot read as a clean bill of health it did not earn.
    print("probe-mi-county-boards: %d robots.txt read across %d counties — "
          "%d recorded for the first time, %d compared against a previous "
          "reading, %d of those disagreed"
          % (read, len(data["counties"]), filled, read - filled, changed))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true",
                    help="offline re-audit of the written artifact")
    ap.add_argument("--prune", action="store_true",
                    help="offline: drop counties that have left the frontier")
    ap.add_argument("--refresh-robots", action="store_true",
                    help="re-read robots.txt for the recorded hosts, nothing else")
    ap.add_argument("--county", help="probe one county by name")
    ap.add_argument("--limit", type=int, help="probe only the first N")
    args = ap.parse_args()

    rows, built, probed, statepop = frontier()
    if args.check:
        return check(rows)
    if args.prune:
        return prune(rows)
    if args.refresh_robots:
        return refresh_robots(rows)

    n = check_generator()
    print("probe-mi-county-boards: generator finds %d of %d known hosts" % (n, n))
    # THE LAYER'S OWN TOTAL, NOT MICHIGAN'S. frontier() sums the shipped
    # district geometry's Population field, which comes to 10,007,596 because
    # 24 counties' districts do not add up to their census population and
    # Cheboygan's seven all read 0. Michigan's Census 2020 population is
    # 10,077,331. Calling this figure Michigan's overstates every coverage
    # share computed from it, which is what three documents did until
    # 2026-09-18.
    print("frontier: %d counties untried (%d ship a roster, %d recorded shut), "
          "%s of the %s people the state's district layer accounts for\n"
          % (len(rows), built, probed,
             format(sum(r["pop"] for r in rows), ","), format(statepop, ",")))

    if args.county:
        rows = [r for r in rows if r["county"].lower() == args.county.lower()]
        if not rows:
            raise SystemExit("no untried county named %r" % args.county)
    if args.limit:
        rows = rows[:args.limit]

    t0 = time.time()
    results = sweep(rows)
    report(results, None)
    if not args.county and not args.limit:
        os.makedirs(os.path.dirname(ARTIFACT), exist_ok=True)
        payload = {"measured": time.strftime("%Y-%m-%d"),
                   "client": UA_ROSTER_BOT,
                   "candidates_per_county": "about 61, gated on %d known hosts" % n,
                   "counties": results}
        with open(ARTIFACT, "w") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("\nwrote %s (%d counties)" % (os.path.relpath(ARTIFACT, _ROOT), len(results)))
    print("elapsed %.0fs" % (time.time() - t0))
    return 0


def prune(rows):
    """Offline: drop the counties that have LEFT the frontier since the sweep.

    A county leaves by shipping a roster or by being recorded in the scraper's
    PROBES table, and neither makes its measurement wrong — it makes the
    measurement redundant, because the scraper's own tables are the record for
    a county that has been decided. Re-sweeping 59 hosts to write that down
    would be traffic for nothing, and traffic is not free: six sweeps in four
    days tripped Sucuri on Tuscola while this file was being written.

    A county ARRIVING on the frontier is the opposite case and this refuses it
    — nothing has measured that county, and only a sweep can.
    """
    if not os.path.exists(ARTIFACT):
        print("probe-mi-county-boards: no artifact to prune (%s)"
              % os.path.relpath(ARTIFACT, _ROOT))
        return 0
    data = json.load(open(ARTIFACT))
    want = {r["fips"] for r in rows}
    have = {r["fips"] for r in data["counties"]}
    new = sorted(want - have)
    if new:
        print("probe-mi-county-boards: FAIL — %d untried counties are absent from "
              "the artifact (%s). Nothing has measured them, so this is a sweep "
              "and not a prune." % (len(new), ", ".join(new)))
        return 1
    gone = sorted(have - want)
    if not gone:
        print("probe-mi-county-boards: nothing to prune — the artifact already "
              "describes the %d untried counties" % len(want))
        return 0
    names = {r["fips"]: r["county"] for r in data["counties"]}
    data["counties"] = [r for r in data["counties"] if r["fips"] in want]
    data["pruned"] = sorted(set(data.get("pruned", []))
                            | {"%s %s" % (f, names[f]) for f in gone})
    with open(ARTIFACT, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("probe-mi-county-boards: pruned %d county(ies) that have shipped or "
          "been recorded shut (%s) — %d untried counties remain, still measured %s"
          % (len(gone), ", ".join("%s %s" % (f, names[f]) for f in gone),
             len(data["counties"]), data["measured"]))
    return 0


def check(rows):
    """Offline: the artifact must still describe the tree it was measured on."""
    if not os.path.exists(ARTIFACT):
        print("probe-mi-county-boards: no artifact yet (%s) — nothing to audit"
              % os.path.relpath(ARTIFACT, _ROOT))
        return 0
    data = json.load(open(ARTIFACT))
    have = {r["fips"] for r in data["counties"]}
    want = {r["fips"] for r in rows}
    gone = sorted(have - want)
    new = sorted(want - have)
    bad = []
    if gone:
        bad.append("%d counties in the artifact have since shipped or been "
                   "recorded shut (%s) — run --prune, which drops them without "
                   "re-fetching anything" % (len(gone), ", ".join(gone)))
    if new:
        bad.append("%d untried counties are absent from the artifact (%s) — "
                   "re-run the sweep" % (len(new), ", ".join(new)))
    # THE FIELD IS REQUIRED WHERE IT IS MEANINGFUL, or the gate passes on the
    # very file it was written to guard. A record naming a host must carry that
    # host's robots reading and a record naming a board page must carry the
    # page's; --refresh-robots fills both without re-probing anything.
    missing = []
    for rec in data["counties"]:
        got = rec.get("robots") or {}
        if rec.get("host") and not got.get("host"):
            missing.append("%s (host)" % rec["county"])
        if rec.get("board_url") and not got.get("board"):
            missing.append("%s (board)" % rec["county"])
    if missing:
        bad.append("%d record(s) name a URL and carry no robots reading (%s) — "
                   "run --refresh-robots, which reads robots.txt and no page"
                   % (len(missing), ", ".join(missing[:6])))
    check_generator()
    if bad:
        print("probe-mi-county-boards: FAIL")
        for b in bad:
            print("  " + b)
        return 1
    print("probe-mi-county-boards: OK — %d counties measured %s%s, every named "
          "URL carries a robots reading, generator still finds all %d known hosts"
          % (len(have), data["measured"],
             ", %d since pruned" % len(data["pruned"]) if data.get("pruned") else "",
             len(KNOWN_HOSTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
