#!/usr/bin/env python3
"""
Build data/app/mcdonough-board-districts.json by dissolving the county's own
27 voting precincts according to the composition the County Board publishes.

WHY DERIVE WHEN THE COUNTY PUBLISHES A BOARD-DISTRICT LAYER. It does — layer 3
of the WIU GIS Center's `precinct_map`, and unlike the precinct layer it
exports geometry cleanly. It is not used as the source because its ATTRIBUTE
TABLE is visibly corrupt:

    County Board District 2   Population 20045   Acres 7025.39254229
    County Board District 3   Population 20045   Acres 7025.39254229
    County Board District 1   Population None    Acres None

Two districts carrying an identical population AND an identical acreage to
eight decimal places is a copy-paste, not a measurement; the third has neither.
The totals are not McDonough's either — the county's 2020 population is about
27,000, and these two alone sum to 40,090. A table that wrong about its own
districts is not a table to take boundaries from on trust.

So the boundary is DERIVED from the precincts, the way Grundy's and LaSalle's
are, and the county's own polygons are used as a CROSS-CHECK rather than as
the source. Both have to agree before this file is written.

THE COMPOSITION IS THE COUNTY'S OWN, printed under each district heading on
http://mcg.mcdonough.il.us/members.html — the same page that carries the 21
members. Boundary and roster in one document is the tightest binding available
(the Marshall posture), because a composition change and a membership change
arrive together.

The composition is a PERFECT PARTITION of the precinct layer, verified before
anything is dissolved: 4 + 12 + 11 = 27 precincts, every precinct named exactly
once, nothing in the layer unnamed and nothing named that the layer lacks. That
bijection is the proof this derivation is exact — unlike a township dissolve,
there is no split unit anywhere, because the county draws its districts on
precinct lines and Macomb city is divided by numbered city precincts rather
than cut.

Regenerate when the county reapportions, and re-read the page first.

Usage:
    python3 scripts/build_mcdonough_board_districts.py
    python3 scripts/build_mcdonough_board_districts.py --check
"""

import argparse
import json
import os
import sys
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRECINCTS_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "mcdonough-precincts.json")
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "mcdonough-board-districts.json")

MEMBERS_PAGE = "http://mcg.mcdonough.il.us/members.html"
COUNTY_BOARD_LAYER = ("https://gis.wiu.edu/arcgis/rest/services/precinct_map/"
                      "MapServer/3")
REQUEST_TIMEOUT = 120
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}

# Transcribed verbatim from the district headings on MEMBERS_PAGE, read
# 2026-08-03. The page writes townships and Macomb city precincts in one list
# ("Townships: Emmet. Macomb City #1, #2, and #3"); the names below are the
# PRECINCT-layer names those refer to, which is the only form that can be
# joined. "MC n" is the layer's name for Macomb City precinct n.
DISTRICTS = {
    "1": ["Emmet", "MC 1", "MC 2", "MC 3"],
    "2": ["Blandinsville", "Bushnell 1", "Bushnell 2", "Hire", "Macomb",
          "Mound", "New Salem", "Prairie City", "Sciota", "Walnut Grove",
          "MC 4", "MC 5"],
    "3": ["Bethel", "Chalmers", "Colchester", "Eldorado", "Industry",
          "LaMoine", "Scotland", "Tennessee", "MC 6", "MC 7", "MC 8"],
}
# Seven members from each of the three districts. Printed on the same page.
SEATS_PER_DISTRICT = 7

COORD_PRECISION = 6
# The derived districts and the county's own polygons must agree this closely.
# Not 100%: the two are built from different source geometry (the county's
# board layer is its own polygon set, not a dissolve of these precincts), so
# hairline disagreement along shared edges is expected and meaningless. A real
# disagreement — a precinct assigned to the wrong district — moves whole square
# miles and would fail this by a wide margin.
MIN_CROSSCHECK_IOU = 0.97


def load_precincts():
    if not os.path.exists(PRECINCTS_PATH):
        raise RuntimeError("%s is missing — run build_mcdonough_precincts.py first"
                           % PRECINCTS_PATH)
    with open(PRECINCTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    by_name = {}
    for feature in data.get("features") or []:
        by_name[feature["properties"]["name"]] = feature
    return by_name


def verify_partition(by_name):
    """The composition must name every precinct exactly once. Hard failure."""
    named = [p for names in DISTRICTS.values() for p in names]
    layer = set(by_name)
    problems = []
    if len(named) != len(set(named)):
        dupes = sorted({p for p in named if named.count(p) > 1})
        problems.append("named in more than one district: %s" % ", ".join(dupes))
    missing = sorted(set(named) - layer)
    if missing:
        problems.append("named by the county but absent from the precinct layer: %s"
                        % ", ".join(missing))
    extra = sorted(layer - set(named))
    if extra:
        problems.append("in the precinct layer but assigned to no district: %s"
                        % ", ".join(extra))
    if problems:
        raise RuntimeError("the published composition is not a partition of the "
                           "precinct layer — " + "; ".join(problems) +
                           ". Re-read %s before rebuilding." % MEMBERS_PAGE)
    return len(named)


def dissolve(features, warnings):
    """Union a district's precincts, repairing each one FIRST.

    Repairing only the result is not enough here: at least one of the county's
    precinct polygons is self-invalid (a ring edge is missing near Macomb at
    -90.7144, 40.4556), and unary_union raises on invalid INPUT rather than
    quietly producing a wrong answer. Each polygon is therefore made valid on
    the way in, which closes the defective ring without moving any boundary a
    valid neighbour shares.
    """
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    parts = []
    for feature in features:
        geom = shape(feature["geometry"])
        if not geom.is_valid:
            fixed = geom.buffer(0)
            # A repair that changes the area by more than a rounding artefact is
            # not a repair — it is a different polygon, and it gets a human.
            before, after = abs(geom.area), abs(fixed.area)
            drift = abs(after - before) / before if before else 0.0
            if drift > 1e-6:
                raise RuntimeError("repairing %s changed its area by %.4f%% — "
                                   "too much to be a topology artefact"
                                   % (feature["properties"]["name"], drift * 100))
            warnings.append("%s is self-invalid at the source and was repaired "
                            "(area unchanged to within %.1e)"
                            % (feature["properties"]["name"], 1e-6))
            geom = fixed
        parts.append(geom)
    merged = unary_union(parts)
    if not merged.is_valid:
        merged = merged.buffer(0)
    return merged, mapping(merged)


def round_coords(obj):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(obj[0]), COORD_PRECISION),
                    round(float(obj[1]), COORD_PRECISION)]
        return [round_coords(o) for o in obj]
    return obj


