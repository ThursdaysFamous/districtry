#!/usr/bin/env python3
"""
Write data/app/wi-municipal-executives.json from the scraper's raw capture.
Stage 2 of the pair; wi_municipal_executive_scraper.py is stage 1 and its
docstring carries the source, the witness rule and the measured outcome.

WHAT SHIPS, AND WHAT DELIBERATELY DOES NOT. A NAME ships only where the
municipality's own page witnessed it. Everything else about a municipality —
the office's own title ("City of Franklin Mayor"), the fact that the county
publishes an executive for it at all — is not in question and is not withheld.

CONTACT RIDES THE NAME, and that is a rule rather than a convenience. The
layer's e-mail addresses are PERSON-keyed (`jcyborowski@greendale.org`), so
shipping one beside a withheld name would publish the very name the witness
refused — the withholding would be cosmetic. Phone travels with it for the
same reason: the layer's numbers are direct lines, not switchboards. A
withheld municipality therefore carries its office title, its status and, when
the page answered at all, its link — never a person or a way to reach one.

THE LINK IS DROPPED WHEN IT 404s. Four of the layer's own `Exec_Url` values
were dead on 2026-09-03 (Bayside, Hales Corners, South Milwaukee, West Allis)
and FIVE are on 2026-09-18, Oak Creek's having moved from a 403 to a 404 — both
counts corroborating evidence of the layer's 2024-07-30 vintage. A card must
not hand a reader a link this build already knows is broken, so `pageUrl` ships
only for a page that answered.

KEYED BY 7-DIGIT PLACE GEOID — "55" + the layer's own `Muni_Code`, which is
the Census place code (West Allis 85300 -> 5585300). That is the key the
municipality card already reads off its own feature, and the same join
Illinois's municipal roster uses.

THE FLOORS ARE MEASUREMENTS, NOT TARGETS (the Barron rule). 19 municipalities
is exact — Milwaukee County's incorporated count, and the scraper fails before
this if the dedupe gives anything else. MIN_WITNESSED is set BELOW the 9
measured on 2026-09-03 rather than at it: a village that redesigns its site
drops one honestly, and a build that refuses on that would wedge weekly for a
reason that is not a defect. It is a floor against the witness silently
breaking altogether.

A NAME IS NOT DELETED BECAUSE ONE FETCH FAILED (2026-09-18)
------------------------------------------------------------
Until this date the shipped file was written from the scrape alone, so a
municipality whose page had witnessed a name last week and did not answer this
week lost the name and shipped a withholding instead. That is the whole weekly
diff for that municipality, and it reads exactly like the case the witness
exists to catch — a name that stopped witnessing because of an election or a
resignation. It is not that. It is a webserver that did not answer.

NOTHING IN THE FLEET NOTICES. `check_roster_retention.py` measures a field's
coverage per SOURCE, and this file's sources are its 19 municipalities: one
record each, below `MIN_GROUP_RECORDS`, so its per-source pass cannot fire here
at all. File-wide, one of nine names going away is a ninth, far under the
"half the records" threshold. Measured 2026-09-17, 125 of the fleet's 277
roster files have every group below that floor, so this is a CLASS of file
rather than this one's quirk, and the defence has to live in the builder.

So THE SHIPPED FILE IS AN INPUT AS WELL AS THE OUTPUT — the shape
`build_ia_county_chair.py` uses for Iowa's board chairs and
`build_wi_alderperson_roster.py` for the eighteen councils — and a name is
carried when, and only when, ALL of these hold:

* THE SCRAPER SAYS `unreachable`. That is the one verdict meaning we could not
  ASK. `refused` is an access control and a carried copy would be the site's
  data kept alive against its refusal; `missing` (404) and a page that READ and
  did not witness are both the source answering, and carrying either would hide
  a real change in what the municipality publishes. The scraper's own comment
  above `fetch` carries the split.
* THE COUNTY'S LAYER STILL NAMES THE SAME PERSON. The name in this file is the
  layer's; the municipality's page is what witnessed it. If the layer moves on,
  the carried name is contradicted by the county's own current data and is
  dropped — the same re-gate Iowa's chairs get against their supervisor roster.
* IT IS YOUNGER THAN MAX_CARRY_DAYS, counted from `carriedFrom` — the date the
  CARRY BEGAN, not today's, so a municipality carried four weeks running shows a
  four-week-old date instead of a fresh one. `carriedFrom` is written ONLY on a
  carry, so an ordinary run adds no field and produces no diff, and it
  disappears by itself the run the page reads again.
* NO SPRING ELECTION HAS FALLEN SINCE. Wisconsin elects mayors and village
  presidents on the first Tuesday of April in even years (Wis. Stat. 8.11), so a
  name read before one is no longer a claim about who holds the office, however
  few days old it is. They take office a fortnight later, on the third Tuesday,
  which makes the ELECTION the earlier and therefore stricter of the two dates
  and the one used here.

A CARRIED MUNICIPALITY DOES NOT COUNT TOWARD MIN_WITNESSED, which measures what
the SCRAPE witnessed, and the floor is checked BEFORE any carry: four sites
going quiet at once is the witness breaking, and failing there leaves last
week's correct file in place. MAX_CARRIED caps the other end — more than a
couple of unreachable municipalities in one run is this end failing rather than
theirs, and a refusal to write is louder than a file full of carried rows.

Usage:
    python3 wi/scripts/build_wi_municipal_executives.py [--raw PATH] [--out PATH]
    python3 wi/scripts/build_wi_municipal_executives.py --selftest
"""

