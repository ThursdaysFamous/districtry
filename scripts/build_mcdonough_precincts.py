#!/usr/bin/env python3
"""
Build data/app/mcdonough-precincts.json — McDonough County's 27 voting
precincts, each carrying its own polling place.

WHY A PRE-BUILT FILE AND NOT A LIVE FETCH, which is the fleet default:
McDonough's precinct layer cannot be queried for geometry. It is layer 4 of
the WIU GIS Center's `precinct_map` MapServer, it declares
`capabilities: Map,Query,Data`, `geometryType: esriGeometryPolygon` and
`hasGeometryProperties: true` — and every /query returns attributes with the
geometry silently omitted, in Esri JSON and GeoJSON alike, for one feature or
all 27. The layer is a JOIN (its key is `OBJECTID_12`, and unlike sibling
layer 3 it exposes no Shape field), and the join is what breaks geometry
export.

The /identify endpoint returns all 27 WITH geometry. That is a
whole-map-extent request, not something a browser layer should issue on every
first toggle, so it happens here once and ships as a same-origin file — the
same reasoning as the `*-county-outline.json` files.

REPROJECTION IS REQUIRED AND IS NOT OPTIONAL HERE. /identify ignores `outSR`:
ask for 4326 and it still answers in the service's native wkid 102672
(EPSG:3436, NAD83 / Illinois West, US survey feet). Sibling layer 3 reprojects
correctly under `f=geojson`, so this is specific to identify. pyproj does the
transform; a hand-rolled Transverse Mercator inverse was considered and
rejected, because civic boundaries are not the place to debug projection math.

HOW THIS COUNTY WAS FOUND, recorded because the lesson generalises: the
2026-08-02 sweep concluded McDonough had NO LOCATABLE PUBLIC WEBSITE after
nine hostnames failed to resolve. That was wrong. The county is at
`mcg.mcdonough.il.us` — a subdomain, served over HTTP only — and its GIS is
hosted by Western Illinois University rather than by the county. Neither is
guessable. County Clerk Jeremy Benson supplied both in one reply on
2026-08-03, ten minutes after being asked. **When a county cannot be found,
ask its clerk.**

Usage:
    python3 scripts/build_mcdonough_precincts.py
    python3 scripts/build_mcdonough_precincts.py --check
"""

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import group_rings  # noqa: E402  (shared — do not fork)
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_ROSTER_BOT,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "mcdonough-precincts.json")

SERVICE = "https://gis.wiu.edu/arcgis/rest/services/precinct_map/MapServer"
PRECINCT_LAYER = 4
COUNTY_PAGE = "http://mcg.mcdonough.il.us/"
# The service's own declared extent, in its own spatial reference. Passed as
# both the identify geometry and the map extent so the request covers the whole
# county rather than a viewport.
NATIVE_WKID = 102672          # EPSG:3436, NAD83 / Illinois West (ftUS)
EXTENT = (2089274, 1314656, 2219153, 1447575)
REQUEST_TIMEOUT = 120
HEADERS = {
    "User-Agent": UA_ROSTER_BOT,
}

# Identify returns attributes keyed by FIELD ALIAS, not field name.
ALIAS_NAME = "Precinct Name"
ALIAS_POLL_NAME = "Poll Name"
ALIAS_POLL_ADDRESS = "Poll Address"
FIELD_PRECINCT_ID = "PrecinctID"

# Not a floor — an EQUALITY. The county has 27 precincts and the composition
# this file feeds (build_mcdonough_board_districts.py) names all 27 exactly
# once, so any other number means the fabric changed and the board districts
# must be re-derived rather than silently rebuilt on a different base.
EXPECTED_PRECINCTS = 27

COORD_PRECISION = 6           # ~11 cm; the app's other boundary files match


def fetch_precincts():
    params = {
        "geometry": json.dumps({
            "xmin": EXTENT[0], "ymin": EXTENT[1],
            "xmax": EXTENT[2], "ymax": EXTENT[3],
            "spatialReference": {"wkid": NATIVE_WKID},
        }),
        "geometryType": "esriGeometryEnvelope",
        "layers": "all:%d" % PRECINCT_LAYER,
        "tolerance": "1",
        "mapExtent": ",".join(str(v) for v in EXTENT),
        "imageDisplay": "600,600,96",
        "returnGeometry": "true",
        "f": "json",
    }
    url = "%s/identify?%s" % (SERVICE, urllib.parse.urlencode(params))
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-mcdonough-precincts")
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("error"):
        raise RuntimeError("identify returned an error: %s" % payload["error"])
    results = payload.get("results") or []
    if not results:
        raise RuntimeError("identify returned no precincts — the service or its "
                           "layer ids have changed")
    return results


