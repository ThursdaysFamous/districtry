"""Coffee County elects 18 commissioners, two from each of 9 districts (the
ballot names no seat or position, so no seat is recorded).

The county's commission page (CivicPlus) lists the members under a "Members"
subheading as a grid of widgets: for each member an image widget linking to
the member's own page and, separately, an editor widget whose
`<div class="fr-view">` holds one heading "Name, District N" and one
paragraph with the member's county e-mail as plain text. The name and the
district are read from that one heading, never from the grid's order. An
editor widget whose heading does not read "Name, District N" raises, as does
a widget with more than one heading or e-mail.

The profile link is taken only where an image widget's own link names the
member exactly (`/214/Amanda LeVieux`, the page title CivicPlus put in the
path), so it is matched by name rather than by the grid's position. The link
is written as the county's server answers it: the published path has spaces,
and /222/Missy DeFord redirects to /222/Missy-DeFord (checked 2026-10-11), so
spaces become hyphens.

PRIVACY: the page publishes no phone or address. Each widget's e-mail is on
coffeecountytn.gov and is kept only when its local part carries the member's
surname; Missy DeFord's is pdeford@, which does. The member pages linked as
profileUrl print a phone number with nothing saying it is a county line; they
are not read, and no phone is recorded. The county staff directory
(Directory.aspx?did=36) is not read either.

Currency: checked 2026-10-11 against the Coffee County Election Commission's
"August 6, 2026 Official Results" (coffeecountytn.gov DocumentCenter/View/
7193, a text PDF dated August 20, 2026). In every County Commissioner
District 1-9 the two highest totals are the two names this page lists for
that district. Ballot forms differ only by middle names, initials and a
suffix (Dowe Langford Jones, Amanda Levieux, Laura Cason Nettles, Mark T.
Brothers, Sammy Anderson, III, Terry L. Hershman, Jackie A. Duncan, J. Todd
Malone, Frank C B Watkins). The page's spellings are kept. The page names no
chair, so no role is recorded."""
import re
from ._common import txt, district_number, member

COUNTY = "Coffee"; FIPS = "031"
DOMAINS = ("coffeecountytn.gov",)
URLS = ["https://www.coffeecountytn.gov/213/County-Commission"]
SEATS = {str(i): 2 for i in range(1, 10)}
AT_LARGE = 0
BASE = "https://www.coffeecountytn.gov"

WIDGET = re.compile(r'<div class="fr-view">(.*?)</div>', re.S)
HEADING = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.S)
ENTRY = re.compile(r"^(?P<name>[A-Z][A-Za-z.'’ -]+), District (?P<d>\d{1,2})$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower()
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surname(name):
    words = [w for w in name.replace(",", " ").split() if w]
    while words and words[-1].lower().strip(".") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def parse(pages):
    page = pages[URLS[0]]
    members_at = page.find(">Members</h2>")
    if members_at < 0:
        raise ValueError("no 'Members' subheading on the commission page")
    profiles = {}
    for href, title in re.findall(r'<a href="(/\d+/)([^"/]+)" target="_self"><img\b', page):
        profiles[txt(title)] = BASE + href + "-".join(txt(title).split())
    districts = {}
    for w in WIDGET.finditer(page, members_at):
        body = w.group(1)
        heads = HEADING.findall(body)
        if not heads:
            if txt(body):
                raise ValueError("a text widget under Members with no name heading: %r" % txt(body)[:80])
            continue
        if len(heads) != 1:
            raise ValueError("a member widget with %d headings: %r" % (len(heads), txt(body)[:80]))
        label = txt(heads[0])
        m = ENTRY.match(label)
        if not m or district_number(label) != int(m.group("d")):
            raise ValueError("member heading %r is not 'Name, District N'" % label)
        name, n = m.group("name").strip(), m.group("d")
        if re.search(r"\bvacan", name, re.I):
            raise ValueError("District %s: heading %r; decide how to record a vacancy" % (n, label))
        rest = txt(HEADING.sub(" ", body))
        found = EMAIL.findall(rest)
        if len(found) > 1:
            raise ValueError("%r's widget carries %d e-mails" % (name, len(found)))
        email = None
        if found and _on_domain(found[0]):
            if _surname(name) not in found[0].split("@", 1)[0].lower():
                raise ValueError("county address %r does not carry %r's surname" % (found[0], name))
            email = found[0]
        districts.setdefault(n, []).append(member(name, email=email, profileUrl=profiles.get(name)))
    return {"districts": districts, "atLarge": []}
