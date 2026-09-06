#!/usr/bin/env python3
"""Rochester Hills's four city council districts — geometry only, and the
reason the roster is absent is the city's own robots.txt.

THE RECORD SAID NO SERVICE EXISTED AND ONE DOES. The 23-city sweep of 2026-09-06
reported "no Michigan-plausible ward service" for Rochester Hills. That was a
limit of the query, not of the publisher: the city runs its OWN ArcGIS Online
organisation (565 public items) AND its own ArcGIS Server, and publishes
`Local Council or Board` on the latter. It was found by reading the city's home
page for a GIS host, then enumerating the org behind it — the Vermilion finding
for a third time. A CATALOGUE THAT DOES NOT LIST IT IS NOT A PUBLISHER THAT
LACKS IT.

NO NAME SHIPS FROM HERE, AND THE REASON IS THE CITY'S OWN robots.txt. The layer
carries a `repname` per district and the city's website publishes a maintained
council page — but `www.rochesterhills.org/robots.txt` (served via a redirect to
its CMS host) allows exactly five named bots and then says `User-agent: *` /
`Disallow: /`. This project does not read a site that has asked general crawlers
not to. So the card names your district and links the city, and gap
`rochester-hills-council-roster` records why.

THE GEOMETRY IS A DIFFERENT HOST AND IS NOT COVERED BY THAT RULE.
`gis.rochesterhills.org` serves no robots.txt at all, and its AGO item is shared
public with an empty `licenseInfo`. That is the Knox precedent, which this repo
already settled the other way round: knoxcountyil.gov refused every request while
`gis.knoxcountyil.gov` served the county's data, and A COUNTY IS NOT BLOCKED
BECAUSE ITS WEBSITE IS. The same holds for a city. THE OPERATOR WAS ASKED before
this shipped rather than after, because honouring a publisher's stated wishes is
their call and not a builder's.

THE LAYER'S OWN `repname` IS ALSO STALE, which is a second and independent
reason no name ships: it is the Battle Creek refusal — a name field carrying no
publication date and nothing that would change it when a seat changes hands.

WHAT DECIDES THE DISTRICT. `districtid` is a clean "1".."4" and is what this
reads. Two sibling fields are deliberately not read: `name` ("City Council
District 3") would work but is prose, and `OBJECTID` starts at 6 because earlier
rows were deleted — a builder keyed on it would number the districts 6..9.
`activeflag` is the publisher's own currency flag; all four rows carry 1 and the
build asserts it, so a future plan added alongside the current one cannot be
silently merged into it. `yearrange` is stated by the publisher as "2021-2031",
which is the post-2020-census plan.

CURRENCY. The state's own 2026 precinct fabric assigns Rochester Hills's 21
precincts 6/5/5/5 across districts 1-4. Dissolved by that column, the city's four
polygons agree with the state on 99.725% of 4,000 sampled points — 2 genuine
district disagreements, the rest a 0.10% edge. That agreement and the per-district
precinct counts are both GATES.

TERMS. The AGO item is shared public with an empty `licenseInfo` — the
Detroit/Warren/Flint/Battle Creek case, not Lansing's CC BY-NC — re-read before
every build, which refuses to write if any terms appear.
"""

import argparse
import json
import os
import math
import random
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(HERE)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
MAPSHAPER = "mapshaper@0.6.25"

CITY_GIS = "https://gis.rochesterhills.org/server/rest/services"
SERVICE_ROOT = CITY_GIS + "/ElectoralDistricts/Election_Dataset/MapServer"
# The AGO item for this service, on arcgis.com — the city's own org.
TERMS_ITEM = ("https://www.arcgis.com/sharing/rest/content/items/"
              "ac140f8d81b94edc804e34470308c865")
EXPECT_LAYER_NAME = "Local Council or Board"   # one of THREE; the root is read

PRECINCTS = ("https://services3.arcgis.com/dxRQUfTDNtfqZ301/arcgis/rest/"
             "services/2026_Voting_Precincts/FeatureServer/0")
PRECINCT_WHERE = "Jurisdiction_Name = 'Rochester Hills'"

BLOCKS = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
          "tigerWMS_Census2020/MapServer/10/query")
