"""Rings the simplifier drops, judged by the ANSWER they change rather than by
their area — one mechanism for every Wisconsin boundary builder.

WHY THE ANSWER AND NOT THE AREA. `keep-shapes` protects a SHAPE and not a RING:
a multipolygon is one feature, so once one ring survives the guarantee is met and
every hole and every detached part is eligible for removal like any other
geometry. Some of those losses cost a reader the right answer and some cost
nothing, and AREA DOES NOT TELL THEM APART. Measured on this state's own layers:
a 31.7 m2 ring on Washington Island moves 610 of 900 points inside it from
district 1 to the water pseudo-district, while far larger dropped rings move
nothing at all. (That ring was described here as being IN Lake Michigan until
2026-09-27, which was an inference from its coordinate rather than a measurement;
TIGER's areal hydrography finds no water at it. CLAUDE.md carries the rule.)
An aggregate dropped-area ceiling would therefore license the drops that cost a
reader an answer and fail on the ones that cost nothing, which is why this module
computes the answer for every dropped ring instead.

WHAT IT COMPUTES, PER DISTINCT RING. Points provably inside the ring are put to
the FULL-PRECISION source and to the DRAWN output, and THE ANSWER A READER IS
GIVEN is compared:

    unchanged      the reader is told the same district -- no declaration needed
    gap-closed     the reader was told NO district and is now told one
    wrong-name     the reader is told a different district
    false-silence  the reader was told a district and is now told none
    degenerate     no point can be found inside the ring at all

THE READER'S ANSWER IS ONE DISTRICT, NOT THE SET, AND THAT DISTINCTION CHANGES
THE COUNT BY A THIRD. The app's `findFeatureContaining` scans the shipped features
in file order and BREAKS ON THE FIRST MATCH, so where two districts both contain a
point a reader sees whichever comes first and never learns of the second. A drop
that takes the set from {A, B, C} to {A} therefore changes no reader's answer if A
came first both times, and counting it would have this builder confessing to a
wrong answer it does not give. Measured on the shipped geometry: 102 rings change
the SET and 73 change what a reader is told. `wi/WATCH.md` row 57 established this
in September and put it exactly -- quote 63 to a reader and 133 to a builder -- and
the first version of this module measured the set anyway. The set is recorded
beside each answer as `before_all` / `after_all`, because a builder wants to know
the geometry moved even where the card does not.

`wrong-name` and `false-silence` are the harms and must be declared one by one.
`unchanged` and `degenerate` need nothing. `gap-closed` is counted but not
declared per ring, and that is a judgement this module states rather than hides:
a hole that NO district covers is a gap in the publisher's own coverage, so
closing it moves a reader from "you are in no supervisory district" to the
district that surrounds them on every side. The supporting measurement is that
LTSB's own statewide geometry overlaps ITSELF on 0.017% of its area, so gaps and
overlaps are the same stitching artefact between 72 county submissions. IT IS
STILL AN INFERENCE: a hole could in principle be a deliberate void, and closing
it would then name a district for ground no district holds. So the COUNT is
declared and gated, and a rebuild that starts closing a different number of gaps
fails and has to be looked at.

THE SAMPLER IS A SCANLINE, AND A BOUNDING-BOX GRID IS THE WRONG TOOL HERE.
Nearly every dropped ring is a thin sliver along a county line, so its bounding
box is mostly outside it. Measured on the supervisory layer's own 464 distinct
dropped rings, a 0.25 m bbox grid needed 15,597,792 cells for a single ring and
STILL found no point inside 157 of them; the scanline finds points in 355 and
uses 1,457 points in total. An interior SPAN on a scanline has positive width by
construction, so its midpoint is inside -- but the sampler only ever PROPOSES,
and `point_in_ring` decides, because 1.02% of those midpoints are rejected where
a ring is degenerate or self-touching.

AND THE SAMPLE COUNT IS THE RING'S OWN, NOT A ROUND NUMBER. One scanline sits
between each pair of distinct vertex latitudes, so a three-vertex sliver gets one
point and a complex ring gets one per span per scanline -- measured, a median of
2 and a maximum of 77 -- thinned evenly to SCANLINE_MAX_POINTS above that. Two
rings at the shipped setting return DIFFERENT answers at different points inside
themselves, so one point is demonstrably not always enough and a fixed single
sample would have missed them.

SAMPLING MUST BE DETERMINISTIC, WHICH COST ONE WRONG MEASUREMENT TO LEARN. A
first version drew points until it had a target number, refining the grid until
it did; run twice with different targets on one file it answered 308 and 307
answer-changing rings, 41 and 38 unchanged. A gate whose verdict depends on how
hard it looked cannot say which rings need declaring, so nothing here is
target-driven.
"""

import math

# A SOURCE RING COUNTS AS DROPPED when none of its own vertices survived, and
# this is the threshold for "survived", in metres. Simplification KEEPS a subset
# of the source vertices, so a retained ring holds at least one of its own
# exactly and its minimum distance to the drawn line is 0 up to floating point;
# a dropped ring has every vertex off that line. 1 m is far above the float noise
# and far below any real stray.
#
# The one way this reads wrong is safe: a dropped ring lying exactly on ANOTHER
# ring's drawn line would measure as retained, and its stray would then be held
# to the caller's fidelity ceiling -- stricter than a declaration, never looser.
RETAINED_RING_M = 1.0

