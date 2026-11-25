#!/usr/bin/env python3
"""
Resolve scripts/boone_county_board_scraper.py's raw output into
data/app/boone-county-board-members.json, keyed by board district — three
four-member districts, every seat carrying a phone, an e-mail and the
"Term Expires" year the page publishes (Boone's terms are staggered, so the
year answers "which of these do I vote on next?" per seat). Role tags ride
their member rows exactly as the page states them — currently a single
Vice-Chairman; no Chairman is named anywhere on the page, so none is
rendered.

index.html's consolidated county-board layer fetches this file lazily on
first click (same-origin) and joins it by district number to the county
GIS's three pre-dissolved district layers, merged at load time.

Usage:
    python3 build_boone_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import sys
from scraper_common import make_fail  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = "https://www.boonecountyil.gov/government/county_board_members.php"

EXPECT_DISTRICTS = ("1", "2", "3")
EXPECT_MEMBERS_PER_DISTRICT = 4
MIN_PHONES = 10
MIN_EMAILS = 10
MIN_TERMS = 10
ALLOWED_ROLES = {"Chairman", "Vice-Chairman"}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("boone-board-roster")


def main():
    if len(sys.argv) < 2:
        fail("usage: build_boone_board_roster.py <raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as f:
        records = json.load(f)["records"]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    roster = {}
    roles = []
    for rec in records:
        if not rec.get("name") or rec.get("district") is None:
            continue
        d = str(rec["district"])
        roster.setdefault(d, {"members": [], "sourceUrl": SOURCE_URL})
        m = {"name": rec["name"]}
        if rec.get("role"):
            m["role"] = rec["role"]
            roles.append((rec["role"], rec["name"]))
        if rec.get("term_year"):
            m["termExpires"] = rec["term_year"]
        for k in ("phone", "email"):
            if rec.get(k):
                m[k] = rec[k]
        roster[d]["members"].append(m)

    if sorted(roster) != sorted(EXPECT_DISTRICTS):
        fail("parsed districts %s, expected exactly %s" % (sorted(roster), list(EXPECT_DISTRICTS)))
    for d, entry in roster.items():
        # One seat short is how the page shows a member who left (District 2,
        # 2026-11: Ryan Curry's row gone, no vacancy printed); the card says
        # "1 of 4 seats not listed" from `seats`. Two short is a parse break.
        n = len(entry["members"])
        if not EXPECT_MEMBERS_PER_DISTRICT - 1 <= n <= EXPECT_MEMBERS_PER_DISTRICT:
            fail("district %s has %d members, the county seats exactly %d"
                 % (d, n, EXPECT_MEMBERS_PER_DISTRICT))
        entry["seats"] = EXPECT_MEMBERS_PER_DISTRICT
        entry["members"].sort(key=lambda m: m["name"].split()[-1])
    # Roles pass through verbatim, but a value outside the body's two titles
    # or the same title on two rows means the markup changed — a human look.
    for role, _ in roles:
        if role not in ALLOWED_ROLES:
            fail("unexpected role tag %r — the page's role wording changed" % role)
    if len(set(r for r, _ in roles)) != len(roles):
        fail("a role tag appears on more than one member: %s" % roles)
    phones = sum(1 for v in roster.values() for m in v["members"] if m.get("phone"))
    emails = sum(1 for v in roster.values() for m in v["members"] if m.get("email"))
    terms = sum(1 for v in roster.values() for m in v["members"] if m.get("termExpires"))
    if phones < MIN_PHONES:
        fail("only %d members carry a phone (floor %d)" % (phones, MIN_PHONES))
    if emails < MIN_EMAILS:
        fail("only %d members carry an e-mail (floor %d)" % (emails, MIN_EMAILS))
    if terms < MIN_TERMS:
        fail("only %d/12 members carry a term-expiry year (floor %d)" % (terms, MIN_TERMS))

    out_path = os.path.join(out_dir, "boone-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("boone-board-roster: wrote %s — 3 districts, %d of 12 seats named "
          "(%d phones, %d e-mails, %d terms%s)"
          % (os.path.relpath(out_path, REPO_ROOT),
             sum(len(v["members"]) for v in roster.values()), phones, emails, terms,
             "; " + ", ".join("%s %s" % (r, n) for r, n in sorted(roles)) if roles else ""))


if __name__ == "__main__":
    main()
