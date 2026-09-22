#!/usr/bin/env python3
"""Commissioner NAMES for the 35 counties the weekly scraper does not reach,
from the state layer's own certified-returns column.

WHAT THIS PUBLISHES AND WHY IT IS NOT A CONTRADICTION.
`build_mi_commissioner_districts.py` deliberately DISCARDS the `Commissioner`
and `Party` columns of this same service and refuses to write if either reaches
`data/app/`. That decision stands and is not reversed here. It was right: the
district file is a BOUNDARY file, refreshed when the boundary is, and a name
riding a boundary would have shipped Wayne District 5's commissioner -- who
died on 10 June 2025 -- as the sitting member with nothing on the card to say
otherwise.

What changed (Adam, 2026-09-22) is that a name may be published when the row
SAYS WHAT IT IS. These columns are the canvassed winners of the general
election of 5 November 2024. That is a fact with a date on it, and a row that
names the election is true whether or not the person still holds the seat --
the posture Clark, Union and Williamson already ship under in Illinois, where
every commissioner row names the election that seated them because a certified
return names who WON and never who holds the seat today.

So: a separate file, a separate route, and every record carries its own
provenance sentence. `mi-commissioner-districts.json` stays name-free and its
BANNED_FIELDS guard is untouched.

THE FOUR TRAPS, RE-MEASURED ON THE 35 RATHER THAN CARRIED OVER (2026-09-22).

(1) SPELLING. The served sample turned up Markam/Markham, Wuerful/Wuerfel,
    Richarc/Richard and Sealberg/Seaberg -- the layer's spelling against the
    county's own page. On the 35 THERE IS NO COMPARAND: these are the counties
    whose pages this project cannot read, which is why they are unserved. So
    the question is not "which spelling is right" but "what does a row do when
    the certified spelling is the only spelling there is", and the answer is:
    SHIP IT VERBATIM AND NEVER CORRECT IT. Correcting a name against a guess
    is inventing officeholder data, which this project does not do, and
    dropping the row would conceal a seat the county fills.

    What the builder does instead is REPORT. `near_duplicate_surnames()` prints
    every surname that is one edit from another surname anywhere in the layer,
    every run, with its county and district. Measured on the 35 today that is
    three pairs, of which two are plainly different people in different
    counties (Andersen/Anderson, Baughan/Vaughan) and one is a probable
    truncation: WEXFORD DISTRICT 2 SHIPS "Jason L. Nelso", one edit from a
    "Nelson" the layer carries twice elsewhere. It ships as spelled, it is
    printed on every run, and it is recorded on Wexford's gap record so that a
    question to the county has somewhere to land. The heuristic is a REPORT and
    not a gate precisely because it is two-thirds false positives.

(2) THE FILL RATE IS EVIDENCE AGAINST UPKEEP, NOT FOR IT. Measured on the 35:
    249 of 249 districts carry a Commissioner and 249 of 249 carry a Party --
    100% on both columns (Republican 179, Democratic 60, NPA 10). A winners
    list is complete BY CONSTRUCTION, because every district always has a
    winner and none can ever be blank, so the absence of vacancies says the
    column was filled once rather than that it is maintained. No row here may
    imply upkeep, and none does: `lede` names the election and stops.

(3) A WINNER WHO HAS SINCE LEFT IS REAL ON THIS COHORT, AND IT IS MEASURED.
    Three of the 35 publish a board page this project can read at all, so three
    is the whole comparand available. Of those, Manistee is the only one whose
    page renders names in its served bytes, and on it 6 of 7 certified names
    still match -- 5 exactly and one as a short form the test first read as a
    miss ("Jeffrey Dontz" certified, "Jeff Dontz" on the page) -- while ONE HAS
    GENUINELY CHANGED: District 6's certified winner is David Miehlke and the
    county's own page names Karen Goodman. That is the Wayne case on the 35,
    confirmed rather than assumed, and it is the reason every row here names
    the election instead of the office.

    The other two could not be measured and are recorded as such rather than as
    agreement: Van Buren renders its directory through a `county-directory-person`
    component, so NONE of its seven names is in the served bytes and a substring
    test reads 0 of 7 -- the method failing, not the county changing (the one
    apparent hit, "Peat", is inside a CSS `repeat(...)`). Newaygo's board URL as
    recorded in `mi-county-board-probe.json` on 2026-09-19 answers HTTP 404
    today, so there was nothing to compare; that is a stale URL in the artifact
    and is reported by this builder rather than fixed silently here.

(4) FIVE OF THE 35 DO PUBLISH NAMES AND ONLY THE PARSING IS HARD -- Washtenaw,
    Bay, Manistee, Newaygo and Van Buren. They ship on this route too, because
    a name a reader can check beats no name at all, and each carries
    `betterSource`, which the card and the county page render as the sentence
    saying the county publishes its own list and a scraper remains the better
    answer. Manistee is exactly why: its page is the one that caught the
    District 6 change.

FETCH POLICY. robots.txt for gisagocss.state.mi.us read as the fetching client
(`districtry/1.0 (+https://districtry.com/mi/)`) on 2026-09-22: HTTP 404, so
allow-all, no Crawl-delay and no Content-Signal. One query, no paging.

Usage:
    python3 mi/scripts/build_mi_returns_roster.py           # fetch and write
    python3 mi/scripts/build_mi_returns_roster.py --check   # offline drift gate
"""

