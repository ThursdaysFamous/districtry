#!/usr/bin/env python3
"""
Write il/data/source/chicago-candidates.json from chicago_candidates_scraper.py's
output: who filed to run in Chicago's next municipal election, office by
office, with the Chicago Board of Election Commissioners' status for each.

WHAT IT IS FOR. scripts/build_candidates_page.py turns it into
il/chicago-candidates.html, the "who is running in my ward" page Adam asked for
on 2026-11-10. The map does not read it, so it lives in data/SOURCE beside the
other build-time rosters (ward-members.json is the same case), where
validate_index.py's rule that every data/app file is referenced by the app does
not apply.

IT REFUSES TO WRITE, rather than shipping a list the page would misdescribe,
when:
  * an office is not one it knows (mayor, clerk, treasurer, alderperson of a
    ward, member of a police district council): a new kind of race needs words
    on the page before it can be shown;
  * the 50 wards, the 22 police districts or the three citywide offices are
    not each there exactly once;
  * a status is not one the page explains (STATUS_WORDS): the Board prints
    "Candidate" and "Challenged" today, and a new word, such as one for a
    candidate removed by an objection, is exactly the change a reader must not
    be shown unexplained;
  * a name carries a digit or is implausibly long, which is what an address,
    a page footer or two rows run together would look like. The scraper never
    reads the address line; this is the second lock on that door.

NO ADDRESS IS WRITTEN. The Board's list prints each candidate's home address;
the scraper does not read it and nothing here could carry it, because each
candidate is rebuilt from exactly three keys (name, status, ballotNumber).

    python3 scripts/build_chicago_candidates.py /tmp/chicago_candidates_raw.json
"""

import datetime
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "il", "data", "source", "chicago-candidates.json")

# The words build_candidates_page.py prints beside each status. Adding a status
# means adding its explanation here AND on the page, in the same change.
STATUS_WORDS = {
    "Candidate": "no objection on file",
    "Challenged": "an objection has been filed",
}

CITYWIDE = ("Mayor", "Clerk", "Treasurer")
WARDS = set(range(1, 51))
# Chicago's 22 police districts. 13, 21 and 23 were consolidated into others
# in 2012 and have no council.
POLICE_DISTRICTS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18,
                    19, 20, 22, 24, 25}

WARD_RE = re.compile(r"^Alderperson, (\d{1,2})(?:st|nd|rd|th) Ward$")
POLICE_RE = re.compile(
    r"^Council Member, Chicago Police Department (\d{1,2})(?:st|nd|rd|th) District$")
VOTE_FOR_RE = re.compile(r"^Vote for (?:not more than )?(One|Two|Three|Four|Five)$", re.I)
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

MAX_NAME = 60


def fail(msg):
    print("build-chicago-candidates: FAIL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def classify(office):
    if office in CITYWIDE:
        return office.lower(), None
    m = WARD_RE.match(office)
    if m:
        return "ward", int(m.group(1))
    m = POLICE_RE.match(office)
    if m:
        return "police-council", int(m.group(1))
    fail("an office this page has no words for: %r" % office)


def build(raw):
    for key in ("electionDate", "listAsOf", "sourcePage", "sourceUrl", "read"):
        if not raw.get(key):
            fail("raw file has no %s" % key)
    try:
        datetime.date.fromisoformat(raw["electionDate"])
        datetime.datetime.fromisoformat(raw["listAsOf"])
        datetime.date.fromisoformat(raw["read"])
    except ValueError as e:
        fail("a date does not parse: %s" % e)

    contests, seen = [], set()
    for c in raw["contests"]:
        kind, district = classify(c["office"])
        if (kind, district) in seen:
            fail("%s appears twice" % c["office"])
        seen.add((kind, district))
        m = VOTE_FOR_RE.match(c.get("voteFor") or "")
        if not m:
            fail("%s: 'Vote for' line not read (%r)" % (c["office"], c.get("voteFor")))
        names = set()
        people = []
        for p in c["candidates"]:
            name, status = p["name"], p["status"]
            if status not in STATUS_WORDS:
                fail("%s: status %r has no words on the page yet (known: %s)"
                     % (c["office"], status, ", ".join(sorted(STATUS_WORDS))))
            if re.search(r"\d", name) or not re.search(r"[A-Za-z]", name) \
                    or len(name) > MAX_NAME:
                fail("%s: a name this will not ship (%d characters, digit=%s); "
                     "an address or a page footer looks like this"
                     % (c["office"], len(name), bool(re.search(r"\d", name))))
            if name in names:
                fail("%s: %s is listed twice" % (c["office"], name))
            names.add(name)
            row = {"name": name, "status": status}
            if p.get("ballotNumber"):
                if not re.fullmatch(r"\d{1,3}", p["ballotNumber"]):
                    fail("%s: ballot number %r is not a number"
                         % (c["office"], p["ballotNumber"]))
                row["ballotNumber"] = int(p["ballotNumber"])
            people.append(row)
        contests.append({"kind": kind, "district": district, "office": c["office"],
                         "voteFor": NUMBER_WORDS[m.group(1).lower()],
                         "candidates": people})

    for office in CITYWIDE:
        if (office.lower(), None) not in seen:
            fail("no %s race on the list" % office)
    wards = {d for k, d in seen if k == "ward"}
    if wards != WARDS:
        fail("wards on the list are not 1-50: missing %s, extra %s"
             % (sorted(WARDS - wards), sorted(wards - WARDS)))
    police = {d for k, d in seen if k == "police-council"}
    if police != POLICE_DISTRICTS:
        fail("police districts on the list are not Chicago's 22: missing %s, extra %s"
             % (sorted(POLICE_DISTRICTS - police), sorted(police - POLICE_DISTRICTS)))
    if not next(c for c in contests if c["kind"] == "mayor")["candidates"]:
        fail("nobody is listed for mayor")
    n_ward = sum(len(c["candidates"]) for c in contests if c["kind"] == "ward")
    if n_ward < 50:
        fail("only %d alderperson candidates across 50 wards" % n_ward)
    empty = [c["office"] for c in contests if not c["candidates"]]
    if empty:
        print("build-chicago-candidates: NOTE nobody filed for %s" % ", ".join(empty))

    return {
        "electionDate": raw["electionDate"],
        "listAsOf": raw["listAsOf"],
        "read": raw["read"],
        "source": "Chicago Board of Election Commissioners",
        "sourcePage": raw["sourcePage"],
        "sourceUrl": raw["sourceUrl"],
        "contests": contests,
    }


def main():
    if len(sys.argv) != 2:
        fail("usage: build_chicago_candidates.py <scraper output>")
    with open(sys.argv[1], encoding="utf-8") as f:
        raw = json.load(f)
    out = build(raw)
    # The read date moves every day, so a run whose list did not change leaves
    # the file alone and opens no pull request.
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        if {k: v for k, v in old.items() if k != "read"} == \
                {k: v for k, v in out.items() if k != "read"}:
            print("build-chicago-candidates: list unchanged since %s; file left as it is"
                  % old.get("read"))
            return
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    n = sum(len(c["candidates"]) for c in out["contests"])
    ch = sum(1 for c in out["contests"] for p in c["candidates"] if p["status"] == "Challenged")
    print("wrote %s: %d races, %d candidates (%d challenged), list as of %s"
          % (os.path.relpath(OUT, REPO_ROOT), len(out["contests"]), n, ch, out["listAsOf"]))


if __name__ == "__main__":
    main()
