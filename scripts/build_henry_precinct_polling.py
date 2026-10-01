#!/usr/bin/env python3
"""
Build data/app/henry-precinct-polling.json from the Henry County Clerk's own
Polling Places directory.

WHY THIS FILE EXISTS, AND WHY IT NEARLY DID NOT. Henry's precinct GEOMETRY came
from the county GIS office as a shapefile on 2026-08-06 — 52 precincts, the
cleanest precinct data any county has sent this project — but the reply carried
no polling assignment, and GIS said so explicitly: "The other questions are for
Barb to answer/supply." So `henry-precinct-polling` opened as the REMAINDER of a
gap that otherwise closed, and it sat with the Clerk for five days.

Clerk Barbara Link answered on 2026-08-11 in one sentence: "I have pdf precinct
maps on my webpage for all precinct boundaries so I feel that my webpage is
sufficient for what is needed. Also, I have polling place locations as well."
That reads as a brush-off and is a POINTER, and the pointer is correct — her
Polling Places directory lists all 52 locations, one per precinct, and had been
reachable for the entire life of this project without anyone opening it. It is
the Stephenson lesson arriving a second time: ask the clerk what she HAS, not
whether the thing you want exists, because the miss is in which page was looked
at and only she can audit that from the inside.

THE JOIN IS ON THE PRECINCT'S OWN FIELD, not on the listing title. Each row's
bold title is "<Precinct> - <Location>", which looks like the key and is not
one: the county writes "Colona 3- Colona Activity Center" without the space and
"Andover Village Hall" with no precinct prefix at all. Every row also carries
the precinct in a field of its own, and that is what this reads. The title is
used only to strip a redundant prefix off the location name.

THE ONE ALIAS, ENUMERATED RATHER THAN FUZZY. Sixteen of Henry's townships hold
a single precinct, and the two sources disagree about whether it has a number:
the shapefile writes "Alba 1", the directory writes "Alba". The rule applied is
narrow and asserted — a bare directory name maps to "<name> 1" ONLY when the
shapefile has exactly one precinct in that township and no bare form of its own.
Anything else fails the build rather than being matched approximately.

POLLING ASSIGNMENTS ARE PER-ELECTION, AND THIS ONE RUNS WEEKLY — the fleet's
first scheduled polling job (.github/workflows/update-henry-precinct-polling.yml,
Fri 18:00 UTC). Carroll's, Logan's and Montgomery's are operator steps, re-run
when the clerk republishes, which is fine for a table nobody reads between
elections. A polling place is not that: it is the one row on any card in this
app where being a cycle out of date sends a resident to the wrong building on
election day. Six page fetches a week turns "we will remember to re-run it" into
a PR. The job opens one only when a polling place actually MOVED — the shipped
file carries a fetch date that changes every run, and a PR that is nothing but a
new date teaches a reviewer to stop reading them.

--check does the same comparison without writing, which is the thing to run by
hand before an election rather than trusting the date. The card links the
Clerk's Elections page as the authority.

Usage:
    python3 build_henry_precinct_polling.py            # fetch + write
    python3 build_henry_precinct_polling.py --check    # fetch + compare, writes nothing
"""

import argparse
import datetime
import json
import os
import re
import sys

import requests
from scraper_common import require_robots_once, UA_ROSTER_BOT, fetch as fetch_with_retry  # noqa: E402  (shared machinery — do not fork)

DIRECTORY_URL = ("https://www.henrycty.com/BusinessDirectoryii.aspx"
                 "?lngBusinessCategoryID=25&lngNewPage=%d")
CLERK_PAGE = "https://www.henrycty.com/211/Elections"
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "henry-precincts.json")
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "henry-precinct-polling.json")

EXPECTED_PRECINCTS = 52
MAX_PAGES = 12            # the directory pages ten at a time; this is a runaway stop
FETCH_ATTEMPTS = 3

ROW_START_RE = re.compile(r'<div class="(?:alt )?listItemsRow"')
TITLE_RE = re.compile(r'font-weight: bold;">(.*?)</span>(.*?)</div>', re.S)
FIELD_RE = re.compile(r'<div style="font-size:small;">([^<]*)</div>')
COUNT_RE = re.compile(r'(\d+)\s*-\s*(\d+)\s+of\s+(\d+)\s+Listings')


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip()


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    require_robots_once(url, HEADERS["User-Agent"],
                        headers=HEADERS, label="il-build-henry-precinct-polling")
    return fetch_with_retry(url, HEADERS, timeout=60,
                            attempts=FETCH_ATTEMPTS).text


def parse_page(html):
    """Rows as (precinct, title, address-lines).

    Split on row starts rather than matching a closing tag: the rows nest divs
    and one of them — Colona 4 — has no "View Map" link where every other row
    does, which is exactly the kind of row a tighter pattern drops in silence.
    """
    starts = [m.start() for m in ROW_START_RE.finditer(html)]
    rows = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else html.find('<div class="pageStyles"', start)
        block = html[start:end if end > start else len(html)]
        title_match = TITLE_RE.search(block)
        fields = [clean(f) for f in FIELD_RE.findall(block) if clean(f)]
        if not title_match or not fields:
            continue
        body = title_match.group(2)
        body = re.sub(r'<a href="http://maps.*?</a>', "", body, flags=re.S)
        lines = [clean(part) for part in body.split("<br>")]
        rows.append((fields[-1], clean(title_match.group(1)),
                     [line for line in lines if line]))
    return rows