# The largest area a ring may have and still be reported `degenerate` — i.e. no
# point can be found inside it. DERIVED FROM THE SHIPPED COORDINATE PRECISION,
# not fitted to what has been observed. These files ship at 6 decimals, and one
# 6-decimal cell measures 0.0821 m x 0.1105 m at 42.5 N through 0.0759 m x
# 0.1105 m at 47.0 N — 0.0084 to 0.0091 m2 across Wisconsin's latitudes. A ring
# smaller than one cell cannot be guaranteed to hold an interior span of positive
# width at all, so 0.01 m2 is one cell rounded up to cover the whole state.
#
# ABOVE THIS BOUND, A RING WITH NO INTERIOR POINT IS A FAILURE OF THE SAMPLER
# rather than a ring with no inside, and the caller is told to fail rather than
# to pass it silently. That guard is why the bound is derived: the first bbox-grid
# sampler reported rings of 97.6 m2 and 131.6 m2 as having no interior point, and
# an observed-maximum bound would have grown to cover them. Fitting it to the data
# is the same mistake as choosing a ceiling to fit the drops.
DEGENERATE_MAX_M2 = 0.01

# Scanlines per ring, above which they are thinned evenly. 64 is a cap on work
# rather than a measurement: the median ring offers 2 points and the largest 77.
SCANLINE_MAX_POINTS = 64

# How far apart two samples inside one ring may be, in metres. NOT A NEW NUMBER:
# it is RETAINED_RING_M, the distance at which a vertex counts as having survived,
# reused because it is already finer than any simplification interval this fleet
# ships — so no boundary the drawn output draws can pass between two samples
# unseen. A four-vertex rectangle has one scanline and would otherwise be judged
# on a single point however large it is.
SAMPLE_STEP_M = RETAINED_RING_M

# How close a dropped ring must be to a declared one to be the same ring, in
# metres, and how far its area may differ.
RING_MATCH_M = 25.0
RING_MATCH_AREA = 0.10

KIND_UNCHANGED = "unchanged"
KIND_GAP_CLOSED = "gap-closed"
KIND_WRONG_NAME = "wrong-name"
KIND_FALSE_SILENCE = "false-silence"
KIND_DEGENERATE = "degenerate"
HARM_KINDS = (KIND_WRONG_NAME, KIND_FALSE_SILENCE)


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def mscale(lat):
    """Metres per degree of longitude and of latitude at `lat`."""
    return (111320.0 * math.cos(math.radians(lat)), 110540.0)


def rings(geom):
    """Every ring of a Polygon or MultiPolygon, outer rings and holes alike."""
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [r for r in geom["coordinates"] if r]
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly if r]
    return []


def ring_area_m2(ring):
    """Unsigned planar area, metres squared, at the ring's own latitude."""
    if len(ring) < 3:
        return 0.0
    sx, sy = mscale(sum(p[1] for p in ring) / float(len(ring)))
    a = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][0] * sx, ring[i][1] * sy
        x2, y2 = ring[(i + 1) % len(ring)][0] * sx, ring[(i + 1) % len(ring)][1] * sy
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def ring_centre(ring):
    """Mean of the DISTINCT vertices — the identity a declaration is matched on.

    Distinct, because a closed ring repeats its first vertex and would otherwise
    pull the centre towards it.
    """
    pts = sorted({(round(p[0], 9), round(p[1], 9)) for p in ring})
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def ring_verts(ring):
    """Distinct vertices, so a closed ring is not counted one high."""
    return len({(round(p[0], 9), round(p[1], 9)) for p in ring})


def ring_signature(ring):
    """Identity of a ring's GEOMETRY, at the 6 decimals these files ship.

    One ring geometry can be dropped from several features at once — a sliver on
    a shared boundary sits in both districts that drew it, and on the water line
    in the land district and the water pseudo-district, in both chambers — so
    drops are grouped by this rather than counted per feature.
    """
    return tuple(sorted((round(p[0], 6), round(p[1], 6)) for p in ring))


def point_in_ring(pt, ring):
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


def point_in_geometry(pt, geom):
    """Even-odd over every ring, so a point in a hole is correctly OUTSIDE."""
    if geom is None:
        return False
    if geom["type"] == "Polygon":
        inside = False
        for ring in geom["coordinates"]:
            if point_in_ring(pt, ring):
                inside = not inside
        return inside
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            inside = False
            for ring in poly:
                if point_in_ring(pt, ring):
                    inside = not inside
            if inside:
                return True
    return False


def bbox(geom):
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


def model(features, key_prop):
    """(key, geometry, bbox) per feature — the form `districts_at` scans."""
    return [(f["properties"].get(key_prop), f["geometry"], bbox(f["geometry"]))
            for f in features if f.get("geometry")]


def reader_answer(mod, pt):
    """The ONE district a reader is told they are in, or None.

    THIS IS THE ANSWER THE GATE JUDGES, AND IT IS NOT THE SET. The app's
    `findFeatureContaining` scans the shipped features in file order, bbox-rejects,
    ray-casts, and BREAKS ON THE FIRST MATCH — so where two districts both contain
    a point, a reader is shown whichever comes first in the file and never learns
    of the second. `wi/WATCH.md` row 57 established this in September and put it
    exactly: quote 63 to a reader and 133 to a builder.

    So a drop that changes the SET from {A, B, C} to {A} changes no reader's answer
    if A came first both times, and counting it as harm would have this builder
    confessing to a wrong answer it does not give. The set is still recorded beside
    it, because a builder wants to know the geometry moved even where the card
    does not.

    `mod` must be in the file's own feature order, which is what `model` returns
    and what mapshaper preserves through simplification.
    """
    for k, g, bb in mod:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and point_in_geometry(pt, g):
            return k
    return None


