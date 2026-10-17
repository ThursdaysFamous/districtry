"""Madison County elects 25 commissioners from 10 districts: three in
Districts 2, 4, 5, 9 and 10 and two in Districts 1, 3, 6, 7 and 8 (the ballot
calls them Position 1, 2, 3; the pages do not, so no seat is recorded).

The commission page (/154/County-Commission) names no member; under "View All
Districts" it links one page per district, "District One" .. "District Ten".
Each district page's own <h1> names its district, and every member on it is a
`<div class="fr-view">` block holding an <h3> name, then a home address, a
phone and an e-mail link. A member's district is the district the page's own
heading names, and the parser checks that page is the one the commission page
links under that name; nothing is read from order.

PRIVACY: the address and phone in every block are the member's own (some are
labelled Home, Cell or a business office). The phones are recorded as printed,
each label kept in front of its number ("home (731) ...", "office (731) ..."),
under Adam's ruling of 2026-10-17 that a number a government publishes beside
an official ships whosever line it is; a number labelled Fax is not kept. Only
telephone-shaped numbers are read from a block; the address is never read. The
commission office's line on the commission page and the county's line printed
at the foot of every page are OFFICE_LINES and never land on a member. Each
block ends with a visible link "Email <member's name>", and only that link is
read: some blocks also hold empty mailto links a reader never sees, left over
from a former member (titled "Email Luther T. Mercer" inside Tina Mercer's and
Mike Bailey's blocks) or from an earlier address (inside William C. Martin's).
The address the visible link opens is recorded, a personal or business one
(aol, bellsouth, yahoo, a business domain) as much as the county's, under
Adam's choice of 2026-10-17 that a personal address a government page prints
beside an official is shown ("E-mails too"); a madisoncountytn.gov address
must contain the member's surname or the parse raises. Julie Wiser's link
opens the commission coordinator's address (smcclain@), which the commission
page prints as its own, so no address is recorded for her. Juanita Jones's
link is written "mailto:mailto%20jjones@..." and is read as the address it
plainly is.

Currency: the Madison County Election Commission's election-night summary of
6 August 2026 (scanned, read as an image) gives the same 25 winners by
district."""
import re
from ._common import (txt, mailtos, district_number, member, read_phones, member_email,
                      address_of, MAILTO_A, MAILTO_HREF)

COUNTY = "Madison"; FIPS = "113"
DOMAINS = ("madisoncountytn.gov",)
BASE = "https://www.madisoncountytn.gov"
# Whole literals rather than BASE + path, so each page a reader of this file
# (or the fleet's user-agent probe) sees is a page the scraper fetches.
URLS = [
    "https://www.madisoncountytn.gov/154/County-Commission",
    "https://www.madisoncountytn.gov/158/District-One",
    "https://www.madisoncountytn.gov/159/District-Two",
    "https://www.madisoncountytn.gov/160/District-Three",
    "https://www.madisoncountytn.gov/161/District-Four",
    "https://www.madisoncountytn.gov/162/District-Five",
    "https://www.madisoncountytn.gov/163/District-Six",
    "https://www.madisoncountytn.gov/164/District-Seven",
    "https://www.madisoncountytn.gov/165/District-Eight",
    "https://www.madisoncountytn.gov/166/District-Nine",
    "https://www.madisoncountytn.gov/167/District-Ten",
]
SEATS = {"1": 2, "2": 3, "3": 2, "4": 3, "5": 3, "6": 2, "7": 2, "8": 2,
         "9": 3, "10": 3}
AT_LARGE = 0
# The commission office's line (commission page) and the county's line printed
# at the foot of every page.
OFFICE_LINES = ("(731) 988-3110", "731-988-3960")

SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _named_links(blk, sur):
    """The addresses of the block's visible links that read "Email <name>" and
    carry this member's surname; an empty link is never seen and not read."""
    out = []
    for a in MAILTO_A.finditer(blk):
        href = MAILTO_HREF.search(a.group(1))
        shown = txt(a.group(2))
        if href and shown.lower().startswith("email ") and sur and \
                sur in re.sub(r"[^a-z]", "", shown.lower()):
            out.append(address_of(href.group(1)))
    return out


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surname(name):
    words = [w for w in re.split(r"[\s,]+", re.sub(r'"[^"]*"', " ", name)) if w]
    while words and words[-1].lower().strip(".") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def parse(pages):
    home = pages[URLS[0]]
    office = {a.lower() for a in mailtos(home) if _on_domain(a)}
    # The commission page's own list: "District Word" -> its page.
    view = home.find("View All Districts")
    if view < 0:
        raise ValueError("no 'View All Districts' list on the commission page")
    ul = home[view:home.find("</ul>", view)]
    links = {}
    for href, label in re.findall(r'<a href="(/\d+/District-[A-Za-z]+)"[^>]*>([^<]+)</a>', ul):
        d = district_number(txt(label))
        if not d:
            raise ValueError("district link without a number: %r" % label)
        links[str(d)] = BASE + href
    if sorted(links.values()) != sorted(URLS[1:]):
        raise ValueError("commission page links %s, URLS has %s" % (sorted(links.values()), URLS[1:]))

    districts = {}
    for url in URLS[1:]:
        page = pages[url]
        h1 = re.search(r'<h1\b[^>]*id="versionHeadLine"[^>]*>(.*?)</h1>', page, re.S)
        d = district_number(txt(h1.group(1))) if h1 else None
        if not d or links.get(str(d)) != url:
            raise ValueError("%s: heading %r does not match the commission page's link"
                             % (url, txt(h1.group(1)) if h1 else None))
        s = page.find('id="moduleContent"')
        e = page.find('id="featureColumn"', s)
        if s < 0 or e < 0:
            raise ValueError("%s: content region not found" % url)
        body = page[s:e]
        found = []
        for blk in re.findall(r'<div class="fr-view">(.*?)</div>', body, re.S):
            h3 = re.search(r"<h3\b[^>]*>(.*?)</h3>", blk, re.S)
            if not h3:
                if txt(blk) and txt(blk) != "District Representatives":
                    # Never quotes the block: a member's can carry an address.
                    raise ValueError("%s: a text block of %d characters has no name heading"
                                     % (url, len(txt(blk))))
                continue
            name = txt(h3.group(1))
            sur = _surname(name)
            mine = []
            for a in _named_links(blk, sur):
                if a.lower() in office:
                    continue
                if _on_domain(a) and not (sur and sur in a.split("@", 1)[0].lower()):
                    raise ValueError("%s: the county address under %r does not look like theirs"
                                     % (url, name))
                mine.append(a)
            found.append(member(name, email=member_email(mine, DOMAINS), phones=read_phones(blk)))
        if not found:
            raise ValueError("%s: no members found" % url)
        districts[str(d)] = found
    return {"districts": districts, "atLarge": []}