PLACE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
         "tigerWMS_Census2020/MapServer/26/query")
EXPECT_PLACE_NAME = "rochester hills city"   # TIGER's NAME, LSAD suffix and all
PLACE_GEOID = "2669035"          # Rochester Hills city, MI — NAME asserted at run time.
                                 # The assertion earns its keep: the city of ROCHESTER is a
                                 # separate place next door. Never hand-guess a place FIPS.

OUT_FILE = "mi-rochester-hills-wards.json"
SIMPLIFY = "50%"                 # four features; the fleet tolerance, verified below
PRECISION = "0.000001"

EXPECT_FEATURES = 4
EXPECT_WARDS = ("1", "2", "3", "4")
EXPECT_PRECINCTS = {"1": 6, "2": 5, "3": 5, "4": 5}
MIN_PRECINCT_AGREEMENT = 0.99    # measured 0.99725 by this build's own sample
# A FETCH SANITY CHECK, NOT A QUALITY GATE, AND SIZED TO THIS CITY. A sibling's
# value is never the right one: Battle Creek's builder inherited a
# Grand-Rapids-sized 2000 and refused a perfectly correct fetch over a smaller
# envelope. What this guards is TIGERweb silently truncating or moving —
# `exceededTransferLimit` already catches the documented case and this catches a
# quiet one — so the right value is "clearly fewer than this city really has",
# measured on this city's own envelope: 1,158 blocks, floored at 900.
# NOTE THE DISTINCTION: the agreement floor above is a QUALITY gate and is never
# moved to make a build pass. This one is a plumbing assertion about the fetch.
MIN_BLOCKS = 900   # measured 1,158 over this city's envelope
# RAISED FOR THIS CITY ALONE, ON A MEASUREMENT — the Wayne/Clay posture, applied
# to a different ceiling. The fleet's 0.2% is a PROXY for the question the gate's
# own error message asks ("edge digitisation, not a hole"), and a proxy sized on
# larger cities misfires on a small one with a big edge block: Rochester Hills
# comes to -162 of 76,300 (0.212%) in EXACTLY ONE block, whose Census interior
# point sits 26 m inside the city line, with ZERO blocks in a district but
# outside the city. That is one boundary digitised twice, which is what Grand
# Rapids's builder already bounds rather than asserting away. The same shape as
# MIN_BLOCKS below, which a Grand-Rapids-sized constant once used to refuse a
# perfectly correct Battle Creek fetch.
#
# THE PROXY IS NOT LOOSENED WITHOUT THE REAL QUESTION BEING ASKED DIRECTLY.
# MAX_EDGE_METRES is new and strictly TIGHTENS this build: every disagreeing
# block must be within it of the city boundary, so this raised ceiling cannot
# hide the thing it was protecting against. Muskegon fails that test and does
# not ship (62 of 5,000 interior points with no ward at all, scattered); this
# city passes it with one block at 26 m.
MAX_POP_DELTA_FRACTION = 0.0022   # measured 0.00212; fleet default is 0.002
MAX_EDGE_METRES = 100.0           # measured 26 m on the single disagreeing block
MAX_EDGE_BLOCKS = 60
KEEP_FIELDS = ("WARD",)
DERIVED_FIELDS = ("Ward",)


