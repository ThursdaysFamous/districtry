#!/usr/bin/env python3
"""
Build the pre-simplified New Hampshire congressional, State Senate and State
House boundary files in data/app/, so the app fetches them same-origin
(cache-first) instead of downloading full statewide geometry live on every
first toggle.

Statewide, like the Illinois reference and every newer state: the instance
answers anywhere in New Hampshire, so each map ships whole — fetch ->
simplify -> validate -> write data/app/<file>. No clip step: the served area
IS the state.

Like build_state_counties.py this is an occasional OPERATOR step, not weekly
CI — re-run it on redistricting. The officeholder ROSTERS (congress-roster,
nh-senate-members, nh-house-members) are separate; only the geometry is here.

THE CONGRESSIONAL MAP IS THE 2022 MAP, DRAWN FROM TIGERweb LAYER 0 (THE 120TH
CONGRESS), AND THAT IS A MEASUREMENT RATHER THAN A DEFAULT. New Hampshire's
two districts were drawn by the New Hampshire Supreme Court in 2022, when the
Legislature and the Governor did not agree on a plan, and have not been drawn
again. check_same_map measures layer 0 ("120th Congressional Districts")
against layer 4 ("119th Congressional Districts") on every build and refuses
to draw layer 0 before 3 January 2027 if any district's
intersection-over-union falls below 0.9999, because until then the sitting
members were elected from layer 4's map. check_serving_map also refuses on or
after 3 January 2029, so a person reads which map the 2028 election used
before anything is drawn.

THE HOUSE HAS 400 SEATS IN 203 DISTRICTS, AND 39 OF THEM OVERLAP THE OTHER
164. New Hampshire's 2022 House plan draws 164 "base" districts, which tile
the state, and 39 "floterial" districts, each the union of two to six whole
base districts, which elect members on top of the base districts' own. A
reader in a base district that belongs to a floterial is represented by the
members of both. TIGERweb's lower-house layer (layer 2) carries the 164 base
districts and no floterial, because Census geography cannot overlap, so the
floterials come from the state's GIS clearinghouse, NH GRANIT (University of
New Hampshire), whose 2022 House layers carry both: NHHouseDists2022_base and
NHHouseDists2022_float, derived from the Secretary of State's district codes
applied to GRANIT's town boundaries. floterial_membership() measures, with
shapely on GRANIT's own geometry, which base districts each floterial is made
of, and refuses unless every floterial is EXACTLY a union of whole base
districts (symmetric difference under one part in a million of its area), no
base district sits in two floterials, and GRANIT's 164 base codes are TIGER's
164. Measured 2026-11-11: all 39 floterials are exact unions, 108 of the 164
base districts belong to one, and none belongs to two. So the House ships as
ONE file of the 164 base districts drawn from TIGER, each carrying its own
`district` name ("Belknap 3") and, where it has one, its `floterial`
("Belknap 8") — and the card names the members of both. A floterial is never
drawn as an outline of its own, which keeps the file a partition (one House
base district at every point, which the population check and the 2,000-point
gate both require); the card says which base districts make it.

GRANIT'S CERTIFICATE CHAIN ENDS AT A ROOT THIS SANDBOX'S PROXY BUNDLE LACKS
(nhgeodata.unh.edu presents InCommon's intermediate, cross-signed by emSign
Root CA - G1, which is in Mozilla's store, measured 2026-11-11), so its
fetches verify against certifi's copy of Mozilla's store rather than the
environment's bundle. Verification is never switched off.

THE THREE MAPS ARE SIMPLIFIED IN ONE SHARED TOPOLOGY. New Hampshire draws its
Senate and House districts from whole towns and city wards, and its two
congressional districts from whole towns too, so the three share their
lines. mapshaper's combine-files puts them in one dataset, which makes a
shared edge one arc simplified once, so a Senate line and the House line it
runs along can never part (the Illinois builder's lesson,
scripts/build_legislative_boundaries.py).

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
Adam chose for Mississippi's maps before that instance opened ("Finer first",
2026-10-16) and the newer states' builders carry. Douglas-Peucker thresholds
the stray itself; every build prints the worst stray against the ceiling.

THE WATER RECORDS ARE LEFT OUT. TIGERweb files New Hampshire's coastal water
under a "not defined" record in each layer (CD120 ZZ, SLDU ZZZ, SLDL ZZZ),
with no land; it is not a district and nobody represents it, so it is not
written, and a click on that water gets no district.

Prerequisites: requests, shapely, certifi, and Node.js (mapshaper via
`npx mapshaper@<pinned>`).

Usage:
    python3 nh/scripts/build_legislative_boundaries.py
"""

