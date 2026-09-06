#!/usr/bin/env python3
"""Warren's five council wards — the city's own layer, current, unrestricted.

Warren is Michigan's third-largest city and elects its council by ward. The
boundary comes from the city's own ArcGIS account (`smcdade_City_of_Warren`),
item snippet "Approved 1/10/2023 Updated Labels 4-30-24". Its `licenseInfo` is
empty and the item is shared public, with no sibling item stating terms — which
is the DETROIT case (a public item with no stated restriction), NOT the LANSING
case, where the same publisher states CC BY-NC on the same plan one item away.
That difference is the whole reason Warren ships and Lansing does not.

TWO TRAPS, BOTH IN THE SERVICE RATHER THAN THE DATA
----------------------------------------------------
THE WARD LAYER IS AT INDEX 32, NOT 0. A builder that assumes /0 gets an HTTP 200
carrying no `features` key and dies with a KeyError that reads like an outage.
Read the FeatureServer root and take the layer it lists.

THE ITEM'S EXTENT IS IN PROJECTED COORDINATES, so a catalogue filter that tests
the extent centre against a lat/lon bounding box for Michigan rejects this
service as "not Michigan" — measured while finding it, and it nearly discarded
the right layer. Filter candidates by CONTENT, never by an extent whose CRS you
have not checked.

CURRENCY IS A MEASUREMENT, NOT A DATE
--------------------------------------
The state's own 2026 precinct fabric carries a WARD column assigning Warren's 53
precincts 10/10/11/11/11 across wards 1-5. Dissolved by that column and compared
by point classification, the city's five polygons agree with the state on
2663 of 2666 sampled points (99.887%). Two independent publishers drawing the
same five lines. That agreement and the per-ward precinct counts are both GATES.
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
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.25"

CITY_ORG = "https://services8.arcgis.com/oGUlQVwqEiX7aF12/arcgis/rest/services"
SERVICE_ROOT = CITY_ORG + "/Warren_Council_Wards_2023/FeatureServer"
EXPECT_LAYER_NAME = "Council Wards 2023"   # the root is read; this asserts what we got

PRECINCTS = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
             "services/2026_Voting_Precincts/FeatureServer/0")
PRECINCT_WHERE = "Jurisdiction_Name = 'Warren'"

BLOCKS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
          "tigerWMS_Census2020/MapServer/10/query")
PLACE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
         "tigerWMS_Census2020/MapServer/26/query")
PLACE_GEOID = "2684000"          # Warren city, MI — NAME asserted at run time

OUT_FILE = "mi-warren-wards.json"
SIMPLIFY = "50%"                 # five features; Grand Rapids's tolerance, same shape
PRECISION = "0.000001"

EXPECT_FEATURES = 5
EXPECT_WARDS = ("1", "2", "3", "4", "5")
EXPECT_PRECINCTS = {"1": 10, "2": 10, "3": 11, "4": 11, "5": 11}
MIN_PRECINCT_AGREEMENT = 0.99    # measured 0.99887
MAX_POP_DELTA_FRACTION = 0.002
MAX_EDGE_BLOCKS = 60
KEEP_FIELDS = ("WARD",)
DERIVED_FIELDS = ("Ward",)


def fail(msg):
    print("build-mi-warren-wards: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def esri(url, params):
    p = {"f": "geojson", "outSR": 4326, "geometryPrecision": 6}
    p.update(params)
    u = url + ("/query?" if not url.endswith("/query") else "?") + urllib.parse.urlencode(p)
    out = subprocess.run(["curl", "-sS", "--fail", "--max-time", "300", u],
                         check=True, capture_output=True).stdout
    d = json.loads(out)
    if isinstance(d, dict) and "error" in d:
        raise RuntimeError("%s answered an error envelope: %r" % (url, d["error"]))
    feats = d.get("features") or []
    if not feats:
        raise RuntimeError(
            "%s returned no features — an Esri error envelope arrives as HTTP 200, "
            "so read this as 'the field list or the service moved', not an outage" % url)
    if d.get("exceededTransferLimit"):
        raise RuntimeError("%s hit its transfer cap — needs paging" % url)
    return feats


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
    """The ward number, from whichever field the publisher happened to use.

    Three vocabularies meet here and none is a superset of the others: the CITY
    writes LONGNAME "Ward 1" and SHORTNAME "D1", the STATE's precinct layer
    writes WARD "01", and the file this build EMITS writes WARD/Ward "1".
    Normalise NUMERICALLY — never by stripping characters, which would turn
    "D1" and "01" into different keys and silently classify every point wrong.
    """
    for k in ("LONGNAME", "DISTRICT", "SHORTNAME", "WARD", "Ward", "ward"):
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
    d = json.loads(subprocess.run(["curl", "-sS", "--fail", "--max-time", "600", url],
                                  check=True, capture_output=True).stdout)
    if "error" in d:
        raise RuntimeError("TIGERweb answered an error envelope: %r" % d["error"])
    if d.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb capped the block fetch — needs paging")
    rows = []
    for f in d.get("features", []):
        a = f["attributes"]
        try:
            rows.append((float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"] or 0)))
        except (TypeError, ValueError, KeyError):
            continue
    if len(rows) < 2000:
        raise RuntimeError("only %d usable blocks over Warren's envelope — expected "
                           "thousands; read this as a capped or moved TIGERweb query" % len(rows))
    return rows


def point_agreement(a, b, box, samples=4000, seed=20260905):
    """Fraction of points landing in EITHER model that both put in the same
    unit. Used twice: city-wards vs state-precinct-dissolve (the currency
    gate) and full-precision vs simplified (the fleet's 2,000-point protocol)."""
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


def check_shape(feats, require_derived=False):
    """`require_derived` is False upstream of the build, where the fetched
    features carry only the publisher's own WARD column, and True on the
    shipped file, where the bare `Ward` the card and hover both read must
    exist. Conflating the two is why the first run of this script refused its
    own input."""
    problems = []
    if len(feats) != EXPECT_FEATURES:
        problems.append("%d features, expected %d — Grand Rapids has three wards"
                        % (len(feats), EXPECT_FEATURES))
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
    """Warren ships because its item states NO terms — so notice if that changes.

    This is the mirror of Lansing's gate next door. There, the city states
    CC BY-NC and the build refuses to write; here the item's licenseInfo is
    empty and no sibling item states terms, which is the Detroit case: a public
    item with no stated restriction. If Warren ever adds a licence, that is news
    a human must read BEFORE the next rebuild republishes the geometry under it.
    """
    root = json.loads(subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "120", SERVICE_ROOT + "?f=json"],
        check=True, capture_output=True).stdout)
    iid = root.get("serviceItemId")
    if not iid:
        fail("%s carries no serviceItemId, so its terms cannot be checked" % SERVICE_ROOT)
    item = json.loads(subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "120",
         "https://www.arcgis.com/sharing/rest/content/items/%s?f=json" % iid],
        check=True, capture_output=True).stdout)
    stated = re.sub(r"<[^>]+>", " ", item.get("licenseInfo") or "").strip()
    if stated:
        fail("the city now STATES TERMS on this item (%r). Warren shipped because it "
             "stated none; read the terms and decide before rebuilding — do not "
             "republish the geometry under a licence nobody has read."
             % (re.sub(r"\s+", " ", stated)[:200]))
    print("  terms: the city still states none on this item (shared public)")


