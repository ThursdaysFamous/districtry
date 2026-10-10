#!/usr/bin/env python3
"""
Resolve scripts/carroll_county_board_scraper.py's raw output into
data/app/carroll-county-board-members.json, keyed by Carroll County Board
district ("1".."3" — three districts electing three members each, 9 seats).

index.html's consolidated county-board layer fetches this file lazily on first
click (same-origin) and joins it by district number to
data/app/carroll-county-board-districts.json, the township dissolve built by
build_carroll_board_districts.py from the county's published district map.
Carroll is the fleet's third county where BOTH halves are DERIVED rather than
fetched, after Livingston and Ogle, and for the same reason: it publishes
officeholders and a readable district map but no district geometry.

THE DISTRICT KEY IS ARABIC. The county's directory writes Roman numerals
("District II") while its map uses "District 2"; the scraper converts, so this
file and the boundary agree.

Shape mirrors the other rosters — {district: {members: [...], seats, sourceUrl}}.
The Board Chair and Vice Chair are district members carrying a `role`, not a
countywide section: Carroll's board elects its officers from among its own 9
members, so there is no at-large seat to imply.

Usage:
    python3 build_carroll_county_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import sys

SOURCE_URL = "https://www.carrollcountyil.gov/government/county_board/index.php"

# THE SEAT COUNT IS CARRIED INTO THE DATA, not just asserted in this docstring,
# because the card has no other way to know a district is SHORT. Emitting
# `seats` lets the card say "1 of 3 seats not listed in the county's directory"
# instead of quietly showing two names where three belong — the Ogle/DeKalb/
# Kendall pattern. It states what the source shows, never why: a row can be
# missing because a seat is empty or because the parse dropped it, and this
# county publishes nothing that tells the two apart.
SEATS_PER_DISTRICT = 3

# Three districts, three seats each. Floors, not equalities: a resignation
# between scrapes is normal and must not block a refresh, while a collapse means
# the directory table changed and the old file should stand.
#
# MIN_MEMBERS was 9 (the full board) DELIBERATELY, not one under, to force a
# human to confirm any vacancy before it shipped — the county has "District"
# typo'd as "Distirct" on one row, and the first version of the scraper
# silently dropped that member, which a floor of 8 would not have caught. That
# confirmation happened on 2026-08-24: the live directory was read directly and
# genuinely lists 8, District III down to Iske and Beyers with Kevin Barnes no
# longer on the page. Now that `seats` makes a shortfall VISIBLE on the card
# instead of silent, the floor can drop to match the confirmed count rather
# than continuing to block every refresh until the vacant seat is filled.
MIN_DISTRICTS = 3
MIN_MEMBERS = 8
MIN_EMAILS = 8
MIN_PHONES = 8

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
        print("build-carroll-board: FAIL — refusing to overwrite a good file with a "
              "partial scrape: %s" % "; ".join(problems), file=sys.stderr)
        sys.exit(1)

    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    out_path = os.path.join(out_dir, "carroll-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False)
    print("build-carroll-board: wrote %s — %d districts, %d members, %d phones, "
          "%d e-mails, chair %s, vice chair %s"
          % (out_path, len(roster), members, phones, emails,
             chairs[0]["name"] if chairs else "unresolved",
             vices[0]["name"] if vices else "unresolved"))


if __name__ == "__main__":
    main()
