#!/usr/bin/env python3
"""
Measure which county and city hosts actually refuse this project's own
user-agent, so that the files sending a browser string (106 on 2026-09-12; `--inventory`
prints the count and the per-file tally) can say whether they need one.

WHY THIS EXISTS
---------------
CLAUDE.md's honesty rules (settled 2026-09-11) allow a scraper to send a browser
string where a site refuses the districtry token by client fingerprint, on two
conditions: the calling file records which token was refused, what the site
answered, and the date — "so a later pass can tell a site that needs this from
one nobody tested" — and robots.txt still binds. scripts/scraper_common.py says
the same thing from the other side: its UA constants "consolidate the
DEFINITION, never the VALUE", because "several sites in this fleet block or
challenge by client fingerprint" and nobody had measured which.

Measured 2026-09-12: 290 hosts are reached by a caller that sends a browser
string, and almost none of them had such a measurement on file. This script is
that measurement.

THE TWO AXES, AND WHY ONE IS NOT ENOUGH
---------------------------------------
scripts/scraper_common.py's 2026-09-03 leave-one-out table shows the HTTP STACK
is refused as often as the token: `requests` never succeeded against five
Illinois sources with or without browser headers, while the stdlib client did,
because urllib3's TLS ClientHello differs from the ssl module's and these edges
fingerprint it. A probe that varied only the user-agent would report "this host
refuses the token" about a host that refuses a stack, and a browser string would
be credited with a fix it did not make. So every refusal is retried across both
axes, cheapest cell first, stopping the moment something answers:

    1. requests + districtry token      <- what a scraper should send
    2. stdlib   + districtry token      <- same claim, different stack
    3. requests + Chrome/126 + hints
    4. stdlib   + Chrome/126 + hints    <- what the browser-string files send

A host that answers cell 1 needs no browser string. One that answers cell 2
needs a different STACK, not a different name. Only a host that answers 3 or 4
and refuses 1 and 2 has refused the token itself.

WHAT IT WILL NOT DO
-------------------
robots.txt is read before the first fetch of a host and re-read with each rung's
own client until one can read it — sending a weaker client than the crawl is the
one asymmetry a compliance check must not have. A path the `*` group disallows
is never fetched, and the host is reported unmeasured rather than probed. A
captcha or managed challenge is an access control: it is recorded and never
answered. Nothing here disables TLS verification.

TWO THINGS THIS GOT WRONG FIRST, BOTH RECORDED BECAUSE THE SECOND WAS A
CONFIDENT WRONG ANSWER RATHER THAN AN ERROR
-------------------------------------------------------------------------
The first draft read robots.txt once, with rung 1's client. Marathon, McHenry
and DeKalb refuse that client the FILE, so their policies were filed unreadable
while rung 4 went on to fetch a page — a crawl whose rules were never read.

The first draft also called any body containing /captcha/ a challenge. It
reported board.danecounty.gov as challenged: the host had served a 7.7 MB page
titled "Dane County District Supervisor List" to the districtry token, and the
match was a CSS rule hiding the reCAPTCHA badge on a contact form. Gating the
keyword on a 60 KB body caught the same error fifteen more times one size down
— www.appletonwi.gov at 58 KB, www.algomacity.org at 51 KB, four Dane County
offices between 23 and 39 KB, every one a real page. So the keyword now decides
nothing: an interstitial is recognised by phrases that appear nowhere else, and
everything else is judged on how much VISIBLE TEXT came back, which is the one
thing a challenge page cannot fake.

THE VANTAGE IS PART OF THE MEASUREMENT
--------------------------------------
A refusal measured here is a fact about the address it was measured from. The
scrapers run in GitHub Actions; this script is written to run there too, and the
artifact records which vantage produced it. A `--check` run makes no requests at
all: it re-audits the artifact against the tree, so an entry cannot outlive the
file that fetched the host.

Usage:
    python3 scripts/probe_user_agents.py --inventory            # list the surface
    python3 scripts/probe_user_agents.py --probe                # measure, write artifact
    python3 scripts/probe_user_agents.py --probe --hosts a,b     # measure a subset
    python3 scripts/probe_user_agents.py --check                # offline re-audit
    python3 scripts/probe_user_agents.py --refresh-callers        # who reaches each host
    python3 scripts/probe_user_agents.py --report out.md         # render the artifact
"""

import argparse
import ast
import concurrent.futures
import datetime
import glob
import gzip
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from scraper_common import (UA_CHROME_WIN_126, UA_HINTS_CHROME_126,  # noqa: E402
                            UA_ROSTER_BOT)

ARTIFACT = os.path.join(ROOT, "user-agent-measurements.json")

INSTANCES = ("il", "ny", "ca", "wi", "ia", "mi")


# --- robots.txt: ONE COPY, at scripts/robots_policy.py (RFC 9309: every group
# naming the fetching client, merged, else every `*` group, merged; longest
# match wins; Crawl-delay and Content-Signal read from the binding groups).
#
# This module used to load wi/scripts/validate_robots.py by file path, then for
# part of 2026-09-12 imported a `robots_rules` module that carried that audit's
# `*`-only parser. Both are retired: a reader that evaluates only `*` cannot
# see a group a site writes for this client's own token, and this probe reads
# each host's policy with the RUNG'S client, so the token that fetches is the
# token the policy is asked about.
# `classify` is imported under its own name because this module defines a
# `classify(code, body, headers)` of its own for PAGE responses (line ~438),
# and the bare import was shadowed by it: read_robots() called the page
# classifier with two arguments and every --probe run raised TypeError from
# 2026-09-12 (#886) until #917 found it. Nothing offline exercised the
# robots-read path; --selftest now does.
from robots_policy import RobotsPolicy, resolve_template  # noqa: E402
from robots_policy import classify as robots_verdict  # noqa: E402

# --- what each rung sends.
TOKEN_HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    # identity, not gzip: the stdlib client does not decode for us, and a
    # compressed body measured as-is is how validate_card_links.py called a real
    # 1,705-byte page an 805-byte hollow one.
    "Accept-Encoding": "identity",
}
BROWSER_HEADERS = dict(UA_HINTS_CHROME_126)

HARD_CHALLENGE_RE = re.compile(
    r"just a moment|checking your browser|cf-browser-verification|cf_chl_|"
    r"cf-please-wait|attention required! \| cloudflare|_incapsula_resource|"
    r"ddos-guard|px-captcha|/_sec/cp_challenge|sgcaptcha|"
    r"enable javascript and cookies to continue", re.I)
