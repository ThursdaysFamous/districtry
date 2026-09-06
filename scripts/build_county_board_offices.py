#!/usr/bin/env python3
"""
Build il/data/app/il-county-board-offices.json — the county board's OFFICE
ADDRESS for the districted counties whose own roster publishes none.

THE GAP THIS CLOSES. `county-board-office-addresses` is Illinois's largest
card-order gap: of 63 districted board cards, 13 name an office and 50 name
none. The fleet's card convention is identity -> LOCATION -> contact -> link,
and fifty cards were skipping the location outright.

WHERE THE ADDRESS COMES FROM, AND WHY THIS SOURCE AND NOT ITS NEIGHBOUR. ISBE's
County Officers Book names one officer per office in all 102 counties, and this
repo already parses it (scripts/isbe_county_officers_scraper.py ->
scripts/build_county_board_chairs.py). Its CHAIR NAME column is read NOWHERE
here and must stay that way: measured 2026-08-20, it names a different chair in
16 of the 56 counties where a comparison is possible, and in the ten checked
live the person it names appears nowhere on the county's current board page.
Twenty-nine per cent wrong disqualifies a name printed under "who represents
you".

THE ADDRESS COLUMN IS A DIFFERENT COLUMN WITH A DIFFERENT FAILURE MODE, and
that is the whole argument for using it. A chair turns over every election
cycle; a courthouse does not move. Two things are measured rather than assumed:

  1. IT IS ALREADY CORROBORATED INSIDE ITS OWN DOCUMENT. build_county_board_chairs
     emits `office.address` ONLY when a second courthouse office on the same
     county's page prints the same street and city — so what ships is a shared
     public building, never a home address, which is the line this repo does not
     cross (the Madison/Peoria rule). 72 of 102 counties clear that bar.
  2. IT AGREES WITH EVERY COUNTY THAT PUBLISHES ITS OWN. Seven of the 13 counties
     that ship a board address have an ISBE address to compare against, and all
     seven name the same building — the differences are abbreviation ("200 South
     Cherry" vs "200 South Cherry Street"), an added room, or an added PO box.
     THAT COMPARISON IS A GATE HERE, not a note: if any county's own published
     address ever stops matching ISBE's, this refuses to write, because the
     column's reliability is exactly what the disagreement would disprove.

WHAT SHIPS AND WHAT DOES NOT. Only counties that (a) dispatch a districted
board card, (b) have a corroborated ISBE address, and (c) do NOT already ship
one of their own. The county's own publication always wins and is never
overwritten — this file is a floor, not an override — so the exclusion list is
maintained by measurement rather than by hand.

The card labels it as what it is: the state's directory, with the document's own
"last updated" date on the row. A reader is told where the address came from.
"""

import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_index import _first_office_address  # noqa: E402  (one copy of the rule)

APP_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
SOURCE = os.path.join(REPO_ROOT, "il", "data", "source",
                      "isbe-county-board-chairs.json")
INDEX = os.path.join(REPO_ROOT, "il", "index.html")
OUT_NAME = "il-county-board-offices.json"

# Counties whose board card renders its office from live GIS rather than from a
# shipped roster file, so no *-board-*.json carries the address. They are
# ANSWERED and must never be given a fallback row.
LIVE_RENDER = ("cook", "lake")

MIN_OFFICES = 30          # 33 today; a collapse means the source changed shape


def fail(msg):
    raise SystemExit("build-county-board-offices: FAIL — " + msg)


def districted_keys():
    """The county keys the `county-board` dispatcher actually serves.

    Read from the shipped app rather than listed here, so a county that joins
    or leaves the layer is picked up without an edit — the same reason
    validate_index.py derives this list instead of keeping one.
    """
    html = open(INDEX, encoding="utf-8").read()
    chunks = re.split(r"\n  (register[A-Za-z]*)\(\{", html)
    for i in range(1, len(chunks) - 1, 2):
        if chunks[i] != "registerCountyLayer":
            continue
        body = chunks[i + 1]
        lid = re.search(r'id:\s*"([a-z-]+)"', body)
        if lid and lid.group(1) == "county-board":
            return set(re.findall(r'key:\s*"([a-z-]+)"', body))
    fail("no county-board dispatch entries found in il/index.html")


def own_address(key):
    """The address a county's OWN shipped roster publishes, if any.

    Reads through validate_index's own `_first_office_address` rather than
    re-implementing it. TWO SHAPES ARE CURRENT and a reader of one file would
    only meet the first: eleven counties hoist a `board.address`, and Vermilion
    stores the same string nine times as a per-district `officeAddress`. The
    first draft here read only `board.address`, so it offered Vermilion a
    fallback address it already publishes — a second copy of the rule that had
    already drifted from the gate that enforces it.
    """
    import glob
    for path in sorted(glob.glob(os.path.join(APP_DIR, "*.json"))):
        base = os.path.basename(path)[:-len(".json")]
        if "board" not in base and "commission" not in base:
            continue
        if not base.startswith(key + "-"):
            continue
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        found = _first_office_address(data)
        if found:
            return found
    return None


