#!/usr/bin/env python3
"""
Shared machinery for the Minnesota layers that are DISSOLVED out of one
fabric: the robots gate, the paged read of the Secretary of State's precinct
service, and the dissolve/point/simplify helpers.

Two layers are built this way today and the Secretary of State's own
attributes hold five more (mn/WATCH.md records the seven), so the dissolve
lives in one file rather than once per builder. It is machinery and not a
question: the builders decide what a district IS and this module only turns a
set of polygons into one.

WHY THE DISSOLVE IS EXACT RATHER THAN APPROXIMATE: every polygon handed to it
comes out of a single publisher's single fabric, so a border shared by two
neighbours is the same vertex sequence on both sides, and dropping every
segment walked twice leaves exactly the group's outline. The function RAISES
on an open chain rather than closing one, because a chain that will not close
means that assumption has stopped holding and the answer would be a polygon
nobody drew.

Imported by build_mn_judicial_districts.py and
build_mn_commissioner_districts.py. Both are in this instance's own tree;
scripts/validate_workflow_deps.py fails a reach into another instance's.
"""

import math
import sys

USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 120
PAGE_SIZE = 2000

PRECINCT_LAYER = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
                  "us_mn_state_sos/bdry_votingdistricts/FeatureServer/0")
PRECINCT_QUERY = PRECINCT_LAYER + "/query"

EXPECT_PRECINCTS = 4105
SIMPLIFY_TOLERANCE_M = 40.0


# --------------------------------------------------------------------------
# robots, once per host, with the client that fetches
# --------------------------------------------------------------------------

def require_robots(urls, fleet_scripts, user_agent=USER_AGENT, paced=False):
    """Read each host's robots.txt with the exact client that will crawl it,
    and refuse to go on if it says no. `paced` is the caller stating that it
    honours a stated Crawl-delay; a caller that does not pace itself is
    stopped by a newly stated delay rather than quietly ignoring it."""
    sys.path.insert(0, fleet_scripts)
    import requests  # noqa: PLC0415
    import robots_policy  # noqa: PLC0415
    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    gate = robots_policy.RobotsGate(session, user_agent)
    delays = {}
    for url in urls:
        host = url.split("/")[2]
        ok, why = gate.allows(url)
        print("robots %s: %s — %s" % (host, "allowed" if ok else "REFUSED", why),
              file=sys.stderr)
        if not ok:
            raise SystemExit("FATAL: robots.txt refuses this client for %s. Nothing "
                             "here works around a refusal." % url)
        delay = gate.crawl_delay(url)
        if delay:
            if not paced:
                raise SystemExit(
                    "FATAL: %s now states Crawl-delay %s. This caller makes its "
                    "requests back to back and does not pace itself, so it must "
                    "learn to before it runs again." % (host, delay))
            print("robots %s: Crawl-delay %s — honoured" % (host, delay),
                  file=sys.stderr)
            delays[host] = float(delay)
    return delays


# --------------------------------------------------------------------------
# the precinct fabric
# --------------------------------------------------------------------------

def fetch_precincts(out_fields, geometry=False, where="1=1",
                    expect=EXPECT_PRECINCTS, user_agent=USER_AGENT):
    """Page the whole precinct layer. The service's maxRecordCount is 2000, so
    a single query silently returns a truncated answer; `exceededTransferLimit`
    is not relied on, the page length is. Returns GeoJSON features when
    `geometry` is set and plain attribute dicts otherwise.

    `expect` is a count this caller requires, and None switches it off for a
    caller reading one county. A floor would be the wrong shape here: the
    fabric is a known size and a changed size means re-measure, not carry on."""
    import requests  # noqa: PLC0415
    rows, offset = [], 0
    while True:
        params = {
            "where": where,
            "outFields": ",".join(out_fields),
            "returnGeometry": "true" if geometry else "false",
            "orderByFields": "objectid",
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE_SIZE),
            "f": "geojson" if geometry else "json",
        }
        if geometry:
            params["outSR"] = "4326"
        resp = requests.get(PRECINCT_QUERY, headers={"User-Agent": user_agent},
                            timeout=REQUEST_TIMEOUT, params=params)
        resp.raise_for_status()
        body = resp.json() or {}
        if "error" in body:
            raise SystemExit("FATAL: the precinct service returned an error: %s"
                             % body["error"])
        page = list(body.get("features") or [])
        if not geometry:
            page = [row.get("attributes") or {} for row in page]
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    if expect is not None and len(rows) != expect:
        raise SystemExit("FATAL: read %d precincts, expected exactly %d. The precinct "
                         "fabric moved — re-measure before trusting it."
                         % (len(rows), expect))
    return rows


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def rings_of(feature):
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        return list(geom.get("coordinates") or [])
    if geom.get("type") == "MultiPolygon":
        return [ring for poly in (geom.get("coordinates") or []) for ring in poly]
    return []


