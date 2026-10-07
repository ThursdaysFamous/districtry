#!/usr/bin/env python3
"""
Build data/source/{jones,tama}-supervisor-districts.geojson — the supervisor
districts of the two Iowa counties whose current lines the statewide layer
does not draw, from files each county's own office sent this project, resolved
to whole Census 2020 blocks.

WHY THESE TWO, AND WHY THEY SHARE A SCRIPT
--------------------------------------------
build_ia_supervisor_districts.py reads the Iowa Legislature's statewide
CountySupervisorDistricts layer (vintage 2024-01-30). Two counties cannot be
answered from it:

  * JONES has no row in it at all, by name or by FIPS 105. The county publishes
    its adopted plan only as a PDF whose map body is raster strips, so nothing
    could be read from it (ia/WATCH.md). Asked on 2026-10-01 for the file the
    map was drawn from (docs/ASK_DRAFTS.md Ask 14), GIS Coordinator Kristi
    Aitchison sent a 2012 shapefile on 2026-10-05, which the population gate
    below refused, and then the 2022 file on 2026-10-06, which it accepts.
  * TAMA has three districts in it. The county moved from three supervisors to
    five at the 2022 general election, and the Legislative Services Agency drew
    the five-district plan on 2024-02-05 — after the layer's vintage. Auditor
    Karen Rohrs sent the county's own district map on 2026-10-01.

Both are files a county official sent by e-mail, neither is published at a URL
this script could re-read, so both are committed under data/source/raw/
(deploy-excluded) and pinned by SHA-256. Both go through the same last step —
every Census 2020 block in the county is assigned to the district covering
most of it, and the shipped polygons are unions of whole blocks — and the same
gate: the block populations must equal a population table that is NOT an input
to the derivation. That shared step and gate are why one script carries both.

JONES: THE COUNTY'S OWN GIS FILE
----------------------------------
`BOS_2022` is a polygon shapefile in NAD83 / Iowa North (US feet): five
districts keyed DIST_ID 1-5, plus one record labelled `Unassigned` with no
shape, which is skipped and reported. Its gate is the county's own published
figures — 4,128 / 4,120 / 4,137 / 4,132 / 4,129, printed on the adopted plan's
own map PDF (bos_districts_final_23073.pdf on jonescountyiowa.gov). The 2012
file the county sent first missed them by -183, +268, -149, -27 and +91, which
is what this gate is for: a plan drawn on 2020 blocks matches its own figures
to the person, and an earlier plan cannot.

TAMA: THE COUNTY'S OWN PRINTED MAP
------------------------------------
The map ("TAMA COUNTY SUPERVISOR DISTRICTS 2024", layer
`County_Tama_Supervisor_Districts2025`) draws each district as a FILLED path in
one of five colours, and its own legend pairs each colour with `District_1` to
`District_5`. That is the Jackson precondition — the districts themselves are
filled path objects — so the read is the path objects, never the pixels.
read_tama_legend() pairs each colour to its legend label by position rather than
trusting a table typed here.

The page is drawn in NAD83 / Iowa North: the drawn county's aspect agrees with
the true county's to 0.006% in EPSG:26975 against 0.27% in UTM 15N and 0.70% in
Web Mercator (measured 2026-10-07). The fit starts from the bounding boxes and
is then refined by an affine least-squares match of the drawn outline to the
county's real one; the residual is printed and ceilinged.

Tama's independent witness is the Legislative Services Agency's own report,
"Tama County Supervisor Redistricting Report - Plan I" (2024-02-05), whose
Attachment 3 gives 3,426 / 3,446 / 3,395 / 3,420 / 3,448. THE MAP DOES NOT
MATCH IT EXACTLY, AND THE DIFFERENCE IS ONE BLOCK, STATED HERE RATHER THAN
ABSORBED. Block 191712905002022 (7 people), in the west half of section 31 of
Tama Township, is a detached piece of District 2 on the county's map, where the
LSA plan's District 2 is precinct 9 alone. The county's 2025 precinct map, sent
by the same Auditor on 2026-10-06, colours that same parcel as part of the Tama
precinct — so two county documents agree that the parcel now votes with Tama,
and the plan as drawn today is Plan I with that block moved from District 5 to
District 2. The gate is therefore Plan I's figures with exactly that move
applied (3,426 / 3,453 / 3,395 / 3,420 / 3,441), and it also requires the block
itself to land in District 2: any OTHER difference fails, and so does this one
going away.

NOTHING TRACED SHIPS
----------------------
For both counties, the source geometry only decides which district each block
belongs to; every shipped vertex is the Census Bureau's. A block whose best
district covers less than MIN_BLOCK_SHARE of it fails the build.

Occasional OPERATOR step, not CI: needs shapely, pyproj, numpy and pymupdf, and
reads Census 2020 blocks from TIGERweb.

Usage:
    python3 ia/scripts/build_county_supplied_supervisor_districts.py
    python3 ia/scripts/build_county_supplied_supervisor_districts.py --check
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
sys.path.insert(0, os.path.join(os.path.dirname(REPO_ROOT), "scripts"))
from scraper_common import UA_HEADERS_ROSTER_BOT, require_robots_once  # noqa: E402

RAW_DIR = os.path.join(REPO_ROOT, "data", "source", "raw")
OUT_DIR = os.path.join(REPO_ROOT, "data", "source")
PLAN_CRS = "EPSG:26975"   # NAD83 / Iowa North, metres; both counties lie in it

BLOCK_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
             "tigerWMS_Census2020/MapServer/10/query")

MIN_BLOCK_SHARE = 0.55        # measured worst: Jones 0.9998, Tama 0.6190
TAMA_FIT_MEDIAN_CEILING_M = 15.0   # measured 6.2
TAMA_FIT_P90_CEILING_M = 40.0      # measured 23.3
COUNTY_IOU_FLOOR = 0.995           # measured Jones 0.99993, Tama 0.99862

COUNTIES = {
    "Jones": {
        "fips": "105",
        "blocks": 1460,
        "population": 20646,
        "files": {
            "jones-bos-2022/BOS_2022.shp":
                "0b5f8488417d39ba075a48633aee99af15772bbe80af44cd06172d42c5152481",
            "jones-bos-2022/BOS_2022.shx":
                "82c3ee8ebc72ad25631aabc35f0b3ee2f0ad7ee6cbf5548cdc52113a436aea80",
            "jones-bos-2022/BOS_2022.dbf":
                "5dfd390939bd8fe8a94cd1804865fa081d1c2f362d99facb4c6fb600879f64ce",
            "jones-bos-2022/BOS_2022.prj":
                "39c42866c3d39a5e23a59dfa5baf29c072509edfb2b274a0080ae8aaa5762752",
        },
        "witness": {"1": 4128, "2": 4120, "3": 4137, "4": 4132, "5": 4129},
        "witness_cite": ("Jones County's own adopted-plan map "
                         "(bos_districts_final_23073.pdf), district populations"),
        "source": "JONES-COUNTY-GIS-BOS-2022",
        "source_url": "https://www.jonescountyiowa.gov/board_of_supervisors/",
        "out": "jones-supervisor-districts.geojson",
    },
    "Tama": {
        "fips": "171",
        "blocks": 1805,
        "population": 17135,
        "files": {
            "tama-supervisor-districts-2025.pdf":
                "8536a4ca00f00eea8148106dcc8aebab791a0b76b389b54c987b44a694491d03",
        },
        "lsa_plan": {"1": 3426, "2": 3446, "3": 3395, "4": 3420, "5": 3448},
        "lsa_doc": "https://www.legis.iowa.gov/docs/publications/CSR/1445661.pdf",
        # The one declared difference from LSA's Plan I; see the docstring.
        "moved": {"geoid": "191712905002022", "people": 7,
                  "from": "5", "to": "2"},
        "source": "TAMA-COUNTY-AUDITOR-MAP-2025",
        "source_url": "https://www.tamacounty.iowa.gov/supervisors/",
        "out": "tama-supervisor-districts.geojson",
    },
}

TAMA_LEGEND = ["District_1", "District_2", "District_3", "District_4",
               "District_5"]
TAMA_MIN_DISTRICT_BOX_PT2 = 5000   # legend swatches are far smaller


def fail(msg):
    raise SystemExit("county-supplied-supervisor-districts: " + msg)


def check_files(county, cfg):
    for rel, want in cfg["files"].items():
        path = os.path.join(RAW_DIR, rel)
        try:
            with open(path, "rb") as f:
                got = hashlib.sha256(f.read()).hexdigest()
        except OSError as e:
            fail("%s: %s is missing (%s)" % (county, rel, e))
        if got != want:
            fail("%s: %s has changed (sha256 %s, pinned %s). A county file is "
                 "replaced only by a person who has re-read it; re-pin by hand."
                 % (county, rel, got, want))


def fetch_blocks(cfg):
    """Every Census 2020 block in the county with POP100, ordered so paging
    is stable, with TIGERweb's HTTP-200 error envelope treated as a failure."""
    hdrs = dict(UA_HEADERS_ROSTER_BOT)
    require_robots_once(BLOCK_URL, hdrs["User-Agent"], headers=hdrs,
                        label="county-supplied-supervisor-districts")
    feats, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "where": "STATE='19' AND COUNTY='%s'" % cfg["fips"],
            "outFields": "GEOID,POP100", "returnGeometry": "true",
            "outSR": "4326", "f": "geojson", "orderByFields": "GEOID",
            "resultOffset": offset, "resultRecordCount": 1000})
        req = urllib.request.Request(BLOCK_URL + "?" + q, headers=hdrs)
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        if "error" in data:
            fail("TIGERweb answered with an error envelope: %r" % data["error"])
        batch = data.get("features") or []
        feats.extend(batch)
        offset += len(batch)
        if len(batch) < 1000:
            break
    total = sum(int(f["properties"].get("POP100") or 0) for f in feats)
    if len(feats) != cfg["blocks"] or total != cfg["population"]:
        fail("TIGERweb returned %d blocks holding %d people, expected %d / %d"
             % (len(feats), total, cfg["blocks"], cfg["population"]))
    return feats


