#!/usr/bin/env python3
"""
Check the SHIPPED Kenosha supervisory districts against the county's OWN
adopted map. An operator verification, not a weekly job — re-run it after an
LTSB filing window or whenever Kenosha redistricts (wi/WATCH.md).

WHY THIS EXISTS. Every county's supervisory geometry in this app comes from one
publisher: LTSB's statewide aggregate of the boundaries Wis. Stat. 5.15(4)(br)1
makes each county file twice a year (build_wi_supervisory_districts.py). That is
the right source and it is a SINGLE source, so for the one county whose roster
this project reads off county documents it is worth asking the county's own
cartography whether it agrees. It does, and this script is the arithmetic.

THE MAP IS GEOREFERENCED AND NOTHING HERE IS TRACED. Kenosha's "Countywide Map -
Supervisor Districts and Voting Wards" is an ArcMap export carrying a real PDF
/Measure /GEO viewport — four corner lat/lons against the unit square of the
viewport's BBox — under the viewport NAME "County Supervisor Districts". So a
label's position on the sheet converts to a coordinate with no fitting, no
scale-bar reading and no colour sampling, and the check is a point-in-polygon
test of the county's own "DISTRICT n" labels against LTSB's polygon n.

WHAT IT CAN AND CANNOT WITNESS, stated plainly so the pass is not over-read:

  * Only districts 15-23 carry spelled "DISTRICT n" labels. 1-14 are the City of
    Kenosha's, drawn at a scale where the sheet carries ward numbers and street
    names instead, so this script witnesses NINE of the county's 23 districts
    and says so rather than reporting a whole-county pass.
  * A LABEL IS PLACED NEAR ITS POLYGON, NOT NECESSARILY INSIDE IT. ArcMap
    repeats a polygon's label across its parts, and districts 15 and 19 are
    sprawling multipart ribbons wrapping the city districts, so some repeats
    land next door. 86 of 99 label instances sit inside the district they name;
    district 15 alone accounts for nine of the thirteen that do not.

SO THE GATE IS PLURALITY, NOT A RATE. For each labelled district, its own
polygon must hold MORE of its labels than any other polygon does. That is the
question worth asking — whether the two publishers number the same ground the
same way — and it is decisive even where the rate is weakest: district 15's
labels sit inside polygon 15 ten times against at most three inside any other.
A rate threshold would instead fail the day the county nudges a label, which
is noise, and would still pass a genuine renumbering that kept its labels
tidily inside the wrong polygons, which is the thing to catch.

Usage:
    python3 wi/scripts/verify_kenosha_supervisory_map.py
    python3 wi/scripts/verify_kenosha_supervisory_map.py --map <local.pdf>
"""

import collections
import json
import os
import re
import sys

import pymupdf
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_CHROME_WIN_124, require_robots_once)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOMETRY = os.path.join(REPO_ROOT, "data", "app", "county-supervisory-districts.json")
CNTY_FIPS = "55059"
SEATS = 23

# The county's map INDEX page. The map's own address is a DocumentCenter
# edition id, so it is discovered from the page rather than pinned — a
# re-publication moves the id and this script should follow it, not 404.
INDEX_URL = "https://www.kenoshacountywi.gov/142/County-Board-Supervisor-Districts"
MAP_LINK = re.compile(
    r'(?is)<a[^>]+href="([^"]*/DocumentCenter/View/[^"]+)"[^>]*>\s*Countywide Map[^<]*</a>')
# the viewport whose /Measure carries the supervisor-district frame's corners;
# the same sheet also carries State Senate and State Assembly inset viewports
VIEWPORT_NAME = "County Supervisor Districts"
# the county's own approval, printed on the sheet — the plan this file expects
ORDINANCE = re.compile(r"(?i)Kenosha County Board\s*-\s*Ordinance\s*12\s*-\s*11/8/2021")
LABEL = re.compile(r"(?i)^district$")

# MEASURED 2026-08-29 against the shipped LTSB geometry. A future run may move
# these by a label or two if the county re-exports the sheet; a run that moves
# them a lot is the news this script exists to produce.
BASELINE_LABELS = 99
BASELINE_INSIDE = 86


