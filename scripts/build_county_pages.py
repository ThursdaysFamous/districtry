#!/usr/bin/env python3
"""
One crawlable page per county board in the fleet, naming every member.

WHY THIS EXISTS. Measured 2026-09-13: across all 51 authored HTML pages on
this site, NOT ONE OFFICEHOLDER NAME appears. The rosters are real — 2,574
seats across 164 counties in three states, every seat named, most with an
e-mail or a phone — and every one of them reaches a reader only after
JavaScript fetches a JSON file and renders a card. A crawler sees a map and a
toggle list. So the site that knows who holds those seats publishes that fact
nowhere a search engine can read it, and someone typing "who is on the LaSalle
County board" is answered by everyone except the project built to answer it.

WHY A PAGE PER COUNTY AND NOT PER DISTRICT. The obvious reading is one page per
seat, which is 2,574 of them. Two reasons not to: the queries people actually
type are county-level far more often than district-level, and a page whose
whole content is one name and a phone number is the shape search engines treat
as thin. A county page carries every name in the county — the same crawlable
text at a fraction of the page count, with an anchor per district so a link to
one seat still lands on it. Per-district pages remain possible later; this
decides nothing against them.

WHAT IS ON A PAGE, AND WHAT IS NOT. Everything comes from the shipped roster
the app itself reads, so the page and the card cannot disagree — that is the
point of generating it rather than writing it. A field the roster does not
carry is absent from the page rather than blank: no "email: —", no invented
office. A district the roster leaves empty says so in the app's own words
rather than being skipped, because a board of eighteen showing seventeen seats
reads as complete and is not. Nothing here is guessed, and nothing is
reformatted beyond escaping and one stated party-spelling table.

HOW A NEW STATE'S COUNTIES GET PAGES. Two halves, and the second is the one
that makes it automatic.

  The INSTANCES registry holds one entry per state that publishes county
  officeholders, and the entry holds WORDING and an ADAPTER NAME. It never
  holds a list of counties: every adapter enumerates whatever its roster
  carries, so a county's page appears the run after its roster ships and
  disappears the run after it leaves. Illinois gained Menard and Lake that way
  on introduction; no list was edited.

  check_registration() is what covers a state that is not in the registry at
  all. It walks every instance's data/app, finds each file whose records name
  people and look county-shaped, subtracts what the adapters read, and FAILS on
  anything left over — naming the file and the two ways to clear it: write an
  adapter, or record in NOT_COUNTY_BOARDS why these pages are the wrong home
  for it. So a new state's county roster cannot land quietly. Nobody has to
  remember, and nothing is generated from a guess about a shape nobody has
  looked at. Michigan is the case it is written for: it ships county
  commissioner DISTRICTS and no names, so it has no entry and nothing to flag,
  and the day a roster arrives this gate asks for one.

FOUR ROSTER SHAPES, because the three states genuinely differ and a schema
describing all four would be longer than the four adapter functions:

  il_districted  55 files, one per county, keyed by district. Three record
                 shapes share those files — see the adapter.
  il_at_large    one file for the 20 counties that elect countywide. These
                 pages say so outright, which is the answer to "what district
                 am I in" for a fifth of the counties Illinois serves.
  wi_seats       one file keyed by SEAT, every record naming its own county.
                 Four things a record can be: a name, a vacancy, a withheld
                 district with a printed reason, or a county's at-large list.
  ia_supervisors one file keyed by county with districts nested, plus a
                 separate chairs file joined by name onto the members.

THE COUNTY NAME AND SLUG ARE NOT A NEW TABLE. Illinois's come from
build_county_status.py's ALL_COUNTIES and slug_of(), which the county-status
page and the coverage ring already use; Wisconsin's and Iowa's records name
their own county, so those slugs are derived and no list can go stale. A roster
file this script cannot place is a failure, not a skip.

  python3 scripts/build_county_pages.py            # (re)generate in place
  python3 scripts/build_county_pages.py --check    # the CI drift gate
"""

import glob
import json
import os
import re
import subprocess
import sys
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    """Stop, naming THIS script. build_privacy_page exports a fail() and this
    file used to borrow it, so a missing GENERATED region in wi/county-board.html
    reported itself as `build-privacy-page: FAIL` — a reader's first move on
    that line is to open the wrong generator."""
    print("build-county-pages: FAIL — %s" % msg, file=sys.stderr)
    raise SystemExit(1)

from build_landing_page import (  # noqa: E402
    FAVICON, FONTFACE, TOKENS, parse_token_block, read, token_css,
)
from build_privacy_page import (  # noqa: E402
    DARK_EXTRA, DARK_TOKENS, LIGHT_TOKENS, esc,
)
from build_history_page import shared_footer_byline, shared_goatcounter  # noqa: E402
from build_county_status import ALL_COUNTIES, scan_dispatch_tables, slug_of  # noqa: E402

# A county whose shipped roster names NOBODY. A page for it would be a page
# about a county board with no officeholder on it, which is the opposite of
# why these pages exist — and it would fail this work's own test that a
# generated URL names someone. Recorded with what the roster does carry, and
# re-audited: the moment the roster starts naming people the entry is stale
# and the build fails, which is the property ACCEPTED_DROPS had to be given
# after the fact.
#
# KEYED "<instance tag>/<county>", not by county name. Illinois and Wisconsin
# both have a Winnebago County, Wisconsin has a county named IOWA, and eleven
# other names are shared between the two states — a bare county name would let
# an entry written about one state silence a real regression in another.
NAMES_NOBODY = {}
# It is EMPTY since 2026-10-15. From 2026-10-11 it carried North Carolina's
# Tyrrell, whose board seats the election results alone could not settle
# until the county's own page was read. Before that it was empty from
# 2026-09-15, and carried one entry from 2026-09-13 — Illinois's Winnebago, whose data/app file is 20 flat records
# with an e-mail, a phone and a source URL and no name field anywhere, because
# the card reads the member from WinGIS live. il_gis_board_scraper.py
# snapshotted those names on 2026-09-15 and this gate FAILED the build on the
# stale entry, which is what it is for.

# ——— the fleet registry ———
#
# One entry per instance that publishes county-level officeholders. `adapters`
# names the reader functions below; everything else is reader-facing wording.
# WHAT IS NEVER CONFIGURED IS WHICH COUNTIES EXIST — every adapter enumerates
# whatever its roster carries, so a county's page appears the run after its
# roster ships and disappears the run after it leaves. That is the whole
# mechanism for "as counties come online": there is no list to update.
#
# An adapter is CODE rather than a schema because the three shipped roster
# shapes are genuinely different (per-county files keyed by district; one file
# keyed by seat; one file keyed by county with districts nested), and a
# declarative description of all three would be longer than the three
# functions. The instance's OWN county names come from the roster wherever the
# roster carries them (wi, ia) and from the state's canonical list only where
# it does not (il, whose filenames are slugs).
# WORDING IS FIVE KEYS RATHER THAN ONE, because one noun cannot do all five
# jobs and a single `body` key produced "Menominee County County Board" on
# every Wisconsin page in the first draft:
#
#   heading      what follows the county name — the h1, the schema name, the
#                description subject. "Adams County Board", "Adams County
#                Board of Supervisors".
#   page_title   the <title>, which is the search result's own line, so it
#                carries the word a reader would type. Illinois's board has
#                "members"; Wisconsin's members are supervisors.
#   phrase       the body's name in running prose, lower case.
#   index_label  the breadcrumb's middle step and the topic page's own name.
#   all_label    the footer link back to that page.
INSTANCES = [
    dict(tag="il", state="Illinois", concept="county-board",
         index_page="county-board.html",
         heading="%(county)s County Board",
         page_title="%(county)s County Board members",
         phrase="county board", index_label="County boards",
         all_label="All Illinois county boards",
         app_name="districtry Illinois", app_url="https://districtry.com/il/",
         district_word="District", member_word="County Board Member",
         adapters=("il_districted", "il_at_large"),
         contacts="il_clerk_contact"),
    dict(tag="wi", state="Wisconsin", concept="county-board",
         index_page="county-board.html",
         heading="%(county)s County Board",
         page_title="%(county)s County Board supervisors",
         phrase="county board", index_label="County boards",
         all_label="All Wisconsin county boards",
         app_name="districtry Wisconsin", app_url="https://districtry.com/wi/",
         district_word="District", member_word="Supervisor",
         adapters=("wi_seats",),
         contacts="wi_clerk_contact"),
    dict(tag="ia", state="Iowa", concept="county-supervisor",
         index_page="county-supervisor.html",
         heading="%(county)s County Board of Supervisors",
         page_title="%(county)s County Board of Supervisors",
         phrase="board of supervisors", index_label="Boards of supervisors",
         all_label="All Iowa boards of supervisors",
         app_name="districtry Iowa", app_url="https://districtry.com/ia/",
         district_word="District", member_word="Supervisor",
         adapters=("ia_supervisors", "ia_at_large"),
         contacts="ia_board_contact"),
    dict(tag="mi", state="Michigan", concept="county-commissioner",
         index_page="county-commissioner.html",
         heading="%(county)s County Board of Commissioners",
         # The <title> is shorter than the <h1> here alone, and deliberately:
         # "Kalamazoo County Board of Commissioners — districtry Michigan" is
         # 61 characters against validate_serp_lengths.py's 60, so a search
         # result would cut the last of it. "County Commissioners" is what the
         # members are called and what a reader searches, and it leaves room —
         # Grand Traverse, Michigan's longest county name, lands at 57.
         page_title="%(county)s County Commissioners",
         phrase="board of commissioners", index_label="Boards of commissioners",
         all_label="All Michigan boards of commissioners",
         app_name="districtry Michigan", app_url="https://districtry.com/mi/",
         district_word="District", member_word="Commissioner",
         adapters=("mi_commissioners",),
         # a third of these counties name certified 2024 winners, so "each
         # name published by the county itself" was false of them
         index_provenance="each name from the county's own board page or, "
                          "where that county's page says so, from the state's "
                          "certified results of the November 2024 election"),
    # MINNESOTA NAMES ELECTION WINNERS, NOT A COUNTY'S OWN LIST. Every county
    # board here is elected by district (Minn. Stat. 375.025), and the names
    # are each seat's most recent winner in the Secretary of State's results,
    # so the pages carry the Michigan certified-returns wording rather than
    # "the county's own published roster", and the index says so too.
    dict(tag="mn", state="Minnesota", concept="county-commissioner",
         index_page="county-commissioner.html",
         heading="%(county)s County Board of Commissioners",
         page_title="%(county)s County Commissioners",
         # "Lake of the Woods County Commissioners — districtry Minnesota"
         # is 61 characters against validate_serp_lengths.py's 60, so a
         # title that would overrun drops the word "County" instead, and
         # only that one county's does.
         page_title_short="%(county)s commissioners",
         phrase="board of commissioners", index_label="Boards of commissioners",
         all_label="All Minnesota boards of commissioners",
         app_name="districtry Minnesota", app_url="https://districtry.com/mn/",
         district_word="District", member_word="Commissioner",
         adapters=("mn_commissioners",),
         index_provenance="each name the winner of that seat's most recent "
                          "election in the Minnesota Secretary of State's "
                          "results, dated to it"),
    # INDIANA NAMES ELECTION WINNERS TOO, from the Election Division's
    # certified results, and its seats are not all numbered: 15 counties name
    # theirs ("Middle District", "Western District"), so `district_word` is
    # empty and every label is whole. There is no commissioner-district layer
    # yet, so the map link opens the county layer, whose card lists the board.
    dict(tag="in", state="Indiana", concept="county-commissioner",
         index_page="county-commissioner.html",
         heading="%(county)s County Board of Commissioners",
         page_title="%(county)s County Commissioners",
         page_title_short="%(county)s commissioners",
         phrase="board of commissioners", index_label="Boards of commissioners",
         all_label="All Indiana boards of commissioners",
         app_name="districtry Indiana", app_url="https://districtry.com/in/",
         district_word="", member_word="Commissioner",
         cta_layers="county",
         adapters=("in_commissioners",),
         index_provenance="each name the winner of that seat's most recent "
                          "election in the Indiana Election Division's "
                          "certified results, dated to it"),
    # OKLAHOMA NAMES THE STATE ELECTION BOARD'S ROSTER, A DATED SNAPSHOT.
    # Every county elects three commissioners from three districts (19 O.S.
    # 321), and the Board's Roster of State and County Officers lists all
    # three after each general election, holdovers included. It is not kept
    # current between elections, so the pages say when it was compiled.
    dict(tag="ok", state="Oklahoma", concept="county-commissioner",
         index_page="county-commissioner.html",
         heading="%(county)s County Board of Commissioners",
         page_title="%(county)s County Commissioners",
         page_title_short="%(county)s commissioners",
         phrase="board of county commissioners", index_label="Boards of county commissioners",
         all_label="All Oklahoma boards of county commissioners",
         app_name="districtry Oklahoma", app_url="https://districtry.com/ok/",
         district_word="District", member_word="Commissioner",
         adapters=("ok_commissioners",),
         contacts="ok_county_contact",
         vacancy_phrase="as the State Election Board's roster listed it",
         index_provenance="each name from the Oklahoma State Election Board's "
                          "Roster of State and County Officers, compiled after "
                          "the general election it is dated to"),
    # NORTH CAROLINA NAMES ELECTION WINNERS TOO, from the State Board of
    # Elections' results read with its filing lists, and many boards elect
    # several seats in one contest, so a label ("Board seat", "At large")
    # holds more than one member and `district_word` is empty for the same
    # reason as Indiana's. There is no commissioner-district layer, so the map
    # link opens the county layer, whose card lists the board.
    dict(tag="nc", state="North Carolina", concept="county-commissioner",
         index_page="county-commissioner.html",
         heading="%(county)s County Board of Commissioners",
         page_title="%(county)s County Commissioners",
         page_title_short="%(county)s commissioners",
         phrase="board of commissioners", index_label="Boards of commissioners",
         all_label="All North Carolina boards of commissioners",
         app_name="districtry North Carolina", app_url="https://districtry.com/nc/",
         district_word="", member_word="Commissioner",
         cta_layers="county",
         adapters=("nc_commissioners",),
         index_provenance="each name the winner of that seat's most recent "
                          "election in the North Carolina State Board of "
                          "Elections' results, dated to it"),
    # KENTUCKY'S GOVERNING BODY IS NOT ONE BODY. 118 counties are governed by a
    # fiscal court, and Jefferson and Fayette by the councils of the merged
    # Louisville Metro and Lexington-Fayette governments, so the concept path
    # is the county's government rather than the fiscal court, and those two
    # pages take their own heading from `heading_for` rather than calling a
    # metro council a fiscal court. The names come from the state's county
    # directory, which says nothing about districts, so every page is the flat
    # shape and none claims an election method it was not told.
    dict(tag="ky", state="Kentucky", concept="county-government",
         index_page="county-government.html",
         heading="%(county)s County Fiscal Court",
         heading_for={"Jefferson": "Louisville Metro Council",
                      "Fayette": "Lexington-Fayette Urban County Council"},
         page_title="%(county)s County Fiscal Court",
         page_title_for={"Jefferson": "Louisville Metro Council",
                         "Fayette": "Lexington-Fayette Urban Council"},
         phrase="fiscal court", index_label="County governments",
         all_label="All Kentucky county governments",
         app_name="districtry Kentucky", app_url="https://districtry.com/ky/",
         district_word="District", member_word="Magistrate",
         adapters=("ky_county_governments",),
         index_provenance="each name as the Kentucky Department for Local "
                          "Government's county directory lists it"),
    # SOUTH CAROLINA NAMES ELECTION WINNERS, from the State Election
    # Commission's certified results, and reads each county's own council page
    # beside them, so a seat the county lists differently says so on its line.
    # Every county has had an elected council since the Home Rule Act of 1975.
    # A chair, supervisor or at-large member elected countywide gets a section
    # of its own, and Hampton and Jasper, whose members are all elected
    # countywide, are the at-large shape.
    dict(tag="sc", state="South Carolina", concept="county-council",
         index_page="county-council.html",
         heading="%(county)s County Council",
         page_title="%(county)s County Council",
         phrase="county council", index_label="County councils",
         all_label="All South Carolina county councils",
         app_name="districtry South Carolina", app_url="https://districtry.com/sc/",
         district_word="District", member_word="Council member",
         adapters=("sc_councils",),
         index_provenance="each name the winner of that seat's most recent "
                          "election in the South Carolina Election "
                          "Commission's certified results, dated to it"),
    # TENNESSEE NAMES WHAT EACH COUNTY'S OWN PAGE LISTS, county by county as
    # the roster reaches them, so a county the roster has not read has no page
    # rather than one naming nobody. Every county elects its commission from
    # districts, often two or three members from one district, and Nashville
    # and Davidson County's body is the Metro Council, which its record names.
    dict(tag="tn", state="Tennessee", concept="county-commissioner",
         index_page="county-commissioner.html",
         heading="%(county)s County Commission",
         page_title="%(county)s County Commissioners",
         phrase="county commission", index_label="County commissions",
         all_label="All Tennessee county commissions",
         app_name="districtry Tennessee", app_url="https://districtry.com/tn/",
         district_word="District", member_word="Commissioner",
         adapters=("tn_commissioners",),
         index_provenance="each name from the county's own published list of "
                          "its commission, read every week"),
    # ARKANSAS'S GOVERNING BODY IS THE QUORUM COURT, AND ITS PRESIDING OFFICER
    # IS NOT ONE OF ITS MEMBERS. Every county elects a county judge, who runs
    # the county and presides over the quorum court without a vote (Ark.
    # Const. amend. 55), and nine to fifteen justices of the peace, one from
    # each district. The judge is a section of its own; a justice is named by
    # district only where the district card names one, from the county's own
    # numbered list or the association's 2024 results (Adam's rulings of
    # 2026-10-13), and the justices no source places in a district are listed
    # after the districts rather than dropped.
    dict(tag="ar", state="Arkansas", concept="quorum-court",
         index_page="quorum-court.html",
         heading="%(county)s County Quorum Court",
         page_title="%(county)s County Quorum Court",
         phrase="quorum court", index_label="Quorum courts",
         all_label="All Arkansas quorum courts",
         app_name="districtry Arkansas", app_url="https://districtry.com/ar/",
         district_word="District", member_word="Justice of the Peace",
         adapters=("ar_quorum_courts",),
         index_provenance="each county judge from the Arkansas Judiciary's "
                          "directory, and each justice of the peace named by "
                          "district from the county's own list or from the "
                          "Association of Arkansas Counties' 2024 election "
                          "results"),
    # MISSISSIPPI NAMES WHAT THE SECRETARY OF STATE'S DIRECTORY PRINTS. Every
    # county is run by a board of five supervisors, one from each district,
    # and five counties call their districts beats, so `district_word` is
    # empty and every label is whole ("District 3", "Beat 3"), the way the
    # app's cards print them. The directory is published once a year, so the
    # pages name its edition and never a schedule.
    dict(tag="ms", state="Mississippi", concept="county-supervisor",
         index_page="county-supervisor.html",
         heading="%(county)s County Board of Supervisors",
         # "Jefferson Davis County Board of Supervisors — districtry
         # Mississippi" is 68 characters against validate_serp_lengths.py's
         # 60; "County Supervisors" is what the members are called, and
         # Jefferson Davis, the longest county name, lands at 59.
         page_title="%(county)s County Supervisors",
         phrase="board of supervisors", index_label="Boards of supervisors",
         all_label="All Mississippi boards of supervisors",
         app_name="districtry Mississippi", app_url="https://districtry.com/ms/",
         district_word="", member_word="Supervisor",
         adapters=("ms_supervisors",),
         contacts="ms_board_contact",
         vacancy_phrase="as the Secretary of State's directory lists it",
         index_provenance="each name as the Mississippi Secretary of State's "
                          "County Offices and Directory lists it, by district "
                          "or beat"),
    # LOUISIANA'S COUNTIES ARE PARISHES, and every parish elects its governing
    # body from districts: a police jury in 38, a council in 25 (two of them
    # the councils of a city and parish that share one government, New
    # Orleans's and Baton Rouge's) and Caddo's parish commission. So the concept
    # path is the parish's government rather than any one body, as Kentucky's
    # is, and every record names its own body. The names are the Secretary of
    # State's list of elected officials, the record the app's Parish card
    # reads, so the pages say the day it was read and never a schedule beyond
    # the weekly re-read. `county_word` and its two siblings put "Parish"
    # wherever a page says "County"; `district_layer` is the map layer, which
    # is not the concept path here.
    dict(tag="la", state="Louisiana", concept="parish-government",
         index_page="parish-government.html",
         # Every record carries its own heading and title; these two are what
         # a record without them would read.
         heading="%(county)s Parish governing body",
         page_title="%(county)s Parish governing body",
         phrase="police jury or parish council", index_label="Parish governments",
         all_label="All Louisiana parish governments",
         app_name="districtry Louisiana", app_url="https://districtry.com/la/",
         district_word="", member_word="Member",
         county_word="Parish", county_noun="parish", county_plural="parishes",
         district_layer="parish-district",
         adapters=("la_parish_bodies",),
         contacts="la_board_contact",
         index_provenance="each name as the Louisiana Secretary of State's list "
                          "of elected officials prints it, by district or ward"),
    # NEW YORK IS THE FIRST INSTANCE WHOSE COUNTIES DO NOT ALL HAVE A BODY
    # THESE PAGES CAN BE ABOUT, which is why its `phrase` names one form
    # rather than the county tier: a county legislature is elected from
    # districts, a board of supervisors is the towns' own supervisors
    # sitting ex officio, and Otsego's board of representatives is its own
    # question. The adapter enumerates whatever ships and the form is
    # proven per county first, so this list never names a county.
    dict(tag="ny", state="New York", concept="county-legislature",
         index_page="county-legislature.html",
         heading="%(county)s County Legislature",
         page_title="%(county)s County Legislature",
         phrase="county legislature", index_label="County legislatures",
         all_label="All New York county legislatures",
         app_name="districtry New York", app_url="https://districtry.com/ny/",
         district_word="District", member_word="Legislator",
         adapters=("ny_legislature",)),
    # THE SECOND NEW YORK ENTRY, and the first time one state holds two. A
    # county legislature and a board of supervisors are two bodies with two
    # names and two kinds of seat, so neither entry's wording can describe the
    # other. `district_word` is empty because the seat here is a town or a
    # city, not a district, and the label says which.
    dict(tag="ny", state="New York", concept="county-supervisor",
         index_page="county-supervisor.html",
         heading="%(county)s County Board of Supervisors",
         # Shorter than the <h1> for the Michigan reason: "Cattaraugus County
         # Board of Supervisors — districtry New York" is 65 characters against
         # validate_serp_lengths.py's 60, so a search result would cut the end
         # of it. "County Supervisors" is what the members are called.
         page_title="%(county)s County Supervisors",
         phrase="board of supervisors", index_label="Boards of supervisors",
         all_label="All New York boards of supervisors",
         app_name="districtry New York", app_url="https://districtry.com/ny/",
         district_word="", member_word="Supervisor",
         adapters=("ny_supervisors",)),
]


# AN INSTANCE WHOSE ADAPTER IS SETTLED AND WHOSE PAGES ARE HELD. Nothing here
# renders, indexes or counts these: they exist so that build_eam_status.py's
# scorecard reads the county tier through the same adapter the pages will use,
# rather than through a second reader of the same file. An instance is held
# while it is dark, with a NOT_COUNTY_BOARDS entry saying so, and its go-live
# moves it into INSTANCES with the page wording beside it and drops that
# entry; the adapter does not change. South Carolina was the first, and moved
# at its go-live; none is held today.
HELD_INSTANCES = []


def heading_of(inst, county, rec=None):
    """The body's name for one county. A RECORD MAY NAME ITS OWN BODY, because
    one state can hold counties whose legislative body is not the one the
    instance's wording describes: Tennessee's county commissions sit beside
    the Metro Council of Nashville and Davidson County, one metropolitan
    government whose council is that county's legislative body. An instance
    may also name a county's body in `heading_for` (Kentucky's two merged
    governments). A county with neither reads exactly as before."""
    if rec and rec.get("heading"):
        return rec["heading"]
    own = (inst.get("heading_for") or {}).get(county)
    return own or inst["heading"] % {"county": county}


def inst_key(inst):
    """The registry key for one entry.

    IT IS NOT THE TAG, because a state can elect its county boards in more
    than one FORM and each form needs its own wording, concept path and index
    page. New York is the first: a county that elects a legislature from
    districts and a county governed by a board of supervisors are two bodies
    with two names, so New York holds two entries. Keying the per-run tables on
    the tag made the second silently replace the first."""
    return "%s/%s" % (inst["tag"], inst["concept"])


INDEX_REGION = "county-index"

# Illinois alone needs a name table: its roster FILENAMES are slugs and its
# records carry no county field. Wisconsin's and Iowa's records name their own
# county, so those slugs are derived and no list can go stale.
IL_NAME_BY_SLUG = {slug_of(n): n for n, _ in ALL_COUNTIES}
IL_NAME_BY_UPPER = {n.upper(): n for n, _ in ALL_COUNTIES}


def county_slug(name):
    """A county name to its URL slug. Measured on the shipped rosters: 72
    Wisconsin and 17 Iowa names produce 72 and 17 distinct slugs, no
    collisions, and the five two-word Wisconsin names (Eau Claire, Fond Du Lac,
    Green Lake, La Crosse, St Croix) hyphenate cleanly."""
    return (name.lower().replace(".", "").replace("'", "")
            .replace(" ", "-").replace("--", "-"))


def app_data(tag):
    return os.path.join(REPO_ROOT, tag, "data", "app")


def out_dir(inst):
    return os.path.join(REPO_ROOT, inst["tag"], inst["concept"])


def index_page(inst):
    return os.path.join(REPO_ROOT, inst["tag"], inst["index_page"])


def district_sort_key(key):
    """Districts are '1'..'30' in most counties and letters ('A'..'N') in Clay.
    Sort numerics numerically and letters after them, so a page reads 1, 2, 10
    rather than 1, 10, 2."""
    return (0, int(key), "") if key.isdigit() else (1, 0, key)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seat_heading(inst, label):
    """The words over one seat's section.

    MOST SEATS ARE CALLED DISTRICTS AND ONE FORM IS NOT. A New York county
    governed by a board of supervisors seats the towns and cities themselves,
    so the seat's name IS "Town of Ballston" and prefixing it with a district
    word would print "District Town of Ballston". Such an entry sets
    `district_word` to the empty string and the label carries the whole of it.
    Every other instance is unchanged, because a non-empty word still joins the
    label exactly as it did."""
    word = inst["district_word"]
    return "%s %s" % (word, label) if word else label


