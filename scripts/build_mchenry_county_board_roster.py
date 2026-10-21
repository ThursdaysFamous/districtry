#!/usr/bin/env python3
"""
Resolve scripts/mchenry_county_board_scraper.py's raw output into
data/app/mchenry-county-board-members.json, keyed by McHenry County Board
district ("1".."9" — 9 districts electing 2 members each) plus a top-level
"chair" for the countywide-elected Board Chairman (the DuPage roster shape).

index.html's consolidated county-board layer fetches this file lazily on
first click (same-origin) and joins it to the county's own boundary GIS by
district number — the same boundary+roster join the Will, DuPage, and
Kendall entries use. Stage 2 of the two-stage pipeline (see
scripts/mchenry_county_board_scraper.py); mirrors
build_dupage_county_board_roster.py.

EVERY NUMBER A MEMBER'S PAGE PRINTS SHIPS. The first goes in `phone` and any
others in `phonesExtra`, each led by the page's own annotation ("home", "cell",
"work", "mobile") where it gives one. Until Adam's ruling of 2026-10-17 ("if the
official government source uses personal phone numbers, we publish those") only
the first number shipped and its annotation was dropped. Every number is checked
for its shape (scraper_common.person_phone_problem) and the error names the
seat, never the number.

Usage:
    python3 build_mchenry_county_board_roster.py <raw-scraper-output.json> [output_dir]

output_dir defaults to the repo's data/app/ directory.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import person_phone_problem  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = "https://www.mchenrycountyil.gov/departments/county-board/meet-your-county-board-members"

# THE SEAT COUNT IS CARRIED INTO THE DATA, not just asserted in this docstring,
# because the card has no other way to know a district is SHORT. The floors
# below are deliberately permissive — a resignation between scrapes must not
# block a refresh — and that permissiveness had a silent side: the district
# keeps its key, one row simply stops appearing, and the card shows a smaller
# delegation than the county elects with nothing saying so. Emitting `seats`
# lets the card say "1 of 2 seats not listed in the county's directory"
# instead. It states what the source shows, never why: a row can be missing
# because a seat is empty or because the parse dropped it, and this county
# publishes nothing that tells the two apart (the Sangamon members-index
# distinction does not exist here). Making the shortfall VISIBLE is what avoids
# the false trade between a silently short card and a floor tightened to an
# equality, which would freeze the file with a departed member still named.
SEATS_PER_DISTRICT = 2

# 9 districts x 2 members + the countywide Chairman. Refuse to overwrite the
# file with a suspiciously partial scrape rather than silently wiping good
# data — the same safety net as the sibling board builders.
MIN_DISTRICTS = 9
MIN_MEMBERS = 16
# Every member page publishes an email; a collapse in the count means the
# contact-block parse broke, not the members.
MIN_EMAILS = 14
# Every member page printed a number on 2026-10-17 bar one (18 of 19), so a
# collapse means the number parse broke. Two thirds of 18.
MIN_PHONES = 12
# Members whose page prints a second number of their own (a cell beside a work
# line): measured 1 of 19 on 2026-10-17. Two thirds of 1 rounds to 1, so the
# build fails if the second number stops being read; if that member stops
# printing one, lower this floor rather than reading the page differently.
MIN_SECOND_NUMBERS = 1

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


def member_obj(rec):
    # url is the member's own profile page on the county directory (the card
    # renders it as the Profile link). The scraper's term and the pages'
    # street addresses are deliberately NOT carried: term-end isn't card
    # material, and the addresses are residences, not offices. Every number the
    # page prints is carried (`phone`, then `phonesExtra`), per Adam's ruling
    # of 2026-10-17.
    member = {"name": rec["name"]}
    for k in ("role", "phone", "phonesExtra", "email"):
        if rec.get(k):
            member[k] = rec[k]
    # `url` under either name. The hand-verified seed carried it as `url`; the
    # scraper — which could not run at all while the county's edge refused every
    # rung — emits `source_url`, as Kendall's does and as its builder already
    # reads. The mismatch was invisible for as long as nothing scraped: the
    # first live run since July would have shipped nineteen members with no
    # Profile link, and check_roster_retention caught exactly that.
    profile = rec.get("url") or rec.get("source_url")
    if profile:
        member["url"] = profile
    return member


def resolve_roster(records):
    roster = {}
    chair = None
    for rec in records:
        if not rec.get("name"):
            continue
        if rec.get("role") == "Chairman" and rec.get("district") is None:
            chair = member_obj(rec)
            continue
        district = rec.get("district")
        if district is None:
            continue
        roster.setdefault(str(district), {"members": [], "seats": SEATS_PER_DISTRICT,
                                          "sourceUrl": SOURCE_URL})
        roster[str(district)]["members"].append(member_obj(rec))
    if chair:
        roster["chair"] = chair
    return roster


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: %s <raw-scraper-output.json> [output_dir]" % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        records = json.load(f)
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR

    roster = resolve_roster(records)
    districts = [k for k in roster if k != "chair"]
    total_members = sum(len(roster[d]["members"]) for d in districts)
    total_emails = sum(1 for d in districts for m in roster[d]["members"] if m.get("email"))

    if len(districts) < MIN_DISTRICTS:
        print("WARNING: resolved only %d/%d districts — refusing to overwrite the "
              "roster with an incomplete scrape" % (len(districts), MIN_DISTRICTS),
              file=sys.stderr)
        sys.exit(1)
    if total_members < MIN_MEMBERS:
        print("WARNING: only %d/%d+ members parsed across %d districts — likely site "
              "drift; refusing to overwrite" % (total_members, MIN_MEMBERS, len(districts)),
              file=sys.stderr)
        sys.exit(1)
    if total_emails < MIN_EMAILS:
        print("WARNING: only %d/%d+ member emails parsed — the contact-block parse "
              "likely broke; refusing to overwrite" % (total_emails, MIN_EMAILS),
              file=sys.stderr)
        sys.exit(1)
    if not roster.get("chair", {}).get("email"):
        print("WARNING: no countywide Chairman with an email resolved — the chair "
              "section parse likely broke; refusing to overwrite", file=sys.stderr)
        sys.exit(1)

    seats = [("McHenry County District %s, seat %d of %d" % (d, i, len(roster[d]["members"])), m)
             for d in sorted(districts, key=int)
             for i, m in enumerate(roster[d]["members"], 1)]
    seats.append(("the countywide Chairman", roster["chair"]))
    total_phones = sum(1 for _seat, m in seats if m.get("phone"))
    total_seconds = sum(1 for _seat, m in seats if m.get("phonesExtra"))
    if total_phones < MIN_PHONES:
        print("WARNING: only %d/%d+ member phones parsed — the number parse likely "
              "broke; refusing to overwrite" % (total_phones, MIN_PHONES), file=sys.stderr)
        sys.exit(1)
    if total_seconds < MIN_SECOND_NUMBERS:
        print("WARNING: only %d/%d+ members carry a second number — the member pages' "
              "layout may have changed; refusing to overwrite"
              % (total_seconds, MIN_SECOND_NUMBERS), file=sys.stderr)
        sys.exit(1)
    # The shape of every number, named by seat, never by value.
    for seat, member in seats:
        values = [("phone", member["phone"])] if member.get("phone") else []
        values += [("phonesExtra[%d]" % i, v)
                   for i, v in enumerate(member.get("phonesExtra") or [])]
        for field, value in values:
            problem = person_phone_problem(value)
            if problem:
                print("WARNING: %s: %s %s — refusing to overwrite" % (seat, field, problem),
                      file=sys.stderr)
                sys.exit(1)

    # district keys in numeric order, chair last
    ordered = {d: roster[d] for d in sorted(districts, key=int)}
    ordered["chair"] = roster["chair"]
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "mchenry-county-board-members.json")
    with open(out_path, "w") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("Wrote %s: %d districts + chair, %d members, %d emails, %d phones "
          "(%d with a second number)"
          % (out_path, len(districts), total_members, total_emails, total_phones,
             total_seconds), file=sys.stderr)


if __name__ == "__main__":
    main()
