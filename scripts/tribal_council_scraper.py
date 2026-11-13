#!/usr/bin/env python3
"""
Read who sits on the council of each nation whose land a districtry app draws, from the nation.

THE AUTHORITY IS EACH NATION'S OWN PUBLISHED COUNCIL. The Bureau of Indian
Affairs' directory carries one leader per government and never a council, so
there is no federal list to read instead. This module reads one page per
nation (two for the Ho-Chunk Nation and the Little Traverse Bay Bands, whose
executive and legislative branches publish separately), with a parser written
for that page, and writes data/tribal-councils.json. Illinois's one nation, the
Prairie Band Potawatomi, is governed from Kansas and holds trust land near
Shabbona; its council page was behind a Cloudflare challenge on 2026-10-01 and
served this project normally on three reads on 2026-10-10, which is when it was
added. scripts/build_tribal_areas.py
--rosters stamps it onto each instance's tribal-areas.json, offline.

A STATE'S LIST, AND ONLY WHERE THE NATION PUBLISHES NOTHING. The Wisconsin
Department of Administration publishes "Wisconsin Tribal Head Officials", a
one-page PDF naming every Wisconsin nation's council (updated 8 July 2026 when
this was written). It is a government publisher, but it is a state's list of
another government's officials, and on 2026-10-06 it was already behind four
nations' own pages (Oneida's vice-chair and two council seats, two of
Stockbridge-Munsee's, and a Forest County Potawatomi suffix). So it is used for
exactly the two Wisconsin nations that publish no council at all: Lac du
Flambeau, whose recorded council address now serves its employment page and
whose site names no council anywhere this project could find, and Sokaogon,
whose whole navigation names none. The card says the names are the state's and
gives the state's own date. Michigan has no current equivalent (the state's
own directory is dated January 2017), so Michigan's unreadable councils stay
unnamed.

Virginia's Secretary of the Commonwealth publishes a list of the state's
recognized tribes that names each tribe's chief and assistant chief and no
council member. It is used for the one Virginia nation with land on the map
that publishes no council, the Rappahannock Tribe, and for its two leaders
only, on Adam's ruling of 2026-10-30. Every other nation here is carried with
its whole council, so the card heads these two names "Chief and Assistant
Chief" rather than "Council" and says the rest of the council is not named.
The list writes the office "Assistant Cheif"; the office is read and written
correctly, and the names are carried as the list prints them.

WHAT A PARSER MAY NOT DO. A parser returns exactly the seats its page states,
and `SEATS` pins how many that is: a page that loses a member, gains a staff
row, or changes shape fails the run rather than shipping a short or padded
council. Nothing is corrected. Two cases are carried as published with a note
rather than repaired:
  * Bad River's page spells its treasurer "Michelle Conners" in its current
    council block and "Michelle Connors" in the contact table below it, and the
    state's list says Connors. The council block is what ships, with the other
    spelling stated on the row, because choosing between a nation's two
    spellings of its own officer is not this project's call.
  * Stockbridge-Munsee prints one member as "JOE Miller". Casing is the
    nation's and ships unchanged; so do the Yurok Tribe's names, all in
    capitals.
  * Several pages read on 2026-11-13 contradict themselves about one member:
    a paragraph giving another office or spelling (Chehalis, Jamul) or a
    contact card spelling a name another way (Pala). The council block
    ships, with the page's other wording stated on the row.
  * A courtesy title (Mr., Ms., Mrs.) is not part of a name and is dropped
    (Quechan, Round Valley); "Dr." and "Esq." are the page's own and ship.
  * An alternate (Redding), a proxy (Torres Martinez) or a staff member
    listed under a council (Soboba's executive assistant) is not a seat.
    Shingle Springs lists a Secretary with no term under its council of
    seven elected members; that row ships as printed and says so.
  * Duckwater prints its offices in capitals, which is the page's styling,
    so each is written in title case; Paskenta writes one office "Tribal
    COuncil Member at Large", which is read and written correctly.
A COUNCIL MISSING ONE SEAT IS CARRIED, AND SAYS WHICH (Adam's ruling,
2026-11-13, "carry"). Where a page says how many seats its council has and
names every member, or all but one, or says which seats are vacant, the
council ships, and NATIONS' "partial" is the sentence the card adds saying
which seat the page leaves out: Ak-Chin's page names four of its five
members, Hopi's 21 of its 22 village representatives (under the five
officers it lists first), and the Washoe Tribe's one of its two
Off-Reservation representatives; Duckwater lists two seats as vacant and
Paskenta one. Each of those parsers checks the fact its sentence states, so
a seat filled or newly left empty fails the run rather than leaving a card
line that is no longer true. A page that names only its officers or only
its chair is still not carried.

Contact details ship only where the page pairs them with the person on the
same row, never from a table elsewhere on the page with a different date
(Bad River's contact table is headed "2021", so its numbers are not taken).

DISTRICTS. Some councils are elected by district — Ho-Chunk's four, the Sault
Tribe's five units, Gun Lake's three, Fond du Lac's three. Those are the
nation's MEMBERSHIP districts, not shapes this app draws, so a district is
carried as a word on the member's row and never as geometry. Saginaw Chippewa's
list and its own biographies disagree about one member's district (the list
says "District 3", the biography "At-Large District 2"), so no Saginaw
district is carried at all.

PRESERVE, NEVER DELETE (Adam's ruling, 2026-09-19). A nation whose page cannot
be read this week keeps its last-read council with the date it was last read,
which the card prints. A refusal stops the fetch and never unpublishes. A
nation that has never been read and fails is a failed run.

Every page is fetched only after its robots.txt is read with the same client,
through scraper_common.require_robots_once.

Usage:
    python3 scripts/tribal_council_scraper.py                 # fetch and write
    python3 scripts/tribal_council_scraper.py --from-dir DIR  # parse saved pages
    python3 scripts/tribal_council_scraper.py --selftest      # offline
"""

import argparse
import datetime
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "tribal-councils.json")

WI_DOA_LIST = "https://doa.wi.gov/DIR/Tribal-Leaders.pdf"
VA_SOC_LIST = "https://www.commonwealth.virginia.gov/virginia-indians/state-recognized-tribes/"

# The councils file's own description. It names no state, because a list of
# states here went stale the day a state was added without it (Mississippi's
# band was read from 2026-10-15 and the list still ended at Tennessee).
NOTE = ("Who sits on the council of each nation whose land a districtry app draws, "
        "read by scripts/tribal_council_scraper.py. Stamped onto the cards by "
        "scripts/build_tribal_areas.py --rosters.")

# AIANNH code -> the pages read and the parser. `seats` is the exact number of
# members the page states today; see the module docstring.
_SENECA = ["https://sni.org/about-our-government/executive/",
           "https://sni.org/about-our-government/council/"]