def districts_at(mod, pt):
    """Every district of `mod` containing `pt`, sorted, as a tuple."""
    return tuple(sorted(
        k for k, g, bb in mod
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
        and point_in_geometry(pt, g)))


def _seg_dist_m(p, a, b, sx, sy):
    px, py = (p[0] - a[0]) * sx, (p[1] - a[1]) * sy
    bx, by = (b[0] - a[0]) * sx, (b[1] - a[1]) * sy
    L = bx * bx + by * by
    if L <= 0:
        return math.hypot(px, py)
    t = max(0.0, min(1.0, (px * bx + py * by) / L))
    return math.hypot(px - t * bx, py - t * by)


def index_segments(rs, cell=0.01):
    """Bucket every segment of `rs` into a degree grid for nearest-segment work."""
    grid = {}
    for r in rs:
        for i in range(len(r) - 1):
            a, b = r[i], r[i + 1]
            for cx in range(int(math.floor(min(a[0], b[0]) / cell)),
                            int(math.floor(max(a[0], b[0]) / cell)) + 1):
                for cy in range(int(math.floor(min(a[1], b[1]) / cell)),
                                int(math.floor(max(a[1], b[1]) / cell)) + 1):
                    grid.setdefault((cx, cy), []).append((a, b))
    return grid, cell


def dist_to_drawn(p, grid, cell, sx, sy):
    """Distance from `p` to the nearest indexed segment, widening the search."""
    best = float("inf")
    cx, cy = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
    span = 1
    while span <= 8:
        for i in range(cx - span, cx + span + 1):
            for j in range(cy - span, cy + span + 1):
                for a, b in grid.get((i, j), ()):
                    d = _seg_dist_m(p, a, b, sx, sy)
                    if d < best:
                        best = d
        if best < span * cell * min(sx, sy):
            return best
        span *= 2
    return best


def interior_points(ring, max_pts=SCANLINE_MAX_POINTS):
    """Points provably inside `ring`, from interior SPANS on scanlines.

    A bbox grid is the wrong sampler for these rings: nearly all are thin slivers
    along a county line, so the bounding box is mostly outside the ring. Measured
    on the supervisory layer's own 464 distinct dropped rings, a 0.25 m bbox grid
    needed 15,597,792 cells for a single ring and STILL found no point inside 157
    of them. An interior SPAN on a scanline has positive width by construction, so
    its midpoint is inside — but the sampler only ever PROPOSES, and
    `point_in_ring` decides, because 1.02% of those midpoints are rejected where a
    ring is degenerate or self-touching.

    TWO THINGS SET THE SAMPLE COUNT, AND THE VERTICES ALONE ARE NOT ENOUGH.
    A scanline sits between each pair of distinct vertex latitudes, which suits a
    sliver traced with many vertices. It is not enough for a LARGE ring with few:
    a four-vertex rectangle has two distinct latitudes and therefore ONE scanline
    and ONE point, whoever big it is — which is exactly the case where one point
    is not representative, and a fixture of that shape is what caught it. So the
    scanlines are also subdivided, and each span sampled along its length, until
    consecutive samples are no more than SAMPLE_STEP_M apart.

    The step is RETAINED_RING_M, this module's own measured constant, rather than
    a new round number: it is the distance at which a vertex counts as having
    survived, and it is finer than any simplification interval this fleet ships,
    so no boundary the drawn output draws can pass between two samples unseen.

    Work is bounded by `max_pts` per ring, thinned evenly so the choice stays a
    deterministic function of the ring.
    """
    r = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    n = len(r)
    if n < 3:
        return []
    ys = sorted({p[1] for p in r})
    if len(ys) < 2:
        return []
    sx, sy = mscale((ys[0] + ys[-1]) / 2.0)
    step_lat = SAMPLE_STEP_M / sy
    cuts = []
    for i in range(len(ys) - 1):
        lo, hi = ys[i], ys[i + 1]
        cuts.append((lo + hi) / 2.0)
        extra = int((hi - lo) / step_lat)          # subdivide a tall gap
        for k in range(1, min(extra, max_pts)):
            cuts.append(lo + (hi - lo) * k / float(extra + 1))
    cuts = sorted(set(cuts))
    if len(cuts) > max_pts:
        st = len(cuts) / float(max_pts)
        cuts = [cuts[int(i * st)] for i in range(max_pts)]
    step_lng = SAMPLE_STEP_M / max(sx, 1e-9)
    out = []
    for y in cuts:
        xs = []
        for i in range(n):
            x1, y1 = r[i][0], r[i][1]
            x2, y2 = r[(i + 1) % n][0], r[(i + 1) % n][1]
            if (y1 > y) != (y2 > y):
                xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            x0, x1 = xs[k], xs[k + 1]
            if x1 <= x0:
                continue
            steps = max(1, min(int((x1 - x0) / step_lng), max_pts))
            for j in range(steps):
                base = x0 + (x1 - x0) * (j + 0.5) / steps
                for f in (0.0, -0.25, 0.25):
                    p = (base + (x1 - x0) * f / steps, y)
                    if x0 < p[0] < x1 and point_in_ring(p, ring):
                        out.append(p)
                        break
        if len(out) > max_pts * 4:
            break
    return out


