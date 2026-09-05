#!/usr/bin/env python3
"""
Build the pre-built parcel-fabric district files in data/app — every county
tiling whose upstream geometry is dissolved from a PARCEL fabric and therefore
draws the road network as voids. Supersedes build_rock_island_tax_districts.py
(Rock Island's three tilings moved into the source table here unchanged).

Why these files exist: a tax tiling dissolved from parcels excludes road
right-of-way, so served raw each district is a lattice of fragments separated
by 15-200 ft voids — the overlay draws the county's road grid as a dark mesh
and a click on any road inside a district lands in no polygon. The 2026-08-16
fleet survey measured the fabric signature across every fire/library/park
source; the SEVERE tier (hundreds of road-band voids: Kendall x3, Macon x3,
Sangamon fire, Cook fire, Rock Island x3) ships pre-built from this script,
while moderate sources keep live fetch + the 60 ft runtime snap.

The transform, per named district (identical to the Rock Island original):
  1. FETCH full-precision GeoJSON, make valid, DISSOLVE BY NAME (tax-code
     tilings publish many rows per district — Kendall's fire is 170 rows for
     10 FPDs).
  2. CLOSE with a 75 ft radius (morphological closing in a local ft frame,
     longitudes cos(lat)-scaled). Closing bridges only voids narrower than
     150 ft — road right-of-way, including the ~141 ft diagonal across an
     intersection — where the two sides face each other along enough
     frontage (erosion dissolves a bridge shorter than the closing diameter,
     so a lone outlying parcel across a road stays separate and the runtime
     snap covers its road strip). It mathematically cannot claim any point
     farther than 75 ft from ground the county published, nor fill a hole
     the size of an unserved municipality.
  3. KEEP CONTESTED GROUND OUT: final_i = raw_i UNION (closed_i minus every
     other district's closed shape). A road BETWEEN two districts is claimed
     by both closings, so it ships in neither — the seam stays visible and
     the runtime snap keeps refusing it as genuinely ambiguous. Raw
     county-published ground is never surrendered — including ground the
     county's own fabric puts in TWO districts (Cook's Clerk tiling double-
     claims Orland∩Mokena by 57 acres): that ships in both, exactly as the
     live layer answers today, and the disjointness pass strips only
     closing-added ground.
  4. SIMPLIFY (10 ft, topology-preserving), drop sub-2000-sq-ft slivers,
     enforce disjointness deterministically (later name cedes the
     simplify-wobble strip), round to 5 decimals.

Verification before writing (the build FAILS, it does not warn):
  - district count equals the pinned expectation, blank-named rows equal the
    pinned expectation (Rock Island's library carries exactly one — a stray
    byte-identical copy of the UNITED TWP HIGH 30 school polygon — excluded);
  - every district keeps >=99.5% of its raw area and claims nothing beyond a
    90 ft dilation of its raw self;
  - no two shipped districts overlap;
  - the road-void signature is GONE: at most a handful of sibling-part gaps
    in the 15-150 ft band survive per source (wider ones are genuine
    separations);
  - hand-measured probes hit: the dead-road points the survey proved
    (Kendall NEWARK FPD, Cook LEYDEN FPD, Rock Island's three) resolve, and
    unserved ground (Chicago Loop, Moline, Rock Island city, Andalusia)
    stays honestly empty — the closing must not manufacture coverage.

Freshness: sources that publish a dataLastEditDate are PINNED — a changed
stamp fails the build so a re-run is a conscious re-verification, not a
silent re-base. Kendall's hosted layers and Cook's MapServer publish no
stamp (Cook's Clerk refreshes tilings in place), so those pin the district
COUNT and name set instead, and validate_sources.py watches each service
monthly via the files' PROVENANCE entries.

Usage (rare operator step; network access to the county services required):
    pip install -c scripts/requirements.txt shapely requests
    python3 scripts/build_parcel_fabric_districts.py            # all sources
    python3 scripts/build_parcel_fabric_districts.py cook-fire  # one slug
"""

import json
import math
import os
import re
import sys

import requests
from shapely import make_valid
from shapely.geometry import mapping, shape, Point
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

CLOSE_FT = 75.0       # bridges voids < 150 ft; survey medians run 39-107 ft
SIMPLIFY_FT = 10.0
SLIVER_SQFT = 2000.0  # subtraction confetti — well under any annexed house lot
FEET_PER_DEG_LAT = 364000.0  # the app's own constant (index.html snap block)
MAX_RESIDUAL_VOIDS = 5       # sibling gaps left in the 15-150 ft band
PAGE_SIZE = 1000             # every county service here caps at 1,000 per query
MAX_FETCH_ROWS = 200000      # a runaway pager stops rather than looping forever

RI = ("https://services9.arcgis.com/6FnscPPlUa9DXXOk/arcgis/rest/services/"
      "TaxDistricts/FeatureServer/")
KENDALL = "https://maps.co.kendall.il.us/server/rest/services/Hosted/"
MACON = "https://services1.arcgis.com/a3k0qIja5SolIRYR/arcgis/rest/services/"
BOONE_PARCELS = ("https://maps.boonecountyil.org/arcgis/rest/services/"
                 "Boone_Sales_Locator/Devnet_Parcels/MapServer/0")

# Boone publishes NO park or library district layer — measured across its whole
# ArcGIS server (12 folders, 99 services) and its AGOL org. What it does publish
# is a parcel fabric carrying a tax_code, plus a County Clerk report saying which
# districts each code pays into, so a district is the union of its own parcels.
# Both halves are the county's own, which is what separates this from the
# broadband-contractor statewide layer recorded in the guidebook's backlog.
#
# THE CODE SETS COME FROM THE CLERK'S "Taxcode Value within District Report"
# (tax year 2025), NOT from her "District Rates by Taxcode Report". The rates
# report lists the codes carrying a RATE LINE for a district, which is a
# narrower thing: read as a membership list it omits twelve codes on 956
# parcels, and the first attempt at this build read that omission as the county
# contradicting itself and stopped.
#
# THE 90 UNCODED PARCELS ARE MEASURED, AND THE OBVIOUS EXPLANATION IS WRONG.
# This lived in the `boone-park-library-contact` gap record, which was retired
# on 2026-09-05 when its subject shipped; a measurement about the BUILD belongs
# with the build, not with a gap that closed. Ninety parcels carry no tax_code
# at all, so they never enter the where clause and are holes by construction:
# 23 of them, 104 acres, sit inside the Belvidere Park District's outline and
# outside its shipped polygon. The natural guess is that they ARE the parks —
# and the county's own layers refute it. Overlaid on every published
# park-property polygon (BCCD Property, Belvidere Parks, Poplar Grove Parks,
# Parks and Conservation Foundation Property) the 23 overlap by 0.0% of their
# area, one merely touching, while the county's 15 `Belvidere Parks` polygons
# (301 acres) fall 100% INSIDE the shipped district — a second, independent
# corroboration of the boundary. WHAT THE 23 ARE IS UNKNOWN AND IS NOT GUESSED
# AT: every one of the 90 carries a completely empty attribute row — no owner,
# no address, no class, no assessment — so the layer says nothing about them
# beyond their shape.
#
# THE MAPS BELOW ARE HAND-TRANSCRIBED FROM THOSE PDFs, so the documents are
# pinned here and the tax year is stated: re-verifying means re-reading these
# two, not searching the Clerk's page again. Both are linked from
# boonecountyil.gov's Clerk & Recorder "Tax Reports" page, which carries a
# folder per tax year back to 2013.
BOONE_TAX_YEAR = 2025
BOONE_REPORTS = {
    "roster": "https://www.boonecountyil.gov/Departments/Clerk-Recorder/"
              "Tax%20Reports/2025/Taxcode%20Value%20within%20district%20report.pdf",
    "corroborating": "https://www.boonecountyil.gov/Departments/Clerk-Recorder/"
                     "Tax%20Reports/2025/District%20Value%20with%20taxcode%20report.pdf",
    # the NARROWER report, kept named because reading it as a membership list is
    # what manufactured the twelve
    "rates": "https://www.boonecountyil.gov/Departments/Clerk-Recorder/"
             "Tax%20Reports/2025/District%20rates%20by%20taxcode%20report.pdf",
}
#
# TWO COUNTY DOCUMENTS, EACH USED FOR WHAT IT OWNS. The Clerk's "Taxcode Value
# within District Report" owns the LINES — which tax codes pay into which
# district — and abbreviates the names to fit its columns (`PDBV - BELVIDERE PK
# DIST`, `LYBV - IDA LIBRARY`). The Clerk's YEARBOOK, the same office's annual
# directory of officials and already scraped weekly by
# boone_municipal_officials_scraper.py, owns the NAMES: it gives each body a
# section heading, address, telephone and website. So the names below are the
# yearbook's headings verbatim, and nothing is expanded or invented. Checking
# the districts' own websites instead was tried and is the worse route — two of
# the five were unreachable from here, and cherryvalleylibrary.org turns out to
# be a library in Cherry Valley, NEW YORK, where the yearbook's own
# cherryvalleylib.org is the Illinois one.
#
# BOONE LEVIES FIVE OF THESE, NOT TWO. The first cut of this build shipped
# Belvidere and Ida alone, which would have told a resident of the county's
# western strip (Loves Park, in Rockford Park District and North Suburban
# District Library) or its south-west corner (Cherry Valley District Library)
# that they are in NO park or library district. They are in one; it is simply
# seated in Winnebago County and reaches across the line — the same shape as
# Stark's Kewanee and Williamsfield entries. Only the Boone slice is drawn, and
# the entries are coverage-gated to Boone, so no district is claimed anywhere
# this build cannot see it.
BELVIDERE_PARK = "BELVIDERE PARK DISTRICT"
ROCKFORD_PARK = "ROCKFORD PARK DISTRICT"
IDA_LIBRARY = "IDA PUBLIC LIBRARY"
CHERRY_VALLEY_LIBRARY = "CHERRY VALLEY DISTRICT LIBRARY"
NORTH_SUBURBAN_LIBRARY = "NORTH SUBURBAN DISTRICT LIBRARY"

