#!/usr/bin/env python3
"""
Build tn/data/app/tn-commissioners.json - who sits on each Tennessee county's
legislative body, by district, keyed by the 5-digit county code that
tn-commission-districts.json carries - and read by tn/index.html's County
Commission District card.

WHAT IT ADDS. The district layer draws all 859 districts and names nobody,
because no state office publishes who holds them. This file names the members
for the counties tn_commissioner_scraper.py reads from each county's own page,
a tranche at a time; its COUNTIES table is the list.

GATES, AND A COUNTY FAILING ONE SHIPS NOTHING NEW
--------------------------------------------------
  1. The county's districts are exactly 1..N, where N is the number of
     districts the shipped geometry draws for that county, so a redistricting
     turns the run red instead of shipping names keyed to lines that moved.
  2. Each district carries exactly the seats the scraper's row says the county
     elects there (a vacancy the county states counts as a seat), and the
     countywide seats match too. The row is what a person read off the county's
     page; the parse is what the page says this week; they have to agree.
  3. Every seat names a person or is a vacancy the county states, and no two
     seats in one county name the same person - two identical names on one
     body is a parse collision, not a body.
  4. PRIVACY: a record carries only name, seat, role, e-mail, phone, further
     phones and profile page; a profile page only on the county's own domains;
     and no name, seat or role may look like a street address or a ZIP code.
     These pages print home addresses beside the names, so this is checked
     here whatever a parser returns.
  5. TELEPHONE NUMBERS: under Adam's ruling of 2026-10-17 for every state ("if
     the official government source uses personal phone numbers, we publish
     those"), a number the county prints beside a member ships whosever line
     it is, the first in `phone` and any others in `phonesExtra`. Each value
     must be ONE telephone number and nothing else: an optional label word
     (cell, home, work, business, office, mobile, personal, residence), the
     number as printed, and an optional extension. Anything carrying a street
     word, a ZIP code, an "@" or a second number fails, and the message names
     the county and seat, never the value. No number may sit on two members'
     records in one county, because a number printed for several members is
     the office's. Until 2026-10-17 this gate refused every phone in a county
     whose scraper row did not say its phones were office lines (PHONES).
  6. E-MAIL ADDRESSES: Adam chose on 2026-10-17, for every state, to show a
     personal address a government page prints beside an official ("E-mails
     too"), so an address the county prints beside a member ships whatever its
     domain; until that day only an address on the county's own domains did.
     Each value must be ONE address, and the message names the county and
     seat, never the value. No address may sit on two members' records in one
     county, because an address printed for several members is the office's.
     An address on the fleet's undeliverable list (scripts/undeliverable.py)
     is dropped before these gates, with a line naming the seat.

A COUNTY THAT WAS NOT READ, OR FAILED A GATE, KEEPS ITS LAST GOOD RECORD for up
to PRESERVE_MAX_AGE_DAYS, printed loudly every run, and past that the run
fails. That is the operator's ruling of 2026-09-19 (a refusal stops the fetch
and never unpublishes what was already read) with the ceiling Michigan's
builder carries, so preserving cannot turn into a roster frozen for as long as
nobody looks. Every county in the scraper's table must end up in the file,
read or carried, so no floor counts the counties or the names: a global count
cannot protect a named county. The two floors are MIN_MEMBERS_WITH_PHONE and
MIN_MEMBERS_WITH_EMAIL, on how many members carry a telephone number and an
e-mail address across the file, because a county page that changes how it
prints them would otherwise empty them quietly while every name still ships
(scripts/check_roster_retention.py watches each county's fields against the
last shipped file as well).

Usage:
    python3 tn/scripts/build_tn_commissioner_roster.py          # from the cache
    python3 tn/scripts/build_tn_commissioner_roster.py --check  # offline gate on the shipped file
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.append(os.path.join(os.path.dirname(INSTANCE), "scripts"))
import undeliverable  # noqa: E402  (FLEET_SHARED: the fleet's withhold list)
APP = os.path.join(INSTANCE, "data", "app")
CACHE = os.path.join(HERE, ".cache", "tn_commissioner_roster.json")
DISTRICTS = os.path.join(APP, "tn-commission-districts.json")
OUT = os.path.join(APP, "tn-commissioners.json")

PRESERVE_MAX_AGE_DAYS = 45
FIELDS = ("name", "seat", "role", "email", "phone", "phonesExtra", "profileUrl", "vacant")
# Members carrying at least one telephone number, across the whole file.
# MEASURED 2026-10-17 on the first build under Adam's ruling of that day, from a
# live read of all 57 counties: 780 of the 1,000 named members carry a number
# and 24 of those a second, in the 48 counties whose pages print a member's
# number. The floor is about two thirds of 780, so a change in how a few
# counties print their numbers fails the build instead of shipping names with
# the numbers gone.
MIN_MEMBERS_WITH_PHONE = 520
# Members carrying an e-mail address, across the whole file. MEASURED
# 2026-10-17 on the first build under Adam's choice of that day to show a
# personal address a government page prints beside an official ("E-mails
# too"): 653 of the 1,000 named members, 188 of them on a domain other than
# their county government's. The floor is about two thirds of that.
MIN_MEMBERS_WITH_EMAIL = 435

# One telephone number as a county page prints it, after the parsers' own
# reading: an optional label word, an optional area code ("(931) ", "931-",
# "931.", "931/"), the exchange and the line, and an optional extension. A
# number printed without an area code ships that way, never with one guessed.
PHONE_LABELS = ("cell", "home", "work", "business", "office", "mobile", "personal",
                "residence")
PHONE_VALUE = re.compile(
    r"(?:(?:%s) )?"
    r"(?:(?:\(\d{3}\) ?[-.]? ?|\d{3}\) ?|\d{3} ?[-./] ?)?\d{3} ?[-.] ?\d{4}"
    r"|\(\d{3}\) ?\d{3} \d{4})"
    r"(?: ?(?:ext\.?|x) ?\d{1,6})?" % "|".join(PHONE_LABELS), re.I)

# One e-mail address and nothing else.
EMAIL_VALUE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

# What a street address or a ZIP code looks like inside a value. A name never
# contains either, so a match is a parser that read the wrong column.
ADDRESS = re.compile(
    r"\b\d{2,6}\s+(?:[NSEW]\.?\s+)?[A-Za-z][A-Za-z.' ]*\s(?:Rd|Road|St|Street|Ave|Avenue|"
    r"Ln|Lane|Dr|Drive|Pike|Hwy|Highway|Blvd|Boulevard|Ct|Court|Cir|Circle|Way|"
    r"Trl|Trail|Pl|Place|Pkwy|Parkway)\b\.?", re.I)
ZIP = re.compile(r"\b3[78]\d{3}(?:-\d{4})?\b")


def fail(msg):
    print("build-tn-commissioner-roster: FAIL - %s" % msg, file=sys.stderr)
    return 1


def geometry_counts():
    with open(DISTRICTS) as handle:
        fc = json.load(handle)
    counts, names = {}, {}
    for f in fc["features"]:
        p = f["properties"]
        counts.setdefault(p["countyfips"], set()).add(int(p["district"]))
        names[p["countyfips"]] = p["county"]
    for fips, ds in counts.items():
        if ds != set(range(1, len(ds) + 1)):
            raise SystemExit(fail("the shipped geometry numbers %s %s, not 1..N"
                                  % (names[fips], sorted(ds))))
    return {k: len(v) for k, v in counts.items()}, names


def _host_ok(url, domains):
    host = (urlsplit(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in domains)


def phone_values(rec):
    """Every telephone number on a record, `phone` first."""
    extra = rec.get("phonesExtra")
    return [v for v in [rec.get("phone")] + (extra if isinstance(extra, list) else []) if v]


def dialled(value):
    """The digits of a number (an extension and a leading 1 dropped), to
    compare two numbers; a seven-digit number compares as the end of a ten."""
    d = re.sub(r"\D", "", re.split(r"(?i)\s*(?:ext\.?|x)\s*\d", value)[0])
    return d[1:] if len(d) == 11 and d.startswith("1") else d


def record_problems(rec, domains, where):
    out = []
    extra = set(rec) - set(FIELDS)
    if extra:
        out.append("%s carries %s, which this file never ships" % (where, sorted(extra)))
    if rec.get("vacant"):
        if rec.get("name"):
            out.append("%s is both vacant and named" % where)
        return out
    if not (rec.get("name") or "").strip():
        out.append("%s names nobody and is not a stated vacancy" % where)
    # An e-mail ships whatever its domain (rule 6); the message never quotes
    # it, since a value that fails here may be text a parser misread.
    email = rec.get("email")
    if email is not None and not (isinstance(email, str) and
                                  EMAIL_VALUE.fullmatch(email.strip())):
        out.append("%s e-mail is not one address" % where)
    if rec.get("profileUrl") and not _host_ok(rec["profileUrl"], domains):
        out.append("%s profile page %r is not on the county's own domains"
                   % (where, rec["profileUrl"]))
    extra = rec.get("phonesExtra")
    if extra is not None and not (isinstance(extra, list) and extra and rec.get("phone") and
                                  all(isinstance(x, str) and x.strip() for x in extra)):
        out.append("%s phonesExtra is not a list of further numbers after a phone" % where)
    for i, value in enumerate(phone_values(rec)):
        # The message never quotes the value: it may be the line a parser
        # misread, an address or a number that is not the member's.
        if not isinstance(value, str) or not PHONE_VALUE.fullmatch(value.strip()) or \
                ADDRESS.search(value) or ZIP.search(value) or "@" in value:
            out.append("%s %s is not one telephone number (a label word, one number "
                       "and an extension at most)"
                       % (where, "phone" if i == 0 else "further phone %d" % i))
    for key in ("name", "seat", "role"):
        val = rec.get(key) or ""
        if ADDRESS.search(val) or ZIP.search(val):
            out.append("%s %s %r looks like an address or a ZIP code" % (where, key, val))
    return out


def shared_mail(rec, where, mails):
    """[] or the problem of an e-mail address another seat in the county
    already carries; `mails` records each address against its seat."""
    mail = rec.get("email")
    if not isinstance(mail, str) or not mail.strip():
        return []
    key = mail.strip().lower()
    if key in mails:
        return ["%s and %s carry the same e-mail address, which is the office's, not "
                "either member's" % (mails[key], where)]
    mails[key] = where
    return []


def withhold_undeliverable(entry):
    """Drop, before the gates, every e-mail address the fleet's undeliverable
    list withholds (an address mail cannot reach); the module prints a line
    naming the seat for each one."""
    name = entry.get("county") or "?"
    seats = [("%s District %s seat %d" % (name, d, i + 1), rec)
             for d, recs in (entry.get("districts") or {}).items()
             for i, rec in enumerate(recs)]
    seats += [("%s countywide seat %d" % (name, i + 1), rec)
              for i, rec in enumerate(entry.get("atLarge") or [])]
    for where, rec in seats:
        if rec.get("email"):
            value, _why = undeliverable.withhold(rec["email"], where)
            if not value:
                rec.pop("email")


def county_problems(fips5, entry, n_geom, check_seats=True):
    """Every gate for one county; [] when it may ship."""
    name = entry.get("county") or fips5
    domains = [d.lower() for d in entry.get("domains") or []]
    ds = entry.get("districts") or {}
    out = []
    want = {str(i) for i in range(1, n_geom + 1)}
    if set(ds) != want:
        out.append("%s districts %s, and the shipped geometry draws 1..%d"
                   % (name, sorted(ds, key=int), n_geom))
    if check_seats:
        seats = entry.get("seatsByDistrict") or {}
        if set(seats) != want:
            out.append("%s: the scraper's seat table covers %s, the geometry 1..%d"
                       % (name, sorted(seats, key=int), n_geom))
        for d in sorted(ds, key=int):
            if len(ds[d]) != seats.get(d):
                out.append("%s District %s: %d seat(s) parsed, the county elects %s"
                           % (name, d, len(ds[d]), seats.get(d)))
        if len(entry.get("atLarge") or []) != (entry.get("atLargeSeats") or 0):
            out.append("%s: %d countywide seat(s) parsed, the county elects %d"
                       % (name, len(entry.get("atLarge") or []), entry.get("atLargeSeats") or 0))
    labels = entry.get("districtLabels")
    if labels is not None:
        # THE COUNTY'S OWN NAME FOR A DISTRICT the state numbers (Dyer letters
        # its districts A to J): every district or none, each name different,
        # because a card printing one county's "District A" beside the state's
        # "District 3" for the same ground would be two answers to one question.
        if set(labels) != set(ds):
            out.append("%s names districts %s and labels %s"
                       % (name, sorted(ds, key=int), sorted(labels)))
        vals = [str(v).strip() for v in labels.values()]
        if not all(vals) or len(set(vals)) != len(vals):
            out.append("%s district labels %s are empty or repeat" % (name, vals))
        for v in vals:
            if ADDRESS.search(v) or ZIP.search(v) or len(v) > 40:
                out.append("%s district label %r is not a district's name" % (name, v))
    names, numbers, mails = [], [], {}      # numbers: (digits, where); mails: address -> where
    for d in sorted(ds, key=int):
        if not ds[d]:
            out.append("%s District %s has no seat at all" % (name, d))
        for i, rec in enumerate(ds[d]):
            where = "%s District %s seat %d" % (name, d, i + 1)
            out += record_problems(rec, domains, where)
            if rec.get("name"):
                names.append(rec["name"])
            numbers += [(dialled(v), where) for v in phone_values(rec) if isinstance(v, str)]
            out += shared_mail(rec, where, mails)
    for i, rec in enumerate(entry.get("atLarge") or []):
        where = "%s countywide seat %d" % (name, i + 1)
        out += record_problems(rec, domains, where)
        if rec.get("name"):
            names.append(rec["name"])
        numbers += [(dialled(v), where) for v in phone_values(rec) if isinstance(v, str)]
        out += shared_mail(rec, where, mails)
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        out.append("%s names %s more than once" % (name, dup))
    for k, (a, wa) in enumerate(numbers):
        for b, wb in numbers[k + 1:]:
            short, long_ = sorted((a, b), key=len)
            if wa != wb and short and (a == b or (len(short) == 7 and len(long_) == 10
                                                  and long_.endswith(short))):
                out.append("%s and %s carry the same number, which is the office's, not "
                           "either member's" % (wa, wb))
    if not names:
        out.append("%s names nobody" % name)
    return out


def shipped_entry(entry, county_name, domains):
    """The record as it ships: data only. The domains travel with it so --check
    can re-run the privacy gate offline."""
    ds = entry["districts"]
    # `seatTitle`, never `memberTitle`: scripts/build_eam_status.py reads a key
    # whose words name an office and whose value looks like a name ("Council
    # Member") as a person, and this field names a title, not anybody.
    rec = {"county": county_name,
           "seatTitle": entry.get("seatTitle") or "Commissioner",
           "bodyName": entry.get("bodyName") or "County Commission",
           "sourceUrl": entry["sourceUrl"],
           "readAt": entry["readAt"],
           "seats": sum(len(v) for v in ds.values()) + len(entry.get("atLarge") or []),
           "domains": domains,
           "districts": {d: ds[d] for d in sorted(ds, key=int)}}
    if entry.get("districtLabels"):
        rec["districtLabels"] = {d: entry["districtLabels"][d]
                                 for d in sorted(entry["districtLabels"], key=int)}
    if entry.get("atLarge"):
        rec["atLarge"] = entry["atLarge"]
    return rec


def members_with_phone(roster, extra=False):
    """How many members carry a telephone number (with extra=True, two or more)."""
    return members_with(roster, "phonesExtra" if extra else "phone")


def members_with(roster, key):
    """How many members carry a value under `key`."""
    return sum(1 for e in roster.values()
               for m in [r for d in (e.get("districts") or {}).values() for r in d]
               + list(e.get("atLarge") or []) if m.get(key))


def build():
    if not os.path.exists(CACHE):
        return fail("no scrape cache at %s - run tn_commissioner_scraper.py first" % CACHE)
    with open(CACHE) as handle:
        cache = json.load(handle)
    counts, gnames = geometry_counts()
    shipped = {}
    if os.path.exists(OUT):
        with open(OUT) as handle:
            shipped = json.load(handle)
    sys.path.insert(0, HERE)
    import tn_commissioner_scraper as scraper  # same instance tree
    table = {c["fips"]: c for c in scraper.COUNTIES}

    out, carried, problems_all = {}, [], []
    unread = {u["fips"]: u for u in cache.get("unread") or []}
    today = datetime.now(timezone.utc).date()
    for fips3, spec in sorted(table.items()):
        fips5 = "47" + fips3
        if fips5 not in counts:
            return fail("%s County (%s) is in the scraper's table and not in the geometry"
                        % (spec["county"], fips5))
        entry = (cache.get("counties") or {}).get(fips3)
        why = None
        if entry is None:
            why = (unread.get(fips3) or {}).get("why") or "absent from the scrape cache"
        else:
            withhold_undeliverable(entry)
            probs = county_problems(fips5, entry, counts[fips5])
            if probs:
                why = "GATE FAILED: " + "; ".join(probs)
        if why is None:
            out[fips5] = shipped_entry(entry, gnames[fips5], entry["domains"])
            continue
        prior = shipped.get(fips5)
        if prior is None:
            problems_all.append("%s County: %s, and there is no shipped record to carry "
                                "forward" % (spec["county"], why))
            continue
        age = (today - date.fromisoformat(prior["readAt"])).days
        if age > PRESERVE_MAX_AGE_DAYS:
            problems_all.append("%s County: %s, and its last good read (%s) is %d days "
                                "old, past the %d-day ceiling" % (spec["county"], why,
                                prior["readAt"], age, PRESERVE_MAX_AGE_DAYS))
            continue
        # The record as last read, less the retired `phones` flag (2026-10-17),
        # which nothing reads any more.
        out[fips5] = {k: v for k, v in prior.items() if k != "phones"}
        carried.append("%s (%s, last read %s)" % (spec["county"], why, prior["readAt"]))
    if problems_all:
        for p in problems_all:
            print("  " + p, file=sys.stderr)
        return fail("%d county(ies) can neither be built nor carried forward" % len(problems_all))
    with_phone = members_with_phone(out)
    if with_phone < MIN_MEMBERS_WITH_PHONE:
        return fail("only %d members carry a telephone number, under the floor of %d: a "
                    "county page has probably changed how it prints its numbers"
                    % (with_phone, MIN_MEMBERS_WITH_PHONE))
    with_email = members_with(out, "email")
    if with_email < MIN_MEMBERS_WITH_EMAIL:
        return fail("only %d members carry an e-mail address, under the floor of %d: a "
                    "county page has probably changed how it prints them"
                    % (with_email, MIN_MEMBERS_WITH_EMAIL))
    gone = sorted(set(shipped) - set(out))
    with open(OUT, "w") as handle:
        json.dump(out, handle, indent=1, ensure_ascii=False, sort_keys=False)
        handle.write("\n")
    seats = sum(e["seats"] for e in out.values())
    named = sum(1 for e in out.values() for d in e["districts"].values() for m in d
                if m.get("name")) + sum(1 for e in out.values() for m in e.get("atLarge") or []
                                        if m.get("name"))
    for line in carried:
        print("  CARRIED FORWARD, NOT READ THIS RUN - %s" % line)
    if gone:
        print("  left the file (no longer in the scraper's table): %s"
              % ", ".join(shipped[g]["county"] for g in gone))
    print("build-tn-commissioner-roster: wrote %s - %d counties, %d seats, %d named, "
          "%d with a telephone number (floor %d), %d with two or more, %d with an e-mail "
          "address (floor %d), %d carried forward"
          % (os.path.relpath(OUT, os.path.dirname(INSTANCE)), len(out), seats, named,
             with_phone, MIN_MEMBERS_WITH_PHONE, members_with_phone(out, extra=True),
             with_email, MIN_MEMBERS_WITH_EMAIL, len(carried)))
    return 0


def check():
    if not os.path.exists(OUT):
        return fail("%s is missing" % OUT)
    with open(OUT) as handle:
        shipped = json.load(handle)
    counts, gnames = geometry_counts()
    problems = []
    for fips5, rec in sorted(shipped.items()):
        if fips5 not in counts:
            problems.append("%s is not a county the geometry draws" % fips5)
            continue
        if rec.get("county") != gnames[fips5]:
            problems.append("%s is named %r, the geometry calls it %r"
                            % (fips5, rec.get("county"), gnames[fips5]))
        problems += county_problems(fips5, rec, counts[fips5], check_seats=False)
        total = sum(len(v) for v in (rec.get("districts") or {}).values()) + \
            len(rec.get("atLarge") or [])
        if rec.get("seats") != total:
            problems.append("%s says %s seats and carries %d" % (rec.get("county"),
                                                                 rec.get("seats"), total))
        for key in ("sourceUrl", "readAt", "seatTitle", "bodyName"):
            if not rec.get(key):
                problems.append("%s carries no %s" % (rec.get("county"), key))
    with_phone = members_with_phone(shipped)
    if with_phone < MIN_MEMBERS_WITH_PHONE:
        problems.append("only %d members carry a telephone number, under the floor of %d"
                        % (with_phone, MIN_MEMBERS_WITH_PHONE))
    with_email = members_with(shipped, "email")
    if with_email < MIN_MEMBERS_WITH_EMAIL:
        problems.append("only %d members carry an e-mail address, under the floor of %d"
                        % (with_email, MIN_MEMBERS_WITH_EMAIL))
    if problems:
        for p in problems:
            print("  " + p, file=sys.stderr)
        return fail("%d problem(s) in the shipped roster" % len(problems))
    print("build-tn-commissioner-roster: OK - %d counties, every district 1..N against the "
          "geometry, every record within the privacy gate, %d members with a telephone "
          "number (floor %d), %d with an e-mail address (floor %d)"
          % (len(shipped), with_phone, MIN_MEMBERS_WITH_PHONE, with_email,
             MIN_MEMBERS_WITH_EMAIL))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
