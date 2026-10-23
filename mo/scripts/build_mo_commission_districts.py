#!/usr/bin/env python3
"""
Build Missouri's county commission districts for the counties whose own
published maps draw them: data/app/mo-commission-districts.json (the lines)
and data/app/mo-commission-counties.json (the list of drawn counties, which
the layer's coverage test reads).

WHY THESE COUNTIES AND NO OTHERS. RSMo 49.010 has each county commission
divide its county into two districts "of contiguous territory, as nearly equal
in population as practicable, without dividing municipal townships", and RSMo
49.020 has each district elect one commissioner. No statewide map of the lines
exists (gap mo-county-commission-district-lines records the search and the
Secretary of State's two answers), so a county joins when its own published
map draws them. Measured 2026-10-23, 21 counties' public map viewers, all
built by one vendor (Integrity GIS, on its Geocortex Essentials servers),
carry a layer named Commissioner District that any visitor can query, and
Cole County's regional GIS office (midmogis.org, for Jefferson City and Cole
County) offers the lines as a shapefile download. And Lawrence County posts a
scanned map of its two districts whose lines run along whole townships; its
clerk pointed to that map when asked (2026-10-23), so its districts are drawn
as the union of the Census Bureau's township lines the map names (TOWNSHIPS
below). And Cass County's GIS office, in the Assessor's office, e-mailed this
project a shapefile of its two districts on 2026-10-23 after its clerk passed
on the request; the file is kept under data/source/raw/ (SENT below). And
Saline County's clerk listed, on 2026-10-23, the townships and precincts in
each of its two districts: whole townships but for Marshall, which its city's
wards split, so Saline is drawn from TIGER's township lines and, inside
Marshall township, the Census Bureau's 2020 voting districts, whose four
Marshall wards tile that township (LISTED below). Those 25 are SOURCES below.
The other 89 counties and the City of St. Louis are not
drawn, and the layer is hidden there; the County card names every county's commissioners either
way.

WHAT IS CHECKED, AND WHAT IS NOT. Every build refuses a county unless:
  - its source answers exactly two districts, and each district's name maps
    to one of the two district seats the Secretary of State's 2025-2026
    Missouri Roster prints for that county (mo-county-officials.json), so a
    district is never drawn under a seat the roster does not have;
  - the two districts cover the county as state-counties.json draws it to
    within MAX_GAP and overlap each other by no more than MAX_OVERLAP.
It also counts the 2020 census population of each district from the Census
Bureau's block points and records it, with the spread between the two, in
the counties file. That spread is a measurement and not a gate: the statute
asks for districts as nearly equal "as practicable" without splitting
townships, which allows a wide spread, and the statute sets no date by which
a county must redraw. So NOTHING HERE PROVES A COUNTY'S MAP IS THE ONE ITS
ELECTIONS USE TODAY. A county may have redrawn and left its viewer behind.
The card says where the line comes from and that it has not been checked
against the election records. The Secretary of State's office offered, on
2026-10-22 (Sunshine request SUN0000590), a report for each county listing
every precinct split with its commission district; that report is the check
this builder does not yet have, and it is held on Adam's word of 2026-10-23.

THE DRAWN LINE TILES THE COUNTY CARD'S COUNTY EXACTLY. One district (the
first in the pair) is clipped to the county as state-counties.json draws it,
simplified by Douglas-Peucker at SIMPLIFY_M metres in an equal-area
projection, and clipped again; the other is the rest of the county. So the
two never overlap, never leave a gap, and agree with the County card about
the county at every point: inside a drawn county a point is in exactly one
district. The price is that the county edge is the County card's simplified
edge rather than the viewer's. The line between the two districts is held
to FIDELITY_MAX_M: every vertex of the source's own dividing line must lie
within that distance of the drawn one.

Build (network: the viewers, the Cole download and TIGERweb; Cass's file is
read from disk; shapely and
pyproj):
    python3 mo/scripts/build_mo_commission_districts.py
Check (offline, stdlib only; in CI):
    python3 mo/scripts/build_mo_commission_districts.py --check
"""

import datetime
import io
import json
import math
import os
import random
import re
import struct
import sys
import time
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

REPO_ROOT = os.path.dirname(_HERE)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
sys.path.append(os.path.join(os.path.dirname(REPO_ROOT), "scripts"))
from scraper_common import UA_HEADERS_ROSTER_BOT, require_robots_once  # noqa: E402

OUT_FILE = os.path.join(APP_DATA_DIR, "mo-commission-districts.json")
COUNTIES_OUT = os.path.join(APP_DATA_DIR, "mo-commission-counties.json")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
ROSTER_FILE = os.path.join(APP_DATA_DIR, "mo-county-officials.json")
STATE = "29"

