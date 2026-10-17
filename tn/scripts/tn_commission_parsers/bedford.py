"""Bedford County elects 18 commissioners, two from each of 9 districts. The
county's "About the county commission" page (read 2026-10-11) says "There is
one race in each district, with the top two finishers in each district
elected to that district's two seats", so no seat label exists and none is
recorded. The same page says the County Mayor chairs the commission; the
mayor is not one of the 18, so no chair is recorded.

The Board of Commissioners page (Revize) carries one table under the heading
"BEDFORD COUNTY BOARD OF COMMISSIONERS (AS OF SEPT. 1, 2026)". Its first row
is the column header (PHONE, EMAIL); after it, a row whose first cell reads
"DISTRICT N" and whose other cells are empty opens that district, and each
following row until the next such row is one member: a name cell (sometimes
with a photo), a spacer, a phone cell and an e-mail cell. A member is paired
with the "DISTRICT N" row that opens the table section they sit in, the way a
heading is read, and each section must hold exactly the seats the county
elects there; a row that is neither shape raises. The heading must still
read "AS OF SEPT. 1, 2026": it is the only evidence of this table's currency
(below), so a changed date means the table changed and is refused until its
names are checked again.

PRIVACY: the member rows print up to two phone numbers each in their PHONE
cell, all different, and they are recorded as printed, the first as the
member's phone and a second beside it, under Adam's ruling of 2026-10-17 that
a number a government publishes beside an official ships whosever line it
is. The page prints no address. Ten of the 18 e-mails are personal
(yahoo, gmail, outlook, icloud, a business domain). An e-mail is kept only
when it is on bedfordcountytn.gov AND its local part carries the member's
surname.

Currency: NOT checked against the election results, because they cannot be
read with this project's client. The Bedford County Election Commission's
"Past Election Results" page (bedfordcountytn.gov/departments/elections/
past_election_results.php) links "County General Results 8-6-2026" as a PDF
(20260825075719.pdf); the county's site answers that request with a redirect
to its Revize CMS host (path /revize/bedfordtn/...), whose robots.txt
disallows it (`Disallow: /`, line 22, binding this client), so it was not
read (2026-10-11). Both spellings of the link tried (relative to the page,
and to the page's <base href>) were redirected there, so no other document
the site serves, the commission's minutes included, was tried. The fallback evidence used is the
page's own heading, "BEDFORD COUNTY BOARD OF COMMISSIONERS (AS OF SEPT. 1,
2026)", the first day of the term that the 6 August 2026 election filled."""
import re
from ._common import txt, mailtos, district_number, member, read_phones

COUNTY = "Bedford"; FIPS = "003"
DOMAINS = ("bedfordcountytn.gov",)
URLS = ["https://www.bedfordcountytn.gov/government/board_of_commissioners.php"]
SEATS = {str(i): 2 for i in range(1, 10)}
AT_LARGE = 0

HEADING = re.compile(r"BEDFORD COUNTY BOARD OF COMMISSIONERS \(AS OF SEPT\. 1, 2026\)")
DISTRICT = re.compile(r"^DISTRICT (\d{1,2})$")
NAME = re.compile(r'^[A-Z][A-Za-z.\'’" -]+$')
PHONE = re.compile(r"^(?:\(?\d{3}\)?[-. ]?\d{3}[-. ]\d{4}\s*)+$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surname(name):
    words = [w for w in re.sub(r'"[^"]*"', " ", name).replace(",", " ").split() if w]
    while words and words[-1].lower().strip(".") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def parse(pages):
    page = pages[URLS[0]]
    head = HEADING.search(page)
    if not head:
        raise ValueError("the 'BOARD OF COMMISSIONERS (AS OF SEPT. 1, 2026)' heading is gone")
    table = re.search(r"<table\b.*?</table>", page[head.end():], re.S)
    if not table:
        raise ValueError("no table after the roster heading")
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", table.group(0), re.S)
    if not rows:
        raise ValueError("the roster table has no rows")
    first = [txt(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", rows[0], re.S)]
    if first != ["", "", "PHONE", "EMAIL"]:
        raise ValueError("the roster table's header row is %r" % first)
    districts, current = {}, None
    for r in rows[1:]:
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S)
        if len(cells) != 4:
            raise ValueError("a roster row with %d cells" % len(cells))
        text = [txt(c) for c in cells]
        m = DISTRICT.match(text[0])
        if m:
            if any(text[1:]):
                raise ValueError("district row %r carries more than its label" % text)
            current = m.group(1)
            if district_number(text[0]) != int(current):
                raise ValueError("district row %r read two ways" % text[0])
            if current in districts:
                raise ValueError("District %s opens twice" % current)
            districts[current] = []
            continue
        if current is None:
            raise ValueError("a member row before the first DISTRICT row: %r" % text)
        name = text[0]
        if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
            raise ValueError("District %s: %r does not look like a name" % (current, name))
        if text[1] or (text[2] and not PHONE.match(text[2])):
            raise ValueError("District %s: %r's row has unexpected cells" % (current, name))
        email = None
        for a in mailtos(cells[3]):
            if not _on_domain(a):
                continue
            if _surname(name) not in a.split("@", 1)[0].lower():
                raise ValueError("county address %r does not carry %r's surname" % (a, name))
            email = a
            break
        districts[current].append(member(name, email=email, phones=read_phones(cells[2], strict=True)))
    for n, seats in districts.items():
        if len(seats) != SEATS.get(n):
            raise ValueError("District %s has %d member rows, the county elects %s"
                             % (n, len(seats), SEATS.get(n)))
    return {"districts": districts, "atLarge": []}
