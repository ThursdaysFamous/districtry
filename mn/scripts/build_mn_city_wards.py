#!/usr/bin/env python3
"""
Build data/app/mn-city-wards.json — the council wards and districts of the
Minnesota cities whose councils this app names and which elect members by ward
or district, dissolved out of the Secretary of State's own precinct fabric.

WHICH CITIES IS READ, NOT LISTED. data/app/mn-city-councils.json names the
councils of the 43 cities above 25,000 people, one record per seat, and a seat
called "Ward N" or "District N" is elected by part of the city. Every city whose
roster carries such a seat is drawn here, and no other: measured 2026-10-15
that is 22 cities and 101 wards. A city added to the roster with ward seats is
drawn on the next run with nothing to edit.

THE PRECINCT FABRIC CARRIES THE WARD. The Secretary of State's statewide
precinct layer (mn_vtd_dissolve.PRECINCT_LAYER, 4,105 precincts) gives every
precinct its city (`mcdfips`) and, where the city has wards, its `ward` ("W-01",
"W-C"). A Minnesota precinct lies wholly inside one ward, so each ward is a
union of whole precincts and dissolving them reproduces the city's own plan.
The fabric carries wards for 69 cities; the 47 whose councils this app does not
name are not drawn, because a ward the card cannot name a member for, in a city
whose council the app does not describe, is a polygon answering a question
nobody on the card can finish. They are the next step and are printed.

THE ROSTER AND THE FABRIC MUST AGREE ABOUT EVERY CITY'S WARDS, EXACTLY. For each
city the set of ward seats in the roster ("Ward 1".."Ward 4", "Ward C/E/W",
"District 1".."District 6") must equal the set of wards the fabric gives its
precincts, and the build fails on any difference. Measured 2026-10-15: 22 of 22
agree.

THE SECOND WITNESS IS THE BALLOT. The Secretary of State's per-precinct local
results (`localPrct.txt` on electionresultsfiles.sos.mn.gov, one file per
election day) list every precinct that voted in each council contest, so a
"Council Member Ward 3 (Mankato)" contest was on the ballot in exactly the
precincts of Mankato's Ward 3. For each ward, the latest regular contest's
precincts are compared with the precincts the fabric of THE SAME VINTAGE puts in
that ward: an even-year general is read against that general's own precinct
layer (`bdry_electionresults_2022_2030`), because precincts are renumbered
between elections and a code from 2022 looked up in today's fabric can land
somewhere else; an odd-year contest is read against today's fabric. That is the
school-board-district builder's method turned round: there the ballot draws a
map nobody publishes, here it checks one the Secretary of State does. Any
precinct in one set and not the other fails the build, and a ward with no
contest since the 2022 general is printed rather than failed.

WHAT THIS DOES NOT CLAIM. A ward the fabric and the ballot agree about can still
have been redrawn since that ballot if the fabric has not caught up; the
witness proves the two agreed at the latest contest, and the fabric is the
Secretary of State's own working copy for the next one. Population balance
(Minn. Stat. 204B.135 subd. 1) is not measured, because the fabric publishes no
population.

Simplification is Douglas-Peucker in one shared topology, as the commissioner
builder does, for the reason its own docstring records: two wards simplified on
their own come out with different copies of the line between them.

Run:  python3 mn/scripts/build_mn_city_wards.py
      python3 mn/scripts/build_mn_city_wards.py --check    (offline, on what ships)
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, FLEET_SCRIPTS)

import mn_vtd_dissolve as vtd  # noqa: E402
from scraper_common import require_robots_once  # noqa: E402

ROSTER_FILE = os.path.join(INSTANCE, "data", "app", "mn-city-councils.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-city-wards.json")

FILES_HOST = "https://electionresultsfiles.sos.mn.gov"
PRECINCT_RESULTS = FILES_HOST + "/%s/localPrct.txt"
RESULTS_SERVICE = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
                   "us_mn_state_sos/bdry_electionresults_2022_2030/FeatureServer")
FIRST_YEAR = 2022
CANVASS_DAYS = 21
PACE_SECONDS = 0.5

MAPSHAPER = "mapshaper@0.6.102"
# 15 m, the commissioner layer's interval and for its reason: about one step
# of a precinct line along a street grid.
SIMPLIFY_INTERVAL_M = 15

# Measured 2026-10-15. Floors fail a parse that loses a city or a ward; the
# set may grow as the roster does.
MIN_CITIES = 22
MIN_WARDS = 101

SEAT_RE = re.compile(r"^(Ward|District) (\w+)$")
OFFICE_RE = re.compile(
    r"^(?P<special>Special Election for )?Council Member (?:Ward|District) "
    r"(?P<label>\w+)(?: (?:First|Second|Third) Choice)? \([^)]*\)", re.I)


def fail(msg):
    raise SystemExit("build-mn-city-wards: FATAL: %s" % msg)


def ward_label(raw):
    """"W-01" -> "1", "W-C" -> "C", "W-1" -> "1"."""
    m = re.match(r"^W-0*(\w+)$", (raw or "").strip())
    return m.group(1).upper() if m else None


def roster_cities():
    """{place geoid: (city name, word, {label})} for every city whose roster
    carries a seat elected by ward or district."""
    with open(ROSTER_FILE, encoding="utf-8") as fh:
        roster = json.load(fh)
    out = {}
    for geoid, city in sorted(roster.items()):
        labels, words = set(), set()
        for seat in city.get("seats") or []:
            m = SEAT_RE.match(seat.get("seat") or "")
            if m:
                words.add(m.group(1))
                labels.add(m.group(2).upper())
        if labels:
            if len(words) != 1:
                fail("%s names its seats both Ward and District: %s"
                     % (city["name"], sorted(words)))
            out[geoid] = (city["name"], words.pop(), labels)
    return out


def general_dates(today):
    out = []
    for year in range(FIRST_YEAR, today.year + 1):
        nov1 = datetime.date(year, 11, 1)
        monday = nov1 + datetime.timedelta(days=(0 - nov1.weekday()) % 7)
        day = monday + datetime.timedelta(days=1)
        if today >= day + datetime.timedelta(days=CANVASS_DAYS):
            out.append(day)
    return out


def get_json(session, url, params):
    resp = session.get(url, params=params, headers={"User-Agent": vtd.USER_AGENT},
                       timeout=vtd.REQUEST_TIMEOUT)
    if resp.status_code != 200:
        fail("%s answered HTTP %d" % (url, resp.status_code))
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        fail("%s answered an error: %r" % (url, data["error"]))
    return data


def vtdid(county_code, pct):
    return "27%03d%s" % (2 * int(county_code) - 1, pct)


def ballot_contests(session, days, wanted):
    """{(geoid, label): [{date, office, special, precincts}]} for every council
    ward or district contest in the wanted cities."""
    codes = {g[2:]: g for g in wanted}
    found = {}
    for day in days:
        url = PRECINCT_RESULTS % day.strftime("%Y%m%d")
        require_robots_once(url, vtd.USER_AGENT)
        resp = session.get(url, headers={"User-Agent": vtd.USER_AGENT},
                           timeout=vtd.REQUEST_TIMEOUT)
        time.sleep(PACE_SECONDS)
        if resp.status_code == 404:
            continue
        if resp.status_code != 200:
            fail("%s answered HTTP %d" % (url, resp.status_code))
        for line in resp.content.decode("latin-1").splitlines():
            f = line.split(";")
            if len(f) < 8:
                continue
            geoid = codes.get(f[5].strip())
            if geoid is None or "Council Member" not in f[4]:
                continue
            m = OFFICE_RE.match(f[4].strip())
            if not m:
                continue
            key = (geoid, m.group("label").upper())
            office = f[4].strip()
            contests = found.setdefault(key, [])
            contest = next((c for c in contests
                            if c["date"] == day and c["office"] == office), None)
            if contest is None:
                contest = {"date": day, "office": office,
                           "special": bool(m.group("special")), "precincts": set()}
                contests.append(contest)
            contest["precincts"].add(vtdid(f[1], f[2].strip()))
    return found


def results_layers(session):
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


def vintage_wards(session, layer_id, wanted):
    """{vtdid: (geoid, label)} from one general's own precinct layer."""
    url = "%s/%d/query" % (RESULTS_SERVICE, layer_id)
    require_robots_once(url, vtd.USER_AGENT)
    codes = {g[2:]: g for g in wanted}
    out, offset = {}, 0
    while True:
        body = get_json(session, url, {
            "where": "1=1", "outFields": "vtdid,mcdfips,ward",
            "returnGeometry": "false", "orderByFields": "objectid",
            "resultOffset": str(offset), "resultRecordCount": str(vtd.PAGE_SIZE),
            "f": "json"})
        page = [r.get("attributes") or {} for r in body.get("features") or []]
        for r in page:
            geoid = codes.get((r.get("mcdfips") or "").strip())
            label = ward_label(r.get("ward"))
            if geoid and label:
                out[r["vtdid"]] = (geoid, label)
        if len(page) < vtd.PAGE_SIZE:
            break
        offset += vtd.PAGE_SIZE
        time.sleep(PACE_SECONDS)
    return out