NATIONS = {
    "0140": {"nation": "Bad River", "pages": ["https://www.badriver-nsn.gov/government/"], "seats": 7},
    "0170": {"nation": "Bay Mills", "pages": ["https://www.baymills.org/executive-council"], "seats": 5},
    "1125": {"nation": "Fond du Lac", "pages": ["https://www.fdlband.org/government/tribal_council.php"], "seats": 5},
    "1135": {"nation": "Forest County Potawatomi", "pages": ["https://www.fcpotawatomi.com/government/executive-council/"], "seats": 6},
    "1370": {"nation": "Grand Traverse", "pages": ["https://www.gtbindians.org/council_members.asp"], "seats": 7},
    "1450": {"nation": "Ho-Chunk", "pages": [
        "https://ho-chunknation.com/government/executive-branch/office-of-the-president/",
        "https://ho-chunknation.com/government/legislative-branch/"], "seats": 13},
    "1550": {"nation": "Nottawaseppi Huron", "pages": ["https://nhbp-nsn.gov/tribal-council/"], "seats": 5},
    "1610": {"nation": "Saginaw Chippewa", "pages": ["https://www.sagchip.org/council/councilprofiles.aspx"], "seats": 12},
    "1815": {"nation": "Lac Courte Oreilles", "pages": ["https://lco-nsn.gov/tribal-governing-board/"], "seats": 7},
    "1825": {"nation": "Lac du Flambeau", "pages": [WI_DOA_LIST], "seats": 12, "stateList": "wi"},
    "1830": {"nation": "Lac Vieux Desert", "pages": ["https://lvd-nsn.gov/Content/Tribal-Council.cfm"], "seats": 9, "br": " "},
    "1963": {"nation": "Little Traverse Bay", "pages": [
        "https://ltbbodawa-nsn.gov/government/executive/tribal-chairman-tribal-vice-chairperson/",
        "https://ltbbodawa-nsn.gov/tribal-council-and-legislative-office/"], "seats": 11},
    "2150": {"nation": "Gun Lake", "pages": ["https://gunlaketribe-nsn.gov/about/tribal-council/"], "seats": 7},
    "2175": {"nation": "Menominee", "pages": ["https://www.menominee-nsn.gov/GovernmentPages/Legislature"], "seats": 9},
    "2560": {"nation": "Oneida", "pages": ["https://oneida-nsn.gov/government/business-committee/members/"], "seats": 9},
    # Minnesota (read 2026-10-10)
    "0335": {"nation": "Bois Forte", "pages": ["https://boisforte.com/departments/tribal-council/"], "seats": 5},
    "1940": {"nation": "Leech Lake", "pages": ["https://www.llojibwe.org/government/government.html"], "seats": 5},
    "2055": {"nation": "Lower Sioux", "pages": ["https://lowersioux.com/community-council/"], "seats": 5},
    "2285": {"nation": "Minnesota Chippewa Tribe", "pages": ["https://mnchippewatribe.org/governance/tribal-executive-committee/"], "seats": 12},
    "3680": {"nation": "Shakopee Mdewakanton", "pages": ["https://shakopeedakota.org/government/how-we-operate/"], "seats": 3},
    "0080": {"nation": "Seneca Nation (Allegany)", "pages": _SENECA, "seats": 17},
    "0540": {"nation": "Seneca Nation (Cattaraugus)", "pages": _SENECA, "seats": 17},
    "2535": {"nation": "Seneca Nation (Oil Springs)", "pages": _SENECA, "seats": 17},
    "3320": {"nation": "Saint Regis Mohawk", "pages": ["https://www.srmt-nsn.gov/tribal-council"], "seats": 6},
    "4445": {"nation": "Upper Sioux", "pages": ["https://www.uppersiouxcommunity-nsn.gov/page/board-of-trustees"], "seats": 5},
    "4595": {"nation": "White Earth", "pages": ["https://www.whiteearth.com/rbc/chairman",
                                               "https://www.whiteearth.com/rbc/secretary-treasurer",
                                               "https://www.whiteearth.com/rbc/district-i",
                                               "https://www.whiteearth.com/rbc/district-ii",
                                               "https://www.whiteearth.com/rbc/district-iii"], "seats": 5},
    # New York (read 2026-10-10). The Seneca Nation holds three reservations,
    # each its own AIANNH code, so the one council is read once (the fetch is
    # cached by URL) and carried under all three.
    "2980": {"nation": "Prairie Band Potawatomi",
             "pages": ["https://www.pbpindiantribe.com/tribal-council"], "seats": 7},
    # Iowa (read 2026-10-10). The Winnebago Tribe of Nebraska holds a sliver
    # of its reservation in Iowa. Its page was changed on 2026-10-07, after the
    # swearing-in of that month's election, so it names the new council.
    "4625": {"nation": "Winnebago", "pages": ["https://winnebagotribe.com/tribal-council/"], "seats": 9},
    "2890": {"nation": "Pokagon", "pages": ["https://www.pokagonband-nsn.gov/government/tribal-council/"], "seats": 11},
    "3085": {"nation": "Red Cliff", "pages": ["https://www.redcliff-nsn.gov/government/tribal_government/index.php"], "seats": 9},
    "3305": {"nation": "St. Croix", "pages": ["https://stcroixojibwe-nsn.gov/tribal-council/"], "seats": 5},
    "3635": {"nation": "Sault Ste. Marie", "pages": ["https://www.saulttribe.com/government/board-of-directors/29-government/board-of-directors/109-board-members-and-reports"], "seats": 13},
    "3885": {"nation": "Sokaogon", "pages": [WI_DOA_LIST], "seats": 6, "stateList": "wi"},
    "4015": {"nation": "Stockbridge-Munsee", "pages": ["https://mohican-nsn.gov/tribal-council/"], "seats": 7},
    # South Carolina. The Bureau lists www.catawbaindian.net, which reset the
    # connection on every read here (2026-10-12); the nation's own site is
    # catawba.com, whose robots.txt is a 404 (allow all), read with this
    # scraper's client the same day.
    "0525": {"nation": "Catawba", "pages": ["https://catawba.com/executive-committee"], "seats": 5},
    # Mississippi Band of Choctaw Indians: seated in Choctaw, Mississippi; its
    # off-reservation trust land near Henning is the one tribal land in
    # Tennessee. robots.txt (www.choctaw.org, read 2026-10-15 with this
    # scraper's client) is "User-Agent: * / Disallow:", which allows every path.
    "2300": {"nation": "Mississippi Band of Choctaw Indians",
             "pages": ["https://www.choctaw.org/about-us/tribal-government/"], "seats": 18},
    # Louisiana (read 2026-10-20, each robots.txt with this scraper's client).
    # www.chitimacha.gov's allows the council page and states a Crawl-delay of
    # 10 s, which the pacer honours. www.jenachoctaw.org is a Google Sites page
    # whose robots.txt is a 404 (allow all). The Bureau lists www.tunica.org
    # for the Tunica-Biloxi, which answered 404 over http and a certificate
    # for another name over https; the tribe's own site is
    # www.tunicabiloxi.org, whose footer gives the tribe's Marksville office
    # and an @tunica.org address, and whose robots.txt allows every path (its
    # Crawl-delay line stands before any User-agent line, so it binds no
    # client). That page says a new website is coming, so a changed page
    # fails this parser and the council last read is carried.
    "0635": {"nation": "Chitimacha",
             "pages": ["https://www.chitimacha.gov/tribal-government/tribal-council"], "seats": 5},
    "1690": {"nation": "Jena Band of Choctaw",
             "pages": ["https://www.jenachoctaw.org/about-jbci/tribal-leaders"], "seats": 5},
    "4315": {"nation": "Tunica-Biloxi",
             "pages": ["https://www.tunicabiloxi.org/tribal-info/tribal-council/"], "seats": 7},
    # Virginia (read 2026-10-30, each robots.txt with this scraper's client;
    # both allow these paths). The Pamunkey Indian Tribe's page says its
    # government is "one Chief and seven council members", the Assistant
    # Chief being selected by the council from among them, and names the
    # Chief, the Assistant Chief and six more. The Mattaponi Tribe's page says
    # its council is "seven members and the chiefs", and names the Chief, the
    # Assistant Chief and seven council members. The Mattaponi are recognized
    # by Virginia and not by the United States, which
    # data/tribal-government-join.json records.
    "9260": {"nation": "Pamunkey",
             "pages": ["https://www.pamunkey.org/tribal-government"], "seats": 8},
    "9230": {"nation": "Mattaponi",
             "pages": ["https://www.mattaponi.gov/mattaponi-tribal-council"], "seats": 9},
    # The Rappahannock Tribe's own site names no council (read 2026-10-30:
    # its front page and every page its sitemap lists; its staff directory is
    # behind the tribe's member sign-in, which stays shut). The Secretary of
    # the Commonwealth's list of state-recognized tribes names its Chief and
    # its Assistant Chief and no council member; that page's robots.txt (299
    # bytes, read 2026-10-30 with this scraper's client) has no rule matching
    # it. Every other nation here is carried only with its whole council, so
    # these two names are carried on Adam's ruling of 2026-10-30 ("name the
    # tribe leaders"), and the card says that only the two are named. The
    # list's other lines for the tribe (its administrator, its finance officer
    # and its consultation contacts) are staff, not officers, and are not read.
    "3075": {"nation": "Rappahannock", "pages": [VA_SOC_LIST], "seats": 2,
             "stateList": "va"},
    # Texas (read 2026-11-12, each robots.txt with this scraper's client; all
    # three allow every path). The Alabama-Coushatta Tribe's page says the
    # tribe "is governed by an elected Tribal Council" of seven, "advised by
    # our Chiefs"; the two chiefs are not council members and are not carried.
    # The council's telephone on that page is one number for the whole
    # council, so it rides no member. The Kickapoo Traditional Tribe of
    # Texas's page lists each of its five council members twice. The Bureau
    # lists no website for the Ysleta del Sur Pueblo; the pueblo's own site
    # says its council is the Governor, the Lieutenant Governor, the Alguacil
    # and four council members, elected each year, and the Cacique and the War
    # Captain, appointed for life, and names all nine in its "2026 Tribal
    # Council" caption.
    "0050": {"nation": "Alabama-Coushatta",
             "pages": ["https://www.alabama-coushatta.com/government/"], "seats": 7},
    "1775": {"nation": "Kickapoo Traditional Tribe of Texas",
             "pages": ["https://kickapootexas.org/tribal-council/"], "seats": 5},
    "4755": {"nation": "Ysleta del Sur Pueblo",
             "pages": ["https://www.ysletadelsurpueblo.org/government/tribal-council"],
             "seats": 9},
    # Florida (read 2026-11-12). The Bureau lists www.seminoletribe.com for the
    # Seminole Tribe of Florida, which failed TLS here; the tribe's own site is
    # www.semtribe.com, which serves an HTML page at /robots.txt (no rules,
    # so every path is allowed). Its "Today's Government" page says the
    # council is "a Chairman, a Vice-Chairman and Council Representatives from
    # each reservation", and the council page names five. The tribe holds
    # eight pieces of land, each its own AIANNH code, so the one council is
    # read once (the fetch is cached by URL) and carried under all eight, as
    # the Seneca Nation's is. The Miccosukee Tribe's site and the Poarch Band's
    # cannot be read here; build_tribal_areas.py's ROSTER_BLOCKED says why.
    **{code: {"nation": "Seminole Tribe of Florida (%s)" % where,
              "pages": ["https://www.semtribe.com/government/tribal-council"], "seats": 5}
       for code, where in (("0225", "Big Cypress"), ("0360", "Brighton"),
                           ("0690", "Coconut Creek"), ("1260", "Fort Pierce"),
                           ("1475", "Hollywood"), ("1555", "Immokalee"),
                           ("3665", "Seminole Trust Land"), ("4130", "Tampa"))},
    # Washington, Arizona, Nevada and California (read 2026-11-13, each
    # robots.txt with this scraper's client; every one allows the page read).
    # Each nation is carried only where its own page names the whole council;
    # the nations that are not, and why, are in build_tribal_areas.py's
    # ROSTER_BLOCKED. A nation whose land lies in two or three of these states
    # (the Colorado River Indian Tribes, Fort Mojave, Quechan, the Navajo
    # Nation, Zuni, Duck Valley, the Goshute, Timbisha, Umatilla) is read once
    # and carried for every state its land is drawn in.
    # Washington. The Umatilla's board of trustees is also Oregon's.
    "0575": {"nation": "Chehalis",
             "pages": ["https://www.chehalistribe.org/business-committee/"], "seats": 5},
    "0760": {"nation": "Colville",
             "pages": ["https://www.colvilletribes.com/get-to-know-your-council"], "seats": 14},
    "0820": {"nation": "Cowlitz",
             "pages": ["https://www.cowlitz.org/council-members"], "seats": 22},
    "2040": {"nation": "Lower Elwha Klallam",
             "pages": ["https://www.elwha.org/departments/tribal-government/"], "seats": 5},
    "2070": {"nation": "Lummi",
             "pages": ["https://www.lummi-nsn.gov/node/Website.php?PageID=763"], "seats": 11},
    "2085": {"nation": "Makah",
             "pages": ["https://makah.com/makah-tribal-info/governance/"], "seats": 5},
    "2375": {"nation": "Muckleshoot",
             "pages": ["https://www.muckleshoot.nsn.us/tribal-council"], "seats": 9},
    "2460": {"nation": "Nisqually",
             "pages": ["https://www.nisqually-nsn.gov/Nisqually-Tribal-Council"], "seats": 7},
    "2475": {"nation": "Nooksack", "pages": ["https://nooksacktribe.org/council/"], "seats": 8},
    "2910": {"nation": "Port Gamble S'Klallam",
             "pages": ["https://pgst.nsn.us/tribal-council/"], "seats": 6},
    "2925": {"nation": "Suquamish",
             "pages": ["https://suquamish.nsn.us/home/government/"], "seats": 7},
    "3030": {"nation": "Quileute",
             "pages": ["https://quileutetribe.com/government/tribal-council/"], "seats": 5},
    "3040": {"nation": "Quinault",
             "pages": ["https://www.quinaultindiannation.com/255/Tribal-Council"], "seats": 11},
    "3780": {"nation": "Shoalwater Bay",
             "pages": ["https://www.shoalwaterbay-nsn.gov/tribal-government/general-council/"], "seats": 5},
    "3825": {"nation": "Skokomish",
             "pages": ["https://skokomish.org/skokomish-tribal-council/"], "seats": 8},
    "3860": {"nation": "Snoqualmie",
             "pages": ["https://snoqualmietribe.us/snoqualmie-tribal-council/"], "seats": 10},
    "4000": {"nation": "Stillaguamish",
             "pages": ["https://www.stillaguamish.com/departmentprogramservice/tribal-government/"], "seats": 6},
    "4290": {"nation": "Tulalip",
             "pages": ["https://www.tulaliptribes-nsn.gov/Government/BoardOfDirectors"], "seats": 7},
    "4405": {"nation": "Umatilla",
             "pages": ["https://ctuir.org/our-government/board-of-trustees/bot-members/"], "seats": 9},
    "4690": {"nation": "Yakama",
             "pages": ["https://yakama.com/about/tribal-council/"], "seats": 14},
    # Arizona. The Hualapai Tribe's site answers over http only. The Navajo
    # Nation Council's own site is the nation's legislative branch (the Bureau
    # lists the executive's www.navajo-nsn.gov, which reset every connection
    # here); the Zuni Pueblo's council is also New Mexico's.
    "0695": {"nation": "Cocopah",
             "pages": ["https://www.cocopah.com/government.html"], "seats": 5},
    "0735": {"nation": "Colorado River Indian Tribes",
             "pages": ["https://crit-nsn.gov/crit_contents/government/"], "seats": 9},
    "1235": {"nation": "Fort Mojave",
             "pages": ["https://www.fortmojaveindiantribe.com/tribal-council/"], "seats": 6},
    "1280": {"nation": "Quechan",
             "pages": ["https://quechantribe.com/government.html"], "seats": 7},
    "1310": {"nation": "Gila River",
             "pages": ["https://www.gilariver.org/index.php/government/misc/council-members"], "seats": 17},
    "1545": {"nation": "Hualapai",
             "pages": ["http://www.hualapai-nsn.gov/government/tribal_council/index.php"], "seats": 9},
    "2430": {"nation": "Navajo",
             "pages": ["https://www.navajonationcouncil.org/council/"], "seats": 24},
    "2680": {"nation": "Pascua Yaqui",
             "pages": ["https://www.pascuayaqui-nsn.gov/council-administration"], "seats": 11},
    "3340": {"nation": "Salt River Pima-Maricopa",
             "pages": ["https://srpmic-nsn.gov/government/council/"], "seats": 9},
    "3355": {"nation": "San Carlos Apache",
             "pages": ["https://www.scat-nsn.gov/san-carlos-apache-tribe-tribal-council/"], "seats": 11},
    "4200": {"nation": "Tohono O'odham",
             "pages": ["https://tolc-nsn.org/representatives-and-committees/"], "seats": 22},
    "4708": {"nation": "Yavapai-Apache",
             "pages": ["https://yavapai-apache.org/tribal_council/"], "seats": 9},
    "4785": {"nation": "Zuni", "pages": ["https://ashiwi.org/tribal-leadership/"], "seats": 8},
    # Two councils whose page names all but one seat, carried on Adam's ruling
    # of 2026-11-13 with a card line saying which seat is not named. Ak-Chin's
    # page says five members and names four; Hopi's says 22 village
    # representatives and names 21, under the five officers it lists first.
    "2130": {"nation": "Ak-Chin",
             "pages": ["http://www.ak-chin.nsn.us/community-council/"], "seats": 4,
             "partial": "The page says the council has five members and names four, "
                        "so one council member's seat is not named here."},
    "1505": {"nation": "Hopi",
             "pages": ["https://www.hopi-nsn.gov/tribal-government/"], "seats": 26,
             "partial": "The page lists five officers and says the council has 22 "
                        "village representatives, of whom it names 21, so one "
                        "representative is not named here."},
    # Nevada. Goshute's and Moapa's older domains have lapsed (one now a
    # finance blog, the other a forms company's page); each nation's current
    # site is the one read. Walker River's council is on its government page,
    # Las Vegas Paiute's on its front page.
    # The Yerington Paiute Tribe's two pieces of land, Campbell Ranch (0440)
    # and the Yerington Colony (4725), and the Fallon Paiute-Shoshone Tribe's
    # two, the colony (1070) and the reservation (1075), each carry the one
    # council, read from the one page.
    "0440": {"nation": "Yerington Paiute",
             "pages": ["https://ypt-nsn.gov/our-government/"], "seats": 7},
    "4725": {"nation": "Yerington Paiute",
             "pages": ["https://ypt-nsn.gov/our-government/"], "seats": 7},
    "0965": {"nation": "Shoshone-Paiute (Duck Valley)",
             "pages": ["https://shopaitribes.org/business-council/"], "seats": 7},
    "1070": {"nation": "Fallon Paiute-Shoshone",
             "pages": ["https://www.fpst.org/166/Fallon-Business-Council"], "seats": 7},
    "1075": {"nation": "Fallon Paiute-Shoshone",
             "pages": ["https://www.fpst.org/166/Fallon-Business-Council"], "seats": 7},
    "1340": {"nation": "Confederated Tribes of the Goshute",
             "pages": ["https://ctgr.us/home/tribal-council/"], "seats": 5},
    "1915": {"nation": "Las Vegas Paiute", "pages": ["https://www.lvpaiute.gov/"], "seats": 7},
    "2315": {"nation": "Moapa Band of Paiutes",
             "pages": ["https://www.moapabandofpaiutes.com/tribal-administration"], "seats": 6},
    "4180": {"nation": "Timbisha Shoshone",
             "pages": ["https://timbisha.com/newsite/government-info/"], "seats": 5},
    "4515": {"nation": "Walker River Paiute",
             "pages": ["https://www.wrpt.org/tribal-government/"], "seats": 7},
    # Carried on Adam's ruling of 2026-11-13: Duckwater's page lists its vice
    # chairperson's and council secretary's seats as vacant, and the Washoe
    # Tribe's names one of the two Off-Reservation representatives its members
    # elect. The card says which seats those are.
    "0975": {"nation": "Duckwater Shoshone",
             "pages": ["https://duckwatertribe.org/tribal-council/"], "seats": 3,
             "partial": "The page lists the Vice Chairperson's and Council "
                        "Secretary's seats as vacant."},
    # The Washoe Tribe's site draws each page in the browser from its own
    # content service, so the council is read from that service's answer for
    # the page (the address the page itself asks), and the card links the page
    # a visitor sees. Its five pieces of land in Nevada and California, the
    # Carson Colony (0510), Dresslerville (0940), Stewart (3980), Washoe Ranches
    # (4560) and Woodfords (4665), each carry the one council.
    **{code: {"nation": "Washoe",
              "pages": ["https://washoetribe.us/api/v2/pages/163/?format=json"],
              "link": "https://washoetribe.us/departmentlandingpage/163-Page-tribal-council",
              "json": True, "seats": 10,
              "partial": "The page says the tribe's members elect two Off-Reservation "
                         "representatives and names one, so the other is not named here."}
       for code in ("0510", "0940", "3980", "4560", "4665")},
    # California. Where the Bureau lists no website, or one that has lapsed or
    # names no council, the nation's current site was found by a web search
    # and is the one read: Big Pine, Jamul, Picayune (Chukchansi), Table
    # Mountain, Redwood Valley, Sherwood Valley, Mesa Grande, Cahuilla and
    # Kletsel Dehe. Cahuilla's and Picayune's addresses are the ones their
    # older links redirect to.
    "0120": {"nation": "United Auburn",
             "pages": ["https://www.auburnrancheria.com/about-us/tribal-council/"], "seats": 5},
    "0125": {"nation": "Augustine",
             "pages": ["https://tribe.augustinetribe-nsn.gov/tribal-council/"], "seats": 2},
    "0155": {"nation": "Barona", "pages": ["https://www.barona-nsn.gov/government"], "seats": 6},
    "0185": {"nation": "Benton Paiute",
             "pages": ["https://www.bentonpaiutereservation.org/council.htm"], "seats": 5},
    "0250": {"nation": "Big Pine Paiute",
             "pages": ["https://bigpinepaiute.org/about-the-tribe/"], "seats": 5},
    "0265": {"nation": "Big Sandy",
             "pages": ["https://www.bigsandyrancheria.com/governance-administration-1"], "seats": 5},
    "0275": {"nation": "Big Valley",
             "pages": ["https://www.bvrancheria.com/tribal-council"], "seats": 4},
    "0290": {"nation": "Bishop Paiute",
             "pages": ["https://bishoppaiute.net/about-us/"], "seats": 5},
    "0325": {"nation": "Blue Lake",
             "pages": ["https://www.bluelakerancheria-nsn.gov/about/Tribal-government/"], "seats": 5},
    "0435": {"nation": "Cahuilla",
             "pages": ["https://cahuilla-nsn.gov/tribal-government/tribal-council/"], "seats": 5},
    # The Viejas Band's own reservation; the Capitan Grande Reservation
    # (0495), which it holds jointly with the Barona Band, carries neither
    # band's council (build_tribal_areas.py's ROSTER_BLOCKED says why).
    "4500": {"nation": "Viejas",
             "pages": ["https://viejasbandofkumeyaay.org/modern-government/viejas-government-officers/"], "seats": 7},
    "0780": {"nation": "Kletsel Dehe Wintun",
             "pages": ["https://www.kletseldehe.org/governance/"], "seats": 5},
    "0955": {"nation": "Dry Creek",
             "pages": ["https://drycreekrancheria.com/board-of-directors/"], "seats": 5},
    "1010": {"nation": "Elk Valley",
             "pages": ["https://elk-valley.com/the-rancheria/tribal-council/"], "seats": 9},
    "1055": {"nation": "Estom Yumeka Maidu (Enterprise)",
             "pages": ["https://enterpriserancheria.org/our-tribe/"], "seats": 7},
    "1380": {"nation": "Greenville", "pages": ["https://www.grth.org/about"], "seats": 5},
    "1490": {"nation": "Hoopa Valley",
             "pages": ["https://www.hoopa-nsn.gov/hoopa-valley-tribal-council/"], "seats": 8},
    "1515": {"nation": "Hopland",
             "pages": ["https://www.hbpi.gov/getpage.php?name=Tribal_Council&sub=Governance"], "seats": 7},
    "1670": {"nation": "Jamul", "pages": ["https://jiv-nsn.gov/tribal-government/"], "seats": 7},
    "1750": {"nation": "Karuk", "pages": ["https://www.karuk.us/council"], "seats": 9},
    "1895": {"nation": "La Posta",
             "pages": ["https://www.lptribe.net/government-officers/"], "seats": 5},
    "2190": {"nation": "Mesa Grande",
             "pages": ["https://www.mesagrandeband-nsn.gov/tribal-government/"], "seats": 5},
    "2255": {"nation": "Middletown",
             "pages": ["https://middletownrancheria-nsn.gov/tribal-council/"], "seats": 5},
    "2360": {"nation": "Morongo",
             "pages": ["https://morongonation.org/tribal-council/"], "seats": 7},
    "2495": {"nation": "North Fork",
             "pages": ["https://northforkrancheria-nsn.gov/sovereign-nation/tribal-council/"], "seats": 5},
    "2635": {"nation": "Pala",
             "pages": ["https://www.palatribe.com/government/executive-committee/"], "seats": 6},
    # Carried on Adam's ruling of 2026-11-13: the page lists the Tribal
    # Secretary's seat as vacant, and the card says so.
    "2685": {"nation": "Paskenta",
             "pages": ["https://paskenta-nsn.gov/about-the-nation/our-government/"], "seats": 4,
             "partial": "The page lists the Tribal Secretary's seat as vacant."},
    "2715": {"nation": "Pauma", "pages": ["https://www.paumatribe.com/government/"], "seats": 5},
    "2775": {"nation": "Picayune Rancheria of the Chukchansi",
             "pages": ["https://chukchansi-nsn.gov/council/"], "seats": 7},
    "3095": {"nation": "Redding",
             "pages": ["https://www.reddingrancheria-nsn.gov/tribal-council/"], "seats": 7},
    "3115": {"nation": "Redwood Valley",
             "pages": ["https://www.rvrpomo.net/about-us-1"], "seats": 7},
    "3145": {"nation": "Pulikla Tribe of Yurok People",
             "pages": ["https://puliklatribe.gov/who-we-are/tribal-council/"], "seats": 5},
    "3220": {"nation": "Bear River Band",
             "pages": ["https://www.bearriverrancheria.org/about-1"], "seats": 7},
    "3250": {"nation": "Round Valley",
             "pages": ["https://www.rvit.org/government/tribal-council"], "seats": 7},
    "3520": {"nation": "Tachi Yokut (Santa Rosa Rancheria)",
             "pages": ["https://www.tachi-yokut-nsn.gov/council"], "seats": 6},
    "3540": {"nation": "Santa Ynez Chumash",
             "pages": ["https://chumash.gov/government"], "seats": 5},
    "3735": {"nation": "Sherwood Valley",
             "pages": ["https://www.sherwoodvalleybandofpomo.com/tribal-government.html"], "seats": 7},
    "3750": {"nation": "Shingle Springs",
             "pages": ["https://shinglespringsrancheria.com/tribal-council/"], "seats": 8},
    "3855": {"nation": "Tolowa Dee-ni'",
             "pages": ["https://www.tolowa.gov/209/LHETLH-XAT-NE-TRIBAL-COUNCIL"], "seats": 7},
    "3870": {"nation": "Soboba", "pages": ["https://www.soboba-nsn.gov/about-us"], "seats": 5},
    "4060": {"nation": "Susanville",
             "pages": ["https://sir-nsn.gov/boards-committees.html"], "seats": 7},
    "4090": {"nation": "Sycuan",
             "pages": ["https://sycuantribe.com/tribal-government/"], "seats": 7},
    "4110": {"nation": "Table Mountain",
             "pages": ["https://tablemountainrancheria.com/tribal-council/"], "seats": 5},
    "4255": {"nation": "Torres Martinez",
             "pages": ["https://torresmartinez.org/tribal_council/"], "seats": 6},
    "4275": {"nation": "Trinidad (Cher-Ae Heights)",
             "pages": ["https://trinidad-rancheria.org/tribal-council/"], "seats": 5},
    "4760": {"nation": "Yurok",
             "pages": ["https://www.yuroktribe.org/tribal-council-members"], "seats": 9},
}

_BLOCK = (r"(?:p|div|h[1-6]|li|ul|ol|td|th|tr|table|section|article|header|footer|"
          r"nav|figcaption|figure|dt|dd|dl|main|aside|option|select|form|button|"
          r"label|title|hr)")


def _cf_decode(hexstr):
    """One address Cloudflare's e-mail protection hides: the first byte is
    the key and every later byte is a character XORed with it."""
    key = int(hexstr[:2], 16)
    return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))


def _cf_emails(body):
    """Each element Cloudflare's e-mail protection fills with "[email
    protected]" is replaced by the address it carries in data-cfemail, which
    the page's own script shows every visitor. Only that element is
    replaced: a link whose href alone is protected keeps its own text,
    because Upper Sioux's footer wraps its telephone line in one. Decoded
    since 2026-10-17 under the operator's rule that contact details an
    official government page prints are published (the fleet already does
    this for Will, Warren, Tennessee, Wisconsin and Aitkin pages); measured
    that day, no nation's parsed council changes except Prairie Band's."""
    return re.sub(r'(?is)<(a|span)\b[^>]*\bdata-cfemail="([0-9a-fA-F]+)"[^>]*>.*?</\1>',
                  lambda m: _cf_decode(m.group(2)), body)


