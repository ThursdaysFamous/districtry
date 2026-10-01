#!/usr/bin/env python3
"""
Build data/app/ia-precincts.json — every one of Iowa's 1,660 election
precincts, as a polygon FeatureCollection for the identity-only precinct
card.

SOURCE: "State of Iowa Precinct Boundaries" (AGOL item
d394edea208c4003ac1d6bd1ec78532f), owner Jodi.Flory@legis.iowa.gov_iowa —
the same Iowa Legislative Services Agency org and owner as
county-supervisor's own aggregate, vintage 2024-01-30 (same edit batch).
licenseInfo null. Verified live 2026-08-28: 1,660 features, native WGS84.

A TRIPLE-DUPLICATE-SERVICE TRAP, measured live: two decoys share
deceptively similar names —

  * `IaPrecincts` on the SEPARATE `LSAFiscal` org (services2.arcgis.com/
    KhKjlwEBlPJd6v51) — 1,651 features, titled "2022 Precincts", last
    edited 2022-08-30 (stale).
  * A bare `Precincts` service on the SAME org as the real one — 1,689
    features, no edit metadata, unexplained.

The item id is recorded above specifically so a future refresh can never
silently retarget one of these by a name-based search; the query below
still hits the layer by its own URL, pinned as a literal.

POLLING-PLACE FIELDS ARE DELIBERATELY NEVER FETCHED. The live layer
carries PollingPlace / PollingPlaceAddr / PPID in-band, but no dated,
per-election display contract exists yet for polling data (see
docs/IA_EXPANSION_PLAN.md's phase 4) — shipping "current" polling
information off a vintage-2024 item would be exactly the honesty failure
the fleet's display-contract discipline exists to prevent (Wisconsin's own
`build_wi_polling_places.py` states the five-condition contract this
concept needs before it can ship). This builder does not request those
columns at all — the strongest form of "never render this," since a field
that was never fetched cannot be added to a card by a future edit that
merely forgets the rule.

PAGINATION IS REQUIRED: maxRecordCount is 1,000, below the layer's own
1,660-feature count.

A NAME GAP, measured across the full 1,660 records: PctNameOfficial is
empty on exactly 2 of them (Warren County precincts 91-1 and 91-31), while
the all-caps Label field is populated on all 1,660 with no exceptions —
those two fall back to a title-cased Label ("Allen 2", "Norwalk 6").

SIMPLIFICATION IS REQUIRED: the raw full-precision fetch is ~18 MB (1,660
small, densely-vertexed precinct polygons — this layer follows actual
parcel/road boundaries, unlike the county-line-following chamber
districts build_legislative_boundaries.py simplifies). Same
topology-aware mapshaper pipeline as that script (Visvalingam,
keep-shapes) and the same 2,000-random-point agreement gate, adapted to
precincts' PCTID_TXT key instead of a district number. mapshaper reports
78 source self-intersections it cannot auto-repair (measured 2026-08-28,
stable across reruns) — a property of the source data's own digitization,
not of the simplification. The build does not treat that warning as
fatal; the 2,000-point gate is what actually proves correctness (0
overlaps, 99.95% agreement measured), and it passes clean.
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
OUT_PATH = os.path.join(APP_DATA_DIR, "ia-precincts.json")

LAYER_URL = "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/Iowa_Precincts/FeatureServer/0"
# Deliberately excludes PollingPlace / PollingPlaceAddr / PPID — see the
# module docstring. Never add them here without also building the dated
# per-election display contract phase 4 requires.
OUT_FIELDS = "CoName,CoFIPS,PctNameOfficial,Label,PctNumID,PCTID_TXT"
PAGE_SIZE = 1000

EXPECT_FEATURES = 1660
EXPECT_COUNTIES = 99

# Iowa's own bounding envelope (METRO_BBOX), used both as a sanity check on
# fetched points and as the sample region for the agreement gate.
STATE_BBOX = {"minLng": -96.69, "minLat": 40.32, "maxLng": -90.09, "maxLat": 43.55}

MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
SIMPLIFY_RETAIN = "20%"  # small, densely-vertexed polygons — conservative vs. the 9-12% used for statewide chamber districts
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m — the precision the app requests live


def fetch_json(url):
    require_robots_once(url, UA_STDLIB_DEFAULT, label="ia-build-ia-precincts")
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def layer_count():
    d = fetch_json(LAYER_URL + "/query?where=1%3D1&returnCountOnly=true&f=json")
    return int(d["count"])


def fetch_all_geojson():
    """Page past the 1,000-record cap, requesting GeoJSON directly (so no
    hand-rolled Esri-ring conversion is needed) with 6-decimal precision to
    keep the raw payload down before mapshaper ever sees it."""
    feats = []
    offset = 0
    while True:
        url = (LAYER_URL + "/query?where=1%3D1&outFields=" + OUT_FIELDS +
               "&outSR=4326&geometryPrecision=6&f=geojson"
               "&resultOffset=%d&resultRecordCount=%d" % (offset, PAGE_SIZE))
        d = fetch_json(url)
        if "error" in d:
            raise SystemExit("%s answered an error: %s" % (LAYER_URL, d["error"]))
        page = d.get("features", [])
        feats.extend(page)
        if len(page) < PAGE_SIZE and not d.get("properties", {}).get("exceededTransferLimit"):
            return feats
        offset += len(page)


def run_mapshaper(source_path, out_path):
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-simplify", "visvalingam", "keep-shapes", SIMPLIFY_RETAIN,
            "-o", "precision=" + PRECISION, "format=geojson", out_path,
        ],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon mirroring index.html's even-odd test (fleet-standard copy) ---
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


def _precincts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def validate(source_features, result_features, key_prop, samples=2000, seed=2024):
    """Refuse the build unless simplification preserves precinct coverage
    over the state envelope vs. the full-precision fetch — the project's
    2,000 uniform-random-point protocol. Any point landing in two result
    precincts is a topology break."""
    src = _model(source_features, key_prop)
    new = _model(result_features, key_prop)
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        s_hits = _precincts_at(new, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = _precincts_at(src, pt)
        o = o_hits[0] if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    if overlaps > 0:
        return False, "topology broken: %d/%d points fell in >1 precinct" % (overlaps, samples)
    if pct < 99.5:
        return False, "point-in-precinct agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) agreement over the state envelope, 0 overlaps" % (agree, samples, pct)


def main():
    check_only = "--check" in sys.argv[1:]

    expected = layer_count()
    if expected != EXPECT_FEATURES:
        raise SystemExit(
            "Iowa_Precincts now reports %d features, expected %d — "
            "re-verify before shipping (Iowa counties re-precinct "
            "periodically; a count change is real information)"
            % (expected, EXPECT_FEATURES)
        )
    raw = fetch_all_geojson()
    if len(raw) != expected:
        raise SystemExit(
            "paged %d features against the layer's own count of %d — "
            "the page cap or a filter ate records" % (len(raw), expected)
        )

    source_features = []
    counties = set()
    for f in raw:
        props = f.get("properties") or {}
        geom = f.get("geometry")
        name = (props.get("PctNameOfficial") or "").strip()
        if not name:
            # measured 2026-08-28: exactly 2 of 1,660 (both Warren County) —
            # Label is populated on all 1,660 with no exceptions
            label = (props.get("Label") or "").strip()
            if not label:
                raise SystemExit("a record has neither PctNameOfficial nor "
                                 "Label (properties=%r)" % props)
            name = label.title()
        county = (props.get("CoName") or "").strip()
        co_fips = (props.get("CoFIPS") or "").strip()
        if not (county and co_fips):
            raise SystemExit("a record is missing county/FIPS (properties=%r)" % props)
        if not geom:
            raise SystemExit("%r (%s) carries no geometry" % (name, county))
        counties.add(county)
        pctid = (props.get("PCTID_TXT") or "").strip()
        source_features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "pctid": pctid,
                "name": name,
                "county": county,
                "geoid": "19" + co_fips.zfill(3),
                "number": (props.get("PctNumID") or "").strip() or None,
            },
        })

    if len(counties) != EXPECT_COUNTIES:
        raise SystemExit("precincts span %d counties, expected %d — a county "
                         "with zero precincts (or a name typo) would explain "
                         "this" % (len(counties), EXPECT_COUNTIES))

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "ia-precincts-src.geojson")
        with open(src_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": source_features}, f)
        out_tmp = os.path.join(tmp, "ia-precincts.geojson")
        run_mapshaper(src_path, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != EXPECT_FEATURES:
        raise SystemExit("%d features after simplify (expected exactly %d "
                         "precincts) — refusing to write" % (n, EXPECT_FEATURES))

    ok, msg = validate(source_features, simplified["features"], "pctid")
    if not ok:
        raise SystemExit("validation failed: %s" % msg)

    # pctid was only carried through for the validation join key — drop it
    # from the shipped properties (the card never needs it)
    for feat in simplified["features"]:
        feat["properties"].pop("pctid", None)
    simplified["features"].sort(key=lambda f: (f["properties"]["county"], f["properties"]["name"]))

    payload = json.dumps(simplified, ensure_ascii=False, separators=(",", ":"))
    if check_only:
        try:
            with open(OUT_PATH) as f:
                shipped = f.read()
        except OSError as e:
            raise SystemExit("data/app/ia-precincts.json is missing (%s) — run "
                             "this script without --check" % e)
        if shipped != payload:
            raise SystemExit("data/app/ia-precincts.json has drifted from the "
                             "live layer. Re-run: "
                             "python3 ia/scripts/build_ia_precincts.py")
        print("check: shipped file matches the live layer (%d precincts, %d counties); %s"
              % (n, len(counties), msg), file=sys.stderr)
        return

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(payload)
    print("wrote %d precincts across %d counties -> %s (%d bytes, %s; %s)"
          % (n, len(counties), os.path.relpath(OUT_PATH, REPO_ROOT), len(payload),
             SIMPLIFY_RETAIN, msg),
          file=sys.stderr)


if __name__ == "__main__":
    main()
