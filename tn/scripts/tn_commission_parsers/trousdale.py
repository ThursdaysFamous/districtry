"""Trousdale County commissioners, from the county's own commission page.

Trousdale is the Hartsville/Trousdale County metropolitan government, and its
legislative body is the Hartsville/Trousdale County Commission: 20
commissioners, two from each of 10 districts (the page's own "District Map
2020" links name Districts 1 to 10).

The page (trousdalecountytn.gov, a Revize staff directory) shows two groups of
cards. The first, "Mayor and Commission Chair", is the Mayor, the Chair and
the Chair Pro Tempore; the Mayor is not a commission seat, and the other two
reappear in the second group, so nothing is read from the first. The second,
headed "Comissioners" (the page's spelling), is one card per member: the
card's position line is "Nth District" (with "Commission Chair" or "Pro
Tempore" after it on two cards), then the name, then either "Beginning Term:
September 1, 2026" or a "Terms Served" list. A member's district is the
district on their own card; nothing is read from order. Every card must name
a district, every district 1..10 must hold two cards, and a card whose name
does not look like a name raises.

Each card's e-mail, in its contact block, is Cloudflare-obfuscated; it is
decoded and kept only on trousdalecountytn.gov and only when it carries the
member's surname. A card is bounded by the next card's opening tag, never by
the page's HTML comments, which the scraper removes before parsing; only the
first position line, name and contact block after the opening are read, so
the page footer's general address that follows the last card is not. Steve
Whittaker's card has no e-mail. No phone is printed on any card.

Currency, checked 2026-10-13. On 2026-10-11 this page still listed the
2022-2026 commission (Mark Presley, David Nollner, Landon Gulley, Jerry Ford,
Lesley Overman, Will Dennis, Brian Crook, David Thomas and Tommy Belcher among
them). By 2026-10-13 it had been rewritten for the new term: its photographs
carry a 12 October 2026 version stamp, eight cards read "Beginning Term:
September 1, 2026", and every returning member's "Terms Served" list ends
"September 1, 2026-". The commission's own agenda for its 28 September 2026
meeting (trousdalecountytn.gov, "20260928 September Agenda.pdf") prints the
2026-2030 commission on its masthead, and its 20 names are this page's 20
("Lacie Jones" there, "Lacey Jones" here; the page's spelling is kept). That
agenda's packet, read 2026-10-13, carries the 24 August minutes, whose item 14,
"Administration of Oath of the 2026-2030 County Commissioners", reads "All
returning commissioners and newly elected in attendance, were sworn in to
begin their term beginning Sept. 1, 2026." The minutes do not list who was
sworn.

What that does NOT establish, stated as for Claiborne: no August 2026 results
are published on a government host here (the election commission's own site
posted its November notices and sample ballot and no August results when read
on 2026-10-11, and on 2026-10-13 its robots.txt reset the connection, so it
was not read again; the state's results site refuses this project), so the district each member sits
for rests on this page. For the eleven returning members it agrees with the
2022 page in every case but one, and that one the page explains itself: Alan
Carman's card is under the 10th District and reads "September 1, 2022-2026
(District 6)". The nine new members' districts (Dies and Johnson 1, Enoch 2,
Jones 3, Barnes and Farley 5, Green 6, Fergusson 8, Langford 9; Fergusson
served 2006-2022 and returns) rest on the page alone.

The page names a Commission Chair (Lonnie Taylor) and a Chair Pro Tempore
(Terry "Bubba" Gregory), and the 28 September agenda lists "Election of
Officers" as business. Nothing read shows how that election went, so neither
role is recorded."""
import re
from ._common import mailtos, member, txt, district_number

COUNTY = "Trousdale"; FIPS = "169"
DOMAINS = ("trousdalecountytn.gov",)
URLS = ["https://trousdalecountytn.gov/government/local_government/county_commission.php"]
SEATS = {str(i): 2 for i in range(1, 11)}
AT_LARGE = 0

GROUP = '>Comissioners</h2>'
CARD_START = '<div class="rz-element rz-staff-directory-card-wrap"'
CONTACT = re.compile(r'class="staff-contact">(.*?)</div>', re.S)
POSITION = re.compile(r'class="staff-position[^"]*">\s*<p[^>]*>(.*?)</p>', re.S)
NAME_P = re.compile(r'class="staff-name">\s*<p[^>]*>(.*?)</p>', re.S)
POSITION_TEXT = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District(?: (?:Commission Chair|Pro Tempore))?$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’\" -]+$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _surname(name):
    words = [w for w in name.split() if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def _email(name, card):
    for a in mailtos(card):
        dom = a.rsplit("@", 1)[-1].lower() if "@" in a else ""
        if not any(dom == d or dom.endswith("." + d) for d in DOMAINS):
            continue
        if _surname(name) in a.split("@", 1)[0].lower():
            return a
        raise ValueError("county address %r in %r's card does not carry the surname" % (a, name))
    return None


def parse(pages):
    page = pages[URLS[0]]
    at = page.find(GROUP)
    if at < 0 or page.find(GROUP, at + 1) >= 0:
        raise ValueError("the page does not carry exactly one 'Comissioners' group")
    districts = {}
    cards = page[at:].split(CARD_START)[1:]
    if len(cards) != sum(SEATS.values()):
        raise ValueError("the Comissioners group holds %d cards, the county elects %d"
                         % (len(cards), sum(SEATS.values())))
    for card in cards:
        pos, nm, contact = POSITION.search(card), NAME_P.search(card), CONTACT.search(card)
        if not pos or not nm or not contact:
            raise ValueError("a card without a position line, a name or a contact block")
        label, name = txt(pos.group(1)), txt(nm.group(1))
        m = POSITION_TEXT.match(label)
        if not m or district_number(label) != int(m.group(1)):
            raise ValueError("card position %r is not 'Nth District'" % label)
        if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
            raise ValueError("District %s: %r does not look like a name" % (m.group(1), name))
        districts.setdefault(m.group(1), []).append(member(name, email=_email(name, contact.group(1))))
    if set(districts) != set(SEATS):
        raise ValueError("the cards name districts %s, not 1..10" % sorted(districts, key=int))
    for d, ms in districts.items():
        if len(ms) != SEATS[d]:
            raise ValueError("District %s holds %d cards, the county elects %d" % (d, len(ms), SEATS[d]))
    return {"districts": districts, "atLarge": []}
