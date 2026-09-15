#!/usr/bin/env python3
"""
Resolve scripts/il_court_justices_scraper.py's raw output into the app-data
file the `il-supreme-court` card reads: il/data/app/il-court-justices.json,
keyed by judicial district ("1".."5").

index.html fetches it lazily on first click (same-origin, network-first via the
service worker) and joins it to the PA 102-0011 district geometry the app
already ships in il/data/app/il-supreme-court-districts.json. Same two-stage
pattern as scripts/ccbr_scraper.py + scripts/build_ccbr_roster.py.

ONE FILE ANSWERS FOR BOTH COURTS because one set of districts serves both.
Illinois Constitution art. VI, sec. 2 divides the State into five Judicial
Districts "for the selection of Supreme and Appellate Court Judges"; 705 ILCS
25/1(a) establishes a branch of the appellate court "in each of the 5 judicial
districts as such districts are determined by law"; and 705 ILCS 23, the
Judicial Districts Act of 2021 (P.A. 102-11), is where they are determined.
So the appellate districts are the geometry already shipped, and this file adds
people and offices to it rather than a second polygon layer.

THE COUNTY LISTS ARE THE GATE, and they are what makes this more than a scrape.
Each appellate district's page names the circuits it hears appeals from and the
counties in each -- the courts' own account of the composition. STATUTE_COUNTIES
below is the General Assembly's, transcribed from 705 ILCS 23/10 through /30.
The two are independent publishers, and the build refuses to write unless they
agree exactly: every Illinois county named once, in the district the statute
puts it in. That catches a redistricting, a page rewrite and a parser fault
with the same test. (The shipped geometry was separately checked against the
same statute when this was built: every one of the 101 counties with an outline
in il/data/app lands in the district 705 ILCS 23 names, Cook being the 102nd
and the First District by the Constitution itself.)

WHAT THE COUNTS MEAN, AND WHAT THEY DO NOT. The Supreme Court complement is
constitutional and exact: art. VI, sec. 3, "The Supreme Court shall consist of
seven Judges. Three shall be selected from the First Judicial District and one
from each of the other Judicial Districts." So SUPREME_SEATS is an equality,
not a floor. The appellate complement is NOT: 705 ILCS 25/1(b)-(c) elects 18
justices in the First District and 6 in each of the others, while sec. 1(d)
lets the Supreme Court assign additional judges "as the business of the
appellate court requires", and the directory lists everyone serving. Measured
2026-09-15 it lists 57 against the 42 elected seats. MIN_APPELLATE is therefore
a parse-failure floor set below the elected complement -- a vacancy must not
fail the build -- and no record here claims a justice is elected rather than
assigned, because the directory does not say.

Usage:
    python3 build_il_court_justices.py <raw.json> [output_dir]
    python3 build_il_court_justices.py <raw.json> --check
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
OUT_NAME = "il-court-justices.json"

# 705 ILCS 23/10, /15, /20, /25, /30 (P.A. 102-11, eff. 6-4-21), read from
# ilga.gov on 2026-09-15. One entry per county, 102 in all.
STATUTE_COUNTIES = {
    1: "Cook",
    2: "DeKalb Kendall Kane Lake McHenry",
    3: "Bureau LaSalle Grundy Iroquois Kankakee DuPage Will",
    4: ("Jo-Daviess Stephenson Carroll Ogle Lee Winnebago Boone Mercer Rock-Island Whiteside "
        "Henry Stark Putnam Marshall Peoria Tazewell Adams Pike Calhoun Schuyler Brown Cass "
        "Mason Menard Morgan Scott Greene Jersey Macoupin Sangamon Logan McLean Woodford "
        "Livingston Ford Henderson Warren Knox Fulton McDonough Hancock"),
    5: ("DeWitt Macon Piatt Moultrie Champaign Douglas Vermilion Edgar Coles Cumberland Clark "
        "Christian Shelby Montgomery Fayette Effingham Jasper Clay Marion Clinton Bond Madison "
        "St-Clair Washington Monroe Randolph Perry Crawford Richland Lawrence Wabash Edwards "
        "Wayne Jefferson Franklin Hamilton White Gallatin Hardin Saline Williamson Jackson "
        "Union Johnson Pope Alexander Pulaski Massac"),
}

# Illinois Constitution art. VI, sec. 3 -- an equality, not a floor.
SUPREME_SEATS = {1: 3, 2: 1, 3: 1, 4: 1, 5: 1}
# Parse-failure floors, deliberately below the 705 ILCS 25/1 elected
# complement (18/6/6/6/6) so a vacancy cannot fail the build.
MIN_APPELLATE = {1: 14, 2: 4, 3: 4, 4: 4, 5: 4}
MIN_APPELLATE_TOTAL = 34


def county_key(name):
    return re.sub(r"[^a-z]", "", (name or "").lower())


STATUTE_BY_COUNTY = {}
for _district, _names in STATUTE_COUNTIES.items():
    for _name in _names.split():
        STATUTE_BY_COUNTY[county_key(_name)] = _district
assert len(STATUTE_BY_COUNTY) == 102, len(STATUTE_BY_COUNTY)


def fail(message):
    print("FAIL: %s" % message)
    sys.exit(1)


def check_counties(branches):
    """The courts' county lists against 705 ILCS 23, both directions."""
    seen = {}
    for branch in branches:
        district = branch["district"]
        for name in branch.get("counties") or []:
            key = county_key(name)
            if key in seen:
                fail("the court's pages name %s in districts %d and %d"
                     % (name, seen[key][0], district))
            seen[key] = (district, name)
    unknown = sorted(name for key, (_d, name) in seen.items() if key not in STATUTE_BY_COUNTY)
    if unknown:
        fail("the court's pages name %d county/counties 705 ILCS 23 does not: %s"
             % (len(unknown), ", ".join(unknown)))
    missing = sorted(key for key in STATUTE_BY_COUNTY if key not in seen)
    if missing:
        fail("the court's pages name none of %d statutory county/counties: %s"
             % (len(missing), ", ".join(missing)))
    wrong = [(name, district, STATUTE_BY_COUNTY[key])
             for key, (district, name) in sorted(seen.items())
             if STATUTE_BY_COUNTY[key] != district]
    if wrong:
        fail("the court and 705 ILCS 23 disagree on %d county/counties: %s"
             % (len(wrong), "; ".join("%s court=%d statute=%d" % w for w in wrong)))
    print("  counties: 102/102 agree with 705 ILCS 23 (%s)"
          % " ".join("D%d=%d" % (d, len(STATUTE_COUNTIES[d].split()))
                     for d in sorted(STATUTE_COUNTIES)))


