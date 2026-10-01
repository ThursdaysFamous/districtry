#!/usr/bin/env python3
"""
Build data/app/stephenson-precincts.json — Stephenson County's 36 current
voting precincts, georeferenced from the county's own two adopted precinct
maps.

WHY THIS EXISTS, AND WHY IT DID NOT UNTIL NOW. Two gaps in the guidebook said
flatly that "the county publishes no current precinct boundaries", and the
board build's header says the same. Both were wrong, and wrong in the way the
ask ledger predicts: they described what we had FOUND, not what the county
had PUBLISHED. On 2026-08-03 County Clerk Jazmin Wingert answered a records
request with one line — "Here is a link to the maps I have record of" — and
the link was the Clerk's own Elections page, which carries CITY OF FREEPORT
PRECINCT MAP and RURAL PRECINCT MAP. Both are VECTOR PDFs of the current
(post-2020-census, adopted 2022-01-07) precincts, and between them they cover
the county exactly once. The data was on the county's website the whole time,
one page away from the board-district maps this repo already used.

WHAT THE TWO MAPS ARE
  * RURAL PRECINCTS — 20 precincts covering the county's 17 rural townships.
    Fourteen townships run a single precinct; Harlem, Rock Run and West Point
    each run two.
  * FREEPORT TOWNSHIP PRECINCTS — Freeport 01-16, the township that holds 53%
    of the county.
Each precinct is one filled path with its own fill colour, and each is
labelled in the map body with its name and its 2020 census population.

THE PRECINCT LINES ARE NOT THE TOWNSHIP LINES, and the maps say so in
numbers. Six rural precincts print a population that differs from the Census
count for the township they are named after: the rural precincts reach into
Freeport township and take 329 people with them. That is not transcription
error — the sum runs the other way exactly. The 20 rural figures total 20,986
and the 16 Freeport figures total 23,644; together 44,630, which is
Stephenson County's live Census 2020 POP100 to the person. Both halves of
that arithmetic are asserted on every run. The georeference then confirms it
independently: the precincts that gained population are the ones whose
polygons measurably cross the Freeport township line.

So this build ships the polygons AS DRAWN and never snaps them to township
edges. Snapping would look tidier and would invent a boundary the county did
not draw.

MEASURED ACCURACY (regenerated on every run; the build fails if it degrades).
The two maps are fitted separately, because they are drawn at very different
scales, and each is checked against a feature class its own fit never saw:

  * FREEPORT — fitted against the TIGER Freeport county subdivision (the
    union of its 16 precincts is that township). Control median 1.6 m /
    RMS 10.9 m. INDEPENDENT check: the map's hydrography vs TIGER
    hydrography, 98.9% within 50 m, median 15.7 m.
  * RURAL — fitted against the TIGER county subdivisions dissolved WITHOUT
    Freeport (the union of its 20 precincts is that shape). Control median
    6.2 m / RMS 16.2 m. INDEPENDENT checks: the map's own 16 township NAME
    labels, which are text and were never fitted against, must each land
    inside the township they name (16/16); and every precinct polygon must
    sit at least 97% inside the township it is named for (worst 97.4% —
    Harlem 02, the deliberate crossing above; median 99.7%).

AND ONE CROSS-CHECK THE FLEET HAS NEVER HAD BEFORE. Stephenson's four
Freeport board districts were georeferenced in 2026-08 from a DIFFERENT PDF —
COUNTY BOARD FREEPORT TOWNSHIP DISTRICTS — which draws the same 16 precincts
coloured by district instead of individually. Two documents, two independent
georeferences. They agree: all 16 precincts land in the district
build_stephenson_board_districts.py assigns them, 16/16, and each district
matches the union of its four precincts at IoU 0.996 or better (worst 0.9959,
district B — the residue is the two builds' separate simplification passes).
That is asserted here on every run, so the day either map is republished the
disagreement surfaces instead of shipping.

THAT CROSS-CHECK EARNED ITS KEEP ON ITS FIRST RUN, and it is worth recording
which way it pointed. This build originally unioned each precinct's rings as
solids, and the cross-check failed: district D matched the union of its four
precincts at only IoU 0.956 where B, C and E all matched at 0.996. The
suspicion was a defect in the shipped board file — build_metro_outline's
group_rings() nests district D's ten dissolved rings as one outer ring and
nine holes, which "loses" 4.06% of its area. It was not a defect. EVERY
filled path on both maps declares the PDF EVEN-ODD fill rule (asserted on
every run now), so a ring inside another ring is a hole; group_rings() lands
on the same 95.94% that even-odd does, and it was this build's solids-union
that was wrong — it was filling 1.64% of Freeport township that the county
never painted, 6.66% of it in precinct 13 alone. fill_geometry() below now
applies the rule the document declares.

THIS IS A RARE OPERATOR STEP (pymupdf + numpy + shapely; the PDFs are
archived in data/source/raw/). Re-run only if the county republishes a
precinct map — or DELETE this script the day Stephenson publishes real
precinct geometry.

Usage:
    python3 scripts/build_stephenson_precincts.py
    python3 scripts/build_stephenson_precincts.py --check
"""

