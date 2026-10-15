#!/usr/bin/env python3
"""
Build ms/data/app/ms-supervisor-districts.json: the county supervisor
districts of the Mississippi counties whose CURRENT lines this app has
confirmed, so the app can say which of a county's five supervisors represents
a point. The County card names all five in every county; this layer draws the
district only where its lines are known to be the ones in force.

WHERE THE LINES COME FROM. Every Mississippi county elects five supervisors,
each from a district (five counties call them "beats"). The Census Bureau
carries all 410 districts as county subdivisions: TIGERweb's current layer
(tigerWMS_Current, layer 22, "January 1, 2026 vintage") has BASENAME 1 to 5 in
every county, every one nonfunctioning (FUNCSTAT N), which is how the Census
files a supervisor district. No state office publishes a statewide map of the
current lines, measured 2026-10-15.

WHY MOST COUNTIES ARE NOT DRAWN. Counties redrew their districts after the
2020 census, and in most of them the Census never received the new lines: the
2026 layer still carries the lines in its own 2020 edition (tigerWMS_Census2020,
layer 20), which are the lines drawn after the 2010 census. Those lines would
name the wrong supervisor for many readers. The planning measurement found
the old lines put 34% of Madison County's residents in a different district
from the one they now vote in, 16% of Lee's and 9.5% of Harrison's.

WHAT CONFIRMS A COUNTY. Two measurements, both re-taken on every build from
the Census's own data, for every county in CENSUS_COUNTIES:

  1. Its 2026 lines differ from the 2020 edition's, so the county sent the
     Census new lines after the 2020 census. The witness is people, not area:
     the build counts the residents whose district NUMBER the change moved
     (each 2020 census block assigned by its internal point).
  2. On the 2020 census's own block counts the five districts hold nearly
     equal numbers of people: the largest and smallest differ by no more than
     MAX_DEVIATION_PCT percent of an equal share. Lines drawn to balance on
     the 2020 census pass this; lines drawn on the 2010 census mostly do not.

Measured 2026-10-15 across all 82 counties (`--survey` re-takes it): 12
counties pass both, at 3.2% to 9.0%, and their 2020-edition lines measure
15.6% to 85.6% on the same blocks. Of the 70 counties whose 2026 lines ARE the
2020 edition's, 64 measure more than 10%, and six measure under it —
Lafayette 2.5%, Marshall 6.1%, Montgomery 6.2%, Jefferson Davis 6.8%,
Walthall 7.7% and Marion 7.8%. Those six are NOT drawn: their lines balance on
2020 population, so a county may have kept them, but it may equally have
redrawn them and never told the Census, and nothing here can tell which. A
county's own published map, or its answer to a letter, is what settles one of
them. Marion's 2026 layer differs from its 2020 edition by a sliver on the
line between districts 4 and 5 (about 19 m2, 0.0000027% of the county,
measured 2026-10-15). It moves nobody, so `--survey` reports 0 people moved
and the test does not count it as a change.

GATES BEFORE ANYTHING IS WRITTEN:
  - every drawn county has exactly five districts numbered 1 to 5;
  - the Secretary of State's directory (ms-county-officials.json) names a
    supervisor, or a vacancy, for each of those five districts, in the
    county's own word ("District" or "Beat");
  - the two confirmations above, with every populated 2020 block in exactly
    one district, and the county's block total equal to its tract total;
  - the fleet's 2,000-point agreement test between the simplified districts
    and the full-precision fetch, sampled inside the drawn counties;
  - the fidelity ceiling the legislative builder pins (no source vertex more
    than build_legislative_boundaries.FIDELITY_CEILING_M from its district as
    drawn), and the people simplification moves across a line, printed;
  - the county witness: at points sampled over the drawn counties, a point
    the County layer (state-counties.json) puts in a drawn county must lie in
    one of THAT county's districts, and a point it puts elsewhere in none,
    except within EDGE_M of a county line, where two simplified files may
    differ by their two strays.

SIMPLIFICATION. Douglas-Peucker in metres, the legislative builder's method,
for the reason its docstring gives, and ALL DRAWN COUNTIES IN ONE MAPSHAPER
RUN, so a line two districts share — inside a county or where two drawn
counties meet — is one arc simplified once.

WHAT `--check` CAN AND CANNOT SEE. It is offline and runs in CI: the shipped
file's counties, numbering and county names, the roster join, the record in
data/source/ms-supervisor-districts.source.json, the Census edition the app's
card names, and the county witness against the shipped state-counties.json. It cannot re-measure population, because the
blocks are not shipped; the deviations it prints are the ones the build
measured and recorded, and a hand edit to them is not something it can catch.

robots.txt: tigerweb.geo.census.gov serves a 189-byte HTML page at
/robots.txt rather than a policy (HTTP 200, read 2026-10-15), which the shared
reader takes as no robots.txt, so every path is allowed. It is read through
scraper_common.require_robots_once before the first fetch, with the same client
the fetches send.

Prerequisites: Node.js (mapshaper via `npx mapshaper@<pinned>`).

Usage:
    python3 ms/scripts/build_ms_supervisor_districts.py           # fetch, build, write
    python3 ms/scripts/build_ms_supervisor_districts.py --check   # offline gate (CI)
    python3 ms/scripts/build_ms_supervisor_districts.py --survey  # all 82 counties, writes nothing
"""

