#!/usr/bin/env python3
"""
Build ar/data/app/ar-precincts.json: Arkansas's 2,920 election precincts, from
the Arkansas GIS Office's statewide layer of what each county reports.

    python3 ar/scripts/build_ar_precincts.py            # fetch, check, write
    python3 ar/scripts/build_ar_precincts.py --check    # offline
    python3 ar/scripts/build_ar_precincts.py --watch    # has the layer changed?

The work is scripts/statewide_precincts.py, shared with five other states;
this file says only where Arkansas's layer is, how to read one record and
what to expect.

THE SOURCE. ELECTION_PRECINCTS, layer 11 of the GIS Office's Boundaries
service (item bf5b2828a59542478f903b62ec83fe48), published with the Secretary
of State's Elections Division for the county clerks and county election
commissions. The item says the precincts are as each county's voter
registration system holds them and are updated as counties send new ones; the
GIS Office's web map of the layer says the boundaries are "a public domain
record". The layer's own description still says the data was "finalized in
2012", which only the item description contradicts.

A PRECINCT IN PIECES IS SEVERAL RECORDS. The layer has 2,928 records for
2,920 precincts (measured 2026-10-15): seven precincts are published as two or
three records each, one per piece, in Washington (four of them), Franklin,
Sebastian and Pope counties, and two of Washington's (Greenland Twp-1 and
Johnson Twp-3) have pieces dated more than three years apart, 2022-05-03 and
2025-09-26. They are joined into one precinct each, so a reader in any piece
gets that precinct's card. The key is the county and the precinct's name. The
layer's own `conct` field is not used: it is the county's name followed by the
precinct's everywhere except Searcy County, where it is the precinct's name
followed by a number.

A DATE ON HALF THE PRECINCTS. Each record carries `edit_date` (YYYYMMDD, as
text) where the county's last change was recorded, and the card prints it,
for a precinct in pieces the latest of its pieces' dates: measured 2026-10-15
the newest is 2026-10-02 (158 of Benton's 479), and 1,481 of 2,928 records
carry none, all of them in 34 counties and part of 17 more. A precinct with no
date gets a card that says the state's layer gives none, never an inferred
one.

SLIVERS ARE KEPT AS PUBLISHED. Two of Benton County's precincts, X009 and
X010, are 5 m2 and 3 m2 on the drawn file (measured 2026-10-15), and nothing
in the layer says what they are. A reader is unlikely ever to land in one; a
card there reports them by name like any other.

PACING. gis.arkansas.gov publishes no robots.txt (the address answers with a
web page, which permits every path), but the same office's open-data host,
geodata.gis.arkansas.gov, asks for 60 seconds between requests, and this
builder honours that here as the instance's other builders do. The layer
answers 200 records a request, so a build is about fifteen minutes.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import statewide_precincts as sp  # noqa: E402

LAYER = ("https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/"
         "Boundaries/FeatureServer/11")


def read(props):
    state = (props.get("state_fips") or "").strip()
    county = (props.get("county_fips") or "").strip()
    if state != "05" or not re.fullmatch(r"\d{3}", county):
        sp.fail(SPEC, "county %r/%r is not a five-digit Arkansas code: %r" % (state, county, props))
    edit = (props.get("edit_date") or "").strip()
    name = re.sub(r"\s+", " ", (props.get("precinct") or "").strip())
    out = {
        "key": "%s%s-%s" % (state, county, name),
        "name": name,
        "countyFips": state + county,
    }
    if edit:
        if not re.fullmatch(r"(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", edit):
            sp.fail(SPEC, "edit_date %r is not a YYYYMMDD date: %r" % (edit, props))
        out["edited"] = "%s-%s-%s" % (edit[:4], edit[4:6], edit[6:])
    return out


SPEC = sp.Spec(
    tag="ar",
    label="build_ar_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/ar/)",
    out_fields="state_fips,county_fips,county_name,precinct,edit_date",
    expect=2920,
    expect_counties=75,
    state_bbox={"minLng": -94.62, "minLat": 33.0, "maxLng": -89.64, "maxLat": 36.5},
    read=read,
    out_file="ar-precincts.json",
    pace=60.0,
    page=200,
    measure_field="Shape__Area",
    interval="4",  # 4 m: 9.3 MB, 2.44 MB gzipped (2026-10-15)
    multipart_records=8,
    part_latest=("edited",),
)

if __name__ == "__main__":
    sp.main(SPEC, __doc__)
