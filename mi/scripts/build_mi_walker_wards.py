#!/usr/bin/env python3
"""Walker's three commission wards — read out of the CITY's own precinct map PDF.

Walker elects two commissioners from each of three wards, and a mayor at large.
The city runs no public map service. Its "2025 Precinct Map" is an ArcMap
export (created 2025-05-08) that keeps its layers and its georeferencing, so
the six precinct polygons in its "Wards & Precincts" layer are real
coordinates rather than a picture. Each is labelled "Ward N" and "Precinct M"
on the sheet; dissolving them by ward gives the three wards. The city links
the same file twice (DocumentCenter 3542 and 4311 are the same bytes); the
build reads 4311, the one its Elections page calls the 2025 precinct map.

THE SHEET STATES TERMS, AND THE OPERATOR RULED ON THEM. Its notice reads, in
full: "This map does not represent a legal document. It is intended to serve
as an aid in graphic representation only. Information shown on this map is
not warranted for accuracy and should be verified through other means. Any
duplication is restricted under copyright laws and the Enhanced Access to
Public Records Act, PA 462 of 1996, as amended." Held on 2026-10-15 under the
licence precedent (a stated restriction blocks); on 2026-10-16 the operator
chose to draw Walker's wards anyway, treating the line as a general notice.
The notice is quoted on the card, and the build refuses if its text changes,
so a new edition's terms are read by a person before it is republished.

THE THREE GATES (shared with the other cities, mi_ward_common.py)
1. COMPOSITION. Six precincts, two in each of wards 1-3, both in the map's
   labels and in the state's own 2026 precinct fabric.
2. CURRENCY. The dissolve against the state's precincts at 4,000 points
   inside either map, on the stricter "union" rule. Measured 2026-10-16:
   100.000% where both maps draw a ward, 99.650% over either map.
3. TILING. The wards' Census 2020 population against the Census place's.
   Measured 2026-10-16: 25,132 in both, two edge blocks holding nobody.
"""

import argparse
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi_ward_common as wc  # noqa: E402

PDF_URL = "https://www.walker.city/DocumentCenter/View/4311/2025-Precinct-Map-Interactive"

CFG = {
    "name": "Walker",
    "slug": "walker",
    "out_file": "mi-walker-wards.json",
    "place_geoid": "2682960",
    "place_name": "Walker city",
    "state_where": "Jurisdiction_Name = 'Walker' AND COUNTYFIPS = '081'",
    "expect_wards": ("1", "2", "3"),
    "expect_state": {"1": 2, "2": 2, "3": 2},
    "agreement": "union",
    "robots_urls": (PDF_URL,),
    "min_blocks": 300,
}
EXPECT_SOURCE = {"1": 2, "2": 2, "3": 2}
WARD_LAYER = "Wards & Precincts"
EXPECT_NOTICE = ("This map does not represent a legal document. It is intended to serve "
                 "as an aid in graphic representation only. Information shown on this map "
                 "is not warranted for accuracy and should be verified through other means. "
                 "Any duplication is restricted under copyright laws and the Enhanced Access "
                 "to Public Records Act, PA 462 of 1996, as amended.")


def notice(page):
    for b in page.get_text("blocks"):
        if "duplication" in b[4]:
            return " ".join(b[4].split())
    return None


def read_pdf(path):
    import pymupdf
    from shapely.geometry import Point, Polygon, mapping
    from shapely.ops import transform

    doc = pymupdf.open(path)
    page = doc[0]
    terms = notice(page)
    if terms != EXPECT_NOTICE:
        wc.fail(CFG, "the map's notice now reads %r — read it before republishing" % terms)
    project, resid = wc.geopdf_projector(doc)
    print("  georeference: worst control-point residual %.3f m" % resid)
    if resid > wc.MAX_GEOREF_RESIDUAL_M:
        wc.fail(CFG, "the PDF's control points disagree by %.2f m" % resid)

    texts = [(t, Point(c)) for t, c, _ in wc.geopdf_texts(page)]
    wards_t = [(re.fullmatch(r"Ward (\d)", t).group(1), pt) for t, pt in texts
               if re.fullmatch(r"Ward (\d)", t)]
    precs_t = [(re.fullmatch(r"Precinct (\d)", t).group(1), pt) for t, pt in texts
               if re.fullmatch(r"Precinct (\d)", t)]
    precincts = []
    for d in page.get_drawings():
        if d.get("layer") != WARD_LAYER or not d.get("fill"):
            continue
        shape = None
        for sp in wc.geopdf_subpaths(d):
            if len(sp) < 4:
                continue
            p = Polygon(sp).buffer(0)
            # Even-odd within one drawing: an inner ring is a hole.
            shape = p if shape is None else shape.symmetric_difference(p)
        if shape is None or shape.is_empty:
            continue
        w = sorted({n for n, pt in wards_t if shape.contains(pt)})
        p = sorted({n for n, pt in precs_t if shape.contains(pt)})
        if len(w) != 1 or len(p) != 1:
            wc.fail(CFG, "a precinct polygon holds ward labels %s and precinct labels %s, "
                         "expected one of each" % (w, p))
        geo = transform(lambda x, y, z=None: project(x, y), shape)
        precincts.append({"type": "Feature", "properties": {"WARD": w[0], "PRECINCT": p[0]},
                          "geometry": mapping(geo)})
    return precincts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    ap.add_argument("--pdf", help="read this local copy instead of fetching the city's")
    args = ap.parse_args()
    if args.check:
        wc.check_main(CFG)
        return

    print("reading robots.txt for every host this build fetches…")
    wc.require_robots(CFG)
    with tempfile.TemporaryDirectory() as tmp:
        path = args.pdf
        if not path:
            print("fetching the city's 2025 precinct map…")
            path = os.path.join(tmp, "walker.pdf")
            with open(path, "wb") as f:
                f.write(wc.curl_bytes(PDF_URL))
        precincts = read_pdf(path)
    counts = wc.counts_by(precincts, lambda p: p["WARD"])
    print("  map: %d precincts, per ward %s" % (len(precincts), counts))
    if counts != EXPECT_SOURCE:
        wc.fail(CFG, "the map assigns %s precincts per ward, expected %s"
                % (counts, EXPECT_SOURCE))
    key = lambda p: wc.ward_number(p.get("WARD"))  # noqa: E731
    wards = wc.dissolve(CFG, precincts, key)
    wc.gate_and_write(CFG, wards, key)


if __name__ == "__main__":
    main()