def build(raw):
    branches = {b["district"]: b for b in raw.get("branches") or []}
    if sorted(branches) != [1, 2, 3, 4, 5]:
        fail("expected branches for districts 1-5, got %s" % sorted(branches))
    check_counties(list(branches.values()))

    supreme = {}
    chiefs = 0
    for justice in raw.get("supreme") or []:
        name = (justice.get("name") or "").strip()
        district = justice.get("district")
        if not name or district not in SUPREME_SEATS:
            fail("unusable supreme court record: %r" % (justice,))
        if justice.get("role") == "Chief Justice":
            chiefs += 1
        supreme.setdefault(district, []).append(
            {"name": name, "role": justice.get("role") or "Justice"})
    counts = dict((d, len(v)) for d, v in supreme.items())
    if counts != SUPREME_SEATS:
        fail("art. VI sec. 3 seats %s; the court's page gives %s"
             % (SUPREME_SEATS, counts))
    if chiefs != 1:
        fail("art. VI sec. 3 has the justices select ONE Chief Justice; found %d" % chiefs)
    print("  supreme court: 7 justices, %s, one Chief Justice"
          % " ".join("D%d=%d" % (d, counts[d]) for d in sorted(counts)))

    appellate = {}
    for justice in raw.get("appellate") or []:
        name = (justice.get("name") or "").strip()
        district = justice.get("district")
        if not name or district not in SUPREME_SEATS:
            fail("unusable appellate record: %r" % (justice,))
        entry = {"name": name}
        url = justice.get("profile_url")
        if url and url.startswith("https://"):
            entry["url"] = url
        # Sort on the surname the directory itself publishes, minus any
        # generational suffix; see the scraper's note on the four names a
        # re-derived surname puts in the wrong place.
        entry["_sort"] = re.sub(r"\s+(Jr\.?|Sr\.?|I{2,3}|IV)$", "",
                                justice.get("last") or name.split()[-1]).lower()
        appellate.setdefault(district, []).append(entry)
    total = sum(len(v) for v in appellate.values())
    if total < MIN_APPELLATE_TOTAL:
        fail("appellate directory resolved %d justices, floor %d" % (total, MIN_APPELLATE_TOTAL))
    for district, floor in sorted(MIN_APPELLATE.items()):
        found = len(appellate.get(district) or [])
        if found < floor:
            fail("district %d resolved %d appellate justices, floor %d"
                 % (district, found, floor))
    print("  appellate court: %d justices, %s"
          % (total, " ".join("D%d=%d" % (d, len(appellate[d])) for d in sorted(appellate))))

    districts = {}
    for number in sorted(branches):
        branch = branches[number]
        lines = [line for line in (branch.get("address_lines") or []) if line]
        if not lines:
            fail("district %d published no courthouse address" % number)
        if not branch.get("phone"):
            fail("district %d published no telephone" % number)
        if not branch.get("clerk"):
            fail("district %d named no clerk" % number)
        record = {
            "supreme": sorted(supreme[number], key=lambda j: (j["role"] != "Chief Justice", j["name"])),
            "supremeSourceUrl": (raw.get("supreme") or [{}])[0].get("source_url"),
            "appellate": {
                "seat": branch.get("seat"),
                "addressLines": lines,
                "phone": branch["phone"],
                "clerk": branch["clerk"],
                "counties": len(branch.get("counties") or []),
                "justices": [
                    dict((k, v) for k, v in justice.items() if k != "_sort")
                    for justice in sorted(appellate[number], key=lambda j: j["_sort"])
                ],
                "sourceUrl": branch.get("source_url"),
            },
        }
        if branch.get("population"):
            record["appellate"]["population"] = branch["population"]
        districts[str(number)] = record
    # Keyed by district at the TOP LEVEL, the ccbr-roster.json shape, so
    # validate_index.py's min_keys guard counts districts rather than counting
    # the two keys of a wrapper. No `generated` stamp for the same reason (and
    # because ccbr-roster.json carries none): the refresh PR and the git
    # history are where the date lives.
    return districts


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    with open(args[0]) as handle:
        raw = json.load(handle)
    payload = build(raw)
    out_dir = args[1] if len(args) > 1 else DEFAULT_OUT_DIR
    path = os.path.join(out_dir, OUT_NAME)
    if check:
        if not os.path.exists(path):
            fail("%s is missing" % path)
        with open(path) as handle:
            shipped = json.load(handle)
        moved = []
        for key in sorted(set(payload) | set(shipped)):
            if shipped.get(key) != payload.get(key):
                moved.append(key)
        if moved:
            fail("%s does not match a fresh build; district(s) %s differ"
                 % (OUT_NAME, ", ".join(moved)))
        print("OK: %s matches a fresh build of the courts' own pages" % OUT_NAME)
        return 0
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
