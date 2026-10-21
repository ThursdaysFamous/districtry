#!/usr/bin/env python3
"""
Build Arkansas's townships — every county's townships, one file — from the
state's own statewide layer, so the app fetches them same-origin (cache-first)
instead of reading a live service.

WHY THE STATE'S MAP AND NOT THE CENSUS'S. The fleet's township layer is the
Census's county subdivisions, read live from TIGERweb, everywhere else
(North Carolina's is the model). In Arkansas the Census's map is out of date.
A county court divides its county into townships and alters their lines
(Arkansas Code 14-14-401; Clowers v. Edwards, 2020 Ark. 367, upheld Washington
County's 2013 order cutting fifteen townships to three), and the state's
mapping office publishes the current lines as one layer, TOWNSHIP_POLITICAL_
DIVISION (gis.arkansas.gov, FEATURESERVICES/Boundaries FeatureServer layer
57). Measured 2026-10-15: the state's layer has 820 townships in 75 counties
and TIGERweb's has 1,051, and the two disagree about HOW MANY townships a
county has in 27 of the 75. Where the disagreement was checked the state is
right: TIGERweb still draws 38 townships in Washington County, where the
court's order left 3 and the state's layer has 3; and it draws nine numbered
districts in Scott County, where the county elects constables from named
townships (Lamb, Mill Creek, Hickman) that are among the state's 25. So the
state's lines ship and the Census's do not.

A TOWNSHIP GOVERNS NOBODY, AND THE CARD SAYS SO. It has no government of its
own (the Census records every Arkansas township as a nonfunctioning legal
entity, FUNCSTAT N), but its voters elect a constable for a two-year term
(Arkansas Constitution, article 7, section 47). No source naming constables
by township has been read, so the card names nobody and says why.

THE NAMES ARE THE STATE'S, WITH THE WORD TOWNSHIP ADDED. The layer writes a
name in four shapes, measured 2026-10-15: a plain name ("Washington"); a name
and a number ("Mooney - 15", four names written without the dash, "Spadra 2",
"Carson 5", "Cane Creek 4 " and "Monroe  16", and nine in Clay County joining
two names with a hyphen, "Payne-Swain - 10"); a bare number in the counties
that number their townships ("1", in 19 counties); and "Township 1" or
"Township # 1" (Monroe and Cleburne). The number cannot be dropped: three
counties have two or more townships sharing a name and differing only by it
(Lawrence's Reeds Creek 18 and 19, Columbia's Magnolia 2 and 3, Johnson's
Spadra 1 to 4). So a name becomes "Washington Township", "Mooney Township
15" or "Township 1", and `township_title` refuses a shape it does not know. Two numbers are repeated
within a county (Phillips has a 16 named Bush and another named Spring
Creek, Cleveland a 14 named Rison and another named Smith); they ship as the
state publishes them, since the names tell them apart.

PACING. gis.arkansas.gov publishes no robots.txt (the address redirects to a
web page, which permits every path), but the state's open-data portal on the
same office's other host, geodata.gis.arkansas.gov, asks for 60 seconds
between requests, and this builder honours that here too. The layer answers
200 features a request, so a build is five requests and four minutes.

Everything else is the method this instance's quorum court builder uses:
Douglas-Peucker simplification in metres under a 25 m fidelity ceiling, the
2,000-point agreement gate, ONE mapshaper run so an edge two townships share
is simplified once, and every county's townships held to cover that county
as the Census draws it (state-counties.json).

`--watch` reads the live layer's attributes and areas (no geometry) and
compares them with the fingerprint recorded when the shipped file was built
(data/source/ar-townships.source.json). A difference means a county court
changed its townships or the state re-published its layer.

`--check` is offline: the shipped file's townships, counties, names and
tiling, held to the recorded fingerprint and to state-counties.json.

Usage:
    python3 ar/scripts/build_ar_townships.py           # fetch, build, write
    python3 ar/scripts/build_ar_townships.py --check   # offline gate
    python3 ar/scripts/build_ar_townships.py --watch   # has the source moved?
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE), "scripts"))

from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

APP_DATA = os.path.join(INSTANCE, "data", "app")
OUT_FILE = os.path.join(APP_DATA, "ar-townships.json")
COUNTIES_FILE = os.path.join(APP_DATA, "state-counties.json")
SOURCE_RECORD = os.path.join(INSTANCE, "data", "source", "ar-townships.source.json")

LAYER = ("https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/"
         "Boundaries/FeatureServer/57")
USER_AGENT = "districtry/1.0 (+https://districtry.com/ar/)"
MAPSHAPER = "mapshaper@0.6.102"  # pinned, as in build_legislative_boundaries.py
PRECISION = "0.000001"
SIMPLIFY = "interval=20"
PAGE = 200            # the layer's maxRecordCount
PACE_SECONDS = 60     # the state portal's stated Crawl-delay, honoured here too

EXPECT_TOWNSHIPS = 820
EXPECT_COUNTIES = 75

# 25 m, PINNED, the ceiling this instance's legislative and quorum court
# builders hold their lines to. A ceiling recomputed from the source each run
# could never fail; the measured stray prints beside it on every build.
FIDELITY_CEILING_M = 25.0

# Points sampled inside each Census county for the tiling gate, and how many
# may land in no township or in another county's township (two publishers'
# county lines disagreeing). Set from the first build's measurement, just
# outside it, so a county whose map is missing a township, or filed under the
# wrong county, fails widely.
TILING_SAMPLES = 400
TILING_MIN_SAME = 0.97
TILING_MAX_OTHER = 0.02

STATE_BBOX = {"minLng": -94.8, "minLat": 32.85, "maxLng": -89.45, "maxLat": 36.65}


def fail(msg):
    raise SystemExit("build-ar-townships: FATAL: %s" % msg)


def county_title(raw):
    """The state writes "Saint Francis" where the Census writes "St. Francis".
    The app keys on FIPS, so the name is only a label, and the Census's
    spelling is the one every other card prints."""
    t = " ".join(raw.split()).title()
    return {"Saint Francis": "St. Francis", "St Francis": "St. Francis"}.get(t, t)


_BARE = re.compile(r"(?:Township\s*#?\s*)?(\d+)", re.I)
_NAMED_NUMBER = re.compile(r"([A-Za-z][A-Za-z .'-]*?[A-Za-z.])\s*(?:-\s*)?(\d+)")
_NAMED = re.compile(r"[A-Za-z][A-Za-z .'-]*[A-Za-z.]")


def township_title(raw):
    """The state's name as a reader-facing title, in the four shapes the
    module docstring lists; anything else stops the build."""
    n = " ".join((raw or "").split())
    m = _BARE.fullmatch(n)
    if m:
        return "Township %d" % int(m.group(1))
    m = _NAMED_NUMBER.fullmatch(n)
    if m:
        return "%s Township %d" % (m.group(1).strip(), int(m.group(2)))
    if _NAMED.fullmatch(n):
        return n + " Township"
    fail("a township name in a shape this builder does not know: %r" % raw)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------- fetch ----------
def _get_json(session, url):
    resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
    resp.raise_for_status()
    doc = resp.json()
    if "error" in doc:
        fail("the layer answered an error envelope: %r" % doc["error"])
    return doc


def _paged(session, base_query, collect):
    """Page through the layer 200 features at a time, 60 s apart, ordered by
    objectid so a page boundary cannot move under us."""
    out = []
    offset = 0
    while True:
        url = "%s/query?%s&orderByFields=objectid&resultOffset=%d&resultRecordCount=%d" % (
            LAYER, base_query, offset, PAGE)
        if offset == 0:
            require_robots_once(url, USER_AGENT, label="ar-townships")
        else:
            time.sleep(PACE_SECONDS)
        doc = _get_json(session, url)
        feats = doc.get("features") or []
        out.extend(collect(feats))
        more = doc.get("exceededTransferLimit") or (doc.get("properties") or {}).get(
            "exceededTransferLimit")
        if not feats or (not more and len(feats) < PAGE):
            break
        offset += len(feats)
        if offset > 5 * EXPECT_TOWNSHIPS:
            fail("paging ran past %d features — the layer is not what this builder "
                 "expects" % offset)
    return out


FIELDS = "objectid,county,statefips,countyfips,name,Shape__Area"


def fetch_source(session):
    q = "where=1%3D1&outFields=" + FIELDS + "&outSR=4326&geometryPrecision=6&f=geojson"
    feats = _paged(session, q, lambda fs: fs)
    return {"type": "FeatureCollection", "features": feats}


def fetch_fingerprint(session):
    """The live layer's attributes and areas, no geometry."""
    q = "where=1%3D1&outFields=" + FIELDS + "&returnGeometry=false&f=json"
    rows = _paged(session, q, lambda fs: [f["attributes"] for f in fs])
    return fingerprint(rows)


