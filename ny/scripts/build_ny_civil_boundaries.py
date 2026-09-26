#!/usr/bin/env python3
"""
Build New York's three civil-boundary layers into pre-simplified files under
data/app/, from the state's own NYS_Civil_Boundaries service, in ONE mapshaper
run with ONE shared topology: data/app/ny-counties.json (62 counties),
data/app/ny-cities-towns.json (62 cities + 933 towns, which together tile the
state) and data/app/ny-villages.json (532 villages, which nest inside towns and
never tile the state on their own).

THIS REPLACES TWO BUILDERS AND THE REASON IS A DEFECT, NOT TIDINESS. Until
2026-09-26 ny/scripts/build_ny_counties.py and ny/scripts/build_ny_municipalities.py
each called mapshaper on its own file at its own retain percentage (counties
15%, cities and towns 5%, villages 5% -- the shipped bytes reproduce exactly
from those three numbers). mapshaper builds topology WITHIN one dataset, so a
line two files share cannot survive identically across two runs. Measured that
day against the publisher's own geometry:

  * 98.4% of county vertices at source ARE town vertices -- the county layer is
    the publisher's own dissolve of the town layer -- and in the shipped files
    only 52.2% still were. On the stretches the publisher draws once, the two
    shipped files drew it up to 310 m apart, 8.4% of those vertices more than
    25 m apart.
  * Seven coterminous town/village governments (Harrison, Scarsdale, Mount
    Kisco, Green Island, Kiryas Joel/Palm Tree, East Rochester, Woodbury) agree
    to within a metre at source and shipped 78 to 320 m apart, IoU 0.929-0.989
    against the publisher's 0.997-0.9995.

VILLAGES ARE A DIFFERENT CASE FROM COUNTIES AND THE SHARED TOPOLOGY DOES NOT
FIX THEM. Only 9 of 145,280 village vertices are also a town vertex at source:
the state draws the village layer independently of the town layer, tracing the
same line with different vertices. So there is no shared arc for mapshaper to
find, and what bounds the coterminous pairs is the SIMPLIFICATION ALGORITHM
instead.

WHY DOUGLAS-PEUCKER RATHER THAN VISVALINGAM, and it is the same finding
Illinois recorded on 2026-09-25 for its legislative chambers. Visvalingam
thresholds triangle AREA, which does not bound how far the drawn line strays
from the true one, because successive below-threshold removals compound.
Measured here, as the share of the publisher's own vertices more than 25 m from
the line the app draws in their place:

  layer      Visvalingam (shipped)            dp interval=25
  counties   131.3 m worst,  0.42% over 25 m  26.2 m worst,  0.01% over 25 m
  towns      320.7 m worst,  9.52% over 25 m  26.2 m worst,  0.00% over 25 m
  villages  1604.8 m worst, 31.28% over 25 m  190.8 m worst, 0.02% over 25 m

WHY interval=25 RATHER THAN A SMALLER ONE. An interval is an absolute distance,
so it is the one dial that does not move when the dataset does -- mapshaper's
retain PERCENTAGE is relative to the whole dataset's vertex count, which is why
combining three files changes what a percentage means and why a small-input
test of this builder would lie about it. Measured over 15/20/25/30/40 m
(reproduce with --sweep), 25 is where the whole change is free: the four
cache-first files a first visit precaches go from 738,250 to 735,339 gzipped
bytes, 2,911 SMALLER, while every fidelity measure above improves. 15 m buys a
17-21 m worst stray for +163,068 gzipped bytes, +22.1%, which is a real trade
and not one this layer needs.

  interval   counties+towns+villages+judicial, gzipped
      15     901,318   (+163,068 vs shipped, +22.1%)
      20     802,664   ( +64,414 vs shipped,  +8.7%)
      25     735,339   (  -2,911 vs shipped,  -0.4%)   <- shipped
      30     654,326   fidelity fails: 1.9% of vertices over 25 m
      40     587,381   fidelity fails: 7.5% of vertices over 25 m

WOODBURY IS THE PUBLISHER'S OWN AND IS NOT OURS TO FIX. The Village of Woodbury
and the Town of Woodbury disagree by 1,484 m at source (IoU 0.9861); the built
files reproduce that disagreement and must, because smoothing it would be this
repo inventing a boundary the state does not draw.

SOURCE. One ArcGIS FeatureServer, three layers, counts re-confirmed 2026-09-26
by returnCountOnly (62 / 995 / 532):
  https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Civil_Boundaries/FeatureServer
Layer 2 "Counties", layer 6 "Cities_Towns", layer 7 "Villages". robots.txt on
gisservices.its.ny.gov answers HTTP 404, read as allow-all by
scripts/robots_policy.py as the client that fetches (curl). Each layer's count
is an exact equality rather than a floor: a village is annexed or dissolved
rarely, and when one is, this builder should stop rather than ship a fabric
whose size nobody has looked at.

TRAP, measured and load-bearing: villages are MANY-TO-MANY with towns. Of 532
villages, 76 carry a comma-joined multi-town TOWN value as one string
("Ballston Spa" is "Ballston, Milton"; "Brockport" is "Clarkson, Sweden"), and
8 of those also span two COUNTIES (Almond, Attica, Dolgeville, Earlville,
Deposit, Gowanda, Saranac Lake, Rushville). TOWN and COUNTY ship RAW, exactly
as the service prints them, comma-joined string and all. A reader of this file
must split that string itself and must never treat TOWN or COUNTY as a single
join key back to a town or county record -- doing so silently drops a village's
second town or second county.

TRAP, measured: New York City is ONE row in the Cities_Towns layer (NAME "New
York", MUNI_TYPE "city", COUNTY "New York, Bronx, Kings, Richmond, Queens",
POP2020 8,804,190). Inside the five boroughs that layer can only ever answer
"New York" -- data/app/borough-boundaries.json is the city tier's answer to
which of the five the point is in. It is also why 5 of the 62 counties have no
town line to share: the boroughs' mutual boundaries exist in the county layer
and nowhere in the town layer, which is what the county-vertex share below is
97% rather than 100%.

THE NYC FLAG IS LOAD-BEARING and is not a display convenience: it reads exactly
'Y' on the five boroughs (Bronx 36005, Kings 36047, New York 36061, Queens
36081, Richmond 36085) and 'N' on the other 57. A county-legislature concept
reads this flag to know which 57 counties elect a board and to answer nothing
inside the five that do not, so the flag ships even though no legislature card
renders yet. check_nyc_flag() refuses the build if that split ever moves.

THE SHORELINE DISAGREEMENT IS ALSO BY DESIGN. This service's polygons are
shoreline-clipped. data/app/metro-outline.json and data/app/ny-state-outline.json
come from Census TIGERweb, which is water-inclusive, so this file's county edges
and those two rings DISAGREE at the coast. They are not one product measured
twice: the outline files answer "is this point in the coverage wash", which has
to reach past the last shoreline pixel so a click just offshore still lands
inside the state, and this file answers "which county does the card name", which
has to stop at the shoreline so a point in open water is not attributed to a
county whose jurisdiction does not include it. Do not reconcile them.

FIELDS SHIPPED. A card needs identity and nothing else at this tier, so every
other column is dropped on the way in -- POP1990..POP2010, GNIS_ID, ABBREV,
SWIS, NYSP_ZONE, DOS_LL, DOSLL_DATE, MAP_SYMBOL, CALC_SQ_MI and DATEMOD never
reach data/app/. The Villages layer carries no MUNI_TYPE column at all (every
row in it is a village by construction), so this builder writes
MUNI_TYPE: "village" onto every village feature itself -- a SYNTHESIZED field
with no source column behind it, so a card reading MUNI_TYPE never has to know
which file it is looking at. That is the one field this builder invents.

GATES, all of them run before anything is written, and the build refuses rather
than shipping a measured-worse fabric:
  1. exact feature count per layer (62 / 995 / 532) and no null geometry;
  2. the fleet's 2,000-uniform-random-point classification of each layer
     against its own unsimplified fetch, over New York's published extent:
     >= 99.5% agreement and ZERO points in two simplified features. KEPT,
     and its blind spot is named: it passed every one of the defects above,
     because 2,000 points over a 36 deg-squared envelope cannot see a line
     drawn 300 m out of place;
  3. FIDELITY: at most 0.10% of the publisher's own vertices further than
     25.0 m from the line drawn in their place, per layer. This is the gate
     the classification cannot be: villages shipped at 31.28%;
  4. SHARED EDGES, exact: >= 97.0% of county vertices must also BE town
     vertices (the source's own figure is 98.4%, the shipped files' was 52.2%),
     and on every county vertex within 1 m of a source town line the two built
     layers must agree to 0.0 m;
  5. SHARED EDGES, bounded: on village vertices within 1 m of a source town
     line, the two built layers agree to within the interval;
  6. the NYC flag's 5/57 split.

DISTANCES are measured in a local equirectangular frame anchored at each
feature's own mid-latitude, so a metre here is within a few centimetres of a
metre on the ground anywhere in New York.

NO RAW SOURCE SNAPSHOT IS WRITTEN, the decision build_ny_counties.py and
build_ny_school_districts.py already recorded: 28 MB of near-identical geometry
that nothing reads back, against 1.5 MB for all of Wisconsin's build inputs put
together. The guards above are what make a run reproducible, and the source is
a public service this project can re-fetch.

DOWNSTREAM. ny/scripts/build_ny_judicial_districts.py dissolves the 62 counties
this builder writes into New York's 13 Supreme Court judicial districts, reading
data/app/ny-counties.json rather than re-fetching layer 2, so a judicial
district boundary is literally a union of the county arcs shipped here. Rebuild
it in the same change as this one; ny/scripts/validate_index.py fails the merge
if the two files stop sharing vertices.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ny/scripts/build_ny_civil_boundaries.py
    python3 ny/scripts/build_ny_civil_boundaries.py --sweep     # the interval table, writes nothing
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

# The service root, then each layer's own full path in LAYERS below. Written
# that way on purpose: ny/scripts/validate_sources.py's offline drift guard is a
# SUBSTRING match of its manifest's `builder_ref` against this file, so each
# layer path has to appear here CONTIGUOUSLY -- a URL assembled from a root and
# a number would leave the guard nothing per-layer to match, which is the
# adjacent-string-literals trap scripts/probe_user_agents.py already records
# one field over.
SERVICE_ROOT = "https://gisservices.its.ny.gov/arcgis/rest/services/"
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m -- the precision the app requests live

# New York's own published extent (docs/NY_EXPANSION_PLAN.md, measured
# 2026-09-18), not this instance's city-sized permalink gate, because all three
# of these layers answer statewide.
STATE_BBOX = {"minLng": -79.7626, "minLat": 40.4766, "maxLng": -71.7775, "maxLat": 45.0159}

# Douglas-Peucker interval in METRES. Absolute on purpose: a retain percentage
# is relative to the whole dataset, so it would mean something different the
# next time a layer joins or leaves this run. See the docstring for the sweep
# this value comes out of.
INTERVAL_M = 25
SWEEP_INTERVALS = (15, 20, 25, 30, 40)

# Gate thresholds, every one of them measured rather than picked. See the
# docstring's tables for the values the shipped tree and the source itself give.
CHORD_CEILING_M = 25.0          # the reader-facing fidelity ceiling
CHORD_OVER_CEILING_MAX_PCT = 0.10
SHARED_VERTEX_MIN_PCT = 97.0    # county vertices that must also be town vertices
COINCIDENT_M = 1.0              # within this of a source line = the publisher draws one line here

VALIDATION_KEY = "_vk"  # synthesized, unique per feature, added before
                        # simplification and stripped before writing -- NAME
                        # repeats within Cities_Towns (37 names cover two
                        # features apiece, e.g. a City and a Town of Rochester)
                        # so a validation key must be unique, not descriptive.

NYC_FIPS = {"36005": "Bronx", "36047": "Kings", "36061": "New York",
            "36081": "Queens", "36085": "Richmond"}

LAYERS = [
    {
        "id": "counties",
        "service_path": "NYS_Civil_Boundaries/FeatureServer/2",
        "service_layer_name": "Counties",
        "fields": ["NAME", "FIPS_CODE", "NYC", "POP2020"],
        "expected_count": 62,
        "out_file": "ny-counties.json",
        "synth_muni_type": None,
    },
    {
        "id": "cities_towns",
        "service_path": "NYS_Civil_Boundaries/FeatureServer/6",
        "service_layer_name": "Cities_Towns",
        "fields": ["NAME", "MUNI_TYPE", "COUNTY"],
        "expected_count": 995,
        "out_file": "ny-cities-towns.json",
        "synth_muni_type": None,
        # Cities and towns TILE the state -- every point in New York is in
        # exactly one, so a point landing in zero is itself a disagreement
        # against the unsimplified fetch, never a case of "no answer here".
    },
    {
        "id": "villages",
        "service_path": "NYS_Civil_Boundaries/FeatureServer/7",
        "service_layer_name": "Villages",
        "fields": ["NAME", "TOWN", "COUNTY"],
        "expected_count": 532,
        "out_file": "ny-villages.json",
        "synth_muni_type": "village",
        # Villages nest INSIDE towns and do not tile the state -- most sampled
        # points correctly land in zero villages on both sides, and that is
        # agreement, not a gap in the test.
    },
]

# Which built layer must agree with which, on the stretches the PUBLISHER draws
# once. "exact" is only available where the two layers share vertices at source.
SHARED_EDGES = [
    {"a": "counties", "b": "cities_towns", "mode": "exact"},
    {"a": "villages", "b": "cities_towns", "mode": "bounded"},
]


def fetch_layer(cfg):
    """Fetch one NYS_Civil_Boundaries layer as GeoJSON in a single unpaged query
    (all three counts sit under the service's maxRecordCount of 1000; measured
    2026-09-18, layer 6 returns all 995 features in one 20.6 MB response). Uses
    curl so it works through an HTTPS proxy, as in the Claude Code sandbox."""
    url = (
        SERVICE_ROOT + cfg["service_path"] + "/query"
        "?where=1%3D1"
        "&outFields=" + ",".join(cfg["fields"]) +
        "&outSR=4326&geometryPrecision=6&f=geojson"
    )
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300", url],
        check=True, capture_output=True,
    ).stdout
    geo = json.loads(out)
    feats = geo.get("features") or []
    label = "%s (%s)" % (cfg["service_path"], cfg["service_layer_name"])
    if not feats:
        raise RuntimeError("NYS_Civil_Boundaries %s returned no features" % label)
    if geo.get("exceededTransferLimit") or geo.get("properties", {}).get("exceededTransferLimit"):
        raise RuntimeError(
            "NYS_Civil_Boundaries %s hit the transfer cap -- needs paging "
            "(this builder assumes one unpaged query covers it)" % label
        )
    if len(feats) != cfg["expected_count"]:
        raise RuntimeError(
            "NYS_Civil_Boundaries %s returned %d features, expected exactly %d "
            "-- refusing to build on an unexpected count" % (label, len(feats), cfg["expected_count"])
        )
    for i, f in enumerate(feats):
        if f.get("geometry") is None:
            raise RuntimeError(
                "NYS_Civil_Boundaries %s: feature %r has null geometry"
                % (label, f.get("properties", {}).get("NAME"))
            )
        f["properties"][VALIDATION_KEY] = "%s%d" % (cfg["id"][0], i)
    return geo


def run_mapshaper_combined(src_paths, interval, out_dir):
    """ONE mapshaper run over all three layers, so a line two of them share is
    ONE arc simplified once. `combine-files` is what puts them in a single
    dataset and therefore a single topology; running them separately is the
    defect this builder exists to retire."""
    subprocess.run(
        ["npx", "-y", MAPSHAPER, "-i", "combine-files"] + list(src_paths) +
        ["-simplify", "dp", "keep-shapes", "interval=%d" % interval,
         "-o", "precision=" + PRECISION, "format=geojson", out_dir],
        check=True, cwd=REPO_ROOT, capture_output=True,
    )


# --- point-in-polygon mirroring index.html's even-odd test (so validation
#     agrees with what the app computes at runtime) -- fleet-standard copy ---
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


def _rings(geom):
    if geom["type"] == "Polygon":
        return list(geom["coordinates"])
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


def _project(ring, lat0):
    """Local equirectangular metres. Anchored per feature, so the x scale is
    right where the feature is rather than right on average."""
    kx = 111320.0 * math.cos(math.radians(lat0))
    return [(x * kx, y * 110540.0) for x, y in ring]


def _seg_distance(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


class SegmentIndex:
    """Line segments on a uniform grid, for nearest-distance queries. A grid
    hash rather than an R-tree because this builder stays stdlib, like every
    other New York boundary builder; the fleet installs shapely only where a
    real overlay is needed."""

    def __init__(self, projected_rings, cell=250.0):
        self.cell = cell
        self.cells = {}
        self.segs = []
        for ring in projected_rings:
            for i in range(1, len(ring)):
                ax, ay = ring[i - 1]
                bx, by = ring[i]
                idx = len(self.segs)
                self.segs.append((ax, ay, bx, by))
                lo_x, hi_x = (ax, bx) if ax <= bx else (bx, ax)
                lo_y, hi_y = (ay, by) if ay <= by else (by, ay)
                for cx in range(int(math.floor(lo_x / cell)), int(math.floor(hi_x / cell)) + 1):
                    for cy in range(int(math.floor(lo_y / cell)), int(math.floor(hi_y / cell)) + 1):
                        self.cells.setdefault((cx, cy), []).append(idx)

    def __bool__(self):
        return bool(self.segs)

    def distance(self, px, py, give_up_rings=200):
        """Distance to the nearest segment. Expands in Chebyshev rings and stops
        once the best found beats the closest anything unexamined could be."""
        cell = self.cell
        cx, cy = int(math.floor(px / cell)), int(math.floor(py / cell))
        best = None
        r = 0
        while r <= give_up_rings:
            for i in range(cx - r, cx + r + 1):
                for j in range(cy - r, cy + r + 1):
                    if r and max(abs(i - cx), abs(j - cy)) != r:
                        continue
                    for si in self.cells.get((i, j), ()):
                        ax, ay, bx, by = self.segs[si]
                        d = _seg_distance(px, py, ax, ay, bx, by)
                        if best is None or d < best:
                            best = d
            # anything not yet examined lies in a cell at ring r+1 or beyond,
            # whose nearest point is at least r*cell away
            if best is not None and best <= r * cell:
                return best
            r += 1
        return best


def _model(features):
    return [(f["properties"][VALIDATION_KEY], f["geometry"], _bbox(f["geometry"]))
            for f in features]


def _features_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def classify(source_features, candidate_features, samples=2000, seed=2024):
    """The fleet's 2,000-uniform-random-point protocol, over New York's own
    published extent. Returns (agreement_pct, overlap_count, agree, samples).

    ITS BLIND SPOT IS NAMED IN THIS BUILDER'S DOCSTRING: it answered 99.90% to
    100% with zero overlaps on a villages file whose drawn line ran up to 1.6 km
    from the publisher's own, because 2,000 points over 36 square degrees cannot
    see where a line is. chord_stray() is the gate for that; this one is the gate
    for a point landing in the WRONG feature or in two."""
    src = _model(source_features)
    new = _model(candidate_features)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = _features_at(new, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = _features_at(src, pt)
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    return 100.0 * agree / samples, overlaps, agree, samples


def chord_stray(source_features, built_features):
    """How far the publisher's own line strays from the chord drawn in its place.

    THE DIRECTION MATTERS AND THE OBVIOUS ONE GATES NOTHING: simplification KEEPS
    a subset of source vertices, so every drawn vertex already lies on the source
    line and "no drawn vertex further than X from the source" is ~0 by
    construction. What a reader sees is the true line leaving the chord, so that
    is what is measured. Returns (worst_m, over_ceiling, vertices, mean_m)."""
    built = {f["properties"][VALIDATION_KEY]: f for f in built_features}
    worst = 0.0
    over = 0
    n = 0
    total = 0.0
    for f in source_features:
        key = f["properties"][VALIDATION_KEY]
        if key not in built:
            raise RuntimeError("chord_stray: %r is in the fetch and not in the built layer" % key)
        sb = _bbox(f["geometry"])
        lat0 = 0.5 * (sb[1] + sb[3])
        index = SegmentIndex([_project(r, lat0) for r in _rings(built[key]["geometry"])])
        if not index:
            raise RuntimeError("chord_stray: %r came out of mapshaper with no rings" % key)
        for ring in _rings(f["geometry"]):
            for px, py in _project(ring, lat0):
                d = index.distance(px, py)
                if d is None:
                    raise RuntimeError("chord_stray: no segment found near a source vertex of %r" % key)
                total += d
                n += 1
                if d > worst:
                    worst = d
                if d > CHORD_CEILING_M:
                    over += 1
    return worst, over, n, (total / n if n else 0.0)


def exact_vertex_share(a_features, b_features):
    """The share of layer A's built vertices that are ALSO a built vertex of
    layer B. Under one shared topology a vertex on a shared arc is the SAME
    vertex in both layers, so this is the cheapest possible proof the topology
    exists -- and it needs no source and no geometry library, which is why
    ny/scripts/validate_index.py can run it as a merge gate."""
    def verts(features):
        out = set()
        for f in features:
            geom = f.get("geometry")
            if not geom:
                continue

            def walk(c):
                if c and isinstance(c[0], (int, float)):
                    out.add((c[0], c[1]))
                else:
                    for x in c:
                        walk(x)

            walk(geom["coordinates"])
        return out

    av, bv = verts(a_features), verts(b_features)
    if not av:
        return 0.0, 0, 0
    shared = len(av & bv)
    return 100.0 * shared / len(av), shared, len(av)


def coincident_stray(a_built, b_source, b_built):
    """On the stretches the PUBLISHER draws once, how far apart do the two BUILT
    layers draw it? A vertex of A is on such a stretch when it sits within
    COINCIDENT_M of B's source boundary; the publisher's own divergences (the
    Great Lakes water extents, the five boroughs' mutual lines, which exist in
    no town) fall out on their own rather than being excluded by name.
    Returns (coincident, total, worst_m)."""
    b_src_boxes = [(f["geometry"], _bbox(f["geometry"])) for f in b_source]
    b_bld_boxes = [(f["geometry"], _bbox(f["geometry"])) for f in b_built]
    coincident = 0
    total = 0
    worst = 0.0
    for f in a_built:
        ab = _bbox(f["geometry"])
        lat0 = 0.5 * (ab[1] + ab[3])
        pad = 0.05

        def near(boxes):
            rings = []
            for geom, bb in boxes:
                if (bb[0] <= ab[2] + pad and bb[2] >= ab[0] - pad
                        and bb[1] <= ab[3] + pad and bb[3] >= ab[1] - pad):
                    rings.extend(_project(r, lat0) for r in _rings(geom))
            return rings

        src_index = SegmentIndex(near(b_src_boxes))
        bld_index = SegmentIndex(near(b_bld_boxes))
        if not src_index or not bld_index:
            continue
        for ring in _rings(f["geometry"]):
            for px, py in _project(ring, lat0):
                total += 1
                d_src = src_index.distance(px, py)
                if d_src is None or d_src > COINCIDENT_M:
                    continue
                coincident += 1
                d_bld = bld_index.distance(px, py)
                if d_bld is not None and d_bld > worst:
                    worst = d_bld
    return coincident, total, worst


def check_nyc_flag(county_features):
    """The 5/57 split the flag carries. Refuses rather than shipping a fabric in
    which a future county-legislature card would answer for a borough."""
    flagged = {}
    for f in county_features:
        props = f["properties"]
        if props.get("NYC") == "Y":
            flagged[props["FIPS_CODE"]] = props["NAME"]
    if set(flagged) != set(NYC_FIPS):
        raise RuntimeError(
            "ny-counties: the NYC flag reads 'Y' on %r, expected exactly %r "
            "-- refusing to write" % (sorted(flagged.items()), sorted(NYC_FIPS.items()))
        )
    others = [f["properties"]["NAME"] for f in county_features
              if f["properties"].get("NYC") not in ("Y", "N")]
    if others:
        raise RuntimeError(
            "ny-counties: NYC flag is neither 'Y' nor 'N' on %r -- refusing to write" % others
        )


def strip_for_shipping(features, synth_muni_type):
    out = []
    for f in features:
        props = dict(f["properties"])
        props.pop(VALIDATION_KEY, None)
        if synth_muni_type is not None:
            props["MUNI_TYPE"] = synth_muni_type
        out.append({"type": "Feature", "properties": props, "geometry": f["geometry"]})
    return {"type": "FeatureCollection", "features": out}


def simplify_all(sources, interval, tmp):
    """Write the three keyed fetches, run mapshaper once, read the three results
    back keyed by layer id."""
    src_paths = []
    for cfg in LAYERS:
        p = os.path.join(tmp, cfg["id"] + "-src.geojson")
        with open(p, "w") as fh:
            json.dump(sources[cfg["id"]], fh)
        src_paths.append(p)
    out_dir = os.path.join(tmp, "out-%d" % interval)
    os.makedirs(out_dir, exist_ok=True)
    run_mapshaper_combined(src_paths, interval, out_dir)
    built = {}
    for cfg in LAYERS:
        p = os.path.join(out_dir, cfg["id"] + "-src.json")
        if not os.path.exists(p):
            raise RuntimeError("mapshaper wrote no output for %r (looked for %s)" % (cfg["id"], p))
        with open(p) as fh:
            built[cfg["id"]] = json.load(fh)["features"]
    return built


def report_layer(cfg, source_features, built_features):
    """Every number this build is judged on, printed whether it passes or not."""
    count_ok = len(built_features) == cfg["expected_count"]
    pct, overlaps, agree, samples = classify(source_features, built_features)
    worst, over, nverts, mean = chord_stray(source_features, built_features)
    over_pct = 100.0 * over / nverts if nverts else 0.0
    shipped = strip_for_shipping(built_features, cfg["synth_muni_type"])
    compact = json.dumps(shipped, separators=(",", ":"))
    passed = (count_ok and overlaps == 0 and pct >= 99.5
              and over_pct <= CHORD_OVER_CEILING_MAX_PCT)
    print(
        "  %-13s %4d/%-4d feats | %8d bytes | classify %6.2f%% (%d/%d) overlaps %d "
        "| chord worst %7.1f m mean %5.2f m | over %.0f m: %d of %d (%.3f%%) -> %s"
        % (cfg["id"], len(built_features), cfg["expected_count"], len(compact),
           pct, agree, samples, overlaps, worst, mean, CHORD_CEILING_M,
           over, nverts, over_pct, "PASS" if passed else "FAIL"),
        file=sys.stderr,
    )
    return {"cfg": cfg, "passed": passed, "compact": compact, "shipped": shipped,
            "agreement_pct": pct, "overlaps": overlaps, "chord_worst": worst,
            "chord_over_pct": over_pct, "count_ok": count_ok}


def report_shared_edges(sources, built, interval):
    """The cross-layer gates. Returns (all_passed, lines)."""
    ok = True
    for edge in SHARED_EDGES:
        a, b, mode = edge["a"], edge["b"], edge["mode"]
        coincident, total, worst = coincident_stray(built[a], sources[b]["features"], built[b])
        if mode == "exact":
            share, shared, av = exact_vertex_share(built[a], built[b])
            edge_ok = (worst == 0.0 and share >= SHARED_VERTEX_MIN_PCT)
            print(
                "  %s -> %s (exact): %d of %d vertices on a line the publisher draws once; "
                "built layers disagree by %.1f m at worst; %.2f%% of %s vertices ARE %s "
                "vertices (%d of %d, floor %.1f%%) -> %s"
                % (a, b, coincident, total, worst, share, a, b, shared, av,
                   SHARED_VERTEX_MIN_PCT, "PASS" if edge_ok else "FAIL"),
                file=sys.stderr,
            )
        else:
            edge_ok = worst <= interval
            print(
                "  %s -> %s (bounded by the interval): %d of %d vertices coincident at "
                "source; built layers disagree by %.1f m at worst, ceiling %d m -> %s"
                % (a, b, coincident, total, worst, interval,
                   "PASS" if edge_ok else "FAIL"),
                file=sys.stderr,
            )
        ok = ok and edge_ok
    return ok


def build(interval, write):
    sources = {}
    for cfg in LAYERS:
        sources[cfg["id"]] = fetch_layer(cfg)
        print("%s (%s %s): fetched %d features"
              % (cfg["id"], cfg["service_path"], cfg["service_layer_name"],
                 len(sources[cfg["id"]]["features"])), file=sys.stderr)
    check_nyc_flag(sources["counties"]["features"])

    with tempfile.TemporaryDirectory() as tmp:
        built = simplify_all(sources, interval, tmp)
        print("=== dp keep-shapes interval=%d, ONE shared topology ===" % interval, file=sys.stderr)
        results = [report_layer(cfg, sources[cfg["id"]]["features"], built[cfg["id"]])
                   for cfg in LAYERS]
        edges_ok = report_shared_edges(sources, built, interval)

    failed = [r["cfg"]["id"] for r in results if not r["passed"]]
    if failed or not edges_ok:
        raise RuntimeError(
            "refusing to write: layer gates failed for %r; cross-layer gates %s. "
            "Every number is printed above."
            % (failed, "passed" if edges_ok else "FAILED")
        )
    if not write:
        return results

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    for r in results:
        # Round-trip what is about to be written, so a serialization bug cannot
        # ship silently.
        if json.loads(r["compact"]) != r["shipped"]:
            raise RuntimeError("%s round-trip mismatch before writing" % r["cfg"]["id"])
        path = os.path.join(APP_DATA_DIR, r["cfg"]["out_file"])
        with open(path, "w") as fh:
            fh.write(r["compact"])
        print("%s -> data/app/%s: %d bytes"
              % (r["cfg"]["id"], r["cfg"]["out_file"], len(r["compact"])), file=sys.stderr)
    print("Rebuild data/app/judicial-districts.json in the same change: "
          "python3 ny/scripts/build_ny_judicial_districts.py", file=sys.stderr)
    return results


def sweep():
    """Print the interval table this builder's INTERVAL_M comes out of. Writes
    nothing: it exists so the byte-versus-fidelity trade can be seen measured
    rather than argued, and re-measured when a layer joins or leaves the run."""
    sources = {}
    for cfg in LAYERS:
        sources[cfg["id"]] = fetch_layer(cfg)
    check_nyc_flag(sources["counties"]["features"])
    with tempfile.TemporaryDirectory() as tmp:
        for interval in SWEEP_INTERVALS:
            built = simplify_all(sources, interval, tmp)
            print("=== dp keep-shapes interval=%d ===" % interval, file=sys.stderr)
            total = 0
            for cfg in LAYERS:
                r = report_layer(cfg, sources[cfg["id"]]["features"], built[cfg["id"]])
                total += len(r["compact"])
            report_shared_edges(sources, built, interval)
            print("  total %d bytes across the three files" % total, file=sys.stderr)


def main(argv):
    if "--sweep" in argv:
        sweep()
        return 0
    build(INTERVAL_M, write=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
