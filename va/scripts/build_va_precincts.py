#!/usr/bin/env python3
"""
Build va/data/app/va-precincts.json: Virginia's 2,531 election precincts,
from the Department of Elections' statewide layer of districts and precincts.

    python3 va/scripts/build_va_precincts.py            # fetch, check, write
    python3 va/scripts/build_va_precincts.py --check    # offline
    python3 va/scripts/build_va_precincts.py --watch    # has the layer changed?

The work is scripts/statewide_precincts.py, shared with seven other states;
this file says where Virginia's layer is, how to read one record, how its
pieces are joined, and what to expect.

THE SOURCE. "Districts Union Simplified", layer 0 of the Department of
Elections' hosted service (item f3eb2c0a525d494da8e6190ff2b13182), the layer
behind the Department's redistricting maps. Its data was last edited on
22 September 2026 (measured 2026-10-30). It carries, for every piece, the
county or city, the precinct, the local election district the precinct
votes in (`DistNumber`, `DistName`) and the congressional, Senate and House
districts. The Department also publishes one zipped shapefile per county and
city; measured 2026-10-30 against all 133, the statewide layer holds the same
precincts with the same lines (half the precincts' outlines within 0.0 m of
the package's, 99 in 100 within 1.3 m) and is the newer of the two: Norfolk's
package, dated March 2026, has no precinct 416, which the layer carves out of
precinct 405, and five packages dated 11 September 2026 match the layer.

THE TERMS. Asked by letter on 2026-10-27 whether its district and precinct
files may be used with credit, the Department answered on 2026-10-30 (Brian
Tynes): "The shapefiles on the website are available to anyone pursuant to
§ 24.2-103.1 of the Code of Virginia." The answer names the county and city
shapefiles; this layer holds the same precincts with the same lines, as
measured above, so it is read as covering both. The card and the sources
page credit the Department.

A PRECINCT IS CUT INTO PIECES WHEREVER A LEGISLATIVE LINE CROSSES IT. The
layer is the union of the precinct map with the three legislative maps, so a
precinct split between two House districts is two records, and 7,271 records
make 2,531 precincts (measured 2026-10-30). The fetcher below joins them
into one shape per precinct with shapely before the shared builder sees
them, so the drawn file has no line inside a precinct. Three things are
dropped on the way, each counted and each held to the count measured on the
first build, so a changed layer stops the build rather than changing what is
dropped:

  - 155 records name no county and no precinct (61 of them water by the
    census's hydrography, 94 small pieces of land totalling 137 km2 along
    shores and county lines). They are left undrawn, so a reader there is
    told no precinct holds the point. The layer is asked only for records
    that name a county.
  - 9 records carry no geometry. Each is a sliver of at most 0.016 square
    map units, and each belongs to a precinct whose other records carry its
    shape.
  - Joining pieces whose shared edges do not meet exactly leaves slivers: 120
    holes and 106 detached parts under 100 m2. They are removed, never a
    precinct's largest part. No real hole or part in the county packages is
    between 100 and 1,000 m2, and the join leaves none between them either,
    which is where the line is drawn.

TWO PRECINCTS CAN CLAIM ONE PLACE. Where two counties or cities meet, each
draws its own side of the line, and the two drawings disagree: measured
2026-10-30, 685 pairs of precincts in different counties overlap by a square
metre or more, 13.68 km2 in all (the largest, between Spotsylvania's
Massaponax High and Caroline's Port Royal, about 1 km2), and 102 pairs within
one county overlap by 62,081 m2 in all (the largest 10,171 m2, in Orange
County). resolve() gives every overlap to one precinct before the file is
drawn, so a click is answered by one precinct and the precinct, the county
and the local district cards cannot disagree about which county a point is
in: across a county line, each part of the overlap goes to the precinct whose
county the Census Bureau's county file (the one the County card draws) puts
it in; within a county, the overlap goes to the precinct whose key comes
first, since nothing in the layer says which of the two the county meant.
Both counts are held to what was measured, and the build fails if two
precincts still overlap by a square metre afterwards.

THE COUNTY FILE CARRIES WATER THE PRECINCTS DO NOT. Nine counties and cities
on the Chesapeake Bay and Hampton Roads keep their own floor for the share of
points inside the county that land in one of its precincts, each five points
below what the build measured, because the Census Bureau's county includes
open water the precincts leave undrawn (SPEC below gives each county's share
and the water share the Census Bureau records).

mapshaper's own dissolve was measured first and is not used: it gave two
precincts no shape at all (Prince William 405 and Henrico 509), left 271 of
the joined shapes invalid, and, with snapping, still left 66.

A PRECINCT'S NAME. `PrcnctName` as the Department writes it, in capitals in
29 of the 133 counties and cities. Grayson County's Fries precinct is two
records named "Fries Part 1" and "Fries Part 2"; the part number is removed
so the two read as one precinct.

THE LOCAL DISTRICT ON EACH PRECINCT. `d` and `dn` carry the layer's
`DistNumber` and `DistName` as published. Every precinct has exactly one of
each (measured 2026-10-30), so a precinct lies wholly inside one local
election district. In some counties one of the two is wrong (Carroll names
two districts Fancy Gap, Isle of Wight's names are precinct names, and
Southampton's numbers are stale), which build_va_local_districts.py reads
and corrects; this file ships them as published.

HOW CLOSELY THE LINES ARE DRAWN. The fleet's rule (scripts/statewide_precincts.py,
step 5) takes the smallest of 4, 8 and 12 metres that brings the gzipped file to
2.5 MB or under. Virginia's precincts follow creeks, ridges and roads, as
Kentucky's do: measured 2026-10-30 on the joined and resolved precincts, the
file is 14.6 MB raw and 3.74 MB gzipped at 4 m, 10.5 MB and 2.66 MB at 8 m, and
8.7 MB and 2.17 MB at 12 m, so it is drawn at 12 m.

PACING. The layer's host publishes no robots.txt that binds this client
(measured 2026-10-30), and the builder waits a second between requests.
"""