def district(label, members=(), vacancies=0, note=None, alias=None):
    """One district on a page. A DICT rather than a tuple because a district
    that names nobody can be three different things and a reader has to be told
    which: the county says the seat is vacant (`vacancies`), somebody says why
    no name can be shown (`note` — Wisconsin's one withheld district), or
    nothing is published at all (neither). Wisconsin's own card has drawn that
    distinction since it shipped; these pages draw the same one.

    `alias` is the county's own name for a district the state's map numbers
    (Dyer, Tennessee, letters its districts A to J): printed beside the
    number in the heading, never in place of it, because the number is what
    the map, the anchor and the app's card all use."""
    return {"label": str(label), "members": list(members),
            "vacancies": vacancies, "note": note, "alias": alias}


def district_heading(inst, d):
    """A district section's heading, ONE copy for the page and for the
    read-back that proves every district is on it: the instance's own wording
    for the number, and the county's own name for it beside that where the
    county uses another (`alias`)."""
    heading = seat_heading(inst, d["label"])
    if d.get("alias"):
        heading = "%s (the county's %s)" % (heading, d["alias"])
    return heading


def _slug_of(path):
    return re.sub(r"-(county-board-members|commissioner-members|"
                  r"county-board-roles)\.json$", "", os.path.basename(path))


def _resolve_duplicate_slugs(paths):
    """One county, one roster file — and where there are two, data/source wins.

    A county can legitimately have a file in BOTH directories. Winnebago does:
    data/app carries the CONTACT its GIS declares and never fills, joined by the
    card as an enrichment, while data/source carries the members snapshotted
    from that same GIS so this generator has names to put on a page. Before this
    ran, `sorted()` decided which one won — alphabetically, app before source —
    and the later one silently replaced the earlier. It happened to produce the
    right page and would have produced a county naming nobody if the two
    directory names had sorted the other way.

    So the rule is stated rather than incidental: the data/source file wins,
    because it is the one this generator is FOR, and the data/app file must not
    name anybody it does not. A county whose app roster names a member the
    source roster has never heard of is a real disagreement between two files
    about who holds a seat, and it fails rather than picking one.
    """
    by_slug, problems = {}, []
    for path in paths:
        by_slug.setdefault(_slug_of(path), []).append(path)
    keep = []
    for slug, found in sorted(by_slug.items()):
        if len(found) == 1:
            keep.append(found[0])
            continue
        source = [p for p in found if os.sep + "source" + os.sep in p]
        app = [p for p in found if p not in source]
        if len(source) != 1 or len(app) != 1:
            problems.append(
                "%s has %d roster files and this can only resolve one app file "
                "against one source file: %s"
                % (slug, len(found),
                   ", ".join(os.path.relpath(p, REPO_ROOT) for p in sorted(found))))
            continue
        named_in_app = {
            (r.get("name") or "").strip()
            for r in _read(app[0]).values() if isinstance(r, dict)
        } | {
            (m.get("name") or "").strip()
            for r in _read(app[0]).values() if isinstance(r, dict)
            for m in (r.get("members") or []) if isinstance(m, dict)
        }
        named_in_app.discard("")
        named_in_source = {
            (m.get("name") or "").strip()
            for r in _read(source[0]).values() if isinstance(r, dict)
            for m in (r.get("members") or []) if isinstance(m, dict)
        } | {
            (r.get("name") or "").strip()
            for r in _read(source[0]).values() if isinstance(r, dict)
        }
        named_in_source.discard("")
        orphaned = sorted(named_in_app - named_in_source)
        if orphaned:
            problems.append(
                "%s: %s names %s, whom %s does not — two files disagreeing "
                "about who holds a seat on one board"
                % (slug, os.path.relpath(app[0], REPO_ROOT),
                   ", ".join(orphaned[:4]),
                   os.path.relpath(source[0], REPO_ROOT)))
            continue
        print("build-county-pages: %s reads %s and takes %s for its names"
              % (slug, os.path.relpath(app[0], REPO_ROOT),
                 os.path.relpath(source[0], REPO_ROOT)))
        keep.append(source[0])
    return sorted(keep), problems


def il_districted(inst):
    """Illinois: one file per county, keyed by district.

    THREE RECORD SHAPES SHARE THESE FILES, surveyed key by key rather than
    assumed, and the survey is what makes this correct:

      members[]     53 files. The district and its member list.
      a flat EXTRA  11 files carry one beside the districts — an office
                    address, a clerk phone, a meeting time, a results URL.
                    No `members`, no `name`: not a district, skipped, counted.
      a flat NAMED  the board chair in five files, and in Lake County EVERY
                    district (20 of them, `{"1": {"name": "..."}}`). A flat
                    record that names somebody is a person either way — the
                    `chair` key is the chair, anything else is that district's
                    member.

    THE FILENAME GLOB IS THREE PATTERNS, NOT ONE, and that is a defect this
    generator shipped with: `*-county-board-members.json` alone missed Menard,
    whose file is `menard-commissioner-members.json` (a commission-form county,
    named for what it elects), and Lake, whose file is
    `lake-county-board-roles.json`. Both are real Illinois counties with real
    published members and neither had a page for a day. The registration gate
    below is what found them."""
    data_dir = app_data(inst["tag"])
    # TWO DIRECTORIES, AND THE SECOND ONE HAS A REASON. data/app is where a
    # roster lives when the APP reads it. Cook County's does not: il/index.html
    # fetches the county's GIS people table live on every Cook click, so a file
    # in data/app would fail validate_index.py's rule that every file there is
    # referenced — and Cook, the second most populous county in the country, had
    # no page at all while the Illinois hub's own prose named it. A roster the
    # app does not read is a build-time source and sits in data/source with the
    # rest of them; this reads both, because the reader of a county page does
    # not care which of the two the names came from.
    dirs = [data_dir, os.path.join(REPO_ROOT, inst["tag"], "data", "source")]
    # WHETHER THE MAP DRAWS A COUNTY'S DISTRICTS IS READ OFF THE APP'S OWN
    # DISPATCH TABLE, because a roster in data/source is not always Cook's case.
    # Bond, Bureau, Champaign, Marion and Piatt (measured 2026-10-20) have their
    # members read from their own websites and their districts drawn nowhere, so
    # their rosters sit in data/source with no county board entry in
    # il/index.html at all. Their pages said the map's card read the same source
    # live and offered to find the reader's district on the map, and neither was
    # true: no card reads those files and the map has no district to find. A
    # county the table names keeps the wording it had.
    with open(os.path.join(REPO_ROOT, inst["tag"], "index.html"), encoding="utf-8") as f:
        drawn = set(scan_dispatch_tables(f.read(), ()).get(inst["concept"], ()))
    if not drawn:
        fail("%s/index.html has no %s dispatch entries, so this cannot tell "
             "which counties' districts the map draws"
             % (inst["tag"], inst["concept"]))
    paths = sorted(set(
        path
        for d in dirs
        for pattern in ("*-county-board-members.json", "*-commissioner-members.json",
                        "*-county-board-roles.json")
        for path in glob.glob(os.path.join(d, pattern))))
    paths, problems = _resolve_duplicate_slugs(paths)
    out, nameless, used = {}, set(), []
    for path in paths:
        slug = re.sub(r"-(county-board-members|commissioner-members|"
                      r"county-board-roles)\.json$", "", os.path.basename(path))
        name = IL_NAME_BY_SLUG.get(slug)
        if name is None:
            problems.append(
                "%s names county slug %r, which build_county_status.ALL_COUNTIES "
                "does not carry — the two lists have diverged"
                % (os.path.relpath(path, REPO_ROOT), slug))
            continue
        used.append(path)
        data = _read(path)
        districts, skipped, source, extras = [], [], None, []
        # A roster build_il_gis_board_rosters.py KEPT because the county's
        # service did not answer carries `_notRead`, the date of the first run
        # that could not read it. It is a statement about the file, not a
        # district, and it changes what districted_body may say about the copy.
        not_read = data.get("_notRead") if isinstance(data.get("_notRead"), dict) else None
        for key in sorted(data, key=district_sort_key):
            if key == "_notRead":
                continue
            entry = data[key]
            if not isinstance(entry, dict):
                skipped.append(key)
                continue
            source = source or entry.get("sourceUrl")
            if isinstance(entry.get("members"), list):
                districts.append(district(key, entry["members"],
                                          entry.get("vacancies") or 0,
                                          entry.get("note")))
            elif not (entry.get("name") or "").strip():
                skipped.append(key)          # a per-county extra, not a district
            elif key == "chair":
                chair = dict(entry)
                chair.setdefault("role", "Chair")
                extras.append(("chair", "Board chair", [chair]))
            else:
                # A district whose one member is written flat rather than in a
                # members[] list — Lake County's whole file.
                districts.append(district(key, [dict(entry)]))
        named = _count_named(districts, extras)
        if not named:
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append(
                    "%s names nobody — %d key(s), no name field on any of them. "
                    "Either the roster regressed, or this county belongs in "
                    "NAMES_NOBODY with a reason"
                    % (os.path.relpath(path, REPO_ROOT), len(data)))
            nameless.add(name)
            continue
        rec = {"districts": districts, "sourceUrl": source, "extras": extras,
               "skipped": skipped, "slug": slug, "at_large": False,
               "source_file": path,
               "not_read_since": (not_read or {}).get("since")}
        if slug not in drawn:
            rec["undrawn"] = True
            rec["cta_layers"] = "county"
            rec["cta_note"] = ("Opens the map with the county layer on. This "
                               "board's districts are not on the map yet, so the "
                               "map cannot find your district.")
        out[name] = rec
    return out, problems, nameless, used, None


def il_at_large(inst):
    """Illinois: the shared file for counties that elect their board countywide."""
    path = os.path.join(app_data(inst["tag"]), "il-county-commissioners.json")
    out, problems = {}, []
    for key, entry in sorted(_read(path).items()):
        name = IL_NAME_BY_UPPER.get(key)
        if name is None:
            problems.append(
                "il-county-commissioners.json names %r, which "
                "build_county_status.ALL_COUNTIES does not carry" % key)
            continue
        out[name] = {"members": entry.get("members", []),
                     "structure": entry.get("structure"),
                     "verified": entry.get("verified"),
                     "sourceUrl": entry.get("sourceUrl"),
                     "sourceDocument": entry.get("sourceDocument"),
                     "seats": entry.get("seats"),
                     "slug": slug_of(name), "at_large": True}
    return out, problems, set(), [path], None


def wi_seats(inst):
    """Wisconsin: ONE file, keyed by SEAT — <5-digit county GEOID><2-digit
    district> — with the county name on every record, so the counties are
    read from the data and nothing here lists them.

    FOUR THINGS A SEAT RECORD CAN BE, and the app's own card already draws all
    four distinctions, so these pages draw them too rather than flattening
    three of them into silence:

      a name          1,573 of 1,591 seats.
      `vacant: true`  16 seats. The county says nobody holds it.
      `withheld`      one, Lincoln District 21: the county's map and the
                      state's filing put the boundary in different places, so
                      `withheldWhy` is printed instead of a name.
      `<fips>-at-large`
                      not a district at all. Menominee seats seven for five
                      districts, the other two elected countywide, under a key
                      carrying an `atLarge` LIST. Placing those two in a
                      district would say they represent ground they do not.

    A county's `seats` count comes from county-board-directory.json where that
    file carries one, because a board of twenty showing nineteen members reads
    as complete: the difference is printed rather than left for a reader to
    notice."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "county-board-members.json")
    dir_path = os.path.join(data_dir, "county-board-directory.json")
    directory = _read(dir_path) if os.path.exists(dir_path) else {}
    by_county, problems, nameless = {}, [], set()
    for seat, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name:
            problems.append("wi county-board-members.json seat %r carries no "
                            "county — it cannot be placed on a page" % seat)
            continue
        d = by_county.setdefault(name, {"seats": {}, "at_large": [],
                                        "geoid": seat[:5], "source": None})
        d["source"] = d["source"] or rec.get("sourceUrl")
        if isinstance(rec.get("atLarge"), list):
            for m in rec["atLarge"]:
                m = dict(m)
                m.setdefault("readOn", rec.get("readOn"))
                d["at_large"].append(m)
            continue
        if rec.get("district") is None:
            problems.append("wi county-board-members.json seat %r carries "
                            "neither a district nor an atLarge list" % seat)
            continue
        d["seats"][str(rec["district"])] = rec
    out = {}
    for name, d in sorted(by_county.items()):
        districts = []
        for label in sorted(d["seats"], key=district_sort_key):
            rec = d["seats"][label]
            if rec.get("withheld"):
                districts.append(district(label, note=rec.get("withheldWhy")))
            elif rec.get("vacant"):
                districts.append(district(label, vacancies=1))
            else:
                districts.append(district(label, [rec]))
        extras = ([("at-large", "Elected at large", d["at_large"])]
                  if d["at_large"] else [])
        named = _count_named(districts, extras)
        if not named:
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("wi %s County names nobody" % name)
            nameless.add(name)
            continue
        entry = directory.get(d["geoid"], {})
        out[name] = {"districts": districts, "sourceUrl": d["source"],
                     "extras": extras, "skipped": [], "slug": county_slug(name),
                     "at_large": False, "seats": entry.get("seats"),
                     "source_file": path}
    used = [path] + ([dir_path] if directory else [])
    return out, problems, nameless, used, None


def ia_supervisors(inst):
    """Iowa: ONE file keyed by county code, each carrying a `districts` object
    of {label: {name, party}} and the board's own phone.

    THE CHAIR IS A ROLE ON A SUPERVISOR, NOT A SEPARATE OFFICEHOLDER, which is
    the opposite of Illinois: an Illinois county that publishes a chair elects
    that person countywide and names them in no district, while Iowa's chair is
    one of the supervisors the board itself picks. So ia-county-board-chairs.json
    sets a `role` on the matching member rather than adding a section, and a
    chair who matches nobody in the county's own district list is reported
    rather than shipped as an extra person.

    That file names a chair for 43 counties and this roster covers 17, so 26
    counties have a chair and no board list. They get no page: one name and a
    link is the thin shape the per-county decision rejected in the first place,
    and the count is printed on every run so the absence is visible."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "ia-supervisor-members.json")
    chair_path = os.path.join(data_dir, "ia-county-board-chairs.json")
    chairs = {}
    if os.path.exists(chair_path):
        for rec in _read(chair_path).values():
            if (rec.get("county") or "").strip() and (rec.get("chair") or "").strip():
                chairs[rec["county"].strip()] = rec["chair"].strip()
    out, problems, nameless, chaired = {}, [], set(), 0
    for code, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name:
            problems.append("ia-supervisor-members.json %r carries no county" % code)
            continue
        districts = []
        for label in sorted(rec.get("districts") or {}, key=district_sort_key):
            m = dict((rec["districts"] or {})[label])
            if rec.get("boardPhone") and not m.get("phone"):
                # The board's own number, the only one the roster carries, and
                # the same one the app's card shows for every supervisor.
                m["phone"] = rec["boardPhone"]
            districts.append(district(label, [m]))
        chair = chairs.get(name)
        if chair:
            hit = [m for d in districts for m in d["members"]
                   if (m.get("name") or "").strip() == chair]
            if hit:
                hit[0]["role"] = "Chair"
                chaired += 1
            else:
                problems.append(
                    "ia-county-board-chairs.json names %s as %s County's chair "
                    "and no supervisor in ia-supervisor-members.json has that "
                    "name — the two rosters disagree about who is on the board"
                    % (chair, name))
        named = _count_named(districts, [])
        if not named:
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("ia %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = {"districts": districts, "sourceUrl": rec.get("sourceUrl"),
                     "extras": [], "skipped": [], "slug": county_slug(name),
                     "at_large": False, "source_file": path,
                     # Present only on a county this project no longer reads.
                     # Their absence is what lets every other county keep the
                     # "re-read on a schedule" sentence, which is true of it.
                     "asOf": rec.get("asOf"), "asOfWhy": rec.get("asOfWhy")}
    # THE SET DIFFERENCE, NEVER len(chairs) - len(out). Subtracting the counts
    # is only right if every county with a member list also has a chair, and
    # nine do not (measured 2026-09-19: 38 chairs, 17 member lists, 8 counties
    # with both, so 30 have a chair and no page). The subtraction printed 21.
    # Both dicts are keyed by county name, and a county that named nobody is
    # absent from `out` too, which is correct -- it has a chair and no page for
    # a different reason but no page either way.
    chairless = sorted(set(chairs) - set(out))
    note = ("%d of %d chair(s) joined; %d Iowa county board(s) have a published "
            "chair and no member list, so no page"
            % (chaired, len(out), len(chairless)))
    return out, problems, nameless, [path] + ([chair_path] if chairs else []), note


# The election method each plan names, in the SAME vocabulary ia/index.html's
# own card uses (IA_BOARD_PLAN_NOTE). Iowa Code ch. 331 lets a county elect its
# board under plan 1, plan 2 or plan 3, and the three are NOT interchangeable
# on a page that names people:
#
#   PLAN 1  at large; there are no supervisor districts to be in.
#   PLAN 2  countywide, but each supervisor must LIVE in a different district,
#           so districts exist and nobody is elected by one.
#   PLAN 3  nominated and elected by one district's voters.
#
# ia/scripts/build_ia_supervisor_districts.py already records why the
# difference matters: calling a transitioning county PLAN 3 "would tell a
# reader their district elects one supervisor today, which is the exact class
# of error the fleet's at-large rule exists to prevent". The same is true here
# in reverse -- the at-large page body says in so many words that there are no
# districts to be in, and on a plan 2 or plan 3 county that is false.
IA_PLAN_PAGE = {
    "PLAN 1": {
        "lede": ("%(county)s County elects its %(phrase)s <b>at large</b> — every "
                 "supervisor is chosen countywide, so there are no supervisor "
                 "districts to be in. These %(who)s represent the whole county."),
        "cta_note": ("Opens the map with the county layer on. An at-large board "
                     "has no district geometry, so the members above are the "
                     "answer for anywhere in the county."),
        "desc": "%d members elected at large across the whole county",
        "index_note": ", at large",
    },
    "PLAN 2": {
        "lede": ("%(county)s County elects its %(phrase)s <b>countywide</b> — every "
                 "voter votes on every seat, though each supervisor must live in "
                 "a different district. These %(who)s represent the whole county."),
        "cta_note": ("Opens the map with the supervisor-district layer on. The "
                     "districts decide where each supervisor must live, not who "
                     "votes on them, so the members above are the answer "
                     "anywhere in the county."),
        "desc": "%d members elected countywide from residence districts",
        "index_note": ", countywide",
    },
    "PLAN 3": {
        "lede": ("%(county)s County elects its %(phrase)s <b>by district</b> — each "
                 "supervisor is nominated and elected by the voters of one "
                 "district. These %(who)s hold those seats; which district each "
                 "one holds is not published in the source this page reads."),
        "cta_note": ("Opens the map with the supervisor-district layer on, which "
                     "names the district you are in. Pairing a district with its "
                     "supervisor needs a source this county does not publish, so "
                     "the list above is every seat rather than yours."),
        "desc": "%d members elected one per district",
        "index_note": ", by district",
    },
    "TRANSITIONING": {
        "lede": ("%(county)s County is moving from at-large to district elections "
                 "under Senate File 75. These %(who)s are the board sitting now, "
                 "elected at large."),
        "cta_note": ("Opens the map with the supervisor-district layer on. The "
                     "district lines are drawn but do not elect anyone yet, so "
                     "the members above are the answer anywhere in the county."),
        "desc": "%d members elected at large, moving to district elections",
        "index_note": ", at large until 2026",
    },
}


# A county the state's own plan layer does not carry. It ships ONLY where a
# gap record already explains the absence to a reader, so the page and the
# panel say the same thing about the same county.
IA_PLAN_UNRECORDED = {
    "lede": ("These %(who)s make up %(county)s County's %(phrase)s. How the "
             "county elects them is not established here — the state's own "
             "supervisor-district layer does not carry this county, so this "
             "page names the board without claiming an election method for it."),
    "cta_note": ("Opens the map with the county layer on. The state publishes "
                 "no supervisor districts for this county, so there is no "
                 "district map to send you to."),
    # No method clause and no index suffix: the page says in words that how the
    # county elects this board is not established here, and a description or an
    # index row that names one would contradict the page it describes.
    "desc": "%d members",
    "index_note": "",
}


def ia_at_large(inst):
    """Iowa: the 74 counties whose supervisors are named in the OFFICERS file.

    WHY THIS EXISTS. ia-county-officers.json carries a `supervisors` list for
    91 of the 99 counties -- 345 named people, which the app's own card
    renders -- and until 2026-09-22 it sat in NOT_COUNTY_BOARDS under the
    reason "Row officers, not supervisors; the supervisors are in
    ia/data/app/ia-supervisor-members.json, which these pages read." That
    sentence was written on 2026-09-13 and is false about the file as it
    stands: the districted roster covers 17 counties, the officers file names
    supervisors in 91, and the 74 in the difference reached no crawler and
    counted as UNEXAMINED in build_eam_status.py. Illinois's at-large counties
    ride il-county-commissioners.json, which IS read here, so the fleet was
    applying two standards to the same fact for no reason but which file each
    instance happened to keep it in.

    THE 17 DISTRICTED COUNTIES ARE SKIPPED and the skip is derived, not
    listed: every county in ia-supervisor-members.json is in the officers file
    too, naming the same people without their districts, so the districted
    page is strictly the better one and two entries for one county is what the
    collision guard in county_rows() refuses anyway.

    `at_large` IS NOT SET FROM THE FILE'S SHAPE. A flat list of supervisors
    means "nobody keyed these to districts", which is a statement about this
    project's sources and not about how the county elects anyone. Only plan 1
    is genuinely at large; plan 2 elects countywide from residence districts,
    plan 3 elects by district and simply is not keyed here, and a
    TRANSITIONING county is mid-move. Each gets its own lede and its own
    map-link note rather than the at-large body's "there are no supervisor
    districts to be in", which is true of plan 1 alone.
    """
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "ia-county-officers.json")
    districted_path = os.path.join(data_dir, "ia-supervisor-members.json")
    districted = set()
    if os.path.exists(districted_path):
        for rec in _read(districted_path).values():
            if (rec.get("county") or "").strip():
                districted.add(rec["county"].strip())

    gaps_path = os.path.join(data_dir, "coverage-gaps.json")
    recorded_gaps = set()
    if os.path.exists(gaps_path):
        blob = _read(gaps_path)
        for g in (blob.values() if isinstance(blob, dict) else blob):
            for slug in g.get("counties") or []:
                recorded_gaps.add(slug)

    out, problems, nameless = {}, [], set()
    skipped_districted, withheld = 0, []
    for code, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name:
            problems.append("ia-county-officers.json %r carries no county" % code)
            continue
        if name in districted:
            skipped_districted += 1
            continue
        if rec.get("supervisorsWithheld"):
            withheld.append(name)
            continue
        supervisors = rec.get("supervisors") or []
        if not supervisors:
            continue
        plan = (rec.get("supervisorPlan") or "").strip()
        page = IA_PLAN_PAGE.get(plan)
        if page is None and not plan and county_slug(name) in recorded_gaps:
            # A COUNTY WITH NO PLAN AND A GAP RECORD IS EXPLAINED, NOT
            # UNHANDLED, and the difference is derived from the tree rather
            # than from a second hand-kept list. No county takes this branch
            # since 2026-10-07: Jones was the one, absent from the state's own
            # supervisor-district layer until the county sent its own district
            # file, and a county the state layer omits again would have no
            # plan to print, so nothing here would establish how its board is
            # elected. The page still names the supervisors, because they are
            # real and published; it just does not invent an election method
            # for them. A county that loses its plan WITHOUT a gap record
            # still falls through to the refusal below, which is the case
            # worth stopping for.
            page = IA_PLAN_UNRECORDED
        if page is None:
            # A county whose plan this table does not know gets NO page rather
            # than a guessed sentence about how its board is elected. Printed,
            # never silent: an unhandled plan is a real event (SF 75 moved
            # three counties between plans in one session) and the fix is a
            # row here, not a default.
            problems.append(
                "ia %s County records supervisorPlan %r, which the page "
                "vocabulary does not carry — add a row to IA_PLAN_PAGE rather "
                "than letting it fall back to an election method nobody "
                "measured" % (name, plan or "(none)"))
            continue
        members = []
        for m in supervisors:
            m = dict(m)
            if rec.get("boardPhone") and not m.get("phone"):
                # The board's own number, the only one this file carries, and
                # the same one the app's card shows for every supervisor.
                m["phone"] = rec["boardPhone"]
            members.append(m)
        if not any((m.get("name") or "").strip() for m in members):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("ia %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = {"members": members,
                     "structure": None,
                     "verified": rec.get("readAt") or rec.get("asOf"),
                     "sourceUrl": rec.get("sourceUrl"),
                     "sourceDocument": None,
                     "seats": rec.get("supervisorSeats"),
                     "slug": county_slug(name), "at_large": True,
                     "lede": page["lede"], "cta_note": page["cta_note"],
                     "desc": page["desc"], "index_note": page["index_note"],
                     # THE ONLY PLAN THAT ELECTS AT LARGE. `at_large` above
                     # picks the flat renderer; this says whether the county
                     # actually elects that way, which is what the index page
                     # and the operator line count.
                     "claims_at_large": plan == "PLAN 1",
                     "plan": plan}
    note = ("%d county(s) read from the officers file; %d skipped because the "
            "districted roster covers them, %d withheld by that file's own "
            "seat-count gate (%s)"
            % (len(out), skipped_districted, len(withheld),
               ", ".join(sorted(withheld)) or "none"))
    return out, problems, nameless, [path, districted_path], note


