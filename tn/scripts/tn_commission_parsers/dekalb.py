"""DeKalb County elects 14 commissioners, two from each of 7 districts. The
ballot (each district's race lists four or five candidates, the top two
elected) and the page call no seat by a letter or number, so no seat is
recorded.

The county's commission page (a Weebly site, www.dekalbtennessee.com) lists
the members under a horizontal rule per district: each block is one
two-column layout row whose left cell holds the <h2> heading "County
Commissioners District N" and whose right cell holds one <h2> name per
member, each followed by a paragraph of contact lines. The page is cut at
those rules; a block's names are paired with the heading in that same block,
never with order. A block must hold exactly one district heading, placed
before its names, and as many names as the county elects there; a name
heading outside a district block, or a district named twice, raises.

PRIVACY: every member's paragraph prints a phone, an e-mail and a home street
address, town and ZIP. The phone is recorded as printed, under Adam's ruling
of 2026-10-17 that a number a government publishes beside an official ships
whosever line it is (nothing calls any a county line); only telephone-shaped
numbers are read from the paragraph under a member's <h2> name, never its
street, town or ZIP. The courthouse line in the page header is OFFICE_LINES
and never lands on a member. The e-mails are Cloudflare-obfuscated and
decode to gmail, yahoo, comcast, verizon, dtccom.net addresses and one
dekalbschools.net address (the school system's domain, not the county's);
none is on the county's own domain, so no e-mail is recorded.

Names are kept as printed, the nickname in single quotes included ("Tony
'Cully' Culwell").

Currency: checked 2026-10-11 against the DeKalb County Election
Commission's "Certified Results" of the 6 August 2026 county general
election, "County Wide Totals" (www.dekalbelections.com, results-reports
1785949253-43.pdf, a text PDF, pages footed August 17, 2026, listed under
"Aug 6, 2026 - State & Fed Prim, County Gen, Municipal / Certified Results"
on the commission's Election Results page). In every district the two names
here are the two highest vote-getters: D1 Slager 339, Cripps 309; D2 Adamson
390, Rhody 295 (Farler 279); D3 Rigsby 308, Hendrix 278; D4 Matthews 330,
Culwell 271 (Poss 269); D5 Hale 385, Cantrell 269; D6 Parsley 370, Pack 290;
D7 Anderson 207, Fuller 187. Ballot spellings differ only by middle names
and initials (Daniel D. Cripps, Billy Myron Rhody, Steven A. Cantrell).
The page names no chair, so no role is recorded."""
import re
from ._common import txt, district_number, member, read_phones

COUNTY = "DeKalb"; FIPS = "041"
DOMAINS = ("dekalbtennessee.com",)
URLS = ["https://www.dekalbtennessee.com/county-commission.html"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0
# The courthouse line printed in the page header.
OFFICE_LINES = ("615-597-5175",)

H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
RULE = re.compile(r'<hr class="styled-hr"')
HEAD_RE = re.compile(r"^County Commissioners District\s+(\d{1,2})$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
INTRO = "DeKalb County Commission Meetings"


def parse(pages):
    page = pages[URLS[0]]
    s = page.find('id="wsite-content"')
    e = page.find('id="footer"', s)
    if s < 0 or e < 0:
        raise ValueError("the page's content region is not where it was")
    districts = {}
    for seg in RULE.split(page[s:e]):
        found = [(txt(h.group(1)), h) for h in H2.finditer(seg)]
        found = [(t, h) for t, h in found if t]
        heads = [t for t, _ in found]
        if not heads or heads == [INTRO]:
            continue
        m = HEAD_RE.match(heads[0])
        if not m:
            raise ValueError("a block's first heading is not 'County Commissioners District N': %r" % heads)
        d = m.group(1)
        if district_number(heads[0]) != int(d):
            raise ValueError("heading %r read two ways" % heads[0])
        if d in districts:
            raise ValueError("District %s has two blocks" % d)
        names = heads[1:]
        for n in names:
            if HEAD_RE.match(n) or "District" in n:
                raise ValueError("District %s block holds a second district heading %r" % (d, n))
            if not NAME.match(n):
                raise ValueError("District %s: %r does not look like a name" % (d, n))
        if len(names) != SEATS.get(d):
            raise ValueError("District %s block names %d members, the county elects %s"
                             % (d, len(names), SEATS.get(d)))
        seats = []
        for k, (n, h) in enumerate(found[1:], 1):
            stop = found[k + 1][1].start() if k + 1 < len(found) else len(seg)
            cell_end = seg.find("</td>", h.end())
            if 0 <= cell_end < stop:
                stop = cell_end                 # the paragraph ends with the name's own column
            seats.append(member(n, phones=read_phones(seg[h.end():stop])))
        districts[d] = seats
    return {"districts": districts, "atLarge": []}
