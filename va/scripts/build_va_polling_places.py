#!/usr/bin/env python3
"""
Build va/data/app/va-polling-places.json: each Virginia precinct's Election
Day polling place for the 2026-11-03 general election, joined to the precinct
map the app draws (va/data/app/va-precincts.json), with the Department of
Elections' own map position for each building.

    python3 va/scripts/build_va_polling_places.py          # fetch, join, write
    python3 va/scripts/build_va_polling_places.py --check  # offline: the shipped file holds together

THE SOURCE IS THE DEPARTMENT'S OWN MAP SERVICE, NOT ITS SPREADSHEET. The
Department publishes a polling place workbook per election under
elections.virginia.gov/media/registration-statistics/, and its robots.txt
(read 2026-11-03 with this builder's client) disallows every *.xlsx, *.xls,
*.csv and *.json path to every crawler, so nothing here reads it. The same
Department publishes the same assignments as a point layer in its own
ArcGIS organisation, Current_Voter_Polling_Locations (the organisation the
precinct map itself is read from, va/scripts/build_va_precincts.py; the host
has no robots.txt), one point per building with the building's name, street
address, city, ZIP and voting room, the locality and precinct it serves,
and the election it is for. Read 2026-11-03: 2,398 points in all 133
counties and cities, last written by the Department at 14:36 UTC on
2026-11-02 (the layer's dataLastEditDate).

THE JOIN IS ON THE DEPARTMENT'S OWN NUMBER, which the map carries as `num`
and the service as PrecinctCode (four digits, written as three in Virginia
Beach and with a trailing space in one Fairfax row, so it is stripped and
padded). The service spells one locality "King & Queen County" where the map
says "King and Queen County". Through that every one of the 2,398 points
lands on exactly one map precinct, and the build fails on a point that
lands on none or on two points for one precinct.

ONE POINT PER BUILDING, SO A PRECINCT THAT SHARES ITS BUILDING IS NOT
LISTED. Measured 2026-11-03: the 2,398 points are 2,398 distinct buildings,
each naming ONE precinct, and 133 of the map's 2,531 precincts are named by
no point — Fairfax County's WOODSON #1, whose neighbour WOODSON #2 is listed
at Woodson High School, is the shape. The service does not say which
building those 133 vote at, so the file lists them nowhere and the card
says, for a precinct the file does not name, that the Department's
polling-location map names no polling place for it and links the
Department's lookup, which answers by a voter's address. That is a statement
about the service and never a guess at the building. The build fails if
fewer than MIN_LISTED_FRACTION of the map's precincts are named, so a service
that empties out cannot ship as a short list.

THE PIN IS THE DEPARTMENT'S OWN POINT, kept only when it falls inside the
precinct's own county or city or within COUNTY_SLACK_M of it, tested
against this app's own county file; a point outside ships without a
position, and the app then looks the address up itself when a reader opens
that card, exactly as for any other pin. The service's second address line
(a PO box, or a direction to the entrance) is not part of the address a
reader is given.

THE DATE THE CARD GIVES is the day the Department last wrote the layer
(dataLastEditDate, read in Virginia's time zone), taken only when the
content changed since the shipped file; a day on which the Department
rewrote the layer with the same content keeps the shipped date, so an
unchanged service opens no pull request.

The app stops showing the polling place after the election date.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,  # noqa: E402
                            require_robots_once)

fail = make_fail("va-polling-places")

APP_DIR = os.path.join(REPO_ROOT, "va", "data", "app")
OUT_PATH = os.path.join(APP_DIR, "va-polling-places.json")
PRECINCTS_PATH = os.path.join(APP_DIR, "va-precincts.json")
COUNTIES_PATH = os.path.join(APP_DIR, "state-counties.json")

ELECTION_DATE = "2026-11-03"
ELECTION_NAME = "2026 November General"
SERVICE_URL = ("https://services5.arcgis.com/M3dium4ePYpmdT4B/arcgis/rest/services/"
               "Current_Voter_Polling_Locations/FeatureServer/0")
LOOKUP_URL = "https://vote.elections.virginia.gov/VoterInformation"

# The service's locality name -> the map's, where they differ.
LOCALITY_ALIASES = {"KING & QUEEN COUNTY": "KING AND QUEEN COUNTY"}

COUNTY_SLACK_M = 3000       # a polling place can sit just across a county line
MIN_LISTED_FRACTION = 0.90  # 2,398 of 2,531 (94.7%) on 2026-11-03
MIN_ROWS = 2300


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


def va_day(ms):
    """The calendar day in Virginia of an ArcGIS millisecond stamp."""
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:  # no zone database: Eastern Standard Time, which Election Day is in
        return dt.astimezone(timezone(timedelta(hours=-5))).date().isoformat()


def read_service():
    """Every point of the layer, and the day the Department last wrote it."""
    meta = get_json(SERVICE_URL, {"f": "json"})
    edited = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    if not edited:
        fail("the layer carries no dataLastEditDate")
    feats, offset = [], 0
    while True:
        d = get_json(SERVICE_URL + "/query", {
            "where": "1=1", "outFields": "*", "orderByFields": "OBJECTID", "outSR": 4326,
            "resultOffset": offset, "resultRecordCount": 2000, "f": "json"})
        page = d.get("features", [])
        feats.extend(page)
        if not page or not d.get("exceededTransferLimit"):
            break
        offset += len(page)
    if len(feats) < MIN_ROWS:
        fail("the Department's service has %d points, fewer than %d" % (len(feats), MIN_ROWS))
    names = {clean(f["attributes"].get("ElectionName")) for f in feats}
    dates = {va_day(f["attributes"]["ElectionDate"]) for f in feats if f["attributes"].get("ElectionDate")}
    if names != {ELECTION_NAME} or dates != {ELECTION_DATE}:
        fail("the service is for %s on %s, not %s on %s" % (sorted(names), sorted(dates), ELECTION_NAME, ELECTION_DATE))
    kinds = {clean(f["attributes"].get("ElectionType")) for f in feats}
    if len(kinds) != 1:
        fail("the service mixes election types: %s" % sorted(kinds))
    return feats, kinds.pop().title() + " Election", va_day(edited)


def map_keys():
    out = {}
    for f in json.load(open(PRECINCTS_PATH, encoding="utf-8"))["features"]:
        p = f["properties"]
        out[(p["county"].upper(), p["num"])] = (p["key"], p["countyFips"])
    return out


def county_polygons():
    out = {}
    for f in json.load(open(COUNTIES_PATH, encoding="utf-8"))["features"]:
        g = f["geometry"]
        out[f["properties"]["GEOID"]] = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
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
    zipc = clean(a.get("PollLoc_Zip"))[:5]
    return "%s, %s, VA %s" % (clean(a.get("PollLoc_AddressLine_1")), clean(a.get("PollLoc_City")), zipc)


def place_name(a):
    room = clean(a.get("PollLoc_VotingRoom"))
    name = clean(a.get("PollLoc_Name"))
    return "%s (%s)" % (name, room) if room else name


def build():
    feats, election, modified = read_service()
    mk = map_keys()
    counties = county_polygons()

    joined = {}          # map key -> the point of that precinct
    for f in feats:
        a = f["attributes"]
        locality = clean(a.get("LocalityName")).upper()
        locality = LOCALITY_ALIASES.get(locality, locality)
        code = clean(a.get("PrecinctCode")).zfill(4)
        if not clean(a.get("PollLoc_Name")) or not clean(a.get("PollLoc_AddressLine_1")):
            fail("%s %s has no polling place or address" % (locality, a.get("PrecinctName")))
        hit = mk.get((locality, code))
        if hit is None:
            fail("%s precinct %r (code %s) is not on the precinct map" % (locality, a.get("PrecinctName"), code))
        if hit[0] in joined:
            fail("the service names map precinct %s twice" % hit[0])
        joined[hit[0]] = f
    all_keys = {v[0] for v in mk.values()}
    unlisted = sorted(all_keys - set(joined))
    if len(joined) < MIN_LISTED_FRACTION * len(all_keys):
        fail("the service names a polling place for only %d of the map's %d precincts" % (len(joined), len(all_keys)))
    fips_of = {v[0]: v[1] for v in mk.values()}

    old = None
    if os.path.exists(OUT_PATH):
        old = json.load(open(OUT_PATH, encoding="utf-8"))

    site_index, sites = {}, []
    rejected = []

    def site_for(map_key, f):
        a = f["attributes"]
        sk = (place_name(a), address_line(a))
        if sk not in site_index:
            pos = None
            g = f.get("geometry") or {}
            if g.get("x") is not None and g.get("y") is not None:
                pos = (round(float(g["y"]), 6), round(float(g["x"]), 6))
                polys = counties[fips_of[map_key]]
                if not inside(pos[0], pos[1], polys) and distance_m(pos[0], pos[1], polys) > COUNTY_SLACK_M:
                    rejected.append((map_key, sk[1], pos))
                    pos = None
            site_index[sk] = len(sites)
            sites.append({"place": sk[0], "address": sk[1],
                          "lat": pos[0] if pos else None, "lng": pos[1] if pos else None})
        return site_index[sk]

    precincts = {}
    for k in sorted(joined):
        precincts[k] = site_for(k, joined[k])

    for k, a, pos in rejected:
        print("NO PIN: %s %s: the Department's point %s is more than %d m outside the county"
              % (k, a, pos, COUNTY_SLACK_M))
    placed = sum(1 for s in sites if s["lat"] is not None)

    out = {
        "election": election,
        "electionDate": ELECTION_DATE,
        "listDate": modified,
        "sourceUrl": SERVICE_URL,
        "lookupUrl": LOOKUP_URL,
        "sites": sites,
        "precincts": precincts,
        "unlisted": len(unlisted),
    }
    # A day on which the Department rewrote the layer with the same content
    # keeps the shipped date, so an unchanged service changes nothing here.
    if old is not None:
        same = {k: v for k, v in old.items() if k != "listDate"} == {k: v for k, v in out.items() if k != "listDate"}
        if same:
            out["listDate"] = old["listDate"]
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d of %d precincts named (%d named by no point), "
          "%d buildings (%d placed); %s on %s, service dated %s"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(precincts), len(all_keys), len(unlisted), len(sites),
             placed, election, ELECTION_DATE, out["listDate"]))


def check():
    """Offline: every named precinct is on the map, and enough of the map is named."""
    d = json.load(open(OUT_PATH, encoding="utf-8"))
    keys = {v[0] for v in map_keys().values()}
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
    if d["electionDate"] != ELECTION_DATE:
        fail("shipped file is for %s, this build for %s" % (d["electionDate"], ELECTION_DATE))
    print("OK va-polling-places.json: %d of %d precincts named, %d buildings (%d placed), service dated %s"
          % (len(listed), len(keys), n, sum(1 for s in d["sites"] if s["lat"] is not None), d["listDate"]))


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        check()
    else:
        build()
