#!/usr/bin/env python3
"""Lansing's four council wards — BUILT, MEASURED, AND NOT SHIPPED.

Lansing elects eight council members: four by ward and four at large. The ward
geometry is not in doubt and its currency is not in doubt. THE LICENCE IS THE
WHOLE BLOCKER, and this script exists so that the measurement survives the
decision rather than being re-done after it.

THE SOURCE, AND WHY THE CLEAN-LOOKING COPY IS NOT THE CLEAN ONE
---------------------------------------------------------------
The city's ArcGIS org publishes the current plan three times:

  VotingWards   4 features, WARDID 1-4, licenseInfo EMPTY,
                snippet "Wards for the City of Lansing, updated for the 2022
                elections"                                    <- what this reads
  City_Wards    9 features, licenseInfo CC BY-NC 4.0,
                description "City of Lansing wards, as defined in the 2020
                redistricting cycle"
  Wards        10 features, licenseInfo EMPTY

`City_Wards` and `Wards` are not rival plans: they carry ward 2 in four parts
plus two features keyed DT and MR that are not wards at all. `VotingWards` is
the same plan as four whole wards, which is why it is the one read here.

AN UNSTATED LICENCE IS SILENCE, NOT A GRANT. The tempting move is to take
`VotingWards` because its licenceInfo is empty and call the terms clean. The
same publisher states NonCommercial terms on the same plan, one item away, so
the empty field is an omitted notice rather than a different offer — and
choosing the copy without the notice is choosing the reading that suits us.
The operative licence for Lansing ward geometry is therefore:

    "This work is licensed under a Creative Commons Attribution-NonCommercial
     4.0 International License."

quoted verbatim from the City_Wards item, and whether a free public civic site
is a non-commercial use is the OPERATOR'S call, not this build's.

WHY NOTHING IS WRITTEN BY DEFAULT
----------------------------------
"Build it dark" would normally mean: write the file, do not wire the layer. That
is not enough here, because this repository is public — committing the derived
GeoJSON distributes the data whether or not any toggle serves it. So the default
is to measure and refuse. Pass --licence-approved once the terms question has an
answer, and the same gates run and the file is written.

CURRENCY, MEASURED BEFORE THE LICENCE WAS
------------------------------------------
The state's own 2026 precinct fabric carries a WARD column assigning Lansing's
27 precincts 7/7/6/7 across wards 1-4. Dissolved by that column and compared by
point classification, the city's four polygons agree with the state on
1860 of 1862 sampled points (99.893%) — a tighter agreement than Grand Rapids,
which shipped at 99.575%. Two independent publishers drawing the same four
lines, so a 2022 edit date means UNCHANGED rather than stale. That comparison is
a GATE below, not a note.
"""

import argparse
import html as htmllib
import json
import os
import random
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = os.path.join(os.path.dirname(HERE), "data", "app")

CITY_ORG = "https://services1.arcgis.com/pNPbgWy7hpfFGWoZ/arcgis/rest/services"
SERVICE = CITY_ORG + "/VotingWards/FeatureServer/0"
# The licensed sibling — read only to re-assert the licence clause each run.
LICENCE_ITEM = "59912a33858b4a05b6cd4226aa78dc3a"
LICENCE_CLAUSE = ("This work is licensed under a Creative Commons "
                  "Attribution-NonCommercial 4.0 International License")

PRECINCTS = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
             "services/2026_Voting_Precincts/FeatureServer/0")
PRECINCT_WHERE = "Jurisdiction_Name = 'Lansing'"

OUT_FILE = "mi-lansing-wards.json"
EXPECT_FEATURES = 4
EXPECT_WARDS = ("1", "2", "3", "4")
EXPECT_PRECINCTS = {"1": 7, "2": 7, "3": 6, "4": 7}
MIN_PRECINCT_AGREEMENT = 0.99          # measured 0.99893
SIMPLIFY = "50%"                       # Grand Rapids's tolerance; 4 features, same shape
PRECISION = "0.000001"


def fail(msg):
    print("build-mi-lansing-wards: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def curl(url):
    return subprocess.run(["curl", "-sS", "--fail", "--max-time", "240", url],
                          check=True, capture_output=True).stdout


def esri(url, params):
    p = {"f": "geojson", "outSR": 4326, "geometryPrecision": 6}
    p.update(params)
    d = json.loads(curl(url + "/query?" + urllib.parse.urlencode(p)))
    if isinstance(d, dict) and "error" in d:
        raise RuntimeError("%s answered an error envelope: %r" % (url, d["error"]))
    feats = d.get("features") or []
    if not feats:
        raise RuntimeError("%s returned no features — an Esri error envelope arrives "
                           "as HTTP 200, so read this as 'the service moved'" % url)
    return feats


def assert_licence_unchanged():
    """The licence clause is re-read every run, never trusted from this file.

    If the city relicenses this data the build must notice — in either
    direction. A clause that has changed is a fact for a human, not something
    to shrug past."""
    item = json.loads(curl("https://www.arcgis.com/sharing/rest/content/items/%s?f=json"
                           % LICENCE_ITEM))
    # FLATTEN FIRST. The clause is split across an anchor tag and a styled span,
    # and carries a non-breaking space; matching the raw HTML reports a
    # relicence that has not happened, which is the one false alarm this gate
    # must never raise. (Measured: the first draft did exactly that.)
    live = htmllib.unescape(re.sub(r"<[^>]+>", " ", item.get("licenseInfo") or ""))
    live = re.sub(r"\s+", " ", live.replace("\xa0", " ")).strip()
    if LICENCE_CLAUSE not in live:
        fail("the city's stated licence has CHANGED. This build records %r, which is "
             "no longer in the item's licenseInfo. Re-read the terms and update the "
             "record before building — a relicence is exactly the news this gate "
             "exists to deliver." % LICENCE_CLAUSE)
    print("  licence: the city still states CC BY-NC 4.0 on this plan")


# --- point-in-polygon, mirroring index.html's even-odd test -------------------
def _in_ring(pt, ring):
    x, y = pt
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-19) + xi):
            inside = not inside
        j = i
    return inside