# Integrity GIS's public Geocortex servers. A site's map lists its map
# services, and a layer is queried anonymously through the site's own proxy.
IGIS = ("https://%s.integritygis.com/Geocortex/Essentials/REST/sites/%s/map/"
        "mapservices/%s/rest/services/x/MapServer/%s/query")
VIEWER = "https://%s.integritygis.com/Geocortex/Essentials/REST/sites/%s/map"
BLOCKS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
          "Tracts_Blocks/MapServer/12/query")
SOURCE_VIEWER = "the county's map viewer, its Commissioner District layer"
COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
          "Places_CouSub_ConCity_SubMCD/MapServer/1/query")
VTD2020 = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
           "tigerWMS_Census2020/MapServer/58/query")
RAW_DIR = os.path.join(REPO_ROOT, "data", "source", "raw")
SOURCE_COLE = ("the Jefferson City and Cole County GIS office (midmogis.org), "
               "its download of the commissioner districts")

# County FIPS (3 digits) -> where its lines come from and how the source names
# each district, mapped to the seat the Missouri Roster prints. Measured
# 2026-10-23: each viewer answers two features with exactly these names.
SOURCES = {
    "011": {"viewer": ("camdengis", "Barton_County_MO", "10", "189"),
            "names": {"DISTRICT 1": "District One", "DISTRICT 2": "District Two"}},
    "013": {"viewer": ("christiangis", "Bates_County_MO", "1", "52"),
            "names": {"NORTHERN COMMISSIONER": "Northern District",
                      "SOUTHERN COMMISSIONER": "Southern District"}},
    "021": {"viewer": ("phelpsgis", "Buchanan_Co_MO", "5", "6"),
            "names": {"Eastern District": "Eastern District",
                      "Western District": "Western District"}},
    "029": {"viewer": ("camdengis", "Camden_County_MO", "1", "39"), "field": "DISTRICT",
            "names": {"1ST DISTRICT": "First District", "2ND DISTRICT": "Second District"}},
    "041": {"viewer": ("christiangis", "Chariton_County_MO", "7", "52"),
            "names": {"EASTERN COMMISSIONER'S DISTRICT": "Eastern District",
                      "WESTERN COMMISSIONER'S DISTRICT": "Western District"}},
    "043": {"viewer": ("christiangis", "Christian_County_MO", "7", "104"),
            "names": {"EASTERN DISTRICT": "Eastern District",
                      "WESTERN DISTRICT": "Western District"}},
    "051": {"zip": "https://www.midmogis.org/GIS_Hyperlinks/Downloadables/CC_Commissioner.zip",
            "member": "COMM_DISTS_Layer", "field": "DISTRICT",
            "names": {"Eastern": "Eastern District", "Western": "Western District"}},
    "053": {"viewer": ("christiangis", "Cooper_County_MO", "3", "53"),
            "names": {"EASTERN DISTRICT": "Eastern District",
                      "WESTERN DISTRICT": "Western District"}},
    "057": {"viewer": ("christiangis", "Dade_County_MO", "1", "167"),
            "names": {"EASTERN COMMISSIONER'S DISTRICT": "Eastern District",
                      "WESTERN COMMISSIONER'S DISTRICT": "Western District"}},
    "063": {"viewer": ("christiangis", "Dekalb_County_MO", "11", "62"),
            "names": {"EASTERN COMMISSIONER DISTRICT": "Eastern District",
                      "WESTERN COMMISSIONER DISTRICT": "Western District"}},
    # Lawrence's map (lawrencecountymo.org, a 2024 scan, read 2026-10-23)
    # outlines its Eastern District around six whole townships, and its
    # township and precinct areas match TIGER's 14 townships: Mount Vernon's
    # three precincts all lie west of the line and Aurora's three east of it.
    "109": {"townships": {
                "Eastern District": ["Aurora", "Buck Prairie", "Freistatt", "Ozark",
                                     "Spring River", "Turnback"],
                "Western District": ["Green", "Hoberg", "Lincoln", "Mount Pleasant",
                                     "Mount Vernon", "Pierce", "Red Oak", "Vineyard"]},
            "map": ("https://www.lawrencecountymo.org/_files/ugd/"
                    "e487e4_0038fc0bb16742e8b9dc74b091ced286.pdf"),
            "clerk": "2026-10-23"},
    # Cass County GIS (Lisa Mendpara, PMM, in the Assessor's office) e-mailed
    # this shapefile on 2026-10-23 after the clerk forwarded the request. Its
    # metadata was last synced 2022-04-28, and the county's own district map
    # (sent with it) draws the same two areas: District 2 the northwest,
    # Belton, Raymore and Peculiar, and District 1 the rest. The files are
    # kept as sent and held to their SHA-256 below.
    "037": {"file": "cass-commission-districts/commission", "field": "District",
            "sha256": {
                "shp": "10d69d775098334c8717689fbba58ee6625791120065cbce6bbb73957e4af354",
                "shx": "0df31e0c3cce5f5da1ef99b75552b7ec22b8f8f5208b9268eff4f835075b7328",
                "dbf": "4105dcbdbadef6ccaaf2581f01543fb3a622e6c8e828c93ba19fd5c1b5865e6d",
                "prj": "1e84a19d8fa23d2f23c0cdd5d16cc096abe8ee6235eeb391a139484fbcd35654"},
            "names": {"1": "District 1", "2": "District 2"},
            "sent": "2026-10-23"},
    # Saline's clerk (Brittni Allison Burton) answered on 2026-10-23 with the
    # townships and precincts each district holds, and a 2011 map of the
    # line. Every township is whole but Marshall, whose Wards 3 and 4 are in
    # the Northern District and Wards 1 and 2 in the Southern. Salt Fork is
    # not in her list because it votes with Blackwater (the Census's 2020
    # "Blackwater/Salt Fork" precinct), and her map puts it in the Southern
    # District. The Census's 2020 Marshall 1-4 voting districts tile Marshall
    # township, 3 and 4 in its north half, and their line runs as the map's
    # does through the township. Marshall may have redrawn its wards since
    # 2020, which this does not see.
    "195": {"townships": {
                "Northern District": ["Cambridge", "Clay", "Grand Pass", "Miami"],
                "Southern District": ["Arrow Rock", "Blackwater", "Elmwood", "Liberty",
                                      "Salt Fork", "Salt Pond"]},
            "precincts": {"Marshall": {
                "Northern District": ["Marshall 3", "Marshall 4"],
                "Southern District": ["Marshall 1", "Marshall 2"]}},
            "listed": "2026-10-23"},
    "113": {"viewer": ("phelpsgis", "Lincoln_County_MO", "1", "35"),
            "names": {"DISTRICT I": "First District", "DISTRICT II": "Second District"}},
    "119": {"viewer": ("christiangis", "McDonald_County_MO", "2", "35"), "field": "district_n",
            "names": {"EASTERN COMMISSIONER DISTRICT": "Eastern District",
                      "WESTERN COMMISSIONER DISTRICT": "Western District"}},
    "125": {"viewer": ("phelpsgis", "Maries_County_MO", "3", "40"),
            "names": {"EAST COMMISSIONER DISTRICT": "Eastern District",
                      "WEST COMMISSIONER DISTRICT": "Western District"}},
    "127": {"viewer": ("phelpsgis", "Marion_County_MO_Public", "12", "40"),
            "names": {"EASTERN COMMISSIONER'S DISTRICT": "Eastern District",
                      "WESTERN COMMISSIONER'S DISTRICT": "Western District"}},
    "131": {"viewer": ("phelpsgis", "Miller_County_MO", "2", "28"), "field": "Name",
            "names": {"1st Commissioners District": "First District",
                      "2nd Commissioners District": "Second District"}},
    "161": {"viewer": ("phelpsgis", "Phelps_County_MO_Public", "8", "78"),
            "names": {"DISTRICT 1": "District 1", "DISTRICT 2": "District 2"}},
    "167": {"viewer": ("christiangis", "Polk_County_MO", "1", "51"),
            "names": {"NORTH": "Northern District", "SOUTH": "Southern District"}},
    "169": {"viewer": ("christiangis", "Pulaski_County_MO", "1", "44"),
            "names": {"EASTERN": "Eastern District", "WESTERN": "Western District"}},
    "173": {"viewer": ("christiangis", "Ralls_County_MO", "3", "44"),
            "names": {"EASTERN COMMISSIONER DISTRICT": "Eastern District",
                      "WESTERN COMMISSIONER DISTRICT": "Western District"}},
    "177": {"viewer": ("christiangis", "Ray_County_MO", "11", "61"),
            "names": {"EASTERN DISTRICT": "Eastern District",
                      "WESTERN DISTRICT": "Western District"}},
    "217": {"viewer": ("phelpsgis", "Vernon_County_MO", "2", "38"),
            "names": {"NORTH": "Northern District", "SOUTH": "Southern District"}},
    "219": {"viewer": ("christiangis", "Warren_County_MO", "3", "44"),
            "names": {"District 1": "District 1", "District 2": "District 2"}},
}

