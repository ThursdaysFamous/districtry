"""
Shared plumbing for the scripts/ fleet — the parts that are identical in
dozens of files BECAUSE they carry no county knowledge at all.

WHY THIS MODULE EXISTS. The 2026-08-24 scripts audit measured the fleet at 257
files and found the same three fragments pasted everywhere: 93 byte-identical
`fail()` definitions differing only in their label string, one browser
User-Agent pinned at Chrome/126 in 46 definitions (with six more multi-file UA
strings behind it), and four independent retellings of the same retry loop —
of which only henry_county_board_scraper.py's (written after Henry's directory
served back-to-back 429s on 2026-08-02) honours Retry-After and refuses to
retry a 404. The 2026-07-09 ruling in docs/OPTIMIZATION_PLAYBOOK.md ("keep
scrapers standalone") still governs everything HEURISTIC — parsers, selectors,
zero-row guards, per-county quirks stay in the county's own file, which is
where a reader looks for them — but a fail() that prints a label is not a
heuristic, and a UA string that exists in 46 files is 46 chances to drift.
docs/OPTIMIZATION_PLAYBOOK.md §8 records the supersession.

THE USER-AGENT CONSTANTS CONSOLIDATE THE DEFINITION, NEVER THE VALUE. Changing
a scraper's UA can change how a county site treats it — several sites in this
fleet block or challenge by client fingerprint — so each constant below is the
exact bytes its importers were already sending, drifted Chrome pins and all.
Unifying the VALUES is deliberately not done here; if it ever is, it happens
per county with that county's weekly run as the witness. Single-file UA
strings (the engine tooling, the jodaviess builder, validate_sources) stay in
their own files: a one-consumer constant consolidates nothing.

WHICH SITES THOSE ARE IS NOW MEASURED, AND IT IS FAR FEWER THAN SEND A BROWSER
STRING. The sentence above said "several sites in this fleet" for ten days
(it landed 2026-09-02) without naming one. scripts/probe_user_agents.py asks each host the same page
four ways — each stack with UA_ROSTER_BOT and with UA_CHROME_WIN_126 plus
UA_HINTS_CHROME_126 — and writes user-agent-measurements.json. Measured
2026-09-12 across 296 hosts, of which 283 are reached by a browser-string
caller, 66 of them measured or re-measured since — 61 on 2026-09-13 at the page a
scraper reads rather than the directory above it, four county GIS services on
2026-09-15, and www.cpsboe.org on 2026-09-23, when the Chicago school board roster
began reading it: 226 serve UA_ROSTER_BOT a full page, 18 refuse it and answer the
browser string, and 7 refuse the `requests` STACK while serving the same token
on the stdlib client, so on those a browser string is credited with a fix the
stack made. (The first sweep read 203: 37 hosts had been probed at the first
half of a URL split across two string literals, and 23 more at a directory a
page sat under; not one re-probe moved a host INTO a refusal.) Per file
(`probe_user_agents.py --inventory` prints this tally, re-derived from the tree
and the artifact rather than remembered): 41 files send a browser string; 2
of them reach only hosts that serve the token a full page, 22 more reach no
host that refuses the token (one or more answered nothing or refused the
`requests` stack), and 17 reach at least one host that refuses it -- and 206 of
the 296 measured hosts are still reached by such a caller. The pair 101/62 that
stood here until 2026-10-01 was the state before SIXTY scrapers were switched
off a Chrome string onto our own token in one change: every page each of them
fetches was re-read with the token on that file's own HTTP stack and answered in
full, which is the measurement that licenses a rename. The 2 left in that bucket
are the two the sweep deliberately held, both of which fetch hosts discovered as
they run -- wi_municipal_executive_scraper.py follows each municipality's own
site out of a county layer, and dupage_municipal_officials_scraper.py each
village's, and several of those hosts measurably refuse the token. A FILE'S URL
LITERALS ARE NOT ALWAYS THE HOSTS IT READS, which is why that bucket cannot be
emptied by arithmetic. `fetch_stdlib` came
OFF the browser-marker list on 2026-09-25, which is what moved these four: it is
the CLIENT for two of the four rungs and sends whatever headers its caller
passes, so naming it says nothing about the User-Agent. Two files were
classified on it alone -- validate_sources.py and il_library_trustees_scraper.py
-- and neither names a Chrome string, a hint set or the word Mozilla in code. THESE FIGURES ARE
GATED: `probe_user_agents.py --check` parses them out of this docstring,
CLAUDE.md and the guidebook and FAILS naming the current ones when any differs
from the tree and the artifact, so renaming a scraper to the token moves them
and must update all three files in the same change. THREE OF THOSE FILES HAVE BEEN RENAMED TO THE TOKEN SINCE THE SWEEP and the
per-file figures move with them -- the Iowa minutes-chair scraper (#916), the
Iowa county-officers scraper, and jodaviess_county_board_scraper.py (#945) --
which is this rule working rather than drift: a file whose host serves the
token a full page gets the token back, one at a time, with its own weekly run
as the witness. An earlier
version of this paragraph said 57 and 68 of 115: the classifier then read a
districtry token without a `/N` version, and a UA constant imported from a
sibling module, as a browser string or as nothing, and the 68 was derived by a
rule nobody wrote down.

That does not license a fleet-wide rename, and the rule above is unchanged: a
file's UA moves per county with that county's weekly run as the witness. What
the measurement changes is that the move now starts from a number instead of a
guess, and a file that keeps its browser string can cite the host's own answer.

STDLIB-ONLY AT MODULE SCOPE, deliberately: scripts/validate_workflow_deps.py
walks module-scope import closures against each workflow's pip line, and this
module is imported by scripts whose workflows install nothing. `requests` is
imported inside fetch(), the one function that needs it.
"""
import io
import json
import os
import sys
import time

