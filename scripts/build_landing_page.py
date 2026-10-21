#!/usr/bin/env python3
"""Build the root landing page — the fleet's front door (R4, docs/DEV_PROCESS_ASSESSMENT.md;
address-first redesign with a coverage map, from the Claude Design handoff
"Districtry landing page alternatives").

WHY THIS EXISTS. "One repo, one site" only pays off if the site has a front
door. R2.3 moved the Illinois app to /il/ and left the root a redirect stub; R3
brought SF and NYC in as folders. This is the page that finally makes the root
mean something: the brand, an address box that opens the right place, a map of
what's covered, and the list of places the fleet answers for.

IT IS GENERATED, AND THAT IS THE POINT. The rebrand assessment's central finding
was that brand identity had become scattered literals — 98 files carrying
`chidistricts`, seven strings locked inside engine fences, a redesign built twice
because index.html could not be parameterised. A hand-written landing page whose
state list is HTML would reproduce that failure on day one of the fix. So every
fact on this page comes from a file that already owns it:

    metros.json                            the fleet list — name, tag, blurb,
                                            scope, url, bbox
    districtry/tokens/districtry.tokens.css the design tokens (light + dark)
    districtry/icons/favicon.svg           the mark, inlined as a data URI
    fonts/barlow-fontface.css              self-hosted Barlow (build_fonts.py landing)

Adding a state to the fleet is a metros.json entry and a regenerate. Restyling
is a token edit and a regenerate. Neither is an edit to this page.

THE FORWARDING GUARD IS NOT OPTIONAL. Before R2.3 the app lived AT the root, and
every share link and embed snippet it handed out was built from the root URL:

    https://chidistricts.com/?utm_source=share&utm_medium=link#point=41.88,-87.63&layers=ward
    <iframe src="https://chidistricts.com/?utm_source=embed&utm_medium=iframe#point=...">

Those are in other people's pages and bookmarks and cannot be recalled. The
redirect stub forwarded them; a landing page that simply replaced it would turn
every one of them into a page about Illinois instead of the map they asked for.
So the root still forwards ANY url carrying app parameters — a #point=/#layers=
permalink, or the share/embed campaign tags — and renders the landing page only
for a bare visit. The guard runs in <head> before the body paints, so a
forwarded visit never flashes this page.

THE COVERAGE MAP EXISTS NOW, AND THE OBJECTION THAT USED TO RULE IT OUT IS
ANSWERED RATHER THAN IGNORED. This docstring used to say no coverage map: "it
would need Leaflet plus an instance's own boundary data, and a fleet page that
loads one instance's geometry is telling a lie about the other two." The
objection was about ONE instance's shape standing in for the whole fleet — so
scripts/build_coverage_map.py draws every instance's OWN published outline
(each already shipped in its own data/app/*.json) rather than picking one.
The <iframe> here just embeds that separately-generated, separately-drift-gated
page; see its own module docstring for the two-tier (statewide vs.
county-dispatched) story it draws.

THE ADDRESS BOX ROUTES FOR REAL. It calls the same Photon endpoint the fleet's
own apps already call for their "did you mean a sibling metro" fallback
(geocodeUnbounded in each instance's ENGINE metro-portal block), tests the
result against each metro's own bbox (the same bbox METRO_EXPLORERS already
carries for that fallback), and sends the reader straight to the covered
instance with the point pre-selected — or says plainly that nowhere covers it
yet, never guessing. This duplicates neither data nor a UI: it is new code
because the root page has no per-instance JS module to call into, but the
provider, the bbox test and the tie-break on an overlap are the same ones
metro-portal already uses.

WHAT IS DELIBERATELY ABSENT. No analytics beyond the fleet's existing GoatCounter
tag (adding a NEW tracker to a new surface is not a build-step decision), and
no per-visitor geolocation (the address box asks for a query the reader typed,
never the browser's location).

    python3 scripts/build_landing_page.py            # write index.html
    python3 scripts/build_landing_page.py --check    # drift gate; exit 1 on diff
"""

import argparse
import difflib
import glob
import html
import functools
import json
import math
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The coverage map's own table of areas, so the key under it names the lighter
# statewide wash only while an area that draws one is live. One reader of which
# areas have two tiers, not two.
from build_coverage_map import AREAS  # noqa: E402
# The dark twin of a map colour, so a question tile and the layer it asks about
# share one colour at night as well as by day. One derivation, not two.
import build_dark_map_palette as palette  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO_ROOT, "metros.json")
TOKENS = os.path.join(REPO_ROOT, "districtry", "tokens", "districtry.tokens.css")
# WHY THE FAVICON IS A FILE AND NOT A data: URI ANY MORE. It was inlined here
# — one fewer request, no flash — and that cost the site its logo in Google
# results. Google's rule is blunt: "Googlebot-Image must be able to crawl the
# favicon file", and there is no file to crawl in a data: URI. districtry.com
# showed the generic globe next to its result, and /favicon.ico 404'd too, so
# the fallback every browser requests unprompted was also missing.
#
# Four declarations, because they answer to different consumers: the SVG for
# modern browsers, a 192px PNG well above Google's 48px recommendation, the ICO
# for the unprompted /favicon.ico request, and apple-touch-icon (which Google
# also accepts) for iOS. Google reads the favicon from the HOME PAGE and applies
# it per HOSTNAME, so this page governs every path under districtry.com — the
# apps keep their own inline mark for their own tabs and it changes nothing for
# search. The URLs must stay put: Google asks that a favicon URL be stable.
FAVICON = os.path.join(REPO_ROOT, "districtry", "icons", "favicon.svg")
# The 5c mark is lifted from the app rather than restated, so the geometry has
# one source. The favicon above is the SIMPLIFIED one-polygon fallback the brand
# spec calls for below 24px — right for a browser tab, wrong for the front door,
# which is why the two are different files doing different jobs.
MARK_SOURCE = os.path.join(REPO_ROOT, "il", "index.html")
# The site's one-sentence description. A module constant rather than a local
# because the installed app says the same thing: build_manifests.py reads it for
# the web app manifest's `description`, so the front door and the app a reader
# installs from it cannot come to describe districtry two different ways.
DESCRIPTION = ("Enter an address or ZIP — districtry shows every civic district that covers "
               "that point on the map, and the people who hold those seats. Free, no login.")

# Each instance's worksheet, for the layer count on its row in the state list.
# A row that states a number must read it from the thing that owns it; a
# hand-typed count is the drift this repo keeps writing generators to avoid.
#
# KEYED BY INSTANCE TAG — the folder, which is the URL, which is the state code
# on the pill. R5 renamed sf/ -> ca/ and nyc/ -> ny/ (the tag is the STATE, not
# the metro: metros.json still calls them 'sf' and 'nyc' by id), and this table
# is the one place that pairs a tag with a file, so it moves with them.
INSTANCE_WORKSHEET = {
    "il": "metro-worksheet.json",
    "ca": "ca/metro-worksheet.json",
    "ny": "ny/metro-worksheet.json",
    "wi": "wi/metro-worksheet.json",
    "ia": "ia/metro-worksheet.json",
    "mi": "mi/metro-worksheet.json",
    "mn": "mn/metro-worksheet.json",
    "in": "in/metro-worksheet.json",
    "nc": "nc/metro-worksheet.json",
    "ky": "ky/metro-worksheet.json",
    "ok": "ok/metro-worksheet.json",
    "sc": "sc/metro-worksheet.json",
    "tn": "tn/metro-worksheet.json",
    "ar": "ar/metro-worksheet.json",
    "ms": "ms/metro-worksheet.json",
    "la": "la/metro-worksheet.json",
    "mo": "mo/metro-worksheet.json",
}
FONTFACE = os.path.join(REPO_ROOT, "fonts", "barlow-fontface.css")
THEME_BOOT = os.path.join(REPO_ROOT, "engine", "shared", "theme-boot.txt")


def shared_theme_boot():
    """The theme boot, read from its ONE source.

    engine/shared/theme-boot.txt is shared with the 42 authored pages that take
    it as an ENGINE fence spliced by compose_app.py, and with the root-page
    shell in build_privacy_page.py, which reads the same file for the same
    reason: a fence in a GENERATED page would have to agree with whatever the
    builder emits inside it, which means reading the file anyway. One source,
    three consumers.

    Returned verbatim, because this block is JavaScript and its indentation is
    part of what ships.
    """
    with open(THEME_BOOT, encoding="utf-8") as fh:
        return fh.read().rstrip("\n")
PLAY_APP = os.path.join(REPO_ROOT, "engine", "shared", "play-app.txt")


def shared_play_app():
    """The Google Play app's mark, read from its ONE source.

    engine/shared/play-app.txt is an ENGINE fence in every app, every sources
    page and the sponsorship page, spliced by compose_app.py. This page carries
    it too because its footer asks for sponsorship, and a reader in the Play
    app reaches it from any state's menu. Returned verbatim, like the theme
    boot.
    """
    with open(PLAY_APP, encoding="utf-8") as fh:
        return fh.read().rstrip("\n")
MAP_LINK = os.path.join(REPO_ROOT, "engine", "shared", "map-link.txt")


def shared_map_link():
    """The map-link parser, read from its ONE source.

    engine/shared/map-link.txt is an ENGINE fence in every app, spliced by
    compose_app.py, and the address box here reads pasted links with the same
    code, so the front door and the app it opens cannot read one link two
    ways. Returned verbatim, like the theme boot.

    It also carries the state names a link's address is read against
    (US_STATE_NAMES, for addressStateTag), which must be POSTAL_CODES here:
    otherwise the state list under the map and the address box above it
    would disagree about which states there are, so a difference fails.
    """
    with open(MAP_LINK, encoding="utf-8") as fh:
        text = fh.read().rstrip("\n")
    block = re.search(r"var US_STATE_NAMES = \{(.*?)\};", text, re.S)
    if not block:
        fail("engine/shared/map-link.txt has no US_STATE_NAMES table, which the "
             "address box reads a map link's state from.")
    names = {k.strip('"').upper(): v
             for k, v in re.findall(r'("?[a-z]{2}"?):\s*"([^"]+)"', block.group(1))}
    if names != POSTAL_CODES:
        fail("US_STATE_NAMES in engine/shared/map-link.txt and POSTAL_CODES here "
             "disagree: %s" % sorted(set(names.items()) ^ set(POSTAL_CODES.items())))
    return text
OUT = os.path.join(REPO_ROOT, "index.html")

# The canonical host TODAY. R5 moves this to districtry.com along with
# metros.json's urls; both are data, so that cutover is an edit here plus a
# regenerate, never a rewrite of the page.
# A question page is any .html directly inside an instance folder that is not
# one of these four AND is not a redirect shell. The app itself, and the three
# sub-pages every instance carries, are not answers to a question somebody
# types into a search box.
NOT_A_LOOKUP = {"index.html", "faq.html", "sources.html", "history.html"}

# The second half of that test, and the half a filename cannot make: il/ has a
# privacy.html that is a SHELL pointing at the root page, and the first draft
# of this block linked it, labelled "Moved". Same rule build_sitemap.py uses to
# decide what is a real page — a meta refresh or a noindex is not one — so a
# shell added later is excluded without anybody updating a list.
IS_SHELL = re.compile(r'http-equiv=["\']?refresh|name=["\']?robots["\']?[^>]*noindex',
                      re.I)

CANONICAL = "https://districtry.com/"

# ---------------------------------------------------------------------------
# THE QUESTION ROWS: the front door groups the question pages BY QUESTION, not
# by place. It grouped by place until 2026-09-18, which put the page's own
# question in the link text — good anchor text, but it printed "Who is my U.S.
# representative?" six times and stacked six place headings down the page. The
# row carries the question once, as a heading, and each link names the place it
# answers for.
#
# THE TRADE IS ANCHOR TEXT, so the chip carries a TOPIC as well as a place: a
# bare "Illinois" says nothing about where it points when read out of context,
# which is the test Google's own link guidance sets. Every chip's text is
# therefore "<place> · <topic>", and build() FAILS if any two come out alike.
#
# STILL DISCOVERED, NEVER LISTED: the pages themselves come from the tree
# exactly as before (a .html in an instance folder that is not the app, a
# sub-page or a shell). These tables say only how a discovered page is GROUPED
# and LABELLED, and the audit below fails on a page no row claims, a row no
# page fills, and an override naming a page that is not there. A new state
# needs no edit here at all — its congress.html and state-legislature.html take
# the defaults; a new KIND of page is what has to be filed.
TAIL_ROW = "Also answered in one place"
QUESTION_ROWS = [
    ("Who is my U.S. representative?", ("congress.html",)),
    ("Who is my state legislator?", ("state-legislature.html",)),
    # EIGHT NAMES FOR ONE READER'S QUESTION. A county's governing body is a
    # board in Illinois and Wisconsin, a board of supervisors in Iowa and
    # Mississippi, a board
    # of commissioners in Michigan, a county legislature in New York, a
    # fiscal court (or a merged council) in Kentucky, a county council in
    # South Carolina and a quorum court in Arkansas, and a parish's is a
    # police jury or a council in Louisiana, and
    # somebody asking who sits on it does not know or care which word their
    # state uses. One row, so the front door asks the question once.
    ("Who sits on my county board?", ("county-board.html", "county-supervisor.html",
                                      "county-commissioner.html",
                                      "county-legislature.html",
                                      "county-government.html",
                                      "county-council.html",
                                      "quorum-court.html",
                                      "parish-government.html")),
    ("Who represents me on the city council?", ("ward.html", "council-district.html",
                                                "supervisor-district.html",
                                                "city-council.html")),
    ("What police district am I in?", ("police-district.html", "police-precinct.html")),
    ("Which school board district am I in?", ("school-board.html",)),
    ("Which special district covers me?", ("fire-district.html", "park-district.html",
                                           "library-district.html")),
    ("Which court elects my judges?", ("judicial-subcircuit.html", "circuit-court.html",
                                       "supreme-court.html")),
    # The tail row, for a concept only one place answers. A row of its own per
    # page would be three headings each naming a single link, which is the
    # shape the regrouping exists to retire.
    (TAIL_ROW, ("precinct.html", "precinct-maps.html", "township.html",
                "community-board.html",
                "county-auditor.html", "borough.html")),
]

# THE COLOUR EACH QUESTION'S TILE IS MARKED IN: the map colour of the concept
# the question asks about, from layer-concepts.json `colors`, so a reader who
# goes on to the map meets the same colour on that layer there. The dark twin
# is build_dark_map_palette.dark_twin over the whole fleet's colours, which is
# the colour every app draws that concept in at night, not a second guess at
# it. The tail row asks no one question, so it names no concept and its tile
# is marked in the page's own neutral colour rather than one borrowed from a
# concept it would then seem to be about. render_asks fails on a question
# with no entry here, an entry naming a concept with no colour, and an entry
# for a question no row asks.
QUESTION_CONCEPT = {
    "Who is my U.S. representative?": "us-house",
    "Who is my state legislator?": "state-senate",
    "Who sits on my county board?": "county-board",
    "Who represents me on the city council?": "city-council",
    "What police district am I in?": "police-district",
    "Which school board district am I in?": "school-board-district",
    "Which special district covers me?": "fire-district",
    "Which court elects my judges?": "supreme-court-district",
    TAIL_ROW: None,
}

# The topic each page's chip names, by page basename — the default for every
# instance that carries that page.
CHIP_TOPIC = {
    "congress.html": "U.S. House",
    "state-legislature.html": "Legislature",
    "county-board.html": "county board",
    "county-supervisor.html": "supervisors",
    "county-commissioner.html": "commissioners",
    "county-government.html": "fiscal court",
    "county-council.html": "county council",
    "quorum-court.html": "quorum court",
    "parish-government.html": "police jury or council",
    "county-legislature.html": "county legislature",
    "city-council.html": "city council",
    "county-auditor.html": "county auditor",
    "supreme-court.html": "Supreme Court",
    "borough.html": "borough offices",
    "ward.html": "alderman, by ward",
    "council-district.html": "Council district",
    "supervisor-district.html": "supervisor district",
    "police-district.html": "police district",
    "police-precinct.html": "NYPD precinct",
    "school-board.html": "school board",
    "fire-district.html": "fire district",
    "park-district.html": "park district",
    "library-district.html": "library district",
    "judicial-subcircuit.html": "judicial subcircuit",
    "circuit-court.html": "circuit court",
    "precinct.html": "precinct",
    "precinct-maps.html": "who publishes precinct maps",
    "township.html": "township",
    "community-board.html": "community board",
}

# Where an instance's own word for the same page differs. The body a reader
# would name is the informative one, and it is what makes six otherwise
# identical legislature chips say six different things.
CHIP_TOPIC_BY_INSTANCE = {
    ("il", "state-legislature.html"): "General Assembly",
    ("ny", "state-legislature.html"): "NY Legislature",
    ("ca", "state-legislature.html"): "CA Legislature",
    ("il", "county-board.html"): "commissioners",
    ("wi", "county-board.html"): "supervisors",
    ("il", "school-board.html"): "Board of Education",
}

# Where the page answers for a CITY inside the instance rather than the whole
# of it. Illinois serves 93 counties; its ward, police-district and
# school-board pages answer for Chicago alone, and a chip reading "Illinois"
# on those three would claim ground the page does not cover.
CHIP_PLACE = {
    ("il", "ward.html"): "Chicago",
    ("il", "police-district.html"): "Chicago",
    ("il", "school-board.html"): "Chicago",
}