def lines_of(body, br=" \n"):
    """Page text, one line per block element; inline tags join. A <br> ends a
    line by default, because Red Cliff separates its whole council with them,
    and a page that breaks one NAME across a <br> inside a heading (Lac Vieux
    Desert) says so with `"br": " "` in NATIONS."""
    t = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", body)
    t = _cf_emails(t)
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = re.sub(r"(?i)<br\b[^>]*>", br, t)
    t = re.sub(r"(?i)</?%s\b[^>]*>" % _BLOCK, "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("\xa0", " ").replace("‑", "-")
    out = []
    for raw in t.split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            out.append(line)
    return out


def _after(lines, marker, nth=0):
    """The lines after the nth line equal to `marker` (exact, case-sensitive)."""
    hits = [i for i, l in enumerate(lines) if l == marker]
    if len(hits) <= nth:
        raise ValueError("marker %r not on the page" % marker)
    return lines[hits[nth] + 1:]


def _m(name, role, **extra):
    out = {"name": name.strip(), "role": role.strip()}
    for k, v in extra.items():
        if v:
            # phonesExtra is a list of further numbers, each kept as printed
            out[k] = [x.strip() for x in v] if isinstance(v, list) else v.strip()
    return out


def _email(line):
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", line or "")
    return m.group(0) if m else None


def _phone(line):
    m = re.search(r"\(?\d{3}\)?[-. ]\d{3}-\d{4}", line or "")
    return m.group(0) if m else None


def _sentence_roles(text, roles):
    """'Role A Name, Role B Name, and Role C Name' -> [(role, name)], roles
    matched longest first so 'Vice President' is never read as 'President'."""
    pat = "|".join(re.escape(r) for r in sorted(roles, key=len, reverse=True))
    text = text.strip()
    # a closing full stop ends the sentence, except where it ends a suffix
    if text.endswith(".") and not re.search(r"\b(?:Jr|Sr)\.$", text):
        text = text[:-1]
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
    out = []
    for part in parts:
        m = re.match(r"(%s)\s+(.+)$" % pat, part.strip())
        if not m:
            raise ValueError("cannot read a role in %r" % part)
        out.append((m.group(1), m.group(2)))
    return out


# ---- one parser per nation --------------------------------------------------

def p_bad_river(pages):
    # "Tribal Council" is also a menu entry; the council block opens on its
    # first office heading
    i0 = pages[0].index("TRIBAL CHAIRMAN")
    ls = pages[0][i0:]
    out = []
    for i in range(0, 14, 2):
        role, name = ls[i].title(), ls[i + 1]
        out.append(_m(name, role))
    for m in out:
        if m["name"] == "Michelle Conners":
            m["note"] = "the same page also spells it Connors"
    return out


def p_bay_mills(pages):
    line = [l for l in pages[0] if l.startswith("Serving on the council currently are ")][0]
    text = line[len("Serving on the council currently are "):]
    out = []
    for role, name in _sentence_roles(text, ["Vice President", "President", "Secretary",
                                             "Council Person", "Treasurer"]):
        # the page runs "AndyLeBlanc" together; the space is the page's own
        # missing one, restored only between a lowercase and a capital
        name = re.sub(r"^Andy(?=LeBlanc$)", "Andy ", name)
        out.append(_m(name, role))
    return out


def p_fond_du_lac(pages):
    ls = [l for l in _after(pages[0], "Fond du Lac Tribal Council Members")
          if l != "Email Link" and not l.startswith("(click")]
    out = []
    for line in ls[:5]:
        name, rest = line.split(" - ", 1)
        role = rest.split(" - ")[0]
        district = None
        m = re.search(r"District (I{1,3})", role)
        if m:
            district = "District " + m.group(1)
        role = re.sub(r"\s*&\s*District I{1,3} Representative", "", role)
        role = "District Representative" if role.startswith("District") else role
        out.append(_m(name, role, district=district))
    return out


def p_forest_county(pages):
    line = [l for l in pages[0] if l.startswith("From Left to Right: ")][0]
    text = line[len("From Left to Right: "):]
    return [_m(n, r) for r, n in _sentence_roles(
        text, ["Vice Chairman", "Chairman", "Secretary", "Treasurer", "Council Member"])]


def _role_then_name(ls, roles, count):
    out, i = [], 0
    while len(out) < count:
        if ls[i] in roles:
            out.append(_m(ls[i + 1], ls[i]))
            i += 2
        else:
            i += 1
    return out


def p_grand_traverse(pages):
    # the heading appears in the breadcrumb and again over the list; the list
    # is under the last one
    ls = _after(pages[0], "Tribal Council Members",
                nth=pages[0].count("Tribal Council Members") - 1)
    return _role_then_name(ls, {"Chairwoman", "Chairman", "Vice Chairwoman",
                                "Vice Chairman", "Treasurer", "Secretary", "Councilor"}, 7)


def p_ho_chunk(pages):
    pres = [l for l in pages[0] if l.startswith("Ho-Chunk Nation President: ")][0]
    out = [_m(pres[len("Ho-Chunk Nation President: "):], "President")]
    ls = _after(pages[1], "Legislators")
    district, i = None, 0
    while i < len(ls) and len(out) < 13:
        m = re.match(r"District (\d) Legislators$", ls[i])
        if m:
            district = "District " + m.group(1)
            i += 1
            continue
        if ls[i] in ("Representative", "Vice President"):
            out.append(_m(ls[i + 1], ls[i], district=district, email=_email(ls[i + 2])))
            i += 3
            continue
        i += 1
    return out


def p_nhbp(pages):
    pre = "The current NHBP Tribal Council consists of "
    line = [l for l in pages[0] if l.startswith(pre)][0]
    return [_m(n, r) for r, n in _sentence_roles(
        line[len(pre):], ["Vice Chairperson", "Chairperson", "Secretary", "Treasurer",
                          "Sergeant-at-Arms"])]


def p_saginaw(pages):
    # the heading is in the menu too; the list is under the last one
    ls = _after(pages[0], "Meet The Council", nth=pages[0].count("Meet The Council") - 1)
    out = []
    i = 0
    while len(out) < 12:
        name, label = ls[i], ls[i + 1]
        assert ls[i + 2] == "Read Bio", ls[i:i + 3]
        role = label.split(" / ")[0]
        if role.startswith("District"):
            role = "Council Member"
        # the list prints the office "Chaplin"; the same page's biography of
        # that member calls it "Tribal Chaplain", which is the office's name
        if role == "Chaplin" and "Tribal Chaplain" in " ".join(ls):
            role = "Chaplain"
        out.append(_m(name, role))
        i += 3
    return out


def p_lco(pages):
    i = [k for k, l in enumerate(pages[0]) if re.match(r"Gary .Little Guy. Clause, Chair$", l)][0]
    out = []
    for line in pages[0][i:i + 7]:
        name, role = line.rsplit(", ", 1)
        out.append(_m(name, role))
    return out


def _state_list(pdf_bytes, heading, count):
    """One nation's block of the Wisconsin Department of Administration's list:
    officer lines read "Name, Role", then "Council Members:" and a comma-run of
    names that wraps across lines."""
    # Only the weekly read of the state's PDF needs pymupdf, and
    # update-tribal-councils.yml installs it; --selftest, which the smoke job
    # runs, never reaches this line, so the import is declared optional rather
    # than paid for by every pull request.
    try:
        import pymupdf
    except ImportError:
        raise RuntimeError("reading the state's list needs pymupdf: "
                           "pip install -c scripts/requirements.txt pymupdf")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(p.get_text() for p in doc)
    m = re.search(r"Updated:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if not m:
        raise ValueError("the state list prints no Updated date")
    updated = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    start = [k for k, l in enumerate(lines) if l.startswith(heading)][0]
    out, rest, members = [], [], False
    for line in lines[start + 1:]:
        if line.startswith("Location:"):
            break
        if line == "Council Members:":
            members = True
            continue
        if members:
            rest.append(line)
            continue
        m = re.match(r"(.+?), ((?:Tribal )?(?:Vice[- ])?(?:Chair|President)|Secretary|"
                     r"Treasurer|Council Member I+)$", line)
        if m:
            out.append(_m(m.group(1), m.group(2)))
    if rest:
        for name in re.split(r",\s*", " ".join(rest).strip(" ,")):
            out.append(_m(name, "Council Member"))
    if len(out) != count:
        raise ValueError("the state list gives %d for %r, expected %d: %r"
                         % (len(out), heading, count, out))
    return out, updated


# The two offices the Secretary of the Commonwealth's list gives a tribe's
# leaders. The list writes "Assistant Cheif" for the Rappahannock (read
# 2026-10-30), so both spellings are read and the office is written correctly.
_VA_OFFICES = (("Assistant Chief", r"Assistant Ch(?:ie|ei)f"), ("Chief", r"Chief"))


def _va_state_list(html_bytes, heading, count):
    """One tribe's block of the Secretary of the Commonwealth's list of
    Virginia's state-recognized tribes: the tribe's name on a line of its own,
    then "Chief <name>" and "Assistant Chief <name>", then lines for staff,
    until "Contact information". Only the Chief and the Assistant Chief are
    read. A line such as "Chief Financial Officer <name>" names a staff office
    and is not a chief, so a name that starts with an office word is refused.
    The list prints no date of its own, so it gives none."""
    lines = lines_of(html_bytes.decode("utf-8", "replace"))
    hits = [k for k, l in enumerate(lines) if l == heading]
    if len(hits) != 1:
        raise ValueError("the state list has %d line(s) reading %r, expected 1"
                         % (len(hits), heading))
    out = []
    for line in lines[hits[0] + 1:]:
        if line == "Contact information":
            break
        for role, pat in _VA_OFFICES:
            m = re.match(r"(?:%s) (.+)$" % pat, line)
            if m and not re.match(r"(?i)(financial|executive|operating|officer|"
                                  r"administrator)\b", m.group(1)):
                out.append(_m(m.group(1), role))
                break
    else:
        raise ValueError("the state list's block for %r has no contact line"
                         % heading)
    if [m["role"] for m in out] != ["Chief", "Assistant Chief"][:count]:
        raise ValueError("the state list gives %r for %r, expected the Chief and "
                         "the Assistant Chief" % (out, heading))
    return out, None


# Each state's list of tribal officials that names a nation's leaders where
# the nation publishes no council of its own. `officersOnly` marks a list that
# names a nation's leading officers and no council member, so the card can say
# that only they are named.
STATE_LISTS = {
    "wi": {"publisher": "Wisconsin Department of Administration",
           "list": "list of Wisconsin tribal officials",
           "page": WI_DOA_LIST, "key": "wi-doa.pdf", "parse": _state_list},
    "va": {"publisher": "Secretary of the Commonwealth of Virginia",
           "list": "list of state-recognized tribes",
           "page": VA_SOC_LIST, "key": "va-soc.html", "parse": _va_state_list,
           "officersOnly": True},
}


def p_lvd(pages):
    ls = _after(pages[0], "2024 - 2026")
    out = [_m(ls[k], ls[k + 1]) for k in range(0, 8, 2)]
    rest = _after(pages[0], "TRIBAL COUNCIL MEMBERS")
    assert rest[0].startswith("2024"), rest[0]
    out += [_m(n, "Council Member") for n in rest[1:6]]
    return out


def p_ltbb(pages):
    out = []
    for role in ("Tribal Chairperson", "Vice Chairperson"):
        line = [l for l in pages[0] if l.startswith(role + ": ")][0]
        out.append(_m(line[len(role) + 2:], role))
    ls = _after(pages[1], "Term Expires")
    i = 0
    while len(out) < 11:
        label = ls[i]
        if label.startswith(("Legislative Leader", "Tribal Secretary", "Tribal Treasurer",
                             "Tribal Council")):
            role = label.split(":")[0]
            role = "Council Member" if role == "Tribal Council" else role
            # two office labels carry a link to the statute that defines the
            # office, which lands on a line of its own before the name
            if re.match(r"(?:WOS )?\d{4}-\d{3} ", ls[i + 1]):
                i += 1
            out.append(_m(ls[i + 1], role, phone=_phone(ls[i + 2]), email=_email(ls[i + 3]),
                          termEnds=ls[i + 4] if re.match(r"20\d\d$", ls[i + 4]) else None))
            i += 5
        else:
            i += 1
    return out


def p_gun_lake(pages):
    # each member's line is followed by the district they were elected from
    ls, out = pages[0], []
    for k, line in enumerate(ls):
        m = re.match(r"([A-Z][A-Za-z.' -]+), (Tribal Chairwoman|Tribal Chairman|Vice Chairman|"
                     r"Vice Chairwoman|Secretary|Treasurer|Councilor)$", line)
        if m:
            nxt = ls[k + 1] if k + 1 < len(ls) else ""
            district = nxt if re.match(r"(At-Large|Bradley|Salem) District$", nxt) else None
            if not district:
                raise ValueError("no district under %r" % line)
            out.append(_m(m.group(1), m.group(2).replace("Tribal ", ""), district=district))
    return out


def p_menominee(pages):
    line = [l for l in pages[0] if l.startswith("(left-right) ")][0]
    text = line[len("(left-right) "):]
    out = []
    for part in re.split(r",\s*(?:and\s+)?", text.rstrip(".")):
        m = re.match(r"(.+?)(?: \((.+)\))?$", part.strip())
        role = m.group(2) or "Legislator"
        out.append(_m(m.group(1), role))
    return out


def p_oneida(pages):
    ls = _after(pages[0], "Officers")
    roles = {"Chairperson", "Vice-Chairperson", "Tribal Secretary", "Treasurer", "Council Member"}
    out, i = [], 0
    while len(out) < 9:
        if ls[i] in roles:
            out.append(_m(ls[i + 1], ls[i], phone=_phone(ls[i + 2]), email=_email(ls[i + 3])))
            i += 4
        else:
            i += 1
    return out


def p_pokagon(pages):
    out = []
    for line in _after(pages[0], "Tribal Council Executive Committee Members"):
        if line == "Administrative Staff":
            break
        if line == "Tribal Council Members At Large":
            continue
        name, _, role = line.partition(", ")
        out.append(_m(name, role or "Member At Large"))
    return out


def p_winnebago(pages):
    # Each member is a four-line block under the heading: name, office, the
    # tribe's main number with the member's extension, and an e-mail address.
    # The list ends at the mission statement.
    ls = _after(pages[0], "Winnebago Tribal Council")
    ls = ls[:ls.index("MISSION STATEMENT")]
    if len(ls) % 4:
        raise ValueError("Winnebago's council blocks are not four lines each")
    out = []
    for i in range(0, len(ls), 4):
        name, role, line, email = ls[i:i + 4]
        x = re.search(r"Ext\. (\d+)$", line)
        if not x or not _phone(line):
            raise ValueError("Winnebago block %r carries no phone and extension" % name)
        out.append(_m(name, role, phone="%s ext. %s" % (_phone(line), x.group(1)),
                      email=_email(email)))
    return out


def p_prairie_band(pages):
    # The page lists the council twice: a short "name / office" run under each
    # heading, then the same people again with their term, contact lines and
    # assistant. The second listing is the one read, because each person's
    # term and telephone sit in their own block there; the block is opened by
    # its "Term:" line.
    #
    # The e-mail is the "Email:" line inside the member's own block, which
    # the site hides behind Cloudflare's e-mail protection and lines_of
    # decodes; the "Assistant Email:" line beside it is the assistant's and
    # is not carried. The telephone is the "P)" line in the same block; the
    # fax ("F)") is dropped.
    ls = _after(pages[0], "Meet Our Council Officers")
    out, seen = [], set()
    office = re.compile(r"(?:Tribal Council Chairperson|Vice Chair Person|Treasurer|"
                        r"Secretary|Council Member - \d)$")
    for k in range(len(ls) - 2):
        if not office.match(ls[k + 1]):
            continue
        # the person's own block: every line up to the next office line. The
        # short run at the top lists name and office only, so a block read
        # there holds no "Term:" line and is skipped; Wade Pahmahmie's block
        # carries his clan and an earlier office between his office and term.
        block = []
        for line in ls[k + 2:]:
            if office.match(line):
                break
            block.append(line)
        term = [l for l in block[:3] if l.startswith("Term:")]
        if not term:
            continue
        name, label = ls[k], ls[k + 1]
        if name in seen:
            raise ValueError("%r has two blocks with a term" % name)
        end = re.search(r"(20\d\d)\s*$", term[0])
        phones = [_phone(l) for l in block if l.startswith("P)")]
        phone = phones[0] if phones else None
        emails = [_email(l) for l in block if l.startswith("Email:")]
        if len(emails) > 1:
            raise ValueError("%r has %d Email lines" % (ls[k], len(emails)))
        seat = None
        m = re.match(r"Council Member - (\d)$", label)
        if m:
            role, seat = "Council Member", "seat " + m.group(1)
        elif label == "Tribal Council Chairperson":
            role = "Chairperson"
        elif label == "Vice Chair Person":
            role = "Vice Chairperson"
        else:
            role = label
        out.append(_m(name, role, phone=phone, email=emails[0] if emails else None,
                      note=seat, termEnds=end.group(1) if end else None))
        seen.add(name)
    return out


def p_bois_forte(pages):
    # each member: name, office, then "Office:" / "Cell:" / "Fax:" lines and an
    # e-mail. The first office line is carried in `phone`, as it always was.
    # The member's own number is carried too, in `phonesExtra`, under Adam's
    # ruling of 2026-10-17 ("if the official government source uses personal
    # phone numbers, we publish those"): a "Cell:" line as "cell <number>",
    # and the one line the page labels with the member's own name instead (the
    # Vice-Chairperson's, read 2026-10-17) as the bare number, because the page
    # gives no word for what kind of line it is and none is invented. A fax
    # line is never read, and a number the page prints more than once (a
    # government office's main line) is never carried as anyone's own.
    ls = _after(pages[0], "Bois Forte Tribal Council")
    printed = {}
    for l in ls:
        for n in re.findall(r"\(?\d{3}\)?[-. ]\d{3}-\d{4}", l):
            key = re.sub(r"\D", "", n)
            printed[key] = printed.get(key, 0) + 1
    office = re.compile(r"(Chairperson|Secretary Treasurer|District (I+) Representative)")
    out = []
    for k, line in enumerate(ls):
        if len(out) == 5:
            break
        m = office.match(ls[k + 1]) if k + 1 < len(ls) else None
        if not m or line.startswith(("Office", "Cell", "Fax")):
            continue
        label = ls[k + 1]
        block = []
        for l in ls[k + 2:k + 9]:
            if office.match(l) or "@" in l:
                if "@" in l:
                    block.append(l)
                break
            block.append(l)
        phone = None
        for l in block:
            pm = re.search(r"Office: (\(?\d{3}\)?[-. ]\d{3}-\d{4}(?: x \d+)?)", l)
            if pm:
                phone = pm.group(1)
                break
        own = []
        for l in block:
            cm = re.match(r"(Cell|%s): (\(?\d{3}\)?[-. ]\d{3}-\d{4})$" % re.escape(line), l)
            if cm and printed.get(re.sub(r"\D", "", cm.group(2))) == 1:
                own.append(("cell " if cm.group(1) == "Cell" else "") + cm.group(2))
        district = None
        dm = re.search(r"District (I+) Representative", label)
        if dm:
            district = "District " + dm.group(1)
        if "Vice-Chairperson" in label:
            role = "Vice-Chairperson"
        elif dm:
            role = "District Representative"
        else:
            role = label
        out.append(_m(line, role, district=district, phone=phone, phonesExtra=own,
                      email=_email(block[-1]) if block else None))
    return out


def p_leech_lake(pages):
    # "Faron Jackson, Sr," -- the page closes several names with a comma; it is
    # punctuation between the name and the office below it, and is dropped.
    ls = _after(pages[0], "Leech Lake Government")
    out = []
    for k in range(1, 11, 2):
        name = ls[k].rstrip(",").strip()
        label = ls[k + 1]
        m = re.match(r"District (I+) Representative$", label)
        out.append(_m(name, "District Representative" if m else label,
                      district=("District " + m.group(1)) if m else None))
    return out


def p_lower_sioux(pages):
    ls = _after(pages[0], "Community Council Members")
    out, k = [], 0
    while k < len(ls) and ls[k] != "Full Council Group Email":
        name, role = ls[k], ls[k + 1]
        k += 2
        phone = email = None
        while k < len(ls) and (_phone(ls[k]) or "@" in ls[k]):
            if "@" in ls[k]:
                email = _email(ls[k])
            else:
                phone = _phone(ls[k])
            k += 1
        out.append(_m(name, role, phone=phone, email=email))
    return out


def p_mct(pages):
    # The Tribal Executive Committee is the six bands' chairs and
    # secretary-treasurers; the office line under each name is their TEC
    # office and the line under that is the band office they hold, which is
    # carried as the row's note.
    ls = _after(pages[0], "TEC Members")
    out = []
    for k in range(0, 36, 3):
        out.append(_m(ls[k], ls[k + 1], note=ls[k + 2]))
    return out


def p_shakopee(pages):
    # each member appears twice: on the list and again in a pop-up whose
    # biography is still template text, which is not carried
    ls = _after(pages[0], "Business Council Members")
    out, seen = [], set()
    for k in range(len(ls) - 1):
        if ls[k].startswith("Gaming Enterprise"):
            break
        if re.match(r"(Chairman|Chairwoman|Vice-Chair\w*|Secretary/Treasurer)$", ls[k + 1]) \
                and ls[k] not in seen and ls[k] != "Business Council Member":
            out.append(_m(ls[k], ls[k + 1]))
            seen.add(ls[k])
    return out


def p_upper_sioux(pages):
    ls = _after(pages[0], "Mission")
    roles = {"Tribal Chairman", "Vice Chair", "Tribal Treasurer", "Tribal Secretary",
             "Member at Large"}
    out = []
    for k, line in enumerate(ls):
        if line in roles:
            out.append(_m(ls[k + 1], line, phone=_phone(ls[k + 2])))
    return out


def p_white_earth(pages):
    # one page per office; each reads "Back", then the name, then the office
    out = []
    for ls in pages:
        k = ls.index("Back")
        name, label = ls[k + 1], ls[k + 2]
        m = re.match(r"District (I+)$", label)
        out.append(_m(name, "District Representative" if m else label,
                      district=label if m else None))
    return out


def p_red_cliff(pages):
    ls = pages[0]
    start = ls.index([l for l in ls if re.match(r"20\d\d-\d\d Tribal Council$", l)][0])
    out = []
    for line in ls[start + 1:start + 10]:
        name, role = line.split(" - ", 1)
        if role.startswith("At Large Member, serving the remainder"):
            role = "At Large Member"
        out.append(_m(name, role))
    # the e-mail below each name, where the page prints one
    for k, line in enumerate(ls):
        for m in out:
            if line == m["name"] and k + 3 < len(ls) and ls[k + 1].startswith("Term Expires"):
                e = _email(ls[k + 2])
                if e:
                    m["email"] = e
                m["termEnds"] = ls[k + 1][len("Term Expires "):]
    return out


def p_st_croix(pages):
    ls = _after(pages[0], "Tribal Council Members")
    out = []
    i = 0
    while len(out) < 5:
        if ls[i].endswith(", Tribal Council"):
            out.append(_m(ls[i - 1], ls[i][:-len(", Tribal Council")]))
        i += 1
    return out


def p_sault(pages):
    out = []
    ls = pages[0]
    for k, line in enumerate(ls):
        m = re.match(r"(.+?), (Chairman|Vice-Chairman|Secretary|Treasurer|Director)$", line)
        if not m:
            continue
        unit = ls[k + 1] if re.match(r"Unit [IV]+$", ls[k + 1]) else None
        contact = ls[k + 2] if unit else ls[k + 1]
        out.append(_m(m.group(1), m.group(2), district=unit, phone=_phone(contact)))
    return out


def p_stockbridge(pages):
    ls = _after(pages[0], "Current Tribal Council")
    return [_m(ls[k], ls[k + 1]) for k in range(0, 14, 2)]


def p_catawba(pages):
    # The five elected officers, each a name then an office. Two "Council
    # Member" entries further down sit inside HTML comments, which lines_of
    # drops, so they are not read. The page's prose still says the committee
    # elected in 2019 serves until July 2023; the list itself was revised
    # after that (the 2022 seal stands in for one member's photo), and the
    # list, not the prose, is what is carried.
    ls = _after(pages[0], "The Catawba Nation Executive Committee")
    out = []
    for k in range(0, 10, 2):
        role = ls[k + 1].replace("Commitee", "Committee")  # the page's typo
        out.append(_m(ls[k], role))
    if ls[10] != "Executive Committee Duties":
        raise ValueError("Catawba: the list runs past five offices: %r" % ls[10])
    return out


def p_choctaw(pages):
    # The Tribal Chief, then the 17-member Tribal Council. The chief's card is
    # the one line "Tribal Chief <name>" (the earlier chiefs' cards read
    # "Chief <name>"). Each council card is a name, then a title naming the
    # member's community ("Bogue Chitto Councilwoman", or an office first:
    # "Tribal Vice-Chief and Bogue Chitto Councilman"), then the page
    # builder's placeholder "Your Title Goes Here". The committee lists further
    # down date from a July 2025 resolution and are not read.
    ls = pages[0]
    chief = [m.group(1) for m in (re.match(r"Tribal Chief (\S.*)$", l) for l in ls) if m]
    if len(chief) != 1:
        raise ValueError("Choctaw: expected one Tribal Chief card, found %r" % chief)
    out = [_m(chief[0], "Tribal Chief")]
    body = _after(ls, "Tribal Council Meetings")
    end = body.index("Tribal Council Committee Chairperson and Committee Members")
    body = body[:end]
    for i in range(len(body) - 2):
        if body[i + 2] != "Your Title Goes Here":
            continue
        m = re.match(r"^(?:(.+?) and )?(.+?) (Council(?:man|woman))$", body[i + 1])
        if not m:
            raise ValueError("Choctaw: title not understood: %r" % body[i + 1])
        office = (m.group(1) or "").replace("Tribal Vice-Chief", "Vice-Chief")
        out.append(_m(body[i], office or m.group(3), district=m.group(2)))
    return out


def p_seneca(pages):
    # the President from the executive page, then the councilors, who are
    # elected from the nation's two territories and listed under each
    ls = _after(pages[0], "President", nth=pages[0].count("President") - 1)
    out = [_m(ls[0], "President", note="from " + ls[1])]
    district = None
    for line in _after(pages[1], "RFP/RFQ"):
        m = re.match(r"(Allegany|Cattaraugus) Councilors$", line)
        if m:
            district = m.group(1)
            continue
        if line == "About":
            break
        if district:
            out.append(_m(line, "Councilor", district=district))
    return out


def p_srmt(pages):
    # the council is listed three times on the page; the last, in the body
    # text, carries each chief's full name
    ls = pages[0]
    k = [i for i, l in enumerate(ls) if l.startswith("The Tribal Council is comprised of")][0]
    out = []
    for line in ls[k + 1:k + 7]:
        m = re.match(r"(Sub-Chief|Chief) (.+)$", line)
        if not m:
            raise ValueError("not a chief: %r" % line)
        out.append(_m(m.group(2), m.group(1)))
    return out


def p_chitimacha(pages):
    # The council is the lines under the last "Tribal Council" heading, each
    # "Name - Office" except the secretary-treasurer's, which the page writes
    # with a comma ("<name>, Secretary/Treasurer"). The footer line, the
    # tribe's own office on Chitimacha Loop, ends the list.
    ls = _after(pages[0], "Tribal Council", nth=pages[0].count("Tribal Council") - 1)
    out = []
    for line in ls:
        if "Chitimacha Loop" in line:
            break
        name, role = line.split(" - ", 1) if " - " in line else line.rsplit(", ", 1)
        out.append(_m(name, role))
    return out


def p_jena(pages):
    # Each leader is an office line ("Tribal Chief", "Councilwoman",
    # "Councilman"), the name, then a biography; "Stay connected" opens the
    # footer. Every office line is read, so a sixth leader fails the seat
    # count rather than being dropped.
    ls = _after(pages[0], "Tribal Leaders", nth=pages[0].count("Tribal Leaders") - 1)
    ls = ls[:ls.index("Stay connected")]
    return [_m(ls[i + 1], line) for i, line in enumerate(ls[:-1])
            if line in ("Tribal Chief", "Councilwoman", "Councilman")]


def p_tunica_biloxi(pages):
    # Under "Our Tribal Council", each member is a name, the office, then a
    # biography; the tribe's footer address ends the list. Two biographies
    # open with "<name>, Sr." where the heading gives the name alone, and the
    # heading ships with the other form stated, as Bad River's two spellings do.
    ls = _after(pages[0], "Our Tribal Council")
    ls = ls[:ls.index("Tunica Biloxi Tribe of Louisiana")]
    offices = ("Chairman", "Vice Chairman", "Secretary-Treasurer", "Council Member")
    out = []
    for i, line in enumerate(ls[:-1]):
        if ls[i + 1] not in offices:
            continue
        bio = ls[i + 2] if i + 2 < len(ls) else ""
        m = re.match(re.escape(line) + r"(, (?:Sr|Jr)\.)", bio)
        out.append(_m(line, ls[i + 1],
                      note=("the same page also writes " + line + m.group(1)) if m else None))
    return out


def p_pamunkey(pages):
    # "Chief <name>" and "Assistant Chief <name>" head their biographies, and
    # the six other council members are the lines under "Tribal Council" up to
    # "Tribal Administration", which opens the staff list.
    # A heading is the office and a name of two to four words with no full
    # stop at its end; the biographies under them are whole sentences.
    ls = pages[0]
    out = []
    for role in ("Chief", "Assistant Chief"):
        heads = [l for l in ls
                 if re.match(r"%s (?:[A-Z][^ ]* ?){2,4}$" % role, l) and not l.endswith(".")]
        if len(heads) != 1:
            raise ValueError("Pamunkey: expected one %r heading, found %r" % (role, heads))
        out.append(_m(heads[0][len(role) + 1:], role))
    ls = _after(ls, "Tribal Council")
    ls = ls[:ls.index("Tribal Administration")]
    out.extend(_m(name, "Council Member") for name in ls)
    return out


def p_mattaponi(pages):
    # The list headed "Mattaponi Tribal Council": "Chief:", the name,
    # "Assistant Chief:", the name, then "Council Members:" and one name a
    # line, ending at the site's footer ("All materials used on this
    # website..."). THE SAME PAGE'S LEADERSHIP PANEL, above the list, names
    # another assistant chief under a placeholder biography; the list agrees
    # with the nation's own front page and with the Secretary of the
    # Commonwealth's list of state-recognized tribes (both read 2026-10-30),
    # so the list ships and the other name is stated on the row, as Bad
    # River's two spellings are.
    ls = pages[0]
    panel = {}
    for i, line in enumerate(ls[:-1]):
        if ls[i + 1] in ("CHIEF", "ASSISTANT CHIEF"):
            panel[ls[i + 1].title()] = line
    ls = _after(ls, "Mattaponi Tribal Council")
    if ls[0] != "Chief:" or ls[2] != "Assistant Chief:" or ls[4] != "Council Members:":
        raise ValueError("Mattaponi: the list is not Chief, Assistant Chief, Council "
                         "Members: %r" % ls[:5])
    out = []
    for name, role in ((ls[1], "Chief"), (ls[3], "Assistant Chief")):
        other = panel.get(role)
        out.append(_m(name, role, note=("the same page's leadership panel names %s as %s"
                                         % (other, role.lower())) if other and other != name else None))
    for line in ls[5:]:
        if line.startswith("All materials used on this website"):
            break
        out.append(_m(line, "Council Member"))
    return out


def p_alabama_coushatta(pages):
    # The two chiefs come first, each a name line and then "Principal Chief"
    # or "second Chief"; the council follows as a name line and then an office
    # line that begins "Tribal", and "Constitution and By Laws" ends it. Every
    # pair after the chiefs must carry a "Tribal" office, so a page that adds
    # a line the parser does not know fails rather than shipping it as a name.
    ls = pages[0]
    i = ls.index("second Chief") + 1
    end = ls.index("Constitution and By Laws", i)
    block = ls[i:end]
    if len(block) % 2:
        raise ValueError("Alabama-Coushatta: the council block is not name/office pairs: %r"
                         % block)
    out = []
    for name, role in zip(block[0::2], block[1::2]):
        if not role.startswith("Tribal "):
            raise ValueError("Alabama-Coushatta: %r is not a council office (for %r)"
                             % (role, name))
        out.append(_m(name, role))
    return out


def p_kickapoo_tx(pages):
    # Under the last "TRIBAL COUNCIL" heading each member is a name line and
    # an office line, and the page prints every pair twice; "Fitness Center"
    # opens the footer's links. A pair is kept once, in page order.
    ls = _after(pages[0], "TRIBAL COUNCIL", nth=pages[0].count("TRIBAL COUNCIL") - 1)
    ls = ls[:ls.index("Fitness Center")]
    offices = ("Chairman", "Vice Chairman", "Secretary", "Treasurer", "Member")
    out, seen = [], set()
    for i in range(0, len(ls) - 1):
        if ls[i + 1] in offices and ls[i] not in offices:
            if (ls[i], ls[i + 1]) not in seen:
                seen.add((ls[i], ls[i + 1]))
                out.append(_m(ls[i], ls[i + 1]))
    return out


def p_ysleta(pages):
    # The caption under the "<year> Tribal Council" photograph names the
    # council left to right as "<office> <name>", one sentence over several
    # lines, ending at the "Documents" list. Only one such caption may be on
    # the page, so a page keeping last year's council beside this year's fails.
    ls = pages[0]
    heads = [i for i, l in enumerate(ls) if re.match(r"\d{4} Tribal Council$", l)]
    if len(heads) != 1:
        raise ValueError("Ysleta del Sur: expected one '<year> Tribal Council' caption, "
                         "found %r" % [ls[i] for i in heads])
    block = ls[heads[0] + 1:]
    block = block[:block.index("Documents")]
    if block and block[0].rstrip(":").lower() == "left to right":
        block = block[1:]
    text = " ".join(block).strip().rstrip(",")
    return [_m(n, r) for r, n in _sentence_roles(
        text, ["Councilman", "Councilwoman", "War Captain", "Lt. Governor", "Governor",
               "Cacique", "Alguacil"])]


def p_seminole_fl(pages):
    # The council is the name/office pairs after the "Tribal Council" heading
    # whose next-but-one line is "Chairman", ending at "Toggle navigation",
    # which opens the page's own menu. A representative's office names the
    # reservation that elects them ("Hollywood Councilman"), which rides the
    # member as their district, so the card lists it beside the name.
    ls = pages[0]
    starts = [i for i, l in enumerate(ls[:-2]) if l == "Tribal Council" and ls[i + 2] == "Chairman"]
    if len(starts) != 1:
        raise ValueError("Seminole: expected one council block, found %d" % len(starts))
    block = ls[starts[0] + 1:]
    block = block[:block.index("Toggle navigation")]
    if len(block) % 2:
        raise ValueError("Seminole: the council block is not name/office pairs: %r" % block)
    out = []
    for name, role in zip(block[0::2], block[1::2]):
        m = re.match(r"(.+?) (Council(?:man|woman))$", role)
        if m:
            out.append(_m(name, m.group(2), district=m.group(1)))
        else:
            out.append(_m(name, role))
    return out


# ---- Washington ---------------------------------------------------------------
# Read 2026-11-13. Contact details ship only where the page prints them in that
# member's own entry and nowhere else; a telephone printed beside every member
# (Nooksack's, Quileute's) is the council office's and rides nobody.

def _name_role_pairs(ls, roles, count):
    """name line, then its office line, `count` times, starting at ls[0]."""
    out = []
    for i in range(0, 2 * count, 2):
        name, role = ls[i], ls[i + 1]
        if not re.search(roles, role):
            raise ValueError("expected an office after %r, found %r" % (name, role))
        out.append(_m(name, role))
    return out


def _comma_role_lines(ls, count):
    """'Name, Office' lines; the office is after the last comma."""
    out = []
    for line in ls[:count]:
        name, role = line.rsplit(", ", 1)
        out.append(_m(name, role))
    return out


def p_chehalis(pages):
    # each member is a name, an office heading and a paragraph about them; on
    # 2026-11-13 two paragraphs give a different office from the heading above
    # them and one spells the name differently, so the heading ships and the
    # page's other wording is stated on the row rather than chosen between
    ls = pages[0]
    i0 = ls.index("Chairman") - 1
    out, i = [], i0
    while len(out) < 5:
        name, role = ls[i], ls[i + 1]
        out.append(_m(name, role))
        i += 2
        if i < len(ls) and ls[i].startswith(("Thomas ", "Farley ", "Cheryle ", "Don ")) \
                and " serves as " in ls[i]:
            bio = ls[i]
            said = re.search(r" serves as (?:Tribal )?(.+?) on the Chehalis", bio)
            if said and said.group(1) != role:
                out[-1]["note"] = ("the same page also describes this member as serving as %s"
                                   % said.group(1))
            spelled = bio.split(",", 1)[0]
            if spelled.split()[-1] != name.split()[-1]:
                extra = "the same page also spells the name %s" % spelled
                out[-1]["note"] = ("; ".join([out[-1]["note"], extra])
                                   if out[-1].get("note") else extra)
            i += 1
    return out


_COLVILLE_OFFICES = {"Chairwoman", "Chairman", "Vice-Chairwoman", "Vice-Chairman", "Secretary"}


def p_colville(pages):
    # name, then the council office if any, then any committee the member
    # chairs, then the member's district, then a "learn more" link (whose text
    # sometimes runs onto a line of its own)
    ls = _after(pages[0], "-Colville Business Council")
    out, i = [], 0
    while len(out) < 14:
        name = ls[i]
        i += 1
        labels = []
        while not ls[i].endswith("District Representative"):
            labels.append(ls[i])
            i += 1
        district = ls[i][:-len(" Representative")]
        i += 1
        if not ls[i].startswith("Click to Learn More About"):
            raise ValueError("Colville: no link after %r" % name)
        if ls[i] == "Click to Learn More About":
            i += 1
        i += 1
        office = [l for l in labels if l in _COLVILLE_OFFICES]
        committee = [l for l in labels if l not in _COLVILLE_OFFICES]
        out.append(_m(name, office[0] if office else "Council Member", district=district,
                      note="; ".join(committee)))
    return out


def p_cowlitz(pages):
    ls = _after(pages[0], "Current Tribal Council Members")
    out, i = [], 0
    while i + 2 < len(ls) and ls[i + 1].startswith("Term ends "):
        out.append(_m(ls[i], ls[i + 2], termEnds=ls[i + 1][len("Term ends "):]))
        i += 3
    return out


def p_lower_elwha(pages):
    return _comma_role_lines(_after(pages[0], "Our Council"), 5)


def p_makah(pages):
    return _comma_role_lines(_after(pages[0], "Makah Tribal Council Members:"), 5)


def p_muckleshoot(pages):
    # the contact box near the top names the chair once; the council is the
    # list that follows the introduction
    i0 = [k for k, l in enumerate(pages[0])
          if l == "Chair" and k > 0 and pages[0][k - 1] == "Donny Stevenson"][0] - 1
    return _name_role_pairs(pages[0][i0:], r"Chair|Secretary|Treasurer|Councilmember", 9)


def p_nisqually(pages):
    ls = _after(pages[0], "The Nisqually Tribal Council")
    return [_m(*l.rsplit(" - ", 1)) for l in ls[:7]]


def p_nooksack(pages):
    # each member is name, office, the council office's telephone (the same
    # number for all eight) and an e-mail link
    ls = _after(pages[0], "Council Members", nth=1)
    out = []
    for i in range(0, 32, 4):
        if ls[i + 3] != "Email":
            raise ValueError("Nooksack: unexpected row at %r" % ls[i])
        out.append(_m(ls[i], ls[i + 1]))
    return out


def p_pgst(pages):
    i0 = pages[0].index("Policy Manual") + 1
    return _name_role_pairs(pages[0][i0:], r"Chair|Council Person", 6)


def p_quileute(pages):
    # name, office, the council office's shared telephone, the office's mailbox
    ls = _after(pages[0], "Quileute Tribal Council")[1:]
    out = []
    for i in range(0, 20, 4):
        out.append(_m(ls[i], ls[i + 1], email=_email(ls[i + 3])))
    return out


def p_quinault(pages):
    ls = _after(pages[0], "Members")
    out = []
    for i in range(0, 33, 3):
        if ls[i + 2] != "More Information":
            raise ValueError("Quinault: unexpected row at %r" % ls[i])
        out.append(_m(ls[i], ls[i + 1]))
    return out


def p_shoalwater(pages):
    # a table of name, office and the member's own telephone; the
    # member-at-large's row gives an e-mail address instead
    ls = _after(pages[0], "Phone Number")
    out = []
    for i in range(0, 15, 3):
        contact = ls[i + 2]
        out.append(_m(ls[i], ls[i + 1], phone=_phone(contact), email=_email(contact)))
    return out


def p_skokomish(pages):
    # a table of office, name, the member's own telephone and e-mail; one
    # member's row has no telephone, and the table ends with the council's
    # executive secretary, who is staff
    ls = _after(pages[0], "E-Mail")
    out, i = [], 0
    while ls[i] != "Executive Secretary":
        role, name = ls[i], ls[i + 1]
        i += 2
        phone = email = None
        if _phone(ls[i]):
            phone = ls[i]
            i += 1
        if _email(ls[i]):
            email = ls[i]
            i += 1
        out.append(_m(name, role, phone=phone, email=email))
    return out


def p_snoqualmie(pages):
    out = []
    for line in pages[0]:
        m = re.match(r"(Chairperson|Vice Chair|Tribal Secretary|Treasurer): (.+)$", line)
        if m:
            out.append(_m(m.group(2), m.group(1)))
        elif line.startswith("Council: "):
            out += [_m(n, "Council") for n in line[len("Council: "):].split(", ")]
    return out


def p_stillaguamish(pages):
    return _comma_role_lines(_after(pages[0], "Tribal Council/Board of Directors:"), 6)


_SUQ = r"Council Member|Vice Chair|Chairman|Secretary|Treasurer"


def p_suquamish(pages):
    # the council is named in the caption of its photograph; a suffix follows
    # its own comma ("Mills, Jr"), so the caption is split on offices, not commas
    pre = "Suquamish Tribal Council, from left to right, is "
    text = [l for l in pages[0] if l.startswith(pre)][0][len(pre):].rstrip(".")
    found = re.findall(r"(%s) (.+?)(?=, (?:and )?(?:%s) |$)" % (_SUQ, _SUQ), text)
    return [_m(n, r) for r, n in found]


def p_tulalip(pages):
    ls = _after(pages[0], "Board of Directors", nth=3)[1:]
    return _name_role_pairs(ls, r"Chair|Secretary|Treasurer|Board Member", 7)


def p_lummi(pages):
    i0 = [k for k, l in enumerate(pages[0]) if l.startswith("Lummi Indian Business Council (LIBC) is")][0]
    return _name_role_pairs(pages[0][i0 + 1:], r"Chair|Secretary|Treasurer|Council Member", 11)


def p_yakama(pages):
    # name, the member's Yakama name, then for an officer the office; every
    # entry ends "VIEW BIO"
    ls = _after(pages[0], "Executive Members")
    out, i, role = [], 0, None
    while len(out) < 14:
        if ls[i] == "Members":
            i += 1
            continue
        name, own = ls[i], ls[i + 1]
        if ls[i + 2] == "VIEW BIO":
            role, i = "Council Member", i + 3
        else:
            role, i = ls[i + 2], i + 4
            if ls[i - 1] != "VIEW BIO":
                raise ValueError("Yakama: unexpected row at %r" % name)
        out.append(_m(name, role, note="Yakama name " + own))
    return out


def p_umatilla(pages):
    # the heading is in the menu and the breadcrumb too; the list is under the last
    ls = _after(pages[0], "Board of Trustees", nth=pages[0].count("Board of Trustees") - 1)
    return _name_role_pairs(ls, r"Chair|Treasurer|Secretary|Trustee", 9)


# ---- Arizona ------------------------------------------------------------------
# Read 2026-11-13, each robots.txt with this scraper's client. A telephone
# printed beside every member of a council (Gila River's main line) is the
# council office's and rides nobody.

def _drop_stop(name):
    """A full stop closing a line that is only a name ends the caption, except
    where it ends a suffix or an initial."""
    if name.endswith(".") and not re.search(r"(?:\bJr|\bSr|\b[A-Z])\.$", name):
        return name[:-1]
    return name


def p_cocopah(pages):
    # "Chairwoman:" / name, "Vice-Chairman:" / name, "Council members:" / three
    ls = _after(pages[0], "Current Tribal Council 2026-2028:")
    out = [_m(ls[1], ls[0].rstrip(":")), _m(ls[3], ls[2].rstrip(":"))]
    if ls[4] != "Council members:":
        raise ValueError("Cocopah: expected the council members heading, found %r" % ls[4])
    out += [_m(n, "Council Member") for n in ls[5:8]]
    return out


def p_gila_river(pages):
    # "District N" headings, each over its members: an optional "(Photo Coming
    # Soon)", the name, an e-mail line, a telephone line and an optional fax.
    # The council's main line, (520) 562-9720, is printed beside most members
    # and is the office's; a different number is that member's own.
    ls = _after(pages[0], "Council Members", nth=1)
    out, district, i = [], None, 0
    while len(out) < 17:
        line = ls[i]
        if re.match(r"^District \d$", line):
            district = line
        elif line == "(Photo Coming Soon)" or line.startswith(("Fax", "Phone", "E-Mail",
                                                               "E-mail", "Email")):
            pass
        else:
            email = _email(ls[i + 1])
            if not email:
                raise ValueError("Gila River: no e-mail after %r" % line)
            phone = None
            if ls[i + 2].startswith("Phone"):
                digits = re.sub(r"\D", "", ls[i + 2])
                if digits != "5205629720":
                    phone = ls[i + 2].split(":", 1)[1].strip()
            out.append(_m(_drop_stop(line), "Council Member", district=district,
                          email=email, phone=phone))
        i += 1
    return out


def p_hualapai(pages):
    # "Name, Office, 2024-2028" then the member's e-mail
    ls = _after(pages[0], "Tribal Council", nth=pages[0].count("Tribal Council") - 1)
    ls = [l for l in ls if not l.startswith("If you would like")]
    out = []
    for k in range(0, 18, 2):
        name, role, term = ls[k].rsplit(", ", 2)
        if not re.match(r"^\d{4}-\d{4}$", term):
            raise ValueError("Hualapai: no term on %r" % ls[k])
        out.append(_m(name, role, termEnds=term.split("-")[1], email=_email(ls[k + 1])))
    return out


def p_pascua_yaqui(pages):
    # name, OFFICE in capitals, e-mail, "Office <n>" and an optional "Cell <n>"
    i0 = pages[0].index("CHAIRMAN") - 1
    ls = pages[0][i0:]
    out = []
    for k in range(0, 44, 4):
        name, role, email, tel = ls[k:k + 4]
        m = re.match(r"^Office (\S+)(?: Cell (\S+))?$", tel)
        if not m or not _email(email):
            raise ValueError("Pascua Yaqui: unexpected rows after %r" % name)
        out.append(_m(name, role.title(), email=_email(email), phone=m.group(1),
                      phonesExtra=["cell " + m.group(2)] if m.group(2) else None))
    return out


def p_salt_river(pages):
    # name, then the office or the member's district, then a "Read Bio" link
    ls = _after(pages[0], "Council Leadership")
    out = []
    for k in range(0, 27, 3):
        name, what, link = ls[k:k + 3]
        if not link.startswith("Read Bio"):
            raise ValueError("Salt River: expected a bio link after %r" % name)
        if what in ("President", "Vice President"):
            out.append(_m(name, what))
        else:
            out.append(_m(name, "Council Member", district=what))
    return out


def p_tohono_oodham(pages):
    # the Legislative Council's table: "Surname, Given", e-mail, telephone,
    # district, the month a term expires, then committee lines; the council's
    # own Chairperson and Vice Chairperson are the committee line "TOLC, ...".
    # The table writes each name surname first, so it is turned round at its
    # one comma; no word of it changes.
    ls = _after(pages[0], "Committee Title")
    out, k = [], 0
    while len(out) < 22:
        name, email, phone, district, term = ls[k:k + 5]
        if not _email(email) or not re.match(r"^\d{1,2}/\d{4}$", term):
            raise ValueError("Tohono O'odham: unexpected rows after %r" % name)
        surname, given = name.split(", ")
        k += 5
        role = "Representative"
        while (k < len(ls) and ls[k] != "Tohono O’odham Nation"
               and not (k + 1 < len(ls) and _email(ls[k + 1]))):
            if ls[k] == "TOLC, Chairperson":
                role = "Chairperson"
            elif ls[k] == "TOLC, Vice Chairperson":
                role = "Vice Chairperson"
            k += 1
        out.append(_m(given + " " + surname, role, district=district, email=_email(email),
                      phone=phone, termEnds=term))
    return out


def p_yavapai_apache(pages):
    ls = _after(pages[0], "Tribal Council")
    return _name_role_pairs(ls, r"(?i)^(chairman|vice chairman|council member)$", 9)


_FORT_MOJAVE_OFFICES = ("Vice Chairman", "Chairman", "Secretary", "Council Member")


def p_fort_mojave(pages):
    # each member's name runs straight into the office ("Tim WilliamsChairman");
    # the office is cut off the end, longest first
    i0 = [i for i, l in enumerate(pages[0]) if l.startswith("Tribal Counciladmin")][0]
    out = []
    for line in pages[0][i0 + 1:i0 + 7]:
        for off in _FORT_MOJAVE_OFFICES:
            if line.endswith(off):
                out.append(_m(line[:-len(off)], off))
                break
        else:
            raise ValueError("Fort Mojave: no office on %r" % line)
    return out


def p_quechan(pages):
    # the President and Vice President under their own headings, then a photo
    # caption naming the whole council "(l-r)". The caption puts "Mr." before
    # each man's name: a courtesy title is not part of the name and is not
    # carried. "Dr." and "Ed. D." are the page's own and ship, as Dr. ships for
    # other nations.
    ls = pages[0]
    i = ls.index("Quechan Tribal President")
    out = [_m(ls[i + 1], "President")]
    if ls[i + 2] != "Quechan Tribal Vice President":
        raise ValueError("Quechan: no vice president heading")
    out.append(_m(ls[i + 3], "Vice President"))
    cap = " ".join(ls[i + 4:i + 7])
    if not cap.startswith("Quechan Tribal Council (l-r): "):
        raise ValueError("Quechan: no council caption")
    cap = cap[len("Quechan Tribal Council (l-r): "):]
    for part in re.split(r",\s+(?=(?:Mr\.|Dr\.|Tribal President|Vice-President) )", cap):
        part = _drop_stop(part.strip())
        if part.startswith(("Tribal President ", "Vice-President ")):
            continue
        out.append(_m(re.sub(r"^Mr\. ", "", part), "Council Member"))
    return out


def p_san_carlos(pages):
    # photo captions, most "<District> Councilwoman – Name"; on 2026-11-13 one
    # caption is a name alone and one an office over a name, and the last is a
    # name alone. A member the block names with no office is carried as a
    # council member with that stated on the row, never given a district the
    # block does not print.
    ls = _after(pages[0], "San Carlos Apache Tribe Tribal Council")
    out = []
    for line in ls[:2]:
        role, name = line.split(" – ", 1)
        out.append(_m(name, role))
    for line in ls[2:8]:
        m = re.match(r"^(.+ District) (Council(?:wo)?man)(?: –)? (.+)$", line)
        if not m:
            raise ValueError("San Carlos: cannot read %r" % line)
        out.append(_m(m.group(3), m.group(2), district=m.group(1)))
    if ls[8:12] != ["Ned Anderson Jr", "Bylas District Councilman", "Jonathan Kitcheyan",
                    "Dr. John Bush"]:
        raise ValueError("San Carlos: the last captions changed: %r" % ls[8:12])
    out.append(_m("Ned Anderson Jr", "Council Member",
                  note="the council block names this member without an office or district"))
    out.append(_m("Jonathan Kitcheyan", "Councilman", district="Bylas District"))
    out.append(_m("Dr. John Bush", "Council Member",
                  note=("the council block names this member without an office; the "
                        "page's menu lists him under the Peridot District office")))
    return out


def p_zuni(pages):
    ls = _after(pages[0], "Pueblo of Zuni Governor and Council")[1:]
    return _name_role_pairs(ls, r"^(Governor|Lieutenant Governor|Head Councilman|"
                                r"Councilman|Councilwoman)$", 8)


def p_crit(pages):
    # "Office:" / name for the four officers, then "Councilmembers:" over the
    # rest; the page breaks one member's name over two lines ("Bill" /
    # "Beeson"), which are rejoined
    ls = _after(pages[0], "The current CRIT Tribal Council is:")
    out = []
    for k in range(0, 8, 2):
        out.append(_m(ls[k + 1], ls[k].rstrip(":")))
    if ls[8] != "Councilmembers:":
        raise ValueError("CRIT: expected the council members heading, found %r" % ls[8])
    rest, names = ls[9:], []
    while rest and len(names) < 5:
        if len(rest[0].split()) == 1 and len(rest) > 1 and len(rest[1].split()) == 1:
            names.append(rest[0] + " " + rest[1])
            rest = rest[2:]
        else:
            names.append(rest[0])
            rest = rest[1:]
    out += [_m(n, "Council Member") for n in names]
    return out


def p_navajo(pages):
    # the Navajo Nation Council's own site (the nation's legislative branch;
    # the Bureau lists the executive's www.navajo-nsn.gov, which reset every
    # connection on 2026-11-13). Each delegate: name, "<name> is representing:",
    # the chapters in brackets, a committee line, the delegate's e-mail, then
    # clan and hometown lines, which are not carried. The site's own menu links
    # "Speaker" to Crystalyne Curley's biography, and she is the one delegate
    # with no standing committee, so her row carries that office.
    ls = _after(pages[0], "Click below to expand")
    out = []
    for i, line in enumerate(ls):
        if not line.endswith(" is representing:"):
            continue
        name, chapters, committee, email = ls[i - 1], ls[i + 1], ls[i + 2], ls[i + 3]
        if not (chapters.startswith("(") and chapters.endswith(")")
                and committee.startswith("Committee:") and _email(email)):
            raise ValueError("Navajo: unexpected rows for %r" % name)
        role = "Speaker" if name == "Crystalyne Curley" else "Council Delegate"
        out.append(_m(name, role, district=chapters[1:-1], email=_email(email)))
    return out




# ---- Nevada -------------------------------------------------------------------
# Read 2026-11-13 with this scraper's client, each robots.txt first. Goshute's
# and Moapa's older domains have lapsed (one now a finance blog, the other a
# forms company's page); each nation's current site is the one read.

def p_fallon(pages):
    # name / office pairs from the Chairwoman down, with an "Email <name>"
    # link line under some names
    ls = pages[0][pages[0].index("Tribal Chairwoman") - 1:]
    ls = [l for l in ls if not l.startswith("Email ")]
    return _name_role_pairs(ls, r"^(Tribal Chairwoman|Tribal Chairman|Vice Chairman|"
                                r"Vice Chairwoman|Tribal Secretary|Treasurer|"
                                r"Council Member)$", 7)


def p_duck_valley(pages):
    # office, name, "Term: April 2029", "Email: x", "Phone: <main line> ext. N";
    # the extension is the member's own, so the line rides that member
    ls = _after(pages[0], "Business Council")
    out = []
    for k in range(0, 35, 5):
        role, name, term, email, phone = ls[k:k + 5]
        m = re.match(r"^Term: \w+ (\d{4})$", term)
        x = re.match(r"^Phone: (.+ ext\. \d+)$", phone)
        if not (m and x and _email(email)):
            raise ValueError("Duck Valley: unexpected rows after %r" % name)
        out.append(_m(_drop_stop(name), role, termEnds=m.group(1), email=_email(email),
                      phone=x.group(1)))
    if ls[35] != "Chief Executive Officer":
        raise ValueError("Duck Valley: the council block runs past seven, found %r" % ls[35])
    return out


def p_timbisha(pages):
    # name, office, e-mail, then a sentence about the member, from the
    # Chairperson down
    ls = pages[0]
    i0 = ls.index("Tribal Chairperson") - 1
    out = []
    for k in range(i0, i0 + 20, 4):
        name, role, email = ls[k:k + 3]
        if not _email(email):
            raise ValueError("Timbisha: no e-mail after %r" % name)
        out.append(_m(name, role, email=_email(email)))
    return out


def p_yerington(pages):
    # the Chairman's name over "Tribal Chairman |Yerington Paiute Tribe" and a
    # biography, then name / office pairs
    ls = _after(pages[0], "Meet Our Tribal Council")
    role = ls[1].split("|")[0].strip()
    if role != "Tribal Chairman":
        raise ValueError("Yerington: expected the Chairman first, found %r" % ls[1])
    out = [_m(ls[0], role)]
    i = ls.index("Vice Chairman") - 1
    out += _name_role_pairs(ls[i:], r"^(Vice Chairman|Council Member|Secretary|"
                                    r"Treasurer)$", 6)
    return out


def p_walker_river(pages):
    # name, office, "Email – x"
    ls = _after(pages[0], "Tribal Council")
    out = []
    for k in range(0, 21, 3):
        name, role, email = ls[k:k + 3]
        if not email.startswith("Email") or not _email(email):
            raise ValueError("Walker River: no e-mail after %r" % name)
        out.append(_m(name, role, email=_email(email)))
    return out


def p_las_vegas_paiute(pages):
    # a heading repeating each office, then the name and the office; a
    # "Council Members" heading sits over the five council members
    ls = _after(pages[0], "Executive Leadership")
    ls = ls[:ls.index("Serving Our Community")]
    ls = [l for l in ls if l != "Council Members"]
    out = []
    for k in range(0, len(ls), 3):
        heading, name, role = ls[k:k + 3]
        if heading not in ("Chairman", "Vice Chairman", "Council Member"):
            raise ValueError("Las Vegas Paiute: unexpected heading %r" % heading)
        out.append(_m(name, role))
    return out


def p_goshute(pages):
    # "Name – Office" lines under "Tribal Council Members"
    ls = _after(pages[0], "Tribal Council Members")
    out = []
    for line in ls[:5]:
        name, role = line.split(" – ", 1)
        out.append(_m(name, role))
    return out


def p_moapa(pages):
    # office, name, the tribe's main line (rides nobody), a description; the
    # council's six come before the Tribal Administrator
    ls = _after(pages[0], "Meeting Minutes Request Form")
    out = []
    i = 0
    while ls[i] != "Tribal Administrator":
        if re.match(r"^(Chairman|Vice Chairman|Tribal Secretary|Council Member|"
                    r"Council Treasurer)$", ls[i]):
            out.append(_m(ls[i + 1], ls[i]))
            i += 2
        else:
            i += 1
    return out


# ---- California ---------------------------------------------------------------
# Read 2026-11-13 with this scraper's client, each robots.txt first. Where the
# Bureau lists no website, or one that has lapsed, the nation's current site was
# found by a web search and is the one read. A telephone printed beside every
# member, or the tribe's main line printed alone, is the office's and rides
# nobody; the main line with a member's own extension rides that member.

def _visible(ls):
    """Drop lines that hold only zero-width or icon characters."""
    return [l for l in ls if re.sub(r"[​﻿-\s]", "", l)]


def _dash_role_lines(ls, count, sep=" – "):
    """'Name – Office' lines."""
    out = []
    for line in ls[:count]:
        if sep not in line:
            raise ValueError("expected 'name%soffice', found %r" % (sep, line))
        name, role = line.split(sep, 1)
        out.append(_m(_drop_stop(name.strip()), role))
    return out


def _role_dash_name(ls, count, sep=" – "):
    """'Office – Name' lines."""
    out = []
    for line in ls[:count]:
        if sep not in line:
            raise ValueError("expected 'office%sname', found %r" % (sep, line))
        role, name = line.split(sep, 1)
        out.append(_m(_drop_stop(name.strip()), role))
    return out


def p_augustine(pages):
    # name, office and a "Read More" link for each member of the council
    # block, which on 2026-11-13 names two
    ls = pages[0]
    ls = [l for l in ls[ls.index("Tribal Chairperson") - 1:] if l != "Read More"]
    out = _name_role_pairs(ls, r"^Tribal (Chairperson|Treasurer|Vice Chairperson|Secretary)$", 2)
    if ls[4].startswith("Tribal "):
        raise ValueError("Augustine: the council block runs past two, found %r" % ls[4])
    return out


def p_big_sandy(pages):
    # the Chairperson's name heads the block and her office label comes after
    # the other four pairs
    ls = pages[0]
    s = ls.index("Vice Chairperson") - 2
    if ls[s - 1] != "Tribal Council" or ls[s + 9] != "Chairperson":
        raise ValueError("Big Sandy: the council block has moved")
    out = [_m(ls[s], "Chairperson")]
    out += _name_role_pairs(ls[s + 1:s + 9], r"^(Vice Chairperson|Treasurer|Secretary|"
                                             r"Member-at-Large)$", 4)
    return out


def p_big_valley(pages):
    ls = _visible(pages[0][pages[0].index("Tribal Chairman"):])
    return _role_then_name(ls, {"Tribal Chairman", "Tribal Treasurer", "Tribal Vice-Chairman",
                                "Tribal Secretary"}, 4)


def p_bishop(pages):
    ls = _visible(pages[0])
    ls = ls[ls.index("Chairman") - 1:]
    return _name_role_pairs(ls, r"^(Chairman|Chairwoman|Vice Chairman|Vice Chairwoman|"
                                r"Secretary/Treasurer|Council Member)$", 5)


def p_blue_lake(pages):
    # "Name, Office" lines under "Current Elected Leadership"; "Dr." is the
    # page's own and ships
    return _comma_role_lines(_after(pages[0], "of the Blue Lake Rancheria"), 5)


def p_barona(pages):
    ls = _after(pages[0], "BARONA TRIBAL COUNCIL")
    if ls[12] != "Gaming Commission":
        raise ValueError("Barona: the council block runs past six, found %r" % ls[12])
    return _name_role_pairs(ls, r"^(Chairman|Chairwoman|Vice-Chairman|Vice-Chairwoman|"
                                r"Councilman|Councilwoman)$", 6)


def p_trinidad(pages):
    ls = pages[0][pages[0].index("Chairman") - 1:]
    return _name_role_pairs(ls, r"^(Chairman|Vice Chairman|Secretary / Treasurer|"
                                r"Council Member Seat #\d)$", 5)


_DRY_CREEK_OFFICES = ("Secretary/Treasure", "Member at Large", "Vice-Chair", "Chairman")


def p_dry_creek(pages):
    # each director's name runs straight into the office ("Chris WrightChairman");
    # the office is cut off the end, longest first, and kept as printed
    ls = _after(pages[0], "Board of Directors", nth=2)
    out = []
    for line in ls[:5]:
        for off in sorted(_DRY_CREEK_OFFICES, key=len, reverse=True):
            if line.endswith(off):
                out.append(_m(line[:-len(off)], off))
                break
        else:
            raise ValueError("Dry Creek: no office on %r" % line)
    return out


def p_viejas(pages):
    ls = pages[0]
    ls = [l for l in ls[ls.index("Chairman") - 1:] if l != "Click for Bio"]
    return _name_role_pairs(ls, r"^(Chairman|Vice Chairman|Secretary|Treasurer|Councilman|"
                                r"Councilwoman)$", 7)


def p_elk_valley(pages):
    # four officers, each a name, an office and paragraphs about them, then
    # five "Name, Council Member" lines; the page says the council has nine
    ls = pages[0]
    i, out = ls.index("Chairman") - 1, []
    while len(out) < 4:
        if ls[i + 1] in ("Chairman", "Vice-Chairman", "Treasurer", "Secretary") \
                and len(ls[i].split()) <= 4:
            out.append(_m(ls[i], ls[i + 1]))
            i += 2
        else:
            i += 1
    members = [l for l in ls[i:] if l.endswith(", Council Member")][:5]
    out += _comma_role_lines(members, 5)
    return out


def p_hoopa(pages):
    # the Chairman (with the Administrative Officer's telephone, which is not
    # his, and his office's e-mail), then each district's representative: the
    # name, "<District> District Representative", the main line with the
    # member's extension (some printed with no number) and an e-mail
    ls = _after(pages[0], "Hoopa Valley Tribal Council")
    name, role = ls[0].split(" | ")
    if not ls[1].startswith("Administrative Officer"):
        raise ValueError("Hoopa: unexpected line under the Chairman: %r" % ls[1])
    out = [_m(name, role, email=_email(ls[2]))]
    i = 3
    while len(out) < 8:
        head, dist = ls[i], ls[i + 1]
        m = re.match(r"^(.+ District) Representative$", dist)
        x = re.match(r"^Office Phone: (.+ Ext\. \d+)$", ls[i + 2])
        if not m or not ls[i + 2].startswith("Office Phone:") or not _email(ls[i + 3]):
            raise ValueError("Hoopa: unexpected rows after %r" % head)
        if " | " in head:
            name, role = head.split(" | ")
        else:
            name, role = head, "District Representative"
        out.append(_m(name, role, district=m.group(1), phone=x.group(1) if x else None,
                      email=_email(ls[i + 3])))
        i += 4
        if ls[i].startswith("Click here"):
            i += 1
    return out


def p_hopland(pages):
    # "Name – Office", the member's e-mail, and a telephone line (the main
    # line with the member's extension) under some
    ls = _after(pages[0], "Contact the Tribal Council Office")
    out, i = [], 0
    while len(out) < 7:
        if " – " not in ls[i] or not _email(ls[i + 1]):
            raise ValueError("Hopland: unexpected rows at %r" % ls[i])
        name, role = ls[i].split(" – ", 1)
        email, phone = _email(ls[i + 1]), None
        i += 2
        x = re.match(r"^(707-472-2100) \(ext\. (\d+)\)$", ls[i])
        if x:
            phone = "%s ext. %s" % x.groups()
            i += 1
        out.append(_m(_drop_stop(name), role, email=email, phone=phone))
    return out


def p_karuk(pages):
    # name, office, then the term as "<start>" / "-" / "<end>"; the end ships
    # as printed, including terms the page shows as ending before it was read
    ls = _after(pages[0], "Tribal Council Members", nth=2)
    i0 = ls.index("Chairperson") - 1
    out = []
    for k in range(i0, i0 + 45, 5):
        name, role, start, dash, end = ls[k:k + 5]
        if dash != "-" or not re.match(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}$", end):
            raise ValueError("Karuk: unexpected rows after %r" % name)
        out.append(_m(name, role, termEnds=end))
    if ls[i0 + 45] != "Council Core Values":
        raise ValueError("Karuk: the council block runs past nine, found %r" % ls[i0 + 45])
    return out


def p_la_posta(pages):
    ls = _after(pages[0], "La Posta Government Officers")
    return _name_role_pairs(ls, r"^(Chair Woman|Vice-Chairman|Secretary Treasurer|"
                                r"Tribal Council Member)$", 5)


def p_middletown(pages):
    # "Name, Office: Elected <date> – Present" over each member's paragraph
    out = []
    for line in pages[0]:
        m = re.match(r"^(.+?), (Tribal [^:]+): Elected ", line)
        if m:
            out.append(_m(_drop_stop(m.group(1)), m.group(2)))
    return out


def p_morongo(pages):
    ls = pages[0][pages[0].index("Tribal Chairman") - 1:]
    return _name_role_pairs(ls, r"^(Tribal Chairman|Tribal Vice Chair|Council Member)$", 7)


def p_pala(pages):
    # "Office – Name" under the six-member Executive Committee's heading. The
    # contact cards above it print the Pala admin line beside every member and
    # John A. Machado's own direct line beside him alone; the cards spell one
    # name differently, which the row states
    ls = _after(pages[0], "Current Executive Committee members are:")
    out = _role_dash_name(ls, 6)
    cards = pages[0][:pages[0].index("Tribal Council")]
    for mem in out:
        if mem["name"] == "John A. Machado":
            i = cards.index("John A. Machado")
            x = re.match(r"^(760-891-3535) \(Direct\)$", cards[i + 2])
            if x:
                mem["phone"] = x.group(1)
        if mem["name"] == "Sheila Smith-Lopez" and "Shelia Smith-Lopez" in cards:
            mem["note"] = "the same page also spells it Shelia Smith-Lopez"
    return out


def p_pauma(pages):
    ls = _after(pages[0], "Our Pauma Tribal Council")
    if ls[10] != "Council Committees":
        raise ValueError("Pauma: the council block runs past five, found %r" % ls[10])
    return _name_role_pairs(ls, r"^(Chairman|Chairwoman|Vice Chairman|Vice Chairwoman|"
                                r"Treasurer|Secretary|Council Member)$", 5)


def p_bear_river(pages):
    # office, then name, from the Chairwoman down; the telephone and e-mail
    # above the block are the Executive Secretary's
    ls = pages[0][pages[0].index("Chairwoman"):]
    return _role_then_name(ls, {"Chairwoman", "Chairman", "Vice-Chairman", "Vice-Chairwoman",
                                "Secretary", "Treasurer", "Member-At-Large 1",
                                "Member-At-Large 2", "Member-At-Large 3"}, 7)


def p_northfork(pages):
    # "Chairperson" is also a menu entry; the council is under the last one
    ls = pages[0]
    i0 = len(ls) - 1 - ls[::-1].index("Chairperson") - 1
    return _name_role_pairs(ls[i0:], r"^(Chairperson|Vice Chairman|Vice Chairperson|"
                                     r"Treasurer|Secretary|Member at Large)$", 5)


def p_redding(pages):
    # "Office – Name" from the Tribal Chairman down; the three alternates
    # listed after the seven are not seats
    ls = pages[0][[i for i, l in enumerate(pages[0]) if l.startswith("Tribal Chairman – ")][0]:]
    if not ls[7].startswith("1st Alternate"):
        raise ValueError("Redding: the council block runs past seven, found %r" % ls[7])
    return _role_dash_name(ls, 7)


def p_pulikla(pages):
    # name, office and the member's own e-mail, five times
    ls = pages[0]
    i0 = ls.index("Chairperson") - 1
    out = []
    for k in range(i0, i0 + 15, 3):
        name, role, email = ls[k:k + 3]
        if not _email(email):
            raise ValueError("Pulikla: no e-mail after %r" % name)
        out.append(_m(name, role, email=_email(email)))
    return out


def p_tachi(pages):
    # office, name and a sentence about the office, six times
    ls = pages[0][pages[0].index("Tribal Council Chairman"):]
    out = []
    for k in range(0, 18, 3):
        role, name = ls[k], ls[k + 1]
        if not re.match(r"^(Tribal Council Chairman|Vice-Chairman|Treasurer|Secretary|"
                        r"Delegate)$", role):
            raise ValueError("Tachi Yokut: expected an office, found %r" % role)
        out.append(_m(name, role))
    return out


def p_santa_ynez(pages):
    # the Business Committee: name, "<OFFICE> Santa Ynez Band of Chumash
    # Indians", a paragraph and a "Read More" link; offices printed in capitals
    # are title-cased
    ls = pages[0][pages[0].index("Business Committee", pages[0].index("Our Government") + 2):]
    out = []
    for i, line in enumerate(ls):
        if line.endswith(" Santa Ynez Band of Chumash Indians") and i > 0:
            role = line[:-len(" Santa Ynez Band of Chumash Indians")]
            out.append(_m(ls[i - 1], role.title() if role.isupper() else role))
        if line == "Elders Council":
            break
    return out


def p_shingle_springs(pages):
    # name, office and "Term • <start> – <end>" for seven members, then a
    # Secretary listed with no term, which the row says
    # "Tribal Council" is also a menu entry; the block opens three lines
    # above the first term
    i0 = [i for i, l in enumerate(pages[0]) if l.startswith("Term • ")][0] - 2
    if pages[0][i0 - 1] != "Tribal Council":
        raise ValueError("Shingle Springs: the council block has moved")
    ls = pages[0][i0:]
    out = []
    for k in range(0, 21, 3):
        name, role, term = ls[k:k + 3]
        m = re.match(r"^Term • \d{4} – (\d{4})$", term)
        if not m:
            raise ValueError("Shingle Springs: no term after %r" % name)
        out.append(_m(name, role, termEnds=m.group(1)))
    if ls[22] != "Secretary":
        raise ValueError("Shingle Springs: expected the Secretary, found %r" % ls[21:23])
    out.append(_m(ls[21], ls[22],
                  note="the council block lists this member with no term, unlike the others"))
    return out


def p_soboba(pages):
    # the five, after the sentence saying there are five; the Executive
    # Assistant listed under them is staff
    i = [k for k, l in enumerate(pages[0])
         if l.startswith("The Soboba Tribal Government consists of five ")][0]
    ls = pages[0][i + 1:]
    if not ls[11].startswith("Executive Assistant"):
        raise ValueError("Soboba: the council block runs past five, found %r" % ls[11])
    return _name_role_pairs(ls, r"^(Chairman|Chairwoman|Vice-Chair|Secretary|Treasurer|"
                                r"Sergeant of Arms)$", 5)


def p_susanville(pages):
    # "Office: Name" lines after the sentence saying there are seven; a
    # district councilmember's office carries the district
    i = [k for k, l in enumerate(pages[0])
         if l.startswith("The Tribal Business council of the SIR is composed of seven ")][0]
    out = []
    for line in pages[0][i + 1:i + 8]:
        role, name = line.split(": ", 1)
        m = re.match(r"^(District \d) (Council(?:wo)?man)$", role)
        if m:
            out.append(_m(name, m.group(2), district=m.group(1)))
        else:
            out.append(_m(name, role))
    return out


def p_sycuan(pages):
    # "Name, Office" lines (one broken over two), each officer's with a
    # paragraph and a "READ BIO" link
    ls = _after(pages[0], "Sycuan Tribal Council")
    ls = ls[:ls.index("Sovereignty")]
    rows, carry = [], ""
    for line in ls:
        if line == "READ BIO" or len(line) > 70:
            continue
        if line.endswith(","):
            carry = line + " "
            continue
        rows.append(carry + line)
        carry = ""
    return _comma_role_lines(rows, 7)


def p_torres_martinez(pages):
    # the proxy listed after the six is not a seat
    ls = pages[0][pages[0].index("Chairman") - 1:]
    if ls[13] != "Tribal Council Proxy":
        raise ValueError("Torres Martinez: the council block runs past six, found %r" % ls[13])
    return _name_role_pairs(ls, r"^(Chairman|Vice-Chair|Secretary|Treasurer|Tribal Council)$", 6)


def p_united_auburn(pages):
    ls = pages[0][pages[0].index("Tribal Chairman") - 1:]
    return _name_role_pairs(ls, r"^Tribal (Chairman|Vice Chairman|Secretary|Treasurer|"
                                r"Council Member at Large)$", 5)


def p_benton(pages):
    # "Name - Office" and "Email: x" for each member
    ls = _after(pages[0], "TRIBAL COUNCIL:")
    out = []
    for k in range(0, 10, 2):
        name, role = ls[k].split(" - ", 1)
        if not _email(ls[k + 1]):
            raise ValueError("Benton: no e-mail after %r" % name)
        out.append(_m(name, role, email=_email(ls[k + 1])))
    return out


def p_yurok(pages):
    # name in capitals (kept as printed), then the office or the member's
    # district, then the member's e-mail; on 2026-11-13 the last member's
    # e-mail is printed just above his name
    # the heading is also a menu entry; the council is under the last one
    ls = _after(pages[0], "Tribal Council Members",
                nth=pages[0].count("Tribal Council Members") - 1)
    ls = ls[:ls.index("Home")]
    out, used = [], set()
    i = 0
    while i < len(ls):
        line = ls[i]
        if _email(line):
            i += 1
            continue
        name, what = line, ls[i + 1]
        email = _email(ls[i + 2]) if i + 2 < len(ls) else None
        if email:
            i += 3
        else:
            prior = _email(ls[i - 1]) if i > 0 else None
            if prior and prior not in used:
                email = prior
            i += 2
        used.add(email)
        if what in ("Chairman", "Vice Chairperson"):
            out.append(_m(name, what, email=email))
        elif what.endswith(" District"):
            out.append(_m(name, "Council Member", district=what, email=email))
        else:
            raise ValueError("Yurok: no office or district after %r" % name)
    return out


_TOLOWA_OFFICES = {"Chairperson", "Vice-Chairperson", "Secretary", "Treasurer",
                   "Councilwoman", "Councilman"}


def p_tolowa(pages):
    # each member's name (one broken over two lines), the office, then the
    # name again in full; the full line ships once it agrees with the first
    ls = _after(pages[0], "Members")
    out = []
    for i, line in enumerate(ls[:40]):
        if line in _TOLOWA_OFFICES:
            full = ls[i + 1]
            if full not in (ls[i - 1], ls[i - 2] + " " + ls[i - 1]):
                raise ValueError("Tolowa: the name under %r does not match: %r" % (line, full))
            out.append(_m(full, line))
    return out


def p_greenville(pages):
    ls = _after(pages[0], "The Tribal Council")
    return _name_role_pairs(ls, r"^Tribal (Chairman|Vice-Chairwoman|Vice-Chairman|"
                                r"Secretary / Treasurer|Representative)$", 5)


def p_round_valley(pages):
    # office, "Mr./Ms./Mrs. Name", e-mail, "Term:" and the years. A courtesy
    # title is not part of the name; the receptionist's mailbox printed under
    # one member is the office's and rides nobody
    ls = _after(pages[0], "Round Valley Indian Tribes, Tribal Council")
    out = []
    for k in range(0, 35, 5):
        role, name, email, term, years = ls[k:k + 5]
        m = re.match(r"^\d{4}-(\d{4})$", years)
        if term != "Term:" or not m or not _email(email):
            raise ValueError("Round Valley: unexpected rows after %r" % name)
        email = _email(email)
        if email.lower().startswith("tribalreceptionist@"):
            email = None
        out.append(_m(re.sub(r"^(?:Mr|Ms|Mrs)\. ", "", name), role, email=email,
                      termEnds=m.group(1)))
    return out


def p_enterprise(pages):
    return _dash_role_lines(_after(pages[0], "Estom Yumeka Maidu Tribe"), 7)


def p_big_pine(pages):
    # name, office and the member's own e-mail; the page says five
    ls = pages[0]
    i0 = ls.index("Chairperson") - 1
    out = []
    for k in range(i0, i0 + 15, 3):
        name, role, email = ls[k:k + 3]
        if not _email(email):
            raise ValueError("Big Pine: no e-mail after %r" % name)
        out.append(_m(name, role, email=_email(email)))
    return out


def p_jamul(pages):
    # name, office, a paragraph (or "Coming Soon!") and a "Read More" link,
    # under the last "Tribal Council" before the news; one paragraph spells a
    # member's given name in full, which the row states
    ls = pages[0]
    end = ls.index("Latest News")
    i0 = max(i for i in range(end) if ls[i] == "Tribal Council") + 1
    out = []
    for k in range(i0, end, 4):
        name, role, bio, more = ls[k:k + 4]
        if more != "Read More":
            raise ValueError("Jamul: unexpected rows after %r" % name)
        mem = _m(name, role)
        first = bio.split(" currently serves")[0]
        if first != bio and first != name and first.split()[-1] == name.split()[-1]:
            mem["note"] = "the same page also names this member %s" % first
        out.append(mem)
    return out


def p_picayune(pages):
    # name, office and a "Bio" link; the page says seven
    ls = _after(pages[0], "The Tribal Council")
    ls = [l for l in ls[:ls.index("Meetings")] if l != "Bio"]
    return _name_role_pairs(ls, r"^(Chairperson|Vice-Chairwoman|Vice-Chairman|Secretary|"
                                r"Treasurer|Member-at-Large)$", 7)


def p_table_mountain(pages):
    ls = pages[0][pages[0].index("Tribal Chairperson") - 1:]
    if not ls[10].startswith(">>"):
        raise ValueError("Table Mountain: the council block runs past five, found %r" % ls[10])
    return _name_role_pairs(ls, r"^Tribal (Chairperson|Vice-Chairperson|Secretary/Treasurer|"
                                r"Council Member)$", 5)


def p_redwood_valley(pages):
    rows = [l for l in pages[0] if re.match(r"^[^,]+, Council ", l)]
    return _comma_role_lines(rows, 7)


def p_sherwood_valley(pages):
    # name, office and a contact link (a form, so no address is carried),
    # under the year's "Tribal Council" heading
    i = [k for k, l in enumerate(pages[0]) if re.match(r"^\d{4} Tribal Council$", l)][0]
    ls = pages[0][i + 1:]
    out = []
    for k in range(0, 21, 3):
        name, role, link = ls[k], ls[k + 1].strip("​﻿ "), ls[k + 2]
        if not link.lower().startswith("contact"):
            raise ValueError("Sherwood Valley: unexpected rows after %r" % name)
        out.append(_m(name, role))
    if ls[21] != "Office Hours:":
        raise ValueError("Sherwood Valley: the council block runs past seven, found %r" % ls[21])
    return out


def p_mesa_grande(pages):
    ls = _after(pages[0], "Mesa Grande Tribal Council")
    if not ls[5].startswith("To contact"):
        raise ValueError("Mesa Grande: the council block runs past five, found %r" % ls[5])
    return _comma_role_lines(ls, 5)


_CAHUILLA_OFFICES = {"Chairwoman", "Chairman", "Vice-Chairman", "Vice-Chairwoman",
                     "Secretary", "Treasurer", "Council Member"}


def p_cahuilla(pages):
    # each member is a name (with a line of degrees under one), the office,
    # the year seated or the term, and a bio link; the Chairwoman's entry
    # prints the tribal office's telephone and address, which ride nobody
    ls = _after(pages[0], "for More Information")
    ls = ls[:ls.index("Staff")]
    out = []
    for i, line in enumerate(ls):
        if line not in _CAHUILLA_OFFICES:
            continue
        name = ls[i - 1]
        if re.match(r"^[A-Z][A-Za-z.]*(?:, [A-Z][A-Za-z.]*)+$", name) and "." in name:
            name = ls[i - 2]
        m = re.match(r"^Current Term: .+-(\w+ \d{4})$", ls[i + 1])
        out.append(_m(name, line, termEnds=m.group(1) if m else None))
    return out


def p_kletsel_dehe(pages):
    # after the sentence naming the offices and the one about elections
    i = [k for k, l in enumerate(pages[0]) if l.startswith("The Tribal Council governs ")][0]
    ls = pages[0][i + 2:]
    if ls[10] != "Contact":
        raise ValueError("Kletsel Dehe: the council block runs past five, found %r" % ls[10])
    return _name_role_pairs(ls, r"^(Chairman|Chairwoman|Vice-Chairman|Vice-Chairwoman|"
                                r"Secretary|Treasurer|Councilman|Councilwoman)$", 5)


# The five councils below name all but one seat, or list vacant seats, and
# are carried on Adam's ruling of 2026-11-13 ("carry"). Each parser checks
# the fact its card line states (NATIONS' "partial"), so a page that changes
# fails the run rather than leaving a card line that is no longer true.

def p_ak_chin(pages):
    # name / office pairs under "COMMUNITY COUNCIL"; the chairman and vice
    # chairman each have a biography line under their office, the two
    # council members none
    ls = pages[0]
    i = ls.index("COMMUNITY COUNCIL")
    if not any("governed by a five-member Tribal Council" in l for l in ls[i:i + 4]):
        raise ValueError("Ak-Chin: the page no longer says its council has five members")
    out, k = [], ls.index("Chairman", i) - 1
    while len(out) < 4:
        name, role = ls[k], ls[k + 1]
        if not re.match(r"^(Chairman|Vice-Chairman|Council Member)$", role):
            raise ValueError("Ak-Chin: expected an office after %r, found %r" % (name, role))
        out.append(_m(name, role))
        k += 2
        if ls[k].startswith(name + " is "):
            k += 1
    if ls[k] != "Welcome to the Ak-Chin Indian Community":
        raise ValueError("Ak-Chin: the council block runs past four, found %r" % ls[k])
    return out


_HOPI_OFFICERS = ("Chairman", "Vice Chairman", "Tribal Secretary", "Tribal Treasurer",
                  "Sergeant-at-Arms")


def p_hopi(pages):
    # "Office: Name" for the five officers the page lists under "Hopi Tribal
    # Council", then each village's representatives under "Village of <name>"
    # (or "First Mesa Consolidated Villages"); a line naming a clan sits under
    # some representatives and is not a seat
    ls = pages[0]
    if not any(l.startswith("Today’s current council consists of 22 representatives")
               for l in ls):
        raise ValueError("Hopi: the page no longer says its council has 22 representatives")
    blk = _after(ls, "Hopi Tribal Council")
    out = []
    for line, office in zip(blk[:5], _HOPI_OFFICERS):
        said, _, name = line.partition(": ")
        if said != office or not name:
            raise ValueError("Hopi: expected %r, found %r" % (office, line))
        out.append(_m(name, office))
    if blk[5] != "Hopi Tribal Council Representatives":
        raise ValueError("Hopi: expected the representatives after the officers, found %r"
                         % blk[5])
    village = None
    for line in blk[6:]:
        if line == "Tribal Government":
            break
        if line.startswith("Village of ") or line == "First Mesa Consolidated Villages":
            village = line.replace("Village of ", "", 1)
        elif line.endswith(" Clan"):
            if out[-1]["role"] != "Representative":
                raise ValueError("Hopi: a clan line %r under no representative" % line)
        elif village is None:
            raise ValueError("Hopi: %r before any village" % line)
        else:
            out.append(_m(line, "Representative", district=village))
    else:
        raise ValueError("Hopi: the representatives block has no end")
    reps = sum(1 for m in out if m["role"] == "Representative")
    if reps != 21:
        raise ValueError("Hopi: read %d representatives; the page named 21 of its 22 "
                         "when its card line was written" % reps)
    return out


_DUCKWATER_OFFICES = ("INTERIM CHAIRPERSON", "VICE CHAIRPERSON", "COUNCIL SECRETARY",
                      "COUNCIL MEMBER")


def p_duckwater(pages):
    # office in capitals, then "Name- address@duckwatertribe.org" (or "VACANT-
    # ..."), then "(Term Ending – 2026)" under each seat that is held. The
    # capitals are the page's styling, so each office is written in title
    # case; a vacant seat's mailbox rides nobody
    ls = _after(pages[0], "Council Seats")
    k = ls.index(_DUCKWATER_OFFICES[0])
    out, vacant = [], []
    while not ls[k].startswith("©"):
        role = ls[k]
        if role not in _DUCKWATER_OFFICES:
            raise ValueError("Duckwater: expected an office, found %r" % role)
        m = re.match(r"^(.+?)\s*[-–]\s*(\S+@\S+)$", ls[k + 1])
        if not m:
            raise ValueError("Duckwater: expected 'Name- address' after %r, found %r"
                             % (role, ls[k + 1]))
        name, mail = m.groups()
        office = role.title()
        if name == "VACANT":
            vacant.append(office)
            k += 2
            continue
        t = re.match(r"^\(Term Ending\s*[–-]?\s*(\d{4})\)$", ls[k + 2])
        if not t:
            raise ValueError("Duckwater: no term after %r, found %r" % (name, ls[k + 2]))
        out.append(_m(name, office, termEnds=t.group(1), email=_email(mail)))
        k += 3
    if vacant != ["Vice Chairperson", "Council Secretary"]:
        raise ValueError("Duckwater: the page's vacant seats are now %r" % vacant)
    return out


_PASKENTA_OFFICES = r"^Tribal (Chairman|Vice Chairman|Secretary|Treasurer|Council Member at Large)$"


def p_paskenta(pages):
    # name / office pairs under "Meet Our Tribal Council", "Vacant" in place of
    # a name for an empty seat. The page writes one office "Tribal COuncil
    # Member at Large"; the office is read and written correctly
    ls = pages[0]
    if not any("elects the five members of the Tribal Council" in l for l in ls):
        raise ValueError("Paskenta: the page no longer says its council has five members")
    blk = _after(ls, "Meet Our Tribal Council")
    out, vacant = [], []
    for k in range(0, 10, 2):
        name, role = blk[k], blk[k + 1]
        if role.lower() == "tribal council member at large":
            role = "Tribal Council Member at Large"
        if not re.match(_PASKENTA_OFFICES, role):
            raise ValueError("Paskenta: expected an office after %r, found %r" % (name, role))
        if name == "Vacant":
            vacant.append(role)
        else:
            out.append(_m(name, role))
    if not blk[10].startswith("©"):
        raise ValueError("Paskenta: the council block runs past five seats, found %r" % blk[10])
    if vacant != ["Tribal Secretary"]:
        raise ValueError("Paskenta: the page's vacant seats are now %r" % vacant)
    return out


_WASHOE_PLACES = ("Carson Colony", "Dresslerville Community", "Stewart Community",
                  "Woodfords Community")


def p_washoe(pages):
    # The Washoe Tribe's council page is drawn in the browser from its own
    # content service, and pages[0] is that service's answer for the page:
    # one caption per member under the carousel titled "Washoe Tribal
    # Council", and the page's own text saying who sits on it, which is two
    # members appointed by each of the four community councils, two
    # Off-Reservation representatives elected by the whole membership, and
    # the chairman (read 2026-11-13)
    doc = pages[0]
    blk = doc["content"][0]["value"]
    if blk["title_and_text"]["title"] != "Washoe Tribal Council":
        raise ValueError("Washoe: the page's first block is not the council")
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ",
                                                      doc["content"][1]["value"]["richtext"])))
    for said in ("The Community Council also appoints two members to serve on the Washoe "
                 "Tribal Council",
                 "elect two Off-Reservation representatives to serve on the Washoe Tribal "
                 "Council",
                 "The Washoe Tribal Chairman is elected by the Washoe Tribal membership"):
        if said not in text:
            raise ValueError("Washoe: the page no longer says %r" % said)
    places = "|".join(re.escape(p) for p in _WASHOE_PLACES + ("Off-Reservation",))
    out = []
    for item in blk["image_block"]:
        cap = re.sub(r"\s+", " ", item["value"]["caption"]).strip()
        m = re.match(r"^(.+?), Chairman of the Washoe Tribe of Nevada and California$", cap)
        if m:
            out.append(_m(m.group(1), "Chairman"))
            continue
        m = re.match(r"^(.+?), Washoe Tribal Vice-Chairman, (%s) Representative$" % places, cap)
        if m:
            out.append(_m(m.group(1), "Vice-Chairman", district=m.group(2)))
            continue
        m = re.match(r"^(.+?), (%s) Representative$" % places, cap)
        if not m:
            raise ValueError("Washoe: a caption this parser does not read: %r" % cap)
        out.append(_m(m.group(1), "Representative", district=m.group(2)))
    chairs = [m for m in out if m["role"] == "Chairman"]
    count = {p: sum(1 for m in out if m.get("district") == p) for p in _WASHOE_PLACES}
    off = sum(1 for m in out if m.get("district") == "Off-Reservation")
    if len(chairs) != 1 or any(n != 2 for n in count.values()) or off != 1:
        raise ValueError("Washoe: read %d chairman, %r and %d Off-Reservation; the page named "
                         "one, two per community and one of two when its card line was written"
                         % (len(chairs), count, off))
    return out