import argparse
import collections
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    HEADERS, REQUEST_TIMEOUT, STATE_FIPS, TIGERWEB, dissolve, point_in_rings,
    simplify,
)
from build_stephenson_board_districts import (  # noqa: E402  (same map series)
    DERIVED_TOLERANCE_M, FREEPORT_PRECINCTS, HYDRO_COLOURS, TIGER_COUSUB,
    TOWNSHIP_POP, as_features, fit_affine_icp, hydro_check, need,
    rings_of_path,
)
from scraper_common import require_robots_once, make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "stephenson-precincts.json")
RAW_DIR = os.path.join(REPO_ROOT, "il", "data", "source", "raw")
FREEPORT_PDF = os.path.join(RAW_DIR, "Stephenson FREEPORT TOWNSHIP PRECINCTS 010722.pdf")
RURAL_PDF = os.path.join(RAW_DIR, "Stephenson RURAL PRECINCTS 010722.pdf")
BOARD_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                          "stephenson-county-board-districts.json")

COUNTY_FIPS = "177"
FREEPORT_TOWNSHIP = "Freeport"
SOURCE_LABEL = ("Stephenson County adopted precinct maps, 2022-01-07 "
                "(FREEPORT TOWNSHIP PRECINCTS / RURAL PRECINCTS), supplied by "
                "County Clerk & Recorder Jazmin Wingert 2026-08-03")
SOURCE_URL = ("https://stephensoncountyil.gov/government/"
              "county_clerk_and_recorder/elections.php")

# The Freeport map's own colour classes that are NOT precincts.
FREEPORT_WATER = (0.592, 0.859, 0.949)
FREEPORT_WHITE = (1.0, 1.0, 1.0)
# Legend swatches are small boxes down the left margin; every precinct path is
# far larger than this in both dimensions (smallest measured 62 x 91 pt).
LEGEND_MAX_PT = 30

EXPECTED_RURAL = 20
EXPECTED_FREEPORT = 16
# The county's 2020 population, asserted live against Census POP100 rather
# than hardcoded — this is the constant the two maps' 36 printed figures must
# reproduce between them.
SPLIT_TOWNSHIPS = ("Harlem", "Rock Run", "West Point")

# Accuracy floors, each this build's own measurement at first ship with room
# for the iterative fit to wobble. See the header for what they mean.
MAX_FREEPORT_MEDIAN_M = 6.0
MAX_FREEPORT_RMS_M = 20.0
MAX_RURAL_MEDIAN_M = 12.0
MAX_RURAL_RMS_M = 25.0
MIN_TOWNSHIP_CONTAINMENT = 0.97
# The two-document cross-check. The board build fits the SAME 16 polygons off
# a different PDF; the unions measured IoU 1.0000 at first ship.
MIN_CROSS_CHECK_IOU = 0.995
# A label anchor may be printed just outside a small precinct (measured: West
# Point 02's is 0 pt outside its polygon but inside its bounding box). One
# such orphan is tolerated per map and must still be nearest to the precinct
# it is paired with.
MAX_ORPHAN_LABEL_PT = 25.0
# How far a precinct's NUMBER may sit from its township NAME. The rural map
# also prints US/state highway shields, and one of them ("75") sits on the
# same text line as the HARLEM township label — read naively it becomes a
# 21st precinct, "Harlem 75". Measured: the twenty real labels put the number
# 15.3 to 31.4 pt after the name; that shield sits 139.8 pt away.
MAX_NAME_NUMBER_GAP_PT = 45.0

