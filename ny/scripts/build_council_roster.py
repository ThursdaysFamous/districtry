#!/usr/bin/env python3
"""
Resolve the council scrape (council_scraper.py) into
data/app/council-members.json  { "<district>": {"name"} }.

Stage 2 of the pipeline (METRO_EXPANSION_PLAYBOOK §9). REFUSES to write below the
count floor so a partial scrape can't overwrite a good roster. Party is not taken
(council.nyc.gov doesn't label it in the district cards) — never guessed.

Usage:
    python3 scripts/build_council_roster.py [--in PATH]
"""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "data", "app")
DEFAULT_IN = os.path.join(os.path.dirname(__file__), ".cache", "council_raw.json")
OUT = os.path.join(APP, "council-members.json")
MIN_MEMBERS = 48  # 51 seats; tolerate a few vacancies


def _coverage_line(roster):
    """Per-field coverage one-liner (CHI fleet-status convention): makes
    parser drift visible at a glance in the weekly run logs. Honest nulls
    stay honest — this reports them, it never fills them."""
    rows = []
    for v in roster.values():
        if isinstance(v, dict):
            rows.append(v)
        elif isinstance(v, list):
            rows.extend(x for x in v if isinstance(x, dict))
    if not rows:
        return None
    fields = sorted({k for r in rows for k in r})
    return "  ".join("%s=%d/%d" % (f, sum(1 for r in rows if r.get(f)), len(rows)) for f in fields)


def main():
    argv = sys.argv[1:]
    in_path = argv[argv.index("--in") + 1] if "--in" in argv else DEFAULT_IN
    if not os.path.exists(in_path):
        print("no scrape input at %s (run council_scraper.py first)" % in_path, file=sys.stderr)
        sys.exit(2)

    raw = json.load(open(in_path)).get("members", {})
    roster = {}
    for district, rec in raw.items():
        name = (rec.get("name") or "").strip()
        if name:
            entry = {"name": name}
            # The leadership post the scraper split off the name (Speaker,
            # Majority Leader and the rest). `office` on these records is the
            # district office ADDRESS, so the post has a key of its own rather
            # than overwriting one.
            role = (rec.get("role") or "").strip()
            if role:
                entry["role"] = role
            office = (rec.get("office") or "").strip()
            if office:
                entry["office"] = office
            roster[str(int(district))] = entry

    if len(roster) < MIN_MEMBERS:
        print("REFUSING to write council-members.json: %d members < floor %d" % (len(roster), MIN_MEMBERS), file=sys.stderr)
        sys.exit(1)

    roster = {k: roster[k] for k in sorted(roster, key=lambda x: int(x))}
    with open(OUT, "w") as f:
        json.dump(roster, f, indent=0, ensure_ascii=False)
    print("wrote data/app/council-members.json: %d members" % len(roster), file=sys.stderr)
    cov = _coverage_line(roster)
    if cov:
        print("field coverage: %s" % cov, file=sys.stderr)


if __name__ == "__main__":
    main()
