#!/usr/bin/env python3
"""
Tompkins County Legislature districts — the New York county tier's first county
===============================================================================
Writes two files:

  ny/data/app/tompkins-legislature-districts.json   the 16 districts
  ny/data/app/tompkins-county-outline.json          the dispatch entry's coverage test

THE FORM WAS PROVEN BEFORE THIS FILE EXISTED and is not re-argued here:
docs/DATA_LAYER_GUIDEBOOK.md's "Tompkins County's legislature, proven before
anything was built (measured 2026-09-26)" carries the county Board of
Elections' own results database settling that Tompkins elects a sixteen-member
County Legislature from single-member districts, and that its `County
Legislator` (a County office) is a different office from the `Supervisor` (a
Local one) a board-of-supervisors county would elect. Nothing in this file
re-probes that, and `tompkinsny.elstats2.civera.com` — whose robots.txt is a
`*` Disallow — is never fetched by anything here.

THE SOURCE. ArcGIS Online item 881285a45a6541979dde335fe57a689b,
`LegislativeDistrictBoundaries`, `access: public`, `licenseInfo` "Open to the
Public", credited to "Tompkins County ITS GIS Division, Tompkins County Board
of Elections and Tompkins 2012 Independent Redistricting Committee." That
credit line ships on the card; it is the licence's own Credits clause and not
decoration. The service's single layer is named `LigisDistNew` — a typo, and
the word "New", neither of which is evidence of anything: this builder decides
currency by MEASUREMENT (below), the way the Vermilion rebuild had to.

WHAT SHIPS AND WHAT DOES NOT. The layer also carries `Member` and `URL`
columns naming each district's legislator. THEY ARE NOT READ HERE. Coles's
board layer carried exactly such a column and got six of twelve names wrong,
so this project's rule is geometry from whatever proves the lines and people
from whatever the county maintains as people: the roster comes from the
county's own Legislature page and its own contact sheet
(tompkins_legislature_scraper.py), and that scraper re-reads this layer's
`Member` column every week as a free drift witness — a disagreement is
reported rather than shipped.

THE CURRENCY MEASUREMENT, which is the whole reason this builds at all.
Nothing in a layer's name, description or credits establishes that its
geometry is the plan in force. Four independent totals agree on the county,
and then sixteen agree on the districts:

  TIGERweb Census 2020 TRACT sum for county 36109 ......... 105,740
  TIGERweb Census 2020 BLOCK sum for county 36109 ......... 105,740
  ny-counties.json POP2020 (NYS ITS Civil Boundaries) ..... 105,740
  this layer's own TOTAL column, summed ................... 105,740

and every one of the county's 1,949 populated Census 2020 blocks, summed at
its own internal point into the district that contains it, reproduces that
district's published TOTAL EXACTLY — all sixteen, zero people out, with no
block falling in two districts and none in none. A sixteen-way identity over a
1,949-way partition, computed from another publisher's data, is what says the
geometry and the attributes describe the same plan and that the plan was
apportioned on the 2020 census. It is a GATE on the build path, not a note.

WHAT THAT MEASUREMENT DOES NOT SAY. It does not say when the lines were drawn.
The credits name a 2012 committee and the snippet says "Based on 2020 Census";
both are consistent with lines retained through the 2021 cycle and
re-tabulated on 2020 blocks, and this file asserts neither story. What is
established is that these sixteen districts balance on the 2020 census to the
person and that the county's own Legislature page and contact sheet name a
legislator for each of them today.

SIMPLIFICATION — interval 25 m, Douglas-Peucker, MEASURED not inherited.
Visvalingam thresholds triangle area, which does not bound how far the drawn
line strays from the true one; DP thresholds perpendicular deviation, which is
what a reader sees (the Illinois legislative rebuild of 2026-09-25 and this
instance's own build_ny_civil_boundaries.py both carry the argument). 25 m was
chosen for two measured reasons rather than copied:

  * the SOURCE's own step is a median 18.3 m across its 7,672 segments, so 25 m
    is about one step — the same basis the Illinois rebuild used at its own
    median of 17.9 m;
  * ny-counties.json already ships at interval 25 and the districts' OUTER edge
    is the county line, so a different interval would make the two disagree
    more than they need to.

Measured on the fetch this builder makes: 197,132 bytes and 7,688 vertices at
source become 20,636 bytes and 680 vertices at interval 25 (44,676 -> 4,864
gzipped), with the true line straying a worst 24.9 m and a mean 5.48 m from the
chord drawn in its place. The sweep is in the git history of this file's first
commit and in the guidebook.

ONE FILE, SO ONE TOPOLOGY. mapshaper builds an arc topology within a single
input, so the districts' shared interior edges are simplified once and stay
identical — measured, zero overlapping points at every interval tried. This is
why the 16 are fetched and simplified together and why there is no per-district
path: rebuilding one district alone is the defect that cost this instance its
towns and villages (ny/WATCH.md carries the row).

THE RIM IS TWO PUBLISHERS, NOT A DEFECT. NYS ITS draws Tompkins's county
boundary and Tompkins County draws its own, so they differ at source: the
shipped county ring's 136 vertices sit a median 4.3 m (mean 8.0 m, worst
120.9 m on the west edge) from Tompkins's own lines. The consequence is a thin
rim where the two disagree — measured 18 of 20,000 uniform points inside the
shipped county polygon fall in no district (0.09%), and 10 of 20,000 points in
a district fall outside it (0.05%), every one of them on the boundary. THE
COUNT IS THE SAME AT THE SOURCE AND AT EVERY INTERVAL, which is how it is
known to be the two drafts rather than the simplification. Nothing is snapped
or redrawn — the dispatcher's query returns null there and the card says no
district contains the point, which is true. RIM_GAP_MAX_PCT below is the
ceiling that stops it growing unnoticed.

THE COVERAGE OUTLINE is sliced from the shipped ny-counties.json rather than
fetched, so a point the `county` card calls Tompkins is a point this layer's
coverage test calls Tompkins. Fetching a third drawing of the same county
would have let the two answers disagree.

Usage:
    python3 ny/scripts/build_tompkins_legislature.py          # fetch + build (network, npx)
    python3 ny/scripts/build_tompkins_legislature.py --sweep  # print the interval sweep
    python3 ny/scripts/build_tompkins_legislature.py --check  # CI gate (offline, stdlib)

--check IS OFFLINE AND CANNOT SEE THE SOURCE, so it cannot re-measure the chord
stray; it re-derives everything that lives in the shipped bytes — the district
set, the four-way population identity against ny-counties.json, the county's own
deviation arithmetic, the partition, and that the coverage outline is still the
slice of the county fabric it claims to be.
"""
import argparse
import gzip
import json
import math
import os
import random
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
ROOT = os.path.dirname(INSTANCE)
APP = os.path.join(INSTANCE, "data", "app")
OUT_PATH = os.path.join(APP, "tompkins-legislature-districts.json")
OUTLINE_PATH = os.path.join(APP, "tompkins-county-outline.json")
COUNTIES_PATH = os.path.join(APP, "ny-counties.json")

