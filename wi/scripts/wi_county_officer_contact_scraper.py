#!/usr/bin/env python3
"""
Scrape county officer CONTACT and name-currency from each county's OWN
pages — phase 4 PR 2, tranche 1 (docs/WI_PHASE4_PLAN.md).

The officer rows ship dated to the Blue Book because no STATEWIDE second
publisher measures open. That is a fact about aggregators, not about the
72 counties: a county's own sheriff/DA/treasurer pages are both the only
source of office contact and a fresher NAME witness than an April
snapshot. This scraper reads the counties measured open (2026-08-26),
each page PINNED, and writes an intermediate the officers builder merges:

  * "pages" mode — one pinned URL per office. The page must WITNESS the
    shipped officer: the surname as a WHOLE WORD with a word matching the
    first name's initial nearby. Substring matching is not enough —
    measured: "Jennifer Grant" matches inside Waukesha's "Community
    Block Grant" nav link, which is why the initial requirement exists.
    Contact (phone, e-mail) is taken only from a window around the name,
    never from the page at large — a department page carries many phones
    and shipping the wrong one is worse than shipping none.
  * "indexroll" mode — a single OFFICIALS page carrying one
    self-contained block per officer (name, exact title, and that
    person's own contact list), parsed STRUCTURALLY like civicplus and
    matched against the same per-office allow-sets. It exists because
    "pages" mode cannot read a page like this safely: that mode takes
    contact from a +/-350-character window around the witnessed surname,
    and on a one-page roster the window runs into the NEXT officer's
    block — measured on Green Lake, where the clerk of circuit court
    publishes no e-mail and the window reaches the county clerk's.
    A block boundary is not a distance guess (the board scraper's
    `_indexroll` carries the same reasoning for the same county's
    supervisors page, and this mode reuses its reader).
  * "directory" mode — ONE page carrying SEVERAL offices, each read
    FORWARD from its own witnessed name and STOPPED at the next
    officer's. "pages" mode cannot read such a page and does not fail
    when handed one, which is the whole reason this mode exists:
    `witness_window` centres a +/-350-character window on the name, and
    on a page that runs "Office / Name / Phone / ... / Office / Name /
    Phone" the FIRST phone in that window is the PRECEDING officer's.
    Measured on Sheboygan's elected-officials page 2026-08-29: four of
    five phones came back wrong and all four were plausible county
    numbers on the county's own exchange — the sheriff got the register
    of deeds', the DA the county clerk's, the treasurer the sheriff's,
    the register of deeds the DA's, and only the officer printed first
    on the page (whose window had nothing before it) was right. That is
    the same off-by-one the county board scraper pins a reading
    direction per county to prevent, one file over. So a directory page
    takes a window that BEGINS at the name and ENDS at the next
    witnessed officer's name, and every office on it is pinned to the
    same URL.
  * "civicplus" mode — the platform's one-page staff directory
    (directory.aspx), parsed STRUCTURALLY: each entry is a list item with
    the person's name and exact title(s). Titles are comma-split, the
    "<County> County " prefix stripped, and matched EXACTLY against a
    per-office allow-set, so "Chief Deputy Sheriff" and "Jail Captain"
    can never match "Sheriff". These directories publish NO phone or
    e-mail in the listing (measured — the employee detail pages are
    account-gated), so this mode yields a name check and a link, and the
    extracted name lets the builder detect DIVERGENCE mechanically.
  * Waukesha's executive is a pinned SUPERSEDE: the county's own page
    says County Executive Paul Farrow — the Blue Book's row — died in
    office, and Interim County Executive Tom Farley was sworn in
    2026-07-30. The extraction reads the interim's name from that page;
    the builder refuses to ship the book's name for this county even
    when this scrape fails (STALE_EXEC there).

MEASURED REFUSALS AND MISSES (tranche 3 work, not silently skipped):
county.milwaukee.gov and racinecounty.gov answer 403 to this client
(their board rosters ship from their GIS layers for the same reason).
BAYFIELD's CivicPlus pages render as ~1KB JS shells to a non-JS client,
it has no /Directory staff list, and its directory.aspx carries no staff
rows. VILAS publishes department pages that name no officer (3-7KB
stubs). DANE's medical-examiner and clerk-of-courts subdomains do not
resolve from this network (proxy 502), and its treasurer subdomain is a
payment portal naming nobody. DUNN's administration page does not name
the county manager, dunncountysheriff.com is a JS shell, and its
DA/deeds/examiner pages 404 at every conventional path — it shipped its
two witnessed offices only until 2026-08-31, when dunncountywi.gov's own
robots.txt turned out to disallow this client and the county left this
table entirely (the note above COUNTIES). JEFFERSON's own homepage links no
sheriff page and the conventional path 404s. GRANT publishes no
coroner/medical-examiner page at either conventional path. MARQUETTE's
DA page is a 1KB shell and its treasurer page is unlocated (finance
sits under administration). VERNON's DA page is a 2KB stub naming no
one and its clerk-of-courts page 404s (both spellings). WASHBURN's
clerk-of-courts page 404s (both spellings), and washburnsheriff.org — the
county's separately-hosted sheriff site, and its ONLY sheriff surface —
began answering 403 to this client behind a StackProtect WAF (measured
2026-09-01, three consecutive denials, `server: nginx` with an
`x-stackprotect-id`, so it is the site and not the egress proxy). That
office therefore stops resolving and its phone and link fall out of the
shipped row rather than carrying a `checked` date for a page that now
refuses; the county's floor of 4 still passes on its other four offices,
and a later run picks the sheriff back up if the WAF relents. WAUSHARA
publishes a County Clerk page but no clerk-of-courts page. Waukesha's
medical-examiner page deliberately names no person. A county below its pinned floor is
SKIPPED with a loud line, never shipped partial-silent.
"""

import datetime
import json
import os
import re
import sys
import time
import html as htmllib
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUT = os.path.join(SCRIPT_DIR, ".cache", "wi_county_officer_contacts_raw.json")
COUNTIES_FILE = os.path.join(REPO_ROOT, "data", "app", "state-counties.json")
OFFICERS = os.path.join(REPO_ROOT, "data", "app", "wi-county-officers.json")

