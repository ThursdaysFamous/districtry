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

Honesty: names are never guessed. OpenStates itself is a sourced,
machine-maintained dataset (each person row carries `sources`), never
hand-entered here.

A VACANCY IS A RECORD AND NOT AN ABSENCE (2026-10-01). A vacant district used to
be left out of its roster entirely, and that went wrong three ways at once, all
of them reader-facing: the card fell through to the no-roster path and showed
only the district number, each legislature page's seat table takes its count from
the roster's own length and so read one short, and nothing anywhere said why.
Measured that day, Assembly District 3 was missing from the shipped file and
ca/state-legislature.html said "All 79 seats on the California State Assembly"
for a chamber of eighty; Senate District 10 was about to go the same way in a
pending refresh. A record is now written for every seat in the chamber.

TWO KINDS OF EMPTY SEAT, KEPT APART, BECAUSE ONE IS A STRONGER STATEMENT. Where
the CHAMBER'S OWN members page says the seat is empty, the record carries
`vacant: true` with the day it said so and the page that said it, and the card
and the table read "Vacant". Where our source merely names nobody, the record
carries the date alone and both read "No member listed" — a fact about our
source rather than about the seat. Calling the second a vacancy would be
guessing an officeholder out of existence, which the same honesty rule forbids
as guessing one into it.

Usage:
    python3 build_ca_legislature_roster.py [ca.csv] [output_dir]