UA = "districtry-newyork/1.0 (+https://districtry.com/ny/)"
MAPSHAPER = "mapshaper@0.6.102"   # the fleet pin, for reproducible output
PRECISION = "0.000001"            # 6 decimals ~= 0.11 m

# The service. The path is one contiguous literal so ny/scripts/validate_sources.py's
# substring drift guard has something to match (the Madison lesson: a URL split
# across two string literals is a URL no reader of this file can find).
SERVICE = ("https://services.arcgis.com/oJbAAWNInLrxvF0A/arcgis/rest/services/"
           "LegislativeDistrictBoundaries/FeatureServer/0")
ITEM_ID = "881285a45a6541979dde335fe57a689b"
CREDIT = ("Tompkins County ITS GIS Division, Tompkins County Board of Elections "
          "and Tompkins 2012 Independent Redistricting Committee.")

TIGERWEB_BLOCKS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                   "Tracts_Blocks/MapServer/12/query")
TIGERWEB_TRACTS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                   "Tracts_Blocks/MapServer/10/query")

COUNTY_FIPS = "36109"
STATE = "36"
COUNTY = "109"
DISTRICTS = 16

INTERVAL_M = 25
SWEEP_INTERVALS = (5, 10, 15, 20, 25, 30, 40)
CHORD_CEILING_M = 25.0
CHORD_OVER_CEILING_MAX_PCT = 0.10
# The rim above. 0.30% leaves headroom over the measured 0.09% for a later
# re-simplification of either file without licensing a real gap.
RIM_GAP_MAX_PCT = 0.30
PARTITION_SAMPLES = 20000
PARTITION_SEED = 2026

