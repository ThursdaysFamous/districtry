#!/usr/bin/env python3
"""
The legislator pages: twelve generated pages naming 1,058 officeholders.

WHY. Every one of the six apps already carries its state's two legislative
chambers and its U.S. House districts, with a named member on each card — 1,058
people across eighteen shipped rosters. Measured 2026-09-15, not one of them
appeared in any served byte of this site, and the site had no page at all for
"who is my state representative" or "who is my congressman", which search
results split by state and by office. build_county_pages.py closed that for
county seats and build_officeholder_tables.py for three city councils; this is
the same absence one tier up.

TWO PAGES PER INSTANCE, NOT THREE. The state's two chambers share one page
because a reader asking "who is my state legislator" wants both halves of the
answer and they are elected from different maps over the same ground; the U.S.
House gets its own because it is a different government. A page per chamber
would have split 177 Illinois names across two pages that each answer half a
question.

WHAT IS GENERATED AND WHAT IS PRESERVED. This script owns the page: its head,
its prose, its links, its structure. It does NOT own the four blocks other
generators fill, and it splices them back from the file on disk on every run —
the two ENGINE fences compose_app.py writes, the address box
build_question_forms.py writes, and the officeholder tables
build_officeholder_tables.py writes. A page created by this script carries those
markers EMPTY; the other generators fill them on their own next run, and this
script never clobbers what they wrote. That makes the four `--check`s
order-independent.

NOTHING HERE STATES A SEAT COUNT. "Illinois has 118 House districts" is the kind
of sentence that goes stale in a reapportionment and is never re-read; every
count on these pages is `len(roster)` at build time. What IS stated is the
layer id each page's map link opens, and it is stated because it cannot be
derived — so it is checked against the instance's own worksheet, and a page
naming a layer its app does not register fails the build.

    python3 scripts/build_legislator_pages.py           # write the pages
    python3 scripts/build_legislator_pages.py --check   # drift gate for CI
"""

import argparse
import difflib
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from question_page import (METROS, PageError, check_layer, head, load,  # noqa: E402
                           MARK_RE, preserved_from_disk, shared_head_block,
                           shell, THEMEBOOT_RE)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Per instance: the worksheet, and the two pages' wording. `layer` is the id the
