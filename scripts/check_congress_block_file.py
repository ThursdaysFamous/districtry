#!/usr/bin/env python3
"""Hold a shipped congress-districts.json to the Census Bureau's block file.

THE QUESTION. Each instance's congressional map is built from a TIGERweb
layer, and each builder's own gates compare the built file with that layer.
None of them asks whether the layer is the map the state's election used.
The Census Bureau answers that in a second product, the Block Equivalency
File (BEF) of each Congress: one row per 2020 census block naming the
district the state's own liaison reported for it. This script classifies the
internal point of every populated 2020 block against the shipped file and
compares the answer with the BEF's.

WHAT IT READS. The blocks (GEOID, internal point, 2020 population) come
through build_block_population.py's own fetch from TIGERweb, county by
county, and must sum to the state's 2020 count in that script's INSTANCES
row. The BEF is one zip for the whole country, read member by member without
unpacking it. The shipped file is read as it is on disk.

WHAT A DIFFERENCE MEANS. A block is assigned whole and the shipped line is
simplified, so a block whose internal point lies within a few metres of a
district line can land across the drawn line. --explain asks TIGERweb's
unsimplified layer about each differing point and measures the point's
distance to the nearest drawn edge, which tells that case from the other one
found on 2026-11-16: TIGERweb's own line putting a block's point in a
different district from the BEF.

THE TOLERANCE IS MEASURED. On 2026-11-16 the nine states that drew new maps
for the 120th Congress (AL, CA, FL, LA, NC, OH, TN, TX, UT) differed on 14 of
1,912,169 populated blocks, the worst state North Carolina at 5 of 174,988
(0.003%). The script fails above 1 block in 10,000, which a map swapped for
another passes by three orders of magnitude (Louisiana's two maps disagree on
about a quarter of the state).

This is an OPERATOR step, not a CI gate: it needs the network, shapely and
about a minute per million blocks. Run it after rebuilding a congressional
map, and again when the Bureau regenerates its file (it did for Missouri on
2026-10-07).

Usage:
  python3 scripts/check_congress_block_file.py --instance tx
  python3 scripts/check_congress_block_file.py --instance nc --instance tn --explain
  python3 scripts/check_congress_block_file.py --instance ca --zip /path/to/cd120.zip
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_block_population as blocks  # noqa: E402
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The Congress whose members sit from 3 January 2027 to 3 January 2029. The
# next Congress's file is published at its own address under a new name, so
# both constants change together.
CONGRESS = 120
BEF_URL = ("https://www2.census.gov/programs-surveys/decennial/rdo/mapping-files/"
           "2027/120-congressional-district-befs/cd120.zip")
LAYER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0"
FIELD = "CD%d" % CONGRESS
MAX_DIFFERING_SHARE = 1e-4


def read_zip(path):
    if path:
        with open(path, "rb") as fh:
            return fh.read()
    require_robots_once(BEF_URL, blocks.UA, headers={"User-Agent": blocks.UA},
                        label="check-congress-block-file")
    req = urllib.request.Request(BEF_URL, headers={"User-Agent": blocks.UA})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return resp.read()


def bef_rows(raw, fips):
    """{block GEOID: district} and the member file's own date, for one state."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = "CD%d_%s.txt" % (CONGRESS, fips)
        info = z.getinfo(name)
        text = z.read(name).decode("utf-8")
    rows = csv.reader(io.StringIO(text))
    head = next(rows)
    if head[0] != "GEOID" or head[-1] != "CDFP":
        raise SystemExit("%s: unexpected header %r" % (name, head))
    return {r[0]: r[-1] for r in rows if r}, "%04d-%02d-%02d" % info.date_time[:3]


def state_blocks(tag, cache):
    spec = blocks.INSTANCES[tag]
    path = os.path.join(cache, tag + ".csv") if cache else None
    if path and os.path.exists(path):
        with open(path, newline="") as fh:
            rows = [(g, float(x), float(y), int(p)) for g, x, y, p in csv.reader(fh)]
    else:
        names = blocks.county_names(spec)
        if len(names) != blocks.county_count(spec):
            raise SystemExit("%s: %d counties, expected %d"
                             % (tag, len(names), blocks.county_count(spec)))
        rows = []
        for county in sorted(names):
            rows += blocks.county_blocks(spec, county)
        if path:
            with open(path + ".tmp", "w", newline="") as fh:
                csv.writer(fh).writerows(rows)
            os.replace(path + ".tmp", path)
    total = sum(r[3] for r in rows)
    if total != spec["total"]:
        raise SystemExit("%s: the blocks sum to %d people, the state's 2020 count is %d"
                         % (tag, total, spec["total"]))
    return spec, rows


