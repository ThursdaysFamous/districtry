#!/usr/bin/env python3
"""
Build il/data/app/chillicothe-wards.json — the City of Chillicothe's four
wards, drawn to the whole of the city limits as the city's own code describes
them.

WHY CHILLICOTHE SHIPS A FILE WHEN ELMWOOD AND WEST PEORIA FETCH LIVE. All three
cities' wards are on Peoria County's own Elections service (MapServer layer 13,
county-held linework), and il/index.html draws Elmwood's and West Peoria's
straight from it. Chillicothe was HELD there since 2026-09-05 because, measured
against its own Census place polygon, the county's four wards leave 3.3% of the
city in no ward (115.7 acres, the largest piece 100.8 acres in the northwest),
and a card there would tell a resident who HAS a ward that they have none.

THE CITY ANSWERED, AND ITS ANSWER IS A RULE RATHER THAN A NEWER MAP. City Clerk
Jill Byrnes wrote on 2026-10-05 with the ward map and City Code sections 34-1
and 34-2 (Ord. No. 01-09-35, 2001) as "the city code description of ward
locations". Section 34-2 defines every ward as ALL territory within the city
limits on one side of named street centre lines, "extended" to the city
boundary. So the county's internal ward lines are the ordinance's lines, and the
ground they leave uncovered belongs to whichever ward the extended line puts it
in. This builder does exactly that and nothing else:

  1. keeps the county's ward polygons, clipped to the Census city limits (the
     same limits the municipality layer draws, and the "city limits" the code
     names) — 67.5 acres of the county's polygons sit outside them;
  2. extends each internal ward line 3,000 feet straight on from where it meets
     the edge of the county's wards;
  3. splits the uncovered ground along those extensions and gives each piece to
     the ward it shares the most border with.

MEASURED 2026-10-30 against TIGER's roads: the four internal ward lines run
100%, 100%, 100% and 91% within 80 feet of the street centre lines section 34-2
names, so the county's lines are the code's lines and are not moved here. The
result covers the city to 0.000 acres uncovered and 0.000 acres of overlap.

IT IS DERIVED, AND THE CARD SAYS SO: the uncovered ground is assigned by
extending the ordinance's lines, which is what the code says and not a map
anyone surveyed. The gates below fail if the county or the Census moves either
input enough to change that measurement, so a rebuild against a redrawn map
stops rather than shipping.

Usage:
    python3 scripts/build_chillicothe_wards.py            # fetch and write
"""

import json
import os
import sys

import pyproj
import requests
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import linemerge, split, transform, unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import (UA_HEADERS_ROSTER_BOT, make_fail,  # noqa: E402
                            require_robots_once)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "il", "data", "app", "chillicothe-wards.json")

WARDS_URL = ("https://gis.peoriacounty.gov/arcgis/rest/services/DP/Elections/"
             "MapServer/13/query")
PLACE_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
             "tigerWMS_Current/MapServer/28/query")
PLACE_GEOID = "1714117"            # Chillicothe city, Peoria County

WARDS = ("1", "2", "3", "4")
EXTEND_FT = 3000                   # how far each ward line is carried on
SQFT_PER_ACRE = 43560
# What the county's wards leave uncovered inside the city, measured
# 2026-10-30: 115.7 acres. A rebuild outside this band means the county or the
# Census redrew, and the fill has to be looked at again before it ships.
UNCOVERED_ACRES = (100.0, 130.0)
CITY_ACRES = (3400.0, 3700.0)      # 3,544.7 acres measured 2026-10-30

fail = make_fail("chillicothe-wards")
TO_FT = pyproj.Transformer.from_crs(4326, 3435, always_xy=True).transform
TO_DEG = pyproj.Transformer.from_crs(3435, 4326, always_xy=True).transform


