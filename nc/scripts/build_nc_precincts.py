#!/usr/bin/env python3
"""
Build nc/data/app/nc-precincts.json: North Carolina's 2,625 election
precincts, from the State Board of Elections' statewide file as NC OneMap
serves it.

    python3 nc/scripts/build_nc_precincts.py            # fetch, check, write
    python3 nc/scripts/build_nc_precincts.py --check    # offline
    python3 nc/scripts/build_nc_precincts.py --watch    # has the layer changed?

The work is scripts/statewide_precincts.py, shared with five other states;
this file says only where North Carolina's layer is, how to read one record
and what to expect.

TWO SURFACES OF ONE FILE. The State Board of Elections posts its statewide
precinct shapefile as a download only, in a folder of dated zips
(dl.ncsbe.gov/ShapeFiles/Precinct/, SBE_PRECINCTS_20260824.zip the newest on
2026-10-15), and states the data is public information under G.S. 132-1. NC
OneMap, run by the Center for Geographic Information and Analysis, serves a
queryable copy (item 771ae6473a1c4ba3bc768cc2c4b10015, "North Carolina Voting
Precincts", under a free-use policy), and that copy is what this builder
reads. It carries no date of its own; on 2026-10-15 it matched the 2026-08-24
file on the count in all 100 counties and on the maximum, minimum and sum of
`id`, so it is that file.

SO `--watch` ASKS TWO QUESTIONS. Has the copy changed since the build, and
has the Board posted a file newer than the one the copy was built from? The
second is one listing of the Board's own folder: a newer zip there with the
copy unchanged means NC OneMap has not loaded it yet, and the card would be
describing the older file.

THE COUNTY. Each record names its county in capitals and by the Board's own
number (1 to 100); the five-digit Census code comes from this instance's
county file by NAME. The Board's number is not the Census code's order: the
Board puts Macon (56) before McDowell, the Census puts McDowell (37111) before
Macon (37113), so arithmetic on one to get the other is wrong for those two,
which a first draft of this builder found by failing on Macon.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import json  # noqa: E402

import statewide_precincts as sp  # noqa: E402

LAYER = ("https://services.nconemap.gov/secure/rest/services/"
         "NC1Map_Boundaries/MapServer/0")
BUILT_FROM = "SBE_PRECINCTS_20260824.zip"
BOARD_FOLDER = "https://s3.amazonaws.com/dl.ncsbe.gov"


def _built_from_date():
    """BUILT_FROM's date as the card prints it ("August 24, 2026")."""
    import datetime  # noqa: PLC0415
    day = datetime.datetime.strptime(re.search(r"(\d{8})", BUILT_FROM).group(1), "%Y%m%d")
    return "%s %d, %d" % (day.strftime("%B"), day.day, day.year)


def _county_codes():
    path = os.path.join(sp.REPO_ROOT, "nc", "data", "app", "state-counties.json")
    with open(path, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    return {f["properties"]["BASENAME"].upper(): str(f["properties"]["GEOID"]) for f in feats}


COUNTY_CODES = _county_codes()


def read(props):
    name = (props.get("county_nam") or "").strip().upper()
    fips = COUNTY_CODES.get(name)
    if fips is None:
        sp.fail(SPEC, "county %r is not a county in the county file" % name)
    prec = (props.get("prec_id") or "").strip()
    return {
        "key": "%s-%s" % (fips, prec),
        "name": (props.get("enr_desc") or "").strip(),
        "code": prec,
        "countyFips": fips,
    }


def newer_board_file():
    """The newest SBE_PRECINCTS_<date>.zip in the Board's folder, read
    through the same robots gate."""
    import requests  # noqa: PLC0415
    import robots_policy  # noqa: PLC0415

    session = requests.Session()
    session.headers["User-Agent"] = SPEC.user_agent
    ok, why = robots_policy.RobotsGate(session, SPEC.user_agent).allows(BOARD_FOLDER + "/")
    if not ok:
        return None, "robots.txt refuses the Board's folder: %s" % why
    resp = session.get(BOARD_FOLDER, params={"delimiter": "/", "prefix": "ShapeFiles/Precinct/"},
                       timeout=120)
    resp.raise_for_status()
    names = sorted(set(re.findall(r"SBE_PRECINCTS_(\d{8})\.zip", resp.text)))
    if not names:
        return None, "the Board's folder listed no SBE_PRECINCTS file"
    built = re.search(r"(\d{8})", BUILT_FROM).group(1)
    return [n for n in names if n > built], "newest file in the Board's folder: %s" % names[-1]


SPEC = sp.Spec(
    tag="nc",
    label="build_nc_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/nc/)",
    out_fields="county_id,county_nam,prec_id,enr_desc,shape_leng",
    expect=2625,
    expect_counties=100,
    state_bbox={"minLng": -84.33, "minLat": 33.74, "maxLng": -75.39, "maxLat": 36.6},
    read=read,
    out_file="nc-precincts.json",
    pace=2.0,
    measure_field="shape_leng",
    interval="12",  # 4 m: 4.11 MB gzipped; 8 m: 2.97 MB; 12 m: 8.2 MB, 2.43 MB (2026-10-15)
    required=("key", "name", "code", "countyFips"),
    card_claims=("the Board's file of " + _built_from_date(),),
)

if __name__ == "__main__":
    if "--watch" in sys.argv:
        later, note = newer_board_file()
        print("build_nc_precincts --watch: " + note)
        if later:
            print("build_nc_precincts --watch: THE BOARD HAS POSTED A NEWER FILE (%s) than the "
                  "%s this file was built from. Check whether NC OneMap's copy has loaded it."
                  % (", ".join(later), BUILT_FROM))
            raise SystemExit(1)
    sp.main(SPEC, __doc__)
