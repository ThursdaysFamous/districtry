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
    exists. Nothing errors; the data just quietly goes stale. Georgia's
    instance reads no Socrata portal, so that list is empty here.
  * Pre-built boundary layers were downloaded at build time: the congressional
    and both chambers' maps from the General Assembly's Legislative and
    Congressional Reapportionment Office, the counties from TIGERweb. The check
    there is provenance: is the source we cite still reachable, and is it
    still the plan the shipped file was drawn from.

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
     answering for Georgia, with a count at or above its floor.            [WARN]
  5. The congressional map: congress-districts.json is the 2023 plan, which
     elected the 119th Congress and, with no redraw in 2026, elects the 120th
     too, so it is right until noon on 3 January 2029. From 1 December 2028
     this check says so every month.                                      [WARN]
  6. The three plans: the Reapportionment Office's page still lists each
     pinned shapefile under the plan it was chosen as — the builder's own
     --check-listing, so a replaced plan is read by a person a month after it
     appears rather than on the day somebody rebuilds.                    [WARN]

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/ga-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 ga/scripts/validate_sources.py                 # human-readable report
    python3 ga/scripts/validate_sources.py --report r.md   # also write markdown
    python3 ga/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 ga/scripts/validate_sources.py --offline       # manifest↔app checks only
