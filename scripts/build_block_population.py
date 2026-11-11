#!/usr/bin/env python3
"""Build <tag>/data/app/population/, the Census 2020 block populations by county.

WHAT IT IS FOR. Comparing two districts by AREA says how much ground they
share; a reader asking whether their ward sits inside a congressional district
usually means PEOPLE. The apps had no population data, so this ships the
smallest unit the Census counts: every populated 2020 census block, as its
internal point and its POP100. The engine's measurePointWeight
(engine/index.html/geometry-measure.txt) sums the points inside a district, and
because congressional, legislative and ward maps are drawn on block lines,
that sum is the district's population rather than an estimate of it.
Districts that do not follow block lines (school districts, fire districts)
get a close figure, since a block straddling their edge counts wholly on the
side its internal point falls.

EVERY APP, ONE ROW EACH. Illinois had these from 2026-09-23; every other app
joined on 2026-11-06 (Adam: "All"). INSTANCES holds one row per app: its state
code, its published 2020 total, its county count, an extent every block must
fall inside, and the district maps held to it. San Francisco's row names its
one county and holds no maps, because its congressional and legislative
districts reach past the city and the files hold the city alone. The files
hold an app's own ground and nobody beyond it; the compare screen therefore
gives no share of its own people to a district reaching past that ground, and
compares a pinned district that does by area alone (engine compare-stats).

ONE FILE PER COUNTY, NOT PER STATE. A comparison needs only the counties a
district touches, so the app reads `index.json` (each county's extent,
population and file) and fetches the rest on demand. Nothing here is
precached: the service worker serves these by prefix, cached on first use, the
way it serves fonts. Unpopulated blocks are dropped; they add nothing to any
sum.

THE SOURCE AND ITS WITNESSES. Blocks come from TIGERweb's Census 2020 block
layer (Tracts_Blocks/MapServer/12), read county by county. The build refuses to
write unless three independent totals agree:
  - every county's block sum equals the SAME census's tract sum for that
    county (Tracts_Blocks/MapServer/10), an aggregation this script does not
    perform;
  - the state (or city) total equals its published 2020 count, read from
    tigerWMS_Census2020 and recorded in INSTANCES;
  - every block with people is kept: the blocks read per county add up to
    the populated-block count the layer itself reports.

THE POINTS ARE HELD TO THE DISTRICTS THEY WILL BE SUMMED INSIDE. --check also
runs the engine's own measurePointWeight, as shipped, over every congressional,
State Senate and State House (Assembly) district an app ships, and fails
unless each map's districts sum to the state's total less the number recorded
for that map (people whose block point falls outside every simplified
district, a net figure: a block counted twice offsets one counted nowhere),
and unless each district lands where its plan put it, within the map's
recorded tolerance of the equal-population ideal. Illinois's maps hold the
state EXACTLY and its tolerances are the plan's (0.01% congress, 1%
legislative). Every other row's figures were measured on 2026-11-06 on the
simplified district files the apps ship and are pinned (Pennsylvania's and
Nevada's on 2026-11-10, when they were built; Nevada's congressional map sits
0.31% from the raw-census ideal and its Assembly map up to 5.96%): an
uncounted number that moves, or a district further from its ideal than
recorded, fails. Some
plans sit far from the raw-census ideal by design (New York draws on
prisoner-adjusted counts; several states allow 5% either way), which is why
those tolerances are wide; they still catch a map swapped for another.

WHEN IT CHANGES. Not until the 2030 census publishes blocks (2031). WATCH.md
carries the row. --check re-derives every file's totals, extent and count from
its own points against index.json, so a hand edit or a truncated file fails
CI. It is offline and needs only the standard library and Node.

Usage:
  python3 scripts/build_block_population.py --instance wi   # rebuild one app (network)
  python3 scripts/build_block_population.py --check         # CI gate, every app (offline; stdlib + node)
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "districtry-block-population/1.0 (+https://districtry.com/)"
SERVICE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer"
BLOCKS = SERVICE + "/12"   # Census 2020 > Census Blocks
TRACTS = SERVICE + "/10"   # Census 2020 > Census Tracts
COUNTIES = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1"
# The 2020 county polygons, water included, for an app whose own outline is
# drawn on land (San Francisco's is the union of its supervisor districts):
# see GROUND below.
COUNTIES_2020 = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/82"
DIGITS = 5                 # ~1 m; a block's internal point only has to land on the right side of a line
PAGE = 20000

# One row per instance that ships block populations. `total` is the place's
# 2020 Census count (P.L. 94-171 POP100), read 2026-11-06 from TIGERweb's
# Census 2020 States layer (tigerWMS_Census2020/MapServer/80), and for San
# Francisco from its Counties layer (/82): a THIRD witness beside the blocks
# and the tracts, which the build never computes. `counties` is how many
# counties (and county-equivalents: Virginia's independent cities, St. Louis
# city) the place holds, or for a city instance the county codes it covers.
# `bbox` is the state's extent from the same States layer, rounded outward by
# 0.01 degree: every point must fall inside it. `maps` are the shipped district
# files each instance draws from, held to the plan each was drawn to (below);
# a city instance has none, because its districts reach past the city.
#
# THE MAP TOLERANCES ARE MEASURED, NOT CHOSEN FROM A STATUTE. A plan puts each
# district within a stated range of the ideal, and the shipped outline is
# simplified, so a block whose internal point lands across a simplified line
# moves its people to a neighbour. The tolerance is that error plus the plan's
# own range, rounded up from what the run of 2026-11-06 measured.
CONGRESS, LEGIS = 0.0001, 0.01
INSTANCES = {
    "il": {"name": "Illinois", "state": "17", "total": 12812508, "counties": 102,
           "bbox": (-92.0, 36.9, -87.0, 42.6),
           "maps": [("congress-districts.json", 17, CONGRESS), ("il-senate-districts.json", 59, LEGIS),
                    ("il-house-districts.json", 118, LEGIS)]},
    "ca": {"name": "San Francisco", "state": "06", "total": 873965, "counties": ("075",),
           "bbox": (-123.18, 37.63, -122.27, 37.94),
           "maps": [], "ground": True},
    "ny": {"name": "New York", "state": "36", "total": 20201249, "counties": 62,
           "bbox": (-79.77, 40.47, -71.77, 45.03),
           "maps": [("congress-districts.json", 26, 0.002, 5), ("state-senate-districts.json", 63, 0.025, 5),
                    ("state-assembly-districts.json", 150, 0.075, 5)]},
    "wi": {"name": "Wisconsin", "state": "55", "total": 5893718, "counties": 72,
           "bbox": (-92.9, 42.48, -86.24, 47.32),
           "maps": [("congress-districts.json", 8, 0.0005, 11), ("wi-senate-districts.json", 33, 0.01, 52),
                    ("wi-assembly-districts.json", 99, 0.01, 52)]},
    "ia": {"name": "Iowa", "state": "19", "total": 3190369, "counties": 99,
           "bbox": (-96.65, 40.37, -90.13, 43.51),
           "maps": [("congress-districts.json", 4, 0.0005), ("ia-senate-districts.json", 50, 0.01),
                    ("ia-house-districts.json", 100, 0.015)]},
    "mi": {"name": "Michigan", "state": "26", "total": 10077331, "counties": 83,
           "bbox": (-90.43, 41.69, -82.11, 48.32),
           "maps": [("congress-districts.json", 13, 0.001), ("mi-senate-districts.json", 38, 0.025),
                    ("mi-house-districts.json", 110, 0.025)]},
    "mn": {"name": "Minnesota", "state": "27", "total": 5706494, "counties": 87,
           "bbox": (-97.25, 43.49, -89.47, 49.39),
           "maps": [("congress-districts.json", 8, 0.0005), ("mn-senate-districts.json", 67, 0.01),
                    ("mn-house-districts.json", 134, 0.015)]},
    "ky": {"name": "Kentucky", "state": "21", "total": 4505836, "counties": 120,
           "bbox": (-89.58, 36.49, -81.95, 39.16),
           "maps": [("congress-districts.json", 6, 0.0005), ("ky-senate-districts.json", 38, 0.05),
                    ("ky-house-districts.json", 100, 0.05)]},
    "in": {"name": "Indiana", "state": "18", "total": 6785528, "counties": 92,
           "bbox": (-88.11, 37.76, -84.77, 41.77),
           "maps": [("congress-districts.json", 9, 0.0005), ("in-senate-districts.json", 50, 0.02),
                    ("in-house-districts.json", 100, 0.01)]},
    "nc": {"name": "North Carolina", "state": "37", "total": 10439388, "counties": 100,
           "bbox": (-84.33, 33.74, -75.39, 36.6),
           "maps": [("congress-districts.json", 14, 0.0005), ("nc-senate-districts.json", 50, 0.05),
                    ("nc-house-districts.json", 120, 0.05)]},
    "ok": {"name": "Oklahoma", "state": "40", "total": 3959353, "counties": 77,
           "bbox": (-103.01, 33.61, -94.42, 37.01),
           "maps": [("congress-districts.json", 5, 0.0005), ("ok-senate-districts.json", 48, 0.03),
                    ("ok-house-districts.json", 101, 0.025)]},
    "sc": {"name": "South Carolina", "state": "45", "total": 5118425, "counties": 46,
           "bbox": (-83.36, 31.99, -78.49, 35.23),
           "maps": [("congress-districts.json", 7, 0.0005), ("sc-senate-districts.json", 46, 0.05),
                    ("sc-house-districts.json", 124, 0.025)]},
    "tn": {"name": "Tennessee", "state": "47", "total": 6910840, "counties": 95,
           "bbox": (-90.32, 34.97, -81.64, 36.69),
           "maps": [("congress-districts.json", 9, 0.0005, 7), ("tn-senate-districts.json", 33, 0.035, 7),
                    ("tn-house-districts.json", 99, 0.055, 7)]},
    "ar": {"name": "Arkansas", "state": "05", "total": 3011524, "counties": 75,
           "bbox": (-94.63, 32.99, -89.63, 36.51),
           "maps": [("congress-districts.json", 4, 0.001), ("ar-senate-districts.json", 35, 0.03),
                    ("ar-house-districts.json", 100, 0.04)]},
    "ms": {"name": "Mississippi", "state": "28", "total": 2961279, "counties": 82,
           "bbox": (-91.67, 30.13, -88.09, 35.01),
           "maps": [("congress-districts.json", 4, 0.0005), ("ms-senate-districts.json", 52, 0.05),
                    ("ms-house-districts.json", 122, 0.05)]},
    "la": {"name": "Louisiana", "state": "22", "total": 4657757, "counties": 64,
           "bbox": (-94.05, 28.85, -88.75, 33.03),
           "maps": [("congress-districts.json", 6, 0.0005), ("la-senate-districts.json", 39, 0.055),
                    ("la-house-districts.json", 105, 0.05)]},
    "mo": {"name": "Missouri", "state": "29", "total": 6154913, "counties": 115,
           "bbox": (-95.78, 35.99, -89.09, 40.62),
           "maps": [("congress-districts.json", 8, 0.0005), ("mo-senate-districts.json", 34, 0.03),
                    ("mo-house-districts.json", 163, 0.03)]},
    "va": {"name": "Virginia", "state": "51", "total": 8631393, "counties": 133,
           "bbox": (-83.69, 36.53, -75.16, 39.48),
           "maps": [("congress-districts.json", 11, 0.0065), ("va-senate-districts.json", 40, 0.03),
                    ("va-house-districts.json", 100, 0.07)]},
    "ga": {"name": "Georgia", "state": "13", "total": 10711908, "counties": 159,
           "bbox": (-85.62, 30.35, -80.77, 35.01),
           "maps": [("congress-districts.json", 14, 0.0005), ("ga-senate-districts.json", 56, 0.015),
                    ("ga-house-districts.json", 180, 0.015)]},
    "wv": {"name": "West Virginia", "state": "54", "total": 1793716, "counties": 55,
           "bbox": (-82.65, 37.19, -77.71, 40.65),
           "maps": [("congress-districts.json", 2, 0.001, 4), ("wv-senate-districts.json", 17, 0.05, 4),
                    ("wv-house-districts.json", 100, 0.05, 4)]},
    "pa": {"name": "Pennsylvania", "state": "42", "total": 13002700, "counties": 67,
           "bbox": (-80.53, 39.71, -74.68, 42.52),
           "maps": [("congress-districts.json", 17, 0.0005), ("pa-senate-districts.json", 50, 0.045),
                    ("pa-house-districts.json", 203, 0.055)]},
    "nv": {"name": "Nevada", "state": "32", "total": 3104614, "counties": 17,
           "bbox": (-120.01, 35.0, -114.03, 42.01),
           "maps": [("congress-districts.json", 4, 0.0035), ("nv-senate-districts.json", 21, 0.045),
                    ("nv-assembly-districts.json", 42, 0.06)]},
    # One legislative map for both chambers: az-legislative-districts.json
    # serves the Senate and the House layers alike, so it is held once.
    "az": {"name": "Arizona", "state": "04", "total": 7151502, "counties": 15,
           "bbox": (-114.82, 31.33, -109.04, 37.01),
           "maps": [("congress-districts.json", 9, 0.0005), ("az-legislative-districts.json", 30, 0.055)]},
    # One legislative map for both chambers, as Arizona's. The congressional
    # tolerance is wide because the plan is far from the raw-census ideal:
    # measured 2026-11-11 on the shipped outline, District 2 holds 0.642% over
    # it and District 3 0.509%, the two that hold the state's southern prisons
    # and the federal prison at Fort Dix, which fits a plan drawn on
    # prisoner-adjusted counts (New Jersey's 2020 law counts an incarcerated
    # person at their home address); which count the commission used was not
    # read. The legislative plan's worst is 3.24% (District 38).
    "nj": {"name": "New Jersey", "state": "34", "total": 9288994, "counties": 21,
           "bbox": (-75.57, 38.78, -73.88, 41.36),
           "maps": [("congress-districts.json", 12, 0.0065), ("nj-legislative-districts.json", 40, 0.035)]},
    # NEW HAMPSHIRE'S HOUSE MAP IS NOT HELD HERE, and that is the plan's shape
    # rather than an omission: its 164 base districts elect between one and ten
    # representatives each, so one ideal of the state's people over 164
    # districts describes no district, and each is named for its county and a
    # number ("Hillsborough 10") rather than numbered. Its partition of the
    # state is held by nh/scripts/build_legislative_boundaries.py's own
    # 2,000-point gate instead. Measured 2026-11-11 on the shipped outlines,
    # the two congressional districts sit within 0.0005% of their ideal,
    # and the Senate plan's worst district is 5.45% over the raw-census ideal,
    # inside the 10% total deviation a state plan may carry.
    "nh": {"name": "New Hampshire", "state": "33", "total": 1377529, "counties": 10,
           "bbox": (-72.56, 42.69, -70.57, 45.31),
           "maps": [("congress-districts.json", 2, 0.0005), ("nh-senate-districts.json", 24, 0.055)]},
}
def fetch(url, params):
    q = url + "/query?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            require_robots_once(q, UA,
                                headers={"User-Agent": UA}, label="build-block-population")
            req = urllib.request.Request(q, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(data["error"])
            return data
        except Exception as err:  # noqa: BLE001 — retried, then raised
            if attempt == 3:
                raise
            print("build-block-population: retrying after %s" % err, file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def out_dir(tag):
    return os.path.join(ROOT, tag, "data", "app", "population")


def county_where(spec, extra=""):
    where = "STATE='%s'" % spec["state"]
    if isinstance(spec["counties"], tuple):
        where += " AND COUNTY IN (%s)" % ",".join("'%s'" % c for c in spec["counties"])
    return where + extra


def county_count(spec):
    return len(spec["counties"]) if isinstance(spec["counties"], tuple) else spec["counties"]


def sum_by_county(spec, url, extra_where=""):
    stats = json.dumps([
        {"statisticType": "sum", "onStatisticField": "POP100", "outStatisticFieldName": "pop"},
        {"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"},
    ])
    data = fetch(url, {"where": county_where(spec, extra_where), "groupByFieldsForStatistics": "COUNTY",
                       "outStatistics": stats, "f": "json"})
    return {f["attributes"]["COUNTY"]: (int(f["attributes"]["pop"]), int(f["attributes"]["n"]))
            for f in data["features"]}


def county_names(spec):
    data = fetch(COUNTIES, {"where": county_where(spec), "outFields": "COUNTY,NAME",
                            "returnGeometry": "false", "f": "json"})
    return {f["attributes"]["COUNTY"]: f["attributes"]["NAME"] for f in data["features"]}


def county_blocks(spec, county):
    out, offset = [], 0
    while True:
        data = fetch(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (spec["state"], county),
            "outFields": "GEOID,INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": PAGE, "f": "json",
        })
        feats = data.get("features") or []
        for f in feats:
            a = f["attributes"]
            out.append((a["GEOID"], round(float(a["INTPTLON"]), DIGITS), round(float(a["INTPTLAT"]), DIGITS),
                        int(a["POP100"])))
        if len(feats) < PAGE and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    geoids = [b[0] for b in out]
    if len(set(geoids)) != len(geoids):
        raise SystemExit("build-block-population: county %s returned a block twice across pages" % county)
    return out


def extent(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")


def about(spec):
    if isinstance(spec["counties"], tuple):
        scope, sums = "%s (the one county this app covers)" % spec["name"], "the city sums to"
    else:
        scope, sums = "%s county" % spec["name"], "the state sums to"
    return ("GENERATED by scripts/build_block_population.py. Census 2020 populated blocks (POP100 > 0) "
            "by %s, each as [lng, lat, population] at its internal point, from TIGERweb "
            "Tracts_Blocks/MapServer/12. Every county's sum equals the same census's tract sum; %s "
            "%s. Fixed until the 2030 census publishes blocks. Never hand-edit."
            % (scope, sums, format(spec["total"], ",")))


# GROUND. The compare screen gives no share of its own people to a district
# reaching past the ground these files hold, and it reads that ground from the
# outline the app drew its wash with. A state's outline traces the state line
# through its water, as its districts do, so measured 2026-11-06 no state
# legislative or congressional district has more than 0.06% of its area
# outside it. San Francisco's outline is the union of its supervisor
# districts, which is land, while its Assembly districts carry the Bay to the
# county line, so 67% of Assembly District 17, which lies wholly in the city,
# read as outside. A row that sets "ground" therefore ships the counties' own
# 2020 polygons, water included and unsimplified (18 KB for San Francisco;
# simplified to 20 m it left 49 people's block points outside), as
# ground.json, and the screen reads that instead; --check requires every
# block point to lie inside it.
def fetch_ground(spec):
    data = fetch(COUNTIES_2020, {"where": county_where(spec), "outFields": "GEOID", "returnGeometry": "true",
                                 "outSR": "4326", "geometryPrecision": "5",
                                 "f": "json"})
    rings = []
    for f in data["features"]:
        rings.extend(f["geometry"]["rings"])
    if len(data["features"]) != county_count(spec) or not rings:
        raise SystemExit("build-block-population: the 2020 county layer gave %d polygon(s) for %d county(ies)"
                         % (len(data["features"]), county_count(spec)))
    # Esri rings: outer rings clockwise, holes counter-clockwise; the engine
    # tests even-odd, so one Polygon holding every ring answers the same.
    return {"type": "Polygon", "coordinates": rings}


def build(tag):
    spec = INSTANCES[tag]
    want = county_count(spec)
    names = county_names(spec)
    tracts = sum_by_county(spec, TRACTS)
    populated = sum_by_county(spec, BLOCKS, " AND POP100>0")
    if len(names) != want or set(names) != set(tracts):
        raise SystemExit("build-block-population: %s: expected %d counties, the county layer has %d and the "
                         "tract layer %d" % (tag, want, len(names), len(tracts)))
    od = out_dir(tag)
    os.makedirs(od, exist_ok=True)
    index, fails = {}, []
    for county in sorted(names):
        blocks = county_blocks(spec, county)
        pop = sum(b[3] for b in blocks)
        if pop != tracts[county][0]:
            fails.append("%s: blocks sum to %d, its tracts to %d" % (names[county], pop, tracts[county][0]))
        if len(blocks) != populated.get(county, (0, 0))[1]:
            fails.append("%s: read %d populated blocks, the layer reports %d"
                         % (names[county], len(blocks), populated.get(county, (0, 0))[1]))
        points = [[b[1], b[2], b[3]] for b in blocks]
        fips = spec["state"] + county
        write_json(os.path.join(od, fips + ".json"), {
            "county": fips, "name": names[county], "population": pop, "blocks": len(points), "points": points})
        index[fips] = {"name": names[county], "file": fips + ".json", "population": pop,
                       "blocks": len(points), "bbox": extent(points)}
        print("build-block-population: %s %-26s %8d people in %6d blocks" % (tag, names[county], pop, len(points)))
    total = sum(c["population"] for c in index.values())
    if total != spec["total"]:
        fails.append("%s sums to %d, the 2020 census count is %d" % (spec["name"], total, spec["total"]))
    if fails:
        raise SystemExit("build-block-population: %s: refusing to write the index:\n  - " % tag
                         + "\n  - ".join(fails))
    doc = {
        "_about": about(spec),
        "source": BLOCKS, "vintage": "2020 Census (P.L. 94-171)", "state_population": total,
        "counties": index,
    }
    if spec.get("ground"):
        write_json(os.path.join(od, "ground.json"), fetch_ground(spec))
        doc["ground"] = "ground.json"
    write_json_indented(os.path.join(od, "index.json"), doc)
    print("build-block-population: %s: wrote %d county files, %d people in %d blocks"
          % (tag, len(index), total, sum(c["blocks"] for c in index.values())))


def write_json_indented(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


# The engine block, the files, and the plan each map was drawn to.
MEASURE_BLOCK = os.path.join(ROOT, "engine", "index.html", "geometry-measure.txt")
# A district's BASENAME is its number, with a letter after it where a state
# splits a senate district in two (Minnesota's 1A and 1B). Anything else is
# the Census's "ZZ" water filler, which holds no blocks and is no district.
NODE_DRIVER = r"""
const fs = require("fs");
const [block, dir, ...maps] = process.argv.slice(1);
const m = new Function(fs.readFileSync(block, "utf8") + "\nreturn { measurePointWeight };")();
const idx = JSON.parse(fs.readFileSync(dir + "/index.json", "utf8"));
const pts = [];
for (const c of Object.values(idx.counties)) for (const p of JSON.parse(fs.readFileSync(dir + "/" + c.file, "utf8")).points) pts.push(p);
const out = {};
for (const f of maps) {
  out[f] = JSON.parse(fs.readFileSync(f, "utf8")).features
    .filter((x) => /^\d+[A-Z]?$/.test(String((x.properties || {}).BASENAME)))
    .map((x) => [String(x.properties.BASENAME), m.measurePointWeight(x.geometry, pts)]);
}
process.stdout.write(JSON.stringify(out));
"""


GROUND_DRIVER = r"""
const fs = require("fs");
const [block, dir] = process.argv.slice(1);
const m = new Function(fs.readFileSync(block, "utf8") + "\nreturn { measurePointWeight };")();
const idx = JSON.parse(fs.readFileSync(dir + "/index.json", "utf8"));
const ground = JSON.parse(fs.readFileSync(dir + "/" + idx.ground, "utf8"));
let sum = 0;
for (const c of Object.values(idx.counties)) sum += m.measurePointWeight(ground, JSON.parse(fs.readFileSync(dir + "/" + c.file, "utf8")).points);
process.stdout.write(String(sum));
"""


def check_districts(tag):
    """The points summed inside the shipped legislative maps, by the engine's
    own block: each map must partition the place exactly and put each
    district where its plan did."""
    spec = INSTANCES[tag]
    if not spec["maps"]:
        return [], "no district maps held to it"
    maps = [os.path.join(ROOT, tag, "data", "app", f) for f, *_ in spec["maps"]]
    res = subprocess.run(["node", "-e", NODE_DRIVER, MEASURE_BLOCK, out_dir(tag)] + maps,
                         capture_output=True, text=True)
    if res.returncode != 0:
        return ["the engine's measurePointWeight did not run in Node:\n" + res.stderr[-1500:]], ""
    got = json.loads(res.stdout)
    fails, notes = [], []
    for entry, path in zip(spec["maps"], maps):
        rel, n, tol = entry[:3]
        gap = entry[3] if len(entry) > 3 else 0
        rows = got[path]
        name = "%s/%s" % (tag, rel)
        if len(rows) != n:
            fails.append("%s: %d numbered districts, expected %d" % (name, len(rows), n))
            continue
        total = sum(p for _, p in rows)
        if spec["total"] - total != gap:
            fails.append("%s: its districts hold %d people, %s %d, so %d are counted in no district "
                         "(or, if negative, twice) where %d is recorded — a block falls in no district "
                         "or in two" % (name, total, spec["name"], spec["total"], spec["total"] - total, gap))
        ideal = spec["total"] / n
        worst = max(rows, key=lambda r: abs(r[1] - ideal))
        dev = (worst[1] - ideal) / ideal
        if abs(dev) > tol:
            fails.append("%s: District %s holds %d people, %.3f%% from its %.0f ideal (allowed %.2f%%)"
                         % (name, worst[0], worst[1], 100 * dev, ideal, 100 * tol))
        notes.append("%s worst %+.3f%%%s" % (rel.replace("-districts.json", ""), 100 * dev,
                                             ", %d uncounted" % gap if gap else ""))
    return fails, ", ".join(notes)


def check_one(tag):
    spec = INSTANCES[tag]
    od = out_dir(tag)
    index_path = os.path.join(od, "index.json")
    fails = []
    if not os.path.exists(index_path):
        return ["%s is missing; run the builder with --instance %s" % (os.path.relpath(index_path, ROOT), tag)], ""
    with open(index_path, encoding="utf-8") as fh:
        idx = json.load(fh)
    counties = idx.get("counties") or {}
    want = county_count(spec)
    if len(counties) != want:
        fails.append("index names %d counties, %s has %d" % (len(counties), spec["name"], want))
    on_disk = set(f for f in os.listdir(od) if f.endswith(".json")) - {"index.json"}
    if spec.get("ground"):
        on_disk.discard("ground.json")
        if idx.get("ground") != "ground.json" or not os.path.exists(os.path.join(od, "ground.json")):
            fails.append("this row sets ground, and index.json does not name a ground.json in the folder")
    elif "ground" in idx:
        fails.append("index.json names a ground file and this row sets none")
    named = set(c["file"] for c in counties.values())
    for f in sorted(on_disk - named):
        fails.append("%s is in the folder and not in index.json" % f)
    for f in sorted(named - on_disk):
        fails.append("index.json names %s, which is not in the folder" % f)
    x0, y0, x1, y1 = spec["bbox"]
    total = 0
    for fips, rec in sorted(counties.items()):
        path = os.path.join(od, rec["file"])
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        pts = doc.get("points") or []
        pop = 0
        bad = 0
        for p in pts:
            if (len(p) != 3 or not isinstance(p[2], int) or p[2] <= 0 or not (x0 < p[0] < x1)
                    or not (y0 < p[1] < y1)):
                bad += 1
            else:
                pop += p[2]
        if bad:
            fails.append("%s: %d point(s) are not [lng, lat, positive population] inside %s"
                         % (rec["name"], bad, spec["name"]))
        if not fips.startswith(spec["state"]) or doc.get("county") != fips or doc.get("name") != rec["name"]:
            fails.append("%s: the file says it is %r (%r)" % (fips, doc.get("county"), doc.get("name")))
        if pop != rec["population"] or pop != doc.get("population"):
            fails.append("%s: points sum to %d, the file says %s and the index %s"
                         % (rec["name"], pop, doc.get("population"), rec["population"]))
        if len(pts) != rec["blocks"] or len(pts) != doc.get("blocks"):
            fails.append("%s: %d points, the index says %d blocks" % (rec["name"], len(pts), rec["blocks"]))
        if pts and not bad and extent(pts) != rec["bbox"]:
            fails.append("%s: its points' extent is not the one the index records" % rec["name"])
        total += pop
    if total != spec["total"] or idx.get("state_population") != spec["total"]:
        fails.append("the counties sum to %d (index says %s); %s's 2020 census count is %d"
                     % (total, idx.get("state_population"), spec["name"], spec["total"]))
    if idx.get("_about") != about(spec):
        fails.append("index.json's _about is not the one the builder writes")
    notes = ""
    if not fails and spec.get("ground"):
        res = subprocess.run(["node", "-e", GROUND_DRIVER, MEASURE_BLOCK, od], capture_output=True, text=True)
        if res.returncode != 0:
            fails.append("the ground check did not run in Node:\n" + res.stderr[-1500:])
        elif int(res.stdout) != spec["total"]:
            fails.append("ground.json holds %s of %s's %d people; every block point must lie inside it"
                         % (res.stdout.strip(), spec["name"], spec["total"]))
    if not fails:
        more, notes = check_districts(tag)
        fails += more
    summary = ("%s %d county file(s), %s people in %s blocks (%s)"
               % (tag, len(counties), format(total, ","), format(sum(c["blocks"] for c in counties.values()), ","),
                  notes))
    return fails, summary


def worksheet_declares(tag):
    """A folder no app reads is dead weight, and an app reading a folder
    nobody built is a broken compare screen: the worksheet key and the
    table must name the same instances."""
    ws = os.path.join(ROOT, "metro-worksheet.json" if tag == "il" else os.path.join(tag, "metro-worksheet.json"))
    with open(ws, encoding="utf-8") as fh:
        return (json.load(fh).get("population") or {}).get("index") == "population/index.json"


def check(tags):
    fails, summaries = [], []
    for tag in tags:
        f, summary = check_one(tag)
        fails += ["%s: %s" % (tag, x) for x in f]
        if not worksheet_declares(tag):
            fails.append("%s: its worksheet does not declare population.index = population/index.json, so "
                         "no app reads these files" % tag)
        summaries.append(summary)
    for d in sorted(os.listdir(ROOT)):
        if (os.path.isdir(os.path.join(ROOT, d, "data", "app", "population")) and d not in INSTANCES):
            fails.append("%s/data/app/population/ exists and INSTANCES has no row for it" % d)
    if fails:
        print("build-block-population: FAIL")
        for f in fails:
            print("  - " + f)
        return 1
    print("build-block-population: OK — every file's sum, count and extent match its index, every place matches "
          "its 2020 census count, and each district map holds it to the count recorded for that map: " + "; ".join(summaries))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="offline CI gate; never writes")
    ap.add_argument("--instance", action="append", choices=sorted(INSTANCES),
                    help="build or check only this instance (repeatable; default every instance)")
    args = ap.parse_args()
    tags = args.instance or sorted(INSTANCES)
    if args.check:
        sys.exit(check(tags))
    for tag in tags:
        build(tag)
    sys.exit(check(tags))


if __name__ == "__main__":
    main()