PARSERS = {
    "0140": p_bad_river, "0170": p_bay_mills, "1125": p_fond_du_lac,
    "1135": p_forest_county, "1370": p_grand_traverse, "1450": p_ho_chunk,
    "1550": p_nhbp, "1610": p_saginaw, "1815": p_lco, "1830": p_lvd,
    "1963": p_ltbb, "2150": p_gun_lake, "2175": p_menominee, "2560": p_oneida,
    "2890": p_pokagon, "2980": p_prairie_band, "4625": p_winnebago,
    "0080": p_seneca, "0540": p_seneca, "2535": p_seneca, "3320": p_srmt, "0335": p_bois_forte, "1940": p_leech_lake, "2055": p_lower_sioux, "2285": p_mct,
    "3680": p_shakopee, "4445": p_upper_sioux, "4595": p_white_earth,
    "3085": p_red_cliff, "3305": p_st_croix, "3635": p_sault,
    "4015": p_stockbridge, "0525": p_catawba, "2300": p_choctaw,
    "0635": p_chitimacha, "1690": p_jena, "4315": p_tunica_biloxi,
    "9260": p_pamunkey, "9230": p_mattaponi,
    "0050": p_alabama_coushatta, "1775": p_kickapoo_tx, "4755": p_ysleta,
    **{code: p_seminole_fl for code in ("0225", "0360", "0690", "1260", "1475", "1555",
                                        "3665", "4130")},
    # Washington
    "0575": p_chehalis, "0760": p_colville, "0820": p_cowlitz, "2040": p_lower_elwha,
    "2070": p_lummi, "2085": p_makah, "2375": p_muckleshoot, "2460": p_nisqually,
    "2475": p_nooksack, "2910": p_pgst, "2925": p_suquamish, "3030": p_quileute,
    "3040": p_quinault, "3780": p_shoalwater, "3825": p_skokomish, "3860": p_snoqualmie,
    "4000": p_stillaguamish, "4290": p_tulalip, "4405": p_umatilla, "4690": p_yakama,
    # Arizona
    "0695": p_cocopah, "0735": p_crit, "1235": p_fort_mojave, "1280": p_quechan,
    "1310": p_gila_river, "1545": p_hualapai, "2430": p_navajo, "2680": p_pascua_yaqui,
    "3340": p_salt_river, "3355": p_san_carlos, "4200": p_tohono_oodham,
    "4708": p_yavapai_apache, "4785": p_zuni,
    # Nevada
    "0440": p_yerington, "0965": p_duck_valley, "1070": p_fallon, "1075": p_fallon, "1340": p_goshute, "4725": p_yerington,
    "1915": p_las_vegas_paiute, "2315": p_moapa, "4180": p_timbisha, "4515": p_walker_river,
    # California
    "0120": p_united_auburn, "0125": p_augustine, "0155": p_barona, "0185": p_benton,
    "0250": p_big_pine, "0265": p_big_sandy, "0275": p_big_valley, "0290": p_bishop,
    "0325": p_blue_lake, "0435": p_cahuilla, "4500": p_viejas, "0780": p_kletsel_dehe,
    "0955": p_dry_creek, "1010": p_elk_valley, "1055": p_enterprise, "1380": p_greenville,
    "1490": p_hoopa, "1515": p_hopland, "1670": p_jamul, "1750": p_karuk,
    "1895": p_la_posta, "2190": p_mesa_grande, "2255": p_middletown, "2360": p_morongo,
    "2495": p_northfork, "2635": p_pala, "2715": p_pauma, "2775": p_picayune,
    "3095": p_redding, "3115": p_redwood_valley, "3145": p_pulikla, "3220": p_bear_river,
    "3250": p_round_valley, "3520": p_tachi, "3540": p_santa_ynez,
    "3735": p_sherwood_valley, "3750": p_shingle_springs, "3855": p_tolowa,
    "3870": p_soboba, "4060": p_susanville, "4090": p_sycuan, "4110": p_table_mountain,
    "4255": p_torres_martinez, "4275": p_trinidad, "4760": p_yurok,
    # partial councils carried on Adam's ruling of 2026-11-13
    "2130": p_ak_chin, "1505": p_hopi, "0975": p_duckwater, "2685": p_paskenta,
    **{code: p_washoe for code in ("0510", "0940", "3980", "4560", "4665")},
}
STATE_LIST_HEADINGS = {"1825": "Lac du Flambeau Band of Lake", "3885": "Sokaogon Chippewa Community",
                       "3075": "Rappahannock"}

