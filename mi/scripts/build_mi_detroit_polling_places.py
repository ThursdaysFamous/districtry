#!/usr/bin/env python3
"""
Build mi/data/app/mi-detroit-polling-places.json: each Detroit precinct's
Election Day polling place, read from the City of Detroit Department of
Elections' own precinct layer, with a map position for the building.

THE SOURCE. "Detroit Election Precincts (Current)" (ArcGIS Online item
ef621ded941a402fa436185541316994, published by the city's open-data
integration account and described as "Data provided by the City of Detroit
Department of Elections"). Each of its 402 precincts carries the state's own
precinct code (precinct_id, e.g. WP-163-22000-04001), the precinct number, and
the polling place's name, street address, cross street and ZIP code. Measured
2026-10-24: 402 precincts, 156 distinct buildings, no precinct without an
address, data last edited 2026-10-07 and the layer republished 2026-10-23.

WHY NOT THE STATE. Michigan has no statewide polling-place file this project
can read: the Secretary of State's voter information site, the only statewide
lookup, answers this client with a Cloudflare managed challenge, which is an
access control and is never worked around, and data.michigan.gov's robots.txt
disallows every path to every crawler. The state's ArcGIS Online org, which
publishes the precinct map this app draws, has no polling layer. Measured
2026-10-24. So a city publishing its own list is the source, one city at a
time, and Detroit's is the one checked so far.

THE JOIN IS AGAINST THE PRECINCT MAP THE APP DRAWS, by the state's own key.
The state's 2026 Voting Precincts layer is read every run for Detroit's
PRECINCTID and Precinct_Long_Name, and the build fails unless the city's list
and the state's map hold exactly the same 402 precinct codes. The file is keyed
by Precinct_Long_Name, which is the `name` the app's precinct card already
reads off the shipped boundary, and the build also fails unless the shipped
mi-precincts.json holds exactly those 402 names for Detroit. A SECOND TRIPWIRE
CHECKS THE GROUND, not only the codes: a point inside each shipped precinct
must fall inside the city's polygon carrying the same code, so a city layer
whose numbers were moved to other ground cannot pass on matching labels.

THE PIN. Each distinct address is placed with the U.S. Census Bureau's batch
geocoder (geocoding.geo.census.gov, no robots.txt), which estimates a house
number's position along its street's address range. A position is kept only
when the Census matched the same house number on a street of the same name,
and when it lies within PRECINCT_SLACK_M of a precinct the building serves; any
other address ships with no position and its card shows the address as text
with no pin. A building can sit outside the precincts it serves (Garvey Academy
serves precincts 2 and 4), which is why there is slack at all.

WHAT THE CARD IS TOLD: the list's own date, so a reader can see how current the
answer is, and the state's voter information site as the final word. The app
stops showing the polling place after ELECTION_DATE, the next election in
Detroit, because a precinct's polling place belongs to one election and the day
after it the list says nothing true about the next one.

WHAT THIS CANNOT SEE: a building the city moves without updating its layer, and
an address the geocoder places on the wrong block of the right street (the card
prints the city's address either way).

Usage:
    python3 mi/scripts/build_mi_detroit_polling_places.py [--out DIR]
"""

import argparse
import datetime
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mi_ward_common as wc  # noqa: E402

REPO_ROOT = wc.REPO_ROOT
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
from scraper_common import require_robots_once  # noqa: E402

USER_AGENT = wc.USER_AGENT
OUT_NAME = "mi-detroit-polling-places.json"

ITEM_ID = "ef621ded941a402fa436185541316994"
ITEM_PAGE = "https://www.arcgis.com/home/item.html?id=" + ITEM_ID
CITY_LAYER = ("https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/"
              "Election_Precincts/FeatureServer/0")
STATE_PRECINCTS = wc.STATE_PRECINCTS
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
LOOKUP_URL = "https://mvic.sos.state.mi.us/Voter/Index"

DETROIT_GEOID = "2616322000"
EXPECT_PRECINCTS = 402        # the city's layer and the state's 2026 map, both measured 2026-10-24
ELECTION = "General Election"
ELECTION_DATE = "2026-11-03"  # the next election in Detroit; the card hides the row after it
PRECINCT_SLACK_M = 1200       # a polling place can sit outside the precincts it serves
MIN_PLACED_FRACTION = 0.90


