#!/usr/bin/env python3
"""Write il/data/app/woodford-district-officials.json from the scraper's output.

The pair to woodford_district_officials_scraper.py, which reads each fire, park
and library district's own Annual Financial Report filing from the Illinois
Comptroller. This half does the refusing: a run that lost coverage leaves the
shipped file alone rather than replacing it with a thinner one.

WHAT THE FLOORS GUARD, and why each is under its measured value. On 2026-09-10
25 of Woodford's 26 districts filed, with 41 board officers, 16 appointed
officers, 13 offices, 9 street addresses, 6 telephones and 7 e-mails. The
floors sit under those values because a district that stops filing is a real
event and must not freeze the other 24; they are not set AT the measured
figures, which would make one district's late filing indistinguishable from the
source breaking.

THE CONTACT FIGURES ARE LOW BY DESIGN AND THE FLOORS SAY SO. The AFR's contact
block has no unit-address field -- each of its four slots carries the address,
telephone and e-mail of the PERSON in that slot -- so comptroller_afr.py ships
a value only where the filing witnesses it as the district's. Nine addresses
across 25 rural districts is what those filings actually support, and a floor
set where a fuller source would put it would fail every run.

THE 26TH DISTRICT IS NAMED IN THE SCRAPER, NOT COUNTED AS A LOSS. Minonk City
Library is a municipal library filing inside the City of Minonk, so it has no
unit of its own to look up; MIN_DISTRICTS is set against the 25 that file.

THE FISCAL YEAR IS REQUIRED ON EVERY DISTRICT. An AFR is a snapshot filed for
one year and the Comptroller's own page says a different year may name a
different person, so a record without one cannot be rendered honestly and the
build refuses rather than shipping a name with no date attached.

A DISTRICT WITH NO BOARD OFFICER STILL SHIPS, and TWO of the 25 are in that
state: Dana Fire Protection District and El Paso District Library each file
only appointed officers. That is the district's own answer about who it
publishes, not a parse failure. The card names them under Administration and
says nothing about a board, which is what the filing supports.
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "woodford-district-officials.json")

# Measured 2026-09-10: 25 districts / 41 board / 16 appointed / 13 with an
# office / 6 with a telephone. Each floor sits under its measured value.
MIN_DISTRICTS = 20
MIN_BOARD = 32
MIN_WITH_OFFICE = 10
MIN_WITH_PHONE = 4
# Woodford dispatches all three concepts. A kind that disappears entirely is a
# source change, not turnover.
EXPECT_KINDS = {"fire", "park", "library"}


def fail(msg):
    sys.exit("build-woodford-district-officials: FAIL — " + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scraped", help="woodford_district_officials_scraper.py --out")
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file instead of writing")
    args = ap.parse_args()

    with open(args.scraped, encoding="utf-8") as fh:
        payload = json.load(fh)
    districts = payload.get("districts") or {}
    if not isinstance(districts, dict):
        fail("the scraper's output has no districts object")

    board = sum(len(d.get("board") or []) for d in districts.values())
    heads = sum(len(d.get("heads") or []) for d in districts.values())
    with_office = sum(1 for d in districts.values() if (d.get("office") or {}))
    with_phone = sum(1 for d in districts.values()
                     if (d.get("office") or {}).get("phone"))
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
    if with_phone < MIN_WITH_PHONE:
        problems.append("%d district(s) with a telephone < floor %d"
                        % (with_phone, MIN_WITH_PHONE))
    missing_kinds = EXPECT_KINDS - kinds
    if missing_kinds:
        problems.append("no district of kind: %s"
                        % ", ".join(sorted(missing_kinds)))
    unexpected = kinds - EXPECT_KINDS
    if unexpected:
        problems.append("unexpected district kind: %s"
                        % ", ".join(sorted(str(k) for k in unexpected)))
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
        print("build-woodford-district-officials: OK — shipped file matches "
              "(%d district(s), %d board officer(s))" % (len(districts), board))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-woodford-district-officials: wrote %s — %d district(s), %d "
          "board officer(s), %d appointed, %d with an office"
          % (OUT_PATH, len(districts), board, heads, with_office))


if __name__ == "__main__":
    main()
