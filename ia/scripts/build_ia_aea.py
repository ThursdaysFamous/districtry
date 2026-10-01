#!/usr/bin/env python3
"""
Build data/app/ia-aeas.json — Iowa's nine Area Education Agencies, read by
ia/index.html's Area Education Agency card.

Iowa Code ch. 273: every school district belongs to an AEA, which supplies it
with special-education, media and professional services. The nine agencies
therefore tile the state exactly, because the school districts do.

THE GEOMETRY IS NOT THE PUBLISHED AEA POLYGON, AND THAT IS THE WHOLE BUILD
--------------------------------------------------------------------------
The Department of Education publishes an AEA polygon layer, and shipping it
would have been the obvious move and the wrong one. Two things about it:

  * ITS ITEM TITLE AND ITS LAYER NAME DISAGREE. The public item
    `1cfa541b8ebe4bdcbc2f52cdd0977a2b` is titled **IowaAEAs**; the layer it
    serves calls itself **IdoeAeaFY20**. An earlier research note treated the
    two as separate services and worried only about the second. They are one
    — the same trap `build_ia_school_sites.py` records for `IowaSchoolBldgs`
    (internal title `PublicSchoolBldgs`). Pin the ITEM ID, never a name.
  * IT IS STAMPED "for the 2019-2020 school year - updated 3/9/2020". Six
    school years old, on a fabric this repo has already watched move:
    `build_ia_school_districts.py` dissolved Orient-Macksburg into Nodaway
    Valley for 2026-2027.

So the shipped geometry is built from the CURRENT fabric instead. The
Department's own **current** school-district layer (`CurrentIowaSchoolDistricts`
— itself named `IdoeSD`, the same trap again) carries `AEA_NUM`, `AEA` and
`AEA_Name` **in band on every one of its 324 districts**. That is the
Department stating, per current district, which agency it belongs to. Dissolve
the districts this app already ships by that attribute and the result is the
AEA fabric as of the current school year, drawn on edges the app's own
`school-district-unified` layer already uses — so the two layers nest exactly
rather than seaming against each other.

THE JOIN KEY IS EXACT AND IT IS ALSO A TRIPWIRE
-----------------------------------------------
`DistrictNCESCode` on the Department's layer IS the Census GEOID the shipped
school-district file is keyed on: **324 of 324, both directions, zero
leftovers, no alias table.** TIGERweb's 325th feature — Orient-Macksburg — has
no row in the Department's layer at all, which is a THIRD independent
corroboration of this repo's own reconciliation (TIGER's federal lag was the
first; `IowaSchoolDirectorDistricts` still carrying the stale name was the
second). The shipped parent already merged it into Nodaway Valley, so this
builder joins against the parent and expects zero misses on either side. The
day Iowa consolidates another district, that count moves and this fails.

THE PUBLISHED FY20 POLYGON IS THE WITNESS, WHICH IS THE JOB IT CAN STILL DO
---------------------------------------------------------------------------
Measured 2026-09-03 over 26,137 points inside Iowa: the dissolve and the
published FY20 polygons agree on **99.889%**, with **zero self-overlaps in
either layer**. The 29 disagreements split into 19 where one layer has Iowa
and the other does not — the state outline drawn by two publishers, metres
apart — and 10 genuine AEA-vs-AEA points whose **closest pair is 50.5 km
apart**, scattered singletons on eight different shared boundaries. A district
that had actually changed agency would show as a coherent blob of points
inside its own footprint, dozens strong. So the residual is a digitisation
seam between Census school-district edges and the Department's own AEA
cartography, and the gate below tests for the blob rather than only for a
percentage.

NO SECOND SIMPLIFICATION, DELIBERATELY
--------------------------------------
The parent file is already simplified at 9% and its own 2,000-point agreement
gate proved that simplification does not change the answer. A dissolve merges
interior boundaries and leaves the exterior ones untouched, so the result
cannot be worse than the parent. Simplifying again would move edges the
`school-district-unified` layer does not move and break the nesting that is
half the reason for building it this way.

IDENTITY AND CONTACT ONLY — NO DIRECTOR IS NAMED, AND THE REASON IS STATUTORY
-----------------------------------------------------------------------------
**Iowa Code §273.8 gives ZERO of an AEA's nine directors a popular election.**
Five are elected by the boards of directors of the member school districts on
a population-weighted vote; four are appointed by the member districts'
superintendents. A voter does not elect them, so the card says how they are
chosen instead of naming them — Wisconsin's `wtcs-district` posture.

What the card CAN name is the agency itself, and the agencies publish that
themselves: the Iowa AEA system's own **Find My AEA** page carries one block
per agency keyed on the SAME two-digit code the Department's geometry uses
(`id="01"` … `id="15"`), each with the agency's name, its phone number and its
website. Nine for nine, and their names match the Department's `AEA_Name` on
all nine — a cross-publisher agreement, not a hand-kept table in index.html.

Usage:
    python3 ia/scripts/build_ia_aea.py
    python3 ia/scripts/build_ia_aea.py --check
"""

