#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — the dissolved outline of the counties the
app actually serves — from Census TIGERweb. "Serves" means at least one
county-specific layer answers there, which is deliberately broader than "has
its own dispatch entries": METRO_COUNTY_FIPS below also carries the secondary
counties of shipped judicial circuits and the AT-LARGE counties whose only
county-specific answer is the County card's board section (no dispatch entry
at all — see DISPATCH_COUNTY_FIPS, which they deliberately do NOT appear in).
This paragraph used to quote the counts and went stale within a tranche; the
live numbers and the per-county roll-up are GENERATED from the two lists below
into docs/COUNTY_STATUS.md, so no prose — this docstring included — quotes
them by hand anymore. The served area is NOT required to be one connected
region (contiguity was retired as a shipping gate 2026-08-04 — see the policy
note above METRO_COUNTY_FIPS): a county joins whenever a county-keyed layer
answers in it, wherever it sits.

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK THE LAYERS.
Research passes 2 and 3 shipped LaSalle, Kankakee, Boone and Grundy layers
without revisiting this list, and the wash went on greying out all four — it
told a Kankakee user "beyond here only the statewide layers answer" while five
Kankakee layers were answering. Nothing failed, because the anchors only assert
the counties already listed. So: **when a county gains a dispatch entry, add it
here and give it an INSIDE anchor in the same change** (§2.5 step 1). The
OUTSIDE list is the other half of that guard — a county named there can never
be quietly served, because shipping it would fail this build.

Why this exists: the out-of-scope wash (index.html, ENGINE `scope-mask`) marks
where the app's full coverage ends. It used to be driven by the Chicago school
board tiling, i.e. the CITY limits, which greyed out all six collar counties
and suburban Cook. That understated coverage badly: a collar point resolves
17-21 of the 39 layers (county board, precincts, judicial subcircuits, fire /
park / library districts, municipal officials with named officeholders, the
legislative trio, township, ZIP, school districts) against Chicago's 32. The
honest boundary is the metro edge, beyond which only the statewide layers
answer.

It also removes a boot cost: the old call downloaded and parsed the full
20-district school-board GeoJSON on every load — 669 ms in PSI's critical chain
(docs/OPTIMIZATION_PLAYBOOK.md) — to paint a decorative wash. This file is one
small pre-dissolved feature.