# The source's two districts must cover the County card's county to within
# MAX_GAP of its area, reach outside it by no more than MAX_GAP, and overlap
# each other by no more than MAX_OVERLAP. Measured 2026-10-23 the worst gap
# was 0.19% (Camden, along the Lake of the Ozarks shore) and the worst
# overlap 0.001% (Phelps).
MAX_GAP = 0.005
MAX_OVERLAP = 0.0005
SIMPLIFY_M = 5.0
FIDELITY_MAX_M = 8.0
# A county line drawn by the County card and the line between the districts
# meet; within this distance of a county line the witness does not count a
# disagreement (the two files are rounded to 6 decimals on their own).
EDGE_M = 2.0
WITNESS_SAMPLES = 2000
CRS_EQUAL_AREA = "EPSG:5070"  # NAD83 / Conus Albers, metres
UA = UA_HEADERS_ROSTER_BOT["User-Agent"]


# ---------- fetching (build only) ----------

def _get(url, params=None, binary=False):
    import requests  # noqa: PLC0415 (only the build path needs it)
    require_robots_once(url, UA, headers=UA_HEADERS_ROSTER_BOT,
                        label="mo-build-commission-districts")
    # A reset connection is retried twice; an HTTP error status is not.
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=UA_HEADERS_ROSTER_BOT, timeout=120)
            break
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise
            time.sleep(4 * (attempt + 1))
    resp.raise_for_status()
    if binary:
        return resp.content
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer: never read a default here.
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def _layer_named(site_map, ms, layer_id):
    """The name the viewer's own map gives the layer, so a renumbered layer
    is caught rather than read as commission districts."""
    for svc in site_map.get("mapServices") or []:
        if str(svc.get("id")) != str(ms):
            continue
        stack = list(svc.get("layers") or [])
        while stack:
            lay = stack.pop()
            if str(lay.get("id")) == str(layer_id):
                return lay.get("name") or lay.get("displayName")
            stack.extend(lay.get("layers") or [])
    return None


