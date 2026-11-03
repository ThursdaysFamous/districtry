#!/usr/bin/env python3
"""Build il/data/app/early-voting-sites.json from the Illinois State Board of
Elections' statewide early voting list.

THE SOURCE ARRIVES BY HAND, AND THAT IS A RULE RATHER THAN A SHORTCUT. The
Board publishes every election authority's early voting, grace-period
registration and Election Day vote-center sites on one search page,
https://www.elections.il.gov/VotingAndRegistrationSystems/EarlyVotingLocationsSearch.aspx,
with a CSV download. That host's robots.txt is `User-agent: *` /
`Disallow: /` (measured 2026-09-25, re-read 2026-11-03), so nothing in this
repository fetches it: before each election a person downloads the file from
the Board's page and saves it as il/data/source/early-voting-locations-<date>.csv,
and this builder reads that. The one request it makes is to the Census
Bureau's batch geocoder, which places each site's address; the Board's host is
never contacted. Adam downloaded the first file on 2026-11-03 for the
3 November 2026 General Election.

WHAT THE FILE IS. One row per site per kind of use: the same building appears
once as a permanent early voting site, again for its weekend hours, and again
as a vote center on Election Day, each row carrying its own dates and hours
as free text in the authority's own words ("Sept 24-Nov 2", "Begins on
September 24, 2026 and concludes November 2, 2026", "6am-7pm"). The builder
groups the rows into one site per (election authority, address), keeps every
row's kind, dates, hours and notes as the Board prints them, and never
rewrites a date or an hour, because 107 authorities write them 329 ways and a
parse that got one of them wrong would send a reader to a closed door. A
Chicago address carries the ward as a segment ("1615 W Chicago Av, Ward 1,
Chicago, IL 60622"); that segment becomes the site's `ward` and leaves the
address. A name or address printed entirely in capitals is title-cased, with
the abbreviations in ACRONYMS kept; nothing else about a name is changed.

WHAT THE CARD DOES WITH IT. The app's `early-voting` layer answers the nearest
three sites anywhere in Illinois, names the election the list is for from the
metadata, and HIDES ITSELF once that election's date has passed, because a
list of sites for one election says nothing true about the next. So the file
carries `electionDate`, given on the command line and checked against the
Election Day rows (most of which print that date in some form), and the next
election's file replaces this one whole.

THE BUILDER REFUSES TO WRITE when fewer than MIN_AUTHORITIES authorities are
in the file (the Board lists all 107 — 102 counties and the five cities with
their own election commission, plus Chicago), when fewer than MIN_PLACED_SHARE
of the sites could be placed, or when fewer than MIN_DATE_AGREEMENT of the
Election Day rows name the given election date. A site the geocoder could not
place is listed in the metadata rather than dropped silently, so the gap is
visible to whoever rebuilds the file.

Usage:
  python3 scripts/build_early_voting_sites.py --election "General Election" --election-date 2026-11-03
      [--csv il/data/source/early-voting-locations-2026-11-03.csv] [--retrieved 2026-11-03]

--csv defaults to the newest early-voting-locations-*.csv under il/data/source,
and --retrieved to the date in that file's name.
"""
import argparse
import csv
import datetime
import glob
import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,  # noqa: E402
                            require_robots_once)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "early-voting-sites.json")
SOURCE_DIR = os.path.join(REPO_ROOT, "il", "data", "source")
SOURCE_URL = ("https://www.elections.il.gov/VotingAndRegistrationSystems/"
              "EarlyVotingLocationsSearch.aspx")
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"

MIN_AUTHORITIES = 100      # the Board lists 107
MIN_PLACED_SHARE = 0.85    # of sites, placed by the Census geocoder (measured 2026-11-03: 434 of 471 after the address clean-up, see geocode)
MIN_DATE_AGREEMENT = 0.8   # of Election Day rows naming --election-date

# Kept as written when a name printed in capitals is title-cased.
ACRONYMS = {"VFW", "YMCA", "YWCA", "UIC", "UIS", "UIUC", "ISU", "SIU", "SIUE", "NIU", "WIU",
            "EIU", "CSU", "NEIU", "CCC", "CPS", "CTA", "II", "III", "IV", "LLC", "AMVETS",
            "CEFCU", "IBEW", "UAW", "KC", "JCC", "HOA", "VA", "USPS", "AMC", "IL", "US", "NW", "NE", "SW", "SE"}
