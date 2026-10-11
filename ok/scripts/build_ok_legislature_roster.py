#!/usr/bin/env python3
"""
Build the Oklahoma Senate and Oklahoma House rosters (district -> current
officeholder) as same-origin app-data files, so the ok-senate / ok-house
cards join a small roster instead of reaching a third-party host at click
time.

index.html's ok-senate / ok-house layers fetch data/app/ok-senate-members.json
and ok-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script resolves the current
officeholder per district from the Open States bulk people export
(data.openstates.org/people/current/ok.csv — one file for both chambers) and
writes the two rosters, shaped for the registerIlgaChamber factory
({district -> {name, party, url, email}}). A weekly GitHub Action
(.github/workflows/update-ok-legislature-roster.yml) reruns this and opens a PR
when a roster changes, so officeholder data gets a human look before it ships.

WHAT THE EXPORT CARRIES, MEASURED 2026-10-09. 147 rows: 47 upper and 100
lower, against the 48 Senate and 101 House districts the state draws, so one
seat in each chamber is unfilled in the export. Every row carries a name,
party, district, e-mail and a link to the member's own page on oksenate.gov or
okhouse.gov. NO row carries a capitol address or telephone (0 of 147), so the
cards name the member, the party and the e-mail and link the member's own
page for the office — the chambers' own sites carry the room and the phone,
and reading them is recorded in ok/WATCH.md as the next step rather than done
here.

Honesty: names are never guessed. A district the export names nobody for is
written as an EMPTY record ({}), never left out: the fleet's chamber roster
contract is a record for every district the map draws, so the card says "No
member listed" and the generated table on ok/state-legislature.html prints
"Not listed" and counts the chamber at its real size. Leaving the key out made
that page say 47 Senate and 100 House districts at go-live. The record carries
no date on purpose, so an unchanged export produces an unchanged file and no
weekly PR; and it never says "vacant", because the export naming nobody is a
fact about the export, not a statement by the chamber. Open States itself is a sourced,
machine-maintained dataset (each person row carries `sources`), never
hand-entered here.

Usage:
    python3 build_ok_legislature_roster.py [ok.csv] [output_dir]

With no arguments it downloads the source and writes to the instance's
data/app/. Pass a local ok.csv to build offline; pass an output_dir to
redirect the write.
"""

import csv
import io
import json
import os
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once, UA_STDLIB_DEFAULT  # noqa: E402  (FLEET_SHARED)


SOURCE_URL = "https://data.openstates.org/people/current/ok.csv"

# Oklahoma seats 48 senators and 101 representatives. Floors catch a
# truncated download or a schema change while tolerating vacancies — the
# export already carries one unfilled seat in each chamber.
CHAMBERS = {
    "upper": {"out": "ok-senate-members.json", "label": "Senate", "expected": 44, "seats": 48},
    "lower": {"out": "ok-house-members.json", "label": "House", "expected": 93, "seats": 101},
}
# Floors on the e-mail field, measured at 47 of 47 and 100 of 100. A field
# every row carries going missing is the Brown County shape: the row count
# holds and the contact detail silently goes.
MIN_EMAIL_SHARE = 0.9

INSTANCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")


def load_rows(path=None):
    if path:
        with open(path, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    require_robots_once(SOURCE_URL, UA_STDLIB_DEFAULT,
                        label="ok-build-ok-legislature-roster")
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": UA_STDLIB_DEFAULT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def first_link(links):
    """The member's own page, from Open States' semicolon-joined links cell."""
    for candidate in (links or "").split(";"):
        candidate = candidate.strip()
        if candidate.startswith("http"):
            return candidate
    return None


def build_roster(rows, chamber, seats):
    roster = {}
    for row in rows:
        if (row.get("current_chamber") or "").strip() != chamber:
            continue
        district = (row.get("current_district") or "").strip().lstrip("0")
        name = (row.get("name") or "").strip()
        if not district or not name:
            continue
        if not district.isdigit() or not 1 <= int(district) <= seats:
            raise SystemExit("FAIL: %s district %r is not one of the state's %d — "
                             "the export's numbering changed" % (chamber, district, seats))
        if district in roster:
            raise SystemExit("FAIL: %s district %s carries two current members (%r and %r)"
                             % (chamber, district, roster[district]["name"], name))
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
        roster[district] = member
    return {d: roster[d] for d in sorted(roster, key=int)}


def main():
    args = sys.argv[1:]
    if len(args) > 2:
        print("usage: %s [ok.csv] [output_dir]" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    src_path = args[0] if len(args) >= 1 else None
    out_dir = args[1] if len(args) == 2 else DEFAULT_OUT_DIR

    rows = load_rows(src_path)
    os.makedirs(out_dir, exist_ok=True)
    for chamber, cfg in CHAMBERS.items():
        roster = build_roster(rows, chamber, cfg["seats"])
        if len(roster) < cfg["expected"]:
            print("FAIL: resolved %d %s districts (expected >= %d) — refusing to "
                  "overwrite the roster with an incomplete chamber"
                  % (len(roster), cfg["label"], cfg["expected"]), file=sys.stderr)
            sys.exit(1)
        emails = sum(1 for m in roster.values() if m.get("email"))
        if emails < MIN_EMAIL_SHARE * len(roster):
            print("FAIL: only %d of %d %s seats carry an e-mail — the export "
                  "stopped publishing a field it has carried on every row"
                  % (emails, len(roster), cfg["label"]), file=sys.stderr)
            sys.exit(1)
        missing = [str(d) for d in range(1, cfg["seats"] + 1) if str(d) not in roster]
        roster = {str(d): roster.get(str(d), {}) for d in range(1, cfg["seats"] + 1)}
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("Wrote %s (%d of %d districts named, %d with an e-mail; no member in the "
              "export for: %s)" % (out_path, cfg["seats"] - len(missing), cfg["seats"], emails,
                                   ", ".join(missing) or "none"), file=sys.stderr)


if __name__ == "__main__":
    main()
