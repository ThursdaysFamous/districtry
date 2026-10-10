#!/usr/bin/env python3
"""Read the Census's tribal areas, and decide which parts of one belong to a state.

This is the shared reader for districtry's tribal-government layer. It fetches no
app file and writes none: it is the module every per-state builder calls, so that
seven instances cannot come to disagree about which service was read, which
vintage, or how small a cross-border sliver is too small to answer for.

WHY A LAYER ID IS NEVER HARDCODED HERE
--------------------------------------
TIGERweb publishes tribal areas twice over. `TIGERweb/tigerWMS_Current/MapServer` carries
them beside every other geography (federal reservations at 36, off-reservation
trust lands at 38, tribal subdivisions at 34, states at 80, counties at 82), and
`TIGERweb/AIANNHA/MapServer` carries the same classes FOUR TIMES, once per
vintage, at four different sets of ids. Measured 2026-09-30 on AIANNHA: federal
reservations are layer 2 (current), 14 (BAS 2026), 26 (ACS 2025) and 38 (Census
2020) -- and layer 36, which would be the reservations layer if the ids ran in
one sequence, is Alaska Native Regional Corporations. So a note reading "layer 36
has the reservations" is right in one service and names something else entirely
in the other, and a builder that hardcoded 38 would silently read Census 2020
trust lands (167 features) where it meant current ones (177).

Every id this module uses is therefore RESOLVED from the service's own layer
list, by vintage and class name, and the resolved id is reported so a build log
records what was actually read.

WHY THE VINTAGE IS RESOLVED BY ORDER AND NOT BY THE SERVICE'S OWN GROUPING
-------------------------------------------------------------------------
AIANNHA declares three Group Layers -- "BAS 2026" (11), "ACS 2025" (23),
"Census 2020" (35) -- and `parentLayerId` is **None on every one of its 48
layers**, group children included (measured 2026-09-30 against
`/layers?f=json`). The service knows the groups exist and does not say what is in
them. What it does publish is ORDER: a group header precedes its own members, and
the layers before the first header are the current vintage. That inference is
used, and then checked rather than trusted -- a segment must carry every class
name this module knows, and the class counts must be the ones measured
(reservations 312 / trust lands 177 / state reservations 10 on the current
vintage, the trust-land count being what separates the vintages: 177 current,
176 in ACS 2025, 167 in Census 2020).

WHY A NON-EMPTY INTERSECTION IS NOT AN OVERLAP
----------------------------------------------
Two polygons that share a boundary and enclose no ground between them intersect
in a MultiLineString, which has zero area and which `is_empty` reports as False.
The Lake Traverse Reservation's eastern edge IS the Minnesota state line, so a
reader of `is_empty` counts it as Minnesota ground and a reader of AREA does not.
This module measures the area. `clip_to_state` returns zero for that case and
`--selftest` asserts it, because the mistake has been made twice in this project
already, once in a planning thread's 0.139 km2 figure and once in this thread's
own first reading of Minnesota's subdivision count.

RING HANDLING FOLLOWS THE APP'S OWN RULE
----------------------------------------
The app decides what is inside a feature by counting ring crossings (even-odd),
not by winding direction, so a ring nested inside another is a hole whichever way
it is wound. `even_odd` builds the same region with a symmetric difference over a
feature's rings, so an area measured here is the area the app would answer for.

Usage:
    python3 scripts/tribal_areas.py --selftest         # offline, no network
    python3 scripts/tribal_areas.py --report <state>   # live, e.g. --report Minnesota
"""

import argparse
import json
import subprocess
import sys
import urllib.parse

TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services"
AIANNHA = TIGERWEB + "/TIGERweb/AIANNHA/MapServer"
CURRENT_GEOG = TIGERWEB + "/TIGERweb/tigerWMS_Current/MapServer"

# The class names AIANNHA uses, keyed by the short name this project uses.
# These are the service's own layer names, matched exactly.
CLASS_NAMES = {
    "reservation": "Federal American Indian Reservations",
    "trust-land": "Off-Reservation Trust Lands",
    "state-reservation": "State American Indian Reservations",
    "subdivision": "Tribal Subdivisions",
    "otsa": "Oklahoma Tribal Statistical Areas",
    "sdtsa": "State Designated Tribal Statistical Areas",
    "tdsa": "Tribal Designated Statistical Areas",
    "joint-use": "American Indian Joint-Use Areas",
}

