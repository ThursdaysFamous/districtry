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

A CITY ELECTION'S RUNOFF (2026-11-17, Adam: "Build runoff"). Where nobody wins
more than half of the votes for mayor, clerk, treasurer or a ward's
alderperson, the two with the most votes meet again on the runoff date in
RUNOFF_DATES, and nothing else of the city election is on that ballot. The
Board gives the runoff its own results page, titled "<year> Municipal Runoffs"
(2023's is results id 242, read through the scraper on 2026-11-17: Mayor and 14
wards' Alderperson races, the turnout entry over all 1,291 precincts). A build
whose --election-date is a runoff date in RUNOFF_DATES is a runoff build, and
three checks change:
  - at least one contest, not MIN_CONTESTS, since a runoff can be one ward's;
  - the file lists only the precincts with a runoff race on their ballot, so a
    click in a ward with no runoff is answered by the city election's file
    (engine election-results: the latest election whose file LISTS the
    precinct), and the turnout entry need not cover the whole city;
  - a citywide race covers every precinct on the map, and a ward's race every
    precinct of that ward, which is what "one file per ward" asked of a city
    election.
Its races go in the same groups as the city election's, with a sentence saying
how a runoff is decided, and the Board's "Municipal Runoffs" is written
"Municipal Runoff Election". It is kept in its own file (--name
chicago-runoff-results), beside the city election's and November's, so the
three can be compared in the card's Election menu.

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
    python3 scripts/build_chicago_election_results.py --selftest
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
    if re.fullmatch(r"(?i)municipal runoffs?(?: election)?", name):
        return RUNOFF_ELECTION
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


# HOW A CITY RACE IS DECIDED, which the card prints under the race so a reader
# does not take "most votes" for "elected". From the Board's own "2027 Election
# Information Pamphlet and Calendar" (published June 9, 2026, revised July 28,
# 2026, "2027 Elections and offices to be filled in the City of Chicago"),
# read 2026-11-15: mayor, clerk and treasurer need a majority of the votes
# cast, and otherwise the two with the most votes meet in a runoff [65 ILCS
# 20/21-5, 20/21-12]; an alderperson needs a majority in the ward, and
# otherwise the two with the most votes meet in a supplementary election the
# same day [65 ILCS 20/21-26]; and the three candidates with the most votes in
# a police district are elected, with no second election [Chi. Muni. Code
# 2-80-070(c)]. The runoff's date is the Board's, never computed: the
# consolidated election it falls on moves when it meets Passover (10 ILCS
# 5/2A-1.1a), so a city election whose runoff date is not here is refused
# until its calendar has been read. 2023's is the date of the Board's own
# "2023 Municipal Runoffs" results page.
RUNOFF_DATES = {"2027-02-23": "2027-04-06", "2023-02-28": "2023-04-04"}
CITY_GENERAL = "Municipal General Election"
RUNOFF_ELECTION = "Municipal Runoff Election"
# The groups a runoff is held in, and what each race must cover: every precinct
# on the map for a citywide office, and every precinct of its ward for an
# alderperson (the ward number is the race name's).
RUNOFF_GROUPS = ("city", "city-council")


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return "%s %d, %d" % (d.strftime("%B"), d.day, d.year)


def first_round_of(runoff_date):
    """The city election a runoff date follows, or None when the date is not
    a runoff date in RUNOFF_DATES."""
    for first, runoff in RUNOFF_DATES.items():
        if runoff == runoff_date:
            return first
    return None


def group_notes(election, election_date):
    """{group id: the sentence on how its races are decided}, for a city
    election's first round and for its runoff; {} for any other election.

    The runoff's sentences are the Board's own rule in its 2027 calendar
    (read 2026-11-15): "a runoff election shall be held on April 6, 2027, when
    only the names of the candidates receiving the highest and second highest
    number of votes at the February 23, 2027 election" are on the ballot, and
    the same for a ward's supplementary election."""
    first = first_round_of(election_date)
    if first:
        on = long_date(first)
        return {
            "city": "No candidate won more than half of the votes on %s, so the two with the "
                    "most votes meet in this runoff. The candidate with more votes is elected." % on,
            "city-council": "No candidate won more than half of the votes in the ward on %s, so "
                            "the two with the most votes meet in this runoff. The candidate with "
                            "more votes is elected." % on,
        }
    if election != CITY_GENERAL:
        return {}
    if election_date not in RUNOFF_DATES:
        fail("no runoff date for the city election of %s: read it from the Board's election "
             "calendar and add it to RUNOFF_DATES" % election_date)
    runoff = long_date(RUNOFF_DATES[election_date])
    majority =("A candidate with more than half of the votes %sis elected. If no candidate has "
                "more than half, the two with the most votes go to a runoff election on " + runoff + ".")
    return {
        "city": majority % "",
        "city-council": majority % "in the ward ",
        "police-council": "The three candidates with the most votes in the police district are elected.",
    }


WARD_RE = re.compile(r"(\d+)(?:st|nd|rd|th) Ward$")


def runoff_turnout(contests, turnout, allowed):
    """A runoff's turnout entry, cut to the precincts with a runoff race on
    their ballot, after holding each citywide race to every precinct on the
    map and each ward's race to every precinct of its ward. A race of any
    other kind is kept as its group rule places it, and covers what it covers:
    a runoff holds none, and check_results_update.py --first-round holds an
    update with a race February does not explain, where a failed build would
    publish nothing on the night."""
    on_ballot = set()
    for c in contests:
        if c["group"] == "city":
            want = allowed
        elif c["group"] == "city-council":
            ward = "%02d" % int(WARD_RE.search(c["name"]).group(1))
            want = set(k for k in allowed if k[:2] == ward)
        else:
            want = None
        got = set(c["precincts"])
        if want is not None and got != want:
            fail("%s: the runoff race covers %d precincts and its ground has %d (%d of them "
                 "missing, %d outside it)" % (c["name"], len(got), len(want),
                                              len(want - got), len(got - want)))
        on_ballot |= got
    missing = on_ballot - set(turnout["precincts"])
    if missing:
        fail("the turnout entry leaves out %d precinct(s) with a runoff race on their ballot "
             "(the first: %s)" % (len(missing), sorted(missing)[0]))
    kept = dict((k, v) for k, v in turnout["precincts"].items() if k in on_ballot)
    total = turnout["total"]
    if len(kept) != len(turnout["precincts"]):
        # the totals over the precincts this file lists, so the turnout it
        # states is of the ground its races cover
        total = [sum(v[i] for v in kept.values()) for i in range(len(total))]
    return {"total": total, "precincts": kept}


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

def selftest():
    """A runoff build, on made-up reads over a made-up map of 1,291 precincts
    in 50 wards: one with a mayoral runoff lists every precinct; one with ward
    runoffs alone lists those wards' precincts and states their turnout; a
    ward race short of one of its precincts fails; and a city election's read
    with two races still fails, as it did before runoffs were built. Each is a
    run of this script, as the workflow runs it."""
    import shutil
    import subprocess
    import tempfile
    sizes = [26 if w <= 41 else 25 for w in range(1, 51)]
    keys = ["%02d%03d" % (w, p) for w, n in zip(range(1, 51), sizes) for p in range(1, n + 1)]
    assert len(keys) == EXPECTED_PRECINCTS
    wp = lambda k: "%d-%d" % (int(k[:2]), int(k[2:]))

    def race(cid, name, ground, a=60, b=40):
        return {"contestId": cid, "name": name, "columns": ["Total Votes", "Ada", "Ben"],
                "total": [(a + b) * len(ground), a * len(ground), b * len(ground)],
                "precincts": dict((wp(k), [a + b, a, b]) for k in ground)}

    def read(title, races, turnout_keys=keys):
        turnout = {"contestId": "", "name": "", "columns": ["Registered Voters", "Ballots Cast"],
                   "total": [500 * len(turnout_keys), 120 * len(turnout_keys)],
                   "precincts": dict((wp(k), [500, 120]) for k in turnout_keys)}
        return {"source": "https://chicagoelections.gov/elections/results/0", "election": title,
                "electionId": 0, "read": "2027-04-07T02:00:00Z", "contests": [turnout] + races}

    ward = lambda n: [k for k in keys if k[:2] == "%02d" % n]
    runoff_title = "2027 Municipal Runoffs - 4/6/27"
    cases = [
        ("a mayoral runoff lists every precinct, in one file per ward", "2027-04-06",
         read(runoff_title, [race("11", "Mayor", keys), race("12", "Alderperson 4th Ward", ward(4))]),
         dict(precincts=EXPECTED_PRECINCTS, parts=50, contests=2, ballots=120 * EXPECTED_PRECINCTS)),
        ("ward runoffs alone list those wards' precincts and state their turnout", "2027-04-06",
         read(runoff_title, [race("12", "Alderperson 4th Ward", ward(4)),
                             race("13", "Alderperson 10th Ward", ward(10))]),
         dict(precincts=len(ward(4)) + len(ward(10)), parts=2, contests=2,
              ballots=120 * (len(ward(4)) + len(ward(10))))),
        ("a ward's runoff short of one of its precincts fails", "2027-04-06",
         read(runoff_title, [race("12", "Alderperson 4th Ward", ward(4)[1:])]), "4th Ward: the runoff race covers"),
        ("a turnout entry missing a precinct a runoff race is on fails", "2027-04-06",
         read(runoff_title, [race("12", "Alderperson 4th Ward", ward(4))],
              [k for k in keys if k != ward(4)[0]]), "leaves out 1 precinct"),
        ("a city election's read with two races still fails", "2027-02-23",
         read("2027 Municipal General - 2/23/27", [race("11", "Mayor", keys),
                                                  race("12", "Alderperson 4th Ward", ward(4))]),
         "only 2 contests"),
    ]
    tmp = tempfile.mkdtemp(prefix="chicago-results-selftest-")
    bad = []
    try:
        with open(os.path.join(tmp, "keys.json"), "w") as f:
            json.dump(keys, f)
        for n, (why, date, raw, want) in enumerate(cases):
            app = os.path.join(tmp, "app%d" % n)
            os.makedirs(app)
            with open(os.path.join(tmp, "raw%d.json" % n), "w") as f:
                json.dump(raw, f)
            r = subprocess.run([sys.executable, os.path.abspath(__file__), os.path.join(tmp, "raw%d.json" % n),
                                "--election-date", date, "--precincts", os.path.join(tmp, "keys.json"),
                                "--app-data", app, "--name", "chicago-runoff-results"],
                               capture_output=True, text=True)
            if isinstance(want, str):
                if r.returncode == 0 or want not in r.stderr:
                    bad.append("%s: wanted a failure saying %r, got exit %d %r"
                               % (why, want, r.returncode, r.stderr[-300:]))
                continue
            if r.returncode != 0:
                bad.append("%s: the build failed: %s" % (why, r.stderr[-300:]))
                continue
            idx = json.load(open(os.path.join(app, "chicago-runoff-results.json")))
            notes = dict((g["id"], g.get("note", "")) for g in idx["groups"])
            got = dict(precincts=len(idx["precincts"]), parts=len(os.listdir(os.path.join(app, "chicago-runoff-results"))),
                       contests=len(idx["contests"]), ballots=idx["turnout"]["total"][1])
            if got != want:
                bad.append("%s: wanted %r, got %r" % (why, want, got))
            if idx["election"] != RUNOFF_ELECTION or idx["electionDate"] != "2027-04-06":
                bad.append("%s: the file is for the %r of %s" % (why, idx["election"], idx["electionDate"]))
            for g in set(c["group"] for c in idx["contests"]):
                if "February 23, 2027" not in notes.get(g, "") or "runoff" not in notes.get(g, ""):
                    bad.append("%s: group %s's note is %r" % (why, g, notes.get(g)))
            if notes.get("police-council"):
                bad.append("%s: a runoff file says how a police district council is chosen" % why)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if first_round_of("2027-04-06") != "2027-02-23" or first_round_of("2027-02-23") is not None:
        bad.append("first_round_of does not pair the 2027 runoff with its city election")
    for why in bad:
        print("build-chicago-election-results: selftest FAIL — " + why, file=sys.stderr)
    if bad:
        raise SystemExit(1)
    print("build-chicago-election-results: selftest OK — %d runoff builds: every precinct with a "
          "mayoral runoff, only the runoff wards' without one, and a race or turnout short of "
          "its ground refused" % len(cases))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--election-date")
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
    if args.selftest:
        return selftest()
    if not args.election_date:
        ap.error("--election-date is required")
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
    election = election_of(raw.get("election"), args.election_date)
    runoff = first_round_of(args.election_date) is not None

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
            # a runoff's turnout is checked against its races below
            if not runoff and set(precincts) != allowed:
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
    least = 1 if runoff else MIN_CONTESTS
    if len(contests) < least:
        fail("only %d contests; expected at least %d" % (len(contests), least))
    if runoff:
        turnout = runoff_turnout(contests, turnout, allowed)
    for c in contests:
        c["beyond"] = reaches_beyond(c)
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
    notes = group_notes(election, args.election_date)
    for g in groups:
        if g["id"] in notes:
            g["note"] = notes[g["id"]]
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
    # (a runoff's races were each held to their whole ground by runoff_turnout)
    if not runoff and len(set(part_of(k) for k in turnout["precincts"] if ":" not in k)) != 50:
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