import collections
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import statewide_precincts as sp  # noqa: E402

LAYER = ("https://services5.arcgis.com/M3dium4ePYpmdT4B/arcgis/rest/services/"
         "Districts_Union_Simplified/FeatureServer/0")

# What the joined layer holds, measured 2026-10-30. A change to any of these
# is a changed layer: read it, then change the number deliberately.
PIECES = 7271            # records that name a county, 9 of them with no shape
NULL_GEOMETRY = 9        # of those, records with no shape
SLIVER_M2 = 100.0        # a hole or part this small, left by the join, is removed
SLIVER_HOLES = 120
SLIVER_PARTS = 106
CROSS_OVERLAPS = 685     # pairs of precincts in two counties overlapping by 1 m2 or more
SAME_OVERLAPS = 102      # pairs in one county

# Properties that belong to the precinct, so every piece must agree on them.
PRECINCT_FIELDS = ("CountyFIPS", "CountyName", "PrcnctFIPS", "PrcnctNum", "DistNumber", "DistName")
PART_SUFFIX = re.compile(r"\s+Part\s+\d+$", re.I)


def precinct_name(props):
    return re.sub(r"\s+", " ", PART_SUFFIX.sub("", (props.get("PrcnctName") or "").strip()))


def read(props):
    county = (props.get("CountyFIPS") or "").strip()
    code = (props.get("PrcnctFIPS") or "").strip()
    if not re.fullmatch(r"\d{3}", county) or not re.fullmatch(r"\d{6}", code):
        sp.fail(SPEC, "county %r or precinct %r is not a Virginia code: %r" % (county, code, props))
    num = (props.get("PrcnctNum") or "").strip()
    return {
        "key": "51%s-%s" % (county, code),
        "name": precinct_name(props),
        "num": num,
        "countyFips": "51" + county,
        "d": (props.get("DistNumber") or "").strip(),
        "dn": re.sub(r"\s+", " ", (props.get("DistName") or "").strip()),
    }


def _ring_m2(ring, lat):
    from shapely.geometry import Polygon  # noqa: PLC0415
    return Polygon(ring).area * 111320.0 ** 2 * math.cos(math.radians(lat))