import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_ROOT = os.path.dirname(HERE)
APP_DATA_DIR = os.path.join(INSTANCE_ROOT, "data", "app")
REPO_ROOT = os.path.dirname(INSTANCE_ROOT)

SERVICE = ("https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/"
           "boundaries/MapServer/10")
QUERY = (SERVICE + "/query?where=1%3D1&outFields=CountyFIPS,County,DistrictName,"
         "Commissioner,Party&returnGeometry=false&f=json&resultRecordCount=2000")
UA = "districtry/1.0 (+https://districtry.com/mi/)"

OUT_FILE = "mi-commissioner-returns.json"
SCRAPED_ROSTER = "mi-commissioner-members.json"
GAPS_FILE = "coverage-gaps.json"

# The election these columns certify. Stated once, here, and rendered into
# every record's own sentence -- never assembled in the app, where a fork
# could drift from it.
ELECTION_DATE = "2024-11-05"
ELECTION_NAME = "the general election of 5 November 2024"

# Exact, not floors: one statutory compilation with a known shape.
EXPECT_LAYER_FEATURES = 619
EXPECT_LAYER_COUNTIES = 83

# The five that publish a roster of their own; the parsing is what is hard.
# Each ships here WITH the note that a scraper remains the better answer.
PUBLISH_THEIR_OWN = ("Washtenaw", "Bay", "Manistee", "Newaygo", "Van Buren")

# Measured 2026-09-22 and printed every run; see trap (1). NOT A GATE: a
# one-edit surname is two-thirds false positives here, and only a person can
# tell a typo from a family name.
KNOWN_SPELLING_WATCH = {
    "Wexford|District 2": (
        "Jason L. Nelso",
        "PROBABLE TRUNCATION: one edit from `Nelson`, which this layer carries "
        "twice elsewhere (Grand Traverse District 6, Oakland District 10), and "
        "`Nelso` is not a surname this layer carries anywhere else. Ships as "
        "certified; recorded on Wexford's gap record as a question for the "
        "county."),
    "Mason|District 6": (
        "James S. Andersen",
        "PROBABLY CORRECT: one edit from `Anderson` (3x in this layer), but "
        "Andersen is an ordinary surname in its own right, so there is nothing "
        "here but the edit distance."),
    "Wexford|District 8": (
        "Jason D. Baughan",
        "PROBABLY CORRECT: one edit from `Vaughan` (2x), and Baughan is an "
        "ordinary surname. Wexford seats two Jasons with different middle "
        "initials, which reads odd and is not evidence of anything."),
}


def fail(msg):
    print("build-mi-returns-roster: FATAL: %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def fetch():
    """The layer's attributes. curl, so it works through an HTTPS proxy."""
    out = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "300", "-A", UA, QUERY],
        capture_output=True, text=True)
    if out.returncode != 0:
        fail("fetch failed: %s" % (out.stderr or "").strip()[:400])
    try:
        doc = json.loads(out.stdout)
    except ValueError:
        fail("the service did not return JSON (%d bytes)" % len(out.stdout))
    if "error" in doc:
        # An ArcGIS error envelope arrives with HTTP 200, so --fail misses it.
        fail("the service returned an error envelope: %s" % doc["error"])
    feats = doc.get("features") or []
    if doc.get("exceededTransferLimit"):
        fail("the service paged; this builder assumes one query returns all "
             "%d districts" % EXPECT_LAYER_FEATURES)
    if len(feats) != EXPECT_LAYER_FEATURES:
        fail("expected %d districts, got %d -- the source changed shape"
             % (EXPECT_LAYER_FEATURES, len(feats)))
    return [f["attributes"] for f in feats]


