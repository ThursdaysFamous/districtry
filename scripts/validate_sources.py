#!/usr/bin/env python3
"""
Source freshness gate for the app's data layers.

Why this exists: unlike the roster scrapers (which re-pull the same page every
week), several layers point at a *specific* upstream dataset that the publisher
silently supersedes with a new one:

  * Chicago Data Portal (Socrata) datasets are versioned by year. The CPS
    attendance-boundary layers, for example, are published fresh every school
    year under a BRAND NEW dataset id (…SY2526 → …SY2627), so the id hardcoded
    in index.html keeps returning last year's boundaries long after a newer one
    exists. Nothing errors; the data just quietly goes stale.
  * The three shapefile-derived boundary layers (school board, IL Supreme
    Court, Cook County Board of Review) were downloaded once from decennial
    redistricting sources with no API. They change ~once a decade, so the check
    there is provenance: is the source we cite still reachable, and a reminder
    to re-verify.

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
  4. Live service endpoints (CPD ArcGIS, Census TIGERweb): reachable.      [WARN]

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
INDEX_HTML = os.path.join(REPO_ROOT, "il", "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

HTTP_TIMEOUT = 25

# ==== TEMPLATE:BEGIN sources-manifest ====
SOCRATA_DOMAIN = "data.cityofchicago.org"
CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"

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
    {"id": "p293-wvbd", "layer": "Ward + Alderman boundary",
     "name_contains": "Boundaries - Wards"},
    {"id": "htai-wnw4", "layer": "Alderman / Ward Offices",
     "name_contains": "Ward Offices"},
    {"id": "i8fv-xe4b", "layer": "Ward Precincts",
     "name_contains": "Boundaries - Ward Precincts"},
    {"id": "igwz-8jzy", "layer": "Community Area",
     "name_contains": "Boundaries - Community Areas"},
    # ZIP Code moved off Socrata to the statewide Census ZCTA layer (no city
    # boundary line) — the endpoint is tracked in ENDPOINTS below, not here.
    {"id": "x8fc-8rcq", "layer": "Library locations (nearest N)",
     "name_contains": "Libraries - Locations"},
    {"id": "x72b-38qv", "layer": "CPS Elementary School Zone",
     "name_contains": "Elementary School Attendance Boundaries",
     "year_search": {"query": "Elementary School Attendance Boundaries",
                     "pattern": r"SY(\d{4})"}},
    {"id": "xg7c-d8rm", "layer": "CPS High School Zone",
     "name_contains": "High School Attendance Boundaries",
     "year_search": {"query": "High School Attendance Boundaries",
                     "pattern": r"SY(\d{4})"}},
    {"id": "fyff-53xy", "layer": "CPS Middle School Zone",
     "name_contains": "Middle School Attendance Boundaries",
     "year_search": {"query": "Middle School Attendance Boundaries",
                     "pattern": r"SY(\d{4})"}},
    {"id": "pnta-kuqa", "layer": "CPS Network (K-8)",
     "name_contains": "Elementary Geographic Networks"},
    {"id": "aupu-jt2g", "layer": "CPS Network (High School)",
     "name_contains": "High School Geographic Networks"},
]

# Decennial boundary layers built into same-origin data/app files: no runtime
# API. `source_url` is the provenance we cite; `app_file` is the built file.
# These go stale only when the underlying districts are redrawn — the check is a
# reachability probe plus a standing reminder to re-verify against the source.
# The first three are shapefile-derived; the three legislative layers are
# pre-built from Census TIGERweb by scripts/build_legislative_boundaries.py
# (R2-2 — they used to query TIGERweb live at ~5.7 s per first toggle).
# Rock Island's TaxDistricts service root — the provenance of three pre-built
# files below and deliberately absent from ENDPOINTS (nothing fetches it at
# runtime any more).
SERVICE_RI_TAX = ("https://services9.arcgis.com/6FnscPPlUa9DXXOk/arcgis/rest/"
                  "services/TaxDistricts/FeatureServer?f=json")
# Kendall's Hosted root also serves live layers (board, polling); this URL is
# provenance for its three pre-built tax tilings specifically.
SERVICE_KENDALL_TAX = ("https://maps.co.kendall.il.us/server/rest/services/"
                       "Hosted?f=json")
SERVICE_GRUNDY_PARCELS = ("https://maps.grundyco.org/arcgis/rest/services/CountyWebsiteMaps/"
                          "CountyParcelsBaseLayer_ParcelFabric_SPIE/MapServer/0")
SERVICE_WOODFORD = ("https://services1.arcgis.com/iOG1OLysrxLAswZi/arcgis/rest/"
                    "services/%s/FeatureServer/%d")
SERVICE_WOODFORD_FIRE = SERVICE_WOODFORD % ("Fire_Protection_Districts", 2)
SERVICE_WOODFORD_LIBRARY = SERVICE_WOODFORD % ("Library_Districts", 8)
SERVICE_WOODFORD_PARK = SERVICE_WOODFORD % ("Park_Districts", 9)
SERVICE_MACON_ORG = ("https://services1.arcgis.com/a3k0qIja5SolIRYR/arcgis/"
                     "rest/services?f=json")

PROVENANCE = [
    {"layer": "School Board (ERSB) districts",
     "app_file": "school-board-districts.json",
     "source_url": "https://www.ilsenateredistricting.com/",
     "note": "ERSB 20-subdistrict map (SB 15). Redrawn ~once a decade."},
    {"layer": "IL Supreme Court districts",
     "app_file": "il-supreme-court-districts.json",
     "source_url": "https://www.illinoiscourts.gov/",
     "note": "PA 102-0011 shapefile. Redrawn ~once a decade."},
    {"layer": "Cook County Board of Review districts",
     "app_file": "ccbr-districts.json",
     "source_url": "https://www.cookcountyboardofreview.com/",
     "note": "PA 102-0012 shapefile. Redrawn ~once a decade."},
    {"layer": "Kane 16th-Circuit judicial subcircuits",
     "app_file": "kane-judicial-subcircuits.json",
     "source_url": "https://www.ilsenateredistricting.com/",
     "note": "PA 102-0693 enacted-subcircuits shapefile ZIP (archived in "
             "data/source/raw/). Redrawn ~once a decade; the county's own "
             "services are permission-locked, hence the shapefile route."},
    {"layer": "McHenry 22nd-Circuit judicial subcircuits",
     "app_file": "mchenry-judicial-subcircuits.json",
     "source_url": "https://www.ilsenateredistricting.com/",
     "note": "Same PA 102-0693 enacted-subcircuits shapefile ZIP as Kane "
             "(archived in data/source/raw/). Redrawn ~once a decade; the "
             "county publishes no subcircuit service at all."},
    {"layer": "Ogle County Board districts (8, dissolved from Census 2020 precincts)",
     "app_file": "ogle-county-board-districts.json",
     "source_url": "https://www.oglecountyil.gov/county/resolutions_and_ordinances/index.php",
     "note": "Resolution R-2021-1106, ADOPTION OF THE OGLE COUNTY REAPPORTIONMENT "
             "MAP (adopted 2021-11-16), names the 52 precincts making up the 8 "
             "districts; build_ogle_board_districts.py dissolves the Census 2020 "
             "voting districts accordingly. The county publishes no district "
             "geometry. Supersedes R-2021-0607 (June 2021), whose District 5 "
             "omitted Leaf River entirely. Next reapportionment due after the "
             "2030 census; the pinned URL is the county's resolutions index, "
             "since the monthly PDF filename changes."},
    {"layer": "Carroll County Board districts (3, whole townships)",
     "app_file": "carroll-county-board-districts.json",
     "source_url": "https://www.carrollcountyil.gov/County.Board.District.Update.2021.pdf",
     "note": "The county's published 2021 district map, whose lines run exactly "
             "along township boundaries, so the districts are a plain TIGER "
             "township dissolve (build_carroll_board_districts.py). The map is a "
             "RASTER export with no polygons to extract — none were needed. The "
             "map labels Carroll's two consolidated townships by their historic "
             "halves (Cherry Grove/Shannon, Rock Creek/Lima) where TIGER carries "
             "the merged names; both sit wholly in District 3. Redrawn ~once a "
             "decade."},
    {"layer": "Stephenson County Board districts (8, lettered B-I; B-E georeferenced)",
     "app_file": "stephenson-county-board-districts.json",
     "source_url": "https://stephensoncountyil.gov/government/county_board/district_maps_2012.php",
     "note": "The county's adopted 2022-01-06 district maps. F-I are whole "
             "townships (exact, and each district's township populations sum to "
             "the total the map prints). B-E subdivide Freeport Township and are "
             "GEOREFERENCED from the Freeport map's vector precinct polygons "
             "(build_stephenson_board_districts.py; PDFs archived in "
             "data/source/raw/) — the only boundary in the app whose accuracy is "
             "a measured number rather than an exact match, ~20 m, stated on the "
             "card. DELETE that script if Stephenson ever publishes precinct "
             "geometry. Redrawn ~once a decade."},
    {"layer": "Winnebago 17th-Circuit judicial subcircuits",
     "app_file": "winnebago-judicial-subcircuits.json",
     "source_url": "https://www.ilsenateredistricting.com/",
     "note": "PA 102-0693 enacted-subcircuits shapefile ZIP (archived in "
             "data/source/raw/) — the SAME archive Kane and McHenry were built "
             "from, which carries nine circuits where the app long shipped six. "
             "17th Circuit = Winnebago + Boone, the first counties outside the "
             "seven-county metro. Redrawn ~once a decade."},
    {"layer": "Madison 3rd-Circuit judicial subcircuits",
     "app_file": "madison-judicial-subcircuits.json",
     "source_url": "https://www.ilsenateredistricting.com/",
     "note": "Same PA 102-0693 archive. 3rd Circuit = Madison + Bond "
             "(Metro East). Redrawn ~once a decade."},
    {"layer": "Sangamon 7th-Circuit judicial subcircuits",
     "app_file": "sangamon-judicial-subcircuits.json",
     "source_url": "https://www.ilsenateredistricting.com/",
     "note": "Same PA 102-0693 archive. 7th Circuit = Sangamon + Greene, "
             "Jersey, Macoupin, Morgan and Scott — the widest of the three, so "
             "this one file answers for six counties. Redrawn ~once a decade."},
    # Rock Island's three TaxDistricts concept layers are PRE-BUILT rather than
    # fetched live (the only county here whose live-API layers were retired for
    # a same-origin build): the service's tilings are dissolved from the parcel
    # fabric, which excludes road right-of-way, so raw they render as void-split
    # lattices and road clicks landed in no district. The builder closes the
    # road voids at 75 ft and pins each layer's dataLastEditDate (all
    # 2022-01-14), so a county re-edit fails the rebuild loudly — this monthly
    # probe watches that the source itself stays reachable. The board/precinct
    # layers (Other_Layers service, below) are clean polygons and stay live.
    {"layer": "Rock Island County fire districts (pre-built, road voids closed)",
     "app_file": "rock-island-fire-districts.json",
     "source_url": SERVICE_RI_TAX,
     "note": "17 fire protection districts from TaxDistricts layer 2 "
             "(build_parcel_fabric_districts.py). Rebuild only after "
             "re-verifying the script's pinned edit dates and measurements."},
    {"layer": "Rock Island County library districts (pre-built, road voids closed)",
     "app_file": "rock-island-library-districts.json",
     "source_url": SERVICE_RI_TAX,
     "note": "9 named library districts from TaxDistricts layer 5; the "
             "blank-named tenth row (a stray UNITED TWP HIGH 30 school-polygon "
             "copy) is asserted and excluded at build time."},
    {"layer": "Rock Island County park district (pre-built, road voids closed)",
     "app_file": "rock-island-park-districts.json",
     "source_url": SERVICE_RI_TAX,
     "note": "The county's single levied park district (Cordova), TaxDistricts "
             "layer 8."},
    # The 2026-08-16 fabric survey measured every fire/library/park source for
    # EMPTY road-band voids (a parcel-derived tiling excludes right-of-way, so
    # roads render as dead lattice). The severe tier below ships pre-built by
    # scripts/build_parcel_fabric_districts.py — same transform and guards as
    # Rock Island's three above; the moderate tier keeps live fetch plus the
    # 60 ft runtime snap in index.html.
    {"layer": "Kendall County fire districts (pre-built, road voids closed)",
     "app_file": "kendall-fire-districts.json",
     "source_url": SERVICE_KENDALL_TAX,
     "note": "10 FPDs dissolved from 170 tax-code rows (977 empty voids "
             "measured raw); the municipal Joliet row excluded at build time. "
             "No upstream edit stamp — count+names pinned in the builder."},
    {"layer": "Kendall County park districts (pre-built, road voids closed)",
     "app_file": "kendall-park-districts.json",
     "source_url": SERVICE_KENDALL_TAX,
     "note": "5 park districts dissolved from 65 tax-code rows (578 empty "
             "voids measured raw)."},
    {"layer": "Kendall County library districts (pre-built, road voids closed)",
     "app_file": "kendall-library-districts.json",
     "source_url": SERVICE_KENDALL_TAX,
     "note": "9 library taxing bodies dissolved from 145 tax-code rows (1,158 "
             "empty voids measured raw); municipal city-library funds stay, "
             "the Cook-style complete shape."},
    {"layer": "Macon County fire districts (pre-built, road voids closed)",
     "app_file": "macon-fire-districts.json",
     "source_url": SERVICE_MACON_ORG,
     "note": "17 districts (1,318 empty voids measured raw — the fleet's "
             "worst); names verbatim as the county writes them; upstream edit "
             "date pinned in the builder."},
    {"layer": "Macon County library districts (pre-built, road voids closed)",
     "app_file": "macon-library-districts.json",
     "source_url": SERVICE_MACON_ORG,
     "note": "10 districts (960 empty voids measured raw despite the "
             "'Join_Dissolved' upstream name — the dissolve kept the parcel "
             "voids); edit date pinned."},
    {"layer": "Macon County park districts (pre-built, road voids closed)",
     "app_file": "macon-park-districts.json",
     "source_url": SERVICE_MACON_ORG,
     "note": "6 districts (556 empty voids measured raw); edit date pinned."},
    {"layer": "Cook County suburban fire protection districts (pre-built, road voids closed)",
     "app_file": "cook-fire-districts.json",
     "source_url": ("https://gis.cookcountyil.gov/traditional/rest/services/"
                    "politicalBoundary/MapServer/17?f=json"),
     "note": "40 FPDs from the Clerk's L17 tax-agency tiling (102 empty voids "
             "measured raw). Seven district pairs the Clerk's own tiling "
             "DOUBLE-CLAIMS (Orland∩Mokena, 57 acres) ship in both, exactly "
             "as the live layer answers. The Clerk refreshes tilings in "
             "place with no edit stamp, so the builder pins count+names and "
             "this monthly probe is the freshness watch."},
    # Grundy's three come off ONE 27,661-row parcel fabric whose single
    # `Districts` column lists every taxing body a parcel pays into. The service
    # publishes no edit stamp AND cannot page (supportsPagination false), so the
    # builder pins the row count per concept and this probe is the freshness
    # watch on the service itself.
    {"layer": "Grundy County fire districts (pre-built from the parcel fabric)",
     "app_file": "grundy-fire-districts.json",
     "source_url": SERVICE_GRUNDY_PARCELS + "?f=json",
     "note": "13 districts dissolved from the 27,141 parcels whose Districts "
             "cell names one; the set and the shipped names both come from the "
             "county's own 2025 Tax Distribution List with EAV (which names "
             "no office and does not say 'certified'). MVK "
             "RESCUE SQUAD is excluded: the county names it the Mazon Verona "
             "Kinsman Rescue Squad District (70 ILCS 2005/6, its own board and "
             "levy), and a rescue-squad district is not a fire protection "
             "district. Its 2,257 parcels are exactly the union of Mazon and "
             "Verona-Kinsman."},
    {"layer": "Grundy County library districts (pre-built from the parcel fabric)",
     "app_file": "grundy-library-districts.json",
     "source_url": SERVICE_GRUNDY_PARCELS + "?f=json",
     "note": "6 library districts from 24,485 parcels; 69.8% of the county is "
             "in one and the rest is honestly in none."},
    {"layer": "Grundy County park districts (pre-built from the parcel fabric)",
     "app_file": "grundy-park-districts.json",
     "source_url": SERVICE_GRUNDY_PARCELS + "?f=json",
     "note": "2 districts (Channahon, Godley) from 1,779 parcels — most of the "
             "county sits in no park district."},
    # Woodford's three come off ONE 25,824-row parcel fabric published three
    # times over — the county draws no district tiling at all — so each entry
    # names the service its own column lives on. The builder PINS each layer's
    # dataLastEditDate, so a re-run against a changed roll fails rather than
    # silently redrawing a district; this monthly probe is the earlier warning.
    {"layer": "Woodford County fire districts (pre-built from the parcel fabric)",
     "app_file": "woodford-fire-districts.json",
     "source_url": SERVICE_WOODFORD_FIRE + "?f=json",
     "note": "17 districts dissolved from the 24,123 parcels whose Fire_Prote "
             "column names one; corroborated by the county's own 2025 "
             "settlement sheets, which levy for exactly these 17 (that "
             "document names no office and does not say 'certified'). This "
             "item's description dates the ORIGINAL shapes to 2007 IDOR data, "
             "but a parcel's district follows its tax code and all 119 codes "
             "map to one district per concept, so the attribution is current "
             "with the 2025 levy. The Village of Metamora is a measured hole "
             "— it runs its own department."},
    {"layer": "Woodford County library districts (pre-built from the parcel fabric)",
     "app_file": "woodford-library-districts.json",
     "source_url": SERVICE_WOODFORD_LIBRARY + "?f=json",
     "note": "6 library bodies from 22,551 parcels. One is municipal (Minonk "
             "City Library) and its feature carries a note the card renders: "
             "the county's parcel table and its corporate-boundary layer "
             "disagree about five of its 1,230 parcels."},
    {"layer": "Woodford County park districts (pre-built from the parcel fabric)",
     "app_file": "woodford-park-districts.json",
     "source_url": SERVICE_WOODFORD_PARK + "?f=json",
     "note": "3 districts from 4,113 parcels; most of the county sits in no "
             "park district and the empty state is the true answer there."},
    # The statewide library layer behind SEVEN counties' library cards, and it
    # had NO entry here at all until Macoupin joined it — six counties' geometry
    # riding an unwatched source. It is the one boundary in this instance
    # published by neither the county nor the body, so a monthly probe matters
    # more here than most: the publisher is a broadband contractor and the
    # counties it covers have no other library boundary to fall back on.
    {"layer": "Illinois library districts (statewide layer behind 7 counties)",
     "app_file": "macoupin-library-districts.json",
     "source_url": "https://services.arcgis.com/R0IGaIgf2sox9aCY/arcgis/rest/services/"
                   "IL_Boundary_Layers/FeatureServer/11?f=json",
     "note": "Illinois Broadband Office / Connected Nation, layer 11 — 642 polygons "
             "statewide, clipped per county by build_statewide_library_districts.py "
             "for Carroll, Lee, Macoupin, Randolph, Sangamon, St. Clair and "
             "Stephenson. NOT a county or library publication; the item states "
             "public use permitted, no warranty, not for legal boundary "
             "determinations, with attribution and modification-disclosure "
             "requirements the cards carry. TWO counties check it against their own "
             "Clerk's tax lines and the builder refuses to write if either stops "
             "matching: Carroll's seven, and Macoupin's eleven across all 224 of "
             "that county's tax codes."},
    {"layer": "Kane County Board members (roster)",
     "app_file": "kane-county-board-members.json",
     "source_url": "https://www2.kanecountyil.gov/pages/countyboard/boardMembers.aspx",
     "note": "Scraped weekly from the county's own SharePoint Board Members list "
             "API (kane_county_board_scraper.py) — the same data this directory "
             "page renders client-side: party, office phones, emails, and the "
             "countywide-elected Chair. No bot block (verified 2026-07-23); the "
             "boundary GIS separately carries member names (cross-checked)."},
    {"layer": "Lake County Board leadership roles (roster)",
     "app_file": "lake-county-board-roles.json",
     "source_url": "https://www.lakecountyil.gov/2336/Board-Members",
     "note": "Chair/Vice-Chair tags scraped weekly from the county's own "
             "directory (lake_county_board_roles_scraper.py). The edge 403s the "
             "requests stack and answers the stdlib one 200, so since 2026-09-03 "
             "the scraper reads the LIVE page on its stdlib rung instead of the "
             "Internet Archive copy it had been riding — the roles are current "
             "rather than as-archived, and no longer age out with the snapshot. "
             "Member names/contact stay live on the boundary GIS; the card "
             "applies a role only when this file's name matches the GIS."},
    {"layer": "Kendall County Board members (roster)",
     "app_file": "kendall-county-board-members.json",
     "source_url": "https://www.kendallcountyil.gov/county-board/board-members",
     "note": "AUTOMATED AGAIN 2026-09-03, after six weeks hand-verified. The "
             "county's Akamai edge refuses the requests stack and serves the "
             "stdlib one sending a real Chromium's Sec-CH-UA hints; it needs both, "
             "and kendall_county_board_scraper.py now carries that rung between "
             "requests and playwright. The first live scrape reproduced the "
             "hand-verified roster EXACTLY — 10 members, 10/10 districts and "
             "e-mails, the shipped file content-identical — which is the check "
             "that matters, since a rung that returns a page is not the same as "
             "one that returns the right data. Issue #234 can close."},
    {"layer": "McHenry County Board members (roster)",
     "app_file": "mchenry-county-board-members.json",
     "source_url": "https://www.mchenrycountyil.gov/departments/county-board/meet-your-county-board-members",
     "note": "AUTOMATED AGAIN 2026-09-03, after six weeks hand-verified — same "
             "Akamai posture and same stdlib+client-hints rung as Kendall. The "
             "first live scrape reproduced the hand-verified roster EXACTLY: 19 "
             "members including the countywide-elected Chairman, 19/19 e-mails, "
             "the shipped file content-identical. It also surfaced a defect the "
             "block had hidden — the builder read the profile link as `url` while "
             "the scraper emits `source_url`, so the first automated run would "
             "have shipped 19 members with no Profile link. check_roster_retention "
             "caught it; the builder now reads either. Issue #235 can close."},
    {"layer": "Illinois county clerks (roster)",
     "app_file": "il-county-clerks.json",
     "source_url": "https://www.elections.il.gov/ElectionOperations/ElectionAuthorities.aspx",
     "note": "Scraped weekly from ISBE's election-authority directory "
             "(il_county_clerk_scraper.py); Peoria deliberately absent (its "
             "authority is the appointed county election commission)."},
    {"layer": "Suburban municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.cookcountyclerkil.gov/elections/directory-elected-officials",
     "note": "Scraped weekly from the Cook County Clerk's Directory of Elected "
             "Officials JSON API (cook_municipal_officials_scraper.py), keyed by "
             "Census place GEOID. The site is Cloudflare-fronted, so a "
             "reachability WARN here can be a bot filter rather than drift — "
             "confirm with a browser User-Agent before treating it as a source "
             "change. Cook is one of twelve counties shipped in this file, each "
             "with its own entry below (see docs/EXPANSION_GUIDE.md Part 3 "
             "rule 5). Six jurisdiction types "
             "are read: MUNIS (municipalities + citywide officers), MUNIW "
             "(suburban ward/district seats), CHIWD (Chicago citywide), "
             "CHICA (Chicago's 50 ward seats, the only verified source of their "
             "term data — the City's own roster htai-wnw4 publishes none) and "
             "TWNSP, whose Cicero jurisdiction is the Town of Cicero — the "
             "Clerk files it as 'Cicero Township' because town and township "
             "are one coterminous government — MUNIS carries no Town at all, "
             "which is how Cook's sixth-largest municipality shipped nothing "
             "until 2026-08-19. The same TWNSP read carries the Cicero Public "
             "Library's elected trustees (cook-library-trustees.json) and, "
             "since 2026-08-19, every other Cook township's governing "
             "officials (township-officials.json, its own entry below). "
             "The county's Socrata copies of this directory (vw2r-zys4, "
             "jsup-zs8y) are frozen at 2014 and deliberately unused."},
    {"layer": "Cook township governing bodies (roster)",
     "app_file": "township-officials.json",
     "source_url": "https://www.cookcountyclerkil.gov/elections/directory-elected-officials",
     "note": "The same Cook Clerk directory API, TWNSP jurisdiction type: 29 "
             "township governments (supervisor, four trustees, clerk/assessor/"
             "collector/highway commissioner, hall contact) keyed by Census "
             "county-subdivision GEOID — cook_municipal_officials_scraper.py "
             "fetches, build_township_officials.py selects and guards. Party "
             "committeeperson records are excluded (party posts, and the "
             "feed's one personal-e-mail surface); per-person contact never "
             "ships because the hall mailbox is shared township-wide. "
             "Evanston Township dissolved into its city in 2014 and is "
             "skipped by name. Same Cloudflare front as the row above — a "
             "reachability WARN can be a bot filter rather than drift."},
    {"layer": "Will County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.willcountyclerk.gov/local-election-officials/",
     "note": "The Clerk page that LINKS the Will County Directory flipbook — "
             "pinned here rather than the flipbook itself because the book id "
             "changes with each edition and will_municipal_officials_scraper.py "
             "discovers it from this page. The page serves 202/empty to "
             "non-browser user agents, so a reachability WARN can be its bot "
             "filter rather than drift."},
    {"layer": "Will ward-city council contact (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.wilmington-il.com/city-officials",
     "note": "The bounded per-city exception to the source ladder "
             "(will_city_councils_scraper.py): the Will County Clerk's directory "
             "publishes no per-SEAT council contact, and omits Lockport and "
             "Wilmington entirely — their entry headers are missing from the "
             "flipbook's text layer, so no parser can recover them. The three "
             "cities' own sites supply per-seat phone/e-mail plus those two "
             "rosters. Pinned to Wilmington's page as the representative one; "
             "Crest Hill (cityofcresthill.com staff directory) and Lockport "
             "(cityoflockport.net/153) are the others. Joliet is deliberately "
             "unbuilt: joliet.gov 403s non-browser clients, jolietcity.org is "
             "client-rendered, and the only Archive snapshot is from 2022. The "
             "county clerk remains the roster of record — for a municipality the "
             "county covers, this source contributes contact only."},
    {"layer": "Joliet council contact (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.joliet.gov/government/city-council-3189",
     "blocked": "Akamai hard WAF deny, not a solvable challenge — permanent by measurement",
     "note": "Per-seat phone + e-mail for the metro's third-largest city, which "
             "the Will Clerk's directory does not publish "
             "(joliet_council_contact_scraper.py). TERMINAL BLOCK (re-measured "
             "2026-07-28, correcting an earlier read): joliet.gov is Akamai "
             "serving a HARD WAF DENY — a 408-byte static page with an "
             "x-reference-error, not a solvable challenge — so the Playwright "
             "rung fails exactly as requests does and no rung carries this city. "
             "A reachability WARN here is EXPECTED and permanent. The Internet "
             "Archive was re-evaluated and declined on its merits, not its age: "
             "the captures are good (the archived index still yields all nine "
             "bio links, the bio pages still carry their e-mails) but the newest "
             "index capture is 69 days old against the fleet's 45-day guard, so "
             "a conventional rung would refuse every run — and preservation "
             "already carries Joliet's last-good entry from a live scrape, which "
             "beats a dated copy. The Clerk stays the roster of record; this "
             "adds contact only. Note jolietcity.org is NOT the city — it is a "
             "parked domain."},
    {"layer": "Skokie trustee districts (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.skokie.org/486/Board-of-Trustees",
     "note": "Skokie is the one municipality whose ward geometry the app maps "
             "while its county publishes no district for any seat: Cook GIS "
             "carries four Skokie district polygons, the Clerk's directory "
             "lists all six trustees as municipality-wide "
             "(skokie_trustee_districts_scraper.py). The village's own board "
             "page carries the assignment — four district trustees + two "
             "at-large since the April 2025 consolidated election, per its "
             "2025 Electoral Changes page — plus a per-trustee e-mail. The "
             "Clerk stays the roster of record; this fills the district and "
             "e-mail only. If Skokie's board structure changes, the scraper "
             "fails loudly rather than reshaping the card."},
    {"layer": "DuPage municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://dmmc-cog.org/membership-list/",
     "note": "DuPage County government publishes NO municipal-officials "
             "directory (verified negative), so the DuPage Mayors and Managers "
             "Conference directory is the source of record "
             "(dupage_municipal_officials_scraper.py). Pinned to the membership "
             "page, not the PDF: the PDF's URL carries its edition date and "
             "changes, and the scraper discovers it here. Head of government "
             "only — the directory prints no trustees."},
    {"layer": "Kane County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://clerk.kanecountyil.gov/Elections/Documents/GovernmentGuide.pdf",
     "note": "The Clerk's annual Government Guide, 'Cities and Village "
             "Officials' section (kane_municipal_officials_scraper.py). Stable "
             "URL, linked from clerk.kanecountyil.gov/elections. Head of "
             "government + municipal clerk only — the guide prints no trustees."},
    {"layer": "McHenry County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.mchenrycountyil.gov/county-government/county-yearbook/cities-villages",
     "blocked": "Akamai fingerprints the HTTP client, so Playwright is the day-one rung",
     "note": "The Clerk's County Yearbook 'Cities & Villages' page "
             "(mchenry_municipal_officials_scraper.py). Akamai-fronted and it "
             "fingerprints the HTTP CLIENT, not just headers: measured 2026-07, "
             "curl gets 200 where python-requests gets 403 with a byte-identical "
             "browser header set, so Playwright is the day-one rung and a "
             "reachability WARN here is EXPECTED, not drift. Head of government "
             "+ elected clerk/treasurer only; appointed administrators are "
             "excluded deliberately."},
    {"layer": "Kendall County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.kendallcountyil.gov/home/showdocument?id=184",
     "blocked": "same Akamai client-fingerprint posture as McHenry",
     "note": "The Clerk's Yearbook & Government Guide PDF, CITY/VILLAGE "
             "OFFICIALS sections (kendall_municipal_officials_scraper.py). Same "
             "Akamai client-fingerprint posture as McHenry — a reachability WARN "
             "is EXPECTED. The yearbook misspells Minooka as 'Minnoka'; the "
             "scraper carries an explicit alias so the place still joins."},
    {"layer": "Lake County municipal hall contact (roster)",
     "app_file": "municipal-officials.json",
     "source_url": ("https://services3.arcgis.com/HESxeTbDliKKvec2/arcgis/rest/"
                    "services/Municipalities/FeatureServer/0"),
     "note": "Lake publishes NO municipal officeholder names anywhere "
             "county-side (double-verified negative: county/Clerk pages, GIS, "
             "and the Municipal League). This service supplies hall address, "
             "phone, e-mail, and website only, so Lake ships contact-only cards "
             "— the rule-4 honesty floor (lake_municipal_officials_scraper.py). "
             "If a Lake roster ever appears, this is the entry to upgrade."},
    {"layer": "Lee County Board roster",
     "app_file": "lee-county-board-members.json",
     "source_url": "https://www.leecountyil.com/419/Member-Contact-List",
     "note": "The Clerk's Member Contact List — a PDF served at a page-looking URL, and "
             "the only place Lee publishes its membership (the County Board page names "
             "the Chair and Vice-Chair only). Read by WORD POSITION (pdfplumber): pypdf "
             "flattens it into a name block and a separately-ordered e-mail block, so a "
             "line-based read pairs members with the wrong addresses. The Board Chair is "
             "identified by his row carrying the shared leecochair@countyoflee.org "
             "address rather than a personal one."},
    {"layer": "Rock Island County Board roster",
     "app_file": "rock-island-county-board-members.json",
     "source_url": "https://www.rockislandcountyil.gov/263/County-Board",
     "note": "The county's board page — a CivicPlus staff-directory widget with "
             "h-card microformat classes (p-name, p-job-title), so this is a "
             "class parse rather than a text-shape guess. 19 single-member "
             "districts. The Chairman appears TWICE on the page (a prose block "
             "above the widget, and again as his district's member); he is "
             "deduped onto his district row and tagged there, because the county "
             "elects its chair from among the 19. The scraper refuses any "
             "single-member district that ends up holding two names."},
    {"layer": "LaSalle County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://lasallecountyil.gov/294/Officials",
     "note": "The Clerk's Municipality Officials PDF, linked from this page "
             "(lasalle_municipal_officials_scraper.py). Full governing body — "
             "every trustee and ward number — from one county document. Its "
             "directory is a six-column table whose columns interleave, so it "
             "is the one source in this file read from word POSITIONS "
             "(pdfplumber) rather than from extracted lines."},
    {"layer": "Winnebago County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://maps.wingis.org/public/rest/services/ElectedOfficials/MapServer",
     "note": "The only source in the fleet that publishes municipal governing "
             "bodies AS GIS LAYERS — one layer per municipality on WinGIS's "
             "ElectedOfficials service (winnebago_municipal_officials_scraper.py). "
             "A layer disappearing is the drift to watch for here, not a URL "
             "change. WinGIS publishes no mayor/president layer for Loves Park "
             "or Machesney Park, which is why the builder's Winnebago head "
             "floor sits below its municipality floor."},
    {"layer": "Ogle County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://www.oglecountyil.gov/departments/county_clerk/index.php",
     "note": "The Clerk's yearbook, 'OGLE COUNTY CITIES & VILLAGES' section "
             "(ogle_municipal_officials_scraper.py) — full governing body plus "
             "hall address, phone and website for all 13 municipalities. Pinned "
             "to the Clerk page rather than the PDF because the yearbook "
             "filename carries its edition ('2025- 2027 Yearbook.pdf'). Adeline "
             "is the one entry that labels a PHYSICAL and a MAILING address at "
             "different places; the scraper keeps them apart deliberately."},
    {"layer": "Boone County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": ("https://www.boonecountyil.gov/government/departments/"
                    "clerk___recorder/2019_boone_county_illinois_year_book.php"),
     "note": "The Clerk's yearbook, 'CITY/VILLAGE OFFICIALS' section "
             "(boone_municipal_officials_scraper.py) — full governing body for "
             "all 5 municipalities, including Belvidere's ten ward seats, which "
             "are cross-checked against the county's own Belvidere_Wards "
             "service before the payload is written. Pinned to the INDEX page, "
             "not the PDF: the edition is discovered from the link TEXT ('2026 "
             "Yearbook'), because the filenames are not a reliable edition key "
             "— the page's own slug still says 2019 while it serves the 2026 "
             "book. This yearbook prints a RESIDENCE under almost every "
             "official; the scraper refuses those lines by construction and "
             "proves it on the built payload, so no home address can reach "
             "data/app (the Madison/Peoria rule)."},
    {"layer": "Stephenson County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": ("https://stephensoncountyil.gov/government/"
                    "boards_commissions_committees/city_and_villages.php"),
     "note": "The county's Cities & Villages directory "
             "(stephenson_municipal_officials_scraper.py) — full governing body "
             "for 10 of the county's 11 municipalities, and the only source in "
             "this file that marks each office '(Elected)' or '(Appointed)' "
             "explicitly. FREEPORT IS NOT ON THIS PAGE: the county seat comes "
             "from the city's own site, below. The address column is board "
             "members' RESIDENCES and is deliberately not collected."},
    {"layer": "Freeport city council (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://cityoffreeport.org/wp-json/wp/v2/lsvr_person_cat?slug=elected-officials",
     "note": "Freeport is the one Stephenson municipality its county page omits "
             "— and it is the county seat, holding more than half the county's "
             "municipal population (freeport_council_scraper.py). Membership is "
             "a WordPress REST query on the city's own 'elected-officials' "
             "category, and each person page carries a schema.org Person block. "
             "The city ALSO publishes a Wards2022_Public FeatureServer with an "
             "Alderperson field: it is stale (data last edited 2024-05-21, "
             "still naming a pre-2025-election holder) and must not be used for "
             "officeholders — only its geometry would be sound."},
    {"layer": "Carroll County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": ("https://www.carrollcountyil.gov/county_departments/"
                    "clerk___recorder/index.php"),
     "note": "The Clerk's yearbook, 'Cities and Village Officers' section "
             "(carroll_municipal_officials_scraper.py) — head of government + "
             "clerk for all seven municipalities; the county prints no "
             "trustees. Pinned to the Clerk page because the yearbook filename "
             "carries its edition and the scraper discovers it here; note the "
             "link is RELATIVE and only resolves against the Revize CDN root, "
             "which the scraper tries first."},
    {"layer": "DeKalb County Board members (roster)",
     "app_file": "dekalb-county-board-members.json",
     "source_url": "https://dekalbcounty.org/government/county-board/county-board-members/",
     "note": "The county's own members page (dekalb_county_board_scraper.py) — "
             "party, term, 22 phones and 24 e-mails, none of which its boundary "
             "GIS actually populates. Not flagged 'blocked': the block is REAL "
             "but conditional, so both states are informative. The host serves "
             "SiteGround's SG-Captcha stub (HTTP 202 + a /.well-known/sgcaptcha/ "
             "refresh) whose own query string reads y=ipr:<caller ip> — it "
             "scores the ADDRESS, not the request. Measured 2026-08-02: ~1 in 2 "
             "from a well-reputed egress, 6 of 6 from a GitHub Actions runner "
             "(which is what failed the first scheduled run, 2026-07-31). More "
             "retries cannot fix an address, so the scraper walks "
             "requests -> playwright -> wayback and its run log names the rung "
             "that carried it. There is no single CI verdict either: across "
             "four runs of one commit, three runner addresses were refused on "
             "every rung (one held 24s on the interstitial under a real "
             "Chromium) and a fourth was carried by plain requests on its first "
             "try, so the weekly workflow treats a failure as address luck — "
             "continue-on-error onto a standing issue rather than a red job. A "
             "WARN here means only 'this checker drew the stub' and never that "
             "the page changed."},
    {"layer": "DeKalb County municipal governing bodies (roster)",
     "app_file": "municipal-officials.json",
     "source_url": "https://dekalbcounty.org/about/reference-yearbook/",
     "note": "The Clerk's Reference Yearbook, 'Municipalities of DeKalb County' "
             "section (dekalb_municipal_officials_scraper.py) — full governing "
             "body plus hall address, phone and website for all 14 "
             "municipalities, and the only source in this file that dates every "
             "seat's NEXT ELECTION. Pinned to the COUNTY's reference page, not "
             "the clerk's domain: the PDF lives at "
             "dekalbcountyclerkil.gov/wp-content/uploads/<year>/<month>/ under a "
             "path that restamps annually, and the scraper discovers it from "
             "this page. Both section headings are matched whole-line — the "
             "book's own index carries each of them followed by dot leaders. "
             "REACHABILITY IS INTERMITTENT BY DESIGN and a WARN here is not "
             "necessarily drift: this host serves SiteGround's SG-Captcha stub "
             "(HTTP 202 + a /.well-known/sgcaptcha/ refresh) scored on the "
             "CALLER'S IP — measured 2026-08-02 it alternated roughly 1-in-2 "
             "from one address while taking every attempt from a GitHub Actions "
             "runner. Confirm against the PDF host before treating a WARN as a "
             "source change; dekalbcountyclerkil.gov is open and unaffected."},
    {"layer": "Board of Review commissioners (roster)",
     "app_file": "ccbr-roster.json",
     "source_url": "https://www.cookcountyboardofreview.com/",
     "note": "Scraped weekly from the Board's commissioner pages "
             "(ccbr_scraper.py); the menu-discovered pages move to new "
             "name-derived paths after elections, which the scraper follows."},
    {"layer": "U.S. House districts (IL)",
     "app_file": "congress-districts.json",
     "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0?f=json",
     "note": "TIGERweb Legislative layer 0 (STATE=17), pre-built by build_legislative_boundaries.py. Redrawn ~once a decade. Built against TIGERweb's 120th-Congress layer (field CD120, Jan 1 2026 vintage); the retired CD119 field is gone and a query naming it returns an HTTP-200 JSON error envelope with no features key, so a rebuild on the old name fails as no-features."},
    {"layer": "IL State Senate districts",
     "app_file": "il-senate-districts.json",
     "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1?f=json",
     "note": "TIGERweb Legislative layer 1 (2024 Upper, STATE=17), pre-built. Redrawn ~once a decade."},
    {"layer": "IL State House districts",
     "app_file": "il-house-districts.json",
     "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2?f=json",
     "note": "TIGERweb Legislative layer 2 (2024 Lower, STATE=17), pre-built. Redrawn ~once a decade."},
    {"layer": "White County Board members (roster)",
     "app_file": "white-county-board-members.json",
     "source_url": "https://www.whitecounty-il.gov/county-board",
     "note": "The county's own board page (white_county_board_scraper.py) — "
             "five members, party, Chair/Vice, and the board's one PO Box and "
             "one e-mail. The page names NO districts: the join lives in "
             "build_white_county_board.py's certified-canvass table, and any "
             "page name that table cannot place fails the weekly run on "
             "purpose."},
    {"layer": "White County boundaries + polling (Clerk's Elections page)",
     "app_file": "white-county-board-districts.json",
     "source_url": "https://www.whitecounty-il.gov/elections925f89e8",
     "note": "The Clerk's Elections page carries all three of this county's "
             "sources: the adopted 'White County, IL voting districts & "
             "precincts map.pdf' (archived in data/source/raw/; the traced "
             "composition behind white-county-board-districts.json and "
             "white-precincts.json, verified against Census 2020 VTDs by "
             "build_white_boundaries.py), the certified 2022/2024 canvass "
             "PDFs the composition and the member-district join were proven "
             "from, and the polling list behind white-precinct-polling.json. "
             "The weekly roster run separately fails if the map link leaves "
             "this page (the Mason watcher rule)."},
    {"layer": "Jo Daviess County Board members (roster)",
     "app_file": "jo-daviess-county-board-members.json",
     "source_url": "https://www.jodaviesscountyil.gov/1199/County-Board",
     "note": "The county's own board page (jodaviess_county_board_scraper.py) "
             "— 17 seats with party, term and district, enriched with each "
             "member's phone and e-mail from their directory page. On the "
             "county's CURRENT domain: the old jodaviess.org answers every "
             "URL with its home page, so a probe of it would read alive while "
             "being a dead link — never swap this URL to that domain."},
    {"layer": "Jo Daviess County Board districts (purchased, licence #008382)",
     "app_file": "jo-daviess-county-board-districts.json",
     "source_url": "https://www.jodaviesscountyil.gov/1226/GIS-IT",
     "note": "THE GEOMETRY'S SOURCE HAS NO URL TO PROBE: it is the county's "
             "own shapefile, SOLD under Jo Daviess County GIS Digital Data "
             "License Agreement #008382 and delivered by the GIS office's "
             "e-mail of 2026-08-17; display is authorized in writing by "
             "IT/GIS Director Joe Kratcha (same date, naming the site's then "
             "domain chidistricts.com) and CONFIRMED by him for districtry.com "
             "on 2026-08-31, and the raw file is retained OFFLINE because the "
             "licence forbids "
             "redistributing it (build_jodaviess_board_districts.py records "
             "the component hashes). What this entry probes instead is the "
             "county's GIS-IT page — the office the licence came from — so a "
             "domain move (the jodaviess.org trap, again) or a vanished GIS "
             "desk surfaces here. A REDISTRICTING will not: the weekly roster "
             "run is that tripwire, failing when the board page's district "
             "count leaves 17."},
    {"layer": "Coles County Board members (roster)",
     "app_file": "coles-county-board-members.json",
     "source_url": "https://www.colesco.illinois.gov/board/",
     # NOT A REFUSAL, and the flag is used for its MECHANICS rather than its
     # name — read the reason, not the key. This host serves an incomplete TLS
     # chain (leaf only, no intermediate), so every plain client fails
     # verification while the site itself answers HTTP 200 with a complete
     # page. That is permanent and measured, exactly the shape the inversion
     # exists for: unreachable-to-a-plain-probe is the expected steady state,
     # and REACHABLE is the news, because it means the county fixed its chain
     # and the scraper's AIA machinery could be retired. Without this flag the
     # monthly issue would reopen forever on a certificate error that is not a
     # source change — the no-op-WARN problem the flag was introduced to end.
     "blocked": "the county's server sends no intermediate certificate, so a "
                "plain client cannot build the chain — the page itself is "
                "healthy (HTTP 200) and the scraper supplies the intermediate "
                "by AIA with a pinned hash. Reachable here would mean the "
                "county FIXED its chain: re-test, then drop this flag",
     "note": "The county's own board page (coles_county_board_scraper.py) — "
             "12 single-member districts with an e-mail each, 9 phones, and "
             "the board office's own address and phone. THIS IS A SEPARATE "
             "SOURCE FROM THE BOUNDARY ON PURPOSE: the county's board-district "
             "GIS layer carries its own member column and it is a 2022-04-23 "
             "snapshot getting six of twelve names wrong, so geometry comes "
             "from the service and people come from here. NOTE FOR ANYONE "
             "PROBING THIS HOST: it serves an INCOMPLETE certificate chain "
             "(leaf only, no GoDaddy intermediate), so a plain requests/curl "
             "fetch fails verification while the site is perfectly healthy — "
             "that error is what got this county recorded as blocked for a "
             "year. The scraper supplies the intermediate by AIA with a "
             "pinned hash; this validator's own probe may still report the "
             "host unreachable for that reason, which is NOT a source change. "
             "The county's older www.co.coles.il.us is a genuine refusal and "
             "bare co.coles.il.us has no DNS record; neither is cited."},
    {"layer": "Clark County Board (boundaries AND roster — the Clerk's certified canvasses)",
     "app_file": "clark-county-board-members.json",
     "source_url": "https://il-clark.accessliberty.com/pastelections.aspx",
     "note": "ONE SOURCE FOR BOTH HALVES OF THIS COUNTY, which is unique in "
             "the fleet. Clark's Clerk stated in writing on 2026-08-18 that "
             "the board is elected by districts and that the county has no "
             "map to supply, and the county's only board document is a "
             "SCANNED IMAGE with no text layer. So the boundaries are the "
             "Census 2020 voting districts dissolved per the composition its "
             "certified canvasses state (2022 General for all seven, 2024 "
             "General for 3/4/7, 2026 General Primary for 1/2/5/6 — "
             "build_clark_boundaries.py), and the roster is the winners those "
             "same canvasses certify (clark_county_board_scraper.py). This "
             "page is the Clerk's own archive of one text-layer canvass PDF "
             "per election back to 2006; the live feed is the sibling host "
             "il-clark.pollresults.net, an AngularJS shell whose entire "
             "result set is embedded in the page as JSON. The county's own "
             "site is clarkcountyil.ORG — a TLD an earlier name-permutation "
             "probe never tried, which is why this county read as having no "
             "website for five days. The weekly roster run re-reads each "
             "district's tabulated precinct list against the shipped "
             "dissolve, so a re-precincting or redistricting fails there "
             "rather than shipping silently."},
    {"layer": "Crawford County Board (roster + the composition tripwire)",
     "app_file": "crawford-county-board-members.json",
     "source_url": "https://crawfordcounty.illinois.gov/department/county-board/",
     "note": "The county's own board page (crawford_county_board_scraper.py) — "
             "ten members, two per district, a county e-mail each and the "
             "Chairman titled. THE BOUNDARY HAS A SECOND SOURCE that this entry "
             "does not cover: the district composition comes from the Clerk's "
             "certified results at il-crawford.pollresults.net, and the same "
             "weekly run re-reads it and fails if it stops matching the shipped "
             "dissolve (build_crawford_boundaries.py). The county's own district "
             "layers exist — its Assessor maintains them — but their release is "
             "with the county's Mapping Committee, so nothing here reads them."},
    {"layer": "Mercer County Board (roster + the composition tripwire)",
     "app_file": "mercer-county-board-members.json",
     "source_url": "https://www.mercercountyil.org/county_board/index.php",
     "note": "The county's own board table (mercer_county_board_scraper.py) — "
             "ten members, two per district, party and term-expiry on every row, "
             "home town, and the Chairman badged with his phone. THE BOUNDARY "
             "HAS A SECOND SOURCE that this entry does not cover: the district "
             "composition comes from the Clerk's certified results at "
             "il-mercer.pollresults.net, and the same weekly run re-reads it and "
             "fails if it stops matching the shipped dissolve "
             "(build_mercer_boundaries.py). That matters more here than most — "
             "the only map the county has sent is a 2021 scan, so nothing else "
             "would ever show the districts moving. NOTE FOR ANYONE PROBING "
             "THIS COUNTY: il-mercer.accessliberty.com answers 200 and is EMPTY, "
             "carrying no past-election archive at all."},
    {"layer": "Edgar County Board (roster + the composition tripwire)",
     "app_file": "edgar-county-board-members.json",
     "source_url": "https://edgarcountyillinois.com/county-board/",
     "note": "The county's own board page (edgar_county_board_scraper.py) — "
             "name, district and party for all seven, and nothing else. READ "
             "THE DOMAIN: this is edgarcountyillinois.COM. The county also runs "
             "edgarcountyillinois.GOV, which links ACROSS to this page and does "
             "not carry the board itself, so probing the .gov would report a "
             "county with no roster. THE BOUNDARY HAS A SECOND SOURCE that this "
             "entry does not cover: the composition was proven from three "
             "certified canvasses at il-edgar.accessliberty.com (2022 General, "
             "all seven districts; 2024 General, 1/6/7; 2026 General Primary, "
             "2/3/4/5/6), and the weekly run re-reads it from the live feed and "
             "fails if it stops matching the shipped dissolve "
             "(build_edgar_boundaries.py). NOTE ON THAT ARCHIVE: its download "
             "handler is keyed pageid=59&mid=189, NOT the 58/188 Clark uses — "
             "guessing Clark's parameters returns the vendor's LOGIN PAGE "
             "rendered as a PDF, which is a 200 with a plausible size and no "
             "canvass in it."},
    {"layer": "Early-voting sites (Chicago Board of Elections)",
     "app_file": "early-voting-sites.json",
     "source_url": "https://chicagoelections.gov/voting/early-voting",
     "blocked": "RE-MEASURED 2026-09-03: the site answers the stdlib stack 200 (62 KB) and this validator 403 — so the reachability half has lifted, and the second opinion in http_get now sees it. The flag STAYS because the reason the file is hand-made was never only reachability: the transcription carries the election name onto the card, and nothing parses the page yet. Retire it when a scraper ships (WATCH.md puts the next refresh at ~October, for the 3 Nov general)",
     "note": "Hand-transcribed per election (see WATCH.md row). The site 403s "
             "non-browser clients, so a reachability WARN here is expected, "
             "not drift — refresh the file when the Board posts the next "
             "election's list."},
]

# Live named services the app queries at runtime. These aren't year-versioned
# (they're views/endpoints kept current by the publisher), so the only useful
# check is reachability — a rename or retirement shows up here before users hit
# a broken card. WARN-only: the app already isolates a down source per-card.
ENDPOINTS = [
    # Suburban municipal ward boundaries — the non-Chicago entries of the
    # consolidated `ward` layer. No consolidated source exists, hence four.
    {"layer": "Suburban Cook municipal wards (21 municipalities, ward layer)",
     "url": "https://gis.cookcountyil.gov/traditional/rest/services/politicalBoundary/MapServer/22?f=json"},
    {"layer": "Evanston wards (ward layer; carries per-ward alderperson contact)",
     "url": "https://maps.cityofevanston.org/arcgis/rest/services/OpenData/ArcGISOpenData2Administrative/MapServer/0?f=json"},
    {"layer": "Will County municipal wards (Lockport/Wilmington/Crest Hill/Joliet, ward layer)",
     "url": "https://services.arcgis.com/fGsbyIOAuxHnF97m/arcgis/rest/services/Ward_Districts/FeatureServer?f=json"},
    {"layer": "Aurora wards (ward layer)",
     "url": "https://gis.aurora.il.us/arcgis/rest/services/Administrative_Boundaries/2022Wards/FeatureServer/0?f=json"},
    {"layer": "CPD Police District boundaries",
     "url": "https://services2.arcgis.com/t3tlzCPfmaQzSWAk/arcgis/rest/services/Police_District_Boundary_View/FeatureServer/0?f=json"},
    {"layer": "CPD Police District stations",
     "url": "https://services2.arcgis.com/t3tlzCPfmaQzSWAk/arcgis/rest/services/Police_District_Stations_View/FeatureServer/0?f=json"},
    {"layer": "CPD Police Beat boundaries",
     "url": "https://services2.arcgis.com/t3tlzCPfmaQzSWAk/arcgis/rest/services/Police_Beat_Boundary/FeatureServer/0?f=json"},
    {"layer": "CPS school sites",
     "url": "https://services2.arcgis.com/t3tlzCPfmaQzSWAk/arcgis/rest/services/Schools/FeatureServer/0?f=json"},
    {"layer": "USGS National Map structures — post offices (layer 38)",
     "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38?f=json"},
    {"layer": "USGS National Map structures — fire stations (layer 51; replaced CFD 28km-gtjn)",
     "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51?f=json"},
    {"layer": "USGS National Map structures — police stations (layer 53; replaced the CPD station list for the nearest-3 layer)",
     "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53?f=json"},
    {"layer": "Census TIGERweb counties (statewide county layer)",
     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer?f=json"},
    {"layer": "Census TIGERweb county subdivisions + places (township/municipality layers)",
     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer?f=json"},
    {"layer": "Census TIGERweb school districts (unified/secondary/elementary layers)",
     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer?f=json"},
    {"layer": "Census TIGERweb ZCTAs (statewide ZIP Code layer)",
     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer?f=json"},
    {"layer": "Census TIGERweb areal hydrography (Lake Michigan marker test)",
     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Hydro/MapServer?f=json"},
    {"layer": "Will County Board districts 2022 (current 11-district map + reps)",
     "url": "https://services.arcgis.com/fGsbyIOAuxHnF97m/arcgis/rest/services/County_Board_Districts_2022/FeatureServer/0?f=json"},
    {"layer": "Lake County Board districts (19 members + contact carried on the county GIS)",
     "url": "https://services3.arcgis.com/HESxeTbDliKKvec2/arcgis/rest/services/LakeCounty_PoliticalBoundaries/FeatureServer/0?f=json"},
    {"layer": "Kane County Board districts (24 members carried on the county GIS)",
     "url": "https://services1.arcgis.com/oRKmdBXD6EbdmVgJ/arcgis/rest/services/KaneCo_IL_County_Board/FeatureServer/1?f=json"},
    {"layer": "McHenry County Board districts (9, district-number-only on the county GIS)",
     "url": "https://services1.arcgis.com/6iYC5AXXYapRVNzl/arcgis/rest/services/McHenry_County_Board_Districts/FeatureServer/0?f=json"},
    {"layer": "Kendall County Board districts (2, the current line — the county's ArcGIS Enterprise)",
     "url": "https://maps.co.kendall.il.us/server/rest/services/Hosted/County_Board_2010/FeatureServer/0?f=json"},
    {"layer": "Suburban Cook voting precincts (1,430 — the Clerk's current fabric, precinctHistorical L0; "
              "same geometry as Socrata k7sw-w3b8 'Suburban Cook Election Precincts - Current')",
     "url": "https://gis.cookcountyil.gov/traditional/rest/services/precinctHistorical/MapServer/0?f=json"},
    {"layer": "Cook TIF districts (418 — the Clerk's un-yeared current tiling, clerkTaxDistricts L18; "
              "retired year editions archive in Tax_Increment_Finance_District_Boundaries)",
     "url": "https://gis.cookcountyil.gov/traditional/rest/services/clerkTaxDistricts/MapServer/18?f=json"},
    {"layer": "MWRD of Greater Chicago boundary (1 district — the Clerk's tax-agency polygon)",
     "url": "https://gis.cookcountyil.gov/traditional/rest/services/politicalBoundary/MapServer/21?f=json"},
    # DeKalb's five entries all come off ONE ArcGIS Online org, so a single
    # org-level outage would fail all five at once — which is exactly the signal
    # wanted. Layer ids are NOT 0-based on this org (Precincts is 1, the
    # property-tax services are 4/7/9); a wrong id returns an error envelope that
    # parses as an empty result, so each is pinned explicitly here too.
    {"layer": "DeKalb County Board districts (12 electing 2 members each; officeholders come from the weekly roster)",
     "url": "https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/District_AreaEffective2022/FeatureServer/0?f=json"},
    {"layer": "DeKalb voting precincts (69, named by the county's own township codes)",
     "url": "https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/Precincts/FeatureServer/1?f=json"},
    {"layer": "DeKalb fire protection districts (18, the Clerk's property-tax tiling)",
     "url": "https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/PT_Fire_Districts/FeatureServer/4?f=json"},
    {"layer": "DeKalb library districts (13, the Clerk's property-tax tiling)",
     "url": "https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/PT_Library_Districts/FeatureServer/7?f=json"},
    {"layer": "DeKalb park districts (6, the Clerk's property-tax tiling)",
     "url": "https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/PT_Park_Districts/FeatureServer/9?f=json"},
    # Ogle has no live endpoint of its own — both halves of its card are derived
    # files (see PROVENANCE). This is the census layer its district geometry is
    # dissolved from, so an outage or a schema change there is what would break a
    # rebuild.
    {"layer": "Census TIGERweb 2020 voting districts (Ogle board-district dissolve)",
     "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/58?f=json"},
    # Lee's REST root is /leecogis — NOT /server or /arcgis, which is what an
    # earlier pass tried before recording the county as unreachable. It was found
    # the way LaSalle's, Winnebago's, Madison's and DeKalb's were: the portal's
    # FEATURED GROUP (a plain search returns zero items) holds a "Voting Districts
    # & Election Precincts" app whose web map names the root. The county DRAWS its
    # four board districts, so the recorded precinct-dissolve blocker was moot.
    {"layer": "Lee County Board districts (4, county GIS)",
     "url": "https://gis.leecountyil.gov/leecogis/rest/services/Election/County_Board_Districts/MapServer/3?f=json"},
    {"layer": "Lee County precincts (46) + fire districts (22)",
     "url": "https://gis.leecountyil.gov/leecogis/rest/services/Election/Election_Precincts/MapServer/1?f=json"},
    # Whiteside runs the Esri Elections solution. Its Electoral Districts layer
    # holds EVERY office in one table keyed by electedoffice; only the three
    # County Board rows are consumed, filtered in the loader so the overlay draws
    # three shapes rather than twenty-one.
    #
    # DO NOT USE the same org's MyElectedRepresentatives service for
    # officeholders: it carries the same board with DIFFERENT names, its
    # dataLastEditDate is 2019-01-08, and only 11 of its 27 names appear on the
    # county's current board page — where this layer matches 27/27. Two services,
    # seven years apart, no naming cue; the edit date is the only tell.
    # Rock Island — the first served county on the Mississippi. The board and
    # precinct layers sit on one hosted service, reached the usual way (county
    # site -> parcel viewer -> web map -> operationalLayers). The board layer
    # declares a NAME column and populates it on 0 of 19 districts, which is
    # why a roster scrape exists. The county's TaxDistricts tilings (fire,
    # library, park) are NOT probed here: they were retired from live fetch for
    # pre-built files — see their PROVENANCE entries above.
    # Moline (7 wards) and Silvis (4) publish their own layers on the county's
    # hosted org, both edited in 2022 — after the redraw. Whiteside's ward layer
    # covers six MORE municipalities and is deliberately unused: last edited
    # 2019-11-05, before the 2020 census (recorded as a gap).
    {"layer": "Moline + Silvis municipal wards",
     "url": ("https://services9.arcgis.com/6FnscPPlUa9DXXOk/arcgis/rest/services/"
             "MolineWards2020/FeatureServer?f=json")},
    {"layer": "Rock Island County Board districts (19) + precincts (120)",
     "url": ("https://services9.arcgis.com/6FnscPPlUa9DXXOk/arcgis/rest/services/"
             "Other_Layers/FeatureServer?f=json")},
    {"layer": "Whiteside County electoral districts + precincts + polling places",
     "url": ("https://services.arcgis.com/l0M0OC6J9QAHCiGx/arcgis/rest/services/"
             "ElectionGeography_public/FeatureServer?f=json")},
    # DeKalb's four ward-electing municipalities are four separate services on
    # the county's org (DeKalb_Wards, Sycamore_Wards, Genoa_Wards,
    # Sandwich_Wards), all edited 2023-11. DeKalb_Wards is pinned as the
    # representative one — they are published and retired together.
    {"layer": "DeKalb + Sycamore + Genoa + Sandwich municipal wards",
     "url": ("https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/"
             "DeKalb_Wards/FeatureServer?f=json")},
    # Mendota's own org. The only ward geometry any of LaSalle County's four
    # ward-electing cities publishes; La Salle, Peru and Earlville are a
    # recorded gap, and the county's GIS carries corporate boundaries only.
    {"layer": "Mendota municipal wards",
     "url": ("https://services6.arcgis.com/z8UuifZkerkF2dpG/arcgis/rest/services/"
             "Mendota_Wards/FeatureServer?f=json")},
    # Effingham (the first island, 2026-08-04). Board + precincts + polling ride
    # the org's CentralSquare election service — the board's roster lives ON the
    # district features (name/party/phone/e-mail per seat), so this endpoint is
    # also the county's officeholder source; fire comes from the org's Districts
    # service and park/library from TaxDistricts_public.
    {"layer": "Effingham County electoral districts + precincts + polling (board roster on-feature)",
     "url": ("https://services.arcgis.com/vj0V9Lal6oiz0YXp/arcgis/rest/services/"
             "ElectionGeography_public_2d9b4955467947e2802e5d4c4173060f/FeatureServer?f=json")},
    {"layer": "Effingham County fire districts (Districts service) + park/library (TaxDistricts_public)",
     "url": ("https://services.arcgis.com/vj0V9Lal6oiz0YXp/arcgis/rest/services/"
             "Districts/FeatureServer?f=json")},
    # Hamilton (the second island, 2026-08-05). The county's tilings sit on a
    # vendor-hosted AGO org (Magnasoft) the Clerk pointed to in her reply; the
    # at-large board roster is the weekly commissioners scrape, not this.
    {"layer": "Hamilton County voter precincts (17, one unnamed — the county's own layer)",
     "url": ("https://services.arcgis.com/4YineAQdtmx0tv46/arcgis/rest/services/"
             "Voter_Precincts_Hamilton/FeatureServer?f=json")},
    {"layer": "Hamilton County fire districts (3 named + an excluded unnamed sliver)",
     "url": ("https://services.arcgis.com/4YineAQdtmx0tv46/arcgis/rest/services/"
             "Fire_Districts_HamiltonIL/FeatureServer?f=json")},
    # Coles (the 52nd dispatched county, 2026-08-17). Board districts and
    # precincts both live on the county's own PUBLIC ArcGIS Online org — the
    # one no name-permutation probe ever reached, while the county's website
    # was being recorded as blocked over what turned out to be an incomplete
    # TLS chain.
    #
    # UNLIKE EFFINGHAM'S ENTRY ABOVE, THIS ENDPOINT IS NOT AN OFFICEHOLDER
    # SOURCE, and the difference is the point: County_Board_District_View
    # carries Official/party/term/phone/e-mail columns that are a 2022-04-23
    # snapshot getting six of twelve names wrong. The app reads `District` and
    # nothing else here; the roster is the colesco.illinois.gov entry in
    # PROVENANCE. Probing this service therefore tells you the GEOMETRY is
    # alive and says nothing about the people.
    {"layer": "Coles County Board districts (12 — GEOMETRY ONLY, the layer's roster columns are stale)",
     "url": ("https://services2.arcgis.com/MgTN1xrZnaahv1AF/arcgis/rest/services/"
             "County_Board_District_View/FeatureServer?f=json")},
    # Layer 1 is the 44 precinct POLYGONS; layer 0 is 24 polling-place POINTS
    # whose comma-separated Precinct column expands to the same 44 names. Both
    # are needed — the card's polling row is the join between them.
    {"layer": "Coles County voter precincts (layer 1, 44) + polling places (layer 0, 24 points)",
     "url": ("https://services2.arcgis.com/MgTN1xrZnaahv1AF/arcgis/rest/services/"
             "2022_Voter_Precincts_WFL1/FeatureServer?f=json")},
]
# ==== TEMPLATE:END sources-manifest ====

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
            headers={"User-Agent": "DistrictExplorer-CHI source validator (+https://chidistricts.com)"},
        )
    except Exception as e:  # network/TLS/proxy errors are a finding, not a crash
        return False, "request failed: %s" % e
    if resp.status_code in (401, 403):
        # A REFUSAL BY THIS VALIDATOR IS NOT ALWAYS A REFUSAL BY THE SITE, and
        # two of this repo's own checks disagreeing about one host is worse than
        # either being wrong alone. validate_card_links has taken this second
        # opinion since 2026-08-29 (Sheboygan): several county edges fingerprint
        # urllib3's TLS ClientHello and serve the stdlib stack normally, and the
        # Akamai ones also want the Sec-CH-UA hints a real Chromium sends.
        #
        # Measured 2026-09-03: Kendall, McHenry, Adams, Lake and the Chicago
        # Board of Elections all answer that stack 200 while answering this one
        # 403. Without this, dropping their `blocked` flags — which is the whole
        # point of having re-measured them — would trade a monthly false BLOCK
        # for a monthly false UNREACHABLE.
        #
        # Once only, and only on a refusal. A 202 interstitial below is a
        # document about the block rather than a fingerprint of us, and a
        # managed challenge is a question the site is entitled to ask.
        try:
            from scraper_common import fetch_stdlib  # noqa: PLC0415 - optional path
            fetch_stdlib(url, timeout=HTTP_TIMEOUT)
            return True, "HTTP %d to this validator, 200 to a stdlib client " \
                         "(a client fingerprint, not a refusal)" % resp.status_code
        except Exception:  # noqa: BLE001 - a second opinion that fails is no opinion
            pass
        return False, "HTTP %d" % resp.status_code
    if resp.status_code >= 400:
        return False, "HTTP %d" % resp.status_code
    # 202 is never a real document. "Accepted" means the request was taken for
    # later processing, and the bot-management fronts in front of several county
    # sites use it for their interstitial — dekalbcounty.org started doing so
    # around 2026-07-31, which failed the DeKalb board scraper outright while
    # this validator went on reporting the source reachable, because 202 < 400.
    # (The Will County Clerk entry has documented the same "202/empty to
    # non-browser user agents" behaviour for longer.) Treat it as unreachable
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
            # The block LIFTING is the news. Every one of these entries was
            # measured unreachable and says so in its own note, so a monthly
            # WARN on them was pure noise — seven of the eight WARNs in the
            # 2026-08-01 run were this, and the tracking issue reopened every
            # month with nothing to act on. Reachable-again is the state a
            # human should hear about, because it means automation can resume.
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
        ok, res = http_get(e["url"], want_json=False)
        if ok:
            findings.add(OK, e["layer"], "endpoint reachable")
        else:
            findings.add(WARN, e["layer"],
                         "endpoint not reachable (%s): %s — the service may have been "
                         "renamed or retired" % (res, e["url"]))


# ==== TEMPLATE:BEGIN sources-ward-manifest ====
# The `ward` layer is the one CountyDispatch whose entries are keyed by SOURCE
# rather than by county, so its disjointness is not guaranteed by geography the
# way county-keyed layers' is. registerCountyLayer dispatches by containment and
# takes the FIRST entry that matches, so an overlap would not error — it would
# quietly answer from whichever entry happens to be ordered first, and the two
# sources disagree about ward numbering. Verified disjoint 2026-07-28 (206
# features, every ordered pair); this watches for a publisher extending one of
# them into another's territory, which is the realistic way it breaks.
WARD_SOURCES = [
    # Chicago is the pair that matters most: its 50 wards are ALSO in the Cook
    # county layer, and index.html drops them there by normalized name. If that
    # filter ever breaks, this is the check that says so.
    {"key": "chicago",
     "url": "https://data.cityofchicago.org/resource/p293-wvbd.geojson",
     "socrata": True},
    {"key": "cook-suburban",
     "url": "https://gis.cookcountyil.gov/traditional/rest/services/politicalBoundary/"
            "MapServer/22/query",
     # Chicago's 50 wards sit in this county layer too and the chicago entry
     # serves them from the City's own dataset; index.html filters them out by
     # normalized name, so the check must filter identically or report a
     # self-inflicted overlap.
     "drop_municipality": "CHICAGO"},
    {"key": "evanston",
     "url": "https://maps.cityofevanston.org/arcgis/rest/services/OpenData/"
            "ArcGISOpenData2Administrative/MapServer/0/query"},
    {"key": "aurora",
     "url": "https://gis.aurora.il.us/arcgis/rest/services/Administrative_Boundaries/"
            "2022Wards/FeatureServer/0/query"},
    {"key": "will",
     "url": "https://services.arcgis.com/fGsbyIOAuxHnF97m/arcgis/rest/services/"
            "Ward_Districts/FeatureServer/%d/query",
     "sublayers": [0, 1, 2, 3]},
    # The four entries added after this check was written. `urls` covers the
    # shape `sublayers` cannot: an entry whose municipalities are separate
    # SERVICES rather than sublayers of one.
    {"key": "rockford",
     "url": "https://maps.wingis.org/public/rest/services/ElectedOfficials/"
            "MapServer/20/query"},
    {"key": "rock-island",
     "urls": ["https://services9.arcgis.com/6FnscPPlUa9DXXOk/arcgis/rest/services/"
              "MolineWards2020/FeatureServer/0/query",
              "https://services9.arcgis.com/6FnscPPlUa9DXXOk/arcgis/rest/services/"
              "SilvisWards/FeatureServer/0/query"]},
    {"key": "dekalb",
     "urls": ["https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/"
              "%s_Wards/FeatureServer/0/query" % name
              for name in ("DeKalb", "Sycamore", "Genoa", "Sandwich")]},
    {"key": "mendota",
     "url": "https://services6.arcgis.com/z8UuifZkerkF2dpG/arcgis/rest/services/"
            "Mendota_Wards/FeatureServer/0/query"},
]
# ==== TEMPLATE:END sources-ward-manifest ====


def _ward_rings(feature):
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        return list(geom.get("coordinates") or [])
    if geom.get("type") == "MultiPolygon":
        return [r for poly in (geom.get("coordinates") or []) for r in poly]
    return []


def _ward_point_in(feature, pt):
    x, y = pt
    inside = False
    for ring in _ward_rings(feature):
        for i in range(len(ring) - 1):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[i + 1][0], ring[i + 1][1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def _ward_probe_point(feature):
    """Average of the largest ring — not guaranteed interior for a concave ward,
    but it only has to be a stable point that lands in the RIGHT municipality,
    and an overlap this misses is one the next feature catches."""
    rings = _ward_rings(feature)
    if not rings:
        return None
    ring = max(rings, key=len)
    return (sum(c[0] for c in ring) / len(ring), sum(c[1] for c in ring) / len(ring))


def check_ward_dispatch_disjoint(findings, offline):
    if offline:
        return
    layer = "City Ward (dispatch disjointness)"
    loaded = {}
    for src in WARD_SOURCES:
        feats = []
        urls = src.get("urls") or [src["url"] % sub if sub is not None else src["url"]
                                   for sub in src.get("sublayers", [None])]
        for url in urls:
            params = ({"$limit": "1000"} if src.get("socrata") else
                      {"where": "1=1", "outFields": "*", "outSR": "4326",
                       "f": "geojson", "resultRecordCount": "2000"})
            ok, res = http_get(url, params=params)
            if not ok:
                findings.add(WARN, layer,
                             "%s source unreachable (%s) — disjointness unverified this "
                             "run" % (src["key"], res))
                return
            feats.extend((res or {}).get("features") or [])
        drop = src.get("drop_municipality")
        if drop:
            feats = [f for f in feats
                     if (f.get("properties", {}).get("MUNICIPALITY") or "").strip().upper() != drop]
        loaded[src["key"]] = feats

    overlaps = []
    keys = sorted(loaded)
    for a in keys:
        for b in keys:
            if a == b:
                continue
            for f in loaded[a]:
                pt = _ward_probe_point(f)
                if pt and any(_ward_point_in(g, pt) for g in loaded[b]):
                    overlaps.append((a, b))
                    break
    if overlaps:
        findings.add(FAIL, layer,
                     "ward dispatch entries overlap (%s) — registerCountyLayer takes the "
                     "FIRST containing entry, so one source is silently answering for "
                     "territory the other also claims"
                     % ", ".join("%s into %s" % p for p in overlaps))
    else:
        findings.add(OK, layer,
                     "%d ward features across %d sources, every ordered pair disjoint"
                     % (sum(len(v) for v in loaded.values()), len(loaded)))


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
    check_ward_dispatch_disjoint(findings, args.offline)

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
