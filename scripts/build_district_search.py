#!/usr/bin/env python3
"""Build il/data/app/district-search.json, the index behind searching "33rd ward".

WHAT IT IS. The search box geocodes addresses. A reader who knows the name of
a district rather than an address in it ("33rd ward", "State Senate District
7") got nothing from a geocoder, and had to click around the map until the
right shape turned up. This file lets the app answer that locally: one Point
feature per district, placed at the spot inside it farthest from its edges,
with the district's extent beside it, so a search result can select a point
inside the district and frame the whole of it without downloading the layer
first.

TWO HALVES, TWO OWNERS.
  * The PHRASING is a person's: il/data/source/district-search-phrases.json
    names each layer and the official name of its districts with the number
    taken out ("Ward" for "Ward 33"). The layer's sidebar label is added from
    metro-worksheet.json, never retyped, so the two cannot disagree.
  * The DISTRICTS are this script's: read from the same sources the layers
    themselves load, so a redistricting reaches the index by a rebuild rather
    than by somebody editing a list of 50 wards.
The variants a reader types ("ward #33", "33rd ward") are derived by the app
from the phrase, not stored, so there is one rule for all of them.

COUNTY-DISPATCHED LAYERS ("Lake County Board District 3"). Illinois's county
board layer is ~60 counties, most fetched live from each county's own GIS by
loader code that exists only in il/index.html. Those districts are read
THROUGH THE APP: scripts/dump_layer_districts.mjs boots it headless and asks
window.ChiExplorer.layerDistricts for every county's features and the hover
identity the map prints for each. Every county has a District 3, so each of
these districts carries its county ("where": "Lake County") and a query must
name it. A county whose districts are named rather than numbered or lettered
(Menard's "Rock Creek") is recorded in SKIP and not indexed.

BUILD vs --check.
  Building needs the network (two layers are loaded live by the app: Chicago's
  wards from the City's portal and CPD's police districts from its ArcGIS
  org) and shapely, for the interior point (polylabel). It is an operator
  step, like the repo's other boundary builders.
  --check is the CI gate and is stdlib-only and offline. It does not recompute
  the points; it asserts the properties that matter, re-derived from the
  shipped boundary files on every run:
    - the phrasing section is exactly what the phrase file + worksheet give;
    - every layer named is one the app registers;
    - for each layer whose boundary ships in il/data/app, every district is
      present and nothing else is, each point lies INSIDE the district it
      names, and each extent matches that district's geometry;
    - for the two live layers, which cannot be re-read offline, the district
      set is complete and the app still loads the dataset this index was
      built from — so a source swap in index.html fails here instead of
      leaving the index describing a map the app no longer draws.

    - for a county-dispatched layer, every county the index names is one the
      app still dispatches (a county dropped from the map must not stay
      searchable); a county the app dispatches and the index lacks is PRINTED,
      not failed, because counties join weekly and a rebuild needs a browser.

Usage:
  python3 scripts/build_district_search.py            # rebuild (network, shapely, playwright)
  python3 scripts/build_district_search.py --county-dump dump.json   # reuse a dump
  python3 scripts/build_district_search.py --check    # CI gate (offline, stdlib)
"""
import argparse
import json
import os
import re
import sys
import subprocess
import tempfile
import threading
import urllib.request
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_county_status import ALL_COUNTIES, slug_of  # noqa: E402  (the county page slugs are the app's dispatch keys)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE = os.path.join(ROOT, "il")
PHRASES = os.path.join(INSTANCE, "data", "source", "district-search-phrases.json")
OUT = os.path.join(INSTANCE, "data", "app", "district-search.json")
WORKSHEET = os.path.join(ROOT, "metro-worksheet.json")
INDEX_HTML = os.path.join(INSTANCE, "index.html")
UA = "districtry-district-search/1.0 (+https://districtry.com/il/)"

