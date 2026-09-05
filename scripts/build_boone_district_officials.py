#!/usr/bin/env python3
"""
Build il/data/app/boone-district-officials.json from the scraper's payload.

WHAT THIS SHIPS. One roster entry per park or library district Boone County
levies, keyed by the district name the county's own tax reports use — which is
also, exactly, the `district` property on the two shipped geometry files. Each
entry carries the office (address, telephone, fax, website, a contact address),
the head of the agency, and the governing body.

ONE BOARD IS A SEAT SHORT AND THE CARD SAYS SO, because the LIBRARY does:
Ida's own list prints eight trustees and the word "Open". That is `vacancies`,
and it is the reason none of these boards is read from the County Clerk's
annual booklet — a snapshot lists the board it was handed and has no way to
show an absence.

A VACANCY IS NEVER ARITHMETIC, and this floor is what enforces it. An earlier
build computed Belvidere Park's vacancies as its stated seat count minus the
rows parsed, so when a markup quirk hid one commissioner the card announced
"1 of 5 seats is vacant" about a district whose own page names five. The
scraper now counts a vacancy only from a body's own word, and a roster that
comes up short against the seat count the body states breaks the floor here
rather than shipping as an empty seat.

THE JOIN IS A GATE, NOT AN ASSUMPTION. il/index.html stamps this roster onto
the district polygons by name, so a name that stops matching costs a card its
whole contact block SILENTLY — the geometry still draws, the card still names
the district, and nothing is obviously wrong. So the builder refuses to write
unless the roster's five keys are exactly the union of the `district` values in
boone-park-districts.json and boone-library-districts.json. Rebuilding either
side alone then fails here rather than in a reader's browser.

FLOORS ARE PER BODY, because the five bodies have four different publishers
between them and a single total would hide one going dark. Each floor is set
BELOW today's count by the room a normal departure needs (a seat falling vacant
moves these by one), and a count that drops through the floor is a refusal
rather than a smaller file. `check_roster_retention.py` covers the other half —
a FIELD quietly going empty on records that all still exist — which is the
failure no count guard here can see.

A FLOOR OF `None` MEANS NOBODY PUBLISHES THAT BOARD, and nothing is in that
state today — which is worth saying because Cherry Valley District Library was
in it for an hour of this build, on the strength of one HTTP 502 from
cherryvalleylib.org. The library publishes seven trustees with a term year and
an individual address each. A gateway error is not a measurement; the scraper
retries a 5xx before believing it, and a body that really did stop publishing
its board would ship with a sentence saying so rather than an empty heading.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

APP_DIR = os.path.join("il", "data", "app")
OUT = os.path.join(APP_DIR, "boone-district-officials.json")
GEOMETRY_FILES = [
    os.path.join(APP_DIR, "boone-park-districts.json"),
    os.path.join(APP_DIR, "boone-library-districts.json"),
]

# name -> (minimum board members, minimum agency heads). A board of None is one
# nobody publishes; see the docstring.
FLOORS = {
    "BELVIDERE PARK DISTRICT": (5, 1),
    "ROCKFORD PARK DISTRICT": (4, 1),
    "IDA PUBLIC LIBRARY": (6, 1),
    "CHERRY VALLEY DISTRICT LIBRARY": (5, 1),
    "NORTH SUBURBAN DISTRICT LIBRARY": (5, 1),
}
MIN_BODIES = 5
MIN_WITH_PHONE = 5
MIN_WITH_ADDRESS = 5


def fail(message):
    print("FAIL: %s" % message, file=sys.stderr)
    raise SystemExit(1)


def geometry_district_names():
    names = set()
    for path in GEOMETRY_FILES:
        if not os.path.exists(path):
            fail("%s is missing — build the boundaries before the roster" % path)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for feature in data.get("features", []):
            value = (feature.get("properties") or {}).get("district")
            if value:
                names.add(str(value))
    return names


def clean_person(person):
    """-> the shipped person object, dropping every field the source left
    empty. No placeholders and no invented contact: an absent field is simply
    absent, which is what the card's renderer expects."""
    out = {"name": person["name"]}
    for key in ("role", "term", "email", "phone"):
        value = person.get(key)
        if value:
            out[key] = value
    return out


def build(payload):
    districts = {}
    for body in payload["bodies"]:
        name = body["district"]
        office = {k: v for k, v in body["office"].items() if v}
        entry = {
            "kind": body["kind"],
            "office": office,
            "heads": [clean_person(p) for p in body["heads"]],
            "board": [clean_person(p) for p in body["board"]],
        }
        if body.get("boardSource"):
            entry["boardSource"] = body["boardSource"]
        if body.get("boardNote"):
            entry["boardNote"] = body["boardNote"]
        if body.get("seats"):
            entry["seats"] = body["seats"]
        if body.get("vacancies"):
            entry["vacancies"] = body["vacancies"]
        districts[name] = entry
    return {
        "source": payload["source"],
        "sourceUrl": payload["sourceUrl"],
        "officialsPage": payload["officialsPage"],
        "generated": payload["scrapedAt"],
        "districts": districts,
    }


