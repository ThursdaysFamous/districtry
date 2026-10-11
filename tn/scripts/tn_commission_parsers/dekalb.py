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
address, town and ZIP. None is recorded. The phones are the members' own
(nothing calls any a county line). The e-mails are Cloudflare-obfuscated and
decode to gmail, yahoo, comcast, verizon, dtccom.net addresses and one
dekalbschools.net address (the school system's domain, not the county's);
none is on the county's own domain, so no e-mail is recorded. Only the <h2>
name is read.

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
from ._common import txt, district_number, member

COUNTY = "DeKalb"; FIPS = "041"
DOMAINS = ("dekalbtennessee.com",)
URLS = ["https://www.dekalbtennessee.com/county-commission.html"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0

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
        heads = [txt(h) for h in H2.findall(seg)]
        heads = [h for h in heads if h]
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
        districts[d] = [member(n) for n in names]
    return {"districts": districts, "atLarge": []}