# The one external profile that carries the name "districtry" and that this
# project can point at as itself. It goes in the WebSite node's sameAs (below)
# because a coined name has nothing for a search engine to attach it to: the
# root asserted the string and linked it to no identifier anywhere. Only URLs
# that genuinely name this project belong here — the publisher's own GitHub
# account is a different entity and is deliberately not listed.
REPO = "https://github.com/ThursdaysFamous/districtry"

# The front page's notice. Data, not markup, so retiring it is deleting a
# constant rather than editing a page — set NOTICE to None when it has served
# its time.
#
# It invites Android readers into the Google Play app's closed test (Adam,
# 2026-10-20). It replaced the "chidistricts.com is now districtry.com" notice
# that had stood here since the R2.3 move. A personal Play developer account
# made after November 2023 may apply to publish an app only once at least 12
# testers have each stayed opted in to its closed test for the 14 days before
# it applies (Play Console help, read 2026-10-17), so the link goes to the
# steps page the printed sign-up sheet opens, with ref=front-page so the
# traffic report shows how many readers arrive there from this page
# (GoatCounter reads ref as the referrer). It is linked as android.html, the
# way this page links every other page, and not as the printed /android:
# GitHub Pages answers both, but the server the browser checks run against
# serves a file only by its own name, and page_consistency_test.mjs fetches
# every link on the page, hidden or not.
#
# WHO SEES IT is "only": "android". The page ships the notice hidden, and its
# script shows it when the user agent names Android, the window is not an
# installed copy (display-mode standalone, which the Play app's own window
# reports as well) and the Play app's mark from engine/shared/play-app.txt is
# not set. A computer, an iPhone or a browser with no script shows nothing,
# because what the notice offers exists only on Android.
#
# IT STAYS UNTIL THE READER CLOSES IT. The rename notice faded after 15
# seconds, which suited news and suits an invitation to act much less; and on
# a phone it sat in the page's flow, so the fade moved the address box up under
# a reader who had started typing.
#
# A CLOSE OR A TAP ON ITS LINK IS REMEMBERED, "remember": "android-test" (Adam,
# 2026-10-20: a "no" should stay closed). The page writes one word in the
# browser's localStorage under the key the maps' own invitation to the test
# uses, and notice_memory() reads both the key and the word from the engine's
# install-app block, so a reader who closed or followed either invitation is
# shown neither again, while a reader who only saw the maps' bar still sees
# this one. localStorage and not a cookie: a cookie goes to the host with every
# request, and this word never leaves the browser. The privacy page measures
# the write and says so. The notice cannot outlive the maps' test: once
# DST_ANDROID_TEST_URL there is null, this build fails until NOTICE changes.
NOTICE = {
    "heading": "Help test districtry on Android",
    "body": ("districtry is coming to Google Play as an app, and Google needs at "
             "least 12 people to test it for 14 days in a row first. Joining "
             "takes a few minutes."),
    "link": {"href": "/android.html?ref=front-page", "text": "See how to join"},
    "only": "android",
    "remember": "android-test",
}
NOTICE_ONLY = ("android",)
NOTICE_REMEMBER = ("android-test",)
INSTALL_APP = os.path.join(REPO_ROOT, "engine", "index.html", "install-app.txt")

# There is no independence line under the address box any more (Adam,
# 2026-10-21: "It's redundant now and the migration is long past the point of
# the Google warning"). It went in after Google Safe Browsing flagged
# districtry.com under "Deceptive pages" on 2026-08-25: a day-old domain that
# had just absorbed a mass redirect from an established site, asked for a home
# address and rendered county seals and "who represents you", while saying
# NOWHERE who runs it or that it is unofficial. Nothing on the site was
# deceptive, but a classifier had no way to tell an independent civic
# reference from an impersonation of one. The footer says both things, so it
# is now the one place this page says them, and it stays.

# Where a forwarded visit goes. The Illinois app is what lived at this root
# before R2.3, so it is the only instance whose old links can be in the wild.
FORWARD_TO = "/il/"

# Every US state + DC, so the state list under the coverage map never needs a
# hand-typed row: each one is a link when metros.json has an entry for it and
# plain text when it does not. A metros.json entry whose landing_name is a
# state ("Illinois") is that state's row. One whose landing_name is a city
# ("San Francisco") is found through its tag, which is the state's postal code
# (POSTAL_CODES below), and its row says the city is all that answers there —
# so California is a link to /ca/ reading "San Francisco only", never a full
# state and never missing.
US_STATES_AND_DC = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin",
    "Wyoming",
]

# Postal code -> state, for the one case above that needs it: an instance whose
# landing_name is a city. Its tag is the folder and the URL path, and the fleet
# rule is that a tag IS the state code (ny/ and ca/ serve one city each and are
# still named for the state), so the tag is enough to find the row.
POSTAL_CODES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# Tokens this page actually sets. Naming them explicitly makes the token file a
# CHECKED dependency: rename one upstream and this build fails by name instead
# of emitting a page with a broken custom property.
LIGHT_TOKENS = [
    "brand-600", "brand-700", "brand-warm", "brand-tint", "brand-border",
    "paper", "surface", "ink", "ink-3", "muted", "faint", "border", "error",
    "data-500", "data-tint",
    "font-heading", "font-heading-weight", "font-body",
    "radius-card", "radius-btn", "shadow-card",
]
DARK_TOKENS = [
    "brand-700", "brand-warm", "brand-tint", "brand-border",
    "paper", "surface", "ink", "ink-3", "muted", "faint", "border", "error",
    "data-500", "data-tint",
    "shadow-card",
]
# --brand-700 and --brand-warm now EXIST in the token file's dark tier, so the
# dark block takes them by name. They used to be aliased to --brand here, which
# is how this page came to serve #a78bfa where the app serves #c4b0ff for the
# same role on the same brand — the alias was a stand-in for a missing token and
# outlived it.
DARK_EXTRA = {"brand-600": "brand"}


# The metric-matched fallback the body stack names. A real face with no
# download — local('Arial') plus overrides computed with fontTools — so the page
# holds its line metrics while Barlow loads instead of reflowing on swap. It
# lived in the three apps only, while every other surface NAMED it in
# --font-body and did not define it, which is a stack that silently falls
# through to -apple-system. scripts/build_brand_tokens.py --check keeps the
# copies identical. Recompute if the body family or its version changes.
FALLBACK_FACE = """@font-face {
  font-family: 'Barlow Fallback';
  src: local('Arial');
  ascent-override: 100.00%;
  descent-override: 20.00%;
  line-gap-override: 0.00%;
  size-adjust: 101.66%;
}"""


def fail(msg):
    print("build-landing-page: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def read(path, what):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except OSError as e:
        fail("cannot read %s (%s): %s" % (os.path.relpath(path, REPO_ROOT), what, e))


def parse_token_block(css, selector, path):
    """Return {name: value} for one CSS rule's custom properties."""
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\n\}", css, re.S)
    if not m:
        fail("%s has no %s block" % (os.path.relpath(path, REPO_ROOT), selector))
    return dict(re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)))


def token_css(names, table, where, extra=None, indent="  "):
    out = []
    for n in names:
        if n not in table:
            fail("token --%s is missing from the %s block — renamed upstream?" % (n, where))
        out.append("%s--%s: %s;" % (indent, n, table[n].strip()))
    for alias, src in sorted((extra or {}).items()):
        if src not in table:
            fail("token --%s is missing from the %s block" % (src, where))
        out.append("%s--%s: %s;" % (indent, alias, table[src].strip()))
    return "\n".join(out)


def load_mark():
    """The 5c mark, taken from the app and made theme-aware.

    Two adaptations, both from the brand spec: the polygons MULTIPLY on a light
    ground and SCREEN on a dark one (the app only ever paints light, so it
    hardcodes multiply), and the ring-and-ascender takes currentColor so the
    ink follows the theme instead of staying near-black on a dark page.
    """
    src = read(MARK_SOURCE, "the app, for the 5c mark")
    i = src.find('<svg class="districtry-mark"')
    if i < 0:
        fail("the app no longer carries a districtry-mark SVG to lift")
    svg = src[i:src.index("</svg>", i) + len("</svg>")]
    n = svg.count('style="mix-blend-mode:multiply"')
    if n != 3:
        fail("expected the mark's 3 blended polygons, found %d" % n)
    svg = svg.replace('style="mix-blend-mode:multiply"', 'class="mk-blend"')
    if svg.count('stroke="#17161c"') != 2:
        fail("expected the mark's 2 ink strokes (ring + ascender)")
    svg = svg.replace('stroke="#17161c"', 'stroke="currentColor"')
    return svg.replace('<svg class="districtry-mark"', '<svg class="logo-mark"')


def instance_layer_count(tag):
    rel = INSTANCE_WORKSHEET.get(tag)
    if not rel:
        fail("no worksheet mapped for instance %r — add it to INSTANCE_WORKSHEET "
             "so its row can state a layer count" % tag)
    try:
        w = json.loads(read(os.path.join(REPO_ROOT, rel), "the %s worksheet" % tag))
    except ValueError as e:
        fail("%s is not valid JSON: %s" % (rel, e))
    n = len(w.get("layers") or [])
    if not n:
        fail("%s lists no layers" % rel)
    return n


def load_metros():
    try:
        manifest = json.loads(read(MANIFEST, "the fleet manifest"))
    except ValueError as e:
        fail("metros.json is not valid JSON: %s" % e)
    metros = manifest.get("metros")
    if not metros:
        fail("metros.json carries no metros")
    for m in metros:
        for key in ("tag", "landing_name", "blurb", "scope", "url", "bbox"):
            if not m.get(key):
                fail("metro %r has no %r — the landing page is generated from "
                     "these fields, so a new metro must carry them"
                     % (m.get("id", "?"), key))
    return metros


def oxford_join(items):
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return items[0] + " and " + items[1]
    return ", ".join(items[:-1]) + " and " + items[-1]


def render_notice():
    """The notice's markup, or nothing when NOTICE is None.

    A notice with an "only" condition ships hidden and the page's script shows
    it where the condition holds, so a reader it is not for never sees it flash.
    """
    if not NOTICE:
        return ""
    only = NOTICE.get("only")
    if only is not None and only not in NOTICE_ONLY:
        fail('NOTICE["only"] is %r; the page\'s script knows only %s.'
             % (only, ", ".join(NOTICE_ONLY)))
    link = NOTICE.get("link")
    cta = ""
    if link:
        cta = ('      <p class="notice-cta"><a href="%s">%s</a></p>\n'
               % (html.escape(link["href"], quote=True), html.escape(link["text"])))
    attrs = ' data-only="%s" hidden' % only if only else ""
    return (
        '    <aside id="notice" class="notice" aria-labelledby="notice-h"%s>\n'
        '      <p id="notice-h" class="notice-h">%s</p>\n'
        '      <p class="notice-b">%s</p>\n'
        '%s'
        '      <button type="button" id="notice-dismiss" aria-label="Dismiss this notice">&#x2715;</button>\n'
        '    </aside>\n'
        % (attrs, html.escape(NOTICE["heading"]), html.escape(NOTICE["body"]), cta)
    )


def notice_memory():
    """The notice's memory, as script: whether it was answered, and the answer.

    "android-test" keeps the answer with the maps' invitation to the Android
    test, so the key and the word are read from the engine's install-app
    block, the one copy of both, and this page and the maps cannot come to
    write two different things. With no "remember" the answer lasts for the
    page view, and nothing is stored.
    """
    remember = NOTICE.get("remember") if NOTICE else None
    if remember is None:
        return ("  /* Closing the notice lasts for this page view: it remembers nothing. */\n"
                "  function noticeAnswered() { return false; }\n"
                "  function noticeAnswer() {}\n")
    if remember not in NOTICE_REMEMBER:
        fail('NOTICE["remember"] is %r; the page\'s script knows only %s.'
             % (remember, ", ".join(NOTICE_REMEMBER)))
    src = read(INSTALL_APP, "the maps' install invitation")
    key = re.search(r'\bvar DST_INSTALL_INVITE_KEY = "([a-z-]+)";', src)
    word = re.search(r'\bvar DST_TEST_INVITE_ANSWERED = "([a-z-]+)";', src)
    if not key or not word:
        fail("NOTICE remembers its answer with the maps' invitation to the Android "
             "test, and engine/index.html/install-app.txt no longer declares "
             "DST_INSTALL_INVITE_KEY and DST_TEST_INVITE_ANSWERED as plain strings, "
             "so this page cannot know what to write.")
    if not re.search(r'\bvar DST_ANDROID_TEST_URL = "', src):
        fail("NOTICE remembers its answer with the maps' invitation to the Android "
             "test, and that test has ended: DST_ANDROID_TEST_URL in "
             "engine/index.html/install-app.txt is no longer an address. Change or "
             "retire NOTICE in the same change.")
    return (
        "  /* The notice's answer, kept with the maps' own invitation to the Android\n"
        "     test (engine/index.html/install-app.txt names the key and the word):\n"
        "     closing the notice or following its link writes the word, and an\n"
        "     answer on either page keeps both closed. localStorage, not a cookie,\n"
        "     so the word never leaves the browser. */\n"
        '  var NOTICE_KEY = "%s";\n'
        '  var NOTICE_ANSWERED = "%s";\n'
        "  function noticeAnswered() {\n"
        "    try { return window.localStorage.getItem(NOTICE_KEY) === NOTICE_ANSWERED; } catch (e) { return false; }\n"
        "  }\n"
        "  function noticeAnswer() {\n"
        "    try { window.localStorage.setItem(NOTICE_KEY, NOTICE_ANSWERED); } catch (e) { /* storage blocked: it shows again next visit */ }\n"
        "  }\n"
        % (key.group(1), word.group(1)))


def state_rows(metros):
    """Every state and DC, in alphabetical order, each paired with the fleet
    entry that answers there (or None) and whether that entry covers the whole
    state. Fails on an entry it cannot place and on two entries for one state,
    because the list has one row per state and either would drop a place from
    the front door without anyone noticing.
    """
    by_state = {}
    for m in metros:
        name = m["landing_name"]
        if name in US_STATES_AND_DC:
            state, whole = name, True
        else:
            state, whole = POSTAL_CODES.get(m["tag"].upper()), False
            if not state:
                fail("metros.json entry %r has a landing_name (%r) that is not a "
                     "state and a tag (%r) that is not a state's postal code, so "
                     "the state list has no row to put it on."
                     % (m.get("id", "?"), name, m["tag"]))
        if state in by_state:
            fail("metros.json has two entries for %s (%r and %r). The state list "
                 "has one row per state; decide how that row reads before adding "
                 "the second." % (state, by_state[state][0]["tag"], m["tag"]))
        by_state[state] = (m, whole)
    return [(s, ) + by_state.get(s, (None, None)) for s in US_STATES_AND_DC]


def render_states(metros):
    """One list of every state and DC, replacing two things that said the same
    thing twice: the row per live place beside the map, and the folded "not
    yet" list under it (2026-10-13). At thirteen places the rows ran to five
    lines of three and the not-yet list still had to be opened to see the rest,
    so a reader looking for their own state had to know which of the two to
    check. One alphabetical list answers both at a glance and stays the same
    shape at fifty. On a phone the page template folds it behind one toggle
    (the script after the list says why); these rows do not change for that.

    A covered state is a link with a filled square, its scope and its layer
    count (read from the instance's own worksheet). A state where only a city
    answers is a link with a half-filled square and says which city. Every
    other state is plain text with an empty square and, for a screen reader,
    the words "not yet", since the square alone says nothing to one.

    The count is bare in `.st-n` because the browser test reads that span as an
    integer; the word it counts sits beside it, so the visible text still reads
    "41 layers".
    """
    rows = []
    for state, m, whole in state_rows(metros):
        if m is None:
            rows.append(
                '        <li><span class="st st-off"><span class="st-dot" aria-hidden="true"></span>'
                '<span class="st-name">%s</span><span class="vh">, not yet</span></span></li>'
                % html.escape(state))
            continue
        scope = m["scope"] if whole else "%s only" % m["landing_name"]
        rows.append(
            '        <li><a class="st%s" href="%s">'
            '<span class="st-dot" aria-hidden="true"></span>'
            '<span class="st-name">%s</span>'
            '<span class="st-scope">%s &#183; <span class="st-n">%d</span>&nbsp;layers</span></a></li>'
            % ("" if whole else " st-part",
               html.escape(m["url"], quote=True),
               html.escape(state),
               html.escape(scope),
               instance_layer_count(m["tag"])))
    return "\n".join(rows)


def answer_phrase(metros):
    """How many places answer, said the way a reader counts them: "10 states
    and San Francisco". A city instance is named rather than counted as a state
    (California is not covered; San Francisco is), and DC is named rather than
    counted, because it is not a state.
    """
    states = [m for m in metros
              if m["landing_name"] in US_STATES_AND_DC and m["landing_name"] != DC]
    others = ["DC" if m["landing_name"] == DC else m["landing_name"]
              for m in metros if m not in states]
    parts = []
    if states:
        parts.append("%d state%s" % (len(states), "" if len(states) == 1 else "s"))
    parts += others
    one = len(states) + len(others) == 1
    return oxford_join(parts), ("answers" if one else "answer")


