#!/usr/bin/env python3
"""
Build data/app/stephenson-county-board-districts.json — the fleet's only
GEOREFERENCED boundary, and the only one whose accuracy is a measured number
rather than an exact match to a published file.

READ THIS BEFORE TRUSTING THE OUTPUT.

Stephenson's eight board districts are lettered B-I. Four of them (F, G, H, I)
are whole townships and would build like Livingston's. The other four (B, C, D,
E) subdivide FREEPORT township — 53% of the county — along the county's CURRENT
precinct lines, and nothing publishes those:

  * Census 2020 publishes FREEPORT 1-18. The county re-precincted after the
    census and now runs Freeport 01-16, which is what B-E are drawn from. A
    different division of the same township, so census voting districts cannot
    draw these lines.
  * Stephenson runs no GIS server and has no ArcGIS Online presence beyond
    third-party research layers. Its assessment office points at WinGIS, which
    serves the county an address locator and no boundary layers. The Illinois
    SBE's GIS viewer is down.

What the county DOES publish is the adopted map itself — and it is a VECTOR PDF,
not a scan. Its 16 precinct polygons are real paths with real fills, and its
legend maps fill colour to district. So this script georeferences that map:

  1. Read the 16 precinct polygons and their fill colours out of the PDF.
  2. Dissolve them (edge cancellation) into their union outline. The polygons
     share exact vertices, so 710 of 2507 edges cancel — this is a clean
     topological dissolve, not a tolerance match.
  3. Fit an AFFINE transform from PDF page space to WGS84 by trimmed ICP against
     the TIGER county-subdivision polygon for Freeport, which is the same
     geographic area that union covers.
  4. Apply it, dissolve per district, and emit B-E. F-I come from TIGER
     townships directly and are exact.

MEASURED ACCURACY (regenerated on every run; the build fails if it degrades):
  * Control fit — PDF union outline vs TIGER Freeport subdivision:
    median 1.6 m, RMS 10.9 m over the 80% of vertices that have a counterpart
    (the rest are interior enclaves the TIGER outline does not carry).
  * INDEPENDENT check — the map's HYDROGRAPHY layer, which the fit never saw,
    against TIGER hydrography: 98.9% of vertices within 50 m, median 15.7 m.
    This is the number that matters. The transform was fitted on one feature
    class and lands a different one within ~16 m.

So a Freeport district line here is good to roughly 15-20 m — a fraction of a
city block. That is honest for civic exploration and is surfaced ON THE CARD
rather than buried here: the app labels these four districts as derived from the
county's published map, because a reader deserves to know this boundary was
measured off a PDF rather than published as data.

THIS IS A RARE OPERATOR STEP, like build_embedded_boundaries.py — it needs
pymupdf and numpy, which the weekly workflows do not have, and the source PDFs
are archived in data/source/raw/. Re-run it when Stephenson reapportions (next
due after the 2030 census) or if the county ever publishes real precinct
geometry, at which point this script should be DELETED rather than maintained.

Usage:
    python3 scripts/build_stephenson_board_districts.py
    python3 scripts/build_stephenson_board_districts.py --check
"""

import argparse
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    HEADERS, REQUEST_TIMEOUT, SIMPLIFY_TOLERANCE_M, STATE_FIPS, dissolve,
    group_rings, point_in_rings, simplify,
)
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    make_fail,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "stephenson-county-board-districts.json")
RAW_DIR = os.path.join(REPO_ROOT, "il", "data", "source", "raw")
FREEPORT_PDF = os.path.join(RAW_DIR, "Stephenson COUNTY BOARD FREEPORT TOWNSHIP DISTRICTS 010622.pdf")

COUNTY_FIPS = "177"
SOURCE_LABEL = ("Stephenson County adopted district maps, 2022-01-06 "
                "(COUNTY BOARD FREEPORT TOWNSHIP DISTRICTS / COUNTY BOARD RURAL DISTRICTS)")