BOONE_PARK_CODES = {"03007": ROCKFORD_PARK}
for _code in ("03008 05001 05002 05005 05007 05008 05009 05010 05011 05012 05110 "
              "05111 05901 05903 05904 06004 06005 06012 06111 07004 07014 07044 "
              "08002 08102 09700").split():
    BOONE_PARK_CODES[_code] = BELVIDERE_PARK

BOONE_LIBRARY_CODES = {}
for _code in ("05005 05012 05111 05901 05903 05904 06004 06005 06012 06111 07002 "
              "07004 07012 07014 07044 08002 08102 09700").split():
    BOONE_LIBRARY_CODES[_code] = IDA_LIBRARY
for _code in ("05009", "07005"):
    BOONE_LIBRARY_CODES[_code] = CHERRY_VALLEY_LIBRARY
for _code in ("03004", "03007", "03011", "05008"):
    BOONE_LIBRARY_CODES[_code] = NORTH_SUBURBAN_LIBRARY

# --- Woodford ------------------------------------------------------------
# One 25,824-parcel fabric, published three times over under three names. Every
# name it carries is `<CODE> - <District>`, the same form the County Clerk's
# certified settlement sheets use, so the code is the join between the two
# documents; it is kept on the shipped feature and the card leads with the name.
WOODFORD_PARCELS = ("https://services1.arcgis.com/iOG1OLysrxLAswZi/arcgis/rest/"
                    "services/%s/FeatureServer/%d")
WOODFORD_FIRE = WOODFORD_PARCELS % ("Fire_Protection_Districts", 2)
WOODFORD_LIBRARY = WOODFORD_PARCELS % ("Library_Districts", 8)
WOODFORD_PARK = WOODFORD_PARCELS % ("Park_Districts", 9)
WOODFORD_CODE_RE = r"^(?P<code>[A-Z]{2}[A-Z0-9]{2}) - (?P<name>.+)$"

# The second witness, PINNED. A DEVNET-generated Settlement Sheet for tax year
# 2025, in the county's own "County Taxes" archive and linked from its Real
# Estate Tax Information page. Re-verifying the district SET means re-reading
# these two, not searching the county's site again.
WOODFORD_TAX_YEAR = 2025
WOODFORD_SETTLEMENT_SHEETS = "https://www.woodford-county.org/Archive.aspx?ADID=3720"
WOODFORD_COUNTY_SUMMARY = "https://www.woodford-county.org/Archive.aspx?ADID=3719"

# WHAT THE THREE ITEMS SAY ABOUT THEMSELVES. All three are `access: public` in
# the county's own ArcGIS org, and the library and park items carry no licence
# text at all. The FIRE item carries two notes worth carrying forward rather
# than smoothing away: its licenseInfo reads "Does not match scale of Woodford
# Parcel Data", and its description opens "2007 Illinois Department of Revenue
# Taxing District Data for Woodford County".
#
# THAT 2007 DATE DESCRIBES THE ORIGINAL DISTRICT SHAPES, NOT WHAT IS DISSOLVED
# HERE, and the difference is measurable rather than argued. A parcel's district
# on this layer follows its TAX CODE: all 119 distinct `Tax_Code_1` values map
# to exactly one district per concept, on all three concepts, with no code split
# between two districts. So what is being dissolved is a tax-code crosswalk, and
# the tax codes are the ones the 2025 settlement sheets levy under — which is
# why the district set agrees with those sheets exactly. The geometry is the
# county's current parcel fabric throughout. The scale caveat is the county's
# own, and is why nothing here treats a district edge as survey-accurate.

# MINONK IS THE ONE MUNICIPAL LIBRARY IN THE SET and the card says so, because
# "Library District: Minonk City Library" would otherwise read as a district a
# resident lives inside. Measured, not inferred: all 1,230 of its parcels are
# in the City of Minonk and all 1,230 of the city's parcels are in it. The
# app's existing LIBRARY_GOVERNANCE wording for a city library ("levies no
# district tax of its own") is NOT reused, because the Clerk's own 2025
# settlement sheet shows LYMI levying $99,987.82 under a `016 - Library` fund —
# so the note states the territory, which is what was measured, and makes no
# claim about which body votes the levy.
# THE FIRST VERSION OF THIS NOTE SAID "its area is exactly the city" AND THAT
# WAS FALSE, because it was measured against the county's parcel ATTRIBUTE
# (`Village`) and never against the county's corporate-boundary LAYER. Both
# were consulted this time and THEY DISAGREE: the parcel table puts all 1,230
# LYMI parcels in `VCMI - City of Minonk` and all 1,230 city-tagged parcels in
# LYMI, while `Corporate_Boundary` excludes five of them — tax code 06002, a
# 16,059 m² tract whose nearest point is 5.2 km south of the city polygon,
# which is why the shipped LYMI feature is a two-part MultiPolygon. Two county
# products disagreeing IS the finding; the note states the territory and drops
# the word that was doing the overclaiming.
WOODFORD_LIBRARY_NOTES = {
    "LYMI - Minonk City Library":
        "Municipal library — its territory is the City of Minonk: the county's "
        "parcel table puts all 1,230 of the library's parcels in the city, "
        "though its corporate-boundary layer places five of them on a detached "
        "tract 5 km to the south.",
}

# ONE POSITIVE PROBE PER FIRE DISTRICT, plus the Metamora negative. Each point
# is a representative point of a real parcel and its EXPECTED answer is that
# parcel's own attribute value, read from the county's table before this build
# ran — so a probe tests the dissolve-and-close pipeline against the county's
# own row rather than against another product of the same pipeline.
WOODFORD_FIRE_PROBES = [
    (40.61778, -89.31191, "Deer Creek Fire District"),
    (40.74938, -89.49057, "Germantown Fire District"),
    (40.92399, -88.93623, "Dana Fire District"),
    (40.87464, -89.38365, "Washburn Fire District"),
    (40.75507, -88.93417, "Gridley Fire Protection District"),
    (40.76133, -89.03991, "El Paso Fire District"),
    (40.75880, -89.41516, "Central Fire District"),
    (40.61237, -89.25837, "Eureka-Goodfield Fire District"),
    (40.90300, -89.44234, "Spring Bay Fire District"),
    (40.75269, -89.20083, "Roanoke Fire District"),
    (40.77375, -89.41533, "Metamora Rural Fire District"),
    (40.90942, -89.07173, "Minonk Fire District"),
    (40.60559, -89.14376, "Carlock Fire District"),
    (40.69675, -89.08596, "Secor Fire District"),
    (40.63796, -89.05176, "Hudson Fire District"),
    (40.59862, -89.23620, "Congerville Fire District"),
    (40.83437, -89.13839, "Benson Fire District"),
    # inside the Village of Metamora, which runs its own department — the whole
    # of the county's 1,701-parcel fire hole. The SAME point is a positive on
    # the park layer below, so a build that quietly closed this hole over would
    # fail here while still passing there.
    (40.78554, -89.36257, None),
]
WOODFORD_LIBRARY_PROBES = [
    (40.61778, -89.31191, "Deer Creek Library District"),
    (40.69675, -89.08596, "El Paso District Library"),
    (40.76112, -89.28529, "IL Prairie Library District"),
    (40.90850, -89.04460, "Minonk City Library"),
    (40.60559, -89.14376, "Carlock Library District"),
    (40.69351, -89.30522, "Eureka Library District"),
    (40.92399, -88.93623, None),   # Dana — no library district
    (40.61237, -89.25837, None),   # rural Eureka-Goodfield
    (40.59862, -89.23620, None),   # Congerville village
    (40.83437, -89.13839, None),   # Benson village
]
WOODFORD_PARK_PROBES = [
    (40.84710, -89.31738, "Grant Memorial Park District"),
    (40.79629, -89.19274, "Roanoke Park District"),
    (40.78554, -89.36257, "Metamora Park District"),  # fire-negative, park-positive
    (40.61778, -89.31191, None),   # Deer Creek — no park district
    (40.90942, -89.07173, None),   # Minonk — no park district
]


