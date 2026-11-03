#!/usr/bin/env python3
"""
Build il/data/app/rock-island-vote-centers.json from the Rock Island County
Clerk's own Vote Centers list.

ROCK ISLAND VOTES AT VOTE CENTERS. The county consolidated its 120 precincts
into 36 Election Day vote centers, and the Clerk publishes one PDF naming each
center, its address and the precincts it serves ("Vote Centers (PDF)" on
rockislandcountyil.gov/247/Elections). The county's own pages call it the
voter's "home Vote Center" (same-day registration "occurs on the day of the
Election at the voter's home Vote Center"), so each precinct is ASSIGNED one
center and the card says which. Nothing here claims a voter may use any
center, because no county page says so (measured 2026-11-03, Election Day,
on Adam's "Look into Rock Island County polling locations").

THE JOIN IS AN ENUMERATED ABBREVIATION TABLE, not a fuzzy match. The PDF
writes "HAMP 3, 4, 7 & 13" and "SM 8 & 24 & MOL 5" where the county GIS
precinct layer the map draws (Other_Layers/FeatureServer/3, field NAME)
writes "HAMPTON 3" and "SOUTH MOLINE 8". PREFIXES maps each abbreviation, a
bare number takes the prefix before it, and the build fails on an
abbreviation it does not know, on a precinct the list assigns twice, and
unless the list covers the GIS layer's precincts EXACTLY, so a
re-precincting or a renamed center turns the job red rather than shipping a
blank or a wrong row on the one card where that sends a resident to the
wrong building.

THE PDF IS READ BY LAYOUT (pdfplumber), because pypdf flattens each row with
its center number at the END of the line, after the ZIP code, and wraps a
long address onto the next line; the layout read keeps one row per line,
number first, exactly as printed.

THE COUNTY SITE RESETS CONNECTIONS, measured 2026-11-03: three of four reads
of the PDF were reset by the peer before one answered, and two of the site's
pages the same, so every fetch here tries up to six times with a growing
pause. The host has no robots.txt (allow all), read first with the client
that crawls.

POSITIONS come from the Census Bureau's batch geocoder, as Kentucky's do. The
list writes some addresses as "800 - 17 St." (800 17th Street) and "115 - W
- 12 Ave."; the dashes are dropped before the address is sent, and the card
prints the address as the Clerk wrote it. A center the Census cannot place
ships with its address and no position, and the app looks the address up
itself when the card opens.

WEEKLY (.github/workflows/update-rock-island-vote-centers.yml), on Henry's
model: the shipped file keeps its fetch date when nothing moved, so the job
opens a PR only when a center or an assignment changed.

Usage:
    python3 scripts/build_rock_island_vote_centers.py            # fetch + write
    python3 scripts/build_rock_island_vote_centers.py --check    # fetch + compare, writes nothing
"""

import csv
import datetime
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,  # noqa: E402
                            require_robots_once)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "rock-island-vote-centers.json")

LIST_URL = "https://rockislandcountyil.gov/DocumentCenter/View/520/Voting-Centers-PDF"
CLERK_PAGE = "https://rockislandcountyil.gov/247/Elections"
# The Clerk's own "Find Your Voting Center" link, as the Elections page prints it.
LOOKUP_URL = ("https://ova.elections.il.gov/PollingPlaceLookup.aspx"
              "?Name=mmDgPiKx8aN9qemsCi1TOBk6iTw%2fA%2fJFYRiTSnf%2bltwWOcPGp74he9KC")
PRECINCT_URL = ("https://services9.arcgis.com/6FnscPPlUa9DXXOk/arcgis/rest/services/"
                "Other_Layers/FeatureServer/3/query?where=1%3D1&outFields=NAME"
                "&returnGeometry=false&f=json")
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"

EXPECTED_CENTERS = 36   # 2026-11-03
MIN_PRECINCTS = 100     # 120 on 2026-11-03; the list and the layer must still agree exactly

# The list's abbreviation -> the GIS layer's township/city name (NAME is
# "<this> <number>" for a numbered precinct and "<this>" alone otherwise).
PREFIXES = {
    "CORD": "CORDOVA", "COE": "COE", "PT BYR": "PORT BYRON", "CAN CRK": "CANOE CREEK",
    "ZUMA": "ZUMA", "HAMP": "HAMPTON", "SM": "SOUTH MOLINE", "MOL": "MOLINE",
    "RI": "ROCK ISLAND", "SRI": "SOUTH ROCK ISLAND", "BH": "BLACKHAWK", "CV": "COAL VALLEY",
    "BOWL": "BOWLING", "RURAL": "RURAL", "ANDALUSIA": "ANDALUSIA", "EDG": "EDGINGTON",
    "BU PR": "BUFFALO PRAIRIE", "DRURY": "DRURY",
}

