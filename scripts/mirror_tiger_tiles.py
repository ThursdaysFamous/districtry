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
     fields;
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
STATE_FIPS = {"il": "17", "ia": "19", "mi": "26", "wi": "55"}

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

def fail(msg):
    print("mirror-tiger-tiles: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def key(tag, layer):
    return "%s:%s" % (tag, layer)


def archive_path(tag, layer):
    return os.path.join(REPO_ROOT, tag, "data", "app", "tiles", layer + ".pmtiles")


def query_url(tag, service, index, fields):
    where = urllib.parse.quote("STATE='%s'" % STATE_FIPS[tag])
    return ("%s%s/MapServer/%d/query?where=%s&outFields=%s&outSR=4326&f=json&geometryPrecision=5"
            % (SERVICES, service, index, where, fields))


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
    got = subprocess.run(["curl", "-sS", "--fail", "--retry", "3", "--retry-delay", "5",
                          "--max-time", "300", "-o", dest, url], capture_output=True, text=True)
    if got.returncode != 0:
        raise RuntimeError("curl failed (%d): %s" % (got.returncode, got.stderr.strip()[-300:]))


def fetch_as_geojson(tag, service, index, fields, work):
    url = query_url(tag, service, index, fields)
    raw = os.path.join(work, "esri.json")
    fetch(url, raw)
    with open(raw, encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("error"):
        raise RuntimeError("TIGERweb answered an error: %s" % json.dumps(payload["error"])[:300])
    if payload.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb capped the response (exceededTransferLimit) — the set needs paging")
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
    # GEOID order (the server's order is not promised), keys sorted
    fc["features"].sort(key=lambda f: str((f.get("properties") or {}).get("GEOID")))
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
    rows = [r for r in MIRRORS if not only or any(o in (r[0], key(r[0], r[1])) for o in only)]
    if not rows:
        fail("--only matched no mirrored layer")
    changed, failed, replaced = [], [], set()
    tmp = tempfile.mkdtemp(prefix="tiger-mirror-")
    try:
        for tag, layer, service, index, fields in rows:
            k = key(tag, layer)
            work = tempfile.mkdtemp(dir=tmp)
            try:
                url, path, n, digest = fetch_as_geojson(tag, service, index, fields, work)
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
            changed.append(k)
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
    print("mirror-tiger-tiles: OK — %d of %d layer(s) rebuilt" % (len(changed), len(rows)))


# ---- check ---------------------------------------------------------------------

def check():
    rec = load_record()
    problems = []
    listed = set()
    html_by_tag = {}
    for tag, layer, service, index, fields in MIRRORS:
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
        if not loader_call_names(html, service, index, fields):
            problems.append("%s: no tigerStatewideLoader call in %s/index.html names %s layer %d "
                            "with fields %s — the archive would hold something the card does not "
                            "read; update MIRRORS and --refresh" % (k, tag, service, index, fields))
        r = rec.get(k)
        arch = archive_path(tag, layer)
        if not r:
            problems.append("%s has no entry in tiger-mirror.json — run --refresh --only %s" % (k, k))
            continue
        if r.get("query") != query_url(tag, service, index, fields):
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
          "their archives the ones recorded (oldest fetch %s)" % (len(MIRRORS), oldest))


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
