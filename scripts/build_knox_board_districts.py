#!/usr/bin/env python3
"""Build Knox County's five County Board districts from the county's own published sources.

WHY THIS COUNTY WAS STUCK, AND WHAT UNSTUCK IT. Knox's gap record said
knoxcountyil.gov "refuses every request", which is true of the county's WEBSITE
and was written as though it described the county. Knox has FOUR hosts and only
one of them refuses:

  knoxcountyil.gov        403, Akamai-class deny — the website
  gis.knoxcountyil.gov    a public ArcGIS Server serving the COLES PATTERN
  cms2.revize.com/...     the website's DOCUMENTS, served plainly
  knoxclerk.org           cited by the county's own 2022 packet; DEAD (HTTPS
                          resets, HTTP 503), confirmed from two networks

The county's ADOPTED MAP — "Knox County Board Districts 2022", prepared by the
Knox County GIS Department and dated 01/28/2022 — sits on the document host at
Documents/Department/County Clerk/Elections Information/General Information
about Elections/Political Districts/County-District-Map-2022.pdf. It is a
vector PDF, and on it the black-and-yellow DASHED line is the county board
district boundary while the thick ORANGE line is the precinct boundary. That
distinction is the whole read and it is visible where an orange township line
crosses straight through the dashed district line at 2400N.

READING IT COST ONE WRONG METHOD FIRST, recorded because it looked right.
Sampling the map's FILL COLOURS at each precinct label and clustering them
produced a clean, complete, confident assignment that was WRONG: the fills are
per-TOWNSHIP decoration for legibility, not per-district, so the clusters were
meaningless. It was caught by the arithmetic below, not by inspection — which
is why the arithmetic is a gate here and not a comment.

THE COMPOSITION, read off the county's own map:

  District 4 (13 precincts)  Rio, Ontario, Sparta, Henderson, Walnut Grove and
                             Lynn townships; Galesburg Township; Knox 1-6
  District 5 (15 precincts)  Copley, Victoria, Persifer, Truro, Haw Creek,
                             Elba, Salem, Maquon, Chestnut, Orange and Indian
                             Point townships; Cedar 1-4

TWO WITNESSES, which is this project's standard. The counts 13 and 15 are
exactly what the county's CERTIFIED RETURNS report for those two contests, in
every election on the vendor's archive back to 2022 — six result sets across
two districting plans, none of which ever names a precinct. The map names them;
the returns count them; they agree.

IT RESOLVES AT TOWNSHIP LEVEL, which is what makes it drawable. All six Knox
precincts fall in District 4 and all four Cedar precincts in District 5, so no
township is split between districts and the sub-precinct geometry the county
does not publish is not needed. Eight whole townships make District 4 and
twelve make District 5; all twenty are accounted for exactly once.

DISTRICTS 1, 2 AND 3 ARE NOT DERIVED HERE AT ALL. They lie inside the city of
Galesburg, which runs its OWN Board of Election Commissioners, and the city
publishes them as finished polygons ("Knox County Board Districts in Galesburg",
three features keyed DISTRICT 1/2/3). They are taken as published. District 4 is
then the union of its townships MINUS that city area, because the city sits
inside Galesburg Township and its neighbours.

CORROBORATED 2026-09-08 BY THE COUNTY'S OWN PRECINCT LAYER, which is worth
recording because until then this build rested on a map read plus arithmetic
over certified returns, with no county-authored geometry behind it. GIS
Coordinator Taiwo Agbaje sent Precincts_20200717.zip by e-mail in reply to a
request that named districtry -- a 2020-vintage ESRI precinct layer in NAD83 /
Illinois West (ftUS) carrying a District column. Overlaid on what this builder
writes, the two agree at IoU 0.9921, 0.9881, 0.9936 and 0.9999 for districts 1,
3, 4 and 5. District 2 differs by 4.12 km2 and that difference is explained
rather than unexplained: 95% of it is the city of Galesburg's corporate limits
reaching into Galesburg Township and Henderson-2, ground the 2020 precinct
layer still assigns to county precincts.

THE FILE IS RETAINED OFFLINE AND NOTHING DERIVED FROM IT SHIPS. It is the 2020
fabric -- its 31 county precincts match ISBE's certified precinct-level results
for the November 2020 general one for one by name -- and three precincts have
since gone (Henderson 2 to 1, Indian Point 2 to 1, and Knox Seven into
neighbours nothing names). See the knox-precinct-geometry gap record.

THE TWO HARDCODED TABLES BELOW ARE NOW INDEPENDENTLY CONFIRMED, and were not
when they were written. PRECINCTS_PER_TOWNSHIP and CERTIFIED_PRECINCT_COUNTS
were transcribed by hand from the county's map and its returns, and nothing in
this repo re-checked them. ISBE's certified returns for the June 2022 primary
and the 2026 general primary both carry six Knox Township precincts and four
Cedar precincts, which is what these tables assert. A hand-entered constant
that no gate re-measures is worth naming as such even when it turns out right.

Usage:
    python3 scripts/build_knox_board_districts.py           # write the data file
    python3 scripts/build_knox_board_districts.py --check   # re-verify, write nothing
"""