import datetime
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "app")
DEFAULT_RAW = os.path.join(SCRIPT_DIR, ".cache", "wi_municipal_executives_raw.json")
DEFAULT_OUT = os.path.join(APP_DIR, "wi-municipal-executives.json")

EXPECT_MUNIS = 19
MIN_WITNESSED = 6          # 9 witnessed 2026-09-03; see the docstring
STATE_FIPS = "55"

# The only scraper verdict that means WE COULD NOT ASK; see the docstring and
# the comment above `fetch` in wi_municipal_executive_scraper.py.
CARRY_STATUSES = frozenset(["unreachable"])
# Sixty days is eight weekly runs — long enough that a municipality behind an
# address-sensitive CDN survives a run of bad luck, short enough that a site
# which has genuinely gone away clears within two months. The same figure
# build_ia_county_chair.py uses, for the same reason.
MAX_CARRY_DAYS = 60
# Nine of the nineteen witness today. More than two unreachable at once is this
# end failing rather than theirs, and the right answer is to refuse to write:
# the shipped file then stays as it is, which is what a carry was trying to
# achieve anyway, and the red run is what gets read.
MAX_CARRIED = 2

# The county's own terms travel with the data (its item's licenseInfo opens
# "Use of this resource constitutes acknowledgement of these terms of use"),
# so the card credits the publisher by name.
SOURCE_NAME = "Milwaukee County GIS & Land Information"


