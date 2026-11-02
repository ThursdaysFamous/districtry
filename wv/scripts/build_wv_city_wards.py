#!/usr/bin/env python3
"""
Build wv/data/app/wv-city-wards.json: the council wards of the West Virginia
cities whose ward maps this app has, drawn by the `city-ward` layer in
wv/index.html, whose card names the council member from
wv/data/app/wv-city-councils.json (build_wv_city_councils.py).

WHICH CITIES. The four largest elect council members by ward and were asked
for their ward maps on 2026-10-21 (docs/ASK_DRAFTS.md). One has answered:

  Charleston   the City Clerk's office e-mailed a shapefile of the 20 wards on
               2026-11-02 (Deputy City Clerk Nikki Smith, after review by the
               city's Information Systems department and the City Attorney).
               Asked the same day, the City wrote that the file is the
               current one and that the ward boundaries have not changed since
               the 2021 redistricting, and that districtry may show them. Its
               covering e-mail says the city's GIS information is in the
               public domain and for public use without monetary gain, may not
               be copied without permission, and that citing the source is
               appreciated; the card credits the City of Charleston. The files
               are kept as sent, under data/source/raw/charleston-wards/, and
               held to their SHA-256 below (SENT).

Huntington, Parkersburg and Wheeling join CITIES in the change that draws each
one's wards; until then gap wv-city-wards records them.

WHAT THE 2020 CENSUS SAYS ABOUT THE MAP. A plan is drawn on one census and
holds nearly equal numbers of people on it. Counted on the 2020 census's
populated blocks (each block's internal point inside the wards as cut at the
city's limits, below), Charleston's 20 wards hold 2,314 to 2,558 people each,
10.0% apart around an equal share of 2,434: lines drawn on the 2020 census,
which agrees with what the City wrote. The figures are pinned in CITIES, so a
changed line fails the build until a person has read it.

THE CITY'S OUTER EDGE IS THE CENSUS BUREAU'S MAP OF THE CITY (TIGERweb's
current incorporated place, the layer the City, Town or Village card reads), as
every drawn city's is in this fleet (la/scripts/build_la_city_wards.py), so the
ward card never names a ward of a city the City card says a point is not in.
Measured 2026-11-02, the two maps disagree along their edges by more than a
hairline: 2.50 km2 of Charleston as the Census maps it (3.0% of 83.8 km2) is
in no ward on the city's map, in 326 pieces, the largest 0.49 km2 at
38.40095, -81.63961, where 185 people lived in 2020; and 1.85 km2 of the
city's wards lie outside the Census's Charleston, where 73 people lived. Less
than 0.02 km2 of either is the Census's areal water, so it is not the rivers.
Which map is newer at each edge is not established. A point in the first is
told no ward is drawn there; the second is cut away. Both are pinned
(`gap_people`, `outside_people`, `max_gap_km2`, `max_gap_part_m2`). Where the
two edges cross, the cut leaves six pieces of a few square centimetres (one of
Ward 11, five of Ward 15), each smaller than one cell of the output's
coordinate grid and so impossible to write; they are left out, and their count
is pinned (`subcell_parts`).

THE LINES BETWEEN WARDS ARE THE CITY'S, never redrawn. The file carries a ward
name (W1 to W20) and a GlobalID and nothing else; no member names.

SIMPLIFYING. mapshaper Douglas-Peucker at a 3 m interval, keep-shapes, the
fleet's choice for district lines (CLAUDE.md, the IL chambers record). Before
anything is written: every ward is drawn, no ring is lost, the true line
strays at most FIDELITY_MAX_M from the drawn one, every populated 2020 block
gets the same ward from the drawn file as from the cut wards, 4,000 seeded
points agree, and the drawing adds no overlap at them. An exception is a
declaration in ACCEPTED_DROPPED_PARTS or ACCEPTED_OVERLAPS, checked on every
build, and two were needed on 2026-11-02: a 12 m2 piece of Ward 17 the drawing
drops, where nobody lives, and 1.78 m2 where the drawn Wards 7 and 11 cross
because the city's file draws their shared line twice, a few centimetres
apart. Without the first, the true line strays at most 3.00 m from the drawn
one.

ROBOTS. tigerweb.geo.census.gov serves no robots.txt (HTTP 404 with an HTML
page, read 2026-11-02): allow all. Every request is paced at one second.

Usage:
    python3 wv/scripts/build_wv_city_wards.py          # build (network)
    python3 wv/scripts/build_wv_city_wards.py --check  # offline

--check reads the shipped file and the kept source files, offline: the files
are the ones the city sent; every ward in CITIES is drawn once with the
properties the card reads; each drawn ward lies inside the same ward of the
city's own map, as its representative point and as at least 97% of its area;
the drawn file's wards overlap nowhere but the recorded place; and the layer's empty-state sentence in
wv/index.html names the cities drawn (on one source line), as does its
WV_WARD_CITIES, the list the City, Town or Village card reads to say the
council is named on the ward card. It proves the file is what a build of the
kept files writes; the Census outline and the blocks are read only by a
build.
"""

