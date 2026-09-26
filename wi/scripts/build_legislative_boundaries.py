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
7.9 m on retained rings against a 15 m ceiling, with one dropped ring declared
(ACCEPTED_DROPPED_RINGS).

INTERVAL=7 RATHER THAN THE COARSEST SETTING THAT CLEARS THE CEILING, AND THE
REASON IS NOT THE METRES. The curve measured the same day, worst stray on
retained rings: interval=4 5.2 m, 5 5.7, 6 7.7, 7 7.9, 8 11.1, 10 12.1, 12 15.6
(over), 15 20.0. So interval=10 also clears 15 m and costs 40.5% more than main
rather than 74.3% -- and at interval 8 and coarser a SECOND ring goes, 590 m2 of
the Cudahy lakefront, taking a reader there out of Senate 7 and Assembly 20 into
the water pseudo-district. That is a false answer about ground a person can stand
on rather than a silence, and the size of the patch changes how many readers meet
it, not what kind of error it is. interval=7 loses one ring instead of two.

IT DOES NOT LOSE NONE, and this project recorded otherwise for a few hours. The
Door County ring below is dropped at every interval from 4 to 15, and a reader
inside it reads district 1 in the source and the water pseudo-district in the
shipped file. The first reading of that ring said no reader's answer moved,
because it tested the ring's centroid rounded to four decimals -- outside a ring
7.5 m across. So the honest claim for interval=7 is that it loses one 31.7 m2
patch of open Lake Michigan that no measured setting keeps, not that it loses
nothing.

WHAT IT COSTS, PUBLISHED RATHER THAN SMOOTHED, AND MEASURED WITH ITS METHOD --
`gzip -c` over the bytes git holds, against `git show origin/main:<path>` rather
than the working tree, which is how a first reading of this got +0.0% by
comparing the candidate with itself. The two files go from 443,452 to 772,931
bytes gzipped, +329,479 (+74.3%), on geometry `sw.js` serves cache-first, so
every first-load visitor pays it whether or not they ever switch a chamber on.
Illinois's equivalent change came out 871 bytes SMALLER because its old files were
far less aggressive than Wisconsin's; here correctness costs real bytes, and that
trade is worth stating next to a median stray of 80.1 m on the boundaries a reader
is standing beside.

AND THE "EVERY FIRST-LOAD VISITOR" HALF OF THAT STOPPED BEING TRUE HOURS AFTER IT
WAS WRITTEN. It said docs/OPTIMIZATION_PLAYBOOK.md section 10 PLANNED (phase 2) to
stop precaching boundary files at install, and called it "a plan, not code, so it
is a reason the cost is probably temporary and not a reason to discount it". It is
code: #1197 (2026-09-26) sets `PRECACHE_URLS = SHELL_URLS` in wi/sw.js, so the
install handler no longer fetches GEOMETRY_URLS and a boundary file is cached the
first time a layer uses it. The bytes above are unchanged -- they are still what the
two files weigh -- and who pays them is not: a reader who never switches a chamber
on never downloads either file, and cannot read them offline either, which the
privacy page states. The interval ruling was deliberately made WITHOUT leaning on
the plan, so nothing about interval=7 turns on this; what needed correcting is a
comment that went on calling something a plan after it shipped.

Four gates run before anything is written, and each answers a question the
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
  * check_fidelity() -- against the SOURCE: no point on a RETAINED ring of the
                        true boundary may lie further than FIDELITY_MAX_M from
                        the line drawn for it. Needs the fetch, so it is
                        build-time only. It sets dropped rings ASIDE rather than
                        measuring them in, because a dropped ring is a shape that
                        is gone rather than a chord cut across a corner, and
                        pooling the two makes the ceiling a function of the
                        smallest ring in the state.
  * check_dropped_rings()
                     -- every ring check_fidelity set aside must be declared in
                        ACCEPTED_DROPPED_RINGS, every declaration must still be
                        found, and each one's reader answers are VERIFIED by
                        placing a point inside the ring and asking both feature
                        sets which districts contain it. Wisconsin is the first
                        instance in the fleet where a ring went at all.
If any gate fails, nothing is written.

