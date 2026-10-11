#!/usr/bin/env python3
"""
Build tn/data/app/tn-commission-districts.json: every Tennessee county's
commission districts, from the Comptroller of the Treasury's own statewide
service, so the app draws them same-origin (cache-first) rather than
downloading 34 MB of full-precision geometry on a first toggle.

THE SOURCE. The Comptroller's Office of Local Government publishes the
county legislative body districts for all 95 counties in ONE layer —
"County Commission Districts New", layer 2 of its Redistricting_Address_Lookup
feature service, the districts each county drew after the 2020 census and
filed with the state. Measured 2026-10-11: 859 districts in 95 counties, each
county numbered 1..N with no gap and no duplicate, 0 overlapping points in
4,000 samples, and 99.86% agreement with the Census county fabric at points
inside both (2,941 of 2,945; the four misses sit on county lines). Its
robots.txt answers HTTP 403, which RFC 9309 reads as no policy (allow).

A DISTRICT IS NOT A SEAT. Many Tennessee counties elect more than one
commissioner from a district — the University of Tennessee's CTAS list carries
1,585 commissioners against these 859 districts (2026-10-11) — and the layer
carries no seat count, so this file says which district a point is in and
nothing about how many people represent it. Who sits for each district is a
separate roster.

THE COUNTY CODE ARRIVES IN TWO SPELLINGS. The COUNTY field is the county's
three-digit FIPS code, written "005" in some records and "5" in others; read
naively that is 118 "counties". It is normalised to the five-digit GEOID the
county layer uses, and the build refuses unless the result is exactly the 95
GEOIDs in state-counties.json.

THREE GATES BEFORE ANYTHING IS WRITTEN, shared with the legislative builder
next to this one (imported, same tree): the 2,000-point agreement test against
the full-precision fetch, the fidelity ceiling (no source vertex further than
FIDELITY_CEILING_M from its own district as drawn), and a county witness found
here — every district must answer, at points inside it, to its own county in
state-counties.json. That last one is what catches a mis-normalised code: the
geometry would still be self-consistent, in the wrong county.

SIMPLIFICATION. Douglas-Peucker at 20 m, the interval the legislative builder
uses, for the reason its docstring gives. Measured 2026-10-11 on this layer:
median source step 21.34 m, worst stray 21.4 m at interval=20 (0 of 859 over
the 25 m ceiling) and 31.2 m at interval=30 (846 of 859 over). The file is
3.96 MB, 978 KB gzipped.

Usage:
    python3 tn/scripts/build_tn_commission_districts.py           # fetch, build, write
    python3 tn/scripts/build_tn_commission_districts.py --check   # offline, the shipped file
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
# APPENDED, not inserted: the shared scripts/ directory has a
# build_legislative_boundaries.py of its own (Illinois's), and this file must
# import the one beside it.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_HEADERS_ROSTER_BOT,
    UA_ROSTER_BOT,
    require_robots_once,
)

sys.path.insert(0, _HERE)
import build_legislative_boundaries as blb  # noqa: E402  (same instance tree)
assert os.path.dirname(os.path.abspath(blb.__file__)) == _HERE, blb.__file__

INSTANCE_ROOT = os.path.dirname(_HERE)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT = "tn-commission-districts.json"
COUNTIES_FILE = os.path.join(APP_DATA_DIR, "state-counties.json")

SERVICE = ("https://services2.arcgis.com/63Ka7QbNqm4NLbeo/arcgis/rest/services/"
           "Redistricting_Address_Lookup/FeatureServer")
LAYER = 2
# The layer is chosen by index and checked by name, because an index alone
# proves nothing once a publisher re-orders a service. Layer 3 is the same
# service's "Old" plan.
LAYER_NAME = "County Commission Districts New"
PAGE = 200

EXPECTED_COUNTIES = 95
EXPECTED_DISTRICTS = 859
# The one board size stated outside the layer that this build checks: the
# Metropolitan Charter of Nashville and Davidson County, section 3.01, sets a
# council of 35 district members and 5 elected at large.
KNOWN_DISTRICT_COUNTS = {"47037": 35}

SIMPLIFY = "interval=20"
COUNTY_WITNESS_POINTS = 5


def _get(url):
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="tn-build-tn-commission-districts")
    req = urllib.request.Request(url, headers=UA_HEADERS_ROSTER_BOT)
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    if isinstance(data, dict) and "error" in data:
        # An ArcGIS error is an object, not an empty answer.
        raise SystemExit("FAIL: the Comptroller's service answered an error: %r"
                         % (data["error"],))
    return data


def fetch_source():
    meta = _get("%s/%d?f=json" % (SERVICE, LAYER))
    if meta.get("name") != LAYER_NAME:
        raise SystemExit("FAIL: layer %d is now %r, not %r — find the layer that "
                         "is, rather than draw a different plan"
                         % (LAYER, meta.get("name"), LAYER_NAME))
    edited = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    if edited:
        import datetime
        edited = datetime.datetime.fromtimestamp(
            edited / 1000, datetime.timezone.utc).date().isoformat()
    feats, seen, offset = [], set(), 0
    while True:
        q = urllib.parse.urlencode({
            "where": "1=1", "outFields": "OBJECTID,COUNTY,NEWCCDDISTRICT",
            "outSR": "4326", "geometryPrecision": "6", "f": "geojson",
            "orderByFields": "OBJECTID", "resultOffset": offset,
            "resultRecordCount": PAGE})
        page = _get("%s/%d/query?%s" % (SERVICE, LAYER, q))
        got = page.get("features") or []
        for f in got:
            oid = (f.get("properties") or {}).get("OBJECTID", f.get("id"))
            if oid in seen:
                raise SystemExit("FAIL: OBJECTID %r returned twice while paging" % oid)
            seen.add(oid)
            feats.append(f)
        more = page.get("exceededTransferLimit") or (
            (page.get("properties") or {}).get("exceededTransferLimit"))
        if not got or (len(got) < PAGE and not more):
            break
        offset += len(got)
    return feats, edited


def county_names():
    with open(COUNTIES_FILE) as fh:
        fc = json.load(fh)
    return {f["properties"]["GEOID"]: f["properties"]["NAME"] for f in fc["features"]}, fc


def normalise(features, names):
    """Rewrite each feature's properties to {countyfips, county, district}."""
    out = []
    for f in features:
        p = f.get("properties") or {}
        raw, dist = p.get("COUNTY"), p.get("NEWCCDDISTRICT")
        if raw is None or not str(raw).strip().isdigit():
            raise SystemExit("FAIL: a record carries COUNTY %r" % (raw,))
        if not isinstance(dist, int) or dist < 1:
            raise SystemExit("FAIL: county %s carries district %r" % (raw, dist))
        geoid = "47" + str(raw).strip().zfill(3)
        if geoid not in names:
            raise SystemExit("FAIL: county code %r normalises to %s, which is not a "
                             "Tennessee county in state-counties.json" % (raw, geoid))
        if not f.get("geometry"):
            raise SystemExit("FAIL: %s District %d has no geometry" % (names[geoid], dist))
        out.append({"type": "Feature",
                    "properties": {"countyfips": geoid, "county": names[geoid],
                                   "district": dist},
                    "geometry": f["geometry"]})
    return out