With no arguments it downloads the source and writes to the repo's data/app/.
Pass a local ca.csv to build offline; pass an output_dir to redirect the write.
"""

import csv
import datetime
import io
import json
import os
import re
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    require_robots_once,
    UA_HEADERS_ROSTER_BOT,
    UA_ROSTER_BOT,
    UA_STDLIB_DEFAULT,
)


SOURCE_URL = "https://data.openstates.org/people/current/ca.csv"

# CA has 40 State Senate and 80 State Assembly districts. `seats` is that
# number, and it is CHECKED against the chamber's own members page on every run
# rather than merely asserted here: the page carries one entry per seat, so a
# declared count that stops matching the authority's own list fails instead of
# shipping a roster of the wrong size. `expected` is a floor on NAMED members,
# which catches a truncated download or a schema change while tolerating the
# vacancies the seat records now carry.
#
# THE AUTHORITY IS THE CHAMBER'S OWN MEMBERS PAGE, and it is read for one fact:
# which seats it calls vacant. Both chambers publish it, and they publish it
# differently -- measured 2026-10-01, the Senate renders the vacant seat with
# `data-name="Vacant"` and a `data-party` attribute carrying no value at all,
# while the Assembly renders `data-name="Vacant, Member"` with
# `data-party="Vacant"`. So a reading keyed on the party attribute alone finds
# the Assembly's vacancy and silently misses the Senate's, which is why the
# reading below tests the NAME as well and is held to both pages.
CHAMBERS = {
    "upper": {"out": "ca-senate-members.json", "label": "Senate",
              "expected": 38, "seats": 40,
              "authority": "https://www.senate.ca.gov/senators"},
    "lower": {"out": "ca-assembly-members.json", "label": "Assembly",
              "expected": 76, "seats": 80,
              "authority": "https://www.assembly.ca.gov/assemblymembers"},
}

# A seat element carries its district and the name in the seat; a vacant one
# says so in the name, in the party, or in both.
_SEAT_TAG_RE = re.compile(r"<[a-zA-Z][^>]*\bdata-district=[^>]*>")
_SEAT_DISTRICT_RE = re.compile(r'data-district="?(\d{1,2})')
_SEAT_NAME_RE = re.compile(r'data-(?:member-)?name="([^"]*)"')
_SEAT_PARTY_RE = re.compile(r'data-party="([^"]*)"')
_VACANT_RE = re.compile(r"\bvacant\b", re.I)

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


def read_authority(url, seats, label):
    """Which seats the chamber's own members page calls vacant.

    Returns {district: name-in-the-seat} for every seat the page lists. The
    caller decides what to do with it; this only reads.

    THE PAGE IS HELD TO ITS OWN SEAT COUNT. A members page that stops listing
    one entry per district has changed shape, and a vacancy read out of a page
    we no longer understand is exactly the kind of claim this project does not
    make -- so the caller is given nothing rather than a partial reading.
    """
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="ca-legislature-%s-authority" % label.lower())
    req = urllib.request.Request(url, headers=UA_HEADERS_ROSTER_BOT)
    with urllib.request.urlopen(req, timeout=60) as resp:
        page = resp.read().decode("utf-8", "replace")
    seen = {}
    for tag in _SEAT_TAG_RE.findall(page):
        d = _SEAT_DISTRICT_RE.search(tag)
        n = _SEAT_NAME_RE.search(tag)
        if not (d and n):
            continue
        # The first element carrying both wins: a page repeats the district on
        # inner elements (the Senate's own markup carries it three times per
        # seat) and only the outer one names the member.
        seen.setdefault(str(int(d.group(1))), n.group(1))
    want = {str(d) for d in range(1, seats + 1)}
    if set(seen) != want:
        raise ValueError(
            "%s members page lists %d seat(s) and this build expects %d "
            "(districts 1-%d); the page has changed shape, so no vacancy is "
            "read from it" % (label, len(seen), seats, seats))
    return seen


def vacant_districts(authority):
    """The districts whose seat the page itself names as vacant."""
    return {d for d, name in authority.items() if _VACANT_RE.search(name or "")}


def with_seat_records(roster, seats, vacant, as_of, source_url):
    """One record per seat in the chamber, named or not.

    A named member passes through untouched. A seat the authority calls vacant
    gets `vacant: true` with the day and the page that said it. Any other
    unnamed seat gets the date alone, which the card and the table read as "no
    member listed" -- a statement about our source, not about the seat.
    """
    out = dict(roster)
    for d in range(1, seats + 1):
        key = str(d)
        if out.get(key, {}).get("name"):
            continue
        if key in vacant:
            out[key] = {"vacant": True, "asOf": as_of, "sourceUrl": source_url}
        else:
            out[key] = {"asOf": as_of}
    return out


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
    as_of = datetime.date.today().isoformat()
    failed = False
    for chamber, cfg in CHAMBERS.items():
        roster = resolve(rows, chamber)
        named = sum(1 for r in roster.values() if r.get("name"))
        if named < cfg["expected"]:
            print(
                f"WARNING: resolved {named} named CA {cfg['label']} members "
                f"(expected >= {cfg['expected']}) — refusing to overwrite "
                f"{cfg['out']} with an incomplete roster",
                file=sys.stderr,
            )
            failed = True
            continue
        # THE VACANCY CLAIM NEEDS THE AUTHORITY, AND A FAILED READ SAYS LESS
        # RATHER THAN SOMETHING WRONG. If the chamber's page cannot be read, or
        # has changed shape, the unnamed seats still get a record -- so the
        # count stays right and the card still explains itself -- but none of
        # them claims a vacancy. That degradation is loud, because a roster that
        # quietly stops saying "Vacant" looks exactly like a chamber that filled
        # its seat.
        vacant = set()
        try:
            authority = read_authority(cfg["authority"], cfg["seats"], cfg["label"])
            vacant = vacant_districts(authority)
            print(f"{cfg['label']}: the chamber's own page lists "
                  f"{len(authority)} seat(s) and calls "
                  f"{len(vacant) or 'none'} vacant"
                  + (": " + ", ".join(sorted(vacant, key=int)) if vacant else ""),
                  file=sys.stderr)
        except Exception as exc:  # noqa: BLE001  (any failure degrades the same way)
            print(f"WARNING: {cfg['label']} vacancies not read from "
                  f"{cfg['authority']} ({exc.__class__.__name__}: {exc}) — "
                  f"unnamed seats will read as no member listed rather than as "
                  f"vacant", file=sys.stderr)
        roster = with_seat_records(roster, cfg["seats"], vacant, as_of,
                                   cfg["authority"])
        out_path = os.path.join(out_dir, cfg["out"])
        write_json(out_path, roster)
        unlisted = cfg["seats"] - named - len(vacant)
        print(f"Wrote {out_path} ({cfg['seats']} seats — {named} named, "
              f"{len(vacant)} vacant, {unlisted} with no member listed)",
              file=sys.stderr)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