def read_shapefile(stem):
    """A polygon shapefile's records as (attributes, [rings]) in its own CRS.

    Read with struct rather than a GIS library because the format is small and
    fixed and this script should not need one; a record with no shape is
    returned with rings None so the caller can say what it skipped."""
    with open(stem + ".shp", "rb") as f:
        b = f.read()
    shapes, pos = [], 100
    while pos < len(b):
        _num, length = struct.unpack(">ii", b[pos:pos + 8])
        c = b[pos + 8:pos + 8 + length * 2]
        pos += 8 + length * 2
        stype = struct.unpack("<i", c[:4])[0]
        if stype == 0:
            shapes.append(None)
            continue
        if stype != 5:
            fail("%s: shape type %d, expected 5 (polygon)" % (stem, stype))
        nparts, npts = struct.unpack("<ii", c[36:44])
        parts = list(struct.unpack("<%di" % nparts, c[44:44 + 4 * nparts])) + [npts]
        o = 44 + 4 * nparts
        pts = [struct.unpack("<dd", c[o + 16 * i:o + 16 * i + 16])
               for i in range(npts)]
        shapes.append([pts[parts[i]:parts[i + 1]] for i in range(nparts)])
    with open(stem + ".dbf", "rb") as f:
        d = f.read()
    n, header_len, rec_len = struct.unpack("<IHH", d[4:12])
    fields, p = [], 32
    while d[p] != 0x0D:
        fields.append((d[p:p + 11].split(b"\0")[0].decode(), d[p + 16]))
        p += 32
    recs = []
    for i in range(n):
        r = d[header_len + i * rec_len + 1:header_len + (i + 1) * rec_len]
        o, rec = 0, {}
        for name, width in fields:
            rec[name] = r[o:o + width].decode("latin1").strip()
            o += width
        recs.append(rec)
    if len(recs) != len(shapes):
        fail("%s: %d attribute rows against %d shapes" % (stem, len(recs), len(shapes)))
    return list(zip(recs, shapes))


