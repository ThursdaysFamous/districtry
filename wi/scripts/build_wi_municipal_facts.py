#!/usr/bin/env python3
"""
Build data/app/wi-municipal-facts.json and data/app/wi-county-facts.json from
the Blue Book section 190 scrape — stage 2 of the pair
(wi_bluebook_municipal_scraper.py is stage 1).

TWO FILES, BECAUSE THE SOURCE HOLDS TWO DIFFERENT KINDS OF FACT and measuring
that was the whole design question:

  * wi-municipal-facts.json — keyed by PLACE GEOID. The incorporation year and
    the county or counties of each city and village. Both are per-municipality
    facts and both come off the cities/villages tables.
  * wi-county-facts.json — keyed by COUNTY GEOID. The county seat, which is a
    COLUMN OF THE COUNTIES TABLE and therefore a county's own fact.

THE COUNTY SEAT IS NOT PROJECTED ONTO MUNICIPALITIES, and the measurement is
why. Read county-keyed it is clean, 72 of 72. Matched onto the city/village
fabric it is 67 clean, and it manufactures five problems the source does not
have:

  * THREE COUNTY SEATS ARE NOT INCORPORATED MUNICIPALITIES AT ALL. Burnett's
    seat is Meenon, Florence's is Florence and Menominee's is Keshena — a town,
    a town and an unincorporated community. Nothing on a City or Village card
    could carry them.
  * TWO ARE AMBIGUOUS. Douglas County has a City AND a Village of Superior;
    Waukesha County has a City AND a Village of Waukesha. The seat column
    prints a NAME and no class, so the data does not say which — and choosing
    the city because it is the bigger one is an inference, not a reading.

So the seat ships against the county it belongs to, where every one of the 72
is unambiguous, and the County card names it. That also keeps this build clear
of a name join it never needed.

WHAT IS DELIBERATELY NOT TAKEN. The permission (LICENSE-DATA.md section 4)
covers three facts. Section 190's tables also carry 2020 census counts, 2024
estimates, percentage change, population rank, land area, population density
and equalized value, and its counties table prints each county's YEAR CREATED
beside the seat. None of those ships. A later want for one asks the Bureau
again rather than citing this permission.

COVERAGE IS MEASURED, NOT ASSUMED: 607 of the app's 608 cities and villages.
The one absence is the VILLAGE OF GREENLEAF (place 5531375, Brown County),
which appears nowhere in section 190 because it incorporated after the table's
own January 1, 2024 snapshot — the Elections Commission's record of it dates
to 2024-08-22. That is the source being correctly dated rather than short, and
the card says so in those terms rather than rendering a blank.

THE COUNTY FIELD IMPROVES ON THE ONE THE CARD ALREADY SHOWS, which is why it
ships at all. wi-municipal-clerks.json carries the Elections Commission's
county, and for a municipality that straddles a county line the Commission
writes the uninformative "Multiple Counties" — 58 of the 608. Measured against
it, the Blue Book agrees on 538, names all the counties for 57 of those 58,
and disagrees NOWHERE on substance: the only 11 differences are the
Commission's "Fond Du Lac" against the Blue Book's "Fond du Lac", which is
also the shipped county fabric's own spelling. ONE row differs in kind and is
recorded rather than resolved: the Commission files the VILLAGE OF LAKE HALLIE
as Multiple Counties where the Blue Book names only Chippewa.

Floors (refuses to write otherwise): >= 600 municipalities, exactly 190
cities, exactly 72 county seats, and every county named by a municipality must
exist in the shipped fabric.
"""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
RAW = os.path.join(SCRIPT_DIR, ".cache", "wi_bluebook_municipal_raw.json")
MUNI_OUT = os.path.join(REPO_ROOT, "data", "app", "wi-municipal-facts.json")
COUNTY_OUT = os.path.join(REPO_ROOT, "data", "app", "wi-county-facts.json")
CLERKS = os.path.join(REPO_ROOT, "data", "app", "wi-municipal-clerks.json")
COUNTIES = os.path.join(REPO_ROOT, "data", "app", "state-counties.json")

MIN_MUNICIPALITIES = 600
EXPECT_CITIES = 190
EXPECT_COUNTIES = 72