def mi_commissioners(inst):
    """Michigan: ONE file keyed by 3-digit county FIPS, each carrying the
    county's name, the seat count the shipped geometry draws, and a `districts`
    object of {label: {name, role?, party?, phone?, email?, profileUrl?}}.

    IT COVERS SIXTEEN OF 83 COUNTIES AND IS MEANT TO. Michigan publishes no
    maintained statewide roster of commissioners — the one statewide name
    column, on the state's own district layer, holds the certified November
    2024 election winners — so the names are read from each county's own board
    page, a tranche at a time. A county absent from the file gets no page,
    which is the same rule Iowa's 26 chair-only counties meet: one name and a
    link is the thin shape the per-county decision rejected.

    THE CHAIR IS A ROLE ON A COMMISSIONER, the Iowa shape rather than the
    Illinois one, and it arrives already attached: measured 2026-09-15, ten of
    the sixteen counties badge their own officers in the same block the name
    comes from, in nine distinct spellings, so there is no second file to join
    and no name match to get wrong. The spellings are re-measured per change
    rather than listed here, because every tranche has added more.

    A COUNTY CAN BE SHORT, AND `unnamedDistricts` SAYS SO, with `unnamedWhy`
    carrying a per-district reason where the shortfalls differ. TWO COUNTIES ARE
    SHORT AND FOR DIFFERENT REASONS, which is why one sentence cannot serve
    both (the reasons in force move; the roster's `unnamedWhy` is the record). Monroe's directory carries a row whose district field reads
    "District 2" and whose name field reads "Commissioner Vensel", where Vensel
    is District 6's chairman: that row names no District 2 commissioner.
    Lenawee District 5's row named somebody, Jim Daly, while the same county's
    own News Flash of 10 September 2026 announced his death — two surfaces of
    one county disagreeing, so nothing named that seat from 2026-09-15 until
    the county listed his appointed successor on 2026-10-06. Each district gets
    a `note`, printed as "Not named — ..." with its own reason, the third state
    the `district()` helper already draws.

    THE GATE IS STILL EXACT, just not an equality on the named count: every
    district the shipped geometry draws must be either named or noted, no label
    may be both, and the union must be exactly the seat count. A missing label
    nobody accounted for still fails the build."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "mi-commissioner-members.json")
    out, problems, nameless = {}, [], set()
    for fips, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name:
            problems.append("mi-commissioner-members.json %r carries no county" % fips)
            continue
        named = rec.get("districts") or {}
        unnamed = [str(u) for u in (rec.get("unnamedDistricts") or [])]
        both = sorted(set(named) & set(unnamed), key=district_sort_key)
        if both:
            problems.append(
                "mi %s County lists district(s) %s as both named and unnamed"
                % (name, ", ".join(both)))
            continue
        districts = []
        for label in sorted(set(named) | set(unnamed), key=district_sort_key):
            if label in named:
                districts.append(district(label, [dict(named[label])]))
            else:
                # The builder records a per-district reason where the two
                # absences differ: Monroe's row carries no name, and a row the
                # same county contradicts elsewhere (Lenawee District 5, until
                # 2026-10-06) names somebody it has announced died. Without one, the row simply named nobody.
                districts.append(district(label, note=(rec.get("unnamedWhy") or {}).get(
                    label,
                    "the county's own directory row for this district carries "
                    "no commissioner's name")))
        seats = rec.get("seats")
        if seats is not None and len(districts) != seats:
            problems.append(
                "mi %s County accounts for %d district(s) against a %d-seat "
                "board — the roster and the shipped geometry disagree"
                % (name, len(districts), seats))
            continue
        if not _count_named(districts, []):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("mi %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = {"districts": districts, "sourceUrl": rec.get("sourceUrl"),
                     "extras": [], "skipped": [], "slug": county_slug(name),
                     "at_large": False, "source_file": path}
    scraped = len(out)

    # THE SECOND ROUTE, AND IT IS A DIFFERENT KIND OF NAME. Adam opened it on
    # 2026-09-22: the counties the tranches do not reach take their names from
    # the state district layer's own certified-returns column -- the winners of
    # the general election of 5 November 2024 -- on the condition that the row
    # always says so. Every record in that file carries its own `lede`,
    # `cta_note` and `desc`, which is why this adapter passes them through
    # rather than composing a sentence here: one wording, written where the
    # data is built, so the card and this page cannot drift about what these
    # names are. `mi/scripts/build_mi_returns_roster.py` REFUSES TO WRITE a
    # record without a lede, and this adapter refuses to render one.
    returns_path = os.path.join(data_dir, "mi-commissioner-returns.json")
    for fips, rec in sorted(_read(returns_path).items()):
        name = (rec.get("county") or "").strip()
        if not name:
            problems.append("mi-commissioner-returns.json %r carries no county" % fips)
            continue
        if name in out:
            problems.append(
                "mi %s County is in BOTH commissioner rosters; the two carry "
                "different provenance and a page can only state one" % name)
            continue
        # ALL FOUR SURFACES, not just the lede. A page says where its names
        # came from in four places -- the lede, the standfirst under the H1,
        # the meta description a search result shows, and the disclaimer at
        # the foot -- and three of them defaulted to "the county's own
        # published roster". Requiring only the lede would leave a page whose
        # opening paragraph names the election and whose next line and last
        # line contradict it.
        thin = [k for k in ("lede", "standfirst", "disclaimer", "desc")
                if not (rec.get(k) or "").strip()]
        if thin:
            problems.append(
                "mi %s County is on the certified-returns route and carries no "
                "`%s`, so a page would state a provenance it does not have"
                % (name, "`, no `".join(thin)))
            continue
        named = rec.get("districts") or {}
        districts = [district(label, [dict(named[label])])
                     for label in sorted(named, key=district_sort_key)]
        seats = rec.get("seats")
        if seats is not None and len(districts) != seats:
            problems.append(
                "mi %s County accounts for %d district(s) against a %d-seat "
                "board" % (name, len(districts), seats))
            continue
        entry = {"districts": districts, "sourceUrl": rec.get("sourceUrl"),
                 "extras": [], "skipped": [], "slug": county_slug(name),
                 "at_large": False, "source_file": returns_path,
                 "lede": rec["lede"], "cta_note": rec.get("cta_note"),
                 "desc": rec.get("desc"), "standfirst": rec.get("standfirst"),
                 "disclaimer": rec.get("disclaimer"),
                 # the source line names the state's results, not the county
                 "source_label": "the State of Michigan's certified election results"}
        if rec.get("betterSource"):
            entry["better_source"] = rec["betterSource"]
        out[name] = entry
    note = ("%d of Michigan's 83 counties name their commissioners: %d read "
            "from the county's own board page, %d from the state's certified "
            "November 2024 returns with every row saying so"
            % (len(out), scraped, len(out) - scraped))
    return out, problems, nameless, [path, returns_path], note


MN_LEDE = ("These are the people who won each seat on %(county)s County's "
           "Board of Commissioners at its most recent election in the Minnesota "
           "Secretary of State's results, each dated to that election. They are "
           "election winners, not a list the county keeps up to date, so a seat "
           "that has changed hands since, by a resignation or an appointment, "
           "still shows the person who won it.")
MN_STANDFIRST = ("Who won each seat on the %(heading)s at its most recent "
                 "election, from the Minnesota Secretary of State's results.")
MN_DESC = ("Who won each of the %(districts)d seats on %(county)s County's "
           "Board of Commissioners at its most recent election, and which "
           "district each one represents.")
MN_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above won an "
                 "election the Minnesota Secretary of State published results for,\n"
                 "and this page dates each name to that election rather than "
                 "claiming the seat is still held.")
MN_CTA_NOTE = ("Opens the map with the commissioner-district layer on. The "
               "district lines come from the Secretary of State's precinct map; "
               "the names come from its election results and are dated to them.")


def mn_commissioners(inst):
    """Minnesota: ONE file keyed "<county FIPS>-<district>", every record
    carrying its county, its district and either a `name` with the `election`
    that seated it or an `unnamed` reason (mn/scripts/build_mn_commissioner_roster.py).

    EVERY COUNTY GETS A PAGE because the file covers all 447 seats, and a seat
    the results do not name is drawn as the third state `district()` already
    knows: "Not named", with the record's own reason. Where a county's own
    district map names somebody else (`countySays`), the member row says so
    beside the election date, because the two publishers disagreeing is the
    thing a reader of that seat should see."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "mn-county-commissioners.json")
    by_county, problems, nameless = {}, [], set()
    for key, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name or rec.get("district") is None:
            problems.append("mn-county-commissioners.json %r carries no county "
                            "or district" % key)
            continue
        by_county.setdefault(name, []).append(rec)
    out = {}
    for name, recs in sorted(by_county.items()):
        districts = []
        for rec in sorted(recs, key=lambda r: int(r["district"])):
            label = str(rec["district"])
            if (rec.get("name") or "").strip():
                when = _mn_date(rec.get("election"))
                if not when:
                    problems.append("mn %s County District %s names somebody "
                                    "with no election date" % (name, label))
                    continue
                note = ("Won a special election on %s." if rec.get("special")
                        else "Elected %s.") % when
                says = rec.get("countySays") or {}
                if (says.get("name") or "").strip():
                    note += (" %s's own district map names %s for this seat."
                             % (says.get("publisher") or "The county",
                                says["name"].strip()))
                districts.append(district(label, [{"name": rec["name"].strip(),
                                                   "elected": note}]))
            else:
                districts.append(district(label, note=(rec.get("unnamed") or
                                                       "the results name nobody")))
        if not _count_named(districts, []):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("mn %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = {"districts": districts,
                     "sourceUrl": "https://electionresults.sos.mn.gov/",
                     "source_label": "the Minnesota Secretary of State's election results",
                     "extras": [], "skipped": [], "slug": county_slug(name),
                     "at_large": False, "source_file": path,
                     "lede": MN_LEDE, "standfirst": MN_STANDFIRST,
                     "desc": MN_DESC, "disclaimer": MN_DISCLAIMER,
                     "cta_note": MN_CTA_NOTE}
    note = ("%d of Minnesota's 87 counties, every seat named from the Secretary "
            "of State's election results or marked with why not" % len(out))
    return out, problems, nameless, [path], note


OK_LEDE = ("These are the three commissioners the Oklahoma State Election "
           "Board's Roster of State and County Officers lists for %(county)s "
           "County. The Board compiles the roster after each general election "
           "and lists every county's commissioners whether or not their seat "
           "was on that ballot. It is not kept up to date between elections, "
           "so a seat that has changed hands since still shows the earlier name.")
OK_STANDFIRST = ("Who sits on the %(heading)s, from the Oklahoma State Election "
                 "Board's roster of county officers.")
OK_DESC = ("The %(districts)d commissioners of %(county)s County, Oklahoma, "
           "from the State Election Board's roster, and the district each one "
           "represents.")
OK_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above is "
                 "printed in the Oklahoma State Election Board's roster,\n"
                 "and this page dates the roster rather than claiming each seat "
                 "is still held.")
OK_CTA_NOTE = ("Opens the map with the commissioner-district layer on. The "
               "district lines come from the state Department of "
               "Transportation; the names come from the State Election Board's "
               "roster and are dated to it.")


def ok_commissioners(inst):
    """Oklahoma: ONE file keyed "<county GEOID>-<district>", every record
    carrying its county, its district, the `election` the roster was compiled
    after, and either a `name` (with `party`) or `vacant: true`
    (ok/scripts/build_ok_commissioner_roster.py). Every county has three
    seats, so every county gets a page; a vacant seat is drawn as the
    county's roster drew it."""
    path = os.path.join(app_data(inst["tag"]), "ok-county-commissioners.json")
    by_county, problems, nameless = {}, [], set()
    for key, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        if not name or rec.get("district") is None:
            problems.append("ok-county-commissioners.json %r carries no county "
                            "or district" % key)
            continue
        by_county.setdefault(name, []).append(rec)
    out = {}
    for name, recs in sorted(by_county.items()):
        if len(recs) != 3:
            problems.append("ok %s County has %d seats, not 3" % (name, len(recs)))
            continue
        districts = []
        when = _mn_date(recs[0].get("election"))
        if not when:
            problems.append("ok %s County carries no roster date" % name)
            continue
        for rec in sorted(recs, key=lambda r: int(r["district"])):
            label = str(rec["district"])
            if rec.get("vacant"):
                districts.append(district(label, vacancies=1))
            elif (rec.get("name") or "").strip():
                member = {"name": rec["name"].strip(),
                          "elected": "In the roster compiled after the %s general election." % when}
                if rec.get("party"):
                    member["party"] = rec["party"]
                districts.append(district(label, [member]))
            else:
                problems.append("ok %s County District %s is neither named nor "
                                "vacant" % (name, label))
        if not _count_named(districts, []):
            nameless.add(name)
            continue
        out[name] = {"districts": districts,
                     "sourceUrl": recs[0].get("sourceUrl"),
                     "source_label": "the Oklahoma State Election Board's roster of state and county officers",
                     "extras": [], "skipped": [], "slug": county_slug(name),
                     "at_large": False, "source_file": path,
                     "lede": OK_LEDE, "standfirst": OK_STANDFIRST,
                     "desc": OK_DESC, "disclaimer": OK_DISCLAIMER,
                     "cta_note": OK_CTA_NOTE}
    note = ("%d of Oklahoma's 77 counties, every seat named from the State "
            "Election Board's roster or marked vacant as it is there" % len(out))
    return out, problems, nameless, [path], note


IN_LEDE = ("These are the people who won each seat on %(county)s County's "
           "Board of Commissioners at its most recent election in the Indiana "
           "Election Division's certified results, each dated to that election. "
           "They are election winners, not a list the county keeps up to date: "
           "Indiana fills a vacancy by party caucus, so a seat that has changed "
           "hands since still shows the person who won it.")
IN_STANDFIRST = ("Who won each seat on the %(heading)s at its most recent "
                 "election, from the Indiana Election Division's certified results.")
IN_DESC = ("Who won each of the %(districts)d seats on %(county)s County's "
           "Board of Commissioners at its most recent election, and which "
           "district each one holds.")
IN_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above won an "
                 "election the Indiana Election Division certified,\n"
                 "and this page dates each name to that election rather than "
                 "claiming the seat is still held.")
IN_CTA_NOTE = ("Opens the map with the county layer on. Its card lists this "
               "board and the county council, from the same certified results; "
               "the commissioner district lines are not drawn yet.")

# MARION COUNTY'S BODY IS THE INDIANAPOLIS CITY-COUNTY COUNCIL (IC 36-3), the
# legislative body of the consolidated city and of the county, elected in the
# municipal general rather than with the county officers. Its record carries
# its own wording so the page never calls it a board of commissioners.
IN_MARION_WORDING = dict(
    heading="Indianapolis City-County Council",
    page_title="Indianapolis City-County Council",
    page_title_short="Indianapolis City-County Council",
    phrase="City-County Council", member_word="Councilor")
IN_MARION_LEDE = ("Indianapolis and Marion County share one government, and "
                  "its legislative body is the 25-member %(heading)s. These are "
                  "the people who won each of its seats at the most recent "
                  "municipal election in the Indiana Election Division's "
                  "certified results, each dated to that election. They are "
                  "election winners, not a list the council keeps up to date: "
                  "Indiana fills a vacancy by party caucus, so a seat that has "
                  "changed hands since still shows the person who won it.")
IN_MARION_DESC = ("Who won each of the %(districts)d seats on the Indianapolis "
                  "City-County Council, Marion County's legislative body, at "
                  "its most recent election.")
IN_MARION_CTA_NOTE = ("Opens the map with the county layer on. Its card lists "
                      "the council and the mayor, from the same certified "
                      "results; the council's district lines are not drawn yet.")


def in_commissioners(inst):
    """Indiana: ONE file keyed by county GEOID, each record carrying the
    county's name and a `seats` list of {seat, name, party, election, office,
    sourceUrl, seatNotStated?} (in/scripts/build_in_county_officials.py).

    ALL 92 COUNTIES, ONE OF THEM A CITY COUNCIL. Marion County's legislative
    body is the Indianapolis City-County Council, which the certified
    commissioner results do not carry; its 25 seats come from
    in-city-officials.json (in/scripts/build_in_city_officials.py, the same
    archive's 2023 municipal general), and its record carries its own
    `wording` so its page is headed by the body it is about.

    A SEAT WHOSE RACE TITLE NAMES NO DISTRICT is labelled with the title as
    published (Clinton's and Ohio's "County Commissioner"), and the member row
    says so beside the election date, rather than this page placing the seat in
    a district the results do not name."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "in-county-commissioners.json")
    out, problems, nameless = {}, [], set()
    for geoid, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        seats = rec.get("seats") or []
        if not name or not seats:
            problems.append("in-county-commissioners.json %r carries no county "
                            "or no seats" % geoid)
            continue
        labels = [s.get("seat") for s in seats]
        if len(set(labels)) != len(labels):
            problems.append("in %s County lists a seat twice: %r" % (name, labels))
            continue
        districts = []
        for seat in seats:
            when = _mn_date(seat.get("election"))
            if not when or not (seat.get("name") or "").strip():
                problems.append("in %s County %r names nobody or carries no "
                                "election date" % (name, seat.get("seat")))
                continue
            note = "Elected %s." % when
            if seat.get("seatNotStated"):
                note += (" The results do not say which district this seat is: "
                         "%s." % seat["seatNotStated"])
            member = {"name": seat["name"].strip(), "elected": note}
            if seat.get("party"):
                member["party"] = seat["party"]
            districts.append(district(seat["seat"], [member]))
        if not _count_named(districts, []):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("in %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = {"districts": districts,
                     "sourceUrl": max(seats, key=lambda s: s.get("election") or "").get("sourceUrl"),
                     "source_label": "the Indiana Election Division's certified results",
                     "extras": [], "skipped": [], "slug": county_slug(name),
                     "at_large": False, "source_file": path,
                     "lede": IN_LEDE, "standfirst": IN_STANDFIRST,
                     "desc": IN_DESC, "disclaimer": IN_DISCLAIMER,
                     "cta_note": IN_CTA_NOTE}
    # Marion, from the city file: the City-County Council's 25 seats, not the
    # mayor, who is the executive rather than a member of the body.
    city_path = os.path.join(data_dir, "in-city-officials.json")
    indy = _read(city_path).get("1836003") or {}
    seats = [s for s in indy.get("seats") or [] if s.get("seat") != "Mayor"]
    if indy.get("county") != "Marion" or len(seats) != 25:
        problems.append("in-city-officials.json does not carry the 25 seats of "
                        "the Indianapolis City-County Council")
    else:
        districts = []
        for seat in seats:
            when = _mn_date(seat.get("election"))
            if not when or not (seat.get("name") or "").strip():
                problems.append("Indianapolis City-County Council %r names "
                                "nobody or carries no election date"
                                % seat.get("seat"))
                continue
            member = {"name": seat["name"].strip(), "elected": "Elected %s." % when}
            if seat.get("party"):
                member["party"] = seat["party"]
            districts.append(district(seat["seat"], [member]))
        out["Marion"] = {"districts": districts,
                         "sourceUrl": seats[0].get("sourceUrl"),
                         "source_label": "the Indiana Election Division's certified results",
                         "extras": [], "skipped": [], "slug": county_slug("Marion"),
                         "at_large": False, "source_file": city_path,
                         "wording": IN_MARION_WORDING,
                         "lede": IN_MARION_LEDE, "standfirst": IN_STANDFIRST,
                         "desc": IN_MARION_DESC, "disclaimer": IN_DISCLAIMER,
                         "cta_note": IN_MARION_CTA_NOTE}
    note = ("%d of Indiana's 92 counties, every seat named from the Election "
            "Division's certified results (Marion's is the Indianapolis "
            "City-County Council)" % len(out))
    return out, problems, nameless, [path, city_path], note


# Kept short because it ends every page's search description, and the longest
# county names put "the ... county directory" past the 155-character limit.
KY_SOURCE_LABEL = "Kentucky's Department for Local Government"
KY_LEDE = {
    "magistrate": (
        "%(county)s County's fiscal court is its county judge/executive, who "
        "presides, and its magistrates, each elected from a magisterial district "
        "(KRS 67.040). These are the %(who)s the Kentucky Department for Local "
        "Government's county directory lists. The directory does not say which "
        "district each magistrate holds."),
    "commissioner": (
        "%(county)s County's fiscal court is its county judge/executive, who "
        "presides, and three commissioners, each elected by the whole county's "
        "voters and one living in each commissioner district (KRS 67.060). These "
        "are the %(who)s the Kentucky Department for Local Government's county "
        "directory lists."),
}
KY_MERGED_LEDE = (
    "%(county)s County has no fiscal court: it merged with its city, and the "
    "%(body)s is its governing body (%(law)s). These are the %(who)s the "
    "Kentucky Department for Local Government's directory lists, each elected "
    "from a council district that is not drawn here yet. The mayor, %(mayor)s, "
    "is the government's executive and is not a member of the council.")
# Appended to the lede where the builder matched members to the districts they
# won in 2022, so a county with no match never claims one.
KY_DISTRICT_NOTE = ("Where the State Board of Elections' certified 2022 results "
                    "name a member as the winner of a district, that district is "
                    "shown beside the name; a member without one took the seat "
                    "after that election or could not be matched.")
KY_STANDFIRST = ("Every member of the %(heading)s, as the Kentucky Department "
                 "for Local Government's county directory lists them.")
KY_DESC = {"magistrate": "%d members: the judge/executive and the magistrates",
           "commissioner": "%d members: the judge/executive and three commissioners",
           "merged": "%d council members"}
KY_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above is listed "
                 "by the Kentucky Department for Local Government,\n"
                 "which does not say when a county last updated its entry, so the "
                 "county's own website is the current word.")
KY_CTA_NOTE = ("Opens the map with the county layer on. Its card lists this body "
               "and the county's elected officers; the district lines are not "
               "drawn yet, so the map cannot say which district a point is in.")


def ky_county_governments(inst):
    """Kentucky: ONE file keyed by county GEOID (ky/data/app/ky-county-officials.json,
    built by ky/scripts/build_ky_county_officials.py from the Department for
    Local Government's county directory).

    FLAT, AND NEVER CLAIMED AT LARGE. The directory names every magistrate and
    commissioner and no district, so a page lists the body as one list; the
    lede says how the county actually elects (KRS 67.045 and 67.060), which is
    by district or from residence districts and never at large. Where the
    builder matched a member to the district they won in 2022 (the State
    Board of Elections' recap sheets), the district rides in the member's role
    ("Magistrate, District 3") and the lede says where it came from; the list
    stays flat because a member the results do not name has no district to
    file under.

    JEFFERSON AND FAYETTE are the merged governments and their pages are about
    the council, so the mayor is named in the lede as the executive and is not
    listed as a member of a body he does not sit on."""
    path = os.path.join(app_data(inst["tag"]), "ky-county-officials.json")
    out, problems, nameless = {}, [], set()
    for geoid, rec in sorted(_read(path).items()):
        name = (rec.get("county") or "").strip()
        members = [dict(m) for m in rec.get("members") or []]
        for m in members:
            if m.get("district"):
                d = str(m.pop("district"))
                m["role"] = "%s, %s" % (m.get("role") or "Member",
                                        "District " + d if re.match(r"^(\d+|[A-Z])$", d)
                                        else d + " District")
        if not name:
            problems.append("ky-county-officials.json %r carries no county" % geoid)
            continue
        if not any((m.get("name") or "").strip() for m in members):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("ky %s County names nobody" % name)
            nameless.add(name)
            continue
        merged = rec.get("body") != "Fiscal Court"
        if merged:
            if (inst.get("heading_for") or {}).get(name) != rec.get("body"):
                problems.append("ky %s County's body is %r and heading_for does not "
                                "name it" % (name, rec.get("body")))
                continue
            mayor = (rec.get("executive") or {}).get("name") or ""
            lede = KY_MERGED_LEDE % {
                "county": "%(county)s", "who": "%(who)s",
                "body": esc(rec["body"]).replace("%", "%%"),
                "law": esc(rec.get("law") or "").replace("%", "%%"),
                "mayor": esc(mayor).replace("%", "%%")}
            desc, index_note = KY_DESC["merged"], ", " + rec["body"]
        else:
            if rec.get("form") not in KY_LEDE:
                problems.append("ky %s County's fiscal court form %r has no wording"
                                % (name, rec.get("form")))
                continue
            lede, desc = KY_LEDE[rec["form"]], KY_DESC[rec["form"]]
            index_note = ", fiscal court"
            if rec.get("districtsFrom"):
                lede += " " + KY_DISTRICT_NOTE
            if rec.get("formNote"):
                lede += " " + esc(rec["formNote"]).replace("%", "%%")
        out[name] = {"members": members,
                     "structure": None,
                     "verified": rec.get("bodyRead") or rec.get("read"),
                     "sourceUrl": rec.get("bodySourceUrl") or rec.get("sourceUrl"),
                     "source_label": KY_SOURCE_LABEL,
                     "sourceDocument": None,
                     "seats": len(members) + int(rec.get("unnamedSeats") or 0),
                     "slug": county_slug(name), "at_large": True,
                     "claims_at_large": False,
                     "lede": lede, "standfirst": KY_STANDFIRST, "desc": desc,
                     "disclaimer": KY_DISCLAIMER, "cta_note": KY_CTA_NOTE,
                     "index_note": index_note, "source_file": path}
    note = ("%d of Kentucky's 120 counties, every name from the Department for "
            "Local Government's county directory" % len(out))
    return out, problems, nameless, [path], note


TN_LEDE = ("The %(heading)s is elected by district. This page lists its "
           "%(districts)d districts and the %(named)d members who hold them, "
           "exactly as the county publishes them; it is the same list the "
           "map's commission district card reads.")
TN_LEDE_AT_LARGE = ("The %(heading)s is elected mostly by district, with some "
                    "members elected countywide. This page lists its "
                    "%(districts)d districts, the %(named)d members who hold "
                    "them and the members elected countywide, exactly as the "
                    "county publishes them; it is the same list the map's "
                    "commission district card reads.")
TN_CTA_NOTE = ("Opens the map with the county and commission district layers "
               "on. Search your address or ZIP, or tap your location.")


def _tn_seat(seat):
    """The county's own seat label inside a district, as the app's card prints
    it: a bare letter or number reads "Seat A", anything longer is the
    county's own words ("Position 1")."""
    seat = str(seat or "").strip()
    if not seat:
        return ""
    return "Seat " + seat if len(seat) <= 2 else seat


def tn_commissioners(inst):
    """Tennessee: ONE file keyed by county GEOID ("47093"), each record
    carrying the county's name, its body's name and member title, the day the
    county's page was read, and `districts` mapping each district number to the
    members that page lists for it (tn/scripts/build_tn_commissioner_roster.py).

    A DISTRICT IS NOT A SEAT. Many Tennessee counties elect two or three
    members from one district, so a district holds a list; a member may carry
    the county's own seat label, which this page prints beside the name; and a
    seat the county says is vacant is a record marked `vacant`, counted as a
    vacancy and never as a name.

    ONLY THE COUNTIES THE ROSTER HAS READ GET A PAGE. The roster grows county by
    county as each county's page is proven, so a county it has not reached has
    no record here.

    THE BODY IS NOT ALWAYS A COUNTY COMMISSION. Nashville and Davidson County is
    one metropolitan government whose legislative body is the Metro Council, so
    a record whose `bodyName` is not "County Commission" carries that name in
    its heading and title, in the words the app's card uses."""
    path = os.path.join(app_data(inst["tag"]), "tn-commissioners.json")
    out, problems, nameless = {}, [], set()
    for geoid, rec in sorted(_read(path).items()):
        full = (rec.get("county") or "").strip()
        name = re.sub(r"\s+County$", "", full)
        named_districts = rec.get("districts") or {}
        read_on = _mn_date(rec.get("readAt"))
        if not name or not named_districts or not read_on:
            problems.append("tn-commissioners.json %r carries no county, no "
                            "districts or no read date" % geoid)
            continue

        def person(m):
            p = {k: m[k].strip() for k in ("name", "email", "phone", "profileUrl")
                 if isinstance(m.get(k), str) and m[k].strip()}
            # The further numbers the county prints for the same member (a home
            # and a cell line), carried since Adam's ruling of 2026-10-17 that a
            # member's own numbers ship.
            extra = [x.strip() for x in m.get("phonesExtra") or []
                     if isinstance(x, str) and x.strip()]
            if extra:
                p["phonesExtra"] = extra
            role = ", ".join(x for x in ((m.get("role") or "").strip(),
                                         _tn_seat(m.get("seat"))) if x)
            if role:
                p["role"] = role
            p["readOn"] = read_on
            return p

        districts = []
        aliases = rec.get("districtLabels") or {}
        for label in sorted(named_districts, key=district_sort_key):
            ms = named_districts[label] or []
            districts.append(district(
                label, [person(m) for m in ms if not m.get("vacant")],
                vacancies=sum(1 for m in ms if m.get("vacant")),
                alias=aliases.get(label)))
        countywide = rec.get("atLarge") or []
        if any(m.get("vacant") for m in countywide):
            # A page section for countywide members has no vacancy line yet,
            # and dropping the seat would make the page claim a smaller body.
            problems.append("tn %s County reports a vacant countywide seat, which "
                            "these pages cannot say yet" % name)
            continue
        extras = ([("at-large", "Elected countywide",
                    [person(m) for m in countywide])] if countywide else [])
        if not _count_named(districts, extras):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("tn %s County names nobody" % name)
            nameless.add(name)
            continue
        entry = {"districts": districts, "sourceUrl": rec.get("sourceUrl"),
                 "extras": extras, "skipped": [], "slug": county_slug(name),
                 "at_large": False, "source_file": path,
                 "lede": TN_LEDE_AT_LARGE if extras else TN_LEDE,
                 "cta_note": TN_CTA_NOTE}
        body = (rec.get("bodyName") or "").strip()
        if body and body != "County Commission":
            entry["heading"] = entry["page_title"] = "%s County %s" % (name, body)
            entry["member_word"] = (rec.get("seatTitle") or "").strip() or None
        out[name] = entry
    note = ("%d of Tennessee's 95 counties, each named from the county's own "
            "published list" % len(out))
    return out, problems, nameless, [path], note


NC_LEDE = ("These are the people who won each seat on %(county)s County's "
           "Board of Commissioners at its most recent election in the North "
           "Carolina State Board of Elections' results, each dated to that "
           "election. They are election winners, not a list the county keeps up "
           "to date: a board fills a vacancy by appointment, so a seat that has "
           "changed hands since may still show the person who won it.")
NC_STANDFIRST = ("Who won each seat on the %(heading)s at its most recent "
                 "election, from the North Carolina State Board of Elections' results.")
NC_DESC = ("Who won each of the %(districts)d seats on %(county)s County's "
           "Board of Commissioners at its most recent election.")
NC_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above won an "
                 "election the North Carolina State Board of Elections reports,\n"
                 "and this page dates each name to that election rather than "
                 "claiming the seat is still held.")
NC_CTA_NOTE = ("Opens the map with the county layer on. Its card lists this "
               "board from the same results; no publisher draws the "
               "commissioner districts.")


def nc_commissioners(inst):
    """North Carolina: ONE file keyed by county GEOID, each record carrying
    the county's name and a `seats` list of {seat, name | unnamed, party,
    election, note?} (nc/scripts/build_nc_county_commissioners.py).

    A LABEL CAN HOLD SEVERAL SEATS, because a county that elects three
    commissioners in one contest labels all three "Board seat" or "At large",
    so seats are grouped by label into one section each. A seat that names
    nobody carries its reason, printed as the section's note; a named seat's
    own note (one of several earlier winners has left, and the results do not
    say which) prints beside its election date."""
    data_dir = app_data(inst["tag"])
    path = os.path.join(data_dir, "nc-county-commissioners.json")
    out, problems, nameless = {}, [], set()
    for geoid, rec in sorted(_read(path).items()):
        if geoid.startswith("_"):
            continue
        name = (rec.get("county") or "").strip()
        seats = rec.get("seats") or []
        if not name or not seats:
            problems.append("nc-county-commissioners.json %r carries no county "
                            "or no seats" % geoid)
            continue
        groups = {}
        for seat in seats:
            groups.setdefault(seat.get("seat") or "Board seat", []).append(seat)
        districts = []
        for label, group in groups.items():
            members, notes = [], []
            for seat in group:
                if not (seat.get("name") or "").strip():
                    notes.append((seat.get("unnamed") or "the results name nobody").rstrip("."))
                    continue
                when = _mn_date(seat.get("election"))
                if not when:
                    problems.append("nc %s County %r names %r with no election "
                                    "date" % (name, label, seat["name"]))
                    continue
                note = ("Elected to the rest of a term %s." if seat.get("unexpiredTerm")
                        else "Elected %s.") % when
                if seat.get("note"):
                    note += " " + seat["note"]
                member = {"name": seat["name"].strip(), "elected": note}
                if seat.get("party"):
                    member["party"] = seat["party"]
                members.append(member)
            districts.append(district(label, members,
                                      note="; ".join(notes) if notes else None))
        if not _count_named(districts, []):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("nc %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = {"districts": districts,
                     "sourceUrl": "https://er.ncsbe.gov/",
                     "source_label": "the North Carolina State Board of Elections' results",
                     "extras": [], "skipped": [], "slug": county_slug(name),
                     "at_large": False, "source_file": path,
                     "lede": NC_LEDE, "standfirst": NC_STANDFIRST,
                     "desc": NC_DESC, "disclaimer": NC_DISCLAIMER,
                     "cta_note": NC_CTA_NOTE}
    note = ("%d of North Carolina's 100 counties, every seat named from the "
            "State Board of Elections' results or marked with why not" % len(out))
    return out, problems, nameless, [path], note


_MN_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December")


SC_LEDE = ("These are the people who won each seat on %(county)s County "
           "Council at its most recent election in the South Carolina Election "
           "Commission's certified results, each dated to that election. They "
           "are election winners, not a list the county keeps up to date, so a "
           "seat that has changed hands since may still show the person who won "
           "it. Where the county's own council page lists the seat differently, "
           "the seat's line says so.")
SC_STANDFIRST = ("Who won each seat on the %(heading)s at its most recent "
                 "election, from the South Carolina Election Commission's results.")
SC_DESC = ("Who won each seat on %(county)s County Council at its most recent "
           "election, and the district each one represents.")
SC_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above won an "
                 "election the South Carolina Election Commission certified,\n"
                 "and this page dates each name to that election rather than "
                 "claiming the seat is still held.")
