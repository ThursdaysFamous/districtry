#!/usr/bin/env python3
"""
Build data/app/<city>-wards.json for nine Iowa cities that elect council
members by ward, drawn by the `city-ward` layer in ia/index.html beside Des
Moines, Waterloo and Cedar Rapids (which keep their own builders).

ONE BUILDER FOR NINE CITIES, BECAUSE THE NINE DIFFER ONLY IN WHERE THEIR
LINES ARE PUBLISHED. Each row of CITIES names the layer, the field carrying
the ward number, how to read it, and whether the layer holds wards or the
precincts a ward is made of. Everything else -- the tiling gate, the
simplification, the agreement gate -- is the same question asked nine times,
and nine copies of it would be nine places for it to drift.

The PEOPLE are not built here. Every city in this table except Mason City
already has its council in ia/data/app/ia-city-councils.json, each member's
seat written "Ward N" or "At-Large" off the city's own page, and the card
reads that file. A boundary layer that carries member names (Mason City's,
West Des Moines's and Dubuque's do, Cedar Falls's carries names that are no
longer on the council) is NOT read for people: a roster attached to a
boundary is refreshed when the boundary is, which is the Coles County
reading. Dubuque's layer also carries an `Address` field holding what look
like members' home addresses; only the ward field is requested from it, so
those never reach this machine, let alone a file.

WHERE EACH CITY'S LINES COME FROM (all read 2026-10-15)
--------------------------------------------------------
  Ames             Story County AdminElection layer 3, `Ward` '1'..'4'.
                   The city's own "Ames_Precincts_2020" service is a 24-district
                   DRAFT plan under another name and is not used.
  Bettendorf       the city's Bettendorf_Wards (as of 2025) layer, `DISTRICT`.
  Cedar Falls      the city's Admin layer 1, `Ward`.
  Davenport        the city's Admin_Public layer 6, `Ward` '1'..'8'.
  Dubuque          the city's CityCouncil/Wards layer 7, `Ward` 1..4 (0 is the
                   mayor and at-large rows, excluded by the query).
  Marion           LINN COUNTY's ElectionsCityCouncilDistrict, POLITICAL_TWP
                   '21'. That code is proved to be Marion's by
                   build_cedar_rapids_wards.py's cross-control, and it is proved
                   again here by the identity gate below. The city's own
                   Council_Wards layer was last edited 2020-03-20, before the
                   2021 redistricting, and is not used.
  Marshalltown     the city's Wards_and_Precincts_2022 layer, which holds the
                   EIGHT PRECINCTS ("1-1" .. "4-2"); the ward is the number
                   before the hyphen, and the four wards are dissolved from them.
  Mason City       the city's Wards layer, `Ward` "Ward 1".."Ward 4".
  West Des Moines  the city's CouncilPrecinctsExt layer 4: 31 precincts with a
                   `WARD` field, dissolved to three wards.

Iowa City is NOT here: its three district seats are nominated by district and
elected by the whole city, which build_eam_status.py records as at large.

THE GATES, ASKED OF EVERY CITY
-------------------------------
1. The ward numbers are exactly the ones the city elects from.
2. IDENTITY AND TILING against the Census Bureau's incorporated place
   (TIGERweb, by GEOID, not by name). The wards' total area over the place's
   must sit near 1, which is what tells Marion's code from Cedar Rapids', and
   erasing the wards from the place must leave only seam: no COMPACT leftover
   part, since one compact part is ground in the city where the card would
   answer nothing. This compares two publishers, and the Census place trails
   an annexation by up to a year, so the ceilings are per city and were MEASURED
   on the run that wrote them (see CITIES); a city that has grown past them
   fails rather than shipping a hole.
3. Simplification (Douglas-Peucker, which bounds how far the drawn line can
   stray; Visvalingam does not, see CLAUDE.md on the IL chambers) must agree
   with the source at 99.5% of 4,000 points over the wards' own envelope, and
   must add no overlap the source does not have.

Usage:
    python3 ia/scripts/build_ia_city_wards.py              # all nine
    python3 ia/scripts/build_ia_city_wards.py ames dubuque # some
    python3 ia/scripts/build_ia_city_wards.py --check      # never writes
"""

