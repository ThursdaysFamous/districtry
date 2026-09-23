#!/usr/bin/env python3
"""
Resolve scripts/logan_county_board_scraper.py's raw output into
data/app/logan-county-board-members.json, keyed by board district — six
two-member districts, with the Chair and Vice Chair tags riding their own
member rows (the county elects both from within the body AND says who holds
them, unlike Woodford's unmarked directory).

index.html's consolidated county-board layer fetches this file lazily on
first click (same-origin) and joins it to the TCRPC district boundary by
district number — closing the rule-4 branch-3 honesty floor the entry
shipped with (gap logan-county-board-members).

Usage:
    python3 build_logan_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import sys
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = ("https://www.logancountyil.gov/index.php?option=com_content"
              "&view=article&id=176&Itemid=541&lang=en")

EXPECT_DISTRICTS = ("1", "2", "3", "4", "5", "6")

# THE BOARD'S OWN OFFICE, and it is the board's rather than a member's because
# the county says so in those words: the page heads this block "Logan County
# Board Office" and then lists twelve members each with a DIFFERENT address.
# That distinction is the whole reason this ships and Franklin's and Warren's
# do not — a board page's only street address is very often a member's HOME,
# which this fleet never publishes (the Madison/Peoria rule). The county gives
# a PO Box (39) beside the street address; the street one ships, because the
# card's label is where a reader can go.
BOARD = {
    "address": "Logan County Board Office, 601 Broadway St., Lincoln, IL 62656",
    "phone": "(217) 732-6400",
    "email": "logancountyboard@logancountyil.gov",
    "sourceUrl": SOURCE_URL,
}
# SEATS, NOT MEMBERS. The county seats two per district and says so; whether
# both are filled is a different question, and conflating them is what made this
# builder refuse to write the moment a seat went empty. A vacancy moves the
# named count and never the seat count — the split build_sangamon_county_board_roster.py
# already draws, for the same reason: the board did not get smaller, one of its
# seats got emptier.
EXPECT_SEATS_PER_DISTRICT = 2
MIN_PHONES = 10
MIN_EMAILS = 10

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("logan-board-roster")


def main():
    if len(sys.argv) < 2:
        fail("usage: build_logan_board_roster.py <raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as f:
        records = json.load(f)["records"]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    roster = {}
    chairs = []
    for rec in records:
        if rec.get("district") is None:
            continue
        d = str(rec["district"])
        roster.setdefault(d, {"members": [], "sourceUrl": SOURCE_URL})
        if rec.get("vacant"):
            # Counted, never named — the Livingston posture the county-board
            # card and build_county_pages.py both already render ("N of M seats
            # here is vacant"). The role the page printed beside the empty seat
            # is not carried onto the district: it describes a seat nobody
            # holds, and a role with no person on a card reads as a person.
            roster[d]["vacancies"] = roster[d].get("vacancies", 0) + 1
            continue
        if not rec.get("name"):
            continue
        m = {"name": rec["name"]}
        if rec.get("role"):
            m["role"] = rec["role"]
            chairs.append((rec["role"], rec["name"]))
        for k in ("phone", "email"):
            if rec.get(k):
                m[k] = rec[k]
        roster[d]["members"].append(m)

    if sorted(roster) != sorted(EXPECT_DISTRICTS):
        fail("parsed districts %s, expected exactly %s" % (sorted(roster), list(EXPECT_DISTRICTS)))
    for d, entry in roster.items():
        seats = len(entry["members"]) + entry.get("vacancies", 0)
        if seats != EXPECT_SEATS_PER_DISTRICT:
            fail("district %s accounts for %d seats (%d named, %d vacant), the "
                 "county seats exactly %d"
                 % (d, seats, len(entry["members"]), entry.get("vacancies", 0),
                    EXPECT_SEATS_PER_DISTRICT))
    roles = sorted(r for r, _ in chairs)
    if roles != ["Chair", "Vice Chair"]:
        fail("expected exactly one Chair and one Vice Chair, got %s — the page's "
             "role tags changed" % (chairs or "none"))
    named = sum(len(v["members"]) for v in roster.values())
    vacancies = sum(v.get("vacancies", 0) for v in roster.values())
    phones = sum(1 for v in roster.values() for m in v["members"] if m.get("phone"))
    emails = sum(1 for v in roster.values() for m in v["members"] if m.get("email"))
    # The denominator is the NAMED count, not the seat count: an empty seat has
    # nobody to carry a phone, so measuring against 12 would report a shortfall
    # the county has not got.
    if phones < MIN_PHONES:
        fail("only %d/%d named members carry a phone (floor %d)"
             % (phones, named, MIN_PHONES))
    if emails < MIN_EMAILS:
        fail("only %d/%d named members carry an e-mail (floor %d)"
             % (emails, named, MIN_EMAILS))

    # Added AFTER every district check above, all of which read roster's keys
    # as districts (sorted(roster) == EXPECT_DISTRICTS) or index members on
    # each value. A board block written earlier would fail the first and
    # KeyError the second.
    roster["board"] = dict(BOARD)

    out_path = os.path.join(out_dir, "logan-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("logan-board-roster: wrote %s — 6 districts x 2 seats (%d named, %d "
          "vacant) + the board office block (%d phones, %d e-mails; %s)"
          % (os.path.relpath(out_path, REPO_ROOT), named, vacancies,
             phones, emails,
             ", ".join("%s %s" % (r, n) for r, n in sorted(chairs))))


if __name__ == "__main__":
    main()
