#!/usr/bin/env python3
"""
Sullivan County's fire and library districts — New York's special-district tier
==============================================================================
Writes three files:

  ny/data/app/sullivan-fire-districts.json      45 fire districts
  ny/data/app/sullivan-library-districts.json    2 library districts
  ny/data/app/sullivan-county-outline.json      the dispatch entry's coverage test

WHY THIS COUNTY, AND WHY THE COUNTY'S OWN SERVER. New York State's own map
server publishes no statutory special district at all (measured 2026-10-01 and
recorded in docs/DATA_LAYER_GUIDEBOOK.md), so this tier cannot be reached
statewide. Sullivan County's GIS host publishes fourteen district layers in one
service, and the county WEBSITE refuses this project while gis.sullivanny.us
answers freely and serves no robots.txt at all (HTTP 404, allow all, read
through scripts/robots_policy.py with the client this builder sends). That is
the Knox pattern: a county is not blocked because its website is.

WHAT SHIPS AND WHAT DOES NOT. The service carries agricultural, ambulance,
drainage, garbage, gas, historic, light, parking, road, sewer and water
districts beside these two. Those are tax-map assessment districts — a town
improvement district governed by the town board, with no body of its own — so
they are not governments and are not shipped. Fire districts and library
districts are, because New York law creates each as a district corporation with
its own elected board (Town Law article 11; Education Law article 5).

THE TYPE IS NOT DERIVED. The `Subtype` column calls all 58 fire rows "Fire
District", including the five whose own name reads "Fire Protection District" —
and in New York those are different things: a fire district elects five
commissioners, while a fire protection district is a town contract area with no
board of its own. This builder ships the district's NAME exactly as the county's
register publishes it and derives nothing from it. The card states the general
rule and names nobody, because nothing published names a Sullivan fire
commissioner or library trustee (the roster gap is recorded as
ny-special-district-officials).

THE PIECES ARE PER-MUNICIPALITY AND ARE DISSOLVED. The register publishes one
row per (district, municipality) pair — 58 rows for 45 fire districts, 4 for 2
library districts, keyed by a unique ARLM number each — because it is derived
from the county's tax maps. Eleven fire districts and one library district span
more than one municipality. Drawn as published they would carry an internal line
through each district, so the pieces are unioned by name before anything else.
The union is shapely's and not mapshaper's: three source pieces are
self-intersecting (Swan Lake, Bloomingburg, Mamakating Library), which
`-dissolve2` answers by destroying two whole districts' geometry (Fallsburg Line,
4.7 km2, and Howells, 6.7 km2 — real districts, not stubs), and `-clean` answers
by dropping three features and 629 slivers and reporting 26 intersections it
could not repair. Both were measured before shapely was chosen.

THE FIRE DISTRICTS TILE THE COUNTY, which is the measurement that makes this
layer worth drawing: their union is 100.03% of the area of the county as
ny-counties.json draws it, so a reader clicking anywhere in Sullivan is in a fire
district. The 0.03% and the handful of in-county points in no district are the
two publishers' rim — NYS ITS draws Sullivan's boundary and Sullivan County draws
its own — the same rim build_tompkins_legislature.py measures and names. Library
districts cover 22% of the county, which is correct rather than a gap: most
Sullivan towns have no library district.

THE OVERLAPS ARE DIGITISATION SLIVERS, MEASURED NOT ASSUMED. 27 pairs of
distinct fire districts intersect, totalling 0.0026% of the union, and the worst
pair overlaps by 0.063% of the smaller district (Grahamsville and Woodbourne).
That is two independently drawn tax-map edges, not a district line running
through another district. OVERLAP_MAX_PCT is the ceiling that stops it growing
unnoticed.

SIMPLIFICATION — interval 10 m, Douglas-Peucker, MEASURED not inherited.
Visvalingam thresholds triangle area, which does not bound how far the drawn line
strays; DP thresholds perpendicular deviation, which is what a reader sees. The
source's own step is a median 9.633 m over its 60,223 segments, so 10 m is about
one step — the basis the Illinois legislative rebuild and this instance's
Tompkins build both used at their own medians. Measured on the fetch this builder
makes: 2,478,077 bytes and 60,303 vertices at source become 232,641 bytes
(63,603 gzipped) at interval 10, and of 40,000 point answers compared against the
unsimplified source 17 differ (0.043%), every one of them on a boundary. The
sweep at 8, 10, 15 and 25 m is in this file's first commit and in the guidebook;
nothing is dropped at any of them.

THE COVERAGE OUTLINE is sliced from the shipped ny-counties.json rather than
fetched, so a point the `county` card calls Sullivan is a point this layer is
asked about. Fetching a third drawing of the same county would let the two
answers disagree.

WHAT WAS TRIED AND REJECTED. New York State publishes a Fire Department
Directory (data.ny.gov qfsu-zcpv, DHSES) naming 1,773 departments with an
address and a telephone number, 41 of them in Sullivan. It is NOT joined to these
districts. A department is the operational company and a district is the
governing body; the two are different things, and the join is not clean anyway —
33 of 45 district names match a department name exactly and the other 12 are
near-misses (FORESTBURG against Forestburgh, LUMBERLAND against Town Of
Lumberland, SWAN LAKE HOSE COMPANY NO 1 against Swan Lake). A fuzzy join would
put a telephone number somebody might actually ring on a card that guessed it.

Usage:
    python3 ny/scripts/build_sullivan_special_districts.py          # fetch + build (network, npx, shapely)
    python3 ny/scripts/build_sullivan_special_districts.py --sweep  # print the interval sweep
    python3 ny/scripts/build_sullivan_special_districts.py --check  # CI gate (offline, stdlib)

--check IS OFFLINE AND CANNOT SEE THE SOURCE, so it cannot re-measure the chord
stray or the tiling against the county's own drawing. It re-derives everything
that lives in the shipped bytes: the district set and its two kinds, that no
feature has null or empty geometry, that each district contains a point of its
own, that the fire districts still tile the shipped county polygon, that their
overlaps are still slivers, and that the coverage outline is still the slice of
ny-counties.json it claims to be.
"""
import argparse
import collections
import json
import os
import random
import shutil
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
ROOT = os.path.dirname(INSTANCE)
APP = os.path.join(INSTANCE, "data", "app")
OUT_PATHS = {"fire": os.path.join(APP, "sullivan-fire-districts.json"),
             "library": os.path.join(APP, "sullivan-library-districts.json")}
