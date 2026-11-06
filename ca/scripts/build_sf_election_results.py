#!/usr/bin/env python3
"""
Build ca/data/app/election-results.json and its part files from the raw read
made by sf_election_results_scraper.py: every contest on the Department of
Elections' Statement of the Vote, each precinct's votes for each choice,
grouped by the map layer the contest is elected from, so the Election Results
card can offer the contests on the clicked precinct's ballot and the map can
fill each precinct by the choice with the most votes there.

THE KEY is the Election Precinct layer's own `prec_2022` (DataSF jg6x-23ig,
the 2022 precinct map the layer draws). The workbook writes a precinct as
"PCT 1101", and a precinct whose voters all vote by mail as "PCT 1103 MB";
both are the number. Measured on the 3 November 2026 results: the workbook
lists 514 precincts and the layer draws 514, the same numbers. The build fails
on a precinct the layer does not draw, or a precinct the layer draws that is
on no contest's sheet.

THE LAYER'S KEYS are read from DataSF at build time, through the same route
the tile mirror records (portal-mirror.json), after data.sf.gov's robots.txt.

GROUPS. GROUP_RULES places each contest by its title: statewide offices, the
appellate judges on the ballot to be kept or not, state propositions, the U.S.
House, State Senate, Assembly, BART director and Supervisor districts, the
city's other offices, and city measures. A title no rule places fails the
build.

BEYOND THE CITY. Statewide offices, judges and propositions reach past San
Francisco. A district contest reaches past it where its district does, which
DISTRICT_BEYOND records per district, measured 2026-11-06 against the city's
2020 county polygon (ca/data/app/population/ground.json) with shapely: Congress
11 lies 0.01% outside it, Assembly 17 0.01% and BART 8 0.02% (the edge of a
drawing), so they are the city's alone; Congress 15 lies 95% outside, Assembly
19 32%, State Senate 2, Assembly 12 and Assembly 18 more than 99%. A district
contest the table does not name fails the build, so a later election's new
district is measured before it ships rather than guessed.

RANKED-CHOICE CONTESTS. San Francisco elects its Supervisors, Assessor-Recorder
and Public Defender by ranked choice. The workbook counts first choices, so
those contests are named "(first choices)" and the card's note says the winner
comes from the Department's ranked-choice count.

WRITE-INS. Every sheet with a write-in column leaves it out of the sheet's own
Total Votes (measured 2026-11-06, on all twelve that have one), so the build
leaves it out too and each contest's numbers are the Department's own.

CHOICES. Ordered by a rule that cannot lean: Yes, then No, for a measure or a
judge; otherwise alphabetically by the name as the Department prints it, in
capitals. The party label after a name is left off. A choice's colour is that
position, never a party.

SEATS. The workbook does not say how many a contest elects. A contest whose
votes outnumber the precinct's voters cast in most of its precincts elects
several (the Board of Education and the College Board's full term), and the
shared writer marks it so the card says its shares are of votes and not of
voters; every other contest elects one. Most and not any, because the
Department's own counts put a few more votes in a contest than voters cast in a
handful of mail-ballot precincts (measured 2026-11-06: Proposition 1 in
precincts 1103 and 9147, 53 votes from 52 voters and 77 from 75).

TURNOUT. The first sheet gives each precinct's registered voters and voters
cast, which ship as its turnout.

UNOFFICIAL UNTIL CERTIFIED. The file carries `certified: false` and the time it
was read. When the Department certifies the results, run the build with
`--certified <date>`.

Usage:
    python3 ca/scripts/build_sf_election_results.py /tmp/sf_results_raw.json \
        --election-date 2026-11-03 [--certified YYYY-MM-DD] [--layer-keys keys.json]
"""

import argparse
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from election_results_common import ResultsError, write_results  # noqa: E402
from scraper_common import UA_HEADERS_ROSTER_BOT, make_fail, require_robots_once  # noqa: E402

fail = make_fail("build-sf-election-results")

APP_DATA = os.path.join(INSTANCE, "data", "app")
LAYER_SOURCE = "https://data.sf.gov/api/v3/views/jg6x-23ig/query.geojson"
MIN_LAYER_KEYS = 500
MIN_CONTESTS = 30
WRITE_IN = "Write-in"
RANKED = ("MEMBER, BOARD OF SUPERVISORS", "ASSESSOR-RECORDER", "PUBLIC DEFENDER")

