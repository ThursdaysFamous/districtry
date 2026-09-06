#!/usr/bin/env python3
"""
Post-rewrite sanity gate for the app and its generated data files.

The weekly roster workflows regenerate the officeholder rosters under
data/app/*.json (scripts/build_il_roster.py, build_cpd_roster.py) and open a
PR. Those builders validate their *input* (they refuse an incomplete roster),
but this script is the *output*-side gate: run it after any regeneration and
before opening a PR to confirm the app and its data are still coherent.

Before the P0 externalization these datasets were spliced into object literals
inside index.html and the risk was a mis-anchored regex dropping live code.
Now the builders emit plain JSON with json.dump (no splice, no escaping), so the
checks here are: index.html still parses and carries every layer, it no longer
embeds any dataset inline, and every app-data file is present and well formed.

Checks (all must pass; exits non-zero on the first failure):
  1. The main inline <script> still parses (`node --check`).
  2. registerLayer( appears at least as many times as expected, AND every layer
     id in EXPECT_LAYER_IDS is registered. Most layers register through the
     factories, so a lost factory-registered module would not move the raw
     registerLayer( count — the per-id check catches that (ported from the NYC
     fork per docs/ENGINE_SYNC.md backlog item 8, "port checks, not bytes").
  3. index.html embeds no dataset inline (no `JSON.parse('...')` blobs remain)
     and references each data/app/* file it fetches.
  4. Every expected data/app/*.json exists, parses, and has the right shape.
  5. LAYER_AREA_RANK lists every registered layer id exactly once and nothing
     else — the z-order honesty rule made executable so a layer can never be
     registered but forgotten in the stack (or vice versa).
  6. METRO_EXPLORERS entries are well formed (id/label/https url; bbox, when
     present, is a sane min<max box that does NOT contain this metro's own
     center — a bbox covering home would make the sibling-metro portal easter
     egg fire on every pan). Guards the copy-verbatim config diff every fork
     applies when a new metro launches.
  7. sw.js exactly-one-list invariant: every data/app/*.json on disk is
     cached in exactly one of the service worker's GEOMETRY_URLS / ROSTER_URLS,
     so no data file is ever un-cached or double-listed.
  8. Every county with a per-county dispatch entry is inside the scope mask's
     county list, DERIVED from index.html rather than from a hand-kept list.
     The wash claims "beyond here only the statewide layers answer"; this is
     what stops that claim going stale, as it did for LaSalle, Kankakee, Boone
     and Grundy across two research passes with no gate noticing.

Usage:
    python3 scripts/validate_index.py [path/to/index.html]
"""

import json
import os
import re
import subprocess
import sys
import tempfile

# Machine-readable capability declaration (docs/MECHANIZATION_PLAYBOOK.md,
# Conversion 3). The fleet-status workflow in the CHI repo parses this list
# from every fork's validator and diffs it against CHI's: a capability present
# in a fork but absent here is a reverse-parity WARN — the mechanical form of
# "fork-born validator improvements must land in CHI within one release
# cycle". Shape contract (CHI is the master): a module-level list literal
# named CAPABILITIES of kebab-case strings, one per distinct check this
# validator actually performs. Add an entry when you add a check; never
# declare a capability the code doesn't have.
CAPABILITIES = [
    "engine-fence-lint",        # 0/0c: ENGINE markers well formed, index.html + sw.js
    "metro-explorers-lint",     # 0b: portal list shape/bbox sanity
    "inline-script-parses",     # 1: node --check on the main inline script
    "register-layer-floor",     # 2: raw registerLayer( count floor
    "expect-layer-ids",         # 2: every expected layer id registered
    "layer-area-rank-lint",     # 2b: rank array covers the id set exactly
    "layer-sidebar-rank-lint",  # 2c: sidebar rank covers the id set exactly
    "no-inline-datasets",       # 3: no JSON.parse blobs; data files referenced
    "data-file-shapes",         # 4: every data/app file exists with sane counts
    "sw-exactly-one-list",      # 5: each data file cached in exactly one sw list
    "negative-point-ground-truth",  # 4b: worksheet negative point misses every anchor geometry (born in NYC; back-ported per the ENGINE_SYNC DoD)
    "county-coverage-ring",     # 8: dispatched counties are all inside the scope mask
    "sources-page-coverage",    # 6: the public sources page covers every layer and the app links it
]

# The constants below are GENERATED from metro-worksheet.json (Conversion 2 —
# edit the worksheet, run scripts/generate_metro_files.py). Fork history worth
# keeping by hand: this fork's registerLayer floor arithmetic is 1 function
# definition + 11 direct registerLayer() calls + 5 factory bodies; it was
# lowered 16 -> 15 when police-station/fire-station moved onto the
# registerNearestPointLayer factory (-2 direct calls, +1 body), and raised
# 15 -> 17 when the municipality (2026-07) and township (2026-08-19)
# identity layers became bespoke roster-joined blocks (+1 direct call each).
# ==== GENERATED:BEGIN validator-config ====
# Floor, not a moving target: new layers only raise this; a drop means
# modules were lost.
MIN_REGISTER_LAYER = 14

# Every layer id that must be registered in index.html. Most modules register
# through the factories, so deleting one would NOT lower the raw registerLayer(
# count above — this per-id list is the direct module-loss guard. Emitted in
# LAYER_AREA_RANK order; check 5 keeps the two naming the same set.
EXPECT_LAYER_IDS = [
    "us-house", "ia-judicial-district", "iowa-aea", "ia-senate", "county",
    "ia-house", "county-supervisor", "school-district-unified",
    "school-director-district", "community-college", "cc-director-district",
    "county-subdivision", "municipality", "city-ward", "zip-code", "precinct",
    "police-station", "fire-station", "school-site", "post-office",
]