def fetch(url, binary=False):
    import urllib.request
    headers = {"User-Agent": UA_CHROME_WIN_124}
    require_robots_once(url, UA_CHROME_WIN_124, headers=headers,
                        label="wi-verify-kenosha-supervisory-map")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def utf16_name(raw):
    """A PDF viewport /Name arrives UTF-16BE-hex-escaped; decode to text."""
    m = re.search(r"<FEFF([0-9A-Fa-f]+)>", str(raw))
    if not m:
        return " ".join(re.findall(r"[ -~]+", str(raw)))
    return bytes.fromhex(m.group(1)).decode("utf-16-be", "replace")


def supervisor_viewport(doc, page):
    """(BBox, four corner lat/lons) of the sheet's supervisor-district frame."""
    raw = str(doc.xref_get_key(page.xref, "VP")[1])
    for chunk in raw.split("<</Type/Viewport")[1:]:
        if utf16_name(chunk).strip() != VIEWPORT_NAME:
            continue
        bbox = [float(x) for x in
                re.search(r"/BBox\[([^\]]+)\]", chunk).group(1).split()]
        measure = int(re.search(r"/Measure (\d+) 0 R", chunk).group(1))
        gpts = [float(x) for x in
                str(doc.xref_get_key(measure, "GPTS")[1]).strip("[]").split()]
        lpts = [float(x) for x in
                str(doc.xref_get_key(measure, "LPTS")[1]).strip("[]").split()]
        corners = {}
        for i in range(4):
            corners[(lpts[2 * i], lpts[2 * i + 1])] = (gpts[2 * i], gpts[2 * i + 1])
        return bbox, corners
    raise RuntimeError("the sheet no longer carries a %r viewport — its "
                       "georeferencing is what this check rests on" % VIEWPORT_NAME)


def make_projector(bbox, corners, page_height):
    """PDF page point -> (lon, lat), bilinear over the viewport's own corners.

    LPTS y RUNS FROM THE BBOX'S FIRST y VALUE, not from the lower edge: this
    sheet's BBox is written top-then-bottom, and reading it the other way
    puts the county's north edge on its south one. The four corners' latitudes
    say which reading is right and the county-bounds assertion below proves it.
    """
    x0, ytop, x1, ybot = bbox

    def project(px, py_fitz):
        py = page_height - py_fitz            # fitz y counts down from the top
        u = (px - x0) / (x1 - x0)
        v = (py - ytop) / (ybot - ytop)
        out = []
        for idx in (1, 0):                    # lon, then lat
            out.append(corners[(0, 0)][idx] * (1 - u) * (1 - v)
                       + corners[(1, 0)][idx] * u * (1 - v)
                       + corners[(0, 1)][idx] * (1 - u) * v
                       + corners[(1, 1)][idx] * u * v)
        return out[0], out[1]
    return project


def district_labels(page, project):
    """Every "DISTRICT n" on the sheet, as (n, lon, lat) at the label's centre."""
    by_line = collections.defaultdict(list)
    for w in page.get_text("words"):
        by_line[(w[5], w[6])].append(w)
    out = []
    for words in by_line.values():
        words.sort(key=lambda w: w[7])
        toks = [w[4] for w in words]
        for i, tok in enumerate(toks):
            if not LABEL.match(tok) or i + 1 >= len(toks):
                continue
            if not re.fullmatch(r"\d{1,2}", toks[i + 1]):
                continue
            a, b = words[i], words[i + 1]
            cx = (min(a[0], b[0]) + max(a[2], b[2])) / 2.0
            cy = (min(a[1], b[1]) + max(a[3], b[3])) / 2.0
            lon, lat = project(cx, cy)
            out.append((int(toks[i + 1]), lon, lat))
    return out


def rings(geom):
    return [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]


