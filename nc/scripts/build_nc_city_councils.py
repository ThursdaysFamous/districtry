#!/usr/bin/env python3
"""
Build nc/data/app/nc-city-councils.json: the mayor and council of each of
North Carolina's 42 cities and towns above 25,000 people, written down from
each city's own pages and proved against them on every build.

    python3 nc/scripts/build_nc_city_councils.py            # read every page, prove every name, write
    python3 nc/scripts/build_nc_city_councils.py --check    # offline
    python3 nc/scripts/build_nc_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, which
pages are read with a browser's client and why, and which pages are not web
pages. The seats themselves are in nc/data/source/nc-city-council-seats.json,
kept by hand, and the drawn districts of the seventeen cities whose districts
elect seats in nc/data/app/nc-city-wards.json
(nc/scripts/build_nc_city_wards.py), which --check holds the seats to.

WHICH PLACES. The 42 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more), all 42 read on 2026-10-16: 26
cities and 16 towns. North Carolina's other cities and towns are not named,
and gap nc-municipal-officeholders says so.

WHERE THE NAMES COME FROM. Each city's own pages, because no state office
publishes who holds North Carolina's city offices: the North Carolina League
of Municipalities' public directory lists the cities and none of their
officials, and the State Board of Elections' results name candidates and
their votes but not who was elected, who was appointed to an empty seat, or
which seats are empty. A few names come from somewhere other than the
council's own list:
  * Raleigh's and Matthews's from the State Board of Elections' precinct
    results for the elections of 5 November 2024 and 4 November 2025
    (nc/scripts/ncsbe_results.py turns each zip into its winners), because
    both places' websites answer this project with Cloudflare's managed
    challenge ("Just a moment...", an access control, so no other client is
    tried there). The seat's `as` is the contest and the name together, so
    the build proves both. The card says the names are the candidates with
    the most votes in that election, and links each place's own council page
    (`page`), which is not read.
  * Goldsboro's and Asheboro's from the list each council page fills itself
    in from (the read-the-page-first rule in CLAUDE.md): Goldsboro's page
    loads /api/COG/CouncilMembers and Asheboro's loads the site's
    catalogue.json, whose council entries are category 30. The card says so
    and links the council page itself.
  * Wilson's mayor's full name from the city's own map server (the MAYOR
    field of its council district layer), because the council page names the
    mayor only as "Mayor Stevens". The card says so.
  * Charlotte's, Winston-Salem's and Concord's mayors from each mayor's own
    page, and Jacksonville's from the city's directory listing for the Mayor
    and City Council, because the council pages list only the members.
    Charlotte's mayor's page says the council appointed the mayor in June
    2026 to serve out a term that ends in December 2027, which the card's
    sentence says.
  * Three empty seats, each from its city's own words: Mooresville's mayor
    (the town's news item of September 2026 says the mayor would retire on
    30 September 2026), one of Salisbury's council seats (the city's
    newsroom: a member "announced his resignation, effective Oct. 15, 2026")
    and one of Monroe's (the minutes of the council's meeting of 11 August
    2026, in its agenda packet for 8 September 2026, say a member resigned on
    31 July 2026). None of the members who left is named.
  * One of Cornelius's five commissioners' seats is named nobody, because
    the town's own pages disagree: its list of the board names Scott
    Higgins, its page about the Neighborhood Advisory Committee names Todd
    Sansbury as a commissioner, and in the State Board's results for 4
    November 2025 Sansbury was among the five with the most votes while
    Higgins was not on the ballot. Either page could be the stale one (an
    appointment to an empty seat would make the list right), so the card says
    what each says and names no one.

HOW EACH CITY ELECTS, which is what decides whether its districts are drawn.
No state office records it, so it was read from the State Board of
Elections' precinct results for 2022 to 2025 (a contest that appears on only
some of a place's precincts is elected by a district's own voters, and one on
all of them by the whole place) and from each city's own pages, on
2026-10-16:
  * ELECTED BY DISTRICT OR WARD, by that district's own voters (17):
    Charlotte (each district's contest on 15 to 38 of the city's 169
    precincts in 2025), Raleigh (18 to 30 of 111 in 2024), Greensboro (20 to
    23 of 108 in 2025), Winston-Salem (12 to 22 of 86 in 2024), Fayetteville
    (4 to 19 of 59 in 2025), Cary (Districts A and C on 14 and 13 of 46 in
    2025), High Point (7 to 9 of 42 in 2023), Greenville (6 to 12 of 29 in
    2025), Gastonia (Wards 1, 2 and 5 on 7, 8 and 5 of 22 in 2025, the first
    election under S.L. 2023-118), Jacksonville (2 to 5 of 9 in 2025),
    Rocky Mount (Ward 3 on 7 precincts in 2025, where the mayor's contest of
    2023 was on 17), Mooresville (3 to 5 of 9 or 10 in 2023 and 2025),
    Wilson (3 to 7 of 18 in 2023 and 2025), Goldsboro (4 to 7 of 20 in
    2023), New Bern (Ward 4 on 3 of 11 in 2025), Sanford (3 to 5 of 8 in
    2023 and 2025) and Statesville (3 to 5 of 12 in 2025).
  * TIED TO A WARD OR DISTRICT AND ELECTED BY THE WHOLE PLACE: Durham (Wards
    I to III each on all 61 precincts in 2025), Concord (each district on all
    22 in 2023 and 2025), Hickory (each ward on all 22 in 2023 and 2025) and
    Morrisville (each district on all 6 or 7 in 2023 and 2025). These are
    recorded as elected by the whole place, so none of their districts is
    drawn. Gastonia's Wards 3, 4 and 6 are the same until 2027 (each on all 27
    precincts in 2023, and Ward 4's unexpired term on all 22 in 2025); its
    wards are drawn because its other three elect by ward.
  * ELECTED BY THE WHOLE CITY OR TOWN (21): Wilmington, Asheville (all 40
    precincts in 2022 and 2024), Chapel Hill, Huntersville, Apex, Burlington,
    Kannapolis, Wake Forest, Holly Springs, Indian Trail, Salisbury, Monroe
    (all 15 in 2023), Fuquay-Varina, Cornelius, Garner, Matthews,
    Thomasville, Asheboro, Mint Hill, Kernersville and Clayton, each a single
    contest on every one of the place's precincts in 2023 and 2025.
The seat each mayor holds is labelled "Mayor". Where the council chooses a
mayor pro tem or, in Asheville, a vice mayor from among its members, that
member keeps the seat the voters gave.

SEVEN CITIES' PAGES ARE READ WITH A BROWSER'S CLIENT, and this is the
measurement that allows it (CLAUDE.md, "Browser user-agent strings"). On
2026-10-16 scripts/probe_user_agents.py asked each page below four ways:
this project's token got HTTP 403 on both the requests and the stdlib
stacks, and Chrome/126 with its client hints got 403 on requests and HTTP 200
on stdlib, every member named (Greensboro's page 165,162 bytes, Garner's
119,798, Greenville's 116,871, Durham's 113,900, Wilson's 102,930, Rocky
Mount's 98,454 and Cary's 97,029). The 403s are the cities' own edges, not
this sandbox's proxy: Durham, Greenville and Rocky Mount answer with
Cloudflare's "Attention Required!" block page (about 5,485 bytes, a block
and no challenge), Greensboro, Cary and Garner with their Akamai edges'
"Access Denied" (Server AkamaiGHost, 446, 444 and 470 bytes), and Wilson with
a 403 of its own. All seven answer the token's request for robots.txt with
403 too; with Chrome/126 and its client hints on the stdlib client
(scraper_common.UA_HINTS_CHROME_126) each serves its robots.txt, no rule in it
matching the page, and it is read with that same client before the page is.
Four of the pages (Greensboro's, Cary's, Garner's and Wilson's) carry a
reCAPTCHA key in their content-management system's settings for the site's
forms and no challenge. Every other page here is read with this project's
own token, and each served it.

PRIVACY. Only names are carried. Several of these pages also print members'
e-mail addresses, telephone numbers or street addresses (Rocky Mount's,
Cary's, Garner's, Greenville's, Wake Forest's, Thomasville's, Morrisville's
and others), Greensboro's members' biographies, Asheboro's list each
member's street address, and Monroe's packet and Wake Forest's pages name
residents and applicants, and none of it is copied. Goldsboro's page also
loads a second list that carries each member's e-mail address and telephone
number, which is not read.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
nc-municipal-officeholders): no state office publishes who holds North
Carolina's city offices or where their districts run; the State Board of
Elections' results carry no winner and no Census place code, their contest
names do not say who votes in them, and a council member appointed to an
empty seat or a seat left empty appears in no state file; which seats a ward
elects is set by each city's charter, a local act of the General Assembly;
seven city websites refuse this project's client outright and two more
answer it with a managed challenge; two cities publish their councils only
as data the page loads after it opens; one city names its mayor only by
surname; and one town's own pages disagree about who holds a seat.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import city_councils as cc  # noqa: E402
import ncsbe_results  # noqa: E402
from scraper_common import UA_HINTS_CHROME_126  # noqa: E402

DURHAM_COUNCIL = "https://www.durhamnc.gov/1396/City-Council-Members"
GREENSBORO_COUNCIL = ("https://www.greensboro-nc.gov/government/city-council/"
                      "connect-with-city-council")
CARY_COUNCIL = "https://www.carync.gov/mayor-council/town-council"
GREENVILLE_COUNCIL = "https://www.greenvillenc.gov/183/City-Council"
ROCKY_MOUNT_COUNCIL = "https://www.rockymountnc.gov/176"
GARNER_COUNCIL = "https://www.garnernc.gov/government/town-council/town-council-members"
WILSON_COUNCIL = ("https://www.wilsonnc.org/residents/all-departments/administration/"
                  "mayor-city-council")

# Seats per place, the mayor included, as each place's own page (or the State
# Board's results) gives them on 2026-10-16. A redistricting or a charter
# change moves these legitimately: read the place's page, then change the
# number deliberately.
SEATS = {
    "3712000": 12,  # Charlotte: mayor, 4 at large, 7 districts
    "3755000": 8,   # Raleigh: mayor, 2 at large, 5 districts (A to E)
    "3728000": 9,   # Greensboro: mayor, 3 at large, 5 districts
    "3719000": 7,   # Durham: mayor, 3 at large, 3 ward seats elected citywide
    "3775000": 9,   # Winston-Salem: mayor, 8 named wards
    "3722920": 10,  # Fayetteville: mayor, 9 districts
    "3710740": 7,   # Cary: mayor, 2 at large, 4 districts (A to D)
    "3774440": 7,   # Wilmington: mayor, 6 at large
    "3731400": 9,   # High Point: mayor, 2 at large, 6 wards
    "3714100": 8,   # Concord: mayor, 7 district seats elected citywide
    "3702140": 7,   # Asheville: mayor, 6 at large
    "3728080": 7,   # Greenville: mayor, 1 at large, 5 districts
    "3725580": 7,   # Gastonia: mayor, 6 wards (3 by ward, 3 citywide until 2027)
    "3734200": 7,   # Jacksonville: mayor, 4 wards, 2 at large
    "3711800": 9,   # Chapel Hill: mayor, 8 at large
    "3733120": 7,   # Huntersville: mayor, 6 commissioners at large
    "3701520": 6,   # Apex: mayor, 5 at large
    "3709060": 5,   # Burlington: mayor, 4 at large
    "3757500": 8,   # Rocky Mount: mayor, 7 wards
    "3735200": 7,   # Kannapolis: mayor, 6 at large
    "3744220": 7,   # Mooresville: mayor (empty), 4 wards, 2 at large
    "3774540": 8,   # Wilson: mayor, 7 districts
    "3770540": 6,   # Wake Forest: mayor, 5 commissioners at large
    "3731060": 7,   # Hickory: mayor, 6 ward seats elected citywide
    "3732260": 6,   # Holly Springs: mayor, 5 at large
    "3733560": 6,   # Indian Trail: mayor, 5 at large
    "3758860": 5,   # Salisbury: mayor, 4 at large (one empty)
    "3743920": 7,   # Monroe: mayor, 6 at large (one empty)
    "3725300": 6,   # Fuquay-Varina: mayor, 5 commissioners at large
    "3726880": 7,   # Goldsboro: mayor, 6 districts
    "3714700": 6,   # Cornelius: mayor, 5 commissioners at large (one unnamed)
    "3746340": 7,   # New Bern: mayor, 6 wards
    "3725480": 6,   # Garner: mayor, 5 at large
    "3759280": 8,   # Sanford: mayor, 5 wards, 2 at large
    "3744520": 7,   # Morrisville: mayor, 2 at large, 4 district seats elected townwide
    "3741960": 7,   # Matthews: mayor, 6 commissioners at large
    "3764740": 9,   # Statesville: mayor, 6 wards, 2 at large
    "3767420": 8,   # Thomasville: mayor, 7 at large
    "3702080": 8,   # Asheboro: mayor, 7 at large
    "3743480": 5,   # Mint Hill: mayor, 4 commissioners at large
    "3735600": 6,   # Kernersville: mayor, 5 aldermen at large
    "3712860": 6,   # Clayton: mayor, 5 at large
}

SPEC = cc.Spec(
    tag="nc",
    label="build_nc_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/nc/)",
    seats_file="nc-city-council-seats.json",
    out_file="nc-city-councils.json",
    seats=SEATS,
    browser={
        DURHAM_COUNCIL: UA_HINTS_CHROME_126,
        GREENSBORO_COUNCIL: UA_HINTS_CHROME_126,
        CARY_COUNCIL: UA_HINTS_CHROME_126,
        GREENVILLE_COUNCIL: UA_HINTS_CHROME_126,
        ROCKY_MOUNT_COUNCIL: UA_HINTS_CHROME_126,
        GARNER_COUNCIL: UA_HINTS_CHROME_126,
        WILSON_COUNCIL: UA_HINTS_CHROME_126,
    },
    readers={url: ncsbe_results.text for url in ncsbe_results.RESULTS},
    wards_file="nc-city-wards.json",
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
