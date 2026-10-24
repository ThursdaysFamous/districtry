#!/usr/bin/env python3
"""
Build nc/data/app/nc-polling-places.json: each North Carolina precinct's
Election Day polling place for the 2026-11-03 general election, joined to the
precinct map the app draws (nc/data/app/nc-precincts.json), with a map
position for each building.

    python3 nc/scripts/build_nc_polling_places.py          # fetch, join, write
    python3 nc/scripts/build_nc_polling_places.py --check  # offline: the shipped file holds together

THE LIST. The State Board of Elections publishes one file per election,
dl.ncsbe.gov/ENRS/<yyyy_mm_dd>/polling_place_<yyyymmdd>.csv: UTF-16,
tab-separated, one row per precinct with the county, the precinct's NAME, the
polling place's name and its street address, city and ZIP. Read 2026-10-23:
2,626 rows in 100 counties, the object re-written daily (its Last-Modified was
09:25 UTC that morning). dl.ncsbe.gov has no robots.txt (404, allow all),
measured again on 2026-10-24.

THE LIST NAMES A PRECINCT AND THE MAP KEYS IT BY CODE, AND THE NAMES DO NOT
AGREE. The map is NC OneMap's copy of the Board's 2026-08-24 precinct file,
whose name field is in places the precinct's name, in places its code
("007"), in places a polling place's name (all of Union and Buncombe) and in
places "Voting District 00ANTI" (Granville, Greene). Matching the list's names
against it directly joined 2,555 of 2,626 and left 71 for guesswork. So the
join goes through a third file from the same Board that carries both: the
Voting Information Project feed for the same election
(dl.ncsbe.gov/data/vipFeed/vipFeed-37-<yyyy-mm-dd>.zip), whose precinct.txt
gives each precinct's county, name and code ("number"). Measured 2026-10-24:
every (county, name) in that feed has exactly one code, and through it 2,625
of the list's 2,626 rows land on a precinct of the map, each on a different
one, with none of the map's 2,625 left over. The list spells five Sampson
precincts "CLINTON, EAST" where the feed has "CLINTON EAST", so punctuation
is ignored on both sides.

THE ONE ROW THE MAP DOES NOT HAVE. Henderson County's CAROLINA VILLAGE
precinct (code CV) is in the list and the feed and not in the 2026-08-24 map:
the county drew it later. Its 25 street segments in the feed are the Carolina
Village streets off Lark Spur Drive, and 10 Lark Spur Dr (placed by the
Census geocoder at 35.34310, -82.44435) is inside the map's HENDERSONVILLE-2
(HV-2). So a reader there is drawn in HV-2 and would be given HV-2's polling
place. CARVED_OUT records that, and the HV-2 card names both polling places
and says which streets vote at the second. The build fails if any other list
row has no precinct on the map, or if this one stops being missing, so the
table cannot go stale quietly.

THE PIN. Each distinct address is placed with the U.S. Census Bureau's batch
geocoder (geocoding.geo.census.gov, no robots.txt), the same source the
Illinois polling-place build uses. A position is kept only when the Census
matched the same house number and the point falls inside the precinct's own
county or within COUNTY_SLACK_M of it, tested against this app's own county
file. An address it cannot place ships without a position, and the app then
looks it up itself when a reader opens that card, exactly as for any other
pin. Positions already in the shipped file are reused for an address whose
text has not changed, so a daily run asks the Census only about new
addresses.

THE DATE THE CARD GIVES is the day the Board's file was last written
(Last-Modified, read in North Carolina's time zone), taken only when the
list's content changed since the shipped file; a day on which the Board
rewrote the file with the same content keeps the shipped date, so an
unchanged list opens no pull request.

The app stops showing the polling place after the election date.
"""

import csv
import io
import json
import math
import os
import re
import sys
import zipfile
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,  # noqa: E402
                            require_robots_once)

fail = make_fail("nc-polling-places")

APP_DIR = os.path.join(REPO_ROOT, "nc", "data", "app")
OUT_PATH = os.path.join(APP_DIR, "nc-polling-places.json")
PRECINCTS_PATH = os.path.join(APP_DIR, "nc-precincts.json")
COUNTIES_PATH = os.path.join(APP_DIR, "state-counties.json")

