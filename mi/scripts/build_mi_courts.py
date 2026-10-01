#!/usr/bin/env python3
"""
Michigan's Court of Appeals districts and circuit courts, as unions of whole
counties.

Michigan elects its judges by district (Const. 1963 art. 6): Court of Appeals
judges by appellate district (art. 6 s. 8), circuit judges by circuit (s. 11).
No agency publishes either boundary as geometry. The ArcGIS Online catalogue
answered ten queries on 2026-10-01 with no government court layer, and the
state court system's own site (www.courts.michigan.gov) publishes
`User-agent: *` / `Disallow: /`, so it is not read. Both boundaries are written
into statute as lists of whole counties, so this file draws no new line: every
district and every circuit is a union of the counties the app already ships in
data/app/state-counties.json.

THE COMPOSITION HAS TWO WITNESSES THAT AGREE COUNTY FOR COUNTY, read 2026-10-01
from the Legislature's own host (one request each):

  1. The Michigan Compiled Laws, chapter 600 (Revised Judicature Act), as the
     Legislature publishes it in XML, complete through PA 103 of 2026:
     MCL 600.302 for the four appellate districts and MCL 600.502-600.549i for
     the 57 circuits.
  2. The Michigan Manual 2025-2026, Chapter V (pp. 453-454 for the appellate
     districts, pp. 468-469 for the circuits, and the county column of the
     circuit judges table on pp. 471-472).

Five circuit sections are written conditionally ("if county X approves"):
5th/56th (Barry | Eaton), 33rd/57th (Charlevoix | Emmet) and 40th/54th
(Lapeer | Tuscola). The statute alone does not say whether the approvals
happened. The Manual lists the split form in force, with a judge seated in
each circuit, and that is what is drawn. Several sections carry dated clauses
("Beginning July 1, 2022"); the later clause is the one the Manual shows.

The Legislature's host refuses this project's token at the page and serves a
browser User-Agent; its robots.txt answers 404 (no rules), and its own
Automated Data Collection Policy permits automated collection at up to one
request per second. Nothing here fetches anything: the composition is written
below, and re-reading it is an annual WATCH.md check, not a job.

Gates (the build refuses to write unless all hold):
  * exactly 4 districts and 57 circuits;
  * every one of the 83 counties assigned exactly once at each level, by
    name, against the shipped county file;
  * every union's exterior segments chain into closed rings with none left
    over (the county file shares exact segments between neighbours, so an
    open chain means it stopped being one consistent fetch);
  * a grid of points inside every county lands in its own district or
    circuit and in no other.

Usage:
    python3 mi/scripts/build_mi_courts.py            # write both files
    python3 mi/scripts/build_mi_courts.py --check    # verify both shipped files
"""

import argparse
import json
import os
import sys

INSTANCE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTIES_FILE = os.path.join(INSTANCE, "data", "app", "state-counties.json")
COA_FILE = os.path.join(INSTANCE, "data", "app", "mi-court-of-appeals-districts.json")
CIRCUIT_FILE = os.path.join(INSTANCE, "data", "app", "mi-circuit-courts.json")

EXPECT_COUNTIES = 83
EXPECT_DISTRICTS = 4
EXPECT_CIRCUITS = 57

# MCL 600.302, witnessed by the Michigan Manual 2025-2026 pp. 453-454.
COA_DISTRICTS = {
    1: (
        "Branch", "Hillsdale", "Kalamazoo", "Lenawee", "Monroe", "St. Joseph",
        "Wayne",
    ),
    2: (
        "Genesee", "Macomb", "Oakland",
    ),
    3: (
        "Allegan", "Barry", "Berrien", "Calhoun", "Cass", "Eaton", "Ionia",
        "Jackson", "Kent", "Mason", "Montcalm", "Muskegon", "Newaygo", "Oceana",
        "Ottawa", "Van Buren", "Washtenaw",
    ),
    4: (
        "Alcona", "Alger", "Alpena", "Antrim", "Arenac", "Baraga", "Bay", "Benzie",
        "Charlevoix", "Cheboygan", "Chippewa", "Clare", "Clinton", "Crawford",
        "Delta", "Dickinson", "Emmet", "Gladwin", "Gogebic", "Grand Traverse",
        "Gratiot", "Houghton", "Huron", "Ingham", "Iosco", "Iron", "Isabella",
        "Kalkaska", "Keweenaw", "Lake", "Lapeer", "Leelanau", "Livingston", "Luce",
        "Mackinac", "Manistee", "Marquette", "Mecosta", "Menominee", "Midland",
        "Missaukee", "Montmorency", "Ogemaw", "Ontonagon", "Osceola", "Oscoda",
        "Otsego", "Presque Isle", "Roscommon", "Saginaw", "Sanilac", "Schoolcraft",
        "Shiawassee", "St. Clair", "Tuscola", "Wexford",
    ),
}

