#!/usr/bin/env python3
"""
Build data/app/wi-alderpersons.json from wi_alderperson_scraper.py's
intermediate — the aldermanic-district card's roster for the 18 municipalities
whose routes are verified (the six of 2026-08-26: Milwaukee, Madison, Green
Bay, Kenosha, Racine, Waukesha; and the twelve of 2026-09-05: Stevens Point,
Menomonie, Manitowoc, Sheboygan, Superior, Portage, Viroqua, Menasha, Howard,
Tomah, Eau Claire, Appleton — 208 seats, 207 filled + Madison's vacant
District 1).
Keyed by COUSUBFP + zero-padded district id, the exact key pair the
dissolved geometry carries, and CROSS-GATED against the shipped geometry
file: a roster row naming a district the map does not draw fails the build,
as does a covered city whose district count stops matching its seat count.

Floors are per municipality and per field, tuned to that municipality's
measured first run — one losing its e-mail column (the Brown County lesson)
fails here before the retention gate ever sees it.
"""

import datetime
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
RAW = os.path.join(SCRIPT_DIR, ".cache", "wi_alderpersons_raw.json")
GEOMETRY = os.path.join(REPO_ROOT, "data", "app", "aldermanic-districts.json")
OUT = os.path.join(REPO_ROOT, "data", "app", "wi-alderpersons.json")

# COUSUBFP -> (name, seats, min named, min emails, min phones, min urls)
FLOORS = {
    "53000": ("Milwaukee", 15, 15, 0, 0, 0),
    "48000": ("Madison", 20, 18, 17, 0, 17),
    "31000": ("Green Bay", 12, 12, 10, 9, 10),
    "39225": ("Kenosha", 17, 17, 0, 0, 0),
    "66000": ("Racine", 15, 15, 0, 0, 13),
    "84250": ("Waukesha", 15, 15, 14, 14, 0),
    # The twelve added 2026-09-05. Each field floor is the FIRST RUN'S measured
    # count less one, so a single member's blank cell is tolerated and a column
    # emptying is not; a zero is a field the source genuinely does not publish,
    # written down rather than left to look like an omission:
    #   Stevens Point routes contact through per-district forms, not addresses.
    #   Menomonie, Sheboygan, Howard and Tomah publish a profile page per seat
    #     and no contact on the roster page itself.
    #   Menasha publishes a phone and a form, and the one mailto in its table
    #     belongs to a staffer (see the scraper) — so no e-mail is read.
    #   Eau Claire seats eleven and districts five; the five district members
    #     are what an aldermanic-district card can answer for.
    #   Manitowoc's district 3 links the site's own staging host, which is not
    #     shipped, so its url floor is one below its seat count for a reason
    #     about the page rather than about a member.
    "77200": ("Stevens Point", 11, 11, 0, 10, 10),
    "51025": ("Menomonie", 11, 11, 0, 0, 10),
    "48500": ("Manitowoc", 10, 10, 0, 9, 8),
    "72975": ("Sheboygan", 10, 10, 0, 0, 9),
    "78650": ("Superior", 10, 10, 9, 9, 0),
    "64100": ("Portage", 9, 9, 8, 8, 0),
    "82925": ("Viroqua", 9, 9, 8, 8, 0),
    # the tranche of 2026-09-05 evening. THE CONTACT FLOORS ARE MEASURED, NOT
    # ASSUMED, and the first version of this block got that wrong: it set them
    # all to 0 and said "no page here puts a per-member e-mail or phone where
    # this scrape reads", which was false for two of the five. Sturgeon Bay
    # carries a per-seat district mailbox and phone beside every name, and
    # Eagle River a Phone: line and a COERWardN@ mailbox in every block; both
    # now ship, because the card-order convention says surface contact where
    # the source has it. New Berlin, Altoona and Germantown genuinely publish
    # none where this scrape reads. Sturgeon Bay prints a HOME ADDRESS between
    # the name and the phone; it is stepped over and never stored.
    "56375": ("New Berlin", 7, 7, 0, 0, 0),
    "77875": ("Sturgeon Bay", 7, 7, 7, 7, 0),
    "01550": ("Altoona", 6, 6, 0, 0, 0),
    "21625": ("Eagle River", 4, 4, 4, 4, 0),
    "28875": ("Germantown", 4, 4, 0, 0, 0),
    "50825": ("Menasha", 8, 8, 0, 7, 0),
    "35950": ("Howard", 8, 8, 0, 0, 7),
    "80075": ("Tomah", 8, 8, 0, 0, 7),
    "22300": ("Eau Claire", 5, 5, 0, 0, 4),
    # Appleton joins 2026-09-05, the day its geometry could first be drawn
    # (build_wi_aldermanic_districts.py, LOCAL_COMPOSITION). Its council page
    # carries a phone and the city's own per-district page for every seat and
    # no e-mail for any.
    "02375": ("Appleton", 15, 15, 0, 14, 14),
}


