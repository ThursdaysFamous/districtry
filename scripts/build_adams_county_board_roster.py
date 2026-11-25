#!/usr/bin/env python3
"""
Stage 2 of the Adams County Board roster pipeline: turn the scraper's raw
canvass JSON into data/app/adams-county-board-members.json.

WHAT SHIPS AND WHAT DOES NOT. Adams elects 21 members from 7 districts, three
apiece, on staggered four-year terms — the 2018 general elected TWO per district
under an explicit "(Vote for not more than TWO)", the 2020 primary ONE under
"(Vote for ONE)". So today's board is fourteen members seated in November 2022
and seven seated in November 2024. ONLY THE SEVEN SHIP, because the November
2022 canvass is not published anywhere this project can read: the county's own
results page sits behind the same Akamai deny as its board page, Clarity does
not carry the county, and platinumelectionresults.com — which does carry it,
and is where the seven come from — returns an empty one-page placeholder for
Adams for 2021, 2022 and 2023.

That is a partial roster and the card says so in those words. The alternative
was to keep shipping nothing, which is what this county had: before this
pipeline the card named a district and no person at all. Naming one of a
reader's three board members, with the election that seated them on the row, is
strictly more than naming none — and the shortfall is stated rather than left
for the reader to infer from a short list.

SEATS ARE ASSERTED FROM ISBE'S COUNTY-BOARD STRUCTURE TABLE (21 seats, 7
districts, 3 per district), which this repo already cites for STRUCTURE only —
its metadata is 2007-vintage and it carries no revision date, so it is never
read for people and never for currency. Two independent things agree with it
here: the county's own canvasses carry exactly seven board districts, and the
2018/2024 seat cadence (2 + 1) sums to three per district.

NOTHING IS BADGED CHAIR. ISBE's County Officers Book names Adams's chair, and
this repo's own measurement found that column wrong in 16 of the 56 counties
where a comparison was possible, so it is read nowhere (the Coles rule). A
canvass cannot show who the board later elected as its chair.

NO CONTACT DETAIL PER MEMBER, for the same reason Clark ships none: it exists
only on a page no automated client may read. The board block carries the
county's own courthouse address and the County Clerk's published number,
labelled as the Clerk's — not relabelled as the board's.

Usage:
    python3 scripts/build_adams_county_board_roster.py --raw raw.json
    python3 scripts/build_adams_county_board_roster.py            # scrape, then build
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platinum_canvass                                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_PATH = os.path.join(REPO, "il", "data", "app", "adams-county-board-members.json")
SCRAPER = os.path.join(HERE, "adams_county_board_scraper.py")

EXPECTED_DISTRICTS = 7
# ISBE's county-board structure table: 21 seats over 7 districts, 3 apiece.
SEATS_PER_DISTRICT = 3
# The floor. Seven districts must each yield exactly one member from the 2024
# general; anything less means the canvass moved or the parse broke, and this
# refuses to overwrite a good file with a thin one.
MIN_MEMBERS = 7

BOARD = {
    "address": "Adams County Courthouse, 507 Vermont Street, Quincy, IL 62301",
    "clerkPhone": "(217) 277-2150",
    "note": ("Names come from Adams County's certified election canvasses. The "
             "county's own board page cannot be read by an automated client, so "
             "no per-member phone or e-mail is published here."),
    "resultsUrl": "https://platinumelectionresults.com/history",
    "sourceUrl": "https://www.adamscountyil.gov/county-board",
}

PARTY_LETTER = {"REP": "R", "DEM": "D"}


name_case = platinum_canvass.name_case

def load_raw(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def scrape_to_temp():
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="adams-raw-")
    os.close(fd)
    subprocess.run([sys.executable, SCRAPER, "-o", tmp], check=True)
    return tmp


def build(raw):
    problems = []
    elections = raw.get("elections") or []
    # A canvass whose winners have not yet taken their seats is not the board.
    today = datetime.date.today().isoformat()
    ok = [e for e in elections
          if e.get("status") == "ok" and e.get("seated", "") <= today]
    if not ok:
        raise SystemExit("build-adams-board: no readable canvass; refusing to write")

    # Newest-first: the first canvass that carries a district seats its
    # most-recently-elected member. Adams's 2024 general is single-seat, so this
    # yields one member per district; if the 2022 file ever appears, its
    # two-seat contests add the other two without this needing to know the
    # schedule (the Clark walk).
    by_district = {}
    for election in ok:
        for dnum, contests in (election.get("districts") or {}).items():
            for contest in contests:
                seats = contest.get("seats") or 1
                winners = contest.get("candidates", [])[:seats]
                for w in winners:
                    row = {
                        "name": name_case(w["name"]),
                        "party": PARTY_LETTER.get(w["party"], w["party"]),
                        "districtSource": "elected %d (District %s, certified canvass)"
                                          % (election["year"], dnum),
                        "sourceUrl": election["url"],
                    }
                    bucket = by_district.setdefault(str(dnum), [])
                    if not any(m["name"] == row["name"] for m in bucket):
                        bucket.append(row)

    if len(by_district) != EXPECTED_DISTRICTS:
        raise SystemExit("build-adams-board: %d districts, expected %d — refusing to write"
                         % (len(by_district), EXPECTED_DISTRICTS))
    total = sum(len(v) for v in by_district.values())
    if total < MIN_MEMBERS:
        raise SystemExit("build-adams-board: %d members, floor is %d — refusing to write"
                         % (total, MIN_MEMBERS))
    for dnum, members in by_district.items():
        if len(members) > SEATS_PER_DISTRICT:
            raise SystemExit("build-adams-board: District %s has %d members for %d seats"
                             % (dnum, len(members), SEATS_PER_DISTRICT))

    out = {}
    for dnum in sorted(by_district, key=int):
        members = by_district[dnum]
        out[dnum] = {
            "members": [{k: v for k, v in m.items() if k != "sourceUrl"}
                        for m in members],
            "seats": SEATS_PER_DISTRICT,
            "sourceUrl": members[0]["sourceUrl"],
        }
    board = dict(BOARD)
    # The elections this file could NOT read, named rather than omitted, so the
    # weekly run and any reader of the data file can see which cycle is missing.
    unread = [{"election": e["label"], "status": e.get("status"), "url": e.get("url")}
              for e in elections if e not in ok]
    if unread:
        board["unreadElections"] = unread
    out["board"] = board
    return out, total, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", help="scraper output JSON (default: run the scraper)")
    args = ap.parse_args()

    tmp = None
    try:
        path = args.raw or (tmp := scrape_to_temp())
        raw = load_raw(path)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    out, total, _ = build(raw)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    unread = out["board"].get("unreadElections") or []
    print("build-adams-board: wrote %s — %d districts, %d of %d seats named%s"
          % (os.path.relpath(OUT_PATH, REPO), EXPECTED_DISTRICTS, total,
             EXPECTED_DISTRICTS * SEATS_PER_DISTRICT,
             (" (%d canvass(es) unread: %s)"
              % (len(unread), ", ".join(u["election"] for u in unread))) if unread else ""))


if __name__ == "__main__":
    main()