# --- User-Agent strings (see the module docstring: definitions, not values).
# Browser strings, by platform token and pinned Chrome version:
UA_CHROME_WIN_126 = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
UA_CHROME_WIN_126_FULL = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
UA_CHROME_WIN_124 = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
UA_CHROME_X11_128 = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
UA_CHROME_X11_120 = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
# Self-identifying bot strings. RENAMED 2026-09-12 from the retired brands
# ("chidistricts.com roster bot (civic data; contact via site)",
# "Mozilla/5.0 (compatible; districtexplorer-roster/1.0)" and
# "Mozilla/5.0 (compatible; chidistricts.com civic data bot;
# +https://chidistricts.com/)") — the one VALUE change this module has ever
# made, and made under its own rule: measured first, per host. The 26
# scheduled scrapers importing these reach 36 distinct page hosts once the
# *.arcgis.com API hosts are set aside; on 2026-09-12 every one of the 36
# answered the old bytes and the new bytes with the same HTTP status (200)
# and the same body length (equal, not merely within tolerance), through
# Cloudflare, Sucuri, LiteSpeed and IIS fronts alike, with no challenge
# header on either. The measurement script and per-host rows are in the PR
# that made the change (#886). Each county's weekly run remains the standing
# witness; a refusal of the new token is a data event with a name, not a
# reason to put the old one back.
UA_ROSTER_BOT = "districtry.com roster bot (civic data; contact via site)"

# What a bare `urllib.request.urlopen(url)` call sends, so a robots read can be
# made with the SAME client that will crawl. Dozens of this fleet's builders
# fetch that way and set no User-Agent at all, so the string is urllib's own and
# no robots group names it -- `*` binds, which is the answer either way. Stating
# it is the honest reading; RENAMING those callers to a districtry token is a
# different change and needs its own per-host measurement (CLAUDE.md: a rename is
# licensed by a measurement at the page the scraper reads).
UA_STDLIB_DEFAULT = "Python-urllib/%d.%d" % sys.version_info[:2]
UA_ROSTER_COMPACT = "Mozilla/5.0 (compatible; districtry-roster/1.0)"


# The same honest reading one stack over: what a bare `requests.get(url)` call
# sends when the caller sets no headers. A dozen builders in this fleet fetch that
# way, and a robots read has to be made with the SAME client that will crawl, so
# the string is the library's own rather than a districtry token. It is a FUNCTION
# and not a constant because `requests` is imported inside fetch() on purpose --
# see the module docstring -- and a module-level constant would drag the
# dependency into every stdlib-only caller of this file. No robots group names
# this string either, so `*` binds, which is the answer either way; stating it
# keeps the reading honest rather than changing the verdict.
def ua_requests_default():
    import requests  # function-local: see the module docstring
    return "python-requests/%s" % requests.__version__

UA_CIVIC_BOT = ("Mozilla/5.0 (compatible; districtry.com civic data bot; "
                "+https://districtry.com/)")


# --- OUR OWN TOKEN, SENT COMPLETELY. The headers a districtry client sends
# beside UA_ROSTER_BOT, kept here as ONE copy because two readers of one
# question is where this fleet's recurring defect starts: probe_user_agents.py
# measures every host with exactly this set and imports it rather than
# restating it, so a scraper switched to the token sends what was measured.
# `Accept-Encoding: identity` for the reason the comment inside says -- the
# stdlib client does not decode for us, and a compressed body measured as-is
# is how validate_card_links.py called a real 1,705-byte page an 805-byte
# hollow one. No `sec-ch-ua*` hints: those belong to the Chrome rung and
# claiming them beside a districtry UA would be a client that does not exist.
UA_HEADERS_ROSTER_BOT = {
    "User-Agent": UA_ROSTER_BOT,
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
}


