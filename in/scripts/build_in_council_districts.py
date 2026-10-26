#!/usr/bin/env python3
"""Build in/data/app/in-council-districts.json: the county council district
lines Indiana's own mapping office publishes, one feature per district.

WHAT THIS DRAWS AND WHY. An Indiana county council has seven members: four
elected from districts and three by the whole county (IC 36-2-3-4). A reader
inside a county is owed the one district member whose district holds the
point, and only a drawn district says which. The county commissioners are
elected by the whole county from residency districts (IC 36-2-2-4), so a
commissioner's district decides nothing about who represents a point and
those lines are not drawn. Marion County has no county council: its
legislative body is the Indianapolis City-County Council, elected from 25
districts, and those lines are drawn here too.

THE SOURCE. The Indiana Geographic Information Office's statewide
Administrative Boundaries service, layer 4 (CountyCouncilPolygon), which
collects each county's own council districts. Measured 2026-10-15 it carries
493 features from 56 counties. What this builder does with them:

  * The label is free text and differs by county ("District 1", "CC1", "#1",
    "Area 1", "COUNTY COUNCIL DISTRICT 01", "Indianapolis 001"), so only the
    number is read, and each county must come out exactly 1..4 (Marion
    1..25) or the build fails.
  * Several counties file one district as many pieces (Hendricks 105 pieces
    for four districts, Madison 112). They are joined into one feature per
    district.
  * Two kinds of feature are not a council district and are left out, each
    recorded in DROP_LABELS: Noble's three "AT-LARGE" features, each the whole
    county, and Boone's "N.T." feature, a sliver measured at 0.02% of the
    county that carries no district number.
  * Clay County files three districts of its four, covering 37% of the
    county, so it is left out whole (LEFT_OUT_COUNTIES) rather than drawn in
    part: a reader in the missing district would be told they are in none.
  * Each county's districts are clipped to that county's outline in the
    app's own state-counties.json, so the district a point lands in is always
    in the county the County card names, and no point near a county line can
    fall in two counties' districts.

Then the whole file is simplified in one mapshaper run: vertices within
about a metre are snapped together and the result cleaned, so neighbouring
districts share one edge (without it mapshaper reported 740 self-crossings it
could not repair, measured 2026-10-15; with it, one), then Douglas-Peucker at
15 m, the method build_legislative_boundaries.py records the reason for. Two
gates run before anything is written: a 2,000-point agreement test against
the unsimplified districts, and the offline check below.

THE JOIN TO THE NAMES IS CHECKED, NOT ASSUMED. --check is offline: for every
drawn county the council roster (in-county-councils.json, or Indianapolis's
seats in in-city-officials.json for Marion) must carry a seat called
"District N" for each drawn district N, except where SEAT_NOT_NUMBERED records
that the certified results title the seat some other way. A card for such a
district says the results do not number its seat rather than guessing.

Usage:
    python3 in/scripts/build_in_council_districts.py          # fetch + rebuild
    python3 in/scripts/build_in_council_districts.py --check  # offline gate
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(INSTANCE)
APP = os.path.join(INSTANCE, "data", "app")
OUT = os.path.join(APP, "in-council-districts.json")
COUNTIES = os.path.join(APP, "state-counties.json")
COUNCILS = os.path.join(APP, "in-county-councils.json")
CITIES = os.path.join(APP, "in-city-officials.json")
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

SERVICE = ("https://gisdata.in.gov/server/rest/services/Hosted/"
           "Administrative_Boundaries_of_Indiana_Current/FeatureServer/4")
SOURCE_PAGE = ("https://gisdata.in.gov/server/rest/services/Hosted/"
               "Administrative_Boundaries_of_Indiana_Current/FeatureServer")
MAPSHAPER = "mapshaper@0.6.102"  # the pin build_legislative_boundaries.py uses
SIMPLIFY = ["dp", "keep-shapes", "interval=15"]
PRECISION = "0.000001"
PAGE = 200
MARION = "18097"
INDIANAPOLIS_GEOID = "1836003"

# Features that are not a council district, by (county, label). Each is
# measured and recorded rather than matched by a pattern, so a new odd label
# fails the build instead of being dropped quietly.
DROP_LABELS = {
    ("Noble", "AT-LARGE_1"): "the whole county, drawn for an at-large seat",
    ("Noble", "AT-LARGE_2"): "the whole county, drawn for an at-large seat",
    ("Noble", "AT-LARGE_3"): "the whole county, drawn for an at-large seat",
    ("Boone", "N.T."): "a sliver of 0.02% of the county with no district "
                       "number (measured 2026-10-15)",
}

# Counties whose filing cannot be drawn honestly, with the measurement.
LEFT_OUT_COUNTIES = {
    "Clay": "files districts 1 to 3 only, covering 37% of the county "
            "(measured 2026-10-15); a reader in district 4 would be told "
            "they are in no district",
}

# Drawn districts whose seat the certified results do not title "District N".
SEAT_NOT_NUMBERED = {
    ("Boone", "3"): "the 2024 results title the race \"Boone County Council "
                    "Dist 36\"",
}

# Counties the state's service does not carry, drawn from the county's own
# map server instead. Each entry names the layer, the field holding the
# district, a query clause where the layer holds more than council districts,
# and a "map" from the field's value to the district only where the value is
# not the number itself. Every entry was read on the date it records, with
# robots.txt read first by the same client.
OWN_SOURCES = {
    # Read 2026-10-26: the county's own field, "District 1".."District 4"; one
    # extra 252 sq ft piece of District 3 is merged by the dissolve.
    "Adams": {"layer": "https://adamsingis.adams.in.us/arcgis/rest/services/"
                       "General/County_Web/MapServer/24",
              "field": "PRECINCT"},
    # Read 2026-10-26: the county's "Delaware County Council Districts 2022"
    # (the service keeps an older "2012" name).
    "Delaware": {"layer": "https://services.arcgis.com/VyRjdyMziYNF5Bwe/arcgis/"
                          "rest/services/County_council_2012/FeatureServer/0",
                 "field": "COUNCIL_DI"},
    # Read 2026-10-26: the county's election layer holds every office; its four
    # "Porter County District N" features split the county exactly, while the
    # commissioner districts are three features named "(North)" and so on.
    "Porter": {"layer": "https://services6.arcgis.com/TQ2Al5QIvv4tMBL7/arcgis/"
                        "rest/services/ElectionGeography_public_27e9bb8eaa1148"
                        "d08269f6122529bc74/FeatureServer/0",
               "field": "districtname",
               "where": "districtname LIKE 'Porter County District _'"},
    # Read 2026-10-26: "County Council 2025", which the county's own council
    # district map (updated 2026-09-30) draws.
    "St. Joseph": {"layer": "https://services.arcgis.com/OjftlhRHkAABcyiF/arcgis/"
                            "rest/services/County_Council_2025/FeatureServer/0",
                   "field": "COUNCIL_1",
                   "map": {c: c for c in "ABCDEFGHI"}},
    # Read 2026-10-26: Vigo County GIS's council districts, last updated
    # 2026-05-29.
    "Vigo": {"layer": "https://services3.arcgis.com/TA4VkagxbBNgroMb/arcgis/"
                      "rest/services/CountyCouncilDist/FeatureServer/0",
             "field": "District"},
}

# Councils not elected from four numbered districts. Lake County's council has
# seven districts and St. Joseph's nine, lettered A to I (IC 36-2-3-4 sets the
# usual four-and-three; both counties are written into their own sections).
DISTRICTS = {
    "Lake": [str(i) for i in range(1, 8)],
    "St. Joseph": list("ABCDEFGHI"),
}

# Floors: 56 counties file to the state, Clay is left out, and five more are
# drawn from their own servers, so 60 are drawn.
MIN_COUNTIES = 60
DISTRICTS_PER_COUNTY = 4
MARION_DISTRICTS = 25
# How much of each county its districts must cover, measured against the
# app's own simplified county outline (the lowest measured was Perry's 99.09%).
MIN_COVER = 0.985
# Counties whose outline runs out into Lake Michigan, where a council district
# stops at the shore. The Census puts Porter County's land at 418.2 of its
# 521.8 square miles (80.1%); its own districts measured 80.45% on 2026-10-26.
SHORE_COVER = {"Porter": 0.80}
SAMPLES = 2000


def fail(msg):
    print("build-in-council-districts: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def district_number(county, label):
    """The district a feature's free-text label names, or None to drop it."""
    if (county, label) in DROP_LABELS:
        return None
    if county == "Marion":
        m = re.fullmatch(r"Indianapolis 0*(\d+)", label.strip())
    else:
        m = re.search(r"(\d+)(?:st|nd|rd|th)?(?:\s+District)?\s*$", label.strip())
    if not m:
        fail("%s County files a feature labelled %r, which names no district "
             "number this builder knows how to read. Record it in DROP_LABELS "
             "with its reason, or teach district_number() its form." % (county, label))
    return str(int(m.group(1)))


