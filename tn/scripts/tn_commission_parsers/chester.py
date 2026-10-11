"""Chester County elects 12 commissioners, two from each of 6 districts. The
ballot names no seat or position, so no seat is recorded, and the page names
no chair.

The County Commission page heads each district with an <h5> "District N",
followed by a Bootstrap row of "col-sm-4" columns, one per member: a photo,
the name in <strong>, then a line "Commissioner, District N", then the
member's contact lines. The page is cut at those <h5> headings and each
member is read from its own column: the column's "Commissioner, District N"
line must name the same district as the heading of the section it sits in,
so a column that drifted under the wrong heading raises, and nothing is read
from order. Empty spacer columns are skipped; a column with text and no
<strong> name raises. Each section must hold exactly the seats the county
elects there.

PRIVACY: every column prints a street address, town and ZIP, a phone (most
labelled "Cell") and an "Email" link. None of it is recorded. The e-mail
links are all off the county's domain (outlook, gmail, yahoo, bellsouth,
charter, icloud, fhu.edu, and Tim Crowe's tcrowe@hendersontn.gov, a City of
Henderson address, not the county's), and Ann Moore's name is itself wrapped
in a link to another person's bellsouth address. The page's only county
address (trustee@chestercountytn.org in the footer) is not a member's. No
e-mail and no phone is recorded.

Currency: checked 2026-10-11 against the Chester County Election
Commission's own results page (votechestercountytn.gov/results/, "Unofficial
Election Results - Local General & State/Federal Primary, Early and
Absentee; 7 of 7 Precincts Reporting, August 6, 2026", updated August 6,
2026 at 8:33pm; no certified copy was found on the commission's site). All
12 seats were on that ballot, and in every district the two names here are
the two highest: D1 Faulkner 197, Carter 194 (Edgin 186); D2 Seaton 259,
McKinnon 255 (King 183); D3 Weaver 296, Moore 249 (Richardson 124); D4
Clayton 281, Thompson 271 (Maness 160, Holiday 106); D5 Crowe 244, Smith 225
(unopposed); D6 Crump 123, Burns 103 (unopposed). The ballot prints "Dwain
Seaton, Sr" and "Dylan R. Clayton"; the page's spellings are kept. District
1's second seat was decided by 8 votes on the unofficial count. The page
itself carries no date."""
import re
from ._common import txt, district_number, member

COUNTY = "Chester"; FIPS = "023"
DOMAINS = ("chestercountytn.org",)
URLS = ["https://chestercountytn.org/county_commission.html"]
SEATS = {str(i): 2 for i in range(1, 7)}
AT_LARGE = 0

HEAD = re.compile(r"<h5>\s*(District\s+\d{1,2})\s*</h5>")
COL = re.compile(r'<div class="col-sm-4">')
TITLE_RE = re.compile(r"\bCommissioner, District (\d{1,2})\b")
NAME = re.compile(r"^[A-Z][A-Za-z.'’\" -]+$")


def parse(pages):
    page = pages[URLS[0]]
    start = page.find('<h3 class="h-bold">County Commission</h3>')
    end = page.find("<footer", start)
    if start < 0 or end < 0:
        raise ValueError("the County Commission heading or the footer is missing")
    body = page[start:end]
    heads = list(HEAD.finditer(body))
    if not heads:
        raise ValueError("no <h5> 'District N' headings")
    if TITLE_RE.search(txt(body[:heads[0].start()])):
        raise ValueError("a member sits before the first district heading")
    districts = {}
    for k, h in enumerate(heads):
        d = str(district_number(h.group(1)))
        if d in districts:
            raise ValueError("District %s has two headings" % d)
        stop = heads[k + 1].start() if k + 1 < len(heads) else len(body)
        seats = []
        for col in COL.split(body[h.end():stop])[1:]:
            if not txt(col):
                continue
            strongs = [txt(s) for s in re.findall(r"<strong\b[^>]*>(.*?)</strong>", col, re.S)]
            strongs = [s for s in strongs if s]
            if len(strongs) != 1:
                raise ValueError("District %s: a column holds %d <strong> names: %r"
                                 % (d, len(strongs), txt(col)[:80]))
            name = strongs[0]
            titles = TITLE_RE.findall(txt(col))
            if titles != [d]:
                raise ValueError("District %s section holds %r titled District %s" % (d, name, titles))
            if not NAME.match(name) or re.search(r"\bvacan", name, re.I):
                raise ValueError("District %s: %r does not look like a name" % (d, name))
            seats.append(member(name))
        if len(seats) != SEATS.get(d):
            raise ValueError("District %s section has %d members, the county elects %s"
                             % (d, len(seats), SEATS.get(d)))
        districts[d] = seats
    return {"districts": districts, "atLarge": []}
