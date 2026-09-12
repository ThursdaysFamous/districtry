#!/usr/bin/env python3
"""
Source freshness gate for the app's data layers (NYC port of the CHI gate).

Why this exists: unlike the roster scrapers (which re-pull the same page every
week), several layers point at a *specific* upstream dataset that the publisher
silently supersedes with a new one:

  * NYC Open Data (Socrata) school-zone datasets are versioned by school year.
    Each year's zones are published under a BRAND NEW dataset id ("School Zones
    2024-2025 (Elementary School)" → "School Zones 2025-2026 (…)"), so the id
    hardcoded in index.html keeps returning last year's boundaries long after a
    newer one exists. Nothing errors; the data just quietly goes stale. (This
    check absorbs the retired scripts/check_school_zone_ids.py — same catalog
    search, same ids, one gate. One deliberate severity change: the retired
    script WARNed on transient non-404 portal errors, while this gate keeps
    CHI's policy verbatim and FAILs on any resolution failure — the job stays
    green either way and the tracking issue self-heals on the next run.)
    The 2020 NTAs are the decennial version of the
    same failure mode: a "2030 Neighborhood Tabulation Areas" dataset will one
    day appear beside the one in use.
  * Census TIGERweb rolls its congressional layer name and field alias with
    each Congress (CD120 → CD121). NY redistricts congressional maps
    aggressively off-cycle — three maps in three years — so this watch is a
    REDISTRICTING_RUNBOOK detection-layer requirement, not a nicety.
  * The three offline anchors (borough, judicial district, municipal court)
    were downloaded once (see scripts/build_embedded_boundaries.py) with no
    live loader. They change ~never; the check there is provenance: is the
    source we cite still reachable, and a reminder to re-verify.

This script does NOT edit index.html or any data file — swapping a dataset id
is a judgement call (the "newer" dataset may have a different schema), so, like
the roster workflows, it surfaces drift for a human instead of auto-applying it.

What it checks (findings carry a severity — FAIL, WARN, or OK):
  1. Manifest ↔ app coherence: every dataset id / endpoint / data file the
     manifest knows about is still referenced in index.html (anchors: in
     scripts/build_embedded_boundaries.py, where their provenance lives) —
     guards this file drifting from the app it validates.                [FAIL]
  2. Socrata datasets: each id still resolves and still carries the stable part
     of its expected name (a rename usually means it was replaced).       [FAIL]
     For year-versioned datasets, the portal catalog is searched for a newer
     edition than the one in use.                                         [WARN]
  3. TIGERweb Legislative MapServer: the layer index the BUILDER queries still
     carries its expected name (an in-place roll means the pre-built file the
     app now serves predates it and a rebuild is due)                     [FAIL]
     and the layer list is scanned for a successor vintage (CD120 → CD121,
     2024 SLD → newer); the pre-built files also get a presence check.    [WARN]
  4. Anchor provenance: the cited source still resolves, and the built
     data/app file is present.                              [WARN / FAIL if gone]
  5. Live service endpoints (DCP ArcGIS, NYSED ArcGIS): reachable.        [WARN]

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Platform note (REDISTRICTING_RUNBOOK): Socrata is now Tyler "Data & Insights"
and SODA3 requires an app token; SODA2 still runs in parallel. SOCRATA_APP_TOKEN
is sent when set (recommended in CI) so a future SODA2 deprecation surfaces
here as auth guidance rather than as a broken layer.

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
BOUNDARIES_BUILDER = os.path.join(REPO_ROOT, "scripts", "build_embedded_boundaries.py")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

SOCRATA_DOMAIN = "data.cityofnewyork.us"
CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"
HTTP_TIMEOUT = 25

# ---------------------------------------------------------------------------
# The manifest: every source index.html depends on that can go stale silently.
# Layer labels are transcribed from each source's module comment in index.html.
#
# Socrata datasets — `name_contains` is the part of the portal title that must
# stay stable (a change means the dataset was replaced/renamed). `year_search`,
# when present, turns on newer-edition detection: the catalog is searched with
# `query`, results are kept only if their name also contains name_contains AND
# matches `pattern`, and the pattern's capture group (an int) is compared to
# pick the newest edition.
#
# Every entry carries the REDISTRICTING_RUNBOOK detection-layer fields:
#   vintage             — which edition/map the app is serving today
#   expected_successor  — what a human should expect to replace it, and how
#                         this script would notice
# Both are rendered into the report's "Redistricting watch" section so the
# monthly tracking issue always shows the full watch list.
# ---------------------------------------------------------------------------
SOCRATA = [
    {"id": "feuq-due4", "layer": "Library branches (nearest N)",
     "name_contains": "LIBRARY",
     "vintage": "citywide NYPL/BPL/QPL branch points (rows ~2016; branch locations near-static)",
     "expected_successor": "updated in place; per-system datasets (e.g. Queens kh3d-xhq7) are the fresher alternates if hours are ever wanted"},
    {"id": "872g-cjhh", "layer": "City Council District (51)",
     "name_contains": "City Council Districts",
     "vintage": "2023 Districting Commission map (effective Feb 2023)",
     "expected_successor": "next municipal remap ~2032-33; rows update in place on this id"},
    {"id": "5crt-au7u", "layer": "Community District / Community Board (59)",
     "name_contains": "Community Districts",
     "vintage": "charter community districts (59)",
     "expected_successor": "charter changes only, rare; updated in place"},
    {"id": "ruf7-3wgc", "layer": "Community Board leadership roster (rows)",
     "name_contains": "NYC Community Boards",
     "vintage": "live-updated CB roster rows (the only machine-readable CB roster)",
     "expected_successor": "updated in place; no versioned successor expected"},
    {"id": "9nt8-h7nd", "layer": "Neighborhood (NTA 2020)",
     "name_contains": "Neighborhood Tabulation Areas (NTAs)",
     "vintage": "2020 census NTAs",
     "expected_successor": "a '2030 Neighborhood Tabulation Areas' dataset after the "
                           "next census — year_search watches for it",
     "year_search": {"query": "Neighborhood Tabulation Areas",
                     "pattern": r"(\d{4}) Neighborhood Tabulation Areas"}},
    {"id": "pri4-ifjk", "layer": "ZIP Code (MODZCTA)",
     "name_contains": "Modified Zip Code Tabulation Areas (MODZCTA)",
     "vintage": "2020-vintage MODZCTA",
     "expected_successor": "USPS/DOHMH-driven; updated in place; a post-2030 successor "
                           "would be a new dataset"},
    {"id": "8ugf-3d8u", "layer": "Community School District (32)",
     "name_contains": "School Districts",
     "vintage": "DOE community school districts (32)",
     "expected_successor": "DOE-driven, rare; updated in place"},
    {"id": "y76i-bdw7", "layer": "NYPD Precinct (78)",
     "name_contains": "Police Precincts",
     "vintage": "78 precincts (116th Precinct added Dec 2024)",
     "expected_successor": "administrative reorgs, updated in place — "
                           "validate_index's precinct floor catches count changes"},
    {"id": "5rqd-h5ci", "layer": "NYPD Sector (303)",
     "name_contains": "NYPD Sectors",
     "vintage": "current NYPD patrol sectors",
     "expected_successor": "administrative; updated in place"},
    {"id": "ji82-xba5", "layer": "Police Station points (FacDB)",
     "name_contains": "Facilities Database",
     "vintage": "live FacDB (police-station points via factype filter)",
     "expected_successor": "updated in place (facility openings/closures)"},
    {"id": "hc8x-tcnd", "layer": "Firehouse points (219)",
     "name_contains": "FDNY Firehouse Listing",
     "vintage": "live firehouse listing",
     "expected_successor": "updated in place (facility openings/closures)"},
    {"id": "cmjf-yawu", "layer": "Elementary School Zone",
     "name_contains": "(Elementary School)",
     "vintage": "School Zones 2024-2025 (SY2024-25 edition)",
     "expected_successor": "'School Zones 2025-2026 (Elementary School)' — a NEW "
                           "dataset id every school year; year_search watches",
     "year_search": {"query": "School Zones",
                     # position-independent school-year capture (the retired
                     # checker's regex), so a DOE title reformat can't silently
                     # defeat the successor search; the level rides on
                     # name_contains.
                     "pattern": r"(\d{4})\s*-\s*\d{4}"}},
    {"id": "t26j-jbq7", "layer": "Middle School Zone",
     "name_contains": "(Middle School)",
     "vintage": "School Zones 2024-2025 (SY2024-25 edition)",
     "expected_successor": "'School Zones 2025-2026 (Middle School)' — a NEW "
                           "dataset id every school year; year_search watches",
     "year_search": {"query": "School Zones",
                     # position-independent school-year capture (the retired
                     # checker's regex), so a DOE title reformat can't silently
                     # defeat the successor search; the level rides on
                     # name_contains.
                     "pattern": r"(\d{4})\s*-\s*\d{4}"}},
    {"id": "ruu9-egea", "layer": "High School Zone",
     "name_contains": "(High School)",
     "vintage": "School Zones 2024-2025 (SY2024-25 edition)",
     "expected_successor": "'School Zones 2025-2026 (High School)' — a NEW "
                           "dataset id every school year; year_search watches",
     "year_search": {"query": "School Zones",
                     # position-independent school-year capture (the retired
                     # checker's regex), so a DOE title reformat can't silently
                     # defeat the successor search; the level rides on
                     # name_contains.
                     "pattern": r"(\d{4})\s*-\s*\d{4}"}},
]

# Census TIGERweb Legislative MapServer. The chamber geometry is now PRE-BUILT
# same-origin (scripts/build_legislative_boundaries.py, R2-2) — the app fetches
# data/app/{congress,state-senate,state-assembly}-districts.json and only falls
# back to a live loadTigerLayer(index) query if a fork ships no pre-built file
# (that retained fallback is why the MapServer URL still lives in index.html and
# the coherence check above still holds). The BUILDER queries these layers BY
# INDEX, and the Census rolls layer names / field aliases in place with each
# Congress / state-legislature vintage — so an expect_name mismatch at the index
# means the shipped pre-built file predates a roll and a rebuild is due [FAIL],
# and a higher watch_pattern capture anywhere in the layer list means the
# successor vintage has been published and the file should be regenerated [WARN].
# This is the runbook's CD120 → CD121 watch; NY makes it non-optional
# (three congressional maps in three years), and it doubles as the staleness
# detector the pre-build otherwise hides (a static file can't announce its
# own vintage).
TIGERWEB = {
    "mapserver": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer",
    "layers": [
        {"layer": "U.S. House District (NY)", "index": 0,
         "app_file": "congress-districts.json",
         "expect_name": "120th Congressional Districts",
         "watch_pattern": r"(\d+)(?:st|nd|rd|th) Congressional Districts",
         "current": 120,
         "vintage": "120th Congress (Jan 1, 2026 TIGERweb vintage; field CD120); "
                    "NY map enacted Feb 28, 2024",
         "expected_successor": "a '121st Congressional Districts' layer — the CD120 -> "
                               "CD121 roll; the layer-name scan watches for it"},
        {"layer": "NY State Senate District", "index": 1,
         "app_file": "state-senate-districts.json",
         "expect_name": "2026 State Legislative Districts - Upper",
         "watch_pattern": r"(\d{4}) State Legislative Districts - Upper",
         "current": 2026,
         "vintage": "NY Senate: 2022 special-master (Cervas) map, republished under "
                    "TIGERweb's 2026 vintage (the 2024 edition moved to layer indices "
                    "5/9; MEASURED 2026-09-03 as the same lines, not a redraw)",
         "expected_successor": "a newer-year SLDU layer (next redraw or post-2030 census)"},
        {"layer": "NY State Assembly District", "index": 2,
         "app_file": "state-assembly-districts.json",
         "expect_name": "2026 State Legislative Districts - Lower",
         "watch_pattern": r"(\d{4}) State Legislative Districts - Lower",
         "current": 2026,
         "vintage": "NY Assembly: map signed Apr 24, 2023 (effective 2024), republished "
                    "under TIGERweb's 2026 vintage (MEASURED 2026-09-03 as the same "
                    "lines, not a redraw)",
         "expected_successor": "a newer-year SLDL layer (next redraw or post-2030 census)"},
    ],
}

# Offline-anchor provenance: the three boundary layers with no live loader ship
# as same-origin data/app files built by scripts/build_embedded_boundaries.py,
# and their source citations live in THAT script's comments, not index.html —
# so the offline drift guard checks `builder_ref` against the builder. They go
# stale only when the underlying districts are redrawn; the check is a source
# probe plus a standing reminder to re-verify. Socrata-backed anchors get the
# stronger metadata/name check; problems are WARN (the shipped file still
# works), a missing data/app file is FAIL.
PROVENANCE = [
    {"layer": "Borough / County (offline anchor)",
     "app_file": "borough-boundaries.json",
     "socrata_id": "gthc-hcne", "name_contains": "Borough Boundaries",
     "builder_ref": "gthc-hcne",
     "vintage": "boroughs are fixed geography (downloaded once, shoreline-clipped)",
     "expected_successor": "none expected",
     "note": "Also serves Borough President + District Attorney (same 5 polygons)."},
    {"layer": "NY Supreme Court Judicial Districts (offline anchor)",
     "app_file": "judicial-districts.json",
     "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer?f=json",
     "builder_ref": "State_County",
     "vintage": "5 NYC counties relabeled as judicial districts 1/2/11/12/13",
     "expected_successor": "statutory change only — almost never",
     "note": "No live per-district source exists; county-derived from TIGERweb."},
    {"layer": "Civil (Municipal) Court districts (offline anchor)",
     "app_file": "municipal-court-districts.json",
     "socrata_id": "7vpq-4bh4", "name_contains": "Municipal Court Districts",
     "builder_ref": "7vpq-4bh4",
     "vintage": "28 elected-judge districts (map-type view; v3 route)",
     "expected_successor": "rare statutory redraws",
     "note": "Redrawn ~never; re-download via build_embedded_boundaries.py if it is."},
]

# Live named services the app queries at runtime. These aren't year-versioned
# (they're views/endpoints kept current by the publisher), so the only useful
# check is reachability — a rename or retirement shows up here before users hit
# a broken card. WARN-only: the app already isolates a down source per-card.
# The NYSED entries probe the exact layer indexes the app pages through
# (2/3/4 = Public/Private/Charter K-12), so an index reshuffle surfaces too.
# `app_refs`, when present, lists the strings the offline drift guard requires
# in index.html instead of the probe `url` — needed when the app assembles the
# URL at runtime (NYSED_BASE + layerIndex), so the full per-layer URL never
# appears verbatim in the source.
NYSED_BASE = "https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services/NYS_Schools/FeatureServer/"
ENDPOINTS = [
    {"layer": "Election District boundaries (DCP ArcGIS)",
     "url": "https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Election_Districts/FeatureServer/0",
     "vintage": "live BOE election districts via DCP ArcGIS (BOE redraws frequently, in place)",
     "expected_successor": "updated in place"},
    {"layer": "FDNY Battalion boundaries (DCP ArcGIS)",
     "url": "https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Fire_Battalions/FeatureServer/0",
     "vintage": "49 battalions (administrative)",
     "expected_successor": "updated in place"},
    {"layer": "School sites — public (NYSED ArcGIS layer 2)",
     "url": NYSED_BASE + "2",
     "app_refs": [NYSED_BASE, "loadNysedLayerPaged(2"],
     "vintage": "live NYS_Schools 'Public K-12' layer",
     "expected_successor": "updated in place; index reshuffle surfaces as unreachable"},
    {"layer": "School sites — private (NYSED ArcGIS layer 3)",
     "url": NYSED_BASE + "3",
     "app_refs": [NYSED_BASE, "loadNysedLayerPaged(3"],
     "vintage": "live NYS_Schools 'Private K-12' layer",
     "expected_successor": "updated in place; index reshuffle surfaces as unreachable"},
    {"layer": "School sites — charter (NYSED ArcGIS layer 4)",
     "url": NYSED_BASE + "4",
     "app_refs": [NYSED_BASE, "loadNysedLayerPaged(4"],
     "vintage": "live NYS_Schools 'Charter K-12' layer",
     "expected_successor": "updated in place; index reshuffle surfaces as unreachable"},
    {"layer": "Post offices (USGS National Map structures layer 38)",
     "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38",
     "vintage": "national NGDA structures layer, METRO_BBOX envelope-queried at runtime",
     "expected_successor": "updated in place (USGS; successor to the retired HIFLD Open layer)"},
    {"layer": "Early-voting poll sites (NYS GIS elections service layer 1)",
     "url": "https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services/NYS_Elections_Districts_and_Polling_Locations/FeatureServer/1",
     "vintage": "NYS/NYC BOE early-voting sites, refreshed per election cycle in place",
     "expected_successor": "updated in place; a service rename surfaces as unreachable"},
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


def http_get(url, want_json=True, params=None, socrata=False):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises."""
    if requests is None:
        return False, "requests not installed"
    headers = {"User-Agent": "districtry source validator (+https://districtry.com/ny/)"}
    if socrata and os.environ.get("SOCRATA_APP_TOKEN"):
        headers["X-App-Token"] = os.environ["SOCRATA_APP_TOKEN"]
    try:
        resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT, headers=headers)
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