# (group id, menu label, layer id or None, title pattern, beyond)
GROUP_RULES = [
    ("statewide", "Statewide offices", None,
     r"(GOVERNOR|LIEUTENANT GOVERNOR|SECRETARY OF STATE|CONTROLLER|TREASURER|ATTORNEY GENERAL|"
     r"INSURANCE COMMISSIONER|SUPERINTENDENT OF PUBLIC INSTRUCTION|BOARD OF EQUALIZATION MEMBER, DISTRICT \d+)", True),
    ("judges", "Judges (keep or not)", None, r"(ASSOCIATE|PRESIDING) JUSTICE .*", True),
    ("state-props", "State propositions", None, r"Proposition \d+", True),
    ("congress", "U.S. House", "congress", r"UNITED STATES REPRESENTATIVE, DISTRICT (\d+)", None),
    ("ca-senate", "State Senate", "ca-senate", r"STATE SENATOR, DISTRICT (\d+)", None),
    ("ca-assembly", "State Assembly", "ca-assembly", r"STATE ASSEMBLY MEMBER, DISTRICT (\d+)", None),
    ("bart", "BART Board", "bart-director", r"BART BOARD OF DIRECTORS, DISTRICT (\d+)", None),
    ("supervisor", "Board of Supervisors", "supervisor-district", r"MEMBER, BOARD OF SUPERVISORS, DISTRICT \d+", False),
    ("city", "City offices", None,
     r"(MEMBER, BOARD OF EDUCATION|TRUSTEE, COMMUNITY COLLEGE BOARD.*|ASSESSOR-RECORDER|PUBLIC DEFENDER)", False),
    ("measures", "City measures", None, r"Measure [A-Z]+", False),
]
GROUP_ORDER = [g[0] for g in GROUP_RULES]
QUESTION_GROUPS = ("judges", "state-props", "measures")

# Share of each district lying outside the city, measured 2026-11-06 (see the
# docstring): True where the contest reaches past San Francisco.
DISTRICT_BEYOND = {
    ("congress", "11"): False, ("congress", "15"): True,
    ("ca-senate", "2"): True,
    ("ca-assembly", "12"): True, ("ca-assembly", "17"): False,
    ("ca-assembly", "18"): True, ("ca-assembly", "19"): True,
    ("bart", "8"): False,
}

SMALL = {"of", "the", "and", "for"}
KEEP = {"BART": "BART"}


def group_of(title):
    for gid, _label, _layer, pattern, beyond in GROUP_RULES:
        m = re.fullmatch(pattern, title)
        if m:
            if beyond is None:
                key = (gid, m.group(1))
                if key not in DISTRICT_BEYOND:
                    fail("%s: DISTRICT_BEYOND does not say whether this district reaches past the city; "
                         "measure it and add it" % title)
                beyond = DISTRICT_BEYOND[key]
            return gid, beyond
    fail("%r falls into no group" % title)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def office_words(s):
    out = []
    for i, w in enumerate(s.split(" ")):
        core = w.strip(",")
        if core in KEEP:
            word = KEEP[core]
        elif core.lower() in SMALL and i:
            word = core.lower()
        else:
            word = "-".join(p[:1] + p[1:].lower() for p in core.split("-"))
        out.append(word + w[len(core):])
    return " ".join(out)


def contest_name(title):
    """An office in ordinary capitals, a name in brackets as printed."""
    m = re.fullmatch(r"(.*?)( \(.*\))?", title)
    office, person = m.group(1), m.group(2) or ""
    if office.startswith(("Proposition ", "Measure ")):
        return office
    name = office_words(office).replace("United States Representative", "U.S. Representative")
    name += person
    if title.startswith(RANKED):
        name += " (first choices)"
    return name


def choice_name(column):
    c = re.sub(r"\s*\((?:REP|DEM|LIB|GRN|PF|AI|NPP|PAF)\)$", "", column).strip()
    c = re.sub(r"^.* - (YES|NO)$", r"\1", c)
    return {"YES": "Yes", "NO": "No"}.get(c, c)


def choice_order(choice):
    if choice in ("Yes", "No"):
        return (0, 0 if choice == "Yes" else 1, "")
    return (1, 0, choice)


def precinct_key(label):
    m = re.fullmatch(r"PCT (\d{4})(?: MB)?", label)
    if not m:
        fail("%r is not a precinct the build can read" % label)
    return m.group(1)


