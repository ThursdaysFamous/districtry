"""Unicoi County elects 9 commissioners, three from each of 3 districts (the
ballot reads "VOTE FOR 3" in each). No seat is called by a letter or number,
so no seat is recorded.

The Boards & Commissions page (hand-written HTML) has a heading "County
Commission Members" and then one card (a `col-sm-4` box) per member: a
photo, a line "District N", the member's name as a link, then that member's
address and phone. Each name is paired with the "District N" line of its own
card; nothing is read from order. Every card must open with exactly one
"District N" line with the name directly under it, and the name must be the
card's one link with text (an empty page anchor after the last card is not a
link). The list ends at the "Planning Commission" heading. The
same page lists the same nine under "Beer Board" and "Budget Committee"
(the commission sits as both); only the "County Commission Members" section
is read.

PRIVACY: every card prints the member's home street address, town and ZIP
and a phone number (Patrick Callahan's two, "(423) ... or (423) ..."), and
every name links to a personal e-mail (gmail, yahoo, hotmail). Under Adam's
ruling of 2026-10-17 that a number a government publishes beside an official
ships whosever line it is, each card's numbers are read, the first into
`phone` and a second into `phonesExtra`. Only telephone-shaped numbers are
read; the street address, town and ZIP are never read. On 2026-10-17 the
cards print the same number for Jamie Harris and Tim Lingerfelt (the page's
Beer Board and Budget Committee tables print a different number for
Lingerfelt), so that number is left out for both, as any number printed for
two members is (settle_phones); the parser does not choose between the
page's sections. The county's own line in the page header and footer is in
OFFICE_LINES. The address each name links to is recorded on that member, under
Adam's ruling of the same day that an e-mail address a government page prints
beside an official ships too; only the name's own link is read, and a card
printing any other e-mail address raises.

Currency: checked 2026-10-11 against the Unicoi County "Election Summary
Report" for the 2026 State Primary and County General of 6 August 2026
(election-night, run 8/6/2026 8:54:56 PM, 8 of 8 precincts reported, not
labelled certified), published on the county's own site
(www.unicoicountytn.gov/pdfs/state_federal_county_results.pdf, text PDF).
Each district elects three and the three leading candidates in each are
exactly this page's three: D1 James (Jamie) Harris 399, Tim Lingerfelt 439,
Loren Thomas 446 (uncontested beyond write-ins); D2 Patrick Callahan 455,
Jason Harris 542, Corey Hatcher 482, over Christiana Gilbert 287; D3 Gina
Wilson Clark 614, Debbie Bennett Lemmon 591, Todd Wilcox 619. The ballot
gives fuller names than the page; the people are the same."""
import re
from ._common import txt, lines, member, read_phones, read_emails, member_email

COUNTY = "Unicoi"; FIPS = "171"
DOMAINS = ("unicoicountytn.gov",)
URLS = ["https://www.unicoicountytn.gov/boards_commissions.html"]
SEATS = {"1": 3, "2": 3, "3": 3}
AT_LARGE = 0
# The county's own line, printed in the page header and footer.
OFFICE_LINES = ("(423) 743-9391",)

START = "County Commission Members"
END = "<h2>Planning Commission</h2>"
CARD_RE = re.compile(r'<div class="col-sm-4">')
DIST_RE = re.compile(r"^District (\d{1,2})$")
NAME_RE = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def parse(pages):
    page = pages[URLS[0]]
    s = page.find(START)
    e = page.find(END, s)
    if s < 0 or e < 0:
        raise ValueError("the County Commission Members section or the heading after it is missing")
    cards = CARD_RE.split(page[s:e])
    if txt(re.sub(r"<[^>]+>", " ", cards[0])) != START:
        raise ValueError("%d characters of text between the heading and the first card"
                         % len(txt(cards[0])))
    districts = {}
    for card in cards[1:]:
        ls = lines(card)
        ds = [k for k, l in enumerate(ls) if re.search(r"\bDistrict\b", l)]
        if len(ds) != 1 or not DIST_RE.match(ls[ds[0]]) or ds[0] != 0:
            # Never quotes the card's lines: they may be an address.
            raise ValueError("a card does not open with one 'District N' line")
        links = [m for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", card, re.S) if txt(m.group(1))]
        if len(links) != 1 or ds[0] + 1 >= len(ls):
            raise ValueError("a District %s card does not carry exactly one linked name"
                             % DIST_RE.match(ls[0]).group(1))
        name = txt(links[0].group(1))
        if ls[1] != name:
            raise ValueError("District %s: the line under the district %r is not the linked name %r"
                             % (DIST_RE.match(ls[0]).group(1), ls[1], name))
        if not NAME_RE.match(name) or re.search(r"\bvacan", name, re.I) or " " not in name:
            raise ValueError("%r does not look like a name" % name)
        d = DIST_RE.match(ls[0]).group(1)
        # The address the name links to; any other in the card raises.
        if read_emails(card[:links[0].start()] + card[links[0].end():]):
            raise ValueError("District %s: %r's card prints an e-mail address off the name"
                             % (d, name))
        email = member_email(read_emails(links[0].group(0)), DOMAINS)
        districts.setdefault(d, []).append(member(name, email=email, phones=read_phones(card)))
    if not districts:
        raise ValueError("no member cards found")
    return {"districts": districts, "atLarge": []}
