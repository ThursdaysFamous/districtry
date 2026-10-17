#!/usr/bin/env python3
"""
Build sc/data/app/sc-school-board-districts.json: the districts South
Carolina's school boards are elected from, from the Revenue and Fiscal Affairs
Office's statewide map of them, with what each board's own act says about who
elects its members.

    python3 sc/scripts/build_sc_school_board_districts.py            # fetch, check, write
    python3 sc/scripts/build_sc_school_board_districts.py --check    # offline
    python3 sc/scripts/build_sc_school_board_districts.py --watch    # has the layer changed?

The work is scripts/published_district_layers.py, which other builders
share; this file says where South Carolina's layer is, how to read one record,
what to expect and what each board's act says.

THE SOURCE. "School Board Districts", layer 0 of the Boundaries_Districts
service on gis.state.sc.us, credited to the Revenue and Fiscal Affairs Office's
GIS Section ("mapping@rfa.sc.gov"). In South Carolina a school board's
districts and its method of election are set by an act of the General
Assembly for that one school district, and RFA keeps the maps those acts name.
The layer states no licence and no edit date; its service lists "Query,Extract"
and an as-is disclaimer.

WHAT IT HOLDS. Measured 2026-10-16: 401 records on all 72 school districts.
Eighteen school districts are one record each labelled "At Large", which has
no districts to draw, so those 18 records are skipped and declared. The other
383 records are the districts of 54 boards, one record each.

  * THE LABEL. Each record names its district as "<place> School Board Area 3",
    "<place> Board District 5" and the like; the card prints "Area 3" or
    "District 5", the word and number at the end, which is how the board's
    act numbers it (Greenville's are numbered 17 to 28 because Act 301 of 2012
    renumbered them). One label starts with a space (" Clarendon School Board
    Area 3") and one has two spaces inside it (Bamberg's district 5); both read
    the same once spaces are tidied.
  * ONE SCHOOL DISTRICT'S NAME HAS A WORD TWICE: "Sumter County County School
    District", which the card prints as "Sumter County School District"
    (NAME_FIXES). The build fails if the layer ever spells it right, so the fix
    goes when it stops being needed.
  * TWO WEBSITES ARE WRONG (WEBSITE_FIXES). Some of Anderson School District
    4's records give anderson1.org, District 1's site; the rest give
    anderson4.org, which the card uses for all of them. Hampton County School
    District's records give www.hampton2.k12.sc.us, the site of one of the two
    districts Act 184 of 2020 joined into it, and that host has no DNS record
    (measured 2026-10-16); the district's own site is www.hcsdsc.org, whose
    home page was read that day ("Home - Hampton County School District"). The
    other 52 websites answered 200 when probed the same day.

WHAT THE LAYER'S ACT FIELDS GET WRONG, AND WHY THE CARD DOES NOT USE THEM.
Each record also names an act, a map number and a bill link. Every board's act
was read on scstatehouse.gov on 2026-10-16, in its ratified text (33 of the
records link an earlier printed version of the bill instead), and the act
that now sets the board is not always the one the record names:

  * York School District 3 (Rock Hill) cites York School District 1's act and
    map (Act 309 of 2012, S-91-01-12). Its own is Act 101 of 2023, map
    S-91-03-23, which matches the map file RFA publishes for it.
  * Spartanburg 5 and 7 cite "2023 Act No. 106" and "No. 107"; the ratified
    acts are Act 97 and Act 98 of 2023, which amend Acts 106 and 107 of 2015.
  * Williamsburg cites Act 471 of 2002, which ended its two at-large seats;
    Act 107 of 2017 restored them, so the board is nine.
  * Allendale cites Act 233 of 1979 and Marion Act 304 of 2012; the board's
    makeup and voting rule are in Act 174 of 1999 and Act 607 of 1986.
  * Lee cites Act 278 of 1979; Act 272 of 2026, approved 19 May 2026,
    rewrote the board's section.
  * Chester cites only Act 252 of 1979, which is online only as a summary;
    Act 265 of 1985 added a seventh, at-large seat. S.1180 of 2022, which
    would have given the six districts map S-23-00-22, was vetoed and the veto
    was sustained, so it is not law.
  * Edgefield cites Act 305 of 2014, and Act 237 of 2024 replaced that act's
    map with S-37-00-24 from the 2024 elections. RFA's own page still links
    the 2014 map, so the layer may be drawn on it; the card says so, and the
    build fails if the layer's citation for Edgefield changes
    (LAYER_CITES), so the sentence is re-read when RFA updates it.
  * Ten records name no act, and Bamberg and Darlington name neither an act
    nor a map (Darlington's districts are the county council's, set by county
    ordinance).

So the card prints the act ACTS names below, never the layer's.

WHO ELECTS EACH MEMBER (ACTS, `vote`). Read from each act's own words:
  * "area" (33 boards): the voters of the district elect its member. For
    five of them the reading rests on weaker wording, and is kept: Georgetown
    (the act's account of the 2008 Voting Rights Act consent order that ended
    at-large elections), Saluda (the 2024 act says only "in the manner
    provided by law"; the reading rests on a 6 April 1995 Attorney General
    opinion describing the 20 October 1988 federal court order in Holloway v.
    Board of Trustees, which ended at-large elections; the order itself was
    not read), Lancaster ("the highest number of the votes in each
    district"), Cherokee (the voting sentence of Act 587 of 1992, kept when
    Act 416 of 2002 cut the board to seven; the act that put nine seats back
    was not found) and Pickens ("the qualified electors of the district",
    read as the single-member district named just before it).
  * "residence" (5 boards: Anderson 1, 2 and 3, York 2 and York 3): the
    member must live in the district and every voter in the school district
    votes for the seat.
  * "unclear" (16 boards): the act says a member is elected from, or lives in,
    the district, and never who votes. Abbeville's says only "in the manner
    provided by law", and the act that sets the method was not found;
    Chester's six district seats come from the 1979 act online only as a
    summary; Edgefield's 2014 act said "all of the qualified electors of the
    district" and its 2024 act dropped "all"; Fairfield's says "a majority of
    the votes cast" without saying whose. The card says the act does not say.

HOW MANY MEMBERS EACH DISTRICT ELECTS (ACTS, `size`, `at_large`, `seats`).
One, except Spartanburg 5 (area 2 elects two and area 3 six), Florence 3
(areas 4 and 7 elect two each) and Spartanburg 7, whose act states neither
the number per area nor who votes: its population table (54,096 people over
nine seats, about 6,011 a seat; areas 1 to 4 within 266 of that and area 5's
31,051 at +3.31%) fits one member for each of areas 1 to 4 and five for area
5, which is how the card counts them, and its note says the number is worked
out rather than stated. Calhoun's act gives no number: the board is as large
as the Calhoun County Council and uses its districts, so `size` is None. The
build fails unless every other board's district seats plus its at-large seats
add up to the size its act gives.

NAMES. None. No statewide list of South Carolina's school board members has
been read: the School Boards Association's directory is sent on request, and
the State Election Commission's results site answers GitHub's servers with
HTTP 202 and no page. The card names no one and links the school district's
own website, which the layer gives for every board; recorded as gap
sc-school-board-members.

PACING. gis.state.sc.us serves the precinct layer this instance also reads;
one second between requests, as that builder does, after the robots.txt read
the shared fetcher makes on every host it asks.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))

import published_district_layers as psb  # noqa: E402

LAYER = ("https://gis.state.sc.us/arcgis/rest/services/Boundaries_Districts/"
         "School_Board_Districts/FeatureServer/0")

# The school district's name as the layer spells it -> as the card prints it.
NAME_FIXES = {"Sumter County County School District": "Sumter County School District"}

# (school district, the website a record gives) -> the website the card uses.
WEBSITE_FIXES = {
    ("Anderson School District 4", "https://www.anderson1.org"): "https://www.anderson4.org/",
    ("Hampton County School District", "http://www.hampton2.k12.sc.us/home"): "https://www.hcsdsc.org/",
}

# School district -> (the act that sets the board, its ratified text as read on
# 2026-10-16, board size or None, seats elected at large, who votes, the seats
# a district elects where that is not one). Who votes: "area" (the district's
# voters), "residence" (every voter in the school district; the member lives in
# the district) or "unclear" (the act does not say).
ACTS = {
    'Abbeville County School District': ('Act 247 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1263.htm',
        9, 0, 'unclear', {}),
    'Aiken County School District': ('Act 230 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/1025.htm',
        9, 0, 'area', {}),
    'Allendale County School District': ('Act 174 of 1999',
        'https://www.scstatehouse.gov/sess113_1999-2000/bills/3404.htm',
        5, 0, 'area', {}),
    'Anderson School District 1': ('Act 231 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/4892.htm',
        7, 0, 'residence', {}),
    'Anderson School District 2': ('Act 232 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/5153.htm',
        7, 1, 'residence', {}),
    'Anderson School District 3': ('Act 300 of 2014',
        'https://www.scstatehouse.gov/sess120_2013-2014/bills/4633.htm',
        5, 1, 'residence', {}),
    'Anderson School District 4': ('Act 300 of 2014',
        'https://www.scstatehouse.gov/sess120_2013-2014/bills/4633.htm',
        5, 0, 'area', {}),
    'Anderson School District 5': ('Act 300 of 2014',
        'https://www.scstatehouse.gov/sess120_2013-2014/bills/4633.htm',
        9, 2, 'area', {}),
    'Bamberg County School District': ('Act 233 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/5231.htm',
        9, 2, 'unclear', {}),
    'Barnwell County School District': ('Act 92 of 2023',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/654.htm',
        5, 0, 'area', {}),
    'Beaufort County School District': ('Act 583 of 1992',
        'https://www.scstatehouse.gov/sess109_1991-1992/bills/4781.htm',
        11, 0, 'area', {}),
    'Berkeley County School District': ('Act 251 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/910.htm',
        9, 1, 'unclear', {}),
    'Calhoun County Public Schools': ('Act 585 of 1994',
        'https://www.scstatehouse.gov/sess110_1993-1994/bills/4889.htm',
        None, 0, 'area', {}),
    'Charleston County School District': ('Act 182 of 2020',
        'https://www.scstatehouse.gov/sess123_2019-2020/bills/5034.htm',
        9, 0, 'unclear', {}),
    'Cherokee County School District': ('Act 252 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1271.htm',
        9, 0, 'area', {}),
    'Chester County School District': ('Act 252 of 1979 and Act 265 of 1985',
        'https://www.scstatehouse.gov/sess106_1985-1986/bills/2909.htm',
        7, 1, 'unclear', {}),
    'Chesterfield County School District': ('Act 205 of 1993',
        'https://www.scstatehouse.gov/sess110_1993-1994/bills/22.htm',
        9, 0, 'area', {}),
    'Clarendon County School District': ('Act 234 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/738.htm',
        9, 0, 'unclear', {}),
    'Colleton County School District': ('Act 253 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1235.htm',
        7, 0, 'area', {}),
    'Darlington County School District': ('Act 416 of 2006',
        'https://www.scstatehouse.gov/sess116_2005-2006/bills/4912.htm',
        8, 0, 'area', {}),
    'Dorchester County School District 2': ('Act 96 of 2023',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/3961.htm',
        7, 0, 'area', {}),
    'Dorchester School District 4': ('Act 99 of 2015',
        'https://www.scstatehouse.gov/sess121_2015-2016/bills/4082.htm',
        5, 0, 'area', {}),
    'Edgefield County School District': ('Act 237 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/1292.htm',
        7, 0, 'unclear', {}),
    'Fairfield County School District': ('Act 255 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1292.htm',
        7, 0, 'unclear', {}),
    'Florence County School District 1': ('Act 256 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/5339.htm',
        9, 0, 'area', {}),
    'Florence County School District 3': ('Act 238 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/4868.htm',
        9, 0, 'unclear', {'Area 4': 2, 'Area 7': 2}),
    'Florence County School District 5': ('Act 100 of 2015',
        'https://www.scstatehouse.gov/sess121_2015-2016/bills/810.htm',
        7, 3, 'unclear', {}),
    'Georgetown County School District': ('Act 107 of 2021',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/4241.htm',
        9, 2, 'area', {}),
    'Greenville County School District': ('Act 257 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/5159.htm',
        12, 0, 'area', {}),
    'Greenwood County School District 50': ('Act 239 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/972.htm',
        9, 0, 'area', {}),
    'Hampton County School District': ('Act 259 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1264.htm',
        7, 0, 'unclear', {}),
    'Horry County School District': ('Act 287 of 1989',
        'https://www.scstatehouse.gov/sess108_1989-1990/bills/673.htm',
        12, 1, 'area', {}),
    'Jasper County School District': ('Act 240 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/782.htm',
        9, 0, 'unclear', {}),
    'Kershaw County School District': ('Act 241 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/5168.htm',
        9, 0, 'area', {}),
    'Lancaster County School District': ('Act 607 of 1992',
        'https://www.scstatehouse.gov/sess109_1991-1992/bills/1552.htm',
        7, 0, 'area', {}),
    'Laurens County School District 55': ('Act 87 of 2025',
        'https://www.scstatehouse.gov/sess126_2025-2026/bills/3878.htm',
        7, 0, 'area', {}),
    'Laurens County School District 56': ('Act 88 of 2025',
        'https://www.scstatehouse.gov/sess126_2025-2026/bills/3877.htm',
        7, 0, 'area', {}),
    'Lee County School District': ('Act 272 of 2026',
        'https://www.scstatehouse.gov/sess126_2025-2026/bills/5653.htm',
        7, 0, 'unclear', {}),
    'Marion County School District': ('Act 607 of 1986',
        'https://www.scstatehouse.gov/sess106_1985-1986/bills/2674.htm',
        7, 0, 'area', {}),
    'Marlboro County School District': ('Act 149 of 2007',
        'https://www.scstatehouse.gov/sess117_2007-2008/bills/3446.htm',
        8, 0, 'area', {}),
    'Newberry County School District': ('Act 284 of 1985',
        'https://www.scstatehouse.gov/sess106_1985-1986/bills/673.htm',
        7, 0, 'area', {}),
    'Oconee County School District': ('Act 181 of 1995',
        'https://www.scstatehouse.gov/sess111_1995-1996/bills/4215.htm',
        5, 0, 'area', {}),
    'Orangeburg County School District': ('Act 280 of 2018',
        'https://www.scstatehouse.gov/sess122_2017-2018/bills/662.htm',
        9, 2, 'unclear', {}),
    'Pickens County School District': ('Act 261 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1220.htm',
        7, 0, 'area', {}),
    'Richland County School District 1': ('Act 300 of 2016',
        'https://www.scstatehouse.gov/sess121_2015-2016/bills/863.htm',
        7, 3, 'area', {}),
    'Saluda County School District': ('Act 245 of 2024',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/5267.htm',
        7, 0, 'area', {}),
    'Spartanburg County School District 5': ('Act 97 of 2023',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/4215.htm',
        9, 0, 'area', {'Area 2': 2, 'Area 3': 6}),
    'Spartanburg County School District 7': ('Act 98 of 2023',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/4216.htm',
        9, 0, 'unclear', {'Area 5': 5}),
    'Sumter County School District': ('Act 262 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/5288.htm',
        9, 0, 'area', {}),
    'Union County School District': ('Act 264 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1299.htm',
        9, 0, 'area', {}),
    'Williamsburg County School District': ('Act 107 of 2017',
        'https://www.scstatehouse.gov/sess122_2017-2018/bills/568.htm',
        9, 2, 'unclear', {}),
    'York County School District 1': ('Act 309 of 2012',
        'https://www.scstatehouse.gov/sess119_2011-2012/bills/1384.htm',
        7, 2, 'area', {}),
    'York County School District 2': ('Act 265 of 2022',
        'https://www.scstatehouse.gov/sess124_2021-2022/bills/1270.htm',
        7, 2, 'residence', {}),
    'York County School District 3': ('Act 101 of 2023',
        'https://www.scstatehouse.gov/sess125_2023-2024/bills/764.htm',
        7, 2, 'residence', {}),

}

# School district -> a sentence the card prints under the act, for what the act
# or the map says that the other fields cannot.
NOTES = {
    "Anderson School District 2": (
        "Act 232 of 2024 drew these six areas. The members for areas 2, 5 and 6 "
        "were first elected from them in 2024, and those for areas 1, 3 and 4 are "
        "first elected from them in November 2026."),
    "Bamberg County School District": (
        "Act 233 of 2024 moved the board from appointment to election. Districts 1, "
        "4, 5 and 7 were first elected in 2024 and districts 2, 3 and 6 are first "
        "elected in November 2026; until a seat's first election, a member of the "
        "earlier appointed board chosen by the county's legislative delegation "
        "holds it."),
    "Calhoun County Public Schools": (
        "Act 585 of 1994 makes the board as large as the Calhoun County Council "
        "and gives it the council's single-member districts."),
    "Edgefield County School District": (
        "Act 237 of 2024 replaced this board's 2014 map with a new one, map "
        "S-37-00-24, from the 2024 elections. The state's map of school board "
        "districts still cites the 2014 act, so these lines may be the earlier ones."),
    "Greenwood County School District 50": (
        "These are the areas of a new map, set by Act 239 of 2024, that takes "
        "effect with the school board election of 3 November 2026. Members elected "
        "before then were elected from the earlier areas."),
    "Horry County School District": (
        "The member elected at large is the board's chairman, elected by every "
        "voter in the county as a twelfth seat (Act 178 of 1997)."),
    "Laurens County School District 55": (
        "These are the areas of a new map, set by Act 87 of 2025, that takes effect "
        "with the school board election of 3 November 2026. Members elected before "
        "then were elected from the earlier areas."),
    "Laurens County School District 56": (
        "These are the areas of a new map, set by Act 88 of 2025, that takes effect "
        "with the school board election of 3 November 2026. Members elected before "
        "then were elected from the earlier areas."),
    "Spartanburg County School District 7": (
        "The act does not say how many members each area elects. Its population "
        "table fits one member for each of areas 1 to 4 and five for area 5, which "
        "is how this card counts them."),
}

# School district -> (ActName, MapNumber) as the layer gives them, where a note
# above depends on what the layer cites; the build fails when either moves.
LAYER_CITES = {
    "Edgefield County School District": ("2014 Act No. 305 (S.1329)", ""),
}

VOTES = ("area", "residence", "unclear")

_seen_fixes = set()
_at_large = set()
_cites = {}


def tidy(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def read(props):
    raw = tidy(props.get("SchoolDist"))
    board = NAME_FIXES.get(raw, raw)
    if board != raw:
        _seen_fixes.add(raw)
    label_raw = tidy(props.get("SchoolBoar"))
    if "at large" in label_raw.lower():
        _at_large.add(board)
        return None
    m = re.search(r"\b(Area|District) (\d+)$", label_raw)
    if not m:
        psb.fail(SPEC, "the label %r does not end in Area or District and a number: %r"
                 % (label_raw, props))
    label = "%s %s" % (m.group(1), m.group(2))
    if board not in ACTS:
        psb.fail(SPEC, "%r is on the map and not in ACTS: read its act, then add it" % board)
    act, _url, size, at_large, vote, seats = ACTS[board]
    web = tidy(props.get("DistrictUR"))
    fixed = WEBSITE_FIXES.get((board, web))
    if fixed:
        _seen_fixes.add((board, web))
        web = fixed
    if not re.match(r"https?://", web):
        psb.fail(SPEC, "%s, %s gives no website: %r" % (board, label, props))
    if board in LAYER_CITES:
        _cites.setdefault(board, set()).add((tidy(props.get("ActName")),
                                             tidy(props.get("MapNumber"))))
    out = {
        "key": "%s-%s" % (slug(board), slug(label)),
        "board": board,
        "label": label,
        "vote": vote,
        "seats": seats.get(label, 1),
        "act": act,
        "web": web,
    }
    if size is not None:
        out["size"] = size
    if at_large:
        out["atLarge"] = at_large
    if board in NOTES:
        out["note"] = NOTES[board]
    return out


def extra_check(feats):
    boards = {}
    for f in feats:
        p = f["properties"]
        boards.setdefault(p["board"], []).append(p)
    if set(boards) != set(ACTS):
        psb.fail(SPEC, "the map's boards and ACTS differ: on the map only %s; in ACTS only %s"
                 % (sorted(set(boards) - set(ACTS)), sorted(set(ACTS) - set(boards))))
    for board, rows in sorted(boards.items()):
        act, _url, size, at_large, vote, seats = ACTS[board]
        if vote not in VOTES:
            psb.fail(SPEC, "%s: who votes is %r, not one of %s" % (board, vote, VOTES))
        labels = set(r["label"] for r in rows)
        if not set(seats) <= labels:
            psb.fail(SPEC, "%s: ACTS gives seats for %s, which the map does not draw"
                     % (board, sorted(set(seats) - labels)))
        webs = set(r["web"] for r in rows)
        if len(webs) != 1:
            psb.fail(SPEC, "%s: its districts give %d websites, %s" % (board, len(webs), sorted(webs)))
        if size is not None and sum(r["seats"] for r in rows) + at_large != size:
            psb.fail(SPEC, "%s: %d district seats and %d at large do not make the board of %d "
                     "its act gives" % (board, sum(r["seats"] for r in rows), at_large, size))
        if board in _at_large:
            psb.fail(SPEC, "%s has districts and an At Large record" % board)
    if set(NOTES) - set(boards):
        psb.fail(SPEC, "NOTES names %s, which the map does not draw" % sorted(set(NOTES) - set(boards)))
    # the next three see what read() saw, so they run only on a fetch
    if _at_large or _cites:
        expected = set(NAME_FIXES) | set(WEBSITE_FIXES)
        if _seen_fixes != expected:
            psb.fail(SPEC, "a fix is no longer needed: %s. Remove it"
                     % sorted(map(str, expected - _seen_fixes)))
        for board, cite in sorted(LAYER_CITES.items()):
            if _cites.get(board) != {cite}:
                psb.fail(SPEC, "the layer now cites %s for %s, and LAYER_CITES says %s. Re-read "
                         "the board's note in NOTES, then change both together"
                         % (sorted(_cites.get(board) or ()), board, cite))


SPEC = psb.Spec(
    tag="sc",
    label="build_sc_school_board_districts",
    layer=LAYER,
    user_agent="districtry/1.0 (+https://districtry.com/sc/)",
    out_fields="SchoolDist,SchoolBoar,DistrictUR,ActName,MapNumber",
    expect=383,
    expect_groups=54,
    read=read,
    out_file="sc-school-board-districts.json",
    interval="4",
    pace=1.0,
    measure_field="Shape__Area",
    skipped_records=18,
    required=("key", "board", "label", "vote", "seats", "act", "web"),
    extra_check=extra_check,
    card_claims=(
        "Every voter in the school district votes for this seat",
        "does not say whether only this",
        "names no one rather than guessing",
    ),
)

if __name__ == "__main__":
    psb.main(SPEC, __doc__)
