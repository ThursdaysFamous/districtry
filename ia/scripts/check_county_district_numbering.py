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

THE PRECINCT ROUTE IS THE BEST OF THE THREE AND IT NEEDS NO FETCH AT ALL BEYOND
THE COUNTY'S OWN PAGE. Where a county names its own PRECINCTS beside each
supervisor -- Lyon County writes "District 1 - Precinct 9,10" in each member's
own title -- the test runs entirely against two files this instance already
ships: `ia-precincts.json` names every precinct in the county, and each
precinct's interior is sampled on a grid and tested against the supervisor
districts. It beats the town route on completeness, because a county's precincts
PARTITION it while its towns do not: Lyon has no town lying wholly inside its
fifth district, so the towns can only ever speak for four of five, while all ten
precincts are each wholly inside one district and every district is spoken for.

ITS ONE WEAKNESS IS NAMED RATHER THAN IGNORED: the precinct layer and the
supervisor layer come from the SAME publisher, so the precinct route cannot by
itself rule out that publisher having numbered both in its own order. What rules
it out is that a precinct's NAME is a filed name rather than an ordering, and
that the names carry towns -- so the towns' own census centroids are an
independent second witness, and on Lyon they agree with the precinct route on
every pairing they can speak to. RUN BOTH WHERE A PRECINCT NAME CARRIES A TOWN.

LINN COUNTY IS THE FIRST COUNTY MEASURED FROM CERTIFIED PER-PRECINCT RETURNS,
AND IT IS A NEGATIVE: THE TWO SIDES ARE NOT ONE PLAN UNDER TWO LABELS. Iowa's
Secretary of State publishes results through Clarity, and a Clarity archive's
`reports/detailxml.zip` carries every contest broken out per precinct -- so a
single-member district's contest names exactly the precincts entitled to vote in
it. Linn's own certified 2024 Primary (electionresults.iowa.gov/IA/Linn/121565/,
version 342004) runs one board contest, District 3, and all three party ballots
agree on the same 42 reporting units: 41 named precincts plus an Absentee
bucket, every one of the 41 present in this instance's shipped precinct layer.
Placed against the layer's three Linn districts, 36 of the 41 land in the
layer's district 3 and FIVE land wholly inside its district 2 -- Cedar Rapids
01, 04, 07 and 27 and Hiawatha 03, each by 166 to 308 interior sample cells with
no district-3 presence at all, which is a different line and not a digitisation
sliver. The layer's district 3 is a STRICT SUBSET of the county's District 3,
36 of 41 with nothing the other way, so no relabelling can reconcile them and
Linn stays withheld. This is the Butler shape reached by a different route, and
what it wants is the county's own current plan rather than another derivation.

THE ROUTE IS EXHAUSTED FOR IOWA AND THAT IS A MEASUREMENT RATHER THAN A GUESS.
Sweeping all 99 counties' Clarity election indexes on 2026-10-01, FIVE answer
with any election at all -- Henry, Jasper, Lee, Linn and Page -- and of those
only Linn's 2024 Primary carries a board contest; the STATE-level archive
(electionresults.iowa.gov/IA/) carries federal and statewide offices only, with
no board contest at any election and no precinct breakdown, which is the same
shape as Illinois's state election archive. So certified returns settle one
Iowa county and cannot settle the other sixteen.

THIS SCRIPT IS THE MEASUREMENT AND NOT A GATE. The map route needs a county map,
which most counties do not publish; the town route needs a county page that names
a place per district; the precinct route needs one that names precincts. None can
be run for the fleet, and the script says nothing about a county it has not been
pointed at. The question it leaves open is
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

