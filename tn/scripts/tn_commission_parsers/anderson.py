"""Anderson County elects 16 commissioners, two from each of 8 districts ("16
commissioners, 2 from each of the 8 commission districts", the page says; the
ballot was "Vote for Two (2)" in every district and names no seat or
position, so no seat is recorded).

The county's commission page (WordPress, Avada "fusion" layout) gives every
district an <h2> reading "Nth District Commissioners Serving <communities>"
with a link to that district's map, followed by one `fusion-person` block per
seat: a `person-name` span with the name and a `person-title` span reading
"County Commissioner, Nth District", then the member's contact lines. The
page is cut at those <h2> headings and every block is read from its own
title; the title's district must equal the heading of the section the block
sits in, so a block that drifted under the wrong heading raises, and nothing
is read from order. Each section must hold exactly the seats the county
elects there.

District 8's second block reads "VACANT SEAT" over "County Commissioner, 8th
District", and is recorded vacant. The county explains it: the Regular Agenda
of the Board of Commissioners for 21 September 2026 (andersoncountytn.gov,
"Regular-Agenda-Docs-9.21.26-Compressed.pdf", item 7, Letter of Notice) says
"Elizabeth Henry will not take her seat on the Board of Anderson County
Commission as a representative of the 8th District and will not take the
Oath of Office for this position."

PRIVACY: the member blocks carry a street address, town and ZIP (13 of the
15), a "Phone:" line (all 15) and in five cases a personal e-mail (gmail,
ymail, comcast, msn). The phone line is recorded as the page prints it, under
Adam's ruling of 2026-10-17 that a number a government publishes beside an
official ships whosever line it is; only the block's "Phone:" line is read,
never the address lines, and the commission office's own number, printed
separately above the list, is not a member's. Ebony Capshaw's block prints
the commission office's mailing address, which is not hers and is not read
either. A member's e-mail is the address the block prints, whatever its
domain, since Adam chose on 2026-10-17 to show a personal address a government
page prints beside an official ("E-mails too"); until that day only a county
address was kept. Where a block prints a county address it is the one kept,
and its local part must carry the member's surname (Tracy Wandell's block
holds both an msn.com address and twandell@; the county one is kept). A county
address in a member's block that does not carry the surname raises rather than
being attached to the wrong person. The commission office's own address (Amy
Emert, aemert@) sits outside every block and is never read.

Currency: checked 2026-10-11 against the Anderson County Election
Commission's own "Cumulative Results Report" for the 6 August 2026 State
Primary and State and County General (acelection.com, "after-write-ins"
cumulative report run 8/6/2026 10:37 PM, 30 of 30 polling places, marked
Unofficial Results; the commission's past-results page offers no later
report). In every district the two names on this page are the two winners,
with ballot spellings differing only by initials and short forms (Tracy L
Wandell, Michael Y. Foster, J. Shain Vowell, Steve Verran, Sharon Bourgeois
Capshaw). District 7 was close (Steve Verran 596, Sabra Beauchamp 593); the
Operations Committee minutes of 14 September 2026, printed in the same
21 September agenda packet, list Commissioner Stephen Verran present. In
District 8 Jawrell Cook (749) and Elizabeth "Liz" Henry (749) won; Henry's
seat is the vacancy above. The page names no chair (the same packet addresses
Robert McKamey as Chairman), so no role is recorded."""
import re
from ._common import txt, mailtos, member_email, district_number, member, vacant, read_phones

COUNTY = "Anderson"; FIPS = "001"
DOMAINS = ("andersoncountytn.gov",)
URLS = ["https://andersoncountytn.gov/county-commission/"]
# The commission office's own line, printed above the list (a member's record
# never carries it).
OFFICE_LINES = ("865-463-6866",)
SEATS = {str(i): 2 for i in range(1, 9)}
AT_LARGE = 0

