#!/usr/bin/env python3
"""
Build the pre-simplified Ohio congressional and legislative-district boundary
files in data/app/, so the app fetches them same-origin (cache-first) instead
of downloading full statewide geometry live on every first toggle.

Statewide, like the Illinois reference and every newer state: Ohio's instance
answers anywhere in the state, so each map ships whole — fetch -> simplify ->
gate -> write data/app/<file>. No clip step: the served area IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS (congress-roster,
oh-senate-members, oh-house-members) are separate; only the geometry is here.

THE CONGRESSIONAL MAP IS THE ONE THE SITTING MEMBERS WERE ELECTED FROM, TIGERweb
LAYER 4 (THE 119TH CONGRESS), UNTIL 3 JANUARY 2027. Ohio redrew for the 120th
Congress, which TIGERweb carries as layer 0 ("120th Congressional Districts").
Measured 2026-11-11 with shapely on a 6-decimal fetch of both layers: the two
carry the same 15 district numbers, and 13 of the 15 differ (the lowest
intersection-over-union District 15 at 0.478, then District 1 at 0.506 and
District 7 at 0.537), so the two maps are not interchangeable. The members
holding those seats until 3 January 2027 were elected in 2024 from layer 4's
map, so that is the map drawn, and check_serving_map refuses on or after that
date: the change that day is to switch this entry to layer 0 and CD120, which
is a person's step, because the card then names the members elected in 2026.

THE TWO CHAMBERS ARE TIGERweb's 2026 STATE LEGISLATIVE DISTRICTS (layers 1
and 2): 33 Senate and 99 House districts. Measured 2026-11-11 against
TIGERweb's 2024 layers (5 and 6): all 33 Senate districts are identical (the
lowest IoU 0.9999997), and 95 of the 99 House districts are identical while
four differ by slivers (the lowest District 23 at 0.99987, then District 57 at
0.99992). The newer vintage is drawn. Both chambers carry no date guard;
check_serving_map refuses if a layer's name changes, since TIGERweb renumbers
its layers when a vintage rolls.

THREE OHIO HOUSE DISTRICTS MAKE UP EACH OHIO SENATE DISTRICT (Ohio
Constitution, Article XI, Section 4), AND THE SHIPPED FILES MUST AGREE THAT
THEY DO. The numbering is not arithmetic — Senate District 1 is House 81, 82
and 83 — so the three are pinned in NESTING_TRIPLETS, read from TIGER on
2026-11-11: every one of the 33 Senate districts is exactly three whole House
districts (shapely, share of each House district inside its Senate district
1.0), and in the 6-decimal fetch every Senate boundary vertex is a vertex of
one of its three House districts, 33 of 33. So:

  * ALL THREE MAPS ARE SIMPLIFIED IN ONE MAPSHAPER RUN (`combine-files`), the
    Illinois method (scripts/build_legislative_boundaries.py, 2026-09-25):
    mapshaper builds topology within one dataset, so a Senate edge and the
    House edge under it become ONE arc and lose the same vertices. Simplified
    map by map, as Florida's and Pennsylvania's builders do because their
    chambers do not nest, the Senate line and the House lines under it would
    each keep different vertices and part at street scale.
  * The build refuses unless the SOURCE holds the table (every Senate vertex
    on its three House districts, and the 33 triplets covering House 1..99
    once each), so a renumbering or a new map cannot ship under a stale table.
  * The build refuses, and `--check` fails offline in CI, unless every SHIPPED
    Senate vertex is a vertex of its three shipped House districts — exact,
    with no tolerance, because under one topology the Senate ring is
    assembled from House arcs.
  * There is no per-chamber argument: rebuilding one chamber alone is what
    breaks the nesting, so the family is the unit.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
Adam chose for Mississippi's maps before that instance opened ("Finer first",
2026-10-16) and the newer states' builders carry. Visvalingam thresholds
triangle AREA, which does not bound how far the drawn line strays from the
true one, because successive below-threshold removals compound;
Douglas-Peucker thresholds the stray itself. Its interval is absolute metres,
so putting three maps through one run does not change how hard each is
simplified, as a retain PERCENTAGE (relative to the whole dataset's vertex
count) would. Every build prints the worst stray against the ceiling.

Prerequisites: requests, and Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 oh/scripts/build_legislative_boundaries.py           # all three
    python3 oh/scripts/build_legislative_boundaries.py --check   # offline nesting gate
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
OH_FIPS = "39"
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/oh/)"}
REQUEST_TIMEOUT = 300

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -85.0, "minLat": 38.25, "maxLng": -80.35, "maxLat": 42.45}

# map -> how to build data/app/<out>.
#   url:        the TIGERweb layer, filtered to Ohio
#   fields:     outFields kept — the app's extractDistrictNumber reads CD119,
#               SLDU and SLDL directly, with a NAME fallback
#   layer_name: the layer's name as its service states it
#   serving_until: (us-house only) the date the members elected from this
#               map leave office, after which the build refuses
#   out:        the data/app file index.html fetches for this layer
#   count:      the real district count; the build refuses any other
LAYERS = {
    "us-house": {
        # LAYER 4, THE 119TH CONGRESS, until the members elected from it leave
        # office. Layer 0 is the new map the 2026 election used. See the
        # docstring.
        "url": TIGERWEB + "/4",
        "fields": ["CD119", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "119th Congressional Districts",
        "serving_until": "2027-01-03",
        "out": "congress-districts.json",
        "count": 15,  # 15 Ohio congressional districts
    },
    "oh-senate": {
        "url": TIGERWEB + "/1",
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "2026 State Legislative Districts - Upper",
        "out": "oh-senate-districts.json",
        "count": 33,  # 33 Ohio Senate districts
    },
    "oh-house": {
        "url": TIGERWEB + "/2",
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "2026 State Legislative Districts - Lower",
        "out": "oh-house-districts.json",
        "count": 99,  # 99 Ohio House districts
    },
}
SIMPLIFY = ["dp", "keep-shapes", "interval=5"]
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live
VALIDATION_KEY = "GEOID"  # unique per district, preserved through simplification

# 8 m, PINNED rather than recomputed each run: the ceiling
# build_state_counties.py holds the county file to, and the setting Adam chose
# for Mississippi's maps before that instance opened ("Finer first",
# 2026-10-16). Every run prints the measured median source step beside this
# value, because a ceiling derived from the source each run can never fail —
# it rises whenever the source gets coarser.
FIDELITY_CEILING_M = 8.0

# Senate district -> the three House districts that make it up, read from
# TIGER's 2026 layers on 2026-11-11 (see the docstring). The build re-proves
# it against the source before writing, so a stale table refuses rather than
# shipping.
NESTING_UPPER, NESTING_LOWER = "oh-senate", "oh-house"
NESTING_TRIPLETS = {
    1: (81, 82, 83), 2: (44, 75, 89), 3: (5, 10, 12), 4: (45, 46, 47),
    5: (39, 40, 80), 6: (36, 37, 38), 7: (28, 55, 56), 8: (27, 29, 30),
    9: (24, 25, 26), 10: (70, 71, 74), 11: (41, 42, 43), 12: (78, 84, 85),
    13: (52, 53, 54), 14: (62, 63, 90), 15: (1, 2, 3), 16: (4, 8, 11),
    17: (91, 92, 93), 18: (19, 23, 57), 19: (60, 61, 98), 20: (68, 69, 73),
    21: (18, 21, 22), 22: (66, 67, 76), 23: (13, 16, 20), 24: (14, 15, 17),
    25: (6, 7, 9), 26: (86, 87, 88), 27: (31, 35, 72), 28: (32, 33, 34),
    29: (48, 49, 50), 30: (94, 95, 96), 31: (51, 77, 97), 32: (64, 65, 99),
    33: (58, 59, 79),
}


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
                        label="oh-build-legislative-boundaries")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer (CLAUDE.md): read the key, never a
        # default that turns the error object into "no features".
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def fetch_layer(name, cfg, url=None, fields=None):
    """Every Ohio feature of the layer, as GeoJSON."""
    params = {"where": "STATE='%s'" % OH_FIPS,
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
    congressional map whose members have left office. TIGERweb renumbers its
    layers when a vintage rolls, so the index alone proves nothing."""
    got = _layer_name(cfg["url"])
    if got != cfg["layer_name"]:
        raise RuntimeError(
            "%s: %s is now %r, not %r — find the layer that is, and refuse "
            "rather than draw a different map" % (name, cfg["url"], got, cfg["layer_name"]))
    today = today or datetime.date.today().isoformat()
    if "serving_until" in cfg and today >= cfg["serving_until"]:
        raise RuntimeError(
            "%s: the members elected in 2024 from %r left office on %s. Switch "
            "this entry to layer 0 and CD120, the map the 2026 election used, "
            "and set a new serving_until" % (name, cfg["layer_name"], cfg["serving_until"]))


