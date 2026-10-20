#!/usr/bin/env python3
"""
North Carolina Court District Builder (superior and district court, from the statutes)
======================================================================================
Writes two boundary files, one per trial court whose judges are elected by
district:

    data/app/nc-superior-court-districts.json   73 districts  (G.S. 7A-41)
    data/app/nc-district-court-districts.json   47 districts  (G.S. 7A-133)

and the record its offline `--check` holds them to:

    data/source/nc-court-districts.source.json

THE STATUTES ARE THE SOURCE, AND THEY ARE MOSTLY WHOLE COUNTIES. Each table
names the counties of each district, so 91 of the 100 counties go whole into
one superior court district and 98 into one district court district, and those
are drawn from this instance's own county file, `state-counties.json`. NINE
COUNTIES ARE SPLIT for the superior court (New Hanover, Edgecombe, Wilson,
Wake, Cumberland, Durham, Guilford, Mecklenburg, Forsyth) and TWO for the
district court (Wake, Vance), and for those the law lists the 2010 Census
voting districts (VTDs) of each district, and where a VTD is divided, its 2010
Census blocks: G.S. 7A-41(b) and 7A-133(b), with 7A-41(c) and the closing
sentence of 7A-133(b) saying the names and lines are those of the 2010 Census
Redistricting TIGER/Line Shapefiles, and 7A-41(c1) that a later change to a
voting district does not move a court district. So the split counties are
drawn from the Census Bureau's 2010 TIGERweb service, VTD layer 72 and block
layer 18, and nothing else is read.

THE TEXT IS RETAINED AND HELD TO THE LIVE PAGE. The four sections are kept in
`data/source/statutes/` as plain text converted from the General Assembly's
HTML by `statute_text()`; the build fetches each live page, converts it the
same way and stops if it differs from the kept copy (`--accept-statutes`
replaces the copy once a person has read the change). `--check` parses only
the kept copies, offline, and fails if one changed since the record was
written.

THE PARSE IS HELD TO THE STATUTE'S OWN CROSS-REFERENCES, because each table
says "see subsection (b)" for its split districts and (b) says which
counties each one has. A district in one and not the other, a county in two
districts or in none, or a split county named whole somewhere fails the
build. So do these, each pinned to what the text said when the cards were
written, so a change makes a person read it:

  * THE JUDGE COUNTS DISAGREE IN THREE PLACES, one in each statute's way of
    giving a number twice. G.S. 7A-41(a) gives superior court District 31A
    two resident judges and (b)(22) says "It has one judge." G.S. 7A-133(a)
    gives district court District 12 eleven judges and District 32 six, while
    the residence paragraphs (b1) and (b3) say the district's voters "shall
    elect all eight judges" and "all five judges" "established for the
    District in subsection (a)". Why the paragraphs give smaller numbers is
    not established here; that they were left behind when the table was
    raised is an inference, not a measurement. For each of
    the three the file carries both numbers (`judgesDisagree`, table first),
    the paragraph that gives the second (`judgesDisagreeIn`) and no `judgeCount`,
    and the card says the law gives two numbers. Every other split superior
    court district's (b) count agrees with the table, and so do the two other
    residence paragraphs that give a number, (b2) for District 15 (seven) and
    (b4) for District 33 (six).
  * ONE BLOCK NUMBER IS PRINTED WITH 12 DIGITS: Cumberland's "510036004049",
    between 0510036004047 and 0510036004050 in the same list. It is read as
    0510036004049 through STATUTE_TYPOS, which fails if the typo ever goes.
  * ONE LIST CONTINUES PAST A SEMICOLON: in District 14B a block list resumes
    after "; " with no voting district named, so it is read as more blocks of
    the voting district before it (CONTINUED_LISTS).
  * THE 2029 TABLE IS ALREADY ENACTED. 7A-41(a) carries a second table,
    effective 1 January 2029, that drops Districts 10E and 31D and changes
    nothing else, and their (b) paragraphs are marked "(Repealed effective
    January 1, 2029)". The law as written does not say which district their
    ground joins; the file marks the two with `endsOn` and `nc/WATCH.md`
    carries the row.
  * RESIDENCE RULES: 7A-41(b1) has District 5's voters elect both its
    judges while reserving one seat for Onslow County residents and the
    other for Duplin, Jones or Sampson; 7A-133(b1)-(b8) do the same for eight
    district court districts. The file names the paragraph and the card says
    that some seats are reserved for residents of particular counties.

THE DIVIDING LINES ARE 2010 LINES AND THE COUNTY LINES ARE TODAY'S. The
county file is a later Census vintage than the 2010 VTDs, and the two do not
trace every county line identically, so inside a split county there is
ground today's county line includes that no 2010 piece covers, and 2010 ground
the county line now leaves out. The second is cut away (it belongs to the
neighbouring county's own district). The first is GAP GROUND, and 7A-41(c2)
says what governs it: "If any area within North Carolina is not assigned to a
specific district by subsection (b) of this section, the certified true copy
of the block assignment file ... shall control." That file is delivered to
the two clerks of the General Assembly and this project has not found it
published, so each piece of gap ground goes to the district whose 2010 piece is
nearest, and where one
piece of it touches several districts it is divided between them by nearest
distance (a Voronoi division of points along their edges). The record lists
the gap ground of every county and its largest pieces.

ONE DRAWING PER SPLIT COUNTY, THEN ONE FOR THE STATE. A first draft took the
dividing lines from where two districts' 2010 pieces shared an edge, and two
districts (superior 26G and district 10B) were swallowed by a neighbour,
because the lines stopped short of the county line by less than a metre and
enclosed nothing. So each split county is drawn as one planar arrangement of
its county line, every 2010 piece's outline and the gap divisions, noded on
a 1e-6 degree grid; every face is labelled (outside the county: none; inside
one piece: that piece; inside a gap division: its district; otherwise the
nearest piece), and the dividing lines are exactly the face edges with two
different labels on either side, so they meet the county line and each other
by construction. Each line is simplified on its own with Douglas-Peucker at
TOLERANCE_M, ends fixed, which is the county file's own setting
(`build_state_counties.py`), and then all 100 county lines and every
simplified dividing line are noded again into one arrangement for the state,
whose faces are labelled by county: a whole county's faces take its
district, and a split county's take the district they overlap most. The
build fails if that arrangement has a dangling edge, so a line that stops
short cannot pass again. Each district is the union of its faces, so two
neighbours share their edge coordinate for coordinate.

THE GATES, all run before anything is written (the measured values are in
the record and printed on every run):

  * every district the law names is drawn, and nothing else, with the
    properties the parse gives it;
  * every judge count the law gives twice is compared, and the ones that
    disagree must be exactly JUDGE_DISAGREEMENTS;
  * no segment is used by more than two rings, and the outline's segments
    close (every vertex of even degree);
  * the districts cover the counties' ground: each district is its whole
    counties plus its recorded parts, per split county the drawn parts sum
    to the county, and the state's total area is the counties', all within
    AREA_TOLERANCE. These are measured in square degrees of longitude and
    latitude (`plane()`), not in km2, for the reason in that function;
  * FIDELITY: no 2010 vertex of a split county's dividing lines lies more
    than FIDELITY_MAX_M from its district's drawn line
    (`scripts/boundary_fidelity.py`);
  * POINTS: POINTS_PER_COUNTY random points in each split county land in the
    same district in the drawing as in the 2010 pieces, or lie within
    FIDELITY_MAX_M of a 2010 dividing line;
  * NO PART IS LOST: every piece of a district's 2010 ground has its interior
    point in that district in the drawing. A piece that does not is listed
    with its area and the build fails, because a district part too thin to
    draw is a reader in that ground told another district.

MEASURED ON THE FIRST BUILD, 2026-10-20. Superior court: 73 districts, the
worst 2010 vertex 5.0 m from its drawn line (Guilford, 24B) against the 8 m
ceiling, 17,998 of 18,000 points in the same district and the other 2
within 0.91 m of a 2010 line, no part lost, areas within 1.0e-7. District
court: 47 districts, worst 5.0 m (Wake, 10D), 4,000 of 4,000 points, no
part lost, areas within 2.3e-7. Gap ground was 8.9 km2 across the nine
counties the superior court law divides, in 2,707 pieces of which 11
touched more than one district and were divided, and 0.6 km2 across the two
the district court law divides, in 417 pieces of which 2 were divided; the
largest piece was 1.70 km2 in Cumberland, touching only 14C.

`--check` (stdlib only, in CI) re-parses the kept statutes, re-runs every
cross-check, compares each feature's properties with the parse, re-derives
each district's area from the county file plus the recorded split parts,
re-runs the segment gate, and asks the shipped files which district holds
each recorded interior point (the app's rule: even-odd within a polygon, any
part of a multipolygon), so a feature with the wrong ground or a swapped
label fails. It also fails if the county file changed since the build,
because a whole-county district is that file's ground and has to be
rebuilt with it.

WHAT THE CARDS MAY SAY IS NOT THIS BUILDER'S. They say how judges are chosen
from the North Carolina Judicial Branch's own pages, which this builder does
not read, and name no judge: the branch's judicial directory is closed to
crawlers by its robots.txt, so it is linked and never fetched.

Usage:
    python3 nc/scripts/build_nc_court_districts.py [--cache DIR] [--accept-statutes]
    python3 nc/scripts/build_nc_court_districts.py --check   (offline, stdlib only)
"""

import argparse
import collections
import datetime
import hashlib
import html
import json
import math
import os
import random
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

STATUTES = os.path.join(INSTANCE, "data", "source", "statutes")
APP = os.path.join(INSTANCE, "data", "app")
COUNTIES = os.path.join(APP, "state-counties.json")
RECORD = os.path.join(INSTANCE, "data", "source", "nc-court-districts.source.json")
LAYERS = ("superior", "district")
OUT = {
    "superior": os.path.join(APP, "nc-superior-court-districts.json"),
    "district": os.path.join(APP, "nc-district-court-districts.json"),
}
AUTHORITY = {"superior": "G.S. 7A-41", "district": "G.S. 7A-133"}
EXPECT_DISTRICTS = {"superior": 73, "district": 47}
EXPECT_COUNTIES = 100