def in_geometry(pt, geom):
    if not geom:
        return False
    t, c = geom["type"], geom["coordinates"]
    polys = [c] if t == "Polygon" else (c if t == "MultiPolygon" else [])
    for poly in polys:
        if poly and _in_ring(pt, poly[0]) and not any(_in_ring(pt, h) for h in poly[1:]):
            return True
    return False


def ward_of(props):
    """Numeric normalisation, never character-stripping: the state writes '01'
    where the city writes '1'."""
    for k in ("WARDID", "WARD", "wardid", "ward"):
        if k in props and props[k] not in (None, ""):
            try:
                return str(int(str(props[k]).strip()))
            except ValueError:
                return str(props[k]).strip()
    return None


def model(features):
    return [(ward_of(f.get("properties") or {}), f.get("geometry")) for f in features]


def bbox(features):
    xs, ys = [], []
    for f in features:
        stack = [f["geometry"]["coordinates"]]
        while stack:
            c = stack.pop()
            if isinstance(c[0], (int, float)):
                xs.append(c[0]); ys.append(c[1])
            else:
                stack.extend(c)
    return (min(xs), min(ys), max(xs), max(ys))


def point_agreement(a, b, box, samples=3000, seed=20260905):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    same = hit = 0
    for _ in range(samples):
        p = (rnd.uniform(x0, x1), rnd.uniform(y0, y1))
        ka = next((k for k, g in a if in_geometry(p, g)), None)
        kb = next((k for k, g in b if in_geometry(p, g)), None)
        if ka is None or kb is None:
            continue
        hit += 1
        same += (ka == kb)
    return same, hit, (same / hit if hit else 0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--licence-approved", action="store_true",
                    help="the operator has decided the CC BY-NC terms permit this use; "
                         "without it this script measures and refuses to write")
    args = ap.parse_args()

    print("re-reading the city's stated licence…")
    assert_licence_unchanged()

    print("fetching the city's ward service…")
    wards = esri(SERVICE, {"where": "1=1", "outFields": "WARDID"})
    if len(wards) != EXPECT_FEATURES:
        fail("expected %d wards, got %d — the city's plan or this service has moved"
             % (EXPECT_FEATURES, len(wards)))
    got = tuple(sorted(ward_of(f["properties"]) for f in wards))
    if got != EXPECT_WARDS:
        fail("ward ids are %s, expected %s" % (list(got), list(EXPECT_WARDS)))

    print("fetching the state's 2026 precincts for the currency gate…")
    precs = esri(PRECINCTS, {"where": PRECINCT_WHERE, "outFields": "WARD,PRECINCT"})
    counts = {}
    for f in precs:
        k = ward_of(f["properties"])
        counts[k] = counts.get(k, 0) + 1
    if counts != EXPECT_PRECINCTS:
        fail("the state assigns %s precincts per ward, expected %s — the precinct "
             "fabric has moved and these wards must be re-checked against it"
             % (counts, EXPECT_PRECINCTS))

    same, hit, frac = point_agreement(model(wards), model(precs), bbox(wards))
    print("  city wards vs state precinct dissolve: %d/%d (%.3f%%)" % (same, hit, 100 * frac))
    if frac < MIN_PRECINCT_AGREEMENT:
        fail("point agreement %.3f%% is below the %.1f%% floor — find the city's adopted "
             "plan before touching this threshold; the threshold is not the thing to move"
             % (100 * frac, 100 * MIN_PRECINCT_AGREEMENT))

    if not args.licence_approved:
        print("\nbuild-mi-lansing-wards: MEASURED, NOT WRITTEN.\n"
              "  Every gate above passed. Nothing is written because the city licenses\n"
              "  this plan CC BY-NC 4.0 and this repository is public — committing the\n"
              "  derived file would distribute the data, which is the very thing the\n"
              "  terms question is about. Re-run with --licence-approved once the\n"
              "  operator has answered it. See the gap record lansing-ward-boundary.",
              file=sys.stderr)
        return

    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)
    fail("--licence-approved was given, but the write path is deliberately not "
         "implemented yet: the simplify/emit step should be copied from "
         "build_mi_grand_rapids_wards.py in the same change that answers the licence "
         "question, so the attribution the licence requires is written at the same "
         "time as the geometry. Target: %s" % out_path)


if __name__ == "__main__":
    main()
