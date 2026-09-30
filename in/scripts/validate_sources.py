#!/usr/bin/env python3
"""
Source freshness gate for the app's data layers.

Why this exists: unlike the roster scrapers (which re-pull the same page every
week), several layers point at a *specific* upstream dataset that the publisher
silently supersedes with a new one:

  * Socrata portal datasets can be versioned by year. The reference fork's CPS
    attendance-boundary layers, for example, are published fresh every school
    year under a BRAND NEW dataset id (…SY2526 → …SY2627), so the id hardcoded
    in index.html keeps returning last year's boundaries long after a newer one
    exists. Nothing errors; the data just quietly goes stale.
  * Pre-built boundary layers (in this instance: the TIGERweb-derived district
    files) were downloaded at build time. The check there is provenance: is
    the source we cite still reachable, and a reminder to re-verify after
    each redistricting cycle.

This script does NOT edit index.html or any data file — swapping a dataset id
is a judgement call (the "newer" dataset may have a different schema), so, like
the roster workflows, it surfaces drift for a human instead of auto-applying it.

What it checks (findings carry a severity — FAIL, WARN, or OK):
  1. Manifest ↔ app coherence: every dataset id / data file the manifest knows
     about is still referenced in index.html (guards this file drifting from the
     app it validates).                                                   [FAIL]
  2. Socrata datasets: each id still resolves and still carries the stable part
     of its expected name (a rename usually means it was replaced).       [FAIL]
     For year-versioned datasets, the portal catalog is searched for a newer
     edition than the one in use.                                         [WARN]
  3. Shapefile provenance: the cited source URL is reachable and the built
     data/app file is present.                             [WARN / FAIL if gone]
  4. Live service endpoints (Census TIGERweb): reachable.                  [WARN]

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/in-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 in/scripts/validate_sources.py                 # human-readable report
    python3 in/scripts/validate_sources.py --report r.md   # also write markdown
    python3 in/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 in/scripts/validate_sources.py --offline       # manifest↔app checks only
"""

import argparse
import json
import os
import re
import sys

try:
    import requests
except ImportError:  # pragma: no cover - requests is pinned in requirements.txt
    requests = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

HTTP_TIMEOUT = 25

# The freshness gate's source manifest for the Indiana instance. Every layer this
# instance adds gets its rows here in the same change (CLAUDE.md's
# conventions; the reference repo's validate_sources.py shows a mature
# manifest's full shape, including year-search patterns and the `blocked`
# inversion).
SOCRATA_DOMAIN = "data.invalid"  # this fork's Socrata portal, if it adopts one
CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"

# Socrata dataset ids the app hardcodes (none in the starter set).
SOCRATA = []