# Measured 2026-09-10 and expected to stay: incorporated after the table's own
# January 1, 2024 snapshot, so the source is dated rather than short.
KNOWN_ABSENT = {"5531375": "Village of Greenleaf"}

# ONE BLUE BOOK ROW IS INCOMPLETE, AND IT IS MEASURED RATHER THAN PREFERRED.
#
# The Elections Commission files 58 of the 608 municipalities as "Multiple
# Counties". This source names more than one county for 57 of them. The 58th is
# the VILLAGE OF LAKE HALLIE, which the Blue Book files under Chippewa alone —
# so two state publishers disagree about one village, and the earlier version of
# this comparison did not notice because the 58 "Multiple Counties" rows carry
# no county NAME and were therefore excluded from a name-against-name check. The
# subset that was compared was exactly the subset where this disagreement cannot
# appear.
#
# A THIRD WITNESS SETTLES IT, and neither publisher is it: the Census place
# boundary this app already draws, intersected against the shipped county
# fabric. Lake Hallie's TIGER polygon is 99.30% inside Chippewa and 0.70% inside
# Eau Claire — 0.265 km2, four separate pieces, filling 41.5% of their own
# 1.88 x 0.34 km bounding box. THAT IS NOT A DIGITISATION SLIVER: a sliver hugs
# the shared line and fills a few percent of a long thin box. 26.5 hectares of
# the village lie in Eau Claire County.
#
# So the Commission is right that the village is multi-county and the Blue
# Book's row is short one name. The BLUE BOOK'S OWN VALUE STILL SHIPS in
# `counties`, because that field is what this source says and rewriting it would
# put a fact in the reader's hands that its cited source does not carry. The
# measurement rides beside it in `countiesAlso`, with its own reason, and the
# card states both. Never silently switch the value to the other publisher's.
MEASURED_COUNTY_EXTENSIONS = {
    "5541525": {
        "municipality": "Village of Lake Hallie",
        "also": ["Eau Claire"],
        "why": ("the Blue Book files this village under Chippewa alone, and the "
                "Wisconsin Elections Commission files it as Multiple Counties. "
                "Measured against the Census place boundary this app draws, "
                "0.70% of the village — 0.265 km2 in four pieces — lies in Eau "
                "Claire County, so the Commission is right and this row is one "
                "county short."),
        "measured": "2026-09-10",
    },
}


def norm(name):
    """Fold for the name join. The two surfaces differ only in punctuation
    (`St. Cloud` against `St Cloud`), never in letters."""
    return re.sub(r"\s+", " ", name.lower().replace(".", "")
                  .replace("'", "").replace("-", " ")).strip()