def read_layer_keys(path=None):
    if path:
        keys = set(str(k) for k in json.load(open(path)))
    else:
        require_robots_once(LAYER_SOURCE, UA_HEADERS_ROSTER_BOT["User-Agent"], headers=UA_HEADERS_ROSTER_BOT)
        req = urllib.request.Request(LAYER_SOURCE, headers=dict(UA_HEADERS_ROSTER_BOT))
        with urllib.request.urlopen(req, timeout=120) as resp:
            doc = json.loads(resp.read())
        keys = set(str(f["properties"].get("prec_2022")) for f in doc.get("features") or [])
        keys.discard("None")
    if len(keys) < MIN_LAYER_KEYS:
        fail("the precinct layer gave %d keys, expected at least %d" % (len(keys), MIN_LAYER_KEYS))
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw")
    ap.add_argument("--election-date", required=True)
    ap.add_argument("--certified", help="the date the Department of Elections certified the results")
    ap.add_argument("--layer-keys", help="a JSON list of the layer's prec_2022 values, instead of reading DataSF")
    ap.add_argument("--app-data", default=APP_DATA, help="the app's data/app directory (default: ca/data/app)")
    args = ap.parse_args()

    raw = json.load(open(args.raw))
    allowed = read_layer_keys(args.layer_keys)
    turnout_rows = {}
    for label, vals in raw["turnout"].items():
        turnout_rows[precinct_key(label)] = vals
    stray = sorted(set(turnout_rows) - allowed)
    if stray:
        fail("precincts the layer does not draw: %s" % ", ".join(stray[:20]))
    reported = set()
    out = []
    used = set()
    for c in raw["contests"]:
        title = c["title"]
        group, beyond = group_of(title)
        name = contest_name(title)
        keep = [i for i, n in enumerate(c["columns"]) if n != WRITE_IN]
        if c.get("writeInsInTotal") and len(keep) != len(c["columns"]):
            fail("%s counts its write-ins into Total Votes, which this build does not expect" % title)
        names = [choice_name(c["columns"][i]) for i in keep]
        if len(set(names)) != len(names):
            fail("%s: two columns give the same choice %r" % (title, names))
        choices = sorted(names, key=choice_order)
        col_to = [choices.index(n) for n in names]
        question = set(choices) <= {"Yes", "No"}
        if question != (group in QUESTION_GROUPS):
            fail("%s: a %s placed in %s" % (title, "question" if question else "race", group))
        precincts = {}
        for label, vals in c["rows"].items():
            key = precinct_key(label)
            if key not in allowed:
                fail("%s: precinct %s is not one the layer draws" % (title, key))
            counts = [0] * len(choices)
            for j, i in enumerate(keep):
                counts[col_to[j]] += vals[i]
            precincts[key] = [sum(counts)] + counts
            reported.add(key)
        over = sum(1 for k, v in precincts.items() if v[0] > turnout_rows[k][1])
        seats = None if over * 2 > len(precincts) else 1
        total = [0] * (len(choices) + 1)
        for vals in precincts.values():
            total = [a + b for a, b in zip(total, vals)]
        base = "c" + re.sub(r"[^0-9]", "", c["sheet"])
        cid = base
        n = 1
        while cid in used:
            n += 1
            cid = "%s-%d" % (base, n)
        used.add(cid)
        out.append({"id": cid, "name": name, "group": group, "beyond": beyond,
                    "choices": choices, "total": total, "precincts": precincts, "seats": seats,
                    "_sort": (GROUP_ORDER.index(group), natural(name))})
    if len(out) < MIN_CONTESTS:
        fail("only %d contests; expected at least %d" % (len(out), MIN_CONTESTS))
    unreported = sorted(allowed - reported)
    if unreported:
        fail("%d precincts the layer draws are in no contest: %s" % (len(unreported), ", ".join(unreported[:20])))
    missing = sorted(allowed - set(turnout_rows))
    if missing:
        fail("%d precincts the layer draws have no turnout row: %s" % (len(missing), ", ".join(missing[:20])))
    out.sort(key=lambda c: c.pop("_sort"))

    turnout = {
        "total": [sum(v[0] for v in turnout_rows.values()), sum(v[1] for v in turnout_rows.values())],
        "precincts": turnout_rows,
    }
    groups = [{"id": g[0], "label": g[1], "layer": g[2]} for g in GROUP_RULES]
    stamp = {
        "election": "Consolidated General Election",
        "electionDate": args.election_date,
        "source": raw["source"],
        "read": raw["read"],
        "certified": bool(args.certified),
        "certifiedDate": args.certified or None,
        # The page's own "Last Update" time, so the daily job reads the
        # workbook again only when the Department has published.
        "boardAsOf": raw.get("asOf"),
    }
    note = ("Preliminary results as the San Francisco Department of Elections publishes them "
            "by precinct in its Statement of the Vote, until the Department certifies them "
            "(certified then reads true). Precinct keys are the Election Precinct layer's "
            "prec_2022; a mail-ballot precinct (\"MB\") is its number. Ranked-choice contests "
            "count first choices. Write-in votes are left out, as the Department's own totals "
            "leave them out. Turnout is [registered voters, voters cast]. Each precinct's counts "
            "are in a part file named for its first two digits (p + the digits). The layout is "
            "scripts/election_results_common.py's.")
    try:
        n, nparts = write_results(args.app_data, stamp, groups, turnout, out, lambda k: "p" + k[:2], note)
    except ResultsError as e:
        fail(str(e))
    by = {}
    for c in out:
        by[c["group"]] = by.get(c["group"], 0) + 1
    print("wrote %d contests (%s), %d part files under %s"
          % (n, ", ".join("%s %d" % (g, by[g]) for g in GROUP_ORDER if g in by), nparts,
             os.path.relpath(args.app_data)), file=sys.stderr)


if __name__ == "__main__":
    main()
