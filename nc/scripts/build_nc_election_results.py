#!/usr/bin/env python3
"""
Build nc/data/app/election-results.json and its county files from the raw read
made by nc_election_results_scraper.py: every contest the North Carolina State
Board of Elections reports by precinct for one election, each precinct's votes
for each choice, grouped by the map layer the contest is elected from, so the
Election Results card can offer the races on the clicked precinct's ballot by
layer and the map can fill each precinct by the choice with the most votes
there.

THE PRECINCT KEY is the Voting Precinct layer's own `key`
(data/app/nc-precincts.json, the State Board's precinct shapes): the county's
FIPS code, a hyphen, and the precinct code the results file prints (Wake's
01-42 is 37183-01-42). The file names counties in capitals ("NEW HANOVER"), and
the layer's own county names give each one's FIPS code. Measured on the 3
November 2026 file: 2,626 precincts, 2,625 of them the layer's 2,625 keys; the
one left over, Henderson County's CV, is a precinct drawn after the layer's
shapes, and its votes are counted with the units below.

UNITS THAT ARE NOT PRECINCTS ("Real Precinct" N: ABSENTEE, PROVISIONAL,
TRANSFER and, in some counties, each early voting site) and any precinct the
layer does not draw are summed into each contest's `outside` counts: in its
total, never in a precinct's colour, and the card says what share of the race
the colours leave out. On the 2026 file they held 27% of all votes, because
many counties count early votes by site rather than by precinct. More than
MAX_UNDRAWN precincts missing from the layer fails the build, since that means
the layer and the Board's precincts have parted.

WHAT A CONTEST IS. A state-run contest (Contest Type S) is one Contest Group ID
statewide. A county-run contest (C) numbers its group ids per county, and one
that crosses a county line (Raleigh's mayor in Wake and Durham) is printed once
per county under the same name, so a county-run contest is its name, and its
pieces are summed.

CHOICES. The file lists rows in no ballot order (a precinct's U.S. Senate rows
come in a different order in each county), so the choices are ordered by a rule
that cannot lean: For or Yes, then Against or No, for a question; otherwise by
surname, with Write-In (Miscellaneous) last. A choice's colour is that
position, never its party. A line with no choice is a seat nobody filed for and
is left out; a contest with no choice left is left out and named in the output.

SEATS come from the file's own Vote For column.

TURNOUT. The file reports votes and not ballots or registered voters, so each
precinct's turnout is [null, null] and the card says nothing about turnout.

UNOFFICIAL UNTIL CANVASSED. The file carries `certified: false` and the time it
was read. When the State Board certifies the results, run the build with
`--certified <date>`.

THE CHECKS, before anything is written: every precinct the layer draws appears
in the file and every key written is one the layer draws; every contest names
one Vote For and one group from GROUP_RULES (a contest no rule recognises fails
the build, so a new kind of contest is placed by a person rather than dropped);
a state-run group id names one contest; every precinct lists each of its
contest's choices once; at least MIN_CONTESTS contests.

Usage:
    python3 nc/scripts/build_nc_election_results.py /tmp/nc_results_raw.json \
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

fail = make_fail("build-nc-election-results")

APP_DATA = os.path.join(INSTANCE, "data", "app")
PRECINCTS = os.path.join(APP_DATA, "nc-precincts.json")
MIN_CONTESTS = 300
PART_SIZE = 60
MAX_UNDRAWN = 10
EXPECTED_COUNTIES = 100

COUNTY_WORDS = r"(?:COUNTY |COUNTY SCHOOLS |SCHOOLS |CITY SCHOOLS |-[A-Z]+ SCHOOLS |-[A-Z]+ )?"
# (group id, label shown in the race menu, the map layer it is elected from or
# None, a pattern the contest name matches). First match wins, so the narrow
# patterns come first. A group with no layer is elected statewide, by a court's
# or prosecutor's whole ground, or by a body this map does not draw.
GROUP_RULES = [
    ("statewide", "Statewide offices", None, r"^US SENATE$"),
    ("us-house", "U.S. House", "us-house", r"^US HOUSE OF REPRESENTATIVES DISTRICT \d+$"),
    ("nc-senate", "North Carolina Senate", "nc-senate", r"^NC STATE SENATE DISTRICT \d+$"),
    ("nc-house", "North Carolina House", "nc-house", r"^NC HOUSE OF REPRESENTATIVES DISTRICT \d+$"),
    ("appellate", "Supreme Court and Court of Appeals", None,
     r"^NC (SUPREME COURT (CHIEF|ASSOCIATE) JUSTICE|COURT OF APPEALS JUDGE) SEAT \d+( \(UNEXPIRED\))?$"),
    ("superior-court", "Superior court judges", "nc-superior-court",
     r"^NC SUPERIOR COURT JUDGE DISTRICT \d+[A-Z]? SEAT \d+( \(UNEXPIRED\))?$"),
    ("district-court", "District court judges", "nc-district-court",
     r"^NC DISTRICT COURT JUDGE DISTRICT \d+[A-Z]? SEAT \d+( \(UNEXPIRED\))?$"),
    ("district-attorney", "District attorneys", None, r"^DISTRICT ATTORNEY DISTRICT \d+[A-Z]?$"),
    ("questions", "Ballot questions", None,
     r"(^CONSTITUTIONAL AMENDMENT - |REFERENDUM$| (MIXED BEVERAGE|MALT BEVERAGE|UNFORTIFIED WINE|"
     r"ABC STORE|FIRE TAX) ELECTION$)"),
    ("county", "County offices", "county",
     r"^[A-Z .'-]+ COUNTY (SHERIFF|CLERK OF SUPERIOR COURT|REGISTER OF DEEDS|CORONER|TAX COLLECTOR)$"),
    ("county-commissioner", "County commissioners", None,
     r"^[A-Z .'-]+ (COUNTY )?(BOARD|BD) OF COMMISSIONERS\b"),
    ("school-board", "School boards", None, r"^[A-Z .'-]+ BOARD OF EDUCATION\b"),
    ("conservation", "Soil and water supervisors", None, r"SOIL AND WATER CONSERVATION DISTRICT"),
    ("city-ward", "City council by ward or district", "city-ward",
     r"^(CITY|TOWN|VILLAGE) OF [A-Z .'-]+ (CITY |TOWN |VILLAGE )?(COUNCIL|COMMISSIONER)( MEMBER)? "
     r"((EAST|WEST|NORTH|SOUTH) )?(WARD|DISTRICT) ?[0-9A-Z]*$"),
    ("city", "Mayor and town offices", "municipality",
     r"^((CITY|TOWN|VILLAGE) OF [A-Z .'-]+|CHIMNEY ROCK VILLAGE) "
     r"(MAYOR|((CITY|TOWN|VILLAGE) )?(COUNCIL|COUNCILMAN|COMMISSIONER|BOARD OF COMMISSIONERS|"
     r"BOARD OF ALDERMEN|ALDERMEN)( MEMBER)?( AT-LARGE)?)( \(UNEXPIRED\))?$"),
    ("other-local", "Sanitary districts", None, r"SANITARY"),
]
GROUP_ORDER = [g[0] for g in GROUP_RULES]
SUFFIXES = {"JR", "JR.", "SR", "SR.", "II", "III", "IV"}
FIRST = {"FOR": 0, "YES": 0, "AGAINST": 1, "NO": 1}


def group_of(name):
    for gid, _label, _layer, pattern in GROUP_RULES:
        if re.search(pattern, name):
            return gid
    fail("no group recognises contest %r; add a rule to GROUP_RULES" % name)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def choice_order(choice):
    """Questions For/Yes then Against/No; people by surname; a write-in last."""
    up = choice.upper()
    if up in FIRST:
        return (0, FIRST[up], "")
    if up.startswith("WRITE-IN"):
        return (2, 0, up)
    words = [w for w in re.sub(r"\([^)]*\)", " ", up).replace(",", " ").split() if w not in SUFFIXES]
    return (1, 0, (words[-1] if words else up) + " " + up)


def layer_keys():
    doc = json.load(open(PRECINCTS))
    keys = {}
    fips = {}
    for f in doc["features"]:
        p = f["properties"]
        keys[str(p["key"])] = p
        name = re.sub(r" COUNTY$", "", str(p["county"]).upper().strip())
        fips[name] = str(p["countyFips"])
    if len(fips) != EXPECTED_COUNTIES:
        fail("the precinct layer names %d counties, expected %d" % (len(fips), EXPECTED_COUNTIES))
    return keys, fips


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw")
    ap.add_argument("--election-date", required=True)
    ap.add_argument("--certified", help="the date the State Board of Elections certified the results")
    ap.add_argument("--app-data", default=APP_DATA, help="the app's data/app directory (default: nc/data/app)")
    args = ap.parse_args()

    raw = json.load(open(args.raw))
    cols = raw["columns"]
    allowed, fips = layer_keys()

    contests = {}
    seen_real = set()
    undrawn = set()
    for row in raw["rows"]:
        r = dict(zip(cols, row))
        if r["county"] not in fips:
            fail("county %r is not one the precinct layer names" % r["county"])
        name = r["contest"]
        ident = ("S", r["groupId"]) if r["type"] == "S" else ("C", name)
        c = contests.get(ident)
        if c is None:
            c = contests[ident] = {"ident": ident, "name": name, "group": group_of(name),
                                   "seats": r["voteFor"], "choices": {}, "precincts": {},
                                   "outside": {}}
        if c["name"] != name:
            fail("state contest %s is named both %r and %r" % (r["groupId"], c["name"], name))
        if c["seats"] != r["voteFor"]:
            fail("%s: Vote For is both %d and %d" % (name, c["seats"], r["voteFor"]))
        if not r["choice"]:
            continue
        c["choices"][r["choice"]] = True
        key = "%s-%s" % (fips[r["county"]], r["precinct"])
        if r["real"]:
            seen_real.add(key)
        if r["real"] and key in allowed:
            counts = c["precincts"].setdefault(key, {})
            if r["choice"] in counts:
                fail("%s: precinct %s lists %r twice" % (name, key, r["choice"]))
            counts[r["choice"]] = r["votes"]
        else:
            if r["real"]:
                undrawn.add(key)
            c["outside"][r["choice"]] = c["outside"].get(r["choice"], 0) + r["votes"]

    missing = set(allowed) - seen_real
    if missing:
        fail("%d precincts the layer draws are not in the file: %s"
             % (len(missing), ", ".join(sorted(missing)[:10])))
    if len(undrawn) > MAX_UNDRAWN:
        fail("%d precincts in the file are not on the layer (at most %d allowed): %s"
             % (len(undrawn), MAX_UNDRAWN, ", ".join(sorted(undrawn)[:20])))

    out = []
    used = set()
    dropped = []
    for c in contests.values():
        choices = sorted(c["choices"], key=choice_order)
        if not choices:
            dropped.append(c["name"])
            continue
        precincts = {}
        for k, counts in c["precincts"].items():
            if set(counts) != set(choices):
                fail("%s: precinct %s lists %d of the contest's %d choices"
                     % (c["name"], k, len(counts), len(choices)))
            vals = [counts[ch] for ch in choices]
            precincts[k] = [sum(vals)] + vals
        if not precincts:
            dropped.append(c["name"])
            continue
        outside = [c["outside"].get(ch, 0) for ch in choices]
        outside = [sum(outside)] + outside
        total = list(outside)
        for vals in precincts.values():
            total = [a + b for a, b in zip(total, vals)]
        if c["ident"][0] == "S":
            base = "s" + c["ident"][1]
        else:
            base = "c" + re.sub(r"[^a-z0-9]+", "-", c["name"].lower()).strip("-")[:48]
        cid, n = base, 1
        while cid in used:
            n += 1
            cid = "%s-%d" % (base, n)
        used.add(cid)
        entry = {
            "id": cid, "name": c["name"], "group": c["group"], "beyond": False,
            "choices": choices, "total": total, "precincts": precincts, "seats": c["seats"],
            "_sort": (GROUP_ORDER.index(c["group"]), natural(c["name"])),
        }
        if outside[0]:
            entry["outside"] = outside
        out.append(entry)
    if len(out) < MIN_CONTESTS:
        fail("only %d contests; expected at least %d" % (len(out), MIN_CONTESTS))
    out.sort(key=lambda c: c.pop("_sort"))

    turnout = {"total": [None, None], "precincts": dict((k, [None, None]) for k in allowed)}
    groups = [{"id": g[0], "label": g[1], "layer": g[2]} for g in GROUP_RULES]
    stamp = {
        "election": "General Election",
        "electionDate": args.election_date,
        "source": raw["source"],
        "read": raw["read"],
        "certified": bool(args.certified),
        "certifiedDate": args.certified or None,
    }
    note = ("Unofficial results as the North Carolina State Board of Elections publishes "
            "them by precinct (results_pct), until the State Board certifies them (certified "
            "then reads true). Precinct keys are the Voting Precinct layer's key: the county "
            "FIPS code, a hyphen and the Board's precinct code. Absentee, provisional, transfer "
            "and early voting units, and any precinct the layer does not draw, are in each "
            "contest's outside counts. The file reports no turnout. Each precinct's counts are "
            "in a part file named for its county (c + the county FIPS code) and a run of up to "
            "60 of that county's precincts in key order. The layout is "
            "scripts/election_results_common.py's.")
    part = {}
    by_county = {}
    for k in sorted(allowed):
        by_county.setdefault(k[2:5], []).append(k)
    for cf, keys in by_county.items():
        for i, k in enumerate(keys):
            part[k] = "c%s-%d" % (cf, i // PART_SIZE + 1)
    try:
        n, nparts = write_results(args.app_data, stamp, groups, turnout, out, part.get, note)
    except ResultsError as e:
        fail(str(e))
    by = {}
    for c in out:
        by[c["group"]] = by.get(c["group"], 0) + 1
    outside_votes = sum(c.get("outside", [0])[0] for c in out)
    all_votes = sum(c["total"][0] for c in out)
    print("wrote %d contests (%s), %d part files under %s; %.1f%% of votes counted outside "
          "a drawn precinct; undrawn precincts: %s; left out with no choice: %s"
          % (n, ", ".join("%s %d" % (g, by[g]) for g in GROUP_ORDER if g in by), nparts,
             os.path.relpath(args.app_data), 100.0 * outside_votes / max(all_votes, 1),
             ", ".join(sorted(undrawn)) or "none", "; ".join(dropped) or "none"), file=sys.stderr)


if __name__ == "__main__":
    main()
