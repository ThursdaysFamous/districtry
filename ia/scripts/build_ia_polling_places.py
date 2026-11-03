#!/usr/bin/env python3
"""
Build ia/data/app/ia-polling-places.json: the polling place the Iowa
Secretary of State's statewide list names for each precinct on this app's
precinct map (ia/data/app/ia-precincts.json).

    python3 ia/scripts/build_ia_polling_places.py --from-xlsx FILE   # convert the office's spreadsheet to the source CSV (needs openpyxl)
    python3 ia/scripts/build_ia_polling_places.py                    # offline: join the source CSV to the map, write
    python3 ia/scripts/build_ia_polling_places.py --check            # offline: the shipped file holds together

THE SOURCE is the spreadsheet the Secretary of State's Elections Division
e-mailed in answer to Adam's letter on 2026-11-03 ("2026 General Polling
Place Assignments 10_27_2026.xlsx", from Dylan Lynch, Election Security
Manager). The office's site answers this project's robots.txt read with
HTTP 403 and publishes no statewide file, so the list cannot be fetched: a
person receives it and runs --from-xlsx, which writes SOURCE_CSV in
ia/data/source/ with the columns this builder reads. There is no weekly job
for that reason. The office's note: the "temporary" columns hold the actual
locations for this election, the list is pulled about 20 days before an
election, and a polling place can still change, even on Election Day. So
the card reads the temporary columns, names the list's date, says a place
can change, and links the office's own lookup.

THE CARD HIDES THE LIST AFTER ITS ELECTION: the file carries electionDate,
and from the day after it the app treats the list as out of date and names
no polling place, so a reader in a later year is never sent to a 2026
building.

THE JOIN IS ON THE PRECINCT'S NAME within its county (the list's Precinct
Code is a county's own short code, which the map does not carry). A name is
matched after folding case, runs of spaces, leading zeros on numbers, "TWSP"
to "TWP", apostrophes and slashes, and nothing looser. Measured 2026-11-03:
1,638 of the map's 1,659 named precincts match. Of the rest, Tama County
has re-precincted since the map was drawn (2024-01-30), Johnson County
lists CV.2 and CV.9 together, and Mills and Warren spell some names in
ways no fold here reads as the same, and Lee County's West Point row
gives no address; those cards say the list names no
polling place for the precinct rather than guess. A list row naming no
precinct on the map is printed, never forced onto one. The build fails if
fewer than MIN_LISTED_FRACTION of the map's precincts are named.

THE PIN: the list carries no positions. Where a building's address equals
(after folding commas and spaces) one in the Legislature's 2022 list, which
did carry positions, that position is reused from POSITIONS_PATH, kept only
inside the precinct's county or within COUNTY_SLACK_M of it. Any other
building ships without a position, and the app looks the address up itself
when a reader opens that card.
"""

import csv
import json
import math
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from scraper_common import make_fail  # noqa: E402

fail = make_fail("ia-polling-places")

APP_DIR = os.path.join(REPO_ROOT, "ia", "data", "app")
SRC_DIR = os.path.join(REPO_ROOT, "ia", "data", "source")
OUT_PATH = os.path.join(APP_DIR, "ia-polling-places.json")
PRECINCTS_PATH = os.path.join(APP_DIR, "ia-precincts.json")
COUNTIES_PATH = os.path.join(APP_DIR, "state-counties.json")
SOURCE_CSV = os.path.join(SRC_DIR, "ia-sos-polling-places.csv")
POSITIONS_PATH = os.path.join(SRC_DIR, "ia-lsa-polling-positions-2022.json")

LOOKUP_URL = "https://sos.iowa.gov/voters/find-my-precinctpolling-place"
# The list's own date is the one in the spreadsheet's file name as the office
# sent it ("... 10_27_2026.xlsx"); --from-xlsx writes it on every CSV row, so a
# new list carries its own date onto the card.
SOURCE_NAME = "the Iowa Secretary of State's polling-place list"

COUNTY_SLACK_M = 3000       # a polling place can sit just across a county line
MIN_LISTED_FRACTION = 0.95  # 1,638 of 1,659 (98.7%) on 2026-11-03
MIN_ROWS = 1500
CSV_FIELDS = ["electionDate", "listDate", "county", "precinctCode", "precinct", "place", "address"]


def clean(v):
    return " ".join(str(v).split()) if v is not None else ""


def fold(name):
    """The precinct-name comparison: case, spaces, leading zeros, TWSP,
    apostrophes and slashes."""
    s = clean(name).upper().replace("'", "").replace("\u2019", "").replace("/", " ")
    s = " ".join(s.split())
    s = re.sub(r"\b0+(\d)", r"\1", s)
    return s.replace("TWSP", "TWP")


def fold_address(a):
    return " ".join(clean(a).upper().replace(",", " ").split())


def excel_day(v):
    """An Excel serial date (the office's Election Date column) as ISO."""
    if hasattr(v, "date"):
        return v.date().isoformat()
    return date.fromordinal(date(1899, 12, 30).toordinal() + int(v)).isoformat()