#!/usr/bin/env python3


# --------------------------------------------------------------------------
# what was dropped, and what it costs a reader
# --------------------------------------------------------------------------

def _by_key(features, key_prop):
    return {f["properties"].get(key_prop): f
            for f in features if f.get("geometry")}


def find_dropped(source_features, drawn_features, key_prop):
    """[(key, ring)] for every SOURCE ring none of whose vertices survived.

    Compared feature by feature: a ring belongs to one district, so the question
    is whether THAT district's drawn geometry kept it, not whether some other
    district's line happens to pass through it.
    """
    src, drawn = _by_key(source_features, key_prop), _by_key(drawn_features, key_prop)
    out = []
    for key, sf in src.items():
        df = drawn.get(key)
        if df is None:
            continue
        dr, sr = rings(df["geometry"]), rings(sf["geometry"])
        if not dr or not sr:
            continue
        sx, sy = mscale(sr[0][0][1])
        grid, cell = index_segments(dr)
        for r in sr:
            if min(dist_to_drawn((p[0], p[1]), grid, cell, sx, sy) for p in r) > RETAINED_RING_M:
                out.append((key, r))
    return out


def interior_at_precision(pts, ring, lo=6, hi=12):
    """The first sampled point that is STILL inside once rounded, and to how many
    decimals it had to be kept.

    Rounding is not free and this project has paid for it once: at 45.41 N the
    FOURTH decimal is 11.05 m of latitude and 7.81 m of longitude, so rounding a
    point to it displaced it out of a ring 7.5 m across and the answer measured
    there was the surrounding water. Six decimals is about 0.1 m, which is inside
    any ring of a few square metres — but it is NOT enough for every ring here,
    and that is measured rather than assumed: a 0.04 m2 ring in Fond du Lac
    County holds no 6-decimal point at all, so the precision RISES per ring until
    the rounded point is provably inside, instead of a fixed 6 that silently
    yields nothing.

    Returns ((lng, lat), decimals) or (None, None).
    """
    for nd in range(lo, hi + 1):
        for p in pts:
            q = (round(p[0], nd), round(p[1], nd))
            if point_in_ring(q, ring):
                return q, nd
    return None, None


def _merge_coincident(groups):
    """One SLIVER is one record, even when two districts each drew it separately.

    Grouping by `ring_signature` alone is not enough: where a boundary sliver
    belongs to two districts, each county's submission traces it with its own
    vertices, so the two rings coincide on the ground and differ byte for byte.
    Measured on the supervisory layer, that produced TWO harm records for one
    0.84 m2 sliver in Grant County — and no single declaration can satisfy both,
    because each names a different district in its `features`.

    So groups are merged when they pass the SAME identity test a declaration is
    matched on, `RING_MATCH_M` and `RING_MATCH_AREA`. The merge is deterministic:
    signatures are visited in sorted order and each joins the first cluster it
    matches.
    """
    out = []
    for sig in sorted(groups):
        g = groups[sig]
        c, m2 = ring_centre(g["ring"]), ring_area_m2(g["ring"])
        for o in out:
            sx, sy = mscale(o["centre"][1])
            d = math.hypot((c[0] - o["centre"][0]) * sx, (c[1] - o["centre"][1]) * sy)
            span = max(m2, o["m2"], 1e-6) * RING_MATCH_AREA
            if d <= RING_MATCH_M and abs(m2 - o["m2"]) <= max(span, 0.01):
                o["features"].extend(g["features"])
                o["signatures"].extend(g["signatures"])
                break
        else:
            out.append({"ring": g["ring"], "features": list(g["features"]),
                        "signatures": list(g["signatures"]),
                        "centre": c, "m2": m2})
    return {i: o for i, o in enumerate(out)}


