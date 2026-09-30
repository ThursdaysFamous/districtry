#!/usr/bin/env python3
"""
Build the CA U.S. House roster (district -> current officeholder) as a
same-origin app-data file, so the congress card joins a ~10 KB roster instead of
downloading the full national roster to every browser.

index.html's congress layer fetches data/app/congress-roster.json lazily on
first click and joins it to the pre-built CA House geometry by district number.
This script resolves the current officeholder per CA congressional district from
the canonical unitedstates/congress-legislators legislators-current.json and
writes that roster (~10 KB), shaped for the registerIlgaChamber factory
({district -> {name, party, url, capitolOffice:[lines], districtOffice:[lines]}}).
A weekly GitHub Action
(.github/workflows/update-congress-roster.yml) reruns this and opens a PR when
the roster changes, so officeholder data still gets a human look before it ships.

Honesty: names are never guessed. A district whose seat is vacant simply doesn't
appear in the roster, and the card falls back to "district number + House member
directory" — the factory's empty-member path.

Usage:
    python3 build_congress_roster.py [legislators-current.json] [output_dir]

With no arguments it downloads the source and writes to the repo's data/app/.
Pass a local legislators-current.json to build offline; pass an output_dir to
redirect the write (used by tests).
"""

import json
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

SOURCE_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
DISTRICT_OFFICES_URL = "https://unitedstates.github.io/congress-legislators/legislators-district-offices.json"
STATE = "CA"

# CA has 52 U.S. House districts. Refuse to overwrite the roster with a
# suspiciously short result (a truncated download or an upstream schema change
# should fail loudly), but allow for transient vacancies — a resigned/deceased
# member's seat legitimately has no current officeholder until a special election.
EXPECTED_DISTRICTS = 50

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "data", "app")


def load_source(path):
    if path:
        with open(path) as f:
            return json.load(f)
    # The policy is read with the client that crawls: this call sets no
    # User-Agent, so urllib's own string is what the host sees and is what
    # the robots groups are matched against.
    require_robots_once(SOURCE_URL, UA_STDLIB_DEFAULT, label="ca-build-congress-roster")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        return json.load(resp)


def rep_name(legislator):
    name = legislator.get("name") or {}
    if name.get("official_full"):
        return name["official_full"]
    first, last = name.get("first"), name.get("last")
    if first and last:
        return first + " " + last
    return last or first


def capitol_office(term):
    # The DC ("Washington") office — the one the source carries per term. Emit a
    # clean list of lines (address, phone) the factory renders under the
    # chamber's capitolLabel; drop empties so a partial record still renders.
    lines = []
    if term.get("address"):
        lines.append(str(term["address"]))
    if term.get("phone"):
        lines.append("Phone: " + str(term["phone"]))
    return lines


def load_district_offices(path):
    """bioguide -> [office, ...] for each member. Best-effort: a fetch failure
    yields {} so the roster still ships with D.C. offices only."""
    try:
        if path:
            with open(path) as f:
                data = json.load(f)
        else:
            require_robots_once(DISTRICT_OFFICES_URL, UA_STDLIB_DEFAULT, label="ca-build-congress-roster")
            with urllib.request.urlopen(DISTRICT_OFFICES_URL, timeout=60) as resp:
                data = json.load(resp)
    except Exception as exc:  # network / parse — non-fatal
        print(f"WARNING: district offices unavailable ({exc}); shipping D.C. "
              "offices only", file=sys.stderr)
        return {}
    out = {}
    for member in data:
        bioguide = (member.get("id") or {}).get("bioguide")
        if bioguide:
            out[bioguide] = member.get("offices") or []
    return out


def district_office_lines(office):
    """Address lines for one local office — street (+ suite/building), city/ST zip,
    phone — in the order officeAddressForGeocode expects (it drops the phone line
    and geocodes the rest to drop the map pin). Fields are coerced to str: the
    source occasionally types suite/zip as a bare number."""
    def s(v):
        return "" if v is None else str(v)
    lines = []
    street = s(office.get("address"))
    if street:
        if office.get("suite"):
            street += ", " + s(office.get("suite"))
        lines.append(street)
    if office.get("building"):
        lines.append(s(office.get("building")))
    if office.get("city") and office.get("state"):
        line = s(office.get("city")) + ", " + s(office.get("state"))
        if office.get("zip"):
            line += " " + s(office.get("zip"))
        lines.append(line)
    elif office.get("zip"):
        lines.append(s(office.get("zip")))
    if office.get("phone"):
        lines.append("Phone: " + s(office.get("phone")))
    return lines


def resolve_roster(legislators, offices_by_bioguide):
    # The current officeholder is the person whose most recent term is the seat
    # we're keying on — congress-legislators lists terms chronologically, so the
    # last term is the current one for anyone in legislators-current.json.
    roster = {}
    for legislator in legislators:
        terms = legislator.get("terms") or []
        if not terms:
            continue
        term = terms[-1]
        if term.get("type") != "rep" or term.get("state") != STATE:
            continue
        district = term.get("district")
        if district is None:
            continue
        member = {
            "name": rep_name(legislator),
            "party": term.get("party"),
            "url": term.get("url"),
        }
        cap = capitol_office(term)
        if cap:
            member["capitolOffice"] = cap
        member_offices = offices_by_bioguide.get((legislator.get("id") or {}).get("bioguide")) or []
        if member_offices:
            district_lines = district_office_lines(member_offices[0])
            if district_lines:
                member["districtOffice"] = district_lines
        roster[str(district)] = member
    return roster


def ordered(roster):
    # Emit districts in numeric order so the file diffs cleanly week to week.
    return {d: roster[d] for d in sorted(roster, key=int)}


def write_json(path, roster):
    with open(path, "w") as f:
        json.dump(ordered(roster), f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    if len(sys.argv) > 3:
        print(f"usage: {sys.argv[0]} [legislators-current.json] [output_dir]", file=sys.stderr)
        sys.exit(1)

    src_path = sys.argv[1] if len(sys.argv) >= 2 else None
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR

    # If a local legislators-current.json was passed, look for a cached
    # district-offices file next to it so a fully-offline build is possible.
    do_path = None
    if src_path:
        sibling = os.path.join(os.path.dirname(src_path), "legislators-district-offices.json")
        if os.path.exists(sibling):
            do_path = sibling

    legislators = load_source(src_path)
    offices = load_district_offices(do_path)
    roster = resolve_roster(legislators, offices)

    if len(roster) < EXPECTED_DISTRICTS:
        print(
            f"WARNING: resolved {len(roster)} CA U.S. House districts "
            f"(expected >= {EXPECTED_DISTRICTS}) — refusing to overwrite the "
            "roster with an incomplete delegation",
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "congress-roster.json")
    write_json(out_path, roster)

    print(f"Wrote {out_path} ({len(roster)} districts)", file=sys.stderr)


if __name__ == "__main__":
    main()
