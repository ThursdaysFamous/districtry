#!/usr/bin/env python3
"""
Build il/data/app/chicago-polling-places.json from the output of
chicago_polling_places_scraper.py: each Chicago precinct's Election Day polling
place, with a map position for the building.

THE JOIN IS AGAINST THE PRECINCT MAP THE APP DRAWS. The Chicago Data Portal's
"Boundaries - Ward Precincts (2025-)" (i8fv-xe4b) is the ward-precinct layer's
source; its ward and precinct numbers are read here every run, and the build
fails unless the Board's list and the map hold exactly the same 1,291
(ward, precinct) pairs. A precinct the Board adds or retires, or a map that
moves, stops the refresh rather than shipping a card that names the wrong
building or none.

THE PIN. Each distinct address is placed with the U.S. Census Bureau's batch
geocoder (geocoding.geo.census.gov, no robots.txt, measured 2026-10-23), which
estimates a house number's position along its street's address range — the
same source the app's own search uses for a house-number pin. A position is
kept only when it falls inside the precinct's own ward or within
WARD_SLACK_M of it, tested against the city's ward boundaries (p293-wvbd) with
no geometry library; an address the geocoder cannot place, or places
elsewhere, ships with no position, and its card shows the address as text
with no pin. Positions already in the shipped file are reused for an address
whose text has not changed, so a daily run asks the Census only about new
addresses.

WHAT THE CARD IS TOLD: the election's name and date and the list's own date,
so a reader can see how current the answer is, and the Board's lookup as the
final word. The app stops showing the polling place after the election date.

Usage:
    python3 scripts/build_chicago_polling_places.py /tmp/chicago_polling_raw.json [out_dir]
"""

import csv
import io
import json
import math
import os
import sys

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,
                            require_robots_once)

fail = make_fail("chicago-polling-places")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
OUT_NAME = "chicago-polling-places.json"

PRECINCTS_URL = ("https://data.cityofchicago.org/resource/i8fv-xe4b.json"
                 "?$select=ward,precinct&$limit=5000")
WARDS_URL = "https://data.cityofchicago.org/resource/p293-wvbd.geojson?$limit=100"
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
LOOKUP_URL = "https://chicagoelections.gov/voting/your-voter-information"

EXPECT_PRECINCTS = 1291   # i8fv-xe4b and the Board's 2026-10-19 list, both measured 2026-10-23
EXPECT_WARDS = 50
WARD_SLACK_M = 800        # a polling place can sit just across its ward line
MIN_PLACED_FRACTION = 0.90


def get_json(url, **kw):
    import requests  # function-local, mirroring scraper_common.fetch
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    r = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=120, **kw)
    if r.status_code != 200:
        fail("HTTP %s from %s" % (r.status_code, url))
    return r.json()