def join_pieces(records, geometry=True):
    """One record per precinct: the pieces' shapes joined, their areas summed,
    and the precinct's own fields held equal across them."""
    from shapely.geometry import MultiPolygon, Polygon, mapping, shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    groups = collections.OrderedDict()
    for rec in records:
        p = rec.get("properties") or {}
        k = ((p.get("CountyFIPS") or "").strip(), (p.get("PrcnctFIPS") or "").strip())
        groups.setdefault(k, []).append(rec)
    if sum(len(v) for v in groups.values()) != PIECES:
        sp.fail(SPEC, "%d records name a county, expected %d. Read the layer before changing "
                "PIECES" % (sum(len(v) for v in groups.values()), PIECES))
    out, nulls, holes, parts = [], 0, 0, 0
    for k, recs in groups.items():
        first = recs[0]["properties"]
        want = {f: first.get(f) for f in PRECINCT_FIELDS}
        want["name"] = precinct_name(first)
        for r in recs[1:]:
            got = {f: r["properties"].get(f) for f in PRECINCT_FIELDS}
            got["name"] = precinct_name(r["properties"])
            if got != want:
                sp.fail(SPEC, "two pieces of precinct %s/%s differ in what they say: %r and %r"
                        % (k[0], k[1], want, got))
        props = dict(first)
        props["Shape__Area"] = sum(float(r["properties"].get("Shape__Area") or 0) for r in recs)
        if not geometry:
            out.append({"properties": props, "geometry": None})
            continue
        shapes = [shape(r["geometry"]) for r in recs if r.get("geometry")]
        nulls += len(recs) - len(shapes)
        if not shapes:
            sp.fail(SPEC, "precinct %s/%s has no piece with a shape" % k)
        joined = unary_union(shapes)
        polys = [g for g in getattr(joined, "geoms", [joined]) if g.geom_type == "Polygon"]
        if not polys:
            sp.fail(SPEC, "joining precinct %s/%s gave no polygon" % k)
        largest = max(polys, key=lambda g: g.area)
        kept = []
        for g in polys:
            lat = g.representative_point().y
            if g is not largest and _ring_m2(g.exterior, lat) < SLIVER_M2:
                parts += 1
                continue
            inner = []
            for ring in g.interiors:
                if _ring_m2(ring, lat) < SLIVER_M2:
                    holes += 1
                else:
                    inner.append(ring)
            kept.append(Polygon(g.exterior, inner))
        geom = kept[0] if len(kept) == 1 else MultiPolygon(kept)
        if not geom.is_valid:
            geom = geom.buffer(0)
        out.append({"properties": props, "geometry": mapping(geom)})
    if geometry:
        found = {"records with no shape": (nulls, NULL_GEOMETRY),
                 "sliver holes removed": (holes, SLIVER_HOLES),
                 "sliver parts removed": (parts, SLIVER_PARTS)}
        for what, (n, expected) in found.items():
            if n != expected:
                sp.fail(SPEC, "%d %s, expected %d. Read the layer before changing the number"
                        % (n, what, expected))
        print("joined %d records into %d precincts: %d with no shape, %d sliver holes and %d "
              "sliver parts under %.0f m2 removed" % (PIECES, len(out), nulls, holes, parts,
                                                       SLIVER_M2), file=sys.stderr)
    return out


def _m2(g):
    if g.is_empty:
        return 0.0
    return g.area * 111320.0 ** 2 * math.cos(math.radians(g.representative_point().y))


def _polygonal(g):
    """The polygons in a shapely result, however deeply a collection holds
    them; the lines and points an overlay leaves along shared edges are
    dropped."""
    from shapely.geometry import MultiPolygon, Polygon  # noqa: PLC0415
    polys, stack = [], [g]
    while stack:
        x = stack.pop()
        if x.is_empty:
            continue
        if x.geom_type == "Polygon":
            polys.append(x)
        elif hasattr(x, "geoms"):
            stack.extend(x.geoms)
    if not polys:
        return Polygon()
    if len(polys) == 1:
        return polys[0]
    # an overlay's parts can share an edge, which a MultiPolygon may not, so
    # they are unioned rather than collected
    from shapely.ops import unary_union  # noqa: PLC0415
    return _polygonal(unary_union(polys)) if not MultiPolygon(polys).is_valid else MultiPolygon(polys)


