#!/usr/bin/env python3
"""
Build data/app/<slug>-county-outline.json — the coverage outline a county's
dispatch entries test against (docs/EXPANSION_GUIDE.md §3.5 step 1).

Why this exists: the seven metro counties' outlines were each produced by a
one-off run, so the first thing a new county needed was a procedure nobody had
written down. This makes step 1 of the county-N+1 checklist reproducible — and
reuses build_metro_outline.py's TIGERweb fetch, Douglas-Peucker simplify and
point-in-rings test rather than forking them, so a county outline and the metro
outline can never disagree about what a boundary is.

The outline is a coverage TEST, not a drawn boundary: `<county>CountyCoverage`
asks "is this point in the county", so vertex-exact fidelity buys nothing and
costs bytes on every first toggle. Simplification is the same 25 m tolerance the
metro outline uses. What IS load-bearing is that the result still answers
correctly near the edge, so every build validates against anchors — points that
must be inside and points just across each neighbouring county line that must be
outside — and refuses to write when any of them lands wrong.

Usage:
    python3 scripts/build_county_outline.py lasalle kankakee
    python3 scripts/build_county_outline.py --check lasalle   # verify, write nothing
    python3 scripts/build_county_outline.py --list            # known counties
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from build_metro_outline import (  # noqa: E402  (shared machinery — do not fork)
    DISPATCH_COUNTY_FIPS, HEADERS, REQUEST_TIMEOUT, SIMPLIFY_TOLERANCE_M,
    STATE_FIPS, TIGERWEB, point_in_rings, rings_of, simplify,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

# county slug -> FIPS, display name, and the anchors that prove the built ring
# still answers correctly. `inside` points sit well within the county; `outside`
# points sit just across a line the outline must not swallow — each names the
# neighbour it belongs to, so a failure says which edge moved.
COUNTIES = {
    "lasalle": {
        "fips": "099",
        "name": "LaSalle County",
        "inside": [
            (41.3517, -88.8454, "Ottawa (county seat)"),
            (41.1206, -88.8351, "Streator"),
            (41.3273, -89.1290, "Peru"),
            (41.5473, -89.1176, "Mendota"),
        ],
        "outside": [
            (41.4295, -88.2120, "Morris — Grundy County"),
            (41.3670, -89.4640, "Princeton — Bureau County"),
            (41.7606, -88.8570, "DeKalb County"),
            (40.7480, -88.6320, "Pontiac — Livingston County"),
        ],
    },
    # Boone and Grundy: both border-ring counties (the ring is Boone, DeKalb,
    # Grundy, Kankakee, LaSalle). Anchor coordinates geocoded, not recalled.
    "boone": {
        "fips": "007",
        "name": "Boone County",
        "inside": [
            (42.2580, -88.8417, "Belvidere (county seat)"),
            (42.3684, -88.8220, "Poplar Grove"),
            (42.3994, -88.7406, "Capron"),
        ],
        "outside": [
            (42.2714, -89.0940, "Rockford — Winnebago County"),
            (42.2501, -88.6081, "Marengo — McHenry County"),
            (42.0972, -88.6929, "Genoa — DeKalb County"),
        ],
    },
    "grundy": {
        "fips": "063",
        "name": "Grundy County",
        "inside": [
            (41.3574, -88.4215, "Morris (county seat)"),
            (41.2878, -88.2855, "Coal City"),
            (41.4553, -88.2617, "Minooka"),
        ],
        "outside": [
            (41.0945, -88.4251, "Dwight — Livingston County"),
            (41.3107, -88.6091, "Seneca — LaSalle County"),
            (41.1254, -87.8487, "Kankakee — Kankakee County"),
        ],
    },
    "kankakee": {
        "fips": "091",
        "name": "Kankakee County",
        # Coordinates verified by geocoding each place rather than recalled — the
        # first draft put "Herscher" a full county south of the real town and the
        # anchor check caught it, which is exactly what it is for.
        "inside": [
            (41.1254, -87.8487, "Kankakee (county seat)"),
            (41.2502, -87.8326, "Manteno"),
            (41.1647, -87.6625, "Momence"),
            (41.0495, -88.0962, "Herscher"),
        ],
        "outside": [
            (41.3328, -87.7898, "Peotone — Will County"),
            (40.7761, -87.7364, "Watseka — Iroquois County"),
            (41.1600, -87.4400, "Newton County, Indiana"),
            (41.0100, -88.2900, "Livingston County"),
        ],
    },
    # Research pass 4 — the first counties that are NOT contiguous with the metro.
    # Every anchor below was geocoded and its returned county/state read back, not
    # recalled; the "Madison County" and "St. Clair County" names each exist in
    # several states, and DeKalb already showed how far a same-name trap can get.
    "winnebago": {
        "fips": "201",
        "name": "Winnebago County",
        "inside": [
            (42.2714, -89.0940, "Rockford (county seat)"),
            (42.3200, -89.0582, "Loves Park"),
            (42.4931, -89.0368, "South Beloit"),
            (42.3139, -89.3594, "Pecatonica"),
        ],
        "outside": [
            (42.2580, -88.8417, "Belvidere — Boone County"),
            (42.1270, -89.2557, "Byron — Ogle County"),
            (42.2967, -89.6212, "Freeport — Stephenson County"),
            (42.5083, -89.0318, "Beloit — Rock County, Wisconsin"),
        ],
    },
    # The first bridge county toward the Metro East. It publishes no GIS at all,
    # so its board districts are built from TIGER townships
    # (build_livingston_board_districts.py); this outline is still a plain TIGER
    # county boundary like every other, and gates the dispatch entry.
    "livingston": {
        "fips": "105",
        "name": "Livingston County",
        "inside": [
            (40.8809, -88.6298, "Pontiac (county seat)"),
            (41.0945, -88.4251, "Dwight"),
            (40.7473, -88.5148, "Fairbury"),
            (40.8781, -88.8612, "Flanagan"),
        ],
        "outside": [
            (41.1206, -88.8351, "Streator — LaSalle County"),
            (41.3574, -88.4215, "Morris — Grundy County"),
            (41.1254, -87.8487, "Kankakee — Kankakee County"),
            (40.4842, -88.9937, "Bloomington — McLean County"),
        ],
    },
    "mclean": {
        "fips": "113",
        "name": "McLean County",
        "inside": [
            (40.4798, -88.9939, "Bloomington (county seat)"),
            (40.5093, -88.9844, "Normal"),
            (40.6414, -88.7834, "Lexington"),
            (40.3520, -88.7642, "Le Roy"),
        ],
        "outside": [
            (40.8809, -88.6298, "Pontiac — Livingston County"),
            (40.1526, -88.9607, "Clinton — DeWitt County"),
            (40.1481, -89.3637, "Lincoln — Logan County"),
            (40.4653, -88.3759, "Gibson City — Ford County"),
            (40.7213, -89.2727, "Eureka — Woodford County"),
        ],
    },
    "logan": {
        "fips": "107",
        "name": "Logan County",
        "inside": [
            (40.1481, -89.3637, "Lincoln (county seat)"),
            (40.0109, -89.2823, "Mount Pulaski"),
            (40.2597, -89.2332, "Atlanta"),
            (40.0207, -89.4822, "Elkhart"),
        ],
        "outside": [
            (40.4798, -88.9939, "Bloomington — McLean County"),
            (40.0117, -89.8482, "Petersburg — Menard County"),
            (40.3725, -89.5473, "Delavan — Tazewell County"),
            (40.1526, -88.9607, "Clinton — DeWitt County"),
            (39.5487, -89.2942, "Taylorville — Christian County"),
        ],
    },
    "sangamon": {
        "fips": "167",
        "name": "Sangamon County",
        "inside": [
            (39.7990, -89.6440, "Springfield (county seat, state capital)"),
            (39.6762, -89.7045, "Chatham"),
            (39.7495, -89.5318, "Rochester"),
            (39.5917, -89.5804, "Pawnee"),
        ],
        "outside": [
            (40.1481, -89.3637, "Lincoln — Logan County"),
            (40.0117, -89.8482, "Petersburg — Menard County"),
            (39.5487, -89.2942, "Taylorville — Christian County"),
            (39.7344, -90.2288, "Jacksonville — Morgan County"),
            (39.5009, -89.7679, "Virden — Macoupin County"),
        ],
    },
    "macoupin": {
        "fips": "117",
        "name": "Macoupin County",
        "inside": [
            (39.2798, -89.8818, "Carlinville (county seat)"),
            (39.1267, -89.8163, "Gillespie"),
            (39.0122, -89.7885, "Staunton"),
            (39.4459, -89.7782, "Girard"),
        ],
        "outside": [
            (39.7990, -89.6440, "Springfield — Sangamon County"),
            (39.1769, -89.6556, "Litchfield — Montgomery County"),
            (39.1200, -90.3284, "Jerseyville — Jersey County"),
            (38.8114, -89.9532, "Edwardsville — Madison County"),
        ],
    },
    "madison": {
        "fips": "119",
        "name": "Madison County",
        "inside": [
            (38.8114, -89.9532, "Edwardsville (county seat)"),
            (38.8909, -90.1843, "Alton"),
            (38.7014, -90.1487, "Granite City"),
            (38.7396, -89.6715, "Highland"),
        ],
        "outside": [
            (38.5136, -89.9842, "Belleville — St. Clair County"),
            (38.8923, -89.4131, "Greenville — Bond County"),
            (39.2798, -89.8818, "Carlinville — Macoupin County"),
            (39.1200, -90.3284, "Jerseyville — Jersey County"),
            (38.6254, -90.1900, "St. Louis, Missouri (across the river)"),
        ],
    },
    "st-clair": {
        "fips": "163",
        "name": "St. Clair County",
        "inside": [
            (38.5136, -89.9842, "Belleville (county seat)"),
            (38.6269, -90.1597, "East St. Louis"),
            (38.5923, -89.9112, "O'Fallon"),
            (38.4903, -89.7932, "Mascoutah"),
        ],
        "outside": [
            (38.8114, -89.9532, "Edwardsville — Madison County"),
            (38.3359, -90.1498, "Waterloo — Monroe County"),
            (38.6103, -89.3726, "Carlyle — Clinton County"),
            (38.3435, -89.3810, "Nashville — Washington County"),
            (38.6254, -90.1900, "St. Louis, Missouri (across the river)"),
        ],
    },
    # DeKalb closes the notch the ring had been wrapped around since pass 2:
    # Boone to the north, McHenry at the north-east corner, Kane to the east,
    # Kendall to the south-east and LaSalle to the south were all already served.
    # Only the western edge (Ogle, Lee) is a genuine frontier, so those two get
    # the OUTSIDE anchors that matter.
    "dekalb": {
        "fips": "037",
        "name": "DeKalb County",
        "inside": [
            (41.9889, -88.6868, "Sycamore (county seat)"),
            (41.8903, -88.7714, "DeKalb"),
            (41.6459, -88.6217, "Sandwich"),
            (42.0972, -88.6929, "Genoa"),
            (41.7717, -88.7737, "Waterman"),
        ],
        "outside": [
            (41.9239, -89.0687, "Rochelle — Ogle County"),
            (41.8425, -89.4814, "Dixon — Lee County"),
            (42.2580, -88.8417, "Belvidere — Boone County"),
            (41.8922, -88.4723, "Elburn — Kane County"),
            (41.6629, -88.5367, "Plano — Kendall County"),
            (41.5895, -88.9220, "Earlville — LaSalle County"),
            (42.2501, -88.6081, "Marengo — McHenry County"),
        ],
    },
    # Ogle joins on its eastern edge (Boone, Winnebago) and its south-east
    # (DeKalb, LaSalle). Lee, Stephenson, Carroll and Whiteside are the frontier
    # now, so those four carry the OUTSIDE anchors that matter.
    "ogle": {
        "fips": "141",
        "name": "Ogle County",
        "inside": [
            (42.0148, -89.3323, "Oregon (county seat)"),
            (41.9239, -89.0687, "Rochelle"),
            (42.1270, -89.2557, "Byron"),
            (41.9861, -89.5793, "Polo"),
            (42.0503, -89.4312, "Mount Morris"),
            (42.1262, -89.5791, "Forreston"),
        ],
        "outside": [
            (41.8425, -89.4814, "Dixon — Lee County"),
            (42.2967, -89.6212, "Freeport — Stephenson County"),
            (42.0949, -89.9777, "Mount Carroll — Carroll County"),
            (41.7883, -89.6954, "Sterling — Whiteside County"),
            (42.2714, -89.0940, "Rockford — Winnebago County"),
            (42.2580, -88.8417, "Belvidere — Boone County"),
            (41.9889, -88.6868, "Sycamore — DeKalb County"),
            (41.5473, -89.1176, "Mendota — LaSalle County"),
        ],
    },
    # Stephenson sits on the Wisconsin line; its southern and eastern neighbours
    # (Ogle, Winnebago) are served, so Carroll, Jo Daviess and the state line
    # carry the OUTSIDE anchors that matter.
    "stephenson": {
        "fips": "177",
        "name": "Stephenson County",
        "inside": [
            (42.2967, -89.6212, "Freeport (county seat)"),
            (42.3805, -89.8221, "Lena"),
            (42.4680, -89.6449, "Orangeville"),
            (42.2653, -89.8260, "Pearl City"),
            (42.4927, -89.7918, "Winslow"),
            (42.4225, -89.4137, "Davis"),
        ],
        "outside": [
            (42.2714, -89.0940, "Rockford — Winnebago County"),
            (42.1270, -89.2557, "Byron — Ogle County"),
            (42.0949, -89.9777, "Mount Carroll — Carroll County"),
            (42.4157, -90.4295, "Galena — Jo Daviess County"),
            (42.0945, -90.1568, "Savanna — Carroll County"),
        ],
    },
    # Carroll reaches the Mississippi, so its western neighbour is Iowa rather
    # than another Illinois county — the state line is the anchor that matters
    # there, and Jo Daviess, Stephenson, Ogle and Whiteside ring the rest.
    "carroll": {
        "fips": "015",
        "name": "Carroll County",
        "inside": [
            (42.0949, -89.9777, "Mount Carroll (county seat)"),
            (42.0945, -90.1568, "Savanna"),
            (42.1021, -89.8330, "Lanark"),
            (41.9589, -90.0993, "Thomson"),
            (41.9634, -89.7746, "Milledgeville"),
            (42.1547, -89.7398, "Shannon"),
        ],
        "outside": [
            (42.4157, -90.4295, "Galena — Jo Daviess County"),
            (42.2967, -89.6212, "Freeport — Stephenson County"),
            (42.0503, -89.4312, "Mount Morris — Ogle County"),
            (41.7883, -89.6954, "Sterling — Whiteside County"),
            (42.2587, -90.4231, "Bellevue, Iowa (across the Mississippi)"),
        ],
    },
    # Lee and Whiteside close the north-western frontier. Every anchor below is
    # DERIVED, not recalled: each `inside` point is the centroid of that place's
    # largest TIGER ring, tested against the county's own TIGER outline, and each
    # `outside` point is the place in the named neighbour whose centroid sits
    # nearest the shared border while testing outside this county. Anchors
    # written from memory put two Stephenson villages in the wrong townships;
    # they are computed now.
    "lee": {
        "fips": "103",
        "name": "Lee County",
        "inside": [
            (41.8493, -89.4876, "Dixon (county seat)"),
            (41.7280, -89.3784, "Amboy"),
            (41.8652, -89.2225, "Ashton"),
            (41.6870, -88.9814, "Paw Paw"),
            (41.6444, -89.2312, "Sublette"),
            (41.7966, -89.6021, "Nelson"),
        ],
        # Rochelle is NOT an inside anchor: it straddles the Ogle line and its
        # centroid falls in Ogle, which is why it appears below instead.
        "outside": [
            (41.9154, -89.0599, "Rochelle — Ogle County"),
            (41.7661, -88.8748, "Shabbona — DeKalb County"),
            (41.5858, -88.9176, "Earlville — LaSalle County"),
            (41.5558, -89.4632, "Ohio — Bureau County"),
            (41.6073, -89.6880, "Deer Grove — Whiteside County"),
        ],
    },
    # Rock Island is the first served county on the Mississippi and the first
    # whose neighbours include another STATE — the Iowa Quad Cities sit across
    # the river, outside every layer the app answers. Its outside anchors are
    # therefore Illinois-only by construction (the derivation picks places in
    # neighbouring Illinois counties); the river edge is tested by the inside
    # anchors that hug it, Andalusia and Rock Island itself.
    # Woodford: the pass-6 next-county candidate, between Peoria's metro edge
    # and the served McLean/Livingston block. Anchor coordinates geocoded, not
    # recalled; the outside anchors are its Tazewell/Peoria/Marshall/McLean
    # neighbours.
    "woodford": {
        "fips": "203",
        "name": "Woodford County",
        "inside": [
            (40.7214, -89.2723, "Eureka (county seat)"),
            (40.7903, -89.3609, "Metamora"),
            (40.7392, -89.0165, "El Paso"),
            (40.9045, -89.0343, "Minonk"),
            (40.7664, -89.4670, "Germantown Hills"),
            (40.8281, -89.5262, "Spring Bay"),
        ],
        "outside": [
            (40.6131, -89.4590, "Morton — Tazewell County"),
            (40.6936, -89.5890, "Peoria — Peoria County"),
            (41.0245, -89.4109, "Lacon — Marshall County"),
            (40.5142, -88.9906, "Normal — McLean County"),
            (40.8809, -88.6298, "Pontiac — Livingston County"),
        ],
    },
    "rock-island": {
        "fips": "161",
        "name": "Rock Island County",
        "inside": [
            (41.4852, -90.5742, "Rock Island (county seat)"),
            (41.4975, -90.4925, "Moline"),
            (41.5152, -90.4075, "East Moline"),
            (41.4430, -90.7209, "Andalusia"),
            (41.6127, -90.3308, "Port Byron"),
            (41.3310, -90.6724, "Reynolds"),
        ],
        "outside": [
            (41.7902, -90.2160, "Albany — Whiteside County"),
            (41.5048, -90.3159, "Cleveland — Henry County"),
            (41.3054, -90.4931, "Sherrard — Mercer County"),
        ],
    },
    "whiteside": {
        "fips": "195",
        "name": "Whiteside County",
        "inside": [
            (41.8090, -89.9686, "Morrison (county seat)"),
            (41.8024, -89.6993, "Sterling"),
            (41.7743, -89.6882, "Rock Falls"),
            (41.8632, -90.1557, "Fulton"),
            (41.6751, -89.9343, "Prophetstown"),
            (41.6598, -90.0783, "Erie"),
        ],
        "outside": [
            (41.9633, -89.7719, "Milledgeville — Carroll County"),
            (41.9857, -89.5812, "Polo — Ogle County"),
            (41.7966, -89.6021, "Nelson — Lee County"),
            (41.5558, -89.5920, "Walnut — Bureau County"),
            (41.5217, -89.9129, "Hooppole — Henry County"),
            (41.6101, -90.1763, "Hillsdale — Rock Island County"),
        ],
    },
    # ---- Gap-location outlines (2026-08-02) ----------------------------------
    # The three frontier counties below are NOT dispatched — no layer answers
    # in them — but each carries a recorded gap in the guidebook's gaps block,
    # and the gaps panel's location-awareness tests the pin against
    # <slug>-county-outline.json. Without an outline, a pin dropped in the one
    # county the gray wash makes most visible got told "nothing missing where
    # you clicked" — exactly wrong. These outlines exist SOLELY so those gaps
    # attach to their ground; shipping one adds no dispatch entry and no layer
    # (DISPATCH_COUNTY_FIPS is untouched, so the merge gate's county
    # accounting cannot drift from it). Inside anchors reuse coordinates
    # already verified elsewhere in this table (several served counties name
    # these towns as their OUTSIDE anchors); outside anchors reuse served
    # counties' verified inside anchors.
    "jo-daviess": {
        "fips": "085",
        "name": "Jo Daviess County",
        "inside": [
            (42.4185, -90.4253, "Galena (county seat)"),
            (42.3494, -90.0071, "Stockton"),
            (42.3172, -90.2213, "Elizabeth"),
            (42.4961, -89.9887, "Warren"),
            (42.4922, -90.6396, "East Dubuque"),
            (42.2547, -90.2790, "Hanover"),
        ],
        "outside": [
            (42.2967, -89.6212, "Freeport — Stephenson County"),
            (42.3794, -89.8223, "Lena — Stephenson County"),
            (42.0945, -90.1568, "Savanna — Carroll County"),
            (42.0949, -89.9777, "Mount Carroll — Carroll County"),
            (42.5006, -90.6646, "Dubuque — Iowa"),
        ],
    },
    # The five judicial-circuit secondaries, added 2026-08-08 when their board
    # research finally gave them gap records and the gaps panel needed an
    # outline to locate each one. Every anchor below is DERIVED, not recalled:
    # inside points are Census incorporated-place centroids tested against the
    # county's own TIGER rings, and each outside point is the nearest place in a
    # neighbouring county with that county resolved by point-in-polygon rather
    # than by its name. Jersey carries four rather than six because it has four
    # Illinois neighbours — the Mississippi and Missouri are the rest of its line.
    "bond": {
        "fips": "005",
        "name": "Bond County",
        "inside": [
            (38.8866, -89.3895, "Greenville (county seat)"),
            (38.8927, -89.5721, "Old Ripley"),
            (38.7772, -89.5645, "Pierron"),
            (38.7460, -89.2737, "Keyesport"),
            (39.0008, -89.5748, "Sorento"),
            (38.8234, -89.5394, "Pocahontas"),
        ],
        "outside": [
            (39.0291, -89.5246, "Panama — Montgomery County"),
            (38.9698, -89.6665, "New Douglas — Madison County"),
            (38.6826, -89.5536, "St. Rose — Clinton County"),
            (39.1122, -89.2137, "Bingham — Fayette County"),
            (39.0727, -89.7278, "Mount Olive — Macoupin County"),
            (38.7541, -89.0958, "Patoka — Marion County"),
        ],
    },
    "greene": {
        "fips": "061",
        "name": "Greene County",
        "inside": [
            (39.2948, -90.4062, "Carrollton (county seat)"),
            (39.2862, -90.5540, "Eldred"),
            (39.1905, -90.3512, "Kane"),
            (39.2693, -90.2066, "Rockbridge"),
            (39.4496, -90.5386, "Hillview"),
            (39.4807, -90.4868, "Wilmington"),
        ],
        "outside": [
            (39.2971, -90.6127, "Kampsville — Calhoun County"),
            (39.4597, -90.6237, "Pearl — Pike County"),
            (39.5423, -90.3303, "Manchester — Scott County"),
            (39.4777, -90.1038, "Scottville — Macoupin County"),
            (39.1087, -90.4996, "Fieldon — Jersey County"),
            (39.5818, -90.2518, "Murrayville — Morgan County"),
        ],
    },
    "jersey": {
        "fips": "083",
        "name": "Jersey County",
        "inside": [
            (39.1175, -90.3271, "Jerseyville (county seat)"),
            (39.1546, -90.1645, "Fidelity"),
            (39.1087, -90.4996, "Fieldon"),
            (39.0508, -90.3984, "Otterville"),
            (38.9541, -90.3553, "Elsah"),
            (38.9765, -90.4257, "Grafton"),
        ],
        "outside": [
            (39.0405, -90.1409, "Brighton — Macoupin County"),
            (39.2693, -90.2066, "Rockbridge — Greene County"),
            (39.1591, -90.6248, "Hardin — Calhoun County"),
            (38.9577, -90.2156, "Godfrey — Madison County"),
        ],
    },
    "morgan": {
        "fips": "137",
        "name": "Morgan County",
        "inside": [
            (39.7292, -90.2317, "Jacksonville (county seat)"),
            (39.6858, -90.3460, "Lynnville"),
            (39.8156, -90.3704, "Concord"),
            (39.6274, -90.2256, "Woodson"),
            (39.5818, -90.2518, "Murrayville"),
            (39.6205, -90.0477, "Franklin"),
        ],
        "outside": [
            (39.8805, -90.3705, "Arenzville — Cass County"),
            (39.5423, -90.3303, "Manchester — Scott County"),
            (39.4789, -89.9803, "Modesto — Macoupin County"),
            (39.7261, -89.9144, "New Berlin — Sangamon County"),
            (39.8842, -90.6587, "Versailles — Brown County"),
            (39.4841, -90.3740, "Roodhouse — Greene County"),
        ],
    },
    "scott": {
        "fips": "171",
        "name": "Scott County",
        "inside": [
            (39.6298, -90.4560, "Winchester (county seat)"),
            (39.5593, -90.4328, "Alsey"),
            (39.7535, -90.6069, "Naples"),
            (39.7191, -90.4960, "Exeter"),
            (39.7493, -90.5353, "Bluffs"),
            (39.5487, -90.4800, "Glasgow"),
        ],
        "outside": [
            (39.6288, -90.6108, "Florence — Pike County"),
            (39.7669, -90.4027, "Chapin — Morgan County"),
            (39.4841, -90.3740, "Roodhouse — Greene County"),
            (39.8842, -90.6587, "Versailles — Brown County"),
            (39.8805, -90.3705, "Arenzville — Cass County"),
            (39.4777, -90.1038, "Scottville — Macoupin County"),
        ],
    },
    "bureau": {
        "fips": "011",
        "name": "Bureau County",
        "inside": [
            (41.3853, -89.4695, "Princeton (county seat)"),
            (41.3287, -89.1998, "Spring Valley"),
            (41.5558, -89.5920, "Walnut"),
            (41.5558, -89.4632, "Ohio"),
            (41.3583, -89.7373, "Sheffield"),
            (41.2925, -89.5079, "Tiskilwa"),
        ],
        "outside": [
            (41.3273, -89.1290, "Peru — LaSalle County"),
            (41.5473, -89.1176, "Mendota — LaSalle County"),
            (41.2456, -89.9246, "Kewanee — Henry County"),
            (41.3978, -89.9070, "Annawan — Henry County"),
            (41.2542, -89.3421, "Hennepin — Putnam County"),
            (41.6073, -89.6880, "Deer Grove — Whiteside County"),
        ],
    },
    "mercer": {
        "fips": "131",
        "name": "Mercer County",
        "inside": [
            (41.2008, -90.7460, "Aledo (county seat)"),
            (41.3054, -90.4931, "Sherrard"),
            (41.2070, -90.5865, "Viola"),
            (41.1670, -91.0004, "New Boston"),
            (41.1006, -90.9401, "Keithsburg"),
            (41.2606, -90.6068, "Matherville"),
        ],
        "outside": [
            (41.4852, -90.5742, "Rock Island — Rock Island County"),
            (41.4430, -90.7209, "Andalusia — Rock Island County"),
            (40.9114, -90.6473, "Monmouth — Warren County"),
            (41.1675, -90.0432, "Galva — Henry County"),
            (41.4245, -91.0432, "Muscatine — Iowa"),
        ],
    },
    # Henry: the 28th county, closing the gap between the served Rock Island /
    # Whiteside block and the rest of the ring. Every inside anchor was
    # verified against the county's OWN PoliticalTownships_Henry layer before
    # being written down (each lands in its expected township); the outside
    # anchors are its Rock Island/Mercer/Knox/Stark/Bureau/Whiteside
    # neighbours.
    "henry": {
        "fips": "073",
        "name": "Henry County",
        "inside": [
            (41.3036, -90.1929, "Cambridge (county seat)"),
            (41.2456, -89.9246, "Kewanee"),
            (41.4489, -90.1543, "Geneseo"),
            (41.4839, -90.3468, "Colona"),
            (41.1675, -90.0432, "Galva"),
            (41.3545, -90.3815, "Orion"),
        ],
        "outside": [
            (41.5067, -90.5151, "Moline — Rock Island County"),
            (41.3054, -90.4931, "Sherrard — Mercer County"),
            (40.9478, -90.3712, "Galesburg — Knox County"),
            (41.0937, -89.8651, "Toulon — Stark County"),
            (41.3583, -89.7373, "Sheffield — Bureau County"),
            (41.6562, -90.0793, "Erie — Whiteside County"),
        ],
    },
    # Peoria and Tazewell: the pass-7 tranche-1 pair, the two largest counties
    # on the reopened frontier and adjacent to each other across the Illinois
    # River. Both reach the served ring through Woodford, which they share a
    # border with. Every anchor below was verified against TIGERweb's county
    # polygons before being written down (each lands in its stated county).
    "peoria": {
        "fips": "143",
        "name": "Peoria County",
        "inside": [
            (40.6936, -89.5890, "Peoria (county seat)"),
            (40.7509, -89.6151, "Peoria Heights"),
            (40.9223, -89.4859, "Chillicothe"),
            (40.6217, -89.6820, "Bartonville"),
            (40.9034, -89.7515, "Princeville"),
            (40.6875, -89.9145, "Elmwood"),
        ],
        "outside": [
            (40.6664, -89.5709, "East Peoria — Tazewell County"),
            (40.7889, -89.3628, "Metamora — Woodford County"),
            (40.9478, -90.3712, "Galesburg — Knox County"),
            (40.5570, -90.0393, "Canton — Fulton County"),
            (41.0937, -89.8651, "Toulon — Stark County"),
            (41.0295, -89.3628, "Lacon — Marshall County"),
        ],
    },
    "tazewell": {
        "fips": "179",
        "name": "Tazewell County",
        "inside": [
            (40.5675, -89.6407, "Pekin (county seat)"),
            (40.6664, -89.5709, "East Peoria"),
            (40.6136, -89.4595, "Morton"),
            (40.7053, -89.4090, "Washington"),
            (40.4867, -89.4245, "Delavan"),
            (40.4331, -89.6668, "Green Valley"),
        ],
        "outside": [
            (40.6936, -89.5890, "Peoria — Peoria County"),
            (40.7889, -89.3628, "Metamora — Woodford County"),
            (40.4842, -88.9937, "Bloomington — McLean County"),
            (40.1164, -89.4090, "Lincoln — Logan County"),
            (40.2461, -89.7418, "Havana — Mason County"),
            (40.5570, -90.0393, "Canton — Fulton County"),
        ],
    },
    # ---- Gap-location outlines, pass-7 frontier (2026-08-02) ----------------
    # Same purpose as the three above, for the nine counties the pass-7 sweep
    # measured as BLOCKED or partial and which no planned tranche will serve:
    # each carries a recorded gap naming exactly what its publisher would have
    # to release, and without an outline that gap cannot attach to its ground.
    # Anchors here were DERIVED, not recalled: a script read TIGERweb's own
    # Incorporated Places centroids inside each county (and inside each
    # neighbour, for the outside set) and round-tripped every coordinate
    # through a point-in-county query before it was written down.
    "christian": {
        "fips": "021",
        "name": "Christian County",
        "inside": [
            (39.5180, -89.0477, "Assumption"),
            (39.5919, -89.4258, "Bulpitt"),
            (39.6579, -89.3901, "Edinburg"),
            (39.5792, -89.4081, "Jeisyville"),
            (39.5868, -89.4165, "Kincaid"),
        ],
        "outside": [
            (39.2492, -88.8594, "Cowden — Shelby County"),
            (39.5763, -89.7440, "Auburn — Sangamon County"),
            (39.1975, -89.5322, "Butler — Montgomery County"),
            (39.9855, -88.8197, "Argenta — Macon County"),
        ],
    },
    "clinton": {
        "fips": "027",
        "name": "Clinton County",
        "inside": [
            (38.5434, -89.6172, "Albers"),
            (38.6162, -89.6088, "Aviston"),
            (38.5383, -89.4616, "Bartelso"),
            (38.6058, -89.4331, "Beckemeyer"),
            (38.6139, -89.5232, "Breese"),
        ],
        "outside": [
            (39.1122, -89.2137, "Bingham — Fayette County"),
            (38.8866, -89.3895, "Greenville — Bond County"),
            (38.7229, -88.9117, "Alma — Marion County"),
            (38.5165, -89.9900, "Belleville — St. Clair County"),
        ],
    },
    "fayette": {
        "fips": "051",
        "name": "Fayette County",
        "inside": [
            (39.1122, -89.2137, "Bingham"),
            (38.9942, -88.9553, "Brownstown"),
            (38.8301, -88.7796, "Farina"),
            (39.1457, -89.1103, "Ramsey"),
            (39.0211, -88.8507, "St. Elmo"),
        ],
        "outside": [
            (38.6858, -88.3486, "Clay City — Clay County"),
            (39.2492, -88.8594, "Cowden — Shelby County"),
            (38.8866, -89.3895, "Greenville — Bond County"),
            (39.0561, -88.7478, "Altamont — Effingham County"),
        ],
    },
    "ford": {
        "fips": "053",
        "name": "Ford County",
        "inside": [
            (40.4662, -88.2769, "Elliott"),
            (40.4664, -88.3788, "Gibson City"),
            (40.9355, -88.2363, "Kempton"),
            (40.5710, -88.2470, "Melvin"),
            (40.4563, -88.1020, "Paxton"),
        ],
        "outside": [
            (40.8783, -87.9532, "Ashkum — Iroquois County"),
            (41.0788, -87.8012, "Aroma Park — Kankakee County"),
            (40.1115, -88.3683, "Bondville — Champaign County"),
            (40.5681, -88.5385, "Anchor — McLean County"),
        ],
    },
    "macon": {
        "fips": "115",
        "name": "Macon County",
        "inside": [
            (39.9855, -88.8197, "Argenta"),
            (39.7006, -89.1185, "Blue Mound"),
            (39.8557, -88.9345, "Decatur"),
            (39.9261, -88.9641, "Forsyth"),
            (39.8429, -89.0598, "Harristown"),
        ],
        "outside": [
            (39.7993, -88.4627, "Atwood — Piatt County"),
            (39.2492, -88.8594, "Cowden — Shelby County"),
            (40.2638, -89.2309, "Atlanta — Logan County"),
            (39.5763, -89.7440, "Auburn — Sangamon County"),
            # Added when Macon gained dispatch entries (2026-08-04): the four
            # above leave three of its seven neighbours untested, and two of
            # them (Moultrie, Shelby) are the frontier Macon's arrival opens.
            # Each point was COMPUTED to lie inside the named county and clear
            # of Macon, not recalled.
            (40.0575, -88.9257, "De Witt County"),
            (39.7265, -88.8105, "Moultrie County"),
            (39.7359, -89.1455, "Christian County"),
        ],
    },
    "knox": {
        "fips": "095",
        "name": "Knox County",
        # Added 2026-08-22, when Knox's five County Board districts shipped and
        # the county stopped being one of the coverage wash's three enclaves.
        # Anchors DERIVED, not recalled: representative points of the county's
        # own municipal polygons (its GIS server's Corp Poly layer) for the
        # inside set, and of each of its seven neighbouring counties for the
        # outside set, every one checked with a point-in-county test against the
        # Census 2020 county polygon before it was written down.
        "inside": [
            (40.9468, -90.3812, "Galesburg (county seat)"),
            (40.9058, -90.2843, "Knoxville"),
            (40.8039, -90.4003, "Abingdon"),
            (41.1092, -90.3974, "Rio"),
            (40.9277, -90.0190, "Williamsfield"),
        ],
        "outside": [
            (41.3660, -90.1452, "Henry County"),
            (41.1044, -89.8116, "Stark County"),
            (40.7439, -89.7688, "Peoria County"),
            (40.4496, -90.1767, "Fulton County"),
            (40.4582, -90.6775, "McDonough County"),
            (40.8479, -90.6152, "Warren County"),
            (41.1985, -90.7509, "Mercer County"),
        ],
    },
    "schuyler": {
        "fips": "169",
        "name": "Schuyler County",
        # Added 2026-08-21, when Schuyler's seventeen precincts dispatched. This
        # county reached the ring on 2026-08-02 through the County card alone, so
        # it had no outline at all until now — the card needs no coverage test and
        # a dispatch entry does. Anchors DERIVED, not recalled: TIGERweb's
        # Incorporated Places centroids inside the county and inside each of its
        # six neighbours, every one checked with a point-in-county test before it
        # was written down.
        "inside": [
            (40.1271, -90.3730, "Browning"),
            (40.1528, -90.7733, "Camden"),
            (40.2340, -90.6223, "Littleton"),
            (40.1200, -90.5665, "Rushville (county seat)"),
        ],
        "outside": [
            (40.2279, -90.3565, "Astoria — Fulton County"),
            (40.1905, -90.1425, "Bath — Mason County"),
            (39.8805, -90.3705, "Arenzville — Cass County"),
            (40.0066, -90.8737, "Mound Station — Brown County"),
            (40.0374, -91.0662, "Camp Point — Adams County"),
            (40.4959, -90.5631, "Bardolph — McDonough County"),
        ],
    },
    "menard": {
        "fips": "129",
        "name": "Menard County",
        "inside": [
            (39.9619, -89.7216, "Athens"),
            (40.0849, -89.7405, "Greenview"),
            (40.1009, -89.9653, "Oakford"),
            (40.0143, -89.8453, "Petersburg"),
            (39.9457, -89.9366, "Tallula"),
        ],
        "outside": [
            (40.2638, -89.2309, "Atlanta — Logan County"),
            (39.5763, -89.7440, "Auburn — Sangamon County"),
            (40.1905, -90.1425, "Bath — Mason County"),
            (39.8805, -90.3705, "Arenzville — Cass County"),
        ],
    },
    "montgomery": {
        "fips": "135",
        "name": "Montgomery County",
        "inside": [
            (39.1975, -89.5322, "Butler"),
            (39.2841, -89.3029, "Coalton"),
            (39.0882, -89.3898, "Coffeen"),
            (39.0305, -89.4756, "Donnellson"),
            (39.4407, -89.6525, "Farmersville"),
        ],
        "outside": [
            (39.2492, -88.8594, "Cowden — Shelby County"),
            (39.1122, -89.2137, "Bingham — Fayette County"),
            (39.0930, -89.8023, "Benld — Macoupin County"),
            (39.5763, -89.7440, "Auburn — Sangamon County"),
        ],
    },
    # The pass-10 frontier sweep (2026-08-03): nine counties touching the served
    # ring that no earlier pass had probed. FOUR of them — Fulton, Hancock,
    # Henderson and Warren — became frontier only because McDonough shipped the
    # same day, which is the sweep's structural lesson: adding a county grows the
    # frontier rather than shrinking it. None is served; these outlines exist so
    # the Data gaps panel can place each county on the map.
    "fulton": {
        "fips": "057",
        "name": "Fulton County",
        "inside": [
            (40.3956, -90.1526, "Lewistown (county seat)"),
            (40.5581, -90.0351, "Canton"),
            (40.6975, -90.0009, "Farmington"),
            (40.2270, -90.3576, "Astoria"),
        ],
        "outside": [
            (40.4592, -90.6718, "Macomb — McDonough County"),
            (40.6936, -89.5890, "Peoria — Peoria County"),
            (40.1200, -90.5665, "Rushville — Schuyler County"),
            (40.2992, -90.0612, "Havana — Mason County"),
        ],
    },
    "hancock": {
        "fips": "067",
        "name": "Hancock County",
        "inside": [
            (40.4164, -91.1354, "Carthage (county seat)"),
            (40.5501, -91.3849, "Nauvoo"),
            (40.3956, -91.3374, "Hamilton"),
            (40.3564, -91.4346, "Warsaw"),
        ],
        "outside": [
            (40.4592, -90.6718, "Macomb — McDonough County"),
            (39.9356, -91.4098, "Quincy — Adams County"),
            (40.1200, -90.5665, "Rushville — Schuyler County"),
        ],
    },
    "henderson": {
        "fips": "071",
        "name": "Henderson County",
        "inside": [
            (40.9339, -90.9457, "Oquawka (county seat)"),
            (40.7492, -90.9107, "Stronghurst"),
            (40.8542, -90.8646, "Biggsville"),
        ],
        "outside": [
            (40.9114, -90.6473, "Monmouth — Warren County"),
            (40.4592, -90.6718, "Macomb — McDonough County"),
            (41.1997, -90.7490, "Aledo — Mercer County"),
        ],
    },
    "jackson": {
        "fips": "077",
        "name": "Jackson County",
        "inside": [
            (37.7645, -89.3348, "Murphysboro (county seat)"),
            (37.7273, -89.2168, "Carbondale"),
            (37.8878, -89.4923, "Ava"),
        ],
        "outside": [
            (37.9134, -89.8223, "Chester — Randolph County"),
            (38.0803, -89.3823, "Pinckneyville — Perry County"),
            (37.7306, -88.9331, "Marion — Williamson County"),
        ],
    },
    "jefferson": {
        "fips": "081",
        "name": "Jefferson County",
        "inside": [
            (38.3173, -88.9031, "Mount Vernon (county seat)"),
            (38.2145, -89.0393, "Waltonville"),
            (38.3273, -88.7345, "Bluford"),
        ],
        "outside": [
            (38.6270, -88.9456, "Salem — Marion County"),
            (38.0803, -89.3823, "Pinckneyville — Perry County"),
            (38.3437, -89.3812, "Nashville — Washington County"),
        ],
    },
    "marion": {
        "fips": "121",
        "name": "Marion County",
        "inside": [
            (38.6270, -88.9456, "Salem (county seat)"),
            (38.5250, -89.1334, "Centralia"),
            (38.6167, -89.0537, "Odin"),
        ],
        "outside": [
            (38.3173, -88.9031, "Mount Vernon — Jefferson County"),
            (38.3437, -89.3812, "Nashville — Washington County"),
            (38.9606, -89.0937, "Vandalia — Fayette County"),
        ],
    },
    "perry": {
        "fips": "145",
        "name": "Perry County",
        "inside": [
            (38.0803, -89.3823, "Pinckneyville (county seat)"),
            (38.0114, -89.2373, "Du Quoin"),
            (38.1370, -89.2278, "Tamaroa"),
        ],
        "outside": [
            (37.9134, -89.8223, "Chester — Randolph County"),
            (38.3437, -89.3812, "Nashville — Washington County"),
            (37.7645, -89.3348, "Murphysboro — Jackson County"),
        ],
    },
    "vermilion": {
        "fips": "183",
        "name": "Vermilion County",
        "inside": [
            (40.1245, -87.6300, "Danville (county seat)"),
            (40.4670, -87.6684, "Hoopeston"),
            (39.9773, -87.6353, "Georgetown"),
        ],
        "outside": [
            (40.7767, -87.7361, "Watseka — Iroquois County"),
            (40.4606, -88.0956, "Paxton — Ford County"),
            (40.1106, -88.2073, "Urbana — Champaign County"),
        ],
    },
    "warren": {
        "fips": "187",
        "name": "Warren County",
        "inside": [
            (40.9114, -90.6473, "Monmouth (county seat)"),
            (40.7295, -90.6626, "Roseville"),
            (40.8617, -90.7501, "Kirkwood"),
        ],
        "outside": [
            (40.4592, -90.6718, "Macomb — McDonough County"),
            (40.9478, -90.3712, "Galesburg — Knox County"),
            (40.9339, -90.9457, "Oquawka — Henderson County"),
        ],
    },
    # McDonough — pass 9, found by asking its clerk after a nine-hostname sweep
    # wrongly concluded the county had no public website. Gates its county-board
    # and county-precinct dispatch entries.
    "mcdonough": {
        "fips": "109",
        "name": "McDonough County",
        "inside": [
            (40.4592, -90.6718, "Macomb (county seat)"),
            (40.5534, -90.5065, "Bushnell"),
            (40.4295, -90.7940, "Colchester"),
            (40.5573, -90.8646, "Blandinsville"),
        ],
        "outside": [
            (40.7930, -90.6104, "Monmouth — Warren County"),
            (40.2734, -90.4051, "Rushville — Schuyler County"),
            (40.3417, -90.9968, "Carthage — Hancock County"),
            (40.6414, -90.1615, "Avon — Fulton County"),
        ],
    },
    "stark": {
        "fips": "175",
        "name": "Stark County",
        "inside": [
            (41.1772, -89.6582, "Bradford"),
            (41.1096, -89.9735, "La Fayette"),
            (41.0934, -89.8632, "Toulon"),
            (41.0638, -89.7729, "Wyoming"),
        ],
        "outside": [
            (41.4718, -89.2478, "Arlington — Bureau County"),
            (40.8038, -90.4009, "Abingdon — Knox County"),
            (41.1173, -89.3569, "Henry — Marshall County"),
            (41.1917, -90.3805, "Alpha — Henry County"),
        ],
    },
    # Champaign and Piatt: gap-location only, and the reason is LICENSING, not
    # technology. Their board districts and precincts are live and queryable on
    # the CCGISC portal proxy — and the consortium SELLS that data under signed
    # license agreements, with terms that forbid copying it, mirroring it on
    # another server, or putting it on public display. That is exactly what a
    # dispatch entry would do, so neither county is served. See the
    # champaign-piatt-ccgisc-license gap.
    "champaign": {
        "fips": "019",
        "name": "Champaign County",
        "inside": [
            (40.1115, -88.3683, "Bondville"),
            (39.9087, -87.9971, "Broadlands"),
            (40.1141, -88.2736, "Champaign"),
            (40.3158, -88.3502, "Fisher"),
            (40.3611, -88.4291, "Foosland"),
        ],
        "outside": [
            (39.7993, -88.4627, "Atwood — Piatt County"),
            (39.6833, -88.3014, "Arcola — Douglas County"),
            (39.7154, -87.9336, "Brocton — Edgar County"),
            (40.5681, -88.5385, "Anchor — McLean County"),
        ],
    },
    "piatt": {
        "fips": "147",
        "name": "Piatt County",
        "inside": [
            (39.7993, -88.4627, "Atwood"),
            (39.9230, -88.5724, "Bement"),
            (39.8892, -88.7345, "Cerro Gordo"),
            (40.0116, -88.7254, "Cisco"),
            (40.1218, -88.6435, "De Land"),
        ],
        "outside": [
            (39.6833, -88.3014, "Arcola — Douglas County"),
            (40.1115, -88.3683, "Bondville — Champaign County"),
            (40.5681, -88.5385, "Anchor — McLean County"),
            (40.1470, -88.9630, "Clinton — De Witt County"),
        ],
    },
    # Pass-7 tranche 3 (2026-08-02): the eastern full-fat add plus the two
    # COMMISSION counties, whose 3 at-large commissioners ride the county card
    # rather than a county-board dispatch entry (EXPANSION_GUIDE §1.5).
    # Anchors derived from TIGERweb Incorporated Places centroids and
    # point-verified, like the pass-7 gap-location set.
    "iroquois": {
        "fips": "075",
        "name": "Iroquois County",
        "inside": [
            (40.8783, -87.9532, "Ashkum"),
            (40.9534, -87.6547, "Beaverville"),
            (40.5973, -88.0377, "Buckley"),
            (41.0003, -87.9111, "Chebanse"),
            (40.5670, -87.8922, "Cissna Park"),
            (40.7761, -87.7364, "Watseka (county seat)"),
        ],
        "outside": [
            (41.0788, -87.8012, "Aroma Park — Kankakee County"),
            (39.9161, -87.9353, "Allerton — Vermilion County"),
            (40.4563, -88.1020, "Paxton — Ford County"),
            (41.1254, -87.8487, "Kankakee — Kankakee County"),
        ],
    },
    "monroe": {
        "fips": "133",
        "name": "Monroe County",
        "inside": [
            (38.4580, -90.2147, "Columbia"),
            (38.1644, -90.2128, "Fults"),
            (38.3051, -89.9935, "Hecker"),
            (38.2268, -90.2330, "Maeystown"),
            (38.3064, -90.2976, "Valmeyer"),
            (38.3359, -90.1498, "Waterloo (county seat)"),
        ],
        "outside": [
            (38.1838, -89.8452, "Baldwin — Randolph County"),
            (38.5165, -89.9900, "Belleville — St. Clair County"),
            (38.5136, -89.9842, "Belleville — St. Clair County (2)"),
        ],
    },
    "randolph": {
        "fips": "157",
        "name": "Randolph County",
        "inside": [
            (38.1838, -89.8452, "Baldwin"),
            (37.9199, -89.8258, "Chester (county seat)"),
            (38.1849, -89.6046, "Coulterville"),
            (38.0093, -89.9100, "Ellis Grove"),
            (38.0889, -89.9323, "Evansville"),
        ],
        "outside": [
            (38.4580, -90.2147, "Columbia — Monroe County"),
            (37.8886, -89.4964, "Ava — Jackson County"),
            (38.5165, -89.9900, "Belleville — St. Clair County"),
            (38.3913, -89.4865, "Addieville — Washington County"),
        ],
    },
    # De Witt (pass-7 tranche 4): board districts DERIVED by dissolving the
    # county's own precinct layer per the composition it prints for every board
    # member (scripts/build_dewitt_board_districts.py). Anchors derived from
    # TIGERweb place centroids and point-verified.
    "dewitt": {
        "fips": "039",
        "name": "De Witt County",
        "inside": [
            (40.1470, -88.9630, "Clinton (county seat)"),
            (40.1846, -88.7853, "De Witt"),
            (40.2480, -88.6423, "Farmer City"),
            (40.0980, -89.0862, "Kenney"),
            (40.2216, -88.9613, "Wapella"),
        ],
        "outside": [
            (39.7993, -88.4627, "Atwood — Piatt County"),
            (40.2638, -89.2309, "Atlanta — Logan County"),
            (40.5681, -88.5385, "Anchor — McLean County"),
            (39.9855, -88.8197, "Argenta — Macon County"),
        ],
    },
    # Washington (pass-7 tranche 4): board districts DERIVED as whole-township
    # dissolves per the composition the county prints under each district
    # heading (scripts/build_washington_board_districts.py). The county runs no
    # GIS at all, so nothing else about it is live.
    "washington": {
        "fips": "189",
        "name": "Washington County",
        "inside": [
            (38.3913, -89.4865, "Addieville"),
            (38.3289, -89.1893, "Ashley"),
            (38.2214, -89.2127, "Du Bois"),
            (38.4457, -89.2721, "Hoyleton"),
            (38.4386, -89.1601, "Irvington"),
        ],
        "outside": [
            (38.1838, -89.8452, "Baldwin — Randolph County"),
            (38.7229, -88.9117, "Alma — Marion County"),
            (38.5165, -89.9900, "Belleville — St. Clair County"),
            (38.5434, -89.6172, "Albers — Clinton County"),
        ],
    },
    # Cass (pass-7 tranche 4): board districts DERIVED from Census 2020 voting
    # districts per the county's own published district table
    # (scripts/build_cass_board_districts.py). Its GIS is a Beacon parcel
    # viewer with no public REST surface.
    "cass": {
        "fips": "017",
        "name": "Cass County",
        "inside": [
            (39.8805, -90.3705, "Arenzville"),
            (39.8885, -90.0079, "Ashland"),
            (39.9993, -90.4176, "Beardstown"),
            (40.0470, -90.1513, "Chandlerville"),
            (39.9524, -90.2108, "Virginia (county seat)"),
        ],
        "outside": [
            (39.5763, -89.7440, "Auburn — Sangamon County"),
            (40.0066, -90.8737, "Mound Station — Brown County"),
            (39.9619, -89.7216, "Athens — Menard County"),
            (40.1905, -90.1425, "Bath — Mason County"),
        ],
    },
    # Marshall (pass-7 tranche 4): board districts DERIVED as whole-township
    # dissolves per the composition the county prints in the DISTRICT #n
    # headings of its own board roster PDF
    # (scripts/build_marshall_board_districts.py). The county runs no public
    # GIS, so nothing else about it is live.
    "marshall": {
        "fips": "123",
        "name": "Marshall County",
        "inside": [
            (41.0228, -89.4060, "Lacon (county seat)"),
            (41.1173, -89.3569, "Henry"),
            (40.9842, -89.4571, "Hopewell"),
            (41.0044, -89.1339, "Toluca"),
            (41.0296, -89.4412, "Sparland"),
        ],
        "outside": [
            (41.2589, -89.3216, "Hennepin — Putnam County"),
            (41.0638, -89.7729, "Wyoming — Stark County"),
            (40.9158, -89.5020, "Chillicothe — Peoria County"),
            (40.8507, -89.1211, "Benson — Woodford County"),
        ],
    },
    # The pass-7 tranche-5 AT-LARGE tier. None of these four has board-district
    # geometry to ship — each elects its board countywide — so their outlines
    # exist for the coverage ring and the gaps panel, not for a dispatch entry.
    "pike": {
        "fips": "149",
        "name": "Pike County",
        "inside": [
            (39.7078, -90.7276, "Griggsville"),
            (39.6983, -91.0399, "Barry"),
            (39.7087, -91.2033, "Hull"),
            (39.6288, -90.6108, "Florence"),
            (39.7295, -90.9094, "Baylis"),
        ],
        "outside": [
            (39.8843, -91.1084, "Liberty — Adams County"),
            (39.9854, -90.7641, "Mount Sterling — Brown County"),
            (39.6298, -90.4560, "Winchester — Scott County"),
            (39.2948, -90.4062, "Carrollton — Greene County"),
            (39.1591, -90.6248, "Hardin — Calhoun County"),
        ],
    },
    "putnam": {
        "fips": "155",
        "name": "Putnam County",
        "inside": [
            (41.2589, -89.3216, "Hennepin (county seat)"),
            (41.2658, -89.2305, "Granville"),
            (41.1141, -89.1957, "Magnolia"),
            (41.1771, -89.2097, "McNabb"),
            (41.2558, -89.1817, "Standard"),
        ],
        "outside": [
            (41.2877, -89.3640, "Bureau Junction — Bureau County"),
            (41.0228, -89.4060, "Lacon — Marshall County"),
            (41.3588, -89.0738, "LaSalle — LaSalle County"),
        ],
    },
    "brown": {
        "fips": "009",
        "name": "Brown County",
        "inside": [
            (39.9854, -90.7641, "Mount Sterling (county seat)"),
            (40.0066, -90.8737, "Mound Station"),
            (40.0252, -90.6380, "Ripley"),
            (39.8842, -90.6587, "Versailles"),
        ],
        "outside": [
            (40.1200, -90.5665, "Rushville — Schuyler County"),
            (39.9524, -90.2108, "Virginia — Cass County"),
            (39.7078, -90.7276, "Griggsville — Pike County"),
            (40.0301, -90.9580, "Clayton — Adams County"),
        ],
    },
    "calhoun": {
        "fips": "013",
        "name": "Calhoun County",
        "inside": [
            (39.1591, -90.6248, "Hardin (county seat)"),
            (38.9485, -90.5891, "Brussels"),
            (39.0332, -90.6534, "Batchtown"),
            (39.2971, -90.6127, "Kampsville"),
            (39.2327, -90.7152, "Hamburg"),
        ],
        "outside": [
            (39.2862, -90.5540, "Eldred — Greene County"),
            (38.9765, -90.4257, "Grafton — Jersey County"),
            (39.6983, -91.0399, "Barry — Pike County"),
        ],
    },
    # Mason (pass-7 tranche 4): board districts DERIVED as whole-township
    # dissolves per the composition the county prints under its board roster
    # (scripts/build_mason_board_districts.py). Its only mapping surface is a
    # WTH parcel viewer with no feature service.
    "adams": {
        "fips": "001",
        "name": "Adams County",
        # Anchors derived from TIGERweb Incorporated Places centroids and
        # round-tripped through a point-in-county query, not recalled.
        "inside": [
            (39.9351, -91.3684, "Quincy (county seat)"),
            (40.0364, -91.0642, "Camp Point"),
            (39.8170, -91.2436, "Payson"),
            (40.0296, -90.9577, "Clayton"),
            (40.0882, -91.2839, "Mendon"),
        ],
        "outside": [
            (39.7296, -90.9095, "Baylis — Pike County"),
            (40.2316, -90.9498, "Augusta — Hancock County"),
            (40.0058, -90.8738, "Mound Station — Brown County"),
            (40.1521, -90.7730, "Camden — Schuyler County"),
        ],
    },
    "mason": {
        "fips": "125",
        "name": "Mason County",
        "inside": [
            (40.2950, -90.0566, "Havana (county seat)"),
            (40.4201, -89.7806, "Manito"),
            (40.2022, -89.6971, "Mason City"),
            (40.1905, -90.1425, "Bath"),
            (40.3052, -89.6048, "San Jose"),
        ],
        "outside": [
            (40.0143, -89.8453, "Petersburg — Menard County"),
            (40.1200, -90.5665, "Rushville — Schuyler County"),
            (40.5634, -90.0408, "Canton — Fulton County"),
            (40.3710, -89.5461, "Delavan — Tazewell County"),
            (40.1508, -89.3720, "Lincoln — Logan County"),
        ],
    },
    # ---- Pass-13 research sweep (2026-08-04): the 29 counties that had no gap
    # record at all, researched together after contiguity was retired as a
    # shipping gate. GAP-LOCATION outlines only — none is dispatched. Anchors
    # derived from TIGERweb Incorporated Places centroids and round-tripped
    # through a point-in-county test (EXPANSION_GUIDE §3.5.1), never recalled
    # coordinates; outside anchors are the largest place of neighbouring
    # counties. Alexander has two outside anchors, not three — its remaining
    # borders are the Mississippi and Ohio rivers, not Illinois counties.
    "alexander": {
        "fips": "003",
        "name": "Alexander County",
        "inside": [
            (37.0061, -89.1819, "Cairo (county seat)"),
            (37.2415, -89.2713, "Tamms"),
            (37.2957, -89.4869, "East Cape Girardeau"),
        ],
        "outside": [
            (37.1826, -89.0849, "Olmsted — Pulaski County"),
            (37.4612, -89.2378, "Anna — Union County"),
        ],
    },
    "clark": {
        "fips": "023",
        "name": "Clark County",
        "inside": [
            (39.3986, -87.6900, "Marshall (county seat)"),
            (39.3054, -87.9888, "Casey"),
            (39.3381, -87.8813, "Martinsville"),
        ],
        "outside": [
            (39.6148, -87.6909, "Paris — Edgar County"),
            (39.0089, -87.7333, "Robinson — Crawford County"),
            (39.2484, -88.1598, "Greenup — Cumberland County"),
        ],
    },
    "clay": {
        "fips": "025",
        "name": "Clay County",
        "inside": [
            (38.7694, -88.5069, "Louisville (county seat)"),
            (38.6688, -88.4759, "Flora"),
            (38.6858, -88.3486, "Clay City"),
        ],
        "outside": [
            (38.7285, -88.0839, "Olney — Richland County"),
            (39.1202, -88.5508, "Effingham — Effingham County"),
            (38.5224, -89.1233, "Centralia — Marion County"),
        ],
    },
    "coles": {
        "fips": "029",
        "name": "Coles County",
        "inside": [
            (39.4844, -88.1778, "Charleston (county seat)"),
            (39.4774, -88.3623, "Mattoon"),
            (39.5306, -88.0201, "Ashmore"),
        ],
        "outside": [
            (39.2484, -88.1598, "Greenup — Cumberland County"),
            (39.7967, -88.2748, "Tuscola — Douglas County"),
            (39.6148, -87.6909, "Paris — Edgar County"),
        ],
    },
    "crawford": {
        "fips": "033",
        "name": "Crawford County",
        "inside": [
            (39.0089, -87.7333, "Robinson (county seat)"),
            (39.0022, -87.9106, "Oblong"),
            (38.9968, -87.8336, "Stoy"),
        ],
        "outside": [
            (38.7263, -87.6873, "Lawrenceville — Lawrence County"),
            (39.3986, -87.6900, "Marshall — Clark County"),
            (38.9873, -88.1645, "Newton — Jasper County"),
        ],
    },
    "cumberland": {
        "fips": "035",
        "name": "Cumberland County",
        "inside": [
            (39.2728, -88.2422, "Toledo (county seat)"),
            (39.2484, -88.1598, "Greenup"),
            (39.3216, -88.4503, "Neoga"),
        ],
        "outside": [
            (39.4774, -88.3623, "Mattoon — Coles County"),
            (38.9873, -88.1645, "Newton — Jasper County"),
            (39.4098, -88.8007, "Shelbyville — Shelby County"),
        ],
    },
    "douglas": {
        "fips": "041",
        "name": "Douglas County",
        "inside": [
            (39.7967, -88.2748, "Tuscola (county seat)"),
            (39.6833, -88.3014, "Arcola"),
            (39.8645, -88.1600, "Villa Grove"),
        ],
        "outside": [
            (40.1141, -88.2736, "Champaign — Champaign County"),
            (39.5951, -88.6085, "Sullivan — Moultrie County"),
            (39.4774, -88.3623, "Mattoon — Coles County"),
        ],
    },
    "edgar": {
        "fips": "045",
        "name": "Edgar County",
        "inside": [
            (39.6148, -87.6909, "Paris (county seat)"),
            (39.5545, -87.9396, "Kansas"),
            (39.8044, -87.6749, "Chrisman"),
        ],
        "outside": [
            (39.3986, -87.6900, "Marshall — Clark County"),
            (40.1426, -87.6111, "Danville — Vermilion County"),
            (39.4774, -88.3623, "Mattoon — Coles County"),
        ],
    },
    "edwards": {
        "fips": "047",
        "name": "Edwards County",
        "inside": [
            (38.3767, -88.0579, "Albion (county seat)"),
            (38.5198, -88.0092, "West Salem"),
            (38.4449, -87.9976, "Bone Gap"),
        ],
        "outside": [
            (38.4187, -87.7694, "Mount Carmel — Wabash County"),
            (38.3798, -88.3724, "Fairfield — Wayne County"),
            (38.7285, -88.0839, "Olney — Richland County"),
        ],
    },
    "effingham": {
        "fips": "049",
        "name": "Effingham County",
        "inside": [
            (39.1202, -88.5508, "Effingham (county seat)"),
            (39.1320, -88.4796, "Teutopolis"),
            (39.0561, -88.7478, "Altamont"),
        ],
        "outside": [
            (38.6688, -88.4759, "Flora — Clay County"),
            (38.9753, -89.1117, "Vandalia — Fayette County"),
            (38.9873, -88.1645, "Newton — Jasper County"),
        ],
    },
    "franklin": {
        "fips": "055",
        "name": "Franklin County",
        "inside": [
            (38.0110, -88.9178, "Benton (county seat)"),
            (37.8997, -88.9301, "West Frankfort"),
            (37.9918, -89.0636, "North City"),
        ],
        "outside": [
            (38.0019, -89.2323, "Du Quoin — Perry County"),
            (38.0902, -88.5387, "McLeansboro — Hamilton County"),
            (37.7344, -88.9419, "Marion — Williamson County"),
        ],
    },
    "gallatin": {
        "fips": "059",
        "name": "Gallatin County",
        "inside": [
            (37.7158, -88.1865, "Shawneetown (county seat)"),
            (37.9025, -88.1279, "New Haven"),
            (37.7979, -88.2606, "Ridgway"),
        ],
        "outside": [
            (38.0862, -88.1720, "Carmi — White County"),
            (37.7375, -88.5457, "Harrisburg — Saline County"),
            (37.4240, -88.3501, "Rosiclare — Hardin County"),
        ],
    },
    "hamilton": {
        "fips": "065",
        "name": "Hamilton County",
        "inside": [
            (38.0902, -88.5387, "McLeansboro (county seat)"),
            (37.9345, -88.4624, "Broughton"),
            (38.1981, -88.6847, "Dahlgren"),
        ],
        "outside": [
            (38.0862, -88.1720, "Carmi — White County"),
            (38.0110, -88.9178, "Benton — Franklin County"),
            (37.7375, -88.5457, "Harrisburg — Saline County"),
        ],
    },
    "hardin": {
        "fips": "069",
        "name": "Hardin County",
        "inside": [
            (37.4499, -88.3051, "Elizabethtown (county seat)"),
            (37.4240, -88.3501, "Rosiclare"),
            (37.4709, -88.1659, "Cave-In-Rock"),
        ],
        "outside": [
            (37.9025, -88.1279, "New Haven — Gallatin County"),
            (37.3619, -88.4871, "Golconda — Pope County"),
            (37.7375, -88.5457, "Harrisburg — Saline County"),
        ],
    },
    "jasper": {
        "fips": "079",
        "name": "Jasper County",
        "inside": [
            (38.9873, -88.1645, "Newton (county seat)"),
            (38.9300, -88.0277, "Ste. Marie"),
            (38.9958, -88.0218, "Willow Hill"),
        ],
        "outside": [
            (39.2484, -88.1598, "Greenup — Cumberland County"),
            (38.7285, -88.0839, "Olney — Richland County"),
            (39.1202, -88.5508, "Effingham — Effingham County"),
        ],
    },
    "johnson": {
        "fips": "087",
        "name": "Johnson County",
        "inside": [
            (37.4143, -88.8870, "Vienna (county seat)"),
            (37.5610, -88.9557, "Goreville"),
            (37.4716, -88.9746, "Buncombe"),
        ],
        "outside": [
            (37.1826, -89.0849, "Olmsted — Pulaski County"),
            (37.4612, -89.2378, "Anna — Union County"),
            (37.1565, -88.7082, "Metropolis — Massac County"),
        ],
    },
    "lawrence": {
        "fips": "101",
        "name": "Lawrence County",
        "inside": [
            (38.7263, -87.6873, "Lawrenceville (county seat)"),
            (38.7196, -87.8722, "Sumner"),
            (38.7096, -87.7590, "Bridgeport"),
        ],
        "outside": [
            (39.0089, -87.7333, "Robinson — Crawford County"),
            (38.7285, -88.0839, "Olney — Richland County"),
            (38.4187, -87.7694, "Mount Carmel — Wabash County"),
        ],
    },
    "massac": {
        "fips": "127",
        "name": "Massac County",
        "inside": [
            (37.1565, -88.7082, "Metropolis (county seat)"),
            (37.1264, -88.6275, "Brookport"),
            (37.2071, -88.8447, "Joppa"),
        ],
        "outside": [
            (37.4143, -88.8870, "Vienna — Johnson County"),
            (37.3619, -88.4871, "Golconda — Pope County"),
            (37.1826, -89.0849, "Olmsted — Pulaski County"),
        ],
    },
    "moultrie": {
        "fips": "139",
        "name": "Moultrie County",
        "inside": [
            (39.5951, -88.6085, "Sullivan (county seat)"),
            (39.6444, -88.7411, "Bethany"),
            (39.5583, -88.5387, "Allenville"),
        ],
        "outside": [
            (39.7967, -88.2748, "Tuscola — Douglas County"),
            (39.4098, -88.8007, "Shelbyville — Shelby County"),
            (39.8557, -88.9345, "Decatur — Macon County"),
        ],
    },
    "pope": {
        "fips": "151",
        "name": "Pope County",
        "inside": [
            (37.3619, -88.4871, "Golconda (county seat)"),
            (37.5005, -88.5847, "Eddyville"),
        ],
        "outside": [
            (37.1565, -88.7082, "Metropolis — Massac County"),
            (37.4143, -88.8870, "Vienna — Johnson County"),
            (37.4240, -88.3501, "Rosiclare — Hardin County"),
        ],
    },
    "pulaski": {
        "fips": "153",
        "name": "Pulaski County",
        "inside": [
            (37.0853, -89.1629, "Mound City (county seat)"),
            (37.1826, -89.0849, "Olmsted"),
            (37.2777, -89.1752, "Ullin"),
        ],
        "outside": [
            (37.0061, -89.1819, "Cairo — Alexander County"),
            (37.4143, -88.8870, "Vienna — Johnson County"),
            (37.4612, -89.2378, "Anna — Union County"),
        ],
    },
    "richland": {
        "fips": "159",
        "name": "Richland County",
        "inside": [
            (38.7285, -88.0839, "Olney (county seat)"),
            (38.6974, -88.2233, "Noble"),
            (38.6512, -88.0440, "Calhoun"),
        ],
        "outside": [
            (38.6688, -88.4759, "Flora — Clay County"),
            (38.7263, -87.6873, "Lawrenceville — Lawrence County"),
            (38.3767, -88.0579, "Albion — Edwards County"),
        ],
    },
    "saline": {
        "fips": "165",
        "name": "Saline County",
        "inside": [
            (37.7375, -88.5457, "Harrisburg (county seat)"),
            (37.8113, -88.4416, "Eldorado"),
            (37.8262, -88.5304, "Raleigh"),
        ],
        "outside": [
            (38.0902, -88.5387, "McLeansboro — Hamilton County"),
            (37.9025, -88.1279, "New Haven — Gallatin County"),
            (37.7344, -88.9419, "Marion — Williamson County"),
        ],
    },
    "shelby": {
        "fips": "173",
        "name": "Shelby County",
        "inside": [
            (39.4098, -88.8007, "Shelbyville (county seat)"),
            (39.6258, -89.0214, "Moweaqua"),
            (39.3868, -88.9592, "Tower Hill"),
        ],
        "outside": [
            (39.5328, -89.2803, "Taylorville — Christian County"),
            (38.9753, -89.1117, "Vandalia — Fayette County"),
            (39.8557, -88.9345, "Decatur — Macon County"),
        ],
    },
    "union": {
        "fips": "181",
        "name": "Union County",
        "inside": [
            (37.4510, -89.2666, "Jonesboro (county seat)"),
            (37.4612, -89.2378, "Anna"),
            (37.5737, -89.3191, "Alto Pass"),
        ],
        "outside": [
            (37.4143, -88.8870, "Vienna — Johnson County"),
            (37.7223, -89.2238, "Carbondale — Jackson County"),
            (37.1826, -89.0849, "Olmsted — Pulaski County"),
        ],
    },
    "wabash": {
        "fips": "185",
        "name": "Wabash County",
        "inside": [
            (38.4187, -87.7694, "Mount Carmel (county seat)"),
            (38.3830, -87.9106, "Bellmont"),
            (38.5276, -87.7103, "Allendale"),
        ],
        "outside": [
            (38.3767, -88.0579, "Albion — Edwards County"),
            (38.7263, -87.6873, "Lawrenceville — Lawrence County"),
            (38.7285, -88.0839, "Olney — Richland County"),
        ],
    },
    "wayne": {
        "fips": "191",
        "name": "Wayne County",
        "inside": [
            (38.3798, -88.3724, "Fairfield (county seat)"),
            (38.3480, -88.5890, "Wayne City"),
            (38.3618, -88.5355, "Sims"),
        ],
        "outside": [
            (38.3767, -88.0579, "Albion — Edwards County"),
            (38.6688, -88.4759, "Flora — Clay County"),
            (38.0902, -88.5387, "McLeansboro — Hamilton County"),
        ],
    },
    "white": {
        "fips": "193",
        "name": "White County",
        "inside": [
            (38.0862, -88.1720, "Carmi (county seat)"),
            (38.2553, -87.9970, "Grayville"),
            (37.9789, -88.3279, "Norris City"),
        ],
        "outside": [
            (38.0902, -88.5387, "McLeansboro — Hamilton County"),
            (37.9025, -88.1279, "New Haven — Gallatin County"),
            (38.3798, -88.3724, "Fairfield — Wayne County"),
        ],
    },
    "williamson": {
        "fips": "199",
        "name": "Williamson County",
        "inside": [
            (37.7344, -88.9419, "Marion (county seat)"),
            (37.7983, -89.0305, "Herrin"),
            (37.7629, -89.0841, "Carterville"),
        ],
        "outside": [
            (38.0110, -88.9178, "Benton — Franklin County"),
            (37.7223, -89.2238, "Carbondale — Jackson County"),
            (37.7375, -88.5457, "Harrisburg — Saline County"),
        ],
    },
}


# The two tables must agree about what a county's FIPS is. build_metro_outline's
# DISPATCH_COUNTY_FIPS is authoritative (validate_index.py checks the app
# against it); this catches a typo here before it produces a correct-LOOKING
# outline for the wrong county — the class of error the DeKalb-Georgia near-miss
# would have been.
_CONFLICTS = sorted(
    "%s: this table says %s, DISPATCH_COUNTY_FIPS says %s"
    % (slug, spec["fips"], DISPATCH_COUNTY_FIPS[slug])
    for slug, spec in COUNTIES.items()
    if slug in DISPATCH_COUNTY_FIPS and spec["fips"] != DISPATCH_COUNTY_FIPS[slug])
assert not _CONFLICTS, "county FIPS disagree — " + "; ".join(_CONFLICTS)


def fetch_county(fips):
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s' AND COUNTY='%s'" % (STATE_FIPS, fips),
        "outFields": "NAME,GEOID",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != 1:
        raise RuntimeError("TIGERweb returned %d features for county %s, expected 1"
                           % (len(feats), fips))
    return feats[0]


def build_rings(feature):
    """Simplify every ring, keeping the multi-ring structure TIGER returned."""
    out = []
    for ring in rings_of(feature):
        s = simplify(ring, SIMPLIFY_TOLERANCE_M)
        if s[0] != s[-1]:
            s.append(s[0])
        if len(s) >= 4:
            out.append(s)
    if not out:
        raise RuntimeError("simplification produced no usable ring")
    return out


def validate(rings, cfg):
    """Anchors are checked on the SIMPLIFIED rings — the bytes that ship."""
    problems = []
    for lat, lng, label in cfg["inside"]:
        if not point_in_rings(lat, lng, rings):
            problems.append("%s should be INSIDE %s and is not" % (label, cfg["name"]))
    for lat, lng, label in cfg["outside"]:
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE %s and is not" % (label, cfg["name"]))
    return problems


def geojson_for(rings, cfg):
    geom = ({"type": "Polygon", "coordinates": rings} if len(rings) == 1
            else {"type": "MultiPolygon", "coordinates": [[r] for r in rings]})
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": cfg["name"]}, "geometry": geom}],
    }


def run(slug, check_only):
    cfg = COUNTIES[slug]
    out_path = os.path.join(APP_DATA_DIR, "%s-county-outline.json" % slug)
    rings = build_rings(fetch_county(cfg["fips"]))
    problems = validate(rings, cfg)
    if problems:
        for p in problems:
            print("  FAIL: %s" % p, file=sys.stderr)
        print("FATAL: refusing to write an outline that misplaces its anchors",
              file=sys.stderr)
        return False

    payload = json.dumps(geojson_for(rings, cfg), separators=(",", ":"))
    verts = sum(len(r) for r in rings)
    if check_only:
        if not os.path.exists(out_path):
            print("  %s: MISSING (%s)" % (slug, out_path), file=sys.stderr)
            return False
        with open(out_path) as f:
            shipped = f.read()
        if shipped != payload:
            print("  %s: shipped file differs from a fresh build (%d vs %d bytes)"
                  % (slug, len(shipped), len(payload)), file=sys.stderr)
            return False
        print("  %s: OK — matches a fresh build (%d ring(s), %d vertices, %d bytes)"
              % (slug, len(rings), verts, len(shipped)))
        return True

    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(payload)
    print("  %s -> data/app/%s-county-outline.json — %d ring(s), %d vertices, %d bytes, "
          "%d inside / %d outside anchors hold"
          % (slug, slug, len(rings), verts, len(payload),
             len(cfg["inside"]), len(cfg["outside"])))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("counties", nargs="*", help="county slugs (default: all known)")
    ap.add_argument("--check", action="store_true", help="verify shipped files, write nothing")
    ap.add_argument("--list", action="store_true", help="list known county slugs")
    args = ap.parse_args()

    if args.list:
        for slug, cfg in sorted(COUNTIES.items()):
            print("  %-10s %s (FIPS %s)" % (slug, cfg["name"], cfg["fips"]))
        return

    targets = args.counties or sorted(COUNTIES)
    unknown = [t for t in targets if t not in COUNTIES]
    if unknown:
        print("unknown county slug(s): %s; known: %s"
              % (unknown, sorted(COUNTIES)), file=sys.stderr)
        sys.exit(1)

    ok = True
    for slug in targets:
        try:
            ok = run(slug, args.check) and ok
        except Exception as e:
            print("  %s: FAILED — %s" % (slug, e), file=sys.stderr)
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