# --- The stdlib rung: a DIFFERENT HTTP STACK, plus the client hints a real
# Chromium sends beside its UA. Not a disguise — the same claim the fleet's UA
# strings already make, sent completely rather than half.
#
# MEASURED 2026-09-03 across the five Illinois sources recorded as blocked,
# leave-one-out, every cell a live fetch:
#
#     county         requests+bare  requests+hints  stdlib+bare  stdlib+hints
#     Kendall            403            403            403         200 (117 KB)
#     McHenry            403            403            403         200 (200 KB)
#     Adams              403            403            403         200 (164 KB)
#     Chicago BOE        403            403         200 (62 KB)    200 (62 KB)
#     Lake County        403            403         200 (114 KB)   200 (114 KB)
#
# Two signatures. Kendall, McHenry and Adams sit behind Akamai and need BOTH
# the stack and the hints — neither alone moves them. Chicago's and Lake's
# Cloudflare edges need only the stack. And `requests` never succeeds, with or
# without the hints, which is validate_card_links.py's 2026-08-29 Sheboygan
# finding holding for a sixth site: urllib3's TLS ClientHello differs from the
# stdlib ssl module's and these managers fingerprint it, so no header tweak on
# the requests stack reproduces anything.
#
# THIS IS A RUNG, NOT AN ANSWER TO A CHALLENGE. A Cloudflare managed challenge
# (CPD's, measured 403 to both stacks on the same day) is a question the site
# is entitled to ask, and nothing here tries to solve one.
UA_HINTS_CHROME_126 = {
    "User-Agent": UA_CHROME_WIN_126,
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    # identity, not gzip: the stdlib client does not decode for us, and a
    # compressed body measured as-is is how validate_card_links called a real
    # 1,705-byte page an 805-byte hollow one.
    "Accept-Encoding": "identity",
    "sec-ch-ua": '"Chromium";v="126", "Not;A=Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def fetch_stdlib(url, headers=None, timeout=30):
    """GET through the stdlib stack, returning decoded text, or raising.

    Deliberately NOT a retry loop: this is the second opinion a caller reaches
    for after its own rung was refused, and a refusal here is an answer rather
    than a hiccup. Callers that want pacing already have fetch() above.
    """
    import urllib.request  # function-local, mirroring fetch()'s requests import

    req = urllib.request.Request(url, headers=dict(headers or UA_HINTS_CHROME_126))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return body.decode("utf-8", "replace")


def _robots_client(verify):
    """A requests session pinned to `verify`, or None for the stdlib reader.

    None keeps the stdlib client every existing caller reads with, so this module
    stays importable where requests is not installed. With a bundle path the read
    goes through requests, which is the only one of the two clients that takes a
    CA bundle per call.
    """
    if verify is None:
        return None
    import requests

    session = requests.Session()
    session.verify = verify
    return session


def require_robots_allowed(url, user_agent, headers=None, label=None, verify=None):
    """Stop the process unless this client may fetch `url` under the host's own
    robots.txt. Returns the reason when permitted, so a caller can log it.

    WHY A SHARED HELPER AND NOT A LINE IN EACH SCRAPER. CLAUDE.md's rule is that
    robots.txt is read before the first fetch of a host, and measured 2026-09-12
    it was enacted by seven files out of a hundred-odd — "a scraper that fetches
    without asking is not yet in breach of anything it read, and is the next
    thing to fix". On 2026-09-25 that came due: www.elections.il.gov publishes
    `User-agent: * / Disallow: /`, `Last-Modified: Thu, 12 Jun 2025`, so ISBE had
    been refusing this project for over a year while SIX FILES REFERENCED IT AND
    THREE FETCHED IT, none of the three asking. Both halves of that sentence are
    load-bearing and an earlier draft of it said only "six ... read it": the
    other three write an `elections.il.gov` `resultsUrl`/`mapUrl` into their
    output as provenance and never request it, so A CITATION IS NOT A FETCH and
    nothing about them changes. This is the seam the three ask through, so the
    rule has one reading rather than one per caller.

    IT RAISES RATHER THAN RETURNING FALSE. A refusal that a caller can carry on
    past is a refusal the caller will carry on past — on a rushed edit, in an
    `except`, or because the return value reads like a warning. The only correct
    response to a `*` Disallow is not to fetch, so that is the only response this
    offers. CLAUDE.md: "A `*` group that disallows binds this project fully."

    It is NOT wired into `fetch()` or `fetch_stdlib()`, deliberately. Those two
    are called by most of the fleet's scrapers against hosts whose policies have
    never been read here; switching enforcement on inside them would stop an
    unmeasured number of working refreshes in one commit, which is a different
    change from obeying a refusal this project has measured. Adopt this per
    caller, with the measurement recorded, the way the user-agent rungs were.

    `verify` IS THE TRUST STORE THE CRAWL USES, and a caller with a pinned CA
    bundle must pass it. Four hosts in this fleet serve only their leaf
    certificate -- www.ilga.gov, www.colesco.illinois.gov, gallatinco.illinois.gov
    and www.vercounty.org -- so every automated client reports a verification
    failure while a browser notices nothing, and each of those scrapers already
    completes the chain itself from `scripts/aia_bundle.py`'s pinned intermediate.
    Read with the stdlib client instead, their robots.txt is UNREACHABLE, which
    RFC 9309 2.3.1.4 disallows: measured from a GitHub runner on 2026-09-30, all
    four read that way, so wiring them without this argument would stop four
    working refreshes on a verdict about this reader's trust store rather than
    about anybody's policy. That is the same consistency requirement the
    `headers` argument exists for -- read the policy with the client that
    crawls -- one level further down, in the TLS handshake.

    IT TAKES A BUNDLE PATH AND NOT A SESSION, deliberately. A caller's own
    session may carry cookies, auth or a cleared challenge, and reading a policy
    with a stronger client than the crawl is defeating a control rather than
    measuring one; a CA bundle is the narrow thing these four hosts need and
    cannot carry anything else. Nothing here can disable verification -- the
    path is handed to requests as `verify`, which still verifies.
    """
    from robots_policy import RobotsGate  # scripts/ sibling; stdlib-only

    fail = make_fail(label or "robots")
    ok, why = RobotsGate(_robots_client(verify), user_agent, headers=headers).allows(url)
    if not ok:
        fail("%s refuses this client: %s. Nothing is fetched from it. A refusal "
             "stops the FETCH and never unpublishes what we already have "
             "(CLAUDE.md, Adam's ruling of 2026-09-19), so any file already "
             "built from this host keeps its last-good records and its own "
             "read stamp." % (url, why))
    return why


# Hosts a caller may fetch WITHOUT reading robots.txt, each with the measurement
# that put it here and the reason the reading is deferred rather than taken. This
# is a recorded gap, never a permission: an entry says nobody here has managed to
# read the policy, not that the policy permits.
#
# THE ONE ENTRY IS web.archive.org, the host four Illinois scrapers read a
# snapshot's own bytes from on their terminal fetch rung. Measured 2026-09-30
# through robots_policy's reader, it resets the connection on every attempt from
# this project's sandbox — three reads through the shared reader and a plain curl
# alike. An unreachable robots.txt is RFC 9309 2.3.1.4, which disallows, so
# wiring that reading would stop four working weekly refreshes on a verdict about
# this sandbox's route rather than about the Archive's policy. The honest fix is
# to measure it from a GitHub runner, which can reach the host, and then wire it.
#
# ITS SIBLING archive.org IS NOT HERE AND IS GATED NORMALLY: the same run read a
# 238-byte policy from it in which no rule matches /wayback/available. Two hosts,
# two different answers, so only the one that could not be read is deferred.
#
# THE RUNNER MEASUREMENT THIS ENTRY ASKS FOR WAS TAKEN ON 2026-09-30 AND DID NOT
# INCLUDE THIS HOST, because `probe_robots_verdicts.py` read the host list through
# `probe_user_agents.subject_hosts` -- the browser-string subject -- which does not
# carry it, and nothing thought to add the deferred hosts to a probe whose whole
# purpose these entries name. That probe asks them now, so the next dispatch
# answers this entry rather than measuring around it.
# EMPTY, AND THAT IS A MEASUREMENT RATHER THAN AN OMISSION. web.archive.org was
# the one entry: its robots.txt reset the connection on every read from this
# sandbox (3 reads through the shared reader plus a plain curl), and an
# unreachable robots.txt disallows under RFC 9309 2.3.1.4, so wiring that reading
# would have stopped four working weekly refreshes on a verdict about this
# sandbox's route rather than about the Archive's policy. The entry named a
# runner measurement as the fix it was waiting for, and that measurement was
# taken on 2026-09-30: HTTP 404 — no policy, allow all — from the runner AND,
# re-read the same day, from this sandbox too. Two vantages, one answer, so the
# deferral is retired rather than re-dated, and every caller now asks.
#
# AN ENTRY HERE IS NOT A PERMISSION. It records that a host is fetched without a
# robots read and why, and `require_robots_once` prints "NOT READ" for it, so the
# next pass can tell a host nobody here can read from one nobody asked.
ROBOTS_DEFERRED_HOSTS = {}


def robots_deferred(url):
    """The recorded reason this url's host is fetched without a robots read, or
    None when the host must be asked. Callers print the reason, so a deferral is
    visible in the log of every run rather than silent."""
    from urllib.parse import urlsplit

    return ROBOTS_DEFERRED_HOSTS.get(urlsplit(url).hostname or "")


_ROBOTS_ASKED = set()


def require_robots_once(url, user_agent, headers=None, label=None, out=None,
                        verify=None):
    """Ask this url's host for its robots.txt the first time a run reaches it,
    then let the fetch proceed; a later url on the same host costs nothing.

    WHY THIS EXISTS RATHER THAN A HELPER PER SCRAPER. `require_robots_allowed`
    above is the seam that reads the policy, and every caller wired to it so far
    has wrapped it in the same eight lines: a module-level set of hosts already
    asked, a `urlsplit` to get the host, the call, a line to stderr. When this was
    written, `scripts/validate_robots_adoption.py` measured 224 of this fleet's
    266 fetching scripts unwired, so that wrapper was about to be written another
    224 times — and two copies of one question is where this fleet's recurring
    defect starts. One copy, one reading. THE FIGURE MOVES WITH EVERY BATCH, so
    read today's off that gate's own OK line rather than out of this paragraph.

    THE MEMO IS KEYED ON (host, user_agent), not on the host alone. Which client
    crawls decides which robots group binds, so one host asked with two clients
    is two different questions; keying on the host would answer the second from
    the first client's verdict.

    `verify` is the CA bundle the caller's own fetches use, passed straight
    through; see `require_robots_allowed` for the four hosts that cannot be read
    without one. THE MEMO DOES NOT KEY ON IT, because a bundle changes whether the
    file can be READ and never which group binds, so two reads of one host with
    and without it are the same question and the answer that arrived is the one to
    keep.

    It raises exactly as `require_robots_allowed` does — a refusal is not
    something a caller may carry on past — and honours `ROBOTS_DEFERRED_HOSTS`,
    printing the recorded reason so a deferral is visible in the log of every run
    rather than silent. Returns the reason string either way, so a caller that
    wants to log it itself can.
    """
    from urllib.parse import urlsplit

    stream = out if out is not None else sys.stderr
    host = urlsplit(url).hostname or ""
    key = (host, user_agent)
    deferred = robots_deferred(url)
    if deferred:
        if key not in _ROBOTS_ASKED:
            print("robots.txt %s: NOT READ — %s" % (host, deferred), file=stream)
            _ROBOTS_ASKED.add(key)
        return deferred
    if key in _ROBOTS_ASKED:
        return "already asked this run"
    why = require_robots_allowed(url, user_agent, headers=headers, label=label,
                                 verify=verify)
    print("robots.txt %s: %s" % (host, why), file=stream)
    _ROBOTS_ASKED.add(key)
    return why


def output_path(default, usage=None):
    """The output path a scraper was told to write, or `default`.

    WHY THIS EXISTS, MEASURED. Seventeen scrapers read their output path as a
    bare `sys.argv[1]`, so a FLAG in that position was taken as a filename and
    the payload was written to a file named after the flag. On 2026-10-01 two
    such files were found committed at the top of this repository, `--help` and
    `--out`, byte-identical copies of Macon County's board payload: somebody
    asked a scraper for its usage and it answered by writing a file, and
    somebody spelled the path as an option and it believed them. Neither run
    failed, so nothing said anything was wrong.

    A leading `-` is never a path a caller meant, so it is refused rather than
    written to, and `-h`/`--help` prints the usage it was asking for. Exit 2 is
    the shell's own convention for a usage error, which keeps it distinct from
    the exit 1 a scrape failure uses.
    """
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(usage or ("usage: %s [OUTPUT.json]   (default: %s)"
                        % (os.path.basename(sys.argv[0]),
                           default if default else "stdout only, no file")))
        sys.exit(0)
    if args and args[0].startswith("-"):
        print("%s: %r is not an output path. This script takes the path as a "
              "bare argument, with no option name; pass --help for usage."
              % (os.path.basename(sys.argv[0]), args[0]), file=sys.stderr)
        sys.exit(2)
    return args[0] if args else default


def make_fail(label):
    """The fleet's one failure voice: '<label>: FAIL — <msg>' to stderr, exit 1.

    Byte-identical output to the 93 inline copies this replaces; the label is
    the county/script slug those copies hard-coded.
    """
    def fail(msg):
        print("%s: FAIL — %s" % (label, msg), file=sys.stderr)
        sys.exit(1)
    return fail


def fetch(url, headers, timeout=60, attempts=5, retry_after_cap=30.0, verify=None):
    """GET with the fleet's pacing rules, modeled on henry_county_board_scraper
    (the 2026-08-02 back-to-back-429 story): 429 and 5xx are retried, honouring
    a numeric Retry-After capped at retry_after_cap so a hostile value cannot
    hang CI; 401/403/404 raise immediately — a moved or refused page is not
    fixed by waiting. Returns the requests Response (callers take .text or
    .content). Raises RuntimeError after `attempts` failures.

    `verify` passes through to requests untouched (None means the library
    default — verification ON); pinned-CA callers hand in the bundle path
    aia_bundle.ca_bundle() built. Nothing here can disable verification.
    """
    import requests  # function-local: see the module docstring

    last = None
    for attempt in range(attempts):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=verify)
            if resp.status_code == 429 or resp.status_code >= 500:
                # Retry-After may be seconds or a date; only the numeric form
                # is honoured.
                after = (resp.headers.get("Retry-After") or "").strip()
                delay = min(float(after), retry_after_cap) if after.isdigit() \
                    else 2.0 * (attempt + 1)
                last = "HTTP %d" % resp.status_code
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if getattr(exc.response, "status_code", None) in (401, 403, 404):
                raise
            last = str(exc)
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError("failed to fetch %s after %d attempts: %s"
                       % (url, attempts, last))


