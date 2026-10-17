"""Obion County elects 21 commissioners, three from each of 7 districts (the
page says so: "a 21 member board. Three members from each of the 7 Obion
County Commissioner districts"). The ballot is "Vote for Three (3)" in every
district and names no seat, so no seat is recorded. The page says the
chairman and chairman pro tempore are elected each year and names neither,
so no role is recorded.

The County Commission page (a hand-built HTML site) holds one table whose
rows are the districts: the row's first cell is an <h5> reading "District N"
over the district's communities ("District 1 / South Fulton"), and each
further cell in the same row is one member, holding the member's photo, the
name (inside a mailto link on some, plain text on others) and one or two
phone lines. Each member is paired with the "District N" heading of the row
it sits in; nothing is read from order. A member cell that holds anything
but one photo, one name and phone lines raises, every row must carry a
district heading, and every district 1..7 must appear exactly once.

The photos' alt texts are not read: three of them differ from the printed
name ("John Lane McConnell" over "John McConnell", "Claire Saum" over "Clare
Saum", and "Benny McQuire" over "Benny McGuire", whose ballot name is
"Benny J. McGuire"). Names are kept as the page prints them.

PRIVACY: every member cell carries one or two phone numbers, many labelled
"(Home)" or "(Cell)"; they are the members' own. They are recorded as printed,
in the cell's order, each label kept in front of its number ("cell (731) ...",
"home (731) ..."), under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is. The county
government's own line in the page footer is OFFICE_LINES and never lands on a
member. Twelve names are mailto links to the member's own address, personal
or business (outlook, icloud, hotmail, yahoo, gmail, an employer's, and
ocboe.com, which is the county SCHOOLS' domain); none is on
obioncountytn.gov. Each is recorded on the member whose name it wraps, under
Adam's ruling of 2026-10-17 that an e-mail address a government page prints
beside an official ships too. Only the link ON the name is read: a cell with
an e-mail link anywhere else, or a name carrying two addresses, raises. The
page prints no home address; the only street address on it is the county
government's own footer.

Currency: checked 2026-10-11 against the Obion County Election Commission's
own "Cumulative Results Report" for the 6 August 2026 State Primary and State
and County General election (obionvotes.com/electionresults/summary.html,
Election Night Reporting, run 08/06/2026 8:38 PM, 14 of 14 polling places,
marked "Unofficial Results"; the commission's Election Reports page posts
nothing later than 2018, so no certified copy was found). In every district
the three names on this page are the three highest totals of the "COUNTY
COMMISSION District N - Vote for Three (3)" contest: D1 Mayo 287, McConnell
281, Cranford 236 (uncontested); D2 Barnes 359, Ellegood 328, Lewis 255
(Nohsey 238); D3 Jowers 385, Taylor 357, Holman 326 (Key 165); D4 Sherwood,
Dunlap, Gray (uncontested); D5 McGuire 389, Pierce 376, Ferguson 360
(Parsons 221); D6 Cunningham 376, Roberts 347, Hudgins 310 (McDavid 303,
Fussell 272); D7 Sinclair 455, Baggett 387, Saum 352 (Goodrich 260). Ballot
spellings differ only by middle names, initials and short forms (Ricky W
Cranford, John Lane McConnell, Ryan Anthony Ellegood, Joseph Lewis, Danny C
Jowers, Phillip M. Dunlap, James D. Gray, Benny J. McGuire, Terry E.
Roberts, Kyle W Baggett, Clare McConnell Saum, Sam Sinclair Jr). The District
6 third seat was decided by seven votes on these unofficial figures; the page
seats Hudgins, who led them."""
import re
from ._common import (txt, member, vacant, district_number, read_phones, Withheld,
                      read_emails, member_email)

COUNTY = "Obion"; FIPS = "131"
DOMAINS = ("obioncountytn.gov",)
URLS = ["https://www.obioncountytn.gov/county_commission.html"]
SEATS = {str(i): 3 for i in range(1, 8)}
AT_LARGE = 0
# The county government's own line, in the page footer.
OFFICE_LINES = ("(731) 885-9611",)

ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
HEAD_RE = re.compile(r"<h5\b[^>]*>(.*?)</h5>", re.S | re.I)
LABEL = re.compile(r"^District\s+(\d{1,2})\b")
PHONE = re.compile(r"^\(\d{3}\)\s*\d{3}-\d{4}(?:\s*\((?:Home|Cell|Work|Office)\))?$", re.I)
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+(?:,\s*(?:Jr|Sr|II|III|IV)\.?)?$")


def read_cell(d, cell):
    if len(re.findall(r"<img\b", cell, re.I)) != 1:
        raise ValueError("District %s: a member cell without exactly one photo" % d)
    raw = [s for s in re.split(r"<br\s*/?>", cell, flags=re.I) if txt(s)]
    segs = [txt(s) for s in raw]
    if not segs:
        raise ValueError("District %s: an empty member cell" % d)
    if re.fullmatch(r"vacant(?: seat)?", segs[0], re.I) and len(segs) == 1:
        return vacant()
    name = segs[0]
    if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
        raise ValueError("District %s: %r does not look like a name" % (d, name))
    phones = []
    for extra, html_ in zip(segs[1:], raw[1:]):
        if not PHONE.match(extra):
            raise ValueError("District %s: unexpected line %r under %r" % (d, extra, name))
        if not isinstance(phones, Withheld):
            got = read_phones(html_, strict=True)
            phones = got if isinstance(got, Withheld) else phones + got
    if any(re.search(r"mailto:", r, re.I) for r in raw[1:]):
        raise ValueError("District %s: an e-mail link in %r's cell is not on the name" % (d, name))
    mails = read_emails(raw[0])
    if not isinstance(mails, Withheld) and len(mails) > 1:
        raise ValueError("District %s: %r's name carries %d e-mail addresses"
                         % (d, name, len(mails)))
    return member(name, phones=phones, email=member_email(mails, DOMAINS))


def parse(pages):
    page = pages[URLS[0]]
    if "Three members from each of the 7" not in re.sub(r"\s+", " ", page):
        raise ValueError("the page no longer states three members from each of 7 districts")
    body = re.search(r"<tbody\b[^>]*>(.*?)</tbody>", page, re.S | re.I)
    if not body:
        raise ValueError("no commission table body on the page")
    districts = {}
    for row in ROW.findall(body.group(1)):
        cells = CELL.findall(row)
        if not cells:
            continue
        head = HEAD_RE.search(cells[0])
        label = txt(head.group(1)) if head else ""
        m = LABEL.match(label)
        if not head or not m or district_number(label) != int(m.group(1)):
            raise ValueError("a table row does not open with a 'District N' heading: %r" % label[:60])
        d = m.group(1)
        if d in districts:
            raise ValueError("District %s has two rows" % d)
        seats = [read_cell(d, c) for c in cells[1:]]
        if len(seats) != SEATS.get(d):
            raise ValueError("District %s row has %d member cells, the county elects %s"
                             % (d, len(seats), SEATS.get(d)))
        districts[d] = seats
    if set(districts) != set(SEATS):
        raise ValueError("the table names districts %s, not 1..7" % sorted(districts, key=int))
    return {"districts": districts, "atLarge": []}
