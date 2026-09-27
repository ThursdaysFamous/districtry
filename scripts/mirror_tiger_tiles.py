#!/usr/bin/env python3
"""Mirror the Census TIGERweb layers the apps fetch live into tile archives
(docs/OPTIMIZATION_PLAYBOOK.md §10, phase 6).

Sixteen polygon layers across four apps download a whole state from
tigerweb.geo.census.gov the first time they are switched on — Illinois's
county subdivisions alone are 14.5 MB — and ask that server about the reader's
point on every first click. Phase 5 put every layer whose shapes an app SHIPS
on vector tiles; these ship nothing, so they were left. This mirrors them:
it fetches each set exactly as the app does, builds a tile archive through
scripts/build_vector_tiles.py's own build and gate, commits the archive, and
records what it fetched. The app registers each layer with `tiles:` and then
answers the card and draws the map from the archive, like every other layer.

THE WHOLE SET STAYS LIVE AND IS NOT COMMITTED (the operator's choice,
2026-09-27). The census set is fetched from TIGERweb only when something needs
the whole file — the comparison stats screen, a pinned district's outlines,
the boundary-streets labels — or when the archive cannot be read. Committing a
simplified copy as well would have roughly doubled the size this adds.

WHAT IS FETCHED IS WHAT THE APP FETCHES. Each MIRRORS row carries the service,
layer index and outFields of one app's tigerStatewideLoader call, and --check
FAILS when that call in the app's index.html no longer names them, so the
archive cannot come to hold different fields or a different layer from the
one the card reads. The fetch asks for Esri JSON (f=json) at
geometryPrecision=5 with the app's STATE filter, and converts it with the
ENGINE'S OWN esriToGeoJSON, run in Node from engine/index.html/arcgis-loader.txt
rather than re-implemented: the server's GeoJSON export drops interior rings
(the engine refuses f=geojson for that reason), and a second converter is a
second opinion about which ground a district covers.

THE RECORD (tiger-mirror.json, beside layer-sources.json, excluded from the
deploy like it) holds, per layer, the query it made, when, how many features
came back, a SHA-256 of the canonical GeoJSON, and the SHA-256 of the archive
built from it. --check is offline and holds the tree to it:

  1. every MIRRORS row is registered with `tiles:` in its app, its archive
     exists, and the app's own loader call names the same service, layer and
     fields; every ZIP_MIRRORS row (phase 6b) the same, with the app's own
     bounding-box constant in place of the loader call;
  2. every archive's bytes hash to what the record says was built;
  3. nothing is recorded that MIRRORS does not list.

It cannot see the census data change; --refresh (weekly, update-tiger-tiles.yml)
refetches, rebuilds only a layer whose data hash moved, gates it, and opens a
pull request, which is how a new TIGER vintage reaches the apps.

    python3 scripts/mirror_tiger_tiles.py --refresh            # every layer
    python3 scripts/mirror_tiger_tiles.py --refresh --only il  # one app
    python3 scripts/mirror_tiger_tiles.py --check              # offline

--refresh needs curl (it goes through an HTTPS proxy where one is set), node,
tippecanoe and build_vector_tiles.py's Python packages.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
RECORD = os.path.join(REPO_ROOT, "tiger-mirror.json")
ARCGIS_BLOCK = os.path.join(REPO_ROOT, "engine", "index.html", "arcgis-loader.txt")
# esriRingsToParts assigns a hole to its shell with pointInRing, which lives here
PIP_BLOCK = os.path.join(REPO_ROOT, "engine", "index.html", "point-in-polygon.txt")
SERVICES = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
STATE_FIPS = {"il": "17", "ia": "19", "mi": "26", "wi": "55", "ny": "36", "ca": "06"}
# WHO THIS FETCHES AS, and it used to be nobody: the first version shelled out to
# curl with no -A, so the Census saw `curl/8.x` and nothing read robots.txt.
# Nothing was breached — measured 2026-09-27 as that client, the host's
# robots.txt path answers HTTP 200 with 189 bytes of an F5 "Request Rejected"
# page, which robots_policy reads as absent, allow-all — but every other fetcher
# here names itself and asks first, and user-agent-measurements.json already
# records this host serving a districtry token (verdict token-ok).
USER_AGENT = "districtry tiger-tile mirror (+https://districtry.com/)"

# (tag, layer id, service, layer index, outFields) — one app loader call each.
MIRRORS = [
    ("il", "county", "State_County", 1, "GEOID,NAME,BASENAME,STATE,LSADC"),
    ("il", "township", "Places_CouSub_ConCity_SubMCD", 1, "GEOID,NAME,BASENAME,STATE,COUNTY,LSADC"),
    ("il", "municipality", "Places_CouSub_ConCity_SubMCD", 4, "GEOID,NAME,BASENAME,STATE,LSADC"),
    ("il", "school-district-unified", "School", 0, "GEOID,NAME,STATE"),
    ("il", "school-district-secondary", "School", 1, "GEOID,NAME,STATE"),
    ("il", "school-district-elementary", "School", 2, "GEOID,NAME,STATE"),
    ("ia", "county-subdivision", "Places_CouSub_ConCity_SubMCD", 1, "GEOID,NAME,BASENAME,STATE,COUNTY,LSADC"),
    ("ia", "municipality", "Places_CouSub_ConCity_SubMCD", 4, "GEOID,NAME,BASENAME,STATE"),
    ("mi", "county-subdivision", "Places_CouSub_ConCity_SubMCD", 1, "GEOID,NAME,BASENAME,STATE,COUNTY,LSADC"),
    ("mi", "municipality", "Places_CouSub_ConCity_SubMCD", 4, "GEOID,NAME,BASENAME,STATE,LSADC"),
    ("mi", "school-district-unified", "School", 0, "GEOID,NAME,STATE,LOGRADE,HIGRADE"),
    ("mi", "school-district-elementary", "School", 2, "GEOID,NAME,STATE,LOGRADE,HIGRADE"),
    ("wi", "county-subdivision", "Places_CouSub_ConCity_SubMCD", 1, "GEOID,NAME,BASENAME,STATE,COUNTY,LSADC"),
    ("wi", "municipality", "Places_CouSub_ConCity_SubMCD", 4, "GEOID,NAME,BASENAME,STATE,LSADC"),
    ("wi", "school-district-secondary", "School", 1, "GEOID,NAME,STATE"),
    ("wi", "school-district-elementary", "School", 2, "GEOID,NAME,STATE"),
]

# THE ZIP LAYERS (phase 6b). TIGERweb's ZCTA layer has NO STATE field — a ZCTA
# can cross a state line — so every app fetches it by a bounding box instead,
# and each row carries that app's own box constant. --check fails when the
# constant in index.html stops matching, the same guarantee the rows above get
# from the loader call.
#
# FULL DETAIL, NOT THE APP'S WHOLE-SET SIMPLIFICATION (the operator's choice,
# 2026-09-27). The apps ask the server for maxAllowableOffset=0.0005 (~55 m)
# because the raw statewide set is ~40 MB; an archive holds the raw set in a
# fraction of that, so the mirror leaves the simplification out and the card,
# read from the tile, answers from the ZCTA as the Census drew it.
#
# PAGED, BECAUSE THE SERVER CANNOT ANSWER IT WHOLE: asked for Illinois's box at
# full detail in one response, TIGERweb returned `{"code": 500, "message":
# "Error performing query operation"}` for 2,184 ZCTAs (measured 2026-09-27),
# and answered 250 at a time in about 2 s and 5.4 MB a page. A run counts the
# box first and refuses a set that does not add up to that count.
ZIP_MIRRORS = [
    ("il", "zip-code", "IL_BBOX_ENVELOPE", (-91.6, 36.9, -87.0, 42.6)),
    ("ia", "zip-code", "IA_BBOX_ENVELOPE", (-96.69, 40.32, -90.09, 43.55)),
    ("mi", "zip-code", "MI_BBOX_ENVELOPE", (-90.42, 41.69, -82.12, 48.31)),
    ("wi", "zip-code", "WI_BBOX_ENVELOPE", (-93.09, 42.29, -86.04, 47.51)),
    ("ny", "nys-zip-code", "NY_ZCTA_ENVELOPE", (-79.77, 40.47, -71.77, 45.02)),
    ("ca", "zip-code", "SF_BBOX_ENVELOPE", (-122.62, 37.58, -122.28, 37.96)),
]
ZCTA_SERVICE, ZCTA_INDEX, ZCTA_FIELDS = "PUMA_TAD_TAZ_UGA_ZCTA", 11, "ZCTA5"
PAGE_SIZE = 250
# IN-STATE ONLY (the operator's choice, 2026-09-27). A box holding a state
# holds its neighbours' ZCTAs too — measured that day, 2,007 of the 3,833 in New
# York's box are New Jersey, Connecticut, Pennsylvania, Massachusetts and
# Vermont ZCTAs, and Michigan's reaches Chicago — and at full detail they were
# about half of New York's 15.6 MB archive. So a ZCTA is kept only where it
# overlaps the app's own state (the Census States layer, fetched from the same
# host) by more than this many square degrees, about 100 m² at these latitudes:
# a ZCTA that merely touches the state line shares an edge, not ground. What it
# costs is stated rather than implied: a reader who clicks OUTSIDE the state
# gets no ZIP card where the live layer answered one, and each app's emptyNote
# says so. THE FILTER changes no answer inside the state (measured 2026-09-27:
# every dropped ZCTA that touches the state holds 0.00 m2 of it). FULL DETAIL,
# the other half of the same change, DOES: the app's own loader asks for a
# maxAllowableOffset=0.0005 simplification and this archive is the Census's own
# drawing, so ground near an edge moves to the ZCTA the Census puts it in.
# Measured that day around Chicago, 0.49% of 3,514 km2 (218 ZCTAs) and 0.71% of
# 1,426 km2 (140 ZCTAs), the share depending on the box; every change is toward
# the Census's edges, and it is largest for small ZCTAs, where an edge's move is
# a bigger share of the whole (5.6% of 60208's area in the second box).
STATE_OVERLAP_MIN = 1e-8


def rows():
    """Every mirrored layer as one record, whichever way it is fetched."""
    out = [dict(tag=t, layer=l, service=s, index=i, fields=f, env_var=None, env=None)
           for t, l, s, i, f in MIRRORS]
    out += [dict(tag=t, layer=l, service=ZCTA_SERVICE, index=ZCTA_INDEX, fields=ZCTA_FIELDS,
                 env_var=v, env=e) for t, l, v, e in ZIP_MIRRORS]
    return out

def fail(msg):
    print("mirror-tiger-tiles: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def key(tag, layer):
    return "%s:%s" % (tag, layer)


def archive_path(tag, layer):
    return os.path.join(REPO_ROOT, tag, "data", "app", "tiles", layer + ".pmtiles")


def query_url(row):
    """The query recorded for a layer. A box row's is the query WITHOUT its
    page window; fetch_pages adds resultOffset/resultRecordCount per page."""
    if row["env"] is None:
        where = urllib.parse.quote("STATE='%s'" % STATE_FIPS[row["tag"]])
        return ("%s%s/MapServer/%d/query?where=%s&outFields=%s&outSR=4326&f=json&geometryPrecision=5"
                % (SERVICES, row["service"], row["index"], where, row["fields"]))
    xmin, ymin, xmax, ymax = row["env"]
    env = json.dumps({"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax}, separators=(",", ":"))
    return ("%s%s/MapServer/%d/query?where=%s&geometry=%s&geometryType=esriGeometryEnvelope"
            "&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=%s&outSR=4326&f=json"
            "&geometryPrecision=5&orderByFields=OBJECTID"
            % (SERVICES, row["service"], row["index"], urllib.parse.quote("1=1"),
               urllib.parse.quote(env), row["fields"]))


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_record():
    if not os.path.isfile(RECORD):
        return {}
    with open(RECORD, encoding="utf-8") as fh:
        return json.load(fh).get("layers", {})


def write_record(layers):
    doc = {"_comment": "Written by scripts/mirror_tiger_tiles.py --refresh; held to the tree "
                       "by its --check. One entry per Census TIGERweb layer mirrored into a tile archive.",
           "layers": {k: layers[k] for k in sorted(layers)}}
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=False)
        fh.write("\n")


# ---- the app's loader call, read from its index.html --------------------------

def loader_call_names(html, service, index, fields):
    """Does some tigerStatewideLoader call in this app name exactly this
    service, layer index and field list? The two spellings the apps use: il's
    tigerStatewideLoader("State_County", 1, "…") and the others'
    tigerStatewideLoader(TIGERWEB_SERVICES + "School/MapServer", 0, "…")."""
    pats = [
        r'tigerStatewideLoader\(\s*"%s"\s*,\s*%d\s*,\s*"%s"' % (re.escape(service), index, re.escape(fields)),
        r'tigerStatewideLoader\(\s*TIGERWEB_SERVICES\s*\+\s*"%s/MapServer"\s*,\s*%d\s*,\s*"%s"'
        % (re.escape(service), index, re.escape(fields)),
    ]
    return any(re.search(p, html) for p in pats)


def envelope_matches(html, row):
    """Does this app's index.html still declare the box the row fetches, and
    use it in a ZCTA query for layer 11's ZCTA5?"""
    m = re.search(r"var\s+%s\s*=\s*\{\s*xmin:\s*([-\d.]+),\s*ymin:\s*([-\d.]+),"
                  r"\s*xmax:\s*([-\d.]+),\s*ymax:\s*([-\d.]+)\s*\}" % re.escape(row["env_var"]), html)
    if not m or tuple(float(x) for x in m.groups()) != tuple(row["env"]):
        return False
    return ("JSON.stringify(%s)" % row["env_var"]) in html and "PUMA_TAD_TAZ_UGA_ZCTA" in html \
        and "outFields=ZCTA5" in html