fail = make_fail("rock-island-vote-centers")


def fetch(url, tries=6):
    """GET with the roster client, after the host's robots.txt, retried on a reset."""
    import requests
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA_HEADERS_ROSTER_BOT, timeout=120)
            if r.status_code != 200:
                fail("HTTP %s from %s" % (r.status_code, url))
            return r
        except requests.exceptions.ConnectionError as e:
            last = e
            time.sleep(3 * (i + 1))
    fail("%s did not answer in %d tries: %s" % (url, tries, last))


def clean(v):
    return " ".join(str(v or "").split())


def layout_text(pdf_bytes):
    try:
        import pdfplumber
    except ImportError:
        fail("pdfplumber is required (pip install -c scripts/requirements.txt pdfplumber)")
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text(layout=True) or "" for page in pdf.pages)


ROW = re.compile(r"^\s*(\d{2})\s{2,}(\S.*?)\s{2,}(\S.*?)\s*$")


def precinct_names(text):
    """'HAMP 3, 4, 7 & 13' -> ['HAMPTON 3', 'HAMPTON 4', 'HAMPTON 7', 'HAMPTON 13']."""
    out = []
    prefix = None
    for raw in re.split(r"[,&]", text):
        tok = clean(raw)
        if not tok:
            continue
        m = re.match(r"^([A-Z][A-Z ]*?[A-Z])\s*(\d+)?$", tok) or re.match(r"^([A-Z])\s*(\d+)?$", tok)
        if m:
            abbr, num = m.group(1), m.group(2)
            if abbr not in PREFIXES:
                fail("unknown precinct abbreviation %r in %r — add it to PREFIXES after reading the list" % (abbr, text))
            prefix = PREFIXES[abbr]
            out.append(prefix + (" " + num if num else ""))
        elif re.match(r"^\d+$", tok):
            if prefix is None:
                fail("a bare precinct number with no township before it in %r" % text)
            out.append(prefix + " " + tok)
        else:
            fail("cannot read precinct token %r in %r" % (tok, text))
    return out


def parse_list(text):
    centers = []
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        number, precincts, where = m.group(1), clean(m.group(2)), clean(m.group(3))
        if "," not in where:
            fail("center %s has no address after its name: %r" % (number, where))
        place, address = where.split(",", 1)
        centers.append({"number": number, "place": clean(place), "address": clean(address),
                        "precincts": precinct_names(precincts)})
    if len(centers) != EXPECTED_CENTERS:
        fail("read %d vote centers, expected %d — the list's layout or length changed"
             % (len(centers), EXPECTED_CENTERS))
    nums = [c["number"] for c in centers]
    if nums != ["%02d" % i for i in range(1, EXPECTED_CENTERS + 1)]:
        fail("vote centers are not numbered 01..%02d in order: %s" % (EXPECTED_CENTERS, nums))
    return centers


def layer_names():
    j = fetch(PRECINCT_URL).json()
    if "error" in j:
        fail("the county precinct layer answered an error: %s" % j["error"])
    names = [clean((f.get("attributes") or {}).get("NAME")) for f in j.get("features", [])]
    if j.get("exceededTransferLimit"):
        fail("the county precinct layer paged its answer; this builder reads one page")
    if len(names) < MIN_PRECINCTS or len(set(names)) != len(names):
        fail("the county precinct layer holds %d precinct names (%d distinct)" % (len(names), len(set(names))))
    return set(names)


def geocode_parts(address):
    """('800 17 St.', 'Silvis', '61282') from '800 - 17 St., Silvis IL 61282', or None."""
    m = re.match(r"^(.*),\s*([A-Za-z .]+?)\s+IL\s+(\d{5})$", address)
    if not m:
        return None
    street = clean(re.sub(r"\s+-\s+", " ", m.group(1)))
    return (street, clean(m.group(2)), m.group(3))


def same_number(asked, matched):
    a = asked.upper().split()
    m = matched.upper().split(",")[0].split()
    return bool(a and m and a[0] == m[0])


