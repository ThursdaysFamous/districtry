#!/usr/bin/env python3
"""
Build ar/data/app/ar-city-wards.json: the 56 wards of the twelve Arkansas
cities above 25,000 people whose councils are elected by ward, from the
Arkansas GIS Office's map of municipal wards.

    python3 ar/scripts/build_ar_city_wards.py            # fetch, check, write
    python3 ar/scripts/build_ar_city_wards.py --check    # offline
    python3 ar/scripts/build_ar_city_wards.py --watch    # has the layer changed?

The work is scripts/published_district_layers.py, which other builders share;
this file says where the layer is, how to read one record and what to expect.
WHICH cities are drawn is read from the seats file the council roster is
built from (ar/data/source/ar-city-council-seats.json): a city with a seat its
wards' own voters elect is drawn, and the seven that elect every seat
citywide are not, because a reader in one of their wards votes for every
seat. ar/scripts/build_ar_city_councils.py says how that was measured, and
its --check holds every drawn ward to a seat elected by it and every such
seat to a drawn ward.

THE SOURCE. "MUNICIPAL_WARDS", layer 50 of the GIS Office's statewide
boundaries service: 852 wards of 262 cities and towns when read on
2026-10-16, with each ward's city, its number and two dates. It carries the
Arkansas GIS Office's copyright line, states no licence, and describes itself
as not representing exact legal boundaries; the card says that. The twelve
cities' wards number 56: Little Rock 7, Hot Springs 6, Texarkana 6, Benton 5,
and four each in Fayetteville, Fort Smith, North Little Rock, Conway, Pine
Bluff, Sherwood, Paragould and Russellville, one record per ward.

THE DATES ARE NOT A GUIDE TO WHICH PLAN IS CURRENT. Each record carries an
effective date and a revised date, and they are read here but not shown:
Little Rock's Ward 6 took effect on 9 September 2026 and was revised on 14
October 2026, two days before this was read, while Fort Smith's Ward 4 carries
the revised date "2021094", which is not a date. Whether each city's lines
are its current plan was not established for every city, and the card says
the lines are the state's copy.

HOT SPRINGS CALLS ITS WARDS DISTRICTS. The map writes "Ward 1" to "Ward 6"
for Hot Springs, whose Board of Directors is elected by district, so the
label takes the city's word from the seats file.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ar-municipal-officeholders): the map records no voting rule, so nothing says
which cities elect by these wards; its dates cannot tell a current plan from
an old one, and one is malformed; it states no licence; and it describes
itself as not the legal boundaries.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import published_district_layers as psb  # noqa: E402

LAYER = ("https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/"
         "Boundaries/FeatureServer/50")

SEATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                          "data", "source", "ar-city-council-seats.json")
STATE_FIPS = "05"


def ward_cities():
    """{place code: (Census id, name, word for a ward)} for every city in the
    seats file with a seat its ward's own voters elect."""
    with open(SEATS_FILE, encoding="utf-8") as fh:
        cities = json.load(fh)["cities"]
    out = {}
    for geoid, c in sorted(cities.items()):
        if any(s.get("by") == "ward" for s in c["seats"]):
            if not geoid.startswith(STATE_FIPS) or len(geoid) != 7:
                raise SystemExit("build_ar_city_wards: FATAL: %r is not an Arkansas place id"
                                 % geoid)
            out[geoid[2:]] = (geoid, c["name"], c.get("wardWord") or "Ward")
    return out


CITIES = ward_cities()
WHERE = "city_fips IN (%s)" % ",".join("'%s'" % f for f in sorted(CITIES))


def read(props):
    city = CITIES.get(props.get("city_fips"))
    if city is None:
        psb.fail(SPEC, "a record carries city_fips %r, which the query did not ask for: %r"
                 % (props.get("city_fips"), props))
    geoid, name, word = city
    if props.get("city_name") != name:
        psb.fail(SPEC, "the map names city %s %r and the seats file %r"
                 % (props.get("city_fips"), props.get("city_name"), name))
    m = re.fullmatch(r"Ward ([1-9][0-9]?)", str(props.get("ward") or ""))
    if not m:
        psb.fail(SPEC, "%s: a ward reads %r, which is not 'Ward <number>'"
                 % (name, props.get("ward")))
    n = m.group(1)
    if props.get("ward_code") != "W" + n:
        psb.fail(SPEC, "%s ward %s carries ward_code %r" % (name, n, props.get("ward_code")))
    return {"key": "%s-%s" % (geoid, n), "geoid": geoid, "city": name, "ward": n,
            "label": "%s %s" % (word, n)}


SPEC = psb.Spec(
    tag="ar",
    label="build_ar_city_wards",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/ar/)",
    out_fields="city_name,city_fips,ward,ward_code",
    expect=56,
    expect_groups=12,
    read=read,
    out_file="ar-city-wards.json",
    group="geoid",
    group_nouns=("city", "cities"),
    card_noun="city council district card",
    interval="4",
    where=WHERE,
    measure_field="Shape__Area",
    card_claims=(
        "Arkansas GIS Office's map of municipal wards",
        "not the exact legal boundaries",
    ),
    # Each point is one the Census's place map puts in the city named
    # (TIGERweb, read 2026-10-16), and its ward is the answer the GIS Office's
    # own layer gave when asked about that point the same day.
    inside=(
        (-92.28896, 34.74675, "0541000-1", "the State Capitol, Little Rock"),
        (-93.05540, 34.50410, "0533400-1", "a point in Hot Springs"),
        (-92.26720, 34.75500, "0550450-2", "a point in North Little Rock"),
    ),
    outside=(
        # the source puts this point in Springdale's Ward 4, which is not
        # drawn because Springdale elects every seat citywide
        (-94.12900, 36.18670, "a point in Springdale, which elects every seat citywide"),
    ),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
