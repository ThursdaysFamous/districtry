#!/usr/bin/env python3
"""
Build data/app/wi-alderpersons.json from wi_alderperson_scraper.py's
intermediate — the aldermanic-district card's roster for every municipality
whose route is verified. FLOORS below is the list; it is not restated here,
because a prose copy of it went stale twice (it said 24 municipalities and 240
seats while the file held 30 and 285, and it enumerated 28 of the 30) and a
second answer to a question with one is how this file's own gates get believed
over the data. MEASURED 2026-09-25 by the run that wrote the file: 292
alderpersons across 265 districts in 31 municipalities holding 293 seats — one
more seat than people, because Oconomowoc's own directory lists one of District
1's two seats as vacant.
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
`seats` is how many PEOPLE those districts elect, DERIVED here rather than
restated by hand: the members counted, plus every district the city says is
wholly vacant, plus every SEAT inside a named district the city says is vacant.
They diverged on 2026-09-24 when the multi-member tranche landed.

THE THREE THINGS A SOURCE CAN SAY ABOUT AN EMPTY SEAT, and they are different
claims that must not be collapsed:

  `vacantDistricts`  the city names NOBODY for a whole district and says it is
                     vacant (Madison's District 1 at first build). The card says
                     the district is vacant, because it has nothing else to say.
  `vacantSeats`      a count per district of seats the city lists as vacant in a
                     district that DOES name somebody — Oconomowoc's District 1,
                     which seats two, names Karen Spiegelberg and prints
                     `Vacanct` for the other. The card names the member and says
                     the district is a seat short.
  neither            the city seats two, names one and says nothing about the
                     other. That is NOT `vacantSeats`: the city has made no
                     statement about the seat, and a card reading "the city
                     lists the other as vacant" would be a false statement about
                     the city. Illinois's at-large card carries the honest shape
                     for it (`seats`, rendering "1 of 2 seats not listed"), and
                     nothing in Wisconsin needs it yet, so it is not built.
"""

import datetime
import json
import os
import re
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
    # THE MULTI-MEMBER TRANCHE OF 2026-09-24, the four cities #1133 unblocked.
    # Each seats more than one alderperson per district, which is why the
    # `districts` column and the `named` floor are now different numbers: read
    # Wautoma as three districts holding six people. The contact floors are
    # this tranche's first measured run less one, as everywhere above.
    #   Wautoma   1, 3 and 2 across three districts — the UNEVEN council that
    #             settled the schema. Phones for all six, no e-mail published;
    #             its page prints home addresses, which are never read.
    #   Algoma    two per district; a mailbox and a phone for all eight. The
    #             mailboxes are numbered by SEAT (alder1..alder8), not by
    #             district, so they are carried and never used to place anyone.
    #   Horicon   two per district; the page publishes neither e-mail nor phone
    #             where this scrape reads, so both floors are 0 by measurement.
    #   Dodgeville two per district; eight mailboxes, six phones.
    "84625": ("Wautoma", 3, 6, 0, 5, 0),
    "01000": ("Algoma", 4, 8, 7, 7, 0),
    "35750": ("Horicon", 3, 6, 0, 0, 0),
    "20350": ("Dodgeville", 4, 8, 7, 5, 0),
    # The second multi-member tranche, 2026-09-24. Both publish a mailbox and a
    # direct phone for every seat, so their contact floors are the measured
    # count less one rather than a zero.
    #   Black River Falls numbers its seats by WARD and the scraper asserts
    #     ward N IS district N against LTSB's live fabric before reading a name.
    #   Neenah lists its nine members in NO district order, so each name is
    #     read from the text before its own label rather than by position.
    "07900": ("Black River Falls", 4, 8, 7, 7, 0),
    "55750": ("Neenah", 3, 9, 8, 8, 0),
    # Oconomowoc, 2026-09-25. THE NAMED FLOOR IS SEVEN AGAINST EIGHT SEATS, and
    # that is the point of it: the city's own directory lists District 1's second
    # seat as vacant, so seven people hold eight seats and `vacantSeats` carries
    # the difference. A floor may be exceeded, so the day the city fills the seat
    # this passes at eight and the vacancy disappears from the file by itself.
    # Every one of the seven has a mailbox and a direct phone; the floors are
    # that measured count less one, as everywhere above.
    "59250": ("Oconomowoc", 4, 7, 6, 6, 0),
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
    # `vacantSeats` COUNTS SEATS INSIDE A DISTRICT THAT NAMES SOMEBODY, which is
    # a different statement from `vacantDistricts` above and is checked against a
    # different thing: the district must be one the roster names people for, or
    # the card renders a seat count beside no names at all. See this file's
    # docstring for the three claims a source can make about an empty seat.
    vacant_seats = c.get("vacantSeats") or {}
    for district, n in sorted(vacant_seats.items()):
        if district not in ms:
            raise SystemExit("%s district %s lists vacant seats and names "
                             "nobody — a district with no members at all is "
                             "vacantDistricts, which the card reads differently"
                             % (name, district))
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise SystemExit("%s district %s: vacantSeats must be a whole "
                             "number of seats, at least one (got %r)"
                             % (name, district, n))
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
    c["seats"] = len(people) + len(vacant) + sum(vacant_seats.values())
    return len(people)


