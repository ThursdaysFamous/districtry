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

Crawl-delay: NO HOST THIS FILE PROBES STATES ONE, and NONE OF THE THREE PUBLISHES
A READABLE POLICY AT ALL. Measured 2026-10-01 with this file's own user agent, one
robots.txt read per host, over the three the manifest actually reaches (13 live
endpoints and 6 provenance entries, and SOCRATA is empty — this instance draws on
no portal dataset): tigerweb.geo.census.gov serves 189 bytes of HTML at that path
rather than a policy, unitedstates.github.io answers 404, and carto.nationalmap.gov
answers 403 — which under RFC 9309 is a file that was never published rather than a
refusal (CLAUDE.md records the ruling and why reading it as a refusal cost this
fleet real data). The pacer is wired anyway
(scripts/robots_policy.py's HostPacer, the same object the Iowa board-chair
scrape uses) and prints the hosts it held to stderr at the end of the run, so an
honoured delay can be told from an ignored one the day a source with one is
added.

THE PARAGRAPH THIS REPLACES WAS IOWA'S AND WAS FALSE OF THIS FILE from the day
the instance shipped. It stated that this file probes two pages on
www.iowacourts.gov and one PDF on www.issda.org and that neither delay was
honoured before the pacer landed. Minnesota reaches neither host — there is no
sheriff directory and no county-attorney roster in this manifest — so the
measurement was about a sibling's code and read as a measurement about this
one. Carried over wholesale with the file, the same way Michigan's go-live
shipped Iowa's identity block, and corrected rather than deleted so the next
clone can see the class of mistake.

WHAT THIS FILE STILL DOES NOT DO, stated rather than left to be assumed: it
reads robots.txt for the DELAY and does not act on the file's allow/disallow.
That is deliberate for now and not an oversight. RFC 9309 makes an UNREACHABLE
robots.txt disallow-all, and this script's whole question is "is this source
still there" — a transient robots.txt outage would turn into a source-freshness
finding about the wrong thing, so declining a probe needs its own decision
about how that is reported (scripts/validate_card_links.py's ROBOTS_DECLINED is
the shape). CLAUDE.md already records the fleet-level follow-up: several
scrapers fetch without asking, and that is the next thing to fix.

Exit status: 0 when nothing needs a human (OK or WARN only), 1 on any FAIL.
Newer-edition detection is deliberately WARN, not FAIL — the current dataset
still works and a person decides whether/when to migrate. The scheduled
workflow (.github/workflows/mn-validate-sources.yml, 1st of the month at
18:00 UTC) opens an issue on WARN or FAIL so drift is never silent, without
turning the build red. THAT WORKFLOW ARRIVED ON 2026-10-01, TWO DAYS AFTER
THIS FILE AND A DAY AFTER GO-LIVE: this sentence used to defer it on the
ground that the instance was dark and point at a GO-LIVE row in mn/WATCH.md
that nobody wrote, so the deferral had nothing holding it.

Usage:
    python3 mn/scripts/validate_sources.py                 # human-readable report
    python3 mn/scripts/validate_sources.py --report r.md   # also write markdown
    python3 mn/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 mn/scripts/validate_sources.py --offline       # manifest↔app checks only
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling, not a package
from robots_gate import RobotsGate, HostPacer  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

HTTP_TIMEOUT = 25
# The gate must ask a host's robots.txt about the token the fetch actually
# sends, so there is one literal and both read it.
USER_AGENT = "districtry source validator (+https://districtry.com/mn/)"

