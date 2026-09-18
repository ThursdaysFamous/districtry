#!/usr/bin/env python3
"""
Build New York's statewide school-district boundary file in data/app/ from
the state's own NYS_Schools service, so the app fetches same-origin geometry
instead of downloading a live multi-megabyte polygon layer on first toggle.

SOURCE. https://gisservices.its.ny.gov/arcgis/rest/services/NYS_Schools/
FeatureServer/18 ("School Districts"), NYS Office of Information Technology
Services Geospatial Data Services, based on input from the NYS Education
Department. Fields read: SCHOOL_ID, SCHOOLDIST, SED_CODE_1, POPULAR_NA,
SEDDIR_BOC. Measured 2026-09-18: 936 polygon rows, returned by one unpaged
query (the layer's maxRecordCount is 10000, well past 936; a plain
returnCountOnly query confirms 936; exceededTransferLimit is absent). Host
robots.txt on gisservices.its.ny.gov answers HTTP 404, read as allow-all by
scripts/robots_policy.py.

THE RECONCILIATION THIS BUILD RESTS ON, measured 2026-09-18 and recorded in
docs/NY_EXPANSION_PLAN.md's PR 2 "school-district" subsection. TIGERweb's
School layer for New York State (STATE='36') carries 680 rows (663 unified +
3 secondary + 14 elementary). This layer's 936 exceed that by exactly 256,
and the excess is accounted for rather than assumed:
  - 33, from New York City's 34 polygon rows in this layer against
    TIGERweb's ONE row ("New York City Department Of Education"). TIGERweb
    answers "New York City" for every point in the five boroughs; this
    layer names the actual community school district, which is the whole
    reason the state layer is the layer of record here rather than
    TIGERweb.
  - 220, from multipart polygons outside the city (one district's geometry
    split across several rows) plus the two SED-code collisions the trap
    below names.
  - 3, from special-act, non-operating and reservation-area districts
    TIGERweb carries no row for at all (Berkshire UFSD, Hopevale UFSD,
    South Mountain-Hickory Common, and the Tuscarora Indian Reservation
    area).
This script does not re-derive that reconciliation. It dissolves the 936
rows to the distinct-entity count the reconciliation implies and refuses to
write if that count moves (EXPECTED_ENTITIES below, measured 2026-09-18).

DISSOLVE KEY: SED_CODE_1, with a name-keyed fallback for the 6 rows whose
SED_CODE_1 is blank (stored on the service as a single space, not an empty
string or null; both are treated the same by this script's normalization).
Those 6 rows fall into exactly 4 distinct entities by SCHOOLDIST name,
measured 2026-09-18: TUSCARORA IND.RES., OESJ (3 rows), Sewanhaka Central,
Bellmore-Merrick. This script does NOT dissolve on SCHOOLDIST or SCHOOL_ID:
measured the same day, 936 rows carry only 715 distinct SCHOOLDIST values
and 932 distinct SCHOOL_ID values, so both collide across rows that this
script's own guards below prove are NOT the same entity by SED_CODE_1 --
using either as the dissolve key would silently merge some of those.

TRAP, measured 2026-09-18 and load-bearing: SED_CODE_1 is not a clean key
on its own. Two codes are shared by two genuinely distinct districts, and
both members of both pairs exist separately in TIGERweb:
  280230020000 -- two rows, SCHOOLDIST "VALLEY STR HEMP 30" and
                  "VALLEY STRM CENTRAL" (Valley Stream 30 UFSD / Valley
                  Stream Central HS District)
  140701060000 -- two rows, SCHOOLDIST "CHEEKTOWAGA" and
                  "CHEEKTOWAGA-SLOAN"
EXCEPTION_CODES below carries exactly these two, and this script requires,
before it fetches anything else about the data, that they are the ONLY
codes carrying more than one distinct SCHOOLDIST name among the 930
non-blank rows. If a third code ever shows more than one name, the build
refuses rather than silently merging two districts into one polygon; a new
collision found this way must be reviewed and added to EXCEPTION_CODES by
hand.

FIELDS SHIPPED: SCHOOLDIST (falling back to POPULAR_NA on any row where
SCHOOLDIST is blank -- none are, measured 2026-09-18, but the fallback
ships anyway per the plan) as the name, and SED_CODE_1 as the identifier
(null on the 4 blank-code entities, which have none). SCHOOL_ID, POPULAR_NA
and SEDDIR_BOC are fetched only to support the guards above and the
diagnostics this script prints to stderr; none of the three reaches
data/app/.

WHAT THIS IS NOT. ny/data/app/coverage-gaps.json and ny/index.html's
existing `school-district` registration read NYC's Community School
District layer (Socrata 8ugf-3d8u, 32 districts) under the city tier's
coverage gate -- a different concept, New York City's own sub-borough
school-administrative zones, and it stays exactly as shipped. This file is
the statewide school OPERATING district layer, of which the city's part
(NYC Department Of Education) is a single entity in TIGERweb's accounting
and 34 rows / some number of SED codes in this one.

SIMPLIFICATION. mapshaper via npx, pinned to mapshaper@0.6.102 (the fleet
convention), Visvalingam, keep-shapes, topology-aware, dissolve and
simplify in one mapshaper invocation per candidate -- the
ny/scripts/build_ny_judicial_districts.py order: dissolve first, so
simplification is never asked to smooth over an internal seam that the
dissolve is about to remove anyway. This script tries several retain
percentages (RETAIN_CANDIDATES below) against the same full-precision
fetch and, for each, reclassifies the fleet's 2,000-point protocol -- the
raw, multi-row-per-entity fetch against the dissolved-and-simplified
result, over the state envelope measured from this layer's own extent --
refusing any candidate under 99.5% agreement or with any point landing in
more than one entity. Among the candidates that clear the gate it writes
the smallest. The raw-side classifier is not a byte-for-byte copy of the
sibling builders' point-in-polygon check: a raw entity can be several rows
(a multipart district before its dissolve), so a point that lands inside
two of that ONE entity's own rows must read as agreement, not as an
overlap -- see _entities_at() below.

NO RAW SNAPSHOT IS KEPT under data/source/. The unpaged fetch is 8,339,502
bytes (measured 2026-09-18) -- an order of magnitude past ny-counties.json's
source snapshot and closer to the 20.6 MB / 3.7 MB fetches
build_ny_municipalities.py explicitly declines to snapshot for the same
reason. This script follows that precedent rather than build_ny_counties.py's.

Prerequisites: curl (fetch, works through an HTTPS proxy) and Node.js
(mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ny/scripts/build_ny_school_districts.py
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

SERVICE = (
    "https://gisservices.its.ny.gov/arcgis/rest/services/"
    "NYS_Schools/FeatureServer/18"
)
FIELDS = ["SCHOOL_ID", "SCHOOLDIST", "SED_CODE_1", "POPULAR_NA", "SEDDIR_BOC"]
EXPECTED_ROWS = 936  # measured 2026-09-18 (returnCountOnly and the fetch agree)
EXPECTED_ENTITIES = 716  # measured 2026-09-18 -- see _derive_groups()
OUT_FILE = "ny-school-districts.json"
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m, the precision the app requests live
RETAIN_CANDIDATES = ["12%", "8%", "5%"]  # smallest passing one ships
PASS_THRESHOLD = 99.5  # the fleet rule
SAMPLES = 2000
SEED = 2024

# The two SED_CODE_1 values shared by two genuinely distinct districts
# (measured 2026-09-18; see docs/NY_EXPANSION_PLAN.md's PR 2
# "school-district" subsection). Every other non-blank code must carry
# exactly one distinct SCHOOLDIST name across all its rows, or the build
# refuses. Values are the substring common to both districts' names on
# THIS service (abbreviated -- "VALLEY STR HEMP 30" / "VALLEY STRM
# CENTRAL" and "CHEEKTOWAGA" / "CHEEKTOWAGA-SLOAN" -- not the full names
# in the expansion plan's prose), used only to confirm the collision is
# still the one this script was written against.
EXCEPTION_CODES = {"280230020000", "140701060000"}
EXCEPTION_NAME_SUBSTRINGS = {
    "280230020000": "VALLEY STR",
    "140701060000": "CHEEKTOWAGA",
}

# The 6 rows whose SED_CODE_1 is blank fall into exactly 4 distinct
# entities by SCHOOLDIST name (measured 2026-09-18: TUSCARORA IND.RES.,
# OESJ x3, Sewanhaka Central, Bellmore-Merrick). Each expected substring
# must match exactly one of the 4 groups and every group must match
# exactly one substring.
BLANK_CODE_NAME_SUBSTRINGS = ["TUSCARORA", "OESJ", "SEWANHAKA", "BELLMORE"]
EXPECTED_BLANK_ROWS = 6
EXPECTED_BLANK_GROUPS = 4


def fetch_school_districts():
    """Fetch every row of the School Districts layer as GeoJSON in
    EPSG:4326, in one unpaged query (936 rows sits well under the layer's
    maxRecordCount of 10000). Uses curl so it works through an HTTPS proxy
    (as in the Claude Code sandbox)."""
    url = (
        SERVICE + "/query"
        "?where=1%3D1"
        "&outFields=" + ",".join(FIELDS) +
        "&outSR=4326&geometryPrecision=6&f=geojson"
    )
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300", url],
        check=True, capture_output=True,
    ).stdout
    geo = json.loads(out)
    feats = geo.get("features") or []
    if not feats:
        raise RuntimeError("NYS_Schools School Districts layer (18) returned no features")
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("NYS_Schools School Districts layer (18) hit the transfer cap -- needs paging")
    return geo


def run_mapshaper_dissolve_simplify(source_path, simplify, out_path):
    subprocess.run(
        [
            "npx", "-y", MAPSHAPER, source_path,
            "-dissolve", "_gid",
            "calc=SCHOOLDIST=first(_name);SED_CODE_1=first(_sed)",
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
    return [(f["properties"].get(key_prop), f["geometry"], _bbox(f["geometry"])) for f in features]


def _entities_at(model, pt):
    """Distinct entity keys whose polygon contains pt. A set rather than a
    list: the raw (pre-dissolve) model can carry several rows per entity
    (a multipart district's parts before its dissolve), and a point
    landing inside two of that ONE entity's own rows is agreement, not an
    overlap. Only two DIFFERENT keys both matching the same point is a
    real overlap."""
    hits = set()
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.add(key)
    return hits


def _state_bbox(features):
    """Measure the state envelope from this layer's own fetched geometry,
    so validation samples the extent this build actually saw rather than a
    number copied from another document."""
    b = [1e9, 1e9, -1e9, -1e9]
    for f in features:
        fb = _bbox(f["geometry"])
        b[0], b[1] = min(b[0], fb[0]), min(b[1], fb[1])
        b[2], b[3] = max(b[2], fb[2]), max(b[3], fb[3])
    return {"minLng": b[0], "minLat": b[1], "maxLng": b[2], "maxLat": b[3]}


def classify(raw_model, candidate_features, state_bbox, samples=SAMPLES, seed=SEED):
    """The fleet's 2,000-uniform-random-point protocol: raw (pre-dissolve,
    multi-row-per-entity) classification against the dissolved-and-
    simplified candidate, over the measured state envelope. Returns
    (agreement_pct, overlaps, agree, samples)."""
    new_model = _model(candidate_features, "_gid")
    rng = random.Random(seed)
    agree = overlaps = 0
    for _ in range(samples):
        pt = (rng.uniform(state_bbox["minLng"], state_bbox["maxLng"]),
              rng.uniform(state_bbox["minLat"], state_bbox["maxLat"]))
        s_hits = _entities_at(new_model, pt)
        if len(s_hits) > 1:
            overlaps += 1
        o_hits = _entities_at(raw_model, pt)
        o = next(iter(o_hits)) if len(o_hits) == 1 else (None if not o_hits else "MULTI")
        s = next(iter(s_hits)) if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    return pct, overlaps, agree, samples


def _norm(v):
    """String-normalize an ArcGIS attribute value regardless of its JSON
    type. SED_CODE_1 is esriFieldTypeString on this service (measured
    2026-09-18), so this is defensive rather than load-bearing, but
    SCHOOL_ID is esriFieldTypeInteger and this function is also used on
    it."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _derive_groups(feats):
    """Assign every raw feature a dissolve key (_gid) and a display name
    (_name), and run the guards that must hold before any geometry work
    starts. Returns the number of distinct entities the dissolve is
    expected to produce, for the count guard on this build's own dissolve
    step below, and the set of confirmed exception codes."""
    # Pass 1: which non-blank codes carry more than one distinct name.
    code_names = {}
    for f in feats:
        props = f["properties"]
        sed = _norm(props.get("SED_CODE_1"))
        if not sed:
            continue
        name = _norm(props.get("SCHOOLDIST")) or _norm(props.get("POPULAR_NA"))
        code_names.setdefault(sed, set()).add(name.upper())

    dup_codes = {code for code, names in code_names.items() if len(names) > 1}
    if dup_codes != EXCEPTION_CODES:
        raise RuntimeError(
            "school-districts: codes with more than one distinct SCHOOLDIST "
            "name are %s, expected exactly the two known collisions %s -- "
            "refusing to write (a new collision must be reviewed and added "
            "to EXCEPTION_CODES by hand, never merged silently)"
            % (sorted(dup_codes), sorted(EXCEPTION_CODES))
        )
    for code in EXCEPTION_CODES:
        names = code_names.get(code, set())
        if len(names) != 2:
            raise RuntimeError(
                "school-districts: exception code %s carries %d distinct "
                "names (%s), expected exactly 2 -- refusing to write"
                % (code, len(names), sorted(names))
            )
        expected_sub = EXCEPTION_NAME_SUBSTRINGS[code]
        if not all(expected_sub in n for n in names):
            raise RuntimeError(
                "school-districts: exception code %s's two names (%s) do "
                "not both contain %r -- refusing to write, the collision "
                "this code names may have changed"
                % (code, sorted(names), expected_sub)
            )

    # Pass 2: assign the dissolve key per feature.
    for f in feats:
        props = f["properties"]
        sed = _norm(props.get("SED_CODE_1"))
        name = _norm(props.get("SCHOOLDIST")) or _norm(props.get("POPULAR_NA"))
        if not sed:
            gid = "name:" + name.upper()
        elif sed in EXCEPTION_CODES:
            gid = "sedname:" + sed + "|" + name.upper()
        else:
            gid = "sed:" + sed
        props["_gid"] = gid
        props["_name"] = name
        props["_sed"] = sed

    # Blank-code guard: exactly 6 rows, falling into exactly 4 named
    # entities, each matching exactly one of the expected substrings.
    blank_rows = [f for f in feats if not f["properties"]["_sed"]]
    if len(blank_rows) != EXPECTED_BLANK_ROWS:
        raise RuntimeError(
            "school-districts: %d rows have a blank SED_CODE_1, expected "
            "exactly %d -- refusing to write"
            % (len(blank_rows), EXPECTED_BLANK_ROWS)
        )
    blank_names = sorted(set(f["properties"]["_name"].upper() for f in blank_rows))
    if len(blank_names) != EXPECTED_BLANK_GROUPS:
        raise RuntimeError(
            "school-districts: the %d blank-code rows carry %d distinct "
            "names (%s), expected exactly %d -- refusing to write"
            % (len(blank_rows), len(blank_names), blank_names, EXPECTED_BLANK_GROUPS)
        )
    unmatched_subs = list(BLANK_CODE_NAME_SUBSTRINGS)
    unmatched_names = list(blank_names)
    for name in blank_names:
        hit = next((s for s in unmatched_subs if s in name), None)
        if hit is None:
            raise RuntimeError(
                "school-districts: blank-code entity %r matches none of the "
                "expected substrings %s -- refusing to write"
                % (name, BLANK_CODE_NAME_SUBSTRINGS)
            )
        unmatched_subs.remove(hit)
        unmatched_names.remove(name)
    if unmatched_subs:
        raise RuntimeError(
            "school-districts: expected blank-code substrings %s matched no "
            "entity -- refusing to write" % unmatched_subs
        )

    num_entities = len(set(f["properties"]["_gid"] for f in feats))
    return num_entities, dup_codes


