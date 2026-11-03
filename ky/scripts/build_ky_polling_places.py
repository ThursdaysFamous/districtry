#!/usr/bin/env python3
"""
Build ky/data/app/ky-polling-places.json: each Kentucky precinct's Election
Day polling place for the 2026-11-03 general election, or the voting centers
its county opens to every voter, joined to the precinct map the app draws
(ky/data/app/ky-precincts.json), with a map position for each building.

    python3 ky/scripts/build_ky_polling_places.py          # fetch, join, write
    python3 ky/scripts/build_ky_polling_places.py --check  # offline: the shipped file holds together

THE LIST. The State Board of Elections publishes one workbook for the
election, linked from elect.ky.gov/Voters/Pages/Polling-Locations.aspx as
"All Polling Locations - Spreadsheet", with a sheet per voting period; this
build reads the Election Day sheet. One row per building: the county, the
building's name, street, city and ZIP, its hours, whether it is a polling
location or a voting center, and the precincts it serves, as codes
("A102, A104, A105") or "ALL". Read 2026-11-03: 1,432 rows in all 120
counties, 796 polling locations and 636 voting centers, the sheet's own
header saying it was updated 11/2/26, and the workbook last written at
15:24 UTC on 2026-11-02. elect.ky.gov has no robots.txt (404, allow all),
read 2026-11-03 with this builder's client.

TWO KINDS OF ROW, AND THE CARD SHOWS BOTH. A POLLING LOCATION names the
precincts assigned to it, and those codes are the map's own (ky-precincts.json
keys a precinct by its county's FIPS code and the state's precinct code, so
"Adair A102" is 21001A102); every code in the list lands on a map precinct and
none lands on two buildings, or the build fails, and a row the sheet repeats
whole (Jefferson's Grace James Academy, twice, on 2026-11-03) is one row.
Lexington writes a merged pair as "B200/B226", which is two codes. A VOTING
CENTER serves "ALL": any voter in the county may use any of them (KRS
117.065), so it is filed by county rather than by precinct. Measured
2026-11-03: 94 counties open voting centers, 78 of them nothing else, 16 both
(Jefferson and Fayette among them), and 26 assign every precinct a polling
location; one precinct, Lyon's X001, is in neither list and the card says so.
The build fails if a county is missing, and prints the precincts named
nowhere.

THE PIN. Each distinct address is placed with the U.S. Census Bureau's batch
geocoder (geocoding.geo.census.gov, no robots.txt), the same source the
Illinois and North Carolina polling-place builds use. A position is kept only
when the Census matched the same house number and the point falls inside the
building's own county or within COUNTY_SLACK_M of it, tested against this
app's own county file. An address it cannot place ships without a position,
and the app then looks it up itself when a reader opens that card, exactly
as for any other pin. Positions already in the shipped file are reused for
an address whose text has not changed, so a daily run asks the Census only
about new addresses.

THE DATE THE CARD GIVES is the day the Board's workbook was last written
(Last-Modified, read in Frankfort's time zone), taken only when the list's
content changed since the shipped file; a day on which the Board rewrote the
workbook with the same content keeps the shipped date, so an unchanged list
opens no pull request.

The app stops showing the polling place after the election date.
"""

import csv
import io
import json
import math
import os
import re
import sys
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,  # noqa: E402
                            require_robots_once)

fail = make_fail("ky-polling-places")

APP_DIR = os.path.join(REPO_ROOT, "ky", "data", "app")
OUT_PATH = os.path.join(APP_DIR, "ky-polling-places.json")
PRECINCTS_PATH = os.path.join(APP_DIR, "ky-precincts.json")
COUNTIES_PATH = os.path.join(APP_DIR, "state-counties.json")

ELECTION_DATE = "2026-11-03"
ELECTION_DAY_WORDS = "November 3"   # as the Election Day sheet is named
LIST_URL = "https://elect.ky.gov/Voters/Documents/All%20Polling%20Locations%20-%20Spreadsheet.xlsx"
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
LOOKUP_URL = "https://elect.ky.gov/Voters/Pages/Polling-Locations.aspx"

