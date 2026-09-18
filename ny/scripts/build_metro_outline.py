#!/usr/bin/env python3
"""
Metro Outline Builder (the scope mask's coverage geometry)
==========================================================
Builds two files for the New York instance's out-of-scope wash: the coverage
ring (`ny/data/app/metro-outline.json`, the dissolved outline of the five
boroughs) and the region ring (`ny/data/app/ny-state-outline.json`, New York
State itself, from Census TIGERweb).

WHY TWO FILES. New York is a THREE-BAND instance (docs/EXPANSION_GUIDE.md
§2.5.1): the five boroughs are where the city layers (council, community
board, DOE zones, and more) answer, but three statewide layers — the
congressional, state senate and state assembly district polygons, each with
its own roster already shipped — answer everywhere in New York State, not
only inside the city. So the wash needs three zones rather than two: inside
the boroughs everything answers, OUTSIDE NEW YORK nothing does, and in
between — the other 57 counties — the statewide legislative layers still
answer. The coverage key on the map names all three bands, and the key is
only honest if the region band it describes is actually drawn (§2.5.1: "a
three-band instance owes GEOMETRY as well as words"). This is dark for now:
`metro_bbox` and `permalink_gate` stay city-sized until go-live (PR 3), so
building these two files changes nothing a reader can reach yet.

A CORRECTION TO THE EXPANSION PLAN, RECORDED HERE SO THE NEXT READER DOES NOT
REPEAT IT. docs/NY_EXPANSION_PLAN.md's PR 2 section says to copy
`wi/scripts/build_metro_outline.py`. That is the wrong template. Wisconsin's
ring IS its whole state — every Wisconsin layer answers statewide, so its
wash is two zones dressed up with a narrower middle-band LABEL rather than a
real third geometry — and its builder is single-output: no `fetch_state()`,
no `--state-out`, no `STATE_OUTSIDE`, no `validate_state()`. New York needs
the two-output, three-band shape, which exists only in the reference fork's
root-level `scripts/build_metro_outline.py` (Illinois: the served counties
inside, unserved Illinois in the middle, outside Illinois outside). This file
ports THAT script's structure — `fetch_counties()` / `fetch_state()`,
`OUT_PATH` / `STATE_OUT_PATH`, `TIGERWEB` (counties, layer 1) and
`TIGERWEB_STATE` (states, layer 0) on the same MapServer, `INSIDE` /
`OUTSIDE` / `STATE_OUTSIDE`, `check_anchor_registry()`, `validate()`,
`validate_state()`, `containment_problems()`, `check_envelopes()` — and
takes the ANCHOR-KEY CONVENTION from Wisconsin and Iowa instead: those two
statewide instances key every anchor by bare county name (no state ring is a
subset of anything, so there is nothing to disambiguate), where the
reference fork keys "Place (County)" because its ring is a proper subset of
its state and a reader needs to know which county a town vouches for. New
York's OUTSIDE list here is EXHAUSTIVE over every one of the 57 counties the
ring does not serve — the condition the fleet's own docstring on that
convention ties it to — so it is keyed by bare county name, not "Place
(County)".

ANCHORS. All 62 anchors (5 INSIDE, 57 OUTSIDE) were measured on 2026-09-18
by point-in-polygon against New York's own TIGERweb county fabric and
verified before this file was written; none moved. They are carried here
unedited from that measurement, one per served county (a borough) and one
per unserved county, with the place each point sits at recorded in a
trailing comment so a reader can tell what ground an anchor stands on
without re-deriving it. STATE_OUTSIDE is new: six real places just across
New York's land and lake borders, one per neighbouring jurisdiction,
verified the same way against the state ring once it was built.

THE THREE RINGS ARE NOT A SIMPLIFICATION ARTIFACT, AND NEITHER FILE IS A
SINGLE POLYGON. Both outputs come out as a 3-ring MultiPolygon, measured
2026-09-18: one large ring plus two small ones, and the SAME two small rings
appear in both files. They are LIBERTY ISLAND (8 vertices, around
40.689 N 74.045 W) and ELLIS ISLAND (7 vertices, around 40.699 N 74.039 W),
both of which TIGERweb assigns to New York County and which are therefore
inside the five-borough dissolve and inside New York State alike, detached
from everything else by water. Each was confirmed by point-in-polygon
against the built rings and by a point query on the county layer, which
returns New York County for Liberty Island. Do not "tidy" them away: a
dissolve that drops them would shrink the coverage wash by two real pieces
of New York County, and a reader zoomed into the harbour would see the map
claim the Statue of Liberty is outside the area this app serves.

WHY THE COUNTY LIST HERE IS SHORT AND WILL GROW. METRO_COUNTY_FIPS is the
five boroughs only, because that is where a county-keyed layer answers today
— the borough/council/community-board tier and (once it ships) the
five-borough election-district layer. It is NOT "every county with a
statewide layer": the three legislative layers answer everywhere in New York
and are not a reason to add a county here (the county-keyed honesty test,
§3.5.1 — never join the ring for a rich statewide answer). DISPATCH_COUNTY_FIPS
is empty because no county-dispatched concept exists yet; it gains an entry
the day the first tranche-1 county (Westchester, Suffolk, Nassau or Erie)
ships a board or precinct layer, exactly as Illinois's dispatch table grew
county by county.

WHY A BUILD STEP RATHER THAN A LIVE FETCH, AND WHY THE SAME TOLERANCE FOR
BOTH FILES. The in-browser dissolve this mirrors cancels an interior border
only when two neighbouring rings share EXACT coordinates, which independently
simplified per-county files never do; one TIGERweb query returns topologically
consistent geometry, and building it here removes the 300+ KB statewide fetch
from the boot chain for what is, on the map, a decorative wash. The county
ring and the state ring are simplified at the SAME tolerance for the reason
docs/EXPANSION_GUIDE.md §2.5.1 states outright: where a served county fronts
the state's edge, the two rings trace the same coastline or river, and
simplified apart they would open slivers of a false middle band along it. New
York has no served county on the state's outer edge today — the five
boroughs sit well inside Long Island Sound and the Hudson — so this build has
no river seam to protect yet, but the tolerance is matched now so tranche 1
(Westchester fronts Connecticut and the Hudson; Suffolk fronts the Atlantic)
does not have to revisit it.

Usage:
    python3 build_metro_outline.py                 # writes both outline files
    python3 build_metro_outline.py --check          # verify the shipped files, write nothing
"""

