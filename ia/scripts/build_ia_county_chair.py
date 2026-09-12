#!/usr/bin/env python3
"""Build stage 2: ia/data/app/ia-county-board-chairs.json.

Reads BOTH chair scrapers' caches and writes the roster the County
Supervisor card joins by name. A SEPARATE FILE FROM `ia-county-officers.json` ON PURPOSE:
that file is rebuilt weekly from its own sources, so writing chairs into it
would have each pipeline silently erase the other's work. This is the shape
Illinois already uses for Lake County's board roles -- a roles file that
joins to a members file by name -- and the join is the card's, not the
builder's, so a chair who leaves the board simply stops rendering.

TWO ROUTES, FLOORED SEPARATELY
--------------------------------
`ia_county_chair_scraper.py` reads each county's BOARD PAGE and answers 35
counties. `ia_county_minutes_chair_scraper.py` reads each county's own
MINUTES and answers 4 more -- big counties whose board pages never use the
word. It RESOLVES a fifth, Johnson, and does not ship it: Johnson publishes
its minutes through a Granicus portal whose robots.txt refuses this agent on
every path, so the scraper asks first and never fetches. Each route has its OWN floor
and its own count in the log, because a pooled floor cannot see one route
collapse behind the other's healthy number: 4 of 39 is a tenth of this file,
so the minutes route could stop working entirely without a single gate
noticing. That is the same lesson
`check_roster_retention.py` records as "coverage is measured PER SOURCE, not
per file", applied one layer up.

WHERE THE ROUTES DISAGREE, THE COUNTY IS DROPPED
-------------------------------------------------
Two surfaces a county publishes itself can name different chairs, and this
is not hypothetical: Des Moines County's boards-and-commissions page reads
`Tom Broeker, Chair` -- his chairmanship of a different body -- while its own
minutes of 25 August 2026 open "with Chair Shane McCampbell, Vice-Chair Tom
Broeker". The page route excludes that page and the minutes route reads the
minutes, so today the two agree wherever both answer. When they stop
agreeing the county is DROPPED with a printed line, never resolved by
preferring one route: two county-published surfaces disagreeing about a name
is the case this project asks about rather than guesses at. Dropping is also
the safe failure -- the card simply stops marking a chair -- where a hard
build failure would take the whole weekly refresh down for one county's
transition week.

A COUNTY THAT GOES QUIET IS REPORTED, AND SOMETIMES CARRIED
------------------------------------------------------------
This builder used to rebuild from the two scraper caches alone, so a county
that resolved last week and not this week simply stopped appearing, with
nothing in the log about it. That is what happened to Clayton on 2026-09-08:
the run's whole diff was Clayton's six lines, and its log -- which prints a
line only for a county the scrape RESOLVED -- could not say which of `none`,
`no-roster` and `unreachable` it had become. Clayton's page was and is fine.
It answers this project's own client with `Ray Peterson, Chairperson` at
https://www.claytoncountyia.gov/supervisors/, and the county sits behind
Cloudflare, which answers one caller and not another. Two Actions runs three
days apart both missed it; a re-read here on 2026-09-12 got it in full.

So the SHIPPED FILE IS AN INPUT AS WELL AS THE OUTPUT, the shape
build_ia_county_officers.py already uses for the officer e-mail addresses.
Every county in the shipped file that this run does not resolve gets a
PRINTED line saying what became of it, and a narrow subset are carried:

* CARRIED only when the scrapers say `unreachable` -- the one verdict that
  means we could not ASK. Nothing else qualifies. `none`, `many`, `disagree`
  and `too-few-documents` are the county answering and the answer being no
  chair we can pair, `no-roster` is our own roster file missing the county,
  and `unreadable` is a document we fetched and could not parse. Each of
  those is a real change in what the county publishes, and carrying it would
  hide that. `unreadable` is the narrow call here and it is deliberately
  refused: fewer carried records is the safe direction.
* NEVER carried on `robots-refused` or `robots-disallowed`. A site that has
  said no must not have its data kept alive by us, and a stale copy is still
  its data.
* Carried only while the prior chair is STILL on that county's own supervisor
  roster -- the same re-gate a freshly scraped chair gets.
* Carried only for MAX_CARRY_DAYS, counted from the record's own
  `confirmedOn` -- the last date a scrape actually read the name off a county
  surface. A record with no `confirmedOn` is never carried, so the mechanism
  arms itself one run after it ships rather than vouching for records whose
  age nothing measured.
* Dropped outright when a 1 January falls between `confirmedOn` and today,
  whatever the age. Iowa boards elect their chair at the January
  reorganisation, so a carried name cannot cross that date and still be a
  claim about who chairs the board.

A CARRIED COUNTY DOES NOT COUNT TOWARD EITHER FLOOR. MIN_PAGE and MIN_MINUTES
measure what the SCRAPE resolved, so a route collapsing still fails the build
instead of being propped up by last week's file.

WHAT THIS REFUSES TO WRITE, AND WHY EACH ONE IS HERE
-----------------------------------------------------
* Fewer than MIN_PAGE counties from the board-page route, or fewer than
  MIN_MINUTES from the minutes route. Both floors sit BELOW what was
  measured, because the sources are separate county websites and one of them
  redesigning is ordinary churn, not a broken parser. What a floor catches is
  a COLLAPSE -- the parser stopped working, or the network did. Per-county
  loss is `check_roster_retention.py`'s job once this file ships.
* A chair who is not on that county's own supervisor roster. The scraper
  already gates on this; the builder re-gates because the two stages run
  against `ia-county-officers.json` at different times and that file has its
  own weekly refresh. A name that no longer appears there is DROPPED, never
  carried forward on the strength of last week's scrape.
* Any county the scraper reported with two candidates. It collapses those to
  `many` itself and none of 98 produced one, so this is an assertion about a
  thing that has never happened rather than a filter that does work.

Every join whose page form differs from the roster form is PRINTED on every
run -- `Mr. Mike Hadley` against Keokuk's `Michael C. Hadley` -- so a reviewer
sees the four inexact matches rather than trusting a diminutive table.

Usage:
    python3 ia/scripts/build_ia_county_chair.py [--check]
    python3 ia/scripts/build_ia_county_chair.py --selftest
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "app")
CACHE = os.path.join(HERE, ".cache", "ia_county_chairs.json")
MINUTES_CACHE = os.path.join(HERE, ".cache", "ia_county_minutes_chairs.json")
OFFICERS = os.path.join(DATA, "ia-county-officers.json")
OUT_PATH = os.path.join(DATA, "ia-county-board-chairs.json")

# How long a chair may ride the shipped file after the last scrape that
# actually read it off a county page. Sixty days is eight weekly runs: long
# enough that a county behind an address-sensitive CDN survives a run of bad
# luck (Clayton was missed twice in four days), short enough that a page which
# has genuinely stopped naming a chair clears within two months.
MAX_CARRY_DAYS = 60
# The only verdict that means WE COULD NOT ASK. Everything else the two
# scrapers can report is either the county answering or a refusal; see the
# docstring for why `unreadable` is not in here.
CARRY_VERDICTS = frozenset(["unreachable"])

MIN_PAGE = 30               # measured 35 of 98 on 2026-09-05 (36 before the
                            # qualified-chair and expired-term refusals)
MIN_MINUTES = 3             # measured 4 of the 10 largest chair-less counties
                            # on 2026-09-05; the other six are recorded, with
                            # what refused each, in the minutes scraper. FIVE
                            # counties yield a chair and only four ship:
                            # Johnson's minutes live on johnson-county.
                            # granicus.com, whose robots.txt refuses
                            # `districtry` on every path, so its pages are
                            # never requested.
SOURCE_NOTE = ("each county's own board-of-supervisors page or its own board "
               "minutes, paired structurally and gated on the county's "
               "supervisor roster")


def _roster(officers, fips):
    return [m["name"] for m in (officers.get(fips) or {}).get("supervisors", [])]


def collect_page(rows, officers, out, inexact, dropped, today):
    """The board-page route: rows straight from ia_county_chair_scraper."""
    n = 0
    for r in sorted(rows, key=lambda x: x["fips"]):
        if r.get("verdict") != "one":
            continue
        assert r.get("chair"), "a verdict of one with no chair: %r" % r
        fips = "19" + r["fips"]
        if r["chair"] not in _roster(officers, fips):
            dropped.append((r["county"], r["chair"], "page"))
            continue
        rec = {"county": r["county"], "chair": r["chair"], "route": "page",
               "sourceUrl": r["sourceUrl"], "confirmedOn": today}
        if r.get("match") != "exact":
            rec["pageName"] = r["pageName"]
            rec["match"] = r["match"]
            inexact.append((r["county"], r["chair"], r["pageName"], r["match"]))
        out[fips] = rec
        n += 1
    return n


def collect_minutes(rows, officers, out, dropped, conflicts, today):
    """The minutes route, merged onto whatever the page route already has."""
    n = 0
    for r in sorted(rows, key=lambda x: x["fips"]):
        if r.get("verdict") != "one":
            continue
        assert r.get("chair"), "a verdict of one with no chair: %r" % r
        fips = "19" + r["fips"]
        if r["chair"] not in _roster(officers, fips):
            dropped.append((r["county"], r["chair"], "minutes"))
            continue
        n += 1
        have = out.get(fips)
        if have is None:
            out[fips] = {"county": r["county"], "chair": r["chair"],
                         "route": "minutes", "sourceUrl": r["sourceUrl"],
                         "meetingDate": r.get("meetingDate"),
                         "confirmedOn": today}
            continue
        if have["chair"] == r["chair"]:
            # both routes, same name: say so rather than silently preferring one
            have["route"] = "page+minutes"
            have["meetingDate"] = r.get("meetingDate")
            continue
        conflicts.append((r["county"], have["chair"], r["chair"]))
        del out[fips]
    return n


def build(page_rows, minutes_rows, officers, today):
    out, inexact, dropped, conflicts = {}, [], [], []
    n_page = collect_page(page_rows, officers, out, inexact, dropped, today)
    n_min = collect_minutes(minutes_rows, officers, out, dropped, conflicts, today)
    return out, inexact, dropped, conflicts, n_page, n_min


def crosses_january(confirmed, today):
    """True when a 1 January falls in (confirmed, today].

    Iowa boards elect their chair at the January reorganisation, so a name
    read before one and carried past it is no longer a claim about who chairs
    the board -- however few days old it is.
    """
    for year in range(confirmed.year, today.year + 1):
        jan = datetime.date(year, 1, 1)
        if confirmed < jan <= today:
            return True
    return False


def carry_forward(prior, out, verdicts, officers, today):
    """Report every county that left the file, and carry back the askable ones.

    Returns (carried_fips, lines). `verdicts` maps a 5-digit FIPS to the set of
    verdicts the two scrapers reported for it THIS run -- a county the minutes
    route never tries contributes only the page route's.
    """
    carried, lines = [], []
    for fips in sorted(prior):
        if fips in out:
            continue
        was = prior[fips]
        county = was.get("county", fips)
        chair = was.get("chair")
        saw = verdicts.get(fips) or set()
        said = " (this run said: %s)" % ", ".join(sorted(saw)) if saw else ""

        def drop(why):
            lines.append("  DROPPED %s: %r left the file — %s%s"
                         % (county, chair, why, said))

        if not saw:
            drop("the county was not swept at all this run")
            continue
        if saw & frozenset(["robots-refused", "robots-disallowed"]):
            # Say this one in its own words. A refusal is not the county
            # failing to name a chair; it is the site declining to be read,
            # and a carried copy would be its data kept alive against that.
            drop("the site refused this client, so nothing is carried")
            continue
        if not saw <= CARRY_VERDICTS:
            drop("the county was asked and named no chair this run")
            continue
        if not chair or chair not in _roster(officers, fips):
            drop("the carried name is not on the county's supervisor roster")
            continue
        stamp = was.get("confirmedOn")
        try:
            confirmed = datetime.date.fromisoformat(stamp)
        except (TypeError, ValueError):
            drop("no confirmedOn date, so nothing measures how old it is")
            continue
        if crosses_january(confirmed, today):
            drop("a January reorganisation has fallen since %s" % stamp)
            continue
        age = (today - confirmed).days
        if age > MAX_CARRY_DAYS:
            drop("last read %d days ago, past the %d-day limit" % (age, MAX_CARRY_DAYS))
            continue
        out[fips] = dict(was)
        carried.append(fips)
        lines.append("  CARRIED %s: %r kept, unreachable this run, last read "
                     "%s (%d days)" % (county, chair, stamp, age))
    return carried, lines


def substantive_changes(prior, out):
    """Which counties changed in a field OTHER than `confirmedOn`.

    EVERY resolved record is re-stamped with today's date on every run, which
    is what the carry rule needs and which also means the shipped file differs
    from its base every single week. The workflow diffs that file to decide
    whether to open a PR, so without this line a reviewer cannot tell a week
    where a chair actually changed from a week where nothing did but the
    stamps -- they open the diff to find out, every time. (The nine Illinois
    AFR files have the same shape.)

    Returns (lines, summary) where `summary` is one sentence for the PR body.
    """
    def bare(rec):
        return {k: v for k, v in rec.items() if k != "confirmedOn"}

    moved = []
    for fips in sorted(set(prior) | set(out)):
        was, now = prior.get(fips), out.get(fips)
        if was is not None and now is not None:
            if bare(was) == bare(now):
                continue
            fields = sorted(k for k in set(bare(was)) | set(bare(now))
                            if bare(was).get(k) != bare(now).get(k))
            moved.append(((now or was).get("county", fips), ", ".join(fields)))
        elif now is not None:
            moved.append((now.get("county", fips), "added"))
        else:
            moved.append((was.get("county", fips), "removed"))

    lines = ["  CHANGED %s: %s" % (county, what) for county, what in moved]
    if not moved:
        summary = ("No county changed in any field other than `confirmedOn` — "
                   "this refresh re-read the same chairs and only restamped "
                   "the dates.")
    else:
        summary = ("%d county record(s) changed in a field other than "
                   "`confirmedOn`: %s."
                   % (len(moved), "; ".join("%s (%s)" % m for m in moved)))
    return lines, summary


def verdicts_by_fips(page_rows, minutes_rows):
    """{19xxx -> {verdict, ...}} across both scrapers' caches."""
    seen = {}
    for rows in (page_rows, minutes_rows):
        for r in rows:
            v = r.get("verdict")
            if v:
                seen.setdefault("19" + r["fips"], set()).add(v)
    return seen