def _city(members, districts=None, municipality="Testville", vacant=None,
          vacant_seats=None):
    c = {"municipality": municipality, "members": members,
         "districts": districts if districts is not None else len(members),
         "sourceUrl": "https://example.test/council"}
    if vacant is not None:
        c["vacantDistricts"] = vacant
    if vacant_seats is not None:
        c["vacantSeats"] = vacant_seats
    return c


QUEUE_ANCHOR = "QUEUE ROWS FOLLOW"
QUEUE_ROW = re.compile(r"^#\s{2,}(\S.*?\S)\s{2,}C \d+\s+https?://\S+\s*$", re.M)
QUEUE_EMPTY = re.compile(r"^#\s{2,}QUEUE EMPTY\s*$", re.M)


def check_queue_against_floors():
    """No city the queue still lists may be one this builder already floors.

    THE DEFECT THIS CATCHES SHIPPED FOR WEEKS. wi_alderperson_scraper.py keeps a
    comment listing the councils nobody has built yet, with the page a 2026-09-05
    sweep scored, so the next pass starts from a measurement rather than
    repeating it. The rule beside it said an address leaves the queue in the
    change that starts FETCHING it, and nothing said the reverse -- so the rows
    stayed after their cities shipped, and on 2026-09-25 nine of its eighteen
    rows named councils already in the roster. A queue that lists what shipped is
    not a queue; it is a list telling the next pass to redo finished work.

    A CHECK RATHER THAN A DERIVATION, and that was measured rather than assumed.
    The obvious fix is to generate the queue from FLOORS's complement, and it
    cannot be done: a queue row carries a NAME, a council size and a URL, while a
    FLOORS entry is (name, districts, four floors) with NO URL anywhere. The
    complement can say which cities remain; it cannot produce the row a reader
    needs. So the queue stays authored and this compares it.

    IT MUST NOT BE ABLE TO PASS VACUOUSLY, which is the whole risk in reading a
    comment: reformat the block and zero rows parse, and a silent pass looks
    exactly like a clean queue. So the anchor line must be present, and rows must
    parse unless the block says EMPTY -- which is how the end state gets recorded
    when the last city ships, rather than by deleting the block and leaving this
    with nothing to read.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "wi_alderperson_scraper.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    if QUEUE_ANCHOR not in src:
        raise SystemExit(
            "queue check: %r is gone from wi_alderperson_scraper.py, so this "
            "check has nothing to read. Restore the anchor above the queue rows "
            "or retire this check deliberately." % QUEUE_ANCHOR)
    tail = src.split(QUEUE_ANCHOR, 1)[1]
    rows = [m.group(1).strip() for m in QUEUE_ROW.finditer(tail)]
    if not rows:
        # THE SENTINEL IS A WHOLE LINE, and the first draft made it a substring
        # -- which matched the INSTRUCTION telling an author to write it, four
        # lines above where the rows are. So the check read its own
        # documentation as the recorded end state and passed on a queue it could
        # not see, which the negative test for exactly this case caught. A probe
        # that can read its own declaration is measuring itself; this one wants a
        # line that is the sentinel and nothing else, which no sentence about it
        # can be.
        if not QUEUE_EMPTY.search(tail):
            raise SystemExit(
                "queue check: the anchor is there and no queue row parsed. "
                "Either the block was reformatted -- in which case this check "
                "was about to pass on a queue it could not see -- or the last "
                "city shipped, and that is recorded by putting a line reading "
                "QUEUE EMPTY and nothing else where the rows were.")
        print("  queue check: the queue is EMPTY and says so")
        return []
    shipped = {name for name, _d, _a, _b, _c, _e in FLOORS.values()}
    stale = sorted(set(rows) & shipped)
    if stale:
        raise SystemExit(
            "queue check: wi_alderperson_scraper.py still queues %d city/cities "
            "this builder already floors -- %s. A row leaves the queue in the "
            "same change that ships its city, the same step as adding its "
            "constant." % (len(stale), ", ".join(stale)))
    return rows


def selftest():
    """Drive check_city with fixtures, one per count the list shape moved.

    Every case that must FAIL is asserted to fail. A guard nothing can fail on
    purpose is a guard nobody has tested, and four of these count people where
    the code they replaced counted districts — a difference that is invisible
    while every council seats exactly one member, which is every council in the
    file today.
    """
    bad, ran = [], []

    def want_ok(label, members, districts, floors, geo, seats, vacant=None,
                vacant_seats=None):
        ran.append(label)
        c = _city(members, districts, vacant=vacant, vacant_seats=vacant_seats)
        try:
            check_city("Testville", districts, floors, c, set(geo))
        except SystemExit as e:
            bad.append("%s: expected OK, refused with %s" % (label, e))
            return
        if c["seats"] != seats:
            bad.append("%s: seats %r, expected %r" % (label, c["seats"], seats))

    def want_fail(label, members, districts, floors, geo, expect, vacant=None,
                  vacant_seats=None):
        ran.append(label)
        try:
            check_city("Testville", districts, floors,
                       _city(members, districts, vacant=vacant,
                             vacant_seats=vacant_seats), set(geo))
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

    # 9. OCONOMOWOC'S SHAPE: a district that names somebody and is a seat short.
    #    Two districts, two people, one vacant seat — three seats in all, which
    #    neither the district count nor the people count gives on its own.
    want_ok("a named district with a vacant seat", one, 2, (2, 0, 0, 0),
            {"01", "02"}, 3, vacant_seats={"01": 1})

    # 10. A VACANT SEAT MUST NOT PAPER OVER A LOST MEMBER. This is the failure
    #     the field could most easily introduce: if the seat count satisfied the
    #     floor, a city whose page dropped a member would ship short and pass,
    #     because seats would still add up. The floor counts PEOPLE, so it does
    #     not — two people against a floor of three fails whatever the vacancy
    #     says.
    want_fail("a vacant seat does not satisfy the named floor", one, 2,
              (3, 0, 0, 0), {"01", "02"}, "only 2 named", vacant_seats={"01": 1})

    # 11. A vacant seat in a district naming nobody is the OTHER claim, and the
    #     card renders it in another place, so it is refused rather than guessed.
    #     The fixture is the shape a confused scraper would actually emit: the
    #     same district in vacantDistricts AND in vacantSeats. It has to cover
    #     the geometry, or the coverage check above refuses it first for a
    #     different and also correct reason — which is what the first draft of
    #     this case did, proving nothing about the new guard.
    want_fail("vacant seats in a district with no members", {"01": [{"name": "A"}]},
              2, (1, 0, 0, 0), {"01", "02"}, "names nobody",
              vacant=[2], vacant_seats={"02": 1})

    # 12. The count is a count. `true` is an int in Python and would add 1 to
    #     the seat total while meaning nothing, and a 0 would render "2 of 2
    #     seats" with nothing vacant.
    want_fail("vacantSeats given a boolean", one, 2, (2, 0, 0, 0),
              {"01", "02"}, "whole number", vacant_seats={"01": True})
    want_fail("vacantSeats given zero", one, 2, (2, 0, 0, 0),
              {"01", "02"}, "whole number", vacant_seats={"01": 0})

    # THE QUEUE IS PART OF THE SELFTEST rather than a separate step, for the
    # reason main() gives about running selftest() on every build: a check with
    # no caller is one that stops running the week somebody forgets it.
    queued = check_queue_against_floors()

    if bad:
        for line in bad:
            print("  FAIL %s" % line)
        raise SystemExit("selftest: %d of %d case(s) failed"
                         % (len(bad), len(ran)))
    # COUNTED, never stated: an early draft of this line said 11 where ten cases
    # ran, which is the defect the rest of this file exists to prevent. It has
    # not been restated since, and this comment deliberately names no total.
    print("selftest: %d case(s), 0 failures; %d queued city/cities, none already "
          "floored" % (len(ran), len(queued)))


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