def crosscheck(derived_shapes):
    """Compare the dissolve against the county's OWN board-district polygons.

    Returns a {district: iou} map. A network failure here is fatal: this file
    exists precisely because the county's attributes could not be trusted, so
    shipping it without the geometric agreement that replaces them would be
    shipping the same uncertainty under a new name.
    """
    import requests
    from shapely.geometry import shape
    url = (COUNTY_BOARD_LAYER + "/query?where=1%3D1&outFields=CountyDist"
           "&returnGeometry=true&outSR=4326&f=geojson")
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-mcdonough-board-districts")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    official = {}
    for feature in payload.get("features") or []:
        if not feature.get("geometry"):
            continue
        key = str((feature.get("properties") or {}).get("CountyDist") or "").strip()
        geom = shape(feature["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        official[key] = official[key].union(geom) if key in official else geom
    if not official:
        raise RuntimeError("the county's own board-district layer returned no "
                           "geometry — cannot cross-check the derivation")

    ious = {}
    for district, geom in derived_shapes.items():
        theirs = official.get(district)
        if theirs is None:
            raise RuntimeError("the county's layer publishes no District %s, but "
                               "its board page composes one" % district)
        inter = geom.intersection(theirs).area
        union = geom.union(theirs).area
        ious[district] = (inter / union) if union else 0.0
    return ious


def build():
    by_name = load_precincts()
    total = verify_partition(by_name)

    derived_shapes, features, warnings = {}, [], []
    for district in sorted(DISTRICTS, key=int):
        members = [by_name[name] for name in DISTRICTS[district]]
        geom, geojson = dissolve(members, warnings)
        derived_shapes[district] = geom
        features.append({
            "type": "Feature",
            "properties": {
                "district": district,
                "seats": SEATS_PER_DISTRICT,
                "precincts": sorted(DISTRICTS[district]),
            },
            "geometry": {"type": geojson["type"],
                         "coordinates": round_coords(geojson["coordinates"])},
        })

    ious = crosscheck(derived_shapes)
    worst = min(ious.values())
    if worst < MIN_CROSSCHECK_IOU:
        detail = ", ".join("D%s=%.4f" % (d, v) for d, v in sorted(ious.items()))
        raise RuntimeError("the derived districts disagree with the county's own "
                           "polygons (%s; floor %.2f) — a precinct is probably "
                           "assigned to the wrong district, or the county "
                           "reapportioned. Re-read %s"
                           % (detail, MIN_CROSSCHECK_IOU, MEMBERS_PAGE))

    for warning in sorted(set(warnings)):
        print("  warning: %s" % warning, file=sys.stderr)

    return {
        "type": "FeatureCollection",
        "source": "derived: %s dissolved per the composition published at %s"
                  % (PRECINCTS_PATH.replace(REPO_ROOT + os.sep, ""), MEMBERS_PAGE),
        "crosscheck": {"layer": COUNTY_BOARD_LAYER,
                       "iou": {d: round(v, 4) for d, v in sorted(ious.items())}},
        "precinctCount": total,
        "features": features,
    }, ious


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        payload, ious = build()
    except Exception as exc:  # noqa: BLE001
        print("FATAL: %s" % exc, file=sys.stderr)
        sys.exit(1)

    text = json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
    if args.check:
        if not os.path.exists(OUT_PATH):
            print("FAIL: %s is missing" % OUT_PATH, file=sys.stderr)
            sys.exit(1)
        with open(OUT_PATH, encoding="utf-8") as f:
            shipped = f.read()
        if shipped != text:
            print("FAIL: %s does not match a fresh derivation" % OUT_PATH,
                  file=sys.stderr)
            sys.exit(1)
        print("build-mcdonough-board-districts: OK — shipped file matches "
              "(cross-check %s)"
              % ", ".join("D%s=%.4f" % (d, v) for d, v in sorted(ious.items())))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote %s: %d districts of %d seats each, from %d precincts; "
          "cross-check against the county's own polygons %s"
          % (OUT_PATH, len(payload["features"]), SEATS_PER_DISTRICT,
             payload["precinctCount"],
             ", ".join("D%s=%.4f" % (d, v) for d, v in sorted(ious.items()))),
          file=sys.stderr)


if __name__ == "__main__":
    main()