# Linn County, measured from its own certified returns and REFUSED. The 41 named
# precincts the county's 2024 Primary reports under its County Board of
# Supervisors District 3 contest, all three party ballots agreeing. Recorded so
# the comparison below can be re-run offline: the external document is read
# once, here, and everything else is the shipped tree.
LINN_D3_PRECINCTS = [
    "Bertram Township",
    "Boulder-Buffalo",
    "Brown-Linn",
    "Cedar Rapids 01",
    "Cedar Rapids 04",
    "Cedar Rapids 07",
    "Cedar Rapids 27",
    "Fayette Township",
    "Franklin Township",
    "Grant Township",
    "Hiawatha 03",
    "Jackson Township",
    "Maine Township",
    "Marion 01",
    "Marion 02",
    "Marion 03",
    "Marion 04",
    "Marion 05",
    "Marion 06",
    "Marion 07",
    "Marion 08",
    "Marion 09",
    "Marion 10",
    "Marion 11",
    "Marion 12",
    "Marion 13",
    "Marion 14",
    "Marion 15",
    "Marion 16",
    "Marion 17",
    "Marion 18",
    "Marion Township 01",
    "Marion Township 02",
    "Monroe Township 01",
    "Monroe Township 02",
    "Mount Vernon 01",
    "Mount Vernon 02",
    "Otter Creek Township",
    "Robins",
    "Spring Grove Township",
    "Washington Township"
]
# The five the county puts in District 3 and the layer draws inside its own
# district 2. A STRICT SUBSET in one direction and nothing in the other, which
# is what rules out a renumbering.
LINN_DISAGREE = ("Cedar Rapids 01", "Cedar Rapids 04", "Cedar Rapids 07",
                 "Cedar Rapids 27", "Hiawatha 03")
PRECINCT_LAYER = "ia/data/app/ia-precincts.json"

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
#
# MONONA IS THE SAME ROUTE WITH A COMPLETE PARTITION BEHIND IT, and it is the
# strongest witness this route has produced. Its own supervisor-district map
# (mononacountyiowa.gov/files/supervisors/supervisor_district_map_38766.pdf) is
# a vector PDF whose lower half is TEXT: it names, per district, every township
# and city the district contains, so nothing on the drawing is read at all --
# not a fill, not a label position, not a pixel. The nineteen townships and the
# city of Onawa it lists are exactly the twenty county subdivisions TIGERweb
# publishes for the county, so the county's own statement partitions the county
# with nothing left over and nothing named twice, and every one of the twenty
# interior points lands in the district this table pairs it with. The map's own
# content dates itself ("Revised after 2020 Census") rather than its filename,
# and its legend names the same three supervisors in the same three districts
# as the gated roster, which is what makes it the plan in force rather than a
# superseded one.
TOWN_COUNTIES = {
    "Howard": {
        "source": "https://howardcounty.iowa.gov/board-of-supervisors/",
        "districts": 3,
        "towns": {
            "Cresco":       ("1", (43.3717458, -92.1162868)),
            "Lime Springs": ("2", (43.4498991, -92.2840640)),
            "Riceville":    ("3", (43.3619761, -92.5538710)),
        },
    },
    "Monona": {
        "source": "https://mononacountyiowa.gov/files/supervisors/"
                  "supervisor_district_map_38766.pdf",
        "districts": 3,
        "towns": {
            "Ashton":        ("1", (42.0889412, -96.0903664)),
            "Belvidere":     ("1", (41.9862474, -95.9663895)),
            "Center":        ("1", (42.0925902, -95.8262991)),
            "Fairview":      ("1", (42.1803438, -96.2970697)),
            "Franklin":      ("1", (41.9905909, -96.0935195)),
            "Grant":         ("1", (42.1754833, -95.9450839)),
            "Kennebec":      ("1", (42.0769620, -95.9732708)),
            "Lake":          ("1", (42.1642791, -96.2040485)),
            "Lincoln":       ("1", (42.0773247, -96.2040064)),
            "Sherman":       ("1", (41.8982190, -96.0832369)),
            "Sioux":         ("1", (41.9138232, -95.9535027)),
            "West Fork":     ("1", (42.1797571, -96.0908998)),
            "Cooper":        ("2", (42.1621131, -95.7232194)),
            "Jordan":        ("2", (41.9976634, -95.8433519)),
            "Maple":         ("2", (42.1682353, -95.8542875)),
            "Soldier":       ("2", (42.0044272, -95.7404976)),
            "Spring Valley": ("2", (41.9053936, -95.8444687)),
            "St. Clair":     ("2", (42.0778832, -95.7288008)),
            "Willow":        ("2", (41.8963162, -95.7288486)),
            "Onawa":         ("3", (42.0264757, -96.0909168)),
        },
    },
}

