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
    exists. Nothing errors; the data just quietly goes stale. New Hampshire's
    instance reads no Socrata portal, so that list is empty here.
  * Pre-built boundary layers were downloaded at build time from Census
    TIGERweb: the congressional map (layer 0, the 2022 map), the 24 State
    Senate districts (layer 1) and the 164 base State House districts
    (layer 2), with each base district's floterial district measured from the
    state GIS clearinghouse, NH GRANIT. The check there is provenance: is the
    source we cite still reachable, and is it still the map the shipped file
    was drawn from.

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
  3. Provenance: the cited source URL is reachable and the built data/app file
     is present.                                           [WARN / FAIL if gone]
  4. Live service endpoints (Census TIGERweb, the USGS National Map):
     answering for New Hampshire, with a count at or above its floor.  [WARN]
  5. The congressional map: congress-districts.json is TIGERweb layer 0 (the
     120th Congress), which in New Hampshire is the same map as layer 4 (the
     119th): the map the New Hampshire Supreme Court drew in 2022, when the
     Legislature and the Governor did not agree on a plan.
     It is right until noon on 3 January 2029. From 1 December 2028 this check
     says so every month; it also says so if either layer is renamed, since
     the builder would then refuse to rebuild.                            [WARN]
  6. The legislative maps: TIGERweb's 2026 state legislative layers (layer 1,
     the Senate, and layer 2, the House's base districts) still carry the
     names the builder refuses a rebuild on, so a rolled vintage is
     read by a person a month after it appears rather than on the day
     somebody rebuilds.                                                   [WARN]

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/nh-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 nh/scripts/validate_sources.py                 # human-readable report
    python3 nh/scripts/validate_sources.py --report r.md   # also write markdown
    python3 nh/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 nh/scripts/validate_sources.py --offline       # manifest↔app checks only
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
from robots_policy import HostPacer, RobotsGate  # noqa: E402  (FLEET_SHARED)

try:
    import requests
except ImportError:  # pragma: no cover - requests is pinned in requirements.txt
    requests = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

HTTP_TIMEOUT = 25

# The freshness gate's source manifest for the New Hampshire instance. Every
# layer this instance adds gets its rows here in the same change (CLAUDE.md's
# conventions; the reference repo's validate_sources.py shows a mature
# manifest's full shape, including year-search patterns and the `blocked`
# inversion).
SOCRATA_DOMAIN = "data.invalid"  # this instance reads no Socrata portal
CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"

# Socrata dataset ids the app hardcodes (none).
SOCRATA = []

LEGISLATIVE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer"
STATE_COUNTY = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1"
GRANIT = ("https://nhgeodata.unh.edu/hosting/rest/services/Hosted/"
          "APB_ElectoralDistricts/FeatureServer")
LEGISLATURE_FILE = "https://gc.nh.gov/downloads/members.txt"
OPENSTATES_FILE = "https://data.openstates.org/people/current/nh.csv"

