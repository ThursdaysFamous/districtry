#!/usr/bin/env python3
"""Write il/data/app/il-library-contacts.json from the scraper's output.

The pair to il_library_contacts_scraper.py, which reads each Illinois public
library's office address, telephone, website and administrator from L2, the
shared directory the three library systems run. This half does the refusing: a
run that lost coverage leaves the shipped file alone rather than replacing it
with a thinner one.

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
4 on a normalisation — and 365 of those ship something the filings do not: 244 an
address, 223 a telephone, 335 a website and 286 an administrator. Five cards have
no directory row: Chatsworth Area Library District,
Dahlgren Public Library, Grand Prairie of the West Public Library District, Mount
Hope-Funk's Grove Townships Public Library District and Olmsted Public Library.

ONE OFFICER SHIPS AND IT IS NOT A TRUSTEE. Each library's own page in the
directory names a Primary Administrator, and that is the only person on it. The
Staff List and the Annual Certification both answer 403 behind a sign-in, which
is an access control and is not worked around, so the
statewide-library-officials gap stays open on the trustees.

THE WEBSITE'S KEY IS `url` FOR A REASON THAT IS NOT COSMETIC.
validate_card_links.py reads the key to decide who owns an address: `url` means
"somebody else's, exactly as they published it" and is capped at WARN, and any
other key means this repo chose the string and a dead link is a FAIL. A
library's own site is the library's.

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

# Measured 2026-09-11: 365 libraries / 244 addresses / 223 telephones / 335
# websites / 286 administrators. Every floor sits about 14% under its measured
# value, which is the same margin the first three were set with: a library
# renamed in either publisher is a real event and must not freeze the other 364.
#
# THE FIVE DENOMINATORS ARE NOT THE SAME and the two new ones are the widest.
# An address or a telephone ships only where the filing leaves one out, so 244
# and 223 count a residue. A website and an administrator come off the library's
# own page in the directory, which the filings do not carry at all, so every
# matched library can have one.
MIN_LIBRARIES = 315
MIN_WITH_ADDRESS = 210
MIN_WITH_PHONE = 190
MIN_WITH_URL = 290
MIN_WITH_ADMIN = 245


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
    with_url = sum(1 for v in libraries.values() if v.get("url"))
    with_admin = sum(1 for v in libraries.values() if v.get("admin"))
    halves = sorted(k for k, v in libraries.items()
                    if bool(v.get("address")) != bool(v.get("city")))
    empty = sorted(k for k, v in libraries.items()
                   if not any(v.get(f) for f in ("address", "phone", "url", "admin")))
    # An administrator is a PERSON on a card, so a row that names none is a
    # parse that went wrong rather than a library with no administrator.
    nameless = sorted(k for k, v in libraries.items()
                      if v.get("admin") and not (v["admin"].get("name") or "").strip())
    # MARKUP IN A SHIPPED STRING IS A PARSE THAT WENT WRONG, always. The first
    # run of the administrator pass shipped 286 names reading
    # '<a href="/user/67198">Toya Wilson</a>', because the directory wraps each
    # person in a link to their profile and clean() unescapes entities without
    # removing tags. The card renders through textContent, so it was not an
    # injection — it printed the markup at the reader. A browser render caught
    # it and no gate did, which is what this one is for.
    markup = sorted(k for k, v in libraries.items()
                    if any("<" in str(x) or ">" in str(x)
                           for x in (list(v.values()) + list((v.get("admin") or {}).values()))
                           if isinstance(x, str)))
    offsite = sorted(k for k, v in libraries.items()
                     if v.get("url") and not str(v["url"]).startswith(("http://", "https://")))

    problems = []
    for count, floor, what in ((len(libraries), MIN_LIBRARIES, "librar(ies)"),
                               (with_address, MIN_WITH_ADDRESS, "with an address"),
                               (with_phone, MIN_WITH_PHONE, "with a telephone"),
                               (with_url, MIN_WITH_URL, "with a website"),
                               (with_admin, MIN_WITH_ADMIN, "with an administrator")):
        if count < floor:
            problems.append("%d %s < floor %d" % (count, what, floor))
    if halves:
        problems.append("a street without a city, or a city without a street, on: %s"
                        % ", ".join(halves[:8]))
    if empty:
        problems.append("no address, telephone, website or administrator on: %s"
                        % ", ".join(empty[:8]))
    if nameless:
        problems.append("an administrator with no name on: %s" % ", ".join(nameless[:8]))
    if markup:
        problems.append("markup left in a shipped string on: %s" % ", ".join(markup[:8]))
    if offsite:
        problems.append("a website that is not an http(s) address on: %s"
                        % ", ".join(offsite[:8]))
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
              "%d with an address, %d with a telephone, %d with a website, "
              "%d with an administrator)"
              % (len(libraries), with_address, with_phone, with_url, with_admin))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-il-library-contacts: wrote %s — %d librar(ies), %d with an "
          "address, %d with a telephone, %d with a website, %d with an "
          "administrator"
          % (OUT_PATH, len(libraries), with_address, with_phone, with_url,
             with_admin))


if __name__ == "__main__":
    main()
