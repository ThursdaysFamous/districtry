"""Davidson County is the Metropolitan Government of Nashville and Davidson
County, and its county legislative body is the Metro Council: 35 district
members and 5 elected countywide. The council's own page lists all 40 as one
<article> per member. A district member's block carries the district number in
its own field (`district-number`), an at-large member's carries the label
"Council Member At-Large" and a link to /at-large-N, so neither is read from
page order. The phones are the council office's own numbered lines
(615-432-13NN, the last two digits the seat), printed on the government's page
for every member, so they are official. E-mails are Cloudflare-obfuscated and
decoded; only nashville.gov addresses are kept. The council was elected in
August 2023 for a term to 2027, so this list is the sitting council."""
import re
from ._common import txt, mailtos, county_email, member

COUNTY = "Davidson"; FIPS = "037"
DOMAINS = ("nashville.gov",)
URLS = ["https://www.nashville.gov/departments/council/districts"]
SEATS = {str(i): 1 for i in range(1, 36)}
AT_LARGE = 5
PHONES = True
TITLE = "Council Member"
BODY = "Metro Council"
BASE = "https://www.nashville.gov"


def parse(pages):
    page = pages[URLS[0]]
    blocks = re.split(r"<article\b", page)[1:]
    districts, at_large = {}, []
    for b in blocks:
        if "node--type-council-district" not in b[:300]:
            continue
        b = b.split("</article>", 1)[0]
        nm = re.search(r'field--name-field-council-member-name[^>]*>(.*?)</div>', b, re.S)
        if not nm:
            raise ValueError("a council block with no name field")
        name = txt(nm.group(1))
        href = re.search(r'href="(/departments/council/districts/(?:district|at-large)-\d+)"', b)
        tel = re.search(r'href="tel:([0-9-]{12})"', b)
        email = county_email(mailtos(b), DOMAINS)
        rec = member(name, email=email, phone=tel.group(1) if tel else None,
                     profileUrl=BASE + href.group(1) if href else None)
        num = re.search(r'field--name-field-select-district-numeric[^>]*>\s*District\s+(\d+)\s*<', b)
        if num:
            districts.setdefault(num.group(1), []).append(rec)
        elif "Council Member At-Large" in b and href and "/at-large-" in href.group(1):
            at_large.append(rec)
        else:
            raise ValueError("council block for %r is neither a district nor at-large" % name)
    return {"districts": districts, "atLarge": at_large}
