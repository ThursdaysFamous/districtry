#!/usr/bin/env python3
"""
Build ar/data/app/ar-fire-districts.json: Arkansas's fire districts, from the
Arkansas GIS Office's statewide map of them.

    python3 ar/scripts/build_ar_fire_districts.py            # fetch, check, write
    python3 ar/scripts/build_ar_fire_districts.py --check    # offline
    python3 ar/scripts/build_ar_fire_districts.py --watch    # has the layer changed?

The work is scripts/published_district_layers.py, which other builders
share; this file says where the layer is, how to read one record and what to
expect.

WHAT THE MAP IS. FIRE_DISTRICTS, layer 59 of the GIS Office's Boundaries
service. Its description (read 2026-10-16): "This data set represents the fire
protection districts of the State of Arkansas. Arkansas Code Annotated
(A.C.A.) §12-10-329, is a section of state law devoted to 9-1-1 public safety
and dictates each fire district must maintain an accurate map that is
certified by the Mayor, County Judge or County Fire Coordinator and
transmitted to the Arkansas GIS Office. The statute requires the Arkansas GIS
Office to maintain these maps and to assist the Arkansas 911 Board in carrying
out its duties." So the map is the one state law has every fire district file,
and it is the "special districts the state's own law creates" level of the
fleet's done standard (docs/DONE_STANDARD.md, entry 12) for Arkansas. A field
of codes (RFD on 546 records, MFD 348, FPD 63, VFD 7, none on 9) sorts them,
and neither the layer nor the GIS Office's product page (which now redirects
to its open-data home, read 2026-10-16) says what the codes stand for, so the
card shows none of them rather than guessing.

WHAT IT HOLDS. Measured 2026-10-16: 973 records for 971 districts.

  * ONE DISTRICT IN THREE RECORDS. Siloam Springs (Benton County) is three
    records with the same department number, dated 17 March 2025, 16 June 2025
    and 19 March 2026; the two later ones overlap by 12.55 of their 12.8 square
    miles, and whether the latest replaces the one before it the map does not
    say. All three are joined into one district, which is what a reader at any
    point in them is told, and the card gives the latest date (part_latest).
    The spec's multipart_records holds the two extra records.
  * FOUR RECORDS NAME GROUND, NOT A DISTRICT (UNASSIGNED). "Unserviced" (72
    square miles, no county, no date), "Missouri Serviced" (its county given
    as "MO"), "Unallocated Oklahoma" (no county) and "Unallocated" (Hempstead
    County). The card quotes each label as the map writes it and claims
    nothing more about the ground; the build fails if a record is added to or
    leaves that set, or if any other record names no county.
  * SIX NAMES ARE USED TWICE, in different counties (Midway in Logan and
    Baxter, Pea Ridge in Pope and Benton, and so on), so a district is keyed
    by its counties and its name together, and the hover names the county.
  * THE DISTRICTS DO NOT TILE THE STATE EXACTLY. Measured on this fetch with
    the state's county file: 400.5 of the state's 53,198 square miles (0.75%)
    are in no record, in 5,798 pieces: the largest is 56.5 square miles, and
    5,728 are under a tenth of a square mile each. Apart from Siloam Springs,
    134 pairs of districts overlap, by 7.3 square miles in all; the largest are
    PG&S (Searcy County) and Bruno (Marion County), 1.8 square miles, and three
    Hempstead County towns each drawn twice, as "<Town> City" and as "<Town>"
    (Perrytown, Blevins and Washington, 1.0 to 1.4 square miles each). Where
    the uncovered ground is, and why, and which record of an overlap answers,
    the map does not say. map_checks() holds the measurement, sampling
    points inside every county (99.27% land in a record, 2 of 15,000 in two;
    Garland County lowest at 90.5%), and the card lists every district the map
    puts a point in.

THE COUNTIES. `service_area` names the counties each district serves, one or
several, comma-separated ("Faulkner, White"). The card prints them in the
map's order; the build fails on a name that is not one of the 75 counties.
The agreement test runs over each set of counties' districts, which is what
`area` holds, and the two records the map gives no county share the group
NO_AREA.

THE DATE. `revision_date` is printed as the date the GIS Office's map gives
the lines, which is all the field says. 699 of the 973 records carry 21
September 2023, and the map does not say whether that is when those lines
changed, so the card calls it the date the map gives the lines and does not
call it a revision. The service stores each date as midnight in Arkansas,
which is the same calendar day in UTC.

THE FILED RECORDS. 90 records link a document the GIS Office holds for the
lines, 20 documents in all, whose file names name county ordinances, court
orders, resolutions and annexations; every one answered on 2026-10-16. Some file names carry spaces, which are
written as %20 (one already is). The field is named `url`, so the monthly link
check treats it as a link the GIS Office published rather than one this
project chose.

THE TERMS. The layer credits the Arkansas GIS Office and states no licence,
the same as the GIS Office's other layers this instance draws.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ar-fire-district-boards): the map names each fire district but not who runs
it, though the law that has each district file the map names who certifies
it; its type codes are defined nowhere the GIS Office publishes; one district
is filed three times, two of them overlapping; and the districts overlap one
another and leave ground in no district, with nothing saying which ground is
which.

PACING. gis.arkansas.gov publishes no robots.txt (the address answers with a
web page, which permits every path), and the same office's open-data host asks
for 60 seconds between requests, which this builder honours as the instance's
other builders do. The layer answers 200 records a request.
"""

