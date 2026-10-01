#!/usr/bin/env python3
"""
Build data/app/ia-township-officers.json -- the clerk and trustees of each
Iowa civil township whose county publishes them, keyed by the TIGER county
subdivision GEOID the County Subdivision card already holds.

WHAT IT ANSWERS
----------------
The County Subdivision card drew 1,663 subdivisions and named nobody in any of
them. Iowa's civil townships are real governments -- elected clerk and three
trustees under Iowa Code ch. 359, with cemeteries and, outside the cities,
fire and emergency service -- and the card said so while telling the reader
nothing about who holds those offices. This file names 617 of them across 186
townships in twelve counties.

TWELVE OF 99, AND NOT A STEP TOWARDS A STATEWIDE FILE THAT EXISTS
-------------------------------------------------------------------
Nothing publishes Iowa's township officers statewide. The twelve counties here
are the twelve whose own sites publish them, and the card names the publisher
on every row it shows. Iowa has about 1,600 civil townships, so this is 12% of
them and `ia-township-officers` stays an open gap for the rest.

KEYED BY GEOID, WHICH MEANS THE JOIN IS CHECKED RATHER THAN ASSUMED
---------------------------------------------------------------------
The card holds the subdivision's own GEOID at query time, so that is the key,
and building it requires matching each county's printed township name to the
census fabric. The match is the Jasper test in this instance's usual form:
every township the county names must find EXACTLY ONE subdivision in that
county, and this build refuses to write if any does not. Measured 2026-10-01
the join is 186 of 186.

TWO NOTATION DIFFERENCES AND ONE REAL SPELLING DIFFERENCE, all measured:

  * `Mt.` against the census's `Mount` -- Winnebago's Mt. Valley and Cerro
    Gordo's Mt. Vernon. An abbreviation, so it is expanded for matching the
    way the fleet's other abbreviation tables do, and nothing is renamed.

  * Crawford County prints `Nishnabotna` where the census BASENAME is
    `Nishnabotny`. This is a genuine disagreement about a name rather than a
    notation, and it is NOT resolved here in either direction, because it does
    not have to be: the key is the GEOID and the card prints the census name it
    already drew. The difference is declared in ALIASES so the join is explicit
    and a future change to either spelling fails loudly instead of silently
    dropping a township.

THE CITY PLACEHOLDER RECORDS ARE NOT TOWNSHIPS, AND ONE OF THEM COLLIDES
----------------------------------------------------------------------------
Three of the twelve counties carry a subdivision record for an incorporated
city -- Harlan in Shelby, Mason City and Clear Lake in Cerro Gordo -- which the
card already explains as "the Census Bureau's placeholder subdivision record
for an incorporated city". They are not governments distinct from the city, and
no county names township officers for one.

They cannot merely be ignored, because CERRO GORDO HAS BOTH A CLEAR LAKE
TOWNSHIP AND A CLEAR LAKE CITY and the two share a BASENAME. Matching on the
basename alone made Clear Lake ambiguous and this build refused to write --
which is the gate doing its job, found on its first live run. So the join
indexes only the records the card itself calls townships: those whose NAME is
the basename followed by " township", the same suffix the card reads to
decide what kind of subdivision a reader clicked. A county's city record can
therefore never take a township's officers, and the unmatched-census-record
direction stays deliberately NOT a failure, because every one of those is a
city placeholder or a township the county does not publish.

A SOURCE THAT GOES DARK KEEPS ITS LAST-GOOD RECORD (Adam, 2026-09-19). A
county missing from a run's cache -- its site down, or its robots.txt newly
refusing us -- keeps the people it last published, with its own `asOf` stamp
left at the date it was actually read, and the run prints it as carried
forward. Deleting the officers would cost a reader the answer and gain the
county nothing.

Usage:
    python3 ia/scripts/ia_township_officers_scraper.py   # refresh the cache
    python3 ia/scripts/build_ia_township_officers.py
    python3 ia/scripts/build_ia_township_officers.py --check   # offline
"""

