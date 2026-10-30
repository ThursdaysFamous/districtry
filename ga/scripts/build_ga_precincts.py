#!/usr/bin/env python3
"""
Build ga/data/app/ga-precincts.json: Georgia's 2,724 election precincts, from
the statewide precinct map the General Assembly's reapportionment office
publishes, each carrying what the 2026 ballots say about its county's
precincts since that map was made.

    python3 ga/scripts/build_ga_precincts.py            # fetch, check, write
    python3 ga/scripts/build_ga_precincts.py --check    # offline
    python3 ga/scripts/build_ga_precincts.py --watch    # has the file changed?

The work is scripts/statewide_precincts.py, shared with seven other states;
this file says where Georgia's map is, how to read one record, what the
ballots say about each county and what to expect.

THE SOURCE IS A FILE, NOT A LAYER. The office's page,
www.legis.ga.gov/joint-office/reapportionment, reads its listing from the
General Assembly's data service through the token the page hands every
visitor (build_ga_legislature_roster.py's `api`, the route
check_ga_county_maps.py reads the county maps by). Measured 2026-10-30, the
listing names one statewide precinct map, 2024's: one zipped shapefile of
2,724 precincts in all 159 counties, whose files inside the zip are dated
7 March 2025. The builder pins that file's address, its version parameter
included, and its SHA-256, so a newer year listed, the 2024 map listed at
another address, or the same address answering different bytes each stop a
build until a person has read the new file. robots.txt for www.legis.ga.gov
is read with this builder's own client before the file is fetched.

THE MAP CHECK READ THE SAME FILE. ga/data/source/county-map-check.json, which
step 2 of the launch wrote, records the address and SHA-256 of the precinct
map its test used, and the build and --check both stop unless they are the
ones pinned here, because the ballots' verdicts below are about that map.

27 RECORDS CARRY NO COUNTY AND NO NAME. Seventeen are Fulton's precincts
split from another (SC21A, SC08L, 12E2 and the like), and ten are coded FT:
FTBEN, FTBEN1 to FTBEN4 in Chattahoochee and Muscogee, FTSTEW in Bryan and
FTPUL in Chatham. Every record's DISTRICT code is its county's three-digit
FIPS code and then the precinct's own code, which every other record's own
fields agree with, so those 27 take their county and code from it, and their
code stands for their name. The build stops unless there are exactly 27.

A NAME THAT IS ONLY A CODE. 692 records give the precinct's own code as its
name: 462 of Fulton's 480, 68 of Augusta-Richmond's and 162 in 18 other
counties. The card titles those, and the 27 above, "Precinct <code>", and
prints every other name as the county filed it, nearly always in capitals.

WHAT THE 2026 BALLOTS SAY. The map check compared each county's precincts on
the ballots of 19 May and 16 June 2026 with those on the November 2024 ballot,
which it paired with this map by name, and it reads every county's results
for every ballot or stops, so a county it records nothing for kept every
precinct name with about the same number of registered voters in each. Each
precinct carries its county's result, and its card says it:
  - `since`, in the 48 counties whose 2026 ballots list precincts that were
    not on the November 2024 ballot (`new`), leave out some that were
    (`gone`), or show a precinct whose registered voters moved by more than a
    fifth against its county's own change (`moved`), which the map check
    reads as a precinct that may have gained or lost ground without a rename
    (most kept names change by under 7%). 1,648 of the 2,724 precincts are in those
    counties, Fulton's 480 among them, and the card says the line may be out
    of date.
  - `unmatched`, in the 5 counties whose November 2024 ballot names
    precincts the check could not pair with any on this map (all 5 of Long
    County's), so the map may not show the precincts the county used then.
  - neither, in the other counties: the card says their 2026 ballots list
    the precincts this map shows.
These are said of the county, not of the one precinct, because the pairing
of a ballot's name with a map's precinct is made by name and stated only for
the county as a whole. After each election the map check is run again, and
this file is rebuilt from its new record; --check fails until it is.

THE FINGERPRINT'S MEASURE IS ACRES. The file's AREA is in square miles (its
precincts sum to 59,457, Georgia's area), which round to zero for most of
the city precincts, so the fetch adds each one's AREA in acres, rounded to a
tenth, and the fingerprint reads that.

TWELVE METRES. The shared rule draws at the smallest of 4, 8 and 12 metres
that brings the gzipped file to 2.5 MB or under. Measured 2026-10-30 with
gzip at its default level and only the fields the card reads: 2.64 MB at
8 m, over the limit, so Georgia's precincts are drawn to within 12 metres.

NAD83, AS PUBLISHED. The file is in geographic NAD83, which mapshaper's
-proj wgs84 treats as WGS84; the two differ by about a metre in Georgia, far
inside the interval the lines are drawn to.
"""

