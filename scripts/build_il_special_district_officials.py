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

AN OFFICER'S OWN TELEPHONE AND E-MAIL ADDRESS SHIP ON THAT OFFICER, since
Adam's ruling of 2026-10-17 ("if the official government source uses personal
phone numbers, we publish those") and his choice of "E-mails too" the same day.
comptroller_afr.py decides which value a filing gives one officer alone and
which is the district's, and the scraper keeps Lake's own office telephone and
e-mail, which the card prints from the county's GIS, off every officer.
MIN_OFFICER_PHONES and MIN_OFFICER_EMAILS refuse a run that stops reading them;
suspect_phones_in and suspect_emails_in refuse a value not shaped like one,
naming the card and the officer's place in its list and never the value. An
address the roster's filings give beside two different people is nobody's, and
so is one that another roster built from these filings gives beside a different
person; each is taken off before anything is counted (drop_mail_given_for_two).
So is an address shown to be a former officer's (NOT_THE_OFFICERS), which no
test on one filing can see.

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

from comptroller_afr import (  # noqa: E402  (shared -- do not fork)
    count_officer_emails, count_officer_phones, drop_mail_given_for_two,
    mail_digest, mail_elsewhere, MAIL_GIVEN_FOR_TWO, OFFICER_LISTS,
    suspect_emails_in, suspect_names_in, suspect_phones_in)

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from scraper_common import substantive_changes, emit_changes_output  # noqa: E402  (shared machinery — do not fork)


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
# Officers carrying their own telephone, since Adam's ruling of 2026-10-17
# ("if the official government source uses personal phone numbers, we publish
# those"). Measured 2026-10-17: 413 of 1002 officer records (one per card a
# district draws), 8 with a second number, after the one number Lake County's
# GIS prints as a district's own is taken off. About two thirds of 413, so a
# change that stops the numbers being read fails the build instead of
# emptying them quietly.
MIN_OFFICER_PHONES = 275
# Officers carrying their own e-mail address, since Adam chose "E-mails too"
# on 2026-10-17. Measured 2026-10-17: 749 of 1002 officer records, 612 of
# them on a domain that neither carries the district's name nor is a
# government's, after 27 were taken off as given beside two different people
# in this roster's filings or another's. About two thirds of 749, so a change
# that stops the addresses being read fails the build instead of emptying
# them quietly.
MIN_OFFICER_EMAILS = 499
# Every county the scraper's table covers, and both layers. A county or a layer
# disappearing entirely is a source change rather than turnover.
EXPECT_COUNTIES = {"cook", "kendall", "macon", "rock-island", "stark",
                   "stephenson", "dupage", "mchenry", "dekalb", "lee", "adams",
                   "iroquois", "sangamon", "st-clair", "boone", "effingham",
                   "hamilton", "monroe", "madison", "lake"}
EXPECT_LAYERS = {"fire", "park"}


# AN ADDRESS SHOWN TO BE A FORMER OFFICER'S RIDES NOBODY. comptroller_afr
# refuses an address named for another person on the SAME filing, and cannot
# see a name that only an earlier filing carried. Each entry was found by
# comparing a district's filing with the one before it, and is keyed by the
# card and the address's mail_digest, never the address itself. An entry that
# matches nothing withholds nothing; the run says so, and it can be retired.
NOT_THE_OFFICERS = {
    ("st-clair", "fire", "Brooklyn Fire Dept.", "ff7b74aab6ba1d68"): (
        "2026-10-17",
        "Brooklyn FPD (088/005/06): its FY2025 filing names one officer, a "
        "Commissioner, and gives this address in two of its slots; the part "
        "before the @ carries the surname of the Clerk/Treasurer its FY2024 "
        "filing named, whom the FY2025 filing does not name"),
}


def fail(msg):
    sys.exit("build-il-special-district-officials: FAIL — " + msg)