# Same-origin data/app files and the upstream source each was built from.
PROVENANCE = [
    {
        "layer": "us-house",
        "app_file": "congress-districts.json",
        "source_url": LEGISLATIVE + "/0",
        "note": (
            "2 congressional districts pre-built from TIGERweb's layer 0, the "
            "120th Congress's map, by nh/scripts/build_legislative_boundaries.py. "
            "In New Hampshire it is the same map as layer 4, the 119th Congress's "
            "(the builder holds every district's intersection-over-union at "
            "0.9999 or more): the map the New Hampshire Supreme Court drew in "
            "2022. Check 5 below says when the map has to be re-read."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-nh-congress-roster.yml.",
    },
    {
        "layer": "nh-senate",
        "app_file": "nh-senate-districts.json",
        "source_url": LEGISLATIVE + "/1",
        "note": (
            "24 State Senate districts pre-built from TIGERweb's 2026 state "
            "legislative layer (upper chamber) by the same builder, in one "
            "shared topology with the congressional and House maps."
        ),
    },
    {
        "layer": "nh-house",
        "app_file": "nh-house-districts.json",
        "source_url": LEGISLATIVE + "/2",
        "note": (
            "164 base State House districts pre-built from TIGERweb's 2026 state "
            "legislative layer (lower chamber) by the same builder. TIGERweb "
            "carries no floterial district, because Census geography cannot "
            "overlap; the next row is where those come from."
        ),
    },
    {
        "layer": "nh-house",
        "app_file": "nh-house-districts.json",
        "source_url": GRANIT,
        "verify_certifi": True,
        "note": (
            "The 39 floterial districts, from NH GRANIT's 2022 House layers "
            "(NHHouseDists2022_base and NHHouseDists2022_float): the builder "
            "measures which whole base districts make each floterial and writes "
            "that onto each base district as its `floterial`. GRANIT's chain "
            "verifies against certifi's copy of Mozilla's store (the builder's "
            "own note)."
        ),
    },
    {
        "layer": "nh-senate",
        "app_file": "nh-senate-members.json",
        "source_url": LEGISLATURE_FILE,
        "note": (
            "The General Court's own member file, route 1 of "
            "nh/scripts/build_nh_legislature_roster.py, rebuilt weekly by "
            "update-nh-legislature-roster.yml. Unreachable from the build "
            "sandbox on 2026-11-11, when the first roster was built from "
            "route 2; this row says whether a runner reaches it."
        ),
    },
    {
        "layer": "nh-senate, nh-house",
        "app_file": "nh-house-members.json",
        "source_url": OPENSTATES_FILE,
        "note": (
            "Route 2, Open States' export of current legislators, compiled from "
            "the General Court's own pages; used when route 1 cannot be read or "
            "fails a check. Only an e-mail address at the Legislature's own "
            "domain is carried from it."
        ),
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": STATE_COUNTY,
        "note": (
            "The 10 counties pre-built from TIGERweb by "
            "nh/scripts/build_state_counties.py (Douglas-Peucker at 5 m, held "
            "to an 8 m fidelity ceiling)."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": STATE_COUNTY,
        "note": (
            "The state outline for the coverage wash, dissolved from the 10 "
            "counties by nh/scripts/build_metro_outline.py. "
            "Its --check is offline and holds the shipped file to one INSIDE "
            "anchor per county plus OUTSIDE anchors over the state line."
        ),
    },
]

# New Hampshire's envelope, as index.html writes it for the ZIP layer
# (NH_BBOX_ENVELOPE, Esri's {xmin,...} form) and for the USGS layers
# (METRO_BBOX, generated from the worksheet's metro_bbox). The ZIP envelope is
# a little wider than the state's box, so the two carry different numbers;
# each row is counted over the literal its loader reads, and check 1 fails
# when either moves.
ZIP_ENVELOPE_LITERAL = "xmin: -72.65, ymin: 42.6, xmax: -70.45, ymax: 45.4"
USGS_ENVELOPE_LITERAL = "minLng: -72.56, minLat: 42.69, maxLng: -70.57, maxLat: 45.31"
_ENVELOPE_TAIL = "&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects"
ZIP_ENVELOPE_QUERY = "&geometry=-72.65%2C42.6%2C-70.45%2C45.4" + _ENVELOPE_TAIL
ENVELOPE_QUERY = "&geometry=-72.56%2C42.69%2C-70.57%2C45.31" + _ENVELOPE_TAIL

ENDPOINTS = [
    # The live layers -- no builder, no committed data/app file of their own
    # (the census layers are drawn from tile archives mirrored by
    # scripts/mirror_tiger_tiles.py, whose weekly job watches the data) -- so
    # what this list watches is the endpoint still ANSWERING FOR NEW HAMPSHIRE:
    # a returnCountOnly query per layer, so a service moved, renamed or
    # silently emptied for this state surfaces as a WARN instead of as cards
    # that quietly stop resolving.
    #
    # The counts below are measured 2026-11-11 and are RECORDED, not asserted:
    # this validator reports, it never edits the app. County subdivisions 260
    # (13 cities, 222 towns, 24 unincorporated places and 1 water record) ·
    # unified school districts 82 (81 districts and the Census's "School
    # District Not Defined" placeholder) · elementary 90 · secondary 8.
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/1/query?where=STATE%3D%2733%27&returnCountOnly=true&f=json",
        "min_count": 255,  # 260 measured 2026-11-11; towns and places change rarely
    },
    {
        "layer": "school-district-unified",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0/query?where=STATE%3D%2733%27&returnCountOnly=true&f=json",
        "min_count": 76,    # 82 measured 2026-11-11; districts merge into cooperatives now and then
    },
    {
        "layer": "school-district-elementary",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/2/query?where=STATE%3D%2733%27&returnCountOnly=true&f=json",
        "min_count": 84,    # 90 measured 2026-11-11
    },
    {
        "layer": "school-district-secondary",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/1/query?where=STATE%3D%2733%27&returnCountOnly=true&f=json",
        "min_count": 7,     # 8 measured 2026-11-11
    },
    # USGS structures, counted rather than fetched, because the count is the
    # thing at risk: the service caps a response at 2,000 records and says so
    # with HTTP 200 + exceededTransferLimit rather than an error. min_count is
    # what makes each row a real tripwire rather than a ping.
    #
    # returnCountOnly IS NOT SUBJECT TO maxRecordCount, so none of these rows can
    # see the client truncating. What catches a broken pager is the browser gate
    # -- nh/scripts/smoke_test.mjs asserts the loader makes more than one
    # request and that the second page's station reaches the card. New
    # Hampshire's layers are far under the cap (the fire layer is 536 points,
    # measured 2026-11-11); the pager stays so that a larger answer is never
    # cut short.
    #
    # Counted over the app's own envelope (METRO_BBOX), which reaches into
    # Vermont, Maine and Massachusetts, so these are the counts the app
    # downloads rather than the state's exact totals.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query"
                "?where=1%3D1" + ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 395,  # 442 measured 2026-11-11
        "envelope": USGS_ENVELOPE_LITERAL,
    },
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query"
                "?where=1%3D1" + ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 480,  # 536 measured 2026-11-11
        "envelope": USGS_ENVELOPE_LITERAL,
    },
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query"
                "?where=1%3D1" + ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 250,  # 282 measured 2026-11-11
        "envelope": USGS_ENVELOPE_LITERAL,
    },
    # ZCTAs carry NO STATE field, so this one is counted by ENVELOPE, in Esri's
    # own comma form -- the {minLng,...} shape makes TIGERweb answer HTTP 200
    # with a JSON error envelope. min_count is what makes this a real check
    # rather than a reachability ping. The envelope is the app's own
    # (NH_BBOX_ENVELOPE in index.html).
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query"
                "?where=1%3D1" + ZIP_ENVELOPE_QUERY + "&returnCountOnly=true&f=json"),
        "min_count": 490,  # 548 measured 2026-11-11, over the envelope rather than the state
        "envelope": ZIP_ENVELOPE_LITERAL,
    },
]

