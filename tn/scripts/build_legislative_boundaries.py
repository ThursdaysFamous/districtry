#!/usr/bin/env python3
"""
Build the pre-simplified Tennessee legislative-district boundary files in
data/app/ from Census TIGERweb, so the app fetches them same-origin
(cache-first) instead of downloading full statewide geometry live on every
first toggle.

Statewide, like the Illinois reference, Wisconsin and Iowa: Tennessee's
instance answers anywhere in the state, so each chamber ships whole — fetch ->
simplify -> validate -> write data/app/<chamber>-districts.json. No clip
step: the served area IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not
weekly CI — re-run it on redistricting. The officeholder ROSTERS
(tn-senate-members / tn-house-members, from the state's own legislative
map service) are separate; only the geometry is here
(build_tn_legislature_roster.py builds those).

DEFAULT_TARGETS DELIBERATELY INCLUDES us-house, UNLIKE WISCONSIN'S SAME
SCRIPT. Wisconsin's build_legislative_boundaries.py defaults to its two
chambers only because its shipped congress-districts.json bytes originally
came from the (now-deleted, R2.1) state-template bootstrap step — there is
no such bootstrap here, so congress-districts.json has no other producer.
Skipping us-house by default here would silently ship no file at all.

SIMPLIFICATION IS DOUGLAS-PEUCKER, NOT VISVALINGAM. Visvalingam thresholds
triangle AREA, which does not bound how far the drawn line strays from the
true one, because successive below-threshold removals compound — which is how
a staircase along a street grid becomes a chord across a block. Douglas-Peucker
thresholds perpendicular DEVIATION in metres, so it spends vertices where
deviation demands them. The North Carolina instance this builder was copied
from measured the two against each other on 2026-09-29 (worst stray 696 m
under Visvalingam against 21 m under Douglas-Peucker, for +0.5% bytes).
Tennessee's own run on 2026-10-10 at dp interval=20 is recorded beside
FIDELITY_CEILING_M below, and every build prints it again. The Visvalingam side was not
re-measured here.

THE INTERVAL IS ABSOLUTE METRES, WHICH IS WHY EACH CHAMBER IS SIMPLIFIED ON
ITS OWN HERE. Illinois had to put all three chambers through ONE mapshaper
topology, because two Illinois House districts make up one Senate district
and a shared edge survives identically only if both came off one topology.
Tennessee has no such rule — 99 House against 33 Senate districts is a ratio
of three, but the state's own plans are drawn separately and nest nowhere in
law — so there is no shared edge to preserve, and a per-chamber run is safe
in a way it would NOT be under a retain PERCENTAGE, which is relative to the
whole dataset's vertex count and therefore means something different for one
chamber than for three.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 tn/scripts/build_legislative_boundaries.py             # all three
    python3 tn/scripts/build_legislative_boundaries.py tn-senate   # one chamber
"""

import json
import math
import os
import random
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer"
TN_FIPS = "47"

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -90.32, "minLat": 34.98, "maxLng": -81.64, "maxLat": 36.68}

