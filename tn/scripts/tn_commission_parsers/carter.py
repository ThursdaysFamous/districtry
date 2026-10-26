"""Carter County's commission has 24 seats, three in each of 8 districts ("3
seats for each of the 8 legislative districts", the county's election office
page says). No seat is called by a letter or number, so no seat is recorded.

The Commissioners page (government/commissioners.php, a Revize site) is one
table with a row per seat: District / First Name / Last Name / Email / Phone.
The district cell reads "1st District – Hunter, Midway, and Unaka
communities"; the leading ordinal is the district. A name is paired with the
district in its own row; nothing is read from order, and each district must
hold exactly the three seats the county elects there. One row reads "VACANT"
with its other cells empty (District 5) and is recorded vacant, as the county
states it: its election office page puts a "5th District County Commission
unexpired term (1 seat)" on the 3 November 2026 ballot, because only two
candidates ran there in August.

E-mail and phone: each row's own e-mail cell and phone cell are read, as
printed, under Adam's rulings of 2026-10-17 (a number or an address a
government prints beside an official ships).

Currency, checked 2026-10-26: every member on this page is a winner of the
6 August 2026 election in the district the page gives, by the Carter County
Election Commission's "Official Results For August State Primary and County
General" (a 51-page scan, certified 17 August 2026, linked from the county's
election office page). That file is linked as cartercountytn.gov/<name>.pdf
with a "?t=" query added; the county's own address WITHOUT the query
redirects to cms3.revize.com/revize/cartercounty/<name>.pdf, and that host's
robots.txt allows "/*.pdf$" (line 20) while refusing everything else, so the
address that ends in ".pdf" is the one read, with robots.txt asked again at the
redirect. District 1 Christie Grindstaff, Nick Holder, Keith Range; District 2
Julie Guinn, Richard Derrick Guinn (the page's Derrick Guinn, whose county
address is richard.guinn@), Avery "Pops" Wynn (three candidates, three seats);
District 3 Steve Burrough, Charles D. Von Cannon, Bradley N. Johnson; District
4 Jason Lyons, Gary Kemp, Austin Jaynes; District 5 Lisa Childress and
Charlene Thomas (two candidates); District 6 Travis Hill, Todd Smith, Taylor
Brown; District 7 Carole Whaley, Scotty Hall, Michael Miller; District 8 Wes
Holtsclaw, Kelly Collins, Thomas Proffitt. Names are kept as the page prints
them.

Held until then: every county document was linked with the "?t=" query, which
the file host's robots.txt refuses, and the page carries no date, so nothing
checked it."""
import re
from ._common import txt, member, member_email, read_emails, read_phones, vacant

COUNTY = "Carter"; FIPS = "019"
DOMAINS = ("cartercountytn.gov",)
URLS = ["https://cartercountytn.gov/government/commissioners.php"]
SEATS = {str(n): 3 for n in range(1, 9)}
AT_LARGE = 0

TABLE_RE = re.compile(r"<table\b.*?</table>", re.S)
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t([dh])\b[^>]*>(.*?)</t\1>", re.S)
DISTRICT_RE = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District\b")
HEADER = ["District", "First Name", "Last Name", "Email", "Phone"]


def parse(pages):
    page = pages[URLS[0]]
    tables = [t for t in TABLE_RE.findall(page) if ROW_RE.search(t)
              and [txt(c[1]) for c in CELL_RE.findall(ROW_RE.search(t).group(1))] == HEADER]
    if len(tables) != 1:
        raise ValueError("expected one District/First Name/Last Name/Email/Phone table, found %d"
                         % len(tables))
    districts = {}
    for row in ROW_RE.findall(tables[0])[1:]:
        cells = [c[1] for c in CELL_RE.findall(row)]
        if len(cells) != 5:
            raise ValueError("a commissioner row has %d cells, not 5" % len(cells))
        label = txt(cells[0])
        m = DISTRICT_RE.match(label)
        if not m:
            raise ValueError("row district %r is not 'Nth District'" % label)
        n = m.group(1)
        first, last = txt(cells[1]), txt(cells[2])
        if first.upper() == "VACANT":
            if last or txt(cells[3]) or txt(cells[4]):
                raise ValueError("District %s: a VACANT row carries other text" % n)
            districts.setdefault(n, []).append(vacant())
            continue
        name = (first + " " + last).strip()
        if re.search(r"\bvacan", name, re.I) or not re.fullmatch(r"[A-Z][A-Za-z.'’ -]+", name) \
                or not first or not last:
            raise ValueError("District %s: %r does not look like a name" % (n, name))
        districts.setdefault(n, []).append(member(
            name, email=member_email(read_emails(cells[3]), DOMAINS),
            phones=read_phones(cells[4])))
    for n, want in SEATS.items():
        if len(districts.get(n, [])) != want:
            raise ValueError("District %s: the page has %d rows, the county elects %d"
                             % (n, len(districts.get(n, [])), want))
    extra = set(districts) - set(SEATS)
    if extra:
        raise ValueError("the page names districts the county does not have: %s" % sorted(extra))
    return {"districts": districts, "atLarge": []}