import argparse
import json
import os
import sys

import requests
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aia_bundle                                             # noqa: E402
import vtd_board_districts as V                               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_PATH = os.path.join(REPO, "il", "data", "app", "knox-county-board-districts.json")

COUNTY_FIPS = "095"
COUNTY_POP_2020 = 49967

# The county's own GIS server. Serves the Coles pattern; aia_bundle supplies the
# intermediate it omits, with the bytes pinned. Verification is never disabled.
KNOX_GIS = ("https://gis.knoxcountyil.gov/server/rest/services/Public/"
            "Knox_V4/MapServer/60")
# The city's own AGOL org. Complete chain, no bundle needed.
GALESBURG_DISTRICTS = ("https://services1.arcgis.com/T5ar9pn3YeFZ47Wh/arcgis/rest/"
                       "services/Knox_County_Board_Districts_in_the_City_of_Galesburg/"
                       "FeatureServer/0")
GALESBURG_PRECINCTS = ("https://services1.arcgis.com/T5ar9pn3YeFZ47Wh/arcgis/rest/"
                       "services/Precincts/FeatureServer/0")

MAP_URL = ("https://cms2.revize.com/revize/knoxcounty/Documents/Department/"
           "County%20Clerk/Elections%20Information/General%20Information%20about%20"
           "Elections/Political%20Districts/County-District-Map-2022.pdf")
MAP_LABEL = "Knox County Board Districts 2022 (Knox County GIS Department, 01/28/2022)"

# Township -> district, transcribed from the adopted map. Names are the county
# GIS layer's own spelling of its Township field.
DISTRICT_TOWNSHIPS = {
    4: ["RIO", "ONTARIO", "SPARTA", "HENDERSON", "WALNUT GROVE", "LYNN",
        "GALESBURG", "KNOX"],
    5: ["COPLEY", "VICTORIA", "PERSIFER", "TRURO", "HAW CREEK", "ELBA",
        "SALEM", "MAQUON", "CHESTNUT", "ORANGE", "INDIAN POINT", "CEDAR"],
}
EXPECTED_TOWNSHIPS = 20

# The precincts each district's townships carry, per the county's own precinct
# names. Not used to build geometry — used to GATE it, because these counts are
# the independent witness the certified returns supply.
PRECINCTS_PER_TOWNSHIP = {"KNOX": 6, "CEDAR": 4}
CERTIFIED_PRECINCT_COUNTS = {4: 13, 5: 15}
CITY_DISTRICTS = (1, 2, 3)
CITY_PRECINCTS_PER_DISTRICT = {1: 7, 2: 7, 3: 6}

# Population spread this build refuses to ship past. The county's own
# apportionment is what it is and is REPORTED rather than smoothed, but a wild
# figure means the transcription is wrong, not that the county drew it that way.
MAX_DEVIATION_PCT = 30.0

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/126.0 Safari/537.36")}
TIMEOUT = 90


def fail(msg):
    raise SystemExit("build-knox-board: " + msg)


def arcgis_features(url, out_fields, verify=True):
    r = requests.get(url + "/query",
                     params={"where": "1=1", "outFields": out_fields,
                             "outSR": 4326, "f": "geojson"},
                     headers=HEADERS, timeout=TIMEOUT, verify=verify)
    r.raise_for_status()
    gj = r.json()
    feats = gj.get("features") or []
    if not feats:
        fail("%s returned no features" % url)
    return feats


def load_townships(verify):
    feats = arcgis_features(KNOX_GIS, "Township", verify=verify)
    if len(feats) != EXPECTED_TOWNSHIPS:
        fail("county GIS returned %d townships, expected %d"
             % (len(feats), EXPECTED_TOWNSHIPS))
    out = {}
    for f in feats:
        name = (f["properties"].get("Township") or "").strip().upper()
        if not name:
            fail("a township feature carries no name")
        if name in out:
            fail("township %r appears twice" % name)
        out[name] = shape(f["geometry"]).buffer(0)
    return out


def load_city_districts():
    feats = arcgis_features(GALESBURG_DISTRICTS, "DISTRICT")
    out = {}
    for f in feats:
        d = int(str(f["properties"].get("DISTRICT")).strip())
        out[d] = shape(f["geometry"]).buffer(0)
    if sorted(out) != sorted(CITY_DISTRICTS):
        fail("the city layer keys %r, expected %r" % (sorted(out), sorted(CITY_DISTRICTS)))
    return out