# page's map link switches on and is VERIFIED against the worksheet's layers[].
# `chambers` is upper house first, because that is the order both a ballot and
# every one of these states' own legislature websites use.
INSTANCES = {
    "il": dict(
        worksheet="metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Illinois state legislator?",
            body="the Illinois General Assembly",
            short="Illinois General Assembly",
            term="Senators serve staggered two- and four-year terms and "
                 "representatives two-year terms.",
            chambers=[
                dict(layer="il-senate", name="Illinois Senate", short="Senate",
                     holder="Senator", roster="il-senate-members.json"),
                dict(layer="il-house", name="Illinois House of Representatives", short="House",
                     holder="Representative", roster="il-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="congress", roster="congress-roster.json",
            state="Illinois"),
    ),
    "ny": dict(
        worksheet="ny/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my NY state legislator?",
            body="the New York State Legislature",
            short="New York State Legislature",
            term="Both chambers run on two-year terms.",
            chambers=[
                dict(layer="state-senate", name="New York State Senate", short="Senate",
                     holder="Senator", roster="ny-senate-members.json"),
                dict(layer="state-assembly", name="New York State Assembly", short="Assembly",
                     holder="Assembly Member", roster="ny-assembly-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="congress", roster="congress-roster.json",
            state="New York"),
    ),
    "ca": dict(
        worksheet="ca/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my CA state legislator?",
            body="the California State Legislature",
            short="California State Legislature",
            term="Senators serve four-year terms and Assembly members two.",
            chambers=[
                dict(layer="ca-senate", name="California State Senate", short="Senate",
                     holder="Senator", roster="ca-senate-members.json"),
                dict(layer="ca-assembly", name="California State Assembly", short="Assembly",
                     holder="Assembly Member", roster="ca-assembly-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="congress", roster="congress-roster.json",
            state="California"),
    ),
    "wi": dict(
        worksheet="wi/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Wisconsin legislator?",
            body="the Wisconsin Legislature",
            short="Wisconsin Legislature",
            term="Senators serve four-year terms and Assembly members two.",
            chambers=[
                dict(layer="wi-senate", name="Wisconsin State Senate", short="Senate",
                     holder="Senator", roster="wi-senate-members.json"),
                dict(layer="wi-assembly", name="Wisconsin State Assembly", short="Assembly",
                     holder="Representative", roster="wi-assembly-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Wisconsin"),
    ),
    "ia": dict(
        worksheet="ia/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Iowa legislator?",
            body="the Iowa General Assembly",
            short="Iowa General Assembly",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="ia-senate", name="Iowa Senate", short="Senate",
                     holder="Senator", roster="ia-senate-members.json"),
                dict(layer="ia-house", name="Iowa House of Representatives", short="House",
                     holder="Representative", roster="ia-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Iowa"),
    ),
    "mi": dict(
        worksheet="mi/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Michigan legislator?",
            body="the Michigan Legislature",
            short="Michigan Legislature",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="mi-senate", name="Michigan Senate", short="Senate",
                     holder="Senator", roster="mi-senate-members.json"),
                dict(layer="mi-house", name="Michigan House of Representatives", short="House",
                     holder="Representative", roster="mi-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Michigan"),
    ),
    # CONGRESS ONLY. Minnesota's two chambers name nobody, so it is in
    # NO_LEGISLATURE_PAGE below and this entry deliberately carries no
    # `legislature` key. The U.S. House roster is real — 8 members, each with a
    # district office, refreshed weekly — so that page ships exactly as the
    # siblings' do.
    "mn": dict(
        worksheet="mn/metro-worksheet.json",
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Minnesota"),
    ),
    # CONGRESS ONLY, the same shape and the same reason as Minnesota above:
    # Kentucky's two chambers name nobody, so it is in NO_LEGISLATURE_PAGE and
    # carries no `legislature` key. Its U.S. House roster is real — 6 members,
    # each with a district office, refreshed weekly — so that page ships as the
    # siblings' do.
    "ky": dict(
        worksheet="ky/metro-worksheet.json",
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Kentucky"),
    ),
    # CONGRESS ONLY, the third instance of the Minnesota shape: Indiana's two
    # chambers name nobody, so it is in NO_LEGISLATURE_PAGE and carries no
    # `legislature` key. Its U.S. House roster is real — 9 members, refreshed
    # weekly — so that page ships as the siblings' do.
    "in": dict(
        worksheet="in/metro-worksheet.json",
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Indiana"),
    ),
    # North Carolina joined at its 2026-10-09 go-live with BOTH chambers named,
    # the Wisconsin/Iowa/Michigan shape rather than Minnesota's: all 170
    # legislators ship from Open States, enriched from the General Assembly's
    # own member lists, and refreshed weekly. NC Const. art. II, secs. 2 and 4
    # set both chambers' terms at two years, so the term sentence differs from
    # every sibling's on purpose.
    "nc": dict(
        worksheet="nc/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my NC legislator?",
            body="the North Carolina General Assembly",
            short="North Carolina General Assembly",
            term="Senators and representatives both serve two-year terms.",
            chambers=[
                dict(layer="nc-senate", name="North Carolina Senate", short="Senate",
                     holder="Senator", roster="nc-senate-members.json"),
                dict(layer="nc-house", name="North Carolina House of Representatives", short="House",
                     holder="Representative", roster="nc-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="North Carolina"),
    ),
    # Oklahoma joined at its go-live with both chambers named from Open
    # States (one seat in each currently unlisted, which the table prints as
    # "Not listed"). Okla. Const. art. V, sec. 9 sets senators' terms at four
    # years and representatives' at two.
    "ok": dict(
        worksheet="ok/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Oklahoma legislator?",
            body="the Oklahoma Legislature",
            short="Oklahoma Legislature",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="ok-senate", name="Oklahoma Senate", short="Senate",
                     holder="Senator", roster="ok-senate-members.json"),
                dict(layer="ok-house", name="Oklahoma House of Representatives", short="House",
                     holder="Representative", roster="ok-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Oklahoma"),
    ),
    # South Carolina joined at its go-live with both chambers named from the
    # General Assembly's own member pages (46 of 46 and 124 of 124 on
    # 2026-10-10). S.C. Const. art. III, secs. 2 and 6 set representatives'
    # terms at two years and senators' at four.
    "sc": dict(
        worksheet="sc/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my SC legislator?",
            body="the South Carolina General Assembly",
            short="South Carolina General Assembly",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="sc-senate", name="South Carolina Senate", short="Senate",
                     holder="Senator", roster="sc-senate-members.json"),
                dict(layer="sc-house", name="South Carolina House of Representatives", short="House",
                     holder="Representative", roster="sc-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="South Carolina"),
    ),
    # Tennessee joined at its go-live with both chambers named from the
    # Legislature's own map on TNMap (a seat the map lists as vacant prints as
    # a vacancy). Tenn. Const. art. II, sec. 3 sets senators' terms at four
    # years and representatives' at two.
    "tn": dict(
        worksheet="tn/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Tennessee legislator?",
            body="the Tennessee General Assembly",
            short="Tennessee General Assembly",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="tn-senate", name="Tennessee Senate", short="Senate",
                     holder="Senator", roster="tn-senate-members.json"),
                dict(layer="tn-house", name="Tennessee House of Representatives", short="House",
                     holder="Representative", roster="tn-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Tennessee"),
    ),
    # Arkansas joined at its go-live with both chambers named from the
    # Legislature's own member list and every member's own page (a seat whose
    # only row is a departed member prints as a vacancy). Ark. Const. art. 5,
    # secs. 3 and 4 set representatives' terms at two years and senators' at
    # four.
    "ar": dict(
        worksheet="ar/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Arkansas legislator?",
            body="the Arkansas General Assembly",
            short="Arkansas General Assembly",
            term="Senators serve four-year terms and representatives two.",
            chambers=[
                dict(layer="ar-senate", name="Arkansas Senate", short="Senate",
                     holder="Senator", roster="ar-senate-members.json"),
                dict(layer="ar-house", name="Arkansas House of Representatives", short="House",
                     holder="Representative", roster="ar-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Arkansas"),
    ),
    # Mississippi joined at its go-live with both chambers named from the
    # Legislature's own member gallery and every member's profile (three seats
    # the gallery shows as vacant print as vacancies). No term length is
    # stated: the sentence is the Secretary of State's own 2026-2027 election
    # calendar, which lists both chambers among the offices elected on
    # November 2, 2027.
    "ms": dict(
        worksheet="ms/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Mississippi legislator?",
            body="the Mississippi Legislature",
            short="Mississippi Legislature",
            term="The Secretary of State's election calendar lists state "
                 "senators and state representatives among the offices elected "
                 "at the general election of November 2, 2027.",
            chambers=[
                dict(layer="ms-senate", name="Mississippi Senate", short="Senate",
                     holder="Senator", roster="ms-senate-members.json"),
                dict(layer="ms-house", name="Mississippi House of Representatives", short="House",
                     holder="Representative", roster="ms-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Mississippi"),
    ),
    # Louisiana joined at its go-live with both chambers named from each
    # chamber's own member list and every member's own page (the seats either
    # list prints as vacant print as vacancies: Senate 14 and House 77 and 92
    # on 2026-10-20). La. Const. art. III, sec. 4(C), as the Senate's own copy
    # prints it (read 2026-10-21): "A member of the legislature shall be
    # elected for a four-year term."
    "la": dict(
        worksheet="la/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Louisiana legislator?",
            body="the Louisiana Legislature",
            short="Louisiana Legislature",
            term="Senators and representatives both serve four-year terms.",
            chambers=[
                dict(layer="la-senate", name="Louisiana Senate", short="Senate",
                     holder="Senator", roster="la-senate-members.json"),
                dict(layer="la-house", name="Louisiana House of Representatives", short="House",
                     holder="Representative", roster="la-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Louisiana"),
    ),
    # Missouri joined at its go-live with both chambers named from each
    # chamber's own member list (the seats either list prints as vacant print
    # as vacancies: Senate 10 and House 29, 95, 99, 110, 114, 149, 159 and 160
    # on 2026-10-26). Mo. Const. art. III, sec. 11, as the Revisor of Statutes
    # prints it (read 2026-10-26), elects "the whole number of
    # representatives" at every general election and each class of senators
    # every other one, so representatives serve two years and senators four.
    "mo": dict(
        worksheet="mo/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Missouri legislator?",
            body="the Missouri General Assembly",
            short="Missouri General Assembly",
            term="Senators serve four-year terms and representatives two-year terms.",
            chambers=[
                dict(layer="mo-senate", name="Missouri Senate", short="Senate",
                     holder="Senator", roster="mo-senate-members.json"),
                dict(layer="mo-house", name="Missouri House of Representatives", short="House",
                     holder="Representative", roster="mo-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Missouri"),
    ),
    # Virginia joined at its go-live with both chambers named from each
    # chamber's own member list (the House of Delegates' list prints District
    # 20 as vacant, so that seat prints as a vacancy, on 2026-10-29). Va.
    # Const. art. IV, secs. 2 and 3, as the Legislative Information System
    # prints them (read 2026-10-30), elect senators "quadrennially" and
    # delegates "biennially".
    "va": dict(
        worksheet="va/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Virginia legislator?",
            body="the Virginia General Assembly",
            short="Virginia General Assembly",
            term="Senators serve four-year terms and delegates two-year terms.",
            chambers=[
                dict(layer="va-senate", name="Senate of Virginia", short="Senate",
                     holder="Senator", roster="va-senate-members.json"),
                dict(layer="va-house", name="Virginia House of Delegates", short="House of Delegates",
                     holder="Delegate", roster="va-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Virginia"),
    ),
    # West Virginia joined at its go-live with both chambers named from each
    # chamber's own roster page on wvlegislature.gov. ITS SENATE SEATS TWO
    # SENATORS PER DISTRICT, so its roster record is {"seats": 2, "members":
    # [...]} rather than one member, and `adapter` tells the officeholder table
    # to print a row per senator (build_officeholder_tables.multi_member_districts).
    # The terms are W. Va. Const. art. VI, secs. 3 and 4 (four years for
    # senators, half elected every two years, two per district; two years for
    # delegates), not re-read for this change: the Legislature's robots.txt
    # disallows its /WVCODE/ path, where the constitution is printed.
    "wv": dict(
        worksheet="wv/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my WV legislator?",
            body="the West Virginia Legislature",
            short="West Virginia Legislature",
            term="Each Senate district elects two senators to staggered four-year terms, "
                 "and delegates serve two-year terms.",
            chambers=[
                dict(layer="wv-senate", name="West Virginia Senate", short="Senate",
                     holder="Senator", roster="wv-senate-members.json",
                     adapter="multi_member_districts"),
                dict(layer="wv-house", name="West Virginia House of Delegates",
                     short="House of Delegates",
                     holder="Delegate", roster="wv-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="West Virginia"),
    ),
    # Georgia joined at its go-live with both chambers named from the General
    # Assembly's own member data, read through the token its page hands every
    # visitor (every one of the 56 senators and 180 representatives named on
    # 2026-10-29). The term sentence is measured rather than quoted: the
    # Secretary of State's results (results.sos.ga.gov, read 2026-11-10) list
    # all 56 Senate and all 180 House seats on the general election ballots of
    # November 2022, November 2024 and November 2026.
    "ga": dict(
        worksheet="ga/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Georgia legislator?",
            body="the Georgia General Assembly",
            short="Georgia General Assembly",
            term="Senators and representatives both serve two-year terms: the "
                 "Secretary of State's results list every Senate and House seat "
                 "on the general election ballots of 2022, 2024 and 2026.",
            chambers=[
                dict(layer="ga-senate", name="Georgia State Senate", short="Senate",
                     holder="Senator", roster="ga-senate-members.json"),
                dict(layer="ga-house", name="Georgia House of Representatives", short="House",
                     holder="Representative", roster="ga-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Georgia"),
    ),
    # BATCH 1 OF THE STATE-LEVEL LAUNCH (Pennsylvania, Nevada, Arizona, New
    # Jersey, New Hampshire) joined in one go-live change. Each chamber is named
    # from the legislature's own member pages, with Open States as the fallback
    # (Adam's choice of 2026-11-10); New Hampshire's first roster came from
    # Open States, because gc.nh.gov gave the build sandbox empty replies. The
    # term sentences are each state constitution's, not re-read for this change:
    # Pa. Const. art. II, sec. 3; Nev. Const. art. 4, secs. 3 and 4; Ariz.
    # Const. art. 4, pt. 2, sec. 21; N.J. Const. art. IV, sec. II, para. 1 (the
    # 2-4-4 cycle); N.H. Const. pt. II, arts. 3 and 25.
    "pa": dict(
        worksheet="pa/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Pennsylvania legislator?",
            body="the Pennsylvania General Assembly",
            short="Pennsylvania General Assembly",
            term="Senators serve four-year terms and representatives two-year terms.",
            chambers=[
                dict(layer="pa-senate", name="Pennsylvania State Senate", short="Senate",
                     holder="Senator", roster="pa-senate-members.json"),
                dict(layer="pa-house", name="Pennsylvania House of Representatives",
                     short="House", holder="Representative", roster="pa-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Pennsylvania"),
    ),
    "nv": dict(
        worksheet="nv/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Nevada legislator?",
            body="the Nevada Legislature",
            short="Nevada Legislature",
            term="Senators serve four-year terms and Assembly members two-year terms.",
            chambers=[
                dict(layer="nv-senate", name="Nevada Senate", short="Senate",
                     holder="Senator", roster="nv-senate-members.json"),
                dict(layer="nv-assembly", name="Nevada Assembly", short="Assembly",
                     holder="Assembly member", roster="nv-assembly-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Nevada"),
    ),
    # ARIZONA AND NEW JERSEY ELECT BOTH CHAMBERS FROM ONE MAP: each district
    # elects one senator and two members of the lower house, so the lower
    # house's roster record is {"seats": 2, "members": [...]} and `shared_map`
    # holds the two rosters to the same districts. The default wording ("Both
    # are drawn over the same ground", "Two chambers, two maps") would be false
    # of them, and New Jersey's districts are built largely from whole
    # municipalities, so "follows no city boundary" is not claimed either.
    "az": dict(
        worksheet="az/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Arizona legislator?",
            body="the Arizona Legislature",
            short="Arizona Legislature",
            term="Senators and representatives both serve two-year terms.",
            shared_map=True,
            wording=dict(
                strong="The {body} is elected from {districts} districts.",
                ground="Each district elects one senator and two representatives, so one "
                       "district number answers for both chambers. A district can cross "
                       "county lines and split a ZIP code, so the only way to know which "
                       "one covers an address is to put the address on the map.",
                shows="Select any point and the two cards name its <strong>district number</strong>, the\n"
                      "        <strong>senator</strong> and the two <strong>representatives</strong> it elects, with their\n"
                      "        party, their offices and a link to their own page on the Legislature's site.",
                maps_heading="One map, three members",
                maps="An address has one legislative district, and it answers for both chambers: its\n"
                     "      senator and its two representatives each represent every point in it. The tables below list\n"
                     "      both chambers in full, so a reader who knows their district number can look up all three\n"
                     "      members without opening the map at all.",
                desc="Your Arizona legislative district by address or ZIP \u2014 the district "
                     "number and the senator and two representatives it elects."),
            chambers=[
                dict(layer="az-senate", name="Arizona State Senate", short="Senate",
                     holder="Senator", roster="az-senate-members.json"),
                dict(layer="az-house", name="Arizona House of Representatives", short="House",
                     holder="Representative", roster="az-house-members.json",
                     adapter="multi_member_districts"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Arizona"),
    ),
    "nj": dict(
        worksheet="nj/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my New Jersey legislator?",
            body="the New Jersey Legislature",
            short="New Jersey Legislature",
            term="Senators serve four-year terms, except the first term after each "
                 "census, which is two years; Assembly members serve two-year terms.",
            shared_map=True,
            wording=dict(
                strong="The {body} is elected from {districts} districts.",
                ground="Each district elects one senator and two Assembly members, so one "
                       "district number answers for both houses. A district can cross "
                       "county lines and split a ZIP code, so the only way to know which "
                       "one covers an address is to put the address on the map.",
                shows="Select any point and the two cards name its <strong>district number</strong>, the\n"
                      "        <strong>senator</strong> and the two <strong>Assembly members</strong> it elects, with their\n"
                      "        party, their offices and a link to their own page on the Legislature's site.",
                maps_heading="One map, three members",
                maps="An address has one legislative district, and it answers for both houses: its\n"
                     "      senator and its two Assembly members each represent every point in it. The tables below\n"
                     "      list both houses in full, so a reader who knows their district number can look up all\n"
                     "      three members without opening the map at all.",
                desc="Your New Jersey legislative district by address or ZIP \u2014 the district "
                     "number and the senator and two Assembly members it elects."),
            chambers=[
                dict(layer="nj-senate", name="New Jersey Senate", short="Senate",
                     holder="Senator", roster="nj-senate-members.json"),
                dict(layer="nj-assembly", name="New Jersey General Assembly", short="Assembly",
                     holder="Assembly member", roster="nj-assembly-members.json",
                     adapter="multi_member_districts"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="New Jersey"),
    ),
    # NEW HAMPSHIRE'S HOUSE IS NAMED, MULTI-MEMBER AND FLOTERIAL: a district is
    # a county and a number ("Merrimack 18") electing one to ten
    # representatives, and a floterial district is drawn over two or more of
    # the others, so an address can have two House districts at once. The
    # table names each floterial with the districts it is drawn over
    # (build_officeholder_tables.nh_house_districts, read from the shipped
    # boundary file). "NH" in the title because "New Hampshire" takes the
    # <title> to 62 characters, over validate_serp_lengths.py's 60.
    "nh": dict(
        worksheet="nh/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my NH legislator?",
            body="the New Hampshire General Court",
            short="New Hampshire General Court",
            term="Senators and representatives both serve two-year terms.",
            wording=dict(
                ground="The two chambers are drawn separately and a House district can elect "
                       "several representatives, so the only way to know which districts and "
                       "members cover an address is to put the address on the map.",
                shows="Select any point and the two cards name its <strong>Senate district</strong> and\n"
                      "        <strong>senator</strong>, and its <strong>House district</strong> with every\n"
                      "        <strong>representative</strong> it elects, including the floterial district drawn over it\n"
                      "        where there is one.",
                maps_heading="Two chambers, and floterial districts",
                maps="An address has one Senate district and one or two House districts. Each House district is\n"
                     "      named for a county and numbered within it. Most of them cover the state between them;\n"
                     "      the rest are <strong>floterial</strong> districts, each drawn over two or more of those and\n"
                     "      electing more representatives from all of them together, so a reader in a district that\n"
                     "      belongs to a floterial is represented by the members of both. The tables below list every\n"
                     "      district in full, each floterial with the districts it is drawn over, so a reader who\n"
                     "      knows their district can look up the members without opening the map at all.",
                desc="Your New Hampshire Senate and House districts by address or ZIP \u2014 "
                     "the senator, and every representative your House districts elect."),
            chambers=[
                dict(layer="nh-senate", name="New Hampshire Senate", short="Senate",
                     holder="Senator", roster="nh-senate-members.json"),
                dict(layer="nh-house", name="New Hampshire House of Representatives",
                     short="House", holder="Representative", roster="nh-house-members.json",
                     adapter="nh_house_districts"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="New Hampshire"),
    ),
    # BATCH 2 OF THE STATE-LEVEL LAUNCH (Texas, Florida, Ohio, Washington)
    # joined in one go-live change, each chamber named from the legislature's
    # own member pages. The default "neither follows a city, county or ZIP
    # boundary" is not claimed for any of them: Texas House districts are built
    # from whole counties where the population allows, Florida's constitution
    # asks districts to follow political and geographic lines where feasible,
    # and Ohio's to keep counties and cities whole where it can. The term
    # sentences are each state constitution's, not re-read for this change:
    # Tex. Const. art. III, secs. 3 and 4 (after each new map the senators draw
    # lots, and half serve two years); Fla. Const. art. III, sec. 15 (some
    # senators elected after a new map serve two years, to keep the terms
    # staggered); Ohio Const. art. II, sec. 2; Wash. Const. art. II, secs. 4
    # and 6.
    "tx": dict(
        worksheet="tx/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Texas legislator?",
            body="the Texas Legislature",
            short="Texas Legislature",
            term="Senators serve four-year terms, except that some serve two years after "
                 "each new map so their terms stay staggered; representatives serve "
                 "two-year terms.",
            wording=dict(
                ground="Both are drawn over the same ground and a district can split a "
                       "county, a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map."),
            chambers=[
                dict(layer="tx-senate", name="Texas Senate", short="Senate",
                     holder="Senator", roster="tx-senate-members.json"),
                dict(layer="tx-house", name="Texas House of Representatives",
                     short="House", holder="Representative", roster="tx-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Texas"),
    ),
    "fl": dict(
        worksheet="fl/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Florida legislator?",
            body="the Florida Legislature",
            short="Florida Legislature",
            term="Senators serve four-year terms, except that some serve two years after "
                 "each new map so their terms stay staggered; representatives serve "
                 "two-year terms.",
            wording=dict(
                ground="Both are drawn over the same ground and a district can split a "
                       "county, a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map."),
            chambers=[
                dict(layer="fl-senate", name="Florida Senate", short="Senate",
                     holder="Senator", roster="fl-senate-members.json"),
                dict(layer="fl-house", name="Florida House of Representatives",
                     short="House", holder="Representative", roster="fl-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Florida"),
    ),
    # OHIO'S SENATE IS BUILT FROM ITS HOUSE: each Senate district is three
    # whole House districts (Ohio Const. art. XI, sec. 4), which
    # oh/scripts/build_legislative_boundaries.py --check holds on the shipped
    # files, so the default "the two rarely share a boundary" would be false.
    "oh": dict(
        worksheet="oh/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Ohio legislator?",
            body="the Ohio General Assembly",
            short="Ohio General Assembly",
            term="Senators serve four-year terms and representatives two-year terms.",
            wording=dict(
                ground="Each Senate district is made of three whole House districts, and a "
                       "district can split a county, a city or a ZIP code, so the only way "
                       "to know which pair covers an address is to put the address on the "
                       "map.",
                maps_heading="Three House districts to a Senate district",
                maps="An address has one district in each chamber, and because every Senate\n"
                     "      district is three whole House districts, the House district decides the Senate\n"
                     "      one. The tables below list both chambers in full, so a reader who knows their\n"
                     "      district numbers can look up the members without opening the map at all."),
            chambers=[
                dict(layer="oh-senate", name="Ohio Senate", short="Senate",
                     holder="Senator", roster="oh-senate-members.json"),
                dict(layer="oh-house", name="Ohio House of Representatives",
                     short="House", holder="Representative", roster="oh-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Ohio"),
    ),
    # WASHINGTON ELECTS BOTH CHAMBERS FROM ONE MAP, like Arizona: each of its
    # 49 districts elects one senator and two representatives (Positions 1
    # and 2), so the House roster record is {"seats": 2, "members": [...]}.
    "wa": dict(
        worksheet="wa/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Washington legislator?",
            body="the Washington State Legislature",
            short="Washington State Legislature",
            term="Senators serve four-year terms and representatives two-year terms.",
            shared_map=True,
            wording=dict(
                strong="The {body} is elected from {districts} districts.",
                ground="Each district elects one senator and two representatives, so one "
                       "district number answers for both chambers. A district can cross "
                       "county lines and split a ZIP code, so the only way to know which "
                       "one covers an address is to put the address on the map.",
                shows="Select any point and the two cards name its <strong>district number</strong>, the\n"
                      "        <strong>senator</strong> and the two <strong>representatives</strong> it elects, with their\n"
                      "        party, their offices and a link to their own page on the Legislature's site.",
                maps_heading="One map, three members",
                maps="An address has one legislative district, and it answers for both chambers: its\n"
                     "      senator and its two representatives each represent every point in it. The tables below list\n"
                     "      both chambers in full, so a reader who knows their district number can look up all three\n"
                     "      members without opening the map at all.",
                desc="Your Washington legislative district by address or ZIP \u2014 the district "
                     "number and the senator and two representatives it elects."),
            chambers=[
                dict(layer="wa-senate", name="Washington State Senate", short="Senate",
                     holder="Senator", roster="wa-senate-members.json"),
                dict(layer="wa-house", name="Washington House of Representatives", short="House",
                     holder="Representative", roster="wa-house-members.json",
                     adapter="multi_member_districts"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Washington"),
    ),
    # BATCH 3 OF THE STATE-LEVEL LAUNCH (Massachusetts, Colorado, Maryland,
    # Alabama, Oregon, Connecticut, Utah, Kansas) joined in one go-live change,
    # each chamber named from the legislature's own published member list
    # (Adam's choice of 2026-11-10). The term sentences are each state
    # constitution's, not re-read for this change: Mass. Const. amend. art.
    # LXXXII (two years, both chambers); Colo. Const. art. V, sec. 3; Md.
    # Const. art. III, sec. 6 (four years, both chambers); Ala. Const. art. IV
    # (four years, both chambers); Or. Const. art. IV, sec. 4; Conn. Const.
    # art. III, secs. 3 and 4 (two years, both chambers); Utah Const. art. VI,
    # sec. 3; Kan. Const. art. 2, sec. 2.
    #
    # MASSACHUSETTS NAMES ITS DISTRICTS FOR THE COUNTIES THEY LIE IN rather than
    # numbering them ("Third Suffolk", "10th Bristol"), so the default words
    # about a district NUMBER would be false and the table prints each name
    # (build_officeholder_tables.named_districts). "MA" in the title because
    # "Massachusetts" takes the <title> to 62 characters, over
    # validate_serp_lengths.py's 60.
    "ma": dict(
        worksheet="ma/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my MA legislator?",
            body="the Massachusetts General Court",
            short="Massachusetts General Court",
            term="Senators and representatives both serve two-year terms.",
            wording=dict(
                ground="Each district is named for the counties it lies in rather than "
                       "numbered, both are drawn over the same ground, and a district can "
                       "split a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map.",
                shows="Select any point and the two cards name the <strong>district</strong> for each\n"
                      "        chamber and the <strong>member</strong> who holds that seat, with their party, their\n"
                      "        offices and a link to their own page on the Legislature's site.",
                maps="An address has one district in each chamber and the two rarely share a boundary: the\n"
                     "      chambers are apportioned separately. The tables below list both in full, so a reader\n"
                     "      who knows their district's name can look up the member without opening the map at all.",
                desc="Your Massachusetts General Court districts by address or ZIP \u2014 the "
                     "district in each chamber and the member who holds it."),
            chambers=[
                dict(layer="ma-senate", name="Massachusetts Senate", short="Senate",
                     holder="Senator", roster="ma-senate-members.json",
                     adapter="named_districts"),
                dict(layer="ma-house", name="Massachusetts House of Representatives",
                     short="House", holder="Representative", roster="ma-house-members.json",
                     adapter="named_districts"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Massachusetts"),
    ),
    "co": dict(
        worksheet="co/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Colorado legislator?",
            body="the Colorado General Assembly",
            short="Colorado General Assembly",
            term="Senators serve four-year terms and representatives two-year terms.",
            wording=dict(
                ground="Both are drawn over the same ground and a district can split a "
                       "county, a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map."),
            chambers=[
                dict(layer="co-senate", name="Colorado Senate", short="Senate",
                     holder="Senator", roster="co-senate-members.json"),
                dict(layer="co-house", name="Colorado House of Representatives",
                     short="House", holder="Representative", roster="co-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Colorado"),
    ),
    # MARYLAND ELECTS THREE DELEGATES FROM EACH OF ITS 47 SENATE DISTRICTS,
    # at large or from two or three subdistricts drawn inside it (1A, 1B, 1C),
    # so its House roster record is {"seats": n, "members": [...]} and each
    # House district lies inside one Senate district, which
    # md/scripts/build_legislative_boundaries.py --check holds on the shipped
    # files.
    "md": dict(
        worksheet="md/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Maryland legislator?",
            body="the Maryland General Assembly",
            short="Maryland General Assembly",
            term="Senators and delegates both serve four-year terms.",
            wording=dict(
                ground="Each Senate district elects three delegates, either all together or "
                       "from two or three subdistricts drawn inside it, and a district can "
                       "split a county, a city or a ZIP code, so the only way to know which "
                       "pair covers an address is to put the address on the map.",
                shows="Select any point and the two cards name the <strong>district</strong> for each\n"
                      "        chamber and the <strong>senator</strong> and <strong>delegates</strong> who hold its seats,\n"
                      "        with their party, their offices and a link to their own page on the General Assembly's site.",
                maps_heading="Three delegates to a Senate district",
                maps="An address has one district in each chamber, and because every House of Delegates\n"
                     "      district is a Senate district or a subdistrict drawn inside one, the House district decides\n"
                     "      the Senate one. The tables below list both chambers in full, so a reader who knows their\n"
                     "      district can look up the members without opening the map at all.",
                desc="Your Maryland General Assembly districts by address or ZIP \u2014 the "
                     "district in each chamber and the senator and delegates who hold it."),
            chambers=[
                dict(layer="md-senate", name="Maryland Senate", short="Senate",
                     holder="Senator", roster="md-senate-members.json"),
                dict(layer="md-house", name="Maryland House of Delegates",
                     short="House of Delegates", holder="Delegate",
                     roster="md-house-members.json", adapter="multi_member_districts"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Maryland"),
    ),
    "al": dict(
        worksheet="al/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Alabama legislator?",
            body="the Alabama Legislature",
            short="Alabama Legislature",
            term="Senators and representatives both serve four-year terms.",
            wording=dict(
                ground="Both are drawn over the same ground and a district can split a "
                       "county, a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map."),
            chambers=[
                dict(layer="al-senate", name="Alabama Senate", short="Senate",
                     holder="Senator", roster="al-senate-members.json"),
                dict(layer="al-house", name="Alabama House of Representatives",
                     short="House", holder="Representative", roster="al-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Alabama"),
    ),
    # OREGON'S SENATE IS BUILT FROM ITS HOUSE: each Senate district is two
    # whole House districts, which or/scripts/build_legislative_boundaries.py
    # --check holds on the shipped files, so the default "the two rarely share
    # a boundary" would be false.
    "or": dict(
        worksheet="or/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Oregon legislator?",
            body="the Oregon Legislative Assembly",
            short="Oregon Legislative Assembly",
            term="Senators serve four-year terms and representatives two-year terms.",
            wording=dict(
                ground="Each Senate district is made of two whole House districts, and a "
                       "district can split a county, a city or a ZIP code, so the only way "
                       "to know which pair covers an address is to put the address on the "
                       "map.",
                maps_heading="Two House districts to a Senate district",
                maps="An address has one district in each chamber, and because every Senate\n"
                     "      district is two whole House districts, the House district decides the Senate\n"
                     "      one. The tables below list both chambers in full, so a reader who knows their\n"
                     "      district numbers can look up the members without opening the map at all."),
            chambers=[
                dict(layer="or-senate", name="Oregon State Senate", short="Senate",
                     holder="Senator", roster="or-senate-members.json"),
                dict(layer="or-house", name="Oregon House of Representatives",
                     short="House", holder="Representative", roster="or-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Oregon"),
    ),
    "ct": dict(
        worksheet="ct/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Connecticut legislator?",
            body="the Connecticut General Assembly",
            short="Connecticut General Assembly",
            term="Senators and representatives both serve two-year terms.",
            wording=dict(
                ground="Both are drawn over the same ground and a district can split a "
                       "county, a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map."),
            chambers=[
                dict(layer="ct-senate", name="Connecticut State Senate", short="Senate",
                     holder="Senator", roster="ct-senate-members.json"),
                dict(layer="ct-house", name="Connecticut House of Representatives",
                     short="House", holder="Representative", roster="ct-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Connecticut"),
    ),
    "ut": dict(
        worksheet="ut/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Utah legislator?",
            body="the Utah Legislature",
            short="Utah Legislature",
            term="Senators serve four-year terms and representatives two-year terms.",
            wording=dict(
                ground="Both are drawn over the same ground and a district can split a "
                       "county, a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map."),
            chambers=[
                dict(layer="ut-senate", name="Utah State Senate", short="Senate",
                     holder="Senator", roster="ut-senate-members.json"),
                dict(layer="ut-house", name="Utah House of Representatives",
                     short="House", holder="Representative", roster="ut-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Utah"),
    ),
    "ks": dict(
        worksheet="ks/metro-worksheet.json",
        legislature=dict(
            file="state-legislature.html",
            title="Who is my Kansas legislator?",
            body="the Kansas Legislature",
            short="Kansas Legislature",
            term="Senators serve four-year terms and representatives two-year terms.",
            wording=dict(
                ground="Both are drawn over the same ground and a district can split a "
                       "county, a city or a ZIP code, so the only way to know which pair "
                       "covers an address is to put the address on the map."),
            chambers=[
                dict(layer="ks-senate", name="Kansas Senate", short="Senate",
                     holder="Senator", roster="ks-senate-members.json"),
                dict(layer="ks-house", name="Kansas House of Representatives",
                     short="House", holder="Representative", roster="ks-house-members.json"),
            ]),
        congress=dict(
            file="congress.html",
            title="Who is my U.S. representative?",
            layer="us-house", roster="congress-roster.json",
            state="Kansas"),
    ),
}


def fail(msg):
    print("build-legislator-pages: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)



# tag -> why this instance ships NO state-legislature page. The gate below reads
# `metros.json` and refuses an instance with no entry, on a fleet invariant that
# is right: every instance registers two chambers, so a missing entry is a page
# nobody wrote. Minnesota is the first instance where the page cannot be written
# TRUELY, which is a different thing from being forgotten.
#
# Every sentence on that page is about the member: "the two cards name the
# district number for each chamber and the MEMBER who holds that seat", "both
# rosters are re-read on a schedule", and the officeholder table under it is one
# section per chamber keyed on a roster file. Minnesota ships neither chamber
# roster — the Legislature publishes both and this project has not built them,
# recorded as gap `mn-legislature-roster` — so generating the page would publish
# a page of claims about people it does not name, on a site whose whole standard
# is that it names nobody it cannot cite.
#
# WHAT WAS CONSIDERED AND NOT DONE: teaching this generator and
# build_officeholder_tables.py a roster-less chamber mode — district counts off
# the shipped boundary file, prose that links each chamber's own directory. That
# is the page Minnesota should eventually have, and it is a change to two shared
# generators that twelve true pages already ride, made in a change whose subject
# is publishing a state. The roster is what makes the page true, so the page
# lands with the roster.
#
# This is the ACCEPTED_DROPS shape: an entry carries its reason and its date and
# is RE-AUDITED on every run, and it FAILS when it stops describing the tree —
# the instance gone from metros.json, the chambers it names no longer in that
# instance's layers, or the rosters having arrived, which means the page is owed.
NO_LEGISLATURE_PAGE = {
    "mn": dict(
        chambers=["mn-senate", "mn-house"],
        rosters=["mn-senate-members.json", "mn-house-members.json"],
        gap="mn-legislature-roster",
        why="Minnesota names nobody in either chamber, so every claim this page "
            "makes about a member would be false. The page lands with the roster.",
        date="2026-09-30",
    ),
    # Kentucky is the SECOND instance of the same case, which is what makes the
    # reasoning above a rule rather than one state's exception: it registers both
    # chambers, ships neither roster, and the page's every sentence is about the
    # member. The roster-less chamber mode that would let both pages exist is
    # still the right eventual fix and is still not a go-live change's subject.
    "ky": dict(
        chambers=["ky-senate", "ky-house"],
        rosters=["ky-senate-members.json", "ky-house-members.json"],
        gap="ky-legislature-roster",
        why="Kentucky names nobody in either chamber, so every claim this page "
            "makes about a member would be false. The page lands with the roster.",
        date="2026-09-30",
    ),
    "in": dict(
        chambers=["in-senate", "in-house"],
        rosters=["in-senate-members.json", "in-house-members.json"],
        gap="in-general-assembly-roster",
        why="Indiana names nobody in either chamber, so every claim this page "
            "makes about a member would be false. The page lands with the roster.",
        date="2026-10-07",
    ),
}


def audit_no_legislature_page(metros, worksheets):
    """Re-audit NO_LEGISLATURE_PAGE against the tree on every run.

    An exception that nothing re-reads is a permanent hole in a gate with
    nothing saying so, which is the property ACCEPTED_DROPS had to be given
    after the fact. Three ways an entry stops describing the tree, all fatal.
    """
    known = {m["tag"] for m in metros}
    for tag, rec in sorted(NO_LEGISLATURE_PAGE.items()):
        if tag not in known:
            fail("NO_LEGISLATURE_PAGE names %s, which metros.json no longer "
                 "carries — drop the entry" % tag)
        ids = {l["id"] for l in worksheets[tag]["layers"]}
        absent = [c for c in rec["chambers"] if c not in ids]
        if absent:
            fail("NO_LEGISLATURE_PAGE[%s] names chamber layer(s) %s which that "
                 "instance no longer registers — re-read the entry"
                 % (tag, ", ".join(absent)))
        arrived = [r for r in rec["rosters"]
                   if os.path.exists(os.path.join(REPO_ROOT, tag, "data", "app", r))]
        if arrived:
            fail("NO_LEGISLATURE_PAGE[%s] is STALE: %s now ship(s), so the "
                 "state-legislature page is owed. Give %s a legislature entry "
                 "and drop this one" % (tag, ", ".join(arrived), tag))
        print("build-legislator-pages: %s ships no state-legislature page (%s, "
              "recorded %s): %s" % (tag, rec["gap"], rec["date"], rec["why"]))

def roster_rows(tag, filename):
    data = load(os.path.join(tag, "data", "app", filename))
    if not isinstance(data, dict) or not data:
        fail("%s/data/app/%s is not a non-empty object" % (tag, filename))
    named = [k for k, v in data.items() if isinstance(v, dict) and (
        v.get("name") or any(isinstance(m, dict) and m.get("name")
                             for m in v.get("members") or []))]
    if not named:
        fail("%s/data/app/%s names nobody" % (tag, filename))
    return data


def member_count(data):
    """The people a chamber's roster seats: one per district, or the district's
    own `seats` where it elects more than one (West Virginia's Senate, two per
    district). Counted from `seats` rather than from the members listed, so a
    vacant seat still counts as a seat."""
    return sum(int(v.get("seats", 1)) if isinstance(v, dict) else 1
               for v in data.values())


def legislature_page(tag, inst, worksheet, brand, app_name, landing, metros):
    spec = inst["legislature"]
    counts, members, keysets = [], 0, []
    for ch in spec["chambers"]:
        check_layer(worksheet, ch["layer"], "%s/%s" % (tag, spec["file"]))
        data = roster_rows(tag, ch["roster"])
        counts.append(len(data))
        keysets.append(set(data))
        members += member_count(data)
    # A LEGISLATURE ELECTED FROM ONE MAP (Arizona's and New Jersey's: each
    # district elects one senator and two members of the lower house) says so
    # rather than counting the same districts twice, and is HELD to it: the
    # two rosters must be keyed by the same districts, or the page's first
    # sentence is false and the build stops.
    if spec.get("shared_map") and len({frozenset(k) for k in keysets}) != 1:
        fail("%s/%s says both chambers are elected from one map, and its "
             "rosters are keyed by different districts" % (tag, spec["file"]))
    layers = ",".join(ch["layer"] for ch in spec["chambers"])
    # The members, not the districts: equal everywhere but West Virginia, whose
    # 17 Senate districts seat 34 senators.
    total = members
    # "59 Senate districts and 118 House districts", not "59 Illinois Senate
    # districts, 118 Illinois House of Representatives districts" — the state is
    # already in the body's name two words earlier, and a list joined with a
    # comma and no conjunction reads as a fragment.
    parts = ["%d %s district%s" % (n, ch["short"], "" if n == 1 else "s")
             for n, ch in zip(counts, spec["chambers"])]
    pieces = " and ".join(parts)
    # THE WORDS A STATE CAN REPLACE, each defaulting to the sentence every page
    # before 2026-11-11 printed, so a page that sets none is byte-identical. A
    # state sets one where the default would be false of it: one map for both
    # chambers (Arizona, New Jersey), or a House of named, multi-member and
    # floterial districts (New Hampshire). Counts are still len(roster).
    words = spec.get("wording", {})
    fmt = dict(body=spec["short"], pieces=pieces, districts=counts[0])
    strong = words.get("strong", "The {body} has {pieces}.").format(**fmt)
    ground = words.get(
        "ground", "Both are drawn over the same ground and neither follows a city, "
                  "county or ZIP boundary, so the only way to know which pair covers "
                  "an address is to put the address on the map.")
    shows = words.get(
        "shows", "Select any point and the two cards name the <strong>district number</strong> for each\n"
                 "        chamber and the <strong>member</strong> who holds that seat, with their party, their\n"
                 "        offices and a link to their own page where the legislature publishes one.")
    maps_heading = words.get("maps_heading", "Two chambers, two maps")
    maps = words.get(
        "maps", "An address has one district in each chamber and the two rarely share a boundary: the\n"
                "      chambers are apportioned separately, and in several of these states one chamber's districts\n"
                "      are built by pairing the other's. The table below lists both in full, so a reader who knows\n"
                "      their district number can look up the member without opening the map at all.")
    lede = dict(
        html='<p class="lede"><strong>%s</strong> %s %s</p>'
             % (html.escape(strong), html.escape(ground), html.escape(spec["term"])),
        cta='    <a class="cta" href="./#layers=%s">Find your %s districts →</a>\n'
            '    <p class="cta-note">Opens the map with both chambers on. Search your '
            'address or ZIP, or tap your location.</p>'
            % (layers, html.escape(spec["short"])))
    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>%(shows)s</p>
      <p>Every other district covering the same point is listed beside them, so one click answers
        the state question and the county, city and federal ones together.</p>
    </div>
  </section>

  <section>
    <h2>%(maps_heading)s</h2>
    <p>%(maps)s</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>Both rosters are re-read on a schedule from the legislature's own published member lists and
      land as a reviewed pull request; the map names no officeholder it cannot cite. A seat the
      source does not name is shown as unnamed rather than filled in.</p>
    <div class="disclaimer">
      <strong>Not for legal or official use.</strong> Boundary and roster data come from public
      sources that explicitly disclaim legal precision. Confirm district assignments and
      officeholders with the relevant government office before relying on them for anything
      official.
    </div>
  </section>

""" % dict(shows=shows, maps_heading=html.escape(maps_heading), maps=maps)
    subtitle = ("%s district lookup — free, by address, ZIP, or a tap on the map."
                % spec["short"])
    # Under 155 characters, which validate_serp_lengths.py holds every page to:
    # the first draft ran to 164 on the four longest body names, and a
    # description that overruns is cut mid-clause in the search result.
    desc = words.get(
        "desc", "Your {body} districts by address or ZIP — the district number in each "
                "chamber and the member who holds it.").format(**fmt)
    og = ("Find your %s districts by address or ZIP, and the %d members who hold them."
          % (spec["short"], total))
    return spec["file"], spec["title"], subtitle, desc, og, lede, sections, total


def congress_page(tag, inst, worksheet, brand, app_name, landing, metros):
    spec = inst["congress"]
    check_layer(worksheet, spec["layer"], "%s/%s" % (tag, spec["file"]))
    roster = roster_rows(tag, spec["roster"])
    n = len(roster)
    state = spec["state"]
    lede = dict(
        html='<p class="lede"><strong>%s elects %d member%s of the U.S. House of '
             'Representatives.</strong> A congressional district is redrawn after each '
             'census to hold equal population, so it follows neither county lines nor '
             'city limits, and an address a mile away can sit in a different one.</p>'
             % (html.escape(state), n, "" if n == 1 else "s"),
        cta='    <a class="cta" href="./#layers=%s">Find your U.S. House district →</a>\n'
            '    <p class="cta-note">Opens the map with the U.S. House layer on. Search '
            'your address or ZIP, or tap your location.</p>' % spec["layer"])
    sections = """  <section>
    <h2>What the lookup shows</h2>
    <div class="answer-card">
      <p>Select any point and the card names the <strong>district number</strong> covering it and
        the <strong>representative</strong> who holds the seat, with their party, their Washington
        and district offices, and a link to their House page.</p>
      <p>Your U.S. senators are not here, and that is not an omission: senators are elected
        statewide, so every address in the state has the same two and no map can tell them apart.</p>
    </div>
  </section>

  <section>
    <h2>District, county and ZIP are three different shapes</h2>
    <p>A congressional district is an electoral boundary and nothing else. It splits counties, it
      splits cities, and it splits ZIP codes — which is why a ZIP-code lookup can return two
      representatives and be right both times. The map answers for one exact point instead.</p>
  </section>

  <section>
    <h2>Where the names come from</h2>
    <p>The boundaries come from the Census Bureau's own published districts and the roster is
      re-read on a schedule from the House's member list, landing as a reviewed pull request. The
      map names no officeholder it cannot cite.</p>
    <div class="disclaimer">
      <strong>Not for legal or official use.</strong> Boundary and roster data come from public
      sources that explicitly disclaim legal precision. Confirm district assignments and
      officeholders with the relevant government office before relying on them for anything
      official.
    </div>
  </section>

"""
    subtitle = ("%s U.S. House district lookup — free, by address, ZIP, or a tap "
                "on the map." % state)
    desc = ("Your %s U.S. House district by address or ZIP \u2014 the district number, the "
            "representative who holds it, and every other district covering that point." % state)
    # A LONG STATE NAME OVERRUNS validate_serp_lengths.py's 155 characters:
    # "North Carolina" took this sentence to 159 at that instance's 2026-10-09
    # go-live. The shorter wording is used only where the long one does not
    # fit, so every page that already fits is unchanged.
    if len(desc) > 155:
        desc = ("Your %s U.S. House district by address or ZIP \u2014 the district number, "
                "its representative, and every other district covering that point." % state)
    og = ("Find your %s congressional district by address or ZIP, and the "
          "representative who holds it." % state)
    return spec["file"], spec["title"], subtitle, desc, og, lede, sections, n


def related_rows(tag, inst, this_file, landing, metros):
    """Links to the instance's own map, its other new page, and one sibling.

    Derived rather than listed: the sibling is the next instance in metros.json
    order, so a new state joins these rows the day it is registered.
    """
    # "its other new page" is not a given: an instance in NO_LEGISLATURE_PAGE
    # ships congress.html alone, so the row would link a 404. Dropped rather
    # than replaced — there is no other half of the answer to point at, and
    # inventing a third destination to fill the slot would be filling a layout
    # rather than answering anything. Which pages exist is read from the
    # instance entry, the same test build() uses to decide what to write, and
    # never from the disk: a run that creates both pages finds neither on disk
    # while it writes the first, so each would leave the other out and the
    # next --check would report both as drift.
    if this_file == inst["congress"]["file"]:
        other = inst["legislature"]["file"] if "legislature" in inst else None
        other_label = "Who is my state legislator?"
    else:
        other = inst["congress"]["file"]
        other_label = "Who is my U.S. representative?"
    order = [m["tag"] for m in metros]
    sib = order[(order.index(tag) + 1) % len(order)]
    sib_name = next(m["landing_name"] for m in metros if m["tag"] == sib)
    sib_scope = next(m["scope"] for m in metros if m["tag"] == sib)
    esc = html.escape
    return "\n".join([
        '      <li><a href="./">What district am I in?</a><span>Every district that '
        'covers one point in %s, and who represents you there.</span></li>' % esc(landing),
    ] + ([
        '      <li><a href="%s">%s</a><span>The other half of the answer, on its own '
        'page.</span></li>' % (other, esc(other_label)),
    ] if other else []) + [
        '      <li><a href="../%s/">%s</a><span>The same lookup, %s.</span></li>'
        % (sib, esc(sib_name), esc(sib_scope)),
    ])


def build(tag, inst, metros, check):
    worksheet = load(inst["worksheet"])
    brand = worksheet["brand"]
    app_name = brand["app_name"]
    landing = next(m["landing_name"] for m in metros if m["tag"] == tag)
    themeboot = shared_head_block(tag, THEMEBOOT_RE, "theme boot script")
    mark = shared_head_block(tag, MARK_RE, "districtry mark")

    results = []
    makers = [m for m in (legislature_page, congress_page)
              if (m is congress_page or "legislature" in inst)]
    for maker in makers:
        (page_file, title, subtitle, desc, og, lede, sections,
         seats) = maker(tag, inst, worksheet, brand, app_name, landing, metros)
        path = os.path.join(REPO_ROOT, tag, page_file)
        preserved = preserved_from_disk(path)
        page = head(tag, brand, app_name, page_file, title, desc, og)
        page += shell(app_name, title, subtitle, lede, sections,
                      related_rows(tag, inst, page_file, landing, metros), preserved,
                      themeboot, mark, tag)
        results.append((os.path.join(tag, page_file), path, page, seats))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="drift gate: fail rather than write")
    args = ap.parse_args()

    try:
        return run(args)
    except PageError as exc:
        fail(str(exc))


def run(args):
    metros = load(METROS)["metros"]
    known = {m["tag"] for m in metros}
    missing = set(INSTANCES) - known
    if missing:
        fail("INSTANCES names %s, which metros.json does not carry"
             % ", ".join(sorted(missing)))
    unregistered = known - set(INSTANCES) - set(NO_LEGISLATURE_PAGE)
    if unregistered:
        fail("metros.json carries %s with no entry here — every instance ships "
             "a legislature and a U.S. House layer, so a missing entry is two "
             "pages nobody wrote" % ", ".join(sorted(unregistered)))
    # An instance in NO_LEGISLATURE_PAGE still owes a congress page, so it has a
    # CONGRESS_ONLY entry in INSTANCES; being in the table exempts one page, not
    # both. This catches the entry added with no congress entry beside it.
    for tag in sorted(NO_LEGISLATURE_PAGE):
        if tag not in INSTANCES or "congress" not in INSTANCES[tag]:
            fail("NO_LEGISLATURE_PAGE[%s] exempts the legislature page only — "
                 "that instance still ships a U.S. House layer and owes a "
                 "congress page, so it needs a congress entry in INSTANCES" % tag)
    audit_no_legislature_page(
        metros, {t: load(INSTANCES[t]["worksheet"]) for t in sorted(INSTANCES)})

    drift, written, seats = [], 0, 0
    for tag in sorted(INSTANCES):
        for rel, path, page, count in build(tag, INSTANCES[tag], metros, args.check):
            seats += count
            try:
                with open(path, encoding="utf-8") as f:
                    current = f.read()
            except OSError:
                current = None
            if current == page:
                continue
            if args.check:
                drift.append((rel, current, page))
                continue
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(page)
            written += 1
            print("build-legislator-pages: %s — written" % rel)

    if args.check:
        for rel, current, page in drift:
            if current is None:
                print("build-legislator-pages: %s does not exist" % rel, file=sys.stderr)
                continue
            print("build-legislator-pages: DRIFT in %s" % rel, file=sys.stderr)
            for dl in difflib.unified_diff(current.splitlines(), page.splitlines(),
                                           fromfile="committed", tofile="regenerated",
                                           lineterm="", n=1):
                print("  " + dl, file=sys.stderr)
        if drift:
            fail("%d page(s) out of date — run "
                 "python3 scripts/build_legislator_pages.py" % len(drift))
        print("build-legislator-pages: OK — %d page(s) across %d instance(s), "
              "%d officeholder(s) named" % (len(INSTANCES) * 2, len(INSTANCES), seats))
    else:
        print("build-legislator-pages: OK — %d page(s) written, %d current, "
              "%d officeholder(s) named"
              % (written, len(INSTANCES) * 2 - written, seats))


if __name__ == "__main__":
    main()
