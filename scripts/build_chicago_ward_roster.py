#!/usr/bin/env python3
"""
Resolve scripts/chicago_ward_scraper.py's raw output into
il/data/source/ward-members.json — one record per ward, keyed by ward number.

WHAT READS IT. scripts/build_officeholder_tables.py, which puts all 50 names in
the served bytes of il/ward.html. The map card is NOT a reader: it still calls
Socrata live, so a reader running the map is never a week behind the City, and
the page's table is a dated snapshot that names its day.

THE NAME IS FLIPPED AND THE FLIP IS PRINTED. The City publishes the alderperson
surname-first ("La Spata, Daniel"), and the app's own formatAldermanName does
the same flip at render time, so the file has to agree with the card or the two
surfaces name people differently. A row with NO comma is printed by itself
rather than flipped silently — that is either a single-word name or a change in
how the City writes the column, and both are worth seeing.

WHY THE COUNT GATE IS EXACT RATHER THAN A FLOOR. Chicago elects 50
alderpeople, one per ward, fixed by the Municipal Code; every other roster in
this repo floors a count because a county board can gain or lose a seat, and
this one cannot. 49 rows means a truncated fetch or a withdrawn row, 51 means
the dataset changed shape, and both should stop the build rather than ship a
council with the wrong number of seats in it.

Usage:
    python3 build_chicago_ward_roster.py chicago_wards.json [output_dir]
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# NOT data/app, and that is the point. validate_index.py requires every file in
# an instance's data/app to be referenced by its index.html, and this one is not:
# the ward card still calls Socrata live. A roster the app does not read is a
# build-time source, so it sits with the other build-time sources
# (afr-county-offices.json, isbe-county-board-chairs.json) and is served to
# nobody. The day the card moves onto this file, it moves to data/app, gains a
# worksheet entry and a network-first sw.js line, and that gate passes.
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "source")

WARDS = 50

# Field floors, measured against the live dataset on 2026-09-15: 50 of 50 rows
# carry a name, a ward office address, a phone and an e-mail; 27 carry a ward
# website. The floors sit under the measurement, not at it, so one alderperson
# between offices does not fail the build — but a template change that empties
# a column does. This is the Brown County shape: the row count alone was
# satisfied while seven e-mail addresses went to nothing.
MIN_EMAILS = 45
MIN_PHONES = 45
MIN_OFFICES = 45


def resolve(raw):
    rows = raw.get("wards") or []
    roster = {}
    unflipped = []
    for row in rows:
        ward = (row.get("ward") or "").strip()
        if not ward:
            continue
        name = (row.get("alderman") or "").strip()
        if name:
            if "," in name:
                last, _, first = name.partition(",")
                last, first = last.strip(), first.strip()
                name = ("%s %s" % (first, last)).strip()
            else:
                unflipped.append((ward, name))
        rec = {"name": name or None}
        office = (row.get("address") or "").strip()
        if office:
            city = (row.get("city") or "").strip()
            state = (row.get("state") or "").strip()
            zipcode = (row.get("zipcode") or "").strip()
            tail = " ".join(p for p in (city, state, zipcode) if p)
            rec["office"] = ("%s, %s" % (office, tail)) if tail else office
        # The ward WEBSITE is deliberately not carried. 27 wards publish one and
        # nothing renders it from this file — the card reads it from Socrata —
        # and validate_card_links.py's surface is each instance's data/app, which
        # this file is not in. 27 URLs nothing checks is the state that gate
        # exists to prevent, so they are left where something does check them.
        for key, src in (("phone", "ward_phone"), ("email", "email")):
            value = (row.get(src) or "").strip()
            if value:
                rec[key] = value
        rec["sourceUrl"] = raw.get("source_url")
        roster[ward] = rec
    return roster, unflipped


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: %s <raw-scraper-output.json> [output_dir]" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)
    raw_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    roster, unflipped = resolve(raw)

    for ward, name in unflipped:
        print("build-chicago-ward-roster: ward %s is published without a comma "
              "(%r) and was NOT flipped" % (ward, name), file=sys.stderr)

    if len(roster) != WARDS:
        print("build-chicago-ward-roster: FAIL — resolved %d ward(s) and Chicago "
              "elects exactly %d; refusing to overwrite the roster"
              % (len(roster), WARDS), file=sys.stderr)
        sys.exit(1)

    missing = [w for w in roster if not roster[w].get("name")]
    if missing:
        print("build-chicago-ward-roster: FAIL — %d ward(s) resolved with no name "
              "(%s); refusing to write" % (len(missing), ", ".join(sorted(missing)[:5])),
              file=sys.stderr)
        sys.exit(1)

    counts = {k: sum(1 for r in roster.values() if r.get(k))
              for k in ("email", "phone", "office")}
    for key, floor in (("email", MIN_EMAILS), ("phone", MIN_PHONES),
                       ("office", MIN_OFFICES)):
        if counts[key] < floor:
            print("build-chicago-ward-roster: FAIL — only %d of %d ward(s) carry a "
                  "%s, floor %d; the dataset's column likely changed"
                  % (counts[key], WARDS, key, floor), file=sys.stderr)
            sys.exit(1)

    ordered = {w: roster[w] for w in sorted(roster, key=int)}
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ward-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("build-chicago-ward-roster: wrote %s — %d wards, %d e-mail(s), "
          "%d phone(s), %d office(s), %d name(s) flipped surname-first"
          % (out_path, len(ordered), counts["email"], counts["phone"],
             counts["office"], len(ordered) - len(unflipped)),
          file=sys.stderr)


if __name__ == "__main__":
    main()
