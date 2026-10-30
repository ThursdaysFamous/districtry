#!/usr/bin/env python3
"""
Build the pre-simplified Georgia congressional and legislative-district
boundary files in data/app/, so the app fetches them same-origin (cache-first)
instead of downloading statewide geometry on every first toggle.

Statewide, like every newer state: Georgia's instance answers anywhere in the
state, so each map ships whole — fetch -> simplify -> validate -> write
data/app/<file>. No clip step: the served area IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS (congress-roster,
ga-senate-members, ga-house-members) are separate; only the geometry is here.

THE THREE MAPS ARE THE PLANS THE GENERAL ASSEMBLY ENACTED IN DECEMBER 2023,
AS ITS OWN REAPPORTIONMENT OFFICE PUBLISHES THEM, NOT THE CENSUS BUREAU'S
COPIES, AND THAT IS A MEASUREMENT. The Legislative and Congressional
Reapportionment Office (www.legis.ga.gov/joint-office/reapportionment) lists
each enacted plan under "2023 Maps" with a shapefile: the House "As passed
Dec. 5, 2023" (House Bill 1EX), the Senate "As passed Dec. 5, 2023" (Senate
Bill 1EX) and Congress "As passed Dec. 7, 2023" (Senate Bill 3EX). Measured
2026-10-29 against TIGERweb's copies, in an equal-area projection, district
by district:

    Congress  TIGERweb layers 0 and 4   99.9944% of the plan's area in the same
                                        district, lowest IoU 0.99813 (District 7)
    Senate    TIGERweb 2026 and 2024    99.9959%, lowest IoU 0.99563 (District 38)
    House     TIGERweb 2026 and 2024    99.9925%, lowest IoU 0.99169 (District 63)

TIGERweb's two editions of each map agree with each other. The difference
from the plans is not drafting: the largest piece, about 3.9 km2 around
34.7323, -83.9354, is land the plans put in Lumpkin County's districts (House
9, Congress 7) and TIGERweb in Union County's (House 8, Congress 9), because
the Census Bureau's current county line there is not its 2020 one (TIGERweb's
Census2020 county layer names Lumpkin at that point, its current layer
Union). The acts settle which is the law: "Whenever the description of any
house district refers to a named county without any additional VTD, it shall
mean the geographical boundaries of that county as shown on the census maps
for the United States decennial census of 2020 for the State of Georgia"
(House Bill 1EX, 2023, section 3(b)(2); the Senate and congressional acts say
the same of their districts). The plans are drawn on that 2020 geography, so
they are drawn here.

THE CONGRESSIONAL MAP IS THE 2023 MAP FOR THE 120TH CONGRESS TOO. Governor
Kemp called a special session for 17 June 2026 to redraw for 2028, and its
leaders declined to take up any map (WABE and Newsweek, 17-18 June 2026), so
the 3 November 2026 election uses the 2023 map, and TIGERweb's layers 0
(120th Congress) and 4 (119th) carry the same 14 districts for Georgia,
measured 2026-10-29. A redraw for 2028 is still possible, so the us-house
entry carries a date after which it refuses to build until a person re-reads
which map the sitting members were elected from.

The office's file URLs carry a version (sfvrsn) and are pinned here with the
SHA-256 of each zip as fetched on 2026-10-29. A changed file stops the build:
read the office's page again, then change the pin. The office's page itself
is read through the token the page hands every visitor (see
build_ga_legislature_roster.py) only by --check-listing, which confirms each
pinned file is still listed under the plan it was chosen as.

Each feature is written with TIGERweb's field names (CD119, SLDU or SLDL,
NAME, BASENAME, GEOID, STATE), which the app's extractDistrictNumber already
reads. The plans' population and demographic columns are not carried.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
Adam chose for Mississippi's maps ("Finer first", 2026-10-16) and Missouri's
and Louisiana's builders carry. Visvalingam thresholds triangle AREA, which
does not bound how far the drawn line strays from the true one; Douglas-Peucker
thresholds the stray itself. Every build prints the worst stray against the
ceiling. Georgia has no rule nesting House districts in Senate districts, so
each map is simplified on its own, which is safe under an absolute interval.

Prerequisites: requests, pyshp, and Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ga/scripts/build_legislative_boundaries.py             # all three
    python3 ga/scripts/build_legislative_boundaries.py ga-senate   # one map
    python3 ga/scripts/build_legislative_boundaries.py --check-listing
"""

