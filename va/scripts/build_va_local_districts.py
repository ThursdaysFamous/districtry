#!/usr/bin/env python3
"""
Build va/data/app/va-local-districts.json: the districts Virginia's counties
and cities elect their boards of supervisors, city councils and school boards
from, drawn from the precincts in va/data/app/va-precincts.json.

    python3 va/scripts/build_va_local_districts.py              # fetch Norfolk's map, build, write
    python3 va/scripts/build_va_local_districts.py --source F   # build from a kept fetch
    python3 va/scripts/build_va_local_districts.py --check      # offline, for CI

WHERE THE LINES COME FROM. Every precinct lies wholly inside one local
election district, and the Department of Elections' layer says which
(va/scripts/va_localities.py reads it, and corrects the four localities and
the district names the layer gets wrong). A district is drawn as the union of
its precincts, so its lines are the precinct file's lines, drawn to within
12 metres, and a district's edge can never disagree with a precinct's. Adam
chose the Department's lines on 22 October 2026 ("as recommended").

WHICH DISTRICTS ARE DRAWN. Only those a body is elected from. The names
builder (build_va_local_officials.py) reads each locality's election results
and lists, for every district, the seats elected from it; a locality whose
results elect every member at large has no district here, though the layer
may give it some (measured 2026-10-30: Charlottesville, Harrisonburg and
Staunton, whose councils and school boards are elected at large while the
layer divides each city into districts). So a district is drawn exactly when
the names file lists it, and --check holds the two files to each other.

NORFOLK'S SUPERWARDS. Norfolk elects two council members and two school board
members from superwards 6 and 7, which the Department's layer does not carry.
They come from the city's own map (OpenData layer 8 on gisshare.norfolk.gov,
whose host publishes no robots.txt, read 2026-10-30), and each is drawn as the
union of the Norfolk precincts inside it, so its lines are the precincts'
too: every Norfolk precinct lies at least MIN_SHARE inside one superward,
which the build checks. A Norfolk point is therefore in one ward and one
superward, and the card names both.

MEASURED AGAINST FIVE LOCALITIES' OWN MAPS (2026-10-30), because the
Department's layer calls itself simplified. Each locality's own district
layer was fetched after its host's robots.txt was read with this builder's
client, and compared with the districts drawn here for that locality,
projecting both onto a flat plane at the locality's latitude:

  locality             its layer                                       same district   worst district
  Fairfax County       fairfaxcounty.gov Jade/Electoral MapServer 2    99.95% of ground   IoU 0.9978
  Loudoun County       logis.loudoun.gov ElectionDistricts MapServer 8 99.96%             IoU 0.9963
  Prince William Co.   gisweb.pwcva.gov GTS/Election MapServer 5       99.93%             IoU 0.9946
  Chesterfield County  services3.arcgis.com Administrative layer 9     99.97%             IoU 0.9960
  Norfolk (wards)      gisshare.norfolk.gov OpenData/Maps layer 7      99.94%             IoU 0.9955

"Same district" is the share of the ground both maps cover that both put in
the same district; IoU is a district's overlap with the drawn one divided by
their union. Every locality's districts matched one to one and by name, and
what differs is a strip along the lines a few metres wide, the 12-metre
drawing and the county's own drafting. Fairfax's and Norfolk's layers also
name each district's member, and all fourteen agree with the names file.
Fairfax's own Supervisor_Districts_2022 layer asks for a sign-in, which
stays shut; its Electoral service was read instead.

WHAT IS CHECKED BEFORE WRITING. Every district is one or more polygons; no
two districts of one locality overlap by a square metre; every precinct's
interior point lies in its own district and no other district of its
locality (bar a superward); and the districts of a locality cover exactly the
ground its districted precincts cover. The record keeps each district's
precincts and the file's SHA-256, so --check fails when the precinct file is
rebuilt and this one is not.
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))

import va_localities as vl  # noqa: E402

OUT = os.path.join(vl.DATA, "va-local-districts.json")
OFFICIALS = os.path.join(vl.DATA, "va-local-officials.json")
RECORD = os.path.join(vl.INSTANCE, "data", "source", "va-local-districts.record.json")
NORFOLK_LAYER = "https://gisshare.norfolk.gov/pubserver/rest/services/OpenData/Maps/FeatureServer/8"
USER_AGENT = "districtry/1.0 (+https://districtry.com/va/)"
SUPERWARDS = (6, 7)
MIN_SHARE = 0.99         # each Norfolk precinct at least this much inside one superward
PRECISION = 6


def fail(msg):
    print("build_va_local_districts: FAIL: %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def m2(g):
    if g.is_empty:
        return 0.0
    return g.area * 111320.0 ** 2 * math.cos(math.radians(g.representative_point().y))


def valid_shape(geometry):
    """A shapely shape of a drawn precinct. Simplifying can leave a precinct's
    ring touching itself (mapshaper reported 3 it could not repair on
    2026-10-30), which shapely's overlays refuse, so such a shape is repaired
    the way shapely repairs one, and the repair is counted."""
    from shapely.geometry import shape  # noqa: PLC0415

    g = shape(geometry)
    return g if g.is_valid else g.buffer(0)


def fetch_norfolk():
    import requests  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415

    url = NORFOLK_LAYER + "/query"
    require_robots_once(url, USER_AGENT, label="build_va_local_districts")
    r = requests.get(url, params={"where": "1=1", "outFields": "SUPWARD,last_edited_date",
                                  "outSR": "4326", "f": "geojson"},
                     headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    got = r.json()
    if "error" in got:
        fail("Norfolk's superward layer answered an error: %r" % got["error"])
    return got


def superward_of(norfolk, precincts):
    """Norfolk precinct key -> superward number, by the share of each precinct
    inside each superward of the city's map."""
    from shapely.geometry import shape  # noqa: PLC0415

    wards = {}
    for f in norfolk.get("features") or []:
        n = (f.get("properties") or {}).get("SUPWARD")
        if n in SUPERWARDS and f.get("geometry"):
            wards[n] = shape(f["geometry"]).buffer(0)
    if sorted(wards) != list(SUPERWARDS):
        fail("Norfolk's map gives superwards %r, expected %r" % (sorted(wards), SUPERWARDS))
    out, worst = {}, 1.0
    for f in precincts:
        p = f["properties"]
        if p["countyFips"] != "51" + vl.NORFOLK:
            continue
        g = valid_shape(f["geometry"])
        shares = {n: m2(g.intersection(w)) / m2(g) for n, w in wards.items()}
        n, share = max(shares.items(), key=lambda kv: kv[1])
        if share < MIN_SHARE:
            fail("Norfolk precinct %s (%s) is only %.3f inside superward %d; a superward is "
                 "no longer whole precincts" % (p["key"], p["name"], share, n))
        out[p["key"]] = n
        worst = min(worst, share)
    print("Norfolk: %d precincts, each at least %.4f inside one superward (%s)"
          % (len(out), worst, ", ".join("%d: %d precincts" % (n, sum(1 for v in out.values()
                                                                    if v == n))
                                        for n in SUPERWARDS)), file=sys.stderr)
    return out


