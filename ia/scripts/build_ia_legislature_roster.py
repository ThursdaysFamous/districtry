#!/usr/bin/env python3
"""
Build the Iowa Senate and Iowa House rosters (district -> current
officeholder) as same-origin app-data files, so the ia-senate / ia-house
cards join a small roster instead of reaching a third-party host at click
time.

index.html's ia-senate / ia-house layers fetch data/app/ia-senate-members.json
and ia-house-members.json lazily on first click and join them to the
pre-built legislative geometry by district number. This script resolves the
current officeholder per district from the canonical Open States bulk people
export (data.openstates.org/people/current/ia.csv — one file for both
chambers) and writes the two rosters, shaped for the registerIlgaChamber
factory ({district -> {name, party, url, email?, capitolOffice:[lines]}}).
A weekly GitHub Action (.github/workflows/update-ia-legislature-roster.yml)
reruns this and opens a PR when a roster changes, so officeholder data gets
a human look before it ships.

Honesty: names are never guessed. A vacant district simply doesn't appear
in its roster, and the card falls back to "district number + chamber
directory" — the factory's empty-member path. Open States itself is a
sourced, machine-maintained dataset (each person row carries `sources`),
never hand-entered here.

UNLIKE WISCONSIN'S SAME-SHAPED BUILDER, Iowa's enrichment
(ia_legislature_scraper.py) carries no districtOffice at all — the state's
own site publishes only a Capitol phone/e-mail and, for some members, the
Capitol's own business address (never a personal one; the builder asserts
this on the built payload below).

Usage:
    python3 build_ia_legislature_roster.py [ia.csv] [output_dir]

With no arguments it downloads the source and writes to the instance's
data/app/. Pass a local ia.csv to build offline; pass an output_dir to
redirect the write.
"""

import csv
import io
import json
import os
import re
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)


SOURCE_URL = "https://data.openstates.org/people/current/ia.csv"

# The one Capitol street/city/state the enrichment scraper is allowed to
# have found — asserted below so a future change to a personal address
# fails loudly rather than shipping quietly. The ZIP is deliberately not
# part of the match: the state's own pages publish two variants for the
# same building (50319 and 50311, measured 2026-08-27 across every member
# carrying the field), so the check is prefix-only rather than exact.
CAPITOL_ADDRESS_PREFIX = "1007 E Grand Ave, Des Moines, IA"

# Iowa has 50 Senate and 100 House districts. Floors catch a truncated
# download / schema change while tolerating transient vacancies.
CHAMBERS = {
    "upper": {"out": "ia-senate-members.json", "label": "Senate", "expected": 45},
    "lower": {"out": "ia-house-members.json", "label": "House", "expected": 93},
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "data", "app")


def load_rows(path):
    if path:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    require_robots_once(SOURCE_URL, UA_STDLIB_DEFAULT,
                        label="ia-build-ia-legislature-roster")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def current_url(links):
    # Open States `links` packs the member's official page(s), oldest first
    # in some rows — the fleet's WI precedent (docs/WI_PHASE2_PLAN.md PR 6)
    # found the FIRST url can be a stale prior-session page, so the LAST url
    # is taken as current. The engine scheme-checks this via safeHttpUrl
    # before it ever becomes an href, so a stray value degrades to the
    # chamber directory rather than rendering a broken link.
    if not links:
        return None
    found = re.findall(r"https?://[^\s,;'\"\]}]+", links)
    return found[-1] if found else None


def office(address, voice):
    lines = []
    if address:
        lines.append(str(address).strip())
    if voice:
        lines.append("Phone: " + str(voice).strip())
    return lines


def resolve(rows, chamber, offices):
    roster = {}
    for r in rows:
        if (r.get("current_chamber") or "").strip() != chamber:
            continue
        district = (r.get("current_district") or "").strip()
        name = (r.get("name") or "").strip()
        if not district or not name:
            continue
        member = {"name": name, "party": (r.get("current_party") or "").strip() or None}
        email = (r.get("email") or "").strip()
        if email and "@" in email:
            member["email"] = email
        url = current_url(r.get("links"))
        if url:
            member["url"] = url
        cap = office(r.get("capitol_address"), r.get("capitol_voice"))
        if cap:
            member["capitolOffice"] = cap

        # The legis.iowa.gov enrichment (ia_legislature_scraper.py): the
        # Capitol phone and legislative e-mail — everything the Open States
        # export measures empty for Iowa. Fields merge individually; a
        # missing enrichment leaves the Open States base untouched, so a
        # scraper outage degrades rather than emptying the roster.
        enrich = offices.get(district) if offices else None
        if enrich:
            if enrich.get("email"):
                member["email"] = enrich["email"]
            cap_lines = []
            if enrich.get("address"):
                cap_lines.append(enrich["address"])
            for phone in enrich.get("phones") or []:
                cap_lines.append("Phone: " + phone)
            if cap_lines:
                member["capitolOffice"] = cap_lines
        roster[district] = member
    return roster


def ordered(roster):
    def key(d):
        try:
            return (0, int(d))
        except ValueError:
            return (1, d)
    return {d: roster[d] for d in sorted(roster, key=key)}


def write_json(path, roster):
    with open(path, "w") as f:
        json.dump(ordered(roster), f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    if len(sys.argv) > 3:
        print(f"usage: {sys.argv[0]} [ia.csv] [output_dir]", file=sys.stderr)
        sys.exit(1)

    src_path = sys.argv[1] if len(sys.argv) >= 2 else None
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR
    rows = load_rows(src_path)

    # legis.iowa.gov office enrichment (ia_legislature_scraper.py's
    # intermediate); absent file = degrade to the Open States base, never
    # fail the build.
    offices_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".cache", "ia_legislature_offices.json")
    offices_all = {}
    if os.path.exists(offices_path):
        with open(offices_path) as f:
            offices_all = json.load(f)
    chamber_offices = {"upper": offices_all.get("upper") or {},
                       "lower": offices_all.get("lower") or {}}

    os.makedirs(out_dir, exist_ok=True)
    failed = False
    for chamber, cfg in CHAMBERS.items():
        roster = resolve(rows, chamber, chamber_offices.get(chamber))
        if len(roster) < cfg["expected"]:
            print(
                f"WARNING: resolved {len(roster)} Iowa {cfg['label']} districts "
                f"(expected >= {cfg['expected']}) — refusing to overwrite "
                f"{cfg['out']} with an incomplete roster",
                file=sys.stderr,
            )
            failed = True
            continue
        # Iowa's site publishes no district-office address, only the
        # Capitol's own — this asserts on the BUILT payload that any address
        # line is exactly that Capitol address, never a personal one that a
        # future page reshape could otherwise ship silently.
        for d, m in roster.items():
            for line in m.get("capitolOffice") or []:
                if line.startswith("Phone:"):
                    continue
                if not line.startswith(CAPITOL_ADDRESS_PREFIX):
                    raise SystemExit(
                        "capitol office for district %s carries an address "
                        "line (%r) that is not the known Capitol address — "
                        "refusing to ship a possibly personal address"
                        % (d, line)
                    )
        out_path = os.path.join(out_dir, cfg["out"])
        write_json(out_path, roster)
        print(f"Wrote {out_path} ({len(roster)} districts)", file=sys.stderr)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