def check_city_precincts():
    """The city's precinct layer is the cross-check on its district layer.

    Twenty precincts each carrying a COUNTY field the publisher's own web map
    labels "County Board District". If those stop grouping 7/7/6 the city has
    re-drawn something and this build should stop rather than ship a stale
    district.
    """
    feats = arcgis_features(GALESBURG_PRECINCTS, "PRECINCT,COUNTY")
    tally = {}
    for f in feats:
        key = str(f["properties"].get("COUNTY")).strip()
        tally[key] = tally.get(key, 0) + 1
    got = {int(k): v for k, v in tally.items() if k.isdigit()}
    if got != CITY_PRECINCTS_PER_DISTRICT:
        fail("Galesburg's precincts group %r by board district, expected %r"
             % (got, CITY_PRECINCTS_PER_DISTRICT))
    return len(feats)


def precinct_count(townships):
    return sum(PRECINCTS_PER_TOWNSHIP.get(t, 1) for t in townships)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="re-verify and compare against the shipped file; write nothing")
    args = ap.parse_args()

    # THE GATE THAT CAUGHT THE WRONG READ. Transcription first, arithmetic
    # second, geometry last — so a mis-transcribed township fails here rather
    # than shipping as a plausible-looking polygon.
    named = [t for ts in DISTRICT_TOWNSHIPS.values() for t in ts]
    if len(named) != EXPECTED_TOWNSHIPS or len(set(named)) != EXPECTED_TOWNSHIPS:
        fail("the transcription names %d townships (%d distinct), expected %d each"
             % (len(named), len(set(named)), EXPECTED_TOWNSHIPS))
    for d, want in CERTIFIED_PRECINCT_COUNTS.items():
        got = precinct_count(DISTRICT_TOWNSHIPS[d])
        if got != want:
            fail("District %d's townships carry %d precincts; the county's certified "
                 "returns report %d. The map transcription is wrong." % (d, got, want))

    bundle = aia_bundle.ca_bundle("build-knox-board")
    try:
        townships = load_townships(bundle)
    finally:
        if os.path.exists(bundle):
            os.unlink(bundle)

    missing = [t for t in named if t not in townships]
    if missing:
        fail("the county GIS does not carry township(s) %r — its names are %r"
             % (missing, sorted(townships)))

    city = load_city_districts()
    n_city_precincts = check_city_precincts()
    city_area = unary_union(list(city.values())).buffer(0)

    districts = {}
    for d in (4, 5):
        merged = unary_union([townships[t] for t in DISTRICT_TOWNSHIPS[d]]).buffer(0)
        if d == 4:
            # The city sits inside District 4's townships; districts 1-3 are the
            # city. District 5's townships do not touch it, and that is checked
            # rather than assumed immediately below.
            merged = merged.difference(city_area).buffer(0)
        districts[d] = merged
    for d in CITY_DISTRICTS:
        districts[d] = city[d]

    stray = districts[5].intersection(city_area).area
    if stray > districts[5].area * 1e-6:
        fail("District 5's townships overlap the city area by %.6f of their extent — "
             "the city is not wholly inside District 4's townships and this build's "
             "subtraction is wrong" % (stray / districts[5].area))

    # Population, from the census fabric rather than from the county: a gross
    # mis-transcription shows up here as a wildly lopsided pair.
    vtds = V.fetch_vtds(COUNTY_FIPS, shape, fail)
    total = sum(v["pop"] for v in vtds.values())
    if total != COUNTY_POP_2020:
        fail("census VTDs sum to %d, expected the county's %d" % (total, COUNTY_POP_2020))
    pops = {d: 0 for d in districts}
    unplaced = 0
    for rec in vtds.values():
        pt = rec["geom"].representative_point()
        for d, geom in districts.items():
            if geom.contains(pt):
                pops[d] += rec["pop"]
                break
        else:
            unplaced += rec["pop"]
    ideal = COUNTY_POP_2020 / 5.0
    worst = max(abs(p - ideal) / ideal * 100 for p in pops.values())
    if worst > MAX_DEVIATION_PCT:
        fail("worst district deviates %.1f%% from the per-district ideal (%d), past "
             "this build's %.0f%% ceiling — populations %r"
             % (worst, ideal, MAX_DEVIATION_PCT, pops))

    features = []
    for d in sorted(districts):
        features.append({
            "type": "Feature",
            "properties": {
                "district": str(d),
                "precincts": (n_city_precincts if d in CITY_DISTRICTS else None),
                "source": ("City of Galesburg (published)" if d in CITY_DISTRICTS
                           else MAP_LABEL),
            },
            "geometry": V.round_geom(districts[d], mapping),
        })
    payload = {"type": "FeatureCollection", "features": features}

    print("build-knox-board: districts 1-3 as the city publishes them; 4 and 5 "
          "from %d townships" % EXPECTED_TOWNSHIPS)
    for d in sorted(pops):
        print("   district %d: %6d people (%+.1f%% of ideal)"
              % (d, pops[d], (pops[d] - ideal) / ideal * 100))
    if unplaced:
        print("   %d people in VTDs whose representative point fell in no district "
              "(edge effects; not a gate)" % unplaced)

    V.write_or_check([(OUT_PATH, V.dumps(payload))], args.check, REPO, fail,
                     "knox board districts")


if __name__ == "__main__":
    main()
