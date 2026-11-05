#!/usr/bin/env python3
"""
Build il/data/app/election-results.json and its ward files from the raw read made by
chicago_election_results_scraper.py: every contest on Chicago's ballot for one
election, each precinct's votes for each choice, grouped by the map layer the
contest is elected from, so the Election Results card can offer the races on
the clicked precinct's ballot by layer and the map can fill each precinct by
the choice with the most votes there.

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

Usage:
    python3 scripts/build_chicago_election_results.py /tmp/results_raw.json \
        --election-date 2026-11-03 [--certified YYYY-MM-DD] [--precincts keys.json]
"""

import argparse
import json
import os
import re
import sys
import urllib.request

from election_results_common import ResultsError, write_results
from scraper_common import (UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail,
                            require_robots_once)

fail = make_fail("build-chicago-election-results")

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DATA = os.path.join(HERE, "..", "il", "data", "app")
PRECINCT_URL = ("https://data.cityofchicago.org/resource/i8fv-xe4b.json"
                "?$select=ward_precinct&$limit=5000")
MIN_CONTESTS = 50
EXPECTED_PRECINCTS = 1291

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
    ("county-board", "Cook County Board", "county-board",
     r"^Commissioner, County Board \d+(st|nd|rd|th) District$"),
    ("county", "Cook County offices", "county",
     r"^(Board President|Clerk|Sheriff|Treasurer|Assessor), Cook County$"),
    ("ccbr", "Board of Review", "ccbr", r"^Board of Review, \d+(st|nd|rd|th) District$"),
    ("judicial-subcircuit", "Judges elected by subcircuit", "judicial-subcircuit",
     r"^Judge, \d+(st|nd|rd|th) Subcircuit \(Vacancy of .+\)$"),
    ("judges", "Judges elected countywide or by district", None,
     r"^(Appellate Court Judge|Circuit Court Judge|Supreme Court Judge|Judge,? .*Circuit) \(Vacancy of .+\)$"),
    ("school-board", "Board of Education", "school-board",
     r"^(President, Board of Education|Member, Board of Education, Subdistrict \d+[AB])$"),
]
# The menu's order: the ballot's own, top of the ticket down.
GROUP_ORDER = ["statewide", "congress", "il-senate", "il-house", "mwrd", "county",
               "county-board", "ccbr", "judges", "judicial-subcircuit", "retention",
               "school-board", "questions"]
GROUP_LABELS = dict((g[0], g[1]) for g in GROUP_RULES)
GROUP_LABELS.update({"retention": "Judges up for retention", "questions": "Ballot questions"})
GROUP_LAYERS = dict((g[0], g[2]) for g in GROUP_RULES)
GROUP_LAYERS.update({"retention": None, "questions": None})

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
CITY_ONLY_GROUPS = ("school-board",)


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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw")
    ap.add_argument("--election-date", required=True)
    ap.add_argument("--certified", help="the date the Board proclaimed the official results")
    ap.add_argument("--precincts", help="a JSON list of the map's ward_precinct keys (offline)")
    ap.add_argument("--app-data", default=APP_DATA,
                    help="the app's data/app directory (default: il/data/app)")
    args = ap.parse_args()

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
        contests.append({
            "id": c["contestId"],
            "name": c["name"],
            "group": group_of(c),
            "choices": choices,
            "total": c["total"],
            "precincts": precincts,
        })
    if turnout is None:
        fail("the raw read has no turnout entry")
    if len(contests) < MIN_CONTESTS:
        fail("only %d contests; expected at least %d" % (len(contests), MIN_CONTESTS))
    for c in contests:
        c["beyond"] = reaches_beyond(c)
    contests.sort(key=lambda c: (GROUP_ORDER.index(c["group"]), int(c["id"])))

    groups = [{"id": g, "label": GROUP_LABELS[g], "layer": GROUP_LAYERS[g]} for g in GROUP_ORDER]
    stamp = {
        "election": "General Election",
        "electionDate": args.election_date,
        "source": raw["source"],
        "read": raw["read"],
        "certified": bool(args.certified),
        "certifiedDate": args.certified or None,
    }
    note = ("Unofficial results as the Chicago Board of Election Commissioners publishes "
            "them, until the Board proclaims the official results (certified then reads "
            "true). Precinct keys are WWPPP, as the city's precinct map writes its "
            "ward_precinct property; each precinct's counts are in its ward's part file. "
            "The layout is scripts/election_results_common.py's.")
    try:
        n, nparts = write_results(args.app_data, stamp, groups, turnout, contests,
                                  lambda k: "ward-" + k[:2], note)
    except ResultsError as e:
        fail(str(e))
    if nparts != 50:
        fail("wrote %d part files, expected one per ward (50)" % nparts)
    by = {}
    for c in contests:
        by[c["group"]] = by.get(c["group"], 0) + 1
    print("wrote %d contests (%s), turnout for %d precincts and %d ward files under %s"
          % (n, ", ".join("%s %d" % (g, by[g]) for g in GROUP_ORDER if g in by),
             len(turnout["precincts"]), nparts, os.path.relpath(args.app_data)), file=sys.stderr)

if __name__ == "__main__":
    main()
