#!/usr/bin/env python3
"""
Build the CA State Senate and State Assembly rosters (district -> current
officeholder) as same-origin app-data files, so the ca-senate / ca-assembly
cards join a small roster instead of reaching a third-party host at click time.

index.html's ca-senate / ca-assembly layers fetch data/app/ca-senate-members.json
and ca-assembly-members.json lazily on first click and join them to the pre-built
CA legislative geometry by district number. This script resolves the current
officeholder per district from the canonical OpenStates bulk people export
(data.openstates.org/people/current/ca.csv — one file for both chambers) and
writes the two rosters, shaped for the registerIlgaChamber factory
({district -> {name, party, url, districtOffice:[lines], capitolOffice:[lines]}}).
A weekly GitHub Action (.github/workflows/update-ca-legislature-roster.yml) reruns
this and opens a PR when a roster changes, so officeholder data gets a human look
before it ships.

Honesty: names are never guessed. A vacant district simply doesn't appear in its
roster, and the card falls back to "district number + chamber directory" — the
factory's empty-member path. OpenStates itself is a sourced, machine-maintained
dataset (each person row carries `sources`), never hand-entered here.

Usage:
    python3 build_ca_legislature_roster.py [ca.csv] [output_dir]

With no arguments it downloads the source and writes to the repo's data/app/.
Pass a local ca.csv to build offline; pass an output_dir to redirect the write.
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


SOURCE_URL = "https://data.openstates.org/people/current/ca.csv"

# CA has 40 State Senate and 80 State Assembly districts. Floors catch a
# truncated download / schema change while tolerating transient vacancies.
CHAMBERS = {
    "upper": {"out": "ca-senate-members.json", "label": "Senate", "expected": 38},
    "lower": {"out": "ca-assembly-members.json", "label": "Assembly", "expected": 76},
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "data", "app")


def load_rows(path):
    if path:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    require_robots_once(SOURCE_URL, UA_STDLIB_DEFAULT,
                        label="ca-build-ca-legislature-roster")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def first_url(links):
    # OpenStates `links` packs the member's official page(s); pull the first
    # http(s) URL out however it's serialized (JSON array, list-of-dicts, or a
    # delimited string). The engine scheme-checks this via safeHttpUrl before it
    # ever becomes an href, so a stray value degrades to the chamber directory.
    if not links:
        return None
    # `links` is a `;`-delimited list of official pages; take the first clean
    # http(s) URL (stop at whitespace or any delimiter, incl. the `;` separator).
    m = re.search(r"https?://[^\s,;'\"\]}]+", links)
    return m.group(0) if m else None


# Put an embedded unit designator on its own comma-part so the app's
# cleanPoiAddress can strip it before geocoding the district-office pin.
# OpenStates packs the suite into the street segment ("455 Golden Gate Ave.
# Suite 14800, San Francisco, CA 94102"), which Nominatim won't resolve — but
# "455 Golden Gate Ave., Suite 14800, ..." geocodes once cleanPoiAddress drops
# the suite part. Only touches a unit designator not already comma-set off; the
# card still displays the full address (the comma just reads naturally).
_MID_UNIT_RE = re.compile(
    r"(?<!,)\s+(?=(?:suite|ste|room|rm|floor|fl|unit|apt|apartment|bldg|building|no\.?|#)\b\.?\s*#?\s*\d)",
    re.I,
)


def normalize_address(addr):
    s = _MID_UNIT_RE.sub(", ", str(addr).strip(), count=1)
    s = re.sub(r"\s*,\s*", ", ", s)        # normalize comma spacing
    s = re.sub(r"(?:,\s*){2,}", ", ", s)   # collapse repeated commas (source data has some)
    return s.strip().strip(",").strip()


def office(address, voice):
    lines = []
    if address:
        lines.append(normalize_address(address))
    if voice:
        lines.append("Phone: " + str(voice).strip())
    return lines


def resolve(rows, chamber):
    roster = {}
    for r in rows:
        if (r.get("current_chamber") or "").strip() != chamber:
            continue
        district = (r.get("current_district") or "").strip()
        name = (r.get("name") or "").strip()
        if not district or not name:
            continue
        member = {"name": name, "party": (r.get("current_party") or "").strip() or None}
        url = first_url(r.get("links"))
        if url:
            member["url"] = url
        dist = office(r.get("district_address"), r.get("district_voice"))
        if dist:
            member["districtOffice"] = dist
        cap = office(r.get("capitol_address"), r.get("capitol_voice"))
        if cap:
            member["capitolOffice"] = cap
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
        print(f"usage: {sys.argv[0]} [ca.csv] [output_dir]", file=sys.stderr)
        sys.exit(1)

    src_path = sys.argv[1] if len(sys.argv) >= 2 else None
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR
    rows = load_rows(src_path)

    os.makedirs(out_dir, exist_ok=True)
    failed = False
    for chamber, cfg in CHAMBERS.items():
        roster = resolve(rows, chamber)
        if len(roster) < cfg["expected"]:
            print(
                f"WARNING: resolved {len(roster)} CA {cfg['label']} districts "
                f"(expected >= {cfg['expected']}) — refusing to overwrite "
                f"{cfg['out']} with an incomplete roster",
                file=sys.stderr,
            )
            failed = True
            continue
        out_path = os.path.join(out_dir, cfg["out"])
        write_json(out_path, roster)
        print(f"Wrote {out_path} ({len(roster)} districts)", file=sys.stderr)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
