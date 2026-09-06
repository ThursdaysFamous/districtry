#!/usr/bin/env python3
"""
Ship library-district boundaries for the 72 Illinois counties that publish none.

WHOSE BOUNDARY THIS IS, AND WHY THAT SENTENCE COMES FIRST. The source is the
Illinois Broadband Office / Connected Nation `IL_Boundary_Layers` service,
layer 11 "Library Districts" — 642 polygons for the whole state, public and
token-free. The publisher is a BROADBAND CONTRACTOR, not a county and not the
districts, and every attribute besides `Library` and `LibraryType` is a
broadband service metric.

IT CARRIES A LICENCE, AND THE FIRST VERSION OF THIS FILE SAID IT CARRIED NONE.
That claim came from reading LAYER 11, whose own copyrightText and description
are indeed empty, and generalising to the whole publication — the same
read-one-surface-and-generalise mistake this project keeps recording. Measured
2026-09-05: the SERVICE carries `copyrightText` "Illinois Broadband Office,
Connected Nation" plus a full description, and AGOL item
675906ae06b5460296154760b7fb1367 states the terms: public use permitted; no
warranty; NOT for legal boundary determinations; "Attribution Requirement:
Users must cite the data source"; and "Modification & Redistribution: Users may
modify or analyze the data but must indicate any changes when sharing derived
products".

BOTH OBLIGATIONS ARE MET ON THE CARD, and the second one is why the credit is
longer than a publisher's name. This file MODIFIES the data twice — it clips
each district to its county and simplifies at SIMPLIFY_M — so the card states both
the compiler and the changes. Attribution alone would have satisfied half a
licence. That is a real published boundary with a weak provenance line, which
under this project's rules is an operator decision rather than a default; it was recorded in
docs/DATA_LAYER_GUIDEBOOK.md's backlog on 2026-08-20, measured further on
2026-09-04, and the decision to ship was taken 2026-09-05. Every card built on
this file NAMES the publisher, because a reader is entitled to know that the
line they are being shown was drawn by a broadband planner rather than filed
by the library.

WHAT MAKES IT TRUSTWORTHY IS THAT IT IS RIGHT WHERE SOMEONE ELSE'S RECORD SAYS
IT SHOULD BE, and this builder GATES on that rather than describing it:

  * CARROLL IS THE WITNESS. The county Clerk's own tax report names seven
    library tax lines — Savanna, Mount Carroll, Chadwick, Milledgeville, York
    Township, Lanark and Pearl City — recorded in this repo's own gap record
    before this layer was found. The layer returns exactly those seven, and
    the builder REFUSES TO WRITE if it ever stops doing so. The eighth polygon
    touching Carroll is a 0.01 km2 sliver of Hanover Township Library, whose
    body sits in Jo Daviess.
  * IT IS RIGHT ON THE NEGATIVES, which is the check a wrong layer fails.
    Shannon village and Lake Carroll land in NO library district, and the
    Clerk's tax codes independently agree that Shannon's code carries no
    library line. Both are probes below.
  * BOONE IS THE SECOND WITNESS AND IS NOT BUILT HERE. Boone's own library
    boundaries ship from the county's tax roll (build_parcel_fabric_districts.py),
    so it is a control rather than a customer: the two publishers name the same
    three bodies, and the contractor's polygons agree with the county's at
    60-85% IoU. Its `City` typing of Ida Public Library is CORRECT and the
    county proves it — Ida's 18 tax codes (LYBV) are identical to the City of
    Belvidere's (VCBV), so Ida is a municipal library whose area is the city.

THE TYPE IS SHIPPED, NOT HIDDEN. `LibraryType` is the real Illinois governance
vocabulary — District, City, Village, Township, Town, and two `(contracting)`
variants — and the distinction matters to a reader: a library DISTRICT is a
taxing body you live inside, while a municipal library's boundary is simply
the municipality and it levies nothing of its own. A layer compiled only for
broadband arithmetic would not need to separate them.

CLIPPED TO THE COUNTY, DELIBERATELY. Each entry is county-scoped, so its
overlay should draw what the entry speaks for. No ground loses an answer: a
district straddling a county line ships its slice in EACH county's file, so
Pearl City appears in both Carroll's and Stephenson's and a reader on either
side is answered. What clipping avoids is one polygon shipped six times and an
overlay that draws a district into a county this entry does not gate.

Usage:
    python3 scripts/build_statewide_library_districts.py
    python3 scripts/build_statewide_library_districts.py --check
"""

import argparse
import json
import os
import re
import sys

import requests
from shapely.geometry import shape, mapping, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcgis_nesting import assert_nesting_repaired  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.path.dirname(HERE), "il", "data", "app")

SERVICE = ("https://services.arcgis.com/R0IGaIgf2sox9aCY/arcgis/rest/services/"
           "IL_Boundary_Layers/FeatureServer/11")
SOURCE_LABEL = "Illinois Broadband Office / Connected Nation"
PAGE = 2000                  # the service's own maxRecordCount
MIN_STATEWIDE = 600          # 642 today; a floor, not an equality — the
                             # publisher may add a library without breaking us
SIMPLIFY_M = 5.0             # invisible at any zoom this map allows. 10 m was
                             # tried first and rejected on measurement: it ate 3.7%
                             # of Pearl City's Carroll slice, which is a long thin
                             # reach over the county line and exactly the shape a
                             # coarse tolerance destroys. 5 m costs ~40 KB across
                             # the six files and keeps every district inside the
                             # retention gate.

