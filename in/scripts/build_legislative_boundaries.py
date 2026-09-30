#!/usr/bin/env python3
"""
Build the pre-simplified Indiana legislative-district boundary files in
in/data/app/ from Census TIGERweb, so the app fetches them same-origin
(cache-first) instead of downloading the full statewide geometry live on every
first toggle.

Statewide, like every other instance: Indiana's app answers anywhere in the
state, so each chamber ships whole — fetch -> simplify -> validate -> write
in/data/app/<chamber>-districts.json. No clip step: the served area IS the
state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly CI
— re-run it on redistricting. There are no officeholder rosters for the two
state chambers (recorded as gap in-general-assembly-roster); the U.S. House
roster is build_congress_roster.py's and refreshes weekly.

SIMPLIFICATION SIMPLIFIES ALL THREE CHAMBERS IN ONE MAPSHAPER RUN, AND THE
ALGORITHM IS DOUGLAS-PEUCKER RATHER THAN VISVALINGAM. Both halves are carried
from Illinois's builder, where they were measured (scripts/
build_legislative_boundaries.py, 2026-09-25): `combine-files` puts the layers
in ONE dataset, so an edge two layers both draw is ONE arc simplified once, and
Douglas-Peucker thresholds perpendicular DEVIATION where Visvalingam thresholds
triangle AREA — which does not bound how far the drawn line strays, and is how
a boundary running as a STAIRCASE along a street grid gets replaced by a
diagonal chord across a city block through the houses. Illinois measured 331 m
of stray under Visvalingam against 17.8 m under Douglas-Peucker, for FEWER
gzipped bytes.

INDIANA'S CHAMBERS DO NOT NEST, AND THAT IS MEASURED RATHER THAN ASSUMED.
Illinois's builder gates a hierarchy TIGER guarantees there — two IL House
districts make up one IL Senate district — and Indiana's 100 House districts
against 50 Senate districts look like the same 2-to-1 rule. They are not.
Measured 2026-09-29 by testing every House district's interior point against
the Senate layer: a Senate district contains 1, 2, 3 or 4 whole House
districts (11 contain one, 24 two, 11 three, 2 four), and the numbering is
unrelated — Senate 1 holds House 12 and 15, Senate 3 holds House 2, 3 and 14.
So there is NO nesting rule to check, and pairing the layers anyway would
produce a meaningless "offset" rather than a finding, exactly as Michigan's
builder records for its own 38-against-110. check_nesting IS THEREFORE NOT
SHIPPED HERE: a gate that can only be vacuous is worse than no gate, because it
reads as covered.

What --check runs instead is check_partition, which is a real offline question
about the shipped bytes: each layer's district numbers must be exactly 1..N
with nothing missing or doubled, and 2,000 points sampled over the state
envelope must land in at most ONE district of each layer. A simplification that
folded two districts into an overlap, or a hand-edit that dropped one, fails it
with no network and no source fetch.

Three gates run before anything is written, and each answers a question the
others cannot:
  * validate()        -- per layer, the project's 2,000-random-point
                         point-in-district protocol against the
                         pre-simplification fetch (no point in two districts;
                         classification agrees).
  * check_partition() -- the shipped bytes alone: complete 1..N numbering and
                         no self-overlap. No network, so --check runs it in CI.
  * check_fidelity()  -- against the SOURCE: no point on the true boundary may
                         lie further than FIDELITY_MAX_M from the line drawn
                         for it. Needs the fetch, so it is build-time only.
If any gate fails, nothing is written.

Property fields are trimmed to what the app reads so the file stays small:
extractDistrictNumber() keys on the numeric field (SLDU/SLDL) or, for congress,
the trailing number of a *NAME* field ("Congressional District 5" -> "5"); GEOID
is kept as a stable per-feature key for validation.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js (mapshaper
via `npx mapshaper@<pinned>`).

Usage:
    python3 in/scripts/build_legislative_boundaries.py          # fetch + rebuild all three
    python3 in/scripts/build_legislative_boundaries.py --check  # offline partition gate

THERE IS NO PER-CHAMBER BUILD, and that is the point rather than a regression:
the family shares one topology, so rebuilding one chamber alone would simplify
it off a different arc set from its siblings.
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
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (matches build_embedded_boundaries.py)
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer"
IN_FIPS = "18"

# chamber -> how to build data/app/<out>.
#   layer:    TIGERweb Legislative MapServer layer index (0 US House, 1 Senate/Upper, 2 House/Lower)
#   fields:   outFields kept from TIGERweb. district_field is read by the app's
#             extractDistrictNumber (SLDU/SLDL directly; congress via the NAME
#             fallback since TIGERweb ships CD120, not the app's cd### names).
#   out:      the data/app file index.html fetches for this layer
#   min_features: count guard — refuse to write a suspiciously short result.
#                 It is the EXACT count here, because check_partition below
#                 requires the numbering to be 1..min_features: measured
#                 2026-09-29, Indiana ships NO water pseudo-district on any of
#                 the three layers, unlike Illinois's ZZ features, so every
#                 feature carries a district number.
# There is deliberately NO per-layer simplify setting: the whole family is
# simplified in ONE run at ONE setting (SIMPLIFY below), because a shared edge
# can only survive identically if both layers came off the same topology at the
# same threshold. Three percentages is what broke the nesting.
LAYERS = {
    "congress": {
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
        "min_features": 9,  # 9 Indiana congressional districts
    },
    "in-senate": {
        "layer": 1,
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "in-senate-districts.json",
        "min_features": 50,  # 50 Indiana Senate districts
    },
    "in-house": {
        "layer": 2,
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "out": "in-house-districts.json",
        "min_features": 100,  # 100 Indiana House districts
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
# than this from the line drawn for it. MEASURED rather than picked, and
# measured for INDIANA rather than copied from Illinois's 25 m — a ceiling
# derived from another state's street grid is a number with no local meaning.
# The true line's own staircase step -- how far it runs before it turns -- is a
# median 28.2 m over the 1,879 source segments within 0.05 deg of the
# Statehouse (39.7686,-86.1626), Indiana's densest platted grid, so 30 m is
# about one step: the drawn line cannot cut off more than roughly a single step
# of the real one. The value is PINNED rather than recomputed each run, because
# a ceiling derived from the source on every run rises whenever the source gets
# coarser and can then never fail.
FIDELITY_MAX_M = 30.0

# NO NESTING TABLE. Indiana's chambers do not nest -- measured, see the module
# docstring -- so there is no relation between two layers for a gate to check
# and check_nesting is not shipped. The offline gate is check_partition, which
# asks a question about each layer on its own.
#
# How many points check_partition samples, and over what. The envelope is the
# worksheet's permalink_gate, looser than METRO_BBOX, so the sample includes
# ground outside the state where every layer must classify NOTHING.
PARTITION_SAMPLES = 2000
STATE_BBOX = {"minLng": -88.30, "minLat": 37.60, "maxLng": -84.60, "maxLat": 41.95}


def fetch_tiger(layer, fields):
    """Fetch every Indiana feature for a Legislative MapServer layer as GeoJSON.

    Uses curl so it works through an HTTPS proxy (as in the Claude Code sandbox)
    and anywhere curl is present. STATE='18' returns all Indiana districts for
    the chamber in one query (no transfer-cap paging for these layers)."""
    url = (
        TIGERWEB + "/" + str(layer) + "/query"
        "?where=" + "STATE%3D%27" + IN_FIPS + "%27"
        "&outFields=" + ",".join(fields) +
        "&outSR=4326&geometryPrecision=6&f=geojson"
    )
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "120", url],
        check=True, capture_output=True,
    ).stdout
    geo = json.loads(out)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("TIGERweb layer %d returned no features" % layer)
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


# --- the offline gate: the shipped bytes on their own -----------------------
def _by_basename(features):
    return {(f["properties"].get("BASENAME") or "").strip(): f for f in features}


def check_partition(built):
    """Each layer, on the shipped bytes alone: complete numbering, no overlap.

    Two questions, neither of which needs the network or the source:

    * NUMBERING. A chamber's districts are numbered 1..N with no gap and no
      repeat. Measured 2026-09-29, Indiana ships no water pseudo-district on
      any of the three layers — every feature carries a number — but TIGER
      does ship them for other states (Illinois's ZZ features), so a feature
      whose BASENAME is prose rather than a number is counted and reported
      separately instead of failing the numbering.
    * SELF-OVERLAP. PARTITION_SAMPLES points over the state envelope must land
      in at most ONE district of each layer. A simplification that folded two
      neighbours into an overlap, or a hand-edit that broke a ring, fails here.

    The sample is over the worksheet's permalink_gate rather than the tight
    state bbox, on purpose: it includes ground outside Indiana, where every
    layer must classify nothing, so a district whose rings blew out to the
    envelope cannot pass by covering everything.
    """
    problems = []
    lines = []
    rng = random.Random(2026)
    pts = [(rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
            rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
           for _ in range(PARTITION_SAMPLES)]
    for name in sorted(built):
        feats = built[name]["features"]
        nums, prose = [], []
        for f in feats:
            key = (f["properties"].get("BASENAME") or "").strip()
            (nums if key.isdigit() else prose).append(key)
        want = LAYERS[name]["min_features"]
        got = sorted(int(n) for n in nums)
        if len(set(got)) != len(got):
            dupes = sorted({n for n in got if got.count(n) > 1})
            problems.append("%s: district number(s) appear twice: %s" % (name, dupes))
        elif got != list(range(1, want + 1)):
            problems.append("%s: districts are not 1..%d — got %d number(s), "
                            "first gap or extra near %s"
                            % (name, want, len(got),
                               next((i + 1 for i, v in enumerate(got) if v != i + 1), "the end")))
        model = _model(feats, VALIDATION_KEY)
        overlaps = sum(1 for pt in pts if len(_districts_at(model, pt)) > 1)
        if overlaps:
            problems.append("%s: %d of %d sampled points fell in more than one district"
                            % (name, overlaps, len(pts)))
        lines.append("%s %d districts + %d water pseudo-district(s), 0 overlaps"
                     % (name, len(nums), len(prose)))
    if not lines:
        return False, "no layers were read — LAYERS or the shipped files are wrong"
    if problems:
        return False, "; ".join(problems)
    return True, "; ".join(lines)


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
#     agrees with what the app computes at runtime) — same as build_embedded_boundaries.py ---
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


def validate(source_features, simplified_features, key_prop, samples=2000, seed=2024):
    """Refuse the simplification unless it preserves district coverage vs the
    pre-simplification fetch, the project's way (2,000 uniform random points over
    the bbox; any point in two simplified districts is a topology break)."""
    if len(simplified_features) != len(source_features):
        return False, "feature count changed: %d -> %d" % (len(source_features), len(simplified_features))
    src_props = sorted(tuple(sorted(f["properties"].items())) for f in source_features)
    new_props = sorted(tuple(sorted(f["properties"].items())) for f in simplified_features)
    if src_props != new_props:
        return False, "feature properties changed during simplification"

    src = _model(source_features, key_prop)
    new = _model(simplified_features, key_prop)
    ob = [1e9, 1e9, -1e9, -1e9]
    for _, _, bb in src:
        ob[0], ob[1] = min(ob[0], bb[0]), min(ob[1], bb[1])
        ob[2], ob[3] = max(ob[2], bb[2]), max(ob[3], bb[3])

    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(ob[0], ob[2]), rng.uniform(ob[1], ob[3]))
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
    return True, "%d/%d (%.2f%%) agreement, 0 overlaps" % (agree, samples, pct)


def build_family():
    """Fetch every chamber, simplify them as ONE topology, gate, then write."""
    source = {}
    for name, cfg in LAYERS.items():
        geo = fetch_tiger(cfg["layer"], cfg["fields"])
        if len(geo["features"]) < cfg["min_features"]:
            raise RuntimeError(
                "%s: only %d features fetched (need >= %d) — refusing to write"
                % (name, len(geo["features"]), cfg["min_features"]))
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

    # gate 2, the shipped bytes on their own: complete numbering, no overlap
    ok, msg = check_partition(built)
    if not ok:
        raise RuntimeError("partition check failed: %s" % msg)
    print("  partition  %s" % msg, file=sys.stderr)

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
          "metro-worksheet.json and re-run generate_metro_files.py, or a "
          "returning visitor keeps the old geometry.", file=sys.stderr)


def check_shipped():
    """Offline: the partition gate on the files in data/app. This is the CI gate.

    It needs no network and no source fetch, because complete numbering and
    self-overlap are properties of the shipped bytes alone. The fidelity gate
    cannot run here: it needs the TIGER fetch to compare against, so it is
    build-time only, and Indiana has no cross-layer nesting for a third gate to
    check (see the module docstring).
    """
    built = {}
    for name, cfg in LAYERS.items():
        path = os.path.join(APP_DATA_DIR, cfg["out"])
        if not os.path.exists(path):
            print("build-legislative-boundaries: FAIL — %s is missing" % cfg["out"],
                  file=sys.stderr)
            return 1
        with open(path) as f:
            built[name] = json.load(f)
    ok, msg = check_partition(built)
    if not ok:
        print("build-legislative-boundaries: FAIL — %s\n"
              "  Rebuild the WHOLE family "
              "(python3 in/scripts/build_legislative_boundaries.py)." % msg, file=sys.stderr)
        return 1
    print("build-legislative-boundaries: OK — %s" % msg)
    return 0


def main():
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(check_shipped())
    if args:
        print("unexpected argument(s): %s\n"
              "This builder has no per-chamber mode: the family shares one topology, "
              "so the family is the unit.\n"
              "  (no args) fetch and rebuild all three\n"
              "  --check   offline partition gate on the shipped files"
              % args, file=sys.stderr)
        sys.exit(1)
    build_family()


if __name__ == "__main__":
    main()
