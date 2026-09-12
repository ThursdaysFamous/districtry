#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds data/app/metro-outline.json — for Wisconsin, the dissolved outline of
the counties whose county-board SUPERVISOR ROSTER ships — from Census TIGERweb.
Wisconsin's wash means something narrower than the reference fork's: every WI
layer answers statewide (the region ring, wi-state-outline.json, is the state),
so the coverage band claims only "the supervisor holding your district is
NAMED here". METRO_COUNTY_FIPS below is therefore the roster counties, and
DISPATCH_COUNTY_FIPS stays empty on purpose — this instance has no per-county
dispatch layers (its own comment says why). The served area is NOT required to
be one connected region (contiguity was retired as a shipping gate 2026-08-04
in the reference fork, and Wisconsin's 20-county ring was born disjoint —
9 rings on day one).

THE COUNTY LIST HERE IS A CLAIM ABOUT COVERAGE, SO IT HAS TO TRACK THE ROSTER.
The reference fork learned this the hard way: it shipped four counties' layers
without revisiting its list, and the wash went on greying them out — nothing
failed, because the anchors only assert the counties already listed. So: **when
a county's supervisor roster ships, add its FIPS here and give it an INSIDE
anchor in the same change, and delete its OUTSIDE anchor** (the rule #523's
commit message states). The OUTSIDE list is the other half of that guard — a
county named there can never be quietly served, because shipping it would fail
this build.

Why this exists: the out-of-scope wash (index.html, ENGINE `scope-mask`) marks
where the app's fullest answer ends. An unexplained grey band understates what
the app does — in Wisconsin's case the difference between "nothing here" and
"everything but the supervisor's name here" — so the wash and its legend
(COVERAGE_KEY) say exactly which claim is being made.

It also keeps a boot cost out: painting the wash from a live boundary fetch
cost the reference fork 669 ms in PSI's critical chain
(docs/OPTIMIZATION_PLAYBOOK.md) before it pre-built. This file is one small
pre-dissolved feature.

WHY A BUILD STEP RATHER THAN PER-COUNTY OUTLINES (reference-fork lesson kept
verbatim in spirit): the in-browser dissolve cancels an interior border only
when the two neighbours' rings share EXACT coordinates, and independently
simplified per-county files don't. A single TIGERweb query returns
topologically consistent geometry, which is what makes the dissolve sound.