def place(addr):
    """(house number, street tokens, city) — the comparison key.

    Deliberately loose about everything a directory varies freely: "St." vs
    "Street", an added "Room 106", an added PO box, a leading building name.
    Deliberately strict about the house number and the city, which is what
    "the same building" means.
    """
    if not addr:
        return None
    text = re.sub(r"\s+", " ", addr.replace(".", " ")).strip()
    # A PO BOX NUMBER IS NOT A HOUSE NUMBER, and reading it as one is how the
    # first draft of this gate reported White County as a DISAGREEMENT: the
    # county publishes "PO Box 339, Carmi" and ISBE publishes "301 East Main
    # Street, P.O. Box 339, Carmi" — the same office, and the two keys were
    # "339" against "301". So box numbers are skipped when looking for the
    # street number, and an address that has only a box has no street key at
    # all: it is NOT COMPARABLE on the building, which is a different verdict
    # from disagreeing about it.
    # ...and neither is a ZIP CODE, which is what the first fix reached for
    # instead: skipping White's box number left the next number in the string,
    # 62821. So the city/state clause is located FIRST and the street number is
    # looked for only in the text before it.
    city = re.search(r",\s*([A-Za-z .'-]+?)\s*,?\s*IL\b", text, re.I)
    num = None
    if city:
        for m in re.finditer(r"\b(\d{1,6})\b", text[:city.start()]):
            before = text[:m.start()].rstrip().lower()
            if re.search(r"\b(p\s*o\s*box|box)$", before):
                continue
            num = m
            break
    if not (num and city):
        return None
    after = text[num.end():]
    after = re.split(r",", after)[0]
    stop = {"st", "street", "ave", "avenue", "rd", "road", "dr", "drive",
            "blvd", "boulevard", "ln", "lane", "pl", "place", "sq", "square",
            "n", "s", "e", "w", "north", "south", "east", "west", "room",
            "suite", "ste", "floor", "fl", "po", "box"}
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", after)]
    core = frozenset(w for w in words if w not in stop)
    return (num.group(1), core, re.sub(r"\s+", " ", city.group(1)).strip().lower())


def same_building(a, b):
    pa, pb = place(a), place(b)
    if not (pa and pb):
        return None                        # not comparable, not a disagreement
    if pa[0] != pb[0] or pa[2] != pb[2]:
        return False
    return bool(pa[1] & pb[1]) or not (pa[1] and pb[1])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file matches a fresh build; write nothing")
    args = ap.parse_args()

    if not os.path.exists(SOURCE):
        fail("%s is missing — run scripts/build_county_board_chairs.py first"
             % os.path.relpath(SOURCE, REPO_ROOT))
    raw = json.load(open(SOURCE, encoding="utf-8"))
    keys = districted_keys()

    # THE GATE. Every county that publishes its own address and has an ISBE one
    # must name the same building. This is the evidence that licenses using the
    # column at all, so it is re-run on every build rather than quoted.
    agree, mismatched, incomparable = [], [], []
    for key in sorted(keys):
        mine = own_address(key)
        theirs = (raw.get(key) or {}).get("office", {}).get("address")
        if not (mine and theirs):
            continue
        verdict = same_building(mine, theirs)
        if verdict is None:
            incomparable.append(key)
        elif verdict:
            agree.append(key)
        else:
            mismatched.append("%s (own %r vs ISBE %r)" % (key, mine, theirs))
    if mismatched:
        fail("the state's directory disagrees with a county's OWN published "
             "board address in %d case(s): %s. That disagreement is exactly "
             "what would disprove this column, so nothing is written until a "
             "human looks."
             % (len(mismatched), "; ".join(mismatched)))
    if len(agree) < 5:
        fail("only %d county(ies) could be compared against their own "
             "published address (need at least 5) — the corroboration this "
             "file rests on has thinned out" % len(agree))

    out = {}
    for key in sorted(keys):
        if key in LIVE_RENDER or own_address(key):
            continue                       # the county's own publication wins
        rec = raw.get(key) or {}
        office = rec.get("office") or {}
        if not office.get("address"):
            continue
        out[key] = {
            "address": office["address"],
            "confirmedBy": office.get("confirmedBy"),
            "asOf": rec.get("asOf"),
            "sourceUrl": rec.get("sourceUrl"),
        }

    if len(out) < MIN_OFFICES:
        fail("only %d office address(es) resolved, expected at least %d — the "
             "source changed shape or the dispatch table moved"
             % (len(out), MIN_OFFICES))

    payload = json.dumps({
        "note": ("County board office addresses from the Illinois State Board "
                 "of Elections' County Officers Book. Each is published on the "
                 "board chair's own row and corroborated against a second "
                 "courthouse office on the same county's page, so it is a "
                 "shared public building rather than anyone's home. A county "
                 "that publishes its own board address is NOT in this file — "
                 "its own publication is what ships."),
        "offices": out,
    }, indent=1, sort_keys=True) + "\n"

    path = os.path.join(APP_DIR, OUT_NAME)
    if args.check:
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if current != payload:
            fail("il/data/app/%s is stale — rerun "
                 "python3 scripts/build_county_board_offices.py" % OUT_NAME)
        print("build-county-board-offices: OK — %d office(s) current; %d county"
              "(ies) agree with their own published address, %d not comparable"
              % (len(out), len(agree), len(incomparable)))
        return 0

    open(path, "w", encoding="utf-8").write(payload)
    print("build-county-board-offices: wrote il/data/app/%s — %d office(s) for "
          "districted boards that publish none; %d county(ies) agree with their "
          "own published address, %d not comparable"
          % (OUT_NAME, len(out), len(agree), len(incomparable)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
