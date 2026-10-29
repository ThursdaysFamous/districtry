#!/usr/bin/env python3
"""
Build the pre-simplified Virginia congressional and legislative-district
boundary files in data/app/, so the app fetches them same-origin (cache-first)
instead of downloading full statewide geometry live on every first toggle.

Statewide, like the Illinois reference and every newer state: Virginia's
instance answers anywhere in the state, so each map ships whole — fetch ->
simplify -> validate -> write data/app/<file>. No clip step: the served area
IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS (congress-roster,
va-senate-members, va-house-members) are separate; only the geometry is here.

DEFAULT_TARGETS DELIBERATELY INCLUDES us-house: there is no bootstrap step that
writes congress-districts.json, so skipping it by default would ship no file.

THE CONGRESSIONAL MAP IS THE 2021 MAP, DRAWN FROM TIGERweb LAYER 0 (THE 120TH
CONGRESS), AND FOR VIRGINIA THAT IS A MEASUREMENT RATHER THAN A DEFAULT. The
General Assembly put a constitutional amendment to the voters in 2026 that
would have let it redraw the map for that year's election, and the Supreme
Court of Virginia blocked it on 8 May 2026 (NPR and NBC News, 8 May 2026;
Virginia Mercury, 18 May 2026, on the U.S. Supreme Court's refusal to step in).
So the 3 November 2026 election is held on the map the Supreme Court of
Virginia drew in December 2021, and the members seated on 3 January 2027 are
elected from it. Measured 2026-10-29 with shapely on the full-precision fetch
of both layers: layer 0 ("120th Congressional Districts") and layer 4 ("119th
Congressional Districts") carry the same eleven districts, and every
district's intersection-over-union between the two is 1.0. So layer 0 is
right both before and after 3 January 2027, and check_serving_map refuses to
draw it before that date if it ever stops matching layer 4 district for
district, because until then the sitting members were elected from layer 4's
map. It also refuses on or after 3 January 2029, so a person reads which map
the 2028 election used before anything is drawn: another attempt to redraw
before 2028 is possible.

THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1
and 2), the maps the Supreme Court of Virginia drew in December 2021, first
used for the 2023 elections. Measured 2026-10-29 against TIGERweb's 2024
layers (5 and 6): the 100 House of Delegates districts are identical (every
IoU 1.0), and of the 40 Senate districts 38 are identical and two differ by
slivers (District 31 IoU 0.99972, District 28 0.99988), which is the Census
Bureau's own correction between vintages. The newer vintage is drawn. Both
chambers are in force until the maps drawn after the 2030 census, so they carry
no date guard; check_serving_map refuses if a layer's name changes, since
TIGERweb renumbers its layers when a vintage rolls.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
Adam chose for Mississippi's maps before that instance opened ("Finer first",
2026-10-16) and Missouri's and Louisiana's builders carry. Visvalingam
thresholds triangle AREA, which does not bound how far the drawn line strays
from the true one, because successive below-threshold removals compound;
Douglas-Peucker thresholds the stray itself. Every build prints the worst
stray against the ceiling.

THE INTERVAL IS ABSOLUTE METRES, WHICH IS WHY EACH MAP IS SIMPLIFIED ON ITS OWN
HERE. Illinois had to put all three chambers through ONE mapshaper topology,
because two Illinois House districts make up one Senate district and a shared
edge survives identically only if both came off one topology. Virginia has no
such rule (100 House of Delegates against 40 Senate districts is not a nesting
ratio), so a per-map run is safe in a way it would NOT be under a retain
PERCENTAGE, which is relative to the whole dataset's vertex count.

Prerequisites: requests, and Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 va/scripts/build_legislative_boundaries.py             # all three
    python3 va/scripts/build_legislative_boundaries.py va-senate   # one map
"""

import datetime
import json
import math
import os
import random
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer"
VA_FIPS = "51"
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/va/)"}
REQUEST_TIMEOUT = 300

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -83.85, "minLat": 36.35, "maxLng": -74.95, "maxLat": 39.65}

