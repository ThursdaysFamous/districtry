#!/usr/bin/env python3
"""
Read the Cook County Clerk's suburban precinct results saved in il/data/source/
election-results/2026-11-03/cook/ and write them as one raw read for
build_il_county_election_results.py, in the shape the Clarity reader writes.

IT READS NO NETWORK. The Clerk's results site (results1126.cookcountyclerkil.gov)
answers this project's readers with a Cloudflare block page, so the files are
downloaded by hand in a browser, one race to a file, and committed; record.json
beside them holds each file's SHA-256 and the time it was saved, and this reads
the committed copies. The Clerk counts suburban Cook County (Chicago's Board of
Election Commissioners counts the city), so these rows are the 1,430 precincts
outside Chicago.

EACH FILE is the Clerk's "ElectionResults.xlsx" for one race: a Summary sheet
(the election, the race and "Vote for N", then a row per candidate with party
and votes), a Township sheet and a Precinct sheet ("Precinct", "Registered
Voters", "Ballots Cast", a column per candidate, "Total Votes", then a
"Suburban Cook County" row of totals). It is read with the standard library,
so the check needs no spreadsheet package.

THE ROWS ARE CHECKED, NOT TRUSTED: each candidate's precinct votes must add up
to the "Suburban Cook County" row and to the Summary sheet's figure; each
precinct's candidate votes must add up to its "Total Votes"; the races every
precinct votes in must give every precinct the same registered voters and
ballots cast; and a district race, which lists only its own precincts, must
give each the same registered voters and no more ballots (a precinct split
between two districts has only its own side's ballots in each).

EACH RACE IS NAMED for the builder by canonical(): the federal, statewide and
legislative titles in the wording its classify() reads; a race Chicago also
counts (the county's offices, the Water Reclamation District, the county
board, Board of Review, judges and subcircuits) under the Clerk's title, which
is Chicago's too, so the two halves fold into one contest; and a referendum
another office also counts under that office's title (SHARED_QUESTIONS).

Usage:
    python3 scripts/il_cook_election_results_reader.py -o il/data/source/election-results-cook-raw.json
    python3 scripts/il_cook_election_results_reader.py --check -o il/data/source/election-results-cook-raw.json
"""

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from scraper_common import make_fail

fail = make_fail("il-cook-election-results-reader")

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "..", "il", "data", "source", "election-results", "2026-11-03", "cook")
SOURCE = "https://results1126.cookcountyclerkil.gov/"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
TOTAL_ROW = "Suburban Cook County"


