#!/usr/bin/env python3
"""
Source freshness gate for the app's data layers.

Why this exists: unlike the roster scrapers (which re-pull the same page every
week), several layers point at a *specific* upstream dataset that the publisher
silently supersedes with a new one:

  * DataSF (Socrata) datasets can be versioned by year. The SFUSD School
    Attendance Areas layer, for example, is republished each school year under
    a BRAND NEW dataset id ("…(2024-2025)" → "…(2025-2026)"), so the id
    hardcoded in index.html keeps returning last year's boundaries long after a
    newer one exists. Nothing errors; the data just quietly goes stale.
  * The pre-built boundary layers (supervisor districts, analysis neighborhoods,
    police districts, and the three legislative chambers) are built once into
    same-origin data/app files with no runtime API — from DataSF datasets and
    Census TIGERweb. They change ~once a decade, so the check there is
    provenance: is the source we cite still reachable, plus a reminder to
    re-verify.

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
  4. Live service endpoints (Census TIGERweb ZCTA): reachable.            [WARN]

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 scripts/validate_sources.py                 # human-readable report
    python3 scripts/validate_sources.py --report r.md   # also write markdown
    python3 scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 scripts/validate_sources.py --offline       # manifest↔app checks only
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

SOCRATA_DOMAIN = "data.sfgov.org"
# Newer-edition search hits the portal's OWN catalog, not the federated
# api.us.socrata.com one: DataSF is not indexed by the federated catalog (it
# returns zero for data.sfgov.org), whereas the portal-local catalog resolves
# and indexes the year-versioned sibling editions we compare against.
CATALOG_API = "https://%s/api/catalog/v1" % SOCRATA_DOMAIN
HTTP_TIMEOUT = 25

# ---------------------------------------------------------------------------
# The manifest: every source index.html depends on that can go stale silently.
#
# Socrata datasets — `name_contains` is the part of the portal title that must
# stay stable (a change means the dataset was replaced/renamed). `year_search`,
# when present, turns on newer-edition detection: the catalog is searched with
# `query`, results are kept only if their name also contains name_contains, and
# the `pattern` capture group (an int) is compared to pick the newest edition.
# ---------------------------------------------------------------------------
SOCRATA = [
    {"id": "rwdu-9wb2", "layer": "Police Stations (nearest-3)",
     "name_contains": "Police Stations"},
    {"id": "nc68-ngbr", "layer": "Fire Stations (City Facilities, nearest-3)",
     "name_contains": "City Facilities"},
    # ZIP Code is the statewide Census ZCTA layer (no DataSF dataset) — its
    # endpoint is tracked in ENDPOINTS below, not here.
    # SFUSD attendance areas rotate each school year. Caveat: the in-use dataset
    # (e6tr-sxwg, "…(2024-2025)") is a derived view DataSF's catalog does NOT
    # index, so the newer-edition search compares against the catalog's sibling
    # "…School Attendance Areas <year>" editions instead. The year pattern is
    # unparenthesized so it matches both the current "(2024-2025)" title and the
    # bare "2023-2024" sibling form; a later indexed edition with a higher year
    # trips a WARN for a human to re-verify against.
    {"id": "e6tr-sxwg", "layer": "SFUSD Elementary Attendance Area",
     "name_contains": "School Attendance Areas",
     "year_search": {"query": "School Attendance Areas",
                     "pattern": r"(\d{4})-\d{4}"}},
    {"id": "7e7j-59qk", "layer": "School Location (nearest-3)",
     "name_contains": "Schools"},
    {"id": "fhhu-wqa7", "layer": "Library locations (nearest-3)",
     "name_contains": "City Facilities - Public Library"},
    # Precincts are redrawn with each supervisor redistricting (~decadal); the
    # successor will carry a new "Defined <year>" title, which the year-search
    # watches for (next expected ~2032).
    {"id": "jg6x-23ig", "layer": "Election Precinct",
     "name_contains": "Map of Election Precincts",
     "year_search": {"query": "Map of Election Precincts",
                     "pattern": r"Defined (\d{4})"}},
]

# Boundary layers built into same-origin data/app files: no runtime API.
# `source_url` is the provenance we cite; `app_file` is the built file. These go
# stale only when the underlying districts are redrawn — the check is a
# reachability probe plus a standing reminder to re-verify against the source.
# The first three are mapshaper-simplified from DataSF datasets (SF's civic
# geometry is consolidated on DataSF); the three legislative layers are pre-built
# from Census TIGERweb by scripts/build_legislative_boundaries.py (they used to
# query TIGERweb live at ~5.7 s per first toggle).
PROVENANCE = [
    {"layer": "Supervisor districts",
     "app_file": "supervisor-districts.json",
     "source_url": "https://data.sfgov.org/d/hcgx-vtsb",
     "note": "DataSF Current Supervisor Districts (hcgx-vtsb), water-trimmed. Redrawn ~once a decade."},
    {"layer": "Analysis Neighborhoods",
     "app_file": "sf-neighborhoods.json",
     "source_url": "https://data.sfgov.org/d/j2bu-swwd",
     "note": "DataSF Analysis Neighborhoods (j2bu-swwd). Revised rarely."},
    {"layer": "Police districts",
     "app_file": "police-districts.json",
     "source_url": "https://data.sfgov.org/d/d4vc-q76h",
     "note": "DataSF Current Police Districts (d4vc-q76h). Revised rarely."},
    {"layer": "U.S. House districts (CA)",
     "app_file": "congress-districts.json",
     "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0?f=json",
     "note": "TIGERweb Legislative layer 0 (STATE=06), SF-clipped, pre-built by build_legislative_boundaries.py. Redrawn ~once a decade. Built against TIGERweb's 120th-Congress layer (field CD120, Jan 1 2026 vintage); the retired CD119 field is gone and a query naming it returns an HTTP-200 JSON error envelope with no features key, so a rebuild on the old name fails as no-features."},
    {"layer": "CA State Senate districts",
     "app_file": "ca-senate-districts.json",
     "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1?f=json",
     "note": "TIGERweb Legislative layer 1 (Upper, STATE=06), SF-clipped, pre-built. Redrawn ~once a decade."},
    {"layer": "CA State Assembly districts",
     "app_file": "ca-assembly-districts.json",
     "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2?f=json",
     "note": "TIGERweb Legislative layer 2 (Lower, STATE=06), SF-clipped, pre-built. Redrawn ~once a decade."},
    {"layer": "Voting center & ballot drop-off sites (SF Dept of Elections)",
     "app_file": "early-voting-sites.json",
     "source_url": "https://www.sf.gov/return-your-ballot",
     "note": "Hand-transcribed per election (full source list in the file's metadata). Refresh when the Department posts the next election's locations."},
    {"layer": "BART Director roster",
     "app_file": "bart-directors.json",
     "source_url": "https://www.bart.gov/about/bod",
     "note": "Hand-verified 2026-07-19; staggered 4-year terms (SF districts 7/8 "
             "next on the Nov 2026 ballot — see WATCH.md). bart.gov 403s "
             "non-browser clients, so a reachability WARN here is expected, "
             "not drift."},
]

# Live named services the app queries at runtime. These aren't year-versioned
# (they're views/endpoints kept current by the publisher), so the only useful
# check is reachability — a rename or retirement shows up here before users hit
# a broken card. WARN-only: the app already isolates a down source per-card.
ENDPOINTS = [
    {"layer": "Census TIGERweb ZCTAs (statewide ZIP Code layer)",
     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer?f=json"},
    {"layer": "USGS National Map structures — post offices (layer 38)",
     "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38?f=json"},
    {"layer": "BART Director districts (BART's ArcGIS org, 2022 Plan E2)",
     "url": "https://services.arcgis.com/sqS7RNuF1BQinj5N/ArcGIS/rest/services/Board_of_Directors_District_Boundary_Viewer_Base_Data_WFL1/FeatureServer/2?f=json"},
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
            headers={"User-Agent": "districtry source validator (+https://districtry.com/ca/)"},
        )
    except Exception as e:  # network/TLS/proxy errors are a finding, not a crash
        return False, "request failed: %s" % e
    if resp.status_code >= 400:
        return False, "HTTP %d" % resp.status_code
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
                         "out of sync with the app (update scripts/validate_sources.py)"
                         % d["id"])
    for p in PROVENANCE:
        if ("data/app/" + p["app_file"]) not in html:
            findings.add(FAIL, p["layer"],
                         "index.html no longer references data/app/%s — manifest drift"
                         % p["app_file"])


# ---- check 2: Socrata datasets resolve, keep their name, aren't superseded ---
def newest_edition(cfg):
    """Search the portal catalog for the newest edition matching cfg.

    Returns (id, name, year_int) for the highest `pattern` capture, or None if
    the search is unavailable / finds nothing usable.
    """
    ys = cfg["year_search"]
    # The portal-local catalog is already scoped to its own datasets, so it is
    # queried WITHOUT a `domains` filter (passing one returns zero results). No
    # `only` type filter either: SFUSD republishes attendance areas as
    # `federated_href` entries, which a dataset/map/geospatial filter would drop.
    ok, payload = http_get(CATALOG_API, params={
        "q": ys["query"],
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
        if ok:
            findings.add(OK, layer, "source reachable: %s — %s" % (p["source_url"], p["note"]))
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
        ok, res = http_get(e["url"], want_json=False)
        if ok:
            findings.add(OK, e["layer"], "endpoint reachable")
        else:
            findings.add(WARN, e["layer"],
                         "endpoint not reachable (%s): %s — the service may have been "
                         "renamed or retired" % (res, e["url"]))


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
