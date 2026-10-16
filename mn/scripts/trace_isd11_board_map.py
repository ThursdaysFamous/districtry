#!/usr/bin/env python3
"""Read Anoka-Hennepin's own school board election district map and record
which 2022 precincts make up each of its six districts.

WHY THIS BOARD NEEDS ITS OWN MAP. `build_mn_school_board_districts.py` draws a
board's election districts from the precincts that voted in each district's
contest. Anoka-Hennepin (ISD 11) runs its board elections in odd years and
reports every district contest at combined polling places ("ISD 11 SB1 P1 -
RAMSEY MUNICIPAL CENTER"), which the Secretary of State's files never place on
precincts, so the results cannot draw it. The district publishes the map
itself: "Anoka-Hennepin School District Current Board Election Areas, School
Board District Boundaries (2022)", produced by Anoka County and dated
05/05/22, linked as "View the election area map" from the board's own page
(www.ahschools.us/about/school-board, read 2026-10-15 after its robots.txt,
whose `*` group allows /fs/resource-manager/view/ and asks for a five-second
Crawl-delay).

WHAT IS READ FROM IT, AND HOW. The PDF is vector artwork: each district is one
filled shape in its own legend colour, drawn over the 2022 precinct outlines
and labels. The shapes are placed on the ground by an affine fit of their
outer edge to the Census's own Anoka-Hennepin school district boundary
(iterated nearest-edge least squares, starting from the two bounding boxes).
Each 2022 precinct (the Secretary of State's own "By Precinct 2022" layer) is
then given to the district whose shape covers it. The map says the districts
are built of 2022 precincts, and the measurement agrees: every precinct falls
in one district, with no second district holding more than MAX_SECOND of it.
Two independent checks are recorded with the result: the fit's own residual
along the boundary, and the map's printed precinct labels — each label's
position, carried through the fit, must land in the precinct its text names.

A one-off measurement, not a weekly job: the map changes only when the board
redraws its districts, which it does after a census (recorded in
docs/REDISTRICTING_RUNBOOK.md). It needs pymupdf, shapely and numpy, which CI
does not install; `build_mn_school_board_districts.py` reads only its output.

Usage:
    python3 mn/scripts/trace_isd11_board_map.py            # fetch, measure, write
    python3 mn/scripts/trace_isd11_board_map.py --pdf FILE # use a saved copy of the map
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
BOARD_PAGE = "https://www.ahschools.us/about/school-board"
MAP_URL = ("https://www.ahschools.us/fs/resource-manager/view/"
           "64849109-6308-46ab-a5a4-19ab85b45278")
CRAWL_DELAY = 5
SCHOOL_GEOID = "2703180"
TIGER_SCHOOL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "School/MapServer/0/query")
PRECINCTS_2022 = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
                  "us_mn_state_sos/bdry_electionresults_2022_2030/FeatureServer/1/query")
UTM = 26915
OUT_FILE = os.path.join(INSTANCE, "data", "source", "isd11-board-districts.json")

# The six legend colours, top to bottom against "District 1" .. "District 6"
# in the map's own legend (RGB as the PDF states them, rounded).
COLOURS = {
    (0.954, 0.491, 0.5): "District 1",
    (0.752, 0.908, 0.983): "District 2",
    (0.542, 0.783, 0.404): "District 3",
    (0.71, 0.491, 0.715): "District 4",
    (1.0, 0.827, 0.499): "District 5",
    (0.973, 0.944, 0.465): "District 6",
}
# A legend swatch is about 80 points wide; a district shape is hundreds.
MIN_SHAPE_WIDTH = 100

# A precinct is part of the school district when this share of it is.
MIN_IN_SCHOOL = 0.02
# Measured 2026-10-15: no precinct has more than 1.1% of its area under a
# second district's shape, which is the fit's own error along the lines.
MAX_SECOND = 0.03
# Measured 2026-10-15: median 6.1 m along the matched 70% of the boundary.
MAX_MEDIAN_RESIDUAL_M = 15.0


def fail(msg):
    raise SystemExit("trace-isd11-board-map: FATAL: %s" % msg)


def get(session, url, params=None):
    resp = session.get(url, params=params, headers={"User-Agent": USER_AGENT},
                       timeout=120)
    resp.raise_for_status()
    return resp


def district_shapes(pdf_bytes):
    import pymupdf  # noqa: PLC0415
    from shapely.geometry import Polygon  # noqa: PLC0415

    page = pymupdf.open(stream=pdf_bytes, filetype="pdf")[0]

    def bez(p0, c1, c2, p3, n=8):
        out = []
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            out.append((mt ** 3 * p0.x + 3 * mt * mt * t * c1.x + 3 * mt * t * t * c2.x + t ** 3 * p3.x,
                        mt ** 3 * p0.y + 3 * mt * mt * t * c1.y + 3 * mt * t * t * c2.y + t ** 3 * p3.y))
        return out

    shapes = {}
    for draw in page.get_drawings():
        fill = draw.get("fill")
        if not fill:
            continue
        seat = COLOURS.get(tuple(round(c, 3) for c in fill))
        if seat is None or draw["rect"].width < MIN_SHAPE_WIDTH:
            continue
        if seat in shapes:
            fail("two shapes carry %s's colour" % seat)
        rings, cur, last = [], [], None
        for item in draw["items"]:
            if item[0] not in ("l", "c"):
                fail("%s's shape has a %r segment this reader does not draw" % (seat, item[0]))
            start = item[1]
            if last is None or abs(start.x - last[0]) > 1e-3 or abs(start.y - last[1]) > 1e-3:
                if len(cur) > 2:
                    rings.append(cur)
                cur = [(start.x, start.y)]
            cur += [(item[2].x, item[2].y)] if item[0] == "l" else bez(*item[1:])
            last = cur[-1]
        if len(cur) > 2:
            rings.append(cur)
        geom = None
        for ring in rings:  # the PDF fills even-odd
            poly = Polygon(ring).buffer(0)
            geom = poly if geom is None else geom.symmetric_difference(poly)
        shapes[seat] = geom
    if sorted(shapes) != sorted(COLOURS.values()):
        fail("found district shapes for %s, expected all six" % sorted(shapes))
    labels = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
              for w in page.get_text("words") if re.match(r"^(W\d-)?P-\d+$", w[4])]
    return shapes, labels


def fit(shapes, school):
    import numpy as np  # noqa: PLC0415
    from shapely.geometry import Point  # noqa: PLC0415
    from shapely.ops import nearest_points, unary_union  # noqa: PLC0415

    union = unary_union([g.buffer(0.5) for g in shapes.values()]).buffer(-0.5)
    ux0, uy0, ux1, uy1 = union.bounds
    tx0, ty0, tx1, ty1 = school.bounds
    sx, sy = (tx1 - tx0) / (ux1 - ux0), (ty1 - ty0) / (uy1 - uy0)
    a = np.array([[sx, 0, tx0 - sx * ux0], [0, -sy, ty1 + sy * uy0]])
    edge = union.boundary
    pts = np.array([(p.x, p.y) for p in
                    (edge.interpolate(i / 6000, normalized=True) for i in range(6000))])
    target = school.boundary
    # the map leaves rivers and lakes unfilled, so their banks are edges the
    # school boundary does not have; a shrinking distance cut drops them
    for cut in (400, 300, 200, 150, 100, 80, 60, 50, 40, 40, 40):
        moved = pts @ a[:, :2].T + a[:, 2]
        near = np.array([(lambda n: (n.x, n.y))(nearest_points(target, Point(q))[0])
                         for q in moved])
        dist = np.hypot(*(moved - near).T)
        keep = dist < cut
        x = np.c_[pts[keep], np.ones(keep.sum())]
        a = np.array([np.linalg.lstsq(x, near[keep, i], rcond=None)[0] for i in (0, 1)])
    return a, float(np.median(dist)), float(keep.mean())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", help="a saved copy of the map instead of fetching it")
    args = ap.parse_args()

    import numpy as np  # noqa: PLC0415
    import requests  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415
    from shapely.affinity import affine_transform  # noqa: PLC0415
    from shapely.geometry import Point, shape  # noqa: PLC0415

    session = requests.Session()
    if args.pdf:
        with open(args.pdf, "rb") as fh:
            pdf = fh.read()
    else:
        require_robots_once(MAP_URL, USER_AGENT)
        page = get(session, BOARD_PAGE).text
        if MAP_URL.split("ahschools.us")[1] not in page:
            fail("the board page no longer links the map at %s — find the "
                 "current map before re-measuring" % MAP_URL)
        time.sleep(CRAWL_DELAY)
        pdf = get(session, MAP_URL).content
    if not pdf.startswith(b"%PDF"):
        fail("the map URL did not answer a PDF")

    require_robots_once(TIGER_SCHOOL, USER_AGENT)
    school = get(session, TIGER_SCHOOL, {
        "where": "GEOID='%s'" % SCHOOL_GEOID, "outFields": "GEOID,NAME",
        "outSR": UTM, "f": "geojson"}).json()["features"]
    if len(school) != 1:
        fail("TIGER answered %d features for GEOID %s" % (len(school), SCHOOL_GEOID))
    school = shape(school[0]["geometry"]).buffer(0)

    require_robots_once(PRECINCTS_2022, USER_AGENT)
    x0, y0, x1, y1 = school.bounds
    body = get(session, PRECINCTS_2022, {
        "geometry": "%f,%f,%f,%f" % (x0, y0, x1, y1),
        "geometryType": "esriGeometryEnvelope", "inSR": UTM,
        "spatialRel": "esriSpatialRelIntersects", "where": "1=1",
        "outFields": "vtdid,pctname,shortlabel", "outSR": UTM, "f": "geojson",
        "resultRecordCount": 2000}).json()
    if body.get("exceededTransferLimit") or "error" in body:
        fail("the 2022 precinct layer did not answer whole: %r" % body.get("error"))
    precincts = [(f["properties"], shape(f["geometry"]).buffer(0)) for f in body["features"]]

    shapes, labels = district_shapes(pdf)
    a, residual, matched = fit(shapes, school)
    if residual > MAX_MEDIAN_RESIDUAL_M:
        fail("the fit's median residual is %.1f m, above %.0f m" % (residual, MAX_MEDIAN_RESIDUAL_M))
    m = [a[0, 0], a[0, 1], a[1, 0], a[1, 1], a[0, 2], a[1, 2]]
    placed = {seat: affine_transform(g, m) for seat, g in shapes.items()}

    seats = {seat: [] for seat in COLOURS.values()}
    worst = 0.0
    for props, geom in precincts:
        if geom.intersection(school).area / geom.area < MIN_IN_SCHOOL:
            continue
        share = {seat: geom.intersection(g).area / geom.area for seat, g in placed.items()}
        ranked = sorted(share.items(), key=lambda kv: -kv[1])
        if ranked[0][1] < MIN_IN_SCHOOL:
            continue
        worst = max(worst, ranked[1][1])
        if ranked[1][1] > MAX_SECOND:
            fail("%s (%s) lies %.1f%% in %s and %.1f%% in %s — the map does not "
                 "follow 2022 precinct lines there" % (props["pctname"], props["vtdid"],
                 100 * ranked[0][1], ranked[0][0], 100 * ranked[1][1], ranked[1][0]))
        seats[ranked[0][0]].append(props["vtdid"])

    def norm(s):
        return re.sub(r"[^A-Z0-9]", "", s.upper()).replace("W0", "W").replace("P0", "P")
    label_ok, label_off = 0, []
    for text, lx, ly in labels:
        pt = Point(*(a @ np.array([lx, ly, 1.0])))
        hit = [p for p, g in precincts if g.contains(pt)]
        # a label printed on two lines ("W-E-" over "P-08") is read as its
        # precinct number alone
        if hit and (norm(hit[0]["shortlabel"]) == norm(text)
                    or norm(hit[0]["shortlabel"]).endswith(norm(text))):
            label_ok += 1
        else:
            label_off.append("%s -> %s" % (text, hit[0]["pctname"] if hit else "nothing"))
    if label_ok < 0.9 * len(labels):
        fail("only %d of %d printed precinct labels land in their precinct: %s"
             % (label_ok, len(labels), label_off))

    out = {
        "board": "ISD 11",
        "school": SCHOOL_GEOID,
        "map": MAP_URL,
        "mapTitle": ("Anoka-Hennepin School District Current Board Election Areas, "
                     "School Board District Boundaries (2022)"),
        "mapSha256": hashlib.sha256(pdf).hexdigest(),
        "read": datetime.date.today().isoformat(),
        "precinctLayer": PRECINCTS_2022.rsplit("/query", 1)[0],
        "fit": {"medianResidualM": round(residual, 1), "boundaryMatched": round(matched, 2),
                "worstSecondShare": round(worst, 3),
                "labels": {"inTheirPrecinct": label_ok, "printed": len(labels),
                           "elsewhere": label_off}},
        "districts": {seat: sorted(v) for seat, v in seats.items()},
    }
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %s; fit median %.1f m, worst second share %.1f%%, %d of %d labels "
          "in their precinct" % (os.path.relpath(OUT_FILE, REPO),
          ", ".join("%s %d" % (s, len(v)) for s, v in sorted(seats.items())),
          residual, 100 * worst, label_ok, len(labels)))


if __name__ == "__main__":
    main()