def question_pages(metros):
    """Every question page in the tree, as (tag, basename, label) per instance.

    A question page is any .html directly inside an instance folder that is not
    the app, one of the three sub-pages, or a redirect shell — the same rule
    build_sitemap.py uses to decide what is a topic page at all. So a new page
    joins the front door the day it ships and leaves it the day it goes.
    """
    found = []
    for m in metros:
        folder = os.path.join(REPO_ROOT, m["tag"])
        for path in sorted(glob.glob(os.path.join(folder, "*.html"))):
            base = os.path.basename(path)
            if base in NOT_A_LOOKUP:
                continue
            with open(path, encoding="utf-8") as f:
                head = f.read(8192)
            if IS_SHELL.search(head):
                continue
            if not re.search(r"<title>([^<]*)</title>", head):
                fail("%s/%s has no <title> in its first 8KB, so the front "
                     "door cannot label a link to it." % (m["tag"], base))
            found.append((m["tag"], base))
    return found


def render_asks(metros):
    """The question rows, and the audit that keeps the tables honest.

    WHY THIS BLOCK EXISTS AT ALL. The 2026-09-15 search audit found the front
    door linking NONE of the pages that answer a question in words, while
    /il/ward.html sat in the sitemap uncrawled, "URL is unknown" to Google.
    Everything about that page was already right: 200, self-canonical,
    index/follow, sitemapped, linked from seven Illinois pages. What it did not
    have was a link from the site's most-linked page. That is still what this
    block is for; only its shape changed.

    FOUR THINGS FAIL THE BUILD, and each is a way the tables could drift from
    the tree without anybody noticing: a discovered page no row claims, a row
    whose pages are all gone, an override naming a page that is not there, and
    two chips that come out with the same words. The last is the one this
    grouping exists to avoid — a chip's text is all the link says about where
    it points, so two alike means one of them is unlabelled.
    """
    pages = question_pages(metros)
    if not pages:
        fail("no question pages found in any instance folder — this block "
             "cannot be empty, and an empty one would ship silently.")
    order = {m["tag"]: i for i, m in enumerate(metros)}
    names = {m["tag"]: m["landing_name"] for m in metros}

    claimed, groups = set(), []
    for question, bases in QUESTION_ROWS:
        chips = []
        for tag, base in sorted(pages, key=lambda tb: (order[tb[0]], bases.index(tb[1])
                                                       if tb[1] in bases else 0)):
            if base not in bases:
                continue
            claimed.add((tag, base))
            topic = CHIP_TOPIC_BY_INSTANCE.get((tag, base)) or CHIP_TOPIC.get(base)
            if not topic:
                fail("%s/%s has no CHIP_TOPIC, so its link would read as a bare "
                     "place name. Add one in build_landing_page.py." % (tag, base))
            place = CHIP_PLACE.get((tag, base), names[tag])
            chips.append((place, topic, "/%s/%s" % (tag, base)))
        if not chips:
            fail("the question row %r matches no page in any instance — every "
                 "page it names has gone. Retire the row." % question)
        groups.append((question, chips))

    unclaimed = sorted(set(pages) - claimed)
    if unclaimed:
        fail("no question row claims %s. Every question page needs a row in "
             "QUESTION_ROWS, or the front door links it nowhere."
             % ", ".join("%s/%s" % tb for tb in unclaimed))
    for table, label in ((CHIP_TOPIC_BY_INSTANCE, "CHIP_TOPIC_BY_INSTANCE"),
                         (CHIP_PLACE, "CHIP_PLACE")):
        stale = sorted(k for k in table if k not in claimed)
        if stale:
            fail("%s names %s, which is not a question page in this tree."
                 % (label, ", ".join("%s/%s" % tb for tb in stale)))

    seen = {}
    for question, chips in groups:
        for place, topic, href in chips:
            text = "%s \u00b7 %s" % (place, topic)
            if text in seen:
                fail("two question links would both read %r (%s and %s). A "
                     "chip's text is the whole of what the link says about "
                     "where it points, so give one of them its own topic."
                     % (text, seen[text], href))
            seen[text] = href

    colours = question_colours()
    out = []
    for question, chips in groups:
        links = "\n".join(
            '          <li><a class="chip" href="%s">%s<span class="chip-topic">'
            ' &#183; %s</span></a></li>' % (html.escape(href, quote=True),
                                            html.escape(place), html.escape(topic))
            for place, topic, href in chips)
        # What the closed tile says is behind it. Counted from the chips, so
        # it moves the day a page is added and needs no edit here.
        places = len({href.split("/")[1] for _, _, href in chips})
        if question == TAIL_ROW:
            count = "%d page%s" % (len(chips), "" if len(chips) == 1 else "s")
        elif places == len(chips):
            count = "%d place%s" % (places, "" if places == 1 else "s")
        else:
            count = "%d pages in %d place%s" % (len(chips), places, "" if places == 1 else "s")
        style = (' style="--lc-l:%s;--lc-d:%s"' % colours[question]) if question in colours else ""
        out.append('      <details class="ask"%s open>\n'
                   '        <summary><span class="ask-sw" aria-hidden="true"></span>'
                   '<h3>%s</h3><span class="ask-n">%s</span></summary>\n'
                   '        <ul class="ask-chips">\n%s\n        </ul>\n'
                   '      </details>' % (style, html.escape(question), count, links))
    return "\n".join(out)


def question_colours():
    """{question: (light, dark)} for every question row that names a concept."""
    asked = [q for q, _ in QUESTION_ROWS]
    missing = [q for q in asked if q not in QUESTION_CONCEPT]
    if missing:
        fail("QUESTION_CONCEPT has no entry for %s. Name the concept whose map "
             "colour marks its tile, or None for a row that asks no one question."
             % ", ".join(repr(q) for q in missing))
    stale = sorted(q for q in QUESTION_CONCEPT if q not in asked)
    if stale:
        fail("QUESTION_CONCEPT names %s, which no question row asks."
             % ", ".join(repr(q) for q in stale))
    out = {}
    for question in asked:
        concept = QUESTION_CONCEPT[question]
        if concept is None:
            continue
        colour = concept_colour(concept)
        if not colour:
            fail("QUESTION_CONCEPT gives %r the concept %r, which has no line colour "
                 "in layer-concepts.json." % (question, concept))
        out[question] = colour
    return out


@functools.lru_cache(maxsize=None)
def layer_concepts():
    return json.loads(read(os.path.join(REPO_ROOT, "layer-concepts.json"),
                           "the layer concept table"))


@functools.lru_cache(maxsize=None)
def fleet_bounds():
    return palette.fleet_bounds([text for _, _, text in palette.targets()])


@functools.lru_cache(maxsize=None)
def concept_colour(concept):
    """(light, dark) for a concept: its map line colour and the dark twin every
    app draws it in, or None for a concept with no line colour."""
    line = (layer_concepts()["colors"].get(concept) or {}).get("line")
    if not line:
        return None
    return line.upper(), palette.dark_twin(line.upper(), fleet_bounds())


def concept_of(tag, layer_id):
    """The first concept, in file order, that names this app's layer: the rule
    generate_metro_files.py colours a layer under two concepts by. None for a
    layer in no concept, which keeps its own colour in the app (own_colour)."""
    for concept, apps in layer_concepts()["concepts"].items():
        ids = apps.get(tag)
        if ids == layer_id or (isinstance(ids, list) and layer_id in ids):
            return concept
    return None


def own_colour(tag, layer_id):
    """(light, dark) for a layer in no concept: the stroke colour its own
    registerLayer block draws it in, and the dark twin the app derives from
    that colour. A layer drawn by a factory, or with no literal stroke in its
    block, fails here rather than taking a colour the map does not draw."""
    text = read(os.path.join(REPO_ROOT, tag, "index.html"), "the %s app" % tag)
    marker = 'id: "%s",' % layer_id
    if text.count(marker) != 1:
        fail("%s/index.html registers %r %d time(s) as `%s`, so the front page "
             "cannot read the colour the map draws it in."
             % (tag, layer_id, text.count(marker), marker))
    start = text.index(marker)
    end = text.find("registerLayer(", start)
    m = re.search(r'style:\s*\{\s*color:\s*"(#[0-9A-Fa-f]{6})"',
                  text[start:end if end != -1 else len(text)])
    if not m:
        fail("%s/index.html: the %r registration carries no literal stroke "
             "colour, so the front page cannot read the colour the map draws it in."
             % (tag, layer_id))
    colour = m.group(1).upper()
    return colour, palette.dark_twin(colour, fleet_bounds())


def concept_layers(tag, concepts):
    """This app's layer ids for each concept it has, in the order given."""
    out = []
    for concept in concepts:
        ids = layer_concepts()["concepts"].get(concept, {}).get(tag)
        for layer_id in (ids if isinstance(ids, list) else [ids] if ids else []):
            if layer_id not in out:
                out.append(layer_id)
    return out


# ---------------------------------------------------------------------------
# THE WORKED EXAMPLE beside the address box (2026-10-21, the option Adam was
# shown as A). Measured on main that day, the page named no officeholder at
# all: it said what districtry answers and never showed an answer. So it shows
# one, for a well-known place, read the way the map reads it: each district
# from the boundary file its layer draws, and each person from the roster its
# card reads. Nothing below is typed in by hand except each place, its address,
# its point and the name of each body.
#
# SIX PLACES, A BUTTON FOR EACH, AND A DIFFERENT ONE FIRST ON EACH VISIT (Adam,
# the same day, choosing that over an example that changed place by itself
# every few seconds, which is hard to read and needs a pause button). The
# page's script starts on the place after the one it showed on the last visit,
# kept in localStorage under PLACE_KEY, or on one picked at random where
# nothing is kept. A press of a button is counted as example-place/<id>, which
# names one of these places and nothing about the reader, and the privacy page
# names both the count and the key. The buttons replaced a line under the
# address box that opened two other places' maps. With no script the page
# shows Chicago and no buttons, so it offers nothing that cannot work.
#
# THE DISTRICTS ARE MEASURED HERE AND THE NAMES ARE READ WHEN THE PAGE OPENS
# (Adam, the same day: "Why not have the example just be a real read of a
# fixed location instead of a static list that needs to be rebuilt?"). A
# first draft wrote the names into the page, so every weekly job rewriting
# one of its rosters had to regenerate the page too, and a gate failed any
# job that did not. The page's script now reads each roster the map's card
# reads (EXAMPLE_SCRIPT), so a name changes on the front page the moment it
# changes on the map, and no weekly job touches this page. The districts stay
# here because reading them live means downloading each layer's boundary
# file: measured that day (gzip at its default level), 501 KB for Chicago's
# five against 48 KB for the whole page, where Chicago's five rosters are
# 14 KB. A place's rosters are read only when that place is shown, so a visit
# pays for one place's: from 10.5 KB for San Francisco's to 61.9 KB for
# Madison's, whose county board roster holds every Wisconsin county's
# supervisors. Which
# district a fixed point is in changes only when a boundary file is rebuilt,
# which no weekly job does, and --check fails until this page is regenerated
# with it. What it costs: the names need the script (without it the cards
# show the bodies and districts and the link to the map), they are not in the
# page's text, and a roster that loses a seat shows "Not listed" to a reader,
# as the map's card does, rather than failing a build first.
#
# ONLY OFFICES WHOSE BOUNDARIES SHIP AS FILES. Chicago's ward and the Cook
# County Board answer at City Hall too, but the map reads both boundaries from
# the city's and the county's own servers when a reader clicks, and New York
# City's council districts ship only as a tile archive this generator does not
# read, so it cannot measure which district the point is in, and a district
# typed in here would be a claim nothing holds to the map. Each place's link
# opens those layers too (LINK_CONCEPTS).
#
# THE POINT MUST NOT SIT NEAR AN EDGE. The shipped boundaries are simplified,
# and a point a few metres from an edge can fall on one side here and on the
# other in a reader's browser, so the build fails when any example district's
# edge is nearer than EXAMPLE_EDGE_M. Measured on 2026-10-21 the nearest is
# New York City Hall's State Assembly district, 68 m from the point.
EXAMPLE_EDGE_M = 50
PLACE_KEY = "districtry-example-place"


def _chamber(layer, body, boundary, roster):
    """A card for a chamber the app registers through the engine's chamber
    factory, which keys its roster by the district number with its leading
    zeros dropped and prints the district with the registration's
    districtPrefix ("IL-7") or as "District 26" where it has none."""
    return {"layer": layer, "body": body, "boundary": boundary, "roster": roster,
            "chamber": True}


EXAMPLE_PLACES = [
    # Each place: its id (the button's, the panel's and the counted event's),
    # the button's words, the app's tag, the place and its address as the
    # panel names them, its point, and its cards in the order they show. A
    # card names its layer, the body its card names, its boundary file and
    # roster under the app's data/app, and, unless it is a chamber, the path to
    # the seat in that roster (read the way that app's own card reads it) and
    # the district as that card prints it. What the path reaches is one record
    # with a `name`, or a list of them where a district seats several; the
    # page's script reads both (EXAMPLE_SCRIPT).
    {"id": "chicago", "button": "Chicago", "tag": "il",
     "place": "Chicago City Hall", "address": "121 N. LaSalle St., Chicago",
     "point": (41.88372, -87.63238),
     "cards": [
         _chamber("congress", "U.S. House", "congress-districts.json", "congress-roster.json"),
         _chamber("il-senate", "Illinois Senate", "il-senate-districts.json",
                  "il-senate-members.json"),
         _chamber("il-house", "Illinois House", "il-house-districts.json",
                  "il-house-members.json"),
         {"layer": "ccbr", "body": "Cook County Board of Review",
          "boundary": "ccbr-districts.json", "roster": "ccbr-roster.json",
          "seat": lambda p: [str(p["DISTRICT"])],
          "label": lambda p: "District %s" % p["DISTRICT"]},
         # The boundary's 1-20 is the roster's key and is printed nowhere; a
         # seat is named by the Board's own number and letter, its longName.
         {"layer": "school-board", "body": "Chicago Board of Education",
          "boundary": "school-board-districts.json", "roster": "school-board-members.json",
          "seat": lambda p: [str(p["district"])],
          "label": lambda p: p["longName"]},
     ]},
    {"id": "madison", "button": "Madison", "tag": "wi",
     "place": "Wisconsin State Capitol", "address": "2 E. Main St., Madison",
     "point": (43.07468, -89.38421),
     "cards": [
         _chamber("us-house", "U.S. House", "congress-districts.json", "congress-roster.json"),
         _chamber("wi-senate", "Wisconsin Senate", "wi-senate-districts.json",
                  "wi-senate-members.json"),
         _chamber("wi-assembly", "Wisconsin Assembly", "wi-assembly-districts.json",
                  "wi-assembly-members.json"),
         {"layer": "county-board", "body": "Dane County Board",
          "boundary": "county-supervisory-districts.json", "roster": "county-board-members.json",
          "seat": lambda p: [p["SUPER_FIPS"]],
          "label": lambda p: "District %s" % p["SUPERID"]},
         # A district can seat more than one alderperson, so its seat is a list.
         {"layer": "aldermanic-district", "body": "Madison Common Council",
          "boundary": "aldermanic-districts.json", "roster": "wi-alderpersons.json",
          "seat": lambda p: [p["COUSUBFP"], "members", p["ALDERID"]],
          "label": lambda p: "District %d" % int(p["ALDERID"])},
     ]},
    {"id": "detroit", "button": "Detroit", "tag": "mi",
     "place": "Coleman A. Young Municipal Center", "address": "2 Woodward Ave., Detroit",
     "point": (42.32944, -83.04389),
     "cards": [
         _chamber("us-house", "U.S. House", "congress-districts.json", "congress-roster.json"),
         _chamber("mi-senate", "Michigan Senate", "mi-senate-districts.json",
                  "mi-senate-members.json"),
         _chamber("mi-house", "Michigan House", "mi-house-districts.json",
                  "mi-house-members.json"),
         {"layer": "county-commissioner", "body": "Wayne County Commission",
          "boundary": "mi-commissioner-districts.json", "roster": "mi-commissioner-members.json",
          "seat": lambda p: [p["CountyFIPS"], "districts", str(p["District"])],
          "label": lambda p: "District %s" % p["District"]},
         {"layer": "city-ward", "body": "Detroit City Council",
          "boundary": "mi-detroit-council-districts.json",
          "roster": "mi-detroit-council-members.json",
          "seat": lambda p: ["districts", str(p["District"])],
          "label": lambda p: "District %s" % p["District"]},
     ]},
    {"id": "nashville", "button": "Nashville", "tag": "tn",
     "place": "Tennessee State Capitol",
     "address": "600 Dr. Martin L. King Jr. Blvd., Nashville",
     "point": (36.16583, -86.78417),
     "cards": [
         _chamber("us-house", "U.S. House", "congress-districts.json", "congress-roster.json"),
         _chamber("tn-senate", "Tennessee Senate", "tn-senate-districts.json",
                  "tn-senate-members.json"),
         _chamber("tn-house", "Tennessee House", "tn-house-districts.json",
                  "tn-house-members.json"),
         # Nashville and Davidson County are one government, and the county's
         # commission districts are its Metro Council's, as the map's card says.
         {"layer": "county-commissioner", "body": "Metro Council",
          "boundary": "tn-commission-districts.json", "roster": "tn-commissioners.json",
          "seat": lambda p: [p["countyfips"], "districts", str(p["district"])],
          "label": lambda p: "District %s" % p["district"]},
     ]},
    {"id": "new-york", "button": "New York", "tag": "ny",
     "place": "New York City Hall", "address": "City Hall Park, Manhattan",
     "point": (40.71278, -74.00583),
     "cards": [
         _chamber("congress", "U.S. House", "congress-districts.json", "congress-roster.json"),
         _chamber("state-senate", "New York State Senate", "state-senate-districts.json",
                  "ny-senate-members.json"),
         _chamber("state-assembly", "New York State Assembly", "state-assembly-districts.json",
                  "ny-assembly-members.json"),
     ]},
    {"id": "san-francisco", "button": "San Francisco", "tag": "ca",
     "place": "San Francisco City Hall",
     "address": "1 Dr. Carlton B. Goodlett Pl., San Francisco",
     "point": (37.77927, -122.41924),
     "cards": [
         _chamber("congress", "U.S. House", "congress-districts.json", "congress-roster.json"),
         _chamber("ca-senate", "California Senate", "ca-senate-districts.json",
                  "ca-senate-members.json"),
         _chamber("ca-assembly", "California Assembly", "ca-assembly-districts.json",
                  "ca-assembly-members.json"),
         {"layer": "supervisor-district", "body": "Board of Supervisors",
          "boundary": "supervisor-districts.json", "roster": "sf-supervisor-members.json",
          "seat": lambda p: [str(p["district"])],
          "label": lambda p: "District %s" % p["district"]},
     ]},
]
# The kinds of district each place's link turns on besides its cards' own:
# here Chicago's ward and the Cook County Board, and New York City's council.
LINK_CONCEPTS = ("us-house", "state-senate", "state-house", "county-board",
                 "city-council", "school-board-district")


