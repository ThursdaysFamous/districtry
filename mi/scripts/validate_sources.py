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
workflow (.github/workflows/mi-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 mi/scripts/validate_sources.py                 # human-readable report
    python3 mi/scripts/validate_sources.py --report r.md   # also write markdown
    python3 mi/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 mi/scripts/validate_sources.py --offline       # manifest↔app checks only
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

# The freshness gate's source manifest for the Michigan instance. Every layer this
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
            "Congressional districts pre-built from TIGERweb by "
            "mi/scripts/build_legislative_boundaries.py. THE DISTRICT FIELD IS "
            "VERSIONED AND THE OLD ONE IS REMOVED, NOT MERELY STALE: this layer "
            "is now '120th Congressional Districts' and its field is CD120; a "
            "query naming the retired CD119 is rejected outright with HTTP 400 "
            "(measured 2026-09-03). On the next roll the builder's field list "
            "and the app's CONGRESS_DISTRICT_FIELDS both need the new name."
        ),
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-mi-congress-roster.yml.",
    },
    {
        "layer": "mi-senate",
        "app_file": "mi-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": "38 Senate districts pre-built from TIGERweb (SLDU) by mi/scripts/build_legislative_boundaries.py; redrawn by the Independent Citizens Redistricting Commission each decennial cycle (WATCH.md).",
    },
    {
        "layer": "mi-house",
        "app_file": "mi-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": "110 House districts pre-built from TIGERweb (SLDL) by mi/scripts/build_legislative_boundaries.py; same redistricting cycle as the Senate.",
    },
    {
        "layer": "mi-senate",
        "app_file": "mi-senate-members.json",
        "source_url": "https://data.openstates.org/people/current/mi.csv",
        "note": "Roster base for BOTH chambers -- name, party, district, e-mail and the member's own site. It carries NO capitol phone or address for any Michigan legislator (measured 0 of 148 rows, 2026-09-03), which is why the Senate needs the enrichment below and the House card ships without an office block.",
    },
    {
        "layer": "mi-senate",
        "app_file": "mi-senate-members.json",
        "source_url": "https://senate.michigan.gov/senators/all-senators/",
        "note": (
            "The Senate's own directory -- Capitol phone, e-mail, office and "
            "contact page for all 38 seats. THE ROSTER IS AN HTML-ESCAPED "
            "ATTRIBUTE on a Lit component (senatorInfo=\"[{&quot;...&quot;}]\"), "
            "not a script assignment: a parser looking for `var senatorInfo = "
            "[...]` finds nothing on a page that plainly contains the data. "
            "Read by mi/scripts/mi_senate_scraper.py."
        ),
    },
    {
        "layer": "detroit-council",
        "app_file": "mi-detroit-council-districts.json",
        "source_url": ("https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/"
                       "services/city_council_districts_2026/FeatureServer/0"),
        "note": (
            "Detroit's seven City Council districts, from the city's own ArcGIS org. "
            "Pre-built by mi/scripts/build_mi_detroit_council.py. "
            "WHAT THIS ROW WATCHES IS A NAME COLLISION, not an outage. The city "
            "publishes FOUR council-district boundary services -- one titled 'Current' "
            "dating from 2016, this one named for 2026, one named for 2013 that was "
            "CREATED in December 2025, and NewDistrictBoundariesOption6, which reads "
            "like a rejected draft and is the same plan redigitised (99.575% point "
            "agreement, measured) -- and their names do not settle which is in force. "
            "The builder decides it by measurement and gates it in both directions: "
            "'Current' must carry geometry identical to this service and the 2013 "
            "archive must differ, and against Census 2020 blocks this plan must balance "
            "(measured 4.28% worst deviation) while the archive must not (13.51%). If "
            "the archived plan ever comes into balance too, the build refuses, because "
            "the test has stopped telling them apart. "
            "THE PLAN'S OWN DATES ARE IN THIS SERVICE'S `description` FIELD -- adopted "
            "by the Council on 2024-02-06, in effect from 2026-01-01 -- so a watcher "
            "reading this row should read that field too; the city states the dates on "
            "the data itself. "
            "A REDRAW REACHES THIS APP ONLY THROUGH THAT BUILDER -- the file is "
            "pre-built and cache-first -- so this row existing is what makes a "
            "vanished or moved service visible at all."
        ),
    },
    {
        "layer": "detroit-council",
        "app_file": "mi-detroit-council-members.json",
        "source_url": "https://detroitmi.gov/government/city-council",
        "blocked": ("Cloudflare managed challenge. Measured 2026-09-05 on the front door, "
                    "this page and robots.txt alike, on the plain requests rung AND the "
                    "stdlib client-hints rung that unblocked Kendall: 'Just a moment...' "
                    "with cf_chl markers every time. This project does not defeat a "
                    "challenge, so the roster is read from the Internet Archive's copy of "
                    "this same page and REACHABLE AGAIN is the actionable state -- it would "
                    "mean the scraper's direct rung can serve and the archive hop can go."),
        "note": (
            "Detroit's nine City Council members -- seven by district, two at large "
            "(2012 charter Art. 4 SS4-101). Built by mi/scripts/mi_detroit_council_scraper.py "
            "into mi/scripts/build_mi_detroit_council_roster.py, weekly. "
            "THE FRESHNESS GUARD IS IN THE SCRAPER, NOT HERE: a snapshot older than 45 days "
            "is refused rather than served, so this roster cannot go quietly stale even "
            "though its source is unreachable. The card prints the snapshot's date. "
            "NO CONTACT SHIPS AND THAT IS THE GAP `detroit-council-contact`, not an "
            "omission: neither this page nor any member's own page carries a single "
            "mailto: or tel: link, measured on both through the Archive."
        ),
    },
    {
        "layer": "city-ward",
        "app_file": "mi-grand-rapids-wards.json",
        "source_url": ("https://services2.arcgis.com/L81TiOwAPO1ZvU9b/arcgis/rest/"
                       "services/CGR_Wards/FeatureServer/0"),
        "note": (
            "Grand Rapids's three City Commission wards, from the city's own ArcGIS org. "
            "Pre-built by mi/scripts/build_mi_grand_rapids_wards.py. "
            "WHAT THIS ROW WATCHES IS AGE, NOT A NAME COLLISION. The city's second ward "
            "service (City_of_Grand_Rapids_Wards) is a DUPLICATE -- identical Shape__Area to "
            "eight decimals -- and the build refuses if the two ever diverge. The live "
            "question is currency: this layer's geometry was last edited 2018-01-24, before "
            "the census it is checked against, while its item description claims it is "
            "'maintained to reflect the most current adopted ward configuration'. The gate is "
            "Michigan's own 2026 voting-precinct layer, which carries a WARD column and "
            "assigns the city's 59 precincts 20/20/19; dissolved by it, it agrees with these "
            "polygons on 99.575% of 4,000 points. If that agreement ever falls below 99%, or "
            "the per-ward precinct counts move, the build refuses -- which is what a redraw "
            "would look like, and is the only thing standing between this app and a "
            "decade-old ward map."
        ),
    },
    {
        "layer": "city-ward",
        "app_file": "mi-grand-rapids-council-members.json",
        "source_url": "https://www.grandrapidsmi.gov/Government/City-Commission",
        "note": (
            "Grand Rapids's City Commission -- two commissioners per ward plus a mayor at "
            "large, seven seats, of which the city publishes six. Built by "
            "mi/scripts/mi_grand_rapids_council_scraper.py into "
            "build_mi_grand_rapids_council.py, weekly. "
            "UNLIKE DETROIT'S NEXT DOOR THIS SOURCE IS DIRECTLY READABLE: the city answers "
            "200 and its robots.txt permits /government/, so there is no archive hop and a "
            "refusal here should FAIL the run rather than fall back to an older copy. "
            "The roster ships `seats` so the card states the unlisted seat; the builder "
            "refuses below five named. Two traps: member e-mail is @grcity.us, NOT the "
            "website's own domain, and 616.456.3000 appears on every member's page and is "
            "the city switchboard, detected rather than hardcoded and hoisted to the body."
        ),
    },
    {
        "layer": "city-ward",
        "app_file": "mi-rochester-hills-wards.json",
        "source_url": ("https://gis.rochesterhills.org/server/rest/services/"
                       "ElectoralDistricts/Election_Dataset/MapServer"),
        "note": (
            "Rochester Hills's four city council districts, from the CITY's own ArcGIS "
            "Server. Pre-built by mi/scripts/build_mi_rochester_hills_wards.py. "
            "THE LAYER IS ONE OF THREE on this service (0 is polling PLACES, a point "
            "layer; 1 is voting precincts), so the index is read from the root and the "
            "name asserted. The district key is `districtid`; `OBJECTID` starts at 6 "
            "because earlier rows were deleted, so a build keyed on it would number the "
            "districts 6..9. Terms are read from the AGO item on arcgis.com "
            "(ac140f8d81b94edc804e34470308c865, shared public, licenseInfo empty) because "
            "this server's root carries no serviceItemId to follow. Currency is gated "
            "against Michigan's own 2026 voting-precinct layer, whose WARD column assigns "
            "the city's 21 precincts 6/5/5/5; dissolved by it, it agrees with these "
            "polygons on 99.725% of 4,000 points. "
            "NO OFFICEHOLDER SHIPS AND THAT IS THE CITY'S OWN CHOICE: "
            "www.rochesterhills.org/robots.txt allows five named bots and then disallows "
            "`*` site-wide, so its maintained council page is not read. The GIS host is "
            "separate, serves no robots.txt, and is not covered by that rule (the Knox "
            "precedent). The layer's own `repname` column is not read either."
        ),
    },
    {
        "layer": "city-ward",
        "app_file": "mi-battle-creek-wards.json",
        "source_url": ("https://services6.arcgis.com/cuKwt0IKP5B84jop/arcgis/rest/"
                       "services/Wards_BC/FeatureServer/0"),
        "note": (
            "Battle Creek's five commission wards, from the City of Battle Creek's own "
            "ArcGIS org. Pre-built by mi/scripts/build_mi_battle_creek_wards.py. "
            "THE LAYER CARRIES A COMMISSIONER NAME PER WARD AND NONE OF THEM SHIP -- four "
            "of the five records were last edited 2023-03-23, Michigan cities elect in odd "
            "Novembers, and a name field carries no publication date and nothing that would "
            "change it when a seat changes hands. The names on the card come from the "
            "city's own commission page instead (the row below). The build strips the "
            "column at the fetch and its shipped-shape check refuses any property but the "
            "ward number. Currency is gated against Michigan's own 2026 voting-precinct "
            "layer, whose WARD column assigns the city's 13 precincts 2/2/3/3/3; dissolved "
            "by it, it agrees with these polygons on 99.450% of 4,000 points, and the build "
            "refuses below 99% or if those per-ward counts move."
        ),
    },
    {
        "layer": "city-ward",
        "app_file": "mi-battle-creek-commission-members.json",
        "source_url": "https://www.battlecreekmi.gov/380/City-Commission",
        "note": (
            "Battle Creek's City Commission -- nine seats: one commissioner from each of "
            "five wards, three at large, and the Mayor. Built by "
            "mi/scripts/mi_battle_creek_commission_scraper.py into "
            "build_mi_battle_creek_commission.py, weekly. "
            "THE PAGE ID MATTERS AND WAS ONCE GUESSED WRONG: /165/City-Commission answers "
            "403 and is not this city's page; /380/City-Commission answers 200. A 403 from "
            "an invented path is a fact about the guess, not about the site, whose "
            "robots.txt permits general crawling. "
            "The page is h-card microformat and is parsed per block, never by document "
            "order -- it renders wards 5, 2, 1, 3, 4. The city states its own composition "
            "in prose on the same page, and the scraper refuses to write unless that prose "
            "and the published cards agree. No per-member e-mail exists: every card's "
            "contact slot is one shared city form, hoisted to the body."
        ),
    },
    {
        "layer": "county-commissioner",
        "app_file": "mi-commissioner-districts.json",
        "source_url": "https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/boundaries/MapServer/10",
        "note": (
            "The flagship: every county's board plan, filed under MCL 46.401-46.405 and "
            "compiled by the Bureau of Elections into one statewide layer -- 619 districts, "
            "all 83 counties. Pre-built by mi/scripts/build_mi_commissioner_districts.py. "
            "TWO WATCHES, AND THE ENDPOINT ONLY CARRIES ONE. Geometry: the layer has no "
            "editingInfo and no date field at all, so a republish is invisible here; the only "
            "machine-readable signal is the AGO item's `modified` epoch at "
            "arcgis.com/sharing/rest/content/items/4c8d0d854ac04d8787cb3cf6dab7fbec (1764783222000 "
            "= 2025-12-03 when last read), together with its title's own vNN suffix. People: the "
            "layer's Commissioner/Party columns are the certified November 2024 winners, not a "
            "roster, and are DROPPED at build -- gap mi-commissioner-roster."
        ),
    },
    {
        "layer": "precinct",
        "app_file": "mi-precincts.json",
        "source_url": "https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/services/2026_Voting_Precincts/FeatureServer/0",
        "note": (
            "3,895 precincts for the 2026 cycle, pre-built by mi/scripts/build_mi_precincts.py. "
            "WATCH THE ORG, NOT THIS URL: a new cycle appears as a NEW SERVICE, and the "
            "OpenData/boundaries MapServer carrying the commissioner layer still stops at 2024 -- "
            "so a check that only reads a MapServer's layer list returns a complete-looking wrong "
            "answer (Michigan went 4,340 -> 3,895 precincts between the cycles). The one query that "
            "settles it is arcgis.com/sharing/rest/search?q=owner:michigan_admin AND precinct."
        ),
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": "All 83 counties pre-built from TIGERweb by mi/scripts/build_state_counties.py. The fabric is WATER-INCLUSIVE -- each Great Lakes county reaches the state water boundary -- which is why the coverage outline dissolves to one ring and a mid-lake point reads inside coverage.",
    },
]

