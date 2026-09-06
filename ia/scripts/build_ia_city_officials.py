#!/usr/bin/env python3
"""
Build data/app/ia-city-officials.json — the elected officials of the five Iowa
cities whose own pages a machine can read, rendered on the City card.

WHAT THIS FILE IS, AND MORE IMPORTANTLY WHAT IT IS NOT
--------------------------------------------------------
It is FIVE cities out of 939. It is not a statewide roster, it does not close
`ia-municipal-officeholders`, and the City card says so in the same breath as
it names them -- because the reader in the other 932 cities has to be told that
the silence is the app's, not their city's.

The five were not chosen; they are what survived a measurement. On 2026-09-04
all 532 Iowa cities that publish a website were swept for a council roster:
16 yielded one, and five cleared every check (a plausible council, no repeated
name, a mayor identified, and contact on at least half the records). 407 of
Iowa's 939 cities publish no website at all, which is the ceiling before any
parsing question. The whole measurement is in the gap record's blocker.

EVERY ONE IS AT-LARGE, WHICH IS WHY NOTHING HERE IS A LAYER
-------------------------------------------------------------
All five elect a mayor and five council members with no wards among them.
The fleet's at-large rule sends a body elected by the whole unit to the unit's
IDENTITY card rather than to a polygon layer, so these are roster rows on
`municipality` -- no layer, no dispatch entry, no coverage function, nothing
in LAYER_AREA_RANK. Iowa's two cities that DO elect by ward are Des Moines and
Waterloo, and they are the `city-ward` layer.

THE ADDRESS TEST IS THE COUNTY BUILDER'S, APPLIED UNCHANGED
-------------------------------------------------------------
Six of the 30 addresses these cities publish are NOT on a municipal domain:
Moravia lists consumer webmail, an internet-provider account and a contracting
business its councilman runs. That is not sloppiness on the city's part -- it
is what a town of a few hundred people has, and the city publishes those
addresses as the way to reach its officials.

So the same test build_ia_county_officers.py already applies decides it here:
AN ADDRESS SHIPS ONLY IF THE OFFICEHOLDER'S OWN NAME IS IN ITS LOCAL PART, OR
ITS FORM IS AN OFFICE MAILBOX. Measured at first build, all 30 pass -- 27 on
the name and 3 as a `mayor@` office mailbox. That includes the contracting
business, whose local part carries the councilman's surname. Re-run every build against the name
actually shipped, never the one the scrape matched, so a name correction
cannot leave an address witnessed against somebody this card is not naming.

NO HOME ADDRESSES, EVER. These pages carry none, and if one ever appears the
parser must not start shipping it: only name, role, e-mail and phone are read.

Usage:
    python3 ia/scripts/ia_city_officials_scraper.py   # refresh the cache
    python3 ia/scripts/build_ia_city_officials.py
    python3 ia/scripts/build_ia_city_officials.py --check
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache",
                     "ia_city_officials.json")
OUT_NAME = "ia-city-officials.json"
CONTACT_FILE = "ia-city-contact.json"

# A FLOOR, NOT AN EQUALITY, AND THE CHANGE IS NOT A LOOSENING. This was
# `EXPECT_CITIES = 5` while every city in the table was fetchable. Since
# 2026-09-05 the scraper consults each city's robots.txt first, and
# cityofpalo.com refuses `districtry` on every path (an otherwise-permissive
# file ending `User-agent: * / Disallow: /`), so its page is never requested
# and four cities arrive. A city refused by robots re-enters by itself the
# week its file changes, which an equality gate would turn into a build
# failure rather than a measurement.
MIN_CITIES = 4                # measured 4 of the 5 in the scraper's table
SEATS_PER_CITY = 6            # a mayor plus five council members, in all of them
MIN_EMAILS = 24               # measured 24 of 24; the cities publish one for
                              # everyone. Was 30 when Palo's six shipped.
MIN_PHONES = 18               # measured 18 of 24 -- unchanged by Palo leaving,
                              # because Palo published no phone at all

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
OFFICE_FORM = re.compile(r"^(mayor|clerk|council|city|admin|info|office)", re.I)
MAYOR_ONLY = re.compile(r"(?i)^mayor$")


def load(path, what):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError as e:
        raise RuntimeError("cannot read %s (%s) -- %s" % (path, e, what))


def email_witnesses(name, email):
    """Does this address's local part carry THIS person's name?

    Lifted unchanged in behaviour from build_ia_county_officers.py, which is
    the authority; the duplication is deliberate so a change there is a
    decision made twice rather than a silent change of policy here.
    """
    local = re.sub(r"[^a-z]", "", email.split("@")[0].lower())
    toks = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", name or "")]
    if any(t in local for t in toks):
        return True
    parts = [t.lower() for t in re.findall(r"[A-Za-z]{2,}", name or "")]
    if len(parts) >= 2:
        for sur in parts[1:]:
            if local.startswith(parts[0][0] + sur):
                return True
    return False


def main():
    check_only = "--check" in sys.argv[1:]
    out_path = os.path.join(APP_DATA_DIR, OUT_NAME)

    cache = load(CACHE, "run ia/scripts/ia_city_officials_scraper.py first")
    contact = load(os.path.join(APP_DATA_DIR, CONTACT_FILE),
                   "the City card's contact file is this build's place-key witness")

    if len(cache) < MIN_CITIES:
        raise RuntimeError("the cache holds %d cities, floor %d -- read the "
                           "scraper's log before touching this: a city leaves "
                           "either because its page changed shape or because "
                           "its robots.txt now refuses us, and those are "
                           "different problems" % (len(cache), MIN_CITIES))

    payload_obj, emails, phones, offices = {}, 0, 0, 0
    for geoid in sorted(cache):
        city = cache[geoid]
        # THE PLACE KEY MUST BE ONE THE CITY CARD ALREADY RESOLVES. Every city
        # here has to exist in the contact file, which is joined 939/939 to
        # TIGERweb's places -- so a typo'd or retired GEOID fails here rather
        # than shipping a roster onto a card no reader can reach.
        if geoid not in contact:
            raise RuntimeError(
                "%s is keyed %s, which is not a place in %s. The City card reads that "
                "file's keys, so a roster under an unknown key would never render."
                % (city["city"], geoid, CONTACT_FILE))
        if contact[geoid].get("name", "").lower() != city["city"].lower():
            raise RuntimeError(
                "%s is keyed %s, which %s calls %r. Two names for one key means the "
                "roster would render on the wrong city's card."
                % (city["city"], geoid, CONTACT_FILE, contact[geoid].get("name")))

        members = city["members"]
        if len(members) != SEATS_PER_CITY:
            raise RuntimeError("%s carries %d officials, expected %d"
                               % (city["city"], len(members), SEATS_PER_CITY))
        if sum(1 for m in members if MAYOR_ONLY.match(m["role"])) != 1:
            raise RuntimeError("%s does not name exactly one mayor" % city["city"])

        rows = []
        for m in members:
            email = (m.get("email") or "").strip()
            if email:
                if not EMAIL_RE.match(email):
                    raise RuntimeError("%s: %s carries e-mail %r"
                                       % (city["city"], m["name"], email))
                office = bool(OFFICE_FORM.match(email.split("@")[0]))
                if not (email_witnesses(m["name"], email) or office):
                    raise RuntimeError(
                        "%s: %s's published address %s carries neither their own name nor "
                        "an office form. The county-officer test refuses it, and this "
                        "builder refuses it for the same reason -- an address that names "
                        "somebody else is not this person's contact."
                        % (city["city"], m["name"], email))
                if office:
                    offices += 1
                emails += 1
            row = {"name": m["name"], "role": m["role"]}
            if email:
                row["email"] = email
            if m.get("phone"):
                row["phone"] = m["phone"]
                phones += 1
            rows.append(row)

        payload_obj[geoid] = {"city": city["city"], "sourceUrl": city["sourceUrl"],
                              "members": rows}

    if emails < MIN_EMAILS:
        raise RuntimeError("%d e-mails across %d cities, floor %d -- these cities publish "
                           "one for every official, so a shortfall is a page changing "
                           "shape" % (emails, len(payload_obj), MIN_EMAILS))
    if phones < MIN_PHONES:
        raise RuntimeError("%d phones, floor %d" % (phones, MIN_PHONES))

    payload = json.dumps(payload_obj, indent=1, sort_keys=True) + "\n"
    print("ia-city-officials: %d cities, %d officials, %d e-mails (%d office-form), "
          "%d phones" % (len(payload_obj), sum(len(c["members"]) for c in payload_obj.values()),
                         emails, offices, phones), file=sys.stderr)

    if check_only:
        try:
            with open(out_path) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError("%s is missing (%s)" % (OUT_NAME, e))
        if shipped != payload:
            raise RuntimeError("data/app/%s has drifted from the cache. Re-run: "
                               "python3 ia/scripts/build_ia_city_officials.py" % OUT_NAME)
        print("check: shipped roster matches the cache", file=sys.stderr)
        return

    with open(out_path, "w") as f:
        f.write(payload)
    print("wrote data/app/%s" % OUT_NAME, file=sys.stderr)


if __name__ == "__main__":
    main()