SC_CTA_NOTE = ("Opens the map with the county council layer on. The district "
               "lines come from the state Revenue and Fiscal Affairs Office; the "
               "names come from the Election Commission's results and are dated "
               "to them.")
SC_CTA_NOTE_AT_LARGE = ("Opens the map with the county layer on. Every member "
                        "of this council is elected countywide, so the members "
                        "above are the answer for anywhere in the county.")
# The Election Commission's results page, the one the roster builder reads
# (RESULTS_PAGE in sc/scripts/build_sc_county_council_roster.py). Each seat's own
# results page is in the roster; a page names one place for all of them.
SC_RESULTS_URL = "https://scvotes.gov/elections-statistics/election-results/"

# South Carolina's non-district seat kinds, in the words a page prints for them.
SC_SEAT_LABELS = {"chair": "Chair, elected countywide",
                  "at-large": "Elected countywide",
                  "supervisor": "Supervisor, elected countywide",
                  # Jasper's four residence seats: elected by the whole
                  # county, each member required to live in one township.
                  "township": "Elected countywide from a residence township"}


def sc_councils(inst):
    """South Carolina: ONE file keyed by county GEOID ("45001"), each record
    carrying the county's name, its council's `form` and `seats`, every seat
    the winner of its most recent election in the State Election Commission's
    results (sc/scripts, sc-county-council-members.json).

    A SEAT IS EITHER A DISTRICT OR NOT. A `district` seat goes under its
    district; every other kind — a chair or supervisor elected countywide, an
    at-large member, Charleston-area members elected by township — goes in an
    extra section named for the kind, because placing it in a district would
    claim ground the seat does not represent. A council elected wholly at
    large (`form: whole-county`) has no district at all and carries its
    members at the top of the record, the at-large shape the fleet already
    reads.

    Where the county's own page names somebody else for a seat (`countySays`),
    the member's line says so beside the election date: the two publishers
    disagreeing is what a reader of that seat should see."""
    path = os.path.join(app_data(inst["tag"]), "sc-county-council-members.json")
    out, problems, nameless = {}, [], set()
    for geoid, rec in sorted(_read(path).items()):
        name = re.sub(r"\s+County$", "", (rec.get("county") or "").strip())
        seats = rec.get("seats") or []
        if not name or not seats:
            problems.append("sc-county-council-members.json %r carries no county "
                            "or no seats" % geoid)
            continue

        def person(seat):
            when = _mn_date(seat.get("election"))
            p = {"name": seat["name"].strip()}
            note = (("Elected %s to finish a term." if seat.get("unexpiredTerm")
                     else "Elected %s.") % when) if when else None
            # THE SAME FOUR READINGS THE CARD PRINTS (scCountySaysRow in
            # sc/index.html), so a page and a card never describe one seat two
            # ways. A reading this does not know FAILS rather than printing the
            # winner with nothing beside it.
            says = seat.get("countySays") or {}
            read = _mn_date(says.get("read"))
            whose = "%s County's own council page" % name
            said = None
            if (says.get("name") or "").strip():
                said = "%s names %s for this seat." % (whose, says["name"].strip())
            elif says.get("vacant"):
                said = "%s lists this seat as vacant." % whose
            elif says.get("former"):
                said = "%s lists %s as a former member." % (whose, p["name"])
            elif says.get("notListed"):
                said = "%s lists the other members and not %s." % (whose, p["name"])
            elif says:
                problems.append("sc %s County: a countySays reading this page "
                                "does not know: %r" % (name, sorted(says)))
            if said:
                note = ((note + " ") if note else "") + said + (
                    " Read %s." % read if read else "")
            if note:
                p["elected"] = note
            return p

        by_district, extra = {}, {}
        for seat in seats:
            if not (seat.get("name") or "").strip():
                problems.append("sc %s County has a seat naming nobody" % name)
                continue
            kind = seat.get("seat")
            if kind == "district" and seat.get("district") is not None:
                by_district.setdefault(str(seat["district"]), []).append(person(seat))
            elif kind in SC_SEAT_LABELS:
                extra.setdefault(kind, []).append(person(seat))
            else:
                problems.append("sc %s County has a seat of unknown kind %r"
                                % (name, kind))
        districts = [district(label, by_district[label])
                     for label in sorted(by_district, key=district_sort_key)]
        extras = [(kind, SC_SEAT_LABELS[kind], extra[kind])
                  for kind in SC_SEAT_LABELS if kind in extra]
        # THE SOURCE LINK IS THE RESULTS, NOT THE COUNTY'S PAGE: the names
        # are the Commission's, and a link labelled with its name that opened
        # the county's site would say where they came from wrongly.
        entry = {"districts": districts, "sourceUrl": SC_RESULTS_URL,
                 "source_label": "the South Carolina Election Commission's "
                                 "results",
                 "extras": extras, "skipped": [], "slug": county_slug(name),
                 "at_large": False, "source_file": path,
                 "lede": SC_LEDE, "standfirst": SC_STANDFIRST,
                 "desc": SC_DESC, "disclaimer": SC_DISCLAIMER,
                 "cta_note": SC_CTA_NOTE}
        if not districts:
            # A council elected wholly at large: its members are the record.
            entry["at_large"] = True
            entry["members"] = [m for _k, _l, ms in extras for m in ms]
            entry["extras"] = []
            # Results name the seats, so a page whose seats differ says which
            # is which: Jasper's members are one at large and four tied to a
            # residence township, the labels the card prints (scSeatLabel in
            # sc/index.html). Hampton's five are all at large and need none.
            if extra.get("township"):
                entry["members"] = []
                for seat in seats:
                    p = person(seat)
                    label = ("%s Township seat." % str(seat["township"]).strip()
                             if seat.get("seat") == "township" else "At large.")
                    p["elected"] = label + (" " + p["elected"]
                                            if p.get("elected") else "")
                    entry["members"].append(p)
            # These are election winners, not a sitting roster, so the search
            # snippet says "won" where the fleet's flat pages say "sits".
            entry["desc_lead"] = "Who won each seat on the"
            entry["cta_note"] = SC_CTA_NOTE_AT_LARGE
            # The flat page's description takes the member count positionally.
            # Jasper's residence townships are on the page rather than in this
            # sentence, which would otherwise run past validate_serp_lengths'
            # 155 characters (measured: 169).
            entry["desc"] = "%d members elected countywide"
        if not _count_named(districts, extras):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("sc %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = entry
    note = ("%d of South Carolina's 46 counties, every seat the winner of its "
            "most recent election" % len(out))
    return out, problems, nameless, [path], note


AR_INTRO = ("Every Arkansas county is governed by a county judge, who runs the "
            "county and presides over the quorum court without a vote, and a "
            "quorum court of justices of the peace, one elected from each of "
            "its districts. ")
# The date style is the one _mn_date() writes for the read dates beside it.
AR_ELECTION = ("Every seat on the court, and the county judge's office, is "
               "elected at the general election of November 3, 2026 for a term "
               "that starts on January 1, 2027.")
AR_STANDFIRST = ("The county judge and the justices of the peace of the "
                 "%(heading)s, named by district where a source says who sits "
                 "for it.")
AR_DESC = ("%(county)s County's quorum court: its county judge, and the "
           "justice of the peace for each of its %(districts)d districts where "
           "a source names one.")
AR_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above is "
                 "published by the county, the Arkansas Judiciary or the "
                 "Association of Arkansas Counties,\nand where none of them "
                 "says who sits for a district this page says so rather than "
                 "filling the gap.")
AR_CTA_NOTE = ("Opens the map with the county and quorum court district layers "
               "on. The district lines are the state's own map of every "
               "county's justice of the peace districts.")
AR_RESULTS_NOTES = {
    "notOnList": "the justice of the peace elected here in 2024 is no longer on "
                 "the Association of Arkansas Counties' current list for the "
                 "county",
    "noWinner": "the association's 2024 election results list no winner for "
                "this district",
    "unclear": "the 2024 winner's name cannot be matched with certainty to "
               "anyone on the association's current list",
}
AR_SUFFIXES = ("jr", "sr", "ii", "iii", "iv")


def _ar_fold(name):
    import unicodedata
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).split()


def _ar_unplaced(placed, listed):
    """The justices on the association's list whom no district on the page
    names, so a page can list them rather than drop them.

    THIS IS NOT A SECOND READING OF WHO SITS WHERE. The district names were
    matched to the list when the roster was built (match_results and NUMBERED
    in ar/scripts/build_ar_county_officials.py); this asks only which list
    names are left over, in three passes that each take a name only when one
    candidate answers — the whole name, then a surname nobody else on the list
    shares, then the surname with the first given name — and the caller fails
    the build unless what is left is exactly as many people as the districts
    left unnamed. A list name this cannot account for therefore stops the
    build rather than appearing twice or not at all."""
    pool = list(listed)
    left = list(placed)

    def words(n):
        return [w for w in _ar_fold(n) if w not in AR_SUFFIXES]

    def take(test):
        for p in list(left):
            hits = [n for n in pool if test(p, n)]
            if len(hits) == 1:
                pool.remove(hits[0])
                left.remove(p)

    take(lambda p, n: _ar_fold(p) == _ar_fold(n))
    take(lambda p, n: words(p)[-1:] == words(n)[-1:]
         and sum(1 for m in pool if words(m)[-1:] == words(n)[-1:]) == 1)
    take(lambda p, n: words(p)[-1:] == words(n)[-1:]
         and words(p)[:1] == words(n)[:1])
    return pool, left


def ar_quorum_courts(inst):
    """Arkansas: ONE file keyed by county GEOID ("05119"), each record carrying
    the county judge and the quorum court (ar/scripts/build_ar_county_officials.py):
    the association's list of the court's justices, which does not number them,
    and either the county's own numbered list (`quorumCourt.districts`) or the
    association's 2024 results matched to that list (`quorumCourt.results`).

    THE PAGE NAMES WHAT THE DISTRICT CARD NAMES, IN THE SAME ORDER OF
    PRECEDENCE: the county's own list wherever it exists, a "Vacant" there
    being a vacancy; otherwise the 2024 winner while the association's list
    still includes them; otherwise the reason the card gives, and no name. The
    number of districts is the state's map's, so a district no source names
    still has its section. Justices on the list that no district names are
    listed after the districts, and the county judge before them."""
    path = os.path.join(app_data(inst["tag"]), "ar-county-officials.json")
    map_path = os.path.join(app_data(inst["tag"]), "ar-quorum-court-districts.json")
    drawn = {}
    for f in _read(map_path).get("features") or []:
        props = f.get("properties") or {}
        drawn.setdefault(str(props.get("countyFips")), set()).add(
            str(props.get("district")))
    out, problems, nameless = {}, [], set()
    for geoid, rec in sorted(_read(path).items()):
        name = re.sub(r"\s+County$", "", (rec.get("county") or "").strip())
        qc = rec.get("quorumCourt") or {}
        judge = rec.get("judge") or {}
        labels = sorted(drawn.get(geoid) or (), key=district_sort_key)
        read_on = _mn_date(qc.get("asOf"))
        if not name or not labels or not read_on:
            problems.append("ar-county-officials.json %r carries no county or no "
                            "read date, or the district map draws none" % geoid)
            continue
        if labels != [str(i) for i in range(1, len(labels) + 1)]:
            problems.append("ar %s County: the district map does not number its "
                            "districts 1..N" % name)
            continue
        listed = [j["name"].strip() for j in qc.get("justices") or []
                  if not j.get("vacant") and (j.get("name") or "").strip()]
        list_vacant = sum(1 for j in qc.get("justices") or [] if j.get("vacant"))
        own = qc.get("districts")
        res = None if own else (qc.get("results") or {})
        if own is not None and set(own) != set(labels):
            problems.append("ar %s County: the county's own list numbers "
                            "districts the map does not draw" % name)
            continue

        districts, placed, unnamed = [], [], 0
        for label in labels:
            if own is not None:
                held = (own.get(label) or "").strip()
                if not held or re.match(r"(?i)^vacant$", held):
                    districts.append(district(label, vacancies=1))
                    unnamed += 1
                    continue
            else:
                held = ((res.get("districts") or {}).get(label) or "").strip()
                if not held:
                    why = [k for k in AR_RESULTS_NOTES
                           if label in (res.get(k) or [])]
                    if len(why) != 1:
                        problems.append("ar %s County District %s: the 2024 "
                                        "results neither name it nor say why"
                                        % (name, label))
                        continue
                    districts.append(district(label,
                                              note=AR_RESULTS_NOTES[why[0]] + "."))
                    unnamed += 1
                    continue
            placed.append(held)
            districts.append(district(label, [{"name": held,
                                               "role": inst["member_word"]}]))

        extras = []
        if (judge.get("name") or "").strip():
            judge_read = _mn_date(judge.get("asOf"))
            src = (judge.get("source") or "the Arkansas Judiciary's directory of "
                   "county judges and clerks").strip()
            line = src[:1].upper() + src[1:] + (
                ", read %s." % judge_read if judge_read else ".")
            if (judge.get("note") or "").strip():
                line += " " + judge["note"].strip()
            p = {"name": judge["name"].strip(),
                 "role": "County Judge, presiding without a vote",
                 "elected": line}
            if (judge.get("phone") or "").strip():
                p["phone"] = judge["phone"].strip()
            extras.append(("county-judge", "County Judge", [p]))
        else:
            problems.append("ar %s County carries no county judge" % name)

        # Who on the list no district names. None where every district is
        # named or vacant, which is most counties, and then the list is not
        # read at all, so a spelling difference between two publishers of a
        # name both have (Pulaski's Elliot and Elliott) cannot stop the build.
        needed = unnamed - list_vacant
        after = []
        if needed > 0:
            rest, unmatched = _ar_unplaced(placed, listed)
            if unmatched or len(rest) != needed:
                problems.append("ar %s County: %d district(s) name nobody and "
                                "the association lists %d justice(s) no "
                                "district names (%s); the two must agree before "
                                "a page can list them"
                                % (name, needed, len(rest), ", ".join(rest)))
                continue
            extras.append(("not-placed",
                           "Justices not matched to a district",
                           [{"name": n, "role": inst["member_word"]}
                            for n in rest]))
            after.append("not-placed")
            for d in districts:
                if d["note"]:
                    d["note"] = d["note"][:-1] + (
                        "; the justices this page cannot place in a district "
                        "are listed after the districts.")

        if own is not None:
            how = ("%s County publishes its own list of its quorum court by "
                   "district, and this page names each district's justice from "
                   "it, read on %s." % (name, _mn_date(qc.get("districtAsOf"))
                                        or read_on))
        else:
            how = ("No list from %s County says which justice sits for which "
                   "district, so this page names each district's justice from "
                   "the Association of Arkansas Counties' 2024 general election "
                   "results, and only while the association's current list for "
                   "the county, read on %s, still includes the winner." %
                   (name, read_on))
        lede = esc(AR_INTRO + how + " " + AR_ELECTION).replace("%", "%%")

        def link(url, text):
            return ('<a href="%s" rel="noopener" target="_blank">%s</a>'
                    % (esc(url), esc(text))) if url else esc(text)
        judge_src = (judge.get("source") or "the Arkansas Judiciary's directory "
                     "of county judges and clerks").strip()
        sources = ["%s for the county judge" % link(judge.get("sourceUrl"),
                                                     judge_src),
                   "%s for the list of justices"
                   % link(qc.get("sourceUrl"), "the Association of Arkansas "
                          "Counties' page for %s County" % name)]
        if own is not None:
            sources.append("%s for who sits for which district"
                           % link(qc.get("districtSourceUrl"),
                                  "%s County's own list" % name))
        else:
            sources.append("%s for who sits for which district"
                           % link(res.get("sourceUrl"), "the association's 2024 "
                                  "election results"))
        source_html = "Sources: %s, %s and %s, each read on %s." % (
            sources[0], sources[1], sources[2], esc(read_on))

        entry = {"districts": districts, "extras": extras,
                 "after_anchors": after, "skipped": [],
                 "slug": county_slug(name), "at_large": False,
                 "source_file": path, "lede": lede,
                 "standfirst": AR_STANDFIRST, "desc": AR_DESC,
                 "disclaimer": AR_DISCLAIMER, "cta_note": AR_CTA_NOTE,
                 "source_html": source_html}
        if not _count_named(districts, extras):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("ar %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = entry
    note = ("%d of Arkansas's 75 counties, each county judge and every justice "
            "of the peace on the association's list, by district where a source "
            "places them" % len(out))
    return out, problems, nameless, [path], note


# The date style is the one _mn_date() writes for the edition date beside it.
# The calendar is the directory's own (its 2026 edition, page 127, lists
# "Supervisors" under the county offices elected in 2027 and the general
# election on November 2); nothing here states a term or when one starts.
MS_ELECTION = ("The Secretary of State's election calendar lists county "
               "supervisors among the offices elected at the general election "
               "of November 2, 2027.")
MS_STANDFIRST = ("Who holds each of the five seats on the %(heading)s, as the "
                 "Mississippi Secretary of State's County Offices and Directory "
                 "lists them.")
MS_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above is "
                 "printed in the Mississippi Secretary of State's County "
                 "Offices and Directory,\nand where the directory lists a seat "
                 "as vacant this page says so rather than filling the gap.")
MS_SEATS = ("1", "2", "3", "4", "5")


def ms_supervisors(inst):
    """Mississippi: ONE file keyed by county GEOID ("28001"), each record that
    county's page of the Secretary of State's County Offices and Directory
    (ms/scripts/build_ms_county_officials.py): five supervisors in the county's
    own word for a district ("District" or "Beat"), a seat the directory prints
    as vacant marked so, and the board's office where the directory prints one
    for the board rather than for one supervisor.

    FIVE SEATS EVERYWHERE, numbered 1 to 5, and the builder already refuses a
    county with any other count; this refuses it again, because a page with four
    sections would read as a smaller board rather than as a defect.

    THE MAP LINK OPENS WHAT THE APP DRAWS. ms-supervisor-counties.json lists the
    counties whose current district lines the app has confirmed, and outside
    them the supervisor district layer does not appear, so those pages open the
    County layer, whose card lists all five, rather than a layer a reader would
    find missing. That list is held to the districts file here: a county listed
    without five drawn districts, or drawn without being listed, fails, and so
    does a drawn county whose word for a district differs from the directory's.

    THE ELECTION COMMISSIONERS IN THE SAME RECORDS ARE NOT ON THESE PAGES. They
    are a separate elected body, and listing them on a board of supervisors'
    page would mark them as its members in the page's structured data."""
    path = os.path.join(app_data(inst["tag"]), "ms-county-officials.json")
    listed_path = os.path.join(app_data(inst["tag"]), "ms-supervisor-counties.json")
    map_path = os.path.join(app_data(inst["tag"]), "ms-supervisor-districts.json")
    listed = _read(listed_path)
    drawn = {}
    for f in _read(map_path).get("features") or []:
        props = f.get("properties") or {}
        drawn.setdefault(str(props.get("countyfips")), []).append(props)
    out, problems, nameless = {}, [], set()
    for geoid in sorted(set(listed) ^ set(drawn)):
        problems.append("ms %s: the list of drawn counties and the districts file "
                        "disagree about whether this county is drawn" % geoid)
    for geoid, rec in sorted(_read(path).items()):
        name = re.sub(r"\s+County$", "", (rec.get("county") or "").strip())
        word = rec.get("label")
        seats = rec.get("supervisors") or []
        published = _mn_date(rec.get("published"))
        edition = re.search(r"\b(\d{4}) edition\b", rec.get("source") or "")
        if not name or word not in ("District", "Beat") or not published \
                or not edition:
            problems.append("ms-county-officials.json %r carries no county, no "
                            "District or Beat label, no publication date or no "
                            "edition year" % geoid)
            continue
        if sorted(str(s.get("district")) for s in seats) != list(MS_SEATS):
            problems.append("ms %s County: the directory's supervisors are not "
                            "numbered 1 to 5" % name)
            continue
        districts = []
        for s in sorted(seats, key=lambda s: int(s["district"])):
            label = "%s %s" % (word, s["district"])
            held = (s.get("name") or "").strip()
            if s.get("vacant") is True:
                districts.append(district(label, vacancies=1))
            elif held:
                member = {"name": held, "role": inst["member_word"]}
                # The supervisor's own number where the directory prints one
                # that is not the board's (the board's is in the page's office
                # block), published since Adam's ruling of 2026-10-17.
                if (s.get("phone") or "").strip():
                    member["phone"] = s["phone"].strip()
                districts.append(district(label, [member]))
            else:
                problems.append("ms %s County %s names nobody and is not marked "
                                "vacant" % (name, label))
        if len(districts) != len(MS_SEATS):
            continue

        lower = word.lower()
        props = drawn.get(geoid)
        cta_layers = None
        if props:
            got = sorted(str(p.get("district")) for p in props)
            lines = {p.get("lines") for p in props}
            if got != list(MS_SEATS) or {p.get("label") for p in props} != {word} \
                    or len(lines) != 1:
                problems.append("ms %s County: the districts file does not draw "
                                "five %ss numbered 1 to 5 from one source, in the "
                                "directory's word" % (name, lower))
                continue
            how = lines.pop()
            source = (props[0].get("source") or "").strip()
            if how == "census":
                drawn_note = ("The %s lines are the Census Bureau's map of %s "
                              "County's supervisor %ss, which the Census changed "
                              "after the 2020 census." % (lower, name, lower))
            elif how == "county" and source:
                drawn_note = ("The %s lines are %s, redrawn along the Census "
                              "Bureau's 2020 census blocks." % (lower, source))
            else:
                problems.append("ms %s County: the districts file says neither "
                                "where its lines come from nor that they are the "
                                "Census Bureau's" % name)
                continue
            cta_note = ("Opens the map with the county and supervisor district "
                        "layers on. " + drawn_note)
        else:
            cta_layers = "county"
            cta_note = ("Opens the map with the county layer on, whose card lists "
                        "all five supervisors. This app has not confirmed %s "
                        "County's current supervisor %s lines, so the map does "
                        "not draw them." % (name, lower))

        calls = ("" if word == "District" else
                 ", which %s County calls beats" % name)
        lede = esc("Every Mississippi county is run by a board of five "
                   "supervisors, each elected from one of the county's five "
                   "districts%s. This page lists each of %s County's five %ss "
                   "and its supervisor as the Mississippi Secretary of State's "
                   "County Offices and Directory lists them, and the map's "
                   "County card reads the same list. %s"
                   % (calls, name, lower, MS_ELECTION)).replace("%", "%%")

        link = rec.get("sourceUrl") or ""
        page = rec.get("sourcePage")
        if link and isinstance(page, int) and page > 0:
            link += "#page=%d" % page
        title = (rec.get("source") or "").strip()
        title = title[:1].upper() + title[1:]
        cited = ('<a href="%s" rel="noopener" target="_blank">%s</a>'
                 % (esc(link), esc(title)) if link.startswith("https://")
                 else esc(title))
        printed = rec.get("printedPage")
        source_html = ("Source: %s (dated %s)%s. The Secretary of State publishes "
                       "it once a year, so a change on a board can take until "
                       "the next edition to appear here."
                       % (cited, esc(published),
                          ", page %d" % printed if isinstance(printed, int)
                          and printed > 0 else ""))
        # 155 characters is validate_serp_lengths.py's ceiling, and Jefferson
        # Davis, the longest county name, lands at 153 with "district".
        desc = ("Who holds each of the five seats on %(county)s County's board "
                "of supervisors, by " + lower + ", from the Mississippi Secretary "
                "of State's " + edition.group(1) + " directory.")

        entry = {"districts": districts, "extras": [], "skipped": [],
                 "slug": county_slug(name), "at_large": False,
                 "source_file": path, "lede": lede,
                 "standfirst": MS_STANDFIRST, "desc": desc,
                 "disclaimer": MS_DISCLAIMER, "cta_note": cta_note,
                 "source_html": source_html}
        if cta_layers:
            entry["cta_layers"] = cta_layers
        if not _count_named(districts, []):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("ms %s County names nobody" % name)
            nameless.add(name)
            continue
        out[name] = entry
    note = ("%d of Mississippi's 82 counties, five supervisors each, %d with "
            "their districts drawn" % (len(out), len(set(listed) & set(drawn))))
    return out, problems, nameless, [path, listed_path, map_path], note


