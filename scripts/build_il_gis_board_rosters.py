#!/usr/bin/env python3
"""
Stage 2: resolve il_gis_board_scraper.py's snapshot into seven roster files
under il/data/source/, one per county, keyed by district.

THE OUTPUT SHAPE IS THE ONE build_county_pages.il_districted ALREADY READS:

    { "<district>": { "members": [ {name, party?, email?, phone?, url?} ],
                      "sourceUrl": "<the county's own board page>" } }

WHY data/source AND NOT data/app. validate_index.py requires every file in an
instance's data/app to be referenced by its index.html, and these are not: the
card still calls the county GIS live. That gate is right, so these sit with the
other build-time inputs. build_county_pages.il_districted reads both directories
and DERIVES each page's "the map reads the same roster" sentence from which one
the file came from, so all seven pages say the card reads the source live and
can be up to a week newer than the table. Cook County's roster is here for the
same reason.

SEVEN COUNTIES, FOUR RECORD SHAPES, and each one is a property of the county's
own service rather than a preference:

  one seat, one row       Effingham, Kankakee, Madison, St. Clair, Winnebago.
  two seats, two COLUMNS  McLean. REPNAME/REPNAME2 with their own party and
                          profile link. A seat with no name is a vacancy
                          between appointments and drops out rather than
                          shipping an empty person — the app's own rule.
  nine seats, ONE STRING  Whiteside. `repname1` is "James C. Duffy, Kurt E.
                          Glazier, …". Split on commas, matching
                          whitesideBoardMembers in the app. A name that ever
                          contained one would arrive as two people, so the
                          split is GUARDED: a fragment that is a bare suffix
                          (Jr, Sr, II, MD) fails the build naming the county,
                          because it means the split has started being wrong.
  a district that is not   Whiteside's layer holds every office's districts in
  a board district         one table and Effingham's `where` filters
                           server-side; Whiteside is filtered here exactly as
                           whitesideIsBoardFeature does it.

WHAT IS NOT CARRIED. Nothing this file does not read from the county. The GIS
rows carry no term, no election date and no office address, so none ships. Where
a county publishes a per-district page (Madison, McLean, Whiteside) that link
rides the member; where it publishes only one board page, that is the file's
sourceUrl and no member carries a link that names the county rather than a
person — the Cook County rule.

Usage:
    python3 scripts/build_il_gis_board_rosters.py [raw.json]
    python3 scripts/build_il_gis_board_rosters.py --check   # drift gate for CI
"""

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from il_gis_board_scraper import COUNTIES, NO_ROSTER, DEFAULT_OUT  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "source")
APP = os.path.join(REPO_ROOT, "il", "index.html")

# The floor per county, measured 2026-09-15 on the services themselves. A floor
# rather than an exact count, because a board can lose a member to a resignation
# between appointments and this must not refuse to write for that; the drop that
# matters is a parser or a service going empty, which these catch.
SEATS = {"effingham": 9, "kankakee": 28, "madison": 26, "mclean": 20,
         "st-clair": 28, "whiteside": 27, "winnebago": 20}

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "md", "m.d.", "phd",
            "ph.d.", "esq", "esq."}


