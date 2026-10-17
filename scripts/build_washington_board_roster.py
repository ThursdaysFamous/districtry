#!/usr/bin/env python3
"""
Resolve scripts/washington_county_board_scraper.py's raw output into
data/app/washington-county-board-members.json, keyed by board district.

Washington seats fifteen members across three districts, five each. The county
marks no chair on this page, so none is rendered (the Woodford/Henry posture) —
the card links the board page instead of guessing.

THE COMPOSITION CROSS-CHECK — the same page this roster comes from is also the
authority for the district BOUNDARIES, which are Census townships dissolved per
its parentheticals (scripts/build_washington_board_districts.py). This builder
re-reads what the scraper saw and fails on any difference, so a redistricting
turns the weekly job red instead of leaving the derived lines a cycle out of
date. Same mechanism as De Witt; here it is simpler, because Washington's
districts are whole townships with no numbering to reconcile.

DOMAIN SANITY WARNING — the county publishes one member's address on
"washingtonco.illnois.gov", a misspelling of the domain its five siblings use.
It ships AS PUBLISHED: correcting an officeholder's contact details is not this
pipeline's call, even when the correction looks obvious. The builder WARNS
instead, so the typo is in front of a human on every weekly PR.

EVERY NUMBER A MEMBER PRINTS SHIPS: the first in `phone`, any others in
`phonesExtra`, each led by the page's own "(Cell)" label where it gives one.
Until Adam's ruling of 2026-10-17 ("if the official government source uses
personal phone numbers, we publish those") only the first number shipped. Every
number is checked for its shape (scraper_common.person_phone_problem) and the
error names the seat, never the number.

Usage:
    python3 build_washington_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_washington_board_districts import DISTRICTS as BOUNDARY_COMPOSITION  # noqa: E402
from scraper_common import make_fail, person_phone_problem  # noqa: E402  (shared machinery — do not fork)
import undeliverable  # noqa: E402  (the fleet's withhold list)

SOURCE_URL = "https://washingtonco.illinois.gov/county-board/"

EXPECT_DISTRICTS = ("1", "2", "3")
MEMBERS_PER_DISTRICT = 5
MIN_PHONES = 12
MIN_EMAILS = 12
# Members printing a second number of their own: measured 1 of 15 on
# 2026-10-17. Two thirds of 1 rounds to 1, so the build fails if the second
# number stops being read; if that member stops printing one, lower this floor.
MIN_SECOND_NUMBERS = 1

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


fail = make_fail("washington-board-roster")


def edit_distance(a, b):
    """Levenshtein, iterative — small strings, no dependency worth adding."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def township_set(text):
    """"Ashley, Beaucoup, Du Bois and Richview" -> {ASHLEY, BEAUCOUP, ...}"""
    out = set()
    for chunk in re.split(r"\s*,\s*|\s+and\s+", (text or "").strip(), flags=re.I):
        chunk = re.sub(r"\s*Townships?\.?$", "", chunk.strip(), flags=re.I).strip()
        if chunk:
            out.add(" ".join(chunk.upper().split()))
    return out


def main():
    if len(sys.argv) < 2:
        fail("usage: build_washington_board_roster.py <raw-scraper-output.json> [output_dir]")
    with open(sys.argv[1], encoding="utf-8") as f:
        records = json.load(f)["records"]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR

    roster, seen_composition = {}, {}
    for rec in records:
        if not rec.get("name") or not rec.get("district"):
            continue
        district = str(rec["district"])
        member = {"name": rec["name"]}
        for key in ("phone", "phonesExtra", "email"):
            if not rec.get(key):
                continue
            value = rec[key]
            if key == "email":
                value, _why = undeliverable.withhold(
                    value, "%s, district %s" % (member["name"], district))
                if not value:
                    continue
            member[key] = value
        roster.setdefault(district, {"members": [], "sourceUrl": SOURCE_URL})
        roster[district]["members"].append(member)
        if rec.get("composition"):
            seen_composition.setdefault(district, rec["composition"])

    if sorted(roster) != sorted(EXPECT_DISTRICTS):
        fail("parsed districts %s, expected exactly %s" % (sorted(roster), list(EXPECT_DISTRICTS)))
    for d, entry in roster.items():
        if len(entry["members"]) != MEMBERS_PER_DISTRICT:
            fail("district %s has %d members, the county seats exactly %d per district"
                 % (d, len(entry["members"]), MEMBERS_PER_DISTRICT))
        entry["members"].sort(key=lambda m: m["name"].split()[-1])

    # --- composition cross-check against the shipped boundary
    for d in EXPECT_DISTRICTS:
        published = township_set(seen_composition.get(d))
        if not published:
            fail("district %s published no township composition — the page's shape "
                 "changed, and the shipped boundary can no longer be cross-checked" % d)
        expected = {" ".join(n.upper().split()) for n in BOUNDARY_COMPOSITION[d]}
        if published != expected:
            gained = sorted(published - expected)
            lost = sorted(expected - published)
            bits = []
            if gained:
                bits.append("now includes %s" % ", ".join(gained))
            if lost:
                bits.append("no longer includes %s" % ", ".join(lost))
            fail("district %s composition CHANGED — the county %s. Re-read the county "
                 "board page and rebuild data/app/washington-county-board-districts.json "
                 "before shipping this roster." % (d, "; ".join(bits)))

    members = [m for e in roster.values() for m in e["members"]]
    phones = sum(1 for m in members if m.get("phone"))
    seconds = sum(1 for m in members if m.get("phonesExtra"))
    emails = sum(1 for m in members if m.get("email"))
    if phones < MIN_PHONES:
        fail("only %d phones resolved (expected >= %d)" % (phones, MIN_PHONES))
    if seconds < MIN_SECOND_NUMBERS:
        fail("only %d members carry a second number (expected >= %d) — the "
             "page's phone lines may have changed" % (seconds, MIN_SECOND_NUMBERS))
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
                    fail("Washington County District %s, seat %d of %d: %s %s"
                         % (d, seat, len(roster[d]["members"]), field, problem))

    # --- domain sanity: report, never rewrite (see the module header)
    #
    # Members legitimately publish personal addresses (gmail, yahoo, att.net) —
    # those are what the county prints and are not typos. The only case worth
    # flagging is a near-miss of the county's OWN .gov domain, which is why the
    # comparison is restricted to .gov and uses real edit distance. A looser
    # rule flagged hotmail.com as a misspelling of gmail.com.
    domains = collections.Counter(m["email"].split("@")[-1] for m in members if m.get("email"))
    official = [d for d, n in domains.items() if n >= 3 and d.endswith(".gov")]
    for m in members:
        if not m.get("email"):
            continue
        dom = m["email"].split("@")[-1]
        if domains[dom] != 1:
            continue
        for good in official:
            if dom != good and edit_distance(dom, good) <= 2:
                print("washington-board-roster: WARN — %s's published e-mail domain "
                      "%r looks like a misspelling of the county's own %r. Shipping it "
                      "AS PUBLISHED; correcting an officeholder's contact details is "
                      "the county's call, not this pipeline's."
                      % (m["name"], dom, good), file=sys.stderr)
                break

    out_path = os.path.join(out_dir, "washington-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("washington-board-roster: %d districts, %d members (%d phones, %d with a "
          "second number, %d e-mails); composition matches the shipped boundary in "
          "all 3 districts -> %s"
          % (len(roster), len(members), phones, seconds, emails, out_path))


if __name__ == "__main__":
    main()
