"""Fentress County elects 10 commissioners, two from each of 5 districts. No
seat is called by a letter or number, so no seat is recorded. The County
Executive (Jacob Rosenbaum since 1 September 2026) calls the meetings to
order and holds no commission seat; he is not recorded.

The County Commissioners page (WordPress, Avada layout) gives each district
an <h1> heading "Nth District" followed by one `fusion-person` block per
member: a photo and a `person-name` span, with an empty `person-title` and an
empty `person-content` box. The page is cut at those headings and each name
is paired with the heading of the section it sits in; nothing is read from
order. A block with no name, a person-title that is not a commission office,
or a person-content box with any text in it raises (the page carries no
contacts today, and new text is read before it is trusted).

PRIVACY: the page prints no member address, phone or e-mail.

Currency: no results of the 6 August 2026 election were found on a county
host (the county's Election Commission page carries only the director's
office contact and links no results; the state's results site answers this
project HTTP 403 and was not tried). Checked 2026-10-11 instead against
Resolution 2026-14 of the Fentress County Board of Commissioners, "Adopted
this 21st day of September, 2026" and signed by the County Executive and
the County Clerk (fentresscountytn.gov/wp-content/uploads/2026/09/
Fentress-County-Resolution-2026-14.pdf, scanned, read as images), whose
signature page prints each commissioner's line BY DISTRICT: 1st District
Kyle Cooper and Ben Cooper; 2nd Kim Davidson and Jerry JP Reagan; 3rd
Heather Harvey and Haylee Martin; 4th Jeff Green and Leon Stepp; 5th Allen
Tompkins and Rita Murphy. These are this page's ten in the same districts
("J.P. Reagan" and "Rita Pierce Murphy" here). The agenda for that meeting
(21 September 2026, scanned) also names "3rd District Commissioner Heather
Harvey" and "3rd District Commissioner Haylee Martin", and the minutes of
the outgoing commission's 27 August 2026 meeting (certified 21 September
2026) seat Ben Cooper (1st), J.P. Reagan and Kim Davidson (2nd), Leon Stepp
(4th) and Rita Pierce Murphy (5th) in the same districts before the election
took effect. The page itself is dated 2026-09-03. What this does NOT
establish: no results were compared, so the outcome of the August election
is known only through who signed as commissioner afterwards."""
import re
from ._common import txt, member, district_number, ROLE

COUNTY = "Fentress"; FIPS = "049"
DOMAINS = ("fentresscountytn.gov",)
URLS = ["https://fentresscountytn.gov/county-commissioners/"]
SEATS = {str(i): 2 for i in range(1, 6)}
AT_LARGE = 0

HEAD_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S)
SECTION_RE = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District$")
PERSON_RE = re.compile(r'<div class="fusion-person\b')
NAME_RE = re.compile(r'<span class="person-name">(.*?)</span>\s*<span class="person-title">(.*?)</span>', re.S)
CONTENT_RE = re.compile(r'<div class="person-content\b[^>]*>(.*?)</div>', re.S)
OK_NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def parse(pages):
    page = pages[URLS[0]]
    end = page.find("</main>")
    if end < 0:
        raise ValueError("no </main> on the commissioners page")
    heads = [h for h in HEAD_RE.finditer(page, 0, end) if SECTION_RE.match(txt(h.group(1)))]
    if not heads:
        raise ValueError("no 'Nth District' headings")
    if PERSON_RE.search(page, 0, heads[0].start()):
        raise ValueError("a person block sits before the first district heading")
    districts = {}
    for k, h in enumerate(heads):
        label = txt(h.group(1))
        n = SECTION_RE.match(label).group(1)
        if str(district_number(label)) != n:
            raise ValueError("heading %r read two ways" % label)
        if n in districts:
            raise ValueError("District %s has two headings" % n)
        stop = heads[k + 1].start() if k + 1 < len(heads) else end
        found = []
        for b in PERSON_RE.split(page[h.end():stop])[1:]:
            m = NAME_RE.search(b)
            if not m:
                raise ValueError("District %s: a person block without a name" % n)
            name, title = txt(m.group(1)), txt(m.group(2))
            if not OK_NAME.match(name) or re.search(r"\bvacan", name, re.I) or " " not in name:
                raise ValueError("District %s: %r does not look like a name" % (n, name))
            if title and not ROLE.fullmatch(title):
                raise ValueError("District %s: %r's title %r is not a commission office" % (n, name, title))
            content = CONTENT_RE.search(b)
            if content and txt(content.group(1)):
                # The new text is not quoted: it may be an address.
                raise ValueError("District %s: %r's block now carries %d characters of "
                                 "text; read it first"
                                 % (n, name, len(txt(content.group(1)))))
            found.append(member(name, role=title or None))
        if not found:
            raise ValueError("District %s heading has no members under it" % n)
        districts[n] = found
    return {"districts": districts, "atLarge": []}
