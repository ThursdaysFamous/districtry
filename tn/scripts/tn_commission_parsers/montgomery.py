"""Montgomery County's commission is 21 commissioners, one from each of 21
districts. The county's commission page shows one Bootstrap card per member:
a photo linking to that seat's own page (/commission/districtN) and a card body
holding the name in <strong> and, in the same body, a link to that district's
map labelled "District N". The name and the district are read from the same
card, and the profile link's number must agree with the label, so nothing is
taken from page order.

THE HEADING STILL SAYS "2022-2026 Montgomery County Commissioners" AND IS STALE.
The names under it are the sitting commission: checked on 2026-10-11 against
the Montgomery County Election Commission's August 6 2026 precinct summary
(montgomerytn.gov), summing each district's precincts, all 21 card names are
that night's winners
(e.g. District 6 Clayton Rudder, District 20 Renee Michelle Bruens, District 21
Brad VanKirk), and photos for the new members sit under Commissioners-Sept-2026.
So the heading is not used for anything.

This page carries no e-mail or phone. Each seat's own page, linked as
profileUrl, carries a Cloudflare-obfuscated seat address (district1@
montgomerytn.gov on the District 1 page, read 2026-10-11) and, on 16 of the 21
pages on 17 October 2026, a telephone number.

PHONES come from those seat pages (member_pages), which the scraper reads
through the same robots.txt check and pacing as the commission page. Under
Adam's ruling of 2026-10-17 that a number a government publishes beside an
official ships whosever line it is, the number is read as printed from the
paragraph of the page's member card, and only when the page's <h1> is the
roster's "District N" and every card on it (the page prints the card twice,
for narrow and wide screens) names the roster's member and district and
prints the same number; otherwise that member's number is withheld with a
note. District 6's number is printed with a space where a hyphen usually is
(in the shape "(931) 555 0100") and is read and shipped that way. The seat
address is not read: e-mail handling did not change with that ruling, which is
about telephone numbers."""
import re
from ._common import txt, district_number, member, page_field, add_phones, same_person, Withheld

COUNTY = "Montgomery"; FIPS = "125"
DOMAINS = ("montgomerytn.gov", "mcgtn.org")
URLS = ["https://montgomerytn.gov/commission"]
SEATS = {str(i): 1 for i in range(1, 22)}
AT_LARGE = 0
BASE = "https://montgomerytn.gov"
CARD = re.compile(r'<div class="card-body pt-0">(.*?)</div>', re.S)
# The seat address as Cloudflare obfuscates it: the link is left out, unread.
CF_MAIL = re.compile(r'<a\b[^>]*href="[^"]*email-protection[^"]*"[^>]*>.*?</a>', re.S | re.I)


def _roster(pages):
    """The commission page alone: {district: [member record]}, phones not read."""
    page = pages[URLS[0]]
    if "Montgomery County Commission" not in page:
        raise ValueError("commission page lacks its own heading")
    cards = re.split(r'<div class="card card-profile\b', page)[1:]
    if not cards:
        raise ValueError("no commissioner cards on the page")
    districts = {}
    for i, c in enumerate(cards, 1):
        body = re.search(r'<div class="card-body">(.*?)</div>', c, re.S)
        if not body:
            raise ValueError("commissioner card %d has no card body" % i)
        body = body.group(1)
        nm = re.search(r"^\s*<strong>(.*?)</strong>", body, re.S)
        lab = re.search(r'<a href="[^"]*/maps/District(\d+)\.pdf"><strong>(.*?)</strong></a>', body)
        if not nm or not lab:
            # Says which card and never quotes it: a card's text can carry a
            # member's street address.
            raise ValueError("commissioner card %d of %d lacks a name or a "
                             "district label" % (i, len(cards)))
        num = district_number(txt(lab.group(2)))
        if num is None or str(num) != lab.group(1):
            raise ValueError("district label %r disagrees with its map link" % txt(lab.group(2)))
        prof = re.search(r'<a href="(/commission/district(\d+))">', c)
        if not prof or prof.group(2) != str(num):
            raise ValueError("card for District %d links to %r" % (num, prof and prof.group(1)))
        name = txt(nm.group(1))
        districts.setdefault(str(num), []).append(member(name, profileUrl=BASE + prof.group(1)))
    return districts


def member_pages(pages):
    """The seat pages the commission page links, one per district, on the
    county's own host: the scraper reads them for parse()."""
    return [r["profileUrl"] for ms in _roster(pages).values() for r in ms]


def page_phones(page, name, d):
    """The number a seat page's member card prints, or a Withheld reason when
    the page does not plainly name this member and district."""
    heads = [txt(h) for h in re.findall(r"<h1\b[^>]*>(.*?)</h1>", page, re.S)]
    if heads != ["District %s" % d]:
        return Withheld("the seat page's heading is not this district")
    fields = []
    for body in CARD.findall(page):
        title = [txt(t) for t in re.findall(r'<h4 class="card-title[^"]*">(.*?)</h4>', body, re.S)]
        label = [txt(t) for t in re.findall(r'<h[56] class="card-category[^"]*">(.*?)</h[56]>',
                                            body, re.S)]
        paras = re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S)
        if len(title) != 1 or label != ["District %s" % d] or len(paras) != 1 or \
                not (same_person(title[0], name) and same_person(name, title[0])):
            return Withheld("a card on the seat page does not name this member and district")
        fields.append(CF_MAIL.sub(" ", paras[0]))
    if not fields:
        return Withheld("the seat page carries no member card")
    found = [page_field(f) for f in fields]
    if any(isinstance(f, Withheld) for f in found):
        return next(f for f in found if isinstance(f, Withheld))
    if any(f != found[0] for f in found):
        return Withheld("the seat page's cards print different numbers")
    return found[0]


def parse(pages):
    districts = _roster(pages)
    for d, ms in districts.items():
        districts[d] = [add_phones(r, page_phones(pages[r["profileUrl"]], r["name"], d))
                        for r in ms]
    return {"districts": districts, "atLarge": []}
