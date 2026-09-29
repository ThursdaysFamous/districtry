#!/usr/bin/env python3
"""
Stage 1 of Winnebago County's municipal-officials pipeline: read the twelve
municipal officeholder layers WinGIS publishes and emit the payload shape
build_municipal_officials_roster.py consumes.

WHY THIS SOURCE IS UNUSUAL — and why it is a scraper at all. Winnebago is the
only county in the fleet that publishes MUNICIPAL GOVERNING BODIES AS GIS
LAYERS: one layer per municipality on WinGIS's ElectedOfficials service,
carrying the village president or mayor and every trustee by name. Everywhere
else this data comes from a clerk's directory page or a PDF.

That makes it a rule-4 branch 2 source with an odd shape, not a branch 1: the
officials do NOT ride the boundary a card queries (the municipality layer is
statewide TIGER places), so they cannot be read at query time — they have to be
resolved to Census place GEOIDs and shipped in municipal-officials.json like
every other county's.

THREE LAYER SHAPES, because the county did not normalise them:

  WIDE      one feature, one column per seat — "President"/"Mayor" plus
            Trustee1..N or Commissioner1..N. Nine municipalities.
  PER-WARD  one feature per ward. Loves Park elects TWO aldermen per ward
            (Alderman1/Alderman2, each with its own phone); Machesney Park
            elects one trustee per district, with a phone.
  ROCKFORD  split across two layers — the mayor on one, the 14 WARDS on
            another. Only the mayor's NAME comes from WinGIS: since 2026-09-29
            the fourteen alderpersons come from the city's own directory
            (rockford_alderperson_scraper.py), joined to the ward layer by
            ward. See ROCKFORD'S PEOPLE below.

Two municipalities (Loves Park, Machesney Park) have NO head-of-government layer
— WinGIS publishes their council seats only. Their mayors ship anyway, carried
from the County Clerk's elections office, which named both in writing when
asked (EMAIL_CARRIED_HEADS below) — still never inferred, and re-read never
pretended: every run prints how old that e-mail is.

ROCKFORD'S PEOPLE ARE NOT WINGIS'S. Layer 20 carries an `Alderman` and an
`Email` column on every ward polygon, and this scraper read them until
2026-09-29. Joined ward-for-ward against the city's own directory that day the
two sources agreed on all fourteen WARDS and disagreed on two SEATS — ward 3
Tuneburg/Tuneberg and ward 7 Wilkins/Neal — with each layer address spelled
from the layer's own spelling, so both cards sent a reader to an address the
city does not publish. The layer's people column is a snapshot; the city's
directory is maintained. So the ward NUMBERS still come from the layer (it is
the geometry the ward card draws) and the PEOPLE come from the city, joined by
ward, with the join printed every run and a ward-set mismatch fatal. The
geometry is untouched and was separately measured current. This is the Coles
pattern, and the same call made for Freeport one county over.

Nothing is inferred from column ORDER: a seat is emitted only when its column
holds a name, so a village that leaves Trustee6 empty ships five trustees
rather than a blank sixth.

Contact is PER-PERSON here, unlike the Cook DOEO API's municipality-level hall
contact, so it is emitted as `person_phone`/`person_email` — the builder's field
names for contact it may attach to an individual. Emitting plain `phone`/`email`
looks right and is silently DROPPED: the builder reads only the person_* keys,
by design, so a municipality-level number can never be printed as if it reached
one trustee directly.

The mayor's office WEBSITE that layer 19 carries is not emitted: the roster has
no per-person link field (only a municipality-level `url`), and a mayor's office
page is not the municipality's site.

Usage:
    python3 winnebago_municipal_officials_scraper.py [output.json]
"""

import argparse
import datetime
import json
import re
import sys
import urllib.parse
import urllib.request
from scraper_common import UA_CHROME_X11_120  # noqa: E402  (shared machinery — do not fork)
# One reader of Rockford's council directory, shared rather than re-scraped: the
# ward card and this roster must not be free to disagree about who holds a seat.
# Its INDEX_URL is imported rather than restated: a second copy of the address
# would be a second thing to keep true, and it would also put a rockfordil.gov
# literal in this file, which sends a browser string and does not fetch that
# host — probe_user_agents.py reads URL literals per file and would read the
# citation as a fetch.
from rockford_alderperson_scraper import (  # noqa: E402  (one reader, not a fork)
    INDEX_URL as ROCKFORD_DIRECTORY_URL,
    scrape as scrape_rockford_directory,
)

BASE = "https://maps.wingis.org/public/rest/services/ElectedOfficials/MapServer"
DIRECTORY_URL = "https://wingis.org/maps/electedofficials"
COUNTY = "Winnebago"
TIMEOUT = 90
USER_AGENT = UA_CHROME_X11_120

