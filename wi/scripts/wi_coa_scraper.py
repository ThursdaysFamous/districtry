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

import json
import os
import re
import ssl
import time
import sys
import urllib.request

DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "wi_coa_raw.json")
# WHY A DISTRICTRY TOKEN AND NOT A CHROME STRING (2026-09-12). This file sent
# `Mozilla/5.0 ... Chrome/124.0` until today, with nothing recorded about a
# refusal that needed it. www.wicourts.gov is measured `token-ok` in
# user-agent-measurements.json, and re-asked on this file's own stack the same
# day every URL below answered HTTP 200 to this exact token in under a second.
# robots.txt is a 404, so allow-all.
#
# THIS IS NOT THE FIX FOR THIS WORKFLOW'S FAILURES. Four of the six runs of the
# two wicourts.gov workflows die in `sock.connect` with a TCP connect timeout,
# on schedule and on dispatch, across four hours of the day and on both
# scrapers — no HTTP byte leaves the runner, so the host never sees any header
# this file sends. Issue #387 carries the run table.
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

    THE RETRY IS WHY THIS EXISTS. Until 2026-09-03 this was a single
    urlopen with no ladder, and the weekly job had NEVER ONCE been green:
    both scheduled runs (2026-08-26 and 2026-09-02) died in about a minute on one
    `urlopen error timed out`, which is one attempt and no second chance.
    Ten of this instance's thirteen scrapers already retry; this was one of
    the three that did not, and the two never-green jobs were both among
    them. Measured 2026-09-03: every URL here answers in under a second from
    a developer machine, so what failed was a moment on somebody else's
    server, which is exactly what a ladder is for.
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


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    assert_composition(fetch(INDEX_URL))
    districts = parse_contact(fetch(CONTACT_URL))

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
