#!/usr/bin/env python3
"""
Build data/app/county-supervisory-districts.json — every Wisconsin county
board supervisory district, statewide, in one pre-simplified file.

WHERE THE LINES COME FROM
-------------------------
Wisconsin is the one state in this fleet whose county board districts have a
STATEWIDE publisher. Wis. Stat. 5.15(4)(br)1 makes every county submit its
current supervisory district boundaries to the Legislative Technology
Services Bureau twice a year (15 January and 15 July), and LTSB publishes the
aggregate as an open ArcGIS feature service. So the 72-county answer that
costs Illinois one build per county costs Wisconsin one fetch.

That is a convenience, not an authority: LTSB republishes what a county
CLERK sent it, and a defective submission stays defective. This build
therefore never trusts the aggregate on its own — see the gates below.

TREMPEALEAU IS BUILT FROM THE COUNTY'S OWN LAYER, NOT LTSB
----------------------------------------------------------
LTSB's July 2026 file gives Trempealeau SIXTEEN districts numbered 1-14, 16,
17 — no district 15. It is not a missing polygon: the sixteen tile the county
completely (their union covers 100% of the county's own district 15 and
99.935% of its whole plan), because LTSB's "17" is drawn over the county's 15
AND 17 together. It is a MERGE.

The county did not merge them. Trempealeau County's own board page seats
SEVENTEEN supervisors in districts 1 through 17 — District 15 is David
Larson, term ending April 2028 — and the county's own 2021-2031 district
service publishes seventeen districts of 1,736-1,892 people each (ideal
1,809, worst deviation 4.6%), which is what an adopted plan looks like.
LTSB's merged district would hold about 3,478 against a sixteen-seat ideal of
1,922: +81%, which no county adopts and no court would allow.

So for Trempealeau alone the geometry comes from the county's own service and
the other 71 counties come from LTSB — the fleet's standing rule that
geometry comes from whatever proves the lines. Shipping LTSB's Trempealeau
would have told roughly 1,826 people they are in district 17, under a
supervisor who does not represent them.

WHAT THE GATES ACTUALLY CATCH
-----------------------------
* SUPERID continuity (1..n per county) is what caught Trempealeau, because
  the merge left a hole in the NUMBERING. It would not catch a county that
  merged and then renumbered cleanly.
* Ward reconciliation is the structural check: Wisconsin supervisory
  districts are built from whole municipal wards, so LTSB's ward layer
  carries each ward's SUPER_FIPS. Every ward must resolve to a district and
  every district must own at least one ward — a dropped district shows up as
  orphaned wards, whatever the numbering does.
* Per-county seat counts were checked against each county's OWN board page in
  a separate sweep (scripts/... see docs); this build re-asserts only what it
  can measure from the two services.

Population BALANCE is deliberately not a gate. It was measured (ward
populations from LTSB's 2024 election layer, which sum to 5,893,718 — the
state's exact 2020 census count) and it flags counties whose own adopted
plans are simply unequal: Juneau's spread is 466 to 2,157 across 21
districts, and Juneau County's own site publishes those same 21 districts.
An imbalanced plan is the county's, not this file's, and refusing to draw it
would hide a real district rather than fix anything.

Occasional OPERATOR step, not weekly CI — re-run after a 15 Jan / 15 Jul
submission window. Prerequisites: curl and Node.js (mapshaper).

Usage:
    python3 wi/scripts/build_wi_supervisory_districts.py
    python3 wi/scripts/build_wi_supervisory_districts.py --check   # gates only, no write
"""

import datetime
import json
import os
import random
import subprocess
import sys
import tempfile

import dropped_rings as drings

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
OUT_NAME = "county-supervisory-districts.json"
MAPSHAPER = "mapshaper@0.6.102"  # pinned for reproducible output (fleet convention)

LTSB_ORG = "https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest/services"
DISTRICTS = LTSB_ORG + "/WI_County_Supervisory_Districts_Current/FeatureServer/0"
WARDS = LTSB_ORG + "/WI_Municipal_Wards_Current/FeatureServer/0"

# Trempealeau County's own adopted plan, from the service its own "See What
# Voting District You're In" map draws (https://arcg.is/4GGSj0).
TREMPEALEAU_FIPS = "55121"
TREMPEALEAU_NAME = "Trempealeau"
TREMPEALEAU = (
    "https://services9.arcgis.com/cqHJZMbXoaOT0XrP/arcgis/rest/services"
    "/Trempealeau_County_County_Board_Supervisor_Districts_2021_2031_WFL1/FeatureServer/3"
)
TREMPEALEAU_SEATS = 17  # the county's own board page, districts 1-17

# The sidecar this builder writes on every real run, and the monthly
# validate_sources.py run compares against the live services. LTSB republishes
# under Wis. Stat. 5.15(4)(br)1 each 15 January and 15 July; this is an OPERATOR
# build with no schedule, so without a pin nothing could see the two drift
# apart — the same hole, and the same remedy, as the NG911 sidecar.
SIDECAR = os.path.join(REPO_ROOT, "data", "source", "supervisory", "built-rows.json")

EXPECT_DISTRICTS = 1589   # LTSB, July 2026 submission window
EXPECT_COUNTIES = 72      # every Wisconsin county
EXPECT_WARDS_MIN = 7000   # LTSB ward layer, ~7,161 as of July 2026

