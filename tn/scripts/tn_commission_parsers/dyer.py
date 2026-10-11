"""Dyer County elects 20 commissioners, two from each of 10 districts, and
the county LETTERS its districts A to J: the ballot's races are "Co
Commission Dist A Pos 1" .. "Dist J Pos 2", and the county page's table says
"A" .. "J". The state's commission-district geometry (the Comptroller's
"County Commission Districts New", layer 2 of its Redistricting_Address_Lookup
service, field NEWCCDDISTRICT) numbers Dyer's districts 1 to 10 and carries no
letter.

WHICH LETTER IS WHICH NUMBER. No document read states it in words: the county
publishes letters only (its sitemap has no district map or redistricting page,
and its posted minutes start in 2025), and each Comptroller file read here
carries a number or a letter, never both on one record. The table below is MEASURED from
three government sources, all read 2026-10-11, and was not assumed from
alphabetical order (it happens to follow it; it is written out, not computed,
so that a change to it has to be measured again):

1. The same Comptroller service's "Voting Precincts New" layer (layer 12,
   field NEWVOTINGPRECINCT) names Dyer's 15 precincts with their district
   letter, "A-Bonicord" .. "J-N Dyersburg". By area (EPSG:5070), every one of
   them lies 99.99-100% inside a single numbered district of layer 2, and the
   union of each letter's precincts matches one numbered district with an IoU
   of at least 0.9999: A=1, B=2, C=3, D=4, E=5, F=6, G=7, H=8, I=9, J=10.
   Against the shipped, simplified file each precinct is at least 99.54%
   inside the same district.
2. The Comptroller's map "Dyer County Current County Commission Districts
   Color Coded" (comptroller.tn.gov, "2022_CCD Color Coded_Dyer.pdf", an
   ArcMap GeoPDF created 2024-07-22 and modified 2026-04-17, listed on its
   County District Maps page) labels the districts by letter only. Read
   through the map's own embedded georeference, each of its ten large
   district-letter labels falls inside the same-numbered district of layer 2
   and of the shipped file (A in 1 .. J in 10), and each of its 15 precinct
   labels falls inside its own precinct polygon, which checks the
   georeference.
3. The Dyer County Election Commission's precinct report of the 6 August 2026
   election (pages 9-83 of the PDF named under Currency, read as images) gives
   each precinct an ID carrying its letter - A1 Bonicord, A2 Fowlkes, B1
   Newbern, C1 Tatumville, C2 Trimble, D1 Millsfield, D2 Bogota, E1 Finley, E2
   Lenox, F1 Pilgrim Rest, G1 Courthouse, H1 East Dyersburg, I1 Community
   Center, I2 Hurricane Hill, J1 North Dyersburg - and each precinct's ballot
   carries its own letter's two commission races and no other. Those are the
   Comptroller layer's precincts and letters (it spells "Lennox", "Pilgrim
   Rest Baptist Church", "E. Dyersburg" and "N Dyersburg").

The county page's district letter is therefore the county's own district,
recorded here under the geometry's number, and DISTRICT_LABELS carries the
letter so the card and the county's page say "District A" beside the state's
number.

The county's Elected Officials page (a Duda site builder page) carries one
table per body. The one under the paragraph "Dyer County Commissioners" has
the header row District / Name / Term Ends and one row per member: the
district letter, the name and the term's end, all in the same row, so nothing
is read from the table's order. Every row must have a single letter A-J, a
name and a term end of the form M/YYYY. The tables for constables and the
school board, which use the same letters, are not read.

PRIVACY: the table carries no phone, e-mail or address.

Currency: checked 2026-10-11 against the Dyer County Election Commission's
Election Summary Report for the 6 August 2026 State Primary and County
General (printed 8/12/2026 2:00 PM, an 83-page scanned PDF whose first eight
pages are the summary and the rest a five-page report per precinct, linked
from the county's own 2026 results page dyercounty.com/2026 and served from
its site builder's file store irp.cdn-website.com), read as images: each "Dist
X Pos k" race was vote for 1, and the 20 winners are the 20 names this table
lists under the same letters; the precinct pages give the same winners.
Contested: A Pos 2 (Mike Nicks over Larry Shawver), B Pos 2 (Tanner Seratt
over John Uitendaal), E Pos 2 (Adam Royce McGuire over Steven Spires and Lanny
K. Bane), H Pos 2 (Tyler Rogers over James T. "Bubba" Cobb), I Pos 1 (Casey
King over Darrell McElrath) and I Pos 2 (Amy McDonald over Pam Newell). The
ballot writes Cody W. Walker, Victor McLin, Sr, Chris L. Hamm, Debra T.
Roberson and James D. "Dob" Johnson Jr; each is the page's entry. Every term
on the table ends 8/2030."""
import re
from ._common import txt, member

COUNTY = "Dyer"; FIPS = "045"
DOMAINS = ("dyercounty.com",)
URLS = ["https://www.dyercounty.com/elected-officials"]
SEATS = {str(i): 2 for i in range(1, 11)}
AT_LARGE = 0

LETTERS = "ABCDEFGHIJ"
# letter -> the geometry's district number, as MEASURED (see the docstring:
# the Comptroller's lettered precincts nest in its numbered districts, its
# lettered GeoPDF labels fall in them, and the county's precinct report ties
# each precinct to its letter). Written out on purpose; never derive it from
# LETTERS' order.
LETTER_DISTRICT = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5,
                   "F": 6, "G": 7, "H": 8, "I": 9, "J": 10}

# what the card and the county's page print beside the state's number
DISTRICT_LABELS = {str(n): "District " + k for k, n in LETTER_DISTRICT.items()}

NAME = re.compile(r"^[A-Z][A-Za-z.'’\" -]+$")
TERM = re.compile(r"^\d{1,2}/\d{4}$")


def parse(pages):
    page = pages[URLS[0]]
    head = re.search(r">\s*Dyer County Commissioners\s*<", page)
    if not head:
        raise ValueError("no 'Dyer County Commissioners' heading")
    t = re.search(r"<table\b.*?</table>", page[head.end():], re.S)
    if not t:
        raise ValueError("no table after the commissioners heading")
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", t.group(0), re.S)
    header = [txt(c) for c in re.findall(r"<th\b[^>]*>(.*?)</th>", rows[0], re.S)] if rows else []
    if header != ["District", "Name", "Term Ends"]:
        raise ValueError("the commissioners table's header is %r" % header)
    by_letter = {}
    for r in rows[1:]:
        cells = [txt(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S)]
        if len(cells) != 3:
            raise ValueError("a commissioners row with %d cells: %r" % (len(cells), cells))
        letter, name, term = cells
        if len(letter) != 1 or letter not in LETTERS:
            raise ValueError("%r: district %r is not a letter A-J" % (name, letter))
        if not NAME.match(name):
            raise ValueError("%r does not look like a name" % name)
        if not TERM.match(term):
            raise ValueError("%r: term end %r" % (name, term))
        by_letter.setdefault(letter, []).append(member(name))
    if sorted(by_letter) != list(LETTERS):
        raise ValueError("the table's districts are %s, not A-J" % sorted(by_letter))
    if sorted(LETTER_DISTRICT) != list(LETTERS) or \
            sorted(LETTER_DISTRICT.values()) != list(range(1, 11)):
        raise ValueError("LETTER_DISTRICT is not a one-to-one table of A-J onto 1-10")
    return {"districts": {str(LETTER_DISTRICT[k]): v for k, v in by_letter.items()},
            "atLarge": []}