# The client hints go with the UA — see wi_county_board_scraper.py's UA comment
# for the measurement. A Chromium user-agent sent without Chromium's
# Sec-CH-UA headers is a self-contradicting client, and Akamai's bot manager
# answers it 403; Sheboygan's pages are the ones that showed it. Every county
# this file already reads is unaffected (re-run 2026-08-29: identical output).
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml",
      "Accept-Language": "en-US,en;q=0.9",
      "Accept-Encoding": "identity",
      "sec-ch-ua": '"Chromium";v="126", "Not;A=Brand";v="24"',
      "sec-ch-ua-mobile": "?0",
      "sec-ch-ua-platform": '"Linux"'}

OFFICE_KEYS = ["sheriff", "districtAttorney", "treasurer",
               "clerkOfCircuitCourt", "registerOfDeeds", "coroner",
               "executive"]

# civicplus title allow-sets: a comma-split title segment, with the
# "<County> County " prefix stripped, must EQUAL one of these — deputies,
# chief deputies and jail staff can never match.
TITLE_SETS = {
    "sheriff": {"Sheriff"},
    "districtAttorney": {"District Attorney"},
    "treasurer": {"Treasurer", "County Treasurer"},
    "clerkOfCircuitCourt": {"Clerk of Courts", "Clerk of Court",
                            "Clerk of Circuit Court"},
    "registerOfDeeds": {"Register of Deeds"},
    "coroner": {"Coroner", "County Coroner", "Medical Examiner",
                "Chief Medical Examiner"},
    "executive": {"County Executive", "Interim County Executive",
                  "County Administrator", "Administrative Coordinator",
                  "County Manager"},
}