ELECTION_DATE = "2026-11-03"
_Y, _M, _D = ELECTION_DATE.split("-")
LIST_URL = "https://dl.ncsbe.gov/ENRS/%s_%s_%s/polling_place_%s%s%s.csv" % (_Y, _M, _D, _Y, _M, _D)
VIP_URL = "https://dl.ncsbe.gov/data/vipFeed/vipFeed-37-%s.zip" % ELECTION_DATE
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
LOOKUP_URL = "https://vt.ncsbe.gov/PPLkup/"

# (county, the list's precinct name) -> the map precinct whose ground it was
# carved from, measured 2026-10-24 as the docstring describes.
CARVED_OUT = {
    ("HENDERSON", "CAROLINA VILLAGE"): {
        "mapKey": "37089-HV-2",
        "where": "on the Carolina Village streets off Lark Spur Drive",
    },
}

COUNTY_SLACK_M = 3000      # a polling place can sit just across a county line
MIN_PLACED_FRACTION = 0.85
MIN_ROWS = 2500            # 2,626 on 2026-10-23


def get(url, **kw):
    import requests  # function-local, as scraper_common.fetch does
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    r = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=180, **kw)
    if r.status_code != 200:
        fail("HTTP %s from %s" % (r.status_code, url))
    return r


def norm(name):
    """A precinct name with case, punctuation and spacing taken out."""
    return " ".join(re.sub(r"[^A-Z0-9#&/\-. ]", " ", str(name).upper()).replace(",", " ").split())


def read_list():
    r = get(LIST_URL)
    raw = r.content
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    if len(rows) < MIN_ROWS:
        fail("the Board's list has %d rows, fewer than %d" % (len(rows), MIN_ROWS))
    want = "%s/%s/%s" % (_M, _D, _Y)
    dates = {x["election_dt"].strip() for x in rows}
    if dates != {want}:
        fail("the list is for %s, not %s" % (sorted(dates), want))
    modified = r.headers.get("Last-Modified")
    if not modified:
        fail("the list carries no Last-Modified date")
    from datetime import timedelta, timezone
    # North Carolina's own day. Eastern Daylight Time runs to 2026-11-01;
    # after that the list no longer matters to this build.
    stamp = parsedate_to_datetime(modified).astimezone(timezone(timedelta(hours=-4)))
    return rows, stamp.date().isoformat()


def read_crosswalk():
    """{(county, normalised precinct name): code} from the Board's VIP feed."""
    z = zipfile.ZipFile(io.BytesIO(get(VIP_URL).content))

    def table(name):
        member = [n for n in z.namelist() if n.endswith("/" + name) or n == name]
        if len(member) != 1:
            fail("VIP feed has %d copies of %s" % (len(member), name))
        return list(csv.DictReader(io.StringIO(z.read(member[0]).decode("utf-8-sig"))))

    loc = {x["id"]: x["name"].replace(" COUNTY BOARD OF ELECTIONS", "").strip() for x in table("locality.txt")}
    election = table("election.txt")
    if len(election) != 1 or election[0]["date"] != ELECTION_DATE:
        fail("VIP feed is not for %s: %r" % (ELECTION_DATE, [e.get("date") for e in election]))
    xw = {}
    for p in table("precinct.txt"):
        k = (loc[p["locality_id"]], norm(p["name"]))
        code = p["number"].strip()
        if xw.get(k, code) != code:
            fail("VIP feed gives %s two codes: %s and %s" % (k, xw[k], code))
        xw[k] = code
    return xw, election[0]["election_type"].strip().title() + " Election"


def map_keys():
    out = {}
    for f in json.load(open(PRECINCTS_PATH, encoding="utf-8"))["features"]:
        p = f["properties"]
        county = re.sub(r" COUNTY$", "", p["county"].upper())
        out[(county, p["code"])] = (p["key"], p["countyFips"])
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


