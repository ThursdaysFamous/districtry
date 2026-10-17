"""Claiborne County elects 21 commissioners from 9 districts, unevenly: three
in Districts 1, 2, 3, 6 and 7, two in Districts 4 and 8, and one in Districts
5 and 9 (the page says "21 members from 9 districts"; the County Clerk's
roll call by district in the minutes of 17 August 2026 seats the outgoing body
in exactly that pattern). No seat is called by a letter or number, so no seat
is recorded.

The commission page (WordPress) has an <h3> "COUNTY COMMISSIONERS AND
DISTRICTS:" followed by a bold paragraph "DISTRICT N" for each district (the
District 9 one is split over two lines in the HTML) and then one two-column
block per member: the first column holds the member's name on the first line
of a paragraph, then that member's address and phone, then a link "Email
<Name>"; the second column reads "Term ends August 2030". Each member is paired
with the "DISTRICT N" heading of the section the block sits in; nothing is
read from order. Every block must carry a name, exactly one e-mail link and a
"Term ends" line, and anything else between the headings raises.

Names are printed in capitals ("TAMMY CHEEK", "KELLY "ERIC" JONES", "SHERRY
McCREARY") and are title-cased here: each word's first letter kept capital
and the rest lowered, a single-letter initial left as is, "Mc" kept with the
next letter capital (McCreary), and a quoted nickname kept in its quotes
("Kelly "Eric" Jones"). The link text under each name ("Email Sherry
McCreary", "Email Eric Jones") must end in the same surname, so a block
whose name and link disagree raises.

E-mail: each member's link is a per-member county address
(first.last@claibornecountytn.gov) and is recorded only when it is on that
domain and its local part carries the member's surname.

PRIVACY: every block prints the member's home street address or post office
box, town and ZIP and a phone (Mitchell Cosby's adds a second one marked
"(c)"). The phones are recorded as printed, the "(c)" written out as "cell" in
front of its number, under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is; only
telephone-shaped numbers are read from a block, never its address, town or
ZIP. One block prints the area code (968), which is not in use; it is kept as
printed, since nothing here can say which digits are wrong. The commission
office's address, phone and fax at the top of the page belong to no member:
the address is not read and the two numbers are OFFICE_LINES, which never
land on a member.

Roles: the page's header still reads "Claiborne County Commission Chairman:
Mike Campbell", but Mike Campbell is not on this roster (he was a District 3
member of the previous body and, per the 17 August 2026 minutes, was then
serving as interim County Mayor), and the agenda for 21 September 2026 lists
"Appointment of Chairman/Vice-Chairman". That line is stale and no role is
recorded.

Currency: NOT checked against results. No results of the 6 August 2026
election were found on a county host: the county's Election Commission page
(claibornecountytn.gov/countyoffices/county-officials/election-commission/)
links only the August 2022 results, and a search of the site's media library
for "result" and "election" found no 2026 results; the state's results site
answers this project HTTP 403 and was not tried. Evidence used, all on
claibornecountytn.gov and read 2026-10-11: (1) this page, on which every one of
the 21 members is marked "Term ends August 2030", i.e. a roster of the term
that began 1 September 2026; (2) the September 2026 commission packet
(wp-content/uploads/2026/01/SEPTEMBER-COURT-PACKET-V3.pdf, scanned, read as
images), whose agenda for 21 September 2026 names Epperson, Russell,
Jenkins, Brooks, McCreary and Mason as sponsors (seated after 1 September,
but by name only, not by district); (3) the same packet's minutes of the
outgoing commission's 17 August 2026 meeting, whose roll call by district
already seats in the same districts the twelve members who continue (D2
Barker, Epperson, Poore; D3 Crawford; D4 Mullins, Rowe; D5 Cosby; D6
Brooks, Mason; D7 Brogan, Jones, McCreary); and (4) Resolution 2026-093 in
those minutes, which records that the August 2026 District 3 race tied at 427
votes between Robert (Bob) Brooks and Travis Lester, that Brooks conceded,
and declares Travis Lester the winner for District 3. What this does NOT
establish: the districts of the eight other members new this term (D1 Cheek,
Fultz, King; D3 Coffey; D6 Richard Smith; D8 Evans, Russell; D9 Jenkins) rest
on this page alone."""
import re
from ._common import txt, mailtos, member, district_number, read_phones

COUNTY = "Claiborne"; FIPS = "025"
DOMAINS = ("claibornecountytn.gov",)
URLS = ["https://claibornecountytn.gov/countyoffices/county-commission"]
SEATS = {"1": 3, "2": 3, "3": 3, "4": 2, "5": 1, "6": 3, "7": 3, "8": 2, "9": 1}
AT_LARGE = 0
# The commission office's phone and fax, printed at the top of the page.
OFFICE_LINES = ("423-626-5236", "423-626-1661")