def strip_for_shipping(features):
    out = []
    for f in features:
        props = f["properties"]
        shipped = {
            "SCHOOLDIST": props.get("SCHOOLDIST"),
            "SED_CODE_1": props.get("SED_CODE_1") or None,
        }
        out.append({"type": "Feature", "properties": shipped, "geometry": f["geometry"]})
    return {"type": "FeatureCollection", "features": out}


def _verify_exception_pairs_in_output(shipped_features):
    """The output-level version of the same guard: after dissolve, each
    exception code must still name two distinct districts in the file this
    script is about to write, not one merged polygon."""
    by_code = {}
    for f in shipped_features:
        code = f["properties"].get("SED_CODE_1")
        if code in EXCEPTION_CODES:
            by_code.setdefault(code, []).append(_norm(f["properties"].get("SCHOOLDIST")).upper())
    for code in EXCEPTION_CODES:
        names = by_code.get(code, [])
        if len(names) != 2 or len(set(names)) != 2:
            raise RuntimeError(
                "school-districts: after dissolve, code %s carries %r in "
                "the shipped file (expected exactly 2 distinct districts) "
                "-- refusing to write" % (code, names)
            )


def main():
    source = fetch_school_districts()
    feats = source["features"]

    n = len(feats)
    if n != EXPECTED_ROWS:
        raise RuntimeError(
            "school-districts: %d rows fetched (expected exactly %d, "
            "measured 2026-09-18) -- refusing to write" % (n, EXPECTED_ROWS)
        )

    for f in feats:
        if f.get("geometry") is None:
            raise RuntimeError(
                "school-districts: row %r has null geometry"
                % (f.get("properties", {}).get("SCHOOLDIST"),)
            )

    # Diagnostics the docstring's trap describes: SCHOOLDIST and SCHOOL_ID
    # both collide across rows this build's own guards prove are not the
    # same entity, which is why the dissolve key is SED_CODE_1 and not
    # either of them.
    distinct_schooldist = len(set(_norm(f["properties"].get("SCHOOLDIST")).upper() for f in feats))
    distinct_school_id = len(set(_norm(f["properties"].get("SCHOOL_ID")) for f in feats))
    print(
        "school-districts: %d rows fetched; %d distinct SCHOOLDIST names, "
        "%d distinct SCHOOL_ID values (both collide vs SED_CODE_1, see "
        "docstring)" % (n, distinct_schooldist, distinct_school_id),
        file=sys.stderr,
    )

    num_entities, dup_codes = _derive_groups(feats)
    print(
        "school-districts: dissolve key assigned -- %d distinct entities "
        "from %d rows; confirmed exception codes %s"
        % (num_entities, n, sorted(dup_codes)),
        file=sys.stderr,
    )
    if num_entities != EXPECTED_ENTITIES:
        raise RuntimeError(
            "school-districts: dissolve key produces %d distinct entities, "
            "expected exactly %d (measured 2026-09-18) -- refusing to "
            "write; the source has moved and this script's guards need "
            "re-checking before the new number is trusted"
            % (num_entities, EXPECTED_ENTITIES)
        )

    raw_model = _model(feats, "_gid")
    state_bbox = _state_bbox(feats)

    # Slim geometry for mapshaper: only the fields the dissolve needs.
    slim_feats = [
        {
            "type": "Feature",
            "properties": {
                "_gid": f["properties"]["_gid"],
                "_name": f["properties"]["_name"],
                "_sed": f["properties"]["_sed"],
            },
            "geometry": f["geometry"],
        }
        for f in feats
    ]
    slim = {"type": "FeatureCollection", "features": slim_feats}

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "school-districts-src.geojson")
        with open(src_path, "w") as fh:
            json.dump(slim, fh)

        for retain in RETAIN_CANDIDATES:
            out_tmp = os.path.join(tmp, "school-districts-" + retain.rstrip("%") + ".geojson")
            run_mapshaper_dissolve_simplify(src_path, retain, out_tmp)
            with open(out_tmp) as fh:
                dissolved = json.load(fh)
            dfeats = dissolved["features"]

            if len(dfeats) != num_entities:
                raise RuntimeError(
                    "school-districts: dissolve at retain %s produced %d "
                    "entities, expected exactly %d -- refusing to write"
                    % (retain, len(dfeats), num_entities)
                )

            pct, overlaps, agree, samples = classify(raw_model, dfeats, state_bbox)

            shipped = strip_for_shipping(dfeats)
            _verify_exception_pairs_in_output(shipped["features"])

            compact = json.dumps(shipped, separators=(",", ":"))
            n_bytes = len(compact)
            passed = overlaps == 0 and pct >= PASS_THRESHOLD

            results.append({
                "retain": retain,
                "bytes": n_bytes,
                "agreement_pct": pct,
                "agree": agree,
                "samples": samples,
                "overlaps": overlaps,
                "passed": passed,
                "compact": compact,
                "shipped": shipped,
            })

            print(
                "  retain %-4s -> %9d bytes; %d entities; agreement %6.2f%% "
                "(%d/%d); overlaps %d -> %s"
                % (retain, n_bytes, len(dfeats), pct, agree, samples,
                   overlaps, "PASS" if passed else "FAIL"),
                file=sys.stderr,
            )

    passing = [r for r in results if r["passed"]]
    if not passing:
        raise RuntimeError(
            "school-districts: no retain candidate in %r cleared the "
            "%.1f%% classification gate with zero overlaps -- refusing to "
            "write. Results: %r"
            % (RETAIN_CANDIDATES, PASS_THRESHOLD,
               [(r["retain"], r["agreement_pct"], r["overlaps"]) for r in results])
        )
    chosen = min(passing, key=lambda r: r["bytes"])

    # Round-trip: re-parse what is about to be written and confirm it
    # matches the in-memory object, so a serialization bug can't ship
    # silently.
    if json.loads(chosen["compact"]) != chosen["shipped"]:
        raise RuntimeError("school-districts round-trip mismatch before writing")

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)
    with open(out_path, "w") as fh:
        fh.write(chosen["compact"])

    print(
        "school-districts -> data/app/%s: %d entities from %d source rows "
        "(statewide); state envelope measured lng %.3f..%.3f lat %.3f..%.3f; "
        "chosen retain %s, %d bytes, %.2f%% agreement (%d/%d), 0 overlaps; "
        "all other candidates: %s"
        % (OUT_FILE, num_entities, n, state_bbox["minLng"], state_bbox["maxLng"],
           state_bbox["minLat"], state_bbox["maxLat"], chosen["retain"],
           chosen["bytes"], chosen["agreement_pct"], chosen["agree"], chosen["samples"],
           [(r["retain"], r["bytes"], round(r["agreement_pct"], 2), r["overlaps"]) for r in results]),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
