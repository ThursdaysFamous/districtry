#!/usr/bin/env python3
"""
Build data/app/township-officials.json — the township card's officeholder
roster — keyed by the 10-digit Census county-subdivision GEOID the app's
township layer already carries on every TIGERweb feature, so the runtime
join needs no name normalization (the municipal-officials pattern exactly).

WHY THIS FILE EXISTS. Township officers were a RECORDED CANDIDATE, not a new
idea: EXPANSION_GUIDE Appendix A carried "officer candidate via clerk
yearbooks" on the township row, Pattern A (§1.4) named the concept, and a
dozen municipal scrapers deliberately bound their county's township section
OUT "so a future township scrape is additive". This is that scrape's first
county. Cook launches it because its source is the cleanest in the fleet:
the County Clerk's directory API publishes every township's governing
officials as structured JSON under the TWNSP jurisdiction type — the same
feed cook_municipal_officials_scraper.py already reads for the Town of
Cicero — and the whole feed was privacy-audited before this builder existed
(2026-08-19: zero home addresses, zero personal e-mails on any governing
record; see the exclusion block below for where the hazards actually live).

THE JOIN. Census 2020 county-subdivision GEOID = 17 + county FIPS + COUSUBFP,
resolved from the committed reference data/source/st17_il_cousub2020.txt
(the Illinois rows of the Census national_cousub2020.txt codes file — the
cousub sibling of st17_il_place_by_county2020.txt). Township rows are
CLASSFP T1/T5; the C5 city-type cousubs (Chicago, Evanston) and the Z9
undefined-water filler are not townships and never match. The Clerk's
"<Base> Township" strips to a folded base name that matched all 29 live
townships exactly on first measurement; anything unresolved is FATAL, never
guessed.

WHAT NEVER SHIPS, and why each exclusion exists:
  - Democratic/Republican Township Committeeperson: PARTY offices, out of
    scope by the governance taxonomy (§1.6) — and the one place this API
    carries personal contact (gmail/yahoo/aol in Addresses[0].Email on 31 of
    57 records, home-address SLOT AddressTypeId 1 — empty today, dropped
    unconditionally in case it ever populates).
  - Library Trustee: another body's board; Cicero's ships on the
    library-district card via build_cicero_library_trustees.py.
  - Per-person phone/e-mail: the feed publishes ONE shared hall mailbox and
    hall line per township — often a named staffer's mailbox, not the
    officeholder's — so contact ships on the township's office block, never
    on a person row, where it would be wrong attribution.
  - Any address that is not the township hall: every governing record's
    single address carries AddressTypeId 3 (the hall) today, and this
    builder REFUSES any other type, so a residence can never ride this file
    (the build_cicero_library_trustees.py posture).

EVANSTON is the feed's one non-township: its township government dissolved
into the city in 2014, TIGER 2020 carries no township polygon for it, and
its only TWNSP records are the two party committeepersons. After the
exclusions it holds zero governing records and is skipped BY NAME
(EXPECTED_OFFICELESS). Any other township going officeless is FATAL — and so
is a township MISSING from the feed entirely: the township set of a served
county is closed (the county's own cousub table names all 29), so the
builder requires every township in that table to resolve to a roster entry.
A truncated response that drops whole jurisdictions cannot pass the floors
quietly — the Sangamon lesson, a guard keyed on requests succeeding is
blind to a feed that succeeds at nothing, and floors alone left a
two-township window.

CICERO ships here TOO, on purpose. The Town of Cicero and Cicero Township
are one consolidated government (Census FUNCSTAT C); the Clerk answers
"Cicero Township" with that government's officials, so both containment
questions — "what municipality am I in" and "what township am I in" — get
the county's own answer. The municipality card keys it 1714351 (place), this
file keys it 1703114364 (cousub); the President is the head on both.

Usage:
    python3 build_township_officials.py <cook-scraper-output.json> [...] [--out-dir DIR]

Multiple payloads are accepted for the county-by-county growth the
municipal roster proved out; each must carry `county` and a raw
`township_officials` list (the Clerk-API record shape).
"""