# --- Did anything move besides the timestamp? -------------------------------
#
# Nine Illinois data files carry a TOP-LEVEL `generated` stamp that is rewritten
# on every run, so each weekly workflow's `git diff` sees a change whether or
# not an officeholder did, and opens a bot PR every week. The stamp is correct
# and stays: it records when the source was last read, which is exactly what a
# reader of a card's "as filed" line needs. What was missing is a line saying
# whether anything ELSE moved, so a reviewer opening the PR can tell an empty
# refresh from a real one without reading the diff.
#
# This is ia/scripts/build_ia_county_chair.py's `substantive_changes` for a
# different shape, and that function's own docstring already says the Illinois
# AFR files have it. Iowa excludes a PER-RECORD field (`confirmedOn`) from a
# flat {fips -> record} map; here the excluded key is TOP-LEVEL and the records
# sit one to three levels down inside a container.
#
# DEPTH IS STATED BY THE CALLER, NEVER DERIVED, and the reason is measured
# rather than stylistic: the records themselves contain dict-valued fields
# (`boone-district-officials`'s records hold one, `il-special-district-
# officials`'s hold `board` lists and more), so "descend until the value is not
# a dict" walks INTO a record and compares its fields as if they were records.
# `check_roster_retention.py`'s SOURCE_KEY_PREFIX states its width for the same
# reason.
#
# THE TWO WRONG DEPTHS FAIL DIFFERENTLY, and only one of them is guarded:
#
#   TOO DEEP (2 where the shape is 1) descends into a record and meets a field
#   whose value is not a dict. `flatten_records` RAISES. This is the direction
#   that would otherwise compare a record's fields as if each were a record,
#   and the guard for it is total.
#
#   TOO SHALLOW (2 where the shape is 3) treats a container level as a record.
#   It does NOT raise and it is not detectable here: the obvious test — "a
#   record has at least one non-dict value, a container level does not" — is
#   FALSE of this data. Measured across the nine files, 6 of 1,148 records have
#   all-dict values (three of them `Arcola`, `Assumption` and `Bushnell Public
#   Library District` in il-library-contacts), so that test would reject six
#   real records. What a too-shallow depth actually costs is PRECISION, not
#   correctness: the comparison is still `was == now` over the same subtree, so
#   "did anything move" stays right and only the NAME in the line gets shorter.
#   That is why it is documented rather than guarded, and why the nine call
#   sites state a depth that was measured against the shipped file.
#
# WHAT A DOCTORED-INPUT PROOF OF THIS CAN AND CANNOT BE, because the
# distinction was blurred once already. Calling substantive_changes()
# directly proves the HELPER; running a builder end to end proves the
# helper AND its call site. Those are not interchangeable, and for some
# builders only the first is available: an add-or-remove case cannot reach
# this code through build_boone_district_officials.py at all, because that
# builder's check() refuses any roster whose keys are not exactly the
# `district` values of the two shipped geometry files — the doctored payload
# dies at the geometry gate, which is that gate working. So a line reported
# for such a builder is this function's output on that builder's real data,
# never a record of a build that ran; say which when quoting one.