"""

import argparse
import datetime
import os
import re
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(_HERE)),
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

# The freshness gate's source manifest for the Georgia instance. Every
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
        "source_url": "https://www.legis.ga.gov/joint-office/reapportionment",
        "note": (
            "14 congressional districts pre-built from the General Assembly's "
            "own shapefile of the plan passed on 7 December 2023 (Senate Bill "
            "3EX) by ga/scripts/build_legislative_boundaries.py, pinned by "
            "SHA-256. TIGERweb's layers 0 (120th Congress) and 4 (119th) carry "
            "the same plan for Georgia, measured 2026-10-29: a June 2026 "
            "special session declined to redraw, so the 3 November 2026 "
            "election uses it. Check 5 below says when the map has to change."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-ga-congress-roster.yml.",
    },
    {
        "layer": "ga-senate",
        "app_file": "ga-senate-districts.json",
        "source_url": "https://www.legis.ga.gov/joint-office/reapportionment",
        "note": (
            "56 Senate districts pre-built from the General Assembly's own "
            "shapefile of the plan passed on 5 December 2023 (Senate Bill 1EX). "
            "Measured 2026-10-29 against TIGERweb's copy, 99.9959% of the "
            "plan's area is in the same district; the difference is the "
            "Census Bureau's moved Lumpkin-Union county line, and the act "
            "defines its districts on the 2020 census's geography. Check 6 "
            "below watches the office's listing for a replacement."
        ),
    },
    {
        "layer": "ga-house",
        "app_file": "ga-house-districts.json",
        "source_url": "https://www.legis.ga.gov/joint-office/reapportionment",
        "note": (
            "180 House districts pre-built from the General Assembly's own "
            "shapefile of the plan passed on 5 December 2023 (House Bill 1EX), "
            "by the same builder; 99.9925% of the plan's area in the same "
            "district as TIGERweb's copy."
        ),
    },
    {
        "layer": "ga-senate",
        "app_file": "ga-senate-members.json",
        "source_url": "https://www.legis.ga.gov/members/senate",
        "note": (
            "The General Assembly's own member data, which this page reads "
            "through the token it hands every visitor; rebuilt weekly by "
            "ga/scripts/build_ga_legislature_roster.py."
        ),
    },
    {
        "layer": "ga-house",
        "app_file": "ga-house-members.json",
        "source_url": "https://www.legis.ga.gov/members/house",
        "note": "The same member data, for the House; rebuilt weekly by the same builder.",
    },
    {
        "layer": "county",
        "app_file": "ga-county-officials.json",
        "source_url": "https://results.sos.ga.gov/results/public/api/jurisdictions/Georgia",
        "note": (
            "County commissioners and county school board members, named from "
            "the Secretary of State's official election results (county "
            "contests from 5 November 2024 on) by "
            "ga/scripts/build_ga_county_officials.py; refreshed weekly by "
            "update-ga-county-officials.yml. This is the site's list of "
            "elections, which the builder reads first."
        ),
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "All 159 counties pre-built from TIGERweb by "
            "ga/scripts/build_state_counties.py (Douglas-Peucker at 5 m, held "
            "to an 8 m fidelity ceiling)."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "The coverage wash, dissolved from all 159 counties by "
            "ga/scripts/build_metro_outline.py -- 1 ring, 4,295 vertices, "
            "measured rather than predicted. Its --check is offline and holds "
            "the shipped file to one INSIDE anchor per county (159 of 159 "
            "correct) plus 20 OUTSIDE anchors over the state line."
        ),
    },
    {
        "layer": "voting-precinct",
        "app_file": "ga-precincts.json",
        "source_url": "https://www.legis.ga.gov/joint-office/reapportionment",
        "note": (
            "Georgia's 2,724 voting precincts from the Reapportionment "
            "Office's statewide precinct map for 2024, which this page lists; "
            "pre-built by ga/scripts/build_ga_precincts.py through "
            "scripts/statewide_precincts.py, which pins the file by address "
            "and SHA-256. The page is checked rather than the file because "
            "the file is a 16 MB zip; the quarterly --watch row in "
            "ga/WATCH.md reads the listing for a newer map and the file for "
            "a changed one."
        ),
    },
    {
        "layer": "county-commissioner",
        "app_file": "ga-commission-districts.json",
        "source_url": "https://www.legis.ga.gov/joint-office/reapportionment",
        "note": (
            "County commission districts from the Reapportionment Office's "
            "county maps, drawn by ga/scripts/build_ga_board_districts.py only "
            "where ga/scripts/check_ga_county_maps.py found the county's own "
            "district elections agree with the map; each file is pinned by "
            "SHA-256 in ga/data/source/county-map-check.json."
        ),
    },
    {
        "layer": "school-board-district",
        "app_file": "ga-school-board-districts.json",
        "source_url": "https://www.legis.ga.gov/joint-office/reapportionment",
        "note": "The same office's county school board maps, by the same builder and check.",
    },
    {
        "layer": "ga-superior-court",
        "app_file": "ga-judicial-circuits.json",
        "source_url": "https://results.sos.ga.gov/results/public/api/jurisdictions/Georgia",
        "note": (
            "The 51 judicial circuits, each drawn from whole counties of "
            "state-counties.json by ga/scripts/build_ga_superior_courts.py "
            "--draw. Which circuit a county is in comes from its newest "
            "official ballot carrying a court contest, so the source to watch "
            "is the results site; the weekly run stops if a newer ballot moves "
            "a county."
        ),
    },
    {
        "layer": "ga-superior-court",
        "app_file": "ga-circuit-officials.json",
        "source_url": "https://georgiacourts.knack.com/gcd2/",
        "note": (
            "Each circuit's judges and district attorney, named from the "
            "Secretary of State's official election results by "
            "ga/scripts/build_ga_superior_courts.py and refreshed weekly by "
            "update-ga-county-officials.yml. The URL is the Administrative "
            "Office of the Courts' directory of judges and court officers, "
            "which the builder reads as a check (it places a split circuit's "
            "judges and holds back a person it lists in another office), "
            "watched here so a moved or retired directory surfaces."
        ),
    },
]

# Georgia's envelope, as index.html writes it for the ZIP layer
# (GA_BBOX_ENVELOPE, Esri's {xmin,...} form) and for the USGS layers
# (METRO_BBOX, generated from the worksheet's metro_bbox). The two are the same
# four numbers in this instance and these rows count over them, so each row
# names the literal its loader reads, and check 1 fails when either moves.
ZIP_ENVELOPE_LITERAL = "xmin: -85.61, ymin: 30.35, xmax: -80.78, ymax: 35.01"
USGS_ENVELOPE_LITERAL = "minLng: -85.61, minLat: 30.35, maxLng: -80.78, maxLat: 35.01"
ENVELOPE_QUERY = ("&geometry=-85.61%2C30.35%2C-80.78%2C35.01&geometryType=esriGeometryEnvelope"
                  "&inSR=4326&spatialRel=esriSpatialRelIntersects")

ENDPOINTS = [
    # The live layers -- no builder, no committed data/app file -- so a vintage
    # roll reaches them on its own and there is nothing here to rebuild. What
    # this list watches is the endpoint still ANSWERING FOR GEORGIA: a
    # returnCountOnly query per layer, so a service moved, renamed or silently
    # emptied for this state surfaces as a WARN instead of as cards that quietly
    # stop resolving.
    #
    # The counts below are measured 2026-10-29 and are RECORDED, not asserted:
    # this validator reports, it never edits the app. Incorporated places 538 ·
    # county subdivisions 586 · unified school districts 181.
    #
    # SCHOOL LAYERS 1 AND 2 ARE NOT WATCHED: the app draws only the unified
    # districts, which cover Georgia but Fort Benning, whose own schools the
    # Census maps as the one elementary district.
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2713%27&returnCountOnly=true&f=json",
        "min_count": 485,   # 538 measured 2026-10-29; floor set below it, not at it
    },
    {
        "layer": "county-subdivision",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/1/query?where=STATE%3D%2713%27&returnCountOnly=true&f=json",
        "min_count": 525,   # 586 measured 2026-10-29
    },
    {
        "layer": "school-district-unified",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0/query?where=STATE%3D%2713%27&returnCountOnly=true&f=json",
        "min_count": 165,   # 181 measured 2026-10-29
    },
    # USGS structures, counted rather than fetched, because the count is the
    # thing at risk: the service caps a response at 2,000 records and says so
    # with HTTP 200 + exceededTransferLimit rather than an error. min_count is
    # what makes each row a real tripwire rather than a ping.
    #
    # returnCountOnly IS NOT SUBJECT TO maxRecordCount, so none of these rows can
    # see the client truncating. What catches a broken pager is the browser gate
    # -- ga/scripts/smoke_test.mjs asserts the loader makes more than one
    # request and that the second page's station reaches the card. Georgia's
    # fire and EMS stations are the one count here OVER the cap (2,657), so
    # that layer needs the pager on every load.
    #
    # Counted over the app's own envelope (METRO_BBOX, -85.61,30.35,-80.78,35.01),
    # which reaches into Alabama, Florida, South Carolina, North Carolina and
    # Tennessee where the border is not straight, so these are the counts the
    # app downloads rather than the state's exact totals.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query"
                "?where=1%3D1" + ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 960,   # 1,069 measured 2026-10-29
        "envelope": USGS_ENVELOPE_LITERAL,
    },
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query"
                "?where=1%3D1" + ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 2390,  # 2,657 measured 2026-10-29 -- over the 2,000 cap, so paged
        "envelope": USGS_ENVELOPE_LITERAL,
    },
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query"
                "?where=1%3D1" + ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 740,   # 826 measured 2026-10-29
        "envelope": USGS_ENVELOPE_LITERAL,
    },
    # ZCTAs carry NO STATE field, so this one is counted by ENVELOPE, in Esri's
    # own comma form -- the {minLng,...} shape makes TIGERweb answer HTTP 200
    # with a JSON error envelope. min_count is what makes this a real check
    # rather than a reachability ping. The envelope is the app's own
    # (GA_BBOX_ENVELOPE in index.html).
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query"
                "?where=1%3D1" + ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 1080,  # 1,202 measured 2026-10-29
        "envelope": ZIP_ENVELOPE_LITERAL,
    },
]

# Check 5's dates. The builder (ga/scripts/build_legislative_boundaries.py)
# holds the same date as the us-house entry's serving_until, and refuses a
# rebuild once it has passed.
CONGRESS_SERVING_UNTIL = "2029-01-03"
CONGRESS_WARN_FROM = "2028-12-01"

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
    ua = "districtry source validator (+https://districtry.com/ga/)"
    try:
        require_robots_once(url, ua, headers={"User-Agent": ua},
                            label="ga-validate-sources")
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
                         "out of sync with the app (update ga/scripts/validate_sources.py)"
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
        # The envelope is the app's own, so a change to one side is drift.
        if e.get("envelope") and e["envelope"] not in html:
            findings.add(FAIL, e["layer"],
                         "index.html no longer carries the envelope this check counts "
                         "%s over (%s) — update the endpoint row with the app's new one"
                         % (e["layer"], e["envelope"]))


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
                     "the members elected on Georgia's 2023 map left office at noon on "
                     "3 January 2029. If the General Assembly redrew for 2028, the 2028 "
                     "election was held on the new map: re-read which map the sitting "
                     "members were elected from, rebuild congress-districts.json from the "
                     "office's file of it, and change the us-house entry in "
                     "ga/scripts/build_legislative_boundaries.py — ga/WATCH.md has the steps")
    elif today >= CONGRESS_WARN_FROM:
        findings.add(WARN, "us-house",
                     "the members elected on Georgia's 2023 map leave office at noon on "
                     "3 January 2029; congress-districts.json is right until then and must "
                     "be re-read that day — ga/WATCH.md has the steps")


# ---- check 6: the three plans are still the ones the office lists -----------
def check_plan_listing(findings, offline):
    """The builder's own --check-listing: the Reapportionment Office's page
    (read through the token the page hands every visitor) still lists each
    pinned shapefile, at the pinned version, under the plan it was chosen as.
    It prints one line per plan and exits on a miss; both are folded into one
    finding here rather than ending the run."""
    if offline:
        return
    import contextlib  # noqa: PLC0415
    import io  # noqa: PLC0415
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import build_legislative_boundaries as blb  # noqa: PLC0415 (same instance tree)
    except Exception as e:  # requests or pyshp missing, say
        findings.add(WARN, "ga-house", "the plan listing could not be checked (%s)" % e)
        return
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            blb.check_listing()
    except SystemExit as e:
        findings.add(WARN, "ga-house",
                     "the Reapportionment Office's page no longer lists every pinned plan "
                     "as it was chosen (%s). The shipped files are unchanged, but read "
                     "what replaced the plan before drawing it. %s"
                     % (e, out.getvalue().strip().replace("\n", "; ")))
        return
    except Exception as e:
        findings.add(WARN, "ga-house", "the plan listing could not be read (%s)" % e)
        return
    findings.add(OK, "ga-house",
                 "the Reapportionment Office still lists every pinned plan: %s"
                 % out.getvalue().strip().replace("\n", "; "))


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
              "`pip install -c ga/scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    check_manifest_matches_app(html, findings)
    check_socrata(findings, args.offline)
    check_provenance(findings, args.offline)
    check_endpoints(findings, args.offline)
    check_congress_map(findings, args.offline)
    check_plan_listing(findings, args.offline)

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