import datetime
import hashlib
import json
import math
import os
import random
import re
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(_HERE)
REPO_ROOT = os.path.dirname(INSTANCE)
# APPENDED, not inserted: the shared scripts/ directory has a
# build_legislative_boundaries.py of its own (Illinois's), and this file
# imports the one beside it.
sys.path.append(os.path.join(REPO_ROOT, "scripts"))
from scraper_common import require_robots_allowed  # noqa: E402  (FLEET_SHARED)

sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
OUT = os.path.join(APP_DATA_DIR, "wv-city-wards.json")
RAW_DIR = os.path.join(INSTANCE, "data", "source", "raw")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
APP_FILE = os.path.join(INSTANCE, "index.html")

USER_AGENT = "districtry/1.0 (+https://districtry.com/wv/)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
LABEL = "wv-build-wv-city-wards"
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
TIGERWEB_PLACE = TIGERWEB + "Places_CouSub_ConCity_SubMCD/MapServer/4"
BLOCKS = TIGERWEB + "Tracts_Blocks/MapServer/12"  # Census 2020 blocks, POP100
STATE = "54"
PAGE = 20000
MIN_DELAY_S = 1.0

MAPSHAPER = blb.MAPSHAPER
SIMPLIFY = ["dp", "interval=3", "keep-shapes"]
PRECISION = "0.000001"
FIDELITY_MAX_M = 4.0
AGREEMENT_SAMPLES = 4000
MIN_AGREEMENT = 0.995
# --check: a drawn ward must keep this share of its area inside the same ward
# of the city's own map (the cut at the Census edge takes the rest).
CHECK_INSIDE_SHARE = 0.97

CITIES = [
    {
        "geoid": "5414600",
        "city": "Charleston",
        "county3s": ["039"],
        "file": "charleston-wards/wards",
        "field": "WARD",
        "sha256": {
            "shp": "2364e643bd0e7834cbf3df6e17cd30a03d2f0e5ad0614d6a2f4246282c0dffd5",
            "shx": "019731cadb34122888d85a8f03e521814d37eec63bced7b4744a77d2f4d77ca2",
            "dbf": "04256c3f7509ef37c21f798a895742fef223020f6adb25c43b81c0e227a48c3d",
            "prj": "583a589e585c69272435393c1afcab9173a32f3199120a0c5644c70b46fd116b",
            "cpg": "3ad3031f5503a4404af825262ee8232cc04d4ea6683d42c5dd0a2f2a27ac9824",
        },
        "names": {"W%d" % n: str(n) for n in range(1, 21)},
        "sent": "2026-11-02",
        # The 2020 census's people in each ward as cut at the city's limits,
        # by block internal point, measured 2026-11-02.
        "people": {"1": 2314, "2": 2323, "3": 2332, "4": 2326, "5": 2433, "6": 2337,
                   "7": 2352, "8": 2362, "9": 2495, "10": 2361, "11": 2346, "12": 2540,
                   "13": 2558, "14": 2535, "15": 2450, "16": 2499, "17": 2555, "18": 2532,
                   "19": 2509, "20": 2512},
        # Cutting the city's wards at the Census place leaves pieces of a few
        # square centimetres where the two maps' edges cross (one of Ward 11,
        # five of Ward 15), too small to be written at the output's precision.
        "subcell_parts": 6,
        "outside_people": 73,
        "gap_people": 185,
        "max_gap_km2": 2.51,
        "max_gap_part_m2": 490000,
        "source": ("the City of Charleston's own map of its 20 wards, sent by the City "
                   "Clerk's office on November 2, 2026, which the City says is current since "
                   "the 2021 redistricting"),
        "sourceUrl": "https://www.charlestonwv.gov/government/city-council",
    },
]

EDGE = ", ending at the city's limits as the Census Bureau maps them"
PROPS = ("geoid", "city", "ward", "seat", "source", "sourceUrl")

# A declared part or overlap is the one found when its representative point is
# within this many metres of the recorded one and its area within this share
# of the recorded area (la/scripts/build_la_city_wards.py's rule).
DECLARED_WITHIN_M = 1.0
DECLARED_AREA_SHARE = 0.10