def simplify_shared(collection):
    if not shutil.which("npx"):
        fail("npx is not on PATH; this builder simplifies through mapshaper so "
             "neighbouring wards keep one shared border")
    work = tempfile.mkdtemp(prefix="mn-wards-")
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
            fail("mapshaper failed (%d): %s"
                 % (proc.returncode, (proc.stderr or "")[-800:]))
        with open(dst) as handle:
            out = json.load(handle)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if len(out.get("features") or []) != len(collection["features"]):
        fail("mapshaper returned %d features for %d"
             % (len(out.get("features") or []), len(collection["features"])))
    return out


def interior_points(geom, wanted):
    polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
             else [geom["coordinates"]])
    xs = [pt[0] for poly in polys for pt in poly[0]]
    ys = [pt[1] for poly in polys for pt in poly[0]]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    found, step = [], 1
    while len(found) < wanted and step <= 7:
        n = 8 * step
        found = []
        for i in range(1, n):
            for j in range(1, n):
                lng = lo_x + (hi_x - lo_x) * i / float(n)
                lat = lo_y + (hi_y - lo_y) * j / float(n)
                if vtd.point_in_geom(lng, lat, geom):
                    found.append((lng, lat))
                    if len(found) >= wanted:
                        return found
        step += 1
    return found