STATUTE_URL = ("https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/"
               "Chapter_7A/%s.html")
SECTIONS = ("GS_7A-41", "GS_7A-41.1", "GS_7A-133", "GS_7A-140")

TIGERWEB_2010 = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
                 "tigerWMS_Census2010/MapServer")
VTD_LAYER = 72          # 2010 Census Voting Districts
BLOCK_LAYER = 18        # 2010 Census Blocks
PAGE = 2000
BLOCK_CHUNK = 150
USER_AGENT = "districtry/1.0 (+https://districtry.com/nc/)"
STATE_FIPS = "37"
# The counties either statute divides, with their Census county codes.
SPLIT_FIPS = {
    "New Hanover": "129", "Edgecombe": "065", "Wilson": "195", "Wake": "183",
    "Cumberland": "051", "Durham": "063", "Guilford": "081",
    "Mecklenburg": "119", "Forsyth": "067", "Vance": "181",
}

# --- what the text said when the cards were written (the docstring) --------
# A 12-digit token in a block list is read only through this table.
STATUTE_TYPOS = {"510036004049": "0510036004049"}
# (district, county, voting district) whose block list resumes after "; ".
CONTINUED_LISTS = {("14B", "Cumberland", "G11")}
# district -> (judges in the table of subsection (a), judges in a later paragraph):
# 7A-41(b)(22) for 31A, and 7A-133's residence paragraphs (b1) and (b3), which
# say "all eight" and "all five" judges "established for the District in
# subsection (a)" where that table now gives 11 and 6.
JUDGE_DISAGREEMENTS = {
    "superior": {"31A": (2, 1)},
    "district": {"12": (11, 8), "32": (6, 5)},
}
REPEALED_2029 = {"10E", "31D"}
RESIDENCE = {
    "superior": {"5": "b1"},
    "district": {"12": "b1", "15": "b2", "32": "b3", "33": "b4",
                 "21": "b5", "28": "b6", "36": "b7", "29": "b8"},
}
# G.S. 7A-41.1(a)(2): split districts sharing counties make a set of districts.
EXPECT_SETS = 8
# Sentences the cards and this builder rely on; each must still be in its section.
SENTENCES = {
    "GS_7A-41": (
        "the names and boundaries of voting tabulation districts, tracts, block "
        "groups, and blocks specified in this section are as shown on the 2010 "
        "Census Redistricting TIGER/Line Shapefiles",
        "If any voting tabulation district boundary is changed, that change shall "
        "not change the boundary of a judicial district",
        "If any area within North Carolina is not assigned to a specific district "
        "by subsection (b) of this section, the certified true copy of the block "
        "assignment file",
    ),
    "GS_7A-41.1": (
        "There shall be one and only one senior resident superior court judge for "
        "each district or set of districts",
    ),
    "GS_7A-133": (
        "The names and boundaries of voting tabulation districts specified for "
        "Wake County, and Vance County in this section are as shown on the 2010 "
        "Census Redistricting TIGER/Line Shapefiles.",
    ),
    "GS_7A-140": (
        "Each district judge shall be elected by the qualified voters of the "
        "district court district in which he or she is to serve",
        "Each judge shall be a resident of the district for which elected, and "
        "shall serve a term of four years",
    ),
}

# --- geometry -------------------------------------------------------------
GRID = 1e-6               # the county file's own 6-decimal precision
TOLERANCE_M = 5.0         # Douglas-Peucker, as build_state_counties.py
FIDELITY_MAX_M = 8.0      # as build_state_counties.py
# What the two cards in nc/index.html say about how this builder draws, looked
# for in the module that loads its files (check_card), so a changed ceiling or
# gap rule cannot leave the cards saying the old one.
CARD_CLAIMS = (
    "drawn here to within %g metres of their 2010 lines" % FIDELITY_MAX_M,
    "the map gives it to the nearest district",
)
POINTS_PER_COUNTY = 2000
SEED = 741133
AREA_TOLERANCE = 1e-6     # relative, for every area identity
EARTH_KM = 6371.0088
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
DIVISIONS = ("First", "Second", "Third", "Fourth", "Fifth")
TABLE_HEADERS = ("Superior", "Judicial\tCourt\tNo. of Resident",
                 "Division\tDistrict\tCounties\tJudges")


def fail(msg):
    raise SystemExit("build-nc-court-districts: FAIL — %s" % msg)


def note(msg):
    print("build-nc-court-districts: " + msg)


def unit_key(unit):
    m = re.match(r"^(\d+)([A-Z]?)$", unit)
    if not m:
        fail("%r is not a district number" % unit)
    return (int(m.group(1)), m.group(2))


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rel(path):
    return os.path.relpath(path, REPO)


def check_card():
    """The cards' claims about this builder, looked for in the module of
    nc/index.html that loads its two files: from the module comment above the
    loaders to the next module comment or engine fence. String concatenations
    are joined first, so a claim may be split across source lines."""
    path = os.path.join(INSTANCE, "index.html")
    with open(path, encoding="utf-8") as fh:
        page = fh.read()
    refs = []
    for layer in LAYERS:
        ref = '"data/app/%s"' % os.path.basename(OUT[layer])
        if page.count(ref) != 1:
            fail("%s names %s %d times; the court cards' loader names it once"
                 % (rel(path), ref, page.count(ref)))
        refs.append(page.index(ref))
    start = page.rfind("/* ----------", 0, min(refs))
    ends = [i for i in (page.find("/* ----------", max(refs)),
                        page.find("/* ==== ENGINE:BEGIN", max(refs))) if i >= 0]
    if start < 0 or not ends:
        fail("%s: no module comment around the court cards' loaders" % rel(path))
    module = re.sub(r'"\s*\+\s*"', "", page[start:min(ends)])
    missing = [claim for claim in CARD_CLAIMS if claim not in module]
    if missing:
        fail("the court cards in %s no longer say %s; the cards and this builder must "
             "describe the same drawing" % (rel(path), "; ".join(repr(c) for c in missing)))


# --------------------------------------------------------------------------
# the statutes
# --------------------------------------------------------------------------

def statute_text(raw):
    """A section's HTML page as the tab-separated text this builder parses:
    a table cell ends in a tab, a row or paragraph in a newline. The pages are
    served with Windows line endings, which are read as plain newlines."""
    t = raw.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</div>", "\n", t)
    t = re.sub(r"(?i)</td>", "\t", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)


def statute_path(name):
    return os.path.join(STATUTES, name + ".txt")


def statute_lines(name):
    with open(statute_path(name), encoding="utf-8") as fh:
        return fh.read().split("\n")


def split_counties(text):
    """'Camden, Chowan, Currituck' or 'Lenoir and Greene' -> names."""
    return [c.strip() for c in text.replace(" and ", ", ").split(",") if c.strip()]


def whole_number(field, line):
    value = field.rstrip(".")
    if not value.isdigit():
        fail("the judge count %r in the line %r is not a number" % (field, line))
    return int(value)


def superior_table(lines, marker):
    """The rows of one 7A-41(a) table: division, district, counties, judges."""
    starts = [n for n, l in enumerate(lines) if l.startswith("(a)\t" + marker)]
    if len(starts) != 1:
        fail("G.S. 7A-41 has %d tables headed %r, expected one" % (len(starts), marker))
    rows, cur = [], None
    for line in lines[starts[0] + 1:]:
        if line.startswith("(a)\t") or line.startswith("(b)\t"):
            break
        f = line.split("\t")
        if f[0] in DIVISIONS:
            if len(f) not in (3, 4):
                fail("a G.S. 7A-41 table row has %d fields: %r" % (len(f), line))
            cur = {"division": f[0], "district": f[1], "text": f[2], "judges": None}
            rows.append(cur)
            if len(f) == 4:
                cur["judges"] = whole_number(f[3], line)
        elif cur is not None and f[0] == "" and len(f) in (2, 3):
            cur["text"] += " " + f[1]
            if len(f) == 3:
                if cur["judges"] is not None:
                    fail("two judge counts for District %s: %r" % (cur["district"], line))
                cur["judges"] = whole_number(f[2], line)
        elif line.strip() in TABLE_HEADERS:
            continue
        else:
            fail("a G.S. 7A-41 table line could not be read: %r" % line)
    for r in rows:
        if r["judges"] is None:
            fail("G.S. 7A-41 gives District %s no judge count" % r["district"])
        t = r["text"].strip()
        if t.startswith("("):
            if not t.endswith("see subsection (b))"):
                fail("G.S. 7A-41's row for District %s is not a reference to (b): %r"
                     % (r["district"], t))
            r["partial"] = True
            r["named"] = split_counties(t[1:-len("see subsection (b))")].strip().rstrip(","))
        else:
            r["partial"] = False
            r["counties"] = split_counties(t)
    return rows


COUNTY = re.compile(r"([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)?) County(?: Precincts)?\s*(:|\.|;)")
CODE = re.compile(r"VTD:?\s+([A-Za-z0-9][A-Za-z0-9.\-]*?)(?=[,;:.]\s|[,;:.]?$)")
BLOCKS = re.compile(r":\s*(?:Block\(s\)\s*)?(\d{12,13}(?:,\s*\d{12,13})*)")
MORE_BLOCKS = re.compile(r";\s*(\d{12,13}(?:,\s*\d{12,13})*)")
JUDGES_TAIL = re.compile(r"\.?\s*It has (one|two|three|four) judges?\.?\s*$")


