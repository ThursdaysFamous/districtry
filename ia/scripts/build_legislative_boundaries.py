#!/usr/bin/env python3
"""
Build the pre-simplified Iowa legislative-district boundary files in
data/app/ from Census TIGERweb, so the app fetches them same-origin
(cache-first) instead of downloading full statewide geometry live on every
first toggle.

Statewide, like the Illinois reference and Wisconsin: Iowa's instance
answers anywhere in the state, so each chamber ships whole — fetch ->
simplify -> validate -> write data/app/<chamber>-districts.json. No clip
step: the served area IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not
weekly CI — re-run it on redistricting. The officeholder ROSTERS
(ia-senate-members / ia-house-members, from Open States) are separate; only
the geometry is here (build_ia_legislature_roster.py builds those).

EVERY CHAMBER IS SIMPLIFIED IN ONE MAPSHAPER RUN, and both halves of that
sentence are load-bearing. Until 2026-09-26 each chamber was simplified on its
own file at its own retain percentage (congress 12%, senate 10%, house 9%), and
that broke a hierarchy TIGER guarantees exactly: two Iowa House districts make
up one Iowa Senate district (Iowa Code 42.3), so Senate N's outer edge IS the
outer edge of House 2N-1 + 2N. mapshaper builds topology WITHIN one file, so two
files simplified in separate runs cannot keep a shared edge identical. Measured
on the shipped files, full state: ALL FIFTY pairings had Senate vertices lying
on no House line, the worst pairing 93 of them. The SOURCE nests perfectly, so
every metre of that was introduced here. `combine-files` reads the inputs into
ONE dataset, which makes an edge two layers both draw into ONE arc simplified
once, and the nesting comes out exact again — 50 of 50.

AND THE ALGORITHM IS DOUGLAS-PEUCKER RATHER THAN VISVALINGAM, which is the other
half and is the half a shorter change would have missed. Visvalingam thresholds
triangle AREA, which does not bound how far the drawn line strays from the true
one: successive below-threshold removals compound, and that is precisely how a
boundary running as a STAIRCASE along a street grid gets replaced by a diagonal
chord cut across a city block through the houses. Sharing one topology does
NOTHING for that, measured on the full state at the old 10%: the nesting went
exact while the worst stray stayed 333 m and 146 of 154 districts were still
over 25 m — the two layers simply wrong together. Douglas-Peucker thresholds
perpendicular DEVIATION, so it spends vertices where deviation demands them
instead of where triangles happen to be large. Measured, full state:

    shape                                   nesting      worst stray   over 25 m   gzipped
    separate runs, Visvalingam (shipped)    50/50 broken     775.2 m   147 of 154  222,251
    ONE combine-files run, Visvalingam 10%   0/50 broken     333.2 m   146 of 154  226,266
    ONE combine-files run, dp interval=15    0/50 broken      19.1 m     0 of 154  229,918

THE COST IS STATED WITH ITS METHOD, BECAUSE THE TWO OBVIOUS COMPARISONS DISAGREE
IN SIGN AND ONE OF THEM IS CONFOUNDED. Holding the fetch fixed and changing only
the shape -- the table above, one source, one feature order -- the algorithm costs
+7,667 bytes gzipped, 222,251 -> 229,918, a real +3.4% spread over three files a
visitor fetches once and then holds cache-first. That buys a 40x fidelity
improvement and a hierarchy that is exact instead of broken on every pairing, so
it is the right trade, but it is a genuine 3.4% and the next reader should not
have to rediscover it. Illinois's three files came out 871 bytes SMALLER after
the same change, so DO NOT ASSUME A FLEET-WIDE SIGN: measure your own.

Comparing the files this change SHIPPED against the files it replaced answers
-4,433 bytes instead, and that number is not the algorithm's. TIGERweb returns
features in a server-determined order that varies between fetches, mapshaper
preserves it, and gzip compresses neighbouring districts better when they sit
next to each other in the array -- so the SAME geometry at the SAME settings
gzips 5,504 bytes differently for the Senate and 6,596 for the House depending
only on that order. Measured 2026-09-26: re-running the old settings on today's
fetch reproduces the shipped Senate file's raw length to the byte and 48 of its
50 districts' vertex sets exactly, while gzipping 5,504 bytes smaller, because
its features come back ascending where the shipped file's are scattered. THE
ORDER EFFECT IS LARGER THAN THE EFFECT BEING MEASURED, which is why the cost is
quoted from one fetch with the order held fixed, and why a before-and-after on
the committed files cannot be used for it.

A SMALL-INPUT TEST WILL TELL YOU THE COMBINE ALONE FIXED IT AND IT IS LYING.
mapshaper's retain percentage is relative to the WHOLE dataset's vertex count, so
three districts through combine-files keep far more detail per district than a
statewide run at the same percentage. Illinois measured a 4 m worst stray on
three districts against 331 m on the full state with identical settings. Every
figure in the table above is the FULL STATE, 154 districts, or it would be worth
nothing.

Three gates run before anything is written, and each answers a question the
others cannot:
  * validate()       -- per layer, the project's 2,000-random-point
                        point-in-district protocol over the state envelope,
                        against the pre-simplification fetch.
  * check_nesting()  -- ACROSS layers: every Senate boundary vertex must be a
                        vertex of its own two House districts, EXACTLY. Under a
                        shared topology the Senate ring is assembled FROM House
                        arcs, so this holds at zero tolerance -- there is no
                        epsilon to tune and no way for it to pass weakly.
                        Measured 2026-09-26: 50 of 50 together, 0 of 50 apart.
                        No geometry and no network, which is why --check runs it
                        in CI on the shipped files.
  * check_fidelity() -- against the SOURCE: no point on the true boundary may lie
                        further than FIDELITY_MAX_M from the line drawn for it.
                        Needs the fetch, so it is build-time only.
If any gate fails, nothing is written.

Property fields are trimmed to what the app reads so the file stays small: the
app's extractDistrictNumber() keys on SLDU/SLDL, or for congress the trailing
number of a NAME field; GEOID is kept as a stable per-feature key for validation.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js (mapshaper
via `npx mapshaper@<pinned>`).

Usage:
    python3 ia/scripts/build_legislative_boundaries.py           # fetch + rebuild all three
    python3 ia/scripts/build_legislative_boundaries.py --check   # offline: the nesting
                                                                 # gate on the SHIPPED files

THERE IS NO PER-CHAMBER BUILD ANY MORE, and that is the point rather than a
regression: rebuilding one chamber alone is exactly what breaks the nesting, so
an argument permitting it is a defect waiting to be re-introduced. The family is
the unit. `--check` needs no network and is the CI gate.
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
IA_FIPS = "19"

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -96.84, "minLat": 40.17, "maxLng": -89.94, "maxLat": 43.70}

# chamber -> how to build data/app/<out>.
#   layer:    TIGERweb Legislative MapServer layer index (0 US House, 1 upper, 2 lower)
#   fields:   outFields kept from TIGERweb. The app's extractDistrictNumber reads
#             SLDU/SLDL directly; congress uses the NAME fallback since TIGERweb
#             ships CD120, not a bare number.
#   out:      the data/app file index.html fetches for this layer
#   features: the exact district count — Iowa's fetch carries no water
#             pseudo-district (measured 2026-09-26: 4, 50 and 100 features
#             exactly), unlike Illinois's, whose counts are floors for that
#             reason. An exact guard is therefore the stronger one here.
#
# There is deliberately NO per-layer simplify setting: the whole family is
# simplified in ONE run at ONE setting (SIMPLIFY below), because a shared edge
# can only survive identically if both layers came off the same topology at the
# same threshold. Three percentages is what broke the nesting.
#
# us-house IS BUILT HERE, UNLIKE WISCONSIN'S SAME SCRIPT. Wisconsin's builder
# covers its two state chambers only, because its shipped congress-districts.json
# bytes originally came from the (now-deleted, R2.1) state-template bootstrap —
# there is no such bootstrap here, so congress-districts.json has no other
# producer and leaving it out would ship no file at all. It is also now part of
# the shared topology, so it could not be built separately even if it had one.
LAYERS = {
    "us-house": {
        "layer": 0,
        # CD120, not CD119: TIGERweb rolled its congressional layer to the
        # 120th Congress ("120th Congressional Districts; January 1, 2026
        # vintage"). The retired field is GONE, not deprecated, and the
        # service answers a query naming it with HTTP 200 carrying a JSON
        # error envelope -- {"error":{"code":400,...}} with no "features"
        # key -- so a status-code check reads it as success. This builder's
        # own no-features guard is what surfaces it, as
        # "returned no features": read that as "the vintage rolled".
        # Measured 2026-09-03.
        "fields": ["CD120", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "congress-districts.json",
        "features": 4,     # 4 Iowa congressional districts
    },
    "ia-senate": {
        "layer": 1,
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "ia-senate-districts.json",
        "features": 50,    # 50 Iowa Senate districts
    },
    "ia-house": {
        "layer": 2,
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "ia-house-districts.json",
        "features": 100,   # 100 Iowa House districts
    },
}
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live
VALIDATION_KEY = "GEOID"  # unique per district, preserved through simplification

# ONE simplification setting for the whole family. Douglas-Peucker with an
# absolute interval, not Visvalingam with a retain percentage — see the module
# docstring for the measurement. `interval` is a distance, so it means the same
# thing after a redistricting changes the vertex count, where a percentage does
# not.
SIMPLIFY = ["dp", "keep-shapes", "interval=15"]

# The fidelity ceiling, in metres: no point on the true boundary may lie further
# than this from the line drawn for it. MEASURED FROM IOWA'S OWN GEOMETRY, and
# it is NOT Illinois's 25 m — copying that number for consistency would set a
# ceiling calibrated on somebody else's city blocks.
#
# The quantity is the true line's own STAIRCASE STEP: how far it runs before it
# turns, where it is following a street grid, because a stray larger than one
# step is a chord cutting a corner off the real line. Measured structurally
# rather than from a list of places chosen by hand: a step is a segment whose
# turn to the next segment is a right angle (70-110 degrees), counted only in
# ~1 km cells holding at least twenty such turns, since one right angle is a
# field corner and twenty in a square kilometre is a grid. That gives a MEDIAN
# 43.4 m (ia-house) and 43.9 m (ia-senate) over 1,586 and 1,385 steps
# (2026-09-26), so 45 m is about one Iowa step.
#
# THE METHOD WAS VALIDATED AGAINST ILLINOIS BEFORE BEING TRUSTED HERE: run
# unchanged on Illinois's own House layer it answers 19.7 m, against the 17.9 m
# Illinois measured by hand around the neighbourhood the defect was reported in.
# Iowa's step really is about 2.2x Illinois's — bigger blocks, and boundaries
# that follow section lines and arterials — which is why the ceiling differs.
#
# Two earlier derivations were wrong and are recorded so they are not retried.
# Averaging over 1 km of a list of named cities answered 31-113 m depending on
# which city, i.e. it measured the choice of city. Ranking cells by RAW segment
# density answered 4-18 m, because the densest cells in a TIGER district file
# are river meanders and finely digitised corporate limits, not street grids —
# a ceiling from that would have been calibrated on the Mississippi.
#
# SIMPLIFY delivers a statewide worst of 19.1 m with 0 of 154 districts over
# even Illinois's tighter 25 m (measured 2026-09-26), so this leaves room for a
# redistricting to move the geometry without failing the build for no
# reader-visible reason.
FIDELITY_MAX_M = 45.0

# Which chambers nest, and how. Iowa House districts 2N-1 and 2N together make
# up Iowa Senate district N (Iowa Code 42.3: each senatorial district is
# composed of two representative districts), so Senate N's outer edge is theirs
# and the two layers must agree on it exactly. us-house IS DELIBERATELY ABSENT:
# 4 congressional districts stand in no whole-number relation to 50 Senate
# districts, so there is no rule to check and pairing them anyway produces a
# meaningless "offset" rather than a finding.
NESTING = [("ia-senate", "ia-house", 2)]


def fetch_tiger(layer, fields):
    """Fetch every Iowa feature for a Legislative MapServer layer as GeoJSON.
    Uses curl so it works through an HTTPS proxy (as in the Claude Code
    sandbox)."""
    url = (
        TIGERWEB + "/" + str(layer) + "/query"
        "?where=" + "STATE%3D%27" + IA_FIPS + "%27"
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
        raise RuntimeError("TIGERweb layer %d returned no Iowa features" % layer)
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb layer %d hit the transfer cap — needs paging" % layer)
    return geo


def run_mapshaper_family(source_paths, out_dir):
    """Simplify EVERY chamber in one run, so a shared edge is one arc.

    `combine-files` reads the inputs into a single dataset, which is what makes
    mapshaper dedupe an edge two layers both draw into ONE arc; simplification
    then removes the same vertices from it for both. `target=*` writes every
    layer back out, one file per input, each keeping its own fields (verified
    2026-09-26: CD120 stays on congress, SLDU on the Senate, SLDL on the House).
    Output file names come from the input base names, so the caller names its
    temp inputs after the chamber and maps them back.
    """
    subprocess.run(
        ["npx", "-y", MAPSHAPER] + list(source_paths) + ["combine-files",
         "-simplify"] + SIMPLIFY + [
         "-o", "precision=" + PRECISION, "format=geojson", "target=*", out_dir],
        check=True, cwd=REPO_ROOT,
    )


# --- the cross-layer gate: no geometry, no network --------------------------
def _vertex_set(geom):
    pts = set()
    if geom["type"] == "Polygon":
        rings = geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        rings = [r for poly in geom["coordinates"] for r in poly]
    else:
        return pts
    for r in rings:
        for pt in r:
            pts.add((pt[0], pt[1]))
    return pts


def _by_basename(features):
    return {(f["properties"].get("BASENAME") or "").strip(): f for f in features}


def check_nesting(built):
    """Every Senate boundary vertex must be a vertex of its own two House districts.

    Under one shared topology the Senate ring is assembled FROM House arcs, so
    this holds with no tolerance at all — which is what makes it a good gate:
    there is no epsilon to tune and no way for it to pass weakly. Measured
    2026-09-26 on the full state, it holds on 50 of 50 pairings when the family
    is simplified together and fails on 50 of 50 when each chamber is simplified
    alone.

    A non-numeric BASENAME is skipped. Iowa's fetch carries none today (all
    4/50/100 features are bare numbers); the skip is what would keep this gate
    honest if TIGER ever added a water pseudo-district the way it does for
    Illinois.
    """
    problems = []
    checked = 0
    for upper, lower, per in NESTING:
        if upper not in built or lower not in built:
            continue
        up = _by_basename(built[upper]["features"])
        lo = _by_basename(built[lower]["features"])
        for key, feat in sorted(up.items()):
            if not key.isdigit():
                continue
            n = int(key)
            kids = [str(per * (n - 1) + i + 1) for i in range(per)]
            if any(k not in lo for k in kids):
                problems.append("%s %s: %s missing from %s"
                                % (upper, key, [k for k in kids if k not in lo], lower))
                continue
            checked += 1
            child = set()
            for k in kids:
                child |= _vertex_set(lo[k]["geometry"])
            stray = _vertex_set(feat["geometry"]) - child
            if stray:
                problems.append(
                    "%s %s has %d vertex/vertices that are on no %s district (%s); "
                    "the layers were not simplified from one topology"
                    % (upper, key, len(stray), lower, " + ".join(kids)))
    if not checked:
        return False, "no nesting pairings were checked — NESTING or the fetch is wrong"
    if problems:
        return False, "%d pairing(s) broken; first: %s" % (len(problems), problems[0])
    return True, "%d pairing(s) share every boundary vertex exactly" % checked


# --- the fidelity gate: how far the TRUE line strays from the drawn one -----
def _mscale(lat):
    return (111320.0 * math.cos(math.radians(lat)), 110540.0)


def _seg_dist_m(p, a, b, sx, sy):
    px, py = p[0] * sx, p[1] * sy
    ax, ay = a[0] * sx, a[1] * sy
    bx, by = b[0] * sx, b[1] * sy
    dx, dy = bx - ax, by - ay
    d2 = dx * dx + dy * dy
    if d2 == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / d2
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _rings(geom):
    if geom["type"] == "Polygon":
        return list(geom["coordinates"])
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


def _index_segments(rings, cell=0.01):
    grid = {}
    for r in rings:
        for i in range(len(r) - 1):
            a, b = (r[i][0], r[i][1]), (r[i + 1][0], r[i + 1][1])
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    grid.setdefault((gx, gy), []).append((a, b))
    return grid, cell


def _dist_to_drawn(p, grid, cell, sx, sy):
    gx, gy = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
    best = float("inf")
    rad = 0
    while rad <= 4:
        for i in range(gx - rad, gx + rad + 1):
            for j in range(gy - rad, gy + rad + 1):
                if rad and abs(i - gx) != rad and abs(j - gy) != rad:
                    continue
                for a, b in grid.get((i, j), ()):
                    d = _seg_dist_m(p, a, b, sx, sy)
                    if d < best:
                        best = d
        # one band past the first hit, so a nearer segment just outside the
        # band that produced it cannot be missed
        if best < float("inf") and rad >= 1:
            break
        rad += 1
    return best


def check_fidelity(source_features, drawn_features, limit=None):
    """No point on the TRUE boundary may lie further than `limit` from the drawn line.

    The direction matters and the obvious one gates nothing: simplification KEEPS
    a subset of the source vertices, so every drawn vertex already sits on the
    source line and measuring drawn -> source answers ~0 by construction. What a
    reader sees is the true line straying from the chord drawn in its place, so
    that is what this measures.
    """
    limit = FIDELITY_MAX_M if limit is None else limit
    src = _by_basename(source_features)
    drawn = _by_basename(drawn_features)
    worst, where, wkey = 0.0, None, None
    over = 0
    for key, sf in src.items():
        if key not in drawn:
            continue
        dr = _rings(drawn[key]["geometry"])
        sr = _rings(sf["geometry"])
        if not dr or not sr:
            continue
        sx, sy = _mscale(sr[0][0][1])
        grid, cell = _index_segments(dr)
        dworst = 0.0
        dwhere = None
        for r in sr:
            for pt in r:
                d = _dist_to_drawn((pt[0], pt[1]), grid, cell, sx, sy)
                if d > dworst:
                    dworst, dwhere = d, (pt[0], pt[1])
        if dworst > limit:
            over += 1
        if dworst > worst:
            worst, where, wkey = dworst, dwhere, key

    # Iowa's fetch carries no water pseudo-district, so every key here is a
    # number. Name a non-numeric one as what it is rather than printing
    # "district State Senate Districts not defined", which reads as a bug in
    # the gate — the shape Illinois's file does ship.
    def _name(key):
        return ("district %s" % key) if (key or "").isdigit() else (
            "the non-numeric feature (%s)" % key)

    if over:
        return False, ("%d district(s) stray further than %.0f m from the true line; "
                       "worst is %s at %.1f m (%.5f,%.5f)"
                       % (over, limit, _name(wkey), worst, where[1], where[0]))
    return True, "worst stray %.1f m, %s; ceiling %.0f m" % (worst, _name(wkey), limit)


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
    is a topology break.

    The property comparison is Illinois's and catches what the point sampling
    cannot: `combine-files` writing a layer back with a field renamed or
    dropped would change every card's district number while the geometry stayed
    correct, and 2,000 points would agree the whole way through.
    """
    if len(result_features) != len(source_features):
        return False, "feature count changed: %d -> %d" % (len(source_features), len(result_features))
    src_props = sorted(tuple(sorted(f["properties"].items())) for f in source_features)
    new_props = sorted(tuple(sorted(f["properties"].items())) for f in result_features)
    if src_props != new_props:
        return False, "feature properties changed during simplification"

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
    """Fetch every chamber, simplify them as ONE topology, gate, then write."""
    source = {}
    for name, cfg in LAYERS.items():
        geo = fetch_tiger(cfg["layer"], cfg["fields"])
        if len(geo["features"]) != cfg["features"]:
            raise RuntimeError(
                "%s: %d features fetched (expected exactly %d districts) — "
                "refusing to write" % (name, len(geo["features"]), cfg["features"]))
        source[name] = geo

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
                    "%s: mapshaper wrote no output for this chamber (looked for %s) — "
                    "combine-files names outputs after the inputs, so a renamed temp "
                    "input silently drops a layer" % (name, op))
            with open(op) as f:
                built[name] = json.load(f)

    # gate 1, per layer: the project's point-in-district protocol vs the fetch
    for name in sorted(built):
        ok, msg = validate(source[name]["features"], built[name]["features"], VALIDATION_KEY)
        if not ok:
            raise RuntimeError("%s validation failed: %s" % (name, msg))
        print("  %-10s %s" % (name, msg), file=sys.stderr)

    # gate 2, across layers: the nesting Iowa Code 42.3 and TIGER both guarantee
    ok, msg = check_nesting(built)
    if not ok:
        raise RuntimeError("nesting check failed: %s" % msg)
    print("  nesting    %s" % msg, file=sys.stderr)

    # gate 3, against the source: how far the true line strays from the drawn one
    for name in sorted(built):
        ok, msg = check_fidelity(source[name]["features"], built[name]["features"])
        if not ok:
            raise RuntimeError("%s fidelity check failed: %s" % (name, msg))
        print("  %-10s %s" % (name, msg), file=sys.stderr)

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
          "ia/metro-worksheet.json and re-run generate_metro_files.py, or a "
          "returning visitor keeps the old geometry while their cards show the "
          "new answer.", file=sys.stderr)


