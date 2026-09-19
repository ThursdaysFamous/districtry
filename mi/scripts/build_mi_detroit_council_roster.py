#!/usr/bin/env python3
"""Build mi/data/app/mi-detroit-council-members.json — the nine people Detroit
elects to its City Council, read by the `detroit-council` card in mi/index.html.

Detroit City Charter (2012) Art. 4 §4-101: SEVEN members elected by district
and TWO elected at large. The seven ride the polygons this app draws; the two
represent every district and ship in a `citywide` block the card renders under
its own heading, because a district card naming only the district member would
answer seven ninths of the question and look complete doing it. That is the Des
Moines shape (ia/scripts/build_dsm_council.py), and Detroit is the same problem.

WHY THIS FILE EXISTS AT ALL, AND WHAT THE FIRST ATTEMPT GOT WRONG
-------------------------------------------------------------------
The layer shipped with NO roster and a card that said, in the app and in four
other places, that "every route to Detroit's council membership is shut". That
sentence was built out of five measurements, and two of them were wrong:

  * `data.detroitmi.gov` was called challenged. It is not, and never was: it
    answers 200 with a readable robots.txt. That verdict came from grepping a
    68 KB page for the word "challenge" and finding one hit — WHILE THE STATUS
    CODE SAID 200. A substring is not a status.
  * The fleet's own terminal fetch rung — the Internet Archive, in weekly use
    for Kendall and McHenry since 2026-07 — was never tried. It answers, with
    all nine members, their districts and their roles.

So the roster was not unavailable; it was unattempted. The measurements that
survived are the ones about the live site (detroitmi.gov and
mvic.sos.state.mi.us both sat behind a genuine Cloudflare managed challenge on
2026-09-05, on both the requests and the client-hints rungs) and about
Legistar, which is abandoned and could not place a member on a district even
when it was not.

CORRECTED 2026-09-19: that 2026-09-05 measurement was right on its day and was
written here as a standing property, which it is not. Across the three commits
that have ever written this file, `archivedAt` reads 20260831152830
(2026-09-05, archive), null (2026-09-09 — THE DIRECT RUNG SERVED) and
20260912152333 (2026-09-16, archive). Detroit's challenge is INTERMITTENT. The
scraper already did the right thing, trying the direct rung first every run;
what failed was the reporting, because the weekly PR body was one static
paragraph and nobody saw the 2026-09-09 success for ten days. See
mi/scripts/summarize_detroit_roster_change.py.

WHAT THIS REFUSES TO WRITE
---------------------------
  * fewer than nine members, or districts that are not exactly 1..7, or other
    than two at-large seats (the charter's own arithmetic);
  * a roster whose archive snapshot is older than the scraper's ceiling —
    enforced there, at fetch time, so a stale copy never reaches this stage;
  * a district whose member changed without the file changing, which is what
    the weekly workflow's PR is for: officeholder data gets a human look.

CONTACT SHIPS AT THE BODY'S LEVEL AND NOWHERE ELSE
----------------------------------------------------
NO PER-MEMBER contact exists: zero `mailto:` and zero `tel:` links across all
nine, on the listing and on a member's own profile page alike. So no member row
carries a number and nothing here invents one; that absence is the gap
`detroit-council-contact`.

What the city DOES publish is the body's own office — "City Council Office, 2
Woodward Ave. Suite 1340, Detroit, MI 48226, (313) 224-3443" — once, for the
Council rather than for anyone on it. That is the switchboard case
(`docs/EXPANSION_GUIDE.md` Part 5), so it ships once at the top level and the
card renders it as the Council's office, never as a member's direct line. The
scraper refuses if that number stops being unique on the page.

    python3 mi/scripts/mi_detroit_council_scraper.py       # refresh the cache
    python3 mi/scripts/build_mi_detroit_council_roster.py
    python3 mi/scripts/build_mi_detroit_council_roster.py --check
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(HERE)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
OUT = os.path.join(APP_DATA_DIR, "mi-detroit-council-members.json")
CACHE = os.path.join(HERE, ".cache", "mi_detroit_council.json")

EXPECT_DISTRICTS = [str(n) for n in range(1, 8)]
EXPECT_AT_LARGE = 2
EXPECT_SEATS = len(EXPECT_DISTRICTS) + EXPECT_AT_LARGE


def fail(msg):
    print("detroit-council-roster: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def shape(cache):
    districts, citywide = {}, []
    for m in cache["members"]:
        row = {"name": m["name"], "seat": m["seat"], "profileUrl": m["profileUrl"]}
        if m.get("district") is None:
            citywide.append(row)
        else:
            key = str(m["district"])
            if key in districts:
                fail("two members carry district %s" % key)
            districts[key] = row
    doc = {
        "archivedAt": cache.get("archivedAt"),
        "citywide": sorted(citywide, key=lambda r: r["name"]),
        "districts": districts,
        "sourceUrl": cache["sourceUrl"],
    }
    if cache.get("office"):
        doc["office"] = cache["office"]
    return doc


def validate(doc):
    total = len(doc["districts"]) + len(doc["citywide"])
    if total != EXPECT_SEATS:
        fail("%d seats, charter says %d" % (total, EXPECT_SEATS))
    if sorted(doc["districts"], key=int) != EXPECT_DISTRICTS:
        fail("districts %s, expected %s" % (sorted(doc["districts"], key=int), EXPECT_DISTRICTS))
    if len(doc["citywide"]) != EXPECT_AT_LARGE:
        fail("%d at-large seats, expected %d" % (len(doc["citywide"]), EXPECT_AT_LARGE))
    for key, row in doc["districts"].items():
        if not row["name"].strip():
            fail("district %s has no name" % key)
        if not row["profileUrl"].startswith("https://detroitmi.gov/"):
            fail("district %s links off-site: %s" % (key, row["profileUrl"]))
    names = [r["name"] for r in doc["citywide"]] + [r["name"] for r in doc["districts"].values()]
    if len(set(names)) != len(names):
        fail("one person holds two seats")
    # The office is the BODY's, so it must never appear on a member: a number
    # that reached a member row would render as nine direct lines that are not.
    office = doc.get("office") or {}
    if office:
        if not office.get("phone"):
            fail("an office block with no phone — drop the block rather than shipping it empty")
        for row in list(doc["districts"].values()) + doc["citywide"]:
            if "phone" in row or "email" in row:
                fail("%s carries contact the city does not publish per member" % row["name"])


def check():
    if not os.path.exists(OUT):
        fail("%s is missing" % OUT)
    with open(OUT, encoding="utf-8") as fh:
        doc = json.load(fh)
    validate(doc)
    print("detroit-council-roster: OK — %d district members + %d at large, "
          "source %s%s" % (len(doc["districts"]), len(doc["citywide"]), doc["sourceUrl"],
                           ", archive snapshot %s" % doc["archivedAt"] if doc.get("archivedAt") else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="offline gate on the shipped file")
    args = ap.parse_args()
    if args.check:
        return check()

    if not os.path.exists(CACHE):
        fail("no scraper cache — run mi/scripts/mi_detroit_council_scraper.py first")
    with open(CACHE, encoding="utf-8") as fh:
        cache = json.load(fh)

    doc = shape(cache)
    validate(doc)
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("Wrote %s — %d district members + %d at large%s"
          % (OUT, len(doc["districts"]), len(doc["citywide"]),
             " (archive snapshot %s)" % doc["archivedAt"] if doc.get("archivedAt") else ""))


if __name__ == "__main__":
    main()
