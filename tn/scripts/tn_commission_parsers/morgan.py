"""Morgan County commissioners, from the county's own commission page.

The page (morgancountytn.gov/county-commission/, a WordPress page whose
modified stamp reads 2026-09-11, after the 1 September 2026 term began) lists
the 18 commissioners under six headings, "1st District Commissioners Serving
Coalfield" to "6th District Commissioners Serving Petros, Joyner, and Mossy
Grove", each member as a name line followed by "County Commissioner, Nth
District". The heading and the member's own line must name the same district,
or the parse stops. Three seats per district, as the page's own text says
("eighteen (18) Commissioners representing six (6) Commission Districts").

The page prints phone numbers and e-mail addresses beside many members; every
address is a personal or business one (yahoo, gmail, hotmail, a school
district's, a shop's) and no phone is the courthouse's, so none is read. The
county's only number on the page (423-346-6288, the County Executive's office)
belongs to no member.

The county's site answered HTTP 500 on 2026-10-11 and served this page on
2026-10-13. The page says the county stopped posting commission minutes online
after a warning given to county clerks on 9 April 2026, so no minutes are read.

Currency: checked 2026-10-13 against the Morgan County Election Commission's
"August 6, 2026 unofficial Cumulative Results" (its own site, morganelections
.com, the PDF on its file host img1.wsimg.com; a scanned document, run date
08/12/2026, read as images). All 18 seats were on the 6 August 2026 ballot,
three per district, and the 18 names here are the 18 winners in the same
districts: D1 Walls 364, Jackson 307, Roberts 280 (three candidates); D2
Lindsay 432, Snow 423, Scarbrough 392 (three); D3 Justes 569, Hennessee 528,
Morgan 455 (three); D4 Vespie 466, Kreis 359, Gibson 323 (Moore 266, a
write-in 217); D5 Stewart 458, Kennedy 456, Bryant 397 (three); D6 Lively
438, Dagley 427, Adkisson 386 (Duncan 327). The results are unofficial; no
certified copy is published on a government host.

Names are kept as the page prints them. Three differ from the ballot by more
than a nickname or middle name: the page has "Vera Scarbough" (ballot
"Scarbrough", which her own e-mail on the page also spells), "Melissa Kries"
(ballot "Kreis") and "Janet Adkission" (ballot "Adkisson"). The page's
spellings are most likely typos, but they are the county's and are kept, as
Jefferson's "Hufaker" is. Other ballot spellings differ only by nicknames and
middle names (Terry Bear Jackson, Randy Lee Roberts, John "Goose" Lindsay,
Margaret Gibson, Douglas Vespie, Melissa Coleman Bryant, Debbie Woods Lively).

The page names no chair."""
import re
from ._common import lines, member, district_number

COUNTY = "Morgan"; FIPS = "129"
DOMAINS = ("morgancountytn.gov",)
URLS = ["https://morgancountytn.gov/county-commission/"]
SEATS = {str(i): 3 for i in range(1, 7)}
AT_LARGE = 0

HEADING = re.compile(r"^(\d)(?:st|nd|rd|th) District Commissioners Serving\b")
MEMBER_LINE = re.compile(r"^County Commissioner, (\d)(?:st|nd|rd|th) District$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def parse(pages):
    ls = lines(pages[URLS[0]])
    districts, current = {}, None
    for i, line in enumerate(ls):
        head = HEADING.match(line)
        if head:
            current = head.group(1)
            if current in districts:
                raise ValueError("District %s has two headings" % current)
            districts[current] = []
            continue
        title = MEMBER_LINE.match(line)
        if not title:
            continue
        if current is None:
            raise ValueError("a member sits before any district heading")
        if title.group(1) != current or district_number(line) != int(current):
            raise ValueError("a member titled %r sits under the District %s heading"
                             % (line, current))
        name = ls[i - 1]
        if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
            raise ValueError("District %s: %r does not look like a name" % (current, name))
        districts[current].append(member(name))
    if set(districts) != set(SEATS):
        raise ValueError("the page names districts %s, not 1..6" % sorted(districts, key=int))
    for d, ms in districts.items():
        if not ms:
            raise ValueError("District %s heading has no members under it" % d)
    return {"districts": districts, "atLarge": []}
