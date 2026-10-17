"""Dickson County elects 12 commissioners, one from each of 12 districts (the
page: "A commissioner is elected from each of the twelve commission districts
in Dickson County and serves a four year term ... and take office on September
1st"). The page names no commission chair.

The County Commission page (hand-written HTML) lists the members under
"Commission Members", one <div class="col-sm-4"> per district: an <h4>
"District N", a photo whose alt text reads "<Name>, Commissioner", then a
mailto link whose text is the name, then a street address and a phone. The
page is cut at those <h4> headings and each name is paired with the heading of
the block it sits in; the name is the link's text and must equal the photo's
alt text without ", Commissioner", so a heading that drifted away from its
photo and name raises. Nothing is read from order.

PRIVACY: every block carries the member's home street address, a phone and a
personal e-mail (msn, gmail, yahoo, bellsouth, live, comcast, outlook, a
business domain and a campaign address). The phone is recorded as printed,
under Adam's ruling of 2026-10-17 that a number a government publishes
beside an official ships whosever line it is; only telephone-shaped numbers
are read from a block, and the address is never read. No e-mail is on the
county's domain and none is recorded. The Administration Building's and the
Justice Center's lines in the page footer are OFFICE_LINES and never land on
a member.

Currency: checked 2026-10-11 against the Dickson County Election
Commission's own site, dicksoncountyelection.com, which lists under "FINAL
ELECTION RESULTS" a "Dickson County State Primary & County General Aug 6, 2026
Summary Report Final.pdf" (and a matching precinct report). The file itself is
an Electionware summary stamped UNOFFICIAL RESULTS and generated 08/06/2026
8:35 PM, whose statistics say 13 of 15 election-day precincts reporting. The
matching precinct report shows what the other two are: absentee-only
"Property Rights" voter groups for the Charlotte and White Bluff municipal
races, with no election-day voting and no commission race. The 13 polling
precincts (one in each district, two in District 6) all have their
election-day ballots counted, and the commission posts the file as final. In all 12 districts the name on this page is the
winner (ballot spellings: John R. Randy Simpkins on the commission's officials
list, Dennis M O'Shea, Richard E. Riehn, Michael S Petty, John C Stritikus,
Daryl Lee "Rusty" Grove, Johnnie W Reed). Only Districts 2, 3 and 4 were
contested, the closest District 3, O'Shea 374 to Dwight D McIllwain 332."""
import re
from ._common import txt, mailtos, county_email, district_number, member, read_phones

COUNTY = "Dickson"; FIPS = "043"
DOMAINS = ("dicksoncountytn.gov",)
URLS = ["https://www.dicksoncountytn.gov/county_commission.html"]
SEATS = {str(i): 1 for i in range(1, 13)}
AT_LARGE = 0
# The Administration Building's and the Justice Center's lines, in the page footer.
OFFICE_LINES = ("(615) 789-7003", "(615) 789-7002")

H4 = re.compile(r"<h4>(.*?)</h4>", re.S)
MAILTO = re.compile(r'<a href="mailto:[^"]*"[^>]*>(.*?)</a>', re.S)
ALT = re.compile(r'<img[^>]*\balt="([^"]*)"', re.S)
NAME = re.compile(r"^[A-Z][A-Za-z.'’\" -]+$")


def parse(pages):
    page = pages[URLS[0]]
    s = page.find("<h3>Commission Members")
    e = page.find("</section>", s)
    if s < 0 or e < 0:
        raise ValueError("no 'Commission Members' section")
    region = page[s:e]
    heads = list(H4.finditer(region))
    if not heads:
        raise ValueError("no district headings")
    districts = {}
    for k, h in enumerate(heads):
        label = txt(h.group(1))
        d = district_number(label)
        if not d or label != "District %d" % d:
            raise ValueError("heading %r is not 'District N'" % label)
        if str(d) in districts:
            raise ValueError("District %d has two headings" % d)
        block = region[h.end():heads[k + 1].start() if k + 1 < len(heads) else len(region)]
        links = [txt(x) for x in MAILTO.findall(block)]
        links = [x for x in links if x]
        if len(links) != 1:
            raise ValueError("District %d block has %d named links: %s" % (d, len(links), links))
        name = links[0]
        if not NAME.match(name):
            raise ValueError("District %d: %r is not a name" % (d, name))
        alts = [re.sub(r",\s*Commissioner\s*$", "", txt(a)) for a in ALT.findall(block)]
        if alts != [name]:
            raise ValueError("District %d: link %r and photo alt %s disagree" % (d, name, alts))
        email = county_email(mailtos(block), DOMAINS)
        districts[str(d)] = [member(name, email=email, phones=read_phones(block))]
    return {"districts": districts, "atLarge": []}