def _parts(geom):
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def _even_odd(x, y, rings):
    inside = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def _inside(geom, lng, lat):
    """The app's rule: even-odd within a Polygon, and inside ANY part of a
    MultiPolygon."""
    return any(_even_odd(lng, lat, rings) for rings in _parts(geom))


def _edge_metres(geom, lng, lat):
    """How far the point is from the nearest edge of the geometry, in metres,
    on a flat projection at the point's latitude (good to well under a metre
    over the few hundred metres this is asked about)."""
    kx, ky = 111320.0 * math.cos(math.radians(lat)), 110540.0
    best = float("inf")
    for rings in _parts(geom):
        for ring in rings:
            for i in range(len(ring) - 1):
                ax, ay = (ring[i][0] - lng) * kx, (ring[i][1] - lat) * ky
                bx, by = (ring[i + 1][0] - lng) * kx, (ring[i + 1][1] - lat) * ky
                dx, dy = bx - ax, by - ay
                span = dx * dx + dy * dy
                t = 0.0 if span == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / span))
                best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def coord(v):
    """A coordinate as the apps write one: five decimals, trailing zeros dropped."""
    return ("%.5f" % v).rstrip("0").rstrip(".")


@functools.lru_cache(maxsize=None)
def layer_codes():
    return json.loads(read(os.path.join(REPO_ROOT, "layer-codes.json"),
                           "the layer code table"))["codes"]


def app_link(metro, lat, lng, layer_ids):
    """A link that opens an app at a point with these layers on, written the
    way the app writes its own (#p= and the layers' permanent codes)."""
    codes = layer_codes()
    missing = [i for i in layer_ids if i not in codes]
    if missing:
        fail("layer-codes.json has no code for %s, so the front page cannot link "
             "%s with it on." % (", ".join(missing), metro["url"]))
    return "%s#p=%s,%s&l=%s" % (metro["url"], coord(lat), coord(lng),
                                ",".join(codes[i] for i in layer_ids))


@functools.lru_cache(maxsize=None)
def chamber_prefixes(tag):
    """{layer id: its districtPrefix, or None} for every chamber the app
    registers through the engine's chamber factory, read off the registration
    itself, so a chamber card prints its district as the map's card does."""
    src = read(os.path.join(REPO_ROOT, tag, "index.html"), "the %s app" % tag)
    out = {}
    for m in re.finditer(r"(?ms)^[ \t]*registerIlgaChamber\(\{(.*?)^[ \t]*\}\);", src):
        layer = re.search(r'\bid:\s*"([^"]+)"', m.group(1))
        if layer:
            prefix = re.search(r'\bdistrictPrefix:\s*"([^"]*)"', m.group(1))
            out[layer.group(1)] = prefix.group(1) if prefix else None
    return out


def place_cards(place):
    """[(spec, district label, seat path, (light, dark))] at one place's point,
    measured from the shipped boundary files. The colours are the ones the map
    draws each layer in. The names are not here: the page reads them from the
    rosters when it shows the place (EXAMPLE_SCRIPT), so this checks only that
    each roster is the list the map's card reads."""
    tag, (lat, lng) = place["tag"], place["point"]
    base = os.path.join(REPO_ROOT, tag, "data", "app")
    app = read(os.path.join(REPO_ROOT, tag, "index.html"), "the %s app" % tag)
    out = []
    for spec in place["cards"]:
        if spec.get("chamber"):
            prefixes = chamber_prefixes(tag)
            if spec["layer"] not in prefixes:
                fail("%s/index.html registers no chamber %r, so the example cannot "
                     "say how its card prints a district." % (tag, spec["layer"]))
            prefix = prefixes[spec["layer"]] or "District "
            seat = lambda p: [str(int(p["BASENAME"]))]
            label = lambda p, prefix=prefix: prefix + str(int(p["BASENAME"]))
        else:
            seat, label = spec["seat"], spec["label"]
        boundary = os.path.join(base, spec["boundary"])
        try:
            feats = json.loads(read(boundary, "an example boundary"))["features"]
        except (ValueError, KeyError) as e:
            fail("%s is not a feature collection: %s" % (boundary, e))
        hits = {}
        for f in feats:
            if _inside(f.get("geometry"), lng, lat):
                hits.setdefault(json.dumps(seat(f["properties"])), []).append(f)
        if len(hits) != 1:
            fail("%s: %s answers %d district(s) at %s (%s), not one. Pick a point "
                 "every example layer answers once."
                 % (spec["layer"], spec["boundary"], len(hits), place["place"],
                    ", ".join(sorted(hits)) or "none"))
        (key, found), = hits.items()
        edge = min(_edge_metres(f["geometry"], lng, lat) for f in found)
        if edge < EXAMPLE_EDGE_M:
            fail("%s: %s is %.0f m from the edge of its district in %s, nearer "
                 "than EXAMPLE_EDGE_M (%d m), so the map in a reader's browser "
                 "could answer the other side of it. Move the point."
                 % (spec["layer"], place["place"], edge, spec["boundary"], EXAMPLE_EDGE_M))
        try:
            roster = json.loads(read(os.path.join(base, spec["roster"]), "an example roster"))
        except ValueError as e:
            fail("%s/%s is not JSON: %s" % (tag, spec["roster"], e))
        if not isinstance(roster, dict):
            fail("%s/%s is not keyed by district, so the page could not find the seat "
                 "in it." % (tag, spec["roster"]))
        if ("data/app/" + spec["roster"]) not in app:
            fail("%s/index.html never reads data/app/%s, so the example would name "
                 "people from a list the map's card does not read."
                 % (tag, spec["roster"]))
        concept = concept_of(tag, spec["layer"])
        colour = concept_colour(concept) if concept else None
        out.append((spec, label(found[0]["properties"]), json.loads(key),
                    colour or own_colour(tag, spec["layer"])))
    return out


def place_layers(place):
    """The layers a place's link opens: its cards' own, then the
    LINK_CONCEPTS layers its cards leave out."""
    ids = [spec["layer"] for spec in place["cards"]]
    return ids + [i for i in concept_layers(place["tag"], LINK_CONCEPTS) if i not in ids]


# The places past the first, and each card's name line, ship hidden, so a
# reader with no script sees Chicago's bodies, districts and link to the map,
# and no button that cannot work. This runs right after the example. It shows
# the place after the one it showed on the last visit (PLACE_KEY), or one at
# random, shows the buttons, and reads a place's rosters when that place is
# first shown: each roster once, each seat named by the rule the officeholder
# tables print by: a name, or "Vacant", or "Not listed", never a guess. A seat
# that is a list of members names every member, and says how many of its seats
# are vacant. A seat whose number and letter the roster gives differently from
# the boundary (the Chicago Board of Education's, whose boundary numbers its
# seats 1-20) is not named at all. landing_test.mjs block 1i holds each name to
# its roster.
EXAMPLE_SCRIPT = """\
      <script>
      (function () {
        var box = document.currentScript.previousElementSibling;
        if (!box || !window.fetch) return;
        var PLACE_KEY = "%s";
        var pick = box.querySelector(".ex-pick");
        var panels = box.querySelectorAll(".ex-panel[data-place]");
        var buttons = box.querySelectorAll(".ex-pick button[data-place]");
        var order = [], byId = {}, shown = {}, lists = {}, i;
        for (i = 0; i < panels.length; i++) {
          order.push(panels[i].getAttribute("data-place"));
          byId[panels[i].getAttribute("data-place")] = panels[i];
        }
        if (!pick || !order.length) return;
        // The counter loads after this script, so a count waits for it, up to
        // ten seconds, as the address box's does.
        function trackEvent(path, tries) {
          if (window.goatcounter && typeof window.goatcounter.count === "function") {
            window.goatcounter.count({ path: path, title: path, event: true });
            return;
          }
          if ((tries || 0) < 40) setTimeout(function () { trackEvent(path, (tries || 0) + 1); }, 250);
        }
        function show(card, text, named) {
          var line = card.querySelector(".ex-name");
          line.textContent = text;
          line.className = named ? "ex-name" : "ex-name ex-none";
        }
        // One member: the name, "" for a seat the roster calls vacant, or null.
        function member(rec, pill) {
          if (!rec || typeof rec !== "object" || rec.withheld) return null;
          if (rec.subDistrict && pill !== "District " + rec.subDistrict) return null;
          var n = typeof rec.name === "string" ? rec.name.replace(/^\\s+|\\s+$/g, "") : "";
          if (n && n.toUpperCase() !== "VACANT") return n;
          return rec.vacant || n ? "" : null;
        }
        function name(card, list) {
          var path = JSON.parse(card.getAttribute("data-seat")), seat = list, k;
          for (k = 0; k < path.length; k++) {
            seat = seat && typeof seat === "object" &&
              Object.prototype.hasOwnProperty.call(seat, path[k]) ? seat[path[k]] : null;
          }
          var pill = card.querySelector(".ex-pill").textContent;
          var recs = Array.isArray(seat) ? seat : [seat], names = [], vacant = 0;
          for (k = 0; k < recs.length; k++) {
            var n = member(recs[k], pill);
            if (n) names.push(n);
            else if (n === "") vacant++;
          }
          if (!names.length) return show(card, vacant ? "Vacant" : "Not listed", false);
          if (vacant) names.push(vacant === 1 ? "a vacant seat" : vacant + " vacant seats");
          show(card, names.length === 1 ? names[0]
            : names.slice(0, -1).join(", ") + " and " + names[names.length - 1], true);
        }
        function fill(panel) {
          var cards = panel.querySelectorAll(".ex-card[data-roster]"), groups = {}, j;
          for (j = 0; j < cards.length; j++) {
            var url = cards[j].getAttribute("data-roster");
            cards[j].querySelector(".ex-name").hidden = false;
            (groups[url] = groups[url] || []).push(cards[j]);
          }
          Object.keys(groups).forEach(function (url) {
            lists[url] = lists[url] || fetch(url).then(function (r) {
              if (!r.ok) throw new Error("HTTP " + r.status);
              return r.json();
            });
            lists[url].then(function (list) {
              groups[url].forEach(function (card) { name(card, list); });
            }, function () {
              groups[url].forEach(function (card) { show(card, "Name didn't load", false); });
            });
          });
        }
        function choose(id) {
          var j;
          for (j = 0; j < order.length; j++) byId[order[j]].hidden = order[j] !== id;
          for (j = 0; j < buttons.length; j++) {
            buttons[j].setAttribute("aria-pressed",
              buttons[j].getAttribute("data-place") === id ? "true" : "false");
          }
          if (!shown[id]) {
            shown[id] = true;
            fill(byId[id]);
          }
        }
        var last = null, start;
        try { last = window.localStorage.getItem(PLACE_KEY); } catch (e) { /* storage blocked */ }
        i = order.indexOf(last);
        start = i >= 0 ? order[(i + 1) %% order.length]
                       : order[Math.floor(Math.random() * order.length)];
        try { window.localStorage.setItem(PLACE_KEY, start); } catch (e) { /* the next visit picks at random */ }
        choose(start);
        pick.hidden = false;
        pick.addEventListener("click", function (e) {
          var b = e.target;
          while (b && b !== pick && !(b.getAttribute && b.getAttribute("data-place"))) b = b.parentNode;
          if (!b || b === pick || b.getAttribute("aria-pressed") === "true") return;
          choose(b.getAttribute("data-place"));
          trackEvent("example-place/" + b.getAttribute("data-place"));
        });
      })();
      </script>
""" % PLACE_KEY


def render_example(metros):
    """The worked example: its place buttons, a panel for each place, and the
    script that picks the place and names its people."""
    by_tag = {m["tag"]: m for m in metros}
    try:
        outlines = json.loads(read(os.path.join(REPO_ROOT, "fleet-outlines.json"),
                                   "the fleet outlines"))["outlines"]
    except (ValueError, KeyError) as e:
        fail("fleet-outlines.json has no outlines: %s" % e)
    ids = [p["id"] for p in EXAMPLE_PLACES]
    if len(set(ids)) != len(ids) or not all(re.match(r"^[a-z][a-z-]*$", i) for i in ids):
        fail("EXAMPLE_PLACES ids must be distinct and lower-case words joined by "
             "hyphens, since each names a panel, a button and a counted event: %s" % ids)
    buttons, panels = [], []
    for n, place in enumerate(EXAMPLE_PLACES):
        m = by_tag.get(place["tag"])
        if not m:
            fail("EXAMPLE_PLACES puts %s in %r, which metros.json does not list as "
                 "live." % (place["place"], place["tag"]))
        lat, lng = place["point"]
        # A point outside the app's own outline would be handed on to another app.
        if not _inside(outlines.get(m["id"]), lng, lat):
            fail("EXAMPLE_PLACES puts %s at %s,%s, outside %s's own outline in "
                 "fleet-outlines.json, so that app would hand the reader on."
                 % (place["place"], lat, lng, m["id"]))
        items = []
        for spec, label, seat, colour in place_cards(place):
            items.append(
                '            <li class="ex-card" style="--lc-l:%s;--lc-d:%s" data-roster="%s" '
                'data-seat="%s"><span class="ex-body">%s</span>'
                '<span class="ex-name" hidden></span><span class="ex-pill">%s</span></li>'
                % (colour + (html.escape("%s/data/app/%s" % (place["tag"], spec["roster"]), quote=True),
                             html.escape(json.dumps(seat), quote=True), html.escape(spec["body"]),
                             html.escape(label))))
        buttons.append(
            '          <button type="button" data-place="%s" '
            'aria-controls="ex-%s" aria-pressed="%s">%s</button>'
            % (place["id"], place["id"], "true" if n == 0 else "false",
               html.escape(place["button"])))
        panels.append(
            '        <div class="ex-panel" id="ex-%s" data-place="%s"%s>\n'
            '          <h2 class="ex-place">Example: %s</h2>\n'
            '          <p class="ex-addr">%s</p>\n'
            '          <ul class="ex-cards">\n%s\n          </ul>\n'
            '          <a class="ex-open" href="%s">See every district here on the map'
            '<span aria-hidden="true">&#160;&#8594;</span></a>\n'
            '        </div>\n'
            % (place["id"], place["id"], "" if n == 0 else " hidden",
               html.escape(place["place"]), html.escape(place["address"]), "\n".join(items),
               html.escape(app_link(m, lat, lng, place_layers(place)), quote=True)))
    return (
        '      <aside class="example" aria-labelledby="ex-h">\n'
        '        <p id="ex-h" class="ex-eyebrow">What you get</p>\n'
        '        <div class="ex-pick" role="group" aria-label="Example places" hidden>\n'
        '%s\n'
        '        </div>\n'
        '%s'
        '      </aside>\n'
        % ("\n".join(buttons), "".join(panels))) + EXAMPLE_SCRIPT


DC = "District of Columbia"


def _landing_jsonld(metros, title, desc):
    """The root's structured data, built from the same metros list the page renders.

    Every instance page carries a WebSite + Organization graph; the root carried
    none, so the one page naming the whole fleet was the one page search engines
    were told nothing about. The ItemList is the instances in the order a reader
    sees them, so the graph and the visible list cannot disagree.
    """
    items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "name": m.get("landing_name") or m.get("label"),
            "url": m["url"],
        }
        for i, m in enumerate(metros)
    ]
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": CANONICAL + "#website",
                "url": CANONICAL,
                "name": "districtry",
                "description": desc,
                "inLanguage": "en-US",
                "sameAs": [REPO],
                "publisher": {"@id": CANONICAL + "#publisher"},
                "author": {"@id": CANONICAL + "#author"},
            },
            {
                "@type": "Organization",
                "@id": CANONICAL + "#publisher",
                "name": "Overberg",
                "url": "https://overberg.co",
            },
            # The footer has said "Built and run by Adam Overberg" since this
            # page shipped and the graph never carried it. Civic data about who
            # holds public office sits under the quality guidelines' highest
            # bar, and a named author with a URL is the cheapest part of it.
            {
                "@type": "Person",
                "@id": CANONICAL + "#author",
                "name": "Adam Overberg",
                "url": "https://overberg.co",
                # A contactable author, not just a named one. The quality guidelines ask how a reader reaches whoever stands behind the page, and a name plus a URL answers half of it.
                "email": "hello@overberg.co",
                "worksFor": {"@id": CANONICAL + "#publisher"},
            },
            {
                "@type": "ItemList",
                "name": "districtry instances",
                "itemListOrder": "https://schema.org/ItemListUnordered",
                "numberOfItems": len(items),
                "itemListElement": items,
            },
        ],
    }
    return json.dumps(graph, indent=2, ensure_ascii=False)


