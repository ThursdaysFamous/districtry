#!/usr/bin/env python3
"""
Scrape Wisconsin's Court of Appeals bench from wicourts.gov. Stage 1 of the
pair; build_wi_coa_roster.py turns the intermediate JSON into
data/app/wi-court-of-appeals-roster.json.

TWO PAGES: /contact/Court_of_Appeals.html carries the bench — per-district
blocks ("District I - Milwaukee County", a chambers address, then contact
rows where JUDGES ARE THE ALL-CAPS 'X, HON. Y' ROWS and the mixed-case rows
are staff attorneys, never read — and /courts/appeals/index.htm carries the
four district county lists, which this scraper ASSERTS against the statutory
composition (Wis. Stat. 752.11) hardcoded in build_wi_court_of_appeals.py, so
a redistricting of the appeals map fails this run loudly.

THE MEASURED TRAP THIS FILE EXISTS TO DODGE: the judges INDEX page's nav menu
is a stale former-judge list — 6 of its 16 names were wrong at research time
(2026-08-25) — while the contact page's content blocks are current. Read the
content, never the nav.

Seats are gated per district (4/4/3/5 per current law — s. 752.03's
one-per-district-per-year election cycle over 16 judgeships); a vacancy would
show as a count drop and deserves a human read, not a silent ship.
"""

import errno
import json
import os
import re
import socket
import ssl
import time
import sys
import urllib.error
import urllib.request

DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "wi_coa_raw.json")
# WHY A DISTRICTRY TOKEN AND NOT A CHROME STRING (2026-09-12). This file sent
# `Mozilla/5.0 ... Chrome/124.0` until today, with nothing recorded about a
# refusal that needed it. www.wicourts.gov is measured `token-ok` in
# user-agent-measurements.json, and re-asked on this file's own stack the same
# day every URL below answered HTTP 200 to this exact token in under a second.
# robots.txt is a 404, so allow-all.
#
# THIS IS NOT THE FIX FOR THIS WORKFLOW'S FAILURES, AND THE CAUSE IS NOW
# MEASURED: THE BLOCK IS PER RUNNER EGRESS IP. Six of the twelve runs of the
# two wicourts.gov workflows die in `sock.connect` with a TCP connect timeout,
# on schedule and on dispatch — no HTTP byte leaves the runner, so the host
# never sees any header this file sends.
#
# 2026-09-16 settles what varies, from the two workflows' OWN probe steps,
# 36 minutes apart, same host, same day:
#
#   19:01  circuit court  egress 172.202.78.13  http=200  host_ip=165.219.245.77
#                                               connect=0.078s  total=0.186s
#   19:37  appeals        egress 4.246.135.37   http=000  host_ip= (empty)
#                                               connect=0.000s  total=20.003s
#
# `host_ip` EMPTY on the failing side means curl never opened a socket: packets
# DROPPED, not refused. So www.wicourts.gov IS reachable from GitHub's runners,
# just not from every one of them, and which runner a job draws is the whole
# variable — not the token, not the path, not the hour, and not a standing block
# on GitHub's ranges. It also explains the split that looks like two different
# problems and is one: appeals is 2 green of 7 and circuit court 4 of 5, and on
# both 2026-09-09 and 2026-09-16 circuit court passed and appeals failed half an
# hour later. Issue #387 carries the run table.
#
# WHAT THIS RULES OUT, so nobody builds it: an Internet Archive rung (its
# snapshots of these two pages are dated 2026-08-08 and 2026-08-19, both OLDER
# than the shipped roster, so it would move the data backwards), a second
# publisher (the Blue Book's bench is April 2025, older still), and a `blocked`
# entry in validate_sources.py (the source is reachable from CI, so the flag's
# inversion would flap month to month on the luck of the draw). The remedy for a
# failed run is to RE-RUN it and draw another runner.
UA = {
    "User-Agent": "districtry-wisconsin/1.0 (+https://districtry.com/wi/)",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}
CONTACT_URL = "https://www.wicourts.gov/contact/Court_of_Appeals.html"
INDEX_URL = "https://www.wicourts.gov/courts/appeals/index.htm"

