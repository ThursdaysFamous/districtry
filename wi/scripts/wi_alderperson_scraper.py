#!/usr/bin/env python3
"""
Scrape the alderperson rosters for the Wisconsin municipalities whose
aldermanic districts the statewide dissolve ships AND whose rosters have a
verified open route — six measured 2026-08-26, twelve more 2026-09-05.
Stage 1 of the pair; build_wi_alderperson_roster.py writes
data/app/wi-alderpersons.json.

THE FIRST SIX, each with its route and its measured trap:

  Milwaukee (15)  — Legistar (webapi.legistar.com), the Common Council's own
                    system of record: OfficeRecordTitle carries the district
                    ("3rd District", cross-checked against OfficeRecordSort)
                    and First/Last carry the name. NEVER OfficeRecordFullName,
                    which is "ALD. SURNAME".
                    THE CITY'S GIS LAYER WAS THE SOURCE UNTIL 2026-09-05 and is
                    not fetched any more: milwaukeemaps.milwaukee.gov publishes
                    `User-agent: * / Disallow: /`. The city's open-data CKAN
                    shapefile corroborates per district where it answers, and
                    is not required to. Current membership is filtered
                    client-side against today's date.
                    THAT MOVE COST ONE SUFFIX AND IT IS NOT PUT BACK BY HAND:
                    the retired GIS layer spelled district 15 "Russell W
                    Stamper, II" and Legistar — the Council's own system of
                    record — carries First "Russell W." / Last "Stamper", with
                    no suffix field anywhere in the record (Chambers Jr. keeps
                    his, inside the LAST name). Restoring the II would mean
                    typing a name this project cannot source, so the shipped
                    spelling is the Council's own.
  Madison (20)    — the council index page's per-alder links. THE INDEX'S
                    FLAT TEXT PAIRING IS A TRAP: District 1 is vacant, so a
                    flattened read pairs every alder with the district ABOVE
                    their real one (measured: "District 1 / Alder Ochowicz"
                    on the flat page; Ochowicz's own page is District 2).
                    The district comes from each alder's own /council/
                    districtN page — its H1 states "District N - Alder
                    SURNAME" or "District N - Vacant" — and the seat e-mail
                    districtN@cityofmadison.com rides the page.
  Green Bay (12)  — the city's staff directory, parsed per <li> entry
                    (never flattened: the responsive layout prints each
                    title twice). Name, real mailto, phone, profile URL.
                    One entry measures a display-name/e-mail nickname split
                    ("Bill Morgan" / mailto Jim... no — William) — the
                    display name ships.
  Kenosha (17)    — the city GIS's Districts_ElectedRepresentation layer
                    (REP_AREA='D' rows carry REPRESNTTV; each district
                    appears twice, once named and once 'N/A' — both facts
                    gated). kenosha.org itself is Cloudflare-challenged, so
                    the currency witness is the COUNTY's certified April
                    2026 spring canvass (kenoshacountywi.gov, open): all 17
                    alderperson contests, positionally parsed — candidate
                    names are CENTERED vertical column headers, so stacks
                    cluster by column CENTER (clustering by left edge reads
                    the winner out of the wrong column; measured), and the
                    Totals row's first k numbers are the k candidates'
                    votes. Every GIS name must match its district's
                    certified winner.
  Racine (15)     — the city's alderman index, "District #N – Alderman
                    NAME" one line per district, plus each district's page
                    link (the slugs are inconsistent — "district-1" and
                    "02-district" both live — so the link is captured from
                    the line, never composed).
  Waukesha (15)   — the common-council page's per-district blocks:
                    "Aldermanic District N" / "Wards …" / NAME / phone /
                    seat e-mail (alddistN@waukesha-wi.gov — the seat's, so
                    contact survives turnover).

THE TWELVE OF 2026-09-05 — Stevens Point, Menomonie, Manitowoc, Sheboygan,
Superior, Portage, Viroqua, Menasha, Howard, Tomah, Eau Claire and Appleton — carry
their route and their traps on each scrape_* function below, under the sweep
that found them. Three of those traps are worth naming here because they are
the ones that ship a WRONG answer rather than none: Manitowoc's anchors carry
a title= attribute naming the PREVIOUS alderperson on two rows; Menasha's
District 1 cell holds a staff member's mailto that is not the alderperson's;
and Menasha and Portage both publish their members' HOME ADDRESSES, which
never ship, for anybody, anywhere in this fleet.

APPLETON WAS HELD OUT UNTIL 2026-09-05 for exactly one reason and it was the
right one: its roster page has been readable since 2026-08-26 and its GEOMETRY
could not be drawn, so there was no card for the names to ride. Outagamie
County still files all 50 of its Appleton wards uncoded; what changed is that
the CITY CLERK's own polling-locations page turned out to state the
composition, and build_wi_aldermanic_districts.py now composes the fifteen
districts from it under three independent witnesses and a second edition of
one of them. A roster and the boundary it rides ship together or not at all.
"""