import datetime
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED -- validate_workflow_deps)
    UA_HEADERS_ROSTER_BOT,
    UA_ROSTER_BOT,
    require_robots_once,
)

REPO_ROOT = os.path.dirname(_HERE)  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.102"
SIMPLIFY = ["dp", "interval=3", "keep-shapes"]
PRECISION = "0.000001"

TIGERWEB_PLACE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "Places_CouSub_ConCity_SubMCD/MapServer/4")

SOURCE_OVERLAP_CEILING = 0.02
COMPACTNESS_CEILING = 0.30
COMPACTNESS_MIN_AREA_M2 = 2000.0
IDENTITY_RATIO_LO = 0.90
IDENTITY_RATIO_HI = 1.15


def _ward_int(v):
    return int(str(v).strip())


def _ward_word(v):
    # "Ward 3" -> 3
    s = str(v).strip()
    if not s.lower().startswith("ward "):
        raise ValueError("expected 'Ward N', got %r" % s)
    return int(s[5:])


def _ward_before_hyphen(v):
    # Marshalltown's precinct "2-1" -> ward 2
    return int(str(v).split("-")[0])


# Each row: slug, geoid, city, layer url, where clause, the field carrying the
# ward, how to read it, whether the layer holds precincts to dissolve, the
# wards the city elects from, the city's own page for the boundary, and the
# two tiling ceilings (uncovered sq mi, largest uncovered part m2), each set
# at roughly 2.5 times what was measured on 2026-10-15: room for seam drift,
# and far below what a missing neighbourhood would leave. The measured values
# print on every run.
CITIES = [
    dict(slug="ames", geoid="1901855", city="Ames",
         layer="https://apps.storycounty.com/arcgis/rest/services/AdminElection/MapServer/3",
         where="1=1", field="Ward", read=_ward_int, dissolve=False,
         wards=[1, 2, 3, 4],
         page="https://www.cityofames.org/My-Government/Mayor-and-City-Council",
         max_sqmi=0.15, max_part_m2=150000,
         # Measured 2026-10-15: a 2,764 m2 block (Polsby-Popper 0.42) the
         # Census place puts inside Ames and the county's ward layer leaves
         # out, about 40 m from ward 2. The county's precinct layer puts the
         # point in "Ames 8", but nearby precincts such as "Ames 3/Grant Twp"
         # show a precinct can hold township ground too, so which publisher is
         # right about this block is NOT established. A reader standing there
         # is shown no ward card rather than a guessed one.
         accepted_holes=[dict(lat=42.05693, lng=-93.61466, max_m2=4000.0,
                              why="Census place includes it, ward layer does not")]),
    dict(slug="bettendorf", geoid="1906355", city="Bettendorf",
         layer="https://services5.arcgis.com/5hE5PoX87LzkB5tp/arcgis/rest/services/"
               "Bettendorf_Wards__as_of_2025/FeatureServer/0",
         where="1=1", field="DISTRICT", read=_ward_int, dissolve=False,
         wards=[1, 2, 3, 4, 5],
         page="https://www.bettendorf.org/government/mayor___council/index.php",
         max_sqmi=0.05, max_part_m2=60000),
    dict(slug="cedar-falls", geoid="1911755", city="Cedar Falls",
         layer="https://gis.cedarfalls.com/arcgis/rest/services/Admin/MapServer/1",
         where="1=1", field="Ward", read=_ward_int, dissolve=False,
         wards=[1, 2, 3, 4, 5],
         page="https://www.cedarfalls.com/1106/City-Council-Members",
         max_sqmi=0.10, max_part_m2=150000),
    dict(slug="davenport", geoid="1919000", city="Davenport",
         layer="https://gis.davenportiowa.com/arcgis/rest/services/Admin_Public/MapServer/6",
         where="1=1", field="Ward", read=_ward_int, dissolve=False,
         wards=[1, 2, 3, 4, 5, 6, 7, 8],
         page="https://www.davenportiowa.com/cms/One.aspx?portalId=6481456&pageId=7274102",
         max_sqmi=0.06, max_part_m2=70000),
    dict(slug="dubuque", geoid="1922395", city="Dubuque",
         layer="https://maps.cityofdubuque.org/arcgisweb2/rest/services/CityCouncil/Wards/MapServer/7",
         where="Ward>0", field="Ward", read=_ward_int, dissolve=False,
         wards=[1, 2, 3, 4],
         page="https://www.cityofdubuque.org/990/Mayor-City-Council",
         max_sqmi=0.10, max_part_m2=60000),
    dict(slug="marion", geoid="1949485", city="Marion",
         layer="https://services.arcgis.com/i14SLLmXo7Hn9vNc/ArcGIS/rest/services/"
               "ElectionsCityCouncilDistrict/FeatureServer/0",
         where="POLITICAL_TWP='21'", field="CITYCOUNCIL", read=_ward_int, dissolve=False,
         wards=[1, 2, 3, 4],
         page="https://www.linncountyiowa.gov/1350/Cedar-Rapids-Council-Districts-Marion-Wa",
         max_sqmi=0.10, max_part_m2=150000),
    dict(slug="marshalltown", geoid="1949755", city="Marshalltown",
         layer="https://services7.arcgis.com/7WRZWVaTK828hbiZ/arcgis/rest/services/"
               "Marshalltown_Wards_and_Precincts_2022_view/FeatureServer/0",
         where="1=1", field="Precinct", read=_ward_before_hyphen, dissolve=True,
         wards=[1, 2, 3, 4],
         page="https://www.marshalltown-ia.gov/154/Mayor-City-Council",
         max_sqmi=0.07, max_part_m2=50000),
    dict(slug="mason-city", geoid="1950160", city="Mason City",
         layer="https://services1.arcgis.com/84FpxbPitJq31AWu/arcgis/rest/services/"
               "Wards/FeatureServer/0",
         where="1=1", field="Ward", read=_ward_word, dissolve=False,
         wards=[1, 2, 3, 4],
         # The city's home page, linked and never fetched: masoncity.net sits
         # behind a managed challenge, robots.txt included.
         page="https://www.masoncity.net/",
         max_sqmi=0.18, max_part_m2=300000),
    dict(slug="west-des-moines", geoid="1983910", city="West Des Moines",
         layer="https://maps.wdm.iowa.gov/server/rest/services/External/"
               "CouncilPrecinctsExt/MapServer/4",
         where="1=1", field="WARD", read=_ward_int, dissolve=True,
         wards=[1, 2, 3],
         page="https://www.wdm.iowa.gov/government/mayor-city-council/biographies",
         max_sqmi=0.15, max_part_m2=110000),
]