# What the drawn file answers differently from the cut wards, each re-checked
# on every build: the part must still be in the cut ward, and the two files
# must still give the recorded answers at its representative point.
ACCEPTED_DROPPED_PARTS = [
    dict(city="Charleston", ward="17", lat=38.329405, lng=-81.580956, m2=11.67, verts=3,
         before=["17"], after=[],
         why="a three-cornered piece of Ward 17 of about 12 square metres, 16 m from the rest "
             "of the ward: the ground between them is inside the city's limits on the Census "
             "Bureau's map and in no ward on the city's map. The drawing drops it, which is the "
             "true line straying 35.5 m from the drawn one. No census point is inside it",
         date="2026-11-02"),
]

# Ground two drawn wards both cover, each re-checked by check_data (so by
# --check too): a part of OVERLAP_MIN_M2 or more that is not recorded here
# fails, and so does a record no part matches. The card names every ward at a
# point, so a reader there is told both.
OVERLAP_MIN_M2 = 1.0
ACCEPTED_OVERLAPS = [
    dict(geoid="5414600", wards=["7", "11"], lat=38.365423, lng=-81.610745, m2=1.78,
         why="the city's file draws the line between Wards 7 and 11 twice, the two copies a "
             "few centimetres apart (3 of the 18 points of Ward 7 within half a metre of Ward "
             "11's line are not points of Ward 11), so the drawing simplifies each copy on its "
             "own and here they cross. The card names both wards at a point there",
         date="2026-11-02"),
]


def fail(msg):
    raise SystemExit("build-wv-city-wards: FATAL: %s" % msg)


def _order(w):
    return int(w)


# ---------------------------------------------------------- the kept files --
def _raw(c, ext):
    path = os.path.join(RAW_DIR, c["file"] + "." + ext)
    with open(path, "rb") as fh:
        raw = fh.read()
    if hashlib.sha256(raw).hexdigest() != c["sha256"][ext]:
        fail("%s is not the file %s sent" % (os.path.relpath(path, REPO_ROOT), c["city"]))
    return raw


def _dbf_rows(raw, encoding):
    n, header_len, rec_len = struct.unpack("<IHH", raw[4:12])
    fields, o = [], 32
    while raw[o] != 0x0D:
        fields.append((raw[o:o + 11].split(b"\0")[0].decode(), raw[o + 16]))
        o += 32
    rows = []
    for i in range(n):
        rec, p, row = raw[header_len + i * rec_len + 1:header_len + (i + 1) * rec_len], 0, {}
        for name, length in fields:
            row[name] = rec[p:p + length].decode(encoding).strip()
            p += length
        rows.append(row)
    return rows


def _shp_polygons(raw, transform):
    """Polygon (type 5) records of a shapefile as lists of rings, reprojected."""
    out, o = [], 100
    while o < len(raw):
        _, words = struct.unpack(">ii", raw[o:o + 8])
        rec = raw[o + 8:o + 8 + words * 2]
        o += 8 + words * 2
        if struct.unpack("<i", rec[:4])[0] != 5:
            fail("a shapefile record is not a polygon")
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack("<%di" % nparts, rec[44:44 + 4 * nparts]))
        base = 44 + 4 * nparts
        pts = [struct.unpack("<dd", rec[base + 16 * i:base + 16 * i + 16]) for i in range(npts)]
        rings = []
        for k, start in enumerate(parts):
            end = parts[k + 1] if k + 1 < nparts else npts
            xs, ys = transform([p[0] for p in pts[start:end]], [p[1] for p in pts[start:end]])
            rings.append([[x, y] for x, y in zip(xs, ys)])
        out.append(rings)
    return out


def _rings_to_shape(rings, what):
    """Shapefile rings to one shapely geometry: an outer ring winds clockwise
    and a hole counter-clockwise (ArcGIS shares the rule)."""
    from shapely.geometry import LinearRing, Polygon
    from shapely.ops import unary_union
    outers, holes = [], []
    for r in rings:
        if len(r) < 4:
            continue
        (holes if LinearRing(r).is_ccw else outers).append(Polygon(r))
    polys = []
    for o in outers:
        inner = [h.exterior.coords for h in holes if o.contains(h.representative_point())]
        polys.append(Polygon(o.exterior.coords, inner))
    g = unary_union(polys)
    if not g.is_valid or g.is_empty:
        fail("%s is not a valid polygon" % what)
    return g


