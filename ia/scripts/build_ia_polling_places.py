#!/usr/bin/env python3
"""
Build ia/data/app/ia-polling-places.json: the polling place the Iowa
Legislature's statewide list names for each precinct on this app's precinct
map (ia/data/app/ia-precincts.json), with the list's own map position for
each building.

    python3 ia/scripts/build_ia_polling_places.py          # fetch, join, write
    python3 ia/scripts/build_ia_polling_places.py --check  # offline: the shipped file holds together

THE SOURCE is the Legislative Services Agency's public layer IowaPollingPlaces
(ArcGIS Online item b1e65daed17e46aca67dc19ed4248204, owner jodiflory), whose
description says its names, addresses and precincts come from the Secretary
of State and its positions from the state's address locator and hand
placement. Read 2026-11-03: 1,661 points, and EVERY row's LastUpdate and
EffectiveDate is 2022-10-17. So this is the list for the November 2022
general election, and the card says that in so many words: it gives the date
the list was last updated, says the polling place may have changed since, and
links the Secretary of State's own lookup, which answers by address. Adam
asked for it on 2026-11-03 knowing the date, and an e-mail asking the
Legislature whether a current list exists went to its GIS contact the same
day. The Secretary of State's site answers this project's robots.txt read
with HTTP 403 and publishes no statewide file, which is why this list is the
one read.

robots.txt: services2.arcgis.com answers /robots.txt with HTTP 403, which RFC
9309 section 2.3.1.3 reads as no policy (allow); require_robots_once makes
that reading with this builder's own client before the first fetch.

THE JOIN IS ON THE PRECINCT'S NAME within its county, because the list's
PrecinctCode is a county's own short code that the map does not carry. The
map is a later vintage than the list (2024-01-30 against 2022-10-17), so a
name is matched after folding case, runs of spaces, leading zeros on numbers
("01" and "1") and "TWSP"/"TWP", and nothing looser. Measured 2026-11-03:
1,624 of the map's 1,660 precincts are named this way. The other 36 are
precincts the 2022 list spells differently or does not have (Webster County
renamed every precinct, Winneshiek writes its combined townships with
commas), and their cards say the list names no polling place for that
precinct rather than guess which row it was. A list row naming no precinct on
the map is printed, never forced onto one. The build fails if fewer than
MIN_LISTED_FRACTION of the map's precincts are named.

THE PIN is the list's own point, kept only inside the precinct's county or
within COUNTY_SLACK_M of it, tested against this app's own county file; a
point outside ships without a position, and the app then looks the address up
itself when a reader opens that card.

THE DATE THE CARD GIVES is the latest LastUpdate on the list (a date-only
field, read as the day it names). The weekly job re-reads the list, so a newer list reaches the card
with its own date; an unchanged list writes the same bytes and opens nothing.
"""

import json
import math
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,  # noqa: E402
                            require_robots_once)

fail = make_fail("ia-polling-places")

APP_DIR = os.path.join(REPO_ROOT, "ia", "data", "app")
OUT_PATH = os.path.join(APP_DIR, "ia-polling-places.json")
PRECINCTS_PATH = os.path.join(APP_DIR, "ia-precincts.json")
COUNTIES_PATH = os.path.join(APP_DIR, "state-counties.json")

SERVICE_URL = ("https://services2.arcgis.com/KhKjlwEBlPJd6v51/arcgis/rest/services/"
               "IowaPollingPlaces/FeatureServer/0")
LOOKUP_URL = "https://sos.iowa.gov/voters/find-my-precinctpolling-place"

COUNTY_SLACK_M = 3000       # a polling place can sit just across a county line
MIN_LISTED_FRACTION = 0.90  # 1,624 of 1,660 (97.8%) on 2026-11-03
MIN_ROWS = 1500


def get_json(url, params):
    import requests  # function-local, as scraper_common.fetch does
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    r = requests.get(url, params=params, headers=UA_HEADERS_ROSTER_BOT, timeout=180)
    if r.status_code != 200:
        fail("HTTP %s from %s" % (r.status_code, url))
    d = r.json()
    if "error" in d:
        fail("%s answered an error: %s" % (url, d["error"]))
    return d


def clean(v):
    return " ".join(str(v).split()) if v is not None else ""


def fold(name):
    """The precinct-name comparison: case, spaces, leading zeros, TWSP."""
    s = clean(name).upper()
    s = re.sub(r"\b0+(\d)", r"\1", s)
    return s.replace("TWSP", "TWP")


def list_day(ms):
    """The day an ArcGIS date field names. These are date-only values stored
    as midnight UTC (every row reads 1665964800000, 2022-10-17T00:00Z), so
    the day is read in UTC; read in Iowa's time zone it would be the 16th."""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).date().isoformat()


def read_service():
    feats, offset = [], 0
    while True:
        d = get_json(SERVICE_URL + "/query", {
            "where": "1=1", "outFields": "*", "orderByFields": "OBJECTID", "outSR": 4326,
            "resultOffset": offset, "resultRecordCount": 1000, "f": "json"})
        page = d.get("features", [])
        feats.extend(page)
        if not page or not d.get("exceededTransferLimit"):
            break
        offset += len(page)
    if len(feats) < MIN_ROWS:
        fail("the Legislature's layer has %d points, fewer than %d" % (len(feats), MIN_ROWS))
    stamps = [f["attributes"].get("LastUpdate") for f in feats if f["attributes"].get("LastUpdate")]
    if not stamps:
        fail("no row of the layer carries a LastUpdate")
    return feats, list_day(max(stamps))


