#!/usr/bin/env python3
"""Jackson's six council wards — composed from JACKSON COUNTY's precinct layer.

Jackson (the city, in Jackson County) elects one council member from each of six
wards. The city publishes no ward polygon: its site references no GIS host. The
county's does — gis.mijackson.org, whose REST instance is `countygis` and NOT
`arcgis`, so every guessed path 404s — and its Voting/VotingPrecincts layer
carries `MUNICIPALITY` and `WARD` on every precinct. Dissolving the ten City of
Jackson precincts by `WARD` gives the six wards.

WHY THIS ROUTE IS ALLOWED WHEN THE STATE FABRIC IS NOT
-----------------------------------------------------
The operator ruled on 2026-09-21 that the STATE's precinct fabric may only CHECK
a city-published ward boundary, never stand in for one — in Wyoming and Muskegon
the state fabric would have been both source and check. On 2026-09-29 he ruled
the narrower question this city raised: a COUNTY's published map may be the
source for a city's wards. Here the county is the source and the state's own
2026 fabric stays a genuinely independent second witness, so the two-publisher
structure the other cities have is kept.

THE THREE GATES
---------------
1. COMPOSITION. Both publishers assign the city's ten precincts to wards 1-6 as
   1/2/2/2/1/2, and neither may move without a human looking.
2. CURRENCY. The county's dissolve and the state's precincts, compared by point
   classification, must agree on at least 99% of sampled points.
3. TILING. The wards' Census 2020 population is bounded against the Census
   place's, so a dissolve that loses a precinct, or a precinct that strays out
   of the city, fails rather than shipping.

TWO TRAPS IN THE SERVICE
------------------------
It is a 10.6 MAPSERVER, and `f=geojson` on its query answers HTTP 400 "Failed to
execute query". The build asks for Esri JSON and converts rings itself.
An Esri error envelope arrives as HTTP 200 — so an empty answer is read as "the
query or the service moved", never as "no precincts".
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(INSTANCE_ROOT)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.25"
USER_AGENT = "districtry/1.0 (+https://districtry.com/mi/)"

COUNTY_SERVICE = ("https://gis.mijackson.org/countygis/rest/services/"
                  "Voting/VotingPrecincts/MapServer")
COUNTY_LAYER = COUNTY_SERVICE + "/0"
COUNTY_WHERE = "MUNICIPALITY = 'City of Jackson'"

PRECINCTS = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
             "services/2026_Voting_Precincts/FeatureServer/0")
# COUNTYFIPS as well as the name: "Jackson" is a name, and this build is about
# the city in Jackson County (075) and nowhere else.
PRECINCT_WHERE = "Jurisdiction_Name = 'Jackson' AND COUNTYFIPS = '075'"

BLOCKS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
          "tigerWMS_Census2020/MapServer/10/query")
PLACE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
         "tigerWMS_Census2020/MapServer/26/query")
PLACE_GEOID = "2641420"          # Jackson city, MI — NAME asserted at run time

OUT_FILE = "mi-jackson-wards.json"
PRECISION = "0.000001"

EXPECT_FEATURES = 6
EXPECT_WARDS = ("1", "2", "3", "4", "5", "6")
EXPECT_PRECINCTS = {"1": 1, "2": 2, "3": 2, "4": 2, "5": 1, "6": 2}
MIN_PRECINCT_AGREEMENT = 0.99
MAX_POP_DELTA_FRACTION = 0.002
MAX_EDGE_BLOCKS = 60
KEEP_FIELDS = ("WARD",)
DERIVED_FIELDS = ("Ward",)


def fail(msg):
    print("build-mi-jackson-wards: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def curl_json(url, timeout=300):
    out = subprocess.run(["curl", "-sS", "--fail", "--max-time", str(timeout),
                          "-A", USER_AGENT, url],
                         check=True, capture_output=True).stdout
    d = json.loads(out)
    if isinstance(d, dict) and "error" in d:
        raise RuntimeError("%s answered an error envelope: %r" % (url, d["error"]))
    return d


def esri(url, params):
    p = {"f": "geojson", "outSR": 4326, "geometryPrecision": 6}
    p.update(params)
    u = url + ("/query?" if not url.endswith("/query") else "?") + urllib.parse.urlencode(p)
    d = curl_json(u)
    feats = d.get("features") or []
    if not feats:
        raise RuntimeError(
            "%s returned no features — an Esri error envelope arrives as HTTP 200, "
            "so read this as 'the field list or the service moved', not an outage" % url)
    if d.get("exceededTransferLimit"):
        raise RuntimeError("%s hit its transfer cap — needs paging" % url)
    return feats


# --- Esri JSON rings -> GeoJSON ----------------------------------------------
def _signed_area(ring):
    s = 0.0
    for i in range(len(ring) - 1):
        s += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return s / 2.0


def esri_rings_to_geojson(rings):
    """Esri writes outer rings CLOCKWISE and holes counter-clockwise. Each hole
    goes to the smallest outer ring containing its first vertex."""
    outers, holes = [], []
    for r in rings:
        if len(r) < 4:
            continue
        (outers if _signed_area(r) < 0 else holes).append(r)
    if not outers:
        raise RuntimeError("a feature carries no clockwise ring — not Esri JSON as expected")
    polys = [[o] for o in outers]
    for h in holes:
        best = None
        for i, o in enumerate(outers):
            if _in_ring(h[0], o) and (best is None
                                      or abs(_signed_area(o)) < abs(_signed_area(outers[best]))):
                best = i
        if best is None:
            raise RuntimeError("a hole lies in no outer ring of its own feature")
        polys[best].append(h)
    if len(polys) == 1:
        return {"type": "Polygon", "coordinates": polys[0]}
    return {"type": "MultiPolygon", "coordinates": polys}


def county_precincts():
    """The county's MapServer refuses f=geojson (HTTP 400), so read Esri JSON."""
    p = {"where": COUNTY_WHERE, "outFields": "WARD,PRECINCTID,NAME",
         "returnGeometry": "true", "outSR": 4326, "geometryPrecision": 6, "f": "json"}
    d = curl_json(COUNTY_LAYER + "/query?" + urllib.parse.urlencode(p))
    rows = d.get("features") or []
    if not rows:
        raise RuntimeError("the county's precinct query returned nothing — read this as "
                           "'the MUNICIPALITY value or the service moved', not an outage")
    if d.get("exceededTransferLimit"):
        raise RuntimeError("the county's precinct query hit its transfer cap")
    return [{"type": "Feature", "properties": r["attributes"],
             "geometry": esri_rings_to_geojson(r["geometry"]["rings"])} for r in rows]


