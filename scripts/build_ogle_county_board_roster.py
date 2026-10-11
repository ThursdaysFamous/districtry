#!/usr/bin/env python3
"""
Resolve scripts/ogle_county_board_scraper.py's raw output into
data/app/ogle-county-board-members.json, keyed by Ogle County Board district
("1".."8" — eight districts electing three members each, 24 seats).

index.html's consolidated county-board layer fetches this file lazily on first
click (same-origin) and joins it by district number to
data/app/ogle-county-board-districts.json, the precinct dissolve built by
build_ogle_board_districts.py from the county's adopted reapportionment
resolution. Ogle is the fleet's second county where BOTH halves are DERIVED
rather than fetched — after Livingston, and for the same reason: the county
publishes officeholders and a written composition but no district geometry.

Shape mirrors the McHenry/Kendall/Livingston/DeKalb rosters —
{district: {members: [...], sourceUrl}}. The Board Chair and Vice Chair are
district members carrying a `role`, not a countywide section: Ogle's board
elects its officers from among its own 24 members, so there is no at-large seat
to imply. (The Chair currently sits in District 5 and the Vice Chair in
District 2 — they are not fixed to a district, which is exactly why the role
travels with the member rather than with the card.)

Usage:
    python3 build_ogle_county_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import sys
from validate_officeholder_names import is_vacancy_marker  # noqa: E402  (one reader for the word)

SOURCE_URL = "https://www.oglecountyil.gov/staff_directory/county_board_members.php"

# THE SEAT COUNT IS CARRIED INTO THE DATA, not just asserted in this docstring,
# because the card has no other way to know a district is SHORT. The floors
# below are deliberately permissive — a resignation between scrapes must not
# block a refresh — and that permissiveness had a silent side: the district
# keeps its key, one row simply stops appearing, and the card shows a smaller
# delegation than the county elects with nothing saying so. Emitting `seats`
# lets the card say "1 of 3 seats not listed in the county's directory"
# instead. It states what the source shows, never why: a row can be missing
# because a seat is empty or because the parse dropped it, and this county
# publishes nothing that tells the two apart (the Sangamon members-index
# distinction does not exist here). Making the shortfall VISIBLE is what avoids
# the false trade between a silently short card and a floor tightened to an
# equality, which would freeze the file with a departed member still named.
SEATS_PER_DISTRICT = 3

# Eight districts, three seats each. Floors, not equalities: a resignation
# between scrapes is normal and must not block a refresh, while a collapse means
# the directory table changed and the old file should stand.
MIN_DISTRICTS = 8
MIN_MEMBERS = 22
MIN_EMAILS = 20
MIN_PHONES = 20

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


def member_obj(rec):
    member = {"name": rec["name"]}
    for key in ("role", "party", "phone", "email"):
        if rec.get(key):
            member[key] = rec[key]
    return member


def resolve_roster(records):
    roster = {}
    for rec in records:
        district = str(rec.get("district") or "").strip()
        name = (rec.get("name") or "").strip()
        if not district or not name:
            continue
        slot = roster.setdefault(district, {"members": [], "seats": SEATS_PER_DISTRICT,
                                            "sourceUrl": SOURCE_URL})
        if is_vacancy_marker(name):
            # The directory prints "VACANT" in the name cell of an empty seat
            # (District 4, 2026-10-11). That is a fact about the seat, never a
            # person, so it is counted the way Logan and Sangamon count theirs
            # and the card and county page say "N of 3 seats is vacant".
            slot["vacancies"] = slot.get("vacancies", 0) + 1
            continue
        slot["members"].append(member_obj(rec))
    rank = {"Board Chair": 0, "Vice Chair": 1}
    for slot in roster.values():
        # Stable, human-meaningful order: chair, vice chair, then alphabetical —
        # so a card does not reshuffle between weekly refreshes because the
        # directory re-sorted.
        slot["members"].sort(key=lambda m: (rank.get(m.get("role"), 2), m["name"]))
    return roster


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    records = payload.get("records") if isinstance(payload, dict) else payload
    roster = resolve_roster(records or [])

    members = sum(len(v["members"]) for v in roster.values())
    emails = sum(1 for v in roster.values() for m in v["members"] if m.get("email"))
    phones = sum(1 for v in roster.values() for m in v["members"] if m.get("phone"))
    chairs = [m for v in roster.values() for m in v["members"] if m.get("role") == "Board Chair"]
    vices = [m for v in roster.values() for m in v["members"] if m.get("role") == "Vice Chair"]
    problems = []
    if len(roster) < MIN_DISTRICTS:
        problems.append("%d districts (< %d)" % (len(roster), MIN_DISTRICTS))
    if members < MIN_MEMBERS:
        problems.append("%d members (< %d)" % (members, MIN_MEMBERS))
    if emails < MIN_EMAILS:
        problems.append("%d e-mails (< %d)" % (emails, MIN_EMAILS))
    if phones < MIN_PHONES:
        problems.append("%d phones (< %d)" % (phones, MIN_PHONES))
    # A board has one chair and one vice chair. Two of either means the name cell
    # is being parsed wrong, which would put a title on someone who has none.
    if len(chairs) > 1:
        problems.append("%d members marked Board Chair" % len(chairs))
    if len(vices) > 1:
        problems.append("%d members marked Vice Chair" % len(vices))
    if problems:
        print("build-ogle-board: FAIL — refusing to overwrite a good file with a "
              "partial scrape: %s" % "; ".join(problems), file=sys.stderr)
        sys.exit(1)

    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    out_path = os.path.join(out_dir, "ogle-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False)
    print("build-ogle-board: wrote %s — %d districts, %d members, %d phones, "
          "%d e-mails, chair %s, vice chair %s"
          % (out_path, len(roster), members, phones, emails,
             chairs[0]["name"] if chairs else "unresolved",
             vices[0]["name"] if vices else "unresolved"))


if __name__ == "__main__":
    main()
