#!/usr/bin/env python3
"""
Resolve scripts/jodaviess_county_board_scraper.py's raw output into
data/app/jo-daviess-county-board-members.json, keyed by Jo Daviess County
Board district ("1".."17" — seventeen SINGLE-member districts, the widest
single-member board in the fleet after Peoria's 18).

index.html's consolidated county-board layer fetches this file lazily on first
click (same-origin) and joins it by district number to
data/app/jo-daviess-county-board-districts.json — the county's OWN shapefile,
purchased under GIS data licence #008382 and displayed with the county's
written permission (build_jodaviess_board_districts.py has the whole story).
Both halves come from the county itself: no derivation, no tracing, no guess.

Shape mirrors the other rosters — {district: {members: [...], sourceUrl}} —
with the Livingston/Lee vacancy posture: a seat the county prints as VACANT
ships as `vacancies: 1` on its district entry, COUNTED, NEVER NAMED, because
dropping the row would misstate the board's size and naming it would invent an
officeholder. The count guard therefore counts SEATS (named + vacant), which
must equal exactly 17 with districts 1..17 each appearing exactly once — the
same rule that keeps a parse regression distinguishable from a resignation,
and, because the district set is asserted against the boundary module's
EXPECTED_DISTRICTS, the weekly run also fails the day the county's page stops
describing seventeen districts (the earliest visible sign of a
reapportionment; the purchased boundary would then need re-licensing —
see build_jodaviess_board_districts.py).

FLOORS, set at what the page actually publishes (2026-08-17): every named
member carries a party letter (16/16 — a member without one is a parse break,
so the floor is exact); 15+ carry a term; e-mail and phone floors sit two
under the published 16/16 so a single member dropping a listing reads as the
county's change rather than a red week, while a mass loss (the Brown
Cloudflare failure) still trips both this and check_roster_retention.py.

TERM STRINGS ARE NORMALISED IN FORMAT ONLY: the county prints "Term: 2024 to
2028" on most rows and "Term 2022-2026" on one; both ship as "YYYY to YYYY".
The years are never touched. Roles are normalised to the fleet's labels
("Chair" -> "Board Chair", "Vice-Chair" -> "Vice Chair") so one reader renders
every county's board the same way.

Usage:
    python3 build_jodaviess_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Constants only — the boundary module keeps its heavy imports function-local
# (the De Witt seam), so this costs a constant to import.
from build_jodaviess_board_districts import EXPECTED_DISTRICTS  # noqa: E402

SOURCE_URL = "https://www.jodaviesscountyil.gov/1199/County-Board"

# WHERE THE BOARD MEETS, not an office — and the card's label says so, because
# the county's words are "County Board room, Third Floor / Jo Daviess County
# Courthouse in Galena, 330 N. Bench St." A meeting room is not an office and
# is not published as one here. This county is exactly why that care is owed:
# its per-member directory pages DO print home addresses, which the scraper has
# never parsed (the Madison/Peoria rule, recorded in validate_index.py), so the
# courthouse is the only address about this board that is anybody's business.
BOARD = {
    "address": ("Jo Daviess County Courthouse, board room (third floor), "
                "330 N. Bench St., Galena, IL 61036"),
    "sourceUrl": SOURCE_URL,
}

MIN_TERMS = 15
MIN_EMAILS = 14
MIN_PHONES = 14

ROLE_ALIASES = {
    "chair": "Board Chair",
    "chairman": "Board Chair",
    "vice-chair": "Vice Chair",
    "vice chair": "Vice Chair",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


def member_obj(rec):
    member = {"name": rec["name"]}
    if rec.get("party"):
        member["party"] = rec["party"]
    role = (rec.get("role") or "").strip()
    if role:
        member["role"] = ROLE_ALIASES.get(role.lower(), role)
    for key in ("term", "phone", "email", "url"):
        if rec.get(key):
            member[key] = rec[key]
    return member


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    records = payload.get("records") or []
    vacant = payload.get("vacancies") or []

    roster = {}
    with_party = 0
    for rec in records:
        district = str(rec.get("district") or "").strip()
        name = (rec.get("name") or "").strip()
        party = (rec.get("party") or "").strip()
        if not district or not name:
            continue
        slot = roster.setdefault(district,
                                 {"members": [], "sourceUrl": SOURCE_URL})
        slot["members"].append(member_obj(rec))
        if party:
            with_party += 1
    # One member printed without a letter is the county's choice (2026-11-21);
    # most of the board without one is a parse break.
    if records and with_party < len(records) - 2:
        print("build-jodaviess-board: FAIL — only %d of %d members carry a party "
              "letter; the county prints one for nearly all, so this is a parse "
              "break" % (with_party, len(records)), file=sys.stderr)
        sys.exit(1)
    for v in vacant:
        district = str(v.get("district") or "").strip()
        if not district:
            continue
        slot = roster.setdefault(district,
                                 {"members": [], "sourceUrl": SOURCE_URL})
        slot["vacancies"] = slot.get("vacancies", 0) + 1

    members = sum(len(v["members"]) for v in roster.values())
    vacancies = sum(v.get("vacancies", 0) for v in roster.values())
    seats = members + vacancies
    terms = sum(1 for v in roster.values() for m in v["members"] if m.get("term"))
    emails = sum(1 for v in roster.values() for m in v["members"] if m.get("email"))
    phones = sum(1 for v in roster.values() for m in v["members"] if m.get("phone"))
    chairs = [m for v in roster.values() for m in v["members"]
              if m.get("role") == "Board Chair"]
    vices = [m for v in roster.values() for m in v["members"]
             if m.get("role") == "Vice Chair"]
    names = [m["name"] for v in roster.values() for m in v["members"]]

    problems = []
    expected_districts = {str(n) for n in range(1, EXPECTED_DISTRICTS + 1)}
    if set(roster) != expected_districts:
        problems.append("districts are %s, expected exactly 1..%d — if the "
                        "county's page really changed its district count, "
                        "that is a REAPPORTIONMENT and the purchased boundary "
                        "needs re-licensing before anything ships"
                        % (sorted(roster, key=lambda d: int(d)),
                           EXPECTED_DISTRICTS))
    if seats != EXPECTED_DISTRICTS:
        problems.append("%d seats (named %d + vacant %d), the board has "
                        "exactly %d" % (seats, members, vacancies,
                                        EXPECTED_DISTRICTS))
    lopsided = {d: len(v["members"]) + v.get("vacancies", 0)
                for d, v in roster.items()
                if len(v["members"]) + v.get("vacancies", 0) != 1}
    if lopsided:
        problems.append("districts not seating exactly 1: %s" % lopsided)
    if terms < MIN_TERMS:
        problems.append("%d terms (< %d)" % (terms, MIN_TERMS))
    if emails < MIN_EMAILS:
        problems.append("%d e-mails (< %d)" % (emails, MIN_EMAILS))
    if phones < MIN_PHONES:
        problems.append("%d phones (< %d)" % (phones, MIN_PHONES))
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        problems.append("duplicate member names (%s)" % ", ".join(dupes))
    if len(chairs) > 1:
        problems.append("%d members marked Board Chair" % len(chairs))
    if len(vices) > 1:
        problems.append("%d members marked Vice Chair" % len(vices))
    if problems:
        print("build-jodaviess-board: FAIL — refusing to overwrite a good "
              "file with a partial scrape: %s" % "; ".join(problems),
              file=sys.stderr)
        sys.exit(1)

    # District count is taken BEFORE the board block joins the mapping, so the
    # log line keeps reporting districts rather than districts-plus-one; every
    # guard above likewise reads roster's values as districts.
    district_count = len(roster)
    roster["board"] = dict(BOARD)

    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    out_path = os.path.join(out_dir, "jo-daviess-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, sort_keys=True)
    print("build-jodaviess-board: wrote %s — %d districts, %d members + %d "
          "vacant seat(s), %d terms, %d phones, %d e-mails, chair %s"
          % (out_path, district_count, members, vacancies, terms, phones, emails,
             chairs[0]["name"] if chairs else "unresolved"))


if __name__ == "__main__":
    main()
