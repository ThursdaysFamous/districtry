#!/usr/bin/env python3
"""
Build data/app/ia-supervisor-districts.json — Iowa's statewide county
supervisor districts, PLANTYPE-aware (Iowa Code ch. 331 lets each county
choose plan 1 at-large, plan 2 residence-district-elected-countywide, or
plan 3 single-member district).

WHERE THE LINES COME FROM, AND THE STALENESS PROBLEM
------------------------------------------------------
The Iowa Legislature's own ArcGIS organization publishes ALL 99 counties'
supervisor districts as one feature service:
services.arcgis.com/vPD5PVLI6sfkZ5E4/.../CountySupervisorDistricts/FeatureServer/0
(licenseInfo null — attribution-only posture). That is the convenience. The
authority problem: its own edit timestamp is 1706643533798 = 2024-01-30
(RE-VERIFIED live, unchanged, 2026-08-27) — and Senate File 75 (signed
2025-04-11) forces Story, Johnson and Black Hawk counties from PLAN 1
(at-large) to PLAN 3 (single-member district) for the November 2026
election. The aggregate still carries all three under their pre-SF75
at-large form (re-verified live: all three still read PLANTYPE=PLAN 1,
DISTRICT=AT-LARGE, 2026-08-27) — a stale-but-plausible answer is worse than
an absent one, so this build never ships that row as-is.

Two more measured facts the aggregate does NOT explain on its own:
  * JONES COUNTY IS ENTIRELY ABSENT — by name AND by its own FIPS code (105),
    confirmed 2026-08-27 (98 distinct counties in a service that should carry
    99; PLANTYPE has only ever 3 known values, so it isn't hiding under a
    4th). Jones's own site (jonescountyiowa.gov) independently states a
    5-member, single-member-district board with a published PDF map, but
    publishes no GIS service — this build does not draw it and ships no
    ia-supervisor-districts feature for Jones. That is a recorded gap
    (docs/DATA_LAYER_GUIDEBOOK.md), not a silent county-count fudge.
    CLOSED 2026-10-07: the county sent its own district file, and Jones now
    ships from it through COUNTY_SUPPLIED below, as does Tama, whose three
    aggregate rows trailed the five districts it elects from. main() raises
    if the aggregate ever gains a Jones row, so the two cannot both ship.
  * NUMDISTRICTS is each row's county-wide BOARD SIZE (repeated on every row
    of that county); MEMBERS is 1 on every plan-2/plan-3 row and 0 on every
    plan-1 AT-LARGE row (verified across the whole service) — NUMDISTRICTS,
    not MEMBERS, is what a card should state as "how many supervisors".

HOW THE THREE SF-75 COUNTIES ARE RECONCILED (this build's real work)
----------------------------------------------------------------------
Per docs/IA_EXPANSION_PLAN.md PR 5 and re-verified live 2026-08-27 against
LSA's county-redistricting ledger (legis.iowa.gov/publications/legalPubs/
countyRedistricting) plus each county's own site:

  * BLACK HAWK ships REAL, CURRENT geometry. The county's own "Interactive
    Supervisor District Map" ArcGIS Dashboard (linked from
    blackhawkcountyelections.iowa.gov/page/supervisordistricts/) resolves to
    a hosted feature service, BlackHawkCoSupervisor_LSAplan1, at
    services5.arcgis.com/ya62ECiavqTkK0wv/... — 5 districts, populations
    26,148-26,293 against a 26,229 ideal (0.35% worst deviation), vintage
    2026-02-24. This is the adopted plan (news coverage confirms all 5 seats
    on the November 2026 ballot), so it ships as ordinary PLAN 3 data.
  * STORY and JOHNSON have SOS-approved adopted plans (Story: county board
    approved 2026-01-27, SOS technical approval confirmed; Johnson: county
    board approved 2025-12-23, SOS approval 2026-01-07 — both re-confirmed
    live via news coverage 2026-08-27) and NEITHER publishes a GIS service
    (re-swept 2026-09-05). On 2026-08-26 each shipped as ONE county-level
    feature carrying PLANTYPE=TRANSITIONING and the adopted plan's known
    facts, on a card that said plainly it could not resolve which district
    contains a point — and that entry predicted its own successor: "a future
    PR that finds or extracts real geometry (e.g. a Jackson-County-IL-style
    vector PDF trace) supersedes this fallback."
      - STORY DID, 2026-09-05. Its three districts are read off the county
        Auditor's own printed map by build_story_supervisor_districts.py and
        resolved to whole Census 2020 blocks; see STORY below and that
        script's docstring for the method, the gates, and the correction to
        this project's own earlier claim about that PDF. Its PLANTYPE stays
        TRANSITIONING, because the lines are adopted and first elect in
        November 2026 while the board sitting now is at-large.
      - JOHNSON HAS NOT, and is now a recorded gap
        (johnson-county-supervisor-districts in docs/DATA_LAYER_GUIDEBOOK.md)
        rather than an absence described only in prose. It still ships the
        one county-level feature, reusing the county's own outer boundary
        from state-counties.json — county lines don't move, only the
        internal district lines do.

Occasional OPERATOR step, not weekly CI — Iowa publishes no statewide
supervisor roster (`build_ia_county_board_directory.py` is a separate,
board-size-only companion), and district lines only move once a decade plus
whenever SF-75-style legislation forces a mid-decade change. Prerequisites:
curl/requests and Node.js (mapshaper).

Usage:
    python3 ia/scripts/build_ia_supervisor_districts.py
    python3 ia/scripts/build_ia_supervisor_districts.py --check   # gates only, no write
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
OUT_NAME = "ia-supervisor-districts.json"
STATE_COUNTIES_PATH = os.path.join(APP_DATA_DIR, "state-counties.json")
MAPSHAPER = "mapshaper@0.6.102"

LSA_LAYER = "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/CountySupervisorDistricts/FeatureServer/0"
LSA_VINTAGE = "LSA-2024-01-30"
LSA_LAST_EDIT_MS = 1706643533798  # gate: refuse silently if this ever moves without review

KNOWN_TRANSITIONING = {"Black Hawk", "Story", "Johnson"}
# Counties whose LSA rows are replaced by lines the county itself supplied --
# see COUNTY_SUPPLIED below. Jones has no LSA row to drop; Tama's three are the
# pre-2024 plan.
COUNTY_SUPPLIED_REPLACES = {"Jones", "Tama"}
EXPECTED_MISSING = set()
EXPECT_TOTAL_COUNTIES = 99
KNOWN_PLANTYPES = {"PLAN 1", "PLAN 2", "PLAN 3"}

BLACK_HAWK = {
    "county": "Black Hawk",
    "fips": "013",
    "url": "https://services5.arcgis.com/ya62ECiavqTkK0wv/arcgis/rest/services/BlackHawkCoSupervisor_LSAplan1/FeatureServer/0",
    "district_field": "DirectorDi",
    "pop_field": "Pop2020",
    "expected_districts": 5,
    "source": "BLACKHAWK-COUNTY-2026-02-24",
    "source_url": "https://blackhawkcountyelections.iowa.gov/page/supervisordistricts/",
}

# Story LEFT this table on 2026-09-05 -- see STORY below. Johnson has not.
TRANSITIONING_PENDING = {
    "Johnson": {
        "fips": "103",
        "num_districts": 5,
        "populations": None,
        "ideal_population": 30571,
        "note": (
            "Johnson County is transitioning from at-large to district "
            "elections under Senate File 75. The Iowa Legislative Services "
            "Agency's plan (5 districts, ideal population approx. 30,571 "
            "each) was approved by the Board of Supervisors 2025-12-23 and "
            "received Secretary of State approval 2026-01-07. This app "
            "cannot yet identify which specific district contains this point."
        ),
        "source_url": "https://johnsoncountyiowa.gov/supervisor-districts",
    },
}
for _name, _rec in TRANSITIONING_PENDING.items():
    _rec["source"] = "ADOPTED-PENDING-GEOMETRY"

# Story County: real district lines, from the county's own printed map.
#
# Its board is STILL ELECTED AT LARGE. Senate File 75 moves it to three
# single-member districts at the November 2026 election, and the Board adopted
# these lines on 2026-01-27 -- so the county is genuinely mid-transition and
# PLANTYPE stays TRANSITIONING. What changed on 2026-09-05 is only that this
# app can now say WHICH district a point is in, where before it shipped one
# county-shaped feature that could not.
#
# Calling it PLAN 3 would be the tempting simplification and would be false: it
# would tell a reader their district elects one supervisor today, which is the
# exact class of error the fleet's at-large rule exists to prevent. The card
# distinguishes the two states by whether DISTRICT is a number or "PENDING".
#
# The geometry is built by ia/scripts/build_story_supervisor_districts.py --
# the county Auditor's own map read as vector path objects, georeferenced, and
# resolved to whole Census 2020 blocks so nothing traced ships. Its gate is
# that the derived populations equal the Legislative Services Agency's
# published 32,783 / 32,894 / 32,860 EXACTLY, district by district. That file
# is committed (data/source/, deploy-excluded) so this builder needs neither
# the PDF nor shapely; re-derive with that script's --check.
STORY = {
    "county": "Story",
    "fips": "169",
    "path": os.path.join(REPO_ROOT, "data", "source",
                         "story-supervisor-districts.geojson"),
    "expected_districts": 3,
    "populations": {"1": 32783, "2": 32894, "3": 32860},
    "source": "STORY-COUNTY-AUDITOR-MAP-2026-03-13",
    "source_url": "https://www.storycountyiowa.gov/1172/Jurisdictional-Maps",
    "note": (
        "Story County is moving from at-large to district elections under "
        "Senate File 75. These are the lines the Board of Supervisors adopted "
        "2026-01-27, read from the county Auditor's own district map; they "
        "first elect supervisors at the November 2026 election. The board "
        "sitting now is elected at large, so this district does not yet have "
        "a supervisor of its own."
    ),
}

# Jones and Tama: real district lines, from files each county's own office
# sent this project, resolved to whole Census 2020 blocks by
# ia/scripts/build_county_supplied_supervisor_districts.py and committed in
# data/source/ (deploy-excluded), the Story arrangement exactly. Both counties
# elect one supervisor per district today, so both are PLAN 3.
#
#   * JONES was the one county with no row in the LSA layer at all (by name and
#     by FIPS 105). Its GIS Coordinator sent the county's BOS_2022 shapefile on
#     2026-10-06; its block populations equal the county's own published
#     figures to the person.
#   * TAMA's LSA rows draw three districts; the county has elected five since
#     2022 and LSA drew the five on 2024-02-05, after the layer's vintage. The
#     Auditor sent the county's own map on 2026-10-01; its block populations
#     equal LSA's Plan I with one declared, county-witnessed parcel moved.
#
# The populations below are re-checked against the committed derivation, so a
# re-derivation that moved a single block stops this build.
COUNTY_SUPPLIED = [
    {
        "county": "Jones",
        "fips": "105",
        "path": os.path.join(REPO_ROOT, "data", "source",
                             "jones-supervisor-districts.geojson"),
        "populations": {"1": 4128, "2": 4120, "3": 4137, "4": 4132, "5": 4129},
        "note": (
            "Jones County's five supervisor districts, from the county's own "
            "GIS file (BOS_2022) sent by its GIS Coordinator on 6 October 2026."),
    },
    {
        "county": "Tama",
        "fips": "171",
        "path": os.path.join(REPO_ROOT, "data", "source",
                             "tama-supervisor-districts.geojson"),
        "populations": {"1": 3426, "2": 3453, "3": 3395, "4": 3420, "5": 3441},
        "note": (
            "Tama County's five supervisor districts, from the county "
            "Auditor's own district map sent on 1 October 2026."),
    },
]

# SIMPLIFY IS A SHARE OF THE WHOLE DATASET, NOT A PER-FEATURE TOLERANCE, so
# ADDING ONE COUNTY RE-SIMPLIFIES EVERY OTHER COUNTY. #737 added Story's three
# districts (270 features -> 272) and the same commit changed the geometry of
# 76 non-Story features across 49 counties, with no change to this constant
# and none to the mapshaper pin above. That was reported at the time as a
# re-simplification that "did NOT reproduce", i.e. as nondeterminism, and it
# is nothing of the kind: mapshaper's `-simplify <pct>` removes that
# proportion of the DATASET's points, so a bigger dataset gets a different
# per-shape budget. Measured directly on two synthetic collections, same
# mapshaper build, same flags: two rings simplified to 45 and 38 vertices
# alone, and to 57 and 67 with a third ring added beside them.
#
# So the expectation for the NEXT county added here is a large diff touching
# counties the change never mentions -- once, deterministically. A fresh
# rebuild against an unchanged source is a no-op, and if one is ever NOT a
# no-op, that is the upstream aggregate moving and worth reading.
SIMPLIFY = "10%"
PRECISION = "0.000001"
STATE_BBOX = {"minLng": -96.69, "minLat": 40.32, "maxLng": -90.09, "maxLat": 43.55}
VALIDATION_KEY = "_KEY"


def _curl(url):
    return subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300",
         "-H", "User-Agent: districtry/1.0 (+https://districtry.com/ia/)", url],
        check=True, capture_output=True,
    ).stdout


def _fetch_json(url):
    return json.loads(_curl(url))


def oid_field(base):
    meta = _fetch_json(base + "?f=json")
    for f in meta.get("fields", []):
        if f.get("type") == "esriFieldTypeOID":
            return f["name"]
    raise RuntimeError("no object-id field on " + base)


def fetch_layer(base, out_fields, where="1=1"):
    order = oid_field(base)
    feats = []
    offset = 0
    while True:
        params = {
            "where": where, "outFields": out_fields, "returnGeometry": "true",
            "outSR": "4326", "geometryPrecision": "6", "f": "geojson",
            "resultOffset": str(offset), "resultRecordCount": "1000",
            "orderByFields": order,
        }
        data = _fetch_json(base + "/query?" + urllib.parse.urlencode(params))
        batch = data.get("features") or []
        feats.extend(batch)
        if not data.get("properties", {}).get("exceededTransferLimit") and not data.get("exceededTransferLimit"):
            break
        if not batch:
            break
        offset += len(batch)
    return feats


def check_vintage():
    meta = _fetch_json(LSA_LAYER + "?f=json")
    last_edit = meta.get("editingInfo", {}).get("lastEditDate")
    if last_edit != LSA_LAST_EDIT_MS:
        raise RuntimeError(
            "LSA CountySupervisorDistricts lastEditDate changed (%r, expected %r) — "
            "the state may have published an updated plan; re-check Story/Johnson/"
            "Black Hawk (and every other county) before trusting the SF-75 "
            "reconciliation below" % (last_edit, LSA_LAST_EDIT_MS)
        )


def normalize_lsa(features):
    out = []
    for f in features:
        p = f["properties"]
        county = p["COUNTY"]
        out.append({
            "type": "Feature",
            "properties": {
                "COUNTY": county,
                "FIPS": "%03d" % int(p["FIPS"]),
                "DISTRICT": str(p["DISTRICT"]),
                "PLANTYPE": p["PLANTYPE"],
                "NUMDISTRICTS": int(p["NUMDISTRICTS"]),
                "POPULATION": None,
                "SOURCE": LSA_VINTAGE,
            },
            "geometry": f["geometry"],
        })
    return out


def black_hawk_features():
    feats = fetch_layer(BLACK_HAWK["url"], BLACK_HAWK["district_field"] + "," + BLACK_HAWK["pop_field"])
    if len(feats) != BLACK_HAWK["expected_districts"]:
        raise RuntimeError(
            "Black Hawk's own service returned %d districts, expected %d — "
            "re-check its adopted plan before shipping"
            % (len(feats), BLACK_HAWK["expected_districts"])
        )
    nums = sorted(int(f["properties"][BLACK_HAWK["district_field"]]) for f in feats)
    if nums != list(range(1, BLACK_HAWK["expected_districts"] + 1)):
        raise RuntimeError("Black Hawk districts are %s, expected 1..%d" % (nums, BLACK_HAWK["expected_districts"]))
    out = []
    for f in feats:
        p = f["properties"]
        n = int(p[BLACK_HAWK["district_field"]])
        out.append({
            "type": "Feature",
            "properties": {
                "COUNTY": BLACK_HAWK["county"],
                "FIPS": BLACK_HAWK["fips"],
                "DISTRICT": str(n),
                "PLANTYPE": "PLAN 3",
                "NUMDISTRICTS": BLACK_HAWK["expected_districts"],
                "POPULATION": int(p[BLACK_HAWK["pop_field"]]),
                "SOURCE": BLACK_HAWK["source"],
                "SOURCE_URL": BLACK_HAWK["source_url"],
            },
            "geometry": f["geometry"],
        })
    # population balance is informational, not a gate (see WI precedent) —
    # but a wildly unbalanced plan is worth a printed warning.
    pops = [f["properties"]["POPULATION"] for f in out]
    ideal = sum(pops) / len(pops)
    worst = max(abs(p - ideal) for p in pops) / ideal * 100
    print("Black Hawk: %d districts, pop %d-%d (ideal %.0f, worst %.1f%%)"
          % (len(out), min(pops), max(pops), ideal, worst), file=sys.stderr)
    return out


def story_features():
    """Story's three adopted districts, from the committed derivation.

    Read here rather than re-derived: build_story_supervisor_districts.py owns
    the PDF read and carries the gates, and this builder deliberately depends
    on nothing heavier than curl and mapshaper.
    """
    try:
        with open(STORY["path"]) as f:
            fc = json.load(f)
    except OSError as e:
        raise RuntimeError(
            "%s is missing (%s). Build it first: python3 "
            "ia/scripts/build_story_supervisor_districts.py"
            % (os.path.relpath(STORY["path"], REPO_ROOT), e))
    feats = fc.get("features") or []
    if len(feats) != STORY["expected_districts"]:
        raise RuntimeError("Story's derivation carries %d districts, expected %d"
                           % (len(feats), STORY["expected_districts"]))
    got = {f["properties"]["DISTRICT"]: f["properties"]["POPULATION"]
           for f in feats}
    if got != STORY["populations"]:
        raise RuntimeError(
            "Story's derived populations are %s, expected the Legislative "
            "Services Agency's published %s. Re-run "
            "ia/scripts/build_story_supervisor_districts.py --check"
            % (got, STORY["populations"]))
    out = []
    for f in feats:
        d = f["properties"]["DISTRICT"]
        out.append({
            "type": "Feature",
            "properties": {
                "COUNTY": STORY["county"],
                "FIPS": STORY["fips"],
                "DISTRICT": d,
                # NOT "PLAN 3" -- these lines are adopted and not yet in force.
                "PLANTYPE": "TRANSITIONING",
                "NUMDISTRICTS": STORY["expected_districts"],
                "POPULATION": STORY["populations"][d],
                "SOURCE": STORY["source"],
                "SOURCE_URL": STORY["source_url"],
                "SOURCE_NOTE": STORY["note"],
            },
            "geometry": f["geometry"],
        })
    pops = list(STORY["populations"].values())
    ideal = sum(pops) / len(pops)
    print("Story: %d adopted districts, pop %d-%d (ideal %.0f, worst %.2f%%) — "
          "still at-large until November 2026"
          % (len(out), min(pops), max(pops), ideal,
             max(abs(p - ideal) for p in pops) / ideal * 100), file=sys.stderr)
    return out


def county_supplied_features():
    """Jones's and Tama's districts, from their committed derivations."""
    out = []
    for rec in COUNTY_SUPPLIED:
        try:
            with open(rec["path"]) as f:
                feats = json.load(f).get("features") or []
        except OSError as e:
            raise RuntimeError(
                "%s is missing (%s). Build it first: python3 "
                "ia/scripts/build_county_supplied_supervisor_districts.py"
                % (os.path.relpath(rec["path"], REPO_ROOT), e))
        got = {f["properties"]["DISTRICT"]: f["properties"]["POPULATION"]
               for f in feats}
        if got != rec["populations"]:
            raise RuntimeError(
                "%s's derived populations are %s, expected %s. Re-run "
                "ia/scripts/build_county_supplied_supervisor_districts.py --check"
                % (rec["county"], got, rec["populations"]))
        for f in feats:
            p = f["properties"]
            out.append({
                "type": "Feature",
                "properties": {
                    "COUNTY": rec["county"],
                    "FIPS": rec["fips"],
                    "DISTRICT": p["DISTRICT"],
                    "PLANTYPE": "PLAN 3",
                    "NUMDISTRICTS": len(feats),
                    "POPULATION": p["POPULATION"],
                    "SOURCE": p["SOURCE"],
                    "SOURCE_URL": p["SOURCE_URL"],
                    "SOURCE_NOTE": rec["note"],
                },
                "geometry": f["geometry"],
            })
        pops = list(rec["populations"].values())
        print("%s: %d county-supplied districts, pop %d-%d"
              % (rec["county"], len(feats), min(pops), max(pops)), file=sys.stderr)
    return out


def load_state_county_geometry():
    with open(STATE_COUNTIES_PATH) as f:
        sc = json.load(f)
    by_basename = {}
    for f in sc["features"]:
        p = f["properties"]
        name = p.get("BASENAME") or (p.get("NAME") or "").replace(" County", "")
        by_basename[name] = f["geometry"]
    return by_basename


def transitioning_pending_features(county_geoms):
    out = []
    for name, rec in TRANSITIONING_PENDING.items():
        geom = county_geoms.get(name)
        if geom is None:
            raise RuntimeError("no state-counties.json geometry found for %r" % name)
        pops = rec.get("populations")
        out.append({
            "type": "Feature",
            "properties": {
                "COUNTY": name,
                "FIPS": rec["fips"],
                "DISTRICT": "PENDING",
                "PLANTYPE": "TRANSITIONING",
                "NUMDISTRICTS": rec["num_districts"],
                "POPULATION": None,
                "SOURCE": rec["source"],
                "SOURCE_URL": rec["source_url"],
                "SOURCE_NOTE": rec["note"],
            },
            "geometry": geom,
        })
    return out


def gate_counties(feats, county_geoms):
    by_county = {}
    for f in feats:
        by_county.setdefault(f["properties"]["COUNTY"], []).append(f)
    present = set(by_county)
    expected_present = set(county_geoms) - EXPECTED_MISSING
    missing_unexpected = expected_present - present
    present_unexpected = present - expected_present
    if missing_unexpected:
        raise RuntimeError(
            "county/counties present in state-counties.json but missing from the "
            "assembled supervisor-district set (beyond the recorded %s exception): %s"
            % (sorted(EXPECTED_MISSING), sorted(missing_unexpected))
        )
    if present_unexpected:
        raise RuntimeError(
            "county/counties in the assembled set that don't match state-counties.json: %s"
            % sorted(present_unexpected)
        )
    if len(present) != EXPECT_TOTAL_COUNTIES - len(EXPECTED_MISSING):
        raise RuntimeError(
            "%d counties represented, expected %d (%d total minus the recorded %s)"
            % (len(present), EXPECT_TOTAL_COUNTIES - len(EXPECTED_MISSING),
               EXPECT_TOTAL_COUNTIES, sorted(EXPECTED_MISSING))
        )
    bad_plantype = [f["properties"] for f in feats
                    if f["properties"]["PLANTYPE"] not in KNOWN_PLANTYPES | {"TRANSITIONING"}]
    if bad_plantype:
        raise RuntimeError("unknown PLANTYPE value(s): %s" % bad_plantype[:5])
    return by_county


def run_mapshaper(source_path, out_path):
    subprocess.run(
        ["npx", "-y", MAPSHAPER, source_path,
         "-simplify", "visvalingam", "keep-shapes", SIMPLIFY,
         "-o", "precision=" + PRECISION, "format=geojson", out_path],
        check=True, cwd=REPO_ROOT,
    )


# --- point-in-polygon (fleet-standard copy, mirrors index.html's even-odd test) ---
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
    if geom is None:
        return False
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
    return [(f["properties"]["COUNTY"] + "/" + f["properties"]["DISTRICT"], f["geometry"], _bbox(f["geometry"]))
            for f in features if f.get("geometry")]


def _districts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def validate(source_features, result_features, samples=5000, seed=2026):
    src = _model(source_features)
    new = _model(result_features)
    rng = random.Random(seed)
    pts = []
    while len(pts) < samples:
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        hits = _districts_at(src, pt)
        if hits:
            pts.append((pt, hits))
    agree = src_overlaps = new_overlaps = 0
    for pt, o_hits in pts:
        s_hits = _districts_at(new, pt)
        if len(s_hits) > 1:
            new_overlaps += 1
        if len(o_hits) > 1:
            src_overlaps += 1
        o = o_hits[0] if len(o_hits) == 1 else "MULTI"
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    if new_overlaps > src_overlaps:
        return False, ("simplification introduced overlap: %d/%d vs source %d/%d"
                        % (new_overlaps, samples, src_overlaps, samples))
    if pct < 99.5:
        return False, "point-in-district agreement only %.3f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.3f%%) agreement over %d in-state points" % (agree, samples, pct, samples)


def main():
    check_only = "--check" in sys.argv[1:]

    check_vintage()
    raw = fetch_layer(LSA_LAYER, "COUNTY,DISTRICT,PLANTYPE,NUMDISTRICTS,MEMBERS,FIPS")
    lsa = normalize_lsa(raw)
    replaced = KNOWN_TRANSITIONING | COUNTY_SUPPLIED_REPLACES
    lsa_kept = [f for f in lsa if f["properties"]["COUNTY"] not in replaced]
    dropped = len(lsa) - len(lsa_kept)
    print("LSA aggregate: %d features; dropping %d stale row(s) for %s"
          % (len(lsa), dropped, sorted(replaced)), file=sys.stderr)
    if any(f["properties"]["COUNTY"] == "Jones" for f in lsa):
        raise RuntimeError(
            "the LSA aggregate now carries Jones County -- compare it with the "
            "county's own file before letting either one win")

    bh = black_hawk_features()
    story = story_features()
    county_geoms = load_state_county_geometry()
    pending = transitioning_pending_features(county_geoms)

    supplied = county_supplied_features()

    feats = lsa_kept + bh + story + supplied + pending
    by_county = gate_counties(feats, county_geoms)
    print("gates: %d counties represented (%s recorded missing); PLANTYPE values all known"
          % (len(by_county), sorted(EXPECTED_MISSING)), file=sys.stderr)

    if check_only:
        return

    # tag each feature with a unique validation key before simplifying, so
    # mapshaper's feature order changes (if any) can't scramble the model
    for f in feats:
        f["properties"][VALIDATION_KEY] = f["properties"]["COUNTY"] + "/" + f["properties"]["DISTRICT"]

    source = {"type": "FeatureCollection", "features": feats}
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "supervisor-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, "supervisor.geojson")
        run_mapshaper(src_path, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != len(feats):
        raise RuntimeError("simplify changed the feature count: %d -> %d" % (len(feats), n))

    ok, msg = validate(feats, simplified["features"])
    if not ok:
        raise RuntimeError("validation failed: %s" % msg)

    for f in simplified["features"]:
        f["properties"].pop(VALIDATION_KEY, None)

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("round-trip mismatch before writing")
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, OUT_NAME)
    with open(out_path, "w") as f:
        f.write(compact)
    print("ia-supervisor-districts -> data/app/%s: %d features across %d counties; %s; %d bytes"
          % (OUT_NAME, n, len(by_county), msg, len(compact)), file=sys.stderr)


if __name__ == "__main__":
    main()
