#!/usr/bin/env python3
"""Write il/data/app/peoria-district-officials.json from the scraper's output.

The pair to peoria_district_officials_scraper.py, which reads each district's
own Annual Financial Report filing from the Illinois Comptroller. This half
does the refusing: a run that lost coverage leaves the shipped file alone
rather than replacing it with a thinner one.

WHAT THE FLOORS GUARD, and why each is under its measured value. On
2026-09-08 the scraper read 18 of Peoria's 25 fire, park and library
districts, with 26 board officers, 9 appointed officers and an office address
on every one. The seven it does not read are explained rather than missing --
Farmington and Williamsfield file under their home counties because a
cross-county district files once, Peoria Public Library and Peoria Heights are
municipal libraries filing inside their city and village, and Richwoods
matches its unit and files no contact block -- so the floors are set under 18
rather than at it, because a district that stops filing is a real event and
must not freeze the county's other seventeen.

THE FISCAL YEAR IS REQUIRED ON EVERY DISTRICT. An AFR is a snapshot filed for
one year and the Comptroller's own page says a different year may name a
different person, so a record without one cannot be rendered honestly and the
build refuses rather than shipping a name with no date attached.

A DISTRICT WITH NO BOARD OFFICER STILL SHIPS. Alpha Park Library and Pleasure
Driveway Park file only appointed officers -- a Director and a Manager, a
Director and a Superintendent -- and that is the district's own answer about
who it publishes, not a parse failure. The card names them under
Administration and says nothing about a board, which is what the filing
supports.
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "peoria-district-officials.json")

# Measured 2026-09-08: 18 districts / 26 board / 9 appointed / 18 with an
# office. Each floor sits under its measured value; see the module docstring.
MIN_DISTRICTS = 15
MIN_BOARD = 20
MIN_WITH_OFFICE = 15
# Every district the scraper reads carries all three kinds today. A KIND that
# disappears entirely is a source change, not turnover.
EXPECT_KINDS = {"fire", "park", "library"}


def fail(msg):
    sys.exit("build-peoria-district-officials: FAIL — " + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scraped", help="peoria_district_officials_scraper.py --out")
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file instead of writing")
    args = ap.parse_args()

    with open(args.scraped, encoding="utf-8") as fh:
        payload = json.load(fh)
    districts = payload.get("districts") or {}
    if not isinstance(districts, dict):
        fail("the scraper's output has no districts object")

    board = sum(len(d.get("board") or []) for d in districts.values())
    with_office = sum(1 for d in districts.values() if (d.get("office") or {}))
    kinds = {d.get("kind") for d in districts.values()}
    undated = sorted(k for k, d in districts.items() if not d.get("filedFor"))

    problems = []
    if len(districts) < MIN_DISTRICTS:
        problems.append("%d district(s) < floor %d" % (len(districts), MIN_DISTRICTS))
    if board < MIN_BOARD:
        problems.append("%d board officer(s) < floor %d" % (board, MIN_BOARD))
    if with_office < MIN_WITH_OFFICE:
        problems.append("%d district(s) with an office < floor %d"
                        % (with_office, MIN_WITH_OFFICE))
    missing_kinds = EXPECT_KINDS - kinds
    if missing_kinds:
        problems.append("no district of kind: %s" % ", ".join(sorted(missing_kinds)))
    if undated:
        problems.append("no fiscal year on: %s" % ", ".join(undated))
    if problems:
        for p in problems:
            print("  %s" % p, file=sys.stderr)
        fail("refusing to write a payload that lost coverage")

    out = {
        "source": payload.get("source"),
        "sourceUrl": payload.get("sourceUrl"),
        "officialsPage": payload.get("officialsPage"),
        "generated": payload.get("generated"),
        "districts": districts,
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
        print("build-peoria-district-officials: OK — shipped file matches "
              "(%d district(s), %d board officer(s))" % (len(districts), board))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-peoria-district-officials: wrote %s — %d district(s), %d board "
          "officer(s), %d appointed, %d with an office"
          % (OUT_PATH, len(districts), board,
             sum(len(d.get("heads") or []) for d in districts.values()), with_office),
          file=sys.stderr)


if __name__ == "__main__":
    main()
