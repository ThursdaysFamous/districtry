#!/usr/bin/env python3
"""
Build data/app/ok-commissioner-districts.json — Oklahoma's 231 county
commissioner districts, three in each of the 77 counties (19 O.S. 321) — from
the Oklahoma Department of Transportation's statewide layer.

Like build_legislative_boundaries.py this is an occasional OPERATOR step, not
weekly CI: a county redraws its districts after a census, and ok/WATCH.md
carries the re-check. The names on the card come from a different publisher
(the State Election Board's officer roster) and a different builder,
build_ok_commissioner_roster.py.

THE SOURCE IS THE STATE'S, AND A SECOND COPY IS COMPARED AGAINST IT RATHER
THAN SHIPPED. Two ArcGIS layers publish all 231 districts: ODOT's
County_Commissioner_Districts (data last edited 2023-01-20) and a
University of Oklahoma copy, Commissioner_Districts_2020 (edited 2026). The
fleet rule (Adam, 2026-09-29) is government publishers first, so ODOT's is
the one drawn. Measured 2026-10-11, the two agree on 229 of the 231 districts
to an intersection-over-union of 1.000, and disagree in ONE county: Beaver,
where they draw the line between Districts 1 and 2 differently over 27.6 km²
(IoU 0.986 for District 1 and 0.980 for District 2; District 3 agrees). Which
copy is right is not established here. So the disagreement is pinned in
KNOWN_DISAGREEMENTS, re-measured on every run, and written onto the two
Beaver features as `lineNote`, which the card prints. A run FAILS when a new
county disagrees, when Beaver's area moves by more than a tenth, or when
Beaver stops disagreeing (the entry must then be retired, not left to excuse
nothing).

SIMPLIFICATION IS DOUGLAS-PEUCKER, ALL 231 DISTRICTS IN ONE MAPSHAPER RUN.
One run builds one topology, so the line two neighbouring districts share —
inside a county or along a county line — is one arc simplified once and the
districts still tile the state with no slivers between them. The interval is
absolute metres, and the fidelity gate below measures how far the TRUE line
strays from the chord drawn in its place, against the same pinned 25 m
ceiling the legislative builder uses.

Prerequisites: curl, Node.js (mapshaper via npx), and shapely for the
second-copy comparison (pinned in scripts/requirements.txt).

Usage:
    python3 ok/scripts/build_ok_commissioner_districts.py
"""

import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_legislative_boundaries as lb  # noqa: E402  (same tree, same gates)

REPO_ROOT = lb.REPO_ROOT
APP_DATA_DIR = lb.APP_DATA_DIR
OUT = "ok-commissioner-districts.json"

ODOT = ("https://services6.arcgis.com/RBtoEUQ2lmN0K3GY/arcgis/rest/services/"
        "County_Commissioner_Districts/FeatureServer/0")
SECOND_COPY = ("https://services.arcgis.com/3xOwF6p0r7IHIjfn/arcgis/rest/services/"
               "Commissioner_Districts_2020/FeatureServer/0")

COUNTIES = 77
PER_COUNTY = 3
SIMPLIFY = "interval=20"

# Where the second copy draws a district differently, measured 2026-10-11.
# county FIPS (3 digits) -> the districts the line moves between, the area
# that changes hands, and the sentence the card prints.
KNOWN_DISAGREEMENTS = {
    "007": {
        "county": "Beaver",
        "districts": [1, 2],
        "km2": 27.6,
        "note": ("A second published copy of this map, kept by the University "
                 "of Oklahoma, draws the line between Districts 1 and 2 "
                 "differently over about 28 square kilometres in the north and "
                 "east of Beaver County. This map follows the state Department "
                 "of Transportation's copy. If you live near that line, the "
                 "county election board can say which district you vote in."),
    },
}
# A district is counted as disagreeing below this IoU. The 229 that agree
# measured 1.000; Beaver's two measured 0.986 and 0.980.
IOU_FLOOR = 0.999


def fetch(url, fields):
    q = (url + "/query?where=1%3D1&outFields=" + ",".join(fields) +
         "&outSR=4326&geometryPrecision=6&f=geojson")
    out = subprocess.run(["curl", "-sS", "--fail", "--max-time", "300", q],
                         check=True, capture_output=True).stdout
    geo = json.loads(out)
    if "error" in geo:
        raise RuntimeError("%s answered an error: %s" % (url, geo["error"]))
    if geo.get("exceededTransferLimit"):
        raise RuntimeError("%s hit its transfer cap — needs paging" % url)
    return geo


def county_names():
    with open(os.path.join(APP_DATA_DIR, "state-counties.json")) as f:
        g = json.load(f)
    return {ft["properties"]["COUNTY"]: ft for ft in g["features"]}


def normalise(src, counties):
    """ODOT's properties -> the four the app reads, with exact-count guards."""
    feats = []
    seen = {}
    for ft in src["features"]:
        p = ft["properties"]
        fips = str(p.get("CO_FIPS") or "").zfill(3)
        d = int(str(p.get("COMMDIST")).strip())
        if fips not in counties:
            raise RuntimeError("district with unknown county FIPS %r" % fips)
        if d not in (1, 2, 3):
            raise RuntimeError("%s: district number %r is not 1-3" % (fips, d))
        key = "40" + fips + "-" + str(d)
        if key in seen:
            raise RuntimeError("district %s published twice" % key)
        seen[key] = True
        name = counties[fips]["properties"]["BASENAME"]
        feats.append({
            "type": "Feature",
            "properties": {
                "key": key,
                "name": "District " + str(d),
                "county": name,
                "countyFips": "40" + fips,
                "district": d,
            },
            "geometry": ft["geometry"],
        })
    by_county = {}
    for ft in feats:
        by_county.setdefault(ft["properties"]["countyFips"], []).append(ft)
    short = sorted(k for k, v in by_county.items() if len(v) != PER_COUNTY)
    if len(by_county) != COUNTIES or short:
        raise RuntimeError("expected %d counties x %d districts; got %d counties, "
                           "wrong count in %s" % (COUNTIES, PER_COUNTY, len(by_county), short))
    return feats


