"""Williamson County's commission is 24 commissioners, two from each of 12
districts (every district race on the 6 August 2026 ballot was "Vote For 2").
The county's Members page (/169/Members) redirects to the CivicPlus staff
directory for the commission department, which lists each member as one <li>
in the category-staff list: a link to the member's directory entry carrying the
name, the member's district as their directory title ("District N", printed
twice in the same <li> for wide and narrow screens; both must agree), a county
e-mail and a phone. Name and district are read from the same <li>, never from
order. The county publishes no seat letter or position inside a district.

PRIVACY: the per-member phones are the members' own (the county's PDF listing
prints them beside home addresses). Under Adam's ruling of 2026-10-17 that a
number a government publishes beside an official ships whosever line it is,
each entry's number is read into `phone`, as printed (two carry an area code
from another state, which is kept). Only telephone-shaped numbers are read,
and the directory prints no member address; the PDF listing is not read. The
department's own phone and fax, printed above the list, are OFFICE_LINES and
stay off every member. E-mails are kept only on williamsoncounty-tn.gov; the
shared commissioners@ address is outside the member list and is not read.

CURRENCY was checked on 2026-10-11 against the Williamson County Election
Commission's own "Unofficial Cumulative Results August 6th" (williamsoncounty-
tn.gov Agenda Center, a 14-page PDF read as images): the two winners in each of
the 12 districts are the 24 names here. The survey's D2 discrepancy is a
nickname, not a different person: the ballot reads Allen "Drell" Floyd, so this
page's "Allen Floyd" and the PDF's "Drell Floyd" are one member; the HTML's
spelling is kept."""
import re
from ._common import txt, mailtos, county_email, district_number, member, read_phones

COUNTY = "Williamson"; FIPS = "187"
DOMAINS = ("williamsoncounty-tn.gov",)
URLS = ["https://www.williamsoncounty-tn.gov/m/directory/department?did=3"]
SEATS = {str(i): 2 for i in range(1, 13)}
AT_LARGE = 0
# The commission department's phone and fax, printed above the member list.
OFFICE_LINES = ("(615) 790-5712", "(615) 790-5610")
BASE = "https://www.williamsoncounty-tn.gov"


def parse(pages):
    page = pages[URLS[0]]
    lst = re.search(r'<ul class="category-staff\b.*?</ul>', page, re.S)
    if not lst:
        raise ValueError("no category-staff list on the directory page")
    items = re.split(r'<li class="list-group-item\b', lst.group(0))[1:]
    if not items:
        raise ValueError("the staff list is empty")
    districts = {}
    for li in items:
        nm = re.findall(r'<a href="(/m/directory/employee\?eid=\d+)" class="fw-bold[^"]*">(.*?)</a>', li, re.S)
        if len(nm) != 1:
            raise ValueError("a staff entry without exactly one name link")
        href, name = nm[0][0], txt(nm[0][1])
        labels = {txt(x) for x in re.findall(r'<div class="[^"]*d-(?:sm-)?(?:block|none)[^"]*">(.*?)</div>', li, re.S)}
        nums = {district_number(l) for l in labels}
        if len(nums) != 1 or None in nums:
            raise ValueError("entry for %r has district labels %r" % (name, sorted(labels)))
        if not all(re.fullmatch(r"District \d{1,2}", l) for l in labels):
            raise ValueError("entry for %r carries an unexpected title %r" % (name, sorted(labels)))
        email = county_email(mailtos(li), DOMAINS)
        districts.setdefault(str(nums.pop()), []).append(
            member(name, email=email, profileUrl=BASE + href, phones=read_phones(li)))
    return {"districts": districts, "atLarge": []}