CAPTCHA_WIDGET_RE = re.compile(r"recaptcha|hcaptcha|turnstile", re.I)
# A body this small answers nothing at all (validate_card_links.py's shape).
TINY = 900
MIN_VISIBLE_TEXT = 500

_STRIP_RE = re.compile(r"(?is)<(script|style|noscript|template)\b.*?</\1>")
_TAG_RE = re.compile(r"(?s)<[^>]*>")





def visible_text(text):
    """The characters a reader would see, near enough to count them."""
    body = _TAG_RE.sub(" ", _STRIP_RE.sub(" ", text))
    return re.sub(r"\s+", " ", body).strip()


# --- the surface: every host a script reaches, and what its callers send.
#
# DISCOVERED FROM THE TREE, never from a list: a hand-kept table of what a sweep
# covers is the one thing the sweep cannot check, and this fleet has learned it
# three times (validate_card_links.py naming four instances of five,
# check_roster_retention.py pointed at one instance's data/app,
# validate_robots.py naming three modules of eleven).
SKIP_HOST_RE = re.compile(r"""(?x)
    ^(www\.)?(github\.com|raw\.githubusercontent\.com|api\.github\.com
             |objects\.githubusercontent\.com)$
  | ^(www\.)?(pypi\.org|files\.pythonhosted\.org|npmjs\.com|registry\.npmjs\.org)$
  | ^(cdnjs\.cloudflare\.com|unpkg\.com|cdn\.jsdelivr\.net|code\.jquery\.com)$
  | ^(fonts\.googleapis\.com|fonts\.gstatic\.com)$
  | ^(www\.)?(districtry\.com|chidistricts\.com)$
  | ^(www\.)?(schema\.org|w3\.org|creativecommons\.org|opensource\.org)$
  | ^(localhost|example\.com|example\.org|example\.gov)$
  | ^(web\.archive\.org|archive\.org)$
  | (^|\.)(sectigo\.com|usertrust\.com|godaddy\.com|digicert\.com|entrust\.net
          |amazontrust\.com|pki\.goog|letsencrypt\.org)$
  | ^(cloudflare-dns\.com|dns\.google|one\.one\.one\.one)$
""")
URL_RE = re.compile(r"""https?://[^\s"'<>)\\]+""")

BROWSER_MARKERS = ("UA_CHROME_WIN_126_FULL", "UA_CHROME_WIN_126", "UA_CHROME_WIN_124",
                   "UA_CHROME_X11_128", "UA_CHROME_X11_120", "UA_HINTS_CHROME_126",
                   "fetch_stdlib")
SELF_MARKERS = ("UA_ROSTER_BOT", "UA_ROSTER_COMPACT", "UA_CIVIC_BOT")
SELF_INLINE_RE = re.compile(r"districtry|chidistricts|DistrictExplorer", re.I)
# A SELF-IDENTIFYING TOKEN IS EITHER VERSIONED OR CONTACT-ADDRESSED. The first
# shape was `districtry[-suffix]/N` anywhere in a literal; it missed every
# token written as `districtry <role> (+https://districtry.com/<tag>/)` — the
# form validate_sources.py sends in all six instances, the metro-outline
# builder in four, and the two Illinois board builders that name themselves —
# so validate_sources.py read as `browser` on 51 hosts (found by #910). The
# second shape is anchored at the start of the literal and requires the `(+`
# contact parenthesis, because `districtry` also opens prose ("districtry is
# an independent, unofficial project"), robots fixtures and page titles.
SELF_TOKEN_RE = re.compile(
    r"\bdistrictry[\w.-]*/\d"
    r"|^\s*districtry[\w.-]*\b[^\n]*\(\+https?://", re.I)
# A UA CONSTANT IMPORTED FROM A SIBLING MODULE IS WHAT THE FILE SENDS. Fifteen
# Illinois board builders do `from build_metro_outline import HEADERS`, Shelby's
# reaches vtd_board_districts.get_json, and none of them carries a literal of
# its own — so all read as `unknown` until the import is followed one level.
# Only UA-shaped names are followed, and only into modules in this tree.
IMPORTED_UA_NAME_RE = re.compile(
    r"^(?:[A-Z0-9_]*HEADERS|UA|USER_AGENT|[A-Z0-9_]*_UA|UA_[A-Z0-9_]+)$")
BROWSER_INLINE_RE = re.compile(
    r"Mozilla/5\.0 \((?:Windows NT|X11;|Macintosh;|iPhone|Android)")


def ua_kind(text, path=None):
    """'browser' | 'self' | 'both' | 'unknown' — what this FILE sends.

    READ AS CODE, NOT AS TEXT. A substring scan counts a constant NAMED in a
    docstring as one the file sends, and it caught this sweep's own record
    corrections within the hour: writing "the edge serves the page to the plain
    UA_ROSTER_BOT token" into lake_county_board_roles_scraper.py's docstring
    flipped that file from browser to both, and the host's caller entry changed
    for a paragraph of prose. So the identifiers come from the parsed module —
    imports and referenced names — and the inline literals from string constants
    that are not docstrings. A file that does not parse falls back to the text
    scan, because an unreadable file whose UA goes unclassified is worse than
    one classified loosely.

    Per file, not per URL, and that is the measurement's one coarse edge: a file
    that pins a browser string for two counties and the token for the rest reads
    as 'both', and the sweep cannot say which of its hosts got which. The report
    names them.
    """
    kinds = set()
    names, literals, parsed = _code_symbols(text, path)
    if not parsed:
        names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
        literals = [m.group(1) for m in
                    re.finditer(r'["\']([^"\']*Mozilla/5\.0[^"\']*)["\']', text)]
    if names & set(SELF_MARKERS):
        kinds.add("self")
    if names & set(BROWSER_MARKERS):
        kinds.add("browser")
    for literal in literals:
        if "Mozilla/5.0" not in literal:
            # A plain product token of ours — `districtry/1.0 (+https://…)`,
            # `districtry-wisconsin/1.0` — is what the Iowa and Wisconsin
            # scrapers send, and the first version of this read every one as
            # 'unknown' (317 files), then reported the Iowa judicial scraper's
            # switch from a Chrome string as 'browser -> unknown'.
            if SELF_TOKEN_RE.search(literal):
                kinds.add("self")
            continue
        if SELF_INLINE_RE.search(literal):
            kinds.add("self")          # UA_ROSTER_COMPACT's shape: Mozilla, but ours
        elif BROWSER_INLINE_RE.search(literal):
            kinds.add("browser")
    if kinds == {"browser"}:
        return "browser"
    if kinds == {"self"}:
        return "self"
    if kinds:
        return "both"
    return "unknown"