# chamber -> how to build data/app/<out>.
#   layer:    TIGERweb Legislative MapServer layer index (4 the serving U.S.
#             House map — see its entry — 1 upper, 2 lower)
#   fields:   outFields kept from TIGERweb. The app's extractDistrictNumber reads
#             SLDU/SLDL and CD119/CD120 directly, with a NAME fallback.
#   layer_name, serving_until: (us-house only) the layer's expected name, and
#             the date the members it was drawn for leave office
#   out:      the data/app file index.html fetches for this layer
#   simplify: mapshaper Douglas-Peucker interval in METRES (keep-shapes) — see
#             the docstring for why it is not a Visvalingam retain percentage
#   min_features: count guard — the real district count
LAYERS = {
    "us-house": {
        # LAYER 4, THE 119TH CONGRESS, UNTIL 3 JANUARY 2027 — NOT LAYER 0.
        # Layer 0 is "120th Congressional Districts", the map Tennessee
        # redrew in May 2026 for the 2026 election. Nobody has been elected
        # from it yet: the members congress-roster.json names were elected in
        # 2024 from the 119th Congress's map, and they serve until noon on
        # 3 January 2027. Measured 2026-10-09 against TIGERweb, 39.9% of the
        # state's area changes district between the two maps, and downtown
        # Memphis reads as District 9 on the 119th map and District 5 on the
        # 120th — so drawing the new map beside these members would put the
        # wrong representative on the card for most of Memphis. The 119th
        # layer also matches the Comptroller's own 2022 congressional map
        # (Redistricting_Address_Lookup layer 11) at IoU 0.998 or better in
        # every district, which is the state's witness that it is the map
        # these members were elected from.
        # On 3 January 2027 switch to the layer named "120th Congressional
        # Districts" and its CD120 field; check_serving_map checks both the
        # layer's name and the date, so the build refuses either way.
        "layer": 4,
        "fields": ["CD119", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "119th Congressional Districts",
        "serving_until": "2027-01-03",
        "out": "congress-districts.json",
        "simplify": "interval=20",
        "min_features": 9,  # 9 Tennessee congressional districts
    },
    "tn-senate": {
        "layer": 1,
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "tn-senate-districts.json",
        "simplify": "interval=20",
        "min_features": 33,  # 33 Tennessee Senate districts
    },
    "tn-house": {
        "layer": 2,
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "tn-house-districts.json",
        "simplify": "interval=20",
        "min_features": 99,  # 99 Tennessee House districts
    },
}
DEFAULT_TARGETS = ["us-house", "tn-senate", "tn-house"]  # all three — see docstring
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live
VALIDATION_KEY = "GEOID"  # unique per district, preserved through simplification

# 25 m, PINNED rather than recomputed each run. It is "about one step of the
# true line's own detail" as the North Carolina builder measured it
# (2026-09-29, median source segment 21.87-26.10 m). On Tennessee's geometry
# (2026-10-10) the median source segment is 27.67 m (us-house), 25.41 m
# (tn-senate) and 23.63 m (tn-house), so 25 m is again about one step; the
# worst stray at dp interval=20 measured 23.2, 21.4 and 21.5 m, every
# district under the ceiling.
# Every run prints the measured step beside this value, because a ceiling
# derived from the source each run can never fail — it rises whenever the
# source gets coarser.
FIDELITY_CEILING_M = 25.0


def _rings_of(geom):
    """Every ring of a Polygon or MultiPolygon, outers and holes alike."""
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "Polygon":
        return c
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def fetch_tiger(layer, fields):
    """Fetch every Tennessee feature for a Legislative MapServer layer as GeoJSON.
    Uses curl so it works through an HTTPS proxy (as in the Claude Code
    sandbox)."""
    url = (
        TIGERWEB + "/" + str(layer) + "/query"
        "?where=" + "STATE%3D%27" + TN_FIPS + "%27"
        "&outFields=" + ",".join(fields) +
        "&outSR=4326&geometryPrecision=6&f=geojson"
    )
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300", url],
        check=True, capture_output=True,
    ).stdout
    geo = json.loads(out)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("TIGERweb layer %d returned no Tennessee features" % layer)
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb layer %d hit the transfer cap — needs paging" % layer)
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


# --- fidelity: how far the TRUE line strays from the chord drawn in its
#     place. The obvious direction gates nothing — simplification KEEPS a
#     subset of source vertices, so every drawn vertex already lies on the
#     source line and "no drawn vertex far from the source" is ~0 by
#     construction. What a reader sees is the other direction, so that is
#     what is measured: for every SOURCE vertex, its distance to the nearest
#     segment of its own district as drawn. -------------------------------
def _seg_index(feature, cell=0.02):
    idx = {}
    for ring in _rings_of(feature["geometry"]):
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    idx.setdefault((gx, gy), []).append((a, b))
    return idx