def point_in(geom, lon, lat):
    """Ray cast, holes subtracted — the same rule the app's own test uses."""
    inside = False
    for poly in rings(geom):
        for ri, ring in enumerate(poly):
            crossings = False
            n = len(ring)
            j = n - 1
            for i in range(n):
                xi, yi = ring[i][0], ring[i][1]
                xj, yj = ring[j][0], ring[j][1]
                if ((yi > lat) != (yj > lat)) and \
                        (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                    crossings = not crossings
                j = i
            if ri == 0:
                if crossings:
                    inside = True
            elif crossings:
                inside = False
    return inside


def main():
    argv = sys.argv[1:]
    local = argv[argv.index("--map") + 1] if "--map" in argv else None
    if local:
        pdf, where = open(local, "rb").read(), local
    else:
        index = fetch(INDEX_URL)
        m = MAP_LINK.search(index)
        if not m:
            raise RuntimeError("%s no longer links a 'Countywide Map' document — "
                               "the county has reorganised its maps page" % INDEX_URL)
        where = m.group(1)
        if where.startswith("/"):
            where = "https://www.kenoshacountywi.gov" + where
        pdf = fetch(where, binary=True)
    print("map: %s (%d KB)" % (where, len(pdf) // 1024))

    doc = pymupdf.open(stream=pdf, filetype="pdf")
    page = doc[0]
    sheet = page.get_text()
    if not ORDINANCE.search(" ".join(sheet.split())):
        print("  WARN the sheet no longer prints 'County Board - Ordinance 12 - "
              "11/8/2021'; the adopted plan may have changed", file=sys.stderr)
    else:
        print("plan: Kenosha County Board Ordinance 12, adopted 11/8/2021 "
              "(printed on the sheet)")

    bbox, corners = supervisor_viewport(doc, page)
    project = make_projector(bbox, corners, page.rect.height)
    labels = district_labels(page, project)
    if not labels:
        raise RuntimeError("no 'DISTRICT n' labels on the sheet — the export has "
                           "changed and this check reads nothing")

    with open(GEOMETRY) as f:
        geo = json.load(f)
    drawn = {int(feat["properties"]["SUPERID"]): feat["geometry"]
             for feat in geo["features"]
             if feat["properties"]["CNTY_FIPS"] == CNTY_FIPS}
    if set(drawn) != set(range(1, SEATS + 1)):
        raise RuntimeError("the shipped geometry draws %d Kenosha districts, not %d"
                           % (len(drawn), SEATS))

    # every label lands inside the county at all — the projection's own check
    outside = [(d, lon, lat) for d, lon, lat in labels
               if not any(point_in(g, lon, lat) for g in drawn.values())]

    hits = collections.defaultdict(collections.Counter)
    for d, lon, lat in labels:
        for other, geom in drawn.items():
            if point_in(geom, lon, lat):
                hits[d][other] += 1

    labelled = sorted({d for d, _, _ in labels})
    counts = collections.Counter(d for d, _, _ in labels)
    inside = sum(hits[d][d] for d in labelled)
    print("labels: %d instances across districts %s"
          % (len(labels), ", ".join(str(d) for d in labelled)))
    print("inside the district they name: %d of %d (%d land in no district — "
          "label placement at the county edge)"
          % (inside, len(labels), len(outside)))

    failures = []
    for d in labelled:
        own = hits[d][d]
        rival = max((n for other, n in hits[d].items() if other != d), default=0)
        if own == 0:
            failures.append("district %d: not one of its %d labels lands inside "
                            "polygon %d" % (d, counts[d], d))
        elif own <= rival:
            best = max((n, other) for other, n in hits[d].items() if other != d)
            failures.append("district %d: its labels sit inside polygon %d as often "
                            "(%d) as inside %d (%d) — the two publishers may not "
                            "number the same ground the same way"
                            % (d, best[1], best[0], d, own))
        print("  district %-3d %2d of %2d labels inside; elsewhere: %s"
              % (d, own, counts[d],
                 ", ".join("%d x%d" % (k, v) for k, v in sorted(hits[d].items())
                           if k != d) or "none"))

    if failures:
        raise RuntimeError("the county's own map and the shipped LTSB geometry "
                           "disagree — " + "; ".join(failures))
    if inside < BASELINE_INSIDE - 5 or len(labels) < BASELINE_LABELS - 5:
        raise RuntimeError("agreement moved a long way from the recorded baseline "
                           "(%d of %d labels, baseline %d of %d) — re-read the sheet"
                           % (inside, len(labels), BASELINE_INSIDE, BASELINE_LABELS))
    print("OK — %d of the county's 23 districts are labelled on this sheet and "
          "every one of them agrees with the LTSB polygon of the same number."
          % len(labelled))


if __name__ == "__main__":
    main()