import html
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
OUT_NAME = "ia-aeas.json"
PARENT_FILE = os.path.join(APP_DATA_DIR, "ia-school-districts.json")
MAPSHAPER = "mapshaper@0.6.102"

# The Department of Education's CURRENT school-district layer. Its own layer
# name is `IdoeSD`; the service path is the one to pin.
DE_DISTRICTS = ("https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/"
                "CurrentIowaSchoolDistricts/FeatureServer/0")

# The published FY20 AEA polygons — the WITNESS, never the shipped geometry.
# Item id, not name: a second copy of this same layer sits on a University of
# Northern Iowa personal account (6f1e8f26fe2c46988d00bf919e7b3321), and a
# name-based search finds both.
AEA_WITNESS = ("https://services.arcgis.com/vPD5PVLI6sfkZ5E4/arcgis/rest/services/"
               "IowaAEAs/FeatureServer/0")
AEA_WITNESS_ITEM = "1cfa541b8ebe4bdcbc2f52cdd0977a2b"

# The AEA system's own agency directory — name, phone and website per agency,
# keyed on the same two-digit code the Department's geometry carries.
FIND_MY_AEA = "https://iowaaea.org/find-my-aea/"

EXPECT_DISTRICTS = 324     # the Department's current layer, and the shipped parent
EXPECT_AEAS = 9            # Iowa Code ch. 273, unchanged by HF 2612 (2024), which
                           # moved accreditation, funding and service scope only

# Agreement of the dissolve against the published FY20 polygons.
WITNESS_SAMPLES = 20000
WITNESS_SEED = 2026
WITNESS_FLOOR = 99.5       # percent of in-state points that must agree
# A coarse ceiling on how much ground the two layers may disagree about at all.
# Measured 2026-09-03: 0.038% of in-state points.
DISAGREE_RATE_CEILING = 0.15   # percent of in-state points
# THE TEST THAT ACTUALLY ASKS THE QUESTION. Random statewide sampling can only
# ever say HOW MUCH the layers disagree, never WHERE, and a first draft of this
# gate tried to infer "seam vs moved district" from how far apart the
# disagreeing points fell. That is not a property of the data: two independent
# points on one long shared boundary land near each other as soon as the sample
# is big enough, and the gate duly fired at 4.3 km on a boundary it had measured
# at 50.5 km one seed earlier. So the question is asked directly instead --
# district by district, of all 324. A district that CHANGED agency reads as the
# other agency across its whole interior; a district merely touching a seam has
# a point or two on the wrong side. A MAJORITY of each district's interior must
# land in its own agency's published polygon, and no district may fail.
DISTRICT_PROBES = 5            # interior points per district
DISTRICT_PROBE_SEED = 273      # Iowa Code ch. 273
# The published layer's OWN self-overlap, which this build does not ship and does
# not have to fix. Measured 2026-09-03 at four pairs / ~5.3 sq mi = 0.009% of
# Iowa, about one sampled point. The ceiling is generous on purpose: it exists to
# notice the witness falling apart, not to police it.
SRC_OVERLAP_CEILING = 0.10       # percent of in-state points

STATE_BBOX = {"minLng": -96.84, "minLat": 40.17, "maxLng": -89.94, "maxLat": 43.70}
UA = "districtry/1.0 (+https://districtry.com/ia/)"
# THE BROWSER STRING THIS FILE USED TO SEND FOR find-my-aea IS RETIRED
# (2026-10-01). Measured that day on this file's own stack -- curl with the
# districtry token and nothing else -- iowaaea.org answered HTTP 200 and
# 97,110 bytes, so the page needs no browser claim.


def _curl(url, ua=UA):
    return subprocess.run(
        ["curl", "-sS", "--fail", "-L", "--max-time", "300", "-H", "User-Agent: " + ua, url],
        check=True, capture_output=True,
    ).stdout


