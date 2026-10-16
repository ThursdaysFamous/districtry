#!/usr/bin/env python3
"""
Build tn/data/app/tn-precincts.json: Tennessee's 1,870 election precincts,
from the Comptroller of the Treasury's statewide layer.

    python3 tn/scripts/build_tn_precincts.py            # fetch, check, write
    python3 tn/scripts/build_tn_precincts.py --check    # offline
    python3 tn/scripts/build_tn_precincts.py --watch    # has the layer changed?

The work is scripts/statewide_precincts.py, shared with five other states;
this file says only where Tennessee's layer is, how to read one record and
what to expect.

THE SOURCE. "Voting Precincts New", layer 12 of the Comptroller's
Redistricting_Address_Lookup service (item 8ad9190272dc44eaa2c81e146b8d20c8),
which feeds the Comptroller's Voter District Lookup. The Comptroller does the
redistricting map work for the counties; each county's election commission
sets its precincts. The service states no licence and no description beyond
"Redistricting 2020", and the Comptroller's site links the lookup and its PDF
maps but not this layer. Last edited 2026-09-10 (measured 2026-10-15).

THREE THINGS IN THE LAYER ARE READ AROUND, EACH MEASURED.
  1. The county is a FIPS number written two ways ("3" and "003"), 108 raw
     values for 95 counties, so it is read as a number.
  2. Overton County's nine precincts each appear twice with the same name and
     identical geometry (1,879 records, 1,870 distinct). The shared builder
     drops a repeat only when the geometry is identical AND this file declares
     how many there are, so a tenth would stop the build.
  3. Davidson County has eight small polygons named "Precinct Created by
     Split CCD & Senate Districts" rather than a precinct. They are ground a
     reader can click, so they are kept, each keyed by its own area, and the
     card says the Comptroller's map does not name the precinct, rather than
     calling the ground part of no precinct, which would be false. "CCD" is
     not spelled out on the card: the same service carries County Commission
     District layers (2 and 3) and no census-division layer, so it most
     likely means a county commission district, which is inferred from the
     layer list, not stated by the Comptroller.

THE NAME IS PRINTED AS PUBLISHED. Counties write it in many shapes: a number
("1303"), a number and a polling place ("601 First Baptist Church"), a ward
("Rockwood Ward 1") or a place ("Parrottsville"). A name that includes a
polling place may be out of date where the polling place moved and the line
did not (inferred, not measured), so the card points to the state's polling
place lookup for where to vote.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import statewide_precincts as sp  # noqa: E402

LAYER = ("https://services2.arcgis.com/63Ka7QbNqm4NLbeo/arcgis/rest/services/"
         "Redistricting_Address_Lookup/FeatureServer/12")
UNNAMED = "Precinct Created by Split CCD & Senate Districts"
UNNAMED_EXPECTED = {"47037": 8}


def read(props):
    county = (props.get("COUNTY") or "").strip()
    if not re.fullmatch(r"\d{1,3}", county):
        sp.fail(SPEC, "COUNTY %r is not a county number: %r" % (county, props))
    fips = "47%03d" % int(county)
    name = re.sub(r"\s+", " ", (props.get("NEWVOTINGPRECINCT") or "").strip())
    out = {"name": name, "countyFips": fips}
    if name == UNNAMED:
        area = props.get("Shape__Area")
        if area is None:
            sp.fail(SPEC, "an unnamed piece in county %s carries no area to key it by" % fips)
        out["key"] = "%s-unnamed-%d" % (fips, int(round(float(area))))
        out["unnamed"] = True
    else:
        out["key"] = "%s-%s" % (fips, name)
    return out


def check_unnamed(feats):
    seen = {}
    for f in feats:
        if f["properties"].get("unnamed"):
            seen[f["properties"]["countyFips"]] = seen.get(f["properties"]["countyFips"], 0) + 1
    if seen != UNNAMED_EXPECTED:
        sp.fail(SPEC, "unnamed pieces by county %r, expected %r — read the layer before "
                "changing UNNAMED_EXPECTED" % (seen, UNNAMED_EXPECTED))


SPEC = sp.Spec(
    tag="tn",
    label="build_tn_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/tn/)",
    out_fields="COUNTY,NEWVOTINGPRECINCT",
    expect=1870,
    expect_counties=95,
    state_bbox={"minLng": -90.32, "minLat": 34.98, "maxLng": -81.64, "maxLat": 36.68},
    read=read,
    out_file="tn-precincts.json",
    pace=1.0,
    measure_field="Shape__Area",
    identical_duplicates=9,
    interval="8",  # 4 m: 3.50 MB gzipped; 8 m: 9.4 MB, 2.45 MB (2026-10-15)
    extra_check=check_unnamed,
)

if __name__ == "__main__":
    sp.main(SPEC, __doc__)
