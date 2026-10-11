"""Stewart County elects 14 commissioners, two from each of 7 districts; the
ballot is "Vote For 2" in every district and names no seat, so no seat is
recorded. The page names no commission office, so no role is recorded.

The Commissioners page (a hand-built HTML template) lays the districts out in
three column tables, out of numeric order (1, 4, 7 / 2, 5 / 3, 6). In each
column a row holding an <h2> "District N" opens a district, and each
following member row (a photo link to the member's "full_info" page, a
spacer cell, and a text cell) belongs to that district until the next <h2>
row. A member is paired with the heading above it in the same column table,
never with its position on the page; a member row before any heading, a
heading that is not "District N", or a district that appears twice raises,
and every district 1..7 must appear.

The name is the first line of the member's text cell, read with the markup
removed rather than replaced by spaces, because the page breaks names across
tags ("E<strong>ric Watkins</strong>", "Terry / Fitzhugh" across two source
lines). Two photos carry the alt text "Thumb", so the photos are not read.

PRIVACY: every member's text cell continues with a home street address, a
town and ZIP, and one or two personal phones (Clint Mathis's first labelled
"(Home)"); none of it is read. The photo links lead to per-member
"full_info" pages, which are not read and not recorded as profile links. The
page prints no e-mail. No address, phone or e-mail is recorded.

Names are kept as printed. The ballot spells four of them more fully: "Ed
Williams" (here Edward Williams), "Leslie Elkins Bickford", "Melissa L.
Fields" and "Alexis Holley Taylor".

Currency: checked 2026-10-11 against the Stewart County Election Commission's
own "Summary Results Report", 2026 AUG Stewart ST_PRI_CO_GEN, August 6,
2026 (stewartcountyelection.com, linked from its 2026 Elections page as
"Unofficial Election Results", wp-content/uploads/2026/08/
0973_260806212327_001.pdf; a 7-page scan headed "UNOFFICIAL RESULTS",
Election Summary 08/06/2026 8:21 PM, 7 of 7 precincts, read as images; no
certified copy is posted there). In every district the two names here are
the two highest of the "County Commissioner District N - Vote For 2"
contest: D1 Elijah Thomas 260, Lane Page 236 (Corey Etherton 116, Michael A
Lorden 52); D2 Justin Booth 361, William Taylor 353; D3 Eric Watkins 390,
Shane Keatts 367; D4 Terry Fitzhugh 371, Ed Williams 218 (Adam Cathey 200);
D5 Leslie Elkins Bickford 372, Melissa L. Fields 360 (Archie L Cryer 283);
D6 Clint Mathis 542, Bradley Jones 451; D7 Mark Dortch 329, Alexis Holley
Taylor 257."""
import html as _html
import re
from ._common import member, district_number

COUNTY = "Stewart"; FIPS = "161"
DOMAINS = ("stewartcogov.com",)
URLS = ["https://www.stewartcogov.com/commissioners/commissioners.html"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0

COLUMN = re.compile(r'<table\b[^>]*class="main_table"[^>]*>(.*?)</table>', re.S | re.I)
ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
LABEL = re.compile(r"^District\s+(\d{1,2})$")
PHOTO = re.compile(r'<a class="iframe" href="full_info/[^"]+"')
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def _plain(fragment):
    """Text with tags removed outright (not replaced by spaces)."""
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def first_line(cell):
    for seg in re.split(r"<br\s*/?>|</p>", cell, flags=re.I):
        s = _plain(seg)
        if s:
            return s
    return ""


def parse(pages):
    page = pages[URLS[0]]
    # The navigation bar is a "main_table" too; the district columns are the
    # ones holding <h2> headings.
    columns = [c for c in COLUMN.findall(page) if H2.search(c)]
    if len(columns) != 3:
        raise ValueError("expected three district column tables, found %d" % len(columns))
    if any(PHOTO.search(c) for c in COLUMN.findall(page) if c not in columns):
        raise ValueError("a member photo sits outside the three district columns")
    districts = {}
    for col in columns:
        current = None
        for row in ROW.findall(col):
            head = H2.search(row)
            if head:
                label = _plain(head.group(1))
                m = LABEL.match(label)
                if not m or district_number(label) != int(m.group(1)):
                    raise ValueError("a heading is not 'District N': %r" % label)
                current = m.group(1)
                if current in districts:
                    raise ValueError("District %s has two headings" % current)
                districts[current] = []
                continue
            if not PHOTO.search(row):
                continue
            if current is None:
                raise ValueError("a member row sits before any District heading")
            cells = CELL.findall(row)
            if len(cells) != 3:
                raise ValueError("District %s: a member row has %d cells" % (current, len(cells)))
            name = first_line(cells[2])
            if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
                raise ValueError("District %s: %r does not look like a name" % (current, name))
            districts[current].append(member(name))
    if set(districts) != set(SEATS):
        raise ValueError("the page names districts %s, not 1..7" % sorted(districts, key=int))
    for d, ms in districts.items():
        if not ms:
            raise ValueError("District %s heading has no members under it" % d)
    return {"districts": districts, "atLarge": []}
