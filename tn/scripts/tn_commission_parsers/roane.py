"""Roane County elects 15 commissioners from 7 districts: three each in
Districts 1, 2 and 6, two each in Districts 4 and 7, and one each in
Districts 3 and 5 (the page: "fifteen (15) Commissioners representing seven
(7) Commission Districts"; the ballot's "Vote For" counts are 3/3/1/2/1/3/2).
No seat is labelled, so none is recorded.

The commission page (WordPress/Elementor) gives each district an <h2>
heading "Nth District Commissioner(s) Serving <areas>", followed by one
image-box widget per member whose <h5 class="elementor-image-box-title"> is
the member's name. Every name is paired with the district heading it sits
under; nothing is read from order. The heading's own number of
"Commissioner"/"Commissioners" must agree with the names under it (one name
under the singular, two or more under the plural), a name above the first
district heading or below the page's footer raises, and the run ends at the
footer.

PRIVACY: each member's widget prints a home street address, a town and ZIP,
and a phone (several labelled "(home)" or "(cell)"); Charlotte Bowers's also
prints an e-mail at an organisation's domain (hfhac.org), which is not read.
The phone is recorded as printed, its label kept in front of it ("home
865.354..."), under Adam's ruling of 2026-10-17 that a number a government
publishes beside an official ships whosever line it is. It is read only from
the description paragraph directly under the member's own <h5> name, and
only telephone-shaped numbers are read from it: the street, box, town and ZIP
are never read. The county's own lines printed on the page are OFFICE_LINES
and never land on a member. The page publishes no county e-mail for any
member.

Names are kept as the page prints them, which are short forms of the ballot
names: "Ron Berry" (Ronald Berry), "Randy Kirby" (Randy L. Kirby),
"Charlotte Bowers" (Charlotte Bowers-Cunningham; the county's own 2026-2030
list calls her Charlotte Cunningham).

Currency: checked 2026-10-11 against the Roane County Election Commission's
OFFICIAL RESULTS Summary Results Report for 6 August 2026
(roanecountytn.gov/wp-content/uploads/2026/08/Official-Summary.pdf,
Electionware, generated 08/19/2026 4:20 PM). Every seat was on the ballot,
and the 15 names here are the 15 winners in the same districts: D1 Berry
1,261, Lehman 1,169, Kirby 1,083; D2 Kittrell 885, Ahler 855, Goss 806
(Greg Ferguson 805, a one-vote margin for the third seat, Junior
Hendrickson 768); D3 Gann; D4 Duff 910, Bowers-Cunningham 663 (Kirk
Gaertner 486); D5 Hooks; D6 Brackett, Hamilton, Wilson (Jeff Parkison 933
behind Wilson 1,404); D7 Hester, Parks. The county's own "Roane County
Commissioners September 1, 2026 - August 31, 2030" list (linked from this
page as "County Commissioners", wp-content/uploads/2026/09, created
2026-09-22) names the same 15 by district, Goss in the 2nd District among
them, so the one-vote seat was filled as the report reads."""
import re
from ._common import txt, district_number, member, read_phones

COUNTY = "Roane"; FIPS = "145"
DOMAINS = ("roanecountytn.gov",)
URLS = ["https://roanecountytn.gov/county-commission/"]
SEATS = {"1": 3, "2": 3, "3": 1, "4": 2, "5": 1, "6": 3, "7": 2}
AT_LARGE = 0
# The county's own lines, printed above the roster and in the footer.
OFFICE_LINES = ("865-376-5578", "865-376-5671")

H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
NAME = re.compile(r'<h5 class="elementor-image-box-title">(.*?)</h5>', re.S)
# A name and the description paragraph directly under it, in the same widget.
NAME_DESC = re.compile(r'<h5 class="elementor-image-box-title">(.*?)</h5>\s*'
                       r'(?:<p class="elementor-image-box-description">(.*?)</p>)?', re.S)
HEAD = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District (Commissioners?) Serving\b")
NAME_FORM = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def parse(pages):
    page = pages[URLS[0]]
    footer = page.find('elementor-location-footer')
    if footer < 0:
        raise ValueError("cannot find the page footer")
    if NAME.search(page, footer):
        raise ValueError("a member name sits in the footer")
    heads = list(H2.finditer(page, 0, footer))
    districts = {}
    first = None
    for k, h in enumerate(heads):
        label = txt(h.group(1))
        m = HEAD.match(label)
        stop = heads[k + 1].start() if k + 1 < len(heads) else footer
        items = [(txt(x.group(1)), x.group(2) or "") for x in NAME_DESC.finditer(page, h.end(), stop)]
        names = [n for n, _ in items]
        if not m:
            if names:
                raise ValueError("names %s sit under the heading %r, which names no district"
                                 % (names, label))
            continue
        first = h.start() if first is None else first
        d = m.group(1)
        if district_number(label) != int(d):
            raise ValueError("heading %r read two ways" % label)
        if d in districts:
            raise ValueError("District %s has two headings" % d)
        if not names:
            raise ValueError("District %s has no names under it" % d)
        if (m.group(2) == "Commissioner") != (len(names) == 1):
            raise ValueError("District %s heading says %r over %d names" % (d, m.group(2), len(names)))
        for n in names:
            if not NAME_FORM.match(n):
                raise ValueError("District %s: %r does not look like a name" % (d, n))
        districts[d] = [member(n, phones=read_phones(desc)) for n, desc in items]
    if first is None:
        raise ValueError("no district headings on the page")
    if NAME.search(page, 0, first):
        raise ValueError("a member name sits above the first district heading")
    return {"districts": districts, "atLarge": []}