# Check 5's dates and the two layers the congressional file is held to. The
# builder (nh/scripts/build_legislative_boundaries.py) holds the same names
# and dates, and refuses a rebuild once either stops being true.
CONGRESS_LAYERS = [
    (LEGISLATIVE + "/0?f=json", "120th Congressional Districts"),
    (LEGISLATIVE + "/4?f=json", "119th Congressional Districts"),
]
CONGRESS_SERVING_UNTIL = "2029-01-03"
CONGRESS_WARN_FROM = "2028-12-01"

# Check 6: the legislative maps' TIGERweb layers, with the names the builder
# refuses a rebuild on (its LAYERS table and check_serving_map). Layer 1 is the
# Senate and layer 2 the House's 164 base districts.
CHAMBER_LAYERS = [
    {
        "layer": "nh-senate",
        "url": LEGISLATIVE + "/1?f=json",
        "name": "2026 State Legislative Districts - Upper",
    },
    {
        "layer": "nh-house",
        "url": LEGISLATIVE + "/2?f=json",
        "name": "2026 State Legislative Districts - Lower",
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


USER_AGENT = "districtry source validator (+https://districtry.com/nh/)"
PACER = None


def pacer():
    """The run's one HostPacer, built on first use.

    No host this run reads states a Crawl-delay (gc.nh.gov's robots.txt could
    not be read from the build sandbox on 2026-11-11); the pacer honours a
    delay the day one is stated. Lazy because --offline fetches nothing and
    should not read anybody's robots.txt to say so.
    """
    global PACER
    if PACER is None:
        PACER = HostPacer(RobotsGate(requests.Session(), USER_AGENT,
                                     timeout=HTTP_TIMEOUT))
    return PACER


def http_get(url, want_json=True, params=None, verify=None):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises.

    `verify` is a CA bundle path for a host whose chain this environment's
    bundle cannot complete (GRANIT's, read through certifi as its builder reads
    it); verification is never switched off.
    """
    if requests is None:
        return False, "requests not installed"
    ua = USER_AGENT
    try:
        require_robots_once(url, ua, headers={"User-Agent": ua},
                            label="nh-validate-sources", verify=verify)
    except SystemExit:
        # require_robots_once has printed why and exits on a refusal or an
        # unreadable policy. Here that is one source's finding rather than the
        # end of the run, and nothing is fetched from the host either way.
        return False, "robots.txt refuses this client or could not be read (the reason is printed above); nothing fetched"
    try:
        with pacer().hold(url):
            resp = requests.get(
                url,
                params=params,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": ua},
                verify=verify if verify else True,
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
                         "out of sync with the app (update nh/scripts/validate_sources.py)"
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
        verify = None
        if p.get("verify_certifi"):
            try:
                import certifi  # noqa: PLC0415 (only GRANIT's row needs it)
                verify = certifi.where()
            except ImportError:
                findings.add(WARN, layer, "certifi is not installed, so %s was "
                             "not read (its chain needs Mozilla's store)" % p["source_url"])
                continue
        ok, res = http_get(p["source_url"], want_json=False, verify=verify)
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
                     "the members elected on New Hampshire's 2022 map in 2026 left office at noon "
                     "on 3 January 2029: re-read which map the 2028 election used, rebuild "
                     "congress-districts.json from the TIGERweb layer that carries it, and "
                     "change the us-house entry in nh/scripts/build_legislative_boundaries.py "
                     "— nh/WATCH.md has the steps")
    elif today >= CONGRESS_WARN_FROM:
        findings.add(WARN, "us-house",
                     "the members elected on New Hampshire's 2022 map in 2026 leave office at noon "
                     "on 3 January 2029; congress-districts.json is right until then and must "
                     "be re-read that day — nh/WATCH.md has the steps")
    if offline:
        return
    for url, want in CONGRESS_LAYERS:
        ok, res = http_get(url)
        if not ok:
            findings.add(WARN, "us-house", "TIGERweb's layer %s is not reachable (%s)" % (url, res))
            continue
        name = res.get("name", "") if isinstance(res, dict) else ""
        if name != want:
            findings.add(WARN, "us-house",
                         "TIGERweb's layer %s is now %r, not %r: the shipped file is "
                         "unchanged, but nh/scripts/build_legislative_boundaries.py would "
                         "refuse to rebuild it until its layer table names the layers that "
                         "carry the 2022 map" % (url, name, want))
        else:
            findings.add(OK, "us-house", "TIGERweb's layer %s is still %r" % (url, name))


# ---- check 6: the legislative layers are still the 2022 plan ---------------
def check_chamber_maps(findings, offline):
    if offline:
        return
    for c in CHAMBER_LAYERS:
        ok, res = http_get(c["url"])
        if not ok:
            findings.add(WARN, c["layer"],
                         "TIGERweb's layer is not reachable (%s): %s" % (res, c["url"]))
            continue
        if not isinstance(res, dict) or "error" in res:
            findings.add(WARN, c["layer"],
                         "TIGERweb's layer answered an error (%s): %s"
                         % (res.get("error") if isinstance(res, dict) else res, c["url"]))
            continue
        name = res.get("name", "")
        if name != c["name"]:
            findings.add(WARN, c["layer"],
                         "TIGERweb's layer is now named %r, not %r. The shipped file is "
                         "unchanged, but nh/scripts/build_legislative_boundaries.py would "
                         "refuse to rebuild it: TIGERweb renumbers its layers when a "
                         "vintage rolls, so find the layer that carries the 2022 plan "
                         "before drawing anything. %s" % (name, c["name"], c["url"]))
        else:
            findings.add(OK, c["layer"], "TIGERweb's layer is still %r" % name)


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
              "`pip install -c nh/scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    check_manifest_matches_app(html, findings)
    check_socrata(findings, args.offline)
    check_provenance(findings, args.offline)
    check_endpoints(findings, args.offline)
    check_congress_map(findings, args.offline)
    check_chamber_maps(findings, args.offline)

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