# A trailing segment of a street that names a room and not a road, dropped
# for the geocoder only; the address the card prints keeps it.
ROOM_WORDS = re.compile(r"^(suite|ste\.?|floor|fl\.?|room|rm\.?|unit|apt\.?|lower level|"
                        r"basement|lobby|annex|\d+(st|nd|rd|th) floor|#)", re.I)

fail = make_fail("early-voting-sites")

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
MONTHS["sept"] = 9


def ws(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def title_caps(s):
    """'ALEXANDER COUNTY CLERK'S OFFICE' -> \"Alexander County Clerk's Office\"; mixed case is left alone."""
    if not s or s != s.upper() or not re.search(r"[A-Z]", s):
        return s
    out = []
    for word in s.split(" "):
        bare = re.sub(r"[^A-Z0-9]", "", word)
        if bare in ACRONYMS:
            out.append(word)
            continue
        w = re.sub(r"[A-Za-z]+", lambda m: m.group(0).capitalize(), word)
        w = re.sub(r"'S\b", "'s", w)
        out.append(w)
    return " ".join(out)


def split_ward(address):
    """('1615 W Chicago Av, Chicago, IL 60622', '1') from Chicago's address form, else (address, None)."""
    m = re.search(r",\s*Ward\s+(\d{1,2})\s*,", address, re.I)
    if not m:
        return address, None
    return address[:m.start()] + "," + address[m.end():], m.group(1)


def clean_address(raw):
    a = ws(raw)
    a = re.sub(r"\s*,\s*", ", ", a)                 # "Chicago , IL" -> "Chicago, IL"
    a = re.sub(r"-_+\s*$", "", a)                   # "62650-____"
    a = re.sub(r"\.\s*$", "", a)                    # "62263."
    a = re.sub(r"\b[Ii][Ll]\.?(?=,?\s+\d{5})", "IL", a)  # "Galena, Il 61036", "IL. 62263"
    a = re.sub(r"\bIL IL$", "IL", a)                   # "Vandalia, IL IL" (no ZIP in the row)
    a = re.sub(r"\s+(\d{5})(-\d{4})?$", r" \1", a)  # one space before the ZIP, no +4
    a = re.sub(r"^#\s*(?=\d)", "", a)                  # "#1 Taylor St"
    a, ward = split_ward(a)
    return title_caps(a), ward


def geocode_parts(address):
    """('507 Vermont St.', 'Quincy', '62301') for the geocoder, or None when the form is not recognised."""
    m = re.match(r"^(.*),\s*([A-Za-z .'-]+?),?\s+IL(?:\s+(\d{5}))?$", address)
    if not m:
        return None
    street = m.group(1)
    # Keep the first segment of a street written with commas unless the first
    # segment names a room; "300 W State St. West State, 300 W State St." keeps
    # its first segment, which the geocoder matches or does not.
    segs = [ws(s) for s in street.split(",") if ws(s)]
    segs = [s for s in segs if not ROOM_WORDS.match(s)] or segs
    return (segs[0], ws(m.group(2)), m.group(3) or "")


def same_number(asked, matched):
    a = asked.upper().split()
    m = matched.upper().split(",")[0].split()
    return bool(a and m and a[0] == m[0])


def geocode_batch(session, ordered, benchmark):
    """[(asked, matched_address, (lat, lng)) ...] for one batch of (street, city, zip) rows; a blank
    city or ZIP is sent blank, which the Census geocoder accepts."""
    buf = io.StringIO()
    w = csv.writer(buf)
    for i, (street, city, zipc) in enumerate(ordered):
        w.writerow([i, street, city, "IL", zipc])
    r = session.post(GEOCODER_URL, headers=UA_HEADERS_ROSTER_BOT,
                     data={"benchmark": benchmark},
                     files={"addressFile": ("addresses.csv", buf.getvalue())}, timeout=900)
    if r.status_code != 200:
        fail("Census geocoder HTTP %s" % r.status_code)
    out = []
    for row in csv.reader(io.StringIO(r.text)):
        if len(row) >= 6 and row[2] == "Match" and row[5]:
            lng, lat = (float(v) for v in row[5].split(","))
            out.append((ordered[int(row[0])], row[4], (round(lat, 6), round(lng, 6))))
    return out


def geocode(parts):
    """{(street, city, zip): (lat, lng)} for the addresses the Census Bureau places.

    FOUR PASSES, AND THE LAST THREE RECOVER LITTLE, WHICH IS A MEASUREMENT.
    The batch geocoder matches an address only inside the city AND the ZIP
    code it is given, so the first retry drops the ZIP and the second the
    city; the third asks the Census 2020 benchmark, whose address ranges
    differ a little from the current one's. Measured on the 3 November 2026
    file: 412 of 471 sites placed on the first pass, 0 and 0 on the two
    retries, and 2 on the 2020 benchmark; the rest are addresses the Census
    Bureau's address ranges do not hold at all (a church on a county road, a
    university building, a township hall), and no other geocoder may be asked
    from here, because photon.komoot.io and nominatim.openstreetmap.org both
    refuse automated readers in their robots.txt (read 2026-11-03). Every pass
    keeps the house number test, so a different building never passes for the
    one asked about, and an unplaced site is listed in the metadata."""
    import requests
    if not parts:
        return {}
    require_robots_once(GEOCODER_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    session = requests.Session()
    out = {}
    pending = sorted(parts)
    for label, benchmark, form in (("city and ZIP", "Public_AR_Current", lambda p: p),
                                   ("city alone", "Public_AR_Current", lambda p: (p[0], p[1], "")),
                                   ("ZIP alone", "Public_AR_Current", lambda p: (p[0], "", p[2])),
                                   ("the Census 2020 benchmark", "Public_AR_Census2020", lambda p: p)):
        if not pending:
            break
        asked_by_sent = {}
        for p in pending:
            asked_by_sent.setdefault(form(p), p)
        placed_now = 0
        for sent, matched, pos in geocode_batch(session, sorted(asked_by_sent), benchmark):
            asked = asked_by_sent[sent]
            if not same_number(asked[0], matched):
                print("NO PIN: %s, %s: the Census matched a different address, %s" % (asked[0], asked[1], matched))
                continue
            out[asked] = pos
            placed_now += 1
        pending = [p for p in pending if p not in out]
        print("geocoder, by %s: %d placed, %d still unplaced" % (label, placed_now, len(pending)))
    return out


def names_date(text, election_date):
    """Whether a DatesOfOperation value names election_date in one of the Board's spellings."""
    t = text.lower().replace(",", " ")
    y, mo, d = election_date.year, election_date.month, election_date.day
    if re.search(r"\b%d/0?%d/%d\b" % (mo, d, y), t):
        return True
    for word, num in MONTHS.items():
        if num != mo:
            continue
        if re.search(r"\b%s\.?\s+0?%d(st|nd|rd|th)?\b(\s+%d)?" % (re.escape(word), d, y), t):
            return True
    return False


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    need = {"County", "LocationName", "LocationAddress", "LocationType",
            "DatesOfOperation", "HoursOfOperation", "Notes"}
    if not rows or not need.issubset(rows[0].keys()):
        fail("%s is not the Board's early voting download (columns %s)" % (path, sorted(rows[0].keys()) if rows else "none"))
    return rows


def build(rows, election, election_date, retrieved, source_file):
    sites = OrderedDict()
    for r in rows:
        authority = ws(r["County"])
        address, ward = clean_address(r["LocationAddress"])
        key = (authority, address.lower())
        site = sites.setdefault(key, {"authority": authority, "address": address, "ward": ward,
                                      "names": Counter(), "schedule": []})
        site["names"][title_caps(ws(r["LocationName"]))] += 1
        entry = {"kind": ws(r["LocationType"]), "dates": ws(r["DatesOfOperation"]),
                 "hours": ws(r["HoursOfOperation"])}
        if ws(r["Notes"]):
            entry["notes"] = ws(r["Notes"])
        if entry not in site["schedule"]:
            site["schedule"].append(entry)

    authorities = sorted(set(k[0] for k in sites))
    if len(authorities) < MIN_AUTHORITIES:
        fail("only %d election authorities in the file (the Board lists 107)" % len(authorities))

    ed_rows = [r for r in rows if "election day" in r["LocationType"].lower()]
    agree = sum(1 for r in ed_rows if names_date(r["DatesOfOperation"], election_date))
    if ed_rows and agree < MIN_DATE_AGREEMENT * len(ed_rows):
        fail("only %d of %d Election Day rows name %s; is --election-date right for this file?"
             % (agree, len(ed_rows), election_date.isoformat()))

    parts = {}
    for key, site in sites.items():
        gp = geocode_parts(site["address"])
        if gp is None:
            print("NO PIN: address not in the expected form: %s" % site["address"])
        else:
            parts[key] = gp
    placed = geocode(set(parts.values()))

    features, unplaced = [], []
    for key, site in sorted(sites.items(), key=lambda kv: (kv[0][0], kv[1]["names"].most_common(1)[0][0], kv[0][1])):
        name = site["names"].most_common(1)[0][0]
        props = OrderedDict([("name", name), ("address", site["address"]), ("authority", site["authority"])])
        if site["ward"]:
            props["ward"] = site["ward"]
        props["schedule"] = site["schedule"]
        props["electionDay"] = any("election day" in e["kind"].lower() for e in site["schedule"])
        pos = placed.get(parts.get(key))
        if not pos:
            print("NO PIN: %s, %s (%s)" % (name, site["address"], site["authority"]))
            unplaced.append(OrderedDict([("name", name), ("address", site["address"]), ("authority", site["authority"])]))
            continue
        features.append(OrderedDict([("type", "Feature"), ("properties", props),
                                     ("geometry", {"type": "Point", "coordinates": [pos[1], pos[0]]})]))
    if len(features) < MIN_PLACED_SHARE * len(sites):
        fail("the Census geocoder placed only %d of %d sites" % (len(features), len(sites)))

    kinds = Counter(e["kind"] for s in sites.values() for e in s["schedule"])
    metadata = OrderedDict([
        ("election", election),
        ("electionDate", election_date.isoformat()),
        ("source", "Illinois State Board of Elections"),
        ("sourceUrl", SOURCE_URL),
        ("sourceFile", os.path.basename(source_file)),
        ("retrieved", retrieved),
        ("how", "Downloaded by a person from the Board's early voting search page, whose robots.txt "
                "refuses automated readers, and built by scripts/build_early_voting_sites.py; one site "
                "per election authority and address, every row's kind, dates, hours and notes kept as "
                "the Board prints them; a name or address printed in capitals is title-cased."),
        ("coordinates", "Each site's address placed by the Census Bureau's batch geocoder; locations approximate."),
        ("rows", len(rows)),
        ("authorities", len(authorities)),
        ("sites", len(sites)),
        ("placed", len(features)),
        ("kinds", OrderedDict(sorted(kinds.items()))),
        ("unplaced", unplaced),
    ])
    print("early-voting-sites: %d rows, %d authorities, %d sites, %d placed, %d unplaced; %d of %d Election Day rows name %s"
          % (len(rows), len(authorities), len(sites), len(features), len(unplaced), agree, len(ed_rows), election_date.isoformat()))
    return OrderedDict([("type", "FeatureCollection"), ("metadata", metadata), ("features", features)])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", help="the Board's download (default: the newest under il/data/source)")
    ap.add_argument("--election", required=True, help='the election the list is for, e.g. "General Election"')
    ap.add_argument("--election-date", required=True, help="YYYY-MM-DD; the layer hides after this day")
    ap.add_argument("--retrieved", help="YYYY-MM-DD the file was downloaded (default: the date in its name)")
    args = ap.parse_args()

    path = args.csv
    if not path:
        found = sorted(glob.glob(os.path.join(SOURCE_DIR, "early-voting-locations-*.csv")))
        if not found:
            fail("no il/data/source/early-voting-locations-*.csv; download the Board's file first")
        path = found[-1]
    try:
        election_date = datetime.date.fromisoformat(args.election_date)
    except ValueError:
        fail("--election-date must be YYYY-MM-DD")
    retrieved = args.retrieved
    if not retrieved:
        m = re.search(r"(\d{4}-\d{2}-\d{2})\.csv$", os.path.basename(path))
        if not m:
            fail("name the file early-voting-locations-YYYY-MM-DD.csv or pass --retrieved")
        retrieved = m.group(1)
    datetime.date.fromisoformat(retrieved)

    payload = build(read_rows(path), ws(args.election), election_date, retrieved, path)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote %s" % os.path.relpath(OUT_PATH, REPO_ROOT))


if __name__ == "__main__":
    main()
