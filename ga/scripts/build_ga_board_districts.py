#!/usr/bin/env python3
"""
Draw Georgia's county commission and county school board districts from the
maps the General Assembly's map office publishes, for the maps that passed the
precinct test in ga/data/source/county-map-check.json, and write:

  data/app/ga-commission-districts.json     the commission districts
  data/app/ga-school-board-districts.json   the school board districts
  data/app/ga-board-district-counties.json  each drawn county's maps: the
      seats each district elects, which seats the whole county elects, and
      which city school systems the school board map leaves out

This is step 3 of the Georgia launch plan, and like the map check it is an
occasional OPERATOR step, not a weekly job: run it again after the map check
is run again. The layers' coverage tests read the counties file, the cards
read it beside the roster (data/app/ga-county-officials.json, built weekly by
build_ga_county_officials.py), and --check holds all three files to the map
check's record offline in CI.

WHICH MAPS ARE DRAWN. Only those whose verdict in the record is PASSES, which
Adam chose with the plan ("county maps from the map office after a precinct
check", 2026-10-22): a map passes where every precinct that voted for one of
its districts lies in that district on the map, and no district failed
(check_ga_county_maps.py says how, and what a district no contest tested is).
Measured 2026-10-30, 111 commission maps and 106 school board maps pass,
counting the four "super district" maps (DeKalb's commission, Lowndes's
commission, and Harris's and Augusta-Richmond's school boards) apart from
their counties' other maps. Every other map is drawn nowhere, and gaps
ga-county-commission-district-lines and ga-school-board-district-lines say
why. A map
whose file has changed since the record was written is refused: its SHA-256
must be the record's.

THE LINES. Each map's shapes are dissolved by its DISTRICT field (the one
record with an empty DISTRICT, which covers the rest of the state, is not a
district), clipped to the county as data/app/state-counties.json draws it, so
a district never answers in a county the County card does not name, and
simplified by Douglas-Peucker at 5 m under the 8 m ceiling the legislative
builder uses, all of one body's districts in one run so that two districts
sharing an edge are drawn with one line. Ground the map leaves out of every
district stays out: measured 2026-10-30 that is a median of 0.09 km2 a county,
mostly along county lines that moved after the maps were drawn on the 2020
census's, and 443 km2 of Bryan County, which neither of its maps covers.

A SLIVER CUT OFF BY THE COUNTY LINE IS DROPPED. Clipping a map drawn on one
edition of a county line to another leaves detached parts along the line,
some no wider than a metre, and Douglas-Peucker at 5 m cannot hold a part
that thin under the 8 m ceiling. So a detached part lying wholly within the
fidelity ceiling (FIDELITY_CEILING_M) of the line it was cut along, the county
line and, for a school board, a city school system's line, is dropped, and
each run prints it. Measured 2026-10-30: eight parts of 0.02 to 406.8 m2, each
0.00 to 6.57 m wide on average, in Cobb, Fulton, Gwinnett, Jackson and
Taliaferro; the smallest detached part kept was 451.9 m2 before simplifying.
A district's largest part is always kept.

A SCHOOL BOARD MAP LEAVES OUT A CITY'S OWN SCHOOL SYSTEM, AND SO DOES THIS
LAYER. Twenty-one Georgia cities run their own school systems with their own
boards, and the county board is elected only outside them. The maps already
leave out all but slivers of them, measured 2026-10-30 at most 3.05 km2 in
one county (Laurens, beside Dublin's), so each county's school board districts
are drawn with the Census Bureau's current map of those systems (TIGERweb
School/MapServer/0) taken out, and the School District card and this layer
never name two school boards at one point. The schools on Fort Stewart are
not taken out: the Census Bureau maps them as a school district of their own,
and the county maps draw the post's ground in their districts, except Bryan's
(measured 2026-10-30 against TIGERweb's Fort Stewart School District: all of
its 479.4 km2 in Liberty and 26.9 km2 in Tattnall lie in those counties'
districts, and none of its 442.9 km2 in Bryan; Long's and Evans's maps are
not drawn).

WHO A DISTRICT ELECTS. Each district carries the seats on the county's ballot
it elects, named as the roster names them, so the card can find them there:
  - a seat whose contest the map check matched to the district, where the
    contest was voted by district, is that district's seat;
  - a seat whose contest was voted county-wide is the district's only when it
    is named the way the map's districts are named and carries the district's
    number ("District 2, Seat C" on Bulloch's commission, whose District 1
    seats are voted by district, and "Post 2" on Peach's).
    Glynn's at-large "Post 1" and "At large, Post 2" are voted county-wide on a
    map whose districts are "District 1" to "District 5", and Coweta's
    "At large, District 1" sits beside its "District 1", so neither is.
The county-wide seats left over, and those the check found no district for (a
chair, an at-large seat), are the seats the whole county elects. A contest
the officials builder sets aside (a city's board on the county ballot, a
public service commission seat) names no seat here either. The card also
reads the roster's own district numbers, so a seat first on a ballot after
the map check (a special election in a district no tested contest named)
still finds its district.

A district says how it is voted: "district" where a contest for it was voted
by district, "county-wide" where every contest for it was voted in every
precinct of the county (the district is where its member must live, and the
whole county votes), and nothing where no contest the check read named it.
`tested` is true where the precinct test passed the district itself.

SUPER DISTRICTS. A county's super district map overlaps its other districts,
so its features ship in the same file after the county's other districts, and
a point there is in one of each. The card names both. The map's highlight
lights the first district holding the point, so it lights the regular one.

Prerequisites: shapely, pyshp, pyproj, requests, and Node.js (mapshaper via
`npx mapshaper@<pinned>`, the version the legislative builder pins).

Usage:
    python3 ga/scripts/build_ga_board_districts.py --cache DIR
    python3 ga/scripts/build_ga_board_districts.py --check

DIR is the map check's cache (check_ga_county_maps.py --cache DIR), whose
maps/ folder already holds every map; anything missing is fetched there.
--check reads the record and the three files alone, without the network or
any geometry library, and confirms every passing map is drawn and nothing
else is, and that every seat list follows from the record.
"""