def socrata_view_meta(dataset_id):
    return http_get("https://%s/api/views/%s.json" % (SOCRATA_DOMAIN, dataset_id),
                    socrata=True)


# ---- check 1: the manifest still matches what the app actually uses ---------
def check_manifest_matches_app(html, builder_src, findings):
    for d in SOCRATA:
        if d["id"] not in html:
            findings.add(FAIL, d["layer"],
                         "dataset id %s not found in index.html — manifest is "
                         "out of sync with the app (update scripts/validate_sources.py)"
                         % d["id"])
    if TIGERWEB["mapserver"] not in html:
        findings.add(FAIL, "TIGERweb legislative layers",
                     "index.html no longer references %s — manifest drift"
                     % TIGERWEB["mapserver"])
    for e in ENDPOINTS:
        for ref in e.get("app_refs", [e["url"]]):
            if ref not in html:
                findings.add(FAIL, e["layer"],
                             "index.html no longer references %s — manifest drift" % ref)
    for p in PROVENANCE:
        if ("data/app/" + p["app_file"]) not in html:
            findings.add(FAIL, p["layer"],
                         "index.html no longer references data/app/%s — manifest drift"
                         % p["app_file"])
        if p["builder_ref"] not in builder_src:
            findings.add(FAIL, p["layer"],
                         "provenance ref %r not found in scripts/build_embedded_boundaries.py "
                         "— manifest drift" % p["builder_ref"])


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
    }, socrata=True)
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
        ok, meta = socrata_view_meta(cfg["id"])
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


