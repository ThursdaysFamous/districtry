#!/usr/bin/env python3
"""
Build New York's statewide municipality layers into pre-simplified files
under data/app/, from the state's own NYS_Civil_Boundaries service, so the
app fetches same-origin geometry instead of a live multi-megabyte polygon
layer on first toggle.

Two outputs, one script: data/app/ny-cities-towns.json (cities and towns,
the layer that tiles the whole state) and data/app/ny-villages.json
(villages, which nest inside towns and never tile the state on their own).

SOURCE. Both come off one ArcGIS FeatureServer, measured 2026-09-18:
  https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Civil_Boundaries/FeatureServer
Layer 6 "Cities_Towns" (995 features: 62 cities + 933 towns) and layer 7
"Villages" (532 features). robots.txt on gisservices.its.ny.gov answers
HTTP 404, read as allow-all by scripts/robots_policy.py. Both counts are
confirmed by a plain returnCountOnly query the same day; both stay exactly
this many features until a village is annexed, dissolved or a town or city
line changes, which is why the guard below is an exact equality rather than
a floor.

CORRECTION TO THE EXPANSION PLAN: docs/NY_EXPANSION_PLAN.md's PR 2 section
says Cities_Towns needs a second page because maxRecordCount is 1000.
Measured 2026-09-18: querying layer 6 with outFields=* at outSR=4326,
geometryPrecision=6 returns all 995 features in ONE request (20,577,821
bytes), and layer 7 the same way returns all 532 in one request (3,702,025
bytes). Both counts sit under the 1000-row cap, so this builder fetches each
layer with a single unpaged query rather than a resultOffset loop.

TRAP, measured and load-bearing: villages are MANY-TO-MANY with towns. Of
532 villages, 76 carry a comma-joined multi-town TOWN value as one string
("Ballston Spa" is "Ballston, Milton"; "Brockport" is "Clarkson, Sweden"),
and 8 of those also span two COUNTIES (Almond, Attica, Dolgeville,
Earlville, Deposit, Gowanda, Saranac Lake, Rushville). TOWN and COUNTY ship
RAW, exactly as the service prints them, comma-joined string and all. A
reader of this file must split that string itself and must never treat TOWN
or COUNTY as a single join key back to a town or county record -- doing so
silently drops a village's second town or second county. Villages are
maintained, not static: of all 532 rows, only two carry a DATEMOD since
2025-01-01 ('Ateres', Sullivan, 2025-05-02; 'Rushville', 2026-01-13).

TRAP, measured: New York City is ONE row in the Cities_Towns layer
(NAME "New York", MUNI_TYPE "city", COUNTY "New York, Bronx, Kings,
Richmond, Queens", POP2020 8,804,190). Inside the five boroughs this layer
can only ever answer "New York" -- the borough layer (data/app/
borough-boundaries.json) is the city tier's answer to which of the five the
point is actually in. This is the same comma-joined-COUNTY shape as the
eight multi-county villages, on the one row a reader is likeliest to hit.

FIELDS SHIPPED. A card needs identity and nothing else at this layer, so
everything but NAME, MUNI_TYPE, COUNTY (and, for villages, TOWN) is dropped
on the way in -- POP1990..POP2020, GNIS_ID, FIPS_CODE, SWIS, DOS_LL,
DOSLL_DATE, MAP_SYMBOL, CALC_SQ_MI and DATEMOD never reach data/app/. The
Villages layer carries no MUNI_TYPE field at all (every row in it is a
village by construction), so this builder writes MUNI_TYPE: "village" onto
every village feature itself, a SYNTHESIZED field with no source column
behind it, so a card reading MUNI_TYPE never has to know which file it is
looking at. That is the one field this builder invents; every other field
is copied verbatim from the service.

SIMPLIFICATION. mapshaper via npx, PINNED (the fleet convention), Visvalingam,
keep-shapes, topology-aware -- the same tool and flags every sibling boundary
builder uses (mi/scripts/build_state_counties.py, ny/scripts/
build_embedded_boundaries.py). This builder tries several retain
percentages (RETAIN_CANDIDATES below) against the SAME full-precision fetch,
because 20.6 MB and 3.7 MB of raw GeoJSON are two orders of magnitude past
anything this instance ships today (its whole data/app/ was 1.58 MB on
2026-09-18) and the right retain percentage is a byte-versus-fidelity
tradeoff worth seeing measured rather than guessed once. For each candidate
it classifies the fleet's 2,000-point protocol against the UNSIMPLIFIED
fetch and against that candidate's simplified output, over New York's own
state bbox, and REFUSES to write anything for a layer where no candidate
clears 99.5% agreement with zero points landing in more than one simplified
feature. Among the candidates that clear the gate it writes the smallest
(most compressed). Every candidate's numbers print to stderr, passing or
not, so a byte budget can be picked without re-running the fetch.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ny/scripts/build_ny_municipalities.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)

SERVICE = "https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Civil_Boundaries/FeatureServer"
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m -- the precision the app requests live

# The state envelope the classification check samples over -- New York's own
# published extent (docs/NY_EXPANSION_PLAN.md, measured 2026-09-18), not this
# instance's city-sized permalink_gate, because these layers answer statewide.
STATE_BBOX = {"minLng": -79.7626, "minLat": 40.4766, "maxLng": -71.7775, "maxLat": 45.0159}

# Tried in this order (most detail first); the smallest one that still
# clears the classification gate is what ships. The plan's own floor: try at
# least these three.
RETAIN_CANDIDATES = ["12%", "8%", "5%"]

VALIDATION_KEY = "_vk"  # a synthesized, per-feature-unique key added before
                         # simplification and stripped before writing -- see
                         # the NAME-collision note in fetch_layer() below.

LAYERS = [
    {
        "id": "cities_towns",
        "layer": 6,
        "service_layer_name": "Cities_Towns",
        "fields": ["NAME", "MUNI_TYPE", "COUNTY"],
        "expected_count": 995,
        "out_file": "ny-cities-towns.json",
        "synth_muni_type": None,
        # Cities and towns TILE the state -- every point in New York is in
        # exactly one, so a point landing in zero is itself a disagreement
        # against the unsimplified fetch (never a case of "no answer here").
    },
    {
        "id": "villages",
        "layer": 7,
        "service_layer_name": "Villages",
        "fields": ["NAME", "TOWN", "COUNTY"],
        "expected_count": 532,
        "out_file": "ny-villages.json",
        "synth_muni_type": "village",
        # Villages nest INSIDE towns and do not tile the state -- most
        # sampled points correctly land in zero villages on both sides, and
        # that is agreement, not a gap in the test.
    },
]


def fetch_layer(layer_num, fields, expected_count):
    """Fetch one NYS_Civil_Boundaries layer as GeoJSON in a single unpaged
    query (both layers' counts sit under the service's maxRecordCount of
    1000). Uses curl so it works through an HTTPS proxy (as in the Claude
    Code sandbox). Adds a synthesized VALIDATION_KEY to every feature before
    returning, because NAME repeats within Cities_Towns (37 names cover 2
    features apiece, e.g. a City of Rochester and a Town of Rochester) and a
    validation key must be unique per feature, not merely descriptive."""
    url = (
        SERVICE + "/" + str(layer_num) + "/query"
        "?where=1%3D1"
        "&outFields=" + ",".join(fields) +
        "&outSR=4326&geometryPrecision=6&f=geojson"
    )
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300", url],
        check=True, capture_output=True,
    ).stdout
    geo = json.loads(out)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("NYS_Civil_Boundaries layer %d returned no features" % layer_num)
    if geo.get("exceededTransferLimit") or geo.get("properties", {}).get("exceededTransferLimit"):
        raise RuntimeError(
            "NYS_Civil_Boundaries layer %d hit the transfer cap -- needs paging "
            "(this builder assumes one unpaged query covers it)" % layer_num
        )
    if len(feats) != expected_count:
        raise RuntimeError(
            "NYS_Civil_Boundaries layer %d returned %d features, expected exactly %d "
            "(measured 2026-09-18) -- refusing to build on an unexpected count"
            % (layer_num, len(feats), expected_count)
        )
    for i, f in enumerate(feats):
        if f.get("geometry") is None:
            raise RuntimeError(
                "NYS_Civil_Boundaries layer %d: feature %r has null geometry"
                % (layer_num, f.get("properties", {}).get("NAME"))
            )
        f["properties"][VALIDATION_KEY] = str(i)
    return geo


def run_mapshaper(source_path, simplify, out_path):
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-simplify", "visvalingam", "keep-shapes", simplify,
            "-o", "precision=" + PRECISION, "format=geojson", out_path,
        ],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon mirroring index.html's even-odd test (so validation
#     agrees with what the app computes at runtime) -- fleet-standard copy ---
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
    return [(f["properties"][key_prop], f["geometry"], _bbox(f["geometry"])) for f in features]


def _features_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def classify(source_features, candidate_features, samples=2000, seed=2024):
    """The fleet's 2,000-uniform-random-point protocol, over New York's own
    state bbox rather than a per-layer envelope, because these are statewide
    layers. Returns (agreement_pct, overlap_count, agree, samples)."""
    src = _model(source_features, VALIDATION_KEY)
    new = _model(candidate_features, VALIDATION_KEY)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = _features_at(new, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = _features_at(src, pt)
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    return pct, overlaps, agree, samples


def strip_for_shipping(features, synth_muni_type):
    """Drop VALIDATION_KEY and every field this builder does not ship, and
    write the one synthesized field (villages' MUNI_TYPE) if this layer
    carries no such column of its own."""
    out = []
    for f in features:
        props = dict(f["properties"])
        props.pop(VALIDATION_KEY, None)
        if synth_muni_type is not None:
            props["MUNI_TYPE"] = synth_muni_type
        out.append({"type": "Feature", "properties": props, "geometry": f["geometry"]})
    return {"type": "FeatureCollection", "features": out}


def build_one(layer_cfg):
    layer_num = layer_cfg["layer"]
    label = "%s (layer %d %s)" % (layer_cfg["id"], layer_num, layer_cfg["service_layer_name"])

    source_geo = fetch_layer(layer_num, layer_cfg["fields"], layer_cfg["expected_count"])
    source_features = source_geo["features"]
    print("%s: fetched %d features" % (label, len(source_features)), file=sys.stderr)

    results = []
    chosen = None

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, layer_cfg["id"] + "-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source_geo, f)

        for retain in RETAIN_CANDIDATES:
            out_tmp = os.path.join(tmp, layer_cfg["id"] + "-" + retain.rstrip("%") + ".geojson")
            run_mapshaper(src_path, retain, out_tmp)
            with open(out_tmp) as f:
                simplified = json.load(f)
            cand_features = simplified["features"]

            count_ok = len(cand_features) == layer_cfg["expected_count"]
            pct, overlaps, agree, samples = classify(source_features, cand_features)

            shipped = strip_for_shipping(cand_features, layer_cfg["synth_muni_type"])
            compact = json.dumps(shipped, separators=(",", ":"))
            n_bytes = len(compact)

            passed = count_ok and overlaps == 0 and pct >= 99.5
            results.append({
                "retain": retain,
                "bytes": n_bytes,
                "count_ok": count_ok,
                "feature_count": len(cand_features),
                "agreement_pct": pct,
                "agree": agree,
                "samples": samples,
                "overlaps": overlaps,
                "passed": passed,
                "compact": compact,
                "shipped": shipped,
            })

            print(
                "  retain %-4s -> %9d bytes; features %d/%d; "
                "agreement %6.2f%% (%d/%d); overlaps %d -> %s"
                % (retain, n_bytes, len(cand_features), layer_cfg["expected_count"],
                   pct, agree, samples, overlaps, "PASS" if passed else "FAIL"),
                file=sys.stderr,
            )

    passing = [r for r in results if r["passed"]]
    if not passing:
        raise RuntimeError(
            "%s: no retain candidate in %r cleared the 99.5%% classification "
            "gate with zero overlaps -- refusing to write. Results: %r"
            % (label, RETAIN_CANDIDATES, [(r["retain"], r["agreement_pct"], r["overlaps"]) for r in results])
        )
    chosen = min(passing, key=lambda r: r["bytes"])

    # Round-trip: re-parse what is about to be written and confirm it
    # matches the in-memory object, so a serialization bug can't ship silently.
    if json.loads(chosen["compact"]) != chosen["shipped"]:
        raise RuntimeError("%s round-trip mismatch before writing" % label)

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, layer_cfg["out_file"])
    with open(out_path, "w") as f:
        f.write(chosen["compact"])

    print(
        "%s -> data/app/%s: chosen retain %s, %d bytes, %.2f%% agreement "
        "(%d/%d), 0 overlaps"
        % (label, layer_cfg["out_file"], chosen["retain"], chosen["bytes"],
           chosen["agreement_pct"], chosen["agree"], chosen["samples"]),
        file=sys.stderr,
    )
    return results, chosen


def main():
    for layer_cfg in LAYERS:
        build_one(layer_cfg)


if __name__ == "__main__":
    main()