# DOUGLAS-PEUCKER AT A METRE INTERVAL, NOT A VISVALINGAM PERCENTAGE, AND THE
# REASON IS THE ANSWER A READER GETS RATHER THAN THE FILE SIZE. Visvalingam
# thresholds triangle AREA, which does not bound how far the drawn line strays,
# and it drops far more rings: measured on the July 2026 filing, the visvalingam
# 9% setting this replaces loses 586 distinct rings of which 73 CHANGE THE DISTRICT
# A READER IS TOLD THEY ARE IN — the largest a 3,496 m2 patch answered Sheboygan 10
# where the truth is Sheboygan 20, and thirty-odd false silences in DOOR COUNTY up
# to 2,621 m2, which is the county it would be: a peninsula with islands, so its
# districts carry detached parts for `keep-shapes` to drop. (Read the county from
# the data and never from the FIPS by eye — 5502904 is Door 04, not Brown, and
# this comment said Brown and Milwaukee before the names were looked up.)
# `dropped_rings.py` is what measures that, and the whole curve is:
#
#     setting          harms   harmed area   largest   >=100 m2   >=1000 m2   gzipped
#     visvalingam 9%      73     67,185 m2   3,496 m2        65          31   --
#     dp interval=4        2         38 m2      37 m2         0           0   +38.6%
#     dp interval=5        8      1,967 m2   1,572 m2         2           1   +27.2%
#     dp interval=6        9      2,140 m2   1,572 m2         3           1   +18.5%
#     dp interval=7       15      4,246 m2   1,572 m2         9           1   +11.7%
#     dp interval=10      21      7,082 m2   1,572 m2        15           2   -2.3%
#
# WHETHER A READER CAN STAND THERE IS MEASURED, NOT INFERRED FROM THE COORDINATES,
# and it is what settles interval=4 against 7. Each harm's interior point is put to
# TIGER's own AREAL HYDROGRAPHY layer: a point inside a water polygon is water, and
# the controls run first — the instance's own Marathon anchor returns no polygon,
# open Lake Michigan returns "Lk Michigan", Lake Winnebago returns "Lk Winnebago".
# A county subdivision is NOT the test, because a town's polygon can include its
# own shoreline water, so "inside Gardner town" proves nothing on its own.
#
#     setting            harms   on DRY LAND   dry area    largest dry   dry >=1000
#     visvalingam 9%        73            62   58,994 m2      3,496 m2           29
#     dp interval=7         15            13
#     dp interval=4          2             2         38 m2       37 m2            0
#
# THE SHIPPED MAP THEREFORE GIVES 62 WRONG OR MISSING ANSWERS ON GROUND A PERSON
# CAN STAND ON, 29 of them on patches over 1,000 m2. Every one of the eleven water
# harms is a false silence in a Door County bay or on Green Lake.
#
# AND THE DECIDING OBJECT IS ONE RING: 1,571.98 m2 at 43.893508,-91.190077, about
# 40 m by 40 m, DRY LAND inside ONALASKA CITY, where a reader is told La Crosse 18
# and the truth is La Crosse 19. Dropped at every interval from 5 to 25, RETAINED
# at 4. Interval=7 also loses a 978 m2 patch inside KENOSHA CITY. A count alone
# could not have settled this — a 0.84 m2 sliver and a standable lobe are both `1`
# to a counter — and neither could area alone, since area cannot tell a bay from a
# street.
#
# This instance already decides these by magnitude rather than by count: Lincoln's
# disputed lobe was WITHHELD because it was a majority of its district, and
# Ashland's ward-18 difference SHIPPED at 3.8% of its. Same question, same answer.
# Population-weighting would be better and is not available — this instance
# declares no `population` index — so area is the honest proxy and is named as one.
#
# HARMS ARE COUNTED AS A READER IS ANSWERED, one district and not the set — see
# `dropped_rings.py` for why, and for the 102-against-73 that distinction is worth
# on this layer.
#
# interval=4 is the setting whose harms are few enough to declare one by one,
# which is the bar this file now has to clear. IT COSTS +402 KB GZIPPED and that
# is stated rather than buried: the trade is 71 fewer wrong answers — 73 down to
# 2 — for a third again of a cache-first file. (Both figures in this sentence were
# wrong on first writing: +414 KB was an estimate off a cached source rather than
# the +402 measured against `git show origin/main:`, and "99" was the difference
# between SET-comparison counts that the reader-answer fix retired.) Since #1197 that file is cached the FIRST TIME A
# LAYER USES IT rather than at install, so the bytes fall only on readers who
# open the county-supervisory layer instead of on every first visit.
SIMPLIFY = ["dp", "keep-shapes", "interval=4"]

# Holes the simplifier closes that NO district covered — see dropped_rings.py for
# why these are counted rather than declared one by one. The count is held
# EXACTLY, so a rebuild that starts closing a different number stops and gets
# read; it is written by the build rather than guessed, and the first run after a
# new LTSB filing is expected to move it.
#
# THE "STITCHING ARTEFACT RATHER THAN A DELIBERATE VOID" READING IS MEASURED AND
# NOT MERELY ARGUED, and the test is COMPLEXITY as well as size: a real void — a
# lake, an airfield, a non-jurisdictional parcel — would be both large and finely
# traced. On these 235 rings the two are ANTI-CORRELATED. The largest is 1,153 m2
# with FOUR vertices, a quadrilateral; the most complex are 54, 49 and 37 vertices
# and every one of those is under 6 m2, sub-metre wiggles between two finely-drawn
# Waukesha wards. Of the 20 rings at or above 100 m2, eleven are triangles or
# quadrilaterals and the most complex has 28. Median area 1.34 m2. Not one ring is
# both large and complex, which is what a deliberate void would be.
#
# RE-MEASURED 2026-09-27 OVER 235 RINGS, having been measured over 229 — the exact
# retained test found six more with no setting changed. Two figures moved with it
# and are corrected above: the median 1.54 -> 1.34 m2, and the count at or above
# 100 m2 19 -> 20. The largest, the three most complex, the eleven simple large
# ones and the 28-vertex maximum are unchanged, and so is the conclusion. A
# characterisation of a SET goes stale when the set grows, even where the sentence
# it supports stays true, so it is re-derived from the build's own classification
# rather than carried forward.
GAP_CLOSED = 235