# Where each layer's districts come from. "file" layers ship in il/data/app;
# "live" layers are fetched by the app at runtime, so the builder reads the
# same service and --check can only confirm completeness and the source.
# `key` returns a district's number as a canonical string ("009" -> "9"), or
# None for a feature that is not a numbered district (TIGER's Lake Michigan
# filler, "District not defined").
def _num(v):
    s = str(v if v is not None else "").strip()
    return str(int(s)) if s.isdigit() and int(s) > 0 else None

SOURCES = {
    "ward": {
        "live": "https://data.cityofchicago.org/resource/p293-wvbd.geojson?$limit=200",
        "format": "geojson",
        "token": "p293-wvbd",
        "key": lambda p: _num(p.get("ward")),
        "ids": [str(n) for n in range(1, 51)],
    },
    "police-district": {
        "live": ("https://services2.arcgis.com/t3tlzCPfmaQzSWAk/arcgis/rest/services/"
                 "Police_District_Boundary_View/FeatureServer/0/query"
                 "?where=1%3D1&outFields=DISTRICT&returnGeometry=true&outSR=4326&f=json"),
        "format": "esri",
        "token": "Police_District_Boundary_View",
        "key": lambda p: _num(p.get("DISTRICT")),
        "count": 22,
    },
    "school-board": {"file": "school-board-districts.json", "key": lambda p: _num(p.get("district"))},
    "congress": {"file": "congress-districts.json", "key": lambda p: _num(p.get("BASENAME"))},
    "il-senate": {"file": "il-senate-districts.json", "key": lambda p: _num(p.get("BASENAME"))},
    "il-house": {"file": "il-house-districts.json", "key": lambda p: _num(p.get("BASENAME"))},
    "il-supreme-court": {"file": "il-supreme-court-districts.json", "key": lambda p: _num(p.get("DISTRICTN"))},
    "ccbr": {"file": "ccbr-districts.json", "key": lambda p: _num(p.get("DISTRICTN"))},
    # Read through the app's own loaders (scripts/dump_layer_districts.mjs).
    "county-board": {
        "app_layer": True,
        "skip": {
            "menard": "its five commissioner districts are NAMED ('Rock Creek', "
                      "'South Petersburg'), not numbered or lettered, so 'District 3' "
                      "cannot name one; indexing them needs a name-search rule first",
        },
    },
}

COUNTY_NAME = {slug_of(n): n for n, _ in ALL_COUNTIES}


def district_token(value):
    """A county district's hover identity as the id a reader types: '3' and
    'District 3' -> '3', 'c' -> 'C'. None when it is neither (a named district)."""
    v = re.sub(r"^\s*district\s+", "", str(value or ""), flags=re.I).strip()
    if v.isdigit() and int(v) > 0:
        return str(int(v))
    if re.fullmatch(r"[A-Za-z]", v):
        return v.upper()
    return None

DIGITS = 5            # ~1 m; the point only has to land inside a district
BBOX_TOLERANCE = 2e-5  # rounding slack when --check re-derives an extent