# The three land classes a nation actually governs. The statistical areas above
# (OTSA, SDTSA, TDSA) are shapes the Census draws so it has something to count
# people inside; ruled 2026-09-30 to be READ, for working out which nation to
# name, and never DRAWN.
GOVERNED_CLASSES = ("reservation", "trust-land", "state-reservation")
STATISTICAL_CLASSES = ("otsa", "sdtsa", "tdsa")

# THE ONE EXCEPTION TO THAT RULING, and it is Adam's, for one state (2026-10-10,
# "Make an exception for OK"). In Oklahoma the Census draws only one federal
# reservation (Osage) and one trust land; every other nation's ground is an
# Oklahoma Tribal Statistical Area, or a joint-use area two of them share. Left
# undrawn, a reader almost anywhere in the state would be told no tribal
# government answers there. So in Oklahoma those two statistical classes ARE
# drawn, and the card says plainly that the Census draws them for counting
# people and that they are not a legal boundary. Keyed by state, so no other
# state can draw a statistical area by accident.
DRAWN_STATISTICAL = {"Oklahoma": ("otsa", "joint-use")}


def drawn_classes(state_name):
    """The land classes a builder draws in one state: the governed three, plus
    a statistical class only where DRAWN_STATISTICAL names that state."""
    return GOVERNED_CLASSES + DRAWN_STATISTICAL.get(state_name, ())

# Measured 2026-09-30 on the current vintage. These are a control on the
# order-based vintage resolution above, not a limit on what may ship: a count
# that has MOVED is reported, and only a count that moved in a way that swaps two
# classes (trust lands reading as a different vintage's) fails.
CURRENT_COUNTS = {"reservation": 312, "trust-land": 177, "state-reservation": 10}

# The vintage every builder reads unless it says otherwise. "current" is the
# segment before AIANNHA's first group header.
DEFAULT_VINTAGE = "current"

# --- the cross-state floor (ruled by Adam, 2026-09-30) -----------------------
# A piece of a tribal area that falls inside a state counts if it is either 1% of
# that area's whole extent OR a quarter of a square kilometre, whichever it
# reaches first -- and never when the overlap comes out as zero. Neither test
# works alone: the share alone drops a real neighbourhood belonging to a very
# large nation, and the absolute area alone keeps a digitisation sliver of a
# small one. Measured consequence: this keeps every piece anyone lives on and
# leaves out exactly two in the states measured, a 4,200 m2 corner of Ponca land
# in Iowa and the shared-boundary strip of Lake Traverse in Minnesota.
KEEP_SHARE = 0.01
KEEP_AREA_KM2 = 0.25

_STATE_LAYER_NAME = "States"

# The fields every builder reads off a tribal-area layer. AIANNH is the Census's
# own code for the area and is the key a join table hangs on; there is no field
# named AIANNHCE on these layers, which is what a first pass asked for and got a
# 400 back for. POP100 is the 2020 population the layer carries.
AREA_FIELDS = "NAME,BASENAME,GEOID,AIANNH,POP100,AREALAND,INTPTLAT,INTPTLON"


def _get(url, timeout=120):
    """Fetch JSON with curl, which goes through an HTTPS proxy where requests may not.

    An ArcGIS service answers a bad query with HTTP 200 carrying an error
    envelope, so every caller here checks for an "error" key rather than trusting
    the status code."""
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", str(timeout), url],
        check=True, capture_output=True,
    ).stdout
    return json.loads(out)


def _require_no_error(payload, what):
    """Raise on an ArcGIS error envelope.

    This exists because `payload.get("features", [])` turns an error object into
    an empty list, which reads downstream as a confident, uniform and completely
    wrong answer -- "this state has no tribal land" assembled out of a failure.
    """
    if isinstance(payload, dict) and "error" in payload:
        raise RuntimeError("%s: service returned an error envelope: %r" % (what, payload["error"]))
    return payload