# The freshness gate's source manifest for the Iowa instance. Every layer this
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
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "Minnesota's 87 counties pre-built from TIGERweb by "
            "mn/scripts/build_state_counties.py. The same file is dissolved into "
            "metro-outline.json for the coverage wash, so a change here moves "
            "both. THE FABRIC IS WATER-INCLUSIVE to the international boundary: "
            "a point in open Lake Superior is still inside Cook County, which is "
            "why this instance's negative point is in North Dakota."
        ),
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": (
            "The whole-state outline the coverage wash paints, dissolved from "
            "the county fabric by mn/scripts/build_metro_outline.py. Its anchor "
            "registry is checked offline on every build and every --check."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0",
        "note": (
            "Minnesota's 8 congressional districts, pre-built from TIGERweb's "
            "120th-Congress layer (field CD120) by "
            "mn/scripts/build_legislative_boundaries.py. That builder takes no "
            "per-chamber argument: all three chambers are simplified in ONE "
            "mapshaper combine-files topology, because a shared edge only "
            "survives identically if both sides came off one run."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": (
            "Delegation roster from the public-domain congress-legislators "
            "project; refreshed weekly by update-mn-congress-roster.yml as a "
            "reviewed pull request. It is the only roster this instance ships."
        ),
    },
    {
        "layer": "mn-senate",
        "app_file": "mn-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": (
            "67 state senate districts from TIGERweb's SLDU layer, built in the "
            "same combine-files run as the House and Congress. NO ROSTER SHIPS: "
            "the card names the district and links senate.mn.gov's own member "
            "directory, recorded as gap mn-legislature-roster."
        ),
    },
    {
        "layer": "mn-house",
        "app_file": "mn-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": (
            "134 state house districts from TIGERweb's SLDL layer. MINNESOTA "
            "NESTS BY LETTER -- Senate 61 holds House 61A and 61B -- which the "
            "builder's exact zero-tolerance nesting gate checks on every run and "
            "its --check re-runs offline in CI."
        ),
    },
    {
        "layer": "voting-precinct",
        "app_file": "mn-precincts.json",
        "source_url": (
            "https://enterprise.gisdata.mn.gov/aghost/rest/services/"
            "us_mn_state_sos/bdry_votingdistricts/FeatureServer/0"
        ),
        "note": (
            "4,105 voting precincts from the Secretary of State's own statewide "
            "service -- the first layer this instance ships from a Minnesota "
            "publisher rather than from the Census. THE FRESHNESS SIGNAL IS THE "
            "SERVICE'S OWN Service Modified STAMP, not a vintage roll: precincts "
            "are redrawn by cities, townships and counties between elections, so "
            "a moved stamp is the only announcement there is. The same service "
            "carries each precinct's county commissioner, judicial, soil-and-water, "
            "hospital and park district and its city ward, none of which this file "
            "takes -- mn/WATCH.md records them as the seven layers that dissolve "
            "out of it."
        ),
    },
    {
        "layer": "county-commissioner",
        "app_file": "mn-commissioner-districts.json",
        "source_url": (
            "https://enterprise.gisdata.mn.gov/aghost/rest/services/"
            "us_mn_state_sos/bdry_votingdistricts/FeatureServer/0"
        ),
        "note": (
            "447 county commissioner districts across all 87 counties, dissolved "
            "from the precinct row above on the ctycomdist each precinct carries. "
            "SO IT SHARES THAT ROW'S FRESHNESS SIGNAL AND HAS ONE MORE OF ITS OWN: "
            "a county that redistricts announces itself in the Service Modified "
            "stamp, and a county that CHANGES ITS BOARD SIZE announces itself in "
            "Minn. Stat. 375.01, which the builder parses on every run rather than "
            "carrying a transcription of the four seven-member counties. Two more "
            "witnesses are gated with it and neither is this service checking "
            "itself: seven county governments' own commissioner-district layers, "
            "and the Secretary of State's certified 2024 and 2022 per-precinct "
            "results, which carry the same key as dated snapshots. The people are "
            "not here -- no commissioner is named, gap "
            "mn-county-commissioner-roster."
        ),
    },
    {
        "layer": "mn-judicial-district",
        "app_file": "mn-judicial-districts.json",
        "source_url": "https://www.revisor.mn.gov/statutes/cite/2.722",
        "note": (
            "The ten judicial districts. THE SOURCE IS A STATUTE RATHER THAN A "
            "DATASET, which is why this row's url is the Revisor's: Minn. Stat. "
            "2.722 subd. 1 names the counties in each district, and the lines are "
            "those counties' own, dissolved from state-counties.json. So what can "
            "go stale here is the TEXT -- an amendment to subd. 1, or an alteration "
            "the supreme court makes under subd. 2 -- and the builder parses the "
            "county lists off this page on every run rather than carrying a "
            "transcription. A second, independent witness is gated with it: the "
            "Secretary of State's precinct service (the row above) carries a "
            "judicial district on every one of the 4,105 precincts, and all 87 "
            "counties must agree with the statute before anything is written."
        ),
    },
    {
        "layer": "watershed-district",
        "app_file": "mn-watershed-districts.json",
        "source_url": (
            "https://enterprise.gisdata.mn.gov/aghost/rest/services/"
            "us_mn_state_bwsr/bdry_watershed_mgmt_dist_orgs/FeatureServer/0"
        ),
        "note": (
            "64 watershed districts and watershed management organizations from "
            "the Board of Water and Soil Resources' own statewide service. The "
            "freshness signal is the service's Service Modified stamp: a district "
            "is formed, enlarged or dissolved by an order of BWSR, and a metro "
            "organization's members can change by joint-powers agreement, so "
            "neither waits for a census. The Geospatial Commons download host "
            "for the same layer answers robots.txt with Disallow: / and is not "
            "read."
        ),
    },
]

