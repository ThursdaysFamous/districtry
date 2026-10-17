#!/usr/bin/env python3
"""
Write data/app/stark-county-board-members.json from the intermediate JSON
stark_county_board_scraper.py produces.

Shape matches every other county board roster the app ships: one entry per
district, each holding its members and the URL the card links.

    { "1": { "members": [ {name, email, termExpires, role} ],
             "sourceUrl": "..." }, ... }

WHAT MAKES STARK'S ROSTER UNUSUAL: the e-mail addresses belong to the SEAT, not
the person — `boarddist1-1@starkco.illinois.gov` through
`boarddist2-4@starkco.illinois.gov`. A county of 5,300 people bothering to run
positional mailboxes is better practice than most of the fleet manages, and it
means these addresses stay correct through turnover. SEAT_MAILBOX_RE reads the
district out of a seat mailbox, and the build fails when a member holds the
other district's mailbox, because then the page's rows and its seat numbering
disagree.

A PERSONAL ADDRESS SHIPS, SINCE 2026-10-17. Until that day this builder failed
on any address that was not a seat mailbox, so that a person would decide
whether a personal address in a seat's place should ship. Adam decided it on
2026-10-17 with his choice to publish personal e-mail addresses ("E-mails
too"): an address the page prints beside one member ships on that member,
checked only for its shape (scraper_common.person_email_problem). An
address printed beside two or more members is an office's or a shared inbox
and ships on neither, and one scripts/undeliverable.py lists ships nowhere.
Measured 2026-10-17, all eight addresses are seat mailboxes.

COUNT GUARDS. The board seats eight members, four from each of two districts,
and that count is pinned independently: the county's own map splits the county
into exactly two board districts, and this builder refuses to write more than
SEATS_PER_DISTRICT names into either. The floor sits two under the full board so
a genuine vacancy does not fail a Thursday run.

NO ADDRESSES REACH THIS FILE. Stark does not publish member home addresses, so
unlike McDonough there is nothing to strip — but the same belt-and-braces
assertion runs anyway, so that the day the county starts publishing them, the
build fails rather than the app quietly shipping them.

Usage:
    python3 scripts/build_stark_board_roster.py stark_board_raw.json
    python3 scripts/build_stark_board_roster.py stark_board_raw.json --check
"""

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import undeliverable  # noqa: E402  (the fleet's withhold list)
from scraper_common import person_email_problem  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "stark-county-board-members.json")

MIN_MEMBERS = 6
EXPECTED_DISTRICTS = ("1", "2")
SEATS_PER_DISTRICT = 4
# Measured 8 of 8 on 2026-10-17, all seat mailboxes; about two thirds of that,
# so a page change that stops the addresses being read fails the build.
MIN_EMAILS = 5
# A seat mailbox, boarddist<district>-<seat>. No longer the only shape that
# ships (see above); it is read to check the mailbox's district.
SEAT_MAILBOX_RE = re.compile(r"(?i)^boarddist(\d)-(\d)@starkco\.illinois\.gov$")
# Any key matching one of these would be a residence leaking into shipped data.
FORBIDDEN_KEY_PARTS = ("address", "addr", "street", "residence", "home")
YEAR_RE = re.compile(r"(20\d\d)")