def fetch_json(url):
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="ia-build-city-wards")
    req = urllib.request.Request(url, headers=UA_HEADERS_ROSTER_BOT)
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    if isinstance(data, dict) and "error" in data:
        # an ArcGIS error is an HTTP 200 with an error object, and reading it
        # as an empty answer is how a failure becomes "no features"
        raise RuntimeError("%s answered an error: %s" % (url, data["error"]))
    return data


def query(layer, where, fields):
    q = urllib.parse.urlencode({
        "where": where, "outFields": fields, "returnGeometry": "true",
        "outSR": "4326", "f": "geojson"})
    return fetch_json("%s/query?%s" % (layer, q))


def vintage(layer):
    meta = fetch_json("%s?f=json" % layer)
    ms = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    return (datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
            if ms else "not stated")


# --- geometry -------------------------------------------------------------

def _each_polygon(geom):
    if not geom:
        return []
    if geom["type"] == "MultiPolygon":
        return [rings for rings in geom["coordinates"] if rings]
    if geom["type"] == "Polygon":
        return [geom["coordinates"]] if geom["coordinates"] else []
    return []


def _ring_area_m2(r, lat0):
    mx = 111320.0 * math.cos(math.radians(lat0))
    my = 110540.0
    s = 0.0
    for i in range(len(r) - 1):
        s += (r[i][0] * mx) * (r[i + 1][1] * my) - (r[i + 1][0] * mx) * (r[i][1] * my)
    return abs(s) / 2.0