def fingerprint(rows):
    """A stable digest of what a county court's order changes: which
    townships each county has, by name, and each one's area to the square
    metre (the layer's own projected area). Sorted, so record order cannot
    move it."""
    lines = sorted("%s|%s|%d" % (
        str(r.get("countyfips")).strip(), " ".join(str(r.get("name")).split()),
        round(float(r.get("Shape__Area") or 0)))
        for r in rows)
    return {"townships": len(lines),
            "sha256": hashlib.sha256("\n".join(lines).encode()).hexdigest()}


# ---------- normalise ----------
def normalise(source):
    feats = []
    seen = set()
    for f in source.get("features") or []:
        p = f.get("properties") or {}
        county = county_title(p.get("county") or "")
        fips3 = str(p.get("countyfips") or "").strip()
        if not county or len(fips3) != 3 or not fips3.isdigit():
            fail("a feature with an unreadable county: %r" % p)
        fips = "05" + fips3
        name = township_title(p.get("name"))
        key = "%s-%s" % (fips, slug(name))
        if key in seen:
            fail("township %s appears twice" % key)
        seen.add(key)
        if not f.get("geometry"):
            fail("township %s has no geometry" % key)
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "key": key, "name": name, "county": county, "countyFips": fips}})
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
    """Worst distance from a SOURCE vertex to its own township as drawn — the
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


def validate(source_features, result_features, samples=2000, seed=2024):
    """The fleet's 2,000 uniform-random-point protocol over the state
    envelope: the simplified file must answer as the source does at >= 99.5%
    of points, and no point may land in two townships."""
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
        return False, "topology broken: %d/%d points fell in >1 township" % (overlaps, samples)
    if pct < 99.5:
        return False, "point-in-township agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (agree, samples, pct)


# ---------- the county tiling gate ----------
def check_tiling(features, seed=2026):
    """Points sampled inside each Census county must land in a township of
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
        problems.append("the township map's counties %s do not match the Census "
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
                problems.append("%s: a point at %.5f,%.5f is in %d townships: %s"
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
                            "of its own townships (%d in another county's, %d in none)"
                            % (c["properties"]["NAME"], same, n, other, none))
        if frac_other > TILING_MAX_OTHER:
            problems.append("%s: %d of %d points inside the county land in another "
                            "county's township" % (c["properties"]["NAME"], other, n))
    worst.sort()
    lines = ["tiling: lowest own-township share %.4f (%s: %d same, %d other, %d none of %d)"
             % (worst[0][0], worst[0][1], worst[0][2], worst[0][3], worst[0][4], worst[0][5])]
    most_other = max(worst, key=lambda w: w[3])
    most_none = max(worst, key=lambda w: w[4])
    lines.append("tiling: most points in another county's township: %s %d; most in "
                 "none: %s %d" % (most_other[1], most_other[3], most_none[1], most_none[4]))
    lines.append("tiling: %d counties, %d sample points each; floor %.2f own, ceiling %.2f other"
                 % (len(worst), TILING_SAMPLES, TILING_MIN_SAME, TILING_MAX_OTHER))
    return problems, lines


def townships_per_county(features):
    out = {}
    for f in features:
        p = f["properties"]
        out[p["countyFips"]] = out.get(p["countyFips"], 0) + 1
    return out


def check_shipped(geo):
    problems = []
    feats = geo.get("features") or []
    if len(feats) != EXPECT_TOWNSHIPS:
        problems.append("%d townships, expected %d" % (len(feats), EXPECT_TOWNSHIPS))
    keys = [f["properties"].get("key") for f in feats]
    if len(set(keys)) != len(keys):
        problems.append("a township key appears twice")
    for f in feats:
        p = f["properties"]
        name = p.get("name") or ""
        if not (name.startswith("Township ") or " Township" in name):
            problems.append("%s's name %r does not say it is a township" % (p.get("key"), name))
        if p.get("key") != "%s-%s" % (p.get("countyFips"), slug(name)):
            problems.append("%s's key does not match its county and name" % p.get("key"))
    per = townships_per_county(feats)
    if len(per) != EXPECT_COUNTIES:
        problems.append("%d counties, expected %d" % (len(per), EXPECT_COUNTIES))
    return problems


def write_record(source, simplified_bytes, fp):
    os.makedirs(os.path.dirname(SOURCE_RECORD), exist_ok=True)
    per_county = {}
    for f in source["features"]:
        p = f["properties"]
        c = "05" + str(p["countyfips"]).strip()
        per_county[c] = per_county.get(c, 0) + 1
    record = {
        "source": LAYER,
        "publisher": "Arkansas GIS Office (TOWNSHIP_POLITICAL_DIVISION)",
        "fetched": datetime.date.today().isoformat(),
        "fingerprint": fp,
        "shipped_sha256": hashlib.sha256(simplified_bytes).hexdigest(),
        "townships_per_county": dict(sorted(per_county.items())),
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
                    "paged query, saved) instead of the network")
    ap.add_argument("--save-source", help="also write the raw paged fetch here")
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
        if townships_per_county(geo["features"]) != record.get("townships_per_county"):
            problems.append("the shipped file's townships per county differ from the record")
        tiling, lines = check_tiling(geo["features"])
        problems += tiling
        for line in lines:
            print(line)
        if problems:
            for p in problems:
                print("build-ar-townships: FAIL: " + p)
            raise SystemExit(1)
        print("build-ar-townships --check: OK — %d townships in %d counties, each "
              "county covered by its own" % (len(geo["features"]), EXPECT_COUNTIES))
        return

    import requests  # noqa: PLC0415
    session = requests.Session()

    if args.watch:
        with open(SOURCE_RECORD, encoding="utf-8") as f:
            record = json.load(f)
        live = fetch_fingerprint(session)
        if live != record["fingerprint"]:
            print("build-ar-townships --watch: THE SOURCE HAS CHANGED. Recorded %s "
                  "(%d townships, fetched %s); live %s (%d townships). A county court "
                  "has changed its townships or the state re-published its layer: "
                  "rebuild this file and bump the service worker's cache name."
                  % (record["fingerprint"]["sha256"][:12], record["fingerprint"]["townships"],
                     record["fetched"], live["sha256"][:12], live["townships"]))
            raise SystemExit(1)
        print("build-ar-townships --watch: unchanged since %s (%d townships)"
              % (record["fetched"], live["townships"]))
        return

    if args.source:
        with open(args.source, encoding="utf-8") as f:
            source = json.load(f)
    else:
        source = fetch_source(session)
        if args.save_source:
            with open(args.save_source, "w", encoding="utf-8") as f:
                json.dump(source, f)
    src = normalise(source)
    if len(src["features"]) != EXPECT_TOWNSHIPS:
        fail("the layer carries %d townships, expected %d — a county court has "
             "changed its townships; read it before changing EXPECT_TOWNSHIPS"
             % (len(src["features"]), EXPECT_TOWNSHIPS))

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
        problems.append("%d township(s) stray past the %.0f m ceiling (worst %.1f m): %s"
                        % (len(over), FIDELITY_CEILING_M, worst, ", ".join(sorted(over)[:8])))
    tiling, lines = check_tiling(simplified["features"])
    problems += tiling
    for line in lines:
        print(line)
    print("fidelity: median source step %.2f m, worst stray %.1f m against a %.0f m "
          "ceiling, %d of %d townships over" % (step, worst, FIDELITY_CEILING_M,
                                               len(over), len(simplified["features"])))
    print("agreement: " + msg)
    if problems:
        for p in problems:
            print("build-ar-townships: FAIL: " + p)
        raise SystemExit(1)

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        fail("round-trip mismatch before writing")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(compact)
    # The fingerprint is taken from the SAME response the geometry came from,
    # so the record cannot describe a different version of the layer.
    write_record(source, compact.encode(),
                 fingerprint([f["properties"] for f in source["features"]]))
    print("wrote ar/data/app/%s: %d townships in %d counties, %d bytes (dp %s, 6dp)"
          % (os.path.basename(OUT_FILE), len(simplified["features"]), EXPECT_COUNTIES,
             len(compact), SIMPLIFY))


if __name__ == "__main__":
    main()
