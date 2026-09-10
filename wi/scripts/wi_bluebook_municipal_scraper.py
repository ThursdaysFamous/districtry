#!/usr/bin/env python3
"""
Scrape the *Wisconsin Blue Book* 2025-26 section 190 for the three municipal
facts this project has written permission to use. Stage 1 of the pair;
build_wi_municipal_facts.py turns the intermediate JSON into
data/app/wi-municipal-facts.json and data/app/wi-county-facts.json.

PERMISSION FIRST, BECAUSE IT IS THE REASON THIS FILE EXISTS. The volume's
front matter reads "(c)2025 Joint Committee on Legislative Organization,
Wisconsin Legislature. All rights reserved.", and the Legislature sells the
book. Madeline Kasper, Managing Legislative Analyst at the Legislative
Reference Bureau, answered this project's ask on 2026-09-10: "These uses seem
acceptable to us." The full record, and what "these uses" was scoped to, is
LICENSE-DATA.md section 4. Three limits ride with it and are why this scraper
takes so little:

  * NO PART OF THE VOLUME IS REPUBLISHED and the PDF IS NOT REDISTRIBUTED.
    The download is a build input; it is cached under .cache/ and is not
    committed.
  * ONLY THE SPECIFIC FACTS NAMED — incorporation year, county, and county
    seat. The same tables carry population counts, estimates, percentage
    change, land area, equalized value and rank. NONE of those is taken, and
    a later want for one asks again rather than citing this permission.
  * A DIFFERENT BLUE BOOK TABLE IS OUTSIDE THIS ANSWER. Section 190's own
    counties table prints each county's YEAR CREATED beside its seat; that is
    a different fact from the three named and IS NOT TAKEN.

WHAT THE SOURCE ACTUALLY CONTAINS, measured 2026-09-10 rather than assumed:

  * pp. 30-33  "Wisconsin cities, January 1, 2024" — 190 rows, grouped by
    class, each `Name | Year incorporated | County(ies) | <numbers>`.
  * pp. 34-41  "Wisconsin villages, January 1, 2024" — 417 rows, same shape.
  * pp. 8-10   "Basic data on Wisconsin counties" — 72 rows, whose COUNTY SEAT
    is a column. The seat is an attribute of the COUNTY, not of a
    municipality, which is why the county seat ships county-keyed.

THE CITIES TABLE CARRIES ITS OWN GATE and it is used: the class headings state
1 first-class + 16 second + 34 third + 139 fourth = 190, and the parse must
produce exactly that. A source that counts itself is a better check than any
floor this project could invent.

FOUR EXTRACTION TRAPS, ALL MEASURED AND ALL ENCODED:

  1. THE TEXT LAYER DROPS PERIODS. "St. Croix" extracts as "St  Croix" (the
     period becomes a space), so a county alternation built from the shipped
     fabric's own spelling matches nothing in ELEVEN city and village rows and
     in the counties table. Counties are matched on a period-stripped alias
     and mapped back to the fabric's spelling, so nothing here invents a name.
  2. LEADER DOTS ARRIVE AS U+0008 BACKSPACE. "Onalaska\x08 \x08 \x08 1887"
     — a name read without stripping them ships with control characters in it.
  3. A COUNTY CAN CARRY ONE GLUED LETTER from the column rule ("Ashlandv" for
     Butternut). One trailing lower-case letter is tolerated after a county
     name and discarded; anything more fails the row rather than guessing.
  4. A MUNICIPALITY CAN NAME SEVERAL COUNTIES, comma-separated, and 57 do —
     Wisconsin Dells names four. A single-county pattern silently drops every
     one of them, which is how a straddling municipality gets filed under one
     county it is only partly in.

The parse is FAIL-CLOSED: any capitalised line inside a table's page range
that matches no row shape is collected and reported, and the caller refuses to
write when the city count misses the source's own 190.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_OUT = os.path.join(SCRIPT_DIR, ".cache", "wi_bluebook_municipal_raw.json")
PDF_CACHE = os.path.join(SCRIPT_DIR, ".cache", "bluebook_190.pdf")
COUNTIES_FILE = os.path.join(REPO_ROOT, "data", "app", "state-counties.json")

EDITION = "Wisconsin Blue Book 2025–26"
SNAPSHOT = "January 1, 2024"
SOURCE_URL = ("https://docs.legis.wisconsin.gov/misc/lrb/blue_book/"
              "2025_2026/190_population_and_political_divisions.pdf")

# docs.legis.wisconsin.gov's robots.txt names no Crawl-delay for `*` (checked
# 2026-09-10) — the sibling clerk scraper waits 10s between fetches there and
# this one makes a single request, so nothing is shortened.
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/pdf,*/*;q=0.8",
}

CITY_PAGES = range(30, 34)
VILLAGE_PAGES = range(34, 42)
COUNTY_PAGES = (8, 9, 10)
EXPECT_CITIES = 190          # the source's own class headings sum to this
MIN_VILLAGES = 400

# Lines that begin a table's own furniture rather than a municipality.
FURNITURE = re.compile(
    r'^(Wisconsin|Statistics|Source|City|Village|Year|Note|First|Second|Third'
    r'|Fourth|Department|Municipalities|Reference|Intergovernmental|League'
    r'|Directory|January|Cities|Villages|Towns|\d)')


def fetch_pdf(path=PDF_CACHE, tries=3):
    """The section 190 PDF, cached. Not committed and not redistributed."""
    if os.path.exists(path) and os.path.getsize(path) > 100000:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(SOURCE_URL, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            if not body.startswith(b"%PDF"):
                raise RuntimeError("%s did not answer with a PDF (got %r) — a "
                                   "portal login page returns 200 too"
                                   % (SOURCE_URL, body[:20]))
            with open(path, "wb") as f:
                f.write(body)
            return path
        except (urllib.error.URLError, RuntimeError) as e:  # pragma: no cover
            last = e
    raise SystemExit("could not fetch %s after %d tries: %s" % (SOURCE_URL, tries, last))


def county_alternation():
    """A regex alternation of county names, keyed by the PERIOD-STRIPPED form
    the PDF's text layer actually produces, mapping back to the shipped
    fabric's own spelling. Trap 1."""
    with open(COUNTIES_FILE) as f:
        fabric = json.load(f)
    names = sorted({feat["properties"]["BASENAME"] for feat in fabric["features"]})
    if len(names) != 72:
        raise SystemExit("the shipped county fabric holds %d counties, not 72 — "
                         "this parse keys on it" % len(names))
    alias = {n.replace(".", ""): n for n in names}
    pattern = "|".join(re.escape(a) for a in sorted(alias, key=len, reverse=True))
    return alias, pattern


