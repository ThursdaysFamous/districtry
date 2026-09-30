#!/usr/bin/env python3
"""
Build il/data/app/st-clair-precinct-polling.json from the table the St. Clair
County Clerk's Election Department sent by e-mail.

WHY A DOCUMENT AND NOT A PAGE. The county's published polling list groups
precincts under combined human labels — "Belleville9,10, 12 & 16" — which
cannot be matched to single precincts without interpreting prose, and the
st-clair-precinct-polling-places gap said so since 31 Jul 2026. Asked for the
same assignment one row per precinct (2026-08-01, followed up 2026-08-16),
Sarah Hermsdorfer of the Clerk's Election Department sent exactly that on
2026-08-26: "St Clair County IL Polling Places.xlsx", one row per precinct.
The table is archived as a faithful CSV transcription at
il/data/source/raw/"St Clair County IL Polling Places 2026-08-26.csv"
(the original workbook stays with the e-mail; its one formatting quirk, a
trailing space on the STITES 1 cell, is normalised in the transcription).

THE HEADER IS A TRAP: the sheet's first column is titled "POLLING PLACE" and
holds the PRECINCT name; the venue is the second column ("LOCATION"). Read
positions, not titles.

TWO CAVEATS RIDE THE DATA, both the Clerk's own words from the same e-mail:

  * "not including East St Louis as they have their own Board of Elections."
    The county's precinct layer carries one bare "East St Louis" feature, and its
    card explains the absence instead of showing a blank row.
  * "Centreville Precincts 2,5, 7 & 8 are getting changed. That will get
    voted on during the next County Board meeting. Those will be moved to
    the New Cahokia High School on 805 Camp Jackson Rd. Cahokia Heights, IL."
    The vote had not happened when the list was sent, so the CURRENT
    assignment ships and those four cards carry the Clerk's advance notice.
    WHEN THAT VOTE PASSES THIS FILE IS STALE for those four precincts —
    re-confirm with the Clerk's office and re-run this builder.

THE JOIN IS AGAINST THE COUNTY'S OWN PRECINCT LAYER (SCC_voting_districts
layer 18, prec_name2 — the same layer the app queries), fetched live at build
time, so the shipped keys are exactly the strings the app will look up.
Matching is uppercase + whitespace-collapse, plus ONE enumerated alias: the
layer spells the township "Ofallon" where the Clerk writes "O FALLON", so
"O FALLON n" maps to the layer's "Ofallon n". Nothing fuzzier: the build
fails on any Clerk row that does not resolve, any layer precinct left
without a row (East St Louis excepted, by name), or any double-join.

Usage:
    python3 scripts/build_stclair_precinct_polling.py            # build + write
    python3 scripts/build_stclair_precinct_polling.py --check    # verify only
"""

import argparse
import csv
import json
import os
import re
import sys

import requests
from scraper_common import require_robots_once, ua_requests_default  # noqa: E402  (FLEET_SHARED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_CSV = os.path.join(REPO_ROOT, "il", "data", "source", "raw",
                       "St Clair County IL Polling Places 2026-08-26.csv")
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "st-clair-precinct-polling.json")

LAYER_URL = ("https://arcgispublicmap.co.st-clair.il.us/server/rest/services/"
             "SCC_voting_districts/MapServer/18/query"
             "?where=1%3D1&outFields=prec_name2&returnGeometry=false&f=json")

RECEIVED = "2026-08-26"
SOURCE_NOTE = ("St. Clair County Clerk's Office, Election Department, by "
               "e-mail 2026-08-26 (St Clair County IL Polling Places.xlsx, "
               "one row per precinct)")

EXPECTED_CLERK_ROWS = 149
EXPECTED_LAYER_PRECINCTS = 150

# The one precinct the Clerk's list does not cover, in the Clerk's own words.
EAST_ST_LOUIS_NOTE = ("East St. Louis runs its own Board of Election "
                      "Commissioners, so the County Clerk's polling-place "
                      "list does not cover it; the city's election board "
                      "assigns its polling places.")

# The Clerk's advance notice of 2026-08-26, on the four precincts it names.
PENDING_MOVE = {"Centreville 2", "Centreville 5", "Centreville 7", "Centreville 8"}
PENDING_NOTE = ("The County Clerk's office said on 2026-08-26 that this "
                "precinct is set to move to the new Cahokia High School, "
                "805 Camp Jackson Rd, Cahokia Heights, once the County "
                "Board votes on the change — check before election day.")


def norm(name):
    return re.sub(r"\s+", " ", str(name)).strip().upper()


