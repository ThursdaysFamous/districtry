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
  5. The four court maps: each court's district page, read the way the court
     map builder reads it, still lists the counties of the copy the maps were
     drawn from.                                                          [WARN]
  6. A later law: every measure of every session the Legislature has held
     since 2025 whose short title names a court, a judge or a judicial
     district, and that became law, has been read (LAWS_REVIEWED).        [WARN]
  7. The judges' changes: the court's news page and the Governor's newsroom
     carry no headline after the last one reviewed that could mean a judge
     left or arrived, which build_ms_judges.py's CHANGES would then need.  [WARN]

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
import contextlib
import datetime
import html as html_module
import io
import json
import os
import re
import sys
import time
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
    # The four courts whose judges are elected from districts. Every district
    # is a list of whole counties, dissolved from state-counties.json by
    # ms/scripts/build_ms_court_districts.py out of copies of the courts' pages
    # and the 2025 and 2026 laws kept in data/source/courts/. These rows ask
    # only that each source answers and each file ships; check 5 below asks
    # whether each court's page still lists what was drawn, and check 6 whether
    # a later law has redrawn a district.
    {
        "layer": "ms-supreme-court",
        "app_file": "ms-supreme-court-districts.json",
        "source_url": "https://courts.ms.gov/appellatecourts/sc/scdistricts.php",
        "note": "3 districts, from the Supreme Court's own list of each district's counties.",
    },
    {
        "layer": "ms-court-of-appeals",
        "app_file": "ms-court-of-appeals-districts.json",
        "source_url": "https://courts.ms.gov/appellatecourts/coa/coadistricts.php",
        "note": (
            "5 districts from the Court of Appeals' own list, which also names "
            "the precincts by which two districts divide each of ten counties; "
            "those ten are drawn on their own, naming both districts."
        ),
    },
    {
        "layer": "ms-chancery-court",
        "app_file": "ms-chancery-court-districts.json",
        "source_url": "https://courts.ms.gov/trialcourts/chancerycourt/chancerycourt.php",
        "note": "20 districts in force until 1 January 2027, from the chancery courts' page, held to Senate Bill 2768 (2025).",
    },
    {
        "layer": "ms-chancery-court",
        "app_file": "ms-chancery-court-districts-2027.json",
        "source_url": "https://billstatus.ls.state.ms.us/documents/2025/html/SB/2700-2799/SB2768SG.htm",
        "note": "20 districts from 1 January 2027, from Senate Bill 2768 (2025) and House Bill 1 (2026); the app draws them from that day.",
    },
    {
        "layer": "ms-circuit-court",
        "app_file": "ms-circuit-court-districts.json",
        "source_url": "https://courts.ms.gov/trialcourts/circuitcourt/circuitcourt.php",
        "note": "23 districts in force until 1 January 2027, from the circuit courts' page, held to House Bill 1544 (2025).",
    },
    {
        "layer": "ms-circuit-court",
        "app_file": "ms-circuit-court-districts-2027.json",
        "source_url": "https://billstatus.ls.state.ms.us/documents/2025/html/HB/1500-1599/HB1544SG.htm",
        "note": "22 districts from 1 January 2027, from House Bill 1544 (2025) and House Bill 580 (2026); the app draws them from that day.",
    },
    {
        "layer": "ms-supreme-court",
        "app_file": "ms-judge-roster.json",
        "source_url": "https://courts.ms.gov/appellatecourts/sc/scjustices.php",
        "note": (
            "The judges of all four courts, from the Supreme Court's and the "
            "Court of Appeals' own pages and the Judiciary's chancery and "
            "circuit lists, with the changes since those lists were printed "
            "applied from the court's own news and the Governor's "
            "announcements; rebuilt weekly by update-ms-judges-roster.yml."
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

# ---- the courts' laws and the judges' news (checks 6 and 7) -----------------
#
# The Legislature lists every measure of a session in one file, which is how
# the 2026 laws the court maps read were found (ms/data/source/courts/README.md).
# A session that has not been held answers HTTP 404 (measured 2026-10-16 on the
# 2026 Second Extraordinary Session), so check 6 reads each year's regular
# session and its extraordinary sessions in order until one is missing.
SESSION_LIST = "https://billstatus.ls.state.ms.us/%s/pdf/all_measures/allmsrs.xml"
FIRST_SESSION_YEAR = 2025
# The sessions whose lists were read in full on 2026-10-15; one of these
# answering 404 is a list that moved, not a session that was never held.
SESSIONS_READ = ("2025", "20251E", "2026", "20261E")
# A short title that names a court, a judge or a judicial district. Measured
# on those four lists, it also matches salaries, appropriations and bills that
# died, which is why a person reads each enacted match once and records it.
COURT_TITLE = re.compile(
    r"chancer|circuit court|court district|judicial district|judgeship|subdistrict"
    r"|chancellor|supreme court district|court of appeals|circuit judge"
    r"|judicial redistrict", re.I)
# A measure's list shows only its latest action. These are the wordings for a
# measure that became law, measured on the same four lists ("Partially Vetoed
# By Governor" is how an appropriation the Governor vetoed in part reads).
ENACTED = re.compile(r"approved by governor|law w/?out governor|veto overridden"
                     r"|partially vetoed", re.I)
NOT_LAW = re.compile(r"\bdied\b|\bvetoed\b|veto sustained", re.I)
# Every enacted bill on those four lists whose short title COURT_TITLE matches,
# and what reading it found. A bill read in full that writes a district's
# counties is one ms/scripts/build_ms_court_districts.py reads (its BILLS), and
# check 1 holds the two tables to each other.
LAWS_REVIEWED = {
    ("2025", "HB 1509"): "title read 2026-10-15: district attorneys' salaries",
    ("2025", "HB 1544"): "read in full 2026-10-15: writes the circuit districts (BILLS)",
    ("2025", "SB 2768"): "read in full 2026-10-15: writes the chancery districts (BILLS)",
    ("20251E", "HB 38"): "title read 2026-10-15: the courts' appropriation",
    ("20251E", "HB 49"): ("read in full 2026-10-15: changes only the number of "
                          "assistant district attorneys"),
    ("2026", "HB 1"): ("read in full 2026-10-15: the Third Chancery District, its "
                       "counties unchanged (BILLS)"),
    ("2026", "HB 580"): ("read in full 2026-10-15: the Fourth and Seventh Circuit "
                         "Districts, their counties unchanged (BILLS)"),
    ("2026", "HB 1931"): "title read 2026-10-15: the courts' appropriation",
}

# The court's news page lists its 15 latest articles, about seven weeks of them
# on 2026-10-16. Every article numbered from 3098 (1 August 2025, the date of
# the older of the two trial lists) to COURT_NEWS_REVIEWED was read by number on
# 2026-10-15 or 2026-10-16 (3172 was "File not found"), and three of them are
# sources in build_ms_judges.py's CHANGES.
COURT_NEWS = "https://courts.ms.gov/news/news.php"
COURT_NEWS_ARTICLE = "https://courts.ms.gov/news/view_news_page.php?article=%d"
COURT_NEWS_REVIEWED = 3171
# The Governor fills a judge's vacancy by appointment and announces it in the
# newsroom, four or five releases a page. Every headline dated from January
# 2024 to GOVERNOR_NEWS_REVIEWED was read (26 pages, 2026-10-15; page 1 again
# 2026-10-16), and two are sources in CHANGES.
GOVERNOR_NEWS = "https://governorreeves.ms.gov/newsroom/"
GOVERNOR_NEWS_PAGE = "https://governorreeves.ms.gov/newsroom/paged-2/%d/"
GOVERNOR_NEWS_REVIEWED = "2026-10-15"
GOVERNOR_NEWS_PAGES = 6
JUDGE_WORD = re.compile(r"\b(judges?|chancellors?|justices?|chancery|circuit|court)\b", re.I)
COURT_CHANGE = re.compile(r"\b(died|dies|death|passed away|retire[sd]?|retiring|resign\w*"
                          r"|appoint\w*|oath|sworn|takes office|elected|vacan\w*"
                          r"|special elections?)\b", re.I)
GOVERNOR_CHANGE = re.compile(r"\b(appoint\w*|vacan\w*|special elections?)\b", re.I)

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
# without the GoDaddy intermediate, measured the same day, and
# billstatus.ls.state.ms.us, where the Legislature publishes its bills and its
# lists of measures (checks 5 and 6), sends its own without the GlobalSign one.
PINNED_CHAINS = {"www.legislature.ms.gov": "globalsign-rsa-ov-2018",
                 "gis.cmpdd.org": "godaddy-g2",
                 "billstatus.ls.state.ms.us": "globalsign-rsa-ov-2018"}
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


def http_get(url, want_json=True, params=None, attempts=1):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises.
    `attempts` above 1 retries a dropped connection, which courts.ms.gov does
    now and then (measured 2026-10-15 and 2026-10-16); an HTTP answer is never
    retried."""
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
    kwargs = {"verify": verify} if verify else {}
    for attempt in range(attempts):
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": ua},
                **kwargs
            )
            break
        except Exception as e:  # network/TLS/proxy errors are a finding, not a crash
            if attempt + 1 == attempts:
                return False, "request failed: %s" % e
            time.sleep(6.0 * (attempt + 1))
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
    # The court maps depend on the laws in the court map builder's BILLS, so
    # each must be one check 6 records as read; and the judges' CHANGES cite
    # the court's news by article, so none may be newer than the article check 7
    # treats as the last one reviewed.
    try:
        import build_ms_court_districts as courts
        import build_ms_judges as judges
    except Exception as e:  # a broken import is a finding, not a crash
        findings.add(FAIL, "court districts (laws)",
                     "could not read the court builders: %s" % e)
    else:
        for bill, name in courts.BILLS:
            m = re.search(r"/documents/(\w+)/html/(HB|SB)/[\d-]+/(?:HB|SB)0*(\d+)SG\.htm$",
                          courts.SOURCES[bill][0])
            key = (m.group(1), "%s %s" % (m.group(2), m.group(3))) if m else None
            if key not in LAWS_REVIEWED:
                findings.add(FAIL, "court districts (laws)",
                             "the court maps read %s (%s), and LAWS_REVIEWED does not "
                             "record it, so check 6 would report it unread"
                             % (name, courts.SOURCES[bill][0]))
        for ch in judges.CHANGES:
            m = re.search(r"[?&]article=(\d+)", ch["source"]["url"])
            if m and int(m.group(1)) > COURT_NEWS_REVIEWED:
                findings.add(FAIL, "judges (news)",
                             "CHANGES cites the court's article %s, after "
                             "COURT_NEWS_REVIEWED (%d); raise it once the articles "
                             "between have been read" % (m.group(1), COURT_NEWS_REVIEWED))
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


# ---- check 5: the courts' district pages still list what was drawn ---------
def check_court_pages(findings, offline):
    """The four court maps are drawn from the counties each court's page lists,
    read from copies kept in data/source/courts/. A court that changes its page
    changes no file here, so the page as served now is parsed the court map
    builder's own way and compared with the copy."""
    if offline:
        return
    import build_ms_court_districts as courts
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for name, layer in sorted(courts.PAGES.items()):
        url, read_on, _sha = courts.SOURCES[name]
        ok, res = http_get(url, want_json=False, attempts=3)
        time.sleep(3.0)
        if not ok:
            findings.add(WARN, layer, "the court's district page could not be read "
                         "(%s), so the map was not checked against it: %s" % (res, url))
            continue
        said = io.StringIO()
        try:
            with contextlib.redirect_stdout(said):
                changes = courts.page_changes(name, res.content)
        except SystemExit:
            findings.add(WARN, layer, "the court's district page no longer reads the "
                         "way the copy of %s did, so the map cannot be checked against "
                         "it (%s): %s" % (read_on, " ".join(said.getvalue().split()), url))
            continue
        if not changes:
            findings.add(OK, layer, "the court's district page still lists the "
                         "counties of the copy of %s: %s" % (read_on, url))
            continue
        expected = ("From 1 January 2027 the chancery and circuit pages are "
                    "expected to list the 2027 districts; if that is the change, "
                    "retire the until-2027 files at the same time (ms/WATCH.md). "
                    if today >= courts.REDRAW and name in ("chancery-districts.htm",
                                                           "circuit-districts.htm")
                    else "")
        findings.add(WARN, layer, "the court's district page now lists different "
                     "counties from the copy the map was drawn from: %s. %sRe-read "
                     "the page into ms/data/source/courts/, record its hash and date in "
                     "build_ms_court_districts.py's SOURCES, and rebuild: %s"
                     % ("; ".join(changes), expected, url))
    if today >= courts.REDRAW:
        still = [n for _c, _p, n, *_r in courts.TRIAL
                 if os.path.exists(os.path.join(APP_DATA_DIR, n))]
        if still:
            findings.add(WARN, "ms-chancery-court", "it is %s and %s still ship. The "
                         "app has drawn the 2027 districts since 1 January 2027; retire "
                         "the until-2027 files (ms/WATCH.md)." % (today, ", ".join(still)))


# ---- check 6: a later law that writes a court district ----------------------
def _tag(tag, text):
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), text, re.S)
    return " ".join(html_module.unescape(m.group(1)).split()) if m else ""