import argparse
import json
import math
import os
import sys

# `requests` is imported INSIDE fetch_counties() and fetch_state() rather than
# here, matching the reference fork: those two are the only uses in this file
# and both are the TIGERweb build path, so a workflow that only CHECKS never
# needs the package installed at all.
TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")
# Layer 0 of the SAME MapServer is states where layer 1 is counties, so the
# state ring costs no new host and no new service.
TIGERWEB_STATE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                  "State_County/MapServer/0/query")

STATE_FIPS = "36"

# The five boroughs — the only counties where a county-keyed layer answers
# today (borough, council, community-board, and the rest of the city tier).
# See the module docstring: a statewide legislative answer is not a reason to
# add a county here.
METRO_COUNTY_FIPS = (
    "005",  # Bronx
    "047",  # Kings (Brooklyn)
    "061",  # New York (Manhattan)
    "081",  # Queens
    "085",  # Richmond (Staten Island)
)

# Empty on purpose: no county-dispatched concept has shipped yet. It gains its
# first entry the day tranche 1's first county (Westchester, Suffolk, Nassau
# or Erie — docs/NY_EXPANSION_PLAN.md) ships a board or precinct layer of its
# own, the way every Illinois county's dispatch entry landed here one at a
# time. An empty dict is a legitimate value for this table: Wisconsin's copy
# of this file carries the same empty dict for the same reason (no per-county
# dispatch layer exists there either), and the assertion below passes
# trivially against it.
DISPATCH_COUNTY_FIPS = {}