import argparse
import collections
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import build_ga_county_officials as off  # noqa: E402  (same instance tree)
import build_legislative_boundaries as blb  # noqa: E402
import check_ga_county_maps as cmap  # noqa: E402
assert os.path.dirname(os.path.abspath(cmap.__file__)) == _HERE, cmap.__file__

INSTANCE_ROOT = os.path.dirname(_HERE)
REPO_ROOT = os.path.dirname(INSTANCE_ROOT)
sys.path.append(os.path.join(REPO_ROOT, "scripts"))
import boundary_fidelity  # noqa: E402  (shared and stdlib only; appended, so it shadows nothing here)

APP = os.path.join(INSTANCE_ROOT, "data", "app")
RECORD = os.path.join(INSTANCE_ROOT, "data", "source", "county-map-check.json")
COUNTIES = os.path.join(APP, "state-counties.json")
OUT = {"commission": os.path.join(APP, "ga-commission-districts.json"),
       "school-board": os.path.join(APP, "ga-school-board-districts.json")}
OUT_COUNTIES = os.path.join(APP, "ga-board-district-counties.json")
BODY_KEY = {"commission": "commission", "school-board": "schoolBoard"}

SIMPLIFY = "interval=5"
FIDELITY_CEILING_M = blb.FIDELITY_CEILING_M
CITY_SCHOOLS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "School/MapServer/0/query")
# The Census Bureau names each city system "<city> City School District":
# 21 of them in Georgia, measured 2026-10-30.
CITY_SCHOOL_NAME = re.compile(r"^(.+) City School District$")
CITY_SCHOOLS_EXPECTED = 21
# A detached part lying wholly within the fidelity ceiling of the line it
# was cut along (the county's line, or for a school board a city system's)
# is a difference between two drawings of that line rather than ground the
# map gives the district, so it is dropped: the drawn edge then moves no
# further than the ceiling already lets it. Measured 2026-10-30, that is
# eight parts of 0.02 to 406.8 m2, each 0.00 to 6.57 m wide on average; the
# next part kept was 451.9 m2 before simplifying.

