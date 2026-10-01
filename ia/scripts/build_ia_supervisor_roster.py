#!/usr/bin/env python3
"""
Build data/app/ia-supervisor-members.json -- which supervisor holds each county
supervisor district, keyed by 3-digit county FIPS (the same key
ia-county-board-directory.json uses) and read by ia/index.html's County
Supervisor District card.

WHAT IT IS FOR
---------------
data/app/ia-county-officers.json names every county's board but cannot say who
holds WHICH district, because no Iowa publisher attaches a district to a
supervisor's name (four statewide routes measured closed -- see
ia_supervisor_district_scraper.py). This file carries that one missing number
for the counties that publish it themselves, so the district card can name the
supervisor a reader actually elected instead of linking away to a board page.

PLAN 3 COUNTIES ONLY. Iowa Code 331.206: under plan 1 a county elects at large
with no districts, and under plan 2 supervisors are elected COUNTYWIDE and
merely reside in a district. Only under plan 3 does a district elect its own
supervisor, so only there does naming one answer a question the County card's
list does not already answer. Keying a plan 2 district would read as
district-based election, which is precisely what plan 2 is not.

THE PEOPLE COME FROM THE SHIPPED ROSTER, NOT FROM THE COUNTY PAGE. The scraper
recovers only a NUMBER; every name and party here is carried over from
data/app/ia-county-officers.json, which was itself gated against Iowa Code
331.201's legal board sizes and against the seat count in the shipped district
geometry. So a county page cannot introduce a person, only place one -- and
this builder re-checks that placement rather than trusting it:

  * every district 1..N is filled, exactly once,
  * the set of people placed is EXACTLY the set the roster names, and
  * N equals NUMDISTRICTS in data/app/ia-supervisor-districts.json.

A county failing any of these ships nothing and is named in the run's output;
its supervisors keep the unkeyed listing they already have on the County card.
NEVER infer a district from the order a page lists people in -- that is the one
failure mode that produces a complete, confident, wrong answer.

NO PHONE RIDES A SUPERVISOR ROW. Every one of these 17 counties publishes ONE
number for the whole board -- measured, one distinct value per county across
all 67 keyed districts -- which is the courthouse board office, not a
supervisor's line. build_ia_county_officers.py already hoists that number out
of its own member rows into `boardPhone`; this file carries the same field at
COUNTY level so the district card can print it as "Board office" instead of
presenting the switchboard as the direct line of whichever supervisor the
reader's district elected. A per-person number is a different fact and would
have to arrive from a source that publishes one; the officer roster this reads
from carries none, so none can leak through.

A COUNTY MAY ANSWER THE QUESTION IN A LETTER RATHER THAN ON A PAGE. Four
statewide routes are measured closed and some counties publish no page that
names a district at all, so this project writes to the county auditor and asks.
An answer that arrives by e-mail is a county official stating, in writing, which
supervisor each of their own districts elects -- which is a better source than a
board page, not a worse one. It rides CORRESPONDENCE_ROSTERS below and flows
through EXACTLY the three re-checks above: the reply supplies only the pairing,
the names and parties still come from the gated officer roster, and a reply that
names somebody the roster does not, or misses a district, ships nothing. What it
does NOT get is a sourceUrl, because a letter is not a page, and the card
therefore dates it and says where it came from instead of claiming a page this
app re-reads every week. Nothing here re-reads a letter: the entry is dated, it
will go out of date, and that is on the card.

A ROBOTS REFUSAL IS NOT AN OUTAGE. The scraper reads each host's robots.txt
before its first fetch and caches {"robotsRefused": <why>} for a county whose
own file says this client may not read it. That is the site's answer and it
does not heal by next Saturday, so the drop guard below would otherwise fail
this job every week for ever. It is excused -- but only where the refusal is
BOTH reported by this run and recorded in ROBOTS_REFUSED_PRESERVED with what was
measured, because a county newly reported refused is also what a bug in the
robots read looks like, and the floors cannot see two counties leave.

Usage:
    python3 ia/scripts/ia_supervisor_district_scraper.py   # refresh the cache
    python3 ia/scripts/build_ia_supervisor_roster.py
    python3 ia/scripts/build_ia_supervisor_roster.py --check
"""

import datetime as dt
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache",
                     "ia_supervisor_districts_roster.json")

DISTRICTS = os.path.join(APP_DATA_DIR, "ia-supervisor-districts.json")
OFFICERS = os.path.join(APP_DATA_DIR, "ia-county-officers.json")
OUT = os.path.join(APP_DATA_DIR, "ia-supervisor-members.json")

# Floor, not a target: 20 of the 39 plan 3 counties published a keyable page on
# 2026-08-28 (the rest 403, sit behind a captcha, or name no district at all).
TODAY = dt.date.today().isoformat()