# ---------------------------------------------------------------- sources ---
def fetch_district_aea():
    """{GEOID: {aea_num, aea, aea_name, name, pop}} from the Department's own
    CURRENT district layer. No geometry — only the membership attribute."""
    url = (DE_DISTRICTS + "/query?where=1%3D1&outFields=DistrictNCESCode,SchoolDistName,"
           "AEA_NUM,AEA_Name,AEA,Pop2020&returnGeometry=false&f=json")
    feats = json.loads(_curl(url)).get("features") or []
    if len(feats) != EXPECT_DISTRICTS:
        raise RuntimeError(
            "CurrentIowaSchoolDistricts returned %d districts, expected %d — Iowa has "
            "consolidated again. Re-derive the join below and this constant together, "
            "and check ia-school-districts.json was rebuilt first"
            % (len(feats), EXPECT_DISTRICTS))
    out = {}
    for f in feats:
        a = f["attributes"]
        code = a.get("DistrictNCESCode")
        num = a.get("AEA_NUM")
        if not code or num is None:
            raise RuntimeError(
                "district %r carries no NCES code or no AEA_NUM — the membership "
                "attribute this layer is built on is not universal after all"
                % a.get("SchoolDistName"))
        out[str(code)] = {
            "aea_num": int(num),
            "aea": str(a.get("AEA") or "").strip(),
            "aea_name": str(a.get("AEA_Name") or "").strip(),
            "district": str(a.get("SchoolDistName") or "").strip(),
            "pop": int(a.get("Pop2020") or 0),
        }
    if len(out) != EXPECT_DISTRICTS:
        raise RuntimeError("DistrictNCESCode is not unique across the %d districts"
                           % EXPECT_DISTRICTS)
    return out


def fetch_agency_directory():
    """{code: {name, phone, site}} from the AEA system's own Find My AEA page.

    The page renders one block per agency whose `id` IS the agency's two-digit
    number — the same value the Department's geometry carries in `AEA`. That is
    what makes this a keyed join rather than a name match.
    """
    page = _curl(FIND_MY_AEA).decode("utf-8", "replace")
    blocks = re.findall(r'<div class="fm-map__info" id="(\d{2})"[^>]*>(.*?)</div>',
                        page, re.S)
    out = {}
    for code, body in blocks:
        name = re.search(r'<h3 class="fm-map__info-text">\s*(.*?)\s*</h3>', body, re.S)
        phone = re.search(r'href="tel:([^"]+)"', body)
        site = re.search(r'<a href="(https?://[^"]+)" class="fm-map__info-website"', body)
        if not (name and site):
            raise RuntimeError(
                "Find My AEA block id=%s carries no name or no website — the page's "
                "markup moved; re-read it before trusting any of the nine" % code)
        out[code] = {
            "name": html.unescape(" ".join(name.group(1).split())),
            "phone": phone.group(1).strip() if phone else None,
            "url": site.group(1).strip(),
        }
    if len(out) != EXPECT_AEAS:
        raise RuntimeError("Find My AEA published %d agency blocks, expected %d"
                           % (len(out), EXPECT_AEAS))
    return out


def fetch_witness():
    url = (AEA_WITNESS + "/query?where=1%3D1&outFields=AEA_NUM,AEA_Name,AEA"
           "&returnGeometry=true&outSR=4326&f=geojson")
    geo = json.loads(_curl(url))
    feats = geo.get("features") or []
    if len(feats) != EXPECT_AEAS:
        raise RuntimeError("the published AEA layer returned %d features, expected %d"
                           % (len(feats), EXPECT_AEAS))
    for f in feats:
        f["properties"]["aea_num"] = int(f["properties"]["AEA_NUM"])
    return feats


# ------------------------------------------------------------------ build ---
def join_parent(district_aea):
    """The shipped school districts, each tagged with its agency. Zero misses
    either way, or nothing ships."""
    with open(PARENT_FILE) as f:
        parent = json.load(f)
    feats = parent.get("features") or []
    if len(feats) != EXPECT_DISTRICTS:
        raise RuntimeError("%s holds %d districts, expected %d — rebuild it first"
                           % (os.path.basename(PARENT_FILE), len(feats), EXPECT_DISTRICTS))
    left = dict(district_aea)
    tagged, missing = [], []
    for f in feats:
        geoid = str(f["properties"].get("GEOID"))
        rec = left.pop(geoid, None)
        if rec is None:
            missing.append((geoid, f["properties"].get("NAME")))
            continue
        tagged.append({"type": "Feature",
                       "properties": {"aea_num": rec["aea_num"], "geoid": geoid},
                       "geometry": f["geometry"]})
    if missing or left:
        raise RuntimeError(
            "the NCES join is no longer exact: %d shipped district(s) with no agency "
            "(%s) and %d agency row(s) with no shipped district (%s). This is what a "
            "consolidation looks like — reconcile it, never widen the join"
            % (len(missing), missing[:4], len(left),
               [v["district"] for v in list(left.values())[:4]]))
    return tagged