import datetime
import json
import os
import re
import sys
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ia/
FLEET_ROOT = os.path.dirname(REPO_ROOT)

# THE DISTRICTRY TOKEN, the same one this instance's scrapers send.
TIGER_HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)",
                 "Accept": "application/json"}
sys.path.insert(0, os.path.join(FLEET_ROOT, "scripts"))
from validate_officeholder_names import is_vacancy_marker  # noqa: E402  (one reader for the word)
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache",
                     "ia_township_officers.json")
OUT_NAME = "ia-township-officers.json"

TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query")

# FLOORS, measured 2026-10-01 against what the twelve counties publish. A floor
# rather than an equality, because a trustee leaving office moves these by ones
# and a county that stops publishing is preserved rather than dropped -- but a
# floor that no run can reach is not a guard, so each is set at the measurement
# less the ordinary drift of a seat or two.
MIN_COUNTIES = 12       # twelve of twelve answered; a county that goes dark is
                        # carried forward, so this counts carried ones too and
                        # a drop here means a county left the TABLE
MIN_TOWNSHIPS = 180     # measured 186
MIN_OFFICIALS = 590     # measured 617
MIN_PHONES = 170        # measured 181, all from the four counties that publish
                        # one at all; the other eight publish none, so a
                        # shortfall is one of those four changing shape

# Expanded on BOTH sides before matching. Notation, not a rename.
ABBREVIATIONS = (("mt", "mount"), ("st", "saint"))

# The one measured name disagreement, declared rather than normalised away.
# {(county FIPS, the county's spelling): the census BASENAME}
ALIASES = {
    ("19047", "Nishnabotna"): "Nishnabotny",
}

ROLES = ("Clerk", "Trustee")
# A PERSON'S NAME IS NEVER CORRECTED, so this pattern is written around what
# these twelve counties actually publish rather than around what a name ought
# to look like. Measured 2026-10-01, four of the 617 carry punctuation a
# tidier pattern rejects, for three different reasons:
#   * `James L, Striegel` (Keokuk, Washington) -- a comma where an initial's
#     period belongs, which is the county's own typo,
#   * `Sean O'Neill` with a curly apostrophe (Sac, Viola),
#   * `Jay Nielsen (Hans)` and `Gaylord "Joe" Gross` (Shelby) -- a nickname,
#     in parentheses and in curly quotes.
# All four ship exactly as published and every one is PRINTED on the run that
# writes them, by `unusual()` below. Dropping a person because their county
# typed a comma would cost a reader the answer; silently rewriting the comma
# would be this project editing somebody's name, which it does not do -- the
# same reasoning that made build_douglas_county_board.py drop a typo'd e-mail
# domain rather than fix a character in it.
NAME_RE = re.compile("^[A-Z][A-Za-z.,'\u2019\u201c\u201d\"()\- ]{1,59}$")
# What `unusual()` reports: anything past a plain name, an apostrophe or a
# hyphen. It changes no verdict; it puts a surprising name in front of a person.
PLAIN_NAME_RE = re.compile("^[A-Z][A-Za-z.'\u2019\-]*(?:[ \-][A-Za-z.'\u2019\-]+){0,4}$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")
GEOID_RE = re.compile(r"^19\d{8}$")
# A street address must never reach this file. Anything carrying a house number
# followed by a word, or a town-and-ZIP tail, is refused outright rather than
# stripped -- a value that can be cleaned is a value that can be forgotten.
ADDRESS_RE = re.compile(r"\b\d{2,5}\s+[A-Za-z]|\b[A-Z]{2}\s+\d{5}\b")


def norm(name):
    """A township name reduced to what two publishers can be compared on."""
    text = re.sub(r"[^a-z ]", " ", (name or "").lower())
    words = [w for w in text.split() if w]
    out = []
    for word in words:
        for short, full in ABBREVIATIONS:
            if word == short:
                word = full
        out.append(word)
    return "".join(out)