# Points that must land in the precinct the county's maps put them in. Every
# one is DERIVED during the build — transformed and read back — never recalled.
ANCHORS = [
    (42.4927, -89.7918, "Winslow 01", "Winslow village"),
    (42.3805, -89.8221, "West Point 02", "Lena village"),
    (42.4680, -89.6449, "Oneco 01", "Orangeville village"),
    (42.3888, -89.5264, "Dakota 01", "Dakota village"),
    (42.3760, -89.6332, "Buckeye 01", "Cedarville village"),
    (42.4225, -89.4137, "Rock Run 02", "Davis village"),
    (42.2964, -89.4754, "Ridott 01", "Ridott village"),
    (42.2653, -89.8260, "Loran 01", "Pearl City village"),
    (42.2966, -89.6220, "Freeport 01", "downtown Freeport"),
]


fail = make_fail("stephenson-precincts")


def fill_geometry(rings, Polygon, unary_union):
    """The area a precinct's path actually paints.

    EVERY path on both maps declares the EVEN-ODD fill rule (asserted below),
    so a ring drawn inside another ring is a HOLE, not more area. Unioning the
    rings as solids instead would fill those holes — measured: it adds 1.64%
    to the Freeport map, 6.66% of it to precinct 13 alone. That is exactly the
    disagreement the board cross-check catches, and it is this build that was
    wrong, not the shipped board file: build_metro_outline's group_rings()
    lands on the same 95.94% for district D that even-odd does.
    """
    polys = [Polygon(r).buffer(0) for r in rings if len(r) >= 3]
    polys = [p for p in polys if not p.is_empty]
    if not polys:
        return unary_union([])
    out = polys[0]
    for poly in polys[1:]:
        out = out.symmetric_difference(poly)
    return out.buffer(0)


def parts_of(geom):
    """A shapely polygon/multipolygon as the MultiPolygon-style coordinate
    list fit_affine_icp expects."""
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    return [[list(p.exterior.coords)] + [list(r.coords) for r in p.interiors]
            for p in polys]


def word_tokens(page, max_x=None):
    """(text, centre-x, centre-y) for every word on the page."""
    return [(w[4], (w[0] + w[2]) / 2.0, (w[1] + w[3]) / 2.0)
            for w in page.get_text("words")
            if max_x is None or w[0] <= max_x]


def population_anchors(toks):
    """Every "POPULATION nnnn" block on the page as (population, x, y).

    The number is set on the line below or beside the word, so it is taken as
    the nearest digit-run that is not above it."""
    out = []
    for text, x, y in toks:
        if text != "POPULATION":
            continue
        best = None
        for t2, x2, y2 in toks:
            if not t2.isdigit():
                continue
            d = math.hypot(x2 - x, y2 - y)
            if y2 >= y - 6 and d < 90 and (best is None or d < best[0]):
                best = (d, int(t2))
        if best is None:
            fail("a POPULATION label on the map has no number beside it")
        out.append((best[1], x, y))
    return out


