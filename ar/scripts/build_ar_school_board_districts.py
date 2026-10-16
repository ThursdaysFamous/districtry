#!/usr/bin/env python3
"""
Build ar/data/app/ar-school-board-zones.json: the zones Arkansas school boards
are elected from, from the Arkansas GIS Office's statewide layer of them.

    python3 ar/scripts/build_ar_school_board_districts.py            # fetch, check, write
    python3 ar/scripts/build_ar_school_board_districts.py --check    # offline
    python3 ar/scripts/build_ar_school_board_districts.py --watch    # has the layer changed?

The work is scripts/published_school_board_districts.py, shared with three
other states; this file says where Arkansas's layer is, how to read one record
and what to expect.

THE SOURCE. SCHOOL_BOARD_ZONES, layer 32 of the GIS Office's Boundaries
service. Its description says the Secretary of State compiles it "to aid in
election administration and future redistricting", and that "Some School
Districts in Arkansas Elect Members at Large which is the reason not all school
districts are included in the data". It credits the "AR Secretary of State"
and is provided "as is"; nothing in it grants or withholds reuse. Layer 56 of
the same service, SCHOOL_BOARD_ZONES_2011, is the previous decade's zones and
is not read.

WHAT IT HOLDS. Measured 2026-10-16: 966 records for 965 zones on 176 of the
state's 234 school districts (the TIGER count the School District card draws).
The zone's number is printed as published, which is how the board numbers its
positions: Gurdon's zones are numbered 8 to 14.

  * ONE ZONE IN TWO PIECES. Jasper's zone 3 is two records with the same
    population, 57 km2 and 5 km2, and is joined into one zone. Jasper has no
    zone 1 on the map; nothing in the layer says why, so the card says nothing
    about it.
  * TWO DISTRICTS WITH NO NAME. Cotter (LEA 0302000) and Cedarville (LEA
    1702000) carry an empty name. Their names come from the same service's
    school district layer (layer 29, PUB_SCHOOL_DISTRICTS, read 2026-10-16),
    in NAMES below. The build fails if either is ever named in the zone layer
    itself, so the table goes when it stops being needed.
  * TWO DISTRICTS WITH ONE NAME. Two districts are called Harmony Grove (LEA
    5205000 and 6304000), and a board named twice would be one board to every
    count below, so each takes its county in brackets (SAME_NAME below). The
    county is the one the LEA code numbers in its first two digits, where
    Arkansas numbers its counties alphabetically (52 Ouachita, 63 Saline);
    measured 2026-10-16 against the zones' own location, 6304000's zones all
    lie in Saline County and 5205000's in Ouachita County and Dallas County,
    whose bracket names only Ouachita, the county the district is numbered in.
    The build fails if any other name is shared, or if either stops being.
  * EIGHT BOARDS PART WAY TO AT LARGE. Act 424 of 2023 let a board return to
    electing every member at large. The GIS Office's notes of 9 April 2026
    (gis.arkansas.gov/2026/04/09/date-update-school-board-zones/, read through
    the Internet Archive's copy of 13 May 2026; the page itself now redirects)
    list twelve boards that resolved to do so. Four are wholly at large and
    gone from the layer (Eureka Springs, Fouke, Mena, Mulberry/Pleasant View).
    The other eight are converting seat by seat as terms end, and the layer
    keeps only the zones whose terms had not ended. TRANSITION below holds each
    board's resolution date and the zones it keeps, and the build fails when
    the layer's zones for one of them change, so the card's sentence about that
    board is re-read whenever the map moves.

PACING. gis.arkansas.gov publishes no robots.txt (the address answers with a
web page, which permits every path), and the same office's open-data host asks
for 60 seconds between requests, which this builder honours as the instance's
other builders do. The layer answers 200 records a request.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import published_school_board_districts as psb  # noqa: E402

LAYER = ("https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/"
         "Boundaries/FeatureServer/32")

# LEA -> name, from layer 29 of the same service (PUB_SCHOOL_DISTRICTS), for the
# two districts the zone layer leaves unnamed.
NAMES = {"0302000": "Cotter", "1702000": "Cedarville"}

# LEA -> the county a district shares its name with another in, taken from the
# LEA code's first two digits (Arkansas's counties numbered alphabetically).
SAME_NAME = {"5205000": "Ouachita County", "6304000": "Saline County"}

# LEA -> (name, zones still on the map, resolution date, what the resolution
# says), from the GIS Office's notes of 9 April 2026. "seat-by-seat" boards are
# moving every seat to at large as its term ends; Decatur's resolution names
# only its Positions 1 to 3, formerly Zones 1 to 3.
TRANSITION = {
    "1702000": ("Cedarville", ("3", "5"), "2024-12-17", "seat-by-seat"),
    "2402000": ("Charleston", ("3", "4"), "2025-04-28", "seat-by-seat"),
    "0302000": ("Cotter", ("1", "5"), "2023-10-19", "seat-by-seat"),
    "0402000": ("Decatur", ("4", "5"), "2025-07-22", "positions-1-3"),
    "0404000": ("Gravette", ("4", "5"), "2025-06-02", "seat-by-seat"),
    "1703000": ("Mountainburg", ("3", "4", "5"), "2024-11-18", "seat-by-seat"),
    "7206000": ("Prairie Grove", ("1", "5"), "2024-05-21", "seat-by-seat"),
    "5605000": ("Trumann", ("1", "2", "3"), "2025-09-08", "seat-by-seat"),
}

# The four boards the same notes say are now wholly at large; none may appear.
WHOLLY_AT_LARGE = ("Eureka Springs", "Fouke", "Mena", "Mulberry/Pleasant View")

_named_from_table = set()


def read(props):
    lea = (props.get("lea") or "").strip()
    if len(lea) != 7 or not lea.isdigit():
        psb.fail(SPEC, "lea %r is not a seven-digit LEA code: %r" % (lea, props))
    zone = str(props.get("zone") or "").strip()
    if not zone.isdigit():
        psb.fail(SPEC, "zone %r is not a number: %r" % (zone, props))
    name = (props.get("name") or "").strip()
    if not name:
        if lea not in NAMES:
            psb.fail(SPEC, "LEA %s has no name in the zone layer and none in NAMES: read "
                     "layer 29 for it" % lea)
        name = NAMES[lea]
        _named_from_table.add(lea)
    elif lea in NAMES:
        psb.fail(SPEC, "the zone layer now names LEA %s (%r); remove it from NAMES" % (lea, name))
    board = name + " School District"
    if lea in SAME_NAME:
        board += " (%s)" % SAME_NAME[lea]
    out = {"key": "%s-%s" % (lea, zone), "board": board, "label": "Zone " + zone}
    if lea in TRANSITION:
        out["atLargeSince"] = TRANSITION[lea][2]
        out["atLargeHow"] = TRANSITION[lea][3]
    return out


def extra_check(feats):
    zones = {}
    leas_by_name = {}
    for f in feats:
        p = f["properties"]
        lea = p["key"].split("-")[0]
        name = p["board"].split(" (")[0][:-len(" School District")]
        zones.setdefault(lea, set()).add(p["label"][len("Zone "):])
        leas_by_name.setdefault(name, set()).add(lea)
        if name in WHOLLY_AT_LARGE:
            psb.fail(SPEC, "%s is on the map, and the GIS Office's notes say it is wholly at "
                     "large: re-read them" % p["board"])
    for lea, (name, kept, _when, _how) in sorted(TRANSITION.items()):
        if zones.get(lea) != set(kept):
            psb.fail(SPEC, "%s (LEA %s) has zones %s on the map, and TRANSITION says %s. The "
                     "GIS Office has moved its zones: re-read its notes, then change the entry "
                     "and the card's sentence together"
                     % (name, lea, sorted(zones.get(lea) or ()), list(kept)))
    shared = set()
    for name, leas in sorted(leas_by_name.items()):
        if len(leas) > 1:
            shared |= leas
            if not leas <= set(SAME_NAME):
                psb.fail(SPEC, "%s names LEAs %s, and SAME_NAME does not tell them apart: add "
                         "each with the county its LEA code numbers" % (name, sorted(leas)))
    if shared != set(SAME_NAME):
        psb.fail(SPEC, "SAME_NAME lists %s and only %s share a name on the layer; remove the rest"
                 % (sorted(SAME_NAME), sorted(shared)))
    if _named_from_table and _named_from_table != set(NAMES):
        psb.fail(SPEC, "NAMES lists %s and the layer leaves unnamed only %s; remove the rest"
                 % (sorted(NAMES), sorted(_named_from_table)))


SPEC = psb.Spec(
    tag="ar",
    label="build_ar_school_board_districts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/ar/)",
    out_fields="lea,name,zone",
    expect=965,
    expect_boards=176,
    read=read,
    out_file="ar-school-board-zones.json",
    interval="4",
    pace=60.0,
    page=200,
    measure_field="Shape__Area",
    multipart_records=1,
    extra_check=extra_check,
    card_claims=(
        "Some School Districts in Arkansas Elect Members at Large",
        "elected from this zone",
    ),
    inside=(),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