# A seat named for the whole county: what the card lists apart when the
# record leaves such a seat out (it was on no ballot the map check read).
COUNTYWIDE_LABEL = re.compile(r"^(chair|vice chair|president|sole commissioner|at large)\b|"
                              r"\bat large\b", re.I)


# --------------------------------------------------------------- the record

def passing(record):
    maps = [m for m in record["maps"] if m["verdict"] == "passes"]
    maps.sort(key=lambda m: (m["fips"], m["body"], m["super"]))
    return maps


def district_label(key):
    """A map district's name for a reader: "001" is "District 1", Crisp's
    commission "D1-2" is "District 1, Post 2"."""
    if key.isdigit():
        return "District %d" % int(key)
    m = re.fullmatch(r"D(\d+)-(\d+)", key)
    if m:
        return "District %d, Post %d" % (int(m.group(1)), int(m.group(2)))
    raise SystemExit("FAIL: a district key this builder cannot name: %r" % key)


def numbers(text):
    return [int(n) for n in re.findall(r"\d+", text)]


def scheme(label):
    """How a seat label names its district, up to its first number: "District
    #" for "District 2, Seat C", "Post #" for "Post 2", "At large, District #"
    for Coweta's at-large seat."""
    return re.sub(r"\d+.*$", "#", label)


def contest_seat(contest, fips, names):
    """The roster's label for the seat a contest names, or None when the
    officials builder would set the contest aside."""
    name = contest["contest"]
    county = names[fips]
    ckey = cmap.county_key(county)
    fixed = off.SEAT_NAMES.get((ckey, name))
    if not fixed and (off.NOT_A_BOARD.search(name) or off.city_board(name, county)):
        return None
    key = off.seat_key(fixed or off.seat_label(name, county))
    if not key:
        return None
    if not fixed and not all(off.SEAT_TOKEN.fullmatch(t) for t in key.split()):
        return None
    return fixed or off.display(key)


def seats_of(maps, fips, names):
    """For one county's maps of one body: ({district key: {"seats", "voted",
    "tested"}}, [the seats the whole county elects])."""
    districts, countywide, at_large = {}, [], []
    for m in maps:
        found = collections.defaultdict(list)
        for c in m["contests"]:
            if not c.get("district"):
                continue
            label = contest_seat(c, fips, names)
            if label:
                found[c["district"]].append((label, c["voted"]))
        schemes = {scheme(label) for v in found.values() for label, voted in v
                   if voted == "by district"}
        for key in m["districts"]:
            seats, voted = [], set()
            for label, how in found.get(key, []):
                if how == "by district" or (scheme(label) in schemes
                                            and numbers(label) == numbers(key)):
                    if label not in seats:
                        seats.append(label)
                    voted.add(how)
                else:
                    countywide.append(label)
            districts[key] = {
                "seats": sorted(seats, key=lambda label: (numbers(label), label)),
                "voted": ("district" if "by district" in voted else
                          "county-wide" if voted else None),
                "tested": m["districts"][key] == "pass",
            }
        for c in m.get("no_district") or []:
            label = contest_seat(c, fips, names)
            if label:
                at_large.append(label)
    claimed = {s for d in districts.values() for s in d["seats"]}
    whole = []
    for label in at_large + countywide:
        if label not in claimed and label not in whole:
            whole.append(label)
    return districts, whole


def describe(record, names):
    """{fips: {"county", body: {...}}} for every county with a passing map.

    Each body carries the day the map check ran (`checked`) and the days of
    the elections whose district contests tested its maps (`elections`), so
    the card can say what the line was checked against without a list of
    elections of its own to go stale."""
    dates = {e["id"]: e["date"] for e in record["sources"]["elections"]}
    by = collections.defaultdict(list)
    for m in passing(record):
        by[(m["fips"], m["body"])].append(m)
    out = {}
    for (fips, body), maps in sorted(by.items()):
        districts, whole = seats_of(maps, fips, names)
        rec = out.setdefault(fips, {"county": names[fips]})
        rec[BODY_KEY[body]] = {
            "maps": [{"year": m["year"], "super": m["super"], "sha256": m["sha256"][:16]}
                     for m in maps],
            "districts": districts,
            "atLarge": whole,
            "checked": record["checked"],
            "elections": sorted({dates[c["election"]] for m in maps for c in m["contests"]
                                 if c.get("district")}),
        }
    return out