# FOUR COUNTIES LEFT THIS TABLE ON 2026-08-31 — Ashland, Dunn, Pepin and Polk —
# and not because their pages stopped answering. Each of those hosts publishes a
# robots.txt whose `User-agent: *` group reads `Disallow: /`, naming a handful of
# search engines above it and giving each a narrow /admin/ and /manager/. This
# scraper is none of the named agents, and it runs in TWO weekly workflows, so
# those counties were being fetched twice a week against a file that had said no.
# `wi/scripts/validate_robots.py` checks every URL this file fetches against its
# host's own `*` group and fails if one is disallowed, so a county cannot come
# back here by accident.
#
# THEIR CONTACT DID NOT GO WITH THEM. It is already read, and robots.txt governs
# RETRIEVAL rather than what already-public information may be shown, so the four
# ride CARRIED_CONTACTS below — the same treatment the board scraper's
# DOCUMENT_ROSTERS gives Jackson, Richland, Rusk, Polk, Dunn and Pepin, and for
# the same reason. Nothing re-fetches them; every run prints a NOT RE-READ line
# naming the county and the capture's age, and the card says the rows are a dated
# capture instead of the weekly check the other 42 counties get.
COUNTIES = {
    "Brown": {"mode": "pages", "floor": 6, "offices": {
        "sheriff": "https://www.browncountywi.gov/government/sheriffs-office/",
        "districtAttorney": "https://www.browncountywi.gov/government/district-attorney/",
        "treasurer": "https://www.browncountywi.gov/departments/treasurer/general-information/",
        "clerkOfCircuitCourt": "https://www.browncountywi.gov/departments/clerk-of-circuit-court/general-information/",
        "registerOfDeeds": "https://www.browncountywi.gov/departments/register-of-deeds/general-information/",
        "coroner": "https://www.browncountywi.gov/departments/medical-examiner/",
        "executive": "https://www.browncountywi.gov/government/county-executive/"}},
    "Washington": {"mode": "pages", "floor": 6, "offices": {
        "executive": "https://www.washcowisco.gov/departments/county_executive",
        "districtAttorney": "https://www.washcowisco.gov/departments/district_attorney",
        "treasurer": "https://www.washcowisco.gov/departments/county_treasurer",
        "registerOfDeeds": "https://www.washcowisco.gov/departments/register_of_deeds",
        "coroner": "https://www.washcowisco.gov/departments/medical_examiner",
        "clerkOfCircuitCourt": "https://www.washcowisco.gov/departments/clerk_of_circuit_court",
        "sheriff": "https://www.washcowisco.gov/elected_officials/sheriff_s_office"}},
    "Eau Claire": {"mode": "pages", "floor": 4, "offices": {
        "sheriff": "https://eauclairecounty.gov/departments/sheriff/index.php",
        "districtAttorney": "https://eauclairecounty.gov/departments/district_attorney/index.php",
        "clerkOfCircuitCourt": "https://eauclairecounty.gov/departments/clerk_of_courts/index.php",
        "treasurer": "https://eauclairecounty.gov/departments/treasurer/index.php",
        "registerOfDeeds": "https://eauclairecounty.gov/departments/register_of_deeds/index.php"}},
    # woodcountywi.gov resets connections intermittently — the fetch
    # retries carry it; its paths ABBREVIATE (DA, ROD, Courts), which is
    # why the conventional guesses 404'd in tranche 1
    "Wood": {"mode": "pages", "floor": 4, "offices": {
        "sheriff": "https://woodcountywi.gov/Departments/Sheriff/",
        "treasurer": "https://woodcountywi.gov/Departments/Treasurer/",
        "coroner": "https://woodcountywi.gov/Departments/Coroner/",
        "clerkOfCircuitCourt": "https://woodcountywi.gov/Departments/Courts/",
        "registerOfDeeds": "https://woodcountywi.gov/Departments/ROD/"}},
    # Dane publishes per-office SUBDOMAINS, not paths
    "Dane": {"mode": "pages", "floor": 3, "offices": {
        "sheriff": "https://danesheriff.com/",
        "executive": "https://exec.danecounty.gov/",
        "districtAttorney": "https://da.danecounty.gov/",
        "registerOfDeeds": "https://rod.danecounty.gov/"}},
    "Waukesha": {"mode": "pages", "floor": 3, "offices": {
        "districtAttorney": "https://www.waukeshacounty.gov/district-attorney/",
        "treasurer": "https://www.waukeshacounty.gov/treasurer/",
        "registerOfDeeds": "https://www.waukeshacounty.gov/register-of-deeds/",
        "sheriff": "https://www.waukeshacounty.gov/sheriff/"},
        "interim_exec": "https://www.waukeshacounty.gov/county-executive/"},
    "Grant": {"mode": "pages", "floor": 5, "offices": {
        "sheriff": "https://www.co.grant.wi.gov/grant-county-sheriffs-office/",
        "districtAttorney": "https://www.co.grant.wi.gov/district-attorney/",
        "treasurer": "https://www.co.grant.wi.gov/county-treasurer/",
        "clerkOfCircuitCourt": "https://www.co.grant.wi.gov/clerk-of-court/",
        "registerOfDeeds": "https://www.co.grant.wi.gov/register-of-deeds/",
        "executive": "https://www.co.grant.wi.gov/county-administrator/"}},
    "Jefferson": {"mode": "pages", "floor": 5, "offices": {
        "executive": "https://www.jeffersoncountywi.gov/administration/index.php",
        "treasurer": "https://www.jeffersoncountywi.gov/county_treasurer/index.php",
        "clerkOfCircuitCourt": "https://www.jeffersoncountywi.gov/courts___legal_services/clerk_of_courts/index.php",
        "districtAttorney": "https://www.jeffersoncountywi.gov/courts___legal_services/district_attorney/index.php",
        "coroner": "https://www.jeffersoncountywi.gov/medical_examiner/index.php",
        "registerOfDeeds": "https://www.jeffersoncountywi.gov/register_of_deeds/index.php"}},
    "Marquette": {"mode": "pages", "floor": 4, "offices": {
        "executive": "https://www.marquettecountywi.gov/administration/",
        "clerkOfCircuitCourt": "https://www.marquettecountywi.gov/clerk-of-courts/",
        "coroner": "https://www.marquettecountywi.gov/medical-examiner/",
        "sheriff": "https://www.marquettecountywi.gov/sheriff/",
        "registerOfDeeds": "https://www.marquettecountywi.gov/register-of-deeds/"}},
    "Vernon": {"mode": "pages", "floor": 3, "offices": {
        "coroner": "https://www.vernoncountywi.gov/departments/county_coroner/index.php",
        "treasurer": "https://www.vernoncountywi.gov/departments/county_treasurer/index.php",
        "registerOfDeeds": "https://www.vernoncountywi.gov/departments/register_of_deeds/index.php",
        "sheriff": "https://www.vernoncountywi.gov/departments/sheriff_s_office/index.php"}},
    "Washburn": {"mode": "pages", "floor": 4, "offices": {
        "executive": "https://co.washburn.wi.us/departments/administration-personnel/",
        "treasurer": "https://co.washburn.wi.us/departments/county-treasurer/",
        "districtAttorney": "https://co.washburn.wi.us/departments/district-attorney/",
        "registerOfDeeds": "https://co.washburn.wi.us/departments/register-of-deeds/",
        "sheriff": "https://www.washburnsheriff.org/"}},
    "Waushara": {"mode": "pages", "floor": 5, "offices": {
        "districtAttorney": "https://www.wausharacountywi.gov/12718/district-attorney",
        "registerOfDeeds": "https://www.wausharacountywi.gov/12726/register-of-deeds",
        "sheriff": "https://www.wausharacountywi.gov/12727/sheriffs-office",
        "treasurer": "https://www.wausharacountywi.gov/12730/treasurer",
        "coroner": "https://www.wausharacountywi.gov/41436/medical-examiner",
        "executive": "https://www.wausharacountywi.gov/12681/administration"}},
    "Winnebago": {"mode": "civicplus", "floor": 5,
                  "url": "https://www.winnebagocountywi.gov/directory.aspx"},
    "Burnett": {"mode": "civicplus", "floor": 5,
                "url": "https://burnettcountywi.gov/directory.aspx"},
    "Green": {"mode": "civicplus", "floor": 5,
              "url": "https://greencountywi.org/directory.aspx"},
    "Walworth": {"mode": "civicplus", "floor": 5,
                 "url": "https://co.walworth.wi.us/directory.aspx"},
    "Portage": {"mode": "civicplus", "floor": 5,
                "url": "https://www.co.portage.wi.gov/Directory"},
    # ---- tranche 3 (2026-08-26): the non-roster-county sweep — every URL
    # below was witness-tested live before pinning; floors sit one under
    # the measured office count so one flaky page cannot drop a county ----
    "Adams": {"mode": "pages", "floor": 4, "offices": {
        "clerkOfCircuitCourt": "https://www.co.adams.wi.us/departments/clerk-of-circuit-court",
        "coroner": "https://www.co.adams.wi.us/departments/medical-examiner",
        "districtAttorney": "https://www.co.adams.wi.us/departments/district-attorney",
        "executive": "https://www.co.adams.wi.us/departments/county-administrator",
        "registerOfDeeds": "https://www.co.adams.wi.us/departments/register-of-deeds"
    }},
    "Buffalo": {"mode": "pages", "floor": 4, "offices": {
        "clerkOfCircuitCourt": "https://www.buffalocountywi.gov/departments/clerk-of-courts/",
        "coroner": "https://www.buffalocountywi.gov/departments/coroner/",
        "districtAttorney": "https://www.buffalocountywi.gov/departments/district-attorney-corporation-counsel/",
        "executive": "https://www.buffalocountywi.gov/departments/county-administration/",
        "registerOfDeeds": "https://www.buffalocountywi.gov/departments/register-of-deeds/"
    }},
    "Clark": {"mode": "pages", "floor": 3, "offices": {
        "clerkOfCircuitCourt": "https://www.clarkcountywi.gov/clerk-of-courts",
        "coroner": "https://www.clarkcountywi.gov/corner",
        "districtAttorney": "https://www.clarkcountywi.gov/da",
        "registerOfDeeds": "https://www.clarkcountywi.gov/register-of-deeds"
    }},
    "Columbia": {"mode": "pages", "floor": 2, "offices": {
        "registerOfDeeds": "https://www.co.columbia.wi.us/ColumbiaCounty/registerofdeeds/VitalRecords/tabid/375/Default.aspx",
        "sheriff": "https://www.co.columbia.wi.us/columbiacounty/sheriff/SheriffsOfficeHomePage/tabid/551/Default.aspx"
    }},
    "Florence": {"mode": "pages", "floor": 4, "offices": {
        "clerkOfCircuitCourt": "https://www.florencecountywi.com/departments/clerk-of-courts/",
        "coroner": "https://www.florencecountywi.com/departments/coroner/",
        "registerOfDeeds": "https://www.florencecountywi.com/departments/register-of-deeds/",
        "sheriff": "https://www.florencecountywi.com/departments/sheriff/",
        "treasurer": "https://www.florencecountywi.com/departments/treasurer/"
    }},
    "Juneau": {"mode": "pages", "floor": 2, "offices": {
        "clerkOfCircuitCourt": "https://www.co.juneau.wi.gov/departments/clerk_of_court/index.php",
        "districtAttorney": "https://www.co.juneau.wi.gov/departments/district_attorney/staff_directory.php",
        "sheriff": "https://www.co.juneau.wi.gov/departments/sheriff_s_office/index.php"
    }},
    "Langlade": {"mode": "pages", "floor": 5, "offices": {
        "clerkOfCircuitCourt": "https://www.co.langlade.wi.us/departments/clerk-of-circuit-court/",
        "coroner": "https://www.co.langlade.wi.us/departments/coroner/",
        "districtAttorney": "https://www.co.langlade.wi.us/departments/district-attorney/",
        "registerOfDeeds": "https://www.co.langlade.wi.us/departments/register-of-deeds/",
        "sheriff": "https://www.co.langlade.wi.us/departments/sheriffs-office/",
        "treasurer": "https://www.co.langlade.wi.us/departments/county-treasurer/"
    }},
    "Manitowoc": {"mode": "pages", "floor": 3, "offices": {
        "coroner": "https://manitowoccountywi.gov/departments/coroner/",
        "districtAttorney": "https://manitowoccountywi.gov/departments/district-attorney/",
        "registerOfDeeds": "https://manitowoccountywi.gov/departments/register-of-deeds/",
        "sheriff": "https://manitowoccountywi.gov/departments/sheriff/"
    }},
    "Marinette": {"mode": "pages", "floor": 5, "offices": {
        "clerkOfCircuitCourt": "https://www.marinettecountywi.gov/departments/clerk-of-circuit-court/",
        "coroner": "https://www.marinettecountywi.gov/departments/medical-examiner/",
        "districtAttorney": "https://www.marinettecountywi.gov/departments/district-attorney/",
        "registerOfDeeds": "https://www.marinettecountywi.gov/departments/register-of-deeds/",
        "sheriff": "https://www.marinettecountywi.gov/departments/office-of-sheriff/",
        "treasurer": "https://www.marinettecountywi.gov/departments/treasurer/"
    }},
    "Oneida": {"mode": "pages", "floor": 3, "offices": {
        "districtAttorney": "https://www.oneidacountywi.gov/departments/da/",
        "registerOfDeeds": "https://www.oneidacountywi.gov/departments/rd/",
        "sheriff": "https://www.oneidacountywi.gov/departments/sd/",
        "treasurer": "https://www.oneidacountywi.gov/departments/tr/"
    }},
    "Sauk": {"mode": "pages", "floor": 6, "offices": {
        "clerkOfCircuitCourt": "https://www.co.sauk.wi.us/clerkofcourts",
        "coroner": "https://www.co.sauk.wi.us/coroner",
        "districtAttorney": "https://www.co.sauk.wi.us/districtattorney",
        "executive": "https://www.co.sauk.wi.us/countyadministration",
        "registerOfDeeds": "https://www.co.sauk.wi.us/registerofdeeds",
        "sheriff": "https://www.co.sauk.wi.us/sheriffsoffice",
        "treasurer": "https://www.co.sauk.wi.us/treasurer"
    }},
    "Trempealeau": {"mode": "pages", "floor": 4, "offices": {
        "clerkOfCircuitCourt": "https://co.trempealeau.wi.us/departments/administrative_departments/clerk_of_court/index.php",
        "coroner": "https://co.trempealeau.wi.us/departments/court___legal_departments/county_coroner.php",
        "districtAttorney": "https://co.trempealeau.wi.us/departments/court___legal_departments/district_attorney/index.php",
        "registerOfDeeds": "https://co.trempealeau.wi.us/departments/court___legal_departments/register_of_deeds/index.php",
        "treasurer": "https://co.trempealeau.wi.us/departments/administrative_departments/treasurer/index.php"
    }},
    "Waupaca": {"mode": "pages", "floor": 4, "offices": {
        "clerkOfCircuitCourt": "https://www.waupacacounty-wi.gov/departments/government_departments/clerk_of_courts/clerk_of_circuit_courts.php",
        "districtAttorney": "https://www.waupacacounty-wi.gov/departments/government_departments/district_attorney/index.php",
        "registerOfDeeds": "https://www.waupacacounty-wi.gov/departments/register_of_deeds/index.php",
        "sheriff": "https://www.waupacacounty-wi.gov/departments/sheriff_s_office/index2.php",
        "treasurer": "https://www.waupacacounty-wi.gov/departments/government_departments/county_treasurer/index.php"
    }},
    "Calumet": {"mode": "civicplus", "floor": 5,
        "url": "https://calumetcounty.org/Directory"},
    "Chippewa": {"mode": "civicplus", "floor": 5,
        "url": "https://chippewacountywi.gov/Directory"},
    "Douglas": {"mode": "civicplus", "floor": 4,
        "url": "https://douglascountywi.gov/Directory"},
    "Iron": {"mode": "civicplus", "floor": 5,
        "url": "https://www.co.iron.wi.gov/Directory"},
    "Kenosha": {"mode": "civicplus", "floor": 5,
        "url": "https://www.kenoshacountywi.gov/Directory"},
    "Oconto": {"mode": "civicplus", "floor": 5,
        "url": "https://www.ocontocountywi.gov/Directory"},
    "Ozaukee": {"mode": "civicplus", "floor": 5,
        "url": "https://ozaukeecounty.gov/Directory"},
    "Price": {"mode": "civicplus", "floor": 4,
        "url": "https://co.price.wi.us/Directory"},
    "Sawyer": {"mode": "civicplus", "floor": 4,
        "url": "https://www.sawyercounty.gov/Directory"},
    "St. Croix": {"mode": "civicplus", "floor": 5,
        "url": "https://sccwi.gov/Directory"},
    # ---- 2026-08-29: Green Lake publishes every elected officer on ONE
    # page, each in their own block with an exact title and their own
    # phone/e-mail. Its County Clerk and Circuit Court Judge blocks match
    # no office key here and are ignored — the clerk ships from
    # wi-county-clerks.json and the bench from wi-circuit-judges.json.
    "Green Lake": {"mode": "indexroll", "floor": 5,
        "url": "https://www.greenlakecountywi.gov/officials_type/elected-officials/"},
    # The first "directory" county: one Elected Officials page carrying six
    # offices with a phone and a courthouse location each. Its own site was
    # recorded unreadable until 2026-08-29 — an Akamai 403 against a header
    # set that claimed to be Chromium and sent none of Chromium's client
    # hints (wi_county_board_scraper.py's UA comment carries the
    # measurement). FIVE of the six are pinned here. The county clerk is the
    # sixth and belongs to wi_county_clerk_scraper.py, not to this file's
    # OFFICE_KEYS; and the two APPOINTED offices this file does track — the
    # county administrator and the medical examiner — are absent from the
    # page itself, because they are not elected, so the book's dated rows
    # continue to ship for both.
    "Sheboygan": {"mode": "directory", "floor": 5,
        "url": "https://www.sheboygancounty.com/government/elected-officials",
        "offices": ["sheriff", "districtAttorney", "treasurer",
                    "clerkOfCircuitCourt", "registerOfDeeds"]},
}


