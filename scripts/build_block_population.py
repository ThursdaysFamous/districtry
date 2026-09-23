#!/usr/bin/env python3
"""Build il/data/app/population/, the Census 2020 block populations by county.

WHAT IT IS FOR. Comparing two districts by AREA says how much ground they
share; a reader asking whether their ward sits inside a congressional district
usually means PEOPLE. The app has no population data, so this ships the
smallest unit the Census counts: every populated 2020 census block, as its
internal point and its POP100. The engine's measurePointWeight
(engine/index.html/geometry-measure.txt) sums the points inside a district, and
because Illinois's congressional, legislative and ward maps are drawn on block
lines, that sum is the district's population rather than an estimate of it.
Districts that do not follow block lines (school districts, fire districts)
get a close figure, since a block straddling their edge counts wholly on the
side its internal point falls.

ONE FILE PER COUNTY, NOT PER STATE. The statewide set is 278,166 populated
blocks; a comparison needs only the counties a district touches, so the app
reads `index.json` (each county's extent, population and file) and fetches the
rest on demand. Nothing here is precached: the service worker serves these by
prefix, cached on first use, the way it serves fonts. Unpopulated blocks
(91,812 of 369,978) are dropped — they add nothing to any sum.

THE SOURCE AND ITS WITNESSES. Blocks come from TIGERweb's Census 2020 block
layer (Tracts_Blocks/MapServer/12), read county by county. The build refuses to
write unless three independent totals agree:
  - every county's block sum equals the SAME census's tract sum for that
    county (Tracts_Blocks/MapServer/10), an aggregation this script does not
    perform;
  - the state total equals 12,812,508, Illinois's published 2020 census count;
  - every block with people is kept: the blocks read per county add up to
    the statewide populated-block count the layer itself reports.

THE POINTS ARE HELD TO THE DISTRICTS THEY WILL BE SUMMED INSIDE. --check also
runs the engine's own measurePointWeight, as shipped, over every Illinois
congressional, State Senate and State House district in il/data/app, and fails
unless each map partitions the state EXACTLY (its districts sum to 12,812,508,
so no block falls in none or in two) and each district lands where its plan
put it: every congressional district within 0.01% of the 753,677-person ideal,
every legislative district within 1%. Measured 2026-09-23 on the simplified
district files the app ships: congress 753,665-753,691 (worst 14 people off,
0.002%), senate -0.20% to +0.19%, house -0.22% to +0.29%, and all three maps
exact to the person across the state. A block's point landing on the wrong side
of a simplified line is the whole of that error, which is also the size of the
error a reader will see.

WHEN IT CHANGES. Not until the 2030 census publishes blocks (2031). WATCH.md
carries the row. --check re-derives every file's totals, extent and count from
its own points against index.json, so a hand edit or a truncated file fails
CI. It is offline and needs only the standard library and Node.

Usage:
  python3 scripts/build_block_population.py           # rebuild (network)
  python3 scripts/build_block_population.py --check   # CI gate (offline; stdlib + node)
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "il", "data", "app", "population")
INDEX = os.path.join(OUT_DIR, "index.json")
UA = "districtry-block-population/1.0 (+https://districtry.com/il/)"
SERVICE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer"
BLOCKS = SERVICE + "/12"   # Census 2020 > Census Blocks
TRACTS = SERVICE + "/10"   # Census 2020 > Census Tracts
COUNTIES = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1"
STATE = "17"
STATE_TOTAL = 12812508     # Illinois, 2020 Census apportionment-resident count (P.L. 94-171 total)
COUNTY_COUNT = 102
DIGITS = 5                 # ~1 m; a block's internal point only has to land on the right side of a line
PAGE = 20000


def fetch(url, params):
    q = url + "/query?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(q, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(data["error"])
            return data
        except Exception as err:  # noqa: BLE001 — retried, then raised
            if attempt == 3:
                raise
            print("build-block-population: retrying after %s" % err, file=sys.stderr)
            time.sleep(2 ** (attempt + 1))


def sum_by_county(url, extra_where=""):
    stats = json.dumps([
        {"statisticType": "sum", "onStatisticField": "POP100", "outStatisticFieldName": "pop"},
        {"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"},
    ])
    data = fetch(url, {"where": "STATE='%s'%s" % (STATE, extra_where), "groupByFieldsForStatistics": "COUNTY",
                       "outStatistics": stats, "f": "json"})
    return {f["attributes"]["COUNTY"]: (int(f["attributes"]["pop"]), int(f["attributes"]["n"]))
            for f in data["features"]}


def county_names():
    data = fetch(COUNTIES, {"where": "STATE='%s'" % STATE, "outFields": "COUNTY,NAME",
                            "returnGeometry": "false", "f": "json"})
    return {f["attributes"]["COUNTY"]: f["attributes"]["NAME"] for f in data["features"]}


def county_blocks(county):
    out, offset = [], 0
    while True:
        data = fetch(BLOCKS, {
            "where": "STATE='%s' AND COUNTY='%s' AND POP100>0" % (STATE, county),
            "outFields": "GEOID,INTPTLAT,INTPTLON,POP100", "returnGeometry": "false",
            "orderByFields": "GEOID", "resultOffset": offset, "resultRecordCount": PAGE, "f": "json",
        })
        feats = data.get("features") or []
        for f in feats:
            a = f["attributes"]
            out.append((a["GEOID"], round(float(a["INTPTLON"]), DIGITS), round(float(a["INTPTLAT"]), DIGITS),
                        int(a["POP100"])))
        if len(feats) < PAGE and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    geoids = [b[0] for b in out]
    if len(set(geoids)) != len(geoids):
        raise SystemExit("build-block-population: county %s returned a block twice across pages" % county)
    return out


def extent(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")


def build():
    names = county_names()
    tracts = sum_by_county(TRACTS)
    populated = sum_by_county(BLOCKS, " AND POP100>0")
    if len(names) != COUNTY_COUNT or set(names) != set(tracts):
        raise SystemExit("build-block-population: expected %d counties, the county layer has %d and the tract "
                         "layer %d" % (COUNTY_COUNT, len(names), len(tracts)))
    os.makedirs(OUT_DIR, exist_ok=True)
    index, fails = {}, []
    for county in sorted(names):
        blocks = county_blocks(county)
        pop = sum(b[3] for b in blocks)
        if pop != tracts[county][0]:
            fails.append("%s: blocks sum to %d, its tracts to %d" % (names[county], pop, tracts[county][0]))
        if len(blocks) != populated.get(county, (0, 0))[1]:
            fails.append("%s: read %d populated blocks, the layer reports %d"
                         % (names[county], len(blocks), populated.get(county, (0, 0))[1]))
        points = [[b[1], b[2], b[3]] for b in blocks]
        fips = STATE + county
        write_json(os.path.join(OUT_DIR, fips + ".json"), {
            "county": fips, "name": names[county], "population": pop, "blocks": len(points), "points": points})
        index[fips] = {"name": names[county], "file": fips + ".json", "population": pop,
                       "blocks": len(points), "bbox": extent(points)}
        print("build-block-population: %-22s %8d people in %6d blocks" % (names[county], pop, len(points)))
    total = sum(c["population"] for c in index.values())
    if total != STATE_TOTAL:
        fails.append("the state sums to %d, the 2020 census count is %d" % (total, STATE_TOTAL))
    if fails:
        raise SystemExit("build-block-population: refusing to write the index:\n  - " + "\n  - ".join(fails))
    write_json_indented(INDEX, {
        "_about": "GENERATED by scripts/build_block_population.py. Census 2020 populated blocks (POP100 > 0) "
                  "by Illinois county, each as [lng, lat, population] at its internal point, from TIGERweb "
                  "Tracts_Blocks/MapServer/12. Every county's sum equals the same census's tract sum; the state "
                  "sums to 12,812,508. Fixed until the 2030 census publishes blocks. Never hand-edit.",
        "source": BLOCKS, "vintage": "2020 Census (P.L. 94-171)", "state_population": total,
        "counties": index,
    })
    print("build-block-population: wrote %d county files, %d people in %d blocks"
          % (len(index), total, sum(c["blocks"] for c in index.values())))


def write_json_indented(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


# The engine block, the files, and the plan each map was drawn to.
MEASURE_BLOCK = os.path.join(ROOT, "engine", "index.html", "geometry-measure.txt")
DISTRICT_MAPS = [
    # (file, districts, allowed deviation from the equal-population ideal)
    ("il/data/app/congress-districts.json", 17, 0.0001),
    ("il/data/app/il-senate-districts.json", 59, 0.01),
    ("il/data/app/il-house-districts.json", 118, 0.01),
]
NODE_DRIVER = r"""
const fs = require("fs");
const [block, dir, ...maps] = process.argv.slice(1);
const m = new Function(fs.readFileSync(block, "utf8") + "\nreturn { measurePointWeight };")();
const idx = JSON.parse(fs.readFileSync(dir + "/index.json", "utf8"));
const pts = [];
for (const c of Object.values(idx.counties)) for (const p of JSON.parse(fs.readFileSync(dir + "/" + c.file, "utf8")).points) pts.push(p);
const out = {};
for (const f of maps) {
  out[f] = JSON.parse(fs.readFileSync(f, "utf8")).features
    .filter((x) => /^\d+$/.test(String((x.properties || {}).BASENAME)))
    .map((x) => [String(x.properties.BASENAME), m.measurePointWeight(x.geometry, pts)]);
}
process.stdout.write(JSON.stringify(out));
"""


def check_districts():
    """The points summed inside the shipped legislative maps, by the engine's
    own block: each map must partition the state exactly and put each
    district where its plan did."""
    maps = [os.path.join(ROOT, f) for f, _, _ in DISTRICT_MAPS]
    res = subprocess.run(["node", "-e", NODE_DRIVER, MEASURE_BLOCK, OUT_DIR] + maps,
                         capture_output=True, text=True)
    if res.returncode != 0:
        return ["the engine's measurePointWeight did not run in Node:\n" + res.stderr[-1500:]], ""
    got = json.loads(res.stdout)
    fails, notes = [], []
    for (rel, n, tol), path in zip(DISTRICT_MAPS, maps):
        rows = got[path]
        name = os.path.basename(rel)
        if len(rows) != n:
            fails.append("%s: %d numbered districts, expected %d" % (name, len(rows), n))
            continue
        total = sum(p for _, p in rows)
        if total != STATE_TOTAL:
            fails.append("%s: its districts hold %d people, the state %d — a block falls in no district or "
                         "in two" % (name, total, STATE_TOTAL))
        ideal = STATE_TOTAL / n
        worst = max(rows, key=lambda r: abs(r[1] - ideal))
        dev = (worst[1] - ideal) / ideal
        if abs(dev) > tol:
            fails.append("%s: District %s holds %d people, %.3f%% from its %.0f ideal (allowed %.2f%%)"
                         % (name, worst[0], worst[1], 100 * dev, ideal, 100 * tol))
        notes.append("%s worst %+.3f%%" % (name.replace("-districts.json", ""), 100 * dev))
    return fails, ", ".join(notes)


def check():
    fails = []
    if not os.path.exists(INDEX):
        raise SystemExit("build-block-population: FAIL — %s is missing; run the builder" % os.path.relpath(INDEX, ROOT))
    with open(INDEX, encoding="utf-8") as fh:
        idx = json.load(fh)
    counties = idx.get("counties") or {}
    if len(counties) != COUNTY_COUNT:
        fails.append("index names %d counties, Illinois has %d" % (len(counties), COUNTY_COUNT))
    on_disk = set(f for f in os.listdir(OUT_DIR) if f.endswith(".json")) - {"index.json"}
    named = set(c["file"] for c in counties.values())
    for f in sorted(on_disk - named):
        fails.append("%s is in the folder and not in index.json" % f)
    for f in sorted(named - on_disk):
        fails.append("index.json names %s, which is not in the folder" % f)
    total = 0
    for fips, rec in sorted(counties.items()):
        path = os.path.join(OUT_DIR, rec["file"])
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        pts = doc.get("points") or []
        pop = 0
        bad = 0
        for p in pts:
            if (len(p) != 3 or not isinstance(p[2], int) or p[2] <= 0 or not (-92 < p[0] < -87)
                    or not (36.9 < p[1] < 42.6)):
                bad += 1
            else:
                pop += p[2]
        if bad:
            fails.append("%s: %d point(s) are not [lng, lat, positive population] inside Illinois" % (rec["name"], bad))
        if doc.get("county") != fips or doc.get("name") != rec["name"]:
            fails.append("%s: the file says it is %r (%r)" % (fips, doc.get("county"), doc.get("name")))
        if pop != rec["population"] or pop != doc.get("population"):
            fails.append("%s: points sum to %d, the file says %s and the index %s"
                         % (rec["name"], pop, doc.get("population"), rec["population"]))
        if len(pts) != rec["blocks"] or len(pts) != doc.get("blocks"):
            fails.append("%s: %d points, the index says %d blocks" % (rec["name"], len(pts), rec["blocks"]))
        if pts and not bad and extent(pts) != rec["bbox"]:
            fails.append("%s: its points' extent is not the one the index records" % rec["name"])
        total += pop
    if total != STATE_TOTAL or idx.get("state_population") != STATE_TOTAL:
        fails.append("the counties sum to %d (index says %s); Illinois's 2020 census count is %d"
                     % (total, idx.get("state_population"), STATE_TOTAL))
    notes = ""
    if not fails:
        more, notes = check_districts()
        fails += more
    if fails:
        print("build-block-population: FAIL")
        for f in fails:
            print("  - " + f)
        return 1
    print("build-block-population: OK — %d county files, %s people in %s populated blocks, every file's sum, "
          "count and extent matching index.json and the state matching the 2020 census count; the congressional "
          "and legislative maps each partition it exactly (%s)"
          % (len(counties), format(total, ","), format(sum(c["blocks"] for c in counties.values()), ","), notes))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="offline CI gate; never writes")
    args = ap.parse_args()
    if args.check:
        sys.exit(check())
    build()
    sys.exit(check())


if __name__ == "__main__":
    main()
