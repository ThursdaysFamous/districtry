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
  4. PRIVACY: a record carries only name, seat, role, e-mail, phone and profile
     page; an e-mail and a profile page only on the county's own domains; a
     phone only for a county whose row says its phones are office lines; and no
     value may look like a street address or a ZIP code. These pages print
     home addresses and personal phones beside the names, so this is checked
     here whatever a parser returns.

A COUNTY THAT WAS NOT READ, OR FAILED A GATE, KEEPS ITS LAST GOOD RECORD for up
to PRESERVE_MAX_AGE_DAYS, printed loudly every run, and past that the run
fails. That is the operator's ruling of 2026-09-19 (a refusal stops the fetch
and never unpublishes what was already read) with the ceiling Michigan's
builder carries, so preserving cannot turn into a roster frozen for as long as
nobody looks. Every county in the scraper's table must end up in the file,
read or carried; there is no floor to slip under, because a global count
cannot protect a named county.

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
APP = os.path.join(INSTANCE, "data", "app")
CACHE = os.path.join(HERE, ".cache", "tn_commissioner_roster.json")
DISTRICTS = os.path.join(APP, "tn-commission-districts.json")
OUT = os.path.join(APP, "tn-commissioners.json")

PRESERVE_MAX_AGE_DAYS = 45
FIELDS = ("name", "seat", "role", "email", "phone", "profileUrl", "vacant")

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


def record_problems(rec, domains, phones_ok, where):
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
    email = rec.get("email")
    if email and not _host_ok("mailto://" + email.rsplit("@", 1)[-1], domains):
        out.append("%s e-mail %r is not on the county's own domains %s"
                   % (where, email, domains))
    if rec.get("profileUrl") and not _host_ok(rec["profileUrl"], domains):
        out.append("%s profile page %r is not on the county's own domains"
                   % (where, rec["profileUrl"]))
    if rec.get("phone") and not phones_ok:
        out.append("%s carries a phone, and this county's phones are not recorded "
                   "as office lines" % where)
    for key in ("name", "seat", "role"):
        val = rec.get(key) or ""
        if ADDRESS.search(val) or ZIP.search(val):
            out.append("%s %s %r looks like an address or a ZIP code" % (where, key, val))
    return out


def county_problems(fips5, entry, n_geom, check_seats=True):
    """Every gate for one county; [] when it may ship."""
    name = entry.get("county") or fips5
    domains = [d.lower() for d in entry.get("domains") or []]
    phones_ok = bool(entry.get("phones"))
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
    names = []
    for d in sorted(ds, key=int):
        if not ds[d]:
            out.append("%s District %s has no seat at all" % (name, d))
        for i, rec in enumerate(ds[d]):
            out += record_problems(rec, domains, phones_ok,
                                   "%s District %s seat %d" % (name, d, i + 1))
            if rec.get("name"):
                names.append(rec["name"])
    for i, rec in enumerate(entry.get("atLarge") or []):
        out += record_problems(rec, domains, phones_ok, "%s countywide seat %d" % (name, i + 1))
        if rec.get("name"):
            names.append(rec["name"])
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        out.append("%s names %s more than once" % (name, dup))
    if not names:
        out.append("%s names nobody" % name)
    return out


def shipped_entry(entry, county_name, domains, phones):
    """The record as it ships: data only. The domains and the phone rule travel
    with it so --check can re-run the privacy gate offline."""
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
           "phones": phones,
           "districts": {d: ds[d] for d in sorted(ds, key=int)}}
    if entry.get("atLarge"):
        rec["atLarge"] = entry["atLarge"]
    return rec


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
            probs = county_problems(fips5, entry, counts[fips5])
            if probs:
                why = "GATE FAILED: " + "; ".join(probs)
        if why is None:
            out[fips5] = shipped_entry(entry, gnames[fips5], entry["domains"], entry["phones"])
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
        out[fips5] = prior
        carried.append("%s (%s, last read %s)" % (spec["county"], why, prior["readAt"]))
    if problems_all:
        for p in problems_all:
            print("  " + p, file=sys.stderr)
        return fail("%d county(ies) can neither be built nor carried forward" % len(problems_all))
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
          "%d carried forward" % (os.path.relpath(OUT, os.path.dirname(INSTANCE)),
                                  len(out), seats, named, len(carried)))
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
    if problems:
        for p in problems:
            print("  " + p, file=sys.stderr)
        return fail("%d problem(s) in the shipped roster" % len(problems))
    print("build-tn-commissioner-roster: OK - %d counties, every district 1..N against the "
          "geometry, every record within the privacy gate" % len(shipped))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
