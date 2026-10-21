#!/usr/bin/env python3
"""
Resolve scripts/macoupin_county_board_scraper.py's raw output into
data/app/macoupin-county-board-members.json, keyed by Macoupin County Board
district (9 districts of 2 members = 18 seats).

index.html's county-board layer fetches this file on first click and joins it
to data/app/macoupin-county-board-districts.json by district number.

THE DRIFT CHECK RUNS FIRST. The shipped boundary is the county's own Board
Districts layer as it stood on 2026-10-15 (build_macoupin_board_districts.py).
The scraper re-reads that layer's nine keys and each one's area; this builder
FAILS if the set of districts or any area has moved, because a moved line moves
an area. A red run here means the county redrew its board districts and the
geometry must be rebuilt (and re-witnessed) before this county ships again.
WHAT IT CANNOT SEE: a redraw that kept every district's area to the square
metre. Nothing cheaper than re-fetching the geometry could.

THE ROSTER GUARDS ARE EXACT: nine districts, two members each, eighteen in
all, every one named; the Clerk's directory states the seats exactly, so a
short list is a red run with an owner rather than a quietly smaller board. The
Chair is a separate office in the same directory and must be exactly one of
the eighteen, by name; the join is printed every run.

WHAT SHIPS: name, district, the Chair's role, the year the seat is next on the
ballot, `appointed` where the directory marks a member appointed to fill an
unexpired term, and, since 2026-10-17, the e-mail address in the seat's
second-contact slot where it is shown to be the member's (below). WHAT DOES
NOT: party, which the directory does not publish; any telephone number, because
the only per-seat number is the same slot's and nothing in a number can tie it
to the member; and the residence addresses the detail endpoint carries, which
the scraper never reads into its output.

THE SECOND-CONTACT E-MAIL SHIPS ONLY WHERE IT NAMES THE MEMBER. The slot
belongs to the office rather than the person (the municipal scraper found a
predecessor's address still sitting in a primary slot), so an address ships on
a member only when the letters of its local part contain the member's surname
(three letters or more, a Jr/Sr/II/III/IV dropped). On 2026-10-17, when Adam
chose to publish officials' own e-mail addresses, personal ones included
("E-mails too"), 14 seats carried one and 12 passed that test; the other two
are left out and the run says which districts. An address on two or more
members' seats is an office's and ships on neither, an address
scripts/undeliverable.py lists ships nowhere, and an address that would ship
must be exactly one address (scraper_common.person_email_problem). Messages
name the district and never the address.

Usage:
    python3 build_macoupin_county_board.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import undeliverable  # noqa: E402  (the fleet's withhold list)
from build_macoupin_board_districts import (  # noqa: E402  (constants only)
    DISTRICT_AREAS, EXPECT_DISTRICTS, SEATS_PER_DISTRICT,
)
from scraper_common import make_fail, person_email_problem  # noqa: E402  (shared machinery -- do not fork)
from vtd_board_districts import norm  # noqa: E402  (shared machinery -- do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
OUT_NAME = "macoupin-county-board-members.json"
EXPECT_MEMBERS = EXPECT_DISTRICTS * SEATS_PER_DISTRICT
CHAIR_ROLE = "Chair"
# Shape__Area is a float the service recomputes; a whole square metre is far
# below any line a redraw would move.
AREA_TOLERANCE_M2 = 1.0
# Second-contact e-mails that name their member: 12 of 18 seats, measured
# 2026-10-17. About two thirds, so a change that stops the slot being read
# fails the build instead of emptying the e-mails quietly.
MIN_EMAILS = 8
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}

fail = make_fail("macoupin-board-roster")


def surname_of(name):
    """The last word of a ballot name, letters only, lower case, a Jr/Sr/II/
    III/IV dropped."""
    words = [w for w in re.sub(r"[^A-Za-z\s'-]", " ", name or "").lower().split()
             if w not in NAME_SUFFIXES]
    return re.sub(r"[^a-z]", "", words[-1]) if words else ""


def names_member(email, name):
    """True when the letters of the address's local part contain the member's
    surname of three letters or more."""
    surname = surname_of(name)
    local = re.sub(r"[^a-z]", "", email.split("@", 1)[0].lower())
    return len(surname) >= 3 and surname in local


def second_emails(seats):
    """({index into seats: address}, [notes]): the second-contact e-mails that
    ship, and why each of the others does not. See the module docstring."""
    holders = {}
    for seat in seats:
        value = (seat.get("email2") or "").strip()
        if value:
            holders.setdefault(value.lower(), set()).add(norm(seat.get("name") or ""))
    keep, notes = {}, []
    for i, seat in enumerate(seats):
        value = (seat.get("email2") or "").strip()
        if not value:
            continue
        where = "District %s, %s" % (seat.get("district"), (seat.get("name") or "").strip())
        if len(holders[value.lower()]) > 1:
            notes.append("%s: the directory gives the same e-mail to %d members, so "
                         "it is the office's and ships on none"
                         % (where, len(holders[value.lower()])))
        elif value.lower() in undeliverable.UNDELIVERABLE:
            notes.append("%s: scripts/undeliverable.py lists the e-mail as an "
                         "address that cannot receive mail" % where)
        elif not names_member(value, seat.get("name")):
            notes.append("%s: the e-mail's local part does not carry the member's "
                         "surname, so it is not shown to be theirs" % where)
        else:
            problem = person_email_problem(value)
            if problem:
                fail("Macoupin County %s: the directory's e-mail %s" % (where, problem))
            keep[i] = value
    return keep, notes


def main():
    if len(sys.argv) < 2:
        fail("usage: build_macoupin_county_board.py <raw.json> [output_dir]")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    with open(sys.argv[1], encoding="utf-8") as handle:
        raw = json.load(handle)

    areas = raw.get("districtAreas") or {}
    if sorted(areas) != sorted(DISTRICT_AREAS):
        fail("the county's Board Districts layer now keys %s, the shipped boundary "
             "keys %s — re-run build_macoupin_board_districts.py and re-witness it"
             % (sorted(areas), sorted(DISTRICT_AREAS)))
    for d, shipped in sorted(DISTRICT_AREAS.items(), key=lambda kv: int(kv[0])):
        got = areas[d]
        if not isinstance(got, (int, float)) or abs(got - shipped) > AREA_TOLERANCE_M2:
            fail("District %s's area in the county layer is %r m2, the shipped "
                 "boundary's is %d — the county redrew it; re-run "
                 "build_macoupin_board_districts.py and re-witness it" % (d, got, shipped))

    seats = raw.get("seats") or []
    if len(seats) != EXPECT_MEMBERS:
        fail("the directory lists %d board seats, expected %d" % (len(seats), EXPECT_MEMBERS))
    emails, email_notes = second_emails(seats)
    roster = {}
    for i, seat in enumerate(seats):
        d = str(seat.get("district") or "")
        if d not in DISTRICT_AREAS:
            fail("a seat names district %r, which the boundary does not carry" % d)
        name = (seat.get("name") or "").strip()
        if not name or seat.get("vacant"):
            fail("District %s has a seat with no holder" % d)
        member = {"name": name}
        if seat.get("appointed"):
            member["appointed"] = True
        if seat.get("nextElection"):
            member["nextElection"] = str(seat["nextElection"])
        if i in emails:
            member["email"] = emails[i]
        roster.setdefault(d, {"members": [], "sourceUrl": raw["source"]})["members"].append(member)
    if len(emails) < MIN_EMAILS:
        fail("only %d members carry an e-mail that names them (floor %d) — the "
             "directory's detail records may have changed shape" % (len(emails), MIN_EMAILS))
    if len(roster) != EXPECT_DISTRICTS:
        fail("the directory names members in %d districts, expected %d"
             % (len(roster), EXPECT_DISTRICTS))
    for d, entry in roster.items():
        names = [m["name"] for m in entry["members"]]
        if len(names) != SEATS_PER_DISTRICT:
            fail("District %s lists %d members, expected %d"
                 % (d, len(names), SEATS_PER_DISTRICT))
        if len(set(norm(n) for n in names)) != len(names):
            fail("District %s lists one person twice: %r" % (d, names))
        entry["members"].sort(key=lambda m: m["name"])

    chair = (raw.get("chair") or "").strip()
    hits = [(d, m) for d, e in roster.items() for m in e["members"]
            if norm(m["name"]) == norm(chair)]
    if len(hits) != 1:
        fail("the Chair %r matches %d board members, expected exactly 1" % (chair, len(hits)))
    hits[0][1]["role"] = CHAIR_ROLE
    print("macoupin-board-roster: Chair %r joined to District %s by name" % (chair, hits[0][0]))

    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(roster, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    appointed = sum(1 for e in roster.values() for m in e["members"] if m.get("appointed"))
    print("macoupin-board-roster: wrote %s — %d members in %d districts, %d appointed "
          "to fill an unexpired term, %d with an e-mail that names them (of %d "
          "seats whose slot holds one)"
          % (os.path.relpath(path, REPO_ROOT), EXPECT_MEMBERS, len(roster), appointed,
             len(emails), sum(1 for s in seats if (s.get("email2") or "").strip())))
    for note in email_notes:
        print("  NOT SHIPPED — %s" % note)
    print("macoupin-board-roster: the county's district layer still matches the "
          "shipped boundary by key and area; a redraw keeping every area would not "
          "show here")


if __name__ == "__main__":
    main()
