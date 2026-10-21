"""Hardin County elects 20 commissioners, two from each of 10 districts (the
ballot reads "Vote For 2" in every district); no seat letters are published or
recorded, and the page names no commission chair.

The commissioners are the first section of the county's Government Directory
page (WordPress/Avada), under the heading "Hardin County Commissioners" and
above "Hardin County Departments". Each district is a column holding an <h2>
"District N" and, directly after it, one text block in which every name is a
<strong> run and every other line is a phone number. The page is cut at those
"District N" headings and each name is paired with the heading of the column
it sits in; nothing is read from order. A line in a block that is neither a
<strong> name nor a phone number raises, and so does a block with no name.

Names are kept as printed, except that the one ALL-CAPS generational suffix
("Fred McFalls, JR.") is written "Jr.".

PRIVACY: every member has one or two phone numbers beside the name, with no
label and none of them a county office line (some are 901 numbers, most differ
member to member). They are recorded as printed, under Adam's ruling of
2026-10-17 that a number a government publishes beside an official ships
whosever line it is: a number is the member's whose <strong> name it follows,
up to the next name. The page publishes no e-mail and no address for a
member. The department contacts below the roster are not read.

Currency: checked 2026-10-11 against the Hardin County Election Commission's
"Aug-26-Official-Results.pdf" (hardincoelections.com wp-content/uploads/2026/08,
an Electionware summary marked OFFICIAL RESULTS, generated 08/12/2026 11:24 AM,
14 of 14 precincts complete). In all 10 districts the two names on this page
are the two winners (ballot spellings Gary L Combs, Fred McFalls, Adam F.
Coleman, Roger L Jenkins, T J Barker, Kaden R. Holt). The closest race was
District 5, where Lisa Wyatt took the second seat with 143 votes to Stacey L
Moore's 121. The page itself was last modified 9 September 2026."""
import re
from ._common import txt, district_number, member, read_phones

COUNTY = "Hardin"; FIPS = "071"
DOMAINS = ("hardincogov.com",)
URLS = ["https://www.hardincogov.com/directory/"]
SEATS = {str(i): 2 for i in range(1, 11)}
AT_LARGE = 0

H2 = re.compile(r'<h2 class="fusion-title-heading[^"]*"[^>]*>(.*?)</h2>', re.S)
TEXT = re.compile(r'<div class="fusion-text fusion-text-\d+">(.*?)</div>', re.S)
PHONE = re.compile(r"^\(?\d{3}\)?\s*[-. ]?\s*\d{3}\s*[-–. ]\s*\d{4}$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’\" ,-]+$")


def _name(raw):
    return re.sub(r",\s*(JR|SR)\.?$", lambda m: ", " + m.group(1).title() + ".", raw.strip())


def parse(pages):
    page = pages[URLS[0]]
    heads = list(H2.finditer(page))
    titles = [txt(h.group(1)) for h in heads]
    try:
        first = titles.index("Hardin County Commissioners")
        end = titles.index("Hardin County Departments", first)
    except ValueError:
        raise ValueError("the commissioners section's headings are missing: %s" % titles[:6])
    districts = {}
    for k in range(first, end):
        label = titles[k]
        if label == "Hardin County Commissioners":
            continue                          # the section heading (printed twice)
        d = district_number(label)
        if not d or label != "District %d" % d:
            raise ValueError("heading %r inside the commissioners section is not 'District N'" % label)
        if str(d) in districts:
            raise ValueError("District %d has two headings" % d)
        col = page[heads[k].end():heads[k + 1].start()]
        blocks = TEXT.findall(col)
        if len(blocks) != 1:
            raise ValueError("District %d column has %d text blocks" % (d, len(blocks)))
        block = blocks[0]
        named = [(txt(m.group(1)), m) for m in re.finditer(r"<strong\b[^>]*>(.*?)</strong>", block, re.S)]
        named = [(n, m) for n, m in named if n]
        names = [n for n, _ in named]
        rest = re.sub(r"<strong\b[^>]*>.*?</strong>", "\n", block, flags=re.S)
        for ln in re.split(r"<br\s*/?>|\n|</?p>", rest):
            t = txt(ln)
            if t and not PHONE.match(t):
                raise ValueError("District %d: %r is neither a name nor a phone" % (d, t))
        if not names:
            raise ValueError("District %d names nobody" % d)
        seats = []
        for i, (n, m) in enumerate(named):
            if not NAME.match(n):
                raise ValueError("District %d: %r is not a name" % (d, n))
            stop = named[i + 1][1].start() if i + 1 < len(named) else len(block)
            seats.append(member(_name(n), phones=read_phones(block[m.end():stop], strict=True)))
        districts[str(d)] = seats
    return {"districts": districts, "atLarge": []}
