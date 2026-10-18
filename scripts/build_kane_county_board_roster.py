#!/usr/bin/env python3
"""
Resolve scripts/kane_county_board_scraper.py's raw output into
data/app/kane-county-board-members.json, keyed by Kane County Board district
("1".."24" — 24 single-member districts) plus a top-level "chair" for the
countywide-elected Board Chair (the DuPage/McHenry roster shape).

index.html's consolidated county-board layer fetches this file lazily on
first click (same-origin) and joins it to the county's own
KaneCo_IL_County_Board boundary GIS by district number. The GIS keeps
carrying the sitting member's NAME (used for hover and as the card's
fallback); this roster enriches the card with party, the member's office
phone, email, and a profile link. Since Adam's ruling of 2026-10-17 ("if the
official government source uses personal phone numbers, we publish those") it
also carries, in `phonesExtra`, the home, work and cell numbers the county
lists for a member, each led by the county's own label; every number is
checked for its shape (scraper_common.person_phone_problem). Stage 2 of the
two-stage pipeline (see scripts/kane_county_board_scraper.py); mirrors
build_mchenry_county_board_roster.py.

Usage:
    python3 build_kane_county_board_roster.py <raw-scraper-output.json> [output_dir]

output_dir defaults to the repo's data/app/ directory.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import person_phone_problem  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = "https://www2.kanecountyil.gov/pages/countyboard/boardMembers.aspx"

# 24 single-member districts + the countywide Chair. Refuse to overwrite the
# file with a suspiciously partial scrape rather than silently wiping good
# data — the same safety net as the sibling board builders.
MIN_DISTRICTS = 22
MIN_MEMBERS = 22
# Every list record publishes an email; a collapse means the list schema
# moved (e.g. the E-Mail column renamed), not the members.
MIN_EMAILS = 20
# Every record publishes an Office line: measured on 24 of 24 district members
# (and the Chair) on 2026-10-17.
MIN_PHONES = 16
# A second number (the member's own cell, home or work line, beside the Office
# one): measured on 5 of the 24 district members on 2026-10-17, 6 numbers in
# all (cell 4, home 1, work 1); the Chair carries none. Two thirds of 5, so a
# list change that stops these being read fails the build instead of emptying
# them.
MIN_SECOND_NUMBERS = 3

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


def member_obj(rec):
    member = {"name": rec["name"]}
    for k in ("role", "party", "phone", "phonesExtra", "email", "url"):
        if rec.get(k):
            member[k] = rec[k]
    return member


def phone_problems(roster):
    """Every number that is not one telephone number led by its label, named by
    seat and field only — never by the value."""
    out = []
    for key, entry in roster.items():
        members = [entry] if key == "chair" else entry["members"]
        seat = "the countywide Chair" if key == "chair" else "District %s" % key
        for member in members:
            values = [("phone", member["phone"])] if member.get("phone") else []
            values += [("phonesExtra[%d]" % i, v)
                       for i, v in enumerate(member.get("phonesExtra") or [])]
            for field, value in values:
                problem = person_phone_problem(value)
                if problem:
                    out.append("Kane County %s: %s %s" % (seat, field, problem))
    return out


def resolve_roster(records):
    roster = {}
    chair = None
    for rec in records:
        if not rec.get("name"):
            continue
        if rec.get("role") == "Chair" and rec.get("district") is None:
            chair = member_obj(rec)
            continue
        district = rec.get("district")
        if district is None:
            continue
        roster.setdefault(str(district), {"members": [], "sourceUrl": SOURCE_URL})
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
        print("WARNING: only %d/%d+ members parsed across %d districts — likely list "
              "drift; refusing to overwrite" % (total_members, MIN_MEMBERS, len(districts)),
              file=sys.stderr)
        sys.exit(1)
    if total_emails < MIN_EMAILS:
        print("WARNING: only %d/%d+ member emails parsed — the E-Mail column likely "
              "moved; refusing to overwrite" % (total_emails, MIN_EMAILS), file=sys.stderr)
        sys.exit(1)
    if not roster.get("chair", {}).get("email"):
        print("WARNING: no countywide Chair with an email resolved — the Chairman "
              "flag parse likely broke; refusing to overwrite", file=sys.stderr)
        sys.exit(1)
    total_phones = sum(1 for d in districts for m in roster[d]["members"] if m.get("phone"))
    total_seconds = sum(1 for d in districts for m in roster[d]["members"]
                        if m.get("phonesExtra"))
    if total_phones < MIN_PHONES:
        print("WARNING: only %d/%d+ member phones parsed — the Office column likely "
              "moved; refusing to overwrite" % (total_phones, MIN_PHONES), file=sys.stderr)
        sys.exit(1)
    if total_seconds < MIN_SECOND_NUMBERS:
        print("WARNING: only %d/%d+ members carry a second number — the Home, Work "
              "or Cell columns likely moved; refusing to overwrite"
              % (total_seconds, MIN_SECOND_NUMBERS), file=sys.stderr)
        sys.exit(1)
    problems = phone_problems(roster)
    if problems:
        for problem in problems:
            print("FAIL: %s" % problem, file=sys.stderr)
        sys.exit(1)

    # district keys in numeric order, chair last
    ordered = {d: roster[d] for d in sorted(districts, key=int)}
    ordered["chair"] = roster["chair"]
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "kane-county-board-members.json")
    with open(out_path, "w") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("Wrote %s: %d districts + chair, %d members, %d phones (%d with a second "
          "number), %d emails"
          % (out_path, len(districts), total_members, total_phones, total_seconds,
             total_emails), file=sys.stderr)


if __name__ == "__main__":
    main()
