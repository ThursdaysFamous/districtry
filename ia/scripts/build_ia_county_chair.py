#!/usr/bin/env python3
"""Build stage 2: ia/data/app/ia-county-board-chairs.json.

Reads BOTH chair scrapers' caches and writes the roster the County
Supervisor card joins by name. A SEPARATE FILE FROM `ia-county-officers.json` ON PURPOSE:
that file is rebuilt weekly from its own sources, so writing chairs into it
would have each pipeline silently erase the other's work. This is the shape
Illinois already uses for Lake County's board roles -- a roles file that
joins to a members file by name -- and the join is the card's, not the
builder's, so a chair who leaves the board simply stops rendering.

TWO ROUTES, FLOORED SEPARATELY
--------------------------------
`ia_county_chair_scraper.py` reads each county's BOARD PAGE and answers 35
counties. `ia_county_minutes_chair_scraper.py` reads each county's own
MINUTES and answers 4 more -- big counties whose board pages never use the
word. It RESOLVES a fifth, Johnson, and does not ship it: Johnson publishes
its minutes through a Granicus portal whose robots.txt refuses this agent on
every path, so the scraper asks first and never fetches. Each route has its OWN floor
and its own count in the log, because a pooled floor cannot see one route
collapse behind the other's healthy number: 4 of 39 is a tenth of this file,
so the minutes route could stop working entirely without a single gate
noticing. That is the same lesson
`check_roster_retention.py` records as "coverage is measured PER SOURCE, not
per file", applied one layer up.

WHERE THE ROUTES DISAGREE, THE COUNTY IS DROPPED
-------------------------------------------------
Two surfaces a county publishes itself can name different chairs, and this
is not hypothetical: Des Moines County's boards-and-commissions page reads
`Tom Broeker, Chair` -- his chairmanship of a different body -- while its own
minutes of 25 August 2026 open "with Chair Shane McCampbell, Vice-Chair Tom
Broeker". The page route excludes that page and the minutes route reads the
minutes, so today the two agree wherever both answer. When they stop
agreeing the county is DROPPED with a printed line, never resolved by
preferring one route: two county-published surfaces disagreeing about a name
is the case this project asks about rather than guesses at. Dropping is also
the safe failure -- the card simply stops marking a chair -- where a hard
build failure would take the whole weekly refresh down for one county's
transition week.

WHAT THIS REFUSES TO WRITE, AND WHY EACH ONE IS HERE
-----------------------------------------------------
* Fewer than MIN_PAGE counties from the board-page route, or fewer than
  MIN_MINUTES from the minutes route. Both floors sit BELOW what was
  measured, because the sources are separate county websites and one of them
  redesigning is ordinary churn, not a broken parser. What a floor catches is
  a COLLAPSE -- the parser stopped working, or the network did. Per-county
  loss is `check_roster_retention.py`'s job once this file ships.
* A chair who is not on that county's own supervisor roster. The scraper
  already gates on this; the builder re-gates because the two stages run
  against `ia-county-officers.json` at different times and that file has its
  own weekly refresh. A name that no longer appears there is DROPPED, never
  carried forward on the strength of last week's scrape.
* Any county the scraper reported with two candidates. It collapses those to
  `many` itself and none of 98 produced one, so this is an assertion about a
  thing that has never happened rather than a filter that does work.

Every join whose page form differs from the roster form is PRINTED on every
run -- `Mr. Mike Hadley` against Keokuk's `Michael C. Hadley` -- so a reviewer
sees the four inexact matches rather than trusting a diminutive table.

Usage:
    python3 ia/scripts/build_ia_county_chair.py [--check]
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "app")
CACHE = os.path.join(HERE, ".cache", "ia_county_chairs.json")
MINUTES_CACHE = os.path.join(HERE, ".cache", "ia_county_minutes_chairs.json")
OFFICERS = os.path.join(DATA, "ia-county-officers.json")
OUT_PATH = os.path.join(DATA, "ia-county-board-chairs.json")

MIN_PAGE = 30               # measured 35 of 98 on 2026-09-05 (36 before the
                            # qualified-chair and expired-term refusals)
MIN_MINUTES = 3             # measured 4 of the 10 largest chair-less counties
                            # on 2026-09-05; the other six are recorded, with
                            # what refused each, in the minutes scraper. FIVE
                            # counties yield a chair and only four ship:
                            # Johnson's minutes live on johnson-county.
                            # granicus.com, whose robots.txt refuses
                            # `districtry` on every path, so its pages are
                            # never requested.
SOURCE_NOTE = ("each county's own board-of-supervisors page or its own board "
               "minutes, paired structurally and gated on the county's "
               "supervisor roster")


def _roster(officers, fips):
    return [m["name"] for m in (officers.get(fips) or {}).get("supervisors", [])]


def collect_page(rows, officers, out, inexact, dropped):
    """The board-page route: rows straight from ia_county_chair_scraper."""
    n = 0
    for r in sorted(rows, key=lambda x: x["fips"]):
        if r.get("verdict") != "one":
            continue
        assert r.get("chair"), "a verdict of one with no chair: %r" % r
        fips = "19" + r["fips"]
        if r["chair"] not in _roster(officers, fips):
            dropped.append((r["county"], r["chair"], "page"))
            continue
        rec = {"county": r["county"], "chair": r["chair"], "route": "page",
               "sourceUrl": r["sourceUrl"]}
        if r.get("match") != "exact":
            rec["pageName"] = r["pageName"]
            rec["match"] = r["match"]
            inexact.append((r["county"], r["chair"], r["pageName"], r["match"]))
        out[fips] = rec
        n += 1
    return n


def collect_minutes(rows, officers, out, dropped, conflicts):
    """The minutes route, merged onto whatever the page route already has."""
    n = 0
    for r in sorted(rows, key=lambda x: x["fips"]):
        if r.get("verdict") != "one":
            continue
        assert r.get("chair"), "a verdict of one with no chair: %r" % r
        fips = "19" + r["fips"]
        if r["chair"] not in _roster(officers, fips):
            dropped.append((r["county"], r["chair"], "minutes"))
            continue
        n += 1
        have = out.get(fips)
        if have is None:
            out[fips] = {"county": r["county"], "chair": r["chair"],
                         "route": "minutes", "sourceUrl": r["sourceUrl"],
                         "meetingDate": r.get("meetingDate")}
            continue
        if have["chair"] == r["chair"]:
            # both routes, same name: say so rather than silently preferring one
            have["route"] = "page+minutes"
            have["meetingDate"] = r.get("meetingDate")
            continue
        conflicts.append((r["county"], have["chair"], r["chair"]))
        del out[fips]
    return n


def build(page_rows, minutes_rows, officers):
    out, inexact, dropped, conflicts = {}, [], [], []
    n_page = collect_page(page_rows, officers, out, inexact, dropped)
    n_min = collect_minutes(minutes_rows, officers, out, dropped, conflicts)
    return out, inexact, dropped, conflicts, n_page, n_min


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file and exit non-zero on drift")
    args = ap.parse_args()

    for path, script in ((CACHE, "ia_county_chair_scraper.py"),
                         (MINUTES_CACHE, "ia_county_minutes_chair_scraper.py")):
        if not os.path.exists(path):
            sys.exit("build-ia-county-chair: FAIL — no scraper cache at %s; run "
                     "ia/scripts/%s first" % (path, script))
    rows = json.load(open(CACHE, encoding="utf-8"))
    minutes = json.load(open(MINUTES_CACHE, encoding="utf-8"))["counties"]
    officers = json.load(open(OFFICERS, encoding="utf-8"))
    out, inexact, dropped, conflicts, n_page, n_min = build(rows, minutes, officers)

    for county, chair, route in dropped:
        print("  DROPPED %s (%s route): %r is not on the county's supervisor roster"
              % (county, route, chair))
    for county, chair, page, how in inexact:
        print("  name join (%s) %s: roster %r <- page %r" % (how, county, chair, page))
    for county, page_name, minutes_name in conflicts:
        print("  CONFLICT %s: the board page says %r and the minutes say %r — "
              "shipping neither" % (county, page_name, minutes_name))

    if n_page < MIN_PAGE:
        sys.exit("build-ia-county-chair: FAIL — the board-page route resolved %d "
                 "counties, floor is %d" % (n_page, MIN_PAGE))
    if n_min < MIN_MINUTES:
        sys.exit("build-ia-county-chair: FAIL — the minutes route resolved %d "
                 "counties, floor is %d" % (n_min, MIN_MINUTES))

    payload = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        have = open(OUT_PATH, encoding="utf-8").read() if os.path.exists(OUT_PATH) else ""
        if have != payload:
            sys.exit("build-ia-county-chair: FAIL — %s is not what this scrape "
                     "produces (%d counties)" % (OUT_PATH, len(out)))
        print("build-ia-county-chair: OK — %d counties (%d board page, %d minutes), "
              "shipped file current" % (len(out), n_page, n_min))
        return
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(payload)
    print("build-ia-county-chair: OK — wrote %d county board chairs (%d from the "
          "board-page route, %d from the minutes route) to %s"
          % (len(out), n_page, n_min, OUT_PATH))


if __name__ == "__main__":
    main()