import datetime
import hashlib
import io
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
OFFICE = ("https://www.legis.ga.gov/api/document/docs/default-source/"
          "reapportionment-document-library/")
GA_FIPS = "13"
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/ga/)"}
REQUEST_TIMEOUT = 300

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -85.8, "minLat": 30.2, "maxLng": -80.6, "maxLat": 35.2}

# map -> how to build data/app/<out>.
#   url:         the office's shapefile zip, version-pinned
#   sha256:      the zip as fetched on 2026-10-29
#   listed_as:   the plan title the office's page lists the file under
#   district_field, label, geoid_width: the TIGERweb field name, NAME pattern
#                and GEOID digits each feature is written with
#   serving_until: (us-house only) refuse on or after this date
#   out:         the data/app file index.html fetches for this layer
#   simplify:    mapshaper Douglas-Peucker interval in METRES (keep-shapes)
#   count:       the real district count; the build refuses any other
LAYERS = {
    "us-house": {
        "url": OFFICE + "congress/congress-2023-shape.zip?sfvrsn=d3bedfe3_4",
        "sha256": "38336c111890bee8c747e4cbc92d655065ebd37b48c07951558bcf53ea06ae92",
        "listed_as": "Congressional Districts- As passed Dec. 7, 2023- Senate Committee Chair- Senate Bill 3EX",
        "district_field": "CD119",
        "label": "Congressional District %d",
        "geoid_width": 2,
        # The members elected in November 2026 on this map sit until
        # 3 January 2029; a 2028 map would first be elected in November 2028.
        "serving_until": "2029-01-03",
        "out": "congress-districts.json",
        "simplify": "interval=5",
        "count": 14,
    },
    "ga-senate": {
        "url": OFFICE + "senate/senate-2023-shape-file.zip?sfvrsn=b47bc9d0_2",
        "sha256": "ec0fe3646ee7276b9b512a02338091a8df63d3234feda7ff2342ddf45c69baee",
        "listed_as": "Senate Districts- As passed Dec. 5, 2023- Senate Committee Chair- Senate Bill 1EX",
        "district_field": "SLDU",
        "label": "State Senate District %d",
        "geoid_width": 3,
        "out": "ga-senate-districts.json",
        "simplify": "interval=5",
        "count": 56,
    },
    "ga-house": {
        "url": OFFICE + "house/house-2023-shape.zip?sfvrsn=b0126893_2",
        "sha256": "f91f4be57d3510b33e49b1a09023bba577b5f5d93be5fb13f203b2047752e0ea",
        "listed_as": "House Districts- As passed Dec. 5, 2023- House Committee Chair- House Bill 1EX",
        "district_field": "SLDL",
        "label": "State House District %d",
        "geoid_width": 3,
        "out": "ga-house-districts.json",
        "simplify": "interval=5",
        "count": 180,
    },
}
DEFAULT_TARGETS = ["us-house", "ga-senate", "ga-house"]
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
    """A TIGERweb query (build_state_counties.py reads the county layer through
    here): robots.txt read first, an API error raised rather than read as an
    empty answer."""
    import requests  # noqa: PLC0415 (only the fetching path needs it)
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="ga-build-legislative-boundaries")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer (CLAUDE.md): read the key, never a
        # default that turns the error object into "no features".
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def _get_bytes(url):
    import requests  # noqa: PLC0415
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="ga-build-legislative-boundaries")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.content


def check_serving(name, cfg, today=None):
    if "serving_until" in cfg:
        today = today or datetime.date.today().isoformat()
        if today >= cfg["serving_until"]:
            raise RuntimeError(
                "%s: the members elected on Georgia's 2023 map leave office on %s. "
                "Re-read which map the sitting members were elected from (the "
                "General Assembly may have redrawn for 2028), then change this "
                "entry" % (name, cfg["serving_until"]))


