#!/usr/bin/env python3
"""
Build the two statewide NG911 emergency-service-area files from the
Wisconsin Office of Emergency Communications' own aggregate — the route
the phase-2 research recorded and the guidebook backlog queued:

  data/app/fire-service-areas.json  which fire department responds at a
                                    point (FireBoundary, layer 3)
  data/app/law-service-areas.json   which law-enforcement agency serves a
                                    point (LawEnforcementBoundary, layer 4)
  data/app/psap-areas.json          which PSAP — public safety answering
                                    point — answers a 911 call placed at
                                    the point (PSAPBoundary, layer 6)
  data/app/ems-service-areas.json   which emergency medical service is
                                    dispatched at the point
                                    (EmergencyMedicalServicesBoundary,
                                    layer 2)

SOURCE. The OEC publishes every county's NG911 GIS filing as one public
feature service (org WI_OEC_GIS, item 593d0da225b24601ad0c21598ef52fb0,
updated roughly weekly) under an explicit licence: "This data is free and
open for use by the public." The schema is the WI NG911 GIS Data
Standards, "nearly identical to the NENA NG911 Standard". These are
RESPONSE areas — who is dispatched where — never taxing districts and
never electing bodies, which is why the cards name no officeholder; the
guidebook's fire cell calls this "the NYC operational shape, not the IL
taxing shape", and Illinois' own Lee County fire entry already ships the
same product one county at a time.

PER-AGENCY DISSOLVE, AND WHY THE KEY IS A PAIR. Counties file one polygon
per ESN-ish sub-area, so one department arrives as several rows (3,046
fire rows over 1,046 agencies at first build). The dissolve key is
DsplayName + Agency_ID, never DsplayName alone, because the bare name is
wrong in both directions at once: two UNRELATED departments share a name
across counties ("Rome Fire Department" files under both a Jefferson
County town's authority and Wood County's, ~100 miles apart), while one
REAL cross-county agency files under both its counties' authorities
(Appleton Fire under Outagamie's and Winnebago's). The pair keeps the two
Romes apart; a genuine cross-county agency ships as one feature per
filing authority, same name on each, which draws the county line inside
its area exactly as the source draws it — the card answer at any point is
identical either way.

EXPIRED ROWS ARE DROPPED BY DATE, NEVER BY COUNT. NENA carries an Expire
column; every expired fire/law row at first build (37 + 18) was
superseded history, and a FUTURE Expire date is a still-effective row
that must ship. The drop is computed against the clock each run.

WHAT THE DATA DOES NOT COVER IS MEASURED AND PINNED. Five authorities'
filings are absent or partial (Iowa, Vilas and Walworth file none of the
four tilings; Jefferson files law and PSAP but neither fire nor EMS;
Polk's law filing covers ~60% while its other three file in full),
and LANGLADE COUNTY HAS NO PROVISIONING BOUNDARY AT ALL — 72 provisioning
polygons where the other 71 counties plus the City of Milwaukee each
carry one. Every rate is recomputed per run inside the counties' own
provisioning polygons and gated against UNFILED below, so a county
completing its filing fails the build loudly and the operator retires the
entry (and the matching gap record) with eyes open. The remaining
"uncovered" area in a naive statewide sample is Great Lakes water inside
TIGER county polygons — measured, not a gap.

AN OPERATOR REBUILD WHOSE DRIFT NOBODY WAS MEASURING, until 2026-09-05. This
docstring used to end "the monthly source report watches the layer counts",
and validate_sources.py's own comment on these four rows called a count change
"the operator's rebuild trigger". Both were true of the INTENT and false of the
code: those rows asked the service for `returnCountOnly=true` and the checker
read only whether the endpoint answered, throwing the number away — so nothing
anywhere held last month's count and nothing could see it move. A trigger with
no baseline is a sentence, which is the same shape as sw.js's "bump CACHE_NAME
whenever…" before check_cache_version.py existed.

WHAT THAT COST, MEASURED THE FIRST TIME ANYONE COMPARED. The EMS layer had
gained an agency the shipped file did not have: 580 live against 579 shipped,
the new key being `Berlin` under wausharacountywi.gov. It was not a hole being
filled. The CITY OF BERLIN straddles the Green Lake / Waushara county line, and
Waushara had filed the city's OWN ambulance service over the city's Waushara
half — 2.1 km2, Census place 5506925, county subdivision 5513706925 — where
this project was still answering `Poy Sippi`, the rural service, for everyone
in it. 400 of 400 sampled points inside that polygon said Poy Sippi on the
shipped file and Berlin on the source, and the live source no longer files Poy
Sippi there at all, so it was a TRANSFER and not one of the concurrent
jurisdictions this layer legitimately carries.

WHAT A 20,000-POINT SAMPLE SAID ABOUT THAT, AND WHY IT WAS WORTHLESS. Such a
sample across all four layers found ZERO changed answers, and a first version of
this docstring concluded from it that the other three layers had "changed BYTES
while changing no answer". THAT WAS FALSE, and review caught it: measured
against main, this rebuild changes the geometry of 138 fire, 161 law, 19 PSAP
and 79 EMS features (PER FEATURE — a first count said 136 and 74 because it
keyed on DsplayName, which collapses the 12 fire and 14 EMS agencies that file
under more than one authority; keying a measurement on the name alone, in the
builder whose whole dissolve key exists because the name alone is not one). The sample could not see any of it — 2.1 km2 of a 169,000
km2 state is one part in eighty thousand, so a 20,000-point sample expects
FEWER THAN ONE hit — and a null result from an instrument with no power is not
evidence of no change. That is the real lesson: the question a staleness check
must ask is "did the source move at all", which is a COUNT and an EDIT DATE,
never a sample; and byte churn is not evidence of a reader-visible change in
either direction.

THE FIX IS A SIDECAR, NOT A CONSTANT. wi/data/source/ng911/built-rows.json is
written by this build on every successful run and carries the row counts the
OEC's own count endpoints reported at that moment; validate_sources.py reads it
monthly and WARNs when the live counts have moved. It is a file rather than a
hand-edited constant because the two must never disagree, and one run writes
both. Its blind spot is stated where it is read: a county REDRAWING a boundary
without changing its row count does not show up.

Prerequisites: curl and Node.js (mapshaper).
"""

import datetime
import json
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from build_wi_supervisory_districts import (  # noqa: E402
    fetch_layer, _model, _districts_at, _bbox, _point_in_geometry,
    _curl, MAPSHAPER, STATE_BBOX)
import dropped_rings as drings  # noqa: E402

REPO_ROOT = os.path.dirname(SCRIPT_DIR)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")

OEC = ("https://services3.arcgis.com/GoOAGCoqFEhZEh7f/arcgis/rest/services"
       "/WI_NG911_GIS_Service_Polygons_and_Road_Centerline_Data_v2/FeatureServer")
EMS = OEC + "/2"
FIRE = OEC + "/3"
LAW = OEC + "/4"
PROVISIONING = OEC + "/5"
PSAP = OEC + "/6"