_UNLISTED = sorted(set(DISPATCH_COUNTY_FIPS.values()) - set(METRO_COUNTY_FIPS))
assert not _UNLISTED, (
    "DISPATCH_COUNTY_FIPS names county FIPS %s that METRO_COUNTY_FIPS omits — a "
    "county cannot be served and outside the coverage ring at the same time"
    % _UNLISTED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "metro-outline.json")
STATE_OUT_PATH = os.path.join(REPO_ROOT, "data", "app", "ny-state-outline.json")
WORKSHEET = os.path.join(REPO_ROOT, "metro-worksheet.json")

HEADERS = {"User-Agent": "districtry metro-outline builder (+https://districtry.com/ny/)"}
REQUEST_TIMEOUT = 180

# 25 m: the wash is a coverage hint, not a boundary claim, and at metro zoom
# this is sub-pixel. Validation runs on the SIMPLIFIED rings, so a tolerance
# that ever moved the edge past an anchor would fail the build. Matches the
# reference fork and Wisconsin/Iowa's copies — no instance has measured a
# reason to use a different value.
SIMPLIFY_TOLERANCE_M = 25

# Points that MUST fall inside the dissolved five-borough outline (one per
# served county) and points that must fall outside it (one per unserved New
# York county — all 57, since this list is exhaustive). Ring closure alone is
# not proof a dissolve kept every county; these are. Measured 2026-09-18 by
# point-in-polygon against New York's own TIGERweb county fabric; none moved.
#
# Keyed by BARE COUNTY NAME, the Wisconsin/Iowa convention, because OUTSIDE
# here is exhaustive over every county the ring does not serve — there is no
# ambiguity a "Place (County)" key would resolve that a bare name does not.
# Each value carries the measured point and a trailing comment naming the
# place it sits at, so a reader can tell what ground the anchor stands on.
INSIDE = {
    "Bronx": (40.8296, -73.9262),        # Yankee Stadium area, Bronx
    "Kings": (40.6938, -73.9903),        # Downtown Brooklyn (Borough Hall)
    "New York": (40.7580, -73.9855),     # Times Square, Manhattan
    "Queens": (40.7654, -73.8318),       # Flushing
    "Richmond": (40.6437, -74.0765),     # St. George, Staten Island (Borough Hall)
}