def build(payload):
    members = payload.get("members") or []
    if len(members) < MIN_MEMBERS:
        raise RuntimeError("%d members < floor %d — refusing to write"
                           % (len(members), MIN_MEMBERS))

    # Each member's place on the page, so an error or a note can name the seat
    # without printing the address.
    on_page = collections.defaultdict(list)
    for member in members:
        on_page[str(member.get("district") or "").strip()].append(member)

    def seat_of(member, district):
        same = on_page[district]
        place = next(i for i, m in enumerate(same, 1) if m is member)
        return ("Stark County District %s, member %d of %d in page order"
                % (district, place, len(same)))

    # How many members each address is printed beside. One printed beside two
    # or more is an office's or a shared inbox, not either member's own.
    printed = collections.Counter(
        (m.get("email") or "").strip().lower() for m in members
        if (m.get("email") or "").strip())

    by_district = collections.defaultdict(list)
    withheld = []
    for index, member in enumerate(members, 1):
        district = str(member.get("district") or "").strip()
        name = (member.get("name") or "").strip()
        if not district or not name:
            raise RuntimeError("member row %d of %d carries no district or no "
                               "name" % (index, len(members)))

        record = {"name": name}
        email = (member.get("email") or "").strip()
        if email:
            seat = seat_of(member, district)
            problem = person_email_problem(email)
            if problem:
                raise RuntimeError("%s: the page's e-mail %s" % (seat, problem))
            mailbox = SEAT_MAILBOX_RE.match(email)
            if mailbox and mailbox.group(1) != district:
                raise RuntimeError(
                    "%s holds the district %s seat mailbox — the roster and the "
                    "seat numbering disagree" % (seat, mailbox.group(1)))
            if email.lower() in undeliverable.UNDELIVERABLE:
                withheld.append((seat, "scripts/undeliverable.py lists it as an "
                                       "address that cannot receive mail"))
            elif printed[email.lower()] > 1:
                withheld.append((seat, "the page prints it beside %d members, so "
                                       "it is not this member's own"
                                       % printed[email.lower()]))
            else:
                record["email"] = email
        if member.get("phone"):
            record["phone"] = member["phone"].strip()
        term = (member.get("term_expires") or "").strip()
        if term:
            year = YEAR_RE.search(term)
            record["termExpires"] = int(year.group(1)) if year else term
        if member.get("role"):
            # the page writes "Board Chair" / "Board Vice-Chair"; the cards
            # already sit under a board heading, so drop the redundant word
            record["role"] = re.sub(r"(?i)^board\s+", "", member["role"]).strip()

        for key in record:
            lowered = key.lower()
            if any(part in lowered for part in FORBIDDEN_KEY_PARTS):
                raise RuntimeError("refusing to ship field %r for %s — member "
                                   "home addresses never reach data/app/"
                                   % (key, name))
        by_district[district].append(record)

    emails = sum(1 for records in by_district.values() for r in records
                 if r.get("email"))
    if emails < MIN_EMAILS:
        raise RuntimeError("only %d members carry an e-mail (floor %d) — the "
                           "page changed shape" % (emails, MIN_EMAILS))
    for seat, why in withheld:
        print("  WITHHELD the e-mail the page prints for %s: %s" % (seat, why),
              file=sys.stderr)

    missing = [d for d in EXPECTED_DISTRICTS if d not in by_district]
    if missing:
        raise RuntimeError("no members for district(s) %s" % ", ".join(missing))
    unexpected = [d for d in by_district if d not in EXPECTED_DISTRICTS]
    if unexpected:
        raise RuntimeError("unknown district(s) %s — Stark's map has exactly "
                           "two board districts" % ", ".join(sorted(unexpected)))
    for district, records in sorted(by_district.items()):
        if len(records) > SEATS_PER_DISTRICT:
            raise RuntimeError("district %s has %d members but seats %d"
                               % (district, len(records), SEATS_PER_DISTRICT))

    source_url = payload.get("source_url") or ""
    out = {}
    for district, records in by_district.items():
        records.sort(key=lambda r: r["name"].rsplit(" ", 1)[-1].lower())
        out[district] = {"members": records, "sourceUrl": source_url}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", help="intermediate JSON from the scraper")
    parser.add_argument("--check", action="store_true",
                        help="compare against the shipped file; write nothing")
    args = parser.parse_args()

    with open(args.raw, encoding="utf-8") as handle:
        payload = json.load(handle)

    out = build(payload)
    text = json.dumps(out, indent=1, sort_keys=True) + "\n"

    existing = None
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as handle:
            existing = handle.read()

    if args.check:
        if existing != text:
            sys.exit("drift: %s differs from what the scrape builds" % OUT_PATH)
        print("--check: %s matches" % OUT_PATH)
        return

    if existing == text:
        print("no change")
        return

    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    total = sum(len(v["members"]) for v in out.values())
    print("wrote %s — %d members across %d districts (%s)"
          % (OUT_PATH, total, len(out),
             ", ".join("D%s=%d" % (d, len(out[d]["members"]))
                       for d in sorted(out, key=int))))


if __name__ == "__main__":
    main()
