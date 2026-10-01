#!/usr/bin/env python3
"""
Build data/app/mn-judicial-districts.json — Minnesota's 10 judicial
districts, whole-county unions, no new boundary drawn.

Minn. Stat. 2.722 subd. 1 divides the state into ten judicial districts and
names the counties in each, in the statute's own text: "Effective July 1,
1959, the state is divided into ten judicial districts composed of the
following named counties". The same subdivision states each district's
authorized number of judges and where it maintains permanent chambers. So
the boundary needs no publisher at all — it is the county fabric this app
already ships, grouped by a list written into law — and the whole of this
builder is parsing that list, proving it, and dissolving.

THE COUNTY LIST IS PARSED AT BUILD TIME, NEVER TRANSCRIBED. A hand-copied
table of 87 county names is a 87-way opportunity for a typo that no gate
could see, and subd. 2 lets the supreme court alter the boundaries, so the
list is not frozen either. It is fetched from
www.revisor.mn.gov/statutes/cite/2.722 and gated four ways: ten districts,
87 counties, every county exactly once, and every name matching a BASENAME
in this instance's own shipped county file.

THE SECOND WITNESS IS SPATIAL AND COMES FROM A DIFFERENT OFFICE. The
Secretary of State's precinct service carries a `juddist` attribute on every
one of the 4,105 precincts, so each county's own precincts say which
judicial district the Elections Division puts that county in. This builder
reads that field for every precinct and requires three things: every
county's precincts agree with each other, every county's answer equals the
statute's, and all 87 counties are covered. That is 4,105 witnesses from the
Secretary of State against a list from the Revisor — two offices, no shared
copy. Iowa's equivalent builder leans on published district polygons for
this; Minnesota publishes none that this project has found, and a per-
precinct attribute is the stronger substitute, because it is per county
rather than per district.

THE THIRD GATE IS CONTAINMENT, and it is what proves the dissolve rather
than the list: every county's own proven-interior anchor point (the INSIDE
dict in build_metro_outline.py, already verified interior against that
county's own rings) must fall inside the district polygon the statute
assigns it to, and inside no other. A closed ring is not proof a dissolve
kept every county.

JUDGES ARE ELECTED HERE, WHICH IS WHY THIS LAYER EXISTS. Minnesota district
court judges stand in nonpartisan elections and run in the district they
serve, so a reader's judicial district is a district they vote in — unlike
Illinois, where a judge is elected from a subcircuit and then sits
circuit-wide. NO JUDGE IS NAMED BY THIS CHANGE, and the reason is a
measurement rather than a deferral. The statute authorizes 287 judgeships
across the ten districts, and the only publisher of the people in them that
this project has found, www.mncourts.gov, REFUSES EVERY CLIENT IT HAS.
Measured 2026-10-01 on /Find-Courts/FirstJudicialDistrict.aspx, all four
rungs of this repo's own ladder: the districtry token on the stdlib client
and on requests, and a pinned Chrome string with its client hints on both —
403 on all four. A browser-class client is therefore not the
missing ingredient, and the reason is in the response: Server `cloudflare`,
a `__cf_bm` cookie, a `CF-RAY` header and a body whose text is "Just a
moment...". THAT IS A CLOUDFLARE MANAGED CHALLENGE, which is an access
control, and nothing in this project solves or routes around one — the same
answer Christian County got in Illinois. The host's own robots.txt answers
403 as well, which RFC 9309 files as no published policy, so there is no
stated refusal to read either way; the challenge is what shuts the door.
The card names the district, states the authorized judgeship count from the
statute, says plainly that it names nobody, and links the court for a
reader's own browser, which clears the challenge as any person's browser
does. The gap record `mn-judicial-roster` carries the measurement, and
`EXPECTED_UNREACHABLE` in scripts/validate_card_links.py carries the host,
so the monthly link check reports a lift rather than a dead link.

WHAT THE STATUTE'S JUDGE COUNT IS, EXACTLY: an authorized number of
judgeships, not a count of people sitting today. Subd. 4 lets the supreme
court abolish or transfer a vacant position, so the authorized figure and
the occupied one can differ. The card says "authorized", never "there are".

Run:  python3 mn/scripts/build_mn_judicial_districts.py
"""

import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")

STATUTE_URL = "https://www.revisor.mn.gov/statutes/cite/2.722"
PRECINCT_QUERY = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
                  "us_mn_state_sos/bdry_votingdistricts/FeatureServer/0/query")
