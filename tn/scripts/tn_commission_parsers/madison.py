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
labelled Home, Cell or a business office) and are never recorded. Only an
e-mail on madisoncountytn.gov whose local part contains the member's surname is
recorded, because the blocks also carry personal addresses (aol, bellsouth,
yahoo, a business domain), hidden mailto links left over from a former member
("Email Luther T. Mercer" inside Tina Mercer's and Mike Bailey's blocks), and
Julie Wiser's link points to the commission coordinator's address
(smcclain@), which is read off the commission page and never attached to a
member. Juanita Jones's link is written "mailto:mailto%20jjones@..." and is
cleaned to the address it plainly is.

Currency: the Madison County Election Commission's election-night summary of
6 August 2026 (scanned, read as an image) gives the same 25 winners by
district."""
import re
from ._common import txt, mailtos, district_number, member

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

SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _clean(addr):
    return re.sub(r"^(?:mailto(?::|%3a)?(?:%20)*)+", "", addr.strip(), flags=re.I)


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
                    raise ValueError("%s: a text block with no name heading: %r" % (url, txt(blk)[:80]))
                continue
            name = txt(h3.group(1))
            sur = _surname(name)
            email = None
            for a in (_clean(x) for x in mailtos(blk)):
                if not _on_domain(a) or a.lower() in office:
                    continue
                if sur and sur in a.split("@", 1)[0].lower():
                    email = a
                    break
                raise ValueError("%s: county address %r does not look like %r's" % (url, a, name))
            found.append(member(name, email=email))
        if not found:
            raise ValueError("%s: no members found" % url)
        districts[str(d)] = found
    return {"districts": districts, "atLarge": []}