def plan(precincts, officials, superwards):
    """The districts to draw: key -> {"fips", "number", "name", "precincts"}."""
    locs = vl.load_localities()
    ds = vl.districts(precincts)
    wanted = {}
    for geoid, loc in sorted(officials["localities"].items()):
        for key in loc.get("districts") or {}:
            wanted[key] = geoid[2:]
    out = {}
    for fips, entries in ds.items():
        for key, d in entries.items():
            if key in wanted:
                out[key] = {"fips": fips, "number": d["number"], "name": d["name"],
                            "precincts": list(d["precincts"])}
    for n in SUPERWARDS:
        key = "51%s-superward-%d" % (vl.NORFOLK, n)
        if key in wanted:
            out[key] = {"fips": vl.NORFOLK, "number": str(n), "name": "Superward %d" % n,
                        "precincts": sorted(k for k, v in superwards.items() if v == n)}
    missing = sorted(set(wanted) - set(out))
    if missing:
        fail("the names file lists districts no precinct is in: %s" % ", ".join(missing))
    for key, d in out.items():
        d["locality"] = locs[d["fips"]]["name"]
        d["kind"] = locs[d["fips"]]["kind"]
    return out


def draw(planned, precincts):
    from shapely.geometry import mapping  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    from shapely.geometry import shape  # noqa: PLC0415

    by_key = {f["properties"]["key"]: valid_shape(f["geometry"]) for f in precincts}
    print("%d of the drawn precincts touch themselves and were repaired before joining"
          % sum(1 for f in precincts if not shape(f["geometry"]).is_valid), file=sys.stderr)
    feats = []
    for key in sorted(planned):
        d = planned[key]
        g = unary_union([by_key[k] for k in d["precincts"]])
        if not g.is_valid:
            g = g.buffer(0)
        if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            fail("district %s drew as %s" % (key, g.geom_type))
        feats.append({"type": "Feature", "properties": {
            "key": key, "countyFips": "51" + d["fips"], "locality": d["locality"],
            "kind": d["kind"], "name": d["name"], "number": d["number"]},
            "geometry": mapping(g)})
    return feats