def county_sections(body):
    """'Edgecombe County: ...; Wilson County: ...' -> [(county, text or None)];
    None for a county named whole ('Pender County.')."""
    out = []
    found = list(COUNTY.finditer(body))
    for k, m in enumerate(found):
        end = found[k + 1].start() if k + 1 < len(found) else len(body)
        out.append((m.group(1), body[m.end():end] if m.group(2) == ":" else None))
    return out


def block_list(text, where, seen):
    out = []
    for b in text.split(","):
        b = b.strip()
        if len(b) == 12:
            if b not in STATUTE_TYPOS:
                fail("a 12-digit block number %s in %s is not in STATUTE_TYPOS" % (b, where))
            seen["typos"].append((where, b))
            b = STATUTE_TYPOS[b]
        out.append(b)
    return out


def parse_items(seg, where, seen):
    """'VTD: 1101: Block(s) 065...; VTD: 1201, VTD: 1205: 065...' ->
    [(code, [blocks] or None)], None for a whole voting district."""
    items, pos, n = [], 0, len(seg)
    while True:
        m = MORE_BLOCKS.match(seg, pos)
        if m and items and items[-1][1] is not None:
            # a block list after "; " with no voting district named continues
            # the voting district before it (one place, CONTINUED_LISTS)
            items[-1][1].extend(block_list(m.group(1), where, seen))
            seen["continued"].append(tuple(where.split(" ", 1)) + (items[-1][0],))
            pos = m.end()
            continue
        while pos < n and seg[pos] in " ,;":
            pos += 1
        if pos >= n:
            break
        jm = JUDGES_TAIL.match(seg, pos)
        if jm:
            pos = jm.end()
            break
        if seg[pos] == "." and not seg[pos + 1:].strip():
            pos = n
            break
        m = CODE.match(seg, pos)
        if not m:
            fail("text in %s could not be read at %r" % (where, seg[pos:pos + 80]))
        code, pos = m.group(1), m.end()
        blocks = None
        bm = BLOCKS.match(seg, pos)
        if bm:
            blocks = block_list(bm.group(1), where, seen)
            pos = bm.end()
        items.append((code, blocks))
    if seg[pos:].strip():
        fail("the end of %s could not be read: %r" % (where, seg[pos:pos + 80]))
    return items


SUPERIOR_B = re.compile(r"^\((\d+)\)\t(\(Repealed effective January 1, 2029\) )?"
                        r"(?:Superior Court )?District (\w+)(?::| consists of) (.*)$")


def superior_b(lines, seen):
    """G.S. 7A-41(b): district -> {parts: [(county, items or None)], judges, repealed}."""
    starts = [n for n, l in enumerate(lines) if l.startswith("(b)\tFor superior court districts")]
    if len(starts) != 1:
        fail("G.S. 7A-41 no longer has one subsection (b) for superior court districts")
    out = {}
    for line in lines[starts[0] + 1:]:
        if line.startswith("(b1)"):
            break
        m = SUPERIOR_B.match(line)
        if not m:
            fail("a G.S. 7A-41(b) paragraph could not be read: %r" % line[:100])
        dist, body = m.group(3), m.group(4)
        if dist in out:
            fail("G.S. 7A-41(b) describes District %s twice" % dist)
        jm = re.search(r"It has (one|two|three|four) judges?\.?$", body)
        if not jm:
            fail("G.S. 7A-41(b)'s paragraph for District %s gives no judge count" % dist)
        parts = [(county, None if seg is None else parse_items(seg, dist + " " + county, seen))
                 for county, seg in county_sections(body)]
        if not parts:
            fail("G.S. 7A-41(b)'s paragraph for District %s names no county" % dist)
        out[dist] = {"parts": parts, "judges": WORDS[jm.group(1)],
                     "repealed2029": bool(m.group(2))}
    return out


def district_table(lines):
    """G.S. 7A-133(a): [{district, judges, counties, partial}]."""
    starts = [n for n, l in enumerate(lines) if l.startswith("(a)\tEach district court district")]
    if len(starts) != 1:
        fail("G.S. 7A-133 no longer has one subsection (a) table")
    i = starts[0]
    if lines[i + 1] != "District\tJudges\tCounty":
        fail("G.S. 7A-133's table header is %r" % lines[i + 1])
    rows, cur = [], None
    for line in lines[i + 2:]:
        if line.startswith("(b)\t"):
            break
        m = re.match(r"^(\d{1,2}[A-F]?)\t(\d+)\t(.+)$", line)
        if m:
            cur = {"district": m.group(1), "judges": int(m.group(2)), "lines": [m.group(3)]}
            rows.append(cur)
        elif cur is not None and "\t" not in line and line.strip():
            cur["lines"].append(line.strip())
        else:
            fail("a G.S. 7A-133 table line could not be read: %r" % line)
    pat = r"\(part of ([A-Z][A-Za-z ]+?) see subsection\s+\(b\)\)"
    for r in rows:
        text = "\n".join(r.pop("lines")).rstrip(".")
        r["partial"] = re.findall(pat, text)
        r["counties"] = [c.strip() for c in re.split(r"[,\n]", re.sub(pat, "\n", text))
                         if c.strip()]
    return rows


VANCE_11A = ("District Court District 11A consists of Person, Franklin and Granville "
             "Counties and the remainder of Vance County not in District Court District 11B.")
VANCE_11B = re.compile(r"^District Court District 11B consists of Warren County and "
                       r"(VTD [A-Z0-9]+(?:, VTD [A-Z0-9]+)*) of Vance County\.$")


def district_b(lines, seen):
    """G.S. 7A-133(b): district -> {whole: [...], codes: {county: [...]}, rest: county}."""
    starts = [n for n, l in enumerate(lines) if l.startswith("(b)\tFor district court districts")]
    if len(starts) != 1:
        fail("G.S. 7A-133 no longer has one subsection (b) for district court districts")
    out, vintage = {}, False
    for line in lines[starts[0] + 1:]:
        if line.startswith("(b1)"):
            break
        if line.startswith(SENTENCES["GS_7A-133"][0]):
            vintage = True
            continue
        m = re.match(r"^\((\d+)\)\t(.*)$", line)
        if not m:
            fail("a G.S. 7A-133(b) line could not be read: %r" % line[:100])
        body = m.group(2)
        if body.startswith("Repealed by") or body.startswith("through (18) Repealed"):
            continue
        if body == VANCE_11A:
            out["11A"] = {"whole": ["Person", "Franklin", "Granville"], "codes": {},
                          "rest": ("Vance", "11B")}
            continue
        mm = VANCE_11B.match(body)
        if mm:
            out["11B"] = {"whole": ["Warren"],
                          "codes": {"Vance": [x[4:] for x in mm.group(1).split(", ")]}}
            continue
        mm = re.match(r"^District (10[A-F]): Wake County: (.*)$", body)
        if mm:
            items = parse_items(mm.group(2), mm.group(1) + " Wake", seen)
            if any(b for _, b in items):
                fail("G.S. 7A-133(b) now divides a Wake voting district by blocks")
            out[mm.group(1)] = {"whole": [], "codes": {"Wake": [c for c, _ in items]}}
            continue
        fail("a G.S. 7A-133(b) paragraph is not one this builder knows: %r" % body[:120])
    if not vintage:
        fail("G.S. 7A-133(b) no longer says its voting districts are the 2010 Census's")
    return out


RESIDENCE_RE = re.compile(r"^\((b\d+)\)\t(?:Subject to the provisions of this subsection, )?"
                          r"[Tt]he qualified voters of District (?:Court District )?(\w+) "
                          r"shall elect all (?:(\w+) )?judges established for (?:the District|District \w+) "
                          r"in subsection \(a\) of this section, but only persons who reside in ")


def residence_paragraphs(lines, section):
    """({district: 'bN'}, {district: the count of judges the paragraph names, if
    it names one}) for every (bN) paragraph; any other (bN) fails."""
    out, counts = {}, {}
    for line in lines:
        if not re.match(r"^\(b\d+\)\t", line):
            continue
        m = RESIDENCE_RE.match(line)
        if not m:
            fail("%s has a paragraph %s this builder does not know: %r"
                 % (section, line.split("\t", 1)[0], line[:120]))
        if m.group(2) in out:
            fail("%s has two residence paragraphs for District %s" % (section, m.group(2)))
        out[m.group(2)] = m.group(1)
        if m.group(3):
            if m.group(3) not in WORDS:
                fail("%s(%s) counts its judges as %r" % (section, m.group(1), m.group(3)))
            counts[m.group(2)] = WORDS[m.group(3)]
    return out, counts


def squash(text):
    return re.sub(r"\s+", " ", text)


def union_find(pairs, items):
    parent = {x: x for x in items}

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[root(a)] = root(b)
    groups = collections.defaultdict(list)
    for x in items:
        groups[root(x)].append(x)
    return list(groups.values())


