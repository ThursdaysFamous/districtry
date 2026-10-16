#!/usr/bin/env python3
"""Build il/data/app/ford-county-board-members.json from the Clerk's letter.

Ford County's board is twelve members, four per district (Res. 21-101,
build_ford_boundaries.py). Its board page, fordcounty.illinois.gov/ford-county-board/,
answers non-deterministically: measured 2026-10-01, six reads returned the page
three times and a "Javascript is required" interstitial three times. That is an
access control stating its condition, so the page is not scraped here, not even
on the reads where the control happens to be off.

On 2026-10-01 County Clerk Kelsie Vaughn answered our letter by e-mail with the
twelve members by district and the board's two officers. That reply is the
source, and this file is a DOCUMENT roster: nothing here re-verifies itself, and
the only refresh is another letter, or the county's page becoming readable
without a challenge. Every run prints how old the document is, the way
build_christian_county_board.py and the at-large DOCUMENT_ROSTERS do.

What ships: each member's name as the Clerk wrote it, the district, and the
Chairman and Vice Chairman titles she gave. The reply carries no phone, e-mail,
term or party per member, so none ships. The Clerk and the Vice Chairman share
a surname; nothing here joins by surname.

Members are ordered within each district as the Clerk's reply orders them.

    python3 scripts/build_ford_county_board.py           # write
    python3 scripts/build_ford_county_board.py --check   # CI-style check
"""

import argparse
import datetime
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "il", "data", "app", "ford-county-board-members.json")
DISTRICTS_FILE = os.path.join(REPO_ROOT, "il", "data", "app",
                              "ford-county-board-districts.json")

SOURCE_URL = "https://fordcounty.illinois.gov/ford-county-board/"
DOCUMENT = ("the County Board members by district, sent by e-mail from County "
            "Clerk Kelsie Vaughn, 2026-10-01")
VERIFIED = "2026-10-01"
SEATS_PER_DISTRICT = 4

# (name, title or None), in the reply's order.
ROSTER = {
    "1": [("Gene May", None), ("Tom McQuinn", None),
          ("Carson Vaughn", "Vice Chairman"), ("Dominic Brackenhoff", None)],
    "2": [("Cindy Ihrke", None), ("Lesley King", None),
          ("Greg Niewold", None), ("Tim Nuss", None)],
    "3": [("Chase McCall", "Chairman"), ("Randy Ferguson", None),
          ("Sarah Mussman", None), ("Neil Rhoades", None)],
}


def fail(msg):
    print("build-ford-county-board: FAIL — " + msg, file=sys.stderr)
    sys.exit(1)


def build():
    with open(DISTRICTS_FILE, encoding="utf-8") as f:
        shipped = {str(ft["properties"]["district"]): ft["properties"]
                   for ft in json.load(f)["features"]}
    if set(shipped) != set(ROSTER):
        fail("the roster names districts %s and the shipped board districts are "
             "%s — one of the two is out of date"
             % (sorted(ROSTER), sorted(shipped)))
    titles = [t for rows in ROSTER.values() for _, t in rows if t]
    if sorted(titles) != ["Chairman", "Vice Chairman"]:
        fail("the roster carries titles %r, expected one Chairman and one Vice "
             "Chairman" % titles)
    seen = set()
    out = {}
    for key in sorted(ROSTER, key=int):
        rows = ROSTER[key]
        seats = shipped[key].get("seats", SEATS_PER_DISTRICT)
        if len(rows) != seats:
            fail("District %s lists %d members and the district has %d seats"
                 % (key, len(rows), seats))
        members = []
        for name, title in rows:
            if not name.strip():
                fail("District %s has a member with no name" % key)
            if name in seen:
                fail("%s is listed twice" % name)
            seen.add(name)
            member = {"name": name}
            if title:
                member["role"] = title
            members.append(member)
        out[key] = {
            "members": members,
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
    count = sum(len(v["members"]) for v in data.values())
    age = (datetime.date.today() - datetime.date.fromisoformat(VERIFIED)).days
    print("build-ford-county-board: NOT RE-READ — the county's board page is "
          "behind a JavaScript challenge; %d members come from %s, %d days old. "
          "Re-ask the Clerk to refresh." % (count, DOCUMENT, age), file=sys.stderr)
    if args.check:
        try:
            with open(OUT, encoding="utf-8") as f:
                current = f.read()
        except FileNotFoundError:
            fail("%s is missing — run this script" % os.path.relpath(OUT, REPO_ROOT))
        if current != text:
            fail("%s differs from the table in this script — run it"
                 % os.path.relpath(OUT, REPO_ROOT))
        print("build-ford-county-board: OK — %d districts, %d members, matches"
              % (len(data), count))
        return
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print("build-ford-county-board: wrote %s — %d districts, %d members"
          % (os.path.relpath(OUT, REPO_ROOT), len(data), count))


if __name__ == "__main__":
    main()