def map_precincts():
    """(county name folded, precinct name folded) -> [map keys]."""
    out = {}
    for f in json.load(open(PRECINCTS_PATH, encoding="utf-8"))["features"]:
        p = f["properties"]
        # Keyed by county NAME, not geoid: measured 2026-11-03, the map's
        # Wayne County precincts carry Polk's geoid (19153), so a geoid key
        # would test Wayne's polling places against Polk's outline.
        key = "%s|%s" % (p["county"], p["name"])
        out.setdefault((p["county"].upper(), fold(p["name"])), set()).add((key, p["county"]))
    return out


def county_polygons():
    out = {}
    for f in json.load(open(COUNTIES_PATH, encoding="utf-8"))["features"]:
        g = f["geometry"]
        out[f["properties"]["BASENAME"]] = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    return out


def inside(lat, lng, polygons):
    """Even-odd within each polygon, any part: the app's own rule."""
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


def address_line(a):
    city = clean(a.get("City"))
    zipc = clean(a.get("Zipcode"))[:5]
    return ("%s, %s, IA %s" % (clean(a.get("PhysicalAddress")), city, zipc)).strip()


def build():
    feats, list_date = read_service()
    mp = map_precincts()
    all_keys = {k for keys in mp.values() for k, _ in keys}
    fips_of = {k: g for keys in mp.values() for k, g in keys}
    counties = county_polygons()

    joined, stray = {}, []
    for f in feats:
        a = f["attributes"]
        if not clean(a.get("PollingPlaceName")) or not clean(a.get("PhysicalAddress")):
            stray.append((a.get("County"), a.get("Precinct"), "no polling place or address"))
            continue
        hits = mp.get((clean(a.get("County")).upper(), fold(a.get("Precinct"))))
        if not hits:
            stray.append((a.get("County"), a.get("Precinct"), "no precinct of that name on the map"))
            continue
        for key, _ in hits:
            if key in joined:
                fail("the list names map precinct %s twice" % key)
            joined[key] = f
    if len(joined) < MIN_LISTED_FRACTION * len(all_keys):
        fail("the list names a polling place for only %d of the map's %d precincts" % (len(joined), len(all_keys)))

    site_index, sites, rejected = {}, [], []
    precincts = {}
    for key in sorted(joined):
        a = joined[key]["attributes"]
        sk = (clean(a.get("PollingPlaceName")), address_line(a))
        if sk not in site_index:
            pos = None
            g = joined[key].get("geometry") or {}
            if g.get("x") is not None and g.get("y") is not None:
                pos = (round(float(g["y"]), 6), round(float(g["x"]), 6))
                polys = counties[fips_of[key]]
                if not inside(pos[0], pos[1], polys) and distance_m(pos[0], pos[1], polys) > COUNTY_SLACK_M:
                    rejected.append((key, sk[1], pos))
                    pos = None
            site_index[sk] = len(sites)
            sites.append({"place": sk[0], "address": sk[1],
                          "lat": pos[0] if pos else None, "lng": pos[1] if pos else None})
        precincts[key] = site_index[sk]

    for c, p, why in stray:
        print("NOT JOINED: %s %r: %s" % (c, p, why))
    for k, a, pos in rejected:
        print("NO PIN: %s %s: the list's point %s is more than %d m outside the county"
              % (k, a, pos, COUNTY_SLACK_M))

    out = {
        "listDate": list_date,
        "sourceUrl": SERVICE_URL,
        "lookupUrl": LOOKUP_URL,
        "sites": sites,
        "precincts": precincts,
        "unlisted": len(all_keys - set(precincts)),
    }
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d of %d precincts named (%d not), %d buildings (%d placed), "
          "%d list rows not joined; list last updated %s"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(precincts), len(all_keys), out["unlisted"],
             len(sites), sum(1 for s in sites if s["lat"] is not None), len(stray), list_date))


def check():
    """Offline: every named precinct is on the map, and enough of the map is named."""
    d = json.load(open(OUT_PATH, encoding="utf-8"))
    keys = {k for ks in map_precincts().values() for k, _ in ks}
    listed = set(d["precincts"])
    if listed - keys:
        fail("%d precincts in the polling list are not on the map: %s" % (len(listed - keys), sorted(listed - keys)[:10]))
    if len(listed) < MIN_LISTED_FRACTION * len(keys):
        fail("the polling list names only %d of the map's %d precincts" % (len(listed), len(keys)))
    if d.get("unlisted") != len(keys - listed):
        fail("the file says %r precincts are unlisted; the map has %d" % (d.get("unlisted"), len(keys - listed)))
    n = len(d["sites"])
    for k, i in d["precincts"].items():
        if not isinstance(i, int) or not 0 <= i < n:
            fail("precinct %s points at site %r" % (k, i))
    for s in d["sites"]:
        if not s["place"] or not s["address"]:
            fail("a site with no name or address: %r" % s)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d.get("listDate"))):
        fail("listDate %r is not a date" % d.get("listDate"))
    print("OK ia-polling-places.json: %d of %d precincts named, %d buildings (%d placed), list last updated %s"
          % (len(listed), len(keys), n, sum(1 for s in d["sites"] if s["lat"] is not None), d["listDate"]))


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        check()
    else:
        build()
