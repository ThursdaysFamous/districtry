"""Cheatham County elects 12 commissioners, two from each of 6 districts. The
ballot lists each district as one contest ("County Commission District N")
and names no seat, so no seat is recorded. The page names no commission
office, so no role is recorded.

The "Commission by District" page (a Bootstrap portfolio template) holds one
"portfolio-item" block per member: a photo, a "Commissioner Bio" PDF link,
an <h3> reading "District N - Map" (linked to that district's map page,
disclaimer_comptroller_districtN.html), then a paragraph opening with the
member's name in <strong>, followed by address, phone and an "Email" link.
Each block is read on its own: the member's district is the <h3> of the same
block, and the <h3>'s map link must name the same district, so a heading
that drifted from its link raises. Nothing is read from order. A block
without exactly one district heading and one bold name raises, and every
district 1..6 must appear.

E-mail: every member's "Email" link is a per-member county address,
first.last@cheathamcountytn.gov (bj.hudspeth@ for B.J. Hudspeth, Diana.lovell@
for Diana Pike Lovell). It is kept only on cheathamcountytn.gov and only when
its local part carries the member's surname; a county address that does not
carry it raises rather than being attached to the wrong person. An address on
another domain in a member's own block is kept as printed when it prints no
county one, under Adam's ruling of 2026-10-17 that an e-mail address a
government page prints beside an official ships too.

PRIVACY: every block prints the member's home street address, town and ZIP
and one or two phones (two labelled "- Cell"). The phones are recorded as
printed, a "- Cell" label kept as "cell" in front of its number, under Adam's
ruling of 2026-10-17 that a number a government publishes beside an official
ships whosever line it is; only telephone-shaped numbers are read from a
block, never its address, town or ZIP. Some photo links point at image files
named for former members (gary_binkley.jpg, betty_ramsey.jpg); they are not
read.

Names are kept as printed ("B.J. Hudspeth", "Diana Pike Lovell"). The photo
alt texts are not read.

Currency: checked 2026-10-11 against the Cheatham County Election
Commission's "Certification of Election Results for the County General
Election held August 6, 2026" (cheathamcountytn.gov/uploads/
20260827_090853.pdf, linked from the county's Election Results page as
"Certified Results (County Election) August 6, 2026"; a 16-page scan, the
certificate signed by five election commissioners and dated 20 August 2026,
read as images). In every district the two names here are the two highest
totals: D1 David Anderson 556, Calton Blacker 381 (uncontested); D2 Tim
Williamson 674, Randy Noe 551 (Amber Y. Locke 245, Aric Storck 196); D3 Bj
Hudspeth 820, Chris Gilmore 770 (Sarah Knack 269); D4 James E. Gupton Jr.
751, Walter Weakley 713 (Matt Waldron 386, Sandra Red Gregory 229); D5 Diana
Pike Lovell 701, Jody Vann 647 (Eugene Evans Sr. 516); D6 James "Jimmy"
Hedgepath 720, Clint Biggers 601 (Jan Morrison 526). The page prints
"James Gupton" without the "Jr." the certificate carries."""
import re
from ._common import txt, mailtos, member, district_number, read_phones, other_email

COUNTY = "Cheatham"; FIPS = "021"
DOMAINS = ("cheathamcountytn.gov",)
URLS = ["https://cheathamcountytn.gov/commission.html"]
SEATS = {str(i): 2 for i in range(1, 7)}
AT_LARGE = 0

BLOCK = re.compile(r'<div class="portfolio-item\b')
H3 = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.S | re.I)
LABEL = re.compile(r"^District\s+(\d{1,2})\s*-\s*Map$")
MAPLINK = re.compile(r'href="disclaimer_comptroller_district(\d{1,2})\.html"')
NAME_TAG = re.compile(r'<p class="margin-top-10">\s*<strong>(.*?)</strong>', re.S)
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surname(name):
    words = [w for w in name.split() if w.lower().strip(".,") not in SUFFIX]
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def _email(name, block):
    out = None
    for a in mailtos(block):
        if not _on_domain(a):
            continue
        if _surname(name) not in a.split("@", 1)[0].lower():
            raise ValueError("county address %r in %r's block does not carry the surname" % (a, name))
        if out and out.lower() != a.lower():
            raise ValueError("%r's block carries two county addresses" % name)
        out = a
    return out or other_email(block, DOMAINS)


def parse(pages):
    page = pages[URLS[0]]
    blocks = BLOCK.split(page)[1:]
    if not blocks:
        raise ValueError("no portfolio-item blocks on the page")
    districts = {}
    for b in blocks:
        b = b.split('<div class="clearfix">', 1)[0]
        heads, names = H3.findall(b), NAME_TAG.findall(b)
        if len(heads) != 1 or len(names) != 1:
            raise ValueError("a block holds %d district headings and %d bold names"
                             % (len(heads), len(names)))
        label = txt(heads[0])
        m = LABEL.match(label)
        if not m or district_number(label) != int(m.group(1)):
            raise ValueError("a block's heading is not 'District N - Map': %r" % label)
        d = m.group(1)
        links = set(MAPLINK.findall(heads[0]))
        if links != {d}:
            raise ValueError("District %s heading links the map of district(s) %s" % (d, sorted(links)))
        name = txt(names[0])
        if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
            raise ValueError("District %s: %r does not look like a name" % (d, name))
        districts.setdefault(d, []).append(member(name, email=_email(name, b), phones=read_phones(b)))
    if set(districts) != set(SEATS):
        raise ValueError("the page names districts %s, not 1..6" % sorted(districts, key=int))
    return {"districts": districts, "atLarge": []}