# Rings whose loss changes the district a reader is told they are in. Written from
# the builder's own gate output, never by hand — run the build, read the UNDECLARED
# lines, and paste what it measured. Each FAILS when nothing matches it.
ACCEPTED_DROPPED_RINGS = [
    {
        # DOOR COUNTY DISTRICT 4, a 36.75 m2 detached part of the district — a
        # separate outer ring rather than a hole, which is why its loss is a
        # silence and not a gap closed. `keep-shapes` protects a SHAPE and not a
        # RING, so once the main part survives this one is eligible for removal
        # like any other geometry.
        #
        # IT IS ON DRY LAND, AND AN EARLIER VERSION OF THIS COMMENT SAID OPEN
        # WATER. Measured 2026-09-27 against TIGER's own areal hydrography layer —
        # the discriminator, since a county subdivision's polygon can include its
        # own shoreline water and "inside Gardner town" therefore proves nothing —
        # this point returns NO water polygon, where a control in open Lake
        # Michigan returns "Lk Michigan" and one in Lake Winnebago returns
        # "Lk Winnebago". TIGER puts it in GARDNER TOWN, Door County. Door is
        # still the county this would be, a peninsula with islands whose districts
        # carry detached parts, but this particular ring is a sliver on dry ground
        # near the county's edge rather than an islet offshore.
        #
        # A READER STANDING THERE IS TOLD DOOR 4 TODAY AND WOULD BE TOLD NOTHING,
        # which is the false-silence half of the two harms this table is for, and
        # the dry-land measurement makes that worse rather than better: it is
        # ground a person can be on. It is declared rather than avoided because no
        # tested dp interval from 4 to 25 retains it, so the alternative is not a
        # finer setting but a different simplifier.
        "lat": 44.829563, "lng": -87.564510, "verts": 18, "m2": 36.75,
        # Inside the ring at 6 decimals, checked rather than assumed — the build
        # path refuses a point `point_in_ring` rejects, and `--check-shipped`
        # re-derives the AFTER answer here without any source to scan.
        "interior": {"lat": 44.829526, "lng": -87.564510, "decimals": 6},
        "features": ["county-supervisory:5502904"],
        "kind": "false-silence",
        "answer_before": {"county-supervisory": ["5502904"]},
        "answer_after": {"county-supervisory": []},
        "why": "no tested dp interval from 4 to 25 retains it; 36.75 m2 of DRY "
               "LAND in Gardner town, Door County, measured against TIGER's areal "
               "hydrography rather than guessed from the coordinates, and the "
               "answer it costs is recorded above rather than claimed harmless",
        "date": "2026-09-26",
    },
    {
        # LAFAYETTE COUNTY, a 0.84 m2 sliver on the line between districts 3 and 7.
        # BOTH DISTRICTS DREW IT, each with its own vertices, so it is two rings
        # that coincide on the ground and differ byte for byte — one record naming
        # both, which is why `dropped_rings._merge_coincident` exists. Before the
        # merge this produced two harm records and no single declaration could
        # satisfy either, because each named a different district.
        #
        # A reader is told Lafayette 3 today and would be told Lafayette 7. Which of
        # the two is right is not something this build can know: the sliver is where
        # the county's own submission overlaps itself, and LTSB's statewide geometry
        # does that on 0.017% of its area. So the declaration records the move
        # rather than asserting that either answer is the true one.
        "lat": 42.669785, "lng": -90.129781, "verts": 5, "m2": 0.84,
        "interior": {"lat": 42.669739, "lng": -90.129779, "decimals": 6},
        "features": ["county-supervisory:5506503", "county-supervisory:5506507"],
        "kind": "wrong-name",
        "answer_before": {"county-supervisory": ["5506503"]},
        "answer_after": {"county-supervisory": ["5506507"]},
        "why": "0.84 m2 of self-overlap between two districts of one county, which "
               "no interval resolves because the source disagrees with itself "
               "there; dry land in Darlington town by the same hydrography test",
        "date": "2026-09-26",
    },
    {
        # LAFAYETTE COUNTY AGAIN, 2.86 m2 on the line between districts 13 and 14,
        # and the SECOND of three Lafayette rings this table now carries. The
        # 0.84 m2 entry below already records the cause: the county's own
        # submission overlaps itself, and LTSB's statewide geometry does that on
        # 0.017% of its area. What is new is that the EXACT retained test sees
        # them at all — the old any-vertex test read a ring joined to its
        # district's main body by one shared vertex as retained, so a ring that
        # vanished whole measured as kept and its answer change was never
        # counted.
        #
        # DRY LAND, measured 2026-09-27 against TIGER's areal hydrography with
        # four controls answering first (Marathon dry, Lake Michigan, Lake
        # Winnebago and Lake Mendota water). TIGER puts it in SHULLSBURG CITY.
        "lat": 42.566190, "lng": -90.221222, "verts": 4, "m2": 2.86,
        "interior": {"lat": 42.566190, "lng": -90.221241, "decimals": 6},
        "features": ["county-supervisory:5506514"],
        "kind": "wrong-name",
        "answer_before": {"county-supervisory": ["5506514"]},
        "answer_after": {"county-supervisory": ["5506513"]},
        "why": "2.86 m2 of self-overlap between two districts of one county, "
               "which no interval resolves because the source disagrees with "
               "itself there; dry land in Shullsburg city by the hydrography "
               "test, and which of the two districts is right is not something "
               "this build can know",
        "date": "2026-09-27",
    },
    {
        # ST. CROIX COUNTY, districts 11 and 12, and THE SAME GROUND AS THE
        # ALDERMANIC LAYER'S OWN 1.24 m2 RING. Both layers are dissolved from the
        # state's ward fabric, so a sliver in that fabric is inherited by
        # everything drawn from it — which is why the same 5 vertices at the same
        # coordinates appear in two tables in two different builders.
        #
        # THE TWO LAYERS PAY FOR IT DIFFERENTLY, and that is the reason both
        # declarations exist rather than one: the supervisory layer tiles the
        # whole state, so losing the ring hands the reader the neighbouring
        # district (a wrong name), while the aldermanic layer covers only
        # municipalities, so losing it hands the reader NOTHING (a false
        # silence). One sliver, two harms, because the two layers cover
        # different ground.
        #
        # DRY LAND by the same hydrography read, in STAR PRAIRIE TOWN.
        "lat": 45.126489, "lng": -92.569594, "verts": 5, "m2": 1.24,
        "interior": {"lat": 45.126485, "lng": -92.569614, "decimals": 6},
        "features": ["county-supervisory:5510911", "county-supervisory:5510912"],
        "kind": "wrong-name",
        "answer_before": {"county-supervisory": ["5510912"]},
        "answer_after": {"county-supervisory": ["5510911"]},
        "why": "1.24 m2 where two districts of one county both drew the same "
               "ground, the same sliver the aldermanic layer declares because "
               "both dissolve the state's ward fabric; dry land in Star Prairie "
               "town by the hydrography test",
        "date": "2026-09-27",
    },
    {
        # LAFAYETTE COUNTY, THE THIRD, 0.27 m2 between districts 3 and 13 — and
        # the smallest ring any declaration in this fleet carries. Its interior
        # point and its centre are the same to six decimals, which is what a ring
        # a quarter of a square metre across looks like at the precision this
        # file ships at.
        #
        # DRY LAND by the same hydrography read, in SEYMOUR TOWN.
        "lat": 42.646030, "lng": -90.220670, "verts": 4, "m2": 0.27,
        "interior": {"lat": 42.646030, "lng": -90.220670, "decimals": 6},
        "features": ["county-supervisory:5506513"],
        "kind": "wrong-name",
        "answer_before": {"county-supervisory": ["5506513"]},
        "answer_after": {"county-supervisory": ["5506503"]},
        "why": "0.27 m2 of self-overlap between two districts of one county, "
               "the third such ring in Lafayette; dry land in Seymour town by "
               "the hydrography test",
        "date": "2026-09-27",
    },
]
PRECISION = "0.000001"    # 6 decimals ~= 0.11 m
STATE_BBOX = {"minLng": -93.09, "minLat": 42.29, "maxLng": -86.04, "maxLat": 47.51}
VALIDATION_KEY = "SUPER_FIPS"
LAYER_NAME = "county-supervisory"  # the key answers are recorded under


