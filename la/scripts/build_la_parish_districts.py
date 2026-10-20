#!/usr/bin/env python3
"""
Build la/data/app/la-parish-districts.json: the districts of the Louisiana
parishes whose governing body's CURRENT district lines this app has
confirmed, so the app can say which member of a parish's police jury, council
or commission represents a point. The Parish card names every member in every
parish; this layer draws the district only where its lines are known to be
the ones in force. That is Adam's ruling of 2026-10-20 ("Confirmed only"),
the rule Mississippi's supervisor districts follow.

WHERE THE LINES COME FROM. Every Louisiana parish elects its governing body
by district: 38 police juries, 25 councils (each beside an elected parish
president, mayor-president or mayor) and Caddo's commission. Seven of the
councils also elect some members at large. The Census Bureau carries those
districts as county subdivisions: TIGERweb's current layer
(tigerWMS_Current, layer 22, "January 1, 2026 vintage") names them by the
number or letter the parish uses, and every one outside Orleans is
nonfunctioning (FUNCSTAT N), which is how the Census files a governing-body
district. Orleans Parish has a single subdivision, the City of New Orleans
(FUNCSTAT F), because the city council's districts are not filed with the
Census at all. No state office publishes a statewide map of the current
lines, measured 2026-10-09 for the plan and again 2026-10-20.

WHY MOST PARISHES ARE NOT DRAWN. The Census has a parish's new lines only if
the parish sent them after the 2020 census. Measured 2026-10-20 on the 2020
census's own blocks, the 2026 layer puts every resident of 52 of the 63
parishes outside Orleans in the same district as the Census's own 2020
edition (tigerWMS_Census2020, layer 20), and in every one of those 52 the
districts' populations differ by more than ten per cent of an equal share,
so they are not lines drawn on the 2020 census. The plan's
spot check found four such parishes' census lines out of date against the
parish's own current map (East Baton Rouge, Webster, Ouachita and
Lafayette).

THE TEST, the two Mississippi's builder applies, for every parish drawn:
  1. the 2026 lines MOVE at least MIN_PEOPLE_MOVED residents from the 2020
     edition's, which is the evidence that the parish sent the Census new
     lines; and
  2. the districts hold nearly equal numbers of people on the 2020 census's
     own blocks: the largest minus the smallest is no more than
     MAX_DEVIATION_PCT of an equal share, as lines drawn on that census
     should.
The other eleven pass the first test. Six pass both, and they are
CENSUS_PARISHES. The other five, measured 2026-10-20 (largest minus smallest,
as a share of an equal district):

    St. Tammany  10.48%   (88,936 residents moved)
    Ascension    11.26%   (41,114)
    St. James    11.86%   (3,838)
    Vermilion    20.71%   (5,773)
    LaSalle      88.84%   (165)

The first three are close enough that their lines may well be current and
simply drawn a little past ten per cent; that is a question for each parish's
own map, which is recorded in la/WATCH.md and gap
la-parish-district-lines, and never a reason to lower the ceiling for every
parish. A parish passing the test is a reason to look, not yet a reason to
draw, so the list is STATED: `--survey` prints any parish that newly passes
and a person adds it after looking.

THE NAME IS THE SECRETARY OF STATE'S AND THE LINE IS THE CENSUS'S. The
district number or letter joins the two, and the build refuses unless the
Secretary of State's list (data/app/la-parish-officials.json, built by
build_la_parish_officials.py) has a seat for exactly the districts the
Census draws, each named in the parish's own word ("District" or, in
Assumption, "Ward"). Each feature carries that word and the body's name, so
the hover popup can name the district without the roster.

THE SAME DRAWING RULES AS THE PARISH FILE. Every ArcGIS answer is read as
ArcGIS JSON and converted here (esri_polygon), the simplification is
Douglas-Peucker at 5 m under the 8 m fidelity ceiling
build_legislative_boundaries.py holds, and the build refuses unless 2,000
points placed inside the districts agree with the full-precision lines, no
point falls in two districts, simplifying moves no more than one per cent of
a parish's residents across a line, and the Parish layer and this one agree
about the parish everywhere except within EDGE_M of a parish line.

THE COVERAGE TEST READS A LIST, NOT THIS FILE. The app's coverage test for
this layer runs on a reader's first selection even with the layer off, so it
reads la-parish-district-parishes.json (under 1 KB, written by the same
build) beside the parish file the Parish card loads anyway.

Prerequisites: Node.js (mapshaper via `npx mapshaper@<pinned>`), and for the
build (not --check) shapely as scripts/requirements.txt pins it.

Usage:
    python3 la/scripts/build_la_parish_districts.py           # fetch, build, write
    python3 la/scripts/build_la_parish_districts.py --check   # offline gate (CI)
    python3 la/scripts/build_la_parish_districts.py --survey  # all 64 parishes, writes nothing
"""