HEAD = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
SECTION = re.compile(r"^(\d{1,2})(?:st|nd|rd|th) District Commissioners Serving\b")
PERSON = re.compile(r'<div class="fusion-person\b')
NAME = re.compile(r'<span class="person-name">(.*?)</span>\s*<span class="person-title">(.*?)</span>', re.S)
TITLE_RE = re.compile(r"^County Commissioner, (\d{1,2})(?:st|nd|rd|th) District$")
CONTENT = re.compile(r'<div class="person-content\b[^>]*>(.*?)</div>', re.S)
PHONE_LINE = re.compile(r"^Phone\s*:", re.I)
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surnames(name):
    """'Sharon Bourgeois-Capshaw' -> {'bourgeoiscapshaw', 'bourgeois', 'capshaw'}."""
    words = [w for w in re.split(r"\s+", re.sub(r'"[^"]*"', " ", name)) if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    last = words[-1].lower() if words else ""
    parts = {re.sub(r"[^a-z]", "", p) for p in [last] + last.split("-")}
    return {p for p in parts if len(p) > 2}


def _email(name, block):
    addrs = mailtos(block)
    for a in addrs:
        if not _on_domain(a):
            continue
        local = a.split("@", 1)[0].lower()
        if any(s in local for s in _surnames(name)):
            return a
        raise ValueError("county address %r in %r's block does not carry the surname" % (a, name))
    return member_email(addrs, DOMAINS)


def _phones(n, name, block):
    """The block's "Phone:" line, and nothing else in the block."""
    content = CONTENT.search(block)
    segs = re.split(r"<br\s*/?>", content.group(1), flags=re.I) if content else []
    found = [x for x in segs if PHONE_LINE.match(txt(x))]
    if len(found) > 1:
        raise ValueError("District %s: %r's block holds %d phone lines" % (n, name, len(found)))
    return read_phones(found[0], strict=True) if found else []


def parse(pages):
    page = pages[URLS[0]]
    end = page.find("</main>")
    if end < 0:
        raise ValueError("no </main> on the commission page")
    heads = [h for h in HEAD.finditer(page, 0, end) if SECTION.match(txt(h.group(1)))]
    if not heads:
        raise ValueError("no 'Nth District Commissioners Serving ...' headings")
    if PERSON.search(page, 0, heads[0].start()):
        raise ValueError("a person block sits before the first district heading")
    districts = {}
    for k, h in enumerate(heads):
        n = SECTION.match(txt(h.group(1))).group(1)
        if district_number(txt(h.group(1))) != int(n):
            raise ValueError("heading %r read two ways" % txt(h.group(1)))
        if n in districts:
            raise ValueError("District %s has two headings" % n)
        stop = heads[k + 1].start() if k + 1 < len(heads) else end
        blocks = PERSON.split(page[h.end():stop])[1:]
        seats = []
        for b in blocks:
            # The block ends where the next layout column begins.
            b = b.split("fusion-layout-column", 1)[0]
            m = NAME.search(b)
            if not m:
                raise ValueError("District %s: a person block without a name and title" % n)
            name, title = txt(m.group(1)), txt(m.group(2))
            t = TITLE_RE.match(title)
            if not t or t.group(1) != n:
                raise ValueError("District %s section holds %r titled %r" % (n, name, title))
            if re.fullmatch(r"vacant(?: seat)?", name, re.I):
                if mailtos(b):
                    raise ValueError("District %s: a vacant seat carries an e-mail" % n)
                seats.append(vacant())
                continue
            if re.search(r"\bvacan", name, re.I) or not re.fullmatch(r"[A-Z][A-Za-z.'’ -]+", name):
                raise ValueError("District %s: %r does not look like a name" % (n, name))
            seats.append(member(name, email=_email(name, b), phones=_phones(n, name, b)))
        if len(seats) != SEATS.get(n):
            raise ValueError("District %s section has %d seat blocks, the county elects %s"
                             % (n, len(seats), SEATS.get(n)))
        districts[n] = seats
    return {"districts": districts, "atLarge": []}
