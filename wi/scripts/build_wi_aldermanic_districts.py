#!/usr/bin/env python3
"""
Build data/app/aldermanic-districts.json — every aldermanic (and village
trustee) district Wisconsin's ward fabric can honestly compose, dissolved
from LTSB's statewide municipal ward layer.

WHY A DISSOLVE, AND ON WHICH KEY. No Wisconsin publisher ships a statewide
aldermanic-district layer, but the state's ward layer carries each ward's
district assignment in ALDERID (Wis. Stat. 5.15(4)(br) filings, Jan/Jul).
The dissolve key is **COUSUBFP + ALDERID — never ALDER_FIPS**: ALDER_FIPS is
county-qualified, and 25 coded municipalities cross county lines, so keying
on it would split those cities' districts in two at the county line. An
incorporated place's COUSUBFP is statewide-unique (measured: no name
collision among coded C/V municipalities), which is exactly what lets the
dissolve merge a cross-county city back together.

MEASURED 2026-08-26 (July 2026 filing): 7,161 wards, 2,580 coded; 2,576 of
those in cities and villages (the other 4 are the Town of Mercer, Iron
County — a town elects no alderpersons, so the CTV gate drops them and this
builder prints them); 867 distinct district keys across 165 municipalities.
THE STATE'S OWN PRE-DISSOLVE AGREES: LTSB's BAS_Live_Collection_Alderpersons
layer (the mid-collection working set, currently the JANUARY session) holds
the same 867 C/V keys, key for key, across a different filing edition — a
two-edition witness this builder re-runs on every build. That BAS layer is
not the source (no stated terms, mutates mid-collection); the licensed AGOL
ward layer is.

THE PER-CITY COMPLETENESS GATE — the reason this file is not a one-liner.
Fourteen municipalities mix '00' placeholders with real district ids, and
the mix splits three ways, measured by uncoded-ward count and area share:

  * SIX ARE INCOMPLETE SUBMISSIONS and are EXCLUDED, each on the record in
    EXCLUDED below (uncoded share 9.4%-99.9% of the city's area). Bellevue
    is the INVERSE error and the reason the gate cuts both ways: a village
    with ONE spuriously coded ward (99.9% uncoded) would otherwise ship a
    single sliver posing as a trustee district. There were TEN until
    2026-09-06; see LOCAL_COMPOSITION.
  * FOUR ARE LOCALLY COMPOSED and ship: the county files their wards
    uncoded and the CITY publishes the assignment itself — Appleton from
    its clerk's polling-locations page, Kaukauna from the text layer of the
    city's own district-map PDF, Berlin from its council page's prose, and
    Edgerton derived from the city's own district SERVICE. Each is gated in
    LOCAL_COMPOSITION below.
  * SIX ARE THE SLIVER SHAPE and SHIP WITH A HOLE. Four reached that by the
    automatic rule — exactly one uncoded ward, 0.0%-1.4% of the city's area
    (Delavan, De Pere, Green Bay, Howard) — and two by DECLARATION, their
    compositions naming the wards their own sources leave out (Kaukauna 18;
    Edgerton 8 and 9). Inside a sliver the card honestly answers
    no-district; every one is pinned, and the automatic rule still fails if
    a second uncoded ward appears in a city that did not declare one.

An OPERATOR rebuild after each Jan-15 / Jul-15 filing window, exactly like
the supervisory build this file leans on (fetch/validate/mapshaper are
imported from it). A count change at a window is expected news — read it,
then move the EXPECT constants deliberately.

Usage:
    python3 wi/scripts/build_wi_aldermanic_districts.py
    python3 wi/scripts/build_wi_aldermanic_districts.py --check   # gates only
"""

import json
import os
import random
import re
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from build_wi_supervisory_districts import (  # noqa: E402
    _curl, fetch_layer, _model, _districts_at, LTSB_ORG, MAPSHAPER, STATE_BBOX,
    WARDS)
import dropped_rings as drings  # noqa: E402  (shared reader — do not fork)

# The layer name the dropped-ring records are keyed by. One layer here, but the
# field is plural in `classify` because one ring can be dropped from several.
LAYER_NAME = "aldermanic"

REPO_ROOT = os.path.dirname(SCRIPT_DIR)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
OUT_NAME = "aldermanic-districts.json"

BAS_ALDERS = ("https://mapservices.legis.wisconsin.gov/arcgis/rest/services"
              "/BAS_Collection/BAS_Live_Collection_Alderpersons/FeatureServer/0")

EXPECT_CODED_WARDS = 2580      # all coded wards, towns included
EXPECT_TOWN_CODED = 4          # the Town of Mercer anomaly, Iron County
EXPECT_DISTRICT_KEYS = 867     # distinct COUSUBFP+ALDERID over C/V, AS FILED
EXPECT_MUNICIPALITIES = 165    # C/V municipalities with any coded ward
EXPECT_COMPOSED_WARDS = 78     # uncoded wards the four compositions assign:
                               # Appleton 50, Kaukauna 16, Berlin 6, Edgerton 6
                               # (each city's one county-coded ward is not one)
EXPECT_TOTAL_KEYS = 888        # 867 filed + 21 the state does not file:
                               # Appleton 11, Berlin 5, Kaukauna 3, Edgerton 2

# The NINE measurably incomplete submissions: COUSUBFP -> (name, uncoded
# wards, uncoded share of the municipality's ward area). Computed fresh from
# the fetch every run and gated against this list — a change is a filing
# window doing its job, and the operator moves the entry with eyes open.
# Appleton left this list on 2026-09-05 through LOCAL_COMPOSITION below; its
# county still files every ward uncoded, and the city itself now supplies the
# assignment. THE OTHER NINE ARE MEASURED SHUT ON THAT SAME ROUTE: Appleton is
# the only one of the ten whose polling places are one-per-district (15 wards
# groups, 15 districts). The rest consolidate — Berlin, Brillion, Cuba City,
# Durand and Edgerton vote at a SINGLE place, Bellevue and Kaukauna at two,
# New London and Port Washington at three — so no ward-to-place grouping can
# name a district there, whatever their own pages say.
#
# PORT WASHINGTON WAS RE-CHECKED FOR AN ACCESS PROBLEM ON 2026-09-30 AND DOES
# NOT HAVE ONE. It was named to this project as a host shut out only by a 403
# on robots.txt, the class #1271 reopened; read with the client that crawls,
# www.portwashingtonwi.gov SERVES robots.txt (6,641 bytes) with no rule
# matching any path we would ask for, and its front page answers 200 at 89,973
# bytes. So the city is readable and always may have been. THAT CHANGES
# NOTHING HERE, which is the point of recording it: its exclusion is a FILING
# question, not an access one — Ozaukee County files ward 9 with no district
# code and the city votes at three places, so no page of the city's own could
# supply the assignment either. The ask to the county clerk stands
# (docs/ASK_DRAFTS.md). Recorded so the next pass does not re-probe a host
# that answers, or expect a reopened door to close this gap.
EXCLUDED = {
    "06350": ("Bellevue", 11, 0.999),
    "09725": ("Brillion", 2, 0.094),
    "17950": ("Cuba City", 1, 0.158),
    "21225": ("Durand", 1, 0.274),
    "56925": ("New London", 3, 0.429),
    "64450": ("Port Washington", 1, 0.318),
}
# The sliver-hole cities: ship, with a hole answering "no district".
# The first four reached this list by the automatic rule in classify() —
# exactly one uncoded ward, under 5% of the city. Kaukauna and Edgerton reach
# it a different way: their compositions NAME the wards their own sources leave
# out, so the leftovers are declared rather than discovered.
SLIVER_OK = {"19450": "Delavan", "19775": "De Pere",
             "31000": "Green Bay", "35950": "Howard",
             "22575": "Edgerton", "38800": "Kaukauna"}