def _curl(url):
    return subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300",
         "-H", "User-Agent: districtry/1.0 (+https://districtry.com/wi/)", url],
        check=True, capture_output=True,
    ).stdout


def oid_field(base):
    """The layer's own object-id column. LTSB's layers call it OBJECTID and
    Trempealeau's call it FID; paging with the wrong name returns nothing at
    all rather than erroring, so it is read from the layer rather than
    assumed."""
    meta = json.loads(_curl(base + "?f=json"))
    for f in meta.get("fields", []):
        if f.get("type") == "esriFieldTypeOID":
            return f["name"]
    raise RuntimeError("no object-id field on " + base)


def layer_pin(base):
    """What this layer reported at build time: its NAME, its own last data edit,
    and the count its query endpoint answers.

    THE NAME IS THE STRONGEST SIGNAL AND IS WHY THIS IS NOT A ROW COUNT ALONE.
    LTSB names the layer for the filing window it published — `Supervisory_July_2026`
    today, `Supervisory_January_2027` after the next one — so the name moves at
    the statutory moment whether or not the district total happens to land on a
    different number. A count cannot promise that; 72 counties can refile and
    still sum to 1589.

    The count comes from the SAME returnCountOnly endpoint the monthly check
    reads, rather than from len(features) here, so the two compare like with
    like — a paged fetch and a count query need not agree if the service changes
    under a long build.
    """
    meta = json.loads(_curl(base + "?f=json"))
    edit = None
    ms = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    if isinstance(ms, (int, float)):
        edit = datetime.datetime.fromtimestamp(
            ms / 1000.0, datetime.timezone.utc).date().isoformat()
    count = json.loads(_curl(
        base + "/query?where=1%3D1&returnCountOnly=true&f=json")).get("count")
    return {"name": meta.get("name"), "dataLastEdit": edit, "rows": count}


def _ring_is_clockwise(ring):
    """Esri's own rule: a CLOCKWISE ring is an outer boundary, a
    COUNTER-CLOCKWISE one is a hole in the ring that contains it."""
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        s += (x2 - x1) * (y2 + y1)
    return s > 0


def _ring_area(ring):
    """Unsigned planar area of a ring, in squared degrees — used only to compare
    rings with each other, never as a real-world measurement."""
    s = 0.0
    for i in range(len(ring) - 1):
        s += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(s) / 2.0