# file -> (min features, max features) for the boundary layers fetched by the app.
GEOMETRY_FILES = {
    "metro-outline.json": (1, 1),  # The whole-Iowa-state outline for the coverage wash (loadMetroOutline), dissolved from all 99 counties' TIGERweb State_County layer-1 geometry by ia/scripts/build_metro_outline.py (METRO_COUNTY_FIPS = every county; DISPATCH_COUNTY_FIPS empty — no layer is county-keyed yet). Iowa is 2-band coverage — no second, wider region file is needed yet (the WI #523 precedent for when one would be).
    "state-counties.json": (99, 99),  # Every county, pre-built from TIGERweb State_County layer 1.
    "congress-districts.json": (4, 4),  # U.S. House districts, pre-built from TIGERweb Legislative layer 0.
    "ia-senate-districts.json": (50, 50),  # Iowa Senate districts, pre-built by ia/scripts/build_legislative_boundaries.py (2,000-point agreement gate).
    "ia-house-districts.json": (100, 100),  # Iowa House districts, pre-built by ia/scripts/build_legislative_boundaries.py (2,000-point agreement gate).
    "ia-supervisor-districts.json": (272, 272),  # Every county supervisor district across 98 of 99 counties (Jones County absent — a recorded gap), built by ia/scripts/build_ia_supervisor_districts.py: the state's own aggregate for 95 counties, Black Hawk's own hosted GIS (5 real districts), Story's three adopted districts read off the county Auditor's own printed map and resolved to whole Census 2020 blocks by ia/scripts/build_story_supervisor_districts.py (gated on the Legislative Services Agency's published populations matching exactly, district by district), and Johnson still as one county-level TRANSITIONING feature (5,000-in-state-point agreement gate).
    "johnson-county-outline.json": (1, 1),  # Johnson County's own boundary, extracted from state-counties.json by ia/scripts/build_ia_county_outline.py — the Data-gaps panel's map highlight for gap johnson-county-supervisor-districts. Referenced dynamically (built from the gap's county slug at runtime), never by a literal in index.html.
    "jones-county-outline.json": (1, 1),  # Jones County's own boundary, extracted from state-counties.json by ia/scripts/build_ia_county_outline.py — the Data-gaps panel's map highlight for gap jones-county-supervisor. Referenced dynamically (built from the gap's county slug at runtime), never by a literal in index.html.
    "ia-school-districts.json": (324, 324),  # 324 unified school districts, built by ia/scripts/build_ia_school_districts.py: TIGERweb's 325 dissolved (Orient-Macksburg into Nodaway Valley) and witnessed by name against the Dept. of Education's own current layer (2,000-point agreement gate).
    "ia-school-director-districts.json": (716, 716),  # 716 school board director districts, built by ia/scripts/build_ia_school_director_districts.py from the Iowa Legislature's own ArcGIS org. 728 features are published; 10 are EXACT duplicates (Davis County and East Buchanan each publish every row twice) and 2 name districts stale in that layer (LU VERNE, ORIENT-MACKSBURG — the latter independently corroborating this repo's own dissolve into Nodaway Valley). At-large boards are READ from the publisher's own AT-LARGE label in DIST_NAME, never inferred from DISTRICT=0. Keyed <GEOID>-<DISTRICT> because UID is NOT unique — Webster City publishes districts 2 and 3 under one UID. 2,000-point agreement gate at 99.85%, 0 overlaps.
    "ia-cc-director-districts.json": (123, 123),  # 123 community college director districts inside the 15 merged areas, built by ia/scripts/build_ia_cc_director_districts.py. Joined to the parent community-college layer on the NUMERIC key, never the name — the source writes "North Iowa Area" and "Northwest" where the app ships "North Iowa" and "Northwest Iowa" — with ONE asserted remap: this source numbers Southeastern 8 where the app ships 16, the correction build_ia_community_colleges.py already documents, and the builder FAILS if that key stops appearing rather than letting a retired remap mis-key something else. Every college publishes exactly the districts its board seats except Des Moines Area, drawn here as EIGHT districts numbered 1 and 3-9. That is a COUNT disagreement, not a coverage hole: sampling puts the share of each merged area covered by none of its own director districts at 0.00-0.64% across all fifteen, with Des Moines Area at 0.11% — lower than most — and the source's own IDEAL for it is the merged-area population over eight, so it balanced eight deliberately. 2,000-point agreement gate at 99.95%, 0 overlaps.
    "ia-school-sites.json": (1321, 1321),  # 1,321 public school buildings, pre-built by ia/scripts/build_ia_school_sites.py from the Iowa Legislature's own ArcGIS org's IowaSchoolBldgs layer (paginated past its 1,000-record cap).
    "ia-precincts.json": (1660, 1660),  # 1,660 election precincts across all 99 counties, pre-built by ia/scripts/build_ia_precincts.py from the Iowa Legislature's own ArcGIS org's Iowa_Precincts layer (Visvalingam-simplified from ~18MB raw to under 3MB, 2,000-point agreement gate; polling-place fields never fetched).
    "ia-judicial-districts.json": (8, 8),  # 8 judicial election districts, whole-county unions dissolved from state-counties.json by ia/scripts/build_ia_judicial_district.py, per Iowa Code SS602.6107/602.6109 and double-witnessed at build time against the LSAFiscal organization's own published district polygons.
    "ia-community-colleges.json": (15, 15),  # 15 community college merged areas, shipped as published (no dissolve) from the Iowa Legislature's own ArcGIS org by ia/scripts/build_ia_community_colleges.py, witnessed against a second LSA layer on name set, 2020 census population (3,190,369) and director-district count (124).
    "dsm-wards.json": (4, 4),  # The City of Des Moines's four council wards, shipped as published (no dissolve) from the city's own Wards feature service by ia/scripts/build_dsm_wards.py. Gated twice: the wards must still tile the city's own City Boundary layer (0.0070% uncovered in 753 perimeter fragments, largest 3,482 m² — a hole is one large compact part, so the largest fragment is capped as well as the total), and simplification must add no overlap to the source's own 14 m sliver along the ward 1/2 edge. Carries verbatim the City of Des Moines disclaimer its terms of use require, which the card renders.
    "ia-aeas.json": (9, 9),  # Iowa's nine Area Education Agencies (Iowa Code ch. 273), built by ia/scripts/build_ia_aea.py as a DISSOLVE of the shipped school-district fabric by the Department of Education's own in-band AEA_NUM — not from the Department's published AEA polygon, which is stamped for the 2019-2020 school year. Three gates: the NCES join must stay 324/324 with no leftovers either way, the dissolve must not self-overlap, and every one of the 324 districts must still read as its own agency in the published FY20 polygon — the test that asks whether a district has CHANGED agency, which is the only way an AEA line moves.
    "waterloo-wards.json": (5, 5),  # The City of Waterloo's five council wards, shipped as published (no dissolve) from the city's own Wards feature service by ia/scripts/build_waterloo_wards.py. Gated three ways: the wards must still tile the city's own City Limits layer (0.0216% uncovered in 156 fragments), NO uncovered fragment may be COMPACT (Polsby-Popper above 0.30 — a long thin fragment is two outlines digitised apart, a compact one is a hole where the card would answer nothing), and simplification must add no overlap to the source's own zero. Carries no disclaimer: the city states no such condition, and the card's notice row renders only when the key is present.
    "cedar-rapids-wards.json": (5, 5),  # The City of Cedar Rapids' five council DISTRICTS (its own word; Des Moines and Waterloo say ward), shipped as published — no dissolve — by ia/scripts/build_cedar_rapids_wards.py from LINN COUNTY's ElectionsCityCouncilDistrict service. That service is a COUNTY layer holding two cities' districts keyed only by POLITICAL_TWP, an opaque code with no name anywhere in the service, so the build PROVES the code rather than trusting it: the five polygons under '27' must tile Cedar Rapids (area ratio 1.00323, 0.1338% uncovered in 366 fragments) AND the four under '21' — Marion's — must fail to, leaving 99.996% of the city uncovered. That cross-control is the only automated warning available if the county ever reassigns the codes, and without it a swap would put Marion's districts on Cedar Rapids readers' cards under Cedar Rapids labels. City limits come from TIGERweb because Linn publishes no city-limits polygon at all, so this is a cross-publisher tiling comparison and its ceilings are looser than the two same-publisher ones; the compactness floor is 2,000 m² rather than 200 m² for the same reason, with zero fragments above both it and Polsby-Popper 0.30. Carries no disclaimer: the service's copyrightText and serviceDescription are both empty and Linn's page states no condition.
}

