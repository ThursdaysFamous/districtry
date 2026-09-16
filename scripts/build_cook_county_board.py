#!/usr/bin/env python3
"""
Resolve scripts/cook_county_board_scraper.py's rows into
il/data/source/cook-county-board-members.json — 17 districts plus the
countywide Board President, keyed the way build_county_pages.py reads Illinois.

WHAT READS IT. scripts/build_county_pages.py, which had no Cook page at all
because the app fetches the county's GIS people table live and that generator
enumerates whatever the roster FILES carry. The card is unchanged and still
reads the service; this file is the same rows, written down weekly so a page
can carry them.

NOT data/app, for the reason the Chicago ward roster is not:
validate_index.py requires every file in an instance's data/app to be
referenced by its index.html, and this one is not.

THE FILTER IS THE CARD'S FILTER. Layer 26 answers 356 rows for
office='Commissioner' OR 'Board President', of which 355 are commissioners —
because every park, library and metropolitan tax district on the layer elects
commissioners too. The board's own seventeen are the rows whose RELATE_KEY is
CommissionerDistrict_N, which is exactly the join il/index.html makes.

THE GATE IS EXACT AND SO IS THE REASON. Cook seats seventeen commissioners, one
per district, fixed by the county's own apportionment ordinance. Sixteen means a
truncated query or a withdrawn row, eighteen means the layer's key scheme
changed, and both should stop the build rather than publish a board of the wrong
size. The President is required too: a seventeen-district board page with no
countywide chair understates the body.

    python3 build_cook_county_board.py cook_board.json [output_dir]
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "source")

DISTRICTS = 17
KEY_RE = re.compile(r"^commissionerdistrict_(\d+)$", re.I)

# Measured 2026-09-15 against the live layer: 17 of 17 carry a name, 14 an
# e-mail, 15 a County Building phone and 12 a district office. The floors sit
# under the measurement, not at it, so one member between offices does not fail
# the build while a column that empties does.
MIN_EMAILS = 12
MIN_PHONES = 12
MIN_OFFICES = 9

SOURCE_LABEL = "the county's own GIS people table"


def clean(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def full_name(row):
    parts = [clean(row.get("firstName")), clean(row.get("middleName")),
             clean(row.get("lastName")), clean(row.get("suffix"))]
    return " ".join(p for p in parts if p) or None


def office_line(row, n):
    street = clean(row.get("addressStreet_%d" % n))
    if not street:
        return None
    suite = clean(row.get("addressSuite_%d" % n))
    city = clean(row.get("city%d" % n))
    state = clean(row.get("state%d" % n))
    zipcode = clean(row.get("zip%d" % n))
    head = ", ".join(p for p in (street, suite) if p)
    tail = " ".join(p for p in (city, state, zipcode) if p)
    return ("%s, %s" % (head, tail)) if tail else head


def phone(value):
    """(312) 603-6391 from 3126036391, and anything else exactly as published."""
    digits = re.sub(r"\D", "", clean(value) or "")
    if len(digits) == 10:
        return "(%s) %s-%s" % (digits[:3], digits[3:6], digits[6:])
    return clean(value)


# THE BARE COUNTY DOMAIN IS NOT A MEMBER'S WEBSITE. Sixteen of the seventeen
# rows put "cookcountyil.gov" in url1, which is the county's front page and
# identifies nobody; on a card it reads as "this commissioner's site". A link
# that names a person is carried and a link that names the county is dropped.
GENERIC_HOSTS = {"cookcountyil.gov", "www.cookcountyil.gov"}


def website(value):
    url = clean(value)
    if not url:
        return None
    bare = re.sub(r"^https?://", "", url).rstrip("/")
    if bare.lower() in GENERIC_HOSTS:
        return None
    return url if url.startswith(("http://", "https://")) else "https://" + url


def resolve(raw):
    rows = raw.get("rows") or []
    districts, president = {}, None
    for row in rows:
        office = clean(row.get("office"))
        if office == "Board President" and clean(row.get("jurisdiction")) == "Cook County":
            president = row
            continue
        m = KEY_RE.match(clean(row.get("RELATE_KEY")) or "")
        if not m:
            continue
        districts[str(int(m.group(1)))] = row
    return districts, president


def member(row, role=None):
    rec = {"name": full_name(row)}
    # THE SECOND OFFICE, NOT THE FIRST. Measured 2026-09-15 across the seventeen
    # rows, addressStreet_1 is "118 N. Clark St., Room 567" on FOURTEEN of them:
    # it is the board's own suite in the County Building, repeated per row, and
    # a shared address printed as each member's office says nothing about any of
    # them. addressStreet_2 is the district office and is genuinely per-member —
    # thirteen distinct values, twelve of them populated — so that is what a
    # member's record carries, and the shared one rides the board extra below.
    office = office_line(row, 2)
    if office:
        rec["office"] = office
    if role:
        rec["role"] = role
    email = clean(row.get("email1"))
    if email:
        rec["email"] = email
    tel = phone(row.get("phone1"))
    if tel:
        rec["phone"] = tel
    site = website(row.get("url1"))
    if site:
        rec["url"] = site
    return rec


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: %s <raw-scraper-output.json> [output_dir]" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)
    raw_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_OUT_DIR

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)
    districts, president = resolve(raw)

    if len(districts) != DISTRICTS:
        print("build-cook-county-board: FAIL — resolved %d district(s) and Cook "
              "seats exactly %d; refusing to overwrite the roster"
              % (len(districts), DISTRICTS), file=sys.stderr)
        sys.exit(1)
    if president is None:
        print("build-cook-county-board: FAIL — no Board President row; a "
              "seventeen-district page with no countywide chair understates the "
              "board", file=sys.stderr)
        sys.exit(1)

    out = {}
    for key in sorted(districts, key=int):
        rec = member(districts[key])
        if not rec["name"]:
            print("build-cook-county-board: FAIL — district %s has no name" % key,
                  file=sys.stderr)
            sys.exit(1)
        rec["sourceUrl"] = raw.get("source_url")
        out[key] = {"members": [rec]}
    chair = member(president, role="Board President")
    if not chair["name"]:
        print("build-cook-county-board: FAIL — the Board President row has no name",
              file=sys.stderr)
        sys.exit(1)
    chair["sourceUrl"] = raw.get("source_url")
    out["chair"] = chair

    counts = {}
    for field in ("email", "phone"):
        counts[field] = sum(1 for k in out if k != "chair"
                            and out[k]["members"][0].get(field))
    counts["office"] = sum(1 for key in sorted(districts, key=int)
                           if office_line(districts[key], 2))
    for field, floor in (("email", MIN_EMAILS), ("phone", MIN_PHONES),
                         ("office", MIN_OFFICES)):
        if counts[field] < floor:
            print("build-cook-county-board: FAIL — only %d of %d district(s) carry "
                  "a %s, floor %d; the layer's column likely changed"
                  % (counts[field], DISTRICTS, field, floor), file=sys.stderr)
            sys.exit(1)

    # The board's own office, carried as the per-county EXTRA build_county_pages
    # already reads in eleven other Illinois files. It is the first office the
    # County Building rows all share, taken from District 1's row rather than
    # typed here.
    # WITHOUT THE SUITE. Every district's first office is a room in the County
    # Building, and a room number is that member's, not the board's.
    first = dict(districts["1"])
    first["addressSuite_1"] = None
    first["addressStreet_1"] = re.sub(r",\s*(Room|Suite|Ste\.?)\s*\S+$", "",
                                      clean(first.get("addressStreet_1")) or "")
    board_office = office_line(first, 1)
    if board_office:
        out["board"] = {"office": board_office, "sourceUrl": raw.get("source_url")}

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cook-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("build-cook-county-board: wrote %s — %d districts, %d e-mail(s), "
          "%d phone(s), %d district office(s), plus the Board President (%s)"
          % (out_path, DISTRICTS, counts["email"], counts["phone"],
             counts["office"], chair["name"]), file=sys.stderr)


if __name__ == "__main__":
    main()
