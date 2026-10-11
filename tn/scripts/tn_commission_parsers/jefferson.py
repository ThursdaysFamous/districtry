"""Jefferson County elects 21 commissioners from 10 districts: two in every
district except District 3 (White Pine), which elects three. The page's own
"About" text states that rule, and the ballot calls no seat by a letter or a
number, so no seat is recorded.

The commission page (WordPress/Divi) has a "County Commissioners" section in
which each district is a row opening with an <h3> "1st District" .. "10th
District", followed by one column per member. A member's column holds the
name (in an <h4> on some, a <p> on others), sometimes " - <office>" after the
name, sometimes a further title line, and then the member's seat mailbox
printed as two lines, "JCcommNN" and "@jeffersoncountytn.gov". Each member is
paired with the <h3> heading of the row they sit in; nothing is read from
order. The rows' own HTML ids are NOT read: the 10th District's row carries
the id "3rd-district". The photos' alt texts are not read either (Brett
Kilgore's photo is labelled with another person's name). A column that holds
anything but a name, an optional office or title and one mailbox raises.

E-mail: each member's mailbox is a per-seat county address
(JCcomm01@jeffersoncountytn.gov ..), joined from the two printed lines and
recorded as printed. That it is the member's own commission address is
checked against the page's own "Commission Chairman" box, which names "Jimmy
Carmichael, 9th District" and links mailto:JCComm18@jeffersoncountytn.gov,
the mailbox printed under his name in the 9th District row; if the box and
the row ever disagree the parse raises. The page prints no member phone and
no address; the only phone and street address on it are the Mayor's Office's
(214 W. Main Street, 865-397-3800), which belong to no member and are not read.

Roles: "Chair" (Jimmy Carmichael), "Vice Chair" (Katy Hufaker) and
"Parliamentarian" (Aaron Loy) are recorded as printed. Brett Kilgore's second
line "Chaplin" (sic) is a title, not a commission office, and is dropped.

Names are kept as the page prints them. "Katy Hufaker" is printed with one
"f"; the ballot spells her "Katy "Fox" Huffaker" and the page's own photo
file is "Katy-Huffaker", so the page's spelling is most likely a typo, but it
is the county's and is kept.

Currency: checked 2026-10-11 against the Jefferson County Election
Commission's "official 2026 State Primary and County General Election
results" (jeffersoncountytn.gov/wp-content/uploads/2026/08/official-results.pdf,
linked from the commission's own page; a scanned PDF, footer dated August 17,
2026, read as images). All 21 seats were on the 6 August 2026 county general
ballot, and the 21 names here are the 21 winners in the same districts: D1
Huffaker, Leja; D2 Moore 401, Knierim 369 (Bryant 125); D3 Snodgrass,
Reed, Leckie; D4 Byrd 258, Lance 252 (Jennings 225); D5 Underwood,
Solomon; D6 Bruner 406, Parker 322 (Blevins 227); D7 Bales, Loy; D8 Henry
461, Coleman 444 (McSmith 213); D9 Carmichael, Walker; D10 Kilgore, Reed.
Ballot spellings differ only by initials and nicknames (Craig J. Knierim,
James "Jim" Lance, W D Henry, James E. (Jimmy) Carmichael, A. J. Walker,
Marcus T. Reed)."""
import re
from ._common import lines, district_number, member, county_email, ROLE

COUNTY = "Jefferson"; FIPS = "089"
DOMAINS = ("jeffersoncountytn.gov",)
URLS = ["https://jeffersoncountytn.gov/county-commission/"]
SEATS = {"1": 2, "2": 2, "3": 3, "4": 2, "5": 2, "6": 2, "7": 2, "8": 2,
         "9": 2, "10": 2}
AT_LARGE = 0