SOURCE_URL = "https://stephensoncountyil.gov/government/county_board/district_maps_2012.php"

TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query")
TIGER_HYDRO = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
               "Hydro/MapServer/%d/query")

# The rural half, read off COUNTY BOARD RURAL DISTRICTS and confirmed by
# arithmetic: each district's township populations sum EXACTLY to the total the
# map prints for it. Those printed totals are carried here so the check is
# reproducible rather than a claim.
RURAL = {
    "F": (["Winslow", "West Point", "Waddams", "Kent", "Jefferson"], 5398),
    "G": (["Oneco", "Buckeye", "Dakota", "Lancaster", "Silver Creek"], 5356),
    "H": (["Rock Grove", "Rock Run", "Ridott"], 5037),
    "I": (["Erin", "Harlem", "Loran", "Florence"], 5195),
}
# 2020 census population of each rural township, printed on the same map.
TOWNSHIP_POP = {
    "Winslow": 574, "West Point": 3211, "Waddams": 739, "Kent": 622, "Jefferson": 252,
    "Oneco": 1287, "Buckeye": 1195, "Dakota": 811, "Lancaster": 1402, "Silver Creek": 661,
    "Rock Grove": 1451, "Rock Run": 2234, "Ridott": 1352,
    "Erin": 384, "Harlem": 2220, "Loran": 1362, "Florence": 1229,
}
# The Freeport half, read off the vector PDF: legend fill colour -> district.
# Verified two ways before being written down — by eye, and by machine from the
# polygons' own fills — and the two agreed, four precincts per district.
FREEPORT_FILLS = {
    (0.729, 0.753, 0.961): "B",
    (0.98, 0.914, 0.773): "C",
    (0.925, 0.98, 0.784): "D",
    (0.824, 0.988, 0.949): "E",
}
FREEPORT_PRECINCTS = {
    "B": ["01", "02", "03", "06"], "C": ["04", "05", "07", "10"],
    "D": ["08", "09", "13", "14"], "E": ["11", "12", "15", "16"],
}
HYDRO_COLOURS = {(0.251, 0.396, 0.922), (0.592, 0.859, 0.949)}

# Accuracy floors. Regenerating must not make the map worse than it was measured
# to be when it shipped; a large miss means the PDF changed or the fit diverged.
MAX_CONTROL_RMS_M = 20.0
MAX_CONTROL_MEDIAN_M = 6.0
MIN_HYDRO_WITHIN_50M = 0.95
MAX_HYDRO_MEDIAN_M = 30.0

# Simplification, and why the two halves differ. F-I are exact township edges, so
# the fleet's standard 25 m is their whole error budget. B-E already carry the
# georeference's ~16 m, so they get a tighter 10 m rather than stacking a second
# 25 m on top — total error there stays in the same ballpark as an ordinary
# simplified boundary instead of doubling it.
DERIVED_TOLERANCE_M = 10

# Points that must land in the district the county's maps put them in. Every
# rural anchor was DERIVED, not recalled: the town was geocoded, its containing
# township read back from TIGER, and the district then looked up in RURAL above.
# (The first draft of this list was written from memory and put Rock City and
# Lena in the wrong townships — which is exactly why anchors are derived now.)
#
# The four Freeport anchors are the map's OWN "DISTRICT x" label positions, run
# through the same transform. They do not test the transform's accuracy — nothing
# on this map can, which is what the hydrography check is for — but they do test
# that the fill-colour reading agrees with where the county printed each district
# name, and that the dissolve preserved containment end to end.
ANCHORS = [
    (42.4927, -89.7918, "F", "Winslow (Winslow Twp)"),
    (42.3805, -89.8221, "F", "Lena (West Point Twp)"),
    (42.4680, -89.6449, "G", "Orangeville (Oneco Twp)"),
    (42.3888, -89.5264, "G", "Dakota (Dakota Twp)"),
    (42.3760, -89.6332, "G", "Cedarville (Buckeye Twp)"),
    (42.4133, -89.4686, "H", "Rock City (Rock Run Twp)"),
    (42.4225, -89.4137, "H", "Davis (Rock Run Twp)"),
    (42.2964, -89.4754, "H", "Ridott (Ridott Twp)"),
    (42.2156, -89.4734, "H", "German Valley (Ridott Twp)"),
    (42.2653, -89.8260, "I", "Pearl City (Loran Twp)"),
    (42.2953, -89.6011, "B", "the map's own DISTRICT B label"),
    (42.2880, -89.6284, "C", "the map's own DISTRICT C label"),
    (42.2827, -89.6549, "D", "the map's own DISTRICT D label"),
    (42.2999, -89.6693, "E", "the map's own DISTRICT E label"),
]