def fail(msg):
    print("build-mi-detroit-polling-places: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def robots():
    for url in (CITY_LAYER, STATE_PRECINCTS, GEOCODER_URL):
        print("  robots: %s -> %s" % (urllib.parse.urlsplit(url).hostname,
                                      require_robots_once(url, USER_AGENT,
                                                          label="build-mi-detroit-polling-places")))


def city_list():
    meta = wc.curl_json(CITY_LAYER + "?f=json")
    edited = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    if not edited:
        fail("the city's layer no longer says when its data was last edited")
    # The date in Detroit's own time zone (EDT in October, UTC-4; EST after
    # 1 November, UTC-5): the list's date is the city's, not UTC's.
    t = datetime.datetime.utcfromtimestamp(edited / 1000.0)
    offset = 4 if t < datetime.datetime(2026, 11, 1, 6) else 5
    list_date = (t - datetime.timedelta(hours=offset)).date().isoformat()
    feats = wc.esri(CITY_LAYER, {
        "where": "1=1",
        "outFields": ("precinct_id,election_precinct,polling_place_name,polling_place_address,"
                      "polling_place_cross_street,polling_place_zip_code"),
        "resultRecordCount": 2000,
    })
    return feats, list_date


def state_detroit():
    feats = wc.esri(STATE_PRECINCTS, {
        "where": "COUNTYFIPS = '163' AND MCDFIPS = '22000'",
        "outFields": "PRECINCTID,Precinct_Long_Name",
        "returnGeometry": "false",
        "resultRecordCount": 2000,
    })
    out = {}
    for f in feats:
        p = f["properties"]
        pid = (p.get("PRECINCTID") or "").strip()
        name = (p.get("Precinct_Long_Name") or "").strip()
        if not pid or not name:
            fail("a state precinct in Detroit has no PRECINCTID or name: %r" % p)
        if pid in out:
            fail("the state map repeats %s" % pid)
        out[pid] = name
    if len(set(out.values())) != len(out):
        fail("two state precincts in Detroit share a name, so the name cannot key the card")
    return out


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def geocode(rows):
    """{(address, zip): (lat, lng)} for the addresses the Census places at the
    same house number on the same street in the same ZIP code."""
    if not rows:
        return {}
    ordered = sorted(rows)
    lines = []
    for i, (addr, zipc) in enumerate(ordered):
        cells = [str(i), addr, "Detroit", "MI", zipc]
        lines.append(",".join('"%s"' % c.replace('"', "") for c in cells))
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        fh.write("\n".join(lines) + "\n")
        path = fh.name
    try:
        r = subprocess.run(["curl", "-sS", "--fail", "--max-time", "900", "--retry", "3",
                            "--retry-all-errors", "--retry-delay", "5", "-A", USER_AGENT,
                            "-F", "benchmark=Public_AR_Current",
                            "-F", "addressFile=@%s;type=text/csv" % path, GEOCODER_URL],
                           check=True, capture_output=True)
    finally:
        os.unlink(path)
    import csv
    import io
    out = {}
    for row in csv.reader(io.StringIO(r.stdout.decode("utf-8", "replace"))):
        if len(row) >= 6 and row[2] == "Match" and row[5]:
            asked = ordered[int(row[0])]
            if not same_house(asked[0], row[4]):
                # A match that changes the house number or the street is
                # another place, however close it lands.
                print("NO PIN: %s — the Census matched a different address, %s" % (asked[0], row[4]))
                continue
            matched_zip = row[4].strip().split(",")[-1].strip()
            if asked[1] and matched_zip != asked[1]:
                print("NO PIN: %s — the Census matched it in ZIP %s, the city lists %s"
                      % (asked[0], matched_zip, asked[1]))
                continue
            lng, lat = (float(v) for v in row[5].split(","))
            out[asked] = (round(lat, 6), round(lng, 6))
    return out


NUMBER_WORDS = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5", "SIX": "6",
                "SEVEN": "7", "EIGHT": "8", "NINE": "9", "TEN": "10", "ELEVEN": "11",
                "TWELVE": "12", "FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD"}
