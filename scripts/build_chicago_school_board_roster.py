#!/usr/bin/env python3
"""
Resolve scripts/cps_board_scraper.py's raw output into
il/data/app/school-board-members.json, keyed by the same district number the
Elected School Board District geometry carries.

THE TWO PUBLISHERS NUMBER THE SAME SEATS DIFFERENTLY, and that is the whole of
this builder's join. The shipped boundary calls them 1..20 and carries each
one's sub-district label beside it ("District 9a"); the Board calls them 1A..10B
and carries no flat number at all. So the map is READ OFF THE SHIPPED GEOMETRY
rather than written down here — a hardcoded table would keep answering after a
re-districting moved the labels, and it is exactly the kind of table this fleet
has had to correct county by county.

WHAT THIS REPLACED. The file was hand-curated, its provenance note said no
machine-readable roster is published for this board, and by 2026-09-23 it was
wrong about two of twenty seats: District 9a shipped the bare string VACANT
where the Board names its Vice President, and District 10b named a member who
resigned in March 2026. scripts/cps_board_scraper.py's docstring carries the
measurement.

THREE GUARDS, and each answers a different way for this source to go wrong:

  * TWO WITNESSES PER SEAT. The Board's index and each member's own bio page
    state name, role and district separately, and every one of the 21 must
    agree. The index is one block of repeating markup, so a pattern that reads
    it wrongly reads every row wrongly and every count still passes.
  * EVERY DISTRICT THE GEOMETRY DRAWS MUST BE NAMED. A district the Board's
    index does not carry FAILS the build. It is never read as a vacancy: on
    2026-09-23 CPS's own page omitted District 10B altogether while the Board
    named Connie L. Anderson in it, so a list that does not mention a seat is a
    list that is behind.
  * A VACANCY IS THE BOARD'S OWN WORD, and becomes structural. Where the Board
    prints one of the vacancy sentinels where a name goes, the seat ships as
    {"vacant": true} rather than as a person of that name — the shape the card
    and scripts/build_officeholder_tables.py already render, shared with the
    other two Illinois pipelines through is_vacancy_marker().

THE PRESIDENT IS NOT A DISTRICT SEAT. He is appointed city-wide and the Board's
index says so by giving his row an EMPTY district span, so he rides the `board`
block with the Board's own office rather than being filed under a district he
does not hold. The block also carries the office address and telephone from the
Board's own hCard, which is the card-order location row this card has never had.

ONLY AN OFFICE RIDES A MEMBER ROW AS A ROLE. Eighteen of the twenty are
published as "Member", which is what the card's own badge already says, so
carrying it would put the same word on every row; the Vice President's office
is what a reader could not otherwise know.

Usage:
    python3 build_chicago_school_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_common import make_fail                              # noqa: E402
from validate_officeholder_names import (                         # noqa: E402
    is_vacancy_marker, why_not_a_name)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
GEOMETRY = os.path.join(REPO_ROOT, "il", "data", "app", "school-board-districts.json")

SOURCE_URL = "https://www.cpsboe.org/about/bios"

# The Board seats twenty sub-district members plus a president. Both are exact
# rather than floors: the number of sub-districts is the number of polygons the
# app draws, and a board with two presidents is a parse that has gone wrong.
EXPECT_PRESIDENTS = 1
MIN_EMAILS = 18

DISTRICT_RE = re.compile(r"(?i)^district\s+(?P<label>\d+[a-z]?)$")

fail = make_fail("chicago-school-board-roster")


def sub_district_map(path=GEOMETRY):
    """{"9A": "17", ...} — read off the shipped boundary, never written down.

    The geometry's own longName is the Board's label ("District 9a"), so the
    two publishers are joined by the one string they share. A polygon whose
    longName stops looking like one fails here rather than dropping a seat.
    """
    with open(path, encoding="utf-8") as handle:
        features = json.load(handle)["features"]
    out = {}
    for feature in features:
        props = feature.get("properties") or {}
        number, long_name = props.get("district"), props.get("longName")
        m = DISTRICT_RE.match(str(long_name or ""))
        if number is None or not m:
            fail("boundary feature %r carries no district number and sub-district "
                 "label to join the Board's roster by" % (props,))
        label = m.group("label").upper()
        if label in out:
            fail("two boundary features claim sub-district %s" % label)
        out[label] = str(number)
    if not out:
        fail("%s drew no districts" % os.path.relpath(path, REPO_ROOT))
    return out


def witnessed(record):
    """The record's own three facts, or a failure naming the one that differs."""
    bio = record.get("bio") or {}
    for field in ("name", "role", "district"):
        if (record.get(field) or "") != (bio.get(field) or ""):
            fail("the Board's index and %s disagree about %s: %r against %r — "
                 "one of the two pages moved"
                 % (record.get("profile_url"), field,
                    record.get(field), bio.get(field)))
    return bio


