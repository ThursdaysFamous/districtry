#!/usr/bin/env python3
"""
Build nc/data/app/nc-school-board-districts.json — the election districts of
the North Carolina school boards that elect members by district, drawn from
the State Board of Elections' own precinct-level results.

Most North Carolina school boards are elected at large, by the whole school
district. Some elect each member from one part of it. Which boards do, and
where their districts run, is published nowhere this project found as a list
or a map: the State Board of Elections' ShapeFiles folder carries its precinct
maps and nothing else, and the method each board elects by is set by law that
has not been read here.

THE RESULTS SAY WHERE THE LINES ARE. The State Board publishes each election's
results as one tab-separated file per election day
(dl.ncsbe.gov/ENRS/<yyyy_mm_dd>/results_pct_<yyyymmdd>.zip), one row per
contest, choice and precinct. A board seat's contest ("WAKE COUNTY BOARD OF
EDUCATION DISTRICT 03") is on the ballots of exactly the precincts of its
district, so those precincts, read in the State Board's precinct map of that
election and cut to the Census school district's boundary (TIGERweb School
layer 0), are the district. nc/scripts/ncsbe_results.py reads the same files
for municipal winners; this builder reads a different column of them, the
precincts each board contest was on, and reads every file since 2022.

WHICH BOARDS COUNT IS MEASURED, NOT LISTED. A seat labelled "District 3" is an
election district only if its precincts are part of its board's, so for each
election day with two or more of a board's contests, each labelled seat's
share of the board's precincts is measured, and a seat under SHARE_CEILING
(0.95) on every such day is a district seat. Party primaries are left out,
because a primary only nominates: Carteret's board nominates by district and
elects at large. Measured 2026-10-17 over the files since 2022: 115 boards,
45 elected at large, 38 electing by district and 32 that label seats by
district while every precinct votes on each of them, which is a rule about
where a member lives rather than a district, so those 32 are printed and not
drawn (the list is below). A district seat's largest share was 0.800 and a
voted-everywhere seat's smallest 1.000, so the ceiling sits in a gap and
moves no board.

WHICH SEATS ARE CURRENT. A member serves a four-year term and a board's seats
are elected in two groups, so the district seats elected in the board's two
most recent election years (counting only years with a regular contest) are
its board, each drawn from its latest contest. Three seats last elected
before that are printed and not drawn: Granville District 5 (last elected
2022-05-17), Nash District 8 (2022-12-06) and Nash District 9 (2022-11-08).
A seat on the 3 November 2026 ballot is drawn from that ballot: the State
Board posted that election's file on 2026-10-05, before the election, carrying
every contest and the precincts it is on with no votes. That file is not
linked from the State Board's historical results page (read 2026-10-16, which
links files through the 3 March 2026 election); it was found by listing the
bucket the files are served from.

EACH ELECTION IS READ IN ITS OWN PRECINCT MAP. A precinct code means that
election's precinct, and counties renumber and redraw precincts between
elections. The State Board posts its statewide precinct shapefile as dated
zips in one folder (dl.ncsbe.gov/ShapeFiles/Precinct/), and for each election
and county the builder reads the map that holds the most of the codes the
results report there, then the one with the fewest codes either side lacks,
then one dated on or before the election, then the nearest. Measured
2026-10-17: 120 elections-and-counties read; 2 read in a map dated after the
election (Durham's 2024-03-05 precincts in the map of 2025-02-25, Union's
2024-11-05 precincts in the map of 2025-12-12), each because it held more of
that election's codes, or as many with fewer codes either side lacks; 2 where
no map holds every code (Wake on 2022-11-08, 99.0% held by the map of
2022-08-31, and on 2024-11-05, 99.1% by the map of 2024-07-23). One of the
missing codes, WAKE 01-07A, was on one of these boards' ballots; it is left
out of that seat's ground, and the Wake board's report still shows its school
district placed but for 2,738 m2.

FOUR KINDS OF PIECE, AND THE CARD SAYS WHICH.
  * "district": ground where one seat's latest contest was on the ballot.
  * "split": a precinct whose ballots carried two or more seats of one
    election. A district line runs through it and the results do not say
    where, so it ships as its own piece naming every seat.
  * "overlap": ground where different elections put different seats on the
    ballot. A board elects its seats in different years, so where a district
    line runs through a precinct, the precinct shows each district in the year
    that district's seat is on the ballot; a board can also redraw its
    districts between elections. The results do not say which, so the piece
    names every election and its seats and the card chooses none.
  * "unplaced": ground in the school district on no current district seat's
    latest ballot. It ships with its area printed and, read precinct by
    precinct in the newest map, either the contests that were on the ballot
    across most of it (VOTED_SHARE) or the precincts it lies in.
Durham's two consolidated districts are a second tier ("tier": "overlay") over
its four districts; check_overlay measures that each is the union of two or
more of them and that each district lies in exactly one, and fails otherwise.

LINES TWO MAPS DRAW A LITTLE APART. Different elections' maps draw one line a
few metres apart, so pieces are laid down newest election first, and where an
older piece overlaps a newer one, a strip narrower than 2 x SLIVER_M (60 m)
stays with the newer and anything wider, of at least MIN_OVERLAP_KM2, becomes
an overlap piece. A part of a piece nowhere 60 m wide is dropped unless it and
other pieces' thin parts together make ground wider than that; those are where
three or more maps' lines cross. A first draft also dropped every piece under
a hectare, and the hole gate failed it on two holes it left, of 8,153 m2 in
Nash-Rocky Mount and 5,167 m2 in Robeson, so small pieces are listed in the
report and kept. Measured 2026-10-17: 1.56 km2 of map drift given to the newer
election; 59,849 thin parts of 1.69 km2 dropped; 2.25 km2 of ground in a
board's school district and the newest precinct map on no piece, 0 m2 of it in
parts 60 m wide anywhere; 7 pieces under SMALL_PIECE_M2 (Harnett, 2026-11-03
District 1 and District 3: 1 m2; Harnett, 2024-11-05 District 4: 4 m2;
Hickory City, not placed: 9,614 m2; Nash, 2026-11-03 District 2 and District
7: 1,797 m2; Nash, 2026-11-03 District 7: 6,356 m2; Robeson, 2026-03-03
District 2 and District 3: 3,283 m2; Robeson, 2026-03-03 District 3: 1,884
m2); and 0.09 km2 of the school districts outside every precinct of the newest
map, 11,009 m2 of it in parts 60 m wide somewhere, in Martin County. The
card's empty note states both kinds of gap.

ONE SIMPLIFICATION FOR EVERY PIECE. mapshaper runs once over the whole file
(dp interval=15 keep-shapes, 6 decimals), so a line two pieces share is
simplified once. Lines two pieces do not share, because they were read from
different elections' maps, move independently and can cross; the gates
measure that rather than assume it. Measured 2026-10-17 on the written file:
8,414 of 8,443 points sampled inside the exact pieces (99.657%, seed 20261017,
20 a piece) land in the same piece, and only there, after simplification
(floor 99.5%), and none lands in two pieces of one tier; no piece's interior
point lies in another piece of its tier; 368 crossings of 1,766 m2 in all,
the largest 73 m2 (MAX_CROSSING_M2 1,000); 6 outlines touching themselves
where the simplification moved two vertices together, counted and repaired
before the other gates measure; 6,328 holes of 4,287,247 m2 between a board's pieces, the
widest 65.0 m across (MAX_HOLE_M 90, two 30 m strips plus the 15 m each side
can move). Two holes in the Census outlines themselves are another district's
ground and the hole gate skips them by a point inside each, recorded in the
build record: Buncombe County Schools at 35.6102, -82.5591 and
Iredell-Statesville Schools at 35.5937, -80.8622 (inferred to be Asheville City
Schools and Mooresville Graded School District, which the Census draws as
separate districts). 423 features, 3,717,673 bytes, 986,863 gzipped.

SEATS THAT MOVED. A seat whose ground in its latest election differs from its
ground in its election before by at least MOVED_KM2 and MOVED_SHARE is
reported, not changed, because the results cannot say whether a board redrew
its districts or a county redrew its precincts. Measured 2026-10-17, 16 seats
on 11 boards: Alexander District 2 (2022-11-08 to 2026-11-03, 312.7 km2),
District 3 (2024-11-05 to 2026-11-03, 214.6 km2) and District 4 (2024-11-05 to
2026-11-03, 274.3 km2); Bladen District 3 (2024-11-05 to 2026-11-03, 71.9 km2);
Craven District 1 (2022-11-08 to 2024-11-05, 1,321.6 km2) and District 4
(2022-11-08 to 2026-11-03, 19.5 km2); Duplin District 3 (2022-11-08 to
2026-11-03, 125.9 km2); Edgecombe District 1 (2022-05-17 to 2026-03-03, 230.7
km2), District 3 (399.7 km2) and District 5 (60.9 km2), the same two
elections; Harnett District 5 (2022-11-08 to 2026-11-03, 96.4 km2);
Montgomery District 7 (2022-11-08 to 2026-11-03, 81.4 km2); Nash District 4
(2022-11-08 to 2024-11-05, 307.5 km2); Pamlico District 4 (2022-05-17 to
2026-11-03, 113.4 km2); Union District 4 (2022-11-08 to 2026-11-03, 69.1
km2); Vance District 7 (2022-11-08 to 2026-11-03, 11.8 km2).

65 SEATS HAVE NO GROUND OF THEIR OWN, measured 2026-10-17: each is named only
on split or overlap pieces, every one of Vance's seven among them, because
every precinct its contest was on also carried another seat of the same
election or another election's seat. The build prints them by name.

DRAWN, measured 2026-10-17: 38 boards, 214 district seats and 2 consolidated
districts over them, 100 split precincts, 161 overlap pieces, and 11 unplaced
pieces of 628.31 km2, 3.21 km2 of it on none of a board's ballots. Watauga's
board has no district contest in the files before the 3 November 2026 ballot,
which carries its Districts 1 and 4, and its other members were elected at
large in 2022 and 2024, so 535.86 km2 of its ground, 67%, is not placed. Per board, from the build's report (districts, with Durham's two
consolidated districts after the plus; split precincts; overlap pieces; km2
not placed, with the part on none of the board's ballots in brackets; the
share of the ground placed; m2 of map drift given to the newer election; thin
parts dropped and their m2; m2 left on no piece):

  school district (GEOID)        dist  split  overlap  not placed km2  placed  drift m2  thin pieces (m2)  on no piece m2
  Alexander County Schools          5      4        2           60.66     91%     30075       948 (30075)           31312
  Anson County Schools              7      0        2            0.00    100%      8809        805 (7774)            7776
  Beaufort County Schools           9      6        5            0.00    100%     19095       933 (16677)           16679
  Bladen County Schools             3      7        0            0.00    100%         0             0 (0)              19
  Buncombe County Schools           6      3        3     1.33 (1.33)    100%     78329      2215 (49386)          254554
  Caswell County Schools            5      1        6            0.00    100%     19656      2287 (19474)           19523
  Charlotte-Mecklenburg Schools     6      0        0            0.00    100%         0             0 (0)              24
  Craven County Schools             7      0        6            0.00    100%    129780      2011 (90714)           90716
  Cumberland County Schools         6      1        0            0.00    100%         0        73 (22433)           22488
  Duplin County Schools             5      5        7            0.00    100%     80063      3502 (71780)           71782
  Durham Public Schools           4+2      0        0            0.00    100%         0             0 (0)              32
  Edenton-Chowan Schools            3      2        0            0.00    100%         0             0 (0)               1
  Edgecombe County Schools          7      4        9            0.00    100%     28478      4722 (27613)           27620
  Forsyth County Schools            2      0        0     0.44 (0.44)    100%         0             0 (0)           96101
  Franklin County Schools           5      0        2            0.00    100%      2617        201 (1414)            1427
  Granville County Schools          6      4        7            0.00    100%     54895      1929 (48700)           48701
  Guilford County Schools           8      0        0            0.00    100%         0             0 (0)          116582
  Harnett County Schools            5      5       11     0.39 (0.39)    100%    295954     4661 (559229)          612040
  Hickory City Schools              5      0        4    21.81 (0.01)     69%     11031        620 (8788)           17099
  Iredell-Statesville Schools       7      2        1            0.00    100%     36059       229 (35827)           40759
  Lenoir County Schools             5      1        0            0.00    100%         0             0 (0)              13
  Lexington City Schools            6      1        4     6.85 (0.06)     85%     44864       866 (43299)           80562
  Madison County Schools            2      0        0            0.00    100%         0             0 (0)               7
  Martin County Schools             7      1        5            0.00    100%     28233      3415 (28233)           28237
  Montgomery County Schools         7      2        8            0.00    100%     32191      2966 (32191)           32193
  Nash-Rocky Mount Schools          7     12        6            0.00    100%    100519      3834 (91512)           91604
  Newton-Conover City Schools       2      3        0     0.02 (0.02)    100%         0           112 (0)           12080
  Pamlico County Schools            5      1        1            0.00    100%      9171        383 (7904)            7905
  Pitt County Schools               9      4        4            0.00    100%     20509       888 (15652)           15654
  Robeson County Schools            8     11       23            0.00    100%    244432     9053 (238248)          249193
  Rockingham County Schools         4      3        0            0.00    100%         0             0 (0)              21
  Union County Public Schools       6      3        3            0.00    100%     37789      1256 (33725)           33728
  Vance County Schools              7      2        9            0.00    100%     61661      2770 (61661)           61662
  Wake County Schools               9      0        1            0.00    100%     38059         43 (2568)            2738
  Watauga County Schools            2      1        0          535.86     33%         0             0 (0)            7311
  Wayne County Public Schools       6      9       12            0.00    100%     63551      4831 (61118)           61119
  Whiteville City Schools           4      0        4     0.96 (0.96)    100%     40968      1134 (40968)           53056
  Wilson County Schools             7      2       16            0.00    100%     40223      3162 (40223)           40224

Wake's report also names WAKE 01-07A as a precinct code no map holds.

The 32 boards that label seats by district while every precinct votes on each
of them, measured 2026-10-17: Bertie, Brunswick, Burke, Carteret, Chatham,
Cherokee, Columbus, Currituck, Dare, Elkin City, Gaston, Gates, Haywood, Hyde,
Jackson, Johnston, Kannapolis City, Lincoln, Macon, McDowell, Moore, Mount
Airy City, Pasquotank, Pender, Polk, Rowan-Salisbury, Rutherford, Scotland,
Stanly, Surry, Warren and Washington.

WHAT THE STATE BOARD DOES NOT PUBLISH, recorded as found:
  * No map of any board's districts, here or anywhere this project found.
  * The 3 November 2026 file is in the bucket and not on the historical
    results page (above).
  * The 14 May 2024 second primary has no precinct-level file. Its folder
    holds the absentee, provisional, polling-place, voter and history files
    and no results_pct zip, and the historical results page says
    "Precinct-level data is not available for this election", linking the
    State Board's press release of 2024-05-15, "To Protect the Secrecy of the
    Ballot in Second Primary, State Board Removes Precinct-Level Data from
    Website". A second primary is a runoff for party nominations, which this
    builder leaves out (above), so the missing file most likely removes
    nothing it would have read; that is inferred, since the file cannot be
    read to check.
  * Boards are named differently from one file to the next: Charlotte-
    Mecklenburg Schools Board of Education (from 2022-11-08) and
    Charlotte-Mecklenburg Board of Education (from 2025-11-04); Edgecombe
    County Schools Board of Education (2022-05-17) and Edgecombe County Board
    of Education (2026-03-03); Hickory Public Schools Board of Education
    (2024-11-05) and Hickory City Schools Board of Education (2026-11-03); Nash
    County Public Schools Board of Education (2022-11-08) and Nash County Board
    of Education (2024-11-05); Row-Sal Schools Board of Education (2022-11-08),
    Rowan-Salisbury Schools Board of Education (2024-11-05) and Rowan-Salisbury
    Board of Education (2026-03-03). board_stem() folds each to one board, and
    SCHOOL_ALIAS joins Nash's to the Census's name for its district,
    Nash-Rocky Mount.
These, and what the drawn layer cannot place, are recorded as gap
nc-school-board-districts in docs/DATA_LAYER_GUIDEBOOK.md's gaps block.

NO MEMBER IS NAMED. The results name each contest's winner, but a board fills
a vacancy by appointment, which no results file shows, and the seats on the 3
November 2026 ballot stay with the members serving now until that election's
winners take office. Matching winners to the members serving now has not been
done, so the card names no one. No candidate listing was read for this layer;
one read later to name members may give only each candidate's name, contest,
party and term, never a home address, e-mail address or telephone number.
Recorded as gap nc-school-board-members.

THE BOARD'S WEBSITE. The card links each board's school district website, the
address in the district directory of NCES's Common Core of Data, which keys a
district by the NCES id the Census also uses as its GEOID, so the join needs
no name. The builder takes the newest directory file the CCD's own file
listing names (ccd_lea_029_2526_w_0a_050626.zip, for the 2025-26 school year,
on 2026-10-17) and keeps an address only where it answered with a page,
following each redirect with robots.txt read for every hop's host: all 38 on
2026-10-17. The previous year's directory (ccd_lea_029_2425_w_1a_073025.zip)
spelled three of the hosts with one or two w's (w.ecps.k12.nc.us,
w.martin.k12.nc.us, ww.ncpschools.net), none of which has a DNS record; the
2025-26 file spells all three with www. The Department of Public
Instruction's own directory (EDDIE, eddie.ncpublicschools.gov) was not read:
its robots.txt could not be read from this project's sandbox on 2026-10-17
(the proxy's tunnel to the host failed with 502 on three attempts), and a
robots.txt that cannot be read disallows (RFC 9309 2.3.1.4). Whether that
was the host or this sandbox's route is not established.

ROBOTS.TXT, read before the first fetch of every host and at every redirect
hop, 2026-10-16 and 2026-10-17: dl.ncsbe.gov serves none (404, allow);
s3.amazonaws.com, where the bucket is listed, answers 403, which reads as no
policy; tigerweb.geo.census.gov answers 189 bytes of HTML at that path, which
is not a robots.txt; nces.ed.gov serves 437 bytes whose rules shut nothing
this builder fetches (they shut /ccd/districtsearch/ and /ccd/schoolsearch/,
among others); vt.ncsbe.gov, the voter search the card
links, serves none (404). Every school district host is read the same way at
each build.

Run:  python3 nc/scripts/build_nc_school_board_districts.py [--cache DIR]
      python3 nc/scripts/build_nc_school_board_districts.py --check   (offline)
      python3 nc/scripts/build_nc_school_board_districts.py --watch   (network)
"""