def read_sent(c):
    """{ward: shapely geometry} from the files the city sent."""
    from pyproj import Transformer
    prj = _raw(c, "prj").decode("latin-1")
    encoding = _raw(c, "cpg").decode("latin-1").strip() or "latin-1"
    _raw(c, "shx")
    t = Transformer.from_crs(prj, "EPSG:4326", always_xy=True)
    rings = _shp_polygons(_raw(c, "shp"), t.transform)
    rows = _dbf_rows(_raw(c, "dbf"), encoding)
    if len(rings) != len(rows):
        fail("%s: %d shapes and %d records" % (c["city"], len(rings), len(rows)))
    out = {}
    for row, r in zip(rows, rings):
        name = row.get(c["field"])
        ward = c["names"].get(name)
        if ward is None:
            fail("%s: a ward the file calls %r" % (c["city"], name))
        if ward in out:
            fail("%s: Ward %s is in the file twice" % (c["city"], ward))
        out[ward] = _rings_to_shape(r, "%s Ward %s" % (c["city"], ward))
    if sorted(out, key=_order) != sorted(c["names"].values(), key=_order):
        fail("%s: the file draws wards %s" % (c["city"], sorted(out, key=_order)))
    return out


# ---------------------------------------------------------------- fetching --
_ROBOTS = {}
_LAST = {}