import datetime
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET_ROOT = os.path.dirname(REPO_ROOT)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer"
GRANIT = ("https://nhgeodata.unh.edu/hosting/rest/services/Hosted/"
          "APB_ElectoralDistricts/FeatureServer")
NH_FIPS = "33"
HEADERS = {"User-Agent": "districtry boundary builder (+https://districtry.com/nh/)"}
REQUEST_TIMEOUT = 300

# The state envelope the app accepts a click in (the worksheet's
# permalink_gate) — validation samples uniformly over it.
STATE_BBOX = {"minLng": -72.7, "minLat": 42.6, "maxLng": -70.4, "maxLat": 45.4}

# GRANIT writes each district as a county code and a number ("BE3", "HI03").
COUNTY_CODES = {
    "BE": "Belknap", "CA": "Carroll", "CH": "Cheshire", "CO": "Coos",
    "GR": "Grafton", "HI": "Hillsborough", "ME": "Merrimack",
    "RO": "Rockingham", "ST": "Strafford", "SU": "Sullivan",
}

# map -> how to build data/app/<out>.
#   url:        the TIGERweb layer, filtered to New Hampshire
#   fields:     outFields kept
#   key:        the field that numbers or names the district
#   layer_name: the layer's name as its service states it
#   serving_until / same_as: (us-house only) see check_serving_map and
#               check_same_map
#   out:        the data/app file index.html fetches for this layer
#   count:      the real district count; the build refuses any other
LAYERS = {
    "us-house": {
        "url": TIGERWEB + "/0",
        "fields": ["CD120", "NAME", "BASENAME", "GEOID", "STATE"],
        "key": "CD120",
        "layer_name": "120th Congressional Districts",
        "same_as": {"url": TIGERWEB + "/4", "layer_name": "119th Congressional Districts",
                    "field": "CD119", "same_until": "2027-01-03"},
        "serving_until": "2029-01-03",
        "out": "congress-districts.json",
        "count": 2,
    },
    "nh-senate": {
        "url": TIGERWEB + "/1",
        "fields": ["SLDU", "NAME", "BASENAME", "GEOID", "STATE"],
        "key": "SLDU",
        "layer_name": "2026 State Legislative Districts - Upper",
        "out": "nh-senate-districts.json",
        "count": 24,
    },
    "nh-house": {
        "url": TIGERWEB + "/2",
        "fields": ["SLDL", "NAME", "BASENAME", "GEOID", "STATE"],
        "key": "SLDL",
        "layer_name": "2026 State Legislative Districts - Lower",
        "out": "nh-house-districts.json",
        "count": 164,  # the base districts; the 39 floterials ride on them
    },
}
SIMPLIFY = ["dp", "keep-shapes", "interval=5"]
FLOTERIAL_COUNT = 39

PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live
VALIDATION_KEY = "GEOID"  # unique per district, preserved through simplification

# 8 m, PINNED rather than recomputed each run (see the docstring): every run
# prints the measured median source step beside this value, because a
# ceiling derived from the source each run can never fail.
FIDELITY_CEILING_M = 8.0


def _rings_of(geom):
    """Every ring of a Polygon or MultiPolygon, outers and holes alike."""
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "Polygon":
        return c
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


def _get_json(url, params):
    import requests  # noqa: PLC0415 (only the fetching path needs it)
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="nh-build-legislative-boundaries")
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        # An API error is not an empty answer (CLAUDE.md): read the key, never a
        # default that turns the error object into "no features".
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def fetch_layer(name, cfg, url=None, fields=None):
    """Every New Hampshire feature of the layer, as GeoJSON."""
    params = {"where": "STATE='%s'" % NH_FIPS,
              "outFields": ",".join(fields or cfg["fields"]),
              "returnGeometry": "true", "outSR": "4326",
              "geometryPrecision": "6", "f": "geojson"}
    url = url or cfg["url"]
    geo = _get_json(url + "/query", params)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("%s: %s returned no features" % (name, url))
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("%s: %s hit the transfer cap — needs paging" % (name, url))
    return geo