OUTLINE_PATH = os.path.join(APP, "sullivan-county-outline.json")
COUNTIES_PATH = os.path.join(APP, "ny-counties.json")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_ny_civil_boundaries as CIVIL      # noqa: E402  geometry primitives
from scraper_common import UA_ROSTER_BOT, require_robots_once   # noqa: E402

# The client this builder crawls with. The host's policy is read with this exact
# token and nothing richer: `user-agent-measurements.json` records
# gis.sullivanny.us serving it, and reading a policy with a stronger client than
# the crawl is measuring the wrong thing.
UA = UA_ROSTER_BOT

HOST = "https://gis.sullivanny.us"
SERVICE = HOST + "/arcgis/rest/services/Special_Districts/MapServer"
CREDIT = "Sullivan County Real Property Services and Sullivan County ITS: GIS Program."
LAYERS = (("fire", 7, "Fire Districts"), ("library", 11, "Library Districts"))
MAPSHAPER = "mapshaper@0.6.102"               # the fleet pin, for reproducible output
PRECISION = "0.000001"
INTERVAL_M = 10
SWEEP = (8, 10, 15, 25)

# Measured on the 2026-10-01 fetch; each is a ceiling, not the measurement.
EXPECT_FIRE = 45                 # distinct fire district names, 58 register rows
EXPECT_LIBRARY = 2               # distinct library district names, 4 register rows
ANSWER_SAMPLES = 20000
ANSWER_SEED = 20261001
ANSWER_DIFF_MAX_PCT = 0.25       # measured 0.043% at interval 10
TILING_GAP_MAX_PCT = 0.50        # measured 11 of 20,000 (0.055%), the publishers' rim
OVERLAP_MAX_PCT = 0.50           # measured worst 0.063% of the smaller district
OVERLAP_POINTS_MAX_PCT = 0.10    # measured 2 of 20,000 (0.010%)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def require_robots():
    """Read the policy with the client this builder sends, before the first fetch
    of the host, through the one shared seam rather than a spelling of our own."""
    require_robots_once(SERVICE, UA, label="sullivan-special-districts")