# ---- check 3: TIGERweb layer indexes hold their names; successor watch ------
def check_tigerweb(findings, offline):
    # The chamber geometry ships pre-built (R2-2); verify the files the app
    # serves exist regardless of network. validate_index guards their feature
    # counts; this guards existence from the source manifest's point of view,
    # so a deleted pre-built file surfaces here too.
    for cfg in TIGERWEB["layers"]:
        if "app_file" in cfg and not os.path.exists(os.path.join(APP_DATA_DIR, cfg["app_file"])):
            findings.add(FAIL, cfg["layer"],
                         "pre-built data file data/app/%s is missing — run "
                         "scripts/build_legislative_boundaries.py" % cfg["app_file"])
    if offline:
        return
    ok, meta = http_get(TIGERWEB["mapserver"] + "?f=json")
    if not ok or not isinstance(meta, dict) or "layers" not in meta:
        findings.add(WARN, "TIGERweb legislative layers",
                     "MapServer not reachable (%s): %s — the congress / state-legislature "
                     "layers can't be verified this run"
                     % (meta if not ok else "no layer list", TIGERWEB["mapserver"]))
        return
    by_index = {}
    names = []
    for l in meta["layers"]:
        by_index[l.get("id")] = l.get("name", "")
        names.append(l.get("name", ""))
    for cfg in TIGERWEB["layers"]:
        live = by_index.get(cfg["index"])
        if live != cfg["expect_name"]:
            findings.add(FAIL, cfg["layer"],
                         "MapServer layer %d is now %r — expected %r. TIGERweb rolled "
                         "the layer in place, so the pre-built data/app/%s predates the "
                         "roll; re-run scripts/build_legislative_boundaries.py, re-verify "
                         "ground truth + rosters, and update this manifest "
                         "(REDISTRICTING_RUNBOOK)."
                         % (cfg["index"], live, cfg["expect_name"], cfg["app_file"]))
            continue
        rx = re.compile(cfg["watch_pattern"])
        newest = cfg["current"]
        newest_name = None
        for n in names:
            m = rx.search(n)
            if m and int(m.group(1)) > newest:
                newest = int(m.group(1))
                newest_name = n
        if newest_name:
            findings.add(WARN, cfg["layer"],
                         "successor vintage published on TIGERweb: %r (the pre-built "
                         "data/app/%s still serves %r). Regenerate with "
                         "scripts/build_legislative_boundaries.py per REDISTRICTING_RUNBOOK."
                         % (newest_name, cfg["app_file"], cfg["expect_name"]))
        else:
            findings.add(OK, cfg["layer"],
                         "layer %d — %r (no successor vintage on the service)"
                         % (cfg["index"], cfg["expect_name"]))


