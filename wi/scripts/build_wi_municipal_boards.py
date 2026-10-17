#!/usr/bin/env python3
"""
Write data/app/wi-municipal-boards.json — the governing bodies of the Wisconsin
municipalities that elect their WHOLE board AT LARGE. Stage 2 of the pair;
wi_municipal_board_scraper.py produces the intermediate.

WHY A SEPARATE FILE FROM `wi-alderpersons.json`, stated once here because it is
the only reason this pair exists: that file is keyed by DISTRICT. A city whose
council is elected citywide has no district, and seating its members under
numbers would tell a reader they were elected in a way they were not. So these
rows carry a ROLE and no district, and the City-or-Village card renders them in
their own labelled block.

THE SHAPE IS ILLINOIS'S, not a new one. `il/data/app/municipal-officials.json`
already carries a `board` list of people with a role and no district, keyed by
the place's 7-digit GEOID, rendered on a municipal card; Iowa already shows
at-large members under their own heading. The fleet rule is to reuse the shape a
live app already has, so this file is that shape with Wisconsin's own keys.

ONE FLOOR PER CITY, NEVER A TOTAL. A total lets one city's rows disappear while
another's grow, which is the defect per-county floors exist to prevent
everywhere else in this fleet. Each entry is (name, seats, min emails, min
phones); a city that resolves fewer than its seats, or loses a contact column,
fails the build. A city that publishes a second number per member has a floor
for those too (MIN_PHONES_EXTRA).

EVERY NUMBER A CITY PRINTS BESIDE A MEMBER SHIPS, since 2026-10-17. Adam ruled
that day, for every state: "if the official government source uses personal
phone numbers, we publish those." So a member's first number is `phone` and any
further one is in `phonesExtra`, with the label the city prints ("cell ...").
Every value is held to ONE telephone number by wi/scripts/wi_phone_shape.py
before anything is written, and a failure names the city and the member's
position in its list, never the value.

A CITY THAT COULD NOT BE READ KEEPS ITS LAST-GOOD ROWS. "Preserve data we have
already fetched" (Adam, 2026-09-19): a refusal or an unreachable host stops the
FETCH and never unpublishes what was fetched legitimately. So a missing city is
carried forward from the shipped file with a `carriedFrom` date and the reason,
which the card prints — never deleted, and never shown as freshly read.

THE ONE NORMALISATION, AND WHY IT IS THE ONLY ONE. Caledonia publishes its own
seat labels inconsistently, five as `Trustee N` and one as `Trustee #N`, so a
card printing both reads as a defect in the app rather than as the village's own
punctuation. The `#` is dropped and nothing else about a role is touched: this is
the `PARTY_NAMES` precedent, which maps notation and decides nothing about a
person. A name is never normalised beyond collapsing whitespace.
"""

import datetime
import io
import json
import os
import re
import sys

import wi_phone_shape                    # this script's own folder

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
RAW = os.path.join(SCRIPT_DIR, ".cache", "wi_municipal_boards_raw.json")
OUT = os.path.join(REPO_ROOT, "data", "app", "wi-municipal-boards.json")

# label -> (place name, seats, min emails, min phones)
FLOORS = {
    "Caledonia": ("Caledonia", 7, 7, 7),
    "Oshkosh": ("Oshkosh", 7, 7, 6),
    # Janesville's seven all carry a city e-mail and a direct city line, so 7
    # is every member. The city also publishes a Cell Phone column; since
    # 2026-10-17 the scraper emits it as a second number, floored below.
    "Janesville": ("Janesville", 7, 7, 7),
    # The tranche of 2026-10-15. Mount Pleasant prints an e-mail and a phone
    # for all seven. Menomonee Falls prints neither: its one phone is the
    # village's main line on every card and its e-mail is a form. Fond du Lac
    # prints both for all seven.
    "Mount Pleasant": ("Mount Pleasant", 7, 7, 7),
    "Menomonee Falls": ("Menomonee Falls", 7, 0, 0),
    "Fond du Lac": ("Fond du Lac", 7, 7, 7),
}

# label -> the fewest members that must carry a second number (`phonesExtra`).
# Janesville prints a Cell Phone for five of its seven members beside the city
# line (measured 2026-10-17); the floor is about two thirds of that, so a page
# change that stops the column being read fails the build instead of emptying
# it quietly.
MIN_PHONES_EXTRA = {
    "Janesville": 3,
}


# THE GEOID IS CHECKED AGAINST THE PLACE FABRIC, NEVER TAKEN ON TRUST. The
# scraper carries each municipality's 7-digit Census place id so the card can
# join it to the place under the reader's point, and that id is a thing a person
# types: the first draft of this pair shipped Caledonia as 5512050, which is no
# place at all, and the card would simply have found nothing and said nothing
# with every gate green. `wi-municipal-clerks.json` is keyed by that same id for
# all 608 of Wisconsin's cities and villages, so it is the fabric to check
# against, and the municipality's NAME must agree there too — a valid id for the
# wrong town is the failure a bare presence check would let through.
CLERKS = os.path.join(REPO_ROOT, "data", "app", "wi-municipal-clerks.json")


