#!/usr/bin/env python3
"""Indiana's township trustees and township board members, from the Indiana
Election Division's certified results, every name dated to the election that
seated it.

WHAT THIS PUBLISHES. Each of Indiana's 1,004 civil townships elects a trustee
and a three-member township board (IC 36-6-4, IC 36-6-6) at the general
election held in the middle of a presidential term (2022, then 2026). The
Election Division keeps every certified general in the archive the county and
city builders already read, and its office categories 1021 ("Township
Trustee") and 1023 ("Township Board Member") name a winner for nearly every
township. This file is keyed by the Census county-subdivision id the Township
or City card already carries, so the card can only name the officers of the
township it draws.

A winner is a fact with a date on it, NOT a statement of who holds the office
today. Indiana fills a township vacancy by party caucus, which no result
records, so the card says so in words, as the county and city cards do.

HOW A RACE FINDS ITS TOWNSHIP. The results title the same office many ways
("Blue Creek Township Board Member, Adams County", "Pine Twp. Board Member",
Ripley's bare "Township Trustee"), but almost every race also carries the
township as its jurisdiction ("Blue Creek Twp", "Shelby"). A race is matched by
its county and that jurisdiction first, then by the township named in its
title, against the townships the Census draws in that county. A race that
matches no township, or more than one, fails the build unless it is listed
here with the reason:

  ALIASES          a results name that is another spelling of a Census township
                   ("St Joe" for St. Joseph, "Greene" for Green), or a township
                   the Census records under a town's name (Hamilton County's
                   Adams Township is the Census record "Sheridan town").
  SHARED           one government for several Census townships: Johnson
                   County's Franklin, Needham and Union townships elect one
                   trustee and one board between them.
  LEFT_OUT         a race whose title names a different office than its
                   category, so which office it elects cannot be told from the
                   results. It names nobody rather than a guess.

WHAT IS NOT HERE, AND SAYS SO. A township with no race in the results (nobody
was on the ballot) is absent and its card says the results name nobody. A board
whose race elected fewer winners than seats keeps the winners it has and
records how many seats had nobody elected. Marion County's township boards are
not in the results at all; its nine trustees are.

A RESULT COUNTS FROM THE DAY ITS TERM BEGINS, AND ONLY THE NEWEST ONE COUNTS.
Township officers elected in November take office the following January 1, and
every township office is on the same ballot, so the newest certified general
whose terms have begun replaces the last one whole. A township absent from the
newest general is dropped rather than kept on an expired term.

Usage:
    python3 in/scripts/build_in_township_officials.py          # fetch and write
    python3 in/scripts/build_in_township_officials.py --check  # offline gate
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_in_county_officials as C  # noqa: E402
from scraper_common import require_robots_once  # noqa: E402  (C put scripts/ on the path)

INSTANCE = C.INSTANCE
REPO_ROOT = os.path.dirname(INSTANCE)
OUT = os.path.join(INSTANCE, "data", "app", "in-township-officials.json")

# The Election Division's own office-category ids, read off the 2022 archive's
# statewideElectionsC_A.json on 2026-10-15.
TRUSTEE_CATEGORY = "1021"   # "Township Trustee"
BOARD_CATEGORY = "1023"     # "Township Board Member"

FIRST_YEAR = 2022
REQUIRED_YEARS = (2022,)

# The Census's county subdivisions for Indiana, the same layer the Township or
# City card draws (Places_CouSub_ConCity_SubMCD layer 1).
TIGER_COUSUB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                "Places_CouSub_ConCity_SubMCD/MapServer/1/query"
                "?where=STATE%3D%2718%27&outFields=GEOID,NAME,BASENAME,LSADC"
                "&returnGeometry=false&f=json&resultRecordCount=2000")
TOWNSHIPS_EXPECTED = 1004

# (county, the results' township name) -> Census GEOID. Measured 2026-10-15.
# A township the Census records under another name carries a note in ALIAS_NOTES
# so the card can say which government it is naming.
ALIASES = {
    ("Allen", "St Joe"): "1800366924",          # St. Joseph township
    ("Hamilton", "Adams"): "1805769354",        # the Census record "Sheridan town"
    ("Hamilton", "Washington"): "1805782714",   # Westfield Washington township
    ("Lawrence", "Indian"): "1809336054",       # Indian Creek township
    ("Wayne", "Greene"): "1817729250",          # Green township
}
ALIAS_NOTES = {
    "1805769354": "The Census records Adams Township under the name of the "
                  "town of Sheridan. Adams Township still elects a trustee and "
                  "a board, named here.",
}

# One township government for several Census townships.
SHARED = {
    ("Johnson", "Franklin Union Needham"): {
        "geoids": ["1808125468", "1808152164", "1808177390"],
        "note": "Franklin, Needham and Union townships elect one trustee and "
                "one township board between them.",
    },
}

# (year, county, published title) -> why the race is not used.
LEFT_OUT = {
    (2022, "Porter", "Town Of Pines"):
        "filed as a township trustee race with Pine Township as its "
        "jurisdiction, but titled for the Town of Pines",
    (2022, "Clark", "Borden Town Council"):
        "filed as a township board race with Wood Township as its "
        "jurisdiction, but titled for the Borden town council",
}

# Floors on the shipped file, below the 2022 measurement (952 trustees named,
# 915 boards with at least one member) so one county's change cannot empty it.
MIN_TOWNSHIPS = 950
MIN_TRUSTEES = 930
MIN_BOARDS = 880


def fail(msg):
    raise SystemExit("build-in-township-officials: FATAL: %s" % msg)


def norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower().replace("saint", "st"))


def township_names(title, jur):
    """The names a race could mean, jurisdiction first."""
    out = []
    for part in (jur or "").split(","):
        part = re.sub(r"\s+(Township|Twp\.?|Twsp)\b.*$", "", part.strip(), flags=re.I)
        if part:
            out.append(part)
    m = re.match(r"^(.*?)\s+(?:Township|Twp\.?|Twsp|Trustee|Advisory|Board)\b",
                 title, re.I)
    if m and m.group(1).strip():
        out.append(m.group(1).strip())
    return out


def census_townships(session):
    """county FIPS -> {normalised basename: record}, and GEOID -> record."""
    doc = C.fetch_json(session, TIGER_COUSUB)
    if doc is None or doc.get("error"):
        fail("TIGERweb answered no county subdivisions: %r" % (doc or {}).get("error"))
    recs = [f["attributes"] for f in doc.get("features") or []]
    n = sum(1 for r in recs if r.get("LSADC") == "44")
    if n != TOWNSHIPS_EXPECTED:
        fail("TIGERweb draws %d civil townships in Indiana, expected %d"
             % (n, TOWNSHIPS_EXPECTED))
    by_county, by_geoid = {}, {}
    for r in recs:
        by_county.setdefault(r["GEOID"][:5], {})[norm(r["BASENAME"])] = r
        by_geoid[r["GEOID"]] = r
    return by_county, by_geoid


def region_races(doc):
    for region in C.as_list(doc["Root"]["OfficeCategory"]["Regions"]["Region"]):
        for race in C.as_list((region.get("Races") or {}).get("Race")):
            yield region, race


def place(year, region, race, by_county):
    """(geoids, note) for one race, or None for a race LEFT_OUT."""
    county = region["MAP_JURISDICTION_NAME"]
    title = re.sub(r"\s+", " ", race["OFFICE_TITLE"]).strip()
    if (year, county, title) in LEFT_OUT:
        return None
    jur = (race.get("Jurisdiction") or {}).get("JURISDICTION_NAME")
    names = township_names(title, jur)
    for (cty, name), shared in SHARED.items():
        if norm(cty) == norm(county):
            if norm(name) in {norm(n) for n in names} or norm(name) in norm(title):
                return shared["geoids"], shared["note"]
    fips = str(region["MAP_FIPS"])
    if not re.match(r"^18\d{3}$", fips):
        fail("%d %s: region carries no county FIPS (%r)" % (year, county, fips))
    hits = set()
    for name in names:
        alias = next((g for (cty, nm), g in ALIASES.items()
                      if norm(cty) == norm(county) and norm(nm) == norm(name)), None)
        if alias:
            hits.add(alias)
            continue
        rec = by_county.get(fips, {}).get(norm(name))
        if rec:
            hits.add(rec["GEOID"])
    if len(hits) != 1:
        fail("%d %s: the race %r (jurisdiction %r) matches %s — add it to "
             "ALIASES, SHARED or LEFT_OUT with the reason"
             % (year, county, title, jur, sorted(hits) or "no township"))
    geoid = next(iter(hits))
    return [geoid], ALIAS_NOTES.get(geoid)


def read_year(session, year, root, by_county, by_geoid):
    parties = C.party_names(root)
    when = C.election_date(root)
    source = C.PAGE % year
    counties = C.county_geoids()
    out = {}

    def rec_for(geoid, region, note):
        r = out.setdefault(geoid, {
            "name": by_geoid[geoid]["NAME"],
            "county": C.results_county(region["MAP_JURISDICTION_NAME"], counties),
            "trustee": None, "board": [], "boardSeats": 0})
        if note:
            r["note"] = note
        return r

    def person(c, title):
        p = {"name": re.sub(r"\s+", " ", c["NAME_ON_BALLOT"]).strip(),
             "election": when, "office": title, "sourceUrl": source}
        party = parties.get(str(c.get("POLITICALPARTYID")))
        if party:
            p["party"] = party
        return p

    for cat in (TRUSTEE_CATEGORY, BOARD_CATEGORY):
        doc = C.fetch_json(session, C.OFFICE_FILE % (year, cat))
        if doc is None:
            fail("the %d general has no office file for category %s" % (year, cat))
        for region, race in region_races(doc):
            placed = place(year, region, race, by_county)
            if placed is None:
                continue
            geoids, note = placed
            title = re.sub(r"\s+", " ", race["OFFICE_TITLE"]).strip()
            seats = int(race.get("NumofSeats") or 0)
            cands = C.as_list((race.get("Candidates") or {}).get("Candidate"))
            won = sorted([c for c in cands if c.get("isWinner") == "T"],
                         key=lambda c: -int(c.get("TOTAL_VOTES") or 0))
            if len(won) > seats:
                fail("%d %s: %r elects %d and flags %d winners"
                     % (year, region["MAP_JURISDICTION_NAME"], title, seats, len(won)))
            for geoid in geoids:
                r = rec_for(geoid, region, note)
                if cat == TRUSTEE_CATEGORY:
                    if r["trustee"] is not None:
                        fail("%d %s: two trustee races for %s"
                             % (year, region["MAP_JURISDICTION_NAME"], r["name"]))
                    # Three trustee races are filed as electing three; each
                    # flags one winner, and a township has one trustee.
                    if len(won) != 1:
                        fail("%d %s: %r flags %d winners for one trustee"
                             % (year, region["MAP_JURISDICTION_NAME"], title, len(won)))
                    r["trustee"] = person(won[0], title)
                else:
                    r["boardSeats"] += seats
                    r["board"].extend(person(c, title) for c in won)
    for r in out.values():
        if not r["board"]:
            r.pop("board")
            r.pop("boardSeats")
    return out


def counting_years(session, today):
    years = []
    for year in range(FIRST_YEAR, today.year + 1, 4):
        settings = C.fetch_json(session, C.SETTINGS % year)
        if settings is None:
            print("  %d general: no archive yet — skipped" % year)
            continue
        root = settings.get("Root") or {}
        if root.get("Certified") != "T":
            print("  %d general: archived but not certified — skipped" % year)
            continue
        if today < datetime.date(year + 1, 1, 1):
            print("  %d general: certified; its winners take office on January "
                  "1, %d — held until then" % (year, year + 1))
            continue
        years.append((year, root))
    got = {y for y, _ in years}
    for y in REQUIRED_YEARS:
        if y not in got:
            fail("the %d general is not readable — every office rests on it" % y)
    return years


def check(roster):
    problems = []
    trustees = sum(1 for r in roster.values() if r.get("trustee"))
    boards = sum(1 for r in roster.values() if r.get("board"))
    if len(roster) < MIN_TOWNSHIPS:
        problems.append("the file names %d townships, floor %d" % (len(roster), MIN_TOWNSHIPS))
    if trustees < MIN_TRUSTEES:
        problems.append("%d trustees named, floor %d" % (trustees, MIN_TRUSTEES))
    if boards < MIN_BOARDS:
        problems.append("%d boards named, floor %d" % (boards, MIN_BOARDS))
    for geoid, r in sorted(roster.items()):
        if not re.match(r"^18\d{8}$", geoid):
            problems.append("key %r is not an Indiana county-subdivision id" % geoid)
        people = ([r["trustee"]] if r.get("trustee") else []) + (r.get("board") or [])
        if not people:
            problems.append("%s names nobody" % geoid)
        if r.get("board") and len(r["board"]) > r.get("boardSeats", 0):
            problems.append("%s names %d board members for %d seats"
                            % (geoid, len(r["board"]), r.get("boardSeats", 0)))
        for p in people:
            if not (p.get("name") or "").strip():
                problems.append("%s carries a person with no name" % geoid)
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", p.get("election") or ""):
                problems.append("%s: %r carries no election date" % (geoid, p.get("name")))
            if not (p.get("sourceUrl") or "").startswith(C.HOST + "/archive/"):
                problems.append("%s: %r carries no source" % (geoid, p.get("name")))
    for shared in SHARED.values():
        present = [g for g in shared["geoids"] if g in roster]
        if present and len(present) != len(shared["geoids"]):
            problems.append("a shared township government names %s and not %s"
                            % (present, sorted(set(shared["geoids"]) - set(present))))
    return problems


def summary(roster):
    trustees = sum(1 for r in roster.values() if r.get("trustee"))
    boards = sum(1 for r in roster.values() if r.get("board"))
    members = sum(len(r.get("board") or []) for r in roster.values())
    return trustees, boards, members


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its floors and shape")
    args = ap.parse_args()
    if args.check:
        with open(OUT, encoding="utf-8") as f:
            roster = json.load(f)
        problems = check(roster)
        if problems:
            for p in problems:
                print("build-in-township-officials: FAIL: " + p)
            raise SystemExit(1)
        t, b, m = summary(roster)
        print("build-in-township-officials --check: OK — %d townships, %d "
              "trustees and %d boards (%d members) named, every name dated to "
              "its election" % (len(roster), t, b, m))
        return
    import requests  # noqa: PLC0415
    session = requests.Session()
    session.headers.update(C.UA_HEADERS_ROSTER_BOT)
    # The same read C.fetch_json makes before each fetch, stated here so this
    # file asks each host's policy itself, with the client that crawls.
    require_robots_once(C.HOST + "/", C.UA_ROSTER_BOT,
                        headers=C.UA_HEADERS_ROSTER_BOT)
    require_robots_once("https://tigerweb.geo.census.gov/", C.UA_ROSTER_BOT,
                        headers=C.UA_HEADERS_ROSTER_BOT)
    by_county, by_geoid = census_townships(session)
    years = counting_years(session, datetime.date.today())
    year, root = max(years)
    print("general read: %d (the newest certified general whose terms have begun)"
          % year)
    roster = read_year(session, year, root, by_county, by_geoid)
    problems = check(roster)
    if problems:
        for p in problems:
            print("build-in-township-officials: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    t, b, m = summary(roster)
    print("wrote %s: %d townships, %d trustees, %d boards (%d members)"
          % (os.path.relpath(OUT, REPO_ROOT), len(roster), t, b, m))


if __name__ == "__main__":
    main()