def from_xlsx(path):
    import openpyxl
    m = re.search(r"(\d{1,2})_(\d{1,2})_(\d{4})", os.path.basename(path))
    if not m:
        fail("the file name %r carries no list date (MM_DD_YYYY)" % os.path.basename(path))
    list_date = "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    wb = openpyxl.load_workbook(path, read_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    hdr = [clean(h) for h in rows[0]]
    need = ["Election Date", "County Name", "Precinct Code", "Precinct Name",
            "Temporary Polling Place Name", "Temporary Polling Place Address"]
    for n in need:
        if n not in hdr:
            fail("the spreadsheet has no %r column (it has %s)" % (n, hdr))
    ix = {n: hdr.index(n) for n in need}
    out = []
    for r in rows[1:]:
        if not any(r):
            continue
        out.append({
            "electionDate": excel_day(r[ix["Election Date"]]),
            "listDate": list_date,
            "county": clean(r[ix["County Name"]]),
            "precinctCode": clean(r[ix["Precinct Code"]]),
            "precinct": clean(r[ix["Precinct Name"]]),
            # The office: the "temporary" columns are this election's actual locations.
            "place": clean(r[ix["Temporary Polling Place Name"]]),
            "address": clean(r[ix["Temporary Polling Place Address"]]),
        })
    if len(out) < MIN_ROWS:
        fail("the spreadsheet has %d rows, fewer than %d" % (len(out), MIN_ROWS))
    with open(SOURCE_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, lineterminator="\n")
        w.writeheader()
        for row in sorted(out, key=lambda x: (x["county"], x["precinct"])):
            w.writerow(row)
    print("wrote %s: %d rows, list dated %s" % (os.path.relpath(SOURCE_CSV, REPO_ROOT), len(out), list_date))


def read_source():
    with open(SOURCE_CSV, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < MIN_ROWS:
        fail("%s has %d rows, fewer than %d" % (SOURCE_CSV, len(rows), MIN_ROWS))
    for key in ("electionDate", "listDate"):
        vals = {r[key] for r in rows}
        if len(vals) != 1:
            fail("the source list carries %d different %s values: %s" % (len(vals), key, sorted(vals)))
    return rows, rows[0]["electionDate"], rows[0]["listDate"]


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


def build():
    rows, election_date, list_date = read_source()
    positions = json.load(open(POSITIONS_PATH, encoding="utf-8"))["positions"]
    pos_by = {fold_address(a): p for a, p in positions.items()}
    mp = map_precincts()
    all_keys = {k for keys in mp.values() for k, _ in keys}
    county_of = {k: g for keys in mp.values() for k, g in keys}
    counties = county_polygons()

    joined, stray = {}, []
    for r in rows:
        if not r["place"] or not r["address"]:
            stray.append((r["county"], r["precinct"], "no polling place or address"))
            continue
        hits = mp.get((r["county"].upper(), fold(r["precinct"])))
        if not hits:
            stray.append((r["county"], r["precinct"], "no precinct of that name on the map"))
            continue
        for key, _ in hits:
            if key in joined and (joined[key]["place"], joined[key]["address"]) != (r["place"], r["address"]):
                fail("the list names two polling places for map precinct %s" % key)
            joined[key] = r
    if len(joined) < MIN_LISTED_FRACTION * len(all_keys):
        fail("the list names a polling place for only %d of the map's %d precincts" % (len(joined), len(all_keys)))

    site_index, sites, rejected = {}, [], []
    precincts = {}
    for key in sorted(joined):
        r = joined[key]
        sk = (r["place"], r["address"])
        if sk not in site_index:
            pos = pos_by.get(fold_address(r["address"]))
            if pos:
                polys = counties[county_of[key]]
                if not inside(pos[0], pos[1], polys) and distance_m(pos[0], pos[1], polys) > COUNTY_SLACK_M:
                    rejected.append((key, r["address"], pos))
                    pos = None
            site_index[sk] = len(sites)
            sites.append({"place": sk[0], "address": sk[1],
                          "lat": pos[0] if pos else None, "lng": pos[1] if pos else None})
        precincts[key] = site_index[sk]

    for c, p, why in stray:
        print("NOT JOINED: %s %r: %s" % (c, p, why))
    for k, a, pos in rejected:
        print("NO PIN: %s %s: the 2022 position %s is more than %d m outside the county"
              % (k, a, pos, COUNTY_SLACK_M))

    out = {
        "source": SOURCE_NAME,
        "listDate": list_date,
        "electionDate": election_date,
        "lookupUrl": LOOKUP_URL,
        "sites": sites,
        "precincts": precincts,
        "unlisted": len(all_keys - set(precincts)),
    }
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    print("wrote %s: %d of %d precincts named (%d not), %d buildings (%d placed), "
          "%d list rows not joined; list dated %s for the election of %s"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(precincts), len(all_keys), out["unlisted"],
             len(sites), sum(1 for s in sites if s["lat"] is not None), len(stray), list_date, election_date))


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
    for k in ("listDate", "electionDate"):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d.get(k))):
            fail("%s %r is not a date" % (k, d.get(k)))
    print("OK ia-polling-places.json: %d of %d precincts named, %d buildings (%d placed), list dated %s for the election of %s"
          % (len(listed), len(keys), n, sum(1 for s in d["sites"] if s["lat"] is not None), d["listDate"], d["electionDate"]))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--check" in args:
        check()
    elif "--from-xlsx" in args:
        i = args.index("--from-xlsx")
        if i + 1 >= len(args):
            fail("--from-xlsx needs the spreadsheet's path")
        from_xlsx(args[i + 1])
    else:
        build()