def load(path, what):
    try:
        with open(path) as fh:
            return json.load(fh)
    except OSError as exc:
        raise RuntimeError("cannot read %s (%s) -- %s" % (path, exc, what))


def fetch_subdivisions(fips):
    """{normalised basename: [attributes]} for one county, from TIGERweb."""
    sys.path.insert(0, os.path.join(FLEET_ROOT, "scripts"))
    import scraper_common as SC
    query = {"where": "STATE='19' AND COUNTY='%s'" % fips[2:],
             "outFields": "GEOID,NAME,BASENAME", "returnGeometry": "false",
             "f": "json"}
    url = TIGER_COUSUB + "?" + urllib.parse.urlencode(query)
    # THE DISTRICTRY TOKEN, NOT A BROWSER STRING. A browser string is for a
    # host that refuses the token by client fingerprint, and TIGERweb does not:
    # it is recorded `token-ok` in user-agent-measurements.json, and this exact
    # query URL was read three times with the token on 2026-10-01 (HTTP 200,
    # 1,946 bytes, 18 features, no `error` member). A browser string reached
    # this line by being copied from a sibling rather than by being measured,
    # which is how the fleet comes to send one to seventy hosts that never
    # asked for it.
    payload = json.loads(SC.fetch_stdlib(url, headers=TIGER_HEADERS))
    # AN API ERROR IS NOT AN EMPTY ANSWER. `.get("features", [])` on an error
    # object reads as "this county has no subdivisions", which is a confident
    # wrong answer assembled out of a failure -- the reading this repository
    # already records paying for once on TIGER's own subdivision layer.
    if "error" in payload:
        raise RuntimeError("TIGERweb refused county %s: %s"
                           % (fips, payload["error"]))
    index = {}
    for feature in payload.get("features") or []:
        attrs = feature["attributes"]
        # TOWNSHIPS ONLY -- see the Clear Lake note above. The suffix is read
        # off NAME rather than LSADC because that is what the card itself uses
        # to tell a reader which kind of subdivision they clicked, so the two
        # surfaces cannot come to disagree about what a township is.
        name, base = attrs.get("NAME") or "", attrs.get("BASENAME") or ""
        if name.strip().lower() != (base + " township").strip().lower():
            continue
        index.setdefault(norm(base), []).append(attrs)
    if not index:
        raise RuntimeError("TIGERweb returned no subdivisions for county %s" % fips)
    return index


def unusual(name):
    """Does this published name carry punctuation worth a reader's eye?"""
    return not PLAIN_NAME_RE.match(name or "")