def read_law(fabric_names):
    """Both statutes parsed and cross-checked. Returns
    {"superior": {district: entry}, "district": {district: entry}, "findings": ...}
    where an entry carries whole counties and, per split county, its parts."""
    seen = {"typos": [], "continued": []}
    for name, sentences in SENTENCES.items():
        with open(statute_path(name), encoding="utf-8") as fh:
            text = squash(fh.read())
        for s in sentences:
            if squash(s) not in text:
                fail("%s no longer says: %r" % (name.replace("GS_", "G.S. "), s))
    l41, l133 = statute_lines("GS_7A-41"), statute_lines("GS_7A-133")
    rows = superior_table(l41, "(Effective until January 1, 2029)")
    rows29 = superior_table(l41, "(Effective January 1, 2029)")
    b41 = superior_b(l41, seen)
    drows = district_table(l133)
    b133 = district_b(l133, seen)

    # -- the superior court --------------------------------------------------
    if len(rows) != EXPECT_DISTRICTS["superior"]:
        fail("G.S. 7A-41(a) lists %d districts, expected %d"
             % (len(rows), EXPECT_DISTRICTS["superior"]))
    now = {r["district"]: r for r in rows}
    later = {r["district"]: r for r in rows29}
    if len(now) != len(rows) or len(later) != len(rows29):
        fail("a G.S. 7A-41(a) table lists a district twice")
    if set(now) - set(later) != REPEALED_2029 or set(later) - set(now):
        fail("the 2029 table drops %s and adds %s; the cards and nc/WATCH.md say it drops "
             "%s and adds nothing" % (sorted(set(now) - set(later)), sorted(set(later) - set(now)),
                                      sorted(REPEALED_2029)))
    for d, r in later.items():
        for k in ("division", "judges", "partial", "counties", "named"):
            if r.get(k) != now[d].get(k):
                fail("the 2029 table changes District %s's %s from %r to %r, which nc/WATCH.md "
                     "does not record" % (d, k, now[d].get(k), r.get(k)))
    repealed = {d for d, v in b41.items() if v["repealed2029"]}
    if repealed != REPEALED_2029:
        fail("G.S. 7A-41(b) marks %s repealed in 2029, expected %s"
             % (sorted(repealed), sorted(REPEALED_2029)))
    partial = {d for d, r in now.items() if r["partial"]}
    if partial != set(b41):
        fail("G.S. 7A-41(a) refers to (b) for %s and (b) describes %s"
             % (sorted(partial - set(b41)), sorted(set(b41) - partial)))
    superior, disagree = {}, {}
    for d, r in now.items():
        e = {"division": r["division"], "judges": r["judges"], "whole": [], "parts": {}}
        if r["partial"]:
            named = []
            for county, items in b41[d]["parts"]:
                if items is None:
                    e["whole"].append(county)
                    named.append(county)
                else:
                    if county in e["parts"]:
                        fail("G.S. 7A-41(b) names %s twice in District %s" % (county, d))
                    e["parts"][county] = items
                    named.append("part of " + county)
            if sorted(named) != sorted(r["named"]):
                fail("G.S. 7A-41(a) says District %s is %r and (b) says %r"
                     % (d, r["named"], named))
            if b41[d]["judges"] != r["judges"]:
                disagree[d] = (r["judges"], b41[d]["judges"], "(b)")
            e["repealed2029"] = b41[d]["repealed2029"]
        else:
            e["whole"] = list(r["counties"])
        superior[d] = e
    typos = sorted({b for _, b in seen["typos"]})
    if typos != sorted(STATUTE_TYPOS) or len(seen["typos"]) != len(STATUTE_TYPOS):
        fail("the 12-digit block numbers in the text are %r; STATUTE_TYPOS names %r"
             % (seen["typos"], sorted(STATUTE_TYPOS)))
    if set(seen["continued"]) != CONTINUED_LISTS or len(seen["continued"]) != len(CONTINUED_LISTS):
        fail("block lists continue after a semicolon at %r; CONTINUED_LISTS names %r"
             % (seen["continued"], sorted(CONTINUED_LISTS)))

    # -- the district court --------------------------------------------------
    if len(drows) != EXPECT_DISTRICTS["district"]:
        fail("G.S. 7A-133(a) lists %d districts, expected %d"
             % (len(drows), EXPECT_DISTRICTS["district"]))
    dnow = {r["district"]: r for r in drows}
    if len(dnow) != len(drows):
        fail("G.S. 7A-133(a) lists a district twice")
    dpartial = {d for d, r in dnow.items() if r["partial"]}
    if dpartial != set(b133):
        fail("G.S. 7A-133(a) refers to (b) for %s and (b) describes %s"
             % (sorted(dpartial), sorted(b133)))
    district = {}
    for d, r in dnow.items():
        e = {"judges": r["judges"], "whole": list(r["counties"]), "parts": {}}
        if r["partial"]:
            b = b133[d]
            if sorted(b["whole"]) != sorted(r["counties"]):
                fail("G.S. 7A-133(a) gives District %s the whole counties %r and (b) %r"
                     % (d, r["counties"], b["whole"]))
            split = sorted(set(b["codes"]) | ({b["rest"][0]} if b.get("rest") else set()))
            if split != sorted(r["partial"]):
                fail("G.S. 7A-133(a) splits %r for District %s and (b) %r"
                     % (r["partial"], d, split))
            for county, codes in b["codes"].items():
                e["parts"][county] = {"codes": codes}
            if b.get("rest"):
                e["parts"][b["rest"][0]] = {"rest_of": b["rest"][1]}
        district[d] = e

    # -- both: every county in exactly one district, whole or split ----------
    for layer, table in (("superior", superior), ("district", district)):
        whole = collections.Counter(c for e in table.values() for c in e["whole"])
        split = collections.defaultdict(list)
        for d, e in table.items():
            for c in e["parts"]:
                split[c].append(d)
        law = AUTHORITY[layer]
        unknown = sorted((set(whole) | set(split)) - set(fabric_names))
        if unknown:
            fail("%s names %s, which the county file does not carry" % (law, unknown))
        twice = sorted(c for c, k in whole.items() if k > 1)
        if twice:
            fail("%s puts %s whole in more than one district" % (law, twice))
        both = sorted(set(whole) & set(split))
        if both:
            fail("%s names %s whole and also divides it" % (law, both))
        lone = sorted(c for c, ds in split.items() if len(ds) < 2)
        if lone:
            fail("%s divides %s among fewer than two districts" % (law, lone))
        missing = sorted(set(fabric_names) - set(whole) - set(split))
        if missing:
            fail("%s leaves out %s, so a reader there would be told no court answers"
                 % (law, missing))
        if set(split) - set(SPLIT_FIPS):
            fail("%s divides %s, which SPLIT_FIPS does not carry"
                 % (law, sorted(set(split) - set(SPLIT_FIPS))))

    # -- residence paragraphs, and every count of judges against the tables ----
    res41, count41 = residence_paragraphs(l41, "G.S. 7A-41")
    res133, count133 = residence_paragraphs(l133, "G.S. 7A-133")
    if res41 != RESIDENCE["superior"] or res133 != RESIDENCE["district"]:
        fail("the residence paragraphs are %r and %r; the cards were written for %r"
             % (res41, res133, RESIDENCE))
    ddisagree = {}
    for layer, table, counts, res, found in (("superior", superior, count41, res41, disagree),
                                             ("district", district, count133, res133, ddisagree)):
        for d, n in counts.items():
            if d not in table:
                fail("%s(%s) names District %s, which its table does not"
                     % (AUTHORITY[layer], res[d], d))
            if n != table[d]["judges"]:
                if d in found:
                    fail("%s gives District %s three different counts of judges"
                         % (AUTHORITY[layer], d))
                found[d] = (table[d]["judges"], n, "(%s)" % res[d])
    for layer, found in (("superior", disagree), ("district", ddisagree)):
        got = {d: (t, p) for d, (t, p, _) in found.items()}
        if got != JUDGE_DISAGREEMENTS[layer]:
            fail("%s gives two counts of judges for %r; the cards were written for %r"
                 % (AUTHORITY[layer], got, JUDGE_DISAGREEMENTS[layer]))
    pairs = [(ds[0], d) for c in SPLIT_FIPS
             for ds in [[d for d, e in superior.items() if c in e["parts"]]] if ds
             for d in ds[1:]]
    sets = [sorted(g, key=unit_key) for g in union_find(
        pairs, [d for d, e in superior.items() if e["parts"]])]
    if len(sets) != EXPECT_SETS:
        fail("the split superior court districts make %d sets of districts (G.S. 7A-41.1), "
             "expected %d" % (len(sets), EXPECT_SETS))
    set_of = {}
    for members in sets:
        counties = sorted({c for d in members for c in superior[d]["whole"]}
                          | {c for d in members for c in superior[d]["parts"]})
        for d in members:
            set_of[d] = (members, counties)
    return {"superior": superior, "district": district, "sets": set_of,
            "findings": {
                "statuteTypos": [{"where": w, "printed": b, "readAs": STATUTE_TYPOS[b]}
                                 for w, b in seen["typos"]],
                "continuedLists": sorted([list(x) for x in seen["continued"]]),
                "judgeCountsDisagree": {
                    layer: {d: {"table": t, "paragraph": p, "where": "%s%s" % (AUTHORITY[layer], w)}
                            for d, (t, p, w) in found.items()}
                    for layer, found in (("superior", disagree), ("district", ddisagree))},
                "repealedOn20290101": sorted(REPEALED_2029, key=unit_key),
                "residence": {"superior": res41, "district": res133},
                "setsOfDistricts": sorted([m for m in sets], key=lambda m: unit_key(m[0])),
            }}


def expected_properties(law, layer):
    """{district: the properties its feature must carry}."""
    out = {}
    for d, e in law[layer].items():
        # `judgeCount`, not `judges`: the fleet's checks read a property named
        # `judges` on a boundary feature as a list of people (as South Carolina's
        # `judge_count` records), and this one is a number.
        props = {"unit": d, "counties": sorted(e["whole"]), "parts": sorted(e["parts"]),
                 "judgeCount": e["judges"], "authority": AUTHORITY[layer]}
        if d in JUDGE_DISAGREEMENTS[layer]:
            props["judgeCount"] = None
            props["judgesDisagree"] = list(JUDGE_DISAGREEMENTS[layer][d])
            props["judgesDisagreeIn"] = law["findings"]["judgeCountsDisagree"][layer][d]["where"]
        if layer == "superior":
            props["division"] = e["division"]
            if d in law["sets"]:
                members, counties = law["sets"][d]
                props["set"] = members
                props["setCounties"] = counties
            if e.get("repealed2029"):
                props["endsOn"] = "2029-01-01"
        if d in RESIDENCE[layer]:
            props["residence"] = "%s(%s)" % (AUTHORITY[layer], RESIDENCE[layer][d])
        out[d] = props
    return out


def whole_map(law, layer):
    return {c: d for d, e in law[layer].items() for c in e["whole"]}