# governor, cacique, captain and alguacil are the Ysleta del Sur Pueblo's
# council offices (its War Captain and Alguacil are council seats); trustee is
# the Umatilla board's, speaker the Navajo Nation Council's, delegate the
# Tachi Yokut council's and the Navajo Nation's, and parliamentarian Sherwood
# Valley's
_ROLE_OK = re.compile(r"(chair|president|chief|secretary|treasurer|member|representative|"
                      r"director|legislator|councilor|council|sergeant|chaplain|leader|"
                      r"governor|cacique|captain|alguacil|trustee|speaker|delegate|"
                      r"parliamentarian)", re.I)
_ROLE_WORDS = re.compile(r"^(chair|vice|secretary|treasurer|council|member|president|"
                         r"representative|director|legislator|councilor)\b", re.I)


def validate(code, members):
    want = NATIONS[code]["seats"]
    if len(members) != want:
        raise ValueError("%s: read %d member(s), the page states %d"
                         % (NATIONS[code]["nation"], len(members), want))
    names = [m["name"] for m in members]
    if len(set(names)) != len(names):
        raise ValueError("%s: a name appears twice: %r" % (NATIONS[code]["nation"], names))
    for m in members:
        if (not m["name"] or _ROLE_WORDS.match(m["name"]) or len(m["name"]) > 60
                or re.search(r"[\d@&/]", m["name"]) or len(m["name"].split()) < 2):
            raise ValueError("%s: %r is not a name" % (NATIONS[code]["nation"], m["name"]))
        if not m["role"] or not _ROLE_OK.search(m["role"]):
            # a role this module does not recognise as an office is the
            # cheapest sign a parser has walked off its block into a menu
            raise ValueError("%s: %r is not an office (for %r)"
                             % (NATIONS[code]["nation"], m["role"], m["name"]))
    return members


