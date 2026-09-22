#!/usr/bin/env python3
"""
The city rosters, in the served bytes — generated into the question pages.

WHY. scripts/build_county_pages.py put 2,650 county officeholders where a
crawler can read them, and it left the CITY seats where they were: behind a
JSON fetch and a rendered card. Measured 2026-09-15, New York City's 51 Council
Members and San Francisco's 11 Supervisors appeared in no served byte of this
site. Both rosters are already shipped as data/app files and already reviewed
before they ship; nothing was missing except a table.

WHERE. Each city's own question page — ny/council-district.html,
ca/supervisor-district.html — rather than a page per seat. That is the decision
build_county_pages.py already made and states: a page whose whole content is one
name is the shape search engines treat as thin, and the question people type is
about the body far more often than about one seat. Each row carries schema.org
Person markup, so a reader asking a machine "who represents District 6" gets a
name it can attribute.

THE TABLE IS A DATED SNAPSHOT AND SAYS SO. The instance's own verified_date is
printed above it. The map card beside it reads the same roster file, so the two
cannot disagree — but a static table is a claim about a day, and a claim about
a day that does not name the day is the thing this project does not ship.

WHAT IS NOT HERE. Chicago's 50 alderpeople. That roster is not a shipped file:
il/index.html fetches Socrata htai-wnw4 live on every toggle, so there is
nothing for this to read. NOT_YET records it rather than leaving it to be
noticed, and --check FAILS on an entry whose roster has since appeared.

    python3 scripts/build_officeholder_tables.py           # write the regions
    python3 scripts/build_officeholder_tables.py --check   # drift gate for CI
"""

import argparse
import collections
import difflib
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_county_pages import party_name                      # noqa: E402
from build_legislator_pages import INSTANCES as LEGISLATOR_INSTANCES  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REGION = "officeholder-table"
BEGIN = "<!-- ==== GENERATED:BEGIN %s ==== -->" % REGION
END = "<!-- ==== GENERATED:END %s ==== -->" % REGION

# Where the table goes, and the words that page uses for its own seats. The
# roster-to-page join has no mechanical source — nothing in council-members.json
# says which page it belongs on — so it is stated, the way build_county_pages.py
# states one entry per state. Everything else is read: the names and offices
# from the roster, the date from the instance's worksheet, the district count
# from the roster itself.
# Where the tables go, and the words each page uses for its own seats. The
# roster-to-page join has no mechanical source — nothing in council-members.json
# says which page it belongs on — so it is stated, the way build_county_pages.py
# states one entry per state. Everything else is read: the names, parties and
# offices from the roster, the date from the instance's worksheet, the district
# count from the roster itself.
#
# AN ENTRY IS A PAGE AND CARRIES A LIST OF SECTIONS, because a state legislature
# page answers for two chambers over the same ground and splitting it would give
# a reader half an answer per page. The twelve legislator pages' sections are
# DERIVED from build_legislator_pages.INSTANCES rather than restated here —
# that script already names every chamber, its layer and its roster, and two
# copies of "Illinois House of Representatives" is one copy too many.
# ---------------------------------------------------------------- adapters
#
# WHAT AN ADAPTER IS FOR. The renderer below reads a roster shaped
# {seat: {"name": ...}} and eleven of the fleet's rosters are shaped that way.
# Four are not: the Wisconsin bench keys a LIST of judges under a circuit, the
# township directory keys three lists of officials under a township, the two
# Wisconsin school boards nest their members under a `members` key beside the
# board's own office, and Chicago's school board maps a district straight to a
# NAME STRING. An adapter turns one of those into the ordered list of
# (seat label, record) pairs the renderer wants, and nothing else here changes.
#
# THE ADAPTER DECIDES THE ORDER. A flat roster sorts by district number, which
# is the only order it has; these four have a real one — circuit then branch,
# township then the office a ballot lists first — and sorting them numerically
# would scatter a township's own officials down the page.


def circuit_judges(data):
    """The Wisconsin bench: one row per judge, grouped by circuit.

    A circuit's name is the counties it covers, never its slug: three circuits
    cover two counties each and their slug ("buffalo-pepin") is an id rather
    than a name anyone uses. The branch number goes in the seat cell because a
    branch is part of which bench a judge sits on, and the only ROLE the court
    system prints is Chief Judge, which is left empty for everyone else rather
    than filled with a title the source does not claim.
    """
    rows = []
    for key in sorted(data, key=lambda k: data[k]["counties"]):
        circuit = " and ".join(c.replace(" County", "")
                               for c in data[key]["counties"])
        for judge in data[key]["judges"]:
            seat = ("%s, Branch %s" % (circuit, judge["branch"])
                    if judge.get("branch") else circuit)
            rows.append((seat, judge))
    return rows


def township_officials(data):
    """Cook County's township officials: one row per person.

    The order inside a township is the order a ballot lists the offices —
    supervisor, then the other county-wide officers, then the trustees — not
    alphabetical, which would separate a township's clerk from its supervisor.
    NO CONTACT IS CARRIED THROUGH. The county publishes one telephone and one
    mailbox per township hall, often a staff member's, so it belongs beside the
    hall on the page's own table and never beside a person's name; the record
    handed on here holds a name and an office and nothing else.
    """
    rows = []
    for geoid in sorted(data, key=lambda k: data[k]["name"]):
        rec = data[geoid]
        people = ([rec["head"]] if rec.get("head") else []) + \
            list(rec.get("officers") or []) + list(rec.get("board") or [])
        for person in people:
            rows.append((rec["name"],
                         {"name": person.get("name"), "role": person.get("role")}))
    return rows