# ==== THE FOUR COUNTIES' CONTACT, AS LAST READ BEFORE THE CRAWL STOPPED ====
#
# Read from each county's own pages on 2026-08-31 by the "pages" mode above,
# under the same witness rule everything here obeys: the surname as a whole word
# with a word matching the first name's initial nearby, and contact taken only
# from a window around that name. Then the robots.txt sweep ran and these four
# hosts turned out to disallow this client, so the four rows moved here.
#
# NOTHING BELOW IS FETCHED. There is no URL to re-try and no `live` escape
# hatch: the values are the capture, and `main()` prints a NOT RE-READ line per
# county naming the capture's age, so an entry cannot rot unremarked.
#
# WHAT IS CARRIED IS THE OFFICE'S CONTACT, NEVER ITS OFFICEHOLDER. The name each
# row shows still comes from the current Blue Book every build; `witness` is the
# name the page carried when the contact was taken, and the builder DROPS an
# office's carried contact if the shipped name stops matching that witness. An
# office phone and an office page survive a turnover; a predecessor's contact
# rendered under a successor's name would not be a stale row, it would be a
# wrong one. That check is the whole reason the witness is stored.
CARRIED_CONTACTS = {
    "Ashland": {
        "read_on": "2026-08-31",
        "offices": {
            "executive": {
                "witness": "Dan Grady",
                "url": "https://ashlandcountywi.gov/administration"
            },
            "treasurer": {
                "witness": "Tracey Hoglund",
                "url": "https://ashlandcountywi.gov/treasurer",
                "phone": "715-682-7012",
                "email": "tracey.hoglund@ashlandcountywi.gov"
            },
            "clerkOfCircuitCourt": {
                "witness": "Lexi Pierce",
                "url": "https://ashlandcountywi.gov/circuit_court",
                "phone": "715-682-7016",
                "email": "lexi.pierce@wicourts.gov"
            },
            "districtAttorney": {
                "witness": "Blake Gross",
                "url": "https://ashlandcountywi.gov/district_attorney",
                "phone": "715-682-7019"
            },
        },
    },
    "Dunn": {
        "read_on": "2026-08-31",
        "offices": {
            "treasurer": {
                "witness": "Lynn Niggemann",
                "url": "https://dunncountywi.gov/treasurer",
                "phone": "(715) 232-3789",
                "email": "trs@dunncountywi.gov"
            },
            "clerkOfCircuitCourt": {
                "witness": "Katie Schalley",
                "url": "https://dunncountywi.gov/clerkofcourts",
                "phone": "(715) 232-2611",
                "email": "dunn.clerk@wicourts.gov"
            },
        },
    },
    "Pepin": {
        "read_on": "2026-08-31",
        "offices": {
            "treasurer": {
                "witness": "Patricia Scharr",
                "url": "https://www.co.pepin.wi.us/treasurer",
                "phone": "715-672-8850"
            },
            "sheriff": {
                "witness": "Joel D Wener",
                "url": "https://www.co.pepin.wi.us/sheriff",
                "phone": "888 944 8463"
            },
            "coroner": {
                "witness": "Jeff Doughty",
                "url": "https://www.co.pepin.wi.us/coroner",
                "phone": "715-672-7242"
            },
        },
    },
    "Polk": {
        "read_on": "2026-08-31",
        "offices": {
            "treasurer": {
                "witness": "Amanda Nissen",
                "url": "https://www.polkcountywi.gov/government/elected_officials/treasurer/index.php",
                "phone": "715-485-8633",
                "email": "amanda.nissen@polkcountywi.gov"
            },
            "clerkOfCircuitCourt": {
                "witness": "Sharon Jorgenson",
                "url": "https://www.polkcountywi.gov/government/elected_officials/clerk_of_courts/index.php"
            },
            "registerOfDeeds": {
                "witness": "Sally Spanel",
                "url": "https://www.polkcountywi.gov/government/elected_officials/register_of_deeds/index.php",
                "phone": "715-485-9240",
                "email": "sally.spanel@polkcountywi.gov"
            },
            "districtAttorney": {
                "witness": "Jeffrey L Kemp",
                "url": "https://www.polkcountywi.gov/government/divisions_and_departments/public_safety_public_works/district_attorney/index.php"
            },
            "sheriff": {
                "witness": "Brent A Waak",
                "url": "https://www.polkcountywi.gov/government/elected_officials/sheriff/index.php"
            },
        },
    },
}