def flatten_records(container, depth, *, path=()):
    """{'a.b.c': record} from a container nested exactly `depth` keys deep.

    Raises ValueError when the shape does not match, which is what makes a
    stated depth safe to rely on.
    """
    if depth < 1:
        raise ValueError("depth must be at least 1, got %r" % (depth,))
    if not isinstance(container, dict):
        raise ValueError("expected a dict at %r, found %s"
                         % (".".join(path), type(container).__name__))
    out = {}
    for key, value in container.items():
        here = path + (str(key),)
        if depth == 1:
            if not isinstance(value, dict):
                raise ValueError("expected a record (dict) at %r, found %s"
                                 % (".".join(here), type(value).__name__))
            out[".".join(here)] = value
        else:
            out.update(flatten_records(value, depth - 1, path=here))
    return out


def substantive_changes(prior, out, container, depth, stamp_key="generated",
                        max_named=12):
    """Did anything move besides `stamp_key`? -> (lines, summary).

    `prior` and `out` are whole payloads. `container` is the key holding the
    records and `depth` how many key levels sit between it and one record.
    `lines` are per-record log lines; `summary` is one sentence for a PR body,
    written so a reviewer can stop reading there when nothing moved.
    """
    before = flatten_records(prior.get(container) or {}, depth)
    after = flatten_records(out.get(container) or {}, depth)

    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = []
    for key in sorted(set(before) & set(after)):
        was, now = before[key], after[key]
        if was == now:
            continue
        fields = sorted(k for k in set(was) | set(now) if was.get(k) != now.get(k))
        changed.append((key, fields))

    # A top-level key other than the stamp can move too — a renamed source, a
    # moved officials page — and that is a real change a reviewer should see.
    meta = sorted(k for k in (set(prior) | set(out)) - {container, stamp_key}
                  if prior.get(k) != out.get(k))

    lines = []
    lines += ["  ADDED %s" % k for k in added]
    lines += ["  REMOVED %s" % k for k in removed]
    lines += ["  CHANGED %s: %s" % (k, ", ".join(f)) for k, f in changed]
    lines += ["  CHANGED (payload) %s" % k for k in meta]

    n = len(added) + len(removed) + len(changed) + len(meta)
    if not n:
        summary = ("Nothing moved but the `%s` stamp — this refresh re-read the "
                   "same records and rewrote only the timestamp." % stamp_key)
        return lines, summary

    parts = []
    if added:
        parts.append("%d added" % len(added))
    if removed:
        parts.append("%d removed" % len(removed))
    if changed:
        parts.append("%d changed" % len(changed))
    if meta:
        parts.append("%d payload field(s)" % len(meta))
    named = [k for k in added] + [k for k in removed] + [k for k, _ in changed]
    shown = "; ".join(named[:max_named])
    if len(named) > max_named:
        shown += "; and %d more" % (len(named) - max_named)
    summary = ("%s, besides the `%s` stamp%s"
               % (", ".join(parts), stamp_key, (": " + shown) if shown else "."))
    if shown:
        summary += "."
    return lines, summary