# file -> minimum key count (officeholder rosters).
ROSTER_FILES = {
    "congress-roster.json": 4,  # U.S. House roster, refreshed weekly by update-ia-congress-roster.yml.
    "ia-senate-members.json": 45,  # Senate roster from Open States ia.csv + legis.iowa.gov enrichment, refreshed weekly by update-ia-legislature-roster.yml; floor tolerates transient vacancies (50 seats).
    "ia-house-members.json": 93,  # House roster from Open States ia.csv + legis.iowa.gov enrichment, refreshed weekly by update-ia-legislature-roster.yml; floor tolerates transient vacancies (100 seats).
    "ia-county-board-directory.json": 98,  # One row per county covered by ia-supervisor-districts.json: board size read back from the shipped geometry, plus the county's own official page (Iowa State Association of Counties' member directory) for the card's footer link. Built by ia/scripts/build_ia_county_board_directory.py; not a roster of people — Iowa publishes none statewide.
    "ia-county-auditors.json": 99,  # All 99 county auditors: name, party (98 of 99) and office address + phone from the Iowa State Association of County Auditors' own directory, plus an e-mail for all 99 from the Secretary of State's own auditors page (Cloudflare data-cfemail, decoded at scrape time). Where the two directories name different people the county's own site decides, pinned per county in the scraper — 3 measured, resolving 2-1 in the Secretary of State's favour. Built by ia/scripts/ia_county_auditor_scraper.py + build_ia_county_auditors.py, refreshed weekly by update-ia-county-auditor-roster.yml.
    "ia-county-officers.json": 99,  # The other five elected county offices (Iowa Code ch. 331) for all 99 counties: treasurer, recorder, sheriff, county attorney and the board of supervisors — the auditor ships in its own file. Recorder/sheriff/county attorney come from each office's own statewide directory (iowalandrecords.org; ISSDA's sheriff directory PDF; the ICAA roster PDF), the treasurer and the supervisors from ISAC's member portal, which is the only source that exists for those two. Gated hard: a board ships only when the portal's row count is a legal 3 or 5 (Iowa Code 331.201) AND equals the seat count read back from the shipped supervisor-district geometry — 7 counties fail and carry a stated reason instead. An office whose two publishers name different people ships no name at all. Built by ia/scripts/ia_county_officers_scraper.py + ia_county_officer_sources_scraper.py + build_ia_county_officers.py, refreshed weekly by update-ia-county-officers-roster.yml. TREASURER AND SHERIFF E-MAIL ADDRESSES COME FROM THE COUNTIES' OWN SITES (ia/scripts/ia_county_officer_email_scraper.py), because no statewide directory carries them — the ISAC portal has no e-mail column at all. An address ships only if the officeholder's own name is in its local part or its form is the office's mailbox; the builder re-checks a witnessed address against the name it actually ships. The second treasurer source, iowatreasurers.org, SERVES THE WRONG COUNTY on 11 of 99 ids with no error and no 404, so every page must independently identify as its county AND the address's domain must fit it.
    "ia-supervisor-members.json": 12,  # Which supervisor holds each county supervisor district, keyed by 3-digit county FIPS. PLAN 3 COUNTIES ONLY (Iowa Code 331.206): under plan 1 there are no districts and under plan 2 supervisors are elected countywide and merely reside in one, so only under plan 3 does naming a district's supervisor answer something the County card's list does not. No Iowa publisher attaches a district to a supervisor's name — four statewide routes are measured closed — so the district number is recovered from each county's own board page by PROXIMITY to names the shipped roster already carries, reading no markup at all. Gated: districts must be exactly 1..N with no repeats, the people placed must be exactly the people ia-county-officers.json names, and N must equal the shipped geometry's NUMDISTRICTS. A county failing any gate ships nothing and keeps its unkeyed County-card listing. Built by ia/scripts/ia_supervisor_district_scraper.py + build_ia_supervisor_roster.py, refreshed weekly by update-ia-supervisor-roster.yml.
    "ia-judicial-judges.json": 8,  # All 8 districts' benches (371 judges measured 2026-08-28), one entry per district keyed to the geometry's district number. From each district's own "Judges and Magistrates" page at iowacourts.gov (name + each judge's own role/title string, shipped verbatim — no phone/e-mail/address is published for any judge). Built by ia/scripts/ia_judicial_district_scraper.py + build_ia_judicial_district_roster.py, refreshed weekly by update-ia-judicial-district-roster.yml.
    "coverage-gaps.json": 0,  # The Data gaps panel's content; one recorded gap (Jones County, absent from the county-supervisor source layer).
    "dsm-council-members.json": 3,  # All seven seats Des Moines elects — the four ward members keyed by ward plus a citywide block of the mayor and both at-large members — from the city's own council page, refreshed weekly by update-ia-dsm-council-roster.yml. The scrape is scoped by <h2> heading because the page's Appointed Staff and Department Directors sections use IDENTICAL card markup, and it refuses to write if a name appears under both; the four ward members are cross-witnessed against the Wards layer's own in-band names and e-mails before anything is written.
    "ia-city-contact.json": 900,  # The city OFFICE's own phone and website for every one of Iowa's 939 incorporated cities, built by ia/scripts/build_ia_city_contact.py from the Iowa League of Cities' own city table joined to TIGERweb's places. NOT a roster of people — no column of that table names one, which is why the ia-municipal-officeholders gap stays open. The join must be TOTAL (939 of 939 places, one alias: the League's Jewell is TIGER's Jewell Junction) and the nine non-joining League rows must keep their measured shape, so a renamed or dropped city fails the build rather than quietly losing its contact.
    "waterloo-council-members.json": 3,  # All seven seats Waterloo elects to its council — five ward members keyed by ward plus a citywide block of both at-large members — from the city's own council page, refreshed weekly by update-ia-waterloo-council-roster.yml. THE MAYOR IS NOT HERE: he is elected citywide and belongs on the City card by the at-large rule. The page is hand-pasted WYSIWYG HTML with no per-member container, so the scrape keys on each member's own "NAME, SEAT Through MM/DD/YYYY" line; the bio-link anchors that repeat every name WITHOUT a term are the control, and two of them disagree with the authoritative spelling. All five wards and both at-large members are cross-witnessed against the Wards layer's own in-band names before anything is written.
    "cedar-rapids-council-members.json": 3,  # Eight of the nine seats Cedar Rapids elects — five district members keyed by district plus a citywide block of all three at-large members — from the city's own seven seat pages, refreshed weekly by update-ia-cedar-rapids-council-roster.yml. THE MAYOR IS SCRAPED AND NOT SHIPPED: she is elected citywide and belongs on the City card by the at-large rule, and reading her anyway is what keeps that exclusion a decision the pipeline can demonstrate — the scraper demands all nine seats, so a reshaped mayor page fails the run instead of quietly shipping eight. Every member is a structured <h2> heading plus the <p> that follows it, so contact is read from inside that block and nowhere else; the City Clerk's 319-286-5763 sits in the furniture of all seven pages and the scraper refuses if it ever appears inside a member block. NO IN-BAND ROSTER EXISTS to witness against — Linn's layer carries no names — so the witness is the NUMBERING against the shipped boundary, which is weaker than Des Moines's and Waterloo's and is recorded as weaker.
    "ia-city-officials.json": 5,  # The elected officials of the FIVE Iowa cities whose own pages a machine can read — a mayor and five at-large council members apiece, 30 people with an e-mail each. NOT a statewide roster and never to be described as one: a sweep of all 532 Iowa cities that publish a website found 16 with a readable roster and 5 that cleared every check, against 407 cities publishing no site at all, so `ia-municipal-officeholders` stays open for the other 833 -- these five, the three cities that elect by ward, and the 98 named by their own COUNTY in ia-county-city-officials.json are the 106 that name anybody -- and the card says so on every one of them. All five are AT-LARGE, so they are roster rows on the City card and not a layer. Every address is re-tested each build against the name actually shipped by the same rule build_ia_county_officers.py applies — the officeholder's own name in the local part, or an office mailbox — because six of the 30 sit on consumer, provider or business domains that these small cities publish as official contact. Built by ia/scripts/ia_city_officials_scraper.py + build_ia_city_officials.py, refreshed weekly by update-ia-city-officials-roster.yml.
    "ia-county-city-officials.json": 92,  # The mayors, clerks and council members NINE IOWA COUNTIES publish for the 98 cities inside them — 710 officials, every one of the 98 naming a mayor, 85 naming a clerk, and 104 carrying the ward or at-large seat their own county states, which no other Iowa source pairs with a name at all. THE 710 ARE NOT ALL COUNCIL: 487 council members, 98 mayors and 86 clerk rows across 85 cities, plus 39 who are none of those — 12 city administrators, 10 city attorneys, 5 park commissioners, 5 park board, 5 library trustees, a city manager and an administrative secretary — shipped under the role their own county publishes, which is why the card's block is headed CITY OFFICIALS rather than claiming an election. TWO MARKUP FACTS ARE PER-COUNTY AND NOT UNIVERSAL, and both were first written here with JASPER ON THE WRONG SIDE OF EACH: SIX of the twelve put the clerk's and mayor's role in a <b> inside the name's own div (Boone, Crawford, Iowa, Jasper, Marion, Winnebago) while the other SIX give every role a positionTitle heading — and the <b> is an ADDITION rather than an alternative, since all six still take City Council from a heading, so what it carries is the NON-COUNCIL roles, Jasper's four being the widest vocabulary of the twelve and the sole source of all ten City Attorney rows; and the mailto href is EMPTY in Boone, Crawford and Jasper (110 hrefs, none populated), POPULATED in Cerro Gordo, Shelby and Marion, and absent in the other six — the scraper reads the link TEXT and the role structurally, so it needs neither to be universal. This is the route `ia-municipal-officeholders`'s own blocker had recorded as NOT YET PROBED: the county auditors, Iowa's statutory commissioners of elections under Iowa Code 47.2. Twelve counties publish such a page and three are REFUSED by a dated gate rather than by a hand list — Sac, Shelby and Winnebago still publish terms that ended in January 2026, and all three show their four-year seats split across 2025 and 2027 where the other nine straddle 2027 and 2029, the signature of a page last maintained after the November 2023 city election — so a county that updates its page ships on the next weekly run with nothing to edit here, and one that goes stale drops out the same way. NOT a statewide roster: 833 of Iowa's 939 cities still name nobody and the City card says so on every one of them. Built by ia/scripts/ia_county_city_officials_scraper.py + build_ia_county_city_officials.py, refreshed weekly by update-ia-county-city-officials-roster.yml.
    "ia-county-board-chairs.json": 30,  # Which supervisor chairs each county board — 35 of Iowa's 99 counties, each from its own board-of-supervisors page. No statewide publisher records it: ISAC's directory, which is this app's source for the supervisors themselves, carries no chair field at all, and the chair is chosen by the board's own vote each January, so a one-time answer from 99 offices would be stale within the year — which is why this is a weekly re-scrape and not an ask. The `ia-board-chair` gap record had closed this as impossible on the ground that nothing could separate a real name from furniture like `Contact Information` or `Term Expires`; the separator was in the repo already, because a name that is not on that county's own supervisor roster is not a chair. Roster membership alone is NOT enough and an earlier attempt shipped a vice-chairman on it, so the pairing is structural: the role and the name must share the smallest DOM element that holds no OTHER supervisor, a role standing BEFORE a name is refused when a person-shaped phrase stands before it, and the two must sit within 30 characters (widest true pairing measured 28, tightest false one 84). Two further refusals came out of review: a chair QUALIFIED by another body is refused on a window cut backwards from the parent, and a pairing whose own term dates have expired is refused — the latter is why 35 ship rather than 36, Mahaska's page dating itself two board terms ago. Boards-and-commissions pages are excluded outright — a supervisor's chairmanship of some other body is not evidence about the county board, which is how Des Moines County produced a wrong answer that all three structural tests passed. Of 35 shipped, 19 were checkable against the county's own minutes and 19 agreed, none disagreed. The card joins BY NAME so a chair who leaves the board stops rendering rather than sliding onto a successor. Built by ia/scripts/ia_county_chair_scraper.py + build_ia_county_chair.py, refreshed weekly by update-ia-county-chair-roster.yml.
}

