#!/usr/bin/env python3
"""Write il/data/app/grundy-district-officials.json from the scraper's output.

The pair to grundy_district_officials_scraper.py, which reads each fire, park
and library district's own Annual Financial Report filing from the Illinois
Comptroller. This half does the refusing: a run that lost coverage leaves the
shipped file alone rather than replacing it with a thinner one.

WHAT THE FLOORS GUARD, and why each is under its measured value. On 2026-09-10
20 of Grundy's 21 districts filed, with 30 board officers, 11 appointed
officers, 18 offices, 16 street addresses, 13 telephones and 10 e-mails. The
floors sit under those values because a district that stops filing is a real
event and must not freeze the other 19; they are not set AT the measured
figures, which would make one district's late filing indistinguishable from the
source breaking.

THE CONTACT FIGURES ARE WHAT THE FILINGS SUPPORT AND NO MORE. The AFR's contact
block has no unit-address field -- each of its four slots carries the address,
telephone and e-mail of the PERSON in that slot -- so comptroller_afr.py ships
a value only where the filing witnesses it as the district's. Grundy's twenty
support markedly more than Woodford's twenty-five did (16 addresses against 9),
which is a fact about these filings rather than a change of rule.

AN OFFICER'S OWN TELEPHONE SHIPS ON THAT OFFICER, since Adam's ruling of
2026-10-17 ("if the official government source uses personal phone numbers, we
publish those"). The paragraph above is about the DISTRICT's contact and still
governs it. comptroller_afr.py decides which number is an officer's own -- one a
slot prints beside that officer and nobody else -- and which is the district's.
MIN_OFFICER_PHONES refuses a run that stops reading them, and suspect_phones_in
refuses a value not shaped like a telephone number, naming the district and the
officer's place in its list and never the value.
A number that is a library district's own line in the library systems'
directory (il-library-contacts.json) is taken off its officer before
anything is counted: the card prints that line as the library's, so it
belongs to the library and not to the person.

AN OFFICER'S OWN E-MAIL ADDRESS SHIPS ON THAT OFFICER TOO, since Adam chose
"E-mails too" the same day: comptroller_afr.py's OFFICER E-MAIL section says
which address a filing gives one officer alone. MIN_OFFICER_EMAILS and
suspect_emails_in guard it as the two telephone checks guard the numbers. An
address the roster's filings give beside two different people is nobody's, and
so is one that another roster built from these filings gives beside a different
person; each is taken off before anything is counted (drop_mail_given_for_two).

THE 21ST DISTRICT IS MAZON FIRE AND IT IS NOT A LOSS TO BE FLOORED AGAINST.
Its unit exists and is verified every run; its Warehouse landing page carries
no fiscal year, so there is no report to read. MIN_DISTRICTS is set against the
20 that file, and Mazon ships automatically the run its filing appears.

THE FISCAL YEAR IS REQUIRED ON EVERY DISTRICT. An AFR is a snapshot filed for
one year and the Comptroller's own page says a different year may name a
different person, so a record without one cannot be rendered honestly and the
build refuses rather than shipping a name with no date attached.

A DISTRICT WITH NO BOARD OFFICER STILL SHIPS, and THREE of the 20 are in that
state: Coal City Library, Morris Area Library and Godley Park District each
file only appointed officers. That is the district's own answer about who it
publishes, not a parse failure. The card names them under Administration and
says nothing about a board, which is what the filing supports.
"""

import argparse
import json
import os
import sys

from comptroller_afr import (  # noqa: E402  (shared -- do not fork)
    count_officer_emails, count_officer_phones, drop_lines_from_officers,
    drop_mail_given_for_two, library_directory_lines, mail_elsewhere,
    MAIL_GIVEN_FOR_TWO, suspect_emails_in, suspect_names_in, suspect_phones_in)

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from scraper_common import substantive_changes, emit_changes_output  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app",
                        "grundy-district-officials.json")

# Measured 2026-09-10: 20 districts / 30 board / 11 appointed / 18 with an
# office / 13 with a telephone. Each floor sits under its measured value.
MIN_DISTRICTS = 16
MIN_BOARD = 24
MIN_WITH_OFFICE = 14
MIN_WITH_PHONE = 9
# Officers carrying their own telephone, since Adam's ruling of 2026-10-17
# ("if the official government source uses personal phone numbers, we publish
# those"). Measured 2026-10-17: 15 of 40, one with a second number. About two
# thirds of 15, so a change that stops the numbers being read fails the build
# instead of emptying them quietly.
MIN_OFFICER_PHONES = 10
# Officers carrying their own e-mail address, since Adam chose "E-mails too"
# on 2026-10-17. Measured 2026-10-17: 19 of 40, 13 of them on a domain that
# neither carries the district's name nor is a government's. About two thirds
# of 19, so a change that stops the addresses being read fails the build
# instead of emptying them quietly.
MIN_OFFICER_EMAILS = 13
# Grundy dispatches all three concepts. A kind that disappears entirely is a
# source change, not turnover.
EXPECT_KINDS = {"fire", "park", "library"}


