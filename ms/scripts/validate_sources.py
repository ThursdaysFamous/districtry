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
workflow (.github/workflows/ms-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 ms/scripts/validate_sources.py                 # human-readable report
    python3 ms/scripts/validate_sources.py --report r.md   # also write markdown
    python3 ms/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 ms/scripts/validate_sources.py --offline       # manifest↔app checks only
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
import aia_bundle  # noqa: E402  (FLEET_SHARED — the one copy of the pins)

try:
    import requests
except ImportError:  # pragma: no cover - requests is pinned in requirements.txt
    requests = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

HTTP_TIMEOUT = 25

# The freshness gate's source manifest for the Mississippi instance. Every
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
            "ms/scripts/build_legislative_boundaries.py. THE DISTRICT FIELD IS "
            "VERSIONED AND THE OLD ONE IS REMOVED, NOT MERELY STALE: this layer "
            "is now '120th Congressional Districts' and its field is CD120; a "
            "query naming the retired CD119 is rejected outright with HTTP 400. "
            "On the next roll the builder's field list and the app's "
            "CONGRESS_DISTRICT_FIELDS both need the new name. Mississippi did "
            "not redraw for 2026, so layer 0 and the 119th's layer 4 carry the "
            "same four districts with the same land area (measured 2026-10-15)."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-ms-congress-roster.yml.",
    },
    {
        "layer": "ms-senate",
        "app_file": "ms-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": (
            "52 Senate districts pre-built from TIGERweb (SLDU) by "
            "ms/scripts/build_legislative_boundaries.py, carrying the lines a "
            "federal court ordered for the special elections of 4 November "
            "2025; re-run after each redistricting."
        ),
    },
    {
        "layer": "ms-house",
        "app_file": "ms-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": "122 House districts pre-built from TIGERweb (SLDL) by ms/scripts/build_legislative_boundaries.py; re-run after each redistricting.",
    },
    {
        "layer": "ms-senate",
        "app_file": "ms-senate-members.json",
        "source_url": "https://www.legislature.ms.gov/legislators/senators/",
        "note": (
            "The Mississippi Legislature's own member gallery, plus every "
            "member's own profile; rebuilt weekly by "
            "ms/scripts/build_ms_legislature_roster.py. The server sends only "
            "its own certificate, so this check reads it, robots.txt "
            "included, through the GlobalSign intermediate "
            "scripts/aia_bundle.py pins (PINNED_CHAINS above). The profiles "
            "also print a home address and personal telephone, which the "
            "builder never reads."
        ),
    },
    {
        "layer": "ms-house",
        "app_file": "ms-house-members.json",
        "source_url": "https://www.legislature.ms.gov/legislators/representatives/",
        "note": "The same gallery and profiles as the Senate's, read by the same builder.",
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "All 82 counties pre-built from TIGERweb by "
            "ms/scripts/build_state_counties.py (Douglas-Peucker, held to a "
            "25 m fidelity ceiling). The card names each county's five "
            "supervisors from ms-county-officials.json."
        ),
    },
    {
        "layer": "county-supervisor",
        "app_file": "ms-supervisor-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/22",
        "note": (
            "The supervisor districts of the 20 counties whose current lines "
            "are confirmed, pre-built by "
            "ms/scripts/build_ms_supervisor_districts.py: 12 from the Census's "
            "county subdivisions (January 1, 2026 vintage), where the lines "
            "changed after the 2020 census and balance on that census's own "
            "blocks, and 8 from the county's own map, redrawn along whole 2020 "
            "blocks (their layers are counted under ENDPOINTS below). --survey "
            "re-measures all 82, and a new vintage needs a survey and a "
            "rebuild, which stops if the Census has received a county's own "
            "lines."
        ),
    },
    {
        "layer": "county",
        "app_file": "ms-county-officials.json",
        "source_url": "https://www.sos.ms.gov/publications-external-affairs/publications/state-county-directory",
        "note": (
            "The Secretary of State's County Offices and Directory, published "
            "once a year (the 2026 edition is dated 6 May 2026); the builder "
            "finds each edition from this index page and reads the five "
            "supervisors of all 82 counties out of the PDF. Rebuilt weekly by "
            "ms/scripts/build_ms_county_officials.py, which changes nothing "
            "until a new edition appears."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "The coverage wash, dissolved from all 82 counties by "
            "ms/scripts/build_metro_outline.py -- 1 ring, 2,834 vertices, "
            "measured rather than predicted. Its --check is offline and holds "
            "the shipped file to one verified-interior INSIDE anchor per county "
            "(82 of 82 correct) plus eleven OUTSIDE anchors over the state line."
        ),
    },
]