def geocode(addresses):
    """{address: (lat, lng)} for the addresses the Census places; others absent."""
    import requests
    if not addresses:
        return {}
    require_robots_once(GEOCODER_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    buf = io.StringIO()
    w = csv.writer(buf)
    ordered = sorted(addresses)
    for i, a in enumerate(ordered):
        w.writerow([i, a, "Chicago", "IL", ""])
    r = requests.post(GEOCODER_URL, headers=UA_HEADERS_ROSTER_BOT,
                      data={"benchmark": "Public_AR_Current"},
                      files={"addressFile": ("addresses.csv", buf.getvalue())},
                      timeout=600)
    if r.status_code != 200:
        fail("Census geocoder HTTP %s" % r.status_code)
    out = {}
    for row in csv.reader(io.StringIO(r.text)):
        if len(row) >= 6 and row[2] == "Match" and row[5]:
            asked = ordered[int(row[0])]
            if not same_number_and_direction(asked, row[4]):
                # Measured 2026-10-23: asked for "2306 W 69TH ST" the Census
                # answered E 69th, nine kilometres away. A match that changes
                # the house number or the street's direction is another place.
                print("NO PIN: %s — the Census matched a different address, %s" % (asked, row[4]))
                continue
            lng, lat = (float(v) for v in row[5].split(","))
            out[asked] = (round(lat, 6), round(lng, 6))
    return out


def same_number_and_direction(asked, matched):
    a = asked.upper().split()
    m = matched.upper().split(",")[0].split()
    if not a or not m or a[0] != m[0]:
        return False
    # The Census spells some streets with no direction at all (STATE ST,
    # STONY ISLAND AVE); only a DIFFERENT direction is another place.
    if len(a) > 1 and a[1] in ("N", "S", "E", "W") and len(m) > 1 and m[1] in ("N", "S", "E", "W"):
        return m[1] == a[1]
    return True


def rings_of(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    fail("unexpected ward geometry %s" % geometry["type"])


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


def main():
    if len(sys.argv) < 2:
        fail("usage: build_chicago_polling_places.py RAW_JSON [OUT_DIR]")
    raw = json.load(open(sys.argv[1], encoding="utf-8"))
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    out_path = os.path.join(out_dir, OUT_NAME)

    rows = raw["rows"]
    keys = {}
    for r in rows:
        k = "%d-%d" % (r["ward"], r["precinct"])
        if k in keys:
            fail("precinct %s listed twice" % k)
        if not r["address"] or not r["place"]:
            fail("precinct %s has no address or building name" % k)
        keys[k] = r
    if len(keys) != EXPECT_PRECINCTS:
        fail("the Board's list has %d precincts, expected %d" % (len(keys), EXPECT_PRECINCTS))
    if len({r["ward"] for r in rows}) != EXPECT_WARDS:
        fail("the Board's list covers %d wards" % len({r["ward"] for r in rows}))

    # The tripwire: the list and the map the app draws must name the same precincts.
    mapped = {"%d-%d" % (int(x["ward"]), int(x["precinct"])) for x in get_json(PRECINCTS_URL)}
    if mapped != set(keys):
        fail("the Board's list and the precinct map disagree: only in the list %s; only on the map %s"
             % (sorted(set(keys) - mapped)[:20], sorted(mapped - set(keys))[:20]))

    wards = {}
    for f in get_json(WARDS_URL)["features"]:
        wards[int(f["properties"]["ward"])] = rings_of(f["geometry"])
    if len(wards) != EXPECT_WARDS:
        fail("ward boundaries: %d wards" % len(wards))

    shipped = {}
    if os.path.exists(out_path):
        old = json.load(open(out_path, encoding="utf-8"))
        for s in old.get("sites", []):
            if s.get("lat") is not None:
                shipped[s["address"]] = (s["lat"], s["lng"])

    addresses = {r["address"] for r in rows}
    reused = {a: shipped[a] for a in addresses if a in shipped}
    fresh = geocode(addresses - set(reused))
    located = dict(reused)
    located.update(fresh)

    # One site per (address, building): two buildings can share an address.
    site_index, sites, precincts = {}, [], {}
    rejected = []
    for k in sorted(keys, key=lambda s: tuple(int(p) for p in s.split("-"))):
        r = keys[k]
        sk = (r["address"], r["place"])
        if sk not in site_index:
            pos = located.get(r["address"])
            if pos is not None:
                polys = wards[r["ward"]]
                if not inside(pos[0], pos[1], polys) and distance_m(pos[0], pos[1], polys) > WARD_SLACK_M:
                    rejected.append((k, r["address"], pos))
                    pos = None
            site_index[sk] = len(sites)
            sites.append({"address": r["address"], "place": r["place"],
                          "lat": pos[0] if pos else None, "lng": pos[1] if pos else None})
        precincts[k] = site_index[sk]

    placed = sum(1 for s in sites if s["lat"] is not None)
    for k, a, pos in rejected:
        print("NO PIN: %s %s — the geocoder put it at %s, more than %d m outside ward %s"
              % (k, a, pos, WARD_SLACK_M, k.split("-")[0]))
    for s in sites:
        if s["lat"] is None and not any(a == s["address"] for _, a, _ in rejected):
            print("NO PIN: %s (%s) — the Census geocoder found no match" % (s["address"], s["place"]))
    if placed < MIN_PLACED_FRACTION * len(sites):
        fail("only %d of %d buildings placed on the map" % (placed, len(sites)))

    out = {
        "election": raw["election"],
        "electionDate": raw["electionDate"],
        "listDate": raw["listDate"],
        "sourcePage": raw["sourcePage"],
        "sourceUrl": raw["sourceUrl"],
        "lookupUrl": LOOKUP_URL,
        "sites": sites,
        "precincts": precincts,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d precincts, %d buildings (%d placed, %d reused, %d newly geocoded); "
          "%s on %s, list dated %s"
          % (out_path, len(precincts), len(sites), placed, len(reused), len(fresh),
             raw["election"], raw["electionDate"], raw["listDate"]))
    print("The list and the precinct map hold the same %d precincts. This cannot see a "
          "polling place the Board moved without publishing a new list." % len(precincts))


if __name__ == "__main__":
    sys.exit(main())
