#!/usr/bin/env python3
"""
Build the N.C. Senate and N.C. House rosters (district -> current
officeholder) as same-origin app-data files, so the nc-senate / nc-house
cards join a small roster instead of reaching a third-party host at click
time.

index.html's nc-senate / nc-house layers fetch data/app/nc-senate-members.json
and nc-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script resolves the current
officeholder per district from the canonical Open States bulk people export
(data.openstates.org/people/current/nc.csv — one file for both chambers) and
writes the two rosters, shaped for the registerIlgaChamber factory
({district -> {name, party, url, email?, capitolOffice:[lines]}}). A weekly
GitHub Action (.github/workflows/update-nc-legislature-roster.yml) reruns this
and opens a PR when a roster changes, so officeholder data gets a human look
before it ships.

PEOPLE AND CONTACT DETAIL COME FROM TWO DIFFERENT PUBLISHERS, AND WHICH ONE
ANSWERS WHAT IS MEASURED (2026-09-29). Open States' nc.csv carries all 170
seats — 50 upper, 120 lower, one per district — with an e-mail on every one,
and NO capitol address, capitol phone, district address or district phone on
any of them (0 of 170). The General Assembly's own member lists carry the
other half: every listed member's Legislative Building room and Capitol
telephone, 54 of 54 Senate entries and 125 of 125 House entries. So people
and e-mail come from Open States and the office block from ncleg.gov, joined
by district, and — unlike Michigan, whose House site could not be reached at
all — BOTH chambers ship the same depth here.

THE ENRICHMENT IS CROSS-CHECKED AGAINST THE BASE, WHICH IS THE POINT OF
HAVING TWO SOURCES. ncleg.gov keeps a departed member beside their successor
and document order is alphabetical rather than chronological, so its own
scraper resolves the seat on the `(Resigned …)` / `(Appointed …)` /
`(Deceased …)` tag (see ncga_member_scraper.py). This builder then requires
the two publishers to AGREE on the surname for every district it enriches: a
district where they name different people gets the Open States row and NO
office block, and the run says so. Measured on the nine districts that
carried two people, both publishers name the same appointee 9 of 9.

Honesty: names are never guessed. A vacant district simply doesn't appear in
its roster, and the card falls back to "district number + chamber directory"
— the factory's empty-member path. Open States itself is a sourced,
machine-maintained dataset (each person row carries `sources`), never
hand-entered here.

Usage:
    python3 build_nc_legislature_roster.py [nc.csv] [output_dir]

With no arguments it downloads the source and writes to the instance's
data/app/. Pass a local nc.csv to build offline (the ncleg.gov enrichment is
still fetched from the network unless it is cached alongside it as
ncga-members.json); pass an output_dir to redirect the write.
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


SOURCE_URL = "https://data.openstates.org/people/current/nc.csv"

# North Carolina seats 50 senators and 120 representatives. Floors catch a
# truncated download or a schema change while tolerating transient vacancies.
CHAMBERS = {
    "upper": {"out": "nc-senate-members.json", "label": "Senate", "expected": 45},
    "lower": {"out": "nc-house-members.json", "label": "House", "expected": 110},
}

# Honorifics and generational suffixes ncleg.gov prints as part of the name
# and Open States does not ("Danny Earl Britt, Jr.", "Timothy Reeder, MD",
# "Robert T. Reives, II"). They are stripped for the SURNAME COMPARISON only
# — never from a name that ships, which is always the one Open States files.
NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "dds", "esq", "cpa"}

INSTANCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")


def load_rows(path=None):
    if path:
        with open(path, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    require_robots_once(SOURCE_URL, UA_STDLIB_DEFAULT,
                        label="nc-build-nc-legislature-roster")
    with urllib.request.urlopen(SOURCE_URL, timeout=90) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def load_ncga_members(path=None, required=False):
    """{chamber -> {district -> contact}}.

    Best-effort by default: an outage leaves the Open States base untouched
    rather than emptying either roster, which is right for an operator rebuild
    on a flaky connection.

    `required` INVERTS THAT, AND THE WEEKLY JOB PASSES IT. The floor below
    (`with_office < expected`) only fires when the scrape RESOLVED, so a total
    outage skips it and ships 170 seats with no office block and no telephone —
    every count guard green, 170 rows in and 170 rows out, which is exactly the
    shape `check_roster_retention.py` exists to catch after the fact. The
    retention gate would flag it on the PR's diff; failing here instead means
    the bot never opens that PR, and the run log says which publisher was down
    rather than leaving a reviewer to work it out from a diff of missing fields.
    """
    try:
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ncga_member_scraper  # noqa: PLC0415 — optional enrichment, imported on use
        return ncga_member_scraper.parse_all()
    except Exception as exc:  # network / parse
        if required:
            print("FAIL: the General Assembly's member lists were unavailable "
                  "(%s) and --require-enrichment was given — refusing to ship "
                  "170 seats with no office block and no telephone" % exc,
                  file=sys.stderr)
            sys.exit(1)
        print("WARNING: the General Assembly's member lists were unavailable "
              "(%s); shipping the Open States base for both chambers" % exc,
              file=sys.stderr)
        return {}


def surname(name):
    """The last name-bearing token, suffixes and honorifics removed.

    Used only to ask whether two publishers named the same person. It is
    deliberately crude in one direction — a hyphenated or two-word surname
    reduces to its last word — because a false DISAGREEMENT costs an office
    block and a false agreement would ship a room number against the wrong
    member.
    """
    tokens = [t for t in re.split(r"[\s,]+", (name or "").replace(".", "")) if t]
    while tokens and tokens[-1].lower() in NAME_SUFFIXES:
        tokens.pop()
    return tokens[-1].lower() if tokens else ""


def first_link(links):
    """The member's own site, from Open States' semicolon-joined links cell."""
    for candidate in (links or "").split(";"):
        candidate = candidate.strip()
        if candidate.startswith("http"):
            return candidate
    return None


def office_lines(entry):
    """The Capitol office block, or None.

    ncleg.gov publishes a Legislative Building ROOM and a Capitol telephone
    and no street address at all, so there is no home-address risk of the
    shape Michigan's Senate scraper guards against — and equally no address
    to print, which is why the room is labelled rather than shipped bare.
    """
    lines = []
    room = (entry.get("office") or "").strip()
    if room:
        lines.append("Legislative Building, " + room)
    phone = (entry.get("phone") or "").strip()
    if phone:
        lines.append("Phone: " + phone)
    return lines or None


def build_roster(rows, chamber, members, warnings=None):
    warnings = warnings if warnings is not None else []
    roster = {}
    for row in rows:
        if (row.get("current_chamber") or "").strip() != chamber:
            continue
        district = (row.get("current_district") or "").strip().lstrip("0")
        name = (row.get("name") or "").strip()
        if not district or not name:
            continue
        member = {"name": name}
        party = (row.get("current_party") or "").strip()
        if party:
            member["party"] = party
        email = (row.get("email") or "").strip()
        if email:
            member["email"] = email
        url = first_link(row.get("links"))
        if url:
            member["url"] = url

        # The chamber's own office block, only where both publishers name the
        # same person. A disagreement is a seat that changed hands between the
        # two reads, or a parse that resolved the wrong entry; either way the
        # room and telephone would be somebody else's.
        enrich = (members.get(chamber) or {}).get(district) if members else None
        if enrich:
            if surname(enrich.get("name")) == surname(name):
                lines = office_lines(enrich)
                if lines:
                    member["capitolOffice"] = lines
            else:
                warnings.append(
                    "%s/%s: publishers disagree — Open States files %r, ncleg.gov "
                    "files %r. Shipping the Open States row with no office block."
                    % (chamber, district, name, enrich.get("name")))
        roster[district] = member
    return {d: roster[d] for d in sorted(roster, key=int)}


def main():
    args = [a for a in sys.argv[1:] if a != "--require-enrichment"]
    required = "--require-enrichment" in sys.argv[1:]
    if len(args) > 2:
        print("usage: %s [--require-enrichment] [nc.csv] [output_dir]"
              % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    src_path = args[0] if len(args) >= 1 else None
    out_dir = args[1] if len(args) == 2 else DEFAULT_OUT_DIR

    rows = load_rows(src_path)
    cached = None
    if src_path:
        sibling = os.path.join(os.path.dirname(src_path), "ncga-members.json")
        if os.path.exists(sibling):
            cached = sibling
    members = load_ncga_members(cached, required=required)
    if required and not all(members.get(c) for c in CHAMBERS):
        print("FAIL: --require-enrichment was given and the General Assembly's "
              "member lists resolved for %s of %s chambers — refusing to ship a "
              "chamber with no office block"
              % (sum(1 for c in CHAMBERS if members.get(c)), len(CHAMBERS)),
              file=sys.stderr)
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    warnings = []
    for chamber, cfg in CHAMBERS.items():
        roster = build_roster(rows, chamber, members, warnings)
        if len(roster) < cfg["expected"]:
            print("FAIL: resolved %d %s districts (expected >= %d) — refusing to "
                  "overwrite the roster with an incomplete chamber"
                  % (len(roster), cfg["label"], cfg["expected"]), file=sys.stderr)
            sys.exit(1)

        # A roster with no office block at all means the enrichment silently
        # stopped working; the base export has never carried one, so this
        # would ship a quietly poorer card with every count guard green.
        if members.get(chamber):
            with_office = sum(1 for m in roster.values() if m.get("capitolOffice"))
            if with_office < cfg["expected"]:
                print("FAIL: only %d of %d %s seats carry an office block — the "
                      "ncleg.gov enrichment resolved but did not apply"
                      % (with_office, len(roster), cfg["label"]), file=sys.stderr)
                sys.exit(1)

        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        offices = sum(1 for m in roster.values() if m.get("capitolOffice"))
        emails = sum(1 for m in roster.values() if m.get("email"))
        print("Wrote %s (%d districts; %d with an office block, %d with an e-mail)"
              % (out_path, len(roster), offices, emails), file=sys.stderr)

    # Every publisher disagreement, printed. These belong in the run log and in
    # the bot PR that reads it — a seat shipped without its office block is a
    # quieter change than a name change and needs saying.
    for line in warnings:
        print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
