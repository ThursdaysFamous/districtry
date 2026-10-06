#!/usr/bin/env python3
"""Write ny/data/app/ny-supervisor-members.json from the scraper's output.

WHAT THIS ANSWERS. In a New York board-of-supervisors county the county's
governing body is the towns' and cities' own supervisors sitting together, so
naming them answers the county governing body over ground this instance
already draws — the statewide cities-and-towns fabric. There is no district to
draw and none is invented.

THE SHAPE IS unit -> [people], NEVER unit -> person. New York County Law lets
a town or city elect more than one supervisor and Saratoga seats two for the
town of Clifton Park and two for the city of Saratoga Springs, so a one-name
key would drop a real member while reading as complete.

FOUR REFUSALS, each one a count the county itself publishes or the fabric
itself holds:

  - the seat count must come out at what the county's own page states;
  - every unit named must be a unit of that county in this instance's own
    cities-and-towns fabric, which is what keeps Schoharie's Clerk and two
    deputies out of the roster: they sit in the table in a member's shape with
    their ROLE in the column every member fills with a town;
  - EVERY UNIT OF THE COUNTY MUST BE SEATED. A town missing from the roster is
    not a smaller board, it is a town whose card would name nobody while its
    neighbours name somebody, which reads as an unrepresented town rather than
    as a parse that missed a row;
  - no unit may be seated twice by the same person.

A NAME SHIPS AS THE COUNTY PRINTS IT. Saratoga publishes one member as
"Ram mohan Lalukota", with a lower-case m, and that is what ships: correcting
a person's name on the strength of a guess about capitalisation is the same
class of act as guessing the name.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from scraper_common import make_fail  # noqa: E402

# NOT INSIDE THE REPOSITORY, for the reason the scraper's own default
# records: the scrape is an intermediate nothing reads once the roster is
# written, and a copy of last week's sitting in the tree beside this
# week's roster is a file with nothing comparing it to anything. The
# weekly job passes --in explicitly.
SCRAPE = os.path.join(tempfile.gettempdir(), "ny-supervisor-scrape.json")
FABRIC = os.path.join(REPO_ROOT, "ny", "data", "app", "ny-cities-towns.json")
OUT = os.path.join(REPO_ROOT, "ny", "data", "app", "ny-supervisor-members.json")

fail = make_fail("build-ny-supervisor-roster")


def units_of(county):
    with open(FABRIC, encoding="utf-8") as f:
        feats = json.load(f)["features"]
    return {p["NAME"]: p["MUNI_TYPE"]
            for p in (x.get("properties") or {} for x in feats)
            if p.get("COUNTY") == county}


def build(path=None):
    with open(path or SCRAPE, encoding="utf-8") as f:
        scrape = json.load(f)
    out = {}
    for key in sorted(scrape):
        rec = scrape[key]
        units = units_of(rec["county"])
        if not units:
            fail("%s: the cities-and-towns fabric holds no unit in %s County"
                 % (key, rec["county"]))
        members = rec["members"]
        if len(members) != rec["seats"]:
            fail("%s: %d member(s) parsed and the county's own page states %d "
                 "seats" % (key, len(members), rec["seats"]))
        seated = {}
        for m in members:
            unit = m["unit"]
            if unit not in units:
                fail("%s: %r is not a town or city of %s County in this "
                     "instance's own fabric" % (key, unit, rec["county"]))
            people = seated.setdefault(unit, [])
            if any(p["name"] == m["name"] for p in people):
                fail("%s: %s is seated twice for %s" % (key, m["name"], unit))
            person = {"name": m["name"]}
            for field in ("role", "party", "address", "phone", "email", "url"):
                if m.get(field):
                    person[field] = m[field]
            people.append(person)
        missing = sorted(set(units) - set(seated))
        if missing:
            fail("%s: %d unit(s) of %s County are seated by nobody: %s"
                 % (key, len(missing), rec["county"], ", ".join(missing)))
        out[key] = {
            "county": rec["county"],
            "board": rec["board"],
            "sourceUrl": rec["sourceUrl"],
            "seats": rec["seats"],
            "units": {unit: {"type": units[unit], "members": seated[unit]}
                      for unit in sorted(seated)},
        }
        print("build-ny-supervisor-roster: %s — %d seat(s) over %d unit(s), "
              "every unit seated" % (key, len(members), len(seated)))
    return out


def main():
    args = sys.argv[1:]
    src = None
    if "--in" in args:
        i = args.index("--in")
        if i + 1 >= len(args):
            raise SystemExit("build-ny-supervisor-roster: --in needs a path")
        src = args[i + 1]
    out = build(src)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    total = sum(r["seats"] for r in out.values())
    print("build-ny-supervisor-roster: wrote %s — %d county board(s), %d seat(s)"
          % (os.path.relpath(OUT, REPO_ROOT), len(out), total))


if __name__ == "__main__":
    main()
