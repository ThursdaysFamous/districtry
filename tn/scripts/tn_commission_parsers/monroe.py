"""Monroe County elects 10 commissioners from 4 districts, and the seats are
uneven: three each in Districts 1, 2 and 3 and one in District 4. The page
lists exactly that, the shipped geometry draws four districts, and the
election commission's results agree: in both 2022 (official results dated
August 18, 2022) and 2026 District 4 had a single candidate and a single
winner, while Districts 1-3 each elected three, in 2022 from four or five
candidates. No seat letters are published or recorded, and the page names no
commission chair.

The "Board of County Commissioners" page (WordPress/Elementor) gives each
district a container opening with an <h2> "First District" .. "Fourth
District", followed by one text widget per member reading "<Name> –
Commissioner" and, in the same widget, the member's monroetn.gov address as
plain text (not a link). The page is cut at those <h2> headings (up to the
"Further Contact Information" heading that follows the last district) and each
name is paired with the heading of the section its widget sits in, and each
e-mail with the name in its own widget; nothing is read from order. A widget
that is not "<Name> – Commissioner" plus at most one address raises.

PRIVACY: the page prints no address or phone for a member. Each member's
e-mail is firstname.lastname@monroetn.gov, on the county's own domain, and is
kept only when its local part contains the member's surname. The mayor's
office phone, the county attorney's and county clerk's addresses below the
roster belong to those offices and are not read.

Currency: checked 2026-10-11 against the Monroe County Election Commission's
results of the 6 August 2026 county general election, linked from its own
site (monroecountyelectioncommission.com/election-results) as "8-6-26
Federal-State Primary-County General El.pdf" and served from that site's file
host (img1.wsimg.com): an 8-page scan with every page dated August 13, 2026,
read as images. In all four districts the names on this page are the winners
(ballot spellings Adam W. Reynolds, Donald "Dj" Seiler, Mark T. Hatcher, David
Allen Winters, Kraig (Possum) Miller). Districts 1, 3 and 4 had exactly as many
candidates as seats; in District 2 the three named here beat a write-in with 9
votes."""
import re
from ._common import txt, lines, district_number, member

COUNTY = "Monroe"; FIPS = "123"
DOMAINS = ("monroetn.gov",)
URLS = ["https://monroetn.gov/board-of-county-commissioners/"]
SEATS = {"1": 3, "2": 3, "3": 3, "4": 1}
AT_LARGE = 0

H2 = re.compile(r'<h2 class="elementor-heading-title[^"]*">(.*?)</h2>', re.S)
WIDGET = re.compile(r'data-widget_type="text-editor\.default">\s*<div class="elementor-widget-container">(.*?)</div>', re.S)
ENTRY = re.compile(r"^(?P<name>[A-Z][A-Za-z.'’\" -]+?)\s*[–—-]\s*Commissioner$")
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _surname(name):
    words = [w for w in re.split(r"\s+", re.sub(r'["(][^")]*[")]', " ", name)) if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def parse(pages):
    page = pages[URLS[0]]
    heads = list(H2.finditer(page))
    titles = [txt(h.group(1)) for h in heads]
    try:
        first = titles.index("Board of County Commissioners")
        last = titles.index("Further Contact Information", first)
    except ValueError:
        raise ValueError("the roster's opening or closing heading is missing: %s" % titles)
    districts = {}
    for k in range(first + 1, last):
        label = titles[k]
        d = district_number(label)
        if not d or not re.fullmatch(r"[A-Z][a-z]+ District", label):
            raise ValueError("heading %r inside the roster is not 'Nth District'" % label)
        if str(d) in districts:
            raise ValueError("District %d has two headings" % d)
        sect = page[heads[k].end():heads[k + 1].start()]
        seats = []
        for w in WIDGET.findall(sect):
            ls = lines(w)
            if not ls:
                continue
            m = ENTRY.match(ls[0])
            if not m or len(ls) > 2 or (len(ls) == 2 and not EMAIL.match(ls[1])):
                raise ValueError("District %d: a widget that is not 'Name – Commissioner' "
                                 "and an address: %r" % (d, ls))
            name = m.group("name")
            email = None
            if len(ls) == 2:
                addr = ls[1]
                dom = addr.rsplit("@", 1)[-1].lower()
                if any(dom == x or dom.endswith("." + x) for x in DOMAINS):
                    if _surname(name) not in addr.split("@", 1)[0].lower():
                        raise ValueError("District %d: %r does not look like %r's" % (d, addr, name))
                    email = addr
            seats.append(member(name, email=email))
        if not seats:
            raise ValueError("District %d has no members" % d)
        districts[str(d)] = seats
    return {"districts": districts, "atLarge": []}