def fetch_pieces():
    """The register's own rows, one per (district, municipality) pair."""
    pieces = []
    for kind, layer_id, expect_name in LAYERS:
        meta = fetch("%s/%d?f=json" % (SERVICE, layer_id))
        if meta.get("name") != expect_name:
            raise SystemExit("sullivan-special-districts: layer %d is now %r, not %r — the "
                             "service has been renumbered" % (layer_id, meta.get("name"),
                                                              expect_name))
        geo = fetch("%s/%d/query?where=1%%3D1&outFields=Name,ARLMNumber,Municipality,Subtype,"
                    "RetiredByRecord&returnGeometry=true&outSR=4326&f=geojson"
                    % (SERVICE, layer_id))
        rows = geo.get("features") or []
        if not rows:
            raise SystemExit("sullivan-special-districts: %s returned no features" % kind)
        for feature in rows:
            props = feature.get("properties") or {}
            # A retired row is not a current district. None has ever appeared;
            # the day one does, a person reads it rather than shipping it.
            if props.get("RetiredByRecord"):
                raise SystemExit("sullivan-special-districts: %r carries RetiredByRecord %r — the "
                                 "register now marks retired districts and this builder has never "
                                 "had to decide what to do with one"
                                 % (props.get("Name"), props.get("RetiredByRecord")))
            name = (props.get("Name") or "").strip()
            if not name:
                raise SystemExit("sullivan-special-districts: a %s row (ARLM %r) publishes no name"
                                 % (kind, props.get("ARLMNumber")))
            pieces.append({"type": "Feature",
                           "properties": {"kind": kind, "name": name,
                                          "arlm": (props.get("ARLMNumber") or "").strip(),
                                          "municipality": (props.get("Municipality") or "").strip()},
                           "geometry": feature.get("geometry")})
    arlm = collections.Counter(p["properties"]["arlm"] for p in pieces)
    doubled = [key for key, n in arlm.items() if n > 1 and key]
    if doubled:
        raise SystemExit("sullivan-special-districts: ARLM number(s) %s appear twice — the key the "
                         "pieces are distinguished by is no longer unique" % ", ".join(sorted(doubled)))
    return pieces


def dissolve(pieces):
    """Union each district's pieces into one shape. shapely, not mapshaper — the
    docstring records what each of mapshaper's two routes did to this input."""
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union
    grouped = collections.OrderedDict()
    for piece in pieces:
        key = (piece["properties"]["kind"], piece["properties"]["name"])
        grouped.setdefault(key, []).append(shape(piece["geometry"]))
    out = []
    for (kind, name), shapes in grouped.items():
        union = unary_union(shapes)
        if not union.is_valid:
            union = union.buffer(0)
        if union.is_empty:
            raise SystemExit("sullivan-special-districts: %r unioned to nothing" % name)
        out.append({"type": "Feature",
                    "properties": {"kind": kind, "name": name},
                    "geometry": mapping(union)})
    return out


