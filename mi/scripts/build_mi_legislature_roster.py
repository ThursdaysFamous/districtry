#!/usr/bin/env python3
"""
Build the Michigan Senate and Michigan House rosters (district -> current
officeholder) as same-origin app-data files, so the mi-senate / mi-house
cards join a small roster instead of reaching a third-party host at click
time.

index.html's mi-senate / mi-house layers fetch data/app/mi-senate-members.json
and mi-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script resolves the current
officeholder per district from the canonical Open States bulk people export
(data.openstates.org/people/current/mi.csv — one file for both chambers) and
writes the two rosters, shaped for the registerIlgaChamber factory
({district -> {name, party, url, email?, capitolOffice:[lines]}}). A weekly
GitHub Action (.github/workflows/update-mi-legislature-roster.yml) reruns this
and opens a PR when a roster changes, so officeholder data gets a human look
before it ships.

THE TWO CHAMBERS SHIP DIFFERENT CONTACT DEPTH, AND IT IS A MEASUREMENT RATHER
THAN AN OVERSIGHT. Open States carries **no capitol phone and no capitol
address for any Michigan legislator** (measured 0 of 148 rows, 2026-09-03), so
unlike Wisconsin's same-shaped builder there is no office block in the base
export to lean on. The Senate's own all-senators directory publishes a Capitol
phone, e-mail, office and contact page for all 38 seats and
mi_senate_scraper.py reads it. **house.mi.gov could not be reached from this
project's build environment at all** — TLS "unable to get local issuer
certificate", with the egress proxy's CA bundle explicitly supplied, while
senate.michigan.gov answers 200 on identical flags — so the House roster ships
the Open States fields alone and claims nothing further. Whether that block is
the House site's own incomplete certificate chain or an artifact of the
sandbox is unresolved and owes one CI-side probe (mi/WATCH.md).

Honesty: names are never guessed. A vacant district simply doesn't appear in
its roster, and the card falls back to "district number + chamber directory" —
the factory's empty-member path. Open States itself is a sourced,
machine-maintained dataset (each person row carries `sources`), never
hand-entered here.

Usage:
    python3 build_mi_legislature_roster.py [mi.csv] [output_dir]

With no arguments it downloads the source and writes to the instance's
data/app/. Pass a local mi.csv to build offline (the Senate enrichment is
still fetched from the network unless it is cached alongside it as
mi-senate-directory.json); pass an output_dir to redirect the write.
"""

import csv
import io
import json
import os
import sys
import urllib.request

SOURCE_URL = "https://data.openstates.org/people/current/mi.csv"

# Every Capitol-complex address the Senate's directory publishes ends in one
# of these two building names — measured across all 38 seats, 2026-09-03
# ("Suite NNNN, Binsfeld Office Building" x32, "S-NN, Capitol Building" x6).
# An address that stops matching is DROPPED rather than shipped: the failure
# this guards is a directory that starts publishing home addresses, and the
# fleet rule is that a personal address never ships.
CAPITOL_BUILDINGS = ("Binsfeld Office Building", "Capitol Building")

# A NAME THE EXPORT CONTRADICTS IN ITS OWN ROW, corrected per seat.
#
# Open States is the roster's source and is normally taken as it comes: it is
# sourced and machine-maintained, and second-guessing a name is exactly what
# the honesty rule forbids. This table is for the one shape where the export
# is not a second opinion but a single row disagreeing with itself.
#
# ONE PUBLISHER CONTRADICTING ITSELF IS NOT TWO PUBLISHERS DISAGREEING, the
# same distinction scripts/comptroller_afr.py's LOCALITY_CORRECTIONS turns on.
# Where two bodies with standing spell a name differently, neither is
# corrected here and the disagreement is recorded instead.
#
# Measured 2026-09-17, mi.csv row for lower/7:
#     name        Tonya Phillips
#     email       tonyamyersphillips@house.mi.gov
#     links       https://housedems.com/tonya-myers-phillips/
# Both of that row's other identity fields carry "Myers", and so does the page
# they point at: housedems.com/tonya-myers-phillips/ answers 200 and prints
# "Tonya Myers Phillips" 28 times and "Tonya Phillips" not once, under the
# title "Tonya Myers Phillips - State Representative - Michigan House
# Democrats". So the export's `name` column is the outlier against its own
# row, and bot PR #970 would have replaced the name her chamber publishes with
# one it uses nowhere.
#
# AN ENTRY CANNOT OUTLIVE THE DEFECT. Each names the exported value it
# replaces, so the day Open States publishes the full name the entry stops
# matching and the run prints a STALE line naming the entry to delete. A
# warning rather than a failure on purpose: a source fixing its own row is a
# good event, and failing the weekly refresh over it would withhold every
# other seat's update to punish the source for improving.
NAME_CORRECTIONS = {
    # (chamber, district): (name as the export files it, name to ship)
    ("lower", "7"): ("Tonya Phillips", "Tonya Myers Phillips"),
}

# Michigan seats 38 senators and 110 representatives. Floors catch a truncated
# download or a schema change while tolerating transient vacancies.
CHAMBERS = {
    "upper": {"out": "mi-senate-members.json", "label": "Senate", "expected": 34},
    "lower": {"out": "mi-house-members.json", "label": "House", "expected": 99},
}

INSTANCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")


