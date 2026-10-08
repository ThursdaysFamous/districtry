#!/usr/bin/env python3
"""
Build data/app/mn-school-board-districts.json — the election districts of the
Minnesota school boards that elect members by district, drawn from the
Secretary of State's own precinct-level results.

Minn. Stat. 205A.12 subd. 1 lets an independent school district "alter its
organization into separate election districts for the purpose of election of
board members", and a candidate then files for the district they live in
(subd. 5). Most Minnesota boards elect at large; which ones do not is not
published as a list, and no state office publishes these districts as a map.

THE RESULTS SAY WHERE THE LINES ARE. The Secretary of State publishes, per
election, `localPrct.txt` on electionresultsfiles.sos.mn.gov: every local
contest broken out by precinct. A board seat filed as "School Board Member
District 3 (ISD #2180)" is voted on in exactly the precincts that make up
District 3, so the union of those precincts, cut to the school district's own
boundary, is the district. That is the same composition the commissioner
layer uses, read from the ballot rather than from an attribute.

WHICH BOARDS COUNT IS MEASURED, NOT LISTED. A seat called "District N" is a
real election district only if the districts' precinct sets are (nearly)
disjoint. Some boards file "District" or a place name for a seat that every
precinct votes on — a residency rule, not geography (Gibbon-Fairfax-Winthrop's
three place seats are voted on in all of its precincts alike) — and those
fail the disjointness test and are printed rather than drawn. "Position N"
offices are numbered seats every precinct votes on and are never read here.

THE PRECINCTS ARE READ IN THE VINTAGE THE CONTEST WAS HELD IN. A precinct code
in a results file means that election's precinct, and St. Louis County alone
renumbered more than twenty precincts after 2024, so a code from the 2022 or
2024 files looked up in today's fabric lands nowhere or somewhere else. The
Secretary of State publishes each even-year general's precincts as their own
layer (`bdry_electionresults_2022_2030`, one layer per general), so a district
whose latest regular contest was an even-year general is dissolved out of THAT
year's precincts. An odd-year contest has no such layer and is read against
the current fabric.

TWO THINGS THE RESULTS CANNOT PLACE, AND BOTH SHIP AS WHAT THEY ARE.
  * A SPLIT PRECINCT votes in two board districts, because the district line
    runs through it. Which side an address is on is not in the results, so
    the precinct ships as its own feature naming both districts rather than
    being given to either.
  * A COMBINED POLLING PLACE. In odd years a board may run its own election
    and report on combined polling places (codes 9000 and up) instead of
    precincts; those cannot be placed. Anoka-Hennepin (ISD 11) reports every
    district contest that way and is not drawn at all; Duluth (ISD 709)
    reports its rural townships that way, so that ground ships as one
    "not placed" feature. Any other part of a board's school district that
    no contest covers ships the same way, with its area printed.

Run:  python3 mn/scripts/build_mn_school_board_districts.py
      python3 mn/scripts/build_mn_school_board_districts.py --check   (offline)
"""

import argparse
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
FLEET_SCRIPTS = os.path.join(REPO, "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, FLEET_SCRIPTS)

import mn_vtd_dissolve as vtd  # noqa: E402
from build_mn_school_boards import OFFICE_RE  # noqa: E402
from scraper_common import require_robots_once  # noqa: E402

USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 120
PACE_SECONDS = 0.5
FILES_HOST = "https://electionresultsfiles.sos.mn.gov"
PRECINCT_RESULTS = FILES_HOST + "/%s/localPrct.txt"
RESULTS_SERVICE = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
                   "us_mn_state_sos/bdry_electionresults_2022_2030/FeatureServer")
TIGER_LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
               "School/MapServer/%d/query")
TIGER_LAYERS = (0, 2)
FIRST_YEAR = 2022
CANVASS_DAYS = 21

ROSTER_FILE = os.path.join(INSTANCE, "data", "app", "mn-school-boards.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-school-board-districts.json")

MAPSHAPER = "mapshaper@0.6.102"
SIMPLIFY_INTERVAL_M = 15

# A combined polling place in an odd-year board election, not a precinct.
COMBINED_CODE = 9000

# Disjointness: a board whose district contests share more than this share of
# their precincts is a residency or position board, not an election-district
# board. Measured 2026-10-08: the real ones share at most 2 of 33 (6%), and
# Gibbon-Fairfax-Winthrop shares every precinct.
MAX_SHARED_SHARE = 0.10

