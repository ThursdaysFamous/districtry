#!/usr/bin/env python3
"""Build il/data/app/christian-county-board-members.json from the Clerk's letter.

Christian County's board is sixteen members, four per district, and its
website (christiancountyil.gov) has answered every client with a Cloudflare
managed challenge since 2026-09-15. A managed challenge is an access control
and is never worked around, so the county's board page cannot be re-read
here. When it was last readable it named only the Chairman and Vice Chairman.

On 2026-10-07 County Clerk Jodie L. Badman answered our letter with two
screenshots of that same page's "County Board Members" list, which name all
sixteen by district. That reply is the source, and this file is a DOCUMENT
roster: nothing here re-verifies itself, and the only refresh is another
letter, or the county's page becoming readable again. Every run prints how
old the document is, the way the at-large DOCUMENT_ROSTERS do.

What does NOT ship, and why:
  - Each member's home city and ZIP, which the list prints beside the name.
    That is where a member lives, not an office, and home details never ship.
  - The "Yrs of term as of 12/24" column (2 or 4, and "2 yr unexpired term"
    for Ray Koonce). It is the length of the term each member was elected to,
    stated as of December 2024, not when it ends, and a card that turned it
    into an end date would be inventing one.
  - A chair or vice chair. The list marks neither, and the page's own
    Chairman/Vice Chairman line could not be re-read on the day, so nobody is
    given a title.

Members are ordered within each district as the county's list orders them.

    python3 scripts/build_christian_county_board.py           # write
    python3 scripts/build_christian_county_board.py --check   # CI-style check
"""

import argparse
import datetime
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "il", "data", "app", "christian-county-board-members.json")
DISTRICTS_FILE = os.path.join(REPO_ROOT, "il", "data", "app",
                              "christian-county-board-districts.json")

SOURCE_URL = "https://www.christiancountyil.gov/county-board/"
DOCUMENT = ("screenshots of the county's County Board Members list, sent by "
            "e-mail from County Clerk Jodie L. Badman, 2026-10-07")
VERIFIED = "2026-10-07"
SEATS_PER_DISTRICT = 4

ROSTER = {
    "1": ["Linda Curtin", "Venise McWard", "Sam Sassatelli", "Clint Gabriel"],
    "2": ["David Puccetti", "Vicki M. McMahon", "Mark Wolfe", "Ken Franklin"],
    "3": ["David Buckles", "Ray Koonce", "Bryan Sharp", "Mike Specha"],
    "4": ["Jean Vandenbergh", "Miranda McKown", "Clint Epley", "Marsha Miles"],
}


def fail(msg):
    print("build-christian-county-board: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def build():
    with open(DISTRICTS_FILE, encoding="utf-8") as f:
        shipped = {str(ft["properties"]["district"]): ft["properties"]
                   for ft in json.load(f)["features"]}
    if set(shipped) != set(ROSTER):
        fail("the roster names districts %s and the shipped board districts are "
             "%s — one of the two is out of date"
             % (sorted(ROSTER), sorted(shipped)))
    seen = set()
    out = {}
    for key in sorted(ROSTER, key=int):
        names = ROSTER[key]
        seats = shipped[key].get("seats", SEATS_PER_DISTRICT)
        if len(names) != seats:
            fail("District %s lists %d members and the district has %d seats"
                 % (key, len(names), seats))
        for n in names:
            if n in seen:
                fail("%s is listed in two districts" % n)
            seen.add(n)
        out[key] = {
            "members": [{"name": n} for n in names],
            "sourceUrl": SOURCE_URL,
            "sourceDocument": DOCUMENT,
            "verified": VERIFIED,
        }
    return out


def render(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail if the shipped file differs from this table")
    args = ap.parse_args()
    data = build()
    text = render(data)
    age = (datetime.date.today() - datetime.date.fromisoformat(VERIFIED)).days
    print("build-christian-county-board: NOT RE-READ — the county's page is behind "
          "a managed challenge; %d members come from %s, %d days old. Re-ask the "
          "Clerk to refresh." % (sum(len(v) for v in ROSTER.values()), DOCUMENT, age),
          file=sys.stderr)
    if args.check:
        try:
            with open(OUT, encoding="utf-8") as f:
                current = f.read()
        except FileNotFoundError:
            fail("%s is missing — run this script" % os.path.relpath(OUT, REPO_ROOT))
        if current != text:
            fail("%s differs from the table in this script — run it"
                 % os.path.relpath(OUT, REPO_ROOT))
        print("build-christian-county-board: OK — %d districts, %d members, matches"
              % (len(data), len(seen_names(data))))
        return
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print("build-christian-county-board: wrote %s — %d districts, %d members"
          % (os.path.relpath(OUT, REPO_ROOT), len(data), len(seen_names(data))))


def seen_names(data):
    return [m["name"] for v in data.values() for m in v["members"]]


if __name__ == "__main__":
    main()
