"""Benton County elects 18 commissioners, three from each of 6 districts (the
ballot reads "County Commission District N: Vote for 3" in every district and
names no seat or position, so no seat is recorded). The page names no chair.

The County Commission page is one table. Each district is a row whose first
cell holds an <h4> "First District" .. "Sixth District" and whose next three
cells each hold one member: a photo, then a mailto link whose text is the
member's name, then (in most cells) an address and a phone. Each name is
paired with the <h4> label in its own row; nothing is read from order. A row
must hold exactly the seats the county elects there, every district 1..6
exactly once. The name is the first line of the link's text (Barry Holland's
link also wraps his address and phone, which are cut off at the first <br>).
Where the photo carries a name in its alt text, its surname must equal the
name's ("Roseanne Ward" photo over "Rosanne Ward"); "Image Not Available"
photos are not compared.

PRIVACY: the cells print street addresses, towns, ZIPs and phones. The phones
are recorded as printed, under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is; only
telephone-shaped numbers are read from a cell, never its address, town or
ZIP. Every mailto link on the roster is off the
county's domain (gmail, yahoo, bellsouth, charter), and several plainly belong
to someone else (the link over Nicholas Horton's name is a bcos.org address
for another person, Barry Holland's a bctnso.org address for another person,
Keith Arnold's, Bret Burke's, Terry Kiehn's and Jerry Price's other people's
personal addresses, and two photo links share one address), so no e-mail is
recorded.

Names are kept as the page prints them. The page prints "Barry Holland" and
"Sam Shaw"; the results print "Holland, Berry R." and "Shaw, Samuel".

Currency: checked 2026-10-11 against the Benton County Election Commission's
own "Unofficial Results 8/6/2026" page (bentoncotnelections.com/unofficial,
the commission's site; its results archive offers no certified 2026 copy).
All 18 seats were on the 6 August 2026 ballot, and in every district the
three names on this page are the three marked "Win": D1 Horton 437, Davis 344,
Arnold 313 (Powers 165); D2 Vick 404, Shannon 373, Presson 320 (Bain 262,
Miller 231); D3 Furr 409, Burke 373, Shaw 277; D4 Melton 357, Green 304, Kirk
283 (Fowler 278, Watson 239); D5 Nunnery 301, Ward 285, Holland 275 (Lashlee
218, Williams 215, Anderson 146); D6 Kiehn 509, Price 475, Murphy 436. The
page itself carries no date."""
import re
from ._common import txt, district_number, member, read_phones

COUNTY = "Benton"; FIPS = "005"
DOMAINS = ("bentoncountytn.gov",)
URLS = ["https://bentoncountytn.gov/county_commission.html"]
SEATS = {str(i): 3 for i in range(1, 7)}
AT_LARGE = 0

ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
LABEL = re.compile(r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth) District$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’\" -]+$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def surname(s):
    words = [w for w in re.split(r"[\s,]+", s) if w]
    while words and words[-1].lower().strip(".") in SUFFIX:
        words.pop()
    return words[-1].lower() if words else ""


def read_cell(d, cell):
    names = []
    for inner in re.findall(r"<a\b[^>]*>(.*?)</a>", cell, re.S):
        first = txt(re.split(r"<br\s*/?>", inner, maxsplit=1, flags=re.I)[0])
        if first:
            names.append(first)
    if len(names) != 1:
        raise ValueError("%s District: a member cell holds %d named links: %r" % (d, len(names), names))
    name = names[0]
    if not NAME.match(name):
        raise ValueError("%s District: %r does not look like a name" % (d, name))
    alts = [txt(a) for a in re.findall(r'<img\b[^>]*\balt="([^"]*)"', cell)]
    if len(alts) != 1:
        raise ValueError("%s District: %r's cell has %d photos" % (d, name, len(alts)))
    if alts[0] != "Image Not Available" and surname(alts[0]) != surname(name):
        raise ValueError("%s District: photo %r does not match name %r" % (d, alts[0], name))
    return member(name, phones=read_phones(cell))


def parse(pages):
    page = pages[URLS[0]]
    start = page.find("County Commission</h2>")
    if start < 0:
        raise ValueError("no 'County Commission' heading on the page")
    tables = re.findall(r"<table\b[^>]*>(.*?)</table>", page[start:], re.S)
    if len(tables) != 1:
        raise ValueError("expected one roster table, found %d" % len(tables))
    districts = {}
    for row in ROW.findall(tables[0]):
        cells = CELL.findall(row)
        if not any(txt(c) for c in cells):
            continue                              # the trailing blank row
        label = txt(cells[0])
        m = LABEL.match(label)
        d = district_number(label)
        if not m or not d:
            raise ValueError("a row's first cell is not 'Nth District': %r" % label)
        if "<h4" not in cells[0]:
            raise ValueError("%s: the district label is not the row's <h4>" % label)
        d = str(d)
        if d in districts:
            raise ValueError("District %s has two rows" % d)
        seats = [read_cell(m.group(1), c) for c in cells[1:] if txt(c)]
        if len(seats) != SEATS.get(d):
            raise ValueError("District %s row has %d members, the county elects %s"
                             % (d, len(seats), SEATS.get(d)))
        districts[d] = seats
    return {"districts": districts, "atLarge": []}