def _code_symbols(text, path=None):
    """(identifiers, non-docstring string constants, parsed?) for one module.

    With `path`, a UA-shaped name imported from a sibling module in this tree
    contributes that module's string constants for the name — one level, no
    further — so `from build_metro_outline import HEADERS` reads as what
    build_metro_outline.py's HEADERS says.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set(), [], False
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
    names, literals = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.name.split(".")[-1])
                if alias.asname:
                    names.add(alias.asname)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                literals.append(node.value)
    if path:
        literals += _imported_ua_literals(tree, path)
    return names, literals, True


def _imported_ua_literals(tree, path):
    """String constants assigned to UA-shaped names this module imports from
    sibling modules — `from build_metro_outline import HEADERS` → the strings
    inside build_metro_outline.py's `HEADERS = {...}`. Looks in the importing
    file's own directory and the repo's `scripts/` (the two places every
    instance script puts on sys.path); a module not found there contributes
    nothing rather than guessing."""
    out = []
    dirs = [os.path.dirname(os.path.abspath(path)), os.path.join(ROOT, "scripts")]
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module or node.level:
            continue
        wanted = [a.name for a in node.names if IMPORTED_UA_NAME_RE.match(a.name)]
        if not wanted:
            continue
        for d in dirs:
            mod = os.path.join(d, node.module.replace(".", os.sep) + ".py")
            if os.path.exists(mod):
                break
        else:
            continue
        try:
            with open(mod, encoding="utf-8", errors="replace") as f:
                sub = ast.parse(f.read())
        except (OSError, SyntaxError):
            continue
        for stmt in sub.body:
            if not isinstance(stmt, ast.Assign):
                continue
            targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            if not set(targets) & set(wanted):
                continue
            for sub_node in ast.walk(stmt.value):
                if isinstance(sub_node, ast.Constant) and isinstance(sub_node.value, str):
                    out.append(sub_node.value)
    return out


def script_paths():
    out = sorted(glob.glob(os.path.join(ROOT, "scripts", "*.py")))
    for tag in INSTANCES:
        out += sorted(glob.glob(os.path.join(ROOT, tag, "scripts", "*.py")))
    return out


def file_urls(text):
    """Every URL a file names, with adjacent string literals JOINED.

    URL_RE runs over the raw text and stops at a quote, so a URL written as
    two adjacent literals —

        "<scheme>://www.chicago.gov/city/en/depts/dcd/supp_info/"
        "special_service_areasandproviderlist.html"

    — contributed only its first half, a bare directory. Python's own parser
    joins adjacent literals into one Constant, so the AST pass below sees the
    whole address. The regex pass is kept because it also reads comments,
    which the AST does not carry, and the two are unioned.

    A FRAGMENT IS NOT AN ADDRESS. A regex match that is a proper prefix of a
    joined literal, and is not itself a whole literal anywhere in the file, is
    the first half of a split and is dropped — otherwise it would stay a
    candidate and could still be chosen. Found by #928 (2026-09-12): that
    directory answers 403 from Apache to every client, so the probe reported
    www.chicago.gov `all-refused` while the page the scraper reads is a plain
    token refusal.
    """
    regex_found = {m.group(0).rstrip(".,;:%") for m in URL_RE.finditer(text)}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return sorted(regex_found)
    ast_found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for m in URL_RE.finditer(node.value):
                ast_found.add(m.group(0).rstrip(".,;:%"))
    urls = ast_found | regex_found
    return sorted(u for u in urls
                  if u in ast_found
                  or not any(o != u and o.startswith(u) for o in ast_found))


def build_inventory():
    """{host: {"urls": {url: [file]}, "callers": {file: kind}}}"""
    hosts = {}
    for path in script_paths():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        kind = ua_kind(text, path)
        for url in file_urls(text):
            try:
                host = (urllib.parse.urlsplit(url).hostname or "").lower()
            except ValueError:
                continue           # a bracketed-IPv6 shape inside a doc string
            if not host or "." not in host or SKIP_HOST_RE.search(host):
                continue
            # A host built by string formatting is not an address.
            if any(c in host for c in "%{*<("):
                continue
            entry = hosts.setdefault(host, {"urls": {}, "callers": {}})
            entry["urls"].setdefault(url, []).append(rel)
            entry["callers"][rel] = kind
    for entry in hosts.values():
        entry["urls"] = {u: sorted(set(f)) for u, f in sorted(entry["urls"].items())}
    return hosts


def caller_kinds(entry):
    flat = set()
    for kind in entry["callers"].values():
        flat |= {"browser", "self"} if kind == "both" else {kind}
    return flat


def subject_hosts(inventory):
    """The hosts a browser-string caller reaches — the only ones in question."""
    return sorted(h for h, e in inventory.items() if "browser" in caller_kinds(e))


def choose_url(entry):
    """The address to probe: one the scraper actually reads.

    THE PATH, NOT THE FRONT DOOR. An edge that refuses a client usually refuses
    it everywhere, but a path-level refusal answers 200 at the root, and a probe
    that asked only for the root would report "the token works" about the one
    address where it does not.

    A PAGE OVER A DIRECTORY, even a page with a query string, and only then
    the shorter path. The first rank ended on the shortest path, so a bare
    directory (a path ending in `/`) outranked the page beneath it, and a
    directory that denies everyone read as a host that denies the token
    (#928, 2026-09-12). A directory literal is usually the base a scraper
    composes its real requests from; the page or the `?f=json` request is
    what the host actually answers. Shortest-path stays as the tie-break
    among pages. Re-ranking moved the choice on 60 of the 290 measured hosts,
    37 of which had been measured at the first half of a split literal; all
    60 were re-probed on 2026-09-13 (see the per-row `measured`).
    """
    cands = [u for u in entry["urls"] if not re.search(r"%[sd]|[{<]", u)]
    if not cands:
        cands = [resolve_template(u) for u in entry["urls"]]

    def rank(url):
        split = urllib.parse.urlsplit(url)
        path = split.path or "/"
        root = path in ("", "/")
        directory = not root and path.endswith("/")
        return (split.scheme != "https", root, directory, bool(split.query),
                len(path), url)

    return sorted(cands, key=rank)[0]


# --- the two stacks.
def get_requests(url, headers, timeout=25):
    import requests               # function-local, mirroring scraper_common
    r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    return r.status_code, r.content, dict(r.headers), r.url


def get_stdlib(url, headers, timeout=25):
    req = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw, hdrs, code = resp.read(), dict(resp.headers), resp.status
            final = resp.geturl()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        hdrs, code, final = dict(exc.headers or {}), exc.code, url
    if (hdrs.get("Content-Encoding") or "").lower() == "gzip":
        try:
            raw = gzip.decompress(raw)
        except Exception:  # noqa: BLE001
            pass
    return code, raw, hdrs, final


CELLS = (("requests+token", get_requests, TOKEN_HEADERS),
         ("stdlib+token", get_stdlib, TOKEN_HEADERS),
         ("requests+chrome", get_requests, BROWSER_HEADERS),
         ("stdlib+chrome", get_stdlib, BROWSER_HEADERS))


def classify(code, body, headers):
    """('ok'|'refused'|'challenge'|'hollow'|'error', note) for one response."""
    text = body.decode("utf-8", "replace") if body else ""
    ctype = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
    if code == 202:
        return "challenge", "202 (never a document)"
    if code in (401, 403, 406, 451):
        return "refused", "HTTP %d" % code
    if code == 429:
        return "refused", "HTTP 429 (rate-limited; this probe may have caused it)"
    if code == 404:
        return "error", "HTTP 404"
    if code and code >= 500:
        return "error", "HTTP %d" % code
    if code and 200 <= code < 400:
        hit = HARD_CHALLENGE_RE.search(text[:20000])
        if hit:
            return "challenge", "HTTP %d, %r in body" % (code, hit.group(0)[:32])
        if len(body) < TINY:
            return "hollow", "HTTP %d, %d bytes" % (code, len(body))
        # A NON-HTML BODY IS NOT JUDGED BY ITS PROSE. ArcGIS JSON and a canvass
        # PDF carry almost no visible text by construction.
        if "html" in ctype or (not ctype and text.lstrip()[:1] == "<"):
            seen = visible_text(text)
            if len(seen) < MIN_VISIBLE_TEXT:
                return "hollow", "HTTP %d, %d bytes but %d chars of text" % (
                    code, len(body), len(seen))
        note = "HTTP %d, %d bytes" % (code, len(body))
        if CAPTCHA_WIDGET_RE.search(text):
            note += " (page carries a captcha widget)"
        return "ok", note
    return "error", "HTTP %s" % code


def read_robots(getter, headers, scheme, host):
    """([(kind, value)] | None, delay, note) — the `*` group as THIS client reads it.

    None means unread. [] means read and placing no rule on `*`, which permits
    everything — a measured yes, not an assumption.
    """
    url = "%s://%s/robots.txt" % (scheme, host)
    try:
        code, body, _hdrs, _final = getter(url, headers, timeout=20)
    except Exception as exc:  # noqa: BLE001
        return None, None, "unreadable (%s)" % type(exc).__name__
    text = body.decode("utf-8", "replace") if body else ""
    verdict = robots_verdict(code, text)
    ua = headers["User-Agent"]
    if verdict.status == "served":
        policy = verdict.policy
        bound = policy.binding_groups(ua)
        rules = sum(len(g.rules) for g in bound)
        return policy, policy.crawl_delay(ua), "read, %d group(s) bind this client with %d rule(s)" % (len(bound), rules)
    if verdict.status == "absent":
        return RobotsPolicy(""), None, "none (HTTP %s)" % code
    if verdict.status == "refused":
        # 401/403 on robots.txt itself: no readable policy, allowed by default
        # (RFC 9309 §2.3.1.3; the fleet's reading, robots_policy.py's docstring).
        return RobotsPolicy(""), None, "refused to this client (HTTP %s) — no readable policy" % code
    # challenge (202) or unreachable (5xx): this rung may not fetch.
    return None, None, "%s (HTTP %s)" % (verdict.status, code)


def verdict_for(cells):
    kinds = {name: cell["kind"] for name, cell in cells.items()}
    if kinds.get("requests+token") == "ok":
        return "token-ok"
    if kinds.get("stdlib+token") == "ok":
        return "stack-not-token"
    if kinds.get("requests+chrome") == "ok":
        return "token-refused"
    if kinds.get("stdlib+chrome") == "ok":
        return "token-refused-and-stack"
    notes = " ".join(cell["note"] for cell in cells.values())
    if all(k == "error" for k in kinds.values()):
        if "SSLError" in notes or "CERTIFICATE_VERIFY_FAILED" in notes:
            return "tls-chain"
        if "ProxyError" in notes:
            return "proxy-denied"
        if "NameResolution" in notes or "Name or service not known" in notes:
            return "no-dns"
        return "path-answers-nothing"
    if all(k in ("challenge",) for k in kinds.values()):
        return "challenged"
    if all(k == "hollow" for k in kinds.values()):
        return "answers-nothing"
    return "all-refused"


def probe_host(host, url, pace, sleep=None):
    """One host up the ladder, reading its policy with each rung's own client."""
    import time
    sleep = sleep or time.sleep
    out = {"host": host, "url": url, "cells": {}, "robots": {}}
    split = urllib.parse.urlsplit(url)
    scheme = split.scheme or "https"
    path = (split.path or "/") + (("?" + split.query) if split.query else "")

    rules, delay = None, None
    for name, getter, headers in CELLS:
        if rules is None:
            rules, delay, note = read_robots(getter, headers, scheme, host)
            out["robots"][name] = note
            if rules is None:
                # THIS RUNG MAY NOT FETCH. A policy this client could not read
                # (a challenge, a 5xx, a network failure) is disallow-all for
                # it (RFC 9309 §2.3.1.4); the next rung reads with its own
                # client. The first version fetched anyway and the artifact
                # carried 24 such hosts — dekalbcounty.org's robots.txt
                # answered 202 to every client and a page was taken regardless.
                out["cells"][name] = {"kind": "not-fetched",
                                      "note": "robots.txt %s — not fetched by this client" % note}
                continue
            if rules is not None:
                if not rules.allows(headers["User-Agent"], path):
                    out["verdict"] = "robots-disallows-this-path"
                    out["note"] = ("the * group disallows %s — not fetched, so this "
                                   "host carries no user-agent measurement" % path[:90])
                    return out
                if delay:
                    out["robots"]["crawl-delay"] = delay
                if delay and delay > 10:
                    out["verdict"] = "crawl-delay-too-long"
                    out["note"] = ("Crawl-delay: %s — not fetched; four rungs at that "
                                   "pace is not a polite probe" % delay)
                    return out
        sleep(max(pace, delay or 0))
        try:
            code, body, hdrs, _final = getter(url, headers)
            kind, note = classify(code, body, hdrs)
        except Exception as exc:  # noqa: BLE001
            kind, note = "error", "%s: %s" % (type(exc).__name__, str(exc)[:140])
        out["cells"][name] = {"kind": kind, "note": note}
        if kind == "ok":
            break
    if rules is None:
        out["robots"]["policy"] = "unreadable to every client on the ladder"
        out["verdict"] = "robots-unreadable"
        out["note"] = ("robots.txt could not be read by any rung — no page was fetched, "
                       "so this host carries no user-agent measurement")
        return out
    out["verdict"] = verdict_for(out["cells"])
    out["note"] = "; ".join("%s %s" % (n, c["note"]) for n, c in out["cells"].items())
    # A REFUSAL CAN BE THE PATH RATHER THAN THE CLIENT, and the two need
    # different fixes. One extra request at the front door says which.
    if out["verdict"] != "token-ok" and path not in ("", "/"):
        sleep(pace)
        try:
            code, body, hdrs, _final = get_requests("%s://%s/" % (scheme, host),
                                                    TOKEN_HEADERS)
            kind, note = classify(code, body, hdrs)
        except Exception as exc:  # noqa: BLE001
            kind, note = "error", "%s: %s" % (type(exc).__name__, str(exc)[:100])
        out["root"] = {"kind": kind, "note": note}
        if kind == "ok":
            out["note"] += ("; the front door answers the token (%s), so the refusal "
                            "is this path" % note)
    return out


VANTAGE_ENV = ("GITHUB_ACTIONS", "CI")


def vantage():
    if any(os.environ.get(k) for k in VANTAGE_ENV):
        return ("GitHub Actions runner — the vantage the scrapers themselves run "
                "from")
    return ("a Claude Code sandbox, outbound HTTPS through the session's agent "
            "proxy; a refusal measured here is a fact about this address, not "
            "about the host")


def run_probe(args):
    inventory = build_inventory()
    if args.hosts:
        subject = [h for h in args.hosts.split(",") if h.strip() in inventory]
        missing = [h for h in args.hosts.split(",") if h.strip() not in inventory]
        if missing:
            print("probe: not in the inventory, skipped: %s" % ", ".join(missing),
                  file=sys.stderr)
    else:
        subject = subject_hosts(inventory)
    if args.limit:
        subject = subject[:args.limit]
    print("probe: %d host(s), %d worker(s), %.1fs between requests to one host"
          % (len(subject), args.workers, args.pace), file=sys.stderr)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(probe_host, h, choose_url(inventory[h]), args.pace): h
                   for h in subject}
        for done, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            row = fut.result()
            row["callers"] = inventory[row["host"]]["callers"]
            results[row["host"]] = row
            print("%4d/%d  %-26s %-34s %s"
                  % (done, len(subject), row["verdict"], row["host"],
                     row.get("note", "")[:110]), file=sys.stderr)

    prior = None
    if args.merge and os.path.exists(ARTIFACT):
        prior = json.load(open(ARTIFACT))
    payload = merge_measurements(prior, results, datetime.date.today().isoformat(),
                                 full_sweep=not (args.hosts or args.limit))
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False)
        f.write("\n")
    print("\nprobe: wrote %s (%d host(s))" % (os.path.relpath(ARTIFACT, ROOT),
                                              len(payload["hosts"])), file=sys.stderr)
    for verdict, n in sorted(payload["summary"].items(), key=lambda kv: -kv[1]):
        print("  %-28s %4d" % (verdict, n), file=sys.stderr)
    return 0