def fail(msg):
    print("build-il-gis-board-rosters: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def get(row, *names):
    """ArcGIS field case is not stable across services; the app reads these
    case-insensitively (findPropCI) and so does this."""
    lower = {str(k).lower(): v for k, v in row.items()}
    for n in names:
        v = lower.get(n.lower())
        if v is None:
            continue
        v = str(v).strip()
        if v:
            return v
    return None


def person(name, party=None, email=None, phone=None, url=None):
    rec = {"name": re.sub(r"\s+", " ", name).strip()}
    for key, value in (("party", party), ("email", email), ("phone", phone),
                       ("url", url)):
        if value:
            rec[key] = value
    return rec


def simple(rows, district_field, name_field, party=None, phone=None, email=None,
           url=None, strip_prefix=None):
    """One seat per row — Effingham, Kankakee, Madison, St. Clair, Winnebago."""
    out = {}
    for row in rows:
        key = get(row, district_field)
        name = get(row, name_field)
        if not key or not name:
            continue
        if strip_prefix:
            key = re.sub(strip_prefix, "", key)
        out.setdefault(key, []).append(
            person(name, get(row, party) if party else None,
                   get(row, email) if email else None,
                   get(row, phone) if phone else None,
                   get(row, url) if url else None))
    return out


def mclean(rows):
    """Two seats in parallel columns, unpacked the way the app unpacks them."""
    out = {}
    for row in rows:
        key = get(row, "DISTRICTID")
        if not key:
            continue
        seats = []
        for n, p, u in (("REPNAME", "PARTY", "DISTRICTURL"),
                        ("REPNAME2", "PARTY2", "DISTRICTURL2")):
            name = get(row, n)
            if not name:
                continue                      # a vacancy between appointments
            seats.append(person(name, get(row, p), url=get(row, u)))
        if seats:
            out[key] = seats
    return out


def whiteside(rows):
    """Nine names in one comma-separated field, on three of twenty-one rows."""
    out, suspect = {}, []
    for row in rows:
        office = (get(row, "electedoffice") or "").lower()
        if not office.startswith("county board"):
            continue
        name = get(row, "name") or ""
        match = re.search(r"(\d+)\s*$", name)
        if not match:
            fail("Whiteside district %r does not end in a number — the layer's "
                 "`name` values changed" % name)
        raw = get(row, "repname1")
        if not raw:
            continue
        # districturl1 is the county's ONE board page on all three rows, not a
        # per-district page, so it is the file's sourceUrl and rides no member.
        # A link that names the county rather than a person identifies nobody —
        # the rule build_cook_county_board.py states for url1.
        seats = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if part.lower() in SUFFIXES:
                suspect.append(part)
            seats.append(person(part))
        if seats:
            out[match.group(1)] = seats
    if suspect:
        fail("Whiteside's member string split into a bare name suffix (%s). "
             "repname1 packs nine names into one comma-separated field and the "
             "split assumes no member's name contains a comma; one now does, so "
             "the split is producing half-people. Read the field and fix the "
             "split before this ships." % ", ".join(sorted(set(suspect))))
    return out


BUILDERS = {
    "effingham": lambda rows: simple(rows, "district", "repname1", party="party1",
                                     phone="phone1", email="email1"),
    "kankakee": lambda rows: simple(rows, "district", "membername", party="party",
                                    phone="phone", email="email"),
    "madison": lambda rows: simple(rows, "DISTRICT", "OFFICIAL", party="PARTY",
                                   phone="PHONE", email="EMAIL", url="URL"),
    "mclean": mclean,
    "st-clair": lambda rows: simple(rows, "district", "name"),
    "whiteside": whiteside,
    "winnebago": lambda rows: simple(rows, "District", "REP", party="REPPARTY",
                                     strip_prefix=r"(?i)^D"),
}


def district_sort(key):
    return (0, int(key), "") if key.isdigit() else (1, 0, key)


APP_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

# Fields worth folding from a county's data/app roster into the members this
# writes. Anything that names or ranks a PERSON is deliberately absent: the
# point of the fold is contact the GIS declares and does not fill, never a
# second opinion about who holds the seat.
FOLD_FIELDS = ("email", "phone")


def fold_published_contact(spec, districts):
    """Carry a county's own published contact onto the members it seats.

    Winnebago is the one county this applies to today, and the reason is worth
    stating because it is the only place two files describe one board. Its
    WinGIS board layer DECLARES ADDRESS, CITYZIP, PHONEHOME and PHONEBUSIN and
    populates every one of them on 0 of 20 rows, so
    winnebago_county_board_scraper.py reads the phone and the official
    @board.wincoil.gov address off the county's own board page into
    il/data/app/winnebago-county-board-members.json — a contact-only file the
    card joins as an enrichment, with no name in it at all. Without this fold
    the county page would name twenty people and drop the contact the county
    publishes for every one of them.

    The fold is refused where it would be a guess: a district with more than one
    member has no unambiguous owner for one e-mail address, so this fails rather
    than attaching it to whoever is first.
    """
    path = os.path.join(APP_DIR, "%s-county-board-members.json" % spec["key"])
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        published = json.load(f)
    folded = 0
    for key, entry in published.items():
        if not isinstance(entry, dict):
            continue
        values = {f: entry[f] for f in FOLD_FIELDS if entry.get(f)}
        if not values:
            continue
        members = districts.get(key)
        if not members:
            continue
        if len(members) > 1:
            fail("%s district %s has %d members and its data/app roster carries "
                 "one %s — nothing says which member it belongs to"
                 % (spec["county"], key, len(members),
                    " and one ".join(sorted(values))))
        members[0].update(values)
        folded += 1
    if folded:
        print("build-il-gis-board-rosters: %-10s folded %s from "
              "il/data/app/%s-county-board-members.json onto %d member(s)"
              % (spec["key"], "/".join(sorted({f for v in [values] for f in v})),
                 spec["key"], folded))
    return folded


def build(spec, snapshot):
    rows = snapshot["rows"]
    districts = BUILDERS[spec["key"]](rows)
    if not districts:
        fail("%s: no district resolved from %d row(s)" % (spec["county"], len(rows)))
    fold_published_contact(spec, districts)
    seats = sum(len(v) for v in districts.values())
    floor = SEATS[spec["key"]]
    if seats < floor:
        fail("%s: %d seat(s) resolved, below the floor of %d — refusing to "
             "overwrite a good roster" % (spec["county"], seats, floor))
    return {k: {"members": districts[k], "sourceUrl": spec["board_url"]}
            for k in sorted(districts, key=district_sort)}, seats


def check_app_registration():
    """Every county here must have a board card, and every county with a board
    card and no roster file must be here or in NO_ROSTER.

    This is the half that makes the stated query table safe. The table is a copy
    of what il/index.html asks for, so the failure to guard against is the two
    drifting apart — a county that leaves the app and keeps a roster here, or
    one that joins the app's board dispatcher and is never snapshotted. Neither
    is visible in any other gate: build_county_pages.py enumerates files and
    cannot know a file is missing.
    """
    with open(APP, encoding="utf-8") as f:
        app = f.read()
    carded = set(re.findall(r'title: "([A-Za-z. ]+) County Board"', app))
    ours = {c["county"] for c in COUNTIES}
    orphans = sorted(ours - carded)
    if orphans:
        fail("%s no longer has a county-board card in il/index.html — a roster "
             "nothing draws a page beside is a file nobody reads. Drop the "
             "entry from il_gis_board_scraper.COUNTIES."
             % ", ".join(orphans))

    have = set()
    for path in glob.glob(os.path.join(REPO_ROOT, "il", "data", "*", "*.json")):
        base = os.path.basename(path)
        match = re.match(r"^(.*)-(county-board-members|commissioner-members|"
                         r"county-board-roles)\.json$", base)
        if match:
            have.add(match.group(1))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_county_pages import IL_NAME_BY_SLUG                # noqa: E402
    named = {IL_NAME_BY_SLUG[s] for s in have if s in IL_NAME_BY_SLUG}
    unexplained = sorted(carded - named - ours - set(NO_ROSTER))
    if unexplained:
        fail("%s has a county-board card, no roster file and no entry in "
             "il_gis_board_scraper — either add it to COUNTIES so its members "
             "reach a crawler, or record in NO_ROSTER why they cannot"
             % ", ".join(unexplained))
    for county, reason in sorted(NO_ROSTER.items()):
        if county not in carded:
            fail("NO_ROSTER records %s and it has no county-board card — drop "
                 "the entry" % county)
        if county in named:
            fail("NO_ROSTER records %s as having no roster and one now ships — "
                 "drop the entry" % county)
        print("build-il-gis-board-rosters: ~ %s has no roster: %s" % (county, reason))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", nargs="?", default=DEFAULT_OUT,
                    help="il_gis_board_scraper.py output")
    ap.add_argument("--check", action="store_true",
                    help="audit the registration only; touches no file and "
                         "needs no scrape")
    args = ap.parse_args()

    check_app_registration()
    if args.check:
        print("build-il-gis-board-rosters: OK — %d county(ies) snapshotted, "
              "%d recorded as having no roster, every board card accounted for"
              % (len(COUNTIES), len(NO_ROSTER)))
        return

    if not os.path.exists(args.raw):
        fail("no scrape at %s — run scripts/il_gis_board_scraper.py first" % args.raw)
    with open(args.raw, encoding="utf-8") as f:
        snapshots = json.load(f)
    missing = [c["key"] for c in COUNTIES if c["key"] not in snapshots]
    if missing:
        fail("the scrape is missing %s — a partial set would drop a county's "
             "page without saying so" % ", ".join(missing))

    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    for spec in COUNTIES:
        roster, seats = build(spec, snapshots[spec["key"]])
        path = os.path.join(OUT_DIR, "%s-county-board-members.json" % spec["key"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(roster, f, ensure_ascii=False)
        total += seats
        print("build-il-gis-board-rosters: %-10s %2d district(s), %2d seat(s)"
              % (spec["key"], len(roster), seats))
    print("build-il-gis-board-rosters: OK — %d county(ies), %d seat(s) written "
          "to il/data/source/" % (len(COUNTIES), total))


if __name__ == "__main__":
    main()