def ward_layer_url():
    """The FeatureServer root decides the layer index, never this file.

    Warren's ward layer is at index 32. A hardcoded /0 returns HTTP 200 with no
    `features` key — a KeyError that reads like an outage and is not one."""
    root = json.loads(subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "120", SERVICE_ROOT + "?f=json"],
        check=True, capture_output=True).stdout)
    layers = root.get("layers") or []
    if len(layers) != 1:
        fail("expected exactly one layer on %s, found %s — a human should pick"
             % (SERVICE_ROOT, [(l["id"], l["name"]) for l in layers]))
    if layers[0]["name"] != EXPECT_LAYER_NAME:
        fail("the service's only layer is now %r, expected %r — the city has "
             "republished and this build must be re-checked against it"
             % (layers[0]["name"], EXPECT_LAYER_NAME))
    return "%s/%d" % (SERVICE_ROOT, layers[0]["id"])


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
        print("build-mi-warren-wards: OK — 5 wards shipped")
        return

    print("re-checking that the city still states no terms…")
    assert_no_stated_terms()

    print("reading the city's FeatureServer root for the ward layer index…")
    service = ward_layer_url()
    print("  ward layer: %s" % service)

    wards = esri(service, {"where": "1=1", "outFields": "LONGNAME,DISTRICT"})
    if len(wards) != EXPECT_FEATURES:
        fail("expected %d wards, got %d" % (EXPECT_FEATURES, len(wards)))
    got = tuple(sorted(ward_of(f["properties"]) for f in wards))
    if got != EXPECT_WARDS:
        fail("ward ids are %s, expected %s" % (list(got), list(EXPECT_WARDS)))
    problems = check_shape(wards)
    if problems:
        fail("; ".join(problems))

    box = bbox(wards)
    wm = model(wards)

    # ---- CURRENCY: the state's own 2026 precincts must describe these wards --
    print("fetching the state's 2026 precincts for the currency gate…")
    precs = esri(PRECINCTS, {"where": PRECINCT_WHERE, "outFields": "WARD,PRECINCT"})
    counts = {}
    for f in precs:
        k = ward_of(f["properties"])
        counts[k] = counts.get(k, 0) + 1
    if counts != EXPECT_PRECINCTS:
        fail("the state assigns %s precincts per ward, expected %s — the precinct "
             "fabric has moved and these wards must be re-checked against it"
             % (counts, EXPECT_PRECINCTS))
    agree = point_agreement(wm, model(precs), box)
    print("  city wards vs state precinct dissolve: %d/%d (%.3f%%)"
          % (agree["same"], agree["hit"], 100 * agree["frac"]))
    if agree["frac"] < MIN_PRECINCT_AGREEMENT:
        fail("point agreement %.3f%% is below the %.1f%% floor — find the city's adopted "
             "plan before touching this threshold; the threshold is not the thing to move"
             % (100 * agree["frac"], 100 * MIN_PRECINCT_AGREEMENT))

    # ---- the wards must tile the city, bounded rather than asserted exact ----
    print("fetching Census 2020 blocks…")
    blocks = fetch_blocks(box)
    place = esri(PLACE, {"where": "GEOID = '%s'" % PLACE_GEOID, "outFields": "NAME,GEOID"})
    if not place or "warren" not in str(place[0]["properties"].get("NAME", "")).lower():
        fail("place GEOID %s is not Warren (got %r) — the Census place id is wrong"
             % (PLACE_GEOID, place[0]["properties"].get("NAME") if place else None))
    pgeom = place[0]["geometry"]

    # fetch_blocks yields (lon, lat, pop) triples — TIGERweb's own interior
    # points, not polygon centroids, so a block never lands outside itself.
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

    # ---- write, then the fleet's 2,000-point simplification protocol ---------
    src = {"type": "FeatureCollection",
           "features": [{"type": "Feature",
                         "properties": {"WARD": ward_of(f["properties"]),
                                        "Ward": ward_of(f["properties"])},
                         "geometry": f["geometry"]} for f in wards]}
    tmp = os.path.join(APP_DATA_DIR, ".warren-wards-src.json")
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(src, f)
    subprocess.run(["npx", "-y", MAPSHAPER, tmp,
                    "-simplify", "visvalingam", "keep-shapes", SIMPLIFY,
                    "-o", "precision=" + PRECISION, "format=geojson", out_path],
                   check=True)
    os.remove(tmp)

    with open(out_path) as f:
        built = json.load(f)
    bm = model(built["features"])
    proto = point_agreement(model(src["features"]), bm, box, samples=2000, seed=2026)
    src_ov = overlaps(model(src["features"]), box)
    if overlaps(bm, box) > src_ov:
        fail("simplification ADDED overlaps")
    if proto["frac"] < 0.995:
        fail("point-in-ward agreement only %.2f%% (need >= 99.5%%)" % (100 * proto["frac"]))
    print("  simplification: %d/%d (%.2f%%) agreement, %d source overlap(s), none added"
          % (proto["same"], proto["hit"], 100 * proto["frac"], src_ov))

    problems = check_shipped(out_path)
    if problems:
        fail("; ".join(problems))
    print("build-mi-warren-wards: wrote %s (5 wards, %d bytes)"
          % (out_path, os.path.getsize(out_path)))


if __name__ == "__main__":
    main()
