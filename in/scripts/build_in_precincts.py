#!/usr/bin/env python3
"""
Build in/data/app/in-precincts.json: Indiana's 5,121 election precincts, from
IndianaMap's statewide layer of the General Assembly's and the Election
Division's own data.

    python3 in/scripts/build_in_precincts.py            # fetch, check, write
    python3 in/scripts/build_in_precincts.py --check    # offline
    python3 in/scripts/build_in_precincts.py --watch    # has the layer changed?

The work is scripts/statewide_precincts.py, shared with five other states;
this file says only where Indiana's layer is, how to read one record and what
to expect.

THE SOURCE. IndianaMap "Voting District Boundaries 2026" (item
14c2a1ab175449678b2c3f7c9574b77a, owner IndianaMap), published by the Indiana
Geographic Information Office. The item says the data "was obtained from the
Indiana General Assembly and Indiana Elections Division in June 2026" and
that the General Assembly updates these boundaries every year by gathering
each county's own. It names no licence, only a limitation of warranties.

EACH YEAR IS A NEW SERVICE, AND THAT IS THE ONE THING THIS BUILDER CANNOT
NOTICE BY ITSELF. The 2023, 2024 and 2026 editions each sit at their own URL,
the layer id moved (1 in 2023 and 2024, 0 in 2026), and the field names carry
the year (p26, p26county, p26_stfid). There is no 2025 edition. A builder
pinned to one edition goes on reading it after the next one is posted, so
`--watch` also asks IndianaMap's catalogue whether a later "Voting District
Boundaries" service exists, and says so when one does; reading it means
editing LAYER and the field names here deliberately.

MEASURED 2026-10-15: 5,121 records, 5,121 distinct p26_stfid, all 92
counties; the layer was last edited 2026-09-11. The layer has no county-name
field, only the three-digit county code, so the county's name comes from this
instance's own county file.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import statewide_precincts as sp  # noqa: E402

LAYER = ("https://gisdata.in.gov/server/rest/services/Hosted/"
         "Voting_District_Boundaries_2026/FeatureServer/0")
EDITION = 2026
CATALOGUE = "https://gisdata.in.gov/server/rest/services/Hosted"


def read(props):
    """One record as the card reads it. p26_stfid is the state's own key:
    18 + the county's three-digit code + the county's five-digit precinct
    code (e.g. 1809700055 is not a real one; the shape is what is checked)."""
    county = (props.get("county") or "").strip()
    local = (props.get("p26county") or "").strip()
    key = (props.get("p26_stfid") or "").strip()
    if not re.fullmatch(r"\d{3}", county):
        sp.fail(SPEC, "county code %r is not three digits: %r" % (county, props))
    if key[:5] != "18" + county:
        sp.fail(SPEC, "p26_stfid %r does not begin with 18 and county %r" % (key, county))
    return {
        "key": key,
        "name": (props.get("p26") or "").strip(),
        "code": local,
        "countyFips": "18" + county,
    }


def newer_edition():
    """The years of every "Voting_District_Boundaries_<year>" service in
    IndianaMap's hosted folder, read once, through the same robots gate."""
    import requests  # noqa: PLC0415
    import robots_policy  # noqa: PLC0415

    session = requests.Session()
    session.headers["User-Agent"] = SPEC.user_agent
    ok, why = robots_policy.RobotsGate(session, SPEC.user_agent).allows(CATALOGUE)
    if not ok:
        return None, "robots.txt refuses the catalogue: %s" % why
    doc = session.get(CATALOGUE, params={"f": "json"}, timeout=120).json()
    years = sorted(int(m.group(1)) for s in doc.get("services") or []
                   for m in [re.search(r"Voting_District_Boundaries_(\d{4})$", s.get("name") or "")]
                   if m)
    return [y for y in years if y > EDITION], "editions in the catalogue: %s" % years


SPEC = sp.Spec(
    tag="in",
    label="build_in_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/in/)",
    out_fields="county,p26,p26county,p26_stfid",
    expect=5121,
    expect_counties=92,
    state_bbox={"minLng": -88.1, "minLat": 37.77, "maxLng": -84.78, "maxLat": 41.77},
    read=read,
    out_file="in-precincts.json",
    measure_field="SHAPE__Area",
    interval="4",  # 4 m: 7.1 MB, 1.48 MB gzipped (2026-10-15)
    required=("key", "name", "code", "countyFips"),
    card_claims=("Indiana's %d precinct map" % EDITION,),
)

if __name__ == "__main__":
    if "--watch" in sys.argv:
        later, note = newer_edition()
        print("build_in_precincts --watch: " + note)
        if later:
            print("build_in_precincts --watch: A LATER EDITION EXISTS (%s). Read it, then "
                  "edit LAYER, EDITION and the field names here." % ", ".join(map(str, later)))
            raise SystemExit(1)
    sp.main(SPEC, __doc__)
