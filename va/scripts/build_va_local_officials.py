#!/usr/bin/env python3
"""
Build va/data/app/va-local-officials.json: who sits on each Virginia county's
board of supervisors, each independent city's council and each school board,
each city's mayor, and each town's council and mayor, from the state's own
election results.

    python3 va/scripts/build_va_local_officials.py                 # fetch, compose, write
    python3 va/scripts/build_va_local_officials.py --save-source F # also keep the fetch
    python3 va/scripts/build_va_local_officials.py --source F      # build from a kept fetch
    python3 va/scripts/build_va_local_officials.py --check         # offline, for CI

THE SOURCE. The Department of Elections' results site,
historical.elections.virginia.gov, which holds the result of every contest
the state runs, local ones included, and names the district of every
district seat. Its pages read a GraphQL interface at /api/graphql_pr; this
builder asks it the question the site's own search asks: every contest for
one office in one year. Its robots.txt (25 bytes, read 2026-10-30) disallows
nothing, and every request is paced a second apart. Adam chose this source
on 22 October 2026 ("as recommended"), with each card saying which election
its names come from, as Arkansas's cards do.

WHAT A RESULT CAN AND CANNOT SAY. A result names who won a seat on the day
of the election. It does not say who was appointed to a seat that fell
vacant, which in Virginia lasts until a special election, and it goes on
naming a winner who has since left. So:

  - every member carries the date and kind of the election that named them,
    and the card prints it;
  - a seat a special election has filled since its regular election is named
    from the special election;
  - a seat whose history does not settle who holds it (two elections for one
    seat where the body elects two from the district, a special election to
    an at-large body of several members, a seat that stopped being elected)
    is named only from HAND, which records a person's reading of the
    county's or city's own page with its address and date, or not at all;
  - a winner elected to a body after 1 January of the year a new term began
    does not displace the member sitting until then: Virginia's November
    winners take office on 1 January (Code of Virginia §24.2-222 and
    §24.2-228.1), so a contest from November of the current year is held as
    `pending` until then and the card names the sitting member.

HOW A SEAT'S HOLDER IS FOUND. Contests are grouped by locality, body and
district (an at-large seat's district is empty). A district seat's term is
four years. Within a group:

  - A regular contest in year y is IN OFFICE from 1 January of y+1 for four
    years (or the term the group's own history shows, for an at-large
    group: the commonest gap between one person's re-elections, else between
    the group's single-seat elections, else four).
  - A district that has two regular contests in office, each repeated a term
    earlier or later (the district elects two members in alternate years, as
    Wise County's do), seats both winners. Otherwise the latest regular
    contest in office seats its winner, and a special election after it seats
    the special's winner instead.
  - An at-large group seats the winners of the latest regular contest in
    office in each of its classes (the years, counted modulo the term, in
    which it holds regular elections), so a council electing four members
    and then three seats seven.
  - A special election after the regular contests of a group of several
    seats does not say whom it replaced, so that group is UNSETTLED and named
    from HAND or not at all.

A WINNER is the candidate the results mark as the winner. 92 contests carry
no mark at all (measured 2026-10-30, all of Culpeper County's 2023 contests
among them); for those the winners are the candidates with the most votes,
as many as the contest has seats, and a tie at the last seat leaves the
contest unread. "Write-Ins", "Total Votes Cast", "Total Ballots Cast" and
"Undervotes" are totals the results list beside the candidates and are never
a winner; a seat won by write-in votes is recorded as won by someone the
results do not name.

WHICH DISTRICT A RESULT MEANS. Each result names its district by label
("Henrico County - Brookland", "Norfolk - Superward 7"); each label is
matched to one district of va/scripts/va_localities.py by number or by name,
and a locality whose labels do not match its districts one to one stops the
build unless LABEL_MAP says which is which. A label that matches no district
and has no seat in office is a district that no longer exists (Virginia
Beach's boroughs, retired in 2022) and is left out.

THE TOWNS. Every town on the Census's list (va/data/source/va-towns.json,
read from the TIGERweb places layer the City or Town layer draws, LSADC 43)
gets an entry keyed by the Census's BASENAME, which is the property the card
matches on; TOWN_ALIAS turns the results' spelling into it where the two
differ ("MT CRAWFORD"), and TOWN_ROUTES files the few town contests the
results report under their county (Sussex County's three towns, West
Point's school board). A town in two counties was reported once per county
part until 2023, and merge_town_parts makes the parts one contest. A town
council is at large unless the town elects by ward, and a ward town's
council names no one (its wards are not drawn). Its term is read from its
last three regular elections: two years only if at least two members were
re-elected two years on and those outnumber re-elections four years on,
since a member elected to the last two years of a seat looks the same, and
four otherwise; and the latest term's seats must equal the term before's,
or the council is unsettled, since a council of five that elected one
member in 2025 has not shrunk to one. A council named this way was checked
on 2026-10-30 against each town's charter in the Code of Virginia
(law.lis.virginia.gov), which holds 69 of the 77 then named: 65 gave the
same number of seats, Monterey's and Montross's give none (Monterey's own
page lists the same three members), and two differed, Blacksburg, whose
sixth member was elected mayor, and Kenbridge, whose three-of-six cycle the
rule above was changed to read, after which it names no one (a special
election filled one of its seats). HAND names the
larger towns the results do not settle, from their own pages.

NOTHING HERE IS A CONTACT. The results carry names only, so the cards link
the county's or city's own page for a telephone or an e-mail address.
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))

import va_localities as vl  # noqa: E402

API = "https://historical.elections.virginia.gov/api/graphql_pr"
SITE = "https://historical.elections.virginia.gov/"
USER_AGENT = "districtry/1.0 (+https://districtry.com/va/)"
PACE = 1.0
PAGE = 96
FIRST_YEAR = 2015
OUT = os.path.join(vl.DATA, "va-local-officials.json")
RECORD = os.path.join(vl.INSTANCE, "data", "source", "va-local-officials.record.json")

QUERY = ("query($f: SearchFilters!, $p: Pagination!) { search(filters: $f, pagination: $p) "
         "{ results { id name nSeats isSpecial office { id name } event { id startDate } "
         "eventTypeDisplayName division { id name divisionTypeName } "
         "candidates { displayName isWinner nVotes } } } }")

# The results' offices this builder reads, and the body each fills.
OFFICES = {
    "419": "board",         # Board of Supervisors
    "546": "board",         # County Board Member (Arlington's County Board)
    "551": "board",         # City Council
    "554": "chair",         # Chairman of the Board of Supervisors, elected at large
    "73": "mayor",          # Mayor
    "549": "school",        # School Board
    "555": "school-chair",  # Chairman of the School Board, elected at large
    "547": "town",          # Town Council
}
TOWNS_FILE = os.path.join(vl.INSTANCE, "data", "source", "va-towns.json")
TOWNS_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
             "Places_CouSub_ConCity_SubMCD/MapServer/4")
TOWN_TILES = os.path.join(vl.DATA, "tiles", "municipality.pmtiles")
TOWN_FLOOR = 180       # Virginia has 189 towns (TIGERweb, read 2026-10-30)
# The results' spellings of a town that are not the Census's, upper-cased.
# St Charles, in Lee County, is not here: the Census's list holds no such
# town, and the results' last contests for it were in 2020.
TOWN_ALIAS = {"MT CRAWFORD": "Mount Crawford", "MT JACKSON": "Mount Jackson",
              "ST PAUL": "St. Paul", "LACROSSE": "La Crosse", "PAMPLIN": "Pamplin City"}
# A town's contests the results file under its county, with the town as the
# label: (locality, body, label) -> town. Each entry must match a contest.
# Sussex County's districts share three of these names (Stony Creek,
# Wakefield and Waverly are magisterial districts as well as towns), so a
# route names its body and the county's own board and school seats stay its.
TOWN_ROUTES = {
    ("Sussex County", "town", "Stony Creek"): "Stony Creek",
    ("Sussex County", "mayor", "Stony Creek"): "Stony Creek",
    ("Sussex County", "town", "Wakefield"): "Wakefield",
    ("Sussex County", "mayor", "Wakefield"): "Wakefield",
    ("Sussex County", "town", "Waverly"): "Waverly",
    ("Sussex County", "mayor", "Waverly"): "Waverly",
    # the Town of West Point's school board: the town has a school division
    # of its own, and the results file its board under King William County
    ("King William County", "school", "District 1 (West Point)"): "West Point",
}
TOWN_BODIES = ("town", "mayor", "school")
WARD_WHY = ("the town elects council members by ward, and this map does not draw its wards or "
            "name their members yet")
STALE_WHY = ("the results hold no election to it recent enough for its winners to be still in "
             "office")
# Totals the results list beside the candidates. "Total Ballots Cast" is on 445
# contests (counted 2026-10-30), and before it was listed here it was named
# the 2025 winner of Covington's District 1, a contest whose only votes were
# write-ins and which marks no winner.
NOT_CANDIDATES = {"write-ins", "write-in", "total votes cast", "total ballots cast", "undervotes",
                  "overvotes"}
DISTRICT_TERM = 4

# A seat whose history does not settle who holds it, read from the county's or
# city's own page, or its school division's. (county FIPS, body, district key
# or "" for at large) -> {"members": [{"name", "role"?}], "url", "read", "why",
# "by"?, "note"?}: `by` names whose page it is where that is not the county or
# city (a school division's), and `note` is a sentence the card prints beside
# the names. Each page was read after its host's robots.txt, with this
# builder's client; only names and roles are taken, never a street address or
# a telephone the page prints. `why` is for the reader of this file.
#
# THE AT-LARGE READS (2026-10-30). The results could not settle 36 seats, all
# but two of them a body's at-large seats, and each body's own page was read.
# 25 are named below. Where a page lists its members without saying which sit
# at large (Southampton's school board), the at-large members are the page's
# members whom the results elected at large. Mecklenburg's school board names
# a member for each district, and three differ from the results: Districts 4
# and 5, whose 2023 elections the results give no winner, and District 1,
# whose 2023 winner the page no longer lists; none of the three names is in
# any of the board's results since 2015, so each was seated after its last
# election. Covington's council page, read for its District 1, whose 2025
# election the results give no winner, names interim members in Districts 1
# and 2, so both are named from it. Nine stay unnamed: Charles City's and Mathews's school boards
# (neither page lists its members, and co.charles-city.va.us closed the
# connection on its robots.txt), Danville's school board
# (danvillepublicschools.org answered 404 for its board pages), and the
# councils of Falls Church (robots.txt reset the connection), Hampton,
# Lexington, Roanoke and Staunton (each answered our client 403) and
# Manassas Park (robots.txt disallows every path).
_MECKLENBURG = "https://www.mcpsweb.org/o/mcps/page/school-board-members"
_COVINGTON = "https://covington.va.us/about-covington/city-council.html"
#
# THE TWO-MEMBER CHECK (2026-10-30). The results seat two members in every
# district of eight bodies (two_member above), and each was compared with the
# body's own member list the same day. Wise County's board and Prince George's
# and Newport News's school boards agree in every district that names two.
# Winchester's council agrees in every ward but one name: Second Ward's Emily
# Rose Deangelis, on the 2022 ballot, is Emily Rose Windle on the city's page
# (her page says she married in 2022), so that ward is read by hand. Three
# disagreed, and the results' own reasons say why: Prince George's District 2
# elects three supervisors and three school board members, not two, and
# Poquoson's Eastern and Western districts, and Newport News's South District
# school seats, each showed three current terms. Not compared: Wise County's
# school board (wise.k12.va.us reset every connection from this sandbox,
# robots.txt included) and Newport News's council, whose member list sits on
# nngov.civicweb.net, whose robots.txt disallows every path.
_PG_BOARD = "https://www.princegeorgecountyva.gov/departments/board_of_supervisors/index.php"
_PG_SCHOOL = "https://www.pgs.k12.va.us/board-members"
_POQUOSON = "https://www.poquoson-va.gov/252/City-Council"
_AHPS_NOTE = ("Alleghany County and the City of Covington share one school board, Alleghany "
              "Highlands Public Schools. Its page lists the board's seven members without saying "
              "which of the two places elected each, so the whole board is named for both.")
HAND = {
    ("149", "board", "51149-02"): {
        "members": [{"name": "Philip Pugh", "role": "Vice-Chairman"},
                    {"name": "Scott Hammel"}, {"name": "T. J. Webb"}],
        "url": _PG_BOARD, "read": "2026-10-30",
        "why": "District 2 elects three supervisors; the results showed one seat in 2023 and two "
               "a term before"},
    ("149", "school", "51149-02"): {
        "members": [{"name": "Jill A. Andrews", "role": "Chair"},
                    {"name": "Sherry Taylor"}, {"name": "Jessica Vlkojan"}],
        "url": _PG_SCHOOL, "read": "2026-10-30",
        "why": "District 2 elects three school board members; the results showed one seat in "
               "2023 and two a term before"},
    ("700", "school", "51700-03"): {
        "members": [{"name": "Terri L. Best", "role": "Chairman"},
                    {"name": "Maritsa Alger", "role": "Vice Chairman"}],
        "url": "https://www.nnschools.org/board/members.html", "read": "2026-10-30",
        "why": "the results showed three current terms in South District"},
    ("735", "board", "51735-eastern"): {
        "members": [{"name": "Carey L. Freeman"}, {"name": "Anjie Emmett"}],
        "url": _POQUOSON, "read": "2026-10-30",
        "why": "the results showed three current terms in the Eastern District"},
    ("735", "board", "51735-western"): {
        "members": [{"name": "Debra Bunting", "role": "Vice-Mayor"},
                    {"name": "Jeanne Darby Hubbard"}],
        "url": _POQUOSON, "read": "2026-10-30",
        "why": "the results showed three current terms in the Western District"},
    ("840", "board", "51840-02"): {
        "members": [{"name": "Emily Rose Windle", "role": "Vice-President of Council"},
                    {"name": "Terry L. Sloane"}],
        "url": "https://www.winchesterva.gov/Government/City-Leadership/City-Council-Mayor",
        "read": "2026-10-30",
        "why": "the city names its Second Ward member elected in 2022 by her married name"},
    ("117", "school", "51117-01"): {
        "members": [{"name": "Roger G. Clark"}],
        "by": "Mecklenburg County Public Schools", "url": _MECKLENBURG, "read": "2026-10-30",
        "why": "the page names Roger G. Clark, whom no result names, where the results' last "
               "winner was Lindell T. Palmer in 2023"},
    ("117", "school", "51117-04"): {
        "members": [{"name": "Justin Rose"}],
        "by": "Mecklenburg County Public Schools", "url": _MECKLENBURG, "read": "2026-10-30",
        "why": "the results give no winner for the 2023 election and name Travis Wright in 2024; "
               "the page names Justin Rose"},
    ("117", "school", "51117-05"): {
        "members": [{"name": "Eleesha Chaney"}],
        "by": "Mecklenburg County Public Schools", "url": _MECKLENBURG, "read": "2026-10-30",
        "why": "the results give no winner for the 2023 election"},
    ("580", "board", "51580-01"): {
        "members": [{"name": "David B. Goff", "role": "Interim member"}],
        "url": _COVINGTON, "read": "2026-10-30",
        "why": "the 2025 election's only votes were write-ins, and the results name no winner"},
    ("580", "board", "51580-02"): {
        "members": [{"name": "Stephen Allan Tucker", "role": "Interim member"}],
        "url": _COVINGTON, "read": "2026-10-30",
        "why": "the page names an interim member where the results' last winner was Fred Fenton "
               "Forbes, III in 2022"},
    ("005", "school", ""): {
        "members": [{"name": "Jon Lanford", "role": "Chairman"},
                    {"name": "Jay Woodson", "role": "Vice-Chairman"}, {"name": "Jonathan Arritt"},
                    {"name": "Nicole Clemons"}, {"name": "John Littleton"},
                    {"name": "Danielle Morgan"}, {"name": "Bob Umstead"}],
        "by": "Alleghany Highlands Public Schools",
        "note": _AHPS_NOTE,
        "url": "https://www.ahps.k12.va.us/school_board/current_school_board_members", "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("580", "school", ""): {
        "members": [{"name": "Jon Lanford", "role": "Chairman"},
                    {"name": "Jay Woodson", "role": "Vice-Chairman"}, {"name": "Jonathan Arritt"},
                    {"name": "Nicole Clemons"}, {"name": "John Littleton"},
                    {"name": "Danielle Morgan"}, {"name": "Bob Umstead"}],
        "by": "Alleghany Highlands Public Schools",
        "note": _AHPS_NOTE,
        "url": "https://www.ahps.k12.va.us/school_board/current_school_board_members", "read": "2026-10-30",
        "why": "the results give no winner for the city's 2024 school board election"},
    ("009", "school", ""): {
        "members": [{"name": "David Childress", "role": "Chair"}, {"name": "Jason Childress"}],
        "by": "Amherst County Public Schools",
        "url": "https://www.amherst.k12.va.us/school-board-members", "read": "2026-10-30",
        "why": "its at-large seats are elected in two different years and the results show one "
               "of those elections only once"},
    ("059", "school", ""): {
        "members": [{"name": "Kyle McDaniel", "role": "Vice-Chairman"}, {"name": "Ryan McElveen"},
                    {"name": "Ilryong Moon"}],
        "by": "Fairfax County Public Schools",
        "url": "https://www.fcps.edu/school-board/school-board-members", "read": "2026-10-30",
        "why": "the results showed three at-large seats in 2023 and one a term before"},
    ("113", "board", ""): {
        "members": [{"name": "Carty Yowell", "role": "Chairman"},
                    {"name": "James Jewett", "role": "Vice-Chairman"}, {"name": "Jud Buchanan"},
                    {"name": "Mike Snider"}, {"name": "Nancy Sharman"}],
        "url": "https://www.madisonco.virginia.gov/217/Board-of-Supervisors", "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("115", "board", ""): {
        "members": [{"name": "Janice Hudgins Phillips"}, {"name": "Tim Doss"},
                    {"name": "Tom Bowen", "role": "2026 Chairperson"}, {"name": "David Walsh"},
                    {"name": "Patrick Beattie", "role": "2026 Vice-Chair"}],
        "url": "https://www.mathewscountyva.gov/directory.aspx?did=15", "read": "2026-10-30",
        "why": "the results showed three seats in 2023 and one a term before"},
    ("175", "school", ""): {
        "members": [{"name": "Natalie Dever King"}, {"name": "Michael T. Grizzard"},
                    {"name": "Jayson C. Williams"}],
        "by": "Southampton County Public Schools",
        "url": "https://www.southampton.k12.va.us/about-us/school-board", "read": "2026-10-30",
        "why": "its at-large seats are elected in two different years and the results show one "
               "of those elections only once; the page does not mark which members sit at large,"
               " so these are its members the results elected at large"},
    ("510", "board", ""): {
        "members": [{"name": "Sarah Bagley", "role": "Vice Mayor"}, {"name": "Canek Aguirre"},
                    {"name": "John Chapman"}, {"name": "Abdel-Rahman Elnoubi"},
                    {"name": "Jacinta E. Greene"}, {"name": "Sandy Marks"}],
        "url": "https://www.alexandriava.gov/Council", "read": "2026-10-30",
        "why": "a special election filled one of the seats and the results do not say whose term"
               " it finished"},
    ("530", "board", ""): {
        "members": [{"name": "Danny Staton", "role": "Vice-Mayor"}, {"name": "Michelle Poluikis"},
                    {"name": "Ron Cash"}, {"name": "Amy Gilliam"}, {"name": "Stephanie Noel-Branch"},
                    {"name": "William Kerr", "role": "Appointed 19 February 2026"}],
        "url": "https://buenavistava.gov/government/city-council/city-council-members/", "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("530", "school", ""): {
        "members": [{"name": "Teresa Ellison", "role": "Chairperson"},
                    {"name": "Lisa Kerr", "role": "Vice Chairperson"}, {"name": "Paula Charlton"},
                    {"name": "Mac Felts"}, {"name": "Roy Mohler"}, {"name": "Charles Jolley"},
                    {"name": "Ray Gilbert"}],
        "by": "Buena Vista City Public Schools",
        "url": "https://www.bvcps.net/about_us/school_board", "read": "2026-10-30",
        "why": "the results showed one seat in 2023 and three a term before"},
    ("540", "board", ""): {
        "members": [{"name": "Juandiego Wade", "role": "Mayor"},
                    {"name": "Natalie Oschrin", "role": "Vice Mayor"}, {"name": "Jen Fleisher"},
                    {"name": "Michael Payne"}, {"name": "Lloyd Snook"}],
        "url": "https://charlottesville.gov/677", "read": "2026-10-30",
        "why": "the results showed one seat in 2023 and three a term before"},
    ("540", "school", ""): {
        "members": [{"name": "Lisa Torres", "role": "Board Chair"},
                    {"name": "Amanda Burns", "role": "Vice-Chair"}, {"name": "Zyahna Bryant"},
                    {"name": "Shymora Cooper"}, {"name": "Emily Dooley"}, {"name": "Chris Meyer"},
                    {"name": "Nicole Richardson"}],
        "by": "Charlottesville City Schools",
        "url": "https://charlottesvilleschools.org/schoolboard", "read": "2026-10-30",
        "why": "the results showed one seat in 2023 and four a term before"},
    ("550", "school", ""): {
        "members": [{"name": "Kim Scott", "role": "Chairman"},
                    {"name": "Michael Lamonea", "role": "Vice Chairman"}, {"name": "Amanda Walker"},
                    {"name": "John McCormick"}, {"name": "Amanda Quillin"},
                    {"name": "Angie Swygert"}, {"name": "Norman Pool"}, {"name": "Malia Huddle"},
                    {"name": "Elijah Colon"}],
        "by": "Chesapeake Public Schools",
        "url": "https://www.cpschools.com/o/cps/page/school-board", "read": "2026-10-30",
        "why": "a special election filled one of the seats and the results do not say whose term"
               " it finished; the results name Amanda Walker, elected in 2022, as Amanda Grace "
               "Dean"},
    ("600", "school", ""): {
        "members": [{"name": "Lauren Bartelme"}, {"name": "Kristina Cecere"},
                    {"name": "Amit Hickman"}, {"name": "Sarah Kelsey"}, {"name": "Carolyn Pitches"}],
        "url": "https://www.fairfaxva.gov/Government/Council/All-Elected-Officials", "read": "2026-10-30",
        "why": "the results show the same person winning two of the current seats"},
    ("610", "school", ""): {
        "members": [{"name": "Kathleen Tysse", "role": "School Board Chair"},
                    {"name": "Anne Sherwood", "role": "School Board Vice Chair"},
                    {"name": "MaryKate \"MK\" Hughes"}, {"name": "Bethany Henderson"},
                    {"name": "Jerrod Anderson"}, {"name": "Amie Murphy"}, {"name": "Lori Silverman"}],
        "by": "Falls Church City Public Schools",
        "url": "https://www.fccps.org/page/school-board", "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("640", "board", ""): {
        "members": [{"name": "Beth White", "role": "Mayor"},
                    {"name": "Willie Greene", "role": "Vice Mayor"}, {"name": "Sharon Ritchie"},
                    {"name": "Martin Warr"}, {"name": "Evan Henck"}, {"name": "Kathy Burnett"},
                    {"name": "Shane Coomes"}],
        "url": "https://galaxva.com/galax-city-council/", "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("660", "school", ""): {
        "members": [{"name": "Tim Howley"}, {"name": "Matt Snyder", "role": "Vice Chair"},
                    {"name": "Andrew Kohen"}, {"name": "Kristen Loflin"}, {"name": "Emma Phillips"},
                    {"name": "Kaylene Seigle"}],
        "by": "Harrisonburg City Public Schools",
        "url": "https://www.harrisonburg.k12.va.us/District/1125-School-Board.html", "read": "2026-10-30",
        "why": "the results showed three seats in 2024 and one a term before; the page calls two"
               " members Chair, so no role is given for either"},
    ("690", "board", ""): {
        "members": [{"name": "LC Jones", "role": "Mayor"},
                    {"name": "Kathy C. Lawson", "role": "Vice Mayor"}, {"name": "Aaron Rawls"},
                    {"name": "Rayshaun Gravely"}, {"name": "Julian Mei"}],
        "url": "https://www.martinsville-va.gov/285/City-Council", "read": "2026-10-30",
        "why": "the results showed three seats in 2024 and one a term before"},
    ("740", "school", ""): {
        "members": [{"name": "Cardell C. Patillo, Jr.", "role": "Chair"},
                    {"name": "Melvin Cotton, Jr.", "role": "Vice-Chair"},
                    {"name": "LaKeesha S. \"Klu\" Atkinson"}, {"name": "Irene S. Boone"},
                    {"name": "Quniana D. Futrell"}, {"name": "Arnette D. McSwain"},
                    {"name": "Lateacia A. Sessoms"}, {"name": "Tamara L. Shewmake"},
                    {"name": "Jaclyn T. \"Jackie\" Walker"}],
        "by": "Portsmouth Public Schools",
        "url": "https://www.ppsk12.us/page/school-board", "read": "2026-10-30",
        "why": "a special election filled one of the seats and the results do not say whose term"
               " it finished"},
    ("750", "board", ""): {
        "members": [{"name": "Seth Gillespie", "role": "Vice-Mayor"}, {"name": "Kellie Artrip"},
                    {"name": "Jessie Foster"}, {"name": "Guy Wohlford"}],
        "url": "https://www.radfordva.gov/179/City-Council", "read": "2026-10-30",
        "why": "the results showed four seats in 2022 and two a term before"},
    ("750", "school", ""): {
        "members": [{"name": "Gloria Boyd", "role": "Chairperson"},
                    {"name": "Jane Swing", "role": "Vice-Chairperson"}, {"name": "Chris Calfee"},
                    {"name": "Brian Dobbins"}, {"name": "Amanda Winter"}],
        "by": "Radford City Public Schools",
        "url": "https://www.rcps.org/division_information/school_board", "read": "2026-10-30",
        "why": "the results showed two seats in 2024 and one a term before"},
    ("775", "board", ""): {
        "members": [{"name": "Renée Turk", "role": "Mayor"},
                    {"name": "Anne Marie Green", "role": "Vice Mayor"},
                    {"name": "Byron \"Randy\" Foley"}, {"name": "Hunter Holliday"},
                    {"name": "Joe Foley"}],
        "url": "https://www.salemva.gov/458/Council", "read": "2026-10-30",
        "why": "the results showed one seat in 2024 and three a term before"},
    ("810", "school", ""): {
        "members": [{"name": "Sharon Felton"}],
        "by": "Virginia Beach City Public Schools",
        "url": "https://schoolboard.vbschools.com/board", "read": "2026-10-30",
        "why": "the results showed one at-large seat in 2024 and two a term before"},
    ("830", "board", ""): {
        "members": [{"name": "Douglas G. Pons", "role": "Mayor"},
                    {"name": "W. Pat Dent", "role": "Vice Mayor"}, {"name": "Barbara L. Ramsey"},
                    {"name": "Stacy Kern-Scheerer"}, {"name": "Ayanna T. Williams"}],
        "url": "https://www.williamsburgva.gov/369/City-Council", "read": "2026-10-30",
        "why": "the results showed three seats in 2024 and one a term before"},
    ("840", "school", ""): {
        "members": [{"name": "Mary Tedrow"}, {"name": "Melissa Harris"}, {"name": "Kylie Zoller"}],
        "by": "Winchester Public Schools",
        "url": "https://www.wps.k12.va.us/school-board/meet-our-school-board", "read": "2026-10-30",
        "why": "its at-large seats are elected in two different years and the results show one "
               "of those elections only once"},

    # TOWNS, keyed by the town's name. Read on 2026-10-30 from each town's own
    # page, for the larger towns whose results do not settle the council
    # (and Luray's, whose page names a member the results cannot: one seat
    # was filled by appointment). Where the town's charter makes its mayor
    # one of the council's members, or the council chooses the mayor from
    # among them (Abingdon, Ashland, Bedford, Smithfield), the mayor is
    # listed with the council, as the page lists them; elsewhere the mayor is
    # elected on a ballot of their own and is named under "mayor". Not read:
    # Leesburg, Herndon and Lovettsville (each page answered 403), Front
    # Royal (no member list found on its own site), and Grottoes and West
    # Point (their robots.txt could not be read from here).
    ("Abingdon", "town", ""): {
        "members": [{"name": "Dwyane Anderson", "role": "Mayor"},
                    {"name": "Wayne Austin", "role": "Vice Mayor"}, {"name": "Donna Quetsch"},
                    {"name": "Derek Webb"}, {"name": "Amanda Pillion"}],
        "url": "https://www.abingdon-va.gov/page/town-council", "read": "2026-10-30",
        "why": "the results showed three seats in 2022 and two a term before"},
    ("Altavista", "town", ""): {
        "members": [{"name": "Wayne Mitchell", "role": "Vice Mayor"}, {"name": "Tracy Emerson"},
                    {"name": "Timothy George"}, {"name": "Scott Lowman"},
                    {"name": "Victoria Mattox"}, {"name": "Gary Penn"}],
        "url": "https://www.altavistava.gov/government/town_officials/index.php",
        "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("Ashland", "town", ""): {
        "members": [{"name": "Steve Trivett", "role": "Mayor"},
                    {"name": "Daniel McGraw", "role": "Vice Mayor"}, {"name": "Anita Barnhart"},
                    {"name": "Pamela Sopall"}, {"name": "Drew Molloy"}],
        "url": "https://www.ashlandva.gov/91/Ashland-Town-Council", "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("Bedford", "town", ""): {
        "members": [{"name": "C. G. Stanley", "role": "Mayor"},
                    {"name": "Darryl A. Updike", "role": "Vice Mayor"}, {"name": "Stacey Hailey"},
                    {"name": "Todd Foreman"}, {"name": "Jai Ippolito"}, {"name": "Dave Foster"},
                    {"name": "Dwight Evans"}],
        "url": "https://www.bedfordva.gov/1197/Town-Council", "read": "2026-10-30",
        "why": "a special election filled one of its seats"},
    ("Bridgewater", "town", ""): {
        "members": [{"name": "A. Fontaine Canada", "role": "Vice Mayor"},
                    {"name": "Travis Bowman"}, {"name": "Steven A. Schofield"},
                    {"name": "Stephanie Curtis"}, {"name": "Jim Tongue"}, {"name": "Bill Kyger"}],
        "url": "https://www.bridgewater.town/town_hall/town_council/index.php",
        "read": "2026-10-30",
        "why": "the results showed six seats in the four years to 2024 and seven before"},
    ("Broadway", "town", ""): {
        "members": [{"name": "Travis M. Driver", "role": "Vice Mayor"}, {"name": "Richard Fulk"},
                    {"name": "Joan H. Shifflett"}, {"name": "Tristan J. Sinnett"},
                    {"name": "Douglas W. Harpine"}, {"name": "Elizabeth \"Liz\" M. Fawley"}],
        "url": "https://broadwayva.gov/town-council/", "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("Broadway", "mayor", ""): {
        "members": [{"name": "Dave Jordan", "role": "Mayor"}],
        "url": "https://broadwayva.gov/town-council/", "read": "2026-10-30",
        "why": "the results hold no election to it recent enough for its winner to be still in "
               "office"},
    ("Culpeper", "town", ""): {
        "members": [{"name": "Joe Short", "role": "Vice Mayor"}, {"name": "Jamie Dyke"},
                    {"name": "Michael T. Olinger"}, {"name": "Pranas A. Rimeikis"},
                    {"name": "Jon D. Russell"}, {"name": "Janie Schmidt"},
                    {"name": "Max B. Sternberg"}, {"name": "William M. \"Bill\" Yowell"}],
        "url": "https://www.culpeperva.gov/government/mayor_and_council/town_council_bios/index.php",
        "read": "2026-10-30",
        "why": "its seats are elected in two different years and the results show one of those "
               "elections only once"},
    ("Elkton", "town", ""): {
        "members": [{"name": "Phillip \"Rick\" Workman", "role": "Vice Mayor"},
                    {"name": "Virginia Fulginiti"}, {"name": "Aaron Napotnik"},
                    {"name": "Rachel Michael"}, {"name": "Jan Hensley"}, {"name": "Louis Heidel"}],
        "url": "https://www.elktonva.gov/government/council/index.php", "read": "2026-10-30",
        "why": "the results showed three seats in 2022 and four a term before"},
    ("Lebanon", "town", ""): {
        "members": [{"name": "J. Leonard Kegley"}, {"name": "Scott Gilmer"},
                    {"name": "M. Elijah Leonard"}, {"name": "Nina Fields"},
                    {"name": "DeAnna Jackson"}, {"name": "W. Bradley Lambert"}],
        "url": "https://lebanonva.net/government/council/", "read": "2026-10-30",
        "why": "a special election filled one of its seats"},
    ("Luray", "town", ""): {
        "members": [{"name": "Ron Vickers", "role": "Vice Mayor"}, {"name": "Jerry Dofflemyer"},
                    {"name": "Joey Sours"}, {"name": "Jason Pettit"},
                    {"name": "Charles Allen Butler, Jr."}, {"name": "Ryan Dean"}],
        "url": "https://www.townofluray.com/government/town-council", "read": "2026-10-30",
        "why": "the page names Ryan Dean, appointed to a seat whose elected member the results "
               "still name"},
    ("Marion", "town", ""): {
        "members": [{"name": "Jim Gates", "role": "Vice Mayor"}, {"name": "Suzanne Jennings"},
                    {"name": "Tricia Spencer"}, {"name": "Hunter Atwell"}, {"name": "Todd May"},
                    {"name": "Larry Carter"}, {"name": "Debra Hayes"}],
        "url": "https://www.marionva.org/1426/Mayor-Town-Council", "read": "2026-10-30",
        "why": "a special election filled one of its seats"},
    ("Purcellville", "town", ""): {
        "members": [{"name": "Erin Rayner"}, {"name": "Carol Luke"}, {"name": "Kevin Wright"},
                    {"name": "Caleb Stought"}, {"name": "Brian Dean"}],
        "url": "https://www.purcellvilleva.gov/524/Council-Bios", "read": "2026-10-30",
        "note": ("The town's page lists five council members. Its charter gives the council six "
                 "members besides the mayor, so one seat is not named here."),
        "why": "a special election filled one of its seats"},
    ("Smithfield", "town", ""): {
        "members": [{"name": "Michael G. Smith", "role": "Mayor"},
                    {"name": "Bill Harris", "role": "Vice Mayor"}, {"name": "Steven G. Bowman"},
                    {"name": "Valerie Butler"}, {"name": "Jeff Brooks"}, {"name": "Darren Cutler"},
                    {"name": "Mary Ellen Bebermeyer"}],
        "url": "https://www.smithfieldva.gov/287/Town-Council", "read": "2026-10-30",
        "why": "the results showed four seats in 2022 and one a term before"},
}

# A results label the matcher cannot place by number or name, mapped by hand:
# (county FIPS, label) -> district key, or None for a label that is not a
# district of the layer (a body's at-large seats written as a district).
LABEL_MAP = {}

# A results label under a county's name that is another body's seat: (county
# FIPS, body, label) -> why it is left out. Each entry must match a label in
# the results, or the build stops.
SKIP_LABELS = {}

WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
         "seven": "7", "eight": "8", "nine": "9", "ten": "10", "first": "1",
         "second": "2", "third": "3", "fourth": "4", "fifth": "5", "sixth": "6",
         "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10"}
ABBREV = {"n": "north", "s": "south", "e": "east", "w": "west", "mt": "mount", "st": "saint"}
DROP = {"district", "ward", "magisterial", "election", "borough", "the", "of", "dist", "ed", "no"}


def fail(msg):
    raise SystemExit("build_va_local_officials: FATAL: " + msg)


# ---------- fetch ----------
def fetch(today, offices=None, label="build_va_local_officials"):
    """Every contest for `offices` (the results' office ids, OFFICES by
    default) from FIRST_YEAR to today's year. The conservation boards'
    builder asks for its own office through this one reader."""
    import requests  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415

    require_robots_once(API, USER_AGENT, label=label)
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    contests = {}
    last = 0.0
    for year in range(FIRST_YEAR, today.year + 1):
        for office in (offices or OFFICES):
            page = 1
            while True:
                wait = PACE - (time.time() - last)
                if wait > 0:
                    time.sleep(wait)
                filters = {"global": {"years": {"from": year, "to": year}},
                           "ballotQuestions": {"text": "", "types": [], "number": "", "divisions": []},
                           "contests": {"candidates": [], "divisions": [], "offices": [{"id": int(office)}]},
                           "specialElectionsOnly": False, "voterStats": False, "stages": []}
                body = json.dumps({"query": QUERY, "variables": {"f": filters, "p": {"page": page, "size": PAGE}}})
                for attempt in range(3):
                    try:
                        r = s.post(API, data=body, timeout=120)
                        last = time.time()
                        r.raise_for_status()
                        data = r.json()
                        break
                    except Exception as e:  # noqa: BLE001
                        if attempt == 2:
                            fail("the results site did not answer for %d office %s page %d: %s"
                                 % (year, office, page, e))
                        time.sleep(5 * (attempt + 1))
                if data.get("errors"):
                    fail("the results site answered an error for %d office %s: %s"
                         % (year, office, data["errors"]))
                res = data["data"]["search"]["results"]
                for c in res:
                    contests[c["id"]] = c
                if len(res) < PAGE:
                    break
                page += 1
        print("%d: %d contests so far" % (year, len(contests)), file=sys.stderr)
    return {"fetched": today.isoformat(), "api": API, "contests": contests}


# ---------- reading one contest ----------
def spelled(name):
    """A candidate's name as the results print it, with runs of spaces made
    one and a stray trailing comma dropped ("Thomas R "Tommy" Elliott,")."""
    return re.sub(r"\s+", " ", name).strip().rstrip(",").strip()


def winners(c):
    """(names, how): the contest's winners, None for a seat won by write-in
    votes, or ([], why) when the result does not say."""
    cands = c.get("candidates") or []
    marked = [x for x in cands if x.get("isWinner")]
    if marked:
        return [None if x["displayName"].strip().lower() in NOT_CANDIDATES else spelled(x["displayName"])
                for x in marked], "marked"
    real = [x for x in cands if x["displayName"].strip().lower() not in NOT_CANDIDATES
            and x.get("nVotes") is not None]
    if not real:
        return [], "no candidate"
    real.sort(key=lambda x: -x["nVotes"])
    n = c.get("nSeats") or 1
    if len(real) > n and real[n - 1]["nVotes"] == real[n]["nVotes"]:
        return [], "a tie at the last seat"
    return [spelled(x["displayName"]) for x in real[:n]], "most votes"


def read_contest(c):
    office = (c.get("office") or {}).get("id")
    div = c.get("division") or {}
    if office not in OFFICES or not div.get("name"):
        return None
    if "primary" in (c.get("eventTypeDisplayName") or "").lower():
        return None
    date = datetime.date.fromisoformat(c["event"]["startDate"][:10])
    loc, _, label = div["name"].strip().partition(" - ")
    label = re.sub(r"\s+", " ", label.replace("\x08", "")).strip()
    if label.lower() in ("at large", "at-large"):
        label = ""
    names, how = winners(c)
    return {
        "id": c["id"], "date": date, "loc": loc.strip(), "town": div.get("divisionTypeName") == "Town",
        "body": OFFICES[office], "label": label, "seats": c.get("nSeats") or 1,
        "special": bool(c.get("isSpecial")) or "special" in (c.get("eventTypeDisplayName") or "").lower(),
        "event": (c.get("eventTypeDisplayName") or "").strip(), "winners": names, "how": how,
    }


def locality_fips(loc, by_name):
    n = loc.upper()
    if not (n.endswith(" CITY") or n.endswith(" COUNTY")):
        n = {"ISLE OF WIGHT": "ISLE OF WIGHT COUNTY"}.get(n, n + " CITY")
    return by_name.get(n)


# ---------- composing one seat group ----------
SUFFIX = {"jr", "sr", "ii", "iii", "iv", "v"}


def person_key(name):
    n = re.sub(r'"[^"]*"', " ", name or "")
    n = re.sub(r"\([^)]*\)", " ", n)
    toks = [t for t in re.split(r"[\s,.]+", n.lower()) if t and t not in SUFFIX]
    return (toks[-1], toks[0][0]) if toks else (name or "").lower()


def takes_office(x):
    # November winners take office on 1 January; the few May elections the
    # results still hold (before 2022) took office on 1 July.
    if x["date"].month >= 11:
        return datetime.date(x["date"].year + 1, 1, 1)
    if x["special"]:
        return x["date"]
    return datetime.date(x["date"].year, 7, 1)


def term_of(xs, at_large):
    # A Virginia county's or city's governing body and school board serve
    # four-year terms. A mayor's or a chair's term, and a town council's
    # (many towns elect the whole council every two years), are read from the
    # group's own history: the commonest gap between one person's
    # re-elections. A town council's gaps count only at two and four years,
    # because the move of town elections from May to November in 2022 put
    # three years between some members' elections, and a three-year term is
    # no town's.
    town = bool(xs) and xs[0]["body"] == "town"
    if not at_large or not xs or (xs[0]["body"] not in SINGLE_SEAT_BODIES and not town):
        return DISTRICT_TERM
    regs = [x for x in xs if not x["special"]]
    if town:
        # A town's terms are read from its last three regular elections
        # only: Kenbridge re-elected a member two years on in 2016, 2018 and
        # 2020 and has elected three of its six members every two years for
        # four-year terms since its 2019 charter change, so its older history
        # would name half its council as the whole of it.
        recent = sorted({x["date"].year for x in regs})[-3:]
        regs = [x for x in regs if x["date"].year in recent]
    gaps = collections.Counter()
    seen = collections.defaultdict(list)
    for x in regs:
        for w in x["winners"]:
            if w:
                seen[person_key(w)].append(x["date"].year)
    for ys in seen.values():
        ys = sorted(set(ys))
        for a, b in zip(ys, ys[1:]):
            if b - a in ((2, 4) if town else (2, 3, 4)):
                gaps[b - a] += 1
    if town:
        # one member re-elected two years on is not enough to say the whole
        # council serves two-year terms: a member elected to the last two
        # years of a seat does the same
        return 2 if gaps[2] >= 2 and gaps[2] > gaps[4] else DISTRICT_TERM
    if gaps:
        top = gaps.most_common()
        if len(top) == 1 or top[0][1] > top[1][1]:
            return top[0][0]
    years = sorted({x["date"].year for x in regs if x["seats"] == 1})
    eg = collections.Counter(b - a for a, b in zip(years, years[1:]) if b - a in (2, 3, 4))
    if eg:
        top = eg.most_common()
        if len(top) == 1 or top[0][1] > top[1][1]:
            return top[0][0]
    return DISTRICT_TERM


def member(x, name):
    return {"name": name, "elected": x["date"].isoformat(),
            "election": "special" if x["special"] else "regular", "contest": x["id"]}


SINGLE_SEAT_BODIES = ("mayor", "chair", "school-chair")


def latest_first(xs):
    # On one day a special election for the weeks left of a term and the
    # regular election for the next term can both be held for one seat; the
    # regular one's winner is the one sitting after 1 January, so it sorts last.
    return sorted(xs, key=lambda x: (x["date"], not x["special"]))


def compose(xs, today, two=False):
    """{"members": [...], "pending": [...]} or {"unsettled": why} or
    {"obsolete": True} for one group of contests: one body's seat or seats in
    one district, or its seats at large. `two` says the locality elects two
    members from every district of this body, in alternate years."""
    xs = latest_first(xs)
    unread = [x for x in xs if not x["winners"]]
    xs = [x for x in xs if x["winners"]]
    at_large = (xs or unread)[0]["label"] == ""
    T = term_of(xs, at_large)
    held = [x for x in xs if takes_office(x) > today]
    past = [x for x in xs if takes_office(x) <= today]
    regs = [x for x in past if not x["special"]]
    years = [x["date"].year for x in regs]

    def anchored(x):
        return any(abs(x["date"].year - y) in (T, 2 * T) for y in years)

    def in_office(x):
        start = takes_office(x)
        return start <= today < datetime.date(start.year + T, start.month, start.day)

    out = {"term": T, "pending": [member(x, w) for x in held for w in x["winners"]]}
    if any(not x["special"] and in_office(x) for x in unread):
        out["unsettled"] = ("the state's election results do not give the winner of the most "
                            "recent election to it")
        return out
    if not past:
        out["obsolete"] = True
        return out
    single = (not at_large and not two) or (
        at_large and (xs[0]["body"] in SINGLE_SEAT_BODIES or all(x["seats"] == 1 for x in past)
                      and len({x["date"].year % T for x in regs if in_office(x)}) <= 1))
    if single:
        latest = past[-1]
        if latest["special"]:
            if latest["date"].year < today.year - T:
                out["obsolete"] = True
                return out
        elif not in_office(latest):
            out["obsolete"] = True
            return out
        out["members"] = dedupe([member(latest, w) for w in latest["winners"]])
        return out
    live = [x for x in regs if in_office(x)]
    if not live:
        if any(x["special"] and x["date"].year >= today.year - T for x in past):
            out["unsettled"] = ("a special election has been held since the last regular "
                                "election, and the results do not say which seat it filled")
        else:
            out["obsolete"] = True
        return out
    classes = {}
    for x in live:
        classes[x["date"].year % T] = x      # live is oldest first, so the latest wins
    chosen = sorted(classes.values(), key=lambda x: x["date"])
    if two and len(chosen) != 2:
        out["unsettled"] = ("the district elects two members in different years, and the "
                            "results show %d current terms rather than two" % len(chosen))
        return out
    if (len(chosen) > 1 and all(x["seats"] == 1 for x in chosen)
            and len({person_key(w) for x in chosen for w in x["winners"] if w}) == 1):
        chosen = chosen[-1:]          # one person re-elected early: one seat
    if len(chosen) > 1 and any(not anchored(x) for x in chosen):
        out["unsettled"] = ("its seats are elected in two different years, and the results "
                            "show only one election in one of those years, so it is not "
                            "clear which seats are still current")
        return out
    for x in chosen:
        before = [y for y in regs if y["date"].year == x["date"].year - T]
        if before and sum(y["seats"] for y in before) != x["seats"]:
            n, m = x["seats"], sum(y["seats"] for y in before)
            out["unsettled"] = ("%d %s on the ballot in %d and %d a term before, so the "
                                "number of seats seems to have changed"
                                % (n, "seat was" if n == 1 else "seats were", x["date"].year, m))
            return out
    specials = [x for x in past if x["special"] and x["date"] > chosen[0]["date"]]
    if specials:
        out["unsettled"] = ("a special election filled one of the seats, and the results do "
                            "not say whose term it finished")
        return out
    members = dedupe([member(x, w) for x in chosen for w in x["winners"]])
    if len(members) < sum(x["seats"] for x in chosen):
        out["unsettled"] = "the results show the same person winning two of the current seats"
        return out
    out["members"] = members
    return out


def dedupe(members):
    seen = set()
    out = []
    for m in reversed(members):        # the latest spelling of a name wins
        k = person_key(m["name"]) if m["name"] else id(m)
        if k not in seen:
            seen.add(k)
            out.append(m)
    return list(reversed(out))


def two_member(groups_for_body, today):
    """True when every district of one body in one locality has regular
    contests in office in two different years, each repeated a term earlier
    or later, won by different people: Wise County's supervisors, elected two
    to a district in alternate years. One district showing it alone is a seat
    filled for an unexpired term (Clarke County's Berryville District, 2020
    and 2024), not a second member."""
    if len(groups_for_body) < 2:
        return False
    for xs in groups_for_body:
        regs = [x for x in xs if x["winners"] and not x["special"] and takes_office(x) <= today]
        years = [x["date"].year for x in regs]
        live = [x for x in regs if takes_office(x) <= today <
                datetime.date(takes_office(x).year + DISTRICT_TERM, takes_office(x).month, 1)]
        anchored = [x for x in live if any(abs(x["date"].year - y) in (4, 8) for y in years)]
        people = {person_key(w) for x in anchored for w in x["winners"] if w}
        if len({x["date"].year for x in anchored}) < 2 or len(people) < 2:
            return False
    return True


FAMILIES = (("board", "chair", "mayor"), ("school", "school-chair"), ("town", "mayor"))


def hand_seat(hand):
    seat = {"members": hand["members"], "verified": {"url": hand["url"], "read": hand["read"]}}
    for k in ("by", "note"):
        if hand.get(k):
            seat["verified"][k] = hand[k]
    return seat


# ---------- towns ----------
def fetch_towns(today):
    """Virginia's towns from the Census's own list, the one the City or Town
    layer draws: GEOID, name and the Census's internal point of each."""
    import requests  # noqa: PLC0415
    from scraper_common import require_robots_once  # noqa: PLC0415

    url = TOWNS_URL + "/query"
    require_robots_once(url, USER_AGENT, label="build_va_local_officials")
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120, params={
        "where": "STATE='51' AND LSADC='43'", "outFields": "GEOID,BASENAME,INTPTLAT,INTPTLON",
        "returnGeometry": "false", "orderByFields": "GEOID", "f": "json"})
    r.raise_for_status()
    data = r.json()
    if data.get("error") or data.get("exceededTransferLimit"):
        fail("TIGERweb did not list Virginia's towns: %s" % (data.get("error") or "truncated"))
    towns = [{"geoid": a["GEOID"], "name": a["BASENAME"], "lat": float(a["INTPTLAT"]),
              "lng": float(a["INTPTLON"])} for a in (f["attributes"] for f in data["features"])]
    if len(towns) < TOWN_FLOOR:
        fail("TIGERweb listed %d towns, fewer than %d" % (len(towns), TOWN_FLOOR))
    if len({t["name"] for t in towns}) != len(towns):
        fail("two of Virginia's towns share a name, and the card finds a town by its name")
    return {"fetched": today.isoformat(), "source": TOWNS_URL, "towns": towns}