def slug_of(name):
    """The county slug the gap records and the panel use.

    A COPY of scripts/build_county_status.py's slug_of rather than an import:
    that function carries one override, `De Witt` -> `dewitt`, which is an
    ILLINOIS county, and importing it would hand a Michigan reader a rule that
    can only ever mislead here.
    """
    return name.lower().replace(".", "").replace(" ", "-")


def bare(county):
    return re.sub(r" County$", "", county)


def unserved_slugs():
    """The counties a gap record names -- the set this route is FOR.

    Read from the shipped gap file rather than derived as "83 minus the roster",
    because the gap records are what the Data gaps panel and the E.A.M. measure
    already read, and `mi/scripts/probe_mi_county_boards.py --check` already
    FAILS when that set and the served set disagree. Deriving it a second way
    would be a second reader of one question.
    """
    path = os.path.join(APP_DATA_DIR, GAPS_FILE)
    gaps = json.load(io.open(path, encoding="utf-8"))
    out = set()
    for rec in gaps.values():
        out |= set(rec.get("counties") or [])
    if not out:
        fail("%s names no counties, so this route has no cohort" % GAPS_FILE)
    return out


def served_fips():
    path = os.path.join(APP_DATA_DIR, SCRAPED_ROSTER)
    roster = json.load(io.open(path, encoding="utf-8"))
    return set(roster.keys())


# A GENERATIONAL SUFFIX IS NOT A SURNAME, and taking the last token as one is
# a defect this builder shipped for an hour: "Philip Duckham III" yields `iii`,
# so four seats read as different people when only a suffix differed. It biases
# BOTH readers below -- the spelling report and the staleness comparison.
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def surname(name):
    parts = [p.strip(".,") for p in name.replace(",", " ").split()]
    parts = [p for p in parts if len(p) > 1 and p.lower() not in SUFFIXES]
    return parts[-1].lower() if parts else ""


def _one_edit(a, b):
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    i = j = diff = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        diff += 1
        if diff > 1:
            return False
        if len(a) > len(b):
            i += 1
        elif len(a) < len(b):
            j += 1
        else:
            i += 1
            j += 1
    return diff + (len(a) - i) + (len(b) - j) <= 1


def near_duplicate_surnames(rows):
    """Surnames one edit apart anywhere in the layer -- REPORTED, never fixed.

    Compared across all 83 counties rather than only the 35, because the
    corroborating spelling usually sits in a county this route does not cover:
    Wexford's `Nelso` is only suspicious because Grand Traverse and Oakland
    both spell it `Nelson`.
    """
    names = {}
    for a in rows:
        nm = (a.get("Commissioner") or "").strip()
        if nm:
            names.setdefault(surname(nm), []).append(
                (bare(a["County"]), a["DistrictName"], nm))
    keys = sorted(names)
    pairs = []
    for i, x in enumerate(keys):
        for y in keys[i + 1:]:
            if _one_edit(x, y):
                pairs.append((x, y))
    return pairs, names


def compare_with_scraped(rows):
    """How stale is this column, measured where a comparand exists?

    The 35 have no county page to check against -- that is why they are on this
    route. But the OTHER 48 do: `mi-commissioner-members.json` is read from each
    county's own board page weekly, and the state layer covers all 83, so every
    seat those two share is a place where "who the state certified in November
    2024" can be set beside "who the county names now". 366 seats, which is a
    far better answer than the twelve-county sample of 2026-09-03.

    It is REPORTED and not gated. The rate is a property of the source, not of
    this build, and a gate on it would fire on somebody else's election.
    """
    path = os.path.join(APP_DATA_DIR, SCRAPED_ROSTER)
    scraped = json.load(io.open(path, encoding="utf-8"))
    by_seat = {}
    for a in rows:
        num = re.sub(r"^District\s+", "", a["DistrictName"]).strip()
        by_seat.setdefault(a["CountyFIPS"], {})[num] = a.get("Commissioner") or ""
    identical = form = surname_differs = 0
    differing = []
    for fips, rec in scraped.items():
        for num, member in (rec.get("districts") or {}).items():
            certified = (by_seat.get(fips) or {}).get(num)
            current = member.get("name")
            if not certified or not current:
                continue
            if certified.strip() == current.strip():
                identical += 1
            elif surname(certified) == surname(current):
                form += 1
            else:
                surname_differs += 1
                differing.append((rec["county"], num, certified, current))
    total = identical + form + surname_differs
    return total, identical, form, differing


