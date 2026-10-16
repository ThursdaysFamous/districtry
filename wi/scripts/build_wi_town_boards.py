#!/usr/bin/env python3
"""Build wi/data/app/wi-town-boards.json — who sits on each Wisconsin town board.

A Wisconsin town is governed by its town board: a chairperson and two or more
supervisors (Wis. Stat. 60.21). No state agency publishes who they are. Measured
2026-10-15, 50 of the 72 counties publish the list themselves, nearly all as
the county clerk's yearly Official Directory; `wi_town_board_scraper.py` reads
them, one module per county under `town_boards/`, and this file decides what
ships.

WHAT SHIPS, PER TOWN: the board members' names and the role the county prints,
keyed by the town's 10-digit county-subdivision GEOID — the key the County
Subdivision card already holds, so the card needs no name matching of its own.
Never an address, a telephone number or an e-mail: the directories print home
details beside these names, and a town supervisor's house is not an office.

WHAT SHIPS, PER COUNTY (`_counties`): whether the county publishes a list, the
document cited and its edition, and the day it was last actually read. The
card uses it to say the true thing in each of three cases — a named board; a
town the county's list does not name; a county that publishes no list, which
is the county's fact and not this town's.

THE NAME MATCH IS EXACT AFTER NORMALISATION, AND A MISS IS REPORTED, NEVER
GUESSED. A town is matched to its GEOID through the Elections Commission's
town-clerk files (`town-clerks-<fips>.json`, `municipality`), comparing names
with case, punctuation, spacing and a leading "Town of" removed and "St." read
as "Saint". A directory town that matches nothing is printed by name; an alias
goes in ALIASES with the reason, and a county below its floor fails the build.

A COUNTY WHOSE READ FAILS KEEPS ITS LAST GOOD RECORD (Adam, 2026-09-19:
"Preserve data we have already fetched"), carried forward with the date it was
last read, so a card never prints a read date for a document nobody read.
"""

import argparse
import datetime
import importlib
import json
import math
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
APP_DIR = os.path.join(SCRIPT_DIR, "..", "data", "app")
RAW = os.path.join(SCRIPT_DIR, ".cache", "wi_town_boards_raw.json")
OUT = os.path.join(APP_DIR, "wi-town-boards.json")

# A directory's spelling of a town that the normalisation below cannot reach,
# keyed (county FIPS, normalised directory name) -> normalised Commission name.
ALIASES = {
}

# The counties whose town boards this file cannot name, as measured on
# 2026-10-15 (the survey is summarised in wi/scripts/town_boards/__init__.py).
# Each note is the sentence the card prints, so it is written for a reader.
#   "none"     the county's own site carries no list of town boards;
#   "refused"  a list or site exists and the county's robots.txt, or a check in
#              front of the site, keeps this project from reading it — the
#              county's policy, never a gap in its publishing;
#   "image"    the list is published as a scanned picture with no text in it;
#   "stale"    the only list published predates the last town elections;
#   "partial"  the county publishes part of the board and not the rest.
_ASKED = ("{c} County's website asks automated readers not to read it, so "
          "this app does not read its list of town officials.")
_CHECK = ("{c} County's website sits behind a check that turns automated "
          "readers away, so this app does not read its list of town officials.")
_NONE = ("{c} County does not publish a list of who sits on its town boards.")
NOT_READ = {
    "001": ("Adams", "refused", "Adams County publishes its directory as a "
            "Google Drive file, and Google's robots.txt asks automated readers "
            "not to download it."),
    "003": ("Ashland", "refused", _ASKED),
    "005": ("Barron", "refused", _ASKED),
    "011": ("Buffalo", "none", _NONE),
    "015": ("Calumet", "none", _NONE),
    "025": ("Dane", "none", _NONE),
    "027": ("Dodge", "image", "Dodge County publishes its directory as "
            "scanned pages with no text in them, which this app cannot read "
            "yet."),
    "033": ("Dunn", "refused", _ASKED),
    "041": ("Forest", "refused", "Forest County's website could not be "
            "reached to read its policy for automated readers, so this app "
            "does not read it."),
    "047": ("Green Lake", "none", _NONE),
    "049": ("Iowa", "refused", "Iowa County publishes a directory, and its "
            "robots.txt asks automated readers not to read it."),
    "053": ("Jackson", "refused", _ASKED),
    "063": ("La Crosse", "none", _NONE),
    "065": ("Lafayette", "refused", _CHECK),
    "069": ("Lincoln", "refused", _CHECK),
    "075": ("Marinette", "refused", "Marinette County publishes a directory, "
            "and its robots.txt asks automated readers not to read it."),
    "078": ("Menominee", "partial", "Menominee County publishes the town "
            "chair only, in an undated document, and not the rest of the "
            "town board."),
    "091": ("Pepin", "refused", _ASKED),
    "095": ("Polk", "refused", _ASKED),
    "103": ("Richland", "refused", _ASKED),
    "105": ("Rock", "none", _NONE),
    "107": ("Rusk", "refused", _ASKED),
    "125": ("Vilas", "stale", "Vilas County's only published directory is "
            "from April 2023, before the 2025 town elections, so this app "
            "does not name a board from it."),
    "137": ("Waushara", "refused", _CHECK),
}