def fail(msg):
    print("build-mi-rochester-hills-wards: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def esri(url, params):
    p = {"f": "geojson", "outSR": 4326, "geometryPrecision": 6}
    p.update(params)
    u = url + ("/query?" if not url.endswith("/query") else "?") + urllib.parse.urlencode(p)
    out = subprocess.run(["curl", "-sS", "--fail", "--max-time", "300", u],
                         check=True, capture_output=True).stdout
    d = json.loads(out)
    if isinstance(d, dict) and "error" in d:
        raise RuntimeError("%s answered an error envelope: %r" % (url, d["error"]))
    feats = d.get("features") or []
    if not feats:
        raise RuntimeError(
            "%s returned no features — an Esri error envelope arrives as HTTP 200, "
            "so read this as 'the field list or the service moved', not an outage" % url)
    if d.get("exceededTransferLimit"):
        raise RuntimeError("%s hit its transfer cap — needs paging" % url)
    return feats


# --- point-in-polygon, mirroring index.html's even-odd test -------------------
def _in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def in_geometry(pt, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if not poly or not _in_ring(pt, poly[0]):
            continue
        if any(_in_ring(pt, hole) for hole in poly[1:]):
            continue
        return True
    return False


def ward_of(props):
    """The ward number, from whichever field the publisher happened to use.

    Three vocabularies meet here and none is a superset of the others: the CITY
    writes LONGNAME "Ward 1" and SHORTNAME "D1", the STATE's precinct layer
    writes WARD "01", and the file this build EMITS writes WARD/Ward "1".
    Normalise NUMERICALLY — never by stripping characters, which would turn
    "D1" and "01" into different keys and silently classify every point wrong.
    """
    # `districtid` FIRST and alone among the city's fields. `OBJECTID` starts at
    # 6 (earlier rows were deleted), so a builder keyed on it numbers the
    # districts 6..9; `name` is prose. The STATE's precincts arrive here too and
    # write WARD "01", which is why this normalises numerically rather than by
    # stripping characters.
    for k in ("districtid", "DISTRICTID", "WARDNUM", "LONGNAME", "DISTRICT",
              "SHORTNAME", "WARD", "Ward", "ward"):
        v = props.get(k)
        if v in (None, ""):
            continue
        m = re.search(r"\d+", str(v))
        if m:
            return str(int(m.group(0)))
    return None

def model(features, key=ward_of):
    return [(key(f.get("properties") or {}), f["geometry"])
            for f in features if f.get("geometry")]


def bbox(features):
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for q in c:
                walk(q)
    for f in features:
        walk(f["geometry"]["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def fetch_blocks(box):
    env = "%2C".join("%.5f" % v for v in box)
    url = (BLOCKS + "?where=STATE%3D%2726%27&geometry=" + env +
           "&geometryType=esriGeometryEnvelope&inSR=4326"
           "&spatialRel=esriSpatialRelIntersects"
           "&outFields=POP100,INTPTLAT,INTPTLON&returnGeometry=false"
           "&outSR=4326&f=json&resultRecordCount=100000")
    d = json.loads(subprocess.run(["curl", "-sS", "--fail", "--max-time", "600", url],
                                  check=True, capture_output=True).stdout)
    if "error" in d:
        raise RuntimeError("TIGERweb answered an error envelope: %r" % d["error"])
    if d.get("exceededTransferLimit"):
        raise RuntimeError("TIGERweb capped the block fetch — needs paging")
    rows = []
    for f in d.get("features", []):
        a = f["attributes"]
        try:
            rows.append((float(a["INTPTLON"]), float(a["INTPTLAT"]), int(a["POP100"] or 0)))
        except (TypeError, ValueError, KeyError):
            continue
    if len(rows) < MIN_BLOCKS:
        raise RuntimeError("only %d usable blocks over Rochester Hills's envelope, floor %d — "
                           "read this as a capped or moved TIGERweb query" % (len(rows), MIN_BLOCKS))
    return rows


def point_agreement(a, b, box, samples=4000, seed=20260905):
    """Fraction of points landing in EITHER model that both put in the same
    unit. Used twice: city-wards vs state-precinct-dissolve (the currency
    gate) and full-precision vs simplified (the fleet's 2,000-point protocol)."""
    rng = random.Random(seed)
    hit = same = diff = only_a = only_b = 0
    tried = 0
    while hit < samples and tried < samples * 80:
        tried += 1
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        ha = [k for k, g in a if in_geometry(pt, g)]
        hb = [k for k, g in b if in_geometry(pt, g)]
        if not ha and not hb:
            continue
        hit += 1
        if ha and hb:
            if ha[0] == hb[0]:
                same += 1
            else:
                diff += 1
        elif ha:
            only_a += 1
        else:
            only_b += 1
    return {"hit": hit, "same": same, "diff": diff, "only_a": only_a, "only_b": only_b,
            "frac": (same / hit) if hit else 0.0}


def overlaps(m, box, samples=2000, seed=7):
    rng = random.Random(seed)
    n = 0
    for _ in range(samples):
        pt = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        if len([k for k, g in m if in_geometry(pt, g)]) > 1:
            n += 1
    return n


def metres_to_boundary(pt, geom):
    """Crude but adequate distance from a point to a polygon's nearest VERTEX.

    Vertex distance overstates the true distance to an edge, so it can only make
    this gate STRICTER than the truth — which is the safe direction for a check
    whose job is to prove a disagreement sits on the boundary. Degrees are
    converted with a fixed scale at Michigan's latitude; a metre or two either
    way cannot matter against a 100 m ceiling.
    """
    lon, lat = pt
    best = float("inf")
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        for ring in poly:
            for x, y in ring:
                d = math.hypot((x - lon) * 82000.0, (y - lat) * 111000.0)
                if d < best:
                    best = d
    return best


def check_shape(feats, require_derived=False):
    """`require_derived` is False upstream of the build, where the fetched
    features carry only the publisher's own WARD column, and True on the
    shipped file, where the bare `Ward` the card and hover both read must
    exist. Conflating the two is why the first run of this script refused its
    own input."""
    problems = []
    if len(feats) != EXPECT_FEATURES:
        problems.append("%d features, expected %d — Rochester Hills has four council districts"
                        % (len(feats), EXPECT_FEATURES))
    seen = tuple(sorted((ward_of(f.get("properties") or {}) or "?") for f in feats))
    if seen != EXPECT_WARDS:
        problems.append("ward numbers are %s, expected %s" % (list(seen), list(EXPECT_WARDS)))
    if require_derived:
        for f in feats:
            if "Ward" not in (f.get("properties") or {}):
                problems.append("a feature carries no bare Ward number — the card headline "
                                "and the hover label both read it")
                break
    return problems


def check_shipped(path):
    if not os.path.exists(path):
        return ["%s is missing" % path]
    with open(path) as f:
        shipped = json.load(f)
    feats = shipped.get("features") or []
    problems = check_shape(feats, require_derived=True)
    keys = {k for f in feats for k in (f.get("properties") or {})}
    stray = keys - set(KEEP_FIELDS) - set(DERIVED_FIELDS)
    if stray:
        problems.append("shipped properties carry unexpected keys: %s" % sorted(stray))
    return problems




def assert_no_stated_terms():
    """Rochester Hills ships because its item states NO terms — so notice if that changes.

    This is the mirror of Lansing's gate next door. There, the city states
    CC BY-NC and the build refuses to write; here the item is shared public with
    an empty licenseInfo, which is the Detroit case.

    THE ITEM ID IS PINNED RATHER THAN DISCOVERED, because the service is on the
    city's own ArcGIS Server and its root carries no `serviceItemId` to follow —
    the sibling builders' trick does not work here. A pinned id can drift onto
    some other item, so the title is asserted: a licence check against the wrong
    item is worse than no check at all.
    """
    item = json.loads(subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "120", TERMS_ITEM + "?f=json"],
        check=True, capture_output=True).stdout)
    if item.get("error"):
        fail("arcgis.com answered an error for the terms item: %r" % item["error"])
    title = item.get("title") or ""
    if "Council Districts" not in title:
        fail("the terms item is now titled %r — that is not this service's item, and a "
             "licence check against the wrong item is worse than none" % title)
    if item.get("access") != "public":
        fail("the city's item is no longer shared publicly (access=%r); it shipped "
             "because it was public and a human should re-read that before rebuilding"
             % item.get("access"))
    stated = re.sub(r"<[^>]+>", " ", item.get("licenseInfo") or "").strip()
    if stated:
        fail("the city now STATES TERMS on this item (%r). Rochester Hills shipped "
             "because it stated none; read the terms and decide before rebuilding — do "
             "not republish the geometry under a licence nobody has read."
             % (re.sub(r"\s+", " ", stated)[:200]))
    print("  terms: the city still states none on this item (shared public)")


def ward_layer_url():
    """The MapServer root decides the layer index, never this file.

    THREE layers live here and only one is the districts: 0 is polling PLACES (a
    point layer) and 1 is voting precincts. A build hardcoded to /0 gets points
    where it expects polygons. The index is read and the NAME asserted, so a
    republish that reorders them fails loudly rather than building the wrong
    thing."""
    root = json.loads(subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "120", SERVICE_ROOT + "?f=json"],
        check=True, capture_output=True).stdout)
    layers = root.get("layers") or []
    named = [l for l in layers if l.get("name") == EXPECT_LAYER_NAME]
    if len(named) != 1:
        fail("expected exactly one layer named %r on %s, found %s — a human should pick"
             % (EXPECT_LAYER_NAME, SERVICE_ROOT, [(l["id"], l["name"]) for l in layers]))
    return "%s/%d" % (SERVICE_ROOT, named[0]["id"])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)

    if args.check:
        problems = check_shipped(out_path)
        if problems:
            fail("; ".join(problems))
        print("build-mi-rochester-hills-wards: OK — 4 council districts shipped")
        return

    print("re-checking that the city still states no terms…")
    assert_no_stated_terms()

    print("reading the city's MapServer root for the district layer index…")
    service = ward_layer_url()
    print("  ward layer: %s" % service)

    # `activeflag=1` is the publisher's own currency flag, and `repname` is
    # deliberately NOT fetched: the city publishes a maintained council page and
    # this layer's names are not it (and the page is closed to this client by the
    # city's own robots.txt, which is why no name ships at all).
    wards = esri(service, {"where": "activeflag = 1",
                           "outFields": "districtid,activeflag,yearrange"})
    if len(wards) != EXPECT_FEATURES:
        fail("expected %d wards, got %d" % (EXPECT_FEATURES, len(wards)))
    got = tuple(sorted(ward_of(f["properties"]) for f in wards))
    if got != EXPECT_WARDS:
        fail("ward ids are %s, expected %s" % (list(got), list(EXPECT_WARDS)))
    problems = check_shape(wards)
    if problems:
        fail("; ".join(problems))

    box = bbox(wards)
    wm = model(wards)

    # ---- CURRENCY: the state's own 2026 precincts must describe these wards --
    print("fetching the state's 2026 precincts for the currency gate…")
    precs = esri(PRECINCTS, {"where": PRECINCT_WHERE, "outFields": "WARD,PRECINCT"})
    counts = {}
    for f in precs:
        k = ward_of(f["properties"])
        counts[k] = counts.get(k, 0) + 1
    if counts != EXPECT_PRECINCTS:
        fail("the state assigns %s precincts per ward, expected %s — the precinct "
             "fabric has moved and these wards must be re-checked against it"
             % (counts, EXPECT_PRECINCTS))
    agree = point_agreement(wm, model(precs), box)
    print("  city wards vs state precinct dissolve: %d/%d (%.3f%%)"
          % (agree["same"], agree["hit"], 100 * agree["frac"]))
    if agree["frac"] < MIN_PRECINCT_AGREEMENT:
        fail("point agreement %.3f%% is below the %.1f%% floor — find the city's adopted "
             "plan before touching this threshold; the threshold is not the thing to move"
             % (100 * agree["frac"], 100 * MIN_PRECINCT_AGREEMENT))

    # ---- the wards must tile the city, bounded rather than asserted exact ----
    print("fetching Census 2020 blocks…")
    blocks = fetch_blocks(box)
    place = esri(PLACE, {"where": "GEOID = '%s'" % PLACE_GEOID, "outFields": "NAME,GEOID"})
    # EXACT, INCLUDING TIGER'S LSAD SUFFIX, and not a substring: the city of
    # "Rochester" is a separate Census place immediately adjacent, and
    # "rochester" is a substring of "rochester hills". TIGERweb's NAME is
    # "Rochester Hills city" — a first draft compared against "rochester hills"
    # and refused its own correct fetch, which is why the suffix is in the
    # constant rather than stripped out of the answer.
    if not place or str(place[0]["properties"].get("NAME", "")).strip().lower() != EXPECT_PLACE_NAME:
        fail("place GEOID %s is not Rochester Hills (got %r) — the Census place id is wrong"
             % (PLACE_GEOID, place[0]["properties"].get("NAME") if place else None))
    pgeom = place[0]["geometry"]

    # fetch_blocks yields (lon, lat, pop) triples — TIGERweb's own interior
    # points, not polygon centroids, so a block never lands outside itself.
    per, total, place_pop, edge = {}, 0, 0, 0
    edge_blocks = []
    for lon, lat, pop in blocks:
        pt = (lon, lat)
        inw = next((k for k, g in wm if in_geometry(pt, g)), None)
        inp = in_geometry(pt, pgeom)
        if inw is not None:
            per[inw] = per.get(inw, 0) + pop
            total += pop
        if inp:
            place_pop += pop
        if (inw is not None) != inp:
            edge += 1
            edge_blocks.append((pt, pop, inp))
    ideal = total / float(EXPECT_FEATURES) if total else 0
    for k in sorted(per):
        print("    Ward %-3s %7d  %+.2f%%" % (k, per[k], 100.0 * (per[k] - ideal) / (ideal or 1)))
    delta = total - place_pop
    print("  wards total %d against the Census place's %d (%+d); %d edge block(s)"
          % (total, place_pop, delta, edge))
    if place_pop and abs(delta) > MAX_POP_DELTA_FRACTION * place_pop:
        fail("the wards' population differs from the city's by %+d (%.3f%%), past the "
             "%.1f%% tolerance — this is meant to be edge digitisation, not a hole"
             % (delta, 100.0 * abs(delta) / place_pop, 100 * MAX_POP_DELTA_FRACTION))
    # THE DIRECT TEST OF WHAT THE PERCENTAGE ONLY PROXIES FOR. A disagreement on
    # the city's own perimeter is two organisations tracing one line; the same
    # disagreement 500 m inside the city is a HOLE, and a reader standing in it
    # gets no district. This refuses the second whatever the percentage says.
    for pt, pop, inp in edge_blocks:
        d = metres_to_boundary(pt, pgeom)
        print("    edge block at %.5f,%.5f — %d people, %.0f m from the city line (%s)"
              % (pt[1], pt[0], pop, d, "in the city, in no district" if inp
                 else "in a district, outside the city"))
        if d > MAX_EDGE_METRES:
            fail("a block %.0f m from the city boundary (%d people) disagrees between the "
                 "districts and the Census place — past the %.0f m ceiling. That is not "
                 "edge digitisation, it is a hole, and a reader standing in it would get "
                 "no district." % (d, pop, MAX_EDGE_METRES))
    if edge > MAX_EDGE_BLOCKS:
        fail("%d blocks fall on one side of the ward outline and the other side of the "
             "Census place outline (ceiling %d)" % (edge, MAX_EDGE_BLOCKS))

    # ---- write, then the fleet's 2,000-point simplification protocol ---------
    src = {"type": "FeatureCollection",
           "features": [{"type": "Feature",
                         "properties": {"WARD": ward_of(f["properties"]),
                                        "Ward": ward_of(f["properties"])},
                         "geometry": f["geometry"]} for f in wards]}
    tmp = os.path.join(APP_DATA_DIR, ".rochester-hills-wards-src.json")
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(src, f)
    subprocess.run(["npx", "-y", MAPSHAPER, tmp,
                    "-simplify", "visvalingam", "keep-shapes", SIMPLIFY,
                    "-o", "precision=" + PRECISION, "format=geojson", out_path],
                   check=True)
    os.remove(tmp)

    with open(out_path) as f:
        built = json.load(f)
    bm = model(built["features"])
    proto = point_agreement(model(src["features"]), bm, box, samples=2000, seed=2026)
    src_ov = overlaps(model(src["features"]), box)
    if overlaps(bm, box) > src_ov:
        fail("simplification ADDED overlaps")
    if proto["frac"] < 0.995:
        fail("point-in-ward agreement only %.2f%% (need >= 99.5%%)" % (100 * proto["frac"]))
    print("  simplification: %d/%d (%.2f%%) agreement, %d source overlap(s), none added"
          % (proto["same"], proto["hit"], 100 * proto["frac"], src_ov))

    problems = check_shipped(out_path)
    if problems:
        fail("; ".join(problems))
    print("build-mi-rochester-hills-wards: wrote %s (4 council districts, %d bytes)"
          % (out_path, os.path.getsize(out_path)))


if __name__ == "__main__":
    main()
