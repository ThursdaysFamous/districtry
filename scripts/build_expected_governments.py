#!/usr/bin/env python3
"""
Emit docs/expected-governments.json — every general-purpose local government of
25,000 people or more in each state an app serves, measured from the Census.

WHY THIS FILE EXISTS. `docs/DONE_STANDARD.md` sets a fourth test, Covered, and
one of its thirteen entries has a SIZE in it: the governing body of every local
government above 25,000 people that governs its residents generally. Nothing in
this tree knows how many people live in a municipality, so that entry cannot be
scored from the tree alone — and `scripts/build_eam_status.py`, which scores it,
is stdlib-only and offline by design. So the population question is measured
ONCE, here, against the Census, and committed with its date, its query and its
method; the report then joins each app's own rosters against it offline.

WHAT COUNTS, AND WHY IT IS A RULE RATHER THAN A LIST OF STATES. The standard's
test is GENERAL PURPOSE: the body that governs a resident because nothing
smaller does. Every incorporated city and village qualifies. A county
subdivision qualifies only where that state's law makes the town or township
the general-purpose government outside incorporated places — a New York town
and a Michigan township do, an Illinois township does not (roads, assessment
and general assistance, while an unincorporated Illinois resident is governed
generally by the county; Illinois townships are owed under the standard's entry
9 instead). `SUBDIVISION_IS_GENERAL_PURPOSE` carries that fact of law per state
and the build REFUSES rather than guessing: a state whose rule is not recorded
and whose subdivisions clear the line stops the run, so a township crossing
25,000 in a state nobody has ruled on cannot be silently included or silently
dropped.

MEASURED, NOT ASSERTED. The source is TIGERweb's Census 2020 service, which
carries the same `POP100` the decennial published; `api.census.gov` would
need a key this project does not hold. Robots is read through the fleet's one
reader with the client that fetches, before the first request.

This is an operator step. It needs the network and is NOT in CI; the
consistency gate on its output lives in `build_eam_status.py`, which is the
only reader, because two readers of one question is where this fleet's
recurring defect starts.
"""

import argparse
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import robots_policy  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "docs", "expected-governments.json")

UA = "districtry/1.0 (+https://districtry.com/)"
SERVICE = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
           "tigerWMS_Census2020/MapServer")
PLACES_LAYER = 26          # Incorporated Places
SUBDIVISIONS_LAYER = 20    # County Subdivisions
FLOOR = 25000

# The state each app answers for. A city app is not here: San Francisco's own
# city tier is the whole app, which the report states rather than measures.
STATE_FIPS = {"il": "17", "wi": "55", "ia": "19", "mi": "26",
              "mn": "27", "ky": "21", "ny": "36"}

# Is a county subdivision the GENERAL-PURPOSE government for residents outside
# incorporated places in this state? A fact of that state's law, recorded with
# what it rests on. None means nobody has ruled, which is safe only while no
# subdivision in that state clears the floor — the build checks that.
SUBDIVISION_IS_GENERAL_PURPOSE = {
    "ny": True,   # A New York town governs everyone outside a village or city.
    "mi": True,   # A Michigan township likewise, charter or general law.
    "il": False,  # Limited purpose; the county governs unincorporated residents.
    "wi": None,   # Wisconsin towns are general purpose, but none reaches the
                  # floor, so the question has not had to be settled here.
    "mn": None,   # Same: no Minnesota township reaches the floor.
    "ia": None,   # Same.
    "ky": None,   # Kentucky has no township tier at all.
}


def fail(msg):
    print("build-expected-governments: FAIL — %s" % msg)
    sys.exit(1)


