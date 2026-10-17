"""Wilson County's commission is 25 commissioners, one from each of 25
districts ("The Wilson County Commission is made up of 25 people"). The county's
CivicPlus page (/245/County-Commissioners redirects to /222/County-Commission)
gives each member an editor widget of their own: an <h2> with the name, then a
paragraph "County Commissioner, District N" and a "More Information" link to the
member's staff-directory entry. Name and district are read from the same
widget, never from page order.

No e-mail is published (the directory offers a contact form only). The
directory entries print the member's own street address, which is never read.

PHONES come from those directory entries (member_pages), which the scraper
reads through the same robots.txt check and pacing as the roster page. Under
Adam's ruling of 2026-10-17 that a number a government publishes beside an
official ships whosever line it is, the entry's phone and second phone (its
"staff-phone" and "staff-add-phone" lines; the directory labels neither) are
read as printed, and only when the entry's heading names the roster's member
and its subheadings read "District N Commissioner" for the roster's district
and "County Commission"; otherwise that member's numbers are withheld with a
note. Five entries print the area code with a slash ("615/555-0100"), which
is kept as printed. A number printed on both lines is kept once. On 17
October 2026, 22 of the 25 entries printed a number, four printed a second,
different one, and one printed the same number on both lines.

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
from ._common import (txt, district_number, member, page_field, add_phones, same_person,
                      same_number, Withheld)

COUNTY = "Wilson"; FIPS = "189"
DOMAINS = ("wilsoncountytn.gov",)
URLS = ["https://www.wilsoncountytn.gov/245/County-Commissioners"]
SEATS = {str(i): 1 for i in range(1, 26)}
AT_LARGE = 0
PROFILE = "https://www.wilsoncountytn.gov/Directory.aspx?EID=%s"
STAFF_PHONE = re.compile(r'<div id="staff-(phone|add-phone)"[^>]*>(.*?)</div>', re.S)


def _roster(pages):
    """The roster page alone: {district: [member record]}, phones not read."""
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
    return districts


def member_pages(pages):
    """The directory entries the roster page links, rebuilt on the county's
    own host: the scraper reads them for parse()."""
    return [r["profileUrl"] for ms in _roster(pages).values() for r in ms
            if r.get("profileUrl")]


def page_phones(page, name, d):
    """The numbers a directory entry prints on its phone lines, or a Withheld
    reason when the entry does not plainly name this member and district."""
    title = [txt(t) for t in re.findall(r'<h2 class="directory-page-title[^"]*">(.*?)</h2>',
                                        page, re.S)]
    subs = [txt(t) for t in re.findall(r'<h3 class="directory-subhead[^"]*">(.*?)</h3>',
                                       page, re.S)]
    if len(title) != 1 or not (same_person(title[0], name) and same_person(name, title[0])):
        return Withheld("the directory entry's heading does not name this member")
    if len(subs) != 2 or subs[1] != "County Commission" or \
            not re.fullmatch(r"District \d{1,2}(?: Commissioner)?", subs[0]) or \
            district_number(subs[0]) != int(d):
        return Withheld("the directory entry does not name this member's district on the "
                        "County Commission")
    numbers = []
    for _kind, field in STAFF_PHONE.findall(page):
        got = page_field(re.sub(r"<svg\b.*?</svg>", " ", field, flags=re.S))
        if isinstance(got, Withheld):
            return got
        numbers += [n for n in got if not any(same_number(n, k) for k in numbers)]
    return numbers


def parse(pages):
    districts = _roster(pages)
    for d, ms in districts.items():
        districts[d] = [add_phones(r, page_phones(pages[r["profileUrl"]], r["name"], d))
                        if r.get("profileUrl") else r for r in ms]
    return {"districts": districts, "atLarge": []}
