#!/usr/bin/env python3
"""Voting precincts for the counties whose Census 2020 fabric is still their own.

WHY THIS EXISTS, AND WHAT IT CORRECTS. Seventeen of Illinois's ninety-one served
counties shipped no precinct layer when this file was written, and EIGHT of them
are drawn here. Six of the first seven carried a gap record, and all six gave the
same reason — the county publishes no precinct map file — which is the wrong
question. (The eighth, Clay, is the exception and is described below: its record
named a real obstacle rather than the wrong question, and it took a third
publisher to clear.) Pike's record says
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
the same precincts in all eight counties here, so a name is never taken from a
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
the rule Calhoun's build set. NO BOARD DISTRICT ships: six of these eight
counties elect their boards county-wide, and the two that do not (Mason and
Clay) already ship their board districts as their own layer. NO ROSTER ships.

CLAY WAS THE EIGHTH AND IT TOOK A THIRD PUBLISHER, not a better reading of the
two already in hand. Everything about it reconciled except a count: the
county's certified returns report ONE precinct named CLAY CITY at one reporting
id in both witness elections, and its County Board page names CLAY CITY I in
District A and CLAY CITY II in District B. Two differently-named slots are not
the Jackson, Douglas or Shelby shape, where a canvass repeats one precinct's
OWN name under each district it lies in — so eighteen could not be inferred
from the returns and nineteen could not be inferred from the board page, and
the county was held back on 2026-08-26 and again on 2026-09-11 for exactly that
reason.

THE CLERK'S OWN POLLING LIST SETTLED IT, and what makes it readable is its
internal structure rather than its authority. claycounty.illinois.gov's
elections page publishes "a list of all current polling locations in Clay
County": eighteen rows, one of them Clay City. A polling notice normally CANNOT
be read as a precinct list — Cumberland's groups seven precincts into three
buildings as "NEOGA I & II" — but this one demonstrably does not group. Three
of its buildings serve several precincts and every precinct still gets its own
row: 202 N. Olive St. serves Harter 1, 3, 4 and 5; 435 Chestnut St. serves
Louisville 1 and 2; 4722 Cherrybark Ln. serves Harter 6 and 7. Eight precincts
share an address with a sibling and none is folded, so a second Clay City at
237 S. 2nd St. SE would have its own row the way Louisville 2 does. It has
none. The list also reproduces the county's own oddity of having NO HARTER 2,
which a list of buildings would not.

So three publishers say one Clay City — the returns, Census 2020's single CLAY
CITY I voting district, and the Clerk's polling list — and the board page stops
disagreeing once its two slots are read as what Clerk Britton called them on
2026-08-24: "Clay City Dist A is located within the Village limits of Clay
City", "Dist B is the unincorporated area". Those are BOARD DISTRICTS through
one precinct, which is how build_clay_boundaries.py already drew them. The
NAMES here come from the canvass and not from that list, per the Cumberland
rule; the list settled the count and nothing else.

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
    python3 scripts/build_vtd_precincts.py                 # write all eight
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
    "clay": {
        "fips": "025", "pop2020": 13288, "county": "Clay County",
        "precincts": (
            "BIBLE GROVE", "BLAIR", "CLAY CITY", "HARTER 1", "HARTER 3",
            "HARTER 4", "HARTER 5", "HARTER 6", "HARTER 7", "HOOSIER",
            "LARKINSBURG", "LOUISVILLE 1", "LOUISVILLE 2", "OSKALOOSA",
            "PIXLEY", "SONGER", "STANFORD", "XENIA"),
        # Eleven renames in two shapes, and both are the census's convention
        # rather than a difference about which precincts exist. EIGHT ROMAN
        # ORDINALS: the census writes HARTER III and LOUISVILLE II where the
        # county's certified returns write HARTER 3 and LOUISVILLE 2. THREE
        # VESTIGIAL TRAILING I's on names with no sibling: CLAY CITY I,
        # LARKINSBURG I, PIXLEY I, where no II exists in the census, in either
        # canvass, or on the Clerk's polling list. norm() keeps arabic and
        # roman apart (HARTER1 vs HARTERI), so none of these can collide.
        "aliases": {"CLAY CITY": "CLAY CITY I",
                    "HARTER 1": "HARTER I", "HARTER 3": "HARTER III",
                    "HARTER 4": "HARTER IV", "HARTER 5": "HARTER V",
                    "HARTER 6": "HARTER VI", "HARTER 7": "HARTER VII",
                    "LARKINSBURG": "LARKINSBURG I",
                    "LOUISVILLE 1": "LOUISVILLE I",
                    "LOUISVILLE 2": "LOUISVILLE II",
                    "PIXLEY": "PIXLEY I"},
        "board": ("Clay County's fourteen lettered board districts ship as "
                  "their own layer, so no board district is carried here — and "
                  "one of its precincts could not carry one anyway: CLAY CITY "
                  "is split between districts A and B at the village limits, "
                  "which is a board-layer fact and is drawn there."),
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