# --- point-in-polygon, mirroring index.html's even-odd test -------------------
def _in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def in_geometry(pt, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if not poly or not _in_ring(pt, poly[0]):
            continue
        if any(_in_ring(pt, hole) for hole in poly[1:]):
            continue
        return True
    return False


def ward_of(props):
    """The ward number, normalised NUMERICALLY: the county writes WARD "1", the
    state writes WARD "01", and the emitted file writes WARD/Ward "1"."""
    for k in ("WARD", "Ward", "ward"):
        v = props.get(k)
        if v in (None, ""):
            continue
        m = re.search(r"\d+", str(v))
        if m:
            return str(int(m.group(0)))
    return None


def model(features, key=ward_of):
    return [(key(f.get("properties") or {}), f["geometry"])
            for f in features if f.get("geometry")]


def bbox(features):
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for q in c:
                walk(q)
    for f in features:
        walk(f["geometry"]["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def fetch_blocks(box):
    env = "%2C".join("%.5f" % v for v in box)
    url = (BLOCKS + "?where=STATE%3D%2726%27&geometry=" + env +
           "&geometryType=esriGeometryEnvelope&inSR=4326"
           "&spatialRel=esriSpatialRelIntersects"
           "&outFields=POP100,INTPTLAT,INTPTLON&returnGeometry=false"
           "&outSR=4326&f=json&resultRecordCount=100000")
    d = curl_json(url, timeout=600)
    if d.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb capped the block fetch — needs paging")
    rows = []
    for f in d.get("features", []):
        a = f["attributes"]
        try:
            rows.append((float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"] or 0)))
        except (TypeError, ValueError, KeyError):
            continue
    if len(rows) < 500:
        raise RuntimeError("only %d usable blocks over Jackson's envelope — expected "
                           "about a thousand; read this as a capped or moved TIGERweb "
                           "query" % len(rows))
    return rows


def point_agreement(a, b, box, samples=4000, seed=20260929):
    """Fraction of points landing in EITHER model that both put in the same unit."""
    rng = random.Random(seed)
    hit = same = diff = only_a = only_b = 0
    tried = 0
    while hit < samples and tried < samples * 80:
        tried += 1
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        ha = [k for k, g in a if in_geometry(pt, g)]
        hb = [k for k, g in b if in_geometry(pt, g)]
        if not ha and not hb:
            continue
        hit += 1
        if ha and hb:
            if ha[0] == hb[0]:
                same += 1
            else:
                diff += 1
        elif ha:
            only_a += 1
        else:
            only_b += 1
    return {"hit": hit, "same": same, "diff": diff, "only_a": only_a, "only_b": only_b,
            "frac": (same / hit) if hit else 0.0}


def overlaps(m, box, samples=2000, seed=7):
    rng = random.Random(seed)
    n = 0
    for _ in range(samples):
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        if len([k for k, g in m if in_geometry(pt, g)]) > 1:
            n += 1
    return n


def precinct_counts(features):
    counts = {}
    for f in features:
        k = ward_of(f.get("properties") or {})
        counts[k] = counts.get(k, 0) + 1
    return counts


def check_shape(feats, require_derived=False):
    problems = []
    if len(feats) != EXPECT_FEATURES:
        problems.append("%d features, expected %d" % (len(feats), EXPECT_FEATURES))
    seen = tuple(sorted((ward_of(f.get("properties") or {}) or "?") for f in feats))
    if seen != EXPECT_WARDS:
        problems.append("ward numbers are %s, expected %s" % (list(seen), list(EXPECT_WARDS)))
    if require_derived:
        for f in feats:
            if "Ward" not in (f.get("properties") or {}):
                problems.append("a feature carries no bare Ward number — the card headline "
                                "and the hover label both read it")
                break
    return problems


def check_shipped(path):
    if not os.path.exists(path):
        return ["%s is missing" % path]
    with open(path) as f:
        shipped = json.load(f)
    feats = shipped.get("features") or []
    problems = check_shape(feats, require_derived=True)
    keys = {k for f in feats for k in (f.get("properties") or {})}
    stray = keys - set(KEEP_FIELDS) - set(DERIVED_FIELDS)
    if stray:
        problems.append("shipped properties carry unexpected keys: %s" % sorted(stray))
    return problems


def assert_no_stated_terms():
    """The county's service states no terms: copyrightText, serviceDescription
    and description are all empty, measured 2026-09-29. If the county ever adds
    terms, a human reads them BEFORE the next rebuild republishes the geometry."""
    stated = []
    for url in (COUNTY_SERVICE + "?f=json", COUNTY_LAYER + "?f=json"):
        d = curl_json(url, timeout=120)
        for k in ("copyrightText", "serviceDescription", "description"):
            v = re.sub(r"<[^>]+>", " ", d.get(k) or "").strip()
            if v:
                stated.append("%s: %r" % (k, re.sub(r"\s+", " ", v)[:200]))
    if stated:
        fail("the county now STATES TEXT on its precinct service (%s). Jackson shipped "
             "because it stated none; read it and decide before rebuilding."
             % "; ".join(stated))
    print("  terms: the county still states none on this service")


def require_robots():
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    from scraper_common import require_robots_allowed
    for url in (COUNTY_LAYER, PRECINCTS, BLOCKS):
        print("  robots: %s -> %s" % (url.split("/")[2],
                                      require_robots_allowed(url, USER_AGENT,
                                                             label="build-mi-jackson-wards")))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)

    if args.check:
        problems = check_shipped(out_path)
        if problems:
            fail("; ".join(problems))
        print("build-mi-jackson-wards: OK — 6 wards shipped")
        return

    print("reading robots.txt for every host this build fetches…")
    require_robots()
    print("re-checking that the county still states no terms…")
    assert_no_stated_terms()

    # ---- SOURCE: the county's precincts, and their composition -------------
    print("fetching the county's City of Jackson precincts…")
    cprecs = county_precincts()
    counts = precinct_counts(cprecs)
    if counts != EXPECT_PRECINCTS:
        fail("the county assigns %s precincts per ward, expected %s — the county has "
             "re-precincted and the composition must be re-checked"
             % (counts, EXPECT_PRECINCTS))
    print("  county: %d precincts, per ward %s" % (len(cprecs), counts))

    # ---- WITNESS: the state's own 2026 precincts, same composition ----------
    print("fetching the state's 2026 precincts for the witness gates…")
    sprecs = esri(PRECINCTS, {"where": PRECINCT_WHERE, "outFields": "WARD,PRECINCT"})
    scounts = precinct_counts(sprecs)
    if scounts != EXPECT_PRECINCTS:
        fail("the state assigns %s precincts per ward, expected %s — the two publishers "
             "no longer agree on the composition" % (scounts, EXPECT_PRECINCTS))
    print("  state: %d precincts, per ward %s" % (len(sprecs), scounts))

    # ---- DISSOLVE by ward --------------------------------------------------
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    src_path = os.path.join(APP_DATA_DIR, ".jackson-precincts-src.json")
    diss_path = os.path.join(APP_DATA_DIR, ".jackson-wards-dissolved.json")
    with open(src_path, "w") as f:
        json.dump({"type": "FeatureCollection",
                   "features": [{"type": "Feature",
                                 "properties": {"WARD": ward_of(p["properties"])},
                                 "geometry": p["geometry"]} for p in cprecs]}, f)
    try:
        subprocess.run(["npx", "-y", MAPSHAPER, src_path, "-dissolve", "WARD",
                        "-o", "precision=" + PRECISION, "format=geojson", diss_path],
                       check=True)
        with open(diss_path) as f:
            wards = json.load(f)["features"]
    finally:
        for p in (src_path, diss_path):
            if os.path.exists(p):
                os.remove(p)
    problems = check_shape(wards)
    if problems:
        fail("; ".join(problems))

    box = bbox(wards)
    wm = model(wards)
    agree = point_agreement(wm, model(sprecs), box)
    print("  county dissolve vs state precincts: %d/%d (%.3f%%), %d differ, "
          "%d county-only, %d state-only"
          % (agree["same"], agree["hit"], 100 * agree["frac"], agree["diff"],
             agree["only_a"], agree["only_b"]))
    if agree["frac"] < MIN_PRECINCT_AGREEMENT:
        fail("point agreement %.3f%% is below the %.1f%% floor — the two publishers "
             "disagree; find out which before touching this threshold"
             % (100 * agree["frac"], 100 * MIN_PRECINCT_AGREEMENT))
    ov = overlaps(wm, box)
    if ov:
        fail("the dissolved wards overlap at %d of 2000 sampled points" % ov)

    # ---- TILING against the Census place -----------------------------------
    print("fetching Census 2020 blocks…")
    blocks = fetch_blocks(box)
    place = esri(PLACE, {"where": "GEOID = '%s'" % PLACE_GEOID, "outFields": "NAME,GEOID"})
    if not place or str(place[0]["properties"].get("NAME", "")) != "Jackson city":
        fail("place GEOID %s is not Jackson city (got %r)"
             % (PLACE_GEOID, place[0]["properties"].get("NAME") if place else None))
    pgeom = place[0]["geometry"]
    per, total, place_pop, edge = {}, 0, 0, 0
    for lon, lat, pop in blocks:
        pt = (lon, lat)
        inw = next((k for k, g in wm if in_geometry(pt, g)), None)
        inp = in_geometry(pt, pgeom)
        if inw is not None:
            per[inw] = per.get(inw, 0) + pop
            total += pop
        if inp:
            place_pop += pop
        if (inw is not None) != inp:
            edge += 1
    ideal = total / float(EXPECT_FEATURES) if total else 0
    for k in sorted(per):
        print("    Ward %-3s %7d  %+.2f%%" % (k, per[k], 100.0 * (per[k] - ideal) / (ideal or 1)))
    delta = total - place_pop
    print("  wards total %d against the Census place's %d (%+d); %d edge block(s)"
          % (total, place_pop, delta, edge))
    if place_pop and abs(delta) > MAX_POP_DELTA_FRACTION * place_pop:
        fail("the wards' population differs from the city's by %+d (%.3f%%), past the "
             "%.1f%% tolerance — this is meant to be edge digitisation, not a hole"
             % (delta, 100.0 * abs(delta) / place_pop, 100 * MAX_POP_DELTA_FRACTION))
    if edge > MAX_EDGE_BLOCKS:
        fail("%d blocks fall on one side of the ward outline and the other side of the "
             "Census place outline (ceiling %d)" % (edge, MAX_EDGE_BLOCKS))

    # ---- write --------------------------------------------------------------
    # Six wards from ten precincts are small enough to ship unsimplified: the
    # dissolve is written at the fleet's 6-decimal precision and nothing else,
    # so the shipped lines ARE the county's lines.
    out = {"type": "FeatureCollection",
           "features": [{"type": "Feature",
                         "properties": {"WARD": ward_of(f["properties"]),
                                        "Ward": ward_of(f["properties"])},
                         "geometry": f["geometry"]}
                        for f in sorted(wards, key=lambda f: int(ward_of(f["properties"])))]}
    with open(out_path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    problems = check_shipped(out_path)
    if problems:
        fail("; ".join(problems))
    print("build-mi-jackson-wards: wrote %s (6 wards, %d bytes)"
          % (out_path, os.path.getsize(out_path)))


if __name__ == "__main__":
    main()