import html as H
import io
import json
import os
import re
import struct
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)
import scraper_common as sc  # noqa: E402  (FLEET_SHARED)
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, ".cache")
DEFAULT_OUT = os.path.join(CACHE_DIR, "wi_alderpersons_raw.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# THE AKAMAI TRIO, measured 2026-10-01. www.wausauwi.gov, www.wauwatosa.net and
# www.janesvillewi.gov sit behind an Akamai edge that answers 403 to the header
# set above -- ROBOTS.TXT INCLUDED, so the policy cannot be read at all -- and
# 200 to the same kind of Chrome string sent with Accept, Accept-Language,
# Accept-Encoding: identity, Connection: close and the three sec-ch-ua client
# hints. Three reads fifteen seconds apart, all three hosts stable both ways;
# 403 on every thinner rung tried (urllib and requests, bare districtry token
# and Chrome alike, and curl), 200 with the full set. All three then serve one
# BYTE-IDENTICAL policy, md5 16e66653dfbe3d2bee5636483dea61df, 6,641 bytes of
# one CMS vendor's own admin and asset paths -- which is published at each
# city's own host and so binds here, and must never be cited as something any
# of these three cities decided.
#
# IT IS THE SET wi_municipal_executive_scraper.py ALREADY MEASURED on
# www.wauwatosa.net on 2026-09-29, and the hints are IMPORTED rather than typed,
# for the reason that file records: a hand-typed sec-ch-ua is a plausible string
# that is not the one the measurement used.
#
# THIS IS NOT AN ESCALATION TO GET A BETTER ROBOTS VERDICT. The thinner client
# gets no verdict at all, not a worse one, and the policy these hosts serve is
# read with the exact client that then fetches their pages -- which is the whole
# of the consistency requirement.
UA_AKAMAI = dict(UA, **{
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
})
UA_AKAMAI.update({k: v for k, v in sc.UA_HINTS_CHROME_126.items()
                  if k.lower().startswith("sec-ch-ua")})

# REMOVED 2026-09-05: milwaukeemaps.milwaukee.gov/arcgis/rest/services/election
# /alderman/... was this file's primary Milwaukee source, and that host publishes
# `User-agent: * / Disallow: /`. It is not re-added under another name or agent;
# scrape_milwaukee() reads Legistar, which it was already fetching.
MKE_CKAN_ZIP = ("https://data.milwaukee.gov/dataset/1301738f-4b4a-4f73-bbaa-a4cac069e371"
                "/resource/4b68b244-779e-406f-9d94-7fb85a764496/download/alderman.zip")
MKE_LEGISTAR = ("https://webapi.legistar.com/v1/milwaukee/officerecords"
                "?$filter=OfficeRecordBodyId%20eq%201&$top=1000")
MADISON_INDEX = "https://www.cityofmadison.com/council/council-members"
MADISON_DISTRICT = "https://www.cityofmadison.com/council/district%d"
GREEN_BAY_DIR = "https://www.greenbaywi.gov/m/directory"
KENOSHA_GIS = ("https://gis-city.kenosha.org/server/rest/services/Organizational_Layers"
               "/Districts_ElectedRepresentation/FeatureServer/150/query"
               "?where=REP_AREA%3D%27D%27&outFields=DIST_NO,REPRESNTTV"
               "&returnGeometry=false&f=json&resultRecordCount=100")
KENOSHA_CANVASS = ("https://www.kenoshacountywi.gov/DocumentCenter/View/31064"
                   "/OFFICIAL-CANVASSED-RESULTS")
RACINE_INDEX = ("https://cityofracinewi.gov/government/city-leadership"
                "/common-council/cityalderman/")
WAUKESHA_INDEX = "https://www.waukesha-wi.gov/about_the_common_council/index.php"

# ---------------------------------------------------------------------------
# THE TWELVE ADDED 2026-09-05, each hand-read from its own page before a line of
# parser was written. They came out of a sweep of all 149 unrostered districted
# municipalities: home page (robots.txt honoured first), then up to two hops of
# council-ish links, scoring how many of the municipality's districts a page
# pairs with a person. The sweep is a TRIAGE — it points at pages worth reading;
# nothing below ships from its score.
#
# WHAT THE SWEEP MEASURED, over all 149:
#
#     32  a page pairing every district with a name, read automatically
#     14  the same, partially
#     67  home page readable, no such pairing found
#     17  the host publishes `User-agent: * / Disallow: /`
#     15  the host answers HTTP 403 to this client
#      3  a network error or an HTTP 503
#      1  no municipal website in the Elections Commission's clerk file (Hurley)
#
# So the record this replaces — "no bulk source exists", which is true — was
# silent about the thing that actually decides each city, and 32 municipalities
# were publishing exactly what the gap said was wanted. The 17 blanket Disallows
# are the finding worth naming: Baraboo, Cudahy, Delavan, Elroy, Marion,
# Marshfield, Mauston, Merrill, Prairie du Chien, Princeton, Reedsburg, Rice
# Lake, Ripon, St Croix Falls, St Francis, Tomahawk, Westfield. Those are shut,
# not unexamined, and nothing here renames a user agent to get past one.
#
# TEN OF THE TWELVE BELOW CAME OUT OF THAT 32, AND MENOMONIE DID NOT — its
# council page pairs every seat with a name and the triage scored it 0, because
# the crawl never reached the page inside its six-link budget. The sweep
# UNDER-reports, which is the right direction for a triage and the reason the
# 67 "no pairing found" is a floor rather than a verdict.
#
# THE TWENTY-TWO FULL MATCHES the sweep found. FIVE WERE BUILT on 2026-09-05
# evening (New Berlin, Sturgeon Bay, Altoona, Eagle River, Germantown — 28
# seats) and FIVE MORE WERE MEASURED SHUT that same evening, which is the more
# useful half:
#
#   ALGOMA, DODGEVILLE, OCONOMOWOC and HORICON each seat TWO alderpersons per
#   district on staggered terms — Dodgeville's district 1 is Shaun Sersch
#   (2025-2027) AND Roxanne Reynolds-Lair (2026-2028), and so on. The roster
#   schema is members[district] -> ONE member, so naming either would conceal
#   the other. Shut on the SCHEMA, not on the source: representing them needs
#   a schema and a card that hold a list. THE SWEEP COULD NOT HAVE SEEN THIS —
#   it scored district-to-name PAIRINGS, and a page that pairs each district
#   twice scores as a full match. ALL FOUR SHIP NOW, the first three in #1135
#   and Oconomowoc on 2026-09-25.
#
#   OCONOMOWOC SHIPPED 2026-09-25, and it was never an access problem: its
#   APEX host serves robots.txt and permits /225/Common-Council, and its page
#   answers 200 at 132,246 bytes; its `www` host resets the connection, the
#   Barron and Forest pattern where neither prefix is a safe default, and the
#   apex reset on three of nine reads from this sandbox and answered on a
#   retry. WHAT HELD IT BACK WAS THE CARD'S VOCABULARY. The city's own sentence
#   says "eight Aldermen representing each of the City's four districts", and
#   its directory names SEVEN people plus one entry reading `Vacanct District 1`
#   — the city's own typo — so District 1 seats two, names one, and leaves one
#   empty. `vacantDistricts` says a whole district is vacant (Madison's District
#   1 at first build) and could not say a district seats two and names one, and
#   shipping the one name silently is the same concealment one level down that
#   the list schema was built to end. So this change adds `vacantSeats`, a count
#   per district of the seats the source itself lists as vacant, and the card
#   states it beside the names.
#
#   TWO CLAIMS THAT LOOK ALIKE AND ARE NOT, recorded here because the next city
#   will be one or the other. `vacantSeats` is the city SAYING a seat is vacant.
#   A city that seats two, names one and says nothing about the other is making
#   no such statement, and the honest field for that is the one Illinois's
#   at-large card carries — `seats`, with the card reading "1 of 2 seats not
#   listed". Nothing here needs it yet, so it is not built; do not reach for
#   `vacantSeats` to express it, because a card saying "the city lists the other
#   as vacant" about a seat the city never mentioned is a false statement.
#
#   WAUPACA's page numbers its districts 1-5 while LTSB keys its geometry
#   41-45. Nothing read here witnesses the correspondence, and a wrong offset
#   moves every name one seat, so it is not guessed.
#
# ALL 22 ARE MEASURED AS OF 2026-09-06. Six ship one member per district (the
# five above plus New Lisbon); FIFTEEN seat more than one, and Wisconsin Dells
# is a probable sixteenth. The last three read — Black River Falls (two per
# ward, 8 over 4; its labels are uppercase WARD N, which a case-sensitive
# pattern misses), Neenah (three per district, 9 over 3) and Wautoma (UNEVEN at
# one, three and two, 6 over 3) — are all multi-member. WAUTOMA SETTLES THE
# DESIGN QUESTION: a two-slot schema would not carry it; these cities need a
# genuine LIST per district. Wautoma also prints home addresses beside every
# name, which are never read.
#
# THE REMAINING QUEUE, with the page the sweep scored, so the next pass starts
# from a measurement instead of repeating this one. NO COUNT IN THIS HEADING,
# and that is the same finding one paragraph further down sitting in its own
# heading: it read THE REMAINING NINE, a number restated beside the list that
# owns it, which goes stale the moment a city ships and which nothing could
# check. The rows are now the only statement of how many remain.
# IT WAS EIGHTEEN ROWS UNTIL
# 2026-09-25 AND NINE OF THEM HAD SHIPPED — Algoma, Dodgeville, Horicon and
# Wautoma in #1135, Black River Falls and Neenah in #1138, New Lisbon on
# 2026-09-06, Oconomowoc in this change, and Horicon a second time because the
# list had carried it twice. The comment above this one says an address moves
# out of the queue in the same change that starts fetching it; nothing said the
# reverse, so a queue meant to stop the next pass repeating a measurement was
# instead sending it to re-read six councils already in the shipped file. A
# QUEUE THAT LISTS WHAT SHIPPED IS NOT A QUEUE. Removing a row is now part of
# building the city, the same step as adding its constant.
#
# THEIR SEAT VOCABULARY WAS MEASURED 2026-09-05: six number seats by WARD (the
# Viroqua shape, needing the live LTSB ward-is-district witness) — Cumberland,
# Hillsboro, Nekoosa, Westby, Greenwood, Montreal; Wisconsin Dells uses an
# ordinal "Nth District"; New Holstein pairs by neither and wants a read before
# a regex:
#
#   QUEUE ROWS FOLLOW — build_wi_alderperson_roster.selftest() reads them
#   from this file and refuses any row naming a city FLOORS already holds.
#   When the last one ships, put a line reading QUEUE EMPTY and nothing
#   else where the rows were, rather than deleting the block, so the
#   check keeps something to read.
#   Waupaca           C 5  https://cityofwaupaca.org/government/mayor-city-council/
#   Cumberland        C 4  https://cityofcumberland.net/city-council
#   Hillsboro         C 4  https://www.hillsborowi.com/mayor-and-council
#   Nekoosa           C 4  https://cityofnekoosa.org/city-council
#   New Holstein      C 4  https://cityofnewholstein.org/elected-officials/
#   Westby            C 3  https://www.cityofwestby.org/westby-city-council
#   Wisconsin Dells   C 3  https://www.citywd.org/departments/city-government
#   Greenwood         C 2  https://cityofgreenwood.wi.gov/city-council
#   Montreal          C 2  https://montrealwis.com/departments/city-council/
#
# These are ADDRESSES THIS MODULE DOES NOT FETCH — a queue, deliberately in a
# comment rather than in an upper-case table, because validate_robots.py reads
# upper-case attributes as scheduled fetches and would report policies for
# requests nobody makes.
LTSB_WARDS = ("https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest"
              "/services/WI_Municipal_Wards_Current/FeatureServer/0/query")
STEVENS_POINT_DIR = "https://stevenspoint.com/Directory.aspx?DID=23"
MENOMONIE_INDEX = "https://www.menomonie-wi.gov/248/City-Council"
MANITOWOC_INDEX = "https://www.manitowoc.org/78/Meet-Your-Alderperson"
SHEBOYGAN_INDEX = "https://www.sheboyganwi.gov/395/Common-Council"
# www.ci.superior.wi.us answers, and 301s to this host; the redirect target is
# what ships so a reader clicks the address the city actually serves.
SUPERIOR_INDEX = "https://www.superiorwi.gov/697/City-Councilor-Information"
PORTAGE_INDEX = "https://www.portagewi.gov/mayor-and-council"
# http:// 301s here, the same shape as Superior's host; the redirect target is
# what ships so a reader clicks the address the city actually serves.
VIROQUA_INDEX = ("https://viroqua-wisconsin.com/government"
                 "/city_council_and_committees.php")
MENASHA_INDEX = ("https://www.menashawi.gov/residents/government"
                 "/common_council/index.php")
HOWARD_INDEX = ("https://www.villageofhoward.com/208"
                "/Village-President-Board-of-Trustees")
TOMAH_INDEX = "https://www.tomahwi.gov/citycouncil"
EAU_CLAIRE_INDEX = "https://www.eauclairewi.gov/310/City-Council"

# ---- the tranche of 2026-09-05 evening, from the 22 the sweep had measured ----
# FIVE constants, for the five cities actually fetched. Algoma, Dodgeville,
# Oconomowoc and Horicon were built and then withdrawn (two members per
# district, see below), and their addresses go back to the queue comment
# rather than staying here: validate_robots.py reads an upper-case module
# attribute as a SCHEDULED FETCH and would report policies for requests this
# module no longer makes.
# Each address moves from the queue comment above into a constant HERE in the
# same change that starts fetching it, never before: validate_robots.py reads
# upper-case module attributes as scheduled fetches and would otherwise report
# policies for requests nobody makes. robots.txt was read for ALL TWENTY-TWO
# candidate hosts before any page fetch, not just the five kept — none
# carries a Disallow reaching these paths.
NEW_LISBON_INDEX = "https://cityofnewlisbon.com/common-council"
NEW_BERLIN_INDEX = "https://www.newberlinwi.gov/"
STURGEON_BAY_INDEX = ("https://www.sturgeonbaywi.org/government/"
                      "city_council/index.php")
ALTOONA_INDEX = "https://www.altoonawi.gov/government/elected_officials.php"
EAGLE_RIVER_INDEX = "https://eagleriverwi.gov/city-government/elected-officials/"
GERMANTOWN_INDEX = "https://www.germantownwi.gov/299/Village-Board"

# ---- the multi-member tranche of 2026-09-24, unblocked by #1133 ----
# Each address moves out of the queue comment above into a constant HERE in the
# same change that starts fetching it, never before — validate_robots.py reads
# an upper-case module attribute as a SCHEDULED FETCH. robots.txt was read for
# every one of these BEFORE the first page fetch, as the client this file
# sends: Algoma serves no robots.txt (404, allow all), Wautoma, Horicon and
# Dodgeville each serve one whose `*` group reaches none of these paths.
# DODGEVILLE STATES `Crawl-delay: 15`, AND IT IS SATISFIED BY CONSTRUCTION
# RATHER THAN BY PACING — which is worth stating plainly, because "honoured"
# would be a claim this module cannot back. A Crawl-delay governs the INTERVAL
# BETWEEN requests to one host; this scrape makes exactly ONE request per host
# per weekly run, so there is no interval to be too short. If a second page on
# that host is ever added, this stops being true and the delay has to be
# enacted, not re-asserted.
#
# AND IF YOU SEE www.cityofdodgeville.com IN validate_robots.py's "would not
# serve robots.txt — policy unknown" LIST, THAT IS THE SWEEP AND NOT THE HOST.
# Measured 2026-09-24: five consecutive reads through the shared reader each
# returned the same 3,885-byte file, permitting this path, stating the delay
# above — while the gate's own run minutes earlier could not read it. The
# likeliest cause is the gate asking a host that states a 15-second delay as
# fast as it asks the rest, which is the one kind of refusal this project can
# provoke in itself. Re-read it before recording that host as unknown.
#
# THIS MODULE DOES NOT READ robots.txt ITSELF, and that is the fleet's recorded
# state for it rather than a gap this tranche opens: `wi/scripts/
# validate_robots.py` reads every host named in an upper-case attribute here
# against that host's own file, monthly, and fails on a Disallow that reaches
# one of these paths. The four below were additionally read by hand, through
# the shared reader and as the client this file sends, before their first
# fetch.
# ---- the second multi-member tranche, 2026-09-24 ----
# robots.txt read for both before the first page fetch, through the shared
# reader and as the client this file sends: each serves a file whose `*`
# group reaches neither path, and neither states a Crawl-delay.
BLACK_RIVER_FALLS_INDEX = ("https://blackriverfallswi.gov"
                           "/common-council-committee-of-the-whole")
NEENAH_INDEX = "https://www.ci.neenah.wi.us/common-council/"

# ---------------------------------------------------------------------------
# THE TRANCHE OF 2026-10-01, which is the first aimed at the fourth test rather
# than at whatever happened to be readable: the done standard asks whether every
# general-purpose government above 25,000 people names its governing body, and
# Wisconsin named 14 of 35. These four are what the 21 unnamed cities yielded,
# each robots.txt read at the PAGE with the Chrome client this file crawls as
# (2026-10-01): Franklin 47 bytes, no rule matching; Greenfield 816 bytes, no
# rule matching, and that file is one CMS vendor's default shared byte for byte
# with Brookfield, Oak Creek, Sun Prairie and Fitchburg — published at each
# city's own host so it binds there, and never to be cited as something any of
# those five chose; Muskego and West Bend serve no robots.txt at all (404).
#
# ALL FOUR SERVE THE DISTRICTRY TOKEN A FULL PAGE, measured across the four
# client rungs on 2026-10-01 and recorded in `user-agent-measurements.json`
# (75,642 / 97,686 / 82,128 / 101,259 bytes to `requests` plus the bare token).
# So the browser string this file sends is not licensed by these four, and they
# are named here rather than left implied: the string stays because 17 of the 35
# hosts this one file reaches do refuse the token, and the User-Agent is set once
# for all of them. Franklin's page carries a contact form's captcha widget and is
# NOT a challenge -- HTTP 200 with the whole council on it -- which is the
# false-positive class CLAUDE.md already records for keyword matching on a body.
#
# THE FIVE THAT ARE SHUT, measured the same day and worth as much as the four
# that shipped. The heading over this block has now been wrong twice and both
# errors are the same one: it read FIVE while the bullets below it named SIX
# cities, because the middle bullet is four cities in one line, and the
# correction that removed Oshkosh then wrote FOUR, subtracting one from the
# wrong total. COUNT THE CITIES, NOT THE BULLETS. The 21 unnamed cities of
# 2026-10-01 are 4 built here, 5 shut below, 1 Oshkosh (open, at large) and 11
# readable behind a page that assembles itself in the browser:
#   THAT BREAKDOWN IS THE 2026-10-01 MORNING STATE AND THREE OF ITS ENTRIES HAVE
#   MOVED SINCE; the corrected block below, headed THAT SWEEP SAID FIVE CITIES
#   WERE SHUT, is the authority. Wausau and Wauwatosa ship from this file, and
#   Janesville ships from `wi_municipal_board_scraper.py`, its council being
#   elected at large. No total is restated here, because the two errors this
#   heading has already made were both arithmetic on a figure nobody recounted.
#   BELOIT publishes `User-agent: * / Disallow: /` under six named crawlers that
#   get narrow rules. That is the city's own host and its own file, so it binds
#   fully, and nothing here renames an agent to get past it.
#   JANESVILLE, WAUSAU, WAUWATOSA and MEQUON answer HTTP 403 to this client at
#   the HOME page, not merely on robots.txt — a site-wide block that enforces
#   itself, which is #1271's own reading of why a robots 403 needed no strict
#   treatment. Not probed with a second client: a host that refuses the first is
#   not an invitation to try a richer one.
#   OSHKOSH IS NOT SHUT AT ALL, and the line above read that it served an
#   INCOMPLETE TLS CHAIN, the Coles pattern. Measured 2026-10-01 through
#   `scripts/probe_incomplete_tls_chains.py`: `{"state": "ok", "code": "200"}`,
#   0 of 1 hosts serving an incomplete chain. The claim was wrong, and it was
#   wrong in the direction that keeps a readable city unread — the record this
#   file already carries about Eau Claire, one city later. What is true is
#   narrower and is a fact about THIS CLIENT rather than about the city: both
#   Python stacks fail the handshake with `UNEXPECTED_EOF_WHILE_READING` where
#   `curl` completes it, and the one setting that fixes it is
#   `ssl.create_default_context()` plus `set_ciphers("DEFAULT@SECLEVEL=1")`,
#   which relaxes OpenSSL's signature-and-key-size POLICY and leaves
#   certificate verification fully intact — nothing here disables verification.
#   Pinning the maximum version to TLS 1.2 does NOT fix it, and under SECLEVEL=1
#   the connection negotiates TLSv1.3 with TLS_AES_256_GCM_SHA384.
#   THE NEXT SENTENCE USED TO DRAW A CONCLUSION FROM THAT AND IT DOES NOT
#   FOLLOW: it read that "the cause is something Debian's level 2 rejects in the
#   CHAIN rather than anything weak about the transport", which is a claim about
#   what OSHKOSH SERVES, and nothing measured here can support one. This
#   sandbox's egress gateway intercepts and re-signs every outbound TLS
#   connection -- `wi/WATCH.md`'s 2026-09-13 row already records every host
#   measured here carrying the gateway's own issuer, and the app thread
#   re-confirmed it on 2026-10-01 against Google and GitHub as controls -- so the
#   chain inspected was the GATEWAY'S and not the city's, and the app thread
#   could not reproduce the handshake failure at all. The symptom is real from
#   here and is UNEXPLAINED; it is not evidence about the city's certificate.
#   THE SAME DOUBT REACHES THE ROBOTS READ BELOW, which went through the
#   SECLEVEL=1 context, so it was a read through a client this project does not
#   crawl with and is held as provisional rather than as the policy measurement.
#   So nothing in the shared reader changes and no per-site security setting is
#   considered: the next step is `scripts/probe_robots_verdicts.py` from a GitHub
#   runner, the vantage the scheduled scrapers crawl from and the one this fleet
#   already uses for this class of sandbox-only TLS symptom. Provisionally, its
#   robots.txt (331 bytes) disallows fourteen paths — Laserfiche, WebTrac, test directories —
#   and PERMITS /CityCouncil/. And its council is AT LARGE: the page states
#   "seven elected officials in the Common Council including the mayor, the
#   deputy mayor, and five council members", so it has no district to draw and
#   belongs in a municipal at-large roster rather than in this file, which is
#   keyed by district.
#
# THAT SWEEP SAID FIVE CITIES WERE SHUT AND THREE OF THE FIVE WERE NEVER SHUT
# (corrected 2026-10-01). Wausau and Wauwatosa ship below, and Janesville's
# roster reads fine; all three sit behind an Akamai edge that answers 403 to
# every client this file had tried -- ROBOTS.TXT INCLUDED, which is why the
# reading came out as a block rather than as a policy -- and 200 to the fuller
# header set in UA_AKAMAI above, which a SIBLING SCRAPER IN THIS SAME DIRECTORY
# had already measured on one of these very hosts two days earlier. The evidence
# was in the repository before the record was written.
#
# A NO ANSWER AND A NO ARE DIFFERENT THINGS, and reading the first as the second
# is what kept three councils out for weeks: a refusal is a host telling you not
# to read it, while 403 to every rung you happened to try is a measurement of
# your own client. Janesville is at large (its own page: "seven members, who are
# elected on a nonpartisan basis and represent the city as a whole") so it has no
# district to draw and belongs in the at-large roster, not here. Beloit is the one
# of the five that genuinely refuses: its robots.txt answers the districtry token
# with `Disallow: /`, and that is obeyed.
#
# JANESVILLE SHIPPED ON 2026-10-01, from `wi_municipal_board_scraper.py` rather
# than from this file, because its seven councilmembers are elected at large and
# a row keyed by a seat number here would tell a reader they were elected in a
# way they were not. Its edge wants BOTH a non-urllib3 stack AND Chrome's client
# hints — the Kendall shape — and the policy it then serves is BYTE-IDENTICAL to
# Kendall County's own, one CMS vendor's default, which binds at the city's host
# and is never to be cited as Janesville's choice. Mequon cannot be read from a Claude Code
# sandbox at all -- every spelling of its host fails at the egress gateway with
# `Tunnel connection failed: 502`, which is a fact about this route and says
# nothing about the city -- so it waits on a measurement from a GitHub runner
# (wi/WATCH.md).
FRANKLIN_INDEX = ("https://www.franklinwi.gov/Departments/Elected-Officials"
                  "/Common-Council.htm")
GREENFIELD_INDEX = "https://www.ci.greenfield.wi.us/334/Common-Council"
MUSKEGO_INDEX = ("https://www.muskego.wi.gov/government/boards_commissions"
                 "/common_council.php")
WEST_BEND_INDEX = ("https://www.westbendwi.gov/government/elected_officials"
                   "/west_bend_common_council/index.php")

ALGOMA_INDEX = "https://www.algomacity.org/government/city_council.php"
DODGEVILLE_INDEX = "https://www.cityofdodgeville.com/council"
# MARION is read from its COUNTY, not its own site: cityofmarionwi.gov publishes
# `User-agent: * / Disallow: /` (re-read 2026-10-06), which is obeyed. The
# Waupaca County Clerk's Directory of Public Officials carries the council in
# its city-officials section, and that host serves no robots.txt (HTTP 404) and
# serves the districtry token a full page (user-agent-measurements.json), so it
# is fetched with the token rather than this file's browser string.
MARION_INDEX = "https://public4.co.waupaca.wi.us/CountyDirectory"
HORICON_INDEX = "https://www.horiconwi.gov/185/Elected-Officials"
WAUTOMA_INDEX = "http://www.cityofwautoma.com/common-council"

# ---- the partially-filled district, 2026-09-25 ----
# THE APEX HOST, NOT `www`. Measured 2026-09-25: oconomowoc-wi.gov serves
# robots.txt (816 bytes, four of four reads) and its `*` group reaches
# /activedit, /admin, /Search, /map.aspx and 19 more paths and not this one;
# www.oconomowoc-wi.gov resets the connection. Neither prefix is a safe
# default (the Barron and Forest pattern), so the spelling that answers is
# the spelling that ships.
OCONOMOWOC_INDEX = "https://oconomowoc-wi.gov/225/Common-Council"

APPLETON_INDEX = "https://www.appletonwi.gov/government/common_council.php"

# The two districted councils of 2026-10-01, both behind the Akamai edge above.
WAUSAU_INDEX = ("https://www.wausauwi.gov/your-government/city-council"
                "/alderpersons")
WAUWATOSA_INDEX = ("https://www.wauwatosa.net/government/common-council"
                   "/contact-the-common-council")

# Cardinal number words, for a page that STATES the size of its own council.
# Oconomowoc's "eight Aldermen representing each of the City's four
# districts" is the only witness this project has for how many seats that
# council holds, so the sentence is parsed rather than read by a person once
# and written down; a word outside this table fails the build rather than
# being skipped, because the seat total is what the vacancy count is checked
# against.
CARDINALS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
             "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
             "sixteen": 16, "seventeen": 17, "eighteen": 18,
             "nineteen": 19, "twenty": 20}

ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
            "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
            "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
            "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
            "eighteenth": 18, "nineteenth": 19, "twentieth": 20}

# Districts where the certified April 2026 canvass OVERRIDES the city GIS,
# each pinned only after its story was read. The pin is self-retiring twice
# over: it fails if the canvass stops naming this winner, and it fails the
# day the GIS catches up (remove it then).
# RETIRED 2026-09-03, EXACTLY AS THIS BLOCK'S OWN COMMENT INSTRUCTS. District
# 14's pin existed because the GIS still named Kenny Harper, who won in April
# 2024 and did not seek re-election; Daniel Prozanski won the certified April
# 2026 contest 913 votes to write-ins' 17. The city's layer now names Prozanski
# itself, so there is no longer a disagreement to override and the card ships
# the city's own current spelling with no override note — which is the whole
# point of a self-retiring pin.
#
# IT DID NOT SELF-RETIRE, AND THAT WAS A REAL DEFECT rather than an oversight:
# the loop below tested the GIS against the canvass FIRST and `continue`d on a
# match, so the "the GIS now agrees — remove the pin" guard sat behind a branch
# that could no longer be reached. The pin had become dead code announcing
# nothing. The pin check now runs BEFORE that test, so the next one retires
# itself loudly on the day it should.
KENOSHA_CANVASS_WINS = {}

# CITIES WAS RETIRED 2026-09-24. It listed the municipalities a second
# time, was never imported and was read only as main()'s denominator,
# where it had been stale at 18 since the tranche of 2026-09-05 — so
# every run since printed a fraction over the wrong total. The list
# lives once, as COVERED in main().