START = "COUNTY COMMISSIONERS AND DISTRICTS"
HEAD_RE = re.compile(r"<p\b[^>]*>\s*<strong>\s*DISTRICT\s+(\d{1,2})\s*</strong>\s*</p>", re.I)
BLOCK_RE = re.compile(r'<div class="wp-block-columns\b')
TERM_RE = re.compile(r"\bTerm ends [A-Z][a-z]+ \d{4}\b")
SUFFIX = {"JR", "SR", "II", "III", "IV"}


def title_case(caps):
    """'KELLY “ERIC” JONES' -> 'Kelly “Eric” Jones';
    'SHERRY McCREARY' -> 'Sherry McCreary'."""
    out = []
    for word in caps.split():
        parts = []
        for part in word.split("-"):
            m = re.fullmatch(r"([^A-Za-z]*)([A-Za-z.']*)([^A-Za-z]*)", part)
            if not m:
                raise ValueError("cannot title-case %r in %r" % (part, caps))
            lead, core, trail = m.groups()
            letters = core.replace(".", "").replace("'", "")
            if not letters:
                parts.append(part)
                continue
            mc = re.fullmatch(r"M[Cc]([A-Z]{2,})", core)
            if mc:
                core = "Mc" + mc.group(1).capitalize()
            elif any(c.islower() for c in core):
                if not re.fullmatch(r"[A-Z][a-z.']+", core):
                    raise ValueError("unexpected mixed case %r in %r" % (core, caps))
            elif len(letters) == 1 or letters in SUFFIX - {"JR", "SR"}:
                pass                            # an initial, or II/III/IV
            elif re.fullmatch(r"O'[A-Z]+", core):
                core = "O'" + core[2:].capitalize()
            else:
                core = core.capitalize()
            parts.append(lead + core + trail)
        out.append("-".join(parts))
    return " ".join(out)


def surname(name):
    words = [w for w in re.split(r"[\s,]+", re.sub(r"[“\"][^”\"]*[”\"]", " ", name)) if w]
    while words and words[-1].upper().strip(".") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def read_block(d, blk):
    paras = re.findall(r"<p\b[^>]*>(.*?)</p>", blk, re.S)
    if not paras:
        raise ValueError("District %s: a member block with no paragraph" % d)
    first = re.split(r"<br\s*/?>", paras[0], flags=re.I)[0]
    caps = txt(first)
    if not re.fullmatch(r"[A-Z][A-Za-z.'‘’“”\" -]+", caps):
        raise ValueError("District %s: %r does not look like a name" % (d, caps))
    if re.search(r"\bvacan", caps, re.I):
        raise ValueError("District %s: a block reads %r; check what the county says" % (d, caps))
    name = title_case(caps)
    terms = TERM_RE.findall(txt(blk))
    if len(terms) != 1:
        raise ValueError("District %s: %r's block has %d 'Term ends' lines" % (d, name, len(terms)))
    links = re.findall(r'<a\b[^>]*href="mailto:[^"]*"[^>]*>(.*?)</a>', blk, re.S)
    addrs = mailtos(blk)
    if len(links) != 1 or len(addrs) != 1:
        raise ValueError("District %s: %r's block has %d e-mail links" % (d, name, len(links)))
    label = txt(links[0])
    if not label.startswith("Email ") or surname(label[6:]) != surname(name):
        raise ValueError("District %s: link %r does not match name %r" % (d, label, name))
    addr = addrs[0]
    local, _, dom = addr.lower().partition("@")
    email = None
    if any(dom == x or dom.endswith("." + x) for x in DOMAINS):
        if surname(name) not in re.sub(r"[^a-z]", "", local):
            raise ValueError("District %s: county address %r is not %r's" % (d, addr, name))
        email = addr
    return member(name, email=email, phones=read_phones(blk)), terms[0]


def parse(pages):
    page = pages[URLS[0]]
    s = page.find(START)
    e = page.find("</article>", s)
    if s < 0 or e < 0:
        raise ValueError("the commissioners section or its end is missing")
    section = page[s:e]
    pieces = HEAD_RE.split(section)
    if BLOCK_RE.search(pieces[0]) or mailtos(pieces[0]):
        raise ValueError("a member block sits before the first DISTRICT heading")
    districts, terms = {}, set()
    for n, body in zip(pieces[1::2], pieces[2::2]):
        if district_number("District " + n) != int(n):
            raise ValueError("heading DISTRICT %s" % n)
        if n in districts:
            raise ValueError("District %s has two headings" % n)
        blocks = BLOCK_RE.split(body)
        if txt(blocks[0]):
            raise ValueError("District %s: text before the first member: %r" % (n, txt(blocks[0])[:80]))
        found = []
        for blk in blocks[1:]:
            rec, term = read_block(n, blk)
            found.append(rec)
            terms.add(term)
        if not found:
            raise ValueError("District %s heading has no members under it" % n)
        districts[n] = found
    if len(terms) != 1:
        raise ValueError("members' term lines differ: %s" % sorted(terms))
    return {"districts": districts, "atLarge": []}
