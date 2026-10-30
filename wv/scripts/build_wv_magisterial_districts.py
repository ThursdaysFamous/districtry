#!/usr/bin/env python3
"""
Build data/app/wv-magisterial-districts.json, West Virginia's 195 magisterial
districts, from the state's own election map, so the app answers which
magisterial district a point is in with no request to anyone.

WHAT A MAGISTERIAL DISTRICT IS HERE. Every West Virginia county is divided
into three or more magisterial districts (W. Va. Code 7-2-2), and they are the
state's county subdivisions: the Census Bureau files them as its minor civil
divisions in West Virginia. They elect nobody of their own. They matter to a
reader because the county commission and the county board of education are
elected by the whole county but each draws its members from them: no two
county commissioners may live in the same magisterial district (W. Va. Const.
art. IX, sec. 10), and no more than two school board members may (W. Va. Code
18-5-1). So the card names the district a point is in, and the County card says
what the rule is.

THE LINES ARE THE STATE'S, NOT THE CENSUS BUREAU'S, AND THAT IS A MEASUREMENT.
The West Virginia GIS Technical Center at West Virginia University runs the
state's map service; its Boundaries/WV_Election_Layers folder carries a
"Magisterial 2026" layer (layer 9 at street scale, layer 10 a generalized copy
for small scales) with 195 districts in all 55 counties: three in 38 counties,
four in 9, five in 5, six in Berkeley and Harrison and eight in Hampshire
(measured 2026-10-29). State law since 2022 (W. Va. Code 3-1-5, as amended by
SB 253) has each county send its current precinct and magisterial maps to the
Secretary of State, and the centre redrew them for the county clerks, which is
why one statewide layer exists. TIGERweb's current county-subdivision layer
carries 225 records for STATE='54' (170 coded LSAD 27 and 55 coded LSAD 28),
and the research for this instance's plan found only about 26 counties whose
Census subdivisions were plausibly current, so the state's layer is drawn. The
service states no licence or terms; the plan records that as unmeasured and
asks the centre in a letter.

EACH DISTRICT IS KEYED BY ITS NAME, NOT ITS NUMBER. The layer's DISTRICT
number is empty in Jefferson and Hampshire counties, and in Harrison County it
disagrees with the number the statewide voter registration system uses
(SVRS_Mag_Name: the layer's district 1, Northern District, is the system's 5).
So a number would be a claim nobody publishes consistently, and neither number
is shipped; each district carries its county's GEOID and its own name, which is
unique inside its county on every build or the build refuses.

THE SAME SERVICE HOLDS A LAYER OF INDIVIDUAL VOTER LOCATIONS (the
Applications/WV_Election folder). It is never read, by this builder or any
other.

THE STATE'S LAYER CARRIES DRAWING SLIVERS, AND THEY ARE REMOVED BEFORE
SIMPLIFYING. Measured 2026-10-29: 44 rings under 10 square metres, in four
districts, every one smaller than 7.2 square metres, against 2,022 square
metres for the next smallest ring (a real enclave of Monongalia's Eastern
District inside its Central District, which is kept). Almost all of them are
one seam drawn twice in Preston County, where District 2 carries 21 detached
fragments that sit exactly in 16 holes of District 3; the rest are a 0.31
square-metre fragment of Nicholas County's Birch District and two holes in
Kanawha County. Douglas-Peucker drops a ring that small, which leaves a source
vertex with no drawn line near it and fails the fidelity check below, so a
part or hole under SLIVER_M2 is removed here instead, and every run prints how
many and how much ground they held. Removing a fragment and the hole it sits
in gives that ground to the district around it; removing either alone changes
the answer over at most SLIVER_M2 of ground.

THE LAYER ALSO CARRIES SPIKES, AND THEY ARE REMOVED TOO. A spike is a line
that runs out from a boundary and comes straight back along itself, so it
encloses no ground: measured 2026-10-29, a 328-metre one on Upshur County's
1st District (80.3176 W, 39.0152 N), an 11.7-metre one on Marshall County's
District 3 and a 17.5-metre one where Preston County's District 3 ring starts (a
triangle of 0.75 square metres, its sides under half a degree apart).
Simplifying drops each one at every interval tried (5, 2 and 1 metres), which
reads to the fidelity check as the drawn line straying 17.5 metres from the
true one, though no point's answer changes. So a vertex is removed when the
two vertices beside it are under SPIKE_GAP_M apart, or when the line turns
back on itself there (an angle under SPIKE_ANGLE_DEG) around a triangle under
SPIKE_M2, and every run prints how many and the ground those triangles held.

SIMPLIFICATION IS DOUGLAS-PEUCKER AT 5 M UNDER AN 8 M CEILING, the setting
this instance's county and legislative files carry.

Usage:
    python3 wv/scripts/build_wv_magisterial_districts.py           # rebuild
    python3 wv/scripts/build_wv_magisterial_districts.py --check   # verify the shipped file offline
"""