# --- Whiteside ------------------------------------------------------------
# The Boone shape, and the county that shows why the shape is worth looking for
# twice. Its record read "no taxing district boundaries of any kind" for five
# weeks and that was true and beside the point: Whiteside publishes both halves
# of a dissolve and neither is a district layer.
#
# THE FABRIC. `Tax Parcels - Whiteside County` in the county's own ArcGIS
# Online org (`whiteside.maps.arcgis.com`, org l0M0OC6J9QAHCiGx, item public,
# licenseInfo EMPTY, accessInformation "Whiteside County IL GIS"), linked as
# "GIS Maps" from the county's own home page. 36,499 parcels over 70 fields.
# THE COLUMN IS `CVTTXCD` AND A SCREENING REGEX CANNOT FIND IT: it is named for
# the CIVIL TAXING UNIT and abbreviates "code" to CD, so a pattern match for
# fire|librar|park|dist|code|tax answers NONE — while the column holds a
# five-digit TAX CODE, 138 distinct values on 36,267 of the 36,499 parcels
# (99.4%). Its declared siblings are empty on every parcel in the county
# (CVTTXDSCRP, SCHLTXCD, SCHLDSCRP, USECD, USEDSCRP: 0 of 36,499), so the code
# is the whole of what the layer gives — exactly what Boone gives.
#
# ONE PARCEL IN THE COUNTY HAS NO SHAPE, and it is declared rather than
# skipped: PIN 1127382016, 805 Ave D in Rock Falls, tax code 01110, assessed
# at $53,448 — an assessment record the county has not drawn. It appears in
# the LIBRARY and PARK sets and in no fire set, because Rock Falls's city tax
# codes carry no fire district at all, which is the same fact the three
# negative fire probes below test. 232 further parcels carry no CVTTXCD and
# never enter a where clause, so they are holes by construction and printed
# on every run.
#
# THE CROSSWALK, AND THE ONE WAY THIS COUNTY IS RISKIER THAN BOONE. Boone's
# build takes its code sets from the Clerk's "Taxcode Value within District
# Report" and warns in this very file that her "District Rates by Taxcode
# Report" is the NARROWER document — read as a membership list it omitted
# twelve of Boone's codes on 956 parcels. WHITESIDE PUBLISHES ONLY THE RATES
# REPORT. Its Clerk's "Tax Computation & District Rate Information" page
# carries exactly two documents per tax year, ten years deep, and neither is a
# value-within-district report.
#
# SO THE COMPLETENESS OF THE MEMBERSHIP LIST IS TESTED RATHER THAN ASSUMED, and
# the report tests itself. Every tax-code block prints each levying district's
# rate and then its own "Totals for <code> <rate>" line. SPLIT ON THAT
# TERMINATOR AND NEVER ON THE BLOCK HEADER: the header form (`NNNNN - `) is
# lost at page breaks for twelve of the 140 codes, so a header split yields 128
# and manufactures a ten-code shortfall against the parcel layer's 138 that is
# a parse artefact and not a gap in the county's document. Split on the
# terminator and all 138 parcel codes are present, with two the report carries
# that no parcel does (00923, 01111). A district omitted
# from a code would leave that arithmetic short. ALL 140 TAX CODES BALANCE TO
# FOUR DECIMALS across 1,140 district rate lines, 140 of 140. And the omission
# mechanism that would evade an arithmetic test — a district present at a rate
# of exactly 0.0000 — is ruled out by the document's own behaviour: it PRINTS
# 16 zero-rate lines over 12 districts, including a VILLAGE (VDGR - Deer Grove
# Village), rather than suppressing them.
#
# A CODE THE REPORT DOES NOT CARRY WOULD READ AS "NO DISTRICT" AND MUST NOT.
# `code_map` skips an unmapped value silently, which is right for a code the
# county genuinely puts in no fire district and WRONG for one the crosswalk
# never saw — the two are indistinguishable downstream, and a card would say
# "no fire district" about a parcel nobody looked up. So the 140-code universe
# is declared as `code_universe` and the builder fails on any parcel code
# outside it. Boone carries the same hole and is not fixed here; its own
# crosswalk covers every code it maps, so the guard would be vacuous there
# until someone re-measures it.
#
# A SECOND CHECK WAS TRIED AND IS NOT CLAIMED. The Tax Computation Report gives
# each district's County Total EAV, so summing the parcel layer's CNTASSDVAL
# over a district's tax codes ought to reproduce it. It does not: the sums run
# +12% to +32% on twenty-one districts and NEGATIVE on four, because a parcel
# layer's current assessed value and a tax year's rate-setting EAV are not the
# same quantity. Recorded here because a reader would otherwise try it, and
# because a check that does not work must not be dressed as one that does.
WHITESIDE_PARCELS = ("https://services.arcgis.com/l0M0OC6J9QAHCiGx/arcgis/rest/"
                     "services/Tax_Parcels_Ver_2_Parcels_Only/FeatureServer/0")
WHITESIDE_TAX_YEAR = 2025
WHITESIDE_REPORTS = {
    # the membership list, and the ONLY one this county publishes
    "rates": "https://www.whitesidecountyil.gov/DocumentCenter/View/1285/"
             "2025-District-Tax-Rates-PDF",
    # per-district EAV and levy detail; used for the district NAMES, which it
    # writes identically to the rates report, and for the EAV check above that
    # does not work
    "computation": "https://www.whitesidecountyil.gov/DocumentCenter/View/1284/"
                   "2025-Tax-Computation-Rates-PDF",
}
# THE NAMES ARE THE COUNTY'S OWN AND ARE NOT EXPANDED. Both county documents
# write every body the same way — `FALB - ALBANY FIRE`, `LWAL - WALNUT PUBLIC
# LIBRARY`, `PCOL - COLOMA PARK` — in a column narrow enough that "Albany Fire"
# is plainly an abbreviation of a fire protection district's real name. It is
# rendered in title case and NOTHING IS EXPANDED: the county's ETSB page writes
# "Prophetstown Fire District" in full, which is one body of thirteen, and
# inventing the other twelve from a pattern is exactly the guess this project
# does not make. The four-letter code ships beside the name, as Woodford's
# does, so a reader or a re-verifier can find the row in the county's document.
WHITESIDE_CODE_RE = WOODFORD_CODE_RE

# THE CITY HOLES ARE MEASURED, AND ONLY TWO OF THEM ARE ATTRIBUTED. TWELVE tax
# codes carrying STERLING CITY or ROCK FALLS CITY have no fire district at all
# (seven VSTG, five VRFL, one of the five being 01111, which no parcel carries),
# which is the Metamora shape: both cities run their own departments, and the
# county's own ETSB/911 page names the "Twin City Communication Center,
# Sterling, IL (Sterling, Rock Falls Police & Fire, CGH Ambulance)". MORRISON IS
# NOT ATTRIBUTED, only measured: its two tax codes 00715 and 00805 carry no fire
# line, and no county page read here says why. Thirty-three of the 140 codes
# carry no fire line in total.

# THE 140 TAX CODES THE CLERK'S REPORT COVERS. Declared so a parcel carrying a
# code the crosswalk never saw FAILS rather than reading as "no district" —
# see code_universe in build_source. All 138 codes on the parcel layer are
# among these; 00923 and 01111 are report-only.
WHITESIDE_CODE_UNIVERSE = (
    "00101 00105 00110 00115 00116 00117 00120 00125 00201 00205 "
    "00210 00215 00220 00301 00305 00310 00315 00320 00325 00330 "
    "00401 00405 00410 00415 00420 00425 00430 00435 00440 00445 "
    "00450 00455 00460 00505 00510 00515 00520 00525 00530 00535 "
    "00540 00545 00550 00601 00605 00606 00610 00615 00625 00626 "
    "00701 00705 00710 00715 00720 00801 00805 00905 00910 00915 "
    "00920 00921 00922 00923 00925 00930 00935 01001 01005 01006 "
    "01011 01012 01013 01014 01101 01105 01110 01111 01115 01121 "
    "01201 01205 01215 01305 01320 01401 01405 01410 01415 01421 "
    "01430 01505 01510 01520 01525 01530 01535 01540 01545 01601 "
    "01605 01615 01620 01625 01630 01701 01705 01715 01720 01725 "
    "01730 01735 01805 01810 01811 01815 01820 01905 01915 01920 "
    "01925 01945 01955 02001 02005 02006 02010 02101 02105 02115 "
    "02120 02125 02201 02205 02210 02215 02220 02225 02230 02235"
).split()

