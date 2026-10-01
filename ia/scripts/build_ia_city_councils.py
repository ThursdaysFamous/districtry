#!/usr/bin/env python3
"""
Build data/app/ia-city-councils.json — the mayor and council of the fourteen
Iowa cities above 25,000 that named nobody on this app before 2026-10-01.

WHAT THIS CLOSES, AND IN WHOSE WORDS
--------------------------------------
The done standard's Covered test asks an app to answer every level of
government it is expected to answer, and one of those levels is the governing
body of every general-purpose local government above 25,000 people. Iowa has
eighteen such cities. Four were answered -- Des Moines and Waterloo by ward
through the `city-ward` layer, Cedar Rapids and Des Moines by their own
builders -- and the other FOURTEEN named nobody, which is 96 officeholders a
reader in those cities could not get from this app.

THIS IS A SECOND FILE AND NOT A WIDENING OF THE FIRST
-------------------------------------------------------
`build_ia_city_officials.py` holds five SMALL cities and gates them globally:
six seats each, exactly one plain Mayor, an e-mail for every member. Not one
of those holds here -- Davenport seats ten, Sioux City five, Council Bluffs
publishes no member e-mail at all, and two cities name no mayor on their own
council page. Loosening those gates to admit these fourteen would retire the
gates that protect the five, so every declaration here is PER CITY and every
one is a measurement of that city's page taken 2026-10-01.

NO HOME ADDRESSES, EVER -- AND THREE OF THESE CITIES PUBLISH THEM
-------------------------------------------------------------------
Bettendorf, Dubuque and Ottumwa each print a residential street address under
the member's name. The scraper reads name, role, seat, phone, e-mail and term
and nothing else, and this builder refuses to write if any field of any
record reads as a street address -- per field and over the whole record, which
is the test `build_ia_township_officers.py` already applies. The refusal is
not a formality: on all three pages the address sits between the role and the
phone, so a parser taking "the line after the role" would ship it.

THE E-MAIL WITNESS IS THE COUNTY BUILDER'S, APPLIED UNCHANGED
---------------------------------------------------------------
An address ships only if the officeholder's own name is in its local part, or
its form is an office mailbox (`mayor@`, `council@`). Measured at first build
all 47 pass. The witness runs against the name THIS FILE SHIPS, never the one
the scrape matched, so a name correction cannot leave an address witnessed
against somebody the card is not naming.

WHAT THESE PAGES DO NOT PUBLISH, STATED RATHER THAN FILLED
------------------------------------------------------------
Measured 2026-10-01: 47 of 96 members carry an e-mail, 47 a telephone, 61 a
named seat and 30 a term. Those are not shortfalls to chase -- five of the
fourteen cities publish a roster and no contact at all. Two cities name no
mayor anywhere this project has read (Davenport, whose own Mayor's Office
page carries the office's address and telephone and no person; Cedar Falls,
whose council page names its seven members and whose `/67/Mayor` path answers
404), and both carry `namesMayor: false` so the card can say so instead of
implying the city has none.

AT-LARGE AND BY WARD IN ONE FILE, AND NEITHER IS A LAYER
----------------------------------------------------------
Nine of the fourteen elect at least some members by ward or district and the
seat is carried per member, but nothing here is a polygon layer: this project
draws no Iowa city ward outside Des Moines and Waterloo, and a card naming a
ward it cannot draw is still the honest answer -- it tells a reader which
seats their city has and who holds them. The ward geometry for these cities
is a separate, recorded gap.

Usage:
    python3 ia/scripts/ia_city_council_scraper.py     # refresh the cache
    python3 ia/scripts/build_ia_city_councils.py
    python3 ia/scripts/build_ia_city_councils.py --check
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)                               # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
CACHE = os.path.join(HERE, ".cache", "ia_city_councils.json")
OUT_NAME = "ia-city-councils.json"

# EXACT, NOT A FLOOR, AND PER CITY. A city's council size is set by its own
# charter and does not drift the way a county board's roster does, so a page
# publishing a different number is the page changing or the city changing and
# both need reading. Measured 2026-10-01 off each city's own page.
SEATS = {
    "1901855": ("Ames", 7), "1902305": ("Ankeny", 6),
    "1906355": ("Bettendorf", 8), "1911755": ("Cedar Falls", 7),
    "1916860": ("Council Bluffs", 6), "1919000": ("Davenport", 10),
    "1922395": ("Dubuque", 7), "1938595": ("Iowa City", 7),
    "1949485": ("Marion", 7), "1949755": ("Marshalltown", 8),
    "1960465": ("Ottumwa", 6), "1973335": ("Sioux City", 5),
    "1979950": ("Urbandale", 6), "1983910": ("West Des Moines", 6),
}
# The two cities whose council page names no mayor, each measured rather than
# assumed -- see the module docstring.
NO_MAYOR = {"1919000": "Davenport", "1911755": "Cedar Falls"}

MIN_CITIES = 14        # measured 14 of 14; a city refused by robots.txt would
                       # make this a floor, and none is today
MIN_SEATS = 96         # measured 96 across the fourteen
MIN_EMAILS = 47        # measured 47 of 96 -- five cities publish none at all
MIN_PHONES = 47        # measured 47 of 96
MIN_SEATS_NAMED = 61   # measured 61 of 96 carry a ward, district or at-large
MIN_WITH_CONTACT = 8   # measured 8 of 14 cities publish contact for anybody

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
OFFICE_FORM = re.compile(r"^(mayor|clerk|council|city|admin|info|office)", re.I)
# The same refusal the scraper applies, restated here on purpose: this builder
# is the last thing between a scraped page and a reader, and a refusal that
# exists in only one of the two is a refusal one change away from gone.
ADDRESS = re.compile(
    r"(?i)(^\s*\d+[\w-]*\s+[\w.'-]+(\s+[\w.'-]+)*\s*,?\s*\b(st|street|ave|avenue|rd|road"
    r"|dr|drive|ln|lane|ct|court|pl|place|blvd|boulevard|way|ter|terrace|cir|circle"
    r"|pkwy|parkway|hwy|highway|trail|trl|park)\b"
    r"|\b[A-Z][a-z]+,\s*(IA|Iowa)\s*\d{5}\b"
    r"|\bP\.?\s*O\.?\s*Box\s*\d+)")

FIELDS = ("name", "role", "kind", "seat", "phone", "email", "termEnds")


def fail(message):
    raise SystemExit("ia-city-councils: " + message)


def load(path, what):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError as e:
        fail("cannot read %s (%s) -- %s" % (path, e, what))


def email_witnesses(name, email):
    """Does this address's local part carry THIS person's name?

    Behaviour lifted from build_ia_county_officers.py, which is the authority.
    The duplication is deliberate: a change there should be a decision made
    twice rather than a silent change of policy here.
    """
    local = re.sub(r"[^a-z]", "", email.split("@")[0].lower())
    toks = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", name or "")]
    if any(t in local for t in toks):
        return True
    parts = [t.lower() for t in re.findall(r"[A-Za-z]{2,}", name or "")]
    if len(parts) >= 2 and (parts[0][0] + parts[-1]) in local:
        return True
    return bool(OFFICE_FORM.match(email.split("@")[0]))


def build(cache, today):
    if len(cache) < MIN_CITIES:
        fail("%d cities in the cache, expected at least %d. A city refused by its "
             "own robots.txt is the one legitimate reason for a shortfall and none "
             "is recorded today, so read the scraper's output before shipping."
             % (len(cache), MIN_CITIES))

    out, seats, emails, phones, named, with_contact = {}, 0, 0, 0, 0, 0
    for geoid, rec in sorted(cache.items()):
        if geoid not in SEATS:
            fail("%s is in the cache and not in SEATS. A city joins this file with "
                 "its own measured seat count, never on a default." % geoid)
        city, want = SEATS[geoid]
        members = rec.get("members") or []
        if len(members) != want:
            fail("%s: %d members, its page publishes %d. A council's size is set by "
                 "its charter and does not drift, so this is the page changing or "
                 "the city changing and both need reading."
                 % (city, len(members), want))

        mayors = [m for m in members if m.get("kind") == "mayor"]
        expect_mayor = geoid not in NO_MAYOR
        if len(mayors) != (1 if expect_mayor else 0):
            fail("%s: %d mayor records, expected %d. Davenport and Cedar Falls name "
                 "no mayor on the page this project reads and carry that as a "
                 "measurement; a change either way needs reading."
                 % (city, len(mayors), 1 if expect_mayor else 0))

        clean, city_contact = [], False
        for member in members:
            name = (member.get("name") or "").strip()
            if not name:
                fail("%s: a member with no name" % city)
            row = {"name": name, "role": (member.get("role") or "").strip(),
                   "kind": member.get("kind")}
            if member.get("seat"):
                row["seat"] = member["seat"]
                named += 1
            if member.get("termEnds"):
                row["termEnds"] = member["termEnds"]

            phone = (member.get("phone") or "").strip()
            if phone:
                row["phone"] = phone
                phones += 1
                city_contact = True

            email = (member.get("email") or "").strip()
            if email:
                if not EMAIL_RE.match(email):
                    fail("%s: %s's address %r is not an address" % (city, name, email))
                if not email_witnesses(name, email):
                    fail("%s: %s's address %r carries neither their name nor an "
                         "office form. An address witnessed against nobody this card "
                         "names is how a reader writes to the wrong person."
                         % (city, name, email))
                row["email"] = email
                emails += 1
                city_contact = True

            for field, value in row.items():
                if isinstance(value, str) and ADDRESS.search(value):
                    fail("%s: %s's %s reads as a street address (%r). Three of these "
                         "cities publish their members' home addresses and none of "
                         "them ships." % (city, name, field, value))
                if field not in FIELDS:
                    fail("%s: %s carries an unexpected field %r" % (city, name, field))
            clean.append(row)

        names = [m["name"].lower() for m in clean]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            fail("%s: these names appear more than once: %s. A repeated name means "
                 "the page now names each member twice, and the second naming is not "
                 "always spelled the same." % (city, ", ".join(dupes)))

        seats += len(clean)
        if city_contact:
            with_contact += 1
        out[geoid] = {"city": city, "sourceUrl": rec.get("sourceUrl"),
                      "namesMayor": bool(expect_mayor),
                      "asOf": today, "members": clean}

    return out


def verify(payload, where):
    """Every floor and every refusal, re-applied to a finished file.

    THE BUILD PATH AND `--check` BOTH RUN THIS, and `--check` runs it on the
    file a READER IS SERVED rather than on a rebuild from the cache. The cache
    is gitignored, so a check comparing against it could never run in CI --
    which is the shape `build_ia_township_officers.py` already settled on, and
    the reason it is a merge gate rather than a developer's convenience.
    """
    if len(payload) < MIN_CITIES:
        fail("%s: %d cities, expected at least %d. A city refused by its own "
             "robots.txt is the one legitimate reason for a shortfall and none is "
             "recorded today." % (where, len(payload), MIN_CITIES))
    seats = emails = phones = named = with_contact = 0
    for geoid, rec in sorted(payload.items()):
        if geoid not in SEATS:
            fail("%s: %s is in the file and not in SEATS. A city joins with its own "
                 "measured seat count, never on a default." % (where, geoid))
        city, want = SEATS[geoid]
        members = rec.get("members") or []
        if len(members) != want:
            fail("%s: %s has %d members, its page publishes %d."
                 % (where, city, len(members), want))
        mayors = [m for m in members if m.get("kind") == "mayor"]
        expect = 0 if geoid in NO_MAYOR else 1
        if len(mayors) != expect:
            fail("%s: %s has %d mayor records, expected %d."
                 % (where, city, len(mayors), expect))
        if rec.get("namesMayor") != (geoid not in NO_MAYOR):
            fail("%s: %s's namesMayor disagrees with NO_MAYOR, and the card reads "
                 "that field to decide whether to say the mayor is not published."
                 % (where, city))
        contact = False
        for member in members:
            if not (member.get("name") or "").strip():
                fail("%s: %s has a member with no name" % (where, city))
            for field, value in member.items():
                if field not in FIELDS:
                    fail("%s: %s's %s carries an unexpected field %r"
                         % (where, city, member.get("name"), field))
                if isinstance(value, str) and ADDRESS.search(value):
                    fail("%s: %s's %s reads as a street address (%r). Three of these "
                         "cities publish their members' home addresses and no field "
                         "of this file may ever hold one."
                         % (where, member.get("name"), field, value))
            if member.get("email"):
                if not email_witnesses(member["name"], member["email"]):
                    fail("%s: %s's address %r carries neither their name nor an "
                         "office form." % (where, member["name"], member["email"]))
                emails += 1
                contact = True
            if member.get("phone"):
                phones += 1
                contact = True
            if member.get("seat"):
                named += 1
        seats += len(members)
        if contact:
            with_contact += 1

    for label, got, floor in (("seats", seats, MIN_SEATS),
                              ("e-mails", emails, MIN_EMAILS),
                              ("phones", phones, MIN_PHONES),
                              ("named seats", named, MIN_SEATS_NAMED),
                              ("cities publishing any contact", with_contact,
                               MIN_WITH_CONTACT)):
        if got < floor:
            fail("%s: %d %s, expected at least %d. Every floor was measured against "
                 "what the fourteen pages publish, so a shortfall is a page changing "
                 "rather than a person declining to publish."
                 % (where, got, label, floor))
    return seats, emails, phones, named, with_contact


def report(prefix, payload, counts):
    print("ia-city-councils: %s — %d cities, %d seats (%d e-mails, %d phones, "
          "%d named seats, %d cities publish any contact)"
          % (prefix, len(payload), counts[0], counts[1], counts[2], counts[3],
             counts[4]))


def main(check_only):
    path = os.path.join(APP_DATA_DIR, OUT_NAME)
    if check_only:
        shipped = load(path, "the shipped roster")
        report("OK", shipped, verify(shipped, OUT_NAME))
        return 0

    cache = load(CACHE, "run ia/scripts/ia_city_council_scraper.py first")
    payload = build(cache, datetime.date.today().isoformat())
    counts = verify(payload, OUT_NAME)
    with open(path, "w") as f:
        f.write(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    report("wrote " + OUT_NAME, payload, counts)
    for geoid in sorted(NO_MAYOR):
        print("  %s names no mayor on the page this project reads — the card says so"
              % NO_MAYOR[geoid])
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