def resolve_layers(service=AIANNHA):
    """Return {vintage: {short class name: layer id}} for a tribal-areas service.

    Walks the service's own layer list in order. A Group Layer starts a new
    vintage named after it; the layers before the first group are "current".
    See the module docstring for why order is the only available signal.
    """
    meta = _require_no_error(_get(service + "/layers?f=json"), "layer list")
    layers = meta.get("layers")
    if not layers:
        raise RuntimeError("layer list for %s carried no layers" % service)

    by_name = {v: k for k, v in CLASS_NAMES.items()}
    vintages = {}
    vintage = DEFAULT_VINTAGE
    for layer in layers:
        if layer.get("type") == "Group Layer":
            vintage = layer["name"]
            continue
        short = by_name.get(layer["name"])
        if short is None:
            continue
        # First occurrence within a vintage wins; a repeat would mean the order
        # inference has run past a group boundary.
        vintages.setdefault(vintage, {}).setdefault(short, layer["id"])

    for name, found in vintages.items():
        missing = [c for c in GOVERNED_CLASSES if c not in found]
        if missing:
            raise RuntimeError(
                "vintage %r resolved without %s — the order-based vintage split is wrong"
                % (name, ", ".join(missing))
            )
    if DEFAULT_VINTAGE not in vintages:
        raise RuntimeError("no current-vintage layers found in %s" % service)
    return vintages


def count_features(service, layer):
    """How many features a layer holds, from the service's own count."""
    url = "%s/%d/query?where=1%%3D1&returnCountOnly=true&f=json" % (service, layer)
    got = _require_no_error(_get(url), "count for layer %d" % layer)
    if "count" not in got:
        raise RuntimeError("count for layer %d carried no count: %r" % (layer, got))
    return got["count"]


def check_vintage_counts(resolved, service=AIANNHA, vintage=DEFAULT_VINTAGE):
    """Confirm the resolved vintage is the one whose counts were measured.

    Returns a list of human-readable notes about counts that have MOVED, which is
    ordinary (the Census refiles) and is reported rather than failed. It RAISES
    only when a count matches a DIFFERENT vintage's measured value, because that
    is the signature of the order inference having slipped a group -- the one
    failure this control exists to catch.
    """
    other_trust = {176: "ACS 2025", 167: "Census 2020"}
    notes = []
    ids = resolved[vintage]
    for cls, expected in CURRENT_COUNTS.items():
        if cls not in ids:
            continue
        got = count_features(service, ids[cls])
        if got == expected:
            continue
        if cls == "trust-land" and got in other_trust:
            raise RuntimeError(
                "layer %d resolved as the %s trust lands holds %d features, which is "
                "%s's measured count — the vintage resolution has slipped a group"
                % (ids[cls], vintage, got, other_trust[got])
            )
        notes.append(
            "%s: layer %d holds %d features, measured %d on 2026-09-30"
            % (cls, ids[cls], got, expected)
        )
    return notes


def fetch_layer(service, layer, where="1=1", fields="*", page=800):
    """Every feature of a layer as GeoJSON features, paging past the transfer cap.

    A service that caps a response sets `exceededTransferLimit`; reading a capped
    response as the whole layer is how a builder comes to ship a subset of a
    nation's land without anything looking wrong.
    """
    feats = []
    offset = 0
    while True:
        url = (
            "%s/%d/query?where=%s&outFields=%s&outSR=4326&geometryPrecision=6"
            "&returnGeometry=true&resultOffset=%d&resultRecordCount=%d&f=geojson"
            % (service, layer, urllib.parse.quote(where), urllib.parse.quote(fields), offset, page)
        )
        got = _require_no_error(_get(url), "layer %d at offset %d" % (layer, offset))
        batch = got.get("features")
        if batch is None:
            raise RuntimeError("layer %d at offset %d carried no features key" % (layer, offset))
        feats.extend(batch)
        if not got.get("exceededTransferLimit") and len(batch) < page:
            break
        if not batch:
            break
        offset += len(batch)
    return feats


def state_polygon(name):
    """The Census's own polygon for one state, with a control on the way in.

    The control is the point of this function: the layer must answer with a
    two-digit state code and no error envelope. Clipping a nation's land to a
    state read out of a failure is the measurement this project has already got
    wrong once by reading `.get("features", [])` on an error.
    """
    where = "NAME='%s'" % name.replace("'", "''")
    layers = _require_no_error(_get(CURRENT_GEOG + "/layers?f=json"), "geography layer list")
    ids = [l["id"] for l in layers.get("layers", []) if l.get("name") == _STATE_LAYER_NAME]
    if len(ids) != 1:
        raise RuntimeError(
            "expected exactly one %r layer in tigerWMS_Current, found %d"
            % (_STATE_LAYER_NAME, len(ids))
        )
    feats = fetch_layer(CURRENT_GEOG, ids[0], where=where, fields="NAME,GEOID,STATE")
    if len(feats) != 1:
        raise RuntimeError("state %r matched %d features, expected 1" % (name, len(feats)))
    props = feats[0].get("properties") or {}
    geoid = props.get("GEOID") or props.get("STATE")
    if not geoid or len(str(geoid)) != 2 or not str(geoid).isdigit():
        raise RuntimeError(
            "control failed: state %r came back without a two-digit code (%r)" % (name, geoid)
        )
    return feats[0], str(geoid)