EXPECT_SEATS = {"1": 4, "2": 4, "3": 3, "4": 5}

# The statutory composition the index page must keep agreeing with —
# build_wi_court_of_appeals.py's DISTRICTS is the authority; this import
# keeps one table, two witnesses.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_wi_court_of_appeals import DISTRICTS  # noqa: E402


def fetch(url, tries=3, timeout=45):
    """One wicourts.gov page, with the ladder the sibling scrapers use.

    THE RETRY IS WHY THIS EXISTS, AND IT CANNOT CLEAR THE CURRENT FAILURE.
    Until 2026-09-03 this was a single urlopen with no ladder, and the weekly
    job had NEVER ONCE been green: both scheduled runs (2026-08-26 and
    2026-09-02) died in about a minute on one `urlopen error timed out`, which
    is one attempt and no second chance. Ten of this instance's thirteen
    scrapers already retry; this was one of the three that did not, and the two
    never-green jobs were both among them.

    That reasoning ended "what failed was a moment on somebody else's server,
    which is exactly what a ladder is for", and the header above now DISPROVES
    it. ALL THREE ATTEMPTS RUN ON ONE RUNNER AND THEREFORE FROM ONE EGRESS IP,
    and that address is what decides whether a socket opens at all — so three
    tries from a dropped address are three failures, which is what the
    2026-09-12 run spent 2m39s demonstrating. The ladder stays, because it is
    right for the failure it was written for and this file still fetches two
    pages over somebody else's network. What clears THIS failure is a different
    runner, so the remedy is re-running the job, never anything in here.
    """
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=ssl.create_default_context()) as r:
                data = r.read()
            return data.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — retried, then re-raised
            last = e
            time.sleep(2 * (i + 1))
    raise last


# EXIT 75 MEANS "COULD NOT ASK", AND NOTHING ELSE DOES.
# The header above measures why this job fails: the runner's egress address
# decides whether a socket opens at all, so a failing run never sends a byte and
# the host never sees it. That is not the same event as the contact page moving
# or the bench changing shape, and until 2026-09-19 this file reported both the
# same way — a traceback and exit 1 — so the workflow could not tell a court
# that answered something unexpected from a court it never reached.
#
# 75 is EX_TEMPFAIL. The workflow forgives it, subject to the staleness ceiling
# in wi_coa_staleness.py; every other failure stays red, which is the direction
# that costs nothing if this classifier is wrong.
#
# AN AUTOMATIC RE-RUN WAS CONSIDERED AND DELIBERATELY NOT BUILT. Clearing this
# failure needs a DIFFERENT RUNNER, which is a thing no in-process retry can
# ask for — the `fetch()` docstring below is the measurement that proves it,
# three attempts from one dropped egress address being three failures. Getting
# another runner means dispatching the workflow again, and a workflow that
# dispatches itself is the loop this repo has already run into once:
# update-bing-performance.yml committed on every run, and a commit pushed as a
# PAT triggers the next run, so it was looping two runs in (CLAUDE.md, the
# traffic-data workflows). The weekly schedule gives about eight draws inside
# the 60-day ceiling against a host this job reaches on roughly two runs in
# seven, so the schedule IS the retry and the ceiling is what makes its failure
# visible. An operator re-running the job by hand is still the fastest fix and
# the staleness message says so. An HTTPError is DELIBERATELY
# not forgiven: a 404 or a 500 is the host answering, and a page that has moved
# is a finding a reader needs, not a network condition to wait out.
UNREACHABLE_EXIT = 75

# WHY THIS UNWRAPS RATHER THAN MATCHING urllib.error.URLError. Measured
# 2026-09-19 on loopback: urllib funnels EVERY transport failure into URLError
# and puts the real one in `.reason` — a refused connection arrives as
# URLError(ConnectionRefusedError), a DNS miss as URLError(gaierror), and AN
# UNTRUSTED CERTIFICATE AS URLError(SSLCertVerificationError). A first draft
# matched URLError itself and therefore forgave that third one, which is wrong
# in the expensive direction: a TLS failure means the socket opened and the host
# spoke, so it is the incomplete-chain case this fleet already knows how to fix
# (pin the intermediate by AIA — scripts/coles_county_board_scraper.py), not a
# condition to wait sixty days out. Same for a URLError whose reason is a plain
# string ("unknown url type"), which is a defect in the URL above, not a network.
#
# ENETUNREACH and EHOSTUNREACH raise a bare OSError rather than a ConnectionError,
# so they are named by errno; they are genuinely before-the-host failures.
_NET_ERRNOS = {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ENETDOWN, errno.EHOSTDOWN}