# Files the app references DYNAMICALLY — the URL is built from a slug at
# runtime (the gaps panel's <slug>-county-outline.json contract), so no
# literal appears in index.html. Exempt from the reference check only;
# existence, shape and the negative-point test still apply.
DYNAMIC_REFERENCE = frozenset({
    "johnson-county-outline.json",
    "jones-county-outline.json",
})
# ==== GENERATED:END validator-config ====


def fail(msg):
    print("validate_index: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


# ENGINE fence lint (docs/ENGINE_SYNC.md): the cross-fork byte comparison is
# scripts/check_engine_parity.py's job; this merge gate only guards fence
# structure so a bad edit can't silently break the parity check itself.
ENGINE_MARKER_RE = re.compile(
    r"^[ \t]*(?:/\*|<!--)[ \t]*==== ENGINE:(BEGIN|END) ([a-z0-9][a-z0-9-]*) ====[ \t]*(?:\*/|-->)[ \t]*$"
)


def check_engine_markers(html):
    open_name = None
    names = set()
    for lineno, line in enumerate(html.splitlines(), 1):
        m = ENGINE_MARKER_RE.match(line)
        if not m:
            continue
        kind, name = m.groups()
        if kind == "BEGIN":
            if open_name is not None:
                fail("line %d: ENGINE:BEGIN %s while %s is still open" % (lineno, name, open_name))
            if name in names:
                fail("line %d: duplicate ENGINE block name %r" % (lineno, name))
            open_name = name
            names.add(name)
        else:
            if name != open_name:
                fail("line %d: ENGINE:END %s does not match open block %r" % (lineno, name, open_name))
            open_name = None
    if open_name is not None:
        fail("ENGINE block %s is never closed" % open_name)
    if not names:
        fail("no ENGINE blocks found — fences were deleted? (docs/ENGINE_SYNC.md)")
    return len(names)


def _split_object_literals(block):
    """Split the body of a JS array literal into its top-level {...} entries
    (depth-tracked, so nested objects like bbox stay inside their entry)."""
    entries, depth, start = [], 0, None
    for i, ch in enumerate(block):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                entries.append(block[start:i + 1])
                start = None
    return entries


def check_metro_explorers(html):
    """Lint the METRO_EXPLORERS config list (the copy-verbatim cross-fork
    diff applied whenever a new metro launches — the likeliest place for a
    future typo to land). bbox drives the sibling-metro portal easter egg."""
    m = re.search(r'var THIS_METRO = "([a-z0-9-]+)"', html)
    if not m:
        fail("could not find THIS_METRO in the METRO config block")
    this_metro = m.group(1)
    m = re.search(r"var METRO_CENTER = \[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", html)
    if not m:
        fail("could not find METRO_CENTER in the METRO config block")
    center_lat, center_lng = float(m.group(1)), float(m.group(2))
    m = re.search(r"var METRO_EXPLORERS = \[(.*?)\n\s*\];", html, re.DOTALL)
    if not m:
        fail("could not find the METRO_EXPLORERS list in the METRO config block")
    entries = _split_object_literals(m.group(1))
    if not entries:
        fail("METRO_EXPLORERS is empty")

    ids = []
    for entry in entries:
        eid = re.search(r'\bid:\s*"([^"]*)"', entry)
        label = re.search(r'\blabel:\s*"([^"]*)"', entry)
        url = re.search(r'\burl:\s*"([^"]*)"', entry)
        if not (eid and eid.group(1)):
            fail("METRO_EXPLORERS entry missing id: %s" % entry.strip()[:80])
        if not (label and label.group(1)):
            fail("METRO_EXPLORERS[%s] missing label" % eid.group(1))
        if not (url and url.group(1).startswith("https://")):
            fail("METRO_EXPLORERS[%s] url missing or not https" % eid.group(1))
        ids.append(eid.group(1))

        bm = re.search(r"\bbbox:\s*\{([^}]*)\}", entry)
        if not bm:
            continue  # no bbox = the metro opts out of the portal; allowed
        vals = dict(re.findall(r"(minLng|minLat|maxLng|maxLat):\s*(-?[\d.]+)", bm.group(1)))
        if sorted(vals) != ["maxLat", "maxLng", "minLat", "minLng"]:
            fail("METRO_EXPLORERS[%s] bbox is missing fields (need minLng/minLat/maxLng/maxLat)" % eid.group(1))
        b = {k: float(v) for k, v in vals.items()}
        if not (b["minLat"] < b["maxLat"] and b["minLng"] < b["maxLng"]):
            fail("METRO_EXPLORERS[%s] bbox is inverted (min must be < max on both axes)" % eid.group(1))
        if eid.group(1) != this_metro and (
            b["minLat"] <= center_lat <= b["maxLat"] and b["minLng"] <= center_lng <= b["maxLng"]
        ):
            fail(
                "METRO_EXPLORERS[%s] bbox contains this metro's own center (%s, %s) — "
                "the metro-portal easter egg would fire on every pan at home" % (eid.group(1), center_lat, center_lng)
            )

    if len(set(ids)) != len(ids):
        fail("METRO_EXPLORERS has duplicate ids: %s" % ids)
    if this_metro not in ids:
        fail('METRO_EXPLORERS has no entry for THIS_METRO ("%s")' % this_metro)
    return len(ids)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    if not os.path.exists(path):
        fail("no such file: " + path)
    html = open(path).read()
    repo_root = os.path.dirname(os.path.abspath(path))
    app_dir = os.path.join(repo_root, "data", "app")

    # 0. ENGINE fences are structurally sound (docs/ENGINE_SYNC.md)
    check_engine_markers(html)

    # 0b. METRO_EXPLORERS config list is sane (metro-portal easter egg)
    n_metros = check_metro_explorers(html)

    # 0c. sw.js ENGINE fences are structurally sound too (the service worker's
    # handler logic is shared engine; docs/ENGINE_SYNC.md). Absence is reported
    # by check_sw_lists below with a clearer message.
    sw_path = os.path.join(repo_root, "sw.js")
    if os.path.exists(sw_path):
        check_engine_markers(open(sw_path).read())

    # 1. main inline script parses
    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    if not scripts:
        fail("no inline <script> blocks found")
    main_script = max(scripts, key=len)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
        tf.write(main_script)
        js_path = tf.name
    try:
        proc = subprocess.run(["node", "--check", js_path], capture_output=True, text=True)
    finally:
        os.unlink(js_path)
    if proc.returncode != 0:
        fail("inline script failed `node --check`:\n" + (proc.stderr or proc.stdout))

    # 2. no modules lost — engine floor plus every expected layer id present
    n = len(re.findall(r"registerLayer\(", html))
    if n < MIN_REGISTER_LAYER:
        fail("registerLayer( count %d < expected floor %d — a module was likely deleted" % (n, MIN_REGISTER_LAYER))
    for lid in EXPECT_LAYER_IDS:
        if ('id: "%s"' % lid) not in html:
            fail('layer id "%s" is not registered in index.html' % lid)

    # 2b. LAYER_AREA_RANK covers every registered id exactly once, and nothing
    # else (no "stub", no dropped layer). This is the z-order pass made
    # executable: reorderActiveLayers() walks this list, so a registered layer
    # missing here never gets restacked, and a stale id here is a silent no-op
    # that hides a rename.
    m = re.search(r"var LAYER_AREA_RANK = \[(.*?)\];", html, re.DOTALL)
    if not m:
        fail("LAYER_AREA_RANK array not found in index.html")
    rank = re.findall(r'"([a-z0-9-]+)"', m.group(1))
    dupes = sorted(set(x for x in rank if rank.count(x) > 1))
    if dupes:
        fail("LAYER_AREA_RANK lists these ids more than once: %s" % ", ".join(dupes))
    expected = set(EXPECT_LAYER_IDS)
    got = set(rank)
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    if missing:
        fail("LAYER_AREA_RANK is missing registered layer id(s): %s" % ", ".join(missing))
    if extra:
        fail("LAYER_AREA_RANK has id(s) not in the registered set: %s" % ", ".join(extra))

    # 2c. LAYER_SIDEBAR_RANK covers every registered id exactly once, and
    # nothing else — same contract as 2b for the sidebar display order
    # (docs/EXPANSION_GUIDE.md Part 4 "Sidebar placement standard"): the boot
    # sort deliberately sinks an unranked id to the end instead of throwing,
    # so this check is the only place a rank/registry drift fails loudly.
    m = re.search(r"var LAYER_SIDEBAR_RANK = \[(.*?)\];", html, re.DOTALL)
    if not m:
        fail("LAYER_SIDEBAR_RANK array not found in index.html")
    srank = re.findall(r'"([a-z0-9-]+)"', m.group(1))
    dupes = sorted(set(x for x in srank if srank.count(x) > 1))
    if dupes:
        fail("LAYER_SIDEBAR_RANK lists these ids more than once: %s" % ", ".join(dupes))
    got = set(srank)
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    if missing:
        fail("LAYER_SIDEBAR_RANK is missing registered layer id(s): %s" % ", ".join(missing))
    if extra:
        fail("LAYER_SIDEBAR_RANK has id(s) not in the registered set: %s" % ", ".join(extra))

    # 3. nothing embedded inline anymore, and every data file is referenced
    blobs = re.findall(r"var (\w+) = JSON\.parse\('", html)
    if blobs:
        fail("dataset(s) still embedded inline (should be in data/app/): %s" % blobs)
    for fname in list(GEOMETRY_FILES) + list(ROSTER_FILES):
        if fname in DYNAMIC_REFERENCE:
            continue  # URL built from a slug at runtime — see the generated set
        if ("data/app/" + fname) not in html:
            fail("index.html does not reference data/app/%s" % fname)

    # 4. every app-data file exists, parses, and has the right shape
    for fname, (lo, hi) in GEOMETRY_FILES.items():
        fpath = os.path.join(app_dir, fname)
        if not os.path.exists(fpath):
            fail("missing app-data file: data/app/%s" % fname)
        try:
            gj = json.load(open(fpath))
        except Exception as e:
            fail("data/app/%s does not parse as JSON: %s" % (fname, e))
        feats = gj.get("features") if isinstance(gj, dict) else None
        if gj.get("type") != "FeatureCollection" or not isinstance(feats, list):
            fail("data/app/%s is not a GeoJSON FeatureCollection" % fname)
        if not (lo <= len(feats) <= hi):
            fail("data/app/%s has %d features, expected %d-%d" % (fname, len(feats), lo, hi))

    for fname, min_keys in ROSTER_FILES.items():
        fpath = os.path.join(app_dir, fname)
        if not os.path.exists(fpath):
            fail("missing app-data file: data/app/%s" % fname)
        try:
            roster = json.load(open(fpath))
        except Exception as e:
            fail("data/app/%s does not parse as JSON: %s" % (fname, e))
        if not isinstance(roster, dict):
            fail("data/app/%s is not a JSON object" % fname)
        if len(roster) < min_keys:
            fail("data/app/%s has %d entries, expected at least %d" % (fname, len(roster), min_keys))

    # 5. sw.js exactly-one-list invariant: every data/app/*.json on disk
    # must be cached in exactly one of GEOMETRY_URLS (cache-first) or ROSTER_URLS
    # (network-first). A boundary served network-first would be a needless fetch;
    # a roster served cache-first could name a stale officeholder — the cardinal
    # sin here. An un-listed file silently loses offline support.
    # 4b. negative ground-truth point misses every anchor geometry
    check_negative_point(repo_root, app_dir)

    check_sw_lists(repo_root, app_dir)

    # 5. every county the app dispatches a layer on is inside the coverage ring
    n_counties = check_county_coverage_list(html, repo_root)

    # 5b. and the ring itself, which the check above cannot see here
    n_ring = check_coverage_ring_tracks_counties(repo_root, app_dir)

    # 6. the public sources page, if this fork ships one, still accounts for
    # every layer and is still reachable from the app.
    n_sourced = check_sources_page(html, repo_root)

    print(
        "validate_index: OK — inline script parses, %d registerLayer( calls, "
        "LAYER_AREA_RANK + LAYER_SIDEBAR_RANK cover all %d ids, no inline datasets, %d well-formed "
        "METRO_EXPLORERS entries, all data/app files present and cached in "
        "exactly one sw.js list, %d dispatched counties all inside the coverage "
        "ring whose %d counties match the shipped county-officers roster exactly%s"
        % (n, len(EXPECT_LAYER_IDS), n_metros, n_counties, n_ring,
           "" if n_sourced is None else
           ", sources page linked and covering all %d layers" % n_sourced)
    )


SOURCES_PAGE = "sources.html"


def check_sources_page(html, repo_root):
    """The public sources page accounts for every registered layer, and the app
    still links to it. Returns the number of layers covered, or None if this
    fork ships no such page.

    Two failure modes, neither of which any other gate sees. A layer that ships
    without a matrix row leaves a reader reading the page as complete when it
    isn't — silence about a source reads as 'there is no source'. And a page
    nothing links to is a page nobody reads: the credits row that used to sit
    in the footer was self-evidently reachable, a separate page is only as
    reachable as its pointer. The row-per-layer content itself is generated
    from the same worksheet list as EXPECT_LAYER_IDS
    (scripts/generate_metro_files.py), so this checks the OUTCOME rather than
    trusting that the generator ran."""
    path = os.path.join(repo_root, SOURCES_PAGE)
    if not os.path.exists(path):
        return None
    page = open(path, encoding="utf-8").read()
    missing = [lid for lid in EXPECT_LAYER_IDS if ('id="layer-%s"' % lid) not in page]
    if missing:
        fail("%s has no matrix row for %d layer(s): %s — regenerate with "
             "scripts/generate_metro_files.py after adding the layer's source "
             "block to metro-worksheet.json"
             % (SOURCES_PAGE, len(missing), ", ".join(missing)))
    if SOURCES_PAGE not in html:
        fail("index.html no longer links to %s — the page ships but nothing in "
             "the app points a reader at it" % SOURCES_PAGE)
    return len(EXPECT_LAYER_IDS)


def _point_in_geometry(lng, lat, geom):
    """Stdlib ray-casting point-in-polygon over a GeoJSON (Multi)Polygon."""
    def ring_hit(ring):
        inside = False
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return any(ring_hit(p[0]) and not any(ring_hit(h) for h in p[1:]) for p in polys)


def check_negative_point(repo_root, app_dir):
    """4b. The worksheet's negative ground-truth point must miss EVERY feature
    of every anchor geometry file — the honest no-district state the smoke
    test asserts is only meaningful if the committed geometries agree. Catches
    a re-simplified boundary quietly swallowing the negative point."""
    ws_path = os.path.join(repo_root, "metro-worksheet.json")
    if not os.path.exists(ws_path):
        fail("metro-worksheet.json not found — negative-point ground truth needs it")
    ws = json.load(open(ws_path))
    neg = ws["negative_point"]
    lng, lat = neg["lng"], neg["lat"]
    for fname in GEOMETRY_FILES:
        gj = json.load(open(os.path.join(app_dir, fname)))
        for feat in gj.get("features", []):
            geom = feat.get("geometry") or {}
            if geom.get("type") not in ("Polygon", "MultiPolygon"):
                # amenity-point files (school-sites, library-sites) ride the
                # geometry list for their cache policy, but a point cannot
                # contain the negative point — nothing to assert here
                continue
            if _point_in_geometry(lng, lat, geom):
                fail(
                    "negative point %.5f,%.5f is INSIDE a feature of data/app/%s (%r) — "
                    "it must miss every anchor geometry; pick a new negative point in the "
                    "worksheet or check the geometry build" % (lat, lng, fname, feat.get("properties"))
                )


def _sw_url_list(sw, name):
    """Extract the ./data/app/*.json basenames from a `const NAME = [...]` array."""
    m = re.search(r"const %s = \[(.*?)\];" % name, sw, re.DOTALL)
    if not m:
        fail("sw.js: %s array not found" % name)
    return re.findall(r'\./data/app/([A-Za-z0-9._-]+\.json)', m.group(1))


def check_sw_lists(repo_root, app_dir):
    sw_path = os.path.join(repo_root, "sw.js")
    if not os.path.exists(sw_path):
        fail("sw.js not found next to index.html")
    sw = open(sw_path).read()
    geometry = _sw_url_list(sw, "GEOMETRY_URLS")
    roster = _sw_url_list(sw, "ROSTER_URLS")

    # No file appears in both lists.
    both = sorted(set(geometry) & set(roster))
    if both:
        fail("sw.js: file(s) in BOTH GEOMETRY_URLS and ROSTER_URLS: %s" % ", ".join(both))

    listed = geometry + roster
    dupes = sorted(set(x for x in listed if listed.count(x) > 1))
    if dupes:
        fail("sw.js: file(s) listed more than once: %s" % ", ".join(dupes))

    # Every listed file exists on disk.
    for fname in listed:
        if not os.path.exists(os.path.join(app_dir, fname)):
            fail("sw.js caches data/app/%s but the file does not exist" % fname)

    # Every data/app/*.json on disk is cached in exactly one list.
    on_disk = set(f for f in os.listdir(app_dir) if f.endswith(".json"))
    uncached = sorted(on_disk - set(listed))
    if uncached:
        fail("data/app file(s) not cached in any sw.js list: %s" % ", ".join(uncached))


# Layers that dispatch by MUNICIPALITY rather than by county. Their entry keys
# are place names, so they are exempt from the county check below. Listed, not
# inferred: a new municipality-keyed concept should have to say so here rather
# than quietly opting itself out of the guard.
MUNICIPALITY_KEYED_LAYERS = {"ward", "city-ward"}


# The distinctive word each county-dispatched layer's loader names carry. Used
# to catch an entry pasted into the wrong table: a loader that reads as another
# concept, and not as its own, is misfiled. Keys absent here are not checked.
LAYER_CONCEPT_TOKEN = {
    "county-board": "Board",
    "county-precinct": "Precinct",
    "fire-district": "Fire",
    "library-district": "Library",
    "park-district": "Park",
    "judicial-subcircuit": "Subcircuit",
}


def _literals_from(path, names):
    """Read module-level literals without importing the module.

    build_metro_outline.py imports `requests`, which is not installed in the
    smoke-test workflow where this gate runs — and executing a builder to read
    two constants would be the wrong trade anyway. ast parses, never runs.
    """
    import ast
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                try:
                    found[target.id] = ast.literal_eval(node.value)
                except ValueError:
                    pass
    missing = sorted(set(names) - set(found))
    if missing:
        fail("%s no longer defines %s — the county-list check cannot run"
             % (os.path.basename(path), ", ".join(missing)))
    return found


def check_county_coverage_list(html, repo_root):
    """Every county the app dispatches a layer on must be inside the scope mask.

    VACUOUS IN THIS INSTANCE, AND THAT IS WHY THE CHECK BELOW EXISTS. Iowa
    registers no registerCountyLayer dispatch entries at all — every county
    concept is one statewide layer — so this walks an empty set and returns 0
    on every run. It is kept because the shape is shared with the reference
    instance and a future dispatch entry must be covered from its first day,
    not because it is currently measuring anything.

    THE BUG IT EXISTS FOR, in an instance that does dispatch: the mask's county
    list was previously guarded only by the outline builder's OUTSIDE anchors,
    which catch a county only if somebody had already thought to name it. Four
    of the reference instance's counties therefore shipped layers and stayed
    greyed out for two research passes — the wash telling residents "beyond
    here only the statewide layers answer" while five of their layers answered.
    Nothing failed, because nothing was comparing the list against what the app
    actually registers. In Iowa that comparison is
    check_coverage_ring_tracks_counties(), below.

    So this derives the answer instead of trusting a list: it reads the county
    keys out of index.html's own dispatch tables and requires each one to be in
    METRO_COUNTY_FIPS. An unrecognised key fails too — a new county that nobody
    added to DISPATCH_COUNTY_FIPS is exactly the case that used to slip through.

    IT ALSO CHECKS THE REVERSE, which for a long time nothing did: a
    DISPATCH_COUNTY_FIPS row with no dispatch entry behind it. That gap was
    found on 2026-08-02 while shipping the at-large tier (Pike, Brown, Calhoun,
    Putnam) — counties served entirely through the COUNTY card, with no dispatch
    entry of any kind. The expansion guide had said to add such a county to
    DISPATCH_COUNTY_FIPS "if any other layer answers there", and adding one
    anyway passed every gate silently, because this function only ever looked
    from index.html outward. A stale row is not cosmetic: DISPATCH_COUNTY_FIPS
    is what build_county_outline.py cross-checks FIPS against and what the
    guidebook and CLAUDE.md quote as the count of dispatched counties, so a
    county listed there but dispatching nothing makes all three quietly wrong.
    An at-large county belongs in METRO_COUNTY_FIPS only.
    """
    outline_py = os.path.join(repo_root, "scripts", "build_metro_outline.py")
    if not os.path.exists(outline_py):
        fail("scripts/build_metro_outline.py not found — the county-list check "
             "cannot run; it is the source of the coverage ring")
    consts = _literals_from(outline_py, ("DISPATCH_COUNTY_FIPS", "METRO_COUNTY_FIPS"))
    slug_fips = consts["DISPATCH_COUNTY_FIPS"]
    in_ring = set(consts["METRO_COUNTY_FIPS"])

    # Split the script at every top-level register*() call so each dispatch
    # table is read within its own call and cannot absorb a neighbour's keys.
    chunks = re.split(r"\n  (register[A-Za-z]*)\(\{", html)
    unknown, outside, misfiled = [], [], []
    seen_counties = set()
    for i in range(1, len(chunks) - 1, 2):
        if chunks[i] != "registerCountyLayer":
            continue
        body = chunks[i + 1]
        layer_id = re.search(r'id:\s*"([a-z-]+)"', body)
        if not layer_id or layer_id.group(1) in MUNICIPALITY_KEYED_LAYERS:
            continue
        lid = layer_id.group(1)
        keys_here = re.findall(r'key:\s*"([a-z-]+)"', body)
        dupes = sorted({k for k in keys_here if keys_here.count(k) > 1})
        if dupes:
            fail("%s registers the same county key twice: %s. registerCountyLayer's "
                 "byKey lookup is LAST-WINS and render/cardIdentifier/primaryLink "
                 "all dispatch through it, so the duplicate silently re-points the "
                 "first entry's card at the second entry's renderer — no gate "
                 "notices, because the layer still registers and still queries."
                 % (lid, ", ".join(dupes)))
        # An entry whose loader belongs to a DIFFERENT concept is an entry pasted
        # into the wrong table. That shipped twice (2026-08-03/04): precinct
        # entries for Stephenson and Macon landed in county-board, which gave
        # Macon a board card it must not have and broke Stephenson's. The keys
        # were legal and unique, so nothing above caught it.
        own = LAYER_CONCEPT_TOKEN.get(lid)
        if own:
            others = {t for k, t in LAYER_CONCEPT_TOKEN.items() if t != own}
            for ekey, loader in re.findall(
                    r'key:\s*"([a-z-]+)",\s*\n\s*coverage:[^\n]*\n\s*'
                    r'(?:loadGeometry|loader):\s*(\w+)', body):
                foreign = sorted(t for t in others if t in loader)
                if foreign and own not in loader:
                    misfiled.append("%s entry '%s' uses %s (reads as %s, not %s)"
                                    % (lid, ekey, loader, "/".join(foreign), own))
        for key in keys_here:
            if key not in slug_fips:
                unknown.append("%s: %s" % (lid, key))
                continue
            seen_counties.add(key)
            if slug_fips[key] not in in_ring:
                outside.append("%s (%s)" % (key, lid))

    if misfiled:
        fail("dispatch entr%s sitting in the wrong layer's table: %s. Move the "
             "entry into the registerCountyLayer call for its own concept."
             % ("ies are" if len(misfiled) > 1 else "y is", "; ".join(sorted(misfiled))))
    if unknown:
        fail("dispatch entr%s for a county with no DISPATCH_COUNTY_FIPS entry: %s. "
             "Add the county (slug -> Census FIPS) to scripts/build_metro_outline.py, "
             "or list its layer in MUNICIPALITY_KEYED_LAYERS if it dispatches by "
             "place rather than county."
             % ("ies" if len(unknown) > 1 else "y", ", ".join(sorted(set(unknown)))))
    if outside:
        fail("county/counties serve layers but are NOT in METRO_COUNTY_FIPS, so the "
             "out-of-scope wash greys them out while their cards answer: %s. Add "
             "them to scripts/build_metro_outline.py and rebuild "
             "data/app/metro-outline.json."
             % ", ".join(sorted(set(outside))))

    # The reverse direction (see the docstring): listed as dispatched, but
    # dispatching nothing.
    undispatched = sorted(set(slug_fips) - seen_counties)
    if undispatched:
        fail("county/counties in DISPATCH_COUNTY_FIPS that register NO dispatch "
             "entry in index.html: %s. That list is the count of dispatched "
             "counties the docs quote and the FIPS table build_county_outline.py "
             "cross-checks, so a row with nothing behind it makes both wrong. If "
             "the county is served only through the COUNTY card (an AT-LARGE "
             "board — EXPANSION_GUIDE §3.5.1), remove it from DISPATCH_COUNTY_FIPS "
             "and leave it in METRO_COUNTY_FIPS. Otherwise its dispatch entry was "
             "dropped — restore it."
             % ", ".join(undispatched))
    return len(seen_counties)


def check_coverage_ring_tracks_counties(repo_root, app_dir):
    """METRO_COUNTY_FIPS must be exactly the counties this app answers for.

    THE CHECK ABOVE CANNOT SEE THIS INSTANCE. It walks registerCountyLayer
    dispatch entries, and Iowa has none — every county concept is ONE statewide
    layer, so DISPATCH_COUNTY_FIPS is empty by design, that loop never
    executes, and it reported "0 dispatched counties all inside the coverage
    ring" on every run: a vacuum printed as a result. Wisconsin, the same
    shape, closed this after seven counties sat greyed out for two days with
    every gate in the repo green; Iowa carried the identical hole and, until
    2026-09-02, an unedited copy of the reference instance's docstring
    describing Illinois counties.

    WHICH ROSTER IS THE COMPARAND MATTERS, and the obvious one is wrong.
    Iowa's wash claims where its STATEWIDE layers answer, and they answer for
    all 99 counties; ia-supervisor-members.json covers 17, because naming
    sitting supervisors is a known roster gap rather than a coverage claim.
    Comparing the ring against THAT would fail a correct instance and read as
    82 counties wrongly washed. The county officers layer is the one that must
    answer everywhere the wash reaches, so it is what the ring is held to.
    """
    outline_py = os.path.join(repo_root, "scripts", "build_metro_outline.py")
    roster_path = os.path.join(app_dir, "ia-county-officers.json")
    for path in (outline_py, roster_path):
        if not os.path.exists(path):
            fail("%s not found — the coverage-ring/county check cannot run"
                 % os.path.relpath(path, repo_root))
            return 0

    in_ring = set(_literals_from(outline_py, ("METRO_COUNTY_FIPS",))["METRO_COUNTY_FIPS"])
    with open(roster_path, encoding="utf-8") as f:
        roster = json.load(f)
    # The roster is keyed by 5-digit GEOID ("19001"), the ring by the 3-digit
    # county code ("001"). Slicing rather than stripping a literal "19" so a
    # malformed key cannot silently normalise to something plausible.
    rostered, malformed = set(), sorted(k for k in roster if len(k) != 5 or not k.isdigit())
    if malformed:
        fail("ia-county-officers.json has %d key(s) that are not a 5-digit "
             "GEOID (%s) — the ring cannot be compared against keys it cannot "
             "read" % (len(malformed), ", ".join(malformed[:6])))
        return 0
    for key in roster:
        rostered.add(key[-3:])

    masked = sorted(rostered - in_ring)
    if masked:
        fail("count%s whose officers this app NAMES but which sit outside "
             "METRO_COUNTY_FIPS, so the out-of-scope wash greys them out while "
             "their cards answer in full: %s. Add the FIPS to "
             "scripts/build_metro_outline.py WITH an INSIDE anchor and rebuild "
             "data/app/metro-outline.json."
             % ("ies" if len(masked) > 1 else "y", ", ".join(masked)))
    promised = sorted(in_ring - rostered)
    if promised:
        fail("count%s inside METRO_COUNTY_FIPS with no entry in "
             "ia-county-officers.json, so the wash promises an answer the card "
             "cannot give: %s. Either the roster stopped resolving (re-read the "
             "source) or the county was added to the ring too early."
             % ("ies are" if len(promised) > 1 else "y is", ", ".join(promised)))
    return len(in_ring)


if __name__ == "__main__":
    main()
