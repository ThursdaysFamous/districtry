"""Polk County's commission has 10 seats in 4 districts: three in Districts 1
and 3, two in Districts 2 and 4. The page shows nine members and states "One
District 2 commission seat is currently vacant", so District 2 is one member
and one vacancy. No seat letter or number is published, so no seat is
recorded.

The county's Commissioners page (WordPress, rebuilt with inline-styled
blocks in September 2026) gives each district an <h2> "District N" followed
by one card per member: a photo placeholder captioned with the name, the
name, a title line "District N Commissioner", then "Phone:" and "Email:".
The page is cut at the <h2> headings and stops at the first heading that is
not "District N" (the "In Memory" section that follows names a former
member, Commissioner Greg Brooks, District 2, and is never read as a seat).
Each member is found by their own card's title line, whose district must
equal the heading of the section the card sits in; the name is the line
immediately above that title, and nothing is read from order. The vacancy is
read from the section's own notice, "One District N commission seat is
currently vacant" under its label "District N Vacancy:", whose N must be the
section's district; any other text mentioning a vacancy raises.

E-mail: each card's address is Cloudflare-obfuscated and decodes to a
first.last@polkcountytn.gov address; it is recorded where it is on
polkcountytn.gov and its local part carries the member's surname (all nine;
Deborah Anne Davis's reads debbie.davis@, James Mush Davis's james.davis@). An
address on another domain in a member's own card is kept as printed when it
prints no county one, under Adam's ruling of 2026-10-17 that an e-mail address
a government page prints beside an official ships too.

PRIVACY: every card prints a phone, several of them Georgia (706) mobile
numbers, and nothing calls any a county line. Each card's "Phone:" number is
recorded as printed, under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is; it is
read from the text after the card's own title line, up to the next card's
title. The cards print no address. The County Executive's office and the two
non-emergency lines in the page footer are OFFICE_LINES and never land on a
member. The county's own September 2026 commissioner list (below) prints
personal gmail, yahoo, outlook and bellsouth addresses and phones for the
members; it is not read by the parser and nothing from it is recorded.

Currency: NO results of the 6 August 2026 election were found on a
government host. The county site's "Election Commission" menu item points
to its Board of Education page, no election commission site was found, and
the state's results site answers this project HTTP 403 and was not tried.
Fallback evidence, both on the county's own host, read 2026-10-11 from its
Agendas & Minutes page (polkcountytn.gov/agendas-minutes-2/): the agenda of
the Board of County Commissioners' Regular Monthly Meeting of September 17th
2026 (wp-content/uploads/commission-meetings/agendas/agenda-2026-09.pdf, a
scan made September 9, 2026), which opens with "APPOINTMENT OF CHAIRMAN" and
"APPOINTMENT OF VICE CHAIR", names Commissioners Keith Barker and Christy
Hardin, and carries "PROCLAMATION GREG BROOKS"; and that meeting's supporting
document "Commissioner List" (wp-content/uploads/commission-meetings/
supporting-documents/2026-09/commissioner-list.pdf, a scan headed "COUNTY
COMMISSIONER LIST", undated, filed with the September 2026 meeting), which
lists by district exactly the nine people this page lists in the same
districts (as "Debbie Davis" and "Mush Davis") and one name under District
2. What this does NOT establish: the list carries no date or term of its
own, so its post-September date rests on where the county filed it; no
results were compared; and neither document says how many seats District 2
elects, which rests on this page's own vacancy notice. The page names no
chair, so no role is recorded."""
import re
from ._common import (txt, lines, mailtos, district_number, member, vacant, read_phones,
                      other_email)

COUNTY = "Polk"; FIPS = "139"
DOMAINS = ("polkcountytn.gov",)
URLS = ["https://polkcountytn.gov/county-commissioners/"]
SEATS = {"1": 3, "2": 2, "3": 3, "4": 2}
AT_LARGE = 0
# The County Executive's office and the two non-emergency lines, in the footer.
OFFICE_LINES = ("(423) 338-4527", "(423) 338-8215", "(423) 496-3301")

H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
HEAD_RE = re.compile(r"^District\s+(\d{1,2})$")
CARD_TITLE = re.compile(r">\s*District\s+(\d{1,2})\s+Commissioner\s*<")
VACANCY = re.compile(r"\bOne District (\d{1,2}) commission seat is currently vacant\.")
NAME = re.compile(r"^[A-Z][A-Za-z.'’\" -]+$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _surname(name):
    words = [w for w in name.split() if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def _email(name, fragment):
    for a in mailtos(fragment):
        dom = a.rsplit("@", 1)[-1].lower() if "@" in a else ""
        if not any(dom == d or dom.endswith("." + d) for d in DOMAINS):
            continue
        if _surname(name) in a.split("@", 1)[0].lower():
            return a
        raise ValueError("county address %r in %r's card does not carry the surname" % (a, name))
    return other_email(fragment, DOMAINS)


def read_section(d, sec):
    titles = list(CARD_TITLE.finditer(sec))
    seats = []
    for i, t in enumerate(titles):
        if t.group(1) != d:
            raise ValueError("District %s section holds a card titled District %s" % (d, t.group(1)))
        above = lines(sec[titles[i - 1].end() if i else 0:t.start() + 1])
        if not above:
            raise ValueError("District %s: a card title with no name above it" % d)
        name = above[-1]
        if not NAME.match(name) or name in ("Phone:", "Email:") or re.search(r"\bvacan", name, re.I):
            raise ValueError("District %s: %r above a card title does not look like a name" % (d, name))
        after = sec[t.end():titles[i + 1].start() if i + 1 < len(titles) else len(sec)]
        seats.append(member(name, email=_email(name, after), phones=read_phones(after)))
    text = txt(sec)
    vac = VACANCY.findall(text)
    if any(v != d for v in vac):
        raise ValueError("District %s section states a vacancy in District %s" % (d, vac))
    labels = re.findall(r"\bDistrict (\d{1,2}) Vacancy:", text)
    if labels != vac or len(re.findall(r"vacan", text, re.I)) != len(labels) + len(vac):
        raise ValueError("District %s section mentions a vacancy in words this parser does not know: %r"
                         % (d, text[-200:]))
    seats += [vacant() for _ in vac]
    if len(seats) != SEATS.get(d):
        raise ValueError("District %s shows %d seats, the county elects %s" % (d, len(seats), SEATS.get(d)))
    return seats


def parse(pages):
    page = pages[URLS[0]]
    heads = list(H2.finditer(page))
    first = next((k for k, h in enumerate(heads) if HEAD_RE.match(txt(h.group(1)))), None)
    if first is None:
        raise ValueError("no 'District N' headings on the page")
    if CARD_TITLE.search(page, 0, heads[first].start()):
        raise ValueError("a commissioner card sits before the first district heading")
    districts = {}
    for k in range(first, len(heads)):
        label = txt(heads[k].group(1))
        m = HEAD_RE.match(label)
        if not m:
            if label != "In Memory":
                raise ValueError("unexpected heading %r after the districts" % label)
            tail = page[heads[k].end():]
            if CARD_TITLE.search(tail):
                raise ValueError("a commissioner card sits after the district sections")
            break
        d = m.group(1)
        if district_number(label) != int(d):
            raise ValueError("heading %r read two ways" % label)
        if d in districts:
            raise ValueError("District %s has two headings" % d)
        stop = heads[k + 1].start() if k + 1 < len(heads) else len(page)
        districts[d] = read_section(d, page[heads[k].end():stop])
    return {"districts": districts, "atLarge": []}