def assign_blocks(geoms, blocks, Point):
    """Map each fill's geometry to exactly one label block, by containment,
    allowing ONE block whose anchor is printed just outside its polygon.

    Returns {fill key: block}. Fails on any other shape of mismatch, so a
    republished map that moves labels around stops the build instead of
    silently mislabelling a precinct."""
    taken, out = set(), {}
    for key, geom in geoms.items():
        hits = [i for i, b in enumerate(blocks)
                if i not in taken and geom.contains(Point(b[1], b[2]))]
        if len(hits) == 1:
            out[key] = blocks[hits[0]]
            taken.add(hits[0])
        elif len(hits) > 1:
            # More than one block inside one polygon means a neighbouring
            # precinct's label was printed over this one; resolve by taking
            # the nearest and leaving the rest for their own polygons.
            best = min(hits, key=lambda i: geom.centroid.distance(
                Point(blocks[i][1], blocks[i][2])))
            out[key] = blocks[best]
            taken.add(best)

    loose_keys = [k for k in geoms if k not in out]
    loose_blocks = [i for i in range(len(blocks)) if i not in taken]
    if len(loose_keys) != len(loose_blocks):
        fail("%d precinct polygons have no label and %d labels have no polygon "
             "— the map's labelling changed" % (len(loose_keys), len(loose_blocks)))
    if len(loose_keys) > 1:
        fail("%d precinct polygons could not be labelled by containment; only a "
             "single label printed outside its own polygon is tolerated"
             % len(loose_keys))
    for key in loose_keys:
        i = loose_blocks[0]
        anchor = Point(blocks[i][1], blocks[i][2])
        gap = geoms[key].distance(anchor)
        # The pairing is forced — one polygon, one label — so the guard that
        # earns its keep is spatial, not combinatorial: the label must sit
        # ON the polygon's own footprint. Measured for West Point 02 (Lena,
        # the county's smallest precinct by area): 0.2 pt outside the polygon
        # and well inside its bounding box, because the label is printed on
        # the surrounding precinct's fill where there is room for the text.
        if gap > MAX_ORPHAN_LABEL_PT or not geoms[key].envelope.contains(anchor):
            fail("the one unmatched label %r sits %.1f pt from the one unmatched "
                 "polygon and outside its bounding box — refusing to guess"
                 % (blocks[i][0], gap))
        out[key] = blocks[i]
    return out


def read_rural(pymupdf, Polygon, Point, unary_union):
    """{fill: (rings, precinct name, population)} for the RURAL map."""
    page = pymupdf.open(RURAL_PDF)[0]
    fills = collections.defaultdict(list)
    for path in page.get_drawings():
        colour = path.get("fill")
        if colour is None:
            continue
        if not path.get("even_odd"):
            fail("a filled path on the rural map does not use the even-odd fill "
                 "rule — fill_geometry()'s assumption no longer holds")
        fills[tuple(round(c, 3) for c in colour)] += rings_of_path(path)
    if len(fills) != EXPECTED_RURAL:
        fail("the rural map has %d filled colours, expected %d precincts"
             % (len(fills), EXPECTED_RURAL))

    geoms = {k: fill_geometry(rings, Polygon, unary_union)
             for k, rings in fills.items()}
    toks = word_tokens(page)
    names = set(TOWNSHIP_POP)
    # "<TOWNSHIP> NN" as printed, matched against the township vocabulary the
    # board build already carries so a stray all-caps word cannot become one.
    lines = collections.defaultdict(list)
    for tok in toks:
        lines[round(tok[2] / 4.0)].append(tok)
    blocks, seen = [], set()
    pops = population_anchors(toks)
    for key in sorted(lines):
        row = sorted(lines[key], key=lambda w: w[1])
        for width in (1, 2, 3):
            for i in range(len(row) - width):
                label = " ".join(w[0] for w in row[i:i + width]).title()
                number = row[i + width][0]
                if label not in names or not re.fullmatch(r"\d{2}", number):
                    continue
                if row[i + width][1] - row[i + width - 1][1] > MAX_NAME_NUMBER_GAP_PT:
                    continue                       # a highway shield, not a precinct
                full = "%s %s" % (label, number)
                if full in seen:
                    continue
                seen.add(full)
                cx = sum(w[1] for w in row[i:i + width + 1]) / (width + 1)
                cy = sum(w[2] for w in row[i:i + width + 1]) / (width + 1)
                pop = min(pops, key=lambda p: math.hypot(p[1] - cx, p[2] - cy))
                blocks.append((full, cx, cy, pop[0]))
    if len(blocks) != EXPECTED_RURAL:
        fail("read %d precinct labels off the rural map, expected %d: %s"
             % (len(blocks), EXPECTED_RURAL, sorted(b[0] for b in blocks)))
    assigned = assign_blocks(geoms, blocks, Point)
    return page, fills, {k: (v[0], v[3]) for k, v in assigned.items()}


