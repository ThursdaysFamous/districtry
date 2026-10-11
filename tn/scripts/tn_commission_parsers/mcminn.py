"""McMinn County elects ten commissioners, two from each of 5 districts ("The
Board consists of 10 members ... Two commissioners are elected from each of
the 5 districts in the county"). The ballot names no seat or position inside a
district, and neither does the page, so no seat is recorded.

The county's County Commission page is one <table class="table">: each row
holds two members, and each member is a photo cell followed by a text cell.
The text cell opens with the member's name (a mailto link) and its next line
reads "District N, Commissioner"; the name and the district are read from that
same cell, never from the row or the table's order. Every photo carries alt
text "District N, Commissioner <Name>", and the set of (district, name) pairs
read from the alt texts must equal the set read from the text cells, so a
photo or a label that drifted from its member raises. A text cell with a name
and no "District N, Commissioner" line raises, and the page's own statement of
the board size ("consists of N members") must equal the seats in SEATS.

The server sends no charset, so the page arrives decoded as ISO-8859-1 while
its <meta> says utf-8 (non-breaking spaces read as "Â "); the text is
re-decoded as UTF-8 before it is read.

PRIVACY: nine of the ten text cells carry the member's home street address,
town and ZIP, seven carry a personal phone, and every name is a mailto link to
a personal address (aol.com, outlook.com, gmail.com, hotmail.com, comcast.net).
None of it is recorded: only the name and the district line are read. No
member has an address on the county's own domain, so no e-mail is kept; the
footer's mayoroffice@ address is the County Mayor's office and is outside the
table.

Currency: checked 2026-10-11 against the McMinn County Election Commission's
"Election Results August 6, 2026" (pages dated August 18, 2026), linked from
the commission's own site mcminnelections.com and served from its site
builder's file store (files.cdn-files-a.com/uploads/3293126/
normal_6a8c79bc050e4.pdf). Each district elected two, and the two with the
most votes in every district are the ten names here: District 1 Brent Carter
709, Scott D Williams 660; District 2 Jerry L Millsaps 929, J. W. McPhail 869;
District 3 Roger Masingale 949, Tim King 943; District 4 Scott Cass 886, Tony
Allman 811 (Kim Bivens 750 and Willis S Stewart 176 lost); District 5 Scott
Curtis 1,064, Travis Crisp 1,042. The results list candidates in ballot order,
not vote order. The page writes "Scott Williams" and "Jerry Millsaps" where
the ballot carries a middle initial."""
import re
from ._common import txt, member

COUNTY = "McMinn"; FIPS = "107"
DOMAINS = ("mcminncountytn.gov",)
URLS = ["https://www.mcminncountytn.gov/county_commission_main.html"]
SEATS = {str(i): 2 for i in range(1, 6)}
AT_LARGE = 0

LABEL = re.compile(r"^District\s+(\d{1,2}),\s*Commissioner$")
ALT = re.compile(r"^District\s+(\d{1,2}),\s*Commissioner\s+(.+)$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def _utf8(page):
    """Undo the ISO-8859-1 decoding of a UTF-8 page ('Â\\xa0' -> '\\xa0')."""
    if "Â" not in page and "â€" not in page:
        return page
    try:
        return page.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return page.replace("Â\xa0", " ")


def _key(name):
    return re.sub(r"\s+", " ", name).strip().casefold()


def parse(pages):
    page = _utf8(pages[URLS[0]])
    size = re.search(r"Board consists of\s+(\d+)\s+members", txt(page))
    if size and int(size.group(1)) != sum(SEATS.values()):
        raise ValueError("the page says the board has %s members, SEATS has %d"
                         % (size.group(1), sum(SEATS.values())))
    start = page.find("Board consists of")
    tables = [m for m in re.finditer(r'<table class="table">(.*?)</table>', page[start:], re.S)]
    if start < 0 or len(tables) != 1:
        raise ValueError("expected one member table after the board description, found %d"
                         % len(tables))
    table = tables[0].group(1)
    cells = re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", table, re.S)
    districts, from_cells, from_alts = {}, set(), set()
    for cell in cells:
        for alt in re.findall(r'<img\b[^>]*\balt="([^"]*)"', cell):
            m = ALT.match(txt(alt))
            if not m:
                raise ValueError("photo alt %r is not 'District N, Commissioner Name'" % alt)
            from_alts.add((m.group(1), _key(m.group(2))))
        parts = [txt(p) for p in re.split(r"<br\s*/?>", cell, flags=re.I)]
        parts = [p for p in parts if p]
        if not parts:
            continue
        link = re.search(r"<a\b[^>]*>(.*?)</a>", cell, re.S)
        if not link or txt(link.group(1)) != parts[0]:
            raise ValueError("a member cell does not open with its name link: %r" % parts[:2])
        name = parts[0]
        if not NAME.match(name):
            raise ValueError("%r does not look like a name" % name)
        m = LABEL.match(parts[1]) if len(parts) > 1 else None
        if not m:
            raise ValueError("%r: the line after the name is not 'District N, Commissioner': %r"
                             % (name, parts[1:2]))
        d = m.group(1)
        if (d, _key(name)) in from_cells:
            raise ValueError("%r listed twice in District %s" % (name, d))
        from_cells.add((d, _key(name)))
        # Address, phone and the personal mailto are the member's own: not read.
        districts.setdefault(d, []).append(member(name))
    if from_cells != from_alts:
        raise ValueError("text cells %s and photo alts %s disagree"
                         % (sorted(from_cells - from_alts), sorted(from_alts - from_cells)))
    return {"districts": districts, "atLarge": []}
