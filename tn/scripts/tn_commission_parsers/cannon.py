"""Cannon County elects 10 commissioners, two from each of 5 districts ("10
elected County Commissioners, two for each of the five voting districts", the
page says). The ballot runs one race per district and names no seat, so no
seat is recorded.

The county's Commissioners page (WordPress) says "Below are the current
County Commissioners by district:" and then gives each district a bold
paragraph "District One:" .. "District Five:" followed by one paragraph per
member, "<name><br><e-mail link>", with a separator rule before the next
district. The list is cut at those bold district paragraphs, so each member is
paired with the heading of the section they sit in, never with order; every
section must hold exactly the seats the county elects there, and a member
paragraph before the first heading raises.

E-MAIL: every member's paragraph PRINTS an address of the form
First.Last@CannonCountyTN.gov, but the link behind it does not always go
there: Nathan Sanders's link is an empty "mailto:", and the links under the
printed addresses of Curtis George, Randy Gannon and Kristal Alexander go to
personal addresses (yahoo, gmail; Curtis George's to an address in another
person's name). An address is therefore recorded only where the link and the
printed text are the same county address (case aside) AND its local part
carries the member's surname: six members. The other four get none, since
what the page would send is not what it prints. The personal addresses behind
those links are never recorded.

PRIVACY: Marty Williams's paragraph prints a phone, (615) 456-0068, that
nothing labels a county line; it is not recorded. The page prints no address.

Currency: checked 2026-10-11 against the Cannon County Election
Commission's results of the 6 August 2026 county general election, linked
from its page on the county site (cannoncountytn.gov/election-commission-2/,
"Aug 6, 2026 Primary Election Results", "Pages 1-2":
wp-content/uploads/2026/08/20260825_140251.pdf, a scanned PDF footed August
17, 2026, read as images; "Pages 3-4" were not needed). In every district the
two names here are the two highest vote-getters: D1 Sanders 409, Schoen 232
(Taylor 216); D2 Williams 379, Adkins 368 (Herron 126); D3 George 327,
Basham 262 (Martin 170); D4 Gannon 374, Hollandsworth 294 (McGee 235); D5
Burnett 289, Alexander 226. Ballot spellings differ only by middle initials
(Nathan A. Sanders, Shea R. Basham, Curtis W. George, Randy D. Gannon,
Michael W. Hollandsworth, Tony R. Burnett). The page names no chair, so no
role is recorded."""
import re
from ._common import txt, district_number, member

COUNTY = "Cannon"; FIPS = "015"
DOMAINS = ("cannoncountytn.gov",)
URLS = ["https://cannoncountytn.gov/county-commissioners/"]
SEATS = {str(i): 2 for i in range(1, 6)}
AT_LARGE = 0

P = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
HEAD_RE = re.compile(r"^<strong>\s*(District\s+[A-Za-z]+)\s*:\s*</strong>$")
LINK = re.compile(r'<a\b[^>]*href="mailto:([^"?]*)[^"]*"[^>]*>(.*?)</a>', re.S)
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
PHONE = re.compile(r"^\(?\d{3}\)?[-. ]?\d{3}[-. ]\d{4}$")
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surname(name):
    words = [w for w in name.split() if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def read_member(d, para):
    segs = [txt(s) for s in re.split(r"<br\s*/?>", para, flags=re.I)]
    segs = [s for s in segs if s]
    if not segs or not NAME.match(segs[0]) or re.search(r"\bvacan", segs[0], re.I):
        raise ValueError("District %s: %r does not open with a name" % (d, segs))
    name = segs[0]
    for extra in segs[1:]:
        if not (EMAIL.match(extra) or PHONE.match(extra)):
            raise ValueError("District %s: unexpected line %r under %r" % (d, extra, name))
    email = None
    links = LINK.findall(para)
    if len(links) > 1:
        raise ValueError("District %s: %r carries %d e-mail links" % (d, name, len(links)))
    if links:
        href, shown = links[0][0].strip(), txt(links[0][1])
        if (href.lower() == shown.lower() and _on_domain(shown)
                and _surname(name) in shown.split("@", 1)[0].lower()):
            email = shown
    return member(name, email=email)


def parse(pages):
    page = pages[URLS[0]]
    start = page.find("Below are the current County Commissioners by district")
    end = page.find('id="site-aside-secondary"', start)
    if start < 0 or end < 0:
        raise ValueError("the commissioner list or the end of the page content is missing")
    districts, d = {}, None
    for para in P.findall(page, start, end):
        body = para.strip()
        if not txt(body) or "Below are the current" in body:
            continue
        m = HEAD_RE.match(body)
        if m:
            n = district_number(m.group(1))
            if not n:
                raise ValueError("district heading %r has no number" % txt(body))
            d = str(n)
            if d in districts:
                raise ValueError("District %s has two headings" % d)
            districts[d] = []
            continue
        if re.search(r"\bDistrict\b", txt(body)):
            raise ValueError("a paragraph names a district but is not a heading: %r" % txt(body))
        if d is None:
            raise ValueError("a member paragraph sits before the first district heading")
        districts[d].append(read_member(d, body))
    for n, ms in districts.items():
        if len(ms) != SEATS.get(n):
            raise ValueError("District %s lists %d members, the county elects %s"
                             % (n, len(ms), SEATS.get(n)))
    return {"districts": districts, "atLarge": []}
