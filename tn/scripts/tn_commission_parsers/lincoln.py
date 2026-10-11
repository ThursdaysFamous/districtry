"""Lincoln County elects 24 commissioners from 8 districts, three in each (the
ballot names no seat, so none is recorded).

The county's "Chairman Commission" page (a Revize directory page) is one table,
id="example", whose header is District | First Name | Last Name | Email |
Phone. Each commissioner is one row; the district is that row's own first
cell, a bare numeral, and the name is the row's First Name and Last Name
cells joined. The first row's district cell reads "County Mayor" (Walt
Patrick): in Lincoln County the county mayor presides over the commission as
its chairman, which is why the page carries that title, but the mayor is not a
commission seat and that row is not recorded. Any other non-numeral district
cell, a header that changes, or a row with other than five cells raises.

PRIVACY: every row carries a phone number, and most are personal (some on
Alabama 256 and Nashville 615 area codes); the mayor's row carries the county
office line. No phone is recorded. E-mails are kept only on
lincolncountytn.gov and only when the address is plainly the member's: its
local part must start with the member's first initial and contain the surname
(jhammons@, cynthia.bates@, jnix@ for Jason Gary Nix). The mayor's
mayor@lincolncountytn.gov is never read.

Currency: NO RESULTS OF THE 6 AUGUST 2026 ELECTION COULD BE READ ON A
GOVERNMENT HOST. The county's Election Commission page
(lincolncountytn.gov/county_directory/election_commission.php) now carries
only November 2026 material and links no August results, and nothing on the
county's document hub is a results document. What was read instead, all on
lincolncountytn.gov, 2026-10-11:
  - the minutes of the outgoing commission's last meeting, 18 August 2026
    (roll call of 24 by name): ten of them are on this page (Creson, Rogers,
    Walker, Atchley, Mitchell, Hunter, Steve Spray, Nix, Bryant, Guntherberg)
    and the other fourteen are not, so the page was rewritten after the
    election;
  - the agenda of the new commission's first regular meeting, 15 September
    2026, which names Jim Hammons as "a newly elected County Commissioner";
  - the county's "Lincoln County, TN - Committees Roster", "Updated September
    2026" (Documents/Document Hub/Lincoln County Committee Roster.pdf, created
    2026-09-24), which places all 24 people on this page on the new
    commission's committees (Ricky Bryant as "Chair Pro Tempore (Sept 2027)").
None of those gives districts. The district each name sits under was compared
only with WAFF 48's "Lincoln County Local Election Winners" list of 7 August
2026 (a news site, not a government host), which agrees in all eight
districts (it prints "Robert Spray" in District 4 where the county prints
Steve Spray). So the membership is current on county evidence and the
district pairing rests on the county's own page plus a news report.

Not recorded: the Chair Pro Tempore title (it is on the committees roster,
not this page)."""
import re
from ._common import txt, member, mailtos, county_email

COUNTY = "Lincoln"; FIPS = "103"
DOMAINS = ("lincolncountytn.gov",)
URLS = ["https://lincolncountytn.gov/county_directory/chairman_commission.php"]
SEATS = {str(i): 3 for i in range(1, 9)}
AT_LARGE = 0

HEAD = ["District", "First Name", "Last Name", "Email", "Phone"]
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def _own(addr, first, last):
    local = re.sub(r"[^a-z]", "", addr.split("@", 1)[0].lower())
    sur = re.sub(r"[^a-z]", "", last.lower())
    return local.startswith(first[:1].lower()) and sur in local


def parse(pages):
    page = pages[URLS[0]]
    tab = re.search(r'<table\b[^>]*id="example"[^>]*>(.*?)</table>', page, re.S)
    if not tab:
        raise ValueError("no table#example on the page")
    head = [txt(x) for x in re.findall(r"<th\b[^>]*>(.*?)</th>", tab.group(1), re.S)]
    if head != HEAD:
        raise ValueError("table header is %r" % head)
    body = re.search(r"<tbody\b[^>]*>(.*?)</tbody>", tab.group(1), re.S)
    if not body:
        raise ValueError("table has no body")
    districts, mayor = {}, 0
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", body.group(1), re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        if not cells and not txt(row):
            continue
        if len(cells) != 5:
            raise ValueError("a row with %d cells: %r" % (len(cells), txt(row)[:80]))
        dist, first, last = txt(cells[0]), txt(cells[1]), txt(cells[2])
        if dist == "County Mayor":
            mayor += 1
            continue
        if not re.match(r"^\d{1,2}$", dist):
            raise ValueError("district cell %r is not a district number" % dist)
        name = "%s %s" % (first, last)
        if not first or not last or not NAME.match(name):
            raise ValueError("District %s: %r is not a name" % (dist, name))
        addr = county_email(mailtos(cells[3]), DOMAINS)
        if addr and not _own(addr, first, last):
            raise ValueError("%r: county address %r does not look like the member's" % (name, addr))
        districts.setdefault(str(int(dist)), []).append(member(name, email=addr))
    if mayor != 1:
        raise ValueError("expected one County Mayor row, found %d" % mayor)
    return {"districts": districts, "atLarge": []}