ENDPOINTS = [
    # The live layers -- no builder, no committed data/app file -- so a vintage
    # roll reaches them on its own and there is nothing here to rebuild. What
    # this list watches is the endpoint still ANSWERING FOR MISSISSIPPI: a
    # returnCountOnly query per layer, so a service moved, renamed or silently
    # emptied for this state surfaces as a WARN instead of as cards that quietly
    # stop resolving.
    #
    # The counts below are measured 2026-10-15 and are RECORDED, not asserted:
    # this validator reports, it never edits the app. Incorporated places 300 ·
    # unified school districts 137.
    #
    # SCHOOL LAYERS 1 (SECONDARY) AND 2 (ELEMENTARY) ANSWER ZERO FOR
    # MISSISSIPPI, measured the same day; the unified layer covers the state
    # alone. Neither is watched -- a row whose count is zero on purpose cannot
    # tell a drop from the status quo.
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2728%27&returnCountOnly=true&f=json",
        "min_count": 270,   # 300 measured 2026-10-15; floor set below it, not at it
    },
    {
        "layer": "school-district-unified",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0/query?where=STATE%3D%2728%27&returnCountOnly=true&f=json",
        "min_count": 123,   # 137 measured 2026-10-15
    },
    # USGS structures, counted rather than fetched, because the count is the
    # thing at risk: the service caps a response at 2,000 records and says so
    # with HTTP 200 + exceededTransferLimit rather than an error. min_count is
    # what makes each row a real tripwire rather than a ping.
    #
    # returnCountOnly IS NOT SUBJECT TO maxRecordCount, so none of these rows can
    # see the client truncating. What catches a broken pager is the browser gate
    # -- ms/scripts/smoke_test.mjs asserts the loader makes more than one
    # request and that the second page's station reaches the card.
    #
    # Counted over the app's own envelope (METRO_BBOX, -91.66,30.13,-88.09,35.0),
    # which reaches into the neighbouring states where the border is not
    # straight, so these are the counts the app downloads rather than the
    # state's exact totals.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query"
                "?geometry=-91.66%2C30.13%2C-88.09%2C35.0&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 590,   # 654 measured 2026-10-15
    },
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query"
                "?geometry=-91.66%2C30.13%2C-88.09%2C35.0&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 1360,  # 1,508 measured 2026-10-15 -- within 492 of the 2,000 cap
    },
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query"
                "?geometry=-91.66%2C30.13%2C-88.09%2C35.0&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 415,   # 462 measured 2026-10-15
    },
    # ZCTAs carry NO STATE field, so this one is counted by ENVELOPE, in Esri's
    # own comma form -- the {minLng,...} shape makes TIGERweb answer HTTP 200
    # with a JSON error envelope. min_count is what makes this a real check
    # rather than a reachability ping.
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query?where=1%3D1"
                "&geometry=-91.75%2C30.05%2C-88.00%2C35.10&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 745,   # 827 measured 2026-10-15
    },
    # The county maps ms/scripts/build_ms_supervisor_districts.py reads for the
    # eight counties drawn from their own lines. Unlike the rows above these have
    # a builder and a committed file; they are COUNTED here because all three
    # servers answer a deleted layer with HTTP 200 (an empty page, an
    # "Application Error" page or a blank one, measured 2026-10-15), so a status
    # check would read a layer that is gone as reachable. A count query on a
    # missing layer answers HTTP 200 with an Esri error envelope instead, which
    # the check below reports. Each layer held exactly 5 districts that day; a
    # change is a reason to rebuild, which re-reads the evidence each county's
    # lines were confirmed with. Check 1 holds these rows to the builder's own
    # COUNTY_SOURCES, so the two cannot name different layers.
    {
        "layer": "county-supervisor",   # Copiah
        "url": "https://gis.cmpdd.org/server/rest/services/Hosted/Copiah_County_Feature_Layer/FeatureServer/15/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
    },
    {
        "layer": "county-supervisor",   # Harrison
        "url": "https://geo.co.harrison.ms.us/server/rest/services/AGO/HarrisonCounty_SupervisorDistrict/FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
    },
    {
        "layer": "county-supervisor",   # Hinds
        "url": "https://gis.cmpdd.org/server/rest/services/Hosted/Hinds_County_Map/FeatureServer/17/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
    },
    {
        "layer": "county-supervisor",   # Lamar
        "url": "https://services1.arcgis.com/mz3jHVSffoNsLuEB/arcgis/rest/services/Lamar_Service/FeatureServer/15/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
    },
    {
        "layer": "county-supervisor",   # Madison
        "url": "https://gis.cmpdd.org/server/rest/services/Hosted/Madison_County_Map/FeatureServer/44/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
    },
    {
        "layer": "county-supervisor",   # Rankin
        "url": "https://gis.cmpdd.org/server/rest/services/Hosted/Rankin_County_Feature_Layer/FeatureServer/13/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
    },
    {
        "layer": "county-supervisor",   # Simpson
        "url": "https://gis.cmpdd.org/server/rest/services/Hosted/Simpson_County_Feature_Layer/FeatureServer/32/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
    },
    {
        "layer": "county-supervisor",   # Warren
        "url": "https://gis.cmpdd.org/server/rest/services/Hosted/Warren_County_Feature_Layer/FeatureServer/21/query?where=1%3D1&returnCountOnly=true&f=json",
        "min_count": 5,
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


# Hosts that send only their own certificate, keyed to the intermediate
# scripts/aia_bundle.py pins for them. The builder that reads the host completes
# the chain from that pin, so this check reads it the same way, robots.txt
# included: read with the plain trust store, www.legislature.ms.gov's robots.txt
# is unreachable, which RFC 9309 treats as a refusal, and on 2026-10-15 that
# stopped the whole run at the first legislature row. gis.cmpdd.org, the
# planning district's map server the supervisor build reads, sends its leaf
# without the GoDaddy intermediate, measured the same day.
PINNED_CHAINS = {"www.legislature.ms.gov": "globalsign-rsa-ov-2018",
                 "gis.cmpdd.org": "godaddy-g2"}
_BUNDLES = {}


def _verify_for(url):
    """The CA bundle path to read `url` with, or None for the default store."""
    from urllib.parse import urlsplit

    key = PINNED_CHAINS.get(urlsplit(url).hostname or "")
    if key is None:
        return None
    if key not in _BUNDLES:
        _BUNDLES[key] = aia_bundle.ca_bundle("ms-validate-sources", key)
    return _BUNDLES[key]


def _drop_bundles():
    for path in _BUNDLES.values():
        try:
            os.unlink(path)
        except OSError:
            pass


def http_get(url, want_json=True, params=None):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises."""
    if requests is None:
        return False, "requests not installed"
    ua = "districtry source validator (+https://districtry.com/ms/)"
    try:
        verify = _verify_for(url)
    except (Exception, SystemExit) as e:  # a moved pin is a finding, not a crash
        return False, "could not build the pinned certificate chain: %s" % e
    try:
        require_robots_once(url, ua, headers={"User-Agent": ua},
                            label="ms-validate-sources", verify=verify)
    except SystemExit:
        # require_robots_once has printed why and exits on a refusal or an
        # unreadable policy. Here that is one source's finding rather than the
        # end of the run, and nothing is fetched from the host either way.
        return False, "robots.txt refuses this client or could not be read (the reason is printed above); nothing fetched"
    try:
        kwargs = {"verify": verify} if verify else {}
        resp = requests.get(
            url,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": ua},
            **kwargs
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
                         "out of sync with the app (update ms/scripts/validate_sources.py)"
                         % d["id"])
    # The county maps the supervisor build reads are counted under ENDPOINTS,
    # and the builder's COUNTY_SOURCES is the authority on which they are: a
    # county added there and not here would be a layer nothing watches.
    try:
        import build_ms_supervisor_districts as supervisor
    except Exception as e:  # a broken import is a finding, not a crash
        findings.add(FAIL, "county-supervisor",
                     "could not read the supervisor builder's county sources: %s" % e)
    else:
        want = sorted(spec["url"] for spec in supervisor.COUNTY_SOURCES.values())
        have = sorted(e["url"].split("/query?")[0] for e in ENDPOINTS
                      if e["layer"] == "county-supervisor")
        if want != have:
            findings.add(FAIL, "county-supervisor",
                         "ENDPOINTS counts %s and the builder reads %s — update "
                         "ms/scripts/validate_sources.py" % (have, want))
        unpinned = sorted(h for h, k in supervisor.PINNED_CHAINS.items()
                          if PINNED_CHAINS.get(h) != k)
        if unpinned:
            findings.add(FAIL, "county-supervisor",
                         "the builder pins a certificate for %s and this check does "
                         "not, so it would read the host differently" % unpinned)
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
              "`pip install -c ms/scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    try:
        check_manifest_matches_app(html, findings)
        check_socrata(findings, args.offline)
        check_provenance(findings, args.offline)
        check_endpoints(findings, args.offline)
    finally:
        _drop_bundles()

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