def run_mapshaper(src_path, interval, out_dir):
    subprocess.run(["npx", "-y", MAPSHAPER, "-i", src_path,
                    "-simplify", "dp", "keep-shapes", "interval=%d" % interval,
                    "-o", "precision=" + PRECISION, "format=geojson", out_dir],
                   check=True, cwd=ROOT, capture_output=True)
    names = os.listdir(out_dir)
    if len(names) != 1:
        raise SystemExit("sullivan-special-districts: mapshaper wrote %d files, expected 1"
                         % len(names))
    with open(os.path.join(out_dir, names[0]), encoding="utf-8") as fh:
        return json.load(fh)


def simplify(features, interval, tmp):
    os.makedirs(tmp, exist_ok=True)
    src = os.path.join(tmp, "in.json")
    with open(src, "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": features}, fh)
    out_dir = os.path.join(tmp, "out%d" % interval)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    return run_mapshaper(src, interval, out_dir)


def county_polygon():
    with open(COUNTIES_PATH, encoding="utf-8") as fh:
        for feature in json.load(fh)["features"]:
            if (feature["properties"].get("NAME") or "").strip() == "Sullivan":
                return feature
    raise SystemExit("sullivan-special-districts: ny-counties.json has no Sullivan feature")


def in_county_points(county, samples, seed):
    bb = CIVIL._bbox(county["geometry"])
    rng = random.Random(seed)
    points = []
    while len(points) < samples:
        pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
        if CIVIL._point_in_geometry(pt, county["geometry"]):
            points.append(pt)
    return points


def answers(features, kind, points):
    """What each point is told, by district name, for one kind of district."""
    model = [(f["properties"]["name"], f["geometry"], CIVIL._bbox(f["geometry"]))
             for f in features if f["properties"]["kind"] == kind and f["geometry"]]
    out = []
    for pt in points:
        hits = frozenset(name for name, geom, bb in model
                         if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
                         and CIVIL._point_in_geometry(pt, geom))
        out.append(hits)
    return out


def shape_problems(features, points, label):
    """The gates that live in the shipped bytes, so --check runs them too."""
    problems = []
    counts = collections.Counter(f["properties"]["kind"] for f in features)
    if counts.get("fire") != EXPECT_FIRE or counts.get("library") != EXPECT_LIBRARY:
        problems.append("%s: %d fire and %d library districts, expected %d and %d"
                        % (label, counts.get("fire", 0), counts.get("library", 0),
                           EXPECT_FIRE, EXPECT_LIBRARY))
    for feature in features:
        if not feature.get("geometry") or not CIVIL._rings(feature["geometry"]):
            problems.append("%s: %r has no geometry" % (label, feature["properties"].get("name")))
    names = collections.Counter((f["properties"]["kind"], f["properties"]["name"])
                                for f in features)
    doubled = [n for n, c in names.items() if c > 1]
    if doubled:
        problems.append("%s: %s appear(s) twice — the pieces were not dissolved"
                        % (label, ", ".join(sorted(n[1] for n in doubled))))

    fire = answers(features, "fire", points)
    gaps = sum(1 for hits in fire if not hits)
    overlaps = sum(1 for hits in fire if len(hits) > 1)
    gap_pct = 100.0 * gaps / len(points)
    overlap_pct = 100.0 * overlaps / len(points)
    if gap_pct > TILING_GAP_MAX_PCT:
        problems.append("%s: %d of %d in-county points are in no fire district (%.3f%%, past the "
                        "%.2f%% ceiling) — the fire districts no longer tile the county"
                        % (label, gaps, len(points), gap_pct, TILING_GAP_MAX_PCT))
    if overlap_pct > OVERLAP_POINTS_MAX_PCT:
        problems.append("%s: %d of %d in-county points are in TWO fire districts (%.3f%%, past the "
                        "%.2f%% ceiling) — the overlaps are no longer digitisation slivers"
                        % (label, overlaps, len(points), overlap_pct, OVERLAP_POINTS_MAX_PCT))
    return problems, gaps, overlaps


