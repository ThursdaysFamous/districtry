#!/usr/bin/env python3
"""Build mi/data/app/mi-battle-creek-commission-members.json — Battle Creek's
City Commission, read by the Battle Creek entry of mi/index.html's `city-ward`
card.

NINE SEATS, FIVE OF THEM WARDS, AND THE CARD SHOWS BOTH
---------------------------------------------------------
The city states its own arithmetic on its commission page: "made up of nine
elected officials… Five ward commissioners representing geographic districts…
Three at-large commissioners serving the entire city… The Mayor, elected
citywide." Five ride the polygons; the other four ride a `citywide` block,
because a ward card naming one of nine would read as the whole of a reader's
city representation. That is the Grand Rapids shape, second use.

THIS ROSTER EXISTS BECAUSE A 403 WAS MISREAD. The change that shipped Battle
Creek's wards recorded, in four places, that "the city's commission page
answers HTTP 403 to this client". It does not. The page whose id was GUESSED
answers 403; the real one, /380/City-Commission, answers 200. The wards shipped
nameless on the strength of that mistake, so the correction ships the names.

WHAT SHIPS PER MEMBER, AND WHAT DOES NOT
------------------------------------------
Name, seat, a direct phone and the city's own directory link for that person.
NOT an e-mail: every card's contact slot links the SAME city contact form, so
there is no per-member address to ship. That form is the body's, not anyone's,
and is hoisted beside City Hall's address exactly as Grand Rapids's switchboard
is — this refuses to write if it ever reappears on a member row.

AND NOT THE WARD LAYER'S OWN NAMES. `Wards_BC` carries a COMMISSIONER per ward,
four of whose five records were last edited in March 2023; those names are
still not read, and the builder that ships the geometry still refuses them.
Geometry from whatever proves the lines, people from whatever the city
maintains as people — and here the two sources happen to agree on all five
ward names, which is a corroboration and not the reason either is trusted.

    python3 mi/scripts/mi_battle_creek_commission_scraper.py   # refresh the cache
    python3 mi/scripts/build_mi_battle_creek_commission.py
    python3 mi/scripts/build_mi_battle_creek_commission.py --check
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(HERE)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT = os.path.join(APP_DATA_DIR, "mi-battle-creek-commission-members.json")
CACHE = os.path.join(HERE, ".cache", "mi_battle_creek_commission.json")

EXPECT_WARDS = ["1", "2", "3", "4", "5"]
COMMISSIONERS_PER_WARD = 1
EXPECT_SEATS = 9
SITE = "https://www.battlecreekmi.gov"
# The city has published all nine since this was written; the floor allows a
# single seat to fall vacant without failing the refresh, and no more.
MIN_NAMED = EXPECT_SEATS - 1


def fail(msg):
    print("battle-creek-commission: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def shape(cache):
    wards = {w: [] for w in EXPECT_WARDS}
    citywide = []
    for m in cache["members"]:
        row = {"name": m["name"], "seat": m["role"]}
        if m.get("profileUrl"):
            row["profileUrl"] = m["profileUrl"]
        if m.get("phone"):
            row["phone"] = m["phone"]
        if m.get("contactUrl"):
            row["contactUrl"] = m["contactUrl"]
        if m.get("ward"):
            if m["ward"] not in wards:
                fail("member %s carries ward %r, which is not one of %s"
                     % (m["name"], m["ward"], EXPECT_WARDS))
            wards[m["ward"]].append(row)
        else:
            citywide.append(row)
    for w in wards:
        wards[w].sort(key=lambda r: r["name"])
    doc = {
        "citywide": sorted(citywide, key=lambda r: r["name"]),
        "seats": cache.get("seats", EXPECT_SEATS),
        # Shipped so the card never hardcodes the city's own arithmetic: how
        # many commissioners a ward elects is a civic fact and belongs in the
        # data, beside the members it is used to count.
        "seatsPerWard": COMMISSIONERS_PER_WARD,
        "sourceUrl": cache["sourceUrl"],
        "wards": wards,
    }
    office = dict(cache.get("office") or {})
    if cache.get("contactUrl"):
        office["contactUrl"] = cache["contactUrl"]
    if office:
        office.setdefault("label", "City Hall")
        doc["office"] = office
    return doc


def validate(doc):
    if sorted(doc["wards"], key=int) != EXPECT_WARDS:
        fail("wards are %s, expected %s" % (sorted(doc["wards"], key=int), EXPECT_WARDS))
    if doc["seats"] != EXPECT_SEATS:
        fail("seats is %r, but the city's own composition sentence gives %d"
             % (doc["seats"], EXPECT_SEATS))
    named = len(doc["citywide"]) + sum(len(v) for v in doc["wards"].values())
    if named > doc["seats"]:
        fail("%d people named for %d seats" % (named, doc["seats"]))
    if named < MIN_NAMED:
        fail("only %d of %d seats named (floor %d) — the city's commission page has "
             "probably been rebuilt into a shape this parser no longer reads"
             % (named, doc["seats"], MIN_NAMED))
    if doc.get("seatsPerWard") != COMMISSIONERS_PER_WARD:
        fail("seatsPerWard is %r, but the city elects %d commissioner per ward"
             % (doc.get("seatsPerWard"), COMMISSIONERS_PER_WARD))
    for w, rows in doc["wards"].items():
        if len(rows) > COMMISSIONERS_PER_WARD:
            fail("ward %s has %d commissioners, more than the %d the city elects"
                 % (w, len(rows), COMMISSIONERS_PER_WARD))

    # THE MAYOR IS A CITYWIDE SEAT AND MUST BE ONE OF THEM. A parse that dropped
    # him into a ward, or lost him entirely, would leave the card naming eight
    # of nine with nothing saying which one is missing.
    mayors = [r for r in doc["citywide"]
              if re.search(r"\bmayor\b", r["seat"], re.I)
              and not re.search(r"\bvice\b", r["seat"], re.I)]
    if len(mayors) != 1:
        fail("%d citywide seats name a mayor, expected exactly one: %s"
             % (len(mayors), [r["seat"] for r in doc["citywide"]]))
    for r in doc["citywide"]:
        if re.search(r"\bward\b", r["seat"], re.I):
            fail("%s is filed citywide but its seat names a ward: %r"
                 % (r["name"], r["seat"]))
    for w, rows in doc["wards"].items():
        for r in rows:
            if not re.search(r"\bward\s*%s\b" % re.escape(w), r["seat"], re.I):
                fail("%s is filed under ward %s but its seat reads %r"
                     % (r["name"], w, r["seat"]))

    everyone = doc["citywide"] + [r for rows in doc["wards"].values() for r in rows]
    office = doc.get("office") or {}
    for r in everyone:
        if not r["name"].strip():
            fail("a member row carries no name")
        for key in ("profileUrl", "contactUrl"):
            if r.get(key) and not r[key].startswith(SITE):
                fail("%s links off-site: %s" % (r["name"], r[key]))
        if office.get("phone") and r.get("phone") == office["phone"]:
            fail("%s carries the city switchboard as a direct line — it is the BODY's "
                 "number and is hoisted, never repeated per member" % r["name"])
        if office.get("contactUrl") and r.get("contactUrl") == office["contactUrl"]:
            fail("%s carries the city's shared contact form as a personal address — "
                 "one form for nine people belongs to the body" % r["name"])
    names = [r["name"] for r in everyone]
    if len(set(names)) != len(names):
        fail("one person holds two seats")
    if not doc["sourceUrl"].startswith(SITE):
        fail("the roster cites %s, which is not the city's own site" % doc["sourceUrl"])


def _named(doc):
    return len(doc["citywide"]) + sum(len(v) for v in doc["wards"].values())


def check():
    if not os.path.exists(OUT):
        fail("%s is missing" % OUT)
    with open(OUT, encoding="utf-8") as fh:
        doc = json.load(fh)
    validate(doc)
    print("battle-creek-commission: OK — %d of %d seats named (%s; %d citywide), source %s"
          % (_named(doc), doc["seats"],
             ", ".join("ward %s: %d" % (w, len(doc["wards"][w])) for w in EXPECT_WARDS),
             len(doc["citywide"]), doc["sourceUrl"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    if args.check:
        return check()

    if not os.path.exists(CACHE):
        fail("no scraper cache — run mi/scripts/mi_battle_creek_commission_scraper.py first")
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
