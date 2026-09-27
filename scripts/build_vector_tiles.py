#!/usr/bin/env python3
"""Build a vector-tile archive per shipped polygon layer, and prove it answers
the way the file it was built from answers.

WHY. docs/OPTIMIZATION_PLAYBOOK.md §10, finding 5: a layer drawn from a shipped
file downloads the whole state to draw one screen — 2.3 MB gzipped for
Wisconsin's unified school districts — and draws it at one resolution whatever
the zoom. A tile archive holds each layer at every zoom from 4 to 12, a screen
at a time, so a reader downloads what they look at and sees more detail the
closer they zoom. Phase 3 of that plan built the archives and their gate;
phases 4 and 5 moved the app onto them, and every layer registered with
`tiles:` is now drawn and answered from its archive.

WHAT IS COMMITTED. Only the archive of a layer the app draws from tiles
(the operator's ruling, 2026-09-26). An archive is a binary several times the
gzipped file and every rebuild adds a full copy to git history, so each layer's
archive is committed in the pull request that switches that layer to tiles.
For any other layer the script builds into a temporary directory and throws it
away, and what it keeps is the answer to one question: would these archives be
correct? `--out DIR` keeps them. `--committed` holds the SHIPPED archives to
today's files without tippecanoe, and requires the archives shipped and the
layers registered with `tiles:` to be the same set.

WHICH LAYERS. Every polygon layer drawn from this site's own files, in every
app — not only the large ones, also the operator's ruling. Which files a layer
draws is MEASURED, not declared: `layer-sources.json`, written by
scripts/probe_layer_sources.mjs, records the `data/app` files each layer
fetched when it was switched on, and for a county-dispatched layer the files
each county's entry fetched on its own. One archive per LAYER, so a
county-dispatched layer's counties are one archive with the county key on each
feature (`_c`), which is how the app tags them (`dxCounty`); a county whose
entry reads a live service is left out, since its tiles are phase 6. A layer
that is not county-dispatched is tiled only when ALL its shapes are shipped
(`source` is `shipped`): an archive of a mostly-live layer's one or two local
files would draw a layer with holes. The probe matches files by the features
the layer actually loaded, so a coverage test's outline fetched beside it is
not mistaken for something it draws. A feature that is not a polygon is left
out.

THE GATE. Each archive is read back and held to the file it was built from:

  1. EVERY FEATURE IS IN THE ARCHIVE AT ITS DEEPEST ZOOM, found at a point inside it
     (shapely's point_on_surface), and its properties read back EXACTLY under
     one decoding rule. The tile format has no arrays, objects or null, so
     tippecanoe writes an array or object as its JSON text and drops a null;
     the rule parses a string that is JSON text back into its value and treats
     a missing key as null. That rule is only unambiguous if no source string
     already looks like an array or object, so a file where one does FAILS
     rather than being decoded wrongly.
  2. A POINT'S ANSWER IS THE SAME. Points are placed near district edges on
     purpose, where tiles and the file can disagree, and each is answered twice:
     from the whole file by the app's own rule (even-odd within a Polygon, any
     part of a MultiPolygon), and from the deepest tile under it by even-odd
     across the tile feature's rings, which is how the app will read a tile. The answer is the SET of features containing the point,
     because several layers overlap. A disagreement at a point two metres or
     more from every edge FAILS. Under two metres they are counted and
     printed: zoom 12's grid step is about two metres, and the shipped files
     already stray further than that from the true line (the Illinois
     legislative outlines by up to 17.8 m, by design), so an answer there
     means nothing.

THE DEEPEST ZOOM IS 12 (the operator's ruling, 2026-09-27). The archives were
first built to zoom 13 with a one-metre tolerance; measured across the fleet
that day, zoom 13 came to 102.0 MB of archives and zoom 12 to 58.4 MB, with
both passing the gate on every layer at their own grid step. The map still
draws closer than zoom 12 by scaling the zoom-12 tiles.

Distances are measured in Web Mercator metres times the cosine of the point's
latitude, which is exact locally. The sample is seeded, so a run is
repeatable, and the gate reads an archive back rather than comparing its
bytes, so nothing depends on tippecanoe writing identical bytes twice.

    python3 scripts/build_vector_tiles.py               # build and gate everything
    python3 scripts/build_vector_tiles.py --only wi:school-districts-unified --out build/tiles
    python3 scripts/build_vector_tiles.py --only il     # one app
    python3 scripts/build_vector_tiles.py --committed   # the shipped archives

Needs tippecanoe (2.49 measured) on PATH, and shapely, mapbox-vector-tile and
pmtiles (scripts/requirements.txt).
"""