def resolve(feats, counties):
    """Give every overlap between two precincts to one of them: across a
    county line to the precinct whose county the Census draws there, within
    a county to the precinct whose key comes first."""
    from shapely.geometry import mapping, shape  # noqa: PLC0415
    from shapely.strtree import STRtree  # noqa: PLC0415

    feats = sorted(feats, key=lambda f: f["properties"]["key"])
    county = {g: shape(c["geometry"]) for g, c in counties.items()}
    original = [shape(f["geometry"]) for f in feats]
    geoms = list(original)
    tree = STRtree(original)
    cross = same = 0
    cross_m2 = same_m2 = 0.0
    for i, g in enumerate(original):
        for j in sorted(int(x) for x in tree.query(g)):
            if j <= i or not g.intersects(original[j]):
                continue
            first = _m2(_polygonal(g.intersection(original[j])))
            ca = feats[i]["properties"]["countyFips"]
            cb = feats[j]["properties"]["countyFips"]
            if first >= 1.0:
                if ca == cb:
                    same, same_m2 = same + 1, same_m2 + first
                else:
                    cross, cross_m2 = cross + 1, cross_m2 + first
            inter = _polygonal(geoms[i].intersection(geoms[j]))
            if inter.is_empty or inter.area == 0:
                continue
            if ca == cb:
                geoms[j] = _polygonal(geoms[j].difference(inter))
                continue
            # each half is cut from the overlap by the county polygon itself:
            # cut by the other half, GEOS loses slivers along the county line
            geoms[i] = _polygonal(geoms[i].difference(_polygonal(inter.intersection(county[cb]))))
            geoms[j] = _polygonal(geoms[j].difference(_polygonal(inter.difference(county[cb]))))
    found = {"overlaps across a county line": (cross, CROSS_OVERLAPS),
             "overlaps within a county": (same, SAME_OVERLAPS)}
    for what, (n, expected) in found.items():
        if n != expected:
            sp.fail(SPEC, "%d %s of 1 m2 or more, expected %d. Read the layer before "
                    "changing the number" % (n, what, expected))
    out, left = [], 0.0
    for f, g in zip(feats, geoms):
        if not g.is_valid:
            g = _polygonal(g.buffer(0))
        if g.is_empty:
            sp.fail(SPEC, "precinct %s lost all its ground to its neighbours" % f["properties"]["key"])
        out.append({"properties": f["properties"], "geometry": mapping(g)})
    # what is left is the overlay's rounding along edges: never as much as
    # 1 m2 between two precincts (2026-10-30: at most 0.13 m2, 1.1 m2 in all)
    after, worst = STRtree(geoms), 0.0
    for i, g in enumerate(geoms):
        for j in after.query(g):
            j = int(j)
            if j > i:
                m2 = _m2(_polygonal(g.intersection(geoms[j])))
                left, worst = left + m2, max(worst, m2)
    if worst >= 1.0:
        sp.fail(SPEC, "two precincts still overlap by %.2f m2 after resolving it" % worst)
    print("resolved %d overlaps across a county line (%.2f km2) and %d within a county "
          "(%.0f m2); %.2f m2 of overlap left, at most %.3f m2 between two precincts"
          % (cross, cross_m2 / 1e6, same, same_m2, left, worst),
          file=sys.stderr)
    return out


def fetcher(spec, geometry=True):
    records, meta = sp.fetch_layer(spec, geometry)
    return join_pieces(records, geometry), meta


SPEC = sp.Spec(
    tag="va",
    label="build_va_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/va/)",
    out_fields="CountyFIPS,CountyName,PrcnctFIPS,PrcnctNum,PrcnctName,DistNumber,DistName",
    where="CountyFIPS <> ''",
    expect=2531,
    expect_counties=133,
    state_bbox={"minLng": -83.68, "minLat": 36.54, "maxLng": -75.24, "maxLat": 39.47},
    read=read,
    out_file="va-precincts.json",
    pace=1.0,
    page=2000,
    measure_field="Shape__Area",
    # 4 m: 3.74 MB gzipped; 8 m: 2.66 MB; 12 m: 2.17 MB (2026-10-30)
    interval="12",
    required=("key", "name", "num", "countyFips"),
    fetcher=fetcher,
    resolve=resolve,
    # The county file carries each county's water, which the precincts mostly
    # leave undrawn. Each floor is five points below the share of that
    # county's sample the build measured on 2026-10-30 (in brackets), beside
    # the share of the county the Census Bureau counts as water.
    tiling_floor_by_county={
        "51095": 0.79,  # James City County (0.840): water 20.5%
        "51103": 0.75,  # Lancaster County (0.800): 42.4%
        "51119": 0.57,  # Middlesex County (0.625): 38.2%
        "51650": 0.42,  # Hampton (0.470): 62.2%
        "51700": 0.53,  # Newport News (0.580): 42.3%
        "51710": 0.57,  # Norfolk (0.625): 44.7%
        "51735": 0.21,  # Poquoson (0.260): 80.4%
        "51740": 0.57,  # Portsmouth (0.620): 28.7%
        "51810": 0.54,  # Virginia Beach (0.590): 50.8%
    },
)

if __name__ == "__main__":
    sp.main(SPEC, __doc__)
