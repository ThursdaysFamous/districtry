#!/usr/bin/env python3
"""
Build sd/data/app/sd-city-councils.json: the mayor and council of each of
South Dakota's 3 cities of 25,000 people or more, written down from each
city's own pages and proved against them on every build.

    python3 sd/scripts/build_sd_city_councils.py            # read every page, prove every name, write
    python3 sd/scripts/build_sd_city_councils.py --check    # offline
    python3 sd/scripts/build_sd_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, and why
no city's wards are drawn. The seats are in
sd/data/source/sd-city-council-seats.json, kept by hand.

WHICH PLACES. The 3 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more): Sioux Falls, Rapid City and
Aberdeen, all read on 2026-11-27 by this project's own reader. South Dakota's
other cities and towns name nobody, and gap sd-municipal-officeholders says
so.

WHERE THE NAMES COME FROM. Each city's own council page and its mayor's page.
Sioux Falls's council page prints each member's own telephone number and
e-mail address at siouxfalls.gov, and the card carries them. Rapid City's and
Aberdeen's pages print no contact beside one member alone: the numbers printed
near their mayors are the mayor's office's and the city's main line.

HOW EACH CITY ELECTS, read on 2026-11-27:
  * Sioux Falls: the city's home rule charter, section 2.02(a), read once by
    hand in Adam's Chrome because codelibrary.amlegal.com answers this
    project's reader with HTTP 403: "Three (3) council members shall be
    nominated and elected by the voters of the city at large, and five (5)
    shall be nominated and elected by the voters of each of the five (5)
    council districts". The council page does not say which at-large member
    holds which lettered seat (the 2026 runoff ballot names At Large A), so
    the three are written "At large".
  * Rapid City: the council page quotes the city's own section 9-8-3 (two
    aldermen per ward, each a resident of the ward) and calls the body the
    common council, which is the aldermanic form of SDCL chapter 9-8, whose
    section 9-8-4 reads "two aldermen elected from and by the voters of each
    ward".
  * Aberdeen: the city charter, section 2.02(a), in the code the city
    publishes on its own site (DocumentCenter/View/17960, current through
    2026-05-06): "The council members shall be elected by the voters of the
    city according to districts established in section 6.03", which sets four.
    The charter does not say in so many words that a district's own voters
    elect its members, so it was measured: in the city's canvass of the
    election of 3 June 2025 (Resolution 25-06-01R, published as a legal
    notice), the Southwest District contest drew 398 votes and the Southeast
    District contest 326, at the same three voting centers, which a contest
    the whole city votes in could not do.

WARDS. All three cities elect members by ward or district and none of the
maps is drawn yet; `undrawn` says so city by city, and the City card says the
ward map is not drawn. The status page counts each as owed a ward map.

RE-READ. Sioux Falls elects in June of even years and Rapid City and Aberdeen
every June; sd/WATCH.md carries the re-read after each election.
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
    "4659020": 9,   # Sioux Falls: mayor, 5 districts, 3 at large
    "4652980": 11,  # Rapid City: mayor, 2 members from each of 5 wards
    "4600100": 9,   # Aberdeen: mayor, 2 members from each of 4 districts
}

NOT_DRAWN = "its wards are not drawn yet; the city publishes them as a map"

SPEC = cc.Spec(
    tag="sd",
    label="build_sd_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/sd/)",
    seats_file="sd-city-council-seats.json",
    out_file="sd-city-councils.json",
    seats=SEATS,
    # 8 members' e-mail addresses and 8 members' numbers were written down on
    # 2026-11-27, all Sioux Falls's; these floors are about two thirds of each.
    min_emails=5,
    min_phones=5,
    undrawn={geoid: NOT_DRAWN for geoid in SEATS},
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
