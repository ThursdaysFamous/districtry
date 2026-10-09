#!/usr/bin/env python3
"""
Build Kentucky's city officials — `data/app/ky-city-officials.json`
===================================================================

Turns `ky_city_officials_scraper.py`'s read of the Department for Local
Government's municipal directory into the roster the City card reads, keyed by
the Census place id the card's TIGERweb feature carries:

    {"2158620": {"name": "Owensboro", "govType": "City Manager",
                 "seats": [{"name": "Thomas H. Watson", "title": "Mayor",
                            "phone": "...", "email": "..."}, ...],
                 "hall": {"address": "...", "phone": "..."},
                 "sourceUrl": "https://kydlgweb.ky.gov/Cities/16_CityView.cfm?City_ID=316",
                 "read": "2026-10-09"}}

WHO IS THE GOVERNING BODY. The directory's officials table mixes the elected
body with staff, under a closed set of titles (measured 2026-10-09 over all 476
entries: 22 distinct titles). Three of them are the elected body under the
plans KRS 83A.030 allows — `Mayor`, `City Council` (the mayor-council plan's
legislative body) and `City Commission` (the commission and city-manager
plans'). Everything else is an appointed officer and is left out. A title the
table below does not know FAILS the build, so a new elected title cannot be
dropped quietly.

THE JOIN IS BY NAME, CHECKED BY COUNTY. The directory does not print a Census
id, so each entry is joined to TIGERweb's incorporated places by name, which is
unique among Kentucky's 415 places (measured 2026-10-09). Three names differ
between the two publishers and are stated in ALIASES rather than fuzzed. The
place list is saved in `data/source/ky-places.json` so `--check` needs no
network; `--refresh-places` re-reads it. Every joined place's interior point is
then tested against the shipped county fabric, and a city whose point is not in
the county the directory names is PRINTED — a city can straddle a county line,
so that is a question and not a failure.

LOUISVILLE IS TWO CENSUS PLACES AND ONE GOVERNMENT. The Census carries the
consolidated "Louisville/Jefferson County metro government (balance)" and the
pre-merger "Louisville city" inside it; both are governed by the Metro Council
since 2003, so the directory's one Louisville entry answers both ids.

NAMES ARE PRINTED AS THE STATE PUBLISHES THEM, with one exception class:
NAME_FIXES corrects a spelling only where the SAME RECORD witnesses the
correction (the Louisville mayor's surname is published "Greenbereg" beside the
e-mail address craig.greenberg@louisvilleky.gov). Each fix fails the build once
the directory stops printing the misspelling, so it cannot outlive the typo.

A ROW WITH A TITLE AND NO NAME is a seat the directory lists without saying who
holds it (Lexington's District 3 on 2026-10-09). It is counted as
`unnamedSeats`, never filled from somewhere else and never called a vacancy —
the directory has not said the seat is empty.

HOW CURRENT IT IS, MEASURED 2026-10-09 against the cities' own pages, read with
this project's own client after each host's robots.txt: Owensboro (5 of 5
names), Richmond (5 of 5), Paducah (5 of 5) and Lexington (14 of 14 named
council seats; the fifteenth is the unnamed row, and the city prints Tom Eblen
for District 3) all agree. Louisville's own council page refused this client
(HTTP 403) and was not read another way. The directory prints no "as of" date,
so the card prints the date it was read and names the publisher.

Usage:
    python3 ky/scripts/build_ky_city_officials.py                    # build
    python3 ky/scripts/build_ky_city_officials.py --refresh-places   # re-read TIGERweb first
    python3 ky/scripts/build_ky_city_officials.py --check            # offline drift gate
    python3 ky/scripts/build_ky_city_officials.py --selftest         # offline
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)

SCRAPE = os.path.join(INSTANCE, "data", "source", "ky-city-officials-scrape.json")
PLACES = os.path.join(INSTANCE, "data", "source", "ky-places.json")
COUNTIES = os.path.join(INSTANCE, "data", "app", "state-counties.json")
OUT = os.path.join(INSTANCE, "data", "app", "ky-city-officials.json")

PLACES_URL = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
              "Places_CouSub_ConCity_SubMCD/MapServer/4/query")

GOVERNING = ("Mayor", "City Council", "City Commission")
STAFF = {
    "City Clerk", "City Attorney", "City Treasurer", "Fire Chief",
    "Police Chief", "Public Works Director", "Public works Director",
    "Finance Director", "Planning and Zoning Administrator",
    "Planning & Zoning Administrator", "City Manager", "City Administrator",
    "Human Resource Director", "Human Resources Director",
    "Information Technology Manager", "Public Relations/Communications Officer",
    "PR & Communications Officer", "Risk Manager",
}

# Directory name -> the Census place ids it answers. Stated, not fuzzed.
ALIASES = {
    "Lexington": ["2146027"],      # Census: Lexington-Fayette urban county
    "Louisville": ["2148006", "2148000"],  # metro government (balance) + Louisville city
    "Middlesboro": ["2151924"],    # Census spells it Middlesborough
}

# (directory City_ID, surname as published) -> (corrected surname, witness)
NAME_FIXES = {
    ("248", "Greenbereg"): ("Greenberg", "craig.greenberg@louisvilleky.gov"),
}

# Plans the directory marks a city as no longer governing under, or entries that
# are not cities at all (an unincorporated county or a census-designated place
# the directory keeps for its own mailing purposes).
NOT_A_CITY = re.compile(r"\((UNINC)\)$|\bCDP$|^Z_")
GONE = {"Dissolved"}

# Floors, measured 2026-10-09: 410 of 415 Census places joined, 408 of them
# naming a governing body. The 17 units over 25,000 are an identity, checked
# separately below.
MIN_PLACES = 400
MIN_NAMED = 395
MIN_SEATS = 2300


def norm(s):
    return re.sub(r"[^a-z]", "", s.lower().replace("saint", "st"))


def fetch_places():
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import requests
    import scraper_common as sc
    sc.require_robots_once(PLACES_URL, sc.UA_ROSTER_BOT, headers=sc.UA_HEADERS_ROSTER_BOT)
    r = requests.get(PLACES_URL, params={
        "where": "STATE='21'", "outFields": "GEOID,NAME,BASENAME,INTPTLAT,INTPTLON",
        "returnGeometry": "false", "orderByFields": "GEOID", "f": "json"},
        headers=sc.UA_HEADERS_ROSTER_BOT, timeout=60)
    r.raise_for_status()
    doc = r.json()
    if "error" in doc:
        raise SystemExit("FAIL: TIGERweb answered an error: %r" % doc["error"])
    rows = [{"geoid": f["attributes"]["GEOID"], "name": f["attributes"]["NAME"],
             "basename": f["attributes"]["BASENAME"],
             "lat": float(f["attributes"]["INTPTLAT"]),
             "lng": float(f["attributes"]["INTPTLON"])} for f in doc["features"]]
    if len(rows) < MIN_PLACES:
        raise SystemExit("FAIL: TIGERweb returned %d Kentucky places, floor %d"
                         % (len(rows), MIN_PLACES))
    return rows


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def county_at(features, lng, lat):
    for f in features:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            if sum(_in_ring(lng, lat, r) for r in poly) % 2:
                return f["properties"].get("BASENAME") or f["properties"].get("NAME")
    return None


def fix_name(cid, official):
    last = official.get("last", "")
    fix = NAME_FIXES.get((cid, last))
    if fix:
        if fix[1].lower() != (official.get("email") or "").lower():
            raise SystemExit("FAIL: NAME_FIXES corrects %s %r on City_ID %s and the "
                             "record no longer carries its witness %s"
                             % (official.get("first"), last, cid, fix[1]))
        last = fix[0]
    return " ".join(p for p in (official.get("first", "").strip(), last.strip()) if p)


def build(scrape, places, counties):
    read = scrape["source"]["read"]
    by_name = {}
    for p in places:
        key = norm(p["basename"])
        if key in by_name:
            raise SystemExit("FAIL: two Kentucky places share the name %r; the "
                             "join by name needs a county now" % p["basename"])
        by_name[key] = p
    by_geoid = {p["geoid"]: p for p in places}

    out = {}
    used_fixes = set()
    unknown_titles = set()
    county_notes = []
    for cid, c in sorted(scrape["cities"].items(), key=lambda kv: int(kv[0])):
        name = c.get("name", "")
        if NOT_A_CITY.search(name) or c.get("govType") in GONE:
            continue
        if name in ALIASES:
            ids = ALIASES[name]
        elif norm(name) in by_name:
            ids = [by_name[norm(name)]["geoid"]]
        else:
            raise SystemExit("FAIL: directory city %r (City_ID %s) joins no Census "
                             "place; add it to ALIASES if the two publishers spell "
                             "it differently" % (name, cid))
        seats, unnamed = [], 0
        for o in c.get("officials", []):
            title = o.get("title", "")
            if title not in GOVERNING:
                if title not in STAFF and (o.get("first") or o.get("last")):
                    unknown_titles.add(title)
                continue
            if (cid, o.get("last", "")) in NAME_FIXES:
                used_fixes.add((cid, o.get("last", "")))
            full = fix_name(cid, o)
            if not full:
                unnamed += 1
                continue
            seat = {"name": full, "title": title}
            if o.get("phone"):
                seat["phone"] = o["phone"]
            if o.get("email"):
                seat["email"] = o["email"]
            seats.append(seat)
        if not seats:
            continue
        # Mayor first, then the body in the order the directory prints it.
        seats.sort(key=lambda s: 0 if s["title"] == "Mayor" else 1)
        rec = {"name": name, "seats": seats, "sourceUrl": c["sourceUrl"],
               "read": read}
        if c.get("govType"):
            rec["govType"] = c["govType"]
        if unnamed:
            rec["unnamedSeats"] = unnamed
        hall = {k: c[k] for k in ("address", "phone") if c.get(k)}
        if hall.get("address"):
            tail = ", ".join(x for x in (c.get("mailCity"), "KY " + c["zip"] if c.get("zip") else None) if x)
            if tail:
                hall["address"] = hall["address"] + ", " + tail
        if hall:
            rec["hall"] = hall
        for gid in ids:
            if gid not in by_geoid:
                raise SystemExit("FAIL: ALIASES sends %r to %s, which is not a "
                                 "Kentucky place" % (name, gid))
            if gid in out:
                raise SystemExit("FAIL: Census place %s is answered by two "
                                 "directory entries (%s and %s)"
                                 % (gid, out[gid]["name"], name))
            p = by_geoid[gid]
            got = county_at(counties, p["lng"], p["lat"])
            if counties and c.get("county") and got and got != c["county"]:
                county_notes.append("%s: directory says %s County, the Census "
                                    "place's interior point is in %s"
                                    % (name, c["county"], got))
            out[gid] = rec
    if unknown_titles:
        raise SystemExit("FAIL: the directory prints title(s) this builder does "
                         "not classify: %s. Add each to GOVERNING or STAFF."
                         % sorted(unknown_titles))
    stale = set(NAME_FIXES) - used_fixes
    if stale:
        raise SystemExit("FAIL: NAME_FIXES entries match nothing the directory "
                         "prints now, so the typo is gone: %s" % sorted(stale))
    return out, county_notes


def check_big_units(out):
    path = os.path.join(REPO, "docs", "expected-governments.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        units = json.load(fh).get("units", {}).get("ky", [])
    missing = [u["name"] for u in units if u["geoid"] not in out]
    if missing:
        raise SystemExit("FAIL: %d of Kentucky's %d units over the floor name no "
                         "governing body: %s" % (len(missing), len(units), missing))
    print("build-ky-city-officials: all %d units over 25,000 named" % len(units))


def gate(out):
    named = len(out)
    seats = sum(len(r["seats"]) for r in out.values())
    if named < MIN_NAMED or seats < MIN_SEATS:
        raise SystemExit("FAIL: %d places and %d seats, floors %d and %d"
                         % (named, seats, MIN_NAMED, MIN_SEATS))
    check_big_units(out)
    return named, seats


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def render(out):
    return json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def selftest():
    places = [{"geoid": "2158620", "name": "Owensboro city", "basename": "Owensboro",
               "lat": 37.7, "lng": -87.1},
              {"geoid": "2148006", "name": "Louisville/Jefferson County metro government (balance)",
               "basename": "Louisville/Jefferson County metro government (balance)",
               "lat": 38.1, "lng": -85.6},
              {"geoid": "2148000", "name": "Louisville city", "basename": "Louisville",
               "lat": 38.2, "lng": -85.7}]
    scrape = {"source": {"read": "2026-10-09"}, "cities": {
        "316": {"name": "Owensboro", "govType": "City Manager", "address": "101 E 4th St",
                "mailCity": "Owensboro", "zip": "42303", "phone": "(270) 687-8565",
                "sourceUrl": "u316", "officials": [
                    {"first": "Bob", "last": "Glenn", "title": "City Commission"},
                    {"first": "Thomas H.", "last": "Watson", "title": "Mayor"},
                    {"first": "", "last": "", "title": "City Commission"},
                    {"first": "Ann", "last": "Clerk", "title": "City Clerk"}]},
        "248": {"name": "Louisville", "govType": "Metro", "sourceUrl": "u248",
                "officials": [{"first": "Craig", "last": "Greenbereg", "title": "Mayor",
                               "email": "craig.greenberg@louisvilleky.gov"}]},
        "34": {"name": "Boone County (UNINC)", "officials": []},
        "29": {"name": "Blackey", "govType": "Dissolved", "officials": [
            {"first": "X", "last": "Y", "title": "Mayor"}]},
    }}
    out, _ = build(scrape, places, [])
    o = out["2158620"]
    assert [s["name"] for s in o["seats"]] == ["Thomas H. Watson", "Bob Glenn"], o
    assert o["unnamedSeats"] == 1 and o["hall"]["address"] == "101 E 4th St, Owensboro, KY 42303", o
    assert out["2148006"] is out["2148000"]
    assert out["2148000"]["seats"][0]["name"] == "Craig Greenberg"
    assert len(out) == 3
    bad = json.loads(json.dumps(scrape))
    bad["cities"]["248"]["officials"][0]["email"] = "someone@else.gov"
    try:
        build(bad, places, [])
        raise AssertionError("a fix without its witness must fail")
    except SystemExit:
        pass
    bad = json.loads(json.dumps(scrape))
    bad["cities"]["316"]["officials"].append({"first": "A", "last": "B", "title": "Vice Mayor"})
    try:
        build(bad, places, [])
        raise AssertionError("an unknown title must fail")
    except SystemExit:
        pass
    print("build_ky_city_officials selftest: ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--refresh-places", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if args.refresh_places:
        places = fetch_places()
        with open(PLACES, "w", encoding="utf-8") as fh:
            json.dump(places, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    places = load(PLACES)
    counties = load(COUNTIES)["features"]
    out, notes = build(load(SCRAPE), places, counties)
    named, seats = gate(out)
    for n in notes:
        print("build-ky-city-officials: note — " + n)
    text = render(out)
    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            if fh.read() != text:
                raise SystemExit("FAIL: %s is not what the scrape builds; run "
                                 "python3 ky/scripts/build_ky_city_officials.py"
                                 % os.path.relpath(OUT, REPO))
        print("build-ky-city-officials: OK — %d places, %d seats" % (named, seats))
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-ky-city-officials: wrote %s — %d places, %d seats"
          % (os.path.relpath(OUT, REPO), named, seats))


if __name__ == "__main__":
    main()
