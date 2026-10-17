#!/usr/bin/env python3
"""Build wi/data/app/wi-town-boards.json — who sits on each Wisconsin town board.

A Wisconsin town is governed by its town board: a chairperson and two or more
supervisors (Wis. Stat. 60.21). No state agency publishes who they are. Measured
2026-10-15, 50 of the 72 counties publish the list themselves, nearly all as
the county clerk's yearly Official Directory; `wi_town_board_scraper.py` reads
them, one module per county under `town_boards/`, and this file decides what
ships.

WHAT SHIPS, PER TOWN: the board members' names, the role the county prints, the
telephone numbers the county prints beside each member — the first in `phone`,
any further ones in `phonesExtra`, each with the county's own label ("cell
715-555-0100") — and the e-mail address it prints beside them, in `email`,
keyed by the town's 10-digit county-subdivision GEOID, the key the County
Subdivision card already holds, so the card needs no name matching of its own.
The numbers ship whosever line they are, because the county prints them for the
public (Adam, 2026-10-17: "if the official government source uses personal
phone numbers, we publish those"); until that day none shipped. The e-mail
address ships whatever its domain, a supervisor's Gmail address included, on
the same reasoning (Adam, 2026-10-17: "E-mails too"); until that day none
shipped either. A number or an address printed for two officers, or for the
town hall or its clerk, is the town's and the scraper takes it off
(`town_boards.normalize`), as it does a mailbox named for an office; one
address per member ships, a town's own domain first where both are printed;
an address `scripts/undeliverable.py` lists is withheld; and a number printed
without an area code ships exactly as printed. Never an address: the
directories print home addresses beside these names, and a town supervisor's
house is not an office. Every number that ships must have the shape of one
telephone number (`check_phones`) and every e-mail address the shape of one
address (`check_emails`), and a county whose directory was read must ship at
least its floor of members with a number (`MIN_PHONES`) and with an e-mail
address (`MIN_EMAILS`), so a layout change that stops either being read fails
the build instead of emptying them quietly.

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
# the fleet-wide list of addresses mail cannot reach, at the repo root
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "scripts"))
import undeliverable  # noqa: E402
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


# The keys a board member's record may carry. Anything else a county module
# returns is dropped here, so a parser change can never put an address on a
# card.
FIELDS = ("name", "role", "phone", "phonesExtra", "email")

# MEMBERS WITH A NUMBER, PER COUNTY, a floor at about two thirds of what the
# directories gave on the first read after Adam's ruling of 2026-10-17, read
# live on 2026-10-17 (the measured count is the comment beside each).
# Trempealeau's directory prints no numbers for its town boards and has no
# floor. Checked only for a county whose directory was read this run; a county
# carried forward keeps what it had.
MIN_PHONES = {
    "007": 55,   # Bayfield, 83 measured
    "009": 26,   # Brown, 40 measured
    "013": 39,   # Burnett, 59 measured
    "017": 50,   # Chippewa, 75 measured
    "019": 63,   # Clark, 95 measured
    "021": 46,   # Columbia, 69 measured
    "023": 7,    # Crawford, 11 measured
    "029": 36,   # Door, 55 measured
    "031": 28,   # Douglas, 43 measured
    "035": 7,    # Eau Claire, 11 measured
    "037": 14,   # Florence, 21 measured
    "039": 41,   # Fond du Lac, 62 measured
    "043": 64,   # Grant, 97 measured
    "045": 30,   # Green, 46 measured
    "051": 19,   # Iron, 29 measured
    "055": 32,   # Jefferson, 49 measured
    "057": 38,   # Juneau, 58 measured
    "059": 10,   # Kenosha, 15 measured
    "061": 18,   # Kewaunee, 28 measured
    "067": 32,   # Langlade, 48 measured
    "071": 36,   # Manitowoc, 54 measured
    "073": 78,   # Marathon, 117 measured
    "077": 25,   # Marquette, 38 measured
    "081": 46,   # Monroe, 70 measured
    "083": 4,    # Oconto, 6 measured
    "085": 42,   # Oneida, 64 measured
    "087": 39,   # Outagamie, 59 measured
    "089": 13,   # Ozaukee, 20 measured
    "093": 36,   # Pierce, 55 measured
    "097": 36,   # Portage, 55 measured
    "099": 32,   # Price, 48 measured
    "101": 12,   # Racine, 18 measured
    "109": 54,   # St. Croix, 81 measured
    "111": 50,   # Sauk, 75 measured
    "113": 7,    # Sawyer, 11 measured
    "115": 50,   # Shawano, 76 measured
    "117": 42,   # Sheboygan, 64 measured
    "119": 42,   # Taylor, 64 measured
    "123": 41,   # Vernon, 62 measured
    "127": 38,   # Walworth, 57 measured
    "129": 41,   # Washburn, 62 measured
    "131": 14,   # Washington, 22 measured
    "133": 20,   # Waukesha, 30 measured
    "135": 38,   # Waupaca, 57 measured
    "139": 32,   # Winnebago, 48 measured
    "141": 48,   # Wood, 73 measured
}

# MEMBERS WITH AN E-MAIL ADDRESS, PER COUNTY, a floor at about two thirds of
# what the directories gave on the first read after Adam's choice of
# 2026-10-17 ("E-mails too"), read live on 2026-10-17 (the measured count is
# the comment beside each). A county whose directory prints no address beside
# a board member has no floor, and nor has Sawyer, whose one address would
# make a floor of two thirds round to nothing. Checked only for a county whose
# directory was read this run.
MIN_EMAILS = {
    "007": 52,   # Bayfield, 79 measured
    "009": 22,   # Brown, 34 measured
    "013": 38,   # Burnett, 57 measured
    "017": 28,   # Chippewa, 42 measured
    "019": 27,   # Clark, 41 measured
    "021": 30,   # Columbia, 45 measured
    "029": 33,   # Door, 50 measured
    "031": 14,   # Douglas, 21 measured
    "035": 3,    # Eau Claire, 5 measured
    "037": 8,    # Florence, 13 measured
    "039": 32,   # Fond du Lac, 49 measured
    "043": 50,   # Grant, 76 measured
    "045": 20,   # Green, 31 measured
    "055": 30,   # Jefferson, 45 measured
    "057": 10,   # Juneau, 15 measured
    "059": 4,    # Kenosha, 7 measured
    "061": 18,   # Kewaunee, 28 measured
    "067": 17,   # Langlade, 26 measured
    "077": 24,   # Marquette, 36 measured
    "083": 1,    # Oconto, 2 measured
    "085": 34,   # Oneida, 51 measured
    "087": 36,   # Outagamie, 55 measured
    "089": 14,   # Ozaukee, 21 measured
    "093": 20,   # Pierce, 31 measured
    "097": 26,   # Portage, 39 measured
    "101": 8,    # Racine, 13 measured
    "109": 38,   # St. Croix, 57 measured
    "111": 46,   # Sauk, 69 measured
    "115": 34,   # Shawano, 52 measured
    "119": 1,    # Taylor, 2 measured
    "123": 28,   # Vernon, 42 measured
    "127": 26,   # Walworth, 39 measured
    "129": 34,   # Washburn, 52 measured
    "133": 16,   # Waukesha, 25 measured
    "135": 40,   # Waupaca, 61 measured
    "139": 15,   # Winnebago, 23 measured
    "141": 38,   # Wood, 57 measured
}

# A telephone number as `town_boards.phones_in` writes one: an optional label
# word, the number (with or without its area code, exactly as printed) and an
# optional extension, and nothing else — no street word, ZIP code, "@" or
# second number can match.
_PHONE_SHAPE = re.compile(
    r"^(?:(?:cell|home|work|business|office|mobile|personal|residence)\s+)?"
    r"(?:(?:\(\d{3}\)\s*[-.]?\s*|\d{3}\s?[-./ ]\s?)?\d{3}\s?[-.]\s?\d{4}"
    r"|\d{3} \d{3} \d{4})"
    r"(?:\s*(?:ext\.?|x)\s*\d{1,5})?$", re.I)


# One e-mail address and nothing else: no space, one "@", a dot in the domain
# and a top-level domain of letters.
_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def check_emails(towns, county_names):
    """Every `email` value that would ship is exactly one e-mail address. A
    failure names the county, the town's GEOID and the member's role, never
    the value."""
    problems = []
    for geoid, rec in sorted(towns.items()):
        for p in rec.get("board") or []:
            if "email" not in p:
                continue
            v = p["email"]
            if not isinstance(v, str) or not _EMAIL_SHAPE.match(v):
                problems.append("%s County, town %s, %s: the e-mail value is "
                                "not the shape of one e-mail address"
                                % (county_names.get(rec.get("county"), "?"),
                                   geoid, p.get("role")))
    return problems


def board_row(p, where):
    """The record that ships for one member: the keys in FIELDS that carry a
    value, with an address `undeliverable.withhold` lists taken off."""
    row = {k: p[k] for k in FIELDS if p.get(k)}
    if row.get("email"):
        addr, _why = undeliverable.withhold(row["email"], where)
        if addr:
            row["email"] = addr
        else:
            del row["email"]
    return row


def check_phones(towns, county_names):
    """Every `phone` and `phonesExtra` value that would ship has the shape
    of one telephone number. A failure names the county, the town's GEOID
    and the member's role, never the value."""
    problems = []
    for geoid, rec in sorted(towns.items()):
        for p in rec.get("board") or []:
            values = [p.get("phone")] if "phone" in p else []
            extra = p.get("phonesExtra")
            if extra is not None and not isinstance(extra, list):
                values.append(None)
            else:
                values += list(extra or [])
            for v in values:
                if not isinstance(v, str) or "@" in v or not _PHONE_SHAPE.match(v):
                    problems.append("%s County, town %s, %s: a telephone value "
                                    "is not the shape of one telephone number"
                                    % (county_names.get(rec.get("county"), "?"),
                                       geoid, p.get("role")))
    return problems


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
            towns_out[geoid] = {"county": fips, "board": [
                board_row(p, "%s County, %s, %s" % (mod.COUNTY_NAME, town,
                                                     p.get("role")))
                for p in people]}
            # a town counts as named with any member: a chair the county prints
            # as vacant leaves the supervisors it does name
            matched += 1
        need = floor_for(mod, len(index))
        members = [p for g, t in towns_out.items() if t["county"] == fips
                   for p in t["board"]]
        with_phone = sum(1 for p in members if p.get("phone"))
        phone_floor = MIN_PHONES.get(fips, 0)
        with_email = sum(1 for p in members if p.get("email"))
        email_floor = MIN_EMAILS.get(fips, 0)
        line = "%-12s %3d of %3d towns named (floor %d); %d of %d members " \
               "with a number (floor %d), %d with a second; %d with an " \
               "e-mail (floor %d)" % (
                   mod.COUNTY_NAME, matched, len(index), need, with_phone,
                   len(members), phone_floor,
                   sum(1 for p in members if p.get("phonesExtra")),
                   with_email, email_floor)
        if unmatched:
            line += "; unmatched: " + ", ".join(unmatched)
        print(line)
        if matched < need:
            problems.append("%s: %d towns named, floor %d" %
                            (mod.COUNTY_NAME, matched, need))
        if with_phone < phone_floor:
            problems.append("%s: %d members with a telephone number, floor %d"
                            % (mod.COUNTY_NAME, with_phone, phone_floor))
        if with_email < email_floor:
            problems.append("%s: %d members with an e-mail address, floor %d"
                            % (mod.COUNTY_NAME, with_email, email_floor))
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
    for name, floors in (("MIN_PHONES", MIN_PHONES), ("MIN_EMAILS", MIN_EMAILS)):
        for fips in floors:
            if fips not in counties or counties[fips].get("status") != "published":
                problems.append("%s names county %s, which has no "
                                "published list" % (name, fips))
    names = {f: c["county"] for f, c in counties.items()}
    problems += check_phones(towns_out, names)
    problems += check_emails(towns_out, names)
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
            "about": "Wisconsin town boards as each county publishes them: "
                     "names, roles, and the telephone numbers and e-mail "
                     "address the county prints beside each member (Adam, "
                     "2026-10-17). wi/scripts/build_wi_town_boards.py",
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
    members = [p for t in towns.values() for p in t["board"]]
    print("OK  %d towns, %d people (%d with a telephone number, %d with a "
          "second, %d with an e-mail address), %d of %d counties publish a "
          "list"
          % (len(towns), people, sum(1 for p in members if p.get("phone")),
             sum(1 for p in members if p.get("phonesExtra")),
             sum(1 for p in members if p.get("email")), published,
             len(counties)))


if __name__ == "__main__":
    main()
