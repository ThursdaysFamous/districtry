#!/usr/bin/env python3
"""
Build data/app/jo-daviess-county-board-districts.json — Jo Daviess County's 17
single-member County Board districts, from the county's OWN board-district
shapefile, purchased and licensed 2026-08-17.

THE SOURCE, AND WHY IT IS NOT IN THE REPO. Jo Daviess cuts 14 of its 17
districts across precincts along roads (its own 2 Dec 2021 mapping memo: "If
one of those boundaries needed to be split I used roads"), publishes the
adopted map only as a picture, and runs no public GIS service — so no dissolve,
tracing or derivation could produce these lines, and the county's shapefile was
the only route (the gap record jo-daviess-county-board-districts, retired the
day this shipped). The export was purchased from Jo Daviess County GIS under
the county's Digital Data License Agreement #008382 ($33.50, invoice/order
008382 dated 8/17/2026, paid online 2026-08-17; the signed licence and payment
receipt were returned to the county the same day) and delivered by GIS
Technician/Website Administrator Diane LaScala by e-mail, 2026-08-17 15:34Z,
on the thread "County board district boundaries — public release, or a digital
data order?" ("Thank you Adam. Attached are your files").

THE LICENCE SHAPES THIS BUILD. The agreement's Protection of Proprietary
Rights clause forbids redistribution of the dataset and derived products
"without permission from JoDavGIS", and IT/GIS Director Joe Kratcha supplied
that permission in writing the same day: "Please let this email serve as
official authorization, in addition to the signed license agreement, granting
you permission to display the requested Jo Daviess County Board District
boundaries to be provided in shapefile format on your website: chidistricts.com
for public viewing." (e-mail of 2026-08-17 13:49Z, same thread). That
authorization covers DISPLAY — which the simplified data/app file is — and does
NOT cover republishing the raw dataset, so, as a DELIBERATE DEVIATION from the
data/source/raw convention, THE RAW SHAPEFILE IS NOT COMMITTED.

THE PERMISSION NAMED A DOMAIN, AND THE DOMAIN CHANGED. Kratcha's 2026-08-17
wording authorized display on "chidistricts.com"; the site was renamed to
districtry.com, and a permission that names a domain says what it names, so the
carryover was ASKED rather than assumed (2026-08-29) and CONFIRMED on
2026-08-31: "I confirm you are authorized to use the Jo Daviess County Board
district shapefiles provided under GIS Digital Data License Agreement #008328 on
the new districtry.com website as noted below in your email." The licence number
there, #008328, is a DIGIT TRANSPOSITION of #008382 — the number on the invoice,
on the signed agreement, and in the request being replied to — and is quoted as
written rather than corrected, so a reader comparing the two is not left
guessing. "As noted below in your email" incorporates the request's four stated
conditions (free public map, no redistribution, county credited, the file
excluded from this project's own ODbL grant), which LICENSE-DATA.md §3 holds to. The originals are retained offline (the operator's Drive and
the session archive); this header records each component's byte size and
sha256 so a re-supplied copy can be authenticated against the licensed
delivery:

    CountyBoardDistricts_2021.shp  4,813,436 bytes
        sha256 a47b838f0a545cf40c9c03db8ea3b34d11f4fa07b941ff5d46a2f48326cc69e3
    CountyBoardDistricts_2021.shx        236 bytes
        sha256 d928769c1c6ab1df3e972f36f05174ad7364331ed173cb31e305e807f7cf15f6
    CountyBoardDistricts_2021.dbf      2,017 bytes
        sha256 5d37eb35509771713a208ff5160ff03816dc6e95c98aa1674df940262c2161ca
    CountyBoardDistricts_2021.prj        508 bytes
        sha256 fc369c037a014a9705729aecf012c2434432c2e6020b6ab91598cc34c156dfe0
    CountyBoardDistricts_2021.csf     10,240 bytes
        sha256 c4db504efb87cc18db0429612b048233770375141b4ecd8dce5c70b9fb55a309

The licence's Credits clause requires indicating the source: the card names
Jo Daviess County GIS on every render (index.html's jo-daviess county-board
entry), and this file plus the guidebook cite licence #008382 and the Kratcha
authorization.

WHAT THE FILE CARRIES, measured before anything was written. 17 polygon
records, one per district, CtyBrdDist "DISTRICT 01".."DISTRICT 17" each
exactly once, every one single-part with no holes. CtyBrdMemb is DECLARED AND
EMPTY on every row — it is read nowhere and asserted empty below, because
member data comes from the county's own board page weekly
(build_jodaviess_board_roster.py), never from a static column that would rot.
Projection per the .prj: NAD83 / StatePlane Illinois West FIPS 1202 in US
survey feet (EPSG:3436), reprojected here with pyproj (the McDonough/Ogle
rule: the app does point-in-polygon in degrees, and civic boundaries are not
the place to debug hand-rolled projection math).

IT PROVES ITSELF AGAINST TIGER AND ITSELF. At full precision the 17 districts
tile 99.93% of TIGER's Jo Daviess County with a worst pairwise overlap of
0.3 m^2 — properly edge-matched, the Menard class. Simplification is
topology-aware mapshaper (pinned, the repo's tool for exactly this), with a
-clean pass either side so shared edges stay shared; the measured cost is a
median boundary displacement of ~0.5 m (p95 ~7 m, max ~54 m) at interval=25 m,
and the floors below fail the build if a rebuild ever does worse. A 2,000-point
random sample must classify identically against the full-precision and shipped
geometries, the union must still cover the county, and every district's
representative point must land in exactly its own feature under the app's own
even-odd test.

THIS IS A RARE OPERATOR STEP (pyshp + pyproj + shapely + requests, plus
Node for the pinned mapshaper; every heavy import is function-local — the
De Witt seam — so the weekly roster workflow can import this module's
CONSTANTS for a constant's cost). Re-run only if the county reapportions
(next due after the 2030 census) and a fresh licensed export is obtained;
point --source (or JODAVIESS_SOURCE_DIR) at the offline directory holding the
five components. Output is deterministic — same input bytes, same pinned
tools, same output — so --check is a byte compare.

Usage:
    python3 scripts/build_jodaviess_board_districts.py --source <dir>
    python3 scripts/build_jodaviess_board_districts.py --source <dir> --check
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "jo-daviess-county-board-districts.json")
OUTLINE_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                            "jo-daviess-county-outline.json")

SHAPE_STEM = "CountyBoardDistricts_2021"
# sha256 of the five components of the licensed 2026-08-17 delivery (also in
# the module docstring with byte sizes). A component that hashes differently is
# a DIFFERENT DELIVERY: re-read the licence posture and re-measure before
# updating these — never update them to make a build pass.
EXPECTED_SHA256 = {
    ".shp": "a47b838f0a545cf40c9c03db8ea3b34d11f4fa07b941ff5d46a2f48326cc69e3",
    ".shx": "d928769c1c6ab1df3e972f36f05174ad7364331ed173cb31e305e807f7cf15f6",
    ".dbf": "5d37eb35509771713a208ff5160ff03816dc6e95c98aa1674df940262c2161ca",
    ".prj": "fc369c037a014a9705729aecf012c2434432c2e6020b6ab91598cc34c156dfe0",
    ".csf": "c4db504efb87cc18db0429612b048233770375141b4ecd8dce5c70b9fb55a309",
}

SOURCE_LABEL = ("Jo Daviess County GIS board-district shapefile "
                "(CountyBoardDistricts_2021), licensed under Jo Daviess County "
                "GIS Digital Data License Agreement #008382 and displayed with "
                "the written authorization of IT/GIS Director Joe Kratcha "
                "(e-mail of 2026-08-17); delivered by GIS Technician Diane "
                "LaScala by e-mail 2026-08-17")
BOARD_URL = "https://www.jodaviesscountyil.gov/1199/County-Board"

# The roster builder imports these two constants as its own seat/count guard —
# keep this module import-light (heavy imports live inside functions).
EXPECTED_DISTRICTS = 17
DISTRICT_FIELD = "CtyBrdDist"

SOURCE_EPSG = "EPSG:3436"       # NAD83 / Illinois West (ftUS), per the .prj
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output
SIMPLIFY_INTERVAL_M = 25         # same order as the metro outline's tolerance
COORD_PRECISION = "0.000001"

# Accuracy floors — each is this build's own first-ship measurement with room
# to wobble; a large miss means a different export or a broken transform, and
# nothing ships until a human re-measures.
MIN_RAW_COVERAGE = 99.85         # measured 99.9327 (full precision vs TIGER)
MAX_RAW_PAIR_M2 = 50.0           # measured 0.3
MIN_COVERAGE = 99.85             # measured 99.9335 (shipped vs TIGER)
MAX_PAIR_M2 = 100.0              # measured 0.0
MAX_DISP_MEDIAN_M = 5.0          # measured 0.5
MAX_DISP_MAX_M = 120.0           # measured 54.1
MAX_OUTLINE_SYMDIFF_PCT = 0.25   # measured 0.125 (vs the shipped TIGER outline)
SAMPLE_POINTS = 2000             # random-point agreement, seeded
MAX_SAMPLE_MISMATCH = 2          # measured 0
COUNTY_FIPS = "085"

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")


fail = make_fail("jodaviess-districts")


def need(name):
    try:
        return __import__(name)
    except ImportError:
        fail("%s is required: pip install -c scripts/requirements.txt "
             "pyshp pyproj shapely requests" % name)


def verify_source(source_dir):
    """Every component present and byte-identical to the licensed delivery."""
    stems = {}
    for ext, want in sorted(EXPECTED_SHA256.items()):
        path = os.path.join(source_dir, SHAPE_STEM + ext)
        if not os.path.exists(path):
            fail("missing source component %s — the licensed shapefile is "
                 "retained OFFLINE (operator's Drive + session archive; the "
                 "licence's redistribution clause is why it is not in this "
                 "repo). Point --source at the directory holding all five "
                 "components." % (SHAPE_STEM + ext))
        with open(path, "rb") as handle:
            got = hashlib.sha256(handle.read()).hexdigest()
        if got != want:
            fail("%s hashes %s, the licensed 2026-08-17 delivery is %s — this "
                 "is a DIFFERENT export. Re-read the licence posture and the "
                 "tiling measurements before updating EXPECTED_SHA256; never "
                 "update the fingerprints just to make a build pass."
                 % (SHAPE_STEM + ext, got, want))
        stems[ext] = path
    return stems


def read_districts(source_dir):
    """district number ("1".."17") -> WGS84 shapely geometry."""
    shapefile = need("shapefile")
    pyproj = need("pyproj")
    need("shapely")
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    reader = shapefile.Reader(os.path.join(source_dir, SHAPE_STEM))
    if reader.shapeType != 5:
        fail("shape type is %d, expected 5 (Polygon)" % reader.shapeType)
    records = list(zip(reader.records(), reader.shapes()))
    if len(records) != EXPECTED_DISTRICTS:
        fail("the export carries %d records, expected exactly %d"
             % (len(records), EXPECTED_DISTRICTS))

    transform = pyproj.Transformer.from_crs(SOURCE_EPSG, "EPSG:4326",
                                            always_xy=True)
    geoms = {}
    for rec, shp in records:
        label = (rec[DISTRICT_FIELD] or "").strip()
        m = re.fullmatch(r"DISTRICT\s+(\d{2})", label)
        if not m:
            fail("record %r does not match the 'DISTRICT NN' pattern" % label)
        num = str(int(m.group(1)))
        if num in geoms:
            fail("district %s appears twice" % num)
        member_col = (rec["CtyBrdMemb"] or "").strip()
        if member_col:
            fail("CtyBrdMemb is no longer empty (district %s carries %r). "
                 "That column was declared-and-empty in the licensed delivery "
                 "and is read NOWHERE — member data comes from the county's "
                 "board page weekly (build_jodaviess_board_roster.py). A "
                 "populated column means a different export; re-measure before "
                 "trusting any of it." % (num, member_col))
        # Ring nesting by CONTAINMENT, not winding — the rule this project
        # settled on after winding collapsed Emmet in the McDonough build.
        starts = list(shp.parts) + [len(shp.points)]
        rings = []
        for i in range(len(shp.parts)):
            pts = shp.points[starts[i]:starts[i + 1]]
            lon, lat = transform.transform([p[0] for p in pts],
                                           [p[1] for p in pts])
            ring = list(zip(lon, lat))
            if len(ring) >= 4:
                rings.append(ring)
        if not rings:
            fail("district %s has no usable rings" % num)
        polys = [Polygon(r) for r in rings]
        polys = [p if p.is_valid else p.buffer(0) for p in polys]
        outers, holes = [], []
        for i, poly in enumerate(polys):
            if any(j != i and polys[j].contains(poly.representative_point())
                   for j in range(len(polys))):
                holes.append(poly)
            else:
                outers.append(poly)
        built = []
        for outer in outers:
            mine = [h.exterior.coords for h in holes
                    if outer.contains(h.representative_point())]
            geom = Polygon(outer.exterior.coords, mine)
            built.append(geom if geom.is_valid else geom.buffer(0))
        geoms[num] = unary_union(built)

    expected = {str(n) for n in range(1, EXPECTED_DISTRICTS + 1)}
    if set(geoms) != expected:
        fail("districts are %s — expected exactly 1..%d"
             % (sorted(geoms, key=int), EXPECTED_DISTRICTS))
    return geoms


def fetch_tiger_county():
    requests = need("requests")
    from shapely.geometry import shape
    resp = requests.get(TIGERWEB, params={
        "where": "STATE='17' AND COUNTY='%s'" % COUNTY_FIPS,
        "outFields": "NAME,GEOID", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson"},
        headers={"User-Agent": "districtry jodaviess builder (+https://districtry.com/il/)"},
        timeout=180)
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != 1:
        fail("TIGERweb returned %d features for Jo Daviess County" % len(feats))
    geom = shape(feats[0]["geometry"])
    return geom if geom.is_valid else geom.buffer(0)


def metres2_factor(lat):
    kx = math.cos(math.radians(lat))
    return (111320.0 * kx) * 111320.0


def tiling_stats(geoms, county):
    from shapely.ops import unary_union
    union = unary_union(list(geoms.values()))
    m2 = metres2_factor((union.bounds[1] + union.bounds[3]) / 2.0)
    coverage = union.intersection(county).area / county.area * 100.0
    names = sorted(geoms, key=int)
    worst, worst_pair = 0.0, None
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = geoms[names[i]].intersection(geoms[names[j]]).area
            if a > worst:
                worst, worst_pair = a, (names[i], names[j])
    return union, coverage, worst * m2, worst_pair


def run_mapshaper(full_geojson, out_path):
    """Topology-aware simplification: -clean either side of the simplify so
    the county's edge-matched borders stay shared arcs (without the first
    -clean, the source's ~280 hairline slivers pin vertices and the file
    barely shrinks; without the last, the simplify's own slivers ship)."""
    subprocess.run(
        ["npx", "-y", MAPSHAPER, full_geojson,
         "-clean",
         "-simplify", "visvalingam", "keep-shapes",
         "interval=%d" % SIMPLIFY_INTERVAL_M,
         "-clean",
         "-o", "precision=" + COORD_PRECISION, "format=geojson", "force",
         out_path],
        check=True, cwd=REPO_ROOT)


