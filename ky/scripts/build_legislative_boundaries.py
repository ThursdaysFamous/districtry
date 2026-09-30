#!/usr/bin/env python3
"""
Build the pre-simplified Kentucky legislative-district boundary files in
data/app/ from Census TIGERweb, so the app fetches them same-origin
(cache-first) instead of downloading full statewide geometry live on every
first toggle.

Statewide, like the Illinois reference and Wisconsin: Kentucky's instance
answers anywhere in the state, so each chamber ships whole — fetch ->
simplify -> validate -> write data/app/<chamber>-districts.json. No clip
step: the served area IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not
weekly CI — re-run it on redistricting. The officeholder ROSTERS
(ky-senate-members / ky-house-members, from Open States) are separate; only
the geometry is here (build_ky_legislature_roster.py builds those).

EVERY CHAMBER IS SIMPLIFIED IN ONE MAPSHAPER RUN, with Douglas-Peucker at an
absolute interval rather than Visvalingam at a retain percentage. Both halves of
that are load-bearing, and NEITHER WAS MEASURED HERE — they are Illinois's and
Iowa's findings, ported deliberately, and they are attributed rather than
restated as Kentucky's:

  * ONE RUN, because mapshaper builds topology WITHIN one file. KENTUCKY HAS NO
    NESTING RULE TO PROTECT — its 100 House districts stand in no whole-number
    relation to its 38 Senate districts and are drawn independently — but the
    three layers still share one edge that is guaranteed exactly: THE STATE
    BORDER. Every district layer tiles the whole of Kentucky, so the outer edge
    of each layer's union IS the state boundary, identically, in the source.
    Simplified in separate runs that shared edge cannot survive identically,
    and a reader zoomed in on the Ohio River would see a Senate district and a
    House district disagreeing about where the state ends. Illinois measured
    55 of 59 nesting pairings with a Senate vertex more than 25 m off any House
    line, worst 210 m, all of it introduced by the build; the mechanism is the
    same one, and here it is the border rather than the nesting that it damages.
  * DOUGLAS-PEUCKER, because Visvalingam thresholds triangle AREA, which does not
    bound how far the drawn line strays from the true one — successive
    below-threshold removals compound, which is how a boundary running as a
    STAIRCASE along a street grid becomes a diagonal chord across a city block.
    Douglas-Peucker thresholds perpendicular DEVIATION. Sharing one topology does
    nothing for that on its own: Iowa measured the nesting exact while the worst
    stray stayed 333 m and 146 of 154 districts were over 25 m.

KENTUCKY'S OWN MEASUREMENT, at these settings, full state, 2026-09-30 — the
three gates' own output on the shipped files:

    border           3 layers share one state border exactly (4,856 edges)
    worst stray      15.3 m against a 29.9 m ceiling (all three layers)
    coverage         2000/2000 point agreement on us-house and ky-house,
                     1999/2000 on ky-senate, 0 overlaps in any layer
    written          congress 407,183 B / senate 1,030,502 B / house 1,550,824 B raw

THE BORDER GATE WAS NEGATIVE-TESTED, not merely observed to pass. Simplifying
each chamber in its OWN mapshaper run and re-running the gate on the result
fails it: 696 border edges appear only in ky-house and 698 only in ky-senate,
first difference near 36.62020,-89.37192 on the Mississippi at the state's
south-western corner. A gate that has never been seen to fail is a gate nobody
knows the strength of, and this one is the only thing standing between a shared
topology and three layers quietly disagreeing about where Kentucky ends.

THE ONE POINT OF DISAGREEMENT IN ky-senate IS NOT SMOOTHED AWAY. 1999/2000 is
one sampled point out of two thousand landing in a different Senate district
after simplification than before it, which is what a 15.3 m boundary movement
costs at the scale a reader clicks, and it is inside the 99.5% floor the fleet
protocol sets rather than an exception granted to this state.

NO SIZE COMPARISON IS QUOTED, because none was measured here and the quantity is
treacherous. Iowa recorded +7,667 bytes gzipped for the same change and Illinois
recorded 871 bytes SMALLER, so there is no fleet-wide sign to inherit; and
TIGERweb returns features in a server-determined order that mapshaper preserves,
which moved Iowa's own gzipped size by 5,504-6,596 bytes for identical geometry
at identical settings. A before-and-after on committed files cannot separate the
setting from the order. If a size figure is ever wanted for Kentucky, measure it
on one fetch with the feature order held fixed.

A SMALL-INPUT TEST WILL TELL YOU THE COMBINE ALONE FIXED IT AND IT IS LYING.
mapshaper's retain percentage is relative to the WHOLE dataset's vertex count, so
three districts through combine-files keep far more detail per district than a
statewide run at the same percentage. Illinois measured a 4 m worst stray on
three districts against 331 m on the full state with identical settings. Every
figure above is the FULL STATE, all 144 features, or it would be worth nothing.

Three gates run before anything is written, and each answers a question the
others cannot:
  * validate()       -- per layer, the project's 2,000-random-point
                        point-in-district protocol over the state envelope,
                        against the pre-simplification fetch.
  * check_shared_border() -- ACROSS layers: each layer's own state border must
                        be identical, edge for edge, to every other layer's.
                        A layer's border is derived rather than assumed: under
                        one shared topology every interior edge is traced by
                        exactly two adjacent districts and every border edge by
                        exactly one, so the edges appearing ONCE in a layer are
                        that layer's outline. There is no epsilon to tune and
                        no way for it to pass weakly. No geometry library and
                        no network, which is why --check runs it in CI on the
                        shipped files.
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
    python3 ky/scripts/build_legislative_boundaries.py           # fetch + rebuild all three
    python3 ky/scripts/build_legislative_boundaries.py --check   # offline: the nesting
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
KY_FIPS = "21"

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -89.72, "minLat": 36.35, "maxLng": -81.85, "maxLat": 39.30}

# chamber -> how to build data/app/<out>.
#   layer:    TIGERweb Legislative MapServer layer index (0 US House, 1 upper, 2 lower)
#   fields:   outFields kept from TIGERweb. The app's extractDistrictNumber reads
#             SLDU/SLDL directly; congress uses the NAME fallback since TIGERweb
#             ships CD120, not a bare number.
#   out:      the data/app file index.html fetches for this layer
#   features: the exact district count — Kentucky's fetch carries no water
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
        # Re-measured for Kentucky 2026-09-30: naming CD119 answered
        # {"code":400,"message":"Failed to execute query."} and naming CD120
        # answered all 6 districts.
        "fields": ["CD120", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "congress-districts.json",
        "features": 6,     # 6 Kentucky congressional districts
    },
    "ky-senate": {
        "layer": 1,
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "ky-senate-districts.json",
        "features": 38,    # 38 Kentucky Senate districts
    },
    "ky-house": {
        "layer": 2,
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "ky-house-districts.json",
        "features": 100,   # 100 Kentucky House districts
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
# than this from the line drawn for it. MEASURED FROM KENTUCKY'S OWN GEOMETRY —
# it is not Illinois's 25 m and not Kentucky's 34.0 m, because a ceiling copied
# from another state is calibrated on somebody else's city blocks.
#
# The quantity is the true line's own STAIRCASE STEP: how far it runs before it
# turns, where it is following a street grid, because a stray larger than one
# step is a chord cutting a corner off the real line. Measured structurally
# rather than from a list of places chosen by hand: a step is a segment whose
# turn to the next segment is a right angle (70-110 degrees), counted only in
# ~1 km cells holding at least twenty such turns, since one right angle is a
# field corner and twenty in a square kilometre is a grid. On Kentucky's own
# full-precision TIGER fetch (2026-09-30) that gives a MEDIAN 29.8 m (ky-house,
# 540 steps over 19 cells) and 27.2 m (ky-senate, 140 steps over 6 cells), so
# 29.9 m is about one Kentucky senate-layer step at the 1.10x the chambers
# builders use.
#
# THE INSTRUMENT WAS VALIDATED AGAINST A STATE THAT HAS PUBLISHED A FIGURE,
# before Kentucky's was trusted: run unchanged on Illinois's own full-precision
# House fetch it answers 19.6 m against the 19.7 m Illinois measured by hand. So
# the 27.2 m is this method's answer for Kentucky and not a different method's.
#
# THE CEILING COMES FROM THE FINER CHAMBER, which in Kentucky is the SENATE —
# the reverse of Kentucky, where the House was finer. That is the conservative
# direction either way, and it is worth naming because the obvious assumption
# (more districts means finer lines) is false here: Kentucky's 38 Senate
# districts follow city streets through Louisville and Lexington as closely as
# its 100 House districts do.
#
# THE VALUE IS PINNED, NEVER RECOMPUTED PER RUN. A ceiling re-derived from the
# source each time can never fail, because it rises whenever the source gets
# coarser; the builder prints the measured worst stray beside the pinned number
# so a real change in the source is visible to a person. A redistricting
# re-opens it: re-measure the step on the new lines rather than carrying the
# number forward.
FIDELITY_MAX_M = 29.9

# KENTUCKY'S TWO CHAMBERS DO NOT NEST, so there is no nesting table here and
# check_nesting() is deliberately absent rather than disabled. 100 House
# districts stand in no whole-number relation to 38 Senate districts, and the
# Kentucky Constitution sec. 33 constrains each chamber's districts to county
# lines where population permits without relating one chamber to the other. The
# Michigan instance measured what happens when two such chambers are paired
# anyway: a meaningless 767 km "offset" rather than a finding.
#
# What IS guaranteed across all three layers is the STATE BORDER, and that is
# what check_shared_border() gates. Every one of these layers tiles the whole
# of Kentucky, so the outer edge of each layer's union is the state boundary,
# and in the source the three are identical. Under one shared topology they stay
# identical after simplification; simplified separately they cannot.


def fetch_tiger(layer, fields):
    """Fetch every Kentucky feature for a Legislative MapServer layer as GeoJSON.
    Uses curl so it works through an HTTPS proxy (as in the Claude Code
    sandbox)."""
    url = (
        TIGERWEB + "/" + str(layer) + "/query"
        "?where=" + "STATE%3D%27" + KY_FIPS + "%27"
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
        raise RuntimeError("TIGERweb layer %d returned no Kentucky features" % layer)
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
def _by_basename(features):
    return {(f["properties"].get("BASENAME") or "").strip(): f for f in features}


def _border_edges(features):
    """The layer's own state border, derived from the edges it draws.

    Under one shared topology every INTERIOR edge is traced by exactly two
    adjacent districts and every BORDER edge by exactly one, so the undirected
    segments appearing an odd number of times across the layer are the layer's
    outline. Nothing here needs to know where Kentucky is: the border falls out
    of the tiling.

    An edge is undirected because two adjacent districts trace their shared arc
    in opposite directions.
    """
    counts = {}
    for f in features:
        geom = f["geometry"]
        if geom["type"] == "Polygon":
            rings = geom["coordinates"]
        elif geom["type"] == "MultiPolygon":
            rings = [r for poly in geom["coordinates"] for r in poly]
        else:
            continue
        for r in rings:
            for i in range(len(r) - 1):
                a = (r[i][0], r[i][1])
                b = (r[i + 1][0], r[i + 1][1])
                if a == b:
                    continue
                key = (a, b) if a <= b else (b, a)
                counts[key] = counts.get(key, 0) + 1
    return {k for k, n in counts.items() if n % 2 == 1}


def check_shared_border(built):
    """Every layer's own state border must be identical, edge for edge.

    This is Kentucky's cross-layer gate, standing where a nesting gate stands in
    a state whose chambers nest. All three layers tile the whole state, so each
    one's outline IS the Kentucky border, and in the TIGER source the three are
    the same line. Simplified from ONE shared topology they stay the same line;
    simplified one layer at a time they cannot, and a reader zoomed in on the
    Ohio River would see a Senate district and a House district disagreeing
    about where the state ends.

    There is no tolerance and nothing to tune: the comparison is set equality
    over exact coordinate pairs. It needs no geometry library and no network,
    which is why --check runs it in CI on the shipped files.

    IT CANNOT PASS VACUOUSLY. A layer whose border came out empty, or a run that
    somehow compared a layer with itself, fails before the comparison: the gate
    requires at least three layers, and each layer's border must be a closed
    boundary, which it checks by requiring every vertex on it to be the endpoint
    of an even number of border edges. A border that is not closed means the
    odd-count derivation found something other than an outline, and the number
    is reported rather than the gate quietly passing.
    """
    names = sorted(built)
    if len(names) < 3:
        return False, ("only %d layer(s) present — the border comparison needs every "
                       "chamber, so nothing was actually compared" % len(names))
    borders = {}
    for name in names:
        edges = _border_edges(built[name]["features"])
        if not edges:
            return False, ("%s produced an EMPTY border — every district is reported as "
                           "sharing all its edges, which cannot be true of a layer that "
                           "tiles a state" % name)
        degree = {}
        for a, b in edges:
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
        dangling = [v for v, d in degree.items() if d % 2 == 1]
        if dangling:
            return False, ("%s's border is not closed: %d vertex/vertices sit on an odd "
                           "number of border edges, so the odd-count derivation found "
                           "something other than an outline" % (name, len(dangling)))
        borders[name] = edges
    ref = names[0]
    for name in names[1:]:
        only_ref = borders[ref] - borders[name]
        only_other = borders[name] - borders[ref]
        if only_ref or only_other:
            sample = sorted(only_ref or only_other)[0]
            return False, (
                "%s and %s draw the state border differently: %d edge(s) only in %s, "
                "%d only in %s (first difference near %.5f,%.5f); the layers were not "
                "simplified from one topology"
                % (ref, name, len(only_ref), ref, len(only_other), name,
                   sample[0][1], sample[0][0]))
    return True, ("%d layers share one state border exactly (%d edges)"
                  % (len(names), len(borders[ref])))


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

    # Kentucky's fetch carries no water pseudo-district, so every key here is a
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

    # gate 2, across layers: the state border all three layers draw
    ok, msg = check_shared_border(built)
    if not ok:
        raise RuntimeError("shared-border check failed: %s" % msg)
    print("  border     %s" % msg, file=sys.stderr)

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
          "ky/metro-worksheet.json and re-run generate_metro_files.py, or a "
          "returning visitor keeps the old geometry while their cards show the "
          "new answer.", file=sys.stderr)


def check_shipped():
    """Offline: the shared-border gate on the files in data/app. This is the CI gate.

    It needs no network and no source fetch, because the shared border is a
    relation BETWEEN the shipped layers — which is exactly the regression a
    per-chamber rebuild would reintroduce. The fidelity gate cannot run here: it
    needs the TIGER fetch to compare against, so it is build-time only.
    """
    built = {}
    for name, cfg in LAYERS.items():
        path = os.path.join(APP_DATA_DIR, cfg["out"])
        if not os.path.exists(path):
            print("build-ky-legislative-boundaries: FAIL — %s is missing" % cfg["out"],
                  file=sys.stderr)
            return 1
        with open(path) as f:
            built[name] = json.load(f)
    ok, msg = check_shared_border(built)
    if not ok:
        print("build-ky-legislative-boundaries: FAIL — %s\n"
              "  Rebuild the WHOLE family (python3 ky/scripts/build_legislative_boundaries.py); "
              "simplifying one chamber alone is what breaks this." % msg, file=sys.stderr)
        return 1
    print("build-ky-legislative-boundaries: OK — %s" % msg)
    return 0


def main():
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(check_shipped())
    if args:
        print("unexpected argument(s): %s\n"
              "This builder has no per-chamber mode: rebuilding one chamber alone is "
              "what makes the three layers draw the Kentucky border differently, so the "
              "family is the unit.\n"
              "  (no args) fetch and rebuild all three\n"
              "  --check   offline shared-border gate on the shipped files"
              % args, file=sys.stderr)
        sys.exit(1)
    build_family()


if __name__ == "__main__":
    main()