`--check` IS THE CI GATE, and it closes the gap the change that added these gates
recorded rather than closed: until 2026-09-26 this builder took no arguments at
all, so nothing in CI re-asked the nesting question about the SHIPPED files, where
Illinois's and Iowa's builders both did. It runs the two halves that need no
fetch -- the nesting relation between the two shipped layers, and each declared
dropped ring's AFTER answer re-derived from the shipped bytes at the interior point
the declaration records. It cannot see an UNDECLARED drop or any BEFORE answer,
because both need the source; check_shipped()'s own docstring says so rather than
leaving a reader to assume a green check means the declarations are complete.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 wi/scripts/build_legislative_boundaries.py            # both chambers
    python3 wi/scripts/build_legislative_boundaries.py --check    # offline CI gate

IT TAKES NO ARGUMENTS. Rebuilding one chamber on its own is the defect the
combined run exists to fix, so main() refuses any argument rather than quietly
writing a file that no longer shares a topology with its sibling. `us-house`
stays in LAYERS as a target a redistricting re-run can reach by editing FAMILY,
which is a deliberate edit rather than a command line away.
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

# The fidelity ceiling, in metres: no point on a RETAINED ring of the true
# boundary may lie further than this from the line drawn for it. DERIVED FROM
# WISCONSIN'S OWN GEOMETRY rather than copied from Illinois's 25 m, and the
# derivation took two goes.
#
# "Wisconsin's median vertex step" -- how far the true line runs before it turns
# -- IS NOT ONE QUANTITY, and the first ceiling was set from one reading of it
# without saying which. Measured on the TIGERweb source both chambers carry:
#     senate, every ring          12.43 m
#     assembly, every ring        14.71 m   <- the figure the first 20 m came from
#     both chambers pooled        13.59 m
#     senate, water row excluded  15.66 m
#     assembly, water excluded    19.30 m
#     both pooled, water excluded 17.63 m
# Six answers spanning 12.4 to 19.3 m. The reading that matches the population
# THIS GATE measures over -- both chambers, every ring, the water pseudo-district
# included -- is 13.59 m, and 15 m is 1.10x it. Which reading is meant matters:
# the pooled water-excluded reading would put the ceiling near 19 m and admit a
# coarser interval. The 20 m this replaced came of taking the assembly-only
# 14.71 m and multiplying by 25/17.9 = 1.40, Illinois's own ceiling over its own
# step, which is Illinois rounding rather than a transferable ratio.
#
# A MEDIAN STEP IS NOT A FLOOR ON ACHIEVABLE STRAY, which is the other thing the
# first derivation assumed. dp thresholds PERPENDICULAR DEVIATION, so a removed
# vertex offset by little from its neighbours' chord costs little however far
# apart they are: interval=4 measures a 5.2 m worst against that 13.59 m step.
#
# SIMPLIFY delivers a statewide worst of 7.9 m on retained rings, which clears
# this with margin rather than sitting on it. The coarser settings measured the
# same day: interval=8 11.1 m, interval=10 12.1 m, interval=12 15.6 m (over),
# interval=15 20.0 m. interval=10 also clears 15 m, at 40.5% more bytes than
# main instead of 74.3% -- and it was NOT taken, because at interval 8 and
# coarser a 590 m2 patch of the Cudahy lakefront leaves Senate 7 and Assembly 20
# for the water pseudo-district, so a reader standing there would be told they
# are inside no district in this layer. That is a false answer rather than a
# silence. interval=7 changes no reader's answer anywhere in the state, which is
# the measurement the setting rests on (ACCEPTED_DROPPED_RINGS below).
FIDELITY_MAX_M = 15.0

# A SOURCE RING COUNTS AS DROPPED when none of its own vertices survived, and
# this is the threshold for "survived", in metres. Simplification KEEPS a subset
# of the source vertices, so a retained ring holds at least one of its own
# exactly and its minimum distance to the drawn line is 0 up to floating point;
# a dropped ring has every vertex off that line. 1 m is far above the float
# noise and far below any real stray.
#
# The one way this reads wrong is safe: a dropped ring lying exactly on ANOTHER
# ring's drawn line would measure as retained, and its stray would then be held
# to FIDELITY_MAX_M -- stricter than the declaration table, never looser.
RETAINED_RING_M = 1.0