LAYERS = [
    {"name": "fire", "url": FIRE, "out": "fire-service-areas.json",
     "min_rows": 2800, "min_agencies": 950},
    {"name": "law", "url": LAW, "out": "law-service-areas.json",
     "min_rows": 2900, "min_agencies": 600},
    # PSAP is the tiling where the date filter EARNS its by-date form: 11 of
    # its 208 raw rows carried FUTURE Expire dates at first measurement —
    # still-effective rows a drop-anything-with-Expire filter would delete.
    # 205 effective rows over 95 answering points; its rare overlaps
    # (a county PSAP and a city PD's own dispatch both filed, ~0.1% of
    # points) render like law's, every center at the point.
    {"name": "psap", "url": PSAP, "out": "psap-areas.json",
     "min_rows": 190, "min_agencies": 88},
    # EMS re-proves the pair key on ambulance services: regional providers
    # (Emplify, Tri State) file under multiple counties' authorities, and a
    # few EMS Agency_IDs are not county domains at all (BVEM files under
    # BVEM1/BVEM2) — the pair still keys them correctly. 2,443 effective
    # rows over 579 services at first measurement (2026-08-26); 2,444 over
    # 580 at the 2026-09-05 rebuild, the extra one being Berlin. Essentially
    # no cross-name overlap (1 same-name multi-hit in 3,000 points).
    {"name": "ems", "url": EMS, "out": "ems-service-areas.json",
     "min_rows": 2300, "min_agencies": 530},
]

# Filing absences, pinned exactly as measured 2026-08-26 (40 seeded sample
# points inside each authority's own provisioning polygon; flagged under
# 90% coverage). Keyed by the provisioning DiscrpAgID; the value is the
# set of layers that authority has NOT (fully) filed. Mirrored by the gap
# records ng911-fire-filings / ng911-law-filings — retire both together.
UNFILED = {
    "iowacounty.org": {"fire", "law", "psap", "ems"},
    "vilascountywi.gov": {"fire", "law", "psap", "ems"},
    "co.walworth.wi.us": {"fire", "law", "psap", "ems"},
    "jeffersoncountywi.gov": {"fire", "ems"},  # law and PSAP file in full
    "polkcountywi.gov": {"law"},          # partial: ~60% covered at pin time
}
EXPECT_PROVISIONING = 72   # 71 counties + the City of Milwaukee; Langlade absent
NO_PROVISIONING = "langlade"

# THE DROPPED-RING QUESTION WAS ASKED OF ALL FOUR LAYERS ON 2026-09-27, AND THE
# ANSWER WAS THE WORST IN THE FLEET. The comment that stood here said the
# question was unasked and that visvalingam was likely costing readers answers,
# on the county-supervisory layer's evidence. It was, by a wide margin. At the
# `8%` this constant used to hold, measured against the full-precision dissolve
# of the same fetch:
#
#     layer  dropped rings  answers changed   of which wrong-name
#     fire        229              64                 36
#     law         389             296                264
#     psap         37              28                  5
#     ems         195              44                 19
#
# 432 rings across the four layers changed the agency a reader is told answers at
# their point, and EVERY ONE OF THOSE FOUR BUILDS REPORTED 4000/4000 (100.000%)
# NAME-SET AGREEMENT. That gate scatters 4,000 points over the whole state and
# the rings are slivers along county-filing seams, so it is blind to them by
# construction — the same blindness `wi/WATCH.md` row 58 records on this very
# layer, where a 20,000-point sample saw nothing while a rebuild had changed 397
# features. A sample cannot find a sliver; only asking each dropped ring what it
# answers can.
#
# THE WRONG-NAME HALF IS WHY THIS MATTERS MORE HERE THAN ON A DISTRICT LAYER.
# On the supervisory and aldermanic layers a dropped ring mostly took a reader's
# answer away. Here a neighbour fills it, so a reader is told the WRONG fire
# department, the WRONG police agency, the WRONG 911 answering point: Somers Fire
# & Rescue read as Kenosha Fire, the Oneida Nation's own police department read as
# City of Green Bay PD, Wausau PD read as the Marathon County Sheriff.
#
# DOUGLAS-PEUCKER AT A METRE INTERVAL IS THE FIX, and the algorithm rather than
# the dial is what does the work — the finding `build_legislative_boundaries.py`
# already records. Visvalingam thresholds triangle AREA, which does not bound how
# far the drawn line strays and drops a small ring outright; dp thresholds
# perpendicular DEVIATION. Measured on the same fetch (gzipped bytes, which is
# what a reader downloads):
#
#     layer  setting              dropped  changed  gzipped
#     fire   visvalingam 8%           229       64   963,658
#     fire   dp interval=1            157        1 1,920,288
#     law    visvalingam 8%           389      296 1,031,353
#     law    dp interval=1            103       16 2,222,125
#     psap   visvalingam 8%            37       28   381,488
#     psap   dp interval=2              7        0   503,747
#     ems    visvalingam 8%           195       44   756,603
#     ems    dp interval=1            142        0 1,535,934
#
# THE SETTING IS PER LAYER BECAUSE THE RULE IS MEASURED PER LAYER, never pooled.
# Size breaks a tie only among settings that tie on EVERY instrument — answers
# changed, the dissolve+simplify name-set agreement, and the independent
# server point gate — and psap is the one layer where that happens: interval=1
# and interval=2 both change NO answer there, so the smaller wins. Nothing ties
# on the other three, so their answer-count decides alone. The full table,
# including intervals 2, 4 and 7 for every layer, is in the pull request that
# made this change and summarised in `wi/WATCH.md`.
#
# ONE TABLE, AND THE LABEL IS DERIVED FROM IT. A label beside the arguments is a
# second copy of one fact and would eventually disagree with what mapshaper was
# actually given, which is the defect this repository keeps paying for; the
# reader-facing string is built from the arguments instead.
# KEY separator; never appears in either field. It sits ABOVE the
# declaration tables because those write agency KEYs with it rather than
# with a raw escape, which is the difference between a reader seeing
# "Madison PD" and seeing "Madison PD\x1fwww.cityofmadison.com".
SEP = "\x1f"

SIMPLIFY = {
    "fire": ["dp", "keep-shapes", "interval=1"],
    "law": ["dp", "keep-shapes", "interval=1"],
    "psap": ["dp", "keep-shapes", "interval=2"],
    "ems": ["dp", "keep-shapes", "interval=1"],
}


def simplify_label(name):
    return " ".join(a for a in SIMPLIFY[name] if a != "keep-shapes")


# Holes that NO agency covered and the drawn output now fills, per layer, pinned
# exactly. `dropped_rings` argues why these are not declared one by one and why
# it is still an inference; the count is held so a rebuild that closes a
# different number of them stops and gets read. These move with the setting —
# measured at the settings above.
#
# THEY ALSO MOVE WITH THE INSTRUMENT, AND ON 2026-09-27 THAT IS WHAT MOVED
# THREE OF THEM: fire 78 -> 82, law 53 -> 59 and ems 75 -> 77 with the settings
# above untouched and the shipped geometry byte-identical. `find_dropped` used
# to ask whether ANY of a source ring's vertices survived anywhere in its
# agency's drawn geometry; a ring joined to the main body at one shared vertex
# answered yes after vanishing whole. So every count this table has ever held
# was a FLOOR, and the same blindness put five real answer changes in the harm
# table below (four on law, one on psap, whose count did not move at all).
GAP_CLOSED = {"fire": 82, "law": 59, "psap": 6, "ems": 77}