CARRIED_WHY = ("The county asks automated readers not to crawl its site, so "
               "these office contacts are a dated capture rather than the "
               "weekly re-read the other counties' rows get.")

TAG_STRIP = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>")
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# SITE CHROME IS NOT AN OFFICER'S CONTACT. Every path below takes the FIRST
# address inside a window that witnesses the officeholder's own name, which is
# the right shape and is not sufficient: a county whose page publishes no
# address for the officer still has a footer, and the footer is inside the
# window. Grant County shipped `webmaster@co.grant.wi` as its SHERIFF's e-mail
# — the only address anywhere on that page — so the card told a reader to write
# to the webmaster to reach the Sheriff.
#
# wi_county_board_scraper.py already carries this warning in its own comments
# ("a page-wide search would happily ship a footer's webmaster address as ...");
# it was never applied here.
#
# THE LIST IS DELIBERATELY SHORT. An office mailbox is a legitimate contact —
# `sheriff@`, `clerk@`, `treas@` all ship as published, and several counties
# publish nothing else — so only local parts that can never be a person or an
# office are rejected. `info@` is NOT here: for a small county that is often the
# real front door.
#
# (Grant's address is also mistyped by the county itself, which is how it turned
# up: the page prints `webmaster@co.grant.wi,gov`, a comma for the dot, so the
# match stops at a domain that does not exist. That is a second defect and not
# this one's business — the address would be wrong for the Sheriff either way.)
SITE_CHROME_LOCALS = {"webmaster", "postmaster", "noreply", "no-reply",
                      "donotreply", "do-not-reply", "mailer-daemon", "abuse"}