# Each case: label, the prior record, the verdicts this run reported for it,
# and whether it should still be in the file afterwards. The roster used is
# Clayton's own, so a case can test the re-gate by naming somebody else.
TODAY = datetime.date(2026, 9, 12)
ROSTER = {"19043": {"supervisors": [{"name": "Ray Peterson"},
                                    {"name": "Doug Reimer"}]}}
CARRY_CASES = [
    ("unreachable, 1 day old — the Clayton case",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"unreachable"}, True),
    ("unreachable, 59 days old — inside the limit",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-07-15"},
     {"unreachable"}, True),
    ("unreachable, 61 days old — past the limit",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-07-13"},
     {"unreachable"}, False),
    ("unreachable but no confirmedOn — nothing measures its age",
     {"chair": "Ray Peterson", "county": "Clayton"},
     {"unreachable"}, False),
    ("asked and named nobody",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"none"}, False),
    ("two candidates",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"many"}, False),
    ("our own roster file lost the county",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"no-roster"}, False),
    ("the site said no — never carried",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"robots-refused"}, False),
    ("the minutes portal said no — never carried",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"robots-disallowed"}, False),
    ("unreachable on one route, asked on the other — not carried",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"unreachable", "none"}, False),
    ("the county was not swept at all",
     {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": "2026-09-11"},
     set(), False),
    ("carried name has left the supervisor roster",
     {"chair": "Somebody Else", "county": "Clayton", "confirmedOn": "2026-09-11"},
     {"unreachable"}, False),
]
# A January reorganisation clears a carried chair however fresh it is, so this
# case is dated against its own `today` rather than TODAY.
JANUARY_CASES = [
    ("3 days old but across 1 January", datetime.date(2027, 1, 3),
     "2026-12-31", False),
    ("3 days old, same side of 1 January", datetime.date(2027, 1, 5),
     "2027-01-02", True),
]