import argparse
import json
import os
import re
import sys
from scraper_common import make_fail, person_email_problem  # noqa: E402  (shared machinery — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUSUB_FILE = os.path.join(REPO_ROOT, "il", "data", "source", "st17_il_cousub2020.txt")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")

# Counties this builder knows how to key. Growth is adding a FIPS here and a
# payload on the command line — the EXPANSION_GUIDE Part 2 shape.
COUNTY_FIPS = {"Cook": "031"}

# Township rows in the Census cousub codes file. T1 = active township, T5 =
# township coterminous/consolidated with another government (Berwyn, Oak
# Park, River Forest, Cicero). C5 city-type cousubs and the Z9 filler are
# not townships.
TOWNSHIP_CLASSES = {"T1", "T5"}

# The elected township offices this file carries, an include list on the
# Cicero precedent: a new office appearing in the feed gets a WARN and a
# human look, never a silent carry or a silent drop. President and Collector
# exist only on Cicero's consolidated government.
HEAD_OFFICES = ("President", "Supervisor")  # priority order — Cicero has both
BOARD_OFFICES = {"Trustee"}
# No township elects a Treasurer today (measured 2026-08-19: zero records);
# one appearing should get the WARN-and-a-human-look, not a silent carry.
OFFICER_OFFICES = {"Supervisor", "Clerk", "Assessor", "Collector",
                   "Highway Commissioner"}
# See the module docstring for why each of these is excluded.
EXCLUDED_OFFICES = {"Democratic Township Committeeperson",
                    "Republican Township Committeeperson",
                    "Library Trustee"}

# The township hall. Any governing record carrying a different address type
# means the Clerk changed what the directory publishes — re-read it before
# shipping; a residence must never ride this file.
HALL_ADDRESS_TYPE = 3

# The one contact surface this file ships is the hall block's e-mail: the
# address the Clerk's directory lists as the township's own contact. Until
# 2026-10-17 the build REFUSED to write when that address sat on a personal
# mailbox provider (gmail, yahoo and the like), on the reasoning that a small
# township re-pointing its contact at a supervisor's own mailbox would be a
# privacy leak shown under the Township Hall label. Adam's choice of that day
# ("E-mails too") is that an address a government source publishes as an
# official's or an office's contact ships whatever its domain, so the domain
# test is gone. Two checks apply instead: the value must be exactly one
# address (scraper_common.person_email_problem; the error names the township,
# never the address), and an address two or more townships give as their hall
# e-mail is none of theirs, so it ships on none of them and the run says
# which. Measured that day: 29 of 29 townships list a hall e-mail, none on a
# provider the old test named and no two the same. The committeeperson
# records, whose e-mails are the personal ones (31 of 57 on 2026-08-19), stay
# out of this file because they are party offices, not because of their
# domains.
#
# Hall e-mails that ship: 29, measured 2026-10-17. About two thirds, so a
# feed change that empties the field fails the build instead of shipping a
# roster with the contact gone.
MIN_HALL_EMAILS = 19

# Jurisdictions expected to hold ZERO governing records after the
# exclusions. Evanston Township dissolved into the City of Evanston in 2014;
# only its party committeepersons remain in the feed, and TIGER 2020 carries
# no township polygon for it. Any OTHER township going officeless is FATAL.
EXPECTED_OFFICELESS = {"Evanston Township"}

# Floors, deliberate under-tolerances against the 2026-08-19 live values
# (29 townships, 220 governing records, 4 trustees on every board): normal
# turnover and a vacancy pass, a collapse fails and the shipped file stands.
MIN_TOWNSHIPS = 27
MIN_MEMBERS = 195
MIN_TRUSTEES_PER_TOWNSHIP = 3


fail = make_fail("build-township-officials")