STREET_TYPES = {"N", "S", "E", "W", "ST", "STREET", "AVE", "AVENUE", "RD", "ROAD", "BLVD",
                "BOULEVARD", "DR", "DRIVE", "HWY", "HIGHWAY", "PKWY", "PARKWAY", "PL", "PLACE",
                "CT", "COURT", "LN", "LANE", "WAY", "TER", "TERRACE", "CIR", "CIRCLE",
                "SVC", "SERVICE"}


def street_key(s):
    """A street name with its type, direction and spacing taken out and number
    words written as digits, so the city's "W Seven Mile" and the Census's
    "W 7 MILE RD", or "McKinstry St" and "MC KINSTRY ST", compare equal while
    a different street does not. Measured 2026-10-24 on Detroit's 156 addresses:
    13 matches were refused for spelling alone before this."""
    w = re.sub(r"[^A-Z0-9 ]", " ", s.upper()).split()
    w = [NUMBER_WORDS.get(x, x) for x in w if x not in STREET_TYPES]
    return "".join(w)


def same_house(asked, matched):
    a = asked.upper().split()
    m = matched.upper().split(",")[0].split()
    if not a or not m or a[0] != m[0]:
        return False
    return street_key(" ".join(a[1:])) == street_key(" ".join(m[1:]))


