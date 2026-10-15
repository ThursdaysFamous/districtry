#!/usr/bin/env python3
"""
Build the pre-simplified Mississippi county boundary file in data/app/ from Census
TIGERweb, so the app fetches it same-origin (cache-first) instead of
downloading full statewide geometry live on every first toggle.

Statewide, like the Illinois reference, Wisconsin and Iowa: Mississippi's
instance answers anywhere in the state, so the county layer ships whole — fetch ->
simplify -> validate -> write data/app/state-counties.json. No clip step:
the served area IS the state.

This is an occasional OPERATOR step, not weekly CI — county lines change
essentially never; re-run only if TIGERweb corrects a boundary.

SIMPLIFICATION IS DOUGLAS-PEUCKER WITH A FIDELITY CEILING, AND THAT IS A
MEASUREMENT. This file was first built the way the copied builder built it,
Visvalingam at 10% retained, and measured on 2026-10-15 against the
full-precision TIGERweb lines that drew a line up to 184.5 m away from where
the county line really runs (Holmes and Attala, along their shared edge),
with 54 of the 82 counties more than 25 m off somewhere. A reader within that
distance of a county line could be told the wrong county, and the County
Supervisor District layer, which is simplified with a bounded stray, would
then disagree with this one about which county a point is in. Visvalingam
thresholds triangle AREA, which does not bound how far the drawn line strays;
Douglas-Peucker thresholds the stray itself. The legislative builder beside
this one already uses it, and its fidelity check is imported from there rather
than copied.

AND THE STRAY IS ONE OF TWO MEASURES, AND ON THE OTHER interval=20 IS WORSE
THAN THE SETTING IT REPLACED (measured later on 2026-10-15, after another
thread measured the same trade across the newer states). The second measure is
the ground a reader is given the wrong answer on: the area, in an equal-area
projection (EPSG:5070), where this file names a different county than the
full-precision TIGERweb lines do, or names none inside the state.

    setting                    worst stray   ground answered wrongly   gzipped
    visvalingam 10%  (first)       184.5 m          23.1 km2            134 KB
    dp interval=20   (shipped)      21.7 m          40.7 km2            139 KB
    dp interval=10                  11.1 m          18.0 km2            208 KB
    dp interval=5                    5.6 m           8.1 km2            295 KB

At a 20 m interval the drawn line stays within about 20 m of the true one but
leaves out more of its small bends, and the ground those bends enclose is
answered with the neighbouring county. Every interval of 10 m or finer beats
the first build on both measures, with a larger file. Which interval ships is a
trade between accuracy and the size of a file every reader downloads, and Adam
is choosing it for the ten newer states' county files (asked 2026-10-15). This
file stays at interval=20 until he does, and Mississippi follows his choice
before it goes live (ms/WATCH.md). Measuring only the stray is how interval=20
looked like a fix.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ms/scripts/build_state_counties.py
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
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1"
MS_FIPS = "28"

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -91.85, "minLat": 29.95, "maxLng": -87.9, "maxLat": 35.15}

FIELDS = ["NAME", "BASENAME", "GEOID", "STATE", "COUNTY"]
OUT_FILE = "state-counties.json"
# Douglas-Peucker interval in METRES (keep-shapes). Measured 2026-10-15: the
# median source step is 27.84 m, and interval=20 leaves the worst stray under
# the 25 m ceiling the legislative builder pins (blb.FIDELITY_CEILING_M).
# PROVISIONAL: it answers more ground with the wrong county than the setting it
# replaced (the docstring's table), and changes to Adam's choice before go-live.
SIMPLIFY = "interval=20"
MIN_FEATURES = 82  # every Mississippi county — no water pseudo-district on this layer
VALIDATION_KEY = "GEOID"  # unique per county, preserved through simplification
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live


def fetch_tiger():
    """Fetch every Mississippi county feature as GeoJSON. Uses curl so it works
    through an HTTPS proxy (as in the Claude Code sandbox)."""
    url = (
        TIGERWEB + "/query"
        "?where=" + "STATE%3D%27" + MS_FIPS + "%27"
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
        raise RuntimeError("TIGERweb State_County layer returned no Mississippi features")
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
            "Mississippi counties) — refusing to write" % (n, MIN_FEATURES)
        )

    ok, msg = validate(source["features"], simplified["features"], VALIDATION_KEY)
    if not ok:
        raise RuntimeError("state-counties validation failed: %s" % msg)

    step = blb.median_source_step_m(source["features"])
    worst, over = blb.check_fidelity(source["features"], simplified["features"], VALIDATION_KEY)
    if over:
        raise RuntimeError(
            "state-counties: %d county(ies) stray past the %.0f m fidelity ceiling "
            "(worst %.1f m): %s — refusing to write"
            % (len(over), blb.FIDELITY_CEILING_M, worst, ", ".join(sorted(over)[:5])))
    print("state-counties: median source step %.2f m, worst stray %.1f m against a "
          "%.0f m ceiling, 0 of %d counties over"
          % (step, worst, blb.FIDELITY_CEILING_M, n))

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