HEADING = re.compile(r"<h3>\s*(.*?)\s*</h3>", re.S)
COLUMN = re.compile(r'<div class="et_pb_column\b[^>]*>')
LABEL = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District$")
LOCAL = re.compile(r"^JCcomm\d{2}$", re.I)
AT_DOMAIN = "@jeffersoncountytn.gov"
NAME = re.compile(r"^[A-Z][A-Za-z.'’() -]+$")
TITLES = {"chaplin", "chaplain"}          # titles that are not commission offices


def split_name(line):
    """'Katy Hufaker – Vice Chair' -> ('Katy Hufaker', 'Vice Chair')."""
    parts = re.split(r"\s+[-–—]\s+", line)
    if len(parts) > 2:
        raise ValueError("%r: more than one dash" % line)
    name, role = parts[0], (parts[1] if len(parts) == 2 else None)
    if role is not None and not ROLE.fullmatch(role):
        raise ValueError("%r: %r is not a commission office" % (line, role))
    if not NAME.match(name):
        raise ValueError("%r does not look like a name" % line)
    return name, role


def read_column(d, ls):
    """One member column -> member, or None for an empty column."""
    ls = [x for x in ls if x]
    if not ls:
        return None
    boxes = [i for i, x in enumerate(ls) if LOCAL.match(x)]
    if len(boxes) != 1 or boxes[0] + 2 != len(ls) or ls[-1].lower() != AT_DOMAIN:
        raise ValueError("District %s: a column is not 'name, mailbox': %r" % (d, ls))
    head = ls[:boxes[0]]
    if not head:
        raise ValueError("District %s: a mailbox with no name above it: %r" % (d, ls))
    name, role = split_name(head[0])
    for extra in head[1:]:
        if ROLE.fullmatch(extra) and not role:
            role = extra
        elif extra.lower() not in TITLES:
            raise ValueError("District %s: unknown line %r under %r" % (d, extra, name))
    email = county_email([ls[boxes[0]] + ls[-1]], DOMAINS)
    return member(name, role=role, email=email)


def parse(pages):
    page = pages[URLS[0]]
    start = page.find("<h2>County Commissioners</h2>")
    end = page.find('id="contact-commission"', start)
    if start < 0 or end < 0:
        raise ValueError("the County Commissioners section or the contact box is missing")
    end = page.rfind("<", start, end)       # the start of the contact box's own tag
    section = page[start:end]
    pieces = HEADING.split(section)
    if any(LOCAL.match(x) for x in lines(pieces[0])):
        raise ValueError("a mailbox sits before the first District heading")
    districts = {}
    for label, body in zip(pieces[1::2], pieces[2::2]):
        m = LABEL.match(label)
        if not m or district_number(label) != int(m.group(1)):
            raise ValueError("an <h3> in the section is not 'Nth District': %r" % label)
        d = m.group(1)
        if d in districts:
            raise ValueError("District %s has two headings" % d)
        found = []
        for col in COLUMN.split(body):
            rec = read_column(d, lines(col))
            if rec:
                found.append(rec)
        if not found:
            raise ValueError("District %s heading has no members under it" % d)
        districts[d] = found

    # The page's own Commission Chairman box must agree with the rows.
    box = page[end:end + 4000]
    who = re.search(r"<p>([^<,]+),\s*<em>\s*(\d{1,2})(?:st|nd|rd|th) District\s*</em></p>", box)
    mail = re.search(r'mailto:([^"\s?]+)', box)
    if not who or not mail:
        raise ValueError("the Commission Chairman box no longer names a chairman and a mailbox")
    chair = [r for r in districts.get(who.group(2), []) if r.get("role") == "Chair"]
    if (len(chair) != 1 or chair[0]["name"] != who.group(1).strip()
            or (chair[0].get("email") or "").lower() != mail.group(1).lower()):
        raise ValueError("the Commission Chairman box (%s, District %s, %s) disagrees with the rows"
                         % (who.group(1), who.group(2), mail.group(1)))
    return {"districts": districts, "atLarge": []}