def jones_districts(geo):
    Polygon, transform, Transformer, CRS = (geo["Polygon"], geo["transform"],
                                            geo["Transformer"], geo["CRS"])
    stem = os.path.join(RAW_DIR, "jones-bos-2022", "BOS_2022")
    with open(stem + ".prj") as f:
        src = CRS.from_wkt(f.read())
    to_plan = Transformer.from_crs(src, PLAN_CRS, always_xy=True)
    out = {}
    for rec, rings in read_shapefile(stem):
        if not rings:
            print("Jones: skipped the shapefile's empty record %r" % rec,
                  file=sys.stderr)
            continue
        key = str(int(rec["DIST_ID"]))
        g = None
        for ring in rings:        # even-odd: a hole is a hole whatever its winding
            pr = Polygon(ring).buffer(0)
            g = pr if g is None else g.symmetric_difference(pr)
        if key in out:
            fail("Jones: DIST_ID %s appears twice" % key)
        out[key] = transform(lambda x, y, z=None: to_plan.transform(x, y), g).buffer(0)
    return out


def tama_districts(geo):
    """The five filled districts, each colour paired to its legend label."""
    import pymupdf
    Polygon, Point = geo["Polygon"], geo["Point"]
    page = pymupdf.open(os.path.join(RAW_DIR, "tama-supervisor-districts-2025.pdf"))[0]
    labels = {}
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            for span in line["spans"]:
                t = span["text"].strip()
                if t in TAMA_LEGEND:
                    labels[t] = span["bbox"]
    if sorted(labels) != TAMA_LEGEND:
        fail("Tama: the legend carries %s, expected %s" % (sorted(labels), TAMA_LEGEND))

    big, swatches = {}, {}
    for d in page.get_drawings():
        fill = d.get("fill")
        if not fill:
            continue
        k = tuple(round(c, 3) for c in fill)
        if d["rect"].get_area() > TAMA_MIN_DISTRICT_BOX_PT2:
            big.setdefault(k, []).append(d)
        else:
            swatches.setdefault(k, []).append(d["rect"])

    # Pair each district colour to the legend label beside its swatch: the
    # swatch sits to the label's left, and the one whose centre is nearest the
    # label's centre vertically is its own. Nearest, not "within a line": the
    # legend rows are 13 pt apart and a text span's box is 19 pt tall, so a
    # within-a-line test accepts the next row's swatch too.
    colour_of = {}
    for label, (x0, y0, x1, y1) in labels.items():
        cy = (y0 + y1) / 2
        best = None
        for k, rects in swatches.items():
            if k not in big:
                continue
            for r in rects:
                if r.x1 <= x0 + 1 and 0 <= x0 - r.x1 < 10:
                    dy = abs((r.y0 + r.y1) / 2 - cy)
                    if best is None or dy < best[0]:
                        best = (dy, k)
        if best is None or best[0] > 4:
            fail("Tama: no district-coloured swatch level with legend label %s "
                 "(nearest %s pt off)" % (label, best and round(best[0], 1)))
        colour_of[label] = best[1]
    if len(set(colour_of.values())) != len(TAMA_LEGEND):
        fail("Tama: two legend labels share a colour: %s" % colour_of)

    out = {}
    for label, k in colour_of.items():
        rings = []
        for d in big[k]:
            cur = []
            for it in d["items"]:
                if it[0] in ("l", "c"):
                    a = (it[1].x, it[1].y)
                    b = (it[2].x, it[2].y) if it[0] == "l" else (it[4].x, it[4].y)
                    if not cur or abs(cur[-1][0] - a[0]) > 1e-6 or abs(cur[-1][1] - a[1]) > 1e-6:
                        if len(cur) >= 4:
                            rings.append(cur)
                        cur = [a]
                    cur.append(b)
                elif it[0] == "re":
                    r = it[1]
                    rings.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
            if len(cur) >= 4:
                rings.append(cur)
        g = None
        for ring in rings:
            pg = Polygon(ring).buffer(0)
            if pg.is_empty:
                continue
            g = pg if g is None else g.symmetric_difference(pg)
        out[label.split("_")[1]] = g
    print("Tama: legend pairs %s" % {lbl: c for lbl, c in sorted(colour_of.items())},
          file=sys.stderr)
    return out


