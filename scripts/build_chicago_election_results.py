#!/usr/bin/env python3
"""
Build il/data/app/election-results.json and its ward files from the raw read made by
chicago_election_results_scraper.py: every contest on Chicago's ballot for one
election, each precinct's votes for each choice, grouped by the map layer the
contest is elected from, so the Election Results card can offer the races on
the clicked precinct's ballot by layer and the map can fill each precinct by
the choice with the most votes there.

TWO KINDS OF BALLOT (2026-11-15). The November general election's contests,
and a city election's: Mayor, Clerk, Treasurer, each ward's Alderperson and
each police district's council, as the Board named them on its 2023 Municipal
General page (results id 241, read through the scraper that day: 88 contests
over 1,291 precincts, every check passing). The election's own name and date
are read from the Board's page title, and --election-date must agree with it,
so a read of the wrong election fails rather than being written under the
right one's date.

UNOFFICIAL UNTIL CERTIFIED. The file carries `certified: false` and the time it
was read; the card and the map legend say so on every view. When the Board of
Election Commissioners proclaims the official results, run the build with
`--certified <date the Board proclaimed them>` and the file says that instead.

THE CHECKS, before anything is written:
  - every precinct key is one of the 1,291 the map draws (the city's precinct
    map, Socrata i8fv-xe4b, keyed WWPPP like its `ward_precinct` property),
    read from that dataset when --precincts is not given;
  - the turnout entry covers every one of them;
  - every contest names at least one choice (an unopposed race names one), at least one precinct, and a
    group from GROUP_RULES (a contest no rule recognises fails the build, so a
    new kind of contest is placed by a person rather than dropped);
  - at least MIN_CONTESTS contests.

THE COUNTIES (--counties, one raw read per scraper): the seven county clerks'
precinct results are folded in beside Chicago's by
build_il_county_election_results.py, which carries its own checks and the
rules for one race counted by several offices. Each office's count is
certified on its own (--certified for the Board, --county-certified
county=date for a clerk, kept from the shipped file once given); the file
reads certified once every office's is.

Usage:
    python3 scripts/build_chicago_election_results.py /tmp/results_raw.json \
        --election-date 2026-11-03 [--certified YYYY-MM-DD] [--precincts keys.json] \
        [--counties platinum_raw.json --counties kane_raw.json]
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

from election_results_common import ResultsError, write_results
import build_il_county_election_results as il_counties
from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,
                            require_robots_once)

fail = make_fail("build-chicago-election-results")

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DATA = os.path.join(HERE, "..", "il", "data", "app")
PRECINCT_URL = ("https://data.cityofchicago.org/resource/i8fv-xe4b.json"
                "?$select=ward_precinct&$limit=5000")
MIN_CONTESTS = 50
EXPECTED_PRECINCTS = 1291
# A mail ballot postmarked by Election Day is counted if it arrives within 14
# days after it (10 ILCS 5/19-8(c)); for 3 November 2026 the Board's own
# vote-by-mail page said 17 November, which is that rule.
MAIL_BALLOT_DAYS = 14


def uncounted_note(election_date):
    last = datetime.date.fromisoformat(election_date) + datetime.timedelta(days=MAIL_BALLOT_DAYS)
    return ("The Board is still counting mail ballots postmarked by Election Day that "
            "arrive by %s %d." % (last.strftime("%B"), last.day))


# The Board titles a results page "<year> <name> - <m>/<d>/<yy or yyyy>"
# ("2026 General Election - 11/3/2026", "2023 Municipal General - 2/28/23").
TITLE_RE = re.compile(r"^(\d{4}) (.+?) - (\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$")


def election_of(title, election_date):
    """The election's name as the cards print it after its year ("General
    Election", "Municipal General Election"), from the Board's page title,
    which must name --election-date."""
    m = TITLE_RE.match(str(title or "").strip())
    if not m:
        fail("the Board's page title %r is not '<year> <name> - <m>/<d>/<yy>'" % title)
    year = int(m.group(5)) if len(m.group(5)) == 4 else 2000 + int(m.group(5))
    on_page = "%04d-%02d-%02d" % (year, int(m.group(3)), int(m.group(4)))
    if on_page != election_date:
        fail("the Board's page is for %s (%r); --election-date says %s"
             % (on_page, title, election_date))
    if int(m.group(1)) != year:
        fail("the Board's page title %r names two years" % title)
    name = m.group(2).strip()
    return name if re.search(r"(?i)\belection\b", name) else name + " Election"


# (group id, label shown in the race menu, the map layer it is elected from or
# None, a pattern the Board's contest name matches). First match wins, so the
# narrow patterns come first. The layer is what the menu groups by; a group
# with no layer is elected citywide, countywide or statewide.
GROUP_RULES = [
    ("congress", "U.S. House", "congress", r"^U\.S\. Representative, \d+(st|nd|rd|th) District$"),
    ("statewide", "Statewide offices", None,
     r"^(Senator, U\.S\.|Governor & Lieutenant Governor, Illinois|"
     r"(Attorney General|Secretary of State|Comptroller|Treasurer), State of Illinois)$"),
    ("il-senate", "Illinois Senate", "il-senate", r"^State Senator, \d+(st|nd|rd|th) District$"),
    ("il-house", "Illinois House", "il-house", r"^State Representative, \d+(st|nd|rd|th) District$"),
    ("mwrd", "Water Reclamation District", "mwrd", r"^Commissioner, Water Reclamation Dist"),
    ("county-board", "County board", "county-board",
     r"^Commissioner, County Board \d+(st|nd|rd|th) District$"),
    ("county", "County offices", "county",
     r"^(Board President|Clerk|Sheriff|Treasurer|Assessor), Cook County$"),
    ("ccbr", "Board of Review", "ccbr", r"^Board of Review, \d+(st|nd|rd|th) District$"),
    ("judicial-subcircuit", "Judges elected by subcircuit", "judicial-subcircuit",
     r"^Judge, \d+(st|nd|rd|th) Subcircuit \(Vacancy of .+\)$"),
    ("judges", "Judges elected countywide or by district", None,
     r"^(Appellate Court Judge|Circuit Court Judge|Supreme Court Judge|Judge,? .*Circuit) \(Vacancy of .+\)$"),
    ("school-board", "Board of Education", "school-board",
     r"^(President, Board of Education|Member, Board of Education, Subdistrict \d+[AB])$"),
    # a city election's ballot, as the Board named its contests in 2023
    ("city", "Citywide offices", None, r"^(Mayor|Clerk|Treasurer)$"),
    ("city-council", "City Council", "ward",
     r"^(Alderperson|Alderman),? \d+(st|nd|rd|th) Ward$"),
    ("police-council", "Police district councils", "ccpsa-district-council",
     r"^Council Member, Chicago Police Department \d+(st|nd|rd|th) District$"),
]
# Each police district elects a council of three (Municipal Code of Chicago
# 2-80-070; the app's own council roster lists three seats per district), so
# a voter may choose up to three and a share is of votes, not of voters.
GROUP_SEATS = {"police-council": 3}
# The menu's order: the ballot's own, top of the ticket down.
GROUP_ORDER = ["statewide", "congress", "il-senate", "il-house", "mwrd", "county",
               "county-board", "ccbr", "regional", "judges", "judicial-subcircuit", "retention",
               "school-board", "city", "city-council", "police-council", "local", "questions"]
GROUP_LABELS = dict((g[0], g[1]) for g in GROUP_RULES)
GROUP_LABELS.update({"retention": "Judges up for retention", "questions": "Ballot questions",
                     "regional": "Regional superintendents of schools", "local": "Local offices"})
GROUP_LAYERS = dict((g[0], g[2]) for g in GROUP_RULES)
GROUP_LAYERS.update({"retention": None, "questions": None, "regional": None, "local": None})

# A retention contest is a judge's name with Yes/No; the Board heads the
# question with the judge's name alone. A name is two to five words, each
# capitalised (initials, quoted nicknames and suffixes allowed), with no word
# that a ballot question uses.
NAME_RE = re.compile(r'^[A-Z][A-Za-z.\'-]*(?:,? (?:[A-Z][A-Za-z.\'-]*|"[^"]+"|Jr\.|Sr\.|II|III|IV)){1,5}$')
QUESTION_WORDS = re.compile(r"(?i)\b(question|tax|amendment|chicago|w\d\d|p\d\d|"
                            r"services|support|limits|park|monument|remediation|"
                            r"advisory|extension|relief|shall|restart|recovery|space|"
                            r"detection|festival|blitz|national|surcharge)\b")


def group_of(contest):
    name = contest["name"]
    for gid, _label, _layer, pattern in GROUP_RULES:
        if re.search(pattern, name):
            return gid
    choices = contest["columns"][1:]
    if choices == ["Yes", "No"]:
        if NAME_RE.match(name) and not QUESTION_WORDS.search(name):
            return "retention"
        return "questions"
    fail("no group recognises contest %r (choices %r); add a rule to GROUP_RULES"
         % (name, choices))


# Contests elected from ground the Board counts all of: Chicago's own school
# board, and ballot questions put to Chicago's voters alone. Every other group
# reaches past the city line, and so does a question put to all of Cook County.
CITY_ONLY_GROUPS = ("school-board", "city", "city-council", "police-council")


def reaches_beyond(contest):
    if contest["group"] in CITY_ONLY_GROUPS:
        return False
    if contest["group"] == "questions":
        return bool(re.search(r"(?i)\bcook county\b", contest["name"]))
    return True


def key_of(ward_precinct):
    w, p = ward_precinct.split("-")
    return "%02d%03d" % (int(w), int(p))


def map_precincts(path):
    if path:
        keys = json.load(open(path))
    else:
        require_robots_once(PRECINCT_URL, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
        req = urllib.request.Request(PRECINCT_URL, headers=dict(UA_HEADERS_ROSTER_BOT))
        with urllib.request.urlopen(req, timeout=60) as resp:
            keys = [r["ward_precinct"] for r in json.load(resp)]
    keys = set("%05d" % int(k) for k in keys)
    if len(keys) != EXPECTED_PRECINCTS:
        fail("the city's precinct map lists %d precincts, expected %d"
             % (len(keys), EXPECTED_PRECINCTS))
    return keys


RESULTS_INDEX = "https://chicagoelections.gov/elections/results"

def write_placeholder(args):
    """The file the app ships before the Board has published a count.

    The map's results layer reads every election file it is given when it is
    switched on, so the file has to exist from the day the app names it; with
    no contests the layer never offers it (engine `election-results`,
    moreElections). It is never written over a file that holds results.
    """
    if not args.name or args.raw or args.counties or args.certified:
        fail("--placeholder takes --name and --election-date and nothing to build from")
    try:
        datetime.date.fromisoformat(args.election_date)
    except ValueError:
        fail("--election-date %r is not a date" % args.election_date)
    shipped = os.path.join(args.app_data, args.name + ".json")
    if os.path.exists(shipped) and json.load(open(shipped)).get("contests"):
        fail("%s already holds results; a placeholder would remove them" % os.path.relpath(shipped))
    stamp = {"election": args.placeholder, "electionDate": args.election_date,
             "source": RESULTS_INDEX, "read": None, "certified": False, "certifiedDate": None}
    note = ("No results yet: the Chicago Board of Election Commissioners has not published a "
            "count for this election. The file is here so the map can ask for it; the layout "
            "is scripts/election_results_common.py's.")
    try:
        write_results(args.app_data, stamp, [], {"total": [None, None], "precincts": {}}, [],
                      lambda k: k, note, extra={"sources": []}, name=args.name)
    except ResultsError as e:
        fail(str(e))
    # no precinct, so no part file: git keeps no empty directory, and the next
    # real build makes it again
    parts_dir = os.path.join(args.app_data, args.name)
    if os.path.isdir(parts_dir) and not os.listdir(parts_dir):
        os.rmdir(parts_dir)
    print("wrote %s with no results, for the %s of %s"
          % (os.path.relpath(shipped), args.placeholder, args.election_date), file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw", nargs="?")
    ap.add_argument("--election-date", required=True)
    ap.add_argument("--certified", help="the date the Board proclaimed the official results")
    ap.add_argument("--precincts", help="a JSON list of the map's ward_precinct keys (offline)")
    ap.add_argument("--counties", action="append", default=[],
                    help="a county scraper's raw read to fold in (il_platinum_election_results_scraper.py, "
                         "il_kane_election_results_scraper.py); give each once")
    ap.add_argument("--county-map-names", help="a JSON {county: [map precinct names]} (offline)")
    ap.add_argument("--county-certified", action="append", default=[],
                    help="county=YYYY-MM-DD for a county whose canvass is complete")
    ap.add_argument("--app-data", default=APP_DATA,
                    help="the app's data/app directory (default: il/data/app)")
    ap.add_argument("--name", help="the files' base name where this election is kept beside "
                                   "another's (default: election-results)")
    ap.add_argument("--placeholder", metavar="ELECTION",
                    help="write a file with no results for an election the Board has not counted "
                         "yet, named as this builder names it from the Board's page (\"Municipal "
                         "General Election\"); needs --name and --election-date, takes no raw read")
    args = ap.parse_args()
    if args.name and args.counties:
        fail("--name is for an election the Board alone counts; --counties folds the "
             "county clerks' results into the default file")
    if args.placeholder:
        write_placeholder(args)
        return
    if not args.raw:
        fail("give the scraper's raw read, or --placeholder for an election not counted yet")

    raw = json.load(open(args.raw))
    allowed = map_precincts(args.precincts)

    turnout = None
    contests = []
    for c in raw["contests"]:
        precincts = {}
        for wp, vals in c["precincts"].items():
            k = key_of(wp)
            if k not in allowed:
                fail("%s: precinct %s is not on the city's precinct map" % (c["name"] or "turnout", wp))
            precincts[k] = vals
        if c["contestId"] == "":
            if c["columns"] != ["Registered Voters", "Ballots Cast"]:
                fail("the turnout entry's columns are %r" % c["columns"])
            if set(precincts) != allowed:
                fail("the turnout entry covers %d of the map's %d precincts"
                     % (len(precincts), len(allowed)))
            turnout = {"total": c["total"], "precincts": precincts}
            continue
        choices = c["columns"][1:]
        # One choice is an unopposed race, which the Board lists like any other.
        if not choices:
            fail("%s names no choices" % c["name"])
        if not precincts:
            fail("%s has no precincts" % c["name"])
        group = group_of(c)
        contests.append({
            "id": c["contestId"],
            "name": c["name"],
            "group": group,
            "choices": choices,
            "total": c["total"],
            "precincts": precincts,
            "seats": GROUP_SEATS.get(group),
        })
    if turnout is None:
        fail("the raw read has no turnout entry")
    if len(contests) < MIN_CONTESTS:
        fail("only %d contests; expected at least %d" % (len(contests), MIN_CONTESTS))
    for c in contests:
        c["beyond"] = reaches_beyond(c)
    election = election_of(raw.get("election"), args.election_date)
    part_of = lambda k: "ward-" + k[:2]
    county_lines = []
    # The Board's own entry rides every file, so the card reads the publisher,
    # the reading time and the mail-ballot date from the file it is showing
    # rather than from the app's code, which names one election's date.
    chicago = {"id": "chicago", "publisher": "Chicago Board of Election Commissioners",
               "areaName": "Chicago", "source": raw["source"], "read": raw["read"],
               "certified": bool(args.certified), "certifiedDate": args.certified or None,
               "uncountedNote": "" if args.certified else uncounted_note(args.election_date)}
    sources = [chicago]
    if args.counties:
        # a county's certification, once given, is kept from the shipped
        # index, so a daily run does not turn it back into unofficial
        certified = {}
        shipped = os.path.join(args.app_data, "election-results.json")  # --name never comes with --counties
        if os.path.exists(shipped):
            for src in json.load(open(shipped)).get("sources") or []:
                if src.get("id") != "chicago" and src.get("certified") and src.get("certifiedDate"):
                    certified[src["id"]] = src["certifiedDate"]
        certified.update(dict(c.split("=", 1) for c in args.county_certified))
        offline = json.load(open(args.county_map_names)) if args.county_map_names else None
        try:
            sources, county_part, county_lines = il_counties.add_counties(
                contests, turnout, [json.load(open(p)) for p in args.counties], chicago,
                offline_names=offline, certified=certified)
        except il_counties.CountyError as e:
            fail(str(e))
        part_of = lambda k: county_part(k) if ":" in k else "ward-" + k[:2]
        contests.sort(key=il_counties.sort_key(GROUP_ORDER))
    else:
        contests.sort(key=lambda c: (GROUP_ORDER.index(c["group"]), int(c["id"])))
    for c in contests:
        c.pop("_order", None)

    groups = [{"id": g, "label": GROUP_LABELS[g], "layer": GROUP_LAYERS[g]} for g in GROUP_ORDER]
    stamp = {
        "election": election,
        "electionDate": args.election_date,
        "source": raw["source"],
        "read": raw["read"],
        "certified": bool(args.certified),
        "certifiedDate": args.certified or None,
    }
    if sources:
        # the file is certified once every office's count is
        stamp["certified"] = all(s["certified"] for s in sources)
        stamp["certifiedDate"] = max(s["certifiedDate"] for s in sources) if stamp["certified"] else None
    note = ("Unofficial results as the Chicago Board of Election Commissioners publishes "
            "them, until the Board proclaims the official results (certified then reads "
            "true). Precinct keys are WWPPP, as the city's precinct map writes its "
            "ward_precinct property; each precinct's counts are in its ward's part file. "
            "The layout is scripts/election_results_common.py's.")
    try:
        n, nparts = write_results(args.app_data, stamp, groups, turnout, contests,
                                  part_of, note, extra={"sources": sources}, name=args.name)
    except ResultsError as e:
        fail(str(e))
    if len(set(part_of(k) for k in turnout["precincts"] if ":" not in k)) != 50:
        fail("the Chicago precincts do not fill one file per ward (50)")
    for line in county_lines:
        print(line, file=sys.stderr)
    by = {}
    for c in contests:
        by[c["group"]] = by.get(c["group"], 0) + 1
    print("wrote %d contests (%s), turnout for %d precincts and %d ward files under %s"
          % (n, ", ".join("%s %d" % (g, by[g]) for g in GROUP_ORDER if g in by),
             len(turnout["precincts"]), nparts, os.path.relpath(args.app_data)), file=sys.stderr)

if __name__ == "__main__":
    main()