def main():
    if len(sys.argv) < 2:
        fail("usage: build_chicago_school_board_roster.py "
             "<raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as handle:
        raw = json.load(handle)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    districts = sub_district_map()
    roster, presidents = {}, []
    for record in raw.get("records") or []:
        bio = witnessed(record)
        name, role = record.get("name") or "", record.get("role") or ""
        label = record.get("district") or ""

        if not label:
            presidents.append((name, role, record.get("profile_url"), bio.get("email")))
            continue

        m = DISTRICT_RE.match(label)
        if not m:
            fail("%r is not a district the Board publishes in its own scheme" % label)
        key = districts.get(m.group("label").upper())
        if key is None:
            fail("the Board seats a member in %s and the shipped boundary draws no "
                 "such sub-district — a re-districting, not a roster change" % label)
        if key in roster:
            fail("two members claim %s (district %s)" % (label, key))
        # THE NAME A READER IS SHOWN. The key is the boundary's row number
        # (1..20), which nothing the Board or the ballot publishes uses — its
        # "District 4" is the PAIR 4a + 4b, not the seat this file keys as 4 —
        # so the key stays an index and every surface prints this instead.
        sub = m.group("label").lower()

        if is_vacancy_marker(name):
            # The Board's own word for an empty seat, kept as a seat rather than
            # shipped as a person of that name. IT CARRIES NO ROLE, unlike the
            # CCPSA vacancies this shape is shared with: there a role is the
            # seat's committee assignment, and here it is an OFFICE OF THE BOARD
            # that the members elect one of their own to — an empty seat cannot
            # hold the vice presidency.
            roster[key] = {"vacant": True, "subDistrict": sub}
            continue

        reason = why_not_a_name(name)
        if reason:
            fail("%s would ship %r as its member's name, which is %s"
                 % (label, name, reason))
        entry = {"name": name, "subDistrict": sub}
        if bio.get("email"):
            entry["email"] = bio["email"]
        if record.get("profile_url"):
            entry["profileUrl"] = record["profile_url"]
        # Eighteen of twenty are published as "Member", which is what the card's
        # own badge already says, so only an OFFICE rides a row.
        if role and role.lower() != "member":
            entry["role"] = role
        roster[key] = entry

    missing = sorted(set(districts.values()) - set(roster), key=int)
    if missing:
        fail("the Board's index names nobody in district(s) %s. A list that does "
             "not mention a seat is a list that is behind, never a statement that "
             "the seat is empty — check the source before anything else"
             % ", ".join(missing))
    if len(presidents) != EXPECT_PRESIDENTS:
        fail("parsed %d member(s) with no district, expected exactly %d (the "
             "president, whom the Board seats city-wide)"
             % (len(presidents), EXPECT_PRESIDENTS))

    emails = sum(1 for entry in roster.values() if entry.get("email"))
    if emails < MIN_EMAILS:
        fail("only %d/%d members carry an e-mail (floor %d)"
             % (emails, len(roster), MIN_EMAILS))

    name, role, profile, email = presidents[0]
    reason = why_not_a_name(name)
    if reason:
        fail("the board block would ship %r as the president's name, which is %s"
             % (name, reason))
    office = raw.get("office") or {}
    board = {"president": name, "role": role, "sourceUrl": SOURCE_URL}
    for key, value in (("presidentProfileUrl", profile), ("email", email),
                       ("address", office.get("address")), ("phone", office.get("phone"))):
        if value:
            board[key] = value
    if "address" not in board or "phone" not in board:
        fail("the Board's own hCard gave no office address and telephone — the "
             "footer's markup moved")
    roster["board"] = board

    out_path = os.path.join(out_dir, "school-board-members.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(roster, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    vacant = sum(1 for k, v in roster.items() if k != "board" and v.get("vacant"))
    print("chicago-school-board-roster: wrote %s — %d districts (%d named, %d "
          "vacant, %d with an e-mail) + the board block (%s, president %s)"
          % (os.path.relpath(out_path, REPO_ROOT), len(roster) - 1,
             len(roster) - 1 - vacant, vacant, emails, board["phone"], name))


if __name__ == "__main__":
    main()