def clerk_rows():
    with open(RAW_CSV, encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != ["PRECINCT", "LOCATION", "ADDRESS"]:
            sys.exit("stclair-polling: %s header changed (%r) — re-read the "
                     "transcription before trusting it" % (RAW_CSV, header))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    if len(rows) != EXPECTED_CLERK_ROWS:
        sys.exit("stclair-polling: the Clerk's table carried %d precinct rows "
                 "and the archived CSV has %d — the transcription and the "
                 "document disagree" % (EXPECTED_CLERK_ROWS, len(rows)))
    out = {}
    for precinct, place, address in rows:
        key = norm(precinct)
        if key in out:
            sys.exit("stclair-polling: %r appears twice in the Clerk's table" % precinct)
        if not re.search(r", IL \d{5}$", address.strip()):
            sys.exit("stclair-polling: %r has an address that does not end in "
                     "', IL <zip>' (%r) — a mangled row, not a style choice"
                     % (precinct, address))
        out[key] = {"place": place.strip(), "address": address.strip()}
    return out


def layer_names():
    require_robots_once(LAYER_URL, ua_requests_default(), label="il-build-stclair-precinct-polling")
    resp = requests.get(LAYER_URL, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if "error" in payload:
        sys.exit("stclair-polling: the county's precinct layer answered an "
                 "error envelope: %s" % payload["error"])
    names = [f["attributes"]["prec_name2"] for f in payload.get("features", [])]
    names = [str(n).strip() for n in names if n is not None and str(n).strip()]
    if len(names) != len(set(names)):
        sys.exit("stclair-polling: the county's layer repeats a precinct name")
    if len(names) != EXPECTED_LAYER_PRECINCTS:
        sys.exit("stclair-polling: the county's layer now carries %d precincts, "
                 "expected %d — the county re-precincted, so this join needs "
                 "re-checking against a fresh Clerk list" % (len(names), EXPECTED_LAYER_PRECINCTS))
    return names


def build():
    clerk = clerk_rows()
    names = layer_names()

    resolved, used = {}, set()
    unmatched_layer = []
    for name in names:
        key = norm(name)
        entry = clerk.get(key)
        if entry is None and key.startswith("OFALLON "):
            # the county GIS's own spelling; the Clerk writes "O FALLON n"
            entry = clerk.get("O FALLON " + key.split(" ", 1)[1])
            key = "O FALLON " + key.split(" ", 1)[1] if entry else key
        if entry is None:
            unmatched_layer.append(name)
            continue
        if key in used:
            sys.exit("stclair-polling: Clerk row %r joined two layer precincts" % key)
        used.add(key)
        row = dict(entry)
        if name in PENDING_MOVE:
            row["note"] = PENDING_NOTE
        resolved[name] = row

    if sorted(unmatched_layer) != ["East St Louis"]:
        sys.exit("stclair-polling: expected exactly one unmatched layer "
                 "precinct (East St Louis, which the Clerk's list excludes "
                 "by design) but got: %s" % (sorted(unmatched_layer) or "none"))
    resolved["East St Louis"] = {"note": EAST_ST_LOUIS_NOTE}

    unused = sorted(set(clerk) - used)
    if unused:
        sys.exit("stclair-polling: %d Clerk row(s) match no layer precinct: %s\n"
                 "  Resolve them by name rather than loosening the rule."
                 % (len(unused), unused))
    missing_pending = sorted(PENDING_MOVE - set(resolved))
    if missing_pending:
        sys.exit("stclair-polling: the Clerk's pending-move precincts %s are "
                 "not in the join — the note would be attached to nothing"
                 % missing_pending)

    payload = {
        "fetched": RECEIVED,
        "source": SOURCE_NOTE,
        "precincts": dict(sorted(resolved.items())),
    }
    return json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    parser.add_argument("--check", action="store_true",
                        help="rebuild and compare against the shipped file; writes nothing")
    args = parser.parse_args()

    text = build()
    fresh = json.loads(text)
    with_place = sum(1 for v in fresh["precincts"].values() if v.get("place"))
    with_note = sum(1 for v in fresh["precincts"].values() if v.get("note"))
    print("stclair-polling: %d precincts joined (%d with a polling place, "
          "%d carrying a Clerk's note)" % (len(fresh["precincts"]), with_place, with_note))

    if args.check:
        if not os.path.exists(OUT_PATH):
            sys.exit("--check: %s does not exist yet" % os.path.relpath(OUT_PATH, REPO_ROOT))
        with open(OUT_PATH, encoding="utf-8") as handle:
            current = json.load(handle)
        if current.get("precincts") != fresh.get("precincts"):
            sys.exit("--check: the rebuilt table no longer matches %s — the "
                     "county's precinct layer moved under the Clerk's list"
                     % os.path.relpath(OUT_PATH, REPO_ROOT))
        print("  --check OK — the join still holds against the live layer")
        return

    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("  wrote %s (%s bytes)"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), "{:,}".format(len(text))))


if __name__ == "__main__":
    main()