SAMPLE_POINTS = 2000
MIN_AGREEMENT = 0.995


def agreement(exact, simple):
    """2,000 seeded points over the cities' extents must get the same ward from
    the simplified file as from the exact dissolve, the fleet's agreement gate."""
    import random  # noqa: PLC0415
    rng = random.Random(27)
    def bbox(g):
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        xs = [p[0] for poly in polys for p in poly[0]]
        ys = [p[1] for poly in polys for p in poly[0]]
        return min(xs), min(ys), max(xs), max(ys)
    def answer(fc, lng, lat):
        return tuple(sorted((f["properties"]["geoid"], f["properties"]["ward"])
                            for f in fc["features"]
                            if vtd.point_in_geom(lng, lat, f["geometry"])))
    boxes = [bbox(f["geometry"]) for f in exact["features"]]
    same = 0
    for i in range(SAMPLE_POINTS):
        x0, y0, x1, y1 = boxes[i % len(boxes)]
        lng, lat = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if answer(exact, lng, lat) == answer(simple, lng, lat):
            same += 1
    if same < MIN_AGREEMENT * SAMPLE_POINTS:
        fail("the simplified wards agree with the exact dissolve at %d of %d points, "
             "below %.1f%%" % (same, SAMPLE_POINTS, 100 * MIN_AGREEMENT))
    print("agreement: %d of %d seeded points get the same ward from the simplified "
          "file as from the exact dissolve" % (same, SAMPLE_POINTS), file=sys.stderr)


