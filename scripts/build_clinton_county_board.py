#!/usr/bin/env python3
"""
Resolve scripts/clinton_county_board_scraper.py's raw output into
data/app/clinton-county-board-members.json, keyed by Clinton County Board
district (5 districts of 3 members each).

index.html's consolidated county-board layer fetches this file lazily on first
click and joins it to data/app/clinton-county-board-districts.json by district
number.

THE ROSTER IS THE PAGE AND THE GEOMETRY IS THE RETURNS. Clinton's districts are
derived from its certified per-precinct returns because the county publishes its
board map only as a PDF (build_clinton_boundaries.py); its members come from the
county's own board page, which is the richest source this route has met — name,
phone, e-mail and term-expiry year on all fifteen, with the Board Chairman and
Vice Chairman named above the grid.

THE DRIFT CHECK. The scraper re-reads the county's live precinct count and each
numbered board contest's precinct count from the Clerk's results system every
week, and this asserts both against the shipped dissolve. It COUNTS rather than
names — two requests instead of thirty-four — and both events that would
invalidate the boundary (a re-precincting or a redistricting) move the counts.

WHAT SHIPS: name, district, phone, e-mail, term-expiry year, the Chair and
Vice-Chair roles the county itself prints, and a `board` block naming where the
board meets, from the County Clerk's own answer (BOARD_MEETS). WHAT DOES NOT: party, which the page
does not publish.

Usage:
    python3 build_clinton_county_board.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_clinton_boundaries import COMPOSITION, SEATS_PER_DISTRICT  # noqa: E402
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://clintonco.illinois.gov/county-offices/county-board/"

EXPECT_DISTRICTS = 5
EXPECT_MEMBERS = EXPECT_DISTRICTS * SEATS_PER_DISTRICT      # 15 seats
MIN_PHONES = 13
MIN_EMAILS = 13
STREET_RE = re.compile(
    r"\d+\s+\S+\s*(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|"
    r"blvd|hwy|way|circle|cir|place|pl|trail)\b", re.I)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("clinton-board-roster")

# WHERE THE BOARD MEETS, from the County Clerk's own answer. Clinton's filing
# gives only PO Box 308, Carlyle, which is not a place a reader can go, so the
# card had no address until Clerk Vicky Albers wrote on 2026-10-05 that the
# board meets in the board room on the first floor of the jail building, 810
# Franklin Street, Carlyle. It is a MEETING place, so the card says "Board
# meets at" (the Franklin and Jo Daviess label). The ZIP is the one the
# county's own filing gives for its Carlyle post-office box. The e-mail is in
# the operator's mailbox, not in this repository.
BOARD_MEETS = {
    "address": "Board room, first floor of the jail building, "
               "810 Franklin Street, Carlyle, IL 62231",
    "source": "The Clinton County Clerk, by e-mail, 5 October 2026",
}


def main():
    if len(sys.argv) < 2:
        fail("usage: build_clinton_county_board.py <raw-scraper-output.json> "
             "[output_dir]")
    with open(sys.argv[1], encoding="utf-8") as handle:
        raw = json.load(handle)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    # ---- the drift check ---------------------------------------------------
    check = raw.get("compositionCheck") or {}
    counts = check.get("precinctsPerDistrict") or {}
    if not counts:
        fail("the results system yielded no numbered county-board contest — "
             "this county's only automatic redistricting warning did not run")
    # The dissolve is keyed by CENSUS voting district; the contest counts are the
    # county's own precincts, which the boundaries module carries separately.
    from build_clinton_boundaries import COUNTY_COMPOSITION  # noqa: E402
    want = {d: len(p) for d, p in COUNTY_COMPOSITION.items()}
    got = {str(d): int(n) for d, n in counts.items()}
    if got != want:
        fail("the certified board contests now cover %s precincts per district, "
             "but the shipped boundary was dissolved for %s — Clinton "
             "redistricted or re-precincted; re-measure against the census "
             "fabric before shipping again (scripts/build_clinton_boundaries.py)"
             % (got, want))
    total = check.get("totalPrecincts")
    if total != sum(want.values()):
        fail("the Clerk's system reports %s precincts county-wide, the shipped "
             "dissolve describes %d" % (total, sum(want.values())))

    # ---- the roster --------------------------------------------------------
    chair = (raw.get("chair") or "").strip()
    vice = (raw.get("viceChair") or "").strip()
    roster = {}
    for dnum, members in (raw.get("districts") or {}).items():
        if str(dnum) not in COMPOSITION:
            fail("the board page names a district %r that does not exist" % dnum)
        entry = roster.setdefault(str(dnum), {"members": [], "sourceUrl": BOARD_URL})
        for rec in members:
            member = {"name": re.sub(r"\s+", " ", rec["name"]).strip()}
            for key in ("phone", "email", "termExpires"):
                if rec.get(key):
                    member[key] = re.sub(r"\s+", " ", str(rec[key])).strip()
            if member["name"] == chair:
                member["role"] = "Chairman"
            elif member["name"] == vice:
                member["role"] = "Vice Chairman"
            entry["members"].append(member)

    if len(roster) != EXPECT_DISTRICTS:
        fail("parsed %d districts, expected exactly %d"
             % (len(roster), EXPECT_DISTRICTS))
    seats = sum(len(v["members"]) for v in roster.values())
    if seats != EXPECT_MEMBERS:
        fail("parsed %d members, expected exactly %d (%d districts of %d)"
             % (seats, EXPECT_MEMBERS, EXPECT_DISTRICTS, SEATS_PER_DISTRICT))
    for dnum, entry in roster.items():
        if len(entry["members"]) != SEATS_PER_DISTRICT:
            fail("district %s carries %d member(s), expected %d"
                 % (dnum, len(entry["members"]), SEATS_PER_DISTRICT))
        entry["members"].sort(key=lambda m: m["name"])
    phones = sum(1 for v in roster.values() for m in v["members"] if m.get("phone"))
    emails = sum(1 for v in roster.values() for m in v["members"] if m.get("email"))
    if phones < MIN_PHONES:
        fail("only %d/%d members carry a phone (floor %d)"
             % (phones, EXPECT_MEMBERS, MIN_PHONES))
    if emails < MIN_EMAILS:
        fail("only %d/%d members carry an e-mail (floor %d)"
             % (emails, EXPECT_MEMBERS, MIN_EMAILS))
    badged = [m["name"] for v in roster.values() for m in v["members"] if m.get("role")]
    if len(badged) != 2:
        fail("expected exactly two badged officers (Chairman, Vice Chairman), "
             "got %s" % badged)
    for entry in roster.values():
        for member in entry["members"]:
            for key, value in member.items():
                if STREET_RE.search(str(value)):
                    fail("a street address reached %s's %s (%r)"
                         % (member["name"], key, value))

    roster["board"] = dict(BOARD_MEETS)

    out_path = os.path.join(out_dir, "clinton-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(roster, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    print("clinton-board-roster: wrote %s — %d districts of %d (%d phones, "
          "%d e-mails, term year on every seat; Chairman %s, Vice Chairman %s)"
          % (os.path.relpath(out_path, REPO_ROOT), EXPECT_DISTRICTS,
             SEATS_PER_DISTRICT, phones, emails, chair, vice))
    print("  composition verified against the shipped dissolve: %s precincts per "
          "district, %d county-wide" % (got, sum(want.values())))


if __name__ == "__main__":
    main()
