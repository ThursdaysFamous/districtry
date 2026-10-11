"""Hamilton County Commission: 11 commissioners, one from each of Districts
1-11. The county's County Commission Committees page carries one tile per
district: a link to DistrictN.aspx whose element ids end in DistrictN and
whose label reads "District N Commissioner<br />Name[, Chairman | , Chairman
Pro-Tempore]". The district is read from that label and must agree with the
link's own DistrictN.aspx and the element id, so nothing is read from page
order. An older commented-out copy of the tiles (nine districts, no 10 or 11)
sits lower on the page; comments are stripped before parsing.

Each DistrictN.aspx page names the same commissioner, but its contact block is
the commission office's (401 Courthouse, 423-209-7200, the same number on
every district page) and its "Email Me" is a web form
(Commission_EmailForm.aspx), so no per-member e-mail or phone is published and
none is recorded; the district pages are not fetched.

All eleven seats were on the 6 August 2026 county general ballot. Checked
2026-10-11 against the Hamilton County Election Commission's official results
(govotehamiltontn.gov/2608-OfficialResults, read through the page's own data
feed assets/data.js and summed over precincts): every winner is the name this
page lists for that district (Steve Highlander is "Dr. Steve Highlander" here;
the honorific is the county's and is kept)."""
import re
from ._common import txt, member, district_number

COUNTY = "Hamilton"; FIPS = "065"
DOMAINS = ("hamiltontn.gov",)
URLS = ["https://www.hamiltontn.gov/CountyCommission_Committees.aspx"]
SEATS = {str(i): 1 for i in range(1, 12)}
AT_LARGE = 0
BASE = "https://www.hamiltontn.gov/"

TILE = re.compile(
    r'<a href="(District(\d{1,2})\.aspx)" id="BodyContent_CountyCommission_Link_District(\d{1,2})">'
    r'(.*?)</a>', re.S)
LABEL = re.compile(r'<p id="BodyContent_CountyCommission_Label_District(\d{1,2})"[^>]*>(.*?)</p>', re.S)
ROLE_TAIL = re.compile(r",\s*(Chairman(?:\s+Pro[- ]Tem(?:pore)?)?|Vice[- ]Chairman|Chairwoman|Chairperson)\s*$",
                       re.I)


def parse(pages):
    page = pages[URLS[0]]
    districts = {}
    tiles = TILE.findall(page)
    if not tiles:
        raise ValueError("no commission tiles (BodyContent_CountyCommission_Link_DistrictN) on the page")
    for href, n_href, n_id, inner in tiles:
        lab = LABEL.search(inner)
        if not lab:
            raise ValueError("tile %s has no commissioner label" % href)
        n_lab = lab.group(1)
        parts = [txt(x) for x in re.split(r"<br\s*/?>", lab.group(2), flags=re.I)]
        parts = [x for x in parts if x]
        if len(parts) != 2:
            raise ValueError("tile %s: label %r is not 'District N Commissioner' + name" % (href, parts))
        head, who = parts
        m = re.fullmatch(r"District (\d{1,2}) Commissioner", head)
        if not m or district_number(head) != int(m.group(1)):
            raise ValueError("tile %s: first label line %r is not 'District N Commissioner'" % (href, head))
        n = m.group(1)
        if len({n, n_href, n_id, n_lab}) != 1:
            raise ValueError("tile %s: district read four ways disagrees: label %s, link %s, ids %s/%s"
                             % (href, n, n_href, n_id, n_lab))
        role = None
        r = ROLE_TAIL.search(who)
        if r:
            role = r.group(1)
            who = who[:r.start()]
        if "," in who or re.search(r"\bvacan", who, re.I):
            raise ValueError("tile %s: name %r has a part this parser does not know" % (href, who))
        if n in districts:
            raise ValueError("District %s appears twice" % n)
        districts[n] = [member(who, role=role, profileUrl=BASE + href)]
    return {"districts": districts, "atLarge": []}