# Ground in a board's school district that no contest places is shipped only
# above this size; anything smaller is where the Census's school line and the
# Secretary of State's precinct lines are drawn a few metres apart.
SLIVER_M = 30.0
MIN_UNPLACED_KM2 = 0.25

# Measured 2026-10-08: 13 boards and 59 districts. The floors fail a parse
# that loses a board or a district, and are no promise the set cannot grow.
MIN_BOARDS = 12
MIN_DISTRICTS = 55

M_PER_DEG_LAT = 110540.0

# THE ONE WITNESS IS A CITY GOVERNMENT'S OWN DRAWING. Minneapolis publishes
# its six park commissioner districts, and its six school board districts are
# drawn on the same lines with the same numbers; measured 2026-10-08, all
# 1,800 points sampled inside the six districts dissolved here land in the park
# district of the same number. Read as a
# check on the method — the precinct composition reproducing a map drawn in a
# different office — not as a source.
WITNESS = ("SSD 1",
           "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/"
           "Park_Commissioner_Districts_2022/FeatureServer/0/query",
           "MPLSPARK")
WITNESS_POINTS = 300
WITNESS_FLOOR = 0.98


def fail(msg):
    raise SystemExit("build-mn-school-board-districts: FATAL: %s" % msg)


def general_dates(today):
    """Every November general from FIRST_YEAR whose canvass is over."""
    out = []
    for year in range(FIRST_YEAR, today.year + 1):
        nov1 = datetime.date(year, 11, 1)
        monday = nov1 + datetime.timedelta(days=(0 - nov1.weekday()) % 7)
        day = monday + datetime.timedelta(days=1)
        if today >= day + datetime.timedelta(days=CANVASS_DAYS):
            out.append(day)
    return out


def get_json(session, url, params):
    resp = session.get(url, params=params, headers={"User-Agent": USER_AGENT},
                       timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        fail("%s answered HTTP %d" % (url, resp.status_code))
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        fail("%s answered an error: %r" % (url, data["error"]))
    return data


def vtdid(county_code, pct):
    return "27%03d%s" % (2 * int(county_code) - 1, pct)


def read_contests(texts):
    """{board key: {seat: [contest]}} for every district-seat contest."""
    found = {}
    for day, text in sorted(texts.items()):
        for line in text.splitlines():
            f = line.split(";")
            if len(f) < 8 or "School Board Member" not in f[4]:
                continue
            m = OFFICE_RE.match(f[4].strip())
            if not m:
                fail("%s: an office this parser does not read: %r" % (day, f[4]))
            seat = m.group("seat")
            if not seat or seat.lower() == "at large" or seat.startswith("Position"):
                continue
            key = "%s %d" % (m.group("type"), int(m.group("num")))
            seats = found.setdefault(key, {})
            contest = None
            for c in seats.setdefault(seat, []):
                if c["date"] == day and c["office"] == f[4].strip():
                    contest = c
            if contest is None:
                contest = {"date": day, "office": f[4].strip(),
                           "special": bool(m.group("special")),
                           "precincts": set(), "combined": set()}
                seats[seat].append(contest)
            code = f[2].strip()
            if int(code) >= COMBINED_CODE:
                contest["combined"].add(vtdid(f[1], code))
            else:
                contest["precincts"].add(vtdid(f[1], code))
    return found


def choose(contests):
    """The contest that says where a seat's district is: the latest regular
    one, a special only where there is no regular."""
    regular = [c for c in contests if not c["special"]]
    pool = regular or contests
    return max(pool, key=lambda c: c["date"])


def results_layers(session):
    """{year: layer id} for the per-general precinct layers."""
    data = get_json(session, RESULTS_SERVICE, {"f": "json"})
    out = {}
    for layer in data.get("layers") or []:
        m = re.search(r"By Precinct (\d{4})$", layer.get("name") or "")
        if m:
            out[int(m.group(1))] = layer["id"]
    if 2022 not in out or 2024 not in out:
        fail("the results service no longer lists the 2022 and 2024 precinct "
             "layers: %r" % out)
    return out


def fetch_precinct_geometry(session, url, ids):
    feats = []
    ids = sorted(ids)
    for i in range(0, len(ids), 80):
        chunk = ids[i:i + 80]
        body = get_json(session, url, {
            "where": "vtdid IN (%s)" % ",".join("'%s'" % v for v in chunk),
            "outFields": "vtdid,pctname,countyname", "returnGeometry": "true",
            "outSR": "4326", "f": "geojson"})
        feats.extend(body.get("features") or [])
        time.sleep(PACE_SECONDS)
    got = {(f.get("properties") or {}).get("vtdid") for f in feats}
    missing = sorted(set(ids) - got)
    return feats, missing


def fetch_school(session, geoid):
    for layer in TIGER_LAYERS:
        body = get_json(session, TIGER_LAYER % layer, {
            "where": "GEOID='%s'" % geoid, "outFields": "GEOID,NAME",
            "returnGeometry": "true", "outSR": "4326", "f": "geojson"})
        time.sleep(PACE_SECONDS)
        feats = body.get("features") or []
        if feats:
            return feats[0]["geometry"]
    fail("TIGERweb has no school district %s in layers %s" % (geoid, TIGER_LAYERS))


def fabric_cover(session, school):
    """The union of today's precincts that touch a school district."""
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    minx, miny, maxx, maxy = school.bounds
    feats, offset = [], 0
    while True:
        body = get_json(session, vtd.PRECINCT_QUERY, {
            "where": "1=1", "geometry": "%f,%f,%f,%f" % (minx, miny, maxx, maxy),
            "geometryType": "esriGeometryEnvelope", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects", "outFields": "vtdid",
            "returnGeometry": "true", "outSR": "4326", "orderByFields": "objectid",
            "resultOffset": str(offset), "resultRecordCount": "2000", "f": "geojson"})
        page = body.get("features") or []
        feats.extend(page)
        time.sleep(PACE_SECONDS)
        if len(page) < 2000:
            break
        offset += 2000
    if not feats:
        fail("no precinct touches the school district's envelope %r" % (school.bounds,))
    return unary_union([shape(f["geometry"]).buffer(0) for f in feats])


def local_scale(geom):
    from shapely.geometry import shape  # noqa: PLC0415
    lat = shape(geom).centroid.y
    return math.cos(math.radians(lat)) * M_PER_DEG_LAT, M_PER_DEG_LAT


def to_m(g, sx, sy):
    from shapely import affinity  # noqa: PLC0415
    return affinity.scale(g, xfact=sx, yfact=sy, origin=(0, 0))


def to_deg(g, sx, sy):
    from shapely import affinity  # noqa: PLC0415
    return affinity.scale(g, xfact=1.0 / sx, yfact=1.0 / sy, origin=(0, 0))


def polygonal(g):
    from shapely.geometry import MultiPolygon, Polygon  # noqa: PLC0415
    if g.is_empty:
        return g
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    parts = [p for p in getattr(g, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))]
    from shapely.ops import unary_union  # noqa: PLC0415
    return unary_union(parts) if parts else Polygon()


