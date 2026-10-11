#!/usr/bin/env python3
"""
Build South Carolina's county council districts — all 46 counties, one file —
from the state Revenue and Fiscal Affairs Office's statewide layer, so the app
fetches them same-origin (cache-first) instead of reading a 15 MB service live.

THE PUBLISHER IS THE STATE, NOT 46 COUNTIES. The Revenue and Fiscal Affairs
Office (RFA) keeps South Carolina's redistricting geography and publishes every
county's council districts as one feature service
(gis.state.sc.us, Boundaries_Districts/County_Council_Districts). Measured
2026-10-10: 315 districts in 46 counties, each carrying its county, its
district number, and for most counties the ordinance and effective date of the
plan. The host's robots.txt answers 404, which permits every path.

THREE COUNTIES ARE NOT ORDINARY DISTRICT MAPS, AND `FORMS` SAYS WHICH:

  Hampton  draws ONE feature, numbered "0", covering the whole county. Its
           five council members are all elected at large (certified results:
           three in 2022, two in 2024), so there is no district to draw and the
           feature is the county. The card names all five.
  Jasper   draws four districts, and its council members are elected by the
           whole county: each of four must live in one of four residence areas,
           which the county names by township (Coosawhatchie, Hardeeville,
           Pocotaligo, Robertville), and a fifth is elected at large. The
           certified results confirm the countywide vote; which of the map's
           numbers is which township is published by NEITHER the state's layer
           nor the county's own redistricting service (Jasper County's
           REDISTRICTING FeatureServer numbers them 1-4 too), so the card
           names the residence district by number and names all five members.
  Colleton draws two districts numbered "23" and "45", and Greenville numbers
           its twelve 17 to 28. Both are what the county's own ballots use, so
           they ship as published.

Everything else here is the method `build_legislative_boundaries.py` already
uses for this instance, applied to one more layer: Douglas-Peucker
simplification in metres (not Visvalingam, whose area threshold does not bound
how far a line strays), the 2,000-point agreement gate, and a fidelity ceiling
measured against the source. ALL 46 COUNTIES GO THROUGH ONE MAPSHAPER RUN so
an edge two districts share — inside a county, or where two counties meet —
is one arc simplified once and survives identically on both sides.

ONE GATE IS NEW, BECAUSE A COUNCIL MAP HAS A WITNESS THE LEGISLATIVE MAPS DO
NOT: every county's districts must cover that county. Each district's county is
checked against the Census county fabric this instance already ships
(state-counties.json) — points sampled inside each county must land in a
district OF THAT COUNTY — so a district filed under the wrong county, a county
whose map covers half its ground, or two counties' districts overlapping all
fail the build.

`--watch` is for the weekly job. It reads the live layer's attributes and areas
(no geometry, one request) and compares them with the fingerprint recorded
when the shipped file was built (data/source/sc-county-council-districts.source.json).
A difference means a county redistricted or the state re-published its layer;
the job opens an issue and this file is rebuilt by hand, because a new council
map also changes which seat a certified winner holds and needs a person to read
it alongside the roster.

`--check` is offline and runs in CI: the shipped file's districts, counties and
tiling, held to the recorded fingerprint and to state-counties.json.

Usage:
    python3 sc/scripts/build_sc_county_council_districts.py           # fetch, build, write
    python3 sc/scripts/build_sc_county_council_districts.py --check   # offline gate
    python3 sc/scripts/build_sc_county_council_districts.py --watch   # has the source moved?
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

APP_DATA = os.path.join(INSTANCE, "data", "app")
OUT_FILE = os.path.join(APP_DATA, "sc-county-council-districts.json")
COUNTIES_FILE = os.path.join(APP_DATA, "state-counties.json")
SOURCE_RECORD = os.path.join(INSTANCE, "data", "source",
                             "sc-county-council-districts.source.json")

LAYER = ("https://gis.state.sc.us/arcgis/rest/services/Boundaries_Districts/"
         "County_Council_Districts/FeatureServer/0")
USER_AGENT = "districtry/1.0 (+https://districtry.com/sc/)"
MAPSHAPER = "mapshaper@0.6.102"  # pinned, as in build_legislative_boundaries.py
PRECISION = "0.000001"
SIMPLIFY = "interval=20"

EXPECT_DISTRICTS = 315
EXPECT_COUNTIES = 46

# The counties whose features are not one-member election districts. See the
# docstring; the roster builder holds its own seat table to these.
FORMS = {
    "Hampton": "whole-county",
    "Jasper": "residence",
}

# 25 m, PINNED, and the same ceiling this instance's legislative builder holds
# its three chambers to. The council layer's own median source step, measured
# 2026-10-11 on all 315 districts, is 23.41 m, so the ceiling is a little over
# one step, as it is for the chambers (17.8-24.3 m). At interval=20 the worst
# stray was 20.9 m with no district over; interval=25 put eight districts past
# the ceiling (worst 27.6 m), and interval=15 cost 17% more bytes (654 KB
# gzipped against 558 KB) for a 15.7 m worst stray. Every run prints the
# measured step beside this value; a ceiling recomputed from the source each
# run could never fail.
FIDELITY_CEILING_M = 25.0

# Points sampled inside each county for the tiling gate, and how many of them
# may land in no district or in another county's district — two publishers'
# county lines disagreeing. Measured 2026-10-11 on the simplified file at 400
# points a county: every county put at least 98.75% of its points in its own
# districts, the most in another county's was Charleston's 5 of 400 (three of
# them in Georgetown's District 3, near 33.07,-79.25, where the Census's
# Charleston County and the state's Georgetown council map overlap along the
# coast), and one point in the whole state landed in no district (McCormick
# County, 1 of 400). The floor
# and ceiling sit just outside those measurements so that a county whose map
# is missing a district, or filed under the wrong county, fails by a wide
# margin.
TILING_SAMPLES = 400
TILING_MIN_SAME = 0.97
TILING_MAX_OTHER = 0.02


def fail(msg):
    raise SystemExit("build-sc-county-council-districts: FATAL: %s" % msg)


def county_title(raw):
    """RFA writes counties in capitals; the app and the Census write them in
    title case, with McCormick's inner capital."""
    t = raw.strip().title()
    return "McCormick" if t == "Mccormick" else t


