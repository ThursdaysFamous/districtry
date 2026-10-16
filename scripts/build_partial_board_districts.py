#!/usr/bin/env python3
"""
Build il/data/app/<county>-county-board-districts.json for the four Illinois
counties whose board districts are PROVEN EVERYWHERE BUT ONE AREA — Fayette,
Cumberland, Jersey and Lawrence (Adam's choice, 2026-10-16: "Draw the proven
parts").

WHAT "PROVEN" MEANS HERE. Each county's own publication names, for every
district, the precincts or townships that make it up. Where a precinct or
township belongs WHOLLY to one district, its Census 2020 geometry is that
district's ground, exactly as on the canvass route the rest of Illinois uses
(scripts/vtd_board_districts.py). Where the county says a precinct or township
is SHARED between districts and does not publish where the line runs, this
build draws that area as its own feature carrying the districts it lies
between, and NO district number. The card then says a point there is in one of
those districts and that the county has not published the line, which is true;
picking one would be a guess, and officeholder data is never guessed.

  Fayette (7 districts, 2 members each). The county's certified 2022 General
  canvass lists each district's precincts; three appear under more than one
  district — Avena (3 and 5), Bear Grove (2 and 6) and Vandalia 3 (5, 6 and
  7). Its other 25 precincts are the Census 2020 voting districts name for name.

  Cumberland (3 districts — Western, Central, Eastern — 2 members each). The
  county's 2025 Yearbook lists Western as Spring Point and part of Neoga,
  Central as Cottonwood, Woodbury, Sumpter and part of Neoga, and Eastern as
  Union, Greenup and Crooked Creek. Its certified returns count 3, 6 and 5
  precincts per district against 12 precincts, which is the two Neoga
  precincts counted twice. The County Clerk's map photo (e-mail of 2026-10-01)
  shows a line through them; a road read off a phone photo is not published,
  so Neoga 1 and Neoga 2 stay shared.

  Jersey (4 districts, 3 members each). The County Clerk's precinct-by-district
  table (e-mail of 2026-10-01) puts Elsah, Otter Creek, Quarry, Richwood and
  Rosedale in District 3, Mississippi and Piasa in District 4, Fidelity and
  Ruyle in District 1 and English in District 2. Jersey Township's precincts
  are split between Districts 1 and 2, and the county now runs Jersey 1 to 8
  where the census carries Jersey 1 to 10, so no census precinct can be placed
  inside that township: the whole township stays shared. (The census's Quarry
  1 and 2 are the county's one Quarry precinct; both lie in Quarry Township,
  which the township witness below proves.)

  Lawrence (7 districts, 1 member each). The County Clerk's "Precinct
  Description of County Board Districts — 2024" (e-mail of 2026-10-01) gives
  District 1 as all of Petty 25, Bond 3 and Russell 27; District 2 Christy 8
  and Lukin 24; District 3 Bridgeport 4 and 6; District 4 Allison 1, Denison 10
  and Denison 12. Districts 5, 6 and 7 divide Lawrence Township (the
  Lawrenceville precincts 13 to 22) along streets and railroads; the
  description names them, but this build does not draw street lines, so the
  township stays shared between 5, 6 and 7. The county consolidated its
  precincts after the census (the census's Christy 9 is now part of Christy 8),
  so the rural districts are drawn as whole TOWNSHIPS, and the township witness
  proves each census precinct lies in the township its name says.

THE TOWNSHIP WITNESS (Jersey and Lawrence). Where a county's precincts were
consolidated after 2020, the census names no longer match the county's one for
one, so the Jasper test cannot run as a name comparison. What still holds is
that a precinct named for a township lies in that township. Each census voting
district is checked against the Census 2020 county subdivision of the same name
and must lie inside it (MIN_IN_TOWNSHIP of its area), and each district's
dissolve must equal the union of its townships. A consolidation that crossed a
township line fails here rather than shipping a precinct into the wrong
district.

THIS IS A RARE OPERATOR STEP (requests + shapely). Re-run when a county
reapportions, re-precincts, or publishes the line through its shared area.
Output is deterministic, so --check is a byte compare.

Usage:
    python3 scripts/build_partial_board_districts.py [--county SLUG] [--check]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_metro_outline import point_in_rings  # noqa: E402
import vtd_board_districts as V  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
COUNTYSUB_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                 "tigerWMS_Census2020/MapServer/20/query")

MAX_OVERLAP_M2 = 1.0
MIN_COVERED = 0.9999
MIN_IN_TOWNSHIP = 0.995      # share of a voting district's area inside its township
MAX_TOWNSHIP_MISMATCH = 0.002  # symmetric difference / township area

fail = make_fail("partial-board-districts")


def shared(*districts):
    """The composition key for an area the county divides between districts."""
    return "|".join(districts)


COUNTIES = {
    "fayette": {
        "name": "Fayette", "fips": "051", "pop": 21488, "vtds": 28, "seats": 2,
        "label": lambda d: "District %s" % d,
        "order": ["1", "2", "3", "4", "5", "6", "7"],
        "composition": {
            "1": ("BOWLING GREEN 1", "CARSON 1", "LOUDON 1", "RAMSEY 1"),
            "2": ("HURRICANE 1", "SO HURRICANE 1", "KASKASKIA 1", "POPE 1",
                  "SEMINARY 1", "SHAFTER 1", "WILBERTON 1"),
            "3": ("LA CLEDE 1", "LONE GROVE 1", "WHEATLAND 1"),
            "4": ("SHARON 1",),
            "5": ("OTEGO 1", "SEFTON 1", "VANDALIA 1"),
            "6": ("VANDALIA 6", "VANDALIA 7", "VANDALIA 8"),
            "7": ("VANDALIA 2", "VANDALIA 4", "VANDALIA 5", "VANDALIA 9"),
            shared("3", "5"): ("AVENA 1",),
            shared("2", "6"): ("BEAR GROVE 1",),
            shared("5", "6", "7"): ("VANDALIA 3",),
        },
        "areas": {
            shared("3", "5"): "Avena precinct",
            shared("2", "6"): "Bear Grove precinct",
            shared("5", "6", "7"): "Vandalia 3 precinct",
        },
        "townships": None,
        "source": ("Census 2020 voting districts grouped by each district's "
                   "precincts as Fayette County's certified 2022 General "
                   "Election canvass lists them"),
        "planUrl": ("https://www.fayettecountyillinois.gov/wp-content/uploads/"
                    "2024/02/2a_Fayette-General-Election-11-08-2022-Canvass.pdf"),
        "boardUrl": "https://www.fayettecountyillinois.gov/county-board/",
        "unplaced": ("The county's canvass lists this precinct under more than "
                     "one district, so a district line runs through it, and the "
                     "county has not published where."),
    },
    "cumberland": {
        "name": "Cumberland", "fips": "035", "pop": 10450, "vtds": 12, "seats": 2,
        "label": lambda d: "%s District" % d,
        "order": ["Western", "Central", "Eastern"],
        "composition": {
            "Western": ("SPRING POINT",),
            "Central": ("COTTONWOOD", "WOODBURY", "SUMPTER 1", "SUMPTER 2"),
            "Eastern": ("UNION", "GREENUP 1", "GREENUP 2", "GREENUP 3",
                        "CROOKED CREEK"),
            shared("Western", "Central"): ("NEOGA 1", "NEOGA 2"),
        },
        "areas": {shared("Western", "Central"): "Neoga Township"},
        "townships": None,
        "source": ("Census 2020 voting districts grouped by each district's "
                   "precincts as Cumberland County's 2025 Yearbook lists them"),
        "planUrl": ("https://cumberlandcoil.gov/pdf/"
                    "2025%20Cumberland%20County%20Yearbook.pdf"),
        "boardUrl": "https://cumberlandcoil.gov/",
        "unplaced": ("The county's Yearbook puts part of Neoga in the Western "
                     "District and part in the Central District, and the "
                     "county has not published where the line runs."),
    },
    "jersey": {
        "name": "Jersey", "fips": "083", "pop": 21512, "vtds": 25, "seats": 3,
        "label": lambda d: "District %s" % d,
        "order": ["1", "2", "3", "4"],
        "composition": {
            "1": ("FIDELITY", "RUYLE"),
            "2": ("ENGLISH",),
            "3": ("ELSAH 1", "ELSAH 2", "OTTER CREEK", "QUARRY 1", "QUARRY 2",
                  "RICHWOOD", "ROSEDALE"),
            "4": ("MISSISSIPPI 1", "MISSISSIPPI 2", "PIASA 1", "PIASA 2", "PIASA 3"),
            shared("1", "2"): tuple("JERSEY %d" % n for n in range(1, 11)),
        },
        "areas": {shared("1", "2"): "Jersey Township"},
        "townships": {
            "1": ("Fidelity", "Ruyle"), "2": ("English",),
            "3": ("Elsah", "Otter Creek", "Quarry", "Richwood", "Rosedale"),
            "4": ("Mississippi", "Piasa"),
            shared("1", "2"): ("Jersey",),
        },
        "source": ("Census 2020 voting districts grouped by township, per the "
                   "precinct-by-district table Jersey County's Clerk sent on "
                   "2026-10-01"),
        "planUrl": "https://jerseycountyclerk-il.gov/wp-content/2022-elections/22GILJER/EL30.HTM",
        "boardUrl": "https://jerseycounty-il.gov/county-board/",
        "unplaced": ("The county divides Jersey Township's precincts between "
                     "Districts 1 and 2, one of them (Jersey 7) split between "
                     "both, and its precincts changed after the 2020 census, so "
                     "this map cannot yet say which side a point is on."),
    },
    "lawrence": {
        "name": "Lawrence", "fips": "101", "pop": 15280, "vtds": 22, "seats": 1,
        "label": lambda d: "District %s" % d,
        "order": ["1", "2", "3", "4", "5", "6", "7"],
        "composition": {
            "1": ("PETTY 25", "BOND 3", "RUSSELL 27"),
            "2": ("CHRISTY 8", "CHRISTY 9", "LUKIN 24"),
            "3": ("BRIDGEPORT 4", "BRIDGEPORT 6"),
            "4": ("ALLISON 1", "DENISON 10", "DENISON 12"),
            shared("5", "6", "7"): tuple("LAWRENCE %d" % n for n in range(13, 24)),
        },
        "areas": {shared("5", "6", "7"): "Lawrence Township"},
        "townships": {
            "1": ("Petty", "Bond", "Russell"), "2": ("Christy", "Lukin"),
            "3": ("Bridgeport",), "4": ("Allison", "Denison"),
            shared("5", "6", "7"): ("Lawrence",),
        },
        "source": ("Census 2020 voting districts grouped by township, per the "
                   "2024 precinct description of the county board districts "
                   "Lawrence County's Clerk sent on 2026-10-01"),
        "planUrl": None,
        "boardUrl": "https://lawrencecounty.illinois.gov/boards/county-board",
        "unplaced": ("The county's 2024 description divides Lawrence Township "
                     "between Districts 5, 6 and 7 along streets and railroads "
                     "in and around Lawrenceville; this map does not draw those "
                     "lines yet."),
    },
}


def fetch_townships(fips, shape_fn):
    data = V.get_json(COUNTYSUB_URL, {
        "where": "STATE='17' AND COUNTY='%s'" % fips,
        "outFields": "BASENAME,POP100", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson"}, fail)
    out = {}
    for feature in data.get("features") or []:
        base = (feature.get("properties") or {}).get("BASENAME") or ""
        geom = shape_fn(feature["geometry"])
        out[V.norm(base)] = geom if geom.is_valid else geom.buffer(0)
    if not out:
        fail("the census county-subdivision layer returned nothing for county %s" % fips)
    return out


def township_witness(cfg, vtds, districts, shape_fn, unary_union, area_fn):
    """Every census precinct inside the township its name says, and every
    district's dissolve equal to the union of its townships."""
    towns = fetch_townships(cfg["fips"], shape_fn)
    for key, names in cfg["townships"].items():
        geoms = []
        for name in names:
            tk = V.norm(name)
            if tk not in towns:
                fail("%s: no census township named %r" % (cfg["name"], name))
            geoms.append(towns[tk])
        town_union = unary_union(geoms)
        for vname in cfg["composition"][key]:
            g = vtds[V.norm(vname)]["geom"]
            share = area_fn(g.intersection(town_union)) / area_fn(g)
            if share < MIN_IN_TOWNSHIP:
                fail("%s: census precinct %s lies only %.2f%% inside %s — a "
                     "consolidated precinct may cross a township line"
                     % (cfg["name"], vname, 100 * share, " + ".join(names)))
        mismatch = area_fn(districts[key].symmetric_difference(town_union)) / area_fn(town_union)
        if mismatch > MAX_TOWNSHIP_MISMATCH:
            fail("%s: %s dissolves to ground that differs from %s by %.3f%%"
                 % (cfg["name"], key, " + ".join(names), 100 * mismatch))
    return len(cfg["townships"])


