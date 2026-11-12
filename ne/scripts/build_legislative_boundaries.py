#!/usr/bin/env python3
"""
Build the pre-simplified Nebraska congressional and legislative-district
boundary files in data/app/, so the app fetches them same-origin (cache-first)
instead of downloading full statewide geometry live on every first toggle.

Statewide, like the Illinois reference and every newer state: Nebraska's
instance answers anywhere in the state, so each map ships whole — fetch ->
simplify -> validate -> write data/app/<file>. No clip step: the served area
IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS (congress-roster,
ne-legislature-members) are separate; only the geometry is
here.

DEFAULT_TARGETS DELIBERATELY INCLUDES us-house: there is no bootstrap step that
writes congress-districts.json, so skipping it by default would ship no file.

THE CONGRESSIONAL MAP IS DRAWN FROM TIGERweb LAYER 0 (THE 120TH CONGRESS),
WHICH IN NEBRASKA IS THE SAME MAP AS LAYER 4. Measured 2026-11-12 with shapely on
a 6-decimal fetch of both layers: layer 0 ("120th Congressional Districts")
and layer 4 ("119th Congressional Districts") carry the same 3 districts,
and every district's intersection-over-union between the two is 1.0. So
layer 0 is right both before and after 3 January 2027, and check_same_map
refuses to draw it before that date if it ever stops matching layer 4
district for district, because until then the sitting members were elected
from layer 4's map. check_serving_map also refuses on or after 3 January
2029, so a person reads which map the 2028 election used before anything is
drawn.

NEBRASKA'S LEGISLATURE HAS ONE CHAMBER (Nebraska Constitution, Article III,
Section 1), AND IT IS NONPARTISAN: 49 senators, one from each of 49
legislative districts. TIGERweb carries the districts on layer 1 (2026 State Legislative
Districts - Upper, field SLDU) and nothing on layer 2. Measured 2026-11-12 against
TIGERweb's 2024 layer (5): every district identical (intersection-over-union
1.0). check_serving_map refuses if the layer's name changes, since TIGERweb
renumbers its layers when a vintage rolls. There is no second map, so nothing
nests and the one map is simplified on its own.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
Adam chose for Mississippi's maps before that instance opened ("Finer first",
2026-10-16) and the newer states' builders carry. Visvalingam thresholds
triangle AREA, which does not bound how far the drawn line strays from the
true one, because successive below-threshold removals compound;
Douglas-Peucker thresholds the stray itself. Every build prints the worst
stray against the ceiling. The interval is absolute metres, so a small test
input says the same thing as the full state, which a retain percentage would
not.

Prerequisites: requests, and Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ne/scripts/build_legislative_boundaries.py           # all three
    python3 ne/scripts/build_legislative_boundaries.py us-house  # congress only
    python3 ne/scripts/build_legislative_boundaries.py --check   # offline: the
        nesting gate on the shipped files (CI)
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
TAG = "ne"
NO_NEST_WHY = "Nebraska's Legislature has one chamber"
ST_NAME = "Nebraska"
ST_FIPS = "31"
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/ne/)"}
REQUEST_TIMEOUT = 300

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -104.3, "minLat": 39.75, "maxLng": -95.06, "maxLat": 43.25}

# map -> how to build data/app/<out>.
#   url:        the TIGERweb layer, filtered to Nebraska
#   fields:     outFields kept — the app's extractDistrictNumber reads CD120,
#               CD119, SLDU and SLDL directly, with a NAME fallback
#   layer_name: the layer's name as its service states it
#   serving_until: (us-house only) the date after which a person must re-read
#               which map the sitting members were elected from
#   same_as:    (us-house only) the layer that must match this one district
#               for district until `same_until`, and the field it numbers with
#   where_extra: a filter added to STATE='31' (the Census's "not defined"
#               water record is not a district)
#   out:        the data/app file index.html fetches for this layer
#   simplify:   mapshaper Douglas-Peucker interval in METRES (keep-shapes)
#   count:      the real district count; the build refuses any other
LAYERS = {
    "us-house": {
        # LAYER 0, THE 120TH CONGRESS, which is the same map as layer 4 in
        # Nebraska. See the docstring.
        "url": TIGERWEB + "/0",
        "fields": ["CD120", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "120th Congressional Districts",
        "same_as": {"url": TIGERWEB + "/4", "layer_name": "119th Congressional Districts",
                    "field": "CD119", "same_until": "2027-01-03"},
        "serving_until": "2029-01-03",
        "out": "congress-districts.json",
        "simplify": "interval=5",
        "count": 3,  # 3 Nebraska congressional districts
    },
    "ne-legislature": {
        "url": TIGERWEB + "/1",
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "2026 State Legislative Districts - Upper",
        "out": "ne-legislature-districts.json",
        "simplify": "interval=5",
        "count": 49,  # 49 Nebraska Legislature districts
    },
}
DEFAULT_TARGETS = ["us-house", "ne-legislature"]  # both — see docstring

# Nebraska's Legislature has one chamber, so there is no pairing to keep.
FAMILY = ("ne-legislature",)
NESTING = None
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
                        label="ne-build-legislative-boundaries")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer (CLAUDE.md): read the key, never a
        # default that turns the error object into "no features".
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def fetch_layer(name, cfg, url=None, fields=None):
    """Every Nebraska feature of the layer, as GeoJSON."""
    # The not-defined filter names the field of the layer asked: the
    # same_as check asks layer 4, whose field is CD119, not CD120.
    extra = cfg.get("where_extra", "")
    if url and cfg.get("same_as") and url == cfg["same_as"]["url"]:
        extra = extra.replace("CD120", cfg["same_as"]["field"])
    params = {"where": "STATE='%s'%s" % (ST_FIPS, extra),
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
            "%s: %s is past. Re-read which map the sitting members were elected "
            "from, then change this entry" % (name, cfg["serving_until"]))


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


def run_mapshaper_family(source_paths, simplify, out_dir):
    """Simplify the Senate and the House in ONE run, so a shared edge is one
    arc. `combine-files` reads the inputs into a single dataset, which is what
    makes mapshaper dedupe an edge both layers draw into ONE arc; simplification
    then removes the same vertices from it for both. `target=*` writes every
    layer back out, one file per input named after the input."""
    subprocess.run(
        ["npx", "-y", MAPSHAPER] + list(source_paths) + [
            "combine-files", "-simplify", "dp", "keep-shapes", simplify,
            "-o", "precision=" + PRECISION, "format=geojson", "target=*", out_dir],
        check=True, cwd=REPO_ROOT,
    )


# --- nesting: the measured pairing, in the source and in the shipped files --
def check_source_nesting(senate_src, assembly_src):
    """Refuse a fetch whose House districts no longer pair into the Senate
    districts NESTING records (shapely, on the full-precision fetch)."""
    from shapely.geometry import shape  # noqa: PLC0415 (only this check needs it)
    sen = {f["properties"]["SLDU"]: shape(f["geometry"]).buffer(0) for f in senate_src["features"]}
    hse = {f["properties"]["SLDL"]: shape(f["geometry"]).buffer(0) for f in assembly_src["features"]}
    want = {a: s for s, pair in NESTING.items() for a in pair}
    if set(sen) != set(NESTING) or set(hse) != set(want):
        raise RuntimeError(
            "the fetched districts (%d Senate, %d House) are not the ones NESTING "
            "records — a redistricting? Read it, then re-measure the table"
            % (len(sen), len(hse)))
    for a, g in sorted(hse.items()):
        inside = sen[want[a]].intersection(g).area / g.area
        if inside < 0.9999:
            raise RuntimeError(
                "House %s has only %.5f of its area inside Senate %s — the pairing "
                "NESTING records no longer holds" % (a, inside, want[a]))
    print("nesting: all %d House districts lie inside the Senate district NESTING "
          "pairs them with" % len(hse))


def _vertex_set(geom):
    return {(pt[0], pt[1]) for ring in _rings_of(geom) for pt in ring}


def check_nesting(built):
    """Every Senate boundary vertex must be a vertex of its own two House
    districts. Under one shared topology the Senate ring is assembled FROM
    House arcs, so this holds with no tolerance at all — which is what makes
    it a good gate: there is no epsilon to tune and no way for it to pass
    weakly. It fails on a pair simplified in two separate runs."""
    sen = {f["properties"].get("SLDU"): f for f in built[FAMILY[0]]["features"]}
    hse = {f["properties"].get("SLDL"): f for f in built[FAMILY[1]]["features"]}
    problems = []
    checked = 0
    for s, pair in sorted(NESTING.items()):
        if s not in sen or any(a not in hse for a in pair):
            problems.append("Senate %s or one of House %s is missing" % (s, " + ".join(pair)))
            continue
        checked += 1
        kids = set()
        for a in pair:
            kids |= _vertex_set(hse[a]["geometry"])
        stray = _vertex_set(sen[s]["geometry"]) - kids
        if stray:
            problems.append(
                "Senate %s has %d vertex/vertices on no line of House %s; the two "
                "chambers were not simplified from one topology"
                % (s, len(stray), " + ".join(pair)))
    if not checked:
        return False, "no pairing was checked — NESTING or the files are wrong"
    if problems:
        return False, "%d pairing(s) broken; first: %s" % (len(problems), problems[0])
    return True, "%d Senate districts share every boundary vertex with their House districts" % checked


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


def gate_and_write(name, cfg, source, simplified):
    """The per-layer gates every map passes, then the write."""
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
    return msg


def write_map(name, cfg, simplified, msg):
    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("%s round-trip mismatch before writing" % name)

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, cfg["out"])
    with open(out_path, "w") as f:
        f.write(compact)

    print(
        "%s -> data/app/%s: %d features (statewide); %s; %d bytes (dp %s, 6dp)"
        % (name, cfg["out"], len(simplified["features"]), msg, len(compact), cfg["simplify"]),
        file=sys.stderr,
    )


def build_map(name, cfg):
    """One map alone: Congress, which nests in nothing."""
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

    msg = gate_and_write(name, cfg, source, simplified)
    write_map(name, cfg, simplified, msg)


def build_family():
    """The Senate and the House: fetch both, check the pairing, simplify them
    as ONE topology, gate each and the pair, then write both."""
    source = {}
    for name in FAMILY:
        check_serving_map(name, LAYERS[name])
        source[name] = fetch_layer(name, LAYERS[name])
    check_source_nesting(source[FAMILY[0]], source[FAMILY[1]])
    simplify = LAYERS[FAMILY[0]]["simplify"]
    if any(LAYERS[n]["simplify"] != simplify for n in FAMILY):
        raise RuntimeError("the two chambers must share one simplify interval")

    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name in FAMILY:
            sp = os.path.join(tmp, name + ".geojson")
            with open(sp, "w") as f:
                json.dump(source[name], f)
            paths.append(sp)
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir)
        run_mapshaper_family(paths, simplify, out_dir + os.sep)
        built = {}
        for name in FAMILY:
            # mapshaper writes a directory target as <input base>.json
            op = os.path.join(out_dir, name + ".json")
            if not os.path.exists(op):
                raise RuntimeError(
                    "%s: mapshaper wrote no output for this chamber (looked for %s) — "
                    "combine-files names outputs after the inputs" % (name, op))
            with open(op) as f:
                built[name] = json.load(f)

    msgs = {name: gate_and_write(name, LAYERS[name], source[name], built[name]) for name in FAMILY}
    ok, msg = check_nesting(built)
    if not ok:
        raise RuntimeError("nesting check failed: %s — refusing to write" % msg)
    print("nesting: %s" % msg)
    for name in FAMILY:
        write_map(name, LAYERS[name], built[name], msgs[name])


def check_shipped():
    """Offline: the nesting gate on the files in data/app. This is the CI gate.
    It needs no network, because the nesting is a relation BETWEEN two shipped
    layers — which is exactly the regression a single-chamber rebuild would
    reintroduce. The fidelity gate needs the TIGER fetch and is build-time
    only."""
    if not NESTING:
        print("%s build-legislative-boundaries: OK — no nesting rule to check: %s"
              % (TAG, NO_NEST_WHY))
        return 0
    built = {}
    for name in FAMILY:
        path = os.path.join(APP_DATA_DIR, LAYERS[name]["out"])
        if not os.path.exists(path):
            print("ne build-legislative-boundaries: FAIL — %s is missing" % LAYERS[name]["out"],
                  file=sys.stderr)
            return 1
        with open(path) as f:
            built[name] = json.load(f)
    ok, msg = check_nesting(built)
    if not ok:
        print("ne build-legislative-boundaries: FAIL — %s\n"
              "  Rebuild the pair (python3 ne/scripts/build_legislative_boundaries.py); "
              "simplifying one chamber alone is what breaks this." % msg, file=sys.stderr)
        return 1
    print("ne build-legislative-boundaries: OK — %s" % msg)
    return 0


def main():
    args = sys.argv[1:]
    if args == ["--check"]:
        sys.exit(check_shipped())
    targets = args or DEFAULT_TARGETS
    unknown = [t for t in targets if t not in LAYERS]
    if unknown:
        print("unknown map(s): %s; known: %s" % (unknown, list(LAYERS)), file=sys.stderr)
        sys.exit(1)
    lone = [t for t in targets if t in FAMILY] if NESTING else []
    if lone and set(lone) != set(FAMILY):
        print("the Senate and the House are rebuilt together or not at all: "
              "rebuilding one alone breaks the nesting", file=sys.stderr)
        sys.exit(1)
    for name in targets:
        if name not in FAMILY or not NESTING:
            build_map(name, LAYERS[name])
    if lone:
        build_family()


if __name__ == "__main__":
    main()
