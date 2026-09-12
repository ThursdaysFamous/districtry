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
2026-09-12 across the 290 hosts a browser-string caller reaches: 203 serve
UA_ROSTER_BOT a full page, 17 refuse it and answer the browser string, and 6
refuse the `requests` STACK while serving the same token on the stdlib client,
so on those a browser string is credited with a fix the stack made. 57 files
send a browser string where every host they reach serves the token a full
page, and 68 where no host they reach refuses it (the other 11 also reach a
host that answered nothing or refuses the requests stack).

That does not license a fleet-wide rename, and the rule above is unchanged: a
file's UA moves per county with that county's weekly run as the witness. What
the measurement changes is that the move now starts from a number instead of a
guess, and a file that keeps its browser string can cite the host's own answer.

STDLIB-ONLY AT MODULE SCOPE, deliberately: scripts/validate_workflow_deps.py
walks module-scope import closures against each workflow's pip line, and this
module is imported by scripts whose workflows install nothing. `requests` is
imported inside fetch(), the one function that needs it.
"""
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
UA_ROSTER_COMPACT = "Mozilla/5.0 (compatible; districtry-roster/1.0)"
UA_CIVIC_BOT = ("Mozilla/5.0 (compatible; districtry.com civic data bot; "
                "+https://districtry.com/)")


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