# ---------------------------------------------------------------------------
# geometry. The stdlib helpers live in the sibling builder, which is the one
# copy of them in this instance — importing rather than re-deriving is the
# point (two readers of one question is where this fleet's recurring defect
# starts). It imports nothing at module scope that needs the network.
sys.path.insert(0, HERE)
import build_ny_civil_boundaries as CIVIL  # noqa: E402
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

VK = CIVIL.VALIDATION_KEY


def fetch_json(url, params, timeout=180):
    q = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    require_robots_once(q, UA,
                        headers={"User-Agent": UA}, label="ny-build-tompkins-legislature")
    req = urllib.request.Request(q, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_districts():
    """The 16 districts as GeoJSON in WGS84, attributes and all."""
    data = fetch_json(SERVICE + "/query", {
        "where": "1=1",
        "outFields": "LegDist,DISTRICT,TOTAL,TARGET_DEV,TARGET_D_1,Member",
        "returnGeometry": "true", "outSR": "4326", "f": "geojson",
        "geometryPrecision": "7",
    })
    feats = data.get("features") or []
    if len(feats) != DISTRICTS:
        raise SystemExit("tompkins-legislature: the service returned %d features, expected %d — "
                         "the plan or the service changed" % (len(feats), DISTRICTS))
    for f in feats:
        f["properties"][VK] = "D%d" % int(f["properties"]["LegDist"])
    return feats


def check_attributes(feats):
    """The layer's own arithmetic, and its two district numberings.

    A SECOND NUMBERING IS A REAL TRAP ELSEWHERE IN THIS FLEET (Chicago's school
    board publishes 1A..10B while its boundary numbers 1-20, and the two
    collide), so the agreement of LegDist and DISTRICT is asserted rather than
    assumed. And TARGET_DEV (people) and TARGET_D_1 (percent) must reproduce
    from TOTAL against the county's own ideal — which is what says those columns
    were computed on THIS set of sixteen and not carried from another plan."""
    problems = []
    legs = sorted(int(f["properties"]["LegDist"]) for f in feats)
    if legs != list(range(1, DISTRICTS + 1)):
        problems.append("LegDist is %s, not 1..%d" % (legs, DISTRICTS))
    for f in feats:
        p = f["properties"]
        if int(p["LegDist"]) != int(p["DISTRICT"]):
            problems.append("district %s: LegDist and DISTRICT disagree (%s vs %s) — the layer has "
                            "two numberings and this builder reads LegDist"
                            % (p["LegDist"], p["LegDist"], p["DISTRICT"]))
    total = sum(int(round(f["properties"]["TOTAL"])) for f in feats)
    ideal = total / float(DISTRICTS)
    for f in feats:
        p = f["properties"]
        dev = int(round(p["TOTAL"])) - ideal
        if abs(dev - float(p["TARGET_DEV"])) > 1.0:
            problems.append("district %s: TARGET_DEV %s does not reproduce from TOTAL (%.1f)"
                            % (p["LegDist"], p["TARGET_DEV"], dev))
        pct = 100.0 * dev / ideal
        if abs(pct - float(p["TARGET_D_1"])) > 0.02:
            problems.append("district %s: TARGET_D_1 %s does not reproduce from TOTAL (%.2f)"
                            % (p["LegDist"], p["TARGET_D_1"], pct))
    return problems, total, ideal


def shipped_county():
    """Tompkins as the instance's own county fabric draws it."""
    with open(COUNTIES_PATH, encoding="utf-8") as fh:
        doc = json.load(fh)
    hits = [f for f in doc["features"] if f["properties"].get("FIPS_CODE") == COUNTY_FIPS]
    if len(hits) != 1:
        raise SystemExit("tompkins-legislature: ny-counties.json carries %d features for FIPS %s"
                         % (len(hits), COUNTY_FIPS))
    return hits[0]


def county_blocks():
    """Every populated Census 2020 block in the county, at its internal point.

    Paged the way scripts/build_block_population.py pages it, and held to the
    same census's TRACT sum — an aggregation nothing here performs."""
    stats = json.dumps([{"statisticType": "sum", "onStatisticField": "POP100",
                         "outStatisticFieldName": "pop"}])
    tracts = fetch_json(TIGERWEB_TRACTS, {"where": "STATE='%s' AND COUNTY='%s'" % (STATE, COUNTY),
                                          "outStatistics": stats, "f": "json"})
    tract_sum = int(tracts["features"][0]["attributes"]["pop"])
    out, offset = [], 0
    while True:
        data = fetch_json(TIGERWEB_BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, COUNTY),
            "outFields": "GEOID,INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": 20000,
            "f": "json",
        })
        feats = data.get("features") or []
        for f in feats:
            a = f["attributes"]
            out.append((a["GEOID"], float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"])))
        if len(feats) < 20000 and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    geoids = [b[0] for b in out]
    if len(set(geoids)) != len(geoids):
        raise SystemExit("tompkins-legislature: TIGERweb returned a block twice across pages")
    return out, tract_sum


def block_identity(feats, blocks):
    """Each district's published TOTAL, re-derived from another publisher's blocks.

    Returns (problems, per_district, none_count, none_pop, multi_count)."""
    model = CIVIL._model(feats)
    derived = {int(f["properties"]["LegDist"]): 0 for f in feats}
    none = none_pop = multi = 0
    for _gid, lng, lat, pop in blocks:
        hits = CIVIL._features_at(model, (lng, lat))
        if not hits:
            none += 1
            none_pop += pop
            continue
        if len(hits) > 1:
            multi += 1
        derived[int(hits[0][1:])] += pop
    problems = []
    if none:
        problems.append("%d populated block(s) (%d people) fall in NO district — the 16 do not "
                        "cover the county" % (none, none_pop))
    if multi:
        problems.append("%d populated block(s) fall in TWO districts — the 16 overlap" % multi)
    for f in feats:
        d = int(f["properties"]["LegDist"])
        want = int(round(f["properties"]["TOTAL"]))
        if derived[d] != want:
            problems.append("district %d: the county publishes %d and the census blocks inside it "
                            "sum to %d — geometry and attributes describe different plans"
                            % (d, want, derived[d]))
    return problems, derived, none, none_pop, multi


def run_mapshaper(src_path, interval, out_dir):
    subprocess.run(["npx", "-y", MAPSHAPER, "-i", src_path,
                    "-simplify", "dp", "keep-shapes", "interval=%d" % interval,
                    "-o", "precision=" + PRECISION, "format=geojson", out_dir],
                   check=True, cwd=ROOT, capture_output=True)
    names = os.listdir(out_dir)
    if len(names) != 1:
        raise SystemExit("tompkins-legislature: mapshaper wrote %d files, expected 1" % len(names))
    with open(os.path.join(out_dir, names[0]), encoding="utf-8") as fh:
        return json.load(fh), os.path.join(out_dir, names[0])


def simplify(feats, interval, tmp):
    os.makedirs(tmp, exist_ok=True)
    src = os.path.join(tmp, "in.json")
    with open(src, "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh)
    out_dir = os.path.join(tmp, "out%d" % interval)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    return run_mapshaper(src, interval, out_dir)


def partition_problems(feats, county, samples=PARTITION_SAMPLES, seed=PARTITION_SEED):
    """Two-sided: points in the county with no district, and points in a district
    outside the county. Overlaps FAIL; the rim is held to RIM_GAP_MAX_PCT."""
    model = CIVIL._model(feats)
    bb = CIVIL._bbox(county["geometry"])
    rng = random.Random(seed)
    inside = gaps = overlaps = 0
    while inside < samples:
        pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
        if not CIVIL._point_in_geometry(pt, county["geometry"]):
            continue
        inside += 1
        hits = CIVIL._features_at(model, pt)
        if not hits:
            gaps += 1
        elif len(hits) > 1:
            overlaps += 1
    spill = 0
    n = 0
    dbb = CIVIL._bbox({"type": "MultiPolygon",
                       "coordinates": [[r] for f in feats for r in CIVIL._rings(f["geometry"])]})
    while n < samples:
        pt = (rng.uniform(dbb[0], dbb[2]), rng.uniform(dbb[1], dbb[3]))
        if not CIVIL._features_at(model, pt):
            continue
        n += 1
        if not CIVIL._point_in_geometry(pt, county["geometry"]):
            spill += 1
    problems = []
    if overlaps:
        problems.append("%d of %d points inside the county fall in TWO districts — the shared "
                        "interior edges did not survive simplification" % (overlaps, samples))
    gap_pct = 100.0 * gaps / samples
    if gap_pct > RIM_GAP_MAX_PCT:
        problems.append("%.3f%% of points inside the county fall in no district, past the %.2f%% "
                        "ceiling — this is meant to be the two publishers' rim, so a bigger "
                        "share means a real hole" % (gap_pct, RIM_GAP_MAX_PCT))
    return problems, gaps, overlaps, spill


def strip(built_feats, ideal):
    """What ships. `Member`, `URL` and the validation key are deliberately dropped.

    IT TAKES THE SIMPLIFIED FEATURES, and the first draft took the fetched ones.
    Every gate still passed — the chord stray and the partition both measure the
    BUILT list, correctly — and the file written was the 197 KB source. So the
    caller asserts the written vertex count against the built one rather than
    trusting the argument: a gate that measures one list while the writer takes
    another is exactly the shape nothing else here can see."""
    out = []
    for f in sorted(built_feats, key=lambda x: int(x["properties"]["LegDist"])):
        p = f["properties"]
        out.append({"type": "Feature",
                    "properties": {"district": int(p["LegDist"]),
                                   "population": int(round(p["TOTAL"])),
                                   "deviationPct": round(100.0 * (int(round(p["TOTAL"])) - ideal) / ideal, 2)},
                    "geometry": f["geometry"]})
    return out


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")


def sweep():
    feats = fetch_districts()
    county = shipped_county()
    tmp = os.path.join(ROOT, ".tompkins-sweep")
    print("%-9s %9s %9s %7s %8s %8s  %s" %
          ("interval", "raw", "gzip", "verts", "worst_m", "mean_m", "partition"))
    for interval in SWEEP_INTERVALS:
        built, path = simplify(feats, interval, tmp)
        raw = os.path.getsize(path)
        with open(path, "rb") as fh:
            gz = len(gzip.compress(fh.read(), 9))
        verts = sum(len(r) for f in built["features"] for r in CIVIL._rings(f["geometry"]))
        worst, over, n, mean = CIVIL.chord_stray(feats, built["features"])
        _p, gaps, overlaps, spill = partition_problems(built["features"], county, samples=5000)
        print("%-9d %9d %9d %7d %8.1f %8.2f  gaps=%d ovl=%d spill=%d (of 5000)" %
              (interval, raw, gz, verts, worst, mean, gaps, overlaps, spill))
    shutil.rmtree(tmp, ignore_errors=True)


def build():
    feats = fetch_districts()
    county = shipped_county()
    county_pop = int(county["properties"]["POP2020"])

    problems, total, ideal = check_attributes(feats)
    if total != county_pop:
        problems.append("the layer's TOTAL column sums to %d and ny-counties.json publishes %d for "
                        "the same county and census" % (total, county_pop))

    blocks, tract_sum = county_blocks()
    block_sum = sum(b[3] for b in blocks)
    if tract_sum != county_pop or block_sum != county_pop:
        problems.append("the census does not agree with itself or with the county fabric: tracts "
                        "%d, populated blocks %d, ny-counties.json %d"
                        % (tract_sum, block_sum, county_pop))
    bp, derived, none, none_pop, multi = block_identity(feats, blocks)
    problems.extend(bp)

    built, path = simplify(feats, INTERVAL_M, os.path.join(ROOT, ".tompkins-build"))
    worst, over, nverts, mean = CIVIL.chord_stray(feats, built["features"])
    if worst > CHORD_CEILING_M:
        over_pct = 100.0 * over / nverts if nverts else 0.0
        if over_pct > CHORD_OVER_CEILING_MAX_PCT:
            problems.append("the true line strays a worst %.1f m from the chord drawn for it, and "
                            "%.3f%% of its vertices are past the %.0f m ceiling"
                            % (worst, over_pct, CHORD_CEILING_M))
    pp, gaps, overlaps, spill = partition_problems(built["features"], county)
    problems.extend(pp)

    if problems:
        for p in problems:
            print("tompkins-legislature: FAIL %s" % p, file=sys.stderr)
        raise SystemExit(1)

    write_json(OUT_PATH, {
        "type": "FeatureCollection",
        "_about": ("GENERATED by ny/scripts/build_tompkins_legislature.py from ArcGIS Online item "
                   + ITEM_ID + " (" + SERVICE + "), licenceInfo \"Open to the Public\", credited "
                   + CREDIT + " Simplified with mapshaper dp keep-shapes interval="
                   + str(INTERVAL_M) + " m. The 16 districts' populations are the county's own "
                   "TOTAL column, each re-derived to the person from the Census 2020 blocks "
                   "inside it. Member and URL columns deliberately not read — the roster comes "
                   "from the county's own pages."),
        "features": strip(built["features"], ideal),
    })
    with open(OUT_PATH, encoding="utf-8") as fh:
        written = json.load(fh)
    built_verts = sum(len(r) for f in built["features"] for r in CIVIL._rings(f["geometry"]))
    written_verts = sum(len(r) for f in written["features"] for r in CIVIL._rings(f["geometry"]))
    if written_verts != built_verts:
        raise SystemExit("tompkins-legislature: wrote %d vertices where the simplified layer has %d "
                         "— the writer took a different list from the one the gates measured"
                         % (written_verts, built_verts))
    outline = shipped_county()
    write_json(OUTLINE_PATH, {
        "type": "FeatureCollection",
        "_about": ("GENERATED by ny/scripts/build_tompkins_legislature.py — Tompkins County sliced "
                   "verbatim from ny/data/app/ny-counties.json so the county-legislature layer's "
                   "coverage test and the county card cannot disagree about where Tompkins is."),
        "features": [{"type": "Feature",
                      "properties": {"NAME": outline["properties"]["NAME"],
                                     "FIPS_CODE": outline["properties"]["FIPS_CODE"]},
                      "geometry": outline["geometry"]}],
    })
    shutil.rmtree(os.path.join(ROOT, ".tompkins-build"), ignore_errors=True)

    print("tompkins-legislature: OK %d districts, %d people (tracts %d, blocks %d, county fabric %d "
          "all agree), every district's population re-derived from its own blocks exactly, "
          "worst chord stray %.1f m (mean %.2f m), %d of %d in-county points in no district "
          "(%.3f%%, the two publishers' rim), %d overlaps, %d of %d in-district points outside the "
          "county polygon" % (len(feats), total, tract_sum, block_sum, county_pop, worst, mean,
                              gaps, PARTITION_SAMPLES, 100.0 * gaps / PARTITION_SAMPLES, overlaps,
                              spill, PARTITION_SAMPLES))
    print("tompkins-legislature: wrote %s (%d bytes, %d vertices, from %d at source) and %s "
          "(%d bytes)" %
          (os.path.relpath(OUT_PATH, ROOT), os.path.getsize(OUT_PATH), written_verts,
           sum(len(r) for f in feats for r in CIVIL._rings(f["geometry"])),
           os.path.relpath(OUTLINE_PATH, ROOT), os.path.getsize(OUTLINE_PATH)))


def check():
    problems = []
    for path in (OUT_PATH, OUTLINE_PATH, COUNTIES_PATH):
        if not os.path.exists(path):
            print("tompkins-legislature: FAIL %s is missing" % os.path.relpath(path, ROOT),
                  file=sys.stderr)
            return 1
    with open(OUT_PATH, encoding="utf-8") as fh:
        shipped = json.load(fh)
    feats = shipped["features"]
    county = shipped_county()
    county_pop = int(county["properties"]["POP2020"])

    nums = sorted(int(f["properties"]["district"]) for f in feats)
    if nums != list(range(1, DISTRICTS + 1)):
        problems.append("the shipped districts are %s, not 1..%d" % (nums, DISTRICTS))
    total = sum(int(f["properties"]["population"]) for f in feats)
    if total != county_pop:
        problems.append("the shipped populations sum to %d and ny-counties.json publishes %d"
                        % (total, county_pop))
    ideal = total / float(DISTRICTS)
    for f in feats:
        p = f["properties"]
        want = round(100.0 * (int(p["population"]) - ideal) / ideal, 2)
        if abs(want - float(p["deviationPct"])) > 0.01:
            problems.append("district %s: deviationPct %s does not reproduce from population (%.2f)"
                            % (p["district"], p["deviationPct"], want))

    for f in feats:
        f["properties"][VK] = "D%d" % int(f["properties"]["district"])
    pp, gaps, overlaps, spill = partition_problems(feats, county)
    problems.extend(pp)

    with open(OUTLINE_PATH, encoding="utf-8") as fh:
        outline = json.load(fh)
    if len(outline["features"]) != 1:
        problems.append("the coverage outline carries %d features, expected 1"
                        % len(outline["features"]))
    elif outline["features"][0]["geometry"] != county["geometry"]:
        problems.append("tompkins-county-outline.json is no longer the ny-counties.json slice it "
                        "claims to be — rebuild it in the same change as the county fabric")

    if problems:
        for p in problems:
            print("tompkins-legislature: FAIL %s" % p, file=sys.stderr)
        return 1
    print("tompkins-legislature: OK %d shipped districts summing to %d (ny-counties.json agrees), "
          "each deviation reproducing from its own population, %d of %d in-county points in no "
          "district (%.3f%%, the two publishers' rim), %d overlaps, %d of %d in-district points "
          "outside the county polygon, coverage outline identical to the county fabric's slice. "
          "The chord stray needs the source and is a build-path measurement, not this gate's."
          % (len(feats), total, gaps, PARTITION_SAMPLES, 100.0 * gaps / PARTITION_SAMPLES,
             overlaps, spill, PARTITION_SAMPLES))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Build Tompkins County's legislature districts.")
    ap.add_argument("--check", action="store_true", help="verify the shipped files, write nothing")
    ap.add_argument("--sweep", action="store_true", help="print the simplification sweep")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    if args.sweep:
        sweep()
        return 0
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
