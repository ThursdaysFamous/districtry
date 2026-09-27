#!/usr/bin/env python3
"""Hold the engine's vector-tile reader to the Python decoders, on real archives.

WHAT IT GUARDS. engine/index.html/vector-tiles.txt reads a PMTiles archive and
decodes its tiles without a library (docs/OPTIMIZATION_PLAYBOOK.md §10,
phase 4), and a card drawn from tiles is answered by it. A decoder that got a
varint, a zigzag or a Hilbert id wrong would put a reader in the wrong
district with every other gate green, because scripts/build_vector_tiles.py
checks archives with the Python decoders and never runs the app's.

HOW. It runs the block AS SHIPPED, read from the engine file and evaluated in
Node, never re-implemented, against each archive and compares it with the
`pmtiles` and `mapbox-vector-tile` packages the builder's gate trusts:

  1. TILES. Up to 300 tiles, spread over every zoom, are fetched by z/x/y
     through the block's own directory walk and decoded; every feature's id,
     properties (arrays parsed back from their JSON text, as the builder
     wrote them) and every ring vertex must equal the Python decode of the
     same tile read by the same z/x/y.
  2. POINTS. 500 points inside the archive's bounds are answered by the
     block's tileFeaturesAt, the function a card calls, with the app's
     even-odd test on the longitude/latitude rings it returns; the ids must
     equal the Python answer from the same tile in tile coordinates.

Which archives: the ones COMMITTED under <instance>/data/app/tiles/ (every
layer drawn from tiles ships its archive there), or the paths given. With no
committed archive and no path it says so and passes, which is the state before
the first layer ships.

    python3 scripts/validate_vector_tiles.py
    python3 scripts/validate_vector_tiles.py build/tiles/wi/school-district-unified.pmtiles

Needs node (18+, for DecompressionStream) and the pmtiles and
mapbox-vector-tile packages (scripts/requirements.txt).
"""

import glob
import gzip
import json
import math
import os
import random
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK = os.path.join(REPO_ROOT, "engine", "index.html", "vector-tiles.txt")
LAYER = "d"

