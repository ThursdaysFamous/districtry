#!/usr/bin/env python3
"""
Scrape stage 1: fetch each of Iowa's 8 judicial districts' own "Judges and
Magistrates" roster page from iowacourts.gov and write the raw name/role
pairs to .cache/ia_judicial_district_judges.json for
build_ia_judicial_district_roster.py (stage 2) to join against the shipped
geometry's district numbers.

THREE DIFFERENT URL SHAPES, verified live 2026-08-28, one hardcoded per
district rather than derived from a single pattern:
    District 1:      .../judicial-district-1/judges-and-magistrates-district-1/  (number SUFFIX)
    Districts 2-7:    .../judicial-district-N/judges-and-magistrates/            (bare)
    District 8:       .../judicial-district-8/district-8-judges-and-magistrates/ (number PREFIX)

THE CLIENT IS A DISTRICTRY TOKEN, AND ROBOTS.TXT IS READ FIRST (since
2026-09-12). Until then this file sent a Chrome browser string on the strength
of a sentence added 2026-09-02 (commit 0b1fd80): "iowacourts.gov returns HTTP
403 to at least one common automated-client signature; a plain browser
User-Agent is required (verified: curl with one gets 200, without one gets 403
from this same sandbox)". That sentence named no token, which is the one thing
CLAUDE.md's user-agent rule asks a refusal record to do, and it did not
reproduce: measured 2026-09-12 against district 2's page from the same kind
of sandbox, `chidistricts.com roster bot (civic data; contact via site)`,
`Mozilla/5.0 (compatible; districtexplorer-roster/1.0)`, a bare
`python-requests/2.31.0` and the Chrome string ALL answered HTTP 200 with the
same 61 judge blocks. Whatever was refused on 2026-09-02 — a different URL, a
different day, or the sandbox's egress rather than the site — the site does
not refuse this instance's own token today, so this file sends it, the same
one the four other Iowa scrapers send. If the site ever refuses it, the
weekly run fails loudly, and the record to write is: which token, what the
site answered, and the date.

iowacourts.gov's robots.txt (read through scripts/robots_policy.py, one fetch
per run) has TWO `User-agent: *` groups: Cloudflare's managed block
(`Content-Signal: search=yes,ai-train=no,use=reference`, `Allow: /`) and the
court's own, which carries `Crawl-delay: 30` and an empty `Disallow:`. Both
bind this client and are read as one: everything is allowed, and the delay is
honoured — 30 seconds between each of the 8 district fetches, about four
minutes a week, where this file used to sleep one second. The Content-Signal
is the same line Sheboygan's file carries, and the operator's 2026-09-05
ruling on it (wi/scripts/wi_alderperson_scraper.py, scrape_sheboygan, and
CLAUDE.md's honesty rules) covers this fetch for the same reason: nothing here
trains, and naming a judge with a link back to the court's own page is the
reference use the signal permits. The ClaudeBot group in the same file
disallows a different agent and does not bind this one.

THE TITLE FIELD IS NOT SPLIT INTO RANK + SUB-DISTRICT. Sampled across all 8
districts (2026-08-28), the CMS punctuates it at least four different ways
with no consistent separator:
    "Chief Judge: District 1B"            (colon)
    "District court Judge; District 3A"   (semicolon, lowercase "court")
    "District Court Judge D5"             (no punctuation at all)
    "Senior Judge District 2A"            (no punctuation at all)
    "Magisrate"                           (a genuine misspelling in the source)
Guessing a split rule risks mis-parsing some of these into a wrong rank or a
wrong sub-district; shipping the whole string verbatim (HTML-entity-decoded,
whitespace-collapsed) as one field is the honest choice and the fleet's own
convention (never invent structure the source doesn't clearly state). A
sub-district or county named in the title (e.g. "District 1B", "Cedar
County") is informational only — this layer's own district is the whole
NUMBERED district a judge's page sits under, never the sub-division.

Markup (identical shape across all 8 districts, confirmed by direct fetch):
    <div class="cms_list_item">
      ...
      <h2 class="title_header">David P. Odekirk</h2>
      <div class="cms_metadata2 cms_title" ...>Chief Judge&#x3a; District 1B</div>
      ...
    </div>

Floors (refuses to write otherwise): all 8 districts present; >= 250 judges
total (measured 2026-08-28: District totals ranged 31-77, ~360 statewide);
every district has at least one judge.

Usage:
    python3 ia/scripts/ia_judicial_district_scraper.py
"""

