#!/usr/bin/env python3
"""
Build data/app/mn-swcd-districts.json — the ground each elected soil and water
conservation district (SWCD) supervisor answers for, dissolved from the
Secretary of State's own precinct layer.

WHAT AN SWCD IS. Minnesota's soil and water conservation districts (Minn.
Stat. ch. 103C) are special-purpose local governments, each governed by an
elected board of supervisors, normally five. They are NOT the watershed
districts and watershed management organizations already drawn by
build_mn_watershed_districts.py, whose managers are appointed; an SWCD
supervisor is on the general election ballot.

HOW A SUPERVISOR IS ELECTED DECIDES WHAT IS DRAWN. BWSR's "SWCD Board of
Supervisors" page (bwsr.state.mn.us/swcd-board-supervisors, read 2026-10-26)
states the two forms Minn. Stat. 103C.311 allows:
  * AT LARGE (subd. 1): the board divides the district into nomination
    districts a candidate must live in, but "all eligible voters throughout
    the area included in the SWCD are eligible to vote" for every seat. So
    the ground a supervisor answers for is the WHOLE SWCD, and the nomination
    districts are a residency rule, never a polygon here — drawing them would
    tell a reader one supervisor represents them when all five do.
  * BY DISTRICT (subd. 2): the SWCD chose to elect each supervisor from a
    supervisor district made of precincts. Those districts are drawn.

THE PRECINCT LAYER SAYS WHICH IS WHICH, AND THAT IS WHY IT IS THE SOURCE.
Every precinct in the Secretary of State's layer (the fabric mn_vtd_dissolve.py
reads) carries `swcdist` and `swcdist_n`, the soil and water ballot that
precinct votes. Measured 2026-10-26: 116 values. In seven counties — Anoka,
Carver, Dakota, Fillmore, Renville, Scott and Washington — the value differs
between precincts of one SWCD ("Anoka District 1" .. "Anoka District 5"),
which is a by-district election; everywhere else one value covers the whole
SWCD. Three counties hold two at-large SWCDs each (Otter Tail East and West,
Polk East and West, North and South St. Louis). That is 88 SWCDs and 116
polygons. Hennepin's and Ramsey's 557 precincts carry no value at all: both
districts are run by their counties, and BWSR's directory of 21 February 2023
lists staff and no board members for either, so neither has an elected
supervisor to draw.

A WITNESS THAT LOOKED RIGHT AND IS NOT ONE. The same BWSR page says supervisor
districts "must align with county commissioner districts". Compared precinct
by precinct on 2026-10-26, the supervisor district number equals the
commissioner district number on every precinct in Fillmore, Renville, Scott
and Washington, on 36 of 39 in Carver, and on 18 of 128 in Anoka and 54 of 144
in Dakota — both of which elect seven commissioners and five supervisors, so
the numbers cannot coincide there. That is a finding about the statute's
wording against seven-commissioner counties, not a gate, and none is built on
it.

GATES, each on the geometry that ships:
  1. partition — every precinct carries exactly one SWCD value except the
     declared Hennepin and Ramsey precincts, and each value lies in one county;
  2. no two polygons overlap at a point inside either;
  3. every county's proven-interior anchor lands in exactly one polygon of its
     own county, except the two declared counties, whose anchors must land in
     none.

Usage:
    python3 mn/scripts/build_mn_swcd_districts.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, HERE)

import mn_vtd_dissolve as vtd  # noqa: E402
import build_mn_commissioner_districts as cd  # noqa: E402  (interior points, shared simplify)

sys.path.insert(0, FLEET_SCRIPTS)
from scraper_common import require_robots_once  # noqa: E402

OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-swcd-districts.json")

EXPECT_POLYGONS = 116
EXPECT_SWCDS = 88
# Counties whose precincts carry no SWCD value, with the reason. A county that
# gains a value, or a new county without one, fails the build.
NO_ELECTED_SWCD = {
    "Hennepin": "Hennepin Conservation District is run by Hennepin County; "
                "BWSR's directory of 21 February 2023 lists its staff and no "
                "board members, and no precinct votes a supervisor",
    "Ramsey": "Ramsey County SWCD is run by Ramsey County; BWSR's directory "
              "of 21 February 2023 lists its staff and no board members, and "
              "no precinct votes a supervisor",
}
BY_DISTRICT_RE = re.compile(r"^(.+) District (\d+)$")


def main():
    vtd.require_robots([vtd.PRECINCT_QUERY], FLEET_SCRIPTS)
    require_robots_once(vtd.PRECINCT_QUERY, vtd.USER_AGENT)
    features = vtd.fetch_precincts(
        ["vtdid", "countyname", "countyfips", "swcdist", "swcdist_n"], geometry=True)

    # Gate 1 — the partition.
    groups, blank = {}, {}
    for feature in features:
        p = feature.get("properties") or {}
        county = (p.get("countyname") or "").strip()
        code = (p.get("swcdist") or "").strip()
        label = (p.get("swcdist_n") or "").strip()
        if not county:
            raise SystemExit("FATAL: a precinct names no county: %r" % p)
        if not code or not label:
            blank[county] = blank.get(county, 0) + 1
            continue
        g = groups.setdefault(code, {"label": label, "counties": set(),
                                     "fips": set(), "features": []})
        if g["label"] != label:
            raise SystemExit("FATAL: SWCD code %s is %r on one precinct and %r on "
                             "another" % (code, g["label"], label))
        g["counties"].add(county)
        g["fips"].add((p.get("countyfips") or "").strip())
        g["features"].append(feature)
    if set(blank) != set(NO_ELECTED_SWCD):
        raise SystemExit("FATAL: precincts with no SWCD value lie in %s; the "
                         "builder declares %s. Re-read BWSR's directory for the "
                         "difference before trusting either."
                         % (sorted(blank), sorted(NO_ELECTED_SWCD)))
    for code, g in sorted(groups.items()):
        if len(g["counties"]) != 1:
            raise SystemExit("FATAL: SWCD code %s (%s) spans %s; every SWCD this "
                             "builder knows lies in one county"
                             % (code, g["label"], sorted(g["counties"])))
    if len(groups) != EXPECT_POLYGONS:
        raise SystemExit("FATAL: %d SWCD values, expected %d" % (len(groups), EXPECT_POLYGONS))

    swcds = {}
    for code, g in groups.items():
        m = BY_DISTRICT_RE.match(g["label"])
        swcd = m.group(1) if m else g["label"]
        swcds.setdefault(swcd, []).append((code, int(m.group(2)) if m else None))
    for swcd, parts in sorted(swcds.items()):
        numbered = sorted(n for _c, n in parts if n is not None)
        if numbered and (len(numbered) != len(parts)
                         or numbered != list(range(1, len(numbered) + 1))):
            raise SystemExit("FATAL: %s mixes at-large and numbered values, or its "
                             "districts are not numbered from 1: %s" % (swcd, parts))
    if len(swcds) != EXPECT_SWCDS:
        raise SystemExit("FATAL: %d SWCDs, expected %d" % (len(swcds), EXPECT_SWCDS))
    by_district = sorted(s for s, parts in swcds.items() if parts[0][1] is not None)
    print("partition: %d precincts in %d polygons, %d SWCDs (%d elect by district: %s); "
          "%d precincts in %s vote no supervisor, as declared"
          % (len(features) - sum(blank.values()), len(groups), len(swcds),
             len(by_district), ", ".join(by_district), sum(blank.values()),
             " and ".join(sorted(blank))), file=sys.stderr)

    exact = {"type": "FeatureCollection", "features": []}
    for code in sorted(groups):
        polys = vtd.group_rings(vtd.dissolve(groups[code]["features"]))
        exact["features"].append({
            "type": "Feature", "properties": {"code": code},
            "geometry": ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                         else {"type": "MultiPolygon", "coordinates": polys}),
        })
    simple = cd.simplify_shared(exact)
    built = {}
    for feature in simple["features"]:
        code = str((feature.get("properties") or {}).get("code") or "")
        if code not in groups or code in built:
            raise SystemExit("FATAL: mapshaper returned an unknown or repeated code %r" % code)
        built[code] = feature["geometry"]

    # Gate 2 — no overlap.
    for code, geom in sorted(built.items()):
        points = cd.interior_points(geom, 12)
        if len(points) < 4:
            raise SystemExit("FATAL: could not seed interior points in SWCD %s" % code)
        for lng, lat in points:
            hits = [c for c, g in built.items() if vtd.point_in_geom(lng, lat, g)]
            if hits != [code]:
                raise SystemExit("FATAL: %.5f,%.5f is inside %s and %s"
                                 % (lng, lat, code, [h for h in hits if h != code]))
    print("overlap: no point inside any of the %d polygons is inside a second one"
          % len(built), file=sys.stderr)

    # Gate 3 — containment.
    sys.path.insert(0, HERE)
    from build_metro_outline import INSIDE  # noqa: PLC0415
    if len(INSIDE) != 87:
        raise SystemExit("FATAL: build_metro_outline.INSIDE holds %d anchors, expected 87" % len(INSIDE))
    county_of = {code: next(iter(g["counties"])) for code, g in groups.items()}
    placed = declared = 0
    for place, (lat, lng) in sorted(INSIDE.items()):
        hits = [c for c, g in built.items() if vtd.point_in_geom(lng, lat, g)]
        if any(c in place for c in NO_ELECTED_SWCD):
            if hits:
                raise SystemExit("FATAL: %s is declared to have no elected SWCD and its "
                                 "anchor lands in %s" % (place, hits))
            declared += 1
            continue
        if len(hits) != 1 or county_of[hits[0]] not in place:
            if place in cd.ANCHORS_OUTSIDE_FABRIC and not hits:
                declared += 1
                continue
            raise SystemExit("FATAL: %s's anchor lands in %s"
                             % (place, [(h, county_of[h]) for h in hits]))
        placed += 1
    print("containment: %d county anchors land in exactly one polygon of their own "
          "county; %d declared to land in none" % (placed, declared), file=sys.stderr)

    out = {"type": "FeatureCollection", "features": []}
    for code in sorted(built, key=lambda c: (county_of[c], c)):
        label = groups[code]["label"]
        m = BY_DISTRICT_RE.match(label)
        out["features"].append({
            "type": "Feature",
            "properties": {
                "code": code,
                "swcd": m.group(1) if m else label,
                "county": county_of[code],
                "countyFips": next(iter(groups[code]["fips"])),
                "district": int(m.group(2)) if m else None,
                "precincts": len(groups[code]["features"]),
            },
            "geometry": built[code],
        })
    with open(OUT_FILE, "w") as handle:
        json.dump(out, handle, separators=(",", ":"))
        handle.write("\n")
    print("mn-swcd-districts -> %s: %d polygons for %d SWCDs, %d bytes"
          % (os.path.relpath(OUT_FILE, INSTANCE), len(out["features"]), len(swcds),
             os.path.getsize(OUT_FILE)), file=sys.stderr)


if __name__ == "__main__":
    main()
