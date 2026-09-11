#!/usr/bin/env python3
"""
Build data/app/municipal-ward-coverage.json — the cheap, same-origin coverage
test for the suburban entries of the consolidated `ward` layer.

Why a prebuilt file instead of testing the ward geometry itself: the engine
evaluates every layer's `coverage(point)` on EVERY point selection, whether or
not the layer is toggled on (updateAllLayerRelevance). Deriving suburban ward
coverage from the live ward services would therefore pull four ArcGIS payloads
on the first click anywhere in Illinois — including for the Chicago users who
are most of the traffic. This file is one small cache-first fetch instead, the
same shape as the `*-county-outline.json` files the county-dispatched layers
use for exactly this reason.

Each feature is one ward-electing municipality's TIGER place polygon, tagged
with the dispatch entry that serves its wards, so an entry's coverage test is
"containment in my own features" and the dispatcher's OR still short-circuits
in table order.

Municipalities are discovered from the live ward services (so a source that
gains or drops a municipality is followed rather than missed), then resolved
to a Census place GEOID through the committed place-by-county reference and
fetched from TIGERweb — the same boundary the `municipality` layer draws, so
coverage can never disagree with the municipality the card names.

Operator step, rarely re-run (ward maps are redrawn ~once a decade):
    python3 scripts/build_municipal_ward_coverage.py
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

from arcgis_error import raise_for_arcgis_error
from scraper_common import UA_CHROME_WIN_124  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "municipal-ward-coverage.json")
PLACES_FILE = os.path.join(REPO_ROOT, "il", "data", "source", "st17_il_place_by_county2020.txt")

TIGER_PLACES = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/4/query")
COOK_WARDS = ("https://gis.cookcountyil.gov/traditional/rest/services/politicalBoundary/"
              "MapServer/22/query")

USER_AGENT = UA_CHROME_WIN_124
TIMEOUT = 120

# Entries whose municipality list is fixed by the service itself (one service,
# known municipalities). Cook's is discovered live because its layer carries
# 20+ municipalities and gains more as suburbs redistrict.
STATIC_ENTRY_MUNICIPALITIES = {
    "evanston": ["Evanston"],
    "will": ["Lockport", "Wilmington", "Crest Hill", "Joliet"],
    "aurora": ["Aurora"],
    # Rockford's 14 aldermanic wards ride WinGIS's ElectedOfficials service —
    # the same regional-consortium GIS the Winnebago county-board entry uses.
    "rockford": ["Rockford"],
    # Moline (7) and Silvis (4) publish their own ward layers on Rock Island
    # County's hosted org; East Moline's 7 (with per-seat contact) live on the
    # CITY's own org and joined the same dispatch entry 2026-08-02. Rock Island
    # city joined 2026-08-03, once its clerk confirmed the wards were kept.
    "rock-island": ["Moline", "Silvis", "East Moline", "Rock Island"],
    # Whiteside's six ward-electing municipalities. The layer is a 2016 edit,
    # confirmed current by the County Clerk on 2026-08-03 ("The wards were not
    # redrawn at the time of the census in 2020").
    "whiteside-cities": ["Sterling", "Rock Falls", "Morrison", "Fulton",
                         "Prophetstown", "Erie"],
    # The CITY of Peoria's five council districts, on the city's own org. Its
    # other five council members are elected at large and belong to no district.
    "peoria-city": ["Peoria"],
    # DeKalb County's own org publishes one ward layer per ward-electing
    # municipality: DeKalb (7), Sycamore (4), Genoa (4), Sandwich (4), all
    # edited 2023-11.
    "dekalb": ["DeKalb", "Sycamore", "Genoa", "Sandwich"],
    # Mendota is the only one of LaSalle County's four ward-electing cities that
    # publishes ward geometry anywhere; La Salle, Peru and Earlville are a
    # recorded gap. The layer is the city's own, edited 2022-12.
    # Galesburg's seven aldermanic wards, on the CITY's own AGOL org, added
    # 2026-08-22 — the day after Knox County itself joined the coverage ring on
    # its board districts. The wards were never the blocker: the city has
    # published them, current and with a MEMBER column, the whole time. What
    # blocked them was that their county was not covered, so this entry is the
    # second half of the same join rather than a new source.
    "galesburg": ["Galesburg"],
    "mendota": ["Mendota"],
    # The pass-6 ward tranche (2026-08-02) — thirteen sources across
    # twenty-two cities, every geometry vintage and officeholder posture
    # verified live before shipping (see index.html's loader block).
    "berwyn": ["Berwyn"],
    "lake-cities": ["Waukegan", "North Chicago"],
    "belvidere": ["Belvidere"],
    "kane-cities": ["St. Charles", "Geneva", "Batavia"],
    "dupage-cities": ["West Chicago"],
    "mchenry-city": ["McHenry"],
    # Madison County's six ward-electing cities on ONE county layer
    # (MadCo_Wards, 31 polygons). Five join the roster ward-for-ward; the CITY
    # OF MADISON's four wards name nobody, because the regional directory lists
    # its eight council members with no ward against any of them, and it is
    # listed here anyway so its wards still DRAW — a ward a resident lives in is
    # a fact whether or not its holder is published.
    "madison-cities": ["Alton", "Edwardsville", "Granite City", "Madison",
                       "Troy", "Venice"],
    "kendall-cities": ["Yorkville", "Plano"],
    "pontiac": ["Pontiac"],
    "mclean-cities": ["Bloomington", "Le Roy", "Lexington"],
    "lincoln": ["Lincoln"],
    "springfield": ["Springfield"],
    "freeport": ["Freeport"],
    "st-clair-cities": ["Belleville", "O'Fallon"],
    # Elmwood alone of the three cities on Peoria County's own Wards layer
    # (2026-09-05). Chillicothe and West Peoria are on that same service and are
    # deliberately NOT here: measured against their own Census place polygons
    # they leave 3.3% and 8.0% of themselves in no ward, against Elmwood's 0.4%
    # and the 0.1-0.5% the shipped layers manage. A held city is held in this
    # table as much as in index.html — an entry here with no dispatch entry
    # would claim coverage the layer cannot answer.
    "elmwood": ["Elmwood"],
}
# Chicago's wards are the city's own Socrata layer with its own coverage test
# (chicagoCoverage); it is never part of this file.
EXCLUDE = {"CHICAGO"}

# Deliberate under-tolerance against what the twenty-one entries resolve to at
# build time: 21 suburban Cook + Evanston + 4 Will + Aurora + Rockford + 3 Rock
# Island cities + 4 DeKalb + Mendota + the pass-6 tranche's 22, less overlap.
MIN_MUNICIPALITIES = 50


# Ramer-Douglas-Peucker tolerance in degrees (~0.0004 deg ≈ 45 m at this
# latitude). This file decides whether the ward TOGGLE APPLIES at a point, not
# what is drawn, so a boundary generalized to tens of metres is ample — and it
# is what keeps a file fetched on the first click off Illinois' largest
# payload list. The unsimplified TIGER polygons are 671 KB; the county-outline
# coverage files this mirrors are 35-64 KB. Implemented here rather than via
# mapshaper so the build needs no toolchain (cf. build_embedded_boundaries.py,
# which does shell out to mapshaper for the boundaries it SHIPS as geometry).
SIMPLIFY_TOLERANCE = 0.0004


def _rdp(points, tolerance):
    if len(points) < 3:
        return points[:]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        norm_sq = dx * dx + dy * dy
        worst, worst_i = -1.0, None
        for i in range(first + 1, last):
            px, py = points[i]
            if norm_sq == 0:
                dist_sq = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / norm_sq
                t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                cx, cy = ax + t * dx, ay + t * dy
                dist_sq = (px - cx) ** 2 + (py - cy) ** 2
            if dist_sq > worst:
                worst, worst_i = dist_sq, i
        if worst_i is not None and worst > tolerance * tolerance:
            keep[worst_i] = True
            stack.append((first, worst_i))
            stack.append((worst_i, last))
    return [p for p, k in zip(points, keep) if k]


def simplify_ring(ring, tolerance):
    """Simplify a closed ring, keeping it closed and a valid polygon (>=4 pts)."""
    if len(ring) < 5:
        return ring
    closed = ring[0] == ring[-1]
    pts = [tuple(p) for p in (ring[:-1] if closed else ring)]
    out = _rdp(pts + [pts[0]], tolerance)
    if out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 4:
        return ring
    return [list(p) for p in out]


def simplify_geometry(geometry, tolerance):
    kind = (geometry or {}).get("type")
    coords = (geometry or {}).get("coordinates")
    if kind == "Polygon":
        rings = [simplify_ring(r, tolerance) for r in coords]
        return {"type": "Polygon", "coordinates": rings}
    if kind == "MultiPolygon":
        polys = [[simplify_ring(r, tolerance) for r in poly] for poly in coords]
        return {"type": "MultiPolygon", "coordinates": polys}
    return geometry


def get_json(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        # ArcGIS reports failures with HTTP 200 and an `error` member, which
        # would read here as a layer with no features and trip the "source
        # changed" guards below — naming the wrong cause for what is often a
        # rate limit that clears on its own.
        return raise_for_arcgis_error(json.load(resp), url)


def norm(name):
    """Normalize a ward service's municipality name ("Calumet City").

    These arrive bare, so nothing is stripped except an optional "City of"
    style prefix. Stripping a trailing type word here would reduce "Calumet
    City" to "Calumet" and miss the join — the type suffix belongs to the
    Census side of the comparison only (see norm_census).
    """
    text = re.sub(r"^(village|city|town)\s+of\s+", "", (name or "").strip(), flags=re.I)
    return re.sub(r"[^A-Z]", "", text.upper())


def norm_census(placename):
    """Normalize a Census PLACENAME ("Calumet City city", "Oak Lawn village").

    Exactly one trailing type token is removed, so "Calumet City city" becomes
    "Calumet City" rather than "Calumet".
    """
    text = re.sub(r"\s+(village|city|town|CDP)$", "", (placename or "").strip(), flags=re.I)
    return re.sub(r"[^A-Z]", "", text.upper())


# Which county each entry's municipalities sit in, so a name that exists twice
# in Illinois resolves to the right one. Aurora spans four counties; Kane holds
# its Census place record.
# Rockford straddles the Winnebago/Ogle line, so it appears under both counties
# in the place-by-county reference; Winnebago is where the city sits.
# Points that must land inside a named entry's coverage, checked on the polygons
# this run is about to write. The file is a COVERAGE TEST — its whole job is to
# answer "is this point in an entry's ward cities" before the layer fetches any
# ward geometry — so a wrong or missing outline shows up as a card that never
# appears, which no other gate here would notice.
#
# They exist because Madison's entry was verified by an ad-hoc script that lived
# only in a PR body ("both probe points fall inside"). A check nobody can re-run
# is a claim, not a test. Each point is a real ward centroid taken from the
# county's own ward layer, so it also pins the municipality NAME the roster join
# depends on.
COVERAGE_PROBES = [
    (42.25670, -88.83936, "belvidere", "Belvidere"),        # Belvidere City Hall
    (38.90913, -90.19487, "madison-cities", "Alton"),       # Alton ward 1
    (38.69008, -90.12943, "madison-cities", "Granite City"),  # Granite City ward 1
    (38.68852, -90.14947, "madison-cities", "Madison"),     # the four that name nobody
]

ENTRY_COUNTY_FIPS = {"cook-suburban": "031", "evanston": "031",
                     "will": "197", "aurora": "089", "rockford": "201",
                     "berwyn": "031", "lake-cities": "097", "belvidere": "007",
                     "kane-cities": "089", "dupage-cities": "043",
                     "mchenry-city": "111", "kendall-cities": "093",
                     "madison-cities": "119",
                     "pontiac": "105", "mclean-cities": "113", "lincoln": "107",
                     "springfield": "167", "freeport": "177",
                     "st-clair-cities": "163", "rock-island": "161",
                     "whiteside-cities": "195",
                     "galesburg": "095",
                     "peoria-city": "143"}


def load_place_geoids():
    """-> ({county_fips: {name: geoid}}, {name: set(geoid)}) for IL places.

    Both indexes are needed because Illinois has TWO Wilmingtons and two
    Windsors. A first-wins lookup silently picked Greene County's Wilmington
    village for the Will County entry — the coverage polygon landed 180 miles
    downstate, so the ward layer hid in the real Wilmington and switched itself
    on in a village that has no ward services. County-qualified lookup first,
    statewide only when it is unambiguous, and a hard failure otherwise.
    """
    if not os.path.exists(PLACES_FILE):
        print("FATAL: Census place reference missing at %s" % PLACES_FILE, file=sys.stderr)
        sys.exit(1)
    by_county = {}
    statewide = {}
    with open(PLACES_FILE, encoding="utf-8-sig") as f:
        rows = [line.rstrip("\n").split("|") for line in f if line.strip()]
    header = rows[0]
    for row in rows[1:]:
        if len(row) != len(header):
            continue
        rec = dict(zip(header, row))
        if rec.get("TYPE") != "INCORPORATED PLACE":
            continue
        key = norm_census(rec["PLACENAME"])
        geoid = "17" + rec["PLACEFP"]
        by_county.setdefault(rec["COUNTYFP"], {})[key] = geoid
        statewide.setdefault(key, set()).add(geoid)
    return by_county, statewide


def resolve_place_geoid(name, entry, by_county, statewide):
    key = norm(name)
    fips = ENTRY_COUNTY_FIPS.get(entry)
    if fips and key in by_county.get(fips, {}):
        return by_county[fips][key]
    matches = statewide.get(key) or set()
    if len(matches) == 1:
        return next(iter(matches))
    if not matches:
        return None
    print("FATAL: '%s' (%s entry) matches %d Illinois places (%s) and the entry's "
          "county does not disambiguate it — refusing to guess"
          % (name, entry, len(matches), ", ".join(sorted(matches))), file=sys.stderr)
    sys.exit(1)


def discover_cook_municipalities():
    payload = get_json(COOK_WARDS, {
        "where": "1=1", "outFields": "MUNICIPALITY",
        "returnGeometry": "false", "returnDistinctValues": "true", "f": "json",
    })
    names = set()
    for feature in payload.get("features", []):
        name = (feature.get("attributes", {}).get("MUNICIPALITY") or "").strip()
        if name and norm(name) not in EXCLUDE:
            names.add(name)
    if not names:
        print("FATAL: Cook ward layer returned no municipalities — source changed",
              file=sys.stderr)
        sys.exit(1)
    return sorted(names)


def point_in_feature(lng, lat, geom):
    """Even-odd, matching the app's own pointInGeometry over a MultiPolygon."""
    def ring_hit(ring):
        hit = False
        for i in range(len(ring) - 1):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[i + 1][0], ring[i + 1][1]
            if (y1 > lat) != (y2 > lat):
                if lng < (x2 - x1) * (lat - y1) / ((y2 - y1) or 1e-12) + x1:
                    hit = not hit
        return hit

    def in_polygon(rings):
        inside = False
        for ring in rings:
            if ring_hit(ring):
                inside = not inside
        return inside

    if not geom:
        return False
    if geom["type"] == "Polygon":
        return in_polygon(geom["coordinates"])
    return any(in_polygon(poly) for poly in geom["coordinates"])