OUTSIDE = {
    "Albany": (42.66793, -73.77609),          # Albany (city)
    "Allegany": (42.13002, -77.91448),        # Wellsville (town)
    "Broome": (42.11606, -76.02878),          # Union (town)
    "Cattaraugus": (42.08286, -78.42939),     # Olean (city)
    "Cayuga": (42.93277, -76.56713),          # Auburn (city)
    "Chautauqua": (42.10139, -79.23681),      # Jamestown (city)
    "Chemung": (42.0925, -76.80897),          # Elmira (city)
    "Chenango": (42.53306, -75.52035),        # Norwich (city)
    "Clinton": (44.69591, -73.45659),         # Plattsburgh (city)
    "Columbia": (42.41164, -73.68227),        # Kinderhook (town)
    "Cortland": (42.60026, -76.17931),        # Cortland (city)
    "Delaware": (42.31356, -75.30969),        # Sidney (town)
    "Dutchess": (41.65972, -73.90937),        # Poughkeepsie (town)
    "Erie": (42.89623, -78.85364),            # Buffalo (city)
    "Essex": (44.23942, -73.9968),            # North Elba (town)
    "Franklin": (44.79648, -74.2859),         # Malone (town)
    "Fulton": (43.04727, -74.34839),          # Gloversville (city)
    "Genesee": (42.99892, -78.18188),         # Batavia (city)
    "Greene": (42.20248, -73.94093),          # Catskill (town)
    "Hamilton": (43.78622, -74.27507),        # Indian Lake (town)
    "Herkimer": (42.98343, -74.98918),        # German Flatts (town)
    "Jefferson": (44.07883, -75.77453),       # Le Ray (town)
    "Lewis": (43.81836, -75.52625),           # Lowville (town)
    "Livingston": (42.80467, -77.77131),      # Geneseo (town)
    "Madison": (43.09599, -75.89103),         # Sullivan (town)
    "Monroe": (43.18552, -77.61021),          # Rochester (city)
    "Montgomery": (42.94247, -74.18898),      # Amsterdam (city)
    "Nassau": (40.64101, -73.61237),          # Hempstead (town)
    "Niagara": (43.09955, -79.03075),         # Niagara Falls (city)
    "Oneida": (43.09831, -75.22567),          # Utica (city)
    "Onondaga": (43.03514, -76.14093),        # Syracuse (city)
    "Ontario": (42.98891, -77.42754),         # Victor (town)
    "Orange": (41.34029, -74.16712),          # Palm Tree (town)
    "Orleans": (43.23283, -78.20709),         # Albion (town)
    "Oswego": (43.46203, -76.5047),           # Oswego (city)
    "Otsego": (42.45576, -75.06349),          # Oneonta (city)
    "Putnam": (41.39034, -73.7248),           # Carmel (town)
    "Rensselaer": (42.74466, -73.67407),      # Troy (city)
    "Rockland": (41.12966, -74.11308),        # Ramapo (town)
    "Saratoga": (42.85407, -73.83319),        # Clifton Park (town)
    "Schenectady": (42.80359, -73.94052),     # Schenectady (city)
    "Schoharie": (42.67369, -74.44898),       # Cobleskill (town)
    "Schuyler": (42.46531, -76.79091),        # Hector (town)
    "Seneca": (42.91271, -76.79102),          # Seneca Falls (town)
    "St Lawrence": (44.67745, -75.0402),      # Potsdam (town)
    "Steuben": (42.32964, -77.30334),         # Bath (town)
    "Suffolk": (40.84445, -72.92411),         # Brookhaven (town)
    "Sullivan": (41.6507, -74.6736),          # Thompson (town)
    "Tioga": (42.09211, -76.19299),           # Owego (town)
    "Tompkins": (42.4425, -76.50046),         # Ithaca (city)
    "Ulster": (41.92749, -73.99551),          # Kingston (city)
    "Warren": (43.36922, -73.68534),          # Queensbury (town)
    "Washington": (43.34363, -73.5396),       # Kingsbury (town)
    "Wayne": (43.08712, -77.08626),           # Arcadia (town)
    "Westchester": (40.9444, -73.87333),      # Yonkers (city)
    "Wyoming": (42.75754, -78.01463),         # Perry (town)
    "Yates": (42.62371, -77.03318),           # Milo (town)
}


def fetch_counties():
    import requests
    where = "STATE='%s' AND COUNTY IN (%s)" % (
        STATE_FIPS, ",".join("'%s'" % c for c in METRO_COUNTY_FIPS))
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