WHITESIDE_FIRE_CODES = {}
for _code in ("00605 00606 01201 01205 01215 01305").split():
    WHITESIDE_FIRE_CODES[_code] = "FALB - Albany Fire"
for _code in ("00305 00330").split():
    WHITESIDE_FIRE_CODES[_code] = "FCHA - Chadwick Fire"
for _code in ("01320 01405 01410 01510 01805 01810 01811 01820 01905").split():
    WHITESIDE_FIRE_CODES[_code] = "FERI - Erie Fire"
for _code in ("00101 00105 00110 00115 00116 00117 00205 00210 00610 00615 "
              "00625 00626 00705 00720").split():
    WHITESIDE_FIRE_CODES[_code] = "FFUL - Fulton Fire"
for _code in ("01915 01955").split():
    WHITESIDE_FIRE_CODES[_code] = "FHIL - Hillsdale Fire"
for _code in ("00310 00315 00320 00410 00415 00420 00425 00445 00450 00455 "
              "00460 00505 00510 00540 00545 00910 00915 00935").split():
    WHITESIDE_FIRE_CODES[_code] = "FMLV - Milledgeville Fire"
for _code in ("00515 00530").split():
    WHITESIDE_FIRE_CODES[_code] = "FPOL - Polo Fire"
for _code in ("01415 01421 01520 01525 01545 01601 01815 01920 01925 01945 "
              "02001 02005 02006 02101 02115").split():
    WHITESIDE_FIRE_CODES[_code] = "FPTN - Prophetstown Fire"
for _code in ("01105 01115 01620 01625 01705 01715 01730").split():
    WHITESIDE_FIRE_CODES[_code] = "FRFL - Rock Falls Fire"
for _code in ("00430 00520 00535 00550 00920 00922 00923 00925 01001 01535 "
              "01540").split():
    WHITESIDE_FIRE_CODES[_code] = "FSTG - Sterling Fire"
for _code in ("01605 01615 01630 01701 01720 02010 02105 02120 02125 02205 "
              "02215 02225 02230").split():
    WHITESIDE_FIRE_CODES[_code] = "FTAM - Tampico Fire"
for _code in ("00120 00125 00215").split():
    WHITESIDE_FIRE_CODES[_code] = "FTHO - Thomson Fire"
for _code in ("01725 02201 02210 02220 02235").split():
    WHITESIDE_FIRE_CODES[_code] = "FWAL - Walnut Fire"

WHITESIDE_LIBRARY_CODES = {}
for _code in ("00606 01215").split():
    WHITESIDE_LIBRARY_CODES[_code] = "LALB - Albany Library"
for _code in ("00325 00330").split():
    WHITESIDE_LIBRARY_CODES[_code] = "LCHA - Chadwick Library"
for _code in ("01305 01320 01401 01410 01430 01805 01810 01811 01815 01820 "
              "01905 01915 01925 01955").split():
    WHITESIDE_LIBRARY_CODES[_code] = "LERI - Erie Library"
for _code in ("00110 00115 00116 00117 00625 00626").split():
    WHITESIDE_LIBRARY_CODES[_code] = "LFUL - Fulton Library"
for _code in ("00315 00320 00455 00460 00540 00545 00550").split():
    WHITESIDE_LIBRARY_CODES[_code] = "LMLV - Milledgeville Library"
for _code in ("01101 01105 01110 01111 01115 01121").split():
    WHITESIDE_LIBRARY_CODES[_code] = "LRFL - Rock Falls Library"
for _code in ("02230 02235").split():
    WHITESIDE_LIBRARY_CODES[_code] = "LWAL - Walnut Public Library"

WHITESIDE_PARK_CODES = {}
for _code in ("01101 01105 01110 01111 01115 01121 01730").split():
    WHITESIDE_PARK_CODES[_code] = "PCOL - Coloma Park"
for _code in ("00320 00420 00460 00510 00545").split():
    WHITESIDE_PARK_CODES[_code] = "PMLV - Milledgeville Park"
for _code in ("01601 01605 01920 01945 02001 02005 02006 02010 02101 02105").split():
    WHITESIDE_PARK_CODES[_code] = "PPTN - Prophetstown Park"
for _code in ("01001 01005 01006 01011 01012 01013 01014").split():
    WHITESIDE_PARK_CODES[_code] = "PSTG - Sterling Park"
for _code in ("02230 02235").split():
    WHITESIDE_PARK_CODES[_code] = "PWAL - Walnut Park"

def _in_clause(codes, col="tax_code"):
    # The column holding the code is per-county: Boone's is `tax_code`,
    # Whiteside's is `CVTTXCD` — a name that says CIVIL TAXING UNIT and holds a
    # whole five-digit tax code, which is why a screening regex over field names
    # missed it for a month (EXPANSION_GUIDE §3.5.1).
    return "%s IN (%s)" % (col, ", ".join("'%s'" % c for c in sorted(codes)))

