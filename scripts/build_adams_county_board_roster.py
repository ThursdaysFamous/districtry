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

# THE NOVEMBER 2026 GENERAL, which refilled the fourteen seats the 2022 general
# did: two races per district, every winner unopposed. Certified by County Clerk
# Ryan A. Niekamp on 17 November 2026 ("Canvass Cert.pdf", 9 pages, pages 4-5).
# The county's site refuses every automated client, so this was read by a person
# in a browser on 25 November 2026 and transcribed by eye; it is never fetched.
# District 3's first race had NO CANDIDATE FILED (0 votes), so that seat is not
# named here: the canvass does not say who fills it. Members take their seats on
# 7 December 2026, the first Monday of December, and are not shown before then.
CANVASS_2026 = {
    "status": "ok",
    "label": "November 2026 general",
    "year": 2026,
    "seated": "2026-12-07",
    "url": "https://www.adamscountyil.gov/home/showpublisheddocument/14169/639305268852570000",
    "districts": {d: [{"seats": len(names),
                       "candidates": [{"name": n, "party": "REP"} for n in names]}]
                  for d, names in {
                      "1": ["CHAD DOWNS", "BRUCE C. TERSTEGE"],
                      "2": ["RYAN HINKAMPER", "BARBARA J FLETCHER"],
                      "3": ["MARK DIETRICH"],
                      "4": ["TRAVIS L. COOLEY", "M. STEVE MCQUEEN"],
                      "5": ["TIM FINLAY", "JON MCCOY"],
                      "6": ["JOHN R. GUNTHER", "BRADLEY W. POULTER"],
                      "7": ["JOE ZANGER", "RUSSELL E. HINKAMPER"],
                  }.items()},
    # Shown on the card in place of the "elected in a separate cycle" note.
    "notes": {"3": ("2 of this district's 3 seats named. The November 2026 "
                    "ballot had no candidate for the third seat, and no source "
                    "this project can read names who fills it.")},
}


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
    # Checked after the refusal above, so a run that cannot read the 2024
    # canvass still fails rather than shipping 2026's members alone.
    if CANVASS_2026["seated"] <= today:
        ok.insert(0, CANVASS_2026)

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
        if CANVASS_2026 in ok and dnum in CANVASS_2026["notes"]:
            out[dnum]["note"] = CANVASS_2026["notes"][dnum]
    board = dict(BOARD)
    # The elections this file could NOT read, named rather than omitted, so the
    # weekly run and any reader of the data file can see which cycle is missing.
    unread = [{"election": e["label"], "status": e.get("status"), "url": e.get("url")}
              for e in elections if e.get("status") != "ok"]
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