def run_mapshaper_family(source_paths, out_dir):
    """Simplify EVERY map in one run, so a shared edge is one arc.

    `combine-files` reads the inputs into a single dataset, which is what
    makes mapshaper dedupe an edge two layers both draw into ONE arc;
    simplification then removes the same vertices from it for both.
    `target=*` writes every layer back out, one file per input, each keeping
    its own fields, named after the input base names.
    """
    subprocess.run(
        ["npx", "-y", MAPSHAPER] + list(source_paths) + ["combine-files",
         "-simplify"] + SIMPLIFY + [
         "-o", "precision=" + PRECISION, "format=geojson", "target=*", out_dir],
        check=True, cwd=REPO_ROOT,
    )


# --- the cross-layer gate: no geometry library, no network ------------------
def _vertex_set(geom):
    return {(pt[0], pt[1]) for ring in _rings_of(geom) for pt in ring}


def _by_number(features):
    out = {}
    for f in features:
        key = (f["properties"].get("BASENAME") or "").strip()
        if key.isdigit():
            out[int(key)] = f
    return out


def check_triplet_table():
    """The table itself: 33 triplets covering House 1..99 exactly once each."""
    seen = [h for trio in NESTING_TRIPLETS.values() for h in trio]
    if sorted(NESTING_TRIPLETS) != list(range(1, LAYERS[NESTING_UPPER]["count"] + 1)):
        return False, "NESTING_TRIPLETS does not name every Senate district once"
    if sorted(seen) != list(range(1, LAYERS[NESTING_LOWER]["count"] + 1)):
        return False, "NESTING_TRIPLETS does not name every House district exactly once"
    return True, "table names 33 Senate districts and 99 House districts once each"