# THE FLOORS WERE 12 COUNTIES AND 40 DISTRICTS AND THEY ARE NOW 2 AND 8, WHICH
# IS A GUARD BEING RE-AIMED RATHER THAN LOWERED, AND THE DIFFERENCE MATTERS.
# The old pair floored how many counties this builder keys. That quantity
# collapsed on 2026-10-01 for a measured reason and not because anything broke:
# a county's own district NUMBER turned out not to be this instance's district
# number (NUMBERING_CHECKED below), so the 21 counties that were shipping a
# keyed board were shipping it on an unchecked assumption and three of the four
# counties measured that day had it wrong. What ships now is the counties whose
# numbering has been CHECKED, which is a different quantity with its own floor,
# and the two figures must never be confused: a run that keys twenty counties on
# trust would clear the old floor and would be exactly the defect.
MIN_COUNTIES = 4
MIN_DISTRICTS = 16

# WHETHER A COUNTY'S OWN DISTRICT NUMBER IS THIS INSTANCE'S DISTRICT NUMBER.
#
# This builder joins people to geometry on a NUMBER: the county says "District
# 3" and that name goes on district 3 of ia-supervisor-districts.json, which is
# the Legislative Services Agency's statewide layer. NOTHING HAD EVER CHECKED
# THAT THE TWO NUMBERINGS ARE THE SAME NUMBERING, and measured on 2026-10-01
# they usually are not: of the first four counties checked, three disagreed.
# The agency numbers each county's districts in its own order, this instance
# carries that number straight through, and the county's own page numbers them
# differently -- so a reader was shown the wrong supervisor.
#
# A COUNTY SHIPS A KEYED BOARD ONLY IF IT IS IN THIS TABLE. That is the whole
# mechanism: an entry carries the county's own number -> this layer's number,
# measured, with the date and the witness. An absent county keeps its
# supervisors on the County card, unkeyed, which is true either way.
#
# EACH ENTRY IS AUDITED AGAINST THIS RUN: it FAILS when the county is not a plan
# 3 county in the shipped geometry, when its map is not a bijection of the
# county's 1..N onto the layer's own district ids, or when the geometry seats a
# different number of districts than the map pairs. A map that stops describing
# the shipped layer must be re-measured rather than inherited.
#
# HOW EACH ONE WAS MEASURED, cheapest first. Where a county's page names a TOWN
# or TOWNSHIP per district, the test is one page read plus a point-in-polygon
# test on that place's own published centroid -- no map and no georeferencing.
# Where it publishes only a district map, the map is georeferenced against its
# own town labels rather than traced (ia/scripts/check_county_district_numbering.py).
# Only places are recorded: a supervisor's street address is never written down
# here or anywhere else in this repository.
#
# BUTLER IS DELIBERATELY ABSENT AND IS THE REASON THIS TABLE DEMANDS A
# BIJECTION. Thirteen of its fifteen named townships move, consistently, as
# though county 1 <-> layer 2 with 3 fixed -- but Ripley Township, which the
# county puts in its District 3, lies WHOLLY inside the layer's district 1,
# sampled 144 of 144 interior points. A renumbering cannot do that, so the two
# sides are not describing one plan and the county has to be asked which is
# current. A partial map would have shipped two wrong districts out of three.
NUMBERING_CHECKED = {
    "Howard": {
        "map": {"1": "1", "2": "2", "3": "3"},
        "checked": "2026-10-01",
        "witness": "the county's own board page names a residence town beside "
                   "each supervisor; Cresco, Lime Springs and Riceville each "
                   "lie wholly inside one district and all three land in the "
                   "district the county numbers them",
    },
    "Pocahontas": {
        "map": {"1": "2", "2": "1", "3": "3", "4": "5", "5": "4"},
        "checked": "2026-10-01",
        "witness": "the county's own board page composes every district out of "
                   "named townships and communities; 15 township centroids and "
                   "8 city centroids agree on this pairing with no "
                   "contradiction, Laurens settling district 2 and the city of "
                   "Pocahontas district 3",
    },
    "Monona": {
        "map": {"1": "2", "2": "1", "3": "3"},
        "checked": "2026-10-01",
        "witness": "the county's own supervisor-district map states in TEXT, "
                   "per district, every township and city that district "
                   "contains -- nothing on the drawing is read -- and those "
                   "twenty places are exactly the twenty county subdivisions "
                   "the census publishes for the county, so the statement "
                   "partitions the county with nothing left over; all twenty "
                   "interior points agree on this pairing, and the map's own "
                   "legend names the same three supervisors in the same three "
                   "districts as this roster",
    },
    "Lyon": {
        "map": {"1": "5", "2": "4", "3": "1", "4": "3", "5": "2"},
        "checked": "2026-10-01",
        "witness": "the county writes its own PRECINCT numbers into each "
                   "member's title (District 1 - Precinct 9,10, and so on "
                   "through all ten), and this instance's own precinct layer "
                   "names those precincts; each of the ten lies wholly inside "
                   "one of this layer's districts and all five are spoken for, "
                   "with six towns' census centroids independently agreeing on "
                   "every pairing they can speak to",
    },
}

