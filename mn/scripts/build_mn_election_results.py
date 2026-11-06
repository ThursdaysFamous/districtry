#!/usr/bin/env python3
"""
Build mn/data/app/election-results.json and its county files from the raw read
made by mn_election_results_scraper.py: every contest the Minnesota Secretary
of State reports by precinct for one election, each precinct's votes for each
choice, grouped by the map layer the contest is elected from, so the Election
Results card can offer the races on the clicked precinct's ballot by layer and
the map can fill each precinct by the choice with the most votes there.

THE PRECINCT KEY is the Voting Precinct layer's own `vtdid`
(data/app/mn-precincts.json, from the Secretary of State's statewide precinct
service): "27", then the county's FIPS code, then the four-digit precinct id
the results files print. The results files number counties 01 to 87 in
alphabetical order, and Minnesota's FIPS codes are the odd numbers in the same
order, so the FIPS code is 2 x id - 1 (Aitkin 01 -> 001, Yellow Medicine 87 ->
173). Measured on the 3 November 2026 files: all 4,105 precincts in
pctstats.txt are keys of the shipped layer and the layer has no other.

WHAT A CONTEST IS. A results row names an Office ID, an office name and a
District. The District field is empty for statewide and countywide offices and
is not unique across counties for county commissioner districts, so every
county office (its name begins "County", "Special Election for County" or
"COUNTY QUESTION") is one contest per county and is named with its county. An
Office ID and District that print two different office names (ISD #1's school
board and SSD #1's, both 5000 / 0001) are two contests.

CHOICES are listed in the order the files list them, which is the Candidate
Order Code's order (measured: no exception in 146,805 precinct-contests), with
WRITE-IN last as the office prints it. A choice's colour is that position,
never its party.

TURNOUT is [registered voters, ballots]: registered at 7 a.m. plus registered
on election day, and the total number who voted, from pctstats.txt. A precinct
whose county has not reported its statistics (the file's "Has Reported
Statistics" is 0; twelve counties on 5 November) has no turnout, and the card
leaves the line out.

UNOFFICIAL UNTIL CANVASSED. The file carries `certified: false` and the time it
was read. When the State Canvassing Board certifies the results, run the build
with `--certified <date>`.

THE CHECKS, before anything is written: every precinct key is one the layer
draws and every one the layer draws has turnout; every contest names at least
one choice and a group from GROUP_RULES (a contest no rule recognises fails the
build, so a new kind of contest is placed by a person rather than dropped); at
least MIN_CONTESTS contests; and every precinct's votes for a contest add up to
the office total the file prints beside them (for a constitutional amendment,
at most that total: its total is every ballot cast, since a blank ballot counts
against an amendment, and the card's shares are of the Yes and No votes).

Usage:
    python3 mn/scripts/build_mn_election_results.py /tmp/mn_results_raw.json \
        --election-date 2026-11-03 [--certified YYYY-MM-DD]
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from election_results_common import ResultsError, write_results  # noqa: E402
from scraper_common import make_fail  # noqa: E402

fail = make_fail("build-mn-election-results")

APP_DATA = os.path.join(INSTANCE, "data", "app")
PRECINCTS = os.path.join(APP_DATA, "mn-precincts.json")
MIN_CONTESTS = 500
PART_SIZE = 60
EXPECTED_PRECINCTS = 4105

# (group id, label shown in the race menu, the map layer it is elected from or
# None, a pattern the office name matches once "(Elect N)" is taken off).
# First match wins, so the narrow patterns come first. A group with no layer
# is elected statewide, by a court's whole ground, or by a body this map does
# not draw.
SPECIAL = r"^(?:Special Election for )?"
GROUP_RULES = [
    ("statewide", "Statewide offices", None,
     r"^(U\.S\. Senator|Governor & Lt Governor|Secretary of State|Attorney General|State Auditor)$"),
    ("us-house", "U.S. House", "us-house", r"^U\.S\. Representative District \d+$"),
    ("mn-senate", "Minnesota Senate", "mn-senate", r"^State Senator District \d+$"),
    ("mn-house", "Minnesota House", "mn-house", r"^State Representative District \d+[AB]$"),
    ("appellate", "Supreme Court and Court of Appeals", None,
     r"^(Associate Justice - Supreme Court|Chief Justice - Supreme Court|Judge - Court of Appeals) \d+$"),
    ("district-court", "District court judges", "mn-judicial-district",
     r"^Judge - \d+(st|nd|rd|th) District Court \d+$"),
    ("county", "County offices", "county",
     r"^County (Attorney|Auditor|Auditor/Treasurer|Treasurer|Recorder|Sheriff|Surveyor|Coroner)$"),
    ("county-commissioner", "County commissioners", "county-commissioner",
     SPECIAL + r"County Commissioner District \d+$"),
    ("county-park", "County park commissioners", None, r"^County Park Commissioner District \d+$"),
    ("conservation", "Soil and water supervisors", "conservation-district",
     SPECIAL + r"Soil and Water Supervisor District \d+$"),
    ("city-ward", "City council by ward or district", "city-ward",
     SPECIAL + r"Council Member (Ward [0-9A-Z]+|Wards \d+ & \d+|District \d+|Precinct \d+|Section [IVX]+)$"),
    ("city", "Mayor and city offices", "municipality",
     SPECIAL + r"(Mayor|Council Member( At Large| Seat \d+)?|City Clerk( - Treasurer)?|City Treasurer|"
               r"Board of Public Works|Utility Board Commissioner)$"),
    ("town", "Town offices", "county-subdivision",
     SPECIAL + r"(Town Supervisor( Seat [A-Z0-9]+| At Large)?|Town Clerk( - Treasurer)?|Town Treasurer)$"),
    ("school-board-district", "School board by district", "school-board-district",
     SPECIAL + r"School Board Member (District \d+|\w+ District)$"),
    ("school-board", "School boards", "school-district-unified",
     SPECIAL + r"School Board Member( At Large| Position \d+)?$"),
    ("other-local", "Hospital and sanitary districts", None,
     SPECIAL + r"(Hospital District Board Member.*|Sanitary District Board Member)$"),
    ("questions", "Ballot questions", None,
     r"^(CONSTITUTIONAL AMENDMENT|COUNTY QUESTION|CITY QUESTION|SCHOOL DISTRICT QUESTION|TOWNSHIP QUESTION) \d+$"),
]
GROUP_ORDER = [g[0] for g in GROUP_RULES]
COUNTY_SCOPED = re.compile(r"^(County |Special Election for County |COUNTY QUESTION)")
ELECT_RE = re.compile(r"\s*\(Elect (\d+)\)")
PLACE_RE = re.compile(r"\s*\(([^()]*)\)")


def group_of(office):
    """The group of an office name with its parentheticals taken off."""
    bare = PLACE_RE.sub("", office).strip()
    for gid, _label, _layer, pattern in GROUP_RULES:
        if re.search(pattern, bare):
            return gid
    fail("no group recognises office %r; add a rule to GROUP_RULES" % office)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def layer_keys():
    doc = json.load(open(PRECINCTS))
    keys = {}
    counties = {}
    for f in doc["features"]:
        p = f["properties"]
        keys[str(p["vtdid"])] = p
        counties[str(p["vtdid"])[2:5]] = str(p.get("countyname") or "").strip()
    if len(keys) != EXPECTED_PRECINCTS:
        fail("the precinct layer has %d precincts, expected %d" % (len(keys), EXPECTED_PRECINCTS))
    return keys, counties


def key_of(county_id, precinct):
    return "27%03d%s" % (int(county_id) * 2 - 1, precinct)


def build_contests(rows, county_names, source_tag):
    """Group results rows into contests: {id: contest} in first-seen order."""
    contests = {}
    for r in rows:
        office = r["office"]
        group = group_of(office)
        scoped = bool(COUNTY_SCOPED.match(office))
        ident = (source_tag, r["officeId"], r["district"], office, r["county"] if scoped else "")
        c = contests.get(ident)
        if c is None:
            m = ELECT_RE.search(office)
            name = ELECT_RE.sub("", office).strip()
            if scoped:
                name += " (%s County)" % county_names[r["county"]]
            c = contests[ident] = {
                "ident": ident, "name": name, "group": group,
                "seats": int(m.group(1)) if m else 1,
                "choices": [], "orders": [], "precincts": {}, "officeVotes": {},
            }
        if r["order"] not in c["orders"]:
            c["orders"].append(r["order"])
            c["choices"].append(r["candidate"])
        k = key_of(r["county"], r["precinct"])
        counts = c["precincts"].setdefault(k, {})
        if r["order"] in counts:
            fail("%s: precinct %s lists choice %s twice" % (office, k, r["order"]))
        counts[r["order"]] = r["votes"]
        prior = c["officeVotes"].setdefault(k, r["officeVotes"])
        if prior != r["officeVotes"]:
            fail("%s: precinct %s prints two office totals (%d, %d)" % (office, k, prior, r["officeVotes"]))
    return list(contests.values())


def contest_id(c, used):
    tag, office_id, district, _office, county = c["ident"]
    base = ("L" if tag == "local" else "") + office_id
    if district:
        base += "-" + district
    if county:
        base += "-c" + county
    cid, n = base, 1
    while cid in used:
        n += 1
        cid = "%s-%d" % (base, n)
    used.add(cid)
    return cid


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw")
    ap.add_argument("--election-date", required=True)
    ap.add_argument("--certified", help="the date the State Canvassing Board certified the results")
    ap.add_argument("--app-data", default=APP_DATA, help="the app's data/app directory (default: mn/data/app)")
    args = ap.parse_args()

    raw = json.load(open(args.raw))
    allowed, by_fips = layer_keys()
    county_names = dict(("%02d" % i, by_fips.get("%03d" % (i * 2 - 1), "")) for i in range(1, 88))
    if any(not v for v in county_names.values()):
        fail("the precinct layer names no county for ids %s"
             % ", ".join(k for k, v in county_names.items() if not v))

    turnout = {"precincts": {}}
    reg_total = cast_total = 0
    for s in raw["stats"]:
        k = key_of(s["county"], s["precinct"])
        if k not in allowed:
            fail("pctstats.txt precinct %s-%s (%s, key %s) is not on the precinct layer"
                 % (s["county"], s["precinct"], s["name"], k))
        if s["reported"]:
            vals = [s["registered7am"] + s["registeredToday"], s["voted"]]
            reg_total += vals[0]
            cast_total += vals[1]
        else:
            vals = [None, None]
        turnout["precincts"][k] = vals
    if set(turnout["precincts"]) != set(allowed):
        fail("pctstats.txt covers %d of the layer's %d precincts"
             % (len(turnout["precincts"]), len(allowed)))
    turnout["total"] = [reg_total, cast_total]

    grouped = build_contests(raw["results"], county_names, "state") + \
        build_contests(raw["local"], county_names, "local")
    contests = []
    used = set()
    for c in grouped:
        precincts = {}
        for k, counts in c["precincts"].items():
            if set(counts) != set(c["orders"]):
                fail("%s: precinct %s lists %d of the contest's %d choices"
                     % (c["name"], k, len(counts), len(c["orders"])))
            vals = [counts[o] for o in c["orders"]]
            # A constitutional amendment's office total is every ballot cast,
            # because a ballot left blank counts against it (Minn. Const. art.
            # IX, sec. 1), so its Yes and No add up to less; every other
            # office's total is exactly its choices' sum.
            amendment = c["name"].startswith("CONSTITUTIONAL AMENDMENT")
            if sum(vals) > c["officeVotes"][k] or (not amendment and sum(vals) != c["officeVotes"][k]):
                fail("%s: precinct %s's choices add up to %d, the office total is %d"
                     % (c["name"], k, sum(vals), c["officeVotes"][k]))
            precincts[k] = [sum(vals)] + vals
        total = [0] * (len(c["choices"]) + 1)
        for vals in precincts.values():
            total = [a + b for a, b in zip(total, vals)]
        contests.append({
            "id": contest_id(c, used), "name": c["name"], "group": c["group"],
            "beyond": False, "choices": c["choices"], "total": total,
            "precincts": precincts, "seats": c["seats"],
            # the ballot's order within a group: the office's own id (U.S.
            # Senator 0102 before Governor 0331), then the name
            "_sort": (GROUP_ORDER.index(c["group"]), c["ident"][1], natural(c["name"])),
        })
    if len(contests) < MIN_CONTESTS:
        fail("only %d contests; expected at least %d" % (len(contests), MIN_CONTESTS))
    contests.sort(key=lambda c: c.pop("_sort"))

    groups = [{"id": g[0], "label": g[1], "layer": g[2]} for g in GROUP_RULES]
    stamp = {
        "election": "General Election",
        "electionDate": args.election_date,
        "source": raw["source"],
        "read": raw["read"],
        "certified": bool(args.certified),
        "certifiedDate": args.certified or None,
    }
    note = ("Unofficial results as the Minnesota Secretary of State publishes them "
            "(allracesbyprecinct.txt, localPrct.txt and pctstats.txt), until the State "
            "Canvassing Board certifies them (certified then reads true). Precinct keys are "
            "the Voting Precinct layer's vtdid: 27, the county FIPS code, and the office's "
            "four-digit precinct id. Each precinct's counts are in a part file named for "
            "its county (c + the county FIPS code) and a run of up to 60 of that county's "
            "precincts in key order. The layout is scripts/election_results_common.py's.")
    # A click reads one part file, so a county's precincts are split into runs
    # of at most PART_SIZE: Hennepin's 432 precincts as one file measured
    # 422 KB (127 KB gzipped) a click, against Chicago's 12 KB.
    part = {}
    by_county = {}
    for k in sorted(turnout["precincts"]):
        by_county.setdefault(k[2:5], []).append(k)
    for fips, keys in by_county.items():
        for i, k in enumerate(keys):
            part[k] = "c%s-%d" % (fips, i // PART_SIZE + 1)
    try:
        n, nparts = write_results(args.app_data, stamp, groups, turnout, contests,
                                  part.get, note)
    except ResultsError as e:
        fail(str(e))
    if nparts != len(set(part.values())):
        fail("wrote %d part files, expected %d" % (nparts, len(set(part.values()))))
    by = {}
    for c in contests:
        by[c["group"]] = by.get(c["group"], 0) + 1
    print("wrote %d contests (%s), turnout for %d precincts and %d part files under %s"
          % (n, ", ".join("%s %d" % (g, by[g]) for g in GROUP_ORDER if g in by),
             len(turnout["precincts"]), nparts, os.path.relpath(args.app_data)), file=sys.stderr)


if __name__ == "__main__":
    main()