def rings_of_geometry(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    return [r for poly in geometry["coordinates"] for r in poly]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.environ.get("JODAVIESS_SOURCE_DIR"),
                    help="directory holding the five CountyBoardDistricts_2021 "
                         "components (offline; see the module docstring)")
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and byte-compare the shipped file; "
                         "writes nothing")
    args = ap.parse_args()
    if not args.source:
        fail("no source directory. The licensed shapefile is retained OFFLINE "
             "(operator's Drive + session archive) because licence #008382's "
             "redistribution clause covers the raw dataset; pass --source or "
             "set JODAVIESS_SOURCE_DIR to its location. This is a rare "
             "operator step — the shipped data/app file is the display copy "
             "Kratcha's 2026-08-17 authorization covers.")

    verify_source(args.source)
    need("shapely")  # fail early, before any network work
    from shapely.geometry import Point, mapping, shape
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_metro_outline import point_in_rings  # shared even-odd test

    geoms = read_districts(args.source)
    county = fetch_tiger_county()

    # ---- full-precision proof: the export tiles TIGER's county -------------
    _, raw_cov, raw_pair_m2, raw_pair = tiling_stats(geoms, county)
    if raw_cov < MIN_RAW_COVERAGE:
        fail("full-precision districts cover %.4f%% of TIGER's Jo Daviess "
             "County (floor %.2f%%) — wrong projection or a different county"
             % (raw_cov, MIN_RAW_COVERAGE))
    if raw_pair_m2 > MAX_RAW_PAIR_M2:
        fail("full-precision districts %s overlap by %.1f m2 (max %.1f) — the "
             "export is no longer edge-matched; re-measure before shipping"
             % (raw_pair, raw_pair_m2, MAX_RAW_PAIR_M2))

    # ---- simplify (topology-aware, pinned mapshaper) -----------------------
    with tempfile.TemporaryDirectory() as tmp:
        full_path = os.path.join(tmp, "full.geojson")
        simp_path = os.path.join(tmp, "simplified.geojson")
        feats = []
        for num in sorted(geoms, key=int):
            feats.append({"type": "Feature",
                          "properties": {"district": num,
                                         "name": "District %s" % num},
                          "geometry": mapping(geoms[num])})
        with open(full_path, "w", encoding="utf-8") as handle:
            json.dump({"type": "FeatureCollection", "features": feats}, handle)
        run_mapshaper(full_path, simp_path)
        with open(simp_path, encoding="utf-8") as handle:
            simplified = json.load(handle)

    feats = simplified.get("features") or []
    if len(feats) != EXPECTED_DISTRICTS:
        fail("simplification left %d features, expected %d"
             % (len(feats), EXPECTED_DISTRICTS))
    simp = {}
    for f in feats:
        num = f["properties"]["district"]
        geom = shape(f["geometry"])
        simp[num] = geom if geom.is_valid else geom.buffer(0)
    if set(simp) != set(geoms):
        fail("districts changed identity during simplification")

    # ---- shipped-quality floors -------------------------------------------
    union, coverage, pair_m2, pair = tiling_stats(simp, county)
    if coverage < MIN_COVERAGE:
        fail("shipped districts cover %.4f%% of the county (floor %.2f%%)"
             % (coverage, MIN_COVERAGE))
    if pair_m2 > MAX_PAIR_M2:
        fail("shipped districts %s overlap by %.1f m2 (max %.1f)"
             % (pair, pair_m2, MAX_PAIR_M2))

    disps = []
    for num in sorted(geoms, key=int):
        full_b = geoms[num].boundary
        simp_b = simp[num].boundary
        length = full_b.length
        for i in range(120):
            p = full_b.interpolate(length * i / 120.0)
            disps.append(simp_b.distance(p) * 111320.0)
    disps.sort()
    disp_median = disps[len(disps) // 2]
    disp_max = disps[-1]
    if disp_median > MAX_DISP_MEDIAN_M or disp_max > MAX_DISP_MAX_M:
        fail("simplification moved the boundary median %.1f m / max %.1f m "
             "(floors %.1f / %.1f) — the tolerance or the fabric changed"
             % (disp_median, disp_max, MAX_DISP_MEDIAN_M, MAX_DISP_MAX_M))

    import random
    rng = random.Random(2024)
    minx, miny, maxx, maxy = county.bounds
    mismatches = 0
    for _ in range(SAMPLE_POINTS):
        p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        full_hits = sorted(n for n, g in geoms.items() if g.contains(p))
        simp_hits = sorted(n for n, g in simp.items() if g.contains(p))
        if len(simp_hits) > 1:
            fail("point (%.5f, %.5f) lands in districts %s of the shipped "
                 "geometry — districts must be disjoint" % (p.y, p.x, simp_hits))
        if full_hits != simp_hits:
            mismatches += 1
    if mismatches > MAX_SAMPLE_MISMATCH:
        fail("%d of %d sample points classify differently before and after "
             "simplification (max %d)"
             % (mismatches, SAMPLE_POINTS, MAX_SAMPLE_MISMATCH))

    with open(OUTLINE_PATH, encoding="utf-8") as handle:
        outline_gj = json.load(handle)
    from shapely.ops import unary_union
    outline = unary_union([shape(f["geometry"])
                           for f in outline_gj["features"]])
    outline_pct = union.symmetric_difference(outline).area / outline.area * 100
    if outline_pct > MAX_OUTLINE_SYMDIFF_PCT:
        fail("the district union differs from the shipped coverage outline by "
             "%.3f%% (max %.2f%%) — the coverage test and the card would "
             "disagree about where the county is"
             % (outline_pct, MAX_OUTLINE_SYMDIFF_PCT))

    # ---- emit (deterministic), then the app's own even-odd test ------------
    out_features = []
    for num in sorted(simp, key=int):
        geo = mapping(simp[num])
        out_features.append({
            "type": "Feature",
            "properties": {"district": num, "name": "District %s" % num},
            "geometry": {"type": geo["type"],
                         "coordinates": geo["coordinates"]},
        })
    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL,
            "license": ("Jo Daviess County GIS Digital Data License Agreement "
                        "#008382 (2026-08-17); display authorized in writing "
                        "by IT/GIS Director Joe Kratcha, 2026-08-17, and "
                        "confirmed for districtry.com by the same office "
                        "2026-08-31. The raw shapefile is retained offline "
                        "and is not redistributed."),
            "boardUrl": BOARD_URL,
            "note": ("17 single-member districts, the county's own adopted "
                     "2021 lines (effective December 1, 2022). Simplified for "
                     "display (median boundary movement ~0.5 m, max ~54 m); "
                     "the full-precision export tiles TIGER's county at "
                     "99.93% with 0.3 m2 worst overlap."),
        },
        "features": out_features,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"

    for num in sorted(simp, key=int):
        probe = simp[num].representative_point()
        hits = [f["properties"]["district"] for f in out_features
                if point_in_rings(probe.y, probe.x,
                                  rings_of_geometry(f["geometry"]))]
        if hits != [num]:
            fail("district %s's representative point lands in %s under the "
                 "app's even-odd test" % (num, hits or "no district"))

    print("jodaviess-districts: 17 districts reprojected %s -> WGS84"
          % SOURCE_EPSG)
    print("  full precision: %.4f%% of TIGER county covered; worst pair "
          "overlap %.1f m2" % (raw_cov, raw_pair_m2))
    print("  shipped: %.4f%% covered; worst pair %.1f m2; boundary moved "
          "median %.1f m / max %.1f m; %d/%d sample points agree; %.3f%% "
          "sym-diff vs the coverage outline"
          % (coverage, pair_m2, disp_median, disp_max,
             SAMPLE_POINTS - mismatches, SAMPLE_POINTS, outline_pct))

    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s is missing — run this script without --check"
                 % os.path.relpath(OUT_PATH, REPO_ROOT))
        with open(OUT_PATH, encoding="utf-8") as handle:
            if handle.read() != body:
                fail("%s differs from a fresh build of the licensed source"
                     % os.path.relpath(OUT_PATH, REPO_ROOT))
        print("  --check OK — %s matches a fresh build (%s bytes)"
              % (os.path.relpath(OUT_PATH, REPO_ROOT), "{:,}".format(len(body))))
        return
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(body)
    print("  wrote %s (%s bytes)"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), "{:,}".format(len(body))))


if __name__ == "__main__":
    main()
