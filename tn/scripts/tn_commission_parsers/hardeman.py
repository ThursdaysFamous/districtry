"""Hardeman County's commission has 16 members from 9 districts, as the
Hardeman County Election Commission's list of elected officials holds them:
three in Districts 1 and 5, two in Districts 2, 3 and 7, and one in Districts
4, 6, 8 and 9. The list numbers the seats inside a district ("District 1
Position 2"), and those positions are recorded as seats.

THE COUNTY'S OWN COMMISSION PAGE IS NOT READ. On 2026-10-26 the page on
hardemancounty.org still showed the eight districts of the plan before the
2021 redistricting and the outgoing commission, while the Comptroller's layer
the app draws has nine. The election commission's "Your Elected Officials"
page (www.hardemanvotes.com, the site the county's election page links) is a
table of Office name / Office level / Official name / Mailing address / Email,
and follows the nine-district plan; that table is the source, as Scott
County's election commission list is Scott's. The office cell reads "County
Commissioner, District N Position M", or "County Commissioner, District N" for
a district with one seat. A name is paired with the district in its own row;
nothing is read from order, and each district must hold exactly the seats the
list gives it.

PRIVACY: the table's Mailing address column is NEVER read. Its Email column is
read into `email`, as printed, under Adam's ruling of 2026-10-17 that an
address a government prints beside an official ships; the table prints no
telephone.

DISTRICT 9 IS THE ONE THING NOT ESTABLISHED. Its single row reads "District 9
Position 1", the only one-seat district the list gives a position number to.
No second District 9 row exists, vacant or otherwise, and the list totals 16,
the number the county's old page and its September minutes both show; so one
seat is recorded, and whether District 9 elects a second is not established.

Currency, checked 2026-10-26: the minutes of the Legislative Body's meeting of
15 September 2026 (hardemancounty.org/images/uploads/site_files/
September_15_2026_Minutes.pdf, a scan) record as present "a quorum of
Commissioners, namely" exactly these sixteen, without districts: David Bell,
Cory Bufford, Russell Deberry, Michion Gatlin, Ricky Griggs, Bobby Hensley,
Terry Howell, Joe Jenkins, Jeff Kennamore, Chandra Y. Lake, Johnny Lanier,
Jackie Sain, Dylan Stewart, Johnny Weems, Erica Woods and Bobby Wright. The
four outgoing members the county's page still lists are absent from them. The
election commission's August 2026 results are on Google Drive, whose
robots.txt refuses this project, so they were not read and the districts rest
on the election commission's own list, as Scott's do. Names are kept as the
list prints them.

Held until then: on 2026-10-11 and 2026-10-13 only the county's stale page had
been read."""
import re
from ._common import txt, member, member_email, read_emails

COUNTY = "Hardeman"; FIPS = "069"
DOMAINS = ("hardemancounty.org",)
URLS = ["https://www.hardemanvotes.com/p/your-elected-officials.html"]
SEATS = {"1": 3, "2": 2, "3": 2, "4": 1, "5": 3, "6": 1, "7": 2, "8": 1, "9": 1}
AT_LARGE = 0

ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t([dh])\b[^>]*>(.*?)</t\1>", re.S)
OFFICE_RE = re.compile(r"^County Commissioner, District (\d{1,2})(?: Position (\d))?$")
HEADER = ["Office name", "Office level", "Official name", "Mailing address", "Email"]


def parse(pages):
    page = pages[URLS[0]]
    rows = [[c[1] for c in CELL_RE.findall(r)] for r in ROW_RE.findall(page)]
    if not any([txt(c) for c in r] == HEADER for r in rows):
        raise ValueError("no Office name / Office level / Official name / Mailing address / "
                         "Email header row")
    districts = {}
    for cells in rows:
        office = txt(cells[0]) if cells else ""
        if "Commission" not in office or "County Commissioner" not in office:
            continue
        m = OFFICE_RE.match(office)
        if not m or len(cells) != 5 or txt(cells[1]) != "County":
            raise ValueError("commission row %r is not shaped as it was" % office)
        n, pos = m.group(1), m.group(2)
        if (pos is None) != (SEATS.get(n) == 1) and not (n == "9" and pos == "1"):
            raise ValueError("District %s: position %r does not fit the seats the list gives"
                             % (n, pos))
        name = txt(cells[2])
        if re.search(r"\bvacan", name, re.I) or not re.fullmatch(r"[A-Z][A-Za-z.,'’() -]+", name):
            raise ValueError("District %s: %r does not look like a name" % (n, name))
        seat = ("Position " + pos) if pos and SEATS.get(n, 0) > 1 else None
        districts.setdefault(n, []).append(member(
            name, seat=seat, email=member_email(read_emails(cells[4]), DOMAINS)))
    for n, want in SEATS.items():
        if len(districts.get(n, [])) != want:
            raise ValueError("District %s: the list names %d, it gave %d"
                             % (n, len(districts.get(n, [])), want))
    extra = set(districts) - set(SEATS)
    if extra:
        raise ValueError("the list names districts the county does not have: %s" % sorted(extra))
    return {"districts": districts, "atLarge": []}