ENDPOINTS = [
    # THIS LIST NOW COVERS TWO DIFFERENT KINDS OF DEPENDENCY, and the
    # distinction decides what a FAIL means. The first four rows are about the
    # REBUILD: those layers ship as same-origin files, so a broken endpoint
    # breaks the next build and not a reader's card. The nine rows after them
    # are about a RUNTIME FETCH: those layers query the service on every
    # toggle, so a broken endpoint is a reader looking at an error card right
    # now. Both are checked the same way and the report says which is which.
    #
    # The nine live rows also carry the whole of this instance's behaviour
    # coverage for those layers, deliberately. The browser gate exercises the
    # four offline anchors and not these, because a check that needs a
    # government server up fails on somebody else's schedule -- so the count
    # floors here are what would catch a layer that has quietly started
    # answering nothing. Each is the app's own enveloped query
    # shape with a count floor, not a metadata probe -- Iowa's #718 is the
    # measurement behind that choice, where a reachable /11?f=json passed for
    # weeks while the query the app actually sent answered HTTP 200 with an
    # Esri error envelope and no features.
    #
    # THE LAYER INDICES ARE THE BUILDER'S, NOT GUESSED: TIGERweb's Legislative
    # MapServer is 0 US House, 1 upper chamber, 2 lower chamber (LAYERS in
    # mn/scripts/build_legislative_boundaries.py). A first draft of this file
    # wrote 2 and 4 for the two state chambers, and the count floors are what
    # caught it -- layer 2 answered 134 under the heading mn-senate, which is
    # the HOUSE's count, and layer 4 answered 8, which is Congress's. A
    # reachability probe would have called all four rows OK.
    {
        "layer": "county",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "State_County/MapServer/1/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 87,  # Minnesota's county count is fixed by statute
    },
    {
        "layer": "us-house",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Legislative/MapServer/0/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 8,
    },
    {
        "layer": "mn-senate",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Legislative/MapServer/1/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 67,
    },
    {
        "layer": "mn-house",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Legislative/MapServer/2/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 134,
    },
    # ---- live runtime fetches: TIGERweb fabrics, STATE-filtered ----
    {
        "layer": "school-district-unified",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "School/MapServer/0/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 300,  # 322 measured 2026-09-29; districts consolidate, so the floor sits below it
    },
    {
        "layer": "school-district-elementary",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "School/MapServer/2/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        # 8 measured 2026-09-29. The floor is 1 rather than 8 on purpose: this
        # tiling exists to gap-fill the unified one, and a district leaving it
        # (by consolidating into a unified district) is an ordinary event that
        # must not turn a monthly job red. Zero is the state worth catching,
        # because it would mean the layer had stopped answering.
        "min_count": 1,
    },
    {
        "layer": "school-district-secondary",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "School/MapServer/1/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        # Exactly 1 feature for the whole state, so the floor IS the count and
        # there is no room below it: if Park Rapids-in-Pine-Point ever leaves
        # this tiling the layer answers nowhere, and this row going red is how
        # anyone would find out.
        "min_count": 1,
    },
    {
        "layer": "county-subdivision",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 2600,  # 2,762 measured 2026-09-29; towns dissolve and cities annex, so the floor sits below it
    },
    {
        "layer": "municipality",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2727%27"
                "&returnCountOnly=true&f=json"),
        "min_count": 800,  # 856 measured 2026-09-29
    },
    # ---- live runtime fetch with NO state filter ----
    {
        "layer": "zip-code",
        # A ZCTA has no state field, so this is the app's own ENVELOPE query
        # rather than a STATE filter, spelled exactly as index.html spells it.
        # The envelope is this instance's metro_bbox.
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query?where=1%3D1"
                "&geometry=%7B%22xmin%22%3A-97.3%2C%22ymin%22%3A43.44%2C"
                "%22xmax%22%3A-89.43%2C%22ymax%22%3A49.44%7D"
                "&geometryType=esriGeometryEnvelope&inSR=4326"
                "&spatialRel=esriSpatialRelIntersects"
                "&returnCountOnly=true&f=json"),
        "min_count": 1300,  # 1,385 in the envelope, measured 2026-09-29
    },
    # ---- live runtime fetches: USGS National Map structures, enveloped ----
    # Each is the app's own enveloped query. The counts include points across
    # each border ON PURPOSE -- nearest is a proximity fact -- so these floors
    # are about the service answering at all, not about Minnesota's own share.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/"
                "MapServer/38/query?where=1%3D1&geometry=-97.3%2C43.44%2C-89.43%2C49.44"
                "&geometryType=esriGeometryEnvelope&inSR=4326"
                "&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 1000,  # 1,199 measured 2026-09-29 (793 in Minnesota)
    },
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/"
                "MapServer/51/query?where=1%3D1&geometry=-97.3%2C43.44%2C-89.43%2C49.44"
                "&geometryType=esriGeometryEnvelope&inSR=4326"
                "&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 1300,  # 1,484 measured 2026-09-29 (961 in Minnesota)
    },
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/"
                "MapServer/53/query?where=1%3D1&geometry=-97.3%2C43.44%2C-89.43%2C49.44"
                "&geometryType=esriGeometryEnvelope&inSR=4326"
                "&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 600,  # 694 measured 2026-09-29 (448 in Minnesota)
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


