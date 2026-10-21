#!/usr/bin/env python3
"""
Build the pre-simplified Missouri congressional and legislative-district
boundary files in data/app/, so the app fetches them same-origin (cache-first)
instead of downloading full statewide geometry live on every first toggle.

Statewide, like the Illinois reference and every newer state: Missouri's
instance answers anywhere in the state, so each map ships whole — fetch ->
simplify -> validate -> write data/app/<file>. No clip step: the served area
IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS (congress-roster,
mo-senate-members, mo-house-members) are separate; only the geometry is here.

DEFAULT_TARGETS DELIBERATELY INCLUDES us-house: there is no bootstrap step that
writes congress-districts.json, so skipping it by default would ship no file.

THE CONGRESSIONAL MAP IS THE 2022 MAP, FROM TIGERweb LAYER 4 (THE 119TH
CONGRESS), AND IT DOES NOT SWITCH ON 3 JANUARY 2027 THE WAY LOUISIANA'S AND
TENNESSEE'S DO. Missouri's legislature passed a new congressional map in
September 2025; a referendum petition froze it, and the U.S. Supreme Court's
order of 25 September 2026 kept the 3 November 2026 election on the 2022 map
(St. Louis Public Radio, 2026-09-25). So the members seated on 3 January 2027
are elected from the 2022 map too, and serve until 3 January 2029. TIGERweb's layer 0, "120th Congressional Districts", already
carries the frozen 2025 map for Missouri: measured 2026-10-21 against layer 4
in an equal-area projection, Kansas City's 5th District grows from 1,118 to
21,546 square kilometres there and the 3rd District keeps only 27.49% of its
ground. Drawing layer 0 would name the wrong member across most of the state
for the whole of the 120th Congress. Layer 4 matches the state's own current
congressional map (gis.mo.gov LEGIS/CongressHouseDistricts, which names the
sitting members). check_serving_map refuses if layer 4 stops being the 119th
Congress's map, since TIGERweb renumbers its layers when a vintage rolls, and
refuses on or after 3 January 2029, when the members elected on the 2022 map
leave office: the referendum on the 2025 map is on the 3 November 2026 ballot,
and if voters keep it, the 2028 election is the first held on it, so a person
has to re-read which map the 121st Congress was elected from before anything
is drawn.

THE TWO CHAMBERS COME FROM THE STATE'S OWN MAPS, NOT TIGERweb's, AND THAT IS A
MEASUREMENT. Both are the 2022 apportionment plans: the Senate's filed by the
Judicial Redistricting Commission, the House's by the House Independent
Bipartisan Citizens Commission, both staffed by the Office of Administration's
redistricting office. That office publishes each plan as a shapefile
(budplan.oa.mo.gov) and as a map service (gis.mo.gov LEGIS
StateSenateDistricts layer 2 and StateHouseDistricts layer 0, credited
"Missouri Office of Administration, Division of Budget and Planning,
Redistricting Office"). Measured 2026-10-21 against the filed shapefiles, in
an equal-area projection, district by district:

    Senate   state map   99.9977% of the plan's area in the same district,
                         lowest district IoU 0.9995 (District 4)
             TIGERweb    99.9954%, lowest IoU 0.99078 (District 13)
    House    state map   99.9954%, lowest IoU 0.99851 (District 78)
             TIGERweb    99.9938%, lowest IoU 0.97332 (District 135)

The largest disagreement is in Springfield: about 1.45 square kilometres
around -93.2005, 37.2529 that the filed plan and the state's map put in House
District 131 and TIGERweb puts in 135. So the state's map is drawn, and its
residue against the filing is spread thinly along every edge rather than
moving any block between districts. The member names and web links the state's
layers carry are dropped: the rosters are built from the chambers' own pages,
and a second copy of a name in a geometry file is a second source that can
disagree. Each feature is written with TIGERweb's field names (SLDU or SLDL,
NAME, BASENAME, GEOID, STATE), which the app's extractDistrictNumber already
reads.

The 2022 plans are in force until the plans drawn after the 2030 census, so
the chambers carry no date guard; check_state_layer refuses if a layer stops
being the redistricting office's own, or if the Senate layer stops describing
the 2022 plan, so a replacement is read by a person before it is drawn.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
Adam chose for Mississippi's maps before that instance opened ("Finer first",
2026-10-16) and Louisiana's builder carries. Visvalingam thresholds triangle
AREA, which does not bound how far the drawn line strays from the true one,
because successive below-threshold removals compound; Douglas-Peucker
thresholds the stray itself. Every build prints the worst stray against the
ceiling.

THE INTERVAL IS ABSOLUTE METRES, WHICH IS WHY EACH MAP IS SIMPLIFIED ON ITS OWN
HERE. Illinois had to put all three chambers through ONE mapshaper topology,
because two Illinois House districts make up one Senate district and a shared
edge survives identically only if both came off one topology. Missouri has no
such rule (163 House against 34 Senate districts is not a nesting ratio), so a
per-map run is safe in a way it would NOT be under a retain PERCENTAGE, which
is relative to the whole dataset's vertex count.

Prerequisites: requests, and Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 mo/scripts/build_legislative_boundaries.py             # all three
    python3 mo/scripts/build_legislative_boundaries.py mo-senate   # one map
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
STATE_GIS = "https://gis.mo.gov/arcgis/rest/services/LEGIS"
MO_FIPS = "29"
REDISTRICTING_OFFICE = "Redistricting Office"
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/mo/)"}
REQUEST_TIMEOUT = 300

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -96.0, "minLat": 35.8, "maxLng": -88.9, "maxLat": 40.8}

# map -> how to build data/app/<out>.
#   source:     "tiger" (TIGERweb Legislative, filtered to Missouri) or "state"
#               (the redistricting office's own map service, Missouri only)
#   url:        the layer
#   fields:     (tiger) outFields kept — the app's extractDistrictNumber reads
#               CD119 directly, with a NAME fallback
#   layer_name: the layer's name as its service states it
#   serving_until: (us-house only) the date the members it was drawn for leave
#               office
#   number_field, district_field, label: (state) the state's own district
#               number field, and the TIGERweb field name and NAME pattern each
#               feature is written with
#   description_must_contain: (state, optional) a phrase the layer's own
#               description must still carry
#   out:        the data/app file index.html fetches for this layer
#   simplify:   mapshaper Douglas-Peucker interval in METRES (keep-shapes)
#   count:      the real district count; the build refuses any other
LAYERS = {
    "us-house": {
        # LAYER 4, THE 119TH CONGRESS: the 2022 map, which also elects the
        # 120th Congress in Missouri. See the docstring.
        "source": "tiger",
        "url": TIGERWEB + "/4",
        "fields": ["CD119", "NAME", "BASENAME", "GEOID", "STATE"],
        "layer_name": "119th Congressional Districts",
        "serving_until": "2029-01-03",
        "out": "congress-districts.json",
        "simplify": "interval=5",
        "count": 8,  # 8 Missouri congressional districts
    },
    "mo-senate": {
        "source": "state",
        "url": STATE_GIS + "/StateSenateDistricts/MapServer/2",
        "layer_name": "State Senate Boundaries",
        "description_must_contain": "Apportionment Plan 2022",
        "number_field": "District",
        "district_field": "SLDU",
        "label": "State Senate District %d",
        "out": "mo-senate-districts.json",
        "simplify": "interval=5",
        "count": 34,  # 34 Missouri Senate districts
    },
    "mo-house": {
        "source": "state",
        "url": STATE_GIS + "/StateHouseDistricts/MapServer/0",
        "layer_name": "State House Boundaries",
        "number_field": "District",
        "district_field": "SLDL",
        "label": "State House District %d",
        "out": "mo-house-districts.json",
        "simplify": "interval=5",
        "count": 163,  # 163 Missouri House districts
    },
}
DEFAULT_TARGETS = ["us-house", "mo-senate", "mo-house"]  # all three — see docstring
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
                        label="mo-build-legislative-boundaries")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer (CLAUDE.md): read the key, never a
        # default that turns the error object into "no features".
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def fetch_layer(name, cfg):
    """Every Missouri feature of the layer, as GeoJSON."""
    if cfg["source"] == "tiger":
        params = {"where": "STATE='%s'" % MO_FIPS, "outFields": ",".join(cfg["fields"])}
    else:
        params = {"where": "1=1", "outFields": cfg["number_field"]}
    params.update({"returnGeometry": "true", "outSR": "4326",
                   "geometryPrecision": "6", "f": "geojson"})
    geo = _get_json(cfg["url"] + "/query", params)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("%s: %s returned no features" % (name, cfg["url"]))
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("%s: %s hit the transfer cap — needs paging" % (name, cfg["url"]))
    return geo


def check_serving_map(name, cfg, today=None):
    """Refuse a layer that no longer carries the map it was chosen for, and a
    congressional map whose members have left office. TIGERweb renumbers its
    layers when a vintage rolls, so the index alone proves nothing."""
    info = _get_json(cfg["url"], {"f": "json"})
    got = info.get("name", "")
    if got != cfg["layer_name"]:
        raise RuntimeError(
            "%s: %s is now %r, not %r — find the layer that is, and refuse "
            "rather than draw a different map" % (name, cfg["url"], got, cfg["layer_name"]))
    if cfg["source"] == "state":
        credit = info.get("copyrightText") or ""
        if REDISTRICTING_OFFICE not in credit:
            raise RuntimeError(
                "%s: %s is credited %r, not to the Office of Administration's "
                "redistricting office — re-read where it comes from before "
                "drawing it" % (name, cfg["url"], credit))
        phrase = cfg.get("description_must_contain")
        if phrase and phrase not in (info.get("description") or ""):
            raise RuntimeError(
                "%s: %s no longer describes itself as the %s — a new plan? Re-read "
                "it before drawing it" % (name, cfg["url"], phrase))
    if "serving_until" in cfg:
        today = today or datetime.date.today().isoformat()
        if today >= cfg["serving_until"]:
            raise RuntimeError(
                "%s: the members elected on Missouri's 2022 map left office on %s. "
                "If voters kept the 2025 map on 3 November 2026, the 2028 election "
                "was held on it: re-read which map the sitting members were "
                "elected from, then change this entry" % (name, cfg["serving_until"]))


def normalize_state(name, cfg, geo):
    """Write each state feature with TIGERweb's field names, and refuse unless
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
            "GEOID": MO_FIPS + code,
            "STATE": MO_FIPS,
        }
    want = set(range(1, cfg["count"] + 1))
    if set(seen) != want:
        raise RuntimeError(
            "%s: districts %s missing and %s unexpected — refusing to write"
            % (name, sorted(want - set(seen)), sorted(set(seen) - want)))
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
    if cfg["source"] == "state":
        source = normalize_state(name, cfg, source)

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