# --------------------------------------------------------------------------
# stdlib geometry: areas, rings, point in polygon, the segment gate
# --------------------------------------------------------------------------

def rings_of(geometry):
    kind = geometry.get("type")
    if kind == "Polygon":
        return list(geometry["coordinates"])
    if kind == "MultiPolygon":
        return [r for part in geometry["coordinates"] for r in part]
    fail("unexpected geometry type %r" % kind)


def ring_area_km2(ring):
    """Signed spherical area of one ring."""
    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return total * EARTH_KM * EARTH_KM / 2.0


def measure(geometry):
    """km2, each polygon's holes subtracted. For reading, not for the identities."""
    polys = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
             else geometry["coordinates"])
    total = 0.0
    for poly in polys:
        total += abs(ring_area_km2(poly[0])) - sum(abs(ring_area_km2(h)) for h in poly[1:])
    return total


def ring_area_deg2(ring):
    total = 0.0
    for (x1, y1), (x2, y2) in zip([c[:2] for c in ring], [c[:2] for c in ring[1:]]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def plane(geometry):
    """Area in square degrees of longitude and latitude, holes subtracted.

    THE AREA IDENTITIES ARE MEASURED HERE AND NOT IN KM2, because the spherical
    formula above treats an edge as straight in longitude and the sine of
    latitude, so a vertex inserted part-way along a long straight edge changes
    its answer. The drawing does insert them: where a dividing line meets a
    county line, the meeting point becomes a vertex of both neighbours. Measured
    on the first full run, Nash County's 10 km straight line with Edgecombe gave
    District 8A 2,374 m2 less in km2 than Nash County alone, a relative 1.69e-6,
    while the ground was the same to 1.1e-8 square degrees. In the plane of
    longitude and latitude a straight edge stays straight, which is also how the
    app's own point test reads an edge, so an inserted vertex changes nothing."""
    polys = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
             else geometry["coordinates"])
    total = 0.0
    for poly in polys:
        total += abs(ring_area_deg2(poly[0])) - sum(abs(ring_area_deg2(h)) for h in poly[1:])
    return total


def ring_contains(ring, x, y):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def geometry_contains(geometry, x, y):
    """The app's rule: even-odd within a polygon, any part of a multipolygon."""
    polys = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
             else geometry["coordinates"])
    for poly in polys:
        inside = False
        for ring in poly:
            if ring_contains(ring, x, y):
                inside = not inside
        if inside:
            return True
    return False


def segment_gate(features):
    """(segments, [segments in 3+ rings], [outline segments], [odd-degree vertices])."""
    segs = collections.Counter()
    for f in features:
        for ring in rings_of(f["geometry"]):
            for a, b in zip(ring, ring[1:]):
                a, b = (a[0], a[1]), (b[0], b[1])
                if a != b:
                    segs[(a, b) if a < b else (b, a)] += 1
    over = [s for s, k in segs.items() if k > 2]
    once = [s for s, k in segs.items() if k == 1]
    degree = collections.Counter()
    for a, b in once:
        degree[a] += 1
        degree[b] += 1
    odd = [v for v, k in degree.items() if k % 2]
    return len(segs), over, once, odd


def load_fabric():
    with open(COUNTIES, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    out = {}
    for f in feats:
        name = (f.get("properties") or {}).get("BASENAME")
        if not name:
            fail("a county feature carries no BASENAME")
        if name in out:
            fail("%s appears twice in the county file" % name)
        out[name] = f["geometry"]
    if len(out) != EXPECT_COUNTIES:
        fail("the county file carries %d counties, expected %d" % (len(out), EXPECT_COUNTIES))
    return out


def verify(law, layer, features, rec_layer, county_points, fabric):
    """Everything --check asks of one shipped layer, run on the build's own
    output before it is written. Returns a summary for the OK line."""
    label = AUTHORITY[layer]
    expected = expected_properties(law, layer)
    by = {}
    for f in features:
        unit = (f.get("properties") or {}).get("unit")
        if unit in by:
            fail("%s ships District %s twice" % (label, unit))
        by[unit] = f
    if set(by) != set(expected):
        fail("%s ships %s and the law names %s" % (label, sorted(set(by) - set(expected)),
                                                  sorted(set(expected) - set(by))))
    for unit, props in expected.items():
        if by[unit]["properties"] != props:
            fail("%s District %s ships %r; the law gives %r"
                 % (label, unit, by[unit]["properties"], props))
    parts = rec_layer["parts"]
    want_keys = {"%s|%s" % (c, u) for u, p in expected.items() for c in p["parts"]}
    if set(parts) != want_keys:
        fail("the record's %s parts are %s; the law divides %s"
             % (label, sorted(set(parts) ^ want_keys), sorted(want_keys)))
    area = {c: plane(g) for c, g in fabric.items()}
    worst, worst_at = 0.0, None
    for unit, props in expected.items():
        want = (sum(area[c] for c in props["counties"])
                + sum(parts["%s|%s" % (c, unit)]["deg2"] for c in props["parts"]))
        got = plane(by[unit]["geometry"])
        if abs(got - want) / want > worst:
            worst, worst_at = abs(got - want) / want, unit
    if worst > AREA_TOLERANCE:
        fail("%s District %s's area differs from its counties' and recorded parts' by %.2e "
             "of its area" % (label, worst_at, worst))
    per_county = collections.defaultdict(float)
    for key, v in parts.items():
        per_county[key.split("|")[0]] += v["deg2"]
    for c, total in per_county.items():
        if abs(total - area[c]) / area[c] > AREA_TOLERANCE:
            fail("%s's %s parts add up to %.3e of its area more or less than the county"
                 % (c, label, (total - area[c]) / area[c]))
    drawn = sum(plane(f["geometry"]) for f in features)
    state = sum(area.values())
    if abs(drawn - state) / state > AREA_TOLERANCE:
        fail("the %s districts cover %.3e of the state more or less than the counties"
             % (label, (drawn - state) / state))
    nsegs, over, once, odd = segment_gate(features)
    if over:
        fail("%d %s segment(s) are used by more than two rings, first %r"
             % (len(over), label, over[0]))
    if odd:
        fail("the %s outline does not close: %d vertex/vertices of odd degree, first %r"
             % (label, len(odd), odd[0]))
    points = 0
    for key, v in sorted(parts.items()):
        county, unit = key.split("|")
        hits = [u for u, f in by.items() if geometry_contains(f["geometry"], *v["point"])]
        if hits != [unit]:
            fail("the recorded point inside %s's part of %s District %s lies in %r"
                 % (county, label, unit, hits))
        points += 1
    wm = whole_map(law, layer)
    for county, unit in sorted(wm.items()):
        hits = [u for u, f in by.items()
                if geometry_contains(f["geometry"], *county_points[county])]
        if hits != [unit]:
            fail("the recorded point inside %s County lies in %s districts %r, expected %s"
                 % (county, label, hits, unit))
        points += 1
    return {"districts": len(by), "segments": nsegs, "outline": len(once), "area": worst,
            "points": points}


# --------------------------------------------------------------------------
# --check
# --------------------------------------------------------------------------

def check():
    check_card()
    fabric = load_fabric()
    law = read_law(fabric)
    if not os.path.exists(RECORD):
        fail("%s is missing. Run this builder without --check." % rel(RECORD))
    with open(RECORD, encoding="utf-8") as fh:
        rec = json.load(fh)
    for name in SECTIONS:
        if sha256(statute_path(name)) != rec["statutes"][name]["sha256"]:
            fail("%s changed since the build; rebuild, which also holds it to the live page"
                 % rel(statute_path(name)))
    if sha256(COUNTIES) != rec["countyFile"]["sha256"]:
        fail("%s changed since the court districts were built from it; rebuild them, because a "
             "whole-county district is that file's ground" % rel(COUNTIES))
    for layer in LAYERS:
        if not os.path.exists(OUT[layer]):
            fail("%s is missing. Run this builder without --check." % rel(OUT[layer]))
        with open(OUT[layer], encoding="utf-8") as fh:
            features = json.load(fh)["features"]
        st = verify(law, layer, features, rec["layers"][layer], rec["countyPoints"], fabric)
        note("%s — %s: %d districts as the law names them, %d interior points each in its "
             "own district only, areas within %.1e of the counties' and recorded parts', no "
             "segment in three rings and an outline that closes"
             % (rel(OUT[layer]), AUTHORITY[layer], st["districts"], st["points"], st["area"]))
    note("OK — both statutes parse and cross-check, the kept text and the county file are the "
         "ones the build read, and the cards say how the districts are drawn")


# --------------------------------------------------------------------------
# fetching: robots.txt read for every host and every redirect hop
# --------------------------------------------------------------------------

def connect():
    import requests  # noqa: PLC0415
    from robots_gate import HostPacer, RobotsGate  # noqa: PLC0415
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    gate = RobotsGate(session, USER_AGENT)
    return session, gate, HostPacer(gate)


def http(net, url, data=None, timeout=180):
    import requests  # noqa: PLC0415
    session, gate, pacer = net
    for _hop in range(6):
        ok, why = gate.allows(url)
        if not ok:
            fail("robots.txt refuses %s: %s" % (url, why))
        last = None
        for attempt in range(4):
            try:
                with pacer.hold(url):
                    if data is None:
                        resp = session.get(url, timeout=timeout, allow_redirects=False)
                    else:
                        resp = session.post(url, data=data, timeout=timeout,
                                            allow_redirects=False)
                break
            except requests.RequestException as exc:
                last = exc
                time.sleep(3 * (attempt + 1))
        else:
            fail("%s could not be read: %s" % (url, last))
        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
            if data is not None:
                fail("a query to %s was redirected" % url)
            url = requests.compat.urljoin(url, resp.headers["Location"])
            continue
        if resp.status_code != 200:
            fail("%s answered HTTP %d" % (url, resp.status_code))
        return resp
    fail("%s redirected more than five times" % url)


def fetch_statutes(net, accept):
    """Each section's live page, converted, against the kept copy."""
    for name in SECTIONS:
        url = STATUTE_URL % name
        live = statute_text(http(net, url, timeout=90).content.decode("utf-8", "replace"))
        with open(statute_path(name), encoding="utf-8") as fh:
            kept = fh.read()
        if live == kept:
            continue
        if not accept:
            a, b = kept.split("\n"), live.split("\n")
            first = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]),
                         min(len(a), len(b)))
            fail("the live text of %s differs from %s from line %d: kept %r, live %r. Read the "
                 "change, then run with --accept-statutes."
                 % (name.replace("GS_", "G.S. "), rel(statute_path(name)), first + 1,
                    a[first][:120] if first < len(a) else None,
                    b[first][:120] if first < len(b) else None))
        with open(statute_path(name), "w", encoding="utf-8") as fh:
            fh.write(live)
        note("replaced %s with the live text, as --accept-statutes asks" % rel(statute_path(name)))


