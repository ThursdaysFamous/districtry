#!/usr/bin/env python3
"""
Build the Wisconsin State Senate and State Assembly rosters (district ->
current officeholder) as same-origin app-data files, so the wi-senate /
wi-assembly cards join a small roster instead of reaching a third-party host
at click time.

index.html's wi-senate / wi-assembly layers fetch data/app/wi-senate-members.json
and wi-assembly-members.json lazily on first click and join them to the
pre-built legislative geometry by district number. This script resolves the
current officeholder per district from the canonical Open States bulk people
export (data.openstates.org/people/current/wi.csv — one file for both
chambers) and writes the two rosters, shaped for the registerIlgaChamber
factory ({district -> {name, party, url, districtOffice:[lines],
capitolOffice:[lines]}}). A weekly GitHub Action
(.github/workflows/update-wi-legislature-roster.yml) reruns this and opens a
PR when a roster changes, so officeholder data gets a human look before it
ships.

Honesty: names are never guessed. A vacant district simply doesn't appear in
its roster, and the card falls back to "district number + chamber directory"
— the factory's empty-member path. Open States itself is a sourced,
machine-maintained dataset (each person row carries `sources`), never
hand-entered here.

Usage:
    python3 build_wi_legislature_roster.py [wi.csv] [output_dir]

With no arguments it downloads the source and writes to the instance's
data/app/. Pass a local wi.csv to build offline; pass an output_dir to
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


SOURCE_URL = "https://data.openstates.org/people/current/wi.csv"

# WI has 33 State Senate and 99 State Assembly districts. Floors catch a
# truncated download / schema change while tolerating transient vacancies.
CHAMBERS = {
    "upper": {"out": "wi-senate-members.json", "label": "Senate", "expected": 31},
    "lower": {"out": "wi-assembly-members.json", "label": "Assembly", "expected": 94},
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "data", "app")


def load_rows(path):
    if path:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    require_robots_once(SOURCE_URL, UA_STDLIB_DEFAULT,
                        label="wi-build-wi-legislature-roster")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def current_url(links):
    # Open States `links` packs the member's official page(s) in session
    # order, OLDEST FIRST — taking the first match shipped a senator's 2019
    # page for a year (the measured defect docs/WI_PHASE2_PLAN.md PR 6
    # records), so the LAST url is the current one. The engine scheme-checks
    # this via safeHttpUrl before it ever becomes an href, so a stray value
    # degrades to the chamber directory.
    if not links:
        return None
    found = re.findall(r"https?://[^\s,;'\"\]}]+", links)
    return found[-1] if found else None


# Put an embedded unit designator on its own comma-part so the app's
# cleanPoiAddress can strip it before geocoding the district-office pin.
# Open States packs the suite into the street segment, which Nominatim won't
# resolve; comma-separated it geocodes once cleanPoiAddress drops the unit
# part. Only touches a designator not already comma-set off; the card still
# displays the full address.
_MID_UNIT_RE = re.compile(
    r"(?<!,)\s+(?=(?:suite|ste|room|rm|floor|fl|unit|apt|apartment|bldg|building|no\.?|#)\b\.?\s*#?\s*\d)",
    re.I,
)


def normalize_address(addr):
    s = _MID_UNIT_RE.sub(", ", str(addr).strip(), count=1)
    s = re.sub(r"\s*,\s*", ", ", s)        # normalize comma spacing
    s = re.sub(r"(?:,\s*){2,}", ", ", s)   # collapse repeated commas
    return s.strip().strip(",").strip()


def office(address, voice):
    lines = []
    if address:
        lines.append(normalize_address(address))
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
        # The CSV's email column is filled 132/132 for Wisconsin and was
        # DISCARDED for the instance's first weeks (the second measured
        # defect); the legislature's own page overrides it below where both
        # exist, since that is the address the member's office publishes.
        email = (r.get("email") or "").strip()
        if email and "@" in email:
            member["email"] = email
        url = current_url(r.get("links"))
        if url:
            member["url"] = url
        dist = office(r.get("district_address"), r.get("district_voice"))
        if dist:
            member["districtOffice"] = dist
        cap = office(r.get("capitol_address"), r.get("capitol_voice"))
        if cap:
            member["capitolOffice"] = cap

        # The docs.legis enrichment (wi_legislature_scraper.py): the Madison
        # office room, phones, fax, e-mail and the CURRENT session link —
        # everything the Open States export measures 0/132 on for Wisconsin.
        # Fields merge individually; a missing enrichment leaves the Open
        # States base untouched, so a scraper outage degrades rather than
        # emptying the roster.
        enrich = offices.get(district) if offices else None
        if enrich:
            if enrich.get("url"):
                member["url"] = enrich["url"]
            if enrich.get("email"):
                member["email"] = enrich["email"]
            cap_lines = list(enrich.get("capitolOffice") or [])
            for phone in enrich.get("phones") or []:
                cap_lines.append("Phone: " + phone)
            if enrich.get("fax"):
                cap_lines.append("Fax: " + enrich["fax"])
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
        print(f"usage: {sys.argv[0]} [wi.csv] [output_dir]", file=sys.stderr)
        sys.exit(1)

    src_path = sys.argv[1] if len(sys.argv) >= 2 else None
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR
    rows = load_rows(src_path)

    # docs.legis office enrichment (wi_legislature_scraper.py's intermediate);
    # absent file = degrade to the Open States base, never fail the build.
    offices_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".cache", "wi_legislature_offices.json")
    offices_all = {}
    if os.path.exists(offices_path):
        with open(offices_path) as f:
            offices_all = json.load(f)
    chamber_offices = {"upper": offices_all.get("senate") or {},
                       "lower": offices_all.get("assembly") or {}}

    os.makedirs(out_dir, exist_ok=True)
    failed = False
    for chamber, cfg in CHAMBERS.items():
        roster = resolve(rows, chamber, chamber_offices.get(chamber))
        if len(roster) < cfg["expected"]:
            print(
                f"WARNING: resolved {len(roster)} WI {cfg['label']} districts "
                f"(expected >= {cfg['expected']}) — refusing to overwrite "
                f"{cfg['out']} with an incomplete roster",
                file=sys.stderr,
            )
            failed = True
            continue
        # The legislature's page prints each member's HOME address under
        # "Voting Address"; the scraper never reads that span, and this
        # asserts on the BUILT payload that nothing shaped like it survived
        # (every shipped capitol line is the Capitol's own room/box/phone).
        for d, m in roster.items():
            for line in m.get("capitolOffice") or []:
                low = line.lower()
                if not any(tok in low for tok in ("room", "state capitol", "po box",
                                                   "madison", "phone:", "fax:")):
                    raise SystemExit("capitol office for district %s carries a "
                                     "non-Capitol line (%r) — a home address "
                                     "cannot ship" % (d, line))
        out_path = os.path.join(out_dir, cfg["out"])
        write_json(out_path, roster)
        print(f"Wrote {out_path} ({len(roster)} districts)", file=sys.stderr)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
