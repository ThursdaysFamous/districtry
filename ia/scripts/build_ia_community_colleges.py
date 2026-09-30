#!/usr/bin/env python3
"""
Build data/app/ia-community-colleges.json -- Iowa's 15 community college
merged areas (Iowa Code 260C.11), identity-only.

BOUNDARY SOURCE, and why the NEWER of two layers is the one shipped: the
Iowa Legislative Services Agency's ArcGIS org (services.arcgis.com/
vPD5PVLI6sfkZ5E4) carries two vintages of the same 15 merged-area polygons --
`CommColleges2020` (published 2021-12-15) and `CC_2026update` (edited
2026-07-02, service path `CC_2026update/FeatureServer/0`, layer name
`CC_Boundaries_REV2026` -- the layer NAME, not the service name, so query
`.../CC_2026update/FeatureServer/0`, never `.../CC_Boundaries_REV2026/...`,
which 400s). CONFIRMED LIVE 2026-08-28, the two disagree on Southeastern
Community College's own code: the older layer carries `DISTRICT="08"`,
the newer `DISTRICT="16"`. Southeastern's own institutional history page
(scciowa.edu) states it was chartered as "Merged Area XVI" in 1965, and
Iowa's community college numbering runs I-VII, IX-XVI (no "VIII" survives
today -- the original Merged Area 8 was dissolved into its neighbors
decades ago), which every other source in this build agrees with:
ccforiowa.org's own 15-seat table uses I-VII, IX-XVI, skipping VIII. So
"16" is correct and "08" is the stale value -- the newer layer is shipped.

A NATIVE SPATIAL-REFERENCE TRAP, confirmed live: `CC_2026update`'s service
metadata declares its native SR as wkid 102675 ("NAD 1983 StatePlane
Oklahoma North FIPS 3501 Feet") -- almost certainly a copy-paste artifact,
since the data is Iowa. It reprojects correctly when `outSR=4326` is
requested explicitly (verified: Southeastern's own polygon returns
coordinates in its real West Burlington-area location), so this builder
always passes `outSR` -- never trust a bare geometry fetch from this
service to already be in degrees.

THREE INDEPENDENT WITNESSES agree exactly, confirmed live 2026-08-28: (1)
the 15 college names in `CC_2026update` match `CommColleges2020` layer 1's
15 names one for one; (2) that layer's own `SUM_TotalPop20` field sums to
3,190,369 across all 15 -- Iowa's exact official 2020 census population;
(3) its `NumberofDirectorDistricts` field sums to 124 -- exactly the
"124 locally elected trustees" figure ccforiowa.org (the state trustees'
association) states in prose on its own site. All three gate the build.

NO SUB-DISTRICT GEOMETRY SHIPS HERE, and that is a measurement, not a
deferral of convenience: the LSA org's own `CC_DD2023` layer (123 director
sub-districts, "effective August 1, 2023") is short exactly one polygon --
confirmed live: Des Moines Area Community College's own site names 9
sitting trustees across Districts 1-9, but `CC_DD2023` carries only 8
Des Moines Area features (District 2 is entirely absent, not merely
mis-drawn), and the layer's total (123) is short by exactly the 124 the
population/name witnesses above independently confirm. A per-district
card would either misrepresent that missing seat as unrepresented
territory or require sourcing DMACC's District 2 boundary from a
non-machine-readable PDF map. `cc-director-district` is deferred to a
later phase pending that geometry.

NO ROSTER SHIPS EITHER, and for a different reason: `ccforiowa.org/about/
board-members-officers` -- the only statewide roster candidate --
publishes 15 rows (one representative per college, the association's own
governing table), not the 124 individual trustees; confirmed live
2026-08-28. Each of Iowa's 15 colleges names its own trustees on its own
site (DMACC, Kirkwood and Iowa Western all confirmed live, each with a
clean per-district table), so the real roster is 15 separate publishers,
not one -- exactly the shape this project ships identity-only for
elsewhere (Iowa's own `school-district-unified` is the direct precedent:
elected boards, no statewide roster, link to the district instead) rather
than as a 15-source scrape in this PR.

Iowa Code 260C.11/260C.13 (lawserver.com, cross-checked against Justia
and legis.iowa.gov section listings, live 2026-08-28): the board is
GENUINELY ELECTED -- "one member elected from each director district in
the area by the electors of the respective district" -- four-year terms,
board-filled vacancies only until the next election. Districts follow
precinct or school-district lines and MAY SPLIT A COUNTY (260C.13:
"boundaries shall follow precinct boundaries or school director district
boundaries"; Southeastern's own service area is stated as covering "the
south half of Louisa" county) -- unlike Wisconsin's WTCS technical
college districts, whose board is APPOINTED under a different statute,
this is a genuinely DISTRICTED, ELECTED political layer, and the card
says so explicitly.

Gates (the build refuses to write unless all hold):
  * exactly 15 features from CC_2026update;
  * exactly 15 records from the CommColleges2020 witness, names matching
    CC_2026update's COMCOLLEGE set 1:1;
  * the witness population sum equals 3,190,369 (Iowa's 2020 census total);
  * the witness director-district sum equals 124;
  * Southeastern's own NDISTRICT is 16, never 8 (the confirmed bug fix).

Usage:
    python3 ia/scripts/build_ia_community_colleges.py            # write the file
    python3 ia/scripts/build_ia_community_colleges.py --check    # verify shipped, write nothing
"""