def same_number(asked, matched):
    """The Census matched the same house number, and no other direction."""
    a = asked.upper().split()
    m = matched.upper().split(",")[0].split()
    if not a or not m or a[0] != m[0]:
        return False
    # "4113 N C HWY 581" is a state highway, not North: "N C" is never a direction.
    if len(a) > 2 and a[1] == "N" and a[2] == "C":
        return True
    if len(a) > 1 and a[1] in ("N", "S", "E", "W") and len(m) > 1 and m[1] in ("N", "S", "E", "W"):
        return a[1] == m[1]
    return True


def for_geocoder(street):
    """The street as the geocoder reads it best: "410N MARKET ST" -> "410 N MARKET ST"."""
    return re.sub(r"^(\d+)([NSEW])\s", r"\1 \2 ", street)


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
            w.writerow([start + i, for_geocoder(street), city, "NC", zipc])
        r = requests.post(GEOCODER_URL, headers=UA_HEADERS_ROSTER_BOT,
                          data={"benchmark": "Public_AR_Current"},
                          files={"addressFile": ("addresses.csv", buf.getvalue())},
                          timeout=900)
        if r.status_code != 200:
            fail("Census geocoder HTTP %s" % r.status_code)
        for row in csv.reader(io.StringIO(r.text)):
            if len(row) >= 6 and row[2] == "Match" and row[5]:
                asked = ordered[int(row[0])]
                if not same_number(for_geocoder(asked[0]), row[4]):
                    print("NO PIN: %s, %s: the Census matched a different address, %s"
                          % (asked[0], asked[1], row[4]))
                    continue
                lng, lat = (float(v) for v in row[5].split(","))
                out[asked] = (round(lat, 6), round(lng, 6))
    return out


def address_line(street, city, zipc):
    return "%s, %s, NC %s" % (street, city, zipc)