# THE PRECINCT ROUTE. Where a county names its own PRECINCTS beside each
# supervisor, the test needs nothing but two files this instance already ships.
# Keys are the precinct layer's own names; values are the district the COUNTY
# puts that precinct in. A county's precincts partition it, so unlike the town
# route this can speak for every district.
PRECINCT_COUNTIES = {
    "Lyon": {
        "source": "https://lyoncounty.iowa.gov/supervisors/",
        "districts": 5,
        # The county writes the precinct numbers into each member's own title:
        # "District 1 - Precinct 9,10", and so on through all ten precincts.
        "precincts": {
            "Pct 9 Lester":        "1",
            "Pct 10 Larchwood":    "1",
            "Pct 6 Inwood":        "2",
            "Pct 7 Logan S":       "2",
            "Pct 8 Logan N":       "2",
            "Pct 1 George":        "3",
            "Pct 2 Little Rock":   "3",
            "Pct 4 Rock Rapids S": "4",
            "Pct 5 Doon":          "4",
            "Pct 3 Rock Rapids N": "5",
        },
        # The independent half: six towns each lying wholly inside one of those
        # precincts, from TIGERweb's own place centroids. They can only speak
        # for four of the five districts -- Rock Rapids is split between the
        # county's District 4 and 5, so no town names either -- which is why
        # they corroborate the precincts rather than standing alone.
        "towns": {
            "Lester":      ("1", (43.4402929, -96.3314163)),
            "Larchwood":   ("1", (43.4546482, -96.4363405)),
            "Inwood":      ("2", (43.3092095, -96.4343566)),
            "George":      ("3", (43.3418726, -96.0032567)),
            "Little Rock": ("3", (43.4470661, -95.8804342)),
            "Doon":        ("4", (43.2789717, -96.2329074)),
        },
    },
}

PRECINCTS = "ia/data/app/ia-precincts.json"
GRID = 40

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
    """The town route: one page read, no map. Prints the pairing each county's
    own places imply and whether that pairing is a clean bijection -- which is
    what makes it trustworthy, exactly as the map route's bijection is. Returns
    the number of counties whose own numbering agrees with this layer's."""
    agreeing = 0
    for county, rec in sorted(TOWN_COUNTIES.items()):
        towns = rec["towns"]
        polys = polygons(county, expect=rec["districts"])
        implied = {}
        bad = []
        for town, (claimed, (lat, lon)) in sorted(towns.items()):
            hit = [d for d, geom in polys.items() if contains(lon, lat, geom)]
            got = hit[0] if len(hit) == 1 else "/".join(hit) or "none"
            print("  %s: %s sits in this layer's district %s; the county puts "
                  "its District %s there" % (county, town, got, claimed))
            if implied.setdefault(claimed, got) != got:
                bad.append("the county's District %s reaches this layer's %s "
                           "and %s" % (claimed, implied[claimed], got))
        if len(set(implied.values())) != len(implied):
            bad.append("two of the county's districts land in one of this "
                       "layer's")
        if len(implied) != rec["districts"]:
            bad.append("only %d of the county's %d district(s) are spoken for"
                       % (len(implied), rec["districts"]))
        pairing = ", ".join("%s->%s" % (c, implied[c]) for c in sorted(implied))
        if bad:
            print("check-county-district-numbering: %s -- NO PAIRING: %s (%s)"
                  % (county, "; ".join(bad), rec["source"]))
            continue
        same = sum(1 for c, d in implied.items() if c == d)
        if same == len(implied):
            agreeing += 1
        print("check-county-district-numbering: %s -- %d place(s) agree on "
              "county->layer %s, %d of %d number(s) the same (%s)"
              % (county, len(towns), pairing, same, len(implied), rec["source"]))
    return agreeing