def session_measures(raw):
    """[(measure, short title, latest action)] for the bills on one session's
    list of all measures, each named "HB 1544". The list pads a number to four
    places with spaces ("HB   1", "HB1544"). Nominations (SN) and resolutions
    are not laws."""
    text = raw.decode("latin-1")
    out = []
    for group in re.findall(r"<MSRGROUP>(.*?)</MSRGROUP>", text, re.S):
        m = re.match(r"^(HB|SB)\s*(\d+)$", _tag("MEASURE", group))
        if m:
            out.append(("%s %d" % (m.group(1), int(m.group(2))),
                        _tag("SHORTTITLE", group), _tag("ACTION", group)))
    return out


def check_court_laws(findings, offline):
    """Every bill of every session held since 2025 whose short title names a
    court, a judge or a judicial district, and that became law, must be one a
    person has read and recorded in LAWS_REVIEWED: a law that redraws a court
    district changes the map on the day it takes effect, and nothing else here
    would notice it. A matching bill still before the Legislature is listed,
    and is not yet a finding."""
    if offline:
        return
    label = "court districts (laws)"
    today = datetime.datetime.now(datetime.timezone.utc).date()
    seen, read, unread = set(), set(), []
    for year in range(FIRST_SESSION_YEAR, today.year + 2):
        for k in range(0, 10):
            session = str(year) if k == 0 else "%d%dE" % (year, k)
            ok, res = http_get(SESSION_LIST % session, want_json=False, attempts=2)
            time.sleep(3.0)
            if not ok:
                if res == "HTTP 404" and session not in SESSIONS_READ:
                    if k:  # extraordinary sessions are numbered in order
                        break
                    continue
                findings.add(WARN, label, "the list of every measure of the %s session "
                             "could not be read (%s), so no law of that session was "
                             "checked: %s" % (session, res, SESSION_LIST % session))
                if k:
                    break
                continue
            measures = session_measures(res.content)
            if not measures:
                findings.add(WARN, label, "the list of every measure of the %s session "
                             "answered with no bills in it, so its layout has probably "
                             "changed: %s" % (session, SESSION_LIST % session))
                continue
            read.add(session)
            pending = []
            for measure, title, action in measures:
                if not COURT_TITLE.search(title):
                    continue
                key = (session, measure)
                if ENACTED.search(action):
                    seen.add(key)
                    if key not in LAWS_REVIEWED:
                        unread.append(key)
                        findings.add(WARN, label, "%s of the %s session became law (%s) "
                                     "and no one here has read it: \"%s\". If it writes a "
                                     "chancery, circuit, Court of Appeals or Supreme Court "
                                     "district, add it to build_ms_court_districts.py's "
                                     "BILLS and SOURCES and rebuild; either way, record "
                                     "what it does in LAWS_REVIEWED. %s"
                                     % (measure, session, action, title,
                                        SESSION_LIST % session))
                elif not NOT_LAW.search(action):
                    pending.append("%s (%s)" % (measure, action))
            if pending:
                findings.add(OK, label, "%s session: still before the Legislature and "
                             "naming a court in their titles: %s"
                             % (session, "; ".join(pending)))
    for key in sorted(LAWS_REVIEWED):
        if key[0] in read and key not in seen:
            findings.add(WARN, label, "LAWS_REVIEWED records %s of the %s session as a "
                         "law, and that session's list no longer shows it as one"
                         % (key[1], key[0]))
    if read and not unread:
        findings.add(OK, label, "%d session(s) read (%s); every enacted bill naming a "
                     "court in its title is one LAWS_REVIEWED records"
                     % (len(read), ", ".join(sorted(read))))