def clean_officials(county, township, officials, flagged=None):
    """Officials fit to ship, or a refusal naming what was wrong."""
    rows = []
    for official in officials:
        name, role = official.get("name"), official.get("role")
        if role not in ROLES:
            raise RuntimeError(
                "%s County, %s township: %r holds %r, and this file ships only "
                "%s. An office nobody measured is a page to read."
                % (county, township, name, role, " and ".join(ROLES)))
        # A SEAT THE COUNTY SAYS IS EMPTY, which is a fact about the seat and
        # not a person. The scraper converts the county's own word for it
        # (`is_vacancy_marker`, one reader for the list) into this shape
        # BEFORE it can reach a roster, so the row carries a role and no
        # name. It ships, because dropping it would make a four-seat township
        # read as a three-seat one -- the county is naming a seat that exists
        # and saying nobody holds it. A row carrying both is a parse that went
        # wrong rather than a publisher saying something subtle, so it stops
        # the build.
        # THE CONVERSION IS ASKED FOR AGAIN HERE, AND NOT BECAUSE THE SCRAPER
        # IS DISTRUSTED. The scraper writes a cache that outlives it, so a
        # cache taken before the scraper learned the word would otherwise ship
        # a township officer called Vacant through this builder -- which is
        # the file a reader actually downloads. Both call ONE reader for the
        # word list (scripts/validate_officeholder_names.py), so the two can
        # never come to disagree about which words mean an empty seat; what
        # is duplicated is where the question is asked, not the answer.
        vacant = bool(official.get("vacant")) or is_vacancy_marker(name)
        if vacant and is_vacancy_marker(name):
            name = None
        if vacant:
            if name:
                raise RuntimeError(
                    "%s County, %s township: a %s row is marked vacant and "
                    "also carries the name %r. One of the two is wrong, and "
                    "guessing which would either invent an officer or hide one."
                    % (county, township, role, name))
            row = {"role": role, "vacant": True}
        elif not name or not NAME_RE.match(name) or re.search(r"\d", name):
            raise RuntimeError("%s County, %s township: %r is not a name"
                               % (county, township, name))
        else:
            if flagged is not None and unusual(name):
                flagged.append("%s County, %s township: %s"
                               % (county, township, name))
            row = {"name": name, "role": role}
        # The term fields describe the SEAT and so are kept on a vacant row
        # too: a county saying this trustee's term ends in 2026 is telling a
        # reader when the empty seat is next filled. A phone on a vacant row
        # is a different matter and the loop below carries it if the county
        # publishes one, because it would be the seat's line rather than
        # anybody's -- none of the twelve counties does today.
        for field in ("phone", "termEnds", "termLength"):
            value = (official.get(field) or "").strip()
            if not value:
                continue
            if ADDRESS_RE.search(value):
                raise RuntimeError(
                    "%s County, %s township: %s's %s is %r, which reads as a "
                    "street address. These pages publish officers' HOME "
                    "addresses and this file never carries one."
                    % (county, township, name, field, value))
            if field == "phone" and not PHONE_RE.match(value):
                raise RuntimeError("%s County, %s township: %s's phone is %r"
                                   % (county, township, name, value))
            row[field] = value
        rows.append(row)
    return rows


def build(cache, shipped, today):
    """{GEOID: record} plus the lines to print, or a refusal."""
    payload, notes, carried, flagged = {}, [], [], []
    # Preserve first, so a county that went dark keeps what it published and the
    # floors below see it. Its people and its stamp are the OLD run's; nothing
    # is restamped with today's date, because today nothing was read.
    for geoid, record in (shipped or {}).items():
        fips = record.get("countyFips")
        if fips and fips not in cache:
            payload[geoid] = record
            if record.get("county") not in carried:
                carried.append(record.get("county"))

    for fips in sorted(cache):
        county = cache[fips]
        index = fetch_subdivisions(fips)
        matched = 0
        for township in sorted(county["townships"]):
            record = county["townships"][township]
            wanted = ALIASES.get((fips, township), township)
            hits = index.get(norm(wanted)) or []
            if len(hits) != 1:
                raise RuntimeError(
                    "%s County publishes officers for %r and the census fabric "
                    "holds %d subdivision(s) of that name in the county. The key "
                    "is the GEOID, so a township that cannot be placed would "
                    "render on nobody's card -- read the page, and declare an "
                    "alias if the two publishers spell it differently."
                    % (county["county"], township, len(hits)))
            attrs = hits[0]
            geoid = attrs["GEOID"]
            if not GEOID_RE.match(geoid):
                raise RuntimeError("%s County, %s township: TIGERweb gave GEOID %r"
                                   % (county["county"], township, geoid))
            if geoid in payload and payload[geoid].get("countyFips") in cache:
                raise RuntimeError(
                    "two townships resolve to GEOID %s (%s County's %r and %r). "
                    "One key cannot carry two governments."
                    % (geoid, county["county"], payload[geoid].get("township"),
                       township))
            entry = {"township": attrs["NAME"],
                     "county": county["county"],
                     "countyFips": fips,
                     "sourceUrl": county["sourceUrl"],
                     "asOf": today,
                     "officials": clean_officials(county["county"], township,
                                                  record["officials"], flagged)}
            if record.get("selection"):
                entry["selection"] = record["selection"]
            payload[geoid] = entry
            matched += 1
        notes.append("  %-14s %3d township(s) placed, %3d official(s)"
                     % (county["county"], matched,
                        sum(len(payload[g]["officials"]) for g in payload
                            if payload[g].get("countyFips") == fips)))
    if carried:
        notes.append("  carried forward (not read this run): %s"
                     % ", ".join(sorted(c for c in carried if c)))
    # PRINTED EVERY RUN, never corrected and never dropped -- see NAME_RE.
    for line in sorted(flagged):
        notes.append("  published with unusual punctuation, shipped verbatim: %s"
                     % line)
    return payload, notes