# WHAT A COUNTY TOLD US IN WRITING.
#
# Each entry is one county official's own answer to this project's ask, naming
# which supervisor each district elects. The pairing is all it supplies: every
# name and party below is still looked up in ia-county-officers.json, and the
# three re-checks in the loop are applied unchanged -- so an entry that names a
# person the gated roster does not name, or that misses a district, ships
# nothing rather than overriding anything.
#
# AN ENTRY IS AUDITED AGAINST THIS RUN, like every other recorded exception in
# this repo. It FAILS when the county is not a plan 3 county in the shipped
# geometry (orphaned), and it FAILS when the scraper has started keying the
# county from its own page (stale -- a published page is the better source and
# the letter should be retired in favour of it).
CORRESPONDENCE_ROSTERS = {
    "Osceola": {
        "districts": {
            "1": "LeRoy DeBoer",
            "2": "Jayson Vande Hoef",
            "3": "Mike Schulte",
            "4": "Jeff Loring",
            "5": "Jerry Helmers",
        },
        "readOn": "2026-10-01",
        "why": (
            "Osceola County Auditor Rochelle Van Tilburg, by e-mail, "
            "2026-10-01, answering this project's ask: 'Following is the "
            "supervisor by district' followed by all five pairings. The "
            "county's own board page lists its five supervisors and attaches "
            "no district to any of them, which is why it was asked."),
        "cardNote": (
            "Osceola County's auditor gave this pairing by e-mail on 1 "
            "October 2026; the county publishes no page that names a "
            "district, so this app has no page to re-read."),
    },
    "Ida": {
        # Transcribed from the reply exactly as the county wrote it, INCLUDING
        # "Devlun Whiteing", which the gated roster spells "Devlun P.
        # Whiteing". The resolution below turns that into the roster's own
        # spelling, prints the join every run, and refuses an ambiguous one.
        "districts": {
            "1": "Creston Schubert",
            "2": "Kyle Rohlk",
            "3": "Devlun Whiteing",
        },
        "readOn": "2026-10-01",
        "why": (
            "Ida County Auditor Kristy Gilbert, by e-mail, 2026-10-01, "
            "answering this project's ask: 'Here is their district "
            "information.' followed by all three pairings. The county's own "
            "board page names its three supervisors and attaches no district "
            "to any of them, which is why it was asked."),
        "cardNote": (
            "Ida County's auditor gave this pairing by e-mail on 1 October "
            "2026; the county publishes no page that names a district, so "
            "this app has no page to re-read."),
    },
    "Sioux": {
        # Transcribed from the reply exactly as the county wrote it, INCLUDING
        # "Carl Vande Weerd", which the gated roster spells "Carl L. Vande
        # Weerd". The resolution below turns that into the roster's own
        # spelling, prints the join every run, and refuses an ambiguous one.
        "districts": {
            "1": "John Degen",
            "2": "Jerry Muilenburg",
            "3": "Dan Altena",
            "4": "Carl Vande Weerd",
            "5": "Craig Hoftyzer",
        },
        "readOn": "2026-10-01",
        "why": (
            "The Sioux County Auditor's office, by e-mail, 2026-10-01, "
            "answering this project's ask: a table headed '2026 Board of "
            "Supervisors' pairing each of the five names with 'Sioux County "
            "District <n>'. Sent from joevt@siouxcounty.org, copying the "
            "auditor@siouxcounty.org account the ask was addressed to. "
            "Sioux's own host fronts robots.txt with a 202 sgcaptcha "
            "challenge, which is an access control, so this project reads no "
            "page of that site at all -- the letter is the only route to the "
            "pairing, and there is no page for a weekly run to re-read."),
        "cardNote": (
            "Sioux County's auditor's office gave this pairing by e-mail on 1 "
            "October 2026; this app reads no page of the county's own site, "
            "so it has no page to re-read."),
    },
}