# Louisiana's three kinds of parish governing body, as the Secretary of
# State's list names them (la/scripts/build_la_parish_officials.py): the body
# in running prose, and what its members are called.
LA_KINDS = {"police-jury": ("police jury", "Police Juror"),
            "council": ("council", "Council Member"),
            "commission": ("commission", "Commissioner")}
# A body whose name does not say which parish it governs. The heading is the
# page's h1; the title is shorter, because "East Baton Rouge Parish
# Metropolitan Council — districtry Louisiana" is 67 characters against
# validate_serp_lengths.py's 60.
LA_HEADINGS = {"22033": ("East Baton Rouge Parish Metropolitan Council",
                         "East Baton Rouge Metropolitan Council")}
# The two parishes that share one government with a city, whose governing body
# is that government's council. Said first, because a reader looking for a
# parish council there finds a city council.
LA_ONE_GOVERNMENT = {
    "22033": ("East Baton Rouge Parish and the City of Baton Rouge share one "
              "government, and its governing body is the Metropolitan Council."),
    "22071": ("Orleans Parish and the City of New Orleans share one government, "
              "and its governing body is the New Orleans City Council."),
}
LA_STANDFIRST = ("Every member of the %(heading)s, as the Louisiana Secretary of "
                 "State's list of elected officials prints them.")
LA_DISCLAIMER = ("districtry is an independent, unofficial civic reference.\n"
                 "It never guesses at who holds a seat: every name above is "
                 "printed in the Louisiana Secretary of State's list of elected "
                 "officials,\nand where the list names no one for a seat this "
                 "page says so rather than filling the gap.")
# Printed after "Not named — " on a seat the list skips (Avoyelles's District 4
# and LaSalle's District 5 on 2026-10-20).
LA_UNLISTED_NOTE = ("the Secretary of State's list names no one for this seat. "
                    "It does not say the seat is vacant, so this page does not "
                    "either.")


