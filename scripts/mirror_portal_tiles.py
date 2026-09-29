#!/usr/bin/env python3
"""Mirror the city open-data portal layers the apps fetch live into tile
archives (docs/OPTIMIZATION_PLAYBOOK.md §10, phase 6c).

Seventeen polygon layers across Chicago, New York City and San Francisco
download a whole boundary set from a Socrata portal the first time they are
switched on — Chicago's 1,291 ward precincts are 5.2 MB, New York's 770
elementary zones 2.4 MB — and several of them ask that portal about the
reader's point on every first click. Phase 5 put every layer whose shapes an
app SHIPS on vector tiles and phases 6a and 6b did the same for the Census
TIGERweb and ZIP layers; these three portals were what was left live. This
mirrors them the way scripts/mirror_tiger_tiles.py mirrors the census: it
fetches each set exactly as the app does, builds a tile archive through
scripts/build_vector_tiles.py's own build and gate, commits the archive, and
records what it fetched.

THE WHOLE SET STAYS LIVE AND IS NOT COMMITTED, as in phase 6a: the portal is
still what answers the comparison stats screen, a pinned district's outlines
and the boundary-street labels, and what the app falls back to when an
archive cannot be read.

WHAT IS FETCHED IS WHAT THE APP FETCHES, and that is not a resemblance. The
three routes are READ OUT OF engine/index.html/socrata-loader.txt — the same
block the app runs — so the page size, the route order and the route shapes
have one writer; engine_routes() FAILS rather than guessing when that block's
route list stops parsing. SOCRATA_HOST and SOCRATA_APP_TOKEN come from the
app's own index.html. A row's fetch walks the routes in the engine's order
and takes the first response that passes the engine's own test, which is why
San Francisco's election precincts (jg6x-23ig) mirror correctly: route 0
answers 200 with every geometry stripped to null, and the walk falls through
exactly as it does in the browser. The archive is then held to a STRICTER
test than the app applies — every feature must carry geometry — because a
committed archive that silently holds fewer districts than the portal
publishes is the ward-precinct defect in a different costume.

FOUR LAYERS ARE DELIBERATELY NOT HERE, and the reason is one property of the
tile path rather than four separate problems. A tile carries the FILE'S OWN
properties and nothing the app adds after its fetch, and the card, the hover
name and the drawn canvas all read them, so a layer whose loader derives or
stamps a property would print the underlying value everywhere:

  il ssa               stamps each area's service provider, address, phone
                       and url from data/app's provider roster
  ny neighborhood      derives a readable NTA type label from `ntatype`
  ny school-district   normalizes schooldist ("15.0" -> "15"), which the CEC
  ny cec               join and both cards read

(il ward is out for a different reason: it is a county-dispatched layer whose
Chicago entry is one of four sources, each normalizing its own field names,
so it belongs to the county-archive shape of phase 5b rather than here.)
Giving the general tile path a decorate hook is its own change, and it would
still leave the hover name and the canvas reading the raw value, so nothing
is half-done here: those four keep fetching their portal exactly as before.

THE RECORD (portal-mirror.json, beside tiger-mirror.json, excluded from the
deploy like it) holds, per layer, the route it fetched and which of the three
answered, when, how many features came back, a SHA-256 of the canonical
GeoJSON and the SHA-256 of the archive built from it. --check is offline and
holds the tree to it:

  1. every PORTAL_MIRRORS row is registered with `tiles:` in its app, its
     archive exists, and that app's index.html still names the dataset id and
     the portal host the archive was built from;
  2. the query recorded is the one the engine's own route list builds today;
  3. every archive's bytes hash to what the record says was built;
  4. nothing is recorded that PORTAL_MIRRORS does not list.

It cannot see a portal's data change; --refresh (weekly,
update-portal-tiles.yml) refetches, rebuilds only a layer whose data hash
moved, gates it, and opens a pull request.

    python3 scripts/mirror_portal_tiles.py --refresh            # every layer
    python3 scripts/mirror_portal_tiles.py --refresh --only ny  # one app
    python3 scripts/mirror_portal_tiles.py --check              # offline

--refresh needs curl (it goes through an HTTPS proxy where one is set),
tippecanoe and build_vector_tiles.py's Python packages.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import math
import sys
import tempfile
import time
import urllib.parse

from tile_mirror_common import (archive_path, key, registered_tiles, sha256_bytes,
                                sha256_file)
import tile_mirror_common

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
RECORD = os.path.join(REPO_ROOT, "portal-mirror.json")
SOCRATA_BLOCK = os.path.join(REPO_ROOT, "engine", "index.html", "socrata-loader.txt")
USER_AGENT = "districtry portal-tile mirror (+https://districtry.com/)"

# (tag, layer id, Socrata dataset id). The layer id is also the archive's
# name, which is what ties a row to the app's own `tiles:` registration.
PORTAL_MIRRORS = [
    ("il", "community-area", "igwz-8jzy"),
    ("il", "ward-precinct", "i8fv-xe4b"),
    ("il", "cps-elementary", "x72b-38qv"),
    ("il", "cps-high", "xg7c-d8rm"),
    ("il", "cps-middle", "fyff-53xy"),
    ("il", "cps-network", "pnta-kuqa"),
    ("il", "cps-hs-network", "aupu-jt2g"),
    ("ny", "zip-code", "pri4-ifjk"),
    ("ny", "police-precinct", "y76i-bdw7"),
    ("ny", "police-sector", "5rqd-h5ci"),
    ("ny", "council", "872g-cjhh"),
    ("ny", "community-district", "5crt-au7u"),
    ("ny", "es-zone", "cmjf-yawu"),
    ("ny", "ms-zone", "t26j-jbq7"),
    ("ny", "hs-zone", "ruu9-egea"),
    ("ca", "election-precinct", "jg6x-23ig"),
    ("ca", "elementary-attendance-area", "e6tr-sxwg"),
]

# Every one of these portals states Crawl-delay: 1 for the group that binds
# this client (scripts/robots_policy.py); honoured between every request.
DEFAULT_CRAWL_DELAY = 1.0


def rows():
    return [{"tag": t, "layer": l, "dataset": d} for t, l, d in PORTAL_MIRRORS]


def fail(msg):
    print("mirror-portal-tiles: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


# ---- the engine's own route list ------------------------------------------------

_ROUTES = None


def engine_routes():
    """The three route templates and the page size, read from the engine block
    the app runs rather than restated here. Returns a list of Python format
    strings taking {host}, {ds} and {maxrows}.

    Each JS route is a concatenation of string literals and three known names,
    so it converts one term at a time; anything else FAILS, because a route
    this cannot read is a route the mirror would be guessing at."""
    global _ROUTES
    if _ROUTES is not None:
        return _ROUTES
    with open(SOCRATA_BLOCK, encoding="utf-8") as fh:
        block = fh.read()
    m = re.search(r"var\s+SOCRATA_PAGE_MAX\s*=\s*(\d+)\s*;", block)
    if not m:
        fail("%s no longer declares SOCRATA_PAGE_MAX" % os.path.relpath(SOCRATA_BLOCK, REPO_ROOT))
    page_max = int(m.group(1))
    m = re.search(r"function\s+socrataRouteUrls\s*\(\s*datasetId\s*\)\s*\{\s*return\s*\[(.*?)\]\s*"
                  r"\.map\(withAppToken\)\s*;", block, re.S)
    if not m:
        fail("%s: socrataRouteUrls no longer reads as a list of routes mapped through withAppToken — "
             "read the block and update engine_routes()" % os.path.relpath(SOCRATA_BLOCK, REPO_ROOT))
    names = {"SOCRATA_HOST": "{host}", "datasetId": "{ds}", "SOCRATA_PAGE_MAX": "{maxrows}"}
    routes = []
    for line in [x.strip() for x in m.group(1).split(",\n")]:
        line = line.strip().rstrip(",").strip()
        if not line:
            continue
        out = ""
        for term in [t.strip() for t in line.split("+")]:
            if len(term) >= 2 and term[0] == '"' and term[-1] == '"':
                out += term[1:-1].replace("{", "{{").replace("}", "}}")
            elif term in names:
                out += names[term]
            else:
                fail("socrataRouteUrls route %r holds %r, which this mirror cannot read — "
                     "read the engine block and update engine_routes()" % (line, term))
        routes.append(out)
    if len(routes) < 2:
        fail("socrataRouteUrls parsed to %d route(s); the engine has always had three" % len(routes))
    _ROUTES = (routes, page_max)
    return _ROUTES


def route_urls(host, dataset):
    """The routes as the app builds them, WITHOUT the app token: the token is
    appended by withAppToken and is already in the app's index.html, and a
    second copy of it in the record is a second place for it to go stale."""
    routes, page_max = engine_routes()
    return [r.format(host=host, ds=dataset, maxrows=page_max) for r in routes]


# ---- the app's own portal ---------------------------------------------------------

_APP_HTML = {}


def app_html(tag):
    if tag not in _APP_HTML:
        with open(os.path.join(REPO_ROOT, tag, "index.html"), encoding="utf-8") as fh:
            _APP_HTML[tag] = fh.read()
    return _APP_HTML[tag]


def app_portal(tag):
    """(host, app token) as this app declares them."""
    html = app_html(tag)
    m = re.search(r'var\s+SOCRATA_HOST\s*=\s*"([^"]+)"\s*;', html)
    if not m:
        fail("%s/index.html declares no SOCRATA_HOST" % tag)
    host = m.group(1)
    t = re.search(r'var\s+SOCRATA_APP_TOKEN\s*=\s*"([^"]*)"\s*;', html)
    return host, (t.group(1) if t else "")


def with_app_token(url, token):
    if not token:
        return url
    return url + ("?" if "?" not in url else "&") + "$$app_token=" + token


# ---- the record --------------------------------------------------------------------

def load_record():
    if not os.path.isfile(RECORD):
        return {}
    with open(RECORD, encoding="utf-8") as fh:
        return json.load(fh).get("layers", {})


def write_record(layers):
    doc = {"_comment": "Written by scripts/mirror_portal_tiles.py --refresh; held to the tree by its "
                       "--check. One entry per city open-data portal layer mirrored into a tile "
                       "archive. `query` is the route that answered, with the app token left off.",
           "layers": {k: layers[k] for k in sorted(layers)}}
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=False)
        fh.write("\n")


# ---- fetch ---------------------------------------------------------------------------

_LAST_FETCH = {}


def _pace(host, delay):
    wait = delay - (time.monotonic() - _LAST_FETCH.get(host, -1e9))
    if wait > 0:
        time.sleep(wait)


def _host(url):
    return urllib.parse.urlsplit(url).netloc


def resolve(url, allow, delay):
    """The url this route really serves, with EVERY host in the redirect chain
    gated before it is fetched.

    San Francisco's portal moved: data.sfgov.org answers 301 to data.sf.gov,
    and the app's fetch() follows it as any browser does. So the mirror
    follows it too — one hop at a time, reading only the 301's own target
    (never the stub as though it were the document), so a host that appears in
    the chain is asked for its robots.txt BEFORE anything is fetched from it.
    A chain that reaches a host this client is refused stops the row."""
    seen = []
    for _ in range(5):
        allow(url)
        _pace(_host(url), delay)
        got = subprocess.run(["curl", "-sS", "--max-redirs", "0", "--max-time", "60",
                              "-A", USER_AGENT, "-o", os.devnull, "-w", "%{redirect_url}", url],
                             capture_output=True, text=True)
        _LAST_FETCH[_host(url)] = time.monotonic()
        if got.returncode != 0:
            raise RuntimeError("curl could not reach %s (%d): %s"
                               % (url, got.returncode, got.stderr.strip()[-200:]))
        nxt = got.stdout.strip()
        if not nxt:
            return url
        if nxt in seen:
            raise RuntimeError("redirect loop at %s" % nxt)
        seen.append(nxt)
        url = nxt
    raise RuntimeError("more than 5 redirects from %s" % url)


def fetch(url, dest, delay):
    # the portal's own Crawl-delay, per host, across every route and row
    _pace(_host(url), delay)
    # --retry-all-errors: plain --retry skips a reset connection (curl exit 35),
    # which a portal behind a CDN does to a runner often enough to fail a run.
    # -L because the app's own fetch() follows redirects; resolve() has already
    # gated every host the chain reaches.
    got = subprocess.run(["curl", "-sS", "--fail", "-L", "--max-redirs", "5",
                          "--retry", "3", "--retry-all-errors",
                          "--retry-delay", "5", "--max-time", "600", "-A", USER_AGENT,
                          "-o", dest, url], capture_output=True, text=True)
    _LAST_FETCH[_host(url)] = time.monotonic()
    if got.returncode != 0:
        raise RuntimeError("curl failed (%d): %s" % (got.returncode, got.stderr.strip()[-300:]))


def usable_whole(fc, page_max):
    """The engine's own hasWholeUsableGeometry: at least one real geometry, and
    not a response that exactly fills the page (which would be indistinguishable
    from a complete set)."""
    feats = (fc or {}).get("features")
    if not isinstance(feats, list) or not feats:
        return False
    if len(feats) >= page_max:
        return False
    return any(f.get("geometry") for f in feats)


def fetch_as_geojson(row, work, delay, allow):
    """Walk the engine's routes in the engine's order, take the first that
    passes its test, and hold it to the stricter one a committed archive needs."""
    tag, dataset = row["tag"], row["dataset"]
    host, token = app_portal(tag)
    _, page_max = engine_routes()
    urls = route_urls(host, dataset)
    why = []
    for i, url in enumerate(urls):
        raw = os.path.join(work, "route-%d.geojson" % i)
        try:
            fetch(resolve(with_app_token(url, token), allow, delay), raw, delay)
            with open(raw, encoding="utf-8") as fh:
                fc = json.load(fh)
        except (RuntimeError, ValueError) as e:
            why.append("route %d: %s" % (i, str(e)[:160]))
            continue
        if not usable_whole(fc, page_max):
            feats = (fc or {}).get("features") or []
            why.append("route %d: %d feature(s), %d with geometry"
                       % (i, len(feats), sum(1 for f in feats if f.get("geometry"))))
            continue
        # STRICTER than the app: every feature must carry geometry, or the
        # archive would publish fewer districts than the portal does.
        missing = [n for n, f in enumerate(fc["features"]) if not f.get("geometry")]
        if missing:
            raise RuntimeError("route %d returned %d of %d features with null geometry — the portal is "
                               "not serving this set whole; nothing was written"
                               % (i, len(missing), len(fc["features"])))
        # canonical form, so the hash moves only when the data does: each
        # feature serialized with its keys sorted, the features in the order
        # those strings sort in (a portal promises no row order)
        feats = sorted(json.dumps(f, sort_keys=True, separators=(",", ":")) for f in fc["features"])
        canon = ('{"type":"FeatureCollection","features":[' + ",".join(feats) + "]}").encode()
        out = os.path.join(work, "set.geojson")
        with open(out, "wb") as fh:
            fh.write(canon)
        return url, i, out, len(feats), sha256_bytes(canon)
    raise RuntimeError("no route served %s whole (%s)" % (dataset, "; ".join(why)))


def bump_cache(tags):
    tile_mirror_common.bump_cache(tags, fail)


# ---- fragments too small to draw at the deepest zoom the fleet ships -----------
#
# A feature whose whole extent is under about two tile units at zoom 12 cannot
# survive quantisation to the tile grid, `--no-tiny-polygon-reduction` and all:
# every vertex rounds into one cell and the polygon encloses nothing. The gate
# in build_vector_tiles.py is right to report it — a district missing from the
# tile under a point inside it is a card with no answer — so it is DECLARED
# here rather than forgiven by loosening the gate for every layer.
#
# Both entries are the SAME digitisation artefact in two DOE layers drawn from
# one base fabric: a 1.7 m2 and a 1.1 m2 fragment about a metre apart at
# 40.7564, -73.9473 in Queens, each the only feature its own file answers at
# its own interior point. So a reader who clicked inside one would be told no
# zoned school where the file names one, over ground the size of a doormat.
# That is the whole cost, and it is stated rather than smoothed.
#
# EVERY ENTRY IS RE-VERIFIED ON EVERY RUN and FAILS when it stops describing
# the set: the feature must still be there, still be under MAX_UNDRAWABLE_M2,
# and the gate must still report exactly it — so a redrawn zone retires the
# entry rather than leaving a licence behind. The forgiven problem string is
# RECONSTRUCTED from the gate's own wording, never pattern-matched, so a change
# to how the gate words this turns the build red and gets the gate re-read.
MAX_UNDRAWABLE_M2 = 5.0

ACCEPTED_TILE_DROPS = {
    ("ny", "es-zone"): [{"key": "dbn", "value": "30Q111", "m2": 1.7,
                         "at": [40.756365, -73.947341], "answer": "30Q111",
                         "why": "a 1.7 m2 fragment of zone 30Q111 about a metre from ms-zone's "
                                "own, at a shared node in the DOE fabric; 5 other parts of the "
                                "same zone draw normally",
                         "date": "2026-09-29"}],
    ("ny", "ms-zone"): [{"key": "dbn", "value": "30Q204", "m2": 1.1,
                         "at": [40.756369, -73.947348], "answer": "30Q204",
                         "why": "the same artefact one layer over: a 1.1 m2 fragment of zone "
                                "30Q204; 6 other parts of the same zone draw normally",
                         "date": "2026-09-29"}],
}
EARTH_M_PER_DEG = 111320.0


def undrawable(tag, layer, feats, problems, bvt):
    """The gate's problems with the declared fragments taken out, or None when
    a declaration no longer describes the set (which FAILS the row).

    Returns (remaining problems, the drops as the record will carry them)."""
    want = ACCEPTED_TILE_DROPS.get((tag, layer)) or []
    if not want:
        return problems, []
    from shapely.geometry import shape
    forgiven, drops, bad = {}, [], []
    for entry in want:
        hits = [j for j, f in enumerate(feats)
                if str((f.get("_src") or f["properties"]).get(entry["key"])) == entry["value"]]
        small = []
        for j in hits:
            g = shape(feats[j]["tile_geometry"])
            pt = g.point_on_surface()
            m2 = g.area * EARTH_M_PER_DEG ** 2 * math.cos(math.radians(pt.y))
            if m2 <= MAX_UNDRAWABLE_M2:
                small.append((j, m2, pt))
        if len(small) != 1:
            bad.append("%s=%s: %d fragment(s) under %g m2, not the 1 declared — re-measure this "
                       "declaration" % (entry["key"], entry["value"], len(small), MAX_UNDRAWABLE_M2))
            continue
        j, m2, pt = small[0]
        # reconstructed from the gate's own wording, so a reworded gate fails here
        forgiven[j] = ("feature %d (%s) is not in the deepest tile under a point inside it"
                       % (j, bvt.label(feats[j])))
        drops.append({entry["key"]: entry["value"], "m2": round(m2, 2),
                      "at": [round(pt.y, 6), round(pt.x, 6)], "answer": entry["answer"],
                      "why": entry["why"], "declared": entry["date"]})
    if bad:
        raise RuntimeError("; ".join(bad))
    left = [p for p in problems if p not in forgiven.values()]
    unused = [t for t in forgiven.values() if t not in problems]
    if unused:
        raise RuntimeError("the tile gate no longer reports %s — the fragment draws now, so retire "
                           "its ACCEPTED_TILE_DROPS entry" % "; ".join(unused))
    return left, drops


# ---- refresh ---------------------------------------------------------------------

def refresh(only, force, n_points, seed):
    sys.path.insert(0, HERE)
    import build_vector_tiles as bvt
    bvt.need_tools()
    if not shutil.which("curl"):
        fail("needs curl on PATH")
    rec = load_record()
    todo = [r for r in rows() if not only or any(o in (r["tag"], key(r["tag"], r["layer"])) for o in only)]
    if not todo:
        fail("--only matched no mirrored layer")
    # robots.txt is read before the first fetch of each host, as the client
    # that fetches, and again for any host a redirect leads to (resolve); a
    # refusal stops the run and leaves every committed archive as it is.
    from scraper_common import require_robots_allowed
    import robots_policy
    # no session: RobotsGate reads robots.txt on the stdlib client when given
    # none, which keeps `requests` out of this script's import closure — the
    # fetches themselves go through curl, and vector-tiles.yml runs --check
    # without installing it (scripts/validate_workflow_deps.py)
    gate = robots_policy.RobotsGate(None, USER_AGENT)
    delays = {}

    def allow(url):
        host = _host(url)
        if host not in delays:
            # asked for, and reported, WITHOUT the app token: robots.txt matches
            # on the path, and a token echoed into a build log is a second copy
            # of something that already lives in the app's index.html
            bare = re.sub(r"\?&", "?", re.sub(r"[?&]\$\$app_token=[^&]*", "", url))
            why = require_robots_allowed(bare, USER_AGENT, label="mirror-portal-tiles")
            delays[host] = gate.crawl_delay(bare) or DEFAULT_CRAWL_DELAY
            print("mirror-portal-tiles: robots.txt — %s — %s (crawl delay %gs)"
                  % (host, why, delays[host]), flush=True)
        return delays[host]

    changed, failed, replaced = [], [], set()
    tmp = tempfile.mkdtemp(prefix="portal-mirror-")
    try:
        for row in todo:
            tag, layer = row["tag"], row["layer"]
            k = key(tag, layer)
            work = tempfile.mkdtemp(dir=tmp)
            try:
                url, route, path, n, digest = fetch_as_geojson(row, work, DEFAULT_CRAWL_DELAY, allow)
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
            if skipped:
                print("  FAIL  %-36s %d feature(s) are not polygons — a portal set this mirror "
                      "tiles must be whole" % (k, skipped), flush=True)
                failed.append(k)
                continue
            os.makedirs(os.path.dirname(arch), exist_ok=True)
            built = os.path.join(work, "out.pmtiles")
            bdir = tempfile.mkdtemp(dir=work)
            bvt.build(feats, built, bdir)
            problems, st = bvt.gate(tag, layer, feats, built, n_points, seed)
            try:
                problems, drops = undrawable(tag, layer, feats, problems, bvt)
            except RuntimeError as e:
                print("  FAIL  %-36s %s" % (k, e), flush=True)
                failed.append(k)
                continue
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
                "dataset": row["dataset"],
                "query": url,
                "route": route,
                "fetched": datetime.date.today().isoformat(),
                "features": n,
                "data_sha256": digest,
                "archive_sha256": sha256_file(arch),
            }
            if drops:
                rec[k]["undrawable"] = drops
            changed.append(k)
            print("  %-5s %-36s %d features via route %d, %.1f MB set -> %.2f MB archive; "
                  "%d/%d points under %g m differ, %d/%d beyond"
                  % ("new" if not old else "moved" if old.get("data_sha256") != digest else "built",
                     k, n, route, os.path.getsize(path) / 1e6, os.path.getsize(arch) / 1e6,
                     st["near_bad"], st["near"], bvt.EDGE_TOLERANCE_M, st["far_bad"], st["far"]),
                  flush=True)
            for d in drops:
                print("        %-36s %g m2 fragment not drawn at zoom %d; %s is the answer it "
                      "costs at %s" % (k, d["m2"], bvt.MAX_ZOOM, d["answer"], d["at"]), flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if changed:
        write_record(rec)
    bump_cache(replaced)
    if failed:
        fail("%d layer(s) not mirrored: %s — nothing was written for them"
             % (len(failed), ", ".join(failed)))
    print("mirror-portal-tiles: OK — %d of %d layer(s) rebuilt" % (len(changed), len(todo)))


# ---- check -----------------------------------------------------------------------

def check():
    rec = load_record()
    problems, listed = [], set()
    all_rows = rows()
    for row in all_rows:
        tag, layer, dataset = row["tag"], row["layer"], row["dataset"]
        k = key(tag, layer)
        if k in listed:
            problems.append("%s is listed twice in PORTAL_MIRRORS" % k)
        listed.add(k)
        html = app_html(tag)
        if layer not in registered_tiles(html):
            problems.append("%s is mirrored but %s/index.html does not register it with tiles:" % (k, tag))
        if ('"%s"' % dataset) not in html:
            problems.append("%s: %s/index.html no longer names dataset %s — the archive holds a set the "
                            "card does not read; update PORTAL_MIRRORS and --refresh" % (k, tag, dataset))
        host, _ = app_portal(tag)
        r = rec.get(k)
        arch = archive_path(tag, layer)
        if not r:
            problems.append("%s has no entry in portal-mirror.json — run --refresh --only %s" % (k, k))
            continue
        if r.get("query") not in route_urls(host, dataset):
            problems.append("%s was fetched with %s, which is not one of the routes the engine builds for "
                            "%s today — --refresh it" % (k, r.get("query"), host))
        if not os.path.isfile(arch):
            problems.append("%s: %s is missing" % (k, os.path.relpath(arch, REPO_ROOT)))
        elif sha256_file(arch) != r.get("archive_sha256"):
            problems.append("%s: the archive is not the one --refresh built and recorded — rebuild it "
                            "with --refresh --only %s rather than by hand" % (k, k))
    for k in rec:
        if k not in listed:
            problems.append("portal-mirror.json records %s, which PORTAL_MIRRORS no longer lists" % k)
    if problems:
        fail("\n  " + "\n  ".join(problems))
    oldest = min((r["fetched"] for r in rec.values()), default=None)
    print("mirror-portal-tiles: OK — %d mirrored layer(s) registered, their datasets still read by "
          "their apps and their archives the ones recorded (oldest fetch %s)" % (len(all_rows), oldest))


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