def _esri_rings_to_shape(rings):
    """ArcGIS rings to one shapely geometry. An outer ring winds clockwise
    and a hole counter-clockwise (shapefiles share the rule)."""
    from shapely.geometry import LinearRing, Polygon  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    outers, holes = [], []
    for r in rings:
        if len(r) < 4:
            continue
        (holes if LinearRing(r).is_ccw else outers).append(Polygon(r))
    polys = []
    for o in outers:
        inner = [h.exterior.coords for h in holes if o.contains(h.representative_point())]
        polys.append(Polygon(o.exterior.coords, inner).buffer(0))
    return unary_union(polys)


def fetch_viewer(spec):
    host, site, ms, layer = spec["viewer"]
    site_map = _get(VIEWER % (host, site), {"f": "json"})
    name = _layer_named(site_map, ms, layer)
    if not name or not re.match(r"Commissioners? Districts?$", name):
        raise RuntimeError("%s map service %s layer %s is %r, not the Commissioner "
                           "District layer" % (site, ms, layer, name))
    data = _get(IGIS % (host, site, ms, layer), {
        "where": "1=1", "outFields": "*", "returnGeometry": "true",
        "outSR": "4326", "f": "json"})
    if data.get("exceededTransferLimit"):
        raise RuntimeError("%s: the commissioner layer hit the transfer cap" % site)
    field = spec.get("field", "NAME")
    out = []
    for f in data.get("features") or []:
        out.append((f["attributes"].get(field), _esri_rings_to_shape(f["geometry"]["rings"])))
    return out


def fetch_split_township(c3, township, shape_, seats):
    """A township a county splits by precinct, as {seat: part}, from the
    Census Bureau's 2020 voting districts. The precincts named must be every
    voting district inside the township, and together they must tile it."""
    from shapely.ops import unary_union  # noqa: PLC0415
    data = _get(VTD2020, {
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE, c3),
        "outFields": "NAME", "returnGeometry": "true", "outSR": "4326", "f": "json"})
    if data.get("error"):
        raise RuntimeError("county %s voting districts: %r" % (c3, data["error"]))
    inside = {}
    for f in data.get("features") or []:
        g = _esri_rings_to_shape(f["geometry"]["rings"])
        if g.intersection(shape_).area > 0.5 * g.area:
            inside[f["attributes"]["NAME"].replace(" Voting District", "")] = g
    named = [p for ps in seats.values() for p in ps]
    if sorted(named) != sorted(inside) or len(set(named)) != len(named):
        raise RuntimeError("county %s %s: SOURCES names precincts %r, the Census draws %r"
                           % (c3, township, sorted(named), sorted(inside)))
    whole = unary_union(list(inside.values()))
    if whole.symmetric_difference(shape_).area > 0.001 * shape_.area:
        raise RuntimeError("county %s: the %s precincts do not tile the township"
                           % (c3, township))
    return {seat: unary_union([inside[p] for p in ps]).intersection(shape_)
            for seat, ps in seats.items()}