def check(out, wanted):
    """The offline half, on what ships: the roster and the file agree about
    every city's wards, and no two wards overlap."""
    feats = out.get("features") or []
    have = {}
    for feat in feats:
        p = feat.get("properties") or {}
        have.setdefault(p.get("geoid"), set()).add(p.get("ward"))
    if set(have) != set(wanted):
        fail("the file draws %s and the roster has ward seats in %s"
             % (sorted(set(have) - set(wanted)) or "no extra city",
                sorted(set(wanted) - set(have)) or "no missing city"))
    for geoid, (name, _word, labels) in sorted(wanted.items()):
        if have[geoid] != labels:
            fail("%s: the roster's ward seats are %s and the file draws %s"
                 % (name, sorted(labels), sorted(have[geoid])))
    if len(have) < MIN_CITIES or len(feats) < MIN_WARDS:
        fail("%d cities and %d wards, below the floors %d and %d"
             % (len(have), len(feats), MIN_CITIES, MIN_WARDS))
    for feat in feats:
        p = feat["properties"]
        pts = interior_points(feat["geometry"], 10)
        if len(pts) < 4:
            fail("could not seed interior points in %s %s" % (p["city"], p["seat"]))
        for lng, lat in pts:
            hits = [(q["properties"]["city"], q["properties"]["seat"]) for q in feats
                    if vtd.point_in_geom(lng, lat, q["geometry"])]
            if len(hits) != 1:
                fail("%.5f,%.5f inside %s %s is in %d wards: %s"
                     % (lng, lat, p["city"], p["seat"], len(hits), hits))
    print("check: %d wards in %d cities, each city's wards exactly its roster's ward "
          "seats, no point inside one ward inside a second" % (len(feats), len(have)),
          file=sys.stderr)


