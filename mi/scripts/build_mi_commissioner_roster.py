#!/usr/bin/env python3
"""
Build mi/data/app/mi-commissioner-members.json — which commissioner holds each
Michigan county commissioner district, keyed by 3-digit county FIPS (the same
CountyFIPS mi-commissioner-districts.json carries) and read by mi/index.html's
County Commissioner District card.

WHAT IT ADDS. The district layer draws all 619 districts across 83 counties
and names nobody, because the only statewide name source is the state layer's
own Commissioner column and that column holds the November 2024 election
winners rather than the people in office now. This file names the commissioner
for the counties that publish the answer themselves. It is built in TRANCHES:
mi_commissioner_scraper.py's COUNTIES table is what yields today and its
PROBES table records every county tried and what stopped it.

THE COUNTY'S OWN PAGE WINS, ALWAYS. The scraper carries the state column's
name alongside each scraped one purely so this build can PRINT the
disagreement; nothing from that column reaches data/app. Measured 2026-09-13
across the first tranche's 76 seats: 53 agree exactly and 23 differ. Read by
hand, 7 of the 23 are a different person — Macomb 1, Muskegon 4, 5, 6 and 7,
Wayne 5 (the seat whose named commissioner died on 10 June 2025) and Wayne 8 —
and the other 16 are the same person written differently, including one typo
in the state column (Saginaw 4 "Sheldon Mattews" for Matthews). The run prints
the total and every difference; it does not try to sort them, because the test
that would (compare surnames) reads "Michael J. Howard II" against "Michael
Howard" as two people and "Matthews" against "Mattews" as two people too.

FOUR GATES, AND A COUNTY FAILING ANY OF THEM SHIPS NOTHING
------------------------------------------------------------
  1. The county's districts are exactly 1..N with no gaps and no repeats.
  2. N equals the seat count mi-commissioner-districts.json carries for that
     county's FIPS — so a redistricting or a board resize turns this run red
     instead of shipping a roster keyed to lines that moved.
  3. N equals the seat count the scraper's own table states, which is the
     second half of the same tripwire: the table is what a human read, the
     geometry is what the state publishes, and they have to agree.
  4. Every district names a person, and no two districts in one county name
     the same person — two identical names on one board is a parse collision,
     not a board.

A county that fails is named with its reason and simply does not appear; the
card falls back to what it already said. The floors below are floors, not
targets: one county changing CMS is ordinary and must not stop the other five
refreshing, a collapse must stop everything.

NO HOME ADDRESS AND NO PARTY FROM THE STATE. Eight of the counties added in
tranche 5 print members' HOME addresses — Barry, Cheboygan, Hillsdale, Ionia
and Osceola in full, street and city — and no parser reads an address field,
so none of it is in the cache and none can reach the card. Party ships only
where a county prints it on its own page (Muskegon and Barry); taking it from
the state column would attach a 2024 fact to a 2026 person.

THREE WAYS A DISTRICT CAN BE UNNAMED, and each gets its own sentence on the
card, because they are not the same statement to a reader:
  * the county's own row names no person (Monroe 2, a malformed directory row);
  * the county calls the seat VACANT in its own words (Ionia 3, Clinton 4 —
    Clinton carries its own Notice of Vacancy for that seat on the same page);
  * the county contradicts itself about who holds it (Lenawee 5, CONTRADICTED).

Usage:
    python3 mi/scripts/mi_commissioner_scraper.py      # refresh the cache
    python3 mi/scripts/build_mi_commissioner_roster.py
    python3 mi/scripts/build_mi_commissioner_roster.py --check
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)                       # mi/
APP_DATA_DIR = os.path.join(INSTANCE, "data", "app")
CACHE = os.path.join(HERE, ".cache", "mi_commissioner_roster.json")
DISTRICTS = os.path.join(APP_DATA_DIR, "mi-commissioner-districts.json")
OUT = os.path.join(APP_DATA_DIR, "mi-commissioner-members.json")

# Floors. Measured 2026-09-19 after tranche 7: 48 counties, 366 seats shipped.
# These are a COLLAPSE guard and nothing finer. Raise them when a tranche
# lands, never lower one to get past a failure.
#
# THE BASIS USED TO BE "any two counties may go dark" — 48 - 2 = 46 — AND THAT
# WAS THE DEFECT, not a cushion around it. On 2026-09-19 a transport failure
# left Delta and Otsego unread, the run produced exactly 46 counties, the test
# is `< MIN_COUNTIES`, and so a floor written to tolerate two dark counties
# passed the one event it should have stopped: #1052 proposed deleting both
# counties, fourteen named commissioners and two county pages, off pages that
# were serving normally. A GLOBAL COUNT CANNOT PROTECT A NAMED COUNTY; only
# the per-county carry-forward below can, and that is now what does it.
MIN_COUNTIES = 46
MIN_DISTRICTS = 330

# How long a county may ride its last-good record before this run refuses.
# Preserving is what stops a flaky fetch deleting real people; a ceiling is
# what stops preserving turning into a roster frozen for as long as nobody
# looks. 45 days is this instance's own precedent — the Detroit council
# scraper refuses an Archive snapshot older than the same figure, for the same
# reason, and a run that fails loudly is a human's cue to look at the source.
PRESERVE_MAX_AGE_DAYS = 45

# Fields a district row may carry, in card order. Anything else the scraper
# learns is dropped here rather than shipped unreviewed.
FIELDS = ("name", "role", "party", "phone", "email", "profileUrl")

# A DISTRICT WHOSE ROSTER ROW THE SAME COUNTY CONTRADICTS ON ANOTHER OF ITS OWN
# SURFACES. This is neither a parse failure nor a vacancy: the row names
# somebody, and the county has said in its own words on its own site that the
# naming is no longer true. Shipping the name would repeat exactly the error
# this pipeline exists to avoid — the state layer still names Wayne District
# 5's commissioner, who died in June 2025 — and calling the seat vacant would
# assert a filling nothing here can see, since a Michigan board vacancy is
# filled by appointment. So the district ships NAMED BY NOBODY with this reason
# on its card.
#
# THE ENTRY RETIRES ITSELF. It applies only while the roster still carries the
# recorded name at that district: when the county updates its own page the name
# no longer matches, the new name SHIPS, and the run prints a line telling
# whoever reads it to delete the entry. An entry naming a county that has left
# the roster FAILS the build rather than sitting unread, the property
# ACCEPTED_DROPS and EXPECTED_UNREACHABLE already have elsewhere in the fleet.
CONTRADICTED = {
    ("091", "5"): {
        "name": "Jim Daly",
        "why": "Lenawee's own News Flash of 10 September 2026 announces the "
               "death of Commissioner James \u201cJim\u201d Daly and says he "
               "represented District 5; the county's commissioner directory "
               "still lists him here. The two county surfaces disagree, so this "
               "app names nobody for this seat.",
        "source": "https://www.lenawee.mi.us/CivicAlerts.aspx?AID=3012",
        "recorded": "2026-09-15",
    },
}


def fail(msg):
    print("mi-commissioner-roster: FAIL — %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def days_since(stamp):
    """Whole days from an ISO date to today, or None if it cannot be read.

    Unreadable returns None rather than 0 so a malformed stamp cannot silently
    read as "fetched today" and keep a stale county alive past the ceiling;
    the caller treats None as "no age known" and the stamp itself prints.
    """
    try:
        then = datetime.strptime(stamp[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return (datetime.now(timezone.utc) - then).days


def load(path, what):
    try:
        with open(path) as handle:
            return json.load(handle)
    except OSError as exc:
        fail("no %s at %s (%s)" % (what, path, exc))


def seats_from_geometry():
    """How many districts the shipped geometry draws per county FIPS."""
    seats = {}
    for feat in load(DISTRICTS, "commissioner districts")["features"]:
        props = feat["properties"]
        seats.setdefault(props["CountyFIPS"], set()).add(int(props["District"]))
    return {fips: nums for fips, nums in seats.items()}


def main():
    check_only = "--check" in sys.argv[1:]

    cache = load(CACHE, "commissioner cache — run mi_commissioner_scraper.py first")
    geometry = seats_from_geometry()
    # The roster as it stands, read once: both the zero-district check and the
    # carry-forward below ask what we already have for a county.
    shipped_pre = {}
    if os.path.exists(OUT):
        with open(OUT) as handle:
            shipped_pre = json.load(handle)

    directory, skipped, short = {}, [], []
    withheld, retire, vacant = {}, [], {}
    agree, differ = 0, 0
    for fips in sorted(cache.get("counties", {})):
        entry = cache["counties"][fips]
        county = entry.get("county") or fips
        keyed = entry.get("districts") or {}
        drawn = geometry.get(fips)
        if not drawn:
            skipped.append((county, "no district geometry for FIPS %s" % fips))
            continue
        want = set(str(n) for n in drawn)
        stray = sorted(set(keyed) - want, key=lambda k: (not k.isdigit(), k))
        if stray:
            skipped.append((county, "names district(s) %s the geometry does not draw "
                                    "(it draws %s)"
                            % (stray, sorted(want, key=int))))
            continue
        # A COUNTY SHORT OF ITS OWN SEAT COUNT SHIPS WHAT IT PUBLISHES, and the
        # card states the shortfall. Refusing the county instead conceals every
        # name it DOES publish in order to avoid stating one absence, which is
        # backwards: Monroe publishes eight of nine and the ninth is missing
        # because the county's own directory row for it names a district where
        # a person should be. This is Illinois's Alexander decision — the
        # roster block carries `seats` beside its members and the shortfall
        # renders in the same words — applied to a districted board.
        # Drop any district this county contradicts on its own other surface.
        # Done BEFORE the shortfall maths so a withheld seat counts as missing
        # exactly like a row that named nobody, and the card says which.
        for (cf, cd), note in sorted(CONTRADICTED.items()):
            if cf != fips or cd not in keyed:
                continue
            got = (keyed[cd].get("name") or "").strip()
            if got == note["name"]:
                del keyed[cd]
                withheld[(cf, cd)] = note
            else:
                retire.append((county, cd, note["name"], got))
        # A DISTRICT THE COUNTY ITSELF CALLS VACANT. This is a third case and
        # not either of the other two: the row is not malformed (Monroe) and no
        # second county surface contradicts it (Lenawee) — the county's own
        # board page states in its own words that nobody holds the seat. Ionia
        # District 3 is the first, and its page carries the previous
        # commissioner's whole entry commented out beneath the word, which is
        # why the parser strips comments before reading anything.
        for district in sorted(keyed, key=lambda k: (not k.isdigit(), k)):
            if keyed[district].get("vacant"):
                del keyed[district]
                vacant[(fips, district)] = county

        missing = sorted(want - set(keyed), key=int)
        if entry.get("seats") != len(drawn):
            skipped.append((county, "scraper table says %s seats, geometry draws %d"
                            % (entry.get("seats"), len(drawn))))
            continue
        names = [(rec.get("name") or "").strip() for rec in keyed.values()]
        if not all(names):
            skipped.append((county, "%d district(s) name nobody"
                            % sum(1 for n in names if not n)))
            continue
        if len(set(names)) != len(names):
            skipped.append((county, "two districts name the same person — a parse "
                                    "collision, not a board"))
            continue

        districts = {}
        for district, rec in keyed.items():
            row = {}
            for field in FIELDS:
                value = rec.get(field)
                if value not in (None, ""):
                    row[field] = value
            districts[district] = row
            state_name = (rec.get("stateColumnName") or "").strip()
            if not state_name:
                continue
            if state_name == row["name"]:
                agree += 1
            else:
                # Two buckets, not three. A surname test looks like it can
                # separate a respelling from a replacement and cannot: it reads
                # "Michael J. Howard II" against "Michael Howard" as two people
                # (the suffix is the last token) and "Sheldon Matthews" against
                # the state's "Sheldon Mattews" the same way. Every difference
                # is printed and the split is left to whoever reads the run.
                differ += 1
                print("  %s %s: county says %r, the state layer still says %r"
                      % (county, district, row["name"], state_name))
        directory[fips] = {
            "county": county,
            "seats": len(drawn),
            "sourceUrl": entry.get("sourceUrl"),
            "districts": districts,
            # WHEN THIS COUNTY'S PAGE WAS ACTUALLY READ, which is the scraper's
            # per-county stamp and not this run's clock: a county carried
            # forward keeps the older date, and that difference is the whole
            # point. CLAUDE.md's rule is that a card must never print a
            # verification date for a source it did not verify, and no card
            # prints this yet — it is here so the ceiling above has something
            # true to measure.
            # Only ever the scraper's own per-county stamp. A cache entry
            # written before that field existed carries none, and none is
            # written here rather than the run's clock standing in for it.
            "readAt": entry.get("readAt"),
        }
        if directory[fips]["readAt"] is None:
            del directory[fips]["readAt"]
        # Read again, so it is no longer riding a preserved record.
        if missing:
            # Named so the card can say which district, rather than only that
            # the count is short.
            directory[fips]["unnamedDistricts"] = missing
            why = dict((cd, note["why"]) for (cf, cd), note in withheld.items()
                       if cf == fips and cd in missing)
            for (cf, cd), name in sorted(vacant.items()):
                if cf == fips and cd in missing:
                    why[cd] = ("%s County's own board page lists this district as "
                               "vacant. A Michigan board vacancy is filled by "
                               "appointment, and the county's page names no "
                               "appointee." % name)
            if why:
                # A per-district reason, because the two cases a reader meets
                # are not the same fact: Monroe's row carries no name, and
                # Lenawee's carries one the county has contradicted. A card
                # with no specific reason falls back to the generic sentence.
                directory[fips]["unnamedWhy"] = why
            short.append((county, len(drawn), missing))

    for county, why in skipped:
        print("  skipped %s — %s" % (county, why))
    for county, seats, missing in short:
        # Two different absences, so two different sentences: a row that names
        # nobody, or a row the county contradicts elsewhere on its own site.
        held = sorted(cd for (cf, cd), _n in withheld.items()
                      if cd in missing
                      and directory.get(cf, {}).get("county") == county)
        empty = sorted(cd for (cf, cd), nm in vacant.items()
                       if cd in missing and nm == county)
        bare = [d for d in missing if d not in held and d not in empty]
        parts = []
        if bare:
            parts.append("district(s) %s named by nobody on the county's own page"
                         % ", ".join(bare))
        if empty:
            parts.append("district(s) %s the county's own page calls vacant"
                         % ", ".join(empty))
        if held:
            parts.append("district(s) %s withheld, the county contradicting its "
                         "own roster" % ", ".join(held))
        print("  %s ships %d of %d \u2014 %s, stated on the card"
              % (county, seats - len(missing), seats, "; ".join(parts)))

    for (cf, cd), note in sorted(withheld.items()):
        print("  withheld %s district %s \u2014 the roster names %r, recorded "
              "%s, contradicted by %s"
              % (cf, cd, note["name"], note["recorded"], note["source"]))
    for county, cd, was, now in retire:
        print("  RETIRE the CONTRADICTED entry for %s district %s: it records %r "
              "and the county now names %r, which ships" % (county, cd, was, now))
    # An entry naming a county no longer in the roster is unread forever, so it
    # fails rather than calcifying.
    orphans = sorted(k for k in CONTRADICTED if k[0] not in directory)
    if orphans:
        fail("CONTRADICTED names %s, absent from the roster \u2014 retire the "
             "entry" % ", ".join("%s/%s" % k for k in orphans))

    # A COUNTY READ THAT PARSED TO NOTHING IS A FAILED READ, NOT AN EMPTY BOARD.
    #
    # MCL 46.401(1) puts every Michigan board at 5..21 seats, so zero is never
    # the county's own answer. Left alone, such a county reaches here with no
    # districts and every gate above passes it — the county count does not
    # move and the total falls by one board — and the card then states
    # "0 of 5 — named by nobody on the county's own page" about a county whose
    # page names all five. That is an affirmative false claim about a public
    # body, and it is the worse half of the defect #1052 exposed.
    #
    # THE FIRST FIX HERE FAILED THE RUN, AND THAT WAS WRONG (measured the same
    # hour). The full run of 2026-09-19 had Midland parse to zero from a page
    # that answered; re-read on its own it gave 7 of 7 in 120,480 bytes, so the
    # zero was a bad read and not a broken parser. Failing would have turned
    # the weekly job red on a flake, and a job that cries wolf weekly is one a
    # reviewer learns to skim — the same reasoning the Detroit PR body was
    # rewritten on. So these join the carry-forward below and are printed every
    # run; a parser that is genuinely broken stops being read for good, and the
    # staleness ceiling is what turns that into a failure.
    emptied = [fips for fips, entry in directory.items()
               if not entry.get("districts")]
    for fips in emptied:
        county = directory[fips].get("county") or fips
        del directory[fips]
        if fips in shipped_pre:
            cache.setdefault("unread", []).append(
                {"fips": fips, "county": county, "kind": "parsed-zero",
                 "why": "the page answered and the parser matched no district"})
        else:
            # Nothing to carry forward: a county new to the table whose parser
            # has never worked. Silence would ship the roster without it and
            # let the floors decide, which is how a county stays unnoticed.
            fail("%s parsed to ZERO districts from a page that answered and has "
                 "no shipped record to fall back on — fix its parser" % county)

    # ---------------------------------------------------------------- PRESERVE
    # A COUNTY THE SCRAPER COULD NOT READ KEEPS ITS LAST-GOOD RECORD.
    #
    # Adam's ruling, 2026-09-19: "Preserve data we have already fetched." A
    # host that refuses us, or a connection that drops, is not telling us to
    # delete officeholders we fetched legitimately while it was serving —
    # and deleting them costs a reader the answer while gaining the publisher
    # nothing. Michigan was the last of the three statewide instances to still
    # delete: Illinois has carried PRESERVABLE since Will, Wisconsin re-asks an
    # unreachable verdict, and Iowa's builder was fixed the same day after it
    # dropped Bremer and Hamilton.
    #
    # THE SCRAPER'S `unread` LIST IS WHAT MAKES THIS SAFE. Carrying a county
    # forward because it is missing from the cache would also carry one that
    # was deliberately retired from the COUNTIES table, forever. A county is
    # preserved only where the scraper says it TRIED and did not get an answer,
    # so a county removed from that table still leaves the roster normally.
    #
    # A county READ that parsed to nothing is deliberately NOT here: it is in
    # neither `unread` nor `directory`, so it trips the floors below and the
    # run fails. That is the parser-break case, and preserving it quietly is
    # exactly how a county's names would freeze unnoticed.
    shipped = shipped_pre
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    preserved, stale = [], []
    for row in cache.get("unread", []):
        fips = row.get("fips")
        if fips in directory or fips not in shipped:
            continue
        entry = dict(shipped[fips])
        # `readAt` IS NEVER INVENTED. It means "this page was read on this
        # date", so a county that was not read keeps whatever it had, and a
        # county carried forward before this field existed carries none at all.
        # The first draft fell back to the run's own clock, which stamped three
        # challenged counties with today — the precise false claim the field
        # was added to prevent.
        #
        # THE CEILING THEREFORE MEASURES `preservedSince`, not `readAt`: how
        # long this county has been riding its last-good record is both the
        # thing that matters and the thing that is knowable, and it is set the
        # first run a county is carried and cleared the moment one is read.
        entry["preservedSince"] = entry.get("preservedSince") or today
        directory[fips] = entry
        since = entry["preservedSince"]
        preserved.append((entry.get("county") or fips, row.get("why") or "",
                          entry.get("readAt"), since))
        age = days_since(since)
        if age is not None and age > PRESERVE_MAX_AGE_DAYS:
            stale.append((entry.get("county") or fips, since, age))
    for county, why, read_at, since in sorted(preserved):
        print("  %s PRESERVED — not read this run (%s); carried since %s, last "
              "actually read %s"
              % (county, why, since, read_at or "before this field existed"))
    if stale:
        fail("%s — carried forward for more than %d days, so the source needs a "
             "human rather than another week of last-good data"
             % ("; ".join("%s carried since %s (%d days)" % r
                          for r in sorted(stale)), PRESERVE_MAX_AGE_DAYS))

    total = sum(len(e["districts"]) for e in directory.values())
    if len(directory) < MIN_COUNTIES:
        fail("only %d counties resolved, floor is %d" % (len(directory), MIN_COUNTIES))
    if total < MIN_DISTRICTS:
        fail("only %d districts resolved, floor is %d" % (total, MIN_DISTRICTS))

    print("  state column: %d of %d seats agree exactly, %d differ (printed above)"
          % (agree, agree + differ, differ))

    payload = {fips: directory[fips] for fips in sorted(directory)}
    rendered = json.dumps(payload, indent=1, sort_keys=True) + "\n"

    if check_only:
        current = ""
        if os.path.exists(OUT):
            with open(OUT) as handle:
                current = handle.read()
        if current != rendered:
            fail("%s is stale — re-run mi_commissioner_scraper.py and this builder"
                 % os.path.relpath(OUT, os.path.dirname(INSTANCE)))
        print("mi-commissioner-roster: OK — %d counties, %d districts, shipped file matches"
              % (len(payload), total))
        return 0

    with open(OUT, "w") as handle:
        handle.write(rendered)
    print("mi-commissioner-roster: wrote %d counties, %d districts -> %s (%s)"
          % (len(payload), total, os.path.relpath(OUT, os.path.dirname(INSTANCE)),
             datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
