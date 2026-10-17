#!/usr/bin/env python3
"""
Build tn/data/app/tn-school-board-districts.json: the districts eighteen
Tennessee county school boards are elected from, from the Comptroller of the
Treasury's map of them.

    python3 tn/scripts/build_tn_school_board_districts.py            # fetch, check, write
    python3 tn/scripts/build_tn_school_board_districts.py --check    # offline
    python3 tn/scripts/build_tn_school_board_districts.py --watch    # has the layer changed?

The work is scripts/published_district_layers.py, which other builders
share; this file says where Tennessee's layer is, how to read one record and
what to expect.

THE SOURCE. "School Board Districts New", layer 5 of the Comptroller's
Redistricting_Address_Lookup service (item 8ad9190272dc44eaa2c81e146b8d20c8),
the map behind its address lookup for the districts drawn after the 2020
Census. A county board of education is elected from districts of
substantially equal population (Tenn. Code Ann. 49-2-201, as quoted in
Bradley County's private act on the County Technical Assistance Service's
site; the code itself is published by LexisNexis behind pages that show no
text without a browser's scripts). The layer publishes no description and no
terms. Its edit date was 2026-09-10 when read on 2026-10-16.

WHAT IT HOLDS. Measured 2026-10-16: 115 records, which are 114 districts on
the boards of eighteen counties (COUNTIES below) and one record with no county
and no shape, which is skipped and declared. No other county, and no city or
special school district, is on it. Each record carries only its county and its
district number:

  * TWO SPELLINGS OF A COUNTY CODE. Crockett and Henry each appear under a
    three-digit code ("033", "079") for some districts and a two-digit one
    ("33", "79") for the rest; read together they number Crockett's districts
    1 to 12 and Henry's 1 to 5 with none twice. Codes are padded to three
    digits before anything else reads them.
  * THE MAP DOES NOT SAY HOW MANY MEMBERS A DISTRICT ELECTS. Five counties
    draw only three or four districts (Fayette, Hardeman, Johnson and
    Washington three, Jefferson four), which points to districts electing
    several members each, so the card claims no number and says a district may
    elect more than one.
  * SHELBY COUNTY'S DISTRICTS LEAVE OUT THE SIX TOWNS THAT RUN THEIR OWN
    SCHOOL DISTRICTS. The build checks a point in each of Arlington, Bartlett,
    Collierville, Germantown, Lakeland and Millington falls in no district,
    and the card says the map leaves them out.

County names come from the app's own county map (data/app/state-counties.json),
so the card and the County layer cannot name a county two ways.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))

import published_district_layers as psb  # noqa: E402

LAYER = ("https://services2.arcgis.com/63Ka7QbNqm4NLbeo/arcgis/rest/services/"
         "Redistricting_Address_Lookup/FeatureServer/5")

# The eighteen counties on the map (three-digit FIPS) and their district counts.
COUNTIES = {
    "009": 7, "023": 6, "025": 7, "033": 12, "037": 9, "047": 3, "069": 3,
    "079": 5, "089": 4, "091": 3, "099": 9, "111": 5, "113": 6, "155": 5,
    "157": 9, "165": 11, "179": 3, "189": 7,
}


def county_names():
    path = os.path.join(HERE, "..", "data", "app", "state-counties.json")
    with open(path, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    return {f["properties"]["GEOID"][2:]: f["properties"]["BASENAME"] for f in feats}


NAMES = county_names()
# the card names every county on the map, in this order
COUNTY_LIST = sorted(NAMES[c] for c in COUNTIES)
COUNTY_SENTENCE = ", ".join(COUNTY_LIST[:-1]) + " and " + COUNTY_LIST[-1]


def read(props):
    raw = props.get("COUNTY")
    county = str(raw).strip() if raw is not None else ""
    district = str(props.get("NEWSBDDISTRICT") or "").strip()
    if not county:
        return None
    if not county.isdigit() or len(county) > 3:
        psb.fail(SPEC, "COUNTY %r is not a county code: %r" % (raw, props))
    county = county.zfill(3)
    if county not in COUNTIES:
        psb.fail(SPEC, "county %s is not one of the eighteen on the map: read the layer, "
                 "then add it to COUNTIES and the card's list together" % county)
    if not district.isdigit():
        psb.fail(SPEC, "NEWSBDDISTRICT %r is not a number: %r" % (district, props))
    return {"key": "47%s-%s" % (county, district), "board": NAMES[county] + " County",
            "label": "District " + district, "countyFips": "47" + county}


def extra_check(feats):
    per = {}
    for f in feats:
        p = f["properties"]
        per.setdefault(p["countyFips"][2:], set()).add(int(p["label"].split()[-1]))
    for county, n in sorted(COUNTIES.items()):
        if per.get(county) != set(range(1, n + 1)):
            psb.fail(SPEC, "%s County's districts are %s, and COUNTIES says 1 to %d"
                     % (NAMES[county], sorted(per.get(county) or ()), n))


SPEC = psb.Spec(
    tag="tn",
    label="build_tn_school_board_districts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/tn/)",
    out_fields="COUNTY,NEWSBDDISTRICT",
    expect=sum(COUNTIES.values()),
    expect_groups=len(COUNTIES),
    read=read,
    out_file="tn-school-board-districts.json",
    interval="4",
    pace=2.0,
    measure_field="Shape__Area",
    skipped_records=1,
    extra_check=extra_check,
    card_claims=(
        COUNTY_SENTENCE,
        "Arlington, Bartlett, Collierville, Germantown, Lakeland and Millington",
        "A district may elect more than one member",
    ),
    outside=(
        (-89.8101, 35.0868, "Germantown runs its own school district"),
        (-89.6645, 35.0420, "Collierville runs its own school district"),
        (-89.8740, 35.2045, "Bartlett runs its own school district"),
        (-89.8973, 35.3415, "Millington runs its own school district"),
        (-89.6615, 35.2962, "Arlington runs its own school district"),
        (-89.7406, 35.2306, "Lakeland runs its own school district"),
    ),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
