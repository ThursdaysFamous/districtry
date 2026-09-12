#!/usr/bin/env python3
"""
Scrape each NYPD precinct's commanding officer from its nyc.gov precinct page
(METRO_EXPANSION_PLAYBOOK §9). Stage 1 of the pipeline: the precinct list is
driven from the Socrata precinct boundary dataset (y76i-bdw7) — NYPD's precinct
numbers are irregular, so never loop 1..N — and each precinct's ordinal page
(…/precincts/{Nth}-precinct.page) yields the "Commanding Officer:" line.

THREE PRECINCTS ARE NAMED, NOT NUMBERED, ON NYC.GOV. The ordinal pattern holds
for 75 of 78 and 404s for precincts 14, 18 and 22, whose pages are
midtown-south / midtown-north / central-park. That cost twice over and quietly:
those three lost their commanding officer (a 404 yields no name, correctly) AND
their dead URL was still written as `source_url`, so the card rendered a link to
a 404. Caught 2026-08-25 when validate_card_links.py grew to scan every
instance's data/app.

The mapping is not taken from the pages, which never state their own precinct
number, nor from the names looking obvious. It is PROVEN SPATIALLY from the
city's own data: each named station house in FacDB (ji82-xba5) is tested against
the numbered precinct polygons in y76i-bdw7, and each falls inside exactly one —
Midtown South, 357 W 35 St, inside precinct 14; Midtown North, 306 W 54 St,
inside 18; Central Park inside 22. NYPD's own precinct landing page independently
confirms these are the only three named precincts.

Writes an intermediate JSON with source_url + scraped_at per record; the CO name
is the only field taken here (the precinct card already gets station address/phone
from FacDB). A page that WAF-blocks or omits the label yields a null commander —
never guessed. build_nypd_roster.py resolves this into data/app/nypd-precinct-info.json.

Usage:
    python3 scripts/nypd_precinct_scraper.py [--out PATH] [--limit N]
"""

import html as html_lib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SOCRATA = "https://data.cityofnewyork.us/resource/y76i-bdw7.json?$select=precinct&$limit=1000"
PAGE = "https://www.nyc.gov/site/nypd/bureaus/patrol/precincts/{slug}-precinct.page"
# precinct number -> the slug nyc.gov actually serves, for the three that are
# named rather than numbered (see the module docstring for how each was proven).
# A number absent here uses its ordinal.
NAMED_PAGES = {14: "midtown-south", 18: "midtown-north", 22: "central-park"}

# Words that begin the body paragraph after the officer's name — never part of
# a name, and the boundary the capture stops at.
_STOP = (r"(?:The|This|As|New|Its|It|Located|NYPD|Officers|Police|Precinct|In|"
         r"Situated|Bounded|Covering|Home)")
_RANK = r"(?:Deputy\s+|Assistant\s+)?(?:Inspector|Chief|Captain|Lieutenant|Sergeant)"
NAME_RE = re.compile(
    r"Commanding Officer:\s*(" + _RANK +
    r"(?:\s+(?!" + _STOP + r"\b)[A-Z][A-Za-z'\u2019.,\-]*){1,4})"
)
UA = "Mozilla/5.0 (compatible; districtry-nyc/1.0; +https://districtry.com/ny/)"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "nypd_precincts_raw.json")


def ordinal(n):
    n = int(n)
    v = n % 100
    suffix = "th" if 11 <= v <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suffix)


def page_url(n):
    """The precinct's page on nyc.gov — its name where it has one, else its ordinal."""
    return PAGE.format(slug=NAMED_PAGES.get(int(n)) or ordinal(n))


def _get(url, timeout=45):
    headers = {"User-Agent": UA, "Accept": "text/html,application/json"}
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token and "data.cityofnewyork.us" in url:
        headers["X-App-Token"] = token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def precinct_numbers():
    rows = json.loads(_get(SOCRATA))
    nums = sorted({int(r["precinct"]) for r in rows if r.get("precinct") not in (None, "")})
    return nums


def commander_from_html(page_html):
    # Entities are UNESCAPED before matching, and that is load-bearing rather
    # than tidiness: the three named precinct pages write the CO line as
    # "Commanding Officer:&nbsp;Deputy Inspector&nbsp;Christopher Treubig", and
    # a raw match sees "&nbsp;" where it expects a space — so those three
    # returned no commander even once their URLs were right.
    text = re.sub(r"<[^>]+>", " ", page_html)
    text = html_lib.unescape(text).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)

    # ANCHOR ON THE RANK AND TAKE NAME TOKENS, rather than trying to recognise
    # where the body paragraph begins. The previous version enumerated the
    # openings it had seen — "The 13th Precinct serves…", "This precinct…" —
    # and so missed every page that opened differently: the three named
    # precincts' "As its name implies, the Midtown South Precinct…", and the
    # 42nd's "New York City's 42nd Precinct serves…". Precinct 42 had no
    # commanding officer on its card for that reason alone, with a live page
    # and a perfectly readable name on it.
    #
    # A generic "stop before the sentence that mentions Precinct" lookahead was
    # tried and is WRONG, worth recording so it is not tried again: the capture
    # is non-greedy, so it stops at the EARLIEST position satisfying the
    # lookahead — which is inside the name itself — and it truncated 58 of 78
    # names to their bare rank while looking plausible.
    #
    # So the rank is the anchor (NYPD commanding officers are Captains,
    # Inspectors, Deputy Inspectors and Chiefs), followed by up to four
    # capitalised tokens that are not sentence-openers. That reads initials
    # ("Timothy V. Magliente"), suffixes ("James H. Moore III"), hyphenated
    # surnames ("Michael Black-Larkins") and the county's own punctuation typos
    # ("Anthony M, Lavino") exactly as published, and resolves all 78.
    m = NAME_RE.search(text)
    if not m:
        return None
    name = m.group(1).strip(" .,")
    # sanity: a rank + name, not a stray sentence
    return name if 4 <= len(name) <= 60 else None


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None

    nums = precinct_numbers()
    if limit:
        nums = nums[:limit]
    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    records = {}
    found = 0
    for n in nums:
        url = page_url(n)
        commander = None
        try:
            commander = commander_from_html(_get(url))
        except urllib.error.HTTPError as e:
            commander = None  # 404/403 -> no CO for this precinct, never guessed
        except Exception:
            commander = None
        if commander:
            found += 1
        records[str(n)] = {"commander": commander, "source_url": url, "scraped_at": scraped_at}
        time.sleep(0.3)  # courteous to nyc.gov

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"precincts": records}, f, indent=2, ensure_ascii=False)
    print("wrote %s: %d precincts, %d with a commander" % (out_path, len(records), found), file=sys.stderr)


if __name__ == "__main__":
    main()