# ---------------------------------------------------------------------------
# LOCAL COMPOSITION — a municipality whose COUNTY files its wards uncoded and
# whose OWN election authority publishes which district each ward votes in.
#
# APPLETON, ADDED 2026-09-05, is the first and (measured) the only one of the
# ten excluded municipalities this route reaches. Outagamie County submits all
# 50 of its Appleton wards uncoded and has done through four filings; only the
# Calumet and Winnebago fringes carry ids. The city's own ArcGIS org was
# enumerated in full — 72 services, no aldermanic layer — which confirms the
# 2026-08-26 record by a second route and is why nothing here reads a city
# boundary file: there is not one.
#
# WHAT THERE IS is the CITY CLERK's own polling-locations page, which prints
# "District N: <polling place>" and under it the wards that vote there. That is
# the election authority stating the composition, and it is corroborated by TWO
# OTHER PUBLISHERS plus a second edition of the clerk's own assignment.
#
# THE COUNT WAS WRITTEN AS FOUR UNTIL 2026-09-05 AND THAT WAS ONE TOO MANY.
# Items 1 and 2 below are the SAME FACT through a second channel: the Elections
# Commission publishes what each municipality reports, so its ward-to-place file
# IS the Appleton clerk's assignment, machine-readable and already in this repo.
# That makes it the best gate here and NOT an independent voice, and the
# difference matters — three sources agreeing is a weaker claim than four, and
# the record should say the weaker true one.
#
#   1. THE STATE'S POLLING FILE, already shipped in this repo
#      (wi/data/app/{outagamie,calumet,winnebago}-polling-places.json, from the
#      Elections Commission). Appleton's 60 wards group into exactly 15 polling
#      places, one per district, and that grouping reproduces the clerk page's
#      15 ward lists EXACTLY on the 57 wards the page names. This is the gate
#      below: it needs no network and fails if either side moves. SAME SOURCE
#      as the page, second channel — a cross-CHANNEL check, which still catches
#      a mis-transcription, a stale page and a re-warding, and does not catch
#      the clerk being wrong.
#   2. IT ALSO PLACES THE THREE THE PAGE OMITS, which is why it earns its place
#      even without being independent. Wards 51, 59 and 60 are recent annexation
#      slivers (0.025%, 0.714% and 0.012% of the city's area) that the clerk's
#      page does not list; the state's file puts 51 at St Matthew (District 10),
#      59 at Celebration Ministry (District 13) and 60 at First English Lutheran
#      (District 7). They are marked FROM_POLLING_FILE below.
#   3. LTSB'S OWN TEN CODED WARDS — the COUNTIES' filing, a different publisher
#      entirely — agree with the page on all ten (13/14/15→05, 25→08, 33/34→11,
#      44/45/46/47→15). Gated below. This is the one that would catch the clerk
#      being wrong, and it covers ten wards of sixty.
#   4. CENSUS 2020 POPULATION BALANCES: 75,862 across the fifteen, ideal 5,057,
#      worst deviation 6.3% (D4 -6.3%, D12 +3.2%). A plan drawn to a census
#      balances on that census — the Vermilion measurement, applied to a city.
#      Independent of every publisher above, and the check that would catch a
#      composition that was internally consistent and simply not the plan.
#
# A FIFTH SOURCE DISAGREES ON EXACTLY TWO WARDS AND IS RECORDED RATHER THAN
# USED. The city's own parcel service (My_Property_Data_Publish_V2, the data
# behind its "Find your Alderperson" app) carries Aldermanic_Ward and
# Aldermanic_District per parcel. Tallied inside each LTSB ward polygon, 33,570
# parcels agree with the composition on 55 of the 57 wards it covers — and put
# ward 25 in District 11 and ward 33 in District 8, the transpose of what the
# clerk's page and LTSB both say. The parcel field is measurably the PREVIOUS
# ward plan: it knows nothing of wards 48-59, which the other three sources all
# carry, and 1,741 of 20,000 parcels sit in an LTSB ward whose number it does
# not use. So this is a stale layer, not a live disagreement — but it is written
# down, because "two publishers disagree" is never resolved by preference here.
LOCAL_COMPOSITION = {
    "02375": {
        "name": "Appleton",
        "seats": 15,
        # appletonwi.gov/government/departments/clerk/elections/polling_locations.php
        # read 2026-09-05. FOUR OF THE FIFTEEN HEADINGS USE A NON-BREAKING SPACE
        # ("District\xa010:"), which a plain `District (\d+):` read drops in
        # silence — it returns eleven districts and forty-two wards and looks
        # like an incomplete page rather than a parser bug.
        "source_url": ("https://www.appletonwi.gov/government/departments/clerk"
                       "/elections/polling_locations.php"),
        "read_on": "2026-09-05",
        "districts": {
            "01": [1, 2],
            "02": [3, 4, 5, 6, 48],
            "03": [7, 8, 9],
            "04": [10, 11, 12, 52],
            "05": [13, 14, 15, 16],
            "06": [17, 18, 19, 49, 50],
            "07": [20, 21, 22, 54, 60],       # 60 from the state's polling file
            "08": [23, 24, 25, 55],
            "09": [26, 27, 56],
            "10": [28, 29, 30, 51],           # 51 from the state's polling file
            "11": [31, 32, 33, 34, 57],
            "12": [35, 36, 37],
            "13": [38, 39, 40, 41, 53, 58, 59],  # 59 from the state's polling file
            "14": [42, 43],
            "15": [44, 45, 46, 47],
        },
        # the three the clerk's page does not name; the state's file places them
        "from_polling_file": {51: "10", 59: "13", 60: "07"},
        # ward -> polling place, as the shipped WEC files carry it. The gate
        # asserts the composition above partitions the wards exactly the way
        # these places do — a district is one polling place in Appleton and the
        # clerk's page says which, so the two must agree ward for ward.
        "polling_counties": ("outagamie", "calumet", "winnebago"),
        "polling_key": "C|APPLETON|",
        # Measured on the SAME column as the three below, so all four are one
        # source rather than a census figure for one city and a state column for
        # the others: 75,913 over fifteen, ideal 5,061, worst D4 -6.40%. The
        # header above records 75,862 / 5,057 / 6.3% from Census 2020 itself;
        # the small difference is ward 60, which the 2025 edition does not carry.
        "balance": 6.40,
    },
    "06925": {
        "name": "Berlin",
        "seats": 6,
        # cityofberlin.net/city-council/ read 2026-09-06. THE PAGE STATES THE
        # COMPOSITION IN PROSE RATHER THAN IN A TABLE: "The common council is
        # comprised of six members who are elected, by Ward", and then names
        # each member's ward — "Council Member Terry Przybyl, Alderperson Ward 1
        # and Ward 7", "…Ward 2", and so on. Berlin is the ONE of these three
        # whose source names every ward it has: 7 wards, 6 districts, nothing
        # left over.
        #
        # THE RECORD SAID THIS CITY WAS SHUT AND IT WAS SHUT ON A DIFFERENT
        # QUESTION. What was measured on 2026-09-05 is that Berlin votes at a
        # SINGLE polling place, so no ward-to-place grouping can name a district
        # there — true, and about the polling route only. The gap's own `wanted`
        # asked for three things and "a city page naming the wards in each
        # district" was the third; nobody had read the page.
        "source_url": "https://cityofberlin.net/city-council/",
        "read_on": "2026-09-06",
        "districts": {
            "01": [1, 7],
            "02": [2],
            "03": [3],
            "04": [4],
            "05": [5],
            "06": [6],
        },
        # LTSB codes exactly one Berlin ward — 7 -> 01, filed by WAUSHARA while
        # Green Lake files the other six uncoded — and 7 is precisely the ward
        # the page pairs with ward 1 under one alderperson. The counties' filing
        # and the city's page agree on the single ward both describe.
        #
        # BERLIN CARRIES ONE INFERENCE THE OTHER THREE DO NOT, AND IT IS NAMED
        # HERE RATHER THAN LEFT IMPLICIT IN THE TABLE ABOVE. The page gives the
        # GROUPING and never a district NUMBER — it names wards, not districts —
        # so `district N = ward N` for the five single-ward seats is this
        # project's reading, not the city's statement. One label is anchored:
        # Waushara's 7 -> 01 fixes the {1,7} seat as district 01. The other five
        # are the inference, and NO GATE HERE CAN CATCH IT: each of those
        # districts is a single ward, so any permutation among them leaves the
        # balance below identical. It is the only reading the page admits.
        # Compare WAUPACA, which stays out of this table for the same class of
        # problem — its page numbers 1-5 where LTSB keys 41-45, with nothing
        # witnessing the correspondence. Berlin has an anchor that agrees;
        # Waupaca has a visible mismatch.
        "balance": 12.55,
    },
    "22575": {
        "name": "Edgerton",
        "seats": 3,
        # THE ONLY ONE OF THE THREE WHOSE SOURCE IS A SERVICE RATHER THAN A
        # DOCUMENT. The city publishes `Voting_Districts` (3 polygons, named
        # "District 1".."District 3") and `Wards` from its own ArcGIS Online org
        # — found by an unauthenticated catalogue search that needed nothing
        # from the city's website, the Vermilion move. So this composition is
        # not transcribed from prose: it is DERIVED by overlaying LTSB's ward
        # polygons on the city's own district polygons, and re-derived by
        # service_witness below on every run.
        "source_url": ("https://services7.arcgis.com/Sngx5exQaxXjq6qG/arcgis/rest"
                       "/services/Voting_Districts/FeatureServer/0"),
        "read_on": "2026-09-06",
        "districts": {
            "01": [1, 2],
            "02": [3, 4],
            "03": [5, 6, 7],
        },
        # Wards 8 and 9 are annexation slivers the city's district layer does
        # not cover at all (0.68% and 0.36% of their own area lands in any
        # district — digitisation contact, not membership). See `unplaced`.
        "unplaced": {8: 0.0009, 9: 0.0061},
        "service_witness": {
            "url": ("https://services7.arcgis.com/Sngx5exQaxXjq6qG/arcgis/rest"
                    "/services/Voting_Districts/FeatureServer/0"),
            "field": "Voting_District",
            # "District 3" -> "03"
            "label_re": r"^District\s+(\d+)$",
            "min_share": 0.99,
        },
        # LTSB codes exactly one Edgerton ward — 7 -> 03, filed by DANE while
        # Rock files the other eight uncoded — and the city's own layer puts
        # ward 7 in "District 3" at 99.76% of its area. Two publishers, one
        # ward, agreeing.
        "balance": 2.35,
    },
    "38800": {
        "name": "Kaukauna",
        "seats": 4,
        # kaukauna.gov/common-council/ links "Map of Aldermanic Districts",
        # 2025-DISTRICT-MAP-11-24-25.pdf, read 2026-09-06. IT IS A VECTOR PDF
        # AND THE COMPOSITION IS IN ITS TEXT LAYER, so nothing here reads a map:
        #
        #     DIST. #1 - WARDS 1,2,3
        #     DIST. #2 - WARDS 4,5,16
        #     DIST. #3 - WARDS 6,7
        #     DIST. #4 - WARDS 8,9,10,11,12,13,14,15,17
        #
        # The Jackson rule says read a district map's filled path OBJECTS rather
        # than its pixels; the rule before that one is to check whether the map
        # simply SAYS it, which this one does. The page also prints the polling
        # arrangement that closed the Appleton route here — districts 1 & 2 vote
        # at one building, 3 & 4 at another — so the same document that cannot
        # answer through polling places answers directly.
        "source_url": ("https://kaukauna.gov/wp-content/uploads/2025/12"
                       "/2025-DISTRICT-MAP-11-24-25.pdf"),
        "read_on": "2026-09-06",
        "districts": {
            "01": [1, 2, 3],
            "02": [4, 5, 16],
            "03": [6, 7],
            "04": [8, 9, 10, 11, 12, 13, 14, 15, 17],
        },
        # Ward 18 is a 0.29% annexation sliver the map does not name; it is also
        # absent from LTSB's own 2025-ward population edition, i.e. newer than
        # both. It is NOT placed by inference from its neighbours.
        "unplaced": {18: 0.0029},
        # LTSB codes exactly one Kaukauna ward — 12 -> 04, filed by CALUMET
        # while Outagamie files all seventeen of its own uncoded (the Appleton
        # county, again) — and the map puts ward 12 in DIST. #4.
        "balance": 6.38,
    },
}

