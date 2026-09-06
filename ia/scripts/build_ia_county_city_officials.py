#!/usr/bin/env python3
"""
Build data/app/ia-county-city-officials.json — the mayors, clerks and council
members Iowa's COUNTIES publish for the cities inside them.

WHY THIS FILE EXISTS AND WHAT IT CLOSES
-----------------------------------------
`ia-municipal-officeholders` has said since it was written that no statewide
source names Iowa's mayors, council members or clerks, and it has been right.
Its own blocker also named one route as NOT YET PROBED -- the county auditors,
Iowa's statutory commissioners of elections under Iowa Code 47.2 -- and noted
that seven counties' HOME pages had been fetched, "which is what a homepage
looks like either way and settles nothing".

Probed properly on 2026-09-05 it settles a great deal. TWELVE counties publish
a full city-officials page; NINE of them are current. Those nine name 98
cities' officeholders, where this app could previously name EIGHT cities in
the whole state. The answer was never a state office; it is the counties, one
at a time, which is this project's own Knox lesson for the nth time: a level
of government that has no answer is not evidence about the datum.

AND THE TWELFTH IS THAT LESSON AGAIN, ONE LEVEL DOWN. Jasper was very nearly
recorded as unmeasurable: every host permuted from its auditor's MAIL domain
failed, and `jaspercounty.iowa.gov` has no A record at all. Its site is
`jasperia.org` -- cited in three of this app's own data files the whole time --
and that site LINKS OUT to the county's ELECTION AUTHORITY on its own host,
`jaspercountyelections.iowa.gov`, which is where the city officials live. A
county's election authority is a separate publisher on a separate host (the
Knox and Johnson rule), and the county's own domain was already in the repo.
Consult the data this app ships before permuting hostnames.

THE CURRENCY GATE IS THE LOAD-BEARING ONE, AND IT IS A MEASUREMENT
-------------------------------------------------------------------
Iowa city officers are elected in November of ODD years and take office the
following January, so a page maintained since the last city election cannot
still be publishing a term that has already ended. Three of the twelve do:
Sac (29 of its 61 officials), Shelby (38 of 77) and Winnebago (22 of 51), and
all three show their four-year seats split across the SAME TWO CYCLES (2025
and 2027) where the other nine straddle 2027 and 2029 -- the signature of a
page last touched after the November 2023 election, two years and one city
election ago.

So a county ships only if it publishes ZERO already-expired terms. The split
that rule found was 0 against 29, 38 and 22 -- NO COUNTY SAT NEAR THE LINE,
which is itself evidence the test measures maintenance rather than noise. It
is dated rather than hand-listed, so a county that updates its page ships on
the next weekly run with nothing here to edit, and one that goes stale drops
out the same way. This is the Mahaska posture from the board-chair roster:
refusing loses a possibly-right answer, and that is the safe direction.

WHAT THE 605 ACTUALLY ARE, SINCE "MAYOR, CLERK AND COUNCIL" UNDERSTATES IT
---------------------------------------------------------------------------
487 council members, 98 mayors and 86 city clerk rows across 85 cities (Andrew
publishes two) -- and 39 people who are none of those: 12 city administrators,
10 city attorneys, 5 park commissioners, 5 park board members, 5 library
trustees, a city manager and an administrative secretary.
They ship under the role their own county publishes, on the same card, because
dropping them would be this app deciding which of a city's officials a reader
is allowed to see. Several are appointed rather than elected, which is why the
card's block is headed CITY OFFICIALS and not a claim about who was elected.

THE FLOOR IS EXPECTED TO FAIL, PERIODICALLY, BY DESIGN
--------------------------------------------------------
Exactly nine counties are current and MIN_COUNTIES is 9, so ONE county letting
its page go stale fails this build -- not a collapse, one county. And every
EVEN-YEAR JANUARY, when terms elected the previous November begin, all nine
will briefly publish expired terms until each page is updated, so expect red
for days or weeks each cycle. NEVER lower the floor to get past that: it is the
only thing that makes a county quietly going stale visible.

WHAT IS DELIBERATELY NOT CLAIMED
----------------------------------
The seat ("Ward 3", "At Large") is carried where the county publishes it --
104 of the 710 officials that ship, 117 across all twelve counties -- and no
other Iowa source pairs a council member with a ward at all. It is NOT a district card and NOT geometry: this
file names a person and the seat their own county says they hold, and the
`city-ward` layer stays the three cities whose boundaries this app actually
has. A city here that elects by ward gets its members named without any claim
about which part of the city a reader is standing in.

Nothing asserts at-large either. The five cities on `ia-city-officials.json`
were each read from the city's own page and each verified at-large; these 98
were not, and 104 of their officials carry a seat that says otherwise, so the
card's copy for them says who published the roster and stops there.

NO HOME ADDRESSES. The county pages publish CITY HALL's address and phone
under each city, which is an office, and per-person contact only as a phone
and an e-mail. If a residential address ever appears in this markup the
builder must drop it rather than ship it.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache", "ia_county_city_officials.json")
APP = os.path.join(HERE, "..", "data", "app")
OUT_PATH = os.path.join(APP, "ia-county-city-officials.json")
CONTACT = os.path.join(APP, "ia-city-contact.json")
CITY_OWN = os.path.join(APP, "ia-city-officials.json")

# Measured 2026-09-05 on the NINE current counties, after the expired-term gate
# and after the address test below: 98 distinct cities, 710 officials, 98 of 98
# naming a mayor, 85 naming a clerk, 104 carrying a seat, 142 e-mails and 116
# phones. The floors sit just under each measurement -- close enough that a
# source quietly dropping a field fails here, loose enough that ordinary
# turnover does not.
#
# MIN_COUNTIES TRACKS THE CURRENT COUNT ON PURPOSE. It was 8 when eight were
# current and is 9 now that Jasper ships, because the property worth keeping is
# that ONE county going stale fails this build loudly. A floor left behind the
# count would let the first county quietly drop out, which is the whole thing
# the gate exists to prevent. Raise it when a county joins; never lower it to
# get past a county going stale.
MIN_COUNTIES = 9
MIN_CITIES = 92
MIN_OFFICIALS = 650
MIN_MAYORS = 92               # measured 98 of 98. North English straddles the
                              # Iowa/Keokuk line: its mayor and council come
                              # from Iowa County's page and its clerk from
                              # Keokuk's, so the merge is what makes it whole.
MIN_EMAILS = 125              # measured 142; FOUR of the nine publish none
                              # (Iowa, Jackson, Keokuk, Muscatine)
MIN_PHONES = 100              # measured 116; FIVE of the nine publish none
                              # (Cerro Gordo, Iowa, Jackson, Keokuk, Muscatine)

# Lifted unchanged in behaviour from build_ia_city_officials.py, which lifted it
# from build_ia_county_officers.py: an address ships only if the officeholder's
# own name is in its local part, or its form is an office mailbox.
#
# WIDENED HERE, FOR A CLASS THOSE TWO NEVER SAW. Those builders read CITY and
# COUNTY pages, where an office mailbox is written `mayor@` or `clerk@`. These
# county pages carry small towns whose office mailbox is THE TOWN'S OWN NAME --
# plymouth@, ventura@, buckgrove@, rockfallsia@, doughertyofficial@, dowcity@,
# kironcty@, cityofbussey@ -- and an anchored mayor|clerk|city prefix reads every one of them
# as a private address and drops it. So two additions, both measured rather
# than assumed: an office TOKEN anywhere in the local part, and a local part
# that IS the city's name, alone or with one short office suffix.
#
# The widening is deliberately narrow. `meserveymowman@` starts with its city's
# name and is still dropped, because `mowman` is not an office suffix; so are
# jbsauto@, mcfdmedic40@, pst559@ and nikkijo232002@. And Manilla's clerk Lori
# Jahn is published at `laura@manillaia.com` -- a city-domain address carrying
# somebody else's first name -- which fails all three tests and is dropped,
# which is the whole point of testing the address against the name SHIPPED.
OFFICE_TOKEN = re.compile(
    r"clerk|cityof|city_of|cityhall|city_hall|council|mayor|admin|offic"
    r"|townof|town_of"
    r"|deputy|treasurer", re.I)
# Suffixes a town appends to its own name for the office mailbox.
CITY_SUFFIX = re.compile(
    r"^(ia|iowa|city|cityhall|hall|clerk|cty|co|office|official|officials"
    r"|gov|town|info|mail)?$", re.I)


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def office_mailbox(city, email):
    """Is this the CITY's mailbox rather than a private one?"""
    local = email.split("@")[0]
    if OFFICE_TOKEN.search(local):
        return True
    lo, cn = norm(local), norm(city)
    if cn and lo.startswith(cn) and CITY_SUFFIX.match(lo[len(cn):]):
        return True
    return False