def norm(name):
    s = name.lower().replace("’", "'")
    s = re.sub(r"^\s*town\s+of\s+", "", s)
    s = re.sub(r"\s+town$", "", s)
    s = re.sub(r"\bst\.?\s", "saint ", s)
    s = re.sub(r"\bmt\.?\s", "mount ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def town_index(fips):
    path = os.path.join(APP_DIR, "town-clerks-%s.json" % fips)
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        data = json.load(fh)
    out = {}
    for geoid, rec in data.items():
        if geoid.startswith("_"):
            continue
        out[norm(rec["municipality"])] = geoid
    return out


def floor_for(module, n_towns):
    explicit = getattr(module, "MIN_TOWNS", None)
    if explicit is not None:
        return explicit
    return max(1, math.ceil(0.9 * n_towns))


def build(raw, previous):
    import wi_town_board_scraper as runner
    towns_out, counties, problems, notes = {}, {}, [], []
    prev_counties = (previous or {}).get("_counties", {})
    for slug in runner.modules():
        mod = importlib.import_module("town_boards." + slug)
        fips = mod.COUNTY_FIPS
        index = town_index(fips)
        rec = raw.get(slug)
        if not rec or not rec.get("ok"):
            prev = prev_counties.get(fips)
            if prev and prev.get("status") == "published":
                kept = {g: v for g, v in previous.items()
                        if not g.startswith("_") and v.get("county") == fips}
                towns_out.update(kept)
                counties[fips] = prev
                notes.append("%s: read failed (%s); carried forward %d towns "
                             "last read %s" % (mod.COUNTY_NAME,
                                               (rec or {}).get("error", "not run"),
                                               len(kept), prev.get("readOn")))
                continue
            problems.append("%s: no successful read and nothing to carry "
                            "forward (%s)" % (mod.COUNTY_NAME,
                                              (rec or {}).get("error", "not run")))
            continue
        matched, unmatched = 0, []
        for town, people in sorted(rec["towns"].items()):
            key = norm(town)
            key = ALIASES.get((fips, key), key)
            geoid = index.get(key)
            if not geoid:
                unmatched.append(town)
                continue
            if geoid in towns_out:
                problems.append("%s: two directory blocks for %s" %
                                (mod.COUNTY_NAME, town))
                continue
            towns_out[geoid] = {"county": fips, "board": people}
            # a town counts as named with any member: a chair the county prints
            # as vacant leaves the supervisors it does name
            matched += 1
        need = floor_for(mod, len(index))
        line = "%-12s %3d of %3d towns named (floor %d)" % (
            mod.COUNTY_NAME, matched, len(index), need)
        if unmatched:
            line += "; unmatched: " + ", ".join(unmatched)
        print(line)
        if matched < need:
            problems.append("%s: %d towns named, floor %d" %
                            (mod.COUNTY_NAME, matched, need))
        counties[fips] = {
            "county": mod.COUNTY_NAME,
            "status": "published",
            "sourceUrl": rec["sourceUrl"],
            "edition": rec.get("edition") or getattr(mod, "EDITION", None),
            "readOn": rec["readOn"],
        }
        if getattr(mod, "PARTIAL_NOTE", None):
            counties[fips]["note"] = mod.PARTIAL_NOTE
    for fips, (name, status, why) in NOT_READ.items():
        if fips in counties:
            problems.append("%s is in NOT_READ and also has a module" % name)
            continue
        counties[fips] = {"county": name, "status": status,
                          "note": why.format(c=name)}
    return towns_out, counties, problems, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", default=RAW)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    with open(args.raw) as fh:
        raw = json.load(fh)
    previous = None
    if os.path.exists(args.out):
        with open(args.out) as fh:
            previous = json.load(fh)
    towns, counties, problems, notes = build(raw, previous)
    for n in notes:
        print("NOTE  " + n)
    if problems:
        for p in problems:
            print("FAIL  " + p)
        sys.exit(1)
    published = sum(1 for c in counties.values() if c["status"] == "published")
    people = sum(len(t["board"]) for t in towns.values())
    out = {
        "_meta": {
            "builtOn": datetime.date.today().isoformat(),
            "about": "Wisconsin town boards as each county publishes them; "
                     "names and roles only. wi/scripts/build_wi_town_boards.py",
        },
        "_counties": dict(sorted(counties.items())),
    }
    out.update(sorted(towns.items()))
    # one record per line: compact enough for a file fetched on a click, and
    # a weekly diff still shows which town changed
    with open(args.out, "w") as fh:
        fh.write("{\n" + ",\n".join(
            json.dumps(k) + ":" + json.dumps(v, ensure_ascii=False,
                                             separators=(",", ":"))
            for k, v in out.items()) + "\n}\n")
    print("OK  %d towns, %d people, %d of %d counties publish a list"
          % (len(towns), people, published, len(counties)))


if __name__ == "__main__":
    main()