# --------------------------------------------------------------- geometry

def read_map(cache, m):
    import hashlib

    path = os.path.join(cache, "maps", m["file"])
    data = cmap.cached(path, m["url"], binary=True)
    if not data:
        raise SystemExit("FAIL: the map office answered nothing for %s" % m["url"])
    digest = hashlib.sha256(data).hexdigest()
    if digest != m["sha256"]:
        raise SystemExit("FAIL: %s is not the file the map check tested (sha256 %s, the "
                         "record's %s); run the map check again" % (m["file"], digest, m["sha256"]))
    return data


def city_schools(cache):
    """[(name, shapely geometry in degrees)] for Georgia's city school systems."""
    from shapely.geometry import shape

    q = {"where": "STATE='13' AND NAME LIKE '% City School District'",
         "outFields": "GEOID,NAME", "returnGeometry": "true", "outSR": "4326",
         "geometryPrecision": "6", "f": "geojson"}
    url = CITY_SCHOOLS + "?" + urllib.parse.urlencode(q)
    fc = cmap.cached_json(os.path.join(cache, "city-school-systems.json"), url)
    if not fc or "error" in fc or not fc.get("features"):
        raise SystemExit("FAIL: TIGERweb answered %r for the city school systems" % (fc,))
    out = []
    for f in fc["features"]:
        name = f["properties"]["NAME"]
        if not CITY_SCHOOL_NAME.match(name):
            raise SystemExit("FAIL: %r is not a city school system's name" % name)
        out.append((name, shape(f["geometry"]).buffer(0)))
    if len(out) != CITY_SCHOOLS_EXPECTED:
        raise SystemExit("FAIL: TIGERweb maps %d city school systems in Georgia; %d were "
                         "mapped on 2026-10-30, so read the list again"
                         % (len(out), CITY_SCHOOLS_EXPECTED))
    return out


def polygonal(g):
    """The polygons of a shapely geometry, as one Polygon or MultiPolygon."""
    from shapely.geometry import MultiPolygon, Polygon

    parts = []

    def walk(x):
        if isinstance(x, Polygon):
            if not x.is_empty:
                parts.append(x)
        elif hasattr(x, "geoms"):
            for y in x.geoms:
                walk(y)

    walk(g)
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else MultiPolygon(parts)


