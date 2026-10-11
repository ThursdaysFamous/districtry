"""Wilson County's commission is 25 commissioners, one from each of 25
districts ("The Wilson County Commission is made up of 25 people"). The county's
CivicPlus page (/245/County-Commissioners redirects to /222/County-Commission)
gives each member an editor widget of their own: an <h2> with the name, then a
paragraph "County Commissioner, District N" and a "More Information" link to the
member's staff-directory entry. Name and district are read from the same
widget, never from page order.

No e-mail is published (the directory offers a contact form only), and no
phone is recorded: the directory entries print the member's own street address,
and any number with it is the member's, not a county office line.

The "More Information" links point at one CivicPlus directory under three
spellings — relative /Directory.aspx?EID=N, wilsoncountytn.gov/m/directory/
employee?eid=N, and the vendor alias tn-wilsoncounty.civicplus.com — so the
profileUrl is rebuilt from the EID on the county's own host. Checked 2026-10-11:
EID 120, linked through the vendor alias for District 9, is Blake Hall,
"District 9 Commissioner", on www.wilsoncountytn.gov.

CURRENCY was checked on 2026-10-11 against the Wilson County Election
Commission's unofficial final results for 6 August 2026 (wilsontnvotes.gov,
Election Results Reporting): every district elected one commissioner and the
25 winners are the 25 names here (the ballot's Jeremy Hugh Gwynne Hayes is the
page's "Jeremy H.G.Hayes", Jeremy Hale Reich is Jeremy Reich, William Glover III
is William Glover)."""
import re
from ._common import txt, district_number, member

COUNTY = "Wilson"; FIPS = "189"
DOMAINS = ("wilsoncountytn.gov",)
URLS = ["https://www.wilsoncountytn.gov/245/County-Commissioners"]
SEATS = {str(i): 1 for i in range(1, 26)}
AT_LARGE = 0
PROFILE = "https://www.wilsoncountytn.gov/Directory.aspx?EID=%s"


def parse(pages):
    page = pages[URLS[0]]
    if "The Wilson County Commission is made up of 25 people" not in page:
        raise ValueError("the page no longer says the commission is 25 people")
    districts = {}
    for w in re.split(r'<div class="fr-view">', page)[1:]:
        w = w.split("</div>", 1)[0]
        if not re.search(r"County Commissioner\b", txt(w)):
            continue
        heads = re.findall(r"<h2\b[^>]*>(.*?)</h2>", w, re.S)
        labels = re.findall(r"County Commissioner,\s*District\s*\d+", txt(w))
        if len(heads) != 1 or len(labels) != 1:
            raise ValueError("a commissioner widget without exactly one name and one district: %r"
                             % txt(w)[:100])
        name = txt(heads[0])
        num = district_number(labels[0])
        eid = re.search(r'href="[^"]*directory[^"]*\b(?:EID|eid)=(\d+)"', w, re.I)
        districts.setdefault(str(num), []).append(
            member(name, profileUrl=PROFILE % eid.group(1) if eid else None))
    return {"districts": districts, "atLarge": []}