# MCL 600.502-600.549i (one section per circuit), witnessed by the Michigan
# Manual 2025-2026 pp. 468-469 and 471-472.
CIRCUITS = {
    1: ("MCL 600.502", ("Hillsdale",)),
    2: ("MCL 600.503", ("Berrien",)),
    3: ("MCL 600.504", ("Wayne",)),
    4: ("MCL 600.505", ("Jackson",)),
    5: ("MCL 600.506", ("Barry",)),
    6: ("MCL 600.507", ("Oakland",)),
    7: ("MCL 600.508", ("Genesee",)),
    8: ("MCL 600.509", ("Ionia", "Montcalm")),
    9: ("MCL 600.510", ("Kalamazoo",)),
    10: ("MCL 600.511", ("Saginaw",)),
    11: ("MCL 600.512", ("Alger", "Luce", "Mackinac", "Schoolcraft")),
    12: ("MCL 600.513", ("Baraga", "Houghton", "Keweenaw")),
    13: ("MCL 600.514", ("Antrim", "Grand Traverse", "Leelanau")),
    14: ("MCL 600.515", ("Muskegon",)),
    15: ("MCL 600.516", ("Branch",)),
    16: ("MCL 600.517", ("Macomb",)),
    17: ("MCL 600.518", ("Kent",)),
    18: ("MCL 600.519", ("Bay",)),
    19: ("MCL 600.520", ("Benzie", "Manistee")),
    20: ("MCL 600.521", ("Ottawa",)),
    21: ("MCL 600.522", ("Isabella",)),
    22: ("MCL 600.523", ("Washtenaw",)),
    23: ("MCL 600.524", ("Alcona", "Arenac", "Iosco", "Oscoda")),
    24: ("MCL 600.525", ("Sanilac",)),
    25: ("MCL 600.526", ("Marquette",)),
    26: ("MCL 600.527", ("Alpena", "Montmorency")),
    27: ("MCL 600.528", ("Lake", "Newaygo")),
    28: ("MCL 600.529", ("Missaukee", "Wexford")),
    29: ("MCL 600.530", ("Clinton", "Gratiot")),
    30: ("MCL 600.531", ("Ingham",)),
    31: ("MCL 600.532", ("St. Clair",)),
    32: ("MCL 600.533", ("Gogebic", "Ontonagon")),
    33: ("MCL 600.534", ("Charlevoix",)),
    34: ("MCL 600.535", ("Ogemaw", "Roscommon")),
    35: ("MCL 600.536", ("Shiawassee",)),
    36: ("MCL 600.537", ("Van Buren",)),
    37: ("MCL 600.538", ("Calhoun",)),
    38: ("MCL 600.539", ("Monroe",)),
    39: ("MCL 600.540", ("Lenawee",)),
    40: ("MCL 600.541", ("Lapeer",)),
    41: ("MCL 600.542", ("Dickinson", "Iron", "Menominee")),
    42: ("MCL 600.543", ("Midland",)),
    43: ("MCL 600.544", ("Cass",)),
    44: ("MCL 600.545", ("Livingston",)),
    45: ("MCL 600.546", ("St. Joseph",)),
    46: ("MCL 600.547", ("Crawford", "Kalkaska", "Otsego")),
    47: ("MCL 600.548", ("Delta",)),
    48: ("MCL 600.549", ("Allegan",)),
    49: ("MCL 600.549a", ("Mecosta", "Osceola")),
    50: ("MCL 600.549b", ("Chippewa",)),
    51: ("MCL 600.549c", ("Mason", "Oceana")),
    52: ("MCL 600.549d", ("Huron",)),
    53: ("MCL 600.549e", ("Cheboygan", "Presque Isle")),
    54: ("MCL 600.549f", ("Tuscola",)),
    55: ("MCL 600.549g", ("Clare", "Gladwin")),
    56: ("MCL 600.549h", ("Eaton",)),
    57: ("MCL 600.549i", ("Emmet",)),
}


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suffix)


