"""Helpers for in/scripts/build_in_city_wards.py, copied from Louisiana's
la/scripts/build_la_parish_districts.py and la/scripts/build_legislative_boundaries.py
(each instance's scripts import only inside their own tree): reading an ArcGIS
JSON answer into GeoJSON-shaped features, repairing a polygon only where the
repair changes nothing it covers, and reading the Census Bureau's 2020 blocks
for a county, at their internal points."""

import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
# APPENDED, not inserted: the shared scripts/ directory has a
# build_legislative_boundaries.py of its own (Illinois's).
sys.path.append(os.path.join(REPO_ROOT, "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once)

TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
BLOCKS = TIGERWEB + "Tracts_Blocks/MapServer/12"   # Census 2020 blocks, POP100
STATE = "18"
PAGE = 20000
REPAIR_TOLERANCE = 1e-6
MIN_DELAY_S = 1.0
LABEL = "in-city-ward-common"
_LAST = {}


def headers():
    h = dict(UA_HEADERS_ROSTER_BOT)
    h["Accept"] = "application/json"
    return h


def open_json(url, timeout=240):
    """One GET as this project's client, after the host's robots.txt, at least
    MIN_DELAY_S after the last request to the same host; the parsed JSON. An
    ArcGIS error is an object, not an empty answer, so it raises."""
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT, label=LABEL)
    host = urllib.parse.urlsplit(url).hostname
    wait = MIN_DELAY_S - (time.time() - _LAST.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    try:
        req = urllib.request.Request(url, headers=headers())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    finally:
        _LAST[host] = time.time()
    if body[:2] == b"\x1f\x8b":
        import gzip  # noqa: PLC0415
        body = gzip.decompress(body)
    data = json.loads(body.decode("utf-8"))
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError("%s answered an error: %r" % (host, data["error"]))
    return data


def get(url, params):
    q = url + "/query?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            return open_json(q)
        except Exception as err:  # noqa: BLE001 — retried, then raised
            if attempt == 3:
                raise
            print("city-ward-common: retrying after %s" % err, file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def _ring_area(ring):
    """A ring's shoelace area in square degrees: negative when the ring runs
    clockwise, which is how ArcGIS draws an outer ring."""
    return sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
               for i in range(len(ring) - 1)) / 2.0


DROPPED_FLAT_RINGS = {}


def esri_polygon(rings, what):
    """ArcGIS JSON rings as a GeoJSON geometry, by ArcGIS's own rule: a
    clockwise ring is an outer ring, a counter-clockwise one is a hole, and a
    hole belongs to the smallest outer ring that covers it. Anything that
    rule cannot place stops the build. A closed ring with no area at all
    covers no ground and changes no answer, so it is left out and counted in
    DROPPED_FLAT_RINGS under `what`; the builder pins that count."""
    from shapely.geometry import Point, Polygon
    from shapely.prepared import prep
    outers, holes = [], []
    for ring in rings or []:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise SystemExit("FAIL: %s has a ring that is not closed" % what)
        area = _ring_area(ring)
        if area == 0:
            DROPPED_FLAT_RINGS[what] = DROPPED_FLAT_RINGS.get(what, 0) + 1
            continue
        (outers if area < 0 else holes).append(ring)
    if not outers:
        raise SystemExit("FAIL: %s has no outer ring" % what)
    shells = [Polygon(r) for r in outers]
    ready = [prep(s) for s in shells]
    parts = [[r] for r in outers]
    for hole in holes:
        homes = [i for i, s in enumerate(ready)
                 if all(s.covers(Point(x, y)) for x, y in hole[:-1])]
        if not homes:
            raise SystemExit("FAIL: %s has a hole outside every outer ring" % what)
        parts[min(homes, key=lambda i: shells[i].area)].append(hole)
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def esri_features(data, what, key):
    """GeoJSON-shaped features from an ArcGIS JSON query answer. `key` names
    the attribute a failure message identifies a feature by."""
    sr = data.get("spatialReference") or {}
    if data.get("features") and 4326 not in (sr.get("wkid"), sr.get("latestWkid")):
        raise SystemExit("FAIL: %s answered in spatial reference %r, not 4326" % (what, sr))
    out = []
    for f in data.get("features") or []:
        attrs = f.get("attributes") or {}
        rings = (f.get("geometry") or {}).get("rings")
        out.append({"type": "Feature", "properties": attrs,
                    "geometry": (esri_polygon(rings, "%s %s %r" % (what, key, attrs.get(key)))
                                 if rings else None)})
    return out


def fetch_blocks(county3, detail=False):
    """[(lng, lat, people)] for every populated 2020 block in the county, at
    its internal point, or with `detail` [(lng, lat, people, GEOID)]."""
    out, seen, offset = [], set(), 0
    while True:
        data = get(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, county3),
            "outFields": "GEOID,INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": PAGE,
            "f": "json",
        })
        feats = data.get("features") or []
        for f in feats:
            a = f["attributes"]
            if a["GEOID"] in seen:
                raise SystemExit("FAIL: block %s returned twice across pages" % a["GEOID"])
            seen.add(a["GEOID"])
            row = (float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"]))
            out.append(row + (a["GEOID"],) if detail else row)
        if len(feats) < PAGE and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    return out


def checked_shape(geom, what):
    """A shapely geometry for a GeoJSON one, repaired only where the repair
    leaves what it covers unchanged."""
    from shapely.geometry import shape
    from shapely.validation import explain_validity
    g = shape(geom)
    if g.is_valid:
        return g
    fixed = g.buffer(0)
    if g.area <= 0 or abs(fixed.area - g.area) > REPAIR_TOLERANCE * g.area:
        raise SystemExit("FAIL: %s is not a valid polygon (%s), and repairing it would change "
                         "its area by %.4f%%"
                         % (what, explain_validity(g),
                            100.0 * (fixed.area - g.area) / g.area if g.area else 100.0))
    return fixed


def polygonal(g, what):
    """The polygon parts of a shapely result: cutting can leave lines and
    points where two edges touch."""
    from shapely.geometry import MultiPolygon
    if g.is_empty:
        raise SystemExit("FAIL: %s is empty" % what)
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    polys = []
    for part in getattr(g, "geoms", []):
        if part.geom_type == "Polygon":
            polys.append(part)
        elif part.geom_type == "MultiPolygon":
            polys.extend(part.geoms)
    if not polys:
        raise SystemExit("FAIL: %s has no area" % what)
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def geojson(g):
    from shapely.geometry import mapping
    return json.loads(json.dumps(mapping(g)))


def rings_of(geom):
    """Every ring of a Polygon or MultiPolygon, outers and holes alike."""
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "Polygon":
        return c
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def seg_index(feature, cell=0.02):
    idx = {}
    for ring in rings_of(feature["geometry"]):
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    idx.setdefault((gx, gy), []).append((a, b))
    return idx


def point_to_segment_m(p, a, b):
    my = 111320.0
    mx = 111320.0 * math.cos(math.radians(p[1]))
    px, py = p[0] * mx, p[1] * my
    ax, ay = a[0] * mx, a[1] * my
    bx, by = b[0] * mx, b[1] * my
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def letter(v):
    """A district letter as the layer serves it: 'A' -> 'A'."""
    s = str(v).strip()
    if not re.match(r"^[A-Z]$", s):
        raise ValueError("not a district letter: %r" % (v,))
    return s