def load_rows(path=None):
    if path:
        with open(path, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    with urllib.request.urlopen(SOURCE_URL, timeout=90) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def load_senate_directory(path=None):
    """{district -> contact}. Best-effort: an outage leaves the Open States
    base untouched rather than emptying the Senate roster."""
    try:
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import mi_senate_scraper  # noqa: PLC0415 — optional enrichment, imported on use
        return mi_senate_scraper.parse(mi_senate_scraper.fetch())
    except Exception as exc:  # network / parse — non-fatal by design
        print("WARNING: Senate directory unavailable (%s); shipping the Open "
              "States base for both chambers" % exc, file=sys.stderr)
        return {}


def first_link(links):
    """The member's own site, from Open States' semicolon-joined links cell."""
    for candidate in (links or "").split(";"):
        candidate = candidate.strip()
        if candidate.startswith("http"):
            return candidate
    return None


def capitol_lines(entry):
    """The Capitol office block, or None. An address that is not one of the
    two Capitol-complex buildings is dropped and the phone kept — a phone is
    an office switchboard, an unrecognised address might be a home."""
    lines = []
    address = (entry.get("address") or "").strip()
    if address and address.endswith(CAPITOL_BUILDINGS):
        lines.append(address)
    elif address:
        print("WARNING: dropping an unrecognised Senate address (%r) — not one "
              "of %s" % (address, ", ".join(CAPITOL_BUILDINGS)), file=sys.stderr)
    phone = (entry.get("phone") or "").strip()
    if phone:
        lines.append("Phone: " + phone)
    return lines or None


def corrected_name(chamber, district, filed, warnings):
    """The exported name, with a row that contradicts itself corrected.

    Returns the name to ship. Every consultation of the table is PRINTED —
    the correction when it fires, and a STALE line when the export has moved
    on — because a silent override is indistinguishable from a guess.
    """
    entry = NAME_CORRECTIONS.get((chamber, district))
    if not entry:
        return filed
    if filed == entry[0]:
        warnings.append("%s/%s: name corrected, export files %r -> shipped %r "
                        "(NAME_CORRECTIONS)" % (chamber, district, entry[0], entry[1]))
        return entry[1]
    warnings.append("%s/%s: STALE NAME_CORRECTIONS entry — it expects the "
                    "export to file %r and the export now files %r. Delete the "
                    "entry." % (chamber, district, entry[0], filed))
    return filed


def build_roster(rows, chamber, directory, warnings=None):
    warnings = warnings if warnings is not None else []
    roster = {}
    for row in rows:
        if (row.get("current_chamber") or "").strip() != chamber:
            continue
        district = (row.get("current_district") or "").strip().lstrip("0")
        name = (row.get("name") or "").strip()
        if not district or not name:
            continue
        member = {"name": corrected_name(chamber, district, name, warnings)}
        party = (row.get("current_party") or "").strip()
        if party:
            member["party"] = party
        email = (row.get("email") or "").strip()
        if email:
            member["email"] = email
        url = first_link(row.get("links"))
        if url:
            member["url"] = url

        # Senate only: the chamber's own directory supplies the contact block
        # Open States measures empty. Fields merge individually, so a scraper
        # outage degrades to the base rather than emptying the roster.
        enrich = directory.get(district) if directory else None
        if enrich:
            if enrich.get("email"):
                member["email"] = enrich["email"]
            if enrich.get("contactUrl") and not member.get("url"):
                member["url"] = enrich["contactUrl"]
            lines = capitol_lines(enrich)
            if lines:
                member["capitolOffice"] = lines
        roster[district] = member
    return {d: roster[d] for d in sorted(roster, key=int)}


def main():
    if len(sys.argv) > 3:
        print("usage: %s [mi.csv] [output_dir]" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    src_path = sys.argv[1] if len(sys.argv) >= 2 else None
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR

    rows = load_rows(src_path)
    cached = None
    if src_path:
        sibling = os.path.join(os.path.dirname(src_path), "mi-senate-directory.json")
        if os.path.exists(sibling):
            cached = sibling
    directory = load_senate_directory(cached)

    os.makedirs(out_dir, exist_ok=True)
    warnings = []
    for chamber, cfg in CHAMBERS.items():
        roster = build_roster(rows, chamber,
                              directory if chamber == "upper" else {}, warnings)
        if len(roster) < cfg["expected"]:
            print("FAIL: resolved %d %s districts (expected >= %d) — refusing to "
                  "overwrite the roster with an incomplete chamber"
                  % (len(roster), cfg["label"], cfg["expected"]), file=sys.stderr)
            sys.exit(1)

        # A Senate roster with no office block at all means the enrichment
        # silently stopped working; the base export has never carried one, so
        # this would ship a quietly poorer card with every count guard green.
        if chamber == "upper" and directory:
            with_office = sum(1 for m in roster.values() if m.get("capitolOffice"))
            if with_office < cfg["expected"]:
                print("FAIL: only %d of %d Senate seats carry a Capitol office block "
                      "— the directory enrichment resolved but did not apply"
                      % (with_office, len(roster)), file=sys.stderr)
                sys.exit(1)

        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        offices = sum(1 for m in roster.values() if m.get("capitolOffice"))
        emails = sum(1 for m in roster.values() if m.get("email"))
        print("Wrote %s (%d districts; %d with a Capitol office, %d with an e-mail)"
              % (out_path, len(roster), offices, emails), file=sys.stderr)

    # Every NAME_CORRECTIONS consultation, printed. An entry that fired says so;
    # one the export has overtaken says DELETE. Both belong in the run log and
    # in the bot PR that reads it.
    for line in warnings:
        print(line, file=sys.stderr)
    unseen = set(NAME_CORRECTIONS) - {
        ((row.get("current_chamber") or "").strip(),
         (row.get("current_district") or "").strip().lstrip("0")) for row in rows}
    for key in sorted(unseen):
        print("%s/%s: ORPHANED NAME_CORRECTIONS entry — the export carries no "
              "such seat. Delete the entry." % key, file=sys.stderr)


if __name__ == "__main__":
    main()