def main():
    argv = sys.argv[1:]
    raw_path = argv[argv.index("--in") + 1] if "--in" in argv else RAW
    with open(raw_path) as f:
        raw = json.load(f)
    with open(CLERKS) as f:
        clerks = json.load(f)
    with open(COUNTIES) as f:
        fabric = json.load(f)

    fabric_names = {feat["properties"]["BASENAME"]: str(feat["properties"]["GEOID"])
                    for feat in fabric["features"]}

    # the shipped municipal fabric, keyed (type, folded name) — the WEC's own
    # `wecMunicipality` is what records city vs village, and it is needed:
    # Pewaukee, Superior and Waukesha each exist as BOTH in one county.
    ship = {}
    for geoid, row in clerks.items():
        wec = (row.get("wecMunicipality") or "").upper()
        kind = "city" if wec.startswith("CITY") else "village" if wec.startswith("VILLAGE") else None
        if kind is None:
            raise SystemExit("%s (%s) records neither CITY nor VILLAGE in "
                             "wecMunicipality — the join keys on it"
                             % (geoid, row.get("municipality")))
        ship[(kind, norm(row["municipality"]))] = (geoid, row)

    municipal, unmatched = {}, []
    for kind, rows in (("city", raw["cities"]), ("village", raw["villages"])):
        for r in rows:
            key = (kind, norm(r["name"]))
            if key not in ship:
                unmatched.append("%s of %s" % (kind, r["name"]))
                continue
            geoid, _ = ship[key]
            for county in r["counties"]:
                if county not in fabric_names:
                    raise SystemExit("%s of %s names a county the shipped fabric "
                                     "does not have: %r" % (kind, r["name"], county))
            row = {
                "kind": kind,
                "incorporated": r["year"],
                "counties": r["counties"],
            }
            ext = MEASURED_COUNTY_EXTENSIONS.get(geoid)
            if ext:
                # A measured extension is only meaningful while the source still
                # omits it. If a later edition adds the county, this entry has
                # done its job and must be removed rather than left asserting a
                # disagreement that no longer exists.
                if set(ext["also"]) & set(r["counties"]):
                    raise SystemExit(
                        "%s now names %s itself — MEASURED_COUNTY_EXTENSIONS[%s] "
                        "is stale and should be deleted, not carried."
                        % (ext["municipality"], ext["also"], geoid))
                row["countiesAlso"] = ext["also"]
                row["countiesAlsoWhy"] = ext["why"]
            municipal[geoid] = row

    if unmatched:
        raise SystemExit("%d Blue Book municipalities matched nothing in the app's "
                         "own fabric: %s" % (len(unmatched), unmatched[:8]))
    if len(municipal) < MIN_MUNICIPALITIES:
        raise SystemExit("only %d municipalities resolved (floor %d)"
                         % (len(municipal), MIN_MUNICIPALITIES))
    cities = sum(1 for v in municipal.values() if v["kind"] == "city")
    if cities != EXPECT_CITIES:
        raise SystemExit("%d cities resolved, expected %d" % (cities, EXPECT_CITIES))

    # A municipality the app ships and this source does not must be one this
    # build already knows about, or the snapshot has moved under us.
    missing = sorted(set(clerks) - set(municipal))
    surprise = [m for m in missing if m not in KNOWN_ABSENT]
    if surprise:
        raise SystemExit(
            "%d municipalit(ies) the app ships are absent from the Blue Book and "
            "are not the recorded post-snapshot incorporation(s): %s. A new "
            "edition, or a new incorporation — read it before widening "
            "KNOWN_ABSENT." % (len(surprise), [(m, clerks[m].get("municipality")) for m in surprise[:6]]))

    seats = raw["countySeats"]
    if len(seats) != EXPECT_COUNTIES:
        raise SystemExit("%d county seats, expected %d" % (len(seats), EXPECT_COUNTIES))
    county = {}
    for name, seat in seats.items():
        if name not in fabric_names:
            raise SystemExit("county seat table names %r, not in the shipped fabric" % name)
        county[fabric_names[name]] = {"county": name, "seat": seat}

    meta = {
        "asOf": "%s (%s)" % (raw["edition"], raw["snapshot"]),
        "sourceUrl": raw["sourceUrl"],
        "source": "Wisconsin Legislative Reference Bureau",
    }
    for path, payload, label in ((MUNI_OUT, municipal, "municipalities"),
                                 (COUNTY_OUT, county, "county seats")):
        body = dict(payload)
        body["_meta"] = meta
        with open(path, "w") as f:
            json.dump(body, f, indent=1, ensure_ascii=False, sort_keys=True)
        print("wrote %s — %d %s, %.0f KB"
              % (path, len(payload), label, os.path.getsize(path) / 1024.0))

    multi = sum(1 for v in municipal.values() if len(v["counties"]) > 1)
    print("  %d city, %d village; %d name more than one county" % (cities, len(municipal) - cities, multi))
    for geoid, ext in sorted(MEASURED_COUNTY_EXTENSIONS.items()):
        if geoid not in municipal:
            raise SystemExit("MEASURED_COUNTY_EXTENSIONS names %s (%s), which "
                             "this build does not carry" % (geoid, ext["municipality"]))
        print("  measured extension: %s also lies in %s (%s)"
              % (ext["municipality"], ", ".join(ext["also"]), ext["measured"]))
    for geoid, why in sorted(KNOWN_ABSENT.items()):
        print("  not in this edition: %s (%s) — incorporated after the %s snapshot"
              % (why, geoid, raw["snapshot"]))


if __name__ == "__main__":
    main()
