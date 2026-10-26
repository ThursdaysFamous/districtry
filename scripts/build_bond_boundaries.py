#!/usr/bin/env python3
"""
Build il/data/app/bond-county-board-districts.json — Bond County's five County
Board districts, one member each, from the county's own apportionment plan.

THE SOURCE IS THE COUNTY'S RESOLUTION, SENT BY ITS CLERK. Bond publishes no
district map and no precinct map, and its certified canvasses show four of its
precincts each voting in two board districts, so no union of whole precincts can
draw it (the `bond-county-board-districts` gap record measured both). Asked three
times, County Clerk Brooke Weathers replied on 2026-10-26 with Resolution
06-27-11-01, "A Resolution Adopting County Board Apportionment Plan", approved
27 June 2011, archived as
`il/data/source/raw/Bond County Board Apportionment Plan 2011.pdf`. It is a scan
with no text layer; the composition below was read from its page images.

THE PLAN IS WRITTEN IN CENSUS 2010 UNITS, SO THAT IS WHAT THIS BUILDS FROM.
Each district is a list of whole 2010 voting districts plus named 2010 census
blocks, every one with its population, which is what makes the plan checkable:
TIGERweb's Census 2010 voting districts (layer 72) and blocks (layer 18) carry
those same populations, and this refuses to write unless every whole precinct's
population, every listed block's population and every district total equals the
figure the county printed. Nothing is traced and nothing is inferred; a block is
in a district because the resolution names it there or names the precinct that
holds it.

THE PRISON. The plan leaves out the 1,536 people of the Federal Correctional
Institution in Greenville, as Illinois allows. The typed resolution names a
precinct whose number is overwritten by hand to 5 and gives its remainder as
866, which is Central 7's own figure; the census gives Central 5 2,420 people
and the plan lists Central 5 at 884, and 2,420 less 1,536 is 884. So the
exclusion is applied to Central 5, which is the only reading under which the
plan's own district totals add up.

IS IT STILL THE PLAN IN FORCE? The resolution says it governs County Board
elections "to be held in 2012 through 2020". Two things say it is still the one
in use. The county's certified 2022 General canvass, its 2024 General canvass and
its 2026 General Primary feed show exactly four precincts voting in two board
districts, between exactly these pairs: Burgess 2 (1 and 3), Central 6 (4 and 5),
Old Ripley (3 and 4) and Shoal Creek 2 (2 and 3) — the four this plan splits,
between the same pairs — and the three small portions are the three slivers
measured there. And the precincts the county has consolidated since 2020
(LaGrange 1 and 2, Tamalco 1 and 2, Shoal Creek 3 and 4, Central 5) each merge
precincts this plan puts in one district. Whether the board re-adopted the plan
after the 2020 census was asked on 2026-10-26; until it is answered, the file's
own note says the lines are the 2011 plan's.

    python3 scripts/build_bond_boundaries.py           # write
    python3 scripts/build_bond_boundaries.py --check   # rebuild and compare

Operator step: needs requests and shapely, and reaches TIGERweb.
"""

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_metro_outline import point_in_rings  # noqa: E402
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail, require_robots_once  # noqa: E402

COUNTY_FIPS = "005"
COUNTY_POP_2010 = 17768
EXPECTED_VTDS = 25
SEATS_PER_DISTRICT = 1

TIGER_2010 = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
              "tigerWMS_Census2010/MapServer")
VTD_2010_URL = TIGER_2010 + "/72/query"
BLOCK_2010_URL = TIGER_2010 + "/18/query"

BOARD_URL = "https://bondcountyil.gov/bond-county-board/"
OUT = os.path.join(REPO_ROOT, "il", "data", "app", "bond-county-board-districts.json")

SOURCE_LABEL = ("Census 2010 voting districts and blocks, composed per Bond County "
                "Board Resolution 06-27-11-01 (the county's apportionment plan, "
                "approved 27 June 2011), sent by County Clerk Brooke Weathers on "
                "26 October 2026")

# The prison population the plan leaves out, and the precinct that holds it.
PRISON_PRECINCT = "CENTRAL 5"
PRISON_EXCLUDED = 1536

