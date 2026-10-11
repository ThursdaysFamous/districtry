#!/usr/bin/env python3
"""
Build data/app/ok-county-commissioners.json — the names of Oklahoma's 231
county commissioners — from the State Election Board's "Roster of Oklahoma
State and County Officers".

THE SOURCE IS A DATED DOCUMENT AND THE CARD SAYS SO. The Election Board
publishes one roster after each general election, "Elected at the General
Election November 5, 2024, Including Holdover State Officials", as a PDF
(the 2024 edition's own metadata dates it 2025-03-26). Commissioners serve
staggered four-year terms, so every county's three seats appear in it,
whether or not that seat was on the 2024 ballot. A name is therefore "the
commissioner the State Election Board listed when it compiled the roster",
not a claim about who sits today, and the card says that in words and points
at the county. Two seats were listed Vacant (Oklahoma County District 1,
Okmulgee County District 1); those ship as `vacant: true` and the card says
the roster listed the seat vacant.

WHAT IS LEFT OUT ON PURPOSE. Each line reads "District 1 - Name, Party,
Town". The town is the officeholder's home town, which is where a person
lives rather than an office, so it is never written (the same ruling the
fleet made on a county board transcription, 2026-10). The county block's
closing line, "For additional county information: (580) 237-0225", is a
county telephone and is kept, per county.

NEWEST EDITION FIRST. The weekly refresh asks for this year's edition, then
each earlier year down to 2024, and builds from the first that exists, so a
new roster is picked up the week it is posted. robots.txt is read for the
host before the first fetch, with the same client that fetches.

Usage:
    python3 ok/scripts/build_ok_commissioner_roster.py              # fetch
    python3 ok/scripts/build_ok_commissioner_roster.py --pdf FILE   # offline
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)), "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_HEADERS_ROSTER_BOT,
    UA_ROSTER_BOT,
    require_robots_once,
)

INSTANCE_ROOT = os.path.dirname(_HERE)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT = "ok-county-commissioners.json"
URL_TEMPLATE = ("https://oklahoma.gov/content/dam/ok/en/elections/rosters/"
                "officer-roster-%d.pdf")
FIRST_EDITION = 2024

COUNTIES = 77
SEATS = 231
# Measured 2026-10-11 on the 2024 edition: 229 named, 2 vacant. A floor below
# that tolerates a few vacancies and catches a parse that loses names.
MIN_NAMED = 220

PARTIES = {"R": "Republican", "D": "Democratic", "L": "Libertarian", "I": "Independent"}


def fetch_newest(year=None):
    year = year or datetime.date.today().year
    for y in range(year, FIRST_EDITION - 1, -1):
        url = URL_TEMPLATE % y
        require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                            label="ok-build-ok-commissioner-roster")
        req = urllib.request.Request(url, headers=UA_HEADERS_ROSTER_BOT)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("no %d edition (404)" % y, file=sys.stderr)
                continue
            raise
        if not body.startswith(b"%PDF"):
            raise RuntimeError("%s did not return a PDF" % url)
        print("using the %d edition: %s (%d bytes)" % (y, url, len(body)), file=sys.stderr)
        return url, body
    raise RuntimeError("no roster edition found from %d down to %d" % (year, FIRST_EDITION))


def pdf_text(body):
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(body))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def county_fips():
    with open(os.path.join(APP_DATA_DIR, "state-counties.json")) as f:
        g = json.load(f)
    return {re.sub(r"[^a-z]", "", ft["properties"]["BASENAME"].lower()): ft["properties"]["GEOID"]
            for ft in g["features"]}


_NAMES = {}


def county_name(geoid):
    if not _NAMES:
        with open(os.path.join(APP_DATA_DIR, "state-counties.json")) as f:
            for ft in json.load(f)["features"]:
                _NAMES[ft["properties"]["GEOID"]] = ft["properties"]["BASENAME"]
    return _NAMES[geoid]


def parse(text):
    fips_by_name = county_fips()
    lines = [ln.strip() for ln in text.splitlines()]
    m = re.search(r"Elected at the General Election\s+([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if not m:
        raise RuntimeError("could not read the election the roster is for")
    election = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()

    seats, counties = {}, {}
    i = 0
    while i < len(lines) - 1:
        hm = re.fullmatch(r"(.+?) County", lines[i])
        if not (hm and lines[i + 1].startswith("County Seat:")):
            i += 1
            continue
        name = hm.group(1)
        key = re.sub(r"[^a-z]", "", name.lower())
        if key not in fips_by_name:
            raise RuntimeError("roster county %r is not an Oklahoma county" % name)
        fips = fips_by_name[key]
        if fips in counties:
            raise RuntimeError("county %s appears twice" % name)
        info = {"seat": lines[i + 1].split(":", 1)[1].strip()}
        j = i + 2
        found = 0
        while j < len(lines) and not (re.fullmatch(r".+? County", lines[j]) and
                                      j + 1 < len(lines) and lines[j + 1].startswith("County Seat:")):
            dm = re.fullmatch(r"District ([123])\s*[-–—]\s*(.+)", lines[j])
            if dm:
                rec = parse_holder(dm.group(2), name, dm.group(1))
                skey = fips + "-" + dm.group(1)
                if skey in seats:
                    raise RuntimeError("%s listed twice" % skey)
                seats[skey] = rec
                found += 1
            pm = re.match(r"For additional county information:\s*(\(\d{3}\)\s*\d{3}-\d{4})", lines[j])
            if pm:
                info["phone"] = pm.group(1)
            j += 1
        if found != 3:
            raise RuntimeError("%s County: %d commissioner districts read, expected 3" % (name, found))
        counties[fips] = info
        i = j
    return election, seats, counties


def parse_holder(text, county, district):
    text = text.strip()
    if text.lower() == "vacant":
        return {"vacant": True}
    parts = [p.strip() for p in text.rsplit(",", 2)]
    if len(parts) != 3 or not parts[0]:
        raise RuntimeError("%s County District %s: cannot read %r" % (county, district, text))
    name, party, _home_town = parts  # the home town is never written; see the docstring
    rec = {"name": name}
    if party:
        rec["party"] = PARTIES.get(party, party)
    return rec


def build(url, body):
    election, seats, counties = parse(pdf_text(body))
    named = sum(1 for r in seats.values() if r.get("name"))
    if len(counties) != COUNTIES or len(seats) != SEATS:
        raise RuntimeError("read %d counties and %d seats; expected %d and %d"
                           % (len(counties), len(seats), COUNTIES, SEATS))
    if named < MIN_NAMED:
        raise RuntimeError("only %d of %d seats named (floor %d)" % (named, SEATS, MIN_NAMED))
    phones = sum(1 for c in counties.values() if c.get("phone"))
    if phones < COUNTIES - 2:
        raise RuntimeError("only %d of %d counties carry their information line" % (phones, COUNTIES))
    # One record per seat, keyed "<county GEOID>-<district>" like the
    # districts file's own `key`, so the card joins on a field it already has.
    # Every record carries the edition it came from, because the date is part
    # of what the name means.
    names = {fips: info for fips, info in counties.items()}
    out = {}
    for skey, rec in sorted(seats.items()):
        fips, d = skey.split("-")
        row = {"county": county_name(fips), "district": int(d)}
        row.update(rec)
        if names[fips].get("phone"):
            row["countyPhone"] = names[fips]["phone"]
        row["election"] = election
        row["sourceUrl"] = url
        out[skey] = row
    return out, named


ALLOWED = {"county", "district", "name", "party", "vacant", "countyPhone",
           "election", "sourceUrl"}


def check():
    """The shipped file, offline: every seat present once, each either named
    or vacant, every record dated and sourced, and no field outside the ones
    the card reads -- above all no home town, which the roster prints and this
    file must never carry."""
    with open(os.path.join(APP_DATA_DIR, OUT)) as f:
        data = json.load(f)
    problems = []
    if len(data) != SEATS:
        problems.append("%d seats, expected %d" % (len(data), SEATS))
    counties = {}
    for key, rec in data.items():
        m = re.fullmatch(r"(40\d{3})-([123])", key)
        if not m:
            problems.append("bad key %r" % key)
            continue
        counties.setdefault(m.group(1), 0)
        counties[m.group(1)] += 1
        extra = set(rec) - ALLOWED
        if extra:
            problems.append("%s carries %s" % (key, sorted(extra)))
        if bool(rec.get("name")) == bool(rec.get("vacant")):
            problems.append("%s must be either named or vacant" % key)
        if rec.get("district") != int(m.group(2)) or rec.get("county") != county_name(m.group(1)):
            problems.append("%s: county or district disagrees with its key" % key)
        if not rec.get("election") or not rec.get("sourceUrl"):
            problems.append("%s carries no edition date or source" % key)
    if len(counties) != COUNTIES or any(v != 3 for v in counties.values()):
        problems.append("expected 3 seats in each of %d counties" % COUNTIES)
    named = sum(1 for r in data.values() if r.get("name"))
    if named < MIN_NAMED:
        problems.append("only %d named (floor %d)" % (named, MIN_NAMED))
    if problems:
        for p in problems[:20]:
            print("build-ok-commissioner-roster: FAIL — " + p, file=sys.stderr)
        return 1
    print("build-ok-commissioner-roster: OK — %d seats in %d counties, %d named"
          % (len(data), len(counties), named))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", help="build from a saved copy instead of fetching")
    ap.add_argument("--url", default=URL_TEMPLATE % FIRST_EDITION,
                    help="the url to record when building from --pdf")
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to the shape the card reads")
    args = ap.parse_args()
    if args.check:
        sys.exit(check())
    if args.pdf:
        with open(args.pdf, "rb") as f:
            url, body = args.url, f.read()
    else:
        url, body = fetch_newest()
    out, named = build(url, body)
    with open(os.path.join(APP_DATA_DIR, OUT), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("-> data/app/%s: %d seats in %d counties, %d named, %d vacant, election %s"
          % (OUT, SEATS, COUNTIES, named, SEATS - named, next(iter(out.values()))["election"]))


if __name__ == "__main__":
    main()