def fetch_townships(c3, spec):
    """The county's districts as unions of whole TIGER townships, and of the
    parts of any township SOURCES splits by precinct. Every township the
    Census draws in the county must be named in exactly one district or
    split, so a township added or renamed stops the build."""
    from shapely.ops import unary_union  # noqa: PLC0415
    data = _get(COUSUB, {
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE, c3),
        "outFields": "BASENAME", "returnGeometry": "true", "outSR": "4326", "f": "json"})
    if data.get("error"):
        raise RuntimeError("county %s townships: %r" % (c3, data["error"]))
    shapes = {}
    for f in data.get("features") or []:
        shapes[f["attributes"]["BASENAME"]] = _esri_rings_to_shape(f["geometry"]["rings"])
    split = spec.get("precincts") or {}
    named = [t for ts in spec["townships"].values() for t in ts] + list(split)
    if sorted(named) != sorted(shapes) or len(set(named)) != len(named):
        raise RuntimeError("county %s: SOURCES names townships %r, the Census draws %r"
                           % (c3, sorted(named), sorted(shapes)))
    parts = {seat: [shapes[t] for t in ts] for seat, ts in spec["townships"].items()}
    for township, seats in split.items():
        if sorted(seats) != sorted(parts):
            raise RuntimeError("county %s %s: split among %r, not the districts %r"
                               % (c3, township, sorted(seats), sorted(parts)))
        for seat, part in fetch_split_township(c3, township, shapes[township], seats).items():
            parts[seat].append(part)
    return [(seat, unary_union(ps).buffer(0)) for seat, ps in sorted(parts.items())]


def _source_kind(spec):
    return ("cole" if "zip" in spec else "listed" if "listed" in spec
            else "townships" if "townships" in spec
            else "sent" if "file" in spec else "viewer")


def _dbf_rows(raw):
    n, header_len, rec_len = struct.unpack("<IHH", raw[4:12])
    fields, o = [], 32
    while raw[o] != 0x0D:
        fields.append((raw[o:o + 11].split(b"\0")[0].decode(), raw[o + 16]))
        o += 32
    rows = []
    for i in range(n):
        rec, p, row = raw[header_len + i * rec_len + 1:header_len + (i + 1) * rec_len], 0, {}
        for name, length in fields:
            row[name] = rec[p:p + length].decode("latin-1").strip()
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
            raise RuntimeError("shapefile record is not a polygon")
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


def fetch_zip(spec):
    from pyproj import Transformer  # noqa: PLC0415
    zf = zipfile.ZipFile(io.BytesIO(_get(spec["zip"], binary=True)))
    m = spec["member"]
    prj = zf.read(m + ".prj").decode("latin-1")
    t = Transformer.from_crs(prj, "EPSG:4326", always_xy=True)
    rings = _shp_polygons(zf.read(m + ".shp"), t.transform)
    rows = _dbf_rows(zf.read(m + ".dbf"))
    if len(rings) != len(rows):
        raise RuntimeError("%s: %d shapes and %d records" % (spec["zip"], len(rings), len(rows)))
    return [(row.get(spec["field"]), _esri_rings_to_shape(r)) for row, r in zip(rows, rings)]


def _raw_file(spec, ext):
    import hashlib  # noqa: PLC0415
    path = os.path.join(RAW_DIR, spec["file"] + "." + ext)
    with open(path, "rb") as fh:
        raw = fh.read()
    if hashlib.sha256(raw).hexdigest() != spec["sha256"][ext]:
        raise RuntimeError("%s is not the file the county sent" % os.path.relpath(path, REPO_ROOT))
    return raw


def read_sent(spec):
    """A shapefile a county sent, kept under data/source/raw/."""
    from pyproj import Transformer  # noqa: PLC0415
    t = Transformer.from_crs(_raw_file(spec, "prj").decode("latin-1"), "EPSG:4326",
                             always_xy=True)
    _raw_file(spec, "shx")
    rings = _shp_polygons(_raw_file(spec, "shp"), t.transform)
    rows = _dbf_rows(_raw_file(spec, "dbf"))
    if len(rings) != len(rows):
        raise RuntimeError("%s: %d shapes and %d records" % (spec["file"], len(rings), len(rows)))
    return [(row.get(spec["field"]), _esri_rings_to_shape(r)) for row, r in zip(rows, rings)]


def fetch_block_points(c3):
    """Every populated 2020 census block in the county, as (lng, lat, people)
    at its internal point."""
    pts, offset = [], 0
    while True:
        data = _get(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, c3),
            "outFields": "INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
            "resultOffset": offset, "resultRecordCount": 2000, "f": "json"})
        feats = data.get("features") or []
        pts += [(float(a["attributes"]["INTPTLON"]), float(a["attributes"]["INTPTLAT"]),
                 int(a["attributes"]["POP100"])) for a in feats]
        if len(feats) < 2000:
            return pts
        offset += 2000


# ---------- shared reading ----------

def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def district_seats(roster, geoid):
    o = roster.get(geoid) or {}
    return [s["seat"] for s in o.get("seats") or [] if not s.get("countywide")]


# ---------- build ----------