def render_metros_js(metros):
    """The address box's routing table: tag/name/url/bbox, embedded exactly
    like METRO_EXPLORERS is in each instance — enough for the client to
    replicate the same bbox test each app's own metro-portal handoff already
    runs, with nothing fetched for a point only one instance claims.

    Plus `outline`, the path to that instance's OWN published coverage ring,
    for the points where a rectangle cannot answer. It is emitted only where
    the file is actually in the tree (`<tag>/data/app/metro-outline.json`) —
    discovered, not listed, so a new statewide instance gets it the day it
    ships and the city instances, which publish no such ring, simply keep the
    bbox behaviour. The map in the iframe below already fetches these same
    files, so nothing new is published to make this work.

    And `whole`, whether the entry answers for its whole state, by the rule
    the state list under the map uses (state_rows): a landing_name that is a
    state. A map link's address names its state, and only a whole state's
    entry can be sent a place on that alone (namedState in the page)."""
    rows = []
    for m in metros:
        b = m["bbox"]
        rel = os.path.join(m["tag"], "data", "app", "metro-outline.json")
        outline = ("\n      outline: %s," % json.dumps(rel.replace(os.sep, "/"))
                   if os.path.isfile(os.path.join(REPO_ROOT, rel)) else "")
        rows.append(
            '    { id: %s, tag: %s, name: %s, url: %s, whole: %s,%s\n'
            '      bbox: { minLat: %s, maxLat: %s, minLng: %s, maxLng: %s } }'
            % (json.dumps(m["id"]), json.dumps(m["tag"]), json.dumps(m["landing_name"], ensure_ascii=False),
               json.dumps(m["url"]), json.dumps(m["landing_name"] in US_STATES_AND_DC), outline,
               json.dumps(b["minLat"]), json.dumps(b["maxLat"]), json.dumps(b["minLng"]), json.dumps(b["maxLng"]))
        )
    return ",\n".join(rows)


def build():
    metros = load_metros()
    tokens_css = read(TOKENS, "the design tokens")
    light = parse_token_block(tokens_css, ":root", TOKENS)
    dark = parse_token_block(tokens_css, '[data-theme="dark"]', TOKENS)

    favicon = read(FAVICON, "the brand mark").strip()
    if not favicon.startswith("<svg"):
        fail("favicon.svg does not start with <svg — is it still an SVG?")
    favicon_uri = "data:image/svg+xml," + urllib.parse.quote(favicon, safe="")

    fontface = read(FONTFACE, "the self-hosted font CSS").rstrip("\n")
    if "@font-face" not in fontface:
        fail("fonts/barlow-fontface.css carries no @font-face — regenerate it with "
             "`python3 scripts/build_fonts.py landing > fonts/barlow-fontface.css`")

    # The question leads and the brand trails — the composition the instance
    # pages carry (docs/DEV_PROCESS_ASSESSMENT.md, "The SEO surface"). Search
    # Console shows the demand is phrased as a question ("what district am i
    # in"), and a brand nobody is searching for yet cannot earn the click.
    title = "What district am I in? Find your district — districtry"
    desc = DESCRIPTION

    answer_count, answer_verb = answer_phrase(metros)
    # The map's lighter wash is drawn only for an area with a second, wider
    # outline, so the key names it only while one is live.
    two_tier = any((AREAS.get(m["tag"]) or {}).get("state_outline") for m in metros)
    key_wash = ('          <li><span class="sw sw-wash" aria-hidden="true"></span>'
                'Statewide layers only</li>\n' if two_tier else "")

    # The worked example beside the address box: a panel per place, its
    # districts measured here and its names read by the page when it shows that
    # place, so a roster refresh does not touch this page.
    example = render_example(metros)

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(title)s</title>
<meta name="description" content="%(desc)s" />
<link rel="canonical" href="%(canonical)s" />
<meta name="theme-color" content="%(brand)s" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<!-- The one web app manifest (scripts/build_manifests.py). The front door links
     it like every app does, so districtry installs as the same single app from
     here as from any state's map. -->
<link rel="manifest" href="/manifest.webmanifest" />
<meta name="apple-mobile-web-app-title" content="districtry" />
<meta name="robots" content="index, follow" />
<!-- Bing Webmaster Tools site ownership, added 2026-09-13. A PUBLIC ownership
     token like the IndexNow key, not a secret: it proves to Bing that whoever
     controls this page controls the site, and it is worthless to anyone else.
     Bing RE-CHECKS it, so removing this line un-verifies the site — it stays
     even after verification succeeds. The root page is the whole of it: a
     Webmaster Tools site at https://districtry.com/ covers every path under it,
     so no instance page needs a copy. -->
<meta name="msvalidate.01" content="71BE11A34018E35EFAE834F60C3965D5" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="districtry" />
<meta property="og:title" content="%(title)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:url" content="%(canonical)s" />
<meta property="og:image" content="%(canonical)sog-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="districtry — every district that covers a point, and who represents it." />
<meta property="og:locale" content="en_US" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="%(title)s" />
<meta name="twitter:description" content="%(desc)s" />
<meta name="twitter:image" content="%(canonical)sog-image.png" />
<!-- GoatCounter — cookieless page counts. One site for the whole fleet: every instance
     reports to districtry.goatcounter.com and the PATH tells them apart (/, /il, /ny,
     /ca). This page had no analytics at all until then, which made the fleet's front
     door the one page that could not be counted. -->
<script data-goatcounter="https://districtry.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
<script type="application/ld+json">
%(jsonld)s
</script>
<!-- GENERATED by scripts/build_landing_page.py from metros.json + the districtry
     tokens. Do NOT hand-edit: `--check` fails the build. Add a state to
     metros.json and regenerate. -->
<script>
/* FORWARD ANY OLD APP LINK, RENDER THE LANDING PAGE FOR EVERYTHING ELSE.

   Before R2.3 the Illinois app served from this root, and every share link and
   embed snippet it produced was built from the root URL — those are in other
   people's pages and bookmarks and cannot be recalled. A landing page that
   simply replaced the redirect stub would answer all of them with a page about
   Illinois instead of the map they asked for. So: a url carrying app
   parameters still forwards, carrying query AND hash exactly as the stub did.

   The two service-worker lines run on EVERY visit, forwarded or not, and stay
   narrow for the reasons R2.3 recorded: unregister only the registration scoped
   to this origin's root (an unfiltered sweep would kill the /il/ app's own
   worker), and delete only the exact legacy cache name (CacheStorage is
   per-ORIGIN, so a prefix sweep would wipe every instance's cached boundary files).

   This runs in <head> before the body paints, so a forwarded visit never
   flashes the landing page. */
(function () {
  try {
    if ("serviceWorker" in navigator && navigator.serviceWorker.getRegistrations) {
      navigator.serviceWorker.getRegistrations().then(function (regs) {
        regs.forEach(function (r) {
          if (r.scope === location.origin + "/") { r.unregister(); }
        });
      })["catch"](function () {});
    }
    if (window.caches && caches.delete) { caches.delete("district-explorer-shell-v51"); }
  } catch (e) { /* cleanup must never block a forward */ }

  var hash = location.hash, query = location.search;
  var isPermalink = /(?:^|[#&])(?:point|layers|zoom)=/.test(hash);
  var isTaggedShare = /[?&]utm_source=(?:share|embed)\\b/.test(query);
  if (isPermalink || isTaggedShare) {
    location.replace("%(forward)s" + query + hash);
  }
})();
</script>
<script>
%(themeboot)s
</script>
<script>
%(playapp)s
</script>
<style>
%(fontface)s

:root {
  color-scheme: light dark;
%(light)s
}
/* THE ATTRIBUTE TIER, and the guard on the media query beside it. Until
   2026-09-18 this page had NEITHER: it read the OS preference and nothing
   else, so it was the one page in the fleet that ignored a theme a reader had
   chosen inside an app — every instance sub-page, every county page, privacy,
   about, sponsorship and traffic have honoured that choice for weeks. It was
   also why the front door could not have its theme-colour fixed: a tag keyed
   on the stored choice would have contradicted a page painted from the OS.
   The `:not([data-theme="light"])` guard is what lets an explicit light choice
   win on a dark system; the attribute block is what lets an explicit dark
   choice win on a light one. */
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
  margin: 0; min-height: 100vh;
  background: var(--paper); color: var(--ink);
  font: 400 16px/1.55 var(--font-body);
  -webkit-font-smoothing: antialiased;
}
.shell { position: relative; min-height: 100vh; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 56px 24px 72px; }

/* The notice: a card at the top of the column, in the page's flow, above the
   masthead. It used to be a toast placed over the top-right of the window
   that faded after 15 seconds; the notice now asks the reader to do
   something and stays until it is closed, and a card that stays must not sit
   over the masthead's links. See NOTICE for who it is shown to. */
.notice {
  position: relative; margin: 0 0 24px;
  padding: 14px 44px 15px 18px;
  background: var(--brand-tint); border: 1px solid var(--brand-border);
  border-radius: var(--radius-card);
}
.notice[hidden] { display: none; }
.notice-h {
  margin: 0 0 5px; font: var(--font-heading-weight) 17px/1.25 var(--font-heading);
  color: var(--ink);
}
.notice-b { margin: 0; font-size: 14.5px; line-height: 1.5; color: var(--ink-3); max-width: 52em; }
/* The one thing in the notice to tap, on a 32px row so it clears WCAG 2.5.8's
   24px with room to spare on a phone; the colours are the footer support
   line's, on the same tint. */
.notice-cta { margin: 6px 0 0; }
.notice-cta a {
  display: inline-flex; align-items: center; min-height: 32px;
  font-size: 15px; font-weight: 600; color: var(--brand-600);
}
.notice-cta a:hover { color: var(--brand-700); }
.notice-cta a:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; border-radius: 4px; }
.notice #notice-dismiss {
  position: absolute; top: 9px; right: 10px; width: 26px; height: 26px;
  display: flex; align-items: center; justify-content: center; padding: 0;
  background: transparent; border: 1px solid transparent; border-radius: 999px;
  color: var(--muted); font: 400 13px/1 var(--font-body); cursor: pointer;
  transition: color .14s ease, border-color .14s ease, background .14s ease;
}
.notice #notice-dismiss:hover, .notice #notice-dismiss:focus-visible {
  background: var(--surface); border-color: var(--brand-border); color: var(--ink);
}

/* The masthead: the mark beside the wordmark, at a size the mark is actually
   drawn for, in a bar the sub-pages already wear. It was a 64px mark over a
   52px wordmark until 2026-09-18, which pushed the page's actual promise — the
   h1 — below the fold on a phone and left the brand saying it twice.

   The brand spec's blend rule is a REAL rule, not decoration: the three
   polygons read as overlapping translucent districts only if they multiply on
   a light ground and screen on a dark one; keep multiply on dark and they go
   muddy and near-black.

   There is no theme toggle here. The sub-pages carry one because they store a
   choice; this page stores none of its own (it reads the one an app stored,
   through the shared theme boot, and otherwise follows the operating system),
   and a control that looks like the sub-pages' but only lasts a page would be
   worse than none. */
header.mast {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding-bottom: 16px; margin-bottom: 32px; border-bottom: 1px solid var(--border);
}
.mast-brand { display: flex; align-items: center; gap: 10px; }
.logo-mark { width: 34px; height: 34px; flex: 0 0 auto; color: var(--ink); }
.logo-mark .mk-blend { mix-blend-mode: multiply; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .logo-mark .mk-blend { mix-blend-mode: screen; }
}
:root[data-theme="dark"] .logo-mark .mk-blend { mix-blend-mode: screen; }
.wordmark {
  font: var(--font-heading-weight) 28px/1 var(--font-heading);
  letter-spacing: .005em; color: var(--ink);
}
.mast-nav { margin-left: auto; display: flex; flex-wrap: wrap; gap: 2px; }
.mast-nav a {
  display: inline-flex; align-items: center; min-height: 32px; padding: 6px 11px;
  border-radius: var(--radius-btn); text-decoration: none;
  font-size: 14.5px; font-weight: 500; color: var(--ink-3);
  transition: background .14s ease, color .14s ease;
}
.mast-nav a:hover, .mast-nav a:focus-visible { background: var(--brand-tint); color: var(--ink); }
.mast-nav a:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; }

/* The h1 is the promise, and it is now the largest thing on the page. It used
   to be 26px grey under a 52px wordmark, so the biggest words on the fleet's
   front door were its own coined name — which nobody searches for — while the
   sentence that says what it does read as a caption. */
h1 {
  font: var(--font-heading-weight) 44px/1.08 var(--font-heading);
  color: var(--ink); margin: 0; max-width: 17em;
}
.lede { color: var(--ink-3); margin: 14px 0 0; max-width: 40em; font-size: 16.5px; }

.search-card {
  margin: 24px 0 0; padding: 18px 20px 20px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); box-shadow: var(--shadow-card);
}
/* A REAL label, not a span beside the box. The eyebrow said "Start with an
   address" while the input's aria-label said "Street address or ZIP", so a
   sighted reader and a screen-reader user were told two different things about
   one field. The visible words are now the accessible name. */
.search-label {
  display: block; font: var(--font-heading-weight) 13px/1 var(--font-heading);
  letter-spacing: .09em; text-transform: uppercase; color: var(--ink-3);
  margin-bottom: 10px;
}
.search-row { display: flex; gap: 10px; align-items: stretch; }
.search-input {
  flex: 1 1 auto; min-width: 0; padding: 12px 14px;
  font: 400 15px/1.3 var(--font-body); color: var(--ink);
  background: var(--paper); border: 1px solid var(--border);
  border-radius: var(--radius-btn);
}
.search-input::placeholder { color: var(--muted); }
.search-input:focus-visible {
  outline: 2px solid var(--brand-600); outline-offset: 1px;
  border-color: var(--brand-border);
}
/* THE LABEL COLOUR FLIPS WITH THE THEME, and it is a contrast fix rather than
   a preference. --brand-600 is #6d3fd1 in light (white on it: 6.40:1, passes
   AA) and #a78bfa in dark — white on THAT is 2.72:1, well under the 4.5:1 AA
   floor for 15px text. Dark ink on the same violet is 6.76:1, and on the
   --brand-700 hover (#c4b0ff) 9.64:1. This is the one place on the page where
   a token pair reverses its foreground, so it is stated rather than inherited. */
/* THE PADDING AND LINE-HEIGHT ARE THE TAP TARGET, and the desktop layout hides
   it. .search-row is align-items:stretch, so in a ROW the button inherits the
   input's 46px and looks fine; at the mobile breakpoint the row becomes a
   COLUMN, stretch governs width instead, and the height collapsed to the
   content box -- 15px of line plus 2px of border. That is under the 24px WCAG
   2.2 AA floor, on the page's only conversion action, on the 59%% of visits
   that are phones. Sized here to match the input exactly rather than merely to
   clear the floor: same 12px block padding, same 1.3 line-height, so both
   boxes compute to 46px and the pair cannot drift apart again. */
.search-button {
  flex: 0 0 auto; padding: 12px 22px;
  font: var(--font-heading-weight) 15px/1.3 var(--font-heading); color: #fff;
  background: var(--brand-600); border: 1px solid var(--brand-600);
  border-radius: var(--radius-btn); cursor: pointer; white-space: nowrap;
}
.search-button:hover { background: var(--brand-700); border-color: var(--brand-700); }
.search-button:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; }
.search-button:disabled { opacity: .6; cursor: default; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .search-button { color: var(--paper); }
}
:root[data-theme="dark"] .search-button { color: var(--paper); }
.search-help { margin: 12px 0 0; font-size: 13.5px; line-height: 1.5; color: var(--ink-3); }
.search-status { margin: 10px 0 0; font-size: 13.5px; line-height: 1.4; min-height: 0; }
.search-status.err { color: var(--error); }

/* THE WORKED EXAMPLE (2026-10-21): a place and who represents it there, one
   of six a reader can switch between, beside the address box on a wide screen
   and under it on a narrow one. Until then the page said what districtry
   answers and never showed an answer, so it read as a list of what is covered
   rather than as something to use. Each card carries its layer's map colour,
   light and dark, the way the question tiles do; the words on it stay in the
   page's ink, because a map colour is chosen to read as a line and not as
   text. */
.hero {
  display: grid; grid-template-columns: minmax(0, 1fr) 370px;
  gap: 36px; align-items: start;
}
.hero-main { min-width: 0; }
.example {
  margin-top: 4px; padding: 16px 14px 12px;
  background: var(--brand-tint); border: 1px solid var(--brand-border);
  border-radius: 14px;
}
.ex-eyebrow {
  margin: 0 4px 7px; font: var(--font-heading-weight) 12.5px/1 var(--font-heading);
  letter-spacing: .09em; text-transform: uppercase; color: var(--brand-700);
}
/* A button for each place, the one shown filled the way the address box's
   button is, so which place is showing does not rest on colour alone. They
   ship hidden and the page's script shows them, so a reader with no script is
   not offered buttons that cannot work. */