fail = make_fail("stephenson-board")


def need(mod):
    try:
        return __import__(mod)
    except ImportError:
        fail("this is an operator step and needs %s (pip install pymupdf numpy); "
             "the shipped data/app file is what CI validates" % mod)


def fetch_geojson(url, params):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-stephenson-board-districts")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, params=params)
    resp.raise_for_status()
    return (resp.json() or {}).get("features") or []


def rings_of_path(path):
    """Ordered vertex rings from a pymupdf drawing; a new ring starts wherever
    an item does not continue from the previous point."""
    rings, cur = [], []
    for it in path["items"]:
        if it[0] == "l":
            a, b = (it[1].x, it[1].y), (it[2].x, it[2].y)
        elif it[0] == "c":
            a, b = (it[1].x, it[1].y), (it[4].x, it[4].y)
        elif it[0] == "re":
            r = it[1]
            rings.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
            cur = []
            continue
        else:
            continue
        if cur and (abs(cur[-1][0] - a[0]) > 1e-6 or abs(cur[-1][1] - a[1]) > 1e-6):
            if len(cur) >= 3:
                rings.append(cur)
            cur = [a, b]
        elif not cur:
            cur = [a, b]
        else:
            cur.append(b)
    if len(cur) >= 3:
        rings.append(cur)
    return rings


def ring_edges(rings, q=6):
    counts = collections.Counter()
    for r in rings:
        n = len(r)
        for i in range(n):
            a = (round(r[i][0], q), round(r[i][1], q))
            b = (round(r[(i + 1) % n][0], q), round(r[(i + 1) % n][1], q))
            if a != b:
                counts[(a, b) if a < b else (b, a)] += 1
    return counts


def as_features(rings, q=6):
    """Wrap raw PDF rings as GeoJSON-ish features so build_metro_outline's own
    dissolve() can chain them. Hand-rolling that walk here produced a district B
    polygon that swallowed district D — the shared implementation closes each
    ring back to its start instead of stopping at the first dead end, which is
    exactly the case that went wrong."""
    out = []
    for r in rings:
        ring = [[round(p[0], q), round(p[1], q)] for p in r]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        out.append({"geometry": {"type": "Polygon", "coordinates": [ring]}})
    return out


def pt_seg_factory(np):
    """Point-to-segment distances, chunked. Shared by this build and the
    special-district builds (build_stephenson_fire_districts.py), which
    georeference SIBLING maps from the same county map series."""
    def pt_seg(Q, S, chunk=300):
        a, b = S[:, 0], S[:, 1]
        ab = b - a
        L2 = (ab ** 2).sum(1)
        L2[L2 == 0] = 1e-18
        dist = np.empty(len(Q))
        near = np.empty((len(Q), 2))
        for i in range(0, len(Q), chunk):
            q = Q[i:i + chunk][:, None, :]
            tt = (((q - a[None]) * ab[None]).sum(-1) / L2[None]).clip(0, 1)
            proj = a[None] + tt[..., None] * ab[None]
            dd = np.sqrt(((q - proj) ** 2).sum(-1))
            j = dd.argmin(1)
            dist[i:i + chunk] = dd[np.arange(len(j)), j]
            near[i:i + chunk] = proj[np.arange(len(j)), j]
        return dist, near
    return pt_seg