# 9% (the supervisory build's retain) measured 99.675% agreement here — city
# districts are small, so the same retain cuts proportionally deeper.
#
# THE SETTING WAS visvalingam 25% UNTIL 2026-09-27 (LATER THE SAME DAY), AND A
# THIRD INSTRUMENT RETIRED IT. The block that used to stand here chose between
# settings on two instruments — RING-HARM, a dropped ring that changes what a
# reader is told, and POINTS, `validate()`'s 4,000-point sample of boundary
# DISPLACEMENT — and broke a tie on gzipped file size. Both readings were
# honest and neither could see what the third one measures: how far the RETAINED
# boundary moved. `dropped_rings.check_fidelity` measures that, and at this
# layer's own ceiling (below) it FAILS visvalingam 25% on FORTY-NINE vertices,
# worst 54.2 m, every one of them at a point where the answer changes. The
# worst is City of Wisconsin Dells district 2, where a reader on ground the true
# line puts inside the district is told no district at all. It passes only at
# 86.89 m, ten times the median source step, which gates nothing — the same
# shape the NG911 layers measured at 126 m.
#
# RE-MEASURED 2026-09-27 ON THE JULY 2026 FILING, 866 districts, both settings
# run against the same fetch and the same dissolve, with the EXACT retained test
# (#1224) rather than the superseded one the old table was measured with:
#
#   setting            rings  dropped  gap-closed  RING-HARM  POINTS  fidelity @ 9.56 m
#   visvalingam 25%              88          84          2    0/4000  FAILS (49 vertices, worst 54.2 m)
#   dp interval=1                88          84          2    0/4000  PASSES, nothing excluded
#
# THE TWO ANSWER INSTRUMENTS NO LONGER DISTINGUISH THEM AT ALL. Both settings
# drop the SAME 88 rings — the same 84 that close a coverage gap and the same
# two declared harms, Wausau 11 and New Richmond 2 — and both agree with the
# ward fabric at 4000 of 4000 sample points. The old table read 70 dropped
# against 68 with one harm each, and those columns were floors: the instrument
# then in use asked whether ANY of a source ring's vertices survived, so a ring
# joined to the main body at one shared vertex read as retained after vanishing
# whole. So the tie is exact and the fidelity gate is the only instrument that
# separates them.
#
# THE SIZE OBJECTION THAT CHOSE visvalingam WAS APPLIED TO A QUANTITY NOBODY
# DOWNLOADS. This layer is drawn and answered from `aldermanic-district.pmtiles`
# (registered with `tiles:` in wi/index.html), and the whole file is fetched only
# to pin a comparison. Measured on the two COMMITTED states, so anyone can
# reproduce it from git: the gzipped JSON grows 48,156 bytes (604,265 ->
# 652,421 at `gzip -9`, +7.97%) and THE ARCHIVE GROWS 7,923 BYTES (1,190,687 ->
# 1,198,610, +0.67%). The column the tiebreak used moves six times as many bytes
# and twelve times the proportion, which is the same finding the NG911 quartet
# recorded hours earlier (its JSON grew 97.3% and its archives 15.9%). A SIZE
# OBJECTION IS MEASURED ON WHAT A READER FETCHES.
#
# THE ARCHIVE BYTES ARE GOOD TO ABOUT A HUNDRED, NOT TO THE BYTE: tippecanoe's
# output is not byte-identical run to run, measured here at 10 and 58 bytes apart
# rebuilding the same input twice. That is why `--committed` decodes the archive
# and compares ANSWERS rather than hashing it, and why no byte count above is
# quoted as an identity.
#
# WHY THE ALGORITHM AND NOT THE DIAL, for the third time in this fleet:
# Visvalingam thresholds triangle AREA, which does not bound how far the drawn
# line strays, because successive below-threshold removals compound — a staircase
# along a street grid becomes a chord across it. Douglas-Peucker thresholds
# perpendicular DEVIATION, so the stray is bounded by the interval itself
# (approximately: mapshaper applies it through a spherical approximation, and the
# NG911 psap layer measured 1.2x its interval). `scripts/build_legislative_
# boundaries.py` reached this on Illinois's chambers and the NG911 quartet
# reached it on county 911 filings; this is a third layer family.
#
# dp interval=5 and 15 were measured in the old table and are not re-run: 5 cost
# four of the 4,000 sample points where every setting above costs none, and 15
# did not clear the builder's own >=99.9% point-agreement gate at all (99.650%),
# so neither was ever eligible however small its file.
#
# GZIPPED IS THE COLUMN FOR THE JSON, NOT RAW — `scripts/build_legislative_
# boundaries.py` records raw and gzipped disagreeing in SIGN on its own files —
# but the ARCHIVE is the column that decides.
SIMPLIFY = ["-simplify", "dp", "keep-shapes", "interval=1"]
SIMPLIFY_LABEL = "dp interval=1"