def tiger(net, layer, where, fields):
    url = "%s/%d/query" % (TIGERWEB_2010, layer)
    out, offset = [], 0
    while True:
        data = {"where": where, "outFields": fields, "outSR": "4326", "geometryPrecision": "6",
                "f": "geojson", "resultOffset": offset, "resultRecordCount": PAGE,
                "orderByFields": "OBJECTID"}
        body = http(net, url, data=data).json()
        if "error" in body:
            fail("TIGERweb layer %d answered an error for %r: %r" % (layer, where, body["error"]))
        feats = body.get("features")
        if feats is None:
            fail("TIGERweb layer %d answered no features list for %r" % (layer, where))
        out += feats
        if not feats or (len(feats) < PAGE and not body.get("exceededTransferLimit")):
            return out
        offset += len(feats)


def cached(cache, name, fetch, good):
    path = os.path.join(cache, name) if cache else None
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            feats = json.load(fh)["features"]
        if good(feats):
            return feats
        note("the cached %s does not hold what this build needs; fetching it again" % name)
    feats = fetch()
    if path:
        os.makedirs(cache, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"type": "FeatureCollection", "features": feats}, fh)
    return feats


def census2010(net, law, cache):
    """{county: {code: feature}} for the split counties' 2010 voting districts, and
    {13-digit block: feature} for every block the superior court statute lists."""
    vtds = {}
    for county, fips in sorted(SPLIT_FIPS.items()):
        feats = cached(
            cache, "vtd2010_%s.json" % fips,
            lambda fips=fips: tiger(net, VTD_LAYER, "STATE='%s' AND COUNTY='%s'"
                                    % (STATE_FIPS, fips), "GEOID,STATE,COUNTY,VTD,NAME"),
            lambda feats: bool(feats))
        by = {}
        for f in feats:
            p = f["properties"]
            if p.get("STATE") != STATE_FIPS or p.get("COUNTY") != fips:
                fail("a 2010 voting district of %s County is in state %r county %r"
                     % (county, p.get("STATE"), p.get("COUNTY")))
            if p["VTD"] in by:
                fail("the 2010 voting district %s of %s County comes back twice"
                     % (p["VTD"], county))
            by[p["VTD"]] = f
        vtds[county] = by
    need = sorted({STATE_FIPS + b for e in law["superior"].values()
                   for items in e["parts"].values() for _, bl in items if bl for b in bl})

    def fetch_blocks():
        feats = []
        for i in range(0, len(need), BLOCK_CHUNK):
            chunk = need[i:i + BLOCK_CHUNK]
            feats += tiger(net, BLOCK_LAYER, "GEOID IN (%s)" % ",".join("'%s'" % x for x in chunk),
                           "GEOID,STATE,COUNTY,TRACT,BLOCK")
        return feats

    feats = cached(cache, "blocks2010.json", fetch_blocks,
                   lambda feats: sorted(f["properties"]["GEOID"] for f in feats) == need)
    blocks = {}
    for f in feats:
        geoid = f["properties"]["GEOID"]
        if geoid in blocks:
            fail("the 2010 block %s comes back twice" % geoid)
        blocks[geoid[2:]] = f
    missing = sorted(set(b[2:] for b in need) - set(blocks))
    if missing:
        fail("%d block(s) the statute lists are not in the 2010 Census, first %s"
             % (len(missing), missing[0]))
    return vtds, blocks


# --------------------------------------------------------------------------
# the 2010 pieces of each split county
# --------------------------------------------------------------------------

def assignments(law, layer, vtds):
    """{county: {code: [(district, [blocks] or None)]}}, every 2010 voting district
    of every split county assigned, each exactly once whole or by blocks."""
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    rest = []
    for d, e in law[layer].items():
        for county, spec in e["parts"].items():
            if layer == "superior":
                for code, blocks in spec:
                    out[county][code].append((d, blocks))
            elif "codes" in spec:
                for code in spec["codes"]:
                    out[county][code].append((d, None))
            else:
                rest.append((county, d, spec["rest_of"]))
    for county, d, other in rest:
        listed = set(law[layer][other]["parts"][county]["codes"])
        for code in vtds[county]:
            if code not in listed:
                out[county][code].append((d, None))
    for county, assign in out.items():
        have, listed = set(vtds[county]), set(assign)
        if listed - have:
            fail("%s names %s County voting districts %s that the 2010 Census does not have"
                 % (AUTHORITY[layer], county, sorted(listed - have)))
        if have - listed:
            fail("%s leaves %s County's 2010 voting districts %s in no district"
                 % (AUTHORITY[layer], county, sorted(have - listed)))
        for code, a in assign.items():
            whole = [d for d, b in a if b is None]
            part = [d for d, b in a if b is not None]
            if whole and (len(whole) > 1 or part):
                fail("%s puts %s voting district %s in %r" % (AUTHORITY[layer], county, code, a))
            if part and len(set(part)) < 2:
                fail("%s divides %s voting district %s by blocks into one district only"
                     % (AUTHORITY[layer], county, code))
            if part:
                listed_blocks = collections.Counter(x for _, b in a if b for x in b)
                twice = sorted(x for x, k in listed_blocks.items() if k > 1)
                if twice:
                    fail("%s lists %s block(s) %s twice" % (AUTHORITY[layer], county, twice))
    return out


# --------------------------------------------------------------------------
# geometry (shapely, build only)
# --------------------------------------------------------------------------

def geo():
    try:
        import shapely  # noqa: PLC0415
        from shapely import STRtree  # noqa: PLC0415
        from shapely.geometry import (LineString, MultiLineString, MultiPoint,  # noqa: PLC0415
                                      Point, Polygon, mapping, shape)
    except ImportError:
        fail("the build path needs shapely (pip install -c scripts/requirements.txt shapely); "
             "--check is stdlib only")
    return (shapely, STRtree, LineString, MultiLineString, MultiPoint, Point, Polygon,
            mapping, shape)


def mscale(lat):
    return 111320.0 * math.cos(math.radians(lat)), 110540.0


