"""Blount County Commission: 21 seats in 10 districts, two per district except
District 4, which elects three. The county's own Commissioners page (CivicPlus)
is built from layout widgets: each district opens with a one-cell table widget
whose header reads "District N", followed by that district's precinct-and-map
widget (its map link reads "District N Map (PDF)" or "District N Map Part k
(PDF)") and then one widget per seat (name, sometimes a phone, a blounttn.gov
e-mail) each followed by a "Committees" widget. The page is cut at those
"District N" headers and every name is paired with the header of the section
it sits in; the section's own map link must name the same district, so a
header that drifted from its content raises. The widgets are not uniform
(most are Froala "fr-view" editors, one is a "textContent" text widget), so
the section is read as visible lines rather than by widget class.

A seat is a name line followed (after at most one phone line) by an e-mail
line, or the line "Vacant" (District 4's third seat, which the page also marks
with a "Vacant Seat" image). Every seat on this page, the vacant one included,
carries its own "Committees" widget, so the number of "Committees" lines in a
section must equal the seats found there; a seat whose e-mail went missing
therefore raises instead of being dropped.

The page does not print seat letters. The county's "Commission List with
Email 2026" PDF (DocumentCenter/View/30293, "Legislative Body, Term:
9/1/2026 - 8/31/2030", created 2026-09-02) gives the same 20 names and the
vacancy by district AND seat letter (District 4 Seat C "Vacant"); it agreed
with this page on 2026-10-11 and is not read here.

All 21 seats were on the 6 August 2026 county general ballot. Checked
2026-10-11 against the Blount County Election Commission's "August 6, 2026
County Totals" (blounttn.gov DocumentCenter/View/30229, dated August 19,
2026): the 20 named members are the 20 winners of their district's seats
(Roy L. "Hoot" Shields and Robert G. Simerly are spelled without the
nickname/initial here). District 4 Seat C was WON by John Edwin Giles (2,807
to 850), yet both this page and the county's post-election list show that
seat "Vacant"; why he is not seated is not stated on either county source
read. The county says vacant, so it is recorded vacant.

Roles: "Chairman" and "Vice Chairman" are recorded. "Parliamentarian" (on
Tanner Jones) is not a commission office and is dropped.

Phones: the phone line a seat prints between its name and its e-mail is
recorded as printed (16 of the 20 members print one), under Adam's ruling of
2026-10-17 that a number a government publishes beside an official ships
whosever line it is. None is the commission office's (865) 273-5830, which
OFFICE_LINES keeps off every record. The page prints no address. E-mails are
kept only on blounttn.gov."""
import re
from ._common import lines, member, vacant, county_email, district_number, read_phones

COUNTY = "Blount"; FIPS = "009"
DOMAINS = ("blounttn.gov",)
URLS = ["https://blounttn.gov/835/Commissioners"]
SEATS = {"1": 2, "2": 2, "3": 2, "4": 3, "5": 2, "6": 2, "7": 2, "8": 2, "9": 2, "10": 2}
AT_LARGE = 0
# The commission office's own line.
OFFICE_LINES = ("865-273-5830",)

HEADER = re.compile(r'<th scope="col"[^>]*>\s*District\s+(\d{1,2})\s*</th>')
SECTION_END = re.compile(r'class="newCP"|id="gbsContainerTS"')
PHONE = re.compile(r"^\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}$")
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
MAP = re.compile(r"^District\s+(\d{1,2})\s+Map\b", re.I)
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
ROLES = {"chairman": "Chairman", "vice chairman": "Vice Chairman", "vice-chairman": "Vice Chairman",
         "chairman pro tem": "Chairman Pro Tem", "chairman pro tempore": "Chairman Pro Tempore"}
NOT_OFFICES = {"parliamentarian"}


def split_name(line):
    """'Nick Bright, Chairman' -> ('Nick Bright', 'Chairman')."""
    name, role = line, None
    if "," in line:
        name, tail = [x.strip() for x in line.split(",", 1)]
        t = tail.lower()
        if t in ROLES:
            role = ROLES[t]
        elif t not in NOT_OFFICES:
            raise ValueError("%r: unknown title after the name" % line)
    if not NAME.match(name):
        raise ValueError("%r does not look like a name" % line)
    return name, role


def read_section(n, ls):
    maps = {int(m.group(1)) for m in (MAP.match(x) for x in ls) if m}
    if maps != {int(n)}:
        raise ValueError("District %s section's map links name districts %s" % (n, sorted(maps)))
    seats = []
    for i, x in enumerate(ls):
        if x == "Vacant":
            seats.append(vacant())
        elif EMAIL.match(x):
            j, phones = i - 1, []
            if j >= 0 and PHONE.match(ls[j]):
                phones = read_phones(ls[j], strict=True)
                j -= 1
            if j < 0:
                raise ValueError("District %s: an e-mail %r with no name above it" % (n, x))
            name, role = split_name(ls[j])
            seats.append(member(name, role=role, email=county_email([x], DOMAINS), phones=phones))
    committees = sum(1 for x in ls if x == "Committees")
    if committees != len(seats):
        raise ValueError("District %s: %d seat blocks (Committees widgets) but %d seats read"
                         % (n, committees, len(seats)))
    return seats


def parse(pages):
    page = pages[URLS[0]]
    heads = list(HEADER.finditer(page))
    if not heads:
        raise ValueError("no 'District N' table headers on the page")
    end = SECTION_END.search(page, heads[-1].end())
    if not end:
        raise ValueError("cannot find where the last district's section ends")
    districts = {}
    for k, h in enumerate(heads):
        n = h.group(1)
        if district_number("District " + n) != int(n):
            raise ValueError("header %r" % h.group(0))
        if n in districts:
            raise ValueError("District %s has two headers" % n)
        stop = heads[k + 1].start() if k + 1 < len(heads) else end.start()
        districts[n] = read_section(n, lines(page[h.end():stop]))
    return {"districts": districts, "atLarge": []}