# Rings the simplifier drops that CLOSE A GAP — ground no district covered before
# or after — measured at the shipped setting rather than assumed. Held so the
# number cannot drift silently; a change means the filing moved and wants reading.
GAP_CLOSED = 84

# HOW FAR THE RETAINED BOUNDARY MAY MOVE at a point where a reader's ANSWER
# changes, in metres. Derived from THIS layer's own geometry and never borrowed:
# 1.10x the median length of its source line's own segments (8.689 m over 370,170
# retained-ring segments on the July 2026 filing), which is the ratio
# `scripts/build_legislative_boundaries.py` uses for Illinois's chambers. THE
# RULE THAT TRANSFERS BETWEEN LAYER FAMILIES IS THAT THE CEILING COMES OFF THE
# LAYER'S OWN STEP — never the ratio and never the metres. Illinois's 25 m came
# off a 17.9 m street grid and the NG911 quartet's 2.70-3.77 m off county 911
# filing seams drawn five times finer than this ward fabric.
#
# PINNED RATHER THAN DERIVED AT BUILD TIME, which is the whole point of writing
# it down: a ceiling recomputed from the source on every run rises whenever the
# source gets coarser, so it can never fail. The builder PRINTS the measured step
# beside it, so a step that drifts is visible without the ceiling moving with it.
#
# A METRE-CEILING ALONE WOULD GATE THE WRONG THING, which is measured on the
# sibling NG911 layers rather than argued here: there, seven vertices stray past
# their own ceiling on real geometry that costs no reader anything. So
# `check_fidelity` asks the metres AND the answer, through four measured
# predicates whose counts it prints every run. On this layer at this setting it
# excludes nothing at all — every retained vertex is inside the ceiling.
FIDELITY_MAX_M = 9.56

ACCEPTED_DROPPED_RINGS = [
    {
        # CITY OF WAUSAU DISTRICT 11, a 6.35 m2 ring of 4 vertices. Every setting drops
        # it — Douglas-Peucker at 1, which ships, and at 5 and 15 m, and
        # visvalingam at 25%, which shipped until 2026-09-27 — so the alternative
        # is not a finer setting of either simplifier, which is the same
        # conclusion the supervisory layer's Door County ring reached. (This
        # comment said "visvalingam at 25%, which ships" until the fidelity gate
        # retired that setting; the list of settings that drop the ring is
        # unchanged, and so is every measured field below.)
        #
        # IT IS DRY LAND, MEASURED AND NOT INFERRED. TIGER's areal hydrography
        # returns NO water polygon at EITHER the ring's centre or its interior
        # point — both were read, because they are 50.6 m apart and one answer
        # would not have covered the other — with three controls
        # answering first: open Lake Michigan returns "Lk Michigan", Lake
        # Winnebago returns "Lk Winnebago", and a point on land in downtown
        # Wausau returns no water. That order matters — an API error is not an
        # empty answer, and a default read as "no water" is how a failure becomes
        # a confident finding.
        #
        # AND THE CENSUS PUTS IT IN MAINE VILLAGE, NOT IN WAUSAU. Its key is
        # Wausau's (COUSUB 84475) and TIGER's county-subdivision layer answers
        # Maine village (COUSUB 48225), the neighbouring municipality in the same
        # county — so it is a disagreement between LTSB's ward fabric and the
        # census's subdivision fabric over 6 m2, not an island and not water. A
        # subdivision hit names a place and says nothing about the surface, which
        # is why the hydrography above is the finding and this is context.
        #
        # IT IS A HAIRLINE, NOT A PATCH. Its centre and the interior point below
        # are 50.6 m apart, so 6.35 m2 is spread along something around a hundred
        # metres long — the shape a boundary disagreement makes, not a parcel. The
        # WIDTH is deliberately not stated: it follows only if the interior point
        # sits at one end, and nothing measured says it does.
        #
        # A READER STANDING THERE IS TOLD WAUSAU 11 TODAY AND WOULD BE TOLD
        # NOTHING. That is the false-silence harm rather than a wrong name, and it
        # is stated rather than called negligible: it is ground a person can be on.
        #
        # EVERY FIGURE HERE CAME OFF THE GATE, AND THE FIRST DRAFT OF THIS ENTRY
        # GOT TWO OF THEM WRONG — and a THIRD copy of the first of them survived
        # into review, inside `why` below, where the manager session caught it.
        # `check()` validates `kind`, `features`, the two answers, `interior` and
        # `m2`/`lat`/`lng`, and never reads `why` or `date`: so the gate corrected
        # every copy it can see and left the one it cannot, in this same
        # dictionary. `why` is the first field a maintainer reads to decide
        # whether an entry still holds, and it is the field that carried "open
        # Lake Michigan" through five copies elsewhere in this repo.
        #
        # THE 6.06 IN THE NEXT SENTENCE IS DELIBERATE — it names the first draft's
        # error and must stay. It said 6.06 m2, read off a `%f`-rounded
        # `0.000006 km2` rather than the measurement, and it put the INTERIOR
        # point in `lat`/`lng`, where the matcher wants the RING's centre — 50.6 m
        # away, so it matched no dropped ring and the check refused the build and
        # printed the correct row. A declaration derived from a rounded display is
        # the same defect as a correction derived by arithmetic.
        "lat": 44.973516, "lng": -89.674842, "verts": 4, "m2": 6.35,
        # Inside the ring at 6 decimals, from the gate rather than worked out by
        # eye, and the point both hydrography reads were taken at.
        "interior": {"lat": 44.973509, "lng": -89.675484, "decimals": 6},
        "features": ["aldermanic:84475-11"],
        "kind": "false-silence",
        "answer_before": {"aldermanic": ["84475-11"]},
        "answer_after": {"aldermanic": []},
        "why": "no tested setting retains it — visvalingam 25% and dp at 1, 5 and "
               "15 m all drop it; 6.35 m2 of DRY LAND measured against TIGER's "
               "areal hydrography rather than guessed from the coordinates, which "
               "the census places in Maine village though its key is Wausau's, "
               "and the answer it costs is recorded above rather than called harmless",
        "date": "2026-09-27",
    },
    {
        # NEW RICHMOND CITY WARD 2, a 1.24 m2 sliver, and THE SECOND ENTRY IN THIS
        # TABLE WITH THE SAME SHAPE AS THE FIRST: its key is a city's and the
        # census puts the ground outside that city. Measured 2026-09-27 with a
        # control (a point in the middle of New Richmond returns the city), no
        # incorporated place contains this point at all, and TIGER's county
        # subdivision layer puts it in STAR PRAIRIE TOWN. That is exactly why its
        # loss is a SILENCE rather than a wrong name: the ring is the part of the
        # city's ward that lies outside the city's own census boundary, so when it
        # goes, no aldermanic district covers the spot and no neighbour steps in.
        #
        # THE SAME GROUND IS DECLARED IN THE SUPERVISORY BUILDER, as a WRONG NAME
        # rather than a silence. Both layers dissolve the state's ward fabric, so
        # a sliver in that fabric is inherited by both; the supervisory layer
        # tiles the whole state, so a reader there gets St. Croix district 11
        # instead of 12, while here they get nothing. One sliver, two harms,
        # because the two layers cover different ground.
        #
        # FOUND ONLY BECAUSE THE RETAINED TEST BECAME EXACT. The old test asked
        # whether ANY of a source ring's vertices survived anywhere in its
        # district's drawn geometry, so a ring joined to the main body at one
        # shared vertex read as retained after vanishing whole. This layer's
        # gap-closed count moved 67 -> 84 in the same change, which is the same
        # blindness counted on the harmless side.
        #
        # DRY LAND, by TIGER's areal hydrography with four controls answering
        # first (Marathon dry; Lake Michigan, Lake Winnebago and Lake Mendota
        # water).
        "lat": 45.126489, "lng": -92.569594, "verts": 5, "m2": 1.24,
        "interior": {"lat": 45.126485, "lng": -92.569614, "decimals": 6},
        "features": ["aldermanic:57100-02"],
        "kind": "false-silence",
        "answer_before": {"aldermanic": ["57100-02"]},
        "answer_after": {"aldermanic": []},
        "why": "1.24 m2 of dry land in Star Prairie town measured against "
               "TIGER's areal hydrography, carrying New Richmond city's own ward "
               "key although no incorporated place contains it, which is why "
               "losing it leaves the spot with no district rather than a "
               "neighbour's; the supervisory layer declares the same sliver "
               "because both dissolve the state's ward fabric",
        "date": "2026-09-27",
    },
]
PRECISION = "0.000001"
UNCODED = ("", "00", "0000")