def draw(cache, record, names):
    """{body: [GeoJSON feature]} at full precision, and what was taken out."""
    from shapely.geometry import MultiPolygon, mapping, shape
    from shapely.ops import orient, transform, unary_union

    to_m = cmap._projector()
    with open(COUNTIES, encoding="utf-8") as fh:
        county = {f["properties"]["GEOID"]: shape(f["geometry"]).buffer(0)
                  for f in json.load(fh)["features"]}
    cities = city_schools(cache)
    out = {"commission": [], "school-board": []}
    removed, slivers = [], []
    zones = {}
    for m in passing(record):
        rows = cmap.read_zip(read_map(cache, m), lambda x, y: (x, y))
        by = collections.defaultdict(list)
        for rec, g in rows:
            key = str(rec.get("DISTRICT") or "").strip()
            if key:
                by[key].append(g)
        if sorted(by) != sorted(m["districts"]):
            raise SystemExit("FAIL: %s draws districts %s, the record %s"
                             % (m["file"], sorted(by), sorted(m["districts"])))
        ground = county[m["fips"]]
        took = []
        if m["body"] == "school-board":
            for name, g in cities:
                if g.intersects(ground):
                    took.append((name, g))
        for key in sorted(by):
            g = unary_union(by[key]).buffer(0).intersection(ground)
            for name, cg in took:
                cut = g.intersection(cg)
                km2 = transform(to_m, cut).area / 1e6 if not cut.is_empty else 0.0
                if km2 > 0:
                    removed.append((m["county"], name, key, km2))
                g = g.difference(cg)
            g = polygonal(g)
            if g is None:
                raise SystemExit("FAIL: %s %s district %s is empty once clipped"
                                 % (m["county"], m["body"], key))
            if g.geom_type == "MultiPolygon":
                zkey = (m["fips"], m["body"])
                if zkey not in zones:
                    lines = [ground.boundary] + [cg.boundary for _, cg in took]
                    zones[zkey] = unary_union([transform(to_m, ln).buffer(FIDELITY_CEILING_M)
                                               for ln in lines])
                parts = sorted(g.geoms, key=lambda p: transform(to_m, p).area, reverse=True)
                keep = [parts[0]]
                for p in parts[1:]:
                    pm = transform(to_m, p)
                    if pm.difference(zones[zkey]).area < 1e-6:
                        pt = p.representative_point()
                        slivers.append((m["county"], m["body"], key, pm.area, pt.y, pt.x))
                    else:
                        keep.append(p)
                g = polygonal(MultiPolygon(keep))
            g = orient(g) if g.geom_type == "Polygon" else type(g)([orient(p) for p in g.geoms])
            props = {"id": "%s-%s" % (m["fips"], key), "county": names[m["fips"]],
                     "countyfips": m["fips"], "district": key, "label": district_label(key)}
            if m["super"]:
                props["super"] = True
            out[m["body"]].append({"type": "Feature", "properties": props,
                                   "geometry": mapping(g)})
    return out, removed, slivers