# How many municipalities may be CARRIED from the last shipped file in one run
# before this refuses. One unreadable site is a bad afternoon on somebody else's
# server; a THIRD of the fleet at once is this end breaking, and shipping
# six-week-old rows under a current date is exactly what the fleet's dating
# discipline forbids.
#
# WRITTEN AS A FRACTION 2026-09-05, WHICH IS A RE-DERIVATION AND NOT A LOOSENING:
# the constant was a bare 2 with the reasoning "three at once is this end
# breaking", calibrated when there were six cities — a third of them. Ten more
# municipalities on ten more independent webservers makes a flat 2 a different
# and much stricter rule than the sentence that justified it, and the failure it
# would produce is a weekly PR that stops opening. `len(FLOORS) // 3` yields
# exactly 2 for the original six, so nothing about them changes.
MAX_CARRIED = max(2, len(FLOORS) // 3)


def carry_forward(cities, failures):
    """A city the scraper could not read keeps the rows it shipped last time.

    Dropping it instead would take real, correct alderpersons off the card
    because a webserver timed out — and the floors below, which are per city,
    would not even notice: they only measure the cities present. The carried
    rows are at most a week old and unchanged since the last human-reviewed PR,
    which is a far smaller claim than an empty card.

    Loud on purpose: every carry prints a NOT RE-READ line naming the
    municipality, its age and the reason, the way Illinois's DOCUMENT_ROSTERS
    do for a county with no website.

    AND IT IS LOUD IN THE DATA TOO, FROM 2026-09-05. Until then a carry copied
    the previous block verbatim: no date, no marker, and — because the card
    reads only name/phone/email/url/note — nothing a reader or a PR reviewer
    could see. With MAX_CARRIED scaling with the fleet, several municipalities
    could ride weeks-old rows under a current-dated refresh with the weekly PR
    showing no diff at all, which is precisely the "shipped six-week-old rows
    under a current date" this file's own MAX_CARRIED comment forbids.

    A carried block now carries `carriedFrom`, THE DATE THE CARRY BEGAN — not
    today's, so a municipality carried four weeks running shows a four-week-old
    date rather than a fresh one, and the card can say how stale it is. It is
    written ONLY on a carry, so a normal run adds no field and produces no diff;
    it disappears by itself the run the municipality reads again, which is what
    makes the PR that removes it the record of the recovery.
    """
    missing = sorted(set(FLOORS) - set(cities))
    if not missing:
        return cities
    if not os.path.exists(OUT):
        raise SystemExit("%s missed %s and there is no shipped file to carry "
                         "them from" % (RAW, missing))
    with open(OUT) as f:
        shipped = json.load(f)
    carried = []
    today = datetime.date.today().isoformat()
    for code in missing:
        previous = shipped.get(code)
        reason = (failures.get(code) or {}).get("reason", "no reason recorded")
        if not previous or not previous.get("members"):
            raise SystemExit("%s (%s) could not be read (%s) and has no shipped "
                             "rows to carry — a city cannot enter this file by "
                             "failing" % (FLOORS[code][0], code, reason))
        block = dict(previous)
        # keep the date the carry BEGAN, so the age is real on the fourth week
        block["carriedFrom"] = previous.get("carriedFrom") or today
        cities[code] = block
        carried.append(FLOORS[code][0])
        age = ""
        try:
            since = datetime.date.fromisoformat(block["carriedFrom"])
            age = ", %d days" % (datetime.date.today() - since).days
        except ValueError:
            pass
        print("  NOT RE-READ %-14s %d members kept from the last shipped file, "
              "carried since %s%s — %s"
              % (FLOORS[code][0], len(block["members"]), block["carriedFrom"],
                 age, reason))
    if len(carried) > MAX_CARRIED:
        raise SystemExit("%d of %d cities were unreadable (%s) — that is this "
                         "end failing, not their servers; read the scraper log "
                         "before raising MAX_CARRIED (%d)"
                         % (len(carried), len(FLOORS), ", ".join(carried),
                            MAX_CARRIED))
    return cities


def main():
    with open(RAW) as f:
        raw = json.load(f)
    cities = raw["cities"]
    cities = carry_forward(cities, raw.get("failures") or {})
    with open(GEOMETRY) as f:
        geo = json.load(f)["features"]
    geo_keys = {}
    for feat in geo:
        p = feat["properties"]
        geo_keys.setdefault(p["COUSUBFP"], set()).add(p["ALDERID"])

    if set(cities) != set(FLOORS):
        raise SystemExit("scraper covered %s, floors expect %s"
                         % (sorted(cities), sorted(FLOORS)))
    for k, (name, seats, mn, me, mp, mu) in FLOORS.items():
        c = cities[k]
        ms = c["members"]
        if c["municipality"] != name or c["seats"] != seats:
            raise SystemExit("%s: identity drifted (%r/%r)" % (name, c["municipality"], c["seats"]))
        if k not in geo_keys:
            raise SystemExit("%s (%s) has a roster but no districts in the shipped "
                             "geometry" % (name, k))
        if len(geo_keys[k]) != seats:
            raise SystemExit("%s: geometry draws %d districts, the city seats %d"
                             % (name, len(geo_keys[k]), seats))
        stray = set(ms) - geo_keys[k]
        if stray:
            raise SystemExit("%s: roster names district(s) %s the map does not draw"
                             % (name, sorted(stray)))
        vacant = set("%02d" % v for v in c.get("vacantDistricts", []))
        if set(ms) | vacant != geo_keys[k]:
            raise SystemExit("%s: %d named + %d vacant does not cover the %d districts"
                             % (name, len(ms), len(vacant), len(geo_keys[k])))
        counts = (len(ms),
                  sum(1 for m in ms.values() if m.get("email")),
                  sum(1 for m in ms.values() if m.get("phone")),
                  sum(1 for m in ms.values() if m.get("url")))
        for label, got, floor in zip(("named", "emails", "phones", "urls"),
                                     counts, (mn, me, mp, mu)):
            if got < floor:
                raise SystemExit("%s: only %d %s (floor %d) — the page shape moved"
                                 % (name, got, label, floor))

    with open(OUT, "w") as f:
        json.dump(cities, f, indent=1, ensure_ascii=False, sort_keys=True)
    total = sum(len(c["members"]) for c in cities.values())
    print("wi-alderpersons.json: %d alderpersons across %d cities -> %s"
          % (total, len(cities), os.path.relpath(OUT, REPO_ROOT)))


if __name__ == "__main__":
    main()