def _layer_name(url):
    return _get_json(url, {"f": "json"}).get("name", "")


def check_serving_map(name, cfg, today=None):
    """Refuse a layer that no longer carries the map it was chosen for, and a
    congressional map nobody has re-read since the 2028 election. TIGERweb
    renumbers its layers when a vintage rolls, so the index alone proves
    nothing."""
    got = _layer_name(cfg["url"])
    if got != cfg["layer_name"]:
        raise RuntimeError(
            "%s: %s is now %r, not %r — find the layer that is, and refuse "
            "rather than draw a different map" % (name, cfg["url"], got, cfg["layer_name"]))
    today = today or datetime.date.today().isoformat()
    if "serving_until" in cfg and today >= cfg["serving_until"]:
        raise RuntimeError(
            "%s: the members elected on New Hampshire's 2022 map in 2026 leave office on "
            "%s. Re-read which map the 2028 election used, then change this "
            "entry" % (name, cfg["serving_until"]))


def check_same_map(name, cfg, source, today=None):
    """Until `same_until`, the sitting members were elected from the OTHER
    layer's map, so this layer is drawn only while the two are the same map:
    the same districts, each with an intersection-over-union of at least
    0.9999 (shapely, on the full-precision fetch of both). Refuses otherwise.
    """
    same = cfg.get("same_as")
    today = today or datetime.date.today().isoformat()
    if not same or today >= same["same_until"]:
        return
    got = _layer_name(same["url"])
    if got != same["layer_name"]:
        raise RuntimeError(
            "%s: %s is now %r, not %r — re-read which map the sitting members "
            "were elected from" % (name, same["url"], got, same["layer_name"]))
    from shapely.geometry import shape  # noqa: PLC0415 (only this check needs it)
    other = fetch_layer(name, cfg, url=same["url"],
                        fields=[same["field"], "GEOID", "STATE"])
    mine = {f["properties"]["GEOID"]: shape(f["geometry"]) for f in source["features"]}
    theirs = {f["properties"]["GEOID"]: shape(f["geometry"]) for f in other["features"]
              if not str(f["properties"].get(same["field"]) or "").upper().startswith("ZZ")}
    if set(mine) != set(theirs):
        raise RuntimeError(
            "%s: %s and %s carry different districts (%s against %s) — the "
            "sitting members were elected from the second; refusing to draw "
            "the first" % (name, cfg["url"], same["url"], sorted(mine), sorted(theirs)))
    worst = 1.0
    for geoid, g in mine.items():
        o = theirs[geoid]
        iou = g.intersection(o).area / g.union(o).area
        worst = min(worst, iou)
        if iou < 0.9999:
            raise RuntimeError(
                "%s: district %s differs between %s and %s (IoU %.5f) — the "
                "sitting members were elected from the second; refusing to draw "
                "the first" % (name, geoid, cfg["url"], same["url"], iou))
    print("%s: %s matches %s district for district (lowest IoU %.6f)"
          % (name, cfg["layer_name"], same["layer_name"], worst))


# --- fidelity: how far the TRUE line strays from the chord drawn in its
#     place. The obvious direction gates nothing — simplification KEEPS a
#     subset of source vertices, so every drawn vertex already lies on the
#     source line and "no drawn vertex far from the source" is ~0 by
#     construction. What a reader sees is the other direction, so that is
#     what is measured: for every SOURCE vertex, its distance to the nearest
#     segment of its own district as drawn. -------------------------------
def _seg_index(feature, cell=0.02):
    idx = {}
    for ring in _rings_of(feature["geometry"]):
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    idx.setdefault((gx, gy), []).append((a, b))
    return idx


