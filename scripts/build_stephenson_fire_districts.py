#!/usr/bin/env python3
"""
Build data/app/stephenson-fire-districts.json by georeferencing the county's
own COUNTY FIRE DISTRICT MAP (070814) — the same map series, machinery and
honesty posture as build_stephenson_board_districts.py, which documents the
route in full. Read that header first.

WHY THIS MAP — Stephenson runs no GIS and publishes no fire boundary as
data; the 2014 county-produced map preserved on the Illinois SBE's static
precinctmaps mirror is the newest thing the county publishes, and its
fire-service names matched the county's 2025 tax computation report 13/13
when this build was verified (the remaining names are neighbouring
counties' districts whose territory crosses the line). The map is a genuine
VECTOR PDF: each fire service is one filled path, and the legend maps fill
colour to name.

WHAT IS SHIPPED — the map's FIFTEEN named fire services, exactly as it
labels them, and nothing else. The map also overlays grey "Corporate"
municipal outlines and green "Parks" areas — the legend groups them
together as base-map reference classes, and the fire fills run UNDERNEATH
them (measured: Lena village sits inside both the grey overlay and the
Lena Fire fill), so treating the grey as a fire-service statement would
invent an exclusion the county never drew. The card carries a 2014-vintage
caveat on every feature.

The georeference is fitted ON the map's hydrography against TIGER
hydrography (see the block comment below for why the board build's
outline-fit route cannot work here) and validated by an INDEPENDENT
town-label check; the build fails if accuracy degrades below the floors it
shipped with.

THIS IS A RARE OPERATOR STEP (pymupdf + numpy; the PDF is archived in
data/source/raw/). Re-run only if the county republishes the map — or
DELETE this script the day it publishes real boundary data.

Usage:
    python3 scripts/build_stephenson_fire_districts.py
    python3 scripts/build_stephenson_fire_districts.py --check
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
    HEADERS, REQUEST_TIMEOUT, STATE_FIPS, TIGERWEB, dissolve, group_rings,
    point_in_rings, simplify,
)
from build_stephenson_board_districts import (  # noqa: E402  (same map series)
    as_features, need, pt_seg_factory, rings_of_path,
    DERIVED_TOLERANCE_M, HYDRO_COLOURS,
)
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    make_fail, require_robots_once,
)

# WHY THIS FIT IS INVERTED RELATIVE TO THE BOARD BUILD. The board map's
# polygons tile exactly one township, so their union outline IS the fit
# target. This map's fire services keep their TRUE extents — several cross
# the county line (Pecatonica, Forreston, Warren, Shannon, Davis are
# neighbouring counties' districts) — so the union outline is a superset of
# the county and fitting it against the county boundary converges to a
# systematically wrong transform (measured: only 11% of hydrography landed
# within 50 m). The fit therefore runs ON the map's hydrography against
# TIGER hydrography — the densest feature class present in both — and the
# INDEPENDENT check becomes the map's own town-name label positions against
# the towns' real coordinates, a feature class the fit never saw.
#
# Accuracy floors are this build's own, measured at first ship: the map
# covers the whole county (~29 m of ground per PDF point vs the board map's
# ~6), so the same drawing precision lands proportionally coarser.
# Measured at first ship: hydrography fit median 11.5 m / RMS 18.2 m (99% of
# map hydro within 120 m); town-label check median 402 m / worst 1557 m.
MAX_CONTROL_MEDIAN_M = 20.0
MAX_CONTROL_RMS_M = 30.0
MAX_TOWN_MEDIAN_M = 800.0    # a town LABEL sits beside its town, not on it
MAX_TOWN_WORST_M = 2500.0

# The independent check's towns: label text as printed on the map -> the
# town's real coordinates (the board build's derived anchor coordinates and
# the towns' published locations).
TOWNS = {
    "Freeport": (42.2966, -89.6212),
    "Lena": (42.3794, -89.8223),
    "Cedarville": (42.3760, -89.6332),
    "Orangeville": (42.4680, -89.6449),
    "Dakota": (42.3888, -89.5264),
    "Davis": (42.4225, -89.4137),
    "Winslow": (42.4927, -89.7918),
    "Ridott": (42.2964, -89.4754),
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "stephenson-fire-districts.json")
RAW_DIR = os.path.join(REPO_ROOT, "il", "data", "source", "raw")
FIRE_PDF = os.path.join(RAW_DIR, "Stephenson COUNTY FIRE DISTRICT MAP 070814.pdf")

COUNTY_FIPS = "177"
SOURCE_LABEL = ("Stephenson County FIRE DISTRICT MAP (2014-07-08), the county's "
                "own published tiling, preserved on the Illinois SBE precinctmaps mirror")
SOURCE_URL = ("https://www.elections.il.gov/precinctmaps/Stephenson/"
              "COUNTY%20FIRE%20DISTRICT%20MAP%20070814.pdf")

# Legend fill colour -> the map's own label, read from the legend swatches and
# verified by machine (each colour has exactly ONE map-body path). The grey
# "Corporate" fill is handled separately below.
FIRE_FILLS = {
    (1.0, 0.922, 0.686): "Cedarville Fire",
    (1.0, 0.745, 0.745): "Dakota Fire-Ambulance",
    (0.702, 0.988, 0.761): "Davis Fire-Ambulance",
    (0.451, 0.698, 1.0): "Forreston Fire-Ambulance",
    (1.0, 1.0, 0.745): "Freeport Fire-Ambulance",
    (0.894, 0.988, 0.812): "Freeport Rural Fire-Ambulance",
    (1.0, 0.827, 0.498): "German Valley Fire-Ambulance",
    (0.988, 0.843, 0.894): "Lena Fire",
    (0.988, 0.714, 0.937): "Orangeville Fire",
    (0.804, 0.773, 0.988): "Pearl City Fire",
    (0.894, 0.988, 0.714): "Pecatonica Fire-Ambulance",
    (0.745, 0.824, 1.0): "Rock City Fire-Ambulance",
    (1.0, 0.745, 0.91): "Shannon Fire-Ambulance",
    (0.745, 1.0, 0.91): "Warren Fire-Ambulance",
    (0.82, 1.0, 0.451): "Winslow Fire",
}
# The fit's hydro classes: the board build's water fill/outline colours PLUS
# this map's dense bright-blue stream network, which the township-scale board
# map does not carry.
FIT_HYDRO_COLOURS = set(HYDRO_COLOURS) | {(0.039, 0.576, 0.988)}
# The grey municipal-corporate overlay's fill — recorded so nobody re-adds it:
# it is base-map annotation drawn ON TOP of the fire fills, not a district.
CORPORATE_FILL = (0.408, 0.408, 0.408)
# The map body sits left of the legend panel.
MAP_BODY_MAX_X = 1534

# Points that must land in the polygon the county's map puts them in — every
# one DERIVED during the build (transformed and read back), never recalled.
# Town centres sit inside the grey corporate cut-outs, so the named-district
# anchors are rural points just outside each town.
ANCHORS = [
    (42.3805, -89.8221, "Lena Fire", "Lena (village of its namesake service)"),
    (42.2966, -89.6220, "Freeport Fire-Ambulance", "downtown Freeport"),
    (42.2500, -89.7000, "Freeport Rural Fire-Ambulance", "rural point southwest of Freeport"),
    (42.3900, -89.6332, "Cedarville Fire", "rural point north of Cedarville"),
    (42.4133, -89.4900, "Rock City Fire-Ambulance", "rural point west of Rock City"),
    (42.2653, -89.8100, "Pearl City Fire", "rural point east of Pearl City"),
    (42.4680, -89.6300, "Orangeville Fire", "rural point near Orangeville"),
    (42.2156, -89.4900, "German Valley Fire-Ambulance", "rural point west of German Valley"),
    (42.4927, -89.8100, "Winslow Fire", "rural point east of Winslow"),
]


fail = make_fail("stephenson-fire")


def rings_of_feature(feature):
    g = feature["geometry"]
    return (g["coordinates"] if g["type"] == "Polygon"
            else [r for poly in g["coordinates"] for r in poly])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()
    pymupdf = need("pymupdf")
    np = need("numpy")

    if not os.path.exists(FIRE_PDF):
        fail("archived source map missing: %s" % os.path.relpath(FIRE_PDF, REPO_ROOT))

    # ---- read the map: one filled path per fire service + the grey cut-outs --
    page = pymupdf.open(FIRE_PDF)[0]
    per_label = collections.defaultdict(list)
    hydro_pts = []
    for p in page.get_drawings():
        fill = p.get("fill")
        stroke = p.get("color")
        key = tuple(round(c, 3) for c in fill) if fill is not None else None
        if key in FIRE_FILLS:
            if p["rect"].x0 > MAP_BODY_MAX_X:
                continue                                   # legend swatch
            per_label[FIRE_FILLS[key]] += rings_of_path(p)
        for col in (fill, stroke):
            if col is not None and tuple(round(c, 3) for c in col) in FIT_HYDRO_COLOURS:
                for it in p["items"]:
                    if it[0] == "l":
                        hydro_pts += [(it[1].x, it[1].y), (it[2].x, it[2].y)]
                    elif it[0] == "c":
                        hydro_pts += [(it[1].x, it[1].y), (it[4].x, it[4].y)]
                break
    missing = sorted(set(FIRE_FILLS.values()) - set(per_label))
    if missing:
        fail("fire service(s) named by the legend have no map polygon: %s" % ", ".join(missing))

    # ---- georeference: fit the map's hydrography to TIGER hydrography -------
    pt_seg = pt_seg_factory(np)

    # WHICH HOST'S POLICY THIS ASKS FOR, AND WHY IT IS NOT elections.il.gov.
    # SOURCE_URL above is an SBE address, and that host refuses us — but this
    # script never reads it. The map is archived under data/source/raw/ and the
    # url is written into each feature as `mapUrl` so a reader can see where the
    # boundary came from. A CITATION IS NOT A FETCH: robots.txt governs what we
    # crawl, not what we link. The only host this script contacts is TIGERweb,
    # for the county outline and the hydrography the georeference is fitted on,
    # and it publishes no robots.txt at all (HTTP 200, 189 bytes of HTML at
    # /arcgis/rest/services, measured from a runner 2026-09-30), which under
    # RFC 9309 2.3.1.3 is no policy and therefore allow.
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=dict(HEADERS),
                        label="stephenson-fire-districts")
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "NAME", "returnGeometry": "true", "outSR": "4326", "f": "geojson"})
    resp.raise_for_status()
    cfeats = (resp.json() or {}).get("features") or []
    if len(cfeats) != 1:
        fail("TIGERweb returned %d county polygons for Stephenson" % len(cfeats))
    cg = cfeats[0]["geometry"]
    tparts = cg["coordinates"] if cg["type"] == "MultiPolygon" else [cg["coordinates"]]
    T = np.array([c[:2] for p in tparts for r in p for c in r], float)
    lat0 = float(T[:, 1].mean())
    kx = math.cos(math.radians(lat0))

    # TIGER hydro segments over the county envelope plus margin (the map's
    # basemap runs past the county line).
    pad = 0.12
    env = "%.5f,%.5f,%.5f,%.5f" % (T[:, 0].min() - pad, T[:, 1].min() - pad,
                                   T[:, 0].max() + pad, T[:, 1].max() + pad)
    hsegs = []
    for lyr in (0, 1):
        r2 = requests.get(
            "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Hydro/MapServer/%d/query" % lyr,
            headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
                "geometry": env, "geometryType": "esriGeometryEnvelope", "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects", "outFields": "NAME",
                "outSR": "4326", "f": "geojson", "returnGeometry": "true"})
        r2.raise_for_status()
        for f in (r2.json() or {}).get("features") or []:
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
        fail("TIGER returned no hydrography to fit against")
    # Densify the TIGER polylines to ~20 m spacing and put them in a KD-tree:
    # nearest-point ICP against the densified network is both faster and free
    # of the distance inflation that decimating SEGMENTS would introduce.
    need("scipy")
    import importlib
    scipy_spatial = importlib.import_module("scipy.spatial")
    dense = []
    for seg in hsegs:
        for a, b in seg:
            L = float(np.hypot(*(b - a))) * 111320
            n = max(1, int(L // 20))
            for i in range(n + 1):
                dense.append(a + (b - a) * (i / float(n)))
    ctrl_pts = np.unique(np.array(dense), axis=0)
    tree = scipy_spatial.cKDTree(ctrl_pts)

    # PDF hydro points, deduplicated and deterministically subsampled.
    hydro_sample = sorted(set(hydro_pts))
    step = max(1, len(hydro_sample) // 4000)
    P = np.array(hydro_sample[::step], float)

    # Initial guess from the fire-union bbox against the county bbox — a
    # couple of kilometres off (the union spills past the line), which the
    # generous early cutoffs absorb.
    fire_rings = [r for v in per_label.values() for r in v]
    U = np.array(sorted({tuple(pt) for ring in fire_rings for pt in ring}), float)
    Tm = np.column_stack([T[:, 0] * kx, T[:, 1]])
    sx = (Tm[:, 0].max() - Tm[:, 0].min()) / (U[:, 0].max() - U[:, 0].min())
    sy = (Tm[:, 1].max() - Tm[:, 1].min()) / (U[:, 1].max() - U[:, 1].min())
    A = np.array([[sx, 0.0], [0.0, -sy]])
    t = np.array([Tm[:, 0].min() - sx * U[:, 0].min(), Tm[:, 1].max() + sy * U[:, 1].min()])
    for cut in ([float("inf")] * 8 + [2000 / 111320] * 10 + [800 / 111320] * 10 +
                [300 / 111320] * 15 + [120 / 111320] * 15):
        d, idx = tree.query(P @ A.T + t)
        keep = d <= cut
        if keep.sum() < 300:
            fail("georeference lost its correspondences — the map's hydrography no "
                 "longer matches TIGER's")
        M = np.column_stack([P[keep], np.ones(int(keep.sum()))])
        sol, *_ = np.linalg.lstsq(M, ctrl_pts[idx[keep]], rcond=None)
        A, t = sol[:2].T, sol[2]

    d, _ = tree.query(P @ A.T + t)
    matched = d[d < 120 / 111320] * 111320
    ctrl_median, ctrl_rms = float(np.median(matched)), float((matched ** 2).mean() ** 0.5)
    ctrl_within = float((d * 111320 < 120).mean())
    if ctrl_median > MAX_CONTROL_MEDIAN_M or ctrl_rms > MAX_CONTROL_RMS_M:
        fail("hydrography fit degraded: median %.1f m (max %.1f), RMS %.1f m (max %.1f)"
             % (ctrl_median, MAX_CONTROL_MEDIAN_M, ctrl_rms, MAX_CONTROL_RMS_M))

    # INDEPENDENT check: the map's own town-name labels, a feature class the
    # fit never saw, against the towns' real coordinates.
    words = page.get_text("words")
    town_err = {}
    for town, (tlat, tlng) in TOWNS.items():
        parts = town.split()
        cands = []
        # The map prints labels in caps, and township names share the style,
        # so a town can match several candidates; the NEAREST one is compared,
        # which still bounds gross transform error (labels cluster near their
        # towns and nothing else on the map carries these names).
        for w in words:
            if w[0] > MAP_BODY_MAX_X or w[4].upper() != parts[0].upper():
                continue
            cands.append(((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
        if not cands:
            fail("town label %r not found on the map body" % town)
        best = None
        for cx, cy in cands:
            q = np.array([cx, cy], float) @ A.T + t
            lon, lat = float(q[0] / kx), float(q[1])
            dm = math.hypot((lon - tlng) * 111320 * kx, (lat - tlat) * 111320)
            if best is None or dm < best:
                best = dm
        town_err[town] = best
    town_med = float(np.median(list(town_err.values())))
    town_worst = max(town_err.values())
    if town_med > MAX_TOWN_MEDIAN_M or town_worst > MAX_TOWN_WORST_M:
        fail("independent town-label check failed: median %.0f m (max %.0f), worst "
             "%.0f m (max %.0f) — %s" % (town_med, MAX_TOWN_MEDIAN_M, town_worst,
                                         MAX_TOWN_WORST_M, town_err))

    def to_lonlat(pt):
        q = np.array(pt, float) @ A.T + t
        return [round(float(q[0] / kx), 6), round(float(q[1]), 6)]

    # ---- emit: 15 named services + one combined corporate feature -----------
    # No per-label dissolve: unlike the board map's per-precinct polygons, each
    # fire service here is already ONE filled path (outer rings + holes), and
    # the corporate cut-outs are disjoint — group_rings nests them directly.
    features = []
    for label in sorted(per_label):
        closed = [[list(p) for p in r] + ([list(r[0])] if list(r[0]) != list(r[-1]) else [])
                  for r in per_label[label]]
        polys = group_rings(closed)
        polys = [[simplify([to_lonlat(p) for p in ring], DERIVED_TOLERANCE_M) for ring in poly]
                 for poly in polys]
        polys = [[r if r[0] == r[-1] else r + [r[0]] for r in poly if len(r) >= 4] for poly in polys]
        polys = [p for p in polys if p]
        props = {"district": label, "source": SOURCE_LABEL, "mapUrl": SOURCE_URL,
                 "derivedFrom": "georeferenced county map"}
        features.append({
            "type": "Feature", "properties": props,
            "geometry": ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                         else {"type": "MultiPolygon", "coordinates": polys}),
        })

    import os as _os
    if _os.environ.get("ANCHOR_PROBE"):
        for lat, lng, want, label in ANCHORS:
            hit = [f["properties"]["district"] for f in features
                   if point_in_rings(lat, lng, rings_of_feature(f))]
            print("PROBE %.4f,%.4f want=%r got=%s (%s)" % (lat, lng, want, hit, label))
        sys.exit(0)
    for lat, lng, want, label in ANCHORS:
        hit = [f["properties"]["district"] for f in features
               if point_in_rings(lat, lng, rings_of_feature(f))]
        if hit != [want]:
            fail("%s should be %r, got %s" % (label, want, hit or "no polygon"))

    payload = {"type": "FeatureCollection", "features": features}
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    summary = ("%d named fire services — hydrography "
               "fit median %.1f m / RMS %.1f m (%.0f%% of map hydro within 120 m), "
               "independent town-label check median %.0f m / worst %.0f m, %d anchors hold"
               % (len(features), ctrl_median, ctrl_rms, 100 * ctrl_within,
                  town_med, town_worst, len(ANCHORS)))
    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("data/app/stephenson-fire-districts.json is missing — run this script")
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes). NOTE: a "
                 "georeference is an iterative fit, so a byte difference can be "
                 "numerical rather than real — compare the accuracy numbers above "
                 "before assuming the map changed." % (len(shipped), len(text)))
        print("stephenson-fire: OK — matches a fresh build; %s" % summary)
        return
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("stephenson-fire: wrote %s — %s, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), summary, len(text)))


if __name__ == "__main__":
    main()
