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
workflow (.github/workflows/ia-validate-sources.yml) opens an issue on WARN or
FAIL so drift is never silent, without turning the build red.

Usage:
    python3 ia/scripts/validate_sources.py                 # human-readable report
    python3 ia/scripts/validate_sources.py --report r.md   # also write markdown
    python3 ia/scripts/validate_sources.py --status-file s.txt   # ok|warn|fail
    python3 ia/scripts/validate_sources.py --offline       # manifest↔app checks only
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
        "layer": "us-house",
        "app_file": "congress-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0",
        "note": "Congressional districts pre-built from TIGERweb by ia/scripts/build_legislative_boundaries.py; redraws each decennial cycle (WATCH.md). Built against TIGERweb's 120th-Congress layer (field CD120, Jan 1 2026 vintage); the retired CD119 field is gone and a query naming it returns an HTTP-200 JSON error envelope with no features key, so a rebuild on the old name fails as no-features.",
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-ia-congress-roster.yml.",
    },
    {
        "layer": "ia-judicial-district",
        "app_file": "ia-judicial-districts.json",
        "source_url": "https://www.iowacourts.gov/iowa-courts/district-court/",
        "note": (
            "8 judicial election districts, whole-county unions per Iowa Code "
            "SS602.6107/602.6109 (Code 2003) -- the county-to-district crosswalk "
            "is cross-verified against iowacourts.gov's own per-district county "
            "page and Ballotpedia, then dissolved from state-counties.json by "
            "ia/scripts/build_ia_judicial_district.py."
        ),
    },
    {
        "layer": "ia-judicial-district",
        "app_file": "ia-judicial-districts.json",
        "source_url": (
            "https://services2.arcgis.com/KhKjlwEBlPJd6v51/arcgis/rest/services/"
            "JudicialDistricts/FeatureServer/0"
        ),
        "note": (
            "LSAFiscal's own published district polygons -- the spatial double "
            "witness the builder checks the crosswalk against at build time, "
            "never the geometry source itself (this layer draws no new "
            "boundary; it dissolves whole counties)."
        ),
    },
    {
        "layer": "ia-judicial-district",
        "app_file": "ia-judicial-judges.json",
        "source_url": "https://www.iowacourts.gov/iowa-courts/district-court/judicial-district-1/judges-and-magistrates-district-1/",
        "note": (
            "371 judges across all 8 districts (measured 2026-08-28), from each "
            "district's own \"Judges and Magistrates\" page -- three different "
            "URL shapes, one per district (see "
            "ia_judicial_district_scraper.py). Judges are RETENTION, never "
            "elected; no phone/e-mail/address is published for any judge."
        ),
    },
    {
        "layer": "community-college",
        "app_file": "ia-community-colleges.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/CC_2026update/FeatureServer/0",
        "note": (
            "15 community college merged areas, shipped as published (no "
            "dissolve) -- the 2026-07-02 vintage, which fixes a confirmed "
            "coding error the older CommColleges2020 layer carries for "
            "Southeastern Community College. Pre-built by "
            "ia/scripts/build_ia_community_colleges.py, witnessed against a "
            "second LSA layer on name set, 2020 census population (Iowa's "
            "exact 3,190,369) and director-district count (124)."
        ),
    },
    {
        "layer": "community-college",
        "app_file": "ia-community-colleges.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/CommColleges2020/FeatureServer/1",
        "note": (
            "The second LSA layer used as the build-time witness (name set, "
            "population, director-district count) -- never the geometry "
            "source itself."
        ),
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": "County polygons pre-built from TIGERweb by ia/scripts/build_state_counties.py.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-auditors.json",
        "source_url": "https://iowaauditors.org/find/directory/",
        "note": "All 99 county auditors (Iowa Code 47.2), from the auditors' own association directory. Built by ia/scripts/ia_county_auditor_scraper.py + build_ia_county_auditors.py; refreshed weekly by update-ia-county-auditor-roster.yml.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-auditors.json",
        "source_url": "https://sos.iowa.gov/auditors/",
        "note": "The Secretary of State's own auditors page — the second witness on every auditor's name and party, and the ONLY published source of an auditor e-mail (Cloudflare data-cfemail, decoded at scrape time). Read by the same ia/scripts/ia_county_auditor_scraper.py.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-officers.json",
        "source_url": "https://member-portal.iowacounties.org/countydirectory/directory/Story",
        "note": "ISAC's member portal, one page per county — the ONLY statewide source for the county treasurer and for the board of supervisors. Probed here at a single county (Story) because the portal has no index page; a bad county name answers HTTP 200 with an empty table, so the scraper gates on parsed row count and never on status. Built by ia/scripts/ia_county_officers_scraper.py + build_ia_county_officers.py; refreshed weekly by update-ia-county-officers-roster.yml.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-officers.json",
        "source_url": "https://iowalandrecords.org/recorder-directory/",
        "note": "All 99 county recorders with a plain mailto: and office phone — the highest-quality county officer source found in Iowa, and the recorder row's authority over the ISAC portal.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-officers.json",
        "source_url": "https://www.issda.org/assets/Gold-Star/2025%20Sheriff%20Directory.pdf",
        "note": "The Iowa State Sheriffs' & Deputies' Association directory (PDF, 4 April 2025) — the sheriff row's authority. A DATED DOCUMENT, so it is the half of the pair that goes stale: Sac County's own site names a sheriff this PDF has not caught up with, pinned in the builder's DIVERGENCE_RESOLVED. A newer edition appearing at a different path is the thing to watch for.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-officers.json",
        "source_url": "https://iowa-icaa.com/Roster/%40RosterOfCA%26ACAs.pdf",
        "note": "The Iowa County Attorneys Association roster (PDF, 5 May 2026) — the county attorney row's authority. Note the literal @ and & in the filename. iowa-icaa.com answers 404 with a FULL page body, so a reachability check on any other path there proves nothing.",
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-supervisor-members.json",
        "source_url": "https://www.polkcountyiowa.gov/board-of-supervisors/",
        "note": "Which supervisor holds each district, for PLAN 3 counties only (Iowa Code 331.206 — plan 1 has no districts and plan 2 elects countywide). There is no statewide source: the Legislature's own layer names DISTRICTS not people, the ISAC portal attaches a district to nobody, the Secretary of State's statewide canvass carries ZERO supervisor contests (counties canvass their own county offices), and electionresults.iowa.gov exposes no data API. So each county's own board page supplies the district NUMBER by proximity to names the shipped roster already carries. Probed here at one representative county (Polk); the run reads 40 and keys the ones that pass its gates. Built by ia/scripts/ia_supervisor_district_scraper.py + build_ia_supervisor_roster.py; refreshed weekly by update-ia-supervisor-roster.yml.",
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-county-board-chairs.json",
        "source_url": "https://www.linncountyiowa.gov/123/Board-of-Supervisors",
        # ONE ROW, NOT THIRTY-SIX, and the reason is not brevity. Every county
        # page this file rests on ships as a `sourceUrl` INSIDE the data file,
        # and validate_card_links.py extracts every http string in every
        # instance's data/app -- so all 36 are already probed monthly, by the
        # gate whose whole design is that a new one is covered the day it
        # ships. Duplicating them here would be a second hand-kept list of the
        # same URLs, going stale in the way that gate exists to prevent. What
        # this row registers is the PIPELINE.
        "note": "Which supervisor chairs each county board -- 35 of 99 counties, probed here at one representative county (Linn); the run reads all 98 in ia-county-board-directory.json and keys the ones that pass its gates, and the other 34 shipped URLs are probed by validate_card_links.py out of the data file itself. THERE IS NO STATEWIDE SOURCE AND THE TWO OBVIOUS CANDIDATES WERE MEASURED, NOT ASSUMED: the ISAC member portal is already this app's source for the supervisors themselves and its per-county pages contain ZERO occurrences of chair, chairperson, chairman, chairwoman or vice-chair; and iowaauditors.org answers 200 on /, /directory/ and /county-auditors/ with zero occurrences of the same, because it publishes county AUDITORS, who are not board members. The chair is chosen by each board's own January vote, so a weekly re-read tracks it where a one-time answer from 99 offices would not -- which is why the gap record carries NOT YET ASKED rather than a drafted ask. Built by ia/scripts/ia_county_chair_scraper.py + build_ia_county_chair.py; refreshed weekly by update-ia-county-chair-roster.yml.",
    },
    {
        "layer": "city-ward",
        "app_file": "dsm-wards.json",
        "source_url": "https://services.arcgis.com/HT7H9QGiZQoRJDpJ/arcgis/rest/services/Wards_view/FeatureServer/0",
        "note": "The City of Des Moines's own four council wards, pre-built by ia/scripts/build_dsm_wards.py. THE ITEM'S licenseInfo OPENS \"All rights reserved\" AND IS NOT A REFUSAL: the city's own Terms and Conditions of Use (data.dsm.city/pages/terms) permit applications using portal data on condition they carry that exact disclaimer, so the string is the required NOTICE, and the app ships it verbatim on the card. The same terms carry a Right to Discontinue Feeds clause, which is the reason this row exists — a city may withdraw the service, and the shipped file would then be the only copy.",
    },
    {
        "layer": "city-ward",
        "app_file": "dsm-council-members.json",
        "source_url": "https://www.dsm.city/government/city_council/index.php",
        "note": "All seven seats Des Moines elects (Iowa Code 372.4(1)(b): a mayor, two at-large members, one from each of four wards). The page renders Appointed Staff and Department Directors in IDENTICAL card markup to the elected members, so the scrape is scoped by <h2> heading and refuses if a name appears under both; the four ward members are cross-witnessed against the Wards layer's own in-band names and e-mails. Built by ia/scripts/dsm_council_scraper.py + build_dsm_council.py; refreshed weekly by update-ia-dsm-council-roster.yml.",
    },
    {
        "layer": "city-ward",
        "app_file": "waterloo-wards.json",
        "source_url": "https://services1.arcgis.com/QOAXA4I2iTKKdBuy/ArcGIS/rest/services/Wards_view/FeatureServer/0",
        "note": "The City of Waterloo's own five council wards, pre-built by ia/scripts/build_waterloo_wards.py. THE SERVICE STATES NO TERMS AT ALL: queried unauthenticated 2026-09-04 it returns capabilities Query,Extract with BOTH serviceDescription AND copyrightText EMPTY, and the city's robots.txt is empty too. That is recorded rather than read as permission or as refusal, and it is the plain difference from Des Moines, whose terms REQUIRE a verbatim disclaimer -- so Waterloo's card carries no data notice, and this row is where a reader learns that absence was looked for. This row also exists because a city may simply stop publishing: the shipped file would then be the only copy.",
    },
    {
        "layer": "city-ward",
        "app_file": "waterloo-council-members.json",
        "source_url": "https://www.cityofwaterlooiowa.com/government/city_council/index.php",
        "note": "The seven seats Waterloo elects to its council (five wards + two at-large; the mayor is elected citywide and is deliberately not in this file). The page is hand-pasted WYSIWYG HTML with NO per-member container -- one member sits inside an <h2> and the other six are loose <span> runs in <p> blocks -- so the scrape keys on each member's own 'NAME, SEAT Through MM/DD/YYYY' line. The bio-link anchors that repeat every name WITHOUT a term are kept as the control, and TWO of them disagree with the authoritative spelling ('Steve Simons' for Steve Simon), which is why an anchor-keyed parse would ship a misspelt councilman. All five wards and both at-large members are cross-witnessed against the Wards layer's own in-band names. Built by ia/scripts/waterloo_council_scraper.py + build_waterloo_council.py; refreshed weekly by update-ia-waterloo-council-roster.yml.",
    },
    {
        "layer": "city-ward",
        "app_file": "cedar-rapids-wards.json",
        "source_url": "https://services.arcgis.com/i14SLLmXo7Hn9vNc/ArcGIS/rest/services/ElectionsCityCouncilDistrict/FeatureServer/0",
        "note": "Cedar Rapids's five council districts -- and THIS IS NOT THE CITY'S SERVICE. Cedar Rapids publishes no boundary of its own; this is LINN COUNTY's, and it holds NINE polygons for the two Linn cities that elect by district, Cedar Rapids's five and Marion's four, separated only by POLITICAL_TWP ('27' and '21') -- a bare code with no name field, no domain and no description anywhere in the service. A build keyed on an opaque code must prove the code, so build_cedar_rapids_wards.py re-establishes it EVERY RUN IN BOTH DIRECTIONS: the five under '27' must tile Cedar Rapids (area ratio 1.00323, 0.1338% uncovered in 366 fragments) and Marion's four under '21' must fail to, leaving 99.996% of the city uncovered. Without that second half a code swap would put Marion's districts on Cedar Rapids readers' cards under Cedar Rapids labels and nothing here would notice. Queried unauthenticated 2026-09-04: copyrightText and serviceDescription both EMPTY, so no data notice ships -- recorded rather than read as permission or refusal. City limits for the tiling gate come from TIGERweb because Linn publishes NO city-limits polygon at all (its RealEstateBoundary is a cadastral LINE layer), making this a cross-publisher comparison whose ceilings are necessarily looser than the two same-publisher ones.",
    },
    {
        "layer": "city-ward",
        "app_file": "cedar-rapids-council-members.json",
        "source_url": "https://www.cedar-rapids.org/local_government/city_council/mayor_and_city_council/index.php",
        "note": "Eight of the nine seats Cedar Rapids elects (five districts + three at-large; the mayor is elected citywide and is deliberately not in this file, though she IS scraped so that exclusion stays a decision the pipeline can demonstrate). ONE PAGE PER SEAT, seven of them, each member a structured <h2> heading plus the <p> that follows it -- so contact is read from inside that block and nowhere else. THE CITY CLERK'S 319-286-5763 SITS IN THE FURNITURE OF ALL SEVEN PAGES: a window-based or first-number-on-the-page parse would ship it as every member's direct line, which is the shared-number failure the switchboard rule catches only after the fact, so the scraper asserts it appears on each page AND never inside a member block. The council seats TWO OLSONS (Tyler at-large, Scott in District 4), so surname is not a key and a repeated full name fails the scrape; District 4's heading also carries post-nominals ('Scott Olson, AIA (Emeritus), RCFM, RSIOR') and his contact is published on his own firm's domain, which ships because the officeholder's name vouches for the address. Each district page's own stated number is checked against its URL, so a CMS reordering fragments cannot serve one district's member under another's address. NO IN-BAND ROSTER EXISTS to witness against -- Linn's layer carries no names -- so the witness is the numbering against the shipped boundary, which is weaker than Des Moines's and Waterloo's and is recorded as weaker. Built by ia/scripts/cedar_rapids_council_scraper.py + build_cedar_rapids_council.py; refreshed weekly by update-ia-cedar-rapids-council-roster.yml.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-officers.json",
        "source_url": "https://www.iowatreasurers.org/index.php?module=treashome&idCounty=1",
        "note": "The Iowa county treasurers' own state site, ONE OF TWO sources for the treasurer's e-mail address -- the office no statewide directory carries one for (the ISAC portal has no e-mail column at all: re-checked 2026-08-29, zero mailto and zero @ on a county page). ITS PER-COUNTY PAGES SERVE THE WRONG COUNTY, WITH NO ERROR AND NO 404, AND THAT IS WHY NOTHING IS KEYED ON idCounty ALONE. Swept all 99 ids 2026-08-29: eight serve another county's page outright (Buchanan/Johnson/Linn/Montgomery/Poweshiek get Clarke; Floyd/Iowa/Polk get byte-identical Jefferson pages), and three more serve the right page carrying Jefferson's address anyway (Dallas, Kossuth, Muscatine) -- so the page-level county check is necessary and NOT sufficient, and the address's DOMAIN must also fit the county. Probed here at idCounty=1 (Adair) as a reachability check only.",
    },
    {
        "layer": "county",
        "app_file": "ia-county-officers.json",
        "source_url": "https://www.adaircounty.iowa.gov/",
        "note": "A representative COUNTY OWN SITE (Adair), the other source for treasurer and sheriff e-mail addresses. An address ships only if the officeholder's own name is in its local part (witnessed) or its form is the office's mailbox -- a page window is NOT a witness, and the first version of that probe returned a DEPUTY's personal address in four of the first seven counties tried (Appanoose, Boone, Bremer, Buchanan). Built by ia/scripts/ia_county_officer_email_scraper.py, refreshed weekly by update-ia-county-officers-roster.yml; 65 of 99 treasurers and 87 of 98 sheriffs carry an address as of 2026-08-29.",
    },
    {
        "layer": "county",
        "app_file": "metro-outline.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": "The whole-state outline for the coverage wash, pre-built by ia/scripts/build_metro_outline.py — dissolved from all 99 counties' geometry on the same layer as state-counties.json, not fetched as a separate state polygon (so a future partial-coverage narrowing needs only a smaller METRO_COUNTY_FIPS, the Wisconsin precedent).",
    },
    {
        "layer": "ia-senate",
        "app_file": "ia-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": "State Senate districts pre-built from TIGERweb by ia/scripts/build_legislative_boundaries.py; redraws each decennial cycle (WATCH.md).",
    },
    {
        "layer": "ia-senate",
        "app_file": "ia-senate-members.json",
        "source_url": "https://data.openstates.org/people/current/ia.csv",
        "note": "Senate roster base (name, party) from the Open States current-people export; refreshed weekly by update-ia-legislature-roster.yml.",
    },
    {
        "layer": "ia-senate",
        "app_file": "ia-senate-members.json",
        "source_url": "https://www.legis.iowa.gov/legislators/senate",
        "note": (
            "The Legislature's own senate directory — personIDs feed "
            "ia_legislature_scraper.py's per-legislator profile-page reads "
            "(Capitol phone/e-mail, and the Capitol's own address where "
            "published). Unlike Wisconsin's single listing page, Iowa's "
            "office/phone/email data lives on each member's own profile page, "
            "not this index — see WATCH.md's open question on whether those "
            "profile-page URLs are session-scoped."
        ),
    },
    {
        "layer": "ia-house",
        "app_file": "ia-house-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": "State House districts pre-built from TIGERweb by ia/scripts/build_legislative_boundaries.py; redraws each decennial cycle (WATCH.md).",
    },
    {
        "layer": "ia-house",
        "app_file": "ia-house-members.json",
        "source_url": "https://data.openstates.org/people/current/ia.csv",
        "note": "House roster base (name, party) from the Open States current-people export; refreshed weekly by update-ia-legislature-roster.yml.",
    },
    {
        "layer": "ia-house",
        "app_file": "ia-house-members.json",
        "source_url": "https://www.legis.iowa.gov/legislators/house",
        "note": (
            "The Legislature's own house directory — same personID-driven "
            "profile-page enrichment route as the senate row above."
        ),
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-supervisor-districts.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/CountySupervisorDistricts/FeatureServer/0",
        "note": (
            "The Iowa Legislature's own ArcGIS organization — county supervisor "
            "districts for 95 of 99 counties (the other 3 SF-75-transitioning "
            "counties and Jones's absence are handled separately below); "
            "vintage 2024-01-30 (WATCH.md tracks whether it moves)."
        ),
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-supervisor-districts.json",
        "source_url": "https://services5.arcgis.com/ya62ECiavqTkK0wv/arcgis/rest/services/BlackHawkCoSupervisor_LSAplan1/FeatureServer/0",
        "note": (
            "Black Hawk County's own hosted GIS — its adopted Senate File 75 "
            "plan (5 districts), shipped in place of the state layer's stale "
            "pre-SF75 at-large row for this county alone."
        ),
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-supervisor-districts.json",
        "source_url": "https://www.storycountyiowa.gov/1172/Jurisdictional-Maps",
        "note": (
            "Story County's own Jurisdictional Maps page — where the county "
            "publishes the Auditor's Board of Supervisors District Map. Still "
            "no GIS service (re-swept 2026-09-05), so the three adopted "
            "districts are read off that map itself."
        ),
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-supervisor-districts.json",
        "source_url": ("https://www.storycountyiowa.gov/DocumentCenter/View/17463/"
                       "Board-of-Supervisors-District-Map"),
        "note": (
            "The map itself — the document Story's three districts are DERIVED "
            "from, so it is watched separately from the page that links it. "
            "ia/scripts/build_story_supervisor_districts.py pins its SHA-256 "
            "and refuses to re-derive from a re-print, which is a stricter "
            "check than this reachability probe; this row is here so a link "
            "that goes dead surfaces on the monthly issue rather than only "
            "when an operator next rebuilds."
        ),
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-supervisor-districts.json",
        "source_url": "https://johnsoncountyiowa.gov/supervisor-districts",
        "note": (
            "Johnson County's own site — states its SOS-approved Senate File "
            "75 plan's facts; no GIS service found, so the county ships as "
            "one county-level TRANSITIONING feature pending real district "
            "geometry."
        ),
    },
    {
        "layer": "county-supervisor",
        "app_file": "ia-county-board-directory.json",
        "source_url": "https://www.iowacounties.org/member-resources/county-directory/",
        "note": (
            "Iowa State Association of Counties' member directory — one "
            "detail page per county naming its own official website, read by "
            "ia_county_directory_scraper.py; not a roster of supervisors, "
            "since Iowa publishes no statewide one."
        ),
    },
    {
        "layer": "school-director-district",
        "app_file": "ia-school-director-districts.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/IowaSchoolDirectorDistricts/FeatureServer/0",
        "note": "716 school board director districts inside the 324 shipped school districts, from the Iowa Legislature's own ArcGIS org. LICENCE CC0 — carried on the ITEM (5d6e55f885c54dd282eb17daaca20740), NOT on the service, whose own licenseInfo is null and whose copyrightText is empty; query arcgis.com/sharing/rest/search for the service name before concluding an ArcGIS layer states no terms. 728 features are published: 10 are exact duplicates (Davis County and East Buchanan each publish every row twice) and 2 name districts stale in this layer. At-large boards are read from the publisher's own AT-LARGE label in DIST_NAME. Built by ia/scripts/build_ia_school_director_districts.py; operator-rebuilt, no weekly workflow (this is geometry, not a roster).",
    },
    {
        "layer": "cc-director-district",
        "app_file": "ia-cc-director-districts.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/CC_DD2023/FeatureServer/0",
        "note": "123 community college director districts (Iowa Code 260C.11) inside the 15 merged areas, effective 2023-08-01. THE SERVICE'S NAME IS NOT ITS SLUG: the URL says CC_DD2023, the service calls itself CC_DirectorDistricts_FINAL, and an ArcGIS item search on the slug returns unrelated global items — search the NAME (item b89cf40cef40497e80ae8eb0a6e6d22f, owner education_iowa). Its licence is EMPTY, i.e. terms UNSTATED, which is NOT the CC0 the school-director layer's item carries; the two were checked the same way and differ. Joined to the parent on the numeric key with one asserted Southeastern 8->16 remap. Registered BESPOKE rather than through the polygon factory: the children encode the 2023 merged-area plan and the parent layer the 2026 update, so in ~0.2% of ground the two name different colleges and the card must resolve both and decline rather than contradict its own parent. Built by ia/scripts/build_ia_cc_director_districts.py; operator-rebuilt, no weekly workflow (geometry, not a roster).",
    },
    {
        "layer": "municipality",
        "app_file": "ia-city-contact.json",
        "source_url": "https://iowaleague.org/cities/",
        "note": (
            "The office phone and website of all 939 incorporated cities — CONTACT, NEVER "
            "OFFICEHOLDERS. The Iowa League of Cities publishes a row per city (City / "
            "Organization / County / Population / Website / Phone) and NO COLUMN NAMES A "
            "PERSON, which is why the ia-municipal-officeholders gap stays open beside this. "
            "THIS SOURCE WAS ON FILE AS GATED AND IS NOT: it was recorded as 'a membership "
            "directory with no public officials export' and, elsewhere, as membership-gated; "
            "it answers 200 to an ordinary browser request. ONE FETCH TRAP — without an "
            "Accept header the body arrives TRUNCATED at ~4.8 KB with zero anchors, which "
            "reads like a JS-rendered page and is not one. Joined to TIGERweb's places by "
            "ia/scripts/build_ia_city_contact.py, which refuses to write unless all 939 "
            "places still get a row (one alias: the League's Jewell is TIGER's Jewell "
            "Junction) and the nine non-joining rows keep their measured shape. Refreshed "
            "weekly by update-ia-city-contact-roster.yml."
        ),
    },
    # FIVE ROWS FOR ONE FILE, ONE PER CITY, BECAUSE FIVE PUBLISHERS CAN BREAK
    # INDEPENDENTLY. These are the five Iowa cities whose own council pages a
    # machine can read: measured 2026-09-04 by sweeping all 532 cities that
    # publish a website, of which 16 yielded a roster and 5 cleared every
    # check, against 407 cities publishing no site at all. That is 1.7% of
    # Iowa's 939, which is why ia-municipal-officeholders stays open beside
    # these rows and why nothing here may be described as a statewide roster.
    # All five elect AT LARGE, so they are roster rows on the City card and
    # not a layer -- there is no geometry in this group at all.
    {
        "layer": "municipality",
        "app_file": "ia-city-officials.json",
        "source_url": "https://moraviaiowa.com/city-services/council-mayor/",
        "note": (
            "Moravia's mayor and five council members. THIS IS THE CITY THAT SETTLES THE "
            "ADDRESS QUESTION for the whole group: five of its six officials are published "
            "at consumer webmail, an internet-provider account or a business one of them "
            "runs, and that is not sloppiness — it is what a town of a few hundred people "
            "has, published by the city as the way to reach them. Every address in this "
            "file therefore passes the SAME test build_ia_county_officers.py applies: the "
            "officeholder's own name in the local part, or an office-mailbox form. "
            "Re-tested against the name actually SHIPPED on every build, so a name "
            "correction cannot leave an address witnessed against somebody else. Built by "
            "ia/scripts/ia_city_officials_scraper.py + build_ia_city_officials.py; "
            "refreshed weekly by update-ia-city-officials-roster.yml."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-city-officials.json",
        "source_url": "https://www.norwalk.iowa.gov/government/mayor___city_council.php",
        "note": (
            "Norwalk's mayor and five council members. NORWALK IS THE CONTROL FOR THE "
            "CLAIM THAT A PLATFORM DOES NOT PREDICT A PARSER: it runs the same content "
            "system as Des Moines and Waterloo, whose two pages already need two entirely "
            "different scrapers, and needs a third. That is why each city carries its "
            "naming convention explicitly in the scraper's CITIES table rather than having "
            "it guessed from the host."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-city-officials.json",
        "source_url": "https://cityofpalo.com/council",
        "note": (
            "Palo's mayor and five council members. PALO PUBLISHES NO TELEPHONE NUMBER "
            "FOR ANY OF THEM, which is the whole of the reason this file's phone floor is "
            "18 of 30 rather than 30: the floor measures what the sources publish, not "
            "what would be convenient. Its markup is also what the first sweep MISSED — "
            "the splitter did not break on </span>, so Palo returned nothing and the "
            "statewide yield read 1% instead of 3%."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-city-officials.json",
        "source_url": "https://riversideiowa.gov/government/mayor_and_council/",
        "note": (
            "Riverside's mayor and five council members. ITS OFFICIAL MAIL SITS ON A "
            "DOMAIN THAT IS NOT ITS WEBSITE'S, which is the measured reason the "
            "city-domain heuristic is NOT what decides an address here: comparing a "
            "published address against the host it was found on misclassified Riverside's "
            "own municipal addresses as third-party, in both this city's case and "
            "Waterloo's. The name test is what decides; the domain is not consulted."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-city-officials.json",
        "source_url": "https://www.tiffin-iowa.org/city_government/city_council.php",
        "note": (
            "Tiffin's mayor and five council members. TIFFIN IS THE ONE CITY OF THE FIVE "
            "THAT WRITES 'Role: Name' where the other four write 'Name, Role', and it is "
            "the reason the scraper carries two conventions: the first sweep tested only "
            "the forward one and scored Tiffin as unparseable, which is a measurement of "
            "the sweep and not of the city."
        ),
    },
    # THE COUNTY-PUBLISHED CITY OFFICIALS -- 9 counties, 98 cities, 710 people.
    # This is the route ia-municipal-officeholders recorded as NOT YET PROBED:
    # the county auditors, Iowa's statutory commissioners of elections under
    # Iowa Code 47.2. Twelve counties publish a full city-officials page and
    # ALL TWELVE ARE LISTED HERE, including the three the builder currently refuses
    # -- Sac, Shelby and Winnebago still publish terms that ended in January
    # 2026. They are registered deliberately: their pages are exactly what a
    # monthly human look should re-check, because one of them updating is how
    # this file gains a county, and this validator is the only surface that
    # asks about them at all.
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://boonecounty.iowa.gov/about/elected_officials/city/",
        "note": (
            "Boone County's nine cities. THE PAGE THIS PARSER WAS WRITTEN AGAINST, "
            "and NOT the page that settles the markup for the other ten -- an earlier "
            "version of this note said it was, which is the generalising-from-one error "
            "this project keeps correcting elsewhere. Here the clerk's and the mayor's "
            "role sits in a <b> INSIDE the name's own div, as it does in Crawford, Iowa, "
            "Marion and Winnebago; the other six counties give every role a positionTitle "
            "heading instead. Its 59 mailto hrefs are all EMPTY, where Cerro Gordo's 56, "
            "Shelby's 11 and Marion's 8 are populated. The seat follows a <br/> in that "
            "same div. Read flat, Beaver's clerk becomes a "
            "person called 'City Clerk Sarah Miller'; keyed on the heading alone, the "
            "clerk and the mayor are filed as council members. Boone city is also the "
            "ward case -- five ward seats and two at large, published by the county and "
            "by nobody else."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://cerrogordo.gov/about/elected_officials/city/",
        "note": (
            "Cerro Gordo County's ten cities, Mason City and Clear Lake among them. IT "
            "CARRIES THE MOST SEATS OF THE EIGHT (51 of the 93 shipped) and it is where "
            "the vacancy annotation appears: 'Appointed to Fill Vacancy until Election' "
            "sits in its own div behind an info icon, so a text read folds it into the "
            "person's name. It is a real status and ships as one, never as part of a "
            "name."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://www.crawfordcounty.iowa.gov/about/elected_officials/city/",
        "note": (
            "Crawford County's thirteen cities. THE ADDRESS CASE FOR THE GROUP: its "
            "small towns publish an office mailbox that is the TOWN'S OWN NAME -- "
            "townofarion@, buckgrove@, dowcity@, kironcty@, schleswigclerk@ -- which "
            "the anchored mayor|clerk|city prefix the city and county builders use "
            "reads as private and drops. The office test here is widened for exactly "
            "that class and is still narrow enough to drop Manilla's clerk at "
            "laura@manillaia.com, a city-domain address carrying another first name."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://iowacounty.iowa.gov/about/elected_officials/city/",
        "note": (
            "Iowa County's seven cities. It publishes NO e-mail and NO phone for any "
            "official, which is why this file's contact floors are 100 and 75 rather "
            "than one per person: the floor measures what the sources publish. It is "
            "also half of the North English case -- that city straddles the Iowa/Keokuk "
            "line, and this county publishes its mayor and council while Keokuk "
            "publishes its clerk."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://jacksoncounty.iowa.gov/about/elected_officials/city/",
        "note": (
            "Jackson County's thirteen cities. IT PUBLISHES TWO CITY CLERKS FOR ANDREW, "
            "both named and neither annotated, which is the reason nothing here assumes "
            "one clerk per city -- a builder keyed on a single clerk would silently "
            "drop one real person's name."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://jaspercountyelections.iowa.gov/elected_officials/city/",
        "note": (
            "Jasper County's fourteen cities, Newton among them. THE ONLY ONE OF THE "
            "TWELVE WHOSE PUBLISHER IS NOT THE COUNTY'S MAIN SITE: this is the county's "
            "ELECTION AUTHORITY on its own host, linked from jasperia.org, and it is why "
            "Jasper was nearly recorded unmeasurable. Every host permuted from the "
            "auditor's MAIL domain failed and `jaspercounty.iowa.gov` has no A record at "
            "all -- while `jasperia.org` sat in three of this app's own data files the "
            "whole time. If this row ever goes dark, read jasperia.org for the current "
            "elections host before concluding anything: a county's election authority is "
            "a separate publisher, and the county's own domain is in the shipped data."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://keokukcounty.iowa.gov/about/elected_officials/city/",
        "note": (
            "Keokuk County's seventeen cities, the largest of the eight. Its seats are "
            "mostly TWO-YEAR terms, which is what makes the currency gate an expired- "
            "term test rather than a look for a particular end year: a current two-year "
            "term here ends 2027, the same year a STALE four-year term ends in Sac and "
            "Shelby, so the year alone proves nothing."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://www.marioncountyiowa.gov/about/elected_officials/city/",
        "note": (
            "Marion County's eight cities, Knoxville and Pella among them. NOT to be "
            "confused with the CITY of Marion in Linn County, whose council roster is a "
            "separate and still-open gap (marion-council-roster) -- a different unit of "
            "government with a similar name, and the two must never be joined on it."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://muscatinecountyiowa.gov/about/elected_officials/city/",
        "note": (
            "Muscatine County's eight cities. Like Iowa and Jackson it publishes no "
            "contact detail at all, so what this row really watches is whether the page "
            "keeps naming people: a county that quietly drops to identity-only would "
            "still return HTTP 200 and would fail the builder's floors rather than this "
            "check."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://www.saccountyiowa.gov/about/elected_officials/city/",
        "note": (
            "Sac County -- REFUSED BY THE BUILDER, and registered so a human looks. 29 "
            "of its 61 officials still carry a term that ended in January 2026, and its "
            "four-year seats split across 2025 and 2027 where the eight shipped "
            "counties straddle 2027 and 2029: a page last maintained after the November "
            "2023 city election. If it is updated, it ships on the next weekly run with "
            "nothing to edit anywhere."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://shelbycounty.iowa.gov/about/elected_officials/city/",
        "note": (
            "Shelby County -- REFUSED, 38 of 77 officials on an expired term, the "
            "largest shortfall of the three. Same signature as Sac, and its eleven "
            "cities would be the single biggest addition if the county updates."
        ),
    },
    {
        "layer": "municipality",
        "app_file": "ia-county-city-officials.json",
        "source_url": "https://winnebagocountyiowa.gov/about/elected_officials/city/",
        "note": (
            "Winnebago County -- REFUSED, 22 of 51. It is the one worth re-reading "
            "first if any of the three changes, because it dates the fewest of its "
            "officials at all, so a page that started dating them could pass or fail "
            "for a reason unrelated to being updated."
        ),
    },
    {
        "layer": "iowa-aea",
        "app_file": "ia-aeas.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/CurrentIowaSchoolDistricts/FeatureServer/0",
        "note": (
            "Iowa's nine Area Education Agencies (Iowa Code ch. 273). THE SOURCE URL "
            "HERE IS THE SCHOOL-DISTRICT LAYER ON PURPOSE, and that is the whole build: "
            "the Department of Education DOES publish an AEA polygon, and it is stamped "
            "'for the 2019-2020 school year - updated 3/9/2020', so it supplies the "
            "build's WITNESS and never its geometry. What draws the line is the "
            "Department's own CURRENT district layer, which carries AEA_NUM in band on "
            "all 324 districts; ia/scripts/build_ia_aea.py dissolves the districts this "
            "app already ships by that attribute, joined on DistrictNCESCode = Census "
            "GEOID (324/324, both directions, no alias table). TWO NAMING TRAPS, THE SAME "
            "ONE TWICE: the AEA item is titled IowaAEAs and its layer calls itself "
            "IdoeAeaFY20, and this district service calls itself IdoeSD -- pin the URL "
            "and the item id (AEA witness: 1cfa541b8ebe4bdcbc2f52cdd0977a2b; a second "
            "copy of the same FY20 layer sits on a University of Northern Iowa personal "
            "account). Each agency's name, phone and website come from the AEA system's "
            "own Find My AEA directory, keyed on the same two-digit code the geometry "
            "carries. Identity-only: Iowa Code 273.8 gives a voter no say in any of the "
            "nine directors. Operator-rebuilt, no weekly workflow (geometry, not a "
            "roster) -- but re-run it whenever ia-school-districts.json is rebuilt, "
            "because the two are joined."
        ),
    },
    {
        "layer": "school-site",
        "app_file": "ia-school-sites.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/IowaSchoolBldgs/FeatureServer/0",
        "note": (
            "1,321 public school buildings, pre-built by "
            "ia/scripts/build_ia_school_sites.py from the Iowa Legislature's "
            "own ArcGIS org (paginated past the layer's 1,000-record cap; "
            "pin the slug IowaSchoolBldgs, never its internal title "
            "PublicSchoolBldgs, which names a different, stale service)."
        ),
    },
    {
        "layer": "school-district-unified",
        "app_file": "ia-school-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0",
        "note": (
            "324 unified school districts (325 TIGERweb features, one "
            "dissolved into a neighbor — WATCH.md tracks the reconciliation) "
            "pre-built by ia/scripts/build_ia_school_districts.py."
        ),
    },
    {
        "layer": "school-district-unified",
        "app_file": "ia-school-districts.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/CurrentIowaSchoolDistricts/FeatureServer/0",
        "note": (
            "Iowa Dept. of Education's own current district layer — the "
            "name-set witness the builder checks its dissolve against, never "
            "the geometry source."
        ),
    },
    {
        "layer": "precinct",
        "app_file": "ia-precincts.json",
        "source_url": "https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/Iowa_Precincts/FeatureServer/0",
        "note": (
            "1,660 election precincts across all 99 counties, pre-built by "
            "ia/scripts/build_ia_precincts.py from the Iowa Legislature's "
            "own ArcGIS org (item d394edea208c4003ac1d6bd1ec78532f, pinned "
            "by URL rather than name — two decoy services with confusingly "
            "similar names live on the same and a sibling org). "
            "Visvalingam-simplified with a 2,000-point agreement gate; "
            "polling-place fields are never fetched."
        ),
    },
]

# Live endpoints the app queries at runtime.
ENDPOINTS = [
    {
        "layer": "county-subdivision",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/1/query?where=STATE%3D%2719%27&returnCountOnly=true&f=json",
    },
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2719%27&returnCountOnly=true&f=json",
    },
    # WAS A METADATA PROBE (`MapServer/11?f=json`) AND THAT IS WHY NOTHING
    # CAUGHT #718: the layer's metadata was reachable and always would be,
    # while the app's own enveloped QUERY was answering HTTP 200 with an Esri
    # error envelope and zero features, so the ZIP overlay never drew for
    # weeks.
    #
    # THE ENVELOPE IS SENT AS A JSON OBJECT, WITH KEY NAMES, BECAUSE THE KEY
    # NAMES WERE THE BUG. Iowa's loader was ported carrying METRO_BBOX's
    # {minLng,minLat,maxLng,maxLat} where Esri wants {xmin,ymin,xmax,ymax},
    # and `JSON.stringify` is how the app builds it. Esri also accepts a bare
    # comma form (`-96.69,40.32,...`), and two independent fixes for #718 --
    # this one and the Michigan session's -- reached for different ones; the
    # merge of the two is where it showed. MEASURED 2026-09-04, all three
    # against this same layer:
    #
    #     comma form                 -> {"count":1443}
    #     JSON object, xmin/ymin/... -> {"count":1443}
    #     JSON object, minLng/...    -> {"error":{"code":400}}
    #
    # The comma form has NO KEY NAMES, so it returns the right answer whatever
    # the app's object is keyed on -- it is a valid query that tests a
    # different question, and it would have passed all the way through #718.
    # This row sends the shape the app sends, and `min_count` is what makes
    # the answer count rather than the status code.
    {
        "layer": "zip-code",
        "url": ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11/query?where=1%3D1"
                "&geometry=%7B%22xmin%22%3A-96.69%2C%22ymin%22%3A40.32%2C"
                "%22xmax%22%3A-90.09%2C%22ymax%22%3A43.55%7D"
                "&geometryType=esriGeometryEnvelope&inSR=4326"
                "&spatialRel=esriSpatialRelIntersects&returnCountOnly=true&f=json"),
        "min_count": 1300,  # 1,443 measured 2026-09-04; floor set below it, not at it
    },
    {
        "layer": "post-office",
        "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38?f=json",
    },
    {
        "layer": "police-station",
        "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53?f=json",
    },
    {
        "layer": "fire-station",
        "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51?f=json",
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
            headers={"User-Agent": "District Explorer source validator (+https://districtry.com/ia/)"},
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
                         "out of sync with the app (update ia/scripts/validate_sources.py)"
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
