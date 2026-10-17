#!/usr/bin/env python3
"""
Build in/data/app/in-school-board-districts.json: the five districts the
Indianapolis Public Schools board is elected from, from the City of
Indianapolis's map of school board districts.

    python3 in/scripts/build_in_school_board_districts.py            # fetch, check, write
    python3 in/scripts/build_in_school_board_districts.py --check    # offline
    python3 in/scripts/build_in_school_board_districts.py --watch    # has the layer changed?

The work is scripts/published_district_layers.py, which other builders
share; this file says where Indianapolis's layer is, how to read one record
and what to expect.

WHY ONLY INDIANAPOLIS PUBLIC SCHOOLS. Indiana publishes no statewide map of
school board election districts: how each board is elected is set school
corporation by school corporation (Ind. Code 20-23), and the state's school
district layers draw the corporations, not their boards' districts. Measured
2026-10-16, the 2022 and 2024 certified results show about forty corporations
whose board races drew fewer votes than the corporation casts, the mark of a
seat voted on in one part of it only; Indianapolis Public Schools is the one
whose districts a government office publishes as a map. The rest are recorded
as gap in-school-board-districts.

THE SOURCE. "School Board Districts", layer 9 of the City of Indianapolis and
Marion County's OpenData_Political map service (last modified 2025-03-12 when
read). It draws 26 areas across Marion County's eleven school corporations
and carries a district number (BOARDDISTR) only where an area is a numbered
board district. Only IPS's five are election districts:

  * IPS 1 to 5, each electing one member, are read (WHERE below). The layer's
    "IPS At-Large" area is the whole corporation, whose voters elect the
    board's at-large members, and the card says the board has them.
  * LAWRENCE 1-3 AND WASHINGTON 1-3 ARE RESIDENCE DISTRICTS, NOT ELECTION
    DISTRICTS. In the 2022 and 2024 results each of their seats drew about as
    many votes as the township casts, so every voter in the township votes
    for every seat, and a member only has to live in the district. They are
    not drawn, and the empty card says so. Franklin's four areas carry no
    number and are not read either.

The layer publishes no description and no terms of use.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import published_district_layers as psb  # noqa: E402

LAYER = ("https://gis.indy.gov/server/rest/services/OpenData/OpenData_Political/"
         "MapServer/9")
WHERE = "SCHOOLDIST='IPS' AND BOARDDISTR IS NOT NULL"


def read(props):
    if (props.get("SCHOOLDIST") or "").strip() != "IPS":
        psb.fail(SPEC, "a record outside IPS came through the filter: %r" % props)
    district = props.get("BOARDDISTR")
    if not isinstance(district, int) or not 1 <= district <= 5:
        psb.fail(SPEC, "BOARDDISTR %r is not 1 to 5: %r" % (district, props))
    label = (props.get("BRDDISTRIC") or "").strip()
    if label != "School Board District IPS %d" % district:
        psb.fail(SPEC, "district %d is labelled %r on the layer" % (district, label))
    return {"key": "ips-%d" % district, "board": "Indianapolis Public Schools",
            "label": "District %d" % district}


SPEC = psb.Spec(
    tag="in",
    label="build_in_school_board_districts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/in/)",
    out_fields="SCHOOLDIST,BOARDDISTR,BRDDISTRIC",
    expect=5,
    expect_groups=1,
    read=read,
    out_file="in-school-board-districts.json",
    interval="4",
    pace=2.0,
    where=WHERE,
    measure_field="SHAPE.STArea()",
    card_claims=(
        "The voters of this district elect one member",
        "Lawrence and Washington",
    ),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