def _ring_perimeter_m(r, lat0):
    mx = 111320.0 * math.cos(math.radians(lat0))
    my = 110540.0
    return sum(math.hypot((r[i + 1][0] - r[i][0]) * mx, (r[i + 1][1] - r[i][1]) * my)
               for i in range(len(r) - 1))


def _rings_area_m2(rings, lat0):
    return _ring_area_m2(rings[0], lat0) - sum(_ring_area_m2(h, lat0) for h in rings[1:])


def _geom_area_m2(geom, lat0):
    return sum(_rings_area_m2(rings, lat0) for rings in _each_polygon(geom))


def _metres(a, b, lat0):
    return math.hypot((a[0] - b[0]) * 111320.0 * math.cos(math.radians(lat0)),
                      (a[1] - b[1]) * 110540.0)


def _mapshaper(args, tmp):
    subprocess.run(["npx", "-y", MAPSHAPER] + args, check=True, cwd=tmp,
                   capture_output=True)


def _point_in_ring(pt, ring):
    x, y = pt
    inside = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def _point_in_geometry(pt, geom):
    for rings in _each_polygon(geom):
        if _point_in_ring(pt, rings[0]) and not any(_point_in_ring(pt, h) for h in rings[1:]):
            return True
    return False


def _bbox(geom):
    xs = [x for rings in _each_polygon(geom) for x, _ in rings[0]]
    ys = [y for rings in _each_polygon(geom) for _, y in rings[0]]
    return (min(xs), min(ys), max(xs), max(ys))


def _model(features):
    return [(f["properties"]["ward"], _bbox(f["geometry"]), f["geometry"]) for f in features]


def _hits(model, pt):
    return [k for k, bb, g in model
            if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, g)]


# --- the build ------------------------------------------------------------

def wards_of(c, tmp):
    data = query(c["layer"], c["where"], c["field"])
    feats = [f for f in data.get("features", []) if f.get("geometry")]
    if not feats:
        raise RuntimeError("%s: the layer returned no features" % c["city"])
    for f in feats:
        f["properties"] = {"ward": c["read"](f["properties"][c["field"]])}
    got = sorted(set(f["properties"]["ward"] for f in feats))
    if got != c["wards"]:
        raise RuntimeError(
            "%s: the layer holds wards %s and the city elects from %s. A different "
            "set is a redistricting or the layer changing shape, and both need "
            "reading before anything ships." % (c["city"], got, c["wards"]))
    if not c["dissolve"] and len(feats) != len(got):
        raise RuntimeError("%s: %d features for %d wards in a layer read as one "
                           "feature per ward" % (c["city"], len(feats), len(got)))
    if c["dissolve"]:
        src = os.path.join(tmp, "precincts.json")
        out = os.path.join(tmp, "dissolved.json")
        with open(src, "w") as f:
            json.dump({"type": "FeatureCollection", "features": feats}, f)
        _mapshaper([src, "-dissolve", "ward", "-o", out, "format=geojson"], tmp)
        with open(out) as f:
            feats = json.load(f)["features"]
        print("  dissolved %d precincts to %d wards" % (len(data["features"]), len(feats)),
              file=sys.stderr)
    return sorted(feats, key=lambda f: f["properties"]["ward"])


def place_of(c):
    data = query(TIGERWEB_PLACE, "GEOID='%s'" % c["geoid"], "GEOID,BASENAME")
    feats = data.get("features", [])
    if len(feats) != 1:
        raise RuntimeError("%s: TIGERweb returned %d places for GEOID %s"
                           % (c["city"], len(feats), c["geoid"]))
    name = feats[0]["properties"].get("BASENAME")
    if name != c["city"]:
        raise RuntimeError("%s: GEOID %s is %r on TIGERweb" % (c["city"], c["geoid"], name))
    return feats