# Every dropped ring that changes the agency a reader is told answers at their
# point, declared one by one, per layer. `drings.check` FAILS the build on an
# undeclared harm and on a declaration that matches no ring, and the failure
# path below prints the measured rows to paste here.
#
# EACH `interior` IS WRITTEN AT ITS OWN `decimals` AND NOT AT SIX. These rings are
# hairlines under a metre wide, and `dropped_rings.interior_at_precision` RAISES
# the precision for a ring six decimals cannot hold a point inside — seven of
# these seventeen need seven decimals and one needs eight. A generator that
# formatted every coordinate to six undid that silently and put the point outside
# its own ring; the gate caught all seven, which is what it is for, but the next
# person regenerating this table should copy the measured value rather than
# reformat it.
ACCEPTED_DROPPED_RINGS = {
    "fire": [
        # THE ONLY RING THE FIRE LAYER LOSES, AND ITS LIMIT IS THE OUTPUT
        # PRECISION RATHER THAN AN UNTURNED DIAL. A 3-vertex triangle 15.19 m
        # long whose middle vertex sits 0.175 m off the line between the other
        # two -- measured, and the same number two ways (twice the area over the
        # longest side). dp thresholds perpendicular DEVIATION, so any interval
        # at or above 0.18 m removes that vertex and the ring goes with it; at
        # interval=0.5 this file is 23 per cent larger gzipped and loses exactly
        # the same ring. Keeping it would need an interval finer than 1.6 of the
        # 6-decimal coordinate cells this file ships at (0.079 m x 0.111 m here),
        # which is asking the simplifier to preserve something the output format
        # cannot reliably carry.
        #
        # THE GROUND IS IN WAUSAU CITY AND MARATHON COUNTY FILES IT UNDER THE TOWN
        # OF TEXAS'S DEPARTMENT, which is context and not a justification: fire
        # response does not follow a municipal boundary, so the answer a reader
        # now gets is not "actually right" -- it is the county's own filing lost
        # to a seam.
        {
            "lat": 45.002763, "lng": -89.621292, "verts": 3, "m2": 1.33,
            "interior": {"lat": 45.002760, "lng": -89.621249, "decimals": 6},
            "features": ["fire:Texas Fire Department" + SEP + "marathoncounty.gov"],
            "kind": "wrong-name",
            "answer_before": {"fire": ["Texas Fire Department" + SEP + "marathoncounty.gov"]},
            "answer_after": {"fire": ["Wausau Fire Department" + SEP + "marathoncounty.gov"]},
            "why": "1.33 m2 in Wausau city, dry land by TIGER's areal hydrography "
                   "(four controls answered first), a hairline averaging 0.17 m "
                   "wide over a 15 m span; a reader is answered Wausau Fire "
                   "Department where the filing says Texas Fire Department",
            "date": "2026-09-27",
        },
    ],
    "law": [
        # SEVEN RINGS IN DANE COUNTY, all between the City of Madison's own law
        # zone and whatever abuts it -- the county Sheriff, Shorewood Hills PD,
        # University PD, the State Patrol. Every one is a hairline: mean widths
        # 0.002 m to 0.61 m, over spans of 1.6 m to 155 m. These are two
        # publishers' pen strokes not meeting, rather than ground anyone occupies
        # as a place, and they are declared one by one anyway because this
        # module's own rule is that AREA DOES NOT DECIDE -- a 0.008 m2 sliver and
        # a 2,162 m2 one both cost a reader exactly one wrong answer.
        #
        # ONE OF THEM IS IN A CREEK AND SAYS SO. Sixteen of the seventeen rings
        # this builder declares are dry land; the 1.11 m2 one at
        # 43.056617,-89.404710 is inside Wingra Creek by TIGER's own areal
        # hydrography. That is why the surface is measured per ring rather than
        # asserted once for the group -- asserting it would have been wrong here.
        {
            "lat": 43.028317, "lng": -89.258280, "verts": 4, "m2": 9.38,
            "interior": {"lat": 43.027875, "lng": -89.257558, "decimals": 6},
            "features": ["law:Madison PD" + SEP + "www.cityofmadison.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Madison PD" + SEP + "www.cityofmadison.com"]},
            "answer_after": {"law": ["Sheriff" + SEP + "countyofdane.com"]},
            "why": "9.38 m2 in Blooming Grove town, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.13 m wide over a 140 m span; a reader is answered "
                   "Sheriff where the filing says Madison PD",
            "date": "2026-09-27",
        },
        {
            "lat": 43.083697, "lng": -89.446041, "verts": 10, "m2": 9.19,
            "interior": {"lat": 43.083286, "lng": -89.446049, "decimals": 6},
            "features": ["law:Madison PD" + SEP + "www.cityofmadison.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Madison PD" + SEP + "www.cityofmadison.com"]},
            "answer_after": {"law": ["Shorewood Hills PD" + SEP + "www.shorewood-hills.org"]},
            "why": "9.19 m2 in Madison city, dry land by TIGER's areal hydrography "
                   "(four controls answered first), 10 vertices and no span "
                   "measured; a reader is answered Shorewood Hills PD where the "
                   "filing says Madison PD",
            "date": "2026-09-27",
        },
        {
            "lat": 43.063883, "lng": -89.542776, "verts": 3, "m2": 8.55,
            "interior": {"lat": 43.063885, "lng": -89.542254, "decimals": 6},
            "features": ["law:Madison PD" + SEP + "www.cityofmadison.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Madison PD" + SEP + "www.cityofmadison.com"]},
            "answer_after": {"law": ["University PD" + SEP + "uwpd.wisc.edu"]},
            "why": "8.55 m2 in Middleton town, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.11 m wide over a 155 m span; a reader is answered "
                   "University PD where the filing says Madison PD",
            "date": "2026-09-27",
        },
        {
            "lat": 43.067606, "lng": -89.543814, "verts": 4, "m2": 3.54,
            "interior": {"lat": 43.0676055, "lng": -89.5441608, "decimals": 7},
            "features": ["law:Madison PD" + SEP + "www.cityofmadison.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Madison PD" + SEP + "www.cityofmadison.com"]},
            "answer_after": {"law": ["Sheriff" + SEP + "countyofdane.com"]},
            "why": "3.54 m2 in Madison city, dry land by TIGER's areal hydrography "
                   "(four controls answered first), a hairline averaging 0.07 m "
                   "wide over a 99 m span; a reader is answered Sheriff where the "
                   "filing says Madison PD",
            "date": "2026-09-27",
        },
        {
            "lat": 43.056617, "lng": -89.404710, "verts": 4, "m2": 1.11,
            "interior": {"lat": 43.056602, "lng": -89.404711, "decimals": 6},
            "features": ["law:Madison PD" + SEP + "www.cityofmadison.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Madison PD" + SEP + "www.cityofmadison.com"]},
            "answer_after": {"law": ["Sheriff" + SEP + "countyofdane.com"]},
            "why": "1.11 m2 in Madison city, and it is WATER: TIGER's areal "
                   "hydrography puts it in Wingra Crk, a hairline averaging 0.61 m "
                   "wide over a 4 m span; a reader is answered Sheriff where the "
                   "filing says Madison PD",
            "date": "2026-09-27",
        },
        {
            "lat": 43.149518, "lng": -89.305004, "verts": 3, "m2": 0.03,
            "interior": {"lat": 43.1495145, "lng": -89.3050019, "decimals": 7},
            "features": ["law:Madison PD" + SEP + "www.cityofmadison.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Madison PD" + SEP + "www.cityofmadison.com"]},
            "answer_after": {"law": ["Sheriff" + SEP + "countyofdane.com"]},
            "why": "0.03 m2 in Madison city, dry land by TIGER's areal hydrography "
                   "(four controls answered first), a hairline averaging 0.04 m "
                   "wide over a 2 m span; a reader is answered Sheriff where the "
                   "filing says Madison PD",
            "date": "2026-09-27",
        },
        {
            "lat": 43.148152, "lng": -89.304200, "verts": 3, "m2": 0.01,
            "interior": {"lat": 43.14814900, "lng": -89.30419804, "decimals": 8},
            "features": ["law:Madison PD" + SEP + "www.cityofmadison.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Madison PD" + SEP + "www.cityofmadison.com"]},
            "answer_after": {"law": ["State Patrol" + SEP + "wsp.wi.gov"]},
            "why": "0.01 m2 in Madison city, dry land by TIGER's areal hydrography "
                   "(four controls answered first), a hairline averaging 0.01 m "
                   "wide over a 2 m span; a reader is answered State Patrol where "
                   "the filing says Madison PD",
            "date": "2026-09-27",
        },
        # NINE RINGS IN BROWN COUNTY, around the seam where the Hobart-Lawrence,
        # Ashwaubenon, Oneida Nation and Green Bay law zones meet. FOUR OF THEM
        # ARE MIXED -- the SOURCE answers two or three ways at different points
        # inside one ring, because three of those agencies' filings overlap
        # there -- so each declares every pair it shows rather than one of them.
        # No interval resolves that: the simplifier did not author the ambiguity,
        # the filings did. `dropped_rings.check` refused a mixed ring outright
        # until 2026-09-27, which is what made this layer undeclarable; it is
        # declarable now and still refuses one described with a single pair.
        #
        # GOING FINER BUYS ALMOST NOTHING HERE, MEASURED. At dp interval=0.5 the
        # law layer changes 15 answers against 16 at interval=1, with the same
        # four mixed rings -- so at most one of these sixteen is recoverable, for
        # 505 KB more gzipped on a file a reader fetches only to pin a
        # comparison. At the visvalingam 8 per cent this builder shipped until
        # today it changed 296, and TWELVE were mixed.
        {
            "lat": 44.500180, "lng": -88.137851, "verts": 3, "m2": 2.34,
            "interior": {"lat": 44.499304, "lng": -88.137861, "decimals": 6},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL1" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Hobart-Lawrence Police Department Law Zone HL1" + SEP + "browncountywi.gov"]},
            "answer_after": {"law": ["City of Green Bay Police Department Law Zone GBA1" + SEP + "browncountywi.gov"]},
            "why": "2.34 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.01 m wide over a 319 m span; a reader is answered "
                   "City of Green Bay Police Department Law Zone GBA1 where the "
                   "filing says Hobart-Lawrence Police Department Law Zone HL1",
            "date": "2026-09-27",
        },
        {
            "lat": 44.527479, "lng": -88.146430, "verts": 4, "m2": 1.72,
            "interior": {"lat": 44.527449, "lng": -88.146487, "decimals": 6},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL1" + SEP + "browncountywi.gov", "law:Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Hobart-Lawrence Police Department Law Zone HL1" + SEP + "browncountywi.gov"]},
            "answer_after": {"law": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
            "why": "1.72 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.18 m wide over a 19 m span; a reader is answered "
                   "Oneida Police Department Law Zone HLOB where the filing says "
                   "Hobart-Lawrence Police Department Law Zone HL1",
            "date": "2026-09-27",
        },
        {
            "lat": 44.445904, "lng": -88.133036, "verts": 5, "m2": 0.63,
            "interior": {"lat": 44.445835, "lng": -88.133040, "decimals": 6},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_pairs": {"law": [
                {"before": ["Ashwaubenon Public Safety Law Zone ASW" + SEP + "browncountywi.gov"],
                 "after": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
                {"before": ["Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
                 "after": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
            ]},
            "why": "0.63 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.07 m wide over a 19 m span; the source answers 2 "
                   "ways inside it, so every pair is declared here rather than one "
                   "of them chosen",
            "date": "2026-09-27",
        },
        {
            "lat": 44.446505, "lng": -88.132941, "verts": 10, "m2": 0.29,
            "interior": {"lat": 44.446495, "lng": -88.132944, "decimals": 6},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_pairs": {"law": [
                {"before": ["Ashwaubenon Public Safety Law Zone ASW" + SEP + "browncountywi.gov"],
                 "after": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
                {"before": ["Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
                 "after": ["Ashwaubenon Public Safety Law Zone ASW" + SEP + "browncountywi.gov"]},
                {"before": ["Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
                 "after": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
            ]},
            "why": "0.29 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), 10 vertices and no "
                   "span measured; the source answers 3 ways inside it, so every "
                   "pair is declared here rather than one of them chosen",
            "date": "2026-09-27",
        },
        {
            "lat": 44.535119, "lng": -88.122052, "verts": 3, "m2": 0.10,
            "interior": {"lat": 44.5351175, "lng": -88.1223406, "decimals": 7},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL1" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_before": {"law": ["City of Green Bay Police Department Law Zone GBA1" + SEP + "browncountywi.gov"]},
            "answer_after": {"law": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
            "why": "0.10 m2 in Green Bay city, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.00 m wide over a 125 m span; a reader is answered "
                   "Oneida Police Department Law Zone HLOB where the filing says "
                   "City of Green Bay Police Department Law Zone GBA1",
            "date": "2026-09-27",
        },
        {
            "lat": 44.446223, "lng": -88.133003, "verts": 3, "m2": 0.03,
            "interior": {"lat": 44.446228, "lng": -88.133002, "decimals": 6},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"]},
            "answer_after": {"law": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
            "why": "0.03 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.03 m wide over a 2 m span; a reader is answered "
                   "Oneida Police Department Law Zone HLOB where the filing says "
                   "Hobart-Lawrence Police Department Law Zone HL2",
            "date": "2026-09-27",
        },
        {
            "lat": 44.446711, "lng": -88.132879, "verts": 7, "m2": 0.03,
            "interior": {"lat": 44.4466985, "lng": -88.1328829, "decimals": 7},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_pairs": {"law": [
                {"before": ["Ashwaubenon Public Safety Law Zone ASW" + SEP + "browncountywi.gov"],
                 "after": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
                {"before": ["Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
                 "after": ["Ashwaubenon Public Safety Law Zone ASW" + SEP + "browncountywi.gov"]},
            ]},
            "why": "0.03 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.02 m wide over a 3 m span; the source answers 2 "
                   "ways inside it, so every pair is declared here rather than one "
                   "of them chosen",
            "date": "2026-09-27",
        },
        {
            "lat": 44.445775, "lng": -88.133042, "verts": 3, "m2": 0.01,
            "interior": {"lat": 44.4457662, "lng": -88.1330419, "decimals": 7},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"]},
            "answer_after": {"law": ["Ashwaubenon Public Safety Law Zone ASW" + SEP + "browncountywi.gov"]},
            "why": "0.01 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.00 m wide over a 9 m span; a reader is answered "
                   "Ashwaubenon Public Safety Law Zone ASW where the filing says "
                   "Hobart-Lawrence Police Department Law Zone HL2",
            "date": "2026-09-27",
        },
        {
            "lat": 44.446640, "lng": -88.132903, "verts": 5, "m2": 0.01,
            "interior": {"lat": 44.4466345, "lng": -88.1329045, "decimals": 7},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_pairs": {"law": [
                {"before": ["Ashwaubenon Public Safety Law Zone ASW" + SEP + "browncountywi.gov"],
                 "after": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
                {"before": ["Hobart-Lawrence Police Department Law Zone HL2" + SEP + "browncountywi.gov"],
                 "after": ["Oneida Police Department Law Zone HLOB" + SEP + "browncountywi.gov"]},
            ]},
            "why": "0.01 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "averaging 0.01 m wide over a 2 m span; the source answers 2 "
                   "ways inside it, so every pair is declared here rather than one "
                   "of them chosen",
            "date": "2026-09-27",
        },
        # FOUR MORE RINGS, FOUND ONLY WHEN THE RETAINED TEST BECAME EXACT
        # (2026-09-27). The old test asked whether ANY of a source ring's
        # vertices survived anywhere in its agency's drawn geometry, so a ring
        # joined to the main body at one shared vertex read as retained after
        # vanishing whole. This layer's gap-closed count moved 53 -> 59 in the
        # same change, which is the same blindness counted on the harmless side.
        #
        # TWO OF THEM ARE NOT DANE COUNTY AT ALL and neither county was guessed
        # at. The 51.11 m2 one is Marquette County's own filing reaching into
        # Waushara, and the two Brown County ones are one municipal department's
        # zone against another's. Both were established from TIGER's county layer
        # rather than from the agency names, which is how the psap entry below
        # stopped being called a county-line sliver.
        {
            "lat": 43.982814, "lng": -89.212088, "verts": 3, "m2": 51.11,
            "interior": {"lat": 43.982788, "lng": -89.215457, "decimals": 6},
            "features": ["law:MASON" + SEP + "co.marquette.wi.us"],
            "kind": "wrong-name",
            "answer_before": {"law": ["MASON" + SEP + "co.marquette.wi.us"]},
            "answer_after": {"law": ["Marion PD/Waushara SO" + SEP + "wausharacountywi.gov"]},
            "why": "51.11 m2 in Marion town, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "0.13 m wide over an 812 m span and the longest ring this "
                   "builder declares; both its ends sit in WAUSHARA county "
                   "within 100 m of the Marquette line, so this is Marquette's "
                   "filing reaching across it, and a reader is answered "
                   "Waushara's agency where Marquette's filing claims the ground",
            "date": "2026-09-27",
        },
        {
            "lat": 43.018722, "lng": -89.242425, "verts": 4, "m2": 20.20,
            "interior": {"lat": 43.016213, "lng": -89.238099, "decimals": 6},
            "features": ["law:Sheriff" + SEP + "countyofdane.com"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Sheriff" + SEP + "countyofdane.com"]},
            "answer_after": {"law": ["State Patrol" + SEP + "wsp.wi.gov"]},
            "why": "20.20 m2 in McFarland village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "0.05 m wide over a 765 m span; Dane is the only county "
                   "within 2 km, so this is two agencies' filings inside one "
                   "county rather than a boundary, and a reader is answered "
                   "State Patrol where the filing says Sheriff",
            "date": "2026-09-27",
        },
        {
            "lat": 44.454239, "lng": -88.175166, "verts": 3, "m2": 3.22,
            "interior": {"lat": 44.454239, "lng": -88.175404, "decimals": 6},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL2"
                         + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Hobart-Lawrence Police Department Law Zone HL2"
                                      + SEP + "browncountywi.gov"]},
            "answer_after": {"law": ["Oneida Police Department Law Zone HLOB"
                                     + SEP + "browncountywi.gov"]},
            "why": "3.22 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "0.11 m wide over a 58 m span; a reader is answered Oneida "
                   "Police Department where the filing says Hobart-Lawrence",
            "date": "2026-09-27",
        },
        {
            "lat": 44.513650, "lng": -88.172516, "verts": 3, "m2": 1.72,
            "interior": {"lat": 44.513473, "lng": -88.173323, "decimals": 6},
            "features": ["law:Hobart-Lawrence Police Department Law Zone HL1"
                         + SEP + "browncountywi.gov"],
            "kind": "wrong-name",
            "answer_before": {"law": ["Hobart-Lawrence Police Department Law Zone HL1"
                                      + SEP + "browncountywi.gov"]},
            "answer_after": {"law": ["Oneida Police Department Law Zone HLOB"
                                     + SEP + "browncountywi.gov"]},
            "why": "1.72 m2 in Hobart village, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "0.03 m wide over a 137 m span; a reader is answered Oneida "
                   "Police Department where the filing says Hobart-Lawrence",
            "date": "2026-09-27",
        },
    ],
    "psap": [
        # THIS ENTRY REPLACED A CLAIM THAT PSAP DECLARED NOTHING. The sentence
        # here read "PSAP AND EMS DECLARE NOTHING, AND THAT IS A MEASUREMENT
        # RATHER THAN AN OMISSION: at the settings above, NO dropped ring changes
        # any answer on either layer", and it was true of the instrument that
        # measured it and false of the layer. It stays quoted because the reason
        # it was wrong is the finding: the old retained test asked whether ANY of
        # a source ring's vertices survived anywhere in its agency's drawn
        # geometry, so a ring joined to the main body at one shared vertex read as
        # retained after vanishing whole. It remains true of EMS, whose list is
        # still empty below and whose gap-closed count did move (75 -> 77).
        #
        # PSAP'S OWN GAP-CLOSED COUNT DID NOT MOVE — 6 before and after — so
        # nothing in the counts hinted at this ring. That is worth stating: on
        # this layer the exact test changed no harmless number at all and still
        # turned up an answer nobody was counting.
        #
        # At visvalingam 8 per cent psap changed 28 answers (23 of them readers
        # told NO answering point answers where one does) and ems 44.
        #
        # IT IS NOT A COUNTY-LINE SLIVER, WHICH IS WHAT IT LOOKED LIKE. Two
        # counties' PSAPs are named, so the first reading was that the ring sits
        # on the line between them. Measured against TIGER's county layer, both
        # ends are in CALUMET and Outagamie appears only at 2 km, not at 500 m —
        # so Outagamie's PSAP filing reaches about a kilometre into Calumet, and
        # the ring is where the two overlap inside Appleton city, which straddles
        # both counties. The agency names were the wrong instrument for that
        # question.
        {
            "lat": 44.229038, "lng": -88.358372, "verts": 3, "m2": 0.54,
            "interior": {"lat": 44.2290365, "lng": -88.3584619, "decimals": 7},
            "features": ["psap:Calumet County PSAP" + SEP + "calumetcounty.org"],
            "kind": "wrong-name",
            "answer_before": {"psap": ["Calumet County PSAP" + SEP + "calumetcounty.org"]},
            "answer_after": {"psap": ["Outagamie County PSAP" + SEP + "outagamie.org"]},
            "why": "0.54 m2 in Appleton city, dry land by TIGER's areal "
                   "hydrography (four controls answered first), a hairline "
                   "0.04 m wide over a 25 m span; both ends are in Calumet "
                   "county with Outagamie no nearer than 2 km, so this is one "
                   "county's filing reaching into another rather than a line "
                   "between them, and a reader is answered Outagamie's PSAP "
                   "where the filing says Calumet's",
            "date": "2026-09-27",
        },
    ],
    # EMS DECLARES NOTHING AND THAT IS STILL A MEASUREMENT: at the setting above,
    # no dropped ring changes any answer on this layer, re-measured 2026-09-27
    # under the exact retained test that gave psap its entry.
    "ems": [],
}
PRECISION = "0.000001"     # 6 decimals ~= 0.11 m
COVERAGE_SAMPLES = 40      # per provisioning polygon, seeded
VALIDATE_SAMPLES = 4000    # statewide dissolve+simplify agreement gate


def fetch_retry(url, fields, attempts=3):
    """services3.arcgis.com drops the occasional mid-paging request (curl
    exit 92, an HTTP/2 stream reset — measured on the first live build);
    the shared pager has no retry, so the whole fetch retries here."""
    import time
    for attempt in range(attempts):
        try:
            return fetch_layer(url, fields)
        except subprocess.CalledProcessError:
            if attempt == attempts - 1:
                raise
            time.sleep(5 * (attempt + 1))


def effective(features):
    """Drop rows whose Expire date has passed — superseded filings. A future
    Expire is still in force and ships; the counts are printed, never pinned,
    because they move with the OEC's weekly refresh."""
    now_ms = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
              ).total_seconds() * 1000
    keep, dropped, future = [], 0, 0
    for f in features:
        exp = f["properties"].get("Expire")
        if exp and exp < now_ms:
            dropped += 1
            continue
        if exp:
            future += 1
        keep.append(f)
    return keep, dropped, future


def keyed(features, layer_name):
    """Attach the dissolve KEY; refuse rows a card could not answer from."""
    for f in features:
        p = f["properties"]
        name = (p.get("DsplayName") or "").strip()
        agency = (p.get("Agency_ID") or "").strip()
        if not name or not agency:
            raise RuntimeError("%s: a row is missing DsplayName or Agency_ID "
                               "(NGUID %r) — the schema moved, re-measure"
                               % (layer_name, p.get("NGUID")))
        if SEP in name or SEP in agency:
            raise RuntimeError("%s: the KEY separator appears in %r" % (layer_name, name))
        f["properties"] = {"KEY": name + SEP + agency, "NAME": name}
    return features


def sample_inside(geom, n, seed):
    """n seeded uniform points inside a polygon (rejection over its bbox)."""
    import random
    rng = random.Random(seed)
    bb = _bbox(geom)
    pts, tries = [], 0
    while len(pts) < n and tries < n * 200:
        tries += 1
        pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
        if _point_in_geometry(pt, geom):
            pts.append(pt)
    return pts


def gate_against_server(layer, out_feats, samples=25):
    """Ask the SERVICE which agencies cover a point, and compare to what the
    shipped file answers there. THIS IS THE ONLY GATE HERE THAT IS INDEPENDENT.

    validate() below samples 4,000 points, but it compares the dissolved output
    against the SAME fetch it was built from, so it agrees with itself by
    construction — which is exactly how the MASON hole (see fetch_layer's
    esri_rings_to_geojson) passed every gate while shipping a wrong card. This
    one asks the server, whose geometry this project does not hold, so a defect
    introduced anywhere between the query and the written file shows up.

    Deliberately small: 25 points is 25 round trips per layer, enough to catch a
    systematic defect and not a proof of per-point correctness. A disagreement
    FAILS the build rather than warning — the server is the authority here.
    """
    import random
    import urllib.parse
    model = _model(out_feats, "NAME")
    rng = random.Random(4242)
    bb = STATE_BBOX
    checked = 0
    attempts = 0
    while checked < samples and attempts < samples * 40:
        attempts += 1
        pt = (rng.uniform(bb["minLng"], bb["maxLng"]),
              rng.uniform(bb["minLat"], bb["maxLat"]))
        ours = set(_districts_at(model, pt))
        if not ours:
            continue          # outside coverage; the server has nothing to compare
        params = {
            "geometry": "%f,%f" % pt,
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "DsplayName",
            "returnGeometry": "false",
            "where": "1=1",
            "f": "json",
        }
        data = json.loads(_curl(layer["url"] + "/query?" + urllib.parse.urlencode(params)))
        theirs = {(f["attributes"].get("DsplayName") or "").strip()
                  for f in (data.get("features") or [])}
        theirs.discard("")
        # Expired rows this build drops can still answer on the server, so the
        # server may legitimately name MORE than we do; it must never name FEWER.
        if not ours <= theirs:
            raise RuntimeError(
                "%s: the shipped file answers %s at %.5f,%.5f where the service "
                "answers %s — the built geometry claims coverage the source does "
                "not. Re-read fetch_layer's esri_rings_to_geojson before touching "
                "anything else."
                % (layer["name"], sorted(ours), pt[0], pt[1], sorted(theirs)))
        checked += 1
    if checked < samples:
        raise RuntimeError("%s: only %d of %d sample points landed in coverage"
                           % (layer["name"], checked, samples))
    print("%s: %d/%d sampled points agree with the service's own point query"
          % (layer["name"], checked, samples), file=sys.stderr)


def gate_filings(feats_by_layer):
    """Recompute per-authority coverage inside the provisioning polygons and
    refuse the build if it disagrees with the pinned UNFILED map."""
    prov = fetch_layer(PROVISIONING, "DiscrpAgID")
    if len(prov) != EXPECT_PROVISIONING:
        raise RuntimeError("provisioning layer carries %d polygons, expected %d — "
                           "an authority joined or left; re-measure UNFILED and the "
                           "gap records before moving this number"
                           % (len(prov), EXPECT_PROVISIONING))
    if any(NO_PROVISIONING in (f["properties"].get("DiscrpAgID") or "").lower()
           for f in prov):
        raise RuntimeError("Langlade County now carries a provisioning polygon — "
                           "its no-provisioning record (and the gap records) are "
                           "stale; re-measure")
    models = {name: _model(feats, "KEY") for name, feats in feats_by_layer.items()}
    computed = {}
    for i, f in enumerate(prov):
        agid = (f["properties"].get("DiscrpAgID") or "").strip()
        pts = sample_inside(f["geometry"], COVERAGE_SAMPLES, seed=7 + i)
        if not pts:
            raise RuntimeError("no sample points landed inside provisioning %r" % agid)
        missing = set()
        for lname, model in models.items():
            hit = sum(1 for pt in pts if _districts_at(model, pt))
            if 100.0 * hit / len(pts) < 90:
                missing.add(lname)
        if missing:
            computed[agid] = missing
    if computed != UNFILED:
        raise RuntimeError(
            "measured filing absences differ from the pinned UNFILED map — a county "
            "filed (or a filing broke). Re-measure, then move UNFILED and the gap "
            "records together.\n  computed: %s\n  pinned:   %s"
            % (sorted((k, sorted(v)) for k, v in computed.items()),
               sorted((k, sorted(v)) for k, v in UNFILED.items())))
    return len(prov)


def validate(source_feats, result_feats):
    """Statewide seeded sample: wherever the full-precision source answers a
    NAME set, the dissolved+simplified output must answer the same set. Name
    sets, not single names, because law jurisdictions genuinely overlap (a
    sheriff and a municipal PD both filed over ~0.5% of points at first
    build) and the card renders every agency at the point."""
    import random
    src = _model(source_feats, "NAME")
    new = _model(result_feats, "NAME")
    rng = random.Random(2026)
    tested = agree = 0
    while tested < VALIDATE_SAMPLES:
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        o_hits = _districts_at(src, pt)
        if not o_hits:
            continue
        tested += 1
        if set(_districts_at(new, pt)) == set(o_hits):
            agree += 1
    pct = 100.0 * agree / tested
    if pct < 99.9:
        raise RuntimeError("dissolve+simplify agreement only %.3f%% (need >= 99.9%%)"
                           % pct)
    return "%d/%d (%.3f%%) name-set agreement" % (agree, tested, pct)


def build(layer, check_only):
    feats = fetch_retry(layer["url"], "DsplayName,Agency_ID,NGUID,Expire")
    feats, dropped, future = effective(feats)
    # TOTAL is what returnCountOnly reports — effective rows PLUS the expired
    # ones this build drops. The monthly staleness check (below) compares the
    # live count endpoint against it, so the two must be the same quantity;
    # comparing against the effective count would drift on its own every time
    # a row's Expire date passed, with no source change at all.
    total = len(feats) + dropped
    if len(feats) < layer["min_rows"]:
        raise RuntimeError("%s: %d effective rows, floor %d — the service shrank; "
                           "re-measure before shipping"
                           % (layer["name"], len(feats), layer["min_rows"]))
    feats = keyed(feats, layer["name"])
    keys = {f["properties"]["KEY"] for f in feats}
    if len(keys) < layer["min_agencies"]:
        raise RuntimeError("%s: %d agencies, floor %d"
                           % (layer["name"], len(keys), layer["min_agencies"]))
    print("%s: %d effective rows (%d expired dropped, %d future-dated kept) "
          "-> %d agency keys (%d rows total)"
          % (layer["name"], len(feats), dropped, future, len(keys), total),
          file=sys.stderr)
    if check_only:
        return feats, None, total

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, layer["name"] + "-src.geojson")
        with open(src_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": feats}, f)
        def _mapshaper(extra, out):
            subprocess.run(
                # -dissolve, NEVER -dissolve2: dissolve2 flattens the layer into
                # a shared-topology mosaic and assigns each face to ONE group,
                # which silently deletes the real concurrent-jurisdiction
                # overlaps the law layer carries (a sheriff and a municipal PD
                # both filed over ~0.5% of points) — measured as a 98.750%
                # name-set agreement before the swap, 100.000% after it. BOTH
                # calls below keep it, so the full-precision comparand and the
                # shipped output differ in the simplification and nothing else.
                ["npx", "-y", MAPSHAPER, src_path,
                 "-dissolve", "KEY", "copy-fields=NAME"] + extra
                + ["-o", "precision=" + PRECISION, "format=geojson", out],
                check=True, cwd=REPO_ROOT)
            with open(out) as f:
                return json.load(f)

        source = _mapshaper([], os.path.join(tmp, layer["name"] + "-full.geojson"))
        dissolved = _mapshaper(["-simplify"] + SIMPLIFY[layer["name"]],
                               os.path.join(tmp, layer["name"] + ".geojson"))

    out_feats = dissolved["features"]
    if len(out_feats) != len(keys):
        raise RuntimeError("%s: dissolve produced %d features, expected %d"
                           % (layer["name"], len(out_feats), len(keys)))
    src_feats = source["features"]
    if len(src_feats) != len(keys):
        raise RuntimeError("%s: the full-precision dissolve produced %d features, "
                           "expected %d — the comparand must be the same partition "
                           "as the output or every dropped ring is spurious"
                           % (layer["name"], len(src_feats), len(keys)))

    # BOTH SIDES ARE SORTED BY KEY BEFORE THE RINGS ARE MEASURED, and on these
    # layers that is load-bearing rather than tidiness. `dropped_rings` asks what
    # a READER is told, and the app's `findFeatureContaining` breaks on the first
    # match — so where a sheriff and a municipal PD both filed over one point the
    # answer is whichever comes first in the file. Sorting the shipped output
    # alone would compare the reader's real answer against an arbitrary
    # mapshaper ordering and attribute the difference to the simplification.
    out_feats.sort(key=lambda f: f["properties"]["KEY"])
    src_feats.sort(key=lambda f: f["properties"]["KEY"])

    # CLASSIFY BEFORE THE PROPERTY STRIP BELOW. KEY is the only field that
    # identifies an agency on both sides, and the strip drops it.
    records, dstats = drings.classify({
        layer["name"]: {"source": src_feats, "drawn": out_feats, "key": "KEY"}})
    dok, dmsg = drings.check(records, dstats,
                             ACCEPTED_DROPPED_RINGS[layer["name"]],
                             GAP_CLOSED[layer["name"]])
    print("%s dropped rings: %s" % (layer["name"], dmsg), file=sys.stderr)
    if not dok:
        print("\n--- measured rows for %s in ACCEPTED_DROPPED_RINGS ---"
              % layer["name"], file=sys.stderr)
        print("GAP_CLOSED[%r] = %d" % (layer["name"], dstats[drings.KIND_GAP_CLOSED]),
              file=sys.stderr)
        for r in records:
            if r.get("harm"):
                print("  %s" % json.dumps(
                    {k: r[k] for k in ("m2", "verts", "centre", "interior",
                                       "features", "kind", "answers")
                     if k in r}, sort_keys=True), file=sys.stderr)
                # A FEW-VERTEX RING'S OWN COORDINATES, so a declaration can STATE
                # its shape rather than infer one from an area. Most of these are
                # triangles a fraction of a metre wide between two counties'
                # filings, and "1.33 m2 over 3 vertices" does not tell a reader
                # whether that is a pinprick or a hairline 30 m long.
                if r.get("verts", 99) <= 8 and r.get("ring"):
                    print("      ring %s" % json.dumps(r["ring"]), file=sys.stderr)
        raise RuntimeError("%s: dropped-ring check failed: %s"
                           % (layer["name"], dmsg))

    for f in out_feats:
        f["properties"] = {"NAME": f["properties"]["NAME"]}

    msg = validate(feats, out_feats)
    gate_against_server(layer, out_feats)
    compact = json.dumps({"type": "FeatureCollection", "features": out_feats},
                         separators=(",", ":"), ensure_ascii=False)
    path = os.path.join(APP_DATA_DIR, layer["out"])
    with open(path, "w") as f:
        f.write(compact)
    print("%s: wrote %s — %d agency areas, %d bytes; %s (%s, 6dp)"
          % (layer["name"], layer["out"], len(out_feats), len(compact), msg,
             simplify_label(layer["name"])),
          file=sys.stderr)
    return feats, len(out_feats), total


# WHERE THE STALENESS PIN LIVES, AND WHY IT IS A FILE RATHER THAN A CONSTANT.
# This is an OPERATOR build with no schedule, reading a source the OEC refreshes
# roughly weekly — so its output drifts from the source with nothing measuring
# the drift. `validate_sources.py` already asks each of these four layers for
# `returnCountOnly=true` every month and its own comment calls a count change
# "the operator's rebuild trigger", but the checker READ ONLY REACHABILITY and
# threw the number away, so the trigger was a sentence and never a mechanism —
# exactly the defect that file records for the nearest-3 rows and fixed only
# there. Measured 2026-09-05: the shipped EMS file was one agency behind, and
# the difference was not cosmetic (see the Berlin note in the module docstring).
#
# The pin is a SIDECAR written by this build rather than a constant edited by
# hand, because a hand-edited pin is one an operator can forget while the data
# files move — and a staleness gate comparing against a stale pin is worse than
# no gate. Written by the same run that writes the data, it cannot disagree with
# them. It sits under data/source/, which the Pages deploy excludes, because it
# is build metadata and not something a reader fetches.
BUILT_ROWS_PATH = os.path.join(REPO_ROOT, "data", "source", "ng911",
                               "built-rows.json")


def layer_last_edit(url):
    """The layer's own `editingInfo.dataLastEditDate`, as an ISO date.

    A ROW COUNT CANNOT SEE A REDRAW. That was written into this file as a
    stated blind spot on 2026-09-05 and the very rebuild that stated it hit
    the case: the OEC edited all four layers on 2026-08-31, moving boundaries
    in 397 features (138 fire, 161 law, 19 PSAP, 79 EMS), while three of
    the four row counts did not move at all.
    The service publishes the edit timestamp, so the blind spot was avoidable
    rather than inherent, and the monthly check now reads both.
    """
    import urllib.parse  # noqa: F401  (kept local; _curl takes a full url)
    meta = json.loads(_curl(url + "?f=json"))
    ms = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    if not isinstance(ms, (int, float)):
        return None
    return datetime.datetime.fromtimestamp(
        ms / 1000.0, datetime.timezone.utc).date().isoformat()


def read_built_rows():
    """The pin, or None when this build has never run since the pin existed."""
    try:
        with open(BUILT_ROWS_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def write_built_rows(totals, agencies, last_edits):
    os.makedirs(os.path.dirname(BUILT_ROWS_PATH), exist_ok=True)
    payload = {
        "_comment": ("What the OEC's own service reported at the last operator "
                     "build of build_wi_ng911_service_areas.py: `rows` as its "
                     "returnCountOnly endpoints answered, and `dataLastEdit` as "
                     "its editingInfo.dataLastEditDate. validate_sources.py "
                     "compares BOTH monthly and WARNs when either has moved — a "
                     "REDRAW does not change a row count, which is how the "
                     "2026-08-31 edit moved 397 features silently. Written by "
                     "the build; never edit by hand."),
        "builtOn": datetime.date.today().isoformat(),
        "rows": totals,
        "agencies": agencies,
        "dataLastEdit": last_edits,
    }
    with open(BUILT_ROWS_PATH, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote %s — rows %s" % (os.path.relpath(BUILT_ROWS_PATH, REPO_ROOT),
                                  totals), file=sys.stderr)


def check_built_rows(totals, last_edits=None):
    """--check: is the shipped tree still current with the source?

    This is the local half of the monthly staleness check. It compares what the
    source holds NOW against what it held when these files were built. It cannot
    see a county REDRAWING a boundary without changing its row count — that is a
    real blind spot and is why the OEC row is a WARN a human reads rather than a
    claim of freshness.
    """
    pin = read_built_rows()
    if pin is None:
        raise RuntimeError(
            "no %s — run this builder without --check once to write the pin"
            % os.path.relpath(BUILT_ROWS_PATH, REPO_ROOT))
    behind = {name: (pin["rows"].get(name), total)
              for name, total in sorted(totals.items())
              if pin["rows"].get(name) != total}
    if behind:
        raise RuntimeError(
            "the shipped NG911 files are STALE — the source has moved since they "
            "were built on %s. %s. Re-run this builder without --check, bump "
            "cache_name in wi/metro-worksheet.json (these are cache-first), and "
            "commit the rebuilt files with the refreshed pin."
            % (pin.get("builtOn", "an unrecorded date"),
               "; ".join("%s %s -> %s" % (n, was, now)
                         for n, (was, now) in behind.items())))
    moved = {}
    for name, live in sorted((last_edits or {}).items()):
        was = (pin.get("dataLastEdit") or {}).get(name)
        if live and was and live != was:
            moved[name] = (was, live)
    if moved:
        raise RuntimeError(
            "the shipped NG911 files are STALE — the row counts still match, but "
            "the service EDITED %s since the build on %s (%s). A redraw does not "
            "move a row count, which is exactly the blind spot this second signal "
            "closes. Re-run this builder without --check, bump cache_name, and "
            "commit the rebuilt files."
            % (", ".join(sorted(moved)), pin.get("builtOn", "an unrecorded date"),
               "; ".join("%s %s -> %s" % (n, w, l) for n, (w, l) in moved.items())))
    print("staleness: all 4 layers still carry the row counts AND the edit dates "
          "they were built from on %s"
          % pin.get("builtOn", "an unrecorded date"), file=sys.stderr)


def main():
    check_only = "--check" in sys.argv[1:]
    built = {}
    for layer in LAYERS:
        built[layer["name"]] = build(layer, check_only)
    n_prov = gate_filings({name: t[0] for name, t in built.items()})
    print("gates: filing absences match the pinned UNFILED map across all %d "
          "provisioning authorities (Langlade still absent)" % n_prov,
          file=sys.stderr)
    totals = {name: t[2] for name, t in built.items()}
    last_edits = {layer["name"]: layer_last_edit(layer["url"]) for layer in LAYERS}
    if check_only:
        check_built_rows(totals, last_edits)
    else:
        write_built_rows(totals, {name: t[1] for name, t in built.items()},
                         last_edits)


if __name__ == "__main__":
    main()