# ---- check 4: anchor provenance reachable, built file present ---------------
def check_provenance(findings, offline):
    for p in PROVENANCE:
        layer = p["layer"]
        fpath = os.path.join(APP_DATA_DIR, p["app_file"])
        if not os.path.exists(fpath):
            findings.add(FAIL, layer, "built data file data/app/%s is missing" % p["app_file"])
        if offline:
            continue
        if "socrata_id" in p:
            ok, meta = socrata_view_meta(p["socrata_id"])
            name = meta.get("name", "") if ok and isinstance(meta, dict) else ""
            if not ok:
                findings.add(WARN, layer,
                             "provenance dataset %s not reachable (%s). The shipped "
                             "data/app/%s still works; verify the source still exists. %s"
                             % (p["socrata_id"], meta, p["app_file"], p["note"]))
            elif p["name_contains"] not in name:
                findings.add(WARN, layer,
                             "provenance dataset %s is now named %r — expected it to "
                             "contain %r; re-verify before the next regeneration. %s"
                             % (p["socrata_id"], name, p["name_contains"], p["note"]))
            else:
                findings.add(OK, layer, "source resolves: %s — %r. %s"
                             % (p["socrata_id"], name, p["note"]))
        else:
            ok, res = http_get(p["source_url"], want_json=False)
            if ok:
                findings.add(OK, layer, "source reachable: %s — %s" % (p["source_url"], p["note"]))
            else:
                findings.add(WARN, layer,
                             "source not reachable (%s): %s. Boundaries change ~never; "
                             "verify the source still exists and re-download if redrawn. %s"
                             % (res, p["source_url"], p["note"]))