def clean(line):
    """Leader dots arrive as U+0008; runs of space are collapsed. Trap 2."""
    return re.sub(r"\s+", " ", line.replace("\x08", " ")).strip()


def parse_municipalities(pages, page_range, start_marker, alias, cty, stop_marker=None):
    """-> ([{name, year, counties}], [unmatched lines]).

    `stop_marker` matters: the villages table ends PART-WAY DOWN p41 and the
    next table ("Wisconsin cities and villages over 10,000 population") begins
    on the same page. Without the stop, its 21 rows arrive as unmatched lines
    on every run, and a fail-closed report that cries wolf every run is one a
    reader learns to skip."""
    row = re.compile(r"^(?P<name>[A-Z][A-Za-z.'\- ]*?)\d?\s+"
                     r"(?P<year>1[6-9]\d\d|20[0-2]\d)\s+"
                     r"(?P<counties>(?:%s)[a-z]?(?:,\s*(?:%s)[a-z]?)*)(?:\s|$)"
                     % (cty, cty))
    split = re.compile(r"(%s)" % cty)
    out, unmatched, started = [], [], False
    for page in page_range:
        for raw in pages[page].split("\n"):
            line = clean(raw)
            if not line:
                continue
            if not started:
                if start_marker in line:
                    started = True
                continue
            if stop_marker and stop_marker in line:
                return out, unmatched
            m = row.match(line)
            if m:
                out.append({
                    "name": m.group("name").strip(),
                    "year": int(m.group("year")),
                    "counties": [alias[c] for c in split.findall(m.group("counties"))],
                    "page": page,
                })
            elif re.match(r"^[A-Z]", line) and not FURNITURE.match(line):
                unmatched.append({"page": page, "line": line[:120]})
    return out, unmatched


def parse_county_seats(pages, alias, cty):
    """-> {county: seat}. The seat is a column of the COUNTIES table, so it is
    a county's fact; the year the county was created sits beside it and is
    deliberately NOT taken (it is outside the permission's three facts)."""
    row = re.compile(r"^(%s)\s*\(\d{4}\)\s+([A-Z][A-Za-z.' ]*?)\s+[\d,]{4,}\b" % cty)
    seats = {}
    for page in COUNTY_PAGES:
        for raw in pages[page].split("\n"):
            m = row.match(clean(raw))
            if m:
                seats[alias[m.group(1)]] = m.group(2).strip()
    return seats


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    import pdfplumber  # heavy; function-local so validate_workflow_deps stays happy

    alias, cty = county_alternation()
    with pdfplumber.open(fetch_pdf()) as pdf:
        pages = {i + 1: (p.extract_text() or "") for i, p in enumerate(pdf.pages)}

    cities, city_bad = parse_municipalities(pages, CITY_PAGES, "First class cities", alias, cty)
    villages, village_bad = parse_municipalities(
        pages, VILLAGE_PAGES, "Wisconsin villages", alias, cty,
        stop_marker="cities and villages over 10,000")
    seats = parse_county_seats(pages, alias, cty)

    if len(cities) != EXPECT_CITIES:
        raise SystemExit(
            "parsed %d cities against the source's own class headings (1 + 16 + "
            "34 + 139 = %d). The table reshaped, or a row shape is unhandled: %s"
            % (len(cities), EXPECT_CITIES, city_bad[:5]))
    if len(villages) < MIN_VILLAGES:
        raise SystemExit("parsed %d villages (floor %d) — unmatched: %s"
                         % (len(villages), MIN_VILLAGES, village_bad[:5]))
    if len(seats) != 72:
        raise SystemExit("parsed a county seat for %d of 72 counties — missing %s"
                         % (len(seats), sorted(set(alias.values()) - set(seats))))

    payload = {
        "edition": EDITION,
        "snapshot": SNAPSHOT,
        "sourceUrl": SOURCE_URL,
        "cities": cities,
        "villages": villages,
        "countySeats": seats,
        "unmatched": {"cities": city_bad, "villages": village_bad},
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print("scraped %d cities / %d villages / %d county seats -> %s"
          % (len(cities), len(villages), len(seats), out_path))
    multi = sum(1 for r in cities + villages if len(r["counties"]) > 1)
    print("  %d municipalities name more than one county (trap 4)" % multi)
    for label, bad in (("cities", city_bad), ("villages", village_bad)):
        if bad:
            print("  %d unmatched capitalised line(s) in %s — read them:" % (len(bad), label))
            for b in bad[:5]:
                print("     p%d %s" % (b["page"], b["line"]))


if __name__ == "__main__":
    main()