def build(slug, check):
    from shapely.geometry import shape, mapping     # noqa: E402  (heavy, function-local)
    from shapely.ops import unary_union, transform  # noqa: E402
    import math

    cfg = COUNTIES[slug]
    comp = cfg["composition"]
    if set(cfg["areas"]) != {k for k in comp if "|" in k}:
        fail("%s: every shared composition key needs an area name" % slug)
    named = {d for k in comp for d in k.split("|")}
    if named != set(cfg["order"]) or not {k for k in comp if "|" not in k} <= set(cfg["order"]):
        fail("%s: the composition does not name exactly the county's districts"
             % slug)
    for key in comp:
        for d in key.split("|"):
            if d not in cfg["order"]:
                fail("%s: %r names a district the county does not have" % (slug, key))

    vtds = V.fetch_vtds(cfg["fips"], shape, fail)
    if len(vtds) != cfg["vtds"]:
        fail("%s: the census voting-district layer carries %d features, expected %d"
             % (slug, len(vtds), cfg["vtds"]))
    county_geom, county_pop = V.fetch_county(cfg["fips"], shape, fail)
    if county_pop != cfg["pop"]:
        fail("%s: census county population is %d, expected %d"
             % (slug, county_pop, cfg["pop"]))
    V.check_fabric_composed(vtds, county_pop, fail)
    V.check_partition(comp, vtds, fail)

    districts, pops = V.dissolve(comp, vtds, unary_union)
    overlap, covered = V.check_tiling(districts, county_geom, transform,
                                      MAX_OVERLAP_M2, MIN_COVERED, unary_union, fail)
    lat = county_geom.centroid.y
    mx, my = 111320.0 * math.cos(math.radians(lat)), 110574.0

    def area(geom):
        return transform(lambda x, y, z=None: (x * mx, y * my), geom).area

    witnessed = 0
    if cfg["townships"]:
        witnessed = township_witness(cfg, vtds, districts, shape, unary_union, area)

    features = []
    keys = [k for k in cfg["order"] if k in comp] + [k for k in comp if "|" in k]
    for key in keys:
        names = comp[key]
        props = {"precincts": [V.title_case(n) for n in names],
                 "pop2020": pops[key], "areaKm2": round(area(districts[key]) / 1e6, 1)}
        if "|" in key:
            between = key.split("|")
            props.update({"district": None, "between": between,
                          "area": cfg["areas"][key],
                          "name": " or ".join(cfg["label"](d) for d in between),
                          "note": cfg["unplaced"]})
        else:
            props.update({"district": key, "name": cfg["label"](key),
                          "seats": cfg["seats"]})
        features.append({"type": "Feature", "properties": props,
                         "geometry": V.round_geom(districts[key], mapping)})

    # The app's own even-odd test against the rounded output: every census
    # precinct lands in the one feature its composition key names.
    for key, names in comp.items():
        for name in names:
            probe = vtds[V.norm(name)]["geom"].representative_point()
            hits = [f for f in features
                    if point_in_rings(probe.y, probe.x, V.rings_of(f["geometry"]))]
            want = key.split("|")
            got = [h["properties"].get("between") or [h["properties"]["district"]]
                   for h in hits]
            if got != [want]:
                fail("%s: precinct %s lands in %s after rounding, expected %s"
                     % (slug, name, got or "nothing", want))

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": cfg["source"], "planUrl": cfg["planUrl"],
            "boardUrl": cfg["boardUrl"],
            "note": ("Districts drawn where the county's own publication places "
                     "whole precincts or townships. Shared: %s."
                     % "; ".join("%s (%s)" % (cfg["areas"][k],
                                              " or ".join(cfg["label"](d) for d in k.split("|")))
                                 for k in comp if "|" in k)),
        },
        "features": features,
    }
    whole = [k for k in cfg["order"] if k in comp]
    whole_pop = sum(pops[k] for k in whole)
    shared_pop = county_pop - whole_pop
    print("%s: %d census voting districts -> %d districts drawn + %d shared area(s)"
          % (slug, len(vtds), len(whole), len(cfg["areas"])))
    print("  placed: %s; shared: %s — %d of %d people (%.1f%%) are in a shared area"
          % (", ".join("%s=%d" % (k, pops[k]) for k in whole),
             ", ".join("%s=%d" % (cfg["areas"][k], pops[k]) for k in cfg["areas"]),
             shared_pop, county_pop, 100.0 * shared_pop / county_pop))
    print("  tiling: overlap %.2f m2; %.4f%% of the county covered%s"
          % (overlap, 100 * covered,
             "; township witness held for %d groups" % witnessed if witnessed else ""))
    out = os.path.join(APP_DIR, "%s-county-board-districts.json" % slug)
    V.write_or_check([(out, V.dumps(payload))], check, REPO_ROOT, fail, slug)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--county", action="append", choices=sorted(COUNTIES))
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files match a fresh build")
    args = ap.parse_args()
    for slug in args.county or sorted(COUNTIES):
        build(slug, args.check)


if __name__ == "__main__":
    main()