COUNTY_SLACK_M = 3000      # a polling place can sit just across a county line
# 1,100 of 1,423 buildings (77.3%) on 2026-11-03: rural Kentucky's "12592 ST
# RT 93 S" and "0 Lee S Jones Park Rd" are addresses the Census geocoder does
# not hold, and a building it cannot place ships with its address and no
# position, which the app looks up itself when the card opens.
MIN_PLACED_FRACTION = 0.70
MIN_ROWS = 1300            # 1,432 on 2026-11-03
COUNTIES = 120

COLUMNS = ("County", "Polling Location Title", "Polling Location Street", "Polling Location City",
           "Polling Location Zip", "Polling Location Date/Time", "Precincts")


def get(url, **kw):
    import requests  # function-local, as scraper_common.fetch does
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    r = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=180, **kw)
    if r.status_code != 200:
        fail("HTTP %s from %s" % (r.status_code, url))
    return r


def clean(v):
    return " ".join(str(v).split()) if v is not None else ""


def ky_day(stamp):
    """The calendar day in Frankfort of an HTTP date."""
    dt = parsedate_to_datetime(stamp)
    try:
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:  # no zone database: Eastern Standard Time, which Election Day is in
        return dt.astimezone(timezone(timedelta(hours=-5))).date().isoformat()


def read_list():
    """The Election Day sheet's rows as dicts, and the day the Board last wrote the workbook."""
    import openpyxl
    r = get(LIST_URL)
    modified = r.headers.get("Last-Modified")
    if not modified:
        fail("the list carries no Last-Modified date")
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True)
    sheets = [n for n in wb.sheetnames if "Election Day" in n]
    if len(sheets) != 1:
        fail("the workbook has %d Election Day sheets: %s" % (len(sheets), wb.sheetnames))
    if ELECTION_DAY_WORDS not in sheets[0]:
        fail("the Election Day sheet is %r, not for %s" % (sheets[0], ELECTION_DATE))
    ws = wb[sheets[0]]
    it = ws.iter_rows(values_only=True)
    header = [clean(h) for h in next(it)]
    for c in COLUMNS:
        if c not in header:
            fail("the sheet has no %r column; its columns are %s" % (c, header))
    rows = []
    for raw in it:
        raw = list(raw) + [None] * (len(header) - len(raw))
        d = dict(zip(header, raw))
        if not clean(d.get("County")):
            if any(clean(v) for v in raw):
                fail("a row with no county: %r" % (raw,))
            continue
        rows.append(d)
    if len(rows) < MIN_ROWS:
        fail("the Board's list has %d rows, fewer than %d" % (len(rows), MIN_ROWS))
    return rows, ky_day(modified)


def counties():
    """{county name in capitals: (GEOID, name as the map writes it, polygons)}."""
    out = {}
    for f in json.load(open(COUNTIES_PATH, encoding="utf-8"))["features"]:
        p = f["properties"]
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        out[p["BASENAME"].upper()] = (p["GEOID"], p["NAME"], polys)
    if len(out) != COUNTIES:
        fail("the county file has %d counties, not %d" % (len(out), COUNTIES))
    return out


def map_keys():
    """{map key: county GEOID} for every precinct the map draws."""
    out = {}
    for f in json.load(open(PRECINCTS_PATH, encoding="utf-8"))["features"]:
        p = f["properties"]
        out[p["key"]] = p["countyFips"]
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


def same_number(asked, matched):
    """The Census matched the same house number, and no other direction."""
    a = asked.upper().split()
    m = matched.upper().split(",")[0].split()
    if not a or not m or a[0] != m[0]:
        return False
    if len(a) > 1 and a[1] in ("N", "S", "E", "W") and len(m) > 1 and m[1] in ("N", "S", "E", "W"):
        return a[1] == m[1]
    return True