class Geometry(object):
    """The shapely half of the build, in one place."""

    def __init__(self):
        (self.sh, self.STRtree, self.LineString, self.MultiLineString, self.MultiPoint,
         self.Point, self.Polygon, self.mapping, self.shape) = geo()

    # -- small helpers ------------------------------------------------------
    def polys(self, g):
        out = []
        for x in getattr(g, "geoms", [g]):
            if x.is_empty:
                continue
            if x.geom_type == "Polygon":
                out.append(x)
            elif x.geom_type in ("MultiPolygon", "GeometryCollection"):
                out.extend(self.polys(x))
        return out

    def areal(self, g):
        ps = self.polys(g)
        if not ps:
            return self.Polygon()
        return self.sh.union_all(ps, grid_size=GRID) if len(ps) > 1 else ps[0]

    def km2(self, g):
        total = 0.0
        for p in self.polys(g):
            total += abs(ring_area_km2(list(p.exterior.coords)))
            total -= sum(abs(ring_area_km2(list(h.coords))) for h in p.interiors)
        return total

    def m2(self, g):
        return self.km2(g) * 1e6

    @staticmethod
    def xy(p):
        return [round(p.x, 6), round(p.y, 6)]

    def inner_point(self, g):
        ps = self.polys(g)
        return max(ps, key=lambda p: p.area).representative_point()

    def to_metres(self, g, lat):
        sx, sy = mscale(lat)
        return self.sh.transform(g, lambda c: c * [sx, sy])

    def valid(self, geometry):
        return self.areal(self.sh.make_valid(self.shape(geometry)))

    # -- 2010 pieces ---------------------------------------------------------
    def pieces(self, county, assign, vtds, blocks):
        """{district: 2010 ground in this county}, and the split voting districts'
        blocks measured against their voting district."""
        out = collections.defaultdict(list)
        remainders, excess = [], []
        fips = SPLIT_FIPS[county]
        for code, a in sorted(assign.items()):
            poly = self.valid(vtds[county][code]["geometry"])
            if a[0][1] is None:
                out[a[0][0]].append(poly)
                continue
            zone = poly.buffer(1e-7)
            got = {}
            for d, bl in a:
                geoms = []
                for b in bl:
                    if b[:3] != fips:
                        fail("block %s listed in %s County is in county %s" % (b, county, b[:3]))
                    g = self.valid(blocks[b]["geometry"])
                    if not zone.contains(g.representative_point()):
                        fail("block %s is listed in %s voting district %s and lies outside it"
                             % (b, county, code))
                    geoms.append(g)
                got[d] = self.sh.union_all(geoms, grid_size=GRID)
            cover = self.sh.union_all(list(got.values()), grid_size=GRID)
            rest = self.areal(self.sh.difference(poly, cover, grid_size=GRID))
            over = self.areal(self.sh.difference(cover, poly, grid_size=GRID))
            if not rest.is_empty and self.m2(rest) > 0.01:
                remainders.append([code, round(self.m2(rest), 2)])
            if not over.is_empty and self.m2(over) > 0.01:
                excess.append([code, round(self.m2(over), 2)])
            for d, g in got.items():
                out[d].append(g)
        merged = {d: self.areal(self.sh.union_all(gs, grid_size=GRID)) for d, gs in out.items()}
        return merged, {"blockRemainderM2": remainders, "blocksOutsideM2": excess}

    # -- one arrangement per split county ------------------------------------
    def voronoi_parts(self, X, touching):
        """X divided among the pieces it touches, each spot to the nearest piece edge."""
        sh = self.sh
        zone = X.buffer(2e-5)
        seen = collections.defaultdict(set)
        for d, P in touching.items():
            edge = sh.intersection(P.boundary, zone)
            if edge.is_empty:
                continue
            for c in sh.get_coordinates(sh.segmentize(edge, 1e-5)):
                seen[(round(c[0], 7), round(c[1], 7))].add(d)
        keyed = sorted((xy, next(iter(ds))) for xy, ds in seen.items() if len(ds) == 1)
        if len({d for _, d in keyed}) < 2:
            return {}
        vor = sh.voronoi_polygons(self.MultiPoint([self.Point(xy) for xy, _ in keyed]),
                                  extend_to=X.envelope.buffer(1e-3), ordered=True)
        cells = collections.defaultdict(list)
        for cell, (_, d) in zip(vor.geoms, keyed):
            cells[d].append(cell)
        return {d: self.areal(sh.intersection(X, sh.union_all(cs, grid_size=GRID),
                                              grid_size=GRID))
                for d, cs in cells.items()}

    @staticmethod
    def ring_segments(poly):
        for ring in [poly.exterior] + list(poly.interiors):
            cs = [(round(x, 6), round(y, 6)) for x, y in ring.coords]
            for a, b in zip(cs, cs[1:]):
                if a != b:
                    yield (a, b) if a < b else (b, a)

    def county_truth(self, county, C, pieces):
        """The county divided by its 2010 pieces, gap ground given to the nearest:
        ({district: ground}, [dividing lines], stats)."""
        sh = self.sh
        clipped = {d: self.areal(sh.intersection(P, C, grid_size=GRID))
                   for d, P in pieces.items()}
        covered = sh.union_all(list(clipped.values()), grid_size=GRID)
        gap = self.areal(sh.difference(C, covered, grid_size=GRID))
        outside = self.areal(sh.difference(sh.union_all(list(pieces.values()), grid_size=GRID),
                                           C, grid_size=GRID))
        lines = [C.boundary] + [P.boundary for P in pieces.values()]
        vparts, gaps, divided = [], [], 0
        for X in self.polys(gap):
            touch = sorted(d for d, P in clipped.items() if X.buffer(1e-7).intersects(P))
            parts = {}
            if len(touch) > 1:
                parts = self.voronoi_parts(X, {d: clipped[d] for d in touch})
                if parts:
                    divided += 1
                for d, part in sorted(parts.items()):
                    if not part.is_empty:
                        vparts.append((part.buffer(1e-8), d))
                        lines.append(part.boundary)
            gaps.append((self.m2(X), X, touch, sorted(parts)))
        noded = sh.union_all(lines, grid_size=GRID)
        faces, cuts, dangles, invalid = sh.polygonize_full(list(getattr(noded, "geoms", [noded])))
        names = sorted(pieces)
        tree = self.STRtree([pieces[d] for d in names])
        labels, overlap_m2, overlap_n = [], 0.0, 0
        faces = list(faces.geoms)
        for f in faces:
            rp = f.representative_point()
            if not C.contains(rp):
                labels.append(None)
                continue
            hit = sorted(names[i] for i in tree.query(rp, predicate="within"))
            if len(hit) > 1:
                overlap_n += 1
                overlap_m2 += self.m2(f)
            if hit:
                labels.append(hit[0])
                continue
            vp = [d for part, d in vparts if part.contains(rp)]
            if vp:
                labels.append(vp[0])
                continue
            labels.append(min(names, key=lambda d: pieces[d].distance(f)))
        owner = collections.defaultdict(list)
        for f, lab in zip(faces, labels):
            if lab is None:
                continue
            for p in self.polys(f):
                for s in self.ring_segments(p):
                    owner[s].append(lab)
        three = [s for s, labs in owner.items() if len(labs) > 2]
        if three:
            fail("%s: %d segment(s) of the 2010 drawing are shared by three faces, first %r"
                 % (county, len(three), three[0]))
        interior = [s for s, labs in owner.items() if len(labs) == 2 and labs[0] != labs[1]]
        by = collections.defaultdict(list)
        for f, lab in zip(faces, labels):
            if lab is not None:
                by[lab].append(f)
        truth = {d: self.areal(sh.union_all(fs, grid_size=GRID)) for d, fs in by.items()}
        if set(truth) != set(pieces):
            fail("%s: the 2010 drawing has districts %s and the pieces %s"
                 % (county, sorted(truth), sorted(pieces)))
        merged = sh.line_merge(self.MultiLineString([list(s) for s in interior]))
        arcs = [g for g in getattr(merged, "geoms", [merged]) if g.geom_type == "LineString"]
        resid = self.m2(self.areal(sh.symmetric_difference(
            sh.union_all(list(truth.values()), grid_size=GRID), C, grid_size=GRID)))
        gaps.sort(key=lambda g: -g[0])
        stats = {
            "faces": len(faces),
            "gapM2": round(sum(g[0] for g in gaps), 1),
            "gapPieces": len(gaps),
            "gapPiecesDivided": divided,
            "gapLargest": [{"m2": round(a), "at": self.xy(X.representative_point()),
                            "touches": t, "dividedAmong": dv}
                           for a, X, t, dv in gaps[:3]],
            "outsideCountyM2": round(self.m2(outside), 1),
            "overlapFaces": overlap_n,
            "overlapM2": round(overlap_m2, 3),
            "dividingLines": len(arcs),
            "residualM2": round(resid, 3),
            "cuts": len(getattr(cuts, "geoms", [])),
            "dangles": len(getattr(dangles, "geoms", [])),
            "invalidRings": len(getattr(invalid, "geoms", [])),
        }
        return truth, arcs, stats


def dp(coords, tol_m):
    """Douglas-Peucker on one open line, ends kept, distances in metres."""
    n = len(coords)
    if n <= 2:
        return list(coords)
    sx, sy = mscale(coords[0][1])
    P = [(c[0] * sx, c[1] * sy) for c in coords]
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = P[a]
        bx, by = P[b]
        dx, dy = bx - ax, by - ay
        d2 = dx * dx + dy * dy
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            px, py = P[i]
            if d2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = ((px - ax) * dx + (py - ay) * dy) / d2
                t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > best:
                best, bi = d, i
        if bi >= 0 and best > tol_m:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [coords[i] for i in range(n) if keep[i]]


def farthest_from_chord(coords):
    """Index of the interior vertex farthest from the chord between the ends."""
    sx, sy = mscale(coords[0][1])
    ax, ay = coords[0][0] * sx, coords[0][1] * sy
    bx, by = coords[-1][0] * sx, coords[-1][1] * sy
    best, bi = -1.0, None
    for i in range(1, len(coords) - 1):
        px, py = coords[i][0] * sx, coords[i][1] * sy
        d = abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / max(math.hypot(bx - ax, by - ay), 1e-9)
        if d > best:
            best, bi = d, i
    return bi


def simplify_line(coords, tol_m):
    """One dividing line simplified with its ends fixed. A closed line (a district
    wholly inside another) is split at the vertex farthest from its start, and keeps
    at least a triangle."""
    coords = [tuple(c) for c in coords]
    if coords[0] != coords[-1]:
        return dp(coords, tol_m)
    sx, sy = mscale(coords[0][1])
    far = max(range(len(coords) - 1),
              key=lambda i: math.hypot((coords[i][0] - coords[0][0]) * sx,
                                       (coords[i][1] - coords[0][1]) * sy))
    halves = []
    for half in (coords[:far + 1], coords[far:]):
        kept = dp(half, tol_m)
        if len(kept) == 2 and len(half) > 2:
            kept = [half[0], half[farthest_from_chord(half)], half[-1]]
        halves.append(kept)
    return halves[0] + halves[1][1:]


# --------------------------------------------------------------------------
# the build
# --------------------------------------------------------------------------

