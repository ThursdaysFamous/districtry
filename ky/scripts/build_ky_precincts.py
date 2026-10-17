#!/usr/bin/env python3
"""
Build ky/data/app/ky-precincts.json: Kentucky's 3,194 election precincts, from
the State Board of Elections' own statewide layer.

    python3 ky/scripts/build_ky_precincts.py            # fetch, check, write
    python3 ky/scripts/build_ky_precincts.py --check    # offline
    python3 ky/scripts/build_ky_precincts.py --watch    # has the layer changed?

The work is scripts/statewide_precincts.py, shared with five other states;
this file says only where Kentucky's layer is, how to read one record and what
to expect.

THE SOURCE. "Voting Precinct Boundaries in Kentucky", hosted by the Kentucky
Division of Geographic Information (ArcGIS Online owner Kentucky_DGI, item
1a5249ae49ef4d5b9b47a33bac769484). The State Board of Elections compiles it
under KRS 117.055 to 117.0557 from the precinct files each county board of
elections submits, and the item says each county's own records control where
they disagree. Its licence is CC0 1.0. Its text says it "is current through
the November 3, 2026 General Election" and does not reflect a Precinct
Establishment Order filed after that election.

PIN THE ITEM. Two other copies sit under an individual account in the same
organisation ("SBE Voting Precincts with Attributes" and
"sbe_vtd_cities_260827", both August 2026); this builder reads the
Kentucky_DGI service only.

MEASURED 2026-10-15: 3,194 records, 3,194 distinct PrecinctID, no blank name,
all 120 counties; the Census's 2020 file had 3,693, so counties have
consolidated since. The layer's records all carry one creation stamp
(2026-10-13) and one edit stamp (2026-10-15): the layer is reloaded whole, so
nothing in it says when any one county last changed its precincts, and the
fingerprint here is what notices a change.

The State Board of Elections' site does not link this layer; it was found by
searching ArcGIS Online. That is recorded as evidence for the state-publishing
ask, not as a reason to doubt the layer, which is the Board's own.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import statewide_precincts as sp  # noqa: E402

LAYER = ("https://services3.arcgis.com/ghsX9CKghMvyYjBU/arcgis/rest/services/"
         "Ky_SBE_VTD_Boundaries_WM/FeatureServer/0")
# What the item's own text says it is current through, as the card repeats
# it. Re-read the item after that election (ky/WATCH.md) and change both.
CURRENT_THROUGH = "the November 3, 2026 general election"


def read(props):
    """One record as the card reads it. PrecinctID is the state's own key
    (state + county FIPS + the county's precinct code, e.g. 21111N168)."""
    key = (props.get("PrecinctID") or "").strip()
    fips = (props.get("StCoFIPS_str") or "").strip()
    code = (props.get("PrecinctCode") or "").strip()
    if key and fips and code and key != fips + code:
        sp.fail(SPEC, "PrecinctID %r is not county %r plus code %r" % (key, fips, code))
    return {
        "key": key,
        "name": (props.get("PrecinctName") or "").strip(),
        "code": code,
        "countyFips": fips,
    }


SPEC = sp.Spec(
    tag="ky",
    label="build_ky_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/ky/)",
    out_fields="CountyName,StCoFIPS_str,PrecinctCode,PrecinctName,PrecinctID",
    expect=3194,
    expect_counties=120,
    state_bbox={"minLng": -89.62, "minLat": 36.45, "maxLng": -81.91, "maxLat": 39.2},
    read=read,
    out_file="ky-precincts.json",
    measure_field="Shape__Area",
    interval="8",  # 4 m: 14.1 MB, 3.5 MB gzipped; 8 m: 10.2 MB, 2.49 MB (2026-10-15)
    required=("key", "name", "code", "countyFips"),
    card_claims=("current through " + CURRENT_THROUGH,),
)

if __name__ == "__main__":
    sp.main(SPEC, __doc__)
