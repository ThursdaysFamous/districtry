"""Lawrence County elects eighteen commissioners, one from each of 18
districts ("It consists of eighteen members ... Lawrence County is divided
into eighteen districts with each district electing one commissioner").

The county's Commissioners page (WordPress/Elementor) lists the members as
one Elementor loop item per "commissioners" post: inside the item, the post
title <h2> is the member's name and the heading <span> under it reads
"District N", both linking to the member's page /commissioners/district-N/.
The name and the district are read from the same loop item, and the number in
the label must equal the number in both links, so nothing is read from page
order. That link is the county's own page for the seat and is recorded as
profileUrl.

The same page carries a "2025-2026 Lawrence County Committees" section that
predates the new term and names people who are not on the roster above it
(among them Shane Eaton, who ran for County Executive, and Dave Ray, who lost
District 13); it is outside the loop items and is not read. No chair is shown
for the new term.

PRIVACY: the roster page publishes no member e-mail or phone; the number it
does print, 931-766-4100, is the county's own and is in OFFICE_LINES. No
address is read from any page.

PHONES come from the member pages the roster links as profileUrl
(member_pages), which the scraper reads through the same robots.txt check and
pacing as the roster page. Under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is, each
page's one sentence "<name> can be contacted at <number>" is read (on 17
October 2026 every one of the 18 pages had one), and only when the page's
one <h1> names the roster's member and the sentence's name is that member's
("Scott" on Scott Franks's page); otherwise that member's number is withheld
with a note. Nothing else on a member page is read.

Currency: checked 2026-10-11 against the Lawrence County Election Commission's
Election Summary Report for the 6 August 2026 State Primary and County General
(printed 8/6/2026 8:18 PM, all 24 precincts reported), published by the county
as seven page images in its post "2026 LawCo General & State Primary Election
Results" (lawrencecountytn.gov/2026/08/11/...), read as images: every district
elected one commissioner and the 18 winners are the 18 names here. District 1
was the close one: Wayne Yocom 282, Dustin Stutts 271. The ballot spells some
names longer than the page does: Dennis "Denny" Gillespie (D3), Ricky C.
Skillington (D8, "Rick"), Ronald (Bubba) Benefield Jr. (D9, printed here as
Ronald "Bubba" Benefield), Jimmy Dale Bosheers (D16, "J.D."). Fifteen of the
eighteen photos are uploads of 2026/09."""
import re
from ._common import txt, member, district_number, page_field, add_phones, same_person, Withheld

COUNTY = "Lawrence"; FIPS = "099"
DOMAINS = ("lawrencecountytn.gov",)
URLS = ["https://lawrencecountytn.gov/government/commissioners/"]
SEATS = {str(i): 1 for i in range(1, 19)}
AT_LARGE = 0
# The county's own number, printed on the roster page and on every member page.
OFFICE_LINES = ("931-766-4100",)

ITEM = re.compile(r'<div data-elementor-type="loop-item"[^>]*class="[^"]*\btype-commissioners\b[^"]*"')
TITLE_RE = re.compile(r'<h2 class="elementor-heading-title[^"]*"><a href="([^"]+)">(.*?)</a></h2>', re.S)
LABEL = re.compile(r'<span class="elementor-heading-title[^"]*"><a href="([^"]+)">(.*?)</a></span>', re.S)
SEAT_PAGE = re.compile(r"^https://lawrencecountytn\.gov/commissioners/district-(\d{1,2})/$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’“”\" -]+$")
WORDS = {"eighteen": 18}
CONTACT = re.compile(r"<p\b[^>]*>((?:(?!</p>).)*?)can be contacted((?:(?!</p>).)*)</p>", re.S)


def _roster(pages):
    """The roster page alone: {district: [member record]}, phones not read."""
    page = pages[URLS[0]]
    intro = re.search(r"consists of (\w+) members", txt(page))
    if intro:
        n = intro.group(1).lower()
        n = int(n) if n.isdigit() else WORDS.get(n)
        if n != sum(SEATS.values()):
            raise ValueError("the page says the commission has %r members" % intro.group(1))
    starts = [m.start() for m in ITEM.finditer(page)]
    if not starts:
        raise ValueError("no commissioner loop items on the page")
    if re.search(r"data-elementor-type=\"loop-item\"", page[:starts[0]]):
        raise ValueError("a loop item before the first commissioner item is not a commissioner")
    districts = {}
    for k, s in enumerate(starts):
        block = page[s:starts[k + 1] if k + 1 < len(starts) else len(page)]
        end = block.find("</section>")
        if end < 0:
            raise ValueError("a commissioner item that does not close")
        block = block[:end]
        t = TITLE_RE.search(block)
        lab = LABEL.search(block)
        if not t or not lab:
            raise ValueError("a commissioner item without a title or a district label")
        name, label = txt(t.group(2)), txt(lab.group(2))
        if not NAME.match(name):
            raise ValueError("%r does not look like a name" % name)
        d = district_number(label)
        if not d or label != "District %d" % d:
            raise ValueError("%r: label %r is not 'District N'" % (name, label))
        for href in (t.group(1), lab.group(1)):
            m = SEAT_PAGE.match(href)
            if not m or int(m.group(1)) != d:
                raise ValueError("%r: District %d links to %r" % (name, d, href))
        if str(d) in districts:
            raise ValueError("District %d appears twice" % d)
        districts[str(d)] = [member(name, profileUrl=t.group(1))]
    return districts


def member_pages(pages):
    """The member pages the roster page links, one per district, on the
    county's own host: the scraper reads them for parse()."""
    return [r["profileUrl"] for ms in _roster(pages).values() for r in ms]


def page_phones(page, name):
    """The number a member's own page gives in its "can be contacted at"
    sentence, or a Withheld reason when the page does not plainly name this
    member."""
    heads = [txt(h) for h in re.findall(r"<h1\b[^>]*>(.*?)</h1>", page, re.S)]
    if len(heads) != 1 or not (same_person(heads[0], name) and same_person(name, heads[0])):
        return Withheld("the member page's heading does not name this member")
    said = CONTACT.findall(page)
    if not said:
        return []
    if len(said) > 1:
        return Withheld("the member page says how to reach the member %d times" % len(said))
    who, rest = said[0]
    if not same_person(txt(who), name):
        return Withheld("the contact sentence names someone other than the page's member")
    rest = re.sub(r"^(?:\s|&nbsp;)*at\b", "", rest)
    return page_field(re.sub(r"\.\s*$", "", rest.strip()))


def parse(pages):
    districts = _roster(pages)
    for d, ms in districts.items():
        districts[d] = [add_phones(r, page_phones(pages[r["profileUrl"]], r["name"]))
                        for r in ms]
    return {"districts": districts, "atLarge": []}