# How close a dropped ring's centre must be to a declared one to be the same
# ring, in metres, and how far its area may differ.
RING_MATCH_M = 25.0
RING_MATCH_AREA = 0.10

# Rings the simplifier drops, declared one by one. THE CEILING ABOVE IS MEASURED
# ON RETAINED RINGS ONLY, because a dropped ring is a different failure: it is a
# shape that is gone rather than a chord cut across a corner, no `interval` makes
# it reappear, and measuring it into the stray makes the ceiling a function of
# the smallest ring in the state. The Door County ring below sits 17.4-19.9 m out
# at EVERY interval from 4 to 15, so an all-vertex reading would put the floor
# near 20 m however fine the setting.
#
# So each dropped ring FAILS unless it is declared here, and each entry FAILS
# when nothing matches it -- the shape ACCEPTED_DROPS, EXPECTED_UNREACHABLE and
# ACCEPTED_SHORTFALLS already use elsewhere in the fleet.
#
# `answer_before` / `answer_after` ARE THE LOAD-BEARING FIELDS AND ARE VERIFIED
# RATHER THAN RECORDED: the gate finds a point provably inside the ring and asks
# the source features and the drawn features which districts contain it, and
# fails if either differs from what the entry claims. Without that the gate
# cannot tell a ring whose loss moves no reader's answer from one whose loss
# tells a reader they are in no district -- which is the whole difference between
# interval=7 and interval=8 for Wisconsin.
#
# Wisconsin is the first instance in the fleet where a ring went at all: Illinois
# has none and Iowa measured 154 source rings against 154 drawn. `keep-shapes`
# does not prevent it, because it protects a SHAPE and not a RING -- a
# multipolygon is one feature, so once one ring survives the guarantee is met and
# every other ring is eligible for removal like any other geometry. Any state
# whose districts carry islands or shoreline slivers must measure rings rather
# than features.
ACCEPTED_DROPPED_RINGS = [
    {
        # A 31.7 m2 outer ring -- a separate PART of district 1, not a hole -- in
        # open Lake Michigan off Door County, on the Wisconsin/Michigan water
        # line: 7.5 m by 6.6 m, six vertices. Dropped at EVERY interval from 4 to
        # 15, and its own vertices sit 17.4-19.9 m from the drawn line whatever
        # the setting, so no dp interval retains it and an all-vertex ceiling
        # would have to be 20 m to pass at all.
        #
        # ITS LOSS DOES MOVE A READER'S ANSWER, which is the opposite of what this
        # project first recorded about it and the reason the declaration is worth
        # having. 610 of 900 points provably inside it read district 1 in the
        # source and the water pseudo-district in the shipped file, in both
        # chambers. The first reading tested the ring's centroid ROUNDED TO FOUR
        # DECIMALS, which lands outside a ring this small, and so reported the
        # surrounding water and concluded nothing moved.
        #
        # It is declared rather than tolerated silently because no measured
        # setting avoids it, and it is 31.7 m2 of open water rather than the
        # 590 m2 of Cudahy lakefront that interval=8 and coarser also lose.
        "lat": 45.41074, "lng": -86.85963, "verts": 6, "m2": 31.7,
        # A point PROVABLY INSIDE the ring, measured at build time and re-used by
        # `--check`, which has no source to scan. Six decimals: the sixth is about
        # 0.1 m here, so it is well inside a ring 7.5 m across. FOUR would not be
        # -- at 45.41 N the fourth decimal is 11.05 m of latitude and 7.81 m of
        # longitude, so rounding to it displaces a point by up to 5.53 m and
        # 3.91 m, comparable to this ring's half-width. The unrounded centroid
        # (45.410745,-86.859628) is inside; the ROUNDED one is not, which is the
        # whole of the mistake this entry corrects.
        "interior": {"lat": 45.410736, "lng": -86.859659},
        "features": ["wi-assembly:1", "wi-assembly:State House Districts not defined",
                     "wi-senate:1", "wi-senate:State Senate Districts not defined"],
        "answer_before": {"wi-senate": ["1"], "wi-assembly": ["1"]},
        "answer_after": {"wi-senate": ["State Senate Districts not defined"],
                         "wi-assembly": ["State House Districts not defined"]},
        "why": "no dp interval from 4 to 15 retains it; 31.7 m2 of open Lake "
               "Michigan on the Michigan water line, and the reader answers it "
               "does move are recorded above rather than claimed harmless",
        "date": "2026-09-26",
    },
]

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


