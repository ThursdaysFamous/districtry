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

MIN_COUNTIES = 12
MIN_DISTRICTS = 40

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

    directory, skipped, refused_now = {}, [], {}
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

        members = {}
        for dist, name in keyed.items():
            src = by_name[name]
            row = {"name": name}
            if src.get("party"):
                row["party"] = src["party"]
            # src carries no phone by construction (the officer builder hoists
            # the shared board number out of its member rows). Should a source
            # ever start publishing a genuine per-supervisor line, it has to be
            # let through deliberately rather than inherited by this loop.
            if src.get("phone"):
                raise RuntimeError(
                    "%s names a phone on supervisor %s -- a per-person number "
                    "is a new fact here. Confirm it is that supervisor's line "
                    "and not the board switchboard before shipping it."
                    % (county, name))
            members[dist] = row
        rec = {
            "county": county,
            "districts": members,
            "sourceUrl": entry.get("sourceUrl"),
            # The date the SCRAPE read this page, never this process's clock.
            # It is present on every county, read or preserved, because a
            # field that appears only on successfully-read counties is one
            # check_roster_retention reads as VANISHING the week a county
            # fails -- the defect Wisconsin removed on 2026-09-18 after it
            # turned a roster PR red that changed nobody.
            "readOn": entry.get("readOn") or (prev.get(county) or {}).get("readOn") or TODAY,
        }
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
    plan3 = {c for c, plan in plan_by_county.items() if plan == "PLAN 3"}
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
    excused = {c for c in refused_now if c in ROBOTS_REFUSED_PRESERVED}
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
