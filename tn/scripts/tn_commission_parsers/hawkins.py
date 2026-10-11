"""Hawkins County elects 14 commissioners from 7 districts, two in each (the
ballot says "Vote For Two (2)" and names no seat, so none is recorded).

The commission page (hawkinscountytn.gov/county_commission.html) is one table
whose header is District | Name | Phone. Each district is one row: a
<th scope="row"> holding the district number, a cell holding that district's
members one per <br>-separated line, and a cell of phone numbers. Each member
line reads "Name, street, town, TN ZIP"; the name is what stands before the
first comma, and the rest must begin with a street number or a P.O. box, so a
name written with a comma in it raises rather than being cut short. A member
is paired with the number in the header cell of the row it sits in, never
with its position. A district row seen twice raises; the table's empty
trailing row is skipped.

PRIVACY: every member line carries the member's HOME ADDRESS (street, town,
ZIP), and the third cell holds their personal phones; only the text before the
first comma of each line is read. The page publishes no e-mail.

Currency: NO RESULTS OF THE 6 AUGUST 2026 ELECTION COULD BE READ ON A
GOVERNMENT HOST. hawkinscountytn.gov/election_commission.html links no
results (its sample ballot and agenda are November 2026 documents), and the
state's results site elections.tn.gov refused our client (HTTP 403). The
fallback used is the "Minutes of Regular Session of Hawkins County Commission
Meeting, September 28, 2026" on the County Clerk's site, which the county site
links as the commission's documentation (hawkinscountyclerk.com, wp-content/
uploads/2026/10/doc00713020261006154826.pdf, scanned, read as an image):
14 commissioners present, 0 absent, and its roll calls name the same 14
people as this page (Trent, Gibson, Patterson, Barrett, Vaughan, Williams,
Gilliam, Bishop, Davis, Miller, Cope, Barker, Palmer, Jinks; "Matt Williams",
"Josh Gilliam" and "Robbie Palmer" there). The minutes do not give districts.
The districts were compared only with a copy of the county's official sample
ballot for 6 August 2026 published by WATE (a news site, not a government
host): each of the 14 was a commission candidate in the district this page
puts them in, and Districts 1, 4, 5 and 7 were uncontested (two candidates for
two seats). So membership is current on county evidence, and the district
pairing rests on the page plus a non-government copy of the ballot.

Not recorded: the minutes of 28 September 2026 elect Josh Gilliam Chair Pro
Tempore and County Mayor David Linkous chairman; this page states neither."""
import re
from ._common import txt, member, district_number

COUNTY = "Hawkins"; FIPS = "073"
DOMAINS = ("hawkinscountytn.gov",)
URLS = ["https://www.hawkinscountytn.gov/county_commission.html"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0

HEAD = ["District", "Name", "Phone"]
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
SUFFIX = re.compile(r"^(Jr|Sr|II|III|IV)\.?$")
ADDRESS = re.compile(r"^(\d|P\.?\s*O\.?\s*Box\b)", re.I)


def _member_line(line, d):
    parts = [p.strip() for p in line.split(",")]
    name = parts[0]
    rest = parts[1:]
    if rest and SUFFIX.match(rest[0]):
        name, rest = "%s, %s" % (name, rest[0]), rest[1:]
    if not rest or not ADDRESS.match(rest[0]):
        raise ValueError("District %s: %r is not 'Name, street address, ...'" % (d, line))
    bare = re.sub(r",\s*(Jr|Sr|II|III|IV)\.?$", "", name)
    if not NAME.match(bare):
        raise ValueError("District %s: %r is not a name" % (d, name))
    return member(name)


def parse(pages):
    page = pages[URLS[0]]
    tables = [t for t in re.findall(r"<table\b[^>]*>(.*?)</table>", page, re.S)
              if [txt(x) for x in re.findall(r"<th\b[^>]*scope=\"col\"[^>]*>(.*?)</th>", t, re.S)] == HEAD]
    if len(tables) != 1:
        raise ValueError("expected one District | Name | Phone table, found %d" % len(tables))
    districts = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", tables[0], re.S):
        th = re.search(r'<th\b[^>]*scope="row"[^>]*>(.*?)</th>', row, re.S)
        if not th:
            continue
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        label = txt(th.group(1))
        if not label and not any(txt(c) for c in cells):
            continue
        if not re.match(r"^\d{1,2}$", label) or len(cells) != 2:
            raise ValueError("a district row reads %r with %d cells" % (label, len(cells)))
        d = str(district_number("District " + label))
        if d in districts:
            raise ValueError("District %s has two rows" % d)
        lines_ = [txt(x) for x in re.split(r"<br\s*/?>", cells[0], flags=re.I)]
        found = [_member_line(x, d) for x in lines_ if x]
        if not found:
            raise ValueError("District %s row names nobody" % d)
        districts[d] = found
    return {"districts": districts, "atLarge": []}