_PACER = []


def _pacer():
    """One HostPacer for the run. Bois Forte and White Earth both state a
    Crawl-delay of 30 s (read 2026-10-10 with this scraper's own client), and
    both are read across several pages, so each of their requests waits its
    turn; a host that states no delay is not slowed."""
    if not _PACER:
        import requests
        import robots_policy as R
        import scraper_common as S
        session = requests.Session()
        gate = R.RobotsGate(session, S.UA_ROSTER_BOT,
                            headers=S.UA_HEADERS_ROSTER_BOT)
        _PACER.append(R.HostPacer(gate))
    return _PACER[0]


def fetch_page(url):
    import scraper_common as S
    S.require_robots_once(url, S.UA_ROSTER_BOT, headers=S.UA_HEADERS_ROSTER_BOT,
                          label="tribal-councils")
    with _pacer().hold(url):
        resp = S.fetch(url, S.UA_HEADERS_ROSTER_BOT, timeout=40, attempts=3)
    return resp.content


def run(from_dir=None, today=None):
    today = today or datetime.date.today().isoformat()
    prior = {}
    if os.path.exists(OUT):
        prior = json.load(open(OUT)).get("councils", {})
    cache = {}

    def get(url, key):
        if url not in cache:
            if from_dir:
                path = os.path.join(from_dir, key)
                cache[url] = open(path, "rb").read()
            else:
                cache[url] = fetch_page(url)
        return cache[url]

    councils, failed = {}, []
    for code in sorted(NATIONS):
        spec = NATIONS[code]
        try:
            if spec.get("stateList"):
                sl = STATE_LISTS[spec["stateList"]]
                members, updated = sl["parse"](get(sl["page"], sl["key"]),
                                               STATE_LIST_HEADINGS[code], spec["seats"])
                rec = {"source": "state-list", "publisher": sl["publisher"],
                       "page": sl["page"]}
                if updated:
                    rec["listUpdated"] = updated
                if sl.get("officersOnly"):
                    rec["list"] = sl["list"]
                    rec["officersOnly"] = True
            else:
                raw = [get(u, "%s-%d.html" % (code, k)) for k, u in enumerate(spec["pages"])]
                if spec.get("json"):
                    # a page drawn in the browser from its site's own content
                    # service is read from that service's answer (Washoe)
                    pages = [json.loads(r.decode("utf-8")) for r in raw]
                else:
                    pages = [lines_of(r.decode("utf-8", "replace"), spec.get("br", "\n"))
                             for r in raw]
                members = PARSERS[code](pages)
                # the card links the page a visitor sees, which is the last
                # page read unless the spec names the visitor's address
                rec = {"source": "nation", "page": spec.get("link") or spec["pages"][-1],
                       "pages": spec["pages"]}
                if spec.get("partial"):
                    rec["partial"] = spec["partial"]
            rec["members"] = validate(code, members)
            rec["read"] = today
            councils[code] = rec
            print("tribal-councils: %s %-26s %2d member(s) from %s"
                  % (code, spec["nation"], len(members), rec["page"]))
        # SystemExit too: scraper_common's robots gate exits on a refusal or an
        # unreadable robots.txt, and one nation's host must never stop the rest
        # (found 2026-10-10, when www.sagchip.org's robots.txt failed TLS here).
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            if code in prior:
                councils[code] = dict(prior[code], carriedFrom=prior[code].get("read"))
                print("tribal-councils: %s %s NOT READ this run (%s); carrying the "
                      "council last read %s" % (code, spec["nation"], exc,
                                                prior[code].get("read")))
            else:
                failed.append("%s %s: %s" % (code, spec["nation"], exc))
    if failed:
        raise SystemExit("tribal-councils: never read and not readable now:\n  "
                         + "\n  ".join(failed))
    doc = {"note": NOTE,
           "councils": councils}
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("tribal-councils: OK — %d council(s) written to %s" % (len(councils), OUT))
    return doc


