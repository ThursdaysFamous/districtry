#!/usr/bin/env python3
"""
Resolve the NYPD precinct scrape (nypd_precinct_scraper.py) into
data/app/nypd-precinct-info.json
  { "<precinct>": {"commander", "address", "phone", "source_url"} }.

Stage 2 of the pipeline (METRO_EXPANSION_PLAYBOOK §9). Keeps every precinct the
scrape saw (so the layer always has a key per precinct) but REFUSES to write if
too few commanders resolved — a WAF wave or markup change that blanks most pages
must not overwrite a good roster with an empty one.

Usage:
    python3 scripts/build_nypd_roster.py [--in PATH]
"""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "data", "app")
DEFAULT_IN = os.path.join(os.path.dirname(__file__), ".cache", "nypd_precincts_raw.json")
OUT = os.path.join(APP, "nypd-precinct-info.json")

# 78 precincts; require most commanders to have resolved before shipping.
MIN_COMMANDERS = 60
# The station address replaced the city facilities list on the card
# (2026-10-16), measured 78 of 78 that day, so a markup change that blanks it
# fails the build instead of leaving the cards with no station.
MIN_ADDRESSES = 70


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
        print("no scrape input at %s (run nypd_precinct_scraper.py first)" % in_path, file=sys.stderr)
        sys.exit(2)

    raw = json.load(open(in_path)).get("precincts", {})
    roster = {}
    commanders = addresses = 0
    for pct, rec in raw.items():
        commander = (rec.get("commander") or "").strip() or None
        if commander:
            commanders += 1
        address = rec.get("address") or None
        if address:
            addresses += 1
        roster[str(int(pct))] = {"commander": commander, "address": address,
                                 "phone": rec.get("phone") or None,
                                 "source_url": rec.get("source_url")}

    if commanders < MIN_COMMANDERS:
        print("REFUSING to write nypd-precinct-info.json: only %d commanders resolved (< %d)"
              % (commanders, MIN_COMMANDERS), file=sys.stderr)
        sys.exit(1)
    if addresses < MIN_ADDRESSES:
        print("REFUSING to write nypd-precinct-info.json: only %d station addresses resolved (< %d)"
              % (addresses, MIN_ADDRESSES), file=sys.stderr)
        sys.exit(1)

    roster = {k: roster[k] for k in sorted(roster, key=lambda x: int(x))}
    with open(OUT, "w") as f:
        json.dump(roster, f, indent=0, ensure_ascii=False)
    print("wrote data/app/nypd-precinct-info.json: %d precincts, %d commanders" % (len(roster), commanders), file=sys.stderr)
    cov = _coverage_line(roster)
    if cov:
        print("field coverage: %s" % cov, file=sys.stderr)


if __name__ == "__main__":
    main()