import argparse
import collections
import csv
import datetime
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
REPO = os.path.dirname(INSTANCE)
FLEET_SCRIPTS = os.path.join(REPO, "scripts")
sys.path.insert(0, FLEET_SCRIPTS)

from scraper_common import require_robots_once  # noqa: E402

USER_AGENT = "districtry/1.0 (+https://districtry.com/nc/)"
HEADERS = {"User-Agent": USER_AGENT}
REQUEST_TIMEOUT = 300
PACE_SECONDS = 0.5

HOST = "https://dl.ncsbe.gov"
LISTING = "https://s3.amazonaws.com/dl.ncsbe.gov"
RESULTS_FOLDER = "ENRS/"
RESULTS_ZIP = HOST + "/ENRS/%s/results_pct_%s.zip"
PRECINCT_FOLDER = "ShapeFiles/Precinct/"
PRECINCT_ZIP = HOST + "/ShapeFiles/Precinct/SBE_PRECINCTS_%s.zip"
TIGER_LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
               "School/MapServer/0/query")
STATE_FIPS = "37"
FIRST_DATE = datetime.date(2022, 1, 1)
# NCES's Common Core of Data file listing, the API its own files page reads.
CCD_API = "https://nces.ed.gov/ccd/datatables/api/"

OUT_FILE = os.path.join(INSTANCE, "data", "app", "nc-school-board-districts.json")
RECORD_FILE = os.path.join(INSTANCE, "data", "source", "nc-school-board-districts.source.json")

MAPSHAPER = "mapshaper@0.6.102"
SIMPLIFY_INTERVAL_M = 15

# A district seat is voted on in part of its board's ground; a seat every
# precinct votes on is a residency seat (the member lives in the district and
# the whole school district elects). The measured gap between the two is in
# the docstring.
SHARE_CEILING = 0.95

# A seat named "Consolidated District" is a second tier over the board's other
# district seats (Durham's two). The wording is only where the build looks;
# check_overlay measures that each one is the union of two or more districts
# and that each district lies in exactly one of them, and fails otherwise.
OVERLAY_WORD = "CONSOLIDATED "
OVERLAY_INSIDE = 0.90

# Two elections' precinct maps draw one line a little apart; a strip narrower
# than twice this is that, and goes to the newer election. Ground no seat
# places ships as "not placed" wherever it is at least this wide somewhere,
# whatever its area, so that no ground wider than a strip is left on no piece.
SLIVER_M = 30.0
MIN_OVERLAP_KM2 = 0.05
# Pieces smaller than this are listed in the report. They are kept: each is
# made of strips that, with other pieces' strips, cover ground wider than a
# strip, and dropping them was measured to leave such ground on no piece
# (the docstring).
SMALL_PIECE_M2 = 1e4
# The shared simplification moves lines that two pieces do not share (they
# were read from different elections' maps) independently, so the two can
# cross. Measured 2026-10-17 in the docstring; a crossing larger than this is
# not that.
MAX_CROSSING_M2 = 1000.0
# A hole between one board's pieces is a strip of map drift (narrower than
# 2 x SLIVER_M before simplification) whose two sides the simplification can
# each move by up to SIMPLIFY_INTERVAL_M; the card's empty note states this
# ceiling, and a hole wider than it is not that.
MAX_HOLE_M = 2 * SLIVER_M + 2 * SIMPLIFY_INTERVAL_M
# Points sampled inside every exact piece must land in the same piece after
# the shared simplification at least this often (measured in the docstring).
AGREEMENT_FLOOR = 0.995
AGREEMENT_PER_PIECE = 20
# A contest counts as on the ballot in a piece of unplaced ground when its
# precincts cover at least this share of the piece.
VOTED_SHARE = 0.5
# A seat whose ground in its latest election differs from its ground in its
# election before by at least this much, and this share, is reported as
# redrawn between them.
MOVED_KM2 = 1.0
MOVED_SHARE = 0.05
M_PER_DEG_LAT = 110540.0