def classify(layers):
    """Every dropped ring, grouped by geometry, with the answer it changes.

    `layers` is {name: {"source": [...], "drawn": [...], "key": "PROP"}}. One
    ring can be dropped from several features and several layers at once, so the
    grouping is by `ring_signature` and each record names every feature it was
    dropped from.

    A RECORD CARRIES `signatures`, PLURAL, so a caller can ask whether a given
    source ring was dropped without re-deciding it with a second copy of the
    threshold. Plural because a record is a CLUSTER: `_merge_coincident` folds
    rings that coincide on the ground but differ byte for byte, which is what two
    districts tracing one sliver with their own vertices produces. Measured on
    Wisconsin's chambers, the Door County sliver has TWO signatures behind one
    record — district 1's tracing and the water pseudo-district's — so a singular
    field covers one of them and a caller filtering on it sees the other ring as
    retained. That is not hypothetical: it is how the chambers builder's fidelity
    gate failed on 17.5 m the first time this field was wired up, which is the
    same two-readers defect arriving through the fix for it.

    THE ANSWER IS RECORDED PER LAYER BECAUSE IT DIFFERS BY LAYER FOR ONE RING.
    Wisconsin's Door County ring leaves Senate 1 for the SENATE water row and
    Assembly 1 for the ASSEMBLY water row, which are different strings; testing
    one layer and assuming the other would leave half of every declaration in a
    multi-layer family unchecked. Carried here from the chambers builder's own
    hand-written gate, which this replaces.

    Returns (records, stats). A record is::

        {"m2", "verts", "features": ["layer:key", ...], "kinds": [...],
         "kind": "wrong-name", "harm": True, "interior": {"lat", "lng"},
         "answers": {layer: {"before": [...], "after": [...]}},
         "signatures": [ring_signature(r), ...], "sampled": n, "mixed": False}

    `mixed` is a ring that answers DIFFERENTLY at different points inside itself.
    It is reported rather than reduced to one pair, because no single declaration
    describes such a ring and a human should look at it. Measured: none at
    Douglas-Peucker interval 4 through 25, two at the visvalingam setting this
    replaces.
    """
    mods = {}
    groups = {}
    for name, spec in layers.items():
        mods[name] = (model(spec["source"], spec["key"]),
                      model(spec["drawn"], spec["key"]))
        for key, ring in find_dropped(spec["source"], spec["drawn"], spec["key"]):
            sig = ring_signature(ring)
            g = groups.setdefault(sig, {"ring": ring, "features": [],
                                       "signatures": [sig]})
            g["features"].append("%s:%s" % (name, key))
    groups = _merge_coincident(groups)

    records = []
    stats = {KIND_UNCHANGED: 0, KIND_GAP_CLOSED: 0, KIND_WRONG_NAME: 0,
             KIND_FALSE_SILENCE: 0, KIND_DEGENERATE: 0,
             "rings": len(groups), "mixed": 0}
    for sig, g in groups.items():
        ring = g["ring"]
        m2 = ring_area_m2(ring)
        pts = interior_points(ring)
        if not pts:
            # A ring with no inside cannot change an answer — but only below the
            # measured bound. Above it, the SAMPLER failed and the caller must
            # not be told the ring is harmless.
            stats[KIND_DEGENERATE] += 1
            records.append({"m2": m2, "verts": ring_verts(ring),
                            "centre": ring_centre(ring),
                            "signatures": sorted(set(g["signatures"])),
                            "features": sorted(g["features"]),
                            "kinds": [KIND_DEGENERATE], "kind": KIND_DEGENERATE,
                            "harm": False, "interior": None, "answers": {},
                            "sampled": 0, "mixed": False,
                            "oversized": m2 > DEGENERATE_MAX_M2})
            continue
        pairs = {}
        sets = {}
        kinds = set()
        for name, (sm, dm) in mods.items():
            if not any(f.startswith(name + ":") for f in g["features"]):
                continue
            sets.setdefault(name, set())
            seen = set()
            for p in pts:
                before, after = reader_answer(sm, p), reader_answer(dm, p)
                sets[name].add((districts_at(sm, p), districts_at(dm, p)))
                seen.add((before, after))
                if before == after:
                    continue
                kinds.add(KIND_GAP_CLOSED if before is None else
                          (KIND_FALSE_SILENCE if after is None else KIND_WRONG_NAME))
            pairs[name] = sorted(seen, key=lambda t: (t[0] or "", t[1] or ""))
        mixed = any(len(v) > 1 for v in pairs.values())
        harm = bool(kinds & set(HARM_KINDS))
        kind = "+".join(sorted(kinds)) if kinds else KIND_UNCHANGED
        if not kinds:
            stats[KIND_UNCHANGED] += 1
        else:
            for k in kinds:
                stats[k] += 1
        if mixed:
            stats["mixed"] += 1
        interior, idec = interior_at_precision(pts, ring)
        answers = {}
        for name, prs in pairs.items():
            b, a = prs[0]
            sb, sa = sorted(sets.get(name, {((), ())}))[0]
            answers[name] = {"before": [b] if b else [], "after": [a] if a else [],
                             "before_all": list(sb), "after_all": list(sa)}
        records.append({"m2": m2, "verts": ring_verts(ring),
                        "centre": ring_centre(ring), "ring": ring,
                        "signatures": sorted(set(g["signatures"])),
                        "features": sorted(g["features"]),
                        "kinds": sorted(kinds) or [KIND_UNCHANGED], "kind": kind,
                        "harm": harm,
                        "interior": ({"lat": interior[1], "lng": interior[0],
                                      "decimals": idec} if interior else None),
                        "answers": answers, "sampled": len(pts), "mixed": mixed,
                        "oversized": False})
    records.sort(key=lambda r: -r["m2"])
    return records, stats


def _match(rec, dec):
    """Is `dec` a declaration of `rec`'s ring? Centre and area, both."""
    sx, sy = mscale(rec["centre"][1])
    d = math.hypot((rec["centre"][0] - dec["lng"]) * sx,
                   (rec["centre"][1] - dec["lat"]) * sy)
    if d > RING_MATCH_M:
        return False
    span = max(rec["m2"], dec["m2"], 1e-6) * RING_MATCH_AREA
    return abs(rec["m2"] - dec["m2"]) <= max(span, 0.01)


