"""Fayette County elects 19 commissioners from 14 districts: two in Districts
4, 6, 8, 9 and 10 and one in each of the other nine. The ballot calls the two
seats of a district "Pos 1" and "Pos 2"; the page does not, so no seat is
recorded.

The county's Board of County Commissioners page lists, inside its article,
one <h2> per district reading "District N: <place>" (for example "District 1:
West Somerville"), and under it one <p> per member: the name in <strong>, the
line "Commissioner", a phone line and an e-mail address written as plain
text. A member is paired with the district heading of the section their <p>
sits in, and every <p> in a section must have "Commissioner" as its second
line, so nothing is read from page order. A member block before the first
district heading, a heading that is not "District N", or a block whose second
line is not "Commissioner" raises.

PRIVACY: every phone on the page is labelled Cell or Home (or unlabelled
beside one that is). They are recorded as printed, each with the page's own
label in front of it ("cell 901-..."), under Adam's ruling of 2026-10-17 that
a number a government publishes beside an official ships whosever line it is.
Claude Oglesby's line gives a home number that is also printed as his fax; one
line cannot be both, so that number is left off and his cell kept. The page
prints no street address. Ten members print a personal or business e-mail
address (aol, comcast, gmail, att, bellsouth, a family business's domain) and
none of those is kept. An e-mail is recorded only on fayettetn.us and only
when its local part contains the member's surname and starts with the initial
of their given name or of the nickname the page prints ("Betsy" Rice is
brice@); an address that two members' names would both fit is kept for
neither. Nine such addresses are on the page and all nine are kept.

Currency: checked 2026-10-11 against the Fayette County Election
Commission's Election Summary Report for the 6 August 2026 State Primary and
County General (printed 8/6/2026 9:05 PM, election-night totals; whether it is
the certified canvass is not established), the "FINAL GRAND TOTALS" PDF
(fayettetn.us/wp-content/uploads/2026/08/Totals-compressed.pdf) linked from
the county's own "Election Aug 6, 2026" results page, read as images because
its text layer is a noisy OCR. Each race was "County Commission Dist N Pos k",
vote for 1, and the winner of every race is the member listed under that
district: District 2 was contested (Marandy Wilkerson 276, Dave Rhea 239), as
were 4 Pos 1, 9 Pos 1, 9 Pos 2 and 12. The ballot writes Elizabeth (Betsy)
Rice, Kevin J. Powers, Steve R Reeves, Claude D. Oglesby, Jr, Chelsea Kivelle
(the page: "Chelsey"), Thomas Wiley Day, Glen A. Morman, Betty Morrison Salmon
and Terrye L. Canady; each is the same person as the page's entry."""
import re
from ._common import txt, mailtos, member, district_number, read_phones

COUNTY = "Fayette"; FIPS = "047"
DOMAINS = ("fayettetn.us",)
URLS = ["https://fayettetn.us/county-boards-councils/county-commission/"]
SEATS = {"1": 1, "2": 1, "3": 1, "4": 2, "5": 1, "6": 2, "7": 1, "8": 2, "9": 2,
         "10": 2, "11": 1, "12": 1, "13": 1, "14": 1}
AT_LARGE = 0

HEADING = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NAME = re.compile(r"^[A-Z][A-Za-z.'’“”\" -]+$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _surname(name):
    words = [w for w in re.split(r"[\s,]+", re.sub(r"[\"“”(][^\"“”)]*[\"“”)]", " ", name)) if w]
    while words and words[-1].lower().strip(".") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def _initials(name):
    """The first letters a county address may open with: the given name's and
    a quoted nickname's ('Elizabeth "Betsy" Rice' -> {'e', 'b'})."""
    out = {re.sub(r"[^a-z]", "", name.lower())[:1]}
    for nick in re.findall(r"[\"“(]([A-Za-z]+)[\"”)]", name):
        out.add(nick[:1].lower())
    return out


def _members(body, d):
    out = []
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S):
        parts = [txt(x) for x in re.split(r"<br\b[^>]*>", p, flags=re.I)]
        parts = [x for x in parts if x]
        if not parts:
            continue
        if len(parts) < 2 or parts[1] != "Commissioner":
            raise ValueError("District %s: a block that is not 'Name / Commissioner': %r" % (d, parts[:3]))
        if not NAME.match(parts[0]):
            raise ValueError("District %s: %r does not look like a name" % (d, parts[0]))
        addrs = mailtos(p) + [a for x in parts[2:] for a in EMAIL.findall(x)]
        out.append((parts[0], addrs, read_phones(p)))
    return out


def parse(pages):
    page = pages[URLS[0]]
    s = page.find('<div class="pe-article-content">')
    e = page.find("</article>", s)
    if s < 0 or e < 0:
        raise ValueError("the article content was not found")
    article = page[s:e]
    pieces = HEADING.split(article)
    # pieces = [before-first-heading, h2 text, body, h2 text, body, ...]
    if len(pieces) < 3:
        raise ValueError("no <h2> district heading in the article")
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", pieces[0], re.S):
        if "Commissioner" in [txt(x) for x in re.split(r"<br\b[^>]*>", p, flags=re.I)]:
            raise ValueError("a member block sits before the first district heading")
    found = []
    for head, body in zip(pieces[1::2], pieces[2::2]):
        label = txt(head)
        d = district_number(label)
        if not d or not re.match(r"^District\s+%d\s*:" % d, label):
            raise ValueError("heading %r is not 'District N: place'" % label)
        if any(x[0] == str(d) for x in found):
            raise ValueError("District %d has two headings" % d)
        ms = _members(body, d)
        if not ms:
            raise ValueError("District %d has no member under it" % d)
        found.append((str(d), ms))
    keys = [(_surname(n), i) for _, ms in found for n, _, _ in ms for i in _initials(n)]
    districts = {}
    for d, ms in found:
        for name, addrs, phones in ms:
            sur, inits = _surname(name), _initials(name)
            email = None
            for a in addrs:
                local, dom = a.lower().rsplit("@", 1)
                if dom not in DOMAINS or not sur or sur not in local:
                    continue
                hit = [i for i in inits if local.startswith(i)]
                # Two members with this surname and initial: the address
                # could be either's, so it is nobody's.
                if hit and all(keys.count((sur, i)) == 1 for i in hit):
                    email = a
                    break
            districts.setdefault(d, []).append(member(name, email=email, phones=phones))
    return {"districts": districts, "atLarge": []}