def check_nesting(maps, what):
    """Every Senate boundary vertex must be a vertex of its own three House
    districts. On the source this proves the table; on the shipped files it
    proves the three maps came off one topology. Exact, no tolerance."""
    ok, msg = check_triplet_table()
    if not ok:
        return False, msg
    up = _by_number(maps[NESTING_UPPER]["features"])
    lo = _by_number(maps[NESTING_LOWER]["features"])
    problems = []
    for senate, trio in sorted(NESTING_TRIPLETS.items()):
        if senate not in up:
            problems.append("Senate %d is missing from the %s" % (senate, what))
            continue
        missing = [h for h in trio if h not in lo]
        if missing:
            problems.append("House %s missing from the %s" % (missing, what))
            continue
        child = set()
        for h in trio:
            child |= _vertex_set(lo[h]["geometry"])
        stray = _vertex_set(up[senate]["geometry"]) - child
        if stray:
            problems.append(
                "Senate %d has %d vertex/vertices on none of House %s"
                % (senate, len(stray), " + ".join(str(h) for h in trio)))
    if problems:
        return False, "%d of 33 Senate districts broken in the %s; first: %s" % (
            len(problems), what, problems[0])
    return True, "33 of 33 Senate districts share every boundary vertex with their three House districts (%s)" % what


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