def query(layer, where):
    params = {
        "where": where,
        "outFields": "GEOID,NAME,BASENAME,POP100,LSADC,FUNCSTAT",
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": "1000",
    }
    url = "%s/%d/query?%s" % (SERVICE, layer, urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        doc = json.load(resp)
    # AN API ERROR IS NOT AN EMPTY ANSWER. Reading `features` with a default
    # turns a rejected field list into "this state has no such unit", which is
    # a confident, plausible answer assembled entirely out of a failure.
    if "error" in doc:
        fail("TIGERweb layer %d rejected the query: %r" % (layer, doc["error"]))
    if "features" not in doc:
        fail("TIGERweb layer %d answered without a features key: %r"
             % (layer, sorted(doc)))
    return [f["attributes"] for f in doc["features"]]


def build():
    gate = robots_policy.RobotsGate(session=None, user_agent=UA)
    allowed, why = gate.allows("%s/%d/query" % (SERVICE, PLACES_LAYER))
    if not allowed:
        fail("robots.txt refuses this client at the Census service: %s" % why)
    print("build-expected-governments: robots — %s" % why)

    units = {}
    for tag in sorted(STATE_FIPS):
        fips = STATE_FIPS[tag]
        rows = []
        for attrs in query(PLACES_LAYER,
                           "STATE='%s' AND POP100>=%d" % (fips, FLOOR)):
            rows.append(dict(geoid=attrs["GEOID"], name=attrs["NAME"],
                             pop=int(attrs["POP100"]), kind="place",
                             lsadc=str(attrs["LSADC"]).strip()))
        # FUNCSTAT='A' is an ACTIVE government. An inactive subdivision is a
        # census shape with no board to name, so counting it would owe a state
        # a roster for a body that does not meet.
        subs = query(SUBDIVISIONS_LAYER,
                     "STATE='%s' AND POP100>=%d AND FUNCSTAT='A'"
                     % (fips, FLOOR))
        rule = SUBDIVISION_IS_GENERAL_PURPOSE.get(tag, "missing")
        if subs and rule == "missing":
            fail("%s: %d county subdivision(s) clear %d people and no rule of "
                 "law is recorded for this state in "
                 "SUBDIVISION_IS_GENERAL_PURPOSE. Record whether that state's "
                 "township or town is the general-purpose government outside "
                 "incorporated places; do not guess."
                 % (tag, len(subs), FLOOR))
        if subs and rule is None:
            fail("%s: %d county subdivision(s) now clear %d people, and this "
                 "state's rule was recorded as 'does not arise'. It arises "
                 "now. Settle whether that unit is the general-purpose "
                 "government and record it."
                 % (tag, len(subs), FLOOR))
        if rule:
            for attrs in subs:
                rows.append(dict(geoid=attrs["GEOID"], name=attrs["NAME"],
                                 pop=int(attrs["POP100"]), kind="subdivision",
                                 lsadc=str(attrs["LSADC"]).strip()))
        rows.sort(key=lambda r: (-r["pop"], r["geoid"]))
        units[tag] = rows
        print("build-expected-governments: %s — %d unit(s) at %d+ (%d place, "
              "%d subdivision; %d subdivision(s) excluded by state law)"
              % (tag, len(rows), FLOOR,
                 sum(1 for r in rows if r["kind"] == "place"),
                 sum(1 for r in rows if r["kind"] == "subdivision"),
                 0 if rule else len(subs)))

    return {
        "measured": datetime.date.today().isoformat(),
        "floor": FLOOR,
        "source": ("U.S. Census Bureau TIGERweb, tigerWMS_Census2020 — layer "
                   "%d (Incorporated Places) and layer %d (County "
                   "Subdivisions, FUNCSTAT='A'); POP100 is the 2020 decennial "
                   "count." % (PLACES_LAYER, SUBDIVISIONS_LAYER)),
        "service": SERVICE,
        "what_counts": ("Every general-purpose local government of %d people "
                        "or more: all incorporated places, plus county "
                        "subdivisions only in states whose law makes the town "
                        "or township the general-purpose government outside "
                        "incorporated places." % FLOOR),
        "subdivision_is_general_purpose": {
            tag: SUBDIVISION_IS_GENERAL_PURPOSE[tag]
            for tag in sorted(SUBDIVISION_IS_GENERAL_PURPOSE)},
        "built_by": "scripts/build_expected_governments.py",
        "read_by": "scripts/build_eam_status.py",
        "units": units,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_PATH,
                    help="where to write (default docs/expected-governments.json)")
    args = ap.parse_args()
    doc = build()
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    total = sum(len(v) for v in doc["units"].values())
    print("build-expected-governments: OK — %d unit(s) across %d state(s), "
          "written to %s" % (total, len(doc["units"]),
                             os.path.relpath(args.out, REPO_ROOT)))


if __name__ == "__main__":
    main()