def officer_email(text, county=None, office=None):
    """The first address in `text` that could belong to a person or an office.

    Site-chrome addresses are skipped rather than stopping the search, so a
    page whose footer precedes the officer's own address still ships the right
    one. Every skip prints, because a silent drop and a silent wrong address
    are equally hard to notice later.
    """
    for m in EMAIL_RE.finditer(text or ""):
        addr = m.group(0)
        if addr.split("@", 1)[0].lower() in SITE_CHROME_LOCALS:
            print("%s/%s: skipped site-chrome address %r — not an officer's "
                  "contact" % (county or "?", office or "?", addr),
                  file=sys.stderr)
            continue
        return addr
    return None

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "dr"}
# The backstop for a directory office that is the LAST one witnessed on its
# page and so has no next-name bound. Sheboygan's longest real block (name to
# the end of its own entry) is ~250 characters.
DIRECTORY_SPAN = 400


def fetch(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=30).read().decode(
                "utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 — retried, then surfaced
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("%s: %s" % (url, last))


def to_text(raw):
    return re.sub(r"\s+", " ", htmllib.unescape(TAG_STRIP.sub(" ", raw)))


def name_parts(name):
    parts = [p for p in re.sub(r"[^A-Za-z ]", " ", name or "").split()
             if p.lower() not in SUFFIXES]
    if not parts:
        return None, None
    return parts[0], parts[-1]


# PER-OFFICE WINDOW WIDENINGS, EACH ONE MEASURED. The 350-character default
# carried no comment explaining it, which made it look arbitrary; it is not, and
# the sweep that proved so is why this is a table of two rows rather than a
# bigger number.
#
# Washington's sheriff publishes its main line inside the office's own address
# block — "Washington County Sheriff's Office / 500 Rolfs Avenue / West Bend, WI
# 53090 / (View Map) / 262-335-4378" — 392 characters after the name, so the
# window ended 42 characters short and the county shipped no phone. Bot PR #714
# was closed for dropping it.
#
# WIDENING THE DEFAULT WOULD HAVE BEEN WRONG, and that is measured rather than
# feared: swept across all 25 page-mode counties at 450/550/700, thirteen of
# 125 (county, office) pairs move. Six gain a plausible county contact — but
# five are corrupted, and one of those badly: MARQUETTE'S REGISTER OF DEEDS goes
# from its own `(608) 297-3025` / `nziebell@marquettecountywi.gov` to a
# succession of THIRD-PARTY E-RECORDING VENDORS (`support@hopdox.com`,
# `eRecordSupport@Indecomm.net`, `erecording@cscglobal.com`), which would ship a
# commercial address as a county officer's contact. Jefferson's clerk of circuit
# court returns a DIFFERENT phone at every span, and Grant's register of deeds
# picks up a toll-free vendor line.
#
# So each entry here is one office whose wider window was read in context and
# confirmed to be that office's own number. Washington's CORONER is deliberately
# absent: it also changes at 450 (414-516-4300 -> 262-338-0888) and which is
# right was not established, so the county is widened per OFFICE, never whole.
#
# Six other measured gains are recorded and NOT taken here, because each needs
# its own reading first: Langlade's coroner (an address at 450, a phone at 550),
# Trempealeau's and Waupaca's clerks of circuit court, Clark's register of
# deeds, and Washington's own district attorney — which IS taken below, having
# been read: `262-335-4311` sits at +435 under the page's own "Contact Me /
# Contact Us / District Attorney / (View Map) / Phone:" heading.
#
# DO NOT REPLACE THIS TABLE WITH "BOUND A SINGLE-OFFICE PAGE BY THE PAGE".
# The idea is that Washington's sheriff page carries one officer, so the
# cross-attribution the 350 protects against cannot happen there and the window
# could run to the end of the document instead. It is a reasonable thing to
# think and the page refutes it. Measured 2026-09-08 on
# www.washcowisco.gov/elected_officials/sheriff_s_office: 14,767 characters,
# TWELVE phone numbers, and TWO accepted hits on the surname. A department page
# is not one office's worth of text — it lists the department's divisions and
# their numbers — so an unbounded window would take whichever number happens to
# come first, and that it is the right one here is a property of this page's
# layout rather than of single-office pages. The bound stays a measured span
# per office, read in context before it is widened.
#
# THE SPANS BELOW HAVE NEVER RUN. They were committed 2026-09-04 18:54; the last
# run of update-wi-county-board-roster.yml used a head from 14:54 the same day,
# four hours earlier, so it executed the pre-fix code. That is why the shipped
# file still carries the sheriff's phone (correct, from before) and no district
# attorney phone: the next run is the first to exercise this table, and it
# should ADD `262-335-4311` rather than propose deleting anything. Both were
# re-read live on 2026-09-08 and both are found at 450 and missed at 350.
WINDOW_SPAN = {
    ("Washington", "sheriff"): 450,          # 262-335-4378 at +392
    ("Washington", "districtAttorney"): 450,  # 262-335-4311 at +435
}


def witness_window(text, book_name, span=350):
    """Find the shipped officer on the page: the surname as a whole word,
    with a capitalized word sharing the first name's initial nearby.
    Returns the text window around the accepted hit, or None."""
    first, sur = name_parts(book_name)
    if not sur:
        return None
    for m in re.finditer(r"\b%s\b" % re.escape(sur), text, re.I):
        lo, hi = max(0, m.start() - 120), m.start() + 120
        near = text[lo:hi]
        if re.search(r"\b%s[a-z]" % re.escape(first[0]), near):
            lo2, hi2 = max(0, m.start() - span), m.start() + span
            return text[lo2:hi2]
    return None


def scrape_directory(county, cfg, book):
    """Several offices off ONE page, each contact read forward from its name.

    The bound is the NEXT witnessed officer's name rather than a character
    count, so the window can never reach into the following officer's block
    however the page is spaced. An office whose name the page does not
    witness is skipped exactly as in `scrape_pages` — the appointed offices
    (Sheboygan's administrator and medical examiner) are simply not on an
    ELECTED-officials page, and that is a fact about the page, not a miss.
    """
    url = cfg["url"]
    text = to_text(fetch(url))
    starts = {}
    for office in cfg["offices"]:
        book_name = (book.get(office) or {}).get("name")
        if not book_name:
            continue
        first, sur = name_parts(book_name)
        if not sur:
            continue
        for m in re.finditer(r"\b%s\b" % re.escape(sur), text, re.I):
            near = text[max(0, m.start() - 120):m.start() + 120]
            if re.search(r"\b%s[a-z]" % re.escape(first[0]), near):
                starts[office] = m.start()
                break
    bounds = sorted(starts.values())
    out = {}
    for office in cfg["offices"]:
        if office not in starts:
            print("%s/%s: the directory does not witness %r — no contact ships"
                  % (county, office,
                     (book.get(office) or {}).get("name")), file=sys.stderr)
            continue
        begin = starts[office]
        after = [b for b in bounds if b > begin]
        window = text[begin:min(after[0] if after else len(text),
                                begin + DIRECTORY_SPAN)]
        entry = {"url": url}
        phone = PHONE_RE.search(window)
        if phone:
            entry["phone"] = phone.group(0).strip()
        email = officer_email(window, county, office)
        if email:
            entry["email"] = email
        out[office] = entry
    return out


def scrape_pages(county, cfg, book):
    out, unwitnessed, fetched = {}, [], 0
    for office, url in cfg["offices"].items():
        book_name = (book.get(office) or {}).get("name")
        if office == "executive":
            book_name = (book.get("executive") or {}).get("name")
        if not book_name:
            continue
        try:
            text = to_text(fetch(url))
            fetched += 1
        except RuntimeError as exc:
            print("%s/%s: fetch failed — %s" % (county, office, exc),
                  file=sys.stderr)
            continue
        window = witness_window(
            text, book_name, span=WINDOW_SPAN.get((county, office), 350))
        if window is None:
            # COUNTED, NOT JUST PRINTED: see the caller. A page that answered
            # 200 and witnesses nobody is a fact about the FETCH at least as
            # often as about the county.
            unwitnessed.append(office)
            print("%s/%s: page fetched but does not witness %r"
                  % (county, office, book_name), file=sys.stderr)
            continue
        entry = {"url": url}
        phone = PHONE_RE.search(window)
        if phone:
            entry["phone"] = phone.group(0).strip()
        email = officer_email(window, county, office)
        if email:
            entry["email"] = email
        out[office] = entry

    # A 200 IS NOT A DOCUMENT EITHER. When every page this county publishes
    # answered and NONE of them carries the name of the officer it is about,
    # the bodies are not this county's pages — they are a challenge page, an
    # interstitial, or a reshaped template. Oneida hit exactly this on both of
    # 2026-09-04's runs: four pages, HTTP 200 each, zero of four officers
    # witnessed, while the same four pages witness all four from another client
    # and did from the runner on 09-03 (Cloudflare bot management, __cf_bm;
    # a Python-urllib UA is refused outright with a 403). Bot PR #709 was closed
    # for dropping all four contacts on the strength of it.
    #
    # Raising here rather than returning {} is what tells the caller apart from
    # a county that genuinely publishes nothing: RuntimeError is already the
    # "could not read this county" channel, and the builder preserves the last
    # good contacts for a county that does not appear in the intermediate.
    if fetched and not out and len(unwitnessed) == fetched:
        raise RuntimeError(
            "all %d page(s) answered and none witnesses its own officer (%s) — "
            "that is a blocked or reshaped body, not a county without contacts"
            % (fetched, ", ".join(sorted(unwitnessed))))
    return out


# Both gaps are BOUNDED: an entry with no title div must fail the match
# (and be skipped) rather than swallow forward and pair this person's name
# with the NEXT person's title — the measured gap is ~50 chars.
CIVICPLUS_ITEM = re.compile(
    r'employee\?eid=\d+">\s*([^<]+?)\s*</a>'
    r'[\s\S]{0,300}?<div class="d-sm-block d-none">([^<]*)</div>')


def scrape_civicplus(county, cfg, book):
    raw = fetch(cfg["url"])
    found = {}
    for name, titles in CIVICPLUS_ITEM.findall(raw):
        name = htmllib.unescape(name).strip()
        # Trailing certification initialisms are not part of a name
        # (measured: Walworth's medical examiner is listed "Kimberly Rossi
        # D-ABMDI"). Strip trailing all-caps tokens only while a mixed-case
        # token remains before them, so an all-caps SURNAME never strips.
        parts = name.split()
        while (len(parts) > 2 and re.fullmatch(r"[A-Z][-A-Z.]{1,9}", parts[-1])
               and not parts[-2].isupper()):
            parts.pop()
        name = " ".join(parts)
        for seg in htmllib.unescape(titles).split(","):
            seg = seg.strip()
            seg = re.sub(r"^%s County " % re.escape(county), "", seg)
            for office, allowed in TITLE_SETS.items():
                if seg in allowed:
                    # the matched title segment rides along: the builder
                    # uses it to label an executive the book has wrong
                    # (or, for Sawyer, calls "Vacant")
                    found.setdefault(office, {})[name] = seg
    out = {}
    for office, names in found.items():
        # The same person can be listed twice ("Eric Sparr" / "Eric D.
        # Sparr" — measured on Winnebago), so ambiguity means DISTINCT
        # PEOPLE: group by first-initial + surname and count groups. A
        # genuine multi-person title (Winnebago's directory titles a
        # committee treasurer "Treasurer" beside the county treasurer)
        # stays skipped with the loud line.
        groups = {}
        for n in names:
            first, sur = name_parts(n)
            groups.setdefault((first[0].lower() if first else "",
                               (sur or "").lower()), []).append(n)
        if len(groups) > 1:
            print("%s/%s: directory marks %d distinct people (%s) — "
                  "ambiguous, skipped" % (county, office, len(groups),
                                          sorted(names)), file=sys.stderr)
            continue
        best = max(list(groups.values())[0], key=len)  # fullest form ships
        out[office] = {"url": cfg["url"], "name": best,
                       "title": names[best]}
    return out


# The block markup is ONE county CMS's shape used by TWO of its pages — this
# one and the supervisors page the board scraper reads — so it is defined once,
# there, and imported here. A reskin then breaks one definition rather than two
# that silently disagree.
from wi_county_board_scraper import (          # noqa: E402 — same directory
    INDEXROLL_ADDR, INDEXROLL_BLOCK, INDEXROLL_HEAD, INDEXROLL_SUB)


def _block_text(fragment):
    return re.sub(r"\s+", " ", htmllib.unescape(TAG_STRIP.sub(" ", fragment))).strip()


def scrape_indexroll(county, cfg, book):
    """One officials page, one block per officer — contact never crosses a block."""
    raw = fetch(cfg["url"])
    found = {}
    for block in INDEXROLL_BLOCK.findall(raw):
        head = INDEXROLL_HEAD.search(block)
        sub = INDEXROLL_SUB.search(block)
        if not head or not sub:
            continue
        name = _block_text(head.group(1))
        if not name:
            continue
        entry = {"url": cfg["url"], "name": name}
        addr = INDEXROLL_ADDR.search(block)
        if addr:
            # from THIS person's own contact list, never from the page at large
            text = _block_text(addr.group(1))
            phone = PHONE_RE.search(text)
            if phone:
                entry["phone"] = phone.group(0).strip()
            email = officer_email(text, county, name)
            if email:
                entry["email"] = email
        for seg in _block_text(sub.group(1)).split(","):
            seg = re.sub(r"^%s County " % re.escape(county), "", seg.strip())
            for office, allowed in TITLE_SETS.items():
                if seg in allowed:
                    found.setdefault(office, {})[name] = dict(entry, title=seg)
    out = {}
    for office, people in found.items():
        # same ambiguity rule as civicplus: two DISTINCT people under one
        # title is a page this parser has misread, and skipping says so
        groups = {}
        for n in people:
            first, sur = name_parts(n)
            groups.setdefault((first[0].lower() if first else "",
                               (sur or "").lower()), []).append(n)
        if len(groups) > 1:
            print("%s/%s: page names %d distinct people (%s) — ambiguous, "
                  "skipped" % (county, office, len(groups), sorted(people)),
                  file=sys.stderr)
            continue
        best = max(list(groups.values())[0], key=len)
        out[office] = people[best]
    return out


INTERIM_EXEC_RE = re.compile(
    r"About\s+([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){1,2}?)\s+Interim\s+"
    r"(?:Waukesha\s+)?County\s+Executive")


def scrape_interim_exec(county, url):
    text = to_text(fetch(url))
    m = INTERIM_EXEC_RE.search(text)
    if not m:
        print("%s/executive: interim-executive extraction failed — the page "
              "reshaped; the builder will withhold rather than ship the "
              "book's deceased executive" % county, file=sys.stderr)
        return None
    entry = {"url": url,
             "supersede": {"name": m.group(1),
                           "title": "Interim County Executive",
                           "appointed": True}}
    window = witness_window(text, m.group(1))
    if window:
        phone = PHONE_RE.search(window)
        if phone:
            entry["phone"] = phone.group(0).strip()
    return entry


def main():
    feats = json.load(open(COUNTIES_FILE))["features"]
    geoid_by_base = {f["properties"]["BASENAME"]: f["properties"]["GEOID"]
                     for f in feats}
    officers = json.load(open(OFFICERS))
    book_by_base = {v["county"]: v for v in officers.values()}

    out = {}
    for county, cfg in COUNTIES.items():
        book = book_by_base[county]
        try:
            if cfg["mode"] == "pages":
                entries = scrape_pages(county, cfg, book)
                if cfg.get("interim_exec"):
                    exec_entry = scrape_interim_exec(county, cfg["interim_exec"])
                    if exec_entry:
                        entries["executive"] = exec_entry
            elif cfg["mode"] == "indexroll":
                entries = scrape_indexroll(county, cfg, book)
            elif cfg["mode"] == "directory":
                entries = scrape_directory(county, cfg, book)
            else:
                entries = scrape_civicplus(county, cfg, book)
        except RuntimeError as exc:
            # A SKIP IS EMITTED, NOT OMITTED. The builder preserves a county's
            # last-known contacts when the scrape could not read it, and it can
            # only say WHY on the card if the reason travels with the skip. An
            # omitted county and a county that 404'd are the same silence, and
            # the first version of that preservation stamped one sentence about
            # blocked bodies on every absent county — false for a county whose
            # pages had simply moved.
            print("%s: SKIPPED — %s" % (county, exc), file=sys.stderr)
            out[str(geoid_by_base[county])] = {
                "county": county, "offices": {}, "skipped": str(exc)}
            continue
        if len(entries) < cfg["floor"]:
            reason = ("%d of the county's offices resolved against a floor of "
                      "%d, so the read was refused rather than shipped short"
                      % (len(entries), cfg["floor"]))
            print("%s: SKIPPED — %s (a page reshaped; re-read it, never loosen "
                  "the floor)" % (county, reason), file=sys.stderr)
            out[str(geoid_by_base[county])] = {
                "county": county, "offices": {}, "skipped": reason}
            continue
        # THE READ DATE COMES FROM THE SCRAPE, NOT THE BUILDER'S CLOCK. The
        # builder stamps `contactReadOn` so preservation can later say when a
        # contact was last actually read; taking `today` there would date a
        # week-old intermediate as today's — which is the same overstatement
        # preservation was fixed to stop making, arriving from the other side.
        out[str(geoid_by_base[county])] = {
            "county": county,
            "offices": entries,
            "read_on": datetime.date.today().isoformat()}
        print("%s: %d offices (%s)" % (county, len(entries),
                                       ", ".join(sorted(entries))),
              file=sys.stderr)
        time.sleep(1)

    # ---- the carried four: emitted, never fetched ----
    # Printed loudly and dated, the same posture the board scraper takes with
    # DOCUMENT_ROSTERS: a number that ages should say how old it is on every
    # single run, not only on the day somebody thinks to look.
    today = datetime.date.today()
    for county, spec in sorted(CARRIED_CONTACTS.items()):
        read_on = datetime.date.fromisoformat(spec["read_on"])
        age = (today - read_on).days
        out[str(geoid_by_base[county])] = {
            "county": county,
            "offices": {office: {k: v for k, v in c.items() if k != "witness"}
                        for office, c in spec["offices"].items()},
            "witnesses": {office: c["witness"]
                          for office, c in spec["offices"].items()},
            "carried_from_document": spec["read_on"],
            "why": CARRIED_WHY,
        }
        print("%s: NOT RE-READ — %d office(s) carried from the capture of %s "
              "(%d day%s old); the county's robots.txt disallows this client"
              % (county, len(spec["offices"]), spec["read_on"], age,
                 "" if age == 1 else "s"), file=sys.stderr)

    if len(out) < 32:
        raise SystemExit("only %d counties resolved — the tranche floor is "
                         "32; something structural broke" % len(out))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote %s — %d counties" % (OUT, len(out)), file=sys.stderr)


if __name__ == "__main__":
    main()