# A ROBOTS REFUSAL IS A RECORDED DROP -- NOT AN OUTAGE, AND NOT A BLANKET
# EXCUSE EITHER.
#
# The scraper reads each host's robots.txt before its first fetch and writes
# {"robotsRefused": <why>} for a county it may not read. That is the site's own
# answer and it does not heal by next Saturday, so the drop guard below would
# otherwise fail this job every week for ever, or be dulled into ignoring every
# county that vanishes.
#
# But a county the scraper has JUST STARTED reporting as refused is also
# exactly what a bug in the robots read looks like -- and the floors above
# cannot see it: they are sized for the file, so two or three counties
# disappearing clears them with room to spare. That is the Grundy shape, and
# the whole reason this file reads the roster it is about to overwrite.
#
# So a refusal excuses a drop only where it is BOTH reported by this run AND
# recorded here with what was measured and when. Every entry prints on every
# run; an entry whose county keys again is STALE and FAILS, and one naming a
# county that is not a plan 3 county any more is ORPHANED and FAILS. Neither
# can sit here quietly after it stops being true.
ROBOTS_REFUSED_PRESERVED = {
    "Bremer": {
        "why": (
            "2026-09-13: bremercounty.iowa.gov and www.bremercounty.iowa.gov "
            "both answer HTTP 500 on /robots.txt -- five reads over 40 s -- "
            "while the site's own home page serves 178 KB. RFC 9309 and this "
            "project file a 5xx on robots.txt as disallow-all, so a broken "
            "endpoint on a working site costs the county until it is fixed. "
            "Re-verified 2026-09-19 on both spellings, still 500. Retires "
            "itself on the run that URL answers."),
        "cardNote": (
            "Bremer County's robots.txt has not been readable since 13 "
            "September 2026, which this app reads as a refusal, so it no "
            "longer re-reads the county's board page."),
        "seedReadOn": "2026-08-28",
    },
    "Hamilton": {
        "why": (
            "2026-09-13: hamiltoncounty.iowa.gov redirects /robots.txt to its "
            "CMS vendor's per-tenant path, "
            "cms2.revize.com/revize/hamiltonia/robots.txt -- Hamilton's own "
            "file rather than Revize's -- which gives five named search-engine "
            "tokens Allow: / and `*` Disallow: /. No token this repo sends is "
            "a vendor crawler token, so `*` binds us. Re-verified 2026-09-19 "
            "on both spellings, still Disallow."),
        "cardNote": (
            "Hamilton County's robots.txt asks automated clients not to read "
            "the site, so this app no longer re-reads the county's board "
            "page."),
        "seedReadOn": "2026-08-28",
    },
}

# THE SEED DATES ARE MEASURED, NOT ASSUMED. Both counties' records were last
# written to ia-supervisor-members.json by commit bce3108 on 2026-08-28 -- the
# last weekly run that read them before the refusals were recorded -- so that
# is the day the shipped names were last confirmed against the county's own
# page, and it is what a preserved card shows a reader. After the first run
# under this change the date rides the file itself as `readOn` and these seeds
# are never consulted again.


def load(path, what):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError as e:
        raise RuntimeError("no %s at %s (%s)" % (what, path, e))