def merge_measurements(prior, results, today, full_sweep):
    """The artifact to write: this run's rows over the prior artifact's.

    A ONE-HOST RUN IS NOT A SWEEP. The first version stamped `today` on the
    top-level `measured` on every write and rebuilt the payload from scratch,
    so probing one host re-dated 290 rows it never asked and dropped
    `callers_refreshed`, the date --refresh-callers records (#928, 2026-09-12;
    it shipped nothing false only because the artifact already carried that
    day's date). Now every row this run probed carries its own `measured`,
    the top-level `measured` is the date of the last FULL sweep and moves only
    on one, and every other top-level key of the prior artifact is carried
    forward. A row with no `measured` of its own was measured on the top-level
    date — the shape every row had before this.
    """
    merged = dict(prior["hosts"]) if prior else {}
    for host, row in results.items():
        # A HOST THIS PROBE RATE-LIMITED IS NOT A HOST THAT REFUSES US. Rerunning
        # a subset turned www.wcgl.org from a 50 KB page into four 429s, which is
        # this probe's own load and nothing about its policy. An earlier
        # measurement that got a page stands, with the 429 recorded beside it.
        before = merged.get(host)
        if (before and before.get("verdict") == "token-ok"
                and row["verdict"] not in ("token-ok",)
                and "429" in row.get("note", "")):
            before["note"] += ("; a re-probe on %s was rate-limited (429) — this "
                               "probe's own load, not a change of policy" % today)
            continue
        merged[host] = dict(row, measured=today)
    payload = dict(prior) if prior else {}
    payload.update({
        "measured": today if (full_sweep or not prior) else prior["measured"],
        "vantage": vantage(),
        "tokens": {"self": UA_ROSTER_BOT, "browser": UA_CHROME_WIN_126},
        "subject": ("every host reached by a script that sends a browser string; "
                    "hosts reached only by a self-identifying caller are not in "
                    "question and are not probed"),
        "summary": tally(merged),
        "hosts": dict(sorted(merged.items())),
    })
    return payload


