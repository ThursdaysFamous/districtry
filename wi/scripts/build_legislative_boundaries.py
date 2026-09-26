#!/usr/bin/env python3
"""
Build the pre-simplified Wisconsin legislative-district boundary files in
data/app/ from Census TIGERweb, so the app fetches them same-origin
(cache-first) instead of downloading full statewide geometry live on every
first toggle.

Statewide, like the Illinois reference and unlike the SF fork: Wisconsin's
instance answers anywhere in the state, so each chamber ships whole —
fetch -> simplify -> validate -> write data/app/<chamber>-districts.json.
No clip step: the served area IS the state.

Like build_metro_outline.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS
(wi-senate-members / wi-assembly-members, from Open States) are separate;
only the geometry is here (build_wi_legislature_roster.py builds those).

`us-house` is carried as a target for redistricting re-runs, but the shipped
data/app/congress-districts.json bytes come from the state bootstrap and are
not rewritten unless you name the target explicitly — the default build is
the two chambers only, so a chamber refresh can never churn the congress
file's bytes as a side effect.

Great Lakes note: TIGERweb ships a ZZ "undefined" pseudo-district covering
state waters for each chamber, so Wisconsin's counts come back 34/100, not
33/99. The guards below expect the real district count and tolerate the ZZ
feature; validation is classification agreement, which the water feature
participates in like any other.

BOTH CHAMBERS ARE SIMPLIFIED IN ONE RUN, AND THE ALGORITHM IS DOUGLAS-PEUCKER.
Three Assembly districts make up one Senate district, so their outer edges are
the same line and must be drawn the same way. Measured on the files this builder
used to write -- two separate Visvalingam runs at 10% and 9% -- all 33 pairings
disagreed, and every metre of it was introduced here: the TIGERweb source nests
EXACTLY, 33 of 33 with 0.0 m offset. `combine-files` puts both chambers in ONE
dataset, which makes a shared edge ONE arc simplified once, and the nesting comes
out exact again.

THAT FIXES NESTING AND NOT FIDELITY, WHICH IS THE SECOND DEFECT AND WAS MEASURED
SEPARATELY. Visvalingam thresholds triangle AREA, which does not bound how far
the drawn line strays from the true one, so a boundary running as a staircase
along a street grid gets replaced by a diagonal chord across the blocks. Measured
on the full state, source vertex to nearest drawn segment: the old files strayed
a median 80.1 m and a worst 2,939.9 m, with 128 of 134 districts past 20 m --
and combining them at the same 10% made it WORSE, 5,381.4 m, because mapshaper's
percentage is relative to the whole dataset, so combining retains proportionally
less of each layer. Douglas-Peucker thresholds perpendicular DEVIATION instead,
and `interval` is an absolute distance, so it means the same thing after a
redistricting changes the vertex count. At interval=7 the statewide worst is
17.5 m with 0 of 134 districts past 20 m.

WHAT IT COSTS, PUBLISHED RATHER THAN SMOOTHED. The two files go from 443,504 to
772,998 bytes gzipped, +329,494 (+74.3%), on geometry `sw.js` serves cache-first,
so every first-load visitor pays it. Illinois's equivalent change came out 871
bytes SMALLER because its old files were far less aggressive than Wisconsin's;
here correctness costs real bytes, and that trade is worth stating next to a
median stray of 80.1 m on the boundaries a reader is standing beside.

Three gates run before anything is written, and each answers a question the
others cannot:
  * validate()       -- per chamber, the project's 2,000-random-point
                        point-in-district protocol against the pre-simplification
                        fetch. IT NEVER SAW EITHER DEFECT: 2,000 uniform points
                        over Wisconsin almost never land in a thin band, so it
                        passed every time while 2.9 km of stray shipped. Kept
                        because it catches a different failure -- a topology
                        break putting one point in two districts -- not because
                        it covers this one.
  * check_nesting()  -- ACROSS chambers: every Senate boundary vertex must be a
                        vertex of its own three Assembly districts, EXACTLY.
                        Under a shared topology the Senate ring is built from
                        Assembly arcs, so this holds at zero tolerance; under
                        separate runs it failed on 33 of 33. No geometry library
                        and no network.
  * check_fidelity() -- against the SOURCE: no point on the true boundary may lie
                        further than FIDELITY_MAX_M from the line drawn for it.
                        Needs the fetch, so it is build-time only.
If any gate fails, nothing is written.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 wi/scripts/build_legislative_boundaries.py             # both chambers
    python3 wi/scripts/build_legislative_boundaries.py wi-senate   # one chamber
    python3 wi/scripts/build_legislative_boundaries.py us-house    # explicit only
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
WI_FIPS = "55"

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -93.09, "minLat": 42.29, "maxLng": -86.04, "maxLat": 47.51}

# chamber -> how to build data/app/<out>.
#   layer:    TIGERweb Legislative MapServer layer index (0 US House, 1 upper, 2 lower)
#   fields:   outFields kept from TIGERweb. The app's extractDistrictNumber reads
#             SLDU/SLDL directly; congress uses the NAME fallback since TIGERweb
#             ships CD120, not a bare number.
#   out:      the data/app file index.html fetches for this layer
#   min_features: count guard — the real district count (a ZZ water
#             pseudo-district on top of it is expected and tolerated)
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
        "min_features": 8,   # 8 WI congressional districts (+ ZZ)
    },
    "wi-senate": {
        "layer": 1,
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "wi-senate-districts.json",
        "min_features": 33,  # 33 WI Senate districts (+ ZZ)
    },
    "wi-assembly": {
        "layer": 2,
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "wi-assembly-districts.json",
        "min_features": 99,  # 99 WI Assembly districts (+ ZZ)
    },
}
# The family this builder writes, ALWAYS together. There is deliberately no
# per-chamber argument: rebuilding one chamber alone is exactly the defect the
# combined run exists to fix, so an option permitting it would be a loaded gun.
# `us-house` stays in LAYERS as a target for a redistricting re-run and is not
# written by this builder.
FAMILY = ["wi-senate", "wi-assembly"]
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live
VALIDATION_KEY = "GEOID"  # unique per district, preserved through simplification

# ONE simplification setting for the whole family. Douglas-Peucker with an
# absolute interval, not Visvalingam with a retain percentage — see the module
# docstring for the measurement.
SIMPLIFY = ["dp", "keep-shapes", "interval=7"]

# The fidelity ceiling, in metres: no point on the true boundary may lie further
# than this from the line drawn for it. DERIVED FROM WISCONSIN'S OWN GEOMETRY
# rather than copied from Illinois's 25 m. The true line's staircase step -- how
# far it runs before it turns -- is a median 14.7 m over the 365,514 Assembly
# source segments statewide, and the two dense street grids agree with it
# (Milwaukee 14.5 m over 4,834 segments, Madison 15.2 m over 2,871), so no local
# sample was needed to justify it the way Illinois's was. Illinois set 25 m
# against a 17.9 m step, a ratio of 1.40; 14.7 x 1.40 = 20.6, so 20 m -- the
# drawn line cannot cut off more than roughly a single step of the real one.
#
# SIMPLIFY delivers a statewide worst of 17.5 m, which is 12.5% of headroom and
# THINNER THAN IT LOOKS BECAUSE THAT WORST IS NOT THE INTERVAL'S. It is constant
# across interval=5, 6 and 7, because it is set by one dropped micro-ring:
# Senate district 1's source carries 17 rings and the drawn file 16, and the
# worst point sits on the ring that went -- 7 vertices, ~0.0000 km2, at
# 45.4107,-86.8596 in open Lake Michigan off Door County. So a failure here is
# more likely to be a ring the simplifier dropped than a chord it drew, and
# lowering `interval` will not move it (interval=4 measured WORSE, 19.9 m).
FIDELITY_MAX_M = 20.0

# Which chambers nest, and how. Wisconsin Assembly districts 3N-2, 3N-1 and 3N
# together make up Senate district N (Wis. Const. art. IV, s. 5), so Senate N's
# outer edge is theirs and the two layers must agree on it exactly. US HOUSE IS
# DELIBERATELY ABSENT: 8 congressional districts stand in no whole-number
# relation to 33 Senate districts, so there is no rule to check and pairing them
# would produce a meaningless "offset" rather than a finding.
NESTING = [("wi-senate", "wi-assembly", 3)]


def fetch_tiger(layer, fields):
    """Fetch every Wisconsin feature for a Legislative MapServer layer as
    GeoJSON. Uses curl so it works through an HTTPS proxy (as in the Claude
    Code sandbox)."""
    url = (
        TIGERWEB + "/" + str(layer) + "/query"
        "?where=" + "STATE%3D%27" + WI_FIPS + "%27"
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
        raise RuntimeError("TIGERweb layer %d returned no Wisconsin features" % layer)
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb layer %d hit the transfer cap — needs paging" % layer)
    return geo


def run_mapshaper_family(source_paths, out_dir):
    """Simplify EVERY chamber in one run, so a shared edge is one arc.

    `combine-files` reads the inputs into a single dataset, which is what makes
    mapshaper dedupe an edge two layers both draw into ONE arc; simplification
    then removes the same vertices from it for both. `target=*` writes every
    layer back out, one file per input, each keeping its own fields. Output file
    names come from the input base names, so the caller names its temp inputs
    after the chamber and maps them back.
    """
    subprocess.run(
        ["npx", "-y", MAPSHAPER] + list(source_paths) + ["combine-files",
         "-simplify"] + SIMPLIFY + [
         "-o", "precision=" + PRECISION, "format=geojson", "target=*", out_dir],
        check=True, cwd=REPO_ROOT,
    )


# --- the two gates below are a PORT of Illinois's, in scripts/
#     build_legislative_boundaries.py, and are deliberately not a rewrite: they
#     answer the same two questions and any difference between the two states'
#     readings would be a difference nobody intended. There is no shared
#     geometry module for them to live in, and these two builders are already
#     per-instance copies of one shape by fleet convention; if a third state
#     needs them, that is the moment to lift them into scripts/ rather than to
#     make a third copy. Only the pairing arity and the ceiling are Wisconsin's.
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
    2026-09-25, it holds on 59 of 59 pairings when the family is simplified
    together and fails on 59 of 59 when each chamber is simplified alone.
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
    # TIGER ships one pseudo-district per chamber for the water area, whose
    # BASENAME is prose ("State Senate Districts not defined") rather than a
    # number. It is a real shipped feature and is held to the same ceiling, but
    # naming it "district State Senate Districts not defined" reads as a bug in
    # the gate, so say what it is.
    def _name(key):
        return ("district %s" % key) if (key or "").isdigit() else (
            "the water pseudo-district (%s)" % key)

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
    """Fetch, simplify TOGETHER, gate three ways, and only then write.

    Nothing reaches data/app until every chamber has passed its own validate()
    AND the two cross-cutting gates have passed on the whole family, because a
    half-written family is the defect: the two files only agree if they came out
    of the same run.
    """
    sources, built = {}, {}
    for name in FAMILY:
        cfg = LAYERS[name]
        sources[name] = fetch_tiger(cfg["layer"], cfg["fields"])

    with tempfile.TemporaryDirectory() as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir)
        os.makedirs(out_dir)
        # The temp input is named for the chamber, because mapshaper names each
        # output after its input's base name and that is how they map back.
        paths = []
        for name in FAMILY:
            q = os.path.join(in_dir, name + ".geojson")
            with open(q, "w") as f:
                json.dump(sources[name], f)
            paths.append(q)
        run_mapshaper_family(paths, out_dir + os.sep)
        for name in FAMILY:
            # mapshaper names each output after its INPUT's base name, and with a
            # directory target it writes `.json` whatever `format=geojson` says --
            # so the extension here is not the one the inputs carry. The guard
            # below is what caught that rather than a silent empty build.
            q = os.path.join(out_dir, name + ".json")
            if not os.path.exists(q):
                raise RuntimeError(
                    "mapshaper wrote no %s — the combined run did not emit every "
                    "layer, so the two files would not share a topology" % name)
            with open(q) as f:
                built[name] = json.load(f)

    # gate 1, per chamber: count guard + the 2,000-point protocol
    notes = {}
    for name in FAMILY:
        cfg = LAYERS[name]
        n = len(built[name]["features"])
        if not (cfg["min_features"] <= n <= cfg["min_features"] + 1):
            raise RuntimeError(
                "%s: %d features after simplify (expected %d districts, +1 for the "
                "ZZ water pseudo-district at most) — refusing to write"
                % (name, n, cfg["min_features"]))
        ok, msg = validate(sources[name]["features"], built[name]["features"],
                           VALIDATION_KEY)
        if not ok:
            raise RuntimeError("%s validation failed: %s" % (name, msg))
        notes[name] = msg

    # gate 2, across chambers: the nesting the shared topology exists to deliver
    ok, msg = check_nesting(built)
    if not ok:
        raise RuntimeError("nesting check failed: %s" % msg)
    print("nesting: %s" % msg, file=sys.stderr)

    # gate 3, against the source: how far the true line strays from the drawn one
    for name in FAMILY:
        ok, msg = check_fidelity(sources[name]["features"], built[name]["features"])
        if not ok:
            raise RuntimeError("%s fidelity check failed: %s" % (name, msg))
        print("fidelity %s: %s" % (name, msg), file=sys.stderr)

    # every gate passed — now write
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    for name in FAMILY:
        cfg = LAYERS[name]
        compact = json.dumps(built[name], separators=(",", ":"))
        if json.loads(compact) != built[name]:
            raise RuntimeError("%s round-trip mismatch before writing" % name)
        with open(os.path.join(APP_DATA_DIR, cfg["out"]), "w") as f:
            f.write(compact)
        print("%s -> data/app/%s: %d features (statewide); %s; %d bytes (%s, 6dp)"
              % (name, cfg["out"], len(built[name]["features"]), notes[name],
                 len(compact), " ".join(SIMPLIFY)), file=sys.stderr)
    print("REMEMBER: this geometry is cache-first — bump `cache_name` in "
          "wi/metro-worksheet.json and regenerate, or returning visitors keep "
          "the old outlines.", file=sys.stderr)


def main():
    if sys.argv[1:]:
        print("this builder takes no arguments: both chambers are simplified in "
              "ONE run so a shared edge is one arc, and rebuilding one alone is "
              "the defect that shape exists to fix.", file=sys.stderr)
        sys.exit(1)
    build_family()


if __name__ == "__main__":
    main()