def build_county(c3, spec, county_feature, roster, today):
    from pyproj import Transformer  # noqa: PLC0415
    from shapely.geometry import Point, mapping, shape  # noqa: PLC0415
    from shapely.ops import transform as shp_transform  # noqa: PLC0415
    geoid = STATE + c3
    name = county_feature["properties"]["NAME"]
    if "townships" in spec:
        got = fetch_townships(c3, spec)
        spec = dict(spec, names={seat: seat for seat in spec["townships"]})
    else:
        got = (fetch_zip(spec) if "zip" in spec else read_sent(spec) if "file" in spec
               else fetch_viewer(spec))
    if len(got) != 2:
        raise RuntimeError("%s: the source answers %d districts, not 2" % (name, len(got)))
    seats = district_seats(roster, geoid)
    names = [n for n, _ in got]
    if sorted(names) != sorted(spec["names"]):
        raise RuntimeError("%s: the source names %r, SOURCES expects %r"
                           % (name, names, sorted(spec["names"])))
    if sorted(spec["names"].values()) != sorted(seats):
        raise RuntimeError("%s: SOURCES maps to seats %r, the roster prints %r"
                           % (name, sorted(spec["names"].values()), seats))
    county = shape(county_feature["geometry"]).buffer(0)
    a, b = got[0][1], got[1][1]
    union = a.union(b)
    gap = county.difference(union).area / county.area
    outside = union.difference(county).area / county.area
    overlap = a.intersection(b).area / county.area
    if gap > MAX_GAP or outside > MAX_GAP or overlap > MAX_OVERLAP:
        raise RuntimeError("%s: gap %.4f, outside %.4f, overlap %.5f of the county"
                           % (name, gap, outside, overlap))
    fwd = Transformer.from_crs("EPSG:4326", CRS_EQUAL_AREA, always_xy=True).transform
    inv = Transformer.from_crs(CRS_EQUAL_AREA, "EPSG:4326", always_xy=True).transform
    county_m = shp_transform(fwd, county)
    a_src = _polygonal(shp_transform(fwd, a).intersection(county_m))
    b_src = _polygonal(shp_transform(fwd, b).intersection(county_m))
    # Ground inside the County card's county that neither source district
    # reaches (slivers where the two files draw the county line apart) goes to
    # the district it shares the longer edge with, so a point there is
    # answered by the district beside it rather than by whichever district
    # the complement happens to hand it to.
    a_given, b_given = a_src, b_src
    rest = county_m.difference(a_src.union(b_src))
    for piece in getattr(rest, "geoms", [rest]):
        if piece.is_empty or piece.geom_type != "Polygon":
            continue
        # how much of each district lies within a metre of the sliver: the
        # length of edge they share, in square metres
        ring = piece.buffer(1.0)
        if ring.intersection(a_src).area >= ring.intersection(b_src).area:
            a_src = a_src.union(piece)
        else:
            b_src = b_src.union(piece)
    a_draw = _polygonal(a_src.simplify(SIMPLIFY_M, preserve_topology=True).intersection(county_m))
    # The source's own dividing line, where its two districts agree about it:
    # the first district's boundary within a metre of the second's, away from
    # the county edge. Where the source's two districts leave a sliver between
    # them or overlap, the source itself puts the line in two places, and the
    # sliver went to one side above; those stretches are not measured.
    inner = (a_given.boundary.intersection(b_given.boundary.buffer(1.0))
             .difference(county_m.boundary.buffer(SIMPLIFY_M * 4)))
    worst = 0.0
    drawn_line = a_draw.boundary
    for geom in getattr(inner, "geoms", [inner]):
        for x, y in getattr(geom, "coords", []):
            worst = max(worst, drawn_line.distance(Point(x, y)))
    if worst > FIDELITY_MAX_M:
        raise RuntimeError("%s: the drawn dividing line strays %.1f m from the source's, "
                           "over the %.1f m ceiling" % (name, worst, FIDELITY_MAX_M))
    # Round the first district to the file's 6 decimals, then take the
    # other as the rest of the County card's county, so the pair still tiles
    # it after rounding.
    a_out = _rounded(shp_transform(inv, a_draw))
    b_out = _rounded(county.difference(a_out))
    # Simplifying the first district pulls its edge along the county line a
    # few metres inward, and the second, taken as the rest of the county,
    # would get those strips as detached parts. A part of the second that
    # lies mostly in the first district's source ground is given back to the
    # first, so the strip is answered as the district the source puts it in.
    a_src_ll = shp_transform(inv, a_src)
    back = [part for part in getattr(b_out, "geoms", [b_out])
            if part.intersection(a_src_ll).area > 0.5 * part.area]
    if back:
        from shapely.ops import unary_union  # noqa: PLC0415
        a_out = _rounded(unary_union([a_out] + back))
        b_out = _rounded(county.difference(a_out))
    feats = []
    for (src_name, _), geom in zip(got, (a_out, b_out)):
        feats.append({"type": "Feature", "properties": {
            "county": name, "countyfips": geoid, "seat": spec["names"][src_name],
            "source": _source_kind(spec), "read": today},
            "geometry": mapping(geom)})
        if spec.get("clerk"):
            feats[-1]["properties"]["pointedOn"] = spec["clerk"]
        if spec.get("sent"):
            feats[-1]["properties"]["sentOn"] = spec["sent"]
        if spec.get("listed"):
            feats[-1]["properties"]["listedOn"] = spec["listed"]
    people = {spec["names"][n]: 0 for n in names}
    unplaced = 0
    for x, y, p in fetch_block_points(c3):
        pt = Point(x, y)
        hit = [spec["names"][n] for n, g in got if g.contains(pt)]
        if hit:
            people[hit[0]] += p
        else:
            unplaced += p
    vals = list(people.values())
    spread = abs(vals[0] - vals[1]) / (sum(vals) / 2.0) * 100 if sum(vals) else None
    record = {"county": name, "source": feats[0]["properties"]["source"], "read": today,
              "people2020": people, "spreadPct": round(spread, 1),
              "unplaced2020": unplaced}
    print("  %-18s %-36s gap %.4f overlap %.5f stray %4.1f m  2020: %s  spread %.1f%%"
          % (name, " / ".join(sorted(people)), gap, overlap, worst,
             ", ".join("%d" % v for v in vals), spread))
    return feats, record


