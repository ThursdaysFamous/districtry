#!/usr/bin/env python3
"""
Build data/app/county-board-members.json from the county board scraper's
intermediate JSON, keyed by SUPER_FIPS so the card can look a supervisor up
straight from the district feature the map already matched.

The roster is checked against the SHIPPED GEOMETRY rather than against itself:
every county in it must exist in county-supervisory-districts.json, and its
seat count must equal the number of districts actually drawn for that county.
That is what stops a county's page reorganising into a plausible-but-wrong
number of members — the two files were built from different publishers (the
county's own page, and LTSB's statewide filing) and have to agree.

Fifty-seven of Wisconsin's 72 counties have a district-keyed member list this
project can reach, by one of the routes the scraper's docstring sets out; the
other 15 are recorded in the Data gaps panel and their cards keep linking the
county board rather than naming anybody.

AND A COUNTY THAT SHIPPED LAST WEEK MAY NOT SIMPLY VANISH. The floors below are
a fleet-sized net and one county falling out of a fifty-county file goes
straight through it — a whole board quietly deleted, every count guard green,
the diff looking like housekeeping. So the previous shipped file is read back
and any county that resolved nothing this run fails the build by name. Dropping
one deliberately takes `--allow-drop <County>`, which is a decision somebody
makes rather than a silence.

NINE OF THE FIFTY-SEVEN ARE CARRIED FROM A DOCUMENT, NOT RE-READ WEEKLY, AND
THE CARD HAS TO SAY SO — in two classes that must not be blurred. Taylor's host
answers a captcha and Lafayette's and La Crosse's a Cloudflare challenge: those
counties are BLOCKED, and the card's default sentence, that the county's site
refuses automated readers, is true of them.

THE OTHER SIX ARE THE OPPOSITE CASE. Pepin, Jackson, Richland, Rusk, Polk and
Dunn all serve this client perfectly well, and every one publishes a robots.txt
whose `User-agent: *` group disallows the whole site. Five of the six were being
scraped WEEKLY until 2026-08-31, when wi/scripts/validate_robots.py was written
and swept every host this instance fetches; the crawl stopped and the names
stayed, dated, because robots.txt governs RETRIEVAL and not what already-public
information may be shown. A refusal and a request are different facts about a
county, so each of those six carries its own `why` and the card prints it in
place of the default.

The scraper marks those counties `carried_from_document` with the day they were
read; this builder turns that into an `asOf` on every one of their rows, and the
card prints it rather than letting a dated snapshot read like the weekly re-read
the other fifty-three get. A county whose live page
answers on a later run loses the flag in the scraper, so the field disappears
here by itself — which is exactly what Fond du Lac did on the first run after
its own archive route shipped.

AND EVERY ROW NOW CARRIES `readOn`, BECAUSE THE ABSENCE OF `asOf` WAS DOING THAT
JOB AND CANNOT. Until 2026-09-08 a live-read county published no date anywhere:
its freshness was stated only by the absence of the carried-from-a-document
marker, which is legible to a reader who has seen a carried county's card and to
nobody else. The asymmetry became plain when Lafayette's page answered live and
its rows LOST their date, leaving sixteen supervisors with no indication that
anyone had read the county that week. `readOn` is the day the source these names
came from was read, and it means that in all three cases — see read_on_for(),
which refuses a rung it has no date rule for rather than letting a new one
inherit the run's own day.

CONTACT RIDES ONLY WHERE ITS COUNTY PUBLISHED IT, which is why these rows are
not uniform and should not be made uniform. Most counties publish a name and a
district and nothing else; some publish a county mailbox, an office phone or a
profile page beside the seat, and those ride. An absent field renders nothing
rather than a placeholder. `phone` was collected by the scraper and silently
dropped here for a while: ADDING A FIELD TO THE SCRAPER IS NOT ADDING IT TO THE
APP — the two halves have to agree.

Usage:
    python3 wi/scripts/build_wi_county_board_roster.py
    python3 wi/scripts/build_wi_county_board_roster.py --check
    python3 wi/scripts/build_wi_county_board_roster.py --allow-drop Rock
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The withhold list is FLEET-WIDE and lives at the repo root: the same MX sweep
# that found Clark's `yahoo.ocm` found eleven more across Illinois, and one list
# with one measurement behind it beats three drifting copies.
sys.path.insert(0, os.path.join(os.path.dirname(REPO_ROOT), "scripts"))
import undeliverable  # noqa: E402
APP_DATA_DIR = os.path.join(REPO_ROOT, "data", "app")
GEOMETRY = os.path.join(APP_DATA_DIR, "county-supervisory-districts.json")
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "wi_county_boards_raw.json")
OUT = os.path.join(APP_DATA_DIR, "county-board-members.json")

MIN_COUNTIES = 70      # ALL 72 ship one (41 board pages + 3 county GIS layers + Fond du
                       # Lac through the Internet Archive + Dodge's constituent
                       # directory + Kenosha's witnessed directory PDF + Adams's
                       # directory PDF + Clark's, Pierce's and Marathon's
                       # directories + St. Croix's own district table +
                       # Chippewa's board-page h-cards + Menominee's joint
                       # County/Town board + Langlade's board page +
                       # Columbia's framed table + Barron's own board.cfm table
                       # + Forest's supervisors page + Florence's board list
                       # + Sawyer's staff directory + Ashland's board page
                       # + Douglas's ordinal table + Iron's member pages
                       # + TEN by dated document); tolerates two dark
MIN_SEATS = 1517       # 1590 today — every supervisory seat Wisconsin files;
                       # the tolerance is the two largest boards
                       # (Dane 37 + Outagamie 36) going dark in one run, which is
                       # what a floor is for — it is never lowered to fit a result


def read_on_for(entry):
    """The day the source these names came from was read, per county.

    ONE MEANING IN ALL THREE CASES, which is the whole point of the field: the
    day somebody read the surface these names are on. That is the run's own day
    for a county read live, the capture's day for a county carried from a dated
    document, and the CAPTURE's day — never the run's — for a county read
    through a public archive, where the fetch happened today and the page did
    not.

    AN UNKNOWN RUNG RAISES RATHER THAN INHERITING TODAY. The scraper's ladder
    grows a rung every few counties, and the failure this guards against is a
    new one quietly taking the live branch: a county whose names are months old
    would then ship a date saying they were read this morning, which is worse
    than the silence this field replaces. A rung that wants a date has to say
    which day it earned.

    A COUNTY THAT FAILED THIS RUN CANNOT REACH HERE. The scraper drops it into
    `failures` and it never enters `counties`; main() then refuses the build by
    name unless somebody passes --allow-drop. So there is no path by which a
    stale row inherits a fresh date — but the guard is the drop check above,
    not this function, and moving it would put two half-guards where one whole
    one is.
    """
    if entry.get("carried_from_document"):
        # The same value the `asOf` sentence is built from, so the machine-
        # readable date and the prose can never disagree.
        return entry["read_on"], None
    read_from = entry.get("read_from") or ""
    if read_from == "live":
        stamp = entry.get("scraped_at")
        if not stamp:
            raise RuntimeError(
                "%s was read live and the scraper recorded no `scraped_at`, so "
                "there is no day to publish — re-run the scraper rather than "
                "dating this row from the clock the builder happens to run on"
                % entry.get("county", "?"))
        return stamp[:10], None
    if read_from.startswith("archive:"):
        # Wayback's own stamp, YYYYMMDDhhmmss. The county's page was served
        # from a capture taken that day; today is when we fetched the capture,
        # which is not the same claim and is not what ships.
        stamp = read_from.split(":", 1)[1]
        if not re.fullmatch(r"\d{8,}", stamp):
            raise RuntimeError("%s: unreadable archive stamp %r"
                               % (entry.get("county", "?"), stamp))
        return "%s-%s-%s" % (stamp[:4], stamp[4:6], stamp[6:8]), "the Internet Archive"
    raise RuntimeError(
        "%s was read by a rung this builder has no date rule for (%r). Add one "
        "to read_on_for() saying which day that rung earns; do not let it fall "
        "through to the live branch." % (entry.get("county", "?"), read_from))


def shipped_counties():
    """{county name: seats} as the file on disk has them, or {} if it is new."""
    try:
        with open(OUT) as f:
            shipped = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for row in shipped.values():
        out[row["county"]] = out.get(row["county"], 0) + 1
    return out


def main():
    argv = sys.argv[1:]
    check_only = "--check" in argv
    allowed_drops = {argv[i + 1] for i, a in enumerate(argv) if a == "--allow-drop"}
    with open(GEOMETRY) as f:
        geo = json.load(f)
    drawn = {}
    names = {}
    for feat in geo["features"]:
        p = feat["properties"]
        drawn.setdefault(p["CNTY_FIPS"], set()).add(int(p["SUPERID"]))
        names[p["CNTY_FIPS"]] = p["CNTY_NAME"]

    with open(RAW) as f:
        raw = json.load(f)
    counties = raw["counties"]
    if len(counties) < MIN_COUNTIES:
        raise RuntimeError("only %d counties scraped, floor is %d — %s"
                           % (len(counties), MIN_COUNTIES, raw.get("failures")))

    roster = {}
    total = vacant = withheld = 0
    for fips, entry in sorted(counties.items()):
        if fips not in drawn:
            raise RuntimeError("county %s (%s) has members but no districts in the "
                               "shipped geometry" % (fips, entry["county"]))
        if entry["county"] != names[fips]:
            raise RuntimeError("county %s is %r in the geometry and %r in the roster"
                               % (fips, names[fips], entry["county"]))
        want = drawn[fips]
        got = {int(d) for d in entry["districts"]}
        if got != want:
            raise RuntimeError(
                "%s: the roster covers districts %s and the map draws %s — one of the "
                "two publishers has changed; re-read both before shipping"
                % (entry["county"], sorted(got), sorted(want)))
        # A POSITIVE DATE ON EVERY ROW, not the absence of one. Until now the
        # only date in this file was `asOf`, which nine counties carry, so a
        # live-read county said nothing at all about when anybody read it and
        # its freshness was legible only to a reader who had seen a CARRIED
        # county's card and inferred the contrast. Absence is a poor way to
        # state a fact about 1,408 seats.
        read_on, read_via = read_on_for(entry)
        for d, member in entry["districts"].items():
            key = "%s%02d" % (fips, int(d))
            row = {"county": entry["county"], "district": int(d),
                   "readOn": read_on, "sourceUrl": entry["source_url"]}
            # Set only where the read went somewhere other than the county's
            # own live page — today that is the Internet Archive, and the card
            # names it rather than letting an archived capture read as a page
            # the county served this morning.
            if read_via:
                row["readVia"] = read_via
            # Present only for a county the scraper marked as carried from a
            # document rather than read this run. `sourceUrl` is still the
            # page the names came from, so the pair is the whole provenance a
            # reader needs; the exact route lives in the scraper's
            # DOCUMENT_ROSTERS entry and on its NOT RE-READ line.
            if entry.get("carried_from_document"):
                row["asOf"] = "the county's own page, captured %s" % entry["read_on"]
                # WHY it is a capture, where that is not the card's default. The
                # card says a carried roster is dated because the county's site
                # "refuses automated readers", which is true of a captcha and a
                # Cloudflare challenge and false of a county that serves this
                # client and asks it not to crawl (Pepin). A county that states
                # its own reason gets it printed instead.
                if entry.get("why"):
                    row["asOfWhy"] = entry["why"]
            if member.get("withheld"):
                # A SEAT NAMED BY NOBODY BECAUSE TWO PUBLISHERS DISAGREE ABOUT
                # ITS GROUND — never `vacant`, which is a claim the county
                # makes about an empty seat, and never silence, which reads as
                # a lookup that failed. Lincoln district 21 is the case: see
                # district_geometry_witness() in the scraper.
                row["withheld"] = True
                row["withheldWhy"] = member["withheld_why"]
                withheld += 1
            elif member["vacant"]:
                row["vacant"] = True
                vacant += 1
            else:
                row["name"] = member["name"]
                if member["role"]:
                    row["role"] = member["role"]
                # CONTACT RIDES ONLY WHERE ITS COUNTY PUBLISHED IT. The two
                # county-GIS rosters carry an e-mail (and Milwaukee a profile
                # link) on the feature; Taylor's document and Adams's directory
                # carry an e-mail and a phone. The page-scraped counties publish
                # none of it, and an absent field renders nothing rather than a
                # placeholder.
                #
                # `phone` USED TO BE COLLECTED AND SILENTLY DROPPED HERE: the
                # scraper has carried Taylor's seventeen numbers since the day
                # it shipped, its own comment saying a phone is an official
                # contact detail and does ship, and this loop copied `email`
                # and `url` and nothing else. Adding a field to the scraper is
                # not adding it to the app — the two halves have to agree.
                    # where the county STATES the role, when that is not the
                    # page the district list came from (Sheboygan names its
                    # chair on the board's landing page, not its roster table)
                    if member.get("role_url"):
                        row["roleSourceUrl"] = member["role_url"]
                # Contact rides only where its county published it: the two
                # county-GIS rosters carry it as feature attributes, Taylor's
                # comes with its document, and Sheboygan's off the page each
                # supervisor has of their own. A supervisor's ADDRESS is never
                # among these even where the county prints one — it is their
                # home, not an office (the scraper's MEMBER_PAGES comment).
                addr, _why = undeliverable.withhold(
                    member.get("email"), "%s, district %s"
                    % (member.get("name") or "?", row.get("district") or "?"))
                if addr:
                    row["email"] = addr
                if member.get("phone"):
                    row["phone"] = member["phone"]
                if member.get("url"):
                    row["profileUrl"] = member["url"]
            # THE PAGE THE NAMES WERE ACTUALLY READ FROM, where that is not
            # `sourceUrl`. Adams's twenty supervisors come out of a directory
            # PDF the county links; its board page — the county's own landing
            # page and this row's sourceUrl — names none of them, so a reader
            # who clicks through to check a name finds nothing to check it
            # against. The scraper resolves and records the document it read;
            # dropping that here left the card pointing at the one surface that
            # could not corroborate it.
            if entry.get("document_url"):
                row["documentUrl"] = entry["document_url"]
            roster[key] = row
            total += 1

        # THE SUPERVISORS WHO HOLD NO DISTRICT, under a county-keyed entry
        # beside the districts. Only Menominee has any: its joint County/Town
        # board seats seven, five by ward and two elected countywide, and one
        # of the two is the Vice-Chair. A district-keyed roster has no slot for
        # a member elected countywide, and omitting them ships a five-member
        # board for a seven-member body — the Alexander (Illinois) case, where
        # a card that names fewer people than the body seats has to SAY so
        # rather than let the absence read as completeness. Every district card
        # in the county names them beneath its own supervisor, because a reader
        # in ward 3 is represented by all three.
        #
        # The key is deliberately not a district key: `<fips>-at-large` cannot
        # collide with the seven-digit SUPER_FIPS the districts use, so a card
        # looking up a district can never find this row by accident.
        if entry.get("at_large"):
            roster["%s-at-large" % fips] = {
                "county": entry["county"],
                # The same read date as this county's district rows: the two
                # come off one page in one read, and a row that carried no
                # date while every row beside it did would read as a different
                # kind of fact rather than as the same one.
                "readOn": read_on,
                "sourceUrl": entry["source_url"],
                "atLarge": [
                    dict([("name", m["name"])] + ([("role", m["role"])] if m.get("role") else []))
                    for m in entry["at_large"]
                ],
            }
            if read_via:
                roster["%s-at-large" % fips]["readVia"] = read_via

    if total < MIN_SEATS:
        raise RuntimeError("%d seats resolved, floor is %d" % (total, MIN_SEATS))

    # See the docstring: the floors above are a fleet-sized net, and one county
    # falling out of a 57-county file slips straight through it.
    was = shipped_counties()
    gone = sorted(set(was) - {e["county"] for e in counties.values()} - allowed_drops)
    if gone:
        raise RuntimeError(
            "%s shipped last time and resolved nothing this time (%s) — that is a "
            "page to re-read, not a diff to merge; pass --allow-drop to drop a "
            "county deliberately"
            % (", ".join("%s (%d seats)" % (c, was[c]) for c in gone),
               raw.get("failures") or "no failure recorded"))

    for fips, entry in sorted(counties.items()):
        # A county read from anywhere but its own live page says so on the log,
        # so the weekly PR's reviewer can see which rung of the ladder answered.
        read_from = entry.get("read_from", "live")
        if read_from.startswith("archive:"):
            print("  %s: read from the Internet Archive capture of %s"
                  % (entry["county"], read_from.split(":", 1)[1][:8]), file=sys.stderr)

    payload = json.dumps(roster, indent=1, sort_keys=True) + "\n"
    # THE FRESHNESS OF THE WHOLE FILE, IN ONE LINE THE WEEKLY PR'S REVIEWER CAN
    # READ. A healthy run prints one date carrying most of the counties and the
    # carried ones' own older days beside it. A rung that starts answering from
    # somewhere else shows up here as a date or a route nobody expected, which
    # is the point: read_on_for() refuses an UNKNOWN rung, and this catches a
    # known rung whose answer moved.
    per_day = {}
    for row in roster.values():
        per_day.setdefault((row["readOn"], row.get("readVia") or ""), set()).add(row["county"])
    print("  read on: %s" % ", ".join(
        "%s%s (%d)" % (day, " via %s" % via if via else "", len(cs))
        for (day, via), cs in sorted(per_day.items())), file=sys.stderr)
    dated = sorted({r["county"] for r in roster.values() if r.get("asOf")})
    print("county-board-members: %d counties, %d seats (%d named, %d vacant%s)%s"
          % (len(counties), total, total - vacant - withheld, vacant,
             ", %d withheld" % withheld if withheld else "",
             "; carried from a document: %s" % ", ".join(dated) if dated else ""),
          file=sys.stderr)
    if check_only:
        try:
            with open(OUT) as f:
                shipped = f.read()
        except OSError as e:
            raise RuntimeError("data/app/county-board-members.json is missing (%s)" % e)
        if shipped != payload:
            raise RuntimeError("data/app/county-board-members.json has drifted from the "
                               "scraper's output — re-run the builder")
        print("check: shipped roster matches", file=sys.stderr)
        return
    with open(OUT, "w") as f:
        f.write(payload)
    print("wrote data/app/county-board-members.json", file=sys.stderr)


if __name__ == "__main__":
    main()