def check_structure(features, names):
    """Counts and numbering. Returns {geoid: n districts}."""
    by = {}
    for f in features:
        p = f["properties"]
        by.setdefault(p["countyfips"], []).append(p["district"])
    problems = []
    if len(features) != EXPECTED_DISTRICTS:
        problems.append("%d districts, expected %d" % (len(features), EXPECTED_DISTRICTS))
    if set(by) != set(names):
        problems.append("counties differ from state-counties.json: missing %s, extra %s"
                        % (sorted(set(names) - set(by)), sorted(set(by) - set(names))))
    for geoid, ds in sorted(by.items()):
        if sorted(ds) != list(range(1, len(ds) + 1)):
            problems.append("%s is numbered %s, not 1..%d"
                            % (names.get(geoid, geoid), sorted(ds), len(ds)))
    for geoid, n in KNOWN_DISTRICT_COUNTS.items():
        if len(by.get(geoid, [])) != n:
            problems.append("%s has %d districts; its charter sets %d"
                            % (names[geoid], len(by.get(geoid, [])), n))
    for f in features:
        p = f["properties"]
        if p.get("county") != names.get(p["countyfips"]):
            problems.append("%s carries county name %r"
                            % (p["countyfips"], p.get("county")))
    if problems:
        raise SystemExit("FAIL: " + "; ".join(problems[:8]))
    return {g: len(ds) for g, ds in by.items()}