def tiling(c, wards, place, lat0, tmp):
    place_m2 = sum(_geom_area_m2(f["geometry"], lat0) for f in place)
    wards_m2 = sum(_geom_area_m2(f["geometry"], lat0) for f in wards)
    ratio = wards_m2 / place_m2
    p, w, u, g = (os.path.join(tmp, n) for n in ("p.json", "w.json", "u.json", "g.json"))
    with open(p, "w") as f:
        json.dump({"type": "FeatureCollection", "features": place}, f)
    with open(w, "w") as f:
        json.dump({"type": "FeatureCollection", "features": wards}, f)
    _mapshaper([w, "-dissolve", "-o", u, "format=geojson"], tmp)
    _mapshaper([p, "-erase", u, "-o", g, "format=geojson"], tmp)
    with open(g) as f:
        gap = json.load(f)
    parts = []
    for f in gap.get("features", []):
        for rings in _each_polygon(f.get("geometry")):
            a = _rings_area_m2(rings, lat0)
            per = _ring_perimeter_m(rings[0], lat0)
            ring = rings[0][:-1]
            centre = (sum(x for x, _ in ring) / len(ring), sum(y for _, y in ring) / len(ring))
            parts.append((a, (4.0 * math.pi * a / (per * per)) if per else 0.0, centre))
    total_sqmi = sum(a for a, _, _ in parts) / 2.58999e6
    largest = max((a for a, _, _ in parts), default=0.0)
    compact = sorted([t for t in parts if t[0] >= COMPACTNESS_MIN_AREA_M2
                      and t[1] > COMPACTNESS_CEILING], reverse=True)
    declared = list(c.get("accepted_holes", []))
    kept = []
    for t in compact:
        hit = [d for d in declared
               if _metres(t[2], (d["lng"], d["lat"]), lat0) <= 30.0
               and t[0] <= d["max_m2"]]
        if hit:
            print("  declared hole: %.0f m2 at %.5f,%.5f (%s)"
                  % (t[0], t[2][1], t[2][0], hit[0]["why"]), file=sys.stderr)
            declared.remove(hit[0])
        else:
            kept.append(t)
    compact = kept
    msg = ("wards/place area %.4f; %.4f sq mi of the place (%.3f%%) uncovered in %d "
           "parts, largest %.0f m2" % (ratio, total_sqmi,
                                       100.0 * total_sqmi * 2.58999e6 / place_m2,
                                       len(parts), largest))
    print("  tiling: " + msg, file=sys.stderr)
    problems = []
    if not IDENTITY_RATIO_LO <= ratio <= IDENTITY_RATIO_HI:
        problems.append("the wards' area is %.3f of the Census place's; outside "
                        "%.2f-%.2f this is not the same city" %
                        (ratio, IDENTITY_RATIO_LO, IDENTITY_RATIO_HI))
    for d in declared:
        problems.append("the hole declared at %.5f,%.5f is gone or has grown; "
                        "re-read it and retire or re-measure the entry"
                        % (d["lat"], d["lng"]))
    for a, pp, at in compact:
        problems.append("a COMPACT uncovered part of %.0f m2 (Polsby-Popper %.2f) near "
                        "%.5f,%.5f: ground in the city that no ward claims"
                        % (a, pp, at[1], at[0]))
    if c["max_sqmi"] is not None and (total_sqmi > c["max_sqmi"]
                                      or largest > c["max_part_m2"]):
        problems.append("the uncovered seam has grown past its measured ceiling "
                        "(%.2f sq mi / %.0f m2)" % (c["max_sqmi"], c["max_part_m2"]))
    return problems