def _ring_contains(outer, pt):
    x, y = pt[0], pt[1]
    inside = False
    for i in range(len(outer) - 1):
        x1, y1 = outer[i][0], outer[i][1]
        x2, y2 = outer[i + 1][0], outer[i + 1][1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def esri_rings_to_geojson(rings, label=""):
    """Esri rings -> a properly NESTED GeoJSON Polygon/MultiPolygon.

    WHY THIS EXISTS, measured 2026-09-05. `fetch_layer` used to ask ArcGIS for
    `f=geojson` and ship whatever came back. For the NG911 law layer's MASON
    (Marquette County) the server's GeoJSON export returned the feature as a
    MultiPolygon of THREE SINGLE-RING POLYGONS — 1330, 40 and 4 vertices — where
    its own Esri-JSON form returns the same three rings with the 40-vertex one
    COUNTER-CLOCKWISE, i.e. a hole: the Village of Westfield, which files its own
    police department. The exporter had failed to nest it, so the hole became a
    shell, MASON's area grew 669.20 -> 677.13 km2, and every point in Westfield
    got a card reading "MASON ... Also filed at this point: WPD ... concurrent
    jurisdiction exactly as the county filed it" — a jurisdiction the county did
    NOT file. The build's own 4,000-point agreement gate could not see it: it
    compares the dissolved output against the same fetch, so it agreed with
    itself. Not every feature is affected (Brown County Sheriff Law Zone 5A came
    back correctly nested the same day), which is what makes it a silent class
    rather than an outage.

    So the fetch asks for `f=json` and does the nesting here, where the rule is
    NORMATIVE rather than inferred. Winding alone is not enough to lean on in
    GeoJSON — RFC 7946 wants exterior rings counter-clockwise, the opposite
    convention — so this reads Esri's orientation AND requires containment
    before it treats a ring as a hole; a counter-clockwise ring contained by
    nothing is kept as its own shell rather than silently dropped.
    """
    shells, holes = [], []
    for ring in rings:
        if len(ring) < 4:
            # Degenerate; keep it as a shell so nothing is silently discarded.
            shells.append(ring)
            continue
        (shells if _ring_is_clockwise(ring) else holes).append(ring)
    if not shells:
        # Every ring counter-clockwise: the orientation signal is absent, so
        # treat them all as shells rather than inventing holes.
        shells, holes = list(rings), []
    polys = [[s] for s in shells]
    shell_area = [_ring_area(s) for s in shells]
    for hole in holes:
        # WHICH SHELL OWNS A HOLE — measured 2026-09-05, after a first draft of
        # this function got it wrong on Marathon County Sheriff Department. That
        # feature has 34 rings: 22 shells and 12 holes. One of its shells is a
        # 17-vertex SLIVER OF ZERO AREA, and an even-odd test against a zero-area
        # ring is not reliable — it reported that the sliver "contained" a hole
        # of area 0.0358, and a tie-break that only asked whether one SHELL sat
        # inside another then handed the hole to the sliver instead of to the
        # county outline. The hole was therefore never subtracted, and the source
        # claimed the Sheriff covered Kronenwetter, Wausau and Mountain Bay,
        # which the service's own point query denies. So: a hole goes to the
        # SMALLEST shell that contains it AND is larger than it, and containment
        # is a majority vote over three of the hole's own vertices rather than
        # one — a single vertex can sit exactly on a neighbouring ring.
        h_area = _ring_area(hole)
        probes = [hole[0], hole[len(hole) // 3], hole[(2 * len(hole)) // 3]]
        owner, owner_area = None, None
        for i, s in enumerate(shells):
            if shell_area[i] <= h_area:
                continue
            if sum(1 for pt in probes if _ring_contains(s, pt)) < 2:
                continue
            if owner is None or shell_area[i] < owner_area:
                owner, owner_area = i, shell_area[i]
        if owner is None:
            polys.append([hole])          # contained by nothing: its own shell
        else:
            polys[owner].append(hole)
    if len(polys) == 1:
        return {"type": "Polygon", "coordinates": polys[0]}
    return {"type": "MultiPolygon", "coordinates": [[list(r) for r in p] for p in polys]}


def _esri_feature_to_geojson(f, label=""):
    geom = f.get("geometry")
    out = None
    if geom:
        if "rings" in geom:
            out = esri_rings_to_geojson(geom["rings"], label)
        elif "x" in geom and "y" in geom:
            out = {"type": "Point", "coordinates": [geom["x"], geom["y"]]}
        elif "paths" in geom:
            paths = geom["paths"]
            out = ({"type": "LineString", "coordinates": paths[0]} if len(paths) == 1
                   else {"type": "MultiLineString", "coordinates": paths})
        else:
            raise RuntimeError("unhandled Esri geometry shape: %s"
                               % sorted(geom.keys()))
    return {"type": "Feature", "properties": f.get("attributes") or {},
            "geometry": out}


def fetch_layer(base, out_fields, geometry=True, where="1=1"):
    """Page an ArcGIS feature layer out as GeoJSON in 4326.

    Asks the server for ESRI JSON and converts, rather than asking for
    `f=geojson` — see esri_rings_to_geojson for the hole the GeoJSON exporter
    silently unnested and the wrong card it produced.
    """
    import urllib.parse
    order = oid_field(base)
    feats = []
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": out_fields,
            "returnGeometry": "true" if geometry else "false",
            "outSR": "4326",
            "geometryPrecision": "6",
            "f": "json",
            "resultOffset": str(offset),
            "resultRecordCount": "1000",
            "orderByFields": order,
        }
        data = json.loads(_curl(base + "/query?" + urllib.parse.urlencode(params)))
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError("ArcGIS error from %s: %s" % (base, data["error"]))
        batch = [_esri_feature_to_geojson(f) for f in (data.get("features") or [])]
        feats.extend(batch)
        if not data.get("exceededTransferLimit") \
           and not data.get("properties", {}).get("exceededTransferLimit"):
            break
        if not batch:
            break
        offset += len(batch)
    return feats


def normalize_ltsb(features):
    """Keep only what the card reads, and drop LTSB's CONTACT column — those
    are county staff members' individual e-mail addresses, published for
    redistricting correspondence and not for republication in a public app."""
    out = []
    for f in features:
        p = f["properties"]
        out.append({
            "type": "Feature",
            "properties": {
                "CNTY_FIPS": p["CNTY_FIPS"],
                "CNTY_NAME": p["CNTY_NAME"],
                "SUPERID": str(int(p["SUPERID"])),
                "SUPER_FIPS": p["SUPER_FIPS"],
            },
            "geometry": f["geometry"],
        })
    return out


def trempealeau_features():
    feats = fetch_layer(TREMPEALEAU, "DISTRICT")
    if len(feats) != TREMPEALEAU_SEATS:
        raise RuntimeError(
            "Trempealeau's own layer returned %d districts, expected %d — the county's "
            "plan may have changed; re-read its board page before shipping"
            % (len(feats), TREMPEALEAU_SEATS)
        )
    nums = sorted(int(f["properties"]["DISTRICT"]) for f in feats)
    if nums != list(range(1, TREMPEALEAU_SEATS + 1)):
        raise RuntimeError("Trempealeau districts are %s, expected 1..%d" % (nums, TREMPEALEAU_SEATS))
    out = []
    for f in feats:
        n = int(f["properties"]["DISTRICT"])
        out.append({
            "type": "Feature",
            "properties": {
                "CNTY_FIPS": TREMPEALEAU_FIPS,
                "CNTY_NAME": TREMPEALEAU_NAME,
                "SUPERID": str(n),
                "SUPER_FIPS": "%s%02d" % (TREMPEALEAU_FIPS, n),
            },
            "geometry": f["geometry"],
        })
    return out


def gate_districts(feats):
    """Structural gates on the assembled statewide set."""
    by_county = {}
    for f in feats:
        p = f["properties"]
        by_county.setdefault((p["CNTY_FIPS"], p["CNTY_NAME"]), []).append(int(p["SUPERID"]))
    if len(by_county) != EXPECT_COUNTIES:
        raise RuntimeError("%d counties, expected %d" % (len(by_county), EXPECT_COUNTIES))
    bad = []
    for (fips, name), ids in sorted(by_county.items()):
        if sorted(ids) != list(range(1, len(ids) + 1)):
            missing = [i for i in range(1, max(ids) + 1) if i not in set(ids)]
            bad.append("%s (%s): %d districts, numbering gaps at %s" % (name, fips, len(ids), missing))
    if bad:
        raise RuntimeError(
            "district numbering is not 1..n in %d county/counties — a county may have "
            "merged or dropped a district and the submission not caught up:\n  %s"
            % (len(bad), "\n  ".join(bad))
        )
    fipses = [f["properties"]["SUPER_FIPS"] for f in feats]
    if len(set(fipses)) != len(fipses):
        raise RuntimeError("SUPER_FIPS is not unique across the statewide set")
    return by_county


def gate_wards(feats):
    """Wisconsin supervisory districts are unions of whole municipal wards, so
    LTSB's ward layer is an independent witness to the district set: every
    ward must name a district that exists, and every district must own at
    least one ward. A district dropped from the district layer shows up here
    as orphaned wards even if the numbering was tidied afterwards."""
    wards = fetch_layer(WARDS, "WARD_FIPS,CNTY_FIPS,SUPER_FIPS", geometry=False)
    if len(wards) < EXPECT_WARDS_MIN:
        raise RuntimeError("ward layer returned %d wards, expected >= %d" % (len(wards), EXPECT_WARDS_MIN))
    ward_super = {w["properties"]["SUPER_FIPS"] for w in wards if w["properties"].get("SUPER_FIPS")}
    blank = sum(1 for w in wards if not w["properties"].get("SUPER_FIPS"))
    if blank:
        raise RuntimeError("%d ward(s) carry no SUPER_FIPS" % blank)

    # Trempealeau is deliberately not reconciled against the ward layer: the
    # ward layer rides the SAME county submission the district layer does, so
    # it repeats the merge (no ward there names district 15). It is the one
    # county whose witness is the county's own board page instead.
    dist_super = {f["properties"]["SUPER_FIPS"] for f in feats
                  if f["properties"]["CNTY_FIPS"] != TREMPEALEAU_FIPS}
    ward_super = {s for s in ward_super if not s.startswith(TREMPEALEAU_FIPS)}

    orphan_wards = sorted(ward_super - dist_super)
    empty_districts = sorted(dist_super - ward_super)
    if orphan_wards:
        raise RuntimeError("%d ward district-id(s) have no district polygon: %s"
                           % (len(orphan_wards), orphan_wards[:10]))
    if empty_districts:
        raise RuntimeError("%d district(s) own no ward: %s"
                           % (len(empty_districts), empty_districts[:10]))
    return len(wards)


# --- point-in-polygon mirroring index.html's even-odd test (fleet-standard copy) ---
def _point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(pt, geom):
    if geom is None:
        return False
    if geom["type"] == "Polygon":
        inside = False
        for ring in geom["coordinates"]:
            if _point_in_ring(pt, ring):
                inside = not inside
        return inside
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            inside = False
            for ring in poly:
                if _point_in_ring(pt, ring):
                    inside = not inside
            if inside:
                return True
    return False


def _bbox(geom):
    b = [1e9, 1e9, -1e9, -1e9]

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            b[0], b[1] = min(b[0], c[0]), min(b[1], c[1])
            b[2], b[3] = max(b[2], c[0]), max(b[3], c[1])
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    return b


def _model(features, key_prop):
    return [(f["properties"].get(key_prop), f["geometry"], _bbox(f["geometry"]))
            for f in features if f.get("geometry")]


def _districts_at(model, pt):
    hits = []
    for key, geom, bb in model:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and _point_in_geometry(pt, geom):
            hits.append(key)
    return hits


def validate(source_features, result_features, samples=10000, seed=2026):
    """Refuse the build unless simplification preserves district coverage over
    the state envelope vs the full-precision fetch — the project's 2,000
    uniform-random-point protocol.

    OVERLAPS ARE MEASURED AGAINST THE SOURCE, NOT AGAINST ZERO. The fleet's
    other boundary builders draw on TIGERweb, a single topologically clean
    national product, so they can demand a perfect mosaic. This file is 72
    county submissions stitched together, and they disagree slightly about
    where the county lines are: LTSB's own published geometry overlaps itself
    on 0.017% of its area — 24.5 km2 of that between districts in DIFFERENT
    counties (two counties' files drawing one shared boundary differently)
    and only 0.28 km2 between districts in the SAME county, the largest of
    those 8.4 acres. Demanding zero would be demanding the publisher redraw
    the state; what this build can honestly require is that SIMPLIFICATION
    make it no worse, which is what the comparison below tests."""
    src = _model(source_features, VALIDATION_KEY)
    new = _model(result_features, VALIDATION_KEY)
    rng = random.Random(seed)

    # IN-STATE sampling, not envelope sampling. The fleet's other builders
    # scatter 2,000 points over the state's bounding box, which is the right
    # test for 8 or 33 or 99 districts. Wisconsin's envelope is about twice
    # the state's area and this layer has 1,590 districts, so envelope
    # sampling puts roughly one point in every other district — enough to
    # certify a chamber, far too thin to certify this. Points are drawn until
    # `samples` of them land in some district of the FULL-PRECISION source,
    # so every sample is a point that has a real answer to get wrong. (It
    # measured the difference: envelope-2,000 reported 100.00% for every
    # retain level from 4% to 14%, while in-state-20,000 separated them at
    # 99.895 / 99.950 / 99.995.)
    pts = []
    while len(pts) < samples:
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        hits = _districts_at(src, pt)
        if hits:
            pts.append((pt, hits))

    agree = src_overlaps = new_overlaps = 0
    for pt, o_hits in pts:
        s_hits = _districts_at(new, pt)
        if len(s_hits) > 1:
            new_overlaps += 1
        if len(o_hits) > 1:
            src_overlaps += 1
        o = o_hits[0] if len(o_hits) == 1 else "MULTI"
        s = s_hits[0] if len(s_hits) == 1 else (None if not s_hits else "MULTI")
        if o == s:
            agree += 1
    pct = 100.0 * agree / samples
    if new_overlaps > src_overlaps:
        return False, ("simplification introduced overlap: %d/%d sample points fall in >1 "
                       "district, against %d/%d in the full-precision source"
                       % (new_overlaps, samples, src_overlaps, samples))
    if pct < 99.9:
        return False, "point-in-district agreement only %.3f%% (need >= 99.9%%)" % pct
    return True, ("%d/%d (%.3f%%) agreement over %d in-state points; %d of them sit in "
                  "overlapping districts, unchanged from the source's %d"
                  % (agree, samples, pct, samples, new_overlaps, src_overlaps))


def run_mapshaper(source_path, out_path):
    subprocess.run(
        ["npx", "-y", MAPSHAPER, source_path,
         "-simplify"] + SIMPLIFY + [
         "-o", "precision=" + PRECISION, "format=geojson", out_path],
        check=True, cwd=REPO_ROOT,
    )


def check_shipped():
    """OFFLINE: each declared dropped ring's AFTER answer, re-derived from the
    bytes this repository ships. No fetch, no simplifier, no source.

    WHY IT EXISTS SEPARATELY FROM THE BUILD-TIME GATE. That gate compares the
    full-precision source against the simplifier's output, so it can only run
    where the source is — an operator build with a 40 MB fetch, never a pull
    request. Without this, a rebuild that stopped dropping a declared ring, or
    dropped it into a DIFFERENT district, would be caught at the next operator
    build rather than by CI, and the declaration table could rot for months.

    Three blind spots, named rather than implied:
      * It cannot see an UNDECLARED drop. Only the source says which rings were
        dropped, so a new harm is the build-time gate's to catch.
      * It cannot re-derive any BEFORE answer, for the same reason. The "a reader
        used to be told X" half of every declaration rests on the build.
      * It cannot tell that a declared interior point is inside its RING — the
        ring is not in the shipped file, that being the whole point. The build
        path proves it with `point_in_ring`; here the point is only a place to
        ask the shipped geometry a question.
    """
    path = os.path.join(APP_DATA_DIR, OUT_NAME)
    with open(path) as f:
        feats = json.load(f)["features"]
    problems = []
    mod = drings.model(feats, VALIDATION_KEY)
    for d in ACCEPTED_DROPPED_RINGS:
        for key in ("lat", "lng", "m2", "verts", "interior", "features", "kind",
                    "answer_before", "answer_after", "why", "date"):
            if key not in d:
                problems.append("a declaration is missing %r" % key)
        ip = d.get("interior") or {}
        if not ip.get("lat") or not ip.get("lng"):
            problems.append("declaration at %s,%s carries no interior point"
                            % (d.get("lat"), d.get("lng")))
            continue
        if d.get("kind") not in drings.HARM_KINDS:
            problems.append("declaration at %.6f,%.6f declares kind %r, which is "
                            "not one of the harms this table is for"
                            % (d["lat"], d["lng"], d.get("kind")))
        got = list(drings.districts_at(mod, (ip["lng"], ip["lat"])))
        want = sorted((d.get("answer_after") or {}).get(LAYER_NAME, []))
        if got != want:
            problems.append(
                "at the declared interior point %.7f,%.7f the SHIPPED file answers "
                "%s; the declaration says the reader would be answered %s"
                % (ip["lat"], ip["lng"], got or ["NO DISTRICT"], want or ["NO DISTRICT"]))
    if GAP_CLOSED is None and ACCEPTED_DROPPED_RINGS:
        problems.append("GAP_CLOSED is unset, so nothing holds the number of "
                        "coverage gaps this simplification closes")
    if problems:
        print("FAIL dropped-ring declarations: %s" % "; ".join(problems),
              file=sys.stderr)
        return 1
    print("OK %d declared dropped ring(s); every AFTER answer re-derived from the "
          "shipped %d features at its own interior point; GAP_CLOSED %s"
          % (len(ACCEPTED_DROPPED_RINGS), len(feats), GAP_CLOSED), file=sys.stderr)
    return 0


def main():
    args = sys.argv[1:]
    if "--check-shipped" in args:
        sys.exit(check_shipped())
    check_only = "--check" in args

    raw = fetch_layer(DISTRICTS, "GEOID,SUPER_FIPS,SUPERID,CNTY_FIPS,CNTY_NAME")
    if len(raw) != EXPECT_DISTRICTS:
        raise RuntimeError("LTSB returned %d districts, expected %d — a county has "
                           "resubmitted; re-check the per-county seat counts before "
                           "moving this number" % (len(raw), EXPECT_DISTRICTS))
    ltsb = [f for f in normalize_ltsb(raw) if f["properties"]["CNTY_FIPS"] != TREMPEALEAU_FIPS]
    dropped = len(raw) - len(ltsb)
    feats = ltsb + trempealeau_features()

    by_county = gate_districts(feats)
    n_wards = gate_wards(feats)
    print("gates: %d districts across %d counties; numbering 1..n everywhere; "
          "%d wards reconcile with no orphans"
          % (len(feats), len(by_county), n_wards), file=sys.stderr)
    print("       Trempealeau: LTSB's %d merged districts replaced by the county's own %d"
          % (dropped, TREMPEALEAU_SEATS), file=sys.stderr)
    if check_only:
        return

    source = {"type": "FeatureCollection", "features": feats}
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "supervisory-src.geojson")
        with open(src_path, "w") as f:
            json.dump(source, f)
        out_tmp = os.path.join(tmp, "supervisory.geojson")
        run_mapshaper(src_path, out_tmp)
        with open(out_tmp) as f:
            simplified = json.load(f)

    n = len(simplified["features"])
    if n != len(feats):
        raise RuntimeError("simplify changed the feature count: %d -> %d" % (len(feats), n))

    ok, msg = validate(feats, simplified["features"])
    if not ok:
        raise RuntimeError("validation failed: %s" % msg)

    # EVERY DROPPED RING IS ANSWER-TESTED, AND THE 10,000-POINT AGREEMENT CHECK
    # ABOVE CANNOT SEE THEM. That check scatters points over the whole state, and
    # the rings this loses total a fraction of a square kilometre — 0.0222 km2 of
    # 169,635, so about 0.0013 of one expected hit. It is blind to them by
    # construction, which is why the answer test is separate rather than a
    # tightening of it.
    records, dstats = drings.classify({
        LAYER_NAME: {"source": feats, "drawn": simplified["features"],
                     "key": VALIDATION_KEY}})
    gap_closed = (dstats[drings.KIND_GAP_CLOSED] if GAP_CLOSED is None else GAP_CLOSED)
    dok, dmsg = drings.check(records, dstats, ACCEPTED_DROPPED_RINGS, gap_closed)
    print("dropped rings: %s" % dmsg, file=sys.stderr)
    if GAP_CLOSED is None:
        print("       GAP_CLOSED is unset, so the measured %d is accepted for this "
              "run; set it in this file to hold the number" % gap_closed,
              file=sys.stderr)
    if not dok:
        # THE FAILURE HANDS YOU THE TABLE RATHER THAN MAKING YOU DERIVE IT. Every
        # field below is measured on this run — the interior point especially,
        # which is carried at the precision that keeps it inside its own ring and
        # cannot be worked out by eye.
        print("\n--- measured declarations for ACCEPTED_DROPPED_RINGS ---",
              file=sys.stderr)
        print("GAP_CLOSED = %d" % dstats[drings.KIND_GAP_CLOSED], file=sys.stderr)
        for r in records:
            if not r["harm"]:
                continue
            print(json.dumps({
                "lat": round(r["centre"][1], 6), "lng": round(r["centre"][0], 6),
                "verts": r["verts"], "m2": round(r["m2"], 2),
                "interior": r["interior"], "features": r["features"],
                "kind": r["kind"],
                "answer_before": {k: v["before"] for k, v in r["answers"].items()},
                "answer_after": {k: v["after"] for k, v in r["answers"].items()},
                "sampled": r["sampled"],
            }, sort_keys=True), file=sys.stderr)
        raise RuntimeError("dropped-ring gate failed: %s" % dmsg)

    compact = json.dumps(simplified, separators=(",", ":"))
    if json.loads(compact) != simplified:
        raise RuntimeError("round-trip mismatch before writing")
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    out_path = os.path.join(APP_DATA_DIR, OUT_NAME)
    with open(out_path, "w") as f:
        f.write(compact)
    print("county-supervisory-districts -> data/app/%s: %d features; %s; %d bytes (%s, 6dp)"
          % (OUT_NAME, n, msg, len(compact), " ".join(SIMPLIFY)), file=sys.stderr)

    # WRITTEN LAST, so a sidecar on disk always describes a build that finished.
    # Only the three services THIS builder reads are pinned: a sidecar cannot
    # honestly speak for a layer its own run never fetched.
    pins = {
        "districts": layer_pin(DISTRICTS),
        "wards": layer_pin(WARDS),
        "trempealeau": layer_pin(TREMPEALEAU),
    }
    sidecar = {
        "_comment": (
            "What LTSB's and Trempealeau's services reported at the last operator "
            "build of wi/scripts/build_wi_supervisory_districts.py. "
            "validate_sources.py compares all three monthly and WARNs when any has "
            "moved. LTSB republishes each 15 January and 15 July under Wis. Stat. "
            "5.15(4)(br)1 and NAMES THE LAYER FOR THE WINDOW, so `name` is the "
            "signal that leads: it moves at the statutory moment even when the "
            "district total does not. Written by the build; never edit by hand."
        ),
        "builtOn": datetime.date.today().isoformat(),
        "name": {k: v["name"] for k, v in pins.items()},
        "dataLastEdit": {k: v["dataLastEdit"] for k, v in pins.items()},
        "rows": {k: v["rows"] for k, v in pins.items()},
    }
    os.makedirs(os.path.dirname(SIDECAR), exist_ok=True)
    with open(SIDECAR, "w") as f:
        json.dump(sidecar, f, indent=2, sort_keys=True)
        f.write("\n")
    print("       sidecar -> %s: %s"
          % (os.path.relpath(SIDECAR, REPO_ROOT),
             ", ".join("%s %s rows, %s, edited %s"
                       % (k, pins[k]["rows"], pins[k]["name"], pins[k]["dataLastEdit"])
                       for k in sorted(pins))), file=sys.stderr)


if __name__ == "__main__":
    main()