def _ring_centre(ring):
    """The mean of a ring's DISTINCT vertices, as (lng, lat).

    Stated rather than left to a library so a declared centre is reproducible:
    the closing vertex repeats the first, and including it pulls the mean.
    """
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _ring_verts(ring):
    """A ring's DISTINCT vertex count — the closing repeat is not a vertex."""
    return len(ring) - 1 if len(ring) > 1 and ring[0] == ring[-1] else len(ring)


def _ring_area_m2(ring):
    """Shoelace area in square metres, on the local metre scaling.

    These rings are metres across, so a flat approximation at the ring's own
    latitude is exact to far more precision than the declaration needs.
    """
    sx, sy = _mscale(ring[0][1])
    a = 0.0
    for i in range(len(ring) - 1):
        a += (ring[i][0] * sx) * (ring[i + 1][1] * sy) - (ring[i + 1][0] * sx) * (ring[i][1] * sy)
    return abs(a) / 2.0


def _ring_interior_point(ring):
    """A point provably inside the ring, or None.

    A centroid can fall outside a concave ring, so this scans a grid across the
    ring's own bounding box and returns the first point the even-odd test puts
    inside. A ring too thin for the finest grid returns None, which the caller
    reports rather than guessing at.
    """
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    for n in (7, 15, 31, 63):
        for i in range(1, n):
            for j in range(1, n):
                pt = (min(xs) + (max(xs) - min(xs)) * i / n,
                      min(ys) + (max(ys) - min(ys)) * j / n)
                if _point_in_ring(pt, ring):
                    return pt
    return None


def check_fidelity(source_features, drawn_features, limit=None):
    """No point on a RETAINED ring of the TRUE boundary may lie further than
    `limit` from the drawn line. Returns (ok, message, dropped_rings).

    The direction matters and the obvious one gates nothing: simplification KEEPS
    a subset of the source vertices, so every drawn vertex already sits on the
    source line and measuring drawn -> source answers ~0 by construction. What a
    reader sees is the true line straying from the chord drawn in its place, so
    that is what this measures.

    AND IT MEASURES IT ON RETAINED RINGS ONLY. A ring none of whose own vertices
    survived is not a stray the interval controls -- it is a shape that is gone,
    and pooling the two makes this ceiling a function of the smallest ring in the
    state (see RETAINED_RING_M and ACCEPTED_DROPPED_RINGS). The dropped rings are
    returned rather than swallowed, and check_dropped_rings() is what holds them
    to their declarations.
    """
    limit = FIDELITY_MAX_M if limit is None else limit
    src = _by_basename(source_features)
    drawn = _by_basename(drawn_features)
    worst, where, wkey = 0.0, None, None
    over = 0
    dropped = []
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
            ds = [_dist_to_drawn((pt[0], pt[1]), grid, cell, sx, sy) for pt in r]
            if min(ds) > RETAINED_RING_M:
                dropped.append({
                    "basename": key,
                    "centre": _ring_centre(r),
                    "verts": _ring_verts(r),
                    "m2": _ring_area_m2(r),
                    "worst": max(ds),
                    "ring": r,
                })
                continue
            for pt, d in zip(r, ds):
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
    if over:
        return False, ("%d district(s) stray further than %.0f m from the true line; "
                       "worst is %s at %.1f m (%.5f,%.5f)"
                       % (over, limit, _name_district(wkey), worst, where[1], where[0])), dropped
    return True, ("worst stray %.1f m on retained rings, %s; ceiling %.0f m; "
                  "%d ring(s) dropped"
                  % (worst, _name_district(wkey), limit, len(dropped))), dropped


def _name_district(key):
    return ("district %s" % key) if (key or "").isdigit() else (
        "the water pseudo-district (%s)" % key)