def school_board_members(data):
    """A Wisconsin elected school board, nested under `members`.

    Milwaukee elects eight members from districts and one at large, and its
    roster keys that ninth seat `AL` — printed as what it is rather than as
    "District AL". Racine reports one seat vacant and it is carried through as
    vacant: a seat left out would make the board look smaller than it is.
    """
    members = data["members"]
    return [("At large" if k == "AL" else "District %s" % k, members[k])
            for k in sorted(members, key=district_key)]


def name_strings(data):
    """Chicago's elected school board, which maps a district to a NAME STRING.

    The roster writes a vacant seat as the literal "VACANT", which the renderer
    would otherwise mark up as a person of that name. It becomes a vacancy here.
    """
    return [("District %s" % k,
             {"vacant": True} if str(data[k]).strip().upper() == "VACANT"
             else {"name": data[k]})
            for k in sorted(data, key=district_key)]


def _ordinal(n):
    """1 -> 1st. Chicago names each council by the ordinal of its district."""
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def district_council_members(data):
    """Chicago's Police District Councils: three members elected per district.

    EACH COUNCIL IS ITS OWN ELECTED BODY, which is why its section sets
    org_per_seat the way Cook's townships already do — 22 councils, not one
    body of 65 people. The seat label IS the organisation's name in the graph,
    so it is the council's own name ("1st District Council", as ccpsa.chicago.gov
    writes it) rather than the bare district number, which names no body.

    THE `role` IS CARRIED AND IS NOT ALWAYS AN OFFICE. The Commission publishes
    "Chair" beside one member of each council and a committee assignment beside
    the others ("Nominating Committee", "Community Engagement"). Both are what
    the body itself prints against that person, so both ship; nothing here
    promotes a committee to an office or invents a title for a member the
    Commission lists without one.

    Districts are ordered by NUMBER and not by string: 2 sorts before 10.
    """
    rows = []
    for key in sorted(data, key=district_key):
        for member in data[key].get("members") or []:
            rows.append(("%s District Council" % _ordinal(int(key)), member))
    return rows


def city_council(data):
    """A city council or commission: the at-large seats, then the wards.

    SIX ROSTERS, FOUR SHAPES, and the variation is in the containers rather
    than in the records. The at-large members are always a list under
    `citywide`; the ward members live under `wards` in five of the six and
    under `districts` in Detroit's, and the value is a single record in three
    of them and a LIST in the two cities that elect more than one member per
    ward (Grand Rapids seats two). Every record already carries its own `seat`
    — "Mayor", "At-Large", "Ward 1", "City Council District 2" — written by the
    city itself, so the label is read rather than composed, and a city that
    calls its districts wards is not told it has districts.

    A VACANCY IS CARRIED, NEVER DROPPED. Grand Rapids' roster reports Ward 1
    open since a resignation in April 2026; a ward left out would make the
    commission look one seat smaller than the city elects, which is the
    distinction the county-board pages already make in three states.
    """
    rows = [(m.get("seat") or "At large", m) for m in data.get("citywide") or []]
    wards = data.get("wards") or data.get("districts") or {}
    vacancies = data.get("vacancies") or {}
    for key in sorted(wards, key=district_key):
        value = wards[key]
        members = value if isinstance(value, list) else [value]
        for member in members:
            rows.append((member.get("seat") or "Ward %s" % key, member))
        if key in vacancies:
            # The open seat takes the label its WARD-MATES carry, so Grand
            # Rapids' vacancy reads "Ward 1 Commissioner" beside the member who
            # holds the ward's other seat rather than "Ward 1" beside it. Two
            # spellings of one ward in one table read as two wards.
            sibling = next((m.get("seat") for m in members if m.get("seat")), None)
            rows.append((sibling or "Ward %s" % key, {"vacant": True}))
    for key in sorted(set(vacancies) - set(wards), key=district_key):
        rows.append(("Ward %s" % key, {"vacant": True}))
    return rows


def city_officials(data):
    """Small Iowa cities whose officials reach this project through a COUNTY.

    Each city is its own government, so the section sets org_per_seat and the
    seat label is the city's name — one node per council rather than one body
    holding four cities' mayors. The record's own `role` ("Mayor",
    "Councilman") is what the county directory prints and is carried as it is.
    """
    rows = []
    for key in sorted(data, key=lambda k: data[k]["city"]):
        for member in data[key].get("members") or []:
            rows.append((data[key]["city"], member))
    return rows


def county_officers(data):
    """One elected officer per county, keyed by county FIPS.

    THE SEAT IS THE COUNTY AND NOT THE OFFICE, because the organisation this
    person holds office in IS the county: "Adair County" is a government with
    a member who is its Auditor, where "Adair County Auditor" is an office and
    naming it as an organisation would invent a body of one. The role comes
    from the section's `holder`, so no `role` is set on the record — a Role
    column reading "Auditor" ninety-nine times is noise, not information.
    """
    return [("%s County" % data[key]["county"], data[key])
            for key in sorted(data, key=lambda k: data[k]["county"])]


ADAPTERS = {
    "county_officers": county_officers,
    "city_council": city_council,
    "city_officials": city_officials,
    "circuit_judges": circuit_judges,
    "township_officials": township_officials,
    "school_board_members": school_board_members,
    "name_strings": name_strings,
    "district_council_members": district_council_members,
}


