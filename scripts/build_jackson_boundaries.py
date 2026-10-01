#!/usr/bin/env python3
"""
Build data/app/jackson-precincts.json and
data/app/jackson-county-board-districts.json — Jackson County's 56 voting
precincts and its 7 County Board districts (14 members, two per district).

THE FIRST COUNTY IN THE FLEET WHOSE DISTRICTS SPLIT PRECINCTS AND ARE BUILT
ANYWAY. Every canvass-route county so far needed its districts to be unions of
WHOLE precincts, and Jackson is not one: its own certified canvass reports three
precincts twice, under two districts each, with their registration divided
between the two. That is the county stating those precincts straddle a district
line, and it is why this county was recorded as measured-shut on 2026-08-21
alongside Bureau, Cumberland, Douglas, Ford, Knox and Piatt.

WHAT THE RECORD MISSED IS THAT IT NAMED THE ANSWER ITSELF: "the county even
publishes a 'Board District Map (PDF)' — a vector export dated 7/26/2022 whose
text reads cleanly". It is a genuine Esri vector export, and its SEVEN DISTRICTS
ARE SEVEN FILLED PATHS in the content stream — not pixels to be classified, but
polygon objects with exact fill colours that pair one-for-one with the legend's
seven swatches, in legend order, each containing its own district numeral. So
the districts can be read as geometry rather than inferred as a composition,
which is the whole difference between this county and the six beside it.

FOUR STEPS, AND THE THIRD IS WHAT MAKES THE RESULT EXACT RATHER THAN TRACED:

  1. READ the seven filled paths out of the PDF (pymupdf), giving seven polygons
     in PDF space.
  2. GEOREFERENCE them. The map is north-up in EPSG:3436 (Illinois State Plane
     WEST, ftUS) — established by fitting the union of the seven districts to
     TIGER's county boundary across candidate CRSs, where 3436 matched the
     aspect ratio to four decimals (1.0712) and every other candidate did not.
     The fit was then refined against the 53 unambiguous precincts. Residual:
     mean boundary offset 5.3 m against the census county outline, and the map's
     own scale bar independently confirms the scale (19.4 pt/mile fitted against
     19.3 pt/mile drawn).
  3. SNAP TO CENSUS GEOMETRY. Nothing traced is shipped. The 53 precincts the
     canvass assigns unambiguously take their district from the CANVASS and
     their geometry from the census voting districts; the three split precincts
     take their geometry from census BLOCKS, each block assigned to whichever of
     the two districts THE CANVASS NAMES FOR THAT PRECINCT the county's own map
     puts it in. The map never picks a district the canvass did not already name.
  4. VERIFY. See below.

WHY BLOCKS ARE THE RIGHT UNIT: county plans are drawn in redistricting software
over census blocks, and Jackson's is. Of the county's 2,773 blocks, 84% sit
99.9%+ inside a single district under this georeferencing and 98% sit 95%+; the
blocks that straddle hold 414 people countywide, and inside the three split
precincts only FIVE blocks holding SIXTEEN people are less than 95% resolved.
Every one of the 2,773 blocks also nests 99%+ inside exactly one precinct, so
the split-precinct block sets are well defined.

FOUR INDEPENDENT VERIFICATIONS, none of which uses the map to check the map:

  * THE CANVASS, 53/53. Every precinct the canvass assigns to exactly one
     district is placed in that district by the georeferenced map, at 98.3-100%
     of its area. A wrong CRS, scale or offset could not produce that.
  * THE SPLITS, 3/3. The map splits each of the three split precincts between
     exactly the two districts the canvass names for it — never a third.
  * POPULATION BALANCE. The seven districts run 7,371-7,933 against a 7,568
     ideal: worst deviation 4.83%, spread 7.4%. A mis-assigned split precinct
     (each holds 728-2,743 people) would show here immediately.
  * MURPHYSBORO 4 AGAINST ITS OWN REGISTRATION. Its census population divides
     30.2%/69.8% between districts 3 and 5, where the canvass divides its
     REGISTERED VOTERS 29.8%/70.2%. THE SAME CHECK IS DELIBERATELY NOT CLAIMED
     FOR THE OTHER TWO: Carbondale 21 and 24 contain SIU dormitories and student
     apartments — one block holds 700 people in FOUR housing units — and census
     population does not predict voter registration there in either direction.
     Stating that plainly is the point; the check is informative where it works
     and silent where it does not.

THIS IS A RARE OPERATOR STEP (requests + shapely). The composition below is a
CONSTANT, so this build is deterministic and --check is a byte compare; the PDF
is not fetched here. Re-derive it only if Jackson reapportions or re-precincts.

Usage:
    python3 scripts/build_jackson_boundaries.py [--check]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_metro_outline import point_in_rings  # noqa: E402
import vtd_board_districts as V  # noqa: E402
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    make_fail,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PRECINCTS = os.path.join(REPO_ROOT, "il", "data", "app", "jackson-precincts.json")
OUT_DISTRICTS = os.path.join(REPO_ROOT, "il", "data", "app",
                             "jackson-county-board-districts.json")

COUNTY_FIPS = "077"
COUNTY_POP_2020 = 52974
EXPECTED_PRECINCTS = 56
EXPECTED_BLOCKS = 2773
SEATS_PER_DISTRICT = 2          # fourteen members, two per district

BOARD_URL = "https://jacksoncounty-il.gov/158/County-Board"
MAP_URL = "https://jacksoncounty-il.gov/DocumentCenter/View/172/District-Board-Map-PDF"
CANVASS_URL = "https://jacksoncounty-il.gov/DocumentCenter/View/912/2024-Election-Results"

SOURCE_LABEL = ("Census 2020 voting districts and blocks, composed from Jackson "
                "County's certified 5 November 2024 General canvass and, inside "
                "the three precincts that canvass reports under two districts, "
                "from the county's own adopted Board District Map of 26 July 2022")

# THE 53 PRECINCTS THE CANVASS ASSIGNS UNAMBIGUOUSLY, keyed by district. Read
# from the certified 2024 General: each district's contest lists exactly the
# precincts that voted in it. No map is involved in any of these.
WHOLE_PRECINCTS = {
    "1": ("ELK 1", "ELK 3", "LEVAN", "SAND RIDGE", "SOMERSET 1", "SOMERSET 2",
          "SOMERSET 3", "SOMERSET 4", "VERGENNES"),
    "2": ("BRADLEY - AVA", "BRADLEY - CAMPBELL HILL", "DEGOGNIA",
          "FOUNTAIN BLUFF", "GRAND TOWER", "KINKAID", "MURPHYSBORO 12",
          "MURPHYSBORO 6", "MURPHYSBORO 8", "MURPHYSBORO 9", "ORA", "POMONA"),
    "3": ("CARBONDALE 7", "CARBONDALE 8", "MURPHYSBORO 1", "MURPHYSBORO 10",
          "MURPHYSBORO 2", "MURPHYSBORO 3", "MURPHYSBORO 5", "MURPHYSBORO 7"),
    "4": ("CARBONDALE 1", "CARBONDALE 4", "CARBONDALE 5", "CARBONDALE 6",
          "CARBONDALE 9", "DESOTO 1", "DESOTO 2"),
    "5": ("CARBONDALE 10", "CARBONDALE 14", "CARBONDALE 15", "CARBONDALE 16",
          "MAKANDA 1", "MAKANDA 2", "MAKANDA 4"),
    "6": ("CARBONDALE 11", "CARBONDALE 12", "CARBONDALE 13", "CARBONDALE 25",
          "CARBONDALE 26"),
    "7": ("CARBONDALE 18", "CARBONDALE 19", "CARBONDALE 2", "CARBONDALE 20",
          "MAKANDA 3"),
}

# THE THREE THE CANVASS REPORTS TWICE, resolved to whole census blocks. The
# canvass names the two districts; the county's map decides which of the two
# each block falls in. Registration as the canvass divides it:
#   CARBONDALE 21  D6 600 / D7 282      CARBONDALE 24  D5 609 / D6 98
#   MURPHYSBORO 4  D3 166 / D5 391
SPLIT_PRECINCT_BLOCKS = {
    "CARBONDALE 21": {
        "6": ("170770111004010", "170770111004011", "170770112002023",
              "170770112002024", "170770112002027", "170770112002028",
              "170770112002030", "170770112002031", "170770112002032",
              "170770112002033", "170770112002034", "170770112002036",
              "170770114001001", "170770114002005", "170770114002006",
              "170770117022000", "170770117022001", "170770117022002",
              "170770117022007", "170770117022008", "170770117022022",
              "170770117022048", "170770117022049", "170770117022050",
              "170770117022051", "170770117022052", "170770117022058"),
        "7": ("170770112004002", "170770114001000", "170770114001002",
              "170770114001003"),
    },
    "CARBONDALE 24": {
        "5": ("170770110021020", "170770110021036", "170770110021039",
              "170770110021040", "170770110021041", "170770110021042",
              "170770110021043", "170770110021044", "170770110021045",
              "170770110021047", "170770110021048", "170770110021049",
              "170770110021050", "170770116003000", "170770116003001",
              "170770116003002", "170770116003005", "170770116003006",
              "170770116003007", "170770116003019", "170770117011000",
              "170770117011001", "170770117011002", "170770117011005",
              "170770117011006", "170770117021000", "170770117021001",
              "170770117021002", "170770117021003", "170770117021008",
              "170770117021009", "170770117021013", "170770117021014",
              "170770117021015", "170770117021016", "170770117021017",
              "170770117021018", "170770117021019", "170770117021020",
              "170770117021021", "170770117021022"),
        "6": ("170770117021004", "170770117021005", "170770117022023",
              "170770117022024", "170770117022025", "170770117022028",
              "170770117022039", "170770117022041", "170770117022042",
              "170770117022043", "170770117022044", "170770117022045",
              "170770117022046", "170770117022047", "170770117022053",
              "170770117022054", "170770117022057"),
    },
    "MURPHYSBORO 4": {
        "3": ("170770106011005", "170770106011006", "170770106011007",
              "170770106011008"),
        "5": ("170770106011009", "170770106011010", "170770106011011",
              "170770106011012", "170770110021008", "170770110021009",
              "170770110021010", "170770110021011", "170770110021012",
              "170770110021013", "170770110021014"),
    },
}

BALANCE_DEV_MAX = 0.30          # measured 0.0483
MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999
MIN_BLOCK_NESTING = 0.99        # every block inside one precinct by this much

BLOCK_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
             "tigerWMS_Census2020/MapServer/10/query")


fail = make_fail("jackson-boundaries")


def fetch_blocks(shape_fn):
    """Every Census 2020 block in the county. TIGERweb pages this layer and
    returns an EMPTY page unless the query is ordered, which reads as 'the
    county has no blocks' rather than as an error — hence orderByFields."""
    import requests
    out, offset = {}, 0
    while True:
        require_robots_once(BLOCK_URL, V["User-Agent"], headers=V,
                            label="il-build-jackson-boundaries")
        resp = requests.get(BLOCK_URL, headers=V.HEADERS, timeout=V.REQUEST_TIMEOUT,
                            params={"where": "STATE='17' AND COUNTY='%s'" % COUNTY_FIPS,
                                    "outFields": "GEOID,POP100", "returnGeometry": "true",
                                    "outSR": "4326", "f": "geojson",
                                    "orderByFields": "GEOID",
                                    "resultOffset": offset, "resultRecordCount": 1000})
        resp.raise_for_status()
        feats = resp.json().get("features") or []
        for f in feats:
            props = f["properties"]
            geom = shape_fn(f["geometry"])
            out[props["GEOID"]] = {"geom": geom if geom.is_valid else geom.buffer(0),
                                   "pop": int(props.get("POP100") or 0)}
        offset += len(feats)
        if len(feats) < 1000:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files match a fresh build")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping   # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402

    county_precincts = (sorted(n for names in WHOLE_PRECINCTS.values() for n in names)
                        + sorted(SPLIT_PRECINCT_BLOCKS))
    if len(county_precincts) != EXPECTED_PRECINCTS:
        fail("the composition names %d precincts, expected %d"
             % (len(county_precincts), EXPECTED_PRECINCTS))
    if len(set(county_precincts)) != EXPECTED_PRECINCTS:
        fail("a precinct is named twice in the composition")

    vtds = V.fetch_vtds(COUNTY_FIPS, shape, fail)
    if len(vtds) != EXPECTED_PRECINCTS:
        fail("the census voting-district layer carries %d Jackson features, "
             "expected %d" % (len(vtds), EXPECTED_PRECINCTS))
    county_geom, county_pop = V.fetch_county(COUNTY_FIPS, shape, fail)
    if county_pop != COUNTY_POP_2020:
        fail("census county population is %d, expected %d" % (county_pop, COUNTY_POP_2020))
    V.check_fabric(vtds, county_precincts, county_pop, fail)

    blocks = fetch_blocks(shape)
    if len(blocks) != EXPECTED_BLOCKS:
        fail("the census block layer carries %d Jackson blocks, expected %d"
             % (len(blocks), EXPECTED_BLOCKS))
    block_pop = sum(b["pop"] for b in blocks.values())
    if block_pop != county_pop:
        fail("the %d blocks sum to %d people and the county to %d"
             % (len(blocks), block_pop, county_pop))

    # Every block must nest inside exactly one precinct, or the split-precinct
    # block sets below are not well defined.
    home = {}
    for geoid, rec in blocks.items():
        g = rec["geom"]
        if g.is_empty or g.area == 0:
            fail("block %s has no geometry" % geoid)
        best, bestkey = 0.0, None
        for key, v in vtds.items():
            if not v["geom"].intersects(g):
                continue
            frac = v["geom"].intersection(g).area / g.area
            if frac > best:
                best, bestkey = frac, key
        if bestkey is None or best < MIN_BLOCK_NESTING:
            fail("block %s is only %.1f%% inside its best precinct (floor %.0f%%) — "
                 "blocks do not nest in this fabric and the split-precinct block "
                 "sets are not well defined" % (geoid, 100 * best, 100 * MIN_BLOCK_NESTING))
        home[geoid] = bestkey

    # The split precincts' block sets must partition their precinct exactly.
    claimed_blocks = {}
    for pname, per_district in SPLIT_PRECINCT_BLOCKS.items():
        key = V.norm(pname)
        if key not in vtds:
            fail("split precinct %r is not in the census fabric" % pname)
        want = {g for g, h in home.items() if h == key}
        got = []
        for dnum, geoids in per_district.items():
            for geoid in geoids:
                if geoid in claimed_blocks:
                    fail("block %s is claimed by districts %s and %s"
                         % (geoid, claimed_blocks[geoid], dnum))
                claimed_blocks[geoid] = dnum
                got.append(geoid)
        if set(got) != want:
            fail("the block sets for %s do not partition it — extra %s; missing %s"
                 % (pname, sorted(set(got) - want), sorted(want - set(got))))

    # Whole precincts: each named once, none of them a split precinct.
    seen = {}
    for dnum, names in WHOLE_PRECINCTS.items():
        for name in names:
            key = V.norm(name)
            if key not in vtds:
                fail("district %s claims precinct %r, which the census fabric "
                     "does not carry" % (dnum, name))
            if key in seen:
                fail("precinct %r is claimed by districts %s and %s"
                     % (name, seen[key], dnum))
            if name in SPLIT_PRECINCT_BLOCKS:
                fail("precinct %r is listed both whole and split" % name)
            seen[key] = dnum
    unclaimed = sorted(vtds[k]["basename"] for k in set(vtds) - set(seen)
                       - {V.norm(n) for n in SPLIT_PRECINCT_BLOCKS})
    if unclaimed:
        fail("no district claims %s — the composition is incomplete" % ", ".join(unclaimed))

    # ---- dissolve -----------------------------------------------------------
    districts, pops = {}, {}
    for dnum in WHOLE_PRECINCTS:
        parts = [vtds[V.norm(n)]["geom"] for n in WHOLE_PRECINCTS[dnum]]
        pop = sum(vtds[V.norm(n)]["pop"] for n in WHOLE_PRECINCTS[dnum])
        for pname, per_district in SPLIT_PRECINCT_BLOCKS.items():
            for geoid in per_district.get(dnum, ()):
                parts.append(blocks[geoid]["geom"])
                pop += blocks[geoid]["pop"]
        merged = unary_union(parts)
        districts[dnum] = merged if merged.is_valid else merged.buffer(0)
        pops[dnum] = pop

    if sum(pops.values()) != county_pop:
        fail("the districts sum to %d people and the county to %d"
             % (sum(pops.values()), county_pop))
    ideal = county_pop / float(len(districts))
    worst = max(((abs(pops[d] - ideal) / ideal), d) for d in pops)
    if worst[0] > BALANCE_DEV_MAX:
        fail("district %s deviates %.1f%% from the per-district ideal (ceiling "
             "%.0f%%) — that is a mis-assignment, not an apportionment"
             % (worst[1], 100 * worst[0], 100 * BALANCE_DEV_MAX))
    overlap, covered = V.check_tiling(districts, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED, unary_union, fail)

    # ---- output -------------------------------------------------------------
    split_of = {}
    for pname, per_district in SPLIT_PRECINCT_BLOCKS.items():
        split_of[V.norm(pname)] = sorted(per_district, key=int)

    precinct_features = []
    for key in sorted(vtds, key=lambda k: vtds[k]["basename"]):
        rec = vtds[key]
        props = {"name": V.title_case(rec["basename"]), "geoid": rec["geoid"],
                 "pop2020": rec["pop"]}
        if key in split_of:
            props["districts"] = split_of[key]
        else:
            props["district"] = seen[key]
        precinct_features.append({"type": "Feature", "properties": props,
                                  "geometry": V.round_geom(rec["geom"], mapping)})
    precincts_payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "boardUrl": BOARD_URL, "canvassUrl": CANVASS_URL,
            "note": ("Jackson County's 56 precincts are the Census 2020 voting "
                     "districts, which carry the county's own 56 precinct names "
                     "56/56 and sum to its exact 2020 population of 52,974. Most "
                     "features carry their County Board district; THREE carry a "
                     "list of two instead — Carbondale 21, Carbondale 24 and "
                     "Murphysboro 4 are split between districts, which the "
                     "county's own certified canvass states by reporting each of "
                     "them twice with its registration divided. For those three "
                     "the precinct does not determine the district and the card "
                     "says so. No polling place ships: a polling place is a "
                     "roster fact rather than geometry."),
        },
        "features": precinct_features,
    }

    district_features = []
    for dnum in sorted(WHOLE_PRECINCTS, key=int):
        names = [V.title_case(n) for n in sorted(WHOLE_PRECINCTS[dnum])]
        partial = sorted(V.title_case(p) for p, per in SPLIT_PRECINCT_BLOCKS.items()
                         if dnum in per)
        district_features.append({
            "type": "Feature",
            "properties": {"district": dnum, "name": "District %s" % dnum,
                           "precincts": names, "partialPrecincts": partial,
                           "pop2020": pops[dnum], "seats": SEATS_PER_DISTRICT},
            "geometry": V.round_geom(districts[dnum], mapping),
        })
    districts_payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL, "boardUrl": BOARD_URL,
            "canvassUrl": CANVASS_URL, "mapUrl": MAP_URL,
            "canvass": ("Composition from the county's certified 5 November 2024 "
                        "General canvass, which lists for each district's contest "
                        "exactly the precincts that voted in it. Fifty-three of "
                        "the 56 precincts fall in one district and take it from "
                        "the canvass alone. THREE ARE REPORTED TWICE, under two "
                        "districts each with their registration divided — "
                        "Carbondale 21 (D6 600 / D7 282), Carbondale 24 (D5 609 / "
                        "D6 98) and Murphysboro 4 (D3 166 / D5 391) — so those "
                        "three are resolved to whole census blocks using the "
                        "county's own adopted Board District Map of 26 July 2022, "
                        "and the map is only ever allowed to choose between the "
                        "two districts the canvass already names."),
            "note": ("Seven districts electing TWO members each (14 seats). The "
                     "boundary is census geometry throughout: voting districts "
                     "for the 53 whole precincts, blocks inside the three split "
                     "ones. The map was georeferenced to EPSG:3436 and checked "
                     "against the canvass — all 53 unambiguous precincts land in "
                     "the district the canvass names, and all three split "
                     "precincts split between exactly the two it names. "
                     "Populations run 7,371-7,933 against a 7,568 ideal (worst "
                     "4.8%)."),
        },
        "features": district_features,
    }

    prec_body = V.dumps(precincts_payload)
    dist_body = V.dumps(districts_payload)
    print("jackson-boundaries: %d precincts and %d districts of %d seats "
          "(53 whole precincts + %d blocks across 3 split precincts)"
          % (len(precinct_features), len(district_features), SEATS_PER_DISTRICT,
             len(claimed_blocks)))
    print("  populations: %s (total %d = census POP100; worst deviation %.2f%% in "
          "district %s)"
          % (", ".join("D%s=%d" % (d, pops[d]) for d in sorted(pops, key=int)),
             county_pop, 100 * worst[0], worst[1]))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered"
          % (overlap, 100 * covered))
    V.write_or_check([(OUT_PRECINCTS, prec_body), (OUT_DISTRICTS, dist_body)],
                     args.check, REPO_ROOT, fail, "jackson")


if __name__ == "__main__":
    main()
