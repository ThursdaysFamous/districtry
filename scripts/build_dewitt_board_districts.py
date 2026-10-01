#!/usr/bin/env python3
"""
Build data/app/dewitt-county-board-districts.json — De Witt's 4 County Board
districts, DERIVED by dissolving the county's own precinct layer per the
composition the county publishes in prose.

WHY THIS EXISTS — the county publishes no board-district geometry. Its GIS is
a vendor Portico viewer backed by a Sidwell/Magnasoft AGOL org, and the only
board-district artifact anywhere on the county site is a 97 KB raster JPG.

WHAT MAKES THE DERIVATION SOUND — unlike a map that has to be read, De Witt
states each district's composition as TEXT, repeated on every one of its
twelve members' rows ("District B — Wilson, Rutledge, Santa Anna, Harp,
DeWitt, Nixon"). Transcribing text is not interpretation, and the result is
checked three ways on every run:

  1. PARTITION — the four districts must name all 23 precincts the county's
     precinct layer carries, each exactly once. A missing or doubled precinct
     fails the build. This is the strongest check available here and it is
     exact: 6 + 8 + 5 + 4 = 23.
  2. NAME MATCH — every name in the composition must resolve to a precinct in
     the live layer after normalization; nothing is fuzzy-matched.
  3. POPULATION BALANCE — the four districts' live Census 2020 populations are
     fetched and asserted within a tolerance of each other. De Witt's board
     districts are a legal apportionment, so a transcription error big enough
     to move a precinct between districts would show as an imbalance. This is
     a sanity check rather than a proof (the county prints no district totals
     to match against, unlike Grundy and Henry), and the tolerance is stated
     below rather than tuned to whatever the current numbers happen to be.

"SANTA ANNA" IS THREE PRECINCTS. The county writes the township bare where it
means all of its numbered precincts; the layer carries SANTA ANNA 1, 2 and 3.
The expansion is declared explicitly below, not inferred, and the partition
check is what proves it complete.

Regenerate when the county re-precincts (the guards fail loudly if the
23-name fabric changes) or reapportions (next due after the 2030 census).

Usage:
    python3 scripts/build_dewitt_board_districts.py
    python3 scripts/build_dewitt_board_districts.py --check
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    HEADERS, REQUEST_TIMEOUT, point_in_rings,
)
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    make_fail,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "dewitt-county-board-districts.json")

PRECINCT_URL = ("https://services.arcgis.com/4YineAQdtmx0tv46/arcgis/rest/services/"
                "ElectionPrecincts_DeWittIL/FeatureServer/0/query")
ROSTER_URL = "https://www.dewittcountyil.gov/government/county_board.php"
SOURCE_LABEL = ("composed from the county's own precinct GIS per the district "
                "composition the county publishes on its County Board page")

# Census 2020 voting districts — the same fabric the county's precinct layer
# is built from, used only to measure the population balance check.
CENSUS_VTD_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "tigerWMS_Census2020/MapServer/58/query")   # 58 = Voting Districts
STATE_FIPS = "17"
COUNTY_FIPS = "039"

# The composition exactly as the county states it, expanded where the county
# writes a township bare. Nothing here is inferred from geometry.
DISTRICTS = {
    "A": ["WAYNESVILLE", "BARNETT", "TUNBRIDGE", "WAPELLA", "CLINTONIA 1", "CLINTONIA 2"],
    "B": ["WILSON", "RUTLEDGE", "SANTA ANNA 1", "SANTA ANNA 2", "SANTA ANNA 3",
          "HARP", "DEWITT", "NIXON"],
    "C": ["TEXAS", "CREEK", "CLINTONIA 7", "CLINTONIA 8", "CLINTONIA 9"],
    "D": ["CLINTONIA 3", "CLINTONIA 4", "CLINTONIA 5", "CLINTONIA 6"],
}
EXPECT_PRECINCTS = 23
# Each district elects three members, so an apportionment balances on
# population. 20% is deliberately loose — it is a transcription smoke test,
# not a Voting Rights Act analysis, and a single misplaced precinct in a
# county this size moves a district by far more.
MAX_POP_SPREAD = 0.20


fail = make_fail("dewitt-board")


def norm(name):
    return " ".join(str(name or "").upper().split())


def fetch_precincts():
    require_robots_once(PRECINCT_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-dewitt-board-districts")
    resp = requests.get(PRECINCT_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "1=1", "outFields": "NAME20", "returnGeometry": "true",
        "outSR": "4326", "resultRecordCount": "100", "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if not feats:
        fail("county precinct service returned no features")
    return feats


def fetch_vtd_populations():
    """{precinct name: POP100} from the Census 2020 voting-district layer."""
    require_robots_once(CENSUS_VTD_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-dewitt-board-districts")
    resp = requests.get(CENSUS_VTD_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "BASENAME,NAME,POP100", "returnGeometry": "false", "f": "json",
    })
    resp.raise_for_status()
    out = {}
    for feat in (resp.json() or {}).get("features") or []:
        a = feat.get("attributes") or {}
        # BASENAME is the bare precinct name; NAME appends " Voting District"
        name = a.get("BASENAME") or re.sub(r"\s+Voting District$", "", a.get("NAME") or "")
        if name and a.get("POP100") is not None:
            out[norm(name)] = int(a["POP100"])
    return out


def interior_point(geom):
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    p = geom.representative_point()
    return p.y, p.x


def rings_of(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    return [r for poly in geometry["coordinates"] for r in poly]


def main():
    # Local, not module scope: this module's composition constant is
    # imported by the ROSTER builder, whose CI job installs no geometry
    # stack. Keep the heavy imports on the path that needs them.
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()

    # ---- check 1: the composition is a partition, before any network call
    assigned = [norm(n) for names in DISTRICTS.values() for n in names]
    if len(assigned) != len(set(assigned)):
        dupes = sorted({n for n in assigned if assigned.count(n) > 1})
        fail("the composition names these precincts more than once: %s" % ", ".join(dupes))
    if len(assigned) != EXPECT_PRECINCTS:
        fail("the composition names %d precincts, the county runs %d"
             % (len(assigned), EXPECT_PRECINCTS))

    feats = fetch_precincts()
    by_name = {}
    for f in feats:
        key = norm((f.get("properties") or {}).get("NAME20"))
        if not key:
            continue
        if key in by_name:
            fail("the precinct layer carries two features named %r" % key)
        by_name[key] = f
    if len(by_name) != EXPECT_PRECINCTS:
        fail("the precinct layer carries %d precincts, expected %d — the county "
             "re-precincted; re-read its composition before rebuilding"
             % (len(by_name), EXPECT_PRECINCTS))

    # ---- check 2: every composed name exists, and every precinct is composed
    missing = sorted(set(assigned) - set(by_name))
    if missing:
        fail("the composition names precincts the layer does not have: %s" % ", ".join(missing))
    unassigned = sorted(set(by_name) - set(assigned))
    if unassigned:
        fail("the layer has precincts no district claims: %s" % ", ".join(unassigned))

    # ---- check 3: population balance
    pops = fetch_vtd_populations()
    district_pop = {}
    for district, names in DISTRICTS.items():
        vals = [pops.get(norm(n)) for n in names]
        if any(v is None for v in vals):
            unknown = [n for n, v in zip(names, vals) if v is None]
            fail("no Census 2020 population for: %s" % ", ".join(unknown))
        district_pop[district] = sum(vals)
    total = sum(district_pop.values())
    mean = total / float(len(district_pop))
    spread = max(abs(v - mean) for v in district_pop.values()) / mean
    if spread > MAX_POP_SPREAD:
        fail("districts are unbalanced by %.1f%% (%s) — beyond the %.0f%% a real "
             "apportionment would allow, so the composition is suspect"
             % (spread * 100,
                ", ".join("%s=%d" % kv for kv in sorted(district_pop.items())),
                MAX_POP_SPREAD * 100))

    # ---- dissolve
    features = []
    for district in sorted(DISTRICTS):
        parts = [shape(by_name[norm(n)]["geometry"]).buffer(0) for n in DISTRICTS[district]]
        merged = unary_union(parts)
        if merged.is_empty:
            fail("district %s dissolved to an empty geometry" % district)
        features.append({
            "type": "Feature",
            "properties": {"district": district, "precincts": len(DISTRICTS[district]),
                           "pop2020": district_pop[district]},
            "geometry": mapping(merged),
        })

    # ---- verify the SHIPPED geometry with the app's own even-odd test:
    # each precinct's interior point must land in exactly its own district
    for district, names in DISTRICTS.items():
        for name in names:
            lat, lon = interior_point(shape(by_name[norm(name)]["geometry"]).buffer(0))
            hits = [f["properties"]["district"] for f in features
                    if point_in_rings(lat, lon, rings_of(f["geometry"]))]
            if hits != [district]:
                fail("precinct %s lands in %s, expected only %s" % (name, hits or "no district", district))

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL,
            "rosterUrl": ROSTER_URL,
            "note": ("De Witt publishes no board-district GIS; these are the county's "
                     "own precincts dissolved per the composition it prints for every "
                     "board member. No precinct is split."),
        },
        "features": features,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"

    summary = ", ".join("%s=%d precincts/%d people" % (f["properties"]["district"],
                                                       f["properties"]["precincts"],
                                                       f["properties"]["pop2020"])
                        for f in features)
    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s does not exist" % OUT_PATH)
        with open(OUT_PATH, encoding="utf-8") as f:
            if f.read() != body:
                fail("%s differs from a fresh build" % OUT_PATH)
        print("dewitt-board: OK — matches a fresh build (%s; spread %.1f%%)" % (summary, spread * 100))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("dewitt-board: wrote %s — 4 districts (%s), total %d, spread %.1f%%"
          % (OUT_PATH, summary, total, spread * 100))


if __name__ == "__main__":
    main()