import argparse
import json
import math
import os
import random
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

REPO_ROOT = os.path.dirname(_HERE)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
sys.path.append(os.path.join(os.path.dirname(REPO_ROOT), "scripts"))
import boundary_fidelity  # noqa: E402  (shared and stdlib only; appended, so it shadows nothing here)

LAYER = blb.STATE_GIS + "/9"
LAYER_NAME = "Magisterial 2026"
FIELDS = ["LONGNAME", "SHORTNAME", "DISTRICT", "County_Name", "SVRS_Mag_Name"]
OUT_FILE = "wv-magisterial-districts.json"
COUNTIES_FILE = "state-counties.json"
SIMPLIFY = "interval=5"
FIDELITY_MAX_M = 8.0
COUNT = 195  # measured 2026-10-29; a change is a county redistricting, read before it is drawn
# How many districts each county has, by count of counties (measured 2026-10-29).
SHAPE = {3: 38, 4: 9, 5: 5, 6: 2, 8: 1}
VALIDATION_KEY = "KEY"
# A ring smaller than this is a drawing sliver (the docstring's measurement:
# the largest is 7.18 m2 and the next ring up is 2,022 m2).
SLIVER_M2 = 10.0
# A spike's tip: its neighbours closer than this (the 6-decimal output cell is
# about 0.1 m) ...
SPIKE_GAP_M = 0.2
# ... or a turn back sharper than this around a triangle smaller than this.
SPIKE_ANGLE_DEG = 5.0
SPIKE_M2 = 1.0
# The share of sample points inside the state on which a district's county
# must be the county the County layer answers.
COUNTY_AGREEMENT_MIN = 99.5


def county_geoids():
    """County name -> 5-digit GEOID, from the shipped county file."""
    with open(os.path.join(APP_DATA_DIR, COUNTIES_FILE)) as f:
        counties = json.load(f)
    out = {}
    for feat in counties["features"]:
        p = feat["properties"]
        out[str(p["BASENAME"])] = str(p["GEOID"])
    if len(out) != 55:
        raise RuntimeError("%s carries %d counties, not 55" % (COUNTIES_FILE, len(out)))
    return out, counties["features"]


def fetch():
    info = blb._get_json(LAYER, {"f": "json"})
    if info.get("name") != LAYER_NAME:
        raise RuntimeError("%s is now %r, not %r — read it before drawing it"
                           % (LAYER, info.get("name"), LAYER_NAME))
    geo = blb._get_json(LAYER + "/query", {
        "where": "1=1", "outFields": ",".join(FIELDS),
        "returnGeometry": "true", "outSR": "4326",
        "geometryPrecision": "6", "f": "geojson",
    })
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("%s hit the transfer cap — needs paging" % LAYER)
    return geo


def _ring_m2(ring):
    """A ring's area in square metres, on a plane scaled at its own latitude
    (rings this small are flat for any purpose here)."""
    lat = sum(pt[1] for pt in ring) / len(ring)
    sx = 111320.0 * math.cos(math.radians(lat))
    sy = 110540.0
    acc = 0.0
    for i in range(len(ring) - 1):
        acc += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(acc) / 2.0 * sx * sy


