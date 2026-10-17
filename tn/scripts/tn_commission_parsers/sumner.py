"""Sumner County's commission is 24 commissioners, one from each of 24
districts. The county's commission page lists them under "County Commission
2026 - 2030" as one WordPress post per member (<article ... category-
commissioners>): the post title is the name and links to the member's own page
on sumnercountytn.gov, the post excerpt is the district ("1st District" ..
"24th District"), and the post content holds a street address, a phone and a
county e-mail. Name and district come from the same article, never from order.

PRIVACY: the address in each post is the member's own (a home street or a P.O.
box in their town) and is never read. The phone beside it is often the
member's own line; under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is, it is read
from the post content into `phone`, as printed (several carry an area code
from another state, which is kept). Only telephone-shaped numbers are read.
The e-mail is kept only when it is on sumnercountytn.gov, as the county
prints it (one is capitalised, Jerry.Becker@SumnerCountyTN.gov).

CURRENCY was checked on 2026-10-11 against the Sumner County Election
Commission's own Final Results for 6 August 2026 (votesumnertn.org, a scanned
PDF read as images): each of the 24 districts elected one commissioner and the
24 winners are the 24 names here, with the page using full given names where
the ballot used short ones (Daniel/Dan Bristol, James Rohnkohl, Jr./Jim
Rohnkohl, Jacob/Jake Edgar, J. Wes/Wes Wynne). The photos are uploads of
2026/09."""
import re
from ._common import txt, mailtos, county_email, district_number, member, read_phones

COUNTY = "Sumner"; FIPS = "165"
DOMAINS = ("sumnercountytn.gov",)
URLS = ["https://sumnercountytn.gov/government/county-commission/"]
SEATS = {str(i): 1 for i in range(1, 25)}
AT_LARGE = 0


def parse(pages):
    page = pages[URLS[0]]
    if not re.search(r">\s*County Commission \d{4}\s*-\s*\d{4}\s*<", page):
        raise ValueError("the term heading 'County Commission YYYY - YYYY' is gone")
    posts = [b.split("</article>", 1)[0] for b in re.split(r"<article\b", page)[1:]
             if "category-commissioners" in b[:400]]
    if not posts:
        raise ValueError("no commissioner posts on the page")
    districts = {}
    for b in posts:
        title = re.findall(r'elementor-widget-theme-post-title\b.*?<a href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
        exc = re.findall(r'elementor-widget-theme-post-excerpt\b.*?<div class="elementor-widget-container">(.*?)</div>', b, re.S)
        if len(title) != 1 or len(exc) != 1:
            raise ValueError("a commissioner post without exactly one title and one excerpt")
        url, name = title[0][0], txt(title[0][1])
        label = txt(exc[0])
        num = district_number(label)
        if num is None or not re.fullmatch(r"\d{1,2}(st|nd|rd|th) District", label):
            raise ValueError("post for %r has district label %r" % (name, label))
        content = b.split("elementor-widget-theme-post-content", 1)
        email = county_email(mailtos(content[1]) if len(content) == 2 else [], DOMAINS)
        phones = read_phones(content[1]) if len(content) == 2 else None
        prof = url if re.match(r"https://sumnercountytn\.gov/", url) else None
        districts.setdefault(str(num), []).append(
            member(name, email=email, profileUrl=prof, phones=phones))
    return {"districts": districts, "atLarge": []}