import argparse
import datetime
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(_HERE)
# APPENDED, not inserted: the shared scripts/ directory has a
# build_legislative_boundaries.py of its own (Illinois's), and this file must
# import the one beside it.
sys.path.append(os.path.join(os.path.dirname(INSTANCE), "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
SOURCE_DIR = os.path.join(INSTANCE, "data", "source")
OUT = os.path.join(APP_DATA_DIR, "la-parish-districts.json")
PARISH_LIST = os.path.join(APP_DATA_DIR, "la-parish-district-parishes.json")
RECORD = os.path.join(SOURCE_DIR, "la-parish-districts.source.json")
PARISHES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
ROSTER_FILE = os.path.join(APP_DATA_DIR, "la-parish-officials.json")

USER_AGENT = "districtry/1.0 (+https://districtry.com/la/)"
LABEL = "la-build-la-parish-districts"
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
CURRENT = TIGERWEB + "tigerWMS_Current/MapServer/22"
CURRENT_NAME = "County Subdivisions"
CURRENT_VINTAGE = "January 1, 2026"
EDITION_2020 = TIGERWEB + "tigerWMS_Census2020/MapServer/20"
BLOCKS = TIGERWEB + "Tracts_Blocks/MapServer/12"   # Census 2020 blocks, POP100
TRACTS = TIGERWEB + "Tracts_Blocks/MapServer/10"   # Census 2020 tracts, POP100
STATE = "22"

# The parishes whose Census lines are confirmed current, by three-digit code.
# STATED, never derived (see the docstring).
CENSUS_PARISHES = {
    "007": "Assumption",
    "017": "Caddo",
    "057": "Lafourche",
    "089": "St. Charles",
    "105": "Tangipahoa",
    "109": "Terrebonne",
}

MAX_DEVIATION_PCT = 10.0
# A change smaller than this many residents is not counted as new lines: it is
# the size of a boundary correction, not of a redistricting plan. Measured
# 2026-10-20, the smallest change among the six drawn parishes moves 1,040
# people (Assumption), and the smallest of the eleven that moved at all moves
# 165 (LaSalle).
MIN_PEOPLE_MOVED = 50
SIMPLIFY = "interval=5"
EDGE_M = 20.0               # two simplified files, each within the 8 m ceiling
AGREEMENT_SAMPLES = 2000
WITNESS_SAMPLES = 4000
PAGE = 20000
SEAT_RE = re.compile(r"^(District|Ward|Metro District) ([0-9]+|[A-Z])$")


# ---------------------------------------------------------------- fetching --
def _get(url, params):
    q = url + "/query?" + urllib.parse.urlencode(params)
    require_robots_once(q, USER_AGENT, headers={"User-Agent": USER_AGENT}, label=LABEL)
    for attempt in range(4):
        try:
            req = urllib.request.Request(q, headers={"User-Agent": USER_AGENT,
                                                     "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                # An ArcGIS error is an object, not an empty answer.
                raise RuntimeError("TIGERweb answered an error: %r" % (data["error"],))
            return data
        except Exception as err:  # noqa: BLE001 — retried, then raised
            if attempt == 3:
                raise
            print("parish-districts: retrying after %s" % err, file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def _layer_name(url):
    require_robots_once(url, USER_AGENT, headers={"User-Agent": USER_AGENT}, label=LABEL)
    req = urllib.request.Request(url + "?f=json", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    return meta.get("name"), meta.get("description") or ""


# ------------------------------------------------------------ ArcGIS rings --
# EVERY POLYGON THIS BUILDER READS ARRIVES AS ARCGIS JSON AND IS CONVERTED
# HERE, NEVER AS THE SERVER'S OWN GEOJSON. Mississippi's builder measured a
# server's GeoJSON conversion sending a two-part district as one polygon with
# its smaller part as a hole outside the larger, intermittently (2026-10-15);
# TIGERweb's was not seen to fail and is read the same way regardless,
# because a district read like that would ship with a hole where its second
# part should be and the even-odd point test the checks use would not notice.
def _ring_area(ring):
    """A ring's shoelace area in square degrees: negative when the ring runs
    clockwise, which is how ArcGIS draws an outer ring."""
    return sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
               for i in range(len(ring) - 1)) / 2.0


def esri_polygon(rings, what):
    """ArcGIS JSON rings as a GeoJSON geometry, by ArcGIS's own rule: a
    clockwise ring is an outer ring, a counter-clockwise one is a hole, and a
    hole belongs to the smallest outer ring that covers it. Anything that
    rule cannot place stops the build."""
    from shapely.geometry import Point, Polygon
    from shapely.prepared import prep
    outers, holes = [], []
    for ring in rings or []:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise SystemExit("FAIL: %s has a ring that is not closed" % what)
        area = _ring_area(ring)
        if area == 0:
            raise SystemExit("FAIL: %s has a ring with no area" % what)
        (outers if area < 0 else holes).append(ring)
    if not outers:
        raise SystemExit("FAIL: %s has no outer ring" % what)
    shells = [Polygon(r) for r in outers]
    ready = [prep(s) for s in shells]
    parts = [[r] for r in outers]
    for hole in holes:
        homes = [i for i, s in enumerate(ready)
                 if all(s.covers(Point(x, y)) for x, y in hole[:-1])]
        if not homes:
            raise SystemExit("FAIL: %s has a hole outside every outer ring" % what)
        parts[min(homes, key=lambda i: shells[i].area)].append(hole)
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def esri_features(data, what, key):
    """GeoJSON-shaped features from an ArcGIS JSON query answer. `key` names
    the attribute a failure message identifies a feature by."""
    sr = data.get("spatialReference") or {}
    if data.get("features") and 4326 not in (sr.get("wkid"), sr.get("latestWkid")):
        raise SystemExit("FAIL: %s answered in spatial reference %r, not 4326" % (what, sr))
    out = []
    for f in data.get("features") or []:
        attrs = f.get("attributes") or {}
        rings = (f.get("geometry") or {}).get("rings")
        out.append({"type": "Feature", "properties": attrs,
                    "geometry": (esri_polygon(rings, "%s %s %r" % (what, key, attrs.get(key)))
                                 if rings else None)})
    return out


def fetch_cousubs(url, parishes):
    """{parish3: {district: feature}} for the given parishes, full precision."""
    where = "STATE='%s' AND COUNTY IN (%s)" % (STATE, ",".join("'%s'" % c for c in sorted(parishes)))
    feats, offset = [], 0
    while True:
        page = _get(url, {
            "where": where, "outFields": "GEOID,COUNTY,BASENAME,FUNCSTAT",
            "outSR": "4326", "geometryPrecision": "6", "f": "json",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": 200,
        })
        got = esri_features(page, url, "GEOID")
        feats.extend(got)
        more = page.get("exceededTransferLimit")
        if not got or (len(got) < 200 and not more):
            break
        offset += len(got)
    out = {}
    for f in feats:
        p = f.get("properties") or {}
        c, d = p.get("COUNTY"), str(p.get("BASENAME") or "").strip()
        if not f.get("geometry"):
            raise SystemExit("FAIL: %s %s district %r has no geometry" % (url, c, d))
        if d in out.setdefault(c, {}):
            raise SystemExit("FAIL: %s parish %s carries district %r twice" % (url, c, d))
        out[c][d] = f
    return out


def fetch_blocks(parish3):
    """[(lng, lat, people)] for every populated 2020 block in the parish, at
    its internal point."""
    out, seen, offset = [], set(), 0
    while True:
        data = _get(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, parish3),
            "outFields": "GEOID,INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": PAGE,
            "f": "json",
        })
        feats = data.get("features") or []
        for f in feats:
            a = f["attributes"]
            if a["GEOID"] in seen:
                raise SystemExit("FAIL: block %s returned twice across pages" % a["GEOID"])
            seen.add(a["GEOID"])
            out.append((float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"])))
        if len(feats) < PAGE and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    return out


def tract_totals():
    """{parish3: people} from the 2020 tract layer, an aggregation this script
    does not perform — the witness that the block read is complete."""
    stats = json.dumps([{"statisticType": "sum", "onStatisticField": "POP100",
                         "outStatisticFieldName": "pop"}])
    data = _get(TRACTS, {"where": "STATE='%s'" % STATE, "groupByFieldsForStatistics": "COUNTY",
                         "outStatistics": stats, "f": "json"})
    return {f["attributes"]["COUNTY"]: int(f["attributes"]["pop"]) for f in data["features"]}


# ------------------------------------------------------------- measuring ----
def _index(features_by_district):
    return [(d, f["geometry"], blb._bbox(f["geometry"])) for d, f in features_by_district.items()]


def _where(model, x, y):
    return [d for d, geom, bb in model
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] and blb._point_in_geometry((x, y), geom)]


def assign(blocks, districts):
    """{district: people}, plus the people in no district and in two, and the
    per-block answers (for comparing two sets of lines block by block)."""
    model = _index(districts)
    pop = {d: 0 for d in districts}
    none = multi = 0
    answers = []
    for x, y, n in blocks:
        hits = _where(model, x, y)
        if len(hits) == 1:
            pop[hits[0]] += n
            answers.append(hits[0])
        elif not hits:
            none += n
            answers.append(None)
        else:
            multi += n
            answers.append("MULTI")
    return pop, none, multi, answers


def deviation_pct(pop):
    """Largest minus smallest district, as a percentage of an equal share."""
    vals = list(pop.values())
    if not vals:
        return float("inf")
    ideal = sum(vals) / float(len(vals))
    return 100.0 * (max(vals) - min(vals)) / ideal if ideal else float("inf")


def district_order(d):
    """Numbers in numeric order, then letters."""
    return (0, int(d), "") if d.isdigit() else (1, 0, d)


def measure_parish(cur, old, blocks):
    """The two confirmations for one parish, as numbers."""
    pop, none, multi, now = assign(blocks, cur)
    old_pop, _, _, then = assign(blocks, old) if old else ({}, 0, 0, [None] * len(blocks))
    moved = sum(n for (x, y, n), a, b in zip(blocks, now, then) if a != b)
    return {
        "people": sum(n for _, _, n in blocks),
        "deviation_pct": round(deviation_pct(pop), 2),
        "deviation_2020_edition_pct": round(deviation_pct(old_pop), 2) if old else None,
        "people_moved_from_2020_edition": moved,
        "people_in_no_district": none,
        "people_in_two_districts": multi,
        "district_people": {d: pop[d] for d in sorted(pop, key=district_order)},
    }


def parish_names():
    with open(PARISHES_FILE) as fh:
        fc = json.load(fh)
    return {f["properties"]["GEOID"]: f["properties"]["NAME"] for f in fc["features"]}, fc


def roster_seats(o):
    """{district: seat word} for a parish's district seats in the Secretary
    of State's list, from its named seats and the seats it names no one for.
    A seat the list prints twice (two members elected from one district) is
    one district."""
    out = {}
    for label in [s.get("seat") for s in (o.get("seats") or [])] + list(o.get("unlisted") or []):
        m = SEAT_RE.match(str(label or ""))
        if not m:
            raise SystemExit("FAIL: %s seat %r is not a district" % (o.get("parish"), label))
        out[m.group(2)] = m.group(1)
    return out


def roster_problems(roster, drawn, cur=None):
    """The list must name a seat for exactly the districts the map draws, in
    one word per parish, and every one of them by name. `cur` (at build time)
    is the Census's districts; --check reads the shipped file instead."""
    problems = []
    for geoid in sorted(drawn):
        o = roster.get(geoid)
        if not o:
            problems.append("%s: no entry in la-parish-officials.json" % geoid)
            continue
        seats = roster_seats(o)
        if len(set(seats.values())) != 1:
            problems.append("%s: the list calls its districts %s" % (geoid, sorted(set(seats.values()))))
        if o.get("unlisted"):
            problems.append("%s: the list names no one for %s, so this parish's districts are "
                            "not drawn until it does" % (geoid, o.get("unlisted")))
        if cur is not None:
            census = sorted(cur.get(geoid[2:]) or {}, key=district_order)
            listed = sorted(seats, key=district_order)
            if census != listed:
                problems.append("%s: the Census draws districts %s and the list has seats for %s"
                                % (geoid, census, listed))
        counts = {}
        for s in o.get("seats") or []:
            m = SEAT_RE.match(str(s.get("seat") or ""))
            if m:
                counts[m.group(2)] = counts.get(m.group(2), 0) + 1
        double = sorted(d for d, n in counts.items() if n > 1)
        if double:
            problems.append("%s: the list elects more than one member from district(s) %s, "
                            "which the card is not written for" % (geoid, double))
    return problems


def expected_districts():
    """{parish GEOID: lines}: which parishes are drawn, and from what."""
    return {STATE + c: "census" for c in CENSUS_PARISHES}


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FEATURE_KEYS = {"parishfips", "parish", "district", "label", "body", "lines"}


def structure_problems(features, names, roster, expected):
    problems = []
    by = {}
    for f in features:
        p = f.get("properties") or {}
        geoid = p.get("parishfips")
        where = "%s district %s" % (geoid, p.get("district"))
        by.setdefault(geoid, []).append(str(p.get("district")))
        extra = sorted(set(p) - FEATURE_KEYS)
        missing = sorted(FEATURE_KEYS - set(p))
        if extra or missing:
            problems.append("%s: properties carry %s and lack %s" % (where, extra, missing))
        if p.get("parish") != names.get(geoid):
            problems.append("%s carries parish name %r, state-counties.json says %r"
                            % (where, p.get("parish"), names.get(geoid)))
        o = roster.get(geoid) or {}
        if p.get("body") != o.get("body"):
            problems.append("%s: body %r, the list says %r" % (where, p.get("body"), o.get("body")))
        word = roster_seats(o).get(str(p.get("district"))) if o else None
        if p.get("label") != word:
            problems.append("%s: labelled %r and the list says %r" % (where, p.get("label"), word))
        if p.get("lines") != expected.get(geoid):
            problems.append("%s: lines %r, expected %r" % (where, p.get("lines"), expected.get(geoid)))
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            problems.append("%s: geometry %r" % (where, g.get("type")))
    if set(by) != set(expected):
        problems.append("drawn parishes %s, expected %s" % (sorted(by), sorted(expected)))
    for geoid, ds in sorted(by.items()):
        o = roster.get(geoid) or {}
        want = sorted(roster_seats(o), key=district_order) if o else []
        if sorted(ds, key=district_order) != want or len(ds) != len(set(ds)):
            problems.append("%s draws districts %s, the list has seats for %s"
                            % (geoid, sorted(ds, key=district_order), want))
    return problems


def _edge_index(parish_feats):
    return {g: blb._seg_index(f) for g, f in parish_feats.items()}


def _near_line(pt, seg_idx, metres):
    gx, gy = int(math.floor(pt[0] / 0.02)), int(math.floor(pt[1] / 0.02))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for a, b in seg_idx.get((gx + dx, gy + dy), ()):
                if blb._point_to_segment_m(pt, a, b) <= metres:
                    return True
    return False


def parish_witness(features, parishes_fc, drawn, samples=WITNESS_SAMPLES, seed=2026):
    """Points over the drawn parishes: the Parish layer and this layer must
    agree about the parish, except within EDGE_M of a parish line."""
    parish_feats = {f["properties"]["GEOID"]: f for f in parishes_fc["features"]}
    pmodel = [(g, f["geometry"], blb._bbox(f["geometry"])) for g, f in parish_feats.items()]
    dmodel = [((f["properties"]["parishfips"], str(f["properties"]["district"])),
               f["geometry"], blb._bbox(f["geometry"])) for f in features]
    edges = _edge_index({g: parish_feats[g] for g in drawn})
    box = [1e9, 1e9, -1e9, -1e9]
    for g in drawn:
        b = blb._bbox(parish_feats[g]["geometry"])
        box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
    rng = random.Random(seed)
    inside = agree = edge = 0
    bad = []
    for _ in range(samples):
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        ps = [g for g, geom, bb in pmodel
              if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        ds = [k for k, geom, bb in dmodel
              if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        parish = ps[0] if len(ps) == 1 else None
        if parish in drawn:
            inside += 1
        ok = (len(ds) == 1 and ds[0][0] == parish) if parish in drawn else (not ds)
        if ok:
            agree += 1
            continue
        if any(_near_line(pt, edges[g], EDGE_M) for g in drawn):
            edge += 1
        else:
            bad.append((round(pt[1], 5), round(pt[0], 5), parish, ds))
    return inside, agree, edge, bad


def agreement(src_feats, out_feats, drawn_box, samples=AGREEMENT_SAMPLES, seed=2024):
    """The fleet's 2,000-point protocol, sampled where the districts are: only
    points inside a source district count toward the 2,000."""
    def key(f):
        return (f["properties"]["parishfips"], str(f["properties"]["district"]))
    src = [(key(f), f["geometry"], blb._bbox(f["geometry"])) for f in src_feats]
    new = [(key(f), f["geometry"], blb._bbox(f["geometry"])) for f in out_feats]
    rng = random.Random(seed)
    n = agree = overlaps = tries = 0
    while n < samples:
        tries += 1
        if tries > samples * 200:
            raise SystemExit("FAIL: could not place %d points inside the districts" % samples)
        pt = (rng.uniform(drawn_box[0], drawn_box[2]), rng.uniform(drawn_box[1], drawn_box[3]))
        o = [k for k, g, bb in src if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
             and blb._point_in_geometry(pt, g)]
        if not o:
            continue
        n += 1
        s = [k for k, g, bb in new if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
             and blb._point_in_geometry(pt, g)]
        if len(s) > 1:
            overlaps += 1
        if len(o) == 1 and len(s) == 1 and o[0] == s[0]:
            agree += 1
    return agree, n, overlaps


def measure_census_parish(c3, nm, cur, old, tracts):
    """The Census's own lines in one CENSUS_PARISHES parish: (measurements,
    the block points they were taken on, problems)."""
    ds = cur.get(c3) or {}
    problems = []
    if not ds:
        return None, None, ["the Census draws no districts here"]
    bad_func = sorted(d for d, f in ds.items() if (f["properties"].get("FUNCSTAT") or "") != "N")
    if bad_func:
        problems.append("districts %s are not nonfunctioning subdivisions — a functioning one "
                        "is a government of its own, not a governing-body district" % bad_func)
    blocks = fetch_blocks(c3)
    m = measure_parish(ds, old.get(c3), blocks)
    if m["people"] != tracts.get(c3):
        problems.append("blocks sum to %d, tracts to %s" % (m["people"], tracts.get(c3)))
    if m["people_in_no_district"] or m["people_in_two_districts"]:
        problems.append("%d people in no district and %d in two"
                        % (m["people_in_no_district"], m["people_in_two_districts"]))
    if m["deviation_pct"] > MAX_DEVIATION_PCT:
        problems.append("the districts differ by %.2f%% of an equal share on 2020 population "
                        "(ceiling %.0f%%) — not shown to be lines drawn on the 2020 census"
                        % (m["deviation_pct"], MAX_DEVIATION_PCT))
    if m["people_moved_from_2020_edition"] < MIN_PEOPLE_MOVED:
        problems.append("the 2026 lines move %d people from the 2020 edition's — no evidence "
                        "the parish sent the Census new lines"
                        % m["people_moved_from_2020_edition"])
    print("%-12s %7d people  %2d districts  %5.2f%% now, %6.2f%% on the 2020 edition's lines, "
          "%6d people's district moved"
          % (nm, m["people"], len(ds), m["deviation_pct"], m["deviation_2020_edition_pct"],
             m["people_moved_from_2020_edition"]), file=sys.stderr)
    return m, blocks, problems


def build():
    names, parishes_fc = parish_names()
    with open(ROSTER_FILE) as fh:
        roster = json.load(fh)
    expected = expected_districts()
    for c3, nm in sorted(CENSUS_PARISHES.items()):
        if names.get(STATE + c3) != nm + " Parish":
            raise SystemExit("FAIL: %s%s is %r in state-counties.json, this builder says %r"
                             % (STATE, c3, names.get(STATE + c3), nm))

    name, desc = _layer_name(CURRENT)
    if name != CURRENT_NAME or CURRENT_VINTAGE not in desc:
        raise SystemExit("FAIL: %s is now %r (%r), not the %s %s — re-take the survey "
                         "before drawing a different vintage"
                         % (CURRENT, name, desc[:80], CURRENT_VINTAGE, CURRENT_NAME))

    built = datetime.date.today().isoformat()
    cur = fetch_cousubs(CURRENT, CENSUS_PARISHES)
    old = fetch_cousubs(EDITION_2020, CENSUS_PARISHES)
    problems = roster_problems(roster, set(expected), cur)
    if problems:
        raise SystemExit("FAIL (the Secretary of State's list):\n  " + "\n  ".join(problems))
    tracts = tract_totals()
    record, pts, failures = {}, {}, []
    for c3 in sorted(CENSUS_PARISHES):
        m, blocks, found = measure_census_parish(c3, CENSUS_PARISHES[c3], cur, old, tracts)
        failures += ["%s: %s" % (CENSUS_PARISHES[c3], p) for p in found]
        if m is not None:
            record[c3], pts[c3] = m, blocks
    if failures:
        raise SystemExit("FAIL:\n  " + "\n  ".join(failures))

    src_feats = []
    for geoid in sorted(expected):
        c3 = geoid[2:]
        seats = roster_seats(roster[geoid])
        for d in sorted(cur[c3], key=district_order):
            props = {"parishfips": geoid, "parish": names[geoid], "district": d,
                     "label": seats[d], "body": roster[geoid]["body"],
                     "lines": expected[geoid], "key": geoid + "-" + d}
            src_feats.append({"type": "Feature", "properties": props,
                              "geometry": cur[c3][d]["geometry"]})
    with tempfile.TemporaryDirectory() as tmp:
        sp = os.path.join(tmp, "src.geojson")
        with open(sp, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": src_feats}, fh)
        op = os.path.join(tmp, "out.geojson")
        blb.run_mapshaper(sp, SIMPLIFY, op)
        with open(op) as fh:
            simplified = json.load(fh)
    out_feats = simplified["features"]

    box = [1e9, 1e9, -1e9, -1e9]
    for f in src_feats:
        b = blb._bbox(f["geometry"])
        box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
    agree, n, overlaps = agreement(src_feats, out_feats, box)
    if overlaps or agree < 0.995 * n:
        raise SystemExit("FAIL: %d/%d points agree with the full-precision lines and %d "
                         "fall in two districts" % (agree, n, overlaps))
    step = blb.median_source_step_m(src_feats)
    worst, over = blb.check_fidelity(src_feats, out_feats, "key")
    if over:
        raise SystemExit("FAIL: %d district(s) stray past the %.0f m ceiling (worst %.1f m): %s"
                         % (len(over), blb.FIDELITY_CEILING_M, worst, ", ".join(sorted(over)[:5])))
    print("parish-districts: %d/%d points agree, 0 in two districts; median source step "
          "%.2f m, worst stray %.1f m against a %.0f m ceiling"
          % (agree, n, step, worst, blb.FIDELITY_CEILING_M), file=sys.stderr)

    # What simplification costs in people: each block's district under the
    # drawn lines against the full-precision lines.
    by_parish_out = {}
    for f in out_feats:
        p = f["properties"]
        by_parish_out.setdefault(p["parishfips"][2:], {})[str(p["district"])] = f
    for c3, m in sorted(record.items()):
        _, _, _, drawn_answers = assign(pts[c3], by_parish_out[c3])
        _, _, _, true_answers = assign(pts[c3], cur[c3])
        shifted = sum(n for (x, y, n), a, b in zip(pts[c3], drawn_answers, true_answers) if a != b)
        m["simplification_people_moved"] = shifted
        if shifted > 0.01 * m["people"]:
            raise SystemExit("FAIL: simplifying moves %d of %s Parish's %d people across a line"
                             % (shifted, CENSUS_PARISHES[c3], m["people"]))
    print("parish-districts: simplifying moves %s across a district line"
          % ", ".join("%d of %s's %d people" % (m["simplification_people_moved"],
                                                CENSUS_PARISHES[c3], m["people"])
                      for c3, m in sorted(record.items())), file=sys.stderr)

    for f in out_feats:
        f["properties"].pop("key", None)
    problems = structure_problems(out_feats, names, roster, expected)
    if problems:
        raise SystemExit("FAIL (structure after simplifying):\n  " + "\n  ".join(problems))
    inside, agreed, edge, bad = parish_witness(out_feats, parishes_fc, set(expected))
    if bad:
        raise SystemExit("FAIL: the Parish layer and this one disagree about the parish at %d "
                         "point(s) away from any parish line, e.g. %s" % (len(bad), bad[:3]))
    print("parish-districts: parish witness %d/%d points agree (%d inside the drawn parishes); "
          "%d differ within %.0f m of a parish line"
          % (agreed, WITNESS_SAMPLES, inside, edge, EDGE_M), file=sys.stderr)

    fc = {"type": "FeatureCollection", "features": sorted(
        out_feats, key=lambda f: (f["properties"]["parishfips"],
                                  district_order(str(f["properties"]["district"]))))}
    compact = json.dumps(fc, separators=(",", ":"), ensure_ascii=False)
    if json.loads(compact) != fc:
        raise SystemExit("FAIL: round-trip mismatch before writing")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(compact)
    write_parish_list(fc["features"])
    parishes = {}
    for c3, m in sorted(record.items()):
        geoid = STATE + c3
        parishes[geoid] = dict(parish=names[geoid], lines=expected[geoid],
                               districts=len(cur[c3]), **m)
    rec = {
        "_about": ("GENERATED by la/scripts/build_la_parish_districts.py. What each drawn "
                   "parish's lines were measured against when the shipped file was built: "
                   "the Census's own 2020 blocks, its 2020 edition of the same county "
                   "subdivisions, and its block total against its tract total. --check holds "
                   "the shipped file to this record."),
        "built": built,
        "source": CURRENT,
        "vintage": CURRENT_VINTAGE,
        "edition_2020": EDITION_2020,
        "max_deviation_pct": MAX_DEVIATION_PCT,
        "parishes": parishes,
    }
    os.makedirs(SOURCE_DIR, exist_ok=True)
    with open(RECORD, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("parish-districts -> %s: %d districts in %d parishes, %d bytes (dp %s)"
          % (os.path.relpath(OUT, INSTANCE), len(fc["features"]), len(expected),
             len(compact.encode("utf-8")), SIMPLIFY), file=sys.stderr)


def parish_list(features):
    """{GEOID: parish name} for every parish the districts file draws, in
    GEOID order: what la-parish-district-parishes.json must hold."""
    out = {}
    for f in features:
        p = f.get("properties") or {}
        out[p.get("parishfips")] = p.get("parish")
    return dict(sorted(out.items()))


def write_parish_list(features):
    listed = parish_list(features)
    with open(PARISH_LIST, "w", encoding="utf-8") as fh:
        json.dump(listed, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return listed


# --------------------------------------------------------------- --check ----
def record_problems(rec, expected, features):
    """The record's measurements, held to the gates the build applied."""
    problems = []
    recorded = rec.get("parishes") or {}
    if set(recorded) != set(expected):
        problems.append("the record names parishes %s, the builder %s"
                        % (sorted(recorded), sorted(expected)))
    drawn = {}
    for f in features:
        p = f.get("properties") or {}
        drawn.setdefault(p.get("parishfips"), set()).add(str(p.get("district")))
    for geoid, m in sorted(recorded.items()):
        if m.get("lines") != expected.get(geoid):
            problems.append("%s: recorded lines %r, the builder says %r"
                            % (geoid, m.get("lines"), expected.get(geoid)))
        if m.get("deviation_pct") is None or m["deviation_pct"] > MAX_DEVIATION_PCT:
            problems.append("%s: recorded deviation %r" % (geoid, m.get("deviation_pct")))
        if (m.get("people_moved_from_2020_edition") or 0) < MIN_PEOPLE_MOVED:
            problems.append("%s: recorded %r people moved from the 2020 edition"
                            % (geoid, m.get("people_moved_from_2020_edition")))
        people = m.get("district_people") or {}
        if sum(people.values()) != m.get("people"):
            problems.append("%s: district totals do not sum to the parish's people" % geoid)
        if set(people) != drawn.get(geoid, set()) or m.get("districts") != len(people):
            problems.append("%s: the record measured districts %s and the file draws %s"
                            % (geoid, sorted(people), sorted(drawn.get(geoid, set()))))
        if (m.get("simplification_people_moved") or 0) > 0.01 * (m.get("people") or 0):
            problems.append("%s: simplifying moved %r people"
                            % (geoid, m.get("simplification_people_moved")))
    if not _ISO_DATE.match(str(rec.get("built") or "")):
        problems.append("the record's build date %r is not a date" % rec.get("built"))
    return problems


def check():
    names, parishes_fc = parish_names()
    with open(ROSTER_FILE) as fh:
        roster = json.load(fh)
    with open(OUT) as fh:
        fc = json.load(fh)
    with open(RECORD) as fh:
        rec = json.load(fh)
    expected = expected_districts()
    feats = fc.get("features") or []
    problems = structure_problems(feats, names, roster, expected)
    problems += roster_problems(roster, set(expected))
    problems += record_problems(rec, expected, feats)
    # The app's coverage test reads the list, not the districts, so a list
    # naming a parish the districts file does not draw shows the layer with
    # nothing to answer, and one missing a parish hides districts that exist.
    try:
        with open(PARISH_LIST) as fh:
            listed = json.load(fh)
    except (OSError, ValueError) as e:
        listed = None
        problems.append("la-parish-district-parishes.json does not read: %s" % e)
    drawn = parish_list(feats)
    if listed is not None and listed != drawn:
        problems.append("la-parish-district-parishes.json lists %r and the districts file "
                        "draws %r; rebuild" % (listed, drawn))
    # The card names the edition in words ("January 1, 2026 edition"), so a
    # rebuild from a new vintage that left the card alone would tell a reader
    # the wrong edition. Both are held to the record here.
    if rec.get("vintage") != CURRENT_VINTAGE:
        problems.append("the record was built from the %r layer and CURRENT_VINTAGE is %r"
                        % (rec.get("vintage"), CURRENT_VINTAGE))
    with open(os.path.join(INSTANCE, "index.html"), encoding="utf-8") as fh:
        if "(%s edition)" % rec.get("vintage") not in fh.read():
            problems.append("la/index.html's district card does not name the %s edition the "
                            "shipped file was built from" % rec.get("vintage"))
    inside, agreed, edge, bad = parish_witness(feats, parishes_fc, set(expected))
    if bad:
        problems.append("the Parish layer and this one disagree about the parish at %d "
                        "point(s) away from any parish line, e.g. %s" % (len(bad), bad[:3]))
    if problems:
        print("FAIL: la-parish-districts.json\n  " + "\n  ".join(problems))
        return 1
    devs = sorted(m["deviation_pct"] for m in rec["parishes"].values())
    print("OK: la-parish-districts.json draws %d districts in %d parishes, each with a seat in "
          "the Secretary of State's list; recorded deviations %.2f%%-%.2f%% on 2020 population "
          "(ceiling %.0f%%, measured at build, not re-measured here); parish witness %d/%d "
          "agree, %d differ within %.0f m of a parish line"
          % (len(feats), len(expected), devs[0], devs[-1], MAX_DEVIATION_PCT, agreed,
             WITNESS_SAMPLES, edge, EDGE_M))
    return 0


# -------------------------------------------------------------- --survey ----
def survey():
    """Every parish's two measurements, printed; writes nothing."""
    names, _ = parish_names()
    with open(ROSTER_FILE) as fh:
        roster = json.load(fh)
    allp = sorted(g[2:] for g in names)
    cur = fetch_cousubs(CURRENT, allp)
    old = fetch_cousubs(EDITION_2020, allp)
    for c3 in allp:
        geoid = STATE + c3
        ds = cur.get(c3) or {}
        try:
            seats = sorted(roster_seats(roster.get(geoid) or {}), key=district_order)
        except SystemExit as e:
            seats = [str(e)]
        census = sorted(ds, key=district_order)
        if census != seats:
            print("%s %-28s the Census draws %s and the list has seats for %s"
                  % (c3, names[geoid], census, seats))
            continue
        m = measure_parish(ds, old.get(c3), fetch_blocks(c3))
        current = (m["deviation_pct"] <= MAX_DEVIATION_PCT
                   and m["people_moved_from_2020_edition"] >= MIN_PEOPLE_MOVED)
        verdict = ("CURRENT" if current else
                   "unchanged, balanced" if m["deviation_pct"] <= MAX_DEVIATION_PCT else
                   "changed, unbalanced" if m["people_moved_from_2020_edition"] >= MIN_PEOPLE_MOVED
                   else "stale")
        listed = ("drawn" if c3 in CENSUS_PARISHES else "NOT LISTED" if current else "")
        print("%s %-28s %6.2f%% now  %6.2f%% 2020 edition  %6d moved  %-20s %s"
              % (c3, names[geoid], m["deviation_pct"], m["deviation_2020_edition_pct"] or -1,
                 m["people_moved_from_2020_edition"], verdict, listed))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    ap.add_argument("--survey", action="store_true", help="measure all 64 parishes, write nothing")
    args = ap.parse_args()
    if args.check:
        return check()
    if args.survey:
        return survey()
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
