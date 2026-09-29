#!/usr/bin/env python3
"""Build mi/data/app/mi-jackson-council-members.json — Jackson's Mayor and six
ward councilmembers, read by the Jackson entry of mi/index.html's `city-ward`
card.

SEVEN SEATS, SIX OF THEM WARDS. The city's council page lists the Mayor and one
councilmember per ward, and nothing more, so the six ride the ward polygons and
the Mayor rides a `citywide` block: a ward card naming one member would
otherwise read as the whole of a reader's city representation. That is the
Battle Creek shape, third use.

WHAT SHIPS PER MEMBER: name, the seat as the city words it, a phone number, an
e-mail address and that member's own page on the city's site. Every one of
those is printed in the member's contact block on that page. Three of the six
ward e-mail addresses are personal accounts (Hotmail, Yahoo, Gmail); they ship
because the city publishes them as the councilmember's contact, and a card
that quietly swapped them for the switchboard would say less than the city
does.

WHAT DOES NOT: a street address per member. Two ward pages print one and
nothing says whether it is an office or a home, so none ships. City Hall's
address and switchboard, which the city prints as its own, ride `office`.

    python3 mi/scripts/mi_jackson_council_scraper.py   # refresh the cache
    python3 mi/scripts/build_mi_jackson_council.py
    python3 mi/scripts/build_mi_jackson_council.py --check
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(HERE)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT = os.path.join(APP_DATA_DIR, "mi-jackson-council-members.json")
CACHE = os.path.join(HERE, ".cache", "mi_jackson_council.json")

EXPECT_WARDS = ["1", "2", "3", "4", "5", "6"]
MEMBERS_PER_WARD = 1
EXPECT_SEATS = 7
SITE = "https://www.cityofjackson.org"
# The city named all seven when this was written; the floor allows one seat to
# fall vacant without failing the weekly refresh, and no more.
MIN_NAMED = EXPECT_SEATS - 1
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")


def fail(msg):
    print("jackson-council: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def shape(cache):
    wards = {w: [] for w in EXPECT_WARDS}
    citywide = []
    for m in cache["members"]:
        row = {"name": m["name"], "seat": m["seat"]}
        for key in ("phone", "email", "profileUrl"):
            if m.get(key):
                row[key] = m[key]
        if m.get("ward"):
            if m["ward"] not in wards:
                fail("member %s carries ward %r, which is not one of %s"
                     % (m["name"], m["ward"], EXPECT_WARDS))
            wards[m["ward"]].append(row)
        else:
            citywide.append(row)
    for w in wards:
        wards[w].sort(key=lambda r: r["name"])
    return {
        "citywide": sorted(citywide, key=lambda r: r["name"]),
        "office": dict(cache["office"]),
        "seats": cache.get("seats", EXPECT_SEATS),
        # How many members a ward elects is a civic fact and belongs in the
        # data beside the members it counts, so the card never hardcodes it.
        "seatsPerWard": MEMBERS_PER_WARD,
        "sourceUrl": cache["sourceUrl"],
        "wards": wards,
    }


def _named(doc):
    return len(doc["citywide"]) + sum(len(v) for v in doc["wards"].values())


def validate(doc):
    if sorted(doc["wards"], key=int) != EXPECT_WARDS:
        fail("wards are %s, expected %s" % (sorted(doc["wards"], key=int), EXPECT_WARDS))
    if doc["seats"] != EXPECT_SEATS:
        fail("seats is %r; the city's council page lists the Mayor and six ward "
             "councilmembers, %d" % (doc["seats"], EXPECT_SEATS))
    named = _named(doc)
    if named > doc["seats"]:
        fail("%d people named for %d seats" % (named, doc["seats"]))
    if named < MIN_NAMED:
        fail("only %d of %d seats named (floor %d) — the city's pages have probably "
             "been rebuilt into a shape the scraper no longer reads"
             % (named, doc["seats"], MIN_NAMED))
    if doc.get("seatsPerWard") != MEMBERS_PER_WARD:
        fail("seatsPerWard is %r, but the city elects %d councilmember per ward"
             % (doc.get("seatsPerWard"), MEMBERS_PER_WARD))
    for w, rows in doc["wards"].items():
        if len(rows) > MEMBERS_PER_WARD:
            fail("ward %s has %d members, more than the %d the city elects"
                 % (w, len(rows), MEMBERS_PER_WARD))
        for r in rows:
            if not re.search(r"\bWard\s*%s\b" % re.escape(w), r["seat"]):
                fail("%s is filed under ward %s but the seat reads %r"
                     % (r["name"], w, r["seat"]))

    mayors = [r for r in doc["citywide"] if r["seat"] == "Mayor"]
    if len(mayors) != 1 or len(doc["citywide"]) != 1:
        fail("the citywide block must hold exactly the Mayor: %s"
             % [r["seat"] for r in doc["citywide"]])

    office = doc["office"]
    if not office.get("lines") or not PHONE_RE.match(office.get("phone") or ""):
        fail("the City Hall block is missing its address or switchboard: %r" % office)
    everyone = doc["citywide"] + [r for rows in doc["wards"].values() for r in rows]
    for r in everyone:
        if not r["name"].strip():
            fail("a member row carries no name")
        if r.get("profileUrl") and not r["profileUrl"].startswith(SITE + "/"):
            fail("%s's page link is off the city's site: %s" % (r["name"], r["profileUrl"]))
        if r.get("email") and not EMAIL_RE.match(r["email"]):
            fail("%s's e-mail is not an address: %r" % (r["name"], r["email"]))
        if r.get("phone") and not PHONE_RE.match(r["phone"]):
            fail("%s's phone is not a ten-digit number: %r" % (r["name"], r["phone"]))
        if r.get("phone") and r["phone"] == office["phone"]:
            fail("%s carries the City Hall switchboard as a direct line" % r["name"])
        for banned in ("address", "lines", "street"):
            if banned in r:
                fail("%s carries a %r field; no per-member address ships" % (r["name"], banned))
    names = [r["name"] for r in everyone]
    if len(set(names)) != len(names):
        fail("one person holds two seats")
    if not doc["sourceUrl"].startswith(SITE + "/"):
        fail("the roster cites %s, which is not the city's own site" % doc["sourceUrl"])


def check():
    if not os.path.exists(OUT):
        fail("%s is missing" % OUT)
    with open(OUT, encoding="utf-8") as fh:
        doc = json.load(fh)
    validate(doc)
    print("jackson-council: OK — %d of %d seats named, source %s"
          % (_named(doc), doc["seats"], doc["sourceUrl"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    if args.check:
        return check()
    if not os.path.exists(CACHE):
        fail("no scraper cache — run mi/scripts/mi_jackson_council_scraper.py first")
    with open(CACHE, encoding="utf-8") as fh:
        cache = json.load(fh)
    doc = shape(cache)
    validate(doc)
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("Wrote %s — %d of %d seats named" % (OUT, _named(doc), doc["seats"]))


if __name__ == "__main__":
    main()