def is_coded(alderid):
    return (alderid or "").strip() not in UNCODED


def apply_local_composition(attr_feats):
    """Give each locally-composed municipality's wards the district its own
    source publishes, and GATE that assignment before a single polygon is drawn.

    THE GATES ARE PER CITY BECAUSE THE SOURCES ARE. Appleton's composition comes
    from a clerk's polling-locations page and is checked against the Elections
    Commission's own ward-to-place file; Berlin's comes from a council page in
    prose, Kaukauna's from the text layer of the city's own district map, and
    Edgerton's from the city's own district SERVICE. A polling-place partition
    is a real witness for exactly one of those four — the other three vote at
    one or two places for all their districts, which is what closed that route
    on 2026-09-05 — so demanding it of all four would refuse three correct
    compositions, and skipping it for all four would drop Appleton's best check.

    What every city is held to:
      * every ward placed, or named in `unplaced` with its area share pinned
        and RE-MEASURED here (below),
      * agreement with every ward the counties DO code (`is_coded`), which is a
        different publisher and the check that catches the city being wrong,
      * a population balance on LTSB's own 2024-election/2025-ward layer, held
        to the pinned figure in BOTH directions.
    plus, where the city's source supports it, the polling partition (Appleton)
    or a live re-derivation from the city's service (Edgerton).

    Returns (n_wards_composed, {cousubfp: n_districts}).
    """
    by_mun = {}
    for f in attr_feats:
        p = f["properties"]
        if p.get("COUSUBFP") in LOCAL_COMPOSITION and p.get("CTV") in ("C", "V"):
            by_mun.setdefault(p["COUSUBFP"], []).append(f)
    if set(by_mun) != set(LOCAL_COMPOSITION):
        raise RuntimeError("LOCAL_COMPOSITION names %s; the ward layer carries %s"
                           % (sorted(LOCAL_COMPOSITION), sorted(by_mun)))
    composed, shipped = 0, {}
    for cousub, spec in sorted(LOCAL_COMPOSITION.items()):
        feats = by_mun[cousub]
        ward_to_dist = {}
        for dist, wards in spec["districts"].items():
            for w in wards:
                if w in ward_to_dist:
                    raise RuntimeError("%s: ward %d is in two districts (%s, %s)"
                                       % (spec["name"], w, ward_to_dist[w], dist))
                ward_to_dist[w] = dist
        if len(spec["districts"]) != spec["seats"]:
            raise RuntimeError("%s: %d districts composed for a %d-seat council"
                               % (spec["name"], len(spec["districts"]), spec["seats"]))

        # 1. EVERY ward, or none. A partial composition would ship some of a
        #    city's districts as if they were all of them, which is the exact
        #    failure the per-city completeness gate exists to prevent.
        have = set()
        for f in feats:
            try:
                have.add(int(f["properties"]["WARDID"]))
            except (TypeError, ValueError):
                raise RuntimeError("%s: a ward with no numeric WARDID (%r)"
                                   % (spec["name"], f["properties"].get("WARDID")))
        unplaced = spec.get("unplaced") or {}
        missing = sorted(have - set(ward_to_dist) - set(unplaced))
        extra = sorted(set(ward_to_dist) - have)
        if missing or extra:
            raise RuntimeError(
                "%s: the composition and the ward layer disagree about which wards "
                "exist — %d in the layer and neither composed nor declared unplaced "
                "(%s), %d composed and not in the layer (%s). A re-warding has "
                "happened; re-read the source."
                % (spec["name"], len(missing), missing[:8], len(extra), extra[:8]))

        # 1b. A DECLARED-UNPLACED WARD IS A MEASUREMENT, NOT A PERMISSION. Each
        #     one is a recent annexation the city's own source does not name, and
        #     it ships answering "no district" rather than being inferred from a
        #     neighbour. Its share of the municipality's ward area is pinned in
        #     the spec and re-measured here, so a sliver that grows into real
        #     territory stops the build instead of quietly staying a hole. This
        #     needs Shape__Area, which the attribute pass fetches and the
        #     geometry pass now fetches too — both passes check.
        if unplaced:
            gone = sorted(set(unplaced) - have)
            if gone:
                raise RuntimeError("%s: ward(s) %s are declared unplaced and are no "
                                   "longer in the ward layer — re-read the source"
                                   % (spec["name"], gone))
            areas = {}
            for f in feats:
                a = f["properties"].get("Shape__Area")
                if a is None:
                    areas = None
                    break
                areas[int(f["properties"]["WARDID"])] = a
            if areas:
                total = sum(areas.values())
                for w, pinned in sorted(unplaced.items()):
                    share = areas[w] / total
                    if abs(share - pinned) > 0.002:
                        raise RuntimeError(
                            "%s: unplaced ward %d is %.4f%% of the municipality's "
                            "ward area, pinned at %.4f%%. It has moved; re-measure "
                            "and decide again whether it can ship unplaced."
                            % (spec["name"], w, 100 * share, 100 * pinned))

        # 2. IT MUST AGREE WITH EVERY WARD THE STATE DOES CODE. The county files
        #    a handful of these wards with real ids; those are an independent
        #    edition of the same fact and a disagreement means one of the two is
        #    describing a different plan.
        #
        #    FOR THREE OF THE FOUR CITIES THIS IS ONE WARD, AND ONE WARD IS A
        #    KEYING CHECK RATHER THAN A COMPOSITION CHECK. It proves the city's
        #    district NUMBERING is the numbering LTSB keys the geometry by —
        #    ruling out an off-by-one or a relabelled plan — and says nothing
        #    about where the city's other wards sit. Appleton is the exception
        #    at ten of sixty; Edgerton is covered a different way, by
        #    _service_witness re-deriving every ward from the city's polygons.
        #    Kaukauna and Berlin rest on ONE PUBLISHER plus the balance figure.
        for f in feats:
            p = f["properties"]
            if not is_coded(p.get("ALDERID")):
                continue
            w = int(p["WARDID"])
            if ward_to_dist[w] != p["ALDERID"].strip():
                raise RuntimeError(
                    "%s: ward %d — the state files district %s, the city's own "
                    "source composes it into %s. Two publishers disagree; this "
                    "build does not prefer one."
                    % (spec["name"], w, p["ALDERID"].strip(), ward_to_dist[w]))

        # 3. THE STATE'S POLLING FILE MUST PARTITION THE WARDS THE SAME WAY —
        #    FOR THE ONE CITY WHERE THAT IS A QUESTION WITH AN ANSWER. Appleton
        #    votes one place per district and its clerk's page says which, so
        #    the grouping the Elections Commission publishes has to be the
        #    composition, group for group. This reads files already in this repo
        #    — no network, and it fires on every build.
        #
        #    IT IS SKIPPED, NOT WEAKENED, WHERE IT CANNOT APPLY: Berlin votes at
        #    a single place for all six districts, Edgerton at one for three,
        #    Kaukauna at two for four. A city that consolidates polling places
        #    makes this witness say nothing, and running it anyway would either
        #    fail three correct compositions or be quietly satisfied by a
        #    partition of one group. Their fourth witness is `balance` below;
        #    Edgerton also re-derives its whole composition from the city's own
        #    service in service_witness().
        if spec.get("polling_key"):
            _polling_witness(spec, feats, have, ward_to_dist)

        # 4. POPULATION BALANCE, on LTSB's own 2024-election/2025-ward layer.
        #    A plan drawn to a census balances on that census; a composition
        #    that is internally consistent and simply not the plan does not.
        #    Gated in BOTH directions — a figure that improves is a different
        #    plan just as surely as one that worsens, and must be re-read rather
        #    than absorbed.
        _balance_witness(cousub, spec, ward_to_dist)

        # 5. Where the source is a service, re-derive the whole composition from
        #    it rather than trusting the transcription (Edgerton only).
        if spec.get("service_witness"):
            _service_witness(spec, feats, ward_to_dist)

        for f in feats:
            p = f["properties"]
            w = int(p["WARDID"])
            if w not in ward_to_dist:
                continue          # declared unplaced: it stays uncoded
            if not is_coded(p.get("ALDERID")):
                composed += 1
            p["ALDERID"] = ward_to_dist[w]
        shipped[cousub] = len(spec["districts"])
    return composed, shipped