import json
import html
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    print("FATAL: pip install -r ia/scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_FILE = os.path.join(CACHE_DIR, "ia_judicial_district_judges.json")

BASE = "https://www.iowacourts.gov/iowa-courts/district-court"
DISTRICT_URLS = {
    1: BASE + "/judicial-district-1/judges-and-magistrates-district-1/",
    2: BASE + "/judicial-district-2/judges-and-magistrates/",
    3: BASE + "/judicial-district-3/judges-and-magistrates/",
    4: BASE + "/judicial-district-4/judges-and-magistrates/",
    5: BASE + "/judicial-district-5/judges-and-magistrates/",
    6: BASE + "/judicial-district-6/judges-and-magistrates/",
    7: BASE + "/judicial-district-7/judges-and-magistrates/",
    8: BASE + "/judicial-district-8/district-8-judges-and-magistrates/",
}

# The same token the four other Iowa scrapers send (see the module docstring
# for the 2026-09-12 measurement that retired the browser string here).
HEADERS = {
    "User-Agent": "districtry/1.0 (+https://districtry.com/ia/)",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}
REQUEST_TIMEOUT = 60
MIN_TOTAL_JUDGES = 250
# Between fetches, unless the host's robots.txt asks for longer: it does, 30 s
# in the group that binds this client (measured 2026-09-12), so the run takes
# about four minutes. Never shortened below what the host states.
MIN_PAUSE_SECONDS = 1.0

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robots_gate import RobotsGate  # noqa: E402  (shared machinery — do not fork)

ITEM_RE = re.compile(
    r'<h2 class="title_header">([^<]*)</h2>\s*'
    r'<div class="cms_metadata2 cms_title"[^>]*>([^<]*)</div>',
    re.S)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def fetch_district(dist, url, session, gate):
    allowed, why = gate.allows(url)
    if not allowed:
        # A refusal by rule is a data event, not a fetch to retry: the run
        # stops, the shipped roster keeps its last good contents, and the
        # reason is the first thing in the log.
        raise SystemExit("district %d: robots.txt does not permit this client to read %s (%s)"
                         % (dist, url, why))
    resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()
    matches = ITEM_RE.findall(resp.text)
    judges = []
    for raw_name, raw_role in matches:
        name = clean(raw_name)
        role = clean(raw_role)
        if not name:
            continue
        judges.append({"name": name, "role": role})
    if not judges:
        raise SystemExit("district %d: parsed zero judges from %s -- markup changed?"
                          % (dist, url))
    return judges


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    session = requests.Session()
    gate = RobotsGate(session, HEADERS["User-Agent"], timeout=REQUEST_TIMEOUT)
    first_url = DISTRICT_URLS[min(DISTRICT_URLS)]
    stated = gate.crawl_delay(first_url)
    pause = max(MIN_PAUSE_SECONDS, stated or 0.0)
    print("robots.txt for %s: %s; Crawl-delay %s -> pausing %g s between fetches"
          % (first_url.split("/")[2], gate.verdict(first_url).why,
             ("%g s" % stated) if stated else "not stated", pause), file=sys.stderr)
    out = {}
    total = 0
    for dist in sorted(DISTRICT_URLS):
        url = DISTRICT_URLS[dist]
        judges = fetch_district(dist, url, session, gate)
        out[str(dist)] = {"url": url, "judges": judges}
        total += len(judges)
        print("district %d: %d judges (%s)" % (dist, len(judges), url), file=sys.stderr)
        if dist != max(DISTRICT_URLS):
            time.sleep(pause)

    if len(out) != 8:
        raise SystemExit("scraped %d districts, expected 8" % len(out))
    if total < MIN_TOTAL_JUDGES:
        raise SystemExit("only %d judges total (floor %d)" % (total, MIN_TOTAL_JUDGES))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
    print("wrote %s -- %d districts, %d judges" % (OUT_FILE, len(out), total), file=sys.stderr)


if __name__ == "__main__":
    main()