import argparse
import datetime
import json
import math
import os
import random
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
OUT = os.path.join(APP_DATA_DIR, "ms-supervisor-districts.json")
RECORD = os.path.join(SOURCE_DIR, "ms-supervisor-districts.source.json")
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")
ROSTER_FILE = os.path.join(APP_DATA_DIR, "ms-county-officials.json")

USER_AGENT = "districtry/1.0 (+https://districtry.com/ms/)"
TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
CURRENT = TIGERWEB + "tigerWMS_Current/MapServer/22"
CURRENT_NAME = "County Subdivisions"
CURRENT_VINTAGE = "January 1, 2026"
EDITION_2020 = TIGERWEB + "tigerWMS_Census2020/MapServer/20"
BLOCKS = TIGERWEB + "Tracts_Blocks/MapServer/12"   # Census 2020 blocks, POP100
TRACTS = TIGERWEB + "Tracts_Blocks/MapServer/10"   # Census 2020 tracts, POP100
STATE = "28"

# The counties whose Census lines are confirmed current, by three-digit code.
# STATED, never derived: `--survey` prints any county that newly passes both
# tests (when the Census rolls a vintage) and a person adds it here after
# looking, because a county passing a population test is a reason to look and
# not yet a reason to draw.
CENSUS_COUNTIES = {
    "019": "Choctaw",
    "025": "Clay",
    "033": "DeSoto",
    "043": "Grenada",
    "077": "Lawrence",
    "087": "Lowndes",
    "099": "Neshoba",
    "103": "Noxubee",
    "105": "Oktibbeha",
    "137": "Tate",
    "155": "Webster",
    "159": "Winston",
}

DISTRICTS = ("1", "2", "3", "4", "5")
MAX_DEVIATION_PCT = 10.0
# A change smaller than this many residents is not counted as new lines: it is
# the size of a boundary correction, not of a redistricting plan. Measured
# 2026-10-15, the smallest change among the twelve moves 530 people (Choctaw),
# and Clay's, which covers 0.07% of the county's area, moves 689.
MIN_PEOPLE_MOVED = 50
SIMPLIFY = "interval=20"
EDGE_M = 60.0               # two simplified files, each within the 25 m ceiling
AGREEMENT_SAMPLES = 2000
WITNESS_SAMPLES = 4000
PAGE = 20000