def fetch_plan(name, cfg):
    """Every district of the plan's shapefile, as GeoJSON with TIGERweb's
    field names, refusing unless the districts are exactly 1..count."""
    import shapefile  # noqa: PLC0415 (pyshp; only the fetching path needs it)
    body = _get_bytes(cfg["url"])
    digest = hashlib.sha256(body).hexdigest()
    if cfg["sha256"] and digest != cfg["sha256"]:
        raise RuntimeError(
            "%s: the office's file now hashes %s, not the pinned %s — read the "
            "office's page again (--check-listing) before drawing a changed plan"
            % (name, digest, cfg["sha256"]))
    zf = zipfile.ZipFile(io.BytesIO(body))
    stems = sorted({n[:-4] for n in zf.namelist() if n.lower().endswith(".shp")})
    if len(stems) != 1:
        raise RuntimeError("%s: the zip holds %d shapefiles, not one" % (name, len(stems)))
    stem = stems[0]
    prj = zf.read(stem + ".prj").decode("latin-1")
    if "GCS_North_American_1983" not in prj:
        raise RuntimeError("%s: the shapefile is not in NAD83 longitude/latitude (%s)"
                           % (name, prj[:80]))
    reader = shapefile.Reader(shp=io.BytesIO(zf.read(stem + ".shp")),
                              shx=io.BytesIO(zf.read(stem + ".shx")),
                              dbf=io.BytesIO(zf.read(stem + ".dbf")))
    seen = {}
    feats = []
    for sr in reader.iterShapeRecords():
        raw = sr.record["DISTRICT"]
        try:
            n = int(str(raw).strip())
        except ValueError:
            raise RuntimeError("%s: a feature carries district %r, not a number" % (name, raw))
        if n in seen:
            raise RuntimeError("%s: district %d appears twice" % (name, n))
        seen[n] = True
        code = str(n).zfill(cfg["geoid_width"])
        feats.append({"type": "Feature",
                      "properties": {cfg["district_field"]: code,
                                     "NAME": cfg["label"] % n,
                                     "BASENAME": str(n),
                                     "GEOID": GA_FIPS + code,
                                     "STATE": GA_FIPS},
                      "geometry": sr.shape.__geo_interface__})
    want = set(range(1, cfg["count"] + 1))
    if set(seen) != want:
        raise RuntimeError(
            "%s: districts %s missing and %s unexpected — refusing to write"
            % (name, sorted(want - set(seen)), sorted(set(seen) - want)))
    return {"type": "FeatureCollection", "features": feats}, digest


def check_listing():
    """Confirm every pinned file is still listed under the plan it was chosen
    as, on the office's own page (read with the token the page hands every
    visitor)."""
    import build_ga_legislature_roster as roster  # noqa: PLC0415 (same instance tree)
    page = roster.api("Reapportionment/Page")
    found = {}

    def walk(node, trail):
        title = node.get("cmsTitle") or node.get("title") or ""
        url = node.get("url") or ""
        for cfg_name, cfg in LAYERS.items():
            if url and url.split("?")[0] == cfg["url"].split("?")[0]:
                found.setdefault(cfg_name, []).append((trail, url))
        for child in node.get("children") or []:
            walk(child, trail + [title])

    for tab in page.get("resourcesTab") or []:
        walk(tab, [])
    bad = []
    for cfg_name, cfg in LAYERS.items():
        hits = found.get(cfg_name, [])
        ok = [h for h in hits if cfg["listed_as"] in h[0] and h[1] == cfg["url"]]
        print("%s: listed %d time(s); under %r with this version: %s"
              % (cfg_name, len(hits), cfg["listed_as"], "yes" if ok else "NO"))
        if not ok:
            bad.append(cfg_name)
    if bad:
        raise SystemExit("FAIL: %s no longer listed as pinned" % ", ".join(bad))


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
    check_serving(name, cfg)
    source, digest = fetch_plan(name, cfg)
    print("%s: %s sha256 %s" % (name, cfg["url"].rsplit("/", 1)[1], digest))

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
    args = sys.argv[1:]
    if args == ["--check-listing"]:
        check_listing()
        return
    targets = args or DEFAULT_TARGETS
    unknown = [t for t in targets if t not in LAYERS]
    if unknown:
        print("unknown map(s): %s; known: %s" % (unknown, list(LAYERS)), file=sys.stderr)
        sys.exit(1)
    for name in targets:
        build_map(name, LAYERS[name])


if __name__ == "__main__":
    main()