def rings_of(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    fail("unexpected precinct geometry %s" % geometry["type"])


def inside(lat, lng, polygons):
    """Even-odd within each polygon, any part — the app's own rule."""
    for poly in polygons:
        hit = False
        for ring in poly:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                if (y1 > lat) != (y2 > lat) and lng < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                    hit = not hit
        if hit:
            return True
    return False


def distance_m(lat, lng, polygons):
    """Metres from the point to the nearest edge (equirectangular, city scale)."""
    kx = 111320.0 * math.cos(math.radians(lat))
    ky = 110574.0
    best = float("inf")
    for poly in polygons:
        for ring in poly:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                ax, ay = (x1 - lng) * kx, (y1 - lat) * ky
                bx, by = (x2 - lng) * kx, (y2 - lat) * ky
                dx, dy = bx - ax, by - ay
                t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
                best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def interior_point(polygons):
    """A point inside the shape: the middle of the widest interior run along
    the horizontal line through the middle of its largest part's extent."""
    best = None
    for poly in polygons:
        ys = [y for _, y in poly[0]]
        lat = (min(ys) + max(ys)) / 2.0
        xs = []
        for ring in poly:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                if (y1 > lat) != (y2 > lat):
                    xs.append(x1 + (lat - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            if best is None or b - a > best[0]:
                best = (b - a, lat, (a + b) / 2.0)
    if best is None:
        return None
    return best[1], best[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=wc.APP_DATA_DIR)
    args = ap.parse_args()
    out_path = os.path.join(args.out, OUT_NAME)

    robots()
    city, list_date = city_list()
    state = state_detroit()

    rows = {}
    city_shape = {}
    for f in city:
        p = f["properties"]
        pid = clean(p.get("precinct_id"))
        if not pid:
            fail("a city precinct has no precinct_id: %r" % p)
        if pid in rows:
            fail("the city's list repeats %s" % pid)
        place, addr = clean(p.get("polling_place_name")), clean(p.get("polling_place_address"))
        if not place or not addr:
            fail("%s has no polling place name or address" % pid)
        rows[pid] = {"place": place, "address": addr,
                     "cross": clean(p.get("polling_place_cross_street")),
                     "zip": clean(p.get("polling_place_zip_code"))}
        if f.get("geometry"):
            city_shape[pid] = rings_of(f["geometry"])

    if len(rows) != EXPECT_PRECINCTS:
        fail("the city's list has %d precincts, expected %d" % (len(rows), EXPECT_PRECINCTS))
    # The tripwire: the city's list and the state's map name the same precincts.
    if set(rows) != set(state):
        fail("the city's list and the state's precinct map disagree: only in the city's %s; "
             "only on the state's %s" % (sorted(set(rows) - set(state))[:20],
                                          sorted(set(state) - set(rows))[:20]))

    shipped = json.load(open(os.path.join(wc.APP_DATA_DIR, "mi-precincts.json"), encoding="utf-8"))
    drawn = {}
    for f in shipped["features"]:
        if f["properties"].get("geoid") == DETROIT_GEOID:
            drawn[f["properties"]["name"]] = rings_of(f["geometry"])
    if set(drawn) != set(state.values()):
        fail("the shipped precinct map's Detroit names are not the state's: only shipped %s; "
             "only on the state's %s" % (sorted(set(drawn) - set(state.values()))[:10],
                                          sorted(set(state.values()) - set(drawn))[:10]))

    # The ground tripwire: each drawn precinct's inside lies in the city's
    # polygon with the same code.
    by_name = {v: k for k, v in state.items()}
    wrong = []
    for name, polys in drawn.items():
        pt = interior_point(polys)
        pid = by_name[name]
        if pt is None or pid not in city_shape or not inside(pt[0], pt[1], city_shape[pid]):
            wrong.append((name, pid, pt))
    if wrong:
        fail("%d drawn precincts do not lie in the city's polygon with the same code, e.g. %s"
             % (len(wrong), wrong[:5]))

    previous = {}
    if os.path.exists(out_path):
        old = json.load(open(out_path, encoding="utf-8"))
        for s in old.get("sites", []):
            if s.get("lat") is not None:
                previous[(s["address"], s.get("zip") or "")] = (s["lat"], s["lng"])

    asked = {(r["address"], r["zip"]) for r in rows.values()}
    reused = {a: previous[a] for a in asked if a in previous}
    fresh = geocode(asked - set(reused))
    located = dict(reused)
    located.update(fresh)

    # One site per (address, building, cross street): two buildings can share
    # an address. The pin is tested against every precinct the building serves.
    serves = {}
    for pid, r in rows.items():
        serves.setdefault((r["address"], r["place"], r["cross"], r["zip"]), []).append(pid)
    site_index, sites, precincts, rejected, far = {}, [], {}, [], []
    for sk in sorted(serves):
        address, place, cross, zipc = sk
        pos = located.get((address, zipc))
        if pos is not None:
            polys = [p for pid in serves[sk] for p in drawn[state[pid]]]
            if not inside(pos[0], pos[1], polys):
                d = distance_m(pos[0], pos[1], polys)
                far.append(d)
                if d > PRECINCT_SLACK_M:
                    rejected.append((address, place, pos, d))
                    pos = None
        site = {"place": place, "address": address, "zip": zipc,
                "lat": pos[0] if pos else None, "lng": pos[1] if pos else None}
        if cross:
            site["crossStreet"] = cross
        site_index[sk] = len(sites)
        sites.append(site)
        for pid in serves[sk]:
            precincts[state[pid]] = site_index[sk]

    for a, p, pos, d in rejected:
        print("NO PIN: %s (%s) — the geocoder put it at %s, %d m from every precinct it serves"
              % (a, p, pos, d))
    for s in sites:
        if s["lat"] is None and not any(a == s["address"] for a, _, _, _ in rejected):
            print("NO PIN: %s (%s) — the Census geocoder found no match" % (s["address"], s["place"]))
    placed = sum(1 for s in sites if s["lat"] is not None)
    if far:
        far.sort()
        print("measured: %d placed buildings lie outside the precincts they serve; nearest edge "
              "median %d m, largest %d m" % (len(far), far[len(far) // 2], far[-1]))
    if placed < MIN_PLACED_FRACTION * len(sites):
        fail("only %d of %d buildings placed on the map" % (placed, len(sites)))

    out = {
        "election": ELECTION,
        "electionDate": ELECTION_DATE,
        "listDate": list_date,
        "geoid": DETROIT_GEOID,
        "sourcePage": ITEM_PAGE,
        "sourceUrl": CITY_LAYER,
        "lookupUrl": LOOKUP_URL,
        "sites": sites,
        "precincts": precincts,
    }
    os.makedirs(args.out, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d precincts, %d buildings (%d placed, %d reused, %d newly geocoded); "
          "list dated %s" % (out_path, len(precincts), len(sites), placed, len(reused),
                             len(fresh), list_date))
    print("The city's list and the state's precinct map hold the same %d precincts, on the "
          "same ground. This cannot see a polling place the city moved without updating its "
          "layer." % len(precincts))


if __name__ == "__main__":
    sys.exit(main())