def build(rows):
    cohort = unserved_slugs()
    served = served_fips()
    by_county = {}
    for a in rows:
        by_county.setdefault((a["CountyFIPS"], a["County"]), []).append(a)
    if len(by_county) != EXPECT_LAYER_COUNTIES:
        fail("the layer carries %d counties, expected %d"
             % (len(by_county), EXPECT_LAYER_COUNTIES))

    out, seats_total = {}, 0
    for (fips, county), districts in sorted(by_county.items()):
        name = bare(county)
        if slug_of(name) not in cohort:
            continue
        if fips in served:
            fail("%s (%s) is named by a gap record AND covered by %s. One of "
                 "the two is wrong, and shipping both would give the county "
                 "two rosters with different provenance."
                 % (name, fips, SCRAPED_ROSTER))
        seats = {}
        for a in sorted(districts, key=lambda d: d["DistrictName"]):
            num = re.sub(r"^District\s+", "", a["DistrictName"]).strip()
            person = (a.get("Commissioner") or "").strip()
            if not person:
                fail("%s %s carries no Commissioner; this route exists because "
                     "that column is complete, so a blank is a source change"
                     % (name, a["DistrictName"]))
            rec = {"name": person}
            party = (a.get("Party") or "").strip()
            if party:
                rec["party"] = party
            seats[num] = rec
        entry = {
            "county": name,
            "districts": seats,
            "seats": len(seats),
            # THE PROVENANCE IS PER RECORD, not a constant in the app, so a
            # card, a county page and a future consumer cannot disagree about
            # what these names are.
            "route": "certified-returns",
            "election": ELECTION_DATE,
            "sourceUrl": SERVICE,
            "readAt": datetime.date.today().isoformat(),
            "lede": (
                "These are the people the State of Michigan certified as "
                "elected to %%(county)s County's Board of Commissioners in %s. "
                "They are the winners of that election, not a list the county "
                "keeps up to date, so a seat that has changed hands since will "
                "still show the person who won it." % ELECTION_NAME),
            "cta_note": (
                "Opens the map with the commissioner-district layer on. The "
                "district boundaries come from the same state compilation; the "
                "names on this page come from its election-results column and "
                "are dated to that election."),
            "desc": (
                "Who won each seat on %(county)s County's Board of "
                "Commissioners at the last election the state certified, and "
                "which district each one represents."),
        }
        if name in PUBLISH_THEIR_OWN:
            entry["betterSource"] = (
                "%s County publishes its own list of commissioners, which is "
                "kept current where this one is dated. Reading it needs a "
                "scraper this project has not yet written, so the certified "
                "result is what ships today." % name)
        out[fips] = entry
        seats_total += len(seats)

    missing = sorted(cohort - {slug_of(v["county"]) for v in out.values()})
    if missing:
        fail("%d county(s) a gap record names are not in the state layer: %s"
             % (len(missing), ", ".join(missing)))
    return out, seats_total


def check_ledes(doc):
    """Every record on this route must carry its own provenance sentence.

    The whole permission for publishing these names is that the row says what
    they are. A record with no `lede` renders byte-identically to one that
    never had a provenance -- which is exactly the failure this gate exists to
    make impossible, because it would be invisible on the page.
    """
    bad = []
    for fips, rec in sorted(doc.items()):
        if rec.get("route") != "certified-returns":
            bad.append("%s (%s) is in this file and not on the "
                       "certified-returns route" % (rec.get("county"), fips))
            continue
        for key in ("lede", "election"):
            if not (rec.get(key) or "").strip():
                bad.append("%s (%s) carries no `%s`, so its names would ship "
                           "with nothing saying what they are"
                           % (rec.get("county"), fips, key))
        if rec.get("lede") and "%(county)s" not in rec["lede"]:
            bad.append("%s (%s) has a lede with no %%(county)s placeholder"
                       % (rec.get("county"), fips))
    return bad