def fail(msg):
    print("build-wi-municipal-executives: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def spring_election_on(today):
    """The day Wisconsin last elected its mayors and village presidents.

    Wis. Stat. 8.11 puts them on the spring ballot in even-numbered years, and
    the spring election is the first Tuesday in April. They take office on the
    third Tuesday, a fortnight later; this returns the ELECTION, which is the
    earlier date and so the stricter boundary for a carried name.
    """
    year = today.year if today.year % 2 == 0 else today.year - 1
    while True:
        day = datetime.date(year, 4, 1)
        day += datetime.timedelta(days=(1 - day.weekday()) % 7)   # 1st Tuesday
        if day <= today:
            return day
        year -= 2               # April of this even year has not happened yet


def crosses_spring_election(since, today):
    """True when a mayoral election falls in (since, today]."""
    return since < spring_election_on(today)


def load_prior(out_path):
    """The file this build is about to replace, or {}. Read for the carry rule;
    a missing or unreadable file simply means nothing is carried."""
    if not os.path.exists(out_path):
        return {}
    try:
        with open(out_path, encoding="utf-8") as f:
            prior = json.load(f)
    except ValueError:
        return {}
    return prior if isinstance(prior, dict) else {}


def carry_forward(prior, roster, statuses, layer_names, today):
    """Keep a previously witnessed name where this run could not ASK.

    `roster` is mutated in place. Every municipality that had a name last time
    and does not now produces a line, whether it is carried or dropped — a name
    leaving this file is the thing a reviewer must see, and the reason it left
    is the whole content of that event. Returns (carried_geoids, lines).
    """
    carried, lines = [], []
    for geoid in sorted(prior):
        was = prior[geoid]
        if not isinstance(was, dict) or was.get("withheld") or not was.get("name"):
            continue                    # nothing was being claimed; nothing to lose
        now = roster.get(geoid)
        if now is None:
            # A municipality that left the layer entirely is the scraper's
            # EXPECT_MUNIS gate, not this rule's. Say so and move on.
            lines.append("  DROPPED %s: %r left the file — the county's layer no "
                         "longer carries this municipality"
                         % (was.get("municipality", geoid), was["name"]))
            continue
        if not now.get("withheld"):
            continue                    # witnessed again this run
        muni = now.get("municipality") or was.get("municipality") or geoid
        status = statuses.get(geoid)

        def drop(why):
            lines.append("  DROPPED %s: %r is no longer shown — %s" % (muni, was["name"], why))

        if status not in CARRY_STATUSES:
            # Say each one in its own words. These are three different events
            # and collapsing them is what this change exists to undo.
            drop({
                "read": "the municipality's own page was read this run and did "
                        "not witness the name",
                "refused": "the municipality's site refused this client, and a "
                           "refusal is never carried",
                "missing": "the county layer's link to that page is dead, which "
                           "is the source answering rather than a failure to ask",
                "no-url": "the county layer publishes no page for it",
            }.get(status, "the scraper reported %r, which is not a carryable "
                          "verdict" % status))
            continue
        if layer_names.get(geoid) != was["name"]:
            drop("the county's own layer now names %r, so the carried name is "
                 "contradicted by current county data"
                 % (layer_names.get(geoid) or "nobody"))
            continue
        stamp = was.get("carriedFrom") or today.isoformat()
        try:
            since = datetime.date.fromisoformat(stamp)
        except (TypeError, ValueError):
            drop("its carriedFrom date %r does not parse, so nothing measures "
                 "how old it is" % stamp)
            continue
        if crosses_spring_election(since, today):
            drop("Wisconsin has held a spring election since %s, so the name is "
                 "no longer a claim about who holds the office" % stamp)
            continue
        age = (today - since).days
        if age > MAX_CARRY_DAYS:
            drop("last read %d days ago, past the %d-day limit"
                 % (age, MAX_CARRY_DAYS))
            continue
        kept = dict(was)
        kept["carriedFrom"] = stamp
        roster[geoid] = kept
        carried.append(geoid)
        lines.append("  NOT RE-READ %s: %r kept from the last shipped file, "
                     "unreachable this run, carried since %s (%d days)"
                     % (muni, was["name"], stamp, age))
    return carried, lines


def main():
    argv = sys.argv[1:]
    raw_path = argv[argv.index("--raw") + 1] if "--raw" in argv else DEFAULT_RAW
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    if not os.path.exists(raw_path):
        fail("no capture at %s — run wi/scripts/wi_municipal_executive_scraper.py first"
             % raw_path)
    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)
    munis = raw.get("municipalities") or {}
    if len(munis) != EXPECT_MUNIS:
        fail("the capture holds %d municipalities, expected %d"
             % (len(munis), EXPECT_MUNIS))

    roster, witnessed = {}, 0
    statuses, layer_names = {}, {}
    for code, rec in munis.items():
        if not code.isdigit() or len(code) != 5:
            fail("municipality code %r is not a 5-digit place code, so the GEOID "
                 "join cannot be built" % code)
        geoid = STATE_FIPS + code
        statuses[geoid] = rec.get("pageStatus")
        layer_names[geoid] = rec.get("layerName")
        entry = {
            "municipality": rec.get("municipality"),
            "office": rec.get("office"),
            "source": SOURCE_NAME,
            "sourceUrl": raw.get("source"),
        }
        if rec.get("witnessed"):
            witnessed += 1
            entry["name"] = rec.get("layerName")
            entry["witnessUrl"] = rec.get("pageUrl")
            # Contact rides the name — see the docstring.
            if rec.get("layerEmail"):
                entry["email"] = rec["layerEmail"]
            if rec.get("layerPhone"):
                entry["phone"] = rec["layerPhone"]
        else:
            entry["withheld"] = True
            entry["withheldWhy"] = rec.get("withheldWhy") or "not witnessed"
            # Only a link that actually answered.
            if rec.get("pageStatus") == "read" and rec.get("pageUrl"):
                entry["pageUrl"] = rec["pageUrl"]
        roster[geoid] = entry

    # THE FLOOR MEASURES THE SCRAPE, so it is checked before any carry: several
    # sites going quiet at once is the witness breaking, and failing here leaves
    # last week's correct file in place, which is the outcome a carry was after.
    if witnessed < MIN_WITNESSED:
        fail("only %d of %d executive names were witnessed on the municipality's "
             "own page (floor %d). Either several sites reshaped at once or the "
             "witness itself broke — read the scraper's per-municipality log "
             "before lowering this." % (witnessed, len(roster), MIN_WITNESSED))

    prior = load_prior(out_path)
    carried, carry_lines = carry_forward(
        prior, roster, statuses, layer_names, datetime.date.today())
    if len(carried) > MAX_CARRIED:
        fail("%d municipalities were unreachable and would be carried (%s) — "
             "that is this end failing, not theirs. The shipped file is left "
             "alone; read the scraper's per-municipality log before raising "
             "MAX_CARRIED (%d)."
             % (len(carried), ", ".join(roster[g]["municipality"] for g in carried),
                MAX_CARRIED))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    withheld = sum(1 for v in roster.values() if v.get("withheld"))
    print("build-wi-municipal-executives: OK — %d municipalities, %d name(s) "
          "shipped (witnessed on the municipality's own page), %d carried from "
          "the last shipped file, %d withheld -> %s"
          % (len(roster), witnessed, len(carried), withheld,
             os.path.relpath(out_path, os.getcwd())))
    if not prior:
        print("  no previously shipped roster — nothing to carry forward")
    for line in carry_lines:
        print(line)
    print("  withheld: %s" % ", ".join(sorted(
        v["municipality"] for v in roster.values() if v.get("withheld"))))
    print("  NOT CHECKED BY THIS BUILD: whether a witnessed name is still the "
          "sitting officer where the municipality's page is itself stale. The "
          "witness proves the county's layer and the municipality agree, which "
          "is the strongest available statement, not a guarantee.")