.ex-pick { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 4px 13px; }
.ex-pick[hidden] { display: none; }
.ex-pick button {
  min-height: 30px; padding: 5px 11px;
  font: 600 13.5px/1.2 var(--font-body); color: var(--ink);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 999px; cursor: pointer;
}
.ex-pick button:hover { border-color: var(--brand-600); }
.ex-pick button[aria-pressed="true"] {
  color: #fff; background: var(--brand-600); border-color: var(--brand-600); cursor: default;
}
.ex-pick button:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .ex-pick button[aria-pressed="true"] { color: var(--paper); }
}
:root[data-theme="dark"] .ex-pick button[aria-pressed="true"] { color: var(--paper); }
.ex-place {
  margin: 0 4px; font: var(--font-heading-weight) 21px/1.2 var(--font-heading);
  color: var(--ink);
}
.ex-addr { margin: 3px 4px 12px; font-size: 13px; line-height: 1.4; color: var(--ink-3); }
.ex-cards {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 7px; list-style: none; margin: 0; padding: 0;
}
.ex-card {
  --lc: var(--lc-l, var(--muted));
  display: grid; grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 12px; row-gap: 1px; align-items: center;
  padding: 8px 12px 9px;
  background: var(--surface); border: 1px solid var(--border);
  border-left: 3px solid var(--lc); border-radius: var(--radius-btn);
  box-shadow: var(--shadow-card);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .ex-card { --lc: var(--lc-d, var(--muted)); }
}
:root[data-theme="dark"] .ex-card { --lc: var(--lc-d, var(--muted)); }
.ex-body {
  grid-column: 1; font-size: 12.5px; line-height: 1.3; font-weight: 600;
  color: var(--ink-3);
}
.ex-body::before {
  content: ""; display: inline-block; width: 8px; height: 8px; margin-right: 7px;
  border-radius: 50%%; background: var(--lc); vertical-align: 1px;
}
.ex-name {
  grid-column: 1; min-width: 0; min-height: 1.2em; overflow-wrap: anywhere;
  font: var(--font-heading-weight) 19px/1.2 var(--font-heading); color: var(--ink);
}
.ex-name.ex-none { font-weight: 400; color: var(--muted); }
.ex-pill {
  grid-column: 2; grid-row: 1 / span 2;
  padding: 6px 10px; border-radius: 999px; white-space: nowrap;
  font: 600 13px/1 var(--font-body); font-variant-numeric: tabular-nums;
  color: var(--ink); background: var(--paper);
  background: color-mix(in srgb, var(--lc) 14%%, var(--surface));
}
.ex-open {
  display: inline-flex; align-items: center; min-height: 32px; margin: 6px 4px 0;
  font-size: 14px; font-weight: 600; color: var(--brand-600); text-decoration: none;
}
.ex-open:hover { color: var(--brand-700); text-decoration: underline; }
.ex-open:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; border-radius: 4px; }

/* Section headings read as headings, in sentence case. Until 2026-10-21 they
   were 14px grey capitals, which is how a form or a printed report marks its
   parts, and the page read like one. */
h2 {
  font: var(--font-heading-weight) 27px/1.15 var(--font-heading);
  color: var(--ink); margin: 60px 0 14px; text-wrap: balance;
}
.section-note {
  margin: -2px 0 14px; font-size: 13.5px; line-height: 1.5;
  color: var(--muted); max-width: 52em;
}

/* The coverage map and the state list are ONE section, because they answer one
   question. They were two — a map under "Where it answers today", a pill row
   under "Or choose a place" — which asked a reader to find their state twice.

   The map keeps its iframe. It is a real Leaflet map: its areas are clickable,
   pointing at one names it and says how much of it is covered, and it is
   generated and drift-gated on its own (scripts/build_coverage_map.py).

   THE MAP TAKES THE FULL WIDTH AND THE LIST SITS UNDER IT. Side by side was
   tried first and the map cannot afford it: the fleet's bounds run from San
   Francisco to New York, so a narrower frame zooms the whole country down.

   ONE LIST OF EVERY STATE AND DC, SINCE 2026-10-13. A row per live place beside
   the map and a folded "not yet" list under it said the same thing twice, and
   at thirteen places the rows ran five deep while the rest of the country was
   still behind a click. The list flows down four columns on a wide screen and
   two on a phone; its squares are the map's own key (filled: answers here;
   half: one city only; empty: not yet), stated once in the line above it. */
.coverage {
  display: flex; flex-direction: column; gap: 14px;
  padding: 14px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); box-shadow: var(--shadow-card);
}
/* The frame follows the country's own shape rather than a fixed height: at a
   fixed 424px a phone drew the fleet as a strip across the middle of a tall
   box of sea and Canada. Twice as wide as it is tall is about what the lower 48
   need, capped on a wide screen and floored on a phone so the map is never a
   sliver. */
.coverage-frame {
  display: block; width: 100%%; height: auto; aspect-ratio: 2 / 1;
  min-height: 210px; max-height: 400px;
  border: 1px solid var(--border); border-radius: var(--radius-btn);
  background: var(--paper);
}
.cov-head {
  display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between;
  gap: 6px 18px; padding: 2px 4px 0;
}
.cov-count { margin: 0; font-size: 14px; line-height: 1.45; color: var(--ink-3); }
.cov-count strong {
  font: var(--font-heading-weight) 17px/1.3 var(--font-heading); color: var(--ink);
}
.cov-key {
  display: flex; flex-wrap: wrap; gap: 4px 16px; list-style: none; margin: 0; padding: 0;
  font-size: 12.5px; line-height: 1.5; color: var(--muted);
}
.cov-key li { display: flex; align-items: center; gap: 6px; }
/* The squares. --data-500 is the map's own fill colour, so the key, the list
   and the outlines are one vocabulary. The empty square takes --muted rather
   than --faint: it is the only thing that marks a state as not covered, so it
   has to be visible (1.4.11), and --faint is not. */
.sw, .st-dot {
  flex: 0 0 auto; width: 10px; height: 10px; border-radius: 2px;
  background: var(--data-500); border: 1px solid var(--data-500);
}
.sw-wash { background: var(--data-tint); }
.sw-off, .st-off .st-dot { background: none; border-color: var(--muted); }
.st-part .st-dot { background: linear-gradient(135deg, var(--data-500) 50%%, transparent 50%%); }
.states {
  list-style: none; margin: 0; padding: 0;
  columns: 4 190px; column-gap: 18px;
}
/* The fold is a phone's alone: on a wider screen the toggle is not drawn and
   the list stays open (the script under the list holds it open). */
.states-toggle { display: none; }
.states-toggle::-webkit-details-marker { display: none; }
.states li { break-inside: avoid; }
.st {
  display: grid; grid-template-columns: 10px minmax(0, 1fr); column-gap: 9px;
  align-items: baseline; min-height: 28px; padding: 4px 6px;
  border-radius: var(--radius-btn);
}
a.st { text-decoration: none; color: var(--ink); transition: background .14s ease; }
a.st:hover, a.st:focus-visible { background: var(--brand-tint); }
a.st:focus-visible { outline: 2px solid var(--brand-600); outline-offset: -2px; }
.st-name { font: var(--font-heading-weight) 16px/1.25 var(--font-heading); }
.st-scope {
  grid-column: 2; font-size: 12px; line-height: 1.3; color: var(--muted);
  font-variant-numeric: tabular-nums;
}
/* --muted measures 4.08:1 on the light hover tint, under the 4.5 floor, so the
   scope line darkens to --ink-3 with the row (validate_contrast.py holds the
   pair). */
a.st:hover .st-scope, a.st:focus-visible .st-scope { color: var(--ink-3); }
.st-off { color: var(--muted); }
.st-off .st-name { font: 400 15px/1.25 var(--font-heading); }
.vh {
  position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip-path: inset(50%%); white-space: nowrap;
}

/* THE QUESTION ROWS. One row per question, the places that answer it as chips.
   The heading carries the question once where six place headings used to carry
   it six times, and the chip carries the place AND its own topic — a link
   reading only "Illinois" says nothing about where it goes, which is the test
   Google's link guidance sets and the reason render_asks refuses to emit two
   chips alike. They are a <ul> because they are a list of places: a screen
   reader announces how many answer each question and can jump the lot. */
/* EACH QUESTION IS A TILE THAT OPENS TO ITS PLACES. As rows, the chips took
   36%% of this page on a computer and 52%% on a phone, measured 2026-10-21, and
   grew by one chip per question with every state that went live. Closed, the
   nine questions sit in one block of tiles, each marked in the map colour of
   what it asks about and saying how many places answer it. They ship OPEN and
   the script under them folds them, the state list's rule, so a reader with
   no script gets every link. The cost is a second tap to reach a question
   page. A tile opens where it stands rather than across the row, because a
   tile spanning the row would leave a hole wherever it did not start one. */
.asks {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px; align-items: start;
}
.ask {
  --lc: var(--lc-l, var(--muted));
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); box-shadow: var(--shadow-card);
  transition: border-color .14s ease;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .ask { --lc: var(--lc-d, var(--muted)); }
}
:root[data-theme="dark"] .ask { --lc: var(--lc-d, var(--muted)); }
.ask:hover { border-color: var(--brand-border); }
.ask > summary {
  display: grid; grid-template-columns: 30px minmax(0, 1fr) 14px;
  column-gap: 12px; row-gap: 2px; align-items: center;
  min-height: 66px; padding: 13px 14px; list-style: none; cursor: pointer;
  border-radius: var(--radius-card);
}
.ask > summary::-webkit-details-marker { display: none; }
.ask > summary:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; }
.ask-sw {
  grid-row: 1 / span 2; width: 30px; height: 30px; border-radius: 7px;
  border: 2px solid var(--lc); background: var(--surface);
  background: color-mix(in srgb, var(--lc) 16%%, var(--surface));
}
.ask h3 {
  margin: 0; font: var(--font-heading-weight) 17.5px/1.2 var(--font-heading);
  color: var(--ink);
}
.ask-n { grid-column: 2; font-size: 12.5px; line-height: 1.3; color: var(--muted); }
.ask > summary::after {
  content: ""; grid-column: 3; grid-row: 1 / span 2; justify-self: center;
  width: 8px; height: 8px;
  border-right: 2px solid var(--ink-3); border-bottom: 2px solid var(--ink-3);
  transform: translateY(-2px) rotate(45deg); transition: transform .14s ease;
}
.ask[open] > summary::after { transform: translateY(2px) rotate(-135deg); }
.ask-chips {
  display: flex; flex-wrap: wrap; gap: 7px; list-style: none;
  margin: 0; padding: 0 14px 14px 56px;
}
.chip {
  display: inline-flex; align-items: center; min-height: 36px; padding: 7px 13px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 999px;
  text-decoration: none; font-size: 14px; line-height: 1.2; font-weight: 500;
  color: var(--brand-600); white-space: nowrap;
  transition: background .14s ease, border-color .14s ease;
}
.chip:hover, .chip:focus-visible { border-color: var(--brand-border); background: var(--brand-tint); }
.chip:focus-visible { outline: 2px solid var(--brand-600); outline-offset: 2px; }
/* `pre`, because a chip is a flex box and its topic a flex item, and a flex
   item drops the space it starts with: every chip read "Illinois· U.S. House"
   on screen while its text said "Illinois · U.S. House". */
.chip-topic { color: var(--ink-3); font-weight: 400; white-space: pre; }

.does { display: grid; grid-template-columns: repeat(auto-fit, minmax(255px, 1fr)); gap: 22px 26px; }
.does > div { padding-top: 13px; border-top: 2px solid var(--border); }
/* These were <b> until 2026-09-18, so the three things the product claims to do
   were not headings and appeared in no outline of the page. */
.does h3 {
  margin: 0 0 5px; font: var(--font-heading-weight) 18px/1.25 var(--font-heading);
  color: var(--ink);
}
.does p { margin: 0; font-size: 14px; line-height: 1.55; color: var(--ink-3); }

/* Focus-only, and the pair validate_contrast.py already measures: --paper on
   --ink, 16.08:1 light and 15.36:1 dark. The app and the twelve sub-pages have
   carried one since the rebrand; these pages did not, so a keyboard reader met
   a different site depending on which page they landed on. */
.skip-link {
  position: absolute; left: -9999px; top: 0;
  background: var(--ink); color: var(--paper);
  padding: 10px 16px; z-index: 10; border-radius: 0 0 6px 0;
}
.skip-link:focus { left: 0; }

/* The footer was five stacked paragraphs saying the disclaimer twice. Three
   columns, each answering a different reader: what this is, how to keep it
   running, and where else to go. */
footer {
  margin-top: 52px; padding-top: 24px; border-top: 1px solid var(--border);
  font-size: 13.5px; color: var(--ink-3);
}
.foot-grid {
  display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) 168px;
  gap: 24px 34px; align-items: start;
}
footer a { color: var(--brand-600); }
footer a:hover { color: var(--brand-700); }
footer p { margin: 0 0 10px; line-height: 1.55; }
footer p:last-child { margin-bottom: 0; }
.foot-name {
  font: var(--font-heading-weight) 20px/1 var(--font-heading);
  color: var(--ink); display: block; margin-bottom: 10px;
}
/* The support line is the one thing in this footer a reader is being ASKED to
   act on, so it does not sit in the link list where it reads as a seventh
   equal item. It was exactly that before: one of six links, in an app footer,
   on a page that never mentioned funding at all. */
footer .support {
  padding: 13px 15px; background: var(--brand-tint); border: 1px solid var(--brand-border);
  border-radius: var(--radius-card); color: var(--ink-3);
}
footer .support b { color: var(--ink); }
.foot-links { list-style: none; margin: 0; padding: 0; }
/* 24px minimum target, WCAG 2.5.8: these are a LIST of links, which is the
   shape that failed three surfaces when page_consistency_test.mjs began
   sweeping for it, so the Inline exception does not apply. A column gives each
   one its own row and the wrapped-row collision the flat row had cannot
   happen. */
.foot-links a { display: block; padding: 5px 0; min-height: 24px; line-height: 1.4; text-decoration: none; }
.foot-links a:hover, .foot-links a:focus-visible { text-decoration: underline; }