def drop_slivers(geo):
    """Remove every polygon part and every hole under SLIVER_M2, never a
    district's last part. Returns (parts removed, holes removed, m2 held)."""
    parts = holes = 0
    area = 0.0
    for f in geo["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        kept = []
        for poly in polys:
            a = _ring_m2(poly[0])
            if a < SLIVER_M2:
                parts += 1
                area += a
                continue
            inner = []
            for h in poly[1:]:
                ha = _ring_m2(h)
                if ha < SLIVER_M2:
                    holes += 1
                    area += ha
                else:
                    inner.append(h)
            kept.append([poly[0]] + inner)
        if not kept:
            raise RuntimeError("%s: every part is under %.0f m2" % (
                f["properties"].get("NAME"), SLIVER_M2))
        if len(kept) == 1:
            f["geometry"] = {"type": "Polygon", "coordinates": kept[0]}
        else:
            f["geometry"] = {"type": "MultiPolygon", "coordinates": kept}
    return parts, holes, area


def _despike_ring(ring):
    """The ring with every spike removed, and the m2 the removed triangles
    held. Works on the open ring and closes it again."""
    pts = [tuple(p[:2]) for p in ring[:-1]] if ring[0] == ring[-1] else [tuple(p[:2]) for p in ring]
    lat = sum(p[1] for p in pts) / len(pts)
    sx = 111320.0 * math.cos(math.radians(lat))
    sy = 110540.0
    removed = 0
    area = 0.0
    changed = True
    while changed and len(pts) > 3:
        changed = False
        out = []
        n = len(pts)
        skip_next = False
        i = 0
        while i < n:
            v = pts[i]
            a = out[-1] if out else pts[i - 1]
            b = pts[(i + 1) % n]
            ax, ay = (a[0] - v[0]) * sx, (a[1] - v[1]) * sy
            bx, by = (b[0] - v[0]) * sx, (b[1] - v[1]) * sy
            gap = math.hypot(ax - bx, ay - by)
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            tri = abs(ax * by - ay * bx) / 2.0
            spike = False
            if la > 0 and lb > 0:
                cosang = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
                ang = math.degrees(math.acos(cosang))
                spike = gap < SPIKE_GAP_M or (ang < SPIKE_ANGLE_DEG and tri < SPIKE_M2)
            if spike and n - removed > 3:
                removed += 1
                area += tri
                changed = True
                if gap < SPIKE_GAP_M and (i + 1) < n:
                    i += 2  # b sits on a: drop it too
                    removed += 1
                    continue
                i += 1
                continue
            out.append(v)
            i += 1
        pts = out
        if len(pts) < 3:
            raise RuntimeError("a ring is all spike")
    return [list(p) for p in pts] + [list(pts[0])], removed, area


def drop_spikes(geo):
    """Remove every spike vertex. Returns (vertices removed, m2 held)."""
    removed = 0
    area = 0.0
    for f in geo["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for k in range(len(poly)):
                poly[k], r, a = _despike_ring(poly[k])
                removed += r
                area += a
    return removed, area


def _slug(name):
    out = []
    for ch in name.lower():
        out.append(ch if ch.isalnum() else "-")
    return "-".join(part for part in "".join(out).split("-") if part)


def normalize(geo, geoids):
    """Write each district with the properties the card reads, and refuse
    unless every county's district names are unique and the count of
    districts per county is the measured SHAPE."""
    by_county = {}
    for f in geo["features"]:
        p = f.get("properties") or {}
        county = str(p.get("County_Name") or "").strip()
        if county not in geoids:
            raise RuntimeError("a district names county %r, which is not one of the 55" % county)
        name = " ".join(str(p.get("LONGNAME") or "").split())
        if not name:
            raise RuntimeError("%s: a district carries no name" % county)
        if name in by_county.get(county, []):
            raise RuntimeError("%s has two districts named %r" % (county, name))
        by_county.setdefault(county, []).append(name)
        geoid = geoids[county]
        f["properties"] = {
            "KEY": "%s-%s" % (geoid, _slug(name)),
            "NAME": name,
            "COUNTY": county + " County",
            "COUNTYFP": geoid,
        }
    if len(by_county) != 55:
        raise RuntimeError("districts in %d counties, not 55" % len(by_county))
    shape = {}
    for county, names in by_county.items():
        shape[len(names)] = shape.get(len(names), 0) + 1
    if shape != SHAPE:
        raise RuntimeError("districts per county now %r, not %r — a county has "
                           "redistricted; read it before drawing it" % (shape, SHAPE))
    return geo


def check_counties(features, county_features):
    """Every sample point inside the state that falls in a district falls in
    that district's own county, by the County layer's own file."""
    mags = blb._model(features, VALIDATION_KEY)
    cfp = {f["properties"]["KEY"]: f["properties"]["COUNTYFP"] for f in features}
    counties = blb._model(county_features, "GEOID")
    rng = random.Random(54)
    agree = tried = 0
    while tried < 2000:
        pt = (rng.uniform(blb.STATE_BBOX["minLng"], blb.STATE_BBOX["maxLng"]),
              rng.uniform(blb.STATE_BBOX["minLat"], blb.STATE_BBOX["maxLat"]))
        c = blb._districts_at(counties, pt)
        if len(c) != 1:
            continue
        tried += 1
        m = blb._districts_at(mags, pt)
        if len(m) == 1 and cfp[m[0]] == c[0]:
            agree += 1
    pct = 100.0 * agree / tried
    if pct < COUNTY_AGREEMENT_MIN:
        return False, "only %.2f%% of points inside a county fall in one of its districts" % pct
    return True, "%d/%d points inside a county fall in one of that county's districts (%.2f%%)" % (
        agree, tried, pct)


def check_shipped():
    path = os.path.join(APP_DATA_DIR, OUT_FILE)
    with open(path) as f:
        shipped = json.load(f)
    feats = shipped["features"]
    problems = []
    if len(feats) != COUNT:
        problems.append("%s carries %d districts, not %d" % (OUT_FILE, len(feats), COUNT))
    geoids, county_features = county_geoids()
    by_county = {}
    for f in feats:
        p = f["properties"]
        for k in ("KEY", "NAME", "COUNTY", "COUNTYFP"):
            if p.get(k) in (None, ""):
                problems.append("a district carries no %s: %r" % (k, p))
        by_county.setdefault(p.get("COUNTYFP"), []).append(p.get("NAME"))
    if set(by_county) != set(geoids.values()):
        problems.append("the districts' counties are not the 55 counties of %s" % COUNTIES_FILE)
    shape = {}
    for names in by_county.values():
        shape[len(names)] = shape.get(len(names), 0) + 1
        if len(set(names)) != len(names):
            problems.append("a county has two districts of one name: %r" % sorted(names))
    if shape != SHAPE:
        problems.append("districts per county are %r, not %r" % (shape, SHAPE))
    ok, msg = check_counties(feats, county_features)
    if not ok:
        problems.append(msg)
    for p in problems:
        print("FAIL: %s" % p, file=sys.stderr)
    if problems:
        sys.exit(1)
    print("wv-magisterial-districts: OK — %d districts in 55 counties; %s" % (len(feats), msg))


def main():
    ap = argparse.ArgumentParser(description="Build West Virginia's magisterial districts.")
    ap.add_argument("--check", action="store_true", help="verify the shipped file offline")
    args = ap.parse_args()
    if args.check:
        check_shipped()
        return
    geoids, county_features = county_geoids()
    source = normalize(fetch(), geoids)
    parts, holes, sliver_m2 = drop_slivers(source)
    print("wv-magisterial-districts: removed %d sliver part(s) and %d sliver hole(s) "
          "under %.0f m2, holding %.1f m2 in all" % (parts, holes, SLIVER_M2, sliver_m2))
    spikes, spike_m2 = drop_spikes(source)
    print("wv-magisterial-districts: removed %d spike vertex(es), whose triangles held "
          "%.2f m2 in all" % (spikes, spike_m2))
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "mag-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, "mag.geojson")
        blb.run_mapshaper(src_path, SIMPLIFY, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)
    n = len(simplified["features"])
    if n != COUNT:
        raise RuntimeError("%d districts after simplify, not %d — refusing to write" % (n, COUNT))
    ok, msg = blb.validate(source["features"], simplified["features"], VALIDATION_KEY)
    if not ok:
        raise RuntimeError("validation failed: %s" % msg)
    step = blb.median_source_step_m(source["features"])
    ok, fmsg = boundary_fidelity.check_fidelity(
        source["features"], simplified["features"], VALIDATION_KEY, FIDELITY_MAX_M, "NAME")
    if not ok:
        raise RuntimeError("fidelity failed: %s — refusing to write" % fmsg)
    ok, cmsg = check_counties(simplified["features"], county_features)
    if not ok:
        raise RuntimeError("county check failed: %s — refusing to write" % cmsg)
    compact = json.dumps(simplified, separators=(",", ":"))
    with open(os.path.join(APP_DATA_DIR, OUT_FILE), "w") as f:
        f.write(compact)
    print("wv-magisterial-districts: median source step %.2f m; %s" % (step, fmsg))
    print("-> data/app/%s: %d districts; %s; %s; %d bytes (dp %s, 6dp)"
          % (OUT_FILE, n, msg, cmsg, len(compact), SIMPLIFY))


if __name__ == "__main__":
    main()