CITY_TABLES = [
    dict(tag="il", page="ward.html", worksheet="metro-worksheet.json",
         sections=[dict(roster="data/source/ward-members.json",
                        seat="Ward", holder="Alderperson",
                        office_label="Ward office",
                        body="the Chicago City Council", org="Chicago City Council",
                        heading="Who represents each Chicago ward")]),
    dict(tag="ny", page="council-district.html", worksheet="ny/metro-worksheet.json",
         sections=[dict(roster="data/app/council-members.json",
                        seat="District", holder="Council Member",
                        office_label="District office",
                        body="the New York City Council", org="New York City Council",
                        heading="Who represents each Council district")]),
    dict(tag="ca", page="supervisor-district.html", worksheet="ca/metro-worksheet.json",
         sections=[dict(roster="data/app/sf-supervisor-members.json",
                        seat="District", holder="Supervisor",
                        office_label="District office",
                        body="the San Francisco Board of Supervisors",
                        org="San Francisco Board of Supervisors",
                        heading="Who represents each supervisor district")]),
    # THE ONE SECTION WHOSE HOLDER IS NOT ELECTED. An NYPD precinct commander is
    # appointed, so `unit`/`prep` exist to keep the sentence from calling 78
    # commands "seats on" a body. The roster names the person in `commander`
    # rather than `name`, which is why name_field is stated: nothing mechanical
    # says which key on a record holds a person.
    dict(tag="ny", page="police-precinct.html", worksheet="ny/metro-worksheet.json",
         sections=[dict(roster="data/app/nypd-precinct-info.json",
                        seat="Precinct", holder="Commanding Officer",
                        name_field="commander",
                        office_label="Station house",
                        link_label="NYPD page",
                        unit="precincts", prep="in",
                        body="the New York City Police Department",
                        org="New York City Police Department",
                        heading="Who commands each NYPD precinct")]),
    # THE FOUR PHASE-3 PAGES, whose rosters are the reason ADAPTERS exist.
    # Each one names people this site had shipped for months and served to
    # nobody: the Wisconsin bench, Cook County's township officials, the two
    # Wisconsin school boards elected by district, and Chicago's own elected
    # board — which had a question page from the day it shipped and never a
    # table on it.
    dict(tag="wi", page="circuit-court.html", worksheet="wi/metro-worksheet.json",
         sections=[dict(roster="data/app/wi-circuit-judges.json",
                        adapter="circuit_judges",
                        seat="Circuit", holder="Judge", role_label="Role",
                        office_label="Courthouse",
                        unit="judges", prep="in",
                        body="Wisconsin's circuit courts",
                        # One court system, divided into circuits and branches —
                        # which is what the seat cell names.
                        org="Wisconsin Circuit Court",
                        heading="Which judges sit in each circuit")]),
    dict(tag="il", page="township.html", worksheet="metro-worksheet.json",
         sections=[dict(roster="data/app/township-officials.json",
                        adapter="township_officials",
                        seat="Township", holder="Official", role_label="Office",
                        office_label="Township hall",
                        unit="elected officials", prep="in",
                        body="Cook County's townships",
                        # 220 people across 29 governments: each township is its
                        # own organisation and one node for all of them would be
                        # a body that does not exist.
                        org_per_seat=True,
                        heading="Who holds each township office")]),
    dict(tag="wi", page="school-board.html", worksheet="wi/metro-worksheet.json",
         sections=[dict(roster="data/app/mps-school-board-members.json",
                        adapter="school_board_members",
                        seat="Seat", holder="Director", role_label="Role",
                        office_label="Office",
                        body="the Milwaukee Board of School Directors",
                        org="Milwaukee Board of School Directors",
                        heading="Who sits on the Milwaukee Board of School Directors"),
                   dict(roster="data/app/rusd-school-board-members.json",
                        adapter="school_board_members",
                        seat="Seat", holder="Board Member", role_label="Role",
                        office_label="Office",
                        body="the Racine Unified School District Board of Education",
                        org="Racine Unified School District Board of Education",
                        heading="Who sits on the Racine Unified school board")]),
    # Michigan and Iowa draw city wards and named nobody in them until
    # 2026-09-22: Detroit's 9, Grand Rapids' 6, Battle Creek's 9, Des Moines'
    # 7, Cedar Rapids' 8, Waterloo's 7 and 24 more across four small Iowa
    # cities appeared in no served byte of this site, found by a fleet-wide
    # audit of rosters whose names reach no page. Each city is its OWN council,
    # so each gets its own section and its own organisation rather than one
    # node named for a state's worth of unrelated governments.
    dict(tag="mi", page="city-council.html", worksheet="mi/metro-worksheet.json",
         sections=[
             dict(roster="data/app/mi-detroit-council-members.json",
                  adapter="city_council", seat="Seat", holder="Council Member",
                  office_label="City hall", body="the Detroit City Council",
                  org="Detroit City Council",
                  heading="Who sits on the Detroit City Council"),
             dict(roster="data/app/mi-grand-rapids-council-members.json",
                  adapter="city_council", seat="Seat", holder="Commissioner",
                  office_label="City hall", body="the Grand Rapids City Commission",
                  org="Grand Rapids City Commission",
                  heading="Who sits on the Grand Rapids City Commission"),
             dict(roster="data/app/mi-battle-creek-commission-members.json",
                  adapter="city_council", seat="Seat", holder="Commissioner",
                  office_label="City hall", body="the Battle Creek City Commission",
                  org="Battle Creek City Commission",
                  heading="Who sits on the Battle Creek City Commission"),
         ]),
    dict(tag="ia", page="city-council.html", worksheet="ia/metro-worksheet.json",
         sections=[
             dict(roster="data/app/dsm-council-members.json",
                  adapter="city_council", seat="Seat", holder="Council Member",
                  office_label="City hall", body="the Des Moines City Council",
                  org="Des Moines City Council",
                  heading="Who sits on the Des Moines City Council"),
             dict(roster="data/app/cedar-rapids-council-members.json",
                  adapter="city_council", seat="Seat", holder="Council Member",
                  office_label="City hall", body="the Cedar Rapids City Council",
                  org="Cedar Rapids City Council",
                  heading="Who sits on the Cedar Rapids City Council"),
             dict(roster="data/app/waterloo-council-members.json",
                  adapter="city_council", seat="Seat", holder="Council Member",
                  office_label="City hall", body="the Waterloo City Council",
                  org="Waterloo City Council",
                  heading="Who sits on the Waterloo City Council"),
             # FOUR CITIES, FOUR COUNCILS, one file: these reach this project
             # through their COUNTY's own directory rather than through a city
             # page, so the seat is the city's name and each city is its own
             # organisation. They elect at large and have no wards drawn.
             dict(roster="data/app/ia-city-officials.json",
                  adapter="city_officials", seat="City", holder="Council Member",
                  role_label="Office", unit="elected officials", prep="in",
                  office_label="City hall",
                  body="four Iowa cities whose officials their county publishes",
                  org_per_seat=True,
                  heading="Who holds each office in four more Iowa cities"),
         ]),
    # Iowa's county auditors: one per county, the county's own chief election
    # officer, and 99 named people who reached no served byte of this site
    # until 2026-09-22. They are recorded in build_county_pages.py's
    # NOT_COUNTY_BOARDS — correctly, an auditor is not a supervisor — and that
    # reason says why they are not on the BOARD pages, never that they should
    # reach no page at all.
    dict(tag="ia", page="county-auditor.html", worksheet="ia/metro-worksheet.json",
         sections=[dict(roster="data/app/ia-county-auditors.json",
                        adapter="county_officers",
                        seat="County", holder="Auditor",
                        office_label="Office", unit="county auditors", prep="in",
                        body="Iowa's county auditors",
                        org_per_seat=True,
                        heading="Who is the auditor in each Iowa county")]),
    # Chicago's District Councils ride the page the police-district layer
    # already has, because they are elected ON that boundary — one council per
    # police district — and a reader asking "what police district am I in" is
    # one step from "who sits on its council". 65 people who reached no served
    # byte of this site until 2026-09-22, measured by a fleet-wide audit of
    # rosters whose names appear on no page.
    dict(tag="il", page="police-district.html", worksheet="metro-worksheet.json",
         sections=[dict(roster="data/app/ccpsa-district-councils.json",
                        adapter="district_council_members",
                        seat="Council", holder="Member", role_label="Role",
                        unit="elected members", prep="on",
                        body="Chicago's Police District Councils",
                        org_per_seat=True,
                        heading="Who sits on each Police District Council")]),
    dict(tag="il", page="school-board.html", worksheet="metro-worksheet.json",
         sections=[dict(roster="data/app/school-board-members.json",
                        adapter="name_strings",
                        seat="District", holder="Board Member",
                        office_label="Office",
                        unit="elected district seats", prep="on",
                        body="the Chicago Board of Education",
                        org="Chicago Board of Education",
                        heading="Who represents each Chicago school board district")]),
]


