#!/usr/bin/env python3
"""
Build data/app/mi-isd-districts.json: Michigan's 56 intermediate school
districts, from the state's own layer.

An intermediate school district (ISD; also called an RESA, ESA or ESD) is a
special district the Revised School Code creates (MCL 380.601 et seq.). It
serves the local school districts inside it with special education, career and
technical programmes and other shared services, and it can levy its own tax.
Every part of Michigan's land lies in one.

THE SOURCE is the State of Michigan's own "Intermediate School Districts" layer
in the Michigan Geographic Framework, published by the DTMB Center for Shared
Solutions on the state's ArcGIS Online org and listed on the state's open-data
hub (item 735facc5c4e4406a8ec7f91454ce7e77, owner michigan_admin; 56 features,
MGF version V26, last edited 2026-03-03, measured 2026-10-01). Its licence is
stated outright: "This dataset is a public record and ... there are no
restrictions on the use, reproduction, or distribution of this dataset." An
older copy of the same layer sits on the state's MapServer
(OpenData/michigan_geographic_framework/MapServer/21, MGF 17A); the hub copy is
the newer one and is the one read here.

WHO SITS ON THE BOARD, and why this file names nobody. Under MCL 380.614 an
ISD's board is elected by an electoral body of one representative from each
local school board, not by voters; under MCL 380.615-617 an ISD whose voters
approved it elects its board at the ballot instead. Neither is a district a
reader votes in by address, no statewide roster of ISD board members was found
(measured 2026-10-01), and the layer carries no people. So the card names the
ISD and says how its board is chosen.

THE LAYER IS LAND-ONLY. Unlike the Census county fabric this app draws, the
framework stops at the shoreline, so a point out on a Great Lake is in no ISD
and the card says so in its own words rather than reading as a failed lookup.

Simplification is mapshaper's Douglas-Peucker with keep-shapes, which bounds how
far the drawn line strays from the true one (Visvalingam does not, which is the
fleet's measured lesson from the Illinois chambers and the Wisconsin NG911
layers). The interval was measured on 2026-10-01: 20 m wrote 1,337 KB, 50 m
838 KB (272 KB gzipped) with all 2,000 sample points agreeing, and 100 m
607 KB with one point in 2,000 changing district. Almost all of the bytes are
shoreline and the framework's 700-odd island rings, which cost a reader nothing
at a point inland and are kept so an island resident still gets an answer.
Gates, all before anything is written:
  * exactly 56 features, each with a distinct two-digit ISD code and a name;
  * the 2,000-random-point agreement gate against the full-precision fetch,
    with no overlap introduced by simplification.

Usage:
    python3 mi/scripts/build_mi_isd_districts.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)

INSTANCE = os.path.dirname(_HERE)
REPO_ROOT = os.path.dirname(INSTANCE)
OUT_PATH = os.path.join(INSTANCE, "data", "app", "mi-isd-districts.json")

LAYER_URL = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
             "services/IntermediateSchoolDistrict/FeatureServer/0")
OUT_FIELDS = "ISD,Name,Label"
EXPECT_FEATURES = 56

STATE_BBOX = {"minLng": -90.42, "minLat": 41.69, "maxLng": -82.12, "maxLat": 48.31}

MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)
SIMPLIFY = ["dp", "keep-shapes", "interval=50"]
PRECISION = "0.000001"  # 6 decimals ~= 0.11 m


def fetch_json(url, attempts=4):
    require_robots_once(url, UA_STDLIB_DEFAULT, label="mi-build-mi-isd-districts")
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA_STDLIB_DEFAULT})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                raise SystemExit("%s answered an error: %s" % (url, data["error"]))
            return data
        except SystemExit:
            raise
        except Exception as exc:  # URLError, socket timeout, malformed JSON
            last = exc
            if attempt == attempts - 1:
                break
            time.sleep(2 ** attempt)
    raise SystemExit("%s failed after %d attempts: %s" % (url, attempts, last))


def fetch_source():
    url = (LAYER_URL + "/query?where=1%3D1&outFields=" + OUT_FIELDS +
           "&outSR=4326&geometryPrecision=6&f=geojson")
    feats = fetch_json(url).get("features", [])
    if len(feats) != EXPECT_FEATURES:
        raise SystemExit("the layer answered %d features, expected %d"
                         % (len(feats), EXPECT_FEATURES))
    codes = set()
    for f in feats:
        p = f.get("properties") or {}
        code, name = (p.get("ISD") or "").strip(), (p.get("Name") or "").strip()
        if len(code) != 2 or not code.isdigit() or not name:
            raise SystemExit("a feature has no usable ISD code or name: %r" % p)
        if code in codes:
            raise SystemExit("ISD code %s appears twice" % code)
        codes.add(code)
        f["properties"] = {"ISD": code, "NAME": name}
    return feats


def run_mapshaper(source_path, out_path):
    subprocess.run(
        ["npx", "-y", MAPSHAPER, source_path, "-simplify"] + SIMPLIFY +
        ["-o", "precision=" + PRECISION, "format=geojson", out_path],
        check=True, cwd=REPO_ROOT,
    )


def _in_ring(pt, ring):
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


def _in_geom(pt, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if _in_ring(pt, poly[0]) and not any(_in_ring(pt, h) for h in poly[1:]):
            return True
    return False


def _model(features):
    out = []
    for f in features:
        g = f["geometry"]
        rings = [r for poly in (g["coordinates"] if g["type"] == "MultiPolygon"
                                else [g["coordinates"]]) for r in poly]
        xs = [p[0] for r in rings for p in r]
        ys = [p[1] for r in rings for p in r]
        out.append((f["properties"]["ISD"], g, (min(xs), min(ys), max(xs), max(ys))))
    return out


def _at(model, pt):
    return [k for k, g, (a, b, c, d) in model
            if a <= pt[0] <= c and b <= pt[1] <= d and _in_geom(pt, g)]


def validate(source, result, samples=2000, seed=2024):
    src, new = _model(source), _model(result)
    rng = random.Random(seed)
    agree = introduced = 0
    for _ in range(samples):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        o, s = _at(src, pt), _at(new, pt)
        if len(s) > 1 and len(o) <= 1:
            introduced += 1
        if sorted(o) == sorted(s):
            agree += 1
    pct = 100.0 * agree / samples
    if introduced:
        return False, "simplification put %d points in two districts" % introduced
    if pct < 99.5:
        return False, "agreement only %.2f%% (need >= 99.5%%)" % pct
    return True, "%d/%d (%.2f%%) points agree with the full-precision fetch" % (
        agree, samples, pct)


def main():
    source = fetch_source()
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "src.json")
        out_tmp = os.path.join(tmp, "out.json")
        with open(src_path, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": source}, fh)
        run_mapshaper(src_path, out_tmp)
        with open(out_tmp) as fh:
            result = json.load(fh)["features"]
    if len(result) != EXPECT_FEATURES:
        raise SystemExit("%d features after simplify (expected %d)"
                         % (len(result), EXPECT_FEATURES))
    ok, msg = validate(source, result)
    print("validate: " + msg)
    if not ok:
        raise SystemExit("refusing to write: " + msg)
    result.sort(key=lambda f: f["properties"]["ISD"])
    with open(OUT_PATH, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": result}, fh,
                  separators=(",", ":"))
    print("wrote %s: %d districts, %.1f KB" % (os.path.relpath(OUT_PATH, REPO_ROOT),
          len(result), os.path.getsize(OUT_PATH) / 1024.0))


if __name__ == "__main__":
    main()