def interior_point_problems(features):
    """Each district must contain a point of its own — a ring that collapsed to a
    line passes every count and answers nobody."""
    problems = []
    for feature in features:
        rings = CIVIL._rings(feature["geometry"])
        bb = CIVIL._bbox(feature["geometry"])
        rng = random.Random(hash(feature["properties"]["name"]) & 0xFFFF)
        found = False
        for _ in range(4000):
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            if CIVIL._point_in_geometry(pt, feature["geometry"]):
                found = True
                break
        if not found and rings:
            problems.append("%r encloses no point this gate could find — it may have collapsed to a "
                            "line" % feature["properties"]["name"])
    return problems


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
        fh.write("\n")


def build():
    require_robots()
    pieces = fetch_pieces()
    districts = dissolve(pieces)
    county = county_polygon()
    points = in_county_points(county, ANSWER_SAMPLES, ANSWER_SEED)

    source_answers = {kind: answers(districts, kind, points) for kind in ("fire", "library")}
    tmp = os.path.join(ROOT, ".sullivan-build")
    built = simplify(districts, INTERVAL_M, tmp)["features"]

    problems, gaps, overlaps = shape_problems(built, points, "built")
    problems.extend(interior_point_problems(built))
    differ = 0
    for kind in ("fire", "library"):
        after = answers(built, kind, points)
        differ += sum(1 for a, b in zip(after, source_answers[kind]) if a != b)
    total = 2 * len(points)
    diff_pct = 100.0 * differ / total
    if diff_pct > ANSWER_DIFF_MAX_PCT:
        problems.append("simplification moved %d of %d point answers (%.3f%%, past the %.2f%% "
                        "ceiling)" % (differ, total, diff_pct, ANSWER_DIFF_MAX_PCT))

    if problems:
        for problem in problems:
            print("sullivan-special-districts: FAIL %s" % problem, file=sys.stderr)
        raise SystemExit(1)

    for kind, path in OUT_PATHS.items():
        write_json(path, {
            "type": "FeatureCollection",
            "_about": ("GENERATED by ny/scripts/build_sullivan_special_districts.py from "
                       + SERVICE + " layer " + str(dict((k, i) for k, i, _ in LAYERS)[kind])
                       + ", credited " + CREDIT
                       + " The register's per-municipality pieces are unioned by district name, "
                       "then simplified with mapshaper dp keep-shapes interval="
                       + str(INTERVAL_M) + " m over BOTH kinds at once, so the two layers' shared "
                       "edges are simplified once. Names are the register's own; nothing about a "
                       "district's type or governing board is derived from them. The service's "
                       "other twelve layers are tax-map assessment districts with no board of "
                       "their own and are not shipped."),
            "features": [{"type": "Feature",
                          "properties": {"name": f["properties"]["name"]},
                          "geometry": f["geometry"]}
                         for f in built if f["properties"]["kind"] == kind],
        })
    write_json(OUTLINE_PATH, {
        "type": "FeatureCollection",
        "_about": ("GENERATED by ny/scripts/build_sullivan_special_districts.py — Sullivan County "
                   "sliced verbatim from ny/data/app/ny-counties.json so this layer's coverage "
                   "test and the county card cannot disagree about where Sullivan is."),
        "features": [{"type": "Feature",
                      "properties": {"NAME": county["properties"]["NAME"],
                                     "FIPS_CODE": county["properties"]["FIPS_CODE"]},
                      "geometry": county["geometry"]}],
    })
    shutil.rmtree(tmp, ignore_errors=True)

    src_verts = sum(len(r) for f in pieces for r in CIVIL._rings(f["geometry"]))
    out_verts = sum(len(r) for f in built for r in CIVIL._rings(f["geometry"]))
    print("sullivan-special-districts: OK %d fire districts (from %d register rows) and %d library "
          "districts (from %d), %d of %d in-county points in no fire district (%.3f%%, the two "
          "publishers' rim), %d in two (%.3f%%, digitisation slivers), simplification moved %d of "
          "%d point answers (%.3f%%)"
          % (EXPECT_FIRE, sum(1 for p in pieces if p["properties"]["kind"] == "fire"),
             EXPECT_LIBRARY, sum(1 for p in pieces if p["properties"]["kind"] == "library"),
             gaps, len(points), 100.0 * gaps / len(points), overlaps,
             100.0 * overlaps / len(points), differ, total, diff_pct))
    for kind, path in OUT_PATHS.items():
        print("sullivan-special-districts: wrote %s (%d bytes)"
              % (os.path.relpath(path, ROOT), os.path.getsize(path)))
    print("sullivan-special-districts: %d vertices shipped, from %d at source; coverage outline %s "
          "(%d bytes)"
          % (out_verts, src_verts, os.path.relpath(OUTLINE_PATH, ROOT),
             os.path.getsize(OUTLINE_PATH)))