import argparse
import gzip
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(REPO_ROOT, "layer-sources.json")

MAX_ZOOM = 12
MIN_ZOOM = 4
LAYER_NAME = "d"
# Tolerance for the edge test: the zoom-12 grid step. Stated in §10.
EDGE_TOLERANCE_M = 2.0
# How far from an edge the sample points are placed.
SAMPLE_RADIUS_M = 20.0
POLYGON_TYPES = ("Polygon", "MultiPolygon")
# Longest edge handed to tippecanoe, in degrees (about a kilometre). The app
# tests a point against edges that are straight in longitude/latitude; a tile
# stores edges that are straight in Web Mercator, and over a long edge the two
# lines part — measured on New York's Lake Erie county lines, a 1-4 m
# disagreement on edges tens of kilometres long. Splitting every longer edge
# brings the two within about 3 cm, which the gate then holds.
MAX_EDGE_DEG = 0.01

TIPPECANOE_ARGS = [
    "-Z%d" % MIN_ZOOM, "-z%d" % MAX_ZOOM,
    # simplify at the lower zooms only, so the deepest zoom carries every vertex the
    # file carries and the card can be answered from it
    "--simplify-only-low-zooms",
    # districts share borders; simplify each shared edge once, so neighbours
    # stay flush at every zoom
    "--detect-shared-borders",
    # never thin a layer's features to fit a tile: a district missing from a
    # tile is a wrong answer, not a lighter one
    "--no-feature-limit", "--no-tile-size-limit",
    # keep every polygon however small: a sliver district missing from the
    # deepest tile is a card with no answer (one Illinois library district's
    # was dropped at zoom 12 without this, measured 2026-09-27)
    "--no-tiny-polygon-reduction",
    "--force", "--quiet",
]

EARTH_R = 6378137.0


def fail(msg):
    print("build-vector-tiles: FAIL — " + msg)
    sys.exit(1)


def need_tools():
    if not shutil.which("tippecanoe"):
        fail("tippecanoe is not on PATH (apt install tippecanoe, or build "
             "felt/tippecanoe); nothing can be built without it")
    try:
        import shapely  # noqa: F401
        import mapbox_vector_tile  # noqa: F401
        import pmtiles  # noqa: F401
    except ImportError as e:
        fail("%s — pip install -c scripts/requirements.txt shapely "
             "mapbox-vector-tile pmtiles" % e)


# ---- which files each layer draws ------------------------------------------

def plan(only):
    """[(tag, layer, [(county_key or None, repo-relative path)])], from the
    measured layer-sources.json, keeping layers that draw a shipped polygon."""
    if not os.path.isfile(SOURCES):
        fail("layer-sources.json is missing; run scripts/probe_layer_sources.mjs")
    doc = json.load(open(SOURCES, encoding="utf-8"))
    out, unmeasured = [], []
    for tag, app in sorted(doc["apps"].items()):
        for layer, rec in sorted(app["layers"].items()):
            if only and not any(o == tag or o == "%s:%s" % (tag, layer) for o in only):
                continue
            if "files" not in rec:
                unmeasured.append("%s:%s" % (tag, layer))
                continue
            counties = rec.get("counties") or {}
            if counties.get("files"):
                pairs = [(key, f) for key, fs in sorted(counties["files"].items()) for f in fs]
            elif rec.get("source") == "shipped":
                pairs = [(None, f) for f in rec["files"]]
            else:
                # drawn from a live service, perhaps with a shipped file or two
                # beside it: an archive of the shipped part would draw a layer
                # with holes, so it waits for phase 6
                continue
            keep = []
            for key, url in pairs:
                rel = url.lstrip("/")
                if "/data/app/" not in "/" + rel:
                    continue
                if not os.path.isfile(os.path.join(REPO_ROOT, rel)):
                    fail("%s:%s names %s, which is not in the tree — re-run the "
                         "probe" % (tag, layer, rel))
                keep.append((key, rel))
            if keep:
                out.append((tag, layer, keep))
    if unmeasured:
        fail("layer-sources.json predates the `files` field for %d layer(s) "
             "(%s…); re-run scripts/probe_layer_sources.mjs"
             % (len(unmeasured), ", ".join(unmeasured[:3])))
    return out


