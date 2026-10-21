#!/usr/bin/env python3
"""
Build la/data/app/la-precincts.json: Louisiana's 3,569 election precincts,
from the statewide precinct file the Legislature's redistricting office
publishes.

    python3 la/scripts/build_la_precincts.py            # fetch, check, write
    python3 la/scripts/build_la_precincts.py --check    # offline
    python3 la/scripts/build_la_precincts.py --watch    # has the file changed?

The work is scripts/statewide_precincts.py, shared with six other states;
this file says only where Louisiana's file is, how to read one record and
what to expect.

THE SOURCE IS A FILE, NOT A LAYER. The Louisiana Legislature's redistricting
site (redist.legis.la.gov) lists its precinct shapefiles edition by edition on
its "Precinct shapefiles and block equivalency files" page, and the newest,
measured 2026-10-21, is "2026 Precinct Shapefiles (01-27-2026)": one zipped
shapefile of every precinct in all 64 parishes, Last-Modified 2 February 2026.
The Legislature uses these precincts to draw its own plans, and their
population column, the 2020 census as the Legislature allocates it, sums to
4,657,757, the state's 2020 count. So the file is read through the shared
module's ShapefileZip fetcher, which holds the listing to the edition named
here: when the Legislature posts a newer one, a build stops until a person
has read it and changed EDITION. The host publishes no robots.txt (HTTP 404,
which permits every path), read with this builder's own client.

FIVE RECORDS ARE NOT PRECINCTS. Each of the five parishes on Lake
Pontchartrain (Jefferson, Orleans, St. Charles, St. John the Baptist and
Tangipahoa) has one record named "Voting Districts Not Defined", code ZZZZZZ,
covering its part of the lake, with no population; the Census uses that code
for water no voting district covers. They are dropped, so a click on the lake
says no precinct is there rather than naming one called "Voting Districts Not
Defined", and the build stops unless there are exactly five, each in one of
those parishes and each with no one living in it.

SO FIVE PARISHES HAVE A FLOOR OF THEIR OWN. The county file carries each
parish's legal area, the lake included, and the shared tiling check asks that
97% of the points sampled inside a parish land in one of its precincts. The
lake is 40.6% of Orleans's area in the county file, 39.1% of St. John the
Baptist's, 14.8% of Jefferson's, 10.1% of St. Charles's and 3.8% of
Tangipahoa's (measured 2026-10-21 with shapely on the full-precision file),
so each of those five is held to a floor of its own, set five points below
the share of its sample the build measured: 59.0% for Orleans, 57.5% for St.
John the Baptist, 85.0% for Jefferson, 90.0% for St. Charles and 97.0% for
Tangipahoa. Every other parish keeps 97%, and the lowest of them measured
99.5% (Iberia and West Carroll, one point each in a neighbour's precinct).
None of the 11,800 points sampled in the other 59 parishes fell outside
every precinct, which is why the card's empty note names only the lake.

TWELVE METRES. The shared rule draws at the smallest of 4, 8 and 12 metres
that brings the gzipped file to 2.5 MB or under. Measured 2026-10-21 on this
edition: 3.89 MB gzipped at 4 m, 2.82 MB at 8 m and 2.31 MB (7.8 MB raw) at
12 m, so Louisiana's precincts are drawn to within 12 metres, and the
drawn file agrees with the source at 99.95% of 6,000 points with no point in
two precincts.

474 OF THE PRECINCTS HAVE NO 2020 CENSUS CODE. Their Census fields are blank
(in Caddo 128 of its precincts), which reads as precincts split or renumbered
since 2020. Nothing here depends on those fields: the key is the parish and
the precinct's name as the parish uses it, unique across the file.

THE FINGERPRINT'S MEASURE IS POPULATION, NOT AREA. The file's own SHAPE_AREA
is in square degrees, which round to zero, so the fingerprint carries each
precinct's 2020 population as the Legislature allocates it, which moves when
a line moves across a populated block; the record also keeps the zip's own
SHA-256, so --watch also says when the file was replaced in place.

NAD83, AS PUBLISHED. The file is in geographic NAD83, which mapshaper's
-proj wgs84 treats as WGS84; the two differ by about a metre in Louisiana,
far inside the interval the lines are drawn to.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import statewide_precincts as sp  # noqa: E402

# The edition this file is built from, and the page that lists every edition.
EDITION = "2026 Precinct Shapefiles (01-27-2026).zip"
LAYER = "https://redist.legis.la.gov/2026_Files/Shapefiles/" + EDITION.replace(" ", "%20")
LISTING = "https://redist.legis.la.gov/default_ShapeFiles2020"
EDITION_RE = (r"Precinct Shapefiles \((?P<m>\d{2})-(?P<d>\d{2})-(?P<y>\d{4})\)\.zip")

# The parts of Lake Pontchartrain the file leaves undefined, one per parish.
UNDEFINED_CODE = "ZZZZZZ"
UNDEFINED_PARISHES = {"051", "071", "089", "095", "105"}

_read_zip = sp.ShapefileZip(listing=LISTING, edition_re=EDITION_RE)


def fetch(spec, geometry=True):
    records, meta = _read_zip(spec, geometry)
    kept, dropped = [], []
    for rec in records:
        p = rec["properties"]
        if str(p.get("VTD") or "").strip() == UNDEFINED_CODE:
            dropped.append(p)
        else:
            kept.append(rec)
    where = sorted(str(p.get("COUNTY") or "") for p in dropped)
    if where != sorted(UNDEFINED_PARISHES):
        sp.fail(spec, "the records coded %s are in parishes %r, expected one in each of %r — "
                "read the file before changing the declaration"
                % (UNDEFINED_CODE, where, sorted(UNDEFINED_PARISHES)))
    lived = [p for p in dropped if p.get("TOT_POP")]
    if lived:
        sp.fail(spec, "an area coded %s has people living in it: %r" % (UNDEFINED_CODE, lived))
    print("dropped the %d areas coded %s (Lake Pontchartrain, no population)"
          % (len(dropped), UNDEFINED_CODE), file=sys.stderr)
    return kept, meta


def read(props):
    state = str(props.get("STATEFP20") or "").strip()
    parish = str(props.get("COUNTY") or "").strip()
    if state != "22" or len(parish) != 3 or not parish.isdigit() \
            or parish != str(props.get("COUNTYFP20") or "").strip():
        sp.fail(SPEC, "parish %r/%r is not a five-digit Louisiana code: %r" % (state, parish, props))
    name = " ".join(str(props.get("VTD") or "").split())
    if not name:
        sp.fail(SPEC, "a record has no precinct name: %r" % (props,))
    return {
        "key": "22%s-%s" % (parish, name),
        "name": name,
        "countyFips": "22" + parish,
    }


SPEC = sp.Spec(
    tag="la",
    label="build_la_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/la/)",
    out_fields="",
    expect=3569,
    expect_counties=64,
    state_bbox={"minLng": -94.05, "minLat": 28.85, "maxLng": -88.75, "maxLat": 33.02},
    read=read,
    out_file="la-precincts.json",
    measure_field="TOT_POP",
    interval="12",
    fetcher=fetch,
    card_claims=("its edition of 27 January 2026",),
    # Each floor is five points below the share of that parish's sample the
    # build measured on 2026-10-21 at this interval (in brackets).
    tiling_floor_by_county={
        "22051": 0.80,  # Jefferson (0.850): the lake is 14.8% of the parish in the county file
        "22071": 0.54,  # Orleans (0.590): 40.6%
        "22089": 0.85,  # St. Charles (0.900): 10.1%
        "22095": 0.52,  # St. John the Baptist (0.575): 39.1%
        "22105": 0.92,  # Tangipahoa (0.970): 3.8%
    },
)

if __name__ == "__main__":
    sp.main(SPEC, __doc__)
