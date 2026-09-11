#!/usr/bin/env python3
"""Write il/data/app/il-library-contacts.json from the scraper's output.

The pair to il_library_contacts_scraper.py, which reads each Illinois public
library's office address and telephone from L2, the shared directory the three
library systems run. This half does the refusing: a run that lost coverage leaves
the shipped file alone rather than replacing it with a thinner one.

WHAT THIS FILE HOLDS IS ONLY WHAT SHOULD SHIP. The scraper emits a field only
where the library's own Annual Financial Report does not answer it, so the card's
stamper can apply this file over the filing's office with no further judgment.
Three cases produce a field here: the filing gives nothing (173 of the 250 records
are libraries that file no AFR at all, because a municipal or township library is
covered by its city's, village's or township's report); the filing's office block
carries no address or no telephone; or the filing's address is a post-office box
with no street, which is not a place a reader can go.

Measured 2026-09-11: 368 of the layer's 373 card names match a directory row —
348 on the full name, 16 on the agency prefix that precedes a building's own name,
4 on a normalisation — and 250 of those ship something, 244 an address and 223 a
telephone. Five cards have no directory row: Chatsworth Area Library District,
Dahlgren Public Library, Grand Prairie of the West Public Library District, Mount
Hope-Funk's Grove Townships Public Library District and Olmsted Public Library.

NO OFFICER SHIPS FROM THIS SOURCE. The directory's staff lists are behind a
sign-in, so this file answers the location and contact rows and the
statewide-library-officials gap stays open on the people half.

NO E-MAIL SHIPS EITHER. 633 of the 641 directory rows carry one, mixing
institutional mailboxes with named individuals' work addresses, and a directory
row gives no way to tell them apart. The AFR route ships an e-mail only where the
filing witnesses it as the unit's.

THE FLOORS SIT UNDER THE MEASURED VALUES because a library renamed in either
publisher is a real event and must not freeze the other 249. Setting them at the
measured figures would make one rename indistinguishable from the source
breaking.

EVERY ADDRESS CARRIES A CITY. A street with no city names no place a reader can
find, so a record with one and not the other fails the build rather than shipping
half an address.
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "il-library-contacts.json")

# Measured 2026-09-11: 250 libraries / 244 addresses / 223 telephones.
MIN_LIBRARIES = 215
MIN_WITH_ADDRESS = 210
MIN_WITH_PHONE = 190


def fail(msg):
    sys.exit("build-il-library-contacts: FAIL — " + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scraped", help="il_library_contacts_scraper.py --out")
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file instead of writing")
    args = ap.parse_args()

    with open(args.scraped, encoding="utf-8") as fh:
        payload = json.load(fh)
    libraries = payload.get("libraries") or {}
    if not isinstance(libraries, dict):
        fail("the scraper's output has no libraries object")

    with_address = sum(1 for v in libraries.values() if v.get("address"))
    with_phone = sum(1 for v in libraries.values() if v.get("phone"))
    halves = sorted(k for k, v in libraries.items()
                    if bool(v.get("address")) != bool(v.get("city")))
    empty = sorted(k for k, v in libraries.items()
                   if not v.get("address") and not v.get("phone"))

    problems = []
    for count, floor, what in ((len(libraries), MIN_LIBRARIES, "librar(ies)"),
                               (with_address, MIN_WITH_ADDRESS, "with an address"),
                               (with_phone, MIN_WITH_PHONE, "with a telephone")):
        if count < floor:
            problems.append("%d %s < floor %d" % (count, what, floor))
    if halves:
        problems.append("a street without a city, or a city without a street, on: %s"
                        % ", ".join(halves[:8]))
    if empty:
        problems.append("neither an address nor a telephone on: %s"
                        % ", ".join(empty[:8]))
    if problems:
        for problem in problems:
            print("  %s" % problem, file=sys.stderr)
        fail("refusing to write a payload that lost coverage")

    out = {
        "source": payload.get("source"),
        "sourceUrl": payload.get("sourceUrl"),
        "generated": payload.get("generated"),
        "libraries": libraries,
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
            fail("%s does not match a fresh read of the directory" % OUT_PATH)
        print("build-il-library-contacts: OK — shipped file matches (%d librar(ies), "
              "%d with an address, %d with a telephone)"
              % (len(libraries), with_address, with_phone))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-il-library-contacts: wrote %s — %d librar(ies), %d with an "
          "address, %d with a telephone"
          % (OUT_PATH, len(libraries), with_address, with_phone))


if __name__ == "__main__":
    main()