def _col(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(path):
    """{sheet name: [rows of strings]} for a workbook, standard library only."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        rels = {}
        for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
            rels[r.get("Id")] = r.get("Target")
        out = {}
        for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
            target = rels[sh.get(REL)].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            rows = []
            for row in ET.fromstring(z.read(target)).find("m:sheetData", NS):
                vals = {}
                for c in row:
                    v = c.find("m:v", NS)
                    if c.get("t") == "s" and v is not None:
                        text = shared[int(v.text)]
                    elif c.get("t") == "inlineStr":
                        text = "".join(t.text or "" for t in c.iter("{%s}t" % NS["m"]))
                    else:
                        text = v.text if v is not None else None
                    vals[_col(c.get("r"))] = text
                rows.append([vals.get(i) for i in range(max(vals) + 1)] if vals else [])
            out[sh.get("name")] = rows
    return out


def number(text, where):
    t = (text or "").replace(",", "").strip()
    if not re.fullmatch(r"\d+", t):
        fail("%s: %r is not a count" % (where, text))
    return int(t)


def read_race(fname, rec):
    path = os.path.join(DIR, fname)
    body = open(path, "rb").read()
    if hashlib.sha256(body).hexdigest() != rec["sha256"]:
        fail("%s is not the file record.json says was saved" % fname)
    book = read_xlsx(path)
    for need in ("Summary", "Precinct"):
        if need not in book:
            fail("%s has no %s sheet" % (fname, need))
    summary = [r for r in book["Summary"] if any(r)]
    title = re.sub(r"\s+", " ", summary[1][0] or "").strip()
    m = re.fullmatch(r"Vote for (\d+)", (summary[1][1] or "").strip())
    if not title or not m:
        fail("%s: the Summary sheet does not name the race and how many to vote for" % fname)
    vote_for = int(m.group(1))
    if [c for c in summary[2][:3]] != ["Candidate", "Party", "Votes"]:
        fail("%s: the Summary sheet's candidate header is %r" % (fname, summary[2]))
    party_of, summary_votes = {}, {}
    for r in summary[3:]:
        if r and r[0]:
            party_of[r[0].strip()] = (r[1] or "").strip()
            summary_votes[r[0].strip()] = number(r[2], fname + " Summary")
    rows = [r for r in book["Precinct"] if any(r)]
    head = [(h or "").strip() for h in rows[0]]
    if head[:3] != ["Precinct", "Registered Voters", "Ballots Cast"] or head[-1] != "Total Votes":
        fail("%s: the Precinct sheet's header is %r" % (fname, head))
    choices = head[3:-1]
    if sorted(choices) != sorted(summary_votes):
        fail("%s: the Precinct sheet's candidates %r are not the Summary's %r" % (fname, choices, sorted(summary_votes)))
    turnout, precincts, total = {}, {}, None
    for r in rows[1:]:
        r = list(r) + [None] * (len(head) - len(r))
        name = (r[0] or "").strip()
        vals = [number(v, "%s, %s" % (fname, name)) for v in r[1:len(head)]]
        if name == TOTAL_ROW:
            total = vals
            continue
        if name in turnout:
            fail("%s: precinct %r appears twice" % (fname, name))
        if sum(vals[2:-1]) != vals[-1]:
            fail("%s, %s: candidate votes add to %d, the row says %d" % (fname, name, sum(vals[2:-1]), vals[-1]))
        turnout[name] = vals[:2]
        precincts[name] = vals[2:-1]
    if total is None:
        fail("%s: no %r row of totals" % (fname, TOTAL_ROW))
    for i, ch in enumerate(choices):
        got = sum(v[i] for v in precincts.values())
        if got != total[2 + i] or got != summary_votes[ch]:
            fail("%s, %s: precinct votes add to %d, the totals row says %d and the Summary %d"
                 % (fname, ch, got, total[2 + i], summary_votes[ch]))
    for i, label in ((0, "registered voters"), (1, "ballots cast")):
        if sum(v[i] for v in turnout.values()) != total[i]:
            fail("%s: precinct %s add to %d, the totals row says %d"
                 % (fname, label, sum(v[i] for v in turnout.values()), total[i]))
    return {"title": title, "voteFor": vote_for, "choices": choices, "parties": [party_of[c] for c in choices],
            "turnout": turnout, "precincts": precincts, "ballots": total[1]}


ORDINAL = re.compile(r"^(\d+)(?:st|nd|rd|th) District$")

# Races Chicago's Board of Election Commissioners also counts, under the same
# title the Clerk uses: the county's own offices, the Water Reclamation
# District, the county board's and Board of Review's districts and the
# judges. Each is folded into Chicago's contest of the same name where the
# city votes in it; a district wholly outside the city (County Board 6th,
# 13th Subcircuit) becomes a contest of suburban Cook alone.
WITH_CHICAGO = [
    (re.compile(r"^(Board President|Clerk|Sheriff|Treasurer|Assessor), Cook County$"), "county"),
    (re.compile(r"^Commissioner, Water Reclamation Dist\b"), "mwrd"),
    (re.compile(r"^Commissioner, County Board \d+(?:st|nd|rd|th) District$"), "county-board"),
    (re.compile(r"^Board of Review, \d+(?:st|nd|rd|th) District$"), "ccbr"),
    (re.compile(r"^(Appellate|Circuit) Court Judge \(Vacancy of [^)]+\)$"), "judges"),
    (re.compile(r"^Judge, \d+(?:st|nd|rd|th) Subcircuit \(Vacancy of [^)]+\)$"), "judicial-subcircuit"),
]

# A ballot question the Clerk shares with another office: the title that
# office gives it, so the two halves are one contest, and both halves reach
# beyond the area each office counts. Read from the DuPage and Kane reads
# (election-results-clarity-raw.json, election-results-kane-raw.json) and
# Chicago's results; a question not listed here appears on no other ballot
# this layer reads, and is taken to lie inside suburban Cook.
SHARED_QUESTIONS = {
    "Cook County, Millionaire Tax Amendment": ("The Cook County Millionaire Amendment for Property Tax Relief", True),
    "Bartlett Public Library District, Issue Bonds (Renovation)": ("Bartlett Public Library - Library Bonds (Renovations)", False),
    "Bartlett Public Library District, Issue Bonds (New Library)": ("Bartlett Public Library - Library Bonds (New)", False),
    "Roselle Fire Protection District, Increase Limiting Rate": ("Roselle Fire District - Limiting Rate", False),
    "Combined School District 113A, Increase Limiting Rate": ("CSD 113A - Limiting Rate", False),
    "East Dundee & Countryside Fire Protection District, Issue Bonds":
        ("(EAST DUNDEE & CSIDE FIRE) PROPOSITION TO ISSUE $3,500,000 BONDS", False),
    "East Dundee & Countryside Fire Protection District, New Tax Rate":
        ("(EAST DUNDEE & CSIDE FIRE) PROPOSITION TO CREATE A NEW TAX RATE FOR EMERGENCY AND RESCUE FUND PURPOSES", False),
    "Unit School District 300, Issue Bonds": ("(COMMUNITY 300) PROPOSITION TO ISSUE $355,500,000 SCHOOL BUILDING BONDS", False),
}


def canonical(title, vote_for, choices):
    """The Clerk's race title (already in the map's own wording: "Senator,
    U.S.", "State Representative, 15th District") as (name, district,
    fixed) for build_il_county_election_results.py. With fixed None the
    builder's classify() reads name and district; otherwise fixed says what
    the race is. A title no rule knows fails rather than guessing."""
    from build_il_county_election_results import ordinal
    office, _, where = [x.strip() for x in title.partition(",")]
    if title == "Senator, U.S.":
        return "FOR UNITED STATES SENATOR", "FEDERAL", None
    if title == "Governor & Lieutenant Governor, Illinois":
        return "FOR GOVERNOR AND LIEUTENANT GOVERNOR", "STATE OF ILLINOIS", None
    if where == "State of Illinois" and office in ("Attorney General", "Secretary of State", "Comptroller", "Treasurer"):
        return "FOR " + office.upper(), "STATE OF ILLINOIS", None
    m = ORDINAL.match(where)
    if m:
        n = ordinal(int(m.group(1))).upper()
        if office == "U.S. Representative":
            return "FOR REPRESENTATIVE IN CONGRESS", n + " CONGRESSIONAL DIST", None
        if office == "State Senator":
            return "FOR STATE SENATOR", n + " LEGISLATIVE DIST", None
        if office == "State Representative":
            return "FOR REPRESENTATIVE IN THE GENERAL ASSEMBLY", n + " REPRESENTATIVE DIST", None
    m = re.fullmatch(r"Superintendent of Schools, (\w+) County", title)
    if m:
        # the regional superintendent of a neighbour's region, which reaches
        # into suburban Cook; one contest with that county's own half
        return "FOR REGIONAL SUPERINTENDENT OF SCHOOLS (%s County)" % m.group(1), "", None
    for pat, group in WITH_CHICAGO:
        if pat.match(title):
            return title, "", {"group": group, "chicago": True, "seats": vote_for}
    if re.fullmatch(r"Trustee, .+ Sanitary District(, 2Yr)?", title):
        return title, "", {"group": "local", "beyond": False, "seats": vote_for}
    if sorted(c.strip().upper() for c in choices) == ["NO", "YES"]:
        if title in SHARED_QUESTIONS:
            name, chicago = SHARED_QUESTIONS[title]
            return name, "", {"group": "questions", "chicago": chicago, "beyond": True}
        return title, "", {"group": "questions", "beyond": False}
    return None, None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--check", action="store_true",
                    help="write nothing; fail unless --out already holds exactly this read")
    args = ap.parse_args()
    sys.path.insert(0, HERE)
    record = json.load(open(os.path.join(DIR, "record.json")))
    saved = sorted(f for f in os.listdir(DIR) if f.endswith(".xlsx"))
    if sorted(record["files"]) != saved:
        fail("record.json names %s and the folder holds %s" % (sorted(record["files"]), saved))
    races = [(f, read_race(f, record["files"][f])) for f in saved]
    # the precinct turnout comes from the races every precinct votes in, and
    # they must agree; a district race lists only its own precincts, with the
    # same registered voters and, in a precinct split between two districts,
    # only the ballots cast on that district's side
    whole = [(f, r) for f, r in races if len(r["turnout"]) == len(max((x for _, x in races), key=lambda x: len(x["turnout"]))["turnout"])]
    turnout = whole[0][1]["turnout"]
    ballots = whole[0][1]["ballots"]
    for f, r in whole:
        if r["turnout"] != turnout:
            fail("%s gives the precincts different registered voters or ballots than %s" % (f, whole[0][0]))
    contests = []
    for f, r in races:
        for pname, (reg, bal) in r["turnout"].items():
            if pname not in turnout:
                fail("%s: precinct %r is in no countywide race" % (f, pname))
            if reg != turnout[pname][0] or bal > turnout[pname][1]:
                fail("%s, %s: %d registered and %d ballots, against %d and %d countywide"
                     % (f, pname, reg, bal, turnout[pname][0], turnout[pname][1]))
        name, district, fixed = canonical(r["title"], r["voteFor"], r["choices"])
        if name is None:
            fail("%s: no title rule reads %r" % (f, r["title"]))
        race = {"name": name, "district": district, "clerkTitle": r["title"], "voteFor": r["voteFor"],
                "choices": r["choices"], "precincts": r["precincts"]}
        if fixed:
            race["fixed"] = fixed
        contests.append(race)
    county = {
        "county": "cook", "name": "Cook", "source": SOURCE, "publisher": "Cook County Clerk",
        "areaName": "Suburban Cook County", "read": max(record["files"][f]["saved"] for f, _ in races),
        "ballots": ballots, "outsideBallots": 0, "turnout": turnout, "contests": contests,
    }
    doc = {"read": county["read"], "host": SOURCE, "counties": [county]}
    text = json.dumps(doc, separators=(",", ":")) + "\n"
    if args.check:
        if not os.path.exists(args.out) or open(args.out).read() != text:
            fail("%s is not what the saved files read as; run without --check and commit it" % args.out)
        print("il-cook-election-results-reader: OK — %s matches the %d saved race files"
              % (os.path.basename(args.out), len(races)))
        return
    with open(args.out, "w") as fh:
        fh.write(text)
    print("Suburban Cook County: %d precincts, %d races, %d ballots" % (len(turnout), len(contests), ballots),
          file=sys.stderr)
    for f, r in races:
        print("  %s: %s (vote for %d), %d choices" % (f, r["title"], r["voteFor"], len(r["choices"])), file=sys.stderr)


if __name__ == "__main__":
    main()