# ---------- fetch ----------
def fetch_source(session):
    url = (LAYER + "/query?where=1%3D1&outFields=District,County,FIPS,Ordinance,"
           "EffectiveDate,Shape__Area&outSR=4326&geometryPrecision=6&f=geojson")
    require_robots_once(url, USER_AGENT, label="sc-council-districts")
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
    resp.raise_for_status()
    geo = resp.json()
    if "error" in geo:
        fail("the layer answered an error envelope: %r" % geo["error"])
    if geo.get("exceededTransferLimit") or (geo.get("properties") or {}).get("exceededTransferLimit"):
        fail("the layer hit its transfer cap — this builder needs paging")
    return geo


def fetch_fingerprint(session):
    """The live layer's attributes and areas, no geometry — one request."""
    url = (LAYER + "/query?where=1%3D1&outFields=District,County,FIPS,Ordinance,"
           "EffectiveDate,Shape__Area&returnGeometry=false&f=json")
    require_robots_once(url, USER_AGENT, label="sc-council-districts")
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    resp.raise_for_status()
    doc = resp.json()
    if "error" in doc:
        fail("the layer answered an error envelope: %r" % doc["error"])
    return fingerprint([f["attributes"] for f in doc.get("features") or []])


def fingerprint(rows):
    """A stable digest of what a redistricting changes: which districts each
    county has, the ordinance and date that adopted them, and each district's
    area to the square metre. Sorted, so record order cannot move it."""
    lines = sorted("%s|%s|%s|%s|%d" % (
        r.get("FIPS"), str(r.get("District")).strip(), r.get("Ordinance") or "",
        r.get("EffectiveDate") or "", round(float(r.get("Shape__Area") or 0)))
        for r in rows)
    return {"districts": len(lines),
            "sha256": hashlib.sha256("\n".join(lines).encode()).hexdigest()}