# slug -> source config. name_prop is the case-insensitive read key, and by
# default also the property the shipped feature carries (upstream casing
# preserved). A code_map source must set out_prop instead: its name_prop names
# the INPUT column (Boone's `tax_code`) while the value that ships is a district
# NAME, and shipping a district name under a key that says "tax code" is exactly
# the kind of confidently-mislabelled column this builder refuses to carry
# forward from a county.
SOURCES = [
    {"slug": "rock-island-fire", "out": "rock-island-fire-districts.json",
     "layer": RI + "2", "name_prop": "FirePD", "expect": 17,
     "edit_pin": 1642178685982,
     "probes": [(41.36412, -90.53246, "SHERRARD FPD"),      # measured road void
                (41.50670, -90.51510, None)]},              # Moline runs a city FD
    {"slug": "rock-island-library", "out": "rock-island-library-districts.json",
     "layer": RI + "5", "name_prop": "library_di", "expect": 9,
     "edit_pin": 1642179044173, "expect_blanks": 1,  # the stray UT30 school copy
     "probes": [(41.36412, -90.53246, "SHERRARD LIBRARY"),
                (41.39334, -90.61696, "MILAN-BLACKHAWK LIBRARY"),
                (41.74022, -90.25800, "CORDOVA LIBRARY"),
                (41.40835, -90.72851, "MILAN-BLACKHAWK LIBRARY"),
                (41.50670, -90.51510, None),   # downtown Moline (municipal library)
                (41.50950, -90.57870, None),   # Rock Island city (municipal library)
                (41.43800, -90.71800, None)]}, # Andalusia (recorded gap)
    {"slug": "rock-island-park", "out": "rock-island-park-districts.json",
     "layer": RI + "8", "name_prop": "park_distr", "expect": 1,
     "edit_pin": 1642177768661, "probes": []},
    # Boone's two, the first sources here whose upstream is a PARCEL FABRIC
    # rather than a district tiling: 12,816 parcels for the park districts and
    # 9,122 for the libraries, paged 1,000 at a time and PINNED (expect_rows)
    # so a county that re-codes its roll fails the build instead of quietly
    # redrawing a district. The probes carry the
    # weight here, and they are chosen to discriminate rather than to pass —
    # every district gets a positive, every negative sits on a REAL parcel in a
    # code the Clerk's report puts in no such district, and the two sources
    # cross-check each other: 05007 is in the Belvidere park district and in no
    # library, 03004 is in the North Suburban library and in no park district,
    # so a source that quietly reused the other's code map would fail both.
    {"slug": "boone-park", "out": "boone-park-districts.json",
     "layer": BOONE_PARCELS, "name_prop": "tax_code", "expect": 2,
     "expect_rows": 12816,
     "expect_empty_codes": ["05010", "05110", "05901", "05903", "07044", "08102", "09700"],
     "out_prop": "district", "code_map": BOONE_PARK_CODES,
     "where": _in_clause(BOONE_PARK_CODES),
     "probes": [(42.25670, -88.83936, BELVIDERE_PARK),        # Belvidere City Hall (05005)
                (42.32119, -88.83908, BELVIDERE_PARK),        # 05007 — the district reaches past the city
                (42.33062, -88.93750, ROCKFORD_PARK),         # 03007 — the Loves Park strip
                (42.39853, -88.74735, None),                  # Capron village (04003) — in neither
                (42.34853, -88.93519, None)]},                # 03004 — library only, no park
    {"slug": "boone-library", "out": "boone-library-districts.json",
     "layer": BOONE_PARCELS, "name_prop": "tax_code", "expect": 3,
     "expect_rows": 9122,
     "expect_empty_codes": ["05901", "05903", "07044", "08102", "09700"],
     "out_prop": "district", "code_map": BOONE_LIBRARY_CODES,
     "where": _in_clause(BOONE_LIBRARY_CODES),
     "probes": [(42.25670, -88.83936, IDA_LIBRARY),              # Belvidere City Hall (05005)
                (42.24308, -88.93207, CHERRY_VALLEY_LIBRARY),    # 05009
                (42.33062, -88.93750, NORTH_SUBURBAN_LIBRARY),   # 03007
                (42.34853, -88.93519, NORTH_SUBURBAN_LIBRARY),   # 03004
                (42.39853, -88.74735, None),                    # Capron village (04003)
                (42.32119, -88.83908, None)]},                  # 05007 — park only, no library
    # Woodford's three, and the SIMPLER half of Boone's shape: the county
    # publishes no district tiling either, but its parcels carry the district's
    # NAME rather than a bare tax code, so no Clerk crosswalk is needed and
    # nothing is hand-transcribed. `Fire_Protection_Districts`,
    # `Library_Districts` and `Park_Districts` are three views of ONE 25,824-row
    # parcel fabric with an identical 100-column schema; each dissolves a
    # different column of it.
    #
    # THE SECOND WITNESS IS THE COUNTY'S OWN TAX SETTLEMENT SHEETS
    # (WOODFORD_SETTLEMENT_SHEETS above), and what they are NOT is worth
    # stating, because an earlier draft called them "the Clerk's certified"
    # sheets and neither half is supported: the document names NO OFFICE and
    # the word "certified" does not appear in it. What it does establish is the
    # thing that matters — the fabric's 17 fire, 6 library and 3 park districts
    # are exactly the set the county levies for, code for code (`FDBE - BENSON
    # FIRE DISTRICT` there, `FDBE - Benson Fire District` here), so the district
    # SET is corroborated by a different county product rather than by the same
    # layer restating itself.
    #
    # THE HOLES ARE MEASURED, NOT ASSUMED. 1,701 parcels carry no fire district
    # and every single one of them is in the Village of Metamora, which runs its
    # own department — the county says as much in the name of the district that
    # surrounds it, `Metamora RURAL Fire District`. 3,273 carry no library
    # (unincorporated ground plus Goodfield and Congerville) and 21,711 no park
    # district, which is ordinary: Woodford levies only three.
    #
    # THE HOLES WERE THEN COUNTED IN PEOPLE RATHER THAN IN ACRES, because area
    # answers the wrong question. The fire tiling covers 96.9% of the county by
    # area and the largest gap — 66% of all the uncovered ground — is the
    # Illinois River corridor along the western line, where the fabric has no
    # parcels because there is nothing to assess. Against the county's own
    # 16,889 ADDRESS POINTS (2026-09-05): 14,989 land inside a fire district,
    # 1,738 of the 1,900 that do not are the Village of Metamora, 79 more are
    # within the app's 60 ft runtime snap and answer anyway, and 83 — 0.49% —
    # sit on ground the county's OWN FABRIC HAS NO PARCEL FOR. Each of those 83
    # was queried against the county's service one at a time and every one came
    # back with no parcel at all. 72 of the 83 fall inside the City of Eureka's
    # own corporate boundary and 11 are scattered across the county, so the
    # BBOX of the set spans Woodford even though seven in eight sit in one
    # city — an earlier draft said only that they "cluster in and around
    # Eureka", which is true of the points and misleading about their extent.
    # The shape is a subdivision addressed before the assessor split its lots.
    # So the layer says nothing exactly where the county says nothing, which is the
    # right answer rather than a defect to close over.
    # Whiteside's three. Same machinery as Boone's — a bare tax code plus a
    # county crosswalk — with the code_map's VALUE carrying the county's own
    # four-letter district code on the front, so code_split then peels it onto
    # its own property exactly as Woodford's does. `expect_empty_codes` names
    # the codes the Clerk's report carries that no parcel does: 00923 (fire)
    # and 01111 (library and park). They are declared rather than skipped, so a
    # county that starts or stops using one fails the build.
    {"slug": "whiteside-fire", "out": "whiteside-fire-districts.json",
     "edit_pin": 1788362255421,   # the service DOES publish one
     "code_universe": WHITESIDE_CODE_UNIVERSE,
     "blocked": "Whiteside County LICENSES its GIS data and its Data License Agreement forbids redistributing products derived from it. Nothing here ships until the county gives written permission — docs/ASK_DRAFTS.md Ask 19, and the gap record whiteside-special-districts.",
     "layer": WHITESIDE_PARCELS, "name_prop": "CVTTXCD", "expect": 13,
     "where": _in_clause(WHITESIDE_FIRE_CODES, "CVTTXCD"),
     "out_prop": "district", "code_map": WHITESIDE_FIRE_CODES,
     "code_split": WHITESIDE_CODE_RE,
     "expect_rows": 19805, "expect_empty_codes": ["00923"],
     "probes": [(41.78613, -90.21635, "Albany Fire"),
                (41.86500, -90.15932, "Fulton Fire"),
                (41.65885, -90.08136, "Erie Fire"),
                (41.67015, -89.93485, "Prophetstown Fire"),
                (41.63076, -89.78513, "Tampico Fire"),
                # the three city holes, which are the probes that matter: a
                # layer that covered everything would pass every positive
                (41.79961, -89.69553, None),   # Sterling — own fire department
                (41.77238, -89.69271, None),   # Rock Falls — own fire department
                (41.80764, -89.96170, None)]}, # Morrison — own fire department
    {"slug": "whiteside-library", "out": "whiteside-library-districts.json",
     "edit_pin": 1788362255421,   # the service DOES publish one
     "code_universe": WHITESIDE_CODE_UNIVERSE,
     "blocked": "Whiteside County LICENSES its GIS data and its Data License Agreement forbids redistributing products derived from it. Nothing here ships until the county gives written permission — docs/ASK_DRAFTS.md Ask 19, and the gap record whiteside-special-districts.",
     "layer": WHITESIDE_PARCELS, "name_prop": "CVTTXCD", "expect": 7,
     "where": _in_clause(WHITESIDE_LIBRARY_CODES, "CVTTXCD"),
     "out_prop": "district", "code_map": WHITESIDE_LIBRARY_CODES,
     "code_split": WHITESIDE_CODE_RE,
     "expect_rows": 11640, "expect_empty_codes": ["01111"],
     "expect_no_geometry": 1,   # PIN 1127382016, 805 Ave D, code 01110

     "probes": [(41.86500, -90.15932, "Fulton Library"),
                (41.65885, -90.08136, "Erie Library"),
                (41.77238, -89.69271, "Rock Falls Library"),
                (41.79961, -89.69553, None),   # Sterling — municipal library
                (41.80764, -89.96170, None)]}, # Morrison — municipal library
    {"slug": "whiteside-park", "out": "whiteside-park-districts.json",
     "edit_pin": 1788362255421,   # the service DOES publish one
     "code_universe": WHITESIDE_CODE_UNIVERSE,
     "blocked": "Whiteside County LICENSES its GIS data and its Data License Agreement forbids redistributing products derived from it. Nothing here ships until the county gives written permission — docs/ASK_DRAFTS.md Ask 19, and the gap record whiteside-special-districts.",
     "layer": WHITESIDE_PARCELS, "name_prop": "CVTTXCD", "expect": 5,
     "where": _in_clause(WHITESIDE_PARK_CODES, "CVTTXCD"),
     "out_prop": "district", "code_map": WHITESIDE_PARK_CODES,
     "code_split": WHITESIDE_CODE_RE,
     "expect_rows": 15931, "expect_empty_codes": ["01111"],
     "expect_no_geometry": 1,   # the same parcel — 01110 is in both sets

     "probes": [(41.79961, -89.69553, "Sterling Park"),
                (41.77238, -89.69271, "Coloma Park"),
                (41.67015, -89.93485, "Prophetstown Park"),
                (41.86500, -90.15932, None),   # Fulton — no park district
                (41.80764, -89.96170, None)]}, # Morrison — no park district
    {"slug": "woodford-fire", "out": "woodford-fire-districts.json",
     "layer": WOODFORD_FIRE, "name_prop": "Fire_Prote", "expect": 17,
     "out_fields": "Fire_Prote", "where": "Fire_Prote <> ' '",
     "out_prop": "district",
     "expect_rows": 24123, "expect_no_geometry": 2,
     "edit_pin": 1770658506423,
     "code_split": WOODFORD_CODE_RE,
     "probes": WOODFORD_FIRE_PROBES},
    {"slug": "woodford-library", "out": "woodford-library-districts.json",
     "layer": WOODFORD_LIBRARY, "name_prop": "Library_Di", "expect": 6,
     "out_fields": "Library_Di", "where": "Library_Di <> ' '",
     "out_prop": "district",
     "expect_rows": 22551, "expect_no_geometry": 1,
     "edit_pin": 1770655810726,
     "code_split": WOODFORD_CODE_RE, "notes": WOODFORD_LIBRARY_NOTES,
     "probes": WOODFORD_LIBRARY_PROBES},
    {"slug": "woodford-park", "out": "woodford-park-districts.json",
     "layer": WOODFORD_PARK, "name_prop": "Park_Distr", "expect": 3,
     "out_fields": "Park_Distr", "where": "Park_Distr <> ' '",
     "out_prop": "district",
     "expect_rows": 4113, "edit_pin": 1770655529993,
     "code_split": WOODFORD_CODE_RE,
     "probes": WOODFORD_PARK_PROBES},
    {"slug": "kendall-fire", "out": "kendall-fire-districts.json",
     "layer": KENDALL + "Fire_Protection_Districts/FeatureServer/0",
     "name_prop": "fire", "expect": 10,
     # the loader's historical exclusion, baked in: Joliet runs a city FD
     "exclude_names": ["CITY OF JOLIET FIRE DISTRICT"],
     "probes": [(41.53252, -88.58756, "NEWARK FPD")]},  # measured 99 ft dead road
    {"slug": "kendall-park", "out": "kendall-park-districts.json",
     "layer": KENDALL + "Park_Districts/FeatureServer/0",
     "name_prop": "park", "expect": 5, "probes": []},
    {"slug": "kendall-library", "out": "kendall-library-districts.json",
     "layer": KENDALL + "Library_Districts/FeatureServer/0",
     "name_prop": "library", "expect": 9, "probes": []},
    {"slug": "macon-fire", "out": "macon-fire-districts.json",
     "layer": MACON + "Fire/FeatureServer/0", "name_prop": "Fire",
     "expect": 17, "edit_pin": 1770744832443, "probes": []},
    {"slug": "macon-library", "out": "macon-library-districts.json",
     "layer": MACON + "LibraryJoin_Dissolved/FeatureServer/0",
     "name_prop": "Library", "expect": 10, "edit_pin": 1770745259078,
     "probes": []},
    {"slug": "macon-park", "out": "macon-park-districts.json",
     "layer": MACON + "ParkJoin_Dissolve/FeatureServer/0", "name_prop": "Park",
     "expect": 6, "edit_pin": 1770754910514, "probes": []},
    # KENDALL'S FIRE FILE DOES NOT REBUILD BYTE-IDENTICALLY, and it did not
    # before this branch either — the drift is seam wobble under a count+name
    # pin that passes, so nothing here detects it. Recorded rather than fixed:
    # Kendall publishes no edit stamp, so that pin is all there is, and a
    # reproducible rebuild would also need the shapely version of the original
    # run. Nothing in this change touches that source.
    # Sangamon fire is deliberately NOT here: its 226-fragment source measured
    # as INTERLEAVED, not void-carved — 168 of its sibling gaps are another
    # district's territory and only 2 are empty ground, and closing added
    # +0.0% area when tried. Pre-building it would accomplish nothing; the
    # entry keeps live fetch and the runtime snap covers the two dead spots.
    {"slug": "cook-fire", "out": "cook-fire-districts.json",
     "layer": "https://gis.cookcountyil.gov/traditional/rest/services/"
              "politicalBoundary/MapServer/17",
     "name_prop": "AGENCY_DESCRIPTION", "expect": 40,
     "probes": [(41.91589, -87.86480, "LEYDEN FIRE PROTECTION DISTRICT"),
                (41.88250, -87.62850, None)]},  # the Loop: Chicago has CFD, no FPD
]