def dissolve(features):
    """Drop every segment walked more than once (a border interior to the
    group) and chain the survivors into closed rings — the same algorithm
    build_metro_outline.py runs once for the whole state, run here once per
    district. See this module's docstring for why it is exact rather than
    approximate, and why an open chain raises."""
    counts, seg_pts = {}, {}
    for feature in features:
        for ring in rings_of(feature):
            for i in range(len(ring) - 1):
                a, b = tuple(ring[i][:2]), tuple(ring[i + 1][:2])
                if a == b:
                    continue
                key = (a, b) if a < b else (b, a)
                counts[key] = counts.get(key, 0) + 1
                seg_pts[key] = (a, b)

    adj, exterior = {}, 0
    for key, n in counts.items():
        if n != 1:
            continue
        exterior += 1
        a, b = seg_pts[key]
        adj.setdefault(a, []).append((key, b))
        adj.setdefault(b, []).append((key, a))

    used, rings, walked = set(), [], 0
    for seed, n in counts.items():
        if n != 1 or seed in used:
            continue
        start, cur = seg_pts[seed]
        used.add(seed)
        walked += 1
        ring = [list(start), list(cur)]
        while cur != start:
            nxt = None
            for key, pt in adj.get(cur, ()):
                if key not in used:
                    nxt = (key, pt)
                    break
            if nxt is None:
                raise SystemExit("FATAL: open chain while dissolving a district — the "
                                 "county file is no longer topologically consistent")
            used.add(nxt[0])
            walked += 1
            cur = nxt[1]
            ring.append(list(cur))
        rings.append(ring)
    if walked != exterior:
        raise SystemExit("FATAL: dissolve dropped exterior segments (%d walked of %d)"
                         % (walked, exterior))
    return rings


def point_in_ring(lng, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            if lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def point_in_geom(lng, lat, geom):
    polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
             else [geom["coordinates"]])
    for poly in polys:
        if point_in_ring(lng, lat, poly[0]) and not any(
                point_in_ring(lng, lat, hole) for hole in poly[1:]):
            return True
    return False


def ring_area(ring):
    total = 0.0
    for i in range(len(ring) - 1):
        total += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(total) / 2.0


def ring_interior_point(ring):
    """A point STRICTLY inside a ring, never one of its own vertices.

    group_rings needs to ask whether one ring lies inside another, and a
    vertex is the one place that question has no answer: point_in_ring on a
    boundary point returns whichever side the crossing arithmetic happens to
    land on. That is not hypothetical — Otter Tail County's commissioner
    district 5 has a detached piece whose ring touches district 2's own outer
    boundary at exactly one vertex, and testing ring[0] there answered
    "outside", so district 2 was written covering ground that belongs to
    district 5 and the two districts overlapped.

    So cast a horizontal ray at the mid-height of an edge, at a height no
    vertex shares, and take the midpoint of the first interior span. Edges are
    tried in turn because a height can collide with a vertex; a ring with no
    usable height is not a ring."""
    ys = set(round(p[1], 12) for p in ring)
    for i in range(len(ring) - 1):
        y = (ring[i][1] + ring[i + 1][1]) / 2.0
        if round(y, 12) in ys:
            continue
        xs = []
        for j in range(len(ring) - 1):
            x1, y1 = ring[j][0], ring[j][1]
            x2, y2 = ring[j + 1][0], ring[j + 1][1]
            if (y1 > y) != (y2 > y):
                xs.append(x1 + (x2 - x1) * (y - y1) / (y2 - y1))
        if len(xs) >= 2:
            xs.sort()
            return ((xs[0] + xs[1]) / 2.0, y)
    raise SystemExit("FATAL: a dissolved ring has no interior point — it is "
                     "degenerate rather than a polygon (%d vertices)" % len(ring))


def group_rings(rings):
    """Nest each ring at its own containment DEPTH rather than under the first
    enclosing ring found. Kept general rather than assumed: most of these
    districts are simply connected, and a builder that assumed so would write
    a hole as a second island the day one appeared — which Ramsey's
    commissioner districts 1 and 7 already do.

    Depth is counted exactly, from each ring's own interior point: a ring
    inside an even number of others is an outer ring, one inside an odd number
    is a hole in the smallest ring that contains it. An island inside a lake
    is therefore an outer ring again, which taking the first enclosing ring
    got wrong."""
    ordered = sorted(rings, key=ring_area, reverse=True)
    points = [ring_interior_point(ring) for ring in ordered]
    polys, owner = [], {}
    for i, ring in enumerate(ordered):
        lng, lat = points[i]
        containers = [j for j in range(i) if point_in_ring(lng, lat, ordered[j])]
        if len(containers) % 2 == 0:
            poly = [ring]
            polys.append(poly)
            owner[i] = poly
        else:
            owner[containers[-1]].append(ring)
            owner[i] = owner[containers[-1]]
    return polys


def simplify(ring, tolerance_m=SIMPLIFY_TOLERANCE_M):
    """Douglas-Peucker — the fleet's measured finding three times over, and
    right here for the same reason: county lines are survey-grid straight
    runs, and thresholding triangle area does not bound how far the drawn
    line strays from them."""
    if len(ring) < 4:
        return ring
    tol = tolerance_m / 111320.0
    scale = math.cos(math.radians(46.0))

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
        lo, hi = stack.pop()
        worst, idx = 0.0, None
        for i in range(lo + 1, hi):
            d = perp(ring[i], ring[lo], ring[hi])
            if d > worst:
                worst, idx = d, i
        if idx is not None and worst > tol:
            keep.add(idx)
            stack.append((lo, idx))
            stack.append((idx, hi))
    out = [ring[i] for i in sorted(keep)]
    if out[0] != out[-1]:
        out.append(out[0])
    return out if len(out) >= 4 else ring


def round_coords(value, places=6):
    if isinstance(value, list):
        return [round_coords(v, places) for v in value]
    return round(value, places)