# ---------------------------------------------------------------- fetching --
def _get(url, params):
    q = url + "/query?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            require_robots_once(q, USER_AGENT, headers={"User-Agent": USER_AGENT},
                                label="ms-build-ms-supervisor-districts")
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
            print("supervisor-districts: retrying after %s" % err, file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def _layer_name(url):
    req = urllib.request.Request(url + "?f=json", headers={"User-Agent": USER_AGENT})
    require_robots_once(url, USER_AGENT, headers={"User-Agent": USER_AGENT},
                        label="ms-build-ms-supervisor-districts")
    with urllib.request.urlopen(req, timeout=120) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    return meta.get("name"), meta.get("description") or ""


def fetch_cousubs(url, counties):
    """{county3: {district: feature}} for the given counties, full precision."""
    where = "STATE='%s' AND COUNTY IN (%s)" % (STATE, ",".join("'%s'" % c for c in sorted(counties)))
    feats, offset = [], 0
    while True:
        page = _get(url, {
            "where": where, "outFields": "GEOID,COUNTY,BASENAME,FUNCSTAT",
            "outSR": "4326", "geometryPrecision": "6", "f": "geojson",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": 1000,
        })
        got = page.get("features") or []
        feats.extend(got)
        more = page.get("exceededTransferLimit") or (page.get("properties") or {}).get(
            "exceededTransferLimit")
        if not got or (len(got) < 1000 and not more):
            break
        offset += len(got)
    out = {}
    for f in feats:
        p = f.get("properties") or {}
        c, d = p.get("COUNTY"), str(p.get("BASENAME") or "").strip()
        if not f.get("geometry"):
            raise SystemExit("FAIL: %s %s district %r has no geometry" % (url, c, d))
        if d in out.setdefault(c, {}):
            raise SystemExit("FAIL: %s county %s carries district %r twice" % (url, c, d))
        out[c][d] = f
    return out


def fetch_blocks(county3):
    """[(lng, lat, people)] for every populated 2020 block in the county."""
    out, seen, offset = [], set(), 0
    while True:
        data = _get(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, county3),
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
    """{county3: people} from the 2020 tract layer, an aggregation this script
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
    hits = [d for d, geom, bb in model
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] and blb._point_in_geometry((x, y), geom)]
    return hits


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
    vals = [pop.get(d, 0) for d in DISTRICTS]
    ideal = sum(vals) / 5.0
    return 100.0 * (max(vals) - min(vals)) / ideal if ideal else float("inf")


def measure_county(c3, cur, old, blocks):
    """The two confirmations for one county, as numbers."""
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
        "district_people": {d: pop[d] for d in DISTRICTS if d in pop},
    }


# ------------------------------------------------------------- the build ----
def county_names():
    with open(COUNTIES_FILE) as fh:
        fc = json.load(fh)
    return {f["properties"]["GEOID"]: f["properties"]["NAME"] for f in fc["features"]}, fc


def roster_problems(roster, drawn):
    """The directory must name the same five districts the map draws."""
    problems = []
    for geoid in sorted(drawn):
        o = roster.get(geoid)
        if not o:
            problems.append("%s: no entry in ms-county-officials.json" % geoid)
            continue
        if o.get("label") not in ("District", "Beat"):
            problems.append("%s: directory label %r" % (geoid, o.get("label")))
        got = sorted(str(s.get("district")) for s in o.get("supervisors") or [])
        if got != list(DISTRICTS):
            problems.append("%s: the directory names districts %s, the map draws 1-5"
                            % (geoid, got))
        for s in o.get("supervisors") or []:
            if not (s.get("name") or s.get("vacant") is True):
                problems.append("%s district %s: neither a name nor a vacancy"
                                % (geoid, s.get("district")))
    return problems


def structure_problems(features, names, expected):
    problems = []
    by = {}
    for f in features:
        p = f.get("properties") or {}
        by.setdefault(p.get("countyfips"), []).append(str(p.get("district")))
        if p.get("county") != names.get(p.get("countyfips")):
            problems.append("%s district %s carries county name %r, state-counties.json "
                            "says %r" % (p.get("countyfips"), p.get("district"),
                                         p.get("county"), names.get(p.get("countyfips"))))
        if p.get("label") not in ("District", "Beat"):
            problems.append("%s district %s: label %r" % (p.get("countyfips"),
                                                          p.get("district"), p.get("label")))
        if p.get("lines") != "census":
            problems.append("%s district %s: lines %r" % (p.get("countyfips"),
                                                          p.get("district"), p.get("lines")))
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            problems.append("%s district %s: geometry %r" % (p.get("countyfips"),
                                                             p.get("district"), g.get("type")))
    if set(by) != set(expected):
        problems.append("drawn counties %s, expected %s"
                        % (sorted(by), sorted(expected)))
    for geoid, ds in sorted(by.items()):
        if sorted(ds) != list(DISTRICTS):
            problems.append("%s draws districts %s, not 1-5" % (geoid, sorted(ds)))
    return problems


def _edge_index(county_feats):
    return {g: blb._seg_index(f) for g, f in county_feats.items()}


def _near_line(pt, seg_idx, metres):
    gx, gy = int(math.floor(pt[0] / 0.02)), int(math.floor(pt[1] / 0.02))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for a, b in seg_idx.get((gx + dx, gy + dy), ()):
                if blb._point_to_segment_m(pt, a, b) <= metres:
                    return True
    return False


def county_witness(features, counties_fc, drawn, samples=WITNESS_SAMPLES, seed=2026):
    """Points over the drawn counties: the County layer and this layer must
    agree about the county, except within EDGE_M of a county line."""
    county_feats = {f["properties"]["GEOID"]: f for f in counties_fc["features"]}
    cmodel = [(g, f["geometry"], blb._bbox(f["geometry"])) for g, f in county_feats.items()]
    dmodel = [((f["properties"]["countyfips"], str(f["properties"]["district"])),
               f["geometry"], blb._bbox(f["geometry"])) for f in features]
    edges = _edge_index({g: county_feats[g] for g in drawn})
    box = [1e9, 1e9, -1e9, -1e9]
    for g in drawn:
        b = blb._bbox(county_feats[g]["geometry"])
        box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
    rng = random.Random(seed)
    inside = agree = edge = 0
    bad = []
    for _ in range(samples):
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        cs = [g for g, geom, bb in cmodel
              if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        ds = [k for k, geom, bb in dmodel
              if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3]
              and blb._point_in_geometry(pt, geom)]
        county = cs[0] if len(cs) == 1 else None
        if county in drawn:
            inside += 1
        ok = (len(ds) == 1 and ds[0][0] == county) if county in drawn else (not ds)
        if ok:
            agree += 1
            continue
        near = any(_near_line(pt, edges[g], EDGE_M) for g in drawn)
        if near:
            edge += 1
        else:
            bad.append((round(pt[1], 5), round(pt[0], 5), county, ds))
    return inside, agree, edge, bad


def agreement(src_feats, out_feats, drawn_box, samples=AGREEMENT_SAMPLES, seed=2024):
    """The fleet's 2,000-point protocol, sampled where the districts are: only
    points inside a source district count toward the 2,000."""
    def key(f):
        return (f["properties"]["countyfips"], str(f["properties"]["district"]))
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


def build(args):
    names, counties_fc = county_names()
    with open(ROSTER_FILE) as fh:
        roster = json.load(fh)
    drawn = {STATE + c for c in CENSUS_COUNTIES}
    for c3, nm in CENSUS_COUNTIES.items():
        if names.get(STATE + c3) != nm + " County":
            raise SystemExit("FAIL: %s%s is %r in state-counties.json, CENSUS_COUNTIES "
                             "says %r" % (STATE, c3, names.get(STATE + c3), nm))
    problems = roster_problems(roster, drawn)
    if problems:
        raise SystemExit("FAIL (roster):\n  " + "\n  ".join(problems))

    name, desc = _layer_name(CURRENT)
    if name != CURRENT_NAME or CURRENT_VINTAGE not in desc:
        raise SystemExit("FAIL: %s is now %r (%r), not the %s %s — re-take the survey "
                         "before drawing a different vintage"
                         % (CURRENT, name, desc[:80], CURRENT_VINTAGE, CURRENT_NAME))

    cur = fetch_cousubs(CURRENT, CENSUS_COUNTIES)
    old = fetch_cousubs(EDITION_2020, CENSUS_COUNTIES)
    tracts = tract_totals()
    record = {}
    failures = []
    for c3 in sorted(CENSUS_COUNTIES):
        nm = CENSUS_COUNTIES[c3]
        ds = cur.get(c3) or {}
        if sorted(ds) != list(DISTRICTS):
            failures.append("%s: the Census draws districts %s" % (nm, sorted(ds)))
            continue
        bad_func = [d for d, f in ds.items() if (f["properties"].get("FUNCSTAT") or "") != "N"]
        if bad_func:
            failures.append("%s: districts %s are not nonfunctioning subdivisions — a "
                            "functioning one is a town or township, not a supervisor "
                            "district" % (nm, bad_func))
        blocks = fetch_blocks(c3)
        m = measure_county(c3, ds, old.get(c3), blocks)
        if m["people"] != tracts.get(c3):
            failures.append("%s: blocks sum to %d, tracts to %s"
                            % (nm, m["people"], tracts.get(c3)))
        if m["people_in_no_district"] or m["people_in_two_districts"]:
            failures.append("%s: %d people in no district and %d in two"
                            % (nm, m["people_in_no_district"], m["people_in_two_districts"]))
        if m["deviation_pct"] > MAX_DEVIATION_PCT:
            failures.append("%s: the five districts differ by %.2f%% of an equal share on "
                            "2020 population (ceiling %.0f%%) — not lines drawn on the "
                            "2020 census" % (nm, m["deviation_pct"], MAX_DEVIATION_PCT))
        if m["people_moved_from_2020_edition"] < MIN_PEOPLE_MOVED:
            failures.append("%s: the 2026 lines move %d people from the 2020 edition's — "
                            "no evidence the county sent the Census new lines"
                            % (nm, m["people_moved_from_2020_edition"]))
        m["blocks"] = blocks
        record[c3] = m
        print("%-10s %7d people  %5.2f%% now, %6.2f%% on the 2020 edition's lines, "
              "%6d people's district number moved"
              % (nm, m["people"], m["deviation_pct"], m["deviation_2020_edition_pct"],
                 m["people_moved_from_2020_edition"]), file=sys.stderr)
    if failures:
        raise SystemExit("FAIL:\n  " + "\n  ".join(failures))

    src_feats = []
    for c3 in sorted(CENSUS_COUNTIES):
        geoid = STATE + c3
        for d in DISTRICTS:
            f = cur[c3][d]
            src_feats.append({"type": "Feature",
                              "properties": {"countyfips": geoid, "county": names[geoid],
                                             "district": d,
                                             "label": roster[geoid]["label"],
                                             "lines": "census",
                                             "key": geoid + "-" + d},
                              "geometry": f["geometry"]})
    with tempfile.TemporaryDirectory() as tmp:
        sp = os.path.join(tmp, "src.geojson")
        with open(sp, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": src_feats}, fh)
        op = os.path.join(tmp, "out.geojson")
        blb.run_mapshaper(sp, SIMPLIFY, op)
        with open(op) as fh:
            simplified = json.load(fh)
    out_feats = simplified["features"]

    problems = structure_problems(out_feats, names, drawn)
    if problems:
        raise SystemExit("FAIL (structure after simplifying):\n  " + "\n  ".join(problems))

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
    print("supervisor-districts: %d/%d points agree, 0 in two districts; median source step "
          "%.2f m, worst stray %.1f m against a %.0f m ceiling"
          % (agree, n, step, worst, blb.FIDELITY_CEILING_M), file=sys.stderr)

    # What simplification costs in people: each block's district under the
    # drawn lines against the full-precision lines.
    by_county_out = {}
    for f in out_feats:
        p = f["properties"]
        by_county_out.setdefault(p["countyfips"][2:], {})[str(p["district"])] = f
    for c3, m in sorted(record.items()):
        _, _, _, drawn_answers = assign(m["blocks"], by_county_out[c3])
        _, _, _, true_answers = assign(m["blocks"], cur[c3])
        shifted = sum(n for (x, y, n), a, b in zip(m["blocks"], drawn_answers, true_answers)
                      if a != b)
        m["simplification_people_moved"] = shifted
        if shifted > 0.01 * m["people"]:
            raise SystemExit("FAIL: simplifying moves %d of %s County's %d people across a "
                             "line" % (shifted, CENSUS_COUNTIES[c3], m["people"]))
        del m["blocks"]

    for f in out_feats:
        f["properties"].pop("key", None)
    inside, agreed, edge, bad = county_witness(out_feats, counties_fc, drawn)
    if bad:
        raise SystemExit("FAIL: the County layer and this one disagree about the county at "
                         "%d point(s) away from any county line, e.g. %s" % (len(bad), bad[:3]))
    print("supervisor-districts: county witness %d/%d points agree (%d inside the drawn "
          "counties); %d differ within %.0f m of a county line"
          % (agreed, WITNESS_SAMPLES, inside, edge, EDGE_M), file=sys.stderr)

    fc = {"type": "FeatureCollection", "features": sorted(
        out_feats, key=lambda f: (f["properties"]["countyfips"], f["properties"]["district"]))}
    compact = json.dumps(fc, separators=(",", ":"))
    if json.loads(compact) != fc:
        raise SystemExit("FAIL: round-trip mismatch before writing")
    with open(OUT, "w") as fh:
        fh.write(compact)
    rec = {
        "_about": ("GENERATED by ms/scripts/build_ms_supervisor_districts.py. What each drawn "
                   "county's lines were measured against when the shipped file was built: "
                   "the Census's own 2020 blocks, its 2020 edition of the same county "
                   "subdivisions, and its block total against its tract total. --check "
                   "holds the shipped file to this record."),
        "built": datetime.date.today().isoformat(),
        "source": CURRENT,
        "vintage": CURRENT_VINTAGE,
        "edition_2020": EDITION_2020,
        "max_deviation_pct": MAX_DEVIATION_PCT,
        "counties": {STATE + c3: dict(county=names[STATE + c3], lines="census", **m)
                     for c3, m in sorted(record.items())},
    }
    os.makedirs(SOURCE_DIR, exist_ok=True)
    with open(RECORD, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("supervisor-districts -> %s: %d districts in %d counties, %d bytes (dp %s)"
          % (os.path.relpath(OUT, INSTANCE), len(fc["features"]), len(drawn), len(compact),
             SIMPLIFY), file=sys.stderr)


# --------------------------------------------------------------- --check ----
def check():
    names, counties_fc = county_names()
    with open(ROSTER_FILE) as fh:
        roster = json.load(fh)
    with open(OUT) as fh:
        fc = json.load(fh)
    with open(RECORD) as fh:
        rec = json.load(fh)
    drawn = {STATE + c for c in CENSUS_COUNTIES}
    problems = structure_problems(fc.get("features") or [], names, drawn)
    problems += roster_problems(roster, drawn)
    for f in fc.get("features") or []:
        p = f.get("properties") or {}
        word = (roster.get(p.get("countyfips")) or {}).get("label")
        if p.get("label") != word:
            problems.append("%s district %s is labelled %r and the directory says %r"
                            % (p.get("countyfips"), p.get("district"), p.get("label"), word))
    recorded = rec.get("counties") or {}
    if set(recorded) != drawn:
        problems.append("the record names counties %s, CENSUS_COUNTIES %s"
                        % (sorted(recorded), sorted(drawn)))
    for geoid, m in sorted(recorded.items()):
        if m.get("deviation_pct") is None or m["deviation_pct"] > MAX_DEVIATION_PCT:
            problems.append("%s: recorded deviation %r" % (geoid, m.get("deviation_pct")))
        if (m.get("people_moved_from_2020_edition") or 0) < MIN_PEOPLE_MOVED:
            problems.append("%s: recorded %r people moved from the 2020 edition"
                            % (geoid, m.get("people_moved_from_2020_edition")))
        if sum((m.get("district_people") or {}).values()) != m.get("people"):
            problems.append("%s: district totals do not sum to the county's people" % geoid)
    # The card names the edition in words ("January 1, 2026 edition"), so a
    # rebuild from a new vintage that left the card alone would tell a reader
    # the wrong edition. Both are held to the record here.
    if rec.get("vintage") != CURRENT_VINTAGE:
        problems.append("the record was built from the %r layer and CURRENT_VINTAGE is %r"
                        % (rec.get("vintage"), CURRENT_VINTAGE))
    with open(os.path.join(INSTANCE, "index.html"), encoding="utf-8") as fh:
        if "(%s edition)" % rec.get("vintage") not in fh.read():
            problems.append("ms/index.html's supervisor card does not name the %s edition "
                            "the shipped file was built from" % rec.get("vintage"))
    inside, agreed, edge, bad = county_witness(fc.get("features") or [], counties_fc, drawn)
    if bad:
        problems.append("the County layer and this one disagree about the county at %d "
                         "point(s) away from any county line, e.g. %s" % (len(bad), bad[:3]))
    if problems:
        print("FAIL: ms-supervisor-districts.json\n  " + "\n  ".join(problems))
        return 1
    devs = sorted(m["deviation_pct"] for m in recorded.values())
    print("OK: ms-supervisor-districts.json draws %d districts in %d counties, each "
          "numbered 1-5 and named in the directory; recorded deviations %.2f%%-%.2f%% on "
          "2020 population (ceiling %.0f%%, measured at build, not re-measured here); "
          "county witness %d/%d agree, %d differ within %.0f m of a county line"
          % (len(fc["features"]), len(drawn), devs[0], devs[-1], MAX_DEVIATION_PCT,
             agreed, WITNESS_SAMPLES, edge, EDGE_M))
    return 0


# -------------------------------------------------------------- --survey ----
def survey():
    """Every county's two measurements, printed; writes nothing."""
    names, _ = county_names()
    allc = sorted(g[2:] for g in names)
    cur = fetch_cousubs(CURRENT, allc)
    old = fetch_cousubs(EDITION_2020, allc)
    rows = []
    for c3 in allc:
        if sorted(cur.get(c3) or {}) != list(DISTRICTS):
            rows.append((c3, "the Census draws %s" % sorted(cur.get(c3) or {})))
            continue
        m = measure_county(c3, cur[c3], old.get(c3), fetch_blocks(c3))
        current = (m["deviation_pct"] <= MAX_DEVIATION_PCT
                   and m["people_moved_from_2020_edition"] >= MIN_PEOPLE_MOVED)
        verdict = ("CURRENT" if current else
                   "unchanged, balanced" if m["deviation_pct"] <= MAX_DEVIATION_PCT else
                   "changed, unbalanced" if m["people_moved_from_2020_edition"] >= MIN_PEOPLE_MOVED
                   else "stale")
        listed = "listed" if c3 in CENSUS_COUNTIES else ("NOT LISTED" if current else "")
        rows.append((c3, "%-22s %6.2f%% now  %6.2f%% 2020 edition  %6d moved  %-20s %s"
                     % (names[STATE + c3], m["deviation_pct"], m["deviation_2020_edition_pct"],
                        m["people_moved_from_2020_edition"], verdict, listed)))
    for c3, line in rows:
        print(c3, line)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    ap.add_argument("--survey", action="store_true", help="measure all 82 counties, write nothing")
    args = ap.parse_args()
    if args.check:
        return check()
    if args.survey:
        return survey()
    build(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