# layer -> how to read it. `name` is the municipality as the app's TIGER places
# layer spells it; the layers' own CityName is upper-cased and South Beloit's
# service is even titled "SouthBeloit", so the name is stated here rather than
# derived from a field that would need re-casing anyway.
WIDE = "wide"
PER_WARD = "per-ward"
# A per-ward layer whose `people` is this supplies ward numbers only; its
# officeholders come from the municipality's own directory.
CITY_DIRECTORY = "city-directory"

LAYERS = [
    {"id": 13, "name": "Cherry Valley", "shape": WIDE, "head": "President", "seat": "Trustee"},
    {"id": 14, "name": "Durand", "shape": WIDE, "head": "Mayor", "seat": "Trustee"},
    {"id": 17, "name": "New Milford", "shape": WIDE, "head": "President", "seat": "Trustee"},
    {"id": 18, "name": "Pecatonica", "shape": WIDE, "head": "President", "seat": "Trustee"},
    {"id": 21, "name": "Rockton", "shape": WIDE, "head": "Mayor", "seat": "Trustee"},
    {"id": 22, "name": "Roscoe", "shape": WIDE, "head": "President", "seat": "Trustee"},
    {"id": 23, "name": "South Beloit", "shape": WIDE, "head": "Mayor", "seat": "Commissioner"},
    {"id": 24, "name": "Winnebago", "shape": WIDE, "head": "President", "seat": "Trustee"},
    # Loves Park: two aldermen per ward, each with its own phone column.
    {"id": 15, "name": "Loves Park", "shape": PER_WARD, "district": "Ward",
     "seats": [("Alderman1", "Alderman1Phone"), ("Alderman2", "Alderman2Phone")],
     "office": "Alderperson"},
    # Machesney Park: one trustee per district.
    {"id": 16, "name": "Machesney Park", "shape": PER_WARD, "district": "District",
     "seats": [("Trustee", "Ph_Number")], "office": "Trustee"},
    # Rockford is split across two layers; both are declared so the municipality
    # is built from the same table as the others rather than a special case.
    {"id": 19, "name": "Rockford", "shape": WIDE, "head": "Mayor", "seat": None,
     "head_email": "Email"},
    # Layer 20 supplies Rockford's fourteen WARD NUMBERS and nothing else. Its
    # own Alderman/Email columns are read NOWHERE (see ROCKFORD'S PEOPLE above).
    {"id": 20, "name": "Rockford", "shape": PER_WARD, "district": "Ward",
     "seats": [], "office": "Alderperson", "people": CITY_DIRECTORY},
]

# Aggregate floors, deliberately under the 2026-07 live values (11
# municipalities / 9 heads / 75 seats / 16 phones / 15 e-mails). Per-municipality
# floors would be eleven separate guards over bodies of five to fifteen people,
# where one retirement reads as a collapse.
#
# HEADS IS 11 SINCE 2026-08-17, AND TWO OF THEM ARE NOT SCRAPED: WinGIS
# publishes no mayor/president layer for Loves Park or Machesney Park, only
# their council seats. Asked directly, the County Clerk's elections office
# (KHockison@clerk.wincoil.gov) named both heads by e-mail on 2026-08-17, and
# titled the Machesney Park seat MAYOR — its own word, which is what ships.
# Her e-mail lists each mayor's home address; neither ships (the Washington
# rule). The two ride EMAIL_CARRIED_HEADS below rather than a layer, so a
# weekly run refreshes ten layers and re-reads no e-mail — the NOT RE-READ
# line in main() pays that honesty cost out loud, the Edwards convention.
#
# The floors sit just under the live values rather than well under, because a
# failed layer is now fatal (see main) — so these guard a COLUMN rename, which
# shows up as a quiet shortfall, not a fetch failure, which stops the run.
MIN_MUNICIPALITIES = 11
MIN_HEADS = 11
MIN_SEATS = 70

# The two heads WinGIS does not publish, carried from the county's own
# election authority. Names only — the e-mail's home addresses never ship.
EMAIL_CARRIED_HEADS = {
    "Loves Park": {"name": "Greg Jury", "office": "Mayor"},
    "Machesney Park": {"name": "Steve Johnson", "office": "Mayor"},
}
EMAIL_HEADS_SOURCE = ("Winnebago County Clerk's elections office, by e-mail "
                      "2026-08-17")
EMAIL_HEADS_VERIFIED = "2026-08-17"


def get_json(url, params):
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + query, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def rows(layer_id):
    payload = get_json("%s/%d/query" % (BASE, layer_id), {
        "where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "json",
    })
    if "error" in payload:
        raise RuntimeError("layer %d: %s" % (layer_id, payload["error"].get("message")))
    return [f.get("attributes") or {} for f in payload.get("features") or []]