def _polygonal(g):
    """The polygons of a geometry, dropping the lines and points an
    intersection or a rounding can leave beside them."""
    from shapely.geometry import MultiPolygon  # noqa: PLC0415
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    polys = []
    for part in getattr(g, "geoms", []):
        if part.geom_type == "Polygon":
            polys.append(part)
        elif part.geom_type == "MultiPolygon":
            polys.extend(part.geoms)
    return MultiPolygon(polys)


def _rounded(geom):
    from shapely import make_valid, set_precision  # noqa: PLC0415
    return _polygonal(set_precision(make_valid(geom), 1e-6))


def build():
    today = datetime.date.today().isoformat()
    roster = load_json(ROSTER_FILE)
    counties = {f["properties"]["GEOID"]: f for f in load_json(COUNTIES_FILE)["features"]}
    features, records = [], {}
    for c3, spec in sorted(SOURCES.items()):
        geoid = STATE + c3
        feats, rec = build_county(c3, spec, counties[geoid], roster, today)
        features += feats
        records[geoid] = rec
        time.sleep(1)
    out = {"type": "FeatureCollection", "features": features}
    problems = check_problems(out, records, counties, roster)
    if problems:
        raise SystemExit("FAIL:\n  " + "\n  ".join(problems))
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")
    with open(COUNTIES_OUT, "w") as fh:
        json.dump(records, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %d districts in %d counties to %s and %s"
          % (len(features), len(records), os.path.relpath(OUT_FILE, REPO_ROOT),
             os.path.relpath(COUNTIES_OUT, REPO_ROOT)))


# ---------- check (stdlib only) ----------

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ring_area_m2(ring):
    """Area on the sphere (the trapezoid rule on sin(latitude)), which adds up
    across a tiling where a flat projection per ring would not."""
    r = 6371008.8
    s = 0.0
    for i in range(len(ring) - 1):
        (x1, y1), (x2, y2) = ring[i][:2], ring[i + 1][:2]
        s += math.radians(x2 - x1) * (math.sin(math.radians(y1)) + math.sin(math.radians(y2))) / 2.0
    return abs(s) * r * r