import datetime
import json
import os
import random
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import published_district_layers as psb  # noqa: E402
import statewide_precincts as sp  # noqa: E402

LAYER = ("https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/"
         "Boundaries/FeatureServer/59")

COUNTIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "data", "app", "state-counties.json")

# The records whose name labels ground rather than a district, with the
# service_area each carries (None for a null, "" for an empty string),
# measured 2026-10-16.
UNASSIGNED = {
    "Unserviced": None,
    "Missouri Serviced": "MO",
    "Unallocated Oklahoma": "",
    "Unallocated": "Hempstead",
}

# what `area` holds for a record the map gives no county
NO_AREA = "(no county)"

# Points sampled inside each county, as the state's county file draws it, and
# what share must land in a district (one of the four UNASSIGNED records
# included, since the map draws them). Measured on the 2026-10-16 fetch: see
# map_checks().
COVER_SAMPLES = 200
COVER_MIN_ALL = 98.5
COVER_MIN_COUNTY = 85.0
COVER_MAX_TWO = 0.5

_county_names = None


def tidy(text):
    return " ".join(str(text).split()) if text is not None else ""


def county_names():
    global _county_names
    if _county_names is None:
        with open(COUNTIES_FILE, encoding="utf-8") as fh:
            _county_names = {f["properties"]["NAME"] for f in json.load(fh)["features"]}
    return _county_names


def counties_text(names):
    if not names:
        return None
    if len(names) == 1:
        return names[0] + " County"
    return ", ".join(names[:-1]) + " and " + names[-1] + " counties"


def iso_date(ms):
    if ms is None:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).date().isoformat()


