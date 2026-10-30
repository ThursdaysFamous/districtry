#!/usr/bin/env python3
"""
Build the pre-simplified West Virginia congressional and legislative-district
boundary files in data/app/, so the app fetches them same-origin (cache-first)
instead of downloading full statewide geometry live on every first toggle.

Statewide, like every newer state: West Virginia's instance answers anywhere
in the state, so each map ships whole — fetch -> simplify -> validate ->
write data/app/<file>. No clip step: the served area IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS (congress-roster,
wv-senate-members, wv-house-members) are separate; only the geometry is here.

THE CONGRESSIONAL MAP IS THE 2021 MAP, AND IT SERVES THE 120TH CONGRESS TOO.
West Virginia drew two districts in October 2021 (SB 3033) and has not drawn
them again. TIGERweb's layer 4 (the 119th Congress) and layer 0 (the 120th,
seated 3 January 2027) carry the same two districts for STATE='54': measured
2026-10-29 in an equal-area projection, each district's ground in the two
layers overlaps with an intersection-over-union of 1.0, and both match the
legislature's own published file of the plan (IoU 0.999998 and 1.0). So no
switch on 3 January 2027 is needed here, unlike Louisiana and Tennessee.
check_congress_editions refuses if the two layers ever stop carrying the same
districts for West Virginia (by GEOID and the Census's own land area), so a
redraw is read by a person before anything is drawn.

THE TWO CHAMBERS COME FROM THE LEGISLATURE'S OWN PUBLISHED PLANS, NOT
TIGERweb's, AND THAT IS A MEASUREMENT. The Senate's 17 districts (SB 3034)
and the House of Delegates' 100 (HB 301) were enacted in October 2021, and the
Legislature publishes each plan as a file (www.wvlegislature.gov/redistricting.cfm,
"SENATE MAP FINAL" and "HOUSE MAP FINAL", each as a shapefile and as JSON).
Measured 2026-10-29 in an equal-area projection, district by district, against
those files:

    Senate  state GIS centre's "WV Senate 2021"  99.9967% of the plan's area
                                                 in the same district, lowest
                                                 IoU 0.99981 (District 13)
            TIGERweb 2026 (layer 1)              99.9989%, lowest IoU 0.99992
    House   state GIS centre's "WV House 2021"   99.9933%, lowest IoU 0.99884
                                                 (District 79)
            TIGERweb 2026 (layer 2)              99.9900%, lowest IoU 0.91441
                                                 (District 70)

TIGERweb's 2024 and 2026 lower-chamber layers are identical to each other, and
both put about 1.4 km2 of Harrison County around Clarksburg in a different
district than the enacted plan and the state's own map do (around 39.2935,
-80.3345 TIGER says District 70 where the plan says 72, and around 39.2526,
-80.3862 TIGER says 70 where the plan says 69). So the plan is drawn, and the
state's GIS centre's map (services.wvgis.wvu.edu, Boundaries/WV_Election_Layers)
is read on every build as an independent witness: check_state_witness samples
the state envelope and refuses unless both agree on at least 99.5% of points.
The plan files carry population columns, which are dropped; each feature is
written with TIGERweb's field names (SLDU or SLDL, NAME, BASENAME, GEOID,
STATE), which the app's extractDistrictNumber already reads.

The Senate elects TWO senators from each of its 17 districts, in staggered
four-year terms, so the Senate roster carries two members per district
(build_wv_legislature_roster.py); the map does not change for that.

The 2021 plans are in force until the plans drawn after the 2030 census, so
the chambers carry no date guard; check_plan refuses if a plan file's district
set or feature count changes, so a replacement is read by a person before it
is drawn.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
Adam chose for Mississippi's maps before that instance opened ("Finer first",
2026-10-16) and the Louisiana and Missouri builders carry. Visvalingam
thresholds triangle AREA, which does not bound how far the drawn line strays
from the true one, because successive below-threshold removals compound;
Douglas-Peucker thresholds the stray itself. Every build prints the worst
stray against the ceiling.

THE INTERVAL IS ABSOLUTE METRES, WHICH IS WHY EACH MAP IS SIMPLIFIED ON ITS OWN
HERE. West Virginia's 100 delegate districts do not nest in its 17 Senate
districts (100 is not a multiple of 17), so a per-map run is safe in a way it
would NOT be under a retain PERCENTAGE, which is relative to the whole
dataset's vertex count.

Prerequisites: requests, and Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 wv/scripts/build_legislative_boundaries.py             # all three
    python3 wv/scripts/build_legislative_boundaries.py wv-senate   # one map
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
LEGISLATURE = "https://www.wvlegislature.gov/legisdocs/redistricting"
STATE_GIS = ("https://services.wvgis.wvu.edu/arcgis/rest/services/Boundaries/"
             "WV_Election_Layers/MapServer")
WV_FIPS = "54"
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/wv/)"}
REQUEST_TIMEOUT = 300

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -82.8, "minLat": 37.1, "maxLng": -77.6, "maxLat": 40.7}

# map -> how to build data/app/<out>.
#   source:     "tiger" (TIGERweb Legislative, filtered to West Virginia) or
#               "plan" (the Legislature's own published file of the enacted
#               plan, a zip holding one GeoJSON file)
#   url:        the layer, or the plan's zip
#   fields:     (tiger) outFields kept — the app's extractDistrictNumber reads
#               CD119 directly, with a NAME fallback
#   layer_name: (tiger) the layer's name as its service states it
#   twin:       (tiger) the other congressional edition that must carry the
#               same districts, and its name
#   number_field, district_field, label: (plan) the plan's own district
#               number field, and the TIGERweb field name and NAME pattern
#               each feature is written with
#   witness:    (plan) the state GIS centre's layer of the same plan, and its
#               name, read on every build as an independent check
#   out:        the data/app file index.html fetches for this layer
#   simplify:   mapshaper Douglas-Peucker interval in METRES (keep-shapes)
#   count:      the real district count; the build refuses any other
LAYERS = {
    "us-house": {
        # LAYER 4, THE 119TH CONGRESS, which carries the same two districts
        # as layer 0, the 120th. See the docstring.
        "source": "tiger",
        "url": TIGERWEB + "/4",
        "fields": ["CD119", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "119th Congressional Districts",
        "twin": (TIGERWEB + "/0", "120th Congressional Districts"),
        "out": "congress-districts.json",
        "simplify": "interval=5",
        "count": 2,  # 2 West Virginia congressional districts
    },
    "wv-senate": {
        "source": "plan",
        "url": LEGISLATURE + "/senate/datafiles/SENfinal_json.zip",
        "number_field": "District",
        "district_field": "SLDU",
        "label": "State Senate District %d",
        "witness": (STATE_GIS + "/21", "WV Senate 2021"),
        "out": "wv-senate-districts.json",
        "simplify": "interval=5",
        "count": 17,  # 17 Senate districts, two senators each
    },
    "wv-house": {
        "source": "plan",
        "url": LEGISLATURE + "/house/datafiles/HODfinal_json.zip",
        "number_field": "District",
        "district_field": "SLDL",
        "label": "Delegate District %d",
        "witness": (STATE_GIS + "/15", "WV House 2021"),
        "out": "wv-house-districts.json",
        "simplify": "interval=5",
        "count": 100,  # 100 single-member delegate districts
    },
}
DEFAULT_TARGETS = ["us-house", "wv-senate", "wv-house"]  # all three
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live
VALIDATION_KEY = "GEOID"  # unique per district, preserved through simplification

# 8 m, PINNED rather than recomputed each run: the ceiling
# build_state_counties.py holds the county file to, and the setting Adam chose
# for Mississippi's maps before that instance opened ("Finer first",
# 2026-10-16). Every run prints the measured median source step beside this
# value, because a ceiling derived from the source each run can never fail —
# it rises whenever the source gets coarser.
FIDELITY_CEILING_M = 8.0

# The share of sample points over the state envelope on which the plan and
# the state GIS centre's map must name the same district (or both none).
WITNESS_AGREEMENT_MIN = 99.5


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
                        label="wv-build-legislative-boundaries")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer (CLAUDE.md): read the key, never a
        # default that turns the error object into "no features".
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def _get_plan(url):
    """The Legislature's zip of one plan, read as the one GeoJSON file it
    holds. Nothing is written to disk."""
    import io  # noqa: PLC0415
    import zipfile  # noqa: PLC0415
    import requests  # noqa: PLC0415
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="wv-build-legislative-boundaries")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = [n for n in zf.namelist() if n.lower().endswith(".json")]
    if len(names) != 1:
        raise RuntimeError("%s holds %d JSON files, not one: %r" % (url, len(names), zf.namelist()))
    return json.loads(zf.read(names[0]).decode("utf-8"))


def _tiger_features(url, fields):
    params = {"where": "STATE='%s'" % WV_FIPS, "outFields": ",".join(fields),
              "returnGeometry": "true", "outSR": "4326",
              "geometryPrecision": "6", "f": "geojson"}
    geo = _get_json(url + "/query", params)
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("%s hit the transfer cap — needs paging" % url)
    return geo


def fetch_layer(name, cfg):
    """Every West Virginia feature of the layer, as GeoJSON."""
    if cfg["source"] == "tiger":
        geo = _tiger_features(cfg["url"], cfg["fields"])
    else:
        geo = _get_plan(cfg["url"])
        geo = {"type": "FeatureCollection", "features": geo.get("features") or []}
    if not geo.get("features"):
        raise RuntimeError("%s: %s returned no features" % (name, cfg["url"]))
    return geo


def check_serving_map(name, cfg):
    """Refuse a TIGERweb layer that no longer carries the map it was chosen
    for — TIGERweb renumbers its layers when a vintage rolls, so the index
    alone proves nothing — and refuse once the two congressional editions
    stop carrying the same West Virginia districts."""
    if cfg["source"] != "tiger":
        return
    info = _get_json(cfg["url"], {"f": "json"})
    got = info.get("name", "")
    if got != cfg["layer_name"]:
        raise RuntimeError(
            "%s: %s is now %r, not %r — find the layer that is, and refuse "
            "rather than draw a different map" % (name, cfg["url"], got, cfg["layer_name"]))
    twin_url, twin_name = cfg["twin"]
    twin = _get_json(twin_url, {"f": "json"})
    if twin.get("name", "") != twin_name:
        raise RuntimeError("%s: %s is now %r, not %r" % (name, twin_url, twin.get("name"), twin_name))
    sets = []
    for url in (cfg["url"], twin_url):
        geo = _get_json(url + "/query", {"where": "STATE='%s'" % WV_FIPS,
                                         "outFields": "GEOID,AREALAND",
                                         "returnGeometry": "false", "f": "json"})
        sets.append(sorted((f["attributes"]["GEOID"], f["attributes"]["AREALAND"])
                           for f in geo.get("features") or []))
    if not sets[0] or sets[0] != sets[1]:
        raise RuntimeError(
            "%s: %s and %s no longer carry the same West Virginia districts "
            "(%r against %r) — the state may have redrawn its map. Read which "
            "map the sitting members were elected from before drawing either"
            % (name, cfg["layer_name"], twin_name, sets[0], sets[1]))


def normalize_plan(name, cfg, geo):
    """Write each plan feature with TIGERweb's field names, and refuse unless
    the districts are exactly 1..count, each once."""
    seen = {}
    for f in geo["features"]:
        raw = (f.get("properties") or {}).get(cfg["number_field"])
        try:
            n = int(str(raw).split(".")[0])
        except ValueError:
            raise RuntimeError("%s: a feature carries district %r, not a number" % (name, raw))
        if n in seen:
            raise RuntimeError("%s: district %d appears twice" % (name, n))
        seen[n] = True
        code = "%03d" % n
        f["properties"] = {
            cfg["district_field"]: code,
            "NAME": cfg["label"] % n,
            "BASENAME": str(n),
            "GEOID": WV_FIPS + code,
            "STATE": WV_FIPS,
        }
    want = set(range(1, cfg["count"] + 1))
    if set(seen) != want:
        raise RuntimeError(
            "%s: districts %s missing and %s unexpected — refusing to write"
            % (name, sorted(want - set(seen)), sorted(set(seen) - want)))
    return geo


def check_state_witness(name, cfg, plan_features):
    """The state GIS centre's own map of the same plan, read as a witness:
    refuse unless it names the plan's district at WITNESS_AGREEMENT_MIN of
    the sample points over the state envelope."""
    url, layer_name = cfg["witness"]
    info = _get_json(url, {"f": "json"})
    if info.get("name", "") != layer_name:
        raise RuntimeError("%s: %s is now %r, not %r" % (name, url, info.get("name"), layer_name))
    geo = _get_json(url + "/query", {"where": "1=1", "outFields": "DISTRICT",
                                     "returnGeometry": "true", "outSR": "4326",
                                     "geometryPrecision": "6", "f": "geojson"})
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("%s: %s hit the transfer cap" % (name, url))
    witness = []
    for f in geo.get("features") or []:
        n = int(str((f.get("properties") or {}).get("DISTRICT")).split(".")[0])
        witness.append({"type": "Feature", "geometry": f["geometry"],
                        "properties": {"GEOID": WV_FIPS + "%03d" % n}})
    if not witness:
        raise RuntimeError("%s: %s returned no features" % (name, url))
    src = _model(plan_features, VALIDATION_KEY)
    wit = _model(witness, VALIDATION_KEY)
    rng = random.Random(54)
    agree = 0
    samples = 2000
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        a = _districts_at(src, pt)
        b = _districts_at(wit, pt)
        if sorted(set(a)) == sorted(set(b)):
            agree += 1
    pct = 100.0 * agree / samples
    if pct < WITNESS_AGREEMENT_MIN:
        raise RuntimeError("%s: the plan and the state GIS centre's %s agree at only "
                           "%.2f%% of points — refusing to write" % (name, layer_name, pct))
    print("%s: the plan and the state GIS centre's %s agree at %d/%d points (%.2f%%)"
          % (name, layer_name, agree, samples, pct))


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
    if cfg["source"] == "plan":
        source = normalize_plan(name, cfg, source)
        check_state_witness(name, cfg, source["features"])

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