# ---------------------------------------------------------------- self-test
# Literal cases, no network and no capture. A carry rule that has never refused
# has not been tested, so every branch that DROPS a name has a case here and the
# controls beside it differ in one field.
NAMED = {"municipality": "Greenfield", "office": "City of Greenfield Mayor",
         "name": "Michael J. Neitzke", "email": "mayor@greenfieldwi.us",
         "source": SOURCE_NAME, "sourceUrl": "https://example.invalid/layer",
         "witnessUrl": "https://www.greenfieldwi.us/mayor"}
WITHHELD = {"municipality": "Greenfield", "office": "City of Greenfield Mayor",
            "source": SOURCE_NAME, "sourceUrl": "https://example.invalid/layer",
            "withheld": True, "withheldWhy": "not witnessed"}
GEOID = "5531175"
TODAY = datetime.date(2026, 9, 18)

#        label, prior record, this run's pageStatus, this run's layerName, carried?
CARRY_CASES = [
    ("unreachable, the layer agrees, carry begins today",
     NAMED, "unreachable", "Michael J. Neitzke", 1),
    ("unreachable, carried 59 days",
     dict(NAMED, carriedFrom="2026-07-21"), "unreachable", "Michael J. Neitzke", 1),
    ("unreachable, carried 61 days — past the limit",
     dict(NAMED, carriedFrom="2026-07-19"), "unreachable", "Michael J. Neitzke", 0),
    ("unreachable, but the layer now names somebody else",
     NAMED, "unreachable", "Somebody Else", 0),
    ("unreachable, but the layer names nobody at all",
     NAMED, "unreachable", None, 0),
    ("the page READ and did not witness — the election showing up",
     NAMED, "read", "Michael J. Neitzke", 0),
    ("the site refused this client",
     NAMED, "refused", "Michael J. Neitzke", 0),
    ("the layer's own link 404s",
     NAMED, "missing", "Michael J. Neitzke", 0),
    ("the layer publishes no page for it",
     NAMED, "no-url", "Michael J. Neitzke", 0),
    ("a verdict this builder does not know",
     NAMED, "something-new", "Michael J. Neitzke", 0),
    ("carriedFrom is not a date",
     dict(NAMED, carriedFrom="last week"), "unreachable", "Michael J. Neitzke", 0),
    ("the prior record was itself withheld — nothing to carry",
     WITHHELD, "unreachable", "Michael J. Neitzke", 0),
]

