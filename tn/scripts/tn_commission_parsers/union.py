"""Union County's commission has 16 members from 7 districts ("made up of 16
members representing 7 county districts", the page says): three in Districts
1 and 6 and two in Districts 2, 3, 4, 5 and 7, as the page's own district
sections hold them. No seat is called by a letter or number, so no seat is
recorded. The County Mayor (Jason Bailey) "serves as the commission chair";
he holds no commission seat and is not recorded.

The commission page (WordPress, Avada "fusion" layout) gives every district
an <h2> reading "Nth District Commissioners Serving the <community>",
followed by one `fusion-person` block per seat: a `person-name` span with
the name, a `person-title` span reading "County Commissioner, Nth District",
and a `person-content` box with a phone and, for nine of the sixteen, an
e-mail printed as plain text. The page is cut at those <h2> headings and the
title's district must equal the heading of the section the block sits in,
so a block that drifted under the wrong heading raises; nothing is read from
order. Each section must hold exactly the seats the county elects there.

E-mail: an address is recorded only when it is on unioncountytn.gov and its
local part carries the member's surname (R.L. Jones's is roy.jones@, Angela
Conner-Murphy's angela.conner.murphy@). A county address in a block that does
not carry the surname raises rather than being attached to the wrong person.

PRIVACY: every block prints one phone number with no label (the numbers differ
member to member). Under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is, it is read
from the block's `person-content` box into `phone`, as printed. The page
prints no member address.

Currency, checked 2026-10-15: every member on this page is a winner of the
6 August 2026 election in the district the page gives. The Union County
Election Commission's site (www.unioncountytnvotes.com), which answered
HTTP 500 on 2026-10-11 and 2026-10-13, answered on 2026-10-15, robots.txt
allowing the path. Its Election Results page links an "August 6, 2026
precinct based results" file that answers 404 on that host; its media
library lists the election-night "Election Summary Report" of the 2026 State
Primary and County General (wp-content/uploads/2026/08/TOTAL-RESULTS.pdf, a
6-page scan, all 9 precincts reported, run 6 August 2026 at 10:48 PM, not
marked certified), read as images. Its County Commission District 1-7 winners
are exactly the sixteen this page lists, district by district: District 1
Mike Boles, Carrie Shoffner Edds and Gerald Simmons (vote for 3); District 2
Dennis J Nicley and Cheryl Booker Walker; District 3 Kenny Moore and Bill
Cox; District 4 Timothy E.R. Cox and Danny Cooke; District 5 Dustin Berry
and Brett William Pursel; District 6 Ann Dyer, R. L. Jones and Johnny L.
Raley (vote for 3); District 7 Lynn Beeler and Angela Conner-Murphy. Three
margins are narrow on that report (District 3 Bill Cox 248 to Judy Freels
238, District 4 Danny Cooke 246 to Doyle Welch 240, District 7 Angela
Conner-Murphy 212 to Tony Strevel 205); the page, last changed 2026-09-29,
after the term began, seats the same winners, so the two county publications
agree. Names are kept as the page prints them. The page's own "updated"
stamp is 2026-09-29.

Held until then: on 2026-10-11 and 2026-10-13 the election commission's
site answered HTTP 500 (its robots.txt on the second day, which RFC 9309
reads as a refusal of the whole host), so nothing could check the page."""
import re
from ._common import txt, mailtos, district_number, member, read_phones

COUNTY = "Union"; FIPS = "173"
DOMAINS = ("unioncountytn.gov",)
URLS = ["https://unioncountytn.gov/county-commission/"]
SEATS = {"1": 3, "2": 2, "3": 2, "4": 2, "5": 2, "6": 3, "7": 2}
AT_LARGE = 0