def _area_m2(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return sum(_ring_area_m2(p[0]) - sum(_ring_area_m2(h) for h in p[1:]) for p in polys)


def check_problems(fc, records, counties, roster):
    problems = []
    by = {}
    for f in fc.get("features") or []:
        p = f.get("properties") or {}
        geoid = p.get("countyfips")
        where = "%s %s" % (geoid, p.get("seat"))
        by.setdefault(geoid, []).append(f)
        spec = SOURCES.get(str(geoid)[2:])
        if spec is None or not str(geoid).startswith(STATE):
            problems.append("%s: not a county in SOURCES" % where)
            continue
        c = counties.get(geoid)
        if not c or p.get("county") != c["properties"]["NAME"]:
            problems.append("%s: county name %r does not match state-counties.json"
                            % (where, p.get("county")))
        if p.get("seat") not in district_seats(roster, geoid):
            problems.append("%s: the roster prints no such district seat (it prints %r)"
                            % (where, district_seats(roster, geoid)))
        if p.get("source") != _source_kind(spec):
            problems.append("%s: source %r" % (where, p.get("source")))
        if p.get("pointedOn") != spec.get("clerk"):
            problems.append("%s: pointedOn %r, SOURCES says %r" % (where, p.get("pointedOn"),
                                                               spec.get("clerk")))
        if p.get("sentOn") != spec.get("sent"):
            problems.append("%s: sentOn %r, SOURCES says %r" % (where, p.get("sentOn"),
                                                            spec.get("sent")))
        if p.get("listedOn") != spec.get("listed"):
            problems.append("%s: listedOn %r, SOURCES says %r" % (where, p.get("listedOn"),
                                                              spec.get("listed")))
        if not _ISO_DATE.match(str(p.get("read") or "")):
            problems.append("%s: read %r is not a date" % (where, p.get("read")))
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            problems.append("%s: geometry %r" % (where, g.get("type")))
    want = {STATE + c3 for c3 in SOURCES}
    if set(by) != want:
        problems.append("drawn counties %s, SOURCES names %s" % (sorted(by), sorted(want)))
    if set(records) != want:
        problems.append("mo-commission-counties.json lists %s, SOURCES names %s"
                        % (sorted(records), sorted(want)))
    for geoid, feats in sorted(by.items()):
        seats = sorted(f["properties"]["seat"] for f in feats)
        if seats != sorted(district_seats(roster, geoid)):
            problems.append("%s draws %r, the roster prints %r"
                            % (geoid, seats, sorted(district_seats(roster, geoid))))
        c = counties.get(geoid)
        if c:
            ca = _area_m2(c["geometry"])
            da = sum(_area_m2(f["geometry"]) for f in feats)
            if abs(da - ca) / ca > 0.0005:
                problems.append("%s: the two districts' area is %.3f%% off the county's"
                                % (geoid, 100.0 * (da - ca) / ca))
        rec = records.get(geoid) or {}
        if sorted((rec.get("people2020") or {})) != seats:
            problems.append("%s: the counties file counts people in %r, not %r"
                            % (geoid, sorted(rec.get("people2020") or {}), seats))
        if c and rec.get("county") != c["properties"]["NAME"]:
            problems.append("%s: the counties file names %r" % (geoid, rec.get("county")))
    return problems


def witness(fc, counties, samples=WITNESS_SAMPLES, seed=2026):
    """Points over the drawn counties: inside one the County layer and this
    layer agree about the county and exactly one district answers; outside
    every drawn county no district answers. A miss within EDGE_M of a county
    line is counted apart (the files round on their own)."""
    drawn = sorted({f["properties"]["countyfips"] for f in fc["features"]})
    cmodel = [(g, f["geometry"], blb._bbox(f["geometry"])) for g, f in counties.items()]
    dmodel = [(f["properties"]["countyfips"], f["geometry"], blb._bbox(f["geometry"]))
              for f in fc["features"]]
    edges = {g: blb._seg_index(counties[g]) for g in drawn}
    rng = random.Random(seed)
    inside = agree = edge = 0
    bad = []
    for _ in range(samples):
        g0 = rng.choice(drawn)
        b = blb._bbox(counties[g0]["geometry"])
        pt = (rng.uniform(b[0], b[2]), rng.uniform(b[1], b[3]))
        cs = [g for g, geom, bb in cmodel if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        ds = [g for g, geom, bb in dmodel if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        county = cs[0] if len(cs) == 1 else None
        if county in edges:
            inside += 1
        ok = (ds == [county]) if county in edges else (not ds)
        if ok:
            agree += 1
            continue
        near = False
        for g in drawn:
            gx, gy = int(math.floor(pt[0] / 0.02)), int(math.floor(pt[1] / 0.02))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for a, bb2 in edges[g].get((gx + dx, gy + dy), ()):
                        if blb._point_to_segment_m(pt, a, bb2) <= EDGE_M:
                            near = True
        if near:
            edge += 1
        else:
            bad.append((round(pt[1], 5), round(pt[0], 5), county, ds))
    return inside, agree, edge, bad


def check():
    fc = load_json(OUT_FILE)
    records = load_json(COUNTIES_OUT)
    counties = {f["properties"]["GEOID"]: f for f in load_json(COUNTIES_FILE)["features"]}
    roster = load_json(ROSTER_FILE)
    problems = check_problems(fc, records, counties, roster)
    inside, agree, edge, bad = witness(fc, counties)
    if bad:
        problems.append("%d witness points disagree away from a county line, e.g. %r"
                        % (len(bad), bad[:3]))
    if problems:
        raise SystemExit("build-mo-commission-districts: FAIL\n  " + "\n  ".join(problems))
    print("build-mo-commission-districts: OK — %d districts in %d counties, each pair the "
          "roster's two district seats and the county's whole area; witness %d/%d agree "
          "(%d inside a drawn county, %d within %.0f m of a county line)"
          % (len(fc["features"]), len(records), agree, WITNESS_SAMPLES, inside, edge, EDGE_M))


def main():
    if "--check" in sys.argv[1:]:
        check()
    else:
        build()


if __name__ == "__main__":
    main()