def dissolved(features):
    from shapely.geometry import shape  # noqa: PLC0415
    polys = vtd.group_rings(vtd.dissolve(features))
    geom = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
            else {"type": "MultiPolygon", "coordinates": polys})
    g = shape(geom)
    return g if g.is_valid else g.buffer(0)


def simplify_shared(collection):
    """One mapshaper pass over the whole set, so a border two districts share
    is one arc simplified once (build_mn_commissioner_districts.py records
    why simplifying each district alone leaves slivers and overlaps)."""
    if not shutil.which("npx"):
        fail("npx is not on PATH; this builder simplifies through mapshaper")
    work = tempfile.mkdtemp(prefix="mn-sbd-")
    try:
        src = os.path.join(work, "exact.json")
        dst = os.path.join(work, "simple.json")
        with open(src, "w") as handle:
            json.dump(collection, handle, separators=(",", ":"))
        proc = subprocess.run(
            ["npx", "--yes", MAPSHAPER, src,
             "-simplify", "dp", "interval=%d" % SIMPLIFY_INTERVAL_M, "keep-shapes",
             "-o", "precision=0.000001", dst],
            capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(dst):
            fail("mapshaper failed (%d): %s" % (proc.returncode, (proc.stderr or "")[-800:]))
        with open(dst) as handle:
            out = json.load(handle)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if len(out.get("features") or []) != len(collection["features"]):
        fail("mapshaper returned %d features for %d"
             % (len(out.get("features") or []), len(collection["features"])))
    return out


def interior_points(geom, wanted):
    from shapely.geometry import shape  # noqa: PLC0415
    g = shape(geom)
    pts = [g.representative_point()]
    minx, miny, maxx, maxy = g.bounds
    n = 0
    step = 7
    while len(pts) < wanted and n < 4000:
        n += 1
        x = minx + (maxx - minx) * ((n * 0.618034) % 1.0)
        y = miny + (maxy - miny) * ((n * step * 0.414214) % 1.0)
        from shapely.geometry import Point  # noqa: PLC0415
        p = Point(x, y)
        if g.contains(p):
            pts.append(p)
    return [(p.x, p.y) for p in pts]


def board_label(key):
    return key


def build(today, cache):
    import requests  # noqa: PLC0415
    from shapely.geometry import mapping, shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    with open(ROSTER_FILE, encoding="utf-8") as fh:
        roster = json.load(fh)
    geoid_of = {rec["district"]: g for g, rec in roster.items()}
    name_of = {rec["district"]: rec["name"] for rec in roster.values()}

    session = requests.Session()
    days = general_dates(today)
    require_robots_once(PRECINCT_RESULTS % days[0].strftime("%Y%m%d"), USER_AGENT)
    texts = {}
    for day in days:
        stamp = day.strftime("%Y%m%d")
        path = os.path.join(cache, "lp_%s.txt" % stamp) if cache else None
        if path and os.path.exists(path):
            with open(path, encoding="latin-1") as fh:
                texts[day] = fh.read()
            continue
        resp = session.get(PRECINCT_RESULTS % stamp, headers={"User-Agent": USER_AGENT},
                           timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            fail("%s answered HTTP %d" % (PRECINCT_RESULTS % stamp, resp.status_code))
        texts[day] = resp.content.decode("latin-1")
        time.sleep(PACE_SECONDS)
    print("precinct-level results read: %s" % ", ".join(d.isoformat() for d in days))

    found = read_contests(texts)
    require_robots_once(RESULTS_SERVICE + "?f=json", USER_AGENT)
    require_robots_once(TIGER_LAYER % 0, USER_AGENT)
    year_layer = results_layers(session)

    boards, skipped = {}, []
    for key, seats in sorted(found.items()):
        chosen = {seat: choose(cs) for seat, cs in seats.items()}
        if len(chosen) < 2:
            skipped.append((key, "files one district seat only"))
            continue
        union = set().union(*(c["precincts"] for c in chosen.values()))
        if not union:
            skipped.append((key, "reports every district contest on combined polling "
                                 "places, which the results do not place on precincts"))
            continue
        counts = {}
        for c in chosen.values():
            for v in c["precincts"]:
                counts[v] = counts.get(v, 0) + 1
        shared = sorted(v for v, n in counts.items() if n > 1)
        if len(shared) > MAX_SHARED_SHARE * len(union):
            skipped.append((key, "%d of its %d precincts vote for more than one of its "
                                 "district seats, so the seats are residency or numbered "
                                 "seats rather than election districts"
                            % (len(shared), len(union))))
            continue
        if key not in geoid_of:
            fail("%s elects by district and is not in the shipped school board roster"
                 % key)
        boards[key] = (chosen, set(shared))
    for key, why in skipped:
        print("not drawn: %s — %s" % (key, why))

    collection = {"type": "FeatureCollection", "features": []}
    report = []
    for key, (chosen, shared) in sorted(boards.items()):
        geoid = geoid_of[key]
        school = shape(fetch_school(session, geoid))
        if not school.is_valid:
            school = school.buffer(0)
        sx, sy = local_scale(mapping(school))
        # read each seat's precincts in the vintage its contest was held in
        by_source = {}
        for seat, c in chosen.items():
            year = c["date"].year
            url = ("%s/%d/query" % (RESULTS_SERVICE, year_layer[year])
                   if year in year_layer else vtd.PRECINCT_QUERY)
            by_source.setdefault(url, set()).update(c["precincts"])
        geom_of = {}
        for url, ids in by_source.items():
            feats, missing = fetch_precinct_geometry(session, url, ids)
            if missing and url != vtd.PRECINCT_QUERY:
                fail("%s: precinct(s) %s are in the results and not in the precinct "
                     "layer for that election (%s)" % (key, missing, url))
            # an odd-year code today's fabric does not hold is a combined
            # polling place the board numbered for its own election
            for c in chosen.values():
                if c["date"].year not in year_layer:
                    gone = c["precincts"] & set(missing)
                    c["precincts"] -= gone
                    c["combined"] |= gone
            for f in feats:
                geom_of[(url, f["properties"]["vtdid"])] = f
        if not any(c["precincts"] for c in chosen.values()):
            print("not drawn: %s — every district contest is reported on combined "
                  "polling places, which the results do not place on precincts" % key)
            continue

        pieces = []
        for seat, c in sorted(chosen.items()):
            year = c["date"].year
            url = ("%s/%d/query" % (RESULTS_SERVICE, year_layer[year])
                   if year in year_layer else vtd.PRECINCT_QUERY)
            own = [geom_of[(url, v)] for v in sorted(c["precincts"] - shared)]
            g = dissolved(own) if own else None
            if g is not None:
                g = polygonal(g.intersection(school))
            pieces.append({"seat": seat, "geom": g, "contest": c})
        for v in sorted(shared):
            seats_here = sorted(s for s, c in chosen.items() if v in c["precincts"])
            c0 = chosen[seats_here[0]]
            year = c0["date"].year
            url = ("%s/%d/query" % (RESULTS_SERVICE, year_layer[year])
                   if year in year_layer else vtd.PRECINCT_QUERY)
            f = geom_of[(url, v)]
            g = polygonal(shape(f["geometry"]).buffer(0).intersection(school))
            pieces.append({"seat": None, "split": seats_here, "geom": g,
                           "precinct": (f["properties"].get("pctname") or v).strip()})

        # districts read from two vintages can overlap where a precinct line
        # moved between them; the later contest's line wins and the overlap is
        # measured, never silently kept on both sides
        placed = [p for p in pieces if p["geom"] is not None and not p["geom"].is_empty]
        placed.sort(key=lambda p: (p.get("contest") or {"date": datetime.date.max})["date"],
                    reverse=True)
        taken = None
        worst = 0.0
        for p in placed:
            if taken is not None:
                overlap = p["geom"].intersection(taken)
                area = to_m(overlap, sx, sy).area if not overlap.is_empty else 0.0
                worst = max(worst, area)
                if area > 0.02 * to_m(p["geom"], sx, sy).area:
                    fail("%s %s overlaps a neighbour by %.0f m², more than a moved "
                         "precinct line explains" % (key, p.get("seat") or p.get("split"),
                                                     area))
                if area > 0:
                    p["geom"] = polygonal(p["geom"].difference(taken))
            taken = p["geom"] if taken is None else unary_union([taken, p["geom"]])

        residual = polygonal(school.difference(taken)) if taken is not None else school
        # the Census draws a lakeshore district out over the water and the
        # precinct fabric covers only the ground people vote on, so ground no
        # contest places is counted only where some precinct lies
        residual = polygonal(residual.intersection(fabric_cover(session, school)))
        rm = to_m(residual, sx, sy)
        kept = polygonal(rm.buffer(-SLIVER_M).buffer(SLIVER_M).intersection(rm))
        parts = [g for g in getattr(kept, "geoms", [kept]) if not g.is_empty
                 and g.area / 1e6 >= MIN_UNPLACED_KM2]
        unplaced = to_deg(unary_union(parts), sx, sy) if parts else None
        combined = sorted(set().union(*(c["combined"] for c in chosen.values())))

        name = name_of[key]
        for p in placed:
            if p["geom"].is_empty:
                continue
            props = {"geoid": geoid, "board": key, "school": name}
            if p.get("split"):
                props.update({"kind": "split", "seats": p["split"],
                              "precinct": p["precinct"]})
            else:
                c = p["contest"]
                props.update({"kind": "district", "seat": p["seat"],
                              "contest": c["office"], "election": c["date"].isoformat(),
                              "sourceUrl": PRECINCT_RESULTS % c["date"].strftime("%Y%m%d"),
                              "precincts": len(c["precincts"])})
            collection["features"].append({"type": "Feature", "properties": props,
                                           "geometry": mapping(p["geom"])})
        if unplaced is not None:
            props = {"geoid": geoid, "board": key, "school": name, "kind": "unplaced",
                     "why": ("combined" if combined else "uncovered")}
            collection["features"].append({"type": "Feature", "properties": props,
                                           "geometry": mapping(unplaced)})
        report.append("%s (%s): %d districts, %d split precinct(s), %.1f km² not placed%s, "
                      "worst cross-vintage overlap %.0f m²"
                      % (key, name, sum(1 for p in placed if p.get("seat")), len(shared),
                         (to_m(unplaced, sx, sy).area / 1e6) if unplaced is not None else 0.0,
                         (" (%d combined polling places)" % len(combined)) if combined else "",
                         worst))
    for line in report:
        print("  " + line)
    witness(session, collection)
    return collection


def witness(session, collection):
    import random  # noqa: PLC0415
    from shapely.geometry import Point, shape  # noqa: PLC0415
    board, url, field = WITNESS
    require_robots_once(url, USER_AGENT)
    theirs = [(int(f["properties"][field]), shape(f["geometry"]))
              for f in get_json(session, url, {"where": "1=1", "outFields": field,
                                               "outSR": "4326", "f": "geojson"})["features"]]
    rng = random.Random(20261008)
    agree = total = 0
    for f in collection["features"]:
        p = f["properties"]
        if p["board"] != board or p["kind"] != "district":
            continue
        number = int(p["seat"].split()[-1])
        g = shape(f["geometry"])
        minx, miny, maxx, maxy = g.bounds
        n = 0
        while n < WITNESS_POINTS:
            pt = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if not g.contains(pt):
                continue
            n += 1
            hits = [num for num, wg in theirs if wg.contains(pt)]
            total += 1
            agree += hits == [number]
    if not total or agree < WITNESS_FLOOR * total:
        fail("%s: the city's own districts agree at %d of %d sampled points, under "
             "the %.0f%% floor" % (board, agree, total, 100 * WITNESS_FLOOR))
    print("witness: %s — the city's own park commissioner districts agree at %d of "
          "%d points sampled inside the districts drawn here" % (board, agree, total))


def gates(out):
    """Every rule the shipped file must keep, offline."""
    from shapely.geometry import Point, shape  # noqa: PLC0415
    problems = []
    feats = out.get("features") or []
    boards = {}
    for f in feats:
        p = f.get("properties") or {}
        boards.setdefault(p.get("board"), []).append(f)
        if p.get("kind") not in ("district", "split", "unplaced"):
            problems.append("a feature of unknown kind: %r" % p)
        if p.get("kind") == "district" and not p.get("seat"):
            problems.append("a district with no seat: %r" % p)
        if p.get("kind") == "split" and len(p.get("seats") or []) < 2:
            problems.append("a split precinct naming fewer than two seats: %r" % p)
    with open(ROSTER_FILE, encoding="utf-8") as fh:
        roster = json.load(fh)
    districts = 0
    for board, fs in sorted(boards.items()):
        seats = [f["properties"]["seat"] for f in fs if f["properties"]["kind"] == "district"]
        districts += len(seats)
        if len(seats) != len(set(seats)):
            problems.append("%s draws one seat twice" % board)
        geoid = fs[0]["properties"]["geoid"]
        rec = roster.get(geoid)
        if not rec or rec.get("district") != board:
            problems.append("%s's GEOID %s is not that board in the roster" % (board, geoid))
            continue
        roster_seats = {s["seat"] for s in rec["seats"]}
        for s in seats:
            if s not in roster_seats:
                problems.append("%s draws %s and the roster has no such seat" % (board, s))
        # no point inside one feature is inside another of the same board
        shapes = [(f["properties"], shape(f["geometry"])) for f in fs]
        for i, (pa, ga) in enumerate(shapes):
            pt = ga.representative_point()
            hits = [pb for j, (pb, gb) in enumerate(shapes) if j != i and gb.contains(pt)]
            if hits:
                problems.append("%s: a point inside %s is also inside %s"
                                % (board, pa.get("seat") or pa.get("kind"),
                                   [h.get("seat") or h.get("kind") for h in hits]))
    if len(boards) < MIN_BOARDS:
        problems.append("%d boards drawn, floor %d" % (len(boards), MIN_BOARDS))
    if districts < MIN_DISTRICTS:
        problems.append("%d districts drawn, floor %d" % (districts, MIN_DISTRICTS))
    return problems, len(boards), districts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its own rules")
    ap.add_argument("--cache", help="read saved lp_<YYYYMMDD>.txt files from this folder")
    args = ap.parse_args()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as fh:
            out = json.load(fh)
        problems, nb, nd = gates(out)
        if problems:
            for p in problems:
                print("build-mn-school-board-districts: FAIL: " + p)
            raise SystemExit(1)
        print("build-mn-school-board-districts --check: OK — %d districts on %d boards, "
              "every one a seat the roster names, none overlapping" % (nd, nb))
        return
    exact = build(datetime.date.today(), args.cache)
    out = simplify_shared(exact)
    problems, nb, nd = gates(out)
    if problems:
        for p in problems:
            print("build-mn-school-board-districts: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")
    print("wrote %s: %d districts on %d boards, %d bytes"
          % (os.path.relpath(OUT_FILE, REPO), nd, nb, os.path.getsize(OUT_FILE)))


if __name__ == "__main__":
    main()
