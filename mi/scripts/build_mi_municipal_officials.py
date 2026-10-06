#!/usr/bin/env python3
"""
Build stage 2: mi/data/app/mi-municipal-officials.json, the elected boards of
Michigan's large cities and townships, keyed by Census geoid.

Reads the cache mi_municipal_officials_scraper.py writes. The key is the
7-digit Census place id for a city and the 10-digit county-subdivision id for
a township, which are the ids the Municipality and Township cards already
answer with, so the card joins on the feature it found and nothing else.

A UNIT THE SCRAPER COULD NOT READ KEEPS ITS LAST-GOOD RECORD (Adam's ruling of
2026-09-19, "Preserve data we have already fetched"), with `preservedSince`
set the first run it is carried and cleared the run it is read again. `readAt`
is never invented: it is the date the page was actually read. A unit carried
for more than PRESERVE_MAX_AGE_DAYS fails the run, so a dark source reaches a
person instead of riding last-good data indefinitely.

A unit is preserved only where the scraper says it TRIED and did not get an
answer (its `unread` list). A unit retired from the parser tables is in
neither list and leaves the file normally.

Usage:
    python3 mi/scripts/build_mi_municipal_officials.py           # write
    python3 mi/scripts/build_mi_municipal_officials.py --check   # shipped file vs a rebuild
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
CACHE = os.path.join(HERE, ".cache", "mi_municipal_officials.json")
OUT = os.path.join(INSTANCE, "data", "app", "mi-municipal-officials.json")
LABEL = "mi-municipal-officials"

# FLOORS. Measured on the first full run (2026-10-01: 67 units, 472 members)
# and set a few below it, then raised by Lansing's 1 unit and 8 members when it
# was added (2026-10-06);
# raise them when units are added, never lower one to get past a failure. A
# global count cannot protect a named unit, which is what the per-unit
# carry-forward below is for; the floor catches a run where most parsers broke.
MIN_UNITS = 63
MIN_MEMBERS = 448

PRESERVE_MAX_AGE_DAYS = 45

# Fields a member row may carry, in card order. Anything else is dropped here
# rather than shipped unreviewed.
FIELDS = ("name", "role", "seat", "phone", "email")


def fail(msg):
    print("%s: FAIL — %s" % (LABEL, msg), file=sys.stderr)
    raise SystemExit(1)


def days_since(stamp):
    try:
        then = datetime.strptime(stamp[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return (datetime.now(timezone.utc) - then).days


def units_table():
    import mi_municipal_officials_scraper as scraper
    return {u["geoid"]: u for u in scraper.all_units()}


def clean(geoid, entry, unit):
    """The shipped row for one unit, re-checked against the unit table."""
    from mi_municipal_common import check_roster
    members = [{k: m[k] for k in FIELDS if m.get(k)} for m in entry.get("members") or []]
    if unit["kind"] == "township":
        # A township board in its statutory order (MCL 41.70): supervisor,
        # clerk, treasurer, then trustees in the order the page lists them.
        # Pages list them in every order there is; the card should not.
        rank = {"Supervisor": 0, "Clerk": 1, "Treasurer": 2}
        members.sort(key=lambda m: rank.get(m["role"], 3))
    roster = {"members": members}
    if entry.get("vacant"):
        roster["vacant"] = list(entry["vacant"])
    try:
        check_roster(dict(unit, seats=entry.get("seats")), roster)
    except ValueError as exc:
        fail("%s (%s): %s" % (entry.get("name") or unit["name"], geoid, exc))
    row = {
        "name": unit["name"],
        "kind": unit["kind"],
        "body": entry.get("body") or unit["body"],
        "seats": entry["seats"],
        "members": members,
        "sourceUrl": entry.get("sourceUrl") or unit["url"],
    }
    if roster.get("vacant"):
        row["vacant"] = roster["vacant"]
    office = {k: v for k, v in (entry.get("office") or {}).items() if k in ("phone", "email") and v}
    if office:
        row["office"] = office
    if entry.get("readAt"):
        row["readAt"] = entry["readAt"]
    if entry.get("preservedSince"):
        row["preservedSince"] = entry["preservedSince"]
    return row


def build(cache, shipped, table):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {}
    for geoid, entry in (cache.get("units") or {}).items():
        if geoid not in table:
            print("  %s (%s) is in the cache and no longer in the unit tables; dropped"
                  % (entry.get("name"), geoid))
            continue
        out[geoid] = clean(geoid, entry, table[geoid])

    preserved, stale, lost = [], [], []
    for row in cache.get("unread") or []:
        geoid = row.get("geoid")
        if geoid in out or geoid not in table:
            continue
        if geoid not in shipped:
            lost.append("%s (%s): %s" % (row.get("name"), geoid, row.get("why")))
            continue
        entry = dict(shipped[geoid])
        entry["preservedSince"] = entry.get("preservedSince") or today
        out[geoid] = clean(geoid, entry, table[geoid])
        preserved.append((entry["name"], row.get("kind") or "", row.get("why") or "",
                          entry.get("readAt"), entry["preservedSince"]))
        age = days_since(entry["preservedSince"])
        if age is not None and age > PRESERVE_MAX_AGE_DAYS:
            stale.append("%s carried since %s (%d days)" % (entry["name"], entry["preservedSince"], age))
    for name, kind, why, read_at, since in sorted(preserved):
        print("  %s PRESERVED — not read this run [%s] (%s); carried since %s, last read %s"
              % (name, kind, why, since, read_at or "unknown"))
    for line in lost:
        print("  NOT READ and never shipped, so nothing to carry: %s" % line)
    missing = sorted(set(table) - set(out) - {r.get("geoid") for r in cache.get("unread") or []})
    if missing:
        fail("unit(s) %s are in the unit tables and in neither the cache's read nor its "
             "unread list; re-run the scraper in full" % ", ".join(missing))
    if stale:
        fail("%s — carried forward for more than %d days; the source needs a person"
             % ("; ".join(stale), PRESERVE_MAX_AGE_DAYS))
    total = sum(len(r["members"]) for r in out.values())
    if len(out) < MIN_UNITS:
        fail("only %d units resolved, floor is %d" % (len(out), MIN_UNITS))
    if total < MIN_MEMBERS:
        fail("only %d members resolved, floor is %d" % (total, MIN_MEMBERS))
    return {g: out[g] for g in sorted(out)}, total


def main():
    check_only = "--check" in sys.argv[1:]
    if not os.path.exists(CACHE):
        fail("no scraper cache at %s; run mi_municipal_officials_scraper.py first"
             % os.path.relpath(CACHE, INSTANCE))
    with open(CACHE) as fh:
        cache = json.load(fh)
    shipped = {}
    if os.path.exists(OUT):
        with open(OUT) as fh:
            shipped = json.load(fh)
    payload, total = build(cache, shipped, units_table())
    cities = sum(1 for r in payload.values() if r["kind"] == "city")
    rendered = json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
    if check_only:
        current = open(OUT).read() if os.path.exists(OUT) else ""
        if current != rendered:
            fail("%s is stale; re-run the scraper and this builder" % os.path.relpath(OUT, INSTANCE))
        print("%s: OK — %d units (%d cities, %d townships), %d members, shipped file matches"
              % (LABEL, len(payload), cities, len(payload) - cities, total))
        return 0
    with open(OUT, "w") as fh:
        fh.write(rendered)
    print("%s: wrote %d units (%d cities, %d townships), %d members -> %s"
          % (LABEL, len(payload), cities, len(payload) - cities, total,
             os.path.relpath(OUT, INSTANCE)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