def check_dropped_rings(found, sources, built):
    """Every dropped ring must be declared, and every declaration must be found.

    `found` is {chamber: [ring dicts from check_fidelity]}. One RING GEOMETRY can
    be dropped from several features at once -- a sliver on the water boundary
    sits in a land district and in the water pseudo-district, in both chambers --
    so declarations are keyed by the ring and carry the features they appear in.

    THE READER-ANSWER FIELDS ARE VERIFIED, NOT TAKEN ON TRUST: for each declared
    ring the gate finds a point provably inside it and asks the SOURCE features
    and the DRAWN features which districts contain it, then fails if either
    answer differs from the declaration. That is the only thing separating a
    dropped ring whose loss moves no reader's answer from one whose loss tells a
    reader they are in no district at all.

    THE ANSWERS ARE DECLARED PER CHAMBER, because the after-answer differs by
    chamber even for one ring: the Door County ring leaves Senate 1 for the Senate
    water row and Assembly 1 for the ASSEMBLY water row, which are different
    strings. Testing one chamber and assuming the other would leave half of each
    declaration unchecked.

    AND A ROUNDED CENTROID IS NOT AN INTERIOR POINT. The first reading of this
    ring tested its centroid rounded to four decimals, which for a ring 7.5 m
    across lands OUTSIDE it, and so measured the surrounding water: it reported
    that no reader's answer moved, when 610 of 900 points provably inside the ring
    move from district 1 to the water pseudo-district. That is why the point comes
    from _ring_interior_point and never from a rounded coordinate.
    """
    # Group the findings by ring geometry, across chambers.
    groups = []
    for chamber, rings in sorted(found.items()):
        for r in rings:
            label = "%s:%s" % (chamber, r["basename"])
            for g in groups:
                if _ring_dist_m(g["centre"], r["centre"]) <= RING_MATCH_M \
                   and g["verts"] == r["verts"]:
                    g["features"].append(label)
                    g["worst"] = max(g["worst"], r["worst"])
                    break
            else:
                groups.append({
                    "centre": r["centre"], "verts": r["verts"], "m2": r["m2"],
                    "worst": r["worst"], "features": [label], "ring": r["ring"],
                    "chambers": [chamber],
                })
    for g in groups:
        g["features"].sort()
        g["chambers"] = sorted(set(f.split(":", 1)[0] for f in g["features"]))

    problems = []
    matched = set()
    for g in groups:
        hit = None
        for i, e in enumerate(ACCEPTED_DROPPED_RINGS):
            if _ring_dist_m((e["lng"], e["lat"]), g["centre"]) <= RING_MATCH_M \
               and e["verts"] == g["verts"]:
                hit = i
                break
        if hit is None:
            problems.append(
                "UNDECLARED dropped ring at %.5f,%.5f — %d vertices, %.1f m2, "
                "worst %.1f m, dropped from %s. Declare it in "
                "ACCEPTED_DROPPED_RINGS with the answer a reader gets before and "
                "after, or change SIMPLIFY so it survives."
                % (g["centre"][1], g["centre"][0], g["verts"], g["m2"], g["worst"],
                   ", ".join(g["features"])))
            continue
        matched.add(hit)
        e = ACCEPTED_DROPPED_RINGS[hit]
        if e["m2"] and abs(g["m2"] - e["m2"]) > RING_MATCH_AREA * e["m2"]:
            problems.append(
                "the ring at %.5f,%.5f measures %.1f m2 where its declaration "
                "says %.1f m2 — same place and vertex count, different ring"
                % (g["centre"][1], g["centre"][0], g["m2"], e["m2"]))
        if list(e["features"]) != g["features"]:
            problems.append(
                "the ring at %.5f,%.5f is dropped from %s where its declaration "
                "says %s" % (g["centre"][1], g["centre"][0],
                             ", ".join(g["features"]), ", ".join(e["features"])))
        if sorted(e["answer_before"]) != g["chambers"] \
           or sorted(e["answer_after"]) != g["chambers"]:
            problems.append(
                "the ring at %.5f,%.5f is dropped in %s, so its answer_before and "
                "answer_after must each name exactly those chambers"
                % (g["centre"][1], g["centre"][0], ", ".join(g["chambers"])))
            continue
        # THE DECLARED point is the test point, not a freshly scanned one, because
        # `--check` has no source ring to scan and must re-ask the same question
        # offline. It is proved to be inside the ring here, which is the half that
        # cannot be done offline.
        pt = None
        if e.get("interior"):
            pt = (e["interior"]["lng"], e["interior"]["lat"])
            if not _point_in_ring(pt, g["ring"]):
                problems.append(
                    "the ring at %.5f,%.5f declares an interior point at %.6f,%.6f "
                    "that is NOT inside it — a rounded centroid is the usual cause"
                    % (g["centre"][1], g["centre"][0], pt[1], pt[0]))
                continue
        else:
            scanned = _ring_interior_point(g["ring"])
            problems.append(
                "the ring at %.5f,%.5f declares no interior point, so --check "
                "cannot re-ask its reader answers offline; record "
                '"interior": {"lat": %s, "lng": %s}'
                % (g["centre"][1], g["centre"][0],
                   ("%.6f" % scanned[1]) if scanned else "?",
                   ("%.6f" % scanned[0]) if scanned else "?"))
            continue
        for chamber in g["chambers"]:
            got = {
                "before": sorted(_districts_at(
                    _model(sources[chamber]["features"], "BASENAME"), pt)),
                "after": sorted(_districts_at(
                    _model(built[chamber]["features"], "BASENAME"), pt)),
            }
            for label in ("before", "after"):
                want = sorted(e["answer_" + label].get(chamber) or [])
                if got[label] != want:
                    problems.append(
                        "the ring at %.5f,%.5f: a reader at %.5f,%.5f is in %s %s "
                        "in %s, where its declaration says %s"
                        % (g["centre"][1], g["centre"][0], pt[1], pt[0],
                           chamber, got[label] or ["no district"], label, want))

    for i, e in enumerate(ACCEPTED_DROPPED_RINGS):
        if i not in matched:
            problems.append(
                "ORPHANED declaration: no dropped ring matches the one at %.5f,%.5f "
                "(%d vertices) any more — retire the entry"
                % (e["lat"], e["lng"], e["verts"]))

    if problems:
        return False, "; ".join(problems)
    if not groups:
        return True, "no ring was dropped"
    return True, "; ".join(
        "one ring dropped from %d feature(s) and declared: %.5f,%.5f (%d verts, "
        "%.1f m2, worst %.1f m) — %s"
        % (len(g["features"]), g["centre"][1], g["centre"][0], g["verts"], g["m2"],
           g["worst"], _ring_answer_text(ACCEPTED_DROPPED_RINGS, g))
        for g in groups)