def _point_to_segment_m(p, a, b):
    my = 111320.0
    mx = 111320.0 * math.cos(math.radians(p[1]))
    px, py = p[0] * mx, p[1] * my
    ax, ay = a[0] * mx, a[1] * my
    bx, by = b[0] * mx, b[1] * my
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def median_source_step_m(features):
    """The median length of a source segment — what the true line's own
    detail is, and where FIDELITY_CEILING_M comes from. Printed on every run
    beside the pinned ceiling rather than used to recompute it: a ceiling
    derived from the source each run can never fail, because it rises
    whenever the source gets coarser."""
    steps = []
    for f in features:
        for ring in _rings_of(f["geometry"]):
            for i in range(len(ring) - 1):
                a, b = ring[i], ring[i + 1]
                my = 111320.0
                mx = 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
                steps.append(math.hypot((b[0] - a[0]) * mx, (b[1] - a[1]) * my))
    steps.sort()
    return steps[len(steps) // 2] if steps else 0.0


def check_fidelity(src_features, drawn_features, key_prop):
    """Worst stray in metres, and which districts exceed the ceiling."""
    drawn = {f["properties"].get(key_prop): f for f in drawn_features}
    worst = 0.0
    over = []
    for f in src_features:
        d = drawn.get(f["properties"].get(key_prop))
        if d is None:
            continue
        idx = _seg_index(d)
        w = 0.0
        for ring in _rings_of(f["geometry"]):
            for v in ring[:-1]:
                gx = int(math.floor(v[0] / 0.02))
                gy = int(math.floor(v[1] / 0.02))
                cand = []
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        cand += idx.get((gx + ddx, gy + ddy), ())
                if not cand:
                    continue
                best = min(_point_to_segment_m(v, a, b) for a, b in cand)
                if best > w:
                    w = best
        if w > worst:
            worst = w
        if w > FIDELITY_CEILING_M:
            over.append(f["properties"].get(key_prop))
    return worst, over


# --- point-in-polygon mirroring index.html's even-odd test (so validation
#     agrees with what the app computes at runtime) — fleet-standard copy ---
def _point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(pt, geom):
    if geom["type"] == "Polygon":
        inside = False
        for ring in geom["coordinates"]:
            if _point_in_ring(pt, ring):
                inside = not inside
        return inside
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            inside = False
            for ring in poly:
                if _point_in_ring(pt, ring):
                    inside = not inside
            if inside:
                return True
    return False


def _bbox(geom):
    b = [1e9, 1e9, -1e9, -1e9]

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            b[0], b[1] = min(b[0], c[0]), min(b[1], c[1])
            b[2], b[3] = max(b[2], c[0]), max(b[3], c[1])
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    return b


def _model(features, key_prop):
    return [(f["properties"].get(key_prop), f["geometry"], _bbox(f["geometry"])) for f in features]


def _districts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def validate(source_features, result_features, key_prop, samples=2000, seed=2024):
    """Refuse the build unless simplification preserves district coverage over
    the state envelope vs the full-precision fetch — the project's 2,000
    uniform-random-point protocol. Any point landing in two result districts
    is a topology break."""
    src = _model(source_features, key_prop)
    new = _model(result_features, key_prop)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = _districts_at(new, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = _districts_at(src, pt)
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    if overlaps > 0:
        return False, "topology broken: %d/%d points fell in >1 district" % (overlaps, samples)
    if pct < 99.5:
        return False, "point-in-district agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (agree, samples, pct)



def _district_name(basename):
    """TIGER's "Belknap 03" and GRANIT's "BE3"/"HI03" as the name New
    Hampshire uses: "Belknap 3"."""
    m = re.match(r"^([A-Za-z]+) 0*(\d+)$", str(basename or "").strip())
    if not m or m.group(1) not in COUNTY_CODES.values():
        return None
    return "%s %d" % (m.group(1), int(m.group(2)))


def _granit_name(code):
    m = re.match(r"^([A-Z]{2})0*(\d+)$", str(code or "").strip())
    if not m or m.group(1) not in COUNTY_CODES:
        return None
    return "%s %d" % (COUNTY_CODES[m.group(1)], int(m.group(2)))


def drop_water(name, cfg, source):
    """Leave out TIGER's "not defined" water record (see the docstring), and
    refuse if it ever carries land."""
    keep, dropped = [], []
    for f in source["features"]:
        key = str(f["properties"].get(cfg["key"]) or "")
        if key.upper().startswith("ZZ"):
            dropped.append(f)
        else:
            keep.append(f)
    for f in dropped:
        print("%s: left out %r (%s), the water TIGER files in no district"
              % (name, f["properties"].get("NAME"), f["properties"].get(cfg["key"])))
    source["features"] = keep
    return source


def _granit_get(path, params):
    import certifi  # noqa: PLC0415
    import requests  # noqa: PLC0415
    url = GRANIT + path
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="nh-build-legislative-boundaries", verify=certifi.where())
    # verify= on the request itself: a session's verify loses to
    # REQUESTS_CA_BUNDLE in the environment, which is how a sandbox's bundle
    # would otherwise win (see the docstring).
    resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                        verify=certifi.where())
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError("%s answered an error: %r" % (url, data["error"]))
    return data


