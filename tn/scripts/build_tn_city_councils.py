#!/usr/bin/env python3
"""
Build tn/data/app/tn-city-councils.json: the mayor and council of each of
Tennessee's 28 cities and towns above 25,000 people, written down from each
city's own pages and proved against them on every build.

    python3 tn/scripts/build_tn_city_councils.py            # read every page, prove every name, write
    python3 tn/scripts/build_tn_city_councils.py --check    # offline
    python3 tn/scripts/build_tn_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, which
pages are read with a browser's client and why, and which cities' districts
are not drawn. The seats themselves are in
tn/data/source/tn-city-council-seats.json, kept by hand, and the drawn
districts of the eleven cities whose districts are drawn in
tn/data/app/tn-city-wards.json (tn/scripts/build_tn_city_wards.py), which
--check holds the seats to.

WHICH PLACES. The 28 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more), all 28 read on 2026-10-16:
twenty-five cities, two towns (Smyrna and Collierville) and the Metropolitan
Government of Nashville and Davidson County. Tennessee's other cities and
towns are not named, and gap tn-municipal-officeholders says so.

NASHVILLE'S ENTRY NAMES ITS MAYOR AND VICE MAYOR ONLY. Its 35 district
council members and 5 members elected countywide are already named on the
County Commission District card, because the Metropolitan Council is Davidson
County's legislative body (tn/scripts/build_tn_commissioner_roster.py), and
naming them twice would give a reader two copies that could disagree. The
Davidson County Election Commission's sample ballot for the election of 3
August 2023 lists the mayor, the vice mayor and the five countywide council
seats as contests on every ballot in the county and each district's council
seat as a contest of its own, which is what the entry's sentence says.

WHERE THE NAMES COME FROM. Each city's own pages, because no state office
publishes Tennessee's city officials. The University of Tennessee's Municipal
Technical Advisory Service publishes a page for every city naming its
officials, and it is not used: it gives no ward, seat or date, says the cities
supply its information and it is not verified, and on 2026-10-16 it named
someone other than the city's own page in Clarksville's Ward 2, Cleveland's
District 1, three of Kingsport's six aldermen's seats and Bristol's East
District, listed a Johnson City seat as vacant that the city's own page names,
and misspelt Kingsport's mayor. A few names come from a city page other than
its council's own list:
  * Nashville's mayor and vice mayor from each one's own page on the Metro
    government's site, and Clarksville's mayor from the Mayor's Office page,
    because the council pages list only the members.
  * Lebanon's council from the city's staff directory listing for the City
    Council, and its mayor from the same directory's listing for the Mayor's
    Office, which is the only page of the city's that names the mayor beside
    that title other than scanned meeting agendas. The card says so.
  * Memphis's council members each from their own page on the city's site,
    and its mayor from the mayor's page; Knoxville's mayor from the page of
    the mayor's office.
  * Johnson City's from the city's own page about the board's vote of 20
    November 2025, which names all five commissioners and the mayor, because
    the board's list of its members is on the city's meeting-records site,
    whose robots.txt disallows every path to this project's client. The card
    says so.

HOW EACH CITY ELECTS, which is what decides whether its districts are drawn.
No state office records it, so it was read from each city's charter or code,
its own pages, or a county election commission's results, on 2026-10-16:
  * ELECTED BY DISTRICT OR WARD, by that district's own voters: Memphis (seven
    districts and two super districts of three positions each, every one a
    contest on its own district's precincts alone in the Shelby County
    Election Commission's results for 5 October 2023), Knoxville (six
    districts and three members at large: in Knox County's official results
    for 4 November 2025 the contests for Districts 1 to 4 and 6 were each on
    6 to 12 of the city's 52 precincts, 2,959 to 6,202 ballots each, while the
    sales tax referendum on the same ballot was on all 52 with 24,911; until
    then each district's final election was citywide, and District 5's
    member was elected that way in November 2023, the contest on all 52
    precincts with 15,700 ballots like the three seats at large, which the
    card's sentence says), Chattanooga (nine
    districts, city code section 8.2), Clarksville (twelve wards, its city
    code), Jackson (nine districts whose elections are "held only in their
    respective districts", its code), Hendersonville (two aldermen from each
    of six wards, the city's charter page; in the Sumner County Election
    Commission's certified results for 5 November 2024 each ward's contest
    drew 3,208 to 5,320 votes), Franklin (four wards and four aldermen at
    large, its code), Cleveland (five districts and two members at large, its
    charter, not checked against results), Gallatin (five districts and two
    members at large, its code; in 2024 the at-large contest drew 16,010 votes
    and Districts 1 and 2 drew 2,371 and 3,743), Columbia (five wards, charter
    section 2.03), Mount Juliet (four districts; in the Wilson County Election
    Commission's certified results for 5 November 2024 the mayor's contest was
    on 12 precincts and Districts 1 and 3 on 5 each), Lebanon (six wards; in
    the same commission's results the mayor's contest was on 13 precincts and
    Wards 1, 2 and 5 on 5, 5 and 4) and Morristown (four wards and two members
    at large, its code, section 2).
  * TIED TO A DISTRICT AND ELECTED BY THE WHOLE CITY: Spring Hill (two
    aldermen for each of four wards, all voted citywide; in the
    city's certified results for April 2025 the mayor's contest drew 3,483
    votes and the four wards' contests 2,888, 3,101, 2,799 and 3,054) and
    Bristol (three councilmanic districts "elected ... by the eligible voters
    of the city at large", city code sections 2-1 and 2-6). These are recorded
    as elected by the whole city, so none of their districts is drawn.
  * ELECTED BY THE WHOLE CITY OR TOWN: Murfreesboro (Rutherford County's
    results for 1 August 2024, "Vote for 3"; its charter allows districts and
    none are in use), Smyrna (Rutherford County, 5 November 2024, "Vote for
    3"), La Vergne (Rutherford County, November 2024, "Vote for 2"), Kingsport
    (city code, Article III), Bartlett (charter, Article III section 1),
    Collierville (in Shelby County's results for 5 November 2024 the mayor's
    contest and Positions 3 and 5 were on the same 12 precincts), Germantown
    (city code section 4.01; each position on 8 precincts in Shelby County's
    November 2024 results), Johnson City (charter section 10), Brentwood (the
    board's own page: "an elected representative of the entire city"),
    Cookeville (the council's own page: "there are no district divisions
    within the City"), Maryville (its charter) and Oak Ridge (its charter as
    updated in December 2024).
The seat each mayor holds is labelled "Mayor" whether the voters elect the
mayor or the council chooses one of its members, as it does in Johnson City,
Brentwood, Cookeville, Maryville, Oak Ridge and Bristol, and each city's
sentence says which. A vice mayor is labelled so only where the voters elect
one (Nashville and Columbia); where the council chooses a vice mayor or mayor
pro tem from among its members, that member keeps the seat the voters gave.

SIX CITIES' PAGES ARE READ WITH A BROWSER'S CLIENT, and this is the
measurement that allows it (CLAUDE.md, "Browser user-agent strings"). On
2026-10-16 scripts/probe_user_agents.py asked each city's page below four
ways: this project's token got HTTP 403 on both the requests and the stdlib
stacks, and Chrome/126 with its client hints got 403 on requests and HTTP 200
on stdlib, every member named (Murfreesboro's council page 126,283 bytes,
Franklin's board page 121,372, Bristol's council page 112,358, Knoxville's
council page 109,625, Collierville's board page 106,217 and Germantown's
100,428). The 403s are the cities' own edges, not this sandbox's proxy:
Murfreesboro, Bristol and Knoxville answer with Cloudflare's "Sorry, you have
been blocked" page (4,547 bytes at the first two and 5,486 at Knoxville, a
block page and no challenge), and Franklin, Collierville and Germantown with
their Akamai edges' "Access Denied" (Server AkamaiGHost, 460, 470 and 473
bytes). Franklin's edge also cuts the connection when the token asks for
robots.txt, and Knoxville's, Collierville's and Germantown's answer that
request with 403. With Chrome/126 and its client hints on the stdlib client
(scraper_common.UA_HINTS_CHROME_126) each host serves its robots.txt
(Murfreesboro 816 bytes, Bristol 816, Knoxville 816, Franklin 9,751, and
Collierville and Germantown 6,641 each, the same content-management vendor's
default file, identical by MD5 on 2026-10-16, that Kendall County, McHenry
County and Joliet serve in Illinois), no rule in it matching the page, and it is read with that same
client before the page is. Knoxville's mayor's page is on the same host and
is read the same way. Franklin's page carries a reCAPTCHA key for its site
forms and no challenge. Every other page here is read with this project's
own token, and each served it.

PRIVACY. Only names are carried. Franklin's board page also prints its
members' e-mail addresses, one of them on a personal domain, and Knoxville's
council page its members' e-mail addresses and telephone numbers, and none is
copied.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
tn-municipal-officeholders): no state office publishes who holds Tennessee's
city offices or where their wards run; the only statewide list, the
Municipal Technical Advisory Service's, gives no seat, ward or date, says it
is unverified, and on the day it was read disagreed with five cities' own
pages; which seats a ward elects is set by each city's private-act charter
or ordinances, and the results that show it sit with 95 county election
commissions in formats that include scanned pages; one city's list of its
board is on a site whose robots.txt shuts this project out; one city names
its mayor beside that title only in scanned agendas and a staff directory;
six cities refuse this project's client; and the only copy of Knoxville's
council districts published as data reserves all rights, so they cannot be
drawn without its publisher's written permission.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import city_councils as cc  # noqa: E402
from scraper_common import UA_HINTS_CHROME_126  # noqa: E402

MURFREESBORO_COUNCIL = "https://www.murfreesborotn.gov/424/City-Council"
FRANKLIN_BOARD = "https://www.franklintn.gov/government/board-of-mayor-aldermen"
BRISTOL_COUNCIL = "https://www.bristoltn.gov/337/City-Council"
KNOXVILLE_COUNCIL = "https://www.knoxvilletn.gov/1340/City-Council-Members"
KNOXVILLE_MAYOR = "https://www.knoxvilletn.gov/248/Mayor-Indya-Kincannons-Office"
COLLIERVILLE_BOARD = "https://www.colliervilletn.gov/government/mayor-and-board-of-aldermen"
GERMANTOWN_BOARD = "https://www.germantown-tn.gov/government/board-of-mayor-and-aldermen"

# Seats per place, the mayor included, as each place's own page lists them on
# 2026-10-16. A redistricting or a charter change moves these legitimately:
# read the place's page, then change the number deliberately.
SEATS = {
    "4752006": 2,   # Nashville: mayor and vice mayor (the council is on the County Commission District card)
    "4748000": 14,  # Memphis: mayor, 7 districts, 2 super districts of 3 positions
    "4740000": 10,  # Knoxville: mayor, 6 districts, 3 at large
    "4714000": 10,  # Chattanooga: mayor, 9 districts
    "4715160": 13,  # Clarksville: mayor, 12 wards
    "4751560": 7,   # Murfreesboro: mayor, 6 at large
    "4727740": 9,   # Franklin: mayor, 4 wards, 4 at large
    "4738320": 5,   # Johnson City: 5 commissioners, one of them chosen mayor
    "4737640": 10,  # Jackson: mayor, 9 districts
    "4733280": 13,  # Hendersonville: mayor, 2 aldermen from each of 6 wards
    "4703440": 7,   # Bartlett: mayor, 6 positions at large
    "4739560": 7,   # Kingsport: mayor, 6 at large
    "4769420": 7,   # Smyrna: mayor, 6 at large
    "4716420": 6,   # Collierville: mayor, 5 positions at large
    "4770580": 9,   # Spring Hill: mayor, 2 aldermen for each of 4 wards, all citywide
    "4715400": 8,   # Cleveland: mayor, 5 districts, 2 at large
    "4708280": 7,   # Brentwood: 7 commissioners, one of them appointed mayor
    "4728540": 8,   # Gallatin: mayor, 5 districts, 2 at large
    "4716540": 7,   # Columbia: mayor, vice mayor, 5 wards
    "4728960": 6,   # Germantown: mayor, 5 positions at large
    "4750780": 5,   # Mount Juliet: mayor, 4 districts
    "4741200": 5,   # La Vergne: mayor, 4 at large
    "4741520": 7,   # Lebanon: mayor, 6 wards
    "4716920": 5,   # Cookeville: 5 members, one of them chosen mayor
    "4746380": 5,   # Maryville: 5 members, one of them chosen mayor
    "4755120": 7,   # Oak Ridge: 7 members, one of them chosen mayor
    "4750280": 7,   # Morristown: mayor, 4 wards, 2 at large
    "4708540": 5,   # Bristol: 5 members, three from districts, all citywide; one chosen mayor
}

SPEC = cc.Spec(
    tag="tn",
    label="build_tn_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/tn/)",
    seats_file="tn-city-council-seats.json",
    out_file="tn-city-councils.json",
    seats=SEATS,
    browser={
        MURFREESBORO_COUNCIL: UA_HINTS_CHROME_126,
        FRANKLIN_BOARD: UA_HINTS_CHROME_126,
        BRISTOL_COUNCIL: UA_HINTS_CHROME_126,
        KNOXVILLE_COUNCIL: UA_HINTS_CHROME_126,
        KNOXVILLE_MAYOR: UA_HINTS_CHROME_126,
        COLLIERVILLE_BOARD: UA_HINTS_CHROME_126,
        GERMANTOWN_BOARD: UA_HINTS_CHROME_126,
    },
    wards_file="tn-city-wards.json",
    undrawn={
        "4740000": "the only copy of the city's district lines published as data, KGIS's, "
                   "reserves all rights and allows no copy without KGIS's written permission",
        "4741520": "the city's wards are published only as the county election commission's "
                   "PDF files",
    },
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