def interior_points(geom, grid=GRID):
    """Points provably inside a polygon: a grid over its own bounding box,
    kept only where the point-in-polygon test says inside."""
    parts = ([geom["coordinates"]] if geom["type"] == "Polygon"
             else geom["coordinates"])
    xs = [c[0] for part in parts for ring in part for c in ring]
    ys = [c[1] for part in parts for ring in part for c in ring]
    out = []
    for i in range(1, grid):
        x = min(xs) + (max(xs) - min(xs)) * i / grid
        for j in range(1, grid):
            y = min(ys) + (max(ys) - min(ys)) * j / grid
            if contains(x, y, geom):
                out.append((x, y))
    return out


def check_precincts():
    """The precinct route: the county's own page names its precincts per
    district, and both the precincts and the districts are files this instance
    already ships. Returns the number of counties whose own numbering agrees
    with this layer's."""
    with open(PRECINCTS, encoding="utf-8") as f:
        pfile = json.load(f)
    agreeing = 0
    for county, rec in sorted(PRECINCT_COUNTIES.items()):
        polys = polygons(county, expect=rec["districts"])
        shipped = {f["properties"]["name"]: f["geometry"]
                   for f in pfile["features"]
                   if f["properties"].get("county") == county}
        claimed = rec["precincts"]
        missing = sorted(set(claimed) - set(shipped))
        extra = sorted(set(shipped) - set(claimed))
        if missing or extra:
            print("check-county-district-numbering: %s -- NO PAIRING: the "
                  "county's list and the shipped precincts are not the same "
                  "set (county only: %s; layer only: %s) (%s)"
                  % (county, ", ".join(missing) or "none",
                     ", ".join(extra) or "none", rec["source"]))
            continue
        implied = {}
        bad = []
        for name in sorted(claimed, key=lambda n: claimed[n]):
            pts = interior_points(shipped[name])
            hits = {}
            for x, y in pts:
                hit = [d for d, g in polys.items() if contains(x, y, g)]
                key = hit[0] if len(hit) == 1 else "/".join(hit) or "none"
                hits[key] = hits.get(key, 0) + 1
            real = {k: v for k, v in hits.items() if k != "none"}
            got = max(real, key=real.get) if real else "none"
            # A precinct straddling two districts would be the county and the
            # layer describing different plans rather than numbering one -- the
            # Butler case -- so it is reported rather than resolved by majority.
            spread = sorted(k for k in real if k != got)
            print("  %s: %s lies in this layer's district %s%s; the county puts "
                  "its District %s there (%d interior point(s))"
                  % (county, name, got,
                     " AND " + ", ".join(spread) if spread else "",
                     claimed[name], len(pts)))
            if spread:
                bad.append("%s straddles this layer's %s"
                           % (name, ", ".join([got] + spread)))
            if implied.setdefault(claimed[name], got) != got:
                bad.append("the county's District %s reaches this layer's %s "
                           "and %s" % (claimed[name], implied[claimed[name]], got))
        if len(set(implied.values())) != len(implied):
            bad.append("two of the county's districts land in one of this "
                       "layer's")
        if len(implied) != rec["districts"]:
            bad.append("only %d of the county's %d district(s) are spoken for"
                       % (len(implied), rec["districts"]))
        pairing = ", ".join("%s->%s" % (c, implied[c])
                            for c in sorted(implied, key=int))
        if bad:
            print("check-county-district-numbering: %s -- NO PAIRING: %s (%s)"
                  % (county, "; ".join(bad), rec["source"]))
            continue
        same = sum(1 for c, d in implied.items() if c == d)
        if same == len(implied):
            agreeing += 1
        print("check-county-district-numbering: %s -- %d precinct(s), each "
              "wholly inside one district, agree on county->layer %s, %d of %d "
              "number(s) the same (%s)"
              % (county, len(claimed), pairing, same, len(implied),
                 rec["source"]))
        # The independent half. The towns cannot speak for every district, so
        # they confirm or contradict rather than deciding.
        towns = rec.get("towns") or {}
        if towns:
            agree = []
            for town, (cd, (lat, lon)) in sorted(towns.items()):
                hit = [d for d, g in polys.items() if contains(lon, lat, g)]
                got = hit[0] if len(hit) == 1 else "/".join(hit) or "none"
                agree.append(got == implied.get(cd))
                print("  %s: %s sits in this layer's district %s; the precincts "
                      "put the county's District %s at %s"
                      % (county, town, got, cd, implied.get(cd)))
            print("check-county-district-numbering: %s -- %d of %d town(s) "
                  "independently agree with the precinct pairing"
                  % (county, sum(agree), len(agree)))
    return agreeing


