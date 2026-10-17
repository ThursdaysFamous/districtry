#!/usr/bin/env python3
"""
Resolve scripts/marshall_county_board_scraper.py's raw output into
data/app/marshall-county-board-members.json, keyed by board district.

Marshall seats twelve members across three districts, four each, on staggered
terms — half the board expires in 2026 and half in 2028 — so the term year is
per-seat ballot information and is carried through (the Boone posture). The
county marks one Chairperson and one Vice-Chairperson by name in the table;
both are rendered as their own rows carry them, and nothing is inferred.

THE COMPOSITION CROSS-CHECK — the PDF this roster comes from is also the
authority for the district BOUNDARIES, which are Census townships dissolved per
the DISTRICT #n headings (scripts/build_marshall_board_districts.py). This
builder re-reads what the scraper saw and fails on any difference, so a
redistricting turns the weekly job red instead of leaving the derived lines a
cycle out of date.

Marshall is the cleanest fit for that check the fleet has: composition and
roster are the SAME TABLE in the SAME document, so the county cannot publish a
new roster under new districts without the check seeing both at once. (Cass, by
contrast, links its composition from a separate PDF and can only get a
seat-count tripwire.)

WHITESPACE IS NOT A NAME DIFFERENCE — the comparison is on the same
punctuation-insensitive key the boundary builder dissolves on, because the
county writes "LaPrairie" where TIGER writes "La Prairie". Re-spacing a
township name is not a redistricting and must not fail the weekly job.

BOTH OF A MEMBER'S NUMBERS SHIP. The table prints a Phone column and a column
headed "Cell/Work"; a member with both carries the Phone number in `phone` and
the other in `phonesExtra`, led by "cell or work" (the county's heading). Until
Adam's ruling of 2026-10-17 ("if the official government source uses personal
phone numbers, we publish those") only one of the two shipped. Every number is
checked for its shape (scraper_common.person_phone_problem).

Usage:
    python3 build_marshall_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_marshall_board_districts import (  # noqa: E402
    DISTRICTS as BOUNDARY_COMPOSITION, SEATS_PER_DISTRICT, norm as township_key,
)
from scraper_common import make_fail, person_phone_problem  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = ("https://marshallcountyillinois.gov/wp-content/uploads/2026/01/"
              "2026-New-County-Board-Roster-.pdf")
ROSTER_PAGE = "https://marshallcountyillinois.gov/directory/county-board/"

EXPECT_DISTRICTS = ("1", "2", "3")
MIN_PHONES = 10
MIN_EMAILS = 10
# Members carrying a second number (a Phone number and a Cell/Work number):
# measured 2 of 12 on 2026-10-17. Two thirds of 2 rounds to 1, so the build
# fails if the second column stops being read for everyone.
MIN_SECOND_NUMBERS = 1

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("marshall-board-roster")


def township_keys(text):
    """"Henry, Hopewell, LaPrairie" -> {HENRY, HOPEWELL, LAPRAIRIE}"""
    out = set()
    for chunk in re.split(r"\s*,\s*|\s+and\s+", (text or "").strip(), flags=re.I):
        chunk = re.sub(r"\s*Townships?\.?$", "", chunk.strip(), flags=re.I)
        key = township_key(chunk)
        if key:
            out.add(key)
    return out


def main():
    if len(sys.argv) < 2:
        fail("usage: build_marshall_board_roster.py <raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as f:
        records = json.load(f)["records"]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    roster, seen_composition = {}, {}
    for rec in records:
        if not rec.get("name") or not rec.get("district"):
            continue
        district = str(rec["district"])
        member = {"name": rec["name"]}
        if rec.get("role"):
            member["role"] = rec["role"]
        for key in ("phone", "phonesExtra", "email"):
            if rec.get(key):
                member[key] = rec[key]
        if rec.get("termExpires"):
            member["termExpires"] = int(rec["termExpires"])
        roster.setdefault(district, {"members": [], "sourceUrl": ROSTER_PAGE,
                                     "rosterPdf": SOURCE_URL})
        roster[district]["members"].append(member)
        if rec.get("composition"):
            seen_composition.setdefault(district, rec["composition"])

    if sorted(roster) != sorted(EXPECT_DISTRICTS):
        fail("parsed districts %s, expected exactly %s" % (sorted(roster), list(EXPECT_DISTRICTS)))
    for d, entry in roster.items():
        if len(entry["members"]) != SEATS_PER_DISTRICT:
            fail("district %s has %d members, the county seats exactly %d per district"
                 % (d, len(entry["members"]), SEATS_PER_DISTRICT))
        entry["members"].sort(key=lambda m: m["name"].split()[-1])

    # --- composition cross-check against the shipped boundary
    for d in EXPECT_DISTRICTS:
        published = township_keys(seen_composition.get(d))
        if not published:
            fail("district %s published no township composition — the PDF's shape "
                 "changed, and the shipped boundary can no longer be cross-checked" % d)
        expected = {township_key(n) for n in BOUNDARY_COMPOSITION[d]}
        if published != expected:
            gained = sorted(published - expected)
            lost = sorted(expected - published)
            bits = []
            if gained:
                bits.append("now includes %s" % ", ".join(gained))
            if lost:
                bits.append("no longer includes %s" % ", ".join(lost))
            fail("district %s composition CHANGED — the county %s. Re-read the roster "
                 "PDF and rebuild data/app/marshall-county-board-districts.json before "
                 "shipping this roster." % (d, "; ".join(bits)))

    members = [m for e in roster.values() for m in e["members"]]
    roles = sorted(m["role"] for m in members if m.get("role"))
    if roles != ["Chairperson", "Vice-Chairperson"]:
        fail("the table marks %s — expected exactly one Chairperson and one "
             "Vice-Chairperson" % (roles or "no officers"))

    phones = sum(1 for m in members if m.get("phone"))
    seconds = sum(1 for m in members if m.get("phonesExtra"))
    emails = sum(1 for m in members if m.get("email"))
    if phones < MIN_PHONES:
        fail("only %d phones resolved (expected >= %d)" % (phones, MIN_PHONES))
    if seconds < MIN_SECOND_NUMBERS:
        fail("only %d members carry a second number (expected >= %d) — the "
             "Cell/Work column may have moved" % (seconds, MIN_SECOND_NUMBERS))
    if emails < MIN_EMAILS:
        fail("only %d e-mails resolved (expected >= %d)" % (emails, MIN_EMAILS))
    # The shape of every number, named by district and seat, never by value.
    for d in EXPECT_DISTRICTS:
        for seat, member in enumerate(roster[d]["members"], 1):
            values = [("phone", member["phone"])] if member.get("phone") else []
            values += [("phonesExtra[%d]" % i, v)
                       for i, v in enumerate(member.get("phonesExtra") or [])]
            for field, value in values:
                problem = person_phone_problem(value)
                if problem:
                    fail("Marshall County District %s, seat %d of %d: %s %s"
                         % (d, seat, len(roster[d]["members"]), field, problem))

    out_path = os.path.join(out_dir, "marshall-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("marshall-board-roster: %d districts, %d members (%d phones, %d with a "
          "second number, %d e-mails); composition matches the shipped boundary in "
          "all 3 districts -> %s"
          % (len(roster), len(members), phones, seconds, emails, out_path))


if __name__ == "__main__":
    main()
