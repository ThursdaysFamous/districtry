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
ring that no measured setting keeps, not that it loses nothing. CORRECTED
2026-09-27: this said "one 31.7 m2 patch of OPEN LAKE MICHIGAN", and it is DRY
LAND -- see the declaration below for the measurement and for why inferring water
from a coordinate was the mistake.

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
  * dropped_rings.check()
                     -- every ring whose loss costs a reader the right answer
                        must be declared in ACCEPTED_DROPPED_RINGS, every
                        declaration must still be found, and each one's reader
                        answers are VERIFIED by placing a point inside the ring
                        and asking both feature sets which districts contain it.
                        Wisconsin is the first instance in the fleet where a ring
                        went at all.

                        IT IS THE SHARED MODULE SINCE 2026-09-27, not this
                        builder's own gate. `wi/scripts/dropped_rings.py` was
                        lifted out of here for the supervisory layer, which drops
                        402 rings against this family's one, and this builder then
                        kept a hand-written copy of the same question for a day.
                        Two readers of one question is where this fleet's
                        recurring defect starts, and the module's own fixture
                        selftest is a gate in CI where the copy here was exercised
                        only by an operator build. It decides the dropped set ONCE
                        for both gates: check_fidelity() is handed the signatures
                        rather than re-deriving them from its own threshold.
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

import dropped_rings as drings

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

# THE DROPPED-RING THRESHOLDS ARE THE SHARED MODULE'S, NOT A SECOND COPY.
# `dropped_rings.RETAINED_RING_M` is the distance at which a source vertex counts
# as having survived, `RING_MATCH_M` and `RING_MATCH_AREA` are how close a dropped
# ring must be to a declared one to be the same ring. They lived here as well
# until 2026-09-27, which is the two-readers shape this repo keeps paying for: two
# files agreeing about a threshold by coincidence rather than by construction.

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
# Holes that no district covered and the drawn output now fills. They are NOT
# declared one by one -- see `dropped_rings.check` -- but the COUNT is held
# exactly, so a rebuild that starts closing a different number of them stops and
# gets read.
#
# ZERO, AND THAT IS A MEASUREMENT RATHER THAN AN OMISSION. Measured 2026-09-27 on
# the TIGERweb source both chambers carry, against the shipped files (which the
# same pipeline reproduces byte for byte): the whole family drops exactly ONE
# ring statewide, the Door County one declared below, and closes no coverage gap
# anywhere. The supervisory layer at the same threshold closes 229, which is the
# difference between a state-published district map and a county-by-county
# dissolve: TIGER's chambers tile Wisconsin with one water pseudo-district per
# chamber and carry no slivers between neighbours, so there are no uncovered
# holes for simplification to fill.
GAP_CLOSED = 0