def get_geojson(url, params):
    headers = UA_HEADERS_ROSTER_BOT
    require_robots_once(url, headers["User-Agent"], headers=headers,
                        label="chillicothe-wards")
    resp = requests.get(url, params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        fail("%s answered an error: %r" % (url, data["error"]))
    return data


def main():
    county = get_geojson(WARDS_URL, {"where": "CORP_NAME='CHILLICOTHE'",
                                     "outFields": "Ward", "outSR": 4326,
                                     "f": "geojson"})
    place = get_geojson(PLACE_URL, {"where": "GEOID='%s'" % PLACE_GEOID,
                                    "outFields": "GEOID,NAME", "outSR": 4326,
                                    "f": "geojson"})
    if len(place.get("features") or []) != 1:
        fail("TIGERweb returned %d features for place %s, expected 1"
             % (len(place.get("features") or []), PLACE_GEOID))
    city = transform(TO_FT, shape(place["features"][0]["geometry"])).buffer(0)
    city_ac = city.area / SQFT_PER_ACRE
    if not CITY_ACRES[0] <= city_ac <= CITY_ACRES[1]:
        fail("the Census city limits measure %.1f acres, outside %s"
             % (city_ac, CITY_ACRES))

    wards = {}
    for feat in county.get("features") or []:
        key = str((feat.get("properties") or {}).get("Ward") or "").strip()
        if key not in WARDS:
            fail("the county layer carries a ward %r for Chillicothe" % key)
        geom = transform(TO_FT, shape(feat["geometry"])).buffer(0)
        wards[key] = wards[key].union(geom) if key in wards else geom
    if sorted(wards) != list(WARDS):
        fail("the county layer carries wards %s, expected %s"
             % (sorted(wards), list(WARDS)))

    covered = unary_union(list(wards.values()))
    edge = covered.boundary
    uncovered = city.difference(covered)
    un_ac = uncovered.area / SQFT_PER_ACRE
    if not UNCOVERED_ACRES[0] <= un_ac <= UNCOVERED_ACRES[1]:
        fail("the county's wards leave %.1f acres of the city uncovered, "
             "outside the measured %s — re-measure before shipping"
             % (un_ac, UNCOVERED_ACRES))

    # Each internal ward line, carried straight on from where it meets the edge.
    rays = []
    for i, a in enumerate(WARDS):
        for b in WARDS[i + 1:]:
            shared = wards[a].boundary.intersection(wards[b].boundary)
            if shared.is_empty:
                continue
            parts = [g for g in getattr(shared, "geoms", [shared])
                     if g.geom_type == "LineString"]
            if not parts:
                continue
            merged = linemerge(parts)
            for line in getattr(merged, "geoms", [merged]):
                if line.length < 50:
                    continue
                coords = list(line.coords)
                for end in (0, -1):
                    tip = Point(coords[end])
                    if tip.distance(edge) > 5:
                        continue
                    back = line.interpolate(200 if end == 0 else line.length - 200)
                    dx, dy = tip.x - back.x, tip.y - back.y
                    norm = (dx * dx + dy * dy) ** 0.5
                    if norm == 0:
                        continue
                    far = Point(tip.x + dx / norm * EXTEND_FT,
                                tip.y + dy / norm * EXTEND_FT)
                    rays.append(LineString([back, tip, far]))
    if not rays:
        fail("no internal ward line reaches the edge of the county's wards")

    fill = {k: [] for k in WARDS}
    for piece in getattr(uncovered, "geoms", [uncovered]):
        frags = [piece]
        for ray in rays:
            if not ray.intersects(piece):
                continue
            nxt = []
            for frag in frags:
                try:
                    nxt.extend(split(frag, ray).geoms)
                except ValueError:
                    nxt.append(frag)
            frags = nxt
        for frag in frags:
            shared = {k: frag.buffer(3).intersection(v.boundary).length
                      for k, v in wards.items()}
            best = max(shared, key=shared.get)
            if shared[best] == 0:
                best = min(WARDS, key=lambda k: frag.distance(wards[k]))
            fill[best].append(frag)

    out = {k: unary_union([wards[k].intersection(city)] + fill[k]).buffer(0)
           for k in WARDS}
    total = unary_union(list(out.values()))
    gap = city.difference(total).area / SQFT_PER_ACRE
    overlap = (sum(g.area for g in out.values()) - total.area) / SQFT_PER_ACRE
    if gap > 0.01 or overlap > 0.01:
        fail("the filled wards leave %.3f acres uncovered and overlap by %.3f"
             % (gap, overlap))
    if total.difference(city).area / SQFT_PER_ACRE > 0.01:
        fail("the filled wards reach outside the city limits")

    features = []
    for k in WARDS:
        geom = transform(TO_DEG, out[k].simplify(3))
        features.append({"type": "Feature", "properties": {"ward": k},
                         "geometry": json.loads(json.dumps(mapping(geom)),
                                                parse_float=lambda s: round(float(s), 6))})
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump({"type": "FeatureCollection", "features": features}, handle,
                  separators=(",", ":"))
        handle.write("\n")
    print("chillicothe-wards: wrote %s — city %.1f ac; the county's wards left "
          "%.1f ac uncovered, now 0; %s"
          % (os.path.relpath(OUT, REPO_ROOT), city_ac, un_ac,
             ", ".join("Ward %s %.1f ac" % (k, out[k].area / SQFT_PER_ACRE)
                       for k in WARDS)))


if __name__ == "__main__":
    main()