def _point_to_segment_m(p, a, b):
    my = 111320.0
    mx = 111320.0 * math.cos(math.radians(p[1]))
    px, py = p[0] * mx, p[1] * my
    ax, ay = a[0] * mx, a[1] * my
    bx, by = b[0] * mx, b[1] * my
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def median_source_step_m(features):
    """The median length of a source segment — what the true line's own
    detail is, and where FIDELITY_CEILING_M comes from. Printed on every run
    beside the pinned ceiling rather than used to recompute it: a ceiling
    derived from the source each run can never fail, because it rises
    whenever the source gets coarser."""
    steps = []
    for f in features:
        for ring in _rings_of(f["geometry"]):
            for i in range(len(ring) - 1):
                a, b = ring[i], ring[i + 1]
                my = 111320.0
                mx = 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
                steps.append(math.hypot((b[0] - a[0]) * mx, (b[1] - a[1]) * my))
    steps.sort()
    return steps[len(steps) // 2] if steps else 0.0


def check_fidelity(src_features, drawn_features, key_prop):
    """Worst stray in metres, and how many districts exceed the ceiling."""
    drawn = {f["properties"].get(key_prop): f for f in drawn_features}
    worst = 0.0
    over = []
    for f in src_features:
        d = drawn.get(f["properties"].get(key_prop))
        if d is None:
            continue
        idx = _seg_index(d)
        w = 0.0
        for ring in _rings_of(f["geometry"]):
            for v in ring[:-1]:
                gx = int(math.floor(v[0] / 0.02))
                gy = int(math.floor(v[1] / 0.02))
                cand = []
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        cand += idx.get((gx + ddx, gy + ddy), ())
                if not cand:
                    continue
                best = min(_point_to_segment_m(v, a, b) for a, b in cand)
                if best > w:
                    w = best
        if w > worst:
            worst = w
        if w > FIDELITY_CEILING_M:
            over.append(f["properties"].get(key_prop))
    return worst, over


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
    """Refuse the build unless simplification preserves district coverage over
    the state envelope vs the full-precision fetch — the project's 2,000
    uniform-random-point protocol. Any point landing in two result districts
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
        return False, "topology broken: %d/%d points fell in >1 district" % (overlaps, samples)
    if pct < 99.5:
        return False, "point-in-district agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (agree, samples, pct)


def check_serving_map(name, cfg, today=None):
    """Refuse to build a map whose members have left office, or a layer index
    that no longer carries the map it was chosen for. TIGERweb renumbers its
    layers when a vintage rolls, so the index alone proves nothing."""
    if "layer_name" not in cfg:
        return
    import datetime
    today = today or datetime.date.today().isoformat()
    if today >= cfg["serving_until"]:
        raise RuntimeError(
            "%s: the members drawn from %r left office on %s — switch to the "
            "layer named '120th Congressional Districts' and its CD120 field, "
            "then drop layer_name/serving_until" % (name, cfg["layer_name"], cfg["serving_until"]))
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "60",
         TIGERWEB + "/" + str(cfg["layer"]) + "?f=json"],
        check=True, capture_output=True,
    ).stdout
    got = json.loads(out).get("name", "")
    if got != cfg["layer_name"]:
        raise RuntimeError(
            "%s: TIGERweb layer %d is now %r, not %r — find the layer that is, "
            "and refuse rather than draw a different Congress's map"
            % (name, cfg["layer"], got, cfg["layer_name"]))


def build_chamber(name, cfg):
    check_serving_map(name, cfg)
    source = fetch_tiger(cfg["layer"], cfg["fields"])

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, name + "-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, name + ".geojson")
        run_mapshaper(src_path, cfg["simplify"], out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != cfg["min_features"]:
        raise RuntimeError(
            "%s: %d features after simplify (expected exactly %d districts) "
            "— refusing to write" % (name, n, cfg["min_features"])
        )

    ok, msg = validate(source["features"], simplified["features"], VALIDATION_KEY)
    if not ok:
        raise RuntimeError("%s validation failed: %s" % (name, msg))

    step = median_source_step_m(source["features"])
    worst, over = check_fidelity(source["features"], simplified["features"], VALIDATION_KEY)
    if over:
        raise RuntimeError(
            "%s: %d district(s) stray past the %.0f m fidelity ceiling (worst %.1f m): "
            "%s — refusing to write" % (name, len(over), FIDELITY_CEILING_M, worst,
                                        ", ".join(sorted(over)[:5]))
        )
    print("%s: median source step %.2f m, worst stray %.1f m against a %.0f m ceiling, "
          "0 of %d districts over" % (name, step, worst, FIDELITY_CEILING_M, len(simplified["features"])))

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("%s round-trip mismatch before writing" % name)

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, cfg["out"])
    with open(out_path, "w") as f:
        f.write(compact)

    print(
        "%s -> data/app/%s: %d features (statewide); %s; %d bytes (dp %s, 6dp)"
        % (name, cfg["out"], n, msg, len(compact), cfg["simplify"]),
        file=sys.stderr,
    )


def main():
    targets = sys.argv[1:] or DEFAULT_TARGETS
    unknown = [t for t in targets if t not in LAYERS]
    if unknown:
        print("unknown chamber(s): %s; known: %s" % (unknown, list(LAYERS)), file=sys.stderr)
        sys.exit(1)
    for name in targets:
        build_chamber(name, LAYERS[name])


if __name__ == "__main__":
    main()