def geocode(sites):
    """{(street, city, zip): (lat, lng)} for the addresses the Census places."""
    import requests
    if not sites:
        return {}
    require_robots_once(GEOCODER_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    ordered = sorted(sites)
    out = {}
    for start in range(0, len(ordered), 2000):
        chunk = ordered[start:start + 2000]
        buf = io.StringIO()
        w = csv.writer(buf)
        for i, (street, city, zipc) in enumerate(chunk):
            w.writerow([start + i, street, city, "KY", zipc])
        r = requests.post(GEOCODER_URL, headers=UA_HEADERS_ROSTER_BOT,
                          data={"benchmark": "Public_AR_Current"},
                          files={"addressFile": ("addresses.csv", buf.getvalue())},
                          timeout=900)
        if r.status_code != 200:
            fail("Census geocoder HTTP %s" % r.status_code)
        for row in csv.reader(io.StringIO(r.text)):
            if len(row) >= 6 and row[2] == "Match" and row[5]:
                asked = ordered[int(row[0])]
                if not same_number(asked[0], row[4]):
                    print("NO PIN: %s, %s: the Census matched a different address, %s"
                          % (asked[0], asked[1], row[4]))
                    continue
                lng, lat = (float(v) for v in row[5].split(","))
                out[asked] = (round(lat, 6), round(lng, 6))
    return out


def address_line(street, city, zipc):
    return "%s, %s, KY %s" % (street, city, zipc)


def site_tuple(d):
    zipc = clean(d["Polling Location Zip"])
    if len(zipc) == 4:  # a ZIP read as a number loses a leading zero; none in Kentucky, which starts at 40003
        zipc = "0" + zipc
    return (clean(d["Polling Location Street"]), clean(d["Polling Location City"]), zipc[:5])


def precinct_codes(text):
    """The codes a Precincts cell names, or None for ALL."""
    if clean(text).upper() == "ALL":
        return None
    codes = []
    for t in re.split(r"[,;/&]|\s+and\s+", clean(text)):
        t = t.strip().upper()
        if not t:
            continue
        if not re.fullmatch(r"[A-Z]\d{3}", t):
            fail("a precinct code this build does not read: %r in %r" % (t, text))
        codes.append(t)
    return codes


def build():
    rows, modified = read_list()
    cty = counties()
    mk = map_keys()

    assigned = {}        # map key -> site key
    centers = {}         # county GEOID -> [site key]
    site_rows = {}       # site key -> row
    seen = set()
    for d in rows:
        county = clean(d["County"]).upper()
        if county not in cty:
            fail("the list names a county the map does not have: %r" % county)
        fips = cty[county][0]
        if not clean(d["Polling Location Title"]) or not clean(d["Polling Location Street"]):
            fail("%s: a row with no building or address: %r" % (county, d))
        whole = (county,) + tuple(clean(d[c]) for c in COLUMNS[1:])
        if whole in seen:
            continue  # the sheet repeats a row whole
        seen.add(whole)
        sk = (fips, clean(d["Polling Location Title"])) + site_tuple(d)
        site_rows.setdefault(sk, d)
        codes = precinct_codes(d["Precincts"])
        if codes is None:
            centers.setdefault(fips, []).append(sk)
            continue
        for code in codes:
            key = fips + code
            if key not in mk:
                fail("%s precinct %s is in the Board's list and not on the precinct map" % (county, code))
            if assigned.get(key, sk) != sk:
                fail("the Board's list sends %s precinct %s to two buildings: %s and %s"
                     % (county, code, assigned[key][1], sk[1]))
            assigned[key] = sk
    listed_counties = {sk[0] for sk in site_rows}
    if len(listed_counties) != COUNTIES:
        fail("the list covers %d of %d counties" % (len(listed_counties), COUNTIES))
    unlisted = sorted(k for k, fips in mk.items() if k not in assigned and fips not in centers)
    for k in unlisted:
        print("NO POLLING PLACE: map precinct %s is assigned no building and its county opens no voting center" % k)

    shipped = {}
    old = None
    if os.path.exists(OUT_PATH):
        old = json.load(open(OUT_PATH, encoding="utf-8"))
        for s in old.get("sites", []):
            if s.get("lat") is not None:
                shipped[s["address"]] = (s["lat"], s["lng"])
    wanted = {sk[2:] for sk in site_rows}
    reused = {t: shipped[address_line(*t)] for t in wanted if address_line(*t) in shipped}
    fresh = geocode(wanted - set(reused))
    located = dict(reused)
    located.update(fresh)

    site_index, sites = {}, []
    rejected = []
    for sk in sorted(site_rows, key=lambda s: (s[0], s[1], s[2])):
        t = sk[2:]
        pos = located.get(t)
        if pos is not None:
            polys = cty_polys = next(v[2] for v in cty.values() if v[0] == sk[0])
            if not inside(pos[0], pos[1], polys) and distance_m(pos[0], pos[1], cty_polys) > COUNTY_SLACK_M:
                rejected.append((sk[0], address_line(*t), pos))
                pos = None
        site_index[sk] = len(sites)
        sites.append({"place": sk[1], "address": address_line(*t),
                      "hours": clean(site_rows[sk]["Polling Location Date/Time"]) or None,
                      "lat": pos[0] if pos else None, "lng": pos[1] if pos else None})
    for fips, a, pos in rejected:
        print("NO PIN: county %s %s: the geocoder put it at %s, more than %d m outside the county"
              % (fips, a, pos, COUNTY_SLACK_M))
    placed = sum(1 for s in sites if s["lat"] is not None)
    if placed < MIN_PLACED_FRACTION * len(sites):
        fail("only %d of %d buildings placed on the map" % (placed, len(sites)))

    out = {
        "election": "General Election",
        "electionDate": ELECTION_DATE,
        "listDate": modified,
        "sourceUrl": LIST_URL,
        "lookupUrl": LOOKUP_URL,
        "sites": sites,
        "precincts": {k: site_index[sk] for k, sk in sorted(assigned.items())},
        "centers": {fips: [site_index[sk] for sk in sks] for fips, sks in sorted(centers.items())},
        "unlisted": unlisted,
    }
    # A day on which the Board rewrote the workbook with the same content
    # keeps the shipped date, so an unchanged list changes nothing here.
    if old is not None:
        same = {k: v for k, v in old.items() if k != "listDate"} == {k: v for k, v in out.items() if k != "listDate"}
        if same:
            out["listDate"] = old["listDate"]
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d precincts assigned a polling place, %d counties with voting centers (%d of them with "
          "nothing else), %d precincts named nowhere, %d buildings (%d placed, %d reused, %d newly geocoded); "
          "list dated %s"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(assigned), len(centers),
             sum(1 for f in centers if not any(fips == f for fips in (mk[k] for k in assigned))),
             len(unlisted), len(sites), placed, len(reused), len(fresh), out["listDate"]))


