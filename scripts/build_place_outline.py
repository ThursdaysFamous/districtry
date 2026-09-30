#!/usr/bin/env python3
"""
Build data/app/<slug>-city-outline.json — the corporate-limits outline a
dispatch entry tests against when a COUNTY-WIDE layer is wrong inside one
municipality.

Why this exists, and it is one county's bug generalised rather than a wish.
Boone County publishes a five-polygon fire tiling that covers every acre of the
county, and the City of Belvidere is not in a fire protection district at all —
it runs its own municipal fire department. A tiling that covers every acre
implies every acre is in a district, and in Illinois a municipality with its own
department is exactly where that is false, so the card asserted a membership the
county's own levy contradicts, for the largest population in the county
(`boone-fire-belvidere-city`). The fix needs a city boundary the app can test a
point against offline, which is what this writes.

It is deliberately the COUNTY-OUTLINE pattern rather than a new one:
scripts/build_county_outline.py ships `<slug>-county-outline.json` for exactly
the same job one level up, and this reuses its fetch, its 25 m Douglas-Peucker
simplify and its point-in-rings test from build_metro_outline.py rather than
forking them. The only difference is the TIGERweb layer — incorporated PLACES
instead of counties — and that layer is the one il/index.html's own
`municipality` layer already reads, so this adds no host to the privacy surface
and no entry to validate_sources.py's manifest.

WHY NOT A RUNTIME POINT QUERY. TIGERweb's places layer answers a single point
directly (`loadIlPlaces.atPoint`), which would need no file at all — and it is
a `loadArcGISPointGeoJSON` call site, which is exactly what
scripts/build_privacy_page.py counts when it tells a reader which layers send
their exact selected point to a government server. Sending a resident's
coordinates to census.gov in order to decide whether to HIDE a card is a poor
trade; a 3 KB shipped ring costs one cached fetch and tells nobody anything.

The outline is a coverage TEST, not a drawn boundary, so vertex-exact fidelity
buys nothing. What is load-bearing is that it still answers correctly near the
edge, so every build validates against anchors — points that must be inside the
city and points that must not be — and refuses to write when any lands wrong.

Usage:
    python3 scripts/build_place_outline.py belvidere
    python3 scripts/build_place_outline.py --check belvidere
    python3 scripts/build_place_outline.py --list
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    HEADERS, REQUEST_TIMEOUT, SIMPLIFY_TOLERANCE_M, STATE_FIPS,
    point_in_rings, rings_of, simplify,
)
from build_county_outline import build_rings, validate  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import require_robots_once  # noqa: E402  (shared machinery)

# How far the simplified rings' own area may sit from the area the Census
# publishes for the same place before the build refuses. 25 m simplification on
# a ~35 km² city moves it well under a percent; anything larger means the rings
# stopped describing the place.
AREA_TOLERANCE = 0.03

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

# Layer 4 of the SAME MapServer il/index.html's `municipality` layer reads
# (loadIlPlaces) is incorporated places; layer 1 is county subdivisions. Using
# the app's own service keeps this off validate_sources.py's manifest and off
# the privacy page's recipient table, both of which already carry the host.
TIGERWEB_PLACES = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                   "Places_CouSub_ConCity_SubMCD/MapServer/4/query")

# place slug -> the TIGER BASENAME to fetch, the display name, and the anchors
# that prove the built ring still answers correctly. Every coordinate below was
# GEOCODED and its returned place read back, never recalled — build_county_
# outline.py's Kankakee note records what recalling one costs.
PLACES = {
    "belvidere": {
        "basename": "Belvidere",
        "name": "City of Belvidere",
        # The city's own institutions, so an anchor cannot drift with a
        # subdivision: City Hall, the county courthouse (which sits in
        # Belvidere), the high school, and the city fire department's own
        # Station 1 — the building that makes this record true.
        "inside": [
            (42.25670, -88.83936, "Belvidere City Hall"),
            (42.26491, -88.84475, "Boone County Courthouse"),
            (42.24397, -88.82873, "Belvidere High School"),
            (42.25824, -88.84250, "Belvidere Fire Department Station 1"),
        ],
        # Boone County places that are NOT Belvidere. Each is district-served
        # on the county's own fire tiling (Poplar Grove 3, Capron 1, sampled
        # 2026-09-04), so swallowing one would hide a card that is correct.
        "outside": [
            (42.36835, -88.82205, "Poplar Grove — Boone County"),
            (42.39942, -88.74059, "Capron — Boone County"),
            (42.25335, -88.72482, "Garden Prairie — unincorporated Boone"),
            (42.36946, -88.89260, "Caledonia — Boone County"),
            # THE LOAD-BEARING ANCHORS. Three of the 22 unincorporated pockets
            # the city has annexed around — they are holes in the outline, so
            # they are NOT in the city and their residents ARE in the county's
            # fire district. A build that flattens holes into solid polygons
            # reads them as in-city and silently hides a card that is correct;
            # that shipped in this file's first draft and only a rendered card
            # caught it, which is why these sit here now.
            (42.25781, -88.88073, "unincorporated pocket inside Belvidere (1.36 km²)"),
            (42.25266, -88.90096, "unincorporated pocket inside Belvidere (1.31 km²)"),
            (42.24653, -88.88671, "unincorporated pocket inside Belvidere (0.30 km²)"),
        ],
    },
}


def fetch_place(basename):
    require_robots_once(TIGERWEB_PLACES, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-place-outline")
    resp = requests.get(TIGERWEB_PLACES, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND BASENAME='%s'" % (STATE_FIPS, basename),
        "outFields": "NAME,BASENAME,GEOID,AREALAND,AREAWATER",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != 1:
        # A BASENAME is not unique across Illinois in general (there is more
        # than one Springfield-shaped trap in this state), so this refuses
        # rather than picking the first.
        raise RuntimeError("TIGERweb returned %d features for place %r, expected exactly 1"
                           % (len(feats), basename))
    return feats[0]


def _ring_area_km2(ring):
    """Planar area, good to a fraction of a percent at Illinois latitudes."""
    lat0 = sum(p[1] for p in ring) / len(ring)
    kx = 111.32 * math.cos(math.radians(lat0))
    ky = 110.57
    total = 0.0
    for i in range(len(ring) - 1):
        total += (ring[i][0] * kx) * (ring[i + 1][1] * ky) \
                 - (ring[i + 1][0] * kx) * (ring[i][1] * ky)
    return abs(total) / 2


def even_odd_area_km2(rings):
    """Net area under the EVEN-ODD rule the app's own point test uses.

    This is the whole reason the check exists. `geojson_for` writes each ring as
    its own polygon, so a naive read sums a hole as solid area — and Belvidere
    is 1 outer ring, TWENTY-TWO unincorporated holes inside it and one detached
    island, which summed naively reads 43.05 km² against a real 35.19. Both
    `point_in_rings` here and `pointInGeometry` in the app evaluate even-odd, so
    a point inside a hole crosses two rings and lands OUTSIDE, which is correct
    and is what those 22 pockets need: their residents are not in the city, so
    they ARE in the county's fire district and must keep their card.
    """
    outer = max(rings, key=_ring_area_km2)
    net = 0.0
    for ring in rings:
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        hole = ring is not outer and point_in_rings(cy, cx, [outer])
        net += -_ring_area_km2(ring) if hole else _ring_area_km2(ring)
    return net


def check_area(rings, feature, name):
    """The simplified rings still cover what the Census says the place covers."""
    props = feature.get("properties") or {}
    land = props.get("AREALAND")
    water = props.get("AREAWATER") or 0
    if not land:
        return ["TIGERweb returned no AREALAND for %s, so the area gate cannot run" % name]
    published = (land + water) / 1e6
    built = even_odd_area_km2(rings)
    drift = abs(built - published) / published
    if drift > AREA_TOLERANCE:
        return ["%s covers %.2f km² as built and %.2f km² as the Census publishes it "
                "(%.1f%% off, ceiling %.0f%%) — the rings stopped describing the place, "
                "or a hole is being counted as solid"
                % (name, built, published, drift * 100, AREA_TOLERANCE * 100)]
    return []


def nest_rings(rings):
    """Group flat rings into GeoJSON polygons: each outer ring with its holes.

    THIS IS THE WHOLE REASON THIS BUILDER IS NOT build_county_outline.py.
    That one writes every ring as its own single-ring polygon, which is safe for
    a county — its own point test is even-odd across the flattened list, and
    county boundaries essentially never have holes. The APP is a different
    test: `pointInGeometry` ORs `pointInPolygonRings` over a MultiPolygon's
    members, so a hole shipped as its own polygon reads as SOLID, and the point
    lands inside. Belvidere is 22 holes, so the first draft of this file hid the
    fire card for every one of those unincorporated pockets — the exact readers
    whose card is correct. Caught by rendering the card in a browser; no static
    gate here could see it, because both Python-side tests agreed with each
    other and neither is the one the app runs.

    `pointInPolygonRings` IS even-odd within a polygon, so nesting a hole under
    its outer ring gives the right answer. Depth is computed rather than
    assumed: a ring inside an odd number of others is a hole of the smallest
    ring containing it, which handles an island sitting inside a hole should
    one ever appear.
    """
    def contains(outer, inner):
        cx = sum(p[0] for p in inner) / len(inner)
        cy = sum(p[1] for p in inner) / len(inner)
        return point_in_rings(cy, cx, [outer])

    parents = {}
    for i, ring in enumerate(rings):
        holders = [j for j, other in enumerate(rings) if j != i and contains(other, ring)]
        # the immediate parent is the smallest ring that contains this one
        parents[i] = min(holders, key=lambda j: _ring_area_km2(rings[j])) if holders else None

    def depth(i):
        d, seen = 0, set()
        while parents[i] is not None and i not in seen:
            seen.add(i)
            i = parents[i]
            d += 1
        return d

    polygons = {i: [rings[i]] for i in range(len(rings)) if depth(i) % 2 == 0}
    for i in range(len(rings)):
        if depth(i) % 2 == 1:
            polygons[parents[i]].append(rings[i])
    return [polygons[i] for i in sorted(polygons)]


def validate_as_the_app_reads_it(polys, cfg):
    """Re-run every anchor under the APP's rule, not this script's.

    `validate` uses point_in_rings — even-odd across the flattened ring list —
    which is what build_metro_outline.py and build_county_outline.py share. The
    app's pointInGeometry ORs pointInPolygonRings over a MultiPolygon's members
    instead, and those two rules DISAGREE exactly where holes exist: the first
    draft of this file passed `validate` and every static gate in the repo while
    hiding the fire card for 22 unincorporated pockets, because no check here
    ran the rule the browser runs. Only rendering the card caught it. So this
    replays the shipped structure under the app's own semantics, and it is the
    gate that would have failed that draft.
    """
    def ring_hit(lng, lat, ring):
        hit = False
        for i in range(len(ring) - 1):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[i + 1][0], ring[i + 1][1]
            if (y1 > lat) != (y2 > lat):
                if lng < (x2 - x1) * (lat - y1) / ((y2 - y1) or 1e-12) + x1:
                    hit = not hit
        return hit

    def in_polygon(lng, lat, poly):
        inside = False
        for ring in poly:
            if ring_hit(lng, lat, ring):
                inside = not inside
        return inside

    def in_geometry(lng, lat):
        return any(in_polygon(lng, lat, poly) for poly in polys)

    problems = []
    for lat, lng, label in cfg["inside"]:
        if not in_geometry(lng, lat):
            problems.append("%s reads OUTSIDE %s under the app's own point test" % (label, cfg["name"]))
    for lat, lng, label in cfg["outside"]:
        if in_geometry(lng, lat):
            problems.append("%s reads INSIDE %s under the app's own point test" % (label, cfg["name"]))
    return problems


def geojson_for(rings, cfg):
    polys = nest_rings(rings)
    geom = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
            else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": cfg["name"]}, "geometry": geom}],
    }


def run(slug, check_only):
    cfg = PLACES[slug]
    out_path = os.path.join(APP_DATA_DIR, "%s-city-outline.json" % slug)
    feature = fetch_place(cfg["basename"])
    rings = build_rings(feature)
    problems = (validate(rings, cfg)
                + check_area(rings, feature, cfg["name"])
                + validate_as_the_app_reads_it(nest_rings(rings), cfg))
    if problems:
        for p in problems:
            print("  FAIL: %s" % p, file=sys.stderr)
        print("FATAL: refusing to write an outline that misplaces its anchors",
              file=sys.stderr)
        return False

    payload = json.dumps(geojson_for(rings, cfg), separators=(",", ":"))
    verts = sum(len(r) for r in rings)
    if check_only:
        if not os.path.exists(out_path):
            print("  %s: MISSING (%s)" % (slug, out_path), file=sys.stderr)
            return False
        with open(out_path, encoding="utf-8") as fh:
            shipped = fh.read()
        if shipped != payload:
            print("  %s: STALE — the shipped outline is not what TIGERweb returns today "
                  "(%d bytes shipped, %d rebuilt). Re-run without --check."
                  % (slug, len(shipped), len(payload)), file=sys.stderr)
            return False
        print("build-place-outline: OK — %s current (%d ring(s), %d vertices, "
              "%d anchors verified)" % (slug, len(rings), verts,
                                        len(cfg["inside"]) + len(cfg["outside"])))
        return True

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(payload)
    print("build-place-outline: wrote %s — %d ring(s), %d vertices, %d bytes, "
          "%d anchors verified"
          % (os.path.relpath(out_path, REPO_ROOT), len(rings), verts, len(payload),
             len(cfg["inside"]) + len(cfg["outside"])))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slugs", nargs="*", help="place slugs to build (default: all)")
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped outlines match a fresh build; write nothing")
    ap.add_argument("--list", action="store_true", help="list known places")
    args = ap.parse_args()
    if args.list:
        for slug, cfg in sorted(PLACES.items()):
            print("%-14s %s" % (slug, cfg["name"]))
        return
    slugs = args.slugs or sorted(PLACES)
    unknown = [s for s in slugs if s not in PLACES]
    if unknown:
        print("unknown place(s): %s (try --list)" % ", ".join(unknown), file=sys.stderr)
        sys.exit(2)
    ok = True
    for slug in slugs:
        ok = run(slug, args.check) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