def normalize_phrase(text):
    """The same normalisation the app applies to a query: lower case, every run
    of non-alphanumerics one space. 'U.S. House District' -> 'u s house district'."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def worksheet_labels():
    w = load_json(WORKSHEET)
    return {l["id"]: l.get("label") or l["id"] for l in w["layers"]}


def phrase_layers():
    """The emitted `layers` section, derived from the phrase file + worksheet."""
    src = load_json(PHRASES)
    labels = worksheet_labels()
    out, problems = {}, []
    for entry in src["layers"]:
        lid, name = entry["layer"], entry["name"].strip()
        if lid not in labels:
            problems.append("%s: not a layer metro-worksheet.json registers" % lid)
            continue
        if lid not in SOURCES:
            problems.append("%s: no district source in SOURCES — say where its districts come from" % lid)
            continue
        if lid in out:
            problems.append("%s: named twice in the phrase file" % lid)
            continue
        phrases = []
        for p in [name, labels[lid]] + list(entry.get("aliases") or []):
            n = normalize_phrase(p)
            if n and n not in phrases:
                phrases.append(n)
        out[lid] = {"name": name, "label": labels[lid], "phrases": phrases}
        # a layer whose districts belong to one city names it, so a result for
        # Chicago's Ward 3 never reads as a suburb's Ward 3
        if entry.get("where"):
            out[lid]["where"] = entry["where"].strip()
        # a county-dispatched layer: every district carries its own county,
        # which the query must name ("Lake County Board District 3")
        if SOURCES.get(lid, {}).get("app_layer"):
            out[lid]["where_per_district"] = True
    # one phrase must never name two layers, or "house district 5" would be a
    # coin toss rather than a list — the app shows every layer that matches,
    # but a phrase OWNED twice is a phrase file mistake
    owner = {}
    for lid, spec in out.items():
        for p in spec["phrases"]:
            if p in owner:
                problems.append("phrase %r is claimed by both %s and %s" % (p, owner[p], lid))
            owner[p] = lid
    return out, problems


# ---------- geometry helpers (stdlib) ----------
def rings_of(geom):
    """Every ring of a GeoJSON Polygon/MultiPolygon, flattened. Point-in-polygon
    below is EVEN-ODD over all rings of a district, which is correct whatever
    the nesting — the property that makes an Esri ring list safe to read here."""
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return list(geom["coordinates"])
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


def point_in_rings(x, y, rings):
    inside = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def bbox_of(rings):
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return [min(xs), min(ys), max(xs), max(ys)]


def group_districts(features, key):
    """{district id: [rings...]} — a district drawn as more than one feature is
    the union of its features' rings, so a source that splits one never
    produces two results for it."""
    groups = {}
    for f in features:
        d = key(f.get("properties") or {})
        if d is None:
            continue
        groups.setdefault(d, []).extend(rings_of(f.get("geometry")))
    return groups


# ---------- build (network + shapely) ----------
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def esri_to_features(data):
    out = []
    for f in data.get("features", []):
        rings = (f.get("geometry") or {}).get("rings") or []
        out.append({"properties": f.get("attributes") or {},
                    "geometry": {"type": "Polygon", "coordinates": rings}})
    return out


def interior_point(rings):
    """The point of a district farthest from its edges (polylabel), found on the
    even-odd union of its rings so a hole stays a hole."""
    from shapely.geometry import Polygon
    from shapely.ops import polylabel
    shape = None
    for r in rings:
        if len(r) < 4:
            continue
        p = Polygon(r).buffer(0)
        shape = p if shape is None else shape.symmetric_difference(p)
    if shape is None or shape.is_empty:
        raise SystemExit("build-district-search: a district has no usable geometry")
    parts = list(getattr(shape, "geoms", [shape]))
    largest = max(parts, key=lambda g: g.area)
    pt = polylabel(largest, tolerance=1e-6)
    x, y = round(pt.x, DIGITS), round(pt.y, DIGITS)
    if not point_in_rings(x, y, rings):
        raise SystemExit("build-district-search: polylabel's point fell outside its own district after rounding")
    return [x, y]


def load_source(lid):
    spec = SOURCES[lid]
    if "file" in spec:
        return load_json(os.path.join(INSTANCE, "data", "app", spec["file"]))["features"]
    data = fetch(spec["live"])
    return esri_to_features(data) if spec["format"] == "esri" else data["features"]


def run_dump(layer_id):
    """Serve the repo on a free port, boot the app headless and dump the layer's
    districts through its own loaders (scripts/dump_layer_districts.mjs)."""
    handler = partial(SimpleHTTPRequestHandler, directory=ROOT)
    handler.log_message = lambda *a, **k: None
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            out = tmp.name
        env = dict(os.environ, BASE_URL="http://127.0.0.1:%d/il/" % server.server_address[1])
        subprocess.run(["node", os.path.join(ROOT, "scripts", "dump_layer_districts.mjs"), layer_id, out],
                       check=True, env=env, cwd=ROOT)
        return load_json(out)
    finally:
        server.shutdown()


def app_layer_districts(lid, dump):
    """{(county slug, district id): [rings]} for a county-dispatched layer,
    plus {slug: count} and the recorded skips. REFUSES a dump in which any
    county failed to load: a partial index would quietly drop counties."""
    spec = SOURCES[lid]
    if dump.get("layer") != lid:
        raise SystemExit("build-district-search: the dump is of %r, not %r" % (dump.get("layer"), lid))
    failed = [c["key"] for c in dump["counties"] if not c.get("ok")]
    if failed:
        raise SystemExit("build-district-search: %s — %d county source(s) failed to load (%s); refusing a "
                         "partial index. Re-run when they answer." % (lid, len(failed), ", ".join(failed)))
    groups, counts, skipped = {}, {}, {}
    for county in dump["counties"]:
        key = county["key"]
        if key in spec["skip"]:
            skipped[key] = spec["skip"][key]
            continue
        if key not in COUNTY_NAME:
            raise SystemExit("build-district-search: %s entry %r is not an Illinois county slug" % (lid, key))
        ids = [district_token(f["value"]) for f in county["features"]]
        if None in ids:
            bad = sorted({str(f["value"]) for f in county["features"] if district_token(f["value"]) is None})
            raise SystemExit("build-district-search: %s %s has districts that are neither numbered nor "
                             "lettered (%s) — index them by a new rule or record the county in SKIP"
                             % (lid, key, ", ".join(bad[:5])))
        for d, f in zip(ids, county["features"]):
            groups.setdefault((key, d), []).extend(rings_of(f["geometry"]))
        counts[key] = len(set(ids))
    for key in spec["skip"]:
        if key not in skipped:
            raise SystemExit("build-district-search: SKIP names %r, which the app no longer dispatches — "
                             "drop the entry" % key)
    return groups, counts, skipped


def district_name(layer_name, d, where=None):
    """'Ward 33'; with a county, '<County> <layer name> <id>' — 'Lake' +
    'County Board District' + '3' is 'Lake County Board District 3'."""
    return "%s %s %s" % (where, layer_name, d) if where else "%s %s" % (layer_name, d)


def district_sort_key(d):
    return (0, int(d), "") if d.isdigit() else (1, 0, d)


def build(county_dump=None):
    layers, problems = phrase_layers()
    if problems:
        raise SystemExit("build-district-search: " + "; ".join(problems))
    features, live = [], {}
    for lid in layers:
        spec = SOURCES[lid]
        if spec.get("app_layer"):
            dump = load_json(county_dump) if county_dump else run_dump(lid)
            groups, counts, skipped = app_layer_districts(lid, dump)
            for (key, d) in sorted(groups, key=lambda kd: (kd[0], district_sort_key(kd[1]))):
                rings = groups[(key, d)]
                where = COUNTY_NAME[key]
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": interior_point(rings)},
                    "properties": {"layer": lid, "id": d, "county": key, "where": where,
                                   "name": district_name(layers[lid]["name"], d, where),
                                   "bbox": [round(v, DIGITS) for v in bbox_of(rings)]},
                })
            live[lid] = {"source": "the app's own loaders (scripts/dump_layer_districts.mjs)",
                         "fetched": date.today().isoformat(), "counties": counts, "skipped": skipped}
            print("build-district-search: %-17s %3d district(s) in %d count%s (live, via the app); skipped %s"
                  % (lid, len(groups), len(counts), "y" if len(counts) == 1 else "ies", ", ".join(skipped) or "none"))
            continue
        groups = group_districts(load_source(lid), spec["key"])
        expect = spec.get("ids")
        if expect and sorted(groups, key=int) != expect:
            raise SystemExit("build-district-search: %s has districts %s, expected %s"
                             % (lid, sorted(groups, key=int), expect))
        if spec.get("count") and len(groups) != spec["count"]:
            raise SystemExit("build-district-search: %s has %d districts, expected %d"
                             % (lid, len(groups), spec["count"]))
        if "live" in spec:
            live[lid] = {"source": spec["token"], "fetched": date.today().isoformat(), "ids": sorted(groups, key=int)}
        for d in sorted(groups, key=int):
            rings = groups[d]
            bb = [round(v, DIGITS) for v in bbox_of(rings)]
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": interior_point(rings)},
                "properties": {"layer": lid, "id": d, "name": district_name(layers[lid]["name"], d), "bbox": bb},
            })
        print("build-district-search: %-17s %3d district(s)%s" % (lid, len(groups), " (live)" if lid in live else ""))
    return {
        "type": "FeatureCollection",
        "_about": "GENERATED by scripts/build_district_search.py from il/data/source/district-search-phrases.json and each layer's own boundary source. Never hand-edit; --check in CI fails on drift.",
        "layers": layers,
        "live": live,
        "features": features,
    }


def write(doc):
    """ONE DISTRICT PER LINE: compact on the wire (the app fetches this on a
    reader's first search) while a rebuild's diff still reads district by
    district. Everything but `features` is written indented."""
    head = {k: v for k, v in doc.items() if k != "features"}
    text = json.dumps(head, indent=1, ensure_ascii=False)
    lines = [json.dumps(f, ensure_ascii=False, separators=(",", ":")) for f in doc["features"]]
    body = text[:-2] + ',\n "features": [\n' + ",\n".join(lines) + "\n ]\n}\n"
    json.loads(body)  # the splice above must still be JSON
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(body)


# ---------- check (offline, stdlib) ----------
def dispatch_keys(lid, index_html):
    """The entry keys of a county-dispatched layer, read from its own
    registerCountyLayer block in il/index.html (the block runs to the next one)."""
    i = index_html.find('id: "%s"' % lid)
    if i < 0:
        return None
    j = index_html.find("registerCountyLayer({", i)
    return set(re.findall(r'\bkey:\s*"([a-z-]+)"', index_html[i:j if j > 0 else len(index_html)]))


def check_app_layer(lid, feats, doc, index_html):
    fails = []
    src = SOURCES[lid]
    keys = dispatch_keys(lid, index_html)
    if not keys:
        return ["%s: no registerCountyLayer block found in il/index.html" % lid]
    rec = (doc.get("live") or {}).get(lid) or {}
    indexed = {f["properties"].get("county") for f in feats}
    gone = sorted(indexed - keys)
    if gone:
        fails.append("%s: the index still names %s, which the app no longer dispatches — rebuild, or a "
                     "reader is sent to a district the map does not draw" % (lid, ", ".join(gone)))
    for key in src["skip"]:
        if key not in keys:
            fails.append("%s: SKIP names %r, which the app no longer dispatches" % (lid, key))
        if key in indexed:
            fails.append("%s: %r is both skipped and indexed" % (lid, key))
    counts = {}
    for f in feats:
        counts[f["properties"]["county"]] = counts.get(f["properties"]["county"], 0) + 1
    if counts != rec.get("counties"):
        fails.append("%s: the per-county district counts disagree with the ones recorded at build" % lid)
    missing = sorted(keys - indexed - set(src["skip"]))
    if missing:
        # NOT a failure: counties join weekly and a rebuild needs a browser.
        print("build-district-search: NOTE — %s: %d dispatched count%s not yet searchable by name (%s); "
              "run the builder to add them" % (lid, len(missing), "y" if len(missing) == 1 else "ies", ", ".join(missing)))
    return fails


def check():
    fails = []
    if not os.path.exists(OUT):
        raise SystemExit("build-district-search: FAIL — %s is missing; run the builder" % os.path.relpath(OUT, ROOT))
    doc = load_json(OUT)
    layers, problems = phrase_layers()
    fails += problems
    if doc.get("layers") != layers:
        fails.append("the layers/phrases section is not what the phrase file and worksheet give — rebuild")
    index_html = open(INDEX_HTML, encoding="utf-8").read()
    by_layer = {}
    for f in doc.get("features", []):
        p = f.get("properties") or {}
        by_layer.setdefault(p.get("layer"), []).append(f)
    for lid in set(by_layer) - set(layers):
        fails.append("%s: districts in the index for a layer the phrase file does not name" % lid)
    checked = 0
    for lid, spec in layers.items():
        src = SOURCES[lid]
        feats = by_layer.get(lid, [])
        # a district is unique per layer, or per county in a county-dispatched one
        keyed = [(f["properties"].get("county"), f["properties"]["id"]) for f in feats]
        if len(set(keyed)) != len(keyed):
            fails.append("%s: a district is listed twice" % lid)
        ids = [f["properties"]["id"] for f in feats]
        for f in feats:
            p = f["properties"]
            where = p.get("where") if src.get("app_layer") else None
            if src.get("app_layer") and where != COUNTY_NAME.get(p.get("county")):
                fails.append("%s %s: where %r is not that county's name" % (lid, p.get("county"), where))
            if p.get("name") != district_name(spec["name"], p["id"], where):
                fails.append("%s %s: name %r does not follow the phrase file" % (lid, p["id"], p.get("name")))
        if src.get("app_layer"):
            fails += check_app_layer(lid, feats, doc, index_html)
            continue
        if "file" in src:
            if src["file"] not in index_html:
                fails.append("%s: il/index.html no longer loads %s" % (lid, src["file"]))
            groups = group_districts(load_json(os.path.join(INSTANCE, "data", "app", src["file"]))["features"], src["key"])
            if set(ids) != set(groups):
                fails.append("%s: index has %s, boundary file has %s" % (lid, sorted(set(ids) - set(groups), key=int) or "no extras", sorted(set(groups) - set(ids), key=int) or "nothing missing"))
            for f in feats:
                d = f["properties"]["id"]
                if d not in groups:
                    continue
                x, y = f["geometry"]["coordinates"]
                if not point_in_rings(x, y, groups[d]):
                    fails.append("%s %s: its point %s is not inside the district it names" % (lid, d, [x, y]))
                want = bbox_of(groups[d])
                got = f["properties"].get("bbox") or []
                if len(got) != 4 or any(abs(a - b) > BBOX_TOLERANCE for a, b in zip(got, want)):
                    fails.append("%s %s: extent %s does not match its geometry %s" % (lid, d, got, [round(v, DIGITS) for v in want]))
                checked += 1
        else:
            if src["token"] not in index_html:
                fails.append("%s: il/index.html no longer loads %s, the source this index was built from — rebuild against the new one" % (lid, src["token"]))
            rec = (doc.get("live") or {}).get(lid) or {}
            if rec.get("source") != src["token"]:
                fails.append("%s: the index records source %r, the builder reads %r" % (lid, rec.get("source"), src["token"]))
            if sorted(ids, key=int) != rec.get("ids"):
                fails.append("%s: its districts disagree with the ids recorded at build" % lid)
            if src.get("ids") and sorted(ids, key=int) != src["ids"]:
                fails.append("%s: expected districts %s" % (lid, src["ids"]))
            if src.get("count") and len(ids) != src["count"]:
                fails.append("%s: %d districts, expected %d" % (lid, len(ids), src["count"]))
    if fails:
        print("build-district-search: FAIL")
        for f in fails:
            print("  - " + f)
        return 1
    live = ", ".join("%s (%d%s, fetched %s)" % (k, len(v["ids"]) if "ids" in v else sum(v["counties"].values()),
                                                "" if "ids" in v else " in %d counties" % len(v["counties"]), v["fetched"])
                     for k, v in sorted((doc.get("live") or {}).items()))
    print("build-district-search: OK — %d district(s) across %d layer(s); %d re-derived from shipped boundaries "
          "(inside and extent verified); live layers complete: %s" % (len(doc["features"]), len(layers), checked, live))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="offline CI gate; never writes")
    ap.add_argument("--county-dump", help="a dump_layer_districts.mjs output to use instead of running it")
    args = ap.parse_args()
    if args.check:
        sys.exit(check())
    doc = build(args.county_dump)
    write(doc)
    print("build-district-search: wrote %s (%d districts)" % (os.path.relpath(OUT, ROOT), len(doc["features"])))
    sys.exit(check())


if __name__ == "__main__":
    main()
