#!/usr/bin/env python3
"""Write il/data/app/il-library-trustees.json from the scraper's output.

The pair to il_library_trustees_scraper.py, which reads a board of trustees off
each library's own website for the cards no Annual Financial Report answers for.
This half does the refusing: a run that lost coverage leaves the shipped file
alone rather than replacing it with a thinner one.

TWO SOURCES MUST NEVER BOTH CLAIM ONE LIBRARY, and this is the guard. A
district-governed library's filing is the better source — it is a document the
library signed and filed with the State — so a library that starts filing leaves
the scraper's pool on the next run by itself; if one ever appears in both, that
is a pool defect and the build refuses rather than letting a card show two
boards or the app pick one silently. il/index.html stamps this file only where
the filing named no board, and validate_index.py fails on an overlap, so the
rule is enforced on both sides of the hand-off.

A KEY THAT NO CARD CAN REACH FAILS, the sibling builder's rule for the same
reason: the boundary layer's own spelling of a library's name is the join key, so
a library renamed upstream leaves a record here that nothing renders and no gate
would otherwise notice.

EVERY RECORD CARRIES THE PAGE IT WAS READ FROM AND THE DAY IT WAS READ. A
website is not a filing: it has no fiscal year, it can be months stale, and the
only honest thing a card can say is which page said this and when we looked. A
record without both is refused.

A FETCH THAT FAILED IS NOT A LIBRARY THAT STOPPED PUBLISHING, which is Adam's
ruling of 2026-09-19 — "Preserve data we have already fetched" — and here it is
load-bearing rather than a nicety. 176 small library hosts read over an hour is
a lot of chances to time out: Carbondale Public Library answered in one sweep
and timed out in the next, an hour apart, with nothing changed at either end.
A run that simply wrote what it got would drop that library's nine trustees off
the card and the retention gate would see a real loss. So a library the scrape
could not READ keeps its last-good record and its own older read stamp, and the
carried-forward count prints every run.

THE SPLIT IS BY WHAT THE VERDICT MEANS, not by whether the run succeeded. A
transport failure or a host that now refuses us carries forward: neither says
anything about what the page says, and a refusal tells us not to READ a host
rather than to unpublish what it already served. A page that LOADED and no
longer lists a board does not: that is the library having changed its site, the
real event check_roster_retention.py exists to notice, and carrying it forward
would publish trustees the library has taken down.

Usage:
    python3 build_il_library_trustees.py <scraper-output.json> [--check]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import substantive_changes, emit_changes_output  # noqa: E402
from il_library_district_officials_scraper import (  # noqa: E402
    shipped_cards, statewide_library_counties)
from il_library_trustees_scraper import MIN_MEMBERS, MAX_MEMBERS  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "il", "data", "app")
OUT_PATH = os.path.join(APP_DIR, "il-library-trustees.json")
FILINGS = os.path.join(APP_DIR, "il-library-district-officials.json")

SOURCE = "Each library's own website"

# MEASURED 2026-09-25 on the first full run: 53 libraries, 388 trustees, 233 of
# them with a role. Each floor sits about 17% under its value, because a library
# redesigning its site is a real event that must not freeze the other fifty-odd.
#
# TWO PASSES OVER THE SAME POOL AN HOUR APART AGREED ON 51 OF THEM, which is
# what makes these floors settable at all: the first read 54 and the second 53,
# three libraries lost to a transport failure and two gained that had failed one
# before. A floor set from a single pass would be a floor set from that pass's
# weather.
MIN_LIBRARIES = 44
MIN_TRUSTEES = 320
MIN_CARDS = 44
# A board page that names a role for nobody is a shape worth flooring on its
# own: the roles come from a different part of the page than the names, and a
# parse regression can lose every role while keeping every name.
MIN_WITH_ROLE = 180

# A verdict that says nothing about what the page says. The record is carried
# forward with its own older read stamp; see the docstring.
CARRY_FORWARD = ("site-unreachable", "board-page-unreachable",
                 "robots-unreadable", "robots-refused")


def fail(msg):
    sys.exit("build-il-library-trustees: FAIL — " + msg)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scraped", help="il_library_trustees_scraper.py --out")
    parser.add_argument("--check", action="store_true",
                        help="compare against the shipped file instead of writing")
    args = parser.parse_args()

    with open(args.scraped, encoding="utf-8") as handle:
        payload = json.load(handle)
    scraped = payload.get("libraries")
    if not isinstance(scraped, dict) or not scraped:
        fail("the scraper's output has no libraries object")
    read_on = (payload.get("generated") or "")[:10]
    if len(read_on) != 10:
        fail("the scraper's output has no usable `generated` stamp")

    shipped = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as handle:
            shipped = json.load(handle).get("libraries") or {}

    libraries, carried = {}, []
    for name, record in scraped.items():
        verdict = record.get("verdict")
        if verdict == "read":
            board = [m for m in (record.get("board") or []) if m.get("name")]
            entry = {"board": board, "readOn": read_on}
            if record.get("boardUrl"):
                entry["boardUrl"] = record["boardUrl"]
            if record.get("heading"):
                entry["heading"] = record["heading"]
            libraries[name] = entry
            continue
        if verdict in CARRY_FORWARD and name in shipped:
            libraries[name] = shipped[name]
            carried.append("%s (%s, last read %s)"
                           % (name, verdict, shipped[name].get("readOn", "?")))
    for line in sorted(carried):
        print("  carried forward: %s" % line)
    # A library in the shipped file that this run READ a page for and found no
    # board on is DROPPED, and saying which ones is the whole point of printing
    # it: that is the real event, not a flaky fetch.
    dropped = sorted(set(shipped) - set(libraries))
    for name in dropped:
        print("  dropped: %s — this run read its page and found no board (%s)"
              % (name, (scraped.get(name) or {}).get("verdict", "not in the pool")))

    _kinds, where = shipped_cards(statewide_library_counties())
    cards = sum(len(where.get(name) or []) for name in libraries)
    orphans = sorted(name for name in libraries if not where.get(name))

    with open(FILINGS, encoding="utf-8") as handle:
        filings = json.load(handle)["libraries"]
    both = sorted(name for name in libraries
                  if (filings.get(name) or {}).get("board"))

    trustees = sum(len(v["board"]) for v in libraries.values())
    with_role = sum(1 for v in libraries.values()
                    for m in v["board"] if m.get("role"))
    short = sorted(n for n, v in libraries.items() if len(v["board"]) < MIN_MEMBERS)
    long_ = sorted(n for n, v in libraries.items() if len(v["board"]) > MAX_MEMBERS)
    unsourced = sorted(n for n, v in libraries.items() if not v.get("boardUrl"))

    problems = []
    for count, floor, what in ((len(libraries), MIN_LIBRARIES, "librar(ies)"),
                               (trustees, MIN_TRUSTEES, "trustee(s)"),
                               (cards, MIN_CARDS, "card(s) stamped"),
                               (with_role, MIN_WITH_ROLE, "trustee(s) with a role")):
        if count < floor:
            problems.append("%d %s < floor %d" % (count, what, floor))
    if orphans:
        problems.append("no card carries: %s" % ", ".join(orphans[:8]))
    if both:
        problems.append("these librar(ies) are in BOTH this file and the "
                        "filings' boards, so a card would carry two: %s"
                        % ", ".join(both[:8]))
    if short:
        problems.append("below the floor of %d trustee(s): %s"
                        % (MIN_MEMBERS, ", ".join(short[:8])))
    if long_:
        problems.append("past the ceiling of %d trustee(s): %s"
                        % (MAX_MEMBERS, ", ".join(long_[:8])))
    if unsourced:
        problems.append("no board page url on: %s" % ", ".join(unsourced[:8]))
    if problems:
        for problem in problems:
            print("  %s" % problem, file=sys.stderr)
        fail("refusing to write a payload that lost coverage")

    out = {
        "generated": payload.get("generated"),
        "libraries": libraries,
        "source": SOURCE,
    }
    text = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.check:
        if not os.path.exists(OUT_PATH):
            fail("%s is missing" % OUT_PATH)
        with open(OUT_PATH, encoding="utf-8") as handle:
            shipped = json.load(handle)
        # `generated` and every record's `readOn` move on a run that read the
        # same pages and found the same people, so neither is compared.
        def bare(doc):
            libs = {k: {kk: vv for kk, vv in v.items() if kk != "readOn"}
                    for k, v in (doc.get("libraries") or {}).items()}
            rest = {k: v for k, v in doc.items() if k not in ("generated", "libraries")}
            rest["libraries"] = libs
            return rest
        if bare(shipped) != bare(out):
            fail("%s does not match a fresh read of the libraries' own sites"
                 % OUT_PATH)
        print("build-il-library-trustees: OK — shipped file matches (%d "
              "librar(ies) on %d card(s), %d trustee(s))"
              % (len(libraries), cards, trustees))
        return

    prior = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as handle:
            prior = json.load(handle)
    moved_lines, moved_summary = substantive_changes(prior, out, "libraries", 1)
    for line in moved_lines:
        print(line)
    print("  %s" % moved_summary)
    emit_changes_output(moved_summary)

    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)
    fresh = sum(1 for v in libraries.values() if v.get("readOn") == read_on)
    print("build-il-library-trustees: wrote %s — %d librar(ies) on %d card(s), "
          "%d trustee(s), %d with a role; %d read this run, %d carried forward, "
          "%d dropped, of a pool of %d"
          % (OUT_PATH, len(libraries), cards, trustees, with_role, fresh,
             len(libraries) - fresh, len(dropped), len(scraped)))


if __name__ == "__main__":
    main()