def legislator_tables():
    """The twelve legislator pages, read from the script that generates them."""
    out = []
    for tag, inst in sorted(LEGISLATOR_INSTANCES.items()):
        spec = inst["legislature"]
        out.append(dict(
            tag=tag, page=spec["file"], worksheet=inst["worksheet"],
            sections=[dict(roster="data/app/" + ch["roster"],
                           seat="District", holder=ch["holder"],
                           office_label="District office",
                           body="the " + ch["name"], org=ch["name"],
                           heading="Who represents each %s district" % ch["name"])
                      for ch in spec["chambers"]]))
        cong = inst["congress"]
        out.append(dict(
            tag=tag, page=cong["file"], worksheet=inst["worksheet"],
            sections=[dict(roster="data/app/" + cong["roster"],
                           seat="District", holder="Representative",
                           office_label="District office",
                           body="%s's delegation to the U.S. House of Representatives"
                                % cong["state"],
                           # A delegation is a real thing to name and is not the
                           # House: six nodes each claiming to BE the House with
                           # its own state's members would each be false.
                           org="%s delegation to the U.S. House of Representatives"
                               % cong["state"],
                           parent_org="United States House of Representatives",
                           heading="Who represents each %s congressional district"
                                   % cong["state"])]))
    return out


TABLES = CITY_TABLES + legislator_tables()

NOT_YET = []
# EMPTY, which is a measurement rather than an omission. It carried one entry
# from 2026-09-15 — Chicago's 50 alderpeople, whose roster was a live Socrata
# call and not a file — and scripts/chicago_ward_scraper.py closed it the same
# day. Entries here are re-audited on every run: one whose roster has since
# appeared FAILS rather than going quiet, which is what retired that one.

# The region goes immediately before this section, on every page that has one.
ANCHOR = "  <section>\n    <h2>Related lookups</h2>"