fail = make_fail("build-parcel-fabric-districts")


def clean(g):
    g = make_valid(g)
    if not g.is_valid:
        g = g.buffer(0)
    return g


def polygonal(g):
    if g is None:
        return None
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    if g.geom_type == "GeometryCollection":
        parts = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
        return unary_union(parts) if parts else None
    return None


def parts_of(g):
    return list(g.geoms) if g.geom_type == "MultiPolygon" else [g]


def drop_slivers(g, label, name):
    parts = parts_of(g)
    kept = [p for p in parts if p.area >= SLIVER_SQFT]
    if not kept:
        fail("%s: sliver drop removed all of %r" % (label, name))
    return unary_union(kept), len(parts) - len(kept)


def residual_voids(final_ft):
    """Sibling-part gaps still in the road band after closing.

    A gap is only a FAILURE when nothing stopped the closing: a corridor
    another district's closing also reached was deliberately left open by the
    contested-ground rule (the seam the runtime snap refuses), so those are
    reported separately and don't fail the build."""
    from shapely.ops import nearest_points
    unexplained, seams = [], []
    for n, g in final_ft.items():
        parts = parts_of(g)
        if len(parts) < 2:
            continue
        tree = STRtree(parts)
        for i, p in enumerate(parts):
            best = None
            for j in tree.query(p.buffer(160)):
                if j == i:
                    continue
                d = parts[j].distance(p)
                if d > 1 and (best is None or d < best[0]):
                    best = (d, j)
            if best and 15 <= best[0] <= 150:
                a, b = nearest_points(p, parts[best[1]])
                mid = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
                near_other = any(final_ft[m].distance(mid) <= CLOSE_FT + 10
                                 for m in final_ft if m != n)
                if near_other:
                    seams.append((n, round(best[0])))
                    break
                # Erosion dissolves a bridge whose facing frontage is shorter
                # than the closing diameter — a lone outlying parcel across a
                # road from its district body stays separate BY CONSTRUCTION.
                # The parcel itself answers by containment and the runtime
                # snap covers the road strip, so report it, don't fail on it.
                r = best[0] / 2.0 + 5
                ov = p.buffer(r).intersection(parts[best[1]].buffer(r))
                if ov.area < (2 * CLOSE_FT) ** 2:
                    seams.append((n, round(best[0])))
                else:
                    unexplained.append((n, round(best[0])))
                break
    return unexplained, seams