def fit_tama(drawn, county, geo):
    """Bounding-box start, then affine least squares against the real outline.

    The drawn union's exterior runs into the slits left between districts that
    do not quite share an edge, so it is closed by a 1 pt buffer first; the
    worst tenth of matches is excluded each round so a slit or a road shield
    cannot steer the fit."""
    import numpy as np
    Point, nearest_points, transform = geo["Point"], geo["nearest_points"], geo["transform"]
    u = geo["unary_union"](list(drawn.values())).buffer(1).buffer(-1)
    db, cb = u.bounds, county.bounds
    a_drawn = (db[2] - db[0]) / (db[3] - db[1])
    a_true = (cb[2] - cb[0]) / (cb[3] - cb[1])
    if abs(a_drawn / a_true - 1) > 0.005:
        fail("Tama: the drawn county's aspect is %.5f against %.5f in %s"
             % (a_drawn, a_true, PLAN_CRS))
    sx = (cb[2] - cb[0]) / (db[2] - db[0])
    sy = (cb[3] - cb[1]) / (db[3] - db[1])
    A = np.array([[sx, 0, cb[0] - db[0] * sx], [0, -sy, cb[3] + db[1] * sy]])
    ext, n = u.exterior, 4000
    src = np.array([ext.interpolate(i * ext.length / n).coords[0] for i in range(n)])
    edge = county.exterior
    for _ in range(15):
        q = src @ A[:, :2].T + A[:, 2]
        tgt = np.array([nearest_points(edge, Point(x, y))[0].coords[0] for x, y in q])
        dist = np.hypot(*(q - tgt).T)
        keep = dist < np.percentile(dist, 90)
        sol, *_ = np.linalg.lstsq(np.c_[src[keep], np.ones(keep.sum())], tgt[keep], rcond=None)
        A = sol.T
    med, p90 = float(np.median(dist)), float(np.percentile(dist, 90))
    if med > TAMA_FIT_MEDIAN_CEILING_M or p90 > TAMA_FIT_P90_CEILING_M:
        fail("Tama: the fitted outline sits a median %.1f m / p90 %.1f m from the "
             "county's own (ceilings %.0f / %.0f)" % (med, p90,
                                                     TAMA_FIT_MEDIAN_CEILING_M,
                                                     TAMA_FIT_P90_CEILING_M))
    print("Tama: georeference %s, aspect %.5f vs %.5f, affine fit residual median "
          "%.1f m / p90 %.1f m" % (PLAN_CRS, a_drawn, a_true, med, p90), file=sys.stderr)
    place = lambda x, y, z=None: (A[0, 0] * x + A[0, 1] * y + A[0, 2],  # noqa: E731
                                  A[1, 0] * x + A[1, 1] * y + A[1, 2])
    return {k: transform(place, v).buffer(0) for k, v in drawn.items()}