def selftest():
    assert lines_of("<h3>Samuel<br>Klingman</h3><p>Vice Chairman</p>", " ") == ["Samuel Klingman", "Vice Chairman"]
    assert lines_of("Nicole Boyd - Chair<br>Misty Nordin - Vice Chair") == ["Nicole Boyd - Chair", "Misty Nordin - Vice Chair"]
    assert lines_of("<p>906‑632‑6453</p>") == ["906-632-6453"]
    assert _sentence_roles("Vice President Andy LeBlanc, President Whitney Gravelle, "
                           "and Treasurer Audrey Breakie.",
                           ["Vice President", "President", "Treasurer"]) == [
        ("Vice President", "Andy LeBlanc"), ("President", "Whitney Gravelle"),
        ("Treasurer", "Audrey Breakie")]
    try:
        _sentence_roles("Chef Somebody", ["President"])
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown role must fail")
    assert _sentence_roles("Treasurer Joseph Daniels Sr., and Council Member Herb Daniels Jr.",
                           ["Treasurer", "Council Member"])[-1] == ("Council Member", "Herb Daniels Jr.")
    assert _phone("920-869-4420") == "920-869-4420" and _phone("none") is None
    assert _email("x thill7@oneidanation.org y") == "thill7@oneidanation.org"
    # Cloudflare's own example key: 0x15 XORed through "ab@c.de"
    hidden = "15" + "".join("%02x" % (ord(c) ^ 0x15) for c in "ab@c.de")
    assert lines_of('<p>Email: <a href="/cdn-cgi/l/email-protection" class="__cf_email__" '
                    'data-cfemail="%s">[email&#160;protected]</a></p>' % hidden) == ["Email: ab@c.de"]
    # a link whose href alone is protected keeps its own text
    assert lines_of('<a href="/cdn-cgi/l/email-protection#%s"><span>(320) 564-3853</span></a>'
                    % hidden) == ["(320) 564-3853"]
    # Bois Forte's shape (numbers invented): the office line stays in phone,
    # the member's own line rides phonesExtra with the page's word "cell" or
    # bare where the page labels it with the name; a fax and a number printed
    # for the government office as well are not carried as anyone's own.
    bf = p_bois_forte([["Bois Forte Tribal Council",
                        "Ann Example", "Chairperson",
                        "Office: 555-010-1000 x 1", "Cell: 555-010-2001",
                        "ann@example.org",
                        "Bob Sample", "District II Representative, Vice-Chairperson",
                        "Vermilion Office: 555-010-3000", "Fax: 555-010-4000",
                        "Bob Sample: 555-010-2002", "Cell: 555-010-3000",
                        "bob@example.org",
                        "Office: 555-010-3000"]])
    assert bf[0]["phone"] == "555-010-1000 x 1" and bf[0]["phonesExtra"] == ["cell 555-010-2001"], bf
    assert bf[1]["phone"] == "555-010-3000" and bf[1]["phonesExtra"] == ["555-010-2002"], bf
    assert _m("A B", "Chair", phonesExtra=[" cell 1 "])["phonesExtra"] == ["cell 1"]
    # Louisiana's three shapes (names invented): Chitimacha's comma form,
    # Jena's office-then-name cards, and Tunica-Biloxi's "Sr." in a biography
    ch = p_chitimacha([["Tribal Council", "Chairman", "Tribal Council",
                        "Ann Example - Chairman", "Bea Sample, Secretary/Treasurer",
                        "155 Chitimacha Loop | Charenton, LA 70523"]])
    assert ch == [_m("Ann Example", "Chairman"),
                  _m("Bea Sample", "Secretary/Treasurer")], ch
    jb = p_jena([["Tribal Leaders", "Tribal Leaders", "Tribal Chief", "Ann Example",
                  "was elected Tribal Chief.", "Councilman", "Bob Sample", "serves.",
                  "Stay connected", "Councilman", "Not Read"]])
    assert [m["name"] for m in jb] == ["Ann Example", "Bob Sample"], jb
    tb = p_tunica_biloxi([["Our Tribal Council", "Ann Example", "Chairman",
                           "Ann Example is the Chairman.", "Bob Sample", "Council Member",
                           "Bob Sample, Sr. is a commissioner.",
                           "Tunica Biloxi Tribe of Louisiana", "150 Example Road"]])
    assert tb[0] == _m("Ann Example", "Chairman"), tb
    assert tb[1]["note"] == "the same page also writes Bob Sample, Sr.", tb
    # Virginia's two shapes (names invented): Pamunkey's "Chief <name>"
    # headings above biographies, and Mattaponi's list under a leadership
    # panel that names another assistant chief
    pk = p_pamunkey([["Tribal Government", "Chief Ann Example",
                      "Chief Ann Example serves as the leader of the tribe.",
                      "Assistant Chief Bob Sample", "Bob Sample is the Assistant Chief.",
                      "Tribal Council", "Cy Person", "Di Person Jr.",
                      "Tribal Administration", "Executive Director: Ed Staff"]])
    assert pk == [_m("Ann Example", "Chief"), _m("Bob Sample", "Assistant Chief"),
                  _m("Cy Person", "Council Member"),
                  _m("Di Person Jr.", "Council Member")], pk
    mt = p_mattaponi([["Tribal Council Leadership", "Ann Example", "CHIEF", "A bio.",
                       "Old Name", "ASSISTANT CHIEF", "A short bio.",
                       "Mattaponi Tribal Council", "Chief:", "Ann Example",
                       "Assistant Chief:", "Bob Sample", "Council Members:",
                       "Cy Person", "Di Person, Jr",
                       "All materials used on this website belong to the tribe."]])
    assert mt[0] == _m("Ann Example", "Chief"), mt
    assert mt[1] == _m("Bob Sample", "Assistant Chief",
                       note="the same page's leadership panel names Old Name as assistant chief"), mt
    assert [m["name"] for m in mt[2:]] == ["Cy Person", "Di Person, Jr"], mt
    # Texas's and Florida's four shapes (names invented): Alabama-Coushatta's
    # chiefs then "Tribal" offices, Kickapoo's doubled pairs, Ysleta del Sur's
    # caption sentence, and the Seminole Tribe's reservation in the office
    ac = p_alabama_coushatta([["Ann Chief", "Principal Chief", "Bob Chief", "second Chief",
                               "Cy Person", "Tribal Council Chairman",
                               "Di Person", "Tribal Councilmember",
                               "Constitution and By Laws", "Click to read."]])
    assert ac == [_m("Cy Person", "Tribal Council Chairman"),
                  _m("Di Person", "Tribal Councilmember")], ac
    try:
        p_alabama_coushatta([["second Chief", "Cy Person", "Chairman",
                              "Constitution and By Laws"]])
    except ValueError:
        pass
    else:
        raise AssertionError("an Alabama-Coushatta office without 'Tribal' must fail")
    kk = p_kickapoo_tx([["TRIBAL COUNCIL", "Ann Example, Sr., Nameone", "Chairman",
                         "Ann Example, Sr., Nameone", "Chairman", "Bob Sample", "Member",
                         "Bob Sample", "Member", "Fitness Center", "Member"]])
    assert kk == [_m("Ann Example, Sr., Nameone", "Chairman"),
                  _m("Bob Sample", "Member")], kk
    ys = p_ysleta([["Tribal Council", "2026 Tribal Council", "Left To Right:",
                    "Councilman Ann Example Jr., War Captain Bob Sample,",
                    "Lt. Governor Cy Person, Governor E. Di Person,",
                    "Cacique Ed Staff, Alguacil Fay Other", "Documents", "Report"]])
    assert ys == [_m("Ann Example Jr.", "Councilman"), _m("Bob Sample", "War Captain"),
                  _m("Cy Person", "Lt. Governor"), _m("E. Di Person", "Governor"),
                  _m("Ed Staff", "Cacique"), _m("Fay Other", "Alguacil")], ys
    sm = p_seminole_fl([["Tribal Council", "Today's Government", "Tribal Council",
                         "Ann Example Jr.", "Chairman", "Bob Sample",
                         "President/Vice-Chairwoman", "Cy Person", "Big Cypress Councilwoman",
                         "Toggle navigation", "Tribal Council"]])
    assert sm == [_m("Ann Example Jr.", "Chairman"),
                  _m("Bob Sample", "President/Vice-Chairwoman"),
                  _m("Cy Person", "Councilwoman", district="Big Cypress")], sm
    NATIONS["9999"] = {"nation": "Test", "seats": 2}
    try:
        for bad in ([_m("A B", "Chair")],
                    [_m("A B", "Chair"), _m("A B", "Secretary")],
                    [_m("A B", "Chair"), _m("Council Member", "Secretary")],
                    [_m("Veterans", "Tribal Council Meeting Login"), _m("C D", "Law Library")],
                    [_m("A B", "Chair"), _m("WOS 2012-017 Tribal Secretary", "Secretary")]):
            try:
                validate("9999", bad)
            except ValueError:
                continue
            raise AssertionError("validate passed %r" % bad)
        assert validate("9999", [_m("A B", "Chair"), _m("C D", "Secretary")])
    finally:
        del NATIONS["9999"]
    # The Commonwealth's list (names invented): a staff line beginning
    # "Chief" is not a chief, and the list's own misspelling is read
    va_page = ("<p>Upper Example</p><p>Chief Zed Other</p><p>Contact information</p>"
               "<p>Example</p><p>Chief Ann Example</p><p>Assistant Cheif Bob Sample</p>"
               "<p>Tribal Administrator Chief Example</p>"
               "<p>Chief Financial Officer Cy Person</p><p>Contact information</p>"
               "<p>Ed Staff</p>").encode()
    va, upd = _va_state_list(va_page, "Example", 2)
    assert va == [_m("Ann Example", "Chief"), _m("Bob Sample", "Assistant Chief")], va
    assert upd is None
    for bad in (va_page.replace(b"<p>Assistant Cheif Bob Sample</p>", b""),
                va_page.replace(b"<p>Upper Example</p>", b"<p>Example</p>")):
        try:
            _va_state_list(bad, "Example", 2)
        except ValueError:
            continue
        raise AssertionError("the Commonwealth's list parsed %r" % bad)
    # California's shapes (names and numbers invented). Hoopa: the
    # Chairman's line carries a staff member's telephone, which is not his,
    # and a district member printed with an empty extension gets no number
    hp = p_hoopa([["Hoopa Valley Tribal Council", "Ann Example | Chairman",
                   "Administrative Officer's Phone: (555) 010-1000 Ext. 1",
                   "email: chair@example.org"]
                  + sum([["%s | Vice-Chairman" % n if k == 0 else n,
                          "%s District Representative" % d,
                          "Office Phone: (555) 010-1000 Ext.%s" % (" %d" % (k + 2) if k else ""),
                          "email: m%d@example.org" % k]
                         for k, (n, d) in enumerate([("Bob Sample", "East"), ("Cy Person", "West"),
                                                     ("Di Person", "North"), ("Ed Person", "South"),
                                                     ("Flo Person", "Upper"), ("Gus Person", "Lower"),
                                                     ("Hal Person", "Middle")])], [])
                  + ["About Us"]])
    assert hp[0] == _m("Ann Example", "Chairman", email="chair@example.org"), hp[0]
    assert hp[1] == _m("Bob Sample", "Vice-Chairman", district="East District",
                       email="m0@example.org"), hp[1]
    assert hp[2]["phone"] == "(555) 010-1000 Ext. 3" and hp[2]["role"] == "District Representative"
    # Round Valley: a courtesy title is dropped, a receptionist's mailbox
    # rides nobody
    rv = p_round_valley([["Round Valley Indian Tribes, Tribal Council"]
                         + sum([[r, "%s %s" % (t, n), e, "Term:", "2025-2029"]
                                for r, t, n, e in [
                                    ("President", "Mr.", "Ann Example", "ann@example.org"),
                                    ("Secretary", "Ms.", "Bea Sample", "tribalreceptionist@example.org"),
                                    ("Treasurer", "Mrs.", "Cy Person", "t@example.org"),
                                    ("Member at large", "Mr.", "Di Person", "d@example.org"),
                                    ("Member at large", "Ms.", "Ed Person", "e@example.org"),
                                    ("Member at large", "Mr.", "Flo Person", "f@example.org"),
                                    ("Member at large", "Mr.", "Gus Person", "g@example.org")]], [])])
    assert rv[0] == _m("Ann Example", "President", email="ann@example.org", termEnds="2029"), rv[0]
    assert rv[1] == _m("Bea Sample", "Secretary", termEnds="2029"), rv[1]
    # Yurok: a member's address printed just above the name is his, and one
    # already carried is not taken twice
    yk = p_yurok([["Tribal Council Members", "ANN EXAMPLE", "Chairman", "ann@example.org",
                   "BOB SAMPLE", "North District", "bob@example.org",
                   "cy@example.org", "CY PERSON", "South District", "Home"]])
    assert yk == [_m("ANN EXAMPLE", "Chairman", email="ann@example.org"),
                  _m("BOB SAMPLE", "Council Member", district="North District",
                     email="bob@example.org"),
                  _m("CY PERSON", "Council Member", district="South District",
                     email="cy@example.org")], yk
    # Dry Creek: the office runs into the name and is cut off, longest first
    dc = p_dry_creek([["Board of Directors", "Board of Directors", "Board of Directors",
                       "Ann ExampleChairman", "Bob SampleVice-Chair", "Cy PersonSecretary/Treasure",
                       "Di PersonMember at Large", "Ed PersonMember at Large"]])
    assert dc[1] == _m("Bob Sample", "Vice-Chair") and dc[4] == _m("Ed Person", "Member at Large"), dc
    # Redding: an alternate after the seventh member is not a seat
    rd = p_redding([["Tribal Chairman – Ann Example"]
                    + ["Council Member – %s Person" % n for n in "BCDEFG"]
                    + ["1st Alternate – Hal Person"]])
    assert len(rd) == 7 and rd[0] == _m("Ann Example", "Tribal Chairman"), rd
    try:
        p_redding([["Tribal Chairman – Ann Example"]
                   + ["Council Member – %s Person" % n for n in "BCDEFGH"]])
    except ValueError:
        pass
    else:
        raise AssertionError("Redding's block running past seven must fail")
    # The five partial councils (names invented). Each reader checks the
    # fact its card line states, so a filled or newly vacant seat fails.
    ak = p_ak_chin([["COMMUNITY COUNCIL",
                     "The community is governed by a five-member Tribal Council.",
                     "Ann Example", "Chairman", "Ann Example is the chairman.",
                     "Bob Sample", "Vice-Chairman", "Cy Person", "Council Member",
                     "Di Person", "Council Member",
                     "Welcome to the Ak-Chin Indian Community"]])
    assert [m["name"] for m in ak] == ["Ann Example", "Bob Sample", "Cy Person", "Di Person"], ak
    hp_page = (["Today’s current council consists of 22 representatives from the villages.",
                "Hopi Tribal Council", "Chairman: Ann Example", "Vice Chairman: Bob Sample",
                "Tribal Secretary: Cy Person", "Tribal Treasurer: Di Person",
                "Sergeant-at-Arms: Ed Person", "Hopi Tribal Council Representatives",
                "Village of Example"]
               + ["Rep%s Person" % c for c in "ABCDEFGHIJ"] + ["Corn Clan",
                  "First Mesa Consolidated Villages"]
               + ["Rep%s Person" % c for c in "KLMNOPQRSTU"] + ["Tribal Government"])
    hp = p_hopi([hp_page])
    assert hp[5] == _m("RepA Person", "Representative", district="Example"), hp
    assert hp[-1]["district"] == "First Mesa Consolidated Villages" and len(hp) == 26, hp
    for bad in (hp_page[:9] + hp_page[10:],
                [l.replace("22 representatives", "21 representatives") for l in hp_page]):
        try:
            p_hopi([bad])
        except ValueError:
            continue
        raise AssertionError("Hopi's reader passed a changed page")
    dw_page = ["Council Seats", "INTERIM CHAIRPERSON", "Ann Example- chair@example.org",
               "(Term Ending – 2026)", "VICE CHAIRPERSON", "VACANT- vice@example.org",
               "COUNCIL SECRETARY", "VACANT- sec@example.org", "COUNCIL MEMBER",
               "Bob Sample – bob@example.org", "(Term Ending 2028)", "© Example"]
    dw = p_duckwater([dw_page])
    assert dw == [_m("Ann Example", "Interim Chairperson", termEnds="2026",
                     email="chair@example.org"),
                  _m("Bob Sample", "Council Member", termEnds="2028",
                     email="bob@example.org")], dw
    try:
        p_duckwater([[l.replace("VACANT- sec@", "Cy Person- sec@") for l in dw_page]])
    except (ValueError, IndexError):
        pass
    else:
        raise AssertionError("a filled Duckwater seat must fail its card line")
    pk_page = ["The General Council elects the five members of the Tribal Council.",
               "Meet Our Tribal Council", "Ann Example", "Tribal Chairman", "Bob Sample",
               "Tribal Vice Chairman", "Vacant", "Tribal Secretary", "Cy Person",
               "Tribal Treasurer", "Di Person", "Tribal COuncil Member at Large", "© Example"]
    pk = p_paskenta([pk_page])
    assert pk[-1] == _m("Di Person", "Tribal Council Member at Large") and len(pk) == 4, pk
    try:
        p_paskenta([[l.replace("Vacant", "Ed Person") for l in pk_page]])
    except ValueError:
        pass
    else:
        raise AssertionError("a filled Paskenta seat must fail its card line")
    wt_text = ("<p>The Community Council also appoints two members to serve on the Washoe "
               "Tribal Council. The Washoe Tribal membership as a whole elect two "
               "Off-Reservation representatives to serve on the Washoe Tribal Council. "
               "The Washoe Tribal Chairman is elected by the Washoe Tribal membership as a "
               "whole.</p>")
    caps = (["Ann Example, Chairman of the Washoe Tribe of Nevada and California",
             "Bob Sample, Washoe Tribal Vice-Chairman, Dresslerville Community Representative",
             "Cy Person, Dresslerville Community Representative"]
            + ["%s Person, %s Representative" % (n, place) for n, place in (
                ("Di", "Carson Colony"), ("Ed", "Carson Colony"),
                ("Fay", "Stewart Community"), ("Gus", "Stewart Community"),
                ("Hal", "Woodfords Community"), ("Ida", "Woodfords Community"),
                ("Jo", "Off-Reservation"))])
    def wt_doc(captions):
        return {"content": [{"value": {"title_and_text": {"title": "Washoe Tribal Council"},
                                       "image_block": [{"value": {"caption": c}}
                                                       for c in captions]}},
                            {"value": {"richtext": wt_text}}]}
    wt = p_washoe([wt_doc(caps)])
    assert wt[1] == _m("Bob Sample", "Vice-Chairman", district="Dresslerville Community"), wt
    assert len(wt) == 10 and wt[-1]["district"] == "Off-Reservation", wt
    try:
        p_washoe([wt_doc(caps + ["Kay Person, Off-Reservation Representative"])])
    except ValueError:
        pass
    else:
        raise AssertionError("a second Off-Reservation representative must fail Washoe's card line")
    for code, spec in NATIONS.items():
        assert bool(spec.get("partial")) == (PARSERS.get(code) in (
            p_ak_chin, p_hopi, p_duckwater, p_paskenta, p_washoe)), code
    assert _drop_stop("Julian Example.") == "Julian Example"
    assert _drop_stop("Ann Example Jr.") == "Ann Example Jr."
    for code, spec in NATIONS.items():
        if spec.get("stateList"):
            assert spec["pages"] == [STATE_LISTS[spec["stateList"]]["page"]], code
    assert set(PARSERS) | set(STATE_LIST_HEADINGS) == set(NATIONS)
    print("tribal-council-scraper --selftest: OK — %d nation(s), %d parser(s), "
          "%d from the state list" % (len(NATIONS), len(PARSERS), len(STATE_LIST_HEADINGS)))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--from-dir")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return 0 if selftest() else 1
    run(args.from_dir)
    if _PACER:
        for line in _PACER[0].report():
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
