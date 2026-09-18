#!/usr/bin/env python3
"""
Build the pre-simplified New York county boundary file in data/app/ from NYS
ITS, so the app fetches it same-origin (cache-first) instead of downloading
statewide county geometry live on every first toggle.

Statewide, like the Illinois/Wisconsin/Iowa/Michigan county layers: the ny/
instance answers anywhere in the state, so the county layer ships whole -
fetch -> simplify -> validate -> write data/app/ny-counties.json. No clip
step: the served area IS the state.

Source: NYS_Civil_Boundaries/FeatureServer/2 ("Counties"), NYS Office of
Information Technology Services Geospatial Data Services. Service
description read 2026-09-18: "Publication Date: March 2026. Updated as
needed." Host robots.txt answers HTTP 404 on this domain, read as allow-all
by scripts/robots_policy.py.

Fields kept: NAME, FIPS_CODE, NYC, POP2020. The full layer publishes ABBREV,
GNIS_ID, SWIS, NYSP_ZONE, POP1990..POP2020, DOS_LL, DOSLL_DATE, CALC_SQ_MI and
DATEMOD as well; none of those is read by any card, so none of them ships.

The NYC flag is load-bearing and is not a display convenience: it reads
exactly 'Y' on the five boroughs (Bronx 36005, Kings 36047, New York 36061,
Queens 36081, Richmond 36085, measured 2026-09-18) and 'N' on the other 57.
A future county-legislature concept reads this flag to know which 57 counties
elect a Board of Supervisors and to answer nothing inside the five that do
not - so the flag ships even though PR 2 renders no legislature card yet.

The trap this file's own docstring exists to record: the source layer is
EPSG:26918 (NAD83 / UTM 18N) and its polygons are shoreline-clipped. This
script requests outSR=4326, and the resulting county polygons still stop at
the coastline. ny/data/app/metro-outline.json and ny/data/app/ny-state-outline.json
are built from TIGERweb, which is water-inclusive, so this file's county
edges and those two rings DISAGREE at the shoreline BY DESIGN - they are not
the same product measured twice. The outline files answer "is this point in
the coverage wash," which needs to extend past the last shoreline pixel so a
click just offshore still lands inside the state; this file answers "which
county does the card name," which needs to stop at the shoreline so a point
in the water is not attributed to a county whose jurisdiction does not
include it. Do not reconcile the two; ship both as measured.

Simplification is topology-aware mapshaper (Visvalingam, keep-shapes, the
same tool and protocol every other boundary builder here uses), pinned to
mapshaper@0.6.102 for reproducible output. The result is validated against
the pre-simplification fetch on the project's 2,000-random-point
point-in-county protocol before anything is written; if validation fails,
nothing is written.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ny/scripts/build_ny_counties.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
SOURCE_DIR = os.path.join(REPO_ROOT, "data", "source")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
COUNTIES_LAYER = (
    "https://gisservices.its.ny.gov/arcgis/rest/services/"
    "NYS_Civil_Boundaries/FeatureServer/2"
)

FIELDS = ["NAME", "FIPS_CODE", "NYC", "POP2020"]
OUT_FILE = "ny-counties.json"
SOURCE_SNAPSHOT = "ny-counties-source-2026-09-18.geojson"
SIMPLIFY = "15%"  # matches ny/scripts/build_embedded_boundaries.py's boundary retain rate
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m, the precision the app requests live
MIN_FEATURES = 62  # every New York county, measured 2026-09-18
EXPECTED_NYC_Y = 5  # Bronx, Kings, New York, Queens, Richmond
VALIDATION_KEY = "FIPS_CODE"


def fetch_counties():
    """Fetch every New York county feature as GeoJSON in EPSG:4326. Uses curl
    so it works through an HTTPS proxy (as in the Claude Code sandbox)."""
    url = (
        COUNTIES_LAYER + "/query"
        "?where=1%3D1"
        "&outFields=" + ",".join(FIELDS) +
        "&outSR=4326&geometryPrecision=6&f=geojson"
    )
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300", url],
        check=True, capture_output=True,
    ).stdout
    geo = json.loads(out)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("NYS_Civil_Boundaries Counties layer returned no features")
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("NYS_Civil_Boundaries Counties layer hit the transfer cap - needs paging")
    return geo


def run_mapshaper(source_path, simplify, out_path):
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-simplify", "visvalingam", "keep-shapes", simplify,
            "-o", "precision=" + PRECISION, "format=geojson", out_path,
        ],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon mirroring index.html's even-odd test (so validation
#     agrees with what the app computes at runtime) - fleet-standard copy ---
def _point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(pt, geom):
    if geom["type"] == "Polygon":
        inside = False
        for ring in geom["coordinates"]:
            if _point_in_ring(pt, ring):
                inside = not inside
        return inside
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            inside = False
            for ring in poly:
                if _point_in_ring(pt, ring):
                    inside = not inside
            if inside:
                return True
    return False


def _bbox(geom):
    b = [1e9, 1e9, -1e9, -1e9]

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            b[0], b[1] = min(b[0], c[0]), min(b[1], c[1])
            b[2], b[3] = max(b[2], c[0]), max(b[3], c[1])
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    return b


def _model(features, key_prop):
    return [(f["properties"].get(key_prop), f["geometry"], _bbox(f["geometry"])) for f in features]


def _districts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def _state_bbox(features):
    """Measure the state envelope from the fetched geometry itself, so
    validation samples the extent this build actually saw rather than a
    number copied from another document."""
    b = [1e9, 1e9, -1e9, -1e9]
    for f in features:
        fb = _bbox(f["geometry"])
        b[0], b[1] = min(b[0], fb[0]), min(b[1], fb[1])
        b[2], b[3] = max(b[2], fb[2]), max(b[3], fb[3])
    return {"minLng": b[0], "minLat": b[1], "maxLng": b[2], "maxLat": b[3]}


def validate(source_features, result_features, key_prop, samples=2000, seed=2024):
    """Refuse the build unless simplification preserves county coverage over
    the state envelope vs the full-precision fetch - the fleet's 2,000
    uniform-random-point protocol. Any point landing in two result counties
    is a topology break."""
    state_bbox = _state_bbox(source_features)
    src = _model(source_features, key_prop)
    new = _model(result_features, key_prop)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(state_bbox["minLng"], state_bbox["maxLng"]),
              rng.uniform(state_bbox["minLat"], state_bbox["maxLat"]))
        s_hits = _districts_at(new, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = _districts_at(src, pt)
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    if overlaps > 0:
        return False, "topology broken: %d/%d points fell in >1 county" % (overlaps, samples), state_bbox
    if pct < 99.5:
        return False, "point-in-county agreement only %.2f%% (need >= 99.5%%)" % pct, state_bbox
    return True, "%d/%d (%.2f%%) agreement over the measured state envelope, 0 overlaps" % (agree, samples, pct), state_bbox


def main():
    source = fetch_counties()
    feats = source["features"]

    n = len(feats)
    if n != MIN_FEATURES:
        raise RuntimeError(
            "ny-counties: %d features fetched (expected exactly %d New York "
            "counties, measured 2026-09-18) - refusing to write" % (n, MIN_FEATURES)
        )

    nyc_y = [f["properties"]["NAME"] for f in feats if f["properties"].get("NYC") == "Y"]
    if len(nyc_y) != EXPECTED_NYC_Y:
        raise RuntimeError(
            "ny-counties: NYC='Y' on %d counties (expected exactly %d - the "
            "five boroughs) - refusing to write: %s" % (len(nyc_y), EXPECTED_NYC_Y, nyc_y)
        )

    bad_fips = [
        f["properties"].get("FIPS_CODE") for f in feats
        if not (isinstance(f["properties"].get("FIPS_CODE"), str)
                and len(f["properties"]["FIPS_CODE"]) == 5
                and f["properties"]["FIPS_CODE"].startswith("36"))
    ]
    if bad_fips:
        raise RuntimeError(
            "ny-counties: %d FIPS_CODE values are not 5 digits starting '36' "
            "- refusing to write: %s" % (len(bad_fips), bad_fips)
        )

    os.makedirs(SOURCE_DIR, exist_ok=True)
    with open(os.path.join(SOURCE_DIR, SOURCE_SNAPSHOT), "w") as f:
        json.dump(source, f)

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "counties-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, "counties.geojson")
        run_mapshaper(src_path, SIMPLIFY, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n2 = len(simplified["features"])
    if n2 != MIN_FEATURES:
        raise RuntimeError(
            "ny-counties: %d features after simplify (expected exactly %d) "
            "- refusing to write" % (n2, MIN_FEATURES)
        )

    ok, msg, state_bbox = validate(feats, simplified["features"], VALIDATION_KEY)
    if not ok:
        raise RuntimeError("ny-counties validation failed: %s" % msg)

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("ny-counties round-trip mismatch before writing")

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)
    with open(out_path, "w") as f:
        f.write(compact)

    print(
        "ny-counties -> data/app/%s: %d features (statewide); state envelope "
        "measured lng %.3f..%.3f lat %.3f..%.3f; %s; %d bytes (%s retain, "
        "%s precision)"
        % (OUT_FILE, n2, state_bbox["minLng"], state_bbox["maxLng"],
           state_bbox["minLat"], state_bbox["maxLat"], msg, len(compact),
           SIMPLIFY, PRECISION),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
