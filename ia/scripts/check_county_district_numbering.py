#!/usr/bin/env python3
"""Does a county's OWN district numbering match the layer this instance draws?

WHY THIS EXISTS. Every correspondence roster and every county-page roster in
this instance joins on a district NUMBER: the county says "District 3" and the
card shows that name on district 3 of
`ia/data/app/ia-supervisor-districts.json`, which is the Legislative Services
Agency's statewide supervisor-district layer. Nothing had ever checked that the
two numberings are the same numbering.

MEASURED 2026-10-01 ON PALO ALTO COUNTY: THEY ARE NOT. The county's own
supervisor-district map, sent by Auditor Carmen Moser and confirmed by her as
current, numbers its five districts in a completely different order from the
LSA layer -- county D1 is the layer's 4, D2 is 1, D3 is 2, D4 is 5 and D5 is 3.
Not one of the five agrees. So taking a county's district number as the layer's
district number would have put all five Palo Alto supervisors in the wrong
district, on a card a reader would have believed.

THE METHOD, so a second county can be done the same way. The county's map is a
vector PDF whose town labels carry their own positions, so it can be
georeferenced against those towns' published coordinates rather than traced:
seven incorporated places in the county (Ayrshire, Curlew, Cylinder,
Graettinger, Mallard, Rodman, Ruthven, each from TIGERweb's own place
centroids) fit a similarity transform -- scale, rotation, translation and
nothing else, so five control points would already over-determine it -- at
0.219 km rms with +0.31 degrees of rotation. Each of the map's own D1..D5
labels is then carried through that transform and tested for which of the
layer's polygons CONTAINS it.

WHAT MAKES THE ANSWER TRUSTWORTHY IS THE BIJECTION, NOT THE MARGINS. The five
labels land in five DISTINCT polygons, so no polygon is left unnamed and none
is named twice; the weakest margin is 0.65 km from its own boundary, which is
only about twice the fit's worst residual, and it is protected by every other
label being spoken for rather than by its own distance. Leave-one-out over the
seven control points moves nothing: all seven refits return the same pairing at
0.159-0.236 km rms.

TWO CONTROL POINTS ARE DELIBERATELY EXCLUDED AND THAT IS A MEASUREMENT. The map
carries a second, larger label for Emmetsburg and for West Bend, and those two
are not at the town point -- including them takes the fit from 0.219 km to
2.833 km rms and moves the pairing. A control point that disagrees with seven
others by an order of magnitude is a label of something else, not a town that
moved: Palo Alto has an Emmetsburg and a West Bend TOWNSHIP as well as a city.
A FIT THAT GETS WORSE WHEN YOU ADD DATA IS TELLING YOU WHICH DATA IS WRONG.

NOTHING IS TAKEN FROM TEXT ORDER. The legend's pairing of names to D-numbers is
read from the text objects' own geometry: five columns whose name centre sits a
constant 36.18-38.34 pt left of its D-label centre, against a column pitch of
75.8 pt, so every other pairing of the five names displaces at least one name by
a whole column. The names themselves still come from the gated officer roster;
the letter only ever says which district each person holds.

THE OBVIOUS ALTERNATIVE EXPLANATION WAS RULED OUT BY THE COUNTY, NOT BY
REASONING. If Palo Alto had redrawn its districts after the 2020 census, this
map would be the OLD plan and the test would have compared one plan's labels
against another plan's shapes, which says nothing about numbering. The map
carries no date in its own content; the only "2020" anywhere is in the filename
its attachment arrived under, and nothing is taken from a filename. Asked
directly, Auditor Moser answered on 2026-10-01: "the 5 supervisors are current.
The documents are labeled 2020 due to redistricting, but both are current." So
the label is the census the plan was drawn to, and this is two numberings of one
plan. ASK THE PUBLISHER WHEN A DOCUMENT'S VINTAGE DECIDES WHAT A MEASUREMENT
MEANS: no other route was open here, because the district areas are a raster
image -- the whole page has ONE stroke operator and its five vector fills are
the legend swatches -- and paloaltocountyia.gov is unreachable from this
network.

HOWARD COUNTY IS THE SECOND COUNTY AND IT AGREES, SO THIS IS A PER-COUNTY FACT
RATHER THAN A FLEET-WIDE ERROR. It is also the CHEAP shape and the one to reach
for first: its own board page names a residence TOWN beside each of its three
supervisors, so the test is one page read and three point-in-polygon tests, with
no map, no PDF and no georeferencing. All three towns -- the county seat and two
others, far apart and each wholly inside one district -- land in the district the
county numbers them. Only the TOWN is recorded: a supervisor's street address is
never written down here or anywhere else in this repository, which is why
TOWN_COUNTIES carries places and not people.

THIS SCRIPT IS THE MEASUREMENT AND NOT A GATE. The map route needs a county map,
which most counties do not publish; the town route needs a county page that names
a place per district. Neither can be run for the fleet, and the script says
nothing about a county it has not been pointed at. The question it leaves open is
the important one: 21 counties already shipping a member keyed to a district took
the same numbering on trust, and one county agreeing does not clear the others.
Where no county page names a place, the general instrument is certified
per-precinct returns from the Secretary of State -- every one of Iowa's 40
districted counties is PLAN 3 single-member, so a district's contest appears only
in its own precincts and the returns compose it.
"""
import json
import math
import sys