# The PR body says "nothing moved" off this function, so a false negative
# here tells a reviewer to skip a diff that did change a chair.
A = {"chair": "Ray Peterson", "county": "Clayton", "route": "page",
     "confirmedOn": "2026-09-12"}
CHANGE_CASES = [
    ("only confirmedOn moved — the ordinary weekly restamp",
     {"19043": A}, {"19043": dict(A, confirmedOn="2026-09-19")}, 0),
    ("nothing moved at all", {"19043": A}, {"19043": dict(A)}, 0),
    ("the chair changed", {"19043": A},
     {"19043": dict(A, chair="Doug Reimer", confirmedOn="2026-09-19")}, 1),
    ("the route changed", {"19043": A},
     {"19043": dict(A, route="page+minutes", confirmedOn="2026-09-19")}, 1),
    ("a county was added", {}, {"19043": A}, 1),
    ("a county was removed", {"19043": A}, {}, 1),
    ("one restamp and one real change",
     {"19043": A, "19001": dict(A, county="Adair")},
     {"19043": dict(A, confirmedOn="2026-09-19"),
      "19001": dict(A, county="Adair", chair="Someone Else")}, 1),
]


def selftest():
    bad = 0
    for label, prior, out, expect in CHANGE_CASES:
        lines, summary = substantive_changes(prior, out)
        ok = len(lines) == expect
        # a zero-change run must say so rather than listing nothing silently
        if expect == 0 and "No county changed" not in summary:
            ok = False
        bad += 0 if ok else 1
        print("  %-4s %-58s %d" % ("OK" if ok else "FAIL", label, len(lines)))
    for label, rec, saw, expect in CARRY_CASES:
        out = {}
        carry_forward({"19043": rec}, out, {"19043": saw}, ROSTER, TODAY)
        got = "19043" in out
        bad += 0 if got == expect else 1
        print("  %-4s %-58s %s" % ("OK" if got == expect else "FAIL", label,
                                   "carried" if got else "dropped"))
    for label, today, stamp, expect in JANUARY_CASES:
        out = {}
        rec = {"chair": "Ray Peterson", "county": "Clayton", "confirmedOn": stamp}
        carry_forward({"19043": rec}, out, {"19043": {"unreachable"}}, ROSTER, today)
        got = "19043" in out
        bad += 0 if got == expect else 1
        print("  %-4s %-58s %s" % ("OK" if got == expect else "FAIL", label,
                                   "carried" if got else "dropped"))
    n = len(CARRY_CASES) + len(JANUARY_CASES) + len(CHANGE_CASES)
    if bad:
        sys.exit("build-ia-county-chair --selftest: FAIL — %d of %d case(s)"
                 % (bad, n))
    print("build-ia-county-chair --selftest: OK — %d case(s)" % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="compare against the shipped file and exit non-zero on drift")
    ap.add_argument("--selftest", action="store_true",
                    help="run the carry-forward rules against literal cases; no network")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    for path, script in ((CACHE, "ia_county_chair_scraper.py"),
                         (MINUTES_CACHE, "ia_county_minutes_chair_scraper.py")):
        if not os.path.exists(path):
            sys.exit("build-ia-county-chair: FAIL — no scraper cache at %s; run "
                     "ia/scripts/%s first" % (path, script))
    rows = json.load(open(CACHE, encoding="utf-8"))
    minutes = json.load(open(MINUTES_CACHE, encoding="utf-8"))["counties"]
    officers = json.load(open(OFFICERS, encoding="utf-8"))
    today = datetime.date.today()
    out, inexact, dropped, conflicts, n_page, n_min = build(
        rows, minutes, officers, today.isoformat())

    # The shipped file is an input too. A first build, or a checkout without
    # the data file, simply carries nothing forward -- and says so, because a
    # silent zero here is the failure this whole section exists to end.
    prior = {}
    if os.path.exists(OUT_PATH):
        prior = json.load(open(OUT_PATH, encoding="utf-8"))
    else:
        print("  no previously shipped roster — nothing to carry forward")
    carried, carry_lines = carry_forward(
        prior, out, verdicts_by_fips(rows, minutes), officers, today)
    change_lines, change_summary = substantive_changes(prior, out)

    for county, chair, route in dropped:
        print("  DROPPED %s (%s route): %r is not on the county's supervisor roster"
              % (county, route, chair))
    for county, chair, page, how in inexact:
        print("  name join (%s) %s: roster %r <- page %r" % (how, county, chair, page))
    for county, page_name, minutes_name in conflicts:
        print("  CONFLICT %s: the board page says %r and the minutes say %r — "
              "shipping neither" % (county, page_name, minutes_name))
    for line in carry_lines:
        print(line)
    for line in change_lines:
        print(line)
    print("  %s" % change_summary)
    # The weekly workflow puts this sentence in the PR body, so a reviewer can
    # tell an empty refresh from a real one without opening the diff. Written
    # through GITHUB_OUTPUT as a single line and consumed via `env:`, never
    # interpolated into a shell command.
    out_file = os.environ.get("GITHUB_OUTPUT")
    if out_file:
        with open(out_file, "a", encoding="utf-8") as fh:
            fh.write("changes=%s\n" % change_summary.replace("\n", " "))

    if n_page < MIN_PAGE:
        sys.exit("build-ia-county-chair: FAIL — the board-page route resolved %d "
                 "counties, floor is %d" % (n_page, MIN_PAGE))
    if n_min < MIN_MINUTES:
        sys.exit("build-ia-county-chair: FAIL — the minutes route resolved %d "
                 "counties, floor is %d" % (n_min, MIN_MINUTES))

    payload = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        have = open(OUT_PATH, encoding="utf-8").read() if os.path.exists(OUT_PATH) else ""
        if have != payload:
            sys.exit("build-ia-county-chair: FAIL — %s is not what this scrape "
                     "produces (%d counties)" % (OUT_PATH, len(out)))
        print("build-ia-county-chair: OK — %d counties (%d board page, %d minutes, "
              "%d carried), shipped file current"
              % (len(out), n_page, n_min, len(carried)))
        return
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(payload)
    print("build-ia-county-chair: OK — wrote %d county board chairs (%d from the "
          "board-page route, %d from the minutes route, %d carried from the "
          "previously shipped file) to %s"
          % (len(out), n_page, n_min, len(carried), OUT_PATH))


if __name__ == "__main__":
    main()