# ---- check 7: news that a judge has left or arrived -------------------------
COURT_NEWS_ITEM = re.compile(
    r"article=(\d+)&name=[^']*'[^>]*>\s*<span[^>]*>(.*?)</span></a>\s*"
    r"<span class='newsdatetext'><br>([^<]*)</span>", re.S)
GOVERNOR_NEWS_ITEM = re.compile(
    r'itemprop="mainEntityOfPage"[^>]*itemid="([^"]+)"[^>]*content="([^"]*)"\s*/>'
    r'<meta itemprop="datePublished" content="(\d{4}-\d\d-\d\d)"')


def check_judge_news(findings, offline):
    """The judges' lists lag the bench by months, so build_ms_judges.py applies
    the changes since from the court's own news and the Governor's
    announcements (CHANGES). Nothing tells this project of the next one, so
    both newsrooms are read for headlines after the last one reviewed."""
    if offline:
        return
    label = "judges (news)"
    ok, res = http_get(COURT_NEWS, want_json=False, attempts=3)
    time.sleep(3.0)
    if not ok:
        findings.add(WARN, label, "the court's news page could not be read (%s): %s"
                     % (res, COURT_NEWS))
    else:
        items = [(int(n), " ".join(html_module.unescape(re.sub(r"<[^>]+>", " ", t)).split()),
                  d.strip())
                 for n, t, d in COURT_NEWS_ITEM.findall(res.text)]
        if not items:
            findings.add(WARN, label, "the court's news page no longer reads as a list "
                         "of headlines: %s" % COURT_NEWS)
        else:
            newer = [i for i in items if i[0] > COURT_NEWS_REVIEWED]
            for n, title, when in newer:
                if JUDGE_WORD.search(title) and COURT_CHANGE.search(title):
                    findings.add(WARN, label, "the court's news, %s: \"%s\". If a "
                                 "judge left or arrived, add or retire an entry in "
                                 "build_ms_judges.py's CHANGES; then raise "
                                 "COURT_NEWS_REVIEWED past it: %s"
                                 % (when, title, COURT_NEWS_ARTICLE % n))
            oldest = min(i[0] for i in items)
            if oldest > COURT_NEWS_REVIEWED + 1:
                findings.add(WARN, label, "the court's news page now starts at article "
                             "%d, so articles %d to %d left it unread here. Read them at "
                             "%s, then raise COURT_NEWS_REVIEWED."
                             % (oldest, COURT_NEWS_REVIEWED + 1, oldest - 1,
                                COURT_NEWS_ARTICLE % (COURT_NEWS_REVIEWED + 1)))
            findings.add(OK, label, "the court's news page: %d headline(s) after article "
                         "%d" % (len(newer), COURT_NEWS_REVIEWED))
    seen, newest_page_older = {}, False
    for page in range(1, GOVERNOR_NEWS_PAGES + 1):
        url = GOVERNOR_NEWS if page == 1 else GOVERNOR_NEWS_PAGE % page
        ok, res = http_get(url, want_json=False, attempts=2)
        time.sleep(3.0)
        if not ok:
            findings.add(WARN, label, "the Governor's newsroom could not be read (%s): %s"
                         % (res, url))
            break
        items = GOVERNOR_NEWS_ITEM.findall(res.text)
        if len(items) < 2:
            findings.add(WARN, label, "the Governor's newsroom no longer reads as a list "
                         "of dated releases: %s" % url)
            break
        for link, title, when in items:
            seen.setdefault(link, (html_module.unescape(title), when))
        # The first release on every page is the same pinned one, so the page's
        # own order is read from the rest.
        if min(when for _l, _t, when in items[1:]) <= GOVERNOR_NEWS_REVIEWED:
            newest_page_older = True
            break
    if seen and not newest_page_older:
        findings.add(WARN, label, "the Governor's newsroom carries more than %d pages of "
                     "releases after %s, so some were not read here; read them, then "
                     "raise GOVERNOR_NEWS_REVIEWED." % (GOVERNOR_NEWS_PAGES,
                                                        GOVERNOR_NEWS_REVIEWED))
    newer = [(when, title, link) for link, (title, when) in seen.items()
             if when > GOVERNOR_NEWS_REVIEWED]
    for when, title, link in sorted(newer):
        if JUDGE_WORD.search(title) and GOVERNOR_CHANGE.search(title):
            findings.add(WARN, label, "the Governor's newsroom, %s: \"%s\". If it fills "
                         "or opens a judge's seat, add or update the entry in "
                         "build_ms_judges.py's CHANGES; then raise "
                         "GOVERNOR_NEWS_REVIEWED: %s" % (when, title, link))
    if seen:
        findings.add(OK, label, "the Governor's newsroom: %d release(s) after %s"
                     % (len(newer), GOVERNOR_NEWS_REVIEWED))


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
        check_court_pages(findings, args.offline)
        check_court_laws(findings, args.offline)
        check_judge_news(findings, args.offline)
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