def precinct_majority(county, polys, grid=18):
    """Which of `polys` each of the county's shipped precincts mostly lies in.

    A precinct's own interior is sampled on a grid and each sample tested
    against every district, so a precinct is placed by where its GROUND is
    rather than by one representative point -- which is what lets a genuine
    split be told from a digitisation sliver.
    """
    with open(PRECINCT_LAYER, encoding="utf-8") as f:
        g = json.load(f)
    out = {}
    for feat in g["features"]:
        if feat["properties"].get("county") != county:
            continue
        geom = feat["geometry"]
        parts = ([geom["coordinates"]] if geom["type"] == "Polygon"
                 else geom["coordinates"])
        xs = [c[0] for part in parts for ring in part for c in ring]
        ys = [c[1] for part in parts for ring in part for c in ring]
        hits = {}
        for i in range(grid):
            for j in range(grid):
                lon = min(xs) + (max(xs) - min(xs)) * (i + 0.5) / grid
                lat = min(ys) + (max(ys) - min(ys)) * (j + 0.5) / grid
                if not contains(lon, lat, geom):
                    continue
                for d, dgeom in polys.items():
                    if contains(lon, lat, dgeom):
                        hits[d] = hits.get(d, 0) + 1
        if hits:
            out[feat["properties"]["name"]] = max(hits, key=hits.get)
    return out


def check_linn():
    """Re-prove Linn's REFUSAL offline, against the shipped tree.

    The county's own certified returns are read once, into
    LINN_D3_PRECINCTS. Everything here is this instance's own files, so the
    check fails the day either layer is redrawn -- which is exactly when
    somebody should re-read the county's plan rather than trust this record.

    THE SUBSET IS EXACT IN BOTH DIRECTIONS, which is what rules out a
    renumbering rather than merely suggesting one: the layer's district 3
    holds 36 precincts, every one of them among the county's 41, and there is
    no precinct anywhere in the layer's district 3 that the county's District 3
    leaves out. Broken on purpose three ways it fails three ways -- a
    disagreeing precinct dropped from the record, a precinct added that the
    layer puts in another district, and a precinct named that this instance
    does not draw at all.
    """
    polys = polygons("Linn", expect=3)
    mostly = precinct_majority("Linn", polys)
    missing = [n for n in LINN_D3_PRECINCTS if n not in mostly]
    if missing:
        sys.exit("check-county-district-numbering: FAIL -- Linn's certified "
                 "District 3 names %d precinct(s) this instance no longer "
                 "draws: %s" % (len(missing), ", ".join(sorted(missing))))
    canvass = set(LINN_D3_PRECINCTS)
    layer3 = {n for n, d in mostly.items() if d == "3"}
    extra = sorted(layer3 - canvass)
    disagree = sorted(canvass - layer3)
    if extra:
        sys.exit("check-county-district-numbering: FAIL -- the layer's Linn "
                 "district 3 is no longer a subset of the county's District 3; "
                 "it now also holds %s. The two plans have moved, so re-read "
                 "the county's own plan." % ", ".join(extra))
    if tuple(disagree) != LINN_DISAGREE:
        sys.exit("check-county-district-numbering: FAIL -- Linn's disagreement "
                 "has moved: %s, against the recorded %s"
                 % (", ".join(disagree), ", ".join(LINN_DISAGREE)))
    print("check-county-district-numbering: Linn -- %d of %d precinct(s) the "
          "county certifies in its District 3 land in this layer's district 3, "
          "and %d land wholly inside its district 2 (%s). The layer's district "
          "3 is a strict subset of the county's, so this is two plans and not "
          "two numberings; Linn stays withheld."
          % (len(canvass) - len(disagree), len(canvass), len(disagree),
             ", ".join(disagree)))


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
    check_precincts()
    check_linn()


if __name__ == "__main__":
    main()