def agreement(src_feats, out_feats, samples=4000, seed=2026):
    src, new = _model(src_feats), _model(out_feats)
    xs = [b for _, bb, _ in src for b in (bb[0], bb[2])]
    ys = [b for _, bb, _ in src for b in (bb[1], bb[3])]
    rng = random.Random(seed)
    agree = new_over = src_over = inside = 0
    for _ in range(samples):
        pt = (rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys)))
        s, o = _hits(new, pt), _hits(src, pt)
        new_over += len(s) > 1
        src_over += len(o) > 1
        inside += bool(o)
        if (s[0] if len(s) == 1 else len(s)) == (o[0] if len(o) == 1 else len(o)):
            agree += 1
    pct = 100.0 * agree / samples
    problems = []
    if new_over > src_over:
        problems.append("simplification added overlap (%d against the source's %d)"
                        % (new_over, src_over))
    if src_over > samples * SOURCE_OVERLAP_CEILING:
        problems.append("the source places %d/%d points in two wards" % (src_over, samples))
    if inside < samples * 0.25:
        problems.append("only %d/%d points fell in a ward" % (inside, samples))
    if pct < 99.5:
        problems.append("agreement %.2f%% (need 99.5%%)" % pct)
    print("  agreement: %d/%d (%.2f%%), %d inside a ward, overlap %d source / %d drawn"
          % (agree, samples, pct, inside, src_over, new_over), file=sys.stderr)
    return problems


def build(c, check_only):
    print("%s (%s)" % (c["city"], c["layer"]), file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        wards = wards_of(c, tmp)
        print("  layer last edited %s" % vintage(c["layer"]), file=sys.stderr)
        place = place_of(c)
        lat0 = sum(_bbox(f["geometry"])[1] for f in wards) / len(wards)
        problems = tiling(c, wards, place, lat0, tmp)
        for f in wards:
            n = f["properties"]["ward"]
            f["properties"] = {
                "ward": n,
                "label": "Ward %d" % n,
                "city": c["city"],
                "sqmiles": round(_geom_area_m2(f["geometry"], lat0) / 2.58999e6, 2),
            }
        src = os.path.join(tmp, "src.json")
        out = os.path.join(tmp, "out.json")
        with open(src, "w") as f:
            json.dump({"type": "FeatureCollection", "features": wards}, f)
        _mapshaper([src, "-simplify"] + SIMPLIFY +
                   ["-o", "precision=" + PRECISION, "format=geojson", out], tmp)
        with open(out) as f:
            result = json.load(f)
        if len(result["features"]) != len(wards):
            problems.append("mapshaper returned %d features for %d wards"
                            % (len(result["features"]), len(wards)))
        problems += agreement(wards, result["features"])
    if problems:
        raise RuntimeError("%s: %s" % (c["city"], "; ".join(problems)))
    result["boundarySource"] = c["layer"]
    if c["page"]:
        result["sourceUrl"] = c["page"]
    name = "%s-wards.json" % c["slug"]
    path = os.path.join(APP_DATA_DIR, name)
    payload = json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n"
    if check_only:
        with open(path) as f:
            if f.read() != payload:
                raise RuntimeError("%s has drifted from the source; re-run this builder" % name)
        print("  check: %s matches the source" % name, file=sys.stderr)
        return
    with open(path, "w") as f:
        f.write(payload)
    print("  wrote data/app/%s, %.1f KB" % (name, len(payload) / 1024.0), file=sys.stderr)


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    wanted = [a for a in args if not a.startswith("--")]
    known = {c["slug"] for c in CITIES}
    unknown = [w for w in wanted if w not in known]
    if unknown:
        sys.exit("unknown city %s; known: %s" % (", ".join(unknown), ", ".join(sorted(known))))
    failed = []
    for c in CITIES:
        if wanted and c["slug"] not in wanted:
            continue
        try:
            build(c, check_only)
        except Exception as e:  # report every city, then fail
            print("  FAILED: %s" % e, file=sys.stderr)
            failed.append(c["city"])
    if failed:
        sys.exit("failed: %s" % ", ".join(failed))


if __name__ == "__main__":
    main()