import datetime
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(os.path.dirname(INSTANCE_ROOT), "scripts"))

import statewide_precincts as sp  # noqa: E402

# The file this map is built from, as the office's listing names it, and its bytes.
LAYER = ("https://www.legis.ga.gov/api/document/docs/default-source/"
         "reapportionment-document-library/precincts/gaprec_2024-website-shapefile.zip"
         "?sfvrsn=7b38ca99_2")
SOURCE_SHA256 = "4d48e5ba8849cad20809580c3ef56c81c516ef26878a3378be83847394271a8a"
YEAR = "2024"
LISTED_RE = re.compile(r"/precincts/gaprec_(\d{4})[^/?\"]*\.zip")

# The records the file gives no county and no name, by county.
NAMELESS = {"121": 17, "215": 5, "053": 3, "051": 1, "029": 1}

MAP_CHECK = os.path.join(INSTANCE_ROOT, "data", "source", "county-map-check.json")
# The ballot the map check paired with this map: ga/scripts/check_ga_county_maps.py's
# PRECINCT_MAP_ELECTION.
MAP_BALLOT = "2024NovGen"
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")


def _county_key(name):
    # check_ga_county_maps.county_key, which names the record's counties
    return re.sub(r"[^a-z]", "", name.lower().replace(" county", ""))


def _day(iso):
    d = datetime.date.fromisoformat(iso)
    return "%d %s" % (d.day, MONTHS[d.month - 1]), d.year


def load_map_check():
    with open(MAP_CHECK, encoding="utf-8") as fh:
        return json.load(fh)


def later_ballots(record):
    """The ballots the map check compared with the map's own, in order."""
    out = sorted((e for e in record["sources"]["elections"] if e["id"] != MAP_BALLOT),
                 key=lambda e: e["date"])
    if not out:
        raise SystemExit("build_ga_precincts: FATAL: the map check compared no later ballot")
    return out


def ballots_phrase(record):
    """'the ballots of 19 May and 16 June 2026', from the map check's record."""
    days = [_day(e["date"]) for e in later_ballots(record)]
    if len({y for _, y in days}) == 1:
        parts = [d for d, _ in days]
        tail = " %d" % days[0][1]
    else:
        parts = ["%s %d" % (d, y) for d, y in days]
        tail = ""
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return "the ballot%s of %s%s" % ("s" if len(parts) > 1 else "", joined, tail)


def county_status(record, counties):
    """{county GEOID: {"since": {...}} or {"unmatched": n} or {}} from the map
    check's record, every county named, every name in the record a county."""
    by_key = {_county_key(c["name"]): geoid for geoid, c in counties.items()}
    ids = {e["id"] for e in later_ballots(record)}
    since = {}
    for label, v in record["precincts_changed_since_2024"].items():
        el, ckey = label.split(" ", 1)
        if el not in ids or ckey not in by_key:
            raise SystemExit("build_ga_precincts: FATAL: the map check records %r, which "
                             "names no later ballot or no county" % label)
        s = since.setdefault(by_key[ckey], {"new": set(), "gone": set(), "moved": set()})
        s["gone"].update(v["gone"])
        for name, why in v["changed"].items():
            s["new" if why == "new" else "moved"].add(name)
    unmatched = {}
    for label, names in record["unmatched_precinct_names"].items():
        el, ckey = label.split(" ", 1)
        if ckey not in by_key:
            raise SystemExit("build_ga_precincts: FATAL: the map check records %r, which "
                             "names no county" % label)
        if el == MAP_BALLOT:
            unmatched[by_key[ckey]] = len(names)
    out = {}
    for geoid in counties:
        st = {}
        if geoid in since:
            s = since[geoid]
            # a name that was new on one ballot and moved on a later one is new
            s["moved"] -= s["new"]
            st["since"] = {k: len(v) for k, v in s.items() if v}
        if geoid in unmatched:
            st["unmatched"] = unmatched[geoid]
        out[geoid] = st
    return out


_STATUS = {}


