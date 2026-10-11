"""Washington County elects one commissioner from each of 15 districts. The
commission's own page gives every member one heading of the form
`<h2 class="subhead1">Name<br>Nth Commission District</h2>`, followed by a
"Name Contact & Biography" link to the member's page on the county's domain
and, for the chairman only, a line reading "Commission Chairman". The district
is read from the member's own heading, never from page order.

The member pages carry a home address, a per-member phone and an e-mail on
wc911.org (not a county domain), so none of them is read and nothing from them
is recorded; the page itself publishes no e-mail or phone for any member.

Currency: the County Clerk's minutes of the organizational meeting of
10 September 2026 name the same fifteen commissioners (13 present, Wexler and
Malone absent) and record Greg Matherly elected chairman. District 13 was a
507-507 tie on 6 August 2026 (Kenneth "Kenny" Huffine and Cynthia "Cindy"
Humphrey); the outgoing commission adopted Resolution 26-08-18 on 31 August
2026 determining that tie under T.C.A. 2-8-111. The minutes record the
adoption but not which alternative was written into it; Huffine is listed as
a commissioner present at the 10 September meeting."""
import re
from ._common import txt, district_number, member

COUNTY = "Washington"; FIPS = "179"
DOMAINS = ("washingtoncountytn.org",)
URLS = ["https://www.washingtoncountytn.org/208/County-Commission"]
SEATS = {str(i): 1 for i in range(1, 16)}
AT_LARGE = 0
BASE = "https://www.washingtoncountytn.org"

HEAD = re.compile(r'<h2 class="subhead1"[^>]*>(.*?)</h2>', re.S)


def parse(pages):
    page = pages[URLS[0]]
    heads = list(HEAD.finditer(page))
    districts = {}
    for i, h in enumerate(heads):
        inner = h.group(1)
        if "Commission District" not in inner:
            # The page's only other subhead1 heading is "Overview".
            if txt(inner) != "Overview":
                raise ValueError("unexpected heading %r" % txt(inner))
            continue
        parts = re.split(r"<br\s*/?>", inner, flags=re.I)
        if len(parts) != 2:
            raise ValueError("member heading not 'Name<br>District': %r" % txt(inner))
        name, label = txt(parts[0]), txt(parts[1])
        d = district_number(label)
        if not d or not re.fullmatch(r"\d{1,2}(st|nd|rd|th) Commission District", label):
            raise ValueError("no district in heading %r" % label)
        # The member's block runs to the next heading.
        end = heads[i + 1].start() if i + 1 < len(heads) else len(page)
        block = page[h.end():end]
        link = re.search(r'<a href="((?:https://www\.washingtoncountytn\.org)?/\d+/[^"]+)">([^<]*)Contact', block)
        if not link:
            raise ValueError("no Contact & Biography link for %r" % name)
        url = link.group(1)
        if url.startswith("/"):
            url = BASE + url
        surname = name.replace(",", " ").split()
        # Guard: the link must name the same person as the heading.
        if not any(w in txt(link.group(2)) for w in surname if len(w) > 2):
            raise ValueError("link text %r does not match heading %r" % (link.group(2), name))
        role = None
        btxt = txt(block)
        if "Commission Chairman" in btxt:
            role = "Chairman"
        if re.search(r"Vice[- ]Chair", btxt):
            raise ValueError("a vice-chair line appeared for %r; decide how to record it" % name)
        districts.setdefault(str(d), []).append(member(name, role=role, profileUrl=url))
    return {"districts": districts, "atLarge": []}