def sweep():
    require_robots()
    districts = dissolve(fetch_pieces())
    county = county_polygon()
    points = in_county_points(county, ANSWER_SAMPLES, ANSWER_SEED)
    base = {kind: answers(districts, kind, points) for kind in ("fire", "library")}
    tmp = os.path.join(ROOT, ".sullivan-build")
    print("interval  features  bytes   answers-moved")
    for interval in SWEEP:
        built = simplify(districts, interval, tmp)["features"]
        blob = json.dumps({"type": "FeatureCollection", "features": built},
                          separators=(",", ":")).encode("utf-8")
        differ = sum(sum(1 for a, b in zip(answers(built, kind, points), base[kind]) if a != b)
                     for kind in ("fire", "library"))
        print("%8d  %8d  %6d  %d of %d (%.3f%%)"
              % (interval, len(built), len(blob), differ, 2 * len(points),
                 100.0 * differ / (2 * len(points))))
    shutil.rmtree(tmp, ignore_errors=True)


def check():
    for path in list(OUT_PATHS.values()) + [OUTLINE_PATH, COUNTIES_PATH]:
        if not os.path.exists(path):
            print("sullivan-special-districts: FAIL %s is missing" % os.path.relpath(path, ROOT),
                  file=sys.stderr)
            return 1
    shipped = []
    for kind, path in OUT_PATHS.items():
        with open(path, encoding="utf-8") as fh:
            for feature in json.load(fh)["features"]:
                feature["properties"]["kind"] = kind
                shipped.append(feature)
    county = county_polygon()
    points = in_county_points(county, ANSWER_SAMPLES, ANSWER_SEED)
    problems, gaps, overlaps = shape_problems(shipped, points, "shipped")
    problems.extend(interior_point_problems(shipped))

    with open(OUTLINE_PATH, encoding="utf-8") as fh:
        outline = json.load(fh)["features"]
    if len(outline) != 1:
        problems.append("the coverage outline has %d features, expected 1" % len(outline))
    elif json.dumps(outline[0]["geometry"], sort_keys=True) != \
            json.dumps(county["geometry"], sort_keys=True):
        problems.append("the coverage outline is no longer the Sullivan slice of ny-counties.json "
                        "— the layer and the county card can now disagree about where Sullivan is")

    if problems:
        for problem in problems:
            print("sullivan-special-districts: FAIL %s" % problem, file=sys.stderr)
        return 1
    print("sullivan-special-districts: OK %d districts shipped, %d of %d in-county points in no "
          "fire district (%.3f%%), %d in two (%.3f%%), every district encloses a point of its own, "
          "coverage outline still the ny-counties.json slice"
          % (len(shipped), gaps, len(points), 100.0 * gaps / len(points), overlaps,
             100.0 * overlaps / len(points)))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Build Sullivan County's fire and library districts.")
    ap.add_argument("--check", action="store_true", help="offline CI gate on the shipped files")
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
    raise SystemExit(main(sys.argv[1:]))