@media (max-width: 860px) {
  .hero { grid-template-columns: minmax(0, 1fr); gap: 28px; }
  .example { margin-top: 0; }
  .asks { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .wrap { padding: 28px 18px 56px; }
  header.mast { gap: 8px; margin-bottom: 26px; }
  .wordmark { font-size: 25px; }
  h1 { font-size: 31px; }
  h2 { font-size: 24px; margin-top: 44px; }
  .search-row { flex-direction: column; }
  .notice { margin-bottom: 22px; }
  .example { padding: 14px 12px 10px; }
  .states { columns: 2; column-gap: 10px; }
  .states-toggle {
    display: flex; align-items: center; justify-content: space-between;
    min-height: 44px; padding: 0 6px; list-style: none; cursor: pointer;
    border-top: 1px solid var(--border);
    font: var(--font-heading-weight) 16px/1.25 var(--font-heading); color: var(--ink);
  }
  .states-toggle::after {
    content: ""; width: 8px; height: 8px; margin-right: 4px;
    border-right: 2px solid var(--ink-3); border-bottom: 2px solid var(--ink-3);
    transform: translateY(-2px) rotate(45deg); transition: transform .14s ease;
  }
  .states-box[open] > .states-toggle::after { transform: translateY(2px) rotate(-135deg); }
  .states-toggle:focus-visible { outline: 2px solid var(--brand-600); outline-offset: -2px; border-radius: var(--radius-btn); }
  .states-box[open] > .states { margin-top: 8px; }
  /* One column, and the chips grow: a row of links is the shape WCAG 2.5.8
     catches, and 36px tall chips 7px apart are inside each other's 24px
     circle once they wrap on a narrow screen. */
  .asks { grid-template-columns: minmax(0, 1fr); }
  .ask-chips { padding-left: 14px; }
  .chip { min-height: 40px; padding: 9px 14px; }
  .foot-grid { grid-template-columns: minmax(0, 1fr); gap: 20px; }
}
</style>
</head>
<body>
  <a href="#page-main" class="skip-link">Skip to content</a>
  <div class="shell">
    <div class="wrap">
%(notice)s    <header class="mast">
      <div class="mast-brand">
        %(mark)s
        <span class="wordmark">districtry</span>
      </div>
      <nav class="mast-nav" aria-label="Site">
        <a href="about.html">About</a>
        <a href="privacy.html">Privacy</a>
        <a href="https://github.com/ThursdaysFamous/districtry" target="_blank" rel="noopener">Source</a>
      </nav>
    </header>

    <main id="page-main">
    <div class="hero">
      <div class="hero-main">
        <h1>Every district that covers a point, and who represents it.</h1>
        <p class="lede">%(desc)s</p>

        <div class="search-card">
          <label class="search-label" for="search-input">Start with an address</label>
          <form id="search-form" class="search-row">
            <input type="text" id="search-input" class="search-input" name="q"
                   placeholder="Street address or ZIP" autocomplete="off" />
            <button type="submit" id="search-button" class="search-button">Show districts</button>
          </form>
          <p class="search-help">districtry opens the map that covers the point. %(answer_count)s
             %(answer_verb)s today — an address anywhere else says so instead of guessing.</p>
          <p id="search-status" class="search-status" role="status" aria-live="polite"></p>
        </div>
      </div>
%(example)s    </div>

    <h2>Where it answers today</h2>
    <div class="coverage">
      <iframe class="coverage-frame" src="coverage-map.html"
              title="Map of the areas districtry covers today"
              loading="lazy"></iframe>
      <div class="cov-head">
        <p class="cov-count"><strong>%(answer_count)s %(answer_verb)s today.</strong>
          Pick one to open its map.</p>
        <ul class="cov-key" aria-label="Key">
          <li><span class="sw sw-on" aria-hidden="true"></span>Answers here</li>
%(key_wash)s          <li><span class="sw sw-off" aria-hidden="true"></span>Not yet</li>
        </ul>
      </div>
      <details class="states-box" open>
        <summary class="states-toggle">All 50 states and DC</summary>
        <ul class="states">
%(states)s
        </ul>
      </details>
      <script>
      /* Folded on a phone, open everywhere else (Adam, 2026-10-13): fifty-one
         rows under a small map are a long scroll to the questions below them.
         It ships open, so a reader with no script still gets the list, and this
         runs right after the element, so a phone never paints it open first.
         Widening a folded page opens it again, since the toggle is hidden there. */
      (function () {
        var box = document.currentScript.previousElementSibling;
        if (!window.matchMedia || !box) return;
        var phone = window.matchMedia("(max-width: 560px)");
        box.open = !phone.matches;
        var widen = function () { if (!phone.matches) box.open = true; };
        if (phone.addEventListener) phone.addEventListener("change", widen);
        else if (phone.addListener) phone.addListener(widen);
      })();
      </script>
    </div>

    <h2>Or start from a question</h2>
    <p class="section-note">One page per question and place: the answer in prose, the roster as it
       stood on the day it was checked, and a link that opens the map with the right layers on.</p>
    <div class="asks">
%(asks)s
    </div>
    <script>
    /* The question tiles ship open, so a reader with no script still gets
       every link, and fold here, right after they are parsed, so no screen
       paints them open first. */
    (function () {
      var asks = document.currentScript.previousElementSibling;
      if (!asks) return;
      var tiles = asks.querySelectorAll("details.ask");
      for (var i = 0; i < tiles.length; i++) tiles[i].open = false;
    })();
    </script>

    <h2>What it does</h2>
    <div class="does">
      <div>
        <h3>Every district, not the one you asked for</h3>
        <p>Pick a point and it reports every civic boundary that contains it at once —
           legislative, judicial, policing, schools, and the local special districts most
           tools leave out.</p>
      </div>
      <div>
        <h3>The people, where they can be verified</h3>
        <p>It names who holds each seat when a published roster says so, and links the
           official body when none does. It never guesses an officeholder.</p>
      </div>
      <div>
        <h3>It shows its work</h3>
        <p>Every layer names the publisher its boundary came from and where its names come
           from. What nobody publishes is listed too, rather than quietly missing.</p>
      </div>
    </div>
    </main>

    <footer>
      <div class="foot-grid">
        <div>
          <span class="foot-name">districtry</span>
          <p>An independent, unofficial civic reference built from official published
             boundaries and rosters. It is not a government service, not affiliated with or
             endorsed by any government agency, and not a legal record of any district line.
             Where no verifiable roster exists it links the official body instead of guessing.
             Seals shown beside a county belong to that county and say whose district you are
             looking at, not who endorses this site.</p>
          <p>Built and run by <a href="https://overberg.co/" rel="author noopener" target="_blank">Adam
             Overberg</a>. Open source — the code under
             <a href="https://github.com/ThursdaysFamous/districtry/blob/main/LICENSE"
                target="_blank" rel="noopener">Apache&nbsp;2.0</a> and the data under
             <a href="https://github.com/ThursdaysFamous/districtry/blob/main/LICENSE-DATA.md"
                target="_blank" rel="noopener">ODbL&nbsp;1.0</a>. Fork it for your own state.
             Each place names its own sources on its sources page; corrections and anything
             that looks wrong: <a href="mailto:hello@overberg.co">hello@overberg.co</a>.</p>
        </div>
        <p class="support"><b>This project is unfunded and run at personal cost.</b> If it is useful
           to you, <a href="https://github.com/sponsors/ThursdaysFamous" target="_blank" rel="noopener">sponsoring
           it on GitHub</a> keeps the rosters current — that is where the ongoing work is. Sponsorship
           buys no placement and no influence over any answer here; the
           <a href="sponsorship.html">sponsorship policy</a> says so in detail.</p>
        <ul class="foot-links">
          <li><a href="about.html">About</a></li>
          <li><a href="privacy.html">Privacy</a></li>
          <li><a href="sponsorship.html">Sponsorship</a></li>
          <li><a href="traffic.html">Traffic</a></li>
          <li><a href="https://overberg.co/why/" target="_blank" rel="noopener">Why this exists</a></li>
          <li><a href="https://github.com/ThursdaysFamous/districtry" target="_blank" rel="noopener">Source on GitHub</a></li>
        </ul>
      </div>
    </footer>
    </div>
  </div>
<script>
(function () {
  /* ---------- the notice: shown where it applies, closed on request ----------
     A notice with data-only ships hidden (render_notice), and this shows it
     where its condition holds. "android": a browser on Android, not an
     installed copy, which is display-mode standalone (the Play app's own
     window reports it too), and not a window the Play app's mark has set
     (engine/shared/play-app.txt, run in the head). Not once it has been
     answered, which noticeAnswered says (notice_memory). */
%(notice_memory)s  var notice = document.getElementById("notice");
  if (notice) {
    var only = notice.getAttribute("data-only");
    var answered = noticeAnswered();
    if (only === "android") {
      var installed = !!((window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
        window.navigator.standalone === true);
      if (/\\bAndroid\\b/.test(window.navigator.userAgent || "") && !installed &&
          !document.documentElement.classList.contains("dst-play-app") && !answered) {
        notice.hidden = false;
      }
    } else if (!only && !answered) {
      notice.hidden = false;
    }
    var dismiss = document.getElementById("notice-dismiss");
    if (dismiss) dismiss.addEventListener("click", function () {
      /* A keyboard reader's focus would drop to <body> with the button gone,
         so it moves on to the masthead's first link, the next thing in the
         tab order. A tap leaves focus alone. */
      var keyboard = false;
      try { keyboard = dismiss.matches(":focus-visible"); } catch (e) { /* older browser */ }
      notice.hidden = true;
      noticeAnswer();
      var next = document.querySelector(".mast-nav a");
      if (keyboard && next) next.focus();
    });
    /* Following the link answers it too; the browser follows it either way. */
    var follow = notice.querySelector(".notice-cta a");
    if (follow) follow.addEventListener("click", noticeAnswer);
  }

  /* ---------- address box: geocode, then route to the covered instance ----------
     Same provider (Photon, unbounded) and the same bbox test each instance's
     own metro-portal ENGINE block already runs for its sibling-metro fallback
     — see this file's module docstring. Takes the first Photon result (of up
     to 5, ranked) that actually falls inside a covered bbox, so a bare place
     name ambiguous across states still has a fair shot at landing correctly
     rather than wherever result #1 happened to be. */
  var METROS = [
%(metros_js)s
  ];

  function metrosClaiming(lat, lng) {
    var out = [];
    for (var i = 0; i < METROS.length; i++) {
      var b = METROS[i].bbox;
      if (lat < b.minLat || lat > b.maxLat || lng < b.minLng || lng > b.maxLng) continue;
      out.push(METROS[i]);
    }
    return out;
  }

  /* THE FALLBACK, AND WHY IT IS ONLY A FALLBACK. Nearest bbox CENTRE was the
   * whole of this function until Michigan shipped. It is wrong wherever a
   * rectangle claims ground its instance does not serve, and Lake Michigan
   * makes that ordinary rather than exotic: Michigan's counties are
   * water-inclusive, so its box reaches Wisconsin's longitudes, and
   * Wisconsin's box covers Michigan's entire Upper Peninsula. Measured over 37
   * real places, nearest-centre misroutes 7 — Marquette, Houghton, Ironwood,
   * Iron Mountain and Menominee MI to /wi/, Sister Bay WI to /mi/, Dubuque IA
   * to /wi/. Smallest bbox AREA was tried as a replacement and is NOT better:
   * also 7, just wrong at different places (it fixes Sister Bay and Dubuque,
   * and breaks Rock Island and Escanaba). No rectangle rule can separate
   * states that interlock across a lake. */
  function nearestByCentre(cands) {
    return function (lat, lng) {
      var best = null, bestDist = Infinity;
      for (var i = 0; i < cands.length; i++) {
        var b = cands[i].bbox;
        var dLat = lat - (b.minLat + b.maxLat) / 2, dLng = lng - (b.minLng + b.maxLng) / 2;
        var d = dLat * dLat + dLng * dLng;
        if (d < bestDist) { best = cands[i]; bestDist = d; }
      }
      return best;
    };
  }

  /* Ray casting against one ring, then the same for its holes. The rings are
   * [lng, lat] GeoJSON pairs, which is why x is the longitude here. */
  function inRing(lat, lng, ring) {
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if ((yi > lat) !== (yj > lat) &&
          lng < (xj - xi) * (lat - yi) / ((yj - yi) || 1e-15) + xi) inside = !inside;
    }
    return inside;
  }

  function inOutline(lat, lng, geojson) {
    var geoms = [];
    if (!geojson) return false;
    if (geojson.type === "FeatureCollection") {
      for (var f = 0; f < (geojson.features || []).length; f++) {
        if (geojson.features[f] && geojson.features[f].geometry) geoms.push(geojson.features[f].geometry);
      }
    } else if (geojson.type === "Feature") { if (geojson.geometry) geoms.push(geojson.geometry); }
    else { geoms.push(geojson); }
    for (var g = 0; g < geoms.length; g++) {
      var geom = geoms[g];
      var polys = geom.type === "Polygon" ? [geom.coordinates]
                : geom.type === "MultiPolygon" ? geom.coordinates : [];
      for (var p = 0; p < polys.length; p++) {
        var poly = polys[p];
        if (!poly || !poly.length || !inRing(lat, lng, poly[0])) continue;
        var inHole = false;
        for (var h = 1; h < poly.length; h++) { if (inRing(lat, lng, poly[h])) { inHole = true; break; } }
        if (!inHole) return true;
      }
    }
    return false;
  }

  var outlineCache = {};
  function loadOutline(metro) {
    if (!metro.outline) return Promise.resolve(null);
    if (!outlineCache[metro.tag]) {
      outlineCache[metro.tag] = fetch(metro.outline)
        .then(function (r) { return r.ok ? r.json() : null; })
        ["catch"](function () { return null; });   // an outage must never break routing
    }
    return outlineCache[metro.tag];
  }

  /* Which instance should answer for this point. Resolves to a metro or null.
   *
   * The bbox is kept as the cheap first pass, and for a point only ONE
   * instance's rectangle claims — the overwhelming majority — nothing is
   * fetched and the answer is immediate. Only a genuinely CONTESTED point
   * pays for the real geometry, and it is geometry this fleet already
   * publishes: each instance's own dissolved coverage ring, the same file the
   * coverage map below already loads. Measured over the same 37 places, the
   * ring answers all 37 correctly and claims no point twice.
   *
   * It refines WHICH claimant wins; it never overrules the rectangle to say
   * NOBODY covers a point. These rings are simplified for drawing, so a
   * shoreline address can sit a few metres outside one, and telling a real
   * reader their home is uncovered on that evidence would be worse than the
   * misroute this replaces. No ring containing it, or no ring shipped, falls
   * back to the centre rule above. */
  function resolveMetro(lat, lng) {
    var cands = metrosClaiming(lat, lng);
    if (!cands.length) return Promise.resolve(null);
    if (cands.length === 1) return Promise.resolve(cands[0]);
    var withRing = [];
    for (var i = 0; i < cands.length; i++) { if (cands[i].outline) withRing.push(cands[i]); }
    if (!withRing.length) return Promise.resolve(nearestByCentre(cands)(lat, lng));
    return Promise.all(withRing.map(loadOutline)).then(function (rings) {
      var hits = [];
      for (var i = 0; i < withRing.length; i++) {
        if (rings[i] && inOutline(lat, lng, rings[i])) hits.push(withRing[i]);
      }
      if (hits.length === 1) return hits[0];
      return nearestByCentre(hits.length ? hits : cands)(lat, lng);
    })["catch"](function () { return nearestByCentre(cands)(lat, lng); });
  }

  /* THE APPS' OWN ANSWER, ASKED FIRST (2026-09-28). Every app decides which
   * instance a selected point belongs to against fleet-outlines.json — each
   * live instance's widest outline, simplified to about 200 m, generated by
   * scripts/build_fleet_outlines.py and served from this same root — so the
   * front door reads the same file and cannot route an address somewhere the
   * app it opens would send the reader straight back from. It also reaches
   * what no rectangle can: the western Upper Peninsula sits west of
   * Michigan's clipped bbox, so the pass below never offered it to Michigan,
   * and Gary, Indiana sits inside Illinois's bbox, so it was sent to an app
   * with nothing to show there.
   *
   * THE WORRY THE PASS BELOW WAS WRITTEN AGAINST STILL HOLDS: these outlines
   * are simplified, so a shoreline or state-line address can sit a few
   * hundred metres outside the one that serves it. So a point no outline
   * contains goes to the nearest outline within NEAR_DEG (about 1.5 km), and
   * only a point farther than that from every one is told it is uncovered.
   * If the file cannot be read, the rectangle pass below answers, as before. */
  var NEAR_DEG = 0.015;
  var fleetOutlines = null;
  function loadFleetOutlines() {
    if (!fleetOutlines) {
      fleetOutlines = fetch("fleet-outlines.json")
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { return d && d.outlines ? d.outlines : null; })
        ["catch"](function () { return null; });   // an outage falls back, never breaks routing
    }
    return fleetOutlines;
  }

  // Degrees, with longitude scaled by the latitude's cosine so a degree east
  // and a degree north count about the same. Only ever compared with NEAR_DEG.
  function distToGeometry(lat, lng, geom) {
    var k = Math.cos(lat * Math.PI / 180), best = Infinity;
    var polys = geom.type === "Polygon" ? [geom.coordinates]
              : geom.type === "MultiPolygon" ? geom.coordinates : [];
    for (var p = 0; p < polys.length; p++) {
      for (var r = 0; r < polys[p].length; r++) {
        var ring = polys[p][r];
        for (var i = 1; i < ring.length; i++) {
          var ax = ring[i - 1][0] * k, ay = ring[i - 1][1], bx = ring[i][0] * k, by = ring[i][1];
          var px = lng * k, py = lat, dx = bx - ax, dy = by - ay;
          var t = (dx || dy) ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy))) : 0;
          var ex = ax + t * dx - px, ey = ay + t * dy - py;
          var d = Math.sqrt(ex * ex + ey * ey);
          if (d < best) best = d;
        }
      }
    }
    return best;
  }

  function fleetOwner(lat, lng, outlines) {
    var hits = [];
    for (var i = 0; i < METROS.length; i++) {
      var g = outlines[METROS[i].id];
      if (g && inOutline(lat, lng, g)) hits.push(METROS[i]);
    }
    if (hits.length === 1) return hits[0];
    if (hits.length > 1) return nearestByCentre(hits)(lat, lng);
    var best = null, bestDist = NEAR_DEG;
    for (var j = 0; j < METROS.length; j++) {
      var h = outlines[METROS[j].id];
      if (!h) continue;
      var d = distToGeometry(lat, lng, h);
      if (d <= bestDist) { best = METROS[j]; bestDist = d; }
    }
    return best;
  }

