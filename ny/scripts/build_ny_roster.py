#!/usr/bin/env python3
"""
Resolve the raw NY legislature scrape (ny_legislature_scraper.py) into the two
app-data roster files:
    data/app/ny-senate-members.json    { "<district>": {"name", "party"} }
    data/app/ny-assembly-members.json  { "<district>": {"name", "party"} }

Stage 2 of the two-stage pipeline (METRO_EXPANSION_PLAYBOOK §9). Dedupes the
session-member list to one current officeholder per district (incumbent
preferred), and REFUSES to overwrite a roster below its count floor so a partial
scrape can't ship. Party is null (the source doesn't publish it — never guessed).

Usage:
    python3 scripts/build_ny_roster.py [--in PATH]
"""

import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "data", "app")
DEFAULT_IN = os.path.join(os.path.dirname(__file__), ".cache", "ny_legislature_raw.json")

# floors: 63 senate / 150 assembly districts; allow a little vacancy slack.
FLOORS = {"SENATE": 60, "ASSEMBLY": 145}
OUT = {"SENATE": "ny-senate-members.json", "ASSEMBLY": "ny-assembly-members.json"}


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


def resolve(records, chamber):
    by_district = {}
    for r in records:
        if r.get("chamber") != chamber:
            continue
        d = r.get("district")
        name = (r.get("name") or "").strip()
        if d is None or not name:
            continue
        key = str(int(d))
        prev = by_district.get(key)
        # prefer an incumbent; otherwise keep the first seen
        if prev is None or (r.get("incumbent") and not prev.get("_incumbent")):
            entry = {"name": name, "party": r.get("party"), "_incumbent": bool(r.get("incumbent"))}
            if r.get("districtOffice"):
                entry["districtOffice"] = r["districtOffice"]
            if r.get("capitolOffice"):
                entry["capitolOffice"] = r["capitolOffice"]
            if r.get("url"):
                entry["url"] = r["url"]
            by_district[key] = entry
    for v in by_district.values():
        v.pop("_incumbent", None)
    return by_district


ENRICHED = ("party", "districtOffice", "capitolOffice", "url")


def carry_forward(roster, previous, today):
    """Keep a member's last-read party, offices and page when this week's
    Open States read returned nothing for their district.

    Open States is the only source of these four fields, and it is read in
    pages. On 2026-10-12 it returned nothing for Senate District 12 while the
    Open Legislation list still named Michael Gianaris there, so his party and
    both offices vanished from the card with nothing about him having changed.
    A district that comes back with NONE of the four fields while the same
    person is named is a failed read, not news, so the last-good values are
    kept and stamped `preservedSince` (Adam's ruling of 2026-09-19: preserve
    what was already fetched). A district that comes back with any of the four
    is taken as read, and a different name is never given someone else's
    offices. Returns the districts carried forward.
    """
    carried = []
    for key, entry in roster.items():
        old = previous.get(key)
        if not isinstance(old, dict) or old.get("name") != entry.get("name"):
            continue
        if any(entry.get(f) for f in ENRICHED):
            continue
        kept = {f: old[f] for f in ENRICHED if old.get(f)}
        if not kept:
            continue
        entry.update(kept)
        entry["preservedSince"] = old.get("preservedSince") or today
        carried.append(key)
    return carried


def main():
    in_path = DEFAULT_IN
    argv = sys.argv[1:]
    if "--in" in argv:
        in_path = argv[argv.index("--in") + 1]
    if not os.path.exists(in_path):
        print("no scrape input at %s (run ny_legislature_scraper.py first)" % in_path, file=sys.stderr)
        sys.exit(2)

    raw = json.load(open(in_path))
    records = raw.get("members", [])

    for chamber, fname in OUT.items():
        roster = resolve(records, chamber)
        floor = FLOORS[chamber]
        if len(roster) < floor:
            print("REFUSING to write %s: %d districts < floor %d" % (fname, len(roster), floor), file=sys.stderr)
            sys.exit(1)
        roster = {k: roster[k] for k in sorted(roster, key=lambda x: int(x))}
        path = os.path.join(APP, fname)
        previous = {}
        if os.path.exists(path):
            with open(path) as f:
                previous = json.load(f)
        today = time.strftime("%Y-%m-%d", time.gmtime())
        for key in carry_forward(roster, previous, today):
            print("%s district %s: Open States returned nothing for %s; kept the "
                  "party and offices last read (preservedSince %s)"
                  % (chamber.lower(), key, roster[key]["name"],
                     roster[key]["preservedSince"]), file=sys.stderr)
        with open(path, "w") as f:
            json.dump(roster, f, indent=0, ensure_ascii=False)
        print("wrote data/app/%s: %d districts" % (fname, len(roster)), file=sys.stderr)
    cov = _coverage_line(roster)
    if cov:
        print("field coverage: %s" % cov, file=sys.stderr)


if __name__ == "__main__":
    main()