def _ring_answer_text(entries, g):
    """Per chamber, what a reader inside the ring reads before and after."""
    for e in entries:
        if _ring_dist_m((e["lng"], e["lat"]), g["centre"]) <= RING_MATCH_M \
           and e["verts"] == g["verts"]:
            return "; ".join(
                "%s: %s -> %s" % (c,
                                  ", ".join(e["answer_before"].get(c) or ["no district"]),
                                  ", ".join(e["answer_after"].get(c) or ["no district"]))
                for c in g["chambers"])
    return "?"


def _ring_dist_m(a, b):
    sx, sy = _mscale(a[1])
    return math.hypot((a[0] - b[0]) * sx, (a[1] - b[1]) * sy)


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
    dropped = {}
    for name in FAMILY:
        ok, msg, drops = check_fidelity(sources[name]["features"], built[name]["features"])
        dropped[name] = drops
        if not ok:
            raise RuntimeError("%s fidelity check failed: %s" % (name, msg))
        print("fidelity %s: %s" % (name, msg), file=sys.stderr)

    # gate 4, on the rings gate 3 set aside: every dropped ring declared, every
    # declaration still found, and each one's reader answers verified rather than
    # trusted. This is the gate that distinguishes a lost sliver nobody can reach
    # from one that would tell a reader they are in no district.
    ok, msg = check_dropped_rings(dropped, sources, built)
    if not ok:
        raise RuntimeError("dropped-ring check failed: %s" % msg)
    print("dropped rings: %s" % msg, file=sys.stderr)

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


