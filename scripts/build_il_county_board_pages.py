#!/usr/bin/env python3
"""Write six Illinois counties' board rosters from their own board pages.

The scraper beside this one (`il_county_board_pages_scraper.py`) explains WHY
these six exist as one pipeline: each was recorded as a county that had been
asked about its board and had not replied, while publishing its members on its
own website the whole time.

WHERE THE FILES GO, AND THE GATE THAT DECIDES IT. `il/data/source/`, not
`il/data/app/`. `scripts/validate_index.py` requires every file in an instance's
`data/app` to be referenced by that instance's `index.html`, and none of these
six is: not one has county-board GEOMETRY, so the map draws no district for them
and no card reads a roster. That gate is right, so the rosters sit with the other
build-time inputs, and `scripts/build_county_pages.py`'s `il_districted` adapter
reads BOTH directories — the Cook and Chicago-ward precedent — so each county
still gets its own page naming its members for a reader and for a crawler.

The day one of these counties' districts can be drawn, its roster moves to
`data/app`, gains a worksheet entry and a network-first `sw.js` line, and the
gate passes. Nothing here has to change for that to happen.

ONE FILE PER COUNTY, because that is what the adapter's glob reads and what
makes a county's roster removable on its own. Each is
`<slug>-county-board-members.json`, keyed by district, in the shape every other
Illinois districted roster already uses.

THE FLOORS ARE THE SCRAPER'S AND ARE NOT REPEATED HERE. A second copy of
"Bond seats five" is a second thing to keep true; the scraper refuses to emit a
county that falls short, so this refuses only what it alone can see — a county
in the payload it does not know, a county it knows missing from the payload, and
a district that names nobody without saying why.

    python3 scripts/il_county_board_pages_scraper.py --out /tmp/boards.json
    python3 scripts/build_il_county_board_pages.py /tmp/boards.json
"""

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from il_county_board_pages_scraper import SOURCES  # noqa: E402

OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "source")


def note(msg):
    print("build-il-county-board-pages: %s" % msg, file=sys.stderr)


def fail(msg):
    note("FAIL — %s" % msg)
    raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("payload", help="the scraper's --out file")
    ap.add_argument("--county", action="append", choices=sorted(SOURCES),
                    help="write only these counties (default: every county in "
                         "the payload)")
    args = ap.parse_args()

    with open(args.payload, encoding="utf-8") as fh:
        payload = json.load(fh)

    unknown = sorted(set(payload) - set(SOURCES))
    if unknown:
        fail("the payload carries %s, which this pipeline does not know. Add it "
             "to SOURCES in il_county_board_pages_scraper.py, or scrape the "
             "counties this pipeline is for." % ", ".join(unknown))

    want = sorted(set(args.county or payload))
    missing = [slug for slug in want if slug not in payload]
    if missing:
        fail("asked to write %s and the payload does not carry %s — re-run the "
             "scraper for it rather than shipping a county with no roster."
             % (", ".join(want), ", ".join(missing)))

    written = 0
    for slug in want:
        districts = payload[slug]
        people = 0
        for label, entry in sorted(districts.items()):
            members = entry.get("members") or []
            people += len(members)
            # A DISTRICT THAT NAMES NOBODY MUST SAY WHY. Bureau's District 15 is
            # the one in the fleet today and carries the county's own silence as
            # a note; an empty district with no note is a seat this build has
            # dropped without telling anybody, which is the shape that put 112
            # non-names live on Rock Island's cards for fifteen days.
            if not members and not entry.get("note"):
                fail("%s district %s names nobody and gives no reason"
                     % (slug, label))
            for member in members:
                if not (member.get("name") or "").strip():
                    fail("%s district %s carries a record with no name"
                         % (slug, label))
        path = os.path.join(OUT_DIR, "%s-county-board-members.json" % slug)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(districts, fh, indent=2, sort_keys=True)
            fh.write("\n")
        note("%-11s %2d member(s) in %2d district(s) -> %s"
             % (slug, people, len(districts),
                os.path.relpath(path, REPO_ROOT)))
        written += 1
    note("wrote %d county roster(s)" % written)


if __name__ == "__main__":
    main()