# Measured 2026-10-17 (the docstring). A rebuild that draws fewer stops for a
# person to read why.
MIN_BOARDS = 38
MIN_SEATS = 214

BOARD_RE = re.compile(
    r"^(?P<board>.*?\b(?:SCHOOL BOARD OF EDUCATION|BOARD OF EDUCATION|"
    r"BD OF EDUCATION|BD OF EDU|BD OF ED))\b\s*(?P<seat>.*)$")
NOT_SEAT = re.compile(r"REFERENDUM|\bBONDS?\b|ELECTION METHOD")
SUFFIX_RE = re.compile(r"\s*\((REP|DEM|LIB|UNA|GRE|CST|NLB|JFA|UNEXPIRED)\)\s*$")
AT_LARGE = re.compile(r"^(?:|AT-LARGE.*|AT LARGE.*|MEMBER AT-LARGE|COUNTY-WIDE|"
                      r"COUNTYWIDE|CHAIR|CHAIRMAN)$")
ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}

# The results name a board one way and the Census names its school district
# another. Measured 2026-10-17: every other board's name, with the words
# "County", "City", "Public", "Schools" and "Graded" taken out, is its school
# district's.
SCHOOL_ALIAS = {
    # The results call it "Nash County Public Schools" (2022) and "Nash
    # County" (2024 and 2026); the Census still calls it Nash-Rocky Mount.
    "NASH": "NASH-ROCKY MOUNT",
}


def fail(msg):
    raise SystemExit("build-nc-school-board-districts: FATAL: %s" % msg)


# --------------------------------------------------------------------------
# fetching, one redirect hop at a time, robots.txt read for every hop's host
# --------------------------------------------------------------------------

def get(session, url, params=None, stream=False):
    import requests  # noqa: PLC0415
    for _hop in range(6):
        require_robots_once(url, USER_AGENT, headers=HEADERS)
        resp = session.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                           allow_redirects=False, stream=stream)
        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
            url = requests.compat.urljoin(url, resp.headers["Location"])
            params = None
            continue
        if resp.status_code != 200:
            fail("%s answered HTTP %d" % (url, resp.status_code))
        time.sleep(PACE_SECONDS)
        return resp
    fail("%s redirected more than five times" % url)


def cached(cache, name, fetch):
    """Bytes of `name` from the cache folder, fetched and saved there first
    when it is not yet there."""
    path = os.path.join(cache, name) if cache else None
    if path and os.path.exists(path):
        with open(path, "rb") as fh:
            return fh.read()
    body = fetch()
    if path:
        with open(path, "wb") as fh:
            fh.write(body)
    return body


def cached_json(cache, name, make):
    path = os.path.join(cache, name) if cache else None
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    data = make()
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
    return data


def list_folder(session, prefix):
    """(sub-folders, {key: last-modified}) of one folder of the Board's bucket."""
    dirs, files, marker = [], {}, None
    while True:
        params = {"delimiter": "/", "prefix": prefix}
        if marker:
            params["marker"] = marker
        text = get(session, LISTING, params=params).text
        dirs += re.findall(r"<CommonPrefixes><Prefix>([^<]*)</Prefix>", text)
        for key, when in re.findall(r"<Key>([^<]*)</Key><LastModified>([^<]*)</LastModified>",
                                    text):
            files[key] = when
        if "<IsTruncated>true</IsTruncated>" not in text:
            return dirs, files
        last = re.findall(r"<Key>([^<]*)</Key>", text) or re.findall(r"<Prefix>([^<]*)</Prefix>", text)
        marker = last[-1]


# --------------------------------------------------------------------------
# names
# --------------------------------------------------------------------------

def parse_seat(raw):
    """(seat key, party or None, unexpired, seat number or None) from the part
    of a contest name after the board's name."""
    s = raw.upper().strip()
    party, unexpired = None, False
    while True:
        m = SUFFIX_RE.search(s)
        if not m:
            break
        if m.group(1) == "UNEXPIRED":
            unexpired = True
        else:
            party = m.group(1)
        s = s[:m.start()].strip()
    s = re.sub(r"\bDIST\b", "DISTRICT", s)
    s = re.sub(r"\b0+(\d)", r"\1", s)
    s = re.sub(r"\bTWP\b", "TOWNSHIP", s)
    seatno = None
    m = re.match(r"^(DISTRICT \S+) SEAT (\d+)$", s)
    if m:
        s, seatno = m.group(1), int(m.group(2))
    return s, party, unexpired, seatno


def board_stem(name):
    b = name.upper()
    b = re.sub(r"\s*\b(?:SCHOOL BOARD OF EDUCATION|BOARD OF EDUCATION|BD OF EDUCATION|"
               r"BD OF EDU|BD OF ED)$", "", b)
    b = b.replace("ROW-SAL", "ROWAN-SALISBURY")
    b = re.sub(r"\b(?:PUBLIC SCHOOLS|SCHOOLS|SCHOOL|GRADED|CITY|COUNTY|CO)\b", " ", b)
    return re.sub(r"\s+", " ", b).strip()