def _la_seat_key(label):
    """District 2 before District 10, and District 1, Place A before District
    1, Place B: the digits compare as numbers. re.split with one capturing
    group alternates text and digits, so two labels never compare a number
    with a word at the same position."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", label)]


def la_parish_bodies(inst):
    """Louisiana: ONE file keyed by parish GEOID ("22001"), each record one
    parish's governing body as the Secretary of State's list of elected
    officials names it (la/scripts/build_la_parish_officials.py): its members
    by district or ward, any elected at large, the parish president or mayor
    where the parish has one, and the body's office where the list prints one
    for the body rather than for one member.

    THE BODY NAMES ITSELF ON EVERY PAGE: a police jury in 38 parishes, a
    council in 25 and Caddo's commission, so each record's own `body` is the
    heading, and one whose name does not say which parish it governs takes its
    heading from LA_HEADINGS.

    THE PARISH'S EXECUTIVE IS NAMED IN THE LEDE AND IS NOT LISTED AS A MEMBER.
    A parish president, a mayor-president or New Orleans's mayor runs the
    parish government and is not a member of its council, so a section of
    their own would mark them as one in the page's structured data, the reason
    ms_supervisors leaves Mississippi's election commissioners off.

    A SEAT THE LIST SKIPS IS SHOWN AND NOT CALLED VACANT. Where a parish's
    districts are numbered and the list leaves one out (Avoyelles's District 4
    and LaSalle's District 5 on 2026-10-20), the page lists the seat with the
    sentence the app's card prints, because the list does not say the seat is
    vacant.

    THE MAP LINK OPENS WHAT THE APP DRAWS, the Mississippi rule:
    la-parish-district-parishes.json lists the parishes whose current lines
    the app has confirmed, and this holds that list to the districts file and
    each drawn parish's districts to this roster's seats. Every other parish's
    page opens the Parish layer, whose card lists the whole body."""
    path = os.path.join(app_data(inst["tag"]), "la-parish-officials.json")
    listed_path = os.path.join(app_data(inst["tag"]),
                               "la-parish-district-parishes.json")
    map_path = os.path.join(app_data(inst["tag"]), "la-parish-districts.json")
    listed = _read(listed_path)
    drawn = {}
    for f in _read(map_path).get("features") or []:
        props = f.get("properties") or {}
        drawn.setdefault(str(props.get("parishfips")), []).append(props)
    out, problems, nameless = {}, [], set()
    for geoid in sorted(set(listed) ^ set(drawn)):
        problems.append("la %s: the list of drawn parishes and the districts "
                        "file disagree about whether this parish is drawn" % geoid)
    records = _read(path)
    if len(records) != 64:
        problems.append("la-parish-officials.json carries %d parishes, not "
                        "Louisiana's 64" % len(records))
    for geoid, rec in sorted(records.items()):
        parish = (rec.get("parish") or "").strip()
        name = re.sub(r"\s+Parish$", "", parish)
        body = (rec.get("body") or "").strip()
        kind = LA_KINDS.get(rec.get("kind"))
        read = _mn_date(rec.get("read"))
        link = (rec.get("sourceUrl") or "").strip()
        if not name or name == parish or not body or not kind or not read \
                or not link.startswith("https://"):
            problems.append("la-parish-officials.json %r carries no parish, no "
                            "body, no kind of body this page knows, no read date "
                            "or no https source" % geoid)
            continue
        body_word, member_word = kind

        def person(s, role):
            m = {"name": (s.get("name") or "").strip(), "role": role}
            for key in ("party", "phone"):
                if (s.get(key) or "").strip():
                    m[key] = s[key].strip()
            return m

        groups, terms, bad = {}, [], False
        for s in rec.get("seats") or []:
            label = re.sub(r"\s+", " ", (s.get("seat") or "").strip())
            if not label or not (s.get("name") or "").strip():
                problems.append("la %s Parish lists a seat with no label or no "
                                "name" % name)
                bad = True
                continue
            groups.setdefault(label, []).append(person(s, member_word))
            terms.append(s.get("termEnds"))
        for label in rec.get("unlisted") or []:
            if label in groups:
                problems.append("la %s Parish lists %s as both named and left "
                                "out" % (name, label))
                bad = True
            groups.setdefault(label, [])
        at_large = []
        for s in rec.get("atLarge") or []:
            seat = (s.get("seat") or "").strip()
            if not (s.get("name") or "").strip() \
                    or not seat.lower().startswith("at large"):
                problems.append("la %s Parish lists an at-large seat with no "
                                "name, or one not marked at large" % name)
                bad = True
                continue
            at_large.append(person(s, "%s, %s" % (member_word,
                                                  seat[:1].lower() + seat[1:])))
            terms.append(s.get("termEnds"))
        if bad or not groups:
            continue
        # A skipped seat carries its reason as the district's note, so the
        # page prints why it names nobody and the done-standard report reads
        # the seat as answered with a stated reason, as it reads Monroe
        # County, Michigan's directory row with no commissioner on it.
        districts = [district(label, members,
                              note=None if members else LA_UNLISTED_NOTE)
                     for label, members
                     in sorted(groups.items(), key=lambda g: _la_seat_key(g[0]))]
        extras = [("at-large", "Elected at large", at_large)] if at_large else []
        n_district = sum(len(ms) for ms in groups.values())

        seat_word = ("ward" if all(l.startswith("Ward ") for l in groups)
                     else "district")
        props = drawn.get(geoid)
        cta_layers = None
        if props:
            got = sorted("%s %s" % (p.get("label"), p.get("district"))
                         for p in props)
            # A parish is drawn from ONE map: the Census's, or the parish
            # government's own (Orleans and East Baton Rouge, whose features
            # each carry the sentence saying whose map it is).
            lines = {p.get("lines") for p in props}
            sources = {(p.get("source") or "").strip() for p in props}
            if got != sorted(groups) or lines not in ({"census"}, {"own"}) \
                    or {p.get("body") for p in props} != {body} \
                    or (lines == {"own"} and (len(sources) != 1 or "" in sources)):
                problems.append("la %s Parish: the districts file does not draw "
                                "this roster's seats, under this body, from one "
                                "map it names" % name)
                continue
            if lines == {"census"}:
                cta_note = ("Opens the map with the parish and police jury or "
                            "council district layers on. The %s lines are the "
                            "Census Bureau's map of the %s's %ss (January 1, 2026 "
                            "edition), which the Census changed after the 2020 "
                            "census and which hold nearly equal numbers of people "
                            "in that census." % (seat_word, body_word, seat_word))
            else:
                said_source = sources.pop()
                cta_note = ("Opens the map with the parish and police jury or "
                            "council district layers on. The %s lines are %s%s."
                            % (seat_word, said_source[:1].lower(),
                               said_source[1:].rstrip(".")))
        else:
            cta_layers = "county"
            cta_note = ("Opens the map with the parish layer on, whose card lists "
                        "every member of the %s. This app has not confirmed %s "
                        "Parish's current %s lines, so the map does not draw them."
                        % (body_word, name, seat_word))

        heading, page_title = LA_HEADINGS.get(geoid, (body, body))
        whole = "city" if geoid == "22071" else "parish"
        said = [LA_ONE_GOVERNMENT.get(geoid)
                or "The %s is %s Parish's governing body." % (body, name)]
        # A seat the list skips is not a member, so a body with one says how
        # many seats it has and how many the list names, rather than giving a
        # member count that disagrees with the seats listed below it.
        empty = sum(1 for ms in groups.values() if not ms)
        if empty:
            said.append("Its members are elected from %d %ss%s, and the list "
                        "names a member for %d of the %ss."
                        % (len(groups), seat_word,
                           ", with %d more elected by the whole %s"
                           % (len(at_large), whole) if at_large else "",
                           len(groups) - empty, seat_word)
                        if at_large else
                        "Its members are elected from %d %ss, and the list "
                        "names a member for %d of them."
                        % (len(groups), seat_word, len(groups) - empty))
        elif at_large:
            said.append("Of its %d members, %d are elected from %ss and %d by "
                        "the whole %s." % (n_district + len(at_large), n_district,
                                           seat_word, len(at_large), whole))
        else:
            said.append("Its %d members are elected from %ss."
                        % (n_district, seat_word))
        exe = rec.get("executive") or {}
        if (exe.get("name") or "").strip() and (exe.get("title") or "").strip():
            said.append("The %s, %s, is elected by the whole %s and is not a "
                        "member of the %s." % (exe["title"].strip().lower(),
                                               exe["name"].strip(), whole,
                                               body_word))
        if rec.get("kind") == "police-jury":
            said.append("A police jury elects its own president from among its "
                        "members, and the Secretary of State's list does not "
                        "say who that is, so this page does not either.")
        said.append("This page lists every %s and the member who holds it as the "
                    "Louisiana Secretary of State's list of elected officials "
                    "prints them, and the map's Parish card reads the same list."
                    % seat_word)
        if len(set(terms)) == 1 and terms[0] and _mn_date(terms[0]):
            said.append("The list gives every member's term as ending on %s."
                        % _mn_date(terms[0]))
        lede = esc(" ".join(said)).replace("%", "%%")

        source_html = ('Source: <a href="%s" rel="noopener" target="_blank">%s</a>, '
                       "read on %s. The list is the Secretary of State's own "
                       "current record, and this project reads it again every "
                       "week." % (esc(link), esc((rec.get("source") or "").strip()
                                               or "the Louisiana Secretary of "
                                                  "State's list of elected "
                                                  "officials"), esc(read)))
        # 155 characters is validate_serp_lengths.py's ceiling. The longest is
        # St. John the Baptist's, whose council also has members elected at
        # large: it lands at 145. "Who holds each seat on the" put it at 156,
        # one over, because this comment had measured only the longest heading
        # (East Baton Rouge's, now 141) and not the at-large clause.
        desc = ("Who sits on the %(heading)s, by " + seat_word
                + (" and at large" if at_large else "")
                + ", from the Louisiana Secretary of State's list of elected "
                  "officials.")
        # The at-large members follow the districts, where a reader who found
        # their own district's member reads on to the members the whole parish
        # elects.
        entry = {"districts": districts, "extras": extras,
                 "after_anchors": {"at-large"}, "skipped": [],
                 "seat_word": seat_word,
                 "slug": county_slug(name), "at_large": False,
                 "source_file": path, "lede": lede, "heading": heading,
                 "page_title": page_title, "member_word": member_word,
                 "standfirst": LA_STANDFIRST, "desc": desc,
                 "disclaimer": LA_DISCLAIMER, "cta_note": cta_note,
                 "source_html": source_html}
        if cta_layers:
            entry["cta_layers"] = cta_layers
        if not _count_named(districts, extras):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append("la %s Parish names nobody" % name)
            nameless.add(name)
            continue
        out[name] = entry
    note = ("%d of Louisiana's 64 parishes, every governing body named, %d with "
            "their districts drawn" % (len(out), len(set(listed) & set(drawn))))
    return out, problems, nameless, [path, listed_path, map_path], note


def _mn_date(iso):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso or ""))
    if not m:
        return None
    return "%s %d, %s" % (_MN_MONTHS[int(m.group(2)) - 1], int(m.group(3)), m.group(1))


def _nobody_key(inst, county):
    return "%s/%s" % (inst["tag"], county)


# New York's county names, derived from the boundary file its own app ships
# (NYS ITS Civil Boundaries, 62 features) rather than a list kept here. The
# Illinois table above exists because that instance has no such file in
# data/app; New York does, so nothing here can go stale. Measured 2026-09-27:
# 62 names, no two slugging alike, and every one slugs to its own
# lowercase-hyphenated form.
NY_COUNTIES_FILE = "ny-counties.json"

# THE FIVE BOROUGHS HAVE NO COUNTY LEGISLATURE AND A ROSTER FOR ONE WOULD BE AN
# ERROR, not a county to add. New York City absorbed its five counties'
# governments; the Board of Estimate that had been the nearest thing was struck
# down in Board of Estimate of City of New York v. Morris (1989) and not
# replaced. So a file naming one of these is refused with the reason rather than
# rendered — the concept matrix has recorded this since before the tier opened,
# and an adapter that enumerates whatever ships needs the fact in code.
NY_NO_LEGISLATURE = {"bronx", "kings", "new-york", "queens", "richmond"}


def _ny_name_by_slug():
    path = os.path.join(app_data("ny"), NY_COUNTIES_FILE)
    names = {f["properties"]["NAME"]
             for f in _read(path)["features"]
             if (f.get("properties") or {}).get("NAME")}
    return {slug_of(n): n for n in names}, path


def ny_legislature(inst):
    """New York: one file per county, keyed by district, for the counties that
    elect a county legislature FROM districts.

    THREE FORMS AND ONLY ONE OF THEM HAS DISTRICTS TO INDEX. A New York county
    is governed by a county legislature elected from districts, by a board of
    SUPERVISORS who are the towns' own supervisors sitting ex officio, or — in
    Otsego — by a board of representatives whose form is its own question. Only
    the first has a district for a page to be about: a town-elected supervisor
    belongs on the municipality that elected them, and putting one on a county
    page would say they were elected countywide. So this reads the files that
    exist and the tier grows one county at a time, with the form proven per
    county before any roster is written.

    THE COUNTY COMES FROM THE FILENAME, because these records carry no `county`
    field — measured 2026-09-27, 0 of 18 keys in the first county's file — and
    there is no reason for a single-county file to repeat the county on every
    row. That is also exactly why `check_registration()` cannot see these files
    and the New York tier had to be registered by hand: its two signals are
    "names people" and "looks like county", this shape passes the first and
    fails both forms of the second, and `_COUNTY_WORDS` holds the five form
    words of the states that were already registered with no `legislature`
    among them.

    TWO KEYS THAT ARE NOT DISTRICTS, skipped and counted rather than guessed
    at: a `board` block carrying the body's own office, telephone and term (the
    Cook County second-address rule — a number printed against every member is
    the switchboard and belongs to nobody), and an `_about` string.

    ONE NAMING QUESTION IS RECORDED RATHER THAN DECIDED. The boundary file
    spells St Lawrence County without a period, which is what a heading would
    print, while the county writes "St. Lawrence". Nothing turns on it until
    that county ships a roster, and it is named here so whoever ships it
    decides deliberately instead of discovering it on a page."""
    name_by_slug, names_path = _ny_name_by_slug()
    data_dir = app_data(inst["tag"])
    paths = sorted(glob.glob(os.path.join(data_dir, "*-legislature-members.json")))
    out, problems, nameless, used = {}, [], set(), []
    for path in paths:
        slug = re.sub(r"-legislature-members\.json$", "", os.path.basename(path))
        if slug in NY_NO_LEGISLATURE:
            problems.append(
                "%s names %r, one of New York City's five counties, which have "
                "no county legislature — the city absorbed their governments and "
                "Board of Estimate v. Morris (1989) struck down the nearest "
                "thing without replacing it. A roster here is an error rather "
                "than a county to index"
                % (os.path.relpath(path, REPO_ROOT), slug))
            continue
        name = name_by_slug.get(slug)
        if name is None:
            problems.append(
                "%s names county slug %r, which %s does not carry — either the "
                "filename is wrong or the two have diverged"
                % (os.path.relpath(path, REPO_ROOT), slug,
                   os.path.relpath(names_path, REPO_ROOT)))
            continue
        used.append(path)
        data = _read(path)
        districts, skipped, source = [], [], None
        for key in sorted(data, key=district_sort_key):
            entry = data[key]
            if not isinstance(entry, dict):
                skipped.append(key)          # `_about`, a string
                continue
            source = source or entry.get("sourceUrl")
            if isinstance(entry.get("members"), list):
                districts.append(district(key, entry["members"],
                                          entry.get("vacancies") or 0))
            else:
                skipped.append(key)          # the `board` block
        if not _count_named(districts, []):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append(
                    "%s names nobody — %d key(s), no name on any district. "
                    "Either the roster regressed, or this county belongs in "
                    "NAMES_NOBODY with a reason"
                    % (os.path.relpath(path, REPO_ROOT), len(data)))
            nameless.add(name)
            continue
        out[name] = {"districts": districts, "sourceUrl": source, "extras": [],
                     "skipped": skipped, "slug": slug, "at_large": False,
                     "source_file": path}
    note = ("ny   %d county legislature(s) read; New York's other counties elect "
            "a board of supervisors or, in Otsego, a board of representatives, "
            "and neither has a district to index" % len(out))
    return out, problems, nameless, used + [names_path], note



NY_SUPERVISOR_FILE = "ny-supervisor-members.json"


def ny_supervisors(inst):
    """New York: the counties governed by a BOARD OF SUPERVISORS, where the
    county board seat is a town or a city rather than a district.

    IT IS A SECOND REGISTRY ENTRY FOR ONE STATE, not a second adapter on the
    legislature entry, because the two forms are two bodies with two names. A
    county legislature's page is headed "Tompkins County Legislature" and its
    seats are districts; a board of supervisors' page is headed "Saratoga
    County Board of Supervisors" and its seats are towns. One heading cannot
    say both, so New York holds two entries and `inst_key` keeps them apart.

    ONE FILE FOR EVERY COUNTY, keyed by county slug, where the legislature tier
    is one file per county. The shape is the roster's rather than a choice here:
    a board of supervisors publishes a single table of towns and the file holds
    one county's table per key, so the slug is in the data and nothing has to be
    read off a filename.

    THE SEAT NAMES THE TOWN OR CITY AND SAYS WHICH, because New York has towns
    and cities of the same name — a page headed just "Clifton Park" would not
    say whether the row is the town's seat. `district_word` is empty for this
    entry and the label carries "Town of" or "City of" itself.

    MORE THAN ONE SUPERVISOR PER SEAT IS NORMAL rather than an error to
    reconcile: New York County Law lets a town or city elect more than one, and
    Saratoga seats two for the town of Clifton Park and two for the city of
    Saratoga Springs. So the seat count on a page is the SEATS the county states
    and never the number of towns.

    NOTHING HERE SAYS ELECTED COUNTYWIDE. Each supervisor is elected by the one
    town or city their section is headed with, which is what the page states in
    words; the Iowa tier already draws this distinction for its own plan-2
    counties, and getting it wrong would claim a countywide mandate for
    somebody who has none."""
    name_by_slug, names_path = _ny_name_by_slug()
    path = os.path.join(app_data(inst["tag"]), NY_SUPERVISOR_FILE)
    if not os.path.exists(path):
        return {}, [], set(), [], "ny   no board-of-supervisors roster ships yet"
    data = _read(path)
    out, problems, nameless = {}, [], set()
    for slug in sorted(data):
        rec = data[slug]
        name = name_by_slug.get(slug)
        if name is None:
            problems.append(
                "%s names county slug %r, which %s does not carry — either the "
                "roster is wrong or the two have diverged"
                % (os.path.relpath(path, REPO_ROOT), slug,
                   os.path.relpath(names_path, REPO_ROOT)))
            continue
        units = rec.get("units") or {}
        districts = []
        for unit in sorted(units):
            entry = units[unit] or {}
            kind = "City of" if entry.get("type") == "city" else "Town of"
            districts.append(district("%s %s" % (kind, unit),
                                      entry.get("members") or []))
        # THE COUNTY'S OWN STATED SEAT COUNT IS THE GATE, and it is checked
        # here as well as in the builder: this generator can ship a page
        # claiming a board size, so it must not be the one reader that takes
        # the number on trust.
        seated = sum(len(d["members"]) for d in districts)
        if rec.get("seats") and rec["seats"] != seated:
            problems.append(
                "%s seats %d supervisor(s) for %s and the county's own page "
                "states %d — the page would state a board size the county "
                "contradicts"
                % (os.path.relpath(path, REPO_ROOT), seated, name,
                   rec["seats"]))
            continue
        if not _count_named(districts, []):
            if _nobody_key(inst, name) not in NAMES_NOBODY:
                problems.append(
                    "%s names nobody for %s — either the roster regressed, or "
                    "this county belongs in NAMES_NOBODY with a reason"
                    % (os.path.relpath(path, REPO_ROOT), name))
            nameless.add(name)
            continue
        out[name] = {"districts": districts, "sourceUrl": rec.get("sourceUrl"),
                     "extras": [], "skipped": [], "slug": slug,
                     "at_large": False, "source_file": path}
    note = ("ny   %d board(s) of supervisors read, %d seat(s) over %d town(s) "
            "and city(ies)"
            % (len(out),
               sum(len(d["members"]) for r in out.values() for d in r["districts"]),
               sum(len(r["districts"]) for r in out.values())))
    return out, problems, nameless, [path, names_path], note


def _count_named(districts, extras):
    n = sum(1 for d in districts for m in d["members"]
            if (m.get("name") or "").strip())
    return n + sum(1 for _a, _h, ms in extras for m in ms
                   if (m.get("name") or "").strip())


# Every adapter returns (counties, problems, nameless, paths_read, note):
#   counties    {county name: record} — the pages to write.
#   problems    anything that should fail the build, in words.
#   nameless    counties whose roster named nobody, checked against NAMES_NOBODY.
#   paths_read  the roster files it read, which is what check_workflows() holds
#               the weekly jobs to. Derived, so a new roster file is covered by
#               the gate the moment an adapter reads it.
#   note        one line for the OK output, or None.
ADAPTERS = {"il_districted": il_districted, "il_at_large": il_at_large,
            "ia_at_large": ia_at_large,
            "wi_seats": wi_seats, "ia_supervisors": ia_supervisors,
            "mi_commissioners": mi_commissioners,
            "mn_commissioners": mn_commissioners,
            "in_commissioners": in_commissioners,
            "ok_commissioners": ok_commissioners,
            "nc_commissioners": nc_commissioners,
            "sc_councils": sc_councils,
            "ky_county_governments": ky_county_governments,
            "tn_commissioners": tn_commissioners,
            "ar_quorum_courts": ar_quorum_courts,
            "ms_supervisors": ms_supervisors,
            "la_parish_bodies": la_parish_bodies,
            "ny_supervisors": ny_supervisors,
            "ny_legislature": ny_legislature}


# Party, as the fleet's rosters actually spell it. MEASURED 2026-09-13 across
# the three instances: five spellings for two parties — Republican 1,347 / R
# 170 / (R) 7, and Democratic 365 / Democrat 152 / D 33 / (D) 18 — plus
# Independent 24, "No party" 10 and one Libertarian. Each county's own page is
# internally consistent and the fleet is not, so a page printing them verbatim
# says "R" beside one name and "Republican" beside the next.
#
# THIS NORMALISES NOTATION AND DECIDES NOTHING ABOUT A PERSON: every entry is
# one party under another spelling, and a value not in the table ships exactly
# as the county published it rather than being guessed at.
PARTY_NAMES = {
    "r": "Republican", "(r)": "Republican", "rep": "Republican",
    "republican": "Republican",
    "d": "Democratic", "(d)": "Democratic", "dem": "Democratic",
    "democrat": "Democratic", "democratic": "Democratic",
    "i": "Independent", "(i)": "Independent", "independent": "Independent",
    "l": "Libertarian", "libertarian": "Libertarian",
}


def party_name(value):
    v = (value or "").strip()
    return PARTY_NAMES.get(v.lower(), v)


# A label the source prints before a number ("home (843) 665-7321", "cell
# 519-3104") rides in the visible text, where a reader needs it to tell two
# numbers apart, and is left out of the structured data, whose telephone
# property is the number. A value with no label is unchanged.
PHONE_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z .]*?\s+(?=[(+0-9])")


def schema_telephone(value):
    return PHONE_LABEL_RE.sub("", (value or "").strip())


# Where an extension begins in a printed number ("ext. 12", "EXT 105",
# "x 236"). A tel: link dials the number before it: run onto the end of the
# number, the extension's digits would dial a different number. The extension
# stays in the text, where a reader sees it. The apps' cardPhoneDial (engine
# card-helpers) reads a number the same way.
EXTENSION_RE = re.compile(r"(^|[^A-Za-z])(?:ext(?:ension)?|x)[.:]?\s*\d", re.I)


def dial_digits(value):
    """What a tel: link dials for one printed number: its digits (and a
    leading +), stopping where an extension begins. Where two numbers are
    printed as one ("217/555-0100; 217/555-0101") it dials the first, as
    cardPhoneDial does: seven digits where the text opens with a local number
    (three digits, then four), eleven where it opens with the country code 1,
    and ten otherwise; a number written with a leading + is left whole."""
    value = value or ""
    m = EXTENSION_RE.search(value)
    if m:
        value = value[:m.start() + len(m.group(1))]
    dial = re.sub(r"[^0-9+]", "", value)
    if not dial.startswith("+") and len(dial) > 11:
        g = re.findall(r"\d+", value)
        dial = dial[:7 if len(g) > 1 and len(g[0]) == 3 and len(g[1]) == 4
                    else 11 if dial.startswith("1") else 10]
    return dial


# Made-up numbers, each with what its tel: link must dial. "fax" is there for
# the x a word can end in, which is not an extension. The last five are two
# numbers printed as one, in the shapes measured on 2026-10-17 (Mason County's
# municipal officials and Chicago's Ward 2) and three more a source could use.
DIAL_CASES = (
    ("(402) 555-0101 ext. 3203", "4025550101"),
    ("608-555-0102 EXT 105", "6085550102"),
    ("(217) 555-0103 x 236", "2175550103"),
    ("(712) 555-0104 x2", "7125550104"),
    ("555-0105 Ext: 7", "5550105"),
    ("cell 555-0106", "5550106"),
    ("+1 608 555 0107", "+16085550107"),
    ("fax 555-0108", "5550108"),
    ("217/555-0109; 217/555-0110", "2175550109"),
    ("(312) 555-0111 / 0112/0113", "3125550111"),
    ("555-0114 / 555-0115", "5550114"),
    ("1-800-555-0116 or 1-800-555-0117", "18005550116"),
    ("Home: (608) 555-0118 Cell: (608) 555-0119", "6085550118"),
)
CARD_HELPERS = os.path.join(REPO_ROOT, "engine", "index.html", "card-helpers.txt")


def check_dial_rule():
    """[] or the problems with how a tel: link is built: dial_digits must
    answer DIAL_CASES, the apps' cardPhoneDial must read an extension with the
    same pattern, and cardPhoneDial, run as shipped in Node, must answer
    DIAL_CASES too, so a card and a page cannot dial a number differently."""
    out = ["dial_digits(%r) gives %r, not %r" % (v, dial_digits(v), want)
           for v, want in DIAL_CASES if dial_digits(v) != want]
    try:
        block = open(CARD_HELPERS, encoding="utf-8").read()
    except OSError:
        return out + ["%s is missing: cardPhoneDial cannot be compared with "
                      "dial_digits" % os.path.relpath(CARD_HELPERS, REPO_ROOT)]
    m = re.search(r"function cardPhoneDial\(phone\) \{.*?var m = /(.+?)/i\.exec\(s\);",
                  block, re.S)
    if not m:
        out.append("cardPhoneDial in %s no longer reads an extension with one "
                   "/.../i pattern, so it cannot be compared with dial_digits"
                   % os.path.relpath(CARD_HELPERS, REPO_ROOT))
    elif m.group(1) != EXTENSION_RE.pattern:
        out.append("cardPhoneDial reads an extension as /%s/i and dial_digits as "
                   "/%s/i: a card and a page would dial a number differently"
                   % (m.group(1), EXTENSION_RE.pattern))
    # THE FUNCTION ITSELF, RUN AS SHIPPED, because the extension pattern is not
    # all of the rule: what a link dials where two numbers are printed as one
    # is code, and two copies of code agree only when both are run.
    fn = re.search(r"^( *)function cardPhoneDial\(phone\) \{\n.*?^\1\}$", block,
                   re.S | re.M)
    if not fn:
        out.append("cardPhoneDial in %s cannot be found as one function, so it "
                   "cannot be run against DIAL_CASES"
                   % os.path.relpath(CARD_HELPERS, REPO_ROOT))
        return out
    src = (fn.group(0) + "\nprocess.stdout.write(JSON.stringify(%s.map(cardPhoneDial)));"
           % json.dumps([v for v, _ in DIAL_CASES]))
    try:
        run = subprocess.run(["node", "-e", src], capture_output=True, text=True,
                             timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return out + ["cardPhoneDial could not be run in Node (%s), so it cannot be "
                      "compared with dial_digits" % exc]
    if run.returncode != 0:
        said = [ln for ln in run.stderr.splitlines() if "Error" in ln]
        return out + ["cardPhoneDial failed in Node: %s"
                      % (said or run.stderr.strip().splitlines() or ["no output"])[0]]
    for (v, want), got in zip(DIAL_CASES, json.loads(run.stdout)):
        if got != want:
            out.append("cardPhoneDial(%r) gives %r, not %r: a card and a page would "
                       "dial a number differently" % (v, got, want))
    return out


def member_phones(m):
    """Every number a roster carries for one person, first one first: `phone`,
    then `phonesExtra`, the further numbers a source prints for the same
    person (a home and a cell line, say), each with its label in the text.
    A value with no digit in it is no number: Kankakee County's board page
    printed four members' telephones as "Coming Soon" until 2026-10-17, each
    a link that dialled nothing, where the card shows no telephone at all."""
    extras = m.get("phonesExtra") or []
    if isinstance(extras, str):
        extras = [extras]
    out = []
    for value in [m.get("phone")] + list(extras):
        value = (value or "").strip() if isinstance(value, str) else ""
        if value and re.search(r"\d", value) and value not in out:
            out.append(value)
    return out


def schema_telephones(m):
    """The structured-data telephone: one number as a string, several as a
    list, none as None."""
    numbers = [schema_telephone(p) for p in member_phones(m)]
    numbers = [n for n in numbers if n]
    if not numbers:
        return None
    return numbers[0] if len(numbers) == 1 else numbers


def member_node(m):
    """One officeholder as a schema.org Person, from the same fields
    member_html renders. Every field is optional: a roster that does not publish
    a telephone must not assert an empty one."""
    person = {"@type": "Person", "name": (m.get("name") or "").strip()}
    party = party_name(m.get("party"))
    if party:
        person["affiliation"] = party
    email = (m.get("email") or "").strip()
    if email:
        person["email"] = email
    phone = schema_telephones(m)
    if phone:
        person["telephone"] = phone
    # `url` and `profileUrl` are the same field under two names — Illinois's
    # builders write the first, Wisconsin's the second. `documentUrl` is a
    # different thing (a county directory, not the person's own page) and is
    # deliberately not published as sameAs, which would claim it identifies them.
    url = next((u for u in ((m.get("url") or "").strip(),
                            (m.get("profileUrl") or "").strip()) if u), "")
    if url.startswith("http"):
        person["sameAs"] = url
    return person


def board_graph(rec, inst, canonical, head, name):
    """The board as linked data: the organisation, who is in it and in what
    seat, and the list of its districts.

    WHY. Measured 2026-09-16 these 183 pages listed 2,869 named officeholders
    in their HTML and described none of them in structured data — the
    GovernmentOrganization carried a name and an area and nothing else, which is
    the audit's own high-severity schema finding. A crawler could read the names
    and had no statement that they hold seats on the body the page is about.

    NOBODY IS DESCRIBED TWICE. Each seat is an OrganizationRole with a stable
    `@id` under the page's own URL; the district ItemList REFERENCES those ids
    rather than repeating the people, so the two paths reach one object.

    A DISTRICT THE COUNTY NAMES NOBODY FOR STILL GETS A LIST POSITION, with the
    reason the page prints: `vacancies` where the county reports the seat open,
    the county's own `note` where somebody holds it and this project will not say
    who, and neither where the source simply does not say. Dropping it would make
    the list claim a smaller board than the county elects — the distinction the
    page's own three states already make.
    """
    org_id = canonical + "#board"
    roles, items = [], []
    # A record naming its own body names its own members too (Nashville's
    # Metro Council seats Council Members, not Commissioners).
    member_word = rec.get("member_word") or inst["member_word"]
    # AN AT-LARGE BOARD HAS NO DISTRICT LIST AND GETS NO ItemList, which is the
    # statement its page already makes in words: every member is elected
    # countywide, so there are no seats to enumerate. Its members are still
    # roles on the organisation.
    for n, m in enumerate(rec.get("members") or [], 1):
        if not (m.get("name") or "").strip():
            continue
        roles.append({"@type": "OrganizationRole",
                      "@id": "%s-at-large-%d" % (org_id, n),
                      "roleName": (m.get("role") or "").strip()
                                  or member_word,
                      "member": member_node(m)})
    position = 0
    for d in rec.get("districts") or []:
        position += 1
        label = d["label"]
        seat = seat_heading(inst, label)
        ids = []
        for n, m in enumerate(d["members"], 1):
            if not (m.get("name") or "").strip():
                continue
            role_id = "%s-%s-%d" % (org_id,
                                    re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-"),
                                    n)
            roles.append({"@type": "OrganizationRole", "@id": role_id,
                          "roleName": (m.get("role") or "").strip()
                                      or member_word,
                          "namedPosition": seat,
                          "member": member_node(m)})
            ids.append(role_id)
        item = {"@type": "ListItem", "position": position, "name": seat}
        if len(ids) == 1:
            item["item"] = {"@id": ids[0]}
        elif ids:
            item["item"] = [{"@id": i} for i in ids]
        items.append(item)
    for anchor, heading, members in (rec.get("extras") or []):
        for n, m in enumerate(members, 1):
            if not (m.get("name") or "").strip():
                continue
            roles.append({"@type": "OrganizationRole",
                          "@id": "%s-%s-%d" % (org_id, anchor, n),
                          "roleName": (m.get("role") or "").strip() or heading,
                          "member": member_node(m)})
    org = {"@type": "GovernmentOrganization",
           "@id": org_id,
           "name": head,
           "url": canonical,
           "areaServed": {"@type": "AdministrativeArea",
                          "name": "%s %s, %s" % (name,
                                                 inst.get("county_word", "County"),
                                                 inst["state"])}}
    if roles:
        org["member"] = roles
    roster = None
    if items:
        roster = {"@type": "ItemList", "@id": canonical + "#districts",
                  "name": "%s districts" % head,
                  "itemListOrder": "https://schema.org/ItemListOrderAscending",
                  "numberOfItems": len(items),
                  "about": {"@id": org_id},
                  "itemListElement": items}
    return org, roster


def member_html(m):
    """One member. Every field is optional and an absent one is absent from the
    markup — a roster that does not publish a phone must not render an empty
    row that reads as one.

    `url` and `profileUrl` are the SAME FIELD under two names: Illinois's
    builders write the first, Wisconsin's the second, and reading only one
    would drop 164 Wisconsin supervisor pages without anything saying so.
    `documentUrl` is a third thing rather than a third name — where a county
    publishes its board in a document and not on a page, that document is the
    only place the name is checkable (Adams County's board page names none of
    its twenty supervisors), so it is labelled for what it is."""
    name = (m.get("name") or "").strip()
    if not name:
        return None
    bits = ['<span class="m-name">%s</span>' % esc(name)]
    role = (m.get("role") or "").strip()
    if role:
        bits.append('<span class="m-role">%s</span>' % esc(role))
    party = party_name(m.get("party"))
    if party:
        bits.append('<span class="m-party">%s</span>' % esc(party))
    contact = []
    email = (m.get("email") or "").strip()
    if email:
        contact.append('<a href="mailto:%s">%s</a>' % (esc(email), esc(email)))
    for phone in member_phones(m):
        contact.append('<a href="tel:%s">%s</a>'
                       % (esc(dial_digits(phone)), esc(phone)))
    for field, label in (("url", "Official profile"),
                         ("profileUrl", "Official profile"),
                         ("documentUrl", "County directory")):
        url = (m.get(field) or "").strip()
        if url.startswith("http"):
            contact.append('<a href="%s" rel="noopener" target="_blank">%s</a>'
                           % (esc(url), label))
            if label == "Official profile":
                break
    if contact:
        bits.append('<span class="m-contact">%s</span>' % " · ".join(contact))
    when, _why = freshness(m)
    if when:
        bits.append('<span class="m-asof">%s</span>' % esc(when))
    return '<li class="member">%s</li>' % "".join(bits)


DEFAULT_AS_OF_WHY = ("The county's website refuses automated readers, so these "
                     "names are a dated capture rather than the weekly re-read "
                     "the other named counties get.")


def freshness(m):
    """How old this name is, split into the DATE and the EXPLANATION.

    A NAME WITH NO DATE READS AS TODAY'S. Wisconsin's card learned that the hard
    way — the row was lost in a merge and 63 dated captures read as weekly
    re-reads for as long as it was gone — so where the roster carries the date,
    the page carries it too. Illinois's per-county rosters carry none of these
    fields and render nothing, exactly as before.

    THE TWO ARE SEPARATED BECAUSE ONE IS PER MEMBER AND THE OTHER IS NOT. The
    date can differ row to row and belongs on the row. The explanation is a fact
    about the COUNTY's website, identical on every row, and it was rendered on
    every one: measured 2026-09-15, Wisconsin's Dunn County page carried the
    same 27-word sentence 29 times in 1,312 words, so 60% of that page was one
    repeated sentence. Seven pages did it, 134 repetitions between them.
    """
    elected = (m.get("elected") or "").strip()
    if elected:
        # An election winner's own date, written whole by the adapter
        # (Minnesota): the date IS the claim, so it carries no explanation.
        return elected, ""
    as_of = (m.get("asOf") or "").strip()
    if as_of:
        return ("From %s." % as_of,
                (m.get("asOfWhy") or "").strip() or DEFAULT_AS_OF_WHY)
    read_on = (m.get("readOn") or "").strip()
    if not read_on:
        return "", ""
    via = (m.get("readVia") or "").strip()
    if via:
        return ("Read from %s's capture of %s." % (via, read_on),
                "That is the day the copy was taken, not the day it was fetched.")
    return ("Read on %s, and re-read every week." % read_on, "")


def freshness_notes(members):
    """Each distinct explanation once, in the order it first appears.

    The sentence is the ROSTER's, printed as published. Wisconsin's reads "so
    this name is a dated capture", which is exact on the app's card (one member
    per row) and slightly off here, where one copy now covers a whole board.
    Rewriting somebody else's provenance sentence from this side is worse than
    the nit; the fix, if it is worth making, is one word in
    wi/scripts/build_wi_county_board_roster.py, where it would be right on both
    surfaces.
    """
    out = []
    for m in members:
        _when, why = freshness(m)
        if why and why not in out:
            out.append(why)
    return "".join('<p class="unlisted">%s</p>' % esc(w) for w in out)


def districted_body(inst, name, rec):
    seats = sum(len(d["members"]) for d in rec["districts"])
    named = _count_named(rec["districts"], [])
    extra_named = _count_named([], rec.get("extras") or [])
    n_dist = len(rec["districts"])
    out = []
    # WHETHER THE MAP READS THIS FILE IS DERIVED, NOT WRITTEN, because it is the
    # one clause here that can be false. Every roster but one is in data/app and
    # is the very file the card fetches. Cook County's is not: il/index.html
    # calls the county's GIS people table live, and this roster is a weekly
    # snapshot of that same table, so the two can differ for up to a week.
    # Printing "the same roster the map's card reads" on that page would be a
    # false claim about the product on the product.
    source_file = rec.get("source_file")
    if not source_file:
        fail("%s has no source_file, so this cannot tell whether the app reads "
             "its roster — every adapter must record the path it read"
             % heading_of(inst, name, rec))
    app_reads = "%sdata%sapp%s" % (os.sep, os.sep, os.sep) in source_file
    same = ("it is the same roster the map's %s card reads"
            % esc(inst["phrase"]) if app_reads else
            "the map's %s card reads the same source live, so a card can be up "
            "to a week newer than this page" % esc(inst["phrase"]))
    # "Up to a week" is false of a copy nobody could re-read. The names stay —
    # a failed read never unpublishes what was read — and the sentence says how
    # old they are instead.
    if rec.get("not_read_since") and not app_reads:
        same = ("this page has not been re-read since %s, because the county's "
                "map service has not answered this project's weekly refresh since "
                "then, so these are the names it published before that day; the "
                "map's %s card asks the same service directly"
                % (esc(rec["not_read_since"]), esc(inst["phrase"])))
    # A county whose districts the map does not draw has no card reading
    # anything, so neither sentence above is true of it (il_districted says
    # how that is decided).
    if rec.get("undrawn"):
        if rec.get("not_read_since") or app_reads:
            fail("%s is marked undrawn but %s, and this page has no sentence "
                 "for that" % (heading_of(inst, name, rec),
                               "its roster is in data/app" if app_reads else
                               "its roster was kept unread"))
        same = ("the map does not draw these districts yet, so it cannot show "
                "which one an address is in")
    # A RECORD MAY STATE WHERE ITS NAMES CAME FROM, and the default below
    # cannot serve one that did not come from the county. "exactly as the
    # county publishes them" is true of every roster scraped from a county's
    # own board page and FALSE of a roster built from certified election
    # returns, which names who WON rather than who holds the seat today — the
    # posture Clark, Union and Williamson already ship under in Illinois. A
    # record carrying `lede` supplies its own sentence; one that does not
    # renders byte-identically to before this hook existed.
    if rec.get("lede"):
        out.append('<p class="lede">%s</p>'
                   % (rec["lede"] % {"county": esc(name),
                                     "heading": esc(heading_of(inst, name, rec)),
                                     "phrase": esc(inst["phrase"]),
                                     "districts": n_dist,
                                     "named": named}))
    else:
        out.append(
            '<p class="lede">The %s is elected by district. This page '
            'lists %s %s and the %s who %s them, exactly as the county %s '
            'them — %s.</p>'
            % (esc(heading_of(inst, name, rec)), n_dist,
               "district" if n_dist == 1 else "districts",
               "member" if named == 1 else "%d members" % named,
               "holds" if named == 1 else "hold",
               "published" if rec.get("not_read_since") and not app_reads
               else "publishes", same))
    # A RECORD MAY OPEN A DIFFERENT LAYER FROM ITS INSTANCE'S: Mississippi
    # draws supervisor districts only in the counties whose current lines it
    # has confirmed, so every other county's page opens the County layer,
    # whose card lists the board. A record without the key is unchanged.
    cta_layers = rec.get("cta_layers") or inst.get("cta_layers")
    # A LOUISIANA PAGE IS ABOUT A PARISH, and its concept path is the parish's
    # government rather than the map's district layer, so an instance may name
    # both words. One that names neither reads exactly as before.
    word = inst.get("county_word", "County")
    if cta_layers:
        # An instance whose board has no district layer yet opens the layer
        # whose card lists it, rather than a layer id its app does not register.
        out.append('<a class="cta" href="../#layers=%s">'
                   'See %s %s on the map →</a>'
                   % (esc(cta_layers), esc(name), esc(word)))
    else:
        # A record may name its seats: an Assumption Parish juror is elected
        # from a ward, and the link says so. One that does not reads "district".
        out.append('<a class="cta" href="../#layers=%s,county">'
                   'Find your %s %s %s on the map →</a>'
                   % (esc(inst.get("district_layer", inst["concept"])),
                      esc(name), esc(word), esc(rec.get("seat_word", "district"))))
    out.append('<p class="cta-note">%s</p>'
               % (esc(rec["cta_note"]) if rec.get("cta_note") else
                  "Opens the map with the county and %s layers on. Search your "
                  "address or ZIP, or tap your location."
                  % esc(inst["phrase"])))
    # An extra section renders before the districts unless the record names
    # its anchor in `after_anchors`: Arkansas lists the justices no district
    # names AFTER the districts, where a reader who did not find a name under
    # their own district looks next. A record without the key is unchanged.
    after = set(rec.get("after_anchors") or ())

    def extra_sections(trailing):
        for anchor, heading, members in rec.get("extras") or []:
            if (anchor in after) != trailing:
                continue
            rows = [h for h in (member_html(m) for m in members) if h]
            if not rows:
                continue
            out.append('<section class="district" id="%s">' % esc(anchor))
            out.append('<h2>%s</h2>' % esc(heading))
            out.append('<ul class="members">%s</ul>' % "".join(rows))
            out.append('</section>')

    extra_sections(False)
    for d in rec["districts"]:
        label = d["label"]
        # A whole label ("District 2", Indiana's) anchors as #district-2, the
        # same as a bare "2" does everywhere else.
        anchor = "district-%s" % re.sub(r"[^A-Za-z0-9]+", "-",
                                        re.sub(r"^District\s+", "", label)).lower()
        out.append('<section class="district" id="%s">' % esc(anchor))
        out.append('<h2>%s</h2>' % esc(district_heading(inst, d)))
        rows = [h for h in (member_html(m) for m in d["members"]) if h]
        if rows:
            out.append('<ul class="members">%s</ul>' % "".join(rows))
        if d["vacancies"]:
            # A VACANCY IS NOT AN ABSENT NAME, and saying "not listed" about a
            # seat the county has explicitly reported open is a false statement
            # about the county rather than a gap in this project. The app's own
            # card has always distinguished the two ("N of M seats is vacant");
            # the first draft of this page did not, and Jo Daviess's District 10
            # is exactly the case — filled last week, reported vacant this week.
            # WHO REPORTED IT is the instance's to say: Oklahoma's vacancies
            # are the State Election Board's roster, not the county's own word.
            out.append('<p class="unlisted">%d of %d seat%s here %s vacant, '
                       '%s.</p>'
                       % (d["vacancies"], len(rows) + d["vacancies"],
                          "" if len(rows) + d["vacancies"] == 1 else "s",
                          "is" if d["vacancies"] == 1 else "are",
                          esc(inst.get("vacancy_phrase", "as the county reports it"))))
        elif d["note"]:
            # A THIRD STATE: somebody holds this seat and this project will not
            # say who, with the reason printed. Wisconsin's Lincoln District 21
            # is the one — its county's map and the state's filing disagree
            # about the boundary — and reading that as a vacancy or as silence
            # would both be false.
            out.append('<p class="unlisted">Not named — %s</p>' % esc(d["note"]))
        elif not rows:
            # No name, no vacancy, no stated reason: the county's own source
            # does not say. A district dropped from the page would read as a
            # board of n-1.
            out.append('<p class="unlisted">Not listed in the county\'s '
                       'directory.</p>')
        out.append('</section>')
    extra_sections(True)
    unnamed = seats - named
    if unnamed:
        out.append('<p class="unlisted">%d of %d listed seats are not named by '
                   'the county\'s own source.</p>' % (unnamed, seats))
    board_seats = rec.get("seats")
    if board_seats and board_seats > n_dist:
        # The board's OWN size, where the county publishes one and it is bigger
        # than the district count — Menominee seats seven for five districts.
        # A page listing five districts beside a board of seven has to say so.
        out.append('<p class="unlisted">The county reports a board of %d seat%s, '
                   'which is %d more than the %d district%s above.</p>'
                   % (board_seats, "" if board_seats == 1 else "s",
                      board_seats - n_dist, n_dist, "" if n_dist == 1 else "s"))
    # ONE COPY OF EACH EXPLANATION, not one per member — see freshness().
    everyone = [m for d in rec["districts"] for m in d["members"]]
    everyone += [m for _a, _h, ms in (rec.get("extras") or []) for m in ms]
    out.append(freshness_notes(everyone))
    return "\n".join(x for x in out if x), n_dist, named + extra_named


def at_large_body(inst, name, rec):
    members = rec["members"]
    named = sum(1 for m in members if (m.get("name") or "").strip())
    out = []
    who = ("is the one member who represents" if named == 1
           else "%d members" % named)
    # A RECORD MAY STATE ITS OWN ELECTION METHOD, and Iowa's do. The sentence
    # below is true of a board elected at large and false of Iowa's plan 2
    # (countywide from residence districts) and plan 3 (by district, simply
    # not keyed to names here) -- so those carry their own lede rather than
    # being told they have no districts to be in. Illinois passes neither key
    # and renders byte-identically to before.
    if rec.get("lede"):
        out.append('<p class="lede">%s</p>'
                   % (rec["lede"] % {"county": esc(name),
                                     "phrase": esc(inst["phrase"]),
                                     "who": who}))
    else:
        out.append(
            '<p class="lede">%s County elects its %s <b>at large</b> — every '
            'member is chosen countywide, so there are no board districts to be in. '
            'These %s represent the whole county.</p>'
            % (esc(name), esc(inst["phrase"]), who))
    if rec.get("structure"):
        out.append('<p class="structure">%s</p>' % esc(rec["structure"]))
    rows = [h for h in (member_html(m) for m in members) if h]
    out.append('<section class="district" id="members">')
    out.append('<h2>Members</h2>')
    out.append('<ul class="members">%s</ul>' % "".join(rows) if rows else
               '<p class="unlisted">Not listed in the county\'s directory.</p>')
    out.append('</section>')
    if rec.get("seats") and rec["seats"] > named:
        out.append('<p class="unlisted">%d of %d seats are not named by %s.</p>'
                   % (rec["seats"] - named, rec["seats"],
                      esc(rec.get("source_label") or "the county's own source")))
    out.append('<a class="cta" href="../#layers=county">'
               'See %s County on the map →</a>' % esc(name))
    out.append('<p class="cta-note">%s</p>'
               % esc(rec.get("cta_note")
                     or ("Opens the map with the county layer on. An at-large "
                         "board has no district geometry, so the members above "
                         "are the answer for anywhere in the county.")))
    out.append(freshness_notes(rec["members"]))
    return "\n".join(x for x in out if x), 0, named


def source_note(rec, at_large):
    """Where the names came from, in the page's own words. A page that names
    people without saying who published them is the thing this project refuses
    everywhere else."""
    # A RECORD WHOSE NAMES COME FROM SEVERAL PUBLISHERS writes its own line,
    # already escaped (Arkansas: the judiciary for the judge, the association
    # for the list, the county or the 2024 results for the districts). It also
    # states only the day each was read, never a schedule: the job that re-reads
    # Arkansas's could not reach the association's site at go-live.
    if rec.get("source_html"):
        return '<p class="source-note">%s</p>' % rec["source_html"]
    bits = []
    if at_large:
        if rec.get("sourceDocument"):
            bits.append("Source: %s." % esc(rec["sourceDocument"]))
        elif rec.get("sourceUrl") and rec.get("source_label"):
            # A flat roster that is not the county's own says whose it is.
            bits.append('Source: <a href="%s" rel="noopener" target="_blank">%s</a>.'
                        % (esc(rec["sourceUrl"]), esc(rec["source_label"])))
        elif rec.get("sourceUrl"):
            bits.append('Source: <a href="%s" rel="noopener" target="_blank">the '
                        "county's own published roster</a>." % esc(rec["sourceUrl"]))
        if rec.get("verified"):
            bits.append("Verified %s." % esc(rec["verified"]))
    elif rec.get("sourceUrl") and rec.get("asOf"):
        # A PRESERVED COUNTY IS NOT RE-READ ON A SCHEDULE, so it must not say
        # it is. Its roster was fetched legitimately while the county was
        # serving and is kept (fleet policy, 2026-09-19: preserve data we have
        # already fetched), but nothing re-confirms it, and the sentence below
        # would assert a verification this project no longer performs on this
        # county. The date is what tells a reader how much to trust the names.
        bits.append('Source: <a href="%s" rel="noopener" target="_blank">the '
                    "county's own published roster</a>, last read %s and no "
                    "longer re-read. %s These names will go out of date."
                    % (esc(rec["sourceUrl"]), esc(rec["asOf"]),
                       esc(rec.get("asOfWhy") or "").strip()))
    elif rec.get("sourceUrl") and rec.get("source_label"):
        # A ROSTER THAT IS NOT THE COUNTY'S says whose it is. The sentence
        # below is false of a certified-returns route: the names are election
        # results, and calling them "the county's own published roster" is the
        # provenance claim the lede, standfirst and disclaimer already refuse.
        bits.append('Source: <a href="%s" rel="noopener" target="_blank">%s</a>, '
                    "re-read on a schedule and landed as a reviewed pull "
                    "request." % (esc(rec["sourceUrl"]), esc(rec["source_label"])))
    elif rec.get("sourceUrl"):
        bits.append('Source: <a href="%s" rel="noopener" target="_blank">the '
                    "county's own published roster</a>, re-read on a schedule "
                    "and landed as a reviewed pull request." % esc(rec["sourceUrl"]))
    if not bits:
        return ""
    return '<p class="source-note">%s</p>' % " ".join(bits)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(desc)s" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="%(canonical)s" />
<link rel="icon" href="%(favicon)s" type="image/svg+xml" />
%(goatcounter)s
<meta property="og:type" content="article" />
<meta property="og:site_name" content="%(app_name)s" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(og_image)s" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="en_US" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(desc)s" />
<meta name="twitter:image" content="%(og_image)s" />
<!-- GENERATED by scripts/build_county_pages.py from the shipped roster this
     county's own card reads. Do NOT hand-edit: `--check` fails the build, and
     a hand edit here would make the page and the card disagree about a real
     person. Fix the roster, or the scraper that writes it. -->
<script>
(function () {
  try {
    var stored = localStorage.getItem("districtry-theme");
    if (stored === "dark" || stored === "light") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (e) { /* blocked storage — prefers-color-scheme decides */ }
})();
</script>
<style>
%(fontface)s

:root {
  color-scheme: light dark;
%(light)s
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
%(dark)s
  }
}
:root[data-theme="dark"] {
%(dark)s
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 400 16px/1.6 var(--font-body);
  -webkit-text-size-adjust: 100%%;
}
a { color: var(--brand-700); }
:focus-visible { outline: 3px solid var(--brand-600); outline-offset: 2px; }

/* Focus-only, and the pair validate_contrast.py measures as (paper, ink):
   16.08:1 light and 15.36:1 dark. */
.skip-link {
  position: absolute; left: -9999px; top: 0;
  background: var(--ink); color: var(--paper);
  padding: 10px 16px; z-index: 10; border-radius: 0 0 6px 0;
}
.skip-link:focus { left: 0; }

main { max-width: 760px; margin: 0 auto; padding: 40px 20px 64px; }
.kicker {
  font: 600 13px/1 var(--font-body); letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); margin: 0 0 10px;
}
.kicker a { color: inherit; text-decoration: none; }
h1 {
  font: var(--font-heading-weight, 700) clamp(26px, 5vw, 34px)/1.15 var(--font-heading);
  margin: 0 0 6px; text-transform: uppercase; letter-spacing: 0.01em;
}
.title-sub { color: var(--ink-3); margin: 0 0 18px; font-size: 15px; }
.lede { color: var(--ink-2); margin: 0 0 16px; }
.structure {
  font-size: 14px; color: var(--muted); border-left: 3px solid var(--brand-border);
  padding: 2px 0 2px 12px; margin: 0 0 16px;
}
.cta {
  display: inline-block; margin: 6px 0 4px; padding: 11px 18px;
  background: var(--brand-700); color: var(--paper);
  border-radius: var(--radius-btn); font-weight: 600; text-decoration: none;
}
.cta:hover { background: var(--brand-600); }
.cta-note { font-size: 13px; color: var(--muted); margin: 6px 0 26px; }

.district { margin: 0 0 6px; padding: 14px 0 2px; border-top: 1px solid var(--border); }
.district h2 {
  font: var(--font-heading-weight, 700) 19px/1.2 var(--font-heading);
  margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.02em;
}
.members { list-style: none; margin: 0; padding: 0; }
.member { margin: 0 0 12px; }
/* 700, not the 650 this was written with. 650 is a weight no face here
   provides, so CSS font matching rounded it to the nearest face at or
   above the request, which is 700 -- measured in Chromium, the rendered
   advance width at 650 is identical to 700 and differs from 600. The
   officeholder names have been drawing at 700 all along; this says so. */
.m-name { display: block; font-weight: 700; }
.m-role { display: block; font-size: 13px; color: var(--muted); }
.m-party { display: block; font-size: 13px; color: var(--muted); }
/* How old the name is. Small, and under the contact details rather than over
   them, because it qualifies the name rather than competing with it — but it is
   on the page, because a name with no date reads as today's. */
.m-asof { display: block; font-size: 12.5px; color: var(--muted); margin-top: 2px; }
/* line-height 28px, the WCAG 2.5.8 spacing floor the landing and history
   footers were fixed to on 2026-09-13: these are 13.5px links that wrap. */
.m-contact { display: block; font-size: 13.5px; line-height: 28px; }
.unlisted { color: var(--muted); font-size: 14px; margin: 0 0 12px; }
.source-note {
  margin: 22px 0 0; padding: 12px 14px; font-size: 13.5px; color: var(--ink-3);
  background: var(--surface-2); border-radius: var(--radius-card);
}
/* WHO TO ASK. Its own rules rather than a reuse of .district, because a clerk
   is not a district: the same border and heading, and a body that reads as an
   address block rather than a list of members. */
.contact { margin: 18px 0 0; padding: 14px 0 2px; border-top: 1px solid var(--border); }
.contact h2 {
  font: var(--font-heading-weight, 700) 19px/1.2 var(--font-heading);
  margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.02em;
}
.contact .who { margin: 0; font-weight: 600; }
.contact .where { margin: 2px 0 0; font-size: 14px; color: var(--ink-3); }
/* 1.9, not 1.5: when the e-mail wraps at phone width, the telephone and the
   "County website" link sit on neighbouring lines, and at 1.5 their centres
   were as little as 20.3px apart across the 353 pages (measured 2026-10-21),
   under the 24px WCAG 2.5.8 spacing page_consistency_test.mjs holds, which it
   only samples. At 1.9 the closest pair on any page is 25.6px. */
.contact .detail { margin: 4px 0 0; font-size: 13.5px; line-height: 1.9; }
.disclaimer { font-size: 13px; color: var(--muted); margin: 14px 0 0; }
.foot {
  margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border);
  font-size: 14px; line-height: 28px; color: var(--muted);
}
.foot a { margin-right: 14px; }
</style>
<script type="application/ld+json">
%(jsonld)s
</script>
</head>
<body>
<a href="#page-main" class="skip-link">Skip to content</a>
<main id="page-main">
<p class="kicker">%(mark)s<a href="../">districtry / %(instance_word)s</a></p>
<h1>%(h1)s</h1>
<p class="title-sub">%(standfirst)s</p>
%(body)s
%(source)s
<p class="disclaimer">%(disclaimer)s</p>
<p class="foot">
<a href="../%(index_page)s">%(all_label)s</a>
<a href="../">Back to the map</a>
<a href="../sources.html">Sources &amp; data layers</a>
%(faq_link)s<a href="../../privacy.html">Privacy</a>
<a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a>
</p>
%(byline)s
</main>
</body>
</html>
"""