HARNESS = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
const job = JSON.parse(fs.readFileSync(0, "utf8"));
const api = new Function(src + "\nreturn { openTileArchive, decodeTileLayer, tileFeaturesAt };")();
const fd = fs.openSync(job.archive, "r");
function fetchRange(offset, length) {
  const buf = Buffer.alloc(length);
  const n = fs.readSync(fd, buf, 0, length, offset);
  return Promise.resolve(buf.buffer.slice(buf.byteOffset, buf.byteOffset + n));
}
function ringsInside(pt, rings) {
  let inside = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if (((yi > pt[1]) !== (yj > pt[1])) && (pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi)) inside = !inside;
    }
  }
  return inside;
}
(async () => {
  const archive = api.openTileArchive("file", fetchRange);
  const header = await archive.header;
  const tiles = [];
  for (const [z, x, y] of job.tiles) {
    const bytes = await archive.getTile(z, x, y);
    const d = bytes ? api.decodeTileLayer(bytes, "d") : { extent: 4096, features: [] };
    tiles.push({ z, x, y, present: !!bytes, extent: d.extent,
      features: d.features.map((f) => ({ id: f.id, properties: f.properties, rings: f.rings })) });
  }
  const points = [];
  for (const [lng, lat] of job.points) {
    const fc = await api.tileFeaturesAt(archive, { lng, lat });
    points.push(fc.features.filter((f) => ringsInside([lng, lat], f.geometry.coordinates)).map((f) => f.id).sort((a, b) => a - b));
  }
  const metadata = await archive.metadata;
  process.stdout.write(JSON.stringify({ header: { minZoom: header.minZoom, maxZoom: header.maxZoom, bounds: header.bounds }, tiles, points, metadata }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def fail(msg):
    print("validate-vector-tiles: FAIL — " + msg)
    sys.exit(1)


def decode_props(props):
    out = {}
    for k, v in props.items():
        if isinstance(v, str) and v.lstrip()[:1] in ("[", "{"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, (list, dict)):
                    v = parsed
            except ValueError:
                pass
        out[k] = v
    return out


def py_rings(geom):
    """mapbox-vector-tile's polygon rings, closed, as lists of [x, y]."""
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    out = []
    for poly in polys:
        for ring in poly:
            r = [list(p) for p in ring]
            if r and r[0] != r[-1]:
                r.append(list(r[0]))
            out.append(r)
    return out


def canon_rings(rings):
    """Rings as a sorted list of closed vertex lists, so the two decoders are
    compared vertex for vertex without depending on how each groups rings
    into parts."""
    out = []
    for r in rings:
        r = [list(p) for p in r]
        if r and r[0] != r[-1]:
            r.append(list(r[0]))
        out.append(r)
    return sorted(out)


def tile_of(lng, lat, z):
    n = 2 ** z
    xf = (lng + 180) / 360 * n
    lat_r = math.radians(lat)
    yf = (1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n
    return int(xf), int(yf), xf - int(xf), yf - int(yf)


def even_odd(x, y, rings):
    inside = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def check(path, seed):
    import mapbox_vector_tile
    from pmtiles.reader import Reader, MmapSource, all_tiles

    with open(path, "rb") as fh:
        src = MmapSource(fh)
        reader = Reader(src)
        header = reader.header()
        keys = [(z, x, y) for (z, x, y), _ in all_tiles(src)]
        rnd = random.Random(seed)
        by_zoom = {}
        for k in keys:
            by_zoom.setdefault(k[0], []).append(k)
        picked = []
        per = max(1, 300 // max(1, len(by_zoom)))
        for z in sorted(by_zoom):
            picked += rnd.sample(by_zoom[z], min(per, len(by_zoom[z])))
        w, s, e, n = (header["min_lon_e7"] / 1e7, header["min_lat_e7"] / 1e7,
                      header["max_lon_e7"] / 1e7, header["max_lat_e7"] / 1e7)
        points = [[rnd.uniform(w, e), rnd.uniform(s, n)] for _ in range(500)]
        # one tile id nobody holds, so a miss is exercised too
        picked.append((header["max_zoom"], 0, 0))

        job = {"archive": path, "tiles": [list(t) for t in picked], "points": points}
        got = subprocess.run(["node", "-e", HARNESS, BLOCK], input=json.dumps(job),
                             capture_output=True, text=True)
        if got.returncode != 0:
            fail("the block did not run in Node on %s:\n%s" % (path, got.stderr[-2000:]))
        js = json.loads(got.stdout)

        problems = []
        if js["header"]["maxZoom"] != header["max_zoom"] or js["header"]["minZoom"] != header["min_zoom"]:
            problems.append("header zooms %s against %s" % (js["header"], header))
        # the metadata, which carries a county layer's county keys: the app
        # draws a county from the tiles only if the metadata names it
        if js.get("metadata") != reader.metadata():
            problems.append("the metadata reads back differently in Node")

        def py_decode(z, x, y):
            raw = reader.get(z, x, y)
            if not raw:
                return None
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            t = mapbox_vector_tile.decode(raw, default_options={"y_coord_down": True})
            return t.get(LAYER) or {"extent": 4096, "features": []}

        features = 0
        for tile in js["tiles"]:
            z, x, y = tile["z"], tile["x"], tile["y"]
            ref = py_decode(z, x, y)
            if (ref is None) != (not tile["present"]):
                problems.append("tile %d/%d/%d: present %s in the block, %s in Python"
                                % (z, x, y, tile["present"], ref is not None))
                continue
            if ref is None:
                continue
            want = sorted(((f["id"], json.dumps(decode_props(f["properties"]), sort_keys=True),
                            canon_rings(py_rings(f["geometry"])))
                           for f in ref["features"] if f["geometry"]["type"] in ("Polygon", "MultiPolygon")),
                          key=lambda t: t[0])
            have = sorted(((f["id"], json.dumps(f["properties"], sort_keys=True), canon_rings(f["rings"]))
                           for f in tile["features"]), key=lambda t: t[0])
            features += len(have)
            if want != have:
                bad = next((i for i, (a, b) in enumerate(zip(want, have)) if a != b), min(len(want), len(have)))
                problems.append("tile %d/%d/%d decodes differently (%d features in Python, %d in the "
                                "block; first difference at #%d, id %s)"
                                % (z, x, y, len(want), len(have), bad,
                                   want[bad][0] if bad < len(want) else "-"))
            if len(problems) > 10:
                break

        z = header["max_zoom"]
        answered = 0
        for (lng, lat), ids in zip(points, js["points"]):
            x, y, fx, fy = tile_of(lng, lat, z)
            ref = py_decode(z, x, y)
            if ref is None:
                want = []
            else:
                ext = ref["extent"]
                want = sorted(f["id"] for f in ref["features"]
                              if f["geometry"]["type"] in ("Polygon", "MultiPolygon")
                              and even_odd(fx * ext, fy * ext, py_rings(f["geometry"])))
            answered += bool(want)
            if want != ids:
                problems.append("%.6f,%.6f: the block answers %s where the tile holds %s" % (lat, lng, ids, want))
            if len(problems) > 10:
                break
    return problems, len(js["tiles"]), features, len(points), answered


def _check(path):
    return check(path, seed=13)


def main():
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(REPO_ROOT, "*", "data", "app", "tiles", "*.pmtiles")))
    if not paths:
        print("validate-vector-tiles: OK — no archive is committed yet, so there is nothing the app reads")
        return
    failed = 0
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
        results = list(pool.map(_check, paths))
    for p, (problems, tiles, feats, pts, answered) in zip(paths, results):
        rel = os.path.relpath(p, REPO_ROOT)
        print("  %-4s  %s: %d tiles (%d features) decode as Python decodes them; %d points, %d inside "
              "a district, answer as the tile does" % ("FAIL" if problems else "ok", rel, tiles, feats, pts, answered))
        for m in problems:
            print("          " + m)
        failed += bool(problems)
    if failed:
        fail("%d archive(s) read differently by the app's decoder" % failed)
    print("validate-vector-tiles: OK — %d archive(s)" % len(paths))


if __name__ == "__main__":
    main()