def email_witnesses(name, email):
    """Does this address's local part carry THIS person's name?"""
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


def fail(msg):
    print("REFUSING TO WRITE: " + msg, file=sys.stderr)
    sys.exit(1)


def main():
    if not os.path.exists(CACHE):
        fail("no scraper output at %s -- run "
             "ia_county_city_officials_scraper.py first" % CACHE)
    scraped = json.load(open(CACHE))
    contact = json.load(open(CONTACT))
    by_name = {}
    for geoid, rec in contact.items():
        by_name.setdefault(rec["name"].strip().lower(), geoid)
    city_own = json.load(open(CITY_OWN)) if os.path.exists(CITY_OWN) else {}

    this_year = datetime.date.today().year
    kept, dropped = {}, []
    for fips, rec in sorted(scraped.items()):
        expired = [(c["city"], o["name"], o["termEnds"])
                   for c in rec["cities"] for o in c["officials"]
                   if o["termEnds"] and int(o["termEnds"]) < this_year]
        if expired:
            dropped.append((rec["county"], len(expired),
                            sum(len(c["officials"]) for c in rec["cities"])))
            continue
        kept[fips] = rec

    print("counties swept %d; current %d; dropped for expired terms %d"
          % (len(scraped), len(kept), len(dropped)))
    for county, n, tot in dropped:
        print("  DROPPED %-14s %d of %d officials publish a term that has "
              "already ended" % (county, n, tot))
    if len(kept) < MIN_COUNTIES:
        fail("only %d counties are current, floor is %d"
             % (len(kept), MIN_COUNTIES))

    out, unmatched, no_head, shadowed = {}, [], [], []
    dropped_emails = []
    for fips, rec in sorted(kept.items()):
        for city in rec["cities"]:
            name = city["city"].strip()
            geoid = by_name.get(name.lower())
            if not geoid:
                unmatched.append((rec["county"], name))
                continue
            if geoid in city_own:
                # The city's own page is the authority on the city.
                shadowed.append((rec["county"], name))
                continue
            entry = out.setdefault(geoid, {
                "city": name, "members": [], "sources": []})
            src = {"county": rec["county"], "url": rec["sourceUrl"]}
            if src not in entry["sources"]:
                entry["sources"].append(src)
            if city.get("cityAddress") and not entry.get("officeAddress"):
                entry["officeAddress"] = city["cityAddress"]
            if city.get("cityPhone") and not entry.get("officePhone"):
                entry["officePhone"] = city["cityPhone"]
            for off in city["officials"]:
                member = {"name": off["name"], "role": off["role"],
                          "county": rec["county"]}
                for key in ("seat", "status", "termEnds", "termLength",
                            "phone"):
                    if off.get(key):
                        member[key] = off[key]
                email = off.get("email")
                if email:
                    if (email_witnesses(off["name"], email)
                            or office_mailbox(name, email)):
                        member["email"] = email
                    else:
                        dropped_emails.append((name, off["name"], email))
                entry["members"].append(member)

    for geoid, entry in out.items():
        roles = " ".join((m.get("role") or "") for m in entry["members"])
        if "mayor" not in roles.lower() and "clerk" not in roles.lower():
            no_head.append(entry["city"])

    cities = len(out)
    officials = sum(len(e["members"]) for e in out.values())
    mayors = sum(1 for e in out.values()
                 if any("mayor" in (m.get("role") or "").lower()
                        for m in e["members"]))
    emails = sum(1 for e in out.values() for m in e["members"] if m.get("email"))
    phones = sum(1 for e in out.values() for m in e["members"] if m.get("phone"))
    seats = sum(1 for e in out.values() for m in e["members"] if m.get("seat"))

    print("cities %d  officials %d  mayors %d  clerks %d  seats named %d  "
          "e-mails %d  phones %d" % (
              cities, officials, mayors,
              sum(1 for e in out.values()
                  if any("clerk" in (m.get("role") or "").lower()
                         for m in e["members"])), seats, emails, phones))
    if shadowed:
        print("  %d city/cities already named from their OWN page, so the "
              "county's copy is not used: %s"
              % (len(shadowed), ", ".join(c for _, c in shadowed)))
    for city, person, email in dropped_emails:
        print("  DROPPED e-mail (neither the officeholder's name nor an office "
              "form): %s / %s / %s" % (city, person, email))

    if unmatched:
        fail("%d city name(s) do not join the shipped city list: %s"
             % (len(unmatched), unmatched[:6]))
    if no_head:
        fail("%d city/cities name neither a mayor nor a clerk, so the entry is "
             "not a roster: %s" % (len(no_head), no_head[:6]))
    if cities < MIN_CITIES:
        fail("%d cities, floor is %d" % (cities, MIN_CITIES))
    if officials < MIN_OFFICIALS:
        fail("%d officials, floor is %d" % (officials, MIN_OFFICIALS))
    if mayors < MIN_MAYORS:
        fail("%d cities name a mayor, floor is %d" % (mayors, MIN_MAYORS))
    if emails < MIN_EMAILS:
        fail("%d e-mails, floor is %d" % (emails, MIN_EMAILS))
    if phones < MIN_PHONES:
        fail("%d phones, floor is %d" % (phones, MIN_PHONES))

    with open(OUT_PATH, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %s" % OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
