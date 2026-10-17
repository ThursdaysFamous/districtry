#!/usr/bin/env python3
"""
Build ar/data/app/ar-city-councils.json: the mayor and council of each of
Arkansas's 19 cities above 25,000 people, written down from each city's own
pages and proved against them on every build.

    python3 ar/scripts/build_ar_city_councils.py            # read every page, prove every name, write
    python3 ar/scripts/build_ar_city_councils.py --check    # offline
    python3 ar/scripts/build_ar_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which cities, how many seats each has, and which
page is read with a browser's client and why. The seats themselves are in
ar/data/source/ar-city-council-seats.json, kept by hand, and the drawn wards
of the twelve cities that elect by ward in ar/data/app/ar-city-wards.json
(ar/scripts/build_ar_city_wards.py), which --check holds the seats to.

WHICH CITIES. The 19 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more), all 19 read on 2026-10-16. Arkansas's
other 482 cities and towns are not named, and gap ar-municipal-officeholders
says so.

WHERE THE NAMES COME FROM. Each city's own page, because no state office
publishes Arkansas's city officials. The Arkansas Municipal League's 2026
directory (August 2026) names every mayor and council member in the state, and
it is not used: it gives no ward or position, and on the day these pages were
read it disagreed with the city's own page in five of the twelve cities where
both could be compared (Fayetteville, Jonesboro, Pine Bluff, Paragould and
Russellville), naming former members, leaving out current ones, or both. Two
cities fill their council page in from a block of data the page carries
(Springdale and Sherwood), which the proof reads. Conway's names come from the
head of a council meeting agenda, because no page listing its council was
found on its website.

HOW EACH CITY ELECTS, which is what decides whether its wards are drawn. A
seat tied to a ward is not necessarily elected by it: seven of the 19 cities
give every council seat a ward and elect it citywide. Nothing the state
publishes records which rule a city follows, so it was measured from the
ballot, comparing the precincts a seat's contest was on with the mayor's in
the same election, in the Secretary of State's 2024 general results workbook
and the state's results service for 2018 to 2024 (read 2026-10-16):
  * ELECTED BY WARD, a seat's contest on that ward's precincts alone: Little
    Rock (Wards 1, 2, 5, 6 and 7 read; Positions 8 to 10 citywide), Fayetteville
    (five of eight seats read), Fort Smith (Ward 3 read; Positions 5 to 7
    citywide), North Little Rock, Conway's Position 1 seats (all four read; its
    Position 2 seats citywide), Pine Bluff, Hot Springs (four of six districts
    read), Benton (six of ten seats read, against its own page, which says its
    members are typically elected at large), Sherwood, Paragould, Texarkana
    (five of six read) and Russellville (Wards 1 to 3 read). The seats not read
    are taken to follow the rule their city's other seats were measured to
    follow, which is an inference and is recorded as one here.
  * ELECTED CITYWIDE, every seat's contest on as many precincts as the mayor's:
    Springdale, Jonesboro, Rogers, Bentonville, Bella Vista, Jacksonville and
    Cabot. Their wards are not drawn, because a reader in one votes for every
    seat, and scripts/build_eam_status.py records each with its reason.

FORT SMITH IS READ WITH A BROWSER'S CLIENT, and this is the measurement that
allows it (CLAUDE.md, "Browser user-agent strings"). On 2026-10-16 the city's
Akamai edge answered this project's own token with HTTP 403 "Access Denied"
(Server AkamaiGHost, 425 bytes) for robots.txt, and the research pass the same
day had the same answer for the city's pages. Chrome/126 with its client hints
on the stdlib client (scraper_common.UA_HINTS_CHROME_126) was served
robots.txt (HTTP 200, 6,641 bytes: rules for three named crawlers and the
site platform's own paths, none matching the board page) and the board page
(HTTP 200, 122,554 bytes). robots.txt is read with that same client before the
page is. Every other page here is read with this project's own token, and each
served it.

CABOT'S SITE DROPS SOME CONNECTIONS. On 2026-10-16 www.cabotar.gov reset the
connection on one read of its mayor's page and, later the same day, on three
reads in a row of its robots.txt, and served both normally in between. When a
page cannot be read the build keeps what it last said, with that date, so a
NOT READ line for Cabot is worth a second run before it is worth a look.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ar-municipal-officeholders): no state office publishes who holds Arkansas's
city offices, and the Municipal League's directory, the only statewide list,
gives no ward or position and disagreed with five of twelve cities; which
seats a city elects by ward and which citywide is set by its own ordinances
and is published nowhere a reader can find it, and one city's own page states
the opposite of what its ballot shows; one of the 19 cities publishes no page
listing its council; and one refuses this project's client.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import city_councils as cc  # noqa: E402
from scraper_common import UA_HINTS_CHROME_126  # noqa: E402

FORT_SMITH_BOARD = "https://www.fortsmithar.gov/government/leadership/board-of-directors"

# Seats per city, the mayor included, as each city's own page lists them on
# 2026-10-16. A redistricting or a charter change moves these legitimately:
# read the city's page, then change the number deliberately.
SEATS = {
    "0541000": 11,  # Little Rock: mayor, 7 ward directors, 3 at large
    "0523290": 9,   # Fayetteville
    "0524550": 8,   # Fort Smith: mayor, 4 ward directors, 3 at large
    "0566080": 9,   # Springdale
    "0535710": 13,  # Jonesboro
    "0560410": 9,   # Rogers
    "0550450": 9,   # North Little Rock
    "0515190": 9,   # Conway
    "0505320": 9,   # Bentonville
    "0555310": 9,   # Pine Bluff
    "0533400": 7,   # Hot Springs: mayor, 6 district directors
    "0505290": 11,  # Benton
    "0563800": 9,   # Sherwood
    "0504840": 7,   # Bella Vista
    "0553390": 9,   # Paragould
    "0534750": 11,  # Jacksonville
    "0568810": 7,   # Texarkana: mayor, 6 ward directors
    "0561670": 9,   # Russellville
    "0510300": 9,   # Cabot
}

SPEC = cc.Spec(
    tag="ar",
    label="build_ar_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/ar/)",
    seats_file="ar-city-council-seats.json",
    out_file="ar-city-councils.json",
    seats=SEATS,
    browser={FORT_SMITH_BOARD: UA_HINTS_CHROME_126},
    wards_file="ar-city-wards.json",
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