# --- geometry -----------------------------------------------------------------

def _shapely():
    try:
        from shapely.geometry import Polygon  # noqa: F401
    except ImportError:  # pragma: no cover - reported, never guessed around
        raise RuntimeError(
            "shapely is needed for the area measurements (scripts/requirements.txt pins it)"
        )
    import shapely.geometry as sg
    return sg


def _rings(geometry):
    """Every linear ring of a GeoJSON Polygon or MultiPolygon, flat."""
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return [r for r in coords if len(r) >= 4]
    if kind == "MultiPolygon":
        out = []
        for part in coords:
            out.extend(r for r in part if len(r) >= 4)
        return out
    raise RuntimeError("not a polygon geometry: %r" % kind)


def even_odd(geometry):
    """A shapely geometry for the region the app would call inside this feature.

    Even-odd over every ring, so a ring nested inside another is a hole whichever
    way it is wound -- which is the app's own rule and is not shapely's default
    reading of a MultiPolygon.
    """
    sg = _shapely()
    out = None
    for ring in _rings(geometry):
        piece = sg.Polygon(ring).buffer(0)
        out = piece if out is None else out.symmetric_difference(piece)
    if out is None:
        raise RuntimeError("geometry carried no usable ring")
    return out


def area_km2(geom):
    """Area on the WGS84 ellipsoid, in square kilometres.

    pyproj rather than a planar area in degrees: across a state two degrees of
    latitude tall a degree of longitude is not a constant width, and a planar
    reference is what put a floor under an earlier comparison's error.
    """
    from pyproj import Geod
    area, _ = Geod(ellps="WGS84").geometry_area_perimeter(geom)
    return abs(area) / 1e6


def clip_to_state(area_geometry, state_geometry):
    """What part of one tribal area lies inside one state, and whether it counts.

    Returns a dict with the area's whole extent in km2, the part inside the state
    in km2, that part as a share of the whole, and `keep` -- the ruled floor
    applied. AREA decides, never `is_empty`: two shapes sharing a boundary
    intersect in a zero-area line.
    """
    whole = even_odd(area_geometry)
    state = even_odd(state_geometry)
    inter = whole.intersection(state)
    whole_km2 = area_km2(whole)
    inside_km2 = 0.0 if inter.is_empty else area_km2(inter)
    # A zero-area intersection is a shared boundary, not a sliver. Rounding to
    # micro-km2 (a square metre) before the test keeps a floating-point crumb
    # from reading as ground.
    inside_km2 = 0.0 if round(inside_km2, 6) <= 0 else inside_km2
    share = (inside_km2 / whole_km2) if whole_km2 > 0 else 0.0
    keep = inside_km2 > 0 and (share >= KEEP_SHARE or inside_km2 >= KEEP_AREA_KM2)
    return {
        "whole_km2": whole_km2,
        "inside_km2": inside_km2,
        "share": share,
        "keep": keep,
        "intersection_type": None if inter.is_empty else inter.geom_type,
    }


# --- selftest -----------------------------------------------------------------

def _square(x0, y0, x1, y1):
    return {"type": "Polygon", "coordinates": [[
        [x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0],
    ]]}


