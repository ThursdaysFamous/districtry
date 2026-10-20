"""Crockett County elects 24 commissioners, two from each of 12 districts, and
elects them by position: each district's two seats are separate one-member
races, "County Commissioner District N Position 1" and "... Position 2", on
the ballot. The position is recorded as the seat ("Position 1"). The page
names no commission office, so no role is recorded.

THE ROSTER PAGE IS THE ELECTION COMMISSION'S, NOT THE COUNTY GOVERNMENT'S.
No Crockett County government site publishing the commission was found (the
survey of 2026-10-11 found no county-government domain that answers). The
Crockett County Election Commission's own site (crockettvote.com, footer "©
2026 All Rights Reserved | Crockett County Election Commission") publishes
the commission under Elected Officials > County Commission, by district and
position, and that page is read.

The page holds one table (a Duda table widget) with the columns "District",
"Name", "Address", "Phone"; each data row's first cell reads "N Position K"
and its second cell is the name. District and position are read from that
first cell of the same row, never from order. Every row must have that
shape, each (district, position) may appear once, and every district 1..12
must have Positions 1 and 2. The widget also carries its whole table a
second time, base64-encoded in a "data-ext" attribute; that copy is not read.

PRIVACY: the table's "Address" and "Phone" columns are each member's home
street address, town and ZIP and a phone. The "Phone" cell is recorded as
printed, under Adam's ruling of 2026-10-17 that a number a government
publishes beside an official ships whosever line it is (the Election
Commission is a county office). The "Address" cell is never read, and a
"Phone" cell holding anything but a number and its label raises. One cell
prints its number as "73.1-..." with a stray point inside the area code; it
is not a whole telephone number as printed, so that member's number is left
off rather than corrected. The Election Commission's own phone and fax, in
the page footer, are OFFICE_LINES and never land on a member. The page has
no e-mail.

Names are kept as printed, middle initials included ("William C Hooten",
"Ronde' J Howell", "Alice F McDearman").

Currency: checked 2026-10-11 against the Election Commission's own "Summary
Results Report", 26 Aug Crockett_ST_PR_CO_GEN, August 6, 2026 (crockettvote.com
Election Results, "August 6, 2026 State and Federal Primary and County
General Results", irp.cdn-website.com/82953245/files/uploaded/
8-6-26+Unofficial+Results+SFPSCG.pdf, the commission site's own file store;
a 17-page scan headed "UNOFFICIAL RESULTS", Election Summary 08/06/2026 8:14
PM, 12 of 12 precincts, read as images; no certified copy is posted). Every
one of the 24 positions on this page is that position's winner. Twenty-two
were uncontested. District 8 Position 2: Dustin Bodkins 152, Eric Ivester 48.
District 7 Position 2 had "No Candidate Qualified"; of its 8 write-in votes,
4 are "Write-In: Megan Sparks" and 4 "Not Assigned", so Megan Sparks is the
only write-in the report names, and this page seats her. Ballot spellings
differ only by punctuation ("Harvey D. Bradshaw", "Taylor L. Branch",
"Ronde' J. Howell", "Alice F. McDearman", "Jared C. Foust")."""
import re
from ._common import txt, member, read_phones

COUNTY = "Crockett"; FIPS = "033"
DOMAINS = ("crockettvote.com",)
URLS = ["https://www.crockettvote.com/county-commission"]
SEATS = {str(i): 2 for i in range(1, 13)}
AT_LARGE = 0
# The Election Commission's own phone and fax, in the page footer.
OFFICE_LINES = ("731-696-5465", "731-696-4977")

ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
CELL = re.compile(r"<t([dh])\b[^>]*>(.*?)</t[dh]>", re.S | re.I)
LABEL = re.compile(r"^(\d{1,2})\s+Position\s+([12])$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
HEADER = ["District", "Name", "Address", "Phone"]


def parse(pages):
    page = pages[URLS[0]]
    if "Crockett County Election Commission" not in page:
        raise ValueError("the page no longer names the Crockett County Election Commission")
    tables = re.findall(r"<table\b[^>]*>(.*?)</table>", page, re.S | re.I)
    if len(tables) != 1:
        raise ValueError("expected one table on the page, found %d" % len(tables))
    districts, seen, header_seen = {}, set(), False
    for row in ROW.findall(tables[0]):
        cells = CELL.findall(row)
        if all(kind.lower() == "h" for kind, _ in cells):
            if [txt(c) for _, c in cells] != HEADER:
                raise ValueError("the table's header is %r" % [txt(c) for _, c in cells])
            header_seen = True
            continue
        if len(cells) != 4:
            raise ValueError("a table row has %d cells, not District/Name/Address/Phone" % len(cells))
        label, name = txt(cells[0][1]), txt(cells[1][1])
        m = LABEL.match(label)
        if not m:
            raise ValueError("a row's District cell is not 'N Position K': %r" % label)
        d, pos = m.group(1), "Position " + m.group(2)
        if (d, pos) in seen:
            raise ValueError("District %s %s appears twice" % (d, pos))
        seen.add((d, pos))
        if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
            raise ValueError("District %s %s: %r does not look like a name" % (d, pos, name))
        districts.setdefault(d, []).append(
            member(name, seat=pos, phones=read_phones(cells[3][1], strict=True)))
    if not header_seen:
        raise ValueError("the table has no District/Name/Address/Phone header")
    want = {(str(i), "Position %d" % k) for i in range(1, 13) for k in (1, 2)}
    if seen != want:
        raise ValueError("positions missing or extra: %s"
                         % sorted(want ^ seen, key=lambda x: (int(x[0]), x[1])))
    return {"districts": districts, "atLarge": []}