# Palo Alto County, the one county measured so far. PDF label positions are in
# the page's own points, read out of the content stream's Tm matrices.
MAP_LABELS = {1: (228.5, 195.7), 2: (286.1, 450.8), 3: (114.5, 481.8),
              4: (189.4, 626.7), 5: (374.4, 466.6)}
# (pdf x, pdf y) -> (lat, lon), the lat/lon being TIGERweb place centroids.
CONTROLS = {
    "Ayrshire":    ((116.3, 327.4), (43.0396124, -94.8339700)),
    "Curlew":      ((224.4, 233.8), (42.9796992, -94.7378004)),
    "Cylinder":    ((436.7, 401.5), (43.0902504, -94.5512293)),
    "Graettinger": ((210.4, 640.8), (43.2370202, -94.7504693)),
    "Mallard":     ((284.4, 170.4), (42.9393938, -94.6833939)),
    "Rodman":      ((469.8, 307.2), (43.0265836, -94.5273686)),
    "Ruthven":     (( 42.1, 469.2), (43.1300541, -94.8986909)),
}
COUNTY = "Palo Alto"
LAYER = "ia/data/app/ia-supervisor-districts.json"
# The pairing this script measured, so a rerun that disagrees is visible rather
# than quietly replacing it.
MEASURED = {1: "4", 2: "1", 3: "2", 4: "5", 5: "3"}

# The second county, and the CHEAP shape: where a county's own board page names
# a residence TOWN beside each supervisor, no map and no georeferencing are
# needed -- the town's own published centroid is the test point. Only the town
# is recorded. A supervisor's street address is never written down here or
# anywhere else in this repository, which is why this table carries places and
# not people. Towns are TIGERweb place centroids; the district is what the
# county's own page says.
TOWN_COUNTIES = {
    "Howard": {
        "source": "https://howardcounty.iowa.gov/board-of-supervisors/",
        "towns": {
            "Cresco":       ("1", (43.3717458, -92.1162868)),
            "Lime Springs": ("2", (43.4498991, -92.2840640)),
            "Riceville":    ("3", (43.3619761, -92.5538710)),
        },
    },
}

LAT0 = 43.1
KX = math.cos(math.radians(LAT0)) * 111.320
KY = 111.0


def to_km(lat, lon):
    return lon * KX, lat * KY


def fit(keys):
    """Best similarity transform from page points to kilometres."""
    src = [CONTROLS[k][0] for k in keys]
    dst = [to_km(*CONTROLS[k][1]) for k in keys]
    n = len(src)
    px = sum(p[0] for p in src) / n
    py = sum(p[1] for p in src) / n
    qx = sum(q[0] for q in dst) / n
    qy = sum(q[1] for q in dst) / n
    a = b = den = 0.0
    for (x, y), (u, v) in zip(src, dst):
        x, y, u, v = x - px, y - py, u - qx, v - qy
        a += x * u + y * v
        b += x * v - y * u
        den += x * x + y * y
    a, b = a / den, b / den

    def apply(x, y):
        X, Y = x - px, y - py
        return a * X - b * Y + qx, b * X + a * Y + qy

    res = [math.hypot(*(lambda t, q: (t[0] - q[0], t[1] - q[1]))(apply(*p), q))
           for p, q in zip(src, dst)]
    rms = (sum(r * r for r in res) / n) ** 0.5
    return apply, rms, math.degrees(math.atan2(b, a))