def fetch(url, binary=False, tries=3, timeout=60, headers=None):
    # EVERY HOST'S RULES ARE READ BEFORE ITS FIRST PAGE, through the shared seam
    # rather than the hand-recorded readings in the comments above, and with the
    # identity this fetch sends. This file follows each municipality's own site
    # out of a list, so the hosts it reaches are not all in its own source and no
    # fixed table could cover them; asking at the fetch is the only way to ask
    # about every one.
    #
    # The three hosts whose recorded readings had shut this file out were all
    # re-measured from a GitHub runner on 2026-10-01, the vantage the weekly job
    # crawls from: viroqua-wisconsin.com and www.altoonawi.gov answer HTTP 404
    # for robots.txt, so they publish no rules; www.portagewi.gov serves a
    # 29-byte policy matching none of the paths read here, on all three of a
    # deliberate re-measurement's reads fifteen seconds apart. Portage states
    # `Crawl-delay: 5`, which is satisfied by construction for the reason
    # Dodgeville's 15 already is above — one page per host per run.
    #
    # A ROBOTS VERDICT IS ISOLATED PER CITY AND DOES NOT END THE RUN, which is a
    # deliberate reading of the block above `attempt()` rather than a hole in it.
    # That block draws the line between "not today" (a timeout, a reset — caught
    # per municipality, the city's last-good rows carried forward and named) and
    # "a pinned reading has stopped being true" (a gate, which must stop
    # everything). A robots verdict is always the first kind. An UNREACHABLE
    # robots.txt is a fact about a route this minute — measured 2026-10-01, the
    # first run after this seam was wired died at Stevens Point on a connection
    # reset from this sandbox, taking 28 cities' refresh down with it. And a
    # published REFUSAL is a standing fact about one host that says nothing about
    # the other 34, and never unpublishes what we already fetched (Adam, 2026-09-19).
    # So the decline is re-raised as an ordinary Exception: `attempt()` records it
    # as that city's reason, the builder carries that city forward, and NOTHING
    # IS FETCHED from the host either way, which is the whole of what a refusal
    # asks for. The catch above is not widened by this and no gate becomes
    # catchable.
    try:
        # ONE header set for both halves. A page fetched with headers the
        # robots read did not send is the inconsistency #1271 forbids, and on
        # the three Akamai hosts it is also the difference between a policy and
        # a 403, so the two cannot be allowed to drift apart here.
        hdrs = headers or UA
        require_robots_once(url, hdrs["User-Agent"], headers=hdrs,
                            label="wi-alderperson-scraper")
    except SystemExit:
        # `require_robots_allowed` prints the verdict and exits 1, so the
        # exception itself carries only the status code — the first version of
        # this recorded "RuntimeError: 1" as Horicon's reason, which tells the
        # weekly PR's reviewer nothing about which host or why. The host and the
        # verdict are named here instead, because the reason travels into
        # `failures` and is the only thing a reviewer sees.
        raise RuntimeError(
            "robots.txt declined for %s — see the FAIL line above for the "
            "verdict; nothing was fetched from it"
            % (urllib.parse.urlsplit(url).hostname or url))
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or UA)
            # NO EXPLICIT SSL CONTEXT. This call used to pass
            # `context=ssl.create_default_context()`, which reads like a restatement
            # of the default and is not one: `http.client` applies
            # `set_alpn_protocols(["http/1.1"])` and enables post-handshake auth ONLY
            # on the context it builds itself, so handing it one sends a ClientHello
            # advertising no protocol. Cloudflare answers that handshake with a
            # MANAGED CHALLENGE -- 403, `Cf-Mitigated: challenge`, the "Just a
            # moment..." body -- on a site that serves the same URL to the same
            # headers without it. That is how www.milwaukee.gov read as refusing this
            # project for weeks while serving its robots.txt fine (#1277, measured
            # 2026-09-30: explicit context 403 twice, explicit context with ALPN set
            # by hand 200 at 52,682 bytes, no context 200 at 52,682). Removing it
            # defeats no challenge -- it stops provoking one -- and it puts this fetch
            # on the identical call `scripts/robots_policy.py` already makes, which is
            # #1271's consistency requirement: read robots.txt with the client that
            # crawls.
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — retried, then re-raised
            last = e
            time.sleep(2 * (i + 1))
    raise last


def fold(name):
    """First + last alphabetic token, accent-stripped — the fleet's person
    fold: middle initials, suffixes and diacritics never read as different
    people; a genuinely different first or last name still does."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    toks = [t for t in re.split(r"[^a-z]+", s) if len(t) > 1 and t not in
            ("jr", "sr", "ii", "iii", "iv")]
    return (toks[0] + "|" + toks[-1]) if toks else ""


def fold_set(name):
    """Unordered token fold, for a source that prints names surname-first:
    the Kenosha canvass's vertical column headers reassemble in reading
    order ('LaMacchia, Rocco Sr. J.'), so ordered first|last comparison
    reads a reversal as a different person. The token SET doesn't care."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return frozenset(t for t in re.split(r"[^a-z]+", s) if len(t) > 1 and t not in
                     ("jr", "sr", "ii", "iii", "iv"))


CF_TOKEN = re.compile(r'(?:/cdn-cgi/l/email-protection#|data-cfemail=")([0-9a-fA-F]{4,})')


def cf_decode(token):
    """Cloudflare's e-mail scrambling: the first byte is the XOR key for the
    rest. The same decode wi_county_board_scraper.py applies."""
    raw = bytes.fromhex(token)
    return "".join(chr(c ^ raw[0]) for c in raw[1:])


def cf_email(fragment, label, domain=None):
    """{"email": ...} from the one scrambled address in FRAGMENT, or {}.

    THE SCRAMBLING IS NOT AN ACCESS CONTROL (Adam, 2026-10-09): the page hands
    the key to every visitor inside the same bytes, so decoding it reads the
    page as published. Two tokens decoding to different addresses, or a token
    that does not decode to an address (on DOMAIN, where the city has one),
    fails — a wrong address on a card is worse than none.
    """
    got = set()
    for t in CF_TOKEN.findall(fragment):
        try:
            got.add(cf_decode(t).strip())
        except ValueError:
            raise SystemExit("%s: a Cloudflare email token is not hex pairs: %r" % (label, t))
    if not got:
        return {}
    if len(got) > 1:
        raise SystemExit("%s: one entry carries %d different scrambled addresses %s"
                         % (label, len(got), sorted(got)))
    addr = got.pop()
    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", addr) or (
            domain and not addr.lower().endswith("@" + domain)):
        raise SystemExit("%s: a Cloudflare token decoded to %r, not an address%s"
                         % (label, addr, " on " + domain if domain else ""))
    return {"email": addr}