def check_shipped():
    """Offline: the nesting gate on the files in data/app. This is the CI gate.

    It needs no network and no source fetch, because the nesting is a relation
    BETWEEN two shipped layers — which is exactly the regression a per-chamber
    rebuild would reintroduce. The fidelity gate cannot run here: it needs the
    TIGER fetch to compare against, so it is build-time only.
    """
    built = {}
    for name, cfg in LAYERS.items():
        path = os.path.join(APP_DATA_DIR, cfg["out"])
        if not os.path.exists(path):
            print("build-ia-legislative-boundaries: FAIL — %s is missing" % cfg["out"],
                  file=sys.stderr)
            return 1
        with open(path) as f:
            built[name] = json.load(f)
    ok, msg = check_nesting(built)
    if not ok:
        print("build-ia-legislative-boundaries: FAIL — %s\n"
              "  Rebuild the WHOLE family (python3 ia/scripts/build_legislative_boundaries.py); "
              "simplifying one chamber alone is what breaks this." % msg, file=sys.stderr)
        return 1
    print("build-ia-legislative-boundaries: OK — %s" % msg)
    return 0


def main():
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(check_shipped())
    if args:
        print("unexpected argument(s): %s\n"
              "This builder has no per-chamber mode: rebuilding one chamber alone is "
              "what breaks the Iowa House/Senate nesting, so the family is the unit.\n"
              "  (no args) fetch and rebuild all three\n"
              "  --check   offline nesting gate on the shipped files"
              % args, file=sys.stderr)
        sys.exit(1)
    build_family()


if __name__ == "__main__":
    main()
