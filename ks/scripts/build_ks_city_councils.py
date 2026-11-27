#!/usr/bin/env python3
"""
Build ks/data/app/ks-city-councils.json: the mayor and council or commission
of each of Kansas's 16 cities of 25,000 people or more, written down from each
city's own pages and proved against them on every build.

    python3 ks/scripts/build_ks_city_councils.py            # read every page, prove every name, write
    python3 ks/scripts/build_ks_city_councils.py --check    # offline
    python3 ks/scripts/build_ks_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, which
pages were read once by hand or rendered once, and why no city's wards are
drawn. The seats are in ks/data/source/ks-city-council-seats.json, kept by
hand.

WHICH PLACES. The 16 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more): Wichita, Overland Park, Kansas
City, Olathe, Topeka, Lawrence, Shawnee, Lenexa, Manhattan, Salina,
Hutchinson, Leavenworth, Leawood, Garden City, Dodge City and Derby, all read
on 2026-11-27. Kansas's other cities name nobody, and gap
ks-municipal-officeholders says so.

PAGES READ ONCE BY HAND in Adam's Chrome on 2026-11-27 (Adam, 2026-11-25),
because the cities' sites refuse this project's reader: Wichita's and
Olathe's answer it with HTTP 403, and Lawrence's, Shawnee's and Leawood's
council lists are on civicweb.net hosts whose robots.txt disallows them (and
www.leawood.org answers with 403). TWO PAGES WERE RENDERED ONCE by this
project's own reader, with its own token, in a browser engine: Overland
Park's and Hutchinson's council pages fill their member lists in with a
script from a feed that needs a key the script obtains, and their static
markup names nobody (Overland Park's carries the names, and no ward). What
was read is kept, dated, in ks/data/source/councils/, and the build proves
names and contacts against those excerpts (`excerpts` below); they are not
re-read automatically, and ks/WATCH.md carries the re-read.

HOW EACH CITY ELECTS, read or measured on 2026-11-27:
  * Johnson County's five (Overland Park, Olathe, Shawnee, Lenexa, Leawood):
    measured from the Johnson County Election Office's official results of
    the general election of 4 November 2025 (CG2025 Official Final Results,
    jocoelection.org). Overland Park's six ward contests drew 5,214, 8,656,
    6,510, 6,485, 6,089 and 5,995 votes, which sum exactly to the mayor's
    38,949; Olathe's at-large contest drew 19,272 and its Ward 3 and Ward 4
    contests 4,779 and 4,637; Lenexa's, Leawood's and Shawnee's ward contests
    drew a quarter of their cities' votes or so each. A contest the whole city
    votes in could do none of that. Shawnee's council page adds "Each ward has
    two representatives".
  * Wichita: its council page, "Six Council members are elected by district,
    and the Mayor is elected at-large" (the Chrome excerpt).
  * Topeka: Shawnee County's results of 4 November 2025, read in Adam's Chrome
    because cdn.snco.gov disallows this project's reader: the mayor's contest
    drew 17,192 votes, District 1's 1,388 and District 3's 882.
  * Kansas City: the Unified Government's Board of Commissioners page, "Eight
    of the Commission members are nominated and elected from districts. The
    two at-large Commission members are nominated from districts and elected
    at-large", and the mayor/CEO "nominated at-large". The Unified Government
    governs Wyandotte County as well as the city, and the card says so; its
    citywide seats are labelled "At large", not "elected by the whole city".
  * Derby: its council page, "City Council members are elected by ward",
    two from each of four wards it numbers I to IV (written 1 to 4 here).
  * Hutchinson: its council page, "1 elected at-large and 4 elected by
    districts", the mayor and vice-mayor "selected for a 1-year term by the
    Council members". Scott Meggers holds the Northeast District seat and is
    mayor. The Southwest District seat is vacant: the city's application page
    asks for applicants to "fill the unexpired term for the Southwest District
    seat", and the seat carries `vacant` with those words.
  * At large, from each city's own page: Lawrence ("five officials elected at
    large", mayor and vice-mayor elected by the commission each December),
    Manhattan ("five commissioners who are elected at-large", mayor chosen by
    the commission each year), Salina ("five members elected at-large") and
    Garden City ("elected at large by the public", mayor "selected annually").
  * Leavenworth: its page does not say, so it was measured: Leavenworth
    County's abstract of the general election of 7 November 2023 lists "CITY
    OF LEAVENWORTH, COMMISSION: (Elect 3)", one contest counted in every
    precinct of every ward.
  * Dodge City: its page says "There are three seats available each election"
    and that commissioners serve four or two years "depending on the amount of
    votes they receive", one ranked contest for three seats, which a ward
    election could not be.

LAWRENCE LABELS NO MAYOR. The commission named Brad Finkeldei mayor and Mike
Courtney vice mayor "on December 2, 2025", and both terms "end on December 1,
2026", four days after the read; so all five seats are written "At large" and
the card's sentence says the commission chooses its mayor each December.
Re-read after the commission's first December meeting (ks/WATCH.md).

CONTACTS. Every city here but Wichita, Manhattan, Salina and Derby prints a
member's own e-mail address or number beside that member alone, and the card
carries them. Lenexa prints the city's main line (913.477.7500) beside one
member, which `officeLines` records so no seat carries it. Kansas City's
addresses are written in code by Cloudflare's e-mail protection and read
decoded. Topeka's page prints a street address beside one member; it is
never carried.

WARDS. Ten of the sixteen cities elect members by ward or district and none
of their maps is drawn yet; `undrawn` says so city by city, and the City card
says the ward map is not drawn. The status page counts each as owed a ward
map.

RE-READ. Kansas's cities elect in November of odd years and seat the winners
in January; mayors chosen by their commissions change in December (Lawrence)
or January (Salina, Dodge City, Garden City, Manhattan, Hutchinson).
ks/WATCH.md carries those re-reads.
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
    "2079000": 7,    # Wichita: mayor and 6 districts
    "2053775": 13,   # Overland Park: mayor and 2 members from each of 6 wards
    "2036000": 11,   # Kansas City (Unified Government): mayor, 2 at large, 8 districts
    "2052575": 7,    # Olathe: mayor, 4 wards, 2 at large
    "2071000": 10,   # Topeka: mayor and 9 districts
    "2038900": 5,    # Lawrence: 5 commissioners at large
    "2064500": 9,    # Shawnee: mayor and 2 members from each of 4 wards
    "2039350": 9,    # Lenexa: mayor and 2 members from each of 4 wards
    "2044250": 5,    # Manhattan: 5 commissioners at large
    "2062700": 5,    # Salina: 5 commissioners at large
    "2033625": 5,    # Hutchinson: 4 districts and 1 at large
    "2039000": 5,    # Leavenworth: 5 commissioners at large
    "2039075": 9,    # Leawood: mayor and 2 members from each of 4 wards
    "2025325": 5,    # Garden City: 5 commissioners at large
    "2018250": 5,    # Dodge City: 5 commissioners at large
    "2017800": 9,    # Derby: mayor and 2 members from each of 4 wards
}

NOT_DRAWN = "its wards are not drawn yet; the city publishes them as a map"
BY_WARD = ("2079000", "2053775", "2036000", "2052575", "2071000", "2064500",
           "2039350", "2033625", "2039075", "2017800")

SPEC = cc.Spec(
    tag="ks",
    label="build_ks_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/ks/)",
    seats_file="ks-city-council-seats.json",
    out_file="ks-city-councils.json",
    seats=SEATS,
    # 90 members' e-mail addresses and 68 numbers were written down on
    # 2026-11-27; these floors are about two thirds of each.
    min_emails=60,
    min_phones=45,
    undrawn={geoid: NOT_DRAWN for geoid in BY_WARD},
    excerpts={
        "https://www.wichita.gov/599/City-Council": "councils/wichita-2026-11-27.txt",
        "https://www.olatheks.gov/government/city-council": "councils/olathe-2026-11-27.txt",
        "https://lawrenceks.civicweb.net/portal/members.aspx?id=10": "councils/lawrence-2026-11-27.txt",
        "https://cityofshawnee.civicweb.net/portal/members.aspx?id=10": "councils/shawnee-2026-11-27.txt",
        "https://leawood.civicweb.net/portal/members.aspx?id=10": "councils/leawood-2026-11-27.txt",
        "https://www.opkansas.gov/city-council": "councils/overland-park-2026-11-27.txt",
        "https://www.hutchinsonks.gov/city-council": "councils/hutchinson-2026-11-27.txt",
        "https://www.hutchinsonks.gov/application-for-southwest-district-council-seat-1":
            "councils/hutchinson-southwest-2026-11-27.txt",
    },
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