def tally(hosts):
    out = {}
    for row in hosts.values():
        out[row["verdict"]] = out.get(row["verdict"], 0) + 1
    return dict(sorted(out.items()))


RETIRED_BRAND_RE = re.compile(r"chidistricts|districtexplorer|district-explorer|district explorer", re.I)
UA_CONSTANT_RE = re.compile(r"^(UA|USER_AGENT|BOT|BROWSER|HONEST_UA|ARCHIVE_UA|[A-Z0-9_]*_UA|UA_[A-Z0-9_]+)$")


def retired_brand_user_agents():
    """[(relpath, string)] for every user-agent POSITION carrying a retired brand.

    Positions, not substrings: a dict value under a "User-Agent" key (a Name
    resolved to a module-level string constant), a module constant whose name
    says it is a UA, the token handed to RobotsGate(), and a user_agent= keyword.
    """
    found = []
    for path in script_paths():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        consts = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    consts[node.targets[0].id] = node.value.value
        def value_of(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.Name):
                return consts.get(node.id)
            return None
        hits = []
        for name, value in consts.items():
            if UA_CONSTANT_RE.match(name):
                hits.append(value)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and str(k.value).lower() == "user-agent":
                        hits.append(value_of(v))
            elif isinstance(node, ast.Call):
                fn = node.func
                fname = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
                if fname == "RobotsGate" and len(node.args) >= 2:
                    hits.append(value_of(node.args[1]))
                for kw in node.keywords:
                    if kw.arg == "user_agent":
                        hits.append(value_of(kw.value))
        for h in hits:
            if h and RETIRED_BRAND_RE.search(h):
                found.append((rel, h))
    return sorted(set(found))


