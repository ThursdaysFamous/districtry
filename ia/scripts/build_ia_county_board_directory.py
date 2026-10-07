#!/usr/bin/env python3
"""
Build data/app/ia-county-board-directory.json — one row per Iowa county
covered by ia-supervisor-districts.json, naming its board's size and its own
official website, so the county-supervisor card can send a reader to the
body that answers for them.

WHY THIS FILE EXISTS SEPARATELY FROM THE GEOMETRY
----------------------------------------------------
Iowa publishes no statewide roster of county supervisors (this fork's own
plan document confirms it, and no second source was found in the research
pass), so a reader's actual supervisor is only ever published by their own
county. The honesty rules say a card with no verifiable roster source links
to the official body rather than inventing a name, and this file is that
link — one verified URL per county, with the county's board size beside it.

`seats` is read back from the SHIPPED geometry (ia-supervisor-districts.json)
rather than restated here, so the two files can never disagree — the same
invariant Wisconsin's build_wi_county_board_directory.py enforces. Jones
County carried no row here until 2026-10-07, because it carried no row in the
geometry; it has both now, drawn from the county's own district file.

WHERE THE URLS CAME FROM
--------------------------
ia_county_directory_scraper.py reads every county's own website off the Iowa
State Association of Counties' member directory (one detail page per county,
each stating "Website: <url>" — verified 2026-08-27). That is the per-county
source of truth; this builder only joins it to the geometry's board sizes.

Usage:
    python3 ia/scripts/ia_county_directory_scraper.py     # refresh the cache first
    python3 ia/scripts/build_ia_county_board_directory.py
    python3 ia/scripts/build_ia_county_board_directory.py --check
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
GEOMETRY = os.path.join(APP_DATA_DIR, "ia-supervisor-districts.json")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "ia_county_directory.json")
OUT = os.path.join(APP_DATA_DIR, "ia-county-board-directory.json")


def main():
    check_only = "--check" in sys.argv[1:]

    with open(GEOMETRY) as f:
        geo = json.load(f)
    seats = {}
    plans = {}
    drawn = {}
    fips_by_county = {}
    for feat in geo["features"]:
        p = feat["properties"]
        county = p["COUNTY"]
        # Iowa Code 331.206's representation plan, read back from the same
        # shipped geometry `seats` comes from. It is carried here because the
        # County card needs it to say what a list of supervisors MEANS: under
        # plans 1 and 2 every voter votes on every seat, under plan 3 one
        # supervisor represents you, and an unqualified list of N names claims
        # the former (docs/EXPANSION_GUIDE.md Part 5, "PROVE 'AT LARGE' FROM A
        # CERTIFIED ELECTION DOCUMENT").
        if county in plans and plans[county] != p["PLANTYPE"]:
            raise RuntimeError(
                "%s carries two different PLANTYPE values (%s, %s) across its rows"
                % (county, plans[county], p["PLANTYPE"]))
        plans[county] = p["PLANTYPE"]
        if county in seats and seats[county] != p["NUMDISTRICTS"]:
            raise RuntimeError(
                "%s carries two different NUMDISTRICTS values (%d, %d) across its rows"
                % (county, seats[county], p["NUMDISTRICTS"])
            )
        seats[county] = p["NUMDISTRICTS"]
        drawn.setdefault(county, set()).add(p["DISTRICT"])
        fips_by_county[county] = p["FIPS"]

    # A SEAT COUNT TAKEN FROM A COLUMN WHEN THE FILE ITSELF DRAWS THE ANSWER.
    # `seats` came from the state's `NUMDISTRICTS` attribute alone, and for one
    # county that attribute contradicts its own file: WARREN draws five numbered
    # district polygons and says NUMDISTRICTS 3. The figure is not cosmetic --
    # `build_ia_county_officers.py` withholds a whole board when the ISAC
    # directory's supervisor count disagrees with it, so Warren's five
    # supervisors were withheld, with the reason naming the geometry, on the
    # strength of a column the geometry's own polygons disprove.
    #
    # For a county that draws NUMBERED districts the polygon count IS the seat
    # count and nothing has to be believed. For an at-large county the file
    # draws one polygon covering the whole county and the attribute is the only
    # statement of the board's size, so it is what is read -- which is why 42 of
    # the 43 counties whose polygon count differs from their attribute are not
    # disagreements at all.
    #
    # THE DISAGREEMENT IS PRINTED RATHER THAN SMOOTHED. A county whose two
    # statements differ is a finding about the state's layer, and a build that
    # quietly preferred one would hide the next one.
    for county, labels in sorted(drawn.items()):
        numbered = {d for d in labels if str(d).strip().isdigit()}
        if not numbered:
            continue
        if len(numbered) != seats[county]:
            print("  SEATS     %-15s draws %d numbered district(s) and says "
                  "NUMDISTRICTS %d -- the polygons decide"
                  % (county, len(numbered), seats[county]), file=sys.stderr)
        seats[county] = len(numbered)

    try:
        with open(CACHE) as f:
            directory_cache = json.load(f)
    except OSError as e:
        raise RuntimeError(
            "no ISAC directory cache at %s (%s) — run "
            "ia/scripts/ia_county_directory_scraper.py first" % (CACHE, e)
        )
    url_by_county_ci = {}
    for rec in directory_cache:
        name = rec["county_slug_name"].strip()
        if not rec.get("website"):
            continue
        url_by_county_ci[name.lower()] = (name, rec["website"])

    missing_url = sorted(c for c in seats if c.lower() not in url_by_county_ci)
    if missing_url:
        raise RuntimeError("no ISAC website found for: %s" % missing_url)

    directory = {}
    for county, fips in sorted(fips_by_county.items()):
        _, url = url_by_county_ci[county.lower()]
        directory[fips] = {"county": county, "seats": seats[county],
                           "plan": plans[county], "url": url}

    total = sum(v["seats"] for v in directory.values())
    from collections import Counter
    by_plan = Counter(v["plan"] for v in directory.values())
    print("ia-county-board-directory: %d counties, %d supervisor seats, %d official "
          "links | plans %s" % (len(directory), total, len(directory),
                                dict(sorted(by_plan.items()))), file=sys.stderr)

    payload = json.dumps(directory, indent=1, sort_keys=True) + "\n"
    if check_only:
        try:
            with open(OUT) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError(
                "data/app/ia-county-board-directory.json is missing (%s) — run this "
                "script without --check" % e
            )
        if shipped != payload:
            raise RuntimeError(
                "data/app/ia-county-board-directory.json has drifted from the shipped "
                "districts or the ISAC cache. Re-run: "
                "python3 ia/scripts/build_ia_county_board_directory.py"
            )
        print("check: shipped directory matches the shipped districts", file=sys.stderr)
        return

    with open(OUT, "w") as f:
        f.write(payload)
    print("wrote data/app/ia-county-board-directory.json", file=sys.stderr)


if __name__ == "__main__":
    main()