def _fetch_json(url, params=None):
    """GET one url as this builder's client, after asking its host's robots.txt
    about that url's own path, waiting a second between requests to one host."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname
    if (host, parts.path) not in _ROBOTS:
        why = require_robots_allowed(url, USER_AGENT, headers=HEADERS, label=LABEL)
        _ROBOTS[(host, parts.path)] = why
        print("robots.txt %s%s: %s" % (host, parts.path, why), file=sys.stderr)
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    body = None
    for attempt in range(4):
        wait = MIN_DELAY_S - (time.time() - _LAST.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(full, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = resp.read()
            _LAST[host] = time.time()
            break
        except Exception as err:  # noqa: BLE001 — retried, then raised
            _LAST[host] = time.time()
            if attempt == 3:
                raise
            print("city-wards: retrying %s after %s" % (host, err), file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    data = json.loads(body.decode("utf-8"))
    if isinstance(data, dict) and "error" in data:
        # An ArcGIS error is an object, not an empty answer.
        fail("%s answered an error: %r" % (url, data["error"]))
    return data


def fetch_place(c):
    fc = _fetch_json(TIGERWEB_PLACE + "/query", {
        "where": "GEOID='%s'" % c["geoid"], "outFields": "GEOID,BASENAME",
        "returnGeometry": "true", "outSR": "4326", "geometryPrecision": "6", "f": "json"})
    feats = fc.get("features") or []
    if len(feats) != 1:
        fail("%s: TIGERweb returned %d places for GEOID %s" % (c["city"], len(feats), c["geoid"]))
    if feats[0]["attributes"].get("BASENAME") != c["city"]:
        fail("%s: GEOID %s is %r on TIGERweb" % (c["city"], c["geoid"],
                                                  feats[0]["attributes"].get("BASENAME")))
    return _rings_to_shape(feats[0]["geometry"]["rings"], "%s's Census place" % c["city"]).buffer(0)


def fetch_blocks(county3):
    """[(lng, lat, people, GEOID)] for every populated 2020 block in the county."""
    out, seen, offset = [], set(), 0
    while True:
        data = _fetch_json(BLOCKS + "/query", {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, county3),
            "outFields": "GEOID,INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": PAGE,
            "f": "json"})
        feats = data.get("features") or []
        for f in feats:
            a = f["attributes"]
            if a["GEOID"] in seen:
                fail("block %s returned twice across pages" % a["GEOID"])
            seen.add(a["GEOID"])
            out.append((float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"]), a["GEOID"]))
        if len(feats) < PAGE and not data.get("exceededTransferLimit"):
            return out
        offset += len(feats)


# ---------------------------------------------------------------- measuring --
def _m2(g, lat0):
    """Area in square metres by a local plane at lat0."""
    return g.area * 111320.0 * math.cos(math.radians(lat0)) * 110540.0


def _lat0(geoms):
    ys = [g.bounds[1] for g in geoms] + [g.bounds[3] for g in geoms]
    return (min(ys) + max(ys)) / 2.0


def _polygons(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def _part_m2(p):
    return _m2(p, (p.bounds[1] + p.bounds[3]) / 2.0)


def _cell_m2(lat0):
    """The area of one cell of the output's coordinate grid (PRECISION degrees
    square) at lat0: a part smaller than this cannot be written at all."""
    d = float(PRECISION)
    return _m2(__import__("shapely.geometry", fromlist=["box"]).box(0, 0, d, d), lat0)


def _metres(a, b):
    """Metres between two (lng, lat) points, by a local plane."""
    lat = (a[1] + b[1]) / 2.0
    return math.hypot((a[0] - b[0]) * 111320.0 * math.cos(math.radians(lat)),
                      (a[1] - b[1]) * 110540.0)


def _matches(rec, part, m2):
    """Whether a recorded part is this one: its point and its area."""
    rp = part.representative_point()
    return (_metres((rp.x, rp.y), (rec["lng"], rec["lat"])) <= DECLARED_WITHIN_M
            and abs(m2 - rec["m2"]) <= DECLARED_AREA_SHARE * rec["m2"])


def _geojson(g):
    from shapely.geometry import MultiPolygon, mapping
    polys = _polygons(g)
    if not polys:
        fail("an empty ward")
    return json.loads(json.dumps(mapping(polys[0] if len(polys) == 1 else MultiPolygon(polys))))


def cut(c, wards, place):
    """Each ward cut at the city's limits as the Census place draws them, and
    the ground of the place no ward holds."""
    from shapely.geometry import MultiPolygon
    from shapely.ops import unary_union
    lat0 = _lat0(list(wards.values()))
    cell = _cell_m2(lat0)
    out, subcell = {}, 0
    for w, g in wards.items():
        parts = _polygons(g.intersection(place))
        keep = [p for p in parts if _part_m2(p) >= cell]
        subcell += len(parts) - len(keep)
        if not keep:
            fail("%s Ward %s lies wholly outside the Census place" % (c["city"], w))
        out[w] = keep[0] if len(keep) == 1 else MultiPolygon(keep)
    union = unary_union(list(wards.values()))
    gap = place.difference(union)
    outside = union.difference(place)
    parts = sorted(_polygons(gap), key=lambda p: -p.area)
    gap_km2 = _m2(gap, lat0) / 1e6
    largest = _m2(parts[0], lat0) if parts else 0.0
    print("  the Census place: %.3f km2; %.3f km2 of it in no ward, in %d pieces, the largest "
          "%.0f m2; %.3f km2 of the wards outside it; %d pieces of the cut smaller than one "
          "%.4f m2 cell of the output's grid, left out"
          % (_m2(place, lat0) / 1e6, gap_km2, len(parts), largest, _m2(outside, lat0) / 1e6,
             subcell, cell), file=sys.stderr)
    problems = []
    if subcell != c["subcell_parts"]:
        problems.append("cutting at the Census place leaves %d pieces smaller than one cell of "
                        "the output's grid, not the pinned %d" % (subcell, c["subcell_parts"]))
    if gap_km2 > c["max_gap_km2"] or largest > c["max_gap_part_m2"]:
        problems.append("the ground in no ward (%.3f km2, largest piece %.0f m2) is past its "
                        "measured ceiling (%.2f km2 / %.0f m2)"
                        % (gap_km2, largest, c["max_gap_km2"], c["max_gap_part_m2"]))
    return out, union, problems


def people(c, raw_union, wards, place, blocks):
    """{ward: people} on the 2020 census by block internal point, inside the
    cut wards; the people the cut takes away; the people in no ward."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    x0, y0, x1, y1 = raw_union.union(place).bounds
    near = [b for b in blocks if x0 - 0.001 <= b[0] <= x1 + 0.001 and y0 - 0.001 <= b[1] <= y1 + 0.001]
    ready = {w: prep(g) for w, g in wards.items()}
    in_raw, in_place = prep(raw_union), prep(place)
    pop = {w: 0 for w in wards}
    outside = gap = 0
    for x, y, n, _geoid in near:
        pt = Point(x, y)
        hits = [w for w, g in ready.items() if g.contains(pt)]
        if len(hits) > 1:
            fail("%s: %d people live in a block the city's map puts in two wards" % (c["city"], n))
        if hits:
            pop[hits[0]] += n
        elif in_place.contains(pt):
            gap += n
        elif in_raw.contains(pt):
            outside += n
    vals = list(pop.values())
    ideal = sum(vals) / float(len(vals))
    print("  people on the 2020 census: %s; %d in all, %.1f%% apart; %d inside the city's map "
          "and outside its limits, %d inside its limits and in no ward"
          % (", ".join("%s: %d" % (w, pop[w]) for w in sorted(pop, key=_order)), sum(vals),
             100.0 * (max(vals) - min(vals)) / ideal, outside, gap), file=sys.stderr)
    problems = []
    got = {w: pop[w] for w in sorted(pop, key=_order)}
    if got != c["people"]:
        problems.append("the 2020 census puts %s in the wards, not the pinned %s. A line that "
                        "moved is a redistricting until a person has read it" % (got, c["people"]))
    if outside != c["outside_people"]:
        problems.append("%d people live inside the city's map and outside its limits, not the "
                        "pinned %d" % (outside, c["outside_people"]))
    if gap != c["gap_people"]:
        problems.append("%d people live inside the city's limits and in no ward, not the pinned "
                        "%d" % (gap, c["gap_people"]))
    return problems, near