WHY A BUILD STEP RATHER THAN THE EXISTING COUNTY OUTLINES: the app's in-browser
dissolve cancels an interior border only when the two neighbours' rings share
EXACT coordinates. data/app/*-county-outline.json were simplified
independently, so they don't — DuPage and Kendall share 2 vertices where a real
border runs — and Cook has no outline file at all. A single TIGERweb query
returns topologically consistent geometry (Cook/DuPage share 2,034 exact
vertices), which is what makes the dissolve sound.

The dissolve mirrors the app's `coverageOutlineRings` exactly: a segment walked
by two features is an interior border and is dropped; survivors chain back into
closed rings. Doing it here means the browser ships one feature with no interior
edges left to cancel. Disjoint regions fall out of the same walk — each closed
ring is chained independently — and group_rings() nests them into a MultiPolygon.
Effingham exercised that path on 2026-08-04 (the first island, §3.5.1 checklist):
the shipped file became a MultiPolygon whose second polygon was the island's own
OUTER ring — verified by anchor, not by eye, because an island mis-nested as a
hole renders identically and answers False to every containment test inside it.
(Effingham merged back into the mainland on 2026-08-11 when Shelby — bordering
it AND Macon/Montgomery — shipped as the 49th dispatched county; Edwards keeps
the file a MultiPolygon, exercising the same nesting.)

THE SECOND OUTPUT IS THE STATE RING (data/app/il-state-outline.json). The wash
is three zones, not two: inside the served counties everything answers, OUTSIDE
ILLINOIS nothing does, and in between — unserved Illinois — the statewide layers
(county, township, municipality, school district, ZIP) still answer. Telling
those two apart needs Illinois' own boundary, and the coverage key on the map
names all three, so the key is only honest if the ring it describes is drawn.

WHY IT IS PRE-BUILT RATHER THAN FETCHED. The rebrand preview queried TIGERweb
for the state at boot. Measured, that answer is 332 KB over 19,789 vertices —
four times the 83 KB school-board fetch this very builder exists to have removed
from the critical chain for this very wash. Pre-dissolved and simplified it is
an order of magnitude smaller, and it is the same service, the same session and
the same simplifier as the county half.

SAME TOLERANCE AS THE COUNTY DISSOLVE, DELIBERATELY. Where a served county
fronts the state line — Jo Daviess, Rock Island and Mercer on the Mississippi,
Massac, Pulaski and Hardin on the Ohio — the two rings trace the SAME river, and
the violet band between them should be nothing at all there. Simplified at
different tolerances the two would diverge by their difference and open slivers
of "unserved Illinois" along the rivers; at equal tolerance they diverge by at
most a tolerance and the band stays shut.

Usage:
    python3 build_metro_outline.py                 # writes both outline files
    python3 build_metro_outline.py --check         # verify the shipped files, write nothing
"""

import argparse
import json
import math
import os
import sys

import requests

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")
# Layer 0 of the SAME MapServer is states where layer 1 is counties, so the
# state ring costs no new host, no new service and no new entry in
# validate_sources.py's manifest — that MapServer is already on it.
TIGERWEB_STATE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "State_County/MapServer/0/query")

# ==== TEMPLATE:BEGIN outline-county-config ====
# The counties the app serves: the original seven (Cook, DuPage, Will, Lake,
# Kane, McHenry, Kendall), then LaSalle, Kankakee, Boone and Grundy from research
# passes 2-3, then Winnebago, the Livingston -> McLean -> Logan -> Sangamon ->
# Macoupin bridge, and the Metro East (Madison, St. Clair) it was built to reach.
#
# THE LAST FIVE ARE NOT COUNTIES WITH THEIR OWN LAYERS — they are the SECONDARY
# counties of shipped judicial circuits: Bond sits in Madison's 3rd, and Jersey,
# Greene, Morgan and Scott in Sangamon's 7th. A resident there gets a real
# county-specific card (their judicial subcircuit), so the wash saying "beyond
# here only the statewide layers answer" was false for them in the other
# direction from the 2026-07-30 fix: not a served county greyed out by a stale
# list, but a served county nobody had thought to list, because coverage arrived
# through a layer keyed to a CIRCUIT rather than to a county.
#
# That is what this list means now, stated plainly: it is every county where at
# least one county-specific layer answers — not every county with its own
# dispatch entry. All five are contiguous with the served area, so the ring
# stays single.
#
# THE WORD DOING THE WORK IN THAT SENTENCE IS "COUNTY-SPECIFIC", AND A RICH
# STATEWIDE LAYER IS NOT A REASON TO ADD A COUNTY HERE. The trap is concrete
# and already live, so it is written down rather than left to be rediscovered:
# Washington County's Blue Book (2026-08-03) gave us the full governing bodies
# of Centralia and Wamac, and both cities extend well past Washington County —
# Centralia into Clinton, Jefferson and Marion, Wamac into Clinton and Marion.
# So a resident standing in the MARION County part of Centralia now gets their
# whole city council on the Municipality card while the wash greys their
# location out.
#
# That looks exactly like the 2026-07-30 bug this list was rewritten to fix, and
# it is NOT the same thing. `municipality` is one of the STATEWIDE layers — it
# answers everywhere in Illinois, keyed by Census place GEOID rather than by
# county — so the set of layers answering in Marion has not changed. What
# changed is how good one statewide answer is there. Adding Marion or Clinton
# would assert that a Marion resident ANYWHERE gets county-specific data, which
# is false the moment they step outside Centralia's city limits, and would
# overstate coverage in precisely the direction this list exists to prevent.
#
# The test to apply, when a county looks like it should join: does a point
# ANYWHERE in it resolve a layer keyed to that COUNTY? If the honest answer is
# "only inside one municipality, through a statewide layer", the county stays
# out.
#
# ONE RING WAS A DELIBERATE CONSTRAINT, RETIRED 2026-08-04 (operator decision).
# Through pass 12 the call was that coverage grows as one connected region — the
# Livingston -> McLean -> Logan -> Sangamon -> Macoupin bridge carried the
# served area to the Metro East one contiguous county at a time precisely so
# Madison and St. Clair were never an island. Two facts ended the rule. First,
# the map had already stopped honouring its premise: Menard and Bureau sat fully
# enclosed by served counties as HOLES in this outline, because serveability
# follows published data and data availability is not spatially contiguous — a
# connected ring never bought a hole-free region. (Menard shipped 2026-08-07,
# leaving BUREAU as the only hole. Shelby's join on 2026-08-11 then re-proved
# the point in both directions at once: it merged the Effingham island back
# into the mainland AND enclosed CHRISTIAN — whose neighbours Sangamon, Macon,
# Shelby and Montgomery are now all served — as the second hole. FOUR RINGS
# ACROSS TWO POLYGONS. Bureau and Christian are the two unserved counties with
# no unserved neighbour, which is why each reads as a doughnut in the wash
# rather than as frontier.)
# Second, pass 11 measured the
# frontier as ASK-gated, not search-gated (docs/DATA_LAYER_GUIDEBOOK.md, "the
# search lever is spent"): once the lever is a records request, restricting
# growth to ring-adjacent counties stopped being an ordering preference and
# started refusing wins outright — a detached county that answers an ask with a
# full GIS could not ship without a land bridge through counties that may have
# nothing to publish.
#
# What remains the rule is everything that was actually load-bearing: the
# county-keyed test above (a county joins when a county-specific layer answers
# SOMEWHERE in it — never for a rich statewide answer), the INSIDE/OUTSIDE
# anchors, and a recorded gap for whatever a county still lacks. Contiguity
# survives only as a research-ordering preference — a neighbour is cheaper to
# verify against the counties around it — never as a shipping gate. And the
# rule's granularity is the COUNTY: a municipality in an unserved county still
# cannot carry its county in (the Galesburg record,
# galesburg-wards-outside-the-ring).
#
# group_rings() below nests rings correctly and emits a MultiPolygon when the
# served area becomes disjoint. Effingham (FIPS 049) exercised it on 2026-08-04
# as the first island, following the §3.5.1 checklist: its INSIDE anchor plus
# the Vandalia/Shelbyville corridor OUTSIDE anchors prove the island landed as
# its own OUTER ring — mis-nested as a hole it would render identically under
# the wash and answer False to every containment test inside it.
METRO_COUNTY_FIPS = ("031", "043", "197", "097", "089", "111", "093",
                     "099", "091", "007", "063", "201", "105", "113", "107", "167", "117",
                     "119", "163", "037", "141", "177", "015", "103", "195", "161", "203", "073",
                     "143", "179", "075", "133", "157", "039", "189", "017", "123", "125",
                     "149", "155", "009", "013", "169", "001", "109", "175", "057", "115",
                     # Effingham — the FIRST ISLAND (pass 13): two hops beyond
                     # the served area, joined 2026-08-04 under the retired-
                     # contiguity policy, so the dissolve emits a MultiPolygon
                     "049",
                     # Hamilton — the SECOND island (pass 14, 2026-08-05): the
                     # ask campaign's first fruit, at-large board + precinct
                     # and fire tilings from the county's own vendor-hosted org
                     "065",
                     # Jefferson — the 46th dispatched county (2026-08-06), and
                     # the one that ENDED an island: it borders Washington on the
                     # mainland AND Hamilton, so adding it merges the second
                     # island back in and the outline drops from four polygons to
                     # three. Its Clerk sent a precinct shapefile on request; the
                     # county publishes no boundary of any kind itself.
                     "081",
                     # Edwards — the THIRD island (pass 14, 2026-08-06), and the
                     # first island that joins through the AT-LARGE tier alone:
                     # no dispatch entry, no geometry, three commissioners on the
                     # County card. Its Clerk settled the form and sent the names
                     # in two replies; the county has no website at all, so its
                     # roster is the one in DOCUMENT_ROSTERS rather than a scrape.
                     "047",
                     # Montgomery — the 47th dispatched county (2026-08-07),
                     # and a plain mainland join: it borders Macoupin and
                     # Sangamon, both already served, so nothing about the
                     # islands changes. Its GIS office sent BOTH the board
                     # districts and the precincts as a file geodatabase, which
                     # makes it one of the few counties this size where neither
                     # half is derived or traced.
                     "135",
                     # Menard — the 48th dispatched county (2026-08-07), a
                     # mainland join between Sangamon, Logan, Mason and Cass.
                     # A COMMISSION county whose five commissioners are elected
                     # BY DISTRICT, so unlike Monroe/Randolph/Edwards it has
                     # geometry and rides a layer rather than the County card.
                     # Its lines follow section-line roads rather than precinct
                     # edges, so no dissolve could have produced them — the
                     # Beacon export its Clerk and Assessor obtained was the
                     # only route.
                     "129",
                     # Shelby — the 49th dispatched county (2026-08-11), and
                     # the one that ENDED the first island: it borders Macon
                     # and Montgomery on the mainland AND Effingham, so adding
                     # it merges the Effingham island back in and the outline
                     # drops from three polygons to two (Edwards stays out on
                     # its own). The same join ENCLOSES CHRISTIAN as a second
                     # hole beside Bureau — four rings across the two
                     # polygons. Its board districts are dissolved from Census
                     # VTDs per the composition the county publishes, one
                     # precinct split three ways along Rt 16 and Lake
                     # Shelbyville.
                     "173",
                     # Wabash — 2026-08-17, the second county on the at-large
                     # tier alone whose roster is DOCUMENT_ROSTERS rather than
                     # a scrape (a mail domain with no web server; Clerk Will
                     # sent the three names by e-mail). It borders Edwards and
                     # nothing else served — Lawrence and White are frontier —
                     # so it EXTENDED the one remaining island to two counties
                     # rather than starting another (until White, hours later,
                     # merged that island back in — see below).
                     "185",
                     # White — the 50th dispatched county (2026-08-17, the same
                     # day as Wabash), and the county that ENDED the last
                     # island: it borders Hamilton on the mainland side and
                     # Edwards AND Wabash on the island's, so adding it merges
                     # the Edwards–Wabash island back in and the outline drops
                     # from two polygons to ONE (three rings: the outer plus
                     # the Bureau and Christian enclave holes). The dissolve is
                     # recomputed, never patched — the Jefferson/Shelby
                     # precedents. Its Clerk supplied the county's one map file
                     # (the adopted district & precinct PDF) and stated the
                     # board is elected by district; the boundaries are census
                     # VTDs composed per that map and the county's own
                     # certified canvasses (build_white_boundaries.py).
                     "193",
                     # Jo Daviess — the 51st dispatched county (2026-08-17),
                     # and the first whose boundary was PURCHASED: its board
                     # districts cut across precincts along roads, its GIS
                     # data is sold under a signed licence, and the export
                     # shipped only after the county's IT/GIS Director
                     # authorized display in writing (licence #008382;
                     # build_jodaviess_board_districts.py). A plain mainland
                     # join in the state's north-west corner — it borders
                     # served Stephenson and Carroll, so the ring count is
                     # unchanged, and for the first time a newly served
                     # county leaves NO unserved Illinois neighbour behind:
                     # everything it touches is Stephenson, Carroll,
                     # Wisconsin or the Mississippi.
                     "085",
                     # Coles — the 52nd dispatched county (2026-08-17), a plain
                     # mainland join: it borders served Shelby for 6.2 km at its
                     # south-west corner, so the ring count is unchanged (three:
                     # the outer plus the Bureau and Christian enclaves). Its
                     # gap had read "no source" for a year on a misread error —
                     # colesco.illinois.gov serves an INCOMPLETE certificate
                     # chain, which every automated client reports as a failure
                     # and no browser notices, so a server misconfiguration was
                     # recorded as a refusal. The county's GIS is a public
                     # ArcGIS Online org keyed `coles`; board districts and
                     # precincts both come from it live. Leaves five unserved
                     # neighbours behind (Douglas, Edgar, Clark, Cumberland,
                     # Moultrie) and encloses none of them — Cumberland is the
                     # closest, now bordering three served counties, which is
                     # what its new OUTSIDE anchor at Toledo proves.
                     "029",
                     # Clark — the 53rd dispatched county (2026-08-18), and the
                     # first county built entirely out of ELECTION RETURNS. Its
                     # Clerk answered the standing ask in one sentence — "The
                     # County Board is elected by districts. I do not have maps
                     # available" — which settles the form and refuses the
                     # geometry in the same breath; the districts are unions of
                     # whole precincts, so the county's own certified canvasses
                     # describe them completely and the Census 2020 voting
                     # districts (23/23 by name, exact population sum) supply
                     # the polygons. A plain mainland join: it borders served
                     # Coles for ~16 km along its north-west edge, so the ring
                     # count is unchanged (three: the outer plus the Bureau and
                     # Christian enclaves). Leaves four unserved neighbours
                     # behind (Edgar, Cumberland, Crawford, Jasper) and encloses
                     # none — Edgar now borders two served counties, which is
                     # what its new OUTSIDE anchor at Paris proves.
                     "023",
                     # Crawford (54th dispatched), Mercer (55th) and MOULTRIE
                     # (County-card only — at large, so no dispatch entry),
                     # all three added 2026-08-18 by the 34-county sweep of the
                     # `pollresults.net` / `accessliberty.com` election-results
                     # vendor rather than by an e-mail. Each county's own
                     # certified results name which precincts vote in which
                     # board contest, which answers §2.5 step 2 and, where the
                     # districts are unions of whole precincts, supplies the
                     # composition outright. Crawford and Mercer are dissolves
                     # of their Census 2020 voting districts on that basis;
                     # Moultrie's board is elected AT LARGE ("COUNTY BOARD
                     # DISTRICT AT LARGE MEMBER / 16 of 16 precincts / Vote For
                     # 5"), so it has no geometry and rides the County card.
                     # All three are plain mainland joins — Crawford borders
                     # served Clark, Mercer borders served Rock Island and
                     # Henry, Moultrie borders served Macon, Shelby and Coles —
                     # so the ring count is unchanged. Moultrie's own seat,
                     # Sullivan, held an OUTSIDE anchor until this change and
                     # moved up to INSIDE, exactly as that list is designed to
                     # force.
                     "033", "131", "139",
                     # Edgar — the 56th dispatched county (2026-08-18), and the
                     # first the vendor sweep reached whose composition rests on
                     # a FULL SET of certified canvasses rather than one
                     # election: its 2022 General carries all seven districts
                     # over all 31 precincts, the 2024 General re-tabulates
                     # 1/6/7 and the 2026 General Primary 2/3/4/5/6, so every
                     # district is witnessed twice — the Clark standard, met in
                     # full. It had been an OUTSIDE anchor for a matter of
                     # hours: Clark's join that morning left Edgar bordering two
                     # served counties and made Paris the frontier, and this
                     # join moved Paris up to INSIDE. Leaves Douglas and
                     # Vermilion behind and encloses neither; Tuscola already
                     # holds Douglas OUTSIDE and Danville takes Vermilion.
                     "045",
                     # Franklin (2026-08-20), the 70th county and the first
                     # reached through a THIRD results vendor
                     # (platinumelectionresults.com, eight Illinois counties).
                     # It borders Jefferson and Hamilton, both already served,
                     # so it joins the mainland — no island, and it encloses
                     # nothing: every one of its unserved neighbours
                     # (Williamson, Saline, Perry, Jackson) still has unserved
                     # neighbours of its own.
                     "055",
                     # Clinton (2026-08-20), the 71st county and the SECOND from
                     # the platinum results vendor. It borders Washington,
                     # St. Clair, Madison and Jefferson, all served, plus Bond
                     # through the 3rd Circuit — so it fills a notch in the
                     # Metro East rather than extending the frontier, and
                     # CARLYLE MOVES FROM THE OUTSIDE LIST TO THE INSIDE ONE.
                     # Salem (Marion) takes over as the eastern frontier anchor:
                     # Marion borders Clinton, is served by nothing, and its
                     # returns route was measured shut the same afternoon.
                     "027",
                     # Warren (2026-08-21), the 72nd county — and the first
                     # reached by FIXING A PROBE rather than by asking anyone or
                     # finding a vendor. It borders Mercer, Henry and McDonough,
                     # all served, so it fills the western notch those three
                     # left. MONMOUTH MOVES FROM THE OUTSIDE LIST TO THE INSIDE
                     # ONE, and Henderson — Warren's unserved western
                     # neighbour, whose own published address is a parked
                     # domain — takes the west.
                     #
                     # AND IT CLOSES A DOUGHNUT ROUND KNOX. Warren was the last
                     # unserved county on Knox's border: Henry, Stark, Peoria,
                     # Fulton, McDonough and Mercer were already served, so this
                     # join makes KNOX THE THIRD ENCLAVE and metro-outline.json
                     # a four-ring polygon. Galesburg stays in the OUTSIDE list
                     # and is now an ENCLAVE anchor rather than a frontier one —
                     # it proves the hole stays open, which is exactly what an
                     # outside anchor is for. Read the ring count from --check.
                     "187",
                     # Knox — the 80th county (2026-08-22), and the join that
                     # CLOSES AN ENCLAVE rather than extending the frontier: it
                     # was one of the three holes in the mainland, so this
                     # removes a ring instead of adding one. Read the ring count
                     # from --check, never from a sentence. Its five board
                     # districts are the county's own adopted 2022 map — its GIS
                     # server serves the COLES PATTERN and its townships came
                     # from there, the city of Galesburg publishes districts 1-3
                     # itself, and the certified returns' 13/15 precinct counts
                     # and near-equal Census populations both corroborate the
                     # transcription (scripts/build_knox_board_districts.py).
                     "095",
                     # Union (181) and Williamson (199) — the 81st and 82nd
                     # (2026-08-22), both joining through the AT-LARGE tier
                     # alone: no dispatch entry, no district geometry, their
                     # commissioners on the County card. Both sit behind an
                     # sgcaptcha gate that answers 202, so their rosters come
                     # from their own CERTIFIED CANVASSES on
                     # platinumelectionresults.com — Union's five lettered seats
                     # and Williamson's three, each row naming the election that
                     # seated it. Deliberately ABSENT from DISPATCH_COUNTY_FIPS
                     # below (§1.5), like Moultrie and Massac before them.
                     "181", "199",
                     # Massac — the FOURTH ISLAND (2026-08-21), and the second
                     # to join through the AT-LARGE tier alone, after Edwards:
                     # no dispatch entry, no geometry, three commissioners on
                     # the County card. It sits on the Ohio River at the far
                     # south of the state, and when it joined ALL THREE of its
                     # Illinois neighbours were unserved (Johnson, Pope,
                     # Pulaski), so the dissolve emitted a second outer ring
                     # roughly eighty miles clear of the mainland — the largest
                     # detachment yet, and the reason Vienna (Johnson) and
                     # Marion (Williamson) joined the OUTSIDE list to anchor the
                     # corridor between the island and the mainland as washed.
                     #
                     # ITS ISLANDHOOD LASTED THE SAME DAY. Johnson shipped that
                     # evening, bordering served Saline on the mainland side and
                     # Massac on the island's, and the dissolve dropped back to
                     # ONE polygon — Vienna moving from the OUTSIDE list to the
                     # INSIDE one exactly as its own note said it would. Massac
                     # is kept here as an island because the record of HOW IT
                     # JOINED is what the §3.5.1 checklist is for; what it is
                     # today is a plain interior county, and the ring count
                     # comes from --check rather than from this comment.
                     #
                     # HOW IT WAS FOUND, because the route generalises: the
                     # county was recorded as having "a real website" that
                     # surfaced no board page. It has a Commissioners page, and
                     # what reached it was probing the domain in the CLERK
                     # ROSTER (massaccountyil.gov) instead of permuting the
                     # county's name — the same correction Cumberland forced on
                     # 2026-08-20, applied to the whole frontier at once.
                     "127",
                     # Saline — the 74th county (2026-08-21), a plain MAINLAND
                     # join: it borders Hamilton and White, both already served,
                     # so nothing about the Massac island or the three enclaves
                     # changes. Like Massac it joins through the AT-LARGE tier
                     # alone — thirteen members elected countywide, no district
                     # geometry, no dispatch entry.
                     #
                     # Its form is proven from the county's own certified 2026
                     # primary canvass ("FOR MEMBERS OF THE COUNTY BOARD /
                     # Precincts Counted 28 of 28 / Vote for not more than
                     # seven", all 15,441 registered voters), and corroborated
                     # by ISBE's county-board structure table and by the
                     # county's own unlabelled member list.
                     #
                     # SHAWNEETOWN STAYS IN THE OUTSIDE LIST: Gallatin borders
                     # Saline and is still unserved, so that anchor keeps doing
                     # its job on the new eastern edge rather than moving.
                     "165",
                     # Hancock — the 75th county (2026-08-21), a MAINLAND join
                     # on the Mississippi. Its Illinois neighbours are Adams,
                     # McDonough and Schuyler (all served) plus Henderson (still
                     # unserved), so it attaches to the mainland on three sides
                     # and nothing about the Massac island or the three enclaves
                     # changes. Henderson keeps its own OUTSIDE anchor at
                     # Oquawka on the new northern edge.
                     #
                     # The first county built from a COUNTY-RUN RESULTS
                     # DATABASE: its Clerk publishes every contest with a
                     # per-precinct table at electionstats.hancockcounty-il.gov,
                     # so each board-district contest NAMES its precincts
                     # rather than merely counting them. Two witnesses per
                     # district (2022 and 2026 primaries agree exactly, 2024
                     # re-confirms four of five), an exact 33-precinct
                     # partition, and the Jasper test passed 33/33.
                     "067",
                     # Gallatin — the 76th county (2026-08-21), joining
                     # through the County card alone: its board is elected AT
                     # LARGE, so there is no district geometry, no dispatch
                     # entry and no toggle. Five members, proven countywide
                     # TWICE from the Clerk's own certified canvasses
                     # ("CO.BD.MEMBER CWD (VOTE FOR) 3" in 2026 and "COUNTY
                     # BOARD MEMBER CWD (VOTE FOR) 2" in 2024, where CWD is the
                     # marker every countywide office on those ballots carries).
                     #
                     # A MAINLAND JOIN: its Illinois neighbours are Saline,
                     # White and Hamilton (all served) plus Hardin (unserved),
                     # so nothing about the Massac island or the three enclaves
                     # changes, and Hardin is not enclosed either — it still
                     # borders unserved Pope. SHAWNEETOWN MOVES FROM THE OUTSIDE
                     # LIST TO THE INSIDE ONE and Elizabethtown (Hardin) takes
                     # over the southern frontier.
                     #
                     # HOW IT WAS REACHED, which is the part worth carrying
                     # forward: this county was recorded on 2026-08-20 as "DARK
                     # to this client on every route tried". It was not.
                     # gallatinco.illinois.gov answers 200 and serves an
                     # INCOMPLETE TLS CHAIN — the Coles pattern, met a second
                     # time — so every automated client called it unreachable
                     # while the site rendered fine in a browser. Supplying the
                     # intermediate the certificate itself names opened it in
                     # one step.
                     "059",
                     # Cumberland — the 77th county served (2026-08-21), and the
                     # first to join on its PRECINCTS while its board stays
                     # measured shut. Its three compass-point districts —
                     # Western, Central, Eastern — SPLIT precincts: the county's
                     # own certified 2026 General Primary reports them as
                     # Central 6, Eastern 5, Western 3, fourteen against a county
                     # of twelve, identically for both parties, while every
                     # countywide contest on the same canvass reports exactly
                     # twelve. So no union of whole precincts can ever draw the
                     # board, and only the county's own boundary will. The
                     # precincts are a different question and they are answered:
                     # the Jasper test passes 12/12 with the population identity
                     # to the person, and the county's returns name all twelve
                     # one committeeperson contest at a time. This is the join
                     # bar settled on 2026-08-21 — the BOARD or the PRECINCTS —
                     # cleared on the second, the way Calhoun, Morgan and
                     # Gallatin cleared it.
                     #
                     # A MAINLAND JOIN THAT CLOSES NOTHING AND OPENS NOTHING:
                     # its neighbours are Coles, Shelby, Effingham and Clark
                     # (all served) plus Jasper (unserved), so no island and no
                     # enclave moves. TOLEDO MOVES FROM THE OUTSIDE LIST TO THE
                     # INSIDE ONE and Newton (Jasper) takes over that frontier.
                     "035",
                     # Johnson and Perry — the 78th and 79th counties served
                     # (2026-08-21), and the first two reached without their own
                     # websites being readable at all. Both sites refuse this
                     # client, and both blockers stand; what opened the counties
                     # is that their ELECTION AUTHORITIES publish somewhere else,
                     # on results.gbsvote.com — thirteen Illinois counties,
                     # which this project measured into its own backlog on
                     # 2026-08-20 and then left there: never in a county record,
                     # never in a build. A certified canvass answers both
                     # questions a
                     # join needs: each county's 2026 General Primary carries a
                     # single countywide FOR COUNTY COMMISSIONER contest per
                     # party (16 of 16 in Johnson, 27 of 27 in Perry) and no
                     # district-suffixed board contest anywhere, settling both
                     # boards AT LARGE, and prints a committeeperson contest per
                     # precinct that NAMES every precinct. Both Jasper tests pass
                     # clean — 16/16 and 27/27 with the population identity to
                     # the person — so both join on their precincts. Neither
                     # roster ships: commissioners are a County-card fact and the
                     # only county source for them is the blocked site.
                     #
                     # JOHNSON ENDS THE MASSAC ISLAND. It borders served Saline
                     # on the mainland side and Massac on the island's, so the
                     # dissolve drops back to ONE polygon. That is recomputed and
                     # never patched — the Jefferson, Shelby and White precedents
                     # — and VIENNA MOVES FROM THE OUTSIDE LIST TO THE INSIDE ONE
                     # while Metropolis (Massac) does the same.
                     "087", "145",
                     # Alexander — the 83rd county served (2026-08-23), joining
                     # through the County card alone: three commissioners
                     # elected countywide, so no district geometry, no dispatch
                     # entry and no toggle. The form is proven twice from the
                     # county's own documents — its 7 May 2024 minutes carry the
                     # board in their letterhead as Chairman / Vice Chairman /
                     # Commissioner with three names in the roll call, and its
                     # certified 2024 General canvass reports "FOR COMMISSIONER"
                     # in all ELEVEN precincts, the same denominator the
                     # presidential contest on that ballot reports.
                     #
                     # IT JOINED WITH ITS ROSTER KNOWINGLY SHORT — THE FIRST
                     # COUNTY TO, AND THE ASK CLOSED IT THE NEXT DAY. On the day
                     # of the join the county published two of its three members
                     # and its minutes stopped in May 2024, so the third seat was
                     # named by no source anywhere; the card printed "1 of 3 seats
                     # not listed in the county's directory" rather than padding
                     # the list or showing two names without comment, because
                     # concealing a seat and inventing one are the same failure
                     # from opposite directions.
                     #
                     # CORRECTED 2026-09-04. That is history, not the current
                     # state, and this comment went on asserting it for twelve
                     # days. The Clerk & Recorder's office answered on 2026-08-24
                     # and il-county-commissioners.json has shipped all THREE
                     # since — James (Jim) Smith as Chairman, Larry (Steve) Essex
                     # as Vice Chairman, Joe E. Griggs as Member — with `seats`
                     # dropped from the entry, so boardDirectoryShortfallNote
                     # correctly renders nothing. The ask is closed. Read the
                     # roster from that file, never from this comment.
                     #
                     # A MAINLAND JOIN AT THE SOUTHERN TIP: its only Illinois
                     # neighbours are Union (served on 2026-08-22) and Pulaski,
                     # so it attaches through Union and no island moves. MOUND
                     # CITY (PULASKI) JOINS THE OUTSIDE LIST as the frontier
                     # anchor it leaves behind.
                     #
                     # AND IT SETTLES WHAT AN ENCLAVE ACTUALLY IS, by very
                     # nearly making a fourth one. After this join Pulaski has
                     # no unserved Illinois neighbour left — Alexander, Union,
                     # Johnson and Massac all serve — which is the test Bureau
                     # and Christian meet as holes in the mainland. Pulaski is
                     # NOT a hole, and the dissolve says so: the ring count is
                     # unchanged at three (one outer plus those same two holes),
                     # because Pulaski's southern edge IS THE OHIO RIVER, the
                     # Kentucky state line. A county with no unserved neighbour
                     # is an enclave only if it is INTERIOR; one that fronts the
                     # state line is a notch in the outer boundary instead, and
                     # the outer ring simply detours around it (2,231 vertices
                     # to 2,644 in this one change). Read the ring count from
                     # --check, never from this comment — the first draft of it
                     # claimed a fourth enclave and the dissolve refuted it.
                     "003",
                     # Pulaski — the 84th county served (2026-08-23), joining ON
                     # ITS PRECINCTS the day after Alexander closed the wedge
                     # around it, and the day its own comment above described it
                     # as the frontier anchor. Both halves of that were true for
                     # about an hour.
                     #
                     # ITS RECORD HAD SAID SINCE 4 AUG that whether the board is
                     # districted or elected countywide was "not determinable in
                     # this pass", because pulaskicountyil.gov resolves to an
                     # address this project's egress refuses. That blocker is
                     # unchanged and this join does not touch it. What changed is
                     # a SWEEP CORRECTION rather than a new source:
                     # platinumelectionresults.com carries Pulaski at county id
                     # 19, and the sweep that had reported otherwise asked for
                     # ONE election slug. Its certified 2024 General Primary
                     # carries a single countywide "For County Commissioner"
                     # contest per party over all ELEVEN precincts — the same
                     # eleven every countywide office and the presidential
                     # contest report — with no district-suffixed board contest
                     # anywhere, and the only contests reporting 1 of 1 are the
                     # eleven committeeperson races. The 2016 General agrees.
                     # AT LARGE, so there is no board geometry to seek.
                     #
                     # The precincts ARE the Census 2020 voting districts: the
                     # Jasper test passes 11/11 on the county's own names with
                     # the population identity exact at 5,193. NO ROSTER SHIPS —
                     # the commissioners are a County-card fact and the vendor
                     # holds only a primary (nominees, not officeholders) and one
                     # decade-old general.
                     #
                     # IT FILLS THE NOTCH IT WAS ADDED TO ASSERT. MOUND CITY
                     # MOVES FROM THE OUTSIDE LIST TO THE INSIDE ONE, and with it
                     # the whole southern wedge below Union is served, so the
                     # outer ring stops detouring. Read the ring count from
                     # --check.
                     "153",
                     # Hardin — the 85th county served (2026-08-23), joining on
                     # its precincts an hour after Pulaski did, and the county
                     # that CORRECTED A BAR THIS PROJECT HAD JUST INVENTED.
                     # Pulaski's own build log said Hardin lacked "Pulaski's
                     # second naming source", because the platinum canvass that
                     # corroborates its board form carries no committeeperson
                     # contests. That is a standard the fleet has never used:
                     # Johnson, Perry and Pulaski each joined on ONE certified
                     # canvass that names the precincts plus the Jasper test, and
                     # holding a fourth county to a stricter one is not caution,
                     # it is an inconsistency that keeps a county dark for no
                     # stated reason.
                     #
                     # Hardin clears the actual bar twice over. Its certified 2026
                     # General Primary prints a committeeperson contest per
                     # precinct per party — twelve contests naming all six and no
                     # seventh, each reporting 1 of 1 — while every countywide
                     # office on it reports 6 of 6, and the board contest is one
                     # of those. A SECOND VENDOR agrees a decade apart
                     # (platinumelectionresults.com id 20, 2016 General, For
                     # County Commissioner over 6 of 6). The Jasper test passes
                     # 6/6 with the population identity exact at 3,649. NO ROSTER
                     # SHIPS: hardincountyil.gov is a parking lander on both
                     # hosts, and the readable canvass is a primary, which names
                     # nominees rather than officeholders.
                     #
                     # A MAINLAND JOIN: its Illinois neighbours are Gallatin,
                     # Saline and Pope, the first two already served. ELIZABETHTOWN
                     # MOVES FROM THE OUTSIDE LIST TO THE INSIDE ONE, and Pope is
                     # the frontier it leaves — the last unserved county in the
                     # far south, and one the ring should be re-read for rather
                     # than reasoned about here. Read the ring count from --check.
                     "069",
                     # Richland — 2026-08-23, a mainland join against served
                     # Crawford, Edwards and Wabash. It is the first county in
                     # the fleet whose board composition came from the COUNTY'S
                     # OWN GIS rather than from election returns: its canvasses
                     # count precincts per district and never name one (the Knox
                     # shape), while richlandil.wthgis.com publishes the board
                     # districts and the voting precincts as two county-authored
                     # layers that overlay cleanly. THE JOIN LEAVES LAWRENCE
                     # WITH NO UNSERVED ILLINOIS NEIGHBOUR — Crawford, Richland,
                     # Wabash and Edwards all serve — and that does NOT make it
                     # an enclave, for the reason Pulaski settled the same week:
                     # Lawrence's eastern edge IS the Wabash River, the Indiana
                     # state line, so it is a NOTCH in the outer boundary that
                     # the dissolve walks around rather than a hole it closes
                     # over. THE JOIN DOES CLOSE A HOLE, and a big one, which is
                     # the part reasoning-from-the-map got wrong until --check
                     # was run: Clay, Fayette, Jasper, Marion and Wayne form one
                     # contiguous unserved block that used to reach the outside
                     # through Richland and Lawrence. With Richland served the
                     # block is sealed, and the mainland goes from two holes to
                     # THREE — the fleet's first MULTI-COUNTY enclave, and by
                     # far its largest. All five are individually MEASURED shut
                     # (Clay City split between districts A and B; Avena split;
                     # Jasper's wedge precincts; Marion's five VTDs spanning
                     # three districts; Wayne's 32.4% deviation), so this is a
                     # hole made of counties that are blocked rather than
                     # unexamined — and each of the five carries its own OUTSIDE
                     # anchor below, so the whole enclave is proven unwashed.
                     # Read the ring count from --check, never from this comment.
                     "159",
                     # Jackson — 2026-08-23, and the county that FILLS ITS OWN
                     # NOTCH: every one of its five Illinois neighbours (Perry,
                     # Franklin, Williamson, Union, Randolph) was already served,
                     # while its western edge is the Mississippi, the Missouri
                     # state line — so it was a notch in the outer boundary
                     # rather than an enclave, and joining closes it rather than
                     # opening anything. It encloses nothing: it has no unserved
                     # neighbour left to enclose. THE FIRST COUNTY IN THE FLEET
                     # WHOSE DISTRICTS SPLIT PRECINCTS AND ARE BUILT ANYWAY,
                     # from census BLOCKS inside the three split precincts
                     # (scripts/build_jackson_boundaries.py). Read the ring count
                     # from --check.
                     "077",
                     # Douglas — 2026-08-23, a mainland join against served
                     # Moultrie, Coles and Edgar. THE COUNTY PUBLISHES ITS OWN
                     # BOARD DISTRICTS and nobody here had looked: its ArcGIS web
                     # map names one parcel service while the ORG BEHIND IT
                     # carries fifty-four, CountyBoardDistricts among them. So
                     # this county joins on geometry the county drew, with no
                     # dissolve and no map to interpret, even though two of its
                     # seventeen precincts are split between districts
                     # (scripts/build_douglas_boundaries.py). Its unserved
                     # neighbours Champaign and Piatt are part of a block that
                     # still reaches the Indiana line through Vermilion, so
                     # nothing is enclosed — but read the ring count from
                     # --check, never from that sentence.
                     "041",
                     # Vermilion — 2026-08-23, a mainland join on the Indiana
                     # line against served Champaign-side neighbours Ford (no),
                     # Iroquois, Champaign (no), Edgar and Douglas. THE COUNTY
                     # WAS NEVER BLOCKED: its record said the site "is not
                     # reachable from this project's network", which was true of
                     # a TLS handshake and false of the county — vercounty.org
                     # serves the COLES PATTERN, its leaf without the GoGetSSL
                     # intermediate. Supplying that intermediate by AIA opens a
                     # maintained 27-member roster. The districts come from the
                     # county's own ArcGIS org, where the WELL-LABELLED layer is
                     # the superseded one and the misspelled undocumented
                     # CountyBoardDistrcts2021 is current — settled by population
                     # balance against the 2020 census, 0.7% against 15.1%
                     # (scripts/build_vermilion_boundaries.py). THIS JOIN OPENED
                     # A THREE-COUNTY ENCLAVE — the fleet's second multi-county
                     # hole after the Clay/Fayette/Jasper/Marion/Wayne block —
                     # and it was PREDICTED WRONG before --check was run: the
                     # comment here first read that Champaign and Piatt "keep
                     # their own outlet to the frontier through Ford", which
                     # quietly assumed Ford was an outlet rather than part of the
                     # block. Ford is unserved too, and its every other
                     # neighbour (Iroquois, Kankakee, Livingston, McLean and now
                     # Vermilion) is served, so CHAMPAIGN, FORD and PIATT are one
                     # enclosed block. The ring went 4 -> 5 and the hole's bounds
                     # are exactly the union of those three counties' extents.
                     # READ THE RING COUNT FROM --check, NEVER FROM A MAP IN
                     # YOUR HEAD.
                     "183",
                     # Wayne — 2026-08-25, closing one county out of the
                     # Clay/Fayette/Jasper/Marion/Wayne five-county enclave.
                     # Composition settled for weeks by two agreeing sources;
                     # held back by population balance until the Clerk
                     # confirmed the plan is current (build_wayne_boundaries.py).
                     # READ THE RING COUNT FROM --check, NEVER FROM A MAP IN
                     # YOUR HEAD.
                     "191",
                     # Clay — 2026-08-26, the county whose gap record was the
                     # hinge of the four-county Clay/Fayette/Jasper/Marion
                     # enclave. The composition is the county's own board
                     # page; the split of Clay City between districts A and B
                     # is drawn at the village's corporate limits, the line
                     # Clerk Britton stated in writing (2026-08-24), and the
                     # +39.8% Harter V deviation shipped only after she
                     # confirmed "These are the current maps" (2026-08-26;
                     # build_clay_boundaries.py). Its join SPLITS the enclave:
                     # Clay was the block's connective county, so Jasper is
                     # enclosed alone and Fayette-Marion as a pair. READ THE
                     # RING COUNT FROM --check, NEVER FROM A MAP IN YOUR HEAD.
                     "025",
                     # judicial-subcircuit secondary counties (see below)
                     "005", "083", "061", "137", "171")
STATE_FIPS = "17"

# Every county slug the app can dispatch a layer on -> its Census FIPS. This is
# the lookup that makes the county list above CHECKABLE rather than merely
# curated: scripts/validate_index.py reads both, scans index.html for the
# per-county dispatch entries it actually registers, and fails the merge gate if
# a county gained layers without being added to METRO_COUNTY_FIPS.
#
# That check exists because the alternative did not work. Until 2026-07-30 the
# only guard was the OUTSIDE anchor list, which catches a county only if someone
# had already thought to name it — so LaSalle, Kankakee, Boone and Grundy shipped
# layers and stayed greyed out for two research passes with nothing failing.
# Anchors verify the geometry; this verifies the LIST, which is a different job.
#
# METRO_COUNTY_FIPS may be a strict superset of these values: it also carries
# counties served only through a circuit-keyed layer (the judicial-subcircuit
# secondary counties), which have no dispatch entry of their own.
DISPATCH_COUNTY_FIPS = {
    # TWELVE COUNTIES THAT MOVE FROM THE CARD/JUDICIAL TIER TO THE DISPATCH
    # TIER, 2026-09-06, WITHOUT THE RING MOVING. Each was already served —
    # nine through the at-large County card, Jersey through a judicial circuit
    # — so each is already in METRO_COUNTY_FIPS and already has an anchor; what
    # changes is that each now has a county-DISPATCHED layer, its library
    # districts, which is what this table means. Greene made the same kind of
    # tier move in the other direction on 2026-08-08 without touching the ring
    # or an anchor. validate_index.py fails if a county gains a dispatch entry
    # and is not listed here, which is how these twelve were found: the entries
    # were added first and the gate refused them.
    "alexander": "003",
    "bond": "005",
    "brown": "009",
    "edwards": "047",
    "jersey": "083",
    "massac": "127",
    "pike": "149",
    "putnam": "155",
    "saline": "165",
    "union": "181",
    "wabash": "185",
    "williamson": "199",
    "hardin": "069",
    "pulaski": "153",
    "gallatin": "059",
    "hancock": "067",
    "cook": "031", "dupage": "043", "will": "197", "lake": "097",
    "kane": "089", "mchenry": "111", "kendall": "093",
    "lasalle": "099", "kankakee": "091", "boone": "007", "grundy": "063",
    "winnebago": "201", "livingston": "105", "mclean": "113", "logan": "107",
    "sangamon": "167", "macoupin": "117", "madison": "119", "st-clair": "163",
    "dekalb": "037", "ogle": "141", "stephenson": "177", "carroll": "015",
    "lee": "103", "whiteside": "195", "rock-island": "161", "woodford": "203",
    "henry": "073", "peoria": "143", "tazewell": "179",
    "iroquois": "075", "monroe": "133", "randolph": "157",
    "dewitt": "039", "washington": "189", "cass": "017", "marshall": "123",
    "mason": "125", "adams": "001", "mcdonough": "109", "stark": "175",
    "fulton": "057",
    "macon": "115",
    "effingham": "049",
    "hamilton": "065", "jefferson": "081",
    "montgomery": "135", "menard": "129",
    "shelby": "173",
    "white": "193",
    "jo-daviess": "085",
    "coles": "029",
    "clark": "023",
    "crawford": "033",
    "mercer": "131",
    "edgar": "045",
    "franklin": "055",
    "clinton": "027",
    "warren": "187",
    "knox": "095",
    # The rule this list enforces (§1.5): an at-large county's BOARD needs no
    # dispatch entry at all — no district geometry, no toggle — because its
    # members ride the County card via data/app/il-county-commissioners.json.
    # Such a county belongs in METRO_COUNTY_FIPS above and reaches this list
    # only if it gains a dispatched layer of some OTHER kind.
    #
    # CORRECTED 2026-09-04: Moultrie stood here as the worked example of a
    # county that "must not appear here", 25 lines above the line that adds it.
    # Both were right on their own day and the pair was a contradiction inside
    # one dict from 2026-08-21, when Moultrie gained a PRECINCT entry (see the
    # Greene/Scott/Moultrie note below). An at-large board is a reason to skip
    # this list for the BOARD concept, never a reason to skip the county.
    # Precinct-only dispatch entries: both elect their boards at large,
    # so their members ride the County card and what they gain here is the
    # precinct answer alone (2026-08-20).
    "calhoun": "013", "morgan": "137",
    # Cumberland is precinct-only for a DIFFERENT reason than those two: its
    # board is districted, not at large, and its districts split precincts, so
    # nothing rides the County card either and the precinct answer is the whole
    # of what the county gains (2026-08-21).
    "cumberland": "035",
    # Johnson and Perry are precinct-only for the Calhoun/Morgan/Gallatin reason
    # — both boards are elected AT LARGE — but neither rides the County card,
    # because neither county's roster is readable: the only source for each is a
    # website that refuses this client (2026-08-21).
    "johnson": "087", "perry": "145",
    # Greene, Scott and Moultrie gain a dispatch entry WITHOUT changing tier
    # (2026-08-21). All three were already in the ring — Greene and Scott through
    # a 7th-Circuit subcircuit, Moultrie and Greene through the County card — and
    # all three elect their boards at large, so what they gain is the precinct
    # answer alone. Moultrie's is its first dispatch entry of any kind. Cass is
    # deliberately absent from this addition: it has been dispatched since its
    # board districts shipped and is already listed above.
    "greene": "061", "scott": "171", "moultrie": "139",
    # Schuyler joins them the same day, closing out the eight counties the
    # 2026-08-20 audit named. It reached the ring on 2026-08-02 through the County
    # card alone and had no outline at all until now, because a card needs no
    # coverage test and a dispatch entry does. Menard is deliberately absent from
    # this addition: it has been dispatched since its commissioner districts
    # shipped and is already listed above.
    "schuyler": "169",
    # Richland joins 2026-08-23 as a full board + precinct dispatch entry. Its
    # composition came from the COUNTY'S OWN GIS rather than from returns — the
    # first in the fleet to be composed that way — after this project spent
    # weeks reading its canvasses, which count precincts per district and never
    # name one (scripts/build_richland_boundaries.py).
    "richland": "159",
    # Jackson joins 2026-08-23 as a full board + precinct dispatch entry, and is
    # the first county served whose board districts SPLIT precincts: three of its
    # 56 are reported twice by its own certified canvass, and are resolved to
    # whole census blocks by the county's own adopted vector district map
    # (scripts/build_jackson_boundaries.py).
    "jackson": "077",
    # Douglas joins 2026-08-23 as a full board + precinct dispatch entry, and is
    # the second county served whose board districts SPLIT precincts. Unlike
    # Jackson it needed no map read at all: the county publishes the districts
    # themselves as a public feature service
    # (scripts/build_douglas_boundaries.py).
    "douglas": "041",
    # Vermilion joins 2026-08-23 as a BOARD-ONLY dispatch entry — nine districts
    # of three members each, the county's own polygons shipped as drawn. NO
    # PRECINCT ENTRY: the county re-precincted after the 2020 census, so the
    # precinct layer its GIS publishes is the superseded 84-precinct fabric
    # rather than the 38 clerk and 22 Danville Election Commission precincts its
    # own canvasses have reported since 2022
    # (scripts/build_vermilion_boundaries.py).
    "vermilion": "183",
    # Wayne joins 2026-08-25 as a full board + precinct dispatch entry. Its
    # composition was settled for weeks by two agreeing sources (the county's
    # own board page; certified 2024 General returns grouped by precinct) and
    # held back anyway by population balance — District 3 runs 32.4% over the
    # per-district ideal, past this project's usual 30% ceiling — until the
    # Clerk confirmed by e-mail that the plan is current rather than stale
    # (scripts/build_wayne_boundaries.py).
    "wayne": "191",
    # Clay joins 2026-08-26 as a BOARD-ONLY dispatch entry — 14 lettered
    # districts of one member each, composed from the county's own board page
    # with the Clay City precinct split at the village's corporate limits as
    # the Clerk described the line, and the fleet's largest accepted
    # population deviation (+39.8%, Harter V) shipped only after she
    # confirmed the plan is current. NO PRECINCT ENTRY: the county's two
    # surfaces disagree on the precinct count — its board page names Clay
    # City twice where ISBE's certified 2026 returns list it once — so a
    # precinct card would overstate what is known
    # (scripts/build_clay_boundaries.py).
    "clay": "025",
}
# ==== TEMPLATE:END outline-county-config ====

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "metro-outline.json")
STATE_OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "il-state-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "DistrictExplorer-CHI metro-outline builder"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# ==== TEMPLATE:BEGIN outline-anchors ====
# Points that MUST fall inside the dissolved outline (one per county) and
# outside it. A dissolve that silently drops a county still closes its rings,
# so ring-closure alone is not proof — these are.
INSIDE = {
    # Union and Williamson, the 81st and 82nd counties (2026-08-22), both on
    # the at-large tier. Marion (Williamson) moved here from OUTSIDE the day
    # its county joined — it was the last of the pair added on 2026-08-21 to
    # prove the corridor to the Massac island was washed, and its companion
    # Vienna (Johnson) had made the same move within hours. Both counties
    # still refuse automated requests; what changed is that their CANVASSES
    # do not. Anchors are TIGERweb place centroids, round-tripped through a
    # point-in-county query.
    "Marion (Williamson)": (37.7344, -88.9419),
    "Jonesboro (Union)": (37.4517, -89.2673),
    # Cairo (Alexander) — the county seat at the confluence of the Ohio and the
    # Mississippi, and the southernmost point in Illinois, 2026-08-23. Alexander
    # joins through the County card alone (three commissioners elected
    # countywide) on the day after Union, its only served neighbour. Verified by
    # point-in-county against the county's own shipped outline rather than by
    # eye, which matters more than usual here: the county is a narrow wedge
    # between two rivers and most of the ground near this anchor is Missouri or
    # Kentucky.
    "Cairo (Alexander)": (37.0053, -89.1765),
    # Mound City (Pulaski) — the county seat, and the anchor that spent about an
    # hour in the OUTSIDE list on 2026-08-23. It was added there to assert the
    # NOTCH Alexander's join created: Pulaski had no unserved Illinois neighbour
    # left and was still not an enclave, because its southern edge is the Ohio
    # River state line, so the outer ring detoured around it rather than closing
    # over it. Then the county itself joined on its precincts and the notch
    # closed, which is exactly the promotion this list is built to force.
    "Mound City (Pulaski)": (37.0856, -89.1631),
    # Elizabethtown (Hardin) — the county seat, promoted from OUTSIDE to INSIDE
    # on 2026-08-23 when Hardin joined on its precincts. It had held the southern
    # frontier for two days, the fourth anchor to hold that spot in three weeks
    # (Carmi, then Shawneetown, then here) and the fourth to be promoted out of
    # it by the county it stood for shipping.
    "Elizabethtown (Hardin)": (37.4499, -88.3051),
    # Knox, the 80th county (2026-08-22). Galesburg moved here from OUTSIDE
    # the day the county joined: it spent that time proving a HOLE stayed
    # open in the mainland, and now proves the same hole is closed.
    "Galesburg (Knox)": (40.9478, -90.3712),
    # Massac's anchor (2026-08-21). Massac joins through the County card alone —
    # at-large commission board, no district geometry, so no dispatch entry.
    # This point was written as the FOURTH ISLAND's proof that the island landed
    # as its own OUTER ring rather than as a hole, since a mis-nested island
    # renders identically under the wash and answers False to every containment
    # test inside it (the pass-4 nesting bug). Johnson's join hours later ended
    # the island, so what this anchor proves now is the ordinary thing every
    # other entry here proves — that the county is inside the dissolve — and it
    # stays exactly as it was measured. Derived from TIGERweb's Incorporated
    # Places centroid for Metropolis city and round-tripped through a
    # point-in-county query, per the §3.5.1 rule against recalled coordinates.
    "Metropolis (Massac)": (37.1565, -88.7082),
    # Saline's anchor (2026-08-21), the 74th county. Derived from TIGERweb's
    # Incorporated Places centroid for Harrisburg city and round-tripped
    # through a point-in-county query, per the §3.5.1 rule against recalled
    # coordinates. Saline joins on the mainland through the County card alone.
    "Harrisburg (Saline)": (37.7375, -88.5457),
    # Hancock's anchor (2026-08-21), the 75th county. TIGERweb's Incorporated
    # Places centroid for Carthage city — the county seat, and the seat of
    # District 5 — round-tripped through a point-in-county query.
    "Carthage (Hancock)": (40.4144, -91.1284),
    # Gallatin's anchor (2026-08-21), the 76th county, PROMOTED from the OUTSIDE
    # list where it had stood for four days as the southern frontier. The build
    # failed until it was moved, which is the whole of that list's job. Gallatin
    # joins on the mainland through the County card alone — at-large board, no
    # district geometry. The coordinate is unchanged from its OUTSIDE days and
    # still round-trips to Gallatin County.
    "Shawneetown (Gallatin)": (37.7131, -88.1867),
    # Pass 8: the county GIS carries board districts, precincts and Quincy's
    # wards; only the roster is blocked, which is a gap, not a reason to stay out.
    "Quincy (Adams)": (39.9356, -91.4098),
    # Promoted from OUTSIDE in pass 8, the Putnam/Waterloo move: Schuyler joins
    # through the county-commissioners roster alone — at-large board, no district
    # geometry, so no dispatch entry — which is precisely what its OUTSIDE
    # comment predicted when Mason and Brown closed the line around it.
    "Rushville (Schuyler)": (40.1200, -90.5665),
    # Pass 9: found by ASKING. The 2026-08-02 sweep recorded McDonough as having
    # no locatable public website after nine hostnames failed; the county is at
    # mcg.mcdonough.il.us (a subdomain, HTTP only) and its GIS is hosted by
    # Western Illinois University. Its clerk supplied both on request. Joins the
    # ring through Schuyler, which is its southern neighbour.
    "Macomb (McDonough)": (40.4592, -90.6718),
    # Pass 12: Macon joins on FOUR layers and deliberately not on its board.
    # Its ArcGIS Online org publishes ElectionGeography_public — the same
    # CentralSquare service family Tazewell, Whiteside and Iroquois already ship
    # from — with 64 named precincts joined to 29 polling places, plus fire (17),
    # library (10) and park (6) tilings. Its Electoral Districts layer holds the
    # right FIVE shapes and every attribute on every one of them is null, so the
    # board is a recorded gap rather than a guess (macon-county-board-labels).
    # Macoupin is the precedent for joining on precincts with no board layer.
    "Decatur (Macon)": (39.8588, -88.9588),
    "Chicago (Cook)": (41.8825, -87.6285),
    "Wheaton (DuPage)": (41.8661, -88.1070),
    "Joliet (Will)": (41.5250, -88.0817),
    "Waukegan (Lake)": (42.3636, -87.8448),
    "Aurora (Kane)": (41.7606, -88.3201),
    "Woodstock (McHenry)": (42.3147, -88.4487),
    "Yorkville (Kendall)": (41.6411, -88.4473),
    "Ottawa (LaSalle)": (41.3456, -88.8426),
    "Kankakee (Kankakee)": (41.1200, -87.8612),
    "Belvidere (Boone)": (42.2639, -88.8443),
    "Morris (Grundy)": (41.3564, -88.4237),
    "Rockford (Winnebago)": (42.2714, -89.0940),
    "Pontiac (Livingston)": (40.8809, -88.6298),
    "Bloomington (McLean)": (40.4798, -88.9939),
    "Lincoln (Logan)": (40.1481, -89.3637),
    "Springfield (Sangamon)": (39.7990, -89.6440),
    "Carlinville (Macoupin)": (39.2798, -89.8818),
    "Edwardsville (Madison)": (38.8114, -89.9532),
    "Belleville (St. Clair)": (38.5136, -89.9842),
    "Sycamore (DeKalb)": (41.9889, -88.6868),
    "Oregon (Ogle)": (42.0148, -89.3323),
    "Freeport (Stephenson)": (42.2967, -89.6212),
    "Mount Carroll (Carroll)": (42.0949, -89.9777),
    "Dixon (Lee)": (41.8493, -89.4876),
    "Morrison (Whiteside)": (41.8090, -89.9686),
    "Rock Island (Rock Island)": (41.4852, -90.5742),
    "Eureka (Woodford)": (40.7214, -89.2723),
    "Cambridge (Henry)": (41.3036, -90.1929),
    "Peoria (Peoria)": (40.6936, -89.5890),
    "Pekin (Tazewell)": (40.5675, -89.6407),
    "Watseka (Iroquois)": (40.7761, -87.7364),
    "Waterloo (Monroe)": (38.3359, -90.1498),
    "Chester (Randolph)": (37.9199, -89.8258),
    "Clinton (De Witt)": (40.1470, -88.9630),
    "Nashville (Washington)": (38.3439, -89.3812),
    "Virginia (Cass)": (39.9524, -90.2108),
    "Lacon (Marshall)": (41.0228, -89.4060),
    "Havana (Mason)": (40.2950, -90.0566),
    "Toulon (Stark)": (41.0937, -89.8651),
    "Canton (Fulton)": (40.5570, -90.0393),
    # The FIRST ISLAND (pass 13, 2026-08-04): Effingham joined detached, its
    # ring the outline's second polygon, the corridor to the mainland held
    # OUTSIDE by Vandalia (Fayette) and Shelbyville (Shelby). Shelby's own
    # join on 2026-08-11 closed that corridor and merged the island back in;
    # Vandalia still holds Fayette, the corridor's other flank, OUTSIDE.
    "Effingham (Effingham)": (39.1200, -88.5434),
    # Shelbyville (Shelby) — the county seat, 2026-08-11, moved up from the
    # OUTSIDE list where it had held the island corridor since Macon's
    # arrival pushed the frontier onto it. The 49th dispatched county and the
    # first-island merge: with Shelby served, the mainland and Effingham are
    # one polygon and Edwards is the only island left. The same join encloses
    # Christian as the wash's second hole — see Taylorville, OUTSIDE.
    "Shelbyville (Shelby)": (39.4130, -88.7940),
    # The SECOND island (pass 14, 2026-08-05): Hamilton, deep-south and five
    # unserved neighbours around it — Fairfield (Wayne) holds the corridor
    # toward Effingham OUTSIDE.
    "McLeansboro (Hamilton)": (38.0902, -88.5387),
    # The at-large tier: served through the COUNTY card's board section rather
    # than a dispatch entry, because none of the four has district geometry to
    # dispatch on. They belong here for the same reason the judicial-subcircuit
    # secondary counties do — county-specific data answers there.
    # Mount Vernon (Jefferson) — the county seat, 2026-08-06. Jefferson touches
    # both the mainland (Washington) and the Hamilton island, so this anchor is
    # also what proves the merge: the second island stops being one.
    "Mount Vernon (Jefferson)": (38.3173, -88.9031),
    # Albion (Edwards) — the THIRD island, 2026-08-06, and the first to join on
    # the at-large tier alone. White County sits between it and Hamilton, which
    # is why it lands detached rather than extending the second island; Carmi
    # (White) holds that corridor OUTSIDE below.
    "Albion (Edwards)": (38.3781, -88.0578),
    # Mt. Carmel (Wabash) — 2026-08-17: Wabash borders Edwards and joined its
    # island, growing it to two counties. Hours later White merged that island
    # back into the mainland, so this anchor now tests interior fill. The
    # county seat the wabash-county-board record insisted the roster must
    # come from (never Wabash County INDIANA, across the river); Clerk Will's
    # e-mail was exactly that source.
    "Mt. Carmel (Wabash)": (38.4109, -87.7614),
    # Carmi (White) — the county seat, 2026-08-17, moved up from the OUTSIDE
    # list where it had proven the Edwards island and the Hamilton island
    # stayed two since 2026-08-06. The 50th dispatched county and the
    # last-island merge: White borders Hamilton (mainland via Jefferson) AND
    # Edwards AND Wabash (the island), so with White served the outline drops
    # from two polygons to ONE — three rings, the outer plus the Bureau and
    # Christian enclave holes. Islands can un-island and the dissolve is
    # recomputed, never patched (the Jefferson/Shelby precedents); the list
    # failed the build until this anchor moved, exactly as designed.
    "Carmi (White)": (38.0906, -88.1589),
    "Griggsville (Pike)": (39.7078, -90.7276),
    "Hennepin (Putnam)": (41.2589, -89.3216),
    "Mount Sterling (Brown)": (39.9854, -90.7641),
    "Hardin (Calhoun)": (39.1591, -90.6248),
    # Hillsboro (Montgomery) — the county seat, 2026-08-07. Montgomery joins the
    # mainland between Macoupin and Sangamon, so this anchor tests an interior
    # fill rather than a frontier move; Vandalia (Fayette) on its south-east
    # border is the OUTSIDE anchor that keeps the fill from over-running.
    "Hillsboro (Montgomery)": (39.1614, -89.4954),
    # Petersburg (Menard) — the county seat, 2026-08-07. Menard fills the last
    # interior notch between Sangamon, Logan, Mason and Cass, so like Montgomery
    # this anchor tests a fill rather than a frontier move.
    "Petersburg (Menard)": (40.0114, -89.8523),
    # Galena (Jo Daviess) — the county seat, 2026-08-17, moved up from the
    # OUTSIDE list where it had held the state's north-west corner since Lee/
    # Whiteside/Rock Island/Henry pushed the frontier onto it. The 51st
    # dispatched county and the first PURCHASED boundary (licence #008382 +
    # the county's written display authorization — the first licence-gated
    # county ever cleared, because the redistribution question was asked
    # BEFORE signing). A mainland join between served Stephenson and Carroll;
    # no OUTSIDE successor exists for this corner, because every neighbour
    # Jo Daviess has is served, Wisconsin, or across the Mississippi —
    # Milwaukee (WI) keeps proving the state line. Coordinates verified
    # against TIGER's county rings in build_county_outline.py's jo-daviess
    # entry, where this point has been an inside anchor since 2026-08-02.
    "Galena (Jo Daviess)": (42.4185, -90.4253),
    # Charleston (Coles) — the county seat, 2026-08-17. The 52nd dispatched
    # county, joining through its south-western 6.2 km border with served
    # Shelby. Coles was never an OUTSIDE anchor, so nothing moved up; what
    # moved was the reading of its gap, which had recorded the county as
    # refusing this project's network when what its web server actually does
    # is serve an INCOMPLETE certificate chain (leaf only, no intermediate) —
    # invisible in a browser, fatal to every automated client, and not a
    # refusal at all. Board districts and precincts both come live from the
    # county's public ArcGIS Online org. Coordinates verified against TIGER's
    # county rings in build_county_outline.py's coles entry, where this point
    # has been an inside anchor since 2026-08-04.
    "Charleston (Coles)": (39.4844, -88.1778),
    # Marshall (Clark) — the county seat, 2026-08-18. The 53rd dispatched
    # county, joining through its ~16 km north-western border with served
    # Coles, which shipped the day before. Clark was never an OUTSIDE anchor;
    # what changed was not a probe but a REPLY — County Clerk & Recorder
    # Laura H. Lee's one-sentence answer that the board is elected by
    # districts, which turned a no-source gap into a composition problem the
    # county's own certified canvasses already solve. Coordinates verified
    # against TIGER's county rings in build_county_outline.py's clark entry,
    # where this point has been an inside anchor since 2026-08-04.
    "Marshall (Clark)": (39.3986, -87.6900),
    # Robinson (Crawford) — the county seat, 2026-08-18, the 54th dispatched
    # county. Its Clerk confirmed a districted board in writing on 2026-08-17
    # and its Assessor confirmed she maintains the layers, but releasing them
    # needs the county's Mapping Committee; the county's own certified results
    # made the committee moot. Joins through its western border with served
    # Clark.
    "Robinson (Crawford)": (39.0089, -87.7333),
    # Aledo (Mercer) — the county seat, 2026-08-18, the 55th dispatched county.
    # The only map the county sent is a 2021 scan that evidences the district
    # lines and supplies no data; its certified results supplied the
    # composition instead. Borders served Rock Island and Henry.
    "Aledo (Mercer)": (41.2008, -90.7460),
    # Sullivan (Moultrie) — the county seat, 2026-08-18. MOVED UP FROM THE
    # OUTSIDE LIST, where it had held the line since Macon's join in pass 12
    # and where Coles's arrival on 2026-08-17 left it bordering the served area
    # on three sides. Moultrie is a County-card county — its board is elected
    # at large, so it has no dispatch entry — and this anchor is why it still
    # belongs in the ring: a resident here gets a named board, which is a
    # county-specific answer.
    "Sullivan (Moultrie)": (39.5951, -88.6085),
    # Paris (Edgar) — the county seat, 2026-08-18, the 56th dispatched county.
    # MOVED UP FROM THE OUTSIDE LIST THE SAME DAY IT WAS ADDED THERE: Clark's
    # join that morning left Edgar bordering two served counties, and this
    # anchor was written to prove the fill stopped at its line. It stopped for
    # about four hours. The guard failed the build until the point was moved,
    # which is the whole of its job.
    "Paris (Edgar)": (39.6148, -87.6909),
    # Benton (Franklin) — the county seat, 2026-08-20, the 57th dispatched
    # county and the deepest south the mainland has reached. Franklin borders
    # Jefferson and Hamilton, both already served, so it needs no island
    # checklist; it encloses nothing either, because each of its unserved
    # neighbours (Williamson, Saline, Perry, Jackson) still borders unserved
    # counties of its own. Ava (Jackson) and Shawneetown (Gallatin) stay
    # OUTSIDE and now sit one county from the line rather than two. (Every one
    # of those four has since shipped — Perry and Saline 2026-08-21, Williamson
    # 2026-08-22, Jackson 2026-08-23 — so this comment records what was true
    # when Franklin joined, not the frontier today.)
    "Benton (Franklin)": (37.9967, -88.9203),
    # Carlyle (Clinton) — the county seat, 2026-08-20, the 60th dispatched
    # county. It held a place in the OUTSIDE list from the Metro East build
    # onward, proving the fill stopped at Clinton's line; this join moved it up,
    # and the guard failed the build until it did, which is the whole of that
    # list's job. Salem (Marion) inherits the eastern frontier.
    "Carlyle (Clinton)": (38.6103, -89.3726),
    # Monmouth (Warren) — the county seat, 2026-08-21, the 61st dispatched
    # county. It held a place in the OUTSIDE list from Mercer's join onward and
    # this move is the guard doing its job: the build failed until it was
    # promoted. Oquawka (Henderson) inherits the western frontier.
    "Monmouth (Warren)": (40.9114, -90.6473),
    # Toledo (Cumberland) — the county seat, 2026-08-21, the 63rd dispatched
    # county. It held a place in the OUTSIDE list from Coles's join on
    # 2026-08-17, written to prove the fill stopped at Cumberland's line; four
    # days later the county itself joined and the guard failed the build until
    # this point was promoted, which is exactly the job that list does. The
    # coordinates are unchanged — build_county_outline.py's own cumberland
    # inside anchor, round-tripped through a point-in-county query on
    # 2026-08-17 — so what moved is the claim about them, not the measurement.
    # Newton (Jasper) inherits the frontier.
    "Toledo (Cumberland)": (39.2728, -88.2422),
    # Vienna (Johnson) — the county seat, 2026-08-21, and the anchor that ENDED
    # THE MASSAC ISLAND. It was written into the OUTSIDE list that same day, as
    # one of the two points proving the corridor between the island and the
    # mainland was washed, with the note "if either ever ships, these move to
    # the INSIDE list". It shipped within hours. Johnson borders served Saline on
    # the mainland side and Massac on the island's, so the dissolve drops back to
    # ONE polygon and Metropolis stops standing for a detached county — the
    # island geometry is recomputed, never patched. Pope, Pulaski and Union keep
    # Johnson off any enclave list.
    "Vienna (Johnson)": (37.4143, -88.8870),
    # Pinckneyville (Perry) — the county seat, 2026-08-21. A plain mainland join
    # bordering served Washington, Franklin, Randolph and Jefferson, enclosing
    # nothing: its one unserved neighbour, Jackson, still borders unserved
    # Union and Williamson. Ava (Jackson) stayed OUTSIDE then and moved up to
    # INSIDE on 2026-08-23 when Jackson itself shipped; Union and Williamson had
    # shipped the day before, which is what left Jackson a state-line notch. The coordinates are
    # build_county_outline.py's own perry inside anchor.
    "Pinckneyville (Perry)": (38.0803, -89.3823),
    # Ava (Jackson) — moved up from OUTSIDE on 2026-08-23, where it had sat
    # since the Metro East build. Jackson had no unserved Illinois neighbour
    # left — Perry, Franklin, Williamson, Union and Randolph all serve — and was
    # a NOTCH rather than an enclave only because its western edge is the
    # Mississippi River, the Missouri state line (the Pulaski test). Joining
    # fills that notch and encloses nothing, because there is no unserved
    # neighbour left to enclose. Ava is the county's own build_county_outline.py
    # inside anchor rather than the county seat: Murphysboro and Carbondale both
    # sit in the county's populous east, and an anchor in the sparse west is the
    # one that would fail first if the fill were wrong.
    "Ava (Jackson)": (37.8886, -89.4964),
    # Tuscola (Douglas) — the county seat, moved up from OUTSIDE on 2026-08-23.
    # It had stood there since Moultrie shipped, as the anchor for a frontier of
    # Douglas and Piatt. Douglas encloses nothing on joining: Champaign and
    # Piatt, its two unserved neighbours, sit in a block that still reaches the
    # Indiana state line through Vermilion.
    "Tuscola (Douglas)": (39.7967, -88.2748),
    # Olney (Richland) — the county seat, 2026-08-23, moved up from OUTSIDE. A
    # mainland join bordering served Crawford, Edwards and Wabash. It SEALS a
    # five-county hole — Clay, Fayette, Jasper, Marion and Wayne, which reached
    # the outside through Richland until now — so the mainland goes from two
    # rings' worth of holes to three, and this is the fleet's first enclave that
    # is not a single county. It also leaves LAWRENCE with no unserved Illinois
    # neighbour, which is a NOTCH and not a fourth hole, because its eastern
    # edge is the Wabash River and the Indiana state line (the Pulaski test).
    # Lawrenceville is anchored OUTSIDE to prove that notch stays unwashed, and
    # so are all five enclave counties. The coordinates are
    # build_county_outline.py's own richland inside anchor.
    "Olney (Richland)": (38.7285, -88.0839),
    # Danville (Vermilion) — the county seat, moved up from OUTSIDE on
    # 2026-08-23. It stood in the OUTSIDE list from Edgar's join as "the biggest
    # unserved county left, and a RECORDED GAP rather than an unexamined one",
    # on the strength of a measurement that was correct and did not mean what it
    # was taken to mean: Vermilion's 38 current precincts against 84 census 2020
    # voting districts does close the DISSOLVE route, and closes nothing else.
    # The county draws its own board districts and publishes them, so no
    # dissolve was ever needed (scripts/build_vermilion_boundaries.py).
    "Danville (Vermilion)": (40.1245, -87.6300),
    # Fairfield (Wayne) — moved up from OUTSIDE on 2026-08-25. Wayne held the
    # Hamilton-Effingham corridor open while those were islands; both merged
    # in (Shelby 2026-08-11, White 2026-08-17), after which Wayne sat as a
    # deep NOTCH bordered by served Jefferson, Hamilton, White, Edwards and
    # (since 2026-08-23) Richland, with only Clay and Marion keeping it off
    # the enclave list. Composition settled for weeks by two agreeing
    # sources; held back by population balance until the Clerk confirmed the
    # plan is current (scripts/build_wayne_boundaries.py).
    "Fairfield (Wayne)": (38.3798, -88.3724),
    # Flora (Clay) — moved up from OUTSIDE on 2026-08-26, the day Clay shipped
    # as the 91st served county. It held the four-county
    # Clay/Fayette/Jasper/Marion hole's own ground from Richland's join
    # onward; the guard failed the build until this point was promoted, which
    # is that list's whole job. Clay was the block's connective county, so
    # its join SPLITS the hole — Jasper alone, Fayette-Marion as a pair —
    # and Newton, Vandalia and Salem stay OUTSIDE to prove both remnants
    # unwashed. The build itself was unlocked by two Clerk e-mails: the
    # village-limits line through Clay City (2026-08-24) and "These are the
    # current maps" (2026-08-26), which released the fleet's largest accepted
    # population deviation (scripts/build_clay_boundaries.py).
    "Flora (Clay)": (38.6688, -88.4759),
    # judicial-subcircuit secondary counties
    "Greenville (Bond, 3rd Circuit)": (38.8923, -89.4131),
    "Jerseyville (Jersey, 7th Circuit)": (39.1200, -90.3284),
    "Carrollton (Greene, 7th Circuit)": (39.3023, -90.4071),
    "Jacksonville (Morgan, 7th Circuit)": (39.7344, -90.2288),
    "Winchester (Scott, 7th Circuit)": (39.6297, -90.4563),
}
OUTSIDE = {
    # Carlyle (Clinton) sits just past the eastern edge, so the Metro East is
    # shown to have MOVED the boundary rather than merely widened an untested
    # interior — and it would fail the build if a future county list quietly
    # swallowed a neighbour. (Waterloo moved to INSIDE when Monroe shipped as a
    # commission county in pass-7 tranche 3; Sparta stands in for the southern
    # frontier now that Randolph is served.)
    # (Carmi held this spot from 2026-08-06 — proving the Edwards island and
    # the Hamilton mainland stayed separate — until White shipped on
    # 2026-08-17 and merged the last island in; it moved up to INSIDE exactly
    # as the guard is designed to force. Shawneetown (Gallatin) inherited that
    # southern frontier and held it for four days, until Gallatin itself
    # shipped on 2026-08-21 and the guard forced the same promotion again.
    # Elizabethtown (Hardin) inherited it next and held it for two days, until
    # Hardin itself shipped on 2026-08-23 on its precincts and the guard forced
    # the same promotion a fourth time. GOLCONDA (POPE) is the successor and the
    # last anchor this corner can hold: Pope is now the only unserved county in
    # the far south, bordered by served Hardin, Saline, Johnson and Massac. Its
    # own record is unchanged and is the reason it is still out here — the
    # pass-13 probe's claim that no county website answered was corrected on
    # 2026-08-09 (popecountyil.com answers 503 and the Clerk's domain is
    # popeco.illinois.gov), and no county document has been read here at all.
    # TIGERweb's Incorporated Places centroid for Golconda village, round-tripped
    # through a point-in-county query against the county's own shipped outline.)
    "Golconda (Pope)": (37.3648, -88.4870),
    # Salem (Marion) replaced Carlyle here on 2026-08-20, when Clinton shipped
    # and Carlyle moved up to INSIDE — the same forced promotion Carmi and
    # Paris made. Marion is the honest successor: it borders Clinton, is served
    # by nothing, and its own certified returns were measured the same
    # afternoon and found INSUFFICIENT — five census voting districts under the
    # base names CENTRALIA and SALEM span three board districts each, so no
    # name can place them and the dissolve that built Clinton cannot build it.
    "Salem (Marion)": (38.6270, -88.9456),
    # Fayette borders the subcircuit counties but is in no shipped circuit, so
    # it must stay outside — the guard that keeps "a circuit's secondary
    # counties" from quietly becoming "everything nearby". (Pittsfield sat
    # beside it until Pike shipped in tranche 5.)
    "Vandalia (Fayette)": (38.9606, -89.0937),
    # Canton and Toulon both sat here until their counties shipped. Toulon left
    # when Stark's whole GIS — one hand-maintained Google My Maps — was dated by
    # its County Clerk in an e-mail, and Canton left when Fulton was built: the
    # frontier sweep found Fulton needing NOTHING from anybody, its own ArcGIS
    # already serving board districts, precincts and polling places, hidden only
    # behind non-zero layer ids that make a layer-0 probe report it empty. The
    # guard did its job both times — this list failed the build until each county
    # was moved up to INSIDE. The frontier they leave behind is Schuyler, Hancock
    # and McDonough's western neighbours. Schuyler cannot serve as that anchor
    # even though it borders Fulton — it is already IN the ring through the
    # at-large tier, and naming it here failed this build immediately, which is
    # the OUTSIDE list doing exactly its job. Knox sat here as the honest
    # frontier until 2026-08-22, when its five board districts shipped and it
    # moved up to INSIDE as the 80th county — this list failed the build until
    # it was moved, exactly as designed. The frontier it leaves behind on this
    # edge is Fulton's other unserved neighbours.
    # Macon's arrival (pass 12) pushed the line south-east onto two counties
    # this project had never researched. Shelbyville sat beside Sullivan here
    # until 2026-08-11, when Clerk Jessica Fox's four-answer reply de-risked
    # the build and Shelby moved up to INSIDE as the 49th dispatched county —
    # the list failed the build until it was moved, exactly as designed.
    # Sullivan sat here until 2026-08-18, when the vendor sweep found Moultrie's
    # board is elected AT LARGE and it shipped as a County-card county — the
    # guard failed the build until it was moved up to INSIDE, exactly as
    # designed. The frontier it leaves is Douglas and Piatt, and TUSCOLA took
    # the anchor: Douglas then bordered served Coles and Moultrie, with
    # Champaign, Edgar and Piatt keeping it off the enclave list. (Douglas
    # itself shipped on 2026-08-23 and Tuscola moved up to INSIDE, so PIATT is
    # the frontier this corner now leaves — measured shut by the CCGISC licence
    # rather than by a missing source.)
    # Lawrenceville (Lawrence) — one of the two successors Richland's join
    # called for (2026-08-23; Flora, the other, moved up to INSIDE on
    # 2026-08-26 when Clay itself shipped). Olney stood here until Richland
    # shipped, and the guard failed the build until it was moved up to INSIDE,
    # exactly as designed.
    #
    # THE MULTI-COUNTY HOLE CLAY LEFT BEHIND: Clay was the five-county
    # Clay/Fayette/Jasper/Marion/Wayne block's connective county, and its join
    # (after Wayne's on 2026-08-25) SPLITS what remained — Jasper is enclosed
    # alone, Fayette-Marion as a pair, and each of the three is still anchored
    # here (Newton, Vandalia, Salem), so both holes are proven unwashed rather
    # than only their rims. Read the ring count from --check, never from this
    # comment.
    #
    # LAWRENCE IS THE INTERESTING ONE, and it is why this anchor exists.
    # Richland's join leaves it with NO unserved Illinois neighbour at all —
    # Crawford, Richland, Wabash and Edwards all serve — which is the same test
    # Bureau and Christian meet. It is still not an enclave, for the reason
    # Pulaski settled on 2026-08-23: a county with no unserved neighbour is an
    # enclave only if it is INTERIOR, and Lawrence's eastern edge IS the Wabash
    # River, the Indiana state line. That makes it a NOTCH in the outer
    # boundary, which the dissolve walks around rather than closing over. This
    # anchor is what proves the notch stays unwashed; the ring count is read
    # from --check, never reasoned about here.
    "Lawrenceville (Lawrence)": (38.7263, -87.6873),
    # Oquawka (Henderson) — the successor Warren's join calls for. Warren left
    # the OUTSIDE list on 2026-08-21 when its own board page and precinct-map
    # legend turned out to be reachable all along; Henderson is the honest
    # frontier it leaves behind, bordering Warren and served by nothing, and its
    # own recorded gap is that its published web address leads to a holding page.
    "Oquawka (Henderson)": (40.9339, -90.9484),
    # Newton (Jasper) — the successor anchor Cumberland's join calls for
    # (2026-08-21). Cumberland left exactly one unserved neighbour behind and
    # this is it, and Jasper is a MEASURED frontier rather than an unexamined
    # one: its board districts are drawn through the middle of its townships,
    # so its five precincts sit only 1-7% inside the city whose wards their
    # names echo and no whole-precinct dissolve can answer there. Newton is
    # the county seat.
    "Newton (Jasper)": (38.9903, -88.1631),
    # Christian — ENCLOSED 2026-08-11 by Shelby's join: with Sangamon, Macon,
    # Shelby and Montgomery all served, Christian is the second enclave after
    # Bureau, an interior ring rather than frontier. This anchor is what
    # proves the hole IS a hole: mis-nested, the ring would render
    # identically under the wash and Taylorville would answer True here,
    # failing the build.
    "Taylorville (Christian)": (39.5490, -89.2945),
    "Milwaukee (WI)": (43.0389, -87.9065),
    # DeKalb used to sit here, described as "enclosed on three sides by served
    # counties and the one border-ring county with no locatable GIS". The second
    # half was wrong — the county runs a full ArcGIS Online org, it was simply
    # never found — and the day it gained dispatch entries this line failed the
    # build and forced the county list to be updated with it. That is the guard
    # doing its job, so the role is handed to the next counties out.
    #
    # Lee, Whiteside, Rock Island and now Henry each sat here until the day
    # they gained dispatch entries, exactly as DeKalb did, and this list failed
    # the build until each was moved up to INSIDE (Henry's "Alternate Two
    # Board" raster turned out to BE the adopted plan — Ord 21-33, and its
    # 12+12 township composition is proven by the map's own two-census
    # population table). Jo Daviess held the state's north-west corner here
    # until 2026-08-17, when its licence-gated shapefile was bought and
    # cleared for display and Galena moved up to INSIDE — the guard failed
    # the build until it moved, exactly as designed, and no successor anchor
    # replaces it because the corner has no unserved Illinois county left.
    # The remaining frontier here is BUREAU, a RECORDED GAP rather than an
    # un-researched one and now the coverage wash's first enclave: its adopted
    # 18-district map exists only as street-split JPEG scans, its GIS licence
    # (unlike Jo Daviess's) still lacks a display permission, and the 2026
    # vendor sweep confirmed the last remaining route is closed too — its
    # certified results tabulate SIXTEEN of its precincts in more than one
    # district's contest apiece (Princeton 2 in districts 6 and 7, Hall 1 in
    # 10 and 11, and so on), so Bureau SPLITS precincts and no dissolve of
    # whole ones can draw it — the Jasper/Wade shape at scale.
    # (Aledo sat beside it until 2026-08-18, when Mercer's own certified
    # results supplied the composition its 2021 scan could not and Mercer
    # moved up to INSIDE — the guard failed the build until it moved.
    # Monmouth (Warren) takes the frontier Mercer leaves behind.)
    "Princeton (Bureau)": (41.3853, -89.4695),
    # Schuyler is a RECORDED GAP, not a gap in the research, and it now borders
    # BOTH Mason and Brown. (Menard stood beside it here until 2026-08-07, on
    # the reasoning that its five commissioner districts run section-line roads
    # rather than precinct or township unions, so no composition route existed
    # and its only map was a 2021-12 raster. Every word of that was true and
    # none of it mattered: asked, its Clerk and Supervisor of Assessments
    # obtained the Beacon export and Menard moved up to INSIDE. The reasoning
    # this list records is about what can be DERIVED, which was never the same
    # question as what a county will send.)
    # Champaign, Ford and Piatt — ENCLOSED 2026-08-23 by Vermilion's join, the
    # fleet's second multi-county enclave. Ford's every other neighbour
    # (Iroquois, Kankakee, Livingston, McLean, Vermilion) is served and
    # Champaign's and Piatt's are too, so the three are one interior block
    # rather than frontier. All three carry an anchor rather than only the rim,
    # so the whole hole is proven unwashed: mis-nested, the ring would render
    # identically under the wash and all three would answer True here, failing
    # the build. Each is MEASURED shut, not unexamined — Champaign and Piatt by
    # the CCGISC licence ("All Rights Reserved"), Ford by having no vector
    # district map and an adopted 2021 reapportionment resolution that leaves
    # its districts "To be determined".
    "Urbana (Champaign)": (40.1106, -88.2073),
    "Paxton (Ford)": (40.4606, -88.0953),
    "Monticello (Piatt)": (40.0281, -88.5728),
    # (Putnam's anchor moved up to INSIDE in tranche 5, and Adams's Clayton in
    # pass 8, each joining exactly as its OUTSIDE comment said it would — Adams
    # on the strength of its own GIS, with only the roster left as a gap.)
}
# ==== TEMPLATE:END outline-anchors ====


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": where,
        "outFields": "NAME,GEOID",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != len(METRO_COUNTY_FIPS):
        print("FATAL: TIGERweb returned %d counties, expected %d — the query or the "
              "service changed" % (len(feats), len(METRO_COUNTY_FIPS)), file=sys.stderr)
        sys.exit(1)
    return feats


def fetch_state():
    """Illinois itself, from layer 0 of the same MapServer.

    STATE_FIPS rather than STUSAB so the query keys on the same field the
    county half already uses; one feature is expected and anything else means
    the service moved."""
    resp = requests.get(TIGERWEB_STATE, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s'" % STATE_FIPS,
        "outFields": "NAME",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != 1:
        print("FATAL: TIGERweb returned %d state features, expected 1 — the query "
              "or the service changed" % len(feats), file=sys.stderr)
        sys.exit(1)
    return feats[0]


def rings_of(feature):
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        return list(geom.get("coordinates") or [])
    if geom.get("type") == "MultiPolygon":
        return [r for poly in (geom.get("coordinates") or []) for r in poly]
    return []


def dissolve(features):
    """Drop every segment walked twice (an interior border), chain the rest.

    Mirrors index.html's coverageOutlineRings so the shipped file is exactly
    what the browser would have computed — one algorithm, two places, and the
    validation below proves this one.
    """
    counts, seg_pts = {}, {}
    for feat in features:
        for ring in rings_of(feat):
            for i in range(len(ring) - 1):
                a, b = tuple(ring[i][:2]), tuple(ring[i + 1][:2])
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                counts[key] = counts.get(key, 0) + 1
                seg_pts[key] = (a, b)

    adj = {}
    for key, n in counts.items():
        if n != 1:
            continue  # interior border — both neighbours walked it
        a, b = seg_pts[key]
        adj.setdefault(a, []).append((key, b))
        adj.setdefault(b, []).append((key, a))

    used, rings = set(), []
    for seed, n in counts.items():
        if n != 1 or seed in used:
            continue
        start, cur = seg_pts[seed][0], seg_pts[seed][1]
        used.add(seed)
        ring = [list(start), list(cur)]
        while cur != start:
            nxt = None
            for key, pt in adj.get(cur, ()):
                if key not in used:
                    nxt = (key, pt)
                    break
            if nxt is None:
                print("FATAL: open chain while dissolving — the counties do not tile "
                      "cleanly (a source change?)", file=sys.stderr)
                sys.exit(1)
            used.add(nxt[0])
            cur = nxt[1]
            ring.append(list(cur))
        rings.append(ring)
    return rings


def simplify(ring, tolerance_m=SIMPLIFY_TOLERANCE_M):
    """Douglas-Peucker. County borders are survey-grid straight lines and the
    east edge is the state line in Lake Michigan (not the shoreline), so this
    collapses ~2,665 vertices to ~60 with no visible change to a wash whose
    whole job is to say "coverage ends here". Distances are metres, with
    longitude compressed by cos(latitude) so the tolerance means the same thing
    on both axes."""
    if len(ring) < 3:
        return ring
    tol = tolerance_m / 111320.0
    scale = math.cos(math.radians(42.0))

    def perp(p, a, b):
        ax, ay = a[0] * scale, a[1]
        bx, by = b[0] * scale, b[1]
        px, py = p[0] * scale, p[1]
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    keep = {0, len(ring) - 1}
    stack = [(0, len(ring) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        worst, wi = 0.0, None
        for k in range(i + 1, j):
            d = perp(ring[k], ring[i], ring[j])
            if d > worst:
                worst, wi = d, k
        if worst > tol and wi is not None:
            keep.add(wi)
            stack.append((i, wi))
            stack.append((wi, j))
    out = [ring[i] for i in sorted(keep)]
    if out[0] != out[-1]:
        out.append(out[0])  # a ring must close
    return out


def point_in_rings(lat, lng, rings):
    """Even-odd test against every ring, matching the app's pointInGeometry."""
    inside = False
    for ring in rings:
        for i in range(len(ring) - 1):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[i + 1][0], ring[i + 1][1]
            if (y1 > lat) != (y2 > lat):
                if lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                    inside = not inside
    return inside


def validate(rings):
    problems = []
    for label, (lat, lng) in sorted(INSIDE.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s should be INSIDE the metro outline and is not" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE the metro outline and is not" % label)
    return problems


# Anchors for the STATE ring. The county anchors above already name 103 places
# and every one of them is in Illinois, so the state ring is checked against
# them rather than against a second hand-built list — INSIDE (served county
# seats) and OUTSIDE (unserved Illinois county seats) must ALL fall inside it.
# That is the check worth having: the 13 unserved seats are exactly the places
# the middle zone exists for, so this asserts the violet "statewide layers
# only" band actually covers them instead of merely existing.
#
# NON_ILLINOIS names the anchors above that are NOT in Illinois. Adding an
# out-of-state anchor to OUTSIDE without naming it here FAILS this build rather
# than passing quietly, which is the point: a new anchor has to be classified.
NON_ILLINOIS = {"Milwaukee (WI)"}

# And the other three sides, so the ring is bounded everywhere rather than only
# to the north. Each is a real place across a different border of Illinois.
STATE_OUTSIDE = {
    "St. Louis (MO)": (38.6270, -90.1994),      # across the Mississippi, west
    "Davenport (IA)": (41.5236, -90.5776),      # across the Mississippi, north-west
    "Indianapolis (IN)": (39.7684, -86.1581),   # east
    "Paducah (KY)": (37.0834, -88.6000),        # across the Ohio, south
    "Milwaukee (WI)": (43.0389, -87.9065),      # north, shared with OUTSIDE above
}


_STALE_NON_IL = NON_ILLINOIS - set(OUTSIDE)
assert not _STALE_NON_IL, (
    "NON_ILLINOIS names %s, which OUTSIDE no longer carries — an exemption for an "
    "anchor that is gone silently stops exempting anything, and the next "
    "out-of-state anchor added to OUTSIDE would be asserted to be in Illinois"
    % ", ".join(sorted(_STALE_NON_IL)))


def containment_problems(coverage_rings, state_rings):
    """The served counties are Illinois counties, so their outline cannot reach
    outside the state ring — checked as ENVELOPES, not vertex by vertex.

    Vertex-exact containment is the wrong test and would fail honestly: along
    the Mississippi and the Ohio the two rings trace the SAME river and are
    simplified independently, so coverage vertices legitimately land up to a
    tolerance or two outside the state ring there. The envelope catches what is
    actually worth catching — the two files swapped, or one of them rebuilt for
    the wrong place — which would invert the wash rather than nudge it. The
    slack is two simplifier tolerances, the most the shared borders can drift."""
    slack = 2 * SIMPLIFY_TOLERANCE_M / 111320.0

    def envelope(rings):
        pts = [p for r in rings for p in r]
        return (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))

    cw, cs, ce, cn = envelope(coverage_rings)
    sw, ss, se, sn = envelope(state_rings)
    problems = []
    for label, cov, st, inside in (("west", cw, sw, True), ("south", cs, ss, True),
                                   ("east", ce, se, False), ("north", cn, sn, False)):
        past = (cov < st - slack) if inside else (cov > st + slack)
        if past:
            problems.append(
                "the coverage outline reaches %.4f on the %s but the state ring "
                "stops at %.4f — the served area cannot leave Illinois, so one of "
                "the two files is for the wrong place" % (cov, label, st))
    return problems


def validate_state(rings):
    problems = []
    for label, (lat, lng) in sorted(INSIDE.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s is a served county seat and must be INSIDE the "
                            "state ring" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if label in NON_ILLINOIS:
            continue
        if not point_in_rings(lat, lng, rings):
            problems.append("%s is an unserved ILLINOIS county seat and must be "
                            "INSIDE the state ring — the middle zone of the wash "
                            "exists for exactly these places" % label)
    for label, (lat, lng) in sorted(STATE_OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s is not in Illinois and must be OUTSIDE the state "
                            "ring" % label)
    return problems


def build_state_geojson(rings):
    polys = group_rings(rings)
    geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Illinois"},
            "geometry": geometry,
        }],
    }


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their holes.

    Needed from pass 4 on, when the served area stopped being one region. A
    two-ring Polygon means "ring 2 is a HOLE in ring 1", so emitting the detached
    Madison/St. Clair region that way would have claimed a hole in the Chicago
    metro. The wash renders identically either way (it flattens every ring into a
    cut-out), which is precisely why this had to be reasoned about rather than
    eyeballed: the bug would be invisible on the map and wrong to anything that
    ever runs a containment test — including the app's own pointInGeometry, which
    would answer False for every point in Madison County.
    """
    ordered = sorted(rings, key=len, reverse=True)
    polys = []  # [outer, hole, hole, ...]
    for ring in ordered:
        lng, lat = ring[0][0], ring[0][1]
        for poly in polys:
            if point_in_rings(lat, lng, [poly[0]]):
                poly.append(ring)  # enclosed -> a hole in that outer
                break
        else:
            polys.append([ring])
    return polys


def check_envelopes(rings):
    """The input shell must reach at least as far as the data does.

    METRO_BBOX (geocoder viewbox + the geolocate gate) and PERMALINK_GATE (the
    #point= sanity bound) are hand-set values in metro-worksheet.json that
    describe "where we serve" — and they do not move when a county is added, so
    they go stale silently and in a way no other gate sees. That has now bitten
    three times: LaSalle and Kankakee fell outside METRO_BBOX from research pass
    2 onward, Rockford's permalink was being dropped until pass 4 widened the
    gate, and Bloomington's was dropped again one county later.

    The failure is invisible because it is a REJECTION: a shared #point= link
    silently loses its point, and "Use my location" in a served county reports
    the user is outside the covered area. Nothing errors. So this turns it into a
    build failure — add a county whose geometry pokes outside either envelope and
    the outline build stops until the worksheet is widened to match.

    Checked against the SIMPLIFIED rings, i.e. the geometry actually shipped.
    """
    xs = [p[0] for ring in rings for p in ring]
    ys = [p[1] for ring in rings for p in ring]
    env = {"minLng": min(xs), "maxLng": max(xs), "minLat": min(ys), "maxLat": max(ys)}
    try:
        with open(WORKSHEET, encoding="utf-8") as f:
            worksheet = json.load(f)
    except (IOError, ValueError) as exc:
        return ["could not read metro-worksheet.json (%s)" % exc]

    problems = []
    for key in ("metro_bbox", "permalink_gate"):
        box = worksheet.get(key)
        if not box:
            problems.append("metro-worksheet.json has no %s" % key)
            continue
        for edge, cmp_ in (("minLng", "gt"), ("minLat", "gt"), ("maxLng", "lt"), ("maxLat", "lt")):
            if edge not in box:
                problems.append("%s is missing %s" % (key, edge))
                continue
            too_tight = box[edge] > env[edge] if cmp_ == "gt" else box[edge] < env[edge]
            if too_tight:
                problems.append(
                    "%s.%s is %.4f but the served area reaches %.4f — widen it, or a "
                    "point there is silently rejected" % (key, edge, box[edge], env[edge]))
    return problems


def build_geojson(rings):
    polys = group_rings(rings)
    geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "%d-county coverage area" % len(METRO_COUNTY_FIPS)},
            "geometry": geometry,
        }],
    }


# --- the anchor registry: one anchor per served county, and no county both ----
#
# THE ANCHOR LIST IS THIS GATE'S OWN SURFACE, and until 2026-09-02 nothing
# checked it. `--check` validates the SHIPPED ring against INSIDE/OUTSIDE and
# never rebuilds from METRO_COUNTY_FIPS, so a county added to that tuple
# without an anchor is green by construction — the ring is simply never asked
# about it. That is how Wisconsin greyed out seven counties for two days with
# every gate in the repo passing, and what its validator's
# check_coverage_ring_tracks_roster was written for.
#
# The convention every instance already follows is one INSIDE anchor per served
# county, so the count identity below turns "somebody added a FIPS and forgot
# the anchor" (or the reverse) into a failure, offline, from source alone. A
# true rebuild-and-diff would be stronger and needs TIGERweb, which is why it
# is not in CI; this is what can be proven without the network.
#
# KEY SHAPES DIFFER BY INSTANCE AND BOTH ARE CORRECT. The reference instance
# keys anchors "Place (County)" because its ring is a subset of its state and a
# reader needs to know which county a town vouches for; the statewide instances
# whose ring IS the state key them by county name alone. A check that demanded
# either shape would fail correct instances, so county_of() accepts both.
def county_of(anchor_key):
    """The county an anchor vouches for, from either key shape.

    "Marion (Williamson)" -> "Williamson"; "Bond, 3rd Circuit" -> "Bond";
    "Fond du Lac" -> "Fond du Lac".
    """
    key = anchor_key.strip()
    # No regex on purpose: these modules import only what they build with, and
    # a gate should not add a dependency to say something this simple.
    if key.endswith(")") and "(" in key:
        key = key[key.rindex("(") + 1:-1]
    return key.split(",")[0].strip()


def check_anchor_registry():
    """Problems with the anchor lists themselves, as a list of strings."""
    problems = []
    if len(INSIDE) != len(METRO_COUNTY_FIPS):
        problems.append(
            "%d INSIDE anchor(s) for %d served county/counties — every served "
            "county carries exactly one anchor, so these must match. A county "
            "added to METRO_COUNTY_FIPS without an anchor is never tested "
            "against the ring, and an anchor with no county is testing ground "
            "the wash no longer claims."
            % (len(INSIDE), len(METRO_COUNTY_FIPS)))
    seen = {}
    for key in INSIDE:
        seen.setdefault(county_of(key), []).append(key)
    for county, keys in sorted(seen.items()):
        if len(keys) > 1:
            problems.append(
                "%s has %d INSIDE anchors (%s) — with one anchor per county the "
                "count identity above cannot tell a doubled county from a "
                "missing one" % (county, len(keys), ", ".join(sorted(keys))))
    both = sorted({county_of(k) for k in INSIDE} & {county_of(k) for k in OUTSIDE})
    if both:
        problems.append(
            "%s appear(s) in BOTH INSIDE and OUTSIDE — when a county joins, its "
            "OUTSIDE anchor moves rather than being left behind, or the ring is "
            "asserted to both contain and exclude the same ground" % ", ".join(both))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--state-out", default=STATE_OUT_PATH)
    ap.add_argument("--check", action="store_true",
                    help="validate the shipped files instead of rebuilding")
    args = ap.parse_args()

    if args.check:
        with open(args.out) as f:
            shipped = json.load(f)
        # rings_of() flattens Polygon and MultiPolygon alike, so the anchor test
        # reads the file the same way whether or not the served area is one region.
        rings = rings_of(shipped["features"][0])
        problems = (check_anchor_registry() + validate(rings)
                    + check_envelopes(rings))

        with open(args.state_out) as f:
            shipped_state = json.load(f)
        state_rings = rings_of(shipped_state["features"][0])
        problems += validate_state(state_rings)
        # The served area is Illinois counties, so it cannot leave Illinois.
        # Checked on the SHIPPED pair rather than on fresh geometry: it is the
        # two files that have to agree, and they are simplified separately.
        problems += containment_problems(rings, state_rings)

        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        if problems:
            sys.exit(1)
        print("metro-outline: OK — %d ring(s), %d vertices, all %d inside / %d outside "
              "anchors correct" % (len(rings), sum(len(r) for r in rings),
                                   len(INSIDE), len(OUTSIDE)), file=sys.stderr)
        print("il-state-outline: OK — %d ring(s), %d vertices, all %d Illinois "
              "anchors inside / %d out-of-state anchors outside"
              % (len(state_rings), sum(len(r) for r in state_rings),
                 len(INSIDE) + len(OUTSIDE) - len(NON_ILLINOIS), len(STATE_OUTSIDE)),
              file=sys.stderr)
        return

    rings = [simplify(r) for r in dissolve(fetch_counties())]
    # Same simplifier and the same tolerance as the counties — see the module
    # docstring: the two rings share the river borders and must not drift apart.
    state_rings = [simplify(r) for r in rings_of(fetch_state())]

    problems = (check_anchor_registry()
                + validate(rings) + check_envelopes(rings) + validate_state(state_rings)
                + containment_problems(rings, state_rings))
    for p in problems:
        print("FATAL: %s" % p, file=sys.stderr)
    if problems:
        print("FATAL: refusing to write an outline that misplaces its anchors",
              file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w") as f:
        json.dump(build_geojson(rings), f, separators=(",", ":"))
        f.write("\n")
    size = os.path.getsize(args.out)
    print("wrote %s: %d ring(s), %d vertices, %.1f KB"
          % (args.out, len(rings), sum(len(r) for r in rings), size / 1024.0),
          file=sys.stderr)

    with open(args.state_out, "w") as f:
        json.dump(build_state_geojson(state_rings), f, separators=(",", ":"))
        f.write("\n")
    state_size = os.path.getsize(args.state_out)
    print("wrote %s: %d ring(s), %d vertices, %.1f KB"
          % (args.state_out, len(state_rings),
             sum(len(r) for r in state_rings), state_size / 1024.0),
          file=sys.stderr)


if __name__ == "__main__":
    main()
