#!/usr/bin/env python3
"""Voting precincts for the counties whose Census 2020 fabric is still their own.

WHY THIS EXISTS, AND WHAT IT CORRECTS. Seventeen of Illinois's ninety-one served
counties ship no precinct layer, and seven of them are drawn here. Six of those
seven carried a gap record, and all six gave the same reason — the county
publishes no precinct map file — which is the wrong question. Pike's record says
so in the sentence that closed it: "The precincts themselves are certainly
defined ... but only as names." Names are the whole input this route needs. Ten
counties already ship precincts built exactly this way (Johnson, Perry,
Gallatin, Cumberland, Pulaski, Hardin, Cass, Greene, Scott, Moultrie), none of
which publishes a map file either. The seventh, Union, had no record at all,
which is the absence the 2026-08-23 audit exists to surface.

MASON IS THE CASE THAT FORCED THE AUDIT. Its gap record states, as a fact about
the shipped app, that "Mason County's 21 precincts are drawn from 2020 census
boundaries" and that the census carries "exactly the set of 21 shapes the app
already holds". The app holds none of them: mason-precincts.json has never
existed and no dispatch entry has ever named the county. A reader of the Data
gaps panel was being told the precincts were drawn while the map drew nothing.

WHERE THE NAMES COME FROM. ISBE publishes each county's certified precinct-level
return as CSV (scripts/isbe_precinct_fabric.py reads the same archive as a
re-precincting tripwire). That file is the COUNTY'S canvass, published by the
state, so it is a county source and not a state one. TWO WITNESSES PER COUNTY:
the 2024 General (election 66) and the 2026 General Primary (election 69) name
the same precincts in all seven counties here, so a name is never taken from a
single ballot.

SUB-PRECINCT REPORTING UNITS ARE NOT PRECINCTS. Massac reports ADKINS-17 and
ADKINS-17B on the same canvass, five such pairs in 2024 and one in 2026, and its
own Clerk's report heads every countywide contest "Precincts Counted 17 / Total
17". A `-<digits>B` row is a part of the precinct it names, the shape Richland's
record already documents; counting them makes Massac read as 22 precincts in one
election and 18 in the next. They are dropped, and the count that survives is
the same 17 in both.

THE ALIASES, WHICH ARE RENAMES AND NEVER MERGES. apply_aliases enforces that:
each must name a census feature that exists and a county name that does not, and
no two may point at the same feature. Three shapes occur here.
  * A VESTIGIAL TRAILING 1 — census ALLENS GROVE 1 for the county's ALLENS
    GROVE. The base names are identical and the census carries no second
    Allens Grove, so the pairing is forced.
  * THE COUNTY'S PRECINCT NUMBER APPENDED — census BELLMONT 14 for Wabash's
    BELLMONT, ADKINS 17 for Massac's ADKINS. Identical base name, one census
    feature each, so again forced.
  * A DROPPED WORD — Saline's EAST ELDORADO #1 against the census's ELDORADO 1.
    This is the only alias here whose base names differ, so it is the only one
    that needs an argument beyond the name: East Eldorado is the county's ONLY
    Eldorado township (Census 2020 county subdivisions list thirteen townships
    for Saline and no other Eldorado), the six census ELDORADO n are the only
    unmatched census names, the six county EAST ELDORADO #n are the only
    unmatched county names, and the ordinals run 1-6 on both sides. The
    numbering is the county's own, submitted by the county to the Census
    Bureau's voting-district programme, so ELDORADO n IS East Eldorado n.

WASHINGTON WAS BUILT AND THEN DROPPED, AND THE REASON IS THE CHECK WORTH
KEEPING. Read through isbe_precinct_fabric.precinct_key, which strips a trailing
reporting id, Washington reconciles perfectly: 19 county names against 21 census
voting districts, with DUBOIS 1 + DUBOIS 2 and HOYLETON 1 + HOYLETON 2 as two
nameable merges. The RAW canvass says otherwise. Washington reports DuBois,
Johannisburg, Lively Grove and Venedy at TWO ids each in both elections
(DuBOIS-005 and DuBOIS-006 in 2026) and Hoyleton at ONE — so the four names the
county reports twice and the two the census splits agree on DuBois alone. Under
one reading the county runs 23 precincts and four of them have no census
counterpart; under the other it runs 19 and the census's Hoyleton split has no
county counterpart. Neither can be settled from the returns, so nothing ships
and the county's gap record now says this instead of "the county runs no mapping
system". EVERY COUNTY HERE IS CHECKED AGAINST THE RAW NAMES, not the stripped
ones: a base name that appears at two ids is a question, never a duplicate to
collapse.

WHAT SHIPS AND WHAT DOES NOT. The geometry is the census fabric; the NAME is the
county's own, spelled as its certified returns spell it (Mt. Carmel, George's
Creek, East Eldorado #1), because that is the name on a reader's poll card. Where
the two publishers disagree it is the county's spelling that ships, which is why
the census's vestigial trailing 1 and its appended precinct number both
disappear. NO POLLING PLACE ships — that belongs with a roster guard and a date,
the rule Calhoun's build set. NO BOARD DISTRICT ships: six of these seven
counties elect their boards county-wide, and the one that does not (Mason)
already ships its board districts as their own layer. NO ROSTER ships.

CLAY IS THE NEXT COUNTY THIS ROUTE REACHES AND IS NOT HERE, and this paragraph
said the wrong thing about why until 2026-09-11. It claimed the county's board
page "names Clay City under both District A and District B", making the
disagreement one about DISTRICTS with "the count eighteen on both surfaces".
IT IS NOT. The board page names CLAY CITY I in District A and CLAY CITY II in
District B — two differently-named slots, not one precinct listed under two
districts — so this is not the Jackson, Douglas or Shelby shape, where a
canvass repeats one precinct's own name under each district it lies in. Clay's
recorded board-only decision was better founded than that paragraph allowed,
and it stands.

What the route CAN say about Clay is this. The raw-canvass duplicate check
above was run on 2026-09-11 and Clay passes it: eighteen base names in the 2024
General and eighteen in the 2026 General Primary, no name at two reporting ids
and no sub-precinct unit, with only a PRESIDENTIAL ONLY BALLOT class to drop.
The census fabric carries all eighteen after eleven renames (roman ordinals,
plus a vestigial trailing I on CLAY CITY I, LARKINSBURG I and PIXLEY I). So the
ONLY thing between Clay and a precinct layer is whether the county runs one
Clay City precinct or two — its certified returns report one at one id in both
elections, its board page names two — and that is a question for the Clerk
rather than an inference to make here. It is drafted as an ask and recorded in
the clay-precinct-geometry gap.

WHAT THE POPULATION IDENTITY DOES NOT PROVE, said plainly: that the voting
districts sum to the county's own Census 2020 count shows the fabric tiled the
county in 2020, never that no line has moved since. That assurance comes from the
county's own returns naming the same precincts in 2024 and 2026, which is the
strongest statement available where the county draws no map.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run when a county
re-precincts — scripts/isbe_precinct_fabric.py --compare is the tripwire that
says when — or when TIGERweb republishes the voting-district fabric. Output is
deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_vtd_precincts.py                 # write all seven
    python3 scripts/build_vtd_precincts.py --county mason  # one county
    python3 scripts/build_vtd_precincts.py --check         # shipped == fresh
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

# ISBE's own election ids, as scripts/isbe_precinct_fabric.py --list prints them.
WITNESSES = ("2024 General (ISBE election 66)",
             "2026 General Primary (ISBE election 69)")
ARCHIVE_URL = ("https://www.elections.il.gov/ElectionOperations/"
               "ElectionVoteTotals.aspx")

MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999

fail = make_fail("vtd-precincts")


# Each county's own precinct names, spelled as its certified returns spell them,
# identical in both witness elections. `aliases` re-keys a census feature onto
# the county's spelling. Every county here is one precinct per voting district;
# a county whose precincts are unions of whole voting districts is the Calhoun
# shape and needs check_fabric_composed, which no county in this table uses.
COUNTIES = {
    "mason": {
        "fips": "125", "pop2020": 13086, "county": "Mason County",
        "precincts": (
            "ALLENS GROVE", "BATH 1", "CRANE CREEK", "FOREST CITY",
            "HAVANA 1", "HAVANA 2", "HAVANA 3", "HAVANA 4", "HAVANA 5",
            "HAVANA 6", "KILBOURNE", "LYNCHBURG", "MANITO 1", "MANITO 2",
            "MASON CITY 1", "MASON CITY 2", "MASON CITY 3", "PENNSYLVANIA",
            "QUIVER", "SALT CREEK", "SHERMAN"),
        "aliases": {"ALLENS GROVE": "ALLENS GROVE 1",
                    "KILBOURNE": "KILBOURNE 1"},
        "board": ("Mason County's two board districts are unions of whole "
                  "townships and ship as their own layer, so no board district "
                  "is carried here."),
    },
    "pike": {
        "fips": "149", "pop2020": 14739, "county": "Pike County",
        "precincts": (
            "ATLAS 1", "BARRY 1", "BARRY 2", "CHAMBERSBURG 1", "CINCINNATI",
            "DERRY 1", "DETROIT 1", "FAIRMOUNT 1", "FLINT 1", "GRIGGSVILLE 1",
            "GRIGGSVILLE 2", "HADLEY 1", "HARDIN 1", "KINDERHOOK 1",
            "KINDERHOOK 2", "LEVEE 1", "MARTINSBURG 1", "MONTEZUMA 1",
            "NEW SALEM 1", "NEW SALEM 2", "NEWBURG 1", "PEARL 1", "PERRY 1",
            "PITTSFIELD 1", "PITTSFIELD 2", "PITTSFIELD 3", "PITTSFIELD 4",
            "PLEASANT HILL 1", "PLEASANT VALE 1", "ROSS 1", "SPRING CREEK 1"),
        "aliases": {"CINCINNATI": "CINCINNATI 1"},
        "board": ("Pike County elects its nine commissioners county-wide, so "
                  "there is no board district for a precinct to belong to."),
    },
    "union": {
        "fips": "181", "pop2020": 17244, "county": "Union County",
        "precincts": (
            "ALTO PASS", "ANNA 1", "ANNA 2", "ANNA 3", "ANNA 4", "ANNA 5",
            "ANNA 6", "ANNA 7", "BALCOM", "COBDEN 1", "COBDEN 2", "DONGOLA 1",
            "DONGOLA 2", "JONESBORO 1", "JONESBORO 2", "JONESBORO 3",
            "LICK CREEK", "MILL CREEK", "STOKES", "UNION"),
        "aliases": {"UNION": "UNION 1"},
        "board": ("Union County elects its five commissioners county-wide — its "
                  "own returns count every lettered seat in all twenty "
                  "precincts — so there is no board district for a precinct to "
                  "belong to."),
    },
    "edwards": {
        "fips": "047", "pop2020": 6245, "county": "Edwards County",
        "precincts": (
            "ALBION 1", "ALBION 2", "ALBION 3", "BONE GAP", "BROWNS", "DIXON",
            "ELLERY", "FRENCH CREEK", "SALEM 1", "SALEM 2", "SHELBY 1",
            "SHELBY 2"),
        "aliases": {},
        "board": ("Edwards County elects its three commissioners county-wide, "
                  "so there is no board district for a precinct to belong to."),
    },
    "wabash": {
        "fips": "185", "pop2020": 11361, "county": "Wabash County",
        "precincts": (
            "BELLMONT", "COFFEE", "COMPTON", "FRIENDSVILLE", "LANCASTER",
            "LICK PRAIRIE", "MT. CARMEL 1", "MT. CARMEL 2", "MT. CARMEL 3",
            "MT. CARMEL 4", "MT. CARMEL 5", "MT. CARMEL 6", "MT. CARMEL 7",
            "MT. CARMEL 8", "MT. CARMEL 9", "WABASH"),
        "aliases": {"BELLMONT": "BELLMONT 14", "COFFEE": "COFFEE 15",
                    "COMPTON": "COMPTON 16", "FRIENDSVILLE": "FRIENDSVILLE 11",
                    "LANCASTER": "LANCASTER 12", "LICK PRAIRIE": "LICK PRAIRIE 13",
                    "WABASH": "WABASH 10"},
        "board": ("Wabash County elects its three commissioners county-wide — "
                  "one each General Election for a six-year term, the election "
                  "authority in writing — so there is no board district for a "
                  "precinct to belong to."),
    },
    "saline": {
        "fips": "165", "pop2020": 23768, "county": "Saline County",
        "precincts": (
            "BRUSHY", "CARRIER MILLS #1", "CARRIER MILLS #2", "COTTAGE",
            "EAST ELDORADO #1", "EAST ELDORADO #2", "EAST ELDORADO #3",
            "EAST ELDORADO #4", "EAST ELDORADO #5", "EAST ELDORADO #6",
            "GALATIA", "HARRISBURG #1", "HARRISBURG #2", "HARRISBURG #3",
            "HARRISBURG #4", "HARRISBURG #5", "HARRISBURG #6", "HARRISBURG #7",
            "HARRISBURG #8", "HARRISBURG #9", "HARRISBURG #10", "INDEPENDENCE",
            "LONG BRANCH", "MOUNTAIN", "RALEIGH", "RECTOR", "STONEFORT",
            "TATE"),
        "aliases": {"EAST ELDORADO #1": "ELDORADO 1",
                    "EAST ELDORADO #2": "ELDORADO 2",
                    "EAST ELDORADO #3": "ELDORADO 3",
                    "EAST ELDORADO #4": "ELDORADO 4",
                    "EAST ELDORADO #5": "ELDORADO 5",
                    "EAST ELDORADO #6": "ELDORADO 6"},
        "board": ("Saline County elects its thirteen board members county-wide, "
                  "so there is no board district for a precinct to belong to."),
    },
    "massac": {
        "fips": "127", "pop2020": 14169, "county": "Massac County",
        "precincts": (
            "ADKINS", "BENTON", "EAST BROOKLYN", "FRANKLIN", "GEORGE'S CREEK",
            "GRANT", "HILLERMAN", "JACKSON", "JEFFERSON", "LINCOLN", "LOGAN",
            "METROPOLIS 1", "METROPOLIS 2", "METROPOLIS 3", "METROPOLIS 4",
            "WASHINGTON", "WEST BROOKLYN"),
        "aliases": {"ADKINS": "ADKINS 17", "BENTON": "BENTON 10",
                    "EAST BROOKLYN": "EAST BROOKLYN 7", "FRANKLIN": "FRANKLIN 15",
                    "GEORGE'S CREEK": "GEORGES CREEK 11", "GRANT": "GRANT 14",
                    "HILLERMAN": "HILLERMAN 13", "JACKSON": "JACKSON 8",
                    "JEFFERSON": "JEFFERSON 16", "LINCOLN": "LINCOLN 5",
                    "LOGAN": "LOGAN 12", "WASHINGTON": "WASHINGTON 9",
                    "WEST BROOKLYN": "WEST BROOKLYN 6"},
        "board": ("Massac County elects its three commissioners county-wide, so "
                  "there is no board district for a precinct to belong to."),
    },
}

# The county's own spelling is what ships, and title_case renders an ALL-CAPS
# canvass name for a card. Two names it cannot reach are stated outright rather
# than left to a rule: the county writes MT. CARMEL with a stop where the census
# does not, and GEORGE'S CREEK with an apostrophe where the census writes none —
# both come through title_case correctly, so nothing is overridden here today.
# This table exists so a future name that title_case mangles has a home that is
# not a special case inside the loop.
EXPLICIT_LABELS = {}


def label_for(county_name):
    return EXPLICIT_LABELS.get(county_name) or V.title_case(county_name)


def build_one(slug, spec, check):
    from shapely.geometry import shape, mapping   # noqa: E402  (heavy, local)
    from shapely.ops import unary_union, transform  # noqa: E402

    precincts = spec["precincts"]

    vtds = V.fetch_vtds(spec["fips"], shape, fail)
    county_geom, county_pop = V.fetch_county(spec["fips"], shape, fail)
    if county_pop != spec["pop2020"]:
        fail("%s: census county population is %d, expected %d"
             % (slug, county_pop, spec["pop2020"]))
    V.apply_aliases(vtds, spec.get("aliases") or {}, fail)

    composition = {label_for(name): [name] for name in precincts}
    if len(composition) != len(precincts):
        fail("%s: two precincts render to the same label" % slug)

    # The Jasper test proper: names one-for-one AND the population identity.
    V.check_fabric(vtds, precincts, county_pop, fail)
    # One voting district per precinct, so check_partition cannot fail here
    # today. It runs anyway, because it is what would catch a future rebuild in
    # which a name is claimed twice or a voting district left over.
    V.check_partition(composition, vtds, fail)

    shapes, pops = V.dissolve(composition, vtds, unary_union)
    overlap, covered = V.check_tiling(shapes, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED,
                                      unary_union, fail)

    features = []
    for name in sorted(composition):
        features.append({
            "type": "Feature",
            "properties": {"name": name, "pop2020": pops[name]},
            "geometry": V.round_geom(shapes[name], mapping),
        })

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": ("Census 2020 voting districts under %s's own precinct "
                       "names, as its certified returns spell them"
                       % spec["county"]),
            "resultsUrl": ARCHIVE_URL,
            "note": ("%s's %d voting precincts. The geometry is the Census 2020 "
                     "voting-district fabric, which sums to the county's exact "
                     "2020 population of %s; the names are the county's own, "
                     "taken from its certified returns and identical in the %s "
                     "and the %s. %s No polling place is carried, and no "
                     "roster."
                     % (spec["county"], len(composition), "{:,}".format(county_pop),
                        WITNESSES[0], WITNESSES[1], spec["board"])),
        },
        "features": features,
    }

    out = os.path.join(OUT_DIR, "%s-precincts.json" % slug)
    print("%s-precincts: %d voting districts -> %d precincts (pop %s = census "
          "POP100)" % (slug, len(vtds), len(composition),
                       "{:,}".format(county_pop)))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    return out, V.dumps(payload)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files match a fresh build")
    ap.add_argument("--county", metavar="SLUG",
                    help="build one county instead of all of them")
    args = ap.parse_args()

    slugs = sorted(COUNTIES)
    if args.county:
        if args.county not in COUNTIES:
            fail("no county %r — this script builds %s"
                 % (args.county, ", ".join(slugs)))
        slugs = [args.county]

    written = []
    for slug in slugs:
        written.append(build_one(slug, COUNTIES[slug], args.check))
    V.write_or_check(written, args.check, REPO_ROOT, fail, "vtd-precincts")


if __name__ == "__main__":
    main()