def fail(msg):
    print("build-officeholder-tables: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def roster_path(tag, roster):
    """<tag>/<roster>. The path is STATED per section rather than assembled from
    data/app, because Chicago's is not in data/app: il/index.html reads the ward
    roster live from Socrata, so a file the app never fetches would fail
    validate_index.py's rule that every data/app file is referenced. It sits in
    il/data/source beside the other build-time inputs instead."""
    return os.path.join(tag, roster)


def load(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def district_key(k):
    """Sort 1, 2, 10 rather than 1, 10, 2 — and never crash on a lettered one."""
    return (0, int(k), "") if k.isdigit() else (1, 0, k)


def section_rows(tag, section):
    """(seat label, record) in the order the table prints them.

    A section with an adapter hands the file to it; everything else is the flat
    {district: {...}} shape, keyed and ordered by district number.
    """
    data = load(roster_path(tag, section["roster"]))
    if not isinstance(data, dict) or not data:
        fail("%s/%s is not a non-empty object" % (tag, section["roster"]))
    if section.get("adapter"):
        rows = ADAPTERS[section["adapter"]](data)
    else:
        rows = [("%s %s" % (section["seat"], k),
                 data[k] if isinstance(data[k], dict) else {})
                for k in sorted(data, key=district_key)]
    if not rows:
        fail("%s/%s produced no rows" % (tag, section["roster"]))
    return rows


def render_section(tag, section, verified):
    rows_in = section_rows(tag, section)
    name_field = section.get("name_field", "name")
    named = [rec for _s, rec in rows_in if rec.get(name_field)]
    if not named:
        fail("%s/%s names nobody — refusing to write an empty table"
             % (tag, section["roster"]))

    # WHICH COLUMNS EXIST IS DERIVED FROM THE ROSTER, never listed. NYC's and
    # SF's carry no party and get no party column; the legislature rosters carry
    # one on every record; the offices are named differently per chamber and
    # several are absent, so the first one a record carries wins per section.
    has_party = any(rec.get("party") for rec in named)
    # AN OFFICE COLUMN ONLY WHERE THE OFFICE IS ONE LINE. The city rosters carry
    # `office` as a single street address, which reads as a table cell. The
    # legislature and congressional rosters carry `districtOffice` as a LIST of
    # three or four lines with a telephone number among them, and flattening
    # that into a cell on a 118-row table produces a column nobody can scan and
    # a second copy of what the map card already renders. So the column exists
    # when the value is a string and not when it is a list, which is a property
    # of the roster rather than a choice restated per page.
    office_key = next((f for f in ("office", "districtOffice")
                       if any(isinstance(rec.get(f), str) and rec[f]
                              for rec in named)), None)
    # THE SAME RULE FOR THREE MORE FIELDS, each of which is a fact about the
    # person and not about the body. Measured 2026-09-16 across every roster
    # these tables read: `role` appears on the township, judge and school-board
    # sections and on no other, `phone` on Chicago's wards, the Wisconsin bench
    # and Racine's board, and `termExpires` on the two Wisconsin boards. A
    # column heading cannot be derived from a role, so role_label is stated the
    # way `seat` is; the other two name themselves.
    #
    # THE PHONE COLUMN REACHES A PAGE THIS CHANGE WAS NOT ABOUT, which is what
    # a derived column means: Chicago's ward roster carries a telephone on all
    # 50 records, so il/ward.html gains the column too. That is the design
    # working rather than a side effect to suppress.
    #
    # `email` IS DELIBERATELY NOT ONE OF THEM. It is on the Iowa, Michigan and
    # Wisconsin legislature rosters, so deriving it would have put 429 more
    # addresses into three pages this change was not about, and the one section
    # here that would gain by it carries eight. A column that wide is its own
    # decision, not a consequence of this one.
    has_role = any(rec.get("role") for rec in named)
    if has_role and not section.get("role_label"):
        fail("%s/%s carries a role and the section names no role_label — a "
             "column heading cannot be derived from one"
             % (tag, section["roster"]))
    has_phone = any(rec.get("phone") for rec in named)
    has_term = any(rec.get("termExpires") for rec in named)
    # A CITATION COLUMN WHERE THE ROSTER CITES PER RECORD. Measured 2026-09-15
    # across every roster these tables read, `source_url` appears on exactly one
    # — nypd-precinct-info.json, where each commander comes from that precinct's
    # own NYPD page and the 78 links are 78 different pages. Deliberately NOT
    # keyed on `url` or `sourceUrl`: `url` is on nine legislature rosters as the
    # member's own official page, and adding a column to those tables is a
    # different decision than this one. The label is stated, like `seat` and
    # `holder`, because nothing in a URL says what to call it.
    link_key = ("source_url" if all(rec.get("source_url") for _s, rec in rows_in)
                else None)
    if link_key and not section.get("link_label"):
        fail("%s/%s carries source_url on every record and the section names no "
             "link_label — a column heading cannot be derived from a URL"
             % (tag, section["roster"]))

    extras = (bool(has_role) + bool(has_party) + bool(office_key)
              + bool(has_phone) + bool(has_term) + bool(link_key))
    rows = []
    for seat, rec in rows_in:
        name = rec.get(name_field)
        if not name:
            # A seat the roster does not name is printed as one. Leaving it out
            # would make the table claim a smaller body than the state elects.
            # A seat the source calls VACANT says so instead, which is a
            # stronger statement than "not listed" and a different one.
            cells = ['<td>%s</td>' % html.escape(seat),
                     '<td class="who">%s</td>'
                     % ("Vacant" if rec.get("vacant") else "Not listed")]
            cells += ["<td></td>"] * extras
            rows.append("      <tr>%s</tr>" % "".join(cells))
            continue
        # The <meta> sits INSIDE a cell, not between <tr> and <td>. An HTML
        # parser foster-parents any non-table content out of a <tr>, which
        # moves it before the whole table and detaches it from the itemscope
        # it was meant to describe — valid-looking markup that says nothing.
        cells = ['<td>%s</td>' % html.escape(seat),
                 '<td class="who"><meta itemprop="jobTitle" content="%s, %s">'
                 '<span itemprop="name">%s</span></td>'
                 % (html.escape(rec.get("role") or section["holder"], quote=True),
                    html.escape(seat, quote=True), html.escape(name))]
        if has_role:
            cells.append("<td>%s</td>" % html.escape(rec.get("role") or ""))
        if has_party:
            # party_name maps notation and decides nothing about a person: New
            # York's fusion labels ("Democratic/Working Families") are not in the
            # table and ship exactly as the state published them.
            cells.append('<td itemprop="affiliation">%s</td>'
                         % html.escape(party_name(rec.get("party")) or ""))
        if office_key:
            cells.append('<td itemprop="address">%s</td>'
                         % html.escape(rec.get(office_key) or ""))
        if has_phone:
            cells.append("<td>%s</td>" % tel_link(rec.get("phone")))
        if has_term:
            cells.append("<td>%s</td>" % html.escape(rec.get("termExpires") or ""))
        if link_key:
            # No itemprop. The cell sits inside the Person scope, so any
            # itemprop here would claim the precinct's page is a property of the
            # commander. It is a citation for the row, not a fact about them.
            cells.append('<td><a href="%s" target="_blank" rel="noopener">%s</a></td>'
                         % (html.escape(rec[link_key], quote=True),
                            html.escape(section["link_label"])))
        rows.append(
            '      <tr itemscope itemtype="https://schema.org/Person">%s</tr>'
            % "".join(cells))

    head = ["<th>%s</th>" % html.escape(section["seat"]),
            "<th>%s</th>" % html.escape(section["holder"])]
    if has_role:
        head.append("<th>%s</th>" % html.escape(section["role_label"]))
    if has_party:
        head.append("<th>Party</th>")
    if office_key:
        head.append("<th>%s</th>" % html.escape(section["office_label"]))
    if has_phone:
        head.append("<th>Telephone</th>")
    if has_term:
        head.append("<th>Term ends</th>")
    if link_key:
        head.append("<th>Source</th>")

    # WHETHER THE MAP READS THIS FILE IS DERIVED, NOT STATED, because it is the
    # one sentence here that can be false. An instance whose roster is in
    # data/app serves that file to its own card, so the card and this table are
    # one source. Chicago's ward roster is not: il/index.html calls Socrata
    # live, and that file is a weekly snapshot of the same dataset, so the two
    # can differ for up to a week. Saying "the map reads the same roster" on
    # that page would be a false claim about the product on the product.
    if section["roster"].startswith("data/app/"):
        agreement = ("The map above reads the same roster, so a card and this table "
                     "cannot disagree \u2014 but a table is a claim about a day, and "
                     "this one names its day.")
    else:
        agreement = ("The map above reads the same source live rather than this file, "
                     "so a card can be up to a week newer than this table \u2014 which "
                     "is why the table names its day.")

    return """  <section>
    <h2>%(heading)s</h2>
    <p>All %(n)d %(unit)s %(prep)s %(body)s, as this site had them on <strong>%(verified)s</strong>.
      %(agreement)s Where the roster names nobody it says so rather than guessing.
      <a href="sources.html">Where these names come from</a>.</p>
    <div class="flow-table-wrap">
    <table class="flow">
      <thead><tr>%(head)s</tr></thead>
      <tbody>
%(rows)s
      </tbody>
    </table>
    </div>
  </section>

""" % {
        "heading": html.escape(section["heading"]),
        "n": len(rows_in),
        # "seats on the Illinois House" is right for eleven of the twelve
        # entries and wrong for the one whose holders are appointed, so both
        # words are stated with the elected reading as the default.
        "unit": html.escape(section.get("unit", "seats")),
        "prep": html.escape(section.get("prep", "on")),
        "body": html.escape(section["body"]),
        "verified": html.escape(verified),
        "head": "".join(head),
        "agreement": agreement,
        "rows": "\n".join(rows),
    }


def tel_link(value):
    if not value:
        return ""
    return '<a href="tel:%s">%s</a>' % (re.sub(r"[^0-9+]", "", value),
                                        html.escape(value))


SITE = "https://districtry.com"


def slug(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def person_node(rec, name_field, section):
    who = rec.get(name_field)
    person = {"@type": "Person", "name": who}
    if rec.get("party"):
        person["affiliation"] = party_name(rec["party"]) or rec["party"]
    if rec.get("phone"):
        person["telephone"] = rec["phone"]
    office = next((rec[f] for f in ("office", "districtOffice")
                   if isinstance(rec.get(f), str) and rec[f]), None)
    if office:
        person["workLocation"] = {"@type": "Place", "address": office}
    if rec.get("source_url"):
        person["sameAs"] = rec["source_url"]
    return person


def organization(section, org_id, name, roles):
    node = {"@type": "GovernmentOrganization", "@id": org_id, "name": name,
            "member": roles}
    if section.get("parent_org"):
        node["parentOrganization"] = {"@type": "GovernmentOrganization",
                                      "name": section["parent_org"]}
    return node


def render_graph(entry, sections):
    """The page's rosters as linked data, beside the table that renders them.

    WHY IT IS HERE AND NOT IN THE HEAD. Four of these pages are hand-authored
    (il/ward.html, ny/council-district.html, ca/supervisor-district.html,
    ny/police-precinct.html) and the rest are written by two different page
    generators, so a graph in the `<head>` would be four hand-edits that drift
    and two generators that both have to learn the same roster shapes. JSON-LD
    is valid anywhere in the document, so it ships inside the region this script
    already owns — one mechanism, every page, nothing hand-kept.

    WHY BOTH AN ORGANIZATION AND A LIST. The audit asks for two things and they
    answer different questions: `member` -> `OrganizationRole` -> `Person` says
    who belongs to the body and in what seat, and `ItemList` says these are the
    body's seats in order. NOBODY IS DESCRIBED TWICE — each role node carries a
    stable `@id` and the list REFERENCES it, so a consumer reading either path
    reaches one object rather than two copies that can disagree.

    THE ORGANISATION'S NAME IS STATED, NEVER THE BODY PHRASE. Each section
    already carries `body` for its own prose, with the article attached and
    sometimes in the plural — "Cook County's townships", "Wisconsin's circuit
    courts" — and neither is the name of an organisation. Deriving the name from
    it would have published a GovernmentOrganization called "Wisconsin's circuit
    courts" whose 261 members are judges of a court system that has a real name.
    `parent_org` exists for the same reason: a state's U.S. House delegation is
    a real thing to name and is not the House itself, so the six congressional
    pages each describe their delegation and point at the chamber above it
    rather than six nodes claiming to be the whole House with 17 members.

    A SECTION WHOSE SEATS ARE THEMSELVES ORGANISATIONS sets `org_per_seat`. The
    township table is 220 people across 29 governments, and one node named for
    all of them would be a body that does not exist; instead each township is
    its own organisation holding its own officials, and the list is of the 29.

    A SEAT THE ROSTER DOES NOT NAME IS A LIST POSITION WITH A NAME AND NO ITEM,
    which is the same statement the table makes: the body has this seat and this
    file does not say who holds it. Dropping it would make the list claim a
    smaller body than the place elects.

    THE GRAPH IS INDENTED, and that was measured rather than assumed. On the
    largest of these pages (wi/circuit-court.html, 261 judges) indent=2 costs
    158 KB against 101 KB compact — and 32.4 KB against 32.0 KB once gzipped,
    which is what a reader actually downloads. 0.4 KB on the wire buys a diff a
    person can review, on files whose whole point is that a roster change lands
    as a reviewed pull request.
    """
    canonical = "%s/%s/%s" % (SITE, entry["tag"], entry["page"])
    graph = []
    for index, (section, rows) in enumerate(sections, 1):
        if not section.get("org") and not section.get("org_per_seat"):
            fail("%s/%s names no org — a schema.org organisation name cannot be "
                 "derived from the section's body phrase, which carries an "
                 "article and is sometimes plural"
                 % (entry["tag"], section["roster"]))
        name_field = section.get("name_field", "name")
        items = []
        if section.get("org_per_seat"):
            groups = collections.OrderedDict()
            for seat, rec in rows:
                groups.setdefault(seat, []).append(rec)
            for position, (seat, recs) in enumerate(groups.items(), 1):
                org_id = "%s#body-%d-%s" % (canonical, index, slug(seat))
                roles = []
                for n, rec in enumerate(recs, 1):
                    if not rec.get(name_field):
                        continue
                    roles.append({
                        "@type": "OrganizationRole",
                        # org_id already carries the fragment, so this
                        # APPENDS to it. The first draft wrote "%s#role-%d" and
                        # minted ids with two '#' in them, which is not a URL.
                        "@id": "%s-role-%d" % (org_id, n),
                        "roleName": rec.get("role") or section["holder"],
                        "member": person_node(rec, name_field, section),
                    })
                graph.append(organization(section, org_id, seat, roles))
                items.append({"@type": "ListItem", "position": position,
                              "name": seat, "item": {"@id": org_id}})
            graph.append({
                "@type": "ItemList",
                "@id": "%s#roster-%d" % (canonical, index),
                "name": section["heading"],
                "itemListOrder": "https://schema.org/ItemListOrderAscending",
                "numberOfItems": len(items),
                "itemListElement": items,
            })
            continue

        org_id = "%s#body-%d" % (canonical, index)
        roles = []
        for position, (seat, rec) in enumerate(rows, 1):
            if not rec.get(name_field):
                items.append({"@type": "ListItem", "position": position,
                              "name": seat})
                continue
            # THE POSITION IS IN THE ID, not the seat alone. A township lists
            # four trustees under one seat label and a single-branch circuit can
            # seat more than one judge, so a slug of the seat is not unique and
            # the first draft minted the same @id for seven people.
            role_id = "%s#role-%d-%d-%s" % (canonical, index, position,
                                            slug(seat))
            roles.append({
                "@type": "OrganizationRole",
                "@id": role_id,
                "roleName": rec.get("role") or section["holder"],
                "namedPosition": seat,
                "member": person_node(rec, name_field, section),
            })
            items.append({"@type": "ListItem", "position": position,
                          "name": seat, "item": {"@id": role_id}})
        graph.append(organization(section, org_id, section["org"], roles))
        graph.append({
            "@type": "ItemList",
            "@id": "%s#roster-%d" % (canonical, index),
            "name": section["heading"],
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "numberOfItems": len(items),
            "about": {"@id": org_id},
            "itemListElement": items,
        })
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         indent=2, ensure_ascii=False)
    return ('  <script type="application/ld+json">\n%s\n  </script>\n\n'
            % payload)


def render(entry):
    worksheet = load(entry["worksheet"])
    verified = worksheet.get("verified_date")
    if not verified:
        fail("%s has no verified_date and the table is dated with it"
             % entry["worksheet"])
    sections = [(s, section_rows(entry["tag"], s)) for s in entry["sections"]]
    tables = "".join(render_section(entry["tag"], s, verified)
                     for s in entry["sections"])
    return tables + render_graph(entry, sections)


def apply(entry, body, check):
    rel = os.path.join(entry["tag"], entry["page"])
    path = os.path.join(REPO_ROOT, rel)
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    if BEGIN in text:
        i = text.index(BEGIN) + len(BEGIN)
        j = text.index(END)
        current = text[i:j].strip("\n")
        if current == body.rstrip("\n"):
            return ("current", rel, None)
        if check:
            return ("drift", rel, (current, body.rstrip("\n")))
        new = text[:i] + "\n" + body.rstrip("\n") + "\n" + text[j:]
    else:
        if check:
            return ("missing", rel, None)
        if ANCHOR not in text:
            fail("%s has no 'Related lookups' section to sit above" % rel)
        new = text.replace(ANCHOR, BEGIN + "\n" + body.rstrip("\n") + "\n" + END + "\n" + ANCHOR, 1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    return ("written", rel, None)


def verify_shipped(entry):
    """Read the page BACK and find every name the roster carries.

    Byte-equality proves the region matches what render() produces today, and
    would pass a correct, empty template every time — the property
    build_county_pages.py had to be given after the fact. This asks the other
    question: is the person in the file a reader downloads. Escaped, because
    O'Brien ships as O&#x27;Brien.
    """
    rel = os.path.join(entry["tag"], entry["page"])
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as f:
        shipped = f.read()
    named = 0
    for section in entry["sections"]:
        field = section.get("name_field", "name")
        rows = section_rows(entry["tag"], section)
        missing = [seat for seat, rec in rows if rec.get(field)
                   and html.escape(rec[field]) not in shipped]
        if missing:
            fail("%s does not name %d of %s's members (%s) — the table is "
                 "present and does not carry them"
                 % (rel, len(missing), section["roster"], ", ".join(missing[:5])))
        named += sum(1 for _seat, rec in rows if rec.get(field))
    return named


WORKFLOWS = os.path.join(REPO_ROOT, ".github", "workflows")


def check_workflows():
    """A workflow that rewrites a tabled roster must regenerate the table.

    This is the rule build_county_pages.py already enforces for the 170
    per-county pages. Without it the failure lands on the bot's own PR: the
    weekly job rewrites the roster, the page still names last week's members,
    and --check goes red on a PR nobody wrote. Catching it here instead names
    the workflow and the two lines it is missing, before that ever happens.
    """
    seen = set()
    for entry in TABLES:
        page = "%s/%s" % (entry["tag"], entry["page"])
        for section in entry["sections"]:
            roster = roster_path(entry["tag"], section["roster"])
            for name in sorted(os.listdir(WORKFLOWS)):
                if not name.endswith((".yml", ".yaml")):
                    continue
                with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as f:
                    text = f.read()
                if ("git add" not in text) or (roster not in text):
                    continue
                if "build_officeholder_tables.py" not in text:
                    fail(".github/workflows/%s rewrites %s and never regenerates "
                         "%s — add a step running python3 "
                         "scripts/build_officeholder_tables.py and `git add %s`"
                         % (name, roster, page, page))
                if page not in text:
                    fail(".github/workflows/%s regenerates the table and never "
                         "commits it — add `git add %s`" % (name, page))
                if (name, page) not in seen:
                    seen.add((name, page))
                    print("build-officeholder-tables: %s regenerates %s"
                          % (name, page))


def audit_not_yet():
    """An entry that has stopped being true is a hole in the record."""
    for e in NOT_YET:
        roster = os.path.join(REPO_ROOT, e["tag"], "data", "app", e["roster"])
        if os.path.exists(roster):
            fail("NOT_YET records %s/%s as having no shipped roster (%s), and "
                 "%s/data/app/%s now exists — add it to TABLES and drop the entry"
                 % (e["tag"], e["page"], e["date"], e["tag"], e["roster"]))
        page = os.path.join(REPO_ROOT, e["tag"], e["page"])
        if not os.path.exists(page):
            fail("NOT_YET records %s/%s and that page is gone — drop the entry"
                 % (e["tag"], e["page"]))
        print("build-officeholder-tables: ~ %s/%s has no table (%s): %s"
              % (e["tag"], e["page"], e["date"], e["reason"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()

    drifted, missing, seats = [], [], 0
    for entry in TABLES:
        body = render(entry)
        state, rel, detail = apply(entry, body, args.check)
        seats += body.count("itemtype=")
        if state == "drift":
            drifted.append((rel, detail))
        elif state == "missing":
            missing.append(rel)
        elif state == "written":
            print("build-officeholder-tables: %s — table written" % rel)
        if state != "drift" and state != "missing":
            verify_shipped(entry)
    audit_not_yet()
    check_workflows()

    if args.check:
        for rel in missing:
            print("build-officeholder-tables: %s has no %s region" % (rel, REGION),
                  file=sys.stderr)
        for rel, (cur, new) in drifted:
            print("build-officeholder-tables: DRIFT in %s" % rel, file=sys.stderr)
            for dl in difflib.unified_diff(cur.splitlines(), new.splitlines(),
                                           fromfile="committed",
                                           tofile="regenerated", lineterm="", n=1):
                print("  " + dl, file=sys.stderr)
        if missing or drifted:
            fail("%d table(s) out of date — run "
                 "python3 scripts/build_officeholder_tables.py"
                 % (len(missing) + len(drifted)))
        print("build-officeholder-tables: OK — %d table(s), %d officeholder(s) in "
              "the served bytes, %d seat(s) recorded as not tabled yet"
              % (len(TABLES), seats, len(NOT_YET)))
    else:
        print("build-officeholder-tables: OK — %d table(s), %d officeholder(s)"
              % (len(TABLES), seats))


if __name__ == "__main__":
    main()