def unreachable(exc):
    """True only for a failure that happened BEFORE the host answered."""
    if isinstance(exc, urllib.error.HTTPError):
        return False
    if isinstance(exc, urllib.error.URLError):
        if not isinstance(exc.reason, BaseException):
            return False
        exc = exc.reason
    if isinstance(exc, ssl.SSLError):
        return False
    if isinstance(exc, (TimeoutError, ConnectionError, socket.gaierror, socket.herror)):
        return True
    return isinstance(exc, OSError) and exc.errno in _NET_ERRNOS


def strip_tags(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


ROMAN_TO_NUM = {"I": "1", "II": "2", "III": "3", "IV": "4"}


def parse_contact(html):
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = {}
    current = None
    for i, line in enumerate(lines):
        m = re.match(r"^District (I{1,3}|IV)\s*-", line)
        if m:
            current = ROMAN_TO_NUM[m.group(1)]
            out[current] = {"address": [], "judges": []}
            # the address lines follow immediately, until the first phone/fax row
            for nxt in lines[i + 1: i + 6]:
                if re.match(r"^\(|^FAX", nxt):
                    break
                out[current]["address"].append(nxt)
            continue
        if current is None:
            continue
        jm = re.match(r"^(?P<last>[A-Z][A-Z .,'\-]+),\s*HON\.\s*(?P<first>[A-Z][A-Z .,'\-]+?)(?:\s*-\s*(?P<role>.*Judge.*))?$", line)
        if jm:
            name = "%s %s" % (jm.group("first").title().strip(), jm.group("last").title().strip())
            phone = None
            if i + 1 < len(lines) and re.match(r"^\(\d{3}\)", lines[i + 1]):
                phone = lines[i + 1]
            out[current]["judges"].append({
                "name": name,
                "role": (jm.group("role") or "").strip() or None,
                "phone": phone,
            })
    return out


def assert_composition(html):
    """The index page's four county lists must match the statutory table —
    this is the appeals map's redistricting tripwire."""
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    seen = {}
    for i, line in enumerate(lines):
        m = re.match(r"^District (I{1,3}|IV)$", line)
        if m and i + 1 < len(lines):
            counties = re.split(r",\s*|\s+and\s+", lines[i + 1])
            # the Oxford comma leaves "and Winnebago" as one fragment — strip
            # the conjunction wherever it lands, then drop empties
            counties = [re.sub(r"^and\s+", "", c.strip()).rstrip(".") for c in counties]
            counties = [c for c in counties if c and c != "and"]
            seen[ROMAN_TO_NUM[m.group(1)]] = counties
    for did, expect in DISTRICTS.items():
        got = seen.get(did)
        if got is None:
            raise SystemExit("index page names no county list for District %s" % did)
        if sorted(got) != sorted(expect):
            raise SystemExit("District %s composition moved: page says %s, statute table says %s "
                             "— re-read Wis. Stat. 752.11 and rebuild the geometry"
                             % (did, sorted(got), sorted(expect)))


def selftest():
    """The classifier's table, offline and deterministic — no socket is opened.

    A classifier that is wrong in the forgiving direction is SILENT: the job
    goes green, the roster stops being verified, and the only thing that ever
    says so is the staleness ceiling sixty days later. So every kind of failure
    this scraper can meet is named here, on the side it belongs on.

    The URLError shapes are not guesses. Measured 2026-09-19 on loopback: a
    refused connection arrives as URLError(ConnectionRefusedError), a DNS miss
    as URLError(gaierror), and an untrusted certificate as
    URLError(SSLCertVerificationError) — which is why unwrapping `.reason` is
    the whole point of the function and matching URLError alone is not enough.
    """
    cases = [
        # Forgiven: the failure happened BEFORE www.wicourts.gov answered.
        ("URLError(socket.timeout)", urllib.error.URLError(socket.timeout("timed out")), True),
        ("URLError(ConnectionRefused)", urllib.error.URLError(ConnectionRefusedError(111, "refused")), True),
        ("URLError(gaierror)", urllib.error.URLError(socket.gaierror(-2, "Name or service not known")), True),
        ("URLError(ENETUNREACH)", urllib.error.URLError(OSError(errno.ENETUNREACH, "Network is unreachable")), True),
        ("URLError(EHOSTUNREACH)", urllib.error.URLError(OSError(errno.EHOSTUNREACH, "No route to host")), True),
        ("bare TimeoutError", TimeoutError("timed out"), True),
        ("bare ConnectionResetError", ConnectionResetError(104, "reset"), True),
        # Not forgiven: the host answered, or the fault is on this side.
        ("URLError(SSLCertVerification)", urllib.error.URLError(ssl.SSLCertVerificationError("no local issuer")), False),
        ("URLError(SSLError)", urllib.error.URLError(ssl.SSLError("handshake failure")), False),
        ("URLError('unknown url type')", urllib.error.URLError("unknown url type: htps"), False),
        ("bare ssl.SSLError", ssl.SSLError("handshake"), False),
        ("HTTPError 404", urllib.error.HTTPError("u", 404, "Not Found", {}, None), False),
        ("HTTPError 500", urllib.error.HTTPError("u", 500, "Server Error", {}, None), False),
        ("HTTPError 403", urllib.error.HTTPError("u", 403, "Forbidden", {}, None), False),
        ("OSError(ENOENT)", OSError(errno.ENOENT, "No such file"), False),
        ("SystemExit (a seat gate)", SystemExit("District 1 parsed 3 judges, expected 4"), False),
        ("ValueError", ValueError("nonsense"), False),
    ]
    bad = 0
    for label, exc, want in cases:
        got = unreachable(exc)
        ok = got == want
        bad += 0 if ok else 1
        print("  %-32s forgiven=%-5s expected=%-5s %s"
              % (label, got, want, "ok" if ok else "MISMATCH"))
    if bad:
        raise SystemExit("wi-coa: --selftest FAILED on %d case(s)" % bad)
    forgiven = sum(1 for _, _, w in cases if w)
    print("wi-coa: --selftest OK — %d case(s), %d forgiven as exit %d and %d "
          "kept red" % (len(cases), forgiven, UNREACHABLE_EXIT, len(cases) - forgiven))


def main():
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    try:
        index_html = fetch(INDEX_URL)
        contact_html = fetch(CONTACT_URL)
    except Exception as e:                                     # noqa: BLE001
        if unreachable(e):
            sys.stderr.write(
                "wi-coa: COULD NOT REACH www.wicourts.gov from this runner "
                "(%s: %s). No HTTP byte left the machine, so this is the "
                "per-runner drop issue #387 records, not a change at the "
                "court. Exiting %d; the workflow decides whether the shipped "
                "roster is now too old to leave alone.\n"
                % (type(e).__name__, str(e)[:120], UNREACHABLE_EXIT))
            raise SystemExit(UNREACHABLE_EXIT)
        raise

    assert_composition(index_html)
    districts = parse_contact(contact_html)

    if sorted(districts) != ["1", "2", "3", "4"]:
        raise SystemExit("contact page parsed districts %s" % sorted(districts))
    total = 0
    for did, expect in EXPECT_SEATS.items():
        got = len(districts[did]["judges"])
        if got != expect:
            raise SystemExit("District %s parsed %d judges, expected %d — a vacancy or a "
                             "page reshape; read the page before shipping" % (did, got, expect))
        total += got
    if total != 16:
        raise SystemExit("parsed %d judges in all, expected 16" % total)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(districts, f, indent=2, ensure_ascii=False)
    print("scraped 4 districts / %d judges (composition asserted) -> %s" % (total, out_path))


if __name__ == "__main__":
    main()