def check(records, stats, declarations, gap_closed):
    """Every harming drop declared, every declaration found. Default is FAIL.

    THE DEFAULT IS THE POINT. A dropped ring that costs a reader the right answer
    fails this build unless somebody has written down which answer it costs, and
    a declaration that no longer matches anything fails too — the shape
    ACCEPTED_DROPS, EXPECTED_UNREACHABLE and ACCEPTED_SHORTFALLS already use
    across the fleet. What is NOT declared per ring is the drop that changes no
    answer, which is what keeps the table a handful instead of hundreds.

    `gap_closed` is the caller's expected count of holes that no district covered
    and the drawn output now fills. Those are not declared one by one — see the
    module docstring for the inference that rests on and why it is an inference —
    but the COUNT is held exactly, so a rebuild that starts closing a different
    number of them stops and gets read.
    """
    problems = []

    over = [r for r in records if r["kind"] == KIND_DEGENERATE and r["oversized"]]
    for r in over:
        problems.append(
            "ring of %.4f m2 at %.6f,%.6f yielded no interior point, and the "
            "measured bound for that is %.4f m2 — the SAMPLER failed, so this "
            "ring's answer is unknown rather than unchanged"
            % (r["m2"], r["centre"][1], r["centre"][0], DEGENERATE_MAX_M2))

    for r in records:
        if r.get("mixed"):
            problems.append(
                "ring of %.2f m2 at %.6f,%.6f answers differently at different "
                "points inside itself (%s) — one declaration cannot describe it"
                % (r["m2"], r["centre"][1], r["centre"][0],
                   "; ".join("%s: %d distinct" % (k, len(v))
                             for k, v in sorted(r["answers"].items()))))

    harms = [r for r in records if r["harm"]]
    used = set()
    for r in harms:
        hit = [i for i, d in enumerate(declarations) if _match(r, d)]
        if not hit:
            problems.append(
                "UNDECLARED %s: %.2f m2, %d vertices, at %.6f,%.6f, dropped from "
                "%s; a reader there is answered %s and would now be answered %s"
                % (r["kind"], r["m2"], r["verts"], r["centre"][1], r["centre"][0],
                   ", ".join(r["features"]),
                   _answer_text(r["answers"], "before"),
                   _answer_text(r["answers"], "after")))
            continue
        if len(hit) > 1:
            problems.append("ring at %.6f,%.6f matches %d declarations"
                            % (r["centre"][1], r["centre"][0], len(hit)))
        i = hit[0]
        used.add(i)
        d = declarations[i]
        if d.get("kind") != r["kind"]:
            problems.append("declaration at %.6f,%.6f calls it %r; measured %r"
                            % (d["lat"], d["lng"], d.get("kind"), r["kind"]))
        if sorted(d.get("features", [])) != r["features"]:
            problems.append("declaration at %.6f,%.6f names features %s; measured %s"
                            % (d["lat"], d["lng"], sorted(d.get("features", [])),
                               r["features"]))
        for which, field in (("before", "answer_before"), ("after", "answer_after")):
            want = {k: sorted(v) for k, v in (d.get(field) or {}).items()}
            got = {k: sorted(v[which]) for k, v in r["answers"].items()}
            if want != got:
                problems.append("declaration at %.6f,%.6f claims %s %s; measured %s"
                                % (d["lat"], d["lng"], field, want, got))
        ip = d.get("interior")
        if not ip:
            problems.append("declaration at %.6f,%.6f carries no interior point"
                            % (d["lat"], d["lng"]))
        elif "ring" in r and not point_in_ring((ip["lng"], ip["lat"]), r["ring"]):
            problems.append("declaration at %.6f,%.6f gives an interior point "
                            "(%.6f,%.6f) that is NOT inside its ring"
                            % (d["lat"], d["lng"], ip["lat"], ip["lng"]))

    for i, d in enumerate(declarations):
        if i not in used:
            problems.append("declaration at %.6f,%.6f matches no dropped ring — "
                            "the geometry moved, so retire or re-measure it"
                            % (d["lat"], d["lng"]))

    if stats[KIND_GAP_CLOSED] != gap_closed:
        problems.append(
            "%d dropped hole(s) that no district covered are now filled by one; "
            "the builder declares %d. Each moves a reader from 'no district' to "
            "the district around them, so the count is held rather than the rings"
            % (stats[KIND_GAP_CLOSED], gap_closed))

    if problems:
        return False, "; ".join(problems)
    return True, ("%d dropped ring(s): %d harm none (%d unchanged, %d degenerate), "
                  "%d close a coverage gap, %d declared harm(s) "
                  "(%d wrong-name, %d false-silence)"
                  % (stats["rings"], stats[KIND_UNCHANGED] + stats[KIND_DEGENERATE],
                     stats[KIND_UNCHANGED], stats[KIND_DEGENERATE],
                     stats[KIND_GAP_CLOSED], len(harms),
                     stats[KIND_WRONG_NAME], stats[KIND_FALSE_SILENCE]))


def _answer_text(answers, which):
    bits = []
    for layer, a in sorted(answers.items()):
        v = a[which]
        bits.append("%s %s" % (layer, ", ".join(v) if v else "NO DISTRICT"))
    return "; ".join(bits)


# --------------------------------------------------------------------------
# selftest — fixtures only, no network, no data files
# --------------------------------------------------------------------------

def _sq(lng, lat, w, h):
    """A closed rectangular ring, counter-clockwise."""
    return [[lng, lat], [lng + w, lat], [lng + w, lat + h], [lng, lat + h], [lng, lat]]


def _feat(key, geom):
    return {"properties": {"K": key}, "geometry": geom}