# Same-origin data/app files and the upstream source each was built from.
PROVENANCE = [
    {
        "layer": "us-house",
        "app_file": "congress-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0",
        "note": (
            "Indiana's 9 congressional districts, pre-built from TIGERweb by "
            "in/scripts/build_legislative_boundaries.py. THE DISTRICT FIELD IS "
            "VERSIONED AND THE OLD ONE IS REMOVED, NOT MERELY STALE: this layer "
            "is '120th Congressional Districts' and its field is CD120; a query "
            "naming the retired CD119 is rejected outright with HTTP 400 "
            "(measured on this service 2026-09-03). On the next roll the "
            "builder's field list and the app's CONGRESS_DISTRICT_FIELDS both "
            "need the new name."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": (
            "Delegation roster from the public-domain congress-legislators "
            "project; refreshed weekly by update-in-congress-roster.yml. This is "
            "the instance's ONLY roster -- every other layer names nobody, which "
            "the cards say."
        ),
    },
    {
        "layer": "in-senate",
        "app_file": "in-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": (
            "50 Senate districts pre-built from TIGERweb (SLDU) by "
            "in/scripts/build_legislative_boundaries.py. NO WATER PSEUDO-DISTRICT "
            "on this layer for Indiana, unlike Illinois's ZZ features (measured "
            "2026-09-29: the state's districts number 1..50 with nothing else), "
            "which is what lets the builder's min_features be the exact count and "
            "its partition gate require a complete 1..N numbering. Redrawn by the "
            "General Assembly each decennial cycle (WATCH.md)."
        ),
    },
    {
        "layer": "in-house",
        "app_file": "in-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": (
            "100 House districts pre-built from TIGERweb (SLDL) by "
            "in/scripts/build_legislative_boundaries.py; same redistricting cycle "
            "as the Senate. INDIANA'S CHAMBERS DO NOT NEST, which is why this "
            "builder carries no nesting gate: 100 House districts over 50 Senate "
            "districts looks like Illinois's exact 2-to-1 rule and is not one. "
            "Measured 2026-09-29 by testing every House district's own interior "
            "point against the Senate layer, the House districts per Senate "
            "district run {1: 11, 2: 24, 3: 11, 4: 2} and the numbering is "
            "unrelated (Senate 1 holds House 12 and 15). A nesting check here "
            "could only ever be vacuous, so the builder asserts a complete "
            "self-consistent partition of each chamber instead."
        ),
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "All 92 counties pre-built from TIGERweb by "
            "in/scripts/build_state_counties.py. The fabric is WATER-INCLUSIVE: "
            "the four Lake Michigan counties reach the state water boundary and "
            "the southern tier reaches the Ohio River's low-water mark, which is "
            "why the coverage outline dissolves to one ring. THE CARD NAMES NO "
            "OFFICEHOLDER ON PURPOSE -- an Indiana county is run by TWO elected "
            "bodies drawn on their own district lines (a three-member board of "
            "commissioners and a seven-member county council), so neither can "
            "ride this geometry; gap in-county-government."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "The whole-state outline for the coverage wash, pre-built by "
            "in/scripts/build_metro_outline.py -- dissolved from all 92 counties "
            "on the SAME layer state-counties.json comes from, not fetched as a "
            "separate state polygon, so narrowing coverage later needs only a "
            "smaller METRO_COUNTY_FIPS (the Wisconsin precedent). Read the ring "
            "count from `build_metro_outline.py --check`, never from a map. That "
            "check runs offline against the shipped file on every PR, which is a "
            "DIFFERENT question from this row's: it asks whether the 92 INSIDE "
            "anchors still fall inside what SHIPPED, and cannot see the source "
            "moving underneath it."
        ),
    },
]