def simplify(features, name):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, name + "-src.geojson")
        dst = os.path.join(tmp, name + ".geojson")
        with open(src, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": features}, fh)
        blb.run_mapshaper(src, SIMPLIFY, dst)
        with open(dst) as fh:
            return json.load(fh)["features"]


def validate(source, drawn, samples=4000, seed=2026):
    """Every sampled point in the state's envelope must hold the same districts
    before and after simplifying, but for at most 0.5% of the points that hold
    any; and no point may hold two districts of one county unless one of them
    is a super district."""
    def model(fs):
        return [(f["properties"]["id"], f["properties"].get("super", False), f["geometry"],
                 blb._bbox(f["geometry"])) for f in fs]

    def at(mod, pt):
        return [(i, sup) for i, sup, g, bb in mod
                if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
                and blb._point_in_geometry(pt, g)]

    src, new = model(source), model(drawn)
    rng = random.Random(seed)
    box = blb.STATE_BBOX
    held = agree = 0
    for _ in range(samples):
        pt = (rng.uniform(box["minLng"], box["maxLng"]), rng.uniform(box["minLat"], box["maxLat"]))
        a, b = at(src, pt), at(new, pt)
        for hits in (a, b):
            if len([1 for _, sup in hits if not sup]) > 1 or len([1 for _, sup in hits if sup]) > 1:
                return False, "two districts at %.5f,%.5f: %s" % (pt[1], pt[0], hits)
        if a or b:
            held += 1
            agree += sorted(a) == sorted(b)
    if not held:
        return False, "no sampled point held a district"
    pct = 100.0 * agree / held
    if pct < 99.5:
        return False, "only %d of %d points (%.2f%%) hold the same districts" % (agree, held, pct)
    return True, "%d of %d sampled points holding a district agree (%.2f%%)" % (agree, held, pct)


# --------------------------------------------------------------- output

def names_by_fips():
    return off.county_names()


def build(cache):
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    names = names_by_fips()
    counties = describe(record, names)
    drawn, removed, slivers = draw(cache, record, names)
    for county, name, key, km2 in removed:
        print("  %s school board district %s: %.3f km2 of %s taken out"
              % (county, int(key) if key.isdigit() else key, km2, name), file=sys.stderr)
    for county, body, key, m2, lat, lng in slivers:
        print("  %s %s district %s: a %.2f m2 sliver at %.5f,%.5f dropped"
              % (county, body, key, m2, lat, lng), file=sys.stderr)
    for body, features in drawn.items():
        tag = "ga-" + body
        simple = simplify(features, tag)
        if len(simple) != len(features):
            raise SystemExit("FAIL: %s: %d features after simplifying, %d before"
                             % (tag, len(simple), len(features)))
        ok, msg = validate(features, simple)
        if not ok:
            raise SystemExit("FAIL: %s: %s" % (tag, msg))
        print("%s: %s" % (tag, msg))
        ok, fmsg = boundary_fidelity.check_fidelity(features, simple, "id", FIDELITY_CEILING_M)
        if not ok:
            raise SystemExit("FAIL: %s: %s" % (tag, fmsg))
        print("%s: %s" % (tag, fmsg))
        compact = json.dumps({"type": "FeatureCollection", "features": simple},
                             separators=(",", ":"), ensure_ascii=False)
        with open(OUT[body], "w", encoding="utf-8") as fh:
            fh.write(compact)
        print("wrote %s: %d districts, %d bytes" % (os.path.relpath(OUT[body], REPO_ROOT),
                                                    len(simple), len(compact)))
    with open(OUT_COUNTIES, "w", encoding="utf-8") as fh:
        json.dump(counties, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print("wrote %s: %d counties" % (os.path.relpath(OUT_COUNTIES, REPO_ROOT), len(counties)))
    check()


def check():
    """The three files against the record, offline."""
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    names = names_by_fips()
    want = describe(record, names)
    with open(OUT_COUNTIES, encoding="utf-8") as fh:
        got = json.load(fh)
    problems = []
    if got != want:
        for fips in sorted(set(got) | set(want)):
            if got.get(fips) != want.get(fips):
                problems.append("the counties file disagrees with the record about %s (%s)"
                                % (fips, names.get(fips)))
    expected = {}
    for m in passing(record):
        for key in m["districts"]:
            expected[(m["body"], "%s-%s" % (m["fips"], key))] = (m, key)
    seen = set()
    for body, path in OUT.items():
        with open(path, encoding="utf-8") as fh:
            fc = json.load(fh)
        last = None
        for f in fc["features"]:
            p = f["properties"]
            ident = (body, p.get("id"))
            if ident not in expected:
                problems.append("%s draws %s, which no passing map has" % (os.path.basename(path), p.get("id")))
                continue
            if ident in seen:
                problems.append("%s draws %s twice" % (os.path.basename(path), p.get("id")))
            seen.add(ident)
            m, key = expected[ident]
            right = {"id": p["id"], "county": names[m["fips"]], "countyfips": m["fips"],
                     "district": key, "label": district_label(key)}
            if m["super"]:
                right["super"] = True
            if p != right:
                problems.append("%s: %s carries %s, not %s" % (os.path.basename(path), p["id"], p, right))
            if f["geometry"]["type"] not in ("Polygon", "MultiPolygon") or not f["geometry"]["coordinates"]:
                problems.append("%s: %s has no polygon" % (os.path.basename(path), p["id"]))
            order = (m["fips"], m["super"])
            if last and order < last:
                problems.append("%s: %s comes before a district it should follow; a county's "
                                "super districts come after its other districts"
                                % (os.path.basename(path), p["id"]))
            last = order
    for ident in sorted(set(expected) - seen):
        problems.append("%s district %s passes the map check and is not drawn" % ident)
    if problems:
        raise SystemExit("FAIL: %d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))
    n = collections.Counter(body for body, _ in seen)
    print("ok: %d commission and %d school board districts in %d counties, from the %d maps the "
          "map check passes" % (n["commission"], n["school-board"], len(got), len(passing(record))))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--cache", help="the map check's cache directory")
    ap.add_argument("--check", action="store_true", help="hold the files to the record, offline")
    args = ap.parse_args()
    if args.check:
        check()
        return
    if not args.cache:
        ap.error("--cache DIR is required to build")
    build(os.path.abspath(args.cache))


if __name__ == "__main__":
    main()