# ---- check 5: live endpoints reachable --------------------------------------
def check_endpoints(findings, offline):
    if offline:
        return
    for e in ENDPOINTS:
        ok, res = http_get(e["url"] + "?f=json", want_json=False)
        if ok:
            findings.add(OK, e["layer"], "endpoint reachable")
        else:
            findings.add(WARN, e["layer"],
                         "endpoint not reachable (%s): %s — the service may have been "
                         "renamed or retired" % (res, e["url"]))


def watch_rows():
    """(layer, vintage, expected_successor) for every manifest source."""
    rows = []
    for d in SOCRATA:
        rows.append((d["layer"], d["vintage"], d["expected_successor"]))
    for t in TIGERWEB["layers"]:
        rows.append((t["layer"], t["vintage"], t["expected_successor"]))
    for p in PROVENANCE:
        rows.append((p["layer"], p["vintage"], p["expected_successor"]))
    for e in ENDPOINTS:
        rows.append((e["layer"], e["vintage"], e["expected_successor"]))
    return rows


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
                     "review, then update `index.html` (dataset ids) or regenerate the "
                     "anchor boundaries as needed.")
        lines.append("")
    for sev in (FAIL, WARN, OK):
        group = [r for r in rows if r[0] == sev]
        if not group:
            continue
        lines.append("## %s (%d)" % (sev, len(group)))
        for _, layer, msg in group:
            lines.append("- **%s** — %s" % (layer, msg))
        lines.append("")
    # REDISTRICTING_RUNBOOK detection layer: the standing watch list rides
    # along in every report so the monthly tracking issue always carries it.
    lines.append("## Redistricting watch (standing, informational)")
    for layer, vintage, successor in watch_rows():
        lines.append("- **%s** — in use: %s. Watching for: %s." % (layer, vintage, successor))
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="Validate the app's data-layer sources are current.")
    ap.add_argument("--report", metavar="PATH", help="write the markdown report to PATH (also printed to stdout)")
    ap.add_argument("--status-file", metavar="PATH", help="write ok|warn|fail to PATH (for CI)")
    ap.add_argument("--offline", action="store_true", help="run only the manifest↔app checks (no network)")
    args = ap.parse_args()

    if not os.path.exists(INDEX_HTML):
        print("validate_sources: FAIL — index.html not found at %s" % INDEX_HTML, file=sys.stderr)
        sys.exit(1)
    html = open(INDEX_HTML).read()
    builder_src = open(BOUNDARIES_BUILDER).read() if os.path.exists(BOUNDARIES_BUILDER) else ""

    if not args.offline and requests is None:
        print("validate_sources: requests not installed; run with --offline or "
              "`pip install -c scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    check_manifest_matches_app(html, builder_src, findings)
    check_socrata(findings, args.offline)
    check_tigerweb(findings, args.offline)
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
