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

E-mail and phone are NOT read. This page carries neither; each seat's own page
carries a Cloudflare-obfuscated seat address (district1@montgomerytn.gov on the
District 1 page, read 2026-10-11) and a number with nothing saying it is a
county office line. Reading them would cost 21 more requests a week, so the
card links to the seat page as profileUrl instead, on the county's own domain."""
import re
from ._common import txt, district_number, member

COUNTY = "Montgomery"; FIPS = "125"
DOMAINS = ("montgomerytn.gov", "mcgtn.org")
URLS = ["https://montgomerytn.gov/commission"]
SEATS = {str(i): 1 for i in range(1, 22)}
AT_LARGE = 0
BASE = "https://montgomerytn.gov"


def parse(pages):
    page = pages[URLS[0]]
    if "Montgomery County Commission" not in page:
        raise ValueError("commission page lacks its own heading")
    cards = re.split(r'<div class="card card-profile\b', page)[1:]
    if not cards:
        raise ValueError("no commissioner cards on the page")
    districts = {}
    for c in cards:
        body = re.search(r'<div class="card-body">(.*?)</div>', c, re.S)
        if not body:
            raise ValueError("a commissioner card with no card body")
        body = body.group(1)
        nm = re.search(r"^\s*<strong>(.*?)</strong>", body, re.S)
        lab = re.search(r'<a href="[^"]*/maps/District(\d+)\.pdf"><strong>(.*?)</strong></a>', body)
        if not nm or not lab:
            raise ValueError("card body without a name and a district label: %r" % txt(body)[:80])
        num = district_number(txt(lab.group(2)))
        if num is None or str(num) != lab.group(1):
            raise ValueError("district label %r disagrees with its map link" % txt(lab.group(2)))
        prof = re.search(r'<a href="(/commission/district(\d+))">', c)
        if not prof or prof.group(2) != str(num):
            raise ValueError("card for District %d links to %r" % (num, prof and prof.group(1)))
        name = txt(nm.group(1))
        districts.setdefault(str(num), []).append(member(name, profileUrl=BASE + prof.group(1)))
    return {"districts": districts, "atLarge": []}