def check():
    """Offline: every precinct on the map has a polling place, a county center, or is named as having neither."""
    d = json.load(open(OUT_PATH, encoding="utf-8"))
    mk = map_keys()
    n = len(d["sites"])
    for k, i in d["precincts"].items():
        if k not in mk:
            fail("the polling list assigns %s, which is not on the precinct map" % k)
        if not isinstance(i, int) or not 0 <= i < n:
            fail("precinct %s points at site %r" % (k, i))
    fips_all = set(mk.values())
    for fips, idx in d["centers"].items():
        if fips not in fips_all:
            fail("centers names county %s, which no map precinct is in" % fips)
        if not idx or any(not isinstance(i, int) or not 0 <= i < n for i in idx):
            fail("county %s's centers point at %r" % (fips, idx))
    expect = sorted(k for k, fips in mk.items() if k not in d["precincts"] and fips not in d["centers"])
    if expect != d.get("unlisted"):
        fail("the precincts with neither a polling place nor a county center are %s; the file says %s"
             % (expect, d.get("unlisted")))
    for s in d["sites"]:
        if not s["place"] or not s["address"]:
            fail("a site with no name or address: %r" % s)
    if d["electionDate"] != ELECTION_DATE:
        fail("shipped file is for %s, this build for %s" % (d["electionDate"], ELECTION_DATE))
    print("OK ky-polling-places.json: %d precincts assigned, %d counties with voting centers, %d named nowhere, "
          "%d buildings (%d placed), list dated %s"
          % (len(d["precincts"]), len(d["centers"]), len(d["unlisted"]), n,
             sum(1 for s in d["sites"] if s["lat"] is not None), d["listDate"]))


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        check()
    else:
        build()