def _polling_witness(spec, feats, have, ward_to_dist):
    """The Elections Commission's ward-to-place file must partition the wards
    exactly the way the composition does. Appleton only — see gate 3."""
    if True:
        places = {}
        for county in spec["polling_counties"]:
            path = os.path.join(APP_DATA_DIR, "%s-polling-places.json" % county)
            if not os.path.exists(path):
                raise RuntimeError("%s: %s is not in the tree, so the polling-place "
                                   "witness cannot run" % (spec["name"], path))
            with open(path) as fh:
                for key, val in json.load(fh).items():
                    if not key.startswith(spec["polling_key"]):
                        continue
                    if not isinstance(val, dict) or "name" not in val:
                        continue
                    places[int(key.split("|")[2])] = val["name"]
        if set(places) != have:
            raise RuntimeError(
                "%s: the polling file names %d wards and the ward layer %d "
                "(only-in-polling %s, only-in-layer %s)"
                % (spec["name"], len(places), len(have),
                   sorted(set(places) - have)[:6], sorted(have - set(places))[:6]))
        by_place, by_dist = {}, {}
        for w, place in places.items():
            by_place.setdefault(place, set()).add(w)
            by_dist.setdefault(ward_to_dist[w], set()).add(w)
        if sorted(by_place.values(), key=sorted) != sorted(by_dist.values(), key=sorted):
            raise RuntimeError(
                "%s: the state's %d polling places do not partition the wards the "
                "way the %d composed districts do — places %s vs districts %s"
                % (spec["name"], len(by_place), len(by_dist),
                   sorted(map(sorted, by_place.values())),
                   sorted(map(sorted, by_dist.values()))))


POP_WARDS = (LTSB_ORG + "/2024_Election_Data_with_2025_Wards/FeatureServer/0")
BALANCE_TOL = 0.25      # percentage points


def _balance_witness(cousub, spec, ward_to_dist):
    """Worst population deviation across the composed districts, held to the
    figure pinned in the spec.

    THE POPULATION COLUMN IS LTSB'S OWN, on a DIFFERENT service from the ward
    geometry — the same publisher, so this is a cross-service check rather than
    an independent voice, and it is worth running for what it does catch: a
    composition that groups the right wards into the wrong districts balances
    differently, and a re-warding moves it immediately.

    IT IS DRIFT DETECTION AND NOT A CEILING. It pins each city's MEASURED
    figure and fails at +/-BALANCE_TOL in EITHER direction, so a re-warding or a
    mis-transcription stops the build; it enforces no maximum deviation at all,
    and it is NOT the 30% BALANCE_DEV_MAX the Illinois county-board dissolves
    carry. Berlin's 12.55% is not a shortfall against anything — it is what a
    six-seat city of 5,571 people measures. A figure that IMPROVES fails exactly
    as one that worsens, because both mean the plan under it moved.

    IT IS NOT ASSERTED AS A CENSUS IDENTITY. That column runs a little above or
    below each city's Census 2020 count (Berlin 5,571 against 5,486; Edgerton
    5,945 against 5,974) because ward lines have moved since, so the CLAIM here
    is the balance and not the total — the Grand Rapids posture.

    A ward the 2025 edition does not carry contributes nothing. That is honest
    for the deviation (an annexation sliver holds no measured population) and is
    why every such ward is ALSO named in `unplaced` or, for Appleton's ward 60,
    placed by a source that does carry it.
    """
    pinned = spec.get("balance")
    if pinned is None:
        raise RuntimeError("%s: no `balance` pinned — every composition carries "
                           "one" % spec["name"])
    feats = fetch_layer(POP_WARDS, "WARDID,PERSONS", geometry=False,
                        where="COUSUBFP = '%s'" % cousub)
    pop = {}
    for f in feats:
        try:
            pop[int(f["properties"]["WARDID"])] = f["properties"]["PERSONS"] or 0
        except (TypeError, ValueError):
            continue
    if not pop:
        raise RuntimeError("%s: the population layer returned no wards for %s"
                           % (spec["name"], cousub))
    by_dist = {}
    for w, d in ward_to_dist.items():
        by_dist[d] = by_dist.get(d, 0) + pop.get(w, 0)
    ideal = sum(by_dist.values()) / float(len(by_dist))
    if ideal <= 0:
        raise RuntimeError("%s: composed districts hold no population at all"
                           % spec["name"])
    worst = max(abs(v - ideal) / ideal for v in by_dist.values()) * 100
    if abs(worst - pinned) > BALANCE_TOL:
        raise RuntimeError(
            "%s: worst population deviation is %.2f%%, pinned at %.2f%% "
            "(total %d over %d districts, ideal %.0f). The composition or the "
            "wards under it have moved — re-read the source, then re-pin."
            % (spec["name"], worst, pinned, sum(by_dist.values()),
               len(by_dist), ideal))
    return worst


def _service_witness(spec, feats, ward_to_dist):
    """Re-derive the composition from the city's own district service.

    EDGERTON'S SOURCE IS A SERVICE, so its transcription can be checked against
    the thing it transcribes on every run — which is the difference between a
    table someone typed and one the build re-derives. Each composed ward's
    polygon must sit at least `min_share` inside the district the table gives
    it, measured against the city's own polygons.

    IT IS FETCHED AS ESRI JSON, not f=geojson: this is an ArcGIS ONLINE host
    (services7.arcgis.com), which is the host class whose GeoJSON exporter
    silently unnests interior rings — see esri_rings_to_geojson.
    """
    from shapely.geometry import shape
    w = spec["service_witness"]
    got = fetch_layer(w["url"], w["field"])
    dists = {}
    for f in got:
        label = (f["properties"].get(w["field"]) or "").strip()
        m = re.match(w["label_re"], label)
        if not m:
            raise RuntimeError("%s: the service labels a district %r, which does "
                               "not match %s" % (spec["name"], label, w["label_re"]))
        dists["%02d" % int(m.group(1))] = shape(f["geometry"]).buffer(0)
    if set(dists) != set(spec["districts"]):
        raise RuntimeError("%s: the service publishes districts %s; the composition "
                           "names %s" % (spec["name"], sorted(dists),
                                         sorted(spec["districts"])))
    worst = (1.0, None)
    for f in feats:
        ward = int(f["properties"]["WARDID"])
        d = ward_to_dist.get(ward)
        if d is None or not f.get("geometry"):
            continue          # declared unplaced, or the attribute-only pass
        g = shape(f["geometry"]).buffer(0)
        if not g.area:
            continue
        share = g.intersection(dists[d]).area / g.area
        if share < worst[0]:
            worst = (share, ward)
        if share < w["min_share"]:
            best = max(((g.intersection(dg).area / g.area, k)
                        for k, dg in dists.items()))
            raise RuntimeError(
                "%s: ward %d is composed into district %s but only %.4f of it "
                "lands there in the city's own layer (its largest share is %.4f "
                "in %s). The transcription and the service disagree."
                % (spec["name"], ward, d, share, best[0], best[1]))
    return worst


