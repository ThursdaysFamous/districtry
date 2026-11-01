#!/usr/bin/env python3
"""
Build the pre-simplified Virginia county boundary file in data/app/ from
Census TIGERweb, so the app fetches it same-origin (cache-first) instead of
downloading full statewide geometry live on every first toggle.

Statewide, like the Illinois reference and every newer state: Virginia's
instance answers anywhere in the state, so the county layer ships whole —
fetch -> simplify -> validate -> write data/app/state-counties.json. No clip
step: the served area IS the state. The file holds 133 features: Virginia's
95 counties and its 38 independent cities, which belong to no county and
which the Census Bureau files as county equivalents (GEOIDs 51510 to 51840).

This is an occasional OPERATOR step, not weekly CI — county lines change
essentially never; re-run only if TIGERweb corrects a boundary.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M WITH AN 8 M FIDELITY CEILING, WHICH
IS ADAM'S CHOICE ("Finest", 2026-10-15) FOR THE COUNTY FILES OF THE NEWER
STATES. Mississippi's builder, which Missouri's and this one were copied from,
records the measurement behind it: Visvalingam thresholds triangle AREA, which
does not bound how far the drawn line strays, and a coarser Douglas-Peucker
interval bounds the stray while answering more ground with the neighbouring
county. Virginia's run prints its own worst stray against the ceiling on every
build.

The ceiling is checked on every build by scripts/boundary_fidelity.py, the
module the other newer states' county builders import, which measures every
source vertex's distance to the drawn line, because measuring the other way
answers ~0 by construction.

Prerequisites: requests, and Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 va/scripts/build_state_counties.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
sys.path.append(os.path.join(os.path.dirname(REPO_ROOT), "scripts"))
import boundary_fidelity  # noqa: E402  (shared and stdlib only; appended, so it shadows nothing here)
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1"
VA_FIPS = "51"

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = blb.STATE_BBOX

FIELDS = ["NAME", "BASENAME", "GEOID", "STATE", "COUNTY"]
OUT_FILE = "state-counties.json"
# Douglas-Peucker interval in METRES (keep-shapes). The ceiling is pinned
# with headroom rather than recomputed: a ceiling derived from the build it
# checks can never fail. The median source step is printed beside it on every
# run.
SIMPLIFY = "interval=5"
FIDELITY_MAX_M = 8.0
MIN_FEATURES = 133  # 95 Virginia counties and 38 independent cities
VALIDATION_KEY = "GEOID"  # unique per county, preserved through simplification
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live


def fetch_tiger():
    """Fetch every Virginia county feature as GeoJSON, through the chambers
    builder's one fetch path (robots.txt read first, an API error raised)."""
    geo = blb._get_json(TIGERWEB + "/query", {
        "where": "STATE='%s'" % VA_FIPS,
        "outFields": ",".join(FIELDS),
        "returnGeometry": "true", "outSR": "4326",
        "geometryPrecision": "6", "f": "geojson",
    })
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("TIGERweb State_County layer returned no Virginia features")
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb State_County layer hit the transfer cap — needs paging")
    return geo


def run_mapshaper(source_path, simplify, out_path):
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-simplify", "dp", "keep-shapes", simplify,
            "-o", "precision=" + PRECISION, "format=geojson", out_path,
        ],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon mirroring index.html's even-odd test (so validation
#     agrees with what the app computes at runtime) — fleet-standard copy ---
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


def validate(source_features, result_features, key_prop, samples=2000, seed=2024):
    """Refuse the build unless simplification preserves county coverage over
    the state envelope vs the full-precision fetch — the fleet's 2,000
    uniform-random-point protocol. Any point landing in two result counties
    is a topology break."""
    src = _model(source_features, key_prop)
    new = _model(result_features, key_prop)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
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
        return False, "topology broken: %d/%d points fell in >1 county" % (overlaps, samples)
    if pct < 99.5:
        return False, "point-in-county agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (agree, samples, pct)


def main():
    source = fetch_tiger()

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "counties-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, "counties.geojson")
        run_mapshaper(src_path, SIMPLIFY, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != MIN_FEATURES:
        raise RuntimeError(
            "state-counties: %d features after simplify (expected exactly %d "
            "Virginia counties and cities) — refusing to write" % (n, MIN_FEATURES)
        )

    ok, msg = validate(source["features"], simplified["features"], VALIDATION_KEY)
    if not ok:
        raise RuntimeError("state-counties validation failed: %s" % msg)

    step = blb.median_source_step_m(source["features"])
    ok, fmsg = boundary_fidelity.check_fidelity(
        source["features"], simplified["features"], VALIDATION_KEY, FIDELITY_MAX_M, "NAME")
    if not ok:
        raise RuntimeError("state-counties fidelity failed: %s — refusing to write" % fmsg)
    print("state-counties: median source step %.2f m; %s" % (step, fmsg))

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("state-counties round-trip mismatch before writing")

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)
    with open(out_path, "w") as f:
        f.write(compact)

    print(
        "state-counties -> data/app/%s: %d features (statewide); %s; %d bytes (dp %s, 6dp)"
        % (OUT_FILE, n, msg, len(compact), SIMPLIFY),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
