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
    files and LTSB's supervisory districts, which are REPUBLISHED each 15
    January and 15 July) were downloaded at build time. The check there is
    provenance: is the source we cite still reachable, and a reminder to
    re-verify after each publication window.

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
  4. Live service endpoints (Census TIGERweb, USGS structures): reachable.  [WARN]

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
import datetime
import json
import os
import re
from urllib.parse import urlsplit
import sys

try:
    import requests
except ImportError:  # pragma: no cover - requests is pinned in requirements.txt
    requests = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

HTTP_TIMEOUT = 25

# The freshness gate's source manifest for the Wisconsin instance. Every layer
# this instance adds gets its rows
# here in the same change (CLAUDE.md's conventions; the reference repo's
# validate_sources.py shows a mature manifest's full shape, including
# year-search patterns and the `blocked` inversion).
SOCRATA_DOMAIN = "data.invalid"  # this fork's Socrata portal, if it adopts one
CATALOG_API = "https://api.us.socrata.com/api/catalog/v1"

# Socrata dataset ids the app hardcodes (none in the starter set).
SOCRATA = []

# Same-origin data/app files and the upstream source each was built from.
# EVERY PATH ON THIS HOST, NOT ONE. milwaukeemaps.milwaukee.gov publishes
# `User-agent: * / Disallow: /` (Googlebot excepted), measured 2026-09-05, so a
# Disallow on one row is a Disallow on all six — and one of the six is
# `election/alderman/MapServer/0`, the very URL the alderperson scraper stopped
# fetching in this same change. Retiring it there and leaving the monthly
# provenance probe requesting it would have been the fix in name only.
#
# NOTHING IS LOST BY NOT ASKING. All six layers ship as committed data/app
# files, rebuilt by an OPERATOR running a builder — the app never touches this
# host at runtime (wi/index.html says so at its Racine block) — so the monthly
# GET was the only scheduled request, and its whole yield was "the service still
# exists". A re-pull is a deliberate act with the policy in view.
#
# `blocked` WOULD NOT HAVE DONE THIS: that flag is for a host that REFUSES us,
# where the request is how we learn the refusal still stands, so it fetches and
# only inverts the reading. A robots Disallow is the opposite — the host is
# ASKING us not to request — and the honest answer is not to.
ROBOTS_MILWAUKEEMAPS = (
    "milwaukeemaps.milwaukee.gov disallows every path to every agent but "
    "Googlebot (robots.txt, measured 2026-09-05). The layer ships as a "
    "committed data/app file from an operator rebuild, so nothing here needs "
    "this host on a schedule; the shipped file is checked above instead.")