def build_layer(G, law, layer, assigns, vtds, blocks, fabric_shapes, rng):
    sh = G.sh
    wm = whole_map(law, layer)
    split = sorted(assigns)
    truth, raw_arcs, simplified, per_county = {}, {}, [], {}
    nraw = nsimp = 0
    t0 = time.time()
    for county in split:
        pieces, pst = G.pieces(county, assigns[county], vtds, blocks)
        T, arcs, st = G.county_truth(county, fabric_shapes[county], pieces)
        truth[county], raw_arcs[county] = T, arcs
        st.update(pst)
        for a in arcs:
            kept = simplify_line(list(a.coords), TOLERANCE_M)
            nraw += len(a.coords)
            nsimp += len(kept)
            simplified.append(G.LineString(kept))
        per_county[county] = st
        note("  %s %s: %d districts, %d faces, gap %.0f m2 in %d piece(s) (%d divided), "
             "%d dividing line(s), %.1fs" % (AUTHORITY[layer], county, len(T), st["faces"],
                                            st["gapM2"], st["gapPieces"], st["gapPiecesDivided"],
                                            st["dividingLines"], time.time() - t0))
    lines = [fabric_shapes[c].boundary for c in sorted(fabric_shapes)] + simplified
    noded = sh.union_all(lines, grid_size=GRID)
    faces, cuts, dangles, invalid = sh.polygonize_full(list(getattr(noded, "geoms", [noded])))
    if not dangles.is_empty:
        d0 = list(dangles.geoms)[0]
        fail("%s: the state drawing has %d dangling edge(s), first near %r; a dividing line "
             "stops short of the line it should meet" % (AUTHORITY[layer], len(dangles.geoms),
                                                         G.xy(d0.interpolate(0.5, True))))
    if not invalid.is_empty:
        fail("%s: the state drawing has %d invalid ring(s)" % (AUTHORITY[layer],
                                                             len(invalid.geoms)))
    names = sorted(fabric_shapes)
    tree = G.STRtree([fabric_shapes[n] for n in names])
    faces = list(faces.geoms)
    by_district = collections.defaultdict(list)
    by_part = collections.defaultdict(list)
    weakest = (1.0, None)
    for f in faces:
        rp = f.representative_point()
        hit = [names[i] for i in tree.query(rp, predicate="within")]
        if len(hit) != 1:
            fail("%s: a face of the state drawing at %r lies in counties %r"
                 % (AUTHORITY[layer], G.xy(rp), hit))
        c = hit[0]
        if c in wm:
            by_district[wm[c]].append(f)
            continue
        ov = {d: f.intersection(T).area for d, T in truth[c].items()}
        d = max(sorted(ov), key=lambda k: ov[k])
        share = ov[d] / f.area if f.area else 0.0
        if share < weakest[0]:
            weakest = (share, (c, d, G.xy(rp), round(G.m2(f), 1)))
        by_district[d].append(f)
        by_part[(c, d)].append(f)
    expected = expected_properties(law, layer)
    missing = sorted(set(expected) - set(by_district), key=unit_key)
    if missing:
        fail("%s: no ground is drawn for District(s) %s" % (AUTHORITY[layer], missing))
    drawn_parts = {k: G.areal(sh.union_all(fs, grid_size=GRID)) for k, fs in by_part.items()}

    # -- fidelity, points and lost parts, per split county ----------------
    tfeats, dfeats = [], []
    for c in split:
        for d, T in truth[c].items():
            tfeats.append({"properties": {"key": "%s|%s" % (c, d)}, "geometry": G.mapping(T)})
            if (c, d) in drawn_parts:
                dfeats.append({"properties": {"key": "%s|%s" % (c, d)},
                               "geometry": G.mapping(drawn_parts[(c, d)])})
    import boundary_fidelity  # noqa: PLC0415
    fid_ok, fid_msg = boundary_fidelity.check_fidelity(tfeats, dfeats, "key", FIDELITY_MAX_M)
    if not fid_ok:
        fail("%s fidelity: %s" % (AUTHORITY[layer], fid_msg))
    agree = {"points": 0, "same": 0, "explained": 0, "worstM": 0.0}
    lost = []
    for c in split:
        C = fabric_shapes[c]
        lat = C.centroid.y
        tn = sorted(truth[c])
        tt = G.STRtree([truth[c][d] for d in tn])
        dn = sorted(d for (cc, d) in drawn_parts if cc == c)
        dt = G.STRtree([drawn_parts[(c, d)] for d in dn])
        lines_m = G.to_metres(sh.union_all(raw_arcs[c]), lat) if raw_arcs[c] else None
        minx, miny, maxx, maxy = C.bounds
        n = 0
        while n < POINTS_PER_COUNTY:
            p = G.Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if not C.contains(p):
                continue
            n += 1
            a = [tn[i] for i in tt.query(p, predicate="within")]
            b = [dn[i] for i in dt.query(p, predicate="within")]
            agree["points"] += 1
            if a == b and len(a) == 1:
                agree["same"] += 1
                continue
            dist = lines_m.distance(G.to_metres(p, lat)) if lines_m is not None else float("inf")
            if dist > FIDELITY_MAX_M:
                fail("%s: a point at %r in %s is in %r in the 2010 pieces and %r in the drawing, "
                     "%.1f m from any 2010 dividing line" % (AUTHORITY[layer], G.xy(p), c, a, b,
                                                             dist))
            agree["explained"] += 1
            agree["worstM"] = max(agree["worstM"], round(dist, 2))
        for d, T in sorted(truth[c].items()):
            for part in G.polys(T):
                rp = part.representative_point()
                got = [dn[i] for i in dt.query(rp, predicate="within")]
                if got != [d]:
                    lost.append({"county": c, "district": d, "m2": round(G.m2(part), 2),
                                 "at": G.xy(rp), "drawnIn": got})
    lost.sort(key=lambda x: -x["m2"])
    if lost:
        # none on the first build (2026-10-20), so any is a change to read: a
        # piece of 2010 ground the simplified lines no longer hold
        fail("%s: %d piece(s) of 2010 ground are not in their district in the drawing, the "
             "largest %.1f m2 of %s District %s at %r, drawn in %r"
             % (AUTHORITY[layer], len(lost), lost[0]["m2"], lost[0]["county"],
                lost[0]["district"], lost[0]["at"], lost[0]["drawnIn"]))

    # -- the features -------------------------------------------------------
    features = []
    for d in sorted(expected, key=unit_key):
        g = G.areal(sh.union_all(by_district[d], grid_size=GRID))
        geom = G.mapping(g)
        features.append({"type": "Feature", "properties": expected[d],
                         "geometry": round_geometry(geom)})
    parts_rec = {}
    for (c, d), g in sorted(drawn_parts.items()):
        parts_rec["%s|%s" % (c, d)] = {"deg2": g.area, "km2": round(G.km2(g), 4),
                                       "point": G.xy(G.inner_point(g))}
    stats = {
        "file": rel(OUT[layer]),
        "districts": len(features),
        "splitCounties": per_county,
        "dividingLineVertices": [nraw, nsimp],
        "stateFaces": len(faces),
        "stateCuts": len(getattr(cuts, "geoms", [])),
        "weakestFaceMajority": [round(weakest[0], 4), weakest[1]],
        "fidelity": fid_msg,
        "points": agree,
        "lostParts": lost,
    }
    return features, parts_rec, stats


def round_geometry(geom):
    def r(c):
        return [round(c[0], 6), round(c[1], 6)]
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": [[r(c) for c in ring] for ring in geom["coordinates"]]}
    if geom["type"] == "MultiPolygon":
        return {"type": "MultiPolygon",
                "coordinates": [[[r(c) for c in ring] for ring in poly] for poly in geom["coordinates"]]}
    fail("a district dissolved to a %s" % geom["type"])


def build(cache, accept):
    check_card()
    G = Geometry()
    fabric = load_fabric()
    read_law(fabric)              # a parse that fails stops before the network
    net = connect()
    fetch_statutes(net, accept)
    law = read_law(fabric)        # the text as it is now, held to the live page
    fabric_shapes = {c: G.valid(g) for c, g in fabric.items()}
    vtds, blocks = census2010(net, law, cache)
    county_points = {c: G.xy(G.inner_point(g)) for c, g in sorted(fabric_shapes.items())}
    rng = random.Random(SEED)
    out, rec_layers = {}, {}
    for layer in LAYERS:
        assigns = assignments(law, layer, vtds)
        features, parts, stats = build_layer(G, law, layer, assigns, vtds, blocks,
                                             fabric_shapes, rng)
        stats["parts"] = parts
        st = verify(law, layer, features, stats, county_points, fabric)
        out[layer] = features
        rec_layers[layer] = stats
        note("%s: %d districts; %s; %d of %d points agree, %d more within %.1f m of a 2010 line "
             "(worst %.2f m); %d lost part(s)%s; areas within %.1e; %d interior points"
             % (AUTHORITY[layer], st["districts"], stats["fidelity"], stats["points"]["same"],
                stats["points"]["points"], stats["points"]["explained"], FIDELITY_MAX_M,
                stats["points"]["worstM"], len(stats["lostParts"]),
                (", largest %.2f m2" % stats["lostParts"][0]["m2"]) if stats["lostParts"] else "",
                st["area"], st["points"]))
    record = {
        "built": datetime.date.today().isoformat(),
        "statutes": {name: {"url": STATUTE_URL % name, "sha256": sha256(statute_path(name))}
                     for name in SECTIONS},
        "census2010": {"service": TIGERWEB_2010, "vtdLayer": VTD_LAYER,
                       "blockLayer": BLOCK_LAYER,
                       "vtds": {c: len(v) for c, v in sorted(vtds.items())},
                       "blocks": len(blocks)},
        "countyFile": {"file": rel(COUNTIES), "sha256": sha256(COUNTIES)},
        "simplify": {"method": "Douglas-Peucker on each dividing line, ends fixed",
                     "toleranceM": TOLERANCE_M},
        "fidelityMaxM": FIDELITY_MAX_M,
        "countyPoints": county_points,
        "layers": rec_layers,
        "findings": law["findings"],
    }
    return out, record


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="offline, stdlib only: hold the shipped files to the kept statutes")
    ap.add_argument("--cache", help="read and save the 2010 Census queries in this folder")
    ap.add_argument("--accept-statutes", action="store_true",
                    help="replace a kept statute with its live text (after reading the change)")
    ap.add_argument("--dry-run", action="store_true", help="build and run every gate, write nothing")
    args = ap.parse_args()
    if args.check:
        check()
        return
    out, record = build(args.cache, args.accept_statutes)
    if args.dry_run:
        note("dry run: nothing written")
        return
    import gzip  # noqa: PLC0415
    for layer in LAYERS:
        body = json.dumps({"type": "FeatureCollection", "features": out[layer]},
                          separators=(",", ":"))
        with open(OUT[layer], "w", encoding="utf-8") as fh:
            fh.write(body)
        note("wrote %s: %d districts, %d bytes, %d gzipped"
             % (rel(OUT[layer]), len(out[layer]), len(body),
                len(gzip.compress(body.encode("utf-8"), 9))))
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    note("wrote %s" % rel(RECORD))


if __name__ == "__main__":
    main()
