#!/usr/bin/env python3
"""
Resolve scripts/vermilion_county_board_scraper.py's raw output into
data/app/vermilion-county-board-members.json, keyed by Vermilion County Board
district (9 districts x 3 members = 27 seats).

index.html's consolidated county-board layer fetches this file lazily on first
click and joins it to data/app/vermilion-county-board-districts.json by district
number.

THE PEOPLE COME FROM THE COUNTY'S OWN MEMBERS PAGE and nowhere else. Vermilion's
GIS publishes a CountyBoardDistricts layer whose attribute table carries three
Name/Party/Elected/Email sets per district, which looks like a roster and is a
2018-vintage snapshot on a retired e-mail domain. Geometry from the county's
service, PEOPLE FROM WHAT THE COUNTY MAINTAINS AS PEOPLE.

CROSS-CHECKED AGAINST CERTIFIED RETURNS, and the check is a gate. Vermilion's
two election authorities publish per-precinct canvasses, and the members this
page names for the districts those canvasses most recently elected must be the
people those canvasses elected. The names below were confirmed against the
Danville Election Commission's 17 March 2026 General Primary (District 7's
Christine L. Lamar and Timothy Morgan, District 9's James McMahon) at the time
this builder was written; what the builder itself enforces is the shape the page
must keep — 27 members, nine districts, three apiece.

WHAT SHIPS: name, party, the year the member was elected or appointed, and the
e-mail address the page prints beside the member. The board office's address and
phone ride the roster block, so a card for a member with no direct phone still
tells a reader where to reach the board.

WHAT DOES NOT SHIP: nothing is dropped from this page — it publishes no home
addresses, and measured 2026-10-17 every e-mail it prints is a work address on
the county's domain. Only one member publishes a direct phone, and that is the
county's choice rather than a parse failure, which is why the phone floor below
is 1 and not 27.

E-MAIL ON ANY DOMAIN, SINCE 2026-10-17. Until that day this builder failed the
run on any address not on the county's domain, vercounty.org, on the reading
that the county might have moved its mail. Under Adam's choice that day to
publish personal e-mail addresses ("E-mails too"), an address the page prints
beside one member ships on that member whatever its domain, checked only for
its shape (scraper_common.person_email_problem). An address printed beside two
or more members is an office's or a shared inbox and ships on neither, and an
address scripts/undeliverable.py lists ships nowhere. What stays of the old
check is a tripwire for a MOVE: the run fails when more than half of the
addresses the page prints are off vercounty.org, because a county that moves
its mail moves every member's address at once, while a member's own address is
one row. It would also catch the members page being filled from a stale source
such as the county's district layer, whose addresses are on a domain the county
has retired. Measured 2026-10-17, all 27 addresses are on vercounty.org.

Usage:
    python3 build_vermilion_county_board.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys
import undeliverable  # noqa: E402  (the fleet's withhold list)
from scraper_common import make_fail, person_email_problem  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

SOURCE_LABEL = "Vermilion County Board members page"
# Not an allow-list since 2026-10-17: a member's own address on another domain
# ships. The run fails only when more than half the printed addresses are off
# this domain, which is what a move of the county's mail would look like.
COUNTY_EMAIL_DOMAIN = "vercounty.org"

EXPECTED_DISTRICTS = 9
SEATS_PER_DISTRICT = 3
EXPECT_MEMBERS = EXPECTED_DISTRICTS * SEATS_PER_DISTRICT   # 27

MIN_EMAILS = 25          # 27 published, none personal (measured 2026-10-17); a floor, not a target
MIN_PHONES = 1           # exactly one member publishes a direct line
MIN_PARTIES = 25         # 27 published


fail = make_fail("vermilion-board-roster")


def main():
    if len(sys.argv) < 2:
        fail("usage: build_vermilion_county_board.py <raw.json> [out_dir]")
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    members = raw.get("members") or []
    if len(members) != EXPECT_MEMBERS:
        fail("the scrape yielded %d member(s), expected %d"
             % (len(members), EXPECT_MEMBERS))

    office = raw.get("office") or {}
    source_url = raw.get("sourceUrl") or ""
    if not source_url:
        fail("the scrape carries no source URL")

    roster = {}
    for person in members:
        dnum = str(person.get("district") or "").strip()
        if not dnum.isdigit() or not 1 <= int(dnum) <= EXPECTED_DISTRICTS:
            fail("a member carries the unreadable district %r"
                 % person.get("district"))
        member = {"name": re.sub(r"\s+", " ", person["name"]).strip()}
        for field in ("role", "party"):
            if person.get(field):
                member[field] = person[field]
        if person.get("elected"):
            # "Elected/Appointed" on the county's own table: the year the member
            # took the seat, which is not necessarily an election year for them.
            member["since"] = person["elected"]
        email = (person.get("email") or "").strip()
        if email:
            member["email"] = email  # checked below, seat by seat
        if person.get("phone"):
            member["phone"] = person["phone"]
        entry = roster.setdefault(dnum, {
            "members": [],
            "sourceUrl": source_url,
            "sourceLabel": SOURCE_LABEL,
            "seats": SEATS_PER_DISTRICT,
        })
        if office.get("address"):
            entry["officeAddress"] = office["address"]
        if office.get("phone"):
            entry["officePhone"] = office["phone"]
        entry["members"].append(member)

    if sorted(roster, key=int) != [str(i) for i in range(1, EXPECTED_DISTRICTS + 1)]:
        fail("parsed districts %s, expected 1-%d"
             % (sorted(roster, key=int), EXPECTED_DISTRICTS))
    for dnum in sorted(roster, key=int):
        entry = roster[dnum]
        entry["members"].sort(key=lambda m: m["name"].split()[-1].lower())
        if len(entry["members"]) > SEATS_PER_DISTRICT:
            fail("district %s lists %d members for %d seats"
                 % (dnum, len(entry["members"]), SEATS_PER_DISTRICT))

    # E-mail, seat by seat in the shipped order. Errors and notes name the seat
    # and never the address.
    printed = {}
    for entry in roster.values():
        for m in entry["members"]:
            if m.get("email"):
                printed[m["email"].lower()] = printed.get(m["email"].lower(), 0) + 1
    withheld, printed_total, off_domain = [], 0, 0
    for dnum in sorted(roster, key=int):
        named = roster[dnum]["members"]
        for i, m in enumerate(named, 1):
            email = m.get("email")
            if not email:
                continue
            seat = ("Vermilion County District %s, member %d of %d in surname order"
                    % (dnum, i, len(named)))
            problem = person_email_problem(email)
            if problem:
                fail("%s: the page's e-mail %s" % (seat, problem))
            printed_total += 1
            if email.rsplit("@", 1)[1].lower() != COUNTY_EMAIL_DOMAIN:
                off_domain += 1
            if email.lower() in undeliverable.UNDELIVERABLE:
                del m["email"]
                withheld.append((seat, "scripts/undeliverable.py lists it as an "
                                       "address that cannot receive mail"))
            elif printed[email.lower()] > 1:
                del m["email"]
                withheld.append((seat, "the page prints it beside %d members, so "
                                       "it is not this member's own"
                                       % printed[email.lower()]))
    if off_domain * 2 > printed_total:
        fail("%d of the %d e-mail addresses the page prints are not on %s — the "
             "county may have moved its mail, and a human should confirm before "
             "addresses on a new domain ship"
             % (off_domain, printed_total, COUNTY_EMAIL_DOMAIN))

    flat = [m for v in roster.values() for m in v["members"]]
    emails = sum(1 for m in flat if m.get("email"))
    phones = sum(1 for m in flat if m.get("phone"))
    parties = sum(1 for m in flat if m.get("party"))
    if emails < MIN_EMAILS:
        fail("only %d/%d members carry an e-mail (floor %d) — the county's "
             "table changed shape" % (emails, EXPECT_MEMBERS, MIN_EMAILS))
    if phones < MIN_PHONES:
        fail("no member carries a phone (floor %d) — the county's table changed "
             "shape" % MIN_PHONES)
    if parties < MIN_PARTIES:
        fail("only %d/%d members carry a party (floor %d)"
             % (parties, EXPECT_MEMBERS, MIN_PARTIES))

    seated = sum(len(v["members"]) for v in roster.values())
    out_path = os.path.join(out_dir, "vermilion-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(roster, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    print("vermilion-board-roster: wrote %s — %d districts, %d of %d seats named "
          "(%d e-mails, %d of the %d printed not on %s; %d phone, %d parties)"
          % (os.path.relpath(out_path, REPO_ROOT), EXPECTED_DISTRICTS, seated,
             EXPECT_MEMBERS, emails, off_domain, printed_total,
             COUNTY_EMAIL_DOMAIN, phones, parties))
    for seat, why in withheld:
        print("  WITHHELD the e-mail the page prints for %s: %s" % (seat, why))
    for dnum in sorted(roster, key=int):
        entry = roster[dnum]
        if len(entry["members"]) < SEATS_PER_DISTRICT:
            print("  district %s names %d of %d seats — the card says so rather "
                  "than padding" % (dnum, len(entry["members"]), SEATS_PER_DISTRICT))


if __name__ == "__main__":
    main()