PROVENANCE = [
    {
        "layer": "us-house",
        "app_file": "congress-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/0",
        "note": "Congressional districts pre-built from TIGERweb by bootstrap_state.py; redraws each decennial cycle (WATCH.md). Built against TIGERweb's 120th-Congress layer (field CD120, Jan 1 2026 vintage); the retired CD119 field is gone and a query naming it returns an HTTP-200 JSON error envelope with no features key, so a rebuild on the old name fails as no-features.",
    },
    {
        "layer": "us-house",
        "app_file": "congress-roster.json",
        "source_url": "https://unitedstates.github.io/congress-legislators/legislators-current.json",
        "note": "Delegation roster from the public-domain congress-legislators project; refreshed weekly by update-wi-congress-roster.yml.",
    },
    {
        "layer": "county",
        "app_file": "state-counties.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1",
        "note": "County polygons pre-built from TIGERweb by bootstrap_state.py.",
    },
    {
        "layer": "school-district-unified",
        "app_file": "school-districts-unified.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0",
        "note": "Unified school districts pre-built from TIGERweb by bootstrap_state.py.",
    },
    {
        "layer": "wi-senate",
        "app_file": "wi-senate-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/1",
        "note": "State Senate districts pre-built from TIGERweb by wi/scripts/build_legislative_boundaries.py; redraws each decennial cycle (WATCH.md).",
    },
    {
        "layer": "wi-senate",
        "app_file": "wi-senate-members.json",
        "source_url": "https://data.openstates.org/people/current/wi.csv",
        "note": "Senate roster base (name, party) from the Open States current-people export; refreshed weekly by update-wi-legislature-roster.yml.",
    },
    {
        "layer": "wi-senate",
        "app_file": "wi-senate-members.json",
        "source_url": "https://docs.legis.wisconsin.gov/2025/legislators/senate",
        "note": (
            "The Legislature's own senate index — the office/phone/fax/e-mail "
            "enrichment (wi_legislature_scraper.py). SESSION-SCOPED URL: the "
            "/2025/ biennium path must be bumped each odd-year January "
            "(WATCH.md row) — this row going dead is that bump coming due."
        ),
    },
    {
        "layer": "wi-assembly",
        "app_file": "wi-assembly-districts.json",
        "source_url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/2",
        "note": "State Assembly districts pre-built from TIGERweb by wi/scripts/build_legislative_boundaries.py; redraws each decennial cycle (WATCH.md).",
    },
    {
        "layer": "wi-assembly",
        "app_file": "wi-assembly-members.json",
        "source_url": "https://data.openstates.org/people/current/wi.csv",
        "note": "Assembly roster base (name, party) from the Open States current-people export; refreshed weekly by update-wi-legislature-roster.yml.",
    },
    {
        "layer": "wi-assembly",
        "app_file": "wi-assembly-members.json",
        "source_url": "https://docs.legis.wisconsin.gov/2025/legislators/assembly",
        "note": (
            "The Legislature's own assembly index — the office enrichment; "
            "same session-scoped-path caveat as the senate row."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-supervisory-districts.json",
        "source_url": "https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest/services/WI_County_Supervisory_Districts_Current/FeatureServer/0",
        "note": (
            "Supervisory districts for all 72 counties, pre-built by "
            "wi/scripts/build_wi_supervisory_districts.py from LTSB's statewide aggregate of "
            "county filings under Wis. Stat. 5.15(4)(br)1. The layer is REPUBLISHED each 15 "
            "January and 15 July, so re-run the builder after a submission window: its own "
            "gates (feature count, 1..n numbering per county, ward reconciliation) are what "
            "catch a county whose filing changed or broke."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-supervisory-districts.json",
        "source_url": "https://services9.arcgis.com/cqHJZMbXoaOT0XrP/arcgis/rest/services/Trempealeau_County_County_Board_Supervisor_Districts_2021_2031_WFL1/FeatureServer/3",
        "note": (
            "Trempealeau County's own adopted plan, shipped in place of LTSB's file for that "
            "county alone (LTSB merges its districts 15 and 17; the county still elects "
            "seventeen). If this service ever stops answering, the builder fails rather than "
            "silently falling back to the merged geometry."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-directory.json",
        "source_url": "https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest/services/WI_Municipal_Wards_Current/FeatureServer/0",
        "note": (
            "The ward layer is BOTH the independent witness the district builder "
            "reconciles against (every ward names a district that exists, every "
            "district owns a ward) AND, since phase 2, the live source behind the "
            "shipped `ward` card (its own ENDPOINTS row below). Listed here so its "
            "disappearance fails the supervisory build's provenance too."
        ),
    },
    {
        "layer": "wi-circuit-court",
        "app_file": "wi-circuit-courts.json",
        "source_url": "https://www.wicourts.gov/courts/circuit/judges.htm",
        "note": (
            "The 69 circuits as county unions under a double witness — Wis. Stat. "
            "753.06 and this wicourts listing, which the weekly roster scrape "
            "re-asserts (its failure is the redistricting tripwire). Cite the "
            "statute by per-subsection URLs when re-verifying: the chapter page "
            "lazy-loads and one fetch truncates at 52 of 63 entries (measured). "
            "Rebuild with wi/scripts/build_wi_circuit_courts.py only if the "
            "county file or the statute moves."
        ),
    },
    {
        "layer": "wi-circuit-court",
        "app_file": "wi-circuit-judges.json",
        "source_url": "https://www.wicourts.gov/contact/Circuit_Courts.html",
        "note": (
            "The bench's enrichment source (branch, direct phone, courthouse), "
            "joined onto the judges table by wi_circuit_judges_scraper.py + "
            "build_wi_circuit_court_roster.py; refreshed weekly by "
            "update-wi-circuit-court-roster.yml."
        ),
    },
    {
        "layer": "wi-court-of-appeals",
        "app_file": "wi-court-of-appeals-districts.json",
        "source_url": "https://www.wicourts.gov/courts/appeals/index.htm",
        "note": (
            "The four appellate districts as county unions under a double witness "
            "— Wis. Stat. 752.11 (unchanged since 1977) and this appeals page, "
            "whose county lists the weekly roster scrape re-asserts. Rebuild with "
            "wi/scripts/build_wi_court_of_appeals.py only if either witness moves."
        ),
    },
    {
        "layer": "wi-court-of-appeals",
        "app_file": "wi-court-of-appeals-roster.json",
        "source_url": "https://www.wicourts.gov/contact/Court_of_Appeals.html",
        "note": (
            "The sixteen-judge bench (4/4/3/5, gated) with roles, phones and "
            "chambers — read from this page's CONTENT blocks, never the judges "
            "index's stale nav list; refreshed weekly by "
            "update-wi-court-of-appeals-roster.yml."
        ),
    },
    {
        "layer": "county",
        "app_file": "wi-county-clerks.json",
        "source_url": "https://docs.legis.wisconsin.gov/misc/lrb/blue_book/2025_2026/210_officials_and_employees.pdf",
        "note": (
            "The Blue Book county-officers excerpt the clerk roster's names and "
            "party-or-appointed codes come from. A NEW BIENNIAL EDITION is the "
            "drift to watch: the 2027-28 book will publish under a new path, and "
            "the scraper's URL follows it by hand (WATCH.md row)."
        ),
    },
    {
        "layer": "county",
        "app_file": "wi-county-clerks.json",
        "source_url": "https://wisconsincountyclerks.org/wisconsin-counties/",
        "note": (
            "The clerks' association's county index (72 per-county pages) — the "
            "roster's contact half and its currency witness; crawled weekly at "
            "the robots-declared 10-second delay by wi_county_clerk_scraper.py."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://services2.arcgis.com/s1wgJQKbKJihhhaT/arcgis/rest/services/Milwaukee_County_Supervisory_Districts/FeatureServer/46",
        "note": (
            "Milwaukee's 18 supervisors as attributes on the county's own LIO "
            "layer (Sup_Name/Email_Addr/Website_Url) — the blocked-site-is-not-"
            "a-blocked-county route; witnessed per run against the county's "
            "Legistar API (body 138), which is a witness, never a source."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://services1.arcgis.com/z1oAk3W6cWVD8swZ/arcgis/rest/services/County_Board_of_Supervisors_WFL1/FeatureServer/0",
        "note": (
            "Racine's 21 supervisors with e-mails on the county's own AGO org "
            "(REPNAME/Contact, edited post-April-2026) — same route as "
            "Milwaukee, no witness needed: the layer is the county's only "
            "machine-readable roster and its edit date is the currency fact."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://www.co.adams.wi.us/government/county-board",
        "note": (
            "Adams's 20 supervisors, the one roster that rides a DOCUMENT and "
            "still scrapes weekly: the county clerk publishes a public "
            "directory PDF with a text layer, and this page is where the county "
            "links it. THE PAGE IS THE ROW BECAUSE THE FILE IS NOT STABLE — the "
            "clerk republishes each edition at a new Drive id, so the scraper "
            "resolves the `County Directory` link here on every run rather than "
            "pinning a file, and this page going dead (or losing that link) is "
            "the signal. Note this host serves a full 259 KB of site chrome on "
            "a 404, so a body-length probe cannot tell a live page from a "
            "missing one; the status is what counts."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://www.browncountywi.gov/government/county-board-of-supervisors/",
        "note": (
            "The supervisor roster — 29 counties' own board pages, two county GIS layers (rows above) and Kenosha's directory document (row below), refreshed weekly by "
            "update-wi-county-board-roster.yml with each county's reading direction "
            "pinned (the full URL table is COUNTIES in wi_county_board_scraper.py). "
            "Two representative pages are probed — Brown, the largest launch-set "
            "board at 26 seats, and Dane, the largest of all at 37, whose roster "
            "lives on the BOARD's own host rather than the county's — because the "
            "weekly scrape already fails loudly per "
            "county; this row exists so the FILE's disappearance is noticed and so "
            "the roster has a manifest row at all."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": ("https://saukdomino.co.sauk.wi.us/Internet/Applications/"
                       "main.nsf/publicDistrictList.xsp"),
        "note": (
            "Sauk's 31 districts on a Domino application host of the county's "
            "own — linked from co.sauk.wi.us/countyboard/sauk-county-board-"
            "members as its current-term list, and the same distinction Dane "
            "makes below: the roster is not on the host the county's other "
            "surfaces live on. Probed here because it is the only county whose "
            "roster rides an application server rather than a page, so an "
            "application that stops answering is noticed on this report rather "
            "than only in the weekly scrape's own failure."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://board.danecounty.gov/Supervisors",
        "note": (
            "Dane's 37 supervisors on the COUNTY BOARD's own host — a different "
            "host from the countyofdane.com this instance's clerk file carries, "
            "which is why a sweep of county sites recorded Dane as publishing "
            "nothing for a fortnight. Probed here so the distinction stays "
            "measured rather than remembered."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://www.kenoshacountywi.gov/1018/County-Directory-PDF",
        "note": (
            "Kenosha's 23 supervisors come from the Clerk's own Directory of "
            "Public Officials — the file's one FETCHED document, as against "
            "Taylor's carried one below, and re-read on every weekly run. "
            "THE STABLE PAGE ID IS THE "
            "POINT OF PROBING THIS: the document itself lives at a "
            "/DocumentCenter/View/<edition>/ address that freezes on the edition "
            "it names, and this id is the county's own page for whichever edition "
            "is current, so it redirects as the annual directory is republished. "
            "Its going unreachable is the news; the weekly scrape already fails "
            "loudly if the document's board section reshapes."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://www.kenoshacountywi.gov/113/County-Board-of-Supervisors",
        "note": (
            "The WITNESS for the row above: the county board's own page, which "
            "names the same 23 supervisors and states the board's leadership in "
            "prose. The scraper ships nothing for Kenosha unless the two surfaces "
            "agree name-for-name, and withholds the Chair and Vice-Chair roles "
            "unless this page's leadership sentence confirms them, so this URL is "
            "load-bearing rather than decorative. It is also the card's own link, "
            "and it is NOT the county's map index at "
            "/142/County-Board-Supervisor-Districts, which names nobody and which "
            "this gap record mistook for the roster page for a month."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://www.fdlco.wi.gov/government/county-board-supervisors",
        "blocked": "AkamaiGHost \"Access Denied\" on every path, every user-agent and "
                   "both schemes — a client-fingerprint block on a datacenter "
                   "address, not a refusal to publish. Fond du Lac's twenty-five "
                   "supervisors ship anyway, read from the Internet Archive's copy "
                   "of this same public page (ARCHIVE_COUNTIES in "
                   "wi_county_board_scraper.py), with the copy's age gated.",
        "note": (
            "Fond du Lac's County Board Supervisors directory — district-keyed "
            "with name, county e-mail and phone per supervisor, and the Chair and "
            "both Vice Chairs titled. THE INVERSION MATTERS MORE HERE THAN "
            "ANYWHERE ELSE IN THIS FILE: this host answering again would not "
            "merely be tidy news, it is the event that retires the archive hop, "
            "because the scraper already tries the county's own server first on "
            "every run and only falls through on a block. A WARN on this row is "
            "an instruction to delete code."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://board.co.columbia.wi.us/",
        "note": (
            "Columbia's 28 supervisors, as the TABLE its Supervisor Listing page "
            "frames from this second host. The listing page is what the card "
            "links and what the roster records as its source; THIS host is the "
            "one nothing else in the repo names, so it is registered here — "
            "without a row, the only surface that would notice it going away is "
            "the weekly scrape, and only by failing."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": ("https://www.sheboygancounty.com/departments/county-board/"
                       "county-board-supervisors"),
        "probe_as": "scraper",
        "note": (
            "Sheboygan's 25 supervisors — the county recorded for a year as one "
            "of nine answering 403 'and holding it against browser headers'. The "
            "headers were not a browser's: a Chromium user-agent with none of "
            "Chromium's Sec-CH-UA client hints, which Akamai's bot manager scores "
            "as the self-contradiction it is. PROBED AS THE SCRAPER (see "
            "`probe_as` above) because this host also discriminates by client "
            "STACK — urllib 200, requests 403, identical headers. This row is the "
            "standing witness that the fix still holds: the host refusing again "
            "is the one failure the county's own count guard would report merely "
            "as a missing county."
        ),
    },
    {
        "layer": "county",
        "app_file": "wi-county-officers.json",
        "source_url": "https://www.sheboygancounty.com/government/elected-officials",
        "probe_as": "scraper",
        "note": (
            "Sheboygan's six elected county offices on ONE page — the first "
            "'directory' source in wi_county_officer_contact_scraper.py, read "
            "FORWARD from each officer's own witnessed name and stopped at the "
            "next officer's, because the per-office 'pages' window centred on a "
            "name returns the PRECEDING officer's phone on a page shaped like "
            "this one (measured: four of five wrong, every one a plausible "
            "county number)."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://co.taylor.wi.us/directory/county-board/",
        "blocked": "sg-captcha challenge on every path (HTTP 202 + meta-refresh to "
                   "/.well-known/sgcaptcha/); a captcha is an access control and is "
                   "not defeated here. Taylor's seventeen supervisors ship as a DATED "
                   "DOCUMENT read from this page in a browser, not as a scrape.",
        "note": (
            "Taylor's County Board directory — district-keyed with name, county "
            "e-mail and phone per supervisor. Recorded as EXPECTED-UNREACHABLE, so "
            "the check INVERTS: a refusal reads OK and this host becoming readable "
            "is the WARN, because that is the state a human can act on — it would "
            "mean the document route can be retired for a weekly scrape."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://www.lafayettecountywi.org/bos",
        # THE SAME INVERSION AS TAYLOR ABOVE, with one difference that matters:
        # this county's page PARSES. `same-line-lead` reads all sixteen seats
        # off it 16/16 (verified against the Internet Archive's own capture),
        # and the weekly scraper pins that reading on Lafayette's
        # DOCUMENT_ROSTERS entry and RE-TRIES THE LIVE PAGE ON EVERY RUN. So a
        # WARN here is not paperwork: it means the live attempt can start
        # succeeding, and the county moves to COUNTIES with its capture date
        # leaving the card by itself.
        "blocked": ("Cloudflare managed challenge (cf-mitigated: challenge, "
                    "\"Just a moment...\") to plain clients on both the bare and "
                    "www hosts, browser headers included — measured 2026-08-29"),
        "note": (
            "Lafayette's Board of Supervisors page — sixteen seats written "
            "\"Larry Ludlum- Supervisor District #1\", the person, the office, "
            "then the district, which none of the four older readings could see "
            "because they test the text AFTER the district and it ends in the "
            "word every other county uses as a heading. Fifteen of the sixteen "
            "names are witnessed against the Internet Archive's capture of this "
            "page; the chair against the Blue Book. Recorded EXPECTED-UNREACHABLE "
            "on the same inverted terms as Taylor."
        ),
    },
    {
        "layer": "county-board",
        "app_file": "county-board-members.json",
        "source_url": "https://www.co.monroe.wi.us/government/county-board-of-supervisors/"
                      "districts-supervisors",
        "blocked": "Akamai \"Access Denied\" to THIS checker's client and not to the "
                   "scraper: the same page answers HTTP 200 (153 KB, all sixteen "
                   "supervisors) to wi_county_board_scraper.py's urllib fetch with the "
                   "header set a Chrome navigation sends, and is read that way weekly. "
                   "Measured 2026-08-29: `requests` is refused with byte-identical "
                   "headers, so what the edge scores sits below the header layer.",
        "note": (
            "Monroe's Districts & Supervisors table — the county states each seat's "
            "district twice (the District cell and the district.NN@ address it "
            "publishes for that seat) and the scraper requires the two to agree. "
            "Recorded as EXPECTED-UNREACHABLE so this monthly report does not call a "
            "link dead that the weekly roster run reads; the INVERSION means this "
            "host answering here is the WARN, and that WARN would mean the "
            "per-county header exception can go."
        ),
    },
    {
        "layer": "school-site",
        "app_file": "school-sites.json",
        "source_url": "https://services8.arcgis.com/o4NJgD3NfeHnWy06/arcgis/rest/services/Wisconsin_Public_Schools/FeatureServer/20",
        "note": (
            "Public school sites from DPI's own ArcGIS org (2,290 records, "
            "2,138 placed — the rest are placeless virtual programs), "
            "pre-built by wi/scripts/build_wi_school_sites.py. An OPERATOR "
            "rebuild after DPI's school-year rotation (WATCH.md); the builder "
            "pages past the service's 2,000-record cap and asserts the total."
        ),
    },
    {
        "layer": "school-site",
        "app_file": "school-sites.json",
        "source_url": "https://services8.arcgis.com/o4NJgD3NfeHnWy06/arcgis/rest/services/WI_Private_Schools/FeatureServer/2",
        "note": (
            "Private school sites (828) from the same DPI org — the same "
            "builder, which encodes the per-layer attribute renames "
            "(LATITUDE/LONGITUDE here against the public layer's LAT/LON)."
        ),
    },
    {
        "layer": "school-site",
        "app_file": "school-sites.json",
        "source_url": "https://www.arcgis.com/sharing/rest/content/items/d383fe81275e46f2a5a5c4f1a0c2eb85?f=json",
        "note": (
            "The DPI school directory's AGO catalog item — the successor "
            "watch: DPI rotates the directory around each school year, and "
            "this item dying or renaming is the signal a successor item "
            "shipped (the Socrata newer-edition pattern, AGO edition)."
        ),
    },
    {
        "layer": "wtcs-district",
        "app_file": "wtcs-districts.json",
        "source_url": "https://services8.arcgis.com/o4NJgD3NfeHnWy06/arcgis/rest/services/WI_Technical_College_Regions_2019/FeatureServer/0",
        "note": (
            "The 16 WTCS districts from DPI's own AGO org (the school-site "
            "and library builds' org, same reference-use licence), "
            "server-generalized and pre-built by "
            "wi/scripts/build_wi_wtcs_districts.py under five gates — the "
            "seat witness (each college's home city inside its own "
            "district) and the Lake-Winnebago-only hole rule among them. "
            "The '2019' in the service name is a title, not a vintage: the "
            "content carries Northwood, the 2021 rename. Boards appointed "
            "(Wis. Stat. 38.08) — identity-only."
        ),
    },
    {
        "layer": "wtcs-district",
        "app_file": "wtcs-districts.json",
        "source_url": "https://www.arcgis.com/sharing/rest/content/items/0fdad1436fc04ebf85ba7839dad3ab79?f=json",
        "note": (
            "The WTCS-districts AGO catalog item — the successor watch, the "
            "school-directory pattern: this item dying or renaming is the "
            "signal a successor item shipped."
        ),
    },
    {
        "layer": "library",
        "app_file": "library-sites.json",
        "source_url": "https://services8.arcgis.com/o4NJgD3NfeHnWy06/arcgis/rest/services/WI_Public_Libraries_and_Branches/FeatureServer/6",
        "note": (
            "Public library outlets (482, branches included) from DPI's AGO "
            "org, pre-built by wi/scripts/build_wi_libraries.py — whose bbox "
            "gate holds the line on the layer's measured trap: its LAT/LONG "
            "attributes are Web Mercator meters despite their names, so only "
            "the outSR=4326 geometry is ever read."
        ),
    },
    {
        "layer": "aldermanic-district",
        "app_file": "aldermanic-districts.json",
        "source_url": "https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest/services/WI_Municipal_Wards_Current/FeatureServer/0",
        "note": (
            "The dissolve source — the coded city/village wards of LTSB's "
            "statewide layer, dissolved on COUSUBFP+ALDERID by "
            "wi/scripts/build_wi_aldermanic_districts.py (an OPERATOR rebuild "
            "each Jan/Jul filing window, WATCH.md). Same endpoint the ward "
            "layer queries live; this row ties the pre-built file to it."
        ),
    },
    {
        "layer": "aldermanic-district",
        "app_file": "aldermanic-districts.json",
        "source_url": "https://mapservices.legis.wisconsin.gov/arcgis/rest/services/BAS_Collection/BAS_Live_Collection_Alderpersons/FeatureServer/0",
        "note": (
            "The composition WITNESS — the state's own pre-dissolved working "
            "set, a different filing edition that must agree key for key "
            "(867/867 at first build). Never the source: no stated terms and "
            "it mutates mid-collection."
        ),
    },
    {
        "layer": "aldermanic-district",
        "app_file": "wi-alderpersons.json",
        "source_url": "https://www.cityofmadison.com/council/council-members",
        "note": (
            "One representative roster page of the seventeen the weekly "
            "scrape reads (wi_alderperson_scraper.py carries the full table, "
            "and each municipality's sourceUrl reaches the monthly link gate "
            "through the shipped file) — the scrape already fails loudly per "
            "municipality; this row exists so the FILE has a manifest row and "
            "a dead index page is noticed."
        ),
    },
    {
        "layer": "aldermanic-district",
        "app_file": "wi-alderpersons.json",
        "source_url": "https://gis-city.kenosha.org/server/rest/services/Organizational_Layers/Districts_ElectedRepresentation/FeatureServer/150",
        "note": (
            "Kenosha's roster layer (REP_AREA='D' rows; each district appears "
            "twice, one row named and one N/A). Its currency is WITNESSED "
            "against the county's certified spring canvass, which caught the "
            "layer stale on one seat at first build — the item's modified "
            "date is the VIEW definition's, never the data's."
        ),
    },
    {
        "layer": "aldermanic-district",
        "app_file": "wi-alderpersons.json",
        "source_url": "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/election/alderman/MapServer/0",
        "robots_disallowed": ROBOTS_MILWAUKEEMAPS,
        "note": (
            "Milwaukee's roster layer (ALDERPERSON attribute, 15/15). The "
            "host drops ~1 in 4-8 requests with TCP resets — the scraper "
            "retries and falls back to the same data's CKAN shapefile — and "
            "the roster is witnessed against the city's Legistar API "
            "(webapi.legistar.com/v1/milwaukee, body 1) every run."
        ),
    },
    {
        "layer": "mps-school-board",
        "app_file": "mps-school-board-districts.json",
        "source_url": "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/AGO/MPS_School_Districts/MapServer/1",
        "robots_disallowed": ROBOTS_MILWAUKEEMAPS,
        "note": (
            "Milwaukee's own MPS board-district layer, server-reprojected and "
            "pre-built by wi/scripts/build_mps_school_board_districts.py (the "
            "same measured-flaky host as the alderman layer — build-time only, "
            "retried). Adopted 2022-02-25; redraws each census (WATCH.md)."
        ),
    },
    {
        "layer": "mps-school-board",
        "app_file": "mps-school-board-districts.json",
        "source_url": "https://data.milwaukee.gov/dataset/milwaukee-public-school-board-districts",
        "note": (
            "The same districts as the city's CKAN shapefile (CC-BY) — the "
            "build-time WITNESS: districts 1-8 and their area shares must "
            "agree between the two city surfaces before the file ships "
            "(0.04% max share difference at first build)."
        ),
    },
    {
        "layer": "mps-school-board",
        "app_file": "mps-school-board-members.json",
        "source_url": "https://www.milwaukeepublicschools.org/about/board/directors",
        "note": (
            "The district's own directors page — one heading per seat, the "
            "at-large president plus districts 1-8 — scraped weekly by "
            "update-mps-school-board-roster.yml and witnessed against the "
            "board index's committee lists (two separately maintained "
            "surfaces must name the same directors)."
        ),
    },
    {
        "layer": "mpd-district",
        "app_file": "mpd-districts.json",
        "source_url": "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/MPD/MPD_geography/MapServer/2",
        "robots_disallowed": ROBOTS_MILWAUKEEMAPS,
        "note": (
            "The city's own MPD districts layer (field POLICE, districts 1-7), "
            "server-reprojected and pre-built by "
            "wi/scripts/build_milwaukee_city_layers.py — the same measured-"
            "flaky host as the MPS/alderman layers, build-time only, retried."
        ),
    },
    {
        "layer": "mpd-district",
        "app_file": "mpd-district-captains.json",
        "source_url": "https://city.milwaukee.gov/police/districts/District-1",
        "note": (
            "One of the seven per-district pages the weekly captains scrape "
            "reads (mpd_captains_scraper.py carries all seven, plus the city "
            "Directory page's per-district phones) — commanding officer + "
            "district phone, refreshed by update-mpd-captains-roster.yml as "
            "a reviewed bot PR. THE SCRAPER'S VANTAGE IS CI: this host "
            "refuses the development sandbox and answers GitHub's runners "
            "plain (measured 2026-08-27), so a probe of this row from a "
            "sandbox failing is expected — the monthly workflow probes from "
            "the vantage that matters. Two markup shapes are pinned: the "
            "officer h3 (D2's split-word 'Captai n' tolerated) and D4's "
            "empty-h3 contact-block paragraph."
        ),
    },
    {
        "layer": "mpd-district",
        "app_file": "mpd-districts.json",
        "source_url": "https://data.milwaukee.gov/dataset/milwaukee-police-district",
        "note": (
            "The same districts as the city's CKAN shapefile (CC-BY) — the "
            "build-time WITNESS: districts 1-7 and their area shares must "
            "agree between the two city surfaces before the file ships "
            "(0.04% max share difference at first build)."
        ),
    },
    {
        "layer": "milwaukee-neighborhoods",
        "app_file": "milwaukee-neighborhoods.json",
        "source_url": "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/planning/special_districts/MapServer/4",
        "robots_disallowed": ROBOTS_MILWAUKEEMAPS,
        "note": (
            "The city's own neighborhoods layer (field NEIGHBORHD, 190 "
            "polygons), server-reprojected and pre-built by "
            "wi/scripts/build_milwaukee_city_layers.py. Names publish "
            "ALL-CAPS and ship title-cased, the raw value kept on each "
            "feature as NAME_RAW."
        ),
    },
    {
        "layer": "mpd-squad-area",
        "app_file": "mpd-squad-areas.json",
        "source_url": "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/MPD/MPD_geography/MapServer/1",
        "robots_disallowed": ROBOTS_MILWAUKEEMAPS,
        "note": (
            "The city's own MPD squad-area layer (field SQUADAREA, 25 "
            "squads — the beat analog), server-reprojected and pre-built by "
            "wi/scripts/build_milwaukee_city_layers.py. A squad's number "
            "encodes its district (hundreds digit), which the builder "
            "sample-verifies against the shipped district file."
        ),
    },
    {
        "layer": "mpd-squad-area",
        "app_file": "mpd-squad-areas.json",
        "source_url": "https://data.milwaukee.gov/dataset/milwaukee-police-department-squad-areas",
        "note": (
            "The same squad areas as the city's CKAN shapefile (CC-BY) — "
            "the build-time WITNESS: all 25 keys and their area shares must "
            "agree between the two city surfaces before the file ships "
            "(0.02% max share difference at first build)."
        ),
    },
    {
        "layer": "milwaukee-neighborhoods",
        "app_file": "milwaukee-neighborhoods.json",
        "source_url": "https://data.milwaukee.gov/dataset/neighborhoods",
        "note": (
            "The same neighborhoods as the city's CKAN shapefile (CC-BY) — "
            "the build-time WITNESS on a space-insensitive key fold, because "
            "the city's two surfaces spell one neighborhood apart (service "
            "MCGOVERN PARK, shapefile MC GOVERN PARK — the service spelling "
            "ships; 0.007% max share difference at first build)."
        ),
    },
    {
        "layer": "county",
        "app_file": "wi-county-officers.json",
        "source_url": "https://docs.legis.wisconsin.gov/misc/lrb/blue_book/2025_2026/210_officials_and_employees.pdf",
        "note": (
            "The Blue Book's OTHER county-officer tables (phase 4): chair, "
            "executive/administrator (CE/CA/AC/CM typed), treasurer, clerk of "
            "circuit court, register of deeds, DA, sheriff, coroner/ME — "
            "layout-aware x-position parse, chair-seats witness against the "
            "shipped supervisory geometry (Menominee's 7-vs-5 pinned), the "
            "shared Menominee/Shawano DA footnote encoded. Shipped DATED "
            "(April 2025): no second publisher for these offices measures "
            "open — except the BOARD CHAIR, reconciled weekly against "
            "county-board-members.json (a chair the county's own page marks "
            "supersedes the book's; a book chair absent from a complete "
            "roster is withheld with the reason on the card) — and, via the "
            "per-county scrape (tranches 1-3 plus Green Lake), forty-five "
            "counties' own "
            "officer pages "
            "(wi_county_officer_contact_scraper.py): contact and a "
            "per-office name witness, superseding the book where a county "
            "moved past it (Waukesha's interim executive after the book's "
            "died in office; Portage's new county executive; Walworth's "
            "medical-examiner turnover). The "
            "2027-28 edition moves this URL — the biennium row in WATCH.md."
        ),
    },
    {
        "layer": "ward",
        "app_file": "mke-polling-places.json",
        "source_url": "https://data.milwaukee.gov/dataset/voting-wards",
        "note": (
            "Milwaukee's ward -> polling place pairing (CC-BY), pre-built by "
            "build_mke_polling_places.py: the CSV is the pairing of record "
            "(CR-terminated rows — measured), the city's own REST ward layer "
            "witnesses every pair, its places layer supplies the points "
            "(one place carries null geometry — pinned tolerance), and the "
            "ward set is gated EQUAL to LTSB's Milwaukee wards. Rebuilt per "
            "election (WATCH.md row), never weekly; the resource's "
            "last_modified moving is the signal."
        ),
    },
    {
        "layer": "ward",
        "app_file": "madison-polling-places.json",
        "source_url": "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/4",
        "note": (
            "Madison's ward -> polling place pairing, pre-built by "
            "build_madison_polling_places.py: the city's open-data layer is "
            "ONE polling point per ward (137 rows — ward number, building "
            "name, street address), gated EQUAL to LTSB's Madison wards AND "
            "the city's own ward layer (OPEN_DATA/11), every point "
            "bbox-gated inside Madison. The layer publishes no edition date "
            "(no editingInfo — measured 2026-08-27), so records date as "
            "read. Rebuilt per election (WATCH.md row), never weekly."
        ),
    },
    {
        "layer": "ward",
        "app_file": "milwaukee-polling-places.json",
        "app_file_pattern": "\"-polling-places.json\"",
        "source_url": "https://elections.wi.gov/elections",
        # THE INVERSION IS THE POINT HERE, not a way to quiet a warning. This
        # host sits behind a Cloudflare managed challenge that answers a plain
        # client 403 from every vantage measured — the sandbox and GitHub's own
        # runners alike (2026-08-27) — and a challenge is an access control this
        # project does not defeat. So unreachable is the EXPECTED state and
        # reports OK; becoming REACHABLE is the WARN, and it is the one a human
        # can act on: a plain 200 here would mean the published November list is
        # finally fetchable and the per-election refresh can stop being an
        # e-mail. Without this flag the monthly issue would carry the same
        # no-op WARN forever, which is how a report stops being read.
        "blocked": ("Cloudflare managed challenge (Cf-Mitigated: challenge) to plain "
                    "clients from every measured vantage; the file itself came from "
                    "the Commission by e-mail and is committed at wi/data/source/wec/"),
        "note": (
            "THE STATEWIDE pairing, and the one PROVENANCE row here whose "
            "source_url is NOT where the file came from — it is where the "
            "Commission says the published edition WILL be. The build input "
            "is a workbook the Wisconsin Elections Commission sent directly "
            "(help-desk ticket 123582, 2026-08-27), committed at "
            "wi/data/source/wec/ precisely because the provisional edition "
            "has no address: \"I can't provide any direct links for the "
            "attachments at this time, as it isn't published there for "
            "November yet, but that is where it would be\". So this row's URL "
            "is what the monthly check watches for the FINAL edition, and the "
            "2026-09-17 WATCH.md row is what acts on it. "
            "wi/scripts/build_wi_polling_places.py writes 72 per-county "
            "files, of which this one stands for all 72 (they build, gate "
            "and refresh together); it pairs 7,131 of LTSB's 7,161 wards, "
            "floors that rate at 99%, and refuses a ward claimed by two "
            "places. PROVISIONAL until the September re-pull clears the flag."
        ),
    },
    {
        "layer": "tid-district",
        "app_file": "tid-districts.json",
        "source_url": "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/planning/special_districts/MapServer/8",
        "robots_disallowed": (
            "milwaukeemaps.milwaukee.gov publishes `User-agent: * / Disallow: /` "
            "(Googlebot excepted), measured 2026-09-05. The TID layer is built by "
            "an OPERATOR rebuild, not a schedule, so nothing here needs the host "
            "on a cadence — but this monthly provenance probe did, and went on "
            "requesting it after the weekly alderperson scrape stopped. A "
            "re-pull is a deliberate act with the policy in view; a monthly "
            "automated GET is not."),
        "note": (
            "The city's own Tax Incremental Districts layer (79 active; "
            "field TID + NAME + create date), server-reprojected and "
            "pre-built by wi/scripts/build_milwaukee_city_layers.py — "
            "dissolved TIDs drop by date. TIDs are created and closed by "
            "Common Council action, so the count here moves. NOTHING HERE "
            "COMPARES THAT COUNT: this row records the source, and the "
            "monthly check reports only reachability for it, so a change is "
            "a rebuild trigger only for a human who remembers last month's "
            "number. The NG911 rows below show the shape that would close "
            "it — a sidecar the build writes; doing the same for the "
            "Milwaukee builder is recorded, not done."
        ),
    },
    {
        "layer": "tid-district",
        "app_file": "tid-districts.json",
        "source_url": "https://data.milwaukee.gov/dataset/tax-incremental-districts-tid",
        "note": (
            "The same districts as the city's CKAN shapefile (CC-BY) — the "
            "build-time WITNESS, scoped to the city's own STATUS flag "
            "because the shapefile keeps all 56 retired TIDs the live "
            "layer omits (0.007% max share difference at first build)."
        ),
    },
    {
        "layer": "tid-district",
        "app_file": "madison-tid-districts.json",
        "source_url": "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA_PLANNING/MapServer/8",
        "note": (
            "Madison's own TIF Districts layer — 25 rows of TWO concepts "
            "(16 district polygons + 9 half-mile planning buffers, the "
            "HALFMILERULE flag separating them; every row TIF_STATUS 'A'). "
            "wi/scripts/build_madison_city_layers.py ships layer ∩ DOR's "
            "certified active list (14 at first build): the layer still "
            "draws state-closed TID 39/47 and has not drawn active TID 55 "
            "(gap madison-tid-undrawn) — every delta is pinned and a pin "
            "mismatch fails the build."
        ),
    },
    {
        "layer": "tid-district",
        "app_file": "madison-tid-districts.json",
        "source_url": "https://www.cityofmadison.com/dpced/economic-development/tif",
        "note": (
            "The city's TIF program page — Madison display names come from "
            "its 'Current TIF Plans and Maps' listing, which the builder "
            "GATES equal to DOR's active set (the two authorities agreed "
            "15/15 at first build where the GIS layer disagreed three ways)."
        ),
    },
    {
        "layer": "tid-district",
        "app_file": "madison-tid-districts.json",
        "source_url": "https://www.revenue.wi.gov/Pages/Report/tid-active.aspx",
        "note": (
            "DOR's certified annual Active-TID workbook (tid100wi-<year>; "
            "the builder tries the current year then the prior) — the "
            "authority on which Madison TIDs exist. A new annual edition "
            "is the operator's rebuild trigger — for a human reading this "
            "note, since nothing here compares editions automatically."
        ),
    },
    {
        "layer": "madison-neighborhood-assoc",
        "app_file": "madison-neighborhood-assocs.json",
        "source_url": "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/12",
        "note": (
            "Madison's registered-association layer (141 rows; only the "
            "city's STATUS 'Active' 116 ship, classification kept per row "
            "because the registry holds six association kinds that nest). "
            "Same builder; the city's Data Policy is a reference-use "
            "disclaimer with attribution 'City of Madison, Wisconsin'."
        ),
    },
    {
        "layer": "madison-neighborhood-assoc",
        "app_file": "madison-outline.json",
        "source_url": "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/11",
        "note": (
            "The city's own ward fabric (137 at first build), dissolved to "
            "the corporate-limits MultiPolygon that grounds madisonCoverage "
            "— enclaves (Maple Bluff, Shorewood Hills, town islands) stay "
            "holes. Re-run the builder if the city re-wards."
        ),
    },
    {
        "layer": "fire-service",
        "app_file": "fire-service-areas.json",
        "source_url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/3",
        "note": (
            "The OEC's statewide NG911 FireBoundary aggregate (updated "
            "roughly weekly; licence \"free and open for use by the "
            "public\"), dissolved per agency on the DsplayName+Agency_ID "
            "pair by wi/scripts/build_wi_ng911_service_areas.py — 3,009 "
            "effective polygons to 1,046 department areas at first build, "
            "expired rows dropped by date, filing absences pinned (gap "
            "ng911-fire-filings)."
        ),
    },
    {
        "layer": "law-service",
        "app_file": "law-service-areas.json",
        "source_url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/4",
        "note": (
            "The same service's LawEnforcementBoundary layer, same builder "
            "and gates — 3,077 effective polygons to 639 agency areas at "
            "first build. Plain -dissolve, never -dissolve2, so the "
            "concurrent sheriff/PD overlaps the counties filed survive; "
            "absences are gap ng911-law-filings."
        ),
    },
    {
        "layer": "psap-area",
        "app_file": "psap-areas.json",
        "source_url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/6",
        "note": (
            "The same service's PSAPBoundary layer, same builder and gates — "
            "205 effective polygons to 95 answering points at first build. "
            "The tiling with FUTURE-dated Expire rows (11 kept), which is "
            "why the builder drops expired rows by date, never by presence; "
            "absences are gap ng911-psap-filings."
        ),
    },
    {
        "layer": "ems-service",
        "app_file": "ems-service-areas.json",
        "source_url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/2",
        "note": (
            "The same service's EmergencyMedicalServicesBoundary layer, same "
            "builder and gates — 2,443 effective polygons to 579 services at "
            "first build (2026-08-26), 2,444 to 580 after the 2026-09-05 "
            "rebuild. Regional ambulance providers re-prove the "
            "DsplayName+Agency_ID pair key (some EMS Agency_IDs are not "
            "county domains); absences are gap ng911-ems-filings."
        ),
    },
]

# Live endpoints the app queries at runtime.
ENDPOINTS = [
    {
        "layer": "county-subdivision",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/1/query?where=STATE%3D%2755%27&returnCountOnly=true&f=json",
    },
    {
        # Nearest-3 station layers, live by the state envelope (WI plus the
        # border-state stations a reader near the line genuinely wants).
        #
        # THE COUNT IS CHECKED, NOT JUST FETCHED. These rows already asked for
        # returnCountOnly and then threw the number away, so the one thing a
        # count endpoint is for could not be seen: the app fetches each layer
        # in a SINGLE request and ignores exceededTransferLimit, so the day a
        # layer passes the service's maxRecordCount it silently starts serving
        # a truncated set and every nearest-3 answer quietly gets worse. The
        # Michigan session measured exactly that on USGS structures — 2,000 of
        # 2,820 fetched, no error anywhere. `count_layer` names the layer whose
        # maxRecordCount the count is measured against, read live rather than
        # hardcoded, because a service that LOWERS its cap breaks this the same
        # way and a pinned 2000 would never notice.
        "layer": "police-station",
        "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53/query?geometry=-92.94,42.44,-86.19,47.36&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1&returnCountOnly=true&f=json",
        "count_layer": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/53",
    },
    {
        "layer": "fire-station",
        "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51/query?geometry=-92.94,42.44,-86.19,47.36&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1&returnCountOnly=true&f=json",
        "count_layer": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/51",
    },
    {
        # THE POST-OFFICE LAYER HAD NO COUNT ROW AT ALL — only a metadata probe
        # further down, which answers "the service exists" and nothing about
        # what the app receives from it.
        "layer": "post-office",
        "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38/query?geometry=-92.94,42.44,-86.19,47.36&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&where=1%3D1&returnCountOnly=true&f=json",
        "count_layer": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38",
    },
    {
        # The Madison pair is PRE-BUILT, and THIS ROW FETCHES A COUNT IT
        # DOES NOT READ — the same defect corrected for the NG911 rows below
        # on 2026-09-05, left standing here rather than widened into this
        # change: closing it needs the Madison/Milwaukee builders to write a
        # sidecar of their own, which is a different builder and a different
        # PR. Until then a count change is a trigger only for a human who
        # holds last month's number. The TIF layer's 25 counts BOTH concepts
        # (districts + half-mile buffers), so read a move as "something
        # changed", never as the district count itself.
        "layer": "tid-district",
        "url": "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA_PLANNING/MapServer/8/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        "layer": "madison-neighborhood-assoc",
        "url": "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/12/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        # madisonCoverage's ground: the city's ward fabric (137 at first
        # build) — a count change means the city re-warded; re-run the
        # Madison builder so the outline follows.
        "layer": "madison-neighborhood-assoc",
        "url": "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/11/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        # THE NG911 COUNT IS COMPARED, NOT JUST FETCHED. These four rows asked
        # for returnCountOnly=true and this checker read only reachability, so
        # the number was thrown away — the same defect fixed above for the
        # nearest-3 layers and never carried down here. The comment that used to
        # sit on this row said "a count change here is the operator's rebuild
        # trigger (WATCH.md)", which was a sentence and not a mechanism: nothing
        # held last month's number, so nothing could see a change.
        #
        # Measured 2026-09-05, the first time anyone compared: the shipped EMS
        # file was a filing behind. Waushara County had filed the City of
        # Berlin's own ambulance service over the city's Waushara-side half, and
        # the app was still answering Poy Sippi — the rural service — for
        # everyone in it (400/400 sampled points; 2.1 km2).
        #
        # `built_rows` names the key in the sidecar the BUILDER writes on every
        # run (wi/data/source/ng911/built-rows.json). The pin is a file rather
        # than a constant so it cannot fall out of step with the data files it
        # describes: one run writes both. What this CANNOT see is a county
        # redrawing a boundary without changing its row count, which is why the
        # finding is a WARN a human reads rather than a claim of freshness.
        "layer": "fire-service",
        "built_rows": "fire",
        "built_rows_layer": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/3",
        "url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/3/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        "layer": "law-service",
        "built_rows": "law",
        "built_rows_layer": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/4",
        "url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/4/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        "layer": "psap-area",
        "built_rows": "psap",
        "built_rows_layer": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/6",
        "url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/6/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        "layer": "ems-service",
        "built_rows": "ems",
        "built_rows_layer": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/2",
        "url": "https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer/2/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        # The ward layer queries this live (point-first + paged overlay). The
        # count moves with each Jan/July filing window (7,138 Jan 2026 -> 7,161
        # July 2026) — a change is expected news; the layer going unreachable
        # or answering zero is the drift this row exists to catch.
        "layer": "ward",
        "url": "https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest/services/WI_Municipal_Wards_Current/FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json",
    },
    {
        "layer": "municipality",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query?where=STATE%3D%2755%27&returnCountOnly=true&f=json",
    },
    {
        "layer": "school-district-secondary",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/1/query?where=STATE%3D%2755%27&returnCountOnly=true&f=json",
    },
    {
        "layer": "school-district-elementary",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/2/query?where=STATE%3D%2755%27&returnCountOnly=true&f=json",
    },
    {
        "layer": "zip-code",
        "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/PUMA_TAD_TAZ_UGA_ZCTA/MapServer/11?f=json",
    },
    {
        "layer": "post-office",
        "url": "https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer/38?f=json",
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


VALIDATOR_UA = {
    "User-Agent": "District Explorer source validator (+https://districtry.com/wi/)",
}
# A PROVENANCE ROW IS PROBED WITH THE CLIENT THAT ACTUALLY READS IT, or it is
# not a witness for that reader. This validator names itself honestly by
# default and that stays the default. `probe_as: "scraper"` on a row says the
# source is behind a bot manager that refuses this validator and answers the
# scraper, so the row is probed exactly as its scraper fetches it — a
# statement about the CONSUMER, never a way to quiet a finding.
#
# IT IS A DIFFERENT HTTP CLIENT AND NOT ONLY DIFFERENT HEADERS, and that is
# the measurement worth keeping. Sheboygan's host (Akamai bot manager) answers
# stdlib `urllib` 200 and `requests` 403 with BYTE-IDENTICAL headers — the
# Chromium user-agent plus the Sec-CH-UA client hints that
# wi_county_board_scraper.py's UA comment records. curl behaves like urllib.
# So the discriminator is below HTTP: urllib3's TLS ClientHello differs from
# the stdlib ssl module's, and the manager fingerprints it. Copying headers
# into `requests` reproduces nothing; the probe has to be the scraper's own
# stack.
SCRAPER_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "sec-ch-ua": '"Chromium";v="124", "Not;A=Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def scraper_get(url):
    """Reach a source the way its scraper does — stdlib urllib, not requests."""
    import urllib.error  # noqa: PLC0415 - only this one probe needs them
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=SCRAPER_UA)
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            if resp.status == 202:
                return False, "HTTP 202 — bot-management interstitial, not the document"
            resp.read(1)
            return True, resp
    except urllib.error.HTTPError as e:
        return False, "HTTP %d" % e.code
    except Exception as e:  # noqa: BLE001 - a finding, not a crash
        return False, "request failed: %s" % e


# How close to the cap is close enough to say something. A layer at 90% will
# cross it on ordinary growth well inside a year of monthly checks, and the
# whole point is to hear about it BEFORE the app starts silently truncating.
COUNT_HEADROOM_WARN = 0.9


def check_count_envelope_matches_index(findings):
    """The count URLs must measure the envelope the APP actually fetches.

    Every count row below hardcodes `-92.94,42.44,-86.19,47.36`. That is
    correct today and is a copy: the app's own envelope is METRO_BBOX in
    index.html, and the day someone widens it — a border county added, the
    Michigan handoff moved — the gate would go on measuring the OLD rectangle
    and report comfortable headroom for a request that had started truncating.
    A gate measuring a different question than the app asks is worse than no
    gate, because it reports OK.

    Derived rather than pinned would need the count URLs built at runtime;
    checking that the two AGREE costs one regex and fails just as loudly.
    """
    try:
        with open(INDEX_HTML, encoding="utf-8") as f:
            html = f.read()
    except OSError as exc:
        findings.add(WARN, "count-envelope",
                     "could not read index.html (%s), so the count URLs' envelope "
                     "is unchecked" % exc)
        return
    m = re.search(r"var METRO_BBOX = \{\s*minLng:\s*(-?[\d.]+),\s*minLat:\s*(-?[\d.]+),"
                  r"\s*maxLng:\s*(-?[\d.]+),\s*maxLat:\s*(-?[\d.]+)", html)
    if not m:
        findings.add(WARN, "count-envelope",
                     "METRO_BBOX not found in index.html — the count URLs' envelope "
                     "cannot be checked against what the app fetches")
        return
    want = "%s,%s,%s,%s" % (m.group(1), m.group(2), m.group(3), m.group(4))
    rows = [e for e in ENDPOINTS if e.get("count_layer")]
    bad = [e["layer"] for e in rows if ("geometry=" + want) not in e["url"]]
    if bad:
        findings.add(FAIL, "count-envelope",
                     "the count URL(s) for %s do not use the app's own METRO_BBOX "
                     "(%s) — they are measuring a different rectangle than the app "
                     "fetches, so their headroom means nothing"
                     % (", ".join(sorted(bad)), want))
    else:
        findings.add(OK, "count-envelope",
                     "all %d record-count URL(s) measure the app's own METRO_BBOX "
                     "(%s)" % (len(rows), want))


NG911_BUILT_ROWS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "source", "ng911", "built-rows.json")


def _check_shipped_is_current(findings, spec):
    """Report whether the shipped pre-built files still match the live source.

    The OEC refreshes roughly weekly; the builder is an OPERATOR build with no
    schedule. Nothing held the last build's row counts, so nothing could see the
    two drift apart — this reads the sidecar the builder writes and compares.

    A WARN here means a human should re-run wi/scripts/build_wi_ng911_service_areas.py.
    It is deliberately not a FAIL: falling behind a weekly source is the normal
    state between operator builds, and a monthly FAIL on it would be noise.
    """
    layer = spec["layer"]
    key = spec["built_rows"]
    try:
        with open(NG911_BUILT_ROWS) as f:
            pin = json.load(f)
    except (OSError, ValueError) as exc:
        findings.add(WARN, layer,
                     "the NG911 build sidecar could not be read (%s: %s), so "
                     "whether the shipped files are current with the source is "
                     "unknown — re-run the builder to write it"
                     % (os.path.basename(NG911_BUILT_ROWS), exc))
        return
    built = (pin.get("rows") or {}).get(key)
    built_on = pin.get("builtOn", "an unrecorded date")
    if not isinstance(built, int):
        findings.add(WARN, layer,
                     "the NG911 build sidecar carries no row count for %r — it "
                     "was written by an older builder, or the layer was renamed; "
                     "re-run the builder" % key)
        return

    ok, res = http_get(spec["url"])
    if not ok:
        findings.add(WARN, layer,
                     "count endpoint not reachable (%s): %s — the service may have "
                     "been renamed or retired" % (res, spec["url"]))
        return
    count = res.get("count") if isinstance(res, dict) else None
    if count is None:
        findings.add(WARN, layer,
                     "count endpoint answered without a count field: %r" % (res,))
        return

    # A ROW COUNT CANNOT SEE A REDRAW, so read the layer's own edit timestamp
    # too. Measured 2026-09-05: the OEC edited all four layers on 2026-08-31,
    # moving boundaries in 397 features (138 fire, 161 law, 19 PSAP,
    # 79 EMS), while three of the four row counts did not move at all —
    # the blind spot this file first documented and then
    # immediately hit.
    was_edit = (pin.get("dataLastEdit") or {}).get(key)
    live_edit = None
    ok_meta, meta = http_get(spec["built_rows_layer"] + "?f=json")
    if ok_meta and isinstance(meta, dict):
        ms = (meta.get("editingInfo") or {}).get("dataLastEditDate")
        if isinstance(ms, (int, float)):
            live_edit = datetime.datetime.fromtimestamp(
                ms / 1000.0, datetime.timezone.utc).date().isoformat()

    if count == built and was_edit and live_edit and was_edit != live_edit:
        findings.add(WARN, layer,
                     "the row count is unchanged at %d, but the service was "
                     "EDITED on %s against the %s these files were built from — a "
                     "redraw does not move a row count. Re-run "
                     "wi/scripts/build_wi_ng911_service_areas.py, bump cache_name "
                     "in wi/metro-worksheet.json, and commit the rebuilt files."
                     % (count, live_edit, was_edit))
        return
    if count == built:
        findings.add(OK, layer,
                     "%d rows, the same count these files were built from on %s%s"
                     % (count, built_on,
                        ", and the service's own last edit is still %s" % was_edit
                        if was_edit and live_edit == was_edit
                        else " (the service's edit date could not be read, so a "
                             "redraw at this row count would not show)"))
        return
    findings.add(WARN, layer,
                 "the source now has %d rows against the %d these files were "
                 "built from on %s — the shipped layer is behind by %+d and a "
                 "reader may be getting a superseded answer. Re-run "
                 "wi/scripts/build_wi_ng911_service_areas.py, bump cache_name in "
                 "wi/metro-worksheet.json (these files are cache-first), and "
                 "commit the rebuilt files with the refreshed sidecar."
                 % (count, built, built_on, count - built))


def _check_single_request_count(findings, spec):
    """Report the layer's record count against the cap one request can return.

    Reachability is the weaker half of this check. The app fetches these layers
    in ONE request and does not look at exceededTransferLimit, so a count at or
    past maxRecordCount means every card built from the layer is answering off a
    truncated set with nothing raised anywhere.
    """
    layer = spec["layer"]
    ok, res = http_get(spec["url"])
    if not ok:
        findings.add(WARN, layer,
                     "count endpoint not reachable (%s): %s — the service may have "
                     "been renamed or retired" % (res, spec["url"]))
        return
    count = res.get("count") if isinstance(res, dict) else None
    if count is None:
        findings.add(WARN, layer,
                     "count endpoint answered without a count field: %r" % (res,))
        return

    ok_meta, meta = http_get(spec["count_layer"] + "?f=json")
    cap = meta.get("maxRecordCount") if (ok_meta and isinstance(meta, dict)) else None
    if not isinstance(cap, int) or cap <= 0:
        findings.add(WARN, layer,
                     "%d records in the app's envelope, but the layer's "
                     "maxRecordCount could not be read, so whether one request "
                     "returns them all is unknown" % count)
        return

    if count >= cap:
        findings.add(FAIL, layer,
                     "%d records in the app's envelope against a maxRecordCount of "
                     "%d — the app fetches this layer in ONE request and ignores "
                     "exceededTransferLimit, so it is now serving a TRUNCATED set "
                     "and every nearest-N answer from it is suspect. Page the "
                     "loader (the engine's loadArcGISPaged)." % (count, cap))
    elif count >= cap * COUNT_HEADROOM_WARN:
        findings.add(WARN, layer,
                     "%d records against a maxRecordCount of %d — %.0f%% of what a "
                     "single request can return, and this loader makes exactly one. "
                     "Page it before it crosses." % (count, cap, 100.0 * count / cap))
    else:
        findings.add(OK, layer,
                     "%d records against a maxRecordCount of %d (%.0f%%) — one "
                     "request still returns them all"
                     % (count, cap, 100.0 * count / cap))


def http_get(url, want_json=True, params=None):
    """GET with a sane UA; returns (ok, payload_or_error). Never raises."""
    if requests is None:
        return False, "requests not installed"
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers=VALIDATOR_UA,
        )
    except Exception as e:  # network/TLS/proxy errors are a finding, not a crash
        return False, "request failed: %s" % e
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
        # A file the app addresses by a slug built at RUNTIME has no literal to
        # find — the ward card's <county>-polling-places.json is fetched as
        # "data/app/" + slug + "-polling-places.json", the same contract the
        # gaps panel uses for its county outlines and the same exemption
        # validate_index.py grants via `dynamic_reference`. The entry names the
        # suffix instead, and the drift check looks for THAT: a card that
        # stopped fetching the family at all still fails here.
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
        disallowed = p.get("robots_disallowed")
        if disallowed:
            # NOT FETCHED, AND `blocked` WOULD NOT HAVE DONE THIS. That flag is
            # for a host that REFUSES us — Akamai, a captcha — where the request
            # is how we learn the refusal still stands, so it fetches and only
            # inverts the reading. A robots Disallow is the opposite situation:
            # the host is ASKING us not to request, and the polite answer is not
            # to. Carrying this row under `blocked` would have left the monthly
            # job requesting milwaukeemaps.milwaukee.gov every month while the
            # scraper that stopped doing so was cited as the fix.
            findings.add(OK, layer,
                         "NOT REQUESTED — %s disallows this path in robots.txt, so "
                         "this row is checked by the shipped file above and never "
                         "fetched. %s" % (urlsplit(p["source_url"]).hostname,
                                          disallowed))
            continue
        if p.get("probe_as") == "scraper":
            ok, res = scraper_get(p["source_url"])
        else:
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
    check_count_envelope_matches_index(findings)
    for e in ENDPOINTS:
        if e.get("count_layer"):
            _check_single_request_count(findings, e)
            continue
        if e.get("built_rows"):
            _check_shipped_is_current(findings, e)
            continue
        ok, res = http_get(e["url"], want_json=False)
        if ok:
            findings.add(OK, e["layer"], "endpoint reachable")
        else:
            findings.add(WARN, e["layer"],
                         "endpoint not reachable (%s): %s — the service may have been "
                         "renamed or retired" % (res, e["url"]))


# Municipal ward boundary sources (none shipped yet; grown when this instance
# ships its ward layer — docs/WI_PHASE2_PLAN.md PR 1).
WARD_SOURCES = []


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
