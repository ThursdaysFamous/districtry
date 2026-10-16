#!/usr/bin/env python3
"""Holland's six council wards — read out of the CITY's own map PDF.

Holland elects one council member from each of six wards and two at large. The
city runs no public map service, but its "Wards and Precincts" map is an ArcGIS
Pro export (created 2025-12-01) that keeps its layers and its georeferencing,
so the precinct polygons in it are real coordinates rather than a picture. The
"Precincts" layer carries eleven polygons, each labelled "<ward>-<precinct>"
on the sheet; dissolving them by ward gives the six wards.

WHY THE PDF AND NOT A COUNTY LAYER. Holland lies in two counties. Ottawa County's
precinct layer stops at the Allegan County line, so the part of the city south
of 32nd Street is missing from it (94.72% agreement with the state, measured
2026-10-15). The city's own map covers both, and it is the city's publication.

THE THREE GATES (shared with the other cities, mi_ward_common.py)
1. COMPOSITION. Eleven precincts, 2/1/2/2/2/2 across wards 1-6, both in the
   PDF's labels and in the state's own 2026 precinct fabric.
2. CURRENCY. The dissolve against the state's precincts, at 4,000 points
   inside either map, must agree on at least 99% (the "union" rule, which every
   older Michigan ward layer shipped under). Measured 2026-10-15: 99.25%.
3. TILING. The wards' Census 2020 population against the Census place's.

TERMS. The PDF states no licence or restriction anywhere on the sheet, and the
build refuses if the words "copyright", "licence" or "restricted" appear on it,
so a new edition with terms is read by a person before it is republished. That
is the line held for Walker, whose map PDF does state a restriction and is not
read.
"""

import argparse
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi_ward_common as wc  # noqa: E402

PDF_URL = "https://www.cityofholland.com/DocumentCenter/View/605/Wards-and-Precincts"

CFG = {
    "name": "Holland",
    "slug": "holland",
    "out_file": "mi-holland-wards.json",
    "place_geoid": "2638640",
    "place_name": "Holland city",
    # Holland city sits in Ottawa (139) and Allegan (005). The name alone also
    # matches nothing else in those two counties' fabric (the townships carry
    # "Holland Township"), and the county list keeps it that way.
    "state_where": "Jurisdiction_Name = 'Holland' AND COUNTYFIPS IN ('139','005')",
    "expect_wards": ("1", "2", "3", "4", "5", "6"),
    "expect_state": {"1": 2, "2": 1, "3": 2, "4": 2, "5": 2, "6": 2},
    "agreement": "union",
    "robots_urls": (PDF_URL,),
    "min_blocks": 500,
}
EXPECT_SOURCE = {"1": 2, "2": 1, "3": 2, "4": 2, "5": 2, "6": 2}
PRECINCT_LAYER = "Precincts"
LABEL = re.compile(r"(\d)-(\d{1,2})")
TERMS = re.compile(r"(?i)copyright|licen[cs]e|restrict")


def read_pdf(path):
    import pymupdf
    from shapely.geometry import Point, Polygon, mapping
    from shapely.ops import transform

    doc = pymupdf.open(path)
    page = doc[0]
    sheet = page.get_text()
    if TERMS.search(sheet):
        wc.fail(CFG, "the map now states terms (%r) — read them before republishing"
                % TERMS.search(sheet).group(0))
    project, resid = wc.geopdf_projector(doc)
    print("  georeference: worst control-point residual %.3f m" % resid)
    if resid > wc.MAX_GEOREF_RESIDUAL_M:
        wc.fail(CFG, "the PDF's control points disagree by %.2f m" % resid)

    labels = [(m.group(1), m.group(2), Point(c))
              for t, c, _ in wc.geopdf_texts(page)
              for m in [LABEL.fullmatch(t)] if m]
    precincts = []
    for d in page.get_drawings():
        if d.get("layer") != PRECINCT_LAYER:
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
        inside = sorted({(w, p) for w, p, pt in labels if shape.contains(pt)})
        if len(inside) != 1:
            wc.fail(CFG, "a precinct polygon holds %d ward-precinct labels (%s), expected one"
                    % (len(inside), inside))
        w, p = inside[0]
        geo = transform(lambda x, y, z=None: project(x, y), shape)
        precincts.append({"type": "Feature", "properties": {"WARD": w, "PRECINCT": p},
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
            print("fetching the city's Wards and Precincts map…")
            path = os.path.join(tmp, "holland.pdf")
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