def drop_not_the_officers(counties):
    """Take each NOT_THE_OFFICERS address off its card's officers.

    Returns (records changed, [cards whose entry matched nothing]). Messages
    name the card, never the address.
    """
    dropped, unmatched = 0, []
    for (county, layer, name, digest), (since, _why) in sorted(
            NOT_THE_OFFICERS.items()):
        entry = ((counties.get(county) or {}).get(layer) or {}).get(name) or {}
        hit = 0
        for bucket in OFFICER_LISTS:
            for person in entry.get(bucket) or []:
                value = person.get("email") if isinstance(person, dict) else None
                if (isinstance(value, str) and value
                        and mail_digest(value.casefold()) == digest):
                    person.pop("email")
                    hit += 1
        dropped += hit
        if not hit:
            unmatched.append("%s/%s/%s (recorded %s)" % (county, layer, name, since))
    return dropped, unmatched


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

    # AN ADDRESS GIVEN BESIDE TWO PEOPLE IN TWO FILINGS IS NOBODY'S, as one
    # given beside two people in one filing already is (comptroller_afr.
    # drop_mail_given_for_two): an accounting firm's mailbox typed beside a
    # different officer in each of several reports is no officer's own.
    # The same holds across the seven rosters these filings feed, so the other
    # six are read as shipped, and what this one takes off is recorded under
    # MAIL_GIVEN_FOR_TWO for them to read in turn.
    mail_withheld = {}
    elsewhere = mail_elsewhere(os.path.dirname(OUT_PATH),
                               os.path.basename(OUT_PATH))
    shared_mail = drop_mail_given_for_two(counties, elsewhere, mail_withheld)
    print("  %d officer address(es) taken off as given beside two people, "
          "in this roster's filings or another's" % shared_mail)
    former, stale = drop_not_the_officers(counties)
    print("  %d officer address(es) taken off as a former officer's "
          "(NOT_THE_OFFICERS)" % former)
    for where in stale:
        print("  NOTE — NOT_THE_OFFICERS entry for %s matched no officer's "
              "address; the filing no longer gives it, so the entry can be "
              "retired" % where)

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
    officer_phones = count_officer_phones(counties)
    officer_emails = count_officer_emails(counties)
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
    if officer_phones["withPhone"] < MIN_OFFICER_PHONES:
        problems.append("%d officer(s) with their own telephone < floor %d"
                        % (officer_phones["withPhone"], MIN_OFFICER_PHONES))
    if officer_emails["withEmail"] < MIN_OFFICER_EMAILS:
        problems.append("%d officer(s) with their own e-mail address < floor %d"
                        % (officer_emails["withEmail"], MIN_OFFICER_EMAILS))
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

    # A NAME THIS SOURCE FILED IN A SHAPE NOBODY TYPED IS REFUSED, NOT SHIPPED.
    # comptroller_afr.normalise_filed_name has already restored a middle
    # initial's comma to its period and printed that it did, so a comma left
    # over is unexplained. #1226: Walnut Public Library District's FY2026 filing
    # prints its Director as `Jaclyn G,` in two of three populated slots, and a
    # reader is better served by last week's correct spelling than this week's
    # broken one. A filed suffix comma (`, Jr.`) is admitted -- `John Shea, Jr.`
    # in this very file is the one that measures.
    for where, name, why in suspect_names_in(counties):
        problems.append("%s: %r has %s" % (where, name, why))
    # AN OFFICER'S TELEPHONE AND E-MAIL ADDRESS MUST EACH BE SHAPED LIKE ONE
    # (comptroller_afr.OFFICER_PHONE_SHAPE, OFFICER_EMAIL_SHAPE). The refusal
    # names the card and the officer's place in its list, never the value.
    for where, why in suspect_phones_in(counties) + suspect_emails_in(counties):
        problems.append("%s: %s" % (where, why))

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
    if mail_withheld:
        out[MAIL_GIVEN_FOR_TWO] = mail_withheld
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
              "(%d card(s), %d board officer(s), %d officer record(s) with "
              "their own telephone, %d with their own e-mail address)"
              % (len(records), board, officer_phones["withPhone"],
                 officer_emails["withEmail"]))
        return

    # WHAT MOVED BESIDES THE STAMP. `generated` is rewritten every run, so
    # this file differs from its base every week and the workflow opens a PR
    # whether or not an officeholder changed. The stamp is right and stays;
    # this line is what lets a reviewer tell an empty refresh from a real one
    # without reading the diff. Depth is STATED — see scraper_common.
    prior = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as fh:
            prior = json.load(fh)
    moved_lines, moved_summary = substantive_changes(
        prior, out, 'counties', 3)
    for line in moved_lines:
        print(line)
    print("  %s" % moved_summary)
    emit_changes_output(moved_summary)

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    total = sum(len(names) for names in cards.values())
    print("build-il-special-district-officials: wrote %s — %d of %d card(s), "
          "%d board officer(s), %d appointed, %d with an office, %d with a "
          "telephone, %d officer record(s) with their own telephone (%d with a "
          "second), %d with their own e-mail address"
          % (OUT_PATH, len(records), total, board, heads, with_office,
             with_phone, officer_phones["withPhone"],
             officer_phones["withSecond"], officer_emails["withEmail"]))


if __name__ == "__main__":
    main()