def clean(value):
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def clean_phone(value):
    text = clean(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None  # a partial or malformed number is dropped, never padded
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def read_wide(spec, attrs):
    out = []
    head = clean(attrs.get(spec["head"]))
    if head:
        person = {"office": spec["head"], "name": head}
        if spec.get("head_email"):
            email = clean(attrs.get(spec["head_email"]))
            if email:
                person["person_email"] = email
        out.append(person)
    seat = spec.get("seat")
    if seat:
        # Walk the numbered columns the layer actually has, in order, and emit a
        # seat only where a name sits. Column COUNT is not the seat count: some
        # villages leave a trailing column empty between appointments.
        index = 1
        while True:
            column = "%s%d" % (seat, index)
            if column not in attrs:
                break
            name = clean(attrs.get(column))
            if name:
                out.append({"office": seat, "name": name})
            index += 1
    return out


def read_per_ward(spec, attrs):
    out = []
    district = clean(attrs.get(spec["district"]))
    for name_col, phone_col in spec["seats"]:
        name = clean(attrs.get(name_col))
        if not name:
            continue
        person = {"office": spec["office"], "name": name}
        if district:
            person["district"] = "Ward %s" % district
        if phone_col:
            phone = clean_phone(attrs.get(phone_col))
            if phone:
                person["person_phone"] = phone
        if spec.get("email"):
            email = clean(attrs.get(spec["email"]))
            if email:
                person["person_email"] = email
        out.append(person)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="winnebago_municipal_officials.json")
    args = ap.parse_args()

    officials = []
    municipalities = []
    directory_layers = []   # (spec, ward numbers) for the city-directory shape
    # EVERY LAYER MUST ANSWER, or this run produces nothing. WinGIS is
    # intermittently flaky (a run during development lost layer 19 and shipped a
    # Rockford with no mayor, under an aggregate floor that could not tell the
    # difference between "the county has 9 heads" and "we failed to read one").
    # Twelve small layers have no honest partial state, and the pipeline already
    # has the right answer for a failed source: the workflow's continue-on-error
    # plus PRESERVABLE carries the whole county forward from the shipped roster.
    # So a single failure is fatal here rather than a quiet coverage loss.
    for spec in LAYERS:
        try:
            data = rows(spec["id"])
        except Exception as exc:  # noqa: BLE001
            print("winnebago-municipal: FATAL — layer %d (%s) failed: %s. Refusing to "
                  "emit a partial county; the roster build will carry Winnebago "
                  "forward from the shipped file."
                  % (spec["id"], spec["name"], exc), file=sys.stderr)
            sys.exit(1)
        if spec.get("people") == CITY_DIRECTORY:
            # Ward numbers only. The people arrive after the loop, from the
            # city, so that a directory failure cannot leave a half-built
            # municipality behind in `officials`.
            wards = sorted({clean(a.get(spec["district"])) for a in data} - {None},
                           key=lambda w: (len(w), w))
            if not wards:
                print("winnebago-municipal: FATAL — layer %d (%s) returned rows but "
                      "no ward numbers; the %s column changed."
                      % (spec["id"], spec["name"], spec["district"]), file=sys.stderr)
                sys.exit(1)
            directory_layers.append((spec, wards))
            if spec["name"] not in municipalities:
                municipalities.append(spec["name"])
            continue
        found = []
        for attrs in data:
            found.extend(read_wide(spec, attrs) if spec["shape"] == WIDE
                         else read_per_ward(spec, attrs))
        if not found:
            print("winnebago-municipal: FATAL — layer %d (%s) returned rows but no "
                  "officials; the column names changed."
                  % (spec["id"], spec["name"]), file=sys.stderr)
            sys.exit(1)
        if spec["name"] not in municipalities:
            municipalities.append(spec["name"])
        for person in found:
            person["jurisdiction"] = spec["name"]
            officials.append(person)

    # THE CITY-DIRECTORY JOIN, PRINTED EVERY RUN. The ward layer says which
    # wards exist and the city says who holds them; nothing here reconciles a
    # disagreement, because there is no honest way to. A ward the city does not
    # name, or a ward the city names that the layer does not draw, is a
    # question for a person — so this refuses and the whole county carries
    # forward from the shipped roster rather than shipping a council that is
    # short, or one seated in a ward the map cannot draw.
    for spec, wards in directory_layers:
        try:
            by_ward = scrape_rockford_directory()
        except Exception as exc:  # noqa: BLE001 — reported, not swallowed
            print("winnebago-municipal: FATAL — %s's own council directory could not "
                  "be read: %s. Refusing to emit a %s with no council; the roster "
                  "build will carry Winnebago forward from the shipped file."
                  % (spec["name"], exc, spec["name"]), file=sys.stderr)
            sys.exit(1)
        layer_wards = sorted(int(w) for w in wards if str(w).strip().isdigit())
        if len(layer_wards) != len(wards):
            print("winnebago-municipal: FATAL — layer %d (%s) publishes a ward that "
                  "is not a number: %s" % (spec["id"], spec["name"], wards),
                  file=sys.stderr)
            sys.exit(1)
        city_wards = sorted(by_ward)
        print("  %s: ward layer %d wards, city directory %d seats"
              % (spec["name"], len(layer_wards), len(city_wards)))
        for ward in sorted(set(layer_wards) | set(city_wards)):
            seat = by_ward.get(ward)
            print("    ward %-3s %-6s %-22s %s"
                  % (ward,
                     "map+city" if (ward in by_ward and ward in layer_wards)
                     else ("map only" if ward in layer_wards else "city only"),
                     (seat or {}).get("name") or "-",
                     (seat or {}).get("email") or "-"))
        if set(layer_wards) != set(city_wards):
            print("winnebago-municipal: FATAL — %s's ward layer and the city's own "
                  "directory no longer name the same wards (map %s, city %s). That "
                  "is a question for a person, not a partial roster."
                  % (spec["name"], layer_wards, city_wards), file=sys.stderr)
            sys.exit(1)
        for ward in city_wards:
            seat = by_ward[ward]
            person = {
                "office": spec["office"],
                "name": seat["name"],
                "district": "%s %d" % (spec["district"], ward),
                "jurisdiction": spec["name"],
            }
            if seat.get("email"):
                person["person_email"] = seat["email"]
            if seat.get("phone"):
                person["person_phone"] = seat["phone"]
            # Provenance is per person here, because this municipality's entry
            # has two publishers: the mayor is WinGIS's row and these fourteen
            # are the city's own pages. The payload's county-level
            # `directory_url` still describes the payload; it must not be
            # stamped on people it did not supply.
            person["source_url"] = seat.get("url") or ROCKFORD_DIRECTORY_URL
            officials.append(person)

    # The two e-mail-carried heads join here, and never silently: each run
    # names the source and its age, because a scrape that "refreshes" a
    # hand-carried row refreshes nothing.
    try:
        _v = datetime.date.fromisoformat(EMAIL_HEADS_VERIFIED)
        _age = ", %d days old" % (datetime.date.today() - _v).days
    except Exception:
        _age = ""
    for _place, _spec in EMAIL_CARRIED_HEADS.items():
        if _place not in municipalities:
            print("winnebago-municipal: FATAL — %s is not among the scraped "
                  "municipalities; the e-mail-carried head has nothing to attach to"
                  % _place, file=sys.stderr)
            sys.exit(1)
        print("winnebago-municipal: NOT RE-READ — %s's %s (%s) comes from %s%s. "
              "Re-ask the office to refresh."
              % (_place, _spec["office"], _spec["name"], EMAIL_HEADS_SOURCE, _age),
              file=sys.stderr)
        officials.append({"name": _spec["name"], "office": _spec["office"],
                          "jurisdiction": _place,
                          "source_note": EMAIL_HEADS_SOURCE})

    heads = sum(1 for p in officials if p["office"].lower() in ("mayor", "president"))
    seats = len(officials) - heads
    problems = []
    if len(municipalities) < MIN_MUNICIPALITIES:
        problems.append("%d municipalities (< %d)" % (len(municipalities), MIN_MUNICIPALITIES))
    if heads < MIN_HEADS:
        problems.append("%d heads (< %d)" % (heads, MIN_HEADS))
    if seats < MIN_SEATS:
        problems.append("%d seats (< %d)" % (seats, MIN_SEATS))
    if problems:
        print("winnebago-municipal: FATAL — refusing to write a payload that lost "
              "coverage: %s" % "; ".join(problems), file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for person in officials:
        if person.get("source_note"):
            continue  # e-mail-carried: its provenance is its own, not the directory's
        # A person who already carries a source keeps it: the city-directory
        # join sets its own, and overwriting it here would cite WinGIS for
        # fourteen people WinGIS does not publish.
        person.setdefault("source_url", DIRECTORY_URL)
        person["scraped_at"] = scraped_at
    payload = {
        "county": COUNTY,
        "directory_url": DIRECTORY_URL,
        "scraped_at": scraped_at,
        "municipalities": [{"name": n, "source_url": DIRECTORY_URL,
                            "scraped_at": scraped_at} for n in municipalities],
        "officials": officials,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    phones = sum(1 for p in officials if p.get("person_phone"))
    emails = sum(1 for p in officials if p.get("person_email"))
    print("winnebago-municipal: %d municipalities, %d officials (%d heads, %d seats, "
          "%d phones, %d e-mails) -> %s"
          % (len(municipalities), len(officials), heads, seats, phones, emails, args.out))


if __name__ == "__main__":
    main()