def warn(msg):
    print("build-township-officials: WARN — %s" % msg, file=sys.stderr)


def clean(value):
    return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else None


def full_name(rec):
    first = clean(rec.get("FirstName"))
    nick = clean(rec.get("Nickname"))
    parts = [first]
    if nick and nick.lower() != (first or "").lower():
        parts.append('"%s"' % nick)
    parts += [clean(rec.get("MiddleName")), clean(rec.get("LastName")),
              clean(rec.get("Suffix"))]
    return " ".join(p for p in parts if p)


def phone_of(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
    return clean(value)


def year_of(value):
    m = re.match(r"(\d{4})", value or "")
    return m.group(1) if m else None


def fold(name):
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def normalize_website(value):
    site = clean(value)
    if not site:
        return None
    if not re.match(r"https?://", site, re.I):
        site = "https://" + site
    return site


def load_cousubs():
    """{county_fips: {folded base name: 10-digit GEOID}} for township rows."""
    by_county = {}
    with open(COUSUB_FILE, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("|")
        idx = {name: i for i, name in enumerate(header)}
        for line in f:
            row = line.rstrip("\n").split("|")
            if row[idx["CLASSFP"]] not in TOWNSHIP_CLASSES:
                continue
            county = row[idx["COUNTYFP"]]
            # Census prints the suffixed form ("Barrington township").
            base = re.sub(r"\s+township$", "", row[idx["COUSUBNAME"]], flags=re.I)
            geoid = row[idx["STATEFP"]] + county + row[idx["COUSUBFP"]]
            table = by_county.setdefault(county, {})
            key = fold(base)
            if key in table:
                fail("cousub reference carries %r twice in county %s" % (base, county))
            table[key] = geoid
    return by_county


def person_of(rec):
    """A card person row. Contact never rides a person from this feed —
    the hall mailbox/line is shared township-wide (see module docstring)."""
    person = {"name": full_name(rec), "role": clean(rec.get("Office"))}
    if not person["name"]:
        fail("a %s record in %s has no name"
             % (clean(rec.get("Office")), clean(rec.get("Jurisdiction"))))
    # Every township office is elected on one consolidated cycle, so all
    # current appointed flags resolve together at the April 2029 election —
    # that refresh will legitimately drop the field to zero and trip the
    # retention gate's VANISH rule (per-group on Lemont and River Forest, at
    # minimum). That is the gate's designed escape hatch: record it in
    # check_roster_retention.py's ACCEPTED_DROPS with the election date,
    # don't loosen a threshold.
    if rec.get("Appointed"):
        person["appointed"] = True
    next_election = year_of(clean(rec.get("NextElection")))
    if next_election:
        person["nextElection"] = next_election
    return person


def hall_of(rec, jurisdiction):
    addresses = rec.get("Addresses") or []
    addr = addresses[0] if addresses else {}
    if addr.get("AddressTypeId") != HALL_ADDRESS_TYPE:
        fail("%s record in %s carries address type %r, not the hall's (%d) — "
             "the directory changed what it publishes; re-read it before "
             "shipping" % (clean(rec.get("Office")), jurisdiction,
                           addr.get("AddressTypeId"), HALL_ADDRESS_TYPE))
    street = clean(addr.get("Address1"))
    if addr.get("Address2"):
        street = ", ".join(p for p in (street, clean(addr.get("Address2"))) if p)
    city_zip = None
    if addr.get("City"):
        city_zip = "%s IL %s" % (clean(addr.get("City")), clean(addr.get("Zip")) or "")
        city_zip = city_zip.strip()
    email = clean(addr.get("Email"))
    if email:
        problem = person_email_problem(email)
        if problem:
            fail("%s's hall e-mail %s — re-read the directory before shipping"
                 % (jurisdiction, problem))
    office = {
        "address": ", ".join(p for p in (street, city_zip) if p) or None,
        # The hall block's phone ONLY — the record-level Phone sits outside
        # the address-type gate and is never read.
        "phone": phone_of(addr.get("Phone")),
        "email": email,
    }
    return {k: v for k, v in office.items() if v}, normalize_website(addr.get("URL"))


def build_county(payload, cousubs_by_county):
    county = payload.get("county")
    if county not in COUNTY_FIPS:
        fail("payload county %r has no FIPS entry in this builder" % county)
    fips = COUNTY_FIPS[county]
    cousubs = cousubs_by_county.get(fips) or {}
    if not cousubs:
        fail("no township rows for county FIPS %s in %s" % (fips, COUSUB_FILE))
    records = payload.get("township_officials")
    if not records:
        fail("payload for %s carries no township_officials — re-run the "
             "scraper; this builder never writes from nothing" % county)
    source_url = payload.get("directory_url") or "unknown"

    by_jurisdiction = {}
    for rec in records:
        jurisdiction = clean(rec.get("Jurisdiction"))
        office = clean(rec.get("Office"))
        by_jurisdiction.setdefault(jurisdiction, [])
        if office in EXCLUDED_OFFICES:
            continue
        if office not in set(HEAD_OFFICES) | BOARD_OFFICES | OFFICER_OFFICES:
            warn("%s carries unrecognized office %r (%s) — neither included "
                 "nor excluded; skipped pending a human look"
                 % (jurisdiction, office, clean(rec.get("LastName"))))
            continue
        by_jurisdiction[jurisdiction].append(rec)

    roster = {}
    members = 0
    for jurisdiction in sorted(by_jurisdiction):
        gov = by_jurisdiction[jurisdiction]
        if not gov:
            if jurisdiction in EXPECTED_OFFICELESS:
                print("build-township-officials: %s holds no governing "
                      "records, as expected (government dissolved) — skipped"
                      % jurisdiction)
                continue
            fail("%s holds ZERO governing records after the exclusions — a "
                 "township does not lose its whole government between "
                 "elections; the feed or the filter broke" % jurisdiction)

        base = re.sub(r"\s+Township$", "", jurisdiction, flags=re.I)
        geoid = cousubs.get(fold(base))
        if not geoid:
            fail("cannot resolve %r to a %s County township GEOID — names "
                 "matched 29/29 when this was built; a miss is a change "
                 "worth a human look, never a fuzzy guess" % (jurisdiction, county))

        # Head: President over Supervisor (Cicero's consolidated government
        # carries both; everywhere else the Supervisor is the executive).
        head = None
        for head_office in HEAD_OFFICES:
            candidates = [r for r in gov if clean(r.get("Office")) == head_office]
            if len(candidates) > 1:
                fail("%s carries %d %s records — one government, one head"
                     % (jurisdiction, len(candidates), head_office))
            if candidates:
                head = candidates[0]
                break
        if head is None:
            fail("%s has no head office at all (no %s)"
                 % (jurisdiction, " or ".join(HEAD_OFFICES)))

        board = [r for r in gov if clean(r.get("Office")) in BOARD_OFFICES]
        officers = [r for r in gov
                    if r is not head and r not in board]
        # One seat per non-Trustee office: every one of these is a single
        # office, and the feed carrying two (an outgoing and an incoming
        # assessor mid-transition, say) is a state a human should read, not
        # a card that quietly lists both. The head loop's own duplicate
        # check stops at the office it picks, so this covers the rest.
        per_office = {}
        for r in gov:
            office = clean(r.get("Office"))
            if office not in BOARD_OFFICES:
                per_office[office] = per_office.get(office, 0) + 1
        for office, n in sorted(per_office.items()):
            if n > 1:
                fail("%s carries %d %s records — one seat per office"
                     % (jurisdiction, n, office))
        if len(board) < MIN_TRUSTEES_PER_TOWNSHIP:
            fail("%s resolves only %d trustees — every board in this feed "
                 "seats exactly four (measured 2026-08-19); below %d reads "
                 "as a parse or feed failure, not turnover"
                 % (jurisdiction, len(board), MIN_TRUSTEES_PER_TOWNSHIP))
        if len(board) > 4:
            fail("%s resolves %d trustees — every board in this feed seats "
                 "exactly four (measured 2026-08-19); more reads as a feed "
                 "change worth a human look" % (jurisdiction, len(board)))

        office, url = hall_of(head, jurisdiction)
        for rec in gov:
            hall_of(rec, jurisdiction)  # the AddressTypeId gate, every record

        entry = {
            "name": jurisdiction,
            "county": county,
            "head": person_of(head),
            "board": sorted((person_of(r) for r in board),
                            key=lambda p: p["name"]),
            "officers": sorted((person_of(r) for r in officers),
                               key=lambda p: (p["role"], p["name"])),
            "sourceUrl": source_url,
        }
        if office:
            entry["office"] = office
        if url:
            entry["url"] = url
        if geoid in roster:
            fail("GEOID %s resolved twice (%s and %s)"
                 % (geoid, roster[geoid]["name"], jurisdiction))
        roster[geoid] = entry
        members += 1 + len(board) + len(entry["officers"])

    # The county's township set is CLOSED — the cousub table names every
    # township that exists, so any table row missing from the roster means
    # the feed dropped a whole jurisdiction (a truncation the floors alone
    # could tolerate two of). A township that truly dissolves leaves the
    # Census table at the next vintage, which is when this list changes.
    missing = {g: base for base, g in cousubs.items() if g not in roster}
    if missing:
        fail("%s County townships absent from the feed entirely: %s — a "
             "township does not vanish between elections; the feed truncated "
             "or the type changed shape"
             % (county, ", ".join(sorted(missing.values()))))

    return roster, members


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("payloads", nargs="+")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    cousubs_by_county = load_cousubs()
    roster = {}
    total_members = 0
    for path in args.payloads:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        county_roster, members = build_county(payload, cousubs_by_county)
        overlap = set(roster) & set(county_roster)
        if overlap:
            fail("GEOIDs supplied by two payloads: %s" % ", ".join(sorted(overlap)))
        roster.update(county_roster)
        total_members += members

    if len(roster) < MIN_TOWNSHIPS:
        fail("only %d townships resolved (floor %d) — refusing to overwrite "
             "a good file with a partial scrape" % (len(roster), MIN_TOWNSHIPS))
    if total_members < MIN_MEMBERS:
        fail("only %d officials resolved (floor %d) — refusing to overwrite "
             "a good file with a partial scrape" % (total_members, MIN_MEMBERS))

    # An address two or more townships give as their hall e-mail belongs to
    # none of them (see MIN_HALL_EMAILS above); it ships on none.
    givers = {}
    for geoid, entry in roster.items():
        email = (entry.get("office") or {}).get("email")
        if email:
            givers.setdefault(email.lower(), []).append(geoid)
    for geoids in givers.values():
        if len(geoids) > 1:
            warn("%s give the same hall e-mail, so it is none of theirs; it "
                 "ships on none of them" % ", ".join(sorted(roster[g]["name"] for g in geoids)))
            for g in geoids:
                del roster[g]["office"]["email"]
                if not roster[g]["office"]:
                    del roster[g]["office"]
    hall_emails = sum(1 for e in roster.values() if (e.get("office") or {}).get("email"))
    if hall_emails < MIN_HALL_EMAILS:
        fail("only %d townships carry a hall e-mail (floor %d) — the directory "
             "may have stopped publishing it; re-read it before shipping"
             % (hall_emails, MIN_HALL_EMAILS))

    out_path = os.path.join(args.out_dir, "township-officials.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    heads = sum(1 for e in roster.values() if e.get("head"))
    print("build-township-officials: wrote %s — %d townships, %d officials "
          "(%d heads), %d hall e-mails" % (out_path, len(roster), total_members,
                                           heads, hall_emails))


if __name__ == "__main__":
    main()