USER_AGENT = "districtry/1.0 (+https://districtry.com/mn/)"
REQUEST_TIMEOUT = 90
PAGE_SIZE = 2000

COUNTY_FILE = os.path.join(INSTANCE, "data", "app", "state-counties.json")
OUT_FILE = os.path.join(INSTANCE, "data", "app", "mn-judicial-districts.json")

EXPECT_DISTRICTS = 10
EXPECT_COUNTIES = 87
EXPECT_PRECINCTS = 4105
SIMPLIFY_TOLERANCE_M = 40.0   # see simplify(); the county file is already
                              # topology-simplified, so this only drops
                              # vertices the dissolve inherited twice over.


# --------------------------------------------------------------------------
# robots, once per host, with the client that fetches
# --------------------------------------------------------------------------

def require_robots(urls):
    sys.path.insert(0, FLEET_SCRIPTS)
    import requests  # noqa: PLC0415
    import robots_policy  # noqa: PLC0415
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    gate = robots_policy.RobotsGate(session, USER_AGENT)
    for url in urls:
        ok, why = gate.allows(url)
        print("robots %s: %s — %s" % (url.split("/")[2],
                                      "allowed" if ok else "REFUSED", why),
              file=sys.stderr)
        if not ok:
            raise SystemExit("FATAL: robots.txt refuses this client for %s. Nothing "
                             "here works around a refusal." % url)
        delay = gate.crawl_delay(url)
        if delay:
            raise SystemExit("FATAL: %s now states Crawl-delay %s. This builder makes "
                             "its requests back to back and does not pace itself, so "
                             "it must learn to before it runs again."
                             % (url.split("/")[2], delay))


# --------------------------------------------------------------------------
# the statute
# --------------------------------------------------------------------------

