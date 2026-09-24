#!/usr/bin/env python3
"""
Build data/app/wi-alderpersons.json from wi_alderperson_scraper.py's
intermediate — the aldermanic-district card's roster for the 24 municipalities
whose routes are verified (the six of 2026-08-26: Milwaukee, Madison, Green
Bay, Kenosha, Racine, Waukesha; the twelve of 2026-09-05: Stevens Point,
Menomonie, Manitowoc, Sheboygan, Superior, Portage, Viroqua, Menasha, Howard,
Tomah, Eau Claire, Appleton; the five of that evening: New Berlin, Sturgeon
Bay, Altoona, Eagle River, Germantown; and New Lisbon, 2026-09-06).
Measured 2026-09-24: 240 districts, 240 alderpersons, no vacancy. The count
this docstring carried said 18 municipalities and 208 seats, and Madison's
District 1, recorded here as vacant, has since been filled.
Keyed by COUSUBFP + zero-padded district id, the exact key pair the
dissolved geometry carries, and CROSS-GATED against the shipped geometry
file: a roster row naming a district the map does not draw fails the build,
as does a covered city whose district count stops matching its seat count.

Floors are per municipality and per field, tuned to that municipality's
measured first run — one losing its e-mail column (the Brown County lesson)
fails here before the retention gate ever sees it.

THE SHAPE: `members[district]` IS ALWAYS A LIST, never a bare member object.
Wisconsin councils do not all seat one alderperson per district — of the 22
municipalities the 2026-09-06 sweep matched, FIFTEEN seat more than one, and
Wautoma seats ONE, THREE and TWO across its three districts, so an arbitrary
count is the only shape that fits and a fixed pair of slots was refused. Every
municipality shipped today names exactly one member per district, so every list
here has one element; that is a fact about these municipalities and never a
shape any reader may rely on.

TWO NUMBERS THAT COINCIDE TODAY AND WILL NOT. `districts` is how many districts
the municipality's geometry draws, and is what the geometry cross-gate compares.
`seats` is how many PEOPLE those districts elect, DERIVED here by counting the
members rather than restated by hand. They are equal for all 24 municipalities
in this file and diverge the day a multi-member council joins, which is why they
are counted separately now rather than when it happens.
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

# COUSUBFP -> (name, districts, min named, min emails, min phones, min urls)
# `districts` is the count the shipped geometry must draw. The four floors
# count PEOPLE, not districts: in a multi-member council one district losing
# one of its three members is a real loss a district count cannot see.
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
    # New Lisbon numbers its seats by WARD GROUP and LTSB witnesses the
    # grouping live. E-mail is 0 by ACCESS CONTROL, not by absence: every
    # address on the page is Cloudflare-obfuscated, which is not worked around.
    "56900": ("New Lisbon", 4, 4, 0, 4, 0),
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
              % (FLOORS[code][0],
                 sum(len(v) for v in block["members"].values()),
                 block["carriedFrom"],
                 age, reason))
    if len(carried) > MAX_CARRIED:
        raise SystemExit("%d of %d cities were unreadable (%s) — that is this "
                         "end failing, not their servers; read the scraper log "
                         "before raising MAX_CARRIED (%d)"
                         % (len(carried), len(FLOORS), ", ".join(carried),
                            MAX_CARRIED))
    return cities


def check_city(name, districts, floors, c, geo_districts):
    """Every guard for one municipality, and the derived `seats` it writes.

    A function rather than a loop body so selftest() can drive it with
    fixtures: the shape change this file describes moved four counts at once,
    and each of them reads plausibly when it is wrong, so each needs a case
    that fails on purpose.

    `geo_districts` is the set of district ids the shipped geometry draws for
    this municipality. Raises SystemExit naming the municipality on any
    failure; on success sets c["seats"] and returns the people it counted.
    """
    mn, me, mp, mu = floors
    ms = c["members"]
    # THE SHAPE IS CHECKED BEFORE ANYTHING IS COUNTED. Every count below reads
    # through a list, so a bare member object would be counted by len() as its
    # number of KEYS — "name", "phone", "url" reads as three people. A wrong
    # number that looks plausible is worse than a crash, so the shape fails
    # here, named, before any arithmetic runs on it.
    for district, people in sorted(ms.items()):
        if not isinstance(people, list):
            raise SystemExit("%s district %s: members must be a LIST (got %s) "
                             "— see this file's docstring"
                             % (name, district, type(people).__name__))
        if not people:
            raise SystemExit("%s district %s: empty member list — a district "
                             "with nobody in it is a VACANCY and rides "
                             "vacantDistricts" % (name, district))
    if c["municipality"] != name or c.get("districts") != districts:
        raise SystemExit("%s: identity drifted (%r/%r)"
                         % (name, c["municipality"], c.get("districts")))
    if not geo_districts:
        raise SystemExit("%s has a roster but no districts in the shipped "
                         "geometry" % name)
    if len(geo_districts) != districts:
        raise SystemExit("%s: geometry draws %d districts, the roster expects %d"
                         % (name, len(geo_districts), districts))
    stray = set(ms) - geo_districts
    if stray:
        raise SystemExit("%s: roster names district(s) %s the map does not draw"
                         % (name, sorted(stray)))
    vacant = set("%02d" % v for v in c.get("vacantDistricts", []))
    if set(ms) | vacant != geo_districts:
        raise SystemExit("%s: %d district(s) named + %d vacant does not cover "
                         "the %d the map draws"
                         % (name, len(ms), len(vacant), len(geo_districts)))
    # PEOPLE, flattened out of the per-district lists. len(ms) counts DISTRICTS
    # and is the wrong denominator for every one of these four.
    people = [m for lst in ms.values() for m in lst]
    counts = (len(people),
              sum(1 for m in people if m.get("email")),
              sum(1 for m in people if m.get("phone")),
              sum(1 for m in people if m.get("url")))
    for label, got, floor in zip(("named", "emails", "phones", "urls"),
                                 counts, (mn, me, mp, mu)):
        if got < floor:
            raise SystemExit("%s: only %d %s (floor %d) — the page shape moved"
                             % (name, got, label, floor))
    # `seats` is DERIVED and never carried through from the scraper's own
    # hand-kept table: how many people these districts elect is a property of
    # the roster just read, and a hand-kept copy of it is a second reader of
    # one question.
    c["seats"] = len(people) + len(vacant)
    return len(people)


def _city(members, districts=None, municipality="Testville", vacant=None):
    c = {"municipality": municipality, "members": members,
         "districts": districts if districts is not None else len(members),
         "sourceUrl": "https://example.test/council"}
    if vacant is not None:
        c["vacantDistricts"] = vacant
    return c


def selftest():
    """Drive check_city with fixtures, one per count the list shape moved.

    Every case that must FAIL is asserted to fail. A guard nothing can fail on
    purpose is a guard nobody has tested, and four of these count people where
    the code they replaced counted districts — a difference that is invisible
    while every council seats exactly one member, which is every council in the
    file today.
    """
    bad, ran = [], []

    def want_ok(label, members, districts, floors, geo, seats, vacant=None):
        ran.append(label)
        c = _city(members, districts, vacant=vacant)
        try:
            check_city("Testville", districts, floors, c, set(geo))
        except SystemExit as e:
            bad.append("%s: expected OK, refused with %s" % (label, e))
            return
        if c["seats"] != seats:
            bad.append("%s: seats %r, expected %r" % (label, c["seats"], seats))

    def want_fail(label, members, districts, floors, geo, expect, vacant=None):
        ran.append(label)
        try:
            check_city("Testville", districts, floors,
                       _city(members, districts, vacant=vacant), set(geo))
        except SystemExit as e:
            if expect not in str(e):
                bad.append("%s: refused for the wrong reason: %s" % (label, e))
            return
        bad.append("%s: expected a refusal, got none" % label)

    one = {"01": [{"name": "A"}], "02": [{"name": "B"}]}
    # 1. The shape every municipality has today: one member per district.
    want_ok("single-member", one, 2, (2, 0, 0, 0), {"01", "02"}, 2)

    # 2. THE CASE THE CHANGE EXISTS FOR — Wautoma's uneven councils. Two
    #    districts, four people. `seats` must be 4 and the named floor must be
    #    satisfied by 4, not by the 2 a district count would have given.
    uneven = {"01": [{"name": "A"}],
              "02": [{"name": "B"}, {"name": "C"}, {"name": "D"}]}
    want_ok("multi-member", uneven, 2, (4, 0, 0, 0), {"01", "02"}, 4)

    # 3. ...and the floor counts PEOPLE, so a council that loses one of a
    #    district's three members fails even though every district is still
    #    named. This is the loss a district count cannot see.
    short = {"01": [{"name": "A"}], "02": [{"name": "B"}, {"name": "C"}]}
    want_fail("member lost from a multi-member district", short, 2,
              (4, 0, 0, 0), {"01", "02"}, "only 3 named")

    # 4. The old shape must not pass silently. A bare dict has three keys, so
    #    a len() over it reads as three people.
    want_fail("bare member object (the pre-2026-09-24 shape)",
              {"01": {"name": "A", "phone": "x", "url": "y"}, "02": [{"name": "B"}]},
              2, (2, 0, 0, 0), {"01", "02"}, "must be a LIST")

    # 5. An empty list is a vacancy written the wrong way.
    want_fail("empty member list", {"01": [], "02": [{"name": "B"}]}, 2,
              (1, 0, 0, 0), {"01", "02"}, "empty member list")

    # 6. Contact floors count people across the lists, not districts.
    contacts = {"01": [{"name": "A", "email": "a@x.test"}],
                "02": [{"name": "B", "email": "b@x.test"},
                       {"name": "C", "email": "c@x.test"}]}
    want_ok("contacts counted per person", contacts, 2, (3, 3, 0, 0),
            {"01", "02"}, 3)
    want_fail("e-mail column emptying", contacts, 2, (3, 4, 0, 0),
              {"01", "02"}, "only 3 emails")

    # 7. The geometry cross-gate compares DISTRICTS and is unmoved by how many
    #    people sit in them.
    want_fail("geometry draws a district the roster does not expect", uneven, 2,
              (4, 0, 0, 0), {"01", "02", "03"}, "geometry draws 3 districts")
    want_fail("roster names a district the map does not draw", uneven, 2,
              (4, 0, 0, 0), {"01", "09"}, "does not draw")

    # 8. A vacancy is still a district with no members KEY, and still counts
    #    towards seats — the card says "vacant" rather than naming nobody.
    want_ok("vacant district", {"01": [{"name": "A"}]}, 2, (1, 0, 0, 0),
            {"01", "02"}, 2, vacant=[2])

    if bad:
        for line in bad:
            print("  FAIL %s" % line)
        raise SystemExit("selftest: %d of %d case(s) failed"
                         % (len(bad), len(ran)))
    # COUNTED, never stated: the first draft of this line said 11 where ten
    # cases run, which is the defect the rest of this file exists to prevent.
    print("selftest: %d case(s), 0 failures" % len(ran))


def main():
    # ON EVERY BUILD, not as a separate CI step. It costs milliseconds and the
    # weekly job is the witness that it still passes; a --selftest flag with no
    # caller is a test that stops being run the week somebody forgets it.
    selftest()
    if "--selftest" in sys.argv[1:]:
        return
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
    for k, (name, districts, mn, me, mp, mu) in FLOORS.items():
        check_city(name, districts, (mn, me, mp, mu), cities[k],
                   geo_keys.get(k, set()))

    with open(OUT, "w") as f:
        json.dump(cities, f, indent=1, ensure_ascii=False, sort_keys=True)
    total = sum(len(lst) for c in cities.values()
                for lst in c["members"].values())
    print("wi-alderpersons.json: %d alderpersons across %d cities -> %s"
          % (total, len(cities), os.path.relpath(OUT, REPO_ROOT)))


if __name__ == "__main__":
    main()