# WHOLE PRECINCTS per district, with the population the plan prints for each.
# A precinct split by the plan appears under the district that keeps the rest
# of it, and its printed figure is that remainder.
WHOLE = {
    "1": {"BURGESS 1": 966, "BURGESS 2": 634, "MILLS": 552, "TAMALCO 1": 278,
          "TAMALCO 2": 288, "PLEASANT MOUND 2": 529},
    "2": {"PLEASANT MOUND 1": 489, "MULBERRY GROVE 1": 461, "MULBERRY GROVE 2": 900,
          "LAGRANGE 1": 408, "LAGRANGE 2": 761},
    "3": {"SHOAL CREEK 1": 324, "SHOAL CREEK 2": 48, "SHOAL CREEK 3": 396,
          "SHOAL CREEK 4": 788, "OLD RIPLEY": 851, "BURGESS 3": 801},
    "4": {"CENTRAL 3": 522, "CENTRAL 4": 694, "CENTRAL 5": 884, "CENTRAL 6": 264,
          "CENTRAL 7": 866},
    "5": {"CENTRAL 1": 1057, "CENTRAL 1A": 889, "CENTRAL 2": 877},
}
# The plan prints Mulberry Grove 1 at 461 and Mulberry Grove 2 at 900; the
# census has them the other way round. Both are wholly in District 2, so the
# swap moves nobody, and it is checked as a swap rather than forgiven.
SWAPPED_FIGURES = {"MULBERRY GROVE 1", "MULBERRY GROVE 2"}

# Five blocks the plan lists under one precinct lie, by area, in another 2010
# voting district (measured 2026-10-26; each sits 100% inside the precinct
# named here). The plan's own words put each in the district its list names,
# and that is where they go. The county's canvasses back that reading for the
# Central 3 blocks: Central 3 is never split between districts there, while
# Central 6 is, so the current precinct lines put these blocks in Central 6.
# The plan's per-precinct figures were worked out by subtraction ("OR (867-16)"),
# so each such block is counted once too few in its listed precinct's district
# and once too many in the district of the precinct it actually lies in; the
# population check below applies exactly that correction and no other. A sixth
# block in this state, or one of these moving, stops the build.
OUTSIDE_LISTED_PRECINCT = {
    "170059514001015": "SHOAL CREEK 3",   # 0 people, listed under Shoal Creek 2
    "170059513002005": "CENTRAL 1A",      # 8 people, listed under Central 6
    "170059513002043": "CENTRAL 3",       # 10 people, listed under Central 6
    "170059513002044": "CENTRAL 3",       # 22 people, listed under Central 6
    "170059513002045": "CENTRAL 3",       # 48 people, listed under Central 6
}

# Three of those blocks are not where the plan's reading and the county's
# elections agree. They touch Central 3 and Central 4 and nothing of Central 6,
# so the plan's words make them a detached piece of District 5 inside
# District 4, while the canvasses count Central 3 wholly in District 4. Either
# the plan mistyped them or the precinct lines then differed from the census's;
# nothing published here says which. So the map draws them as an area shared
# between Districts 4 and 5 and says why, the way the Jasper, Jersey and
# Lawrence maps draw an area they cannot place.
SHARED_BLOCKS = {"170059513002043", "170059513002044", "170059513002045"}
SHARED_KEY = "4|5"
SHARED_AREA = "Three census blocks in Greenville"
SHARED_NOTE = ("The county's 2011 plan lists these blocks with the Central 6 "
               "precinct and puts them in District 5, but the census places them "
               "in Central 3, and the county's election results count Central 3 "
               "wholly in District 4. This map cannot yet say which is right.")