ACCEPTED_DROPPED_RINGS = [
    {
        # A 31.7 m2 outer ring -- a separate PART of district 1, not a hole -- on
        # WASHINGTON ISLAND, Door County, near the Wisconsin/Michigan water line:
        # 7.5 m by 6.6 m, six vertices. Dropped at EVERY interval from 4 to 15,
        # and its own vertices sit 17.4-19.9 m from the drawn line whatever the
        # setting, so no dp interval retains it and an all-vertex ceiling would
        # have to be 20 m to pass at all.
        #
        # IT IS ON DRY LAND, AND THIS ENTRY SAID "OPEN LAKE MICHIGAN" UNTIL
        # 2026-09-27. Measured against TIGER's own AREAL HYDROGRAPHY layer at both
        # the centre and the declared interior point: no water polygon at either,
        # where a control in open Lake Michigan returns "Lk Michigan" and one in
        # Lake Winnebago returns "Lk Winnebago". TIGER's county-subdivision layer
        # puts both points in WASHINGTON TOWN, which is Washington Island and is
        # inhabited. The claim came from reading the coordinate and knowing Door is
        # a peninsula -- an INFERENCE shipped as a measurement, and the same error
        # `build_wi_supervisory_districts.py` made about its own Door residual on
        # the same day. A subdivision is not the test either, because a town's
        # polygon can include its own shoreline water; hydrography is.
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
        # setting avoids it. The size comparison it was first written with stands
        # -- 31.7 m2 against the 590 m2 of Cudahy lakefront that interval=8 and
        # coarser also lose -- but the WATER half of that sentence does not, and
        # the dry-land reading makes this declaration matter MORE rather than
        # less: it is ground a person can stand on.
        #
        # THE CORRECTION MISSED THIS ENTRY'S OWN `why` FIELD FOR A DAY, and how
        # is worth more than the fact. Three copies of the false claim were found
        # and fixed on 2026-09-26 by grepping for "open Lake Michigan"; the
        # fourth was in the `why` below, where the string is split across a line
        # break as "open Lake " / "Michigan on the", so the phrase matches no
        # line and grep reported the file clean. A LINE-BASED SEARCH CANNOT FIND
        # A WRAPPED STRING: when sweeping a claim out of a tree, grep for the
        # shortest single-line fragment ("Lake Michigan", "open Lake") or read
        # the declarations, and never take a zero from a phrase long enough to
        # wrap as evidence of absence.
        "lat": 45.41074, "lng": -86.85963, "verts": 6, "m2": 31.7,
        # A point PROVABLY INSIDE the ring, measured at build time and re-used by
        # `--check`, which has no source to scan. Six decimals: the sixth is about
        # 0.1 m here, so it is well inside a ring 7.5 m across. FOUR would not be
        # -- at 45.41 N the fourth decimal is 11.05 m of latitude and 7.81 m of
        # longitude, so rounding to it displaces a point by up to 5.53 m and
        # 3.91 m, comparable to this ring's half-width. The unrounded centroid
        # (45.410745,-86.859628) is inside; the ROUNDED one is not, which is the
        # whole of the mistake this entry corrects.
        "interior": {"lat": 45.410736, "lng": -86.859659, "decimals": 6},
        "features": ["wi-assembly:1", "wi-assembly:State House Districts not defined",
                     "wi-senate:1", "wi-senate:State Senate Districts not defined"],
        # THE MEASURED CLASS, not a label: the reader is told a DIFFERENT district
        # rather than none, so this is `wrong-name`. `dropped_rings.check` compares
        # it against what it computed and fails on a mismatch, which is what stops
        # a declaration describing the wrong harm.
        "kind": "wrong-name",
        "answer_before": {"wi-senate": ["1"], "wi-assembly": ["1"]},
        "answer_after": {"wi-senate": ["State Senate Districts not defined"],
                         "wi-assembly": ["State House Districts not defined"]},
        "why": "no dp interval from 4 to 15 retains it; 31.7 m2 on Washington "
               "Island, dry land by TIGER's own hydrography, and the reader "
               "answers it does move are recorded above rather than claimed "
               "harmless",
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


def check_fidelity(source_features, drawn_features, dropped_sigs, limit=None):
    """No point on a RETAINED ring of the TRUE boundary may lie further than
    `limit` from the drawn line. Returns (ok, message).

    The direction matters and the obvious one gates nothing: simplification KEEPS
    a subset of the source vertices, so every drawn vertex already sits on the
    source line and measuring drawn -> source answers ~0 by construction. What a
    reader sees is the true line straying from the chord drawn in its place, so
    that is what this measures.

    AND IT MEASURES IT ON RETAINED RINGS ONLY. A ring none of whose own vertices
    survived is not a stray the interval controls -- it is a shape that is gone,
    and pooling the two makes this ceiling a function of the smallest ring in the
    state (see ACCEPTED_DROPPED_RINGS).

    WHICH RINGS THOSE ARE IS THE CALLER'S ANSWER, in `dropped_sigs`, and that is
    the whole of what this migration changed here: this function used to decide it
    a second time with its own copy of the retained-ring threshold, so the fidelity
    gate and the dropped-ring gate agreed about the dropped set by coincidence
    rather than by construction. `dropped_rings.classify` decides it once and
    `dropped_rings.check` holds those rings to their declarations.
    """
    limit = FIDELITY_MAX_M if limit is None else limit
    src = _by_basename(source_features)
    drawn = _by_basename(drawn_features)
    worst, where, wkey = 0.0, None, None
    over = 0
    dropped = 0
    for key, sf in src.items():
        if key not in drawn:
            continue
        dr = drings.rings(drawn[key]["geometry"])
        sr = drings.rings(sf["geometry"])
        if not dr or not sr:
            continue
        sx, sy = drings.mscale(sr[0][0][1])
        grid, cell = drings.index_segments(dr)
        dworst = 0.0
        dwhere = None
        for r in sr:
            # The caller's answer, not a second reading of it (see the docstring).
            if drings.ring_signature(r) in dropped_sigs:
                dropped += 1
                continue
            ds = [drings.dist_to_drawn((pt[0], pt[1]), grid, cell, sx, sy) for pt in r]
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
                       % (over, limit, _name_district(wkey), worst, where[1], where[0]))
    return True, ("worst stray %.1f m on retained rings, %s; ceiling %.0f m; "
                  "%d ring(s) dropped"
                  % (worst, _name_district(wkey), limit, dropped))


def _name_district(key):
    return ("district %s" % key) if (key or "").isdigit() else (
        "the water pseudo-district (%s)" % key)


def validate(source_features, result_features, key_prop, samples=2000, seed=2024):
    """Refuse the build unless simplification preserves district coverage over
    the state envelope vs the full-precision fetch — the project's 2,000
    uniform-random-point protocol. Any point landing in two result districts
    is a topology break."""
    src = drings.model(source_features, key_prop)
    new = drings.model(result_features, key_prop)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = drings.districts_at(new, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = drings.districts_at(src, pt)
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

    # gates 3 and 4 share ONE reading of which rings went. `classify` decides it
    # across the whole family at once, because a ring on a shared edge is dropped
    # from both chambers and is one ring rather than two, and hands back the
    # signature of each so the fidelity gate can skip exactly those rather than
    # re-deciding with a second copy of the threshold.
    records, dstats = drings.classify({
        name: {"source": sources[name]["features"],
               "drawn": built[name]["features"],
               "key": "BASENAME"}
        for name in FAMILY})
    # `signatures` is PLURAL and the union is what this gate needs. A record is a
    # cluster of rings that coincide on the ground and differ byte for byte --
    # district 1 and the water pseudo-district each trace the Door sliver with
    # their own vertices -- so taking one signature per record leaves the other
    # ring looking retained, and check_fidelity then measures a shape that is gone
    # into the stray. That is not hypothetical: it read 17.5 m against a 15 m
    # ceiling the first time this was wired up with a singular field.
    dropped_sigs = {sig for r in records for sig in r["signatures"]}

    # gate 3, against the source: how far the true line strays from the drawn one
    for name in FAMILY:
        ok, msg = check_fidelity(sources[name]["features"], built[name]["features"],
                                 dropped_sigs)
        if not ok:
            raise RuntimeError("%s fidelity check failed: %s" % (name, msg))
        print("fidelity %s: %s" % (name, msg), file=sys.stderr)

    # gate 4, on the rings gate 3 set aside: every harming drop declared, every
    # declaration still found, and each one's reader answers verified rather than
    # trusted. This is the gate that distinguishes a lost sliver nobody can reach
    # from one that would tell a reader they are in no district.
    ok, msg = drings.check(records, dstats, ACCEPTED_DROPPED_RINGS, GAP_CLOSED)
    if not ok:
        raise RuntimeError(
            "dropped-ring check failed: %s\n"
            "  Each harming drop needs a declaration in ACCEPTED_DROPPED_RINGS "
            "carrying its measured kind, features, reader answers and an interior "
            "point. Re-measure rather than editing a declaration to match." % msg)
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
    dropped_rings.check(). So a green `--check` means the shipped files still nest
    and still say what the declarations claim they say -- not that the declarations
    are complete. GAP_CLOSED is build-time for the same reason: a hole the drawn
    output fills leaves no trace in the drawn output.

    A THIRD BLIND SPOT, FOUND BY NEGATIVE-TESTING THIS FUNCTION: it cannot tell that
    a declared interior point is actually INSIDE its ring. Rounded back to four
    decimals -- the exact defect the Door County entry corrects -- the point falls
    outside the ring and still passes here, because the water pseudo-district it
    lands in is what the declaration says a reader reads. Only the build path can
    catch that, and it does: dropped_rings.check() refuses a declared point that
    dropped_rings.point_in_ring rejects.
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
            got = sorted(drings.districts_at(
                drings.model(built[chamber]["features"], "BASENAME"), pt))
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