def main():
    check_only = "--check" in sys.argv[1:]

    feats = load(DISTRICTS, "supervisor districts")["features"]
    fips_by_county, seats_by_county, plan_by_county = {}, {}, {}
    for feat in feats:
        p = feat["properties"]
        fips_by_county[p["COUNTY"]] = p["FIPS"]
        seats_by_county[p["COUNTY"]] = p.get("NUMDISTRICTS")
        plan_by_county[p["COUNTY"]] = p.get("PLANTYPE")

    officers = load(OFFICERS, "county officers")
    board_by_county, board_phone_by_county = {}, {}
    for rec in officers.values():
        if rec.get("supervisors"):
            board_by_county[rec["county"]] = rec["supervisors"]
        if rec.get("boardPhone"):
            board_phone_by_county[rec["county"]] = rec["boardPhone"]

    cache = load(CACHE, "supervisor district cache -- run the scraper first")

    # CORRESPONDENCE_ROSTERS joins the cache rather than bypassing it, so an
    # answer given in a letter is gated exactly as one read off a page is.
    plan3 = {c for c, plan in plan_by_county.items() if plan == "PLAN 3"}

    # NUMBERING_CHECKED is audited before anything is keyed, so a map that has
    # stopped describing the shipped layer stops the build rather than silently
    # placing a name in a district that is not there.
    layer_ids = {}
    for feat in feats:
        p = feat["properties"]
        layer_ids.setdefault(p["COUNTY"], set()).add(p["DISTRICT"])
    for county in sorted(NUMBERING_CHECKED):
        rec = NUMBERING_CHECKED[county]
        if county not in plan3:
            raise RuntimeError(
                "NUMBERING_CHECKED names %s, which is not a plan 3 county in the "
                "shipped geometry -- the entry is orphaned and should go" % county)
        own, theirs = sorted(rec["map"]), sorted(rec["map"].values())
        if own != [str(i) for i in range(1, len(own) + 1)]:
            raise RuntimeError(
                "NUMBERING_CHECKED[%s] keys %s, which is not the county's own "
                "1..N" % (county, own))
        if sorted(set(theirs)) != theirs:
            raise RuntimeError(
                "NUMBERING_CHECKED[%s] sends two of the county's districts to "
                "one of this layer's -- a map is a bijection or it is not a "
                "measurement" % county)
        if set(theirs) != layer_ids.get(county, set()):
            raise RuntimeError(
                "NUMBERING_CHECKED[%s] pairs this layer's %s, but the shipped "
                "geometry draws %s for that county. Re-measure rather than "
                "inherit." % (county, theirs, sorted(layer_ids.get(county, ()))))
        print("  numbering      %-12s county %s -> this layer %s (checked %s)"
              % (county, ",".join(own), ",".join(rec["map"][d] for d in own),
                 rec["checked"]), file=sys.stderr)
    for county in sorted(CORRESPONDENCE_ROSTERS):
        told = CORRESPONDENCE_ROSTERS[county]
        if county not in plan3:
            raise RuntimeError(
                "CORRESPONDENCE_ROSTERS names %s, which is not a plan 3 county in "
                "the shipped geometry -- the entry is orphaned and should go"
                % county)
        if (cache.get(county) or {}).get("districts"):
            raise RuntimeError(
                "CORRESPONDENCE_ROSTERS names %s, but the scraper keyed its own "
                "page this run -- the entry is stale. Retire it: a page the county "
                "publishes is the better source and is re-read every week."
                % county)
        # THE TABLE IS A TRANSCRIPT OF THE LETTER, NOT OF THE ROSTER, so it
        # may spell a name the way the county's own auditor typed it -- Ida
        # wrote "Devlun Whiteing" where the gated roster has "Devlun P.
        # Whiteing". Silently accepting either would be a normalisation nobody
        # can see; silently FAILING would discard a county's own answer over a
        # middle initial. So a name the roster does not carry is joined on a
        # UNIQUE surname, the join is PRINTED on every run, and an ambiguous
        # or unmatched one stops the build. The ROSTER'S spelling is what
        # ships, because the roster is the gated source for who these people
        # are and the letter is the source for which district each holds.
        board = board_by_county.get(county) or []
        names = {m["name"] for m in board}
        resolved = {}
        for dist, written in told["districts"].items():
            if written in names:
                resolved[dist] = written
                continue
            surname = written.split()[-1]
            hits = sorted(n for n in names if n.split()[-1] == surname)
            if len(hits) != 1:
                raise RuntimeError(
                    "%s district %s: the county wrote %r, which the gated "
                    "roster does not carry, and %d roster name(s) share the "
                    "surname %r (%s). Settle it by hand rather than guessing."
                    % (county, dist, written, len(hits), surname,
                       ", ".join(hits) or "none"))
            print("  name joined   %-12s district %s: the county wrote %r, "
                  "the gated roster spells it %r -- the roster's spelling "
                  "ships" % (county, dist, written, hits[0]), file=sys.stderr)
            resolved[dist] = hits[0]
        cache[county] = {"districts": resolved, "readOn": told["readOn"]}
        print("  from a letter  %-12s %d district(s), %s"
              % (county, len(resolved), told["why"]), file=sys.stderr)

    # THE ROSTER THIS RUN IS ABOUT TO OVERWRITE, read in FULL rather than as
    # district counts. It is two things at once: the Grundy guard below still
    # asks whether a county that shipped last week keyed nothing this week,
    # and the preservation pass needs the county's actual records to carry
    # forward. Reading it once, here, is what lets both happen before the
    # floors are measured -- a preserved county ships, so it counts.
    try:
        with open(OUT) as f:
            prev = {rec["county"]: rec for rec in json.load(f).values()}
    except (OSError, ValueError):
        prev = {}
    was = {c: len(r["districts"]) for c, r in prev.items()}

    directory, skipped, refused_now, unchecked = {}, [], {}, []
    for county in sorted(cache):
        entry = cache[county]
        # The scraper's own outcome for a host it may not read. Reported before
        # anything else is asked of the county, because it is a fact about the
        # SITE: whether the roster names a board or the geometry seats one has
        # no bearing on it, and a refusal reported as "no gated supervisor
        # list" would read as this repo's own gap.
        if entry.get("robotsRefused"):
            refused_now[county] = entry["robotsRefused"]
            skipped.append((county, "robots.txt refuses this client -- %s"
                            % entry["robotsRefused"]))
            continue
        keyed = entry.get("districts") or {}
        board = board_by_county.get(county)
        if not board:
            skipped.append((county, "no gated supervisor list"))
            continue
        if plan_by_county.get(county) != "PLAN 3":
            skipped.append((county, "not a plan 3 county (%s)" % plan_by_county.get(county)))
            continue

        by_name = {m["name"]: m for m in board}
        placed = list(keyed.values())
        # every district 1..N filled exactly once
        want = [str(i) for i in range(1, len(board) + 1)]
        if sorted(keyed, key=lambda k: int(k)) != want:
            skipped.append((county, "districts %s are not 1..%d"
                            % (sorted(keyed), len(board))))
            continue
        # the people placed are EXACTLY the people the roster names
        if sorted(placed) != sorted(by_name):
            skipped.append((county, "placed %s but the roster names %s"
                            % (sorted(placed), sorted(by_name))))
            continue
        seats = seats_by_county.get(county)
        if seats is not None and seats != len(board):
            skipped.append((county, "roster names %d, geometry seats %d"
                            % (len(board), seats)))
            continue

        # A COUNTY'S OWN DISTRICT NUMBER IS NOT THIS INSTANCE'S UNTIL SOMEBODY
        # HAS MEASURED THAT IT IS (NUMBERING_CHECKED). Until then the board is
        # not keyed at all: its supervisors still appear on the County card,
        # which is true whichever way the numbering runs, and no district card
        # claims a person it cannot place.
        checked = NUMBERING_CHECKED.get(county)
        if not checked:
            unchecked.append(county)
            skipped.append((county, "the county's own district numbering has "
                                    "not been checked against this layer's"))
            continue
        # The remap, plus its INVERSE: the card must print the number the
        # county itself uses, not the one the layer happens to carry. Where the
        # two disagree -- five of the six counties measured -- the layer's
        # number names nothing a reader can check against a ballot, so it
        # becomes an internal key and the county's own number is what ships.
        # The remap, plus its INVERSE. The inverse ships beside the members
        # rather than on them: the number the county itself uses is a property
        # of the DISTRICT and not of the person, so it has no business inside a
        # record the structural guard below keeps to a name and a party.
        own = {checked["map"][d]: d for d in checked["map"]}
        keyed = {checked["map"][d]: n for d, n in keyed.items()}

        members = {}
        for dist, name in keyed.items():
            src = by_name[name]
            row = {"name": name}
            if src.get("party"):
                row["party"] = src["party"]
            # A PER-PERSON NUMBER IS DROPPED HERE, DELIBERATELY AND OUT LOUD.
            # This used to raise, on the reading that src carries no phone by
            # construction -- the officer builder hoists a shared board number
            # out of its member rows -- so a number on a member row would be a
            # new fact nobody had looked at. It stopped being hypothetical on
            # 2026-10-01, when Humboldt gained a gated roster read off the
            # county's own board page and that page prints a number beside each
            # of its five supervisors.
            #
            # IT IS MEASURABLY NOT A SWITCHBOARD, which is the question the
            # raise asked: the five numbers are FIVE DISTINCT numbers, two
            # adjacent office extensions and three on other exchanges, where a
            # shared board line would be one number repeated five times. So it
            # cannot be hoisted as the board's number either.
            #
            # WHAT IT IS DOES NOT SETTLE WHETHER IT SHIPS. This builder
            # publishes a name and a party and no contact detail for any of its
            # counties, and three of these five read as personal mobiles rather
            # than office lines. Shipping them would be a reader-visible change
            # to the card, for one county, in the class of fact this project is
            # deliberately cautious with -- so the number is dropped, the drop
            # is printed on every run, and whether these cards should carry a
            # supervisor's own line at all is the operator's question rather
            # than this loop's. The county's own board page is linked from the
            # card, and it is where the numbers are published.
            #
            # ANY OTHER NEW FIELD STILL STOPS THE BUILD. The raise below is
            # what the phone raise was for: a field this builder has never seen
            # must be looked at by a person rather than inherited or discarded.
            extra = sorted(k for k in src
                           if k not in ("name", "party", "phone"))
            if extra:
                raise RuntimeError(
                    "%s names %s on supervisor %s -- a field this builder has "
                    "never shipped. Look at it before it is inherited or "
                    "dropped." % (county, ", ".join(extra), name))
            if src.get("phone"):
                print("  phone dropped  %-12s %s -- this builder ships no "
                      "per-person contact detail; the county's own board page "
                      "publishes it" % (county, name), file=sys.stderr)
            members[dist] = row
        rec = {
            "county": county,
            "districts": members,
            # THE NUMBER THE COUNTY ITSELF USES, keyed by the number this
            # instance's layer carries. The layer's number is the join key and
            # the file's key; the county's is what a reader can check against
            # their own ballot, so it is what the card prints.
            "countyNumbers": own,
            # The date the SCRAPE read this page, never this process's clock.
            # It is present on every county, read or preserved, because a
            # field that appears only on successfully-read counties is one
            # check_roster_retention reads as VANISHING the week a county
            # fails -- the defect Wisconsin removed on 2026-09-18 after it
            # turned a roster PR red that changed nobody.
            "readOn": entry.get("readOn") or (prev.get(county) or {}).get("readOn") or TODAY,
        }
        # A LETTER IS NOT A PAGE. There is no url to carry and nothing to
        # re-read, so the record is dated and says where the pairing came
        # from, which the card renders in place of the instance-wide "Data
        # last verified" date -- the same honesty the preserved counties get,
        # for the same reason.
        if entry.get("sourceUrl"):
            rec["sourceUrl"] = entry["sourceUrl"]
        told = CORRESPONDENCE_ROSTERS.get(county)
        if told:
            rec["asOf"] = told["readOn"]
            rec["asOfWhy"] = told["cardNote"]
        # The board office's own number, county-level and labelled as such on
        # the card. One number shared by every supervisor is a switchboard.
        if board_phone_by_county.get(county):
            rec["boardPhone"] = board_phone_by_county[county]
        directory[fips_by_county[county]] = rec

    # PRESERVATION. Fleet policy, ruled by Adam on 2026-09-19: PRESERVE DATA WE
    # HAVE ALREADY FETCHED. A robots refusal stops this project READING a
    # county; it does not require it to unpublish supervisors it fetched
    # legitimately while the county was serving. Iowa was the outlier --
    # Illinois preserves (PRESERVABLE in build_municipal_officials_roster.py)
    # and Wisconsin re-asks an unreachable verdict before believing it -- and
    # this is the file that deleted.
    #
    # WHAT IS PRESERVED IS THE RECORD, AND WHAT IS NOT PRESERVED IS THE CLAIM
    # THAT IT IS CURRENT. A carried county keeps its members and gains `asOf`
    # and `asOfWhy`, which the card renders instead of the instance-wide
    # "Data last verified" date -- that date would otherwise assert a
    # verification this run did not perform on this county.
    preserved = []
    for county in sorted(refused_now):
        recorded = ROBOTS_REFUSED_PRESERVED.get(county)
        if not recorded:
            # Not recorded: the drop guard below stops the build, which is the
            # point. A newly refused county is indistinguishable from a bug in
            # the robots read until somebody looks at the host.
            continue
        if county not in NUMBERING_CHECKED:
            # PRESERVATION CARRIES A RECORD, NOT A CLAIM NOBODY CHECKED. The
            # record held for a refused county was keyed on the county's own
            # district number, which this project now knows is usually not this
            # layer's -- so carrying it forward would preserve a pairing that
            # was never right rather than one that has stopped being re-read.
            continue
        carried = prev.get(county)
        if not carried:
            # Nothing was ever fetched, so there is nothing to preserve. The
            # county simply does not ship, and says so in the skip list above.
            continue
        rec = dict(carried)
        read_on = carried.get("readOn") or recorded["seedReadOn"]
        rec["readOn"] = read_on
        rec["asOf"] = read_on
        rec["asOfWhy"] = recorded["cardNote"]
        directory[fips_by_county[county]] = rec
        preserved.append((county, read_on, len(rec["districts"])))

    # The scraper caps the name-to-district gap at PROXIMITY_CHARS, so this is
    # a tripwire rather than a second gate: counties publish this pairing
    # adjacently (max 42 characters measured across 67 districts), and a run
    # where the widest gap creeps toward the cap is the signal that assumption
    # has stopped holding somewhere.
    widest = max([cache[c].get("maxGap", 0) for c in cache] or [0])

    total_districts = sum(len(v["districts"]) for v in directory.values())
    if len(directory) < MIN_COUNTIES or total_districts < MIN_DISTRICTS:
        raise RuntimeError(
            "only %d counties / %d districts keyed (floors %d / %d) -- re-run the "
            "scraper and read its skip reasons before loosening anything"
            % (len(directory), total_districts, MIN_COUNTIES, MIN_DISTRICTS))

    # A COUNTY THAT SHIPPED LAST WEEK MAY NOT SIMPLY VANISH. The floors above
    # are sized for the FILE (12 of 17 counties), so ONE county dropping out
    # clears them with room to spare -- and a dropped county here is a whole
    # board deleted from the app, in a diff that reads like housekeeping. It
    # happened: on 2026-08-29 a weekly run lost Grundy County's five
    # supervisors to a single failed fetch, and every guard in this pipeline
    # stayed green. The scraper now retries what waiting can fix; this reads
    # the file it is about to overwrite and refuses to drop a county silently.
    #
    # A county that genuinely stops publishing is a decision somebody makes:
    # --allow-drop <County>, in the run that makes it.
    argv = sys.argv[1:]
    allowed_drops = {argv[i + 1] for i, a in enumerate(argv) if a == "--allow-drop"}


    # ROBOTS_REFUSED_PRESERVED, re-audited against THIS run before it is
    # allowed to carry anything forward. An entry that has stopped being true
    # is a hole in the guard with nothing saying so, which is the failure mode
    # every recorded exception in this repo is written to avoid. BOTH AUDITS
    # SURVIVE THE RENAME UNCHANGED: they are what make the table trustworthy,
    # and preserving rather than dropping does not weaken either.
    for county in sorted(ROBOTS_REFUSED_PRESERVED):
        why = ROBOTS_REFUSED_PRESERVED[county]["why"]
        if county not in plan3:
            raise RuntimeError(
                "ROBOTS_REFUSED_PRESERVED names %s, which is not a plan 3 county "
                "the shipped geometry -- the entry is orphaned and should go"
                % county)
        if county in cache and county not in refused_now:
            raise RuntimeError(
                "ROBOTS_REFUSED_PRESERVED names %s, but this run read its site "
                "without being refused -- the entry is stale. Retire it; the "
                "county keys again like any other." % county)
        state = "refused this run" if county in refused_now else "not read this run"
        held = next((p for p in preserved if p[0] == county), None)
        print("  robots-refused %-12s %s | %s | %s"
              % (county, state,
                 "PRESERVED %d district(s), last read %s" % (held[2], held[1])
                 if held else "nothing preserved -- never fetched",
                 why),
              file=sys.stderr)

    # A refusal excuses a drop only where it is BOTH reported by this run and
    # recorded above. A county newly refused and not recorded stops the build,
    # which is the point: that is indistinguishable from a bug in the robots
    # read until somebody looks at the host.
    # A COUNTY WITHHELD FOR AN UNCHECKED NUMBERING IS A DECISION, NOT A DROP,
    # and it is excused the same way a recorded refusal is -- by being stated
    # rather than by a flag the weekly run cannot pass. It is printed per county
    # so the withholding stays visible in every run's output: an absence nobody
    # can see is the shape this project keeps finding wrong.
    for county in sorted(unchecked):
        print("  numbering      %-12s WITHHELD -- the county's own district "
              "number has not been checked against this layer's; its "
              "supervisors still appear on the County card" % county,
              file=sys.stderr)
    excused = ({c for c in refused_now if c in ROBOTS_REFUSED_PRESERVED}
               | set(unchecked))
    gone = sorted(set(was) - {r["county"] for r in directory.values()}
                  - allowed_drops - excused)
    if gone:
        raise RuntimeError(
            "%s shipped last time and keyed nothing this time -- that is a page to "
            "re-read, not a diff to merge. The scraper's own skip reason for each is "
            "above; pass --allow-drop to drop a county deliberately%s"
            % (", ".join("%s (%d districts)" % (c, was[c]) for c in gone),
               "" if not (set(gone) & set(refused_now)) else
               ". Refused by its own robots.txt: %s -- record each in "
               "ROBOTS_REFUSED_PRESERVED with what was measured, rather than "
               "dropping it by hand"
               % ", ".join(sorted(set(gone) & set(refused_now)))))

    # Structural refusal: only these two fields may ship on a person. No
    # address, ever -- and no phone, because the only number any of these
    # publishers gives is the board office's, which rides the county level.
    for fips, rec in directory.items():
        for dist, row in rec["districts"].items():
            extra = set(row) - {"name", "party"}
            if extra:
                raise RuntimeError("%s district %s carries %s -- only "
                                   "name/party may ship on a supervisor"
                                   % (fips, dist, sorted(extra)))

    # A PRESERVED COUNTY IS NOT SKIPPED AND MUST NOT PRINT AS ONE. It ships
    # its supervisors; what it does not get is a fresh read. The loop above
    # files it under `skipped` before the preservation pass exists, so it is
    # filtered out here rather than being counted twice in one run's log.
    held_counties = {c for c, _, _ in preserved}
    skipped = [(c, why) for c, why in skipped if c not in held_counties]
    print("ia-supervisor-members: %d plan 3 counties, %d districts keyed, "
          "%d preserved, %d skipped | widest name-to-district gap %d chars"
          % (len(directory) - len(preserved), total_districts, len(preserved),
             len(skipped), widest), file=sys.stderr)
    for county, read_on, n in preserved:
        print("  preserved %-13s %d district(s), last read %s -- robots.txt "
              "refuses this client, so the county is not re-read"
              % (county, n, read_on), file=sys.stderr)
    for county, why in skipped:
        print("  skipped %-14s %s" % (county, why), file=sys.stderr)

    payload = json.dumps(directory, indent=1, sort_keys=True) + "\n"
    if check_only:
        try:
            with open(OUT) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError("data/app/ia-supervisor-members.json is missing (%s)" % e)
        if shipped != payload:
            raise RuntimeError("data/app/ia-supervisor-members.json has drifted from "
                               "the cache. Re-run: python3 "
                               "ia/scripts/build_ia_supervisor_roster.py")
        print("check: shipped roster matches the cache", file=sys.stderr)
        return

    with open(OUT, "w") as f:
        f.write(payload)
    print("wrote data/app/ia-supervisor-members.json", file=sys.stderr)


if __name__ == "__main__":
    main()