def fetch_state():
    """New York itself, from layer 0 of the same MapServer.

    STATE_FIPS rather than STUSAB so the query keys on the same field the
    county half already uses; one feature is expected and anything else means
    the service moved."""
    import requests
    resp = requests.get(TIGERWEB_STATE, headers=HEADERS, timeout=REQUEST_TIMEOUT, params={
        "where": "STATE='%s'" % STATE_FIPS,
        "outFields": "NAME",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    resp.raise_for_status()
    feats = (resp.json() or {}).get("features") or []
    if len(feats) != 1:
        print("FATAL: TIGERweb returned %d state features, expected 1 — the query "
              "or the service changed" % len(feats), file=sys.stderr)
        sys.exit(1)
    return feats[0]


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
    """Douglas-Peucker, distances in metres with longitude compressed by
    cos(latitude) so the tolerance means the same thing on both axes. New
    York spans roughly 40.5N to 45.0N; 42 degrees is the middle of that range
    and close enough to the five boroughs (~40.6-40.9N) for the compression to
    be accurate where it matters most for this file's own ring."""
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


# Anchors for the STATE ring, six real places just across New York's borders,
# one per neighbouring jurisdiction: New Jersey (twice, since the five
# boroughs sit right against it), Pennsylvania (twice, the state's southern
# tier and its Lake Erie corner), Connecticut, Massachusetts and Quebec.
#
# UNLIKE THE REFERENCE FORK, THIS LIST NEEDS NO EXEMPTION SET. Illinois mixes
# one out-of-state anchor ("Milwaukee (WI)") into its OUTSIDE dict, to prove
# its coverage ring does not reach across the Wisconsin line, and so it needs
# a NON_ILLINOIS set to keep that one entry out of validate_state()'s "every
# OUTSIDE anchor must be inside the state ring" check. New York's OUTSIDE
# above carries no such entry — it is exhaustive over the 57 unserved New
# York counties and nothing else — so validate_state() below checks all of it
# with no exemption.
STATE_OUTSIDE = {
    "Newark (NJ)": (40.7357, -74.1724),        # west, hard against the boroughs
    "Scranton (PA)": (41.4090, -75.6624),      # south, the Southern Tier's border
    "Erie (PA)": (42.1292, -80.0851),          # west, the Lake Erie corner
    "Hartford (CT)": (41.7658, -72.6734),      # east
    "Pittsfield (MA)": (42.4501, -73.2454),    # northeast, the Berkshires border
    "Montreal (QC)": (45.5019, -73.5674),      # north, across the Canadian border
}


def containment_problems(coverage_rings, state_rings):
    """The served counties are New York counties, so their outline cannot
    reach outside the state ring — checked as ENVELOPES, not vertex by
    vertex.

    Vertex-exact containment is the wrong test and would fail honestly where
    a served county fronts the state line: the two rings would trace the same
    coastline or river, simplified independently, and legitimately land up to
    a tolerance or two apart there. New York has no such county in the ring
    yet (the five boroughs sit inside Long Island Sound and the Hudson), but
    the envelope check is the one worth having regardless — it catches the
    two files swapped, or one of them built for the wrong place, which would
    invert the wash rather than nudge it."""
    slack = 2 * SIMPLIFY_TOLERANCE_M / 111320.0

    def envelope(rings):
        pts = [p for r in rings for p in r]
        return (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))

    cw, cs, ce, cn = envelope(coverage_rings)
    sw, ss, se, sn = envelope(state_rings)
    problems = []
    for label, cov, st, inside in (("west", cw, sw, True), ("south", cs, ss, True),
                                   ("east", ce, se, False), ("north", cn, sn, False)):
        past = (cov < st - slack) if inside else (cov > st + slack)
        if past:
            problems.append(
                "the coverage outline reaches %.4f on the %s but the state ring "
                "stops at %.4f — the served area cannot leave New York, so one of "
                "the two files is for the wrong place" % (cov, label, st))
    return problems


def validate_state(rings):
    problems = []
    for label, (lat, lng) in sorted(INSIDE.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s is a served county and must be INSIDE the "
                            "state ring" % label)
    for label, (lat, lng) in sorted(OUTSIDE.items()):
        if not point_in_rings(lat, lng, rings):
            problems.append("%s is an unserved NEW YORK county and must be "
                            "INSIDE the state ring — the region band of the "
                            "wash exists for exactly these places" % label)
    for label, (lat, lng) in sorted(STATE_OUTSIDE.items()):
        if point_in_rings(lat, lng, rings):
            problems.append("%s is not in New York and must be OUTSIDE the "
                            "state ring" % label)
    return problems


def build_state_geojson(rings):
    polys = group_rings(rings)
    geometry = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                else {"type": "MultiPolygon", "coordinates": polys})
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "New York"},
            "geometry": geometry,
        }],
    }


