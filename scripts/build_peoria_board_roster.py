#!/usr/bin/env python3
"""
Resolve scripts/peoria_county_board_scraper.py's raw output into
data/app/peoria-county-board-members.json, keyed by board district.

Peoria seats 18 SINGLE-member districts — the fleet's largest single-member
county board — so every district key holds exactly one member. The county
publishes a party for all 18 and an e-mail for all 18; phones are per-member
and about two thirds publish one.

The Chairperson and Vice-Chairperson are marked on the member who holds each
role. Both also hold a district seat (Peoria elects them from among the 18),
so the role rides that member's district row rather than becoming a separate
countywide entry — and it is written only where the county's own index page
states it. Because that page is the only source of both roles, this builder
also floors how many of the 18 it named (MIN_ON_INDEX): the roles going quiet
because the county stopped marking them is fine, and the roles going quiet
because the parser stopped reading the page is not, and index coverage is what
tells the two apart.

index.html's consolidated county-board layer fetches this file lazily on
first click (same-origin) and joins it to the live county GIS boundary
(2020_County_Board_Districts, the adopted 2021-11-30 map) by district number.

Usage:
    python3 build_peoria_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = "https://www.peoriacounty.gov/755/County-Board-Members"

# 18 single-member districts. The county publishes an e-mail on every row and
# a party on every row; refuse to overwrite good data with a partial scrape.
EXPECT_DISTRICTS = tuple(str(n) for n in range(1, 19))
MEMBERS_PER_DISTRICT = 1
MIN_PHONES = 9
MIN_EMAILS = 16
MIN_PARTIES = 16
ALLOWED_ROLES = ("Chairperson", "Vice-Chairperson")

# HOW MANY OF THE 18 THE INDEX PAGE MUST NAME, and why this floor exists at all.
# The index is the THIRD county surface this pipeline reads and the ONLY one
# that marks the two roles, so a parser that stops reading it loses them without
# losing a member — which is exactly what happened on 2026-09-11, when three
# members moved from one heading shape to another and the run shipped a roster
# with both roles gone. The scraper had already detected it and printed the
# three names on stderr, where nothing read them.
#
# A ROLE FLOOR WOULD BE THE WRONG GUARD HERE, and deliberately is not added: the
# role block below says the cards carry no role rather than guessing one if the
# county stops marking them, and that posture is right. What must not happen is
# the roles going quiet because THIS CODE stopped reading the page. Index
# coverage is the measurement that tells those two apart.
#
# 17 tolerates exactly one miss — a member dropped from the index before the GIS
# layer catches up, or a name the two surfaces spell further apart than
# same_person absorbs — and refuses on two, because a markup change takes out a
# whole group rather than one person. The trade is deliberate: a refusal stalls
# the weekly refresh visibly and the shipped file keeps its last good contents,
# where a silent narrowing ships a thinner roster nobody notices.
MIN_ON_INDEX = 17

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("peoria-board-roster")


def main():
    if len(sys.argv) < 2:
        fail("usage: build_peoria_board_roster.py <raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    records = payload["records"]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    # The scraper's cross-check against the County Board Members index. An
    # absent block means the file predates the check rather than that the check
    # passed, so it refuses rather than skipping quietly.
    index = payload.get("index")
    if index is None:
        fail("the scraper output carries no `index` cross-check block — it is "
             "from before that check existed. Re-run "
             "scripts/peoria_county_board_scraper.py and build from its output")
    if not index.get("read"):
        # A page that could not be FETCHED is a network outage the roster should
        # survive; no role ships this run and the floor cannot be applied.
        print("peoria-board-roster: WARN — the index page was unreadable on the "
              "scrape, so no role ships and the index floor is not applied")
    elif index.get("matched", 0) < MIN_ON_INDEX:
        fail("the County Board Members index named only %d of the %d roster "
             "members (expected at least %d) — missing: %s. That page is where "
             "both roles come from, so this is a page or parser change to look "
             "at before shipping"
             % (index.get("matched", 0), index.get("rosterCount", 0),
                MIN_ON_INDEX, ", ".join(index.get("missing") or []) or "not named"))

    roster = {}
    for rec in records:
        if not rec.get("name") or not rec.get("district"):
            continue
        d = str(rec["district"])
        role = rec.get("role")
        if role and role not in ALLOWED_ROLES:
            fail("district %s carries unrecognized role %r — the index page's "
                 "wording changed; check it before shipping" % (d, role))
        member = {"name": rec["name"]}
        for key in ("party", "role", "phone", "email"):
            if rec.get(key):
                member[key] = rec[key]
        if rec.get("url") and re.match(r"^https://", rec["url"]):
            member["url"] = rec["url"]
        roster.setdefault(d, {"members": [], "sourceUrl": SOURCE_URL})
        roster[d]["members"].append(member)

    if sorted(roster, key=int) != sorted(EXPECT_DISTRICTS, key=int):
        fail("parsed districts %s, expected exactly 1-18"
             % sorted(roster, key=lambda x: int(x)))
    for d, entry in roster.items():
        if len(entry["members"]) != MEMBERS_PER_DISTRICT:
            fail("district %s has %d members, Peoria's districts each seat exactly %d"
                 % (d, len(entry["members"]), MEMBERS_PER_DISTRICT))

    members = [m for e in roster.values() for m in e["members"]]
    phones = sum(1 for m in members if m.get("phone"))
    emails = sum(1 for m in members if m.get("email"))
    parties = sum(1 for m in members if m.get("party"))
    if phones < MIN_PHONES:
        fail("only %d phones resolved (expected >= %d)" % (phones, MIN_PHONES))
    if emails < MIN_EMAILS:
        fail("only %d e-mails resolved (expected >= %d)" % (emails, MIN_EMAILS))
    if parties < MIN_PARTIES:
        fail("only %d parties resolved (expected >= %d)" % (parties, MIN_PARTIES))

    # Exactly one Chairperson and one Vice-Chairperson, or none at all (the
    # index page is the only surface that marks them; if it stops, the cards
    # simply carry no role rather than guessing one).
    for role in ALLOWED_ROLES:
        held = [m["name"] for m in members if m.get("role") == role]
        if len(held) > 1:
            fail("%d members marked %s (%s) — the board has one" % (len(held), role, ", ".join(held)))

    out_path = os.path.join(out_dir, "peoria-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    roles = sorted(m["role"] for m in members if m.get("role"))
    print("peoria-board-roster: %d districts, %d members (%d phones, %d e-mails, "
          "%d parties, %s, roles: %s) -> %s"
          % (len(roster), len(members), phones, emails, parties,
             ("%d of %d named on the county's index"
              % (index.get("matched", 0), index.get("rosterCount", 0)))
             if index.get("read") else "the county's index was unreadable",
             ", ".join(roles) or "none", out_path))


if __name__ == "__main__":
    main()
