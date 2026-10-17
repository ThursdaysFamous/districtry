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
workflow (.github/workflows/ar-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 ar/scripts/validate_sources.py                 # human-readable report
    python3 ar/scripts/validate_sources.py --report r.md   # also write markdown
    python3 ar/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 ar/scripts/validate_sources.py --offline       # manifest↔app checks only
"""

import argparse
import json
import os
import re
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

try:
    import requests
except ImportError:  # pragma: no cover - requests is pinned in requirements.txt
    requests = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

HTTP_TIMEOUT = 25

# The freshness gate's source manifest for the Arkansas instance. Every
# layer this instance adds gets its rows here in the same change (CLAUDE.md's
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
            "4 congressional districts pre-built from TIGERweb by "
            "ar/scripts/build_legislative_boundaries.py. THE DISTRICT FIELD IS "
            "VERSIONED AND THE OLD ONE IS REMOVED, NOT MERELY STALE: this layer "
            "is now '120th Congressional Districts' and its field is CD120; a "
            "query naming the retired CD119 is rejected outright with HTTP 400. "
            "On the next roll the builder's field list and the app's "
            "CONGRESS_DISTRICT_FIELDS both need the new name. Arkansas did not "
            "redraw for 2026, so layer 0 and the 119th's layer 4 carry the same "
            "four districts with the same land area (measured 2026-10-13)."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-ar-congress-roster.yml.",
    },
    {
        "layer": "ar-senate",
        "app_file": "ar-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": "35 Senate districts pre-built from TIGERweb (SLDU) by ar/scripts/build_legislative_boundaries.py; re-run after each redistricting.",
    },
    {
        "layer": "ar-house",
        "app_file": "ar-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": "100 House districts pre-built from TIGERweb (SLDL) by ar/scripts/build_legislative_boundaries.py; re-run after each redistricting.",
    },
    {
        "layer": "ar-senate",
        "app_file": "ar-senate-members.json",
        "source_url": "https://www.arkleg.state.ar.us/Legislators/List",
        "note": (
            "The Arkansas State Legislature's own member list, plus every "
            "member's own page, which is the only place a departed member is "
            "marked Resigned or Deceased; rebuilt weekly by "
            "ar/scripts/build_ar_legislature_roster.py. The member pages also "
            "print a telephone, which ships as printed (Adam, 2026-10-17), and "
            "a mailing address that may be a home, which the builder never "
            "reads."
        ),
    },
    {
        "layer": "ar-house",
        "app_file": "ar-house-members.json",
        "source_url": "https://www.arkleg.state.ar.us/Legislators/List",
        "note": "The same member list and pages as the Senate's, read by the same builder.",
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "All 75 counties pre-built from TIGERweb by "
            "ar/scripts/build_state_counties.py. The card names the county "
            "judge and the justices of the peace from ar-county-officials.json."
        ),
    },
    {
        "layer": "quorum-court",
        "app_file": "ar-quorum-court-districts.json",
        "source_url": "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Boundaries/FeatureServer/19",
        "note": (
            "All 775 justice of the peace districts in 75 counties, pre-built "
            "from the state's own statewide layer (credited to the Secretary of "
            "State) by ar/scripts/build_ar_quorum_court_districts.py. "
            "update-ar-county-officials.yml compares the live layer with the "
            "fingerprint recorded at build time every week and opens an issue "
            "when a county redraws; this check only says the layer still "
            "answers. Layer 55 of the same service is the 2011 plan and is not "
            "read."
        ),
    },
    {
        "layer": "county-subdivision",
        "app_file": "ar-townships.json",
        "source_url": "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Boundaries/FeatureServer/57",
        "note": (
            "All 820 townships in 75 counties, pre-built from the state's own "
            "TOWNSHIP_POLITICAL_DIVISION layer by "
            "ar/scripts/build_ar_townships.py rather than from the Census, "
            "whose township map of Arkansas disagrees with the state's about "
            "how many townships a county has in 27 counties (2026-10-15). The "
            "layer carries no edit date, so build_ar_townships.py --watch, the "
            "annual row in ar/WATCH.md, is what notices a county court "
            "redrawing; this check only says the layer still answers."
        ),
    },
    {
        "layer": "county",
        "app_file": "ar-county-officials.json",
        "source_url": "https://arcourts.gov/directories/county-judge-clerk",
        "note": (
            "The Arkansas Judiciary's directory of county judges and clerks, "
            "which names all 75 county judges; rebuilt weekly by "
            "ar/scripts/build_ar_county_officials.py."
        ),
    },
    {
        "layer": "quorum-court",
        "app_file": "ar-county-officials.json",
        "source_url": "https://arcounties.org/counties/",
        "note": (
            "The Association of Arkansas Counties' county pages, which list "
            "each county's justices of the peace without numbering them; read "
            "by the same builder at the 20 seconds a page the association's "
            "robots.txt asks."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "The coverage wash, dissolved from all 75 counties by "
            "ar/scripts/build_metro_outline.py -- 1 ring, 2,197 vertices, "
            "measured rather than predicted. Its --check is offline and holds "
            "the shipped file to one verified-interior INSIDE anchor per county "
            "(75 of 75 correct) plus eleven OUTSIDE anchors over the state line."
        ),
    },
    {
        "layer": "voting-precinct",
        "app_file": "ar-precincts.json",
        "source_url": "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Boundaries/FeatureServer/11",
        "note": (
            "Arkansas's 2,920 voting precincts from the Arkansas GIS Office's "
            "statewide layer of what each county reports (2,928 records: "
            "seven precincts are published in pieces and joined), pre-built "
            "by ar/scripts/build_ar_precincts.py through "
            "scripts/statewide_precincts.py; the quarterly --watch row in "
            "ar/WATCH.md compares the fingerprint recorded at the build."
        ),
    },
    {
        "layer": "school-board-district",
        "app_file": "ar-school-board-zones.json",
        "source_url": "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Boundaries/FeatureServer/32",
        "note": (
            "965 school board zones on 176 school districts from the Arkansas "
            "GIS Office's SCHOOL_BOARD_ZONES layer, which the Secretary of "
            "State compiles (966 records: Jasper's zone 3 is published in two "
            "pieces and joined), pre-built by "
            "ar/scripts/build_ar_school_board_districts.py through "
            "scripts/published_district_layers.py; the quarterly "
            "--watch row in ar/WATCH.md compares the fingerprint recorded at "
            "the build, and the eight boards changing to at large are re-read "
            "whenever their zones move."
        ),
    },
    {
        "layer": "ar-court-of-appeals",
        "app_file": "ar-appeals-districts.json",
        "source_url": "https://gis.arkansas.gov/Metadata/HTML/asdi.Boundaries.APPEALS_COURT_export.html",
        "note": (
            "The Court of Appeals' 7 districts, dissolved from the county "
            "fabric by ar/scripts/build_ar_court_districts.py following Act "
            "1812 of 2003 as this metadata page quotes it (read 2026-10-16; "
            "snapshot in ar/data/source/courts/), held county by county to "
            "the GIS Office's Appeals Court Districts layer. The official "
            "Code is not readable here: its copy is LexisNexis's. The re-read "
            "is a row in ar/WATCH.md."
        ),
    },
    {
        "layer": "ar-circuit-court",
        "app_file": "ar-judicial-circuits.json",
        "source_url": "https://arcourts.gov/directories/circuit-judges",
        "note": (
            "The 28 judicial circuits, dissolved from the county fabric by "
            "ar/scripts/build_ar_court_districts.py following the "
            "Administrative Office of the Courts' circuit judge directory "
            "(read 2026-10-16; county-level extract in "
            "ar/data/source/courts/), held county by county to the GIS "
            "Office's Circuit Court Districts layer. A circuit gains a judge "
            "by act; the re-read is a row in ar/WATCH.md."
        ),
    },
]

ENDPOINTS = [
    # The live layers -- no builder, no committed data/app file -- so a vintage
    # roll reaches them on its own and there is nothing here to rebuild. What
    # this list watches is the endpoint still ANSWERING FOR ARKANSAS: a
    # returnCountOnly query per layer, so a service moved, renamed or silently
    # emptied for this state surfaces as a WARN instead of as cards that quietly
    # stop resolving.
    #
    # The counts below are measured 2026-10-13 and are RECORDED, not asserted:
    # this validator reports, it never edits the app. Incorporated places 501 ·
    # unified school districts 234.
    #
    # SCHOOL LAYERS 1 (SECONDARY) AND 2 (ELEMENTARY) ANSWER ZERO FOR ARKANSAS,
    # measured the same day; the unified layer covers the state alone. Neither
    # is watched -- a row whose count is zero on purpose cannot tell a drop
    # from the status quo.
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2705%27&returnCountOnly=true&f=json",
        "min_count": 450,   # 501 measured 2026-10-13; floor set below it, not at it
    },
    {
        "layer": "school-district-unified",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0/query?where=STATE%3D%2705%27&returnCountOnly=true&f=json",
        "min_count": 210,   # 234 measured 2026-10-13
    },
    # USGS structures, counted rather than fetched, because the count is the
    # thing at risk: the service caps a response at 2,000 records and says so
    # with HTTP 200 + exceededTransferLimit rather than an error. min_count is
    # what makes each row a real tripwire rather than a ping.
    #
    # returnCountOnly IS NOT SUBJECT TO maxRecordCount, so none of these rows can
    # see the client truncating. What catches a broken pager is the browser gate
    # -- ar/scripts/smoke_test.mjs asserts the loader makes more than one
    # request and that the second page's station reaches the card.
    #
    # Counted over the app's own envelope (METRO_BBOX, -94.62,33.0,-89.64,36.5),
    # which reaches into the neighbouring states where the border is not
    # straight, so these are the counts the app downloads rather than the
    # state's exact totals.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query"
                "?geometry=-94.62%2C33.0%2C-89.64%2C36.5&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 730,   # 812 measured 2026-10-13
    },
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query"
                "?geometry=-94.62%2C33.0%2C-89.64%2C36.5&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 1450,  # 1,619 measured 2026-10-13 -- within 381 of the 2,000 cap
    },
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query"
                "?geometry=-94.62%2C33.0%2C-89.64%2C36.5&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 470,   # 522 measured 2026-10-13
    },
    # ZCTAs carry NO STATE field, so this one is counted by ENVELOPE, in Esri's
    # own comma form -- the {minLng,...} shape makes TIGERweb answer HTTP 200
    # with a JSON error envelope. min_count is what makes this a real check
    # rather than a reachability ping.
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query?where=1%3D1"
                "&geometry=-94.70%2C32.95%2C-89.55%2C36.55&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 850,   # 942 measured 2026-10-13
    },
    # The precinct layer the builder reads (2026-10-15). A floor rather than
    # the exact count: the quarterly --watch in ar/WATCH.md is what notices a
    # changed precinct; this row notices the query failing or the layer emptying.
    {
        "layer": "voting-precinct",
        "url": ("https://gis.arkansas.gov/arcgis/rest/services/"
                "FEATURESERVICES/Boundaries/FeatureServer/11/query?where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 2630,  # 2,928 records measured 2026-10-15
    },
    # The school board zone layer the builder reads (2026-10-16). A floor, for
    # the reason the precinct row above gives.
    {
        "layer": "school-board-district",
        "url": ("https://gis.arkansas.gov/arcgis/rest/services/"
                "FEATURESERVICES/Boundaries/FeatureServer/32/query?where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 870,   # 966 records measured 2026-10-16
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
    ua = "districtry source validator (+https://districtry.com/ar/)"
    try:
        require_robots_once(url, ua, headers={"User-Agent": ua},
                            label="ar-validate-sources")
    except SystemExit:
        # require_robots_once prints why and exits on a refusal or an
        # unreadable policy. Here that is one source's finding rather than the
        # end of the run, and nothing is fetched from the host either way.
        return False, "robots.txt refuses this client or could not be read (the reason is printed above); nothing fetched"
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": ua},
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
                         "out of sync with the app (update ar/scripts/validate_sources.py)"
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
              "`pip install -c ar/scripts/requirements.txt requests`", file=sys.stderr)
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
