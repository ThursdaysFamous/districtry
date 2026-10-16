#!/usr/bin/env python3
"""
Build ok/data/app/ok-conservation-districts.json: Oklahoma's 84
conservation districts, from the Oklahoma Conservation Commission's map of
them.

    python3 ok/scripts/build_ok_conservation_districts.py            # fetch, check, write
    python3 ok/scripts/build_ok_conservation_districts.py --check    # offline
    python3 ok/scripts/build_ok_conservation_districts.py --watch    # has the layer changed?

The work is scripts/published_district_layers.py, which other builders
share; this file says where the layer is, how to read one record and what to
expect. Each district's office comes from a separate file with a separate
source, built by ok/scripts/build_ok_conservation_offices.py from the
Commission's directory of district offices, and that builder reads this file
to know which districts are drawn.

WHAT A CONSERVATION DISTRICT IS. A unit of local government under the
Conservation District Act (Title 27A of the Oklahoma Statutes), "the primary
local unit of government responsible for the conservation of the renewable
natural resources of this state" (27A O.S. § 3-1-102, as the Commission's own
copy of the act prints it). Its governing body is five directors: three
elected by the registered voters in the district for staggered three-year
terms, and two appointed by the Commission for two-year terms (§ 3-3-201),
on the board's recommendation (the Commission's 2014 notice of the filing
period and its April 2024 training note on director elections, both read
2026-10-16). It is the "special districts the state's own law creates" level
of the fleet's done standard (docs/DONE_STANDARD.md, entry 12), and the one
family of Oklahoma special districts a state office maps statewide with
elected boards: the technology center districts are the other, and their map
was last redrawn in 2020 and is cut at county lines.

THE SOURCE. "cons_dis", layer 0 of the Commission's own hosted service on
ArcGIS Online (owner shellie.willoughby.occ), last edited 15 December 2023
when read. A second copy, published by the state Senate's account and
crediting the Commission, carries the same 106 records with identical shapes
(measured 2026-10-16, every district's symmetric difference zero) and differs
only in one name's capitals; the Commission's is read because it is the
publisher's.

  * 106 RECORDS DRAW 84 DISTRICTS. Five districts are published in several
    records each, 27 in all, and each is joined into one shape here:
    Kingfisher County (11 records), East Canadian County (9), Kiamichi (3),
    Little River (2) and Tillman County (2). The spec's multipart_records
    holds the 22 records beyond each district's first.
  * KINGFISHER'S AND EAST CANADIAN'S DISTRICTS INTERLOCK. Ten of
    Kingfisher's pieces (21.2 km2 in all) lie wholly inside East Canadian's
    lines, and seven of East Canadian's (7.1 km2) inside Kingfisher's, along
    the two districts' shared line near the Kingfisher and Canadian county
    line. Whether that is where the two districts' lines really run, or a
    drafting artefact of how the map was made, the map does not say; it is
    drawn as published, and the point check below holds one Kingfisher piece
    inside East Canadian's lines to that answer.
  * THE DISTRICTS COVER THE STATE, BAR SLIVERS. Measured on the 2026-10-16
    fetch against the state's county file, 67 km2 of Oklahoma (0.04%) is in
    no district, most of it (43 km2) a strip along the Kansas line in Texas
    County where the map's edge and the Census line part, and five pairs of
    districts overlap by 0.36 km2 in all. covers_the_state() holds that
    measurement, and the card says so when a point falls in two districts.

THE NAME. The map writes most districts "<name> CD", which is spelled out
here as "<name> Conservation District"; the card prefers the name the
Commission's directory gives (which spells out one name the map shortens,
Central North Canadian River), carried in the offices file.

THE COUNT IS PER DISTRICT. The map carries no grouping the agreement test
could run over (no county field, and 84 districts for 77 counties), so each
district is its own group and is held to the test on its own.

THE TERMS. The layer and its item state no licence, no access terms and no
copyright line (read 2026-10-16). The Commission's website has general terms
of use that allow only personal, non-commercial use of the site's content,
"databases" included, and reach "any related Oklahoma Conservation Commission
applications"; whether a map the Commission hosts elsewhere is one of those
they do not say. An unstated licence is silence, not a grant (the Lansing
wards reading, mi/scripts/build_mi_lansing_wards.py), so whether to show the
map before the Commission confirms is the operator's call, put to the operator
on 2026-10-16 with the directory's terms, which
ok/scripts/build_ok_conservation_offices.py records in full. The state
Senate's account republishes the map, credited to the Commission.

PUBLISHING GAPS, recorded as evidence for the state-publishing ask (gap
ok-conservation-district-directors): the layer and its item carry no licence,
while the website's terms allow only personal, non-commercial use; five
districts are split across 22 extra records; the map's
names are abbreviated and one drops a word of the district's name; the
Commission's own 2014 notice counts 87 district boards where the map and its
directory count 84, with nothing saying which were merged; and the directory
names each district's office but none of its directors, though the act has
the Commission issue every director's certificate.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import json  # noqa: E402

import published_district_layers as psb  # noqa: E402
import statewide_precincts as sp  # noqa: E402

LAYER = ("https://services5.arcgis.com/L6JGkSUcgPo1zSDi/arcgis/rest/services/"
         "cons_dis/FeatureServer/0")

COUNTIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "data", "app", "state-counties.json")

# Points sampled inside each county, as the state's county file draws it, and
# what share must land in a district. Measured on the 2026-10-16 fetch: the
# districts leave 67 km2 of 181,647 uncovered (0.04%), the most in Texas County
# (43 km2 of its 5,290, 0.8%), and overlap by 0.36 km2.
COVER_SAMPLES = 200
COVER_MIN_ALL = 99.5
COVER_MIN_COUNTY = 97.0
COVER_MAX_TWO = 0.5


def tidy(text):
    return " ".join(str(text).split()) if text is not None else ""


def district_name(raw):
    name = tidy(raw)
    if name.lower().endswith("conservation district"):
        return name
    for short in (" CD", " Cd"):
        if name.endswith(short):
            return name[:-len(short)] + " Conservation District"
    psb.fail(SPEC, "the map names a district %r, which is neither '<name> CD' nor a "
             "conservation district's full name; read it again" % name)


def read(props):
    ident = props.get("CONS_DIST2")
    if not isinstance(ident, int) or ident <= 0:
        psb.fail(SPEC, "CONS_DIST2 %r is not a positive whole number: %r" % (ident, props))
    return {"key": str(ident), "label": district_name(props.get("DIST_NAME"))}


def covers_the_state(feats):
    """Points sampled inside every county land in a district at least
    COVER_MIN_ALL percent of the time overall and COVER_MIN_COUNTY percent in
    each county, and in two districts at most COVER_MAX_TWO percent of the
    time. --watch reads the districts without their shapes, so the test runs
    on every build and every --check and is skipped there."""
    if any(f.get("geometry") is None for f in feats):
        return
    with open(COUNTIES_FILE, encoding="utf-8") as fh:
        counties = json.load(fh)["features"]
    index = psb.Index(feats)
    rng = random.Random(2026)
    total = covered = two = 0
    worst = (101.0, None)
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
        if pct < worst[0]:
            worst = (pct, c["properties"]["NAME"])
        if pct < COVER_MIN_COUNTY:
            psb.fail(SPEC, "only %.1f%% of points inside %s land in a conservation district "
                     "(need %.1f%%)" % (pct, c["properties"]["NAME"], COVER_MIN_COUNTY))
        total += n
        covered += hit
    pct_all = 100.0 * covered / total
    if pct_all < COVER_MIN_ALL:
        psb.fail(SPEC, "only %.2f%% of points inside the state land in a conservation "
                 "district (need %.1f%%)" % (pct_all, COVER_MIN_ALL))
    if 100.0 * two / total > COVER_MAX_TWO:
        psb.fail(SPEC, "%d of %d points inside the state land in two districts" % (two, total))
    print("coverage: %d of %d points inside the state (%.2f%%) land in a district, %d in two; "
          "lowest county %s %.1f%%" % (covered, total, pct_all, two, worst[1], worst[0]))


SPEC = psb.Spec(
    tag="ok",
    label="build_ok_conservation_districts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/ok/)",
    out_fields="CONS_DIST2,DIST_NAME",
    expect=84,
    expect_groups=84,
    read=read,
    out_file="ok-conservation-districts.json",
    group="key",
    group_nouns=("district", "districts"),
    card_noun="conservation district card",
    interval="4",
    measure_field="Shape__Area",
    multipart_records=22,
    extra_check=covers_the_state,
    card_claims=(
        "Oklahoma Conservation Commission's map of conservation districts",
        "three elected by the registered voters in the district",
    ),
    inside=(
        # the State Capitol, Oklahoma City: Oklahoma County's district
        (-97.50335, 35.49227, "56", "the State Capitol, Oklahoma County Conservation District"),
        # one of the ten Kingfisher pieces inside East Canadian's lines,
        # measured on the 2026-10-16 fetch
        (-97.97213, 35.75437, "87", "a Kingfisher County piece inside East Canadian's lines"),
    ),
    outside=(
        # the strip along the Kansas line in Texas County that the map leaves
        # in no district, measured on the 2026-10-16 fetch
        (-101.31920, 36.99620, "the strip along the Kansas line in Texas County"),
    ),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
