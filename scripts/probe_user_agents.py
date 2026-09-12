#!/usr/bin/env python3
"""
Measure which county and city hosts actually refuse this project's own
user-agent, so that the 116 files sending a browser string can say whether they
need one.

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

Measured 2026-09-12: 297 hosts are reached by a caller that sends a browser
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
    4. stdlib   + Chrome/126 + hints    <- what 116 files send today

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


# --- robots.txt.
#
# THE ONE COPY OF THIS PARSER LIVES IN WISCONSIN'S GATE, and it is imported
# rather than restated: wi/scripts/validate_robots.py's permitted() carries the
# record of what a literal startswith() got wrong (it cannot match a rule
# containing `*` or `$` at all, which turned cms5.revize.com's "documents yes,
# everything else no" into a flat refusal and would have discarded a wildcard
# Disallow that genuinely covered a fetch). A second copy here is how that
# record drifts. A root script importing an instance file is backwards and the
# fix is to move those three functions to scripts/robots_rules.py, which is not
# done inside a measurement change because it edits a green CI gate.
def _load_robots_rules():
    path = os.path.join(ROOT, "wi", "scripts", "validate_robots.py")
    spec = importlib.util.spec_from_file_location("_wi_validate_robots", path)
    mod = importlib.util.module_from_spec(spec)
    before = list(sys.path)
    spec.loader.exec_module(mod)
    # That module inserts its own directory at the front of sys.path. Leaving it
    # there is how a bare `import validate_sources` elsewhere resolves to
    # Wisconsin's — the bug that file's own comment records, one level up.
    for entry in list(sys.path):
        if entry not in before:
            sys.path.remove(entry)
    return mod


_ROBOTS = _load_robots_rules()
star_group = _ROBOTS.star_disallows
permitted = _ROBOTS.permitted
resolve_template = _ROBOTS.resolve_template


def crawl_delay(text):
    """The `*` group's Crawl-delay in seconds, or None.

    Read from the file rather than from star_disallows()'s output, which
    collects Allow and Disallow only — reaching for it there returned None for
    every host, so a 60-second delay would have been honoured as zero.
    """
    current, pending, delay = [], True, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (p.strip() for p in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if not pending:
                current, pending = [], True
            current.append(value.lower())
        elif key in ("disallow", "allow", "crawl-delay"):
            if current:
                pending = False
            if key == "crawl-delay" and "*" in current:
                try:
                    delay = float(value)
                except ValueError:
                    pass
    return delay


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
BROWSER_INLINE_RE = re.compile(
    r"Mozilla/5\.0 \((?:Windows NT|X11;|Macintosh;|iPhone|Android)")


def ua_kind(text):
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
    names, literals, parsed = _code_symbols(text)
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


def _code_symbols(text):
    """(identifiers, non-docstring string constants, parsed?) for one module."""
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
    return names, literals, True


def script_paths():
    out = sorted(glob.glob(os.path.join(ROOT, "scripts", "*.py")))
    for tag in INSTANCES:
        out += sorted(glob.glob(os.path.join(ROOT, tag, "scripts", "*.py")))
    return out


def build_inventory():
    """{host: {"urls": {url: [file]}, "callers": {file: kind}}}"""
    hosts = {}
    for path in script_paths():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        kind = ua_kind(text)
        for m in URL_RE.finditer(text):
            url = m.group(0).rstrip(".,;:%")
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
    """
    cands = [u for u in entry["urls"] if not re.search(r"%[sd]|[{<]", u)]
    if not cands:
        cands = [resolve_template(u) for u in entry["urls"]]

    def rank(url):
        split = urllib.parse.urlsplit(url)
        root = (split.path or "/") in ("", "/")
        return (split.scheme != "https", root, bool(split.query),
                len(split.path or "/"), url)

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
    if code == 200 and body:
        text = body.decode("utf-8", "replace")
        rules, delay = star_group(text), crawl_delay(text)
        if rules is None:
            return [], delay, "read, no * group"
        return rules, delay, "read, * group with %d rule(s)" % len(rules)
    if code in (404, 410) or (code and 200 <= code < 400 and not body):
        return [], None, "none (HTTP %s)" % code
    return None, None, "unreadable (HTTP %s)" % code


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
            if rules is not None:
                if not permitted(path, rules):
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

    merged = {}
    if args.merge and os.path.exists(ARTIFACT):
        merged = json.load(open(ARTIFACT))["hosts"]
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
                               "probe's own load, not a change of policy"
                               % datetime.date.today().isoformat())
            continue
        merged[host] = row

    payload = {
        "measured": datetime.date.today().isoformat(),
        "vantage": vantage(),
        "tokens": {"self": UA_ROSTER_BOT, "browser": UA_CHROME_WIN_126},
        "subject": ("every host reached by a script that sends a browser string; "
                    "hosts reached only by a self-identifying caller are not in "
                    "question and are not probed"),
        "summary": tally(merged),
        "hosts": dict(sorted(merged.items())),
    }
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False)
        f.write("\n")
    print("\nprobe: wrote %s (%d host(s))" % (os.path.relpath(ARTIFACT, ROOT),
                                              len(merged)), file=sys.stderr)
    for verdict, n in sorted(payload["summary"].items(), key=lambda kv: -kv[1]):
        print("  %-28s %4d" % (verdict, n), file=sys.stderr)
    return 0


def tally(hosts):
    out = {}
    for row in hosts.values():
        out[row["verdict"]] = out.get(row["verdict"], 0) + 1
    return dict(sorted(out.items()))


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
    payload = json.load(open(ARTIFACT))
    inventory = build_inventory()
    subject = set(subject_hosts(inventory))
    recorded = payload["hosts"]
    problems, notes = [], []

    for host, row in sorted(recorded.items()):
        if host not in inventory:
            problems.append("%s is recorded but no script names it any more — "
                            "drop the entry" % host)
            continue
        now = inventory[host]["callers"]
        then = row.get("callers", {})
        gained = sorted(set(now) - set(then))
        lost = sorted(set(then) - set(now))
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
    if unmeasured:
        notes.append("%d subject host(s) carry no measurement: %s"
                     % (len(unmeasured), ", ".join(unmeasured[:8])
                        + (" ..." if len(unmeasured) > 8 else "")))
    if payload.get("summary") != tally(recorded):
        problems.append("the summary block does not count the hosts below it")

    for line in notes:
        print("user-agent probe: NOTE — %s" % line)
    if problems:
        for line in problems:
            print("user-agent probe: FAIL — %s" % line, file=sys.stderr)
        return 1
    print("user-agent probe: OK — %d host(s) measured %s from %s; %d subject "
          "host(s) in the tree" % (len(recorded), payload["measured"],
                                   payload["vantage"].split(",")[0], len(subject)))
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
        if now != row.get("callers"):
            gained = sorted(set(now) - set(row.get("callers", {})))
            lost = sorted(set(row.get("callers", {})) - set(now))
            changed.append((host, gained, lost))
            row["callers"] = now
    payload["callers_refreshed"] = datetime.date.today().isoformat()
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False)
        f.write("\n")
    for host, gained, lost in changed:
        print("refreshed %-34s +%s %s" % (host, ", ".join(gained) or "-",
                                          ("-" + ", ".join(lost)) if lost else ""))
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
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
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