def registered_tiles(html):
    return set(m for m in re.findall(r'\btiles:\s*"data/app/tiles/([^"/]+)\.pmtiles"', html))


# ---- fetch and convert ---------------------------------------------------------

CONVERT = r"""
const fs = require("fs");
const block = fs.readFileSync(process.argv[1], "utf8");
const start = block.indexOf("function esriSignedRingArea");
const end = block.indexOf("function fetchArcGISAsGeoJSON");
if (start < 0 || end < 0) { console.error("arcgis-loader block has moved"); process.exit(2); }
const pip = fs.readFileSync(process.argv[2], "utf8");
const esriToGeoJSON = new Function(pip + "\n" + block.slice(start, end) + "\nreturn esriToGeoJSON;")();
const payload = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const fc = esriToGeoJSON(payload, process.argv[4].split(","));
fs.writeFileSync(process.argv[5], JSON.stringify(fc));
"""


def fetch(url, dest):
    # --retry-all-errors: plain --retry skips a reset connection (curl exit 35),
    # which the Census server does to a runner often enough to fail a CI run.
    got = subprocess.run(["curl", "-sS", "--fail", "--retry", "3", "--retry-all-errors", "--retry-delay", "5",
                          "--max-time", "300", "-A", USER_AGENT, "-o", dest, url],
                         capture_output=True, text=True)
    if got.returncode != 0:
        raise RuntimeError("curl failed (%d): %s" % (got.returncode, got.stderr.strip()[-300:]))


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("error"):
        raise RuntimeError("TIGERweb answered an error: %s" % json.dumps(payload["error"])[:300])
    return payload