def expected_districts(county, fips):
    if fips == MARION:
        return [str(i) for i in range(1, MARION_DISTRICTS + 1)]
    return DISTRICTS.get(county) or [str(i) for i in range(1, DISTRICTS_PER_COUNTY + 1)]


def _dkey(d):
    d = str(d)
    return (0, int(d), "") if d.isdigit() else (1, 0, d)


def county_table():
    with open(COUNTIES, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = {}
    for f in doc["features"]:
        p = f["properties"]
        out[p["BASENAME"]] = (p["GEOID"], f["geometry"])
    return out


# --- stdlib geometry for the offline gate ----------------------------------
def _rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def _in_poly(pt, polys):
    x, y = pt
    for poly in polys:
        inside = False
        for ring in poly:
            n = len(ring)
            j = n - 1
            for i in range(n):
                xi, yi = ring[i][0], ring[i][1]
                xj, yj = ring[j][0], ring[j][1]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
        if inside:
            return True
    return False


def _model(features):
    out = []
    for f in features:
        polys = _rings(f["geometry"])
        xs = [c[0] for p in polys for r in p for c in r]
        ys = [c[1] for p in polys for r in p for c in r]
        p = f["properties"]
        out.append(((p["fips"], p["district"]), polys,
                    (min(xs), min(ys), max(xs), max(ys))))
    return out


def _hits(model, pt):
    return [k for k, polys, bb in model
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
            and _in_poly(pt, polys)]


def _sample(model, seed):
    xs = [bb[0] for _, _, bb in model] + [bb[2] for _, _, bb in model]
    ys = [bb[1] for _, _, bb in model] + [bb[3] for _, _, bb in model]
    rng = random.Random(seed)
    return [(rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
            for _ in range(SAMPLES)]


def check(doc):
    """The shipped bytes on their own, plus the join to the rosters."""
    problems = []
    feats = doc.get("features") or []
    by = {}
    for f in feats:
        p = f.get("properties") or {}
        for k in ("fips", "county", "district"):
            if not p.get(k):
                problems.append("a feature has no %s" % k)
        by.setdefault((p.get("fips"), p.get("county")), []).append(str(p.get("district")))
    if len(by) < MIN_COUNTIES:
        problems.append("only %d counties drawn (floor %d)" % (len(by), MIN_COUNTIES))
    for (fips, county), ds in sorted(by.items()):
        want = expected_districts(county, fips)
        if sorted(ds, key=_dkey) != want:
            problems.append("%s County's districts are %s, not %s"
                            % (county, ds, ", ".join(want)))
        if county in LEFT_OUT_COUNTIES:
            problems.append("%s County is drawn and recorded as left out" % county)
    with open(COUNCILS, encoding="utf-8") as fh:
        councils = json.load(fh)
    with open(CITIES, encoding="utf-8") as fh:
        cities = json.load(fh)
    for (fips, county), ds in sorted(by.items()):
        if fips == MARION:
            rec = cities.get(INDIANAPOLIS_GEOID) or {}
        else:
            rec = councils.get(fips) or {}
        seats = {s.get("seat") for s in rec.get("seats") or []}
        for d in ds:
            named = ("District %s" % d) in seats
            recorded = (county, d) in SEAT_NOT_NUMBERED
            if not named and not recorded:
                problems.append("%s County District %s has no seat of that name "
                                "in the roster" % (county, d))
            if named and recorded:
                problems.append("%s County District %s is named in the roster and "
                                "still recorded in SEAT_NOT_NUMBERED" % (county, d))
    model = _model(feats)
    doubled = sum(1 for pt in _sample(model, 2026) if len(_hits(model, pt)) > 1)
    if doubled:
        problems.append("%d of %d sampled points fell in two districts" % (doubled, SAMPLES))
    return problems, len(by), len(feats)


def fetch(session):
    feats, off = [], 0
    while True:
        r = session.get(SERVICE + "/query", params={
            "where": "1=1", "outFields": "dsplayname,source_originator,local_id",
            "outSR": "4326", "f": "geojson", "orderByFields": "objectid",
            "resultOffset": off, "resultRecordCount": PAGE}, timeout=120)
        r.raise_for_status()
        doc = r.json()
        if "error" in doc or "features" not in doc:
            fail("the service answered with no features: %s" % str(doc)[:200])
        feats += doc["features"]
        if len(doc["features"]) < PAGE:
            return feats
        off += PAGE


def fetch_own(session, county, spec):
    """One county's council districts from its own layer, as (district, geojson
    geometry) pairs."""
    from scraper_common import (  # noqa: PLC0415
        UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once)
    require_robots_once(spec["layer"], UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    out, off = [], 0
    while True:
        r = session.get(spec["layer"] + "/query", params={
            "where": spec.get("where", "1=1"), "outFields": spec["field"],
            "outSR": "4326", "f": "geojson", "resultOffset": off,
            "resultRecordCount": PAGE}, timeout=120)
        r.raise_for_status()
        doc = r.json()
        if "error" in doc or "features" not in doc:
            fail("%s County's own layer answered with no features: %s"
                 % (county, str(doc)[:200]))
        for f in doc["features"]:
            raw = (f.get("properties") or {}).get(spec["field"])
            value = str(raw).strip() if raw is not None else ""
            if "map" in spec:
                if value not in spec["map"]:
                    fail("%s County's own layer files %s=%r, which its map "
                         "does not name" % (county, spec["field"], value))
                d = spec["map"][value]
            else:
                m = re.search(r"(\d+)\s*$", value)
                if not m:
                    fail("%s County's own layer files %s=%r, which names no "
                         "district number" % (county, spec["field"], value))
                d = str(int(m.group(1)))
            if d is None:
                continue
            if f.get("geometry") is None:
                fail("%s County district %s has no geometry" % (county, d))
            out.append((d, f["geometry"]))
        if len(doc["features"]) < PAGE:
            return out
        off += PAGE


def build(session):
    from shapely.geometry import mapping, shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    raw = fetch(session)
    print("fetched %d features" % len(raw))
    counties = county_table()
    groups, seen_drops = {}, set()
    for f in raw:
        p = f["properties"]
        county = re.sub(r"\s+County$", "", (p.get("source_originator") or "").strip())
        label = (p.get("dsplayname") or "").strip()
        if county not in counties:
            fail("feature from %r, which is not a county in state-counties.json" % county)
        if county in LEFT_OUT_COUNTIES or county in OWN_SOURCES:
            continue
        d = district_number(county, label)
        if d is None:
            seen_drops.add((county, label))
            continue
        if f.get("geometry") is None:
            fail("%s County %r has no geometry" % (county, label))
        groups.setdefault((county, d), []).append(shape(f["geometry"]).buffer(0))
    for county, spec in sorted(OWN_SOURCES.items()):
        if county not in counties:
            fail("OWN_SOURCES names %r, which is not a county" % county)
        pieces = fetch_own(session, county, spec)
        print("%s County: %d features from its own layer" % (county, len(pieces)))
        for d, geom in pieces:
            groups.setdefault((county, d), []).append(shape(geom).buffer(0))
    for k in sorted(set(DROP_LABELS) - seen_drops):
        fail("DROP_LABELS records %s %r, which the service no longer files" % k)
    for c in sorted(LEFT_OUT_COUNTIES):
        if not any(re.sub(r"\s+County$", "", f["properties"]["source_originator"]) == c
                   for f in raw):
            fail("LEFT_OUT_COUNTIES records %s, which the service no longer files" % c)

    source, lines = [], []
    by_county = {}
    for (county, d), geoms in groups.items():
        by_county.setdefault(county, {})[d] = unary_union(geoms)
    for county in sorted(by_county):
        fips, cgeom = counties[county]
        outline = shape(cgeom).buffer(0)
        parts = by_county[county]
        union = unary_union(list(parts.values()))
        cover = union.intersection(outline).area / outline.area
        overlap = (sum(g.area for g in parts.values()) - union.area) / outline.area
        floor = SHORE_COVER.get(county, MIN_COVER)
        if cover < floor:
            fail("%s County's districts cover %.2f%% of the county (floor %.1f%%)"
                 % (county, 100 * cover, 100 * floor))
        if overlap > 0.001:
            fail("%s County's districts overlap over %.3f%% of the county"
                 % (county, 100 * overlap))
        lines.append("%s %.2f%%" % (county, 100 * cover))
        for d in sorted(parts, key=_dkey):
            g = parts[d].intersection(outline)
            g = g.buffer(0)
            if g.geom_type not in ("Polygon", "MultiPolygon"):
                polys = [x for x in getattr(g, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")]
                g = unary_union(polys)
            source.append({"type": "Feature",
                           "properties": {"fips": fips, "county": county, "district": d},
                           "geometry": mapping(g)})
    print("cover per county: " + ", ".join(lines))

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src.geojson")
        dst = os.path.join(tmp, "out.geojson")
        with open(src, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": source}, fh)
        subprocess.run(["npx", "-y", MAPSHAPER, src, "snap", "snap-interval=0.00001", "-clean", "-simplify"] + SIMPLIFY +
                       ["-o", "precision=" + PRECISION, "format=geojson", dst],
                       check=True, cwd=REPO_ROOT)
        with open(dst) as fh:
            built = json.load(fh)

    src_model, new_model = _model(source), _model(built["features"])
    agree = 0
    for pt in _sample(src_model, 2024):
        a, b = _hits(src_model, pt), _hits(new_model, pt)
        if a == b:
            agree += 1
    pct = 100.0 * agree / SAMPLES
    if pct < 99.5:
        fail("simplified districts agree with the source at %.2f%% of sampled "
             "points (need 99.5%%)" % pct)
    print("agreement %d/%d (%.2f%%)" % (agree, SAMPLES, pct))
    return built


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            doc = json.load(fh)
        problems, n, f = check(doc)
        if problems:
            fail("; ".join(problems))
        print("build-in-council-districts --check: OK — %d counties, %d districts, "
              "every district joined to a roster seat or recorded" % (n, f))
        return
    import requests  # noqa: PLC0415
    from scraper_common import (  # noqa: PLC0415
        UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, require_robots_once)
    session = requests.Session()
    session.headers.update(UA_HEADERS_ROSTER_BOT)
    require_robots_once(SERVICE, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    built = build(session)
    built["features"].sort(key=lambda f: (f["properties"]["county"],
                                          _dkey(f["properties"]["district"])))
    problems, n, f = check(built)
    if problems:
        fail("; ".join(problems))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(built, fh, separators=(",", ":"))
        fh.write("\n")
    print("build-in-council-districts: wrote %s — %d counties, %d districts, %d bytes"
          % (os.path.relpath(OUT, REPO_ROOT), n, f, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