def county_list(names):
    """'Oakland County', or 'Alger, Luce, Mackinac and Schoolcraft counties'."""
    if len(names) == 1:
        return "%s County" % names[0]
    return "%s and %s counties" % (", ".join(names[:-1]), names[-1])


def rings_of(geom):
    if geom["type"] == "Polygon":
        return [list(r) for r in geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return [list(r) for poly in geom["coordinates"] for r in poly]
    raise SystemExit("unexpected geometry type %s" % geom["type"])


def in_ring(pt, ring):
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


def point_in_geom(pt, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if in_ring(pt, poly[0]) and not any(in_ring(pt, hole) for hole in poly[1:]):
            return True
    return False


def dissolve(geoms):
    """Union of whole counties: drop every segment walked twice (a county line
    inside the union), chain the rest into closed rings, then nest them. The
    metro-outline dissolve, generalised from Wisconsin's two-county version to
    any number of counties."""
    if len(geoms) == 1:
        return geoms[0]
    counts, seg_pts = {}, {}
    for geom in geoms:
        for ring in rings_of(geom):
            for i in range(len(ring) - 1):
                a, b = tuple(ring[i][:2]), tuple(ring[i + 1][:2])
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                counts[key] = counts.get(key, 0) + 1
                seg_pts[key] = (a, b)
    adj, exterior = {}, 0
    for key, n in counts.items():
        if n > 2:
            raise SystemExit("FATAL: a segment is walked %d times; the county file "
                             "has overlapping counties" % n)
        if n != 1:
            continue
        exterior += 1
        a, b = seg_pts[key]
        adj.setdefault(a, []).append((key, b))
        adj.setdefault(b, []).append((key, a))

    used, rings, walked = set(), [], 0
    for seed in sorted(k for k, n in counts.items() if n == 1):
        if seed in used:
            continue
        start, cur = seg_pts[seed]
        used.add(seed)
        walked += 1
        ring = [list(start), list(cur)]
        while cur != start:
            nxt = None
            for key, pt in adj.get(cur, ()):
                if key not in used:
                    nxt = (key, pt)
                    break
            if nxt is None:
                raise SystemExit("FATAL: open chain dissolving a county union; the "
                                 "county file is no longer topologically consistent")
            used.add(nxt[0])
            walked += 1
            cur = nxt[1]
            ring.append(list(cur))
        rings.append(ring)
    if walked != exterior:
        raise SystemExit("FATAL: dissolve dropped exterior segments (%d walked of %d)"
                         % (walked, exterior))

    # Nest: a ring inside an odd number of others is a hole of the smallest
    # outer ring holding it. The test point is the midpoint of the ring's first
    # segment, which lies on no other ring because every exterior segment is
    # walked exactly once.
    def probe(ring):
        return ((ring[0][0] + ring[1][0]) / 2.0, (ring[0][1] + ring[1][1]) / 2.0)

    def area(ring):
        return abs(sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
                       for i in range(len(ring) - 1))) / 2.0

    containers = []
    for i, ring in enumerate(rings):
        p = probe(ring)
        containers.append([j for j, other in enumerate(rings) if j != i and in_ring(p, other)])
    outers = [i for i in range(len(rings)) if len(containers[i]) % 2 == 0]
    polys = {i: [rings[i]] for i in outers}
    for i in range(len(rings)):
        if i in polys:
            continue
        holders = [j for j in containers[i] if j in polys]
        if not holders:
            raise SystemExit("FATAL: a hole sits inside no outer ring")
        polys[min(holders, key=lambda j: area(rings[j]))].append(rings[i])
    parts = [polys[i] for i in sorted(polys, key=lambda i: -area(rings[i]))]
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def grid_points(geom, n=7):
    """Up to n*n points of a regular grid over the geometry's box that fall
    inside it, so each county is tested at many places rather than one."""
    xs = [p[0] for r in rings_of(geom) for p in r]
    ys = [p[1] for r in rings_of(geom) for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pts = []
    for i in range(n):
        for j in range(n):
            pt = (x0 + (x1 - x0) * (i + 0.5) / n, y0 + (y1 - y0) * (j + 0.5) / n)
            if point_in_geom(pt, geom):
                pts.append(pt)
    return pts


def bbox(geom):
    xs = [p[0] for r in rings_of(geom) for p in r]
    ys = [p[1] for r in rings_of(geom) for p in r]
    return min(xs), min(ys), max(xs), max(ys)


def partition(by_name, groups, what):
    seen = {}
    for key, names in groups.items():
        for name in names:
            if name not in by_name:
                raise SystemExit("%s %s names %r, which is not a county in the file"
                                 % (what, key, name))
            if name in seen:
                raise SystemExit("%s: %s is in both %s and %s" % (what, name, seen[name], key))
            seen[name] = key
    missing = sorted(set(by_name) - set(seen))
    if missing:
        raise SystemExit("%s: counties in no group: %s" % (what, ", ".join(missing)))
    return seen


def containment(by_name, owner, features, key_prop, what):
    """Every grid point inside a county lands in its own group and no other."""
    boxes = [(f, bbox(f["geometry"])) for f in features]
    tested = 0
    for name, feat in sorted(by_name.items()):
        pts = grid_points(feat["geometry"]) or []
        if not pts:
            raise SystemExit("containment gate: no grid point fell inside %s" % name)
        for pt in pts:
            hits = [f["properties"][key_prop] for f, (a, b, c, d) in boxes
                    if a <= pt[0] <= c and b <= pt[1] <= d and point_in_geom(pt, f["geometry"])]
            if hits != [owner[name]]:
                raise SystemExit("containment gate: a point in %s County landed in %s %r, "
                                 "expected only %r" % (name, what, hits, owner[name]))
            tested += 1
    return tested


def build():
    with open(COUNTIES_FILE) as fh:
        counties = json.load(fh)["features"]
    if len(counties) != EXPECT_COUNTIES:
        raise SystemExit("expected %d counties, found %d" % (EXPECT_COUNTIES, len(counties)))
    by_name = {}
    for feat in counties:
        name = feat["properties"].get("BASENAME")
        if not name or name in by_name:
            raise SystemExit("county file: missing or repeated BASENAME %r" % name)
        by_name[name] = feat

    if len(COA_DISTRICTS) != EXPECT_DISTRICTS or len(CIRCUITS) != EXPECT_CIRCUITS:
        raise SystemExit("expected %d districts and %d circuits"
                         % (EXPECT_DISTRICTS, EXPECT_CIRCUITS))
    coa_owner = partition(by_name, COA_DISTRICTS, "Court of Appeals district")
    circuit_owner = partition(by_name, {k: v[1] for k, v in CIRCUITS.items()}, "circuit")

    coa = []
    for district in sorted(COA_DISTRICTS):
        names = sorted(COA_DISTRICTS[district])
        coa.append({
            "type": "Feature",
            "properties": {
                "DISTRICT": district,
                "NAME": "Court of Appeals District %d" % district,
                "COUNTY_COUNT": len(names),
            },
            "geometry": dissolve([by_name[n]["geometry"] for n in names]),
        })

    circuits = []
    for number in sorted(CIRCUITS):
        statute, names = CIRCUITS[number]
        names = sorted(names)
        circuits.append({
            "type": "Feature",
            "properties": {
                "CIRCUIT": number,
                "NAME": "%s Circuit Court" % ordinal(number),
                "COUNTIES": county_list(names),
                "STATUTE": statute,
            },
            "geometry": dissolve([by_name[n]["geometry"] for n in names]),
        })

    n1 = containment(by_name, coa_owner, coa, "DISTRICT", "district")
    n2 = containment(by_name, circuit_owner, circuits, "CIRCUIT", "circuit")
    print("containment: %d points in 83 counties land in their own district; "
          "%d land in their own circuit" % (n1, n2))
    return ({"type": "FeatureCollection", "features": coa},
            {"type": "FeatureCollection", "features": circuits})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped files match a fresh build; write nothing")
    args = ap.parse_args()

    coa, circuits = build()
    pairs = ((COA_FILE, coa), (CIRCUIT_FILE, circuits))
    if args.check:
        bad = 0
        for path, built in pairs:
            with open(path) as fh:
                shipped = json.load(fh)
            if json.dumps(shipped, sort_keys=True) != json.dumps(built, sort_keys=True):
                print("FAIL: shipped %s differs from a fresh build" % os.path.basename(path),
                      file=sys.stderr)
                bad = 1
        if bad:
            sys.exit(1)
        print("check: both court files match the county file (%d districts, %d circuits)"
              % (len(coa["features"]), len(circuits["features"])))
        return

    for path, built in pairs:
        with open(path, "w") as fh:
            json.dump(built, fh, separators=(",", ":"))
        print("wrote %s: %d features, %.1f KB" % (os.path.relpath(path, INSTANCE),
              len(built["features"]), os.path.getsize(path) / 1024.0))


if __name__ == "__main__":
    main()