def report(rows, doc, seats_total):
    pairs, names = near_duplicate_surnames(rows)
    print("build-mi-returns-roster: %d county(s), %d seat(s), every row dated "
          "to %s" % (len(doc), seats_total, ELECTION_DATE))
    fills = [d for r in rows for d in [r] if (r.get("Commissioner") or "").strip()]
    print("  fill rate across the whole layer: %d of %d districts carry a name "
          "-- complete by construction, which is evidence AGAINST upkeep"
          % (len(fills), len(rows)))
    # THE RAW PAIR LIST IS UNREADABLE AND THAT MATTERS: 19 pairs across the 83
    # counties, nearly all of them different people who happen to sit one edit
    # apart. What isolates a probable typo is ASYMMETRY -- a surname seen ONCE
    # against one the same layer spells another way more than once, which is
    # what made Wexford's `Nelso` visible. 19 pairs become 3 candidates.
    print("  surnames one edit apart anywhere in the layer: %d pair(s)"
          % len(pairs))
    shown = 0
    for x, y in pairs:
        for rare, common in ((x, y), (y, x)):
            if len(names[rare]) != 1 or len(names[common]) <= 1:
                continue
            county, dist, nm = names[rare][0]
            note = KNOWN_SPELLING_WATCH.get("%s|%s" % (county, dist))
            print("    %-16s %-12s %-24s '%s' once vs '%s' %dx"
                  % (county, dist, nm, rare, common, len(names[common])))
            if note:
                print("        recorded: %s" % note[1])
            else:
                print("        NOT RECORDED -- a new candidate; decide in "
                      "writing and add it to KNOWN_SPELLING_WATCH")
            shown += 1
    print("  -> %d candidate(s) after the asymmetry filter" % shown)
    print("  NOTHING ABOVE IS CORRECTED. A certified spelling is the only "
          "spelling these counties have; see trap (1) in the docstring.")
    total, identical, form, differing = compare_with_scraped(rows)
    print("  HOW STALE IS THIS COLUMN, on the %d seat(s) where the scraped "
          "roster gives a comparand:" % total)
    print("    identical .......................... %d" % identical)
    print("    same surname, different given form . %d  (Dave/David, middle "
          "initials, diacritics, generational suffixes)" % form)
    print("    different surname .................. %d" % len(differing))
    for county, num, certified, current in sorted(differing):
        print("      %-15s D%-3s certified=%-26s county now=%s"
              % (county, num, certified, current))
    print("    Read by hand 2026-09-22, those 28 split 18 / 9 / 1: EIGHTEEN "
          "name a different person, which is 4.9% of the 366; nine misspell "
          "the same person's surname (Fourmier/Fournier, Wuerful/Wuerfel, "
          "Goodking/Gooding, Blair/Bair, Rathe/Rathje, Herrington/Harrington, "
          "Peterson/Petersen, Bietzke/Brietzke, Mattews/Matthews); and one is "
          "a missing space (Clare D5, `David A.Hoefling`). THE SPLIT IS A HAND "
          "READING, NOT A COMPUTATION -- no rule here separates "
          "Fourmier/Fournier from Brown/Goike, and an earlier draft of this "
          "line said 31 because it was written against a scratch script whose "
          "surname rule counted `III` as a surname.")
    better = sorted(r["county"] for r in doc.values() if r.get("betterSource"))
    print("  publishes its own roster, so a scraper remains the better answer: "
          "%s" % (", ".join(better) or "none"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="offline: re-audit the shipped file, fetch nothing")
    args = ap.parse_args()
    out_path = os.path.join(APP_DATA_DIR, OUT_FILE)

    if args.check:
        if not os.path.exists(out_path):
            fail("%s is missing" % OUT_FILE)
        doc = json.load(io.open(out_path, encoding="utf-8"))
        problems = check_ledes(doc)
        cohort = unserved_slugs()
        shipped = {slug_of(r["county"]) for r in doc.values()}
        if shipped != cohort:
            problems.append(
                "the shipped file covers %d county(s) and the gap records name "
                "%d; only in the file: %s; only in the records: %s"
                % (len(shipped), len(cohort),
                   ", ".join(sorted(shipped - cohort)) or "none",
                   ", ".join(sorted(cohort - shipped)) or "none"))
        served = served_fips()
        both = sorted(set(doc) & served)
        if both:
            problems.append("county(s) in BOTH rosters: %s" % ", ".join(both))
        if problems:
            for p in problems:
                print("  FAIL: %s" % p, file=sys.stderr)
            fail("%d problem(s) with the shipped file" % len(problems))
        seats = sum(r["seats"] for r in doc.values())
        print("build-mi-returns-roster: OK -- %d county(s), %d seat(s), every "
              "record on the certified-returns route carries its own "
              "provenance and names %s; no county is in both rosters"
              % (len(doc), seats, ELECTION_NAME))
        return

    rows = fetch()
    doc, seats_total = build(rows)
    problems = check_ledes(doc)
    if problems:
        for p in problems:
            print("  FAIL: %s" % p, file=sys.stderr)
        fail("refusing to write names with nothing saying what they are")
    io.open(out_path, "w", encoding="utf-8").write(
        json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    report(rows, doc, seats_total)
    print("  wrote %s" % os.path.relpath(out_path, REPO_ROOT))


if __name__ == "__main__":
    main()