def read_freeport(pymupdf, Polygon, Point, unary_union):
    """{fill: (rings, precinct name, population)} + hydrography for FREEPORT."""
    page = pymupdf.open(FREEPORT_PDF)[0]
    fills, hydro = collections.defaultdict(list), []
    for path in page.get_drawings():
        colour, stroke = path.get("fill"), path.get("color")
        key = tuple(round(c, 3) for c in colour) if colour is not None else None
        if (key is not None and key not in (FREEPORT_WATER, FREEPORT_WHITE)
                and not (path["rect"].width < LEGEND_MAX_PT
                         and path["rect"].height < LEGEND_MAX_PT)):
            if not path.get("even_odd"):
                fail("a precinct path on the Freeport map does not use the "
                     "even-odd fill rule — fill_geometry()'s assumption no "
                     "longer holds")
            fills[key] += rings_of_path(path)
        for col in (colour, stroke):
            if col is not None and tuple(round(c, 3) for c in col) in HYDRO_COLOURS:
                for item in path["items"]:
                    if item[0] == "l":
                        hydro += [(item[1].x, item[1].y), (item[2].x, item[2].y)]
                    elif item[0] == "c":
                        hydro += [(item[1].x, item[1].y), (item[4].x, item[4].y)]
                break
    if len(fills) != EXPECTED_FREEPORT:
        fail("the Freeport map has %d precinct colours, expected %d"
             % (len(fills), EXPECTED_FREEPORT))
    if not hydro:
        fail("no hydrography on the Freeport map — the independent accuracy "
             "check has nothing to run against")

    geoms = {k: fill_geometry(rings, Polygon, unary_union)
             for k, rings in fills.items()}
    toks = word_tokens(page)
    pops = population_anchors(toks)
    blocks, seen = [], set()
    for text, x, y in toks:
        if text != "PRECINCT":
            continue
        for t2, x2, y2 in toks:
            if re.fullmatch(r"\d{2}", t2) and abs(y2 - y) < 4 and 0 < x2 - x < 60:
                name = "%s %s" % (FREEPORT_TOWNSHIP, t2)
                pop = min(pops, key=lambda p: math.hypot(p[1] - x, p[2] - y))
                # The map prints PRECINCT 01 twice; keep the first and let
                # containment place it.
                if name not in seen:
                    seen.add(name)
                    blocks.append((name, x, y, pop[0]))
                break
    if len(blocks) != EXPECTED_FREEPORT:
        fail("read %d PRECINCT labels off the Freeport map, expected %d"
             % (len(blocks), EXPECTED_FREEPORT))
    assigned = assign_blocks(geoms, blocks, Point)
    return page, fills, {k: (v[0], v[3]) for k, v in assigned.items()}, hydro


def fetch_townships(shape):
    require_robots_once(TIGER_COUSUB, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-stephenson-precincts")
    resp = requests.get(TIGER_COUSUB, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                        params={"where": "STATE='%s' AND COUNTY='%s'"
                                         % (STATE_FIPS, COUNTY_FIPS),
                                "outFields": "BASENAME", "returnGeometry": "true",
                                "outSR": "4326", "f": "geojson"})
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    out = {}
    for f in feats:
        name = (f["properties"].get("BASENAME") or "").strip()
        out[name] = shape(f["geometry"]).buffer(0)
    if FREEPORT_TOWNSHIP not in out:
        fail("TIGER has no Freeport county subdivision for Stephenson")
    return out


def census_county_population():
    """Live Census 2020 POP100 for Stephenson County, summed over its own
    county subdivisions — the figure the two maps' 36 printed populations
    must reproduce between them."""
    url = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
           "tigerWMS_Census2020/MapServer/20/query")
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-stephenson-precincts")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "BASENAME,POP100", "returnGeometry": "false", "f": "json"})
    resp.raise_for_status()
    rows = (resp.json() or {}).get("features") or []
    if not rows:
        fail("Census returned no county subdivisions for Stephenson")
    return sum(int(r["attributes"]["POP100"]) for r in rows)