def build():
    import requests  # noqa: PLC0415
    wanted = roster_cities()
    vtd.require_robots([vtd.PRECINCT_QUERY, RESULTS_SERVICE,
                        PRECINCT_RESULTS % "20241105"], FLEET_SCRIPTS)
    session = requests.Session()

    features = vtd.fetch_precincts(
        ["vtdid", "countyname", "mcdname", "mcdfips", "ward", "pctname"],
        geometry=True)
    codes = {g[2:]: g for g in wanted}
    groups, today_key, fabric_cities = {}, {}, {}
    for feature in features:
        p = feature.get("properties") or {}
        label = ward_label(p.get("ward"))
        if (p.get("ward") or "").strip() and not label:
            fail("a precinct carries a ward this builder does not read: %r" % p)
        if not label:
            continue
        fabric_cities.setdefault((p.get("mcdfips") or "").strip(),
                                 (p.get("mcdname") or "").strip())
        geoid = codes.get((p.get("mcdfips") or "").strip())
        if geoid is None:
            continue
        groups.setdefault((geoid, label), []).append(feature)
        today_key[p["vtdid"]] = (geoid, label)

    # Gate 1 — the roster and the fabric agree about every city's wards.
    for geoid, (name, _word, labels) in sorted(wanted.items()):
        fabric = {lab for (g, lab) in groups if g == geoid}
        if fabric != labels:
            fail("%s: the roster has seats for wards %s and the Secretary of State's "
                 "precincts carry wards %s" % (name, sorted(labels), sorted(fabric)))
    others = sorted(n for c, n in fabric_cities.items() if c not in codes)
    print("roster: %d cities elect by ward or district, and the precinct fabric "
          "carries exactly their wards (%d); it also carries wards for %d cities "
          "whose councils this app does not name, not drawn: %s"
          % (len(wanted), len(groups), len(others), ", ".join(others)),
          file=sys.stderr)

    # Gate 2 — the ballot.
    today = datetime.date.today()
    days = general_dates(today)
    contests = ballot_contests(session, days, wanted)
    layers = results_layers(session)
    vintages = {}
    agreed, unwitnessed, latest, on_today = 0, [], {}, 0
    for key in sorted(groups):
        geoid, label = key
        pool = [c for c in contests.get(key, []) if not c["special"]] \
            or contests.get(key, [])
        if not pool:
            unwitnessed.append("%s %s" % (wanted[geoid][0], label))
            continue
        c = max(pool, key=lambda x: x["date"])
        # An even-year general is read against its own precinct layer. An
        # odd-year contest has no layer of its own: precincts it was held on
        # are the previous general's or today's, depending on whether a city
        # re-precincted in between (Bloomington merged W-4 P-31 into P-30
        # after the 2024 general, so its 2023 contest matches 2022's map and
        # not today's), so it must agree EXACTLY with one of the two.
        years = [c["date"].year] if c["date"].year % 2 == 0 \
            else [c["date"].year - 1, None]
        tables = []
        for year in years:
            if year is None:
                tables.append(("today's", today_key))
                continue
            if year not in vintages:
                if year not in layers:
                    fail("no precinct layer for the %d general" % year)
                vintages[year] = vintage_wards(session, layers[year], wanted)
            tables.append(("the %d general's" % year, vintages[year]))
        match = None
        for name, table in tables:
            ours = {v for v, k in table.items() if k == key}
            if ours == c["precincts"]:
                match = name
                break
        if match is None:
            name, table = tables[0]
            ours = {v for v, k in table.items() if k == key}
            fail("%s %s: the %s contest %r was on the ballot in %d precincts and "
                 "%s precinct map puts %d in this ward. Only on the ballot: %s. "
                 "Only on the map: %s"
                 % (wanted[geoid][0], label, c["date"], c["office"],
                    len(c["precincts"]), name, len(ours),
                    sorted(c["precincts"] - ours)[:8],
                    sorted(ours - c["precincts"])[:8]))
        if match == "today's" and c["date"].year % 2:
            on_today += 1
        agreed += 1
        latest[key] = c
    print("ballot: %d of %d wards voted in exactly the precincts the same vintage's "
          "precinct map puts in them, at their latest regular contest since %d (%d "
          "odd-year contests on today's map, the rest on a general's own); %d "
          "had no contest to compare (%s)"
          % (agreed, len(groups), FIRST_YEAR, on_today, len(unwitnessed),
             ", ".join(unwitnessed) or "none"), file=sys.stderr)

    exact = {"type": "FeatureCollection", "features": []}
    for geoid, label in sorted(groups):
        polys = vtd.group_rings(vtd.dissolve(groups[(geoid, label)]))
        exact["features"].append({
            "type": "Feature",
            "properties": {"geoid": geoid, "ward": label},
            "geometry": ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                         else {"type": "MultiPolygon", "coordinates": polys}),
        })
    simple = simplify_shared(exact)
    agreement(exact, simple)
    out = {"type": "FeatureCollection", "features": []}
    for feature in simple["features"]:
        p = feature["properties"]
        key = (p["geoid"], p["ward"])
        name, word, _labels = wanted[p["geoid"]]
        c = latest.get(key)
        props = {"geoid": p["geoid"], "city": name, "ward": p["ward"],
                 "seat": "%s %s" % (word, p["ward"]),
                 "precincts": len(groups[key])}
        if c:
            props["ballot"] = c["date"].isoformat()
        out["features"].append({"type": "Feature", "properties": props,
                                "geometry": feature["geometry"]})
    out["features"].sort(key=lambda f: (f["properties"]["city"],
                                        f["properties"]["ward"].zfill(3)))
    check(out, wanted)
    with open(OUT_FILE, "w") as handle:
        json.dump(out, handle, separators=(",", ":"))
        handle.write("\n")
    print("mn-city-wards -> %s: %d wards in %d cities, %d bytes (shared topology, dp "
          "interval %d m, 6dp)" % (os.path.relpath(OUT_FILE, INSTANCE),
                                   len(out["features"]), len(wanted),
                                   os.path.getsize(OUT_FILE), SIMPLIFY_INTERVAL_M),
          file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to the roster")
    args = ap.parse_args()
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as fh:
            check(json.load(fh), roster_cities())
        return
    build()


if __name__ == "__main__":
    main()