def fetch_statute():
    import requests  # noqa: PLC0415
    resp = requests.get(STATUTE_URL, headers={"User-Agent": USER_AGENT},
                        timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    text = re.sub(r"<[^>]+>", "\n", resp.text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return [line for line in lines if line]


def parse_statute(lines):
    """Pull the ten "N. <counties>; <k> judges; [and permanent chambers ...]"
    entries out of subd. 1.

    The lines are matched on their own shape rather than on a position in the
    page, because the page is a whole legislative site around the section —
    but the search is BOUNDED to subd. 1, so a county name appearing in a
    later subdivision's prose cannot be read as a district's membership.
    """
    try:
        start = next(i for i, line in enumerate(lines)
                     if line.startswith("Subdivision 1"))
        end = next(i for i, line in enumerate(lines[start:], start)
                   if line.startswith("Subd. 2"))
    except StopIteration:
        raise SystemExit("FATAL: could not find subdivision 1 of 2.722 on the page — "
                         "the statute's layout changed, or the section was renumbered")

    if not any("divided into ten judicial districts" in line
               for line in lines[start:end]):
        raise SystemExit("FATAL: subd. 1 no longer says the state is divided into ten "
                         "judicial districts. Read the section before changing this.")

    out = {}
    for line in lines[start:end]:
        match = re.match(r"^(\d{1,2})\.\s+(.*)$", line)
        if not match:
            continue
        number = int(match.group(1))
        if not 1 <= number <= EXPECT_DISTRICTS:
            continue
        body = match.group(2)
        parts = [p.strip() for p in body.split(";")]
        counties = parse_county_list(parts[0])
        judges = None
        chambers = []
        for part in parts[1:]:
            jm = re.match(r"^(?:and\s+)?(\d+)\s+judges?\b", part)
            if jm:
                judges = int(jm.group(1))
            if "chambers" in part:
                chambers = parse_chambers(part)
        if judges is None:
            raise SystemExit("FATAL: district %d states no judge count — the statute's "
                             "wording changed" % number)
        if number in out:
            raise SystemExit("FATAL: district %d appears twice in subd. 1" % number)
        out[number] = {"counties": counties, "judges": judges,
                       "chambers": chambers}
    if sorted(out) != list(range(1, EXPECT_DISTRICTS + 1)):
        raise SystemExit("FATAL: parsed districts %s, expected 1-%d"
                         % (sorted(out), EXPECT_DISTRICTS))
    return out


def parse_county_list(text):
    text = text.rstrip(".").strip()
    text = re.sub(r",?\s+and\s+", ", ", text)
    names = [n.strip() for n in text.split(",")]
    names = [n for n in names if n]
    if not names:
        raise SystemExit("FATAL: a district's county list parsed empty")
    return names


def parse_chambers(text):
    """"permanent chambers shall be maintained in A, B, and C" -> [A, B, C].

    Anything after a trailing "and one other shall be maintained at the place
    designated by ..." is dropped: it names no place, so there is nothing for
    a card to print.
    """
    match = re.search(r"maintained in (.+)$", text)
    if not match:
        return []
    body = match.group(1)
    body = re.split(r"\band (?:one|other)\b", body)[0]
    body = body.rstrip(".").strip()
    body = re.sub(r",?\s+and\s+", ", ", body)
    return [p.strip() for p in body.split(",") if p.strip()]


# --------------------------------------------------------------------------
# the Secretary of State's own answer, per precinct
# --------------------------------------------------------------------------

def fetch_precinct_districts():
    import requests  # noqa: PLC0415
    rows, offset = [], 0
    while True:
        resp = requests.get(PRECINCT_QUERY, headers={"User-Agent": USER_AGENT},
                            timeout=REQUEST_TIMEOUT, params={
                                "where": "1=1",
                                "outFields": "vtdid,countyname,juddist",
                                "returnGeometry": "false",
                                "orderByFields": "objectid",
                                "resultOffset": str(offset),
                                "resultRecordCount": str(PAGE_SIZE),
                                "f": "json",
                            })
        resp.raise_for_status()
        body = resp.json() or {}
        if "error" in body:
            raise SystemExit("FATAL: the precinct service returned an error: %s"
                             % body["error"])
        page = [row.get("attributes") or {} for row in (body.get("features") or [])]
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    if len(rows) != EXPECT_PRECINCTS:
        raise SystemExit("FATAL: read %d precincts, expected exactly %d. The precinct "
                         "fabric moved — re-measure before trusting this witness."
                         % (len(rows), EXPECT_PRECINCTS))
    by_county = {}
    for row in rows:
        county = (row.get("countyname") or "").strip()
        district = (row.get("juddist") or "").strip()
        if not county or not district:
            raise SystemExit("FATAL: a precinct carries no county or no judicial "
                             "district: %r" % row)
        by_county.setdefault(county, set()).add(int(district))
    split = {c: sorted(d) for c, d in by_county.items() if len(d) > 1}
    if split:
        raise SystemExit("FATAL: these counties' own precincts disagree about their "
                         "judicial district, so the district is no longer a union of "
                         "whole counties: %s" % split)
    return {county: next(iter(d)) for county, d in by_county.items()}


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
    """Drop every segment walked more than once (an interior county line) and
    chain the survivors into closed rings — the same algorithm
    build_metro_outline.py runs once for the whole state, run here once per
    district. It is exact rather than approximate because every county in the
    group came out of one topology-aware simplification, so a shared border is
    the same vertex sequence on both sides."""
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


def group_rings(rings):
    """Nest each hole under the outer ring that encloses it. Kept general
    rather than assumed: a judicial district is a group of adjacent counties
    and in practice simply connected, and a builder that assumed so would
    write a hole as a second island the day one appeared."""
    ordered = sorted(rings, key=ring_area, reverse=True)
    polys = []
    for ring in ordered:
        lng, lat = ring[0][0], ring[0][1]
        parent = None
        for poly in polys:
            if point_in_ring(lng, lat, poly[0]):
                parent = poly
        if parent is None:
            polys.append([ring])
        else:
            parent.append(ring)
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


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

ORDINALS = {1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth",
            6: "Sixth", 7: "Seventh", 8: "Eighth", 9: "Ninth", 10: "Tenth"}


def main():
    require_robots([STATUTE_URL, PRECINCT_QUERY])

    statute = parse_statute(fetch_statute())

    with open(COUNTY_FILE, encoding="utf-8") as handle:
        counties = json.load(handle)["features"]
    if len(counties) != EXPECT_COUNTIES:
        raise SystemExit("FATAL: the shipped county file holds %d features, expected %d"
                         % (len(counties), EXPECT_COUNTIES))
    by_name = {}
    for feature in counties:
        name = (feature["properties"].get("BASENAME") or "").strip()
        if not name:
            raise SystemExit("FATAL: a county feature carries no BASENAME")
        by_name[name] = feature

    # Gate 1 — the statute's list is a partition of this state's counties.
    assigned, seen = {}, []
    for number in sorted(statute):
        for name in statute[number]["counties"]:
            if name not in by_name:
                raise SystemExit("FATAL: the statute names a county %r that this "
                                 "instance's county file does not carry. Either the "
                                 "statute was amended or the parse is wrong — read "
                                 "2.722 before changing anything here." % name)
            if name in assigned:
                raise SystemExit("FATAL: %s is named in districts %d and %d"
                                 % (name, assigned[name], number))
            assigned[name] = number
            seen.append(name)
    if len(seen) != EXPECT_COUNTIES or set(seen) != set(by_name):
        missing = sorted(set(by_name) - set(seen))
        raise SystemExit("FATAL: the statute's lists cover %d of %d counties; missing "
                         "%s" % (len(seen), EXPECT_COUNTIES, missing))
    print("statute: %d districts covering all %d counties, %d authorized judgeships"
          % (len(statute), len(seen), sum(d["judges"] for d in statute.values())),
          file=sys.stderr)

    # Gate 2 — the Secretary of State's own per-precinct answer agrees.
    sos = fetch_precinct_districts()
    if set(sos) != set(by_name):
        raise SystemExit("FATAL: the precinct service covers %d counties and the county "
                         "file %d; the two no longer name the same set (%s)"
                         % (len(sos), len(by_name),
                            sorted(set(sos) ^ set(by_name))[:6]))
    disagree = {c: (assigned[c], sos[c]) for c in sos if sos[c] != assigned[c]}
    if disagree:
        raise SystemExit("FATAL: the statute and the Secretary of State disagree about "
                         "these counties (statute, SoS): %s. One of the two publishers "
                         "has moved; neither is overridden here." % disagree)
    print("witness: all %d counties agree between Minn. Stat. 2.722 and the Secretary "
          "of State's %d precincts" % (len(sos), EXPECT_PRECINCTS), file=sys.stderr)

    # Build.
    features, vertices = [], 0
    geoms = {}
    for number in sorted(statute):
        names = statute[number]["counties"]
        rings = dissolve([by_name[n] for n in names])
        polys = group_rings(rings)
        polys = [[simplify(ring) for ring in poly] for poly in polys]
        if len(polys) == 1:
            geom = {"type": "Polygon", "coordinates": round_coords(polys[0])}
        else:
            geom = {"type": "MultiPolygon", "coordinates": round_coords(polys)}
        geoms[number] = geom
        vertices += sum(len(ring) for poly in polys for ring in poly)
        features.append({
            "type": "Feature",
            "properties": {
                "district": number,
                "name": "%s Judicial District" % ORDINALS[number],
                "counties": sorted(names),
                "countyCount": len(names),
                "authorizedJudges": statute[number]["judges"],
                "chambers": statute[number]["chambers"],
            },
            "geometry": geom,
        })

    # Gate 3 — containment. Every county's proven-interior anchor must land in
    # its own district and in no other.
    sys.path.insert(0, HERE)
    import build_metro_outline  # noqa: PLC0415
    anchors = build_metro_outline.INSIDE
    if set(anchors) != set(by_name):
        raise SystemExit("FATAL: the anchor dict covers %d counties, the county file %d"
                         % (len(anchors), len(by_name)))
    for name, (lat, lng) in anchors.items():
        hits = [n for n in sorted(geoms) if point_in_geom(lng, lat, geoms[n])]
        if hits != [assigned[name]]:
            raise SystemExit("FATAL: %s County's own interior anchor lands in districts "
                             "%s, expected only %d — the dissolve lost or merged a "
                             "county" % (name, hits, assigned[name]))
    print("containment: all %d county anchors land in exactly their own district"
          % len(anchors), file=sys.stderr)

    out = {"type": "FeatureCollection", "features": features}
    with open(OUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(out, handle, separators=(",", ":"))
        handle.write("\n")
    size = os.path.getsize(OUT_FILE)
    print("mn-judicial-districts -> data/app/%s: %d districts, %d vertices, %d bytes "
          "(dp tolerance %.0f m, 6dp)"
          % (os.path.basename(OUT_FILE), len(features), vertices, size,
             SIMPLIFY_TOLERANCE_M), file=sys.stderr)


if __name__ == "__main__":
    main()
