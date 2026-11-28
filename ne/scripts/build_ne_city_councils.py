#!/usr/bin/env python3
"""
Build ne/data/app/ne-city-councils.json: the mayor and council of each of
Nebraska's 7 cities of 25,000 people or more, written down from each city's
own pages and proved against them on every build.

    python3 ne/scripts/build_ne_city_councils.py            # read every page, prove every name, write
    python3 ne/scripts/build_ne_city_councils.py --check    # offline
    python3 ne/scripts/build_ne_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, which page
was read once by hand, and why no city's wards are drawn. The seats are in
ne/data/source/ne-city-council-seats.json, kept by hand.

WHICH PLACES. The 7 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more): Omaha, Lincoln, Bellevue, Grand
Island, Kearney, Fremont and Hastings, all read on 2026-11-27. Nebraska's
other cities and villages name nobody, and gap ne-municipal-officeholders
says so.

OMAHA WAS READ ONCE BY HAND in Adam's Chrome on 2026-11-27 (Adam,
2026-11-25): www.cityofomaha.org and citycouncil.cityofomaha.org answer this
project's reader, and its request for robots.txt, with HTTP 403. What was
read is kept, dated, in ne/data/source/councils/omaha-2026-11-27.txt, and the
build proves the names against it (`excerpts` below); it is not re-read
automatically, and ne/WATCH.md carries the re-read.

HOW EACH CITY ELECTS, read on 2026-11-27:
  * Omaha (a city of the metropolitan class): the council's own page, "seven
    members, elected by district".
  * Lincoln (the primary class): the council's questions page, "four district
    seats ... and three at-large seats"; "At-large (city-wide) City Council
    members are elected" in a city-wide election, and "District City Council
    members are elected by their district's voters".
  * Bellevue, Grand Island and Fremont are cities of the first class whose
    pages give every member a ward, and Nebraska law reads "a mayor shall be
    elected at large and council members shall be elected by ward or at large
    and by ward" (Neb. Rev. Stat. 32-534), with a city that elects some
    members at large doing so by a vote under section 32-554 and its members
    "residents of the ward from which elected if elected by ward" (16-302.01).
    None of the three pages names an at-large member.
  * Hastings (first class): the council's own page, "elected to four-year
    terms by the voters of their wards".
  * Kearney (first class, city manager plan, to which 32-534 does not apply):
    the city's form of government page, "Its five members are elected at
    large" and "From within the Council, one member is elected as President
    of the Council and is recognized as Mayor". Its members page says Pete
    Kotsiopulos "is serving as Acting City Council Member in place of Alex
    Straatmann", who "is mobilized for the US Military"; the seat is written
    "At large (acting)" and the city's `note` says so. That page prints each
    member's home address and telephone, and neither is carried.

CONTACTS. Lincoln's members page prints each member's own e-mail address at
lincoln.ne.gov and Fremont's council page each member's and the mayor's own
number; the cards carry them. No other city prints a contact beside one
member alone.

WARDS. Six of the seven cities elect members by ward or district, and all
six are drawn by the City Council District layer since 2026-11-28
(ne/scripts/build_ne_city_wards.py, from each city's own map or its
county's), whose --check holds every drawn ward to a seat here. Kearney
elects everyone at large.

RE-READ. Omaha and Lincoln elect in the spring of odd years and the first
class cities in November of even years, their members taking office at the
council's first meeting in December (16-302.01); ne/WATCH.md carries the
re-read in December 2026 and after each election.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import city_councils as cc  # noqa: E402

# Seats per place, the mayor included, as each place's own page gives them on
# 2026-11-27. A redistricting or a charter change moves these legitimately:
# read the place's page, then change the number deliberately.
SEATS = {
    "3137000": 8,    # Omaha: mayor and 7 districts
    "3128000": 8,    # Lincoln: mayor, 4 districts, 3 at large
    "3103950": 7,    # Bellevue: mayor and 6 wards
    "3119595": 11,   # Grand Island: mayor and 2 members from each of 5 wards
    "3125055": 5,    # Kearney: 5 at large, one of them chosen mayor
    "3117670": 9,    # Fremont: mayor and 2 members from each of 4 wards
    "3121415": 9,    # Hastings: mayor and 2 members from each of 4 wards
}


SPEC = cc.Spec(
    tag="ne",
    label="build_ne_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/ne/)",
    seats_file="ne-city-council-seats.json",
    out_file="ne-city-councils.json",
    seats=SEATS,
    # 7 members' e-mail addresses (all Lincoln's) and 9 numbers (all
    # Fremont's) were written down on 2026-11-27; these floors are about two
    # thirds of each.
    min_emails=5,
    min_phones=6,
    wards_file="ne-city-wards.json",
    excerpts={
        "https://citycouncil.cityofomaha.org/councilmembers": "councils/omaha-2026-11-27.txt",
        "https://www.cityofomaha.org/": "councils/omaha-2026-11-27.txt",
    },
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