def fit_affine_icp(np, P, tparts, kx, on_fail):
    """Trimmed-ICP affine fit from PDF page space to (kx-scaled) lon/lat,
    exactly the schedule the board build shipped with. `tparts` is the target
    polygon's MultiPolygon-style coordinate list; returns (A, t, pt_seg, ctrl)."""
    pt_seg = pt_seg_factory(np)
    T = np.array([c[:2] for p in tparts for r in p for c in r], float)
    ctrl = np.concatenate([
        np.stack([np.array([(c[0] * kx, c[1]) for c in r])[:-1],
                  np.array([(c[0] * kx, c[1]) for c in r])[1:]], 1)
        for p in tparts for r in p if len(r) > 1])
    Tm = np.column_stack([T[:, 0] * kx, T[:, 1]])
    sx = (Tm[:, 0].max() - Tm[:, 0].min()) / (P[:, 0].max() - P[:, 0].min())
    sy = (Tm[:, 1].max() - Tm[:, 1].min()) / (P[:, 1].max() - P[:, 1].min())
    A = np.array([[sx, 0.0], [0.0, -sy]])
    t = np.array([Tm[:, 0].min() - sx * P[:, 0].min(), Tm[:, 1].max() + sy * P[:, 1].min()])
    # Trimmed ICP: the cutoff tightens so interior enclaves - real features the
    # target outline does not carry - stop dragging the fit.
    for cut in [float("inf")] * 10 + [600 / 111320] * 10 + [250 / 111320] * 10 + [120 / 111320] * 30:
        d, near = pt_seg(P @ A.T + t, ctrl)
        keep = d <= cut
        if keep.sum() < 200:
            on_fail("georeference lost its correspondences — the map or the target "
                    "polygon changed shape")
        M = np.column_stack([P[keep], np.ones(int(keep.sum()))])
        sol, *_ = np.linalg.lstsq(M, near[keep], rcond=None)
        A, t = sol[:2].T, sol[2]
    return A, t, pt_seg, ctrl