ENDPOINTS = [
    # The seven live layers are TIGERweb and USGS with NO builder and NO
    # committed data/app file between them, so a vintage roll reaches them on
    # their own and there is nothing here to rebuild. What this list watches is
    # each endpoint still ANSWERING FOR INDIANA: the TIGERweb rows are
    # returnCountOnly queries on STATE='18', so a service moved, renamed or
    # silently emptied for this state surfaces as a WARN instead of as cards
    # that quietly stop resolving.
    #
    # The counts below are measured 2026-09-29 and are recorded, not asserted:
    # this validator reports, it never edits the app. County subdivisions 1,012 ·
    # places 566 · unified school districts 291.
    #
    # BOTH OF TIGERWEB'S OTHER SCHOOL TILINGS ANSWER ZERO FOR INDIANA -- layer 1
    # (secondary) and layer 2 (elementary), measured the same day -- so the state
    # runs unified districts alone. Both are recorded drops and neither is
    # watched here: there is no layer for them to break. That is the opposite of
    # Michigan, where layer 2 answers 27 and ships.
    {
        "layer": "county-subdivision",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/1/query?where=STATE%3D%2718%27&returnCountOnly=true&f=json",
        "min_count": 950,  # 1,012 measured 2026-09-29; floor set below it, not at it
    },
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2718%27&returnCountOnly=true&f=json",
        "min_count": 520,  # 566 measured 2026-09-29; floor set below it, not at it
    },
    {
        "layer": "school-district-unified",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0/query?where=STATE%3D%2718%27&returnCountOnly=true&f=json",
        "min_count": 270,  # 291 measured 2026-09-29; floor set below it, not at it
    },
    # USGS structures layer 38. Counted rather than fetched, because the count is
    # the thing at risk: the service caps a response at 2,000 records and says so
    # with HTTP 200 + exceededTransferLimit rather than an error. The app's loader
    # PAGES for that reason, and min_count is what makes this row a real tripwire
    # rather than a ping: a count that falls away, or an error envelope arriving
    # as a 200, both surface here.
    #
    # EVERY USGS ROW IS COUNTED BY ENVELOPE -- these layers carry no state field --
    # so each count includes structures in the four bordering states that fall
    # inside Indiana's box. The app's own point query is what decides what a
    # reader is told; this is a tripwire on the source, not a census of Indiana.
    #
    # THE FLOORS ARE NOT MICHIGAN'S AND THE NUMBERS ARE NOT COMPARABLE: Indiana's
    # box is about a third the area of Michigan's, so a floor copied from that
    # instance would sit above every one of these counts and fail every run.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query"
                "?geometry=-88.10%2C37.77%2C-84.78%2C41.77&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 900,  # 1,012 measured 2026-09-29; floor set below it, not at it
    },
    # Layer 51, THE ONE THAT IS OVER THE CAP: 1,758 in this envelope against a
    # 2,000-record ceiling -- under it today, but the app pages regardless and a
    # widened envelope or a denser refile crosses it.
    #
    # returnCountOnly IS NOT SUBJECT TO maxRecordCount, so no row here can ever
    # see the client hitting the cap; it answers the true count whatever the app
    # does. So this floor watches the SOURCE SHRINKING, exactly like the others.
    # WHAT ACTUALLY CATCHES THE CLIENT TRUNCATING is a check on what the app
    # receives, which is what the browser gate is for -- in/scripts/smoke_test.mjs
    # asserts the pager makes more than one request. A row here cannot substitute
    # for it.
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query"
                "?geometry=-88.10%2C37.77%2C-84.78%2C41.77&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 1600,  # 1,758 measured 2026-09-29; floor set below it, not at it
    },
    # Layer 53, the smallest of the three (650 measured 2026-09-29) and fetched by
    # the same paging path regardless; min_count is what turns this from a
    # reachability ping into a check that can see an error envelope.
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query"
                "?geometry=-88.10%2C37.77%2C-84.78%2C41.77&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 580,  # 650 measured 2026-09-29; floor set below it, not at it
    },
    # ZCTAs carry NO STATE field either, so this one is counted by ENVELOPE too,
    # in Esri's own {xmin,...} comma form -- the {minLng,...} shape makes TIGERweb
    # answer HTTP 200 with a JSON error envelope. min_count is what makes this a
    # real check rather than a reachability ping: without it that error envelope
    # reads as a healthy 200.
    #
    # TWO COUNTS ARE TRUE HERE AND THEY ANSWER DIFFERENT QUESTIONS. This query
    # counts 1,206 -- every ZCTA whose extent touches Indiana's box, including
    # Illinois, Michigan, Ohio and Kentucky ZCTAs across each border -- while 882
    # of them intersect the state itself, which is the figure the app's own
    # sidebar comment states. The floor below belongs to THIS query's number, and
    # the two must not be swapped: a floor of 1,100 against an in-state count
    # would fail every run.
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query?where=1%3D1"
                "&geometry=-88.10%2C37.77%2C-84.78%2C41.77&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 1100,  # 1,206 measured 2026-09-29; floor set below it, not at it
    },
]
FAIL, WARN, OK = "FAIL", "WARN", "OK"


class Findings(object):
    """Collects (severity, layer, message) rows and tracks the worst seen."""

    def __init__(self):
        self.rows = []

    def add(self, severity, layer, message):
        self.rows.append((severity, layer, message))

    def status(self):
        if any(s == FAIL for s, _, _ in self.rows):
            return "fail"
        if any(s == WARN for s, _, _ in self.rows):
            return "warn"
        return "ok"