def main():
    by_county, statewide = load_place_geoids()

    entry_names = dict(STATIC_ENTRY_MUNICIPALITIES)
    entry_names["cook-suburban"] = discover_cook_municipalities()

    # One feature per municipality; if two entries both claim one, the first in
    # this order owns its coverage (matching the dispatch table's order).
    # Dedupe on the resolved GEOID, never the name: two Illinois municipalities
    # can share a name, and a name key would drop the second as a "duplicate"
    # of an entirely different place.
    wanted = []
    seen = set()
    # Order matches index.html's dispatch table. Derived from the tables above
    # rather than hardcoded — the previous literal tuple silently dropped a newly
    # added entry (rockford) with no error: the municipality simply never
    # appeared in the file and its layer never showed.
    ENTRY_ORDER = ["cook-suburban", "evanston", "will", "aurora"]
    order = ENTRY_ORDER + [e for e in STATIC_ENTRY_MUNICIPALITIES if e not in ENTRY_ORDER]
    missing = [e for e in entry_names if e not in order]
    if missing:
        print("FATAL: entry/entries %s have municipalities but no place in the "
              "dispatch order" % ", ".join(sorted(missing)), file=sys.stderr)
        sys.exit(1)
    for entry in order:
        for name in entry_names.get(entry, []):
            geoid = resolve_place_geoid(name, entry, by_county, statewide)
            if not geoid:
                print("FATAL: no Census place GEOID for '%s' (%s entry)" % (name, entry),
                      file=sys.stderr)
                sys.exit(1)
            if geoid in seen:
                continue
            seen.add(geoid)
            wanted.append({"entry": entry, "name": name, "geoid": geoid})

    if len(wanted) < MIN_MUNICIPALITIES:
        print("FATAL: resolved %d ward-electing municipalities, floor is %d"
              % (len(wanted), MIN_MUNICIPALITIES), file=sys.stderr)
        sys.exit(1)

    by_geoid = {w["geoid"]: w for w in wanted}
    geoid_list = ",".join("'%s'" % g for g in sorted(by_geoid))
    # Precision 4 (~11 m) is ample for a containment test and keeps the file
    # small — this decides visibility, not what is drawn.
    payload = get_json(TIGER_PLACES, {
        "where": "GEOID IN (%s)" % geoid_list,
        "outFields": "GEOID,NAME,BASENAME",
        "outSR": "4326", "f": "geojson", "geometryPrecision": "5",
    })
    features = payload.get("features") or []
    if len(features) < MIN_MUNICIPALITIES:
        print("FATAL: TIGERweb returned %d of %d place polygons"
              % (len(features), len(by_geoid)), file=sys.stderr)
        sys.exit(1)

    out = []
    for feature in features:
        props = feature.get("properties") or {}
        geoid = str(props.get("GEOID") or props.get("geoid") or "")
        meta = by_geoid.get(geoid)
        if not meta:
            continue
        out.append({
            "type": "Feature",
            "geometry": simplify_geometry(feature.get("geometry"), SIMPLIFY_TOLERANCE),
            "properties": {
                "geoid": geoid,
                "name": props.get("BASENAME") or props.get("NAME"),
                "entry": meta["entry"],
            },
        })

    if len(out) < MIN_MUNICIPALITIES:
        print("FATAL: matched %d place polygons to entries, floor is %d"
              % (len(out), MIN_MUNICIPALITIES), file=sys.stderr)
        sys.exit(1)

    out.sort(key=lambda f: f["properties"]["geoid"])

    # Read the file we are about to replace, so the run can report any outline
    # it changes that nobody asked it to change (see the NOTE below).
    previous = {}
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as fh:
                for feature in (json.load(fh).get("features") or []):
                    props = feature.get("properties") or {}
                    previous[(props.get("entry"), props.get("geoid"))] = \
                        json.dumps(feature.get("geometry"), sort_keys=True)
        except (OSError, ValueError):
            previous = {}      # unreadable: report nothing rather than guess
    redrawn = set()
    for feature in out:
        props = feature["properties"]
        was = previous.get((props["entry"], props["geoid"]))
        if was is not None and was != json.dumps(feature["geometry"], sort_keys=True):
            redrawn.add(props["name"])

    problems = []
    for lat, lng, entry, name in COVERAGE_PROBES:
        hit = None
        for feature in out:
            props = feature["properties"]
            if props["entry"] != entry:
                continue
            if point_in_feature(lng, lat, feature["geometry"]):
                hit = props["name"]
                break
        if hit != name:
            problems.append("%.5f,%.5f should be %s in entry %s; got %s"
                            % (lat, lng, name, entry, hit or "no coverage"))
    if problems:
        for line in problems:
            print("  FAIL: %s" % line, file=sys.stderr)
        print("FATAL: refusing to write a coverage file that misplaces its probes "
              "— the file on disk is unchanged", file=sys.stderr)
        sys.exit(1)

    with open(OUT_PATH, "w") as f:
        json.dump({"type": "FeatureCollection", "features": out}, f,
                  ensure_ascii=False, separators=(",", ":"))
        f.write("\n")

    if redrawn:
        # NOT a warning to silence. TIGER_PLACES is UNPINNED, so a rebuild run
        # for one reason (adding an entry) silently adopts whatever vintage the
        # Census is serving that day for EVERY municipality already in the file.
        # That happened on 2026-09-04: adding Madison's six re-drew 22 unrelated
        # outlines — Aurora, Belvidere, three in Cook, three in DeKalb, three in
        # Kane, three in Will among them — and the PR that did it described only
        # the six. Harmless in itself: these polygons are a coverage TEST rather
        # than a drawn boundary, and the file is cache-first, so a redraw reaches
        # a returning visitor only behind a CACHE_NAME bump. But an undisclosed
        # change is how a harmful one hides, and a reviewer should not be the
        # first to notice. Printing it puts the fact in the run's own output.
        print("NOTE: %d municipality outline(s) already in this file were REDRAWN "
              "by this run (%s) — TIGERweb's place vintage moved under an unpinned "
              "query. Say so in the PR, and bump CACHE_NAME: this file is "
              "cache-first."
              % (len(redrawn), ", ".join(sorted(redrawn))), file=sys.stderr)

    counts = {}
    for feature in out:
        counts[feature["properties"]["entry"]] = counts.get(feature["properties"]["entry"], 0) + 1
    print("wrote %s: %d municipalities (%s), %.0f KB"
          % (OUT_PATH, len(out),
             ", ".join("%s %d" % kv for kv in sorted(counts.items())),
             os.path.getsize(OUT_PATH) / 1024.0), file=sys.stderr)


if __name__ == "__main__":
    main()