def build():
    rows, modified = read_list()
    xw, election = read_crosswalk()
    mk = map_keys()
    counties = county_polygons()

    joined = {}          # map key -> row
    carved = []          # (map key, row, where)
    for r in rows:
        county = r["county_name"].strip().upper()
        name = r["precinct_name"].strip()
        if not r["polling_place_name"].strip() or not r["street_address"].strip():
            fail("%s %s has no polling place or address" % (county, name))
        code = xw.get((county, norm(name)))
        if code is None:
            fail("%s precinct %r is not in the Board's VIP feed" % (county, name))
        hit = mk.get((county, code))
        if hit is None:
            entry = CARVED_OUT.get((county, name.upper()))
            if entry is None:
                fail("%s precinct %r (code %s) is not on the precinct map, and CARVED_OUT "
                     "does not say whose ground it was drawn from" % (county, name, code))
            carved.append((entry["mapKey"], r, entry["where"]))
            continue
        if hit[0] in joined:
            fail("two list rows land on map precinct %s" % hit[0])
        joined[hit[0]] = r
    for (county, name), entry in CARVED_OUT.items():
        if not any(c[1]["county_name"].strip().upper() == county and c[1]["precinct_name"].strip().upper() == name
                   for c in carved):
            fail("CARVED_OUT names %s %s, which the list no longer has off the map; retire the entry"
                 % (county, name))
        if entry["mapKey"] not in joined:
            fail("CARVED_OUT points %s %s at %s, which is not a joined map precinct" % (county, name, entry["mapKey"]))
    missing = sorted({v[0] for v in mk.values()} - set(joined))
    if missing:
        fail("%d map precincts have no row in the Board's list: %s" % (len(missing), missing[:20]))
    fips_of = {v[0]: v[1] for v in mk.values()}

    shipped = {}
    old = None
    if os.path.exists(OUT_PATH):
        old = json.load(open(OUT_PATH, encoding="utf-8"))
        for s in old.get("sites", []):
            if s.get("lat") is not None:
                shipped[s["address"]] = (s["lat"], s["lng"])

    def site_tuple(r):
        return (" ".join(r["street_address"].split()), " ".join(r["city"].split()), r["zip"].strip())

    all_rows = [(k, r) for k, r in joined.items()] + [(k, r) for k, r, _ in carved]
    wanted = {site_tuple(r) for _, r in all_rows}
    reused = {t: shipped[address_line(*t)] for t in wanted if address_line(*t) in shipped}
    fresh = geocode(wanted - set(reused))
    located = dict(reused)
    located.update(fresh)

    site_index, sites = {}, []
    rejected = []

    def site_for(map_key, r):
        t = site_tuple(r)
        sk = (t, " ".join(r["polling_place_name"].split()))
        if sk not in site_index:
            pos = located.get(t)
            if pos is not None:
                polys = counties[fips_of[map_key]]
                if not inside(pos[0], pos[1], polys) and distance_m(pos[0], pos[1], polys) > COUNTY_SLACK_M:
                    rejected.append((map_key, address_line(*t), pos))
                    pos = None
            site_index[sk] = len(sites)
            sites.append({"place": sk[1], "address": address_line(*t),
                          "lat": pos[0] if pos else None, "lng": pos[1] if pos else None})
        return site_index[sk]

    precincts = {}
    for k in sorted(joined):
        precincts[k] = site_for(k, joined[k])
    carved_out = {}
    for k, r, where in sorted(carved, key=lambda c: c[0]):
        carved_out.setdefault(k, []).append({
            "precinct": " ".join(r["precinct_name"].split()),
            "where": where,
            "site": site_for(k, r),
        })

    for k, a, pos in rejected:
        print("NO PIN: %s %s: the geocoder put it at %s, more than %d m outside the county"
              % (k, a, pos, COUNTY_SLACK_M))
    placed = sum(1 for s in sites if s["lat"] is not None)
    if placed < MIN_PLACED_FRACTION * len(sites):
        fail("only %d of %d buildings placed on the map" % (placed, len(sites)))

    out = {
        "election": election,
        "electionDate": ELECTION_DATE,
        "listDate": modified,
        "sourceUrl": LIST_URL,
        "crosswalkUrl": VIP_URL,
        "lookupUrl": LOOKUP_URL,
        "sites": sites,
        "precincts": precincts,
        "carvedOut": carved_out,
    }
    # A day on which the Board rewrote the file with the same content keeps
    # the shipped date, so an unchanged list changes nothing here.
    if old is not None:
        same = {k: v for k, v in old.items() if k != "listDate"} == {k: v for k, v in out.items() if k != "listDate"}
        if same:
            out["listDate"] = old["listDate"]
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d precincts (+%d drawn later), %d buildings (%d placed, %d reused, %d newly "
          "geocoded); %s on %s, list dated %s"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(precincts), len(carved), len(sites), placed,
             len(reused), len(fresh), election, ELECTION_DATE, out["listDate"]))


def check():
    """Offline: the shipped file names a site for every precinct the map draws."""
    d = json.load(open(OUT_PATH, encoding="utf-8"))
    keys = {v[0] for v in map_keys().values()}
    if set(d["precincts"]) != keys:
        fail("the polling list and the precinct map disagree: %d only in the list, %d only on the map"
             % (len(set(d["precincts"]) - keys), len(keys - set(d["precincts"]))))
    n = len(d["sites"])
    for k, i in d["precincts"].items():
        if not isinstance(i, int) or not 0 <= i < n:
            fail("precinct %s points at site %r" % (k, i))
    for k, extra in d["carvedOut"].items():
        if k not in keys:
            fail("carvedOut names %s, not a precinct on the map" % k)
        for e in extra:
            if not 0 <= e["site"] < n:
                fail("carvedOut %s points at site %r" % (k, e["site"]))
    for s in d["sites"]:
        if not s["place"] or not s["address"]:
            fail("a site with no name or address: %r" % s)
    if d["electionDate"] != ELECTION_DATE:
        fail("shipped file is for %s, this build for %s" % (d["electionDate"], ELECTION_DATE))
    print("OK nc-polling-places.json: %d precincts, %d buildings (%d placed), list dated %s"
          % (len(d["precincts"]), n, sum(1 for s in d["sites"] if s["lat"] is not None), d["listDate"]))


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        check()
    else:
        build()