def emit(name, township, population, geom, simplify_m):
    polys = []
    for poly in ([geom] if geom.geom_type == "Polygon" else list(geom.geoms)):
        rings = [list(poly.exterior.coords)] + [list(r.coords) for r in poly.interiors]
        out = []
        for ring in rings:
            pts = simplify([[round(x, 6), round(y, 6)] for x, y in ring], simplify_m)
            if len(pts) < 4:
                continue
            if pts[0] != pts[-1]:
                pts.append(pts[0])
            out.append(pts)
        if out:
            polys.append(out)
    if not polys:
        fail("precinct %s simplified away to nothing" % name)
    return {
        "type": "Feature",
        "properties": {"name": name, "township": township,
                       "population": population,
                       "derivedFrom": "georeferenced county map",
                       "source": SOURCE_LABEL, "mapUrl": SOURCE_URL},
        "geometry": ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                     else {"type": "MultiPolygon", "coordinates": polys}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file, write nothing")
    args = ap.parse_args()
    pymupdf = need("pymupdf")
    np = need("numpy")
    need("shapely")
    from shapely.geometry import Point, Polygon, shape          # noqa: E402
    from shapely.ops import unary_union                          # noqa: E402

    for path in (FREEPORT_PDF, RURAL_PDF):
        if not os.path.exists(path):
            fail("archived source map missing: %s" % os.path.relpath(path, REPO_ROOT))

    townships = fetch_townships(shape)
    rural_page, rural_fills, rural_labels = read_rural(
        pymupdf, Polygon, Point, unary_union)
    fp_page, fp_fills, fp_labels, hydro = read_freeport(
        pymupdf, Polygon, Point, unary_union)

    # ---- the arithmetic proof, before a single polygon is transformed ------
    rural_pop = sum(p for _, p in rural_labels.values())
    fp_pop = sum(p for _, p in fp_labels.values())
    live = census_county_population()
    if rural_pop + fp_pop != live:
        fail("the maps' 36 printed populations total %d (rural %d + Freeport %d) "
             "but Stephenson County's live Census POP100 is %d — the "
             "transcription is wrong or a precinct was missed"
             % (rural_pop + fp_pop, rural_pop, fp_pop, live))
    by_township = collections.defaultdict(int)
    for name, pop in rural_labels.values():
        by_township[name.rsplit(" ", 1)[0]] += pop
    for name, total in sorted(by_township.items()):
        if TOWNSHIP_POP.get(name) != total:
            fail("the rural map's precinct populations for %s total %d, but the "
                 "county's RURAL DISTRICTS map prints %s for that township — the "
                 "two county maps disagree" % (name, total, TOWNSHIP_POP.get(name)))
    split = sorted(n for n, v in collections.Counter(
        nm.rsplit(" ", 1)[0] for nm, _ in rural_labels.values()).items() if v > 1)
    if split != sorted(SPLIT_TOWNSHIPS):
        fail("townships running more than one precinct are %s, expected %s"
             % (split, sorted(SPLIT_TOWNSHIPS)))

    # ---- georeference: two maps, two fits, two independent checks ----------
    def fit(fills, target, label):
        rings = [r for v in fills.values() for r in v]
        P = np.array(sorted({tuple(pt) for ring in dissolve(as_features(rings))
                             for pt in ring}), float)
        tparts = parts_of(target)
        T = np.array([c[:2] for p in tparts for r in p for c in r], float)
        kx = math.cos(math.radians(float(T[:, 1].mean())))
        A, t, pt_seg, ctrl = fit_affine_icp(np, P, tparts, kx, fail)
        d, _ = pt_seg(P @ A.T + t, ctrl)
        matched = d[d < 120 / 111320] * 111320
        return (A, t, kx, pt_seg, float(np.median(matched)),
                float((matched ** 2).mean() ** 0.5))

    fp_A, fp_t, fp_kx, fp_ptseg, fp_med, fp_rms = fit(
        fp_fills, townships[FREEPORT_TOWNSHIP], "Freeport")
    if fp_med > MAX_FREEPORT_MEDIAN_M or fp_rms > MAX_FREEPORT_RMS_M:
        fail("Freeport fit degraded: median %.1f m (max %.1f), RMS %.1f m (max %.1f)"
             % (fp_med, MAX_FREEPORT_MEDIAN_M, fp_rms, MAX_FREEPORT_RMS_M))
    hydro_within, hydro_median = hydro_check(np, requests, fp_ptseg, hydro,
                                             fp_A, fp_t, fp_kx, fail)

    rural_target = unary_union([g for n, g in townships.items()
                                if n != FREEPORT_TOWNSHIP])
    ru_A, ru_t, ru_kx, ru_ptseg, ru_med, ru_rms = fit(
        rural_fills, rural_target, "rural")
    if ru_med > MAX_RURAL_MEDIAN_M or ru_rms > MAX_RURAL_RMS_M:
        fail("rural fit degraded: median %.1f m (max %.1f), RMS %.1f m (max %.1f)"
             % (ru_med, MAX_RURAL_MEDIAN_M, ru_rms, MAX_RURAL_RMS_M))

    def make(A, t, kx):
        def to_lonlat(pt):
            q = np.array(pt, float) @ A.T + t
            return (float(q[0] / kx), float(q[1]))
        return to_lonlat
    ru_xy, fp_xy = make(ru_A, ru_t, ru_kx), make(fp_A, fp_t, fp_kx)

    # INDEPENDENT check 1 (rural): the map's own township NAME labels. Text is
    # a feature class the fit never touched, and the interior township grid is
    # not in the fit target either.
    label_hits, label_total = 0, 0
    lines = collections.defaultdict(list)
    for tok in word_tokens(rural_page):
        lines[round(tok[2] / 4.0)].append(tok)
    seen_labels = set()
    for key in sorted(lines):
        row = sorted(lines[key], key=lambda w: w[1])
        for width in (1, 2, 3):
            for i in range(len(row) - width + 1):
                name = " ".join(w[0] for w in row[i:i + width]).title()
                nxt = row[i + width][0] if i + width < len(row) else ""
                if (name not in townships or name == FREEPORT_TOWNSHIP
                        or name in seen_labels or re.fullmatch(r"\d{2}", nxt)):
                    continue
                seen_labels.add(name)
                label_total += 1
                cx = sum(w[1] for w in row[i:i + width]) / width
                cy = sum(w[2] for w in row[i:i + width]) / width
                if townships[name].contains(Point(*ru_xy((cx, cy)))):
                    label_hits += 1
    if label_total < len(townships) - 2 or label_hits != label_total:
        fail("independent township-label check: %d of %d labels landed inside "
             "the township they name — the rural georeference is not trustworthy"
             % (label_hits, label_total))

    # ---- build the 36 precinct geometries ---------------------------------
    geoms, worst_containment = {}, (1.0, None)
    for fills, labels, xy in ((rural_fills, rural_labels, ru_xy),
                              (fp_fills, fp_labels, fp_xy)):
        for key, rings in fills.items():
            name, pop = labels[key]
            geom = fill_geometry([[xy(p) for p in r] for r in rings],
                                 Polygon, unary_union)
            township = name.rsplit(" ", 1)[0]
            share = geom.intersection(townships[township]).area / geom.area
            if share < worst_containment[0]:
                worst_containment = (share, name)
            geoms[name] = (geom, township, pop)
    # INDEPENDENT check 2 (rural): containment in the named township.
    if worst_containment[0] < MIN_TOWNSHIP_CONTAINMENT:
        fail("precinct %s sits only %.2f%% inside %s (floor %.0f%%) — the maps' "
             "labelling and their geometry disagree"
             % (worst_containment[1], 100 * worst_containment[0],
                worst_containment[1].rsplit(" ", 1)[0],
                100 * MIN_TOWNSHIP_CONTAINMENT))
    if len(geoms) != EXPECTED_RURAL + EXPECTED_FREEPORT:
        fail("built %d precincts, expected %d"
             % (len(geoms), EXPECTED_RURAL + EXPECTED_FREEPORT))

    # The two maps must tile the county once: no precinct may overlap another,
    # and together they must cover it.
    union = unary_union([g for g, _, _ in geoms.values()])
    overlap = sum(g.area for g, _, _ in geoms.values()) - union.area
    if overlap / union.area > 0.001:
        fail("the 36 precincts overlap each other by %.3f%% of their union — "
             "they are supposed to tile the county exactly once"
             % (100 * overlap / union.area))
    require_robots_once(TIGERWEB, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-stephenson-precincts")
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "NAME", "returnGeometry": "true", "outSR": "4326",
        "f": "geojson"})
    resp.raise_for_status()
    county = shape((resp.json()["features"] or [{}])[0]["geometry"]).buffer(0)
    covered = union.intersection(county).area / county.area
    if covered < 0.99:
        fail("the 36 precincts cover only %.2f%% of Stephenson County" % (100 * covered))

    # ---- the two-document cross-check against the shipped board file ------
    with open(BOARD_PATH, encoding="utf-8") as handle:
        board = json.load(handle)
    board_geom = {f["properties"]["district"]: shape(f["geometry"]).buffer(0)
                  for f in board["features"]}
    worst_iou = (1.0, None)
    for code, members in sorted(FREEPORT_PRECINCTS.items()):
        mine = unary_union([geoms["%s %s" % (FREEPORT_TOWNSHIP, p)][0]
                            for p in members])
        theirs = board_geom.get(code)
        if theirs is None:
            fail("the shipped board file has no district %s to cross-check" % code)
        for p in members:
            g = geoms["%s %s" % (FREEPORT_TOWNSHIP, p)][0]
            share = g.intersection(theirs).area / g.area
            best = max((g.intersection(board_geom[c]).area / g.area, c)
                       for c in FREEPORT_PRECINCTS)
            if best[1] != code:
                fail("precinct Freeport %s lies mostly in shipped district %s, but "
                     "build_stephenson_board_districts.py assigns it to %s — the "
                     "county's two maps disagree" % (p, best[1], code))
            del share
        iou = mine.intersection(theirs).area / mine.union(theirs).area
        if iou < worst_iou[0]:
            worst_iou = (iou, code)
    if worst_iou[0] < MIN_CROSS_CHECK_IOU:
        fail("cross-check against the shipped board districts: district %s only "
             "matches the union of its four precincts at IoU %.4f (floor %.3f). "
             "Two independently georeferenced county maps of the same lines "
             "should agree — investigate before shipping either."
             % (worst_iou[1], worst_iou[0], MIN_CROSS_CHECK_IOU))

    features = [emit(name, township, pop, geom, DERIVED_TOLERANCE_M)
                for name, (geom, township, pop) in sorted(geoms.items())]

    def rings_of_feature(feature):
        g = feature["geometry"]
        return (g["coordinates"] if g["type"] == "Polygon"
                else [r for poly in g["coordinates"] for r in poly])

    if os.environ.get("ANCHOR_PROBE"):
        for lat, lng, want, label in ANCHORS:
            hit = [f["properties"]["name"] for f in features
                   if point_in_rings(lat, lng, rings_of_feature(f))]
            print("PROBE %.4f,%.4f want=%r got=%s (%s)" % (lat, lng, want, hit, label))
        sys.exit(0)
    for lat, lng, want, label in ANCHORS:
        hit = [f["properties"]["name"] for f in features
               if point_in_rings(lat, lng, rings_of_feature(f))]
        if hit != [want]:
            fail("%s should be %r, got %s" % (label, want, hit or "no precinct"))

    payload = {"type": "FeatureCollection", "features": features}
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    summary = ("%d precincts (%d rural + %d Freeport) — 36 printed populations "
               "total %d = live Census POP100; Freeport fit median %.1f m / RMS "
               "%.1f m with hydrography %.1f%% within 50 m (median %.1f m); rural "
               "fit median %.1f m / RMS %.1f m with %d/%d township labels inside "
               "their township and worst containment %.2f%% (%s); board cross-check "
               "worst IoU %.4f (%s); %.2f%% of the county covered, %d anchors hold"
               % (len(features), EXPECTED_RURAL, EXPECTED_FREEPORT, live,
                  fp_med, fp_rms, 100 * hydro_within, hydro_median,
                  ru_med, ru_rms, label_hits, label_total,
                  100 * worst_containment[0], worst_containment[1],
                  worst_iou[0], worst_iou[1], 100 * covered, len(ANCHORS)))

    existing = None
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as handle:
            existing = handle.read()
    if args.check:
        if existing is None:
            fail("data/app/stephenson-precincts.json is missing — run this script")
        if existing != text:
            fail("shipped file differs from a fresh build (%d vs %d bytes). NOTE: a "
                 "georeference is an iterative fit, so a byte difference can be "
                 "numerical rather than real — compare the accuracy numbers above "
                 "before assuming the maps changed." % (len(existing), len(text)))
        print("stephenson-precincts: OK — matches a fresh build; %s" % summary)
        return
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("stephenson-precincts: wrote %s — %s, %d bytes"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), summary, len(text)))


if __name__ == "__main__":
    main()