def verify(payload, where):
    """The floors, applied to whatever is about to ship or already has."""
    counties = {r.get("countyFips") for r in payload.values()}
    officials = sum(len(r.get("officials") or []) for r in payload.values())
    phones = sum(1 for r in payload.values() for o in r.get("officials") or []
                 if o.get("phone"))
    if len(counties) < MIN_COUNTIES:
        raise RuntimeError("%s: %d counties, floor %d -- a county leaves either "
                           "because its page changed shape or because its "
                           "robots.txt now refuses us, and those are different "
                           "problems" % (where, len(counties), MIN_COUNTIES))
    if len(payload) < MIN_TOWNSHIPS:
        raise RuntimeError("%s: %d townships, floor %d"
                           % (where, len(payload), MIN_TOWNSHIPS))
    if officials < MIN_OFFICIALS:
        raise RuntimeError("%s: %d officials, floor %d"
                           % (where, officials, MIN_OFFICIALS))
    if phones < MIN_PHONES:
        raise RuntimeError("%s: %d phones, floor %d -- four of the twelve "
                           "counties publish one and eight publish none, so a "
                           "shortfall is one of those four changing shape"
                           % (where, phones, MIN_PHONES))
    for geoid, record in payload.items():
        if not GEOID_RE.match(geoid):
            raise RuntimeError("%s: %r is not an Iowa subdivision GEOID"
                               % (where, geoid))
        if geoid[:5] != record.get("countyFips"):
            raise RuntimeError("%s: %s sits under county %s"
                               % (where, geoid, record.get("countyFips")))
        blob = json.dumps(record)
        if ADDRESS_RE.search(blob):
            raise RuntimeError(
                "%s: %s carries what reads as a street address. These county "
                "pages publish township officers' HOME addresses and no field "
                "of this file may ever hold one." % (where, geoid))
    return len(counties), officials, phones


def main():
    check_only = "--check" in sys.argv[1:]
    out_path = os.path.join(APP_DATA_DIR, OUT_NAME)
    shipped = None
    if os.path.exists(out_path):
        shipped = load(out_path, "the shipped roster is this build's preserve base")

    if check_only:
        # OFFLINE, which is what makes this a merge gate: it re-applies every
        # floor and the no-address rule to the file a reader is served, and
        # needs neither the cache nor the census.
        if shipped is None:
            raise RuntimeError("%s is missing" % out_path)
        counties, officials, phones = verify(shipped, OUT_NAME)
        print("ia-township-officers: OK — %d townships across %d counties, "
              "%d officials, %d phones" % (len(shipped), counties, officials,
                                           phones))
        return

    cache = load(CACHE, "run ia/scripts/ia_township_officers_scraper.py first")
    today = datetime.date.today().isoformat()
    payload, notes = build(cache, shipped, today)
    for line in notes:
        print(line)
    counties, officials, phones = verify(payload, OUT_NAME)
    with open(out_path, "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("ia-township-officers: wrote %d townships across %d counties, "
          "%d officials, %d phones" % (len(payload), counties, officials, phones))


if __name__ == "__main__":
    main()