def floterial_membership():
    """{base district name: floterial name} from GRANIT's 2022 layers, with the
    refusals the docstring names. Also returns {floterial: [base names]}."""
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    layers = {l["id"]: l["name"] for l in _granit_get("", {"f": "json"}).get("layers", [])}
    want = {8: "NHHouseDists2022_base", 9: "NHHouseDists2022_float"}
    for lid, nm in want.items():
        if layers.get(lid) != nm:
            raise RuntimeError("GRANIT layer %d is now %r, not %r — find the 2022 House "
                               "layers again before drawing anything" % (lid, layers.get(lid), nm))
    q = {"where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson",
         "resultRecordCount": "2000"}
    base_geo = _granit_get("/8/query", q)
    flot_geo = _granit_get("/9/query", q)
    bases = {}
    for f in base_geo["features"]:
        nm = _granit_name(f["properties"].get("basehse22"))
        if nm is None or nm in bases:
            raise RuntimeError("GRANIT base record %r is unreadable or doubled"
                               % f["properties"].get("basehse22"))
        bases[nm] = shape(f["geometry"]).buffer(0)
    flots = {}
    blank = 0
    for f in flot_geo["features"]:
        code = str(f["properties"].get("floathse22") or "").strip()
        if not code:
            blank += 1  # the ground in no floterial, filed as one blank record
            continue
        nm = _granit_name(code)
        if nm is None or nm in flots:
            raise RuntimeError("GRANIT floterial record %r is unreadable or doubled" % code)
        flots[nm] = shape(f["geometry"]).buffer(0)
    if len(flots) != FLOTERIAL_COUNT:
        raise RuntimeError("GRANIT carries %d floterial districts, not %d — read the plan "
                           "again before drawing anything" % (len(flots), FLOTERIAL_COUNT))
    member_of, made_of = {}, {}
    for fl, fg in sorted(flots.items()):
        whole = []
        for bn, bg in bases.items():
            inter = fg.intersection(bg).area
            if inter <= 0:
                continue
            share = inter / bg.area
            if share > 0.99:
                whole.append(bn)
            elif share > 1e-4:
                raise RuntimeError("floterial %s takes %.2f%% of base district %s — a "
                                   "floterial is made of whole base districts" % (fl, 100 * share, bn))
        if len(whole) < 2:
            raise RuntimeError("floterial %s is made of %d base district(s)" % (fl, len(whole)))
        diff = fg.symmetric_difference(unary_union([bases[b] for b in whole])).area / fg.area
        if diff > 1e-6:
            raise RuntimeError("floterial %s differs from the union of %s by %.6f of its area"
                               % (fl, ", ".join(whole), diff))
        for b in whole:
            if b in member_of:
                raise RuntimeError("base district %s sits in two floterials, %s and %s"
                                   % (b, member_of[b], fl))
            member_of[b] = fl
        made_of[fl] = sorted(whole, key=_name_order)
    print("GRANIT: %d base districts, %d floterials (each an exact union of whole base "
          "districts), %d base districts in one, %d blank record(s) for the ground in none"
          % (len(bases), len(flots), len(member_of), blank))
    return set(bases), member_of, made_of


def _name_order(name):
    c, n = name.rsplit(" ", 1)
    return (c, int(n))