# BLOCKS the plan moves out of a precinct into another district, with the
# population it prints for each block. GEOID = state 17, county 005, the
# six-digit tract (9515 is 951500) and the four-digit block.
MOVED = {
    "BURGESS 2": ("3", {
        "170059515002059": 13, "170059515002060": 0, "170059515002096": 3,
        "170059515002097": 17, "170059515002109": 0, "170059515002115": 5,
        "170059515002129": 0}),
    "SHOAL CREEK 2": ("2", {
        "170059514001000": 8, "170059514001001": 14, "170059514001002": 4,
        "170059514001003": 49, "170059514001004": 6, "170059514001005": 0,
        "170059514001006": 8, "170059514001007": 2, "170059514001008": 13,
        "170059514001009": 7, "170059514001010": 6, "170059514001011": 28,
        "170059514001012": 4, "170059514001013": 1, "170059514001014": 2,
        "170059514001015": 0, "170059514001030": 2, "170059514001031": 2,
        "170059514001032": 24, "170059514001033": 5, "170059514001034": 3,
        "170059514001035": 4, "170059514001036": 29, "170059514001038": 0,
        "170059514001168": 6}),
    "OLD RIPLEY": ("4", {
        "170059514002037": 0, "170059514002074": 6, "170059514002075": 0,
        "170059514002076": 0, "170059514002077": 0, "170059514002078": 0,
        "170059515002000": 2, "170059515002001": 2, "170059515003144": 2,
        "170059515003145": 0, "170059515003159": 4}),
    "CENTRAL 6": ("5", {
        "170059513001069": 101, "170059513001070": 0, "170059513001071": 25,
        "170059513001072": 2, "170059513001073": 13, "170059513002005": 8,
        "170059513002043": 10, "170059513002044": 22, "170059513002045": 48,
        "170059513004001": 13, "170059513004002": 25, "170059513004003": 0,
        "170059513004004": 0, "170059513004005": 7, "170059513004006": 4,
        "170059513004007": 0, "170059513004008": 0, "170059513004009": 7,
        "170059513004010": 0, "170059513004011": 0, "170059513004012": 0,
        "170059513004013": 0, "170059513004014": 0, "170059513004015": 5,
        "170059513004016": 11, "170059513004017": 22, "170059513004018": 14,
        "170059513004019": 3, "170059513004020": 6, "170059513004021": 12,
        "170059513004022": 4, "170059513004023": 8, "170059513004024": 14,
        "170059513004028": 2, "170059513004029": 11, "170059513004030": 13,
        "170059513004031": 14}),
}

# The district totals the plan prints, and the four splits the county's own
# certified canvasses show (2022 and 2024 General, 2026 General Primary), as the
# `bond-county-board-districts` gap record measured them on 2026-08-20.
PLAN_TOTALS = {"1": 3247, "2": 3246, "3": 3246, "4": 3246, "5": 3247}
CANVASS_SPLITS = {"BURGESS 2": {"1", "3"}, "CENTRAL 6": {"4", "5"},
                  "OLD RIPLEY": {"3", "4"}, "SHOAL CREEK 2": {"2", "3"}}

MIN_BLOCK_NESTING = 0.99
MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999

fail = make_fail("bond-boundaries")


def get(url, params):
    import requests
    require_robots_once(url, V.HEADERS["User-Agent"], headers=V.HEADERS,
                        label="il-build-bond-boundaries")
    resp = requests.get(url, headers=V.HEADERS, timeout=V.REQUEST_TIMEOUT, params=params)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        fail("%s answered an error: %s" % (url, data["error"]))
    return data


def fetch_vtds(shape):
    data = get(VTD_2010_URL, {"where": "STATE='17' AND COUNTY='%s'" % COUNTY_FIPS,
                              "outFields": "GEOID,BASENAME,POP100",
                              "returnGeometry": "true", "outSR": "4326", "f": "geojson"})
    out = {}
    for f in data.get("features") or []:
        p = f["properties"]
        name = " ".join((p.get("BASENAME") or "").upper().split())
        if name in out:
            fail("the 2010 voting-district layer carries %r twice" % name)
        g = shape(f["geometry"])
        out[name] = {"geom": g if g.is_valid else g.buffer(0),
                     "pop": int(p.get("POP100") or 0)}
    return out