# The April boundary clears a carried name however fresh it is.
#        label, today, carriedFrom, carried?
ELECTION_CASES = [
    ("3 days old but across the April 2026 election",
     datetime.date(2026, 4, 9), "2026-04-06", 0),
    ("3 days old, the same side of it",
     datetime.date(2026, 4, 10), "2026-04-07", 1),
    ("an odd-numbered April, so no election has fallen",
     datetime.date(2027, 4, 10), "2027-03-20", 1),
]

# The dates themselves, against a calendar rather than against this function.
ELECTION_DATES = [
    (datetime.date(2026, 9, 18), datetime.date(2026, 4, 7)),
    (datetime.date(2026, 4, 7), datetime.date(2026, 4, 7)),   # election day itself
    (datetime.date(2026, 4, 6), datetime.date(2024, 4, 2)),   # the day before
    (datetime.date(2027, 1, 1), datetime.date(2026, 4, 7)),
    (datetime.date(2025, 6, 1), datetime.date(2024, 4, 2)),
]


def selftest():
    failures = []
    for label, rec, status, layer_name, expect in CARRY_CASES:
        roster = {GEOID: dict(WITHHELD)}
        carried, _ = carry_forward({GEOID: rec}, roster, {GEOID: status},
                                   {GEOID: layer_name}, TODAY)
        if len(carried) != expect:
            failures.append("%s: carried %d, expected %d" % (label, len(carried), expect))
        elif expect and roster[GEOID].get("name") != rec["name"]:
            failures.append("%s: carried but the name did not come back" % label)
        elif expect and "carriedFrom" not in roster[GEOID]:
            failures.append("%s: carried with no carriedFrom date" % label)
        elif not expect and roster[GEOID].get("name"):
            failures.append("%s: refused the carry but left a name behind" % label)

    for label, today, stamp, expect in ELECTION_CASES:
        roster = {GEOID: dict(WITHHELD)}
        carried, _ = carry_forward({GEOID: dict(NAMED, carriedFrom=stamp)}, roster,
                                   {GEOID: "unreachable"},
                                   {GEOID: NAMED["name"]}, today)
        if len(carried) != expect:
            failures.append("%s: carried %d, expected %d" % (label, len(carried), expect))

    for today, expect in ELECTION_DATES:
        got = spring_election_on(today)
        if got != expect:
            failures.append("spring_election_on(%s) = %s, expected %s"
                            % (today, got, expect))
        if got.weekday() != 1 or got.year % 2:
            failures.append("spring_election_on(%s) = %s, which is not a Tuesday "
                            "in an even year" % (today, got))

    # A carry keeps the date it BEGAN, so a second unreachable run does not
    # reset the clock and the age on the card stays real.
    roster = {GEOID: dict(WITHHELD)}
    carry_forward({GEOID: dict(NAMED, carriedFrom="2026-09-01")}, roster,
                  {GEOID: "unreachable"}, {GEOID: NAMED["name"]}, TODAY)
    if roster[GEOID].get("carriedFrom") != "2026-09-01":
        failures.append("a second carry restamped carriedFrom to today")

    # A municipality that witnesses again loses the marker by itself.
    roster = {GEOID: dict(NAMED)}
    carried, _ = carry_forward({GEOID: dict(NAMED, carriedFrom="2026-09-01")}, roster,
                               {GEOID: "read"}, {GEOID: NAMED["name"]}, TODAY)
    if carried or "carriedFrom" in roster[GEOID]:
        failures.append("a municipality that read again kept its carry marker")

    if failures:
        print("build-wi-municipal-executives selftest: FAILED", file=sys.stderr)
        for line in failures:
            print("  " + line, file=sys.stderr)
        sys.exit(1)
    n = len(CARRY_CASES) + len(ELECTION_CASES) + len(ELECTION_DATES) + 2
    print("build-wi-municipal-executives selftest: %d cases, every carry rule "
          "refuses what it is for" % n)


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        selftest()
    else:
        main()
