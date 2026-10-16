#!/usr/bin/env python3
"""
Build sc/data/app/sc-precincts.json: South Carolina's 2,315 election
precincts, from the official maps the Revenue and Fiscal Affairs Office keeps.

    python3 sc/scripts/build_sc_precincts.py            # fetch, check, write
    python3 sc/scripts/build_sc_precincts.py --check    # offline
    python3 sc/scripts/build_sc_precincts.py --watch    # has the layer changed?

The work is scripts/statewide_precincts.py, shared with five other states;
this file says only where South Carolina's layer is, how to read one record
and what to expect.

THE SOURCE. The Revenue and Fiscal Affairs Office's "Voter Precincts" layer
(item bdf73dfd307e420a92c261659279c7b1). In South Carolina a precinct's lines
are set by an act of the General Assembly (Title 7, Chapter 7 of the Code),
and RFA keeps the official maps, so every record carries the act that set it
and the date it took effect; the card prints both. A county whose act is old
has not had its lines changed by law since, which is not the same as a stale
record. No licence is named, only an as-is disclaimer.

THE COUNTY IS NOT A FIELD. It is read out of the map number, P-<county
code>-<year>, where five counties add a letter after the year (P-83-23A is
Spartanburg); all 46 odd county codes 01 to 91 appear (measured 2026-10-15).

WHAT THE LAYER SAYS THAT THE CARD DOES NOT TRUST. RFA's page and its service
name different map numbers for Beaufort, Greenville and Sumter, and
Beaufort's records cite 2026 Act No. 118 (H.5089) beside a bill link to
H.4350. The card prints the act number and the effective date and no bill
link, because the two can disagree. One precinct code repeats inside a
county (Beaufort 310, on "Bluffton 4F" and "Bluffton 4A"), so the key here is
the county, the code and the name together. One precinct has no code at all:
Aiken's "SRS", the Savannah River Site, so a code is not required.

Each record also names its county's voter registration and elections office
page, and the card links it, which is the one office this layer publishes.
"""

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import statewide_precincts as sp  # noqa: E402

LAYER = ("https://gis.state.sc.us/arcgis/rest/services/Boundaries_Districts/"
         "Voter_Precincts/FeatureServer/0")


def read(props):
    mapnum = (props.get("CodeMapNum") or "").strip()
    m = re.fullmatch(r"P-(\d{2})-(\d{2}[A-Z]?)", mapnum)
    if not m:
        sp.fail(SPEC, "map number %r is not P-<county>-<year>: %r" % (mapnum, props))
    fips = "45%03d" % int(m.group(1))
    code = (props.get("PCode") or "").strip()
    name = (props.get("PName") or "").strip()
    effective = props.get("EffectiveDate")
    if effective is not None:
        effective = datetime.datetime.fromtimestamp(
            effective / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%d")
    act = re.sub(r"\s+", " ", (props.get("ActNumber") or "").strip()) or None
    office = (props.get("Local_Voter_Reg") or "").strip() or None
    if office and not office.startswith("https://") and not office.startswith("http://"):
        office = None
    out = {
        "key": "%s-%s-%s" % (fips, code, name),
        "name": name,
        "countyFips": fips,
    }
    if code:
        out["code"] = code
    if act:
        out["act"] = act
    if effective:
        out["effective"] = effective
    if office:
        out["office"] = office
    return out


SPEC = sp.Spec(
    tag="sc",
    label="build_sc_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/sc/)",
    out_fields="PName,PCode,CodeMapNum,ActNumber,EffectiveDate,Local_Voter_Reg",
    expect=2315,
    expect_counties=46,
    state_bbox={"minLng": -83.36, "minLat": 31.99, "maxLng": -78.49, "maxLat": 35.22},
    read=read,
    out_file="sc-precincts.json",
    pace=1.0,
    measure_field="Shape__Area",
    interval="8",  # 4 m: 2.95 MB gzipped; 8 m: 7.8 MB, 2.24 MB (2026-10-15)
    required=("key", "name", "countyFips"),
)

if __name__ == "__main__":
    sp.main(SPEC, __doc__)