def load_towns():
    with open(TOWNS_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def town_of(r, names_upper, by_name):
    """(town, label) when a contest is a town's, else None. A town's results
    are filed under its own name, sometimes with its county in brackets
    (a town in two counties is reported as two parts), sometimes upper-cased
    or with a ward's precinct code after it ("HILLSVILLE 1250A"), and a few
    under their county with the town as the label (TOWN_ROUTES)."""
    route = TOWN_ROUTES.get((r["loc"], r["body"], r["label"]))
    if route:
        return route, ""
    if r["body"] not in TOWN_BODIES:
        return None
    if not r["town"] and locality_fips(r["loc"], by_name) is not None:
        return None
    n = re.sub(r"\s*\([^)]*\bCounty\)$", "", r["loc"]).strip()
    label = r["label"]
    m = re.match(r"(?i)^(.*?)\s+(?:ward\s+)?(\d{4}[a-z])$", n)
    if m:
        n, label = m.group(1), "Ward " + m.group(2)
    if re.match(r"(?i)^at large\b", label):
        label = ""
    name = TOWN_ALIAS.get(n.upper()) or names_upper.get(n.upper())
    return (name, label) if name else None


def town_cycle_changed(xs, term, members):
    """Why a town council's named members cannot be its whole council, or
    None. The regular contests of the latest term (the `term` years up to the
    latest regular election) must hold as many seats as those of the term
    before it: a council of five that elected everyone in 2022 and one
    member in 2025 has not shrunk to one, and naming the one would read as
    the whole council."""
    regs = [x for x in xs if not x["special"] and x["winners"]]
    if not regs:
        return None
    last = max(x["date"].year for x in regs)

    def seats(top):
        return sum(x["seats"] for x in regs if top - term < x["date"].year <= top)
    now, before = seats(last), seats(last - term)
    if before and before != now:
        return ("%d %s on the ballot in the %d years to %d and %d in the %d years before, so the "
                "number of seats seems to have changed"
                % (now, "seat was" if now == 1 else "seats were", term, last, before, term))
    return None


def merge_town_parts(recs, contests):
    """A town in two counties has each contest reported once per county
    until 2023. Parts that name the same winners are one contest. Parts that
    disagree are summed when they are one contest (the same seats and the
    same candidates), since the town's winners are its voters' totals; parts
    that differ in their seats or candidates are left unread."""
    g = collections.defaultdict(list)
    for r in recs:
        g[(r["town_name"], r["body"], r["label"], r["date"], r["special"])].append(r)
    out, split = [], 0
    for key, xs in sorted(g.items(), key=lambda kv: str(kv[0])):
        if len({x["part"] for x in xs}) < 2:
            out.extend(xs)
            continue
        split += 1
        named = [x for x in xs if x["winners"]]
        if len(named) == 1 or len({tuple(sorted(person_key(w) for w in x["winners"] if w))
                                   for x in named}) == 1:
            out.append(max(named or xs, key=lambda x: x["seats"]))
            continue

        def cands(x):
            return frozenset(person_key(c["displayName"]) for c in contests[x["id"]]["candidates"]
                             if c["displayName"].strip().lower() not in NOT_CANDIDATES)
        if len({x["seats"] for x in xs}) > 1 or len({cands(x) for x in xs}) > 1:
            out.append(dict(xs[0], winners=[], how="the two counties' parts differ"))
            continue
        votes, spelt = collections.Counter(), {}
        for x in xs:
            for c in contests[x["id"]]["candidates"]:
                if c["displayName"].strip().lower() in NOT_CANDIDATES:
                    continue
                k = person_key(c["displayName"])
                votes[k] += c.get("nVotes") or 0
                spelt[k] = spelled(c["displayName"])
        top = votes.most_common()
        n = xs[0]["seats"]
        if len(top) > n and top[n - 1][1] == top[n][1]:
            out.append(dict(xs[0], winners=[], how="a tie at the last seat"))
            continue
        out.append(dict(xs[0], winners=[spelt[k] for k, _ in top[:n]], how="the parts summed"))
    return out, split


def moved_on(entry, report):
    """A person who won one seat and later another on the same body (a
    council member elected mayor, as Roanoke's and Blacksburg's were) sits in
    the later seat only, so the earlier one is left to the results' next
    winner and names no one in the meantime."""
    for family in FAMILIES:
        seats = []
        for body in family:
            a = (entry["bodies"].get(body) or {}).get("atLarge")
            if a and a.get("members"):
                seats.append(a)
            for d in entry.get("districts", {}).values():
                s = (d.get("seats") or {}).get(body)
                if s and s.get("members"):
                    seats.append(s)
        # A seat read by hand from the body's own page is current by
        # definition: its members outrank every result and are never moved.
        def when(seat, m):
            return "9999-12-31" if seat.get("verified") else m["elected"]
        latest = {}
        for seat in seats:
            for m in seat["members"]:
                k = person_key(m["name"]) if m["name"] else None
                if k and (k not in latest or when(seat, m) > latest[k]):
                    latest[k] = when(seat, m)
        for seat in seats:
            if seat.get("verified"):
                continue
            keep = [m for m in seat["members"]
                    if not m["name"] or m["elected"] >= latest[person_key(m["name"])]]
            if len(keep) != len(seat["members"]):
                gone = [m for m in seat["members"] if m not in keep]
                seat["members"] = keep
                seat["left"] = [{"name": m["name"], "elected": m["elected"]} for m in gone]
                report["moved to another seat"] += len(gone)
                print("MOVED ON %s: %s" % (entry["name"], [m["name"] for m in gone]), file=sys.stderr)


# ---------- matching a label to a district ----------
def norm(s):
    s = re.sub(r"\([^)]*\)", " ", s.lower()).replace("&", " and ")
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)
    toks = [t for t in re.split(r"[^a-z0-9]+", s) if t]
    toks = [ABBREV.get(WORDS.get(t, t), WORDS.get(t, t)) for t in toks]
    toks = [(t.lstrip("0") or "0") if t.isdigit() else t for t in toks]
    return " ".join(t for t in toks if t not in DROP)