def round_coords(obj):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(obj[0], PRECISION), round(obj[1], PRECISION)]
        return [round_coords(x) for x in obj]
    return obj


def verify(feats, planned, precincts):
    """The checks the docstring lists. Returns the problems found."""
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    from shapely.strtree import STRtree  # noqa: PLC0415

    problems = []
    geoms = [shape(f["geometry"]) for f in feats]
    keys = [f["properties"]["key"] for f in feats]
    fips = [f["properties"]["countyFips"] for f in feats]
    for k, g in zip(keys, geoms):
        if not g.is_valid:
            problems.append("district %s is not a valid shape" % k)
    tree = STRtree(geoms)
    for i, g in enumerate(geoms):
        for j in tree.query(g):
            j = int(j)
            if j <= i or fips[i] != fips[j]:
                continue
            if "superward" in keys[i] or "superward" in keys[j]:
                continue
            over = m2(g.intersection(geoms[j]))
            if over >= 1.0:
                problems.append("districts %s and %s overlap by %.1f m2" % (keys[i], keys[j], over))
    by_key = {f["properties"]["key"]: valid_shape(f["geometry"]) for f in precincts}
    index = {k: i for i, k in enumerate(keys)}
    for key, d in planned.items():
        mine = geoms[index[key]]
        for pk in d["precincts"]:
            pt = by_key[pk].representative_point()
            if not mine.contains(pt):
                problems.append("precinct %s's interior point is outside its district %s" % (pk, key))
            for j in tree.query(pt):
                j = int(j)
                if keys[j] != key and fips[j] == fips[index[key]] and "superward" not in keys[j] \
                        and "superward" not in key and geoms[j].contains(pt):
                    problems.append("precinct %s's interior point is also in %s" % (pk, keys[j]))
    for loc in sorted(set(fips)):
        drawn = [geoms[i] for i in range(len(keys)) if fips[i] == loc and "superward" not in keys[i]]
        mine = [by_key[pk] for key, d in planned.items()
                if "51" + d["fips"] == loc and "superward" not in key for pk in d["precincts"]]
        a, b = unary_union(drawn), unary_union(mine)
        diff = m2(a.symmetric_difference(b))
        if diff >= 1.0:
            problems.append("%s: its districts and its precincts differ by %.1f m2" % (loc, diff))
    return problems


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(source):
    precincts = vl.load_precincts()
    with open(OFFICIALS, encoding="utf-8") as fh:
        officials = json.load(fh)
    if source:
        with open(source, encoding="utf-8") as fh:
            norfolk = json.load(fh)
    else:
        norfolk = fetch_norfolk()
    edited = max(((f.get("properties") or {}).get("last_edited_date") or 0)
                 for f in norfolk.get("features") or [])
    superwards = superward_of(norfolk, precincts)
    planned = plan(precincts, officials, superwards)
    feats = draw(planned, precincts)
    problems = verify(feats, planned, precincts)
    if problems:
        for p in problems[:40]:
            print("build_va_local_districts: FAIL: %s" % p, file=sys.stderr)
        raise SystemExit(1)
    for f in feats:
        f["geometry"]["coordinates"] = round_coords(f["geometry"]["coordinates"])
    fc = {"type": "FeatureCollection", "features": feats}
    data = json.dumps(fc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    with open(OUT, "wb") as fh:
        fh.write(data)
    with open(vl.PRECINCTS, "rb") as fh:
        precinct_sha = sha(fh.read())
    record = {
        "built": datetime.date.today().isoformat(),
        "precincts_sha256": precinct_sha,
        "shipped_sha256": sha(data),
        "norfolk_layer": NORFOLK_LAYER,
        "norfolk_edited": datetime.datetime.fromtimestamp(edited / 1000.0, datetime.timezone.utc)
        .date().isoformat()
        if edited else None,
        "norfolk_superwards": {k: superwards[k] for k in sorted(superwards)},
        "districts": {k: planned[k]["precincts"] for k in sorted(planned)},
    }
    os.makedirs(os.path.dirname(RECORD), exist_ok=True)
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    localities = len({f["properties"]["countyFips"] for f in feats})
    print("wrote %s: %d districts in %d counties and cities, %d bytes"
          % (os.path.relpath(OUT, os.path.join(vl.INSTANCE, "..")), len(feats), localities,
             len(data)))


def check():
    """Offline and without shapely: the shipped file is the one the record
    describes, built from today's precinct file, and it draws exactly the
    districts the names file lists."""
    problems = []
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    with open(OUT, "rb") as fh:
        data = fh.read()
    with open(vl.PRECINCTS, "rb") as fh:
        precinct_bytes = fh.read()
    with open(OFFICIALS, encoding="utf-8") as fh:
        officials = json.load(fh)
    if sha(data) != record["shipped_sha256"]:
        problems.append("the shipped file does not hash to what the builder recorded; rebuild it")
    if sha(precinct_bytes) != record["precincts_sha256"]:
        problems.append("va-precincts.json has changed since these districts were drawn from "
                        "it; rebuild them")
    precincts = json.loads(precinct_bytes.decode("utf-8"))["features"]
    ds = vl.districts(precincts)
    now = {key: d["precincts"] for entries in ds.values() for key, d in entries.items()}
    for n in SUPERWARDS:
        now["51%s-superward-%d" % (vl.NORFOLK, n)] = sorted(
            k for k, v in record["norfolk_superwards"].items() if v == n)
    for key, members in record["districts"].items():
        if now.get(key) != members:
            problems.append("district %s's precincts are not the ones it was drawn from" % key)
    wanted = {key for loc in officials["localities"].values() for key in loc.get("districts") or {}}
    shipped = json.loads(data.decode("utf-8"))["features"]
    keys = [f["properties"]["key"] for f in shipped]
    if len(set(keys)) != len(keys):
        problems.append("a district key appears twice in the shipped file")
    for key in sorted(wanted - set(keys)):
        problems.append("the names file lists %s and no district is drawn for it" % key)
    for key in sorted(set(keys) - wanted):
        problems.append("%s is drawn and the names file elects nobody from it" % key)
    if set(keys) != set(record["districts"]):
        problems.append("the shipped districts are not the recorded ones")
    for f in shipped:
        p = f["properties"]
        for field in ("key", "countyFips", "locality", "kind", "name"):
            if p.get(field) in (None, ""):
                problems.append("district %s has no %s" % (p.get("key"), field))
    if problems:
        for p in problems[:40]:
            print("build_va_local_districts --check: FAIL: %s" % p, file=sys.stderr)
        raise SystemExit(1)
    print("build_va_local_districts --check: OK — %d districts in %d counties and cities, drawn "
          "on %s from today's precinct file, matching the names file"
          % (len(keys), len({f["properties"]["countyFips"] for f in shipped}), record["built"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--source", help="Norfolk's superward layer as kept from an earlier fetch")
    ap.add_argument("--save-source", help="also keep Norfolk's superward layer here")
    args = ap.parse_args()
    if args.check:
        check()
        return
    if args.save_source and not args.source:
        got = fetch_norfolk()
        with open(args.save_source, "w", encoding="utf-8") as fh:
            json.dump(got, fh)
        args.source = args.save_source
    build(args.source)


if __name__ == "__main__":
    main()
