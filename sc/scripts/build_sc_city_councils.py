#!/usr/bin/env python3
"""
Build sc/data/app/sc-city-councils.json: the mayor and council of each of
South Carolina's 17 cities and towns above 25,000 people, written down from
each city's own pages and proved against them on every build.

    python3 sc/scripts/build_sc_city_councils.py            # read every page, prove every name, write
    python3 sc/scripts/build_sc_city_councils.py --check    # offline
    python3 sc/scripts/build_sc_city_councils.py --watch    # is every name still on its page?

The work is scripts/city_councils.py, which says what the proof is and what it
cannot prove. This file says which places, how many seats each has, and which
page is read with a browser's client and why. The seats themselves are in
sc/data/source/sc-city-council-seats.json, kept by hand, and the drawn
districts of the twelve places whose districts are drawn in
sc/data/app/sc-city-wards.json (sc/scripts/build_sc_city_wards.py), which
--check holds the seats to.

WHICH PLACES. The 17 the done standard counts (docs/expected-governments.json,
Census 2020 population of 25,000 or more), all 17 read on 2026-10-16: thirteen
cities and four towns (Mount Pleasant, Summerville, Hilton Head Island and
Bluffton). South Carolina's other 254 cities and towns are not named, and gap
sc-municipal-officeholders says so.

WHERE THE NAMES COME FROM. Each place's own pages, because no state office
publishes South Carolina's city officials. The Municipal Association of South
Carolina publishes a page for every city and town naming its mayor and council,
and it is not used: it gives no seat or district and no date, so it cannot say
which member a district elects or when the list was last true. Three names
come from a second page: Charleston's and North Charleston's mayors from each
mayor's own page, because the council page lists only the members, and
Anderson's Seat 5 from the Anderson Observer's report of the city's 7 April
2026 election, because the city's own page still lists that seat as vacant.

HOW EACH PLACE ELECTS, which is what decides whether its districts are drawn.
Nothing the state publishes records it, so it was measured from the ballot,
comparing the precincts a district's contest was on with those of the mayor's
or another citywide contest in the same county's file, in the State Election
Commission's certified results for 2022 to 2025 (www.enr-scvotes.org, read
2026-10-16):
  * ELECTED BY DISTRICT OR WARD, a seat's contest on that district's precincts
    alone: Charleston (11 of 12 districts read; District 1 was on neither
    file), Columbia (all four districts; its two at-large seats citywide),
    North Charleston (all ten), Rock Hill (Wards 4 to 6 read; the city's page
    says all six members are elected by wards), Greenville (all four; two at
    large), Summerville (all six), Sumter (all six), Florence (all three; three
    at large), Spartanburg (Districts 2, 4, 5 and 6 read), Hilton Head Island
    (all six wards), Greer (Districts 2, 4 and 6 read) and Aiken (all six). The
    seats not read are taken to follow the rule their city's other seats were
    measured to follow, which is an inference and is recorded as one here.
  * ANDERSON'S election is not on that service. The city's notice of its 7
    April 2026 election says Seats 1, 3 and 5 are single-member districts and
    the mayor and Seat 7 are elected at large; that day Seat 2's special
    election drew 194 votes, beside 179 to 219 for Seats 1, 3 and 5, 971 for
    Seat 7 and 1,281 for mayor (the Observer's unofficial counts). The city
    publishes a district map for each of Seats 1 to 6 and its council page
    calls Seats 7 and 8 at large, so Seats 2, 4 and 6 are taken to be elected
    by their districts and Seat 8 by the whole city, which is an inference for
    Seats 4, 6 and 8 and is recorded as one here. Its districts are not drawn,
    because those maps are pictures in PDF files, and
    scripts/build_eam_status.py records that.
  * ELECTED CITYWIDE: Mount Pleasant (its council contest on all 40 of the
    mayor's precincts in 2025), Goose Creek (22 of 22, 2022), Myrtle Beach (16
    of 16, 2025) and Bluffton, whose own page says its council members serve at
    large and whose council is one contest on its ballot.

ROCK HILL IS READ WITH A BROWSER'S CLIENT, and this is the measurement that
allows it (CLAUDE.md, "Browser user-agent strings"). On 2026-10-16
scripts/probe_user_agents.py asked the city's council members page, the page
the city's own ward map links, four ways: this project's token got HTTP 403 on
both the requests and the stdlib stacks, Chrome/126 with its client hints got
403 on requests and HTTP 200 (168,899 bytes, every member named) on stdlib.
The 403 is the city's Akamai edge (Server AkamaiGHost, "Access Denied", 390
bytes, the same answer for robots.txt), not this sandbox's proxy. With
Chrome/126 and its client hints on the stdlib client
(scraper_common.UA_HINTS_CHROME_126) robots.txt is served (6,641 bytes: the
site platform's own rules, none matching the members page) and is read with
that same client before the page is. The page carries a reCAPTCHA key for its
site forms and no challenge. Every other page here is read with this project's
own token, and each served it.

PRIVACY AND CONTACTS. A member's e-mail address and telephone numbers are
carried where the page the seat cites prints them beside that member alone,
under Adam's rulings of 2026-10-17; scripts/city_councils.py (CONTACTS) says
what does not ship and how the build proves each value on its page. Read on
2026-10-17:
  * The pages cited for Bluffton, Columbia, Florence, Goose Creek,
    Greenville, Mount Pleasant and Rock Hill print no e-mail address or
    number beside any one member, only the city's or the council's own or
    none, so their members carry none. Charleston's council page prints none
    for its members either, and only the mayor carries what the mayor's own
    page prints.
  * Aiken's council page prints one city line for several members, which is
    the office's and is not carried, and its own number for each of the
    others, which is.
  * Anderson's page prints one member's e-mail address in a link that sends
    to a differently spelled one, and Myrtle Beach's prints one member's in a
    link that sends to another, so neither member carries an e-mail address.
    Anderson's seat whose name comes from a newspaper carries nothing, since
    contacts come only from the city's own pages.
  * North Charleston's mayor's page prints the Mayor's Office's e-mail
    address and lines, which are the office's and are not carried.
No street address is carried, nor anything about residents or applicants, nor
a biography.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
sc-municipal-officeholders): no state office publishes who holds South
Carolina's city offices, and the Municipal Association's pages, the only
statewide list, give no seat, district or date; which seats a city elects by
district is set by its own ordinances and can be read only from the precinct
lists in each county's election results, where one county labels a city's
wards "District" in one year and "Ward" in the next and another spells
"Distrcit"; one city's page still lists a seat as vacant six months after the
election that filled it, so its name comes from a newspaper; one city
publishes its districts only as pictures; and one refuses this project's
client.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import city_councils as cc  # noqa: E402
from scraper_common import UA_HINTS_CHROME_126  # noqa: E402

ROCK_HILL_MEMBERS = "https://www.cityofrockhill.com/government/city-council/members"

# Seats per place, the mayor included, as each place's own page lists them on
# 2026-10-16. A redistricting or a charter change moves these legitimately:
# read the place's page, then change the number deliberately.
SEATS = {
    "4513330": 13,  # Charleston: mayor, 12 districts
    "4516000": 7,   # Columbia: mayor, 4 districts, 2 at large
    "4550875": 11,  # North Charleston: mayor, 10 districts
    "4548535": 9,   # Mount Pleasant: mayor, 8 at large
    "4561405": 7,   # Rock Hill: mayor, 6 wards
    "4530850": 7,   # Greenville: mayor, 4 districts, 2 at large
    "4570270": 7,   # Summerville: mayor, 6 districts
    "4529815": 7,   # Goose Creek: mayor, 6 at large
    "4570405": 7,   # Sumter: mayor, 6 wards
    "4525810": 7,   # Florence: mayor, 3 districts, 3 at large
    "4568290": 7,   # Spartanburg: mayor, 6 districts
    "4534045": 7,   # Hilton Head Island: mayor, 6 wards
    "4549075": 7,   # Myrtle Beach: mayor, 6 at large
    "4530985": 7,   # Greer: mayor, 6 districts
    "4500550": 7,   # Aiken: mayor, 6 districts
    "4501360": 9,   # Anderson: mayor, 6 districts, 2 at large
    "4507210": 5,   # Bluffton: mayor, 4 at large
}

SPEC = cc.Spec(
    tag="sc",
    label="build_sc_city_councils",
    user_agent="districtry/1.0 (+https://districtry.com/sc/)",
    seats_file="sc-city-council-seats.json",
    out_file="sc-city-councils.json",
    seats=SEATS,
    # 59 members' e-mail addresses and 39 members' numbers were written down
    # on 2026-10-17; these floors are about two thirds of each.
    min_emails=39,
    min_phones=26,
    browser={ROCK_HILL_MEMBERS: UA_HINTS_CHROME_126},
    wards_file="sc-city-wards.json",
    undrawn={"4501360": "the city publishes its six council districts only as pictures in PDF files"},
)

if __name__ == "__main__":
    cc.main(SPEC, __doc__)