def check_shipped():
    """Offline: the two halves that need no fetch, on the files in data/app.

    This is the CI gate, and it exists because a correct file with no gate watching
    it is one rebuild away from being wrong quietly -- which is exactly what this
    builder's own history demonstrates, since the 2.9 km stray shipped for months
    with every gate green.

    WHAT IT ASKS:
      * the NESTING relation BETWEEN the two shipped layers, which is the
        regression a per-chamber rebuild would reintroduce and which needs nothing
        but the two files;
      * each declared dropped ring's AFTER answer, re-derived from the shipped
        bytes at the interior point the declaration records -- so a rebuild that
        stopped dropping a declared ring, or dropped it into a different district,
        fails here rather than at the next operator build.

    WHAT IT CANNOT ASK, STATED RATHER THAN IMPLIED. Both need the TIGER source:
    whether a ring is still being dropped AT ALL (an undeclared drop is invisible
    offline, because nothing here knows what the true boundary carries), and every
    declaration's BEFORE answer. Those stay build-time, in check_fidelity() and
    check_dropped_rings(). So a green `--check` means the shipped files still nest
    and still say what the declarations claim they say -- not that the declarations
    are complete.

    A THIRD BLIND SPOT, FOUND BY NEGATIVE-TESTING THIS FUNCTION: it cannot tell that
    a declared interior point is actually INSIDE its ring. Rounded back to four
    decimals -- the exact defect the Door County entry corrects -- the point falls
    outside the ring and still passes here, because the water pseudo-district it
    lands in is what the declaration says a reader reads. Only the build path can
    catch that, and it does: check_dropped_rings() refuses a declared point that
    _point_in_ring rejects.
    """
    built = {}
    for name in FAMILY:
        path = os.path.join(APP_DATA_DIR, LAYERS[name]["out"])
        if not os.path.exists(path):
            print("build-legislative-boundaries: FAIL — %s is missing"
                  % LAYERS[name]["out"], file=sys.stderr)
            return 1
        with open(path) as f:
            built[name] = json.load(f)

    ok, msg = check_nesting(built)
    if not ok:
        print("build-legislative-boundaries: FAIL — %s\n"
              "  Rebuild the WHOLE family (python3 wi/scripts/build_legislative_boundaries.py); "
              "simplifying one chamber alone is what breaks this." % msg, file=sys.stderr)
        return 1

    problems = []
    for e in ACCEPTED_DROPPED_RINGS:
        if not e.get("interior"):
            problems.append(
                "the declaration at %.5f,%.5f records no interior point, so its "
                "reader answer cannot be re-asked offline" % (e["lat"], e["lng"]))
            continue
        pt = (e["interior"]["lng"], e["interior"]["lat"])
        for chamber in sorted(e["answer_after"]):
            if chamber not in built:
                problems.append(
                    "the declaration at %.5f,%.5f names chamber %s, which this "
                    "builder does not build" % (e["lat"], e["lng"], chamber))
                continue
            got = sorted(_districts_at(
                _model(built[chamber]["features"], "BASENAME"), pt))
            want = sorted(e["answer_after"][chamber] or [])
            if got != want:
                problems.append(
                    "the declaration at %.5f,%.5f says a reader at %.6f,%.6f reads "
                    "%s in the shipped %s, and the shipped file says %s"
                    % (e["lat"], e["lng"], pt[1], pt[0], want, chamber,
                       got or ["no district"]))
    if problems:
        print("build-legislative-boundaries: FAIL — %s\n"
              "  A declared dropped ring no longer reads the way it is declared to. "
              "Rebuild and re-measure rather than editing the declaration to match."
              % "; ".join(problems), file=sys.stderr)
        return 1

    print("build-legislative-boundaries: OK — %s; %d declared dropped ring(s) still "
          "read as declared in the shipped files (offline: nesting and the AFTER "
          "answers only — an undeclared drop and every BEFORE answer need the source)"
          % (msg, len(ACCEPTED_DROPPED_RINGS)))
    return 0


def main():
    args = sys.argv[1:]
    if "--check" in args and len(args) == 1:
        sys.exit(check_shipped())
    if args:
        print("unexpected argument(s): %s\n"
              "This builder has no per-chamber mode: both chambers are simplified in "
              "ONE run so a shared edge is one arc, and rebuilding one alone is the "
              "defect that shape exists to fix.\n"
              "  (no args) fetch and rebuild both chambers\n"
              "  --check   offline gate on the shipped files (nesting + the declared "
              "dropped rings' after answers)" % args, file=sys.stderr)
        sys.exit(1)
    build_family()


if __name__ == "__main__":
    main()