def to_wgs84(rings):
    """Reproject Esri rings from the service's native SR to WGS84 lon/lat."""
    try:
        from pyproj import Transformer
    except ImportError:  # pragma: no cover
        raise RuntimeError("pyproj is required (pip install -c "
                           "scripts/requirements.txt pyproj) — identify ignores "
                           "outSR, so the transform cannot be pushed to the server")
    transformer = Transformer.from_crs("EPSG:3436", "EPSG:4326", always_xy=True)
    out = []
    for ring in rings:
        pts = []
        for point in ring:
            lng, lat = transformer.transform(point[0], point[1])
            pts.append([round(lng, COORD_PRECISION), round(lat, COORD_PRECISION)])
        # A ring that closes in the source must still close after rounding.
        if pts and pts[0] != pts[-1]:
            pts.append(list(pts[0]))
        out.append(pts)
    return out


def esri_rings_to_geojson(rings):
    """Esri rings -> a GeoJSON Polygon or MultiPolygon, nested by CONTAINMENT.

    This is not cosmetic, and getting it wrong is how the first build of this
    file failed. Esri puts every ring of a feature in one flat list and does not
    say which are outers and which are holes; GeoJSON's Polygon says ring 0 is
    the outer and the rest are holes. Nine of McDonough's 27 precincts have more
    than one ring, and they are not all the same case:

      * MC 1 is a genuine donut — one outer with one hole.
      * Emmet is FOUR SEPARATE PARTS, none inside another. Read as
        "outer plus three holes" it lost 99.5% of its area and collapsed, which
        is what the area guard in the district builder caught.

    group_rings (shared with build_metro_outline, not forked) nests by actual
    containment rather than by winding order, so it is right for both cases and
    does not depend on the source being consistent about ring direction — which
    this one is not: Emmet's four rings are all clockwise while MC 4 mixes both.
    """
    groups = group_rings(rings)
    if len(groups) == 1:
        return {"type": "Polygon", "coordinates": groups[0]}
    return {"type": "MultiPolygon", "coordinates": [g for g in groups]}


def build():
    features = []
    for result in fetch_precincts():
        attrs = result.get("attributes") or {}
        geometry = result.get("geometry") or {}
        rings = geometry.get("rings") or []
        name = (attrs.get(ALIAS_NAME) or "").strip()
        if not name:
            raise RuntimeError("a precinct came back with no name — identify's "
                               "attribute ALIASES have changed")
        if not rings:
            raise RuntimeError("%s came back with no geometry" % name)
        wgs = to_wgs84(rings)
        geojson_geom = esri_rings_to_geojson(wgs)
        props = {"name": name, "precinctId": (attrs.get(FIELD_PRECINCT_ID) or "").strip() or None}
        poll_name = (attrs.get(ALIAS_POLL_NAME) or "").strip()
        poll_address = (attrs.get(ALIAS_POLL_ADDRESS) or "").strip()
        if poll_name:
            props["pollName"] = poll_name
        if poll_address:
            props["pollAddress"] = poll_address
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geojson_geom,
        })

    names = [f["properties"]["name"] for f in features]
    if len(features) != EXPECTED_PRECINCTS:
        raise RuntimeError("expected exactly %d precincts, got %d — if the county "
                           "re-precincted, the board-district composition in "
                           "build_mcdonough_board_districts.py must be re-read "
                           "from the county board page BEFORE this file is "
                           "rebuilt" % (EXPECTED_PRECINCTS, len(features)))
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise RuntimeError("duplicate precinct names %s — the composition join "
                           "keys on the name, so it would be ambiguous" % dupes)
    without_poll = [f["properties"]["name"] for f in features
                    if not f["properties"].get("pollName")]
    if without_poll:
        print("  warning: %d precinct(s) carry no polling place (%s)"
              % (len(without_poll), ", ".join(without_poll[:6])), file=sys.stderr)

    features.sort(key=lambda f: f["properties"]["name"])
    return {
        "type": "FeatureCollection",
        "source": SERVICE + "/%d" % PRECINCT_LAYER,
        "sourceNote": ("Read through /identify: the layer is a join and its "
                       "/query omits geometry. Reprojected from EPSG:3436."),
        "countyPage": COUNTY_PAGE,
        "features": features,
    }


