#!/usr/bin/env python3
"""Write il/data/app/logan-district-officials.json from the scraper's output.

The pair to logan_district_officials_scraper.py, which reads each park
district's own Annual Financial Report filing from the Illinois Comptroller.
This half does the refusing: a run that lost coverage leaves the shipped file
alone rather than replacing it with a thinner one.

WHAT THE FLOORS GUARD, and why each is under its measured value. On
2026-09-09 all SEVEN of Logan's park districts filed, all seven for FY2025,
with 12 board officers, 2 appointed officers and a street address, city,
telephone and e-mail on every one. (11 board officers until slots A and D began
to be read for a board-titled person the unit had not already named -- see
comptroller_afr.BOARD_ONLY_SLOTS; that added San Jose Park District's Alex
Hamilton, Trustee, and moved nobody between lists.) The floors sit under those values because
a district that stops filing is a real event and must not freeze the other
six; they are not set AT seven, which would make one district's late filing
indistinguishable from the source breaking.

THE COUNT IS SEVEN AND THE SCRAPER JOINS ALL SEVEN, which is worth stating
because Peoria's sibling reads 18 of 25. Logan's join is an explicit table of
unit codes rather than a name match, and two of its rows name units filed
under ANOTHER county -- Armington Community in Tazewell, San Jose in Mason,
because a cross-county district files once. Those two carry `filesIn` so a
reader looking for the filing knows which county to search.

THE FISCAL YEAR IS REQUIRED ON EVERY DISTRICT. An AFR is a snapshot filed for
one year and the Comptroller's own page says a different year may name a
different person, so a record without one cannot be rendered honestly and the
build refuses rather than shipping a name with no date attached.

A DISTRICT WITH NO BOARD OFFICER STILL SHIPS, and ONE of the seven is in that
state: Lincoln Park District files a Director and a Manager and no trustee.
That is the district's own answer about who it publishes, not a parse failure.
The card names them under Administration and says nothing about a board, which
is what the filing supports.
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "logan-district-officials.json")

# Measured 2026-09-10: 7 districts / 12 board / 2 appointed / 4 with an office
# / 1 with a telephone. Each floor sits under its measured value; see above.
#
# THE OFFICE AND TELEPHONE FLOORS DROPPED FROM 5 ON 2026-09-10, and not because
# the source lost anything. comptroller_afr.py used to read slot A's address and
# telephone as the district's, and they are the FILER's -- so all seven Logan
# districts carried a contact and four of them were one trustee's home, mobile
# and personal e-mail. Only what the filing witnesses as the unit's now ships,
# which for a county of seven rural park districts is three addresses and
# Lincoln's telephone. A low floor here is the honest one: it is what the
# districts themselves file.
MIN_DISTRICTS = 5
MIN_BOARD = 8
MIN_WITH_OFFICE = 3
MIN_WITH_PHONE = 1
# Logan dispatches only its park districts today. A kind appearing that this
# builder does not expect means the scraper's table grew without the app's
# dispatch entries growing with it.
EXPECT_KINDS = {"park"}


def fail(msg):
    sys.exit("build-logan-district-officials: FAIL — " + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scraped", help="logan_district_officials_scraper.py --out")
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
        print("build-logan-district-officials: OK — shipped file matches "
              "(%d district(s), %d board officer(s))" % (len(districts), board))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-logan-district-officials: wrote %s — %d district(s), %d board "
          "officer(s), %d appointed, %d with an office"
          % (OUT_PATH, len(districts), board,
             sum(len(d.get("heads") or []) for d in districts.values()), with_office),
          file=sys.stderr)


if __name__ == "__main__":
    main()