def geocode(parts):
    """{(street, city, zip): (lat, lng)} for the addresses the Census places."""
    import requests
    if not parts:
        return {}
    require_robots_once(GEOCODER_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    ordered = sorted(parts)
    buf = io.StringIO()
    w = csv.writer(buf)
    for i, (street, city, zipc) in enumerate(ordered):
        w.writerow([i, street, city, "IL", zipc])
    r = requests.post(GEOCODER_URL, headers=UA_HEADERS_ROSTER_BOT,
                      data={"benchmark": "Public_AR_Current"},
                      files={"addressFile": ("addresses.csv", buf.getvalue())}, timeout=600)
    if r.status_code != 200:
        fail("Census geocoder HTTP %s" % r.status_code)
    out = {}
    for row in csv.reader(io.StringIO(r.text)):
        if len(row) >= 6 and row[2] == "Match" and row[5]:
            asked = ordered[int(row[0])]
            if not same_number(asked[0], row[4]):
                print("NO PIN: %s, %s: the Census matched a different address, %s" % (asked[0], asked[1], row[4]))
                continue
            lng, lat = (float(v) for v in row[5].split(","))
            out[asked] = (round(lat, 6), round(lng, 6))
    return out


def build():
    pdf = fetch(LIST_URL)
    if not pdf.content.startswith(b"%PDF"):
        fail("the Vote Centers link did not return a PDF")
    centers = parse_list(layout_text(pdf.content))
    names = layer_names()

    assigned = {}
    for i, c in enumerate(centers):
        for p in c["precincts"]:
            if p in assigned:
                fail("precinct %s is assigned to vote centers %s and %s" % (p, centers[assigned[p]]["number"], c["number"]))
            assigned[p] = i
    missing = sorted(names - set(assigned))
    extra = sorted(set(assigned) - names)
    if missing or extra:
        fail("the list and the county precinct layer disagree — on the map and not in the list: %s; "
             "in the list and not on the map: %s" % (missing, extra))

    parts = {}
    for c in centers:
        gp = geocode_parts(c["address"])
        if gp is None:
            print("NO PIN: center %s address not in the expected form: %s" % (c["number"], c["address"]))
        else:
            parts[c["number"]] = gp
    placed = geocode(set(parts.values()))
    sites = []
    for c in centers:
        site = {"number": c["number"], "place": c["place"], "address": c["address"]}
        pos = placed.get(parts.get(c["number"]))
        if pos:
            site["lat"], site["lng"] = pos
        else:
            print("NO PIN: center %s, %s" % (c["number"], c["address"]))
        sites.append(site)
    n_placed = sum(1 for s in sites if "lat" in s)
    if n_placed < EXPECTED_CENTERS * 0.75:
        fail("the Census geocoder placed only %d of %d centers" % (n_placed, EXPECTED_CENTERS))

    payload = {
        "source": LIST_URL,
        "sourcePage": CLERK_PAGE,
        "lookupUrl": LOOKUP_URL,
        "fetched": datetime.date.today().isoformat(),
        "centers": sites,
        "precincts": {p: assigned[p] for p in sorted(assigned)},
    }
    print("rock-island-vote-centers: %d centers, %d placed, %d precincts assigned"
          % (len(sites), n_placed, len(assigned)))
    return payload


def unchanged(a, b):
    strip = lambda d: {k: v for k, v in d.items() if k != "fetched"}
    return strip(a) == strip(b)


def main():
    check = "--check" in sys.argv
    payload = build()
    shipped = json.load(open(OUT_PATH, encoding="utf-8")) if os.path.exists(OUT_PATH) else None
    if check:
        if shipped is None:
            fail("--check: %s does not exist" % os.path.relpath(OUT_PATH, REPO_ROOT))
        if not unchanged(shipped, payload):
            fail("--check: the Clerk's list no longer matches the shipped file — re-run this builder and review the diff")
        print("rock-island-vote-centers: OK — shipped file matches the Clerk's list (%d centers, %d precincts)"
              % (len(shipped["centers"]), len(shipped["precincts"])))
        return
    if shipped is not None and unchanged(shipped, payload):
        payload["fetched"] = shipped["fetched"]
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print("rock-island-vote-centers: wrote %s" % os.path.relpath(OUT_PATH, REPO_ROOT))


if __name__ == "__main__":
    main()