def check(args):
    """Offline: the artifact against the tree. No requests.

    An entry cannot outlive the file that fetched the host, and a host that has
    gained a caller since the measurement cannot sit in the artifact describing a
    different set of files — that is the property EXPECTED_UNREACHABLE and
    ACCEPTED_DROPS already have, and the reason either can be trusted.
    """
    if not os.path.exists(ARTIFACT):
        print("user-agent probe: FAIL — %s is missing; run --probe"
              % os.path.relpath(ARTIFACT, ROOT), file=sys.stderr)
        return 1
    try:
        payload = json.load(open(ARTIFACT))
    except ValueError as exc:
        print("user-agent probe: FAIL — %s is not valid JSON (%s)"
              % (os.path.relpath(ARTIFACT, ROOT), exc), file=sys.stderr)
        return 1
    inventory = build_inventory()
    subject = set(subject_hosts(inventory))
    recorded = payload["hosts"]
    problems, notes = [], []
    # A RETIRED BRAND IN A USER-AGENT POSITION IS A FAILURE. On 2026-09-12 the
    # three shared tokens and nineteen single-file ones still said
    # chidistricts.com, DistrictExplorer or districtexplorer, weeks after the
    # rename; every one was measured host by host and switched (#886). Only
    # UA positions are scanned — a dict value under "User-Agent", a UA-named
    # constant, RobotsGate's token, a user_agent= keyword — because the old
    # domain legitimately survives elsewhere as a redirect heading, an old
    # cache name and the old repository slug.
    for rel, ua_string in retired_brand_user_agents():
        problems.append("%s sends a retired brand as its user-agent: %r — say districtry"
                        % (rel, ua_string[:70]))
    # THE ARTIFACT'S OWN TOKENS ARE A USER-AGENT POSITION TOO. This scan read
    # files only, so `tokens.self` went on saying chidistricts.com roster bot
    # for two days past #886's rename, with --check green (#928, 2026-09-12).
    # A token that is not retired but is no longer the one the constant sends
    # is a NOTE: the measurement was taken with the old string and stands
    # until a sweep re-takes it.
    tokens = payload.get("tokens") or {}
    for which, ua_string in sorted(tokens.items()):
        if ua_string and RETIRED_BRAND_RE.search(ua_string):
            problems.append("the artifact's tokens.%s carries a retired brand: %r — "
                            "re-run --probe, or set it to the string now sent"
                            % (which, ua_string[:70]))
    if tokens.get("self") and tokens["self"] != UA_ROSTER_BOT:
        notes.append("the artifact's tokens.self (%r) is not the token now sent (%r); "
                     "its verdicts were measured with the old string"
                     % (tokens["self"][:60], UA_ROSTER_BOT[:60]))

    for host, row in sorted(recorded.items()):
        if host not in inventory:
            problems.append("%s is recorded but no script names it any more — "
                            "drop the entry" % host)
            continue
        now = inventory[host]["callers"]
        then = row.get("callers", {})
        gained = sorted(set(now) - set(then))
        lost = sorted(set(then) - set(now))
        # A CALLER CAN CHANGE WHAT IT SENDS WITHOUT THE LIST CHANGING, and the
        # first version of this compared filenames only — so switching
        # logan_municipal_officials_scraper.py from a pinned Chrome string to the
        # districtry token, which is the whole point of the measurement, moved
        # nothing here. A switch the other way is the one that matters: a new
        # unjustified browser string on a host somebody already measured.
        switched = sorted("%s (%s -> %s)" % (f, then[f], now[f])
                          for f in set(now) & set(then) if then[f] != now[f])
        if switched:
            notes.append("%s: a caller changed what it sends: %s "
                         "(--refresh-callers records that)"
                         % (host, "; ".join(switched)))
        if gained:
            notes.append("%s gained caller(s) since the measurement: %s "
                         "(a verdict is per host, so the measurement still "
                         "applies; --refresh-callers records that)"
                         % (host, ", ".join(gained)))
        if lost:
            notes.append("%s lost caller(s) since the measurement: %s "
                         "(--refresh-callers records that)"
                         % (host, ", ".join(lost)))
    unmeasured = sorted(subject - set(recorded))
    # AN UNMEASURED HOST REACHED BY A BROWSER-STRING FILE FAILS. The first
    # version made this a NOTE with exit 0, so a fifteenth browser-string file
    # could ship against a host nobody measured and the gate would say OK. A
    # host reached only by files sending their own token stays a NOTE: nothing
    # there needs a measurement to justify.
    for host in unmeasured:
        kinds = set(inventory[host]["callers"].values())
        if kinds & {"browser", "both"}:
            problems.append("%s is reached by a browser-string file (%s) and carries no "
                            "measurement — run --probe for it, or send the token"
                            % (host, ", ".join(f for f, k in sorted(inventory[host]["callers"].items())
                                               if k in ("browser", "both"))))
        else:
            notes.append("%s carries no measurement (its callers send their own token)" % host)
    if payload.get("summary") != tally(recorded):
        problems.append("the summary block does not count the hosts below it")

    for line in notes:
        print("user-agent probe: NOTE — %s" % line)
    if problems:
        for line in problems:
            print("user-agent probe: FAIL — %s" % line, file=sys.stderr)
        return 1
    later = sorted({r["measured"] for r in recorded.values()
                    if r.get("measured") and r["measured"] > payload["measured"]})
    print("user-agent probe: OK — %d host(s) measured %s from %s%s; %d subject "
          "host(s) in the tree"
          % (len(recorded), payload["measured"], payload["vantage"].split(",")[0],
             (", %d re-measured since (latest %s)"
              % (sum(1 for r in recorded.values()
                     if r.get("measured", payload["measured"]) > payload["measured"]),
                 later[-1])) if later else "",
             len(subject)))
    return 0