# The closing sentence of every one of these pages, hoisted out of the shell
# so a record can replace it. The line breaks are the template's own, kept so
# every page that does not override it is byte-identical to before.
DEFAULT_DISCLAIMER = (
    "districtry is an independent, unofficial civic reference.\n"
    "It never guesses at who holds a seat: every name above is published by the\n"
    "county itself, and where a county publishes none this page says so rather than\n"
    "filling the gap.")


def mark_svg():
    """The same inline mark the history pages carry, read from the one file."""
    svg = read(FAVICON, "the brand mark").strip()
    svg = svg.replace("<svg ", '<svg class="districtry-mark" width="18" height="18" '
                               'aria-hidden="true" style="vertical-align:-3px;'
                               'margin-right:6px" ', 1)
    return svg


def build_page(inst, name, rec, at_large, shell, contact=None):
    # A RECORD MAY NAME A DIFFERENT BODY FROM ITS INSTANCE'S. Indianapolis and
    # Marion County are one government, so Marion's governing body is the
    # City-County Council rather than a board of commissioners; its record
    # carries `wording` (heading, page_title, page_title_short, phrase,
    # member_word) and every sentence on its page reads from that instead. A
    # record without the key renders byte-identically to before it existed.
    if rec.get("wording"):
        inst = dict(inst, **rec["wording"])
    slug = rec["slug"]
    canonical = "%s%s/%s.html" % (inst["app_url"], inst["concept"], slug)
    body, n_dist, named = (at_large_body(inst, name, rec) if at_large
                           else districted_body(inst, name, rec))[:3]
    # WHO TO ASK, after the seats and before the source line. The page names who
    # holds the seats; a reader who thinks one of those names is wrong, or who
    # wants a ballot, needs the office that answers for it.
    block = contact_html(contact)
    if block:
        body = body + "\n" + block
    head = heading_of(inst, name, rec)
    own_title = rec.get("page_title") or (inst.get("page_title_for") or {}).get(name)
    title = "%s — %s" % (own_title or inst["page_title"] % {"county": name},
                         inst["app_name"])
    if len(title) > 60 and inst.get("page_title_short") and not own_title:
        title = "%s — %s" % (inst["page_title_short"] % {"county": name},
                             inst["app_name"])
    if at_large:
        # A FLAT ROSTER IS NOT A CLAIM ABOUT HOW THE COUNTY ELECTS. The default
        # clause below is true of a board elected at large and false of Iowa's
        # plan 2, plan 3, transitioning and plan-less counties, whose records
        # carry their own — the same split the lede already makes, applied to
        # the sentence a search result shows. Illinois passes no `desc` and
        # renders byte-identically to before.
        # "with contact details" came out on 2026-09-22, when Iowa's flat
        # pages put 55 descriptions over validate_serp_lengths.py's 155: it is
        # on every one of these pages, so it differentiates none of them, and
        # the districted half of this same generator never carried it. The
        # em dash matches that half too — the two shapes were gratuitously
        # different.
        desc = ("%s %s — %s, from %s."
                % (rec.get("desc_lead") or "Who sits on the", head, (rec.get("desc")
                          or "%d members elected at large across the whole "
                             "county") % named,
                   rec.get("source_label") or "the county's own published roster"))
    else:
        # `named` counts the EXTRA sections too — Illinois's elected chair,
        # Menominee's two at-large supervisors — and none of those people is in
        # any district (checked: no chair's name appears in that county's own
        # district list). So the description gives the district figure and says
        # what the extras are rather than printing a total the page never shows.
        extras = rec.get("extras") or []
        extra_n = sum(1 for _a, _h, ms in extras for m in ms
                      if (m.get("name") or "").strip())
        extra_words = {"chair": "the elected chair",
                       "at-large": "%d elected at large" % extra_n}
        # 155 characters is the gate's ceiling (scripts/validate_serp_lengths.py)
        # and the longest county name plus the longest suffix ran to 160, so
        # the contact clause goes rather than the counts, which are what make
        # one of these 73 descriptions different from the next.
        suffix = ", ".join(extra_words.get(a, "%d more" % extra_n)
                           for a, _h, ms in extras if ms)
        # Same hook as the flat branch: a record whose names did not come
        # from the county's own roster says so here too, or the search result
        # states a provenance the page itself contradicts.
        # THE SAME VOCABULARY THE LEDE HOOK TAKES. It was three keys against
        # the lede's five, and nothing caught it because Michigan's
        # certified-returns records are this hook's first consumer: a record
        # written to the lede's vocabulary raised KeyError('county') here.
        # Plain values, not esc()'d -- desc is escaped once at insertion
        # (esc(desc)), where the lede is inserted raw and escapes its own.
        desc = (rec["desc"] % {"head": head, "heading": head, "county": name,
                               "phrase": inst["phrase"],
                               "named": named - extra_n,
                               "districts": n_dist}
                if rec.get("desc") else
                "Who represents you on the %s — %d members across "
                "%d districts%s, from the county's own published roster."
                % (head, named - extra_n, n_dist,
                   " plus " + suffix if suffix else ""))
    # THE SAME HOOK, ON THE TWO SURFACES THE LEDE AND THE DESCRIPTION LEFT
    # BEHIND. This sentence sits under the H1 and the disclaimer closes the
    # page, and both asserted "the county's own published roster" on every
    # page of both routes -- so a reader of a certified-returns county was
    # told twice more that the county published these names, in the very
    # places a page states where its content came from. A record supplying
    # neither renders byte-identically to before this hook existed.
    standfirst = (rec["standfirst"] % {"head": head, "heading": head,
                                       "county": name,
                                       "phrase": inst["phrase"]}
                  if rec.get("standfirst") else
                  "Every member of the %s, from the county's own "
                  "published roster." % head)
    disclaimer = rec.get("disclaimer") or DEFAULT_DISCLAIMER

    graph = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical,
        "url": canonical,
        "name": title,
        "description": desc,
        "inLanguage": "en-US",
        "about": board_graph(rec, inst, canonical, head, name)[0],
        "author": {
            "@type": "Person",
            "@id": "https://districtry.com/#author",
            "name": "Adam Overberg",
            "url": "https://overberg.co",
            "email": "hello@overberg.co",
        },
        "isPartOf": {"@id": inst["app_url"] + "#website"},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": inst["app_name"],
                 "item": inst["app_url"]},
                {"@type": "ListItem", "position": 2,
                 "name": inst["index_label"],
                 "item": inst["app_url"] + inst["index_page"]},
                {"@type": "ListItem", "position": 3,
                 "name": "%s %s" % (name, inst.get("county_word", "County"))},
            ],
        },
    }
    roster = board_graph(rec, inst, canonical, head, name)[1]
    if roster:
        graph["mainEntity"] = roster
    jsonld = json.dumps(graph, indent=2, ensure_ascii=False).replace("</", "<\\/")

    return PAGE % dict(
        shell,
        title=esc(title), desc=esc(desc), canonical=esc(canonical),
        h1=esc(head), standfirst=esc(standfirst), disclaimer=esc(disclaimer),
        body=body, source=source_note(rec, at_large), jsonld=jsonld,
        og_image=esc(inst["app_url"] + "og-image.png"),
        app_name=esc(inst["app_name"]), index_page=esc(inst["index_page"]),
        all_label=esc(inst["all_label"]),
        # The masthead kicker names THIS instance. It was the literal
        # "districtry / illinois" until 2026-09-13, so all 72 Wisconsin and 17
        # Iowa pages carried Illinois's name in their own masthead — correct
        # for the instance the template was written in, wrong for every other,
        # and nothing compared it against the page it sat on. Found while
        # registering Michigan as the fourth instance. It belongs here rather
        # than in shell_for_pages(), which is built once and shared by all of
        # them and so cannot know which instance it is rendering.
        instance_word=esc(inst["state"].lower()),
        # Only where the instance ships one: Minnesota publishes no faq.html,
        # and a link to it would be a 404 on every one of its pages.
        faq_link=('<a href="../faq.html">Common questions</a>\n'
                  if os.path.exists(os.path.join(REPO_ROOT, inst["tag"], "faq.html"))
                  else ""),
    )


def render_index(inst, rows):
    """rows: [(county name, slug, seats, index note, kind)] — the index the
    topic page carries. Alphabetical, one flat list: a reader looking for their
    county scans a name, and a crawler gets 73 internal links from a page that
    already ranks for the concept.

    `kind` IS THE CLAIM AND THE RENDERER IS NOT. It is "districted",
    "at-large" or "flat", and the third is a roster with no district keys on a
    county that does not elect at large — Iowa's plan 2 elects countywide from
    residence districts and its plan 3 elects by district, neither of them at
    large, and both reach these pages as a flat list of names. Counting them in
    the at-large tally, or suffixing their rows ", at large", would state an
    election method Iowa Code does not give those counties, on the one page
    that lists every county at once.
    """
    at_large = sum(1 for r in rows if r[4] == "at-large")
    out = ['    <p class="matrix-lede">Every %s %s whose roster this '
           'project has: <b>%d %s</b>, <b>%d people</b>, %s.%s</p>'
           % (esc(inst["state"]), esc(inst.get("county_noun", "county")),
              len(rows), esc(inst.get("county_plural", "counties")),
              sum(r[2] for r in rows),
              esc(inst.get("index_provenance")
                  or "each name published by the county itself"),
              (" %d elect at large, with no districts." % at_large)
              if at_large else ""),
           '    <ul class="county-index">']
    for name, slug, seats, note, _kind in rows:
        out.append('      <li><a href="%s/%s.html">%s %s</a> '
                   '<span class="county-index-n">%d %s%s</span></li>'
                   % (esc(inst["concept"]), esc(slug), esc(name),
                      esc(inst.get("county_word", "County")), seats,
                      "member" if seats == 1 else "members", esc(note)))
    out.append("    </ul>")
    return "\n".join(out)