def attach_house_names(house, granit_bases, member_of, made_of):
    """Each TIGER base district gets `district` and, where it has one,
    `floterial` and `floterialOf` (the base districts the floterial is made
    of, for the card's sentence)."""
    seen = set()
    for f in house["features"]:
        nm = _district_name(f["properties"].get("BASENAME"))
        if nm is None:
            raise RuntimeError("TIGER House record %r does not name a county district"
                               % f["properties"].get("BASENAME"))
        if nm in seen:
            raise RuntimeError("TIGER files House district %s twice" % nm)
        seen.add(nm)
        f["properties"]["district"] = nm
        fl = member_of.get(nm)
        if fl:
            f["properties"]["floterial"] = fl
            f["properties"]["floterialOf"] = ", ".join(made_of[fl])
    if seen != granit_bases:
        raise RuntimeError("TIGER's and GRANIT's base districts differ: %s only in TIGER, "
                           "%s only in GRANIT" % (sorted(seen - granit_bases),
                                                  sorted(granit_bases - seen)))


def run_mapshaper_combined(source_paths, out_dir):
    subprocess.run(
        ["npx", "-y", MAPSHAPER] + list(source_paths) + ["combine-files",
         "-simplify"] + SIMPLIFY + [
         "-o", "precision=" + PRECISION, "format=geojson", "target=*", out_dir],
        check=True, cwd=REPO_ROOT,
    )


def gate(name, cfg, source, simplified):
    n = len(simplified["features"])
    if n != cfg["count"]:
        raise RuntimeError("%s: %d features after simplify (expected exactly %d districts) "
                           "— refusing to write" % (name, n, cfg["count"]))
    ok, msg = validate(source["features"], simplified["features"], VALIDATION_KEY)
    if not ok:
        raise RuntimeError("%s validation failed: %s" % (name, msg))
    step = median_source_step_m(source["features"])
    worst, over = check_fidelity(source["features"], simplified["features"], VALIDATION_KEY)
    if over:
        raise RuntimeError("%s: %d district(s) stray past the %.0f m fidelity ceiling (worst "
                           "%.1f m): %s — refusing to write" % (name, len(over), FIDELITY_CEILING_M,
                                                                worst, ", ".join(sorted(over)[:5])))
    print("%s: %s; median source step %.2f m, worst stray %.1f m against a %.0f m ceiling, "
          "0 of %d districts over" % (name, msg, step, worst, FIDELITY_CEILING_M, n))


def write_map(cfg, simplified):
    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("%s round-trip mismatch before writing" % cfg["out"])
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(os.path.join(APP_DATA_DIR, cfg["out"]), "w") as f:
        f.write(compact)
    print("-> data/app/%s: %d features, %d bytes" % (cfg["out"], len(simplified["features"]),
                                                     len(compact)), file=sys.stderr)


def main():
    if sys.argv[1:]:
        print("this builder takes no arguments: the three maps share one topology, so "
              "rebuilding one alone is the defect it exists to prevent", file=sys.stderr)
        sys.exit(2)
    granit_bases, member_of, made_of = floterial_membership()
    source = {}
    for name, cfg in LAYERS.items():
        check_serving_map(name, cfg)
        src = drop_water(name, cfg, fetch_layer(name, cfg))
        check_same_map(name, cfg, src)
        source[name] = src
    attach_house_names(source["nh-house"], granit_bases, member_of, made_of)
    built = {}
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name in LAYERS:
            p = os.path.join(tmp, name + ".geojson")
            with open(p, "w") as f:
                json.dump(source[name], f)
            paths.append(p)
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir)
        run_mapshaper_combined(paths, out_dir)
        for name in LAYERS:
            op = os.path.join(out_dir, name + ".json")
            if not os.path.exists(op):
                raise RuntimeError("%s: mapshaper wrote no %s — combine-files names outputs "
                                   "after the inputs" % (name, op))
            with open(op) as f:
                built[name] = json.load(f)
    for name, cfg in LAYERS.items():
        gate(name, cfg, source[name], built[name])
    for name, cfg in LAYERS.items():
        write_map(cfg, built[name])


if __name__ == "__main__":
    main()