HEAD_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
SECTION_RE = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District Commissioners Serving\b")
PERSON_RE = re.compile(r'<div class="fusion-person\b')
NAME_RE = re.compile(r'<span class="person-name">(.*?)</span>\s*<span class="person-title">(.*?)</span>', re.S)
TITLE_RE = re.compile(r"^County Commissioner, (\d{1,2})(?:st|nd|rd|th) District$")
CONTENT_RE = re.compile(r'<div class="person-content\b[^>]*>(.*?)</div>', re.S)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surnames(name):
    """'Angela Conner-Murphy' -> {'connermurphy', 'conner', 'murphy'}."""
    words = [w for w in name.split() if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    last = words[-1].lower() if words else ""
    parts = {re.sub(r"[^a-z]", "", p) for p in [last] + last.split("-")}
    return {p for p in parts if len(p) > 2}


def _email(n, name, block):
    content = CONTENT_RE.search(block)
    body = content.group(1) if content else ""
    for piece in (txt(x) for x in re.split(r"<br\s*/?>", body, flags=re.I)):
        if piece and not PHONE_RE.match(piece) and not EMAIL_RE.fullmatch(piece):
            raise ValueError("District %s: %r's block holds an unexpected line %r" % (n, name, piece))
    found = EMAIL_RE.findall(txt(body)) + mailtos(block)
    keep = None
    for a in found:
        if not _on_domain(a):
            continue
        local = a.split("@", 1)[0].lower()
        if not any(s in re.sub(r"[^a-z]", "", local) for s in _surnames(name)):
            raise ValueError("District %s: county address %r is not %r's" % (n, a, name))
        if keep and keep.lower() != a.lower():
            raise ValueError("District %s: %r's block holds two county addresses" % (n, name))
        keep = a
    return keep


def parse(pages):
    page = pages[URLS[0]]
    end = page.find("</main>")
    if end < 0:
        raise ValueError("no </main> on the commission page")
    size = re.search(r"made up of (\d+) members representing (\d+) county districts", txt(page[:end]))
    if not size or (int(size.group(1)), int(size.group(2))) != (sum(SEATS.values()), len(SEATS)):
        raise ValueError("the page no longer says 16 members from 7 districts: %r"
                         % (size.group(0) if size else None))
    heads = [h for h in HEAD_RE.finditer(page, 0, end) if SECTION_RE.match(txt(h.group(1)))]
    if not heads:
        raise ValueError("no 'Nth District Commissioners Serving ...' headings")
    if PERSON_RE.search(page, 0, heads[0].start()):
        raise ValueError("a person block sits before the first district heading")
    districts = {}
    for k, h in enumerate(heads):
        n = SECTION_RE.match(txt(h.group(1))).group(1)
        if district_number(txt(h.group(1))) != int(n):
            raise ValueError("heading %r read two ways" % txt(h.group(1)))
        if n in districts:
            raise ValueError("District %s has two headings" % n)
        stop = heads[k + 1].start() if k + 1 < len(heads) else end
        seats = []
        for b in PERSON_RE.split(page[h.end():stop])[1:]:
            b = b.split("fusion-layout-column", 1)[0]
            m = NAME_RE.search(b)
            if not m:
                raise ValueError("District %s: a person block without a name and title" % n)
            name, title = txt(m.group(1)), txt(m.group(2))
            t = TITLE_RE.match(title)
            if not t or t.group(1) != n:
                raise ValueError("District %s section holds %r titled %r" % (n, name, title))
            if re.search(r"\bvacan", name, re.I) or not re.fullmatch(r"[A-Z][A-Za-z.'’ -]+", name):
                raise ValueError("District %s: %r does not look like a name" % (n, name))
            content = CONTENT_RE.search(b)
            seats.append(member(name, email=_email(n, name, b),
                                phones=read_phones(content.group(1)) if content else None))
        if len(seats) != SEATS.get(n):
            raise ValueError("District %s section has %d seat blocks, the county elects %s"
                             % (n, len(seats), SEATS.get(n)))
        districts[n] = seats
    return {"districts": districts, "atLarge": []}
