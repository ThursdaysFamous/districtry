#!/usr/bin/env python3
"""The county board's office address, from the county's own AFR filing.

Writes il/data/source/afr-county-offices.json, the committed intermediate
build_county_board_offices.py reads offline. It is the same shape as
isbe-county-board-chairs.json and refreshed the same way — by an operator running
this script — because a courthouse does not move.

WHY A SECOND SOURCE. `county-board-office-addresses` is Illinois's largest
card-order gap. 13 counties publish a board address of their own and 33 more take
one from ISBE's County Officers Book; 17 appeared in neither, so their cards named
no place at all: Boone, Carroll, Clinton, Crawford, DeKalb, Franklin, Fulton,
Hancock, Kendall, Marshall, Mason, McHenry, Mercer, Montgomery, Richland, Shelby
and Wayne.

THE ROUTE WAS HIDDEN BY A FILTER, NOT BY THE SOURCE. Every Illinois unit of local
government files an Annual Financial Report with the Comptroller, a county
included, and this repo has read that warehouse since 2026-09-08. But
comptroller_afr.enumerate_county keeps only rows whose label matches "in <X>
County", which is right for the sub-county bodies it was written for and drops the
county itself: a county's own unit is labelled bare, "Boone County", with no type
and no suffix. Measured 2026-09-11, all 17 file and all 17 witness a street.

THE ADDRESS IS THE UNIT'S, NOT A FILER'S, and comptroller_afr decides that rather
than this file: a street ships only where two differently-surnamed officers filed
the same one, which is the rule that stopped this project shipping a park
president's home address in 2026-09-10. A filing that witnesses only a
post-office box is kept as it stands and the builder declines it, because "Office"
names a place a reader can go — Clinton files PO Box 308 and Franklin PO Box 967.

IT AGREES WITH THE COUNTIES THAT PUBLISH THEIR OWN, which is the standing proof
and a GATE in the builder rather than a note here. Of the ten counties shipping a
board address of their own, nine file a contact block and eight name the same
street: Adams 507 Vermont, Clark 501 Archer, Grundy 1320 Union, Jackson 1001
Walnut, Jefferson 100 S Tenth, Jo Daviess 330 N Bench, Knox 200 S Cherry, Logan
601 Broadway. White publishes a post-office box where the filing gives 301 E. Main
St. in the same city, and Coles files no contact block at all.

EVERY DISTRICTED COUNTY IS READ, not only the 17, so the builder has its
comparands and a county that later stops publishing its own address is already
covered. The county list comes from the shipped app's dispatch table, the same way
the builder derives it.
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comptroller_afr import (  # noqa: E402
    PACE, SEARCH_FORM, WAREHOUSE, contact_block, new_session, search_units)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO_ROOT, "il", "index.html")
OUT = os.path.join(REPO_ROOT, "il", "data", "source", "afr-county-offices.json")

# The dispatch key is a slug; the Warehouse spells the county out. Only the
# names that differ by more than case need a row.
SEARCH_NAME = {"dewitt": "Dewitt", "dupage": "DuPage", "jo-daviess": "Jo Daviess",
               "lasalle": "LaSalle", "mcdonough": "McDonough",
               "mchenry": "McHenry", "mclean": "McLean", "rock-island": "Rock Island",
               "st-clair": "St. Clair", "dekalb": "DeKalb"}
MIN_COUNTIES = 40                # 63 districted today; a short run is a failure


def fail(msg):
    sys.exit("il-county-afr-offices: FAIL — " + msg)


def districted_keys():
    """The county keys the `county-board` dispatcher serves, from the app."""
    html = open(INDEX, encoding="utf-8").read()
    chunks = re.split(r"\n  (register[A-Za-z]*)\(\{", html)
    for i in range(1, len(chunks) - 1, 2):
        if chunks[i] != "registerCountyLayer":
            continue
        body = chunks[i + 1]
        lid = re.search(r'id:\s*"([a-z-]+)"', body)
        if lid and lid.group(1) == "county-board":
            return sorted(set(re.findall(r'key:\s*"([a-z-]+)"', body)))
    fail("no county-board dispatch entries found in %s" % INDEX)


def split_city(value):
    """-> (city, zip). The form prints them run together: "Mt Carroll IL61053"."""
    m = re.match(r"^\s*(.*?)[,\s]+IL\s*(\d{5})?(?:-\d{4})?\s*$", value, re.I)
    if not m:
        return (value.strip() or None), None
    return (m.group(1).strip() or None), (m.group(2) or None)


def county_name(key):
    return SEARCH_NAME.get(key, key.replace("-", " ").title())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    keys = districted_keys()
    if len(keys) < MIN_COUNTIES:
        fail("only %d districted county(ies) in the dispatch table" % len(keys))
    session = new_session()
    counties, missing, boxes, warnings = {}, [], [], []
    for key in keys:
        name = county_name(key)
        want = ("%s County" % name).lower()
        time.sleep(PACE)
        try:
            rows = search_units(session, name)
        except Exception as exc:                      # noqa: BLE001
            fail("the Warehouse refused %s (%s)" % (name, exc))
        hits = [(c, t) for c, t in rows if t.strip().lower() == want]
        if not hits:
            missing.append((key, "no unit labelled %r" % ("%s County" % name)))
            continue
        code, label = hits[0]
        time.sleep(PACE)
        block = contact_block(session, code, label, warnings)
        if not block:
            missing.append((key, "unit %s files no contact block" % code))
            continue
        street = (block.get("street") or "").strip()
        if not street:
            missing.append((key, "unit %s witnesses no street" % code))
            continue
        # ONE CANONICAL ADDRESS STRING, because the comparison gate in
        # build_county_board_offices.place() needs a comma before the city and
        # "IL" as its own word, and the form prints the city, state and ZIP run
        # together: "Quincy IL62301". Without this the gate answers "not
        # comparable" for every county and proves nothing.
        town, zipcode = split_city(block.get("city") or "")
        if not town:
            missing.append((key, "unit %s prints no city (%r)"
                            % (code, block.get("city"))))
            continue
        record = {"comptrollerCode": code, "filedFor": block.get("filedFor"),
                  "address": "%s, %s, IL%s" % (street, town,
                                               " " + zipcode if zipcode else ""),
                  "street": street, "city": town}
        if zipcode:
            record["zip"] = zipcode
        if block.get("phone"):
            record["phone"] = block["phone"]
        counties[key] = record
        if re.match(r"^\s*(?:P\.?\s?O\.?\s?BOX|POST OFFICE BOX)", street, re.I):
            boxes.append(key)

    if len(counties) < MIN_COUNTIES:
        fail("only %d county filing(s) read — the search or the form changed shape"
             % len(counties))

    payload = {
        "source": "Illinois Comptroller, Annual Financial Report — Contact Information",
        "sourceUrl": WAREHOUSE,
        "officialsPage": SEARCH_FORM,
        "generated": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counties": counties,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    for warning in warnings:
        print("  WARN: %s" % warning, file=sys.stderr)
    for key, why in sorted(missing):
        print("  NO ADDRESS: %s — %s" % (key, why), file=sys.stderr)
    if boxes:
        print("  POST-OFFICE BOX ONLY, which the builder declines because "
              "\"Office\" names a place: %s" % ", ".join(sorted(boxes)),
              file=sys.stderr)
    print("read %d of %d districted county filing(s), %d with a street -> %s"
          % (len(counties) + len(missing), len(keys), len(counties), args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
