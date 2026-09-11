#!/usr/bin/env python3
"""Write il/data/app/il-library-district-officials.json from the scraper's output.

The pair to il_library_district_officials_scraper.py, which reads each
district-governed library's own Annual Financial Report filing from the Illinois
Comptroller. This half does the refusing: a run that lost coverage leaves the
shipped file alone rather than replacing it with a thinner one.

This file is keyed by library and stamps many cards per key, which is why its
floors read differently from the per-county AFR builders'. The statewide boundary
layer clips each library's service area to the county, so one library's filing
reaches a card in every county it touches: 197 libraries stamp 339 cards. Both
counts are floored because they move independently. A library that stops filing
costs a key and all of its cards at once. A library renamed in the boundary layer
costs its cards and no key at all, leaving a record here that no card can reach.
So the card count is not taken from the scraper's arithmetic; it is re-measured
against the shipped boundary files, and a key that stamps nothing fails the build.

Measured 2026-09-11: 197 of the layer's 216 district-governed names resolved,
stamping 339 of its 371 district cards, with 294 board officers, 96 appointed
officers, 175 offices and 145 telephones. The floors sit under those values
because a library filing late is a real event and must not freeze the other 196.
Setting them at the measured figures would make one late filing
indistinguishable from the source breaking.

The appointed officers are floored separately. 25 of the 197 file no board
officer at all, and their cards name a Director or a Treasurer/Administrator and
nobody else. A parse regression that dropped appointed officers alone would leave
the board count untouched and empty those 25 cards.

The fiscal year is required on every library. An AFR is a snapshot filed for one
year, and the Comptroller's own page says a different year may name a different
person, so a record without one cannot be rendered honestly and the build refuses
rather than shipping a name with no date attached.

Every record carries `filesIn`, and here that is not a footnote: a card in one
county routinely carries a library that files in another — Fossil Ridge files in
Will, Cordova in Rock Island — so the county a reader would search the Warehouse
for is part of the answer.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from il_library_district_officials_scraper import (  # noqa: E402
    shipped_cards, statewide_library_counties)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "il-library-district-officials.json")

# Measured 2026-09-11: 197 libraries / 339 cards / 294 board / 96 appointed /
# 175 with an office / 145 with a telephone. Each floor sits under its value.
MIN_LIBRARIES = 170
MIN_CARDS = 295
MIN_BOARD = 250
MIN_HEADS = 80
MIN_WITH_OFFICE = 150
MIN_WITH_PHONE = 122


def fail(msg):
    sys.exit("build-il-library-district-officials: FAIL — " + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scraped", help="il_library_district_officials_scraper.py --out")
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file instead of writing")
    args = ap.parse_args()

    with open(args.scraped, encoding="utf-8") as fh:
        payload = json.load(fh)
    libraries = payload.get("libraries") or {}
    if not isinstance(libraries, dict):
        fail("the scraper's output has no libraries object")

    _, where = shipped_cards(statewide_library_counties())
    cards = sum(len(where.get(name) or []) for name in libraries)
    orphans = sorted(name for name in libraries if not where.get(name))

    board = sum(len(v.get("board") or []) for v in libraries.values())
    heads = sum(len(v.get("heads") or []) for v in libraries.values())
    with_office = sum(1 for v in libraries.values() if (v.get("office") or {}))
    with_phone = sum(1 for v in libraries.values()
                     if (v.get("office") or {}).get("phone"))
    nobody = sorted(k for k, v in libraries.items()
                    if not (v.get("board") or []) and not (v.get("heads") or []))
    undated = sorted(k for k, v in libraries.items() if not v.get("filedFor"))
    unplaced = sorted(k for k, v in libraries.items() if not v.get("filesIn"))

    problems = []
    for count, floor, what in ((len(libraries), MIN_LIBRARIES, "librar(ies)"),
                               (cards, MIN_CARDS, "card(s) stamped"),
                               (board, MIN_BOARD, "board officer(s)"),
                               (heads, MIN_HEADS, "appointed officer(s)"),
                               (with_office, MIN_WITH_OFFICE,
                                "librar(ies) with an office"),
                               (with_phone, MIN_WITH_PHONE,
                                "librar(ies) with a telephone")):
        if count < floor:
            problems.append("%d %s < floor %d" % (count, what, floor))
    if orphans:
        problems.append("no card carries: %s" % ", ".join(orphans[:8]))
    if nobody:
        problems.append("no officer of any kind on: %s" % ", ".join(nobody[:8]))
    if undated:
        problems.append("no fiscal year on: %s" % ", ".join(undated[:8]))
    if unplaced:
        problems.append("no filing county on: %s" % ", ".join(unplaced[:8]))
    if problems:
        for problem in problems:
            print("  %s" % problem, file=sys.stderr)
        fail("refusing to write a payload that lost coverage")

    out = {
        "source": payload.get("source"),
        "sourceUrl": payload.get("sourceUrl"),
        "officialsPage": payload.get("officialsPage"),
        "generated": payload.get("generated"),
        "libraries": libraries,
    }
    text = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s is missing" % OUT_PATH)
        with open(OUT_PATH, encoding="utf-8") as fh:
            shipped = json.load(fh)
        # `generated` moves every run and says nothing about the data.
        a = {k: v for k, v in shipped.items() if k != "generated"}
        b = {k: v for k, v in out.items() if k != "generated"}
        if a != b:
            fail("%s does not match a fresh read of the filings" % OUT_PATH)
        print("build-il-library-district-officials: OK — shipped file matches "
              "(%d librar(ies) on %d card(s), %d board officer(s))"
              % (len(libraries), cards, board))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-il-library-district-officials: wrote %s — %d librar(ies) on %d "
          "card(s), %d board officer(s), %d appointed, %d with an office, %d "
          "with a telephone"
          % (OUT_PATH, len(libraries), cards, board, heads, with_office,
             with_phone))


if __name__ == "__main__":
    main()