# A BORDER SLIVER IS RULED OUT BY SHAPE, NOT BY AREA, and that distinction was
# forced by measurement rather than chosen. Two independently drawn layers — a
# contractor's library polygon and the census county outline — disagree by tens
# of metres along a shared county line, which manufactures thin intersections
# that are not reach into the county. Sorting the six counties' intersections by
# AREA gives no natural break at all: they run continuously from 257 m2 upward,
# so any area floor is a number picked to make some gate pass. Sorting them by
# how far they reach INWARD from the county line splits them cleanly. Exactly
# three never reach 10 m inside — Winnebago PLD in Stephenson (257 m2),
# Farmersville-Waggoner in Sangamon (3,444 m2) and Hanover Township in Carroll
# (11,806 m2), each a body seated in a neighbouring county — and every other
# intersection reaches at least 10 m in. TEN METRES IS TWICE THE SIMPLIFICATION
# TOLERANCE, which is 5 m: an earlier draft simplified at 10 m and this comment
# still called them the same number after that changed. Twice the tolerance is
# the right bar either way — a patch that never reaches beyond the distance
# simplification alone can move a line is not evidence of reach into the county.
SLIVER_REACH_M = 10.0

# Simplification eats a larger FRACTION of a small high-perimeter shape than of
# a large one, so a bare fraction test fires on a sliver while missing a real
# loss on a big district. Fail only when the fraction AND the absolute area both
# say real ground went missing — the rule build_parcel_fabric_districts.py
# already carries for the same reason.
MIN_AREA_RETAINED = 0.98
MIN_AREA_LOST_M2 = 25000.0

# Two library service areas overlapping by more than this MEAN WIDTH is real
# shared ground rather than two boundaries digitised apart. Twice SIMPLIFY_M,
# the same reasoning as SLIVER_REACH_M — see the overlap check in build_county
# for the measurement that forced it.
OVERLAP_WIDTH_M = 10.0

# Polygons shipped at full precision because SIMPLIFY_M would have cost them
# real ground (see build_county). One today. A ceiling rather than a list,
# because the thing worth catching is the source changing shape wholesale —
# a handful of thin county-line reaches is the expected steady state.
UNSIMPLIFIED = []
MAX_UNSIMPLIFIED = 12

DEG = 1.0 / 111320.0
M2_PER_DEG2 = (111320.0 ** 2) * 0.766   # ~40.5N; used only for the sliver floor

# Carroll's seven, from the County Clerk's own Tax Code by District Listing as
# recorded in this repo's gap record BEFORE this layer was found. This is the
# gate, not a comment: if the layer stops returning exactly these, the build
# stops.
# Macoupin's eleven, from the County Clerk's DEVNET "Taxcode Value within
# District Report" (tax year 2025, linked from the county's own Socrata portal
# alongside the 2023 and 2024 editions). This is the SECOND county with a
# published tax list to check the contractor's layer against, and it is a
# stronger check than Carroll's because the county publishes the crosswalk for
# every one of its 224 tax codes: the report's five LY* library districts, its
# one TL* township library and its five VL* municipal libraries are exactly the
# eleven bodies the layer returns inside the county, and the layer's own
# LibraryType agrees with the Clerk's code prefix on all eleven.
#
# ONE NAME DISAGREEMENT IS CARRIED RATHER THAN RESOLVED SILENTLY. The Clerk
# writes "Virden Library District" under the code LYGP; the layer writes "Grand
# Prairie of the West Public Library District". The Clerk's own code — GP for
# Grand Prairie — shows the county knows both names, so this is one body under
# two labels and not a mismatch. The layer's name is what ships, because it is
# the string on the polygon a reader's card renders.
MACOUPIN_CLERK_LIBRARIES = {
    "Bunker Hill Public Library District",        # LYBH
    "Brighton Memorial Library District",         # LYBR
    "Farmersville-Waggoner Public Library District",  # LYFW
    "Grand Prairie of the West Public Library District",  # LYGP, the Clerk's "Virden"
    "Litchfield Public Library District",         # LYL
    "Girard Township Library",                    # TL07
    "Frank Bertetti Benld Public Library",        # VLBE
    "Carlinville Public Library",                 # VLCA
    "Gillespie Public Library",                   # VLGI
    "Mount Olive Public Library",                 # VLMV
    "Staunton Public Library",                    # VLST
}

CARROLL_CLERK_LIBRARIES = {
    "Savanna Public Library District",
    "Mount Carroll District Library",
    "Chadwick Public Library District",
    "Milledgeville Public Library",
    "York Township Public Library",
    "Lanark Public Library",
    "Pearl City Public Library District",
}