# ---------- normalise ----------
def normalise(source):
    feats = []
    seen = set()
    for f in source.get("features") or []:
        p = f.get("properties") or {}
        county = county_title(p.get("County") or "")
        fips = str(p.get("FIPS") or "").strip()
        dist = str(p.get("District") or "").strip()
        if not county or not fips.startswith("45") or len(fips) != 5 or not dist:
            fail("a feature with an unreadable county or district: %r" % p)
        key = "%s-%s" % (fips, dist)
        if key in seen:
            fail("district %s appears twice" % key)
        seen.add(key)
        form = FORMS.get(county, "district")
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "key": key, "county": county, "countyFips": fips,
            "district": dist, "form": form}})
    return {"type": "FeatureCollection", "features": feats}


# ---------- simplify (the legislative builder's method) ----------
def run_mapshaper(source_path, out_path):
    subprocess.run(
        ["npx", "-y", MAPSHAPER, source_path,
         "-simplify", "dp", "keep-shapes", SIMPLIFY,
         "-o", "precision=" + PRECISION, "format=geojson", out_path],
        check=True, cwd=INSTANCE)


def _rings_of(geom):
    t = geom.get("type")
    c = geom.get("coordinates") or []
    if t == "Polygon":
        return c
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return []


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
    steps = []
    for f in features:
        for ring in _rings_of(f["geometry"]):
            for i in range(len(ring) - 1):
                a, b = ring[i], ring[i + 1]
                mx = 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
                steps.append(math.hypot((b[0] - a[0]) * mx, (b[1] - a[1]) * 111320.0))
    steps.sort()
    return steps[len(steps) // 2] if steps else 0.0


def check_fidelity(src_features, drawn_features):
    """Worst distance from a SOURCE vertex to its own district as drawn — the
    direction a reader sees (the drawn line keeps a subset of source vertices,
    so the other direction is ~0 by construction)."""
    drawn = {f["properties"]["key"]: f for f in drawn_features}
    worst, over = 0.0, []
    for f in src_features:
        d = drawn.get(f["properties"]["key"])
        if d is None:
            continue
        idx = _seg_index(d)
        w = 0.0
        for ring in _rings_of(f["geometry"]):
            for v in ring[:-1]:
                gx, gy = int(math.floor(v[0] / 0.02)), int(math.floor(v[1] / 0.02))
                cand = []
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        cand += idx.get((gx + ddx, gy + ddy), ())
                if cand:
                    w = max(w, min(_point_to_segment_m(v, a, b) for a, b in cand))
        worst = max(worst, w)
        if w > FIDELITY_CEILING_M:
            over.append(f["properties"]["key"])
    return worst, over


# ---------- point-in-polygon, the app's even-odd rule ----------
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


def _model(features):
    return [(f["properties"]["key"], f["properties"]["countyFips"], f["geometry"],
             _bbox(f["geometry"])) for f in features]


def _hits(model, pt):
    return [(k, c) for k, c, g, bb in model
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
            and _point_in_geometry(pt, g)]


STATE_BBOX = {"minLng": -83.36, "minLat": 31.99, "maxLng": -78.49, "maxLat": 35.22}


def validate(source_features, result_features, samples=2000, seed=2024):
    """The fleet's 2,000 uniform-random-point protocol over the state
    envelope: the simplified file must answer as the source does at >= 99.5%
    of points, and no point may land in two districts."""
    src, new = _model(source_features), _model(result_features)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = [k for k, _ in _hits(new, pt)]
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = [k for k, _ in _hits(src, pt)]
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        agree += o == s
    pct = 100.0 * agree / samples
    if overlaps:
        return False, "topology broken: %d/%d points fell in >1 district" % (overlaps, samples)
    if pct < 99.5:
        return False, "point-in-district agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (agree, samples, pct)


# ---------- the county tiling gate ----------
def check_tiling(features, seed=2026):
    """Points sampled inside each Census county must land in a district of
    that county. Returns (problems, report lines)."""
    with open(COUNTIES_FILE, encoding="utf-8") as f:
        counties = json.load(f)["features"]
    model = _model(features)
    rng = random.Random(seed)
    problems, worst = [], []
    by_fips = {}
    for feat in features:
        by_fips.setdefault(feat["properties"]["countyFips"], []).append(feat)
    census = {c["properties"]["GEOID"]: c for c in counties}
    if set(by_fips) != set(census):
        problems.append("the council map's counties %s do not match the Census "
                        "fabric's %d" % (sorted(set(by_fips) ^ set(census)), len(census)))
    for geoid, c in sorted(census.items()):
        geom = c["geometry"]
        bb = _bbox(geom)
        same = other = none = n = 0
        tries = 0
        while n < TILING_SAMPLES and tries < TILING_SAMPLES * 50:
            tries += 1
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            if not _point_in_geometry(pt, geom):
                continue
            n += 1
            hits = _hits(model, pt)
            if len(hits) > 1:
                problems.append("%s: a point at %.5f,%.5f is in %d districts: %s"
                                % (c["properties"]["NAME"], pt[1], pt[0], len(hits),
                                   ", ".join(k for k, _ in hits)))
            if any(cf == geoid for _, cf in hits):
                same += 1
            elif hits:
                other += 1
            else:
                none += 1
        frac_same, frac_other = same / float(n), other / float(n)
        worst.append((frac_same, c["properties"]["NAME"], same, other, none, n))
        if frac_same < TILING_MIN_SAME:
            problems.append("%s: only %d of %d points inside the county land in one "
                            "of its own council districts (%d in another county's, "
                            "%d in none)" % (c["properties"]["NAME"], same, n, other, none))
        if frac_other > TILING_MAX_OTHER:
            problems.append("%s: %d of %d points inside the county land in another "
                            "county's district" % (c["properties"]["NAME"], other, n))
    worst.sort()
    lines = ["tiling: lowest own-district share %.4f (%s: %d same, %d other, %d none of %d)"
             % (worst[0][0], worst[0][1], worst[0][2], worst[0][3], worst[0][4], worst[0][5])]
    most_other = max(worst, key=lambda w: w[3])
    most_none = max(worst, key=lambda w: w[4])
    lines.append("tiling: most points in another county's district: %s %d; most in "
                 "none: %s %d" % (most_other[1], most_other[3], most_none[1], most_none[4]))
    lines.append("tiling: %d counties, %d sample points each; floor %.2f own, ceiling %.2f other"
                 % (len(worst), TILING_SAMPLES, TILING_MIN_SAME, TILING_MAX_OTHER))
    return problems, lines


def check_shipped(geo):
    problems = []
    feats = geo.get("features") or []
    if len(feats) != EXPECT_DISTRICTS:
        problems.append("%d districts, expected %d" % (len(feats), EXPECT_DISTRICTS))
    keys = [f["properties"].get("key") for f in feats]
    if len(set(keys)) != len(keys):
        problems.append("a district key appears twice")
    counties = {f["properties"].get("countyFips") for f in feats}
    if len(counties) != EXPECT_COUNTIES:
        problems.append("%d counties, expected %d" % (len(counties), EXPECT_COUNTIES))
    for f in feats:
        p = f["properties"]
        if p.get("form") != FORMS.get(p.get("county"), "district"):
            problems.append("%s carries form %r, FORMS says %r"
                            % (p.get("key"), p.get("form"), FORMS.get(p.get("county"), "district")))
        if p.get("key") != "%s-%s" % (p.get("countyFips"), p.get("district")):
            problems.append("%s's key does not match its county and district" % p.get("key"))
    for county, form in FORMS.items():
        if not any(f["properties"]["county"] == county for f in feats):
            problems.append("FORMS names %s, which the map does not carry" % county)
    hampton = [f for f in feats if f["properties"]["county"] == "Hampton"]
    if len(hampton) != 1:
        problems.append("Hampton draws %d features; its whole-county form assumes one"
                        % len(hampton))
    return problems


def write_record(source, simplified_bytes, fp):
    os.makedirs(os.path.dirname(SOURCE_RECORD), exist_ok=True)
    per_county = {}
    for f in source["features"]:
        p = f["properties"]
        per_county.setdefault(county_title(p["County"]), []).append(str(p["District"]).strip())
    record = {
        "source": LAYER,
        "publisher": "South Carolina Revenue and Fiscal Affairs Office",
        "fetched": datetime.date.today().isoformat(),
        "fingerprint": fp,
        "shipped_sha256": hashlib.sha256(simplified_bytes).hexdigest(),
        "districts_per_county": {c: " ".join(sorted(d, key=lambda s: int(s)))
                                 for c, d in sorted(per_county.items())},
    }
    with open(SOURCE_RECORD, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1, sort_keys=True)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its record and the county fabric")
    ap.add_argument("--watch", action="store_true",
                    help="compare the live layer with the recorded fingerprint; exit 1 on a change")
    ap.add_argument("--source", help="build from a saved fetch (this builder's own "
                    "query, saved) instead of the network")
    args = ap.parse_args()

    if args.check:
        with open(OUT_FILE, encoding="utf-8") as f:
            raw = f.read()
        geo = json.loads(raw)
        with open(SOURCE_RECORD, encoding="utf-8") as f:
            record = json.load(f)
        problems = check_shipped(geo)
        if hashlib.sha256(raw.encode()).hexdigest() != record.get("shipped_sha256"):
            problems.append("the shipped file does not hash to what the builder "
                            "recorded — rebuild it rather than editing it by hand")
        tiling, lines = check_tiling(geo["features"])
        problems += tiling
        for line in lines:
            print(line)
        if problems:
            for p in problems:
                print("build-sc-county-council-districts: FAIL: " + p)
            raise SystemExit(1)
        print("build-sc-county-council-districts --check: OK — %d districts in %d "
              "counties, each county covered by its own districts"
              % (len(geo["features"]), EXPECT_COUNTIES))
        return

    import requests  # noqa: PLC0415
    session = requests.Session()

    if args.watch:
        with open(SOURCE_RECORD, encoding="utf-8") as f:
            record = json.load(f)
        live = fetch_fingerprint(session)
        if live != record["fingerprint"]:
            print("build-sc-county-council-districts --watch: THE SOURCE HAS CHANGED. "
                  "Recorded %s (%d districts, fetched %s); live %s (%d districts). A county "
                  "has redistricted or the state re-published its layer: rebuild this "
                  "file, re-read which seat each certified winner holds, and bump the "
                  "service worker's cache name."
                  % (record["fingerprint"]["sha256"][:12], record["fingerprint"]["districts"],
                     record["fetched"], live["sha256"][:12], live["districts"]))
            raise SystemExit(1)
        print("build-sc-county-council-districts --watch: unchanged since %s (%d districts)"
              % (record["fetched"], live["districts"]))
        return

    if args.source:
        with open(args.source, encoding="utf-8") as f:
            source = json.load(f)
    else:
        source = fetch_source(session)
    src = normalise(source)
    if len(src["features"]) != EXPECT_DISTRICTS:
        fail("the layer carries %d districts, expected %d — a county has "
             "redistricted; read it before changing EXPECT_DISTRICTS"
             % (len(src["features"]), EXPECT_DISTRICTS))

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "src.geojson")
        out_tmp = os.path.join(tmp, "out.geojson")
        with open(src_path, "w") as f:
            json.dump(src, f)
        run_mapshaper(src_path, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)
    simplified = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": f["properties"], "geometry": f["geometry"]}
        for f in simplified["features"]]}

    problems = check_shipped(simplified)
    ok, msg = validate(src["features"], simplified["features"])
    if not ok:
        problems.append(msg)
    step = median_source_step_m(src["features"])
    worst, over = check_fidelity(src["features"], simplified["features"])
    if over:
        problems.append("%d district(s) stray past the %.0f m ceiling (worst %.1f m): %s"
                        % (len(over), FIDELITY_CEILING_M, worst, ", ".join(sorted(over)[:8])))
    tiling, lines = check_tiling(simplified["features"])
    problems += tiling
    for line in lines:
        print(line)
    if problems:
        for p in problems:
            print("build-sc-county-council-districts: FAIL: " + p)
        raise SystemExit(1)
    print("fidelity: median source step %.2f m, worst stray %.1f m against a %.0f m "
          "ceiling, 0 of %d districts over" % (step, worst, FIDELITY_CEILING_M,
                                               len(simplified["features"])))
    print("agreement: " + msg)

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        fail("round-trip mismatch before writing")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(compact)
    # The fingerprint is taken from the SAME response the geometry came from,
    # so the record cannot describe a different version of the layer.
    write_record(source, compact.encode(),
                 fingerprint([f["properties"] for f in source["features"]]))
    print("wrote sc/data/app/%s: %d districts in %d counties, %d bytes (dp %s, 6dp)"
          % (os.path.basename(OUT_FILE), len(simplified["features"]), EXPECT_COUNTIES,
             len(compact), SIMPLIFY))


if __name__ == "__main__":
    main()