def _vertices(geom):
    """Every coordinate pair in a geometry, regardless of nesting depth."""
    out = []

    def walk(node):
        if isinstance(node, list) and node and isinstance(node[0], (int, float)):
            out.append(tuple(node))
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(geom.get("coordinates"))
    return out


def _bbox(points):
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return (min(xs), min(ys), max(xs), max(ys)) if points else None


def describe_drift(shipped, fresh):
    """Say WHAT changed, not merely that something did.

    The --check failure used to read "does not match a fresh build" and stop
    there, which is true of a redistricting and equally true of the county
    nudging one vertex — so the operator had to reproduce the build by hand
    before knowing whether the answer was "ship it" or "stop everything". That
    ambiguity is what kept this refresh red for sixteen days in Aug/Sep 2026,
    when the whole change was McDonough tidying a ~57 x 39 m sliver off the
    edge MC 8 and Scotland share.

    This reports the shape of the difference and deliberately does not judge
    it: a summary saying no precinct was added, no property moved, no bounding
    box shifted and no vertex was INTRODUCED is strong evidence of a cleanup
    rather than a boundary change, but the call stays with the person reading
    it.
    """
    def index(payload):
        return {f["properties"].get("name") or f["properties"].get("precinct"): f
                for f in payload.get("features", [])}

    old, new = index(shipped), index(fresh)
    lines = ["  %d precinct(s) shipped, %d in the fresh build"
             % (len(old), len(new))]
    gone, added = sorted(set(old) - set(new)), sorted(set(new) - set(old))
    if gone or added:
        lines.append("  precincts removed: %s" % (gone or "none"))
        lines.append("  precincts added:   %s" % (added or "none"))
    else:
        lines.append("  no precinct added or removed")

    prop_changes, geom_changes, introduced, moved_bbox = [], [], 0, 0
    for name in sorted(set(old) & set(new)):
        if old[name]["properties"] != new[name]["properties"]:
            keys = sorted(k for k in set(old[name]["properties"]) | set(new[name]["properties"])
                          if old[name]["properties"].get(k) != new[name]["properties"].get(k))
            prop_changes.append("%s (%s)" % (name, ", ".join(keys)))
        if old[name]["geometry"] == new[name]["geometry"]:
            continue
        a, b = _vertices(old[name]["geometry"]), _vertices(new[name]["geometry"])
        fresh_only = len(set(b) - set(a))
        introduced += fresh_only
        ba, bb = _bbox(a), _bbox(b)
        shift = max(abs(ba[i] - bb[i]) for i in range(4)) if ba and bb else 0.0
        if shift > 1e-7:
            moved_bbox += 1
        geom_changes.append(
            "%s (%d -> %d vertices, %d new, bbox %s)"
            % (name, len(a), len(b), fresh_only,
               "unchanged" if shift <= 1e-7 else "moved ~%.0f m" % (shift * 111000)))

    lines.append("  properties changed: %s"
                 % ("; ".join(prop_changes) if prop_changes else "none"))
    lines.append("  geometry changed:   %s"
                 % ("; ".join(geom_changes) if geom_changes else "none"))
    if geom_changes and not introduced and not moved_bbox and not prop_changes and not (gone or added):
        lines.append("  Every fresh vertex already existed in the shipped file and no bounding "
                     "box moved,")
        lines.append("  which is the signature of the county SIMPLIFYING an edge rather than "
                     "moving one.")
    lines.append("  Read the change, then rebuild without --check to ship it "
                 "(and bump the service-worker")
    lines.append("  cache — this file is cache-first, so a returning visitor "
                 "keeps the old copy otherwise).")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="rebuild and compare against the shipped file")
    args = parser.parse_args()

    try:
        payload = build()
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
            print("FAIL: %s does not match a fresh build of the county's data"
                  % OUT_PATH, file=sys.stderr)
            try:
                print(describe_drift(json.loads(shipped), payload), file=sys.stderr)
            except Exception as exc:  # noqa: BLE001 — a summary must never mask the failure
                print("  (could not summarise the difference: %s)" % exc, file=sys.stderr)
            sys.exit(1)
        print("build-mcdonough-precincts: OK — shipped file matches the source "
              "(%d precincts)" % len(payload["features"]))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    with_poll = sum(1 for f in payload["features"] if f["properties"].get("pollName"))
    print("wrote %s: %d precincts, %d with a polling place"
          % (OUT_PATH, len(payload["features"]), with_poll), file=sys.stderr)


if __name__ == "__main__":
    main()