# Each probe is (lat, lng, expected library or None). The negatives matter more
# than the positives: a layer that covers everything would pass every positive.
COUNTIES = [
    {"slug": "carroll", "label": "Carroll County", "expect": 7,
     "clerk_names": CARROLL_CLERK_LIBRARIES,
     "probes": [(42.0942, -89.9787, "Mount Carroll District Library"),
                (42.1522, -89.7401, None),   # Shannon village — the Clerk's
                (42.1631, -89.8664, None)]}, # tax codes agree: no library line
    {"slug": "lee", "label": "Lee County", "expect": 11,
     "probes": [(41.8389, -89.4795, "Dixon Public Library"),
                (41.7114, -89.3290, "Pankhurst Memorial Library")]},
    {"slug": "macoupin", "label": "Macoupin County", "expect": 11,
     "clerk_names": MACOUPIN_CLERK_LIBRARIES,
     # Hayner is seated in Madison County and reaches 20.6 m over the line —
     # past SLIVER_REACH_M, so shape alone keeps it; the Clerk levies nothing
     # for it, so it is not a Macoupin library. Divernon reaches 0.9 m and the
     # reach rule drops it without needing this list.
     "clerk_excluded": {"Hayner Public Library District": 20.6},
     # every probe is a Census 2020 incorporated-place centroid, so the points
     # are independent of the layer being tested
     "probes": [(39.27748, -89.87612, "Carlinville Public Library"),
                (39.12582, -89.81736, "Gillespie Public Library"),
                (39.04155, -89.95119, "Bunker Hill Public Library District"),
                (39.50606, -89.77110, "Grand Prairie of the West Public Library District"),
                (39.09300, -89.80233, "Frank Bertetti Benld Public Library"),
                (39.44658, -89.78205, "Girard Township Library"),
                # the negatives, which matter more than the positives: a layer
                # covering everything would pass every one above, and the
                # Clerk's tax roll independently agrees these villages pay no
                # library line
                (39.35574, -90.03741, None),   # Hettick
                (39.47771, -90.10379, None)]}, # Scottville
    {"slug": "randolph", "label": "Randolph County", "expect": 9,
     "probes": [(37.9134, -89.8221, "Chester Public Library"),
                (38.1236, -89.7018, "Sparta Public Library")]},
    {"slug": "sangamon", "label": "Sangamon County", "expect": 16,
     "probes": [(39.7817, -89.6501, "Lincoln Library"),
                (39.6739, -89.7018, "Chatham Area Public Library District")]},
    {"slug": "st-clair", "label": "St. Clair County", "expect": 19,
     "probes": [(38.5200, -89.9840, "Belleville Public Library"),
                (38.5706, -90.1798, "Cahokia Public Library District")]},
    {"slug": "stephenson", "label": "Stephenson County", "expect": 5,
     "probes": [(42.2967, -89.6212, "Freeport Public Library"),
                (42.3792, -89.8226, "Lena Community District Library")]},
]

# ---------------------------------------------------------------------------
# THE OTHER 65 COUNTIES, AND WHY THEY CARRY NO PROBES.
#
# The six above were hand-verified: an exact feature count, and probe points a
# person checked one at a time, at least one of them a NEGATIVE. That does not
# scale to 65 counties — 130 probe points nobody actually verified would be
# guesses wearing a gate's clothes, which is the one thing this project's rules
# forbid outright.
#
# So these counties lean on a gate the six never had, which is STRONGER rather
# than weaker and covers all 71 at once: the PLACE WITNESS below. It checks the
# layer against Census 2020 geography — an independent publisher — on the 278
# polygons whose boundary is a claim about a unit somebody else also draws, and
# it discriminates in BOTH directions rather than only confirming. 236 of those
# 278 are actually scored: the other 42 are named for a person rather than for
# their unit (Carnegie, Dominy Memorial, Sallie Logan) and simply have no
# witness, which is reported rather than counted either way.
#
# The labels come from build_county_status.ALL_COUNTIES rather than being typed
# again here. A second hand-kept county-name table is exactly the drift this
# repo keeps finding (the frontier list, the board-office list, the card-links
# instance list), and there is no reason to create a third.
WITNESS_COUNTIES = (
    "alexander", "bond", "brown", "calhoun", "cass", "clark", "clay", "clinton",
    "coles", "crawford", "cumberland", "dewitt", "douglas", "edgar", "edwards",
    "franklin", "fulton", "gallatin", "greene", "hamilton", "hancock", "hardin",
    "henry", "iroquois", "jackson", "jefferson", "jersey", "jo-daviess",
    "johnson", "knox", "lasalle", "livingston", "logan", "marshall", "mason",
    "massac", "mcdonough", "mclean", "menard", "mercer", "monroe", "montgomery",
    "morgan", "moultrie", "ogle", "perry", "pike", "pulaski", "putnam",
    "richland", "saline", "schuyler", "scott", "shelby", "tazewell", "union",
    "vermilion", "wabash", "warren", "washington", "wayne", "white",
    "whiteside", "williamson", "winnebago",
)


def _county_labels():
    """slug -> "X County", from the one table that already owns the mapping."""
    import build_county_status as bcs
    return {bcs.slug_of(n): n + " County" for n, _ in bcs.ALL_COUNTIES}


def _append_witness_counties():
    labels = _county_labels()
    have = {c["slug"] for c in COUNTIES}
    for slug in WITNESS_COUNTIES:
        if slug in have:
            fail("%s is both hand-verified and in WITNESS_COUNTIES — one county, "
                 "one entry" % slug)
        if slug not in labels:
            fail("WITNESS_COUNTIES names %r, which is not an Illinois county in "
                 "build_county_status.ALL_COUNTIES" % slug)
        COUNTIES.append({"slug": slug, "label": labels[slug]})