def selftest():
    """Offline assertions on the two readings this project has already got wrong."""
    checks = 0

    # 1. A shared boundary is not an overlap. Two squares meeting along x=0.
    west = _square(-1.0, 45.0, 0.0, 46.0)
    east = _square(0.0, 45.0, 1.0, 46.0)
    got = clip_to_state(east, west)
    assert got["intersection_type"] is not None, "a shared edge does intersect"
    assert "Line" in got["intersection_type"], got["intersection_type"]
    assert got["inside_km2"] == 0.0, got
    assert got["keep"] is False, got
    checks += 3

    # 2. A real overlap is kept on the absolute test even when its share is tiny.
    #    A 0.5-degree-wide area overlapping a state by 0.02 degrees of longitude
    #    is well under 1% of nothing -- it is about 4%, so widen the area until
    #    the share test cannot be what keeps it.
    big = _square(-1.0, 45.0, 4.0, 46.0)
    state = _square(-1.0, 45.0, -0.98, 46.0)
    got = clip_to_state(big, state)
    assert got["inside_km2"] >= KEEP_AREA_KM2, got
    assert got["share"] < KEEP_SHARE, got
    assert got["keep"] is True, "the absolute test must keep this on its own"
    checks += 3

    # 3. A real overlap is kept on the share test even when its area is small.
    small = _square(0.0, 45.0, 0.002, 45.002)
    half = _square(0.0, 45.0, 0.001, 45.002)
    got = clip_to_state(small, half)
    assert got["inside_km2"] < KEEP_AREA_KM2, got
    assert got["share"] >= KEEP_SHARE, got
    assert got["keep"] is True, "the share test must keep this on its own"
    checks += 3

    # 4. Even-odd: a ring inside another is a hole, wound the same way as its
    #    parent. Shapely's own MultiPolygon reading would count it as land.
    donut = {"type": "Polygon", "coordinates": [
        [[0.0, 45.0], [0.0, 46.0], [1.0, 46.0], [1.0, 45.0], [0.0, 45.0]],
        [[0.4, 45.4], [0.4, 45.6], [0.6, 45.6], [0.6, 45.4], [0.4, 45.4]],
    ]}
    solid = {"type": "Polygon", "coordinates": [donut["coordinates"][0]]}
    assert area_km2(even_odd(donut)) < area_km2(even_odd(solid)), "the hole must be a hole"
    checks += 1

    # 5. An error envelope raises rather than reading as an empty answer.
    try:
        _require_no_error({"error": {"code": 400}}, "control")
    except RuntimeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("an error envelope must raise, not read as no features")
    checks += 1

    # 6. The statistical classes are not in the governed set. Ruled 2026-09-30:
    #    read them to name a nation, never draw them.
    for cls in STATISTICAL_CLASSES:
        assert cls not in GOVERNED_CLASSES, cls
    checks += 1

    # 7. The Oklahoma exception reaches Oklahoma alone, and draws only the two
    #    classes Adam allowed there.
    assert list(DRAWN_STATISTICAL) == ["Oklahoma"], DRAWN_STATISTICAL
    assert drawn_classes("Oklahoma") == GOVERNED_CLASSES + ("otsa", "joint-use")
    assert drawn_classes("Minnesota") == GOVERNED_CLASSES
    for cls in DRAWN_STATISTICAL["Oklahoma"]:
        assert cls in CLASS_NAMES and cls not in GOVERNED_CLASSES, cls
    checks += 1

    print("OK tribal_areas selftest: %d assertions" % checks)
    return 0


def report(state_name):
    """Live: what the Census publishes for one state, class by class."""
    resolved = resolve_layers()
    print("AIANNHA vintages resolved: %s" % ", ".join(sorted(resolved)))
    ids = resolved[DEFAULT_VINTAGE]
    for cls in sorted(ids):
        print("  %-18s layer %d" % (cls, ids[cls]))
    for note in check_vintage_counts(resolved):
        print("NOTE %s" % note)

    state, geoid = state_polygon(state_name)
    print("control OK: %s is state code %s" % (state_name, geoid))

    for cls in drawn_classes(state_name):
        if cls not in ids:
            print("%s: not published in this vintage" % cls)
            continue
        feats = fetch_layer(AIANNHA, ids[cls], fields=AREA_FIELDS)
        kept, dropped = [], []
        for feat in feats:
            geom = feat.get("geometry")
            if not geom:
                continue
            got = clip_to_state(geom, state["geometry"])
            if got["inside_km2"] <= 0:
                continue
            name = (feat.get("properties") or {}).get("NAME") or "?"
            row = (name, got)
            (kept if got["keep"] else dropped).append(row)
        print("\n%s in %s: %d kept, %d under the floor" % (cls, state_name, len(kept), len(dropped)))
        for name, got in sorted(kept, key=lambda r: -r[1]["inside_km2"]):
            print("  keep %8.3f km2  %5.1f%% of the area  %s"
                  % (got["inside_km2"], 100 * got["share"], name))
        for name, got in sorted(dropped, key=lambda r: -r[1]["inside_km2"]):
            print("  drop %8.6f km2  %5.2f%% of the area  %s"
                  % (got["inside_km2"], 100 * got["share"], name))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="offline assertions, no network")
    ap.add_argument("--report", metavar="STATE", help="live report for one state, e.g. Minnesota")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.report:
        return report(args.report)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