def fetch_pages(url, work):
    """A box row's set, PAGE_SIZE at a time, held to the server's own count."""
    count_path = os.path.join(work, "count.json")
    fetch(url.replace("&f=json", "&f=json&returnCountOnly=true"), count_path)
    want = read_json(count_path).get("count")
    if not isinstance(want, int) or want <= 0:
        raise RuntimeError("TIGERweb gave no count for the box")
    feats, shell, offset = [], None, 0
    while True:
        page = os.path.join(work, "page-%d.json" % offset)
        fetch("%s&resultOffset=%d&resultRecordCount=%d" % (url, offset, PAGE_SIZE), page)
        payload = read_json(page)
        got = payload.get("features") or []
        shell = shell or payload
        feats += got
        offset += len(got)
        if not got or not payload.get("exceededTransferLimit"):
            break
    if len(feats) != want:
        raise RuntimeError("the pages hold %d features and the server counts %d in the box" % (len(feats), want))
    shell = dict(shell)
    shell["features"] = feats
    shell.pop("exceededTransferLimit", None)
    return shell


_STATE_SHAPES = {}


def state_shape(tag, work):
    """The app's state as one shapely geometry, from TIGERweb's States layer,
    converted by the engine's own esriToGeoJSON like every set here."""
    if tag not in _STATE_SHAPES:
        from shapely.geometry import shape
        from shapely.ops import unary_union
        url = ("%sState_County/MapServer/0/query?where=%s&outFields=STATE&outSR=4326&f=json"
               "&geometryPrecision=5" % (SERVICES, urllib.parse.quote("STATE='%s'" % STATE_FIPS[tag])))
        raw, out = os.path.join(work, "state.json"), os.path.join(work, "state.geojson")
        fetch(url, raw)
        if not (read_json(raw).get("features")):
            raise RuntimeError("TIGERweb returned no outline for state %s" % STATE_FIPS[tag])
        got = subprocess.run(["node", "-e", CONVERT, ARCGIS_BLOCK, PIP_BLOCK, raw, "STATE", out],
                             capture_output=True, text=True)
        if got.returncode != 0:
            raise RuntimeError("the engine's esriToGeoJSON did not run on the state: %s" % got.stderr[:400])
        with open(out, encoding="utf-8") as fh:
            _STATE_SHAPES[tag] = unary_union([shape(f["geometry"]).buffer(0)
                                              for f in json.load(fh)["features"]])
    return _STATE_SHAPES[tag]