def hydro_check(np, requests_mod, pt_seg, hydro_pts, A, t, kx, on_fail,
                min_within=MIN_HYDRO_WITHIN_50M, max_median=MAX_HYDRO_MEDIAN_M):
    """The INDEPENDENT accuracy check: the map's hydrography, which the fit
    never saw, against TIGER hydrography. Returns (within50_frac, median_m)."""
    H = np.unique(np.array(hydro_pts, float), axis=0) @ A.T + t
    lo, hi = H[:, 0].min() / kx, H[:, 0].max() / kx
    env = "%.5f,%.5f,%.5f,%.5f" % (lo - 0.02, H[:, 1].min() - 0.02, hi + 0.02, H[:, 1].max() + 0.02)
    hsegs = []
    for lyr in (0, 1):
        resp = requests_mod.get(TIGER_HYDRO % lyr, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
            "geometry": env, "geometryType": "esriGeometryEnvelope", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects", "outFields": "NAME",
            "outSR": "4326", "f": "geojson", "returnGeometry": "true"})
        resp.raise_for_status()
        for f in (resp.json() or {}).get("features") or []:
            g = f.get("geometry") or {}
            if g.get("type") in ("Polygon", "MultiPolygon"):
                rr = [r for p in (g["coordinates"] if g["type"] == "MultiPolygon"
                                  else [g["coordinates"]]) for r in p]
            elif g.get("type") in ("LineString", "MultiLineString"):
                rr = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
            else:
                continue
            for r in rr:
                a = np.array([(c[0] * kx, c[1]) for c in r])
                if len(a) > 1:
                    hsegs.append(np.stack([a[:-1], a[1:]], 1))
    if not hsegs:
        on_fail("TIGER returned no hydrography to validate the georeference against")
    hd, _ = pt_seg(H, np.concatenate(hsegs))
    hm = hd * 111320
    within = float((hm < 50).mean())
    median = float(np.median(hm[hm < 100]))
    if within < min_within or median > max_median:
        on_fail("independent hydrography check failed: %.1f%% within 50 m (min %.0f%%), "
                "median %.1f m (max %.1f) — the georeference is not good enough to ship"
                % (100 * within, 100 * min_within, median, max_median))
    return within, median


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()
    pymupdf = need("pymupdf")
    np = need("numpy")

    if not os.path.exists(FREEPORT_PDF):
        fail("archived source map missing: %s" % os.path.relpath(FREEPORT_PDF, REPO_ROOT))

    # ---- rural half: whole townships straight from TIGER -------------------
    feats = fetch_geojson(TIGER_COUSUB, {
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "BASENAME", "returnGeometry": "true", "outSR": "4326", "f": "geojson"})
    townships = {(f["properties"].get("BASENAME") or "").strip(): f for f in feats}
    claimed = [n for names, _ in RURAL.values() for n in names]
    missing = sorted(n for n in claimed if n not in townships)
    if missing:
        fail("township(s) named by the rural map are not in TIGER: %s" % ", ".join(missing))
    if len(claimed) != len(set(claimed)):
        fail("a township is listed in more than one rural district")
    unassigned = sorted(set(townships) - set(claimed) - {"Freeport"})
    if unassigned:
        fail("TIGER township(s) in no district and not Freeport: %s — the county's "
             "composition is incomplete or has changed" % ", ".join(unassigned))
    for code, (names, printed) in sorted(RURAL.items()):
        total = sum(TOWNSHIP_POP[n] for n in names)
        if total != printed:
            fail("district %s townships sum to %d, but its own map prints %d — the "
                 "composition read off that map is wrong" % (code, total, printed))

    # ---- Freeport half: georeference the adopted map -----------------------
    page = pymupdf.open(FREEPORT_PDF)[0]
    per_district, hydro_pts = collections.defaultdict(list), []
    for p in page.get_drawings():
        fill = p.get("fill")
        stroke = p.get("color")
        if fill is not None and tuple(round(c, 3) for c in fill) in FREEPORT_FILLS:
            rs = rings_of_path(p)
            if sum(len(r) for r in rs) > 8:                      # skip legend swatches
                per_district[FREEPORT_FILLS[tuple(round(c, 3) for c in fill)]] += rs
        for col in (fill, stroke):
            if col is not None and tuple(round(c, 3) for c in col) in HYDRO_COLOURS:
                for it in p["items"]:
                    if it[0] == "l":
                        hydro_pts += [(it[1].x, it[1].y), (it[2].x, it[2].y)]
                    elif it[0] == "c":
                        hydro_pts += [(it[1].x, it[1].y), (it[4].x, it[4].y)]
                break
    if sorted(per_district) != ["B", "C", "D", "E"]:
        fail("expected four district fills in the Freeport map, found %s" % sorted(per_district))
    counts = {d: len(v) for d, v in per_district.items()}
    if any(counts[d] < len(FREEPORT_PRECINCTS[d]) for d in counts):
        fail("fewer polygons than precincts in some district: %s" % counts)

    all_rings = [r for v in per_district.values() for r in v]
    shared = sum(1 for v in ring_edges(all_rings).values() if v > 1)
    if shared < 200:
        fail("only %d shared edges cancelled between the precinct polygons — they no "
             "longer share exact vertices, so the union outline is not trustworthy" % shared)
    P = np.array(sorted({tuple(pt) for ring in dissolve(as_features(all_rings)) for pt in ring}),
                 float)

    tf = townships.get("Freeport")
    if tf is None:
        fail("TIGER has no Freeport county subdivision to georeference against")
    tg = tf["geometry"]
    tparts = tg["coordinates"] if tg["type"] == "MultiPolygon" else [tg["coordinates"]]
    T = np.array([c[:2] for p in tparts for r in p for c in r], float)
    lat0 = float(T[:, 1].mean())
    kx = math.cos(math.radians(lat0))
    A, t, pt_seg, ctrl = fit_affine_icp(np, P, tparts, kx, fail)

    d, _ = pt_seg(P @ A.T + t, ctrl)
    matched = d[d < 120 / 111320] * 111320
    ctrl_median, ctrl_rms = float(np.median(matched)), float((matched ** 2).mean() ** 0.5)
    if ctrl_median > MAX_CONTROL_MEDIAN_M or ctrl_rms > MAX_CONTROL_RMS_M:
        fail("control fit degraded: median %.1f m (max %.1f), RMS %.1f m (max %.1f)"
             % (ctrl_median, MAX_CONTROL_MEDIAN_M, ctrl_rms, MAX_CONTROL_RMS_M))

    # INDEPENDENT check: hydrography, a feature class the fit never touched.
    hydro_within, hydro_median = hydro_check(np, requests, pt_seg, hydro_pts, A, t, kx, fail)

    def to_lonlat(pt):
        q = np.array(pt, float) @ A.T + t
        return [round(float(q[0] / kx), 6), round(float(q[1]), 6)]

    features = []
    for code in ("B", "C", "D", "E"):
        # dissolve in PDF space, where the polygons share exact vertices, then
        # transform — the other order would compare rounded lon/lat and lose the
        # edge cancellation entirely
        polys = group_rings(dissolve(as_features(per_district[code])))
        polys = [[simplify([to_lonlat(p) for p in ring], DERIVED_TOLERANCE_M) for ring in poly]
                 for poly in polys]
        polys = [[r if r[0] == r[-1] else r + [r[0]] for r in poly if len(r) >= 4] for poly in polys]
        polys = [p for p in polys if p]
        features.append({
            "type": "Feature",
            "properties": {"district": code, "precincts": FREEPORT_PRECINCTS[code],
                           "derivedFrom": "georeferenced county map", "source": SOURCE_LABEL},
            "geometry": ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                         else {"type": "MultiPolygon", "coordinates": polys}),
        })
    for code in ("F", "G", "H", "I"):
        names = RURAL[code][0]
        polys = group_rings([simplify(r, SIMPLIFY_TOLERANCE_M)
                             for r in dissolve([townships[n] for n in names])])
        polys = [[r if r[0] == r[-1] else r + [r[0]] for r in poly if len(r) >= 4] for poly in polys]
        polys = [p for p in polys if p]
        features.append({
            "type": "Feature",
            "properties": {"district": code, "townships": sorted(names),
                           "derivedFrom": "whole townships", "source": SOURCE_LABEL},
            "geometry": ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                         else {"type": "MultiPolygon", "coordinates": polys}),
        })

    def rings_of_feature(feature):
        g = feature["geometry"]
        return (g["coordinates"] if g["type"] == "Polygon"
                else [r for poly in g["coordinates"] for r in poly])

    for lat, lng, want, label in ANCHORS:
        hit = [f["properties"]["district"] for f in features
               if point_in_rings(lat, lng, rings_of_feature(f))]
        if hit != [want]:
            fail("%s should be district %s, got %s" % (label, want, hit or "no district"))

    payload = {"type": "FeatureCollection", "features": features}
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    summary = ("8 districts (B-E georeferenced, F-I whole townships) — control fit "
               "median %.1f m / RMS %.1f m, independent hydrography check %.1f%% "
               "within 50 m / median %.1f m, %d anchors hold"
               % (ctrl_median, ctrl_rms, 100 * hydro_within, hydro_median, len(ANCHORS)))
    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("data/app/stephenson-county-board-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes). NOTE: a "
                 "georeference is an iterative fit, so a byte difference can be "
                 "numerical rather than real — compare the accuracy numbers above "
                 "before assuming the map changed." % (len(shipped), len(text)))
        print("stephenson-board: OK — matches a fresh build; %s" % summary)
        return
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("stephenson-board: wrote %s — %s, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), summary, len(text)))


if __name__ == "__main__":
    main()