def scrape():
    rows, seen, total = [], set(), None
    for page in range(1, MAX_PAGES + 1):
        html = fetch(DIRECTORY_URL % page)
        count = COUNT_RE.search(html)
        if count and total is None:
            total = int(count.group(3))
        page_rows = parse_page(html)
        if not page_rows:
            break
        new = [r for r in page_rows if r[0] not in seen]
        if not new:                          # paging stopped advancing
            break
        for row in new:
            seen.add(row[0])
        rows.extend(new)
        if total is not None and len(rows) >= total:
            break
    if total is None:
        sys.exit("henry-polling: the directory did not state a listing count — "
                 "the page changed shape, so stop rather than guess (%s)"
                 % (DIRECTORY_URL % 1))
    if len(rows) != total:
        sys.exit("henry-polling: the directory says %d listings and %d parsed. A "
                 "row that does not parse is a polling place a resident would "
                 "not be shown, so this refuses rather than shipping short."
                 % (total, len(rows)))
    return rows


def shipped_precincts():
    with open(PRECINCTS, encoding="utf-8") as handle:
        data = json.load(handle)
    names = []
    for feature in data.get("features", []):
        name = (feature.get("properties") or {}).get("name")
        if name:
            names.append(str(name).strip())
    if len(names) != EXPECTED_PRECINCTS:
        sys.exit("henry-polling: %s holds %d precincts, expected %d — the county's "
                 "fabric changed and this join needs re-checking against it"
                 % (os.path.basename(PRECINCTS), len(names), EXPECTED_PRECINCTS))
    return names


def alias_map(names):
    """Bare directory name -> shipped name, for single-precinct townships only.

    "Alba" -> "Alba 1", but only because the shapefile has exactly one Alba and
    no bare "Alba". A township with two numbered precincts, or one that already
    matches exactly, gets no alias — an ambiguous bare name has to fail.
    """
    exact = set(names)
    bases = {}
    for name in names:
        match = re.match(r"^(.*?)\s+(\d+)$", name)
        if match:
            bases.setdefault(match.group(1), []).append(name)
    return {base: variants[0] for base, variants in bases.items()
            if len(variants) == 1 and base not in exact}


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    parser.add_argument("--check", action="store_true",
                        help="fetch and compare against the shipped file; writes nothing")
    args = parser.parse_args()

    names = shipped_precincts()
    aliases = alias_map(names)
    rows = scrape()

    resolved, unmatched = {}, []
    for precinct, title, address in rows:
        key = precinct if precinct in set(names) else aliases.get(precinct)
        if not key:
            unmatched.append(precinct)
            continue
        if key in resolved:
            sys.exit("henry-polling: %r resolves to %r twice — the alias rule is "
                     "matching two directory rows onto one precinct" % (precinct, key))
        # The title repeats the precinct on most rows ("Alba - Township Hall")
        # and omits it on others ("Andover Village Hall"); strip only an exact
        # prefix so a location that merely starts with a township name survives.
        place = title
        for prefix in (precinct + " - ", precinct + "- ", precinct + " -", precinct + "-"):
            if place.startswith(prefix):
                place = place[len(prefix):].strip()
                break
        entry = {"place": place or title}
        if address:
            entry["address"] = ", ".join(address)
        resolved[key] = entry

    if unmatched:
        sys.exit("henry-polling: %d directory row(s) match no shipped precinct: %s\n"
                 "  Resolve them by name rather than loosening the alias rule."
                 % (len(unmatched), sorted(unmatched)))
    missing = sorted(set(names) - set(resolved))
    if missing:
        sys.exit("henry-polling: %d of %d precincts have no polling place: %s\n"
                 "  A partial join would leave those residents with a blank row, "
                 "so this refuses." % (len(missing), len(names), missing))

    payload = {
        "fetched": datetime.date.today().isoformat(),
        "source": DIRECTORY_URL % 1,
        "precincts": dict(sorted(resolved.items())),
    }
    text = json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n"

    with_address = sum(1 for v in resolved.values() if v.get("address"))
    print("henry-polling: %d/%d precincts joined, %d with a street address"
          % (len(resolved), len(names), with_address))
    print("  %d bare directory name(s) aliased to a single-precinct township"
          % sum(1 for p, _, _ in rows if p not in set(names)))
    print("  source: %s" % (DIRECTORY_URL % 1))

    existing = None
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as handle:
            existing = handle.read()
    if args.check:
        if existing is None:
            sys.exit("--check: %s does not exist yet" % os.path.relpath(OUT_PATH, REPO_ROOT))
        current = json.loads(existing)
        fresh = json.loads(text)
        if current.get("precincts") != fresh.get("precincts"):
            sys.exit("--check: the Clerk's directory no longer matches %s"
                     % os.path.relpath(OUT_PATH, REPO_ROOT))
        print("  --check OK — the directory still matches the shipped file")
        return
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("  wrote %s (%s bytes)"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), "{:,}".format(len(text))))


if __name__ == "__main__":
    main()