def refresh_callers(args):
    """Re-read each measured host's caller list from the tree, keeping verdicts.

    A VERDICT IS PER HOST AND A CALLER LIST IS NOT. When a new script reaches a
    host already measured, what the host answers has not changed — only the
    record of who asks. --check reports that as a NOTE so nobody refreshes it
    without looking; this is the looking, recorded with its own date, so ten
    true notes do not become ten permanent lines in every CI run. It does NOT
    touch `measured`, because the measurement is still the one that was taken,
    and it cannot invent a host: one that has gained no measurement is still
    reported unmeasured by --check.
    """
    payload = json.load(open(ARTIFACT))
    inventory = build_inventory()
    changed = []
    for host, row in payload["hosts"].items():
        if host not in inventory:
            continue
        now = inventory[host]["callers"]
        then = row.get("callers", {})
        if now != then:
            gained = sorted(set(now) - set(then))
            lost = sorted(set(then) - set(now))
            switched = sorted("%s %s->%s" % (f, then[f], now[f])
                              for f in set(now) & set(then) if then[f] != now[f])
            changed.append((host, gained, lost, switched))
            row["callers"] = now
    payload["callers_refreshed"] = datetime.date.today().isoformat()
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False)
        f.write("\n")
    for host, gained, lost, switched in changed:
        # SAY WHICH OF THE THREE IT WAS. The first version printed "+-" for a
        # host whose only change was a caller switching what it sends, which
        # reads as "nothing" beside a line claiming a refresh.
        parts = []
        if gained:
            parts.append("gained " + ", ".join(gained))
        if lost:
            parts.append("lost " + ", ".join(lost))
        if switched:
            parts.append("switched " + "; ".join(switched))
        print("refreshed %-34s %s" % (host, "; ".join(parts)))
    print("probe: refreshed the caller list on %d host(s); verdicts and the "
          "measurement date are unchanged" % len(changed))
    return 0


def report(args):
    payload = json.load(open(ARTIFACT))
    hosts = payload["hosts"]
    order = ["token-ok", "stack-not-token", "token-refused",
             "token-refused-and-stack", "all-refused", "challenged",
             "answers-nothing", "robots-disallows-this-path", "crawl-delay-too-long",
             "tls-chain", "proxy-denied", "no-dns", "path-answers-nothing"]
    lines = ["# Which hosts refuse the districtry user-agent",
             "",
             "Measured %s from %s." % (payload["measured"], payload["vantage"]),
             "",
             "Self-identifying token: `%s`" % payload["tokens"]["self"],
             "Browser string: `%s`" % payload["tokens"]["browser"],
             ""]
    for verdict in order + [v for v in tally(hosts) if v not in order]:
        rows = [r for r in hosts.values() if r["verdict"] == verdict]
        if not rows:
            continue
        lines += ["## %s — %d host(s)" % (verdict, len(rows)), ""]
        for row in sorted(rows, key=lambda r: r["host"]):
            lines.append("- `%s` — %s" % (row["host"], row.get("note", "")[:200]))
        lines.append("")
    text = "\n".join(lines) + "\n"
    if args.report == "-":
        sys.stdout.write(text)
    else:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(text)
        print("probe: wrote %s" % args.report, file=sys.stderr)
    return 0


def show_inventory(args):
    inventory = build_inventory()
    subject = subject_hosts(inventory)
    counts = {}
    for host, entry in inventory.items():
        flat = caller_kinds(entry)
        label = ("browser only" if flat - {"unknown"} == {"browser"} else
                 "self only" if flat - {"unknown"} == {"self"} else
                 "both kinds" if {"browser", "self"} <= flat else
                 "no user-agent set")
        counts[label] = counts.get(label, 0) + 1
    print("hosts a script reaches: %d" % len(inventory))
    for label, n in sorted(counts.items()):
        print("  %-20s %4d" % (label, n))
    print("subject of this probe (a browser-string caller reaches it): %d" % len(subject))
    if args.verbose:
        for host in subject:
            print("  %-40s %s" % (host, choose_url(inventory[host])[:100]))
    for line in file_summary(inventory):
        print(line)
    return 0


def file_summary(inventory):
    """The per-FILE tally CLAUDE.md and the guidebook quote, derived rather
    than remembered. A file sends a browser string if its kind is 'browser' or
    'both'. Against the artifact's per-host verdicts, each such file is one of:
    every host it reaches is `token-ok`; no host it reaches refuses the token
    (all measured, none `token-refused*`, but at least one `stack-not-token`,
    `answers-nothing` or another non-refusal); at least one host refuses the
    token; or it reaches a host the artifact does not carry. The four are
    disjoint and sum to the browser-string file count. Without an artifact the
    first line still prints and the rest are skipped."""
    files = {}
    for host, entry in inventory.items():
        for rel, kind in entry["callers"].items():
            files.setdefault(rel, {"kind": kind, "hosts": set()})["hosts"].add(host)
    browser = sorted(f for f, d in files.items() if d["kind"] in ("browser", "both"))
    lines = ["files sending a browser string: %d (%d of them the token as well)"
             % (len(browser), sum(1 for f in browser if files[f]["kind"] == "both"))]
    if not os.path.exists(ARTIFACT):
        return lines
    verdicts = {h: r["verdict"] for h, r in json.load(open(ARTIFACT))["hosts"].items()}
    refusing = {h for h, v in verdicts.items() if v.startswith("token-refused")}
    token_ok = {h for h, v in verdicts.items() if v == "token-ok"}
    buckets = {"every host serves the token a full page": 0,
               "no host refuses the token (some answered nothing or refused the stack)": 0,
               "at least one host refuses the token": 0,
               "reaches a host the artifact does not carry": 0}
    for f in browser:
        hosts = files[f]["hosts"]
        if hosts - set(verdicts):
            buckets["reaches a host the artifact does not carry"] += 1
        elif hosts & refusing:
            buckets["at least one host refuses the token"] += 1
        elif hosts <= token_ok:
            buckets["every host serves the token a full page"] += 1
        else:
            buckets["no host refuses the token (some answered nothing or refused the stack)"] += 1
    for label, n in buckets.items():
        lines.append("  %-74s %4d" % (label, n))
    return lines