def build_source(cfg):
    meta = requests.get(cfg["layer"], params={"f": "json"}, timeout=90).json()
    edit_ms = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    pin = cfg.get("edit_pin")
    if pin is not None and edit_ms != pin:
        fail("%s: edit date %r != pinned %r — the county changed the fabric; "
             "re-verify this script's measurements before rebuilding"
             % (cfg["slug"], edit_ms, pin))
    if pin is None:
        # SAY WHICH IS MISSING, the pin or the stamp. This printed "no edit
        # stamp published" whenever no pin was declared, including on services
        # that publish one perfectly well — Whiteside's dataLastEditDate is
        # live — which reads as a fact about the county and is a fact about
        # this config.
        print("  (%s; count+name pin is the guard; live stamp: %r)"
              % ("no edit_pin declared" if edit_ms is not None
                 else "no edit stamp published by the service", edit_ms))

    # A source whose SHIPPED value is not the column's own value must say what
    # column it ships under. Two ways that happens, and both mislabel the data
    # in the same way if left alone: a code_map source reads Boone's `tax_code`
    # and ships a district NAME, and a code_split source reads Woodford's
    # `Fire_Prote` ("FDBE - Benson Fire District") and ships only the name half.
    # THIS GUARD WAS code_map-ONLY AND THAT COST A BROWSER RUN: Woodford's three
    # files shipped under `Fire_Prote`/`Library_Di`/`Park_Distr` while the app
    # read `district`, so every static gate passed and every card rendered with
    # its district name reading "Unknown".
    if (cfg.get("code_map") is not None or cfg.get("code_split")) \
            and not cfg.get("out_prop"):
        fail("%s: a source that transforms its name (code_map or code_split) "
             "must set out_prop — name_prop names the INPUT column, and "
             "shipping a different value under it would mislabel the column"
             % cfg["slug"])

    where = cfg.get("where", "1=1")

    # ASK THE SERVER HOW MANY ROWS IT HAS, THEN REQUIRE THE PAGER TO DELIVER
    # THAT MANY. The loop used to trust `exceededTransferLimit` alone, and that
    # flag's LOCATION IS A SERVER DIALECT: an ArcGIS Server MapServer (Boone,
    # Cook) puts it at the top level of a GeoJSON response, while an AGOL hosted
    # FeatureServer (Woodford) puts it under "properties". Reading only the top
    # level, Woodford's 24,123-parcel fire fabric returned its first 1,000 rows
    # with the flag apparently absent and the pager stopped — a district drawn
    # from 4% of its own ground, silently, which is the exact failure the
    # paragraph below says this loop exists to prevent. So the flag is read from
    # BOTH places AND the total is checked against the county's own count: a
    # dialect this script has not met yet fails loudly instead of truncating.
    count_probe = requests.get(cfg["layer"] + "/query", params={
        "where": where, "returnCountOnly": "true", "f": "json",
    }, timeout=120).json().get("count")

    # WHERE + PAGINATION, because Boone's upstream is not a district tiling.
    # Every other source here publishes one row per district (9 to 40 of them),
    # so a single unpaginated query was right and its 1,000-row cap was never
    # near. Boone publishes no district layer at all: its park and library
    # footprints exist only as PARCELS carrying a tax_code, 12,816 and 9,122 of
    # them, and the same one-shot query would have returned the first 1,000 and
    # said nothing — a district drawn from 8% of its own ground, silently. So
    # the fetch pages, and REFUSES rather than truncating if the server still
    # reports more to give.
    #
    # outFields defaults to "*", which is right for a district tiling. A PARCEL
    # fabric sets out_fields to the one column being dissolved: Woodford's
    # carries 100 columns per row including owner names, home addresses and
    # billing addresses, and the honest handling of data this app would never
    # show is not to fetch it.
    features, offset = [], 0
    while True:
        page = requests.get(cfg["layer"] + "/query", params={
            "where": where, "outFields": cfg.get("out_fields", "*"),
            "outSR": 4326, "f": "geojson",
            "resultOffset": offset, "resultRecordCount": PAGE_SIZE,
        }, timeout=180).json()
        got = page.get("features") or []
        features += got
        more = page.get("exceededTransferLimit") or \
            (page.get("properties") or {}).get("exceededTransferLimit")
        if not more or not got:
            break
        offset += len(got)
        if offset > MAX_FETCH_ROWS:
            fail("%s: fetch passed %d rows without the server saying it was "
                 "done — refusing to guess where the data ends"
                 % (cfg["slug"], MAX_FETCH_ROWS))
    if isinstance(count_probe, int):
        if len(features) != count_probe:
            fail("%s: paged %d rows but the server counts %d for the same "
                 "where clause — the pager stopped early (check whether this "
                 "service reports exceededTransferLimit somewhere new)"
                 % (cfg["slug"], len(features), count_probe))
    else:
        print("  (server returned no row count to check the pager against: %r)"
              % (count_probe,))
    geo = {"features": features}

    # ROW-COUNT PIN + EMPTY-CODE GATE, for a code_map source only. `expect`
    # counts DISTRICTS, which for Boone is 2 and 3 — floors so low that half the
    # roll could vanish and every guard here would still pass. So the parcel
    # count is pinned too, and each mapped code is asked whether it produced a
    # parcel: today 7 of the 26 park codes and 5 of the 24 library codes resolve
    # to none. That is not a fault — a tax code with no parcels contributes no
    # geometry — but it was happening SILENTLY, so the codes are declared and
    # any change to that set stops the build.
    # THE ROW PIN IS FOR ANY PARCEL FABRIC, not only a code_map one. `expect`
    # counts DISTRICTS, which for a fabric is a floor so low that half the roll
    # could vanish and every guard here would still pass — true of Boone's 2 and
    # 3, and of Woodford's 3 park districts drawn from 4,113 parcels.
    if cfg.get("expect_rows") is not None:
        want_rows = cfg["expect_rows"]
        if len(features) != want_rows:
            fail("%s: %d parcels, expected %d — the county re-coded its roll; "
                 "re-verify this source's measurements before re-pinning"
                 % (cfg["slug"], len(features), want_rows))
    # EVERY PARCEL CODE MUST BE ONE THE CROSSWALK SAW. `code_map` skips an
    # unmapped value silently, which is right for a code the county puts in no
    # district and WRONG for one the crosswalk never covered — downstream the
    # two are identical, and a card would say "no fire district" about a parcel
    # nobody looked up. A source that declares its code universe fails instead.
    if cfg.get("code_universe"):
        universe = set(cfg["code_universe"])
        stray = sorted({" ".join(str((f.get("properties") or {}).get(k) or "").split())
                        for f in features
                        for k in (f.get("properties") or {})
                        if k.lower() == cfg["name_prop"].lower()} - universe - {""})
        if stray:
            fail("%s: %d parcel code(s) are outside the declared crosswalk "
                 "universe and would read as 'no district': %s"
                 % (cfg["slug"], len(stray), stray[:12]))
        print("  every parcel code is one of the %d the crosswalk covers"
              % len(universe))

    if cfg.get("code_map") is not None:
        seen = set()
        for f in features:
            props = f.get("properties") or {}
            for k in props:
                if k.lower() == cfg["name_prop"].lower() and props[k]:
                    seen.add(" ".join(str(props[k]).split()))
        empty = sorted(set(cfg["code_map"]) - seen)
        if empty != sorted(cfg.get("expect_empty_codes", [])):
            fail("%s: codes with no parcel changed — got %s, expected %s"
                 % (cfg["slug"], empty, sorted(cfg.get("expect_empty_codes", []))))
        if empty:
            print("  %d mapped code(s) resolve to NO parcel and contribute no "
                  "geometry: %s" % (len(empty), " ".join(empty)))
        # The parcels with NO tax_code never enter the where clause at all, so
        # they are holes by construction rather than by decision. Counted and
        # printed because an unmeasured hole is the thing this builder exists to
        # refuse; what they ARE is recorded in the gap record, not guessed at.
        nulls = requests.get(cfg["layer"] + "/query", params={
            "where": cfg["name_prop"] + " IS NULL", "returnCountOnly": "true", "f": "json",
        }, timeout=120).json().get("count")
        print("  %s parcels carry no %s at all and are outside this build by "
              "construction" % (nulls, cfg["name_prop"]))

    # Accumulate PARTS and union each district ONCE at the end. Unioning
    # incrementally per row — the shape this loop had — is quadratic in the row
    # count. Harmless for a 17-row district tiling, and it does not finish in
    # any usable time over Boone's 12,264 parcels, which is what a parcel fabric
    # costs. Same geometry either way; a single unary_union over a list is the
    # call shapely is built for.
    parts, blanks, no_geom = {}, 0, {}
    excl = set(cfg.get("exclude_names", []))
    for f in geo.get("features", []):
        props = f.get("properties") or {}
        v = None
        for k in props:
            if k.lower() == cfg["name_prop"].lower():
                v = props[k]
        # A code_map source names its district from a LOOKUP rather than from
        # the row: Boone's parcels carry a tax_code, and which districts each
        # code pays into is the County Clerk's own "Taxcode Value within
        # District Report". A code the map does not carry is skipped, not
        # guessed — the where clause should already have excluded it, and a row
        # arriving anyway means the county changed something.
        if cfg.get("code_map") is not None:
            v = cfg["code_map"].get(" ".join(str(v or "").split()))
        name = " ".join(str(v or "").split())
        if not name:
            blanks += 1
            continue
        if name in excl:
            continue
        # A PARCEL ROW WITH NO SHAPE AT ALL. Woodford's roll carries three
        # (two on the fire view, one on the library view, all in Eureka) — an
        # assessment record the county has not drawn, which contributes no
        # ground to a district built from thousands of other parcels. It is
        # DECLARED rather than skipped: an undeclared skip here is how a fabric
        # loses ground quietly, so the count is pinned per source and a change
        # to it stops the build. Distinguish it from a row that HAS a geometry
        # which cleaning cannot use — that is a fault and still fails.
        if not f.get("geometry"):
            no_geom[name] = no_geom.get(name, 0) + 1
            continue
        g = polygonal(clean(shape(f["geometry"])))
        if g is None or g.is_empty:
            fail("%s: %r has no usable geometry" % (cfg["slug"], name))
        parts.setdefault(name, []).append(g)

    named = {n: (unary_union(v) if len(v) > 1 else v[0]) for n, v in parts.items()}

    if sum(no_geom.values()) != cfg.get("expect_no_geometry", 0):
        fail("%s: %d rows carry no geometry, expected %d (%s) — the county's "
             "roll changed; re-verify before re-pinning"
             % (cfg["slug"], sum(no_geom.values()),
                cfg.get("expect_no_geometry", 0), dict(no_geom)))
    if no_geom:
        print("  %d undrawn parcel row(s), contributing no ground: %s"
              % (sum(no_geom.values()),
                 ", ".join("%s x%d" % (k, v) for k, v in sorted(no_geom.items()))))
    if blanks != cfg.get("expect_blanks", 0):
        fail("%s: %d blank-named rows, expected %d — the layer changed"
             % (cfg["slug"], blanks, cfg.get("expect_blanks", 0)))
    if len(named) != cfg["expect"]:
        fail("%s: %d named districts, expected %d (got: %s)"
             % (cfg["slug"], len(named), cfg["expect"], sorted(named)[:20]))

    b = unary_union(list(named.values())).bounds
    lat0 = (b[1] + b[3]) / 2.0
    cos0 = math.cos(math.radians(lat0))

    def to_ft(g):
        return transform(lambda x, y, z=None:
                         (x * cos0 * FEET_PER_DEG_LAT, y * FEET_PER_DEG_LAT), g)

    def from_ft(g):
        return transform(lambda x, y, z=None:
                         (x / (cos0 * FEET_PER_DEG_LAT), y / FEET_PER_DEG_LAT), g)

    raw_ft = {n: to_ft(g) for n, g in named.items()}
    closed_ft = {n: clean(g.buffer(CLOSE_FT).buffer(-CLOSE_FT))
                 for n, g in raw_ft.items()}

    final_ft = {}
    for n in sorted(named):
        mine = closed_ft[n]
        others = [closed_ft[m] for m in closed_ft if m != n]
        if others:
            mine = polygonal(clean(mine.difference(unary_union(others))))
            if mine is None:
                fail("%s: %r vanished in the contested-ground subtraction"
                     % (cfg["slug"], n))
        final = polygonal(clean(unary_union([raw_ft[n], mine])))
        final = clean(final.simplify(SIMPLIFY_FT, preserve_topology=True))
        final, dropped = drop_slivers(final, cfg["slug"], n)
        final_ft[n] = final
        print("  %-42s %4d parts -> %3d  (+%4.1f%% area, %d slivers dropped)"
              % (n[:42], len(parts_of(raw_ft[n])), len(parts_of(final)),
                 100.0 * (final.area - raw_ft[n].area) / raw_ft[n].area, dropped))

    # Deterministic disjointness for CLOSING-ADDED ground only: the later name
    # cedes wobble strips and closing bulges, but ground the county's own
    # fabric puts in BOTH districts (Cook's Clerk tiling double-claims
    # Orland∩Mokena by 57 acres) ships in both, exactly as the live layer
    # answers today — raw ground is never surrendered, even to a sibling.
    ordered = sorted(final_ft)
    raw_overlaps = {}
    for i, a in enumerate(ordered):
        for bn in ordered[i + 1:]:
            ov = raw_ft[a].intersection(raw_ft[bn]).area
            if ov > SLIVER_SQFT:
                raw_overlaps[(a, bn)] = ov
                print("  county double-claim: %-30s ∩ %-30s %8.0f sq ft (kept in both)"
                      % (a[:30], bn[:30], ov))
    def cede(loser, keeper):
        """loser gives up its NON-RAW ground wherever keeper's final claims it."""
        takeable = final_ft[keeper].difference(raw_ft[loser])
        ceded = final_ft[loser].intersection(takeable).area
        if ceded > 0:
            final_ft[loser] = polygonal(clean(final_ft[loser].difference(takeable)))
            if final_ft[loser] is None or final_ft[loser].is_empty:
                fail("%s: %r vanished enforcing disjointness" % (cfg["slug"], loser))
            if ceded > SLIVER_SQFT:
                print("  seam: %-38s ceded %6.0f sq ft to %s"
                      % (loser[:38], ceded, keeper))
    for i, n in enumerate(ordered):
        for m in ordered[:i]:
            if not final_ft[n].intersects(final_ft[m]):
                continue
            cede(n, m)  # later name yields first…
            cede(m, n)  # …then the earlier one sheds any wobble left on n's raw
            # after both, remaining overlap ⊆ raw_n ∩ raw_m: the county's own claim

    for n in final_ft:
        lost = raw_ft[n].difference(final_ft[n]).area
        # Simplify wobble sheds foot-wide strips along shared seams, so a
        # TINY high-perimeter district (Kendall's 0.075 sq mi Montgomery
        # sliver) can lose a large FRACTION that is a trivial AREA. Fail only
        # when both the fraction and the absolute area say real ground went
        # missing — a subtraction bug loses whole percents of a real district.
        if lost > 0.005 * raw_ft[n].area and lost > 25000:
            fail("%s: %r lost %.2f%% of county-published ground (%.0f sq ft)"
                 % (cfg["slug"], n, 100.0 * lost / raw_ft[n].area, lost))
        elif lost > 0.005 * raw_ft[n].area:
            print("  tolerated: %-34s lost %.2f%% (%.0f sq ft of seam wobble)"
                  % (n[:34], 100.0 * lost / raw_ft[n].area, lost))
        over = final_ft[n].difference(
            raw_ft[n].buffer(CLOSE_FT + SIMPLIFY_FT + 5)).area
        if over > SLIVER_SQFT:
            fail("%s: %r claims %.0f sq ft beyond the closing's possible reach"
                 % (cfg["slug"], n, over))
    for i, a in enumerate(ordered):
        for bn in ordered[i + 1:]:
            ov = final_ft[a].intersection(final_ft[bn])
            if ov.area <= 1.0:
                continue
            # the only overlap allowed to survive is the county's own
            # double-claimed ground (plus a wobble margin around it)
            allowed = raw_ft[a].intersection(raw_ft[bn]).buffer(SIMPLIFY_FT + 5)
            extra = ov.difference(allowed).area
            if extra > SLIVER_SQFT:
                fail("%s: %r and %r overlap by %.0f sq ft beyond the county's "
                     "own double-claim" % (cfg["slug"], a, bn, extra))
    unexplained, seams = residual_voids(final_ft)
    if len(unexplained) > MAX_RESIDUAL_VOIDS:
        fail("%s: %d districts carry road-band voids the closing should have "
             "bridged: %s" % (cfg["slug"], len(unexplained), unexplained[:8]))
    if unexplained:
        print("  residual near-gaps (nothing nearby stopped the closing):", unexplained)
    if seams:
        print("  gaps kept by design (contested seam or short-frontage outlier):", seams)

    out_prop = cfg.get("out_prop", cfg["name_prop"])

    # SPLIT A COUNTY'S OWN CODE OFF THE FRONT OF THE NAME, when the source says
    # its names carry one. Woodford's fabric and its certified settlement sheets
    # both write every district as `FDBE - Benson Fire District`: the code is
    # the county's join key between the two documents and is worth keeping, and
    # it is not what a resident's card should lead with. The pattern is
    # DECLARED per source and every name must match it — a county that changes
    # its convention fails the build rather than shipping a half-split set —
    # and the code ships beside the name rather than being discarded, so
    # nothing the county published is lost.
    split_re = re.compile(cfg["code_split"]) if cfg.get("code_split") else None
    codes = {}
    if split_re:
        for n in ordered:
            m = split_re.match(n)
            if not m:
                fail("%s: %r does not match the declared code pattern %s"
                     % (cfg["slug"], n, cfg["code_split"]))
            codes[n] = (m.group("code"), m.group("name"))
        shown = [v[1] for v in codes.values()]
        if len(set(shown)) != len(shown):
            fail("%s: splitting the code off leaves duplicate names (%s) — the "
                 "code was carrying the distinction" % (cfg["slug"], sorted(shown)))

    features = []
    for n in ordered:
        g = from_ft(final_ft[n])
        geom = json.loads(json.dumps(mapping(g)))

        def rnd(c):
            if isinstance(c, (int, float)):
                return round(c, 5)
            return [rnd(x) for x in c]
        geom["coordinates"] = rnd(geom["coordinates"])
        props = {out_prop: n}
        if split_re:
            props = {out_prop: codes[n][1], "code": codes[n][0]}
        note = (cfg.get("notes") or {}).get(n)
        if note:
            props["note"] = note
        features.append({"type": "Feature",
                         "properties": props,
                         "geometry": geom})
    fc = {"type": "FeatureCollection", "features": features}

    for lat, lng, want in cfg["probes"]:
        p = Point(lng, lat)
        hits = [f["properties"][out_prop] for f in features
                if shape(f["geometry"]).contains(p)]  # the SHIPPED name
        got = hits[0] if hits else None
        print("  probe %.5f,%.5f -> %-30s [%s]"
              % (lat, lng, got or "no district", "ok" if got == want else "FAIL"))
        if got != want:
            fail("%s: probe %.5f,%.5f expected %r, got %r"
                 % (cfg["slug"], lat, lng, want, got))

    payload = json.dumps(fc, separators=(",", ":"))
    if len(json.loads(payload)["features"]) != cfg["expect"]:
        fail("%s round-trip mismatch" % cfg["out"])
    with open(os.path.join(APP_DIR, cfg["out"]), "w", encoding="utf-8") as f:
        f.write(payload)
    print("  wrote data/app/%s (%d features, %.0f KB)"
          % (cfg["out"], cfg["expect"], len(payload) / 1024.0))


def main():
    only = set(sys.argv[1:])
    print("build-parcel-fabric-districts: closing %g ft, simplify %g ft"
          % (CLOSE_FT, SIMPLIFY_FT))
    for cfg in SOURCES:
        if only and cfg["slug"] not in only:
            continue
        # A SOURCE THE PUBLISHER LICENSES IS NOT BUILT, and the guard is here
        # rather than in a comment because the file this builder writes is
        # exactly the "product derived therefrom" such a licence forbids. Naming
        # it `--force-blocked` and refusing by default means the licensed county
        # cannot be shipped by someone re-running the builder to refresh
        # everything else.
        if cfg.get("blocked") and "--force-blocked" not in only:
            print("%s: SKIPPED — %s" % (cfg["slug"], cfg["blocked"]))
            continue
        print("%s:" % cfg["slug"])
        build_source(cfg)


if __name__ == "__main__":
    main()