def resolve(county, cfg, dist, blocks, geo):
    shape, transform, unary_union = geo["shape"], geo["transform"], geo["unary_union"]
    fwd = geo["fwd"]
    plan_blocks = [(f, transform(fwd, shape(f["geometry"])).buffer(0)) for f in blocks]
    whole = unary_union([g for _, g in plan_blocks])
    drawn = unary_union(list(dist.values()))
    iou = drawn.intersection(whole).area / drawn.union(whole).area
    if iou < COUNTY_IOU_FLOOR:
        fail("%s: the source districts cover the county at IoU %.5f (floor %.3f)"
             % (county, iou, COUNTY_IOU_FLOOR))
    ks = sorted(dist)
    groups = {k: [] for k in ks}
    pops = {k: 0 for k in ks}
    where, worst, marginal = {}, 1.0, 0
    for f, g in plan_blocks:
        if g.is_empty or g.area == 0:
            continue
        share = {k: g.intersection(dist[k]).area / g.area for k in ks}
        best = max(share, key=share.get)
        worst = min(worst, share[best])
        marginal += share[best] < 0.99
        pop = int(f["properties"].get("POP100") or 0)
        groups[best].append(shape(f["geometry"]).buffer(0))
        pops[best] += pop
        where[f["properties"]["GEOID"]] = best
    if worst < MIN_BLOCK_SHARE:
        fail("%s: a block sits only %.1f%% inside its best district (floor %.0f%%)"
             % (county, 100 * worst, 100 * MIN_BLOCK_SHARE))
    print("%s: source covers the county at IoU %.5f; %d blocks sorted, worst "
          "nesting %.2f%%, %d under 99%%" % (county, iou, len(plan_blocks),
                                             100 * worst, marginal), file=sys.stderr)
    return {k: unary_union(groups[k]).buffer(0) for k in ks}, pops, where