def fetch_blocks(shape):
    """Every 2010 block in the county. The layer pages, and returns an empty page
    unless the query is ordered (the Jackson builder's finding), hence
    orderByFields."""
    out, offset = {}, 0
    while True:
        data = get(BLOCK_2010_URL, {"where": "STATE='17' AND COUNTY='%s'" % COUNTY_FIPS,
                                    "outFields": "GEOID,POP100", "returnGeometry": "true",
                                    "outSR": "4326", "f": "geojson",
                                    "orderByFields": "GEOID", "resultOffset": offset,
                                    "resultRecordCount": 1000})
        feats = data.get("features") or []
        for f in feats:
            p = f["properties"]
            g = shape(f["geometry"])
            out[p["GEOID"]] = {"geom": g if g.is_valid else g.buffer(0),
                               "pop": int(p.get("POP100") or 0)}
        offset += len(feats)
        if len(feats) < 1000:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="rebuild and fail if the shipped file differs")
    args = ap.parse_args()

    from shapely.geometry import shape, mapping   # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402

    # ---- the plan agrees with itself ----------------------------------------
    named = [n for d in WHOLE.values() for n in d]
    if len(named) != EXPECTED_VTDS or len(set(named)) != EXPECTED_VTDS:
        fail("the plan names %d precincts (%d distinct), expected %d"
             % (len(named), len(set(named)), EXPECTED_VTDS))
    home_district = {n: d for d, names in WHOLE.items() for n in names}
    splits = {p: {home_district[p], to} for p, (to, _) in MOVED.items()}
    if splits != CANVASS_SPLITS:
        fail("the plan splits %s and the canvasses split %s" % (splits, CANVASS_SPLITS))
    for dnum, total in PLAN_TOTALS.items():
        got = sum(WHOLE[dnum].values()) + sum(
            sum(blocks.values()) for p, (to, blocks) in MOVED.items() if to == dnum)
        if got != total:
            fail("district %s's printed figures sum to %d, and the plan prints %d"
                 % (dnum, got, total))

    # ---- the census agrees with the plan ------------------------------------
    vtds = fetch_vtds(shape)
    if set(vtds) != set(named):
        fail("the 2010 voting districts are %s, the plan names %s"
             % (sorted(set(vtds) - set(named)), sorted(set(named) - set(vtds))))
    if sum(v["pop"] for v in vtds.values()) != COUNTY_POP_2010:
        fail("the 2010 voting districts sum to %d, not the county's %d"
             % (sum(v["pop"] for v in vtds.values()), COUNTY_POP_2010))
    blocks = fetch_blocks(shape)
    if sum(b["pop"] for b in blocks.values()) != COUNTY_POP_2010:
        fail("the 2010 blocks sum to %d, not the county's %d"
             % (sum(b["pop"] for b in blocks.values()), COUNTY_POP_2010))

    for name, rec in vtds.items():
        moved = sum(MOVED[name][1].values()) if name in MOVED else 0
        expect = WHOLE[home_district[name]][name] + moved
        if name == PRISON_PRECINCT:
            expect += PRISON_EXCLUDED
        if name in SWAPPED_FIGURES:
            other = (SWAPPED_FIGURES - {name}).pop()
            expect = WHOLE[home_district[other]][other]
        if rec["pop"] != expect:
            fail("precinct %s has %d people in the 2010 census; the plan's figures "
                 "give %d" % (name, rec["pop"], expect))

    # Each block's home precinct, by area.
    home = {}
    for geoid, rec in blocks.items():
        g = rec["geom"]
        best, bestname = 0.0, None
        for name, v in vtds.items():
            if v["geom"].intersects(g):
                frac = v["geom"].intersection(g).area / g.area
                if frac > best:
                    best, bestname = frac, name
        if bestname is None or best < MIN_BLOCK_NESTING:
            fail("block %s is only %.1f%% inside its best precinct" % (geoid, 100 * best))
        home[geoid] = bestname

    district_of = {g: home_district[h] for g, h in home.items()}
    for pname, (to, listed) in MOVED.items():
        for geoid, pop in listed.items():
            if geoid not in blocks:
                fail("the plan names block %s, which the 2010 census does not carry" % geoid)
            if home[geoid] != pname and OUTSIDE_LISTED_PRECINCT.get(geoid) != home[geoid]:
                fail("the plan moves block %s out of %s, but it lies in %s"
                     % (geoid, pname, home[geoid]))
            if blocks[geoid]["pop"] != pop:
                fail("block %s has %d people in the 2010 census; the plan prints %d"
                     % (geoid, blocks[geoid]["pop"], pop))
            district_of[geoid] = to

    # ---- dissolve ------------------------------------------------------------
    districts, pops = {}, {}
    for dnum in PLAN_TOTALS:
        mine = [g for g, d in district_of.items() if d == dnum]
        merged = unary_union([blocks[g]["geom"] for g in mine])
        districts[dnum] = merged if merged.is_valid else merged.buffer(0)
        pops[dnum] = sum(blocks[g]["pop"] for g in mine)
    listed_from = {g: p for p, (to, listed) in MOVED.items() for g in listed}
    expect = dict(PLAN_TOTALS)
    for geoid, where in OUTSIDE_LISTED_PRECINCT.items():
        if geoid not in listed_from or home.get(geoid) != where:
            fail("block %s is recorded as listed by the plan and lying in %s; it is "
                 "%s and lies in %s" % (geoid, where,
                                        "listed" if geoid in listed_from else "not listed",
                                        home.get(geoid)))
        pop = blocks[geoid]["pop"]
        expect[home_district[listed_from[geoid]]] += pop
        expect[home_district[where]] -= pop
    pops[home_district[PRISON_PRECINCT]] -= PRISON_EXCLUDED
    if pops != expect:
        fail("the districts hold %s people; the plan's figures, corrected for the "
             "blocks listed outside their precinct, give %s" % (pops, expect))

    # Carve out the blocks this map cannot place.
    for geoid in SHARED_BLOCKS:
        if geoid not in OUTSIDE_LISTED_PRECINCT:
            fail("block %s is drawn as shared but is not recorded as listed outside "
                 "its precinct" % geoid)
        district_of[geoid] = SHARED_KEY
    for key in sorted({SHARED_KEY} | {d for d in SHARED_KEY.split("|")}):
        mine = [g for g, d in district_of.items() if d == key]
        merged = unary_union([blocks[g]["geom"] for g in mine])
        districts[key] = merged if merged.is_valid else merged.buffer(0)
        pops[key] = sum(blocks[g]["pop"] for g in mine)
        if key == home_district[PRISON_PRECINCT]:
            pops[key] -= PRISON_EXCLUDED

    for dnum, g in districts.items():
        parts = len(getattr(g, "geoms", [g]))
        if parts != 1:
            fail("district %s is %d separate parts" % (dnum, parts))
    county_geom, _ = V.fetch_county(COUNTY_FIPS, shape, fail)
    overlap, covered = V.check_tiling(districts, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED, unary_union, fail)

    # ---- output ----------------------------------------------------------------
    features = []
    for dnum in sorted(PLAN_TOTALS, key=int):
        features.append({
            "type": "Feature",
            "properties": {"district": dnum, "name": "District %s" % dnum,
                           "pop2010": pops[dnum], "seats": SEATS_PER_DISTRICT},
            "geometry": V.round_geom(districts[dnum], mapping),
        })
    features.append({
        "type": "Feature",
        "properties": {"district": None, "between": SHARED_KEY.split("|"),
                       "area": SHARED_AREA,
                       "name": " or ".join("District %s" % d for d in SHARED_KEY.split("|")),
                       "note": SHARED_NOTE, "pop2010": pops[SHARED_KEY]},
        "geometry": V.round_geom(districts[SHARED_KEY], mapping),
    })
    # The app's own even-odd test, on the rounded output, at a point inside every
    # block that holds people.
    for geoid, rec in blocks.items():
        if not rec["pop"]:
            continue
        probe = rec["geom"].representative_point()
        hits = ["|".join(f["properties"].get("between") or [f["properties"]["district"]])
                for f in features
                if point_in_rings(probe.y, probe.x, V.rings_of(f["geometry"]))]
        if hits != [district_of[geoid]]:
            fail("block %s lands in district %s after rounding, expected %s"
                 % (geoid, hits or "none", district_of[geoid]))

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL,
            "boardUrl": BOARD_URL,
            "note": ("Five single-member districts drawn from the county's 2011 "
                     "apportionment plan, which lists each district as whole 2010 "
                     "precincts plus named census blocks. The plan was adopted for the "
                     "2012 to 2020 elections. The county's 2022 and 2024 election "
                     "results divide the same four precincts between the same "
                     "districts, which is why these lines are taken as the ones in "
                     "use. Populations exclude the 1,536 people of the federal "
                     "prison in Greenville, as the plan does. Shared: %s (District 4 "
                     "or District 5)." % SHARED_AREA),
        },
        "features": features,
    }
    body = V.dumps(payload)
    print("bond-boundaries: 5 districts and 1 shared area from %d blocks; populations %s; overlap "
          "%.1f m2; covers %.4f%% of the county"
          % (len(blocks), ", ".join("%s %d" % (d, pops[d]) for d in sorted(pops)),
             overlap, 100 * covered))
    V.write_or_check([(OUT, body)], args.check, REPO_ROOT, fail, "bond-boundaries")


if __name__ == "__main__":
    main()
