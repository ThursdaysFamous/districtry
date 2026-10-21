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
    exists. Nothing errors; the data just quietly goes stale. Louisiana's
    instance reads no Socrata portal, so that list is empty here.
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
  4. Live service endpoints (Census TIGERweb, the USGS National Map):
     answering for Louisiana, with a count at or above its floor.          [WARN]
  5. The congressional map: congress-districts.json is the 119th Congress's,
     which is right until noon on 3 January 2027 and wrong after it. From
     1 December 2026 this check says so every month; it also says so if
     TIGERweb's layer 4 is no longer the 119th Congress's map, since the
     builder would then refuse to rebuild it.                             [WARN]

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/la-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 la/scripts/validate_sources.py                 # human-readable report
    python3 la/scripts/validate_sources.py --report r.md   # also write markdown
    python3 la/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 la/scripts/validate_sources.py --offline       # manifest↔app checks only
"""

import argparse
import datetime
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

# The freshness gate's source manifest for the Louisiana instance. Every
# layer this instance adds gets its rows here in the same change (CLAUDE.md's
# conventions; the reference repo's validate_sources.py shows a mature
# manifest's full shape, including year-search patterns and the `blocked`
# inversion).
SOCRATA_DOMAIN = "data.invalid"  # this instance reads no Socrata portal
CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"

# Socrata dataset ids the app hardcodes (none).
SOCRATA = []

# Same-origin data/app files and the upstream source each was built from.
PROVENANCE = [
    {
        "layer": "us-house",
        "app_file": "congress-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/4",
        "note": (
            "6 congressional districts pre-built from TIGERweb's layer 4, the "
            "119th Congress's map, by la/scripts/build_legislative_boundaries.py. "
            "LAYER 4 AND NOT LAYER 0, ON PURPOSE: Louisiana redrew for 2026 "
            "(Act 2 of 2026) and layer 0 already carries that map, while the six "
            "members congress-roster.json names were elected from the 2024 map "
            "and serve until noon on 3 January 2027. Measured 2026-10-20 against "
            "the legislature's own shapefile of the 2024 plan, layer 4 matches "
            "every district at IoU 0.99999 or better and layer 0 keeps 76.66% of "
            "the plan's area in the same-numbered district. Check 5 below says "
            "when the map has to change."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-la-congress-roster.yml.",
    },
    {
        "layer": "la-senate",
        "app_file": "la-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": (
            "39 Senate districts pre-built from TIGERweb (SLDU) by "
            "la/scripts/build_legislative_boundaries.py: the plan of the 2022 "
            "First Extraordinary Session, which the sitting senators were "
            "elected from. Act 955 of 2026 moves precincts between Districts "
            "33, 34 and 35 from the 2027 election on; re-run then."
        ),
    },
    {
        "layer": "la-house",
        "app_file": "la-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": "105 House districts pre-built from TIGERweb (SLDL) by la/scripts/build_legislative_boundaries.py; re-run after each redistricting.",
    },
    {
        "layer": "la-senate",
        "app_file": "la-senate-members.json",
        "source_url": "https://senate.la.gov/Senators_FullInfo",
        "note": (
            "The Senate's own member list, plus every member's own page; "
            "rebuilt weekly by la/scripts/build_la_legislature_roster.py. The "
            "pages also name a legislative assistant and a fax number, which "
            "the builder never reads."
        ),
    },
    {
        "layer": "la-house",
        "app_file": "la-house-members.json",
        "source_url": "https://house.louisiana.gov/H_Reps/H_Reps_FullInfo",
        "note": "The House's own member list and member pages, read by the same builder.",
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "All 64 parishes pre-built from TIGERweb by "
            "la/scripts/build_state_counties.py (Douglas-Peucker at 5 m, held "
            "to an 8 m fidelity ceiling). The card names each parish's "
            "governing body from la-parish-officials.json."
        ),
    },
    {
        "layer": "county",
        "app_file": "la-parish-officials.json",
        "source_url": "https://voterportal.sos.la.gov/ElectedOfficials/Office/Index",
        "note": (
            "The Secretary of State's list of elected officials, read as three "
            "CSV exports (police jurors and the other district members, "
            "councilmen at large, parish presidents); rebuilt weekly by "
            "la/scripts/build_la_parish_officials.py. The rows also print a "
            "mailing address, the official's race and gender; the race and "
            "gender are never read, and an address ships only as a body's "
            "office, where three members print it and no official outside the "
            "body does."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "la-municipal-officials.json",
        "source_url": "https://voterportal.sos.la.gov/ElectedOfficials/Office/Index",
        "note": (
            "The same list's Mayor, Alderman / City Council Member, Alderman / "
            "City Council at Large and Chief of Police / Marshal exports, keyed "
            "by the Census place each municipality's name matches; rebuilt "
            "weekly from the parish builder's saved exports by "
            "la/scripts/build_la_local_officials.py. 302 municipalities on "
            "2026-10-20; the race and gender columns are never read."
        ),
    },
    {
        "layer": "school-district-unified",
        "app_file": "la-school-board-members.json",
        "source_url": "https://voterportal.sos.la.gov/ElectedOfficials/Office/Index",
        "note": (
            "The same list's School Board Member export, keyed by the Census "
            "school district; built in the same run, which refuses unless all "
            "69 districts have a board. 610 of the 639 members' terms end on "
            "31 December 2026, so read it again in January 2027."
        ),
    },
    {
        "layer": "parish-district",
        "app_file": "la-parish-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/22",
        "note": (
            "The districts of the 6 parishes whose current lines are "
            "confirmed, pre-built from the Census's county subdivisions "
            "(January 1, 2026 vintage) by "
            "la/scripts/build_la_parish_districts.py. A parish is drawn when its "
            "lines changed after the 2020 census and balance on that census's "
            "own blocks; --survey re-measures all 64, and a new vintage needs a "
            "survey and a rebuild."
        ),
    },
    {
        "layer": "parish-district",
        "app_file": "la-parish-district-parishes.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/22",
        "note": "The list of drawn parishes the layer's coverage test reads, written by the same build.",
    },
    {
        "layer": "voting-precinct",
        "app_file": "la-precincts.json",
        "source_url": "https://redist.legis.la.gov/default_ShapeFiles2020",
        "note": (
            "Louisiana's 3,569 voting precincts from the Legislature's "
            "statewide precinct file, its edition of 27 January 2026, listed on "
            "this page with every earlier edition; pre-built by "
            "la/scripts/build_la_precincts.py through "
            "scripts/statewide_precincts.py, which leaves out the file's five "
            "areas of Lake Pontchartrain in no voting district. The page is "
            "checked rather than the file because the file is a 16 MB zip; "
            "the quarterly --watch row in la/WATCH.md reads the page for a "
            "newer edition and the file for a changed one."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "The coverage wash, dissolved from all 64 parishes by "
            "la/scripts/build_metro_outline.py -- 1 ring, 3,984 vertices, "
            "measured rather than predicted. Its --check is offline and holds "
            "the shipped file to one INSIDE anchor per parish (64 of 64 correct) "
            "plus twelve OUTSIDE anchors over the state line."
        ),
    },
]

ENDPOINTS = [
    # The live layers -- no builder, no committed data/app file -- so a vintage
    # roll reaches them on its own and there is nothing here to rebuild. What
    # this list watches is the endpoint still ANSWERING FOR LOUISIANA: a
    # returnCountOnly query per layer, so a service moved, renamed or silently
    # emptied for this state surfaces as a WARN instead of as cards that quietly
    # stop resolving.
    #
    # The counts below are measured 2026-10-20 and are RECORDED, not asserted:
    # this validator reports, it never edits the app. Incorporated places 305 ·
    # unified school districts 69.
    #
    # SCHOOL LAYERS 1 (SECONDARY) AND 2 (ELEMENTARY) ANSWER ZERO FOR
    # LOUISIANA, measured the same day; the unified layer covers the state
    # alone. Neither is watched -- a row whose count is zero on purpose cannot
    # tell a drop from the status quo.
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2722%27&returnCountOnly=true&f=json",
        "min_count": 275,   # 305 measured 2026-10-20; floor set below it, not at it
    },
    {
        "layer": "school-district-unified",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0/query?where=STATE%3D%2722%27&returnCountOnly=true&f=json",
        "min_count": 62,    # 69 measured 2026-10-20
    },
    # USGS structures, counted rather than fetched, because the count is the
    # thing at risk: the service caps a response at 2,000 records and says so
    # with HTTP 200 + exceededTransferLimit rather than an error. min_count is
    # what makes each row a real tripwire rather than a ping.
    #
    # returnCountOnly IS NOT SUBJECT TO maxRecordCount, so none of these rows can
    # see the client truncating. What catches a broken pager is the browser gate
    # -- la/scripts/smoke_test.mjs asserts the loader makes more than one
    # request and that the second page's station reaches the card.
    #
    # Counted over the app's own envelope (METRO_BBOX, -94.05,28.85,-88.75,33.02),
    # which reaches into Texas, Arkansas and Mississippi where the border is not
    # straight, so these are the counts the app downloads rather than the
    # state's exact totals.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query"
                "?geometry=-94.05%2C28.85%2C-88.75%2C33.02&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 645,   # 717 measured 2026-10-20
    },
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query"
                "?geometry=-94.05%2C28.85%2C-88.75%2C33.02&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 1500,  # 1,675 measured 2026-10-20 -- within 325 of the 2,000 cap
    },
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query"
                "?geometry=-94.05%2C28.85%2C-88.75%2C33.02&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 470,   # 522 measured 2026-10-20
    },
    # ZCTAs carry NO STATE field, so this one is counted by ENVELOPE, in Esri's
    # own comma form -- the {minLng,...} shape makes TIGERweb answer HTTP 200
    # with a JSON error envelope. min_count is what makes this a real check
    # rather than a reachability ping. The envelope is the app's own
    # (LA_BBOX_ENVELOPE in index.html).
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query?where=1%3D1"
                "&geometry=-94.15%2C28.75%2C-88.65%2C33.12&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 750,   # 831 measured 2026-10-20
    },
]

# Check 5's dates and the layer the congressional file is drawn from. The
# builder (la/scripts/build_legislative_boundaries.py) holds the same name and
# date, and refuses a rebuild once either stops being true.
CONGRESS_LAYER_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/4?f=json"
CONGRESS_LAYER_NAME = "119th Congressional Districts"
CONGRESS_SERVING_UNTIL = "2027-01-03"
CONGRESS_WARN_FROM = "2026-12-01"

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
    ua = "districtry source validator (+https://districtry.com/la/)"
    try:
        require_robots_once(url, ua, headers={"User-Agent": ua},
                            label="la-validate-sources")
    except SystemExit:
        # require_robots_once has printed why and exits on a refusal or an
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
                         "out of sync with the app (update la/scripts/validate_sources.py)"
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
    for e in ENDPOINTS:
        # The ZIP envelope is the app's own, so a change to one side is drift.
        if e["layer"] == "zip-code" and "-94.15, ymin: 28.75, xmax: -88.65, ymax: 33.12" not in html:
            findings.add(FAIL, e["layer"],
                         "index.html's LA_BBOX_ENVELOPE no longer matches the envelope this "
                         "check counts ZCTAs over — update the endpoint row with it")


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


# ---- check 5: the congressional map is still the one the members sit for ----
def check_congress_map(findings, offline, today=None):
    today = today or datetime.date.today().isoformat()
    if today >= CONGRESS_SERVING_UNTIL:
        findings.add(WARN, "us-house",
                     "the members congress-districts.json was drawn for left office at noon "
                     "on 3 January 2027. Rebuild it from TIGERweb's layer named '120th "
                     "Congressional Districts' (its CD120 field), drop layer_name and "
                     "serving_until in la/scripts/build_legislative_boundaries.py, and check "
                     "the weekly roster has the new members — la/WATCH.md has the steps")
    elif today >= CONGRESS_WARN_FROM:
        findings.add(WARN, "us-house",
                     "the 120th Congress takes office at noon on 3 January 2027 on the map "
                     "Louisiana drew for 2026; congress-districts.json is the 119th's until "
                     "then and must be rebuilt that day — la/WATCH.md has the steps")
    if offline:
        return
    ok, res = http_get(CONGRESS_LAYER_URL)
    if not ok:
        findings.add(WARN, "us-house", "TIGERweb's Legislative layer 4 is not reachable (%s)" % res)
        return
    name = res.get("name", "") if isinstance(res, dict) else ""
    if name != CONGRESS_LAYER_NAME:
        findings.add(WARN, "us-house",
                     "TIGERweb's Legislative layer 4 is now %r, not %r: the shipped file is "
                     "unchanged, but la/scripts/build_legislative_boundaries.py would refuse to "
                     "rebuild it until its layer table names the layer that carries the 119th "
                     "Congress's map" % (name, CONGRESS_LAYER_NAME))
    else:
        findings.add(OK, "us-house", "TIGERweb's Legislative layer 4 is still %r" % name)


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
              "`pip install -c la/scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    check_manifest_matches_app(html, findings)
    check_socrata(findings, args.offline)
    check_provenance(findings, args.offline)
    check_endpoints(findings, args.offline)
    check_congress_map(findings, args.offline)

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
