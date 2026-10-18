#!/usr/bin/env python3
"""
Telephone gate: every telephone link a page serves dials one whole number, and
every telephone in the apps' data holds at most one.

WHY THIS EXISTS. Measured 2026-10-17, the day Adam ruled that an official's own
number ships wherever a government source prints it, three shipped surfaces
dialled something nobody can answer, with every gate green:

  * il/ward.html linked Ward 2's telephone, printed by the city as one number
    and two four-digit fragments after a slash, as a single 18-digit number;
  * Kankakee County's board page printed four members' telephones as "Coming
    Soon", each a link that dials nothing, and gave the same words to the
    page's structured data as a telephone;
  * seven Mason County municipal officials' entries in
    il/data/app/municipal-officials.json each held two numbers in one string,
    which the card dialled as one 20-digit number.

The builders hold a value's shape where they build it, and the shipped file can
predate that (Mason's did), while a page generator prints whatever a roster
carries. Nothing read what the pages and the data files actually ship, which is
this gate's subject.

WHAT IT CHECKS.
  * Every href="tel:..." on every served page dials seven, ten or eleven
    digits, or a + and eight to fifteen. The pages are the ones
    validate_instance_assets.py discovers, imported rather than listed again.
  * Every telephone in every instance's data/app (a string under a key ending
    in "phone", or a string in a phonesExtra list) carries a digit and holds at
    most one ten-digit number. A source that prints two numbers as one is
    split by its builder into phone and phonesExtra, so a card can dial each.
    Where a string still holds a number and something less than a number (a
    fragment, an extension), the card and the pages dial its first number
    (cardPhoneDial in engine/index.html/card-helpers.txt and
    build_county_pages.dial_digits, which that script's --check holds to each
    other) and print the rest as the source printed it.

WHAT IT DOES NOT CHECK. That a number is right, answered, or the person's: the
builders decide whose a number is. A number a card fetches live never reaches
this tree; the engine's dial rule is what covers those.

Usage:
    python3 scripts/validate_telephones.py
"""

import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_instance_assets import instances, surfaces  # noqa: E402

# An href ATTRIBUTE: never a script's `a.href = "tel:" + dial`, which every app
# carries and which names no number.
TEL_HREF_RE = re.compile(r"""(?<![\w.$])href\s*=\s*(["'])tel:([^"']*)\1""", re.I)
# One whole number: an area code, an exchange and a line, with an optional
# country code 1 in front, and no digit on either side.
NUMBER_RE = re.compile(r"(?<!\d)(?:\+?1[\s.\-]?)?(?:\(\d{3}\)|\d{3})[\s.\-/]*"
                       r"\d{3}[\s.\-]*\d{4}(?!\d)")


def link_problem(target):
    """None, or why a tel: link to `target` dials nothing a reader can call."""
    digits = re.sub(r"[^\d+]", "", target)
    if digits.startswith("+"):
        return None if 8 <= len(digits) - 1 <= 15 else "dials %d digits" % (len(digits) - 1)
    if len(digits) in (7, 10, 11):
        return None
    return "dials nothing" if not digits else "dials %d digits" % len(digits)


def value_problem(value):
    """None, or what is wrong with one telephone a data file carries."""
    if not re.search(r"\d", value):
        return "carries no digit"
    found = NUMBER_RE.findall(value)
    if len(found) > 1:
        return ("holds %d numbers in one string; split them into phone and "
                "phonesExtra" % len(found))
    return None


# Made-up values, each with whether it must be refused.
LINK_CASES = (("5550100", False), ("2175550100", False), ("12175550100", False),
              ("+442079460958", False), ("", True), ("217555010021755501", True),
              ("555", True))
VALUE_CASES = (("(217) 555-0100", False), ("cell 555-0106", False),
               ("1-800-555-0116", False), ("(312) 555-0111 / 0112/0113", False),
               ("217-555-0102 ext. 3203", False), ("Coming Soon", True),
               ("217/555-0109; 217/555-0110", True),
               ("1-800-555-0116 or 1-800-555-0117", True))


def selftest():
    out = []
    for target, refused in LINK_CASES:
        if bool(link_problem(target)) != refused:
            out.append("selftest: tel:%s is %s" % (target, "passed" if refused else "refused"))
    for value, refused in VALUE_CASES:
        if bool(value_problem(value)) != refused:
            out.append("selftest: %r is %s" % (value, "passed" if refused else "refused"))
    return out


def phone_values(node, path=""):
    """(path, value) for every telephone string in one data file."""
    if isinstance(node, dict):
        for key, value in node.items():
            here = "%s/%s" % (path, key)
            if isinstance(value, str) and key.lower().endswith("phone"):
                yield here, value
            elif key == "phonesExtra" and isinstance(value, list):
                for i, extra in enumerate(value):
                    if isinstance(extra, str):
                        yield "%s[%d]" % (here, i), extra
            else:
                yield from phone_values(value, here)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from phone_values(value, "%s[%d]" % (path, i))


def main():
    problems = selftest()
    links = values = 0
    for rel, full in surfaces():
        with open(full, encoding="utf-8") as fh:
            text = fh.read()
        for m in TEL_HREF_RE.finditer(text):
            links += 1
            why = link_problem(m.group(2))
            if why:
                line = text.count("\n", 0, m.start()) + 1
                # The line and what is wrong, never the number itself.
                problems.append("%s:%d: a telephone link %s" % (rel, line, why))
    for tag in instances():
        for full in sorted(glob.glob(os.path.join(REPO_ROOT, tag, "data", "app",
                                                  "**", "*.json"), recursive=True)):
            rel = os.path.relpath(full, REPO_ROOT)
            try:
                with open(full, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError) as exc:
                problems.append("%s: cannot be read (%s)" % (rel, exc))
                continue
            for path, value in phone_values(data):
                values += 1
                why = value_problem(value)
                if why:
                    problems.append("%s %s: the telephone %s" % (rel, path, why))
    if problems:
        for p in problems:
            print("FAIL: %s" % p)
        print("validate-telephones: %d problem(s)" % len(problems))
        return 1
    print("validate-telephones: OK — %d telephone link(s) on %d page(s) each dial "
          "one number; %d telephone(s) in the apps' data each hold at most one"
          % (links, len(surfaces()), values))
    return 0


if __name__ == "__main__":
    sys.exit(main())