def place_fabric():
    with io.open(CLERKS, encoding="utf-8") as f:
        return {k: (v.get("municipality") or "") for k, v in json.load(f).items()}


def load_shipped():
    if not os.path.exists(OUT):
        return {}
    with io.open(OUT, encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    raw_path = argv[argv.index("--raw") + 1] if "--raw" in argv else RAW
    if not os.path.exists(raw_path):
        print("no intermediate at %s — run wi_municipal_board_scraper.py first"
              % os.path.relpath(raw_path), file=sys.stderr)
        return 1
    with io.open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    fabric = place_fabric()
    shipped = load_shipped()
    today = datetime.date.today().isoformat()
    out, notes = {}, []

    for label, (place, seats, min_emails, min_phones) in sorted(FLOORS.items()):
        city = raw.get("cities", {}).get(label)
        if not city:
            reason = raw.get("failures", {}).get(label, "not read on this run")
            # CARRY FORWARD, keyed by whichever shipped record names this place.
            carried = None
            for key, rec in shipped.items():
                if rec.get("name") == place:
                    carried = (key, rec)
                    break
            if carried:
                key, rec = carried
                rec = dict(rec)
                rec.setdefault("carriedFrom", today)
                rec["carriedWhy"] = reason
                out[key] = rec
                notes.append("%s: carried forward (%s)" % (label, reason))
            else:
                notes.append("%s: not read and nothing shipped to carry (%s)"
                             % (label, reason))
            continue

        geoid = str(city["geoid"])
        if fabric.get(geoid) != place:
            print("%s: geoid %s names %r in the statewide place fabric, not %r; "
                  "refusing to write" % (label, geoid,
                                         fabric.get(geoid) or "no place",
                                         place), file=sys.stderr)
            return 1

        members = []
        for m in city["board"]:
            role = re.sub(r"#\s*(\d)", r"\1", str(m["role"])).strip()
            row = {"name": str(m["name"]), "role": role}
            if m.get("email"):
                row["email"] = str(m["email"])
            if m.get("phone"):
                row["phone"] = str(m["phone"])
            if m.get("phonesExtra"):
                row["phonesExtra"] = [str(p) for p in m["phonesExtra"]]
            bad = wi_phone_shape.problems(row, "%s member %d" % (label, len(members) + 1))
            if bad:
                for line in bad:
                    print("%s — refusing to write" % line, file=sys.stderr)
                return 1
            members.append(row)

        if len(members) < seats:
            print("%s: %d member(s) resolved against a floor of %d; refusing to "
                  "write" % (label, len(members), seats), file=sys.stderr)
            return 1
        emails = sum(1 for m in members if m.get("email"))
        phones = sum(1 for m in members if m.get("phone"))
        seconds = sum(1 for m in members if m.get("phonesExtra"))
        if emails < min_emails or phones < min_phones:
            print("%s: %d e-mail(s) and %d phone(s) against floors of %d and %d; "
                  "refusing to write" % (label, emails, phones, min_emails,
                                         min_phones), file=sys.stderr)
            return 1
        if seconds < MIN_PHONES_EXTRA.get(label, 0):
            print("%s: %d member(s) carry a second number against a floor of %d; "
                  "refusing to write" % (label, seconds, MIN_PHONES_EXTRA[label]),
                  file=sys.stderr)
            return 1

        # NOT EVERY BODY HERE SAYS IT IS ELECTED AT LARGE. Menomonee Falls
        # says its trustees are elected "by numbered seat" and Fond du Lac does
        # not say at all; neither draws a district. Such a city carries
        # `atLarge: false` and the scraper's `howElected`, which repeats what
        # the city says, and the card prints that sentence instead of claiming
        # an election method the city never stated.
        at_large = city.get("atLarge") is True
        record = {
            "name": place,
            "county": city.get("county"),
            "atLarge": at_large,
            "board": members,
            "asOf": today,
            "sourceUrl": city.get("sourceUrl"),
        }
        if not at_large:
            how = str(city.get("howElected") or "").strip()
            if not how:
                print("%s: not marked at large and says nothing about how it "
                      "is elected; refusing to write" % label, file=sys.stderr)
                return 1
            record["howElected"] = how
        out[geoid] = record
        notes.append("%s: %d member(s), %d e-mail(s), %d phone(s), %d with a "
                     "second number" % (label, len(members), emails, phones, seconds))

    if not out:
        print("nothing to write", file=sys.stderr)
        return 1

    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    for line in notes:
        print(line)
    print("wrote %s — %d municipality/municipalities, %d member(s)"
          % (os.path.relpath(OUT, REPO_ROOT), len(out),
             sum(len(v["board"]) for v in out.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