def gate(county, cfg, pops, where):
    if county == "Jones":
        if pops != cfg["witness"]:
            fail("Jones: the block populations are %s and the county's own "
                 "adopted plan publishes %s. A plan drawn on 2020 blocks matches "
                 "its own figures to the person; a disagreement means this is "
                 "not the plan in force." % (pops, cfg["witness"]))
        print("Jones POPULATION GATE: %s equals %s exactly"
              % (dict(sorted(pops.items())), cfg["witness_cite"]), file=sys.stderr)
        return
    mv = cfg["moved"]
    want = dict(cfg["lsa_plan"])
    want[mv["from"]] -= mv["people"]
    want[mv["to"]] += mv["people"]
    if where.get(mv["geoid"]) != mv["to"]:
        fail("Tama: block %s lands in district %r, and the one declared "
             "difference from LSA's Plan I puts it in %s. If the county's map no "
             "longer moves it, the declaration is stale and must go."
             % (mv["geoid"], where.get(mv["geoid"]), mv["to"]))
    if pops == cfg["lsa_plan"]:
        fail("Tama: the derivation now equals LSA's Plan I exactly, so the "
             "declared move is stale and must go")
    if pops != want:
        fail("Tama: the block populations are %s; LSA's Plan I is %s, and with "
             "the one declared move (block %s, %d people, district %s to %s) it "
             "is %s. Any other difference means the lines, the labels or the "
             "fit are wrong." % (pops, cfg["lsa_plan"], mv["geoid"], mv["people"],
                                 mv["from"], mv["to"], want))
    print("Tama POPULATION GATE: %s equals LSA's Plan I (%s) with exactly one "
          "declared move, block %s (%d people) from district %s to %s"
          % (dict(sorted(pops.items())), cfg["lsa_doc"], mv["geoid"],
             mv["people"], mv["from"], mv["to"]), file=sys.stderr)


def rnd(o, p=6):
    """Round every coordinate to p decimals. The tuple branch matters: shapely's
    mapping() returns tuples, and a list-only version rounds nothing."""
    if isinstance(o, float):
        return round(o, p)
    if isinstance(o, (list, tuple)):
        return [rnd(x, p) for x in o]
    if isinstance(o, dict):
        return {k: rnd(v, p) for k, v in o.items()}
    return o


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="re-derive and compare against the committed files")
    ap.add_argument("--county", choices=sorted(COUNTIES))
    args = ap.parse_args()

    from shapely.geometry import Polygon, Point, shape, mapping
    from shapely.ops import unary_union, transform, nearest_points
    from pyproj import Transformer, CRS
    to_plan = Transformer.from_crs("EPSG:4326", PLAN_CRS, always_xy=True)
    geo = {"Polygon": Polygon, "Point": Point, "shape": shape,
           "unary_union": unary_union, "transform": transform,
           "nearest_points": nearest_points, "Transformer": Transformer,
           "CRS": CRS, "fwd": lambda x, y, z=None: to_plan.transform(x, y)}

    for county in ([args.county] if args.county else sorted(COUNTIES)):
        cfg = COUNTIES[county]
        check_files(county, cfg)
        blocks = fetch_blocks(cfg)
        if county == "Jones":
            dist = jones_districts(geo)
        else:
            county_shape = unary_union([transform(geo["fwd"], shape(f["geometry"])).buffer(0)
                                        for f in blocks])
            dist = fit_tama(tama_districts(geo), county_shape, geo)
        if sorted(dist) != ["1", "2", "3", "4", "5"]:
            fail("%s: districts %s, expected 1-5" % (county, sorted(dist)))
        shipped, pops, where = resolve(county, cfg, dist, blocks, geo)
        gate(county, cfg, pops, where)

        fc = {"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "properties": {"DISTRICT": k, "POPULATION": pops[k],
                            "SOURCE": cfg["source"], "SOURCE_URL": cfg["source_url"]},
             "geometry": rnd(mapping(shipped[k]))} for k in sorted(shipped)]}
        payload = json.dumps(fc, indent=1, sort_keys=True) + "\n"
        out_path = os.path.join(OUT_DIR, cfg["out"])
        if args.check:
            try:
                with open(out_path) as f:
                    have = f.read()
            except OSError as e:
                fail("%s is missing (%s)" % (cfg["out"], e))
            if have != payload:
                fail("data/source/%s has drifted from a fresh derivation; re-run "
                     "this script without --check" % cfg["out"])
            print("%s check: the committed districts match a fresh derivation"
                  % county, file=sys.stderr)
            continue
        with open(out_path, "w") as f:
            f.write(payload)
        print("wrote data/source/%s" % cfg["out"], file=sys.stderr)


if __name__ == "__main__":
    main()