def keep_in_state(fc, tag, work):
    """Drop the features that do not overlap the app's own state."""
    from shapely.geometry import shape
    st = state_shape(tag, work)
    kept = [f for f in fc["features"]
            if f.get("geometry") and shape(f["geometry"]).buffer(0).intersection(st).area > STATE_OVERLAP_MIN]
    dropped = len(fc["features"]) - len(kept)
    fc["features"] = kept
    return dropped


def fetch_as_geojson(row, work):
    url = query_url(row)
    fields = row["fields"]
    raw = os.path.join(work, "esri.json")
    if row["env"] is None:
        fetch(url, raw)
        payload = read_json(raw)
        if payload.get("exceededTransferLimit"):
            raise RuntimeError("TIGERweb capped the response (exceededTransferLimit) — the set needs paging")
    else:
        payload = fetch_pages(url, work)
        with open(raw, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    feats = payload.get("features") or []
    if not feats:
        raise RuntimeError("TIGERweb returned no features")
    out = os.path.join(work, "set.geojson")
    got = subprocess.run(["node", "-e", CONVERT, ARCGIS_BLOCK, PIP_BLOCK, raw, fields, out],
                         capture_output=True, text=True)
    if got.returncode != 0:
        raise RuntimeError("the engine's esriToGeoJSON did not run: %s" % got.stderr[:600])
    with open(out, encoding="utf-8") as fh:
        fc = json.load(fh)
    # canonical form, so the hash moves only when the data does: features in
    # GEOID order (ZCTA5 for the ZIP layer, which has no GEOID in its fields;
    # the server's order is not promised), keys sorted
    sort_field = fields.split(",")[0]
    fc["features"].sort(key=lambda f: str((f.get("properties") or {}).get(sort_field)))
    row["_dropped"] = keep_in_state(fc, row["tag"], work) if row["env"] is not None else 0
    if not fc["features"]:
        raise RuntimeError("no feature overlaps the state")
    canon = json.dumps(fc, sort_keys=True, separators=(",", ":")).encode()
    with open(out, "wb") as fh:
        fh.write(canon)
    return url, out, len(fc["features"]), sha256_bytes(canon)


# ---- the service worker's cache --------------------------------------------------

def worksheet_path(tag):
    # Illinois's worksheet is the repo-root one, the others sit in their folder
    return os.path.join(REPO_ROOT, "metro-worksheet.json") if tag == "il" \
        else os.path.join(REPO_ROOT, tag, "metro-worksheet.json")


def bump_cache(tags):
    """A REPLACED archive reaches a returning visitor only through a new
    CACHE_NAME: the service worker serves every byte range under data/app/tiles/
    from its cache without asking again (engine sw-handlers), and
    scripts/check_cache_version.py fails a change that modifies an archive
    without one. So each app whose archive this run replaced gets its worksheet's
    cache_name moved on by one and its generated files rewritten. An archive
    that is NEW needs nothing — no visitor holds it."""
    for tag in sorted(tags):
        path = worksheet_path(tag)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        found = re.findall(r'"cache_name":\s*"([^"]*?)(\d+)"', text)
        if len(found) != 1:
            fail("%s: expected one cache_name ending in a number, found %d" % (path, len(found)))
        stem, n = found[0]
        new = "%s%d" % (stem, int(n) + 1)
        text = re.sub(r'("cache_name":\s*")[^"]*(")', lambda m: m.group(1) + new + m.group(2), text, count=1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("  cache  %-36s %s%s -> %s" % (tag, stem, n, new), flush=True)
    if tags:
        got = subprocess.run([sys.executable, os.path.join(HERE, "generate_metro_files.py")],
                             cwd=REPO_ROOT, capture_output=True, text=True)
        if got.returncode != 0:
            fail("generate_metro_files.py failed after the cache bump: %s" % (got.stderr or got.stdout)[-600:])


# ---- refresh -------------------------------------------------------------------

def refresh(only, force, n_points, seed):
    sys.path.insert(0, HERE)
    import build_vector_tiles as bvt
    bvt.need_tools()
    if not shutil.which("curl") or not shutil.which("node"):
        fail("needs curl and node on PATH")
    rec = load_record()
    todo = [r for r in rows() if not only or any(o in (r["tag"], key(r["tag"], r["layer"])) for o in only)]
    if not todo:
        fail("--only matched no mirrored layer")
    # robots.txt is read before the first fetch of the host, as the client that
    # fetches; a refusal stops the run and leaves every committed archive as it is.
    from scraper_common import require_robots_allowed
    why = require_robots_allowed(query_url(todo[0]), USER_AGENT, label="mirror-tiger-tiles")
    print("mirror-tiger-tiles: robots.txt — %s" % why, flush=True)
    changed, failed, replaced = [], [], set()
    tmp = tempfile.mkdtemp(prefix="tiger-mirror-")
    try:
        for row in todo:
            tag, layer = row["tag"], row["layer"]
            k = key(tag, layer)
            work = tempfile.mkdtemp(dir=tmp)
            try:
                url, path, n, digest = fetch_as_geojson(row, work)
            except RuntimeError as e:
                print("  FAIL  %-36s %s" % (k, e), flush=True)
                failed.append(k)
                continue
            old = rec.get(k) or {}
            arch = archive_path(tag, layer)
            if not force and old.get("data_sha256") == digest and os.path.isfile(arch) \
                    and sha256_file(arch) == old.get("archive_sha256"):
                print("  same  %-36s %d features, data unchanged" % (k, n), flush=True)
                continue
            feats, _, skipped = bvt.collect(tag, layer, [(None, path)])
            os.makedirs(os.path.dirname(arch), exist_ok=True)
            built = os.path.join(work, "out.pmtiles")
            bdir = tempfile.mkdtemp(dir=work)
            bvt.build(feats, built, bdir)
            problems, st = bvt.gate(tag, layer, feats, built, n_points, seed)
            if problems:
                print("  FAIL  %-36s the archive does not answer as the fetched set does:" % k)
                for p in problems:
                    print("          " + p)
                failed.append(k)
                continue
            if os.path.isfile(arch):
                replaced.add(tag)
            shutil.copyfile(built, arch)
            rec[k] = {
                "query": url,
                "fetched": datetime.date.today().isoformat(),
                "features": n,
                "data_sha256": digest,
                "archive_sha256": sha256_file(arch),
            }
            if row["env"] is not None:
                rec[k]["page_size"] = PAGE_SIZE
                rec[k]["in_state"] = STATE_FIPS[tag]
                rec[k]["out_of_state_dropped"] = row["_dropped"]
                with open(path, encoding="utf-8") as fh:
                    # one comma-joined string, so the record stays a page long
                    rec[k]["kept"] = ",".join(sorted(str(f["properties"][row["fields"]])
                                                     for f in json.load(fh)["features"]))
            changed.append(k)
            if row.get("_dropped"):
                print("        %-36s %d out-of-state ZCTA(s) dropped" % (k, row["_dropped"]), flush=True)
            print("  %-4s  %-36s %d features%s, %.1f MB set -> %.2f MB archive; %d/%d points "
                  "under %g m differ, %d/%d beyond"
                  % ("new" if not old else "moved" if old.get("data_sha256") != digest else "built", k, n,
                     " (%d non-polygon skipped)" % skipped if skipped else "",
                     os.path.getsize(path) / 1e6, os.path.getsize(arch) / 1e6,
                     st["near_bad"], st["near"], bvt.EDGE_TOLERANCE_M, st["far_bad"], st["far"]),
                  flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if changed:
        write_record(rec)
    bump_cache(replaced)
    if failed:
        fail("%d layer(s) not mirrored: %s — nothing was written for them" % (len(failed), ", ".join(failed)))
    print("mirror-tiger-tiles: OK — %d of %d layer(s) rebuilt" % (len(changed), len(todo)))


# ---- check ---------------------------------------------------------------------

def check():
    rec = load_record()
    problems = []
    listed = set()
    html_by_tag = {}
    all_rows = rows()
    for row in all_rows:
        tag, layer, service, index, fields = (row["tag"], row["layer"], row["service"],
                                              row["index"], row["fields"])
        k = key(tag, layer)
        if k in listed:
            problems.append("%s is listed twice in MIRRORS" % k)
        listed.add(k)
        if tag not in html_by_tag:
            with open(os.path.join(REPO_ROOT, tag, "index.html"), encoding="utf-8") as fh:
                html_by_tag[tag] = fh.read()
        html = html_by_tag[tag]
        if layer not in registered_tiles(html):
            problems.append("%s is mirrored but %s/index.html does not register it with tiles:" % (k, tag))
        if row["env"] is not None:
            if not envelope_matches(html, row):
                problems.append("%s: %s/index.html no longer declares %s = %s for its ZCTA query — "
                                "the archive would cover a different box from the one the app "
                                "fetches; update ZIP_MIRRORS and --refresh" % (k, tag, row["env_var"], row["env"]))
        elif not loader_call_names(html, service, index, fields):
            problems.append("%s: no tigerStatewideLoader call in %s/index.html names %s layer %d "
                            "with fields %s — the archive would hold something the card does not "
                            "read; update MIRRORS and --refresh" % (k, tag, service, index, fields))
        r = rec.get(k)
        arch = archive_path(tag, layer)
        if not r:
            problems.append("%s has no entry in tiger-mirror.json — run --refresh --only %s" % (k, k))
            continue
        if r.get("query") != query_url(row):
            problems.append("%s was fetched with %s, which is not the query MIRRORS makes today — "
                            "--refresh it" % (k, r.get("query")))
        if not os.path.isfile(arch):
            problems.append("%s: %s is missing" % (k, os.path.relpath(arch, REPO_ROOT)))
        elif sha256_file(arch) != r.get("archive_sha256"):
            problems.append("%s: the archive is not the one --refresh built and recorded — rebuild "
                            "it with --refresh --only %s rather than by hand" % (k, k))
    for k in rec:
        if k not in listed:
            problems.append("tiger-mirror.json records %s, which MIRRORS no longer lists" % k)
    if problems:
        fail("\n  " + "\n  ".join(problems))
    oldest = min((r["fetched"] for r in rec.values()), default=None)
    print("mirror-tiger-tiles: OK — %d mirrored layer(s) registered, their loaders unchanged and "
          "their archives the ones recorded (oldest fetch %s)" % (len(all_rows), oldest))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--refresh", action="store_true",
                   help="refetch, and rebuild and gate each layer whose data moved")
    g.add_argument("--check", action="store_true", help="offline: hold the tree to the record")
    ap.add_argument("--only", action="append", default=[], help="an app tag or tag:layer; repeatable")
    ap.add_argument("--force", action="store_true", help="rebuild even when the data hash is unchanged")
    ap.add_argument("--points", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    if args.check:
        check()
    else:
        refresh(args.only, args.force, args.points, args.seed)


if __name__ == "__main__":
    main()