def check_inside_county(feats, counties):
    """Every district's interior point must fall in the county it is labelled
    with, using the app's own even-odd test on the shipped county file."""
    bad = []
    for ft in feats:
        from shapely.geometry import shape
        pt = shape(ft["geometry"]).representative_point()
        cty = counties[ft["properties"]["countyFips"][2:]]
        if not lb._point_in_geometry((pt.x, pt.y), cty["geometry"]):
            bad.append(ft["properties"]["key"])
    if bad:
        raise RuntimeError("district(s) outside their own county: %s" % ", ".join(bad))


def compare_second_copy(feats):
    """Measure where the University of Oklahoma's copy disagrees, and hold the
    result to KNOWN_DISAGREEMENTS."""
    from shapely.geometry import shape
    other = fetch(SECOND_COPY, ["COUNTYFP", "DISTRICT"])
    theirs = {}
    for ft in other["features"]:
        p = ft["properties"]
        k = "40" + str(p["COUNTYFP"]).zfill(3) + "-" + str(int(str(p["DISTRICT"]).strip()))
        g = shape(ft["geometry"]).buffer(0)
        theirs[k] = theirs[k].union(g) if k in theirs else g
    ours = {ft["properties"]["key"]: shape(ft["geometry"]).buffer(0) for ft in feats}
    if set(ours) != set(theirs):
        raise RuntimeError("the second copy names different districts: only ours %s, only theirs %s"
                           % (sorted(set(ours) - set(theirs)), sorted(set(theirs) - set(ours))))
    disagree = {}
    for k, a in ours.items():
        b = theirs[k]
        iou = a.intersection(b).area / a.union(b).area
        if iou < IOU_FLOOR:
            disagree.setdefault(k[2:5], []).append((k, iou, a.symmetric_difference(b)))
    problems = []
    for fips, rows in sorted(disagree.items()):
        want = KNOWN_DISAGREEMENTS.get(fips)
        if not want:
            problems.append("county %s disagrees and is not recorded: %s"
                            % (fips, ", ".join("%s IoU %.3f" % (k, i) for k, i, _ in rows)))
            continue
        got = sorted(int(k.split("-")[1]) for k, _, _ in rows)
        if got != want["districts"]:
            problems.append("county %s: districts %s disagree, recorded %s" % (fips, got, want["districts"]))
        lat = rows[0][2].centroid.y
        km2 = rows[0][2].area * (111.32 ** 2) * math.cos(math.radians(lat))
        if abs(km2 - want["km2"]) > want["km2"] * 0.1:
            problems.append("county %s: %.1f km2 disagrees, recorded %.1f" % (fips, km2, want["km2"]))
        print("second copy: %s County Districts %s disagree over %.1f km2 (recorded %.1f)"
              % (want["county"], got, km2, want["km2"]))
    for fips in sorted(set(KNOWN_DISAGREEMENTS) - set(disagree)):
        problems.append("county %s is recorded as disagreeing and now agrees — retire the entry" % fips)
    if problems:
        raise RuntimeError("second-copy comparison: " + "; ".join(problems))
    print("second copy: %d of %d districts agree to IoU >= %.3f"
          % (len(ours) - sum(len(v) for v in disagree.values()), len(ours), IOU_FLOOR))


def main():
    counties = county_names()
    src = fetch(ODOT, ["CO_FIPS", "COUNTY", "COMMDIST"])
    feats = normalise(src, counties)
    check_inside_county(feats, counties)
    compare_second_copy(feats)

    source = {"type": "FeatureCollection", "features": feats}
    with tempfile.TemporaryDirectory() as tmp:
        sp = os.path.join(tmp, "src.geojson")
        with open(sp, "w") as f:
            json.dump(source, f)
        op = os.path.join(tmp, "out.geojson")
        lb.run_mapshaper(sp, SIMPLIFY, op)
        with open(op) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != COUNTIES * PER_COUNTY:
        raise RuntimeError("%d features after simplify (expected exactly %d) — refusing to write"
                           % (n, COUNTIES * PER_COUNTY))
    ok, msg = lb.validate(feats, simplified["features"], "key")
    if not ok:
        raise RuntimeError("validation failed: " + msg)
    step = lb.median_source_step_m(feats)
    worst, over = lb.check_fidelity(feats, simplified["features"], "key")
    if over:
        raise RuntimeError("%d district(s) stray past the %.0f m ceiling (worst %.1f m): %s"
                           % (len(over), lb.FIDELITY_CEILING_M, worst, ", ".join(sorted(over)[:5])))
    print("median source step %.2f m, worst stray %.1f m against a %.0f m ceiling, 0 of %d over"
          % (step, worst, lb.FIDELITY_CEILING_M, n))

    for ft in simplified["features"]:
        p = ft["properties"]
        rec = KNOWN_DISAGREEMENTS.get(p["countyFips"][2:])
        if rec and p["district"] in rec["districts"]:
            p["lineNote"] = rec["note"]
    simplified["features"].sort(key=lambda ft: ft["properties"]["key"])

    compact = json.dumps(simplified, separators=(",", ":"))
    with open(os.path.join(APP_DATA_DIR, OUT), "w") as f:
        f.write(compact)
    print("-> data/app/%s: %d districts in %d counties; %s; %d bytes (dp %s, 6dp)"
          % (OUT, n, COUNTIES, msg, len(compact), SIMPLIFY))


if __name__ == "__main__":
    main()