%(maplink)s

  var form = document.getElementById("search-form");
  var input = document.getElementById("search-input");
  var button = document.getElementById("search-button");
  var status = document.getElementById("search-status");
  var inFlight = null;

  function setStatus(text, isError) {
    status.textContent = text;
    status.className = "search-status" + (isError ? " err" : "");
  }

  /* COUNTING A MAP LINK READ HERE. The apps count each Google Maps or Apple
   * Maps link their search box reads (ENGINE geocoder-search countLinkRead),
   * and this page counts the ones it reads in the same event, with "front"
   * where an app puts its tag:
   *
   *   map-link-read/front/<source>/<form>/<via>/<outcome>
   *
   * <outcome> is where the link went: to-<tag> (the app it opened),
   * uncovered, none, unreadable, search-failed, or failed-<why> when the
   * lookup could not read a short link. A place shared into the installed
   * app reaches this page (as "opened") when no state has been opened yet.
   * Nothing about the place is in it. It is one of the two events this page
   * sends, with the worked example's example-place/<place> (EXAMPLE_SCRIPT),
   * and the privacy page names both (build_privacy_page.py ROOT_EVENTS). The
   * counter loads after this script, so a count waits for it, up to ten
   * seconds, as the apps' do. */
  var linkRead = null, linkVia = "pasted";
  function trackEvent(path, tries) {
    if (window.goatcounter && typeof window.goatcounter.count === "function") {
      window.goatcounter.count({ path: path, title: path, event: true });
      return;
    }
    if ((tries || 0) < 40) setTimeout(function () { trackEvent(path, (tries || 0) + 1); }, 250);
  }
  function countLinkRead(outcome) {
    var r = linkRead;
    if (!r) return;
    linkRead = null;
    var form = r.short ? (r.retried ? "short-retried" : "short") : "full";
    trackEvent("map-link-read/front/" + r.source + "/" + form + "/" + r.via + "/" + outcome);
  }
  function resetButton() {
    button.disabled = false;
    button.textContent = "Show districts";
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q) { setStatus("Type an address or ZIP first.", true); return; }
    if (inFlight) inFlight.abort();
    inFlight = new AbortController();
    button.disabled = true;
    button.textContent = "Searching\\u2026";
    setStatus("Searching\\u2026", false);
    // A pasted Google Maps or Apple Maps link, or a coordinate pair, is read
    // here by the same parser every app runs (engine/shared/map-link.txt),
    // so nothing it carries goes to the geocoder as address text.
    var link = parseMapLink(q);
    linkRead = link && (link.source === "google" || link.source === "apple")
      ? { source: link.source, short: link.kind === "short", retried: false, via: linkVia } : null;
    linkVia = "pasted";
    if (link && link.kind === "short") {
      var signal = inFlight.signal;
      setStatus("Reading the link\\u2026", false);
      // a failed lookup is tried again (ENGINE map-link), and the reader is
      // told so rather than left watching the same words
      resolveShortMapLink(link, signal, function () {
        if (linkRead) linkRead.retried = true;
        if (!signal.aborted) setStatus("Reading the link\\u2026 trying again", false);
      }).then(function (full) {
        if (signal.aborted) return;
        setStatus("Searching\\u2026", false);
        submitLink(full, full.kind === "text" ? full.text : q, q);
      }, function (err) {
        if (err && err.name === "AbortError") return;
        resetButton();
        setStatus(mapLinkMessage(link, err), true);
        countLinkRead("failed-" + ((err && err.reason) || "other"));
      });
      return;
    }
    submitLink(link, link && link.kind === "text" ? link.text : q, q);
  });

  // `typed` is what was put in the box: the link itself, for a link
  function submitLink(link, q, typed) {
    if (link && link.kind === "point") { routePoint(link.lat, link.lng); return; }
    if (link && link.kind !== "text") {
      resetButton(); setStatus(mapLinkMessage(link), true); countLinkRead("unreadable"); return;
    }
    // a typed ZIP code goes to the app whose list holds it (routeZip)
    var zip = link ? "" : zipQuery(q);
    if (zip) { routeZip(zip); return; }
    var named = link ? namedState(q) : null;
    if (named && !named.metro) {
      countLinkRead("uncovered");
      resetButton();
      setStatus("That place is in " + stateInSentence(named.tag) +
        ", which districtry doesn't cover yet \\u2014 see what's covered below.", true);
      return;
    }
    // a link is handed on rebuilt from its words (ENGINE map-link
    // mapLinkForText), so a short link read here is not read again there;
    // an address with no name in front, typed or carried by a link, is held
    // to its house number (searchAndRoute)
    var bare = link ? addressAfterName(q) : null;
    var address = !bare && OPENS_WITH_ADDRESS.test(q) ? q : null;
    // the state a typed address names, for when the search finds nothing
    // any app covers (searchAndRoute `home`)
    var home = !link && address ? namedState(q) : null;
    searchAndRoute(q, bare, address, link ? mapLinkForText(link) : typed,
      named && named.metro.whole ? named.metro : null, true,
      home && home.metro && home.metro.whole ? home.metro : null);
  }

  /* THE STATE A LINK'S ADDRESS NAMES (ENGINE map-link addressStateTag), with
   * the entry that answers there, or null when it names none. A place in a
   * state nothing here covers is said to be, and nothing is searched. A
   * place in a whole state's app goes to that app and no other: a search's
   * first covered answer somewhere else is another place of the same name,
   * and when the search finds nothing there the link is handed to that app,
   * whose own search tries the address alone, the street and the name
   * (2026-10-16: a Wisconsin place's short link, read here, said "No
   * matches"). San Francisco's app carries California's tag and answers for
   * one city, so an address in California decides nothing and the search
   * routes by position as before. */
  function namedState(text) {
    var tag = addressStateTag(text);
    if (!tag) return null;
    for (var i = 0; i < METROS.length; i++) {
      if (METROS[i].tag === tag) return { tag: tag, metro: METROS[i] };
    }
    return { tag: tag, metro: null };
  }

  // A link or a typed address handed to the app that covers its state, which
  // searches it there
  function handTo(metro, typed) {
    countLinkRead("to-" + metro.tag);
    setStatus("Opening " + metro.name + "\\u2026", false);
    window.location.href = metro.url + "#q=" + encodeURIComponent(typed);
  }

  /* `bare` is the address without the place's name in front of it, for
   * text a map link carried, tried only when the whole text matches nothing
   * (ENGINE map-link addressAfterName): a place shared from the Google Maps
   * app is its name and its address in one string. Its answers count only
   * if they are its house, its number on its street (labelAtHouse), as in
   * the apps. When none is but one is on the address's street in its town
   * (labelOnStreet), the app covering that street is opened with what was
   * typed, and shows the street there for the reader to tap the place
   * (routeText).
   *
   * AN ADDRESS WITH NO NAME IN FRONT, typed or carried by a link, is held
   * to its house number from the first try (`mustCarry` with `whole`), as
   * in the apps (ENGINE geocoder-search runAddressSearch), because an
   * answer without the number is a street and its point a spot somewhere
   * along it: until 2026-10-17 a typed Chicago storefront's address, whose
   * street Photon holds and whose number it does not, opened the Illinois
   * app with a point on that street selected, a ward or more from the
   * storefront, and nothing said so. When no answer carries the number, the
   * app covering an answer on the address's street (addressInTownOf, which
   * reads a town typed with no comma, or not typed at all, from the
   * answer), or else the first answer any app covers, is opened with what
   * was typed, never with a point, and says there what its search knows.
   * An answer with the number on another street is not the house either:
   * until 2026-10-19 it opened its app with that house's point selected.
   *
   * `want` is the app a link's address names (namedState): only an answer
   * there is routed, and when there is none the link is handed to it.
   * `home` is the app of the state a typed address names: when the search
   * finds nothing any app covers, the address is handed to it, whose own
   * search asks the Census Bureau's address records about it (ENGINE
   * geocoder-search), where until 2026-10-19 this page said "No matches" or
   * that the address was outside every place districtry covers. */
  function searchAndRoute(q, bare, mustCarry, typed, want, whole, home) {
    fetch("https://photon.komoot.io/api/?q=" + encodeURIComponent(q) + "&lang=en&limit=5",
      { signal: inFlight.signal, headers: { Accept: "application/json" } })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        var feats = (data && data.features) || [], street = [], loose = whole ? feats : [];
        if (mustCarry) {
          street = feats.filter(function (f) {
            return whole ? !!addressInTownOf(mustCarry, photonParts(f)) : labelOnStreet(photonParts(f), mustCarry);
          });
          feats = feats.filter(function (f) { return labelAtHouse(photonParts(f), mustCarry); });
        }
        if (!feats.length && bare) { searchAndRoute(bare, null, bare, typed, want); return; }
        if (want && !feats.length) return handTo(want, typed);
        if (!feats.length && mustCarry && (street.length || loose.length)) {
          return routeText(street.length ? street : loose, typed).then(function (went) {
            if (went) return;
            if (home) return handTo(home, typed);
            countLinkRead("uncovered"); resetButton(); setStatus("That address is outside every place districtry covers today \\u2014 see what's covered below.", true);
          });
        }
        if (home && !feats.length) return handTo(home, typed);
        return loadFleetOutlines().then(function (outlines) {
          if (!outlines) return want ? handTo(want, typed) : routeByRectangles(feats);
          // The FIRST result an instance answers for, not result #1 — a bare
          // place name ambiguous across states gets a fair shot.
          for (var i = 0; i < feats.length; i++) {
            var c = feats[i] && feats[i].geometry && feats[i].geometry.coordinates;
            if (!c || c.length < 2) continue;
            var metro = fleetOwner(c[1], c[0], outlines);
            if (metro && (!want || metro === want)) { go(metro, { lat: c[1], lng: c[0] }); return; }
          }
          if (want) return handTo(want, typed);
          countLinkRead(feats.length ? "uncovered" : "none");
          resetButton();
          setStatus(
            feats.length
              ? "That address is outside every place districtry covers today \\u2014 see what's covered below."
              : "No matches \\u2014 try a fuller address, or pick a place below.",
            true
          );
        });
      })
      ["catch"](function (err) {
        if (err && err.name === "AbortError") return;
        countLinkRead("search-failed");
        resetButton();
        setStatus("Search failed \\u2014 try again, or pick a place below.", true);
      });
  }

  // A Photon answer's parts in the order the apps label one (photonLabel),
  // which is what labelOnStreet reads
  function photonParts(f) {
    var p = (f && f.properties) || {};
    return [p.name, p.housenumber && p.street ? p.housenumber + " " + p.street : p.street,
            p.district, p.city, p.state, p.postcode].filter(Boolean).join(", ");
  }

  /* The street an address is on, or the answers to it, when none is its
   * house: the app that covers the first of them any app covers is opened
   * with what was typed, so it reads the link or the address again and
   * shows the street there (ENGINE geocoder-search showStreetOnly), or
   * lists the answers for the reader to pick from. It hands over the text
   * and not a position, because a point on a street is not the place. */
  function routeText(answers, typed) {
    return loadFleetOutlines().then(function (outlines) {
      for (var i = 0; i < answers.length; i++) {
        var c = answers[i] && answers[i].geometry && answers[i].geometry.coordinates;
        if (!c || c.length < 2) continue;
        if (outlines) { var m = fleetOwner(c[1], c[0], outlines); if (m) return m; }
        else if (metrosClaiming(c[1], c[0]).length) return resolveMetro(c[1], c[0]);
      }
      return null;
    }).then(function (metro) {
      if (!metro) return false;
      countLinkRead("to-" + metro.tag);
      setStatus("Opening " + metro.name + "\\u2026", false);
      window.location.href = metro.url + "#q=" + encodeURIComponent(typed);
      return true;
    });
  }

  /* A TYPED ZIP CODE (ENGINE map-link zipQuery) is handed, as #q=, to the
   * app whose ZIP code list holds it (fleet-zips.json, from
   * scripts/build_zip_index.mjs), with nothing asked of the geocoder: that
   * app selects a spot inside it, outlines all of it and compares it with
   * the wards or county board districts it crosses (ENGINE geocoder-search
   * showZip). Until 2026-10-21 this page searched a ZIP code like an
   * address and opened the app with the geocoder's one point for it
   * selected, so the cards named one ward of a ZIP code that crosses four.
   * A ZIP code no list holds (a post office box's, or one in Kentucky,
   * whose app draws no ZIP codes) is searched here, and the app covering
   * the first answer is handed the ZIP code rather than the answer's point,
   * so it lists its own answers there and selects none of them for the
   * reader. If the list cannot be read, the same search answers. */
  var fleetZips = null;
  function loadFleetZips() {
    if (!fleetZips) {
      fleetZips = fetch("fleet-zips.json")
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { return d && d.zips ? d.zips : null; })
        ["catch"](function () { return null; });   // an outage falls back to the search, never breaks it
    }
    return fleetZips;
  }
  function routeZip(zip) {
    var signal = inFlight.signal;
    loadFleetZips().then(function (zips) {
      if (signal.aborted) return;
      for (var i = 0; i < METROS.length; i++) {
        if (zips && zipListed(zips[METROS[i].id], zip)) return handTo(METROS[i], zip);
      }
      return fetch("https://photon.komoot.io/api/?q=" + encodeURIComponent(zip) + "&lang=en&limit=5",
        { signal: signal, headers: { Accept: "application/json" } })
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.json();
        })
        .then(function (data) {
          var feats = (data && data.features) || [];
          return routeText(feats, zip).then(function (went) {
            if (went) return;
            resetButton();
            setStatus(feats.length
              ? "ZIP code " + zip + " is outside every place districtry covers today \\u2014 see what's covered below."
              : "No matches for ZIP code " + zip + " \\u2014 try an address, or pick a place below.", true);
          });
        });
    })["catch"](function (err) {
      if (err && err.name === "AbortError") return;
      resetButton();
      setStatus("Search failed \\u2014 try again, or pick a place below.", true);
    });
  }

  /* A position read from a link: the same routing a geocoded address gets. */
  function routePoint(lat, lng) {
    var feats = [{ geometry: { coordinates: [lng, lat] } }];
    loadFleetOutlines().then(function (outlines) {
      if (!outlines) return routeByRectangles(feats);
      var metro = fleetOwner(lat, lng, outlines);
      if (metro) { go(metro, { lat: lat, lng: lng }); return; }
      countLinkRead("uncovered");
      resetButton();
      setStatus("That place is outside every place districtry covers today \\u2014 see what's covered below.", true);
    });
  }

  function go(metro, hit) {
    countLinkRead("to-" + metro.tag);
    setStatus("Opening " + metro.name + "\\u2026", false);
    window.location.href = metro.url + "#point=" + hit.lat.toFixed(5) + "," + hit.lng.toFixed(5);
  }

  /* The rectangle pass, kept whole for the case fleet-outlines.json cannot be
   * read. It is what answered every address before that file existed. */
  function routeByRectangles(feats) {
        // Still the FIRST result any instance's bbox claims, not result #1 —
        // a bare place name ambiguous across states gets a fair shot. The
        // coarse pass stays synchronous and unchanged; only the winner is then
        // refined against the real rings, so an uncovered address costs no
        // fetch at all.
        var hit = null;
        for (var i = 0; i < feats.length; i++) {
          var c = feats[i] && feats[i].geometry && feats[i].geometry.coordinates;
          if (!c || c.length < 2) continue;
          if (metrosClaiming(c[1], c[0]).length) { hit = { lat: c[1], lng: c[0] }; break; }
        }
        if (!hit) {
          countLinkRead(feats.length ? "uncovered" : "none");
          resetButton();
          setStatus(
            feats.length
              ? "That address is outside every place districtry covers today \\u2014 see what's covered below."
              : "No matches \\u2014 try a fuller address, or pick a place below.",
            true
          );
          return;
        }
        return resolveMetro(hit.lat, hit.lng).then(function (metro) {
          if (!metro) { countLinkRead("uncovered"); resetButton(); setStatus("That address is outside every place districtry covers today \\u2014 see what's covered below.", true); return; }
          countLinkRead("to-" + metro.tag);
          setStatus("Opening " + metro.name + "\\u2026", false);
          window.location.href = metro.url + "#point=" + hit.lat.toFixed(5) + "," + hit.lng.toFixed(5);
        });
  }

  /* A PLACE HANDED OVER IN THE ADDRESS (#q=). A place shared into the
   * installed app reaches its launcher (app/index.html), which opens the
   * state the reader used last with #q=, or this page when no state has been
   * opened yet. It is put in the box and sent exactly as if it had been
   * pasted, so a map link is read here and routed, and anything else is an
   * address search. The hash, never the query string, because the counter on
   * this page reports the query string with every visit; and it is taken out
   * of this page's address first, so going back here does not search it
   * again and send the reader forward a second time. */
  var handed = /(?:^#|&)q=([^&]*)/.exec(location.hash);
  if (handed) {
    var handedText = "";
    try { handedText = decodeURIComponent(handed[1]).trim(); } catch (err) { handedText = ""; }
    if (window.history && history.replaceState) history.replaceState(null, "", location.pathname + location.search);
    if (handedText) {
      linkVia = "opened";
      input.value = handedText;
      if (form.requestSubmit) form.requestSubmit(); else button.click();
    }
  }
})();
</script>
</body>
</html>
""" % {
        "title": html.escape(title, quote=True),
        "desc": html.escape(desc, quote=True),
        "jsonld": _landing_jsonld(metros, title, desc),
        "canonical": CANONICAL,
        "forward": FORWARD_TO,
        "brand": light["brand-600"].strip(),
        "favicon": html.escape(favicon_uri, quote=True),
        "fontface": fontface + "\n" + FALLBACK_FACE,
        "themeboot": shared_theme_boot(),
        "playapp": shared_play_app(),
        "maplink": shared_map_link(),
        "light": token_css(LIGHT_TOKENS, light, ":root"),
        "dark": token_css(DARK_TOKENS, dark, '[data-theme="dark"]', DARK_EXTRA,
                          indent="    "),
        "states": render_states(metros),
        "asks": render_asks(metros),
        "mark": load_mark(),
        "notice": render_notice(),
        "notice_memory": notice_memory(),
        "example": example,
        "answer_count": html.escape(answer_count),
        "answer_verb": answer_verb,
        "key_wash": key_wash,
        "metros_js": render_metros_js(metros),
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed index.html matches; exit 1 on drift")
    args = ap.parse_args()

    rendered = build()

    if args.check:
        try:
            with open(OUT, encoding="utf-8", newline="") as f:
                current = f.read()
        except OSError as e:
            fail("cannot read index.html: %s" % e)
        if current != rendered:
            for dl in list(difflib.unified_diff(
                    current.splitlines(), rendered.splitlines(),
                    fromfile="committed index.html", tofile="regenerated",
                    lineterm="", n=1))[:40]:
                print("  " + dl, file=sys.stderr)
            fail("index.html has drifted from metros.json + the districtry tokens. "
                 "Edit the DATA and regenerate; never hand-edit the landing page.")
        print("build-landing-page: OK — index.html matches metros.json (%d place(s)) "
              "and the districtry tokens" % len(load_metros()))
        return

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(rendered)
    print("build-landing-page: wrote index.html — %d place(s), %d bytes"
          % (len(load_metros()), len(rendered)))


if __name__ == "__main__":
    main()