def encode(url):
    """The address as a browser sends it: spaces and the like percent-encoded,
    an existing %XX left alone."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        psb.fail(SPEC, "record_link %r is not an https address; read it again" % url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc,
                                    urllib.parse.quote(parts.path, safe="/%"),
                                    parts.query, parts.fragment))


def read(props):
    name = tidy(props.get("name"))
    if not name:
        psb.fail(SPEC, "a record has no name: %r" % props)
    raw_area = props.get("service_area")
    area = tidy(raw_area)
    out = {"key": "%s|%s" % (area, name), "label": name, "area": area or NO_AREA}
    if name in UNASSIGNED:
        if raw_area != UNASSIGNED[name]:
            psb.fail(SPEC, "%r carries service_area %r, where UNASSIGNED records %r; read the "
                     "record again" % (name, raw_area, UNASSIGNED[name]))
        out["unassigned"] = True
    names = []
    if area and area != "MO":
        names = [tidy(t) for t in area.split(",")]
        for n in names:
            if n + " County" not in county_names():
                psb.fail(SPEC, "%r serves %r, which is not one of the state's counties"
                         % (name, n))
    elif name not in UNASSIGNED:
        psb.fail(SPEC, "%r names no county (service_area %r) and is not in UNASSIGNED"
                 % (name, raw_area))
    text = counties_text(names)
    if text:
        out["counties"] = text
    revised = iso_date(props.get("revision_date"))
    if revised:
        out["revised"] = revised
    link = props.get("record_link")
    if link:
        out["url"] = encode(tidy(link))
    return out


def map_checks(feats):
    """The four UNASSIGNED records are on the map once each; and points
    sampled inside every county land in a record at least COVER_MIN_ALL
    percent of the time overall and COVER_MIN_COUNTY percent in each county,
    and in two at most COVER_MAX_TWO percent of the time. --watch reads the
    districts without their shapes, so the sampling is skipped there."""
    flagged = sorted(f["properties"]["label"] for f in feats if f["properties"].get("unassigned"))
    if flagged != sorted(UNASSIGNED):
        psb.fail(SPEC, "the records naming ground rather than a district are %s, where "
                 "UNASSIGNED lists %s" % (flagged, sorted(UNASSIGNED)))
    if any(f.get("geometry") is None for f in feats):
        return
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        counties = json.load(fh)["features"]
    index = psb.Index(feats)
    rng = random.Random(2026)
    total = covered = two = 0
    lows = []
    for c in sorted(counties, key=lambda f: f["properties"]["GEOID"]):
        geom = c["geometry"]
        bb = sp.bbox(geom)
        n = hit = tries = 0
        while n < COVER_SAMPLES and tries < COVER_SAMPLES * 60:
            tries += 1
            pt = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
            if not sp.point_in_geometry(pt, geom):
                continue
            n += 1
            hits = index.at(pt)
            hit += bool(hits)
            two += len(hits) > 1
        pct = 100.0 * hit / n
        lows.append((pct, c["properties"]["NAME"]))
        if pct < COVER_MIN_COUNTY:
            psb.fail(SPEC, "only %.1f%% of points inside %s land in a fire district "
                     "(need %.1f%%)" % (pct, c["properties"]["NAME"], COVER_MIN_COUNTY))
        total += n
        covered += hit
    pct_all = 100.0 * covered / total
    if pct_all < COVER_MIN_ALL:
        psb.fail(SPEC, "only %.2f%% of points inside the state land in a fire district "
                 "(need %.1f%%)" % (pct_all, COVER_MIN_ALL))
    if 100.0 * two / total > COVER_MAX_TWO:
        psb.fail(SPEC, "%d of %d points inside the state land in two districts" % (two, total))
    lows.sort()
    print("coverage: %d of %d points inside the state (%.2f%%) land in a district, %d in two; "
          "lowest counties %s" % (covered, total, pct_all, two,
                                  ", ".join("%s %.1f%%" % (n, p) for p, n in lows[:5])))


SPEC = psb.Spec(
    tag="ar",
    label="build_ar_fire_districts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/ar/)",
    out_fields="name,service_area,revision_date,record_link",
    expect=971,
    expect_groups=135,
    read=read,
    out_file="ar-fire-districts.json",
    group="area",
    group_nouns=("set of counties", "sets of counties"),
    card_noun="fire district card",
    interval="4",
    pace=60.0,
    page=200,
    measure_field="Shape__Area",
    multipart_records=2,
    part_latest=("revised",),
    extra_check=map_checks,
    card_claims=(
        "Arkansas GIS Office's map of fire districts",
        "certified by the mayor, county judge or county fire coordinator",
    ),
    inside=(
        (-92.28915, 34.74665, "Pulaski|Little Rock", "the State Capitol, Little Rock's district"),
        # where the two later Siloam Springs records overlap, measured on the
        # 2026-10-16 fetch: one district once the records are joined
        (-94.52690, 36.18065, "Benton|Siloam Springs", "the Siloam Springs records' overlap"),
        (-92.99501, 34.77384, "|Unserviced", "the ground the map labels Unserviced"),
    ),
    outside=(
        # the largest piece of ground the map leaves in no record, 56.5 square
        # miles, measured on the 2026-10-16 fetch
        (-93.28415, 34.61342, "the largest piece the map leaves in no record"),
    ),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