def natural(key):
    """Sort "District 2" before "District 10"."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", key)]


def display(key):
    if not key or re.match(r"^(?:MEMBER )?AT[- ]LARGE$", key):
        return "At large"
    m = re.match(r"^AT[- ]LARGE SEAT (\d+)$", key)
    if m:
        return "At large, seat %s" % m.group(1)
    if key in ("COUNTY-WIDE", "COUNTYWIDE"):
        return "Countywide"
    if key in ("CHAIR", "CHAIRMAN"):
        return "Chair"
    words = []
    for w in key.split(" "):
        if w in ROMAN or w.isdigit() or (len(w) == 1 and w.isalpha()):
            words.append(w)
        else:
            words.append("-".join(p[:1] + p[1:].lower() for p in w.split("-")))
    return " ".join(words)


def board_title(name):
    words = []
    for w in name.split(" "):
        if w in ("OF", "AND"):
            words.append(w.lower())
        elif w in ("BD",):
            words.append("Board")
        elif w in ("CO",):
            words.append("County")
        elif w in ("EDU", "ED"):
            words.append("Education")
        else:
            words.append("-".join(p[:1] + p[1:].lower() for p in w.split("-")))
    return re.sub(r"\bMc([a-z])", lambda m: "Mc" + m.group(1).upper(), " ".join(words))


def county_title(name):
    t = " ".join(w[:1] + w[1:].lower() for w in name.split(" "))
    return re.sub(r"\bMc([a-z])", lambda m: "Mc" + m.group(1).upper(), t)


# --------------------------------------------------------------------------
# reading the results
# --------------------------------------------------------------------------

def read_results(day, body):
    """Every school board contest in one results file, and every real
    precinct code per county."""
    z = zipfile.ZipFile(io.BytesIO(body))
    names = [n for n in z.namelist() if n.lower().endswith(".txt")]
    if len(names) != 1:
        fail("%s: expected one text file in the results zip, found %r" % (day, names))
    text = z.read(names[0]).decode("latin-1")
    contests = {}
    precincts = collections.defaultdict(set)
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    for col in ("County", "Precinct", "Contest Name", "Choice", "Vote For", "Total Votes",
                "Real Precinct"):
        if col not in (reader.fieldnames or []):
            fail("%s: the results file has no %r column (%r)" % (day, col, reader.fieldnames))
    for row in reader:
        county = row["County"].strip().upper()
        code = row["Precinct"].strip()
        real = row["Real Precinct"].strip() == "Y"
        if real:
            precincts[county].add(code)
        name = row["Contest Name"].strip().upper()
        m = BOARD_RE.match(name)
        if not m or NOT_SEAT.search(name):
            continue
        c = contests.setdefault((county, name), {
            "day": day, "county": county, "name": name, "board": m.group("board").strip(),
            "seat_raw": m.group("seat").strip(), "codes": set(), "vote_for": set()})
        if real:
            c["codes"].add(code)
        c["vote_for"].add(row["Vote For"].strip())
    return list(contests.values()), precincts


# --------------------------------------------------------------------------
# the precinct maps
# --------------------------------------------------------------------------

def precinct_geojson(cache, stamp, zip_body):
    """The State Board's precinct shapefile for one date, as WGS84 GeoJSON."""
    name = "SBE_PRECINCTS_%s.geojson" % stamp
    path = os.path.join(cache, name) if cache else None
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    if not shutil.which("npx"):
        fail("npx is not on PATH; this builder reads the shapefiles through mapshaper")
    work = tempfile.mkdtemp(prefix="nc-sbd-")
    try:
        src = os.path.join(work, "SBE_PRECINCTS_%s.zip" % stamp)
        dst = os.path.join(work, name)
        with open(src, "wb") as fh:
            fh.write(zip_body)
        proc = subprocess.run(["npx", "--yes", MAPSHAPER, "-i", src, "-proj", "wgs84",
                               "-o", "format=geojson", "precision=0.000001", dst],
                              capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(dst):
            fail("mapshaper could not read %s (%d): %s"
                 % (src, proc.returncode, (proc.stderr or "")[-800:]))
        with open(dst, encoding="utf-8") as fh:
            data = json.load(fh)
        if path:
            shutil.copyfile(dst, path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return data


class Vintages:
    """Every precinct map the Board has posted since FIRST_DATE."""

    def __init__(self, maps):
        from shapely.geometry import shape  # noqa: PLC0415
        self.days = sorted(maps)
        self.codes = {}
        self.feature = {}
        self._shape = {}
        self._tree = {}
        self._shape_of = shape
        for day in self.days:
            per = collections.defaultdict(set)
            for f in maps[day]["features"]:
                p = f["properties"]
                county = str(p.get("county_nam") or "").strip().upper()
                code = str(p.get("prec_id") or "").strip()
                if not county or not code:
                    continue
                if code in per[county]:
                    fail("SBE_PRECINCTS_%s carries %s %s twice" % (day.strftime("%Y%m%d"),
                                                                   county, code))
                per[county].add(code)
                self.feature[(day, county, code)] = f
            self.codes[day] = per

    def touching(self, day, geom):
        """(county, code) of every precinct of one map that meets `geom`."""
        from shapely.strtree import STRtree  # noqa: PLC0415
        if day not in self._tree:
            keys = sorted((c, code) for c, codes in self.codes[day].items() for code in codes)
            shapes = [self.shape(day, c, code) for c, code in keys]
            self._tree[day] = (STRtree(shapes), keys, shapes)
        tree, keys, shapes = self._tree[day]
        return [keys[i] for i in tree.query(geom) if shapes[i].intersects(geom)]

    def shape(self, day, county, code):
        key = (day, county, code)
        if key not in self._shape:
            g = self._shape_of(self.feature[key]["geometry"])
            self._shape[key] = g if g.is_valid else g.buffer(0)
        return self._shape[key]

    def name(self, day, county, code):
        p = self.feature[(day, county, code)]["properties"]
        return str(p.get("enr_desc") or code).strip()

    def choose(self, election, county, codes):
        """(map day, share of the codes held) of the map that holds the most
        of the precinct codes the results report for this county on that
        day; then the one with the fewest codes either side lacks; then a map
        dated on or before the election, the one in force that day; then the
        nearest date."""
        best = None
        for day in self.days:
            have = self.codes[day].get(county, set())
            if not have or not codes:
                continue
            held = len(codes & have) / float(len(codes))
            jaccard = len(codes & have) / float(len(codes | have))
            key = (-held, -jaccard, 0 if day <= election else 1, abs((day - election).days))
            if best is None or key < best[0]:
                best = (key, day, held)
        return (best[1], best[2]) if best else (None, 0.0)


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------

def local_scale(g):
    lat = g.centroid.y
    return math.cos(math.radians(lat)) * M_PER_DEG_LAT, M_PER_DEG_LAT


def to_m(g, sx, sy):
    from shapely import affinity  # noqa: PLC0415
    return affinity.scale(g, xfact=sx, yfact=sy, origin=(0, 0))


def to_deg(g, sx, sy):
    from shapely import affinity  # noqa: PLC0415
    return affinity.scale(g, xfact=1.0 / sx, yfact=1.0 / sy, origin=(0, 0))


def polygonal(g):
    from shapely.geometry import MultiPolygon, Polygon  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    if g is None or g.is_empty:
        return Polygon()
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    parts = [p for p in getattr(g, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))]
    return unary_union(parts) if parts else Polygon()


def opening(g, r):
    """The part of `g` wider than 2r: what survives shrinking by r and
    growing back."""
    return polygonal(g.buffer(-r).buffer(r).intersection(g))


def valid(g):
    from shapely.validation import make_valid  # noqa: PLC0415
    return g if g.is_valid else polygonal(make_valid(g))


def area_km2(g):
    return g.area / 1e6


def parts_of(g):
    return [p for p in getattr(g, "geoms", [g]) if not p.is_empty]


def drop_thin(items):
    """(parts dropped, m2 dropped): a part of a piece that is nowhere as wide
    as 2 x SLIVER_M is dropped, unless it and the thin parts of other pieces
    it touches together make ground wider than that somewhere. A thin part
    alone is left where an older election's precinct map draws a line a
    little outside a newer one's, the same strips resolve() calls map drift;
    thin parts that together are wider are where three or more maps' lines
    cross, and they stay with their pieces, however small the piece they
    leave (the report lists every piece under SMALL_PIECE_M2). A part under
    a square metre is always dropped."""
    from shapely.ops import unary_union  # noqa: PLC0415
    from shapely.strtree import STRtree  # noqa: PLC0415
    thin = []
    for idx, it in enumerate(items):
        it["keep"] = []
        for p in parts_of(polygonal(it["geom"])):
            if p.buffer(-SLIVER_M).is_empty:
                thin.append((idx, p))
            else:
                it["keep"].append(p)
    n, area = 0, 0.0
    if thin:
        regions = parts_of(polygonal(unary_union([p for _i, p in thin])))
        wide = [r for r in regions if not r.buffer(-SLIVER_M).is_empty]
        tree = STRtree(wide) if wide else None
        for idx, p in thin:
            pt = p.representative_point()
            if p.area >= 1.0 and tree is not None and \
                    any(wide[j].intersects(pt) for j in tree.query(pt)):
                items[idx]["keep"].append(p)
            else:
                n += 1
                area += p.area
    for it in items:
        keep = it.pop("keep")
        it["geom"] = unary_union(keep) if keep else polygonal(None)
    return n, area


# --------------------------------------------------------------------------
# what the Board and the Census have posted
# --------------------------------------------------------------------------

def fetch_school(session, cache, geoid):
    def pull():
        resp = get(session, TIGER_LAYER, params={
            "where": "GEOID='%s'" % geoid, "outFields": "GEOID,NAME",
            "returnGeometry": "true", "outSR": "4326", "f": "geojson"})
        return resp.content
    body = json.loads(cached(cache, "tiger_%s.geojson" % geoid, pull).decode("utf-8"))
    if isinstance(body, dict) and body.get("error"):
        fail("TIGERweb answered an error for %s: %r" % (geoid, body["error"]))
    feats = body.get("features") or []
    if len(feats) != 1:
        fail("TIGERweb returned %d school districts for GEOID %s" % (len(feats), geoid))
    return feats[0]


def tiger_names(session, cache):
    def pull():
        resp = get(session, TIGER_LAYER, params={
            "where": "STATE='%s'" % STATE_FIPS, "outFields": "GEOID,NAME",
            "returnGeometry": "false", "f": "json"})
        return resp.content
    body = json.loads(cached(cache, "tiger_names.json", pull).decode("utf-8"))
    if isinstance(body, dict) and body.get("error"):
        fail("TIGERweb answered an error listing school districts: %r" % (body["error"],))
    out = {}
    for f in body.get("features") or []:
        a = f["attributes"]
        out[board_stem(a["NAME"])] = (a["GEOID"], a["NAME"])
    if len(out) < 110:
        fail("TIGERweb listed %d North Carolina unified school districts" % len(out))
    return out


def election_files(session, cache):
    """{day: (url, posted)} for every results file since FIRST_DATE, and the
    dated folders since then that carry none."""
    def make():
        dirs, _ = list_folder(session, RESULTS_FOLDER)
        out = {"found": {}, "missing": []}
        for d in sorted(dirs):
            m = re.match(r"^ENRS/(\d{4})_(\d{2})_(\d{2})/$", d)
            if not m:
                continue
            day = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if day < FIRST_DATE:
                continue
            _, files = list_folder(session, d)
            key = "%sresults_pct_%s.zip" % (d, day.strftime("%Y%m%d"))
            if key in files:
                out["found"][day.isoformat()] = [
                    RESULTS_ZIP % (day.strftime("%Y_%m_%d"), day.strftime("%Y%m%d")), files[key]]
            else:
                out["missing"].append(day.isoformat())
        return out
    data = cached_json(cache, "listing_ENRS.json", make)
    found = {datetime.date.fromisoformat(k): tuple(v) for k, v in data["found"].items()}
    missing = [datetime.date.fromisoformat(k) for k in data["missing"]]
    if not found:
        fail("the Board's ENRS folder lists no results file since %s" % FIRST_DATE)
    return found, missing


def precinct_files(session, cache):
    """{day: (url, posted)} for every statewide precinct map since FIRST_DATE."""
    def make():
        _, files = list_folder(session, PRECINCT_FOLDER)
        out = {}
        for key, when in files.items():
            m = re.match(r"^ShapeFiles/Precinct/SBE_PRECINCTS_(\d{8})\.zip$", key)
            if m:
                day = datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
                if day >= FIRST_DATE:
                    out[day.isoformat()] = [PRECINCT_ZIP % m.group(1), when]
        return out
    data = cached_json(cache, "listing_precincts.json", make)
    out = {datetime.date.fromisoformat(k): tuple(v) for k, v in data.items()}
    if len(out) < 2:
        fail("the Board's precinct folder lists %d maps since %s" % (len(out), FIRST_DATE))
    return out


# --------------------------------------------------------------------------
# each board's school district website, from the CCD's district directory
# --------------------------------------------------------------------------

def ccd_websites(session, cache):
    """(file url, {LEAID: website as published}) for North Carolina, from the
    newest Local Education Agency directory file of NCES's Common Core of Data
    that its file listing names. The CCD keys a district by its NCES id, which
    is the Census GEOID this file carries, so the join needs no name."""
    def find():
        years = json.loads(get(session, CCD_API + "Lookup/").content).get("schoolYears") or []
        for year in sorted((y for y in years if y.get("id")), key=lambda y: -y["id"]):
            listing = json.loads(get(session, CCD_API + "File/2/5/%d/0/0/0" % year["id"]).content)
            urls = []

            def walk(node):
                if isinstance(node, dict):
                    if (node.get("component") == "Directory" and node.get("level") == "District"
                            and node.get("elementType") == "Data File"
                            and str(node.get("fileURL") or "").endswith(".zip")):
                        urls.append(node["fileURL"])
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for v in node:
                        walk(v)
            walk(listing.get("selectionGroupModels"))
            if urls:
                return sorted(set(urls))[-1]
        fail("NCES lists no Common Core of Data district directory file")

    def make():
        url = find()
        body = get(session, url).content
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if len(names) != 1:
                fail("%s holds %d CSV files, not one" % (url, len(names)))
            rows = csv.DictReader(io.TextIOWrapper(z.open(names[0]), encoding="latin-1"))
            sites = {r["LEAID"]: (r.get("WEBSITE") or "").strip() for r in rows
                     if r.get("FIPST") == STATE_FIPS}
        return {"url": url, "websites": sites}
    data = cached_json(cache, "ccd_lea_directory.json", make)
    if len(data["websites"]) < 110:
        fail("the CCD district directory lists %d North Carolina districts"
             % len(data["websites"]))
    return data["url"], data["websites"]


def check_website(session, gate, published):
    """{"published", "url"} for the page the published address answers with,
    or {"published", "why"} when it answers with none. Each redirect hop's
    host has its robots.txt read first; a host that refuses is not fetched and
    the board gets no link, which stops nothing else."""
    import socket  # noqa: PLC0415
    import urllib.parse  # noqa: PLC0415
    import requests  # noqa: PLC0415
    out = {"published": published}
    url = published
    if not url.lower().startswith(("http://", "https://")):
        out["why"] = "no website in the directory"
        return out
    for _hop in range(6):
        host = urllib.parse.urlsplit(url).hostname or ""
        try:
            socket.getaddrinfo(host, None)
        except socket.gaierror:
            out["why"] = "%s has no DNS record" % host
            return out
        ok, why = gate.allows(url)
        if not ok:
            out["why"] = "%s's robots.txt: %s" % (host, why)
            return out
        try:
            resp = session.get(url, headers=HEADERS, timeout=60, allow_redirects=False,
                               stream=True)
        except requests.RequestException as err:
            out["why"] = "%s: %s" % (type(err).__name__, str(err)[:160])
            return out
        try:
            if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
                url = urllib.parse.urljoin(url, resp.headers["Location"])
                continue
            kind = resp.headers.get("Content-Type") or ""
            if resp.status_code == 200 and "html" in kind.lower():
                out["url"] = url
            else:
                out["why"] = "%s answered HTTP %d (%s)" % (url, resp.status_code, kind or "no type")
            return out
        finally:
            resp.close()
            time.sleep(PACE_SECONDS)
    out["why"] = "%s redirected more than five times" % published
    return out


def board_websites(session, cache, geoids):
    """(directory file url, {geoid: check_website result}) for these boards."""
    import robots_policy  # noqa: PLC0415
    file_url, published = ccd_websites(session, cache)
    gate = robots_policy.RobotsGate(session, USER_AGENT, headers=HEADERS)
    out = {}
    for geoid in sorted(geoids):
        if geoid not in published:
            out[geoid] = {"published": None, "why": "not in the directory"}
            continue
        out[geoid] = check_website(session, gate, published[geoid])
    return file_url, out


# --------------------------------------------------------------------------
# which boards elect by district, and which of their seats are current
# --------------------------------------------------------------------------

def group_boards(contests):
    boards = {}
    for c in contests:
        key, party, unexp, seatno = parse_seat(c["seat_raw"])
        c.update(seat=key, party=party, unexpired=unexp, seatno=seatno)
        stem = board_stem(c["board"])
        b = boards.setdefault(stem, {"stem": stem, "names": {}, "contests": []})
        b["names"][c["day"]] = c["board"]
        b["contests"].append(c)
    return boards


def classify(board):
    """Each district-labelled seat's smallest share of its board's precincts,
    over the election days on which the board had at least two contests.

    A party primary only nominates, so it is left out: a board may nominate
    by district and elect at large (Carteret)."""
    electing = [c for c in board["contests"] if not c["party"]]
    byday = collections.defaultdict(lambda: collections.defaultdict(set))
    for c in electing:
        byday[c["day"]][c["seat"]] |= {(c["county"], x) for x in c["codes"]}
    share = {}
    for day, seats in byday.items():
        if len(seats) < 2:
            continue
        union = set().union(*seats.values())
        for s, codes in seats.items():
            if AT_LARGE.match(s) or not union:
                continue
            share[s] = min(share.get(s, 9.0), len(codes) / float(len(union)))
    labelled = {c["seat"] for c in electing if not AT_LARGE.match(c["seat"])}
    district = sorted(s for s, v in share.items() if v < SHARE_CEILING)
    residency = sorted(s for s, v in share.items() if v >= SHARE_CEILING)
    undecided = sorted(labelled - set(share))
    days = sorted({c["day"] for c in electing})
    return {"district": district, "residency": residency, "undecided": undecided,
            "share": share, "days": days, "electing": electing}


def cycle_years(cls):
    """The board's two most recent election years, counting only years with a
    regular contest (an unexpired-term contest fills a vacancy off-cycle)."""
    years = sorted({c["day"].year for c in cls["electing"] if not c["unexpired"]})
    return years[-2:]


def check_overlay(title, base, top, ground):
    """{overlay seat: [the districts inside it]}, failing unless every overlay
    seat is (nearly) the union of two or more of the board's districts and
    every district lies in exactly one overlay seat."""
    from shapely.ops import unary_union  # noqa: PLC0415
    within = {}
    if not top:
        return within
    homes = collections.Counter()
    for t in top:
        mine = ground[t["key"]]
        inside = [b["key"] for b in base if ground[b["key"]].area > 0 and
                  ground[b["key"]].intersection(mine).area >= OVERLAY_INSIDE * ground[b["key"]].area]
        cover = unary_union([ground[k] for k in inside]).intersection(mine).area if inside else 0.0
        if len(inside) < 2 or mine.area <= 0 or cover < OVERLAY_INSIDE * mine.area:
            fail("%s %s is named as a consolidated district and is not the union of two "
                 "or more of the board's districts (%s inside it, covering %.0f%% of it)"
                 % (title, display(t["key"]), [display(k) for k in inside],
                    100 * cover / mine.area if mine.area else 0))
        within[t["key"]] = sorted(inside, key=natural)
        homes.update(inside)
    for b in base:
        if homes[b["key"]] != 1:
            fail("%s %s lies in %d consolidated districts, not exactly one"
                 % (title, display(b["key"]), homes[b["key"]]))
    return within


def current_seats(cls):
    """The district seats elected in the board's two most recent election
    years — a full cycle of four-year terms — with each one's latest contest."""
    first = min(cycle_years(cls))
    cycle = {d for d in cls["days"] if d.year >= first}
    seats, old = [], []
    for s in cls["district"]:
        mine = [c for c in cls["electing"] if c["seat"] == s]
        latest = max(c["day"] for c in mine)
        group = [c for c in mine if c["day"] == latest]
        rec = {"key": s, "day": latest, "codes": collections.defaultdict(set),
               "contests": sorted({c["name"] for c in group}),
               "unexpired": all(c["unexpired"] for c in group),
               "earlier": sorted({c["day"] for c in mine if c["day"] < latest})}
        for c in group:
            rec["codes"][c["county"]] |= c["codes"]
        (seats if latest in cycle else old).append(rec)
    at_large = any(c["day"] in cycle and (AT_LARGE.match(c["seat"]) or c["seat"] in cls["residency"])
                   for c in cls["electing"])
    return seats, old, at_large


# --------------------------------------------------------------------------
# drawing one board
# --------------------------------------------------------------------------

class Board:
    """One board's contests turned into ground, in metres about its own
    latitude."""

    def __init__(self, vint, reported, school, sx, sy):
        self.vint = vint
        self.reported = reported
        self.sx, self.sy = sx, sy
        self.school = school
        self.missing = []        # (day, county, code, seats) the maps do not hold
        self.choice = {}         # (day, county) -> (map day, agreement)
        self._m = {}

    def shape_m(self, day, county, code):
        key = (day, county, code)
        if key not in self._m:
            self._m[key] = to_m(self.vint.shape(day, county, code), self.sx, self.sy)
        return self._m[key]

    def vintage(self, day, county):
        key = (day, county)
        if key not in self.choice:
            codes = self.reported[day].get(county, set())
            self.choice[key] = self.vint.choose(day, county, codes)
        return self.choice[key][0]

    def contest_grounds(self, electing):
        """{(day, seat): ground} for every electing contest of the board, each
        county's precincts read in that county's map for that day and cut to
        the school district."""
        from shapely.ops import unary_union  # noqa: PLC0415
        codes = collections.defaultdict(lambda: collections.defaultdict(set))
        for c in electing:
            codes[(c["day"], c["seat"])][c["county"]] |= c["codes"]
        out = {}
        for (day, seat), per in codes.items():
            parts = []
            for county, cs in per.items():
                v = self.vintage(day, county)
                if v is None:
                    continue
                have = self.vint.codes[v].get(county, ())
                parts += [self.shape_m(v, county, code) for code in cs if code in have]
            out[(day, seat)] = (polygonal(unary_union(parts).intersection(self.school))
                                if parts else polygonal(None))
        return out

    def items(self, seats):
        """One item per seat's own ground and one per precinct two or more
        seats of the same election share, every one cut to the school
        district."""
        from shapely.ops import unary_union  # noqa: PLC0415
        out = []
        byday = collections.defaultdict(list)
        for s in seats:
            byday[s["day"]].append(s)
        for day, group in sorted(byday.items()):
            per_code = collections.defaultdict(list)
            for s in group:
                for county, codes in s["codes"].items():
                    for code in codes:
                        per_code[(county, code)].append(s["key"])
            own = collections.defaultdict(list)
            for (county, code), keys in sorted(per_code.items()):
                v = self.vintage(day, county)
                if v is None or code not in self.vint.codes[v].get(county, ()):
                    self.missing.append((day, county, code, sorted(keys)))
                    continue
                g = self.shape_m(v, county, code)
                if len(keys) == 1:
                    own[keys[0]].append(g)
                else:
                    out.append({"claims": [{"day": day, "seats": sorted(keys, key=natural),
                                            "precinct": self.vint.name(v, county, code)}],
                                "geom": g})
            for key, gs in sorted(own.items()):
                out.append({"claims": [{"day": day, "seats": [key]}], "geom": unary_union(gs)})
        for it in out:
            it["geom"] = polygonal(it["geom"].intersection(self.school))
        return [it for it in out if not it["geom"].is_empty]

    def resolve(self, items):
        """Lay the items down newest election first. Where an older item
        overlaps a newer one, a strip narrower than 2 x SLIVER_M is where the
        two elections' precinct maps draw one line a little apart, and stays
        with the newer; anything wider, of at least MIN_OVERLAP_KM2, is ground
        the two elections put in different districts, and becomes an overlap
        naming both."""
        from shapely.ops import unary_union  # noqa: PLC0415
        placed = []
        drift = 0.0
        for it in sorted(items, key=lambda i: max(c["day"] for c in i["claims"]), reverse=True):
            g = it["geom"]
            day = max(c["day"] for c in it["claims"])
            for p in list(placed):
                if g.is_empty:
                    break
                if not g.intersects(p["geom"]):
                    continue
                inter = polygonal(g.intersection(p["geom"]))
                if inter.is_empty or inter.area <= 0:
                    continue
                pday = max(c["day"] for c in p["claims"])
                thick = opening(inter, SLIVER_M) if pday != day else polygonal(None)
                if not thick.is_empty and area_km2(thick) >= MIN_OVERLAP_KM2:
                    placed.append({"claims": p["claims"] + it["claims"], "geom": thick})
                    p["geom"] = polygonal(p["geom"].difference(thick))
                    drift += inter.area - thick.area
                else:
                    drift += inter.area
                g = polygonal(g.difference(inter))
            it["geom"] = g
            if not g.is_empty:
                placed.append(it)
        placed = [p for p in placed if not p["geom"].is_empty]
        union = unary_union([p["geom"] for p in placed]) if placed else polygonal(None)
        return placed, union, drift

    def unplaced(self, day, touch, residual, grounds):
        """[(contests on the ballot there, ground, precinct names)]: the
        residual ground split by which of the board's contests since
        FIRST_DATE were on the ballot there, read precinct by precinct in the
        newest map."""
        from shapely.ops import unary_union  # noqa: PLC0415
        groups = collections.defaultdict(list)
        for county, code in touch:
            piece = polygonal(self.shape_m(day, county, code).intersection(residual))
            if piece.is_empty or piece.area <= 0:
                continue
            sig = tuple(sorted(
                (k for k, g in grounds.items() if not g.is_empty and g.intersects(piece) and
                 g.intersection(piece).area >= VOTED_SHARE * piece.area),
                key=lambda k: (k[0], natural(k[1]))))
            groups[sig].append((county, self.vint.name(day, county, code), piece))
        out = []
        for sig, rows in sorted(groups.items()):
            geom = opening(unary_union([r[2] for r in rows]), SLIVER_M)
            if geom.is_empty:
                continue
            # the precincts holding at least a hectare, or a quarter, of it
            share = [(piece.intersection(geom).area, county, name) for county, name, piece in rows]
            names = sorted({"%s (%s County)" % (name, county_title(county))
                            for a, county, name in share
                            if a >= min(1e4, 0.25 * geom.area)})
            out.append((sig, geom, names))
        return out


# --------------------------------------------------------------------------
# the build
# --------------------------------------------------------------------------

def load_inputs(session, cache):
    found, missing = election_files(session, cache)
    contests, reported = [], {}
    for day, (url, _posted) in sorted(found.items()):
        body = cached(cache, os.path.basename(url), lambda u=url: get(session, u).content)
        cs, pr = read_results(day, body)
        contests += cs
        reported[day] = pr
    maps = {}
    files = precinct_files(session, cache)
    for day, (url, _posted) in sorted(files.items()):
        stamp = day.strftime("%Y%m%d")
        gj = os.path.join(cache, "SBE_PRECINCTS_%s.geojson" % stamp) if cache else None
        if gj and os.path.exists(gj):
            maps[day] = precinct_geojson(cache, stamp, None)
            continue
        body = cached(cache, os.path.basename(url), lambda u=url: get(session, u).content)
        maps[day] = precinct_geojson(cache, stamp, body)
    return found, missing, files, contests, reported, Vintages(maps)


def claims_rows(claims, found, today):
    rows = []
    for c in sorted(claims, key=lambda c: c["day"], reverse=True):
        row = {"election": c["day"].isoformat(), "seats": [display(k) for k in c["seats"]],
               "sourceUrl": found[c["day"]][0]}
        if c["day"] > today:
            row["posted"] = found[c["day"]][1][:10]
        if c.get("precinct"):
            row["precinct"] = c["precinct"]
        if row not in rows:
            rows.append(row)
    return rows


def build(today, cache, verbose=False):
    import requests  # noqa: PLC0415
    from shapely.geometry import Polygon, mapping, shape  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    session = requests.Session()
    found, missing_days, map_files, contests, reported, vint = load_inputs(session, cache)
    print("results files read: %s" % ", ".join(d.isoformat() for d in sorted(found)))
    for day in sorted(found):
        if day > today:
            print("  %s has not been held yet: its file, posted %s, carries the ballot's "
                  "contests and precincts with no votes" % (day, found[day][1][:10]))
    if missing_days:
        print("dated results folders with no precinct-level file: %s"
              % ", ".join(d.isoformat() for d in missing_days))
    print("precinct maps read: %s" % ", ".join(
        "%s (posted %s)" % (d.isoformat(), map_files[d][1][:10]) for d in vint.days))
    schools = tiger_names(session, cache)
    boards = group_boards(contests)

    tally = collections.Counter()
    drawn = []
    renamed = []
    largest_district, smallest_residency = 0.0, 9.0
    for stem, b in sorted(boards.items()):
        cls = classify(b)
        name = b["names"][max(b["names"])]
        names = sorted(set(b["names"].values()))
        if len(names) > 1:
            renamed.append((stem, [(min(d for d, n in b["names"].items() if n == x), x) for x in names]))
        if not cls["district"] and not cls["residency"] and not cls["undecided"]:
            tally["at large"] += 1
            continue
        for s in cls["district"]:
            largest_district = max(largest_district, cls["share"][s])
        for s in cls["residency"]:
            smallest_residency = min(smallest_residency, cls["share"][s])
        if not cls["district"]:
            tally["district-labelled, voted on everywhere"] += 1
            print("not drawn: %s — every precinct votes on each of its district-labelled "
                  "seats (%s)" % (board_title(name), ", ".join(display(s) for s in cls["residency"])))
            if cls["undecided"]:
                print("  and %s never shared an election day with another of its contests"
                      % ", ".join(display(s) for s in cls["undecided"]))
            continue
        tally["by district"] += 1
        seats, old, at_large = current_seats(cls)
        for s in old:
            print("not drawn: %s %s — last elected %s, not on the board's ballots in %s"
                  % (board_title(name), display(s["key"]), s["day"],
                     " or ".join(str(y) for y in cycle_years(cls))))
        if cls["undecided"]:
            print("not drawn: %s %s — never shared an election day with another of its "
                  "contests, so its share cannot be measured"
                  % (board_title(name), ", ".join(display(s) for s in cls["undecided"])))
        target = SCHOOL_ALIAS.get(stem, stem)
        if target not in schools:
            fail("%s elects by district and no Census school district is named %r"
                 % (board_title(name), target))
        drawn.append((stem, name, schools[target], seats, cls, at_large))
    print("boards in the results since %s: %d — %s" % (
        FIRST_DATE.year, sum(tally.values()),
        ", ".join("%s %d" % (k, v) for k, v in sorted(tally.items()))))
    print("a district seat's largest share of its board's precincts: %.3f; a seat voted on "
          "everywhere, its smallest: %.3f (SHARE_CEILING %.2f)"
          % (largest_district, smallest_residency, SHARE_CEILING))
    for stem, rows in renamed:
        print("board named differently in different results: %s" % "; ".join(
            "%s from %s" % (board_title(n), d) for d, n in sorted(rows)))

    collection = {"type": "FeatureCollection", "features": []}
    enclaves = {}
    report = []
    choices = {}
    totals = collections.Counter()
    moved_boards = []
    pieces_only, nowhere, small = [], [], []
    for stem, name, (geoid, school_name), seats, cls, at_large in drawn:
        title = board_title(name)
        feat = fetch_school(session, cache, geoid)
        school_deg = shape(feat["geometry"])
        if not school_deg.is_valid:
            school_deg = school_deg.buffer(0)
        for part in parts_of(school_deg):
            for ring in part.interiors:
                rp = Polygon(ring).representative_point()
                enclaves.setdefault(geoid, []).append([round(rp.y, 6), round(rp.x, 6)])
        sx, sy = local_scale(school_deg)
        school = to_m(school_deg, sx, sy)
        bd = Board(vint, reported, school, sx, sy)
        grounds = bd.contest_grounds(cls["electing"])
        ground = {s["key"]: grounds[(s["day"], s["key"])] for s in seats}
        overlay = {s["key"] for s in seats if s["key"].startswith(OVERLAY_WORD)}
        base = [s for s in seats if s["key"] not in overlay]
        top = [s for s in seats if s["key"] in overlay]
        within = check_overlay(title, base, top, ground)
        placed, union, drift = bd.resolve(bd.items(base))
        placed_top = []
        if top:
            placed_top, _u, drift_top = bd.resolve(bd.items(top))
            drift += drift_top
        thin_n, thin_m2 = drop_thin(placed)
        if placed_top:
            n, a = drop_thin(placed_top)
            thin_n += n
            thin_m2 += a
        placed = [it for it in placed if not it["geom"].is_empty]
        placed_top = [it for it in placed_top if not it["geom"].is_empty]
        for it in placed + placed_top:
            if it["geom"].area < SMALL_PIECE_M2:
                small.append("%s, %s: %.0f m2" % (title, "; ".join(
                    "%s %s" % (c["day"], " and ".join(display(k) for k in c["seats"]))
                    for c in sorted(it["claims"], key=lambda c: c["day"], reverse=True)),
                    it["geom"].area))
        union = unary_union([it["geom"] for it in placed]) if placed else polygonal(None)
        # a seat whose own ground is all taken by newer elections' districts or
        # shared with another seat is named only on those pieces
        alone = {it["claims"][0]["seats"][0] for it in placed + placed_top
                 if len(it["claims"]) == 1 and len(it["claims"][0]["seats"]) == 1}
        named = {k for it in placed + placed_top for c in it["claims"] for k in c["seats"]}
        for s in seats:
            if s["key"] in alone:
                continue
            totals["no_own"] += 1
            pieces_only.append("%s %s (%s)" % (title, display(s["key"]), s["day"]))
            if s["key"] not in named:
                totals["nowhere"] += 1
                nowhere.append("%s %s (%s)" % (title, display(s["key"]), s["day"]))
        # ground no current seat places, counted only where some precinct of
        # the newest map lies: ground of the school district outside every
        # precinct is on nobody's ballot, and is measured on its own
        newest = vint.days[-1]
        touch = vint.touching(newest, school_deg)
        fabric = unary_union([bd.shape_m(newest, c, code) for c, code in touch])
        covered = school.intersection(fabric)
        outside = polygonal(school.difference(fabric))
        totals["outside_m2"] += outside.area
        totals["outside_wide_m2"] += sum(q.area for q in parts_of(outside)
                                         if not q.buffer(-SLIVER_M).is_empty)
        residual = polygonal(covered.difference(union))
        unplaced = []
        if not opening(residual, SLIVER_M).is_empty:
            unplaced = bd.unplaced(newest, touch, residual, grounds)
        coverage = union.area / covered.area if covered.area else 0.0

        # a seat on different ground in its latest election than in the one before
        moved = []
        for s in seats:
            if not s["earlier"]:
                continue
            a, b = grounds[(s["day"], s["key"])], grounds[(s["earlier"][-1], s["key"])]
            diff = opening(polygonal(a.symmetric_difference(b)), SLIVER_M)
            if area_km2(diff) >= MOVED_KM2 and diff.area >= MOVED_SHARE * max(a.area, b.area):
                moved.append("%s %s to %s (%.1f km2)" % (display(s["key"]), s["earlier"][-1],
                                                         s["day"], area_km2(diff)))
        if moved:
            moved_boards.append((title, moved))

        by_seat = {s["key"]: s for s in seats}
        n_split = n_overlap = 0
        for tier, items in (("base", placed), ("overlay", placed_top)):
            for it in items:
                g = valid(to_deg(it["geom"], sx, sy))
                props = {"geoid": geoid, "school": school_name, "board": title}
                if tier == "overlay":
                    props["tier"] = "overlay"
                    props["within"] = [display(k) for k in sorted(
                        set().union(*(within[k] for c in it["claims"] for k in c["seats"])),
                        key=natural)]
                days = sorted({c["day"] for c in it["claims"]}, reverse=True)
                if len(it["claims"]) == 1 and len(it["claims"][0]["seats"]) == 1:
                    s = by_seat[it["claims"][0]["seats"][0]]
                    props.update({"kind": "district", "seat": display(s["key"]),
                                  "election": s["day"].isoformat(),
                                  "contest": s["contests"][0],
                                  "sourceUrl": found[s["day"]][0]})
                    if s["day"] > today:
                        props["posted"] = found[s["day"]][1][:10]
                    if s["unexpired"]:
                        props["unexpired"] = True
                elif len(days) == 1 and len(it["claims"]) == 1:
                    c = it["claims"][0]
                    n_split += 1
                    props.update({"kind": "split", "seats": [display(k) for k in c["seats"]],
                                  "precinct": c["precinct"], "election": c["day"].isoformat(),
                                  "sourceUrl": found[c["day"]][0]})
                    if c["day"] > today:
                        props["posted"] = found[c["day"]][1][:10]
                else:
                    n_overlap += 1
                    props.update({"kind": "overlap",
                                  "claims": claims_rows(it["claims"], found, today)})
                if at_large:
                    props["atLarge"] = True
                collection["features"].append({"type": "Feature", "properties": props,
                                               "geometry": mapping(g)})
        un_km2 = no_ballot_km2 = 0.0
        for sig, geom, names in unplaced:
            if geom.area < SMALL_PIECE_M2:
                small.append("%s, not placed: %.0f m2" % (title, geom.area))
            props = {"geoid": geoid, "school": school_name, "board": title, "kind": "unplaced",
                     "cycle": cycle_years(cls)}
            if sig:
                byday = collections.defaultdict(list)
                for day, seat in sig:
                    byday[day].append(seat)
                props["votedIn"] = [{"election": d.isoformat(),
                                     "seats": [display(k) for k in sorted(v, key=natural)]}
                                    for d, v in sorted(byday.items(), reverse=True)]
            else:
                props["precincts"] = names
                no_ballot_km2 += area_km2(geom)
            un_km2 += area_km2(geom)
            if at_large:
                props["atLarge"] = True
            collection["features"].append({"type": "Feature", "properties": props,
                                           "geometry": mapping(valid(to_deg(geom, sx, sy)))})
        for key, val in bd.choice.items():
            choices.setdefault(key, val)
        totals.update({"boards": 1, "districts": len(base), "overlay": len(top),
                       "split": n_split, "overlap": n_overlap, "unplaced": len(unplaced)})
        totals["unplaced_m2"] += un_km2 * 1e6
        totals["no_ballot_m2"] += no_ballot_km2 * 1e6
        totals["drift_m2"] += drift
        totals["thin"] += thin_n
        totals["thin_m2"] += thin_m2
        left = polygonal(residual.difference(unary_union([g for _s, g, _n in unplaced])))\
            if unplaced else residual
        left_m2 = left.area
        totals["left_m2"] += left_m2
        # measured, not assumed: what is left should all be strips
        totals["left_wide_m2"] += sum(q.area for q in parts_of(left)
                                      if not q.buffer(-SLIVER_M).is_empty)
        miss = sorted({"%s %s" % (c, code) for d, c, code, k in bd.missing})
        report.append(
            "%s (%s, %s): %d districts%s, %d split precinct(s), %d overlap piece(s), "
            "%.2f km2 not placed%s, %.0f%% of the ground placed, %.0f m2 of map drift, "
            "%d thin piece(s) of %.0f m2 dropped, %.0f m2 on no piece%s"
            % (title, school_name, geoid, len(base),
               (" + %d over them (%s)" % (len(top), ", ".join(display(k) for k in sorted(overlay))))
               if top else "", n_split, n_overlap, un_km2,
               (" (%.2f km2 of it on none of the board's ballots)" % no_ballot_km2)
               if no_ballot_km2 else "",
               100 * coverage, drift, thin_n, thin_m2, left_m2,
               ("; precinct codes no map holds: %s" % ", ".join(miss)) if miss else ""))
        if verbose:
            for tier, items in (("base", placed), ("overlay", placed_top)):
                for it in items:
                    if len(it["claims"]) > 1:
                        print("   overlap %s %.3f km2 %s" % (tier, area_km2(it["geom"]), [
                            (c["day"].isoformat(), [display(k) for k in c["seats"]],
                             c.get("precinct")) for c in it["claims"]]))
            for sig, geom, names in unplaced:
                print("   unplaced %.3f km2 %s %s" % (area_km2(geom), [
                    (d.isoformat(), display(k)) for d, k in sig], names if not sig else ""))
            for s in seats:
                print("   %-24s %s %s" % (display(s["key"]), s["day"],
                                         {c: bd.vintage(s["day"], c).isoformat() for c in s["codes"]}))
    for line in report:
        print("  " + line)
    for title, moved in moved_boards:
        print("seats on different ground than in their election before: %s — %s"
              % (title, "; ".join(moved)))
    later = sorted("%s %s in the map of %s" % (d, county_title(c), v)
                   for (d, c), (v, score) in choices.items() if v is not None and v > d)
    weak = sorted("%s %s (map of %s holds %.1f%% of them)" % (d, county_title(c), v, 100 * held)
                  for (d, c), (v, held) in choices.items() if v is not None and held < 1.0)
    print("elections and counties read: %d; in a map dated after the election: %d%s"
          % (len(choices), len(later), (" (" + "; ".join(later) + ")") if later else ""))
    print("elections and counties with precinct codes no map holds: %d%s"
          % (len(weak), (" (" + "; ".join(weak) + ")") if weak else ""))
    print("seats with no ground of their own, named only on split or overlap pieces: %d (%s)"
          % (totals["no_own"], "; ".join(pieces_only)))
    if nowhere:
        print("seats named on no piece at all: %d (%s)" % (totals["nowhere"], "; ".join(nowhere)))
    print("map drift given to the newer election: %.2f km2; thin pieces dropped: %d of %.2f km2; "
          "ground in a board's school district and the newest precinct map on no piece: %.2f km2, "
          "%.0f m2 of it in parts %d m wide somewhere"
          % (totals["drift_m2"] / 1e6, totals["thin"], totals["thin_m2"] / 1e6,
             totals["left_m2"] / 1e6, totals["left_wide_m2"], 2 * SLIVER_M))
    print("pieces smaller than %.0f m2: %d (%s)" % (SMALL_PIECE_M2, len(small), "; ".join(small)))
    print("ground in a board's school district outside every precinct of the newest map: "
          "%.2f km2, %.0f m2 of it in parts %d m wide somewhere"
          % (totals["outside_m2"] / 1e6, totals["outside_wide_m2"], 2 * SLIVER_M))
    print("drawn: %d boards, %d districts + %d over them, %d split precinct(s), %d overlap "
          "piece(s), %d unplaced piece(s) of %.2f km2 (%.2f km2 on none of a board's ballots)"
          % (totals["boards"], totals["districts"], totals["overlay"], totals["split"],
             totals["overlap"], totals["unplaced"], totals["unplaced_m2"] / 1e6,
             totals["no_ballot_m2"] / 1e6))
    ccd_url, sites = board_websites(
        session, cache, {f["properties"]["geoid"] for f in collection["features"]})
    for f in collection["features"]:
        site = sites[f["properties"]["geoid"]].get("url")
        if site:
            f["properties"]["website"] = site
    school_of = {f["properties"]["geoid"]: f["properties"]["school"]
                 for f in collection["features"]}
    unlinked = ["%s (%s)" % (school_of[g], r["why"]) for g, r in sorted(sites.items())
                if not r.get("url")]
    print("school district websites, from %s: %d of %d boards linked, every one answering "
          "with a page after robots.txt was read at each redirect; not linked: %d%s"
          % (ccd_url, len(sites) - len(unlinked), len(sites), len(unlinked),
             (" (" + "; ".join(unlinked) + ")") if unlinked else ""))
    record = {"built": today.isoformat(),
              "results": {d.isoformat(): found[d][1] for d in sorted(found)},
              "results_missing": [d.isoformat() for d in missing_days],
              "maps": {d.isoformat(): map_files[d][1] for d in sorted(map_files)},
              "enclaves": enclaves,
              "ccd": ccd_url,
              "websites": sites}
    return collection, record


def simplify_shared(collection):
    """One mapshaper pass over the whole set, so a border two features share
    is one arc simplified once."""
    if not shutil.which("npx"):
        fail("npx is not on PATH; this builder simplifies through mapshaper")
    work = tempfile.mkdtemp(prefix="nc-sbd-")
    try:
        src = os.path.join(work, "exact.json")
        dst = os.path.join(work, "simple.json")
        with open(src, "w") as handle:
            json.dump(collection, handle, separators=(",", ":"))
        proc = subprocess.run(
            ["npx", "--yes", MAPSHAPER, src,
             "-simplify", "dp", "interval=%d" % SIMPLIFY_INTERVAL_M, "keep-shapes",
             "-o", "precision=0.000001", dst],
            capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(dst):
            fail("mapshaper failed (%d): %s" % (proc.returncode, (proc.stderr or "")[-800:]))
        with open(dst) as handle:
            out = json.load(handle)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if len(out.get("features") or []) != len(collection["features"]):
        fail("mapshaper returned %d features for %d"
             % (len(out.get("features") or []), len(collection["features"])))
    return out


# --------------------------------------------------------------------------
# the rules the shipped file keeps
# --------------------------------------------------------------------------

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RESULTS_URL = re.compile(r"^https://dl\.ncsbe\.gov/ENRS/\d{4}_\d{2}_\d{2}/results_pct_\d{8}\.zip$")


def gates(out, enclaves, websites):
    """Every rule the shipped file must keep, offline. `enclaves` is
    {geoid: [[lat, lng], ...]}, a point inside each hole of a school district's
    own Census outline (another district's ground), and `websites` is
    {geoid: check_website result}, both from the build record."""
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.strtree import STRtree  # noqa: PLC0415
    problems = []
    feats = out.get("features") or []
    boards = collections.defaultdict(list)
    seats = set()
    district_feats = collections.Counter()
    base_seats = collections.defaultdict(set)
    for f in feats:
        p = f.get("properties") or {}
        kind = p.get("kind")
        geoid = str(p.get("geoid") or "")
        tier = p.get("tier") or "base"
        where = "%s %s" % (p.get("school"), p.get("seat") or kind)
        if not re.match(r"^37\d{5}$", geoid):
            problems.append("%s: GEOID %r is not a North Carolina school district's" % (where, geoid))
        if not p.get("school") or not p.get("board"):
            problems.append("%s: no school district or board name" % where)
        if tier not in ("base", "overlay"):
            problems.append("%s: unknown tier %r" % (where, tier))
        if (f.get("geometry") or {}).get("type") not in ("Polygon", "MultiPolygon"):
            problems.append("%s: geometry is not a polygon" % where)
        if kind == "district":
            if not p.get("seat") or not ISO.match(str(p.get("election") or "")):
                problems.append("%s: a district with no seat or no election date" % where)
            if not RESULTS_URL.match(str(p.get("sourceUrl") or "")):
                problems.append("%s: source %r is not a State Board results file"
                                % (where, p.get("sourceUrl")))
            seats.add((geoid, tier, p.get("seat")))
            district_feats[(geoid, tier, p.get("seat"))] += 1
            if tier == "base":
                base_seats[geoid].add(p.get("seat"))
        elif kind == "split":
            if len(set(p.get("seats") or [])) < 2 or not p.get("precinct"):
                problems.append("%s: a split precinct naming fewer than two seats or no "
                                "precinct" % where)
            if not ISO.match(str(p.get("election") or "")) or \
                    not RESULTS_URL.match(str(p.get("sourceUrl") or "")):
                problems.append("%s: a split precinct with no election or source" % where)
            seats.update((geoid, tier, s) for s in p.get("seats") or [])
            if tier == "base":
                base_seats[geoid].update(p.get("seats") or [])
        elif kind == "overlap":
            claims = p.get("claims") or []
            if len(claims) < 2 or len({c.get("election") for c in claims}) < 2:
                problems.append("%s: an overlap naming fewer than two elections" % where)
            for c in claims:
                if not c.get("seats") or not ISO.match(str(c.get("election") or "")) or \
                        not RESULTS_URL.match(str(c.get("sourceUrl") or "")):
                    problems.append("%s: an overlap claim with no seat, election or source: %r"
                                    % (where, c))
                seats.update((geoid, tier, s) for s in c.get("seats") or [])
                if tier == "base":
                    base_seats[geoid].update(c.get("seats") or [])
        elif kind == "unplaced":
            if tier != "base":
                problems.append("%s: unplaced ground on the overlay tier" % where)
            cycle = p.get("cycle") or []
            if len(cycle) not in (1, 2) or not all(isinstance(y, int) for y in cycle):
                problems.append("%s: unplaced ground with no election years" % where)
            voted = p.get("votedIn")
            if voted:
                for v in voted:
                    if not ISO.match(str(v.get("election") or "")) or not v.get("seats"):
                        problems.append("%s: a votedIn row with no election or seat: %r"
                                        % (where, v))
            elif not p.get("precincts"):
                problems.append("%s: unplaced ground on no ballot names no precinct" % where)
        else:
            problems.append("%s: a feature of unknown kind %r" % (where, kind))
        boards[geoid].append(f)
    for key, n in district_feats.items():
        if n > 1:
            problems.append("%s %s: seat %s is drawn as %d district features" % (key[0], key[1], key[2], n))
    for f in feats:
        p = f["properties"]
        if p.get("tier") == "overlay":
            inside = p.get("within") or []
            if len(inside) < 2 or not set(inside) <= base_seats[str(p.get("geoid"))]:
                problems.append("%s %s: an overlay district over %r, which are not two or more "
                                "of the board's districts" % (p.get("school"), p.get("seat"), inside))
    # no point inside one feature is inside another of the same tier, on any board
    stats = collections.Counter()
    for tier in ("base", "overlay"):
        # a simplified outline can touch itself where mapshaper moved two of
        # its vertices together; it is measured as GEOS repairs it
        raw = [(f["properties"], shape(f["geometry"])) for f in feats
               if (f["properties"].get("tier") or "base") == tier and
               (f.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")]
        stats["self_touching"] += sum(1 for _p, g in raw if not g.is_valid)
        shapes = [(p, valid(g)) for p, g in raw]
        tree = STRtree([g for _p, g in shapes])
        for i, (pa, ga) in enumerate(shapes):
            if ga.is_empty or ga.area <= 0:
                problems.append("%s %s: an empty geometry" % (pa.get("school"),
                                                              pa.get("seat") or pa.get("kind")))
                continue
            pt = ga.representative_point()
            hits = [shapes[j][0] for j in tree.query(pt) if j != i and shapes[j][1].contains(pt)]
            if hits:
                problems.append("%s: a point inside %s is also inside %s"
                                % (pa.get("school"), pa.get("seat") or pa.get("kind"),
                                   ["%s %s" % (h.get("school"), h.get("seat") or h.get("kind"))
                                    for h in hits]))
        # where two pieces of one tier cross, and by how much
        crossings = 0
        for i, (pa, ga) in enumerate(shapes):
            for j in tree.query(ga):
                if j <= i or not ga.intersects(shapes[j][1]):
                    continue
                inter = polygonal(ga.intersection(shapes[j][1]))
                if inter.is_empty:
                    continue
                sx, sy = local_scale(inter)
                m2 = inter.area * sx * sy
                if m2 < 0.01:
                    continue
                crossings += 1
                stats["crossing_m2"] += m2
                stats["worst_m2"] = max(stats["worst_m2"], m2)
                if m2 > MAX_CROSSING_M2:
                    problems.append("%s %s and %s cross over %.0f m2, more than the shared "
                                    "simplification moves a line (ceiling %.0f m2)"
                                    % (pa.get("school"), pa.get("seat") or pa.get("kind"),
                                       shapes[j][0].get("seat") or shapes[j][0].get("kind"),
                                       m2, MAX_CROSSING_M2))
        stats["crossings"] += crossings
    # the holes between one board's pieces, and the widest of them
    from shapely.geometry import Point, Polygon  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415
    import shapely  # noqa: PLC0415
    for geoid, fs in sorted(boards.items()):
        gs = [valid(shape(f["geometry"])) for f in fs
              if (f["properties"].get("tier") or "base") == "base" and
              (f.get("geometry") or {}).get("type") in ("Polygon", "MultiPolygon")]
        if not gs:
            continue
        u = polygonal(unary_union(gs))
        sx, sy = local_scale(u)
        um = to_m(u, sx, sy)
        inner = [h for part in parts_of(um) for h in part.interiors]
        enclave = enclaves.get(geoid, [])
        for ring in inner:
            # a piece can lie inside a hole as an island; it is not the hole
            for hole in parts_of(polygonal(Polygon(ring).difference(um))):
                if any(hole.contains(Point(lng * sx, lat * sy)) for lat, lng in enclave):
                    continue  # the school district's own hole, another district's ground
                stats["holes"] += 1
                stats["hole_m2"] += hole.area
                if hole.area < math.pi * SLIVER_M ** 2:
                    continue  # too small to hold a circle 2 x SLIVER_M across
                wide = 2 * shapely.maximum_inscribed_circle(hole, 0.5).length
                if wide > stats["widest_hole_m"]:
                    stats["widest_hole_m"] = wide
                if wide > MAX_HOLE_M:
                    rp = hole.representative_point()
                    problems.append("%s: a hole between its pieces %.1f m wide at %.5f,%.5f "
                                    "(ceiling %.0f m)" % (fs[0]["properties"].get("school"), wide,
                                                          rp.y / sy, rp.x / sx, MAX_HOLE_M))
    nseats = len({s for s in seats if s[1] == "base"})
    if len(boards) < MIN_BOARDS:
        problems.append("%d boards drawn, floor %d" % (len(boards), MIN_BOARDS))
    if nseats < MIN_SEATS:
        problems.append("%d district seats drawn, floor %d" % (nseats, MIN_SEATS))
    stats["boards"], stats["seats"] = len(boards), nseats
    # every feature carries its board's website exactly as the build checked it
    websites = websites or {}
    for geoid, fs in sorted(boards.items()):
        rec = websites.get(geoid)
        if not isinstance(rec, dict) or ("url" in rec) == ("why" in rec):
            problems.append("%s: the build record has no website result for its board"
                            % fs[0]["properties"].get("school"))
            continue
        want = rec.get("url")
        if want is not None and not re.match(r"^https?://[^\s/]+\.[^\s]+$", want):
            problems.append("%s: website %r is not an address" % (geoid, want))
        got = {f["properties"].get("website") for f in fs}
        if got != {want}:
            problems.append("%s: its features carry website(s) %r, the build record %r"
                            % (fs[0]["properties"].get("school"), sorted(map(str, got)), want))
        stats["websites"] += 1 if want else 0
    return problems, stats


def agreement(exact, simple):
    """(points that land in their own piece after the shared simplification,
    points sampled, points that land in two or more pieces of their tier):
    AGREEMENT_PER_PIECE points drawn at random inside every exact piece, each
    asked which simplified pieces of its tier hold it. A point held by its
    own piece and another counts as a miss."""
    import random  # noqa: PLC0415
    from shapely.geometry import Point, shape  # noqa: PLC0415
    from shapely.prepared import prep  # noqa: PLC0415
    from shapely.strtree import STRtree  # noqa: PLC0415
    rng = random.Random(20261017)
    simple_g = [shape(f["geometry"]) for f in simple["features"]]
    tiers = [(f["properties"].get("tier") or "base") for f in simple["features"]]
    tree = STRtree(simple_g)
    hit = total = double = 0
    for i, f in enumerate(exact["features"]):
        g = shape(f["geometry"])
        inside = prep(g)
        tier = f["properties"].get("tier") or "base"
        minx, miny, maxx, maxy = g.bounds
        n = tries = 0
        while n < AGREEMENT_PER_PIECE and tries < AGREEMENT_PER_PIECE * 5000:
            tries += 1
            pt = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if not inside.contains(pt):
                continue
            n += 1
            total += 1
            got = [j for j in tree.query(pt) if tiers[j] == tier and simple_g[j].contains(pt)]
            if got == [i]:
                hit += 1
            elif len(got) > 1:
                double += 1
    return hit, total, double


def watch():
    """Every results file and precinct map the Board has posted since the
    shipped build: a new or reposted file is when these lines can move."""
    import requests  # noqa: PLC0415
    with open(RECORD_FILE, encoding="utf-8") as fh:
        rec = json.load(fh)
    session = requests.Session()
    found, missing = election_files(session, None)
    maps = precinct_files(session, None)
    changes = []
    for label, now, was in (("results file", {d.isoformat(): v[1] for d, v in found.items()},
                             rec["results"]),
                            ("precinct map", {d.isoformat(): v[1] for d, v in maps.items()},
                             rec["maps"])):
        for day in sorted(set(now) | set(was)):
            if day not in was:
                changes.append("a %s for %s, posted %s, is not in the shipped build"
                               % (label, day, now[day]))
            elif day not in now:
                changes.append("the %s for %s, read by the shipped build, is gone" % (label, day))
            elif now[day] != was[day]:
                changes.append("the %s for %s was posted again on %s; the shipped build read "
                               "the copy of %s" % (label, day, now[day], was[day]))
    if changes:
        for c in changes:
            print("build-nc-school-board-districts --watch: CHANGED: " + c)
        print("Rebuild with this builder; it re-runs every gate before it writes.")
        raise SystemExit(1)
    print("build-nc-school-board-districts --watch: unchanged since the build of %s — %d results "
          "files and %d precinct maps" % (rec["built"], len(found), len(maps)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true",
                    help="offline: hold the shipped file to its own rules")
    ap.add_argument("--watch", action="store_true",
                    help="list the Board's results files and precinct maps against the build")
    ap.add_argument("--cache", help="read and save the Board's files in this folder")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="build, do not write")
    args = ap.parse_args()
    if args.watch:
        watch()
        return
    if args.check:
        with open(OUT_FILE, encoding="utf-8") as fh:
            out = json.load(fh)
        with open(RECORD_FILE, encoding="utf-8") as fh:
            record = json.load(fh)
        problems, st = gates(out, record.get("enclaves") or {}, record.get("websites"))
        if problems:
            for p in problems:
                print("build-nc-school-board-districts: FAIL: " + p)
            raise SystemExit(1)
        print(ok_line("--check", out, st))
        return
    exact, record = build(datetime.date.today(), args.cache, args.verbose)
    if args.dry_run:
        return
    out = simplify_shared(exact)
    problems, st = gates(out, record["enclaves"], record["websites"])
    hit, total, double = agreement(exact, out)
    print("agreement: %d of %d points sampled inside the exact pieces (%.3f%%) land in the "
          "same piece, and only there, after the shared simplification (floor %.1f%%); %d "
          "land in two pieces of one tier"
          % (hit, total, 100.0 * hit / total, 100 * AGREEMENT_FLOOR, double))
    if hit < AGREEMENT_FLOOR * total:
        problems.append("only %.3f%% of sampled points land in their own piece after the "
                        "shared simplification" % (100.0 * hit / total))
    if problems:
        for p in problems:
            print("build-nc-school-board-districts: FAIL: " + p)
        raise SystemExit(1)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")
    record.update({"features": len(out["features"]), "boards": st["boards"], "seats": st["seats"],
                   "agreement": [hit, total], "double": double})
    with open(RECORD_FILE, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(ok_line("build", out, st))
    with open(OUT_FILE, "rb") as fh:
        raw = fh.read()
    import gzip  # noqa: PLC0415
    print("wrote %s: %d bytes, %d gzipped" % (os.path.relpath(OUT_FILE, REPO), len(raw),
                                              len(gzip.compress(raw, 9))))


def ok_line(how, out, st):
    return ("build-nc-school-board-districts %s: OK — %d district seats on %d boards in %d "
            "features; no piece's interior point lies in another piece of its tier; %d "
            "crossing(s) of %.0f m2 in all where the shared simplification moved two lines "
            "apart, the largest %.0f m2 (ceiling %.0f m2); %d outline(s) touching themselves; "
            "%d hole(s) of %.0f m2 between a board's pieces, %s (ceiling %.0f m); %d of %d "
            "boards link their school district's website"
            % (how, st["seats"], st["boards"], len(out["features"]), st["crossings"],
               st["crossing_m2"], st["worst_m2"], MAX_CROSSING_M2, st["self_touching"],
               st["holes"], st["hole_m2"],
               # a hole too small to hold a circle 2 x SLIVER_M across is not
               # measured, so a widest figure under that is not claimed
               ("the widest %.1f m across" % st["widest_hole_m"])
               if st["widest_hole_m"] >= 2 * SLIVER_M else
               ("none %.0f m across" % (2 * SLIVER_M)), MAX_HOLE_M,
               st["websites"], st["boards"]))


if __name__ == "__main__":
    main()