def dissolve(tagged):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src.json")
        out = os.path.join(tmp, "out.json")
        with open(src, "w") as f:
            json.dump({"type": "FeatureCollection", "features": tagged}, f)
        subprocess.run(["npx", "-y", MAPSHAPER, src, "-dissolve", "aea_num",
                        "-o", out, "format=geojson"],
                       check=True, cwd=REPO_ROOT, capture_output=True)
        with open(out) as f:
            return json.load(f).get("features") or []


def build_properties(dissolved, district_aea, directory):
    """Attach the agency's identity and contact, and prove the two publishers
    agree about which agency each number is."""
    by_num = {}
    for rec in district_aea.values():
        by_num.setdefault(rec["aea_num"], {"aea": rec["aea"], "aea_name": rec["aea_name"],
                                           "districts": 0, "pop": 0})
        slot = by_num[rec["aea_num"]]
        if slot["aea"] != rec["aea"] or slot["aea_name"] != rec["aea_name"]:
            raise RuntimeError("AEA %d is published under two names/codes in the "
                               "district layer" % rec["aea_num"])
        slot["districts"] += 1
        slot["pop"] += rec["pop"]
    if len(by_num) != EXPECT_AEAS:
        raise RuntimeError("the district layer names %d agencies, expected %d"
                           % (len(by_num), EXPECT_AEAS))

    out = []
    for feat in dissolved:
        num = int(feat["properties"]["aea_num"])
        agency = by_num[num]
        entry = directory.get(agency["aea"])
        if entry is None:
            raise RuntimeError(
                "the agency directory has no block for code %r (AEA %d, %s) — the two "
                "publishers no longer key the same way" % (agency["aea"], num, agency["aea_name"]))
        # cross-publisher name gate: the Department shouts, the agencies' own
        # page does not, so compare case-folded and ship the agencies' own form
        if entry["name"].upper() != agency["aea_name"].upper():
            raise RuntimeError(
                "AEA %s is %r to the Department of Education and %r to the agencies' own "
                "directory — resolve that before shipping either"
                % (agency["aea"], agency["aea_name"], entry["name"]))
        props = {
            "aea": agency["aea"],
            "aea_num": num,
            "name": entry["name"],
            "districts": agency["districts"],
            "population": agency["pop"],
            # KEY NAMED `url` ON PURPOSE, the Wisconsin municipal-clerk precedent:
            # validate_card_links.py's PUBLISHED_KEYS is {"url", "profileUrl"}, the
            # "somebody else published this address" class that caps a dead link at
            # WARN. These nine are scraped from the agencies' own directory, not
            # hand-picked here, so that is exactly what they are -- and one of them
            # (mbaea.org) answers a bot challenge to this client while loading fine
            # in a browser, which is the shape that class exists for.
            "url": entry["url"],
        }
        if entry["phone"]:
            props["phone"] = entry["phone"]
        out.append({"type": "Feature", "properties": props, "geometry": feat["geometry"]})
    out.sort(key=lambda f: f["properties"]["aea_num"])
    return out


# ------------------------------------------- point-in-polygon (fleet copy) ---
def _point_in_ring(pt, ring):
    x, y = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-16) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_polygon(pt, rings):
    if not rings or not _point_in_ring(pt, rings[0]):
        return False
    return not any(_point_in_ring(pt, hole) for hole in rings[1:])


def _point_in_geometry(pt, geom):
    t = (geom or {}).get("type")
    if t == "Polygon":
        return _point_in_polygon(pt, geom["coordinates"])
    if t == "MultiPolygon":
        return any(_point_in_polygon(pt, p) for p in geom["coordinates"])
    return False