def polygons(county=COUNTY, expect=None):
    with open(LAYER, encoding="utf-8") as f:
        g = json.load(f)
    out = {f["properties"]["DISTRICT"]: f["geometry"] for f in g["features"]
           if f["properties"].get("COUNTY") == county}
    if len(out) != (expect if expect is not None else len(MAP_LABELS)):
        sys.exit("check-county-district-numbering: FAIL -- %s draws %d district(s) "
                 "for %s and the map carries %d label(s)"
                 % (LAYER, len(out), county,
                    expect if expect is not None else len(MAP_LABELS)))
    return out


def contains(lon, lat, geom):
    parts = ([geom["coordinates"]] if geom["type"] == "Polygon"
             else geom["coordinates"])
    for part in parts:
        odd = False
        for ring in part:
            for i in range(len(ring) - 1):
                x1, y1 = ring[i][:2]
                x2, y2 = ring[i + 1][:2]
                if (y1 > lat) != (y2 > lat):
                    if lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                        odd = not odd
        if odd:
            return True
    return False


def place(apply, polys):
    out = {}
    for label, (x, y) in sorted(MAP_LABELS.items()):
        xk, yk = apply(x, y)
        lat, lon = yk / KY, xk / KX
        hit = [d for d, geom in polys.items() if contains(lon, lat, geom)]
        out[label] = hit[0] if len(hit) == 1 else "/".join(hit) or "none"
    return out


def check_towns():
    """The town route: one page read, no map. Returns the number of counties
    whose own numbering agrees with this layer's."""
    agreeing = 0
    for county, rec in sorted(TOWN_COUNTIES.items()):
        towns = rec["towns"]
        polys = polygons(county, expect=len(towns))
        same = 0
        for town, (claimed, (lat, lon)) in sorted(towns.items()):
            hit = [d for d, geom in polys.items() if contains(lon, lat, geom)]
            got = hit[0] if len(hit) == 1 else "/".join(hit) or "none"
            if got == claimed:
                same += 1
            print("  %s: %s sits in this layer's district %s; the county puts "
                  "its District %s there" % (county, town, got, claimed))
        if same == len(towns):
            agreeing += 1
        print("check-county-district-numbering: %s -- %d of %d town(s) land in "
              "the district the county numbers them (%s)"
              % (county, same, len(towns), rec["source"]))
    return agreeing


def main():
    polys = polygons()
    apply, rms, rot = fit(list(CONTROLS))
    got = place(apply, polys)
    print("check-county-district-numbering: %s -- %d control point(s), "
          "rms %.3f km, rotation %+.2f deg" % (COUNTY, len(CONTROLS), rms, rot))
    for label in sorted(got):
        print("  the county's District %s is this layer's district %s"
              % (label, got[label]))
    moved = sum(1 for k in got if got[k] != MEASURED.get(k))
    # Leave-one-out: a pairing that depends on one town is not a pairing.
    unstable = []
    for drop in CONTROLS:
        keys = [k for k in CONTROLS if k != drop]
        a2, r2, _ = fit(keys)
        if place(a2, polys) != got:
            unstable.append(drop)
    if unstable:
        sys.exit("check-county-district-numbering: FAIL -- dropping %s moves the "
                 "pairing, so it rests on one control point rather than on the fit"
                 % ", ".join(sorted(unstable)))
    if moved:
        sys.exit("check-county-district-numbering: FAIL -- %d of %d label(s) "
                 "disagree with the recorded pairing %s. Re-read the map before "
                 "changing the record." % (moved, len(got), MEASURED))
    identity = [k for k in got if got[k] == str(k)]
    print("check-county-district-numbering: OK -- matches the recorded pairing, "
          "stable under leave-one-out over all %d control point(s); %d of %d "
          "district number(s) agree between the county and this layer"
          % (len(CONTROLS), len(identity), len(got)))
    check_towns()


if __name__ == "__main__":
    main()
