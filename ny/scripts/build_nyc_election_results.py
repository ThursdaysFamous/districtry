#!/usr/bin/env python3
"""
Build ny/data/app/election-results.json and its Assembly District files from
the raw read made by nyc_election_results_scraper.py: every contest the Board
of Elections in the City of New York reports by election district, each
district's votes for each candidate, grouped by the map layer the contest is
elected from, so the Election Results card can offer the races on the clicked
election district's ballot by layer and the map can fill each election
district by the candidate with the most votes there.

THE KEY is the Election District layer's own `ElectDist` (the City Planning
service the layer draws): the Assembly District times 1,000 plus the election
district, so AD 41 ED 1 is 41001. Measured on the 3 November 2026 results: the
Board reports 4,285 election districts and the layer draws 4,214, every one of
which the Board reports. The other 71 are numbers the Board lists with no
votes in any contest; the build fails if one of them ever counts a vote, since
that would be votes cast where the map draws nothing.

THE LAYER'S KEYS are read from the same service the map reads, at build time,
after its robots.txt (services5.arcgis.com answers that request with HTTP 403,
which RFC 9309 reads as no policy).

WHAT A CONTEST IS: one of the Board's contest pages. GROUP_RULES places each by
its office: the three statewide offices, the city's ballot proposals, and the
offices elected from a U.S. House, State Senate, Assembly, City Council,
judicial or Civil Court district, or a whole borough (the Surrogate and the
borough-wide Civil Court judges). An office no rule places fails the build.

BEYOND THE CITY: the statewide offices, and the House and Senate districts the
Board marks as reaching past the city line, carry `beyond`, so the card says
its totals are the city's part of the race.

CANDIDATES ON SEVERAL LINES. The Board gives each party line its own column,
so a candidate on three lines has three; the build adds a candidate's lines
together into one choice. The write-in column stays a choice of its own.

CHOICES. The pages list the lines in the order the ballot does, which in New
York follows party, so the choices are ordered by a rule that cannot lean: Yes,
then No, for a proposal; otherwise alphabetically by the name as printed, with
the write-ins last. A choice's colour is that position, never a party. The
Governor and Lieutenant Governor run as a ticket, which the pages print as two
names run together; the build splits them and joins them with "and".

NAMES. The contest page's own title where it says more than the home page's
office (the one City Council race names its district only there), and a
proposal as its number and what it asks.

AN ELECTION DISTRICT LISTED TWICE on one page with the same counts is counted
once; listed twice with different counts, the build fails.

SEATS. The pages do not say how many a contest elects. Where one party line
lists several candidates (the Supreme Court and some Civil Court races, where a
party nominates as many as there are seats), the most names any one line
carries is taken as the contest's seats, so the card says its shares are of
votes and not of voters.

TURNOUT. The pages report no ballots cast, so each election district's turnout
is [null, null] and the card says nothing about turnout.

UNOFFICIAL UNTIL CERTIFIED. The file carries `certified: false` and the time it
was read. When the Board certifies the results, run the build with
`--certified <date>`.

Usage:
    python3 ny/scripts/build_nyc_election_results.py /tmp/nyc_results_raw.json \
        --election-date 2026-11-03 [--certified YYYY-MM-DD] [--layer-keys keys.json]
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
FLEET_SCRIPTS = os.path.join(os.path.dirname(INSTANCE), "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from election_results_common import ResultsError, write_results  # noqa: E402
from scraper_common import make_fail, require_robots_once  # noqa: E402

fail = make_fail("build-nyc-election-results")

APP_DATA = os.path.join(INSTANCE, "data", "app")
LAYER_SERVICE = ("https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/"
                 "NYC_Election_Districts/FeatureServer/0/query")
USER_AGENT = "districtry/1.0 (+https://districtry.com/ny/)"
MIN_LAYER_KEYS = 4000
MIN_CONTESTS = 60
WRITE_IN = "Write-in"

# (group id, label shown in the race menu, the map layer it is elected from or
# None, a pattern the office matches, whether the whole group reaches beyond
# the city (True), never does (False) or does where the Board marks a district
# as crossing the city line (None)). First match wins.
GROUP_RULES = [
    ("statewide", "Statewide offices", None,
     r"^(Governor|State Comptroller|Attorney General)\b", True),
    ("questions", "Ballot proposals", None, r"^Proposal Number", False),
    ("congress", "U.S. House", "congress", r"^Representative in Congress", None),
    ("state-senate", "State Senate", "state-senate", r"^State Senator", None),
    ("state-assembly", "State Assembly", "state-assembly", r"^Member of the Assembly", False),
    ("council", "City Council", "council", r"^Member of the City Council", False),
    ("borough", "Borough-wide courts", "borough", r"^(Surrogate|Judge of the Civil Court - County)\b", False),
    ("judicial-district", "Supreme Court", "judicial-district", r"^Justice of the Supreme Court", False),
    ("municipal-court", "Civil Court by district", "municipal-court",
     r"^Judge of the Civil Court - District", False),
]
GROUP_ORDER = [g[0] for g in GROUP_RULES]
FIRST = {"YES": 0, "NO": 1}


def group_of(office):
    for gid, _label, _layer, pattern, beyond in GROUP_RULES:
        if re.search(pattern, office):
            return gid, beyond
    fail("no group places the contest %r; add a rule to GROUP_RULES" % office)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def choice_order(choice):
    up = choice.upper()
    if up in FIRST:
        return (0, FIRST[up], "")
    if choice == WRITE_IN:
        return (2, 0, "")
    return (1, 0, up)


def read_layer_keys(path=None):
    if path:
        keys = json.load(open(path))
    else:
        require_robots_once(LAYER_SERVICE, USER_AGENT)
        keys, offset = [], 0
        while True:
            q = urllib.parse.urlencode({"where": "1=1", "outFields": "ElectDist", "returnGeometry": "false",
                                        "f": "json", "resultOffset": offset, "resultRecordCount": 2000,
                                        "orderByFields": "ElectDist"})
            req = urllib.request.Request(LAYER_SERVICE + "?" + q, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                doc = json.load(resp)
            if "error" in doc:
                fail("the Election District service answered an error: %r" % doc["error"])
            feats = doc.get("features") or []
            keys += [f["attributes"]["ElectDist"] for f in feats]
            if not doc.get("exceededTransferLimit") and len(feats) < 2000:
                break
            offset += len(feats)
    keys = {str(int(k)) for k in keys if k is not None}
    if len(keys) < MIN_LAYER_KEYS:
        fail("the Election District layer names %d districts, expected at least %d"
             % (len(keys), MIN_LAYER_KEYS))
    return keys


def contest_name(office, title):
    """The contest page's own title where it says more than the home page's
    office (the City Council seat names its district there), and a proposal
    as its number and what it asks."""
    office = re.sub(r"\s+", " ", office).strip().rstrip("*").strip()
    title = re.sub(r"\s+", " ", title or "").strip().rstrip("*").strip()
    m = re.match(r"^(Proposal Number \d+), a Question: (?:Proposed Charter Amendment: )?(.+)$", title)
    if m:
        return "%s: %s" % m.groups()
    if title.startswith(office) and len(title) > len(office):
        return title
    return office


def choice_name(column, ticket):
    """A column's name as a reader should see it. A Governor and Lieutenant
    Governor ticket is printed as two names run together ("Kathy C. Hochul
    Adrienne E. Adams"); each name there carries a middle initial, so the
    first name ends one word after the first initial."""
    name = re.sub(r"\s+", " ", column).strip()
    if name.upper() == "WRITE-IN":
        return WRITE_IN
    if name.upper() in FIRST:
        return name[:1].upper() + name[1:].lower()
    if ticket:
        words = name.split()
        for i, w in enumerate(words[:-2]):
            if re.fullmatch(r"[A-Z]\.", w):
                return "%s and %s" % (" ".join(words[:i + 2]), " ".join(words[i + 2:]))
        fail("cannot split the ticket %r into two names" % name)
    return name


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw")
    ap.add_argument("--election-date", required=True)
    ap.add_argument("--certified", help="the date the Board of Elections certified the results")
    ap.add_argument("--layer-keys", help="a JSON list of the layer's ElectDist values, instead of reading the service")
    ap.add_argument("--app-data", default=APP_DATA, help="the app's data/app directory (default: ny/data/app)")
    args = ap.parse_args()

    raw = json.load(open(args.raw))
    allowed = read_layer_keys(args.layer_keys)
    reported = set()
    out = []
    used = set()
    phantom_votes = []
    for c in raw["contests"]:
        group, beyond = group_of(c["office"])
        if beyond is None:
            beyond = bool(c["partOutside"])
        name = contest_name(c["office"], c.get("title"))
        lines = c["lines"]
        ticket = "/" in c["office"]
        names = [choice_name(n, ticket) for n, _p in lines]
        choices = sorted(set(names), key=choice_order)
        col_to = [choices.index(n) for n in names]
        precincts = {}
        seen_rows = {}
        for ad, ed, vals in c["rows"]:
            key = str(ad * 1000 + ed)
            if key in seen_rows:
                if seen_rows[key] != vals:
                    fail("%s: AD %d ED %d is listed twice with different counts" % (name, ad, ed))
                continue
            seen_rows[key] = vals
            counts = [0] * len(choices)
            for i, v in enumerate(vals):
                counts[col_to[i]] += v
            if key not in allowed:
                if sum(counts):
                    phantom_votes.append("%s AD %d ED %d (%d votes)" % (name, ad, ed, sum(counts)))
                continue
            reported.add(key)
            precincts[key] = [sum(counts)] + counts
        total = [0] * (len(choices) + 1)
        for vals in precincts.values():
            total = [a + b for a, b in zip(total, vals)]
        question = set(ch.upper() for ch in choices) <= {"YES", "NO"}
        if question != (group == "questions"):
            fail("%s: a %s placed in %s" % (name, "question" if question else "race", group))
        names_on_lines = {}
        for ln_name, party in lines:
            if ln_name.upper() != "WRITE-IN":
                names_on_lines[party] = names_on_lines.get(party, 0) + 1
        seats = 1 if question else max(names_on_lines.values() or [1])
        base = "c" + c["id"]
        cid = base
        n = 1
        while cid in used:
            n += 1
            cid = "%s-%d" % (base, n)
        used.add(cid)
        entry = {"id": cid, "name": name, "group": group, "beyond": beyond,
                 "choices": choices, "total": total, "precincts": precincts,
                 "_sort": (GROUP_ORDER.index(group), natural(name))}
        if seats > 1:
            entry["seats"] = seats
        out.append(entry)
    if phantom_votes:
        fail("votes counted in election districts the layer does not draw: %s" % "; ".join(phantom_votes[:20]))
    if len(out) < MIN_CONTESTS:
        fail("only %d contests; expected at least %d" % (len(out), MIN_CONTESTS))
    unreported = sorted(allowed - reported)
    if unreported:
        fail("%d election districts the layer draws are in no contest: %s"
             % (len(unreported), ", ".join(unreported[:20])))
    out.sort(key=lambda c: c.pop("_sort"))

    turnout = {"total": [None, None], "precincts": dict((k, [None, None]) for k in allowed)}
    groups = [{"id": g[0], "label": g[1], "layer": g[2]} for g in GROUP_RULES]
    stamp = {
        "election": "General Election",
        "electionDate": args.election_date,
        "source": raw["source"],
        "read": raw["read"],
        "certified": bool(args.certified),
        "certifiedDate": args.certified or None,
        # The Board's own "Information As Of" time from its home page, so the
        # daily job reads every page again only when the Board has published.
        "boardAsOf": raw.get("asOf"),
    }
    note = ("Unofficial election night results as the Board of Elections in the City of New "
            "York publishes them by election district, until the Board certifies them "
            "(certified then reads true). Precinct keys are the Election District layer's "
            "ElectDist: the Assembly District times 1,000 plus the election district. A "
            "candidate's votes on several party lines are added into one choice. The pages "
            "report no turnout. Each election district's counts are in a part file named for "
            "its Assembly District (ad + the district number). The layout is "
            "scripts/election_results_common.py's.")
    try:
        n, nparts = write_results(args.app_data, stamp, groups, turnout, out,
                                  lambda k: "ad%d" % (int(k) // 1000), note)
    except ResultsError as e:
        fail(str(e))
    by = {}
    for c in out:
        by[c["group"]] = by.get(c["group"], 0) + 1
    print("wrote %d contests (%s), %d part files under %s"
          % (n, ", ".join("%s %d" % (g, by[g]) for g in GROUP_ORDER if g in by), nparts,
             os.path.relpath(args.app_data)), file=sys.stderr)


if __name__ == "__main__":
    main()