def fail(msg):
    print("build-statewide-library-districts: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def clean(g):
    """Repair a geometry and keep only its polygonal parts."""
    if not g.is_valid:
        g = make_valid(g)
    if not g.is_valid:
        g = g.buffer(0)
    if g.geom_type == "GeometryCollection":
        polys = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
        g = unary_union(polys) if polys else g
    return g


def fetch_layer():
    """Every page, refusing rather than truncating.

    The service caps at 2,000 and flags `exceededTransferLimit` on a 200, which
    is the same silent-truncation shape the USGS structures loader shipped with
    for weeks. 642 fits in one page today; the paging is here so that stops
    being load-bearing.
    """
    feats, offset = [], 0
    while True:
        page = requests.get(SERVICE + "/query", params={
            "where": "1=1", "outFields": "Library,LibraryType", "outSR": 4326,
            "f": "geojson", "geometryPrecision": 6,
            "resultRecordCount": PAGE, "resultOffset": offset,
        }, timeout=300).json()
        got = page.get("features") or []
        feats += got
        more = page.get("exceededTransferLimit") or \
            (page.get("properties") or {}).get("exceededTransferLimit")
        if not (more and got):
            break
        offset += len(got)
    if len(feats) < MIN_STATEWIDE:
        fail("statewide layer returned %d features, expected at least %d"
             % (len(feats), MIN_STATEWIDE))
    return feats


def county_outline(slug):
    path = os.path.join(APP_DIR, "%s-county-outline.json" % slug)
    if not os.path.exists(path):
        fail("no shipped outline for %s (%s)" % (slug, path))
    with open(path, encoding="utf-8") as fh:
        return clean(unary_union([shape(f["geometry"])
                                  for f in json.load(fh)["features"]]))


def build_county(cfg, libs, tree, verbose=True):
    outline = county_outline(cfg["slug"])
    inland = outline.boundary.buffer(SLIVER_REACH_M * DEG)
    kept, dropped, excluded = [], [], []
    unsimplified = []
    for idx in tree.query(outline):
        name, ltype, geom = libs[idx]
        if not geom.intersects(outline):
            continue
        clip = clean(geom.intersection(outline))
        if clip.is_empty or clip.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        m2 = clip.area * M2_PER_DEG2
        if clean(clip.difference(inland)).is_empty:
            dropped.append((name, m2))
            continue
        # A BODY THE COUNTY'S OWN TAX ROLL DOES NOT LEVY FOR IS NOT IN THIS
        # COUNTY, however far its polygon reaches in. SLIVER_REACH_M settles a
        # border patch by SHAPE and cannot settle one that reaches further:
        # Hayner Public Library District, seated in Madison County, reaches
        # 21 m into Macoupin over 0.060 km2 — twice the reach rule and so
        # kept by it — while not one of Macoupin's 224 tax codes pays Hayner a
        # cent. Two independently drawn boundaries disagreeing along a county
        # line is what that is, and the Clerk is the authority on membership.
        # Each such body is DECLARED with the reach that was measured, never
        # derived from the expected set: an undeclared newcomer must fail the
        # count gate below rather than be filtered away, and a declared one
        # that stops reaching in must fail too, so the entry cannot rot.
        if name in (cfg.get("clerk_excluded") or {}):
            # MEASURE the reach rather than echo the declared one. A printed
            # number a builder did not compute is a comment wearing a
            # measurement's clothes, and the declared value is here to be
            # CHECKED: if the polygon moves, the entry must stop matching.
            polys = ([clip] if clip.geom_type == "Polygon" else list(clip.geoms))
            reach_m = max((outline.boundary.distance(Point(c))
                           for poly in polys
                           for c in poly.exterior.coords), default=0.0) / DEG
            excluded.append((name, m2, reach_m))
            continue
        if not name or not str(name).strip():
            fail("%s: a polygon has no Library name" % cfg["slug"])
        if not ltype or not str(ltype).strip():
            # one untyped row exists statewide (Sandoval Public Library); it is
            # named rather than silently shipped with a blank governance type
            print("  NOTE %s: %r has no LibraryType and ships without one"
                  % (cfg["slug"], name))
        simple = clip.simplify(SIMPLIFY_M * DEG, preserve_topology=True)
        if simple.is_empty or simple.geom_type not in ("Polygon", "MultiPolygon"):
            simple = clip
        lost_m2 = (clip.area - simple.area) * M2_PER_DEG2
        if simple.area < MIN_AREA_RETAINED * clip.area and lost_m2 > MIN_AREA_LOST_M2:
            # THE ANSWER TO "THIS SHAPE CANNOT BE SIMPLIFIED SAFELY" IS TO NOT
            # SIMPLIFY IT, not to loosen the rule that noticed. Simplification
            # eats a long thin reach over a county line far harder than a
            # compact district — this file already records 10 m destroying
            # Pearl City's Carroll slice, and 5 m does the same to Putnam
            # County PLD's Marshall slice (7.5%, 25,735 m2). Full precision on
            # such a polygon costs a few KB; the alternative costs real ground.
            unsimplified.append((cfg["slug"], name,
                                 100.0 * (1 - simple.area / clip.area), lost_m2))
            simple = clip
        kept.append((str(name).strip(), (str(ltype).strip() if ltype else None), simple))

    kept.sort(key=lambda k: k[0])

    # THE EXCLUSION LIST IS RE-AUDITED EVERY RUN, in both directions — the shape
    # ACCEPTED_DROPS and EXPECTED_UNREACHABLE already have in this repo.
    if cfg.get("clerk_excluded"):
        seen = {n for n, _, _ in excluded}
        declared = set(cfg["clerk_excluded"])
        if seen != declared:
            fail("%s: the Clerk-excluded set moved. no longer reaching in: %s; "
                 "reaching in but not declared: %s"
                 % (cfg["slug"], sorted(declared - seen), sorted(seen - declared)))
        for n, m2, reach_m in sorted(excluded):
            want_m = cfg["clerk_excluded"][n]
            if abs(reach_m - want_m) > 1.0:
                fail("%s: %r now reaches %.1f m into the county, not the %.1f m "
                     "this exclusion was measured at — re-measure before "
                     "re-declaring it" % (cfg["slug"], n, reach_m, want_m))
            if reach_m <= SLIVER_REACH_M:
                fail("%s: %r reaches only %.1f m in, which the sliver rule "
                     "already drops — retire this exclusion rather than keeping "
                     "a second reason for the same outcome"
                     % (cfg["slug"], n, reach_m))
            print("  excluded %r — reaches %.1f m into the county over %.3f km2, "
                  "and no county tax code levies for it" % (n, reach_m, m2 / 1e6))

    if cfg.get("expect") is not None:
        if len(kept) != cfg["expect"]:
            fail("%s: %d libraries, expected %d (got: %s)"
                 % (cfg["slug"], len(kept), cfg["expect"], [k[0] for k in kept]))
    else:
        # NO HAND-VERIFIED COUNT FOR THE WITNESS COUNTIES — so the SHIPPED FILE
        # is the baseline, which is check_roster_retention.py's rule: a field is
        # protected the moment it first ships, with nothing to configure. A
        # county that gains a library is a publisher addition and passes; one
        # that LOSES a library fails, because that is the shape of a source
        # quietly changing under us. A first build has no baseline and only has
        # to find at least one.
        if not kept:
            fail("%s: the statewide layer returned no library for this county, "
                 "which contradicts the 2026-09-05 sweep that found every one "
                 "of the 65 answered" % cfg["slug"])
        prior = os.path.join(APP_DIR, "%s-library-districts.json" % cfg["slug"])
        if os.path.exists(prior):
            with open(prior, encoding="utf-8") as fh:
                was = len(json.load(fh).get("features") or [])
            if len(kept) < was:
                fail("%s: %d libraries now, %d in the shipped file — the source "
                     "lost one. Check the publisher before rebuilding."
                     % (cfg["slug"], len(kept), was))

    # THE CLERK GATE. Only Carroll has a county-published list to check against,
    # and it is the reason this source is trusted at all — so it is enforced
    # rather than remembered.
    if cfg.get("clerk_names"):
        got = {n for n, _, _ in kept}
        if got != cfg["clerk_names"]:
            fail("%s: the layer no longer matches the County Clerk's own tax "
                 "lines. missing %s; unexpected %s"
                 % (cfg["slug"], sorted(cfg["clerk_names"] - got), sorted(got - cfg["clerk_names"])))

    # SEPARATE SERVICE AREAS MUST NOT OVERLAP: a library district is a taxing
    # body you live inside, so two of them cannot both contain the same ground.
    #
    # RULED OUT BY SHAPE, NOT BY AREA — the rule this file already argues for
    # at SLIVER_REACH_M, applied to the check that never got it. Measured across
    # all 102 counties on 2026-09-06, the layer has 62 overlapping pairs and
    # AREA does not separate them: the largest inside a county this builder
    # writes is Livingston's Chatsworth/Piper City pair at 104,503 m2, which is
    # a ribbon 6.7 m WIDE running along a shared boundary — two independently
    # digitised lines, not shared ground — while DuPage's genuine 33.2 m-wide
    # Addison/Bensenville overlap covers only 5,793 m2. An area gate fails the
    # artifact and passes the real one, which is exactly backwards, and the
    # 25,000 m2 threshold this check used to carry did precisely that.
    #
    # MEAN WIDTH IS 2 x AREA / PERIMETER, WHICH IS A RIBBON'S WIDTH. That is
    # the right formula for what this gate is built to dismiss — a long thin
    # patch between two lines drawn apart — and it UNDER-REPORTS a compact one:
    # for a disc, 2A/P is the radius, so a blob-shaped overlap reads at about
    # half its true width and needs to be twice as wide to trip the ceiling.
    # Nothing here is affected — both statewide exceedances are long ribbons,
    # and neither is in a county this builder writes — but the next chunky
    # overlap will be under-reported, so this is recorded rather than left for
    # someone to rediscover from a gate that quietly passed.
    #
    # The floor is twice SIMPLIFY_M for the
    # same reason SLIVER_REACH_M is: an overlap no wider than the distance
    # simplification alone can move a line is not evidence of shared ground.
    # Above it sit exactly two pairs statewide, and NEITHER is in a county this
    # builder writes — Peoria (321.8 m, 580,701 m2) and DuPage (33.2 m) both
    # ship their libraries from their own county publishers.
    for i, (na, _, ga) in enumerate(kept):
        for nb, _, gb in kept[i + 1:]:
            if not ga.intersects(gb):
                continue
            ov = clean(ga.intersection(gb))
            if ov.is_empty or ov.length <= 0:
                continue
            m2 = ov.area * M2_PER_DEG2
            width_m = 2.0 * m2 / (ov.length / DEG)
            if width_m > OVERLAP_WIDTH_M:
                fail("%s: %r and %r overlap over %.0f m2 at a mean width of "
                     "%.1f m (ceiling %.0f m) — two library service areas "
                     "cannot both contain the same ground, and this one is too "
                     "wide to be two lines drawn apart"
                     % (cfg["slug"], na, nb, m2, width_m, OVERLAP_WIDTH_M))

    feats = []
    for name, ltype, geom in kept:
        gm = json.loads(json.dumps(mapping(geom)))

        def rnd(c):
            return round(c, 5) if isinstance(c, (int, float)) else [rnd(x) for x in c]
        gm["coordinates"] = rnd(gm["coordinates"])
        props = {"library": name}
        if ltype:
            props["type"] = ltype
        feats.append({"type": "Feature", "properties": props, "geometry": gm})
    fc = {"type": "FeatureCollection", "features": feats}

    for lat, lng, want in (cfg.get("probes") or ()):
        pt = Point(lng, lat)
        hits = [f["properties"]["library"] for f in feats
                if shape(f["geometry"]).contains(pt)]
        got = hits[0] if hits else None
        if verbose:
            print("  probe %.4f,%.4f -> %-40s [%s]"
                  % (lat, lng, got or "no library district", "ok" if got == want else "FAIL"))
        if got != want:
            fail("%s: probe %.4f,%.4f expected %r, got %r"
                 % (cfg["slug"], lat, lng, want, got))

    if unsimplified:
        UNSIMPLIFIED.extend(unsimplified)
        if verbose:
            for _, n, pct, m2 in unsimplified:
                print("  full precision kept for %r — simplifying at %.0f m "
                      "would have cost %.1f%% of it (%.0f m2)"
                      % (n, SIMPLIFY_M, pct, m2))
    if verbose and dropped:
        print("  border slivers dropped (never reach %.0f m inside the county; "
              "each body is seated in a neighbouring county): %s"
              % (SLIVER_REACH_M, ", ".join("%s %.0f m2" % (n, m) for n, m in dropped)))
    return fc


# ---------------------------------------------------------------------------
# THE PLACE WITNESS.
#
# WHAT IT TESTS. The layer types every polygon with `LibraryType` — the real
# Illinois governance vocabulary: District, City, Village, Town, Township and
# two "(contracting)" variants. That column makes a CHECKABLE claim. A CITY or
# VILLAGE library's boundary IS the municipality, and a TOWNSHIP library's IS
# the township; both are units the Census Bureau draws independently, so those
# 278 polygons can be checked against a publisher who has never heard of this
# layer. A library DISTRICT is drawn by referendum and nobody else publishes
# it — those 361 have no witness and this gate says so rather than pretending.
#
# WHY IT REPLACES PROBES FOR 65 COUNTIES. Two hand-picked points per county
# test two points. This tests every polygon that CAN be tested, in every county
# at once, against geometry from a different government — and it discriminates
# in both directions, which is the property a confirming-only check lacks:
# municipal libraries match their place at a median IoU of 0.968, while library
# DISTRICTS match at a median of 0.063. If the layer were quietly redrawing
# municipalities and labelling some of them "District", that second number
# would be high. It is not, so the type column is carrying real information.
#
# THREE MEASURED READINGS, 2026-09-06, and the floors are set below them rather
# than at them: township n=30 median 0.997 MIN 0.978; municipal n=206 median
# 0.968, 98.1% at or above 0.70; district n=209 median 0.063. Each is quoted
# WITH ITS DATE because each moves with the publisher: the district figure read
# 0.056 on 2026-09-05, a day earlier, on a slightly different candidate set.
#
# A NAME MATCH IS NOT A WITNESS UNLESS THE TWO SHAPES ACTUALLY TOUCH. Ten
# library names collide with a same-named place elsewhere in Illinois —
# Springfield's LINCOLN LIBRARY normalises to "lincoln" and finds the City of
# Lincoln forty miles away in Logan County. Scoring that pair would report 0.000
# and mean nothing. A pair with no overlap at all is therefore reported as a
# spurious name match and never scored, and the COUNT of them is itself gated,
# so a real collapse cannot hide by disqualifying itself.
PLACES_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
              "tigerWMS_Census2020/MapServer/26/query")     # Incorporated Places
