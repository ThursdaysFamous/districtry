#!/usr/bin/env python3
"""
Build data/app/congress-roster.json — the current NY U.S. House delegation —
from the public @unitedstates/congress-legislators dataset (CC0). No scrape and
no key; the whole state is kept because the TIGERweb congressional geometry the
app joins on is whole-state too (METRO_EXPANSION_PLAYBOOK §9; re-parameterized
from Chicago's IL builder — "IL"->"NY", 17->26 reps).

Output shape: { "<district>": {"name", "party", "url", "capitolOffice",
"districtOffice"} }, keyed by district number (offices present when the source
carries them). REFUSES to write below the count floor.

Usage:
    python3 scripts/build_congress_roster.py
"""

import json
import re
import os
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED -- validate_workflow_deps)
    UA_STDLIB_DEFAULT,
    require_robots_once,
)

SRC = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
OFFICES = "https://unitedstates.github.io/congress-legislators/legislators-district-offices.json"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "app", "congress-roster.json")
STATE = "NY"
MIN_REPS = 24  # NY has 26 U.S. House seats; tolerate a couple of vacancies


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


def district_offices_by_bioguide():
    """bioguide -> [address-line, "City, NY zip"] for the member's first NY office."""
    try:
        # The policy is read with the client that crawls: this call sets no
        # User-Agent, so urllib's own string is what the host sees and is
        # what the robots groups are matched against.
        require_robots_once(OFFICES, UA_STDLIB_DEFAULT,
                            label="ny-build-congress-roster")
        data = json.load(urllib.request.urlopen(OFFICES, timeout=90))
    except Exception:  # noqa: BLE001 — offices are an enhancement, never fatal
        return {}
    out = {}
    for p in data:
        bio = (p.get("id") or {}).get("bioguide")
        if not bio:
            continue
        for o in p.get("offices", []):
            if o.get("state") != STATE or not o.get("address"):
                continue
            suite = str(o.get("suite") or "").strip()
            # the suite field usually already reads "Suite 291" / "Rm 3"; only add
            # a designator when it's a bare number/letter.
            if suite and not re.match(r"(?i)(suite|ste|rm|room|fl|floor|#|unit|apt)", suite):
                suite = "Suite " + suite
            line1 = o["address"] + ((" " + suite) if suite else "")
            line2 = ("%s, %s %s" % (o.get("city", ""), o.get("state", ""), o.get("zip", ""))).strip()
            lines = [line1] + ([line2] if line2.strip(", ") else [])
            if o.get("phone"):
                lines.append("Phone: " + o["phone"])
            out[bio] = lines
            break
    return out


def capitol_office(term):
    """The Washington, D.C. office the source carries per term — address + phone,
    as lines the factory renders under capitolLabel; empties dropped."""
    lines = []
    if term.get("address"):
        lines.append(str(term["address"]))
    if term.get("phone"):
        lines.append("Phone: " + str(term["phone"]))
    return lines


def main():
    require_robots_once(SRC, UA_STDLIB_DEFAULT,
                        label="ny-build-congress-roster")
    data = json.load(urllib.request.urlopen(SRC, timeout=90))
    offices = district_offices_by_bioguide()
    roster = {}
    for p in data:
        terms = p.get("terms") or []
        if not terms:
            continue
        term = terms[-1]
        if term.get("type") != "rep" or term.get("state") != STATE:
            continue
        name = p["name"].get("official_full") or (p["name"].get("first", "") + " " + p["name"].get("last", "")).strip()
        entry = {
            "name": name,
            "party": term.get("party"),
            "url": term.get("url") or "https://www.house.gov/representatives",
        }
        cap = capitol_office(term)
        if cap:
            entry["capitolOffice"] = cap
        office = offices.get((p.get("id") or {}).get("bioguide"))
        if office:
            entry["districtOffice"] = office
        roster[str(term.get("district"))] = entry

    if len(roster) < MIN_REPS:
        print("REFUSING to write congress-roster.json: %d reps < floor %d" % (len(roster), MIN_REPS), file=sys.stderr)
        sys.exit(1)

    roster = {k: roster[k] for k in sorted(roster, key=lambda x: int(x))}
    with open(OUT, "w") as f:
        json.dump(roster, f, indent=0, ensure_ascii=False)
    print("wrote data/app/congress-roster.json: %d NY U.S. House reps" % len(roster), file=sys.stderr)
    cov = _coverage_line(roster)
    if cov:
        print("field coverage: %s" % cov, file=sys.stderr)


if __name__ == "__main__":
    main()