# map -> how to build data/app/<out>.
#   url:        the TIGERweb layer, filtered to Virginia
#   fields:     outFields kept — the app's extractDistrictNumber reads CD120,
#               SLDU and SLDL directly, with a NAME fallback
#   layer_name: the layer's name as its service states it
#   serving_until: (us-house only) the date after which a person must re-read
#               which map the sitting members were elected from
#   same_as:    (us-house only) the layer that must match this one district
#               for district until `same_until`, and the field it numbers with
#   out:        the data/app file index.html fetches for this layer
#   simplify:   mapshaper Douglas-Peucker interval in METRES (keep-shapes)
#   count:      the real district count; the build refuses any other
LAYERS = {
    "us-house": {
        # LAYER 0, THE 120TH CONGRESS, which is the same map as layer 4 in
        # Virginia. See the docstring.
        "url": TIGERWEB + "/0",
        "fields": ["CD120", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "120th Congressional Districts",
        "same_as": {"url": TIGERWEB + "/4", "layer_name": "119th Congressional Districts",
                    "field": "CD119", "same_until": "2027-01-03"},
        "serving_until": "2029-01-03",
        "out": "congress-districts.json",
        "simplify": "interval=5",
        "count": 11,  # 11 Virginia congressional districts
    },
    "va-senate": {
        "url": TIGERWEB + "/1",
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "2026 State Legislative Districts - Upper",
        "out": "va-senate-districts.json",
        "simplify": "interval=5",
        "count": 40,  # 40 Senate of Virginia districts
    },
    "va-house": {
        "url": TIGERWEB + "/2",
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "2026 State Legislative Districts - Lower",
        "out": "va-house-districts.json",
        "simplify": "interval=5",
        "count": 100,  # 100 Virginia House of Delegates districts
    },
}
DEFAULT_TARGETS = ["us-house", "va-senate", "va-house"]  # all three — see docstring
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live
VALIDATION_KEY = "GEOID"  # unique per district, preserved through simplification

# 8 m, PINNED rather than recomputed each run: the ceiling
# build_state_counties.py holds the county file to, and the setting Adam chose
# for Mississippi's maps before that instance opened ("Finer first",
# 2026-10-16). Every run prints the measured median source step beside this
# value, because a ceiling derived from the source each run can never fail —
# it rises whenever the source gets coarser.
FIDELITY_CEILING_M = 8.0


def _rings_of(geom):
    """Every ring of a Polygon or MultiPolygon, outers and holes alike."""
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "Polygon":
        return c
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def _get_json(url, params):
    import requests  # noqa: PLC0415 (only the fetching path needs it)
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="va-build-legislative-boundaries")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer (CLAUDE.md): read the key, never a
        # default that turns the error object into "no features".
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def fetch_layer(name, cfg, url=None, fields=None):
    """Every Virginia feature of the layer, as GeoJSON."""
    params = {"where": "STATE='%s'" % VA_FIPS,
              "outFields": ",".join(fields or cfg["fields"]),
              "returnGeometry": "true", "outSR": "4326",
              "geometryPrecision": "6", "f": "geojson"}
    url = url or cfg["url"]
    geo = _get_json(url + "/query", params)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("%s: %s returned no features" % (name, url))
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("%s: %s hit the transfer cap — needs paging" % (name, url))
    return geo


def _layer_name(url):
    return _get_json(url, {"f": "json"}).get("name", "")


def check_serving_map(name, cfg, today=None):
    """Refuse a layer that no longer carries the map it was chosen for, and a
    congressional map nobody has re-read since the 2028 election. TIGERweb
    renumbers its layers when a vintage rolls, so the index alone proves
    nothing."""
    got = _layer_name(cfg["url"])
    if got != cfg["layer_name"]:
        raise RuntimeError(
            "%s: %s is now %r, not %r — find the layer that is, and refuse "
            "rather than draw a different map" % (name, cfg["url"], got, cfg["layer_name"]))
    today = today or datetime.date.today().isoformat()
    if "serving_until" in cfg and today >= cfg["serving_until"]:
        raise RuntimeError(
            "%s: the members elected on Virginia's 2021 map in 2026 left office on "
            "%s. Re-read which map the 2028 election used, then change this "
            "entry" % (name, cfg["serving_until"]))


def check_same_map(name, cfg, source, today=None):
    """Until `same_until`, the sitting members were elected from the OTHER
    layer's map, so this layer is drawn only while the two are the same map:
    the same districts, each with an intersection-over-union of at least
    0.9999 (shapely, on the full-precision fetch of both). Refuses otherwise.
    """
    same = cfg.get("same_as")
    today = today or datetime.date.today().isoformat()
    if not same or today >= same["same_until"]:
        return
    got = _layer_name(same["url"])
    if got != same["layer_name"]:
        raise RuntimeError(
            "%s: %s is now %r, not %r — re-read which map the sitting members "
            "were elected from" % (name, same["url"], got, same["layer_name"]))
    from shapely.geometry import shape  # noqa: PLC0415 (only this check needs it)
    other = fetch_layer(name, cfg, url=same["url"],
                        fields=[same["field"], "GEOID", "STATE"])
    mine = {f["properties"]["GEOID"]: shape(f["geometry"]) for f in source["features"]}
    theirs = {f["properties"]["GEOID"]: shape(f["geometry"]) for f in other["features"]}
    if set(mine) != set(theirs):
        raise RuntimeError(
            "%s: %s and %s carry different districts (%s against %s) — the "
            "sitting members were elected from the second; refusing to draw "
            "the first" % (name, cfg["url"], same["url"], sorted(mine), sorted(theirs)))
    worst = 1.0
    for geoid, g in mine.items():
        o = theirs[geoid]
        iou = g.intersection(o).area / g.union(o).area
        worst = min(worst, iou)
        if iou < 0.9999:
            raise RuntimeError(
                "%s: district %s differs between %s and %s (IoU %.5f) — the "
                "sitting members were elected from the second; refusing to draw "
                "the first" % (name, geoid, cfg["url"], same["url"], iou))
    print("%s: %s matches %s district for district (lowest IoU %.6f)"
          % (name, cfg["layer_name"], same["layer_name"], worst))


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
    """Worst stray in metres, and which districts exceed the ceiling."""
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


def build_map(name, cfg):
    check_serving_map(name, cfg)
    source = fetch_layer(name, cfg)
    check_same_map(name, cfg, source)

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, name + "-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, name + ".geojson")
        run_mapshaper(src_path, cfg["simplify"], out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != cfg["count"]:
        raise RuntimeError(
            "%s: %d features after simplify (expected exactly %d districts) "
            "— refusing to write" % (name, n, cfg["count"])
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
          "0 of %d districts over" % (name, step, worst, FIDELITY_CEILING_M, n))

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
        print("unknown map(s): %s; known: %s" % (unknown, list(LAYERS)), file=sys.stderr)
        sys.exit(1)
    for name in targets:
        build_map(name, LAYERS[name])


if __name__ == "__main__":
    main()