def build_family():
    """Fetch every map, simplify them as ONE topology, gate, then write."""
    source = {}
    for name, cfg in LAYERS.items():
        check_serving_map(name, cfg)
        source[name] = fetch_layer(name, cfg)
        if len(source[name]["features"]) != cfg["count"]:
            raise RuntimeError("%s: fetched %d features, expected exactly %d"
                               % (name, len(source[name]["features"]), cfg["count"]))

    # gate 0: the source holds the pinned table
    ok, msg = check_nesting(source, "TIGER source")
    if not ok:
        raise RuntimeError("nesting table does not match the source: %s — "
                           "re-read NESTING_TRIPLETS from TIGER" % msg)
    print("  nesting    %s" % msg, file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, geo in source.items():
            sp = os.path.join(tmp, name + ".geojson")
            with open(sp, "w") as f:
                json.dump(geo, f)
            paths.append(sp)
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir)
        run_mapshaper_family(paths, out_dir + os.sep)
        built = {}
        for name in source:
            op = os.path.join(out_dir, name + ".json")
            if not os.path.exists(op):
                raise RuntimeError(
                    "%s: mapshaper wrote no output for this map (looked for %s) — "
                    "combine-files names outputs after the inputs" % (name, op))
            with open(op) as f:
                built[name] = json.load(f)

    for name, cfg in LAYERS.items():
        n = len(built[name]["features"])
        if n != cfg["count"]:
            raise RuntimeError("%s: %d features after simplify (expected exactly %d) "
                               "— refusing to write" % (name, n, cfg["count"]))

    # gate 1, per map: the project's point-in-district protocol vs the fetch
    for name in LAYERS:
        ok, msg = validate(source[name]["features"], built[name]["features"], VALIDATION_KEY)
        if not ok:
            raise RuntimeError("%s validation failed: %s" % (name, msg))
        print("  %-10s %s" % (name, msg), file=sys.stderr)

    # gate 2, across maps: the nesting the constitution requires
    ok, msg = check_nesting(built, "simplified files")
    if not ok:
        raise RuntimeError("nesting check failed: %s" % msg)
    print("  nesting    %s" % msg, file=sys.stderr)

    # gate 3, against the source: how far the true line strays from the drawn one
    for name in LAYERS:
        step = median_source_step_m(source[name]["features"])
        worst, over = check_fidelity(source[name]["features"], built[name]["features"],
                                     VALIDATION_KEY)
        if over:
            raise RuntimeError(
                "%s: %d district(s) stray past the %.0f m fidelity ceiling (worst %.1f m): "
                "%s — refusing to write" % (name, len(over), FIDELITY_CEILING_M, worst,
                                            ", ".join(sorted(over)[:5])))
        print("  %-10s median source step %.2f m, worst stray %.1f m against a %.0f m "
              "ceiling, 0 of %d districts over" % (name, step, worst, FIDELITY_CEILING_M,
                                                    len(built[name]["features"])),
              file=sys.stderr)

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    for name, cfg in LAYERS.items():
        compact = json.dumps(built[name], separators=(",", ":"))
        if json.loads(compact) != built[name]:
            raise RuntimeError("%s round-trip mismatch before writing" % name)
        with open(os.path.join(APP_DATA_DIR, cfg["out"]), "w") as f:
            f.write(compact)
        print("%s -> data/app/%s: %d districts, %d bytes (%s, 6dp)"
              % (name, cfg["out"], len(built[name]["features"]), len(compact),
                 " ".join(SIMPLIFY)), file=sys.stderr)
    print("REMEMBER: these are CACHE-FIRST files. Bump `cache_name` in "
          "metro-worksheet.json and re-run generate_metro_files.py, or a "
          "returning visitor keeps the old geometry.", file=sys.stderr)


def check_shipped():
    """Offline: the nesting gate on the files in data/app. This is the CI gate.

    It needs no network, because the nesting is a relation BETWEEN two shipped
    maps — exactly the regression a per-chamber rebuild would reintroduce. The
    fidelity gate needs the TIGER fetch, so it is build-time only."""
    maps = {}
    for name in (NESTING_UPPER, NESTING_LOWER):
        path = os.path.join(APP_DATA_DIR, LAYERS[name]["out"])
        if not os.path.exists(path):
            print("oh-build-legislative-boundaries: FAIL — %s is missing"
                  % LAYERS[name]["out"], file=sys.stderr)
            return 1
        with open(path) as f:
            maps[name] = json.load(f)
    ok, msg = check_nesting(maps, "shipped files")
    if not ok:
        print("oh-build-legislative-boundaries: FAIL — %s\n"
              "  Rebuild the WHOLE family (python3 oh/scripts/build_legislative_boundaries.py); "
              "simplifying one chamber alone is what breaks this." % msg, file=sys.stderr)
        return 1
    print("oh-build-legislative-boundaries: OK — %s" % msg)
    return 0


def main():
    args = sys.argv[1:]
    if args == ["--check"]:
        sys.exit(check_shipped())
    if args:
        print("unexpected argument(s): %s\n"
              "This builder has no per-chamber mode: rebuilding one chamber alone is "
              "what breaks the House/Senate nesting, so the family is the unit.\n"
              "  (no args) fetch and rebuild all three\n"
              "  --check   offline nesting gate on the shipped files" % args,
              file=sys.stderr)
        sys.exit(1)
    build_family()


if __name__ == "__main__":
    main()