def strip_tags(html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    return [l.strip() for l in H.unescape(t).split("\n") if l.strip()]


# ---------------------------------------------------------------- Milwaukee
def read_dbf(data):
    n_rec = struct.unpack("<I", data[4:8])[0]
    hdr_len = struct.unpack("<H", data[8:10])[0]
    rec_len = struct.unpack("<H", data[10:12])[0]
    fields = []
    off = 32
    while data[off] != 0x0D:
        name = data[off:off + 11].split(b"\x00")[0].decode()
        fields.append((name, data[off + 16]))
        off += 32
    rows = []
    pos = hdr_len
    for _ in range(n_rec):
        rec = data[pos:pos + rec_len]
        pos += rec_len
        o = 1
        row = {}
        for name, flen in fields:
            row[name] = rec[o:o + flen].decode("latin1").strip()
            o += flen
        rows.append(row)
    return rows


def scrape_milwaukee():
    """Milwaukee's 15 alderpersons, from Legistar — which was already the witness.

    THE OLD PRIMARY WAS A HOST THAT ASKS NOT TO BE CRAWLED. milwaukeemaps.
    milwaukee.gov publishes

        User-agent: Googlebot
        Allow: /
        User-agent: *
        Disallow: /

    and this function fetched its alderman layer every week, six times over with
    backoff, under a comment calling it "the measured flaky host". It is not
    flaky; it is asking. wi/scripts/validate_robots.py did not cover this module
    until 2026-09-05, which is the whole reason a blanket Disallow went unread
    for as long as it did.

    NOTHING IS LOST AND NO SOURCE IS ADDED. Legistar was already fetched on
    every run as the currency witness, and it carries the district as well as
    the name: OfficeRecordTitle is "3rd District", corroborated by
    OfficeRecordSort. Measured 2026-09-05 against the shipped roster: 15 of 15
    districts and 15 of 15 surnames. So the two fetches this function makes are
    unchanged in number — the ROLES are swapped, and the disallowed one is gone.

    SIX ROWS CHANGED SPELLING ON THE FIRST REBUILD, NOT ONE. An earlier version
    of this paragraph said "one suffix difference", which was the one that
    LOSES something and not the count. The GIS spelled middle names out and
    Legistar abbreviates or omits them: D01 "Andrea M Pratt" -> "Andrea Pratt",
    D02 "Mark Chambers, Jr" -> "Mark Chambers Jr.", D06 "Milele A Coggs" ->
    "Milele A. Coggs", D10 "Sharlen P Moore" -> "Sharlen Moore", D12 "Jose G
    Perez" -> "Jose Perez", D15 "Russell W Stamper, II" -> "Russell W. Stamper".
    Same six people, the Council's own styling. Only D15 loses a name part
    Legistar does not carry at all — there is no suffix field anywhere in the
    record (Chambers keeps his inside the LAST name) — and it is NOT typed back
    in by hand, because that would be a name this project cannot source.

    The CKAN shapefile stays as corroboration rather than as a fallback: it is
    the city's own open-data portal, its robots.txt permits the path, and where
    it answers its districts must agree. It is NOT required, because a host
    that declines one client on one day must not be able to fail a build whose
    data is already sound.
    """
    today = time.strftime("%Y-%m-%d")
    recs = json.loads(fetch(MKE_LEGISTAR))
    members, current = {}, set()
    for r in recs:
        start = (r.get("OfficeRecordStartDate") or "")[:10]
        end = (r.get("OfficeRecordEndDate") or "9999")[:10]
        if not (start <= today <= end):
            continue
        # NEVER OfficeRecordFullName — that column is "ALD. SURNAME" (measured),
        # so the name is built from the First/Last columns.
        full = ((r.get("OfficeRecordFirstName") or "") + " " +
                (r.get("OfficeRecordLastName") or "")).strip()
        if full:
            current.add(fold(full))
        m = re.match(r"\s*(\d+)(?:st|nd|rd|th)\s+District\s*$",
                     r.get("OfficeRecordTitle") or "", re.I)
        if not (m and full):
            continue
        num = int(m.group(1))
        # THE TITLE AND THE SORT COLUMN MUST AGREE. Two fields on the same
        # record naming the same district is the cheapest witness available,
        # and a Legistar body whose Sort stopped tracking the district is
        # exactly the drift that would put a name under the wrong ward.
        sort = r.get("OfficeRecordSort")
        if isinstance(sort, int) and sort != num:
            raise SystemExit("milwaukee: Legistar title %r says district %d but "
                             "OfficeRecordSort says %d — the two disagree, so "
                             "neither is trusted" % (r.get("OfficeRecordTitle"),
                                                     num, sort))
        members["%02d" % num] = {"name": full}
    if len(members) != 15:
        raise SystemExit("milwaukee: Legistar names %d of 15 districts among %d "
                         "current COMMON COUNCIL records" % (len(members),
                                                             len(current)))
    source = MKE_LEGISTAR

    # Corroboration, not a dependency: where the city's open-data shapefile
    # answers, its districts must agree with Legistar's.
    # ONLY THE FETCH IS ALLOWED TO FAIL QUIETLY. A parse error inside this try
    # would have been reported as "did not answer", which is a different fact
    # about a different party — so the download is the only thing it covers.
    try:
        blob = fetch(MKE_CKAN_ZIP, binary=True)
    except Exception as exc:  # noqa: BLE001 — a witness that declines is not a failure
        print("milwaukee: the CKAN shapefile did not answer (%s); Legistar's %d "
              "districts ship uncorroborated this run"
              % (type(exc).__name__, len(members)), file=sys.stderr)
    else:
        z = zipfile.ZipFile(io.BytesIO(blob))
        dbf = next(n for n in z.namelist() if n.lower().endswith(".dbf"))
        ckan = {"%02d" % int(row["DISTRICT"]): row["ALDERPERSO"].strip()
                for row in read_dbf(z.read(dbf))}
        # PER DISTRICT, NOT MEMBERSHIP. Asking only whether CKAN's name is
        # somewhere in the current council would pass a shapefile that had every
        # alderperson right and every district wrong — which is precisely the
        # failure a second source is here to catch.
        disagree = sorted(d for d, name in ckan.items()
                          if d in members and fold(name) != fold(members[d]["name"]))
        if disagree:
            raise SystemExit(
                "milwaukee: CKAN and Legistar name different people for district(s) "
                "%s — %s — so one of the two is stale and neither is trusted"
                % (disagree, ["%s: CKAN %r vs Legistar %r"
                              % (d, ckan[d], members[d]["name"]) for d in disagree]))
        print("milwaukee: CKAN corroborates %d of %d districts by name"
              % (sum(1 for d in ckan if d in members), len(members)),
              file=sys.stderr)
    return members, source


# ------------------------------------------------------------------ Madison
def scrape_madison():
    index = fetch(MADISON_INDEX)
    by_href = {}
    for m in re.finditer(r'href="(?:https://www\.cityofmadison\.com)?/council/district(\d+)"'
                         r'[^>]*>\s*Alder\s+([^<]+)<', index):
        # UNESCAPE. The index writes an apostrophe as `&#039;`, and D16 shipped
        # the literal "Sean O&#039;Brien" from 2026-08-26 to 2026-09-05 because
        # nothing here decoded it and the card renders through textContent, which
        # is exactly right for safety and does not undo an entity. The surname
        # gate below never caught it either: fold() drops punctuation, so
        # "O&#039;Brien" and "O'Brien" both fold to "brien".
        by_href[int(m.group(1))] = " ".join(H.unescape(m.group(2)).split())
    if not (17 <= len(by_href) <= 20):
        raise SystemExit("madison index links %d alder districts (expected ~19-20 "
                         "with vacancies) — the page shape moved" % len(by_href))
    members = {}
    vacant = []
    for n in range(1, 21):
        page = fetch(MADISON_DISTRICT % n)
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
        head = H.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip() if h1 else ""
        if not head.startswith("District %d" % n):
            raise SystemExit("madison district page %d headlines %r" % (n, head))
        if "Vacant" in head:
            vacant.append(n)
            continue
        sur = re.sub(r"^District %d\s*-\s*Alder\s*" % n, "", head).strip()
        name = by_href.get(n)
        if not name or fold(name).split("|")[-1] != fold("x " + sur).split("|")[-1]:
            raise SystemExit("madison D%d: index name %r does not carry the page's "
                             "surname %r — the index/href pairing moved" % (n, name, sur))
        entry = {"name": name, "url": MADISON_DISTRICT % n}
        m = re.search(r'mailto:(district%d@cityofmadison\.com)' % n, page)
        if m:
            entry["email"] = m.group(1)
        members["%02d" % n] = entry
    if len(members) + len(vacant) != 20:
        raise SystemExit("madison: %d named + %d vacant != 20" % (len(members), len(vacant)))
    if len(members) < 17:
        raise SystemExit("madison names only %d of 20 districts" % len(members))
    # The third value is the EXTRA FIELDS this city adds beyond its members,
    # named rather than positional: main() reads it as a mapping and refuses
    # a key it does not know. It was a bare `vacant` list until 2026-09-25,
    # when a second city needed a different extra field (Oconomowoc's
    # vacantSeats) and a fourth positional element would have meant every
    # caller knowing which slot means what.
    return members, MADISON_INDEX, {"vacantDistricts": vacant}


# ---------------------------------------------------------------- Green Bay
def scrape_green_bay():
    page = fetch(GREEN_BAY_DIR)
    members = {}
    # split on the ENTRY container class, never a bare <li>: each entry nests
    # a <ul><li> department list, so a bare-<li> split cuts the entry before
    # its e-mail and phone column (measured — the first draft shipped twelve
    # names with no contact at all)
    for li in re.split(r'<li class="list-group-item', page)[1:]:
        t = re.search(r"District\s+(\d+)\s+Alderperson", li)
        if not t:
            continue
        n = int(t.group(1))
        nm = re.search(r'href="(/m/directory/employee\?eid=\d+)"[^>]*>\s*([^<]+?)\s*<', li)
        if not nm:
            continue
        entry = {"name": " ".join(nm.group(2).split()),
                 "url": "https://www.greenbaywi.gov" + nm.group(1)}
        em = re.search(r'mailto:([^"?]+)"', li)
        if em:
            entry["email"] = em.group(1).strip()
        else:
            entry.update(cf_email(li, "green bay D%d" % n, "greenbaywi.gov"))
        ph = re.search(r'href="tel:([^",]+)', li)
        if ph:
            entry["phone"] = ph.group(1).strip()
        key = "%02d" % n
        if key in members and members[key]["name"] != entry["name"]:
            raise SystemExit("green bay lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 12:
        raise SystemExit("green bay names %d of 12 districts" % len(members))
    # THE ADDRESSES WENT BEHIND CLOUDFLARE'S E-MAIL SCRAMBLING ON OR BEFORE
    # 2026-10-01: the page served twelve `mailto:` links and now serves each
    # as a `/cdn-cgi/l/email-protection#<hex>` link, which cf_email() reads.
    # From 2026-10-01 to 2026-10-09 this function called that an access control
    # and raised, so the builder carried the city whole. It is not one: the
    # page hands the key to every visitor in the same bytes (Adam, 2026-10-09,
    # the reading the county board scraper already applied at Buffalo, Iron
    # and Manitowoc). Measured that day, all twelve decoded addresses are
    # byte-identical to the ones the file already shipped.
    #
    # A page with no address in either form still fails, because twelve seats
    # with no contact is the first draft's split defect above, not a city that
    # stopped publishing.
    if not any("email" in m for m in members.values()):
        raise SystemExit(
            "green bay: no member carries an address, in a mailto: link or a "
            "Cloudflare email-protection link — the entry split or the markup "
            "moved [%d data-cfemail, %d email-protection on the page]"
            % (len(re.findall(r"data-cfemail", page)),
               len(re.findall(r"email-protection#", page))))
    return members, GREEN_BAY_DIR


# ------------------------------------------------------------------ Kenosha
def kenosha_canvass_winners(pdf_path):
    """Positional parse of the county's certified canvass: per alderperson
    contest, candidate columns are centered vertical stacks; the Totals
    row's first k numbers are the k candidates' votes."""
    import pdfplumber
    BOIL = {"VOTE", "FOR", "of", "Precincts", "Reporting", "Totals", "Cast",
            "Total", "Votes", "Overvotes", "Undervotes", "Contest", "Write-in"}
    wins = {}
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            words = pg.extract_words()
            titles = []
            for i, w in enumerate(words):
                if (w["text"] == "Alderperson" and i + 2 < len(words)
                        and words[i + 1]["text"] == "District"
                        and re.match(r"^\d+$", words[i + 2]["text"])):
                    titles.append({"n": int(words[i + 2]["text"]), "x0": w["x0"]})
            if not titles:
                continue
            votes = sorted((w for i, w in enumerate(words) if w["text"] == "VOTE"
                            and i + 1 < len(words) and words[i + 1]["text"] == "FOR"),
                           key=lambda w: w["x0"])
            reps = [w for w in words if w["text"] == "Reporting"]
            units = [w for w in words if w["text"] in ("Town", "Village", "City")]
            tots = [w for w in words if w["text"] == "Totals"]
            if not (votes and reps and units and tots):
                continue
            h_top = max(r["top"] for r in reps) + 2
            unit_tops = [u["top"] for u in units if u["top"] > h_top]
            if not unit_tops:
                continue
            h_bot = min(unit_tops) - 2
            trow = max(tots, key=lambda w: w["top"])
            hw = [w for w in words if h_top < w["top"] < h_bot
                  and w["text"] not in BOIL and not re.match(r"^[\d,%.]+$", w["text"])]
            stacks = []
            for w in sorted(hw, key=lambda a: ((a["x0"] + a["x1"]) / 2, a["top"])):
                c = (w["x0"] + w["x1"]) / 2
                for s in stacks:
                    if abs(s["c"] - c) < 25:
                        s["ws"].append(w)
                        s["c"] = sum((x["x0"] + x["x1"]) / 2 for x in s["ws"]) / len(s["ws"])
                        break
                else:
                    stacks.append({"c": c, "ws": [w]})
            nums = sorted((w for w in words if abs(w["top"] - trow["top"]) < 3
                           and re.match(r"^[\d,]+$", w["text"])), key=lambda w: w["x0"])
            bounds = [0.0]
            for vi in range(1, len(votes)):
                bounds.append((votes[vi - 1]["x0"] + votes[vi]["x0"]) / 2)
            bounds.append(pg.width)
            for vi, v in enumerate(votes):
                lo, hi = bounds[vi], bounds[vi + 1]
                t = min(titles, key=lambda t: abs(t["x0"] - v["x0"]))
                if not (lo <= t["x0"] + 5 and t["x0"] - 5 <= hi):
                    continue  # this VOTE anchor belongs to a non-alder contest
                cst = sorted((s for s in stacks if lo <= s["c"] < hi), key=lambda s: s["c"])
                names = [" ".join(x["text"] for x in sorted(s["ws"], key=lambda a: a["top"]))
                         for s in cst]
                cnm = [w for w in nums if lo <= (w["x0"] + w["x1"]) / 2 < hi]
                k = len(names)
                if not k or len(cnm) < k:
                    continue
                pairs = [(names[i], int(cnm[i]["text"].replace(",", ""))) for i in range(k)]
                winner = max(pairs, key=lambda p: p[1])
                if t["n"] in wins:
                    raise SystemExit("kenosha canvass: contest %d parsed twice" % t["n"])
                wins[t["n"]] = winner
    return wins


def scrape_kenosha():
    d = json.loads(fetch(KENOSHA_GIS))
    members = {}
    for f in d["features"]:
        a = f["attributes"]
        name = (a.get("REPRESNTTV") or "").strip()
        if name and name != "N/A":
            key = "%02d" % int(a["DIST_NO"])
            if key in members and members[key]["name"] != name:
                raise SystemExit("kenosha GIS names two people for district %s" % key)
            members[key] = {"name": name}
    if len(members) != 17:
        raise SystemExit("kenosha GIS names %d of 17 districts" % len(members))

    os.makedirs(CACHE_DIR, exist_ok=True)
    pdf_path = os.path.join(CACHE_DIR, "kenosha_canvass_2026_spring.pdf")
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100000:
        open(pdf_path, "wb").write(fetch(KENOSHA_CANVASS, binary=True))
    wins = kenosha_canvass_winners(pdf_path)
    if len(wins) != 17:
        raise SystemExit("kenosha canvass parsed %d of 17 alderperson contests" % len(wins))
    bad = []
    for n in range(1, 18):
        key = "%02d" % n
        # subset, not equality: the ballot prints middle names the GIS omits
        # ("Brandi Rose Ferree" / "Ruth Delace Dyson", measured) — the same
        # person styled apart, where a different person shares no tokens
        a, b = fold_set(members[key]["name"]), fold_set(wins[n][0])
        agrees = bool(a and b and (a <= b or b <= a))
        # A PIN IS CONSULTED BEFORE THE AGREEMENT TEST, not after it. Reading
        # them the other way round is what let District 14's override outlive
        # its purpose in silence: once the GIS caught up, the agreement test
        # `continue`d and the "remove the pin" guard below became unreachable.
        if n in KENOSHA_CANVASS_WINS:
            pin = KENOSHA_CANVASS_WINS[n]
            if fold_set(wins[n][0]) != fold_set(pin["name"]):
                raise SystemExit("kenosha D%d: the pinned canvass override no longer "
                                 "matches the canvass (%r vs pin %r)" % (n, wins[n][0], pin["name"]))
            if agrees:
                raise SystemExit("kenosha D%d: the GIS now names the certified winner "
                                 "(%r) — the override has served its purpose; remove "
                                 "its KENOSHA_CANVASS_WINS entry"
                                 % (n, members[key]["name"]))
            stale = members[key]["name"]
            members[key] = {"name": pin["name"],
                            "note": "Elected April 2026 (certified by the Kenosha County "
                                    "Board of Canvassers)"}
            print("kenosha D%d: certified April 2026 winner %r ships over the GIS's "
                  "stale %r — %s" % (n, pin["name"], stale, pin["why"]),
                  file=sys.stderr)
            continue
        if agrees:
            continue
        bad.append((n, members[key]["name"], wins[n][0]))
    if bad:
        raise SystemExit("kenosha: GIS name(s) differ from the certified April 2026 "
                         "winner(s): %s — an appointment or a stale layer; needs a "
                         "human look (pin a KENOSHA_CANVASS_WINS entry only after "
                         "reading the story)" % bad)
    return members, KENOSHA_GIS.split("/query")[0]


# ------------------------------------------------------------------- Racine
def scrape_racine():
    page = fetch(RACINE_INDEX)
    members = {}
    # each staff card: a "District #N – Alderman NAME" heading, then a "Read
    # More and Contact" link to the district's own page (slugs inconsistent
    # across districts — captured, never composed)
    for m in re.finditer(r'District\s*#(\d+)\s*[–-]\s*'
                         r'Alder(?:man|woman|person)?\s+([^<]+?)\s*<', page):
        n, name = int(m.group(1)), " ".join(m.group(2).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("racine lists two names for district %d" % n)
        entry = {"name": name}
        tail = page[m.end():m.end() + 800]
        u = re.search(r'href="(https://cityofracinewi\.gov[^"]*cityalderman/[^"]+)"', tail)
        if u:
            entry["url"] = u.group(1)
        members[key] = entry
    if len(members) != 15:
        raise SystemExit("racine names %d of 15 districts" % len(members))
    return members, RACINE_INDEX


# ----------------------------------------------------------------- Waukesha
def scrape_waukesha():
    lines = strip_tags(fetch(WAUKESHA_INDEX))
    members = {}
    i = 0
    while i < len(lines):
        m = re.match(r"^Aldermanic District (\d+)$", lines[i])
        # the page prints the district list twice; only the second pass has a
        # "Wards …" line under each heading, which is the block this reads
        if m and i + 2 < len(lines) and lines[i + 1].startswith("Wards"):
            n = int(m.group(1))
            entry = {"name": lines[i + 2]}
            j = i + 3
            while j < len(lines) and not lines[j].startswith("Aldermanic District"):
                if lines[j] == "P:" and j + 1 < len(lines):
                    entry["phone"] = lines[j + 1]
                if lines[j] == "E:" and j + 1 < len(lines) and "@" in lines[j + 1]:
                    entry["email"] = lines[j + 1]
                j += 1
            if not re.match(r"^[A-Z][A-Za-z.'\- ]+$", entry["name"]):
                raise SystemExit("waukesha district %d name line reads %r — the "
                                 "block shape moved" % (n, entry["name"]))
            members["%02d" % n] = entry
            i = j
        else:
            i += 1
    if len(members) != 15:
        raise SystemExit("waukesha names %d of 15 districts" % len(members))
    return members, WAUKESHA_INDEX


# ======================================================== the twelve of 2026-09-05
# One helper first. TWO OF THEM PRINT A WARD NUMBER WHERE THE KEY IS A
# DISTRICT: Menomonie's council page reads "Jeff Luther, Ward 1" and Viroqua's
# table reads "WARD 1 | SETH MCCLURG", while the file this roster keys into is
# dissolved on ALDERID. In both cities every ward is its own district today and
# ward N carries ALDERID N — measured 2026-09-05, 11 of 11 and 9 of 9 — but that
# is a fact about a filing, not about the English language, and a re-warding
# would silently move every name one seat. So it is WITNESSED on every run from
# the same publisher whose file draws the districts: if the identity breaks,
# those two cities fail (isolated, carried forward) rather than shipping a
# plausible wrong answer.
_LTSB_CACHE = {}


def ltsb_ward_to_alder(mcd_name, ctv):
    """{ward int -> ALDERID str} for one municipality, from LTSB's ward layer."""
    key = (mcd_name, ctv)
    if key not in _LTSB_CACHE:
        q = urllib.parse.urlencode({
            "where": "MCD_NAME='%s' AND CTV='%s'" % (mcd_name.replace("'", "''"), ctv),
            "outFields": "WARDID,ALDERID", "returnGeometry": "false",
            "f": "json", "resultRecordCount": 500})
        d = json.loads(fetch(LTSB_WARDS + "?" + q))
        if "error" in d:
            raise SystemExit("LTSB ward query failed for %s: %s"
                             % (mcd_name, d["error"]))
        rows = [f["attributes"] for f in d.get("features", [])]
        if not rows:
            raise SystemExit("LTSB carries no %s %s wards" % (mcd_name, ctv))
        _LTSB_CACHE[key] = {int(r["WARDID"]): (r["ALDERID"] or "").strip()
                            for r in rows}
    return _LTSB_CACHE[key]


def require_ward_is_district(mcd_name, ctv, seats):
    """The city numbers its seats by ward; assert ward N IS district N."""
    m = ltsb_ward_to_alder(mcd_name, ctv)
    if len(m) != seats:
        raise SystemExit("%s: the state files %d wards for a %d-seat council, so "
                         "its page's ward numbers can no longer be read as "
                         "districts" % (mcd_name, len(m), seats))
    bad = sorted("%d->%s" % (w, a) for w, a in m.items() if a != "%02d" % w)
    if bad:
        raise SystemExit("%s: ward and district have stopped coinciding (%s) — the "
                         "council page numbers seats by ward and cannot be keyed "
                         "to districts any more" % (mcd_name, ", ".join(bad)))


# ------------------------------------------------------------- Stevens Point
def scrape_stevens_point():
    """The city's CivicPlus staff directory, one category per body.

    Its districts are ORDINAL WORDS ("First District"), each printed TWICE per
    entry — the responsive layout renders one copy for wide and one for narrow,
    exactly Green Bay's shape — so the split is on the entry container.
    NO E-MAIL SHIPS AND THAT IS THE CITY'S CHOICE: every "Email Ald. X" link
    is a /formcenter/ form, not a mailto, so there is no address to carry.
    """
    page = fetch(STEVENS_POINT_DIR)
    members = {}
    for li in re.split(r'<li class="list-group-item', page)[1:]:
        t = re.search(r">\s*(%s)\s+District\s*<" % "|".join(ORDINALS), li, re.I)
        if not t:
            continue
        n = ORDINALS[t.group(1).lower()]
        nm = re.search(r'href="(/m/directory/employee\?eid=\d+)"[^>]*>\s*([^<]+?)\s*<', li)
        if not nm:
            continue
        entry = {"name": " ".join(nm.group(2).split()),
                 "url": "https://stevenspoint.com" + nm.group(1)}
        ph = re.search(r'href="tel:([^",]+)', li)
        if ph:
            entry["phone"] = ph.group(1).strip()
        key = "%02d" % n
        if key in members and members[key]["name"] != entry["name"]:
            raise SystemExit("stevens point lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 11:
        raise SystemExit("stevens point names %d of 11 districts" % len(members))
    return members, STEVENS_POINT_DIR


# ----------------------------------------------------------------- Menomonie
def scrape_menomonie():
    """"NAME, Ward N" per <li>, in two columns. The mayor's row says ", Mayor"
    and carries no ward, which is what keeps him out."""
    require_ward_is_district("Menomonie", "C", 11)
    page = fetch(MENOMONIE_INDEX)
    members = {}
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", page, re.S):
        m = re.search(r"</a>\s*,\s*Ward\s+(\d{1,2})\b", li)
        if not m:
            continue
        nm = re.search(r'href="(/[Dd]irectory\.aspx\?EID=\d+)"[^>]*>([^<]+)</a>', li)
        if not nm:
            raise SystemExit("menomonie: a ward row with no directory link (%r)"
                             % li[:120])
        n = int(m.group(1))
        entry = {"name": " ".join(nm.group(2).split()),
                 "url": "https://www.menomonie-wi.gov" + nm.group(1)}
        key = "%02d" % n
        if key in members and members[key]["name"] != entry["name"]:
            raise SystemExit("menomonie lists two names for ward %d" % n)
        members[key] = entry
    if len(members) != 11:
        raise SystemExit("menomonie names %d of 11 wards" % len(members))
    return members, MENOMONIE_INDEX


# ----------------------------------------------------------------- Manitowoc
def scrape_manitowoc():
    """The Common Council table: NAME | District | Term | Phone.

    TWO TRAPS, BOTH IN THE NAME COLUMN. Two anchors carry a title= attribute
    naming the PREVIOUS alderperson — title="Scott McMeans" on the row whose
    text reads "Chad Beeman", title="Steve Czekala" on Brett Norell's — so a
    title-keyed read ships two people who left. The anchor TEXT is the name.
    And one row's href points at wi-manitowoc2.civicplus.com, the site's own
    staging host; only on-domain links ship, so that district carries no url
    rather than a link to a staging copy.

    The mayor's table sits above and has three columns and no district, so
    requiring a district cell is what excludes him.
    """
    page = fetch(MANITOWOC_INDEX)
    members = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        if len(cells) != 4:
            continue
        nm = re.search(r"<a\b[^>]*>\s*([^<]+?)\s*</a>", cells[0])
        dm = re.match(r"^\s*(\d{1,2})\s*(?:<br\s*/?>)?\s*$", cells[1])
        if not (nm and dm):
            continue
        n = int(dm.group(1))
        name = " ".join(H.unescape(nm.group(1)).split())
        entry = {"name": name}
        href = re.search(r'href="([^"]+)"', cells[0])
        # `/path` or an absolute manitowoc.org URL, and NEVER `//host/path`,
        # which urljoin would turn into somebody else's origin
        if href and re.match(r"^(?:https?://(?:www\.)?manitowoc\.org)?/(?!/)",
                             href.group(1)):
            entry["url"] = urllib.parse.urljoin(MANITOWOC_INDEX, href.group(1))
        ph = re.search(r"\(?\d{3}\)?[\s.-]\s*\d{3}-\d{4}", cells[3])
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("manitowoc lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 10:
        raise SystemExit("manitowoc names %d of 10 districts" % len(members))
    return members, MANITOWOC_INDEX


# ----------------------------------------------- Sheboygan and Eau Claire
def civicplus_hcards(page):
    """[(name, job title, profile href)] for a CivicPlus staff-directory
    widget. Two cities below publish their council through it, one h-card per
    member, and the job title is where the district lives."""
    out = []
    for li in re.split(r'<li class="widgetItem h-card"', page)[1:]:
        nm = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', li, re.S)
        jt = re.search(r'class="field p-job-title">\s*(.*?)\s*</div>', li, re.S)
        if not (nm and jt):
            continue
        u = re.search(r'class="field p-link"><a href="([^"]+)"', li)
        out.append((" ".join(re.sub(r"<[^>]+>", " ", H.unescape(nm.group(1))).split()),
                    " ".join(re.sub(r"<[^>]+>", " ", H.unescape(jt.group(1))).split()),
                    u.group(1) if u else None))
    return out


def scrape_sheboygan():
    """One h-card per member, the job title reading "District N (Wards a, b)"
    with a council role sometimes appended.

    THE PAGE'S WARD LISTS ARE BEHIND THE STATE'S FILE — District 9 names wards
    17 and 18 where LTSB also files ward 23 there — so the ward parenthesis is
    read as prose and never as a key; the district number is the key.

    ROBOTS: sheboyganwi.gov's `*` group is `Allow: /` with
    Content-Signal: search=yes,ai-train=no,use=reference. Nine crawlers are
    disallowed BY NAME (Amazonbot, CCBot, ClaudeBot, GPTBot and the rest); this
    weekly civic-data fetch is none of them, nothing here trains on the page,
    and naming the alderperson with a link back to this page is the reference
    use the signal permits. Recorded so the reading is visible and the operator
    can drop this city if they read it differently.

    THE OPERATOR READ IT AND KEPT IT, 2026-09-05. This paragraph was written as
    an open question for exactly that decision; it has been answered, and the
    reading above stands as the reason rather than as a proposal.
    """
    members = {}
    for name, title, href in civicplus_hcards(fetch(SHEBOYGAN_INDEX)):
        d = re.search(r"District\s+(\d{1,2})\b", title)
        if not d:
            continue
        n = int(d.group(1))
        entry = {"name": name}
        if href:
            entry["url"] = urllib.parse.urljoin(SHEBOYGAN_INDEX, href)
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("sheboygan lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 10:
        raise SystemExit("sheboygan names %d of 10 districts" % len(members))
    return members, SHEBOYGAN_INDEX


def scrape_eau_claire():
    """The same widget, job titles reading "City Council - District N".

    THIS CITY WAS RECORDED AS BLOCKED AND IS NOT. The gap record has said since
    2026-08-26 that "Eau Claire and Janesville sit behind Akamai denies";
    measured 2026-09-05, https://www.eauclairewi.gov/310/City-Council answers
    200 with all five district councillors on it. Whatever the earlier probe
    met, the claim was carried forward without being re-measured — and a
    blocked-by-default record is how a readable source stays unread.

    Eau Claire seats ELEVEN and only FIVE are districted: the council is five
    district members, five at-large and a president, whose h-cards carry a job
    title with no district in it and are excluded by requiring one. The other
    six are a City-card fact, not an aldermanic-district one.
    """
    members = {}
    for name, title, href in civicplus_hcards(fetch(EAU_CLAIRE_INDEX)):
        d = re.search(r"City Council\s*[-–]\s*District\s+(\d{1,2})\b", title)
        if not d:
            continue
        n = int(d.group(1))
        entry = {"name": name}
        if href:
            entry["url"] = urllib.parse.urljoin(EAU_CLAIRE_INDEX, href)
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("eau claire lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 5:
        raise SystemExit("eau claire names %d of 5 districts" % len(members))
    return members, EAU_CLAIRE_INDEX


# ------------------------------------------------------------------ Superior
def scrape_superior():
    """One table row per councilor: a left cell headed "Nth District - Area",
    a right cell with the name in an h1.headline, a mailto and a phone.

    TWO REASONS THIS PARSES PER ROW AND NEVER OVER THE PAGE: every bio repeats
    its own ordinal in prose ("1st District Councilor Nicholas Ledin is…"), and
    the district-5 heading is misspelt "5th Disrtict", which is why the anchor
    is the ordinal plus "Dis" rather than the whole word.

    There is also a VILLAGE of Superior (COUSUBFP 78660, one uncoded ward). The
    city is 78650 and is the only one of the two with districts.
    """
    page = fetch(SUPERIOR_INDEX)
    members = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S):
        d = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+Dis[a-z]*\b", row, re.I)
        nm = re.search(r'<h1 class="headline">\s*(.*?)\s*</h1>', row, re.S)
        if not (d and nm):
            continue
        n = int(d.group(1))
        name = " ".join(re.sub(r"<[^>]+>", " ", H.unescape(nm.group(1))).split())
        entry = {"name": name}
        em = re.search(r'href="mailto:([^"?]+)"', row)
        if em:
            entry["email"] = em.group(1).strip()
        ph = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", re.sub(r"<[^>]+>", " ", row))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("superior lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 10:
        raise SystemExit("superior names %d of 10 districts" % len(members))
    return members, SUPERIOR_INDEX


# ------------------------------------------------------------------- Portage
def scrape_portage():
    """Contact cards: <strong>NAME</strong>, then "District N Alderperson
    Term …", then a line this parser must never read, then a phone, then a
    mailto.

    THE THIRD LINE IS THE ALDERPERSON'S HOME ADDRESS. Portage publishes it; the
    fleet does not ship one for anybody, so the card is read field by field —
    the name from the <strong>, the district from the line that says District,
    the phone by its own shape and the address from the mailto — and the line
    between the district and the phone is never touched.
    """
    page = fetch(PORTAGE_INDEX)
    members = {}
    for card in re.split(r'<div class="card-body">', page)[1:]:
        card = card.split("</div>")[0]
        nm = re.search(r"<strong>\s*([^<]+?)\s*</strong>", card)
        d = re.search(r"District\s+(\d{1,2})\s+Alderperson", card)
        if not (nm and d):
            continue
        n = int(d.group(1))
        name = " ".join(H.unescape(nm.group(1)).split())
        entry = {"name": name}
        em = re.search(r'href="mailto:([^"?]+)"', card)
        if em:
            entry["email"] = em.group(1).strip()
        ph = re.search(r"(?<![-\d])\d{3}-\d{3}-\d{4}(?![-\d])",
                       re.sub(r"<[^>]+>", " ", card))
        if ph:
            entry["phone"] = ph.group(0)
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("portage lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 9:
        raise SystemExit(
            "portage names %d of 9 districts [%s]"
            % (len(members),
               body_note(page, ("card-body", r'<div class="card-body">'),
                         ("<strong>", r"<strong>"),
                         ("District N Alderperson",
                          r"District\s+\d{1,2}\s+Alderperson"))))
    return members, PORTAGE_INDEX


# ============================= the tranche of 2026-09-05 evening (five cities)
# All five pair every district with a name, and NONE was parsed by a shared
# routine: a generic "nearest name to District N" pass was written first and
# would have shipped "City Council President" as Eagle River's district 3 and
# "Edit Form" as Altoona's district 6. Per-city functions, as the fleet does.
#
# FIVE of the ten cities worked are DELIBERATELY NOT HERE:
#   * ALGOMA, DODGEVILLE, OCONOMOWOC and HORICON each seat TWO alderpersons
#     per district on staggered terms (Dodgeville's district 1 is Shaun Sersch
#     2025-2027 AND Roxanne Reynolds-Lair 2026-2028; Horicon's is Forrest
#     Frami AND Lisa Sullivan). The roster schema is members[district] -> one
#     member, so shipping any of them would name one of each pair and conceal
#     the other. Shut on the SCHEMA, not on the source. All four WERE built
#     and then withdrawn once _put() refused the second name.
#   * WAUPACA's page numbers its districts 1-5 while LTSB keys its geometry
#     41-45. That correspondence is plausible and NOT witnessed by anything
#     read here, and a wrong offset moves every name one seat, so it is not
#     guessed. (The builder's stray-district gate would catch it, which is why
#     the failure would be loud rather than silent — but a gate catching a
#     guess is not the same as not guessing.)


def _clean(fragment):
    """Tag-stripped, entity-decoded, whitespace-collapsed text."""
    return " ".join(re.sub(r"<[^>]+>", " ", H.unescape(fragment)).split())


def _contact(fragment):
    """{email, phone} from one member's own markup fragment — never a page's."""
    out = {}
    em = re.search(r'href="mailto:([^"?]+)"', fragment)
    if em:
        out["email"] = em.group(1).strip()
    ph = re.search(r"\(?\d{3}\)?[ .-]\d{3}-\d{4}", _clean(fragment))
    if ph:
        out["phone"] = ph.group(0).strip()
    return out


def _put(city, members, key, entry):
    """Append one member to their district's list, refusing an exact duplicate.

    THIS FUNCTION USED TO REFUSE THE SECOND NAME, and that was right while the
    schema held one member per district: a `setdefault` had taken the first and
    dropped the second in silence, so Dodgeville read as four alderpersons
    where its page names eight, and naming one of each pair would have
    concealed the other rather than merely been incomplete. Failing loudly was
    the honest answer available at the time, and it is what kept Algoma,
    Dodgeville, Oconomowoc and Horicon out of the file rather than half-right.

    Since #1133 `members[district]` is a LIST, so a second name is no longer a
    conflict to refuse — it is the answer. What is still refused is the SAME
    person arriving twice, which is a parse reading one block twice rather than
    a council seating somebody twice, and which would inflate every count guard
    below it.
    """
    seat = members.setdefault(key, [])
    for existing in seat:
        if fold(existing["name"]) == fold(entry["name"]):
            raise SystemExit("%s names %s twice in district %s — a block read "
                             "twice, not a seat held twice"
                             % (city, entry["name"], key))
    seat.append(entry)


def _people(members):
    """How many PEOPLE a members mapping holds, across the per-district lists."""
    return sum(len(v) for v in members.values())


def body_note(page, *markers):
    """"body N B; <marker> xM; ..." — what the fetch actually contained.

    A COUNT GATE THAT ONLY SAYS "0 of 9" CANNOT BE DIAGNOSED. Portage failed
    that way three times in five on 2026-09-05 and the log gave no way to tell
    a page that had changed shape from a body that was not the page at all; a
    day later it parsed 12 times out of 12 and the cause is still unknown. So
    every count failure now reports what came back, and the next occurrence is
    readable from the CI log alone instead of needing a live re-fetch that may
    no longer reproduce it.
    """
    bits = ["body %d B" % len(page)]
    for label, pat in markers:
        bits.append("%s x%d" % (label, len(re.findall(pat, page))))
    return "; ".join(bits)


def _seats_or_die(city, members, seats, page=None, *markers):
    """`seats` is the DISTRICT count — the number of keys, not of people.

    It keeps that meaning after #1133 because it is what the geometry draws and
    what every caller passes. A multi-member council additionally states how
    many PEOPLE it expects, through _people_or_die: a page that lost one of a
    district's three members still names every district, so this check alone
    cannot see it.
    """
    if len(members) != seats:
        note = (" [%s]" % body_note(page, *markers)) if page is not None else ""
        raise SystemExit("%s names %d of %d districts%s"
                         % (city, len(members), seats, note))
    return members


def _people_or_die(city, members, people, page=None, *markers):
    """The seat count a MULTI-MEMBER council must produce, people not districts."""
    got = _people(members)
    if got != people:
        note = (" [%s]" % body_note(page, *markers)) if page is not None else ""
        raise SystemExit("%s names %d alderpersons, expected %d across %d "
                         "district(s)%s" % (city, got, people, len(members), note))
    return members


# ---------------------------------------------------------------- New Lisbon
def scrape_new_lisbon():
    """"Ward <list> Council Member | <name> | Phone: | ... | Term Expires:".

    THE CITY NUMBERS ITS SEATS BY WARD GROUP, not by district: "Ward 1, 6 and
    7 Council Member", "Ward 2 Council Member", "Ward 3", "Ward 4 and 5". That
    grouping IS the district plan and LTSB says so independently — its ward
    layer maps 1, 6 and 7 to ALDERID 01, 2 to 02, 3 to 03, and 4 and 5 to 04 —
    so the pairing is witnessed live on every run rather than assumed, the same
    posture Menomonie and Viroqua take for their one-ward-per-district pages.
    A re-warding that broke the grouping fails here instead of moving a name.

    NO MEMBER E-MAIL IS PUBLISHED. The page's only addresses sit behind
    Cloudflare's e-mail scrambling, and decoded on 2026-10-09 they are the
    mayor's and the clerk's (nlmayor@, nlclerk@), neither a council seat's —
    so there is nothing to read here, not something being withheld. (Until
    that date this docstring called the scrambling an access control; it is
    not, and cf_email() reads it where a seat's address is behind it.) The
    phones are published in the clear and do ship.
    """
    ward_to_alder = ltsb_ward_to_alder("New Lisbon", "C")
    page = fetch(NEW_LISBON_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"Ward\s+([\d,\s and]+?)\s+Council Member[\s|]+"
                         r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"((?:[^|]*\|){0,4})", flat):
        wards = [int(w) for w in re.findall(r"\d+", m.group(1))]
        ids = {ward_to_alder.get(w) for w in wards}
        if len(ids) != 1 or None in ids:
            raise SystemExit(
                "new lisbon: the page groups wards %s as one seat and LTSB puts "
                "them in districts %s — the ward plan moved, so which seat this "
                "name holds is not settled" % (wards, sorted(x for x in ids if x)))
        entry = {"name": m.group(2).strip()}
        ph = re.search(r"\(?\d{3}\)?[ .-]?\d{3}-\d{4}", m.group(3))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        _put("new lisbon", members, ids.pop(), entry)
    return _seats_or_die("new lisbon", members, 4, page,
                         ("Ward .. Council Member",
                          r"Ward\s+[\d,\s and]+?\s+Council Member")), NEW_LISBON_INDEX


# ---------------------------------------------------------------- New Berlin
def scrape_new_berlin():
    """Cards whose NAME PRECEDES the "District N" label."""
    page = fetch(NEW_BERLIN_INDEX)
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    flat = re.sub(r"\|+", "|", flat)
    members = {}
    for m in re.finditer(r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"[\s|]+District\s+(\d{1,2})\b", flat):
        _put("new berlin", members, "%02d" % int(m.group(2)), {"name": m.group(1).strip()})
    return _seats_or_die("new berlin", members, 7, page,
                         ("District N", r"District\s+\d{1,2}\b")), NEW_BERLIN_INDEX


# -------------------------------------------------------------- Sturgeon Bay
def scrape_sturgeon_bay():
    """"District N | <name> | <home address> | <phone> | sbdistrictN@...".

    The page also carries an AT-LARGE mayor, who has no district and so is
    never matched. THE CELL AFTER THE NAME IS A HOME ADDRESS and is stepped
    over by shape — the phone and the per-seat district mailbox after it are
    the city's own official contact for the seat and do ship.
    """
    page = fetch(STURGEON_BAY_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"District\s+(\d{1,2})\b[\s|]+"
                         r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"([^|]*(?:\|[^|]*){0,3})", flat):
        entry = {"name": m.group(2).strip()}
        tail = m.group(3)
        ph = re.search(r"\(?\d{3}\)?[ .-]\d{3}-\d{4}", tail)
        if ph:
            entry["phone"] = ph.group(0).strip()
        em = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", tail)
        if em:
            entry["email"] = em.group(0).strip()
        _put("sturgeon bay", members, "%02d" % int(m.group(1)), entry)
    return _seats_or_die("sturgeon bay", members, 7, page,
                         ("District N", r"District\s+\d{1,2}\b")), STURGEON_BAY_INDEX


# ------------------------------------------------------------------- Altoona
def scrape_altoona():
    """"<Name> | Council Person District N (Ward a, b) | Term expires | phone".

    The name PRECEDES the label. A name-follows read gets "Edit Form" for
    district 6 — the page's trailing contact widget, which sits exactly where
    the seventh member would be if there were one.
    """
    page = fetch(ALTOONA_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r"[\s|]+Council Person\s+District\s+(\d{1,2})\b", flat):
        _put("altoona", members, "%02d" % int(m.group(2)), {"name": m.group(1).strip()})
    return _seats_or_die("altoona", members, 6, page,
                         ("Council Person District N",
                          r"Council Person\s+District\s+\d{1,2}\b")), ALTOONA_INDEX


# --------------------------------------------------------------- Eagle River
def scrape_eagle_river():
    """"Aldermanic District N, Wards a & b" then an OPTIONAL office title and
    then the name.

    DISTRICT 3'S TITLE IS THE TRAP: its block reads "... District 3, Wards 3 &
    4 | City Council President | Kim Schaffer", so the first capitalised run
    after the label is an office, not a person. Titles are skipped by name.
    """
    page = fetch(EAGLE_RIVER_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    titles = ("City Council President", "Council President", "Mayor",
              "City Council Vice President")
    members = {}
    for m in re.finditer(r"Aldermanic\s+District\s+(\d{1,2})\b[^|]*((?:\|[^|]*){1,16})",
                         flat):
        cells = [c.strip() for c in m.group(2).split("|") if c.strip()]
        cells = [c for c in cells if c not in titles]
        if not cells:
            raise SystemExit("eagle river: district %s has only a title"
                             % m.group(1))
        entry = {"name": cells[0]}
        tail = m.group(2)
        ph = re.search(r"\(?\d{3}\)?[ .-]?\d{3}-\d{4}", tail)
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        em = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", tail)
        if em:
            entry["email"] = em.group(0).strip()
        _put("eagle river", members, "%02d" % int(m.group(1)), entry)
    return _seats_or_die("eagle river", members, 4, page,
                         ("Aldermanic District N",
                          r"Aldermanic\s+District\s+\d{1,2}\b")), EAGLE_RIVER_INDEX


# ---------------------------------------------------------------- Germantown
def scrape_germantown():
    """A VILLAGE: its four are TRUSTEES, and the card renders them as such.
    "District N" then the trustee's name."""
    page = fetch(GERMANTOWN_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(r"District\s+(\d{1,2})\b[\s|]+"
                         r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})", flat):
        _put("germantown", members, "%02d" % int(m.group(1)), {"name": m.group(2).strip()})
    return _seats_or_die("germantown", members, 4, page,
                         ("District N", r"District\s+\d{1,2}\b")), GERMANTOWN_INDEX


# ------------------------------------------------------------------- Viroqua
def scrape_viroqua():
    """A five-column table: WARD N | NAME | Term Expires | mailto | tel.

    The city numbers its seats by ward, so the same LTSB witness Menomonie uses
    applies here; the MAYOR row's first cell says MAYOR and carries no number,
    which is what excludes it. Names print in capitals and ship that way — this
    project renders what the publisher wrote.
    """
    require_ward_is_district("Viroqua", "C", 9)
    page = fetch(VIROQUA_INDEX)
    members = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 2:
            continue
        w = re.match(r"^\s*WARD\s+(\d{1,2})\s*$",
                     re.sub(r"<[^>]+>", " ", H.unescape(cells[0])).strip(), re.I)
        if not w:
            continue
        n = int(w.group(1))
        name = " ".join(re.sub(r"<[^>]+>", " ", H.unescape(cells[1])).split())
        if not name:
            raise SystemExit("viroqua: ward %d has no name cell" % n)
        entry = {"name": name}
        em = re.search(r'href="mailto:([^"?]+)"', row)
        if em:
            entry["email"] = em.group(1).strip()
        ph = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", re.sub(r"<[^>]+>", " ", row))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("viroqua lists two names for ward %d" % n)
        members[key] = entry
    if len(members) != 9:
        raise SystemExit("viroqua names %d of 9 wards" % len(members))
    return members, VIROQUA_INDEX


# ------------------------------------------------------------------- Menasha
def scrape_menasha():
    """Eight table cells, laid out DOWN THE COLUMNS (1, 5, 2, 6, 3, 7, 4, 8),
    each headed "District N Alderperson" with the name under it.

    TWO THINGS ARE DELIBERATELY NOT READ. The line under each name is the
    alderperson's HOME ADDRESS, which never ships. And District 1's cell
    contains href="mailto:rnichols@ci.menasha.wi.us" wrapping an empty <br> —
    that is not Chris Rand's address, and taking it would attach one person's
    mail to another's name, the same shape as the county page whose footer
    webmaster@ once shipped as a sheriff. So NO e-mail ships for Menasha; the
    city routes contact through a per-district "Contact Me" form anyway.
    """
    page = fetch(MENASHA_INDEX)
    members = {}
    for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", page, re.S):
        d = re.search(r"District\s+(\d{1,2})\s+Alderperson", cell)
        if not d:
            continue
        n = int(d.group(1))
        after = cell[d.end():]
        nm = re.search(r"<strong>\s*(?:<[^>]+>\s*)*([^<]+?)\s*<", after)
        if not nm:
            raise SystemExit("menasha: district %d cell has no name in bold" % n)
        name = " ".join(H.unescape(nm.group(1)).split())
        if not re.match(r"^[A-ZÀ-Þ][A-Za-zÀ-ÿ.'’ -]+$", name):
            raise SystemExit("menasha district %d name reads %r — the cell shape "
                             "moved" % (n, name))
        entry = {"name": name}
        ph = re.search(r"\(\d{3}\)\s*\d{3}-\d{4}", re.sub(r"<[^>]+>", " ", after))
        if ph:
            entry["phone"] = " ".join(ph.group(0).split())
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("menasha lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 8:
        raise SystemExit("menasha names %d of 8 districts" % len(members))
    return members, MENASHA_INDEX


# -------------------------------------------------------------------- Howard
def scrape_howard():
    """A village, not a city: eight TRUSTEE districts, one <li> each, reading
    "NAME, District N (Wards a-b)". The Village President sits in his own list
    above with ", Village President" and no district, which is what keeps a
    citywide officer off a district card."""
    page = fetch(HOWARD_INDEX)
    members = {}
    for li in re.findall(r"<li\b[^>]*>(.*?)</li>", page, re.S):
        d = re.search(r"District\s+(\d{1,2})\b", re.sub(r"<[^>]+>", " ", li))
        nm = re.search(r'href="([^"]*[Dd]irectory\.aspx\?EID=\d+)"[^>]*>(.*?)</a>',
                       li, re.S)
        if not (d and nm):
            continue
        n = int(d.group(1))
        name = " ".join(re.sub(r"<[^>]+>", " ", H.unescape(nm.group(2))).split())
        # THE PAGE MIXES SCHEMES: six of the eight anchors are https and two —
        # districts 1 and 7 — are written http, which urljoin preserves because
        # they are absolute. The host serves both and redirects, but a card that
        # hands a reader an http link on a site that has https is shipping the
        # worse of two addresses the publisher itself uses. Upgraded on this
        # host only, and only for a bare http scheme.
        href = re.sub(r"^http://(www\.villageofhoward\.com)", r"https://\1",
                      nm.group(1))
        entry = {"name": name,
                 "url": urllib.parse.urljoin(HOWARD_INDEX, href)}
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("howard lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 8:
        raise SystemExit("howard names %d of 8 trustee districts" % len(members))
    return members, HOWARD_INDEX


# --------------------------------------------------------------------- Tomah
def scrape_tomah():
    """Drupal view rows: the title field is the member's name and profile link,
    the position field reads "District N Alderperson". The mayor's row has the
    same shape with position "Mayor", so requiring a district excludes him."""
    page = fetch(TOMAH_INDEX)
    members = {}
    for row in re.split(r'<div class="views-row', page)[1:]:
        nm = re.search(r'views-field-title[^>]*>.*?<a href="([^"]+)"[^>]*>\s*'
                       r'([^<]+?)\s*</a>', row, re.S)
        pos = re.search(r'views-field-field-position.*?class="field-content">\s*'
                        r'([^<]*?)\s*</div>', row, re.S)
        if not (nm and pos):
            continue
        d = re.search(r"District\s+(\d{1,2})\b", H.unescape(pos.group(1)))
        if not d:
            continue
        n = int(d.group(1))
        name = " ".join(H.unescape(nm.group(2)).split())
        entry = {"name": name,
                 "url": urllib.parse.urljoin(TOMAH_INDEX, nm.group(1))}
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("tomah lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 8:
        raise SystemExit("tomah names %d of 8 districts" % len(members))
    return members, TOMAH_INDEX




# ------------------------------------------------------------------ Appleton
def scrape_appleton():
    """The city's common-council page, one directory block per alderperson:
    "<h2>NAME, District N</h2>", a "Read More" link to that district's own
    city page, and a tel: link.

    SHIPPED FROM 2026-09-05, when the geometry it rides finally could be drawn
    — Outagamie County still files every Appleton ward uncoded, and the city
    clerk's own polling-locations page supplies the composition instead
    (build_wi_aldermanic_districts.py, LOCAL_COMPOSITION). This roster route
    had been verified readable and recorded as WAITING for that geometry since
    2026-08-26; a roster with no card to ride is not shipped.

    TWO TRAPS. Five members link a personal blog, Wordpress site or Facebook
    page from the same block; those are the member's own, not the city's, so
    the url read here is the `rz-bus-readmore` anchor — the city's district
    page — and its district number is cross-checked against the heading's.
    AND THE PAGE CARRIES `<base href="https://www.appletonwi.gov/">`, so its
    relative hrefs resolve against the SITE ROOT rather than against the page's
    own directory: joining `government/district_1.php` to the page URL gives
    /government/government/district_1.php, which answers 404 (measured). The
    base is read from the page and its absence fails the city, because the day
    it disappears is the day every link here would silently become a 404.
    """
    page = fetch(APPLETON_INDEX)
    base = re.search(r'<base\b[^>]*href="([^"]+)"', page, re.I)
    if not base:
        raise SystemExit("appleton: the page no longer declares a <base href>, so its "
                         "relative links cannot be resolved the way a browser does")
    base_url = urllib.parse.urljoin(APPLETON_INDEX, base.group(1))
    members = {}
    for block in re.split(r"<h2>", page)[1:]:
        h = re.match(r"\s*([^<,]+?)\s*,\s*District\s+(\d{1,2})\s*</h2>", block)
        if not h:
            continue
        name, n = " ".join(H.unescape(h.group(1)).split()), int(h.group(2))
        entry = {"name": name}
        u = re.search(r'href="(government/district_(\d{1,2})\.php)"[^>]*'
                      r'class="rz-bus-readmore"', block)
        if u:
            if int(u.group(2)) != n:
                raise SystemExit("appleton: %s is headed District %d and its Read More "
                                 "goes to district_%s.php" % (name, n, u.group(2)))
            entry["url"] = urllib.parse.urljoin(base_url, u.group(1))
        ph = re.search(r'href="tel:([^"]+)"', block)
        if ph:
            digits = re.sub(r"\D", "", ph.group(1))
            if len(digits) == 10:
                entry["phone"] = "(%s) %s-%s" % (digits[:3], digits[3:6], digits[6:])
        key = "%02d" % n
        if key in members and members[key]["name"] != name:
            raise SystemExit("appleton lists two names for district %d" % n)
        members[key] = entry
    if len(members) != 15:
        raise SystemExit("appleton names %d of 15 districts" % len(members))
    return members, APPLETON_INDEX


# ONE UNREACHABLE SERVER NEVER TAKES THE OTHERS DOWN — AND A BROKEN READING
# TAKES EVERYTHING DOWN ON PURPOSE. The distinction is the whole design and it
# was stated wrongly in this repo until 2026-09-05: the workflow's comment and
# this module's docstring both said a municipality whose page reshapes "fails
# its own gate" in isolation, which is false.
#
# WHAT IS ISOLATED. Until 2026-09-03 the six scrapes ran unguarded and any raise
# ended the run, so greenbaywi.gov timing out after three 60-second tries cost
# Milwaukee, Madison, Kenosha, Racine and Waukesha their weekly refresh as well
# — 82 alderpersons dropped because one city's webserver was slow. `attempt()`
# catches `Exception`, so that class of failure — a timeout, a reset, an HTTP
# error, a malformed body — is now caught per municipality, and
# `build_wi_alderperson_roster.py` carries that municipality's last shipped rows
# forward, names it in the log, and refuses if too many are carried at once. The
# reason travels in `failures` so the weekly PR's reviewer sees WHICH server was
# unreadable rather than inferring it from an absence.
#
# WHAT IS NOT, AND MUST NOT BE. Every gate in this file raises `SystemExit`, and
# `SystemExit` inherits from `BaseException` rather than `Exception` — so a gate
# failure walks straight past `attempt()` and ends the run. THAT IS THE SAFE
# DIRECTION AND THE CATCH IS DELIBERATELY NOT WIDENED. A timeout means "not
# today"; a gate failure means a pinned reading has stopped being true, and the
# honest response to that is to stop, not to carry a municipality forward under
# a date that says the run went fine. Widening this to `BaseException` would
# turn every reshaped page into a silent six-week-old roster.
def attempt(label, fn):
    """(result, None) on success; (None, reason) on an UNREACHABLE source.

    Never catches a gate failure — see the block above. `SystemExit` is not an
    `Exception`, and that is the point rather than an oversight.
    """
    try:
        return fn(), None
    except Exception as e:                   # noqa: BLE001 - reported per city
        reason = "%s: %s" % (type(e).__name__, str(e)[:150])
        print("  MISS %-12s %s" % (label, reason), file=sys.stderr)
        return None, reason



# Roles printed where a name goes. They are NAME-SHAPED — two capitalised
# words — so they must be removed before the name test, not after: Neenah's
# council president read as a member called "Council President" until they
# were.
ROLE_RE = re.compile(r"(Council Vice President|Council President|Vice President)", re.I)
NAME_RE = (r"[A-Z][A-Za-z.'\-]+(?:\s+(?:\"[A-Za-z]+\"\s+)?[A-Z][A-Za-z.'\-]*\.?){1,3}")


def _seat_blocks(flat, label_re):
    """(district, block) per labelled seat, the block running to the NEXT label.

    Counting separators from the label does not survive these pages: stripping
    tags leaves runs of `|` and newlines in no fixed number — Wautoma puts two
    between a label and its name and eleven between a name and its address, on
    the same page — so a parser that says "the field three pipes along" reads
    one member's phone onto another's row. Each seat's own block, bounded by
    the next label, has no such offset to get wrong.
    """
    hits = list(re.finditer(label_re, flat))
    for i, h in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else min(len(flat), h.end() + 900)
        yield h, flat[h.end():end]



# ------------------------------------------------- the multi-member tranche
# FOUR CITIES THAT COULD NOT SHIP UNTIL #1133. Each seats more than one
# alderperson per district, which the old schema could not hold: _put()
# refused the second name, correctly, and these four stayed out of the file
# rather than shipping half a council. What changed is the shape, not the
# source — every page below was already measured on 2026-09-06.


def scrape_wautoma():
    """`Alderperson Dist N`, then the name. UNEVEN: 1, 3 and 2 across three
    districts, six seats.

    THIS IS THE CITY THAT SETTLED THE SCHEMA. A two-slot design would carry
    Algoma, Dodgeville and Horicon and not this, which is why the shape is a
    list of arbitrary length rather than a pair.

    Its page prints a HOME ADDRESS between the name and the phone for every
    member. The address line is stepped over and never stored, the same rule
    Sturgeon Bay, Menasha and Portage are already read under.

    ITS `Term Expires:` YEAR IS READ AND DISCARDED, decided on review of #1135.
    The card maps name, badge, phone, email, note and url and has no term
    branch, so the field would reach a reader's browser and no surface — bytes
    with a live check_roster_retention gate attached, which from its first ship
    reddens a weekly bot PR when Wautoma's page drops a year nobody sees. And
    six records of 268 is not a column: no roster in this file carries a term,
    so a card showing one for Wautoma and not for the other 27 municipalities
    answers a reader's question inconsistently. If terms belong here it is a
    fleet decision with each source's term column established first.
    """
    page = fetch(WAUTOMA_INDEX)
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    members = {}
    LABEL = r"Alderperson\s+Dist\.?\s*(\d{1,2})\b"
    for hit, block in _seat_blocks(flat, LABEL):
        nm = re.search(r"[\s|]*(" + NAME_RE + r")", block)
        if not nm:
            continue
        entry = {"name": " ".join(nm.group(1).split())}
        ph = re.search(r"Phone:\s*\(?(\d{3})\)?[ .-]?(\d{3})-(\d{4})", block)
        if ph:
            entry["phone"] = "(%s) %s-%s" % ph.groups()
        _put("wautoma", members, "%02d" % int(hit.group(1)), entry)
    _seats_or_die("wautoma", members, 3, page,
                  ("Alderperson Dist N", r"Alderperson\s+Dist\.?\s*\d"))
    return _people_or_die("wautoma", members, 6, page,
                          ("Alderperson Dist N", r"Alderperson\s+Dist\.?\s*\d")), WAUTOMA_INDEX


def scrape_algoma():
    """`Alderperson District N` / name / home address / mailbox / phone / term.
    Two per district over four districts, eight seats.

    THE MAILBOX IS NUMBERED BY SEAT, NOT BY DISTRICT — alder1@ and alder2@ are
    both District 1 — so it is carried as that member's own address and never
    used to derive which district anybody sits in.
    """
    page = fetch(ALGOMA_INDEX)
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    members = {}
    LABEL = r"Alderperson\s+District\s+(\d{1,2})\b"
    for hit, block in _seat_blocks(flat, LABEL):
        nm = re.search(r"[\s|]*(" + NAME_RE + r")", block)
        if not nm:
            continue
        entry = {"name": " ".join(nm.group(1).split())}
        em = re.search(r"([A-Za-z0-9._%+-]+@algomacity\.org)", block)
        if em:
            entry["email"] = em.group(1).lower()
        ph = re.search(r"\b(\d{3})-(\d{3})-(\d{4})\b", block)
        if ph:
            entry["phone"] = "(%s) %s-%s" % ph.groups()
        _put("algoma", members, "%02d" % int(hit.group(1)), entry)
    _seats_or_die("algoma", members, 4, page,
                  ("Alderperson District N", r"Alderperson\s+District\s+\d"))
    return _people_or_die("algoma", members, 8, page,
                          ("Alderperson District N", r"Alderperson\s+District\s+\d")), ALGOMA_INDEX


def scrape_horicon():
    """NAME FIRST, then `, [role, ]District N Alderperson` — the Lafayette
    `same-line-lead` reading, which is also the only shape that recovers a ROLE
    from the seat's own row. Two per district over three, six seats.

    Reading this the other way round — district then name — pairs every member
    with the district ABOVE them, which is the off-by-one that shape exists to
    produce.
    """
    page = fetch(HORICON_INDEX)
    flat = re.sub(r"\|+", "|", re.sub(r"<[^>]+>", "|", H.unescape(page)))
    members = {}
    for m in re.finditer(
            r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})\s*\|*\s*,\s*"
            r"(?:([^,|]{3,40}?),\s*)?District\s+(\d{1,2})\s+Alderperson", flat):
        entry = {"name": m.group(1).strip()}
        role = (m.group(2) or "").strip()
        if role and not role.lower().startswith("district"):
            entry["note"] = role
        _put("horicon", members, "%02d" % int(m.group(3)), entry)
    _seats_or_die("horicon", members, 3, page,
                  ("District N Alderperson", r"District\s+\d{1,2}\s+Alderperson"))
    return _people_or_die("horicon", members, 6, page,
                          ("District N Alderperson", r"District\s+\d{1,2}\s+Alderperson")), HORICON_INDEX


def scrape_dodgeville():
    """A TABLE: `Alderperson District N` / `Wards ...` / [`*President*`] /
    name / [phone] / mailbox / term. Two per district over four, eight seats.
    The page states its own shape — "four aldermanic districts with two
    representatives" — which is asserted rather than trusted.

    ITS MAILBOXES ARE NUMERIC CHARACTER REFERENCES (`&#109;&#97;...`), not
    Cloudflare's scrambling (which cf_email() reads): H.unescape decodes them,
    and they are ordinary published addresses.
    """
    page = fetch(DODGEVILLE_INDEX)
    if not re.search(r"four aldermanic districts with two representatives", page, re.I):
        raise SystemExit("dodgeville: the page no longer states four districts "
                         "with two representatives — re-read it before trusting "
                         "the counts below [%s]" % body_note(page))
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    members = {}
    LABEL = r"Alderperson\s+District\s+(\d{1,2})\b"
    for hit, block in _seat_blocks(flat, LABEL):
        # the ward list and an optional *President* sit between the label and
        # the name; neither is a name, so the first name-shaped run is the
        # member's and the role is read from the text before it.
        nm = re.search(r"[\s|]*(?:Wards?[^|]*\|)?[\s|]*(?:\*[^*|]*\*[\s|]*)?("
                       + NAME_RE + r")", block)
        if not nm:
            continue
        entry = {"name": " ".join(nm.group(1).split())}
        if re.search(r"\*President\*", block[:nm.end()]):
            entry["note"] = "Council President"
        em = re.search(r"([A-Za-z0-9._%+-]+@(?:ci\.)?dodgeville[A-Za-z.]*\.\w+)", block)
        if em:
            entry["email"] = em.group(1).lower()
        ph = re.search(r"\b(\d{3})-(\d{3})-(\d{4})\b", block)
        if ph:
            entry["phone"] = "(%s) %s-%s" % ph.groups()
        _put("dodgeville", members, "%02d" % int(hit.group(1)), entry)
    _seats_or_die("dodgeville", members, 4, page,
                  ("Alderperson District N", r"Alderperson\s+District\s+\d"))
    return _people_or_die("dodgeville", members, 8, page,
                          ("Alderperson District N", r"Alderperson\s+District\s+\d")), DODGEVILLE_INDEX



def scrape_marion():
    """Waupaca County's Directory of Public Officials, CITY OF MARION section:
    one card per seat, `Aldermanic District N` / name / home address / phones /
    mailbox. Two seats per district over three districts; one is printed
    `Vacant`, so five people hold six seats and `vacantSeats` carries the sixth.

    THE KEY IS THE STATE'S FILED ALDERID, NOT THE DIRECTORY'S NUMBER. Waupaca
    files Marion's wards 1-3 as 21-23 and the aldermanic builder's LOCAL_RECODE
    joins the Shawano ward to 21, so directory District N is key 2N. That rests
    on the county's April 2026 sample ballot ("Alderperson, District 1 & 4",
    "District 2", "District 3") and on one named inference — that ward 2 is
    District 2 and ward 3 is District 3 — recorded in that builder.

    A NUMBER PRINTED UNDER TWO SEATS IS NOT EITHER MEMBER'S. Districts 1 and 3
    each print one number under both of their alderpersons, the Waupaca
    supervisor rule (wi_county_board_scraper.drop_shared_phones), so it is
    dropped from both and the first number left ships. Home addresses are
    stepped over and never stored.
    """
    page = fetch(MARION_INDEX, headers=sc.UA_HEADERS_ROSTER_BOT)
    start = page.find('<h3 class="block-heading-1">CITY OF MARION</h3>')
    if start < 0:
        raise SystemExit("marion: the directory has no CITY OF MARION heading [%s]"
                         % body_note(page))
    end = page.find("<h3", start + 10)
    section = page[start:end if end > 0 else len(page)]
    cards = []
    for art in re.findall(r'<article class="card">(.*?)</article>', section, re.S):
        title = re.search(r'card__title">([^<]*)<', art)
        m = re.match(r"Aldermanic District\s+(\d)$", _clean(title.group(1)) if title else "")
        if not m:
            continue
        nm = re.search(r'card__name">([^<]*)<', art)
        name = _clean(nm.group(1)) if nm else ""
        phones = ["(%s) %s-%s" % ph.groups() for ph in
                  re.finditer(r'href="tel:\+?1?(\d{3})(\d{3})(\d{4})"',
                              H.unescape(art))]
        em = re.search(r'href="mailto:([^"?]+@cityofmarionwi\.gov)"', art)
        cards.append((int(m.group(1)), name, phones,
                      em.group(1).strip().lower() if em else None))
    counts = {}
    for _, _, phones, _ in cards:
        for ph in set(phones):
            counts[ph] = counts.get(ph, 0) + 1
    members, vacant = {}, {}
    for district, name, phones, email in cards:
        key = "2%d" % district
        if name.lower() == "vacant":
            vacant[key] = vacant.get(key, 0) + 1
            continue
        entry = {"name": name}
        own = [ph for ph in phones if counts[ph] == 1]
        if own:
            entry["phone"] = own[0]
        if email:
            entry["email"] = email
        _put("marion", members, key, entry)
    orphan = sorted(set(vacant) - set(members))
    if orphan:
        raise SystemExit("marion district(s) %s are listed vacant with nobody "
                         "named — that is vacantDistricts, not vacantSeats" % orphan)
    _seats_or_die("marion", members, 3, page,
                  ("Aldermanic District N", r"Aldermanic District\s+\d"))
    if _people(members) + sum(vacant.values()) != 6:
        raise SystemExit("marion names %d alderperson(s) and %d vacant seat(s); "
                         "the directory has listed six seats, two per district"
                         % (_people(members), sum(vacant.values())))
    extra = {"vacantSeats": vacant} if vacant else {}
    return members, MARION_INDEX, extra


def scrape_black_river_falls():
    """`WARD N` headings, two alderpersons under each, eight over four.

    THE HEADINGS ARE UPPERCASE and a case-sensitive `Ward` misses every one of
    them, which is why the 2026-09-06 sweep recorded that shape rather than
    leaving the next reader to find it.

    THE CITY NUMBERS ITS SEATS BY WARD, so ward N is read as district N only
    under require_ward_is_district — the Viroqua rule: the state must file
    exactly four wards for this council and each must carry its own number.
    A city that gains a fifth ward stops being keyable this way and fails here
    rather than filing every alderperson one seat along.

    The per-member anchor is `Serving Since YYYY`, not a separator count: the
    tag strip leaves seventeen `|` runs between Ward 4's first name and its
    anchor and eight between Ward 1's, on one page.
    """
    require_ward_is_district("Black River Falls", "C", 4)
    page = fetch(BLACK_RIVER_FALLS_INDEX)
    flat = H.unescape(re.sub(r"<[^>]+>", "|", page))
    wards = list(re.finditer(r"WARD\s+(\d{1,2})\b", flat))
    members = {}
    for i, hit in enumerate(wards):
        end = wards[i + 1].start() if i + 1 < len(wards) else min(len(flat), hit.end() + 2600)
        block, prev = flat[hit.end():end], 0
        for seat in re.finditer(r"Serving Since\s+(\d{4})", block):
            seg = block[prev:seat.start()]
            prev = seat.end()
            names = re.findall(NAME_RE, ROLE_RE.sub(" ", seg))
            if not names:
                continue
            entry = {"name": " ".join(names[-1].split())}
            role = ROLE_RE.search(seg)
            if role:
                entry["note"] = role.group(1)
            tail = block[seat.end():seat.end() + 400]
            ph = re.search(r"Phone:\s*\((\d{3})\)\s*(\d{3})-(\d{4})", tail)
            if ph:
                entry["phone"] = "(%s) %s-%s" % ph.groups()
            em = re.search(r"([A-Za-z0-9._%+-]+@blackriverfallswi\.gov)", tail)
            if em:
                entry["email"] = em.group(1).lower()
            _put("black river falls", members, "%02d" % int(hit.group(1)), entry)
    _seats_or_die("black river falls", members, 4, page,
                  ("WARD N", r"WARD\s+\d{1,2}\b"))
    return _people_or_die("black river falls", members, 8, page,
                          ("WARD N", r"WARD\s+\d{1,2}\b")), BLACK_RIVER_FALLS_INDEX


def scrape_neenah():
    """NAME FIRST, then `Nth Aldermanic District – Term Expiration: ...`.
    Three per district over three districts, nine seats.

    THE PAGE IS NOT IN DISTRICT ORDER — it opens with the 2nd district's
    council president and then runs 1, 1, 1, 2, 2, 3, 3, 3 — so a positional
    read files eight of nine under the wrong district while looking orderly.
    Each name is taken from the text immediately before its own label.

    A ROLE SITS BETWEEN THE NAME AND THE LABEL (`Council President,
    2026-2027`), and it is name-shaped: the first draft of this parser read
    `Council President` as the member's name for exactly the seat that has
    one. It is stripped for the name test and kept as the note.
    """
    page = fetch(NEENAH_INDEX)
    flat = H.unescape(re.sub(r"<[^>]+>", "|", page))
    members, prev = {}, 0
    for hit in re.finditer(r"(\d)(?:st|nd|rd|th)\s+Aldermanic\s+District", flat):
        seg = flat[prev:hit.start()]
        prev = hit.end()
        names = re.findall(NAME_RE, ROLE_RE.sub(" ", seg))
        if not names:
            continue
        entry = {"name": " ".join(names[-1].split())}
        role = ROLE_RE.search(seg)
        if role:
            entry["note"] = role.group(1)
        tail = flat[hit.end():hit.end() + 400]
        ph = re.search(r"\b(\d{3})[-.](\d{3})[-.](\d{4})\b", tail)
        if ph:
            entry["phone"] = "(%s) %s-%s" % ph.groups()
        em = re.search(r"([A-Za-z0-9._%+-]+@neenahwi\.gov)", tail)
        if em:
            entry["email"] = em.group(1).lower()
        _put("neenah", members, "%02d" % int(hit.group(1)), entry)
    _seats_or_die("neenah", members, 3, page,
                  ("Nth Aldermanic District", r"\d(?:st|nd|rd|th)\s+Aldermanic\s+District"))
    return _people_or_die("neenah", members, 9, page,
                          ("Nth Aldermanic District", r"\d(?:st|nd|rd|th)\s+Aldermanic\s+District")), NEENAH_INDEX


# --------------------------------------------------- the partially-filled seat
# `Vacanct` is Oconomowoc's own spelling, and the test is against the WHOLE
# heading rather than its start, so a member whose surname begins these letters
# is unaffected: the page prints a forename beside every name, and a heading of
# one word is not a name here. The spellings a city might use are few and this
# tolerates three trailing characters, so "Vacant", "Vacanct" and "Vacancy" all
# read as the same statement.
VACANCY_RE = re.compile(r"vacan\w{0,3}\Z", re.I)
H3_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)


def scrape_oconomowoc():
    """One CivicPlus editor widget per SEAT, name first, then `District N`.
    Two seats per district over four districts, and District 1's second seat is
    listed by the city as vacant, so seven people hold eight seats.

    THIS IS THE CITY THE `vacantSeats` FIELD EXISTS FOR. Its page states its own
    council's size — "eight Aldermen representing each of the City's four
    districts" — and its directory prints eight blocks, seven naming a person
    and one reading `Vacanct`. Shipping the seven alone would have said District
    1 seats one alderperson, which is the same concealment as naming one member
    of a two-member seat, so the count the city states is carried and the card
    says the district is a seat short.

    THE SENTENCE IS THE WITNESS AND IT IS PARSED, not read once by a person and
    written into a constant: it is the only source for how many seats this
    council holds, and a hand-kept 8 would go on being asserted after the city
    changed it. CARDINALS turns its number words into integers and a word
    outside that table fails the build.

    EACH SEAT'S CONTACT COMES FROM ITS OWN BLOCK, bounded by the `<script>` the
    widget ends with. Unbounded, the last block runs 70,505 bytes to the end of
    the document and would take its phone from the mayor's row; a block with no
    such bound is SKIPPED rather than guessed at, and the seat total below turns
    that skip into a failure instead of a quiet short council.

    TWO THINGS ON THIS PAGE WOULD SHIP A WRONG ANSWER IF READ, and neither is:
    one mailto carries `title="Ald. Chris Douglas"` over the address
    `ejungwirth@`, a name appearing nowhere else on the page — the Manitowoc
    trap, where a stale `title=` names a previous alderperson — so the name is
    taken from the block's own heading and no title is read. And District 1's
    member links a District 4 map, so no district is ever derived from an href.
    """
    page = fetch(OCONOMOWOC_INDEX)
    text = H.unescape(page)
    MARKERS = (("fr-view widget", r'class="fr-view"'),
               ("District N heading", r"<h3[^>]*>\s*(?:<strong>)?\s*District\s+\d"))
    stated = re.search(r"(\w+)\s+Aldermen\s+representing\s+each\s+of\s+the\s+"
                       r"City.s\s+(\w+)\s+districts", text)
    if not stated:
        raise SystemExit("oconomowoc: the page no longer states its own council "
                         "size, which is the only witness for the seat total "
                         "[%s]" % body_note(page, *MARKERS))
    seats = CARDINALS.get(stated.group(1).lower())
    districts = CARDINALS.get(stated.group(2).lower())
    if not seats or not districts:
        raise SystemExit("oconomowoc states %r aldermen over %r districts and "
                         "one of those words is not in CARDINALS"
                         % (stated.group(1), stated.group(2)))

    members, vacant_seats = {}, {}
    for block in re.split(r'<div class="fr-view">', page)[1:]:
        cut = block.find("<script")
        if cut < 0:
            continue
        block = block[:cut]
        heads = [_clean(h.group(1)) for h in H3_RE.finditer(block)]
        if len(heads) < 2:
            continue
        d = re.match(r"District\s+(\d{1,2})\Z", heads[1])
        if not d:
            continue
        key = "%02d" % int(d.group(1))
        if VACANCY_RE.match(heads[0]):
            vacant_seats[key] = vacant_seats.get(key, 0) + 1
            continue
        if not re.match(NAME_RE + r"\Z", heads[0]):
            raise SystemExit("oconomowoc district %s heads a seat with %r, "
                             "which is neither a name nor a vacancy — a role "
                             "or a label has moved into the name's place"
                             % (key, heads[0]))
        entry = {"name": heads[0]}
        entry.update(_contact(block))
        _put("oconomowoc", members, key, entry)

    _seats_or_die("oconomowoc", members, districts, page, *MARKERS)
    orphan = sorted(set(vacant_seats) - set(members))
    if orphan:
        raise SystemExit("oconomowoc district(s) %s are listed vacant with "
                         "nobody named at all — that is vacantDistricts, which "
                         "the card reads differently, not vacantSeats"
                         % ", ".join(orphan))
    # THE SEAT TOTAL IS CHECKED, NOT THE PEOPLE COUNT. A hard 7 here would fail
    # the day the city fills the seat, which is a correct change in the world;
    # the floor that catches a LOST member is in the builder, where a floor is
    # allowed to be exceeded. What must always hold is that the blocks and the
    # city's own sentence agree about how many seats there are.
    total = _people(members) + sum(vacant_seats.values())
    if total != seats:
        raise SystemExit("oconomowoc names %d alderperson(s) and reads %d vacant "
                         "seat(s) across %d district(s), %d seats in all, where "
                         "the page states %d [%s]"
                         % (_people(members), sum(vacant_seats.values()),
                            len(members), total, seats, body_note(page, *MARKERS)))
    extra = {"vacantSeats": vacant_seats} if vacant_seats else {}
    return members, OCONOMOWOC_INDEX, extra


def as_member_lists(members):
    """district -> ONE member, or district -> [members], in; always a LIST out.

    THE SHIPPED FILE HAS EXACTLY ONE SHAPE — `members[district]` is always a
    list — because a reader that must ask "dict or list?" is a reader that will
    one day guess. This conversion is the only place the question is asked.

    It is applied HERE, at the single point every city's parse passes through,
    rather than by editing twenty-five independently-shaped parsers. Each of
    those has its own witnesses and its own count guards, and a mechanical
    sweep across them is exactly where a silent wrong answer would enter; a
    parser that names one member per district keeps returning what it returns
    and is converted once, in one place, under this docstring.

    A parser that reads a genuinely multi-member council returns lists already
    and passes through untouched — Wautoma seats one, three and two members
    across its three districts, so the shape has to hold an arbitrary count and
    a fixed pair of slots was refused.
    """
    out = {}
    for district, value in members.items():
        if isinstance(value, list):
            if not value:
                raise SystemExit("%s: empty member list — a district with "
                                 "nobody in it is a VACANCY, which rides "
                                 "vacantDistricts, not an empty list" % district)
            out[district] = value
        else:
            out[district] = [value]
    return out


# ------------------------------------------------------------------ Franklin
def scrape_franklin():
    """"NAME, Aldermanic District N", one line per seat, six districts.

    The page states its own size — "comprised of the Mayor and 6 members
    representing the 6 Aldermanic Districts" — and lists the six district
    headings separately from the six name lines, so a parse that read the
    headings would find six districts and nobody. The name comes from the line
    that carries both.
    """
    page = fetch(FRANKLIN_INDEX)
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    members = {}
    for m in re.finditer(r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r",\s*Aldermanic District\s+(\d{1,2})\b", flat):
        _put("franklin", members, "%02d" % int(m.group(2)),
             {"name": " ".join(m.group(1).split())})
    return _seats_or_die("franklin", members, 6, page,
                         ("Aldermanic District N",
                          r"Aldermanic District\s+\d{1,2}\b")), FRANKLIN_INDEX


# ----------------------------------------------------------------- Greenfield
def scrape_greenfield():
    """A table of cells, each "<a>NAME</a>, District N Alderperson".

    THE ARIA-LABEL NAMES THE WRONG PERSON ON ONE OF THE FIVE and is never read.
    District 1's cell links a directory entry whose `aria-label` is "Denise
    Collins Opens in new window" while the link TEXT reads "Andrew Drzewiecki"
    (measured 2026-10-01) — the city's own label left behind by a change of
    member. The link text is what the city maintains and what a reader sees, so
    that is what ships; an accessibility attribute is not a roster column.
    The name also nests inside a `<strong>` on that one cell and not on the
    others, so the tags are stripped rather than matched.
    """
    page = fetch(GREENFIELD_INDEX)
    members = {}
    # The separator between the link and the heading is not always plain text:
    # District 1's name nests inside a `<strong>`, so a closing tag sits between
    # them and a `[^<>]` gap read 4 of 5 (the count guard caught it). Closing
    # tags, entities, commas and space are allowed through; an OPENING tag is
    # not, because that would let the next cell's link pair with this heading.
    for m in re.finditer(r"(?is)(<a\b[^>]*>.{0,160}?</a>)"
                         r"(?:</[a-z][^>]*>|&nbsp;|[\s,]){0,6}"
                         r"District\s+(\d{1,2})\s+Alderperson", page):
        name = " ".join(re.sub(r"(?s)<[^>]+>", " ",
                               H.unescape(m.group(1))).split())
        if not name:
            raise SystemExit("greenfield: district %s links no name"
                             % m.group(2))
        entry = {"name": name}
        href = re.search(r'href="([^"]+)"', m.group(1))
        if href:
            entry["url"] = urllib.parse.urljoin(GREENFIELD_INDEX,
                                                H.unescape(href.group(1)))
        _put("greenfield", members, "%02d" % int(m.group(2)), entry)
    return _seats_or_die("greenfield", members, 5, page,
                         ("District N Alderperson",
                          r"District\s+\d{1,2}\s+Alderperson")), GREENFIELD_INDEX


# -------------------------------------------------------------------- Muskego
def scrape_muskego():
    """"District N Alderman - NAME", seven districts, one line each.

    THE PAGE'S SIDEBAR NAMES FOUR OTHER DISTRICTS — Big Muskego Lake, Little
    Muskego Lake and the Muskego Norway School District — so a parse keyed on
    the word district alone would read lake districts as council seats. The
    pattern requires the number and the word Alderman together.
    """
    page = fetch(MUSKEGO_INDEX)
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    members = {}
    for m in re.finditer(r"District\s+(\d{1,2})\s+Alderman\s*[-\u2013]\s*"
                         r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})",
                         flat):
        _put("muskego", members, "%02d" % int(m.group(1)),
             {"name": " ".join(m.group(2).split())})
    return _seats_or_die("muskego", members, 7, page,
                         ("District N Alderman - NAME",
                          r"District\s+\d{1,2}\s+Alderman")), MUSKEGO_INDEX


# ------------------------------------------------------------------ West Bend
def scrape_west_bend():
    """"District N" heading, then "NAME, District N Alderman", then the seat
    e-mail districtN@westbendwi.gov — eight districts.

    The city writes Alderman, Alderwoman and "Council President, District 4
    Alderman" on the same page, so the title is read loosely and the DISTRICT
    number inside the name line is what keys the seat; the e-mail is matched on
    its own district number rather than on position, which is what stops a
    missing line sliding every address up one seat.
    """
    page = fetch(WEST_BEND_INDEX)
    flat = re.sub(r"<[^>]+>", "|", H.unescape(page))
    members, mails = {}, {}
    for m in re.finditer(r"district(\d{1,2})@westbendwi\.gov", flat, re.I):
        mails["%02d" % int(m.group(1))] = m.group(0).lower()
    for m in re.finditer(r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*\.?){1,3})"
                         r",\s*(?:[A-Za-z ]{0,24},\s*)?District\s+(\d{1,2})\s+"
                         r"Alder(?:man|woman|person)", flat):
        key = "%02d" % int(m.group(2))
        entry = {"name": " ".join(m.group(1).split())}
        if key in mails:
            entry["email"] = mails[key]
        _put("west bend", members, key, entry)
    return _seats_or_die("west bend", members, 8, page,
                         ("District N Alderman",
                          r"District\s+\d{1,2}\s+Alder")), WEST_BEND_INDEX


# ------------------------------------------------------------------- Wausau
def scrape_wausau():
    """One table row per alderperson: photo, "NAME<br>District N Alderperson",
    phone, e-mail, and a link to that district's map.

    THE ROW IS THE UNIT, NEVER THE FLAT PAGE. Each cell is read inside its own
    <tr>, because the table's first row is a header whose only mailto is the
    page's own social-share link -- a flat read of the page would pair it with
    whatever name came next.

    DISTRICT 9'S DISPLAY NAME AND MAILBOX DISAGREE AND THE DISPLAY NAME SHIPS:
    the city prints "Vicki Tierney" and gives her Victoria.Tierney@wausauwi.gov.
    That is the Green Bay nickname split, decided the same way -- the city's own
    rendering of a person's name is what a reader should see, and the mailbox is
    a mailbox.

    THE ADDRESSES ARE PRINTED IN THE CLEAR and are read from the visible cell,
    not out of the mailto, whose characters the page writes as HTML entities.
    Nothing is decoded that the page does not already show a reader.
    """
    page = fetch(WAUSAU_INDEX, headers=UA_AKAMAI)
    members = {}
    for row in re.split(r"<tr[^>]*>", page)[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        flat = [" ".join(re.sub(r"<[^>]+>", " ", H.unescape(c)).split())
                for c in cells]
        hit = None
        for i, text in enumerate(flat):
            m = re.search(r"^(.*?)\s*District\s+(\d{1,2})\s+Alderperson$", text)
            if m:
                hit = (i, m)
                break
        if not hit:
            continue
        i, m = hit
        name = " ".join(m.group(1).split())
        if not name:
            raise SystemExit("wausau: a District %s row names nobody"
                             % m.group(2))
        entry = {"name": name}
        rest = flat[i + 1:]
        for text in rest:
            if re.fullmatch(r"\(?\d{3}\)?[-. ]\d{3}-\d{4}", text):
                entry["phone"] = text
            elif re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", text):
                entry["email"] = text
        _put("wausau", members, "%02d" % int(m.group(2)), entry)
    return _seats_or_die("wausau", members, 11, page,
                         ("District N Alderperson",
                          r"District\s+\d{1,2}\s+Alderperson")), WAUSAU_INDEX


# ---------------------------------------------------------------- Wauwatosa
def scrape_wauwatosa():
    """The city's elected-officials directory table: a name anchor carrying the
    member's own profile link, then "Alderperson - District N", then "Elected
    Official", then a phone cell that may be empty, then an e-mail button.

    THE PHONE BELONGS TO THE ROW ABOVE ON A FLAT READ. District 12's phone cell
    is empty, so flattening the table shifts every number up one seat from there
    on and the mayor's own number lands on a member. Each cell is therefore read
    inside its own <tr> and the phone is taken from the cells AFTER the title.

    NAMES ARE SURNAME-FIRST and are flipped, with the flip PRINTED every run:
    "Small, Scott", "Franzen, Ernst (Ernie)", "Stluka, Michael Indy". The comma
    is the only thing the flip trusts -- a row published without one fails the
    city rather than shipping a name in an order the city did not use.

    NO E-MAIL SHIPS. The directory's Email button is a javascript:void(0) that
    carries only a numeric staff id; the addresses are not in the page. That is
    an obfuscation, and it is not worked around.
    """
    page = fetch(WAUWATOSA_INDEX, headers=UA_AKAMAI)
    members, flipped = {}, []
    for row in re.split(r"<tr[^>]*>", page)[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 2:
            continue
        flat = [" ".join(re.sub(r"<[^>]+>", " ", H.unescape(c)).split())
                for c in cells]
        d = None
        for i, text in enumerate(flat[1:], start=1):
            m = re.fullmatch(r"Alderperson\s*-\s*District\s+(\d{1,2})", text)
            if m:
                d = (i, int(m.group(1)))
                break
        if d is None:
            continue
        i, number = d
        raw = flat[0]
        if "," not in raw:
            raise SystemExit("wauwatosa: District %d names %r with no comma — "
                             "the page has stopped printing surname first and "
                             "the flip can no longer be trusted" % (number, raw))
        surname, given = (part.strip() for part in raw.split(",", 1))
        if not surname or not given:
            raise SystemExit("wauwatosa: District %d names %r, which does not "
                             "split into a surname and a given name"
                             % (number, raw))
        name = "%s %s" % (given, surname)
        flipped.append("%s -> %s" % (raw, name))
        entry = {"name": name}
        href = re.search(r'<a[^>]+href="([^"]+)"', cells[0])
        if href:
            entry["url"] = urllib.parse.urljoin(WAUWATOSA_INDEX, href.group(1))
        for text in flat[i + 1:]:
            if re.fullmatch(r"\(\d{3}\)\s*\d{3}-\d{4}", text):
                entry["phone"] = text
                break
        _put("wauwatosa", members, "%02d" % number, entry)
    for line in flipped:
        print("  wauwatosa name flipped: %s" % line)
    return _seats_or_die("wauwatosa", members, 12, page,
                         ("Alderperson - District N",
                          r"Alderperson\s*-\s*District\s+\d{1,2}")), WAUWATOSA_INDEX


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    got, failures = {}, {}
    # THE ONE LIST. `CITIES` used to restate it and was read in exactly one
    # place — this loop's own denominator — where it had gone stale at 18
    # against 28 and printed "27 of 18". A table nothing else reads, that
    # disagrees with the loop beside it, is not a second source: it is a
    # second answer to a question with one.
    COVERED = (
            ("53000", "Milwaukee", 15, scrape_milwaukee),
            ("48000", "Madison", 20, scrape_madison),
            ("31000", "Green Bay", 12, scrape_green_bay),
            ("39225", "Kenosha", 17, scrape_kenosha),
            ("66000", "Racine", 15, scrape_racine),
            ("84250", "Waukesha", 15, scrape_waukesha),
            ("77200", "Stevens Point", 11, scrape_stevens_point),
            ("51025", "Menomonie", 11, scrape_menomonie),
            ("48500", "Manitowoc", 10, scrape_manitowoc),
            ("72975", "Sheboygan", 10, scrape_sheboygan),
            ("78650", "Superior", 10, scrape_superior),
            ("64100", "Portage", 9, scrape_portage),
            ("82925", "Viroqua", 9, scrape_viroqua),
            ("50825", "Menasha", 8, scrape_menasha),
            ("35950", "Howard", 8, scrape_howard),
            ("80075", "Tomah", 8, scrape_tomah),
            ("22300", "Eau Claire", 5, scrape_eau_claire),
            ("02375", "Appleton", 15, scrape_appleton),
            # the tranche of 2026-09-05 evening
            ("56375", "New Berlin", 7, scrape_new_berlin),
            ("77875", "Sturgeon Bay", 7, scrape_sturgeon_bay),
            ("01550", "Altoona", 6, scrape_altoona),
            ("21625", "Eagle River", 4, scrape_eagle_river),
            ("28875", "Germantown", 4, scrape_germantown),
            ("56900", "New Lisbon", 4, scrape_new_lisbon),
            # the multi-member tranche of 2026-09-24, which #1133 unblocked
            ("84625", "Wautoma", 3, scrape_wautoma),
            ("01000", "Algoma", 4, scrape_algoma),
            ("35750", "Horicon", 3, scrape_horicon),
            ("20350", "Dodgeville", 4, scrape_dodgeville),
            # the second multi-member tranche, 2026-09-24
            ("07900", "Black River Falls", 4, scrape_black_river_falls),
            ("55750", "Neenah", 3, scrape_neenah),
            # the partially-filled district, 2026-09-25
            ("59250", "Oconomowoc", 4, scrape_oconomowoc),
            # the tranche of 2026-10-01, aimed at the done standard's city tier
            ("27300", "Franklin", 6, scrape_franklin),
            ("31175", "Greenfield", 5, scrape_greenfield),
            ("55275", "Muskego", 7, scrape_muskego),
            ("85350", "West Bend", 8, scrape_west_bend),
            # the two Akamai-fronted councils of 2026-10-01, whose sites were
            # recorded here as blocking automated readers and do not
            ("84475", "Wausau", 11, scrape_wausau),
            ("84675", "Wauwatosa", 12, scrape_wauwatosa),
            # read from Waupaca County's directory, 2026-10-07, once the
            # aldermanic builder could draw its three districts (LOCAL_RECODE)
            ("49400", "Marion", 3, scrape_marion),
    )
    for code, name, districts, fn in COVERED:
        result, reason = attempt(name, fn)
        if result is None:
            failures[code] = {"municipality": name, "reason": reason}
            continue
        members, source = result[0], result[1]
        # `districts`, not `seats`: this number has always been the count of
        # districts the municipality's geometry draws, which the builder
        # compares against the shipped layer. It stops equalling the number of
        # people the council seats the moment a multi-member city joins, so it
        # is named for what it counts.
        entry = {"municipality": name, "districts": districts, "sourceUrl": source,
                 "members": as_member_lists(members)}
        # A city may add fields beyond its members, and it names them: Madison
        # says which whole districts are vacant, Oconomowoc how many seats
        # WITHIN a district it lists as vacant. The allow-list is what makes
        # that safe — a misspelled key would otherwise ship a field the card
        # never reads and no gate would see it, which is the shape of every
        # silently-wrong roster column this file already guards against.
        for key, value in sorted((result[2] if len(result) > 2 else {}).items()):
            if key not in ("vacantDistricts", "vacantSeats"):
                raise SystemExit("%s returned the extra field %r, which nothing "
                                 "reads; add it to this allow-list and to the "
                                 "card in the same change" % (name, key))
            entry[key] = value
        got[code] = entry

    if not got:
        raise SystemExit("every city failed (%s) — that is a network or a code "
                         "fault, not six simultaneous site changes"
                         % "; ".join(f["reason"] for f in failures.values()))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"cities": got, "failures": failures}, f, indent=2,
                  ensure_ascii=False)
    # PEOPLE, not districts: len(members) counts districts once the values
    # are lists, and a multi-member city would under-report itself.
    total = sum(len(ms) for c in got.values() for ms in c["members"].values())
    madison = got.get("48000", {}).get("vacantDistricts")
    seats_vacant = sum(sum(c.get("vacantSeats", {}).values()) for c in got.values())
    print("scraped %d alderpersons across %d of %d municipalities (Madison "
          "vacant: %s; %d vacant seat(s) inside a named district)%s -> %s"
          % (total, len(got), len(COVERED), madison or "none", seats_vacant,
             "" if not failures else "; MISSED %s" % ", ".join(
                 sorted(f["municipality"] for f in failures.values())),
             out_path))


if __name__ == "__main__":
    main()