import argparse
import json
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, ua_requests_default  # noqa: E402  (FLEET_SHARED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
OUT_FILE = os.path.join(REPO_ROOT, "data", "app", "ia-community-colleges.json")

BOUNDARY_URL = ("https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/"
                 "CC_2026update/FeatureServer/0/query")
WITNESS_URL = ("https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/"
               "CommColleges2020/FeatureServer/1/query")

EXPECT_COLLEGES = 15
EXPECT_POP_2020 = 3190369
EXPECT_DIRECTOR_DISTRICTS = 124
SOUTHEASTERN_NAME = "Southeastern"
SOUTHEASTERN_NDISTRICT = 16

REQUEST_TIMEOUT = 60


def fetch_json(url, params):
    import requests  # noqa: PLC0415 -- only this module's fetchers need network
    require_robots_once(url, ua_requests_default(), label="ia-build-ia-community-colleges")
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise SystemExit("%s answered an error: %s" % (url, data["error"]))
    return data


def fetch_boundaries():
    data = fetch_json(BOUNDARY_URL, {
        "where": "1=1",
        "outFields": "DISTRICT,NDISTRICT,COMCOLLEGE",
        "outSR": "4326",
        "geometryPrecision": 6,
        "f": "geojson",
    })
    feats = data.get("features") or []
    if len(feats) != EXPECT_COLLEGES:
        raise SystemExit("CC_2026update returned %d features, expected %d"
                          % (len(feats), EXPECT_COLLEGES))
    return feats


def fetch_witness():
    data = fetch_json(WITNESS_URL, {
        "where": "1=1",
        "outFields": "CCname,NumberofDirectorDistricts,SUM_TotalPop20",
        "returnGeometry": "false",
        "f": "json",
    })
    feats = data.get("features") or []
    if len(feats) != EXPECT_COLLEGES:
        raise SystemExit("CommColleges2020 witness returned %d records, expected %d"
                          % (len(feats), EXPECT_COLLEGES))
    return [f["attributes"] for f in feats]


def build():
    boundaries = fetch_boundaries()
    witness = fetch_witness()

    witness_by_name = {w["CCname"]: w for w in witness}
    boundary_names = {f["properties"]["COMCOLLEGE"] for f in boundaries}
    if boundary_names != set(witness_by_name):
        raise SystemExit("name-set mismatch between CC_2026update and the witness: "
                          "boundary-only=%s witness-only=%s"
                          % (sorted(boundary_names - set(witness_by_name)),
                             sorted(set(witness_by_name) - boundary_names)))

    pop_sum = sum(w["SUM_TotalPop20"] for w in witness)
    if pop_sum != EXPECT_POP_2020:
        raise SystemExit("witness population sums to %d, expected Iowa's exact 2020 "
                          "census population %d" % (pop_sum, EXPECT_POP_2020))

    dd_sum = sum(w["NumberofDirectorDistricts"] for w in witness)
    if dd_sum != EXPECT_DIRECTOR_DISTRICTS:
        raise SystemExit("witness director-district count sums to %d, expected %d"
                          % (dd_sum, EXPECT_DIRECTOR_DISTRICTS))

    features = []
    southeastern_seen = False
    for feat in sorted(boundaries, key=lambda f: f["properties"]["NDISTRICT"]):
        props = feat["properties"]
        name = props["COMCOLLEGE"]
        if name == SOUTHEASTERN_NAME:
            southeastern_seen = True
            if props["NDISTRICT"] != SOUTHEASTERN_NDISTRICT:
                raise SystemExit(
                    "Southeastern's NDISTRICT is %r, expected %d -- the source may have "
                    "reverted to the stale pre-2026 numbering" % (props["NDISTRICT"], SOUTHEASTERN_NDISTRICT))
        w = witness_by_name[name]
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "district": props["NDISTRICT"],
                # all-lowercase key: findPropCI() in index.html lowercases the
                # actual property name but not its candidate string, so a
                # camelCase key here would never match its `keys: [...]` entry
                "directordistricts": w["NumberofDirectorDistricts"],
            },
            "geometry": feat["geometry"],
        })
    if not southeastern_seen:
        raise SystemExit("Southeastern Community College is missing from the boundary layer")

    if len(features) != EXPECT_COLLEGES:
        raise SystemExit("built %d colleges, expected %d" % (len(features), EXPECT_COLLEGES))

    return {"type": "FeatureCollection", "features": features}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                     help="verify the shipped file matches a fresh build; write nothing")
    args = ap.parse_args()

    built = build()
    if args.check:
        with open(OUT_FILE) as f:
            shipped = json.load(f)
        if json.dumps(shipped, sort_keys=True) != json.dumps(built, sort_keys=True):
            print("FAIL: shipped ia-community-colleges.json differs from a fresh build",
                  file=sys.stderr)
            sys.exit(1)
        print("check: shipped community-college geometry matches the live source and "
              "all three witnesses (%d colleges)" % len(built["features"]))
        return

    with open(OUT_FILE, "w") as f:
        json.dump(built, f, separators=(",", ":"))
    size = os.path.getsize(OUT_FILE)
    print("wrote %s -- %d community colleges, %.1f KB"
          % (OUT_FILE, len(built["features"]), size / 1024.0))


if __name__ == "__main__":
    main()
