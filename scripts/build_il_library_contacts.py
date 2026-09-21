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
address, 223 a telephone, 331 a website and 286 an administrator. Five cards have
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

A WEBSITE WHOSE HOST DOES NOT RESOLVE NEVER REACHES HERE. The scraper drops it
and prints the drop, because the card labels the link "Library website" and a
host that does not exist makes that label a false statement — the same rule
Douglas County's roster follows on a mistyped e-mail domain. Four of 335 went
that way on 2026-09-11, leaving 331; one was a plain typo in the directory.
MIN_WITH_URL is what stops a broken resolver emptying the field: a run that lost
most of them falls under the floor and this refuses to write.

NO E-MAIL SHIPS EITHER. 633 of the 641 directory rows carry one, mixing
institutional mailboxes with named individuals' work addresses, and a directory
row gives no way to tell them apart. The AFR route ships an e-mail only where the
filing witnesses it as the unit's.

THE FLOORS SIT UNDER THE MEASURED VALUES because a library renamed in either
publisher is a real event and must not freeze the other 364. Setting them at the
measured figures would make one rename indistinguishable from the source
breaking.

EVERY ADDRESS CARRIES A CITY. A street with no city names no place a reader can
find, so a record with one and not the other fails the build rather than shipping
half an address.
"""

import argparse
import json
import os
import re
import sys

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from scraper_common import substantive_changes, emit_changes_output  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "il-library-contacts.json")

# Measured 2026-09-11: 365 libraries / 331 websites / 286 administrators, and
# re-measured 2026-09-15 for the two the scraper's merge rule moved: 364
# addresses / 360 telephones. Every floor sits about 14% under its measured
# value, which is the same margin the first three were set with: a library
# renamed in either publisher is a real event and must not freeze the other 364.
#
# THE FIVE DENOMINATORS USED TO DIFFER AND NO LONGER DO. Until 2026-09-15 an
# address or a telephone shipped only where the filing left one out, so 244 and
# 223 counted a residue; the scraper now keeps the directory's copy wherever the
# two publishers AGREE as well (a disagreement is still the filing's to win), so
# all five count the same thing — every matched library can have one.
#
# THAT ALSO MAKES THESE TWO FLOORS STEADIER RATHER THAN TIGHTER. The count is
# now driven by the directory alone: how many matched libraries publish an
# address this scraper can split. It no longer moves when Sunday's
# library-officials run changes how many filings carry an office block, which is
# what put the old measured values 120 apart from these.
MIN_LIBRARIES = 315
MIN_WITH_ADDRESS = 313
MIN_WITH_PHONE = 310
MIN_WITH_URL = 290
MIN_WITH_ADMIN = 245


def fail(msg):
    sys.exit("build-il-library-contacts: FAIL — " + msg)


def normalise_title(value):
    """Case, punctuation and spacing removed, for comparing a name to a title."""
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower())).strip()


def institution_not_person(name, library):
    """Why `name` is the LIBRARY rather than its administrator, or None.

    L2's Primary Administrator block is a free-text field the libraries fill in
    themselves, and on 2026-09-21 Atkinson's read `Name: Atkinson Public
    Library`, `Title: Director`, with `Ninette` nowhere on the page. The
    scraper reproduced it faithfully, which is the problem: shipped, the card
    would have named an institution as the person who runs it, and would have
    done so by REMOVING a real name — Atkinson has no `heads` entry in
    il-library-district-officials.json, so nothing else fills that slot.

    NEITHER EXISTING GUARD CAN SEE THIS. validate_officeholder_names.py judges
    a name by its SHAPE, and `Atkinson Public Library` is a perfectly well
    formed name. check_roster_retention.py measures coverage per source, and
    one administrator of 285 changing sits under every threshold it sets. The
    value is only wrong RELATIVE TO ITS OWN RECORD, which is why the test has
    to be made here, where both halves are in hand.

    THE RULE IS PREFIX-OR-SUFFIX, AND IT WAS MEASURED RATHER THAN REASONED.
    Against the 285 administrators shipped on 2026-09-21: equality alone does
    NOT catch Atkinson (the key carries a trailing `District` the name does
    not), while prefix-or-suffix catches it and flags ZERO shipped records.
    `contains` also flagged zero but is wider than the defect, so it is not
    used.

    TWO TOKENS MINIMUM, because a single one cannot be told from a surname
    that happens to match the town: Lisle Library District could appoint a
    director named Lisle, and refusing that would be this guard inventing a
    defect. The residual risk is the reverse — a library named after a person
    (this dataset has Rick Warren Memorial) appointing a director who shares
    the namesake. That is why the finding DROPS the administrator and ships
    the record rather than failing the build: the wrong direction costs one
    empty slot, is printed on the run that does it, and never puts a wrong
    name on a card.
    """
    person = normalise_title(name)
    title = normalise_title(library)
    if not person or not title or len(person.split()) < 2:
        return None
    if person == title:
        return "is the library's own name"
    if title.startswith(person) or title.endswith(person):
        return "is the library's own name with a word dropped"
    if person.startswith(title) or person.endswith(title):
        return "is the library's own name with a word added"
    return None


# Cases this guard must keep getting right, checked on every run. The first is
# the value L2 actually served; the rest are the false positives the rule was
# narrowed to avoid.
INSTITUTION_SELFTEST = (
    ("Atkinson Public Library", "Atkinson Public Library District", True),
    ("Atkinson Public Library District", "Atkinson Public Library District", True),
    ("Ninette Carton", "Atkinson Public Library District", False),
    ("Lisle", "Lisle Library District", False),          # one token: a surname
    ("Elaina Holland", "Rick Warren Memorial Library", False),
    ("Vanessa Robnett", "Tri-City Public Library District", False),
)


def _run_institution_selftest():
    for name, library, expected in INSTITUTION_SELFTEST:
        got = institution_not_person(name, library) is not None
        if got != expected:
            fail("institution_not_person(%r, %r) -> %s, expected %s"
                 % (name, library, got, expected))


def main():
    _run_institution_selftest()
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

    # Drop an administrator that is the library itself BEFORE the counts, so
    # with_admin measures what actually ships and its floor still means what it
    # says. Printed every run: a silent drop is how a source's defect becomes
    # this project's, and the count is the only thing a reviewer of a weekly
    # bot PR would otherwise see move.
    for key in sorted(libraries):
        admin = libraries[key].get("admin") or {}
        why = institution_not_person(admin.get("name"), key)
        if why:
            print("  dropped the administrator on %s: %r %s"
                  % (key, admin.get("name"), why), file=sys.stderr)
            libraries[key].pop("admin", None)

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
        prior, out, 'libraries', 1)
    for line in moved_lines:
        print(line)
    print("  %s" % moved_summary)
    emit_changes_output(moved_summary)

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-il-library-contacts: wrote %s — %d librar(ies), %d with an "
          "address, %d with a telephone, %d with a website, %d with an "
          "administrator"
          % (OUT_PATH, len(libraries), with_address, with_phone, with_url,
             with_admin))


if __name__ == "__main__":
    main()