ENDPOINTS = [
    # Phase 3's four fabric layers are LIVE TIGERweb — no builder, no committed
    # data/app file — so a vintage roll reaches them on its own and there is
    # nothing here to rebuild. What this list watches is the endpoint still
    # ANSWERING FOR MICHIGAN: each of these is a returnCountOnly query on
    # STATE='26', so a service moved, renamed or silently emptied for this state
    # surfaces as a WARN instead of as four cards that quietly stop resolving.
    #
    # The counts below are measured 2026-09-04 and are recorded, not asserted:
    # this validator reports, it never edits the app. MCD 1,581 · places 533 ·
    # unified school districts 514 · elementary school districts 27. School
    # layer 1 (SECONDARY) answers ZERO for Michigan and is a recorded drop, so
    # it is deliberately not watched here — there is no layer for it to break.
    {
        "layer": "county-subdivision",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/1/query?where=STATE%3D%2726%27&returnCountOnly=true&f=json",
    },
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2726%27&returnCountOnly=true&f=json",
    },
    {
        "layer": "school-district-unified",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0/query?where=STATE%3D%2726%27&returnCountOnly=true&f=json",
    },
    {
        "layer": "school-district-elementary",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/2/query?where=STATE%3D%2726%27&returnCountOnly=true&f=json",
    },
    # USGS structures layer 38. Counted rather than fetched, because the count
    # is the thing at risk: the service caps a response at 2,000 records and
    # says so with HTTP 200 + exceededTransferLimit rather than an error. The
    # app's loader PAGES for that reason, and min_count below is what makes
    # this row a real tripwire rather than a ping: a count that falls away, or
    # an error envelope arriving as a 200, both surface here. 1,799 measured
    # 2026-09-04.
    {
        "layer": "post-office",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query"
                "?geometry=-90.42%2C41.69%2C-82.12%2C48.31&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 1600,  # 1,799 measured 2026-09-04; floor set below it, not at it
    },
    # Layer 51, THE ONE THAT IS OVER THE CAP: 2,838 measured 2026-09-04 against
    # a 2,000-record ceiling the service reports as HTTP 200 + exceededTransfer-
    # Limit rather than an error.
    #
    # CORRECTED 2026-09-05. This comment used to say the floor was set above
    # 2,000 so that "if this ever answers 2,000 exactly, the app has stopped
    # paging" -- A CHECK THIS ROW CANNOT PERFORM, and the claim shipped in the
    # PR that added it. returnCountOnly is NOT subject to maxRecordCount, so it
    # answers the true count whatever the app does. Measured against this exact
    # envelope: returnCountOnly says 2838, a real feature request on the same
    # layer returns 2000 with exceededTransferLimit set, and the service's own
    # maxRecordCount is 2000. The count endpoint never sees the cap, so it can
    # never see the client hitting it.
    #
    # So this floor watches the SOURCE SHRINKING, exactly like the other three,
    # and the number is above 2,000 only because 2,838 is. WHAT WOULD ACTUALLY
    # CATCH THE CLIENT TRUNCATING is a check on what the app receives, which is
    # what the browser gates are for -- mi/scripts/smoke_test.mjs asserts the
    # pager makes more than one request. A row here cannot substitute for it.
    {
        "layer": "fire-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query"
                "?geometry=-90.42%2C41.69%2C-82.12%2C48.31&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 2500,  # 2,838 measured 2026-09-04; floor set below it, not at it
    },
    # Layer 53. Under the 2,000 cap today (1,290 measured 2026-09-04) and
    # fetched by the paging path regardless; min_count is what turns this from
    # a reachability ping into a check that can see an error envelope.
    {
        "layer": "police-station",
        "url": ("https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query"
                "?geometry=-90.42%2C41.69%2C-82.12%2C48.31&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1"
                "&returnCountOnly=true&f=json"),
        "min_count": 1150,  # 1,290 measured 2026-09-04; floor set below it, not at it
    },
    # ZCTAs carry NO STATE field, so this one is counted by ENVELOPE, in Esri's
    # own {xmin,...} comma form -- the {minLng,...} shape makes TIGERweb answer
    # HTTP 200 with a JSON error envelope (measured 2026-09-04). min_count is
    # what makes this a real check rather than a reachability ping: without it
    # the error envelope reads as a healthy 200.
    #
    # 2,000 IN MICHIGAN'S FULL BOX, AND THAT ROUND NUMBER IS REAL RATHER THAN A
    # CAP -- worth stating, because a count that lands exactly on a power of ten
    # reads like a truncated one. TIGERweb's maxRecordCount on this layer is
    # 100,000, and splitting the envelope at -86.27 counts 1,113 west and 915
    # east: 2,028, which is 2,000 plus the 28 ZCTAs straddling the split and so
    # counted in both halves. Measured 2026-09-05.
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query?where=1%3D1"
                "&geometry=-90.42%2C41.69%2C-82.12%2C48.31&geometryType=esriGeometryEnvelope"
                "&inSR=4326&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 1800,  # 2,000 measured 2026-09-04; floor set below it, not at it
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
            headers={"User-Agent": "District Explorer source validator (+https://districtry.com/mi/)"},
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
                         "out of sync with the app (update mi/scripts/validate_sources.py)"
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
              "`pip install -c mi/scripts/requirements.txt requests`", file=sys.stderr)
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