def county_witness(features, counties_fc, seed=95):
    """Every district must answer to its own county at points inside it."""
    cmodel = [(f["properties"]["GEOID"], f["geometry"], blb._bbox(f["geometry"]))
              for f in counties_fc["features"]]
    rng = random.Random(seed)
    bad = []
    for f in features:
        p = f["properties"]
        bb = blb._bbox(f["geometry"])
        inside, tries = [], 0
        while len(inside) < COUNTY_WITNESS_POINTS and tries < 4000:
            tries += 1
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            if blb._point_in_geometry(pt, f["geometry"]):
                inside.append(pt)
        if not inside:
            bad.append("%s District %d: no interior point found" % (p["county"], p["district"]))
            continue
        own = sum(1 for pt in inside if p["countyfips"] in blb._districts_at(cmodel, pt))
        if own * 2 <= len(inside):
            bad.append("%s District %d: %d of %d interior points in its own county"
                       % (p["county"], p["district"], own, len(inside)))
    if bad:
        raise SystemExit("FAIL: county witness: " + "; ".join(bad[:8]))
    return len(features)


def _keyed(features):
    for f in features:
        p = f["properties"]
        p["_key"] = "%s-%d" % (p["countyfips"], p["district"])
    return features


def build():
    names, counties_fc = county_names()
    raw, edited = fetch_source()
    source = normalise(raw, names)
    check_structure(source, names)
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "ccd-src.geojson")
        with open(src_path, "w") as fh:
            json.dump({"type": "FeatureCollection", "features": source}, fh)
        out_tmp = os.path.join(tmp, "ccd.geojson")
        blb.run_mapshaper(src_path, SIMPLIFY, out_tmp)
        with open(out_tmp) as fh:
            simplified = json.load(fh)
    drawn = simplified["features"]
    sizes = check_structure(drawn, names)

    _keyed(source)
    _keyed(drawn)
    ok, msg = blb.validate(source, drawn, "_key")
    if not ok:
        raise SystemExit("FAIL: validation: " + msg)
    step = blb.median_source_step_m(source)
    worst, over = blb.check_fidelity(source, drawn, "_key")
    if over:
        raise SystemExit("FAIL: %d district(s) stray past the %.0f m ceiling (worst %.1f m): %s"
                         % (len(over), blb.FIDELITY_CEILING_M, worst, ", ".join(sorted(over)[:5])))
    for f in drawn:
        f["properties"].pop("_key", None)
    witnessed = county_witness(drawn, counties_fc)

    compact = json.dumps({"type": "FeatureCollection", "features": drawn},
                         separators=(",", ":"))
    with open(os.path.join(APP_DATA_DIR, OUT), "w") as fh:
        fh.write(compact)
    print("%s: %d districts in %d counties (largest board %d districts); %s; "
          "median source step %.2f m, worst stray %.1f m against a %.0f m ceiling; "
          "county witness held for %d of %d; source last edited %s; %d bytes"
          % (OUT, len(drawn), len(sizes), max(sizes.values()), msg, step, worst,
             blb.FIDELITY_CEILING_M, witnessed, len(drawn), edited, len(compact)))


def check():
    names, counties_fc = county_names()
    with open(os.path.join(APP_DATA_DIR, OUT)) as fh:
        fc = json.load(fh)
    sizes = check_structure(fc["features"], names)
    county_witness(fc["features"], counties_fc)
    print("OK: %s carries %d districts in %d counties, each numbered 1..N, and every "
          "district answers to its own county" % (OUT, sum(sizes.values()), len(sizes)))


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check()
    elif not sys.argv[1:]:
        build()
    else:
        raise SystemExit(__doc__)