# ---- geometry helpers -------------------------------------------------------

def merc(lng, lat):
    x = math.radians(lng) * EARTH_R
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * EARTH_R
    return x, y


def unmerc(x, y):
    return (math.degrees(x / EARTH_R),
            math.degrees(2 * math.atan(math.exp(y / EARTH_R)) - math.pi / 2))


def rings_of(geom):
    """Every ring of a Polygon/MultiPolygon, as lists of (x, y)."""
    if geom["type"] == "Polygon":
        return [r for r in geom["coordinates"]]
    return [r for poly in geom["coordinates"] for r in poly]


def parts_of(geom):
    """A Polygon or MultiPolygon as a list of parts, each a list of rings."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    return list(geom["coordinates"])


def app_inside(x, y, geom):
    """The app's pointInGeometry exactly: even-odd across the rings of a
    Polygon, and a MultiPolygon holds the point when ANY part does. The parts
    are OR'd, not XOR'd, so a part lying inside another part is not a hole."""
    return any(even_odd(x, y, rings) for rings in parts_of(geom))


def even_odd(x, y, rings):
    """Even-odd across a list of rings: inside when a ray crosses an odd
    number of edges, so a hole is a hole whatever its winding. The app's rule
    for one Polygon (see app_inside for a MultiPolygon), and the rule applied
    to a decoded tile feature, whose rings the builder made valid."""
    inside = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def tile_of(lng, lat, z):
    n = 2 ** z
    xf = (lng + 180) / 360 * n
    lat_r = math.radians(lat)
    yf = (1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n
    return int(xf), int(yf), xf - int(xf), yf - int(yf)


def even_odd_region(geom):
    """The area the app's even-odd rule calls inside, as valid geometry wound
    the way the tile format reads it (outer rings one way, holes the other).

    tippecanoe decides which ring is a hole by its WINDING, as the tile format
    requires, while the app ignores winding and counts crossings — so a source
    ring meant as a hole but wound like an outer ring (a Stephenson County fire
    district carries fourteen) is filled in the tile and empty on the card.
    Within one Polygon the symmetric difference of its rings, each taken as a
    filled polygon, IS the even-odd area whatever the winding; a MultiPolygon
    is the UNION of its parts' areas, because the app counts a point inside
    when any part holds it. That is what is tiled; the gate still asks the
    ORIGINAL geometry for the answer (app_inside)."""
    import shapely
    from shapely.geometry import Polygon, mapping
    areas = []
    for rings in parts_of(geom):
        polys = [shapely.segmentize(shapely.make_valid(Polygon(r)), MAX_EDGE_DEG)
                 for r in rings if len(r) >= 4]
        if polys:
            areas.append(shapely.make_valid(shapely.symmetric_difference_all(polys)))
    if not areas:
        return None
    region = shapely.make_valid(shapely.union_all(areas))
    polys = [g for g in getattr(region, "geoms", [region]) if g.geom_type in POLYGON_TYPES]
    flat = []
    for g in polys:
        flat.extend(getattr(g, "geoms", [g]))
    flat = [g for g in flat if not g.is_empty and g.area > 0]
    if not flat:
        return None
    out = shapely.orient_polygons(shapely.MultiPolygon(flat) if len(flat) > 1 else flat[0])
    return mapping(out)


# ---- properties -------------------------------------------------------------

def looks_like_json_container(v):
    if not isinstance(v, str):
        return False
    s = v.strip()
    if not (s.startswith("[") or s.startswith("{")):
        return False
    try:
        return isinstance(json.loads(s), (list, dict))
    except ValueError:
        return False


def decode_props(props):
    out = {}
    for k, v in props.items():
        if looks_like_json_container(v):
            v = json.loads(v)
        out[k] = v
    return out


def same_props(src, got):
    """src is the source feature's properties; got the tile's, decoded. A null
    in the source is a missing key in the tile. Numbers compare by value,
    because the tile format stores an integer-valued double as an integer."""
    keys = set(src) | set(got)
    for k in keys:
        a, b = src.get(k), got.get(k)
        if a is None and k not in got:
            continue
        if isinstance(a, bool) or isinstance(b, bool):
            if a is not b:
                return k
            continue
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a != b and not (math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)):
                return k
            continue
        if a != b:
            return k
    return None


# ---- what an app's loader adds ------------------------------------------------

# Properties an app's loader ADDS to the features of one file after fetching
# it, which the archive must carry too because the card reads them. Stated
# here beside nothing else, and held to the app by scripts/probe_tile_cards.mjs,
# which fails the moment a tiled card differs from the card the whole file
# gives. Keyed (app, layer) -> {file: {property: value}}.
LOADER_ADDS = {
    # wi/index.html loadElectedBoardDistricts tags each feature with the
    # board whose file it came from; the card, hover and roster read it
    ("wi", "mps-school-board"): {
        "wi/data/app/mps-school-board-districts.json": {"board": "mps"},
        "wi/data/app/rusd-school-board-districts.json": {"board": "rusd"},
    },
}


# ---- build ------------------------------------------------------------------

def collect(tag, layer, pairs):
    """The features one archive is built from, each given an integer id (the
    tile's feature id) and `_s`/`_i` (which file, which feature in it) plus
    `_c` for a county-dispatched layer. Returns (features, files, skipped)."""
    feats, files, skipped = [], [], 0
    for key, rel in pairs:
        if rel not in files:
            files.append(rel)
        s = files.index(rel)
        doc = json.load(open(os.path.join(REPO_ROOT, rel), encoding="utf-8"))
        for i, f in enumerate(doc.get("features") or []):
            g = f.get("geometry")
            if not g or g.get("type") not in POLYGON_TYPES:
                skipped += 1
                continue
            props = dict(f.get("properties") or {})
            props.update(LOADER_ADDS.get((tag, layer), {}).get(rel, {}))
            for k, v in props.items():
                if looks_like_json_container(v):
                    fail("%s:%s — %s feature %d has a string property %r that "
                         "reads as JSON; the tile decoding rule would turn it "
                         "into a list or object" % (tag, layer, rel, i, k))
                if k in ("_s", "_i", "_c"):
                    fail("%s:%s — %s already carries a %r property, which the "
                         "archive uses for itself" % (tag, layer, rel, k))
            tprops = dict(props, _s=s, _i=i)
            if key is not None:
                tprops["_c"] = key
            tile_geom = even_odd_region(g)
            if tile_geom is None:
                fail("%s:%s — %s feature %d encloses no area under the even-odd "
                     "rule" % (tag, layer, rel, i))
            feats.append({"type": "Feature", "id": len(feats), "geometry": g,
                          "tile_geometry": tile_geom,
                          "properties": tprops, "_src": props, "_key": key})
    return feats, files, skipped


def county_keys(feats):
    return sorted({f["_key"] for f in feats if f["_key"] is not None})


def archive_counties(archive_path):
    """The county keys an archive's metadata declares, or None if it
    declares none."""
    from pmtiles.reader import Reader, MmapSource
    with open(archive_path, "rb") as fh:
        meta = Reader(MmapSource(fh)).metadata()
    try:
        d = json.loads(meta.get("description") or "null")
    except ValueError:
        return None
    return d.get("counties") if isinstance(d, dict) else None


def build(feats, out_path, workdir):
    seq = os.path.join(workdir, "in.geojsonseq")
    with open(seq, "w", encoding="utf-8") as fh:
        for f in feats:
            fh.write(json.dumps({"type": "Feature", "id": f["id"], "geometry": f["tile_geometry"],
                                 "properties": f["properties"]},
                                separators=(",", ":")) + "\n")
    cmd = ["tippecanoe", "-o", out_path, "-l", LAYER_NAME, "-P"] + TIPPECANOE_ARGS
    # A county-dispatched layer's archive names the counties it holds, so the
    # app can tell a county drawn from the tiles from one it reads live
    # (tile-overlay block, countyTileKeys). tippecanoe writes the description
    # into the archive's JSON metadata, which follows the root directory.
    keys = county_keys(feats)
    if keys:
        cmd += ["-N", json.dumps({"counties": keys}, separators=(",", ":"))]
    cmd.append(seq)
    got = subprocess.run(cmd, capture_output=True, text=True)
    if got.returncode != 0:
        fail("tippecanoe failed on %s: %s" % (out_path, got.stderr.strip()[-400:]))


# ---- gate -------------------------------------------------------------------

class Archive:
    def __init__(self, path):
        from pmtiles.reader import Reader, MmapSource
        self._fh = open(path, "rb")
        self._r = Reader(MmapSource(self._fh))
        self._cache = {}

    def close(self):
        self._fh.close()

    def tile(self, x, y):
        key = (x, y)
        if key not in self._cache:
            import mapbox_vector_tile
            raw = self._r.get(MAX_ZOOM, x, y)
            feats = []
            if raw:
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                t = mapbox_vector_tile.decode(raw, default_options={"y_coord_down": True})
                layer = t.get(LAYER_NAME) or {"extent": 4096, "features": []}
                ext = layer["extent"]
                for ft in layer["features"]:
                    g = ft["geometry"]
                    if g["type"] not in POLYGON_TYPES:
                        continue
                    feats.append((ft["id"], rings_of(g), ft["properties"]))
            else:
                ext = 4096
            self._cache[key] = (ext, feats)
        return self._cache[key]

    def present(self, lng, lat):
        """{id: properties} of every tile feature in the deepest tile under the point."""
        x, y, fx, fy = tile_of(lng, lat, MAX_ZOOM)
        ext, feats = self.tile(x, y)
        return {fid: props for fid, rings, props in feats}

    def answer(self, lng, lat):
        """{id: properties} of every tile feature containing the point."""
        x, y, fx, fy = tile_of(lng, lat, MAX_ZOOM)
        ext, feats = self.tile(x, y)
        px, py = fx * ext, fy * ext
        return {fid: props for fid, rings, props in feats if even_odd(px, py, rings)}


def gate(tag, layer, feats, archive_path, n_points, seed):
    from shapely.geometry import shape, Point
    from shapely.strtree import STRtree
    from shapely import transform

    def to_merc(coords):
        import numpy as np
        lng, lat = coords[:, 0], coords[:, 1]
        x = np.radians(lng) * EARTH_R
        y = np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)) * EARTH_R
        return np.column_stack([x, y])

    # The even-odd region, not the raw rings: an interior point of an invalid
    # polygon can land in what the app counts as a hole, and an edge is only
    # an edge where it bounds that region. Segmentized, as the tiles are, so
    # an edge straight in longitude/latitude is measured with its bend. The
    # ANSWER is still the raw rings' (full_answer below), so this chooses
    # where to look and never what is right.
    shapes = [shape(f["tile_geometry"]) for f in feats]
    mshapes = [transform(s, to_merc) for s in shapes]
    bounds = [s.boundary for s in mshapes]
    tree = STRtree(mshapes)
    geoms = [f["geometry"] for f in feats]

    def full_answer(lng, lat):
        mx, my = merc(lng, lat)
        cand = tree.query(Point(mx, my))
        return {int(j) for j in cand if app_inside(lng, lat, geoms[j])}

    def edge_distance_m(lng, lat):
        mx, my = merc(lng, lat)
        p = Point(mx, my)
        r = SAMPLE_RADIUS_M * 3 / math.cos(math.radians(lat))
        cand = tree.query(p.buffer(r))
        if len(cand) == 0:
            return float("inf")
        d = min(bounds[j].distance(p) for j in cand)
        return d * math.cos(math.radians(lat))

    arch = Archive(archive_path)
    problems = []
    # 0. the counties the archive says it holds are the counties it was built
    # from: the app draws a county from the tiles only if the archive names it
    # and reads every other county live, so a stale list draws a county twice
    # or not at all
    want_keys = county_keys(feats) or None
    got_keys = archive_counties(archive_path)
    if want_keys != got_keys:
        problems.append("the archive declares counties %s, and it was built from %s"
                        % (got_keys, want_keys))
    try:
        # 1. presence and properties, in the deepest tile under a point
        # inside each feature. PRESENCE, not containment: on a district a
        # few metres wide the interior point can sit inside the grid-step
        # tolerance of an edge (a 6 m strip of Franklin County's Crab Orchard
        # library district put it 0.44 m from one), and whether a point that
        # close answers is the edge test's question, not this one's
        for j, s in enumerate(shapes):
            p = s.point_on_surface()
            got = arch.present(p.x, p.y)
            if j not in got:
                problems.append("feature %d (%s) is not in the deepest tile under "
                                "a point inside it" % (j, label(feats[j])))
                continue
            bad = same_props(feats[j]["_src"], {k: v for k, v in decode_props(got[j]).items()
                                                 if k not in ("_s", "_i", "_c")})
            if bad:
                problems.append("feature %d (%s): property %r reads back as %r, "
                                "not %r" % (j, label(feats[j]), bad,
                                           decode_props(got[j]).get(bad),
                                           feats[j]["_src"].get(bad)))
            if len(problems) > 20:
                break

        # 2. answers near edges
        rnd = random.Random(seed)
        lengths = [b.length for b in bounds]
        total = sum(lengths)
        near = far = near_bad = 0
        far_bad = []
        tries = 0
        while near + far < n_points and tries < n_points * 4 and total > 0:
            tries += 1
            j = rnd.choices(range(len(bounds)), weights=lengths)[0]
            q = bounds[j].interpolate(rnd.random(), normalized=True)
            qlng, qlat = unmerc(q.x, q.y)
            a = rnd.uniform(0, 2 * math.pi)
            d = rnd.uniform(0, SAMPLE_RADIUS_M) / math.cos(math.radians(qlat))
            lng, lat = unmerc(q.x + d * math.cos(a), q.y + d * math.sin(a))
            want = full_answer(lng, lat)
            got = set(arch.answer(lng, lat))
            dist = edge_distance_m(lng, lat)
            if dist < EDGE_TOLERANCE_M:
                near += 1
                near_bad += want != got
            else:
                far += 1
                if want != got:
                    far_bad.append((lat, lng, round(dist, 2), sorted(want), sorted(got)))
        for lat, lng, dist, want, got in far_bad[:5]:
            problems.append("%.6f,%.6f is %.2f m from any edge and the file answers "
                            "%s where the tile answers %s" % (lat, lng, dist, want, got))
        if len(far_bad) > 5:
            problems.append("… and %d more such points" % (len(far_bad) - 5))
    finally:
        arch.close()
    return problems, {"near": near, "near_bad": near_bad, "far": far, "far_bad": len(far_bad)}


def label(f):
    p = f["_src"]
    for k in ("name", "NAME", "district", "DISTRICT", "label"):
        if p.get(k) not in (None, ""):
            return "%s=%s" % (k, p[k])
    return "no name"


# ---- main -------------------------------------------------------------------

def run_one(job, out_root, tmp, n_points, seed):
    """Build and gate one archive. Returns (report lines, stats, failed)."""
    tag, layer, pairs = job
    t0 = time.time()
    feats, files, skipped = collect(tag, layer, pairs)
    name = "%s:%s" % (tag, layer)
    if not feats:
        return ["  skip  %-40s no polygon features in %d file(s)" % (name, len(files))], None, False
    os.makedirs(os.path.join(out_root, tag), exist_ok=True)
    path = os.path.join(out_root, tag, layer + ".pmtiles")
    work = tempfile.mkdtemp(dir=tmp)
    build(feats, path, work)
    shutil.rmtree(work)
    src = sum(len(gzip.compress(open(os.path.join(REPO_ROOT, f), "rb").read())) for f in files)
    arch = os.path.getsize(path)
    problems, st = gate(tag, layer, feats, path, n_points, seed)
    st.update(src=src, arch=arch, feats=len(feats))
    lines = ["  %-4s  %-40s %5d features from %3d file(s)%s, %7.0f KB gz -> %7.0f KB "
             "archive; %d/%d points under %g m differ, %d/%d beyond; %.0fs"
             % ("FAIL" if problems else "ok", name, len(feats), len(files),
                " (%d non-polygon skipped)" % skipped if skipped else "",
                src / 1024, arch / 1024, st["near_bad"], st["near"], EDGE_TOLERANCE_M,
                st["far_bad"], st["far"], time.time() - t0)]
    lines += ["          " + p for p in problems]
    return lines, st, bool(problems)


# Everything whose change can change every archive, so --changed-since
# rebuilds all of them when one of these moves.
ALL_INPUTS = ("scripts/build_vector_tiles.py", "scripts/requirements.txt", "layer-sources.json")


def changed_since(ref):
    got = subprocess.run(["git", "diff", "--name-only", "%s...HEAD" % ref],
                         cwd=REPO_ROOT, capture_output=True, text=True)
    if got.returncode != 0:
        fail("git diff against %s failed: %s" % (ref, got.stderr.strip()))
    return set(got.stdout.split())


def committed_archives():
    """{(tag, layer): path} for every archive an app ships, and the layers an
    app registers with `tiles:` — which must be the same set."""
    import glob
    import re
    shipped = {}
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "data", "app", "tiles", "*.pmtiles"))):
        rel = os.path.relpath(path, REPO_ROOT).split(os.sep)
        shipped[(rel[0], os.path.splitext(rel[-1])[0])] = path
    registered = set()
    for index in sorted(glob.glob(os.path.join(REPO_ROOT, "*", "index.html"))):
        if not os.path.isfile(index):
            continue  # engine/index.html is the engine's block directory
        tag = os.path.basename(os.path.dirname(index))
        for m in re.finditer(r'\btiles:\s*"data/app/tiles/([^"/]+)\.pmtiles"', open(index, encoding="utf-8").read()):
            registered.add((tag, m.group(1)))
    return shipped, registered


def _check_one(key, path, pairs, n_points, seed):
    tag, layer = key
    feats, files, _ = collect(tag, layer, pairs)
    problems, st = gate(tag, layer, feats, path, n_points, seed)
    lines = ["  %-4s  %s:%s (committed) — %d features; %d/%d points under %g m differ, %d/%d beyond"
             % ("FAIL" if problems else "ok", tag, layer, len(feats), st["near_bad"], st["near"],
                EDGE_TOLERANCE_M, st["far_bad"], st["far"])]
    lines += ["          " + p for p in problems]
    return lines, bool(problems)


def check_committed(n_points, seed, n_jobs=1):
    """Hold every SHIPPED archive to the file it was built from, today. A
    change to a boundary file that forgets to rebuild its archive leaves the
    app drawing and answering from the old districts; this is what catches it,
    and it needs no tippecanoe."""
    shipped, registered = committed_archives()
    if set(shipped) != registered:
        fail("the archives shipped under */data/app/tiles/ (%s) and the layers registered with "
             "`tiles:` (%s) differ; an archive nothing draws, or a layer whose archive is "
             "missing" % (sorted("%s:%s" % k for k in shipped) or "none",
                          sorted("%s:%s" % k for k in registered) or "none"))
    if not shipped:
        print("build-vector-tiles: OK — no app ships an archive yet")
        return
    jobs = {(t, l): pairs for t, l, pairs in plan([])}
    # An archive mirrored from a live source (scripts/mirror_tiger_tiles.py,
    # phase 6) has no shipped file to hold it to; that script's --check holds
    # it to the record of what was fetched and built instead.
    mirrored = set()
    record = os.path.join(REPO_ROOT, "tiger-mirror.json")
    if os.path.isfile(record):
        with open(record, encoding="utf-8") as fh:
            mirrored = {tuple(k.split(":", 1)) for k in json.load(fh).get("layers", {})}
    for key in list(shipped):
        if key in mirrored:
            if key in jobs:
                fail("%s:%s is both mirrored and drawn from a shipped file" % key)
            del shipped[key]
        elif key not in jobs:
            fail("%s:%s ships an archive but layer-sources.json names no shipped file for it, "
                 "and tiger-mirror.json does not record it" % key)
    if mirrored:
        print("build-vector-tiles: %d mirrored archive(s) are held to tiger-mirror.json by "
              "scripts/mirror_tiger_tiles.py --check" % len(mirrored))
    from concurrent.futures import ProcessPoolExecutor
    failed = 0
    with ProcessPoolExecutor(max_workers=max(1, n_jobs)) as pool:
        futures = [pool.submit(_check_one, key, path, jobs[key], n_points, seed)
                   for key, path in sorted(shipped.items())]
        for fut in futures:
            lines, bad = fut.result()
            print("\n".join(lines), flush=True)
            failed += bad
    if failed:
        fail("%d shipped archive(s) no longer answer as their files do — rebuild with "
             "--only <tag:layer> --out and copy the archive into <tag>/data/app/tiles/" % failed)
    print("build-vector-tiles: OK — %d shipped archive(s) answer as their files do" % len(shipped))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--committed", action="store_true",
                    help="check the archives the apps ship against today's files (no tippecanoe)")
    ap.add_argument("--only", action="append", default=[],
                    help="an app tag (il) or tag:layer (wi:school-districts-unified); repeatable")
    ap.add_argument("--changed-since", metavar="REF",
                    help="only the layers drawing a file changed since REF (all of them "
                         "when this script, its pins or layer-sources.json changed)")
    ap.add_argument("--out", help="keep the archives here as <tag>/<layer>.pmtiles")
    ap.add_argument("--points", type=int, default=2000,
                    help="edge sample points per archive (default 2000)")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1),
                    help="archives built at once (default: up to 4)")
    args = ap.parse_args()
    if args.committed:
        check_committed(args.points, args.seed, args.jobs)
        return

    jobs = plan(args.only)
    if not jobs:
        fail("no shipped polygon layer matched %s" % (args.only or "the whole fleet"))
    if args.changed_since:
        changed = changed_since(args.changed_since)
        if not changed & set(ALL_INPUTS):
            jobs = [j for j in jobs if any(rel in changed for _, rel in j[2])]
        print("build-vector-tiles: %d file(s) changed since %s; %d layer(s) to build"
              % (len(changed), args.changed_since, len(jobs)))
        if not jobs:
            print("build-vector-tiles: OK — no layer draws a changed file")
            return
    need_tools()

    tmp = tempfile.mkdtemp(prefix="vector-tiles-")
    out_root = args.out or os.path.join(tmp, "out")
    failed = built = 0
    totals = {"src": 0, "arch": 0, "feats": 0, "near": 0, "near_bad": 0, "far": 0, "far_bad": 0}
    try:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            futures = [pool.submit(run_one, j, out_root, tmp, args.points, args.seed) for j in jobs]
            for fut in futures:
                lines, st, bad = fut.result()
                print("\n".join(lines), flush=True)
                if st:
                    built += 1
                    for k in totals:
                        totals[k] += st[k]
                failed += bad
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("build-vector-tiles: %d archive(s), %d features, %.1f MB gzipped source -> %.1f MB "
          "of archives; %d of %d points under %g m of an edge differ, %d of %d beyond (0 allowed)"
          % (built, totals["feats"], totals["src"] / 2**20, totals["arch"] / 2**20,
             totals["near_bad"], totals["near"], EDGE_TOLERANCE_M, totals["far_bad"], totals["far"]))
    if failed:
        fail("%d archive(s) do not answer as their files do" % failed)
    print("build-vector-tiles: OK%s" % ("" if args.out else " — nothing kept (pass --out to keep the archives)"))


if __name__ == "__main__":
    main()
