#!/usr/bin/env python3
"""
One telephone number and nothing else: the shape check every Wisconsin
builder that ships an official's own phone runs before it writes.

WHY A SHAPE CHECK RATHER THAN A REFUSAL. Until 2026-10-17 several readers in
this instance dropped a number printed beside a supervisor, a councilmember or
a clerk because it might be that person's own home or cell line. Adam ruled
that day, for every state: "if the official government source uses personal
phone numbers, we publish those." So those numbers ship now, with the label
the source prints beside them ("cell 608-555-0100"), the first in `phone` and
any further ones in `phonesExtra`.

What must still never reach a phone field is anything else the same cell
holds. Several of these sources print a supervisor's house, town and ZIP code
in the same table cell as the number, and an e-mail address on the next line,
so the risk this check exists for is a READER that takes too much: a street
address, a ZIP code, an e-mail address or two numbers run together, written
into a field the card prints as a telephone number. That is a question about
the value's shape, and this module answers it.

A value passes when it is ONE telephone number, optionally led by one label
word (cell, home, work, business, office, mobile, personal, residence) and
optionally followed by an extension ("ext. 12", "x12", or the Elections
Commission's "EXT 12" and its one bare "EXT"). A number printed with no area
code passes as printed: nothing here adds one, because a mobile number can be
issued anywhere and a guessed area code reaches a stranger.

THE CALLER REPORTS A FAILURE BY COUNTY OR MUNICIPALITY AND SEAT ONLY. An error
message that quoted the value would print the very thing this check keeps out
of the data into a run log instead.

    python3 wi/scripts/wi_phone_shape.py --selftest
"""

import re
import sys

# Rule 2 of the 2026-10-17 change, and the three words some sources use for
# the same thing. A label the source does not print is never added.
LABELS = ("cell", "home", "work", "business", "office", "mobile", "personal",
          "residence")

_AREA = r"(?:\+?1[\s.-]?)?(?:\(\s*\d{3}\s*\)\s*|\d{3}[\s.-]?)"
_LOCAL = r"\d{3}[\s.-]?\d{4}"
_EXT = r"(?:\s*,?\s*(?:ext\.?|extension|x\.?)\s*\d{1,6}|\s+ext\.?)"
SHAPE = re.compile(r"(?i)^(?:(?:%s)\.?:?\s+)?(?:%s)?%s%s?$"
                   % ("|".join(LABELS), _AREA, _LOCAL, _EXT))
# Each number a value holds, counted by its seven-digit core. Two of them in
# one value is two people's numbers or two lines run together.
NUMBER = re.compile(r"(?:%s)?%s" % (_AREA, _LOCAL))
EXTENSION = re.compile(r"(?i)%s\s*$" % _EXT)
# Words that only an address carries. Wisconsin's rural grid numbers
# ("N786", "W123N4567") are addresses too and are checked separately.
STREET = re.compile(
    r"(?i)\b(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|blvd|boulevard|"
    r"ct|court|cir|circle|hwy|highway|way|pl|place|ter|terrace|trl|trail|"
    r"pkwy|parkway|cty|cth|county\s+road|box|p\.?\s?o\.?|suite|ste|apt|unit|"
    r"lot|route|rte)\b")
GRID_NUMBER = re.compile(r"(?i)\b[nsew]\d{3,}")
ZIP = re.compile(r"(?<![\d-])\d{5}(?:-\d{4})?(?![\d-])")


def problem(value):
    """None when `value` is one telephone number, else what is wrong with it.

    The reason never repeats the value, so a caller can print it whole."""
    if not isinstance(value, str) or not value.strip():
        return "is empty or not text"
    text = value.strip()
    if "@" in text:
        return "carries an @"
    if STREET.search(text) or GRID_NUMBER.search(text):
        return "carries a street word"
    if ZIP.search(EXTENSION.sub("", text)):
        return "carries a ZIP code"
    if len(NUMBER.findall(text)) > 1:
        return "carries more than one number"
    if not SHAPE.match(text):
        return "is not one telephone number"
    return None


def problems(record, where):
    """Every shape problem on one record's `phone` and `phonesExtra`, each
    named by `where` (a county and seat, or a municipality) and never by value.
    """
    out = []
    if record.get("phone") is not None:
        why = problem(record["phone"])
        if why:
            out.append("%s: phone %s" % (where, why))
    extra = record.get("phonesExtra")
    if extra is not None:
        if not isinstance(extra, list) or not extra:
            out.append("%s: phonesExtra is not a non-empty list" % where)
        else:
            for n, value in enumerate(extra, 1):
                why = problem(value)
                if why:
                    out.append("%s: phonesExtra entry %d %s" % (where, n, why))
    return out


def _selftest():
    passes = [
        "608-555-0100", "(608) 555-0100", "608 555 0100", "1-608-555-0100",
        "6085550100", "555-0100", "cell 608-555-0100", "home (608) 555-0100",
        "Cell: 608-555-0100", "work 608-555-0100 ext. 12", "608-555-0100 x12",
        "608-555-0100 EXT 1234", "(608)555-0100 EXT", "office 608.555.0100",
        "mobile 608-555-0100", "personal 608-555-0100", "residence 555-0100",
    ]
    fails = {
        "608-555-0100 jane@example.org": "carries an @",
        "123 Main St 608-555-0100": "carries a street word",
        "N786 608-555-0100": "carries a street word",
        "Dalton 53926 608-555-0100": "carries a ZIP code",
        "608-555-0100 608-555-0199": "carries more than one number",
        "608-555-": "is not one telephone number",
        "608-555- EXT 1234": "is not one telephone number",
        "Confidential": "is not one telephone number",
        "fax 608-555-0100": "is not one telephone number",
        "": "is empty or not text",
    }
    bad = [v for v in passes if problem(v)]
    bad += ["%r -> %r, wanted %r" % (v, problem(v), want)
            for v, want in fails.items() if problem(v) != want]
    rec = {"phone": "608-555-0100", "phonesExtra": ["cell 608-555-0199"]}
    if problems(rec, "Test County district 1"):
        bad.append("a clean record reported a problem")
    got = problems({"phone": "608-555-0100", "phonesExtra": ["1 Main St"]},
                   "Test County district 2")
    if got != ["Test County district 2: phonesExtra entry 1 carries a street word"]:
        bad.append("problems() reported %r" % got)
    if any("Main" in g for g in got):
        bad.append("a reported problem repeated the value")
    if bad:
        for b in bad:
            print("wi_phone_shape selftest: FAIL %s" % b, file=sys.stderr)
        sys.exit(1)
    print("wi_phone_shape selftest: OK (%d pass, %d refused, 2 record checks)"
          % (len(passes), len(fails)))


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        _selftest()
    else:
        print(__doc__.strip())