COUSUB_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
              "tigerWMS_Census2020/MapServer/20/query")     # County Subdivisions

WITNESS_TOWNSHIP_FLOOR = 0.90       # measured min 0.978
WITNESS_MUNICIPAL_FLOOR = 0.70      # 98.1% of 206 clear it
WITNESS_MUNICIPAL_SHARE = 0.95      # ...and at least this share must
WITNESS_MUNICIPAL_MEDIAN = 0.90     # measured 0.968
WITNESS_DISTRICT_MEDIAN = 0.20      # measured 0.063 (2026-09-06) — the discriminator
WITNESS_MIN_SCORED = 210            # 236 scored today; a floor, so a gate that
                                    # stops finding pairs fails instead of
                                    # passing vacuously on an empty set
WITNESS_MAX_SPURIOUS = 20           # 10 today

# A MUNICIPAL LIBRARY WHOSE OWN GEOMETRY CONTRADICTS ITS OWN TYPE. Declared
# with the value measured, re-audited in both directions every run: a new one
# fails, a recorded one that has moved fails, and an entry whose subject now
# agrees fails so the exception cannot outlive its reason.
WITNESS_ANOMALIES = {
    # Typed Village — "my boundary is the village" — and drawn at 300.7 km2
    # against the Village of Coulterville's 1.44 km2, 209x. The village sits
    # ENTIRELY inside it, so a reader in Coulterville is answered correctly; it
    # is the other 299 km2 that this cannot vouch for. Which half is wrong, the
    # type or the polygon, is not decided here and is not guessed: gap record
    # `coulterville-library-extent`. Its Randolph slice has shipped since
    # 2026-09-05 and its siblings in that county are village-sized (Evansville
    # 2.07 km2, Tilden 2.48) — this one is 53.98.
    "Coulterville Public Library": 0.005,
}
WITNESS_ANOMALY_TOLERANCE = 0.02