def write_index(inst, rows, check):
    """Splice render_index() into the topic page's GENERATED region."""
    page = index_page(inst)
    with open(page, encoding="utf-8", newline="") as f:
        text = f.read()
    begin = "<!-- ==== GENERATED:BEGIN %s ==== -->" % INDEX_REGION
    end = "<!-- ==== GENERATED:END %s ==== -->" % INDEX_REGION
    if begin not in text or end not in text:
        fail("%s carries no GENERATED region %r — the index has nowhere to go"
             % (os.path.relpath(page, REPO_ROOT), INDEX_REGION))
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    new = head + begin + "\n" + render_index(inst, rows) + "\n    " + end + tail
    if new == text:
        return False
    if not check:
        with open(page, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    return True


def roster_names(rec, at_large):
    """Every person the roster names for this county, chair included."""
    names = []
    if at_large:
        names += [m.get("name") for m in rec["members"]]
    else:
        names += [m.get("name") for d in rec["districts"] for m in d["members"]]
        names += [m.get("name") for _a, _h, ms in rec.get("extras") or []
                  for m in ms]
    return [n.strip() for n in names if (n or "").strip()]


def verify_page(inst, name, rec, at_large, html):
    """The check this work exists to pass: the page NAMES THE PEOPLE.

    Byte-equality against a regenerate already proves the page matches the
    template. It cannot prove the template puts the roster on the page — a
    generator that emitted a beautiful, correct, empty page would pass it every
    time. So this reads the shipped HTML back and asserts, per county, that
    every name in the roster appears in it and that at least one does.

    Names are compared HTML-ESCAPED, because that is what is on the page:
    O'Brien ships as O&#x27;Brien, and comparing the raw name would report a
    real, present officeholder as missing.
    """
    problems = []
    names = roster_names(rec, at_large)
    if not names:
        return ["%s: the page names nobody" % name]
    missing = [n for n in names if esc(n) not in html]
    if missing:
        problems.append(
            "%s: %d roster name(s) do not appear on the page it generated — %s"
            % (name, len(missing), ", ".join(missing[:4])))
    # Every district heading, too: a district dropped from the page reads to a
    # reader as a board one seat smaller than it is.
    if not at_large:
        for d in rec["districts"]:
            if ("<h2>%s</h2>"
                    % esc(district_heading(inst, d))) not in html:
                problems.append("%s: district %s has no section on its page"
                                % (name, d["label"]))
    return problems


WORKFLOW_DIR = os.path.join(REPO_ROOT, ".github", "workflows")


def _join_continuations(text):
    """Shell lines with trailing backslashes joined into one, so a command split
    across lines is matched as the one command it is."""
    out, buf = [], ""
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        out.append(buf + line)
        buf = ""
    if buf:
        out.append(buf)
    return out


def check_workflows(read_by_instance):
    """Every weekly job that rewrites a roster these pages read must regenerate
    them in the same run, and must stage THAT INSTANCE'S pages.

    60 workflows rewrite one, and a job that refreshes a roster without
    regenerating opens a bot PR carrying last week's names on a page and this
    week's in the JSON — and fails --check on a PR nobody wrote by hand, which
    is the worst place to discover a convention. The history page has needed
    exactly this rule since it shipped and enforces it nowhere; three workflows
    carry it because someone remembered.

    THE ROSTER LIST IS DERIVED FROM WHAT THE ADAPTERS ACTUALLY READ, not from a
    filename pattern, and the first version was a pattern
    (`[a-z-]+-county-board-members\.json`) which had two defects at once. It
    missed Menard and Lake, whose files are named for what those counties elect
    rather than to the pattern — so two workflows rewrote a roster this builder
    reads and were never asked to regenerate. And it matched Wisconsin's
    `county-board-members.json` by accident, so the one workflow that DID have
    to learn something new passed by staging Illinois's pages for a change to
    Wisconsin's roster. A pattern cannot tell which instance a file belongs to;
    the path can, so the check is per (instance, file).

    A workflow that WRITES no file is not asked to regenerate: the Mason
    watcher reads its source and opens nothing, so requiring a build step of it
    would be requiring a no-op.
    """
    problems = []
    for path in sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.yml"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if "git add " not in text:
            continue                      # a watcher: reads, commits nothing
        rel = os.path.relpath(path, REPO_ROOT)
        for inst in INSTANCES:
            hits = [r for r in read_by_instance.get(inst_key(inst), ())
                    if "%s/data/app/%s" % (inst["tag"], r) in text]
            if not hits:
                continue
            if "scripts/build_county_pages.py" not in text:
                problems.append(
                    "%s rewrites %s and never runs scripts/build_county_pages.py "
                    "— its bot PR would ship a page naming the members it just "
                    "replaced" % (rel, ", ".join(sorted(hits))))
            # A `git add` MAY SPAN LINES, so its continuations are joined
            # before matching. Reading only the line carrying `git add ` failed a
            # workflow that stages the pages correctly on a second line, which is
            # the defect validate_workflow_checkout.py had the same day in the
            # other direction: a gate whose verdict turns on where a line happens
            # to wrap. That one teaches the next author to mangle a comment; this
            # one teaches them to write one unreadable line. The shell's own rule
            # is that a trailing backslash continues the command, so that is the
            # rule applied here.
            staged = [ln for ln in _join_continuations(text) if "git add " in ln]
            want = "%s/%s" % (inst["tag"], inst["concept"])
            # THE DIRECTORY AS A PATH TOKEN, NEVER A SUBSTRING. `il/county-board`
            # is a substring of `il/county-board.html`, so a substring test passes
            # a workflow that stages the INDEX page and none of the per-county
            # pages underneath it — measured by dropping the directory from one
            # workflow, which the substring version waved through. The fleet
            # writes the bare directory (`git add il/county-board
            # il/county-board.html`), and git takes either that or a trailing
            # slash, so both spellings are accepted and the `.html` beside them
            # no longer stands in for them.
            if not any(tok == want or tok.startswith(want + "/")
                       for ln in staged for tok in ln.split()):
                problems.append(
                    "%s rewrites %s and stages no %s/ — the regenerated pages "
                    "would not be in its commit"
                    % (rel, ", ".join(sorted(hits)), want))
    return problems


# A roster this builder does NOT read, and why that is right rather than an
# oversight. The detector below finds every data/app file whose records name
# people and look county-shaped; everything it finds has to be either consumed
# by an adapter or named here with a reason and a date. Re-audited every run:
# an entry naming a file that has left the tree FAILS, which is the property
# ACCEPTED_DROPS had to be given after the fact.
#
# THIS IS THE WHOLE "AS COUNTIES COME ONLINE IN NEW STATES" MECHANISM, and it
# is deliberately a gate rather than a generator. A new state's county roster
# cannot ship quietly: the day it lands, this check fails with the file's name
# and the two ways to clear it — add an adapter, or write down why these pages
# are the wrong home for it. Nobody has to remember, and nothing is generated
# from a guess about a shape nobody has looked at.
NOT_COUNTY_BOARDS = {
    "mn/data/app/mn-county-town-officers.json": dict(
        date="2026-10-16",
        reason="the supervisors, clerks and treasurers of 416 Minnesota "
               "towns, read from the lists of township officers the counties "
               "publish. Real officeholders, named, and town government rather "
               "than county government: each record carries its county only "
               "to say whose list it came from.",
    ),
    "il/data/app/municipal-officials.json": dict(
        date="2026-09-13",
        reason="mayors, clerks and council members of 1,300 Illinois "
               "municipalities. Real officeholders, named, and not county "
               "government — a village trustee belongs on a municipal page, "
               "which is its own piece of work.",
    ),
    "il/data/app/township-officials.json": dict(
        date="2026-09-13",
        reason="township supervisors, clerks and assessors. A township is a "
               "unit below the county, not the county board.",
    ),
    "wi/data/app/wi-county-clerks.json": dict(
        date="2026-09-13",
        reason="the county CLERK, an administrative officer, one per county. "
               "Not a board member, and a page per clerk would be one name.",
    ),
    "wi/data/app/wi-municipal-clerks.json": dict(
        date="2026-09-13",
        reason="municipal clerks, 1,850 of them. Municipal, not county.",
    ),
    "wi/data/app/wi-town-boards.json": dict(
        date="2026-10-15",
        reason="Wisconsin TOWN boards, a chairperson and supervisors per town, "
               "read from each county's own directory. A town is a unit below "
               "the county, not the county board, which is the same reason "
               "il township-officials.json is recorded here.",
    ),
    "wi/data/app/wi-municipal-boards.json": dict(
        date="2026-10-01",
        reason="the governing body of the Wisconsin municipalities that elect "
               "their whole board at large — a village president and trustees, "
               "a mayor and council members. Municipal, not county, and these "
               "names already reach a reader on the City-or-Village card; a "
               "municipal page of their own is its own piece of work, the same "
               "answer municipal-officials.json gets above.",
    ),
    "ia/data/app/ia-township-officers.json": dict(
        date="2026-10-01",
        reason="township clerks and trustees, published by twelve Iowa "
               "counties for the 186 townships inside them. A township is a "
               "unit below the county, not the board of supervisors — the "
               "same reading il/data/app/township-officials.json already "
               "takes. The file is keyed by county only because the county is "
               "the publisher, which is exactly the shape this gate cannot "
               "tell apart from a county roster on its own.",
    ),
    "ia/data/app/ia-county-auditors.json": dict(
        date="2026-09-13",
        reason="the county auditor, who runs elections. One per county, not a "
               "supervisor.",
    ),
    "wi/data/app/wi-county-officers.json": dict(
        date="2026-09-13",
        reason="the county's other elected officers — sheriff, treasurer, "
               "register of deeds, clerk of circuit court, district attorney — "
               "plus the board chair's name. Row officers are a different "
               "concept from the board, and the chair is already a supervisor "
               "on these pages where the two rosters agree: 58 of the 69 chairs "
               "it names appear in wi/data/app/county-board-members.json by "
               "name, 11 do not (measured 2026-09-13), so joining on it would "
               "have to settle eleven disagreements first.",
    ),
    "in/data/app/in-county-councils.json": dict(
        date="2026-10-09",
        reason="the Indiana COUNTY COUNCIL, which is the county's fiscal body "
               "(IC 36-1-2-6) and not its legislative body — that is the board "
               "of commissioners (IC 36-1-2-9), which these pages read from "
               "in-county-commissioners.json. The council's members are named "
               "on the app's County card from the same certified results; a "
               "section for them on these pages is its own change.",
    ),
    "in/data/app/in-township-officials.json": dict(
        date="2026-10-15",
        reason="Indiana's township trustees and township boards, about a "
               "thousand townships' own governments rather than any county's. "
               "These pages are one per county board; a township is a "
               "different government below the county, and the app names its "
               "trustee and board on its own Township card.",
    ),
    "ca/data/app/sf-supervisor-members.json": dict(
        date="2026-09-13",
        reason="San Francisco's Board of Supervisors is a CITY council that "
               "happens to be called a board of supervisors — the city and the "
               "county are one government. It has no county siblings to index "
               "beside, so these pages have no shape to put it in.",
    ),
}

_NAME_FIELDS = ("name", "chair", "member", "supervisor", "commissioner")
_COUNTY_WORDS = re.compile(r"county-board|county-commission|commissioner|"
                           r"supervisor|county-officer|parish")


def _names_people(obj):
    """Does this record name a person? Any of a handful of fields carrying a
    non-empty string, at any nesting this project's rosters actually use."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _NAME_FIELDS and isinstance(v, str) and v.strip():
                return True
            if isinstance(v, (dict, list)) and _names_people(v):
                return True
    elif isinstance(obj, list):
        return any(_names_people(v) for v in obj)
    return False


def check_registration(read_paths):
    """Find a county officeholder roster nothing here has looked at.

    THE TREE IS CANONICAL, NEVER A TABLE — the same rule
    validate_instance_registration.py discovers instances by, and for the same
    reason: a hand-kept list of rosters would let this gate agree with itself
    about a state nobody registered. So it walks every instance's data/app and
    flags a file whose records mostly name people AND whose shape or filename
    says county, then subtracts what the adapters read and what
    NOT_COUNTY_BOARDS accounts for.

    Two signals, not one, because each alone is wrong. A filename match alone
    flags county-officers files that carry no names. A name match alone flags
    every roster in the fleet, 222 of them, which is a gate nobody would keep.
    """
    problems = []
    read = {os.path.relpath(p, REPO_ROOT) for p in read_paths}
    found = []
    for tag in sorted(d for d in os.listdir(REPO_ROOT)
                      if os.path.isdir(os.path.join(REPO_ROOT, d, "data", "app"))
                      and os.path.exists(os.path.join(REPO_ROOT, d, "index.html"))):
        for path in sorted(glob.glob(os.path.join(app_data(tag), "*.json"))):
            rel = os.path.relpath(path, REPO_ROOT)
            if rel in read:
                continue
            try:
                data = _read(path)
            except (ValueError, OSError):
                continue
            if isinstance(data, dict) and data.get("type") == "FeatureCollection":
                # GEOMETRY, NOT A ROSTER, and it has to be excluded
                # STRUCTURALLY rather than by name: four of these carry a
                # district's representative in the feature properties, so they
                # name real people and a name test alone flags them. A
                # FeatureCollection is boundaries — the thing the county
                # dispatch table reads — and a page cannot be built from it.
                continue
            recs = (list(data.values()) if isinstance(data, dict)
                    else data if isinstance(data, list) else [])
            if not recs:
                continue
            named = sum(1 for r in recs if _names_people(r))
            if named * 2 < len(recs):
                continue
            # LOUISIANA'S COUNTIES ARE PARISHES, and its roster says so: a
            # record carries `parish`, never `county`, and the file is named
            # for parish officials. Without this test and the word in
            # _COUNTY_WORDS the gate let the fleet's first parish roster,
            # la-parish-officials.json, land unseen (2026-10-20).
            county_keyed = sum(1 for r in recs if isinstance(r, dict)
                               and (r.get("county") or r.get("parish") or "").strip())
            if not (county_keyed * 2 >= len(recs)
                    or _COUNTY_WORDS.search(os.path.basename(path))):
                continue
            found.append((rel, len(recs), named))
    for rel, n, named in found:
        if rel in NOT_COUNTY_BOARDS:
            continue
        problems.append(
            "%s names people (%d of %d records) and looks like county "
            "officeholders, and no adapter reads it. Either add one to "
            "INSTANCES/ADAPTERS so its counties get pages, or record it in "
            "NOT_COUNTY_BOARDS with a reason" % (rel, named, n))
    for rel, entry in sorted(NOT_COUNTY_BOARDS.items()):
        if not os.path.exists(os.path.join(REPO_ROOT, rel)):
            problems.append(
                "NOT_COUNTY_BOARDS records %s (%s) and that file is not in the "
                "tree — drop the entry" % (rel, entry["date"]))
        elif rel in read:
            problems.append(
                "NOT_COUNTY_BOARDS records %s (%s) as not a county board and an "
                "adapter now reads it — drop the entry" % (rel, entry["date"]))
    return problems, found


# ——— WHO TO ASK, PER COUNTY ———
#
# The county page names who HOLDS the seats and said nothing about who to ask
# when a reader thinks one of those names is wrong, or wants a ballot. Every
# instance but Michigan already ships that: Illinois and Wisconsin publish a
# county clerk with an office and a telephone, and Iowa's officers file carries
# the board's own line plus the representation plan the county elects under.
#
# IT IS A SEPARATE ADAPTER FROM THE ROSTER, and deliberately: a clerk is not an
# officeholder on this board, and folding the two together would put one in the
# member count. It reads the file the APP already reads for the same county, so
# the page and the card cannot name different clerks.
#
# WHAT IS RENDERED IS WHAT IS PUBLISHED. Illinois's file stores the clerk's name
# and office in capitals — "RYAN A. NIEKAMP", "507 VERMONT STREET QUINCY, IL
# 62301" — and the app's own county card renders them exactly that way.
# Title-casing a person's name here would make this page disagree with the card
# about how the county spells them, which is a decision about somebody's name
# that belongs to the county.
def _norm_county(name):
    """The app's own normCountyName, character for character.

    il/index.html joins the clerk roster to a county polygon with
    `toUpperCase().replace(/\s*COUNTY\s*$/, "").replace(/[^A-Z]/g, "")`, and
    this page must join it the same way or the two can name different clerks for
    one county. That is not a nicety: the Illinois file's keys are
    space-stripped (`JODAVIESS`, `ROCKISLAND`, `STCLAIR`), and Wisconsin's clerk
    file spells two counties differently from its own supervisor roster ("Fond
    du Lac" against "Fond Du Lac", "St. Croix" against "St Croix"). A
    title-case join dropped six real counties' contacts over a spelling.
    """
    return re.sub(r"[^A-Z]", "",
                  re.sub(r"\s*COUNTY\s*$", "", str(name or "").upper()))


def _contact(label, name=None, lines=(), phone=None, email=None, website=None,
             note=None, seats=None):
    lines = [l for l in lines if (l or "").strip()]
    if not (name or lines or phone or email or note):
        return None
    return dict(label=label, name=name, lines=lines, phone=phone, email=email,
                website=website, note=note, seats=seats)


def il_clerk_contact(inst):
    """Illinois: il-county-clerks.json, keyed by the county's name in capitals.

    101 of Illinois's 102 counties. PEORIA is not in the file at all — measured
    2026-09-15, a real absence in the source rather than a join that missed, and
    its page carries no contact rather than an empty one.
    """
    path = os.path.join(app_data("il"), "il-county-clerks.json")
    if not os.path.exists(path):
        return {}, [path]
    by_norm = {_norm_county(n): n for n in IL_NAME_BY_SLUG.values()}
    out = {}
    for key, rec in _read(path).items():
        if not isinstance(rec, dict):
            continue
        county = by_norm.get(_norm_county(key))
        if not county:
            continue
        c = _contact("County Clerk", rec.get("name"), [rec.get("address")],
                     rec.get("phone"), rec.get("email"))
        if c:
            out[_norm_county(county)] = c
    return out, [path]


def wi_clerk_contact(inst):
    """Wisconsin: wi-county-clerks.json, keyed by FIPS and carrying the name."""
    path = os.path.join(app_data("wi"), "wi-county-clerks.json")
    if not os.path.exists(path):
        return {}, [path]
    out = {}
    for rec in _read(path).values():
        if not isinstance(rec, dict) or not (rec.get("county") or "").strip():
            continue
        lines = rec.get("address")
        if isinstance(lines, str):
            lines = [lines]
        c = _contact("County Clerk", rec.get("name"), lines or [],
                     rec.get("phone"), rec.get("email"), rec.get("website"))
        if c:
            out[_norm_county(rec["county"])] = c
    return out, [path]


def ok_county_contact(inst):
    """Oklahoma: the county information line the State Election Board's roster
    prints at the foot of each county's block, carried on every seat record."""
    path = os.path.join(app_data("ok"), "ok-county-commissioners.json")
    if not os.path.exists(path):
        return {}, [path]
    out = {}
    for rec in _read(path).values():
        if not isinstance(rec, dict) or not rec.get("countyPhone"):
            continue
        key = _norm_county(rec["county"])
        if key not in out:
            c = _contact("County information line", None, [], rec["countyPhone"],
                         None, None, None)
            if c:
                out[key] = c
    return out, [path]


def ia_board_contact(inst):
    """Iowa: the BOARD'S own line and the plan it elects under.

    ia-county-officers.json carries no clerk or auditor — measured 2026-09-15,
    `auditor` is null on all 99 — so what this contributes is the board's own
    telephone and its representation plan, which is a fact about how the county
    elects rather than a person. MEASURED 2026-09-22: 91 of 99 records carry a
    boardPhone and 90 a supervisorPlan. This docstring said 90 and 89, each one
    short by one, from the day it was written; Iowa's board session caught both
    while reading the file for the at-large adapter. Two hand-typed counts in a
    docstring are exactly the kind nothing gates, so they are dated here rather
    than restated as current.
    """
    path = os.path.join(app_data("ia"), "ia-county-officers.json")
    if not os.path.exists(path):
        return {}, [path]
    out = {}
    for rec in _read(path).values():
        if not isinstance(rec, dict) or not (rec.get("county") or "").strip():
            continue
        plan, seats = rec.get("supervisorPlan"), rec.get("supervisorSeats")
        note = None
        if plan and seats:
            note = ("The county elects %d supervisors under %s, the "
                    "representation plan it has adopted."
                    % (seats, str(plan).title()))
        c = _contact("Board of Supervisors", None, [], rec.get("boardPhone"),
                     None, None, note, seats=seats)
        if c:
            out[_norm_county(rec["county"])] = c
    return out, [path]


def ms_board_contact(inst):
    """Mississippi: the board's own office, from the same directory page that
    names the supervisors.

    THE DIRECTORY PRINTS AN ADDRESS AND A TELEPHONE BESIDE EACH SUPERVISOR, and
    a line printed for one supervisor may be that person's own, so the builder
    keeps a line only where the directory prints it for at least three of the
    county's five, which makes it the board's office (build_ms_county_officials.py).
    A county where no line passes that test carries no board contact rather
    than one supervisor's. A supervisor's own telephone is on that supervisor's
    row instead (ms_supervisors), and no supervisor's own address is carried
    anywhere."""
    path = os.path.join(app_data("ms"), "ms-county-officials.json")
    if not os.path.exists(path):
        return {}, [path]
    out = {}
    for rec in _read(path).values():
        if not isinstance(rec, dict) or not (rec.get("county") or "").strip():
            continue
        c = _contact("Board of supervisors' office", None,
                     [rec.get("boardAddress")], rec.get("boardPhone"))
        if c:
            out[_norm_county(rec["county"])] = c
    return out, [path]


def la_board_contact(inst):
    """Louisiana: the governing body's own office, from the same list that
    names its members.

    THE LIST PRINTS AN ADDRESS AND A TELEPHONE BESIDE EACH OFFICIAL, and a line
    printed for one official may be that person's own, so the builder keeps an
    address as the body's only where at least three of its officials print it
    and no official outside it does, and a telephone only on the same test
    (build_la_parish_officials.py). A parish where neither passes carries no
    contact rather than one member's."""
    path = os.path.join(app_data("la"), "la-parish-officials.json")
    if not os.path.exists(path):
        return {}, [path]
    out = {}
    for rec in _read(path).values():
        if not isinstance(rec, dict) or not (rec.get("parish") or "").strip():
            continue
        word = LA_KINDS.get(rec.get("kind"), ("governing body",))[0]
        c = _contact("The %s's office" % word, None,
                     [rec.get("boardAddress")], rec.get("boardPhone"))
        if c:
            name = re.sub(r"\s+Parish$", "", rec["parish"].strip())
            out[_norm_county(name)] = c
    return out, [path]


def contact_html(c):
    """One contact block. Nothing is invented: a field the county does not
    publish simply does not render."""
    if not c:
        return ""
    bits = ['<section class="contact">', '<h2>%s</h2>' % esc(c["label"])]
    if c["name"]:
        bits.append('<p class="who">%s</p>' % esc(c["name"]))
    if c["lines"]:
        bits.append('<p class="where">%s</p>'
                    % "<br>".join(esc(l) for l in c["lines"]))
    details = []
    if c["phone"]:
        details.append('<a href="tel:%s">%s</a>'
                       % (esc(dial_digits(c["phone"])), esc(c["phone"])))
    if c["email"]:
        details.append('<a href="mailto:%s">%s</a>'
                       % (esc(c["email"]), esc(c["email"])))
    if c["website"]:
        details.append('<a href="%s" target="_blank" rel="noopener">County website</a>'
                       % esc(c["website"]))
    if details:
        bits.append('<p class="detail">%s</p>' % " &middot; ".join(details))
    if c["note"]:
        bits.append('<p class="detail">%s</p>' % esc(c["note"]))
    bits.append('</section>')
    return "\n".join(bits)


def shell_for_pages():
    """The styling every page shares, read from the files that own it."""
    tokens_css = read(TOKENS, "the design tokens")
    favicon = read(FAVICON, "the brand mark").strip()
    if not favicon.startswith("<svg"):
        fail("favicon.svg does not start with <svg — is it still an SVG?")
    # The font CSS is written for a page at the instance ROOT — `url(fonts/…)`
    # — and these pages sit one level deeper under <tag>/<concept>/, where that
    # resolves to <tag>/<concept>/fonts/ and 404s. Every face, silently, on
    # every page: the app would render in system fonts and nothing would say
    # so. That is the defect Michigan's go-live found the hard way (mi/fonts/
    # did not exist while 18 @font-face rules named it); here
    # scripts/validate_instance_assets.py named all 584 references before the
    # pages shipped, which is the gate doing exactly what it was written for.
    fontface = read(FONTFACE, "the self-hosted font CSS").rstrip("\n")
    depth_fixed = fontface.replace("url(fonts/", "url(../fonts/")
    if depth_fixed == fontface and "url(" in fontface:
        fail("the font CSS no longer writes url(fonts/…), so the ../ hop these "
             "pages need was not applied — check %s"
             % os.path.relpath(FONTFACE, REPO_ROOT))
    return {
        "fontface": depth_fixed,
        "light": token_css(LIGHT_TOKENS, parse_token_block(tokens_css, ":root", TOKENS),
                           ":root"),
        "dark": token_css(DARK_TOKENS,
                          parse_token_block(tokens_css, '[data-theme="dark"]', TOKENS),
                          '[data-theme="dark"]', DARK_EXTRA, indent="    "),
        "favicon": "data:image/svg+xml," + urllib.parse.quote(favicon, safe=""),
        "mark": mark_svg(),
        "byline": shared_footer_byline(),
        # THE COUNTER. These 183 pages carried none until 2026-09-15, so the
        # largest page set on the site — and the one this whole run is about —
        # was absent from the traffic report. Read from its one source rather
        # than written here, the same as the byline above it.
        "goatcounter": shared_goatcounter(),
    }


def load_instance(inst):
    """Every adapter this instance declares, merged. A county that turns up in
    two of them is an error rather than a pick: Illinois's districted and
    at-large rosters are two ways of electing one board, so a county in both
    means one of the two files is wrong about it."""
    counties, problems, nameless, paths, notes = {}, [], set(), [], []
    for key in inst["adapters"]:
        if key not in ADAPTERS:
            fail("instance %s names adapter %r, which ADAPTERS does not carry"
                 % (inst["tag"], key))
        out, probs, none_named, used, note = ADAPTERS[key](inst)
        both = sorted(set(counties) & set(out))
        if both:
            problems.append(
                "%s: %s appear in two of this instance's rosters — one county "
                "cannot elect its board two ways, and a page would have to pick"
                % (inst["tag"], ", ".join(both)))
        counties.update(out)
        problems += probs
        nameless |= none_named
        paths += used
        if note:
            notes.append(note)
    return counties, problems, nameless, paths, notes


def main():
    check = "--check" in sys.argv[1:]
    loaded, problems, all_paths, read_by_instance = {}, [], [], {}
    nameless_keys = set()
    for inst in INSTANCES:
        counties, probs, nameless, paths, notes = load_instance(inst)
        loaded[inst_key(inst)] = (inst, counties, notes)
        problems += probs
        all_paths += paths
        nameless_keys |= {_nobody_key(inst, c) for c in nameless}
        read_by_instance[inst_key(inst)] = {os.path.basename(p) for p in paths}
    problems += check_workflows(read_by_instance)
    problems += check_dial_rule()
    reg_problems, candidates = check_registration(all_paths)
    problems += reg_problems
    for key, rec in sorted(NAMES_NOBODY.items()):
        if key not in nameless_keys:
            problems.append(
                "NAMES_NOBODY records %s (%s) and its roster now names someone, "
                "or has left the tree — drop the entry and let the page "
                "generate: %s" % (key, rec["date"], rec["reason"]))
    if problems:
        for p in problems:
            print("build-county-pages: FAIL — %s" % p, file=sys.stderr)
        raise SystemExit(1)
    for key, rec in sorted(NAMES_NOBODY.items()):
        print("  ~ no page for %s: its roster names nobody (recorded %s) — %s"
              % (key, rec["date"], rec["reason"]))
    for rel, entry in sorted(NOT_COUNTY_BOARDS.items()):
        print("  ~ not a county board: %s (%s) — %s"
              % (rel, entry["date"], entry["reason"]))

    shell = shell_for_pages()
    stale, orphans, totals, wrong = [], [], [], []
    for inst in INSTANCES:
        _i, counties, notes = loaded[inst_key(inst)]
        # WHO TO ASK, from the file the app already reads for the same county.
        # An instance with no source names none — Michigan publishes no county
        # clerk roster, so its pages carry no contact rather than a blank one.
        contacts = {}
        if inst.get("contacts"):
            contacts, _paths = globals()[inst["contacts"]](inst)
            # TWO FILES NOW STATE A SEAT COUNT ON ONE PAGE. Iowa's page says
            # "3 districts and the 3 members who hold them" from the roster and
            # "the county elects 3 supervisors under Plan 3" from the officers
            # file. Measured 2026-09-15 all 17 agree; a page that states both
            # and contradicts itself is worse than one that states neither, so
            # the disagreement fails rather than shipping.
            for n, rec in sorted(counties.items()):
                c = contacts.get(_norm_county(n))
                if not c or not c.get("seats") or rec["at_large"]:
                    continue
                held = sum(len(d["members"]) for d in rec["districts"])
                if c["seats"] != held:
                    # INTO `wrong`, not `problems`: that list is checked before
                    # this loop runs, so an append there would be collected and
                    # never read. The gate's own negative test found it.
                    wrong.append(
                        "%s: the roster seats %d and %s says the county elects "
                        "%d. The page states both and would contradict itself"
                        % (heading_of(inst, n, rec), held, inst["contacts"],
                           c["seats"]))
            missing = sorted(n for n in counties
                             if _norm_county(n) not in contacts)
            print("  %s  %d of %d county page(s) name an office to ask%s"
                  % (inst["tag"], len(counties) - len(missing), len(counties),
                     "" if not missing else
                     "; %d do not (%s%s)"
                     % (len(missing), ", ".join(missing[:4]),
                        ", …" if len(missing) > 4 else "")))
        pages, people, skipped, rows = {}, 0, 0, []
        for name, rec in sorted(counties.items()):
            at_large = rec["at_large"]
            html = build_page(inst, name, rec, at_large, shell,
                              contacts.get(_norm_county(name)))
            pages[rec["slug"]] = html
            wrong += ["%s: %s" % (inst["tag"], w)
                      for w in verify_page(inst, name, rec, at_large, html)]
            if at_large:
                seats = len(rec["members"])
                # Illinois carries neither key and keeps the old meaning: a
                # flat roster there IS a county that elects at large.
                kind = "at-large" if rec.get("claims_at_large", True) else "flat"
                note = rec.get("index_note", ", at large")
            else:
                # District members plus whoever the extras name — the same total
                # the index prints, because two adjacent numbers five apart read
                # as one of them being wrong.
                seats = (sum(len(d["members"]) for d in rec["districts"])
                         + sum(len(ms) for _a, _h, ms in rec.get("extras") or []))
                skipped += len(rec["skipped"])
                kind, note = "districted", ""
            people += seats
            rows.append((name, rec["slug"], seats, note, kind))
        rows.sort()
        totals.append((inst, pages, people, skipped, rows, notes))

    if wrong:
        for w in wrong:
            print("build-county-pages: FAIL — %s" % w, file=sys.stderr)
        raise SystemExit(1)

    for inst, pages, _people, _skipped, _rows, _notes in totals:
        d = out_dir(inst)
        os.makedirs(d, exist_ok=True)
        existing = {os.path.basename(p)[:-len(".html")]
                    for p in glob.glob(os.path.join(d, "*.html"))}
        gone = sorted(existing - set(pages))
        orphans += ["%s/%s.html" % (inst["concept"], o) for o in gone]
        for slug, html in sorted(pages.items()):
            out = os.path.join(d, slug + ".html")
            current = ""
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    current = f.read()
            if check:
                if current != html:
                    stale.append(os.path.relpath(out, REPO_ROOT))
            elif current != html:
                with open(out, "w", encoding="utf-8") as f:
                    f.write(html)
        if not check:
            for o in gone:
                os.remove(os.path.join(d, o + ".html"))

    index_stale = []
    for inst, _pages, _people, _skipped, rows, _notes in totals:
        if write_index(inst, rows, check) and check:
            index_stale.append("%s's %r region"
                               % (os.path.relpath(index_page(inst), REPO_ROOT),
                                  INDEX_REGION))

    if check and (stale or orphans or index_stale):
        if stale:
            print("build-county-pages: FAIL — %d page(s) stale, starting with %s. "
                  "Run `python3 scripts/build_county_pages.py`."
                  % (len(stale), ", ".join(stale[:4])), file=sys.stderr)
        for o in orphans:
            print("build-county-pages: FAIL — %s has no roster behind it any "
                  "more; delete it" % o, file=sys.stderr)
        for i in index_stale:
            print("build-county-pages: FAIL — %s is stale. Run `python3 "
                  "scripts/build_county_pages.py`." % i, file=sys.stderr)
        raise SystemExit(1)

    for inst, pages, people, skipped, rows, notes in totals:
        districted = sum(1 for r in rows if r[4] == "districted")
        at_large = sum(1 for r in rows if r[4] == "at-large")
        flat = len(rows) - districted - at_large
        print("  %s  %3d page(s) %s, %4d people named and each one verified onto "
              "its page (%d districted, %d at large%s%s)%s"
              % (inst["tag"], len(pages), "current" if check else "written",
                 people, districted, at_large,
                 ", %d named without districts" % flat if flat else "",
                 ", %d non-district key(s) skipped" % skipped if skipped else "",
                 "; " + "; ".join(notes) if notes else ""))
    print("build-county-pages: OK — %d page(s) across %d instance(s), %d people "
          "named, %d candidate roster(s) classified%s"
          % (sum(len(t[1]) for t in totals), len(totals),
             sum(t[2] for t in totals), len(candidates) + len(all_paths),
             "; removed %d orphan(s)" % len(orphans) if orphans and not check else ""))


if __name__ == "__main__":
    main()
