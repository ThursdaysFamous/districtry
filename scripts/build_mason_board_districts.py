#!/usr/bin/env python3
"""
Build data/app/mason-county-board-districts.json — Mason's 2 County Board
districts, DERIVED by dissolving TIGER county subdivisions per the composition
the county prints at the foot of its board roster.

WHY THIS EXISTS — Mason's only mapping surface is a WTH `tgis` parcel viewer
(masonil.wthgis.com), a raster map server with no REST feature service, so
there is no district layer to fetch. What the county does publish is two
composition lines under its member table:

    District 1 - Allens Grove, Crane Creek, Forest City, Manito, Mason City,
                 Pennsylvania, Salt Creek, and Sherman
    District 2 - Bath, Havana, Kilbourne, Lynchburg, and Quiver

WHY THE DERIVATION IS SOUND HERE — those are WHOLE TOWNSHIPS. No township is
split, so there is no line to interpret: every district edge is a Census
township edge. The build asserts the same three things Washington's, Marshall's
and De Witt's do:

  1. PARTITION — the two districts must name all 13 townships exactly once
     (8 + 5 = 13). A missing or doubled township fails the build.
  2. NAME MATCH — every name must resolve against TIGER's own township names.
  3. POPULATION BALANCE — each district elects FOUR members, so the districts
     are equal-membered and per-district population is the right basis (unlike
     Cass, whose 3/3/3/2 board must be measured per member). Measured spread is
     0.2% — 6,528 against 6,558 — which is what an apportionment onto whole
     townships looks like when it is done carefully.

THE COMPOSITION IS TRANSCRIBED, NOT SCRAPED, AND THAT IS WHY THERE IS NO
WEEKLY DRIFT CHECK. Mason's roster PDF is a SCAN. It carries a text layer, but
that layer is written in a non-embedded Helvetica whose encoding does not
survive extraction — pdfplumber and pdftotext both return line noise
("xRF# ISgH tlgP"), not text. Line noise is worse than no text layer, because
it parses: a scraper reading it would produce confident garbage. So the table
below is transcribed by hand from the scan (2026-08-02) and the weekly job
WATCHES THE SOURCE instead of re-reading it — see scripts/mason_roster_watch.py.

Usage:
    python3 scripts/build_mason_board_districts.py
    python3 scripts/build_mason_board_districts.py --check
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
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "mason-county-board-districts.json")

TOWNSHIP_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "tigerWMS_Census2020/MapServer/20/query")   # 20 = County Subdivisions
ROSTER_PAGE = "https://masoncountyil.gov/county-board/"
STATE_FIPS = "17"
COUNTY_FIPS = "125"
SOURCE_LABEL = ("TIGER county subdivisions dissolved per the whole-township "
                "composition the county prints under its board roster")

# Exactly as the county writes them, in the two "District n -" lines.
DISTRICTS = {
    "1": ["Allens Grove", "Crane Creek", "Forest City", "Manito", "Mason City",
          "Pennsylvania", "Salt Creek", "Sherman"],
    "2": ["Bath", "Havana", "Kilbourne", "Lynchburg", "Quiver"],
}
EXPECT_TOWNSHIPS = 13
SEATS_PER_DISTRICT = 4
# Four members per district, equal-membered. Loose on purpose — a transcription
# smoke test, not a Voting Rights Act analysis. Measured spread is 0.2%.
MAX_POP_SPREAD = 0.20


fail = make_fail("mason-board")


def norm(name):
    """Key a township name ignoring case, whitespace and punctuation, so a
    re-spacing at the source ("Allens Grove" / "AllensGrove") is not mistaken
    for a redistricting."""
    return re.sub(r"[^A-Z0-9]", "", str(name or "").upper())


def fetch_townships():
    require_robots_once(TOWNSHIP_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-build-mason-board-districts")
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
            "rosterUrl": ROSTER_PAGE,
            "note": ("Mason County's only mapping surface is a WTH parcel viewer "
                     "with no feature service; these are Census townships "
                     "dissolved per the composition the county prints under its "
                     "board roster. No township is split, so every district edge "
                     "is a township edge."),
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
        print("mason-board: OK — matches a fresh build (%s; spread %.1f%%)"
              % (summary, spread * 100))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("mason-board: wrote %s — 2 districts (%s), total %d, spread %.1f%%"
          % (OUT_PATH, summary, total, spread * 100))


if __name__ == "__main__":
    main()