def _norm_unit(s):
    """Strip the library vocabulary so a name can be compared to a place name."""
    s = (s or "").lower()
    s = re.sub(r"\b(public|community|memorial|free|district|library|libraries|"
               r"the|of|township|twp|city|village|town)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def _tiger_units(url):
    """Every Illinois feature from a TIGERweb layer, paged, refusing truncation."""
    out, offset = [], 0
    while True:
        page = requests.get(url, params={
            "where": "STATE='17'", "outFields": "BASENAME", "outSR": 4326,
            "f": "geojson", "geometryPrecision": 6,
            "resultRecordCount": 1000, "resultOffset": offset,
        }, timeout=300).json()
        got = page.get("features") or []
        out += got
        if not (page.get("exceededTransferLimit") and got):
            break
        offset += len(got)
    index = {}
    for f in out:
        if not f.get("geometry"):
            continue
        index.setdefault(_norm_unit(f["properties"]["BASENAME"]), []).append(
            clean(shape(f["geometry"])))
    return index


def place_witness(libs):
    """Check the layer against Census 2020 geography. Returns nothing; fails."""
    places, cousubs = _tiger_units(PLACES_URL), _tiger_units(COUSUB_URL)
    print("place witness: %d Census place name(s), %d county-subdivision name(s)"
          % (len(places), len(cousubs)))
    scores, spurious, unwitnessed = {}, [], 0
    for name, ltype, geom in libs:
        kind = (ltype or "").split(" ")[0]
        if kind == "Township":
            index = cousubs
        elif kind in ("City", "Village", "Town"):
            index = places
        else:
            unwitnessed += 1            # District, and the one untyped row
            continue
        cands = [c for c in index.get(_norm_unit(name), []) if c.intersects(geom)]
        if not cands:
            if index.get(_norm_unit(name)):
                spurious.append(name)
            else:
                unwitnessed += 1
            continue
        best = 0.0
        for c in cands:
            union = geom.union(c).area
            if union:
                best = max(best, geom.intersection(c).area / union)
        scores.setdefault("Township" if kind == "Township" else "municipal",
                          []).append((best, name))

    # Districts are scored too — NOT to confirm them, but to prove the type
    # column means something. A district that matched its namesake municipality
    # would be a municipality mislabelled.
    district_scores = []
    for name, ltype, geom in libs:
        if not (ltype or "").startswith("District"):
            continue
        cands = [c for c in places.get(_norm_unit(name), []) if c.intersects(geom)]
        for c in cands:
            union = geom.union(c).area
            if union:
                district_scores.append(geom.intersection(c).area / union)
                break

    town = sorted(s for s, _ in scores.get("Township", []))
    muni = sorted(s for s, _ in scores.get("municipal", []))
    scored = len(town) + len(muni)
    if scored < WITNESS_MIN_SCORED:
        fail("place witness scored only %d polygon(s), expected at least %d — "
             "the join stopped finding pairs, so the gate would pass vacuously"
             % (scored, WITNESS_MIN_SCORED))
    if len(spurious) > WITNESS_MAX_SPURIOUS:
        fail("place witness found %d name(s) matching a census unit they do not "
             "touch (at most %d expected): %s"
             % (len(spurious), WITNESS_MAX_SPURIOUS, sorted(spurious)))

    def median(v):
        return v[len(v) // 2] if v else 0.0

    print("  township  n=%d median %.3f min %.3f" % (len(town), median(town),
                                                     town[0] if town else 0.0))
    print("  municipal n=%d median %.3f  %.1f%% at/above %.2f"
          % (len(muni), median(muni),
             100.0 * sum(1 for s in muni if s >= WITNESS_MUNICIPAL_FLOOR) / max(1, len(muni)),
             WITNESS_MUNICIPAL_FLOOR))
    print("  district  n=%d median %.3f (LOW is correct — a district is not the "
          "municipality it is named for)" % (len(district_scores), median(sorted(district_scores))))
    print("  no witness: %d polygon(s); spurious name match: %d"
          % (unwitnessed, len(spurious)))

    declared = dict(WITNESS_ANOMALIES)
    for score, name in scores.get("municipal", []) + scores.get("Township", []):
        if name in declared:
            want = declared.pop(name)
            if abs(score - want) > WITNESS_ANOMALY_TOLERANCE:
                fail("place witness: %r now scores %.3f against the %.3f it was "
                     "declared at — re-measure before re-declaring it"
                     % (name, score, want))
            if score >= WITNESS_MUNICIPAL_FLOOR:
                fail("place witness: %r now agrees with its census unit (%.3f) — "
                     "retire its WITNESS_ANOMALIES entry rather than keeping an "
                     "exception nothing needs" % (name, score))
            print("  ANOMALY %r scores %.3f, declared and recorded as a gap"
                  % (name, score))
    if declared:
        fail("place witness: WITNESS_ANOMALIES names %s, which the layer no "
             "longer publishes as a municipal or township library — an "
             "exception cannot outlive its subject" % sorted(declared))

    for score, name in sorted(scores.get("Township", [])):
        if score < WITNESS_TOWNSHIP_FLOOR:
            fail("place witness: township library %r matches its census "
                 "township at only %.3f (floor %.2f)"
                 % (name, score, WITNESS_TOWNSHIP_FLOOR))
    low = [(s, n) for s, n in scores.get("municipal", [])
           if s < WITNESS_MUNICIPAL_FLOOR and n not in WITNESS_ANOMALIES]
    share = 1.0 - len(low) / max(1, len(muni))
    if share < WITNESS_MUNICIPAL_SHARE:
        fail("place witness: only %.1f%% of %d municipal libraries match their "
             "census place at %.2f or better (floor %.0f%%): %s"
             % (100 * share, len(muni), WITNESS_MUNICIPAL_FLOOR,
                100 * WITNESS_MUNICIPAL_SHARE,
                ["%s %.3f" % (n, s) for s, n in sorted(low)]))
    if median(muni) < WITNESS_MUNICIPAL_MEDIAN:
        fail("place witness: municipal median fell to %.3f (floor %.2f)"
             % (median(muni), WITNESS_MUNICIPAL_MEDIAN))
    dm = median(sorted(district_scores))
    if dm > WITNESS_DISTRICT_MEDIAN:
        fail("place witness: library DISTRICTS now match their namesake "
             "municipality at a median of %.3f (ceiling %.2f). Either the layer "
             "has started redrawing municipalities as districts or LibraryType "
             "has stopped meaning anything — both make this source unusable."
             % (dm, WITNESS_DISTRICT_MEDIAN))


def run(check):
    feats = fetch_layer()
    print("build-statewide-library-districts: %d polygons from %s layer 11 (%s)"
          % (len(feats), "IL_Boundary_Layers", SOURCE_LABEL))
    libs, nesting_pairs = [], []
    for f in feats:
        if not f.get("geometry"):
            continue
        raw = shape(f["geometry"])
        g = clean(raw)
        if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        # This layer is the fleet's worst case for the ArcGIS GeoJSON export's
        # unnesting: the same query answers 446 interior rings as GeoJSON and
        # 1,663 as Esri JSON. clean() re-nests every one of them — measured
        # 2026-09-05, 0.000000 km2 apart once repaired (the RING COUNTS match
        # only after the repair, never before it) — and that
        # is a property, not a coincidence, so it is asserted rather than
        # assumed (scripts/arcgis_nesting.py).
        nesting_pairs.append((raw, g))
        libs.append((f["properties"].get("Library"),
                     f["properties"].get("LibraryType"), g))
    assert_nesting_repaired(nesting_pairs, "statewide library layer", fail)
    place_witness(libs)
    _append_witness_counties()
    tree = STRtree([g for _, _, g in libs])

    stale = []
    for cfg in COUNTIES:
        print("%s:" % cfg["slug"])
        fc = build_county(cfg, libs, tree)
        payload = json.dumps(fc, separators=(",", ":"))
        out = os.path.join(APP_DIR, "%s-library-districts.json" % cfg["slug"])
        types = sorted({f["properties"].get("type") or "(untyped)" for f in fc["features"]})
        if check:
            if not os.path.exists(out):
                stale.append(cfg["slug"] + " (missing)")
            else:
                with open(out, encoding="utf-8") as fh:
                    if fh.read() != payload:
                        stale.append(cfg["slug"])
            print("  %d libraries (%s)" % (len(fc["features"]), ", ".join(types)))
        else:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(payload)
            print("  wrote data/app/%s-library-districts.json (%d libraries, %.0f KB; %s)"
                  % (cfg["slug"], len(fc["features"]), len(payload) / 1024.0, ", ".join(types)))
    if len(UNSIMPLIFIED) > MAX_UNSIMPLIFIED:
        fail("%d polygon(s) had to ship at full precision because %.0f m "
             "simplification would have cost them real ground, and at most %d "
             "is the expected steady state — the source has changed shape: %s"
             % (len(UNSIMPLIFIED), SIMPLIFY_M, MAX_UNSIMPLIFIED,
                ["%s/%s %.1f%%" % (c, n, p) for c, n, p, _ in UNSIMPLIFIED]))
    if UNSIMPLIFIED:
        print("full precision kept for %d polygon(s) (ceiling %d): %s"
              % (len(UNSIMPLIFIED), MAX_UNSIMPLIFIED,
                 ", ".join("%s/%s" % (c, n) for c, n, _, _ in UNSIMPLIFIED)))
    if check:
        if stale:
            fail("shipped file(s) differ from a fresh build: " + ", ".join(stale))
        print("build-statewide-library-districts: OK — all %d shipped file(s) match "
              "a fresh build of the published layer" % len(COUNTIES))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="re-derive and compare against the shipped files")
    run(ap.parse_args().check)


if __name__ == "__main__":
    main()