def fail(msg):
    sys.exit("build-grundy-district-officials: FAIL — " + msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scraped", help="grundy_district_officials_scraper.py --out")
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file instead of writing")
    args = ap.parse_args()

    with open(args.scraped, encoding="utf-8") as fh:
        payload = json.load(fh)
    districts = payload.get("districts") or {}
    if not isinstance(districts, dict):
        fail("the scraper's output has no districts object")

    # A LIBRARY'S OWN LINE RIDES NOBODY. The card prints the library systems'
    # directory telephone as a library district's own line where its filing
    # gives none (withCountyLibraryPhone in il/index.html), and that line is the
    # library's whether or not the card prints it, so an officer's number that
    # is the same line is taken off before anything is counted. The join is the
    # comptroller code, as the card's is (comptroller_afr.library_directory_lines).
    try:
        _by_name, library_lines_by_code = library_directory_lines(
            os.path.dirname(OUT_PATH))
    except (OSError, ValueError) as exc:
        fail("cannot read the library directory's telephones: %s" % exc)
    library_lines = sum(
        drop_lines_from_officers(d, [library_lines_by_code.get(d.get("comptrollerCode"))])
        for d in districts.values() if isinstance(d, dict))
    print("  %d officer number(s) taken off as a library's own line" % library_lines)

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
    shared_mail = drop_mail_given_for_two(districts, elsewhere, mail_withheld)
    print("  %d officer address(es) taken off as given beside two people, "
          "in this roster's filings or another's" % shared_mail)

    board = sum(len(d.get("board") or []) for d in districts.values())
    heads = sum(len(d.get("heads") or []) for d in districts.values())
    with_office = sum(1 for d in districts.values() if (d.get("office") or {}))
    with_phone = sum(1 for d in districts.values()
                     if (d.get("office") or {}).get("phone"))
    officer_phones = count_officer_phones(districts)
    officer_emails = count_officer_emails(districts)
    kinds = {d.get("kind") for d in districts.values()}
    undated = sorted(k for k, d in districts.items() if not d.get("filedFor"))

    problems = []
    if len(districts) < MIN_DISTRICTS:
        problems.append("%d district(s) < floor %d" % (len(districts), MIN_DISTRICTS))
    if board < MIN_BOARD:
        problems.append("%d board officer(s) < floor %d" % (board, MIN_BOARD))
    if with_office < MIN_WITH_OFFICE:
        problems.append("%d district(s) with an office < floor %d"
                        % (with_office, MIN_WITH_OFFICE))
    if with_phone < MIN_WITH_PHONE:
        problems.append("%d district(s) with a telephone < floor %d"
                        % (with_phone, MIN_WITH_PHONE))
    if officer_phones["withPhone"] < MIN_OFFICER_PHONES:
        problems.append("%d officer(s) with their own telephone < floor %d"
                        % (officer_phones["withPhone"], MIN_OFFICER_PHONES))
    if officer_emails["withEmail"] < MIN_OFFICER_EMAILS:
        problems.append("%d officer(s) with their own e-mail address < floor %d"
                        % (officer_emails["withEmail"], MIN_OFFICER_EMAILS))
    missing_kinds = EXPECT_KINDS - kinds
    if missing_kinds:
        problems.append("no district of kind: %s"
                        % ", ".join(sorted(missing_kinds)))
    unexpected = kinds - EXPECT_KINDS
    if unexpected:
        problems.append("unexpected district kind: %s"
                        % ", ".join(sorted(str(k) for k in unexpected)))
    if undated:
        problems.append("no fiscal year on: %s" % ", ".join(undated))
    # A NAME THIS SOURCE FILED IN A SHAPE NOBODY TYPED IS REFUSED, NOT SHIPPED.
    # comptroller_afr.normalise_filed_name has already restored a middle
    # initial's comma to its period and printed that it did, so a comma left
    # over is unexplained. #1226: Walnut Public Library District's FY2026 filing
    # prints its Director as `Jaclyn G,` in two of three populated slots, and a
    # reader is better served by last week's correct spelling than this week's
    # broken one. A filed suffix comma (`, Jr.`) is admitted.
    for where, name, why in suspect_names_in(districts):
        problems.append("%s: %r has %s" % (where, name, why))
    # AN OFFICER'S TELEPHONE AND E-MAIL ADDRESS MUST EACH BE SHAPED LIKE ONE
    # (comptroller_afr.OFFICER_PHONE_SHAPE, OFFICER_EMAIL_SHAPE). The refusal
    # names the district and the officer's place in its list, never the value.
    for where, why in suspect_phones_in(districts) + suspect_emails_in(districts):
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
        "districts": districts,
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
        print("build-grundy-district-officials: OK — shipped file matches "
              "(%d district(s), %d board officer(s), %d officer(s) with their "
              "own telephone, %d with their own e-mail address)"
              % (len(districts), board, officer_phones["withPhone"],
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
        prior, out, 'districts', 1)
    for line in moved_lines:
        print(line)
    print("  %s" % moved_summary)
    emit_changes_output(moved_summary)

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("build-grundy-district-officials: wrote %s — %d district(s), %d "
          "board officer(s), %d appointed, %d with an office, %d officer(s) "
          "with their own telephone (%d with a second), %d with their own "
          "e-mail address, %d number(s) taken off as a library's own line"
          % (OUT_PATH, len(districts), board, heads, with_office,
             officer_phones["withPhone"], officer_phones["withSecond"],
             officer_emails["withEmail"], library_lines))


if __name__ == "__main__":
    main()