def classify(attr_feats):
    """Group ward attributes by municipality; return (shipped keys by
    municipality, computed exclusions, computed slivers, town-coded count)."""
    composed_unplaced = {k for k, spec in LOCAL_COMPOSITION.items()
                         if spec.get("unplaced")}
    mun = {}
    town_coded = 0
    for f in attr_feats:
        p = f["properties"]
        if is_coded(p.get("ALDERID")) and p.get("CTV") == "T":
            town_coded += 1
            continue
        if p.get("CTV") not in ("C", "V"):
            continue
        m = mun.setdefault(p["COUSUBFP"], {
            "name": p["MCD_NAME"], "ctv": p["CTV"], "coded": 0, "uncoded": 0,
            "coded_area": 0.0, "uncoded_area": 0.0, "districts": set()})
        area = p.get("Shape__Area") or 0.0
        if is_coded(p.get("ALDERID")):
            m["coded"] += 1
            m["coded_area"] += area
            m["districts"].add(p["ALDERID"].strip())
        else:
            m["uncoded"] += 1
            m["uncoded_area"] += area
    coded_mun = {k: m for k, m in mun.items() if m["coded"]}

    excluded, slivers = {}, {}
    for k, m in sorted(coded_mun.items()):
        if not m["uncoded"]:
            continue
        share = m["uncoded_area"] / (m["coded_area"] + m["uncoded_area"])
        if k in composed_unplaced:
            # A COMPOSED CITY'S LEFTOVERS ARE ALREADY NAMED, ONE BY ONE, in its
            # own `unplaced` table, where each ward's share of the municipality
            # is pinned and re-measured by apply_local_composition. The
            # "exactly one" rule below is NOT relaxed for it: that rule guards a
            # COUNTY's filing, where a second uncoded ward means a submission is
            # incomplete in a way nobody has looked at. Here the city's own
            # source has been read and the wards it does not name are known —
            # Edgerton has two (0.09% and 0.61%), Kaukauna one (0.29%).
            slivers[k] = m["name"]
        elif m["uncoded"] == 1 and share < 0.05:
            slivers[k] = m["name"]
        else:
            excluded[k] = (m["name"], m["uncoded"], round(share, 3))
    return coded_mun, excluded, slivers, town_coded


def bas_witness(ltsb_keys):
    """The state's own pre-dissolved layer, a different filing edition, must
    carry exactly the keys the state's WARD layer carries.

    IT IS COMPARED AGAINST THE STATE'S OWN KEYS AND NOT AGAINST WHAT SHIPS.
    Exclusions were always OUR honesty call rather than a disagreement about the
    coding, so they were folded back in; local composition is the same shape one
    step further — Appleton's fifteen districts are the CITY's statement and BAS
    has never carried eleven of them, so comparing against the shipped set would
    fail a witness that is working perfectly."""
    feats = fetch_layer(BAS_ALDERS, "COUSUBFP,CTV,ALDERID", geometry=False)
    bas = set()
    for f in feats:
        p = f["properties"]
        if p.get("CTV") in ("C", "V") and is_coded(p.get("ALDERID")):
            bas.add((p["COUSUBFP"], p["ALDERID"].strip()))
    ours = ltsb_keys
    if bas != ours:
        raise RuntimeError(
            "BAS witness disagrees: %d keys only in BAS (e.g. %s), %d only here (e.g. %s) — "
            "a filing edition moved; re-measure and move the EXPECT constants deliberately"
            % (len(bas - ours), sorted(bas - ours)[:4],
               len(ours - bas), sorted(ours - bas)[:4]))
    return len(bas)


def validate(source_wards, result_districts, samples=4000, seed=2026):
    """In-state sample points: wherever a full-precision coded ward answers,
    the dissolved+simplified district must answer with the same key. Tests
    the dissolve and the simplification in one measure."""
    src = _model(source_wards, "KEY")
    new = _model(result_districts, "KEY")
    rng = random.Random(seed)
    pts = []
    while len(pts) < samples:
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        hits = _districts_at(src, pt)
        if hits:
            pts.append((pt, hits))
    agree = 0
    for pt, o_hits in pts:
        s_hits = _districts_at(new, pt)
        if len(o_hits) == 1 and s_hits == o_hits:
            agree += 1
        elif len(o_hits) > 1:
            agree += 1  # a source self-overlap has no single right answer
    pct = 100.0 * agree / samples
    if pct < 99.9:
        return False, "point agreement only %.3f%% (need >= 99.9%%)" % pct
    return True, "%d/%d (%.3f%%) in-district point agreement" % (agree, samples, pct)