# --------------------------------------------------------------- drawing --
def simplify(exact):
    work = tempfile.mkdtemp(prefix="wv-wards-")
    src = os.path.join(work, "exact.json")
    dst = os.path.join(work, "simple.json")
    try:
        with open(src, "w") as fh:
            json.dump(exact, fh, separators=(",", ":"))
        proc = subprocess.run(
            ["npx", "--yes", MAPSHAPER, src, "-simplify"] + SIMPLIFY +
            ["-o", "precision=" + PRECISION, "format=geojson", dst],
            capture_output=True, text=True, cwd=REPO_ROOT)
        if proc.returncode != 0 or not os.path.exists(dst):
            fail("mapshaper failed (%d): %s" % (proc.returncode, (proc.stderr or "")[-800:]))
        with open(dst) as fh:
            out = json.load(fh)
    finally:
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(work)
    if len(out.get("features") or []) != len(exact["features"]):
        fail("mapshaper returned %d features for %d" % (len(out.get("features") or []),
                                                          len(exact["features"])))
    return out


def _ring_count(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return sum(len(p) for p in polys)


def drawn_checks(exact, simple, blocks_by_city):
    """Every answer the cut wards give, the drawn file gives too, but the ones
    ACCEPTED_DROPPED_PARTS records."""
    from shapely.geometry import shape
    problems = []
    key = lambda f: (f["properties"]["geoid"], f["properties"]["ward"])  # noqa: E731
    src = {key(f): f for f in exact["features"]}
    new = {key(f): f for f in simple["features"]}
    if set(src) != set(new):
        fail("mapshaper changed the set of wards")
    geoid_of = {f["properties"]["city"]: f["properties"]["geoid"] for f in exact["features"]}
    models = {}
    for geoid in sorted(set(k[0] for k in src)):
        feats = [src[k] for k in sorted(src) if k[0] == geoid]
        models[geoid] = (blb._model(feats, "ward"), blb._model([new[key(f)] for f in feats], "ward"))

    def answers(geoid, pt):
        s_model, n_model = models[geoid]
        return sorted(blb._districts_at(s_model, pt)), sorted(blb._districts_at(n_model, pt))

    # parts the drawing removes: each recorded, each record still matching
    skip, dropped = set(), {}
    for rec in ACCEPTED_DROPPED_PARTS:
        geoid = geoid_of.get(rec["city"])
        f = src.get((geoid, rec["ward"]))
        if f is None:
            problems.append("ACCEPTED_DROPPED_PARTS records %s Ward %s, which is not drawn"
                            % (rec["city"], rec["ward"]))
            continue
        found = [p for p in _polygons(shape(f["geometry"]))
                 if len(p.exterior.coords) - 1 == rec["verts"] and _matches(rec, p, _part_m2(p))]
        if len(found) != 1:
            problems.append("ACCEPTED_DROPPED_PARTS records a %.2f m2 part of %s Ward %s at "
                            "%.6f,%.6f, and the cut ward has %d such parts"
                            % (rec["m2"], rec["city"], rec["ward"], rec["lat"], rec["lng"],
                               len(found)))
            continue
        part = found[0]
        rp = part.representative_point()
        before, after = answers(geoid, (rp.x, rp.y))
        if (before, after) != (sorted(rec["before"]), sorted(rec["after"])):
            problems.append("ACCEPTED_DROPPED_PARTS: on the %.2f m2 part of %s Ward %s the cut "
                            "wards answer %s and the drawn file %s, not the recorded %s and %s"
                            % (_part_m2(part), rec["city"], rec["ward"], before, after,
                               rec["before"], rec["after"]))
            continue
        skip.add(tuple(tuple(v) for v in part.exterior.coords))
        dropped[(geoid, rec["ward"])] = dropped.get((geoid, rec["ward"]), 0) + 1
    for k in sorted(src):
        a, b = _ring_count(src[k]["geometry"]), _ring_count(new[k]["geometry"])
        if a - dropped.get(k, 0) != b:
            problems.append("Ward %s has %d rings cut and %d drawn, and ACCEPTED_DROPPED_PARTS "
                            "records %d dropped" % (k[1], a, b, dropped.get(k, 0)))
    # fidelity: the true line's stray from the drawn chord, on every ring kept
    worst, where = 0.0, None
    for k in sorted(src):
        idx = blb._seg_index(new[k])
        for ring in blb._rings_of(src[k]["geometry"]):
            if tuple(tuple(v) for v in ring) in skip:
                continue
            for v in ring[:-1]:
                gx, gy = int(math.floor(v[0] / 0.02)), int(math.floor(v[1] / 0.02))
                cand = []
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        cand += idx.get((gx + dx, gy + dy), ())
                if cand:
                    d = min(blb._point_to_segment_m(v, a, b) for a, b in cand)
                    if d > worst:
                        worst, where = d, (k[1], v)
    print("fidelity: the cut wards' lines stray at most %.2f m from the drawn ones (ceiling "
          "%.1f%s); the source's median step is %.2f m"
          % (worst, FIDELITY_MAX_M,
             ", at Ward %s %.6f,%.6f" % (where[0], where[1][1], where[1][0]) if where else "",
             blb.median_source_step_m(exact["features"])), file=sys.stderr)
    if worst > FIDELITY_MAX_M:
        problems.append("the cut wards' lines stray %.2f m from the drawn ones, over %.1f m"
                        % (worst, FIDELITY_MAX_M))
    for geoid in sorted(blocks_by_city):
        s_model, n_model = models[geoid]
        moved = 0
        for x, y, n, gid in blocks_by_city[geoid]:
            a, b = answers(geoid, (x, y))
            if a != b:
                moved += n
                problems.append("block %s, %d people: Ward %s cut and Ward %s drawn"
                                % (gid, n, a or "none", b or "none"))
        xs = [v for _, _, bb in s_model for v in (bb[0], bb[2])]
        ys = [v for _, _, bb in s_model for v in (bb[1], bb[3])]
        rng = random.Random(int(geoid))
        agree = s_over = n_over = 0
        for _ in range(AGREEMENT_SAMPLES):
            pt = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
            a = blb._districts_at(s_model, pt)
            b = blb._districts_at(n_model, pt)
            s_over += len(a) > 1
            n_over += len(b) > 1
            agree += sorted(a) == sorted(b)
        print("people: %d of the 2020 census's residents get another ward drawn; agreement %d of "
              "%d seeded points; in two wards at %d points cut and %d drawn"
              % (moved, agree, AGREEMENT_SAMPLES, s_over, n_over), file=sys.stderr)
        if agree < MIN_AGREEMENT * AGREEMENT_SAMPLES:
            problems.append("%d of %d seeded points agree" % (agree, AGREEMENT_SAMPLES))
        if n_over > s_over:
            problems.append("the drawing adds overlap (%d seeded points against the cut wards' "
                            "%d)" % (n_over, s_over))
    return problems


def build():
    problems = []
    exact = {"type": "FeatureCollection", "features": []}
    blocks_by_city = {}
    for c in CITIES:
        print("%s (%s, sent %s)" % (c["city"], c["file"], c["sent"]), file=sys.stderr)
        raw = read_sent(c)
        place = fetch_place(c)
        wards, raw_union, p = cut(c, raw, place)
        problems += ["%s: %s" % (c["city"], x) for x in p]
        blocks = []
        for c3 in c["county3s"]:
            blocks += fetch_blocks(c3)
        p, near = people(c, raw_union, wards, place, blocks)
        problems += ["%s: %s" % (c["city"], x) for x in p]
        blocks_by_city[c["geoid"]] = near
        for w in sorted(wards, key=_order):
            exact["features"].append({
                "type": "Feature",
                "properties": {"geoid": c["geoid"], "city": c["city"], "ward": w,
                               "seat": "Ward %s" % w, "source": c["source"] + EDGE,
                               "sourceUrl": c["sourceUrl"]},
                "geometry": _geojson(wards[w]),
            })
    simple = simplify(exact)
    problems += drawn_checks(exact, simple, blocks_by_city)
    out = {"type": "FeatureCollection", "features": []}
    for f in simple["features"]:
        out["features"].append({"type": "Feature",
                                "properties": {k: f["properties"][k] for k in PROPS},
                                "geometry": f["geometry"]})
    out["features"].sort(key=lambda f: (f["properties"]["city"], _order(f["properties"]["ward"])))
    problems += check_data(out)
    if problems:
        fail("refusing to write:\n  " + "\n  ".join(problems))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")
    print("wv-city-wards -> %s: %d wards in %d cities, %d bytes"
          % (os.path.relpath(OUT, INSTANCE), len(out["features"]), len(CITIES),
             os.path.getsize(OUT)), file=sys.stderr)


# ------------------------------------------------------------------ check --
def check_data(fc):
    """What --check and the build both hold the drawn file to."""
    from shapely.geometry import shape
    problems = []
    want = [(c["geoid"], w) for c in CITIES for w in sorted(c["names"].values(), key=_order)]
    got = [(f["properties"].get("geoid"), f["properties"].get("ward")) for f in fc["features"]]
    if sorted(got) != sorted(want) or len(set(got)) != len(got):
        problems.append("the file draws %d wards, not CITIES' %d once each" % (len(got), len(want)))
    by_geoid = {c["geoid"]: c for c in CITIES}
    for f in fc["features"]:
        p = f["properties"]
        c = by_geoid.get(p.get("geoid"))
        if c is None:
            continue
        if set(p) != set(PROPS):
            problems.append("Ward %s carries %s" % (p.get("ward"), sorted(p)))
        if (p.get("city") != c["city"] or p.get("seat") != "Ward %s" % p.get("ward") or
                p.get("source") != c["source"] + EDGE or p.get("sourceUrl") != c["sourceUrl"]):
            problems.append("%s Ward %s: its properties are not CITIES'" % (c["city"], p.get("ward")))
    shapes = [shape(f["geometry"]) for f in fc["features"]]
    used = set()
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            if not shapes[i].intersects(shapes[j]):
                continue
            pair = sorted([got[i][1], got[j][1]], key=_order)
            for part in _polygons(shapes[i].intersection(shapes[j])):
                m2 = _part_m2(part)
                if m2 < OVERLAP_MIN_M2:
                    continue
                hit = [k for k, rec in enumerate(ACCEPTED_OVERLAPS)
                       if k not in used and rec["geoid"] == got[i][0] == got[j][0]
                       and sorted(rec["wards"], key=_order) == pair and _matches(rec, part, m2)]
                if hit:
                    used.add(hit[0])
                else:
                    rp = part.representative_point()
                    problems.append("Wards %s and %s both cover %.2f m2 at %.6f,%.6f as drawn, "
                                    "which nothing records" % (pair[0], pair[1], m2, rp.y, rp.x))
    for k, rec in enumerate(ACCEPTED_OVERLAPS):
        if k not in used:
            problems.append("ACCEPTED_OVERLAPS records Wards %s covering %.2f m2 at %.6f,%.6f, "
                            "and no such overlap is drawn"
                            % (" and ".join(rec["wards"]), rec["m2"], rec["lat"], rec["lng"]))
    return problems


def check():
    from shapely.geometry import shape
    with open(OUT, encoding="utf-8") as fh:
        fc = json.load(fh)
    problems = check_data(fc)
    for c in CITIES:
        raw = read_sent(c)
        lat0 = _lat0(list(raw.values()))
        for f in fc["features"]:
            p = f["properties"]
            if p.get("geoid") != c["geoid"] or p.get("ward") not in raw:
                continue
            g = shape(f["geometry"])
            mine = raw[p["ward"]]
            share = _m2(g.intersection(mine), lat0) / _m2(g, lat0)
            if not mine.contains(g.representative_point()) or share < CHECK_INSIDE_SHARE:
                problems.append("%s Ward %s as drawn is %.1f%% inside the city's own Ward %s"
                                % (c["city"], p["ward"], 100 * share, p["ward"]))
    with open(APP_FILE, encoding="utf-8") as fh:
        app = fh.read()
    names = [c["city"] for c in CITIES]
    sentence = "This map draws the wards of %s" % (names[0] if len(names) == 1 else
                                                    ", ".join(names[:-1]) + " and " + names[-1])
    if sentence not in app:
        problems.append("wv/index.html's City Council Ward empty note does not say %r" % sentence)
    listed = re.search(r'var WV_WARD_CITIES = \[([^\]]*)\];', app)
    geoids = sorted(re.findall(r'"(\d+)"', listed.group(1))) if listed else None
    if geoids != sorted(c["geoid"] for c in CITIES):
        problems.append("wv/index.html's WV_WARD_CITIES lists %s, not CITIES' %s"
                        % (geoids, sorted(c["geoid"] for c in CITIES)))
    if problems:
        print("wv-city-wards --check: FAIL\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print("wv-city-wards --check: OK (%d wards in %s, each inside the city's own ward, kept "
          "files as sent)" % (len(fc["features"]), ", ".join(names)))
    return 0


def main(argv):
    if "--check" in argv[1:]:
        return check()
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