def selftest():
    """Offline: drive read_robots() through every status it distinguishes with
    a stub getter, so the robots-read path cannot silently break again."""
    ua = {"User-Agent": "districtry/1.0 (+https://districtry.com/il/)"}
    served = b"User-agent: *\nDisallow: /private/\nCrawl-delay: 7\n"
    cases = [  # (getter result, expected (policy is not None, delay, note prefix))
        ((200, served, {}, "u"), (True, 7.0, "read, 1 group(s)")),
        ((200, b"", {}, "u"), (True, None, "none (HTTP 200)")),   # an empty 200 is absent: allow-all
        ((404, b"", {}, "u"), (True, None, "none (HTTP 404)")),
        ((403, b"", {}, "u"), (True, None, "refused to this client")),
        ((202, b"<meta http-equiv=refresh>", {}, "u"), (False, None, "challenge (HTTP 202)")),
        ((503, b"", {}, "u"), (False, None, "unreachable (HTTP 503)")),
    ]
    failures = []
    for result, (has_policy, delay, prefix) in cases:
        policy, got_delay, note = read_robots(lambda *a, **k: result, ua, "https", "h.example")
        if (policy is not None) != has_policy or got_delay != delay or not note.startswith(prefix):
            failures.append("HTTP %s: got (%s, %r, %r), want (%s, %r, %r...)" % (
                result[0], policy is not None, got_delay, note, has_policy, delay, prefix))
    def boom(*a, **k):
        raise OSError("no route")
    policy, got_delay, note = read_robots(boom, ua, "https", "h.example")
    if policy is not None or got_delay is not None or not note.startswith("unreadable (OSError)"):
        failures.append("exception: got (%s, %r, %r)" % (policy is not None, got_delay, note))
    policy, _delay, _note = read_robots(lambda *a, **k: (200, served, {}, "u"), ua, "https", "h.example")
    if policy.allows(ua["User-Agent"], "/private/x") or not policy.allows(ua["User-Agent"], "/public/x"):
        failures.append("served policy did not apply its Disallow: /private/ rule")

    # file_urls(): a URL split across adjacent literals is one address, and
    # its first half is not a second one; a whole literal that is a prefix of
    # another whole literal stays.
    # (The fixtures are built from "%s://" so that this file's own literals
    # are not addresses in the inventory it audits.)
    h = "%s://" % "https"
    split = ('SOURCE = ("' + h + 'www.example.gov/city/en/depts/"\n'
             '          "providerlist.html")\n'
             'BASE = "' + h + 'api.example.gov/v1/x.json"\n'
             'Q = "' + h + 'api.example.gov/v1/x.json?$limit=5"\n'
             '# see ' + h + 'docs.example.gov/notes/\n')
    got = file_urls(split)
    want = [h + "api.example.gov/v1/x.json", h + "api.example.gov/v1/x.json?$limit=5",
            h + "docs.example.gov/notes/", h + "www.example.gov/city/en/depts/providerlist.html"]
    if got != want:
        failures.append("file_urls: got %r, want %r" % (got, want))
    # choose_url(): a page beats a directory beats the root; among pages the
    # shorter path still wins.
    entry = {"urls": {h + "h.example/": [], h + "h.example/a/b/": [],
                      h + "h.example/a/b/page.html": [], h + "h.example/a/deeper/x.html": []}}
    if choose_url(entry) != h + "h.example/a/b/page.html":
        failures.append("choose_url: chose %r" % choose_url(entry))
    entry = {"urls": {h + "h.example/": [], h + "h.example/a/b/": []}}
    if choose_url(entry) != h + "h.example/a/b/":
        failures.append("choose_url: a directory should still beat the root, chose %r"
                        % choose_url(entry))
    entry = {"urls": {h + "h.example/rest/services/": [], h + "h.example/rest/services/X/MapServer/1?f=json": []}}
    if choose_url(entry) != h + "h.example/rest/services/X/MapServer/1?f=json":
        failures.append("choose_url: a query page should beat a directory, chose %r"
                        % choose_url(entry))
    # merge_measurements(): a subset run keeps the sweep date and the callers
    # date and dates only the rows it probed; a full sweep re-dates the top.
    prior = {"measured": "2026-09-12", "callers_refreshed": "2026-09-12",
             "hosts": {"a.example": {"host": "a.example", "verdict": "token-ok", "callers": {}},
                       "b.example": {"host": "b.example", "verdict": "token-ok", "callers": {}}}}
    row = {"host": "b.example", "verdict": "token-refused", "note": "HTTP 403", "callers": {}}
    out = merge_measurements(prior, {"b.example": row}, "2026-09-20", full_sweep=False)
    if (out["measured"] != "2026-09-12" or out.get("callers_refreshed") != "2026-09-12"
            or out["hosts"]["b.example"].get("measured") != "2026-09-20"
            or "measured" in out["hosts"]["a.example"]
            or out["summary"] != {"token-ok": 1, "token-refused": 1}):
        failures.append("merge_measurements (subset): %r" % {k: out[k] for k in ("measured", "callers_refreshed", "summary")})
    out = merge_measurements(prior, {"b.example": row}, "2026-09-20", full_sweep=True)
    if out["measured"] != "2026-09-20" or out.get("callers_refreshed") != "2026-09-12":
        failures.append("merge_measurements (full sweep): measured %r, callers_refreshed %r"
                        % (out["measured"], out.get("callers_refreshed")))
    if merge_measurements(None, {"b.example": row}, "2026-09-20", full_sweep=False)["measured"] != "2026-09-20":
        failures.append("merge_measurements: a first artifact must carry today's date")
    if failures:
        for line in failures:
            print("probe --selftest: FAIL — %s" % line, file=sys.stderr)
        return 1
    print("probe --selftest: OK — read_robots() over 7 stub responses; file_urls, "
          "choose_url and merge_measurements over 8 cases")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="offline: drive read_robots() with stub responses")
    ap.add_argument("--probe", action="store_true", help="measure and write the artifact")
    ap.add_argument("--check", action="store_true", help="offline re-audit, no requests")
    ap.add_argument("--inventory", action="store_true", help="list the surface only")
    ap.add_argument("--report", help="render the artifact as markdown ('-' for stdout)")
    ap.add_argument("--hosts", help="comma-separated subset to probe")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--pace", type=float, default=2.0,
                    help="seconds between requests to ONE host")
    ap.add_argument("--merge", action="store_true", default=True,
                    help="keep measurements for hosts this run did not probe")
    ap.add_argument("--no-merge", dest="merge", action="store_false")
    ap.add_argument("--refresh-callers", action="store_true",
                    help="re-read who reaches each measured host; keeps verdicts")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.report:
        return report(args)
    if args.refresh_callers:
        return refresh_callers(args)
    if args.check:
        return check(args)
    if args.probe:
        return run_probe(args)
    return show_inventory(args)


if __name__ == "__main__":
    sys.exit(main())
