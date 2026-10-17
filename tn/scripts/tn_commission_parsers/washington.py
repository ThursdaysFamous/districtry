"""Washington County elects one commissioner from each of 15 districts. The
commission's own page gives every member one heading of the form
`<h2 class="subhead1">Name<br>Nth Commission District</h2>`, followed by a
"Name Contact & Biography" link to the member's page on the county's domain
and, for the chairman only, a line reading "Commission Chairman". The district
is read from the member's own heading, never from page order.

The commission page itself publishes no e-mail or phone for any member. The
member pages carry a home address, which is never read, a per-member phone and
an e-mail address: on 17 October 2026 one member's was on the county's own
domain and the other fourteen on private or 911-district domains.

PHONES come from those member pages (member_pages), which the scraper reads
through the same robots.txt check and pacing as the commission page. Under
Adam's ruling of 2026-10-17 that a number a government publishes beside an
official ships whosever line it is, the number is read from the "Phone:" line
of the paragraph under the page's "Name, District N" heading, and only when
that heading names the roster's member and district; otherwise that member's
number is withheld with a note. The e-mail is not read: e-mail handling did
not change with that ruling, which is about telephone numbers.

Currency: the County Clerk's minutes of the organizational meeting of
10 September 2026 name the same fifteen commissioners (13 present, Wexler and
Malone absent) and record Greg Matherly elected chairman. District 13 was a
507-507 tie on 6 August 2026 (Kenneth "Kenny" Huffine and Cynthia "Cindy"
Humphrey); the outgoing commission adopted Resolution 26-08-18 on 31 August
2026 determining that tie under T.C.A. 2-8-111. The minutes record the
adoption but not which alternative was written into it; Huffine is listed as
a commissioner present at the 10 September meeting."""
import re
from ._common import txt, district_number, member, page_field, add_phones, same_person, Withheld

COUNTY = "Washington"; FIPS = "179"
DOMAINS = ("washingtoncountytn.org",)
URLS = ["https://www.washingtoncountytn.org/208/County-Commission"]
SEATS = {str(i): 1 for i in range(1, 16)}
AT_LARGE = 0
BASE = "https://www.washingtoncountytn.org"

HEAD = re.compile(r'<h2 class="subhead1"[^>]*>(.*?)</h2>', re.S)
MEMBER_HEAD = re.compile(r'<h2 class="subhead1[^"]*"[^>]*>(.*?)</h2>\s*(<p\b.*?</p>)', re.S)
MAILTO = re.compile(r'<a\b[^>]*href="mailto:[^"]*"[^>]*>.*?</a>', re.S | re.I)


def _roster(pages):
    """The commission page alone: {district: [member record]}, phones not read."""
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
    return districts


def member_pages(pages):
    """The member pages the commission page links, one per member, on the
    county's own host: the scraper reads them for parse()."""
    return [r["profileUrl"] for ms in _roster(pages).values() for r in ms]


def page_phones(page, name, d):
    """The number on the "Phone:" line under a member page's "Name, District
    N" heading, or a Withheld reason when the page does not plainly name this
    member and district. The e-mail link and line are left out unread."""
    found = [(m, p) for h, p in MEMBER_HEAD.findall(page)
             for m in [re.fullmatch(r"(.+?),\s*District\s+(\d{1,2})", txt(h))] if m]
    if len(found) != 1:
        return Withheld("the member page has %d 'Name, District N' headings" % len(found))
    m, para = found[0]
    if int(m.group(2)) != int(d) or not same_person(m.group(1), name):
        return Withheld("the member page's heading does not name this member and district")
    fields = [f for f in re.split(r"<br\b[^>]*>", MAILTO.sub(" ", para), flags=re.I) if txt(f)]
    fields = [f for f in fields if not re.match(r"E-?mail\b", txt(f), re.I)]
    phone = [f for f in fields if re.match(r"Phone\s*:", txt(f), re.I)]
    if len(phone) != len(fields) or len(phone) > 1:
        return Withheld("the paragraph under the heading holds lines other than one "
                        "phone line and the e-mail")
    return page_field(phone[0]) if phone else []


def parse(pages):
    districts = _roster(pages)
    for d, ms in districts.items():
        districts[d] = [add_phones(r, page_phones(pages[r["profileUrl"]], r["name"], d))
                        for r in ms]
    return {"districts": districts, "atLarge": []}