def emit_changes_output(summary):
    """Write `changes=<summary>` to $GITHUB_OUTPUT when running under Actions.

    Consumed through `env:` in the workflow, never interpolated into a shell
    command. One line, so a newline in the summary would break the format.
    """
    out_file = os.environ.get("GITHUB_OUTPUT")
    if not out_file:
        return False
    with open(out_file, "a", encoding="utf-8") as fh:
        fh.write("changes=%s\n" % summary.replace("\n", " "))
    return True


# --- self-test ---------------------------------------------------------------

def _selftest():
    """Prove the what-moved line BOTH ways on doctored input.

    The failure this guards is silent in the worst way: a helper that always
    said "nothing moved" would read as a clean week forever, and a reviewer
    trusting the line would stop opening diffs. So the quiet answer and the
    loud one are both asserted, and so is the refusal that makes a STATED
    depth safe.
    """
    fails = []

    def ok(label, got, want):
        if got != want:
            fails.append("%s\n     got  %r\n     want %r" % (label, got, want))

    flat = {"generated": "2026-01-01T00:00:00Z", "source": "S",
            "districts": {"ALPHA FIRE": {"kind": "fire", "chief": "A. One"},
                          "BETA FIRE": {"kind": "fire", "chief": "B. Two"}}}

    # 1. ONLY THE TIMESTAMP MOVED — the week this whole change exists for.
    later = json.loads(json.dumps(flat)); later["generated"] = "2026-02-02T00:00:00Z"
    lines, summary = substantive_changes(flat, later, "districts", 1)
    ok("only the stamp moved: no lines", lines, [])
    ok("only the stamp moved: summary", summary,
       "Nothing moved but the `generated` stamp — this refresh re-read the same "
       "records and rewrote only the timestamp.")

    # 2. ONE NAME CHANGED — must name the record and the field.
    one = json.loads(json.dumps(later)); one["districts"]["BETA FIRE"]["chief"] = "B. Three"
    lines, summary = substantive_changes(flat, one, "districts", 1)
    ok("one field moved: lines", lines, ["  CHANGED BETA FIRE: chief"])
    ok("one field moved: summary", summary,
       "1 changed, besides the `generated` stamp: BETA FIRE.")

    # 3. ADDED and REMOVED are counted and named separately from CHANGED.
    both = json.loads(json.dumps(later))
    both["districts"].pop("ALPHA FIRE")
    both["districts"]["GAMMA FIRE"] = {"kind": "fire", "chief": "C. Four"}
    lines, summary = substantive_changes(flat, both, "districts", 1)
    ok("added+removed: lines", lines, ["  ADDED GAMMA FIRE", "  REMOVED ALPHA FIRE"])
    ok("added+removed: summary", summary,
       "1 added, 1 removed, besides the `generated` stamp: GAMMA FIRE; ALPHA FIRE.")

    # 4. A TOP-LEVEL KEY THAT IS NOT THE STAMP still counts as movement.
    meta = json.loads(json.dumps(later)); meta["source"] = "S2"
    lines, summary = substantive_changes(flat, meta, "districts", 1)
    ok("payload field moved: lines", lines, ["  CHANGED (payload) source"])
    ok("payload field moved: summary", summary,
       "1 payload field(s), besides the `generated` stamp.")

    # 5. NESTED, the il-special-district-officials shape: depth 3.
    deep = {"generated": "t0", "counties": {"adams": {"fire": {"Barry Fire": {"chief": "X"}}}}}
    deep2 = json.loads(json.dumps(deep)); deep2["generated"] = "t1"
    deep2["counties"]["adams"]["fire"]["Barry Fire"]["chief"] = "Y"
    lines, summary = substantive_changes(deep, deep2, "counties", 3)
    ok("depth 3: lines", lines, ["  CHANGED adams.fire.Barry Fire: chief"])

    # 6. TOO DEEP RAISES — the guarded direction, and the one that would
    #    otherwise compare a record's own fields as if each were a record.
    try:
        flatten_records(deep["counties"], 4)
        fails.append("depth 4 on a depth-3 container should have raised")
    except ValueError:
        pass

    # 7. TOO SHALLOW DOES NOT RAISE, and that is recorded rather than pretended
    #    otherwise (see the note above: the test that would catch it is false of
    #    6 of the 1,148 real records). It still answers "did anything move"
    #    correctly, because the comparison is over the same subtree — it only
    #    names the change less precisely. Both halves are asserted so a future
    #    change cannot quietly make the shallow answer WRONG rather than vague.
    shallow = flatten_records(deep["counties"], 2)
    ok("too-shallow flattens to the level above", sorted(shallow), ["adams.fire"])
    lines, summary = substantive_changes(deep, deep2, "counties", 2)
    ok("too-shallow still detects the change", lines, ["  CHANGED adams.fire: Barry Fire"])

    # 8. Records legitimately CONTAIN dicts, so a derived depth would descend
    #    into one. Stating 1 here is right and stating 2 must refuse.
    withdict = {"districts": {"A": {"kind": "fire", "office": {"city": "Belvidere"}}}}
    ok("record with a dict field flattens at the stated depth",
       sorted(flatten_records(withdict["districts"], 1)), ["A"])
    try:
        flatten_records(withdict["districts"], 2)
        fails.append("depth 2 should have refused a record whose fields are not records")
    except ValueError:
        pass

    # --- require_robots_once: asked once per (host, client), offline ---------
    #
    # Stubbed at the seam rather than at the network, because what is under test
    # is the memo and the deferral, not the reading. The real reading has its own
    # gate (robots_policy.py --selftest, 20 assertions against saved bytes).
    global require_robots_allowed
    real_seam, asked = require_robots_allowed, []

    def _stub(url, user_agent, headers=None, label=None, verify=None):
        asked.append((url, user_agent, verify))
        if "refuses" in url:
            make_fail(label or "robots")("stubbed refusal")
        return "stubbed allow"

    require_robots_allowed = _stub
    try:
        _ROBOTS_ASKED.clear()
        log = io.StringIO()
        for _ in range(3):
            require_robots_once("https://example.test/a", "token", out=log)
        require_robots_once("https://example.test/b", "token", out=log)
        if len(asked) != 1:
            fails.append("one host with one client should reach the seam once, "
                         "reached it %d time(s)" % len(asked))
        if len(log.getvalue().strip().splitlines()) != 1:
            fails.append("a host asked once should print one line")
        require_robots_once("https://example.test/a", "chrome", out=log)
        if len(asked) != 2:
            fails.append("a second client on the same host is a second question")
        require_robots_once("https://other.test/a", "token", out=log)
        if len(asked) != 3:
            fails.append("a second host should be asked")
        # THE CA BUNDLE REACHES THE SEAM. Four hosts serve only their leaf
        # certificate and cannot be read without one, so a `verify` that is
        # accepted and then dropped is a gate that refuses those four for a
        # reason that has been fixed.
        require_robots_once("https://pinned.test/a", "token", out=log,
                            verify="/tmp/bundle.pem")
        if asked[-1][2] != "/tmp/bundle.pem":
            fails.append("verify must reach require_robots_allowed; the seam saw "
                         "%r" % (asked[-1][2],))
        # AND IT IS NOT PART OF THE MEMO'S KEY: a bundle changes whether the file
        # can be read, never which group binds, so the same host asked again with
        # the same client is the same question and must not be re-read.
        before = len(asked)
        require_robots_once("https://pinned.test/b", "token", out=log)
        if len(asked) != before:
            fails.append("a bundle must not split the memo: one host and one "
                         "client is one question")

        # A STUBBED ENTRY, NEVER A LIVE ONE. This case used to name
        # web.archive.org out of the table above, so retiring that entry for the
        # right reason turned the selftest red -- a test that dies when the thing
        # it tests is correctly fixed. The behaviour under test is the table's,
        # not any one host's.
        _ROBOTS_ASKED.clear()
        del asked[:]
        log = io.StringIO()
        reason = "selftest: stubbed deferral"
        ROBOTS_DEFERRED_HOSTS["deferred.test"] = reason
        for _ in range(2):
            why = require_robots_once(
                "https://deferred.test/a", "token", out=log)
        del ROBOTS_DEFERRED_HOSTS["deferred.test"]
        if asked:
            fails.append("a deferred host must not reach the seam")
        if why != reason:
            fails.append("a deferred host should return its recorded reason")
        if len(log.getvalue().strip().splitlines()) != 1:
            fails.append("a deferred host should print its reason once")
        if "NOT READ" not in log.getvalue():
            fails.append("a deferral must read as unread, not as a permission")

        _ROBOTS_ASKED.clear()
        try:
            require_robots_once("https://example.test/refuses", "token",
                                label="selftest-robots",
                                out=io.StringIO())
            fails.append("a refusal must stop the process, not return")
        except SystemExit:
            pass
    finally:
        require_robots_allowed = real_seam
        _ROBOTS_ASKED.clear()

    # --- output_path: a flag is never a filename -----------------------------
    # The defect this guards WROTE FILES, so every case asserts what the helper
    # does with a flag rather than only that it complains. A plain path must
    # still pass through untouched, or seventeen scrapers lose their argument.
    real_argv = sys.argv
    try:
        for flag in ("-h", "--help"):
            sys.argv = ["scrape.py", flag]
            buf, real_out = io.StringIO(), sys.stdout
            sys.stdout = buf
            try:
                output_path("default.json")
                fails.append("%s must exit, not return a path" % flag)
            except SystemExit as exc:
                if exc.code != 0:
                    fails.append("%s is a request, not an error: expected "
                                 "exit 0, got %r" % (flag, exc.code))
            finally:
                sys.stdout = real_out
            if "usage" not in buf.getvalue():
                fails.append("%s must print the usage it asked for" % flag)
            if "default.json" not in buf.getvalue():
                fails.append("%s should name the default output" % flag)

        # THE CASE THAT ACTUALLY HAPPENED: `--out somewhere.json`, where the
        # option name itself became the filename.
        for argv in (["scrape.py", "--out", "real.json"],
                     ["scrape.py", "-o"],
                     ["scrape.py", "--outfile=real.json"]):
            sys.argv = argv
            buf, real_err = io.StringIO(), sys.stderr
            sys.stderr = buf
            try:
                got = output_path("default.json")
                fails.append("%r must be refused, not written to; got %r"
                             % (argv[1], got))
            except SystemExit as exc:
                if exc.code != 2:
                    fails.append("a usage error is exit 2, distinct from a "
                                 "scrape failure's 1; got %r" % (exc.code,))
            finally:
                sys.stderr = real_err
            if argv[1] not in buf.getvalue():
                fails.append("the refusal must name the argument it refused")

        sys.argv = ["scrape.py", "out/real.json"]
        if output_path("default.json") != "out/real.json":
            fails.append("a plain path must pass through unchanged")
        sys.argv = ["scrape.py"]
        if output_path("default.json") != "default.json":
            fails.append("no argument must give the default")
        # A SCRAPER THAT WRITES NOTHING BY DEFAULT (Will County) passes None,
        # and None must survive rather than becoming the string "None".
        if output_path(None) is not None:
            fails.append("a None default must stay None")
    finally:
        sys.argv = real_argv

    if fails:
        print("scraper-common selftest: FAIL", file=sys.stderr)
        for f in fails:
            print("  - %s" % f, file=sys.stderr)
        return 1
    print("scraper-common selftest: OK — the what-moved line is proven both "
          "ways (quiet week, changed record, add/remove, payload field, depth 3) "
          "too deep refuses, too shallow stays correct but vaguer; "
          "robots is asked once per host per client, a deferral reads as "
          "unread, a refusal stops the process; a flag in the output-path "
          "position is refused rather than written to, and --help prints")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(_selftest())
    raise SystemExit("scraper-common: this module is imported, not run "
                     "(only --selftest does anything)")
