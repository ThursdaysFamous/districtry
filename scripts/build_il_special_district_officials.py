#!/usr/bin/env python3
"""Write il/data/app/il-special-district-officials.json from the scraper's output.

The pair to il_special_district_officials_scraper.py, which reads each fire and
park district's own Annual Financial Report filing from the Illinois
Comptroller. This half does the refusing: a run that lost coverage leaves the
shipped file alone rather than replacing it with a thinner one.

THE CARD COUNT IS RE-MEASURED HERE, NOT TAKEN FROM THE SCRAPER'S ARITHMETIC.
The payload is keyed by county, then layer, then the name the card reads, so a
record no polygon can reach is invisible to the scraper's own totals. Every key
is checked back against the card names, and a key that stamps nothing fails the
build.

THOSE NAMES COME FROM THE SCRAPER'S OWN INTERMEDIATE, not from a fresh read.
Ten of the twenty-seven layers ship as GeoJSON in this repo and seventeen are
fetched from a county's ArcGIS service at scrape time, and this half has to run
offline: its --check runs in CI, where nineteen county services would be
nineteen ways for an unrelated outage to fail the build. So the scraper records
the names it read and the builder measures against those.

A FIRE CARD AND A PARK CARD IN ONE COUNTY CAN SHARE A NAME. Macon's layers both
draw a `Blue Mound` and both draw a `Niantic` — four separate bodies filing four
separate reports — so the layer is part of the key and the build fails if the
two levels ever collapse.

Measured 2026-09-11 (the figures the floors sit under, each floor deliberately
below its measured value so one district filing late does not freeze the rest).

The fiscal year is required on every district. An AFR is a snapshot filed for
one year, and the Comptroller's own page says a different year may name a
different person, so a record without one cannot be rendered honestly and the
build refuses rather than shipping a name with no date attached.

A DISTRICT WITH NO BOARD OFFICER STILL SHIPS. Some file only a chief or a
director, which is that district's own answer about who it publishes, not a
parse failure. The card names them under Administration and says nothing about
a board. The appointed officers are floored separately, because a regression
that dropped them alone would leave the board count untouched.
"""

import argparse
import json
import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "il-special-district-officials.json")

# Measured 2026-09-11: 485 of the 562 cards stamped across 29 county/layer
# pairs, 579 board officers, 412 appointed, 382 cards with an office block, 348
# of those with a street address, 288 with a telephone, 171 with an e-mail, and
# 103 carrying `filesIn` because their district files under another county.
# Each floor sits under its measured value, because a district filing late is a
# real event and must not freeze the other 484.
MIN_CARDS = 420
MIN_BOARD = 490
MIN_HEADS = 340
MIN_WITH_OFFICE = 325
MIN_WITH_PHONE = 240
# Every county the scraper's table covers, and both layers. A county or a layer
# disappearing entirely is a source change rather than turnover.
EXPECT_COUNTIES = {"cook", "kendall", "macon", "rock-island", "stark",
                   "stephenson", "dupage", "mchenry", "dekalb", "lee", "adams",
                   "iroquois", "sangamon", "st-clair", "boone", "effingham",
                   "hamilton", "monroe", "madison", "lake"}
EXPECT_LAYERS = {"fire", "park"}


def fail(msg):
    sys.exit("build-il-special-district-officials: FAIL — " + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scraped", help="il_special_district_officials_scraper.py --out")
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file instead of writing")
    args = ap.parse_args()

    with open(args.scraped, encoding="utf-8") as fh:
        payload = json.load(fh)
    counties = payload.get("counties") or {}
    if not isinstance(counties, dict):
        fail("the scraper's output has no counties object")

    cards = {}
    for key, names in (payload.get("cards") or {}).items():
        county, _, layer = key.partition("/")
        cards[(county, layer)] = names
    if not cards:
        fail("the scraper's output records no card names — it is from before "
             "this builder measured against them")
    records = []                                # (county, layer, name, entry)
    orphans, undated = [], []
    for county, layers in sorted(counties.items()):
        for layer, byname in sorted(layers.items()):
            drawn = set(cards.get((county, layer)) or [])
            for name, entry in sorted(byname.items()):
                if name not in drawn:
                    orphans.append("%s/%s/%s" % (county, layer, name))
                if not entry.get("filedFor"):
                    undated.append("%s/%s/%s" % (county, layer, name))
                records.append((county, layer, name, entry))

    board = sum(len(e.get("board") or []) for _c, _l, _n, e in records)
    heads = sum(len(e.get("heads") or []) for _c, _l, _n, e in records)
    with_office = sum(1 for _c, _l, _n, e in records if (e.get("office") or {}))
    with_phone = sum(1 for _c, _l, _n, e in records
                     if (e.get("office") or {}).get("phone"))
    nobody = ["%s/%s/%s" % (c, l, n) for c, l, n, e in records
              if not (e.get("board") or e.get("heads"))]
    seen_counties = set(counties)
    seen_layers = {layer for layers in counties.values() for layer in layers}

    problems = []
    if len(records) < MIN_CARDS:
        problems.append("%d card(s) < floor %d" % (len(records), MIN_CARDS))
    if board < MIN_BOARD:
        problems.append("%d board officer(s) < floor %d" % (board, MIN_BOARD))
    if heads < MIN_HEADS:
        problems.append("%d appointed officer(s) < floor %d" % (heads, MIN_HEADS))
    if with_office < MIN_WITH_OFFICE:
        problems.append("%d card(s) with an office < floor %d"
                        % (with_office, MIN_WITH_OFFICE))
    if with_phone < MIN_WITH_PHONE:
        problems.append("%d card(s) with a telephone < floor %d"
                        % (with_phone, MIN_WITH_PHONE))
    missing = EXPECT_COUNTIES - seen_counties
    if missing:
        problems.append("no district in: %s" % ", ".join(sorted(missing)))
    unexpected = seen_counties - EXPECT_COUNTIES
    if unexpected:
        problems.append("unexpected county: %s" % ", ".join(sorted(unexpected)))
    if seen_layers - EXPECT_LAYERS:
        problems.append("unexpected layer: %s"
                        % ", ".join(sorted(seen_layers - EXPECT_LAYERS)))
    if EXPECT_LAYERS - seen_layers:
        problems.append("no district on layer: %s"
                        % ", ".join(sorted(EXPECT_LAYERS - seen_layers)))
    if orphans:
        problems.append("no polygon carries this name: %s" % ", ".join(orphans))
    if undated:
        problems.append("no fiscal year on: %s" % ", ".join(undated))
    if nobody:
        problems.append("names no officer of any kind: %s" % ", ".join(nobody))
    if problems:
        for p in problems:
            print("  %s" % p, file=sys.stderr)
        fail("refusing to write a payload that lost coverage")

    out = {
        "source": payload.get("source"),
        "sourceUrl": payload.get("sourceUrl"),
        "officialsPage": payload.get("officialsPage"),
        "generated": payload.get("generated"),
        "counties": counties,
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
        print("build-il-special-district-officials: OK — shipped file matches "
              "(%d card(s), %d board officer(s))" % (len(records), board))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    total = sum(len(names) for names in cards.values())
    print("build-il-special-district-officials: wrote %s — %d of %d card(s), "
          "%d board officer(s), %d appointed, %d with an office, %d with a "
          "telephone" % (OUT_PATH, len(records), total, board, heads,
                         with_office, with_phone))


if __name__ == "__main__":
    main()