# A SCRAPER WARNING NOBODY GREPS FOR IS NOT A GATE. The scraper checks the
# North Suburban roster PDF's Last-Modified against the last Illinois
# consolidated election — the real test of whether a document describes a board
# that still sits — and wrote the answer to a WARN line. Nothing read it: the
# weekly workflow does not grep the scraper's output, so a document that went
# stale through an election would have surfaced only in a run log nobody opens,
# while the PR it opened looked entirely normal. These prefixes are therefore
# FATAL to the build. Keep this list to warnings that mean THE DATA IS WRONG,
# not ones that mean a field is merely absent; everything else still prints.
FATAL_WARNINGS = (
    "NORTH SUBURBAN DISTRICT LIBRARY: ",
)
FATAL_WARNING_SUBSTRINGS = (
    "BEFORE the ",          # …consolidated election — the document predates it
    "carries no usable Last-Modified",   # its age cannot be checked at all
)


def check_warnings(payload):
    """FAIL on any scraper warning that says the shipped data would be wrong."""
    hits = [w for w in (payload.get("warnings") or [])
            if w.startswith(FATAL_WARNINGS)
            and any(x in w for x in FATAL_WARNING_SUBSTRINGS)]
    if hits:
        fail("the scraper reported %d warning(s) that make this data unsafe to "
             "ship:\n  - %s" % (len(hits), "\n  - ".join(hits)))


def check(out):
    districts = out["districts"]
    if len(districts) < MIN_BODIES:
        fail("%d districts, expected at least %d" % (len(districts), MIN_BODIES))

    shipped = set(districts)
    drawn = geometry_district_names()
    if shipped != drawn:
        fail("the roster and the shipped geometry name different districts — "
             "roster only: %s; geometry only: %s. The card joins them by name, "
             "so a mismatch would silently empty a contact block."
             % (sorted(shipped - drawn) or "none", sorted(drawn - shipped) or "none"))

    with_phone = sum(1 for e in districts.values() if e["office"].get("phone"))
    with_address = sum(1 for e in districts.values() if e["office"].get("address"))
    if with_phone < MIN_WITH_PHONE:
        fail("%d of %d districts carry a telephone, expected %d"
             % (with_phone, len(districts), MIN_WITH_PHONE))
    if with_address < MIN_WITH_ADDRESS:
        fail("%d of %d districts carry an office address, expected %d"
             % (with_address, len(districts), MIN_WITH_ADDRESS))

    for name, (min_board, min_heads) in FLOORS.items():
        entry = districts.get(name)
        if entry is None:
            fail("%s is missing from the roster" % name)
        if len(entry["heads"]) < min_heads:
            fail("%s: %d agency head(s), expected at least %d"
                 % (name, len(entry["heads"]), min_heads))
        if min_board is None:
            if entry["board"]:
                print("  NOTE %s now publishes a board (%d member(s)) where it "
                      "published none — give it a floor in FLOORS."
                      % (name, len(entry["board"])))
            continue
        if len(entry["board"]) < min_board:
            fail("%s: %d board member(s), expected at least %d — check the "
                 "body's own directory before lowering this floor; a seat "
                 "falling vacant is what `vacancies` is for"
                 % (name, len(entry["board"]), min_board))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="data/source/boone-district-officials.json")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped file rather than rewriting it")
    args = ap.parse_args()

    if args.check:
        if not os.path.exists(args.out):
            fail("%s is missing" % args.out)
        with open(args.out, encoding="utf-8") as fh:
            out = json.load(fh)
        check(out)
        print("boone-district-officials: OK — %d districts, %d board member(s), "
              "%d agency head(s); every key matches a drawn district"
              % (len(out["districts"]),
                 sum(len(e["board"]) for e in out["districts"].values()),
                 sum(len(e["heads"]) for e in out["districts"].values())))
        return

    with open(args.input, encoding="utf-8") as fh:
        payload = json.load(fh)
    check_warnings(payload)
    out = build(payload)
    check(out)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for name, entry in out["districts"].items():
        source = (entry.get("boardSource") or {}).get("label") or "no board published"
        print("  %-32s heads=%d board=%d%s  (%s)"
              % (name, len(entry["heads"]), len(entry["board"]),
                 " +%d vacant" % entry["vacancies"] if entry.get("vacancies") else "",
                 source))
    print("boone-district-officials: wrote %d districts -> %s"
          % (len(out["districts"]), args.out))


if __name__ == "__main__":
    main()