def http_get(url, want_json=True, params=None):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises."""
    if requests is None:
        return False, "requests not installed"
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": "districtry source validator (+https://districtry.com/in/)"},
        )
    except Exception as e:  # network/TLS/proxy errors are a finding, not a crash
        return False, "request failed: %s" % e
    if resp.status_code >= 400:
        return False, "HTTP %d" % resp.status_code
    # 202 is never a real document. "Accepted" means the request was taken for
    # later processing, and the bot-management fronts in front of several
    # government sites use it for their interstitial. Treat it as unreachable
    # and say why, so the two signals agree.
    if resp.status_code == 202:
        return False, "HTTP 202 — bot-management interstitial, not the document"
    if not want_json:
        return True, resp
    try:
        return True, resp.json()
    except ValueError as e:
        return False, "non-JSON response: %s" % e


# ---- check 1: the manifest still matches what index.html actually uses -------
def check_manifest_matches_app(html, findings):
    for d in SOCRATA:
        if d["id"] not in html:
            findings.add(FAIL, d["layer"],
                         "dataset id %s not found in index.html — manifest is "
                         "out of sync with the app (update in/scripts/validate_sources.py)"
                         % d["id"])
    for p in PROVENANCE:
        # A file the app addresses by a slug built at RUNTIME has no literal to
        # find — the same `dynamic_reference` exemption validate_index.py
        # grants. The entry names the suffix instead, and the drift check
        # looks for THAT: a card that stopped fetching the family at all
        # still fails here. (No such entries yet in this instance.)
        needle = p.get("app_file_pattern") or ("data/app/" + p["app_file"])
        if needle not in html:
            findings.add(FAIL, p["layer"],
                         "index.html no longer references %s — manifest drift"
                         % needle)


# ---- check 2: Socrata datasets resolve, keep their name, aren't superseded ---
def newest_edition(cfg):
    """Search the portal catalog for the newest edition matching cfg.

    Returns (id, name, year_int) for the highest `pattern` capture, or None if
    the search is unavailable / finds nothing usable.
    """
    ys = cfg["year_search"]
    ok, payload = http_get(CATALOG_API, params={
        "domains": SOCRATA_DOMAIN,
        "q": ys["query"],
        "only": "dataset,map,geospatial",
        "limit": 200,
    })
    if not ok or not isinstance(payload, dict):
        return None
    rx = re.compile(ys["pattern"])
    best = None
    for r in payload.get("results", []):
        res = r.get("resource", {})
        name = res.get("name", "")
        if cfg["name_contains"] not in name:
            continue
        m = rx.search(name)
        if not m:
            continue
        year = int(m.group(1))
        if best is None or year > best[2]:
            best = (res.get("id"), name, year)
    return best


def check_socrata(findings, offline):
    for cfg in SOCRATA:
        layer = cfg["layer"]
        if offline:
            continue
        ok, meta = http_get("https://%s/api/views/%s.json" % (SOCRATA_DOMAIN, cfg["id"]))
        if not ok:
            findings.add(FAIL, layer,
                         "dataset %s does not resolve on the portal (%s) — likely "
                         "retired or replaced" % (cfg["id"], meta))
            continue
        name = meta.get("name", "") if isinstance(meta, dict) else ""
        if cfg["name_contains"] not in name:
            findings.add(FAIL, layer,
                         "dataset %s is now named %r — expected it to contain %r; "
                         "the id may have been repurposed"
                         % (cfg["id"], name, cfg["name_contains"]))
            continue

        if "year_search" not in cfg:
            findings.add(OK, layer, "%s — %r" % (cfg["id"], name))
            continue

        # year-versioned: is a newer edition published?
        cur = re.search(cfg["year_search"]["pattern"], name)
        cur_year = int(cur.group(1)) if cur else None
        newest = newest_edition(cfg)
        if newest is None or cur_year is None:
            findings.add(OK, layer,
                         "%s — %r (newer-edition search unavailable)" % (cfg["id"], name))
        elif newest[2] > cur_year and newest[0] != cfg["id"]:
            findings.add(WARN, layer,
                         "in use: %s (%r). NEWER edition on the portal: %s (%r). "
                         "Review the newer dataset's schema, then update the id in index.html."
                         % (cfg["id"], name, newest[0], newest[1]))
        else:
            findings.add(OK, layer, "%s — %r (newest edition)" % (cfg["id"], name))


# ---- check 3: shapefile provenance reachable, built file present ------------
def check_provenance(findings, offline):
    for p in PROVENANCE:
        layer = p["layer"]
        fpath = os.path.join(APP_DATA_DIR, p["app_file"])
        if not os.path.exists(fpath):
            findings.add(FAIL, layer, "built data file data/app/%s is missing" % p["app_file"])
        if offline:
            continue
        ok, res = http_get(p["source_url"], want_json=False)
        blocked = p.get("blocked")
        if ok and blocked:
            # The block LIFTING is the news — see il/scripts/validate_sources.py
            # for the fuller rationale (the fleet-wide `blocked` inversion).
            findings.add(WARN, layer,
                         "source is REACHABLE again (%s) — its recorded block appears to "
                         "have LIFTED. Re-test the scraper; if it works, drop the "
                         "`blocked` flag on this entry so a future outage warns again. "
                         "Recorded block: %s" % (p["source_url"], blocked))
        elif ok:
            findings.add(OK, layer, "source reachable: %s — %s" % (p["source_url"], p["note"]))
        elif blocked:
            findings.add(OK, layer,
                         "unreachable AS EXPECTED (%s) — %s. %s"
                         % (res, blocked, p["source_url"]))
        else:
            findings.add(WARN, layer,
                         "source not reachable (%s): %s. Boundaries change ~once a "
                         "decade; verify the source still exists and re-download if redrawn. %s"
                         % (res, p["source_url"], p["note"]))


# ---- check 4: live endpoints reachable --------------------------------------
def check_endpoints(findings, offline):
    if offline:
        return
    for e in ENDPOINTS:
        # An entry carrying `min_count` is checked for CONTENT, not just
        # reachability, and the difference is the whole point of the flag.
        # HTTP STATUS CANNOT SEE AN ESRI ERROR ENVELOPE: a malformed query
        # answers 200 with {"error": {"code": 400}} and no rows, which every
        # status-based check reads as healthy. That is exactly how ia/ shipped
        # a dead ZIP overlay for weeks (#718) while its own source validator
        # reported the layer reachable — the endpoint it probed was the layer's
        # METADATA, which was reachable and always would be. A count query with
        # a floor is the smallest check that could actually have caught it.
        want_json = "min_count" in e
        ok, res = http_get(e["url"], want_json=want_json)
        if not ok:
            findings.add(WARN, e["layer"],
                         "endpoint not reachable (%s): %s — the service may have been "
                         "renamed or retired" % (res, e["url"]))
            continue
        if not want_json:
            findings.add(OK, e["layer"], "endpoint reachable")
            continue
        if isinstance(res, dict) and "error" in res:
            findings.add(FAIL, e["layer"],
                         "the query answered HTTP 200 with an Esri ERROR ENVELOPE "
                         "(%s) — the request is malformed or the service rejected "
                         "it, and nothing about the status code says so: %s"
                         % (res.get("error"), e["url"]))
            continue
        count = res.get("count") if isinstance(res, dict) else None
        if count is None:
            findings.add(FAIL, e["layer"],
                         "the count query returned no `count` field, so the layer "
                         "cannot be confirmed to be answering: %s" % e["url"])
        elif count < e["min_count"]:
            findings.add(WARN, e["layer"],
                         "the query returns %d features, below the floor of %d "
                         "recorded when the layer shipped — the source may have "
                         "moved, been re-scoped, or started truncating: %s"
                         % (count, e["min_count"], e["url"]))
        else:
            findings.add(OK, e["layer"], "endpoint answering — %d features" % count)


def render(findings):
    order = {FAIL: 0, WARN: 1, OK: 2}
    rows = sorted(findings.rows, key=lambda r: (order[r[0]], r[1]))
    n_fail = sum(1 for s, _, _ in rows if s == FAIL)
    n_warn = sum(1 for s, _, _ in rows if s == WARN)
    n_ok = sum(1 for s, _, _ in rows if s == OK)
    lines = []
    lines.append("# Layer source validation")
    lines.append("")
    lines.append("**%d FAIL · %d WARN · %d OK**" % (n_fail, n_warn, n_ok))
    lines.append("")
    if n_fail or n_warn:
        lines.append("Sources below need a human look. Nothing is auto-changed — "
                     "review, then update `index.html` (dataset ids) or re-download the "
                     "boundary shapefile as needed.")
        lines.append("")
    for sev in (FAIL, WARN, OK):
        group = [r for r in rows if r[0] == sev]
        if not group:
            continue
        lines.append("## %s (%d)" % (sev, len(group)))
        for _, layer, msg in group:
            lines.append("- **%s** — %s" % (layer, msg))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="Validate the app's data-layer sources are current.")
    ap.add_argument("--report", metavar="PATH", help="write the markdown report to PATH (also printed to stdout)")
    ap.add_argument("--status-file", metavar="PATH", help="write ok|warn|fail to PATH (for CI)")
    ap.add_argument("--offline", action="store_true", help="run only the manifest↔index.html checks (no network)")
    args = ap.parse_args()

    if not os.path.exists(INDEX_HTML):
        print("validate_sources: FAIL — index.html not found at %s" % INDEX_HTML, file=sys.stderr)
        sys.exit(1)
    html = open(INDEX_HTML).read()

    if not args.offline and requests is None:
        print("validate_sources: requests not installed; run with --offline or "
              "`pip install -c scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    check_manifest_matches_app(html, findings)
    check_socrata(findings, args.offline)
    check_provenance(findings, args.offline)
    check_endpoints(findings, args.offline)

    report = render(findings)
    sys.stdout.write(report)
    if args.report:
        with open(args.report, "w") as f:
            f.write(report)

    status = findings.status()
    if args.status_file:
        with open(args.status_file, "w") as f:
            f.write(status)

    sys.exit(1 if status == "fail" else 0)


if __name__ == "__main__":
    main()