def status_for(geoid):
    if not _STATUS:
        counties = sp.load_counties(SPEC)
        record = load_map_check()
        pm = record["sources"]["precinct_map"]
        if pm.get("url") != LAYER or pm.get("sha256") != SOURCE_SHA256:
            sp.fail(SPEC, "the map check read %s (SHA-256 %s), not the map pinned here; run "
                    "both on the same map" % (pm.get("url"), str(pm.get("sha256"))[:12]))
        _STATUS.update(county_status(record, counties))
    return _STATUS[geoid]


_read_zip = sp.ShapefileZip()


def fetch(spec, geometry=True):
    import build_ga_legislature_roster as legis  # noqa: PLC0415  (same instance)

    page = legis.api("Reapportionment/Page")
    listed = {}
    for url in re.findall(r"https?://[^\"\s]+", json.dumps(page)):
        m = LISTED_RE.search(url)
        if m:
            listed.setdefault(m.group(1), set()).add(url)
    if listed.get(YEAR) != {LAYER}:
        sp.fail(spec, "the office's page lists the %s precinct map as %r, not the file pinned "
                "here: read it, then point the builder at it deliberately"
                % (YEAR, sorted(listed.get(YEAR) or ())))
    newer = sorted(y for y in listed if y > YEAR)
    if newer:
        sp.fail(spec, "the office's page lists a statewide precinct map for %s: read it, run "
                "the map check on it, then point the builder at it deliberately"
                % ", ".join(newer))
    print("listing: the office's newest statewide precinct map is the %s file named" % YEAR,
          file=sys.stderr)
    records, meta = _read_zip(spec, geometry)
    if meta.get("source_sha256") != SOURCE_SHA256:
        sp.fail(spec, "the %s file's bytes changed (SHA-256 %s, pinned %s): the office "
                "replaced it in place; read it before building"
                % (YEAR, str(meta.get("source_sha256"))[:12], SOURCE_SHA256[:12]))
    nameless = {}
    for rec in records:
        p = rec["properties"]
        code = str(p.get("DISTRICT") or "").strip()
        if not str(p.get("FIPS") or "").strip():
            nameless[code[:3]] = nameless.get(code[:3], 0) + 1
            if any(str(p.get(k) or "").strip() for k in ("PRECINCT_I", "PRECINCT_N", "CTYNAME")):
                sp.fail(spec, "record %s has no county but has other fields: %r" % (code, p))
        p["ACRES"] = round(float(p["AREA"]) * 640.0, 1)
    if nameless != NAMELESS:
        sp.fail(spec, "the records with no county and no name are %r by county, expected %r"
                % (nameless, NAMELESS))
    return records, meta


def read(props):
    code = str(props.get("DISTRICT") or "").strip()
    m = re.fullmatch(r"(\d{3})(\S.*)", code)
    if not m:
        sp.fail(SPEC, "precinct code %r is not a county's three digits and a code: %r"
                % (code, props))
    county, pid = m.group(1), m.group(2)
    fips = str(props.get("FIPS") or "").strip()
    own = str(props.get("PRECINCT_I") or "").strip()
    if (fips and fips != "13" + county) or (own and own != pid):
        sp.fail(SPEC, "precinct %r disagrees with its own county %r or code %r" % (code, fips, own))
    name = " ".join(str(props.get("PRECINCT_N") or "").split()) or pid
    out = {
        "key": "13%s-%s" % (county, pid),
        "name": name,
        "code": pid,
        "countyFips": "13" + county,
    }
    out.update(status_for("13" + county))
    return out


def extra_check(feats):
    """Every precinct carries what the map check's record now says about its
    county, so a map check run again after an election fails --check until
    this file is rebuilt from it."""
    for f in feats:
        p = f["properties"]
        want = status_for(p["countyFips"])
        got = {k: p[k] for k in ("since", "unmatched") if k in p}
        if got != want:
            sp.fail(SPEC, "precinct %s carries %r and the map check says %r about %s; rebuild"
                    % (p["key"], got, want, p.get("county") or p["countyFips"]))


SPEC = sp.Spec(
    tag="ga",
    label="build_ga_precincts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/ga/)",
    out_fields="",
    expect=2724,
    expect_counties=159,
    state_bbox={"minLng": -85.61, "minLat": 30.35, "maxLng": -80.78, "maxLat": 35.01},
    read=read,
    out_file="ga-precincts.json",
    measure_field="ACRES",
    interval="12",
    fetcher=fetch,
    extra_check=extra_check,
    card_claims=("its map for 2024, whose files are dated 7 March 2025",
                 ballots_phrase(load_map_check())),
    required=("key", "name", "code", "countyFips"),
)

if __name__ == "__main__":
    sp.main(SPEC, __doc__)
