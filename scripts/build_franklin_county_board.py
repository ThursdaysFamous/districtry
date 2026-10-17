#!/usr/bin/env python3
"""
Resolve scripts/franklin_county_board_scraper.py's raw output into
data/app/franklin-county-board-members.json, keyed by Franklin County Board
district (3 districts of 3 members each, staggered).

index.html's consolidated county-board layer fetches this file lazily on first
click and joins it to data/app/franklin-county-board-districts.json by district
number.

THE ROSTER IS THE PAGE AND THE GEOMETRY IS THE RETURNS. Franklin's districts
are derived from its certified per-precinct returns because the county
publishes no boundary as data (build_franklin_boundaries.py); its members come
from the county's own page, because a canvass shows who WON a completed term
and cannot show a seat filled since — the split Edgar's District 6 made the
case for.

THE DRIFT CHECK, which is what makes a derived boundary safe to ship. The
scraper re-reads two facts from the Clerk's results system every week: the
county's live precinct count, and the precinct count of each numbered board
contest in the newest board election. This asserts both against the shipped
dissolve and FAILS on any disagreement. It is deliberately weaker than a
full per-precinct re-read — it counts rather than names — and says so: it
catches a re-precincting or a redistricting, which are the two events that
would invalidate the boundary, and it costs two requests instead of thirty-five.

WHAT SHIPS: name, district, the role the county prints beside the member, the
Mobile column's number ("mobile 618-..."), any home number the county prints in
its "Home or E-Mail" column (`phonesExtra`, "home 618-...", which ships since
Adam's ruling of 2026-10-17: "if the official government source uses personal
phone numbers, we publish those"), and e-mail. WHAT DOES NOT: the Address
column, which is every member's HOME address (the Madison/Peoria rule, enforced
in the scraper by discarding the column and asserted again here), and party,
which the members page does not publish. Every number is checked for its shape
(scraper_common.person_phone_problem): one telephone number, led by its label,
and nothing else.

THE CHAIR IS THE COUNTY'S OWN LABEL, not an inference from the canvasses.
§3.5.1 warns against badging a chair derived from returns, because a
chairmanship is elected from within the body and no certified document shows
it. This is the other case: the county's members page prints a role beside four
of its nine members, and the table distinguishes the board's own officers
("Chairman", "Vice Chairman") from committee chairs by naming the committee in
the latter. Both ship exactly as printed.

Usage:
    python3 build_franklin_county_board.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_franklin_boundaries import COMPOSITION, SEATS_PER_DISTRICT  # noqa: E402
from scraper_common import make_fail, person_phone_problem  # noqa: E402  (shared machinery — do not fork)

BOARD_URL = "https://franklincountyil.gov/county-board-members/"

EXPECT_DISTRICTS = 3
EXPECT_MEMBERS = EXPECT_DISTRICTS * SEATS_PER_DISTRICT      # 9 seats
MIN_PHONES = 7          # measured 8/9 — one member's row carries no number
# No floor for home numbers: measured on 2026-10-17 the "Home or E-Mail" column
# held one e-mail address and eight empty cells, so the count is 0 and a floor of
# two thirds of it would guard nothing. MIN_PHONES above still fails the build if
# the Mobile column stops being read.
STREET_RE = re.compile(
    r"\d+\s+\S+\s*(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|"
    r"blvd|hwy|way|circle|cir|place|pl|trail|heights)\b", re.I)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("franklin-board-roster")


def main():
    if len(sys.argv) < 2:
        fail("usage: build_franklin_county_board.py <raw-scraper-output.json> "
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
    want = {d: len(p) for d, p in COMPOSITION.items()}
    got = {str(d): int(n) for d, n in counts.items()}
    if got != want:
        fail("the certified board contests now cover %s precincts per district, "
             "but the shipped boundary was dissolved from %s — Franklin "
             "redistricted or re-precincted; re-measure against the census "
             "fabric before shipping again "
             "(scripts/build_franklin_boundaries.py)" % (got, want))
    total_precincts = check.get("totalPrecincts")
    shipped_precincts = sum(len(p) for p in COMPOSITION.values())
    if total_precincts != shipped_precincts:
        fail("the Clerk's system reports %s precincts county-wide, the shipped "
             "dissolve uses %d" % (total_precincts, shipped_precincts))

    # ---- the roster --------------------------------------------------------
    roster = {}
    for dnum, members in (raw.get("districts") or {}).items():
        if str(dnum) not in COMPOSITION:
            fail("the members page names a district %r that does not exist" % dnum)
        entry = roster.setdefault(str(dnum), {"members": [], "sourceUrl": BOARD_URL})
        for rec in members:
            member = {"name": re.sub(r"\s+", " ", rec["name"]).strip()}
            for key in ("role", "phone", "email"):
                if rec.get(key):
                    member[key] = re.sub(r"\s+", " ", str(rec[key])).strip()
            extras = [re.sub(r"\s+", " ", str(p)).strip()
                      for p in (rec.get("phonesExtra") or []) if p]
            if extras:
                member["phonesExtra"] = extras
            entry["members"].append(member)

    if len(roster) != EXPECT_DISTRICTS:
        fail("parsed %d districts, expected exactly %d"
             % (len(roster), EXPECT_DISTRICTS))
    total = sum(len(v["members"]) for v in roster.values())
    if total != EXPECT_MEMBERS:
        fail("parsed %d members, expected exactly %d (%d districts of %d)"
             % (total, EXPECT_MEMBERS, EXPECT_DISTRICTS, SEATS_PER_DISTRICT))
    for dnum, entry in roster.items():
        if len(entry["members"]) != SEATS_PER_DISTRICT:
            fail("district %s carries %d member(s), expected %d"
                 % (dnum, len(entry["members"]), SEATS_PER_DISTRICT))
        entry["members"].sort(key=lambda m: m["name"])
    phones = sum(1 for v in roster.values() for m in v["members"] if m.get("phone"))
    if phones < MIN_PHONES:
        fail("only %d/%d members carry a phone (floor %d) — the members page "
             "changed shape" % (phones, EXPECT_MEMBERS, MIN_PHONES))
    # The privacy invariant, asserted again on what is about to be written. The
    # message names the member and the field and never the value.
    for entry in roster.values():
        for member in entry["members"]:
            for key, value in member.items():
                if STREET_RE.search(str(value)):
                    fail("a residence reached %s's %s — the members page's "
                         "Address column is never read" % (member["name"], key))
    # The shape of every number: one telephone number led by its label. The
    # message names the district and the seat's place in it, never the value.
    for dnum, entry in sorted(roster.items()):
        for seat, member in enumerate(entry["members"], 1):
            values = [("phone", member.get("phone"))] if member.get("phone") else []
            values += [("phonesExtra[%d]" % i, v)
                       for i, v in enumerate(member.get("phonesExtra") or [])]
            for field, value in values:
                problem = person_phone_problem(value)
                if problem:
                    fail("Franklin County District %s, seat %d of %d: %s %s"
                         % (dnum, seat, len(entry["members"]), field, problem))
    chairs = sorted(m["name"] for v in roster.values() for m in v["members"]
                    if (m.get("role") or "").lower() == "chairman")
    if len(chairs) > 1:
        fail("two members are badged Chairman (%s) — the page names one"
             % ", ".join(chairs))

    out_path = os.path.join(out_dir, "franklin-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(roster, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    emails = sum(1 for v in roster.values() for m in v["members"] if m.get("email"))
    roles = sum(1 for v in roster.values() for m in v["members"] if m.get("role"))
    homes = sum(1 for v in roster.values() for m in v["members"] if m.get("phonesExtra"))
    print("franklin-board-roster: wrote %s — %d districts of %d (%d phones, "
          "%d with a home number too, %d e-mail, %d roles printed by the county%s)"
          % (os.path.relpath(out_path, REPO_ROOT), EXPECT_DISTRICTS,
             SEATS_PER_DISTRICT, phones, homes, emails, roles,
             "; chairman %s" % chairs[0] if chairs else "; no chairman printed"))
    print("  composition verified against the shipped dissolve: %s precincts per "
          "district, %d county-wide" % (got, shipped_precincts))


if __name__ == "__main__":
    main()