def group_rings(rings):
    """Nest each ring under the ring that encloses it — outers, then their
    holes. A two-ring Polygon means "ring 2 is a HOLE in ring 1", so a detached
    region emitted that way would falsely claim a hole rather than a second
    outer ring. The wash renders identically either way (it flattens every
    ring into a cut-out), which is exactly why this has to be reasoned about
    rather than eyeballed: a mis-nested ring is invisible on the map and wrong
    to any containment test, including the app's own pointInGeometry."""
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
    describe "where we serve", and they do not move automatically when the
    coverage ring changes. Checked against the SIMPLIFIED rings, i.e. the
    geometry actually shipped. This reads the worksheet; it never writes it —
    both `metro_bbox` and `permalink_gate` stay city-sized through PR 2 by
    design (docs/NY_EXPANSION_PLAN.md), and today's five-borough ring is the
    same ground those two boxes were already set for, so this is expected to
    pass without either box moving."""
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
            "properties": {"name": "%d-borough coverage area" % len(METRO_COUNTY_FIPS)},
            "geometry": geometry,
        }],
    }


# --- the anchor registry: one anchor per served county, and no county both ----
#
# THE ANCHOR LIST IS THIS GATE'S OWN SURFACE. `--check` validates the SHIPPED
# ring against INSIDE/OUTSIDE and never rebuilds from METRO_COUNTY_FIPS, so a
# county added to that tuple without an anchor would be green by construction
# — the ring simply never gets asked about it. That is how Wisconsin greyed
# out seven counties for two days with every gate in the repo passing.
#
# The convention every instance follows is one INSIDE anchor per served
# county, so the count identity below turns "somebody added a FIPS and forgot
# the anchor" (or the reverse) into a failure, offline, from source alone.
#
# KEY SHAPES DIFFER BY INSTANCE AND BOTH ARE CORRECT — see the module
# docstring. county_of() accepts both, so this same function is byte-for-byte
# portable across every instance's copy of this file.
def county_of(anchor_key):
    """The county an anchor vouches for, from either key shape.

    "Marion (Williamson)" -> "Williamson"; "Bronx" -> "Bronx".
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
    ap.add_argument("--state-out", default=STATE_OUT_PATH)
    ap.add_argument("--check", action="store_true",
                    help="validate the shipped files instead of rebuilding")
    args = ap.parse_args()

    if args.check:
        with open(args.out) as f:
            shipped = json.load(f)
        # rings_of() flattens Polygon and MultiPolygon alike, so the anchor test
        # reads the file the same way whether or not the served area is one region.
        rings = rings_of(shipped["features"][0])
        problems = (check_anchor_registry() + validate(rings)
                    + check_envelopes(rings))

        with open(args.state_out) as f:
            shipped_state = json.load(f)
        state_rings = rings_of(shipped_state["features"][0])
        problems += validate_state(state_rings)
        # The served area is New York counties, so it cannot leave New York.
        # Checked on the SHIPPED pair rather than on fresh geometry: it is the
        # two files that have to agree, and they are simplified separately.
        problems += containment_problems(rings, state_rings)

        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        if problems:
            sys.exit(1)
        print("metro-outline: OK — %d ring(s), %d vertices, all %d inside / %d outside "
              "anchors correct" % (len(rings), sum(len(r) for r in rings),
                                   len(INSIDE), len(OUTSIDE)), file=sys.stderr)
        print("ny-state-outline: OK — %d ring(s), %d vertices, all %d New York "
              "anchors inside / %d out-of-state anchors outside"
              % (len(state_rings), sum(len(r) for r in state_rings),
                 len(INSIDE) + len(OUTSIDE), len(STATE_OUTSIDE)),
              file=sys.stderr)
        return

    rings = [simplify(r) for r in dissolve(fetch_counties())]
    # Same simplifier and the same tolerance as the counties — see the module
    # docstring: a served county fronting the state line must share that line
    # with the state ring, not drift apart from it.
    state_rings = [simplify(r) for r in rings_of(fetch_state())]

    problems = (check_anchor_registry()
                + validate(rings) + check_envelopes(rings) + validate_state(state_rings)
                + containment_problems(rings, state_rings))
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

    with open(args.state_out, "w") as f:
        json.dump(build_state_geojson(state_rings), f, separators=(",", ":"))
        f.write("\n")
    state_size = os.path.getsize(args.state_out)
    print("wrote %s: %d ring(s), %d vertices, %.1f KB"
          % (args.state_out, len(state_rings),
             sum(len(r) for r in state_rings), state_size / 1024.0),
          file=sys.stderr)


if __name__ == "__main__":
    main()
