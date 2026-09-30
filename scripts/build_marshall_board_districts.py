#!/usr/bin/env python3
"""
Build data/app/marshall-county-board-districts.json — Marshall's 3 County Board
districts, DERIVED by dissolving TIGER county subdivisions per the composition
the county prints in its own board roster.

WHY THIS EXISTS — Marshall runs no public GIS. There is no ArcGIS org, no map
viewer, and the only district artifact the county publishes is the heading line
of its annual "Offices & Committees" roster PDF:

    DISTRICT #1 - Henry, Hopewell, LaPrairie, Saratoga, Whitefield

WHY THE DERIVATION IS SOUND HERE — those are WHOLE TOWNSHIPS. No township is
split between districts, so there is no line to interpret: every district edge
is a Census township edge. The build asserts the same three things Washington's
and De Witt's do:

  1. PARTITION — the three districts must name all 12 townships exactly once
     (5 + 4 + 3 = 12). A missing or doubled township fails the build.
  2. NAME MATCH — every name must resolve against TIGER's own township names.
  3. POPULATION BALANCE — each district elects FOUR members, so the districts
     are equal-membered and per-district population is the right basis here
     (unlike Cass, whose 3/3/3/2 board must be measured per member). Measured
     spread is 1.5%, reported on every run.

WHITESPACE IS NOT A NAME DIFFERENCE. The county writes "LaPrairie"; TIGER
writes "La Prairie". The keys therefore ignore whitespace and punctuation
entirely rather than carrying an alias table — no two Marshall townships differ
only in spacing, and if two ever collided the partition check above would fail
the build rather than silently merge them.

The roster scraper re-reads this same heading weekly and
scripts/build_marshall_board_roster.py fails if it stops matching the table
below — the De Witt pattern. Marshall is a good fit for it: composition and
roster are the same table in the same PDF, so a redistricting cannot reach the
roster without reaching the check.

Usage:
    python3 scripts/build_marshall_board_districts.py
    python3 scripts/build_marshall_board_districts.py --check
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
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "marshall-county-board-districts.json")

TOWNSHIP_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "tigerWMS_Census2020/MapServer/20/query")   # 20 = County Subdivisions
ROSTER_URL = "https://marshallcountyillinois.gov/directory/county-board/"
STATE_FIPS = "17"
COUNTY_FIPS = "123"
SOURCE_LABEL = ("TIGER county subdivisions dissolved per the whole-township "
                "composition the county prints in its board roster")

# Exactly as the county writes them, in the DISTRICT #n heading of the roster PDF.
DISTRICTS = {
    "1": ["Henry", "Hopewell", "LaPrairie", "Saratoga", "Whitefield"],
    "2": ["Bell Plain", "Bennington", "Evans", "Roberts"],
    "3": ["Lacon", "Richland", "Steuben"],
}
EXPECT_TOWNSHIPS = 12
SEATS_PER_DISTRICT = 4
# Four members per district, equal-membered, so per-district population is the
# right basis. Loose on purpose — a transcription smoke test, not a Voting
# Rights Act analysis.
MAX_POP_SPREAD = 0.20


fail = make_fail("marshall-board")


def norm(name):
    """Key a township name ignoring case, whitespace and punctuation, so the
    county's "LaPrairie" and TIGER's "La Prairie" are the same township."""
    return re.sub(r"[^A-Z0-9]", "", str(name or "").upper())


def fetch_townships():
    require_robots_once(TOWNSHIP_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-marshall-board-districts")
    resp = requests.get(TOWNSHIP_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, COUNTY_FIPS),
        "outFields": "BASENAME,POP100", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if not feats:
        fail("TIGERweb returned no county subdivisions")
    return feats


def rings_of(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    return [r for poly in geometry["coordinates"] for r in poly]


def interior_point(geom):
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    p = geom.representative_point()
    return p.y, p.x


def main():
    # Local, not module scope: this module's composition constant is
    # imported by the ROSTER builder, whose CI job installs no geometry
    # stack. Keep the heavy imports on the path that needs them.
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped file, write nothing")
    args = ap.parse_args()

    assigned = [norm(n) for names in DISTRICTS.values() for n in names]
    if len(assigned) != len(set(assigned)):
        dupes = sorted({n for n in assigned if assigned.count(n) > 1})
        fail("the composition names these townships more than once: %s" % ", ".join(dupes))
    if len(assigned) != EXPECT_TOWNSHIPS:
        fail("the composition names %d townships, the county has %d"
             % (len(assigned), EXPECT_TOWNSHIPS))

    feats = fetch_townships()
    by_name, pops, display = {}, {}, {}
    for f in feats:
        props = f.get("properties") or {}
        key = norm(props.get("BASENAME"))
        if not key:
            continue
        by_name[key] = f
        display[key] = props.get("BASENAME")
        if props.get("POP100") is not None:
            pops[key] = int(props["POP100"])
    if len(by_name) != EXPECT_TOWNSHIPS:
        fail("TIGER carries %d subdivisions for the county, expected %d"
             % (len(by_name), EXPECT_TOWNSHIPS))

    missing = sorted(set(assigned) - set(by_name))
    if missing:
        fail("the composition names townships TIGER does not have: %s" % ", ".join(missing))
    unassigned = sorted(display[k] for k in set(by_name) - set(assigned))
    if unassigned:
        fail("TIGER has townships no district claims: %s" % ", ".join(unassigned))

    district_pop = {}
    for district, names in DISTRICTS.items():
        vals = [pops.get(norm(n)) for n in names]
        if any(v is None for v in vals):
            fail("no Census 2020 population for: %s"
                 % ", ".join(n for n, v in zip(names, vals) if v is None))
        district_pop[district] = sum(vals)
    total = sum(district_pop.values())
    mean = total / float(len(district_pop))
    spread = max(abs(v - mean) for v in district_pop.values()) / mean
    if spread > MAX_POP_SPREAD:
        fail("districts are unbalanced by %.1f%% (%s) — beyond what a real "
             "apportionment would allow, so the composition is suspect"
             % (spread * 100, ", ".join("%s=%d" % kv for kv in sorted(district_pop.items()))))

    features = []
    for district in sorted(DISTRICTS):
        parts = [shape(by_name[norm(n)]["geometry"]).buffer(0) for n in DISTRICTS[district]]
        merged = unary_union(parts)
        if merged.is_empty:
            fail("district %s dissolved to an empty geometry" % district)
        features.append({
            "type": "Feature",
            "properties": {"district": district, "townships": len(DISTRICTS[district]),
                           "seats": SEATS_PER_DISTRICT, "pop2020": district_pop[district]},
            "geometry": mapping(merged),
        })

    for district, names in DISTRICTS.items():
        for name in names:
            lat, lon = interior_point(shape(by_name[norm(name)]["geometry"]).buffer(0))
            hits = [f["properties"]["district"] for f in features
                    if point_in_rings(lat, lon, rings_of(f["geometry"]))]
            if hits != [district]:
                fail("township %s lands in %s, expected only %s"
                     % (name, hits or "no district", district))

    payload = {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE_LABEL,
            "rosterUrl": ROSTER_URL,
            "note": ("Marshall County runs no public GIS; these are Census "
                     "townships dissolved per the composition printed in the "
                     "county's own board roster. No township is split, so every "
                     "district edge is a township edge."),
        },
        "features": features,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
    summary = ", ".join("%s=%d townships/%d people" % (f["properties"]["district"],
                                                       f["properties"]["townships"],
                                                       f["properties"]["pop2020"])
                        for f in features)
    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s does not exist" % OUT_PATH)
        with open(OUT_PATH, encoding="utf-8") as f:
            if f.read() != body:
                fail("%s differs from a fresh build" % OUT_PATH)
        print("marshall-board: OK — matches a fresh build (%s; spread %.1f%%)"
              % (summary, spread * 100))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("marshall-board: wrote %s — 3 districts (%s), total %d, spread %.1f%%"
          % (OUT_PATH, summary, total, spread * 100))


if __name__ == "__main__":
    main()