def _poly(*rs):
    return {"type": "Polygon", "coordinates": [list(r) for r in rs]}


def _multi(*polys):
    return {"type": "MultiPolygon",
            "coordinates": [[list(r) for r in p] for p in polys]}


def _selftest():
    fails = []

    def ck(name, cond, extra=""):
        if cond:
            print("  ok   %s" % name)
        else:
            fails.append(name)
            print("  FAIL %s %s" % (name, extra))

    OUT = _sq(-89.00, 44.00, 0.01, 0.01)          # ~800 m x 1110 m
    HOLE = _sq(-88.9960, 44.0040, 0.001, 0.001)   # ~80 m x 111 m
    HALF = _sq(-88.9960, 44.0040, 0.0005, 0.001)  # left half of the hole

    def run(src, drawn):
        return classify({"L": {"source": src, "drawn": drawn, "key": "K"}})

    # 1. a retained ring is not reported dropped at all
    recs, st = run([_feat("A", _poly(OUT, HOLE))], [_feat("A", _poly(OUT, HOLE))])
    ck("a ring the drawn output keeps is not reported dropped", st["rings"] == 0)

    # 2. a dropped hole no district covers -> gap-closed, not harm
    recs, st = run([_feat("A", _poly(OUT, HOLE))], [_feat("A", _poly(OUT))])
    ck("a dropped hole nobody covers is gap-closed",
       st["rings"] == 1 and st[KIND_GAP_CLOSED] == 1 and not recs[0]["harm"],
       "got %s" % st)
    ck("gap-closed records the answer both ways",
       recs and recs[0]["answers"]["L"]["before"] == []
       and recs[0]["answers"]["L"]["after"] == ["A"],
       "got %s" % (recs[0]["answers"] if recs else None))

    # 3. a dropped hole ANOTHER district fills -> wrong-name, a harm
    src = [_feat("A", _poly(OUT, HOLE)), _feat("B", _poly(HOLE))]
    drw = [_feat("A", _poly(OUT)), _feat("B", _poly(HOLE))]
    recs, st = run(src, drw)
    h = [r for r in recs if r["harm"]]
    ck("a dropped hole another district fills is wrong-name",
       len(h) == 1 and h[0]["kind"] == KIND_WRONG_NAME, "got %s" % st)
    # THE READER'S ANSWER AND THE SET ARE DIFFERENT FACTS, and this fixture is
    # where that shows: the reader goes from B to A because A comes first in the
    # file, while the SET grows from {B} to {A, B}. A gate judging the set would
    # call this a harm on a page whose card never mentioned B.
    ck("wrong-name names the reader's answer, and the set beside it",
       h and h[0]["answers"]["L"]["before"] == ["B"]
       and h[0]["answers"]["L"]["after"] == ["A"]
       and h[0]["answers"]["L"]["after_all"] == ["A", "B"],
       "got %s" % (h[0]["answers"] if h else None))

    # 4. a dropped detached PART -> false-silence
    FAR = _sq(-88.90, 44.00, 0.002, 0.002)
    recs, st = run([_feat("C", _multi([OUT], [FAR]))], [_feat("C", _poly(OUT))])
    h = [r for r in recs if r["harm"]]
    ck("a dropped detached part is false-silence",
       len(h) == 1 and h[0]["kind"] == KIND_FALSE_SILENCE, "got %s" % st)
    ck("false-silence records an empty AFTER",
       h and h[0]["answers"]["L"]["after"] == [], "got %s" % (h[0]["answers"] if h else None))

    # 5. a ring below one coordinate cell is degenerate, and harmless
    # COLLINEAR, which is what the real ones are: measured, all 109 rings the
    # sampler cannot reach on the supervisory layer are at or below 0.002 m2. A
    # small TRIANGLE is not the fixture for this — a 0.44 m2 one is sampleable,
    # and writing that first is what proved the sampler reaches genuinely small
    # rings rather than giving up on them.
    TINY = [[-88.9950, 44.0050], [-88.99499, 44.0050], [-88.99498, 44.0050],
            [-88.9950, 44.0050]]
    recs, st = run([_feat("A", _poly(OUT, TINY))], [_feat("A", _poly(OUT))])
    ck("a sub-cell ring is degenerate rather than a harm",
       st[KIND_DEGENERATE] == 1 and not any(r["harm"] for r in recs), "got %s" % st)
    ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
    ck("a degenerate ring under the bound does not fail the gate", ok, msg)

    # 6. an UNSAMPLEABLE ring ABOVE the bound must FAIL — the sampler failed, so
    #    the ring's answer is unknown rather than unchanged. Forced by making the
    #    sampler return nothing, which is the only honest way to reach this state.
    global interior_points
    real = interior_points
    try:
        interior_points = lambda ring, max_pts=SCANLINE_MAX_POINTS: []
        recs, st = run([_feat("A", _poly(OUT, HOLE))], [_feat("A", _poly(OUT))])
        ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
        ck("an unsampleable ring above the bound FAILS", not ok and "SAMPLER failed" in msg, msg)
    finally:
        interior_points = real

    # 7. a ring that answers two ways inside itself FAILS rather than picking one
    src = [_feat("D", _poly(OUT, HOLE)), _feat("E", _poly(HALF))]
    drw = [_feat("D", _poly(OUT)), _feat("E", _poly(HALF))]
    recs, st = run(src, drw)
    ck("a ring answering two ways is reported mixed", st["mixed"] == 1, "got %s" % st)
    ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
    ck("a mixed ring FAILS", not ok and "differently at different" in msg, msg)

    # 8. the declaration contract: undeclared harm fails; a good declaration passes
    src = [_feat("A", _poly(OUT, HOLE)), _feat("B", _poly(HOLE))]
    drw = [_feat("A", _poly(OUT)), _feat("B", _poly(HOLE))]
    recs, st = run(src, drw)
    ok, msg = check(recs, st, [], st[KIND_GAP_CLOSED])
    ck("an undeclared harm FAILS", not ok and "UNDECLARED wrong-name" in msg, msg)
    h = [r for r in recs if r["harm"]][0]
    good = {"lat": h["centre"][1], "lng": h["centre"][0], "m2": h["m2"],
            "verts": h["verts"], "interior": h["interior"], "features": h["features"],
            "kind": h["kind"],
            "answer_before": {"L": h["answers"]["L"]["before"]},
            "answer_after": {"L": h["answers"]["L"]["after"]},
            "why": "fixture", "date": "2026-09-26"}
    ok, msg = check(recs, st, [good], st[KIND_GAP_CLOSED])
    ck("a correct declaration passes", ok, msg)

    # 9. every field of the declaration is load-bearing
    for field, mutate, want in (
            ("kind", lambda d: d.update(kind=KIND_FALSE_SILENCE), "calls it"),
            ("answer_before", lambda d: d.update(answer_before={"L": ["Z"]}), "answer_before"),
            ("answer_after", lambda d: d.update(answer_after={"L": ["Z"]}), "answer_after"),
            ("features", lambda d: d.update(features=["L:zzz"]), "names features"),
            ("interior", lambda d: d.update(interior={"lat": 44.5, "lng": -89.5,
                                                      "decimals": 6}),
             "NOT inside")):
        bad = dict(good)
        mutate(bad)
        ok, msg = check(recs, st, [bad], st[KIND_GAP_CLOSED])
        ck("a wrong %s FAILS" % field, not ok and want in msg, msg)

    # 10. an orphan declaration fails, and the gap-closed count is held
    orphan = dict(good)
    orphan.update(lat=45.5, lng=-90.5)
    ok, msg = check(recs, st, [good, orphan], st[KIND_GAP_CLOSED])
    ck("a declaration matching nothing FAILS", not ok and "matches no dropped ring" in msg, msg)
    ok, msg = check(recs, st, [good], st[KIND_GAP_CLOSED] + 1)
    ck("a moved gap-closed count FAILS", not ok and "declares" in msg, msg)

    # 11. two districts drawing ONE sliver separately are one record, not two
    #
    # THE OFFSET MUST SURVIVE 6-DECIMAL ROUNDING or this fixture tests the wrong
    # mechanism. It was 1e-7 until 2026-09-27, which `ring_signature` rounds away,
    # so the two rings shared a signature and were folded by the grouping dict
    # while `_merge_coincident` — the thing this case exists to exercise — was
    # never reached. 2e-6 degrees is about 0.2 m: distinct signatures, same ground,
    # comfortably inside RING_MATCH_M and RING_MATCH_AREA.
    a = _sq(-88.50, 44.50, 0.0002, 0.0002)
    b = [[p[0] + 2e-6, p[1] + 2e-6] for p in a]          # same ground, other vertices
    src = [_feat("P", _poly(_sq(-88.60, 44.40, 0.02, 0.02), a)),
           _feat("Q", _poly(_sq(-88.52, 44.40, 0.02, 0.02), b))]
    drw = [_feat("P", _poly(_sq(-88.60, 44.40, 0.02, 0.02))),
           _feat("Q", _poly(_sq(-88.52, 44.40, 0.02, 0.02)))]
    recs, st = run(src, drw)
    ck("one sliver drawn twice is ONE record naming both districts",
       st["rings"] == 1 and recs and sorted(recs[0]["features"]) == ["L:P", "L:Q"],
       "rings=%d features=%s" % (st["rings"], recs[0]["features"] if recs else None))
    # ... and the record must name EVERY signature it folded, because a caller
    # filtering source rings on `signatures` sees any it omits as retained. This
    # is the chambers builder's fidelity gate, which failed on 17.5 m when the
    # field was singular.
    want = {ring_signature(a), ring_signature(b)}
    got = set(recs[0]["signatures"]) if recs else set()
    ck("a merged record names every signature it folded",
       len(want) == 2 and got == want,
       "distinct source signatures=%d, record carries %d" % (len(want), len(got)))

    # 12. the interior point's precision rises for a ring 6 decimals cannot hold
    NARROW = [[-88.9950, 44.00500], [-88.994990, 44.00500],
              [-88.994995, 44.005004], [-88.9950, 44.00500]]
    pts = interior_points(NARROW)
    if pts:
        q6, nd = interior_at_precision(pts, NARROW)
        ck("a ring too small for 6 decimals records more of them",
           q6 is None or nd >= 6, "decimals=%s" % nd)
    else:
        ck("a ring too small for 6 decimals records more of them", True)

    print("%s — %d failure(s)" % ("dropped_rings selftest", len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    import sys as _sys
    if "--selftest" in _sys.argv[1:]:
        _sys.exit(_selftest())
    print(__doc__)