def edge_metres(geoms, x, y):
    """Distance from a point to the nearest drawn district edge, in metres,
    on a local scale (a degree of longitude is shorter by cos(latitude))."""
    import shapely  # noqa: PLC0415
    from shapely.geometry import Point  # noqa: PLC0415
    kx, ky = 111320.0 * math.cos(math.radians(y)), 111320.0
    best = float("inf")
    for geom in geoms:
        if geom.boundary.distance(Point(x, y)) > 0.01:
            continue
        local = shapely.transform(geom.boundary, lambda c: (c - [x, y]) * [kx, ky])
        best = min(best, local.distance(Point(0, 0)))
    return best


def check(tag, raw, cache, explain):
    import numpy  # noqa: PLC0415
    import shapely  # noqa: PLC0415
    from shapely.geometry import shape  # noqa: PLC0415
    spec, rows = state_blocks(tag, cache)
    bef, bef_date = bef_rows(raw, spec["state"])
    with open(os.path.join(ROOT, tag, "data", "app", "congress-districts.json")) as fh:
        feats = json.load(fh)["features"]
    if FIELD not in feats[0]["properties"]:
        raise SystemExit("%s: the shipped file numbers its districts with %s, not %s — it is "
                         "another Congress's map" % (tag, sorted(feats[0]["properties"]), FIELD))
    geoms = [shape(f["geometry"]) for f in feats]
    nums = [f["properties"][FIELD] for f in feats]
    tree = shapely.STRtree(geoms)
    points = shapely.points(numpy.array([r[1] for r in rows]), numpy.array([r[2] for r in rows]))
    hits = {}
    for p, g in zip(*[a.tolist() for a in tree.query(points, predicate="intersects")]):
        hits.setdefault(p, []).append(nums[g])
    differing, people_differing, by_district = [], 0, {}
    for i, (geoid, x, y, people) in enumerate(rows):
        want = bef.get(geoid)
        if want is None:
            raise SystemExit("%s: block %s is not in the Bureau's file" % (tag, geoid))
        by_district[want] = by_district.get(want, 0) + people
        got = hits.get(i, [])
        if got != [want]:
            differing.append((geoid, x, y, people, want, got))
            people_differing += people
    if sorted(by_district) != sorted(nums):
        raise SystemExit("%s: the Bureau's file names districts %s, the shipped file %s"
                         % (tag, sorted(by_district), sorted(nums)))
    ideal = spec["total"] / len(nums)
    print("%s: the Bureau's file for %s is dated %s and names %d districts holding %s to %s "
          "people each (an equal share is %.1f)"
          % (tag, spec["name"], bef_date, len(nums), format(min(by_district.values()), ","),
             format(max(by_district.values()), ","), ideal))
    print("%s: %s of %s populated blocks agree; %d differ, holding %s of %s people"
          % (tag, format(len(rows) - len(differing), ","), format(len(rows), ","),
             len(differing), format(people_differing, ","), format(spec["total"], ",")))
    for geoid, x, y, people, want, got in differing if explain else []:
        data = blocks.fetch(LAYER, {
            "geometry": "%s,%s" % (x, y), "geometryType": "esriGeometryPoint", "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects", "where": "STATE='%s'" % spec["state"],
            "outFields": FIELD, "returnGeometry": "false", "f": "json"})
        source = [f["attributes"][FIELD] for f in data.get("features") or []]
        print("%s:   block %s, population %d: the Bureau's file says %s, the shipped file %s, "
              "TIGERweb's own line %s; %.1f m from the nearest drawn edge"
              % (tag, geoid, people, want, " and ".join(got) or "no district",
                 " and ".join(source) or "no district", edge_metres(geoms, x, y)))
    share = len(differing) / len(rows)
    if share > MAX_DIFFERING_SHARE:
        print("%s: FAIL. %.4f%% of populated blocks differ, above the %.2f%% this script "
              "allows; the shipped file is not the map the Bureau's file describes"
              % (tag, 100 * share, 100 * MAX_DIFFERING_SHARE))
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--instance", action="append", required=True,
                    choices=sorted(t for t, s in blocks.INSTANCES.items()
                                   if any(m[0] == "congress-districts.json" for m in s["maps"])))
    ap.add_argument("--zip", help="a copy of the Bureau's zip already on disk; "
                                  "without it the file is downloaded and not kept")
    ap.add_argument("--cache", help="a directory to keep each state's blocks in between runs")
    ap.add_argument("--explain", action="store_true",
                    help="ask TIGERweb's unsimplified layer about each differing block")
    args = ap.parse_args()
    if args.cache:
        os.makedirs(args.cache, exist_ok=True)
    raw = read_zip(args.zip)
    print("the Bureau's file: %s bytes, SHA-256 %s"
          % (format(len(raw), ","), hashlib.sha256(raw).hexdigest()))
    ok = True
    for tag in args.instance:
        ok = check(tag, raw, args.cache, args.explain) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