The dissolve mirrors the app's `coverageOutlineRings` exactly: a segment walked
by two features is an interior border and is dropped; survivors chain back into
closed rings. Doing it here means the browser ships one feature with no interior
edges left to cancel. Disjoint regions fall out of the same walk — each closed
ring is chained independently — and group_rings() nests them into a MultiPolygon.
Wisconsin's roster counties exercise that path from day one — the file was a
MultiPolygon of 9 separate regions when 20 counties shipped — and the count
moves in BOTH directions as counties join. Both moves landed on 2026-08-29:
Iowa merged two regions into one, because it borders served Grant and Richland
on one side and served Dane and Green on the other, and Marinette opened a new
detached one in the northeast. Five went to four went back to five.
READ THE REGION COUNT FROM `--check`, NEVER FROM THIS SENTENCE. Each region is
verified by anchor, not by eye — a region mis-nested as a hole renders
identically and answers False to every containment test inside it (the
reference fork's island lesson).

Usage:
    python3 build_metro_outline.py                 # writes data/app/metro-outline.json
    python3 build_metro_outline.py --check         # verify the shipped file, write nothing
"""

import argparse
import json
import math
import os
import sys

# `requests` is imported INSIDE the one function that fetches, not at module
# scope: this module's pure-geometry helpers (simplify, rings_of,
# point_in_rings) are shared machinery other Wisconsin builders import rather
# than fork, and the county-outline slicer among them never touches the
# network — it slices the shipped county fabric. A module-scope import made
# that offline builder carry a dependency it does not use, which
# validate_workflow_deps.py refuses to let a workflow install for a script
# that never fetches.

TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")

# STATE-TEMPLATE SCAFFOLD — the coverage-ring county lists, empty on day one.
# bootstrap_state.py builds the initial metro-outline.json (the whole state)
# directly from TIGERweb; this script takes over when the fork begins
# COUNTY-KEYED growth (a layer that answers in some counties and not others,
# EXPANSION_GUIDE Part 2) — from then on, every served county's 3-digit FIPS
# joins METRO_COUNTY_FIPS, every county with a dispatch entry joins
# DISPATCH_COUNTY_FIPS, and the outline is REGENERATED here, never patched.
# BOTH must stay plain literal assignments at module top: validate_index.py
# reads them via ast.literal_eval without importing.
# The counties whose county board card names a SUPERVISOR. Wisconsin's
# district geometry is statewide — every county gets its district — so the
# coverage ring here answers the narrower question the wash exists to answer:
# where does the app stop giving you the WHOLE answer? Inside the ring the
# card names the person; in the rest of Wisconsin it names the district and
# links the county board, which is a real answer and is why that band is a
# partial wash rather than the outside one.
#
# THE RULE: when a county's roster ships, add its FIPS here WITH ITS INSIDE
# ANCHOR and drop its OUTSIDE anchor, in the same change. The mask is a claim
# about coverage, so it has to track the roster or it lies in one direction or
# the other — the reference instance greyed out four counties whose layers were
# answering because this list was not updated with them.
#
# THAT RULE WAS WRITTEN HERE AND ENFORCED NOWHERE, AND THIS INSTANCE THEN BROKE
# IT (2026-09-01). Buffalo, Calumet, Door, Jackson, Oconto, Pepin and Waupaca
# shipped their supervisors over two days and stayed under the wash the whole
# time — greyed out on the map while their cards named all 145 members — with
# every gate in the repo green. `--check` below could not catch it: it verifies
# the anchors this file already lists, so a county nobody added is green by
# construction. validate_index.py's dispatch-entry check could not either: it
# walks registerCountyLayer entries and this instance has none.
#
# `check_coverage_ring_tracks_roster()` in wi/scripts/validate_index.py is the
# gate now — METRO_COUNTY_FIPS must equal the county set in the shipped
# county-board-members.json, in BOTH directions, and it runs on every PR with
# no network. A rule with no gate is a comment.
METRO_COUNTY_FIPS = (
    "001", "003", "005", "007", "009", "011", "013", "015",
    "017", "019",
    "021", "023", "025", "027", "029", "031", "033", "035", "037",
    "039", "041", "043", "045", "047", "049", "051", "053", "055",
    "057",
    "059",
    "061", "063", "065", "067", "069", "071", "073", "075",
    "077", "078", "079", "081", "083", "085", "087", "089",
    "091", "093", "095", "097", "099", "101", "103", "105",
    "107", "109", "111", "113", "115", "117", "119", "121", "123",
    "125", "127", "129", "131", "133", "135", "137", "139",
    "141",
)
STATE_FIPS = "55"
# No dispatch entries: county-board is ONE statewide layer here, not a
# per-county dispatcher, so no county is keyed into it by id.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/wi/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation below runs on the SIMPLIFIED rings, so a
# tolerance that ever moved the edge past an anchor would fail the build.
SIMPLIFY_TOLERANCE_M = 25

# ADAMS IS WISCONSIN'S FIRST ENCLAVE (2026-08-29, when Columbia's roster
# shipped) and it is a HOLE in the wash rather than a bite out of its edge:
# every one of Adams's neighbours — Juneau, Wood, Portage, Waushara, Marquette
# and now Columbia — serves, so the dissolve closes a ring around it. Columbia
# moved the topology TWICE in the same join, and NEITHER MOVE WAS PREDICTED
# BEFORE THE BUILD RAN: it borders Dane on one side and Juneau and Marquette on
# the other, so it MERGED the southeast region into the west-central one, and
# that merge is what sealed Adams. THE RING COUNT DID NOT MOVE — six before and
# six after — because the region lost and the hole gained cancel; what moved is
# the POLYGON count, six to five. A count that stands still is not a topology
# that stood still, so read BOTH from `build_metro_outline.py --check` and from
# the anchors, never from a map in your head. Adams keeps its OUTSIDE anchor
# below, which is what proves the hole is a hole — a region mis-nested as a hole
# (or a hole mis-read as a region) renders identically and answers the opposite
# way to every containment test inside it.
#
# LINCOLN WAS THE SECOND ENCLAVE AND LASTED ONE DAY (opened 2026-09-02 when
# Langlade's roster shipped, closed the same day by Lincoln's own). Its five
# Illinois-style neighbours — Langlade, Marathon, Taylor, Price and Oneida —
# all serve, so Langlade's join sealed a ring around it and the count went 2
# to 3; Lincoln's join took it back to 2. TWO THINGS ARE WORTH THE NEXT
# READER'S TIME. An enclave is a county a reader can SEE missing, and seeing
# it is how it got fixed: the hole is what prompted the second look that
# found the county's map server. And the count that remains is NOT a hole —
# both rings are OUTER. Bayfield has been an ISLAND since it joined, its only
# neighbours being unserved Douglas, Ashland and Sawyer, so the file is a
# MultiPolygon of two regions with no interior ring at all. Read which is
# which from --check and from the anchors, never from the number alone.
#
# Points that MUST fall inside the dissolved outline (one per served county)
# and outside it — ring-closure alone is not proof that a dissolve kept every
# county. The template starts empty because no county-keyed layer exists yet;
# when the fork's first county joins, add its anchor here and OUTSIDE anchors
# for the unserved neighbours (the reference repo's file shows the discipline
# at fleet scale, including why every enclave carries its own outside anchor).
# One INSIDE anchor per served county and one OUTSIDE anchor per unserved
# county — ring closure alone is not proof a dissolve kept every county.
# Representative points taken from the shipped TIGER county geometry.
INSIDE = {
    "Adams": (43.94586, -89.77671),
    "Ashland": (46.64701, -90.68578),
    "Barron": (45.42366, -91.84865),
    "Bayfield": (46.6808, -91.18773),
    "Brown": (44.46004, -87.97772),
    "Buffalo": (44.31089, -91.72133),
    "Burnett": (45.89865, -92.36377),
    "Calumet": (44.06871, -88.22361),
    "Chippewa": (45.07456, -91.28766),
    "Clark": (44.72754, -90.61921),
    "Columbia": (43.46157, -89.30349),
    "Crawford": (43.20611, -90.88776),
    "Dane": (43.06959, -89.42476),
    "Dodge": (43.41296, -88.7031),
    "Door": (45.06344, -86.98152),
    "Douglas": (46.52585, -91.92275),
    "Dunn": (44.94602, -91.89321),
    "Eau Claire": (44.72335, -91.28595),
    "Florence": (45.86728, -88.37551),
    "Fond du Lac": (43.74103, -88.5229),
    "Forest": (45.72458, -88.86156),
    "Grant": (42.85909, -90.76231),
    "Green": (42.67898, -89.60243),
    "Green Lake": (43.80746, -89.02684),
    "Iowa": (43.0113, -90.13346),
    "Iron": (46.38983, -90.34647),
    "Jackson": (44.33432, -90.74153),
    "Jefferson": (43.02123, -88.77694),
    "Juneau": (43.94612, -90.13402),
    "Kenosha": (42.5743, -87.66848),
    "Kewaunee": (44.50222, -87.3097),
    "La Crosse": (43.90784, -91.12764),
    "Lafayette": (42.66023, -90.1317),
    "Langlade": (45.24922, -89.05229),
    "Lincoln": (45.33767, -89.73536),
    "Manitowoc": (44.11033, -87.53102),
    "Marathon": (44.90091, -89.76945),
    "Marinette": (45.28025, -88.00346),
    "Marquette": (43.81242, -89.39817),
    "Menominee": (44.98678, -88.73481),
    "Milwaukee": (43.01735, -87.58072),
    "Monroe": (43.94362, -90.61172),
    "Oconto": (45.02524, -88.30368),
    "Oneida": (45.68206, -89.54525),
    "Outagamie": (44.41639, -88.46364),
    "Ozaukee": (43.36679, -87.60391),
    "Pepin": (44.54575, -92.08728),
    "Pierce": (44.70099, -92.4242),
    "Polk": (45.46886, -92.41908),
    "Portage": (44.46479, -89.47499),
    "Price": (45.68002, -90.36068),
    "Racine": (42.72811, -87.68021),
    "Richland": (43.36279, -90.42886),
    "Rock": (42.66871, -89.07199),
    "Rusk": (45.46562, -91.10925),
    "Sauk": (43.39419, -89.89645),
    "Sawyer": (45.89772, -91.10962),
    "Shawano": (44.80705, -88.7373),
    "Sheboygan": (43.71856, -87.63869),
    "St. Croix": (45.03443, -92.45383),
    "Taylor": (45.20651, -90.48556),
    "Trempealeau": (44.28859, -91.34782),
    "Vernon": (43.57669, -90.77139),
    "Vilas": (46.07816, -89.43616),
    "Walworth": (42.66748, -88.54125),
    "Washburn": (45.8978, -91.78707),
    "Washington": (43.36763, -88.22925),
    "Waukesha": (43.01882, -88.30439),
    "Waupaca": (44.46164, -88.98014),
    "Waushara": (44.11364, -89.24186),
    "Winnebago": (44.06844, -88.64513),
    "Wood": (44.46637, -90.02113),
}
# EMPTY, AND THAT IS THE POINT. Every OUTSIDE anchor this file has ever carried
# was a Wisconsin county whose supervisors nobody here could name; Iron was the
# last, and it joined 2026-09-02. The dissolve is now the whole state, so there
# is no in-state ground left to prove the wash STOPS at — the negative test
# that remains is the smoke suite's own out-of-state point, which sits off the
# north-west corner. A county that ever leaves the roster puts its anchor back
# here, and check_coverage_ring_tracks_roster() in validate_index.py fails the
# merge gate until it does.
OUTSIDE = {}


def fetch_counties():
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
    import requests  # noqa: PLC0415 (see the module header)
    resp = requests.get(TIGERWEB, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": where,
        "outFields": "NAME,GEOID",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != len(METRO_COUNTY_FIPS):
        print("FATAL: TIGERweb returned %d counties, expected %d — the query or the "
              "service changed" % (len(feats), len(METRO_COUNTY_FIPS)), file=sys.stderr)
        sys.exit(1)
    return feats


def rings_of(feature):
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        return list(geom.get("coordinates") or [])
    if geom.get("type") == "MultiPolygon":
        return [r for poly in (geom.get("coordinates") or []) for r in poly]
    return []


def dissolve(features):
    """Drop every segment walked twice (an interior border), chain the rest.

    Mirrors index.html's coverageOutlineRings so the shipped file is exactly
    what the browser would have computed — one algorithm, two places, and the
    validation below proves this one.
    """
    counts, seg_pts = {}, {}
    for feat in features:
        for ring in rings_of(feat):
            for i in range(len(ring) - 1):
                a, b = tuple(ring[i][:2]), tuple(ring[i + 1][:2])
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                counts[key] = counts.get(key, 0) + 1
                seg_pts[key] = (a, b)

    adj = {}
    for key, n in counts.items():
        if n != 1:
            continue  # interior border — both neighbours walked it
        a, b = seg_pts[key]
        adj.setdefault(a, []).append((key, b))
        adj.setdefault(b, []).append((key, a))

    used, rings = set(), []
    for seed, n in counts.items():
        if n != 1 or seed in used:
            continue
        start, cur = seg_pts[seed][0], seg_pts[seed][1]
        used.add(seed)
        ring = [list(start), list(cur)]
        while cur != start:
            nxt = None
            for key, pt in adj.get(cur, ()):
                if key not in used:
                    nxt = (key, pt)
                    break
            if nxt is None:
                print("FATAL: open chain while dissolving — the counties do not tile "
                      "cleanly (a source change?)", file=sys.stderr)
                sys.exit(1)
            used.add(nxt[0])
            cur = nxt[1]
            ring.append(list(cur))
        rings.append(ring)
    return rings


def simplify(ring, tolerance_m=SIMPLIFY_TOLERANCE_M):
    """Douglas-Peucker. County borders are survey-grid straight lines and the
    east edge is the state line in Lake Michigan (not the shoreline), so this
    collapses ~2,665 vertices to ~60 with no visible change to a wash whose
    whole job is to say "coverage ends here". Distances are metres, with
    longitude compressed by cos(latitude) so the tolerance means the same thing
    on both axes."""
    if len(ring) < 3:
        return ring
    tol = tolerance_m / 111320.0
    scale = math.cos(math.radians(42.0))

    def perp(p, a, b):
        ax, ay = a[0] * scale, a[1]
        bx, by = b[0] * scale, b[1]
        px, py = p[0] * scale, p[1]
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    keep = {0, len(ring) - 1}
    stack = [(0, len(ring) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        worst, wi = 0.0, None
        for k in range(i + 1, j):
            d = perp(ring[k], ring[i], ring[j])
            if d > worst:
                worst, wi = d, k
        if worst > tol and wi is not None:
            keep.add(wi)
            stack.append((i, wi))
            stack.append((wi, j))
    out = [ring[i] for i in sorted(keep)]
    if out[0] != out[-1]:
        out.append(out[0])  # a ring must close
    return out


def point_in_rings(lat, lng, rings):
    """Even-odd test against every ring, matching the app's pointInGeometry."""
    inside = False
    for ring in rings:
        for i in range(len(ring) - 1):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[i + 1][0], ring[i + 1][1]
            if (y1 > lat) != (y2 > lat):
                if lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                    inside = not inside
    return inside


def validate(rings):
    problems = []
    for label, (lat, lng) in sorted(INSIDE.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s should be INSIDE the metro outline and is not" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s should be OUTSIDE the metro outline and is not" % label)
    return problems


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their holes.

    Needed from pass 4 on, when the served area stopped being one region. A
    two-ring Polygon means "ring 2 is a HOLE in ring 1", so emitting the detached
    Madison/St. Clair region that way would have claimed a hole in the
    served metro. The wash renders identically either way (it flattens every ring into a
    cut-out), which is precisely why this had to be reasoned about rather than
    eyeballed: the bug would be invisible on the map and wrong to anything that
    ever runs a containment test — including the app's own pointInGeometry, which
    would answer False for every point in Madison County.
    """
    ordered = sorted(rings, key=len, reverse=True)
    polys = []  # [outer, hole, hole, ...]
    for ring in ordered:
        lng, lat = ring[0][0], ring[0][1]
        for poly in polys:
            if point_in_rings(lat, lng, [poly[0]]):
                poly.append(ring)  # enclosed -> a hole in that outer
                break
        else:
            polys.append([ring])
    return polys


def check_envelopes(rings):
    """The input shell must reach at least as far as the data does.

    METRO_BBOX (geocoder viewbox + the geolocate gate) and PERMALINK_GATE (the
    #point= sanity bound) are hand-set values in metro-worksheet.json that
    describe "where we serve" — and they do not move when a county is added, so
    they go stale silently and in a way no other gate sees. That has now bitten
    three times: LaSalle and Kankakee fell outside METRO_BBOX from research pass
    2 onward, Rockford's permalink was being dropped until pass 4 widened the
    gate, and Bloomington's was dropped again one county later.

    The failure is invisible because it is a REJECTION: a shared #point= link
    silently loses its point, and "Use my location" in a served county reports
    the user is outside the covered area. Nothing errors. So this turns it into a
    build failure — add a county whose geometry pokes outside either envelope and
    the outline build stops until the worksheet is widened to match.

    Checked against the SIMPLIFIED rings, i.e. the geometry actually shipped.
    """
    xs = [p[0] for ring in rings for p in ring]
    ys = [p[1] for ring in rings for p in ring]
    env = {"minLng": min(xs), "maxLng": max(xs), "minLat": min(ys), "maxLat": max(ys)}
    try:
        with open(WORKSHEET, encoding="utf-8") as f:
            worksheet = json.load(f)
    except (IOError, ValueError) as exc:
        return ["could not read metro-worksheet.json (%s)" % exc]

    problems = []
    for key in ("metro_bbox", "permalink_gate"):
        box = worksheet.get(key)
        if not box:
            problems.append("metro-worksheet.json has no %s" % key)
            continue
        for edge, cmp_ in (("minLng", "gt"), ("minLat", "gt"), ("maxLng", "lt"), ("maxLat", "lt")):
            if edge not in box:
                problems.append("%s is missing %s" % (key, edge))
                continue
            too_tight = box[edge] > env[edge] if cmp_ == "gt" else box[edge] < env[edge]
            if too_tight:
                problems.append(
                    "%s.%s is %.4f but the served area reaches %.4f — widen it, or a "
                    "point there is silently rejected" % (key, edge, box[edge], env[edge]))
    return problems


def build_geojson(rings):
    polys = group_rings(rings)
    geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "%d-county coverage area" % len(METRO_COUNTY_FIPS)},
            "geometry": geometry,
        }],
    }


# --- the anchor registry: one anchor per served county, and no county both ----
#
# THE ANCHOR LIST IS THIS GATE'S OWN SURFACE, and until 2026-09-02 nothing
# checked it. `--check` validates the SHIPPED ring against INSIDE/OUTSIDE and
# never rebuilds from METRO_COUNTY_FIPS, so a county added to that tuple
# without an anchor is green by construction — the ring is simply never asked
# about it. That is how Wisconsin greyed out seven counties for two days with
# every gate in the repo passing, and what its validator's
# check_coverage_ring_tracks_roster was written for.
#
# The convention every instance already follows is one INSIDE anchor per served
# county, so the count identity below turns "somebody added a FIPS and forgot
# the anchor" (or the reverse) into a failure, offline, from source alone. A
# true rebuild-and-diff would be stronger and needs TIGERweb, which is why it
# is not in CI; this is what can be proven without the network.
#
# KEY SHAPES DIFFER BY INSTANCE AND BOTH ARE CORRECT. The reference instance
# keys anchors "Place (County)" because its ring is a subset of its state and a
# reader needs to know which county a town vouches for; the statewide instances
# whose ring IS the state key them by county name alone. A check that demanded
# either shape would fail correct instances, so county_of() accepts both.
def county_of(anchor_key):
    """The county an anchor vouches for, from either key shape.

    "Marion (Williamson)" -> "Williamson"; "Bond, 3rd Circuit" -> "Bond";
    "Fond du Lac" -> "Fond du Lac".
    """
    key = anchor_key.strip()
    # No regex on purpose: these modules import only what they build with, and
    # a gate should not add a dependency to say something this simple.
    if key.endswith(")") and "(" in key:
        key = key[key.rindex("(") + 1:-1]
    return key.split(",")[0].strip()


def check_anchor_registry():
    """Problems with the anchor lists themselves, as a list of strings."""
    problems = []
    if len(INSIDE) != len(METRO_COUNTY_FIPS):
        problems.append(
            "%d INSIDE anchor(s) for %d served county/counties — every served "
            "county carries exactly one anchor, so these must match. A county "
            "added to METRO_COUNTY_FIPS without an anchor is never tested "
            "against the ring, and an anchor with no county is testing ground "
            "the wash no longer claims."
            % (len(INSIDE), len(METRO_COUNTY_FIPS)))
    seen = {}
    for key in INSIDE:
        seen.setdefault(county_of(key), []).append(key)
    for county, keys in sorted(seen.items()):
        if len(keys) > 1:
            problems.append(
                "%s has %d INSIDE anchors (%s) — with one anchor per county the "
                "count identity above cannot tell a doubled county from a "
                "missing one" % (county, len(keys), ", ".join(sorted(keys))))
    both = sorted({county_of(k) for k in INSIDE} & {county_of(k) for k in OUTSIDE})
    if both:
        problems.append(
            "%s appear(s) in BOTH INSIDE and OUTSIDE — when a county joins, its "
            "OUTSIDE anchor moves rather than being left behind, or the ring is "
            "asserted to both contain and exclude the same ground" % ", ".join(both))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--check", action="store_true",
                    help="validate the shipped file instead of rebuilding")
    args = ap.parse_args()

    if args.check:
        with open(args.out) as f:
            shipped = json.load(f)
        # rings_of() flattens Polygon and MultiPolygon alike, so the anchor test
        # reads the file the same way whether or not the served area is one region.
        rings = rings_of(shipped["features"][0])
        problems = (check_anchor_registry() + validate(rings)
                    + check_envelopes(rings))
        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        if problems:
            sys.exit(1)
        print("metro-outline: OK — %d ring(s), %d vertices, all %d inside / %d outside "
              "anchors correct" % (len(rings), sum(len(r) for r in rings),
                                   len(INSIDE), len(OUTSIDE)), file=sys.stderr)
        return

    rings = [simplify(r) for r in dissolve(fetch_counties())]
    problems = (check_anchor_registry() + validate(rings)
                + check_envelopes(rings))
    for p in problems:
        print("FATAL: %s" % p, file=sys.stderr)
    if problems:
        print("FATAL: refusing to write an outline that misplaces its anchors",
              file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w") as f:
        json.dump(build_geojson(rings), f, separators=(",", ":"))
        f.write("\n")
    size = os.path.getsize(args.out)
    print("wrote %s: %d ring(s), %d vertices, %.1f KB"
          % (args.out, len(rings), sum(len(r) for r in rings), size / 1024.0),
          file=sys.stderr)


if __name__ == "__main__":
    main()