def main():
    check_only = "--check" in sys.argv[1:]

    attrs = fetch_layer(
        WARDS, "WARDID,COUSUBFP,MCD_NAME,CTV,ALDERID,Shape__Area", geometry=False)
    coded_total = sum(1 for f in attrs if is_coded(f["properties"].get("ALDERID")))
    if coded_total != EXPECT_CODED_WARDS:
        raise RuntimeError("ward layer carries %d coded wards, expected %d — a filing "
                           "window moved; re-measure before moving the constant"
                           % (coded_total, EXPECT_CODED_WARDS))
    # The STATE's own keys, taken before anything local is applied: this is what
    # the BAS witness compares against, so a locally composed district can never
    # make the two-edition check pass or fail on its own account.
    ltsb_keys = set()
    for f in attrs:
        p = f["properties"]
        if p.get("CTV") in ("C", "V") and is_coded(p.get("ALDERID")):
            ltsb_keys.add((p["COUSUBFP"], p["ALDERID"].strip()))
    if len(ltsb_keys) != EXPECT_DISTRICT_KEYS:
        raise RuntimeError("%d district keys in the state's filing, expected %d"
                           % (len(ltsb_keys), EXPECT_DISTRICT_KEYS))
    composed_wards, composed_mun = apply_local_composition(attrs)
    if composed_wards != EXPECT_COMPOSED_WARDS:
        raise RuntimeError("local composition assigned %d uncoded wards, expected %d — "
                           "a county has started (or stopped) filing them"
                           % (composed_wards, EXPECT_COMPOSED_WARDS))
    coded_mun, excluded, slivers, town_coded = classify(attrs)
    if town_coded != EXPECT_TOWN_CODED:
        raise RuntimeError("%d coded TOWN wards (expected %d — the Mercer anomaly); "
                           "a town cannot elect alderpersons, re-read the filing"
                           % (town_coded, EXPECT_TOWN_CODED))
    if len(coded_mun) != EXPECT_MUNICIPALITIES:
        raise RuntimeError("%d municipalities carry coded wards, expected %d"
                           % (len(coded_mun), EXPECT_MUNICIPALITIES))
    all_keys = set()
    for k, m in coded_mun.items():
        all_keys |= {(k, d) for d in m["districts"]}
    if len(all_keys) != EXPECT_TOTAL_KEYS:
        raise RuntimeError("%d district keys after composition, expected %d"
                           % (len(all_keys), EXPECT_TOTAL_KEYS))

    if {k: v for k, v in excluded.items()} != EXCLUDED:
        raise RuntimeError(
            "computed exclusions differ from the pinned list:\n  computed: %s\n  pinned:   %s\n"
            "A county completed (or broke) a submission — re-measure, then move EXCLUDED."
            % (json.dumps(excluded, sort_keys=True), json.dumps(EXCLUDED, sort_keys=True)))
    if {k: v for k, v in slivers.items()} != SLIVER_OK:
        raise RuntimeError("computed sliver-hole cities differ from SLIVER_OK: %s vs %s"
                           % (sorted(slivers), sorted(SLIVER_OK)))

    shipped_mun = {k: m for k, m in coded_mun.items() if k not in EXCLUDED}
    shipped_keys = {(k, d) for k, m in shipped_mun.items() for d in m["districts"]}
    excluded_keys = all_keys - shipped_keys
    n_bas = bas_witness(ltsb_keys)
    print("gates: %d coded wards + %d locally composed -> %d districts across %d "
          "municipalities shipped (%d districts in %d incomplete municipalities "
          "excluded; %d sliver holes; %d locally composed: %s; %d Mercer town wards "
          "dropped); BAS witness agrees on all %d of the state's own keys"
          % (coded_total, composed_wards, len(shipped_keys), len(shipped_mun),
             len(excluded_keys), len(EXCLUDED), len(SLIVER_OK), len(composed_mun),
             ", ".join("%s %d" % (LOCAL_COMPOSITION[k]["name"], n)
                       for k, n in sorted(composed_mun.items())),
             town_coded, n_bas),
          file=sys.stderr)
    if check_only:
        return

    # Geometry fetch: every coded C/V ward, PLUS every ward of a locally
    # composed municipality — those are uncoded on the server, so the id filter
    # alone fetches none of them and the count gate below fires (measured: it
    # did, 2,545 against 2,595, which is the gate doing its job). WARDID comes
    # back too because apply_local_composition keys on it, and it runs a SECOND
    # time here rather than trusting the attribute pass: the same three gates,
    # against the features actually about to be dissolved.
    where = ("CTV IN ('C','V') AND (ALDERID IS NOT NULL AND "
             "ALDERID NOT IN ('00','0000','')%s)"
             % "".join(" OR COUSUBFP = '%s'" % k for k in sorted(LOCAL_COMPOSITION)))
    wards = fetch_layer(WARDS, "WARDID,COUSUBFP,MCD_NAME,CTV,ALDERID,Shape__Area",
                        where=where)
    apply_local_composition(wards)
    wards = [w for w in wards if w["properties"]["COUSUBFP"] in shipped_mun
             and is_coded(w["properties"].get("ALDERID"))]
    expect_ward_n = sum(m["coded"] for m in shipped_mun.values())
    if len(wards) != expect_ward_n:
        raise RuntimeError("geometry fetch returned %d coded wards, attributes said %d"
                           % (len(wards), expect_ward_n))
    for w in wards:
        p = w["properties"]
        w["properties"] = {
            "KEY": p["COUSUBFP"] + "-" + p["ALDERID"].strip(),
            "COUSUBFP": p["COUSUBFP"],
            "MCD_NAME": p["MCD_NAME"],
            "CTV": p["CTV"],
            "ALDERID": p["ALDERID"].strip(),
        }

    # DISSOLVE AND SIMPLIFY ARE TWO CALLS, NOT ONE, AND THAT IS THE WHOLE REASON
    # THE DROPPED-RING QUESTION COULD NOT BE ASKED BEFORE. One call produced only
    # the simplified output, so there was nothing to compare it against; the gate
    # needs the pre-simplification dissolve as its source. This is the shape
    # `build_wi_supervisory_districts.py` already uses.
    def _mapshaper(src, extra, out):
        subprocess.run(
            ["npx", "-y", MAPSHAPER, src,
             "-dissolve2", "KEY", "copy-fields=COUSUBFP,MCD_NAME,CTV,ALDERID"]
            + extra + ["-o", "precision=" + PRECISION, "format=geojson", out],
            check=True, cwd=REPO_ROOT)
        with open(out) as f:
            return json.load(f)

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "wards-src.geojson")
        with open(src_path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": wards}, f)
        source = _mapshaper(src_path, [], os.path.join(tmp, "alder-src.geojson"))
        dissolved = _mapshaper(src_path, SIMPLIFY, os.path.join(tmp, "alder.geojson"))

    feats = dissolved["features"]
    if len(feats) != len(shipped_keys):
        raise RuntimeError("dissolve produced %d districts, expected %d"
                           % (len(feats), len(shipped_keys)))
    out_keys = {(f["properties"]["COUSUBFP"], f["properties"]["ALDERID"]) for f in feats}
    if out_keys != shipped_keys:
        raise RuntimeError("dissolved key set differs from the plan (e.g. %s)"
                           % sorted(shipped_keys ^ out_keys)[:4])

    ok, msg = validate(wards, feats)
    if not ok:
        raise RuntimeError("validation failed: %s" % msg)

    # EVERY DROPPED RING IS ANSWER-TESTED, AND THE 4,000-POINT CHECK ABOVE CANNOT
    # SEE THEM. That check scatters points over 159 municipalities and the one
    # ring that costs an answer is 6 m2, so it is blind to it by construction —
    # which is exactly the mistake `wi/WATCH.md` row 58 records being made on the
    # sibling NG911 layer, where a 20,000-point sample saw zero changed answers
    # and the rebuild had changed 397 features.
    records, dstats = drings.classify({
        LAYER_NAME: {"source": source["features"], "drawn": feats, "key": "KEY"}})

    # THE UNION OF EACH RECORD'S SIGNATURES, never one per record: rings that
    # coincide on the ground and differ byte for byte are folded into one record,
    # so taking a single signature leaves the other ring looking retained and the
    # fidelity gate then measures a shape that is gone.
    dropped_sigs = {sig for r in records for sig in r["signatures"]}

    # HOW FAR THE RETAINED BOUNDARY MOVED, which is a different question from the
    # one below. `check` asks what a whole DROPPED ring costs a reader; a retained
    # ring keeps only a subset of its vertices, so the drawn line can cut a chord
    # across a narrow excursion and hand its ground to whoever is next door — or,
    # on this layer, to nobody, because it covers municipalities rather than the
    # whole state. That was measured by nothing here until 2026-09-27.
    src_by_key = {f["properties"]["KEY"]: f["geometry"] for f in source["features"]}
    steps = drings.source_step_m(src_by_key, dropped_sigs)
    fok, fmsg = drings.check_fidelity(source["features"], feats, "KEY",
                                      dropped_sigs, FIDELITY_MAX_M)
    print("fidelity: median source step %.2f m, ceiling %.2f m (%.2fx); %s"
          % (steps[len(steps) // 2], FIDELITY_MAX_M,
             FIDELITY_MAX_M / steps[len(steps) // 2], fmsg), file=sys.stderr)
    if not fok:
        raise RuntimeError(
            "fidelity check failed: %s\n"
            "  A chord has been drawn across ground that changes hands. Re-measure "
            "at a finer setting rather than raising FIDELITY_MAX_M, which is "
            "derived from this layer's own median source step." % fmsg)

    dok, dmsg = drings.check(records, dstats, ACCEPTED_DROPPED_RINGS, GAP_CLOSED)
    print("dropped rings: %s" % dmsg, file=sys.stderr)
    if not dok:
        print("\n--- measured declarations for ACCEPTED_DROPPED_RINGS ---",
              file=sys.stderr)
        print("GAP_CLOSED = %d" % dstats[drings.KIND_GAP_CLOSED], file=sys.stderr)
        for r in records:
            if r.get("harm"):
                print("  %s" % json.dumps(
                    {k: r[k] for k in ("m2", "interior", "features", "kind", "answers")
                     if k in r}, sort_keys=True), file=sys.stderr)
        raise RuntimeError("dropped-ring check failed: %s" % dmsg)

    feats.sort(key=lambda f: (f["properties"]["COUSUBFP"],
                              f["properties"]["ALDERID"]))
    compact = json.dumps({"type": "FeatureCollection", "features": feats},
                         separators=(",", ":"), ensure_ascii=False)
    out_path = os.path.join(APP_DATA_DIR, OUT_NAME)
    with open(out_path, "w") as f:
        f.write(compact)
    print("aldermanic-districts -> data/app/%s: %d districts, %d municipalities; %s; "
          "%d bytes (%s retain, 6dp)"
          % (OUT_NAME, len(feats), len(shipped_mun), msg, len(compact), SIMPLIFY_LABEL),
          file=sys.stderr)


if __name__ == "__main__":
    main()