PACER = None


def pacer():
    """The run's one HostPacer, built on first use.

    Lazy because --offline never fetches anything and should not open a
    session or read anybody's robots.txt to say so.
    """
    global PACER
    if PACER is None:
        PACER = HostPacer(RobotsGate(requests.Session(), USER_AGENT,
                                     timeout=HTTP_TIMEOUT))
    return PACER


def http_get(url, want_json=True, params=None):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises."""
    if requests is None:
        return False, "requests not installed"
    try:
        with pacer().hold(url):
            resp = requests.get(
                url,
                params=params,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
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
                         "out of sync with the app (update mn/scripts/validate_sources.py)"
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
                         "it, and nothing about the status code says so. Check the "
                         "envelope's KEY NAMES against the app's own loader first; "
                         "that is what broke last time: %s"
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
              "`pip install -c ia/scripts/requirements.txt requests`", file=sys.stderr)
        sys.exit(1)

    findings = Findings()
    check_manifest_matches_app(html, findings)
    check_socrata(findings, args.offline)
    check_provenance(findings, args.offline)
    check_endpoints(findings, args.offline)

    # Which hosts asked to be slowed down, and by how much. On stderr, because
    # stdout is the markdown report that becomes the monthly issue body.
    if not args.offline and PACER is not None:
        for line in PACER.report(prefix=""):
            print(line, file=sys.stderr)

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
