#!/usr/bin/env python3
"""
Build ok/data/app/ok-city-councils.json: the mayor and council of each of
Oklahoma's 16 cities above 25,000 people, written down from each city's own
pages and proved against them on every build.

    python3 ok/scripts/build_ok_city_councils.py            # read every page, prove every name, write
    python3 ok/scripts/build_ok_city_councils.py --check    # offline
    python3 ok/scripts/build_ok_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, which page
is read with a browser's client and why, and which cities' wards are not
drawn. The seats themselves are in ok/data/source/ok-city-council-seats.json,
kept by hand, and the drawn wards and districts of the nine cities whose wards
are drawn in ok/data/app/ok-city-wards.json (ok/scripts/build_ok_city_wards.py),
which --check holds the seats to.

WHICH PLACES. The 16 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more), all 16 cities, all read on
2026-10-16. Oklahoma's other cities and towns are not named, and gap
ok-municipal-officeholders says so.

WHERE THE NAMES COME FROM. Each city's own pages, because no state office
publishes Oklahoma's city officials. Tulsa's mayor is from the mayor's own page
on the city's site, because the council's site lists only the councilors.
Muskogee's are not from the city at all: its website's robots.txt (redirected
to files.muskogeeonline.org, 210 bytes, last modified 14 December 2022) allows
five named crawlers and then states `User-agent: *` / `Disallow: /`, so no page
of it is read. They come instead from
  * the Muskogee County Election Board's official results for the city's
    election of 10 February 2026, in the copy KJRH, a Tulsa television
    station, published with its report (ok/scripts/muskogee_results.py, which
    names a winner only where a candidate had more than half the votes): the
    mayor and one member each for Wards 1, 2 and 3;
  * the Muskogee Phoenix's report of the runoffs of 7 April 2026: the other
    Ward 1 member, elected to the rest of an unexpired term, and one Ward 4
    member;
  * KJRH's report of 13 August 2026 that the council appointed the other Ward 2
    member at its meeting of 27 July 2026; and
  * the Muskogee Phoenix's report of the election of 13 February 2024, as
    carried by Yahoo News: the other Ward 3 and Ward 4 members, each elected
    to a four-year term.
The card says where Muskogee's names come from. The State Election Board's
own results site answered this project's client with HTTP 403 on 2026-10-16,
and no city page has been read to say whether anyone has left since, which is
why gap ok-municipal-officeholders records Muskogee as named from those
sources. Muskogee's council page is linked for a reader from the address a
search engine lists for it, and is never fetched.

HOW EACH CITY ELECTS, which is what decides whether its wards are drawn. No
state office records it, so it was read from each city's charter, its own
pages, a county election board's results or news reports, on 2026-10-16:
  * ELECTED BY WARD OR DISTRICT, by that ward's own voters:
    Oklahoma City and Norman (each council page: "The voters in each Ward
    elect a Council member to represent them, and all City voters elect the
    Mayor"; in the Cleveland County Election Board's certificate for 13
    February 2024 each Norman ward contest was on 6 to 10 precincts), Tulsa
    (the council's site: "9 members, elected by district"; the Tulsa County
    Election Board's 2026 election packet: "Each one of the nine (9) said City
    Councilors shall be elected from his or her respective City Council
    Election District"), Lawton (the city's news of 18 August 2026: "Only
    registered voters who live in Wards 1, 2, 6, and 7 can vote their ward's
    race"; the mayor's contest of August 2024 counted 6,163 ballots against
    664 in Ward 1's, as the Southwest Ledger reported them), Moore (the
    council page: the mayor "is elected at-large, and six council members ...
    are elected from three wards"; in the same Cleveland County certificate
    the mayor's contest was on 22 precincts with 3,104 votes and Ward 2's on
    11 of them with 1,010), Midwest City (charter, Article VI section 1: "a
    councilman shall be elected by majority vote of the qualified electors
    voting in the respective ward"), Enid (the Enid News & Eagle, 7 February
    2023: "Only registered voters in Ward 2 will be able to vote in the race";
    the mayor's contest of that month was "the citywide election"),
    Bartlesville (charter, Article 3 section 5: "each council member to be
    elected by the registered voters in the ward in which he or she resides"),
    Muskogee (in the county's results for 10 February 2026 the mayor's
    contest was on 24 of 24 precincts and each ward's on 7 to 10, and the four
    ward contests drew 3,803 votes between them against the mayor's 3,824),
    Shawnee (the city's page about its charter election of 13 June 2023, at
    which "all seven Charter amendments were passed", the first of them
    "Switching to Ward-specific voting for Commissioners"; the mayor, whom no
    ward elects, is recorded as elected by the whole city) and Bixby (the
    council's Resolution 2025-27 of 8 December 2025: the charter "calls for
    an election of a Council Member to be held within the precincts lying
    within the ward boundaries of each ward").
  * TIED TO A WARD AND ELECTED BY THE WHOLE CITY: Broken Arrow (the council
    page: "While council members from the four wards must live in that ward,
    all registered voters in the city are eligible to vote on each"), Owasso
    (charter section 6-1(e): "all councilors shall be elected, at large, by
    the qualified electors of the entire city, although they must reside in
    the respective wards from which they are candidates"), Jenks (the council
    page: "All registered voters in the city are eligible to vote on each")
    and Edmond (charter section 9: each ward's council member is "nominated at
    the primary election by the electors of the ward", and "In all general
    City elections, the candidates for City and Ward offices shall be voted
    upon by the electors of the City at large"; section 79: a ward's primary
    is held only where more than two candidates file). These are recorded as
    elected by the whole city, so none of their wards is drawn. Stillwater's
    council has no wards: "five members who are elected at large".
The seat each mayor holds is labelled "Mayor" whether the voters elect the
mayor or the council chooses one of its members, as it does in Broken Arrow,
Bartlesville, Owasso, Bixby and Jenks (each from the council's own members,
by its charter or as its minutes record), and each city's sentence says which.
A mayor chosen from a ward's seat keeps that ward, so the card says which ward
elected the member who is now mayor. A vice mayor or mayor pro tem chosen by
the council keeps the seat the voters gave.

WIKIPEDIA SAYS MUSKOGEE'S COUNCIL IS ELECTED CITYWIDE, and the county's
official results say otherwise: each ward contest of 10 February 2026 was on
that ward's precincts alone, and between them they drew one vote per ballot
in the mayor's contest. The results are what this file follows.

BROKEN ARROW'S PAGE IS READ WITH A BROWSER'S CLIENT, and this is the
measurement that allows it (CLAUDE.md, "Browser user-agent strings"). On
2026-10-16 the city's site answered this project's token with HTTP 403 both for
its robots.txt and for the council page, the page's answer being its Akamai
edge's "Access Denied" (406 bytes). With Chrome/126 and its client hints on the
stdlib client (scraper_common.UA_HINTS_CHROME_126) the site serves its
robots.txt (6,641 bytes, the same content-management vendor's default file,
identical by MD5, that Collierville and Germantown serve in Tennessee and
Kendall County, McHenry County and Joliet in Illinois), no rule in it matching
the page, and the council page (HTTP 200, 137,000 bytes, every member named).
The robots.txt is read with that same client before the page is. Every other
page here is read with this project's own token, and each served it.

LAWTON'S WARDS ARE NOT DRAWN. The city publishes one ward map as data, in
three layers that carry the same lines, and on the 2020 census its wards hold
from 9,180 to 12,570 people leaving out Ward 2, which holds Fort Sill (18,668
with it), against an even share of 11,296; the layer's own population figures
disagree with its lines. Wards redrawn after the 2020 census would be close to
even, so this may not be the map in force, and the card says the wards are not
drawn yet. MUSKOGEE'S WARDS ARE NOT DRAWN because the city publishes no copy
this project may read; the University of Oklahoma publishes one, and its
terms of use are not settled.

PRIVACY AND CONTACTS. A member's e-mail address and telephone numbers are
carried where the page the seat cites prints them beside that member alone,
under Adam's rulings of 2026-10-17; scripts/city_councils.py (CONTACTS) says
what does not ship and how the build proves each value on its page. Read on
2026-10-17:
  * The pages cited for Bixby, Edmond, Jenks, Lawton, Stillwater and Tulsa
    print no e-mail address or number beside any one member, only the city's
    or the council's own or none, so their members carry none. Muskogee's
    members carry none because their names come from the county election
    board's results and from news reports, not from the city's own pages.
  * Broken Arrow's council page prints each member's city e-mail address,
    which is carried, and the council's own telephone number for all of them,
    which is the office's and is not.
No street address is carried, nor anything about residents or applicants, nor
a biography.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ok-municipal-officeholders): no state office publishes who holds Oklahoma's
city offices or where their wards run; whether a city's wards elect its
members is set by each city's charter, and four of the sixteen elect
ward-labelled seats citywide; the State Election Board's results site
refuses this project's client, and the county election boards publish results
in formats of their own; Muskogee's official results were found only as a copy
on a television company's servers, and its website refuses every crawler but
five named ones; Enid's municipal code and meeting records, a document of
Shawnee's 2023 charter election and Muskogee's council documents are on sites
that refuse this project; Broken Arrow's site refuses this project's own
client; Lawton's published ward map does not balance on the 2020 census;
and Wikipedia's account of Muskogee's elections is out of date.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import city_councils as cc  # noqa: E402
import muskogee_results  # noqa: E402
from scraper_common import UA_HINTS_CHROME_126  # noqa: E402

BROKEN_ARROW_COUNCIL = "https://www.brokenarrowok.gov/government/city-council"

# Seats per place, the mayor included, as each place's own page (or, for
# Muskogee, its results and reports) gives them on 2026-10-16. A redistricting
# or a charter change moves these legitimately: read the place's page, then
# change the number deliberately.
SEATS = {
    "4055000": 9,   # Oklahoma City: mayor, 8 wards
    "4075000": 10,  # Tulsa: mayor, 9 districts
    "4052500": 9,   # Norman: mayor, 8 wards
    "4009050": 5,   # Broken Arrow: 4 ward seats and 1 at large, all citywide; one chosen mayor
    "4023200": 5,   # Edmond: mayor, 4 ward seats elected citywide
    "4041850": 9,   # Lawton: mayor, 8 wards
    "4049200": 7,   # Moore: mayor, 2 members from each of 3 wards
    "4048350": 7,   # Midwest City: mayor, 6 wards
    "4023950": 7,   # Enid: mayor, 6 wards
    "4070300": 5,   # Stillwater: mayor, 4 seats at large
    "4056650": 5,   # Owasso: 5 ward seats elected citywide; one chosen mayor
    "4004450": 5,   # Bartlesville: 5 wards; one member chosen mayor
    "4050050": 9,   # Muskogee: mayor, 2 members from each of 4 wards
    "4066800": 7,   # Shawnee: mayor, 6 wards
    "4006400": 5,   # Bixby: 5 wards; one member chosen mayor
    "4037800": 7,   # Jenks: 6 ward seats and 1 at large, all citywide; one chosen mayor (Ward 5 empty)
}

SPEC = cc.Spec(
    tag="ok",
    label="build_ok_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/ok/)",
    seats_file="ok-city-council-seats.json",
    out_file="ok-city-councils.json",
    seats=SEATS,
    # 61 members' e-mail addresses and 30 members' numbers were written down
    # on 2026-10-17; these floors are about two thirds of each.
    min_emails=41,
    min_phones=20,
    browser={
        BROKEN_ARROW_COUNCIL: UA_HINTS_CHROME_126,
    },
    readers={url: muskogee_results.text for url in muskogee_results.RESULTS},
    wards_file="ok-city-wards.json",
    undrawn={
        "4041850": "the only ward map the city publishes as data does not divide the 2020 "
                   "census population evenly, so it may not be the map in force",
        "4050050": "the city publishes no copy of its wards this project may read, and the "
                   "University of Oklahoma's copy waits on its terms of use",
    },
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