def lev(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (ca != cb))
    return d[-1]


def match_labels(fips, labels, ds, extra):
    """label -> district key for one locality, or None for a label that is no
    district of the layer. `ds` is the locality's districts, `extra` further
    districts read from elsewhere (Norfolk's superwards)."""
    allds = collections.OrderedDict(ds)
    allds.update(extra)
    by_num = {}
    by_name = {}
    for key, e in allds.items():
        if e.get("number"):
            by_num.setdefault(norm(e["number"]), []).append(key)
        by_name.setdefault(norm(e["name"]), []).append(key)
    out = {}
    for lab in labels:
        if (fips, lab) in LABEL_MAP:
            out[lab] = LABEL_MAP[(fips, lab)]
            continue
        n = norm(lab)
        hit = by_name.get(n) or by_num.get(n)
        if not hit and len(n) > 4:
            hit = [k for nm, ks in by_name.items() for k in ks if lev(nm, n) <= 2]
        out[lab] = hit[0] if hit and len(hit) == 1 else None
    return out


# ---------- building ----------
def build(source, today, precincts_path=vl.PRECINCTS):
    locs = vl.load_localities()
    by_name = {}
    for fips, e in locs.items():
        by_name[(e["name"] + (" CITY" if e["kind"] == "city" else "")).upper()] = fips
    feats = vl.load_precincts(precincts_path)
    ds_all = vl.districts(feats)
    extra = {vl.NORFOLK: collections.OrderedDict(
        ("51710-superward-%d" % n, {"number": None, "name": "Superward %d" % n}) for n in (6, 7))}

    recs = [r for r in (read_contest(c) for c in source["contests"].values()) if r]
    groups = collections.defaultdict(list)
    town_list = load_towns()
    names_upper = {t["name"].upper(): t["name"] for t in town_list["towns"]}
    town_recs = []
    routed = set()
    skipped = set()
    for r in recs:
        if r["date"] > today:
            continue
        got = town_of(r, names_upper, by_name)
        if got:
            if (r["loc"], r["body"], r["label"]) in TOWN_ROUTES:
                routed.add((r["loc"], r["body"], r["label"]))
            town_recs.append(dict(r, town_name=got[0], label=got[1],
                                  part=r["loc"] + " | " + r["label"]))
            continue
        if r["town"]:
            continue
        fips = locality_fips(r["loc"], by_name)
        if fips is None:
            continue
        body = r["body"]
        if body == "town":
            continue
        if (fips, body, r["label"]) in SKIP_LABELS:
            skipped.add((fips, body, r["label"]))
            continue
        groups[(fips, body, r["label"])].append(r)

    problems = ["SKIP_LABELS names %r, which no contest in the results carries" % (k,)
                for k in sorted(set(SKIP_LABELS) - skipped)]
    problems += ["TOWN_ROUTES names %r, which no contest in the results carries" % (k,)
                 for k in sorted(set(TOWN_ROUTES) - routed)]
    report = collections.Counter()
    out = {}
    fixed = set()
    for fips in sorted(locs):
        e = locs[fips]
        entry = {"name": e["name"], "kind": e["kind"], "bodies": {}, "districts": collections.OrderedDict()}
        ds = ds_all.get(fips, collections.OrderedDict())
        labels = {lab for (f, b, lab) in groups if f == fips and lab}
        lmap = match_labels(fips, labels, ds, extra.get(fips, {}))
        # a district name va_localities corrects must be the name the results
        # give that district, or the correction is a guess
        for lab, key in lmap.items():
            d = ds.get(key) if key else None
            if d and d.get("number") and (fips, d["number"]) in vl.NAME_FIX:
                fixed.add((fips, d["number"]))
                if norm(lab) != norm(vl.NAME_FIX[(fips, d["number"])]):
                    problems.append("%s: va_localities names district %s %r and the results "
                                    "call it %r" % (e["name"], d["number"],
                                                    vl.NAME_FIX[(fips, d["number"])], lab))
        composed = {}
        twos = {}
        for body in ("board", "school"):
            mine = [xs for (f, b, lab), xs in groups.items()
                    if f == fips and b == body and lab and lmap.get(lab)]
            twos[body] = two_member(mine, today)
            if twos[body]:
                report["two-member bodies"] += 1
                print("TWO PER DISTRICT %s %s" % (e["name"], body), file=sys.stderr)
        for (f, body, lab), xs in groups.items():
            if f != fips:
                continue
            got = compose(xs, today, two=bool(lab) and twos.get(body, False))
            if lab and lmap.get(lab) is None:
                if got.get("members") or got.get("unsettled"):
                    problems.append("%s %s: the results' district %r matches no district of the layer"
                                    % (e["name"], body, lab))
                continue
            composed[(body, lmap[lab] if lab else "")] = (got, lab)
        # two labels that reach one district
        seen = collections.defaultdict(list)
        for (body, key), (got, lab) in composed.items():
            if key and not got.get("obsolete"):
                seen[(body, key)].append(lab)
        for (body, key), labs in seen.items():
            if len(labs) > 1:
                problems.append("%s %s: %s all match district %s" % (e["name"], body, labs, key))
        for key, d in list(ds.items()) + list(extra.get(fips, {}).items()):
            entry["districts"][key] = {"name": d["name"]}
        for (body, key), (got, lab) in sorted(composed.items()):
            if got.get("obsolete"):
                report["obsolete"] += 1
                continue
            hand = HAND.get((fips, body, key))
            seat = {}
            if hand:
                seat = hand_seat(hand)
            elif got.get("unsettled"):
                seat = {"unsettled": got["unsettled"]}
                report["unsettled"] += 1
                print("UNSETTLED %s %s %s: %s" % (e["name"], body, lab or "at large", got["unsettled"]),
                      file=sys.stderr)
            else:
                seat = {"members": got["members"]}
                if got.get("two"):
                    report["two-member districts"] += 1
            if got.get("pending"):
                seat["pending"] = got["pending"]
            if key:
                entry["districts"][key].setdefault("seats", {})[body] = seat
            else:
                entry["bodies"].setdefault(body, {})["atLarge"] = seat
        moved_on(entry, report)
        for body in ("board", "school"):
            by_district = any(body in (d.get("seats") or {}) for d in entry["districts"].values())
            entry["bodies"].setdefault(body, {})["byDistrict"] = by_district
            if not by_district and not entry["bodies"][body].get("atLarge"):
                entry["bodies"][body]["elected"] = False
        # a district no body elects from is not drawn
        entry["districts"] = collections.OrderedDict(
            (k, v) for k, v in entry["districts"].items() if v.get("seats"))
        out["51" + fips] = entry
    town_out = collections.OrderedDict()
    merged, split = merge_town_parts(town_recs, source["contests"])
    report["town contests read from two counties' parts"] = split
    tgroups = collections.defaultdict(list)
    for r in merged:
        tgroups[(r["town_name"], r["body"], r["label"])].append(r)
    for t in sorted(town_list["towns"], key=lambda t: t["name"]):
        name = t["name"]
        bodies = {}
        if not any(k[0] == name and k[1] == "town" for k in tgroups):
            problems.append("the results hold no council contest for the town of %s" % name)
            continue
        wards = any(k[0] == name and k[1] == "town" and k[2] for k in tgroups)
        for body in TOWN_BODIES:
            hand = HAND.get((name, body, ""))
            xs = tgroups.get((name, body, ""))
            if hand:
                bodies[body] = hand_seat(hand)
                continue
            if body == "town" and wards:
                bodies[body] = {"unsettled": WARD_WHY}
                report["town councils elected by ward"] += 1
                continue
            if not xs:
                continue
            got = compose(xs, today)
            if got.get("obsolete"):
                got = {"unsettled": STALE_WHY}
            elif body == "town" and got.get("members"):
                why = town_cycle_changed(xs, got["term"], got["members"])
                if why:
                    got = {"unsettled": why}
            seat = {k: got[k] for k in ("members", "unsettled", "pending") if got.get(k)}
            bodies[body] = seat
        tentry = {"name": name, "bodies": {b: {"atLarge": v} for b, v in bodies.items()}}
        moved_on(tentry, report)
        out_t = collections.OrderedDict((b, tentry["bodies"][b]["atLarge"])
                                        for b in TOWN_BODIES if b in tentry["bodies"])
        for b, seat in out_t.items():
            report["town %s %s" % (b, "named" if seat.get("members") else "not named")] += 1
            if seat.get("unsettled"):
                print("UNSETTLED town of %s %s: %s" % (name, b, seat["unsettled"]), file=sys.stderr)
        town_out[name] = out_t
    listed = {t["name"] for t in town_list["towns"]}
    for k, name in sorted(TOWN_ALIAS.items()):
        if name not in listed:
            problems.append("TOWN_ALIAS names %r, which the Census's list does not hold" % name)
    for k, name in sorted(TOWN_ROUTES.items()):
        if name not in listed:
            problems.append("TOWN_ROUTES names %r, which the Census's list does not hold" % name)
    for fips, number in sorted(set(vl.NAME_FIX) - fixed):
        problems.append("va_localities renames %s district %s and no result names that district"
                        % (locs[fips]["name"], number))
    if problems:
        for p in problems:
            print("PROBLEM " + p, file=sys.stderr)
        fail("%d problems; see above" % len(problems))
    print(dict(report), file=sys.stderr)
    return {"asOf": today.isoformat(), "source": SITE, "localities": out, "towns": town_out}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check():
    """Offline: the shipped file is the one the record describes, every seat
    is either named from a contest or says why it is not, and every district
    it names is one of today's precinct file's districts."""
    with open(RECORD, encoding="utf-8") as fh:
        record = json.load(fh)
    with open(OUT, "rb") as fh:
        raw = fh.read()
    data = json.loads(raw.decode("utf-8"))
    problems = []
    if sha(raw) != record.get("shipped_sha256"):
        problems.append("the shipped file does not hash to what the builder recorded; rebuild it")
    ds = vl.districts(vl.load_precincts())
    known = {k for entries in ds.values() for k in entries}
    known |= {"51%s-superward-%d" % (vl.NORFOLK, n) for n in (6, 7)}
    locs = vl.load_localities()
    if set(data["localities"]) != {"51" + f for f in locs}:
        problems.append("the file does not hold exactly the 133 counties and cities")

    def seat_ok(where, seat):
        if not isinstance(seat, dict):
            problems.append("%s: not a seat" % where)
            return
        if "unsettled" in seat:
            if not seat["unsettled"]:
                problems.append("%s: unsettled without a reason" % where)
            return
        if not seat.get("members") and not seat.get("left"):
            problems.append("%s: names no member and gives no reason" % where)
        for m in seat.get("members", []) + seat.get("pending", []):
            if m.get("name") and (m["name"].strip().lower() in NOT_CANDIDATES
                                  or re.search(r"(?i)\btotal\b|\bvotes\b|\bballots\b", m["name"])):
                problems.append("%s: %r is a total the results list, not a person" % (where, m["name"]))
            if m.get("name") and m["name"] != spelled(m["name"]):
                problems.append("%s: %r carries extra spaces or a trailing comma" % (where, m["name"]))
            if "contest" in m:
                if not re.fullmatch(r"\d+", str(m["contest"])) or m.get("election") not in (
                        "regular", "special") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",
                                                                   m.get("elected") or ""):
                    problems.append("%s: member %r lacks its contest, kind or date" % (where, m))
            elif not seat.get("verified"):
                problems.append("%s: member %r comes from no contest and no page" % (where, m))
        if seat.get("verified") and not (seat["verified"].get("url") or "").startswith("https://"):
            problems.append("%s: read by hand from no page" % where)

    for geoid, loc in data["localities"].items():
        for body, b in loc["bodies"].items():
            if "atLarge" in b:
                seat_ok("%s %s at large" % (loc["name"], body), b["atLarge"])
        for key, d in loc["districts"].items():
            if key not in known:
                problems.append("%s: district %s is no district of the precinct file"
                                % (loc["name"], key))
            if not key.startswith(geoid + "-"):
                problems.append("%s: district %s belongs to another locality" % (loc["name"], key))
            if not d.get("seats"):
                problems.append("%s: district %s elects nobody" % (loc["name"], key))
            for body, seat in (d.get("seats") or {}).items():
                seat_ok("%s %s %s" % (loc["name"], body, d.get("name")), seat)
    town_list = load_towns()["towns"]
    if len(town_list) < TOWN_FLOOR:
        problems.append("the list of towns holds %d, fewer than %d" % (len(town_list), TOWN_FLOOR))
    shipped = data.get("towns") or {}
    if set(shipped) != {t["name"] for t in town_list}:
        problems.append("the file's towns are not the Census's list: missing %s, extra %s" % (
            sorted({t["name"] for t in town_list} - set(shipped))[:5],
            sorted(set(shipped) - {t["name"] for t in town_list})[:5]))
    for name, bodies in shipped.items():
        if "town" not in bodies:
            problems.append("the town of %s has no council entry" % name)
        for body, seat in bodies.items():
            if body not in TOWN_BODIES:
                problems.append("the town of %s has a body %r" % (name, body))
            seat_ok("%s %s" % (name, body), seat)
    # The card finds a town's entry by the name on the map's own tile under
    # the point, so each town's Census internal point must land, in the
    # archive the City or Town layer draws, on a town of that name and GEOID.
    sys.path.insert(0, os.path.join(os.path.dirname(vl.INSTANCE), "scripts"))
    from build_landing_page import tile_features  # noqa: PLC0415
    for t in town_list:
        hits = [f["properties"] for f in tile_features(TOWN_TILES, t["lng"], t["lat"])
                if f["properties"].get("BASENAME") == t["name"]]
        if not any(h.get("GEOID") == t["geoid"] for h in hits):
            problems.append("the map's tile at the town of %s's point holds no town of that name "
                            "and GEOID %s" % (t["name"], t["geoid"]))
    used = {(geoid[2:], body, key) for geoid, loc in data["localities"].items()
            for key, d in loc["districts"].items() for body, seat in (d.get("seats") or {}).items()
            if seat.get("verified")}
    used |= {(geoid[2:], body, "") for geoid, loc in data["localities"].items()
             for body, b in loc["bodies"].items() if (b.get("atLarge") or {}).get("verified")}
    used |= {(name, body, "") for name, bodies in shipped.items() for body, seat in bodies.items()
             if seat.get("verified")}
    for k in sorted(set(HAND) - used):
        problems.append("HAND names %r and the shipped file does not use it; rebuild" % (k,))
    if problems:
        for p in problems[:40]:
            print("build_va_local_officials --check: FAIL: " + p, file=sys.stderr)
        raise SystemExit(1)
    seats = sum(1 for loc in data["localities"].values() for d in loc["districts"].values()
                for _ in d["seats"])
    named = sum(1 for b in shipped.values() if (b.get("town") or {}).get("members"))
    print("build_va_local_officials --check: OK — %d counties and cities, %d district seats, "
          "%d towns (%d councils named), composed as of %s from %d contests"
          % (len(data["localities"]), seats, len(shipped), named, data["asOf"], record["contests"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--source")
    ap.add_argument("--save-source")
    ap.add_argument("--today", help="compose as of this date (YYYY-MM-DD)")
    ap.add_argument("--precincts", default=vl.PRECINCTS)
    ap.add_argument("--fetch-towns", action="store_true",
                    help="read the Census's list of towns again even when building from --source")
    args = ap.parse_args()
    if args.check:
        check()
        return
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    if not args.source or args.fetch_towns:
        towns = fetch_towns(today)
        old_towns = load_towns() if os.path.exists(TOWNS_FILE) else {}
        if dict(old_towns, fetched=None) != dict(towns, fetched=None):
            with open(TOWNS_FILE, "w", encoding="utf-8") as fh:
                json.dump(towns, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
            print("wrote %s (%d towns)" % (os.path.relpath(TOWNS_FILE), len(towns["towns"])),
                  file=sys.stderr)
    if args.source:
        with open(args.source, encoding="utf-8") as fh:
            source = json.load(fh)
    else:
        source = fetch(today)
        if args.save_source:
            with open(args.save_source, "w", encoding="utf-8") as fh:
                json.dump(source, fh)
    data = build(source, today, args.precincts)
    # A week whose seats are unchanged keeps the file, its date and its record
    # as they are, so most weeks change nothing and the weekly job opens no
    # pull request. The card's "read" date is then the day the names last
    # changed, never a day they were not read.
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            old = json.load(fh)
        if dict(old, asOf=None) == dict(data, asOf=None):
            print("unchanged since %s; %s left as it is" % (old.get("asOf"), os.path.relpath(OUT)),
                  file=sys.stderr)
            return
    raw = (json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8")
    with open(OUT, "wb") as fh:
        fh.write(raw)
    record = {
        "fetched": source.get("fetched"),
        "api": API,
        "contests": len(source["contests"]),
        "source_sha256": sha(json.dumps(source["contests"], sort_keys=True).encode("utf-8")),
        "asOf": data["asOf"],
        "shipped_sha256": sha(raw),
    }
    os.makedirs(os.path.dirname(RECORD), exist_ok=True)
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %s (%d bytes)" % (os.path.relpath(OUT), len(raw)), file=sys.stderr)


if __name__ == "__main__":
    main()