def _bbox(geom):
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0])
            ys.append(c[1])
        else:
            for part in c:
                walk(part)

    walk(geom["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def _model(features, key):
    return [(f["properties"][key], _bbox(f["geometry"]), f["geometry"]) for f in features]


def _hits(model, pt):
    x, y = pt
    out = []
    for key, (x0, y0, x1, y1), geom in model:
        if x0 <= x <= x1 and y0 <= y <= y1 and _point_in_geometry(pt, geom):
            out.append(key)
    return out


def validate_against_witness(built, witness):
    """The FY20 polygons cannot supply the geometry any more; they can still
    say whether this one is the same shape.

    THE OVERLAP TEST IS SPLIT BY WHOSE DEFECT IT IS, the lesson
    build_dsm_wards.py learned from the City of Des Moines' own ward 1/2
    ribbon: a gate that lumps the source's flaws in with the build's fails for
    the wrong reason and teaches nothing. The dissolve gets ZERO tolerance
    because it is what ships. The published layer's own self-overlaps are
    reported and capped generously, because they are a fact about it —
    measured 2026-09-03, FOUR pairs overlap each other across about 5.3 sq mi
    (01x07 2.989, 01x10 1.005, 12x13 0.943, 01x09 0.348), 124 slivers in the
    largest pair alone, the biggest 171 acres at Polsby-Popper 0.042. Long thin
    shapes: two independently digitised lines that never quite met. **The layer
    this build declined to ship does not close on itself, and the one it built
    does.**

    Fails on a low agreement, on any dissolve self-overlap, and — the test that
    distinguishes a seam from a real change — on AEA-vs-AEA disagreements
    CLUSTERING inside one footprint.
    """
    codes_built = {(f["properties"]["aea_num"], f["properties"]["aea"]) for f in built}
    codes_wit = {(int(f["properties"]["AEA_NUM"]), str(f["properties"]["AEA"]))
                 for f in witness}
    if codes_built != codes_wit:
        raise RuntimeError("the dissolve and the published layer name different agencies: "
                           "%s vs %s" % (sorted(codes_built), sorted(codes_wit)))

    mb, mw = _model(built, "aea"), _model(witness, "aea_num")
    rng = random.Random(WITNESS_SEED)
    inside = agree = 0
    own_overlaps = src_overlaps = 0
    disagree_pts = []
    for _ in range(WITNESS_SAMPLES):
        pt = (rng.uniform(STATE_BBOX["minLng"], STATE_BBOX["maxLng"]),
              rng.uniform(STATE_BBOX["minLat"], STATE_BBOX["maxLat"]))
        b, w = _hits(mb, pt), _hits(mw, pt)
        if len(b) > 1:
            own_overlaps += 1
        if len(w) > 1:
            src_overlaps += 1
        if not b and not w:
            continue
        inside += 1
        kb = int(b[0]) if len(b) == 1 else None
        kw = w[0] if len(w) == 1 else None
        if kb == kw:
            agree += 1
        elif kb is not None and kw is not None:
            disagree_pts.append(pt)
    if own_overlaps:
        raise RuntimeError(
            "topology broken in the SHIPPED dissolve: %d sampled points fell in more "
            "than one agency. The parent school-district fabric must not overlap itself "
            "-- rebuild ia-school-districts.json before this" % own_overlaps)
    if 100.0 * src_overlaps / inside > SRC_OVERLAP_CEILING:
        raise RuntimeError(
            "the PUBLISHED AEA layer now self-overlaps on %.3f%% of in-state points "
            "(ceiling %.2f%%) -- that is past the four sliver pairs measured on "
            "2026-09-03, so re-measure it before trusting it as a witness at all"
            % (100.0 * src_overlaps / inside, SRC_OVERLAP_CEILING))
    pct = 100.0 * agree / inside
    rate = 100.0 * len(disagree_pts) / inside
    if pct < WITNESS_FLOOR:
        raise RuntimeError("the dissolve agrees with the published AEA layer on only "
                           "%.3f%% of %d in-state points (floor %.1f%%)"
                           % (pct, inside, WITNESS_FLOOR))
    if rate > DISAGREE_RATE_CEILING:
        raise RuntimeError("%.3f%% of in-state points land in a different agency than the "
                           "published layer (ceiling %.2f%%) -- too many for a digitisation "
                           "seam" % (rate, DISAGREE_RATE_CEILING))
    return ("%.3f%% agreement over %d in-state points; 0 overlaps in the dissolve, %d "
            "sampled point(s) in the published layer's own sliver overlaps; %d boundary "
            "disagreement(s)" % (pct, inside, src_overlaps, len(disagree_pts)))


def _interior_points(geom, n, rng):
    """n points guaranteed inside the polygon, by rejection inside its bbox."""
    x0, y0, x1, y1 = _bbox(geom)
    pts, tries = [], 0
    while len(pts) < n and tries < 20000:
        tries += 1
        pt = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if _point_in_geometry(pt, geom):
            pts.append(pt)
    if not pts:
        raise RuntimeError("could not find an interior point in a district polygon")
    return pts


def validate_no_district_moved(tagged, district_aea, witness):
    """Ask the question directly, of every district: does the published layer
    still put this district in the agency the Department says it belongs to?

    This is the gate that decides whether a six-year-old boundary is stale in a
    way that MATTERS. An AEA line only moves when a member district changes
    agency, so a district whose interior reads one agency in the Department's
    current attribute table and another in the published polygon is exactly
    that event -- and it is the only thing that would make the dissolve and the
    published shape genuinely different rather than differently drawn.
    """
    mw = _model(witness, "aea_num")
    rng = random.Random(DISTRICT_PROBE_SEED)
    moved, brushed = [], 0
    for feat in tagged:
        own = feat["properties"]["aea_num"]
        agree = 0
        for pt in _interior_points(feat["geometry"], DISTRICT_PROBES, rng):
            hits = _hits(mw, pt)
            if len(hits) == 1 and hits[0] == own:
                agree += 1
        if agree * 2 <= DISTRICT_PROBES:          # not a majority
            moved.append((feat["properties"]["geoid"], own, agree))
        elif agree < DISTRICT_PROBES:
            brushed += 1
    if moved:
        named = [(district_aea[g]["district"], "AEA %d" % n, "%d/%d" % (a, DISTRICT_PROBES))
                 for g, n, a in moved[:6]]
        raise RuntimeError(
            "%d district(s) read as a DIFFERENT agency in the published layer than the "
            "Department's own current attribute says: %s. That is a district changing "
            "agency, not a drawing difference -- resolve which source is right before "
            "shipping either shape" % (len(moved), named))
    return ("all %d districts sit in their own agency's published polygon (%d touch a "
            "seam on at least one probe)" % (len(tagged), brushed))


# ------------------------------------------------------------------- main ---
def main():
    check_only = "--check" in sys.argv[1:]
    out_path = os.path.join(APP_DATA_DIR, OUT_NAME)

    district_aea = fetch_district_aea()
    print("Dept. of Education: %d current districts, all carrying an agency"
          % len(district_aea), file=sys.stderr)

    directory = fetch_agency_directory()
    print("Find My AEA: %d agencies, %d with a phone"
          % (len(directory), sum(1 for v in directory.values() if v["phone"])),
          file=sys.stderr)

    tagged = join_parent(district_aea)
    print("  NCES join onto the shipped fabric: %d/%d, no leftovers either way"
          % (len(tagged), EXPECT_DISTRICTS), file=sys.stderr)

    dissolved = dissolve(tagged)
    if len(dissolved) != EXPECT_AEAS:
        raise RuntimeError("the dissolve produced %d agencies, expected %d"
                           % (len(dissolved), EXPECT_AEAS))
    built = build_properties(dissolved, district_aea, directory)

    witness = fetch_witness()
    print("  witness gate (published FY20 polygons): %s"
          % validate_against_witness(built, witness), file=sys.stderr)
    print("  no-district-moved gate: %s"
          % validate_no_district_moved(tagged, district_aea, witness), file=sys.stderr)

    total_pop = sum(f["properties"]["population"] for f in built)
    total_districts = sum(f["properties"]["districts"] for f in built)
    if total_districts != EXPECT_DISTRICTS:
        raise RuntimeError("the nine agencies account for %d districts, not %d"
                           % (total_districts, EXPECT_DISTRICTS))
    print("  partition: %d districts, %s people across %d agencies"
          % (total_districts, format(total_pop, ","), len(built)), file=sys.stderr)

    payload = json.dumps({"type": "FeatureCollection", "features": built},
                         separators=(",", ":"), sort_keys=True) + "\n"
    if check_only:
        try:
            with open(out_path) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError("%s is missing (%s) — run without --check" % (OUT_NAME, e))
        if shipped != payload:
            raise RuntimeError("%s has drifted from the source. Re-run this builder."
                               % OUT_NAME)
        print("check: shipped layer matches the source", file=sys.stderr)
        return

    with open(out_path, "w") as f:
        f.write(payload)
    print("wrote data/app/%s — %d agencies, %.1f KB (no simplification: the parent "
          "school-district fabric is already simplified and gated)"
          % (OUT_NAME, len(built), len(payload) / 1024.0), file=sys.stderr)


if __name__ == "__main__":
    main()
