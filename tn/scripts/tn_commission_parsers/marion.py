"""Marion County elects 15 commissioners, three from each of 5 districts, in
Seats A, B and C (the ballot runs a separate race for each seat, "County
Commission District N - Seat X"). The seat letter is recorded as the page
prints it.

The county's Leadership page (Squarespace, marioncountytn.net/leadership,
"Meet the Commissioners" on the county site) has a "Commissioners" section in
which every district is one layout row: a text block whose <h3> reads
"District N" (later ones in capitals, "DISTRICT N") over the communities it
covers, then one text block per member, each opening with an <h3>
"COMMISSIONER" and a paragraph "<name><br>Seat X<br><phone>", then the
member's e-mail. The section is read block by block and cut at the district
headings, so every member is paired with the district heading of the row they
sit in and the seat letter printed in their own block; nothing is read from
order. Each district must show Seats A, B and C exactly once, a COMMISSIONER
block before the first district heading raises, and the section ends at the
first heading that is neither.

PRIVACY: thirteen blocks print a phone; nothing calls any a county line (they
are the members' own numbers), so none is recorded. E-mails are recorded only
on marioncountytn.net and only where the address's local part carries the
member's surname (ten members); the gmail and business addresses printed for
Jimmy Cantrell, Linda Mason, Dennis Rollins, Logan Campbell and Chris
Morrison are not recorded, and a county address that does not carry the
surname raises rather than being attached to the wrong person. The Mayor's
office address and telephone above the section are not read.

Names are kept as printed, the nickname in curly quotes included ("Ronnie
“Bo” Burnett"). The page names no chair, so no role is recorded.

Currency: checked 2026-10-11 against the Marion County Election
Commission's "Official Results 8.6.2026 Election" (marionvotes.com,
wp-content/uploads/2026/08/Official%20Results%208.6.2026%20Election.pdf, a
scanned PDF with no text layer, pages footed August 21, 2026, read as
images). Every one of the 15 seats was on the 6 August 2026 county general
ballot as its own race, and the name on this page for each district and seat
is that race's winner: 1A Burkhalter 725 (Stone 387), 1B Smith 577 (Myers
485), 1C Story 469 (Rector 401), 2A Winters unopposed, 2B Keef 612 (Kilgore
610), 2C Cantrell 923, 3A Burnett 1,053, 3B Baker 837 (Franklin 757), 3C
Istanich 834 (Walden 773), 4A Mason, 4B Rollins and 5B Campbell and 5C
Morrison unopposed, 4C Stiefel 703, 5A Higdon 663 (Nunley 453). Ballot
spellings differ only by nicknames and middle names (Joyce (Tuttie) Acuff
Burkhalter, Dennis Denny Rollins, Terry (Turbo) Stiefel, Larry H. Higdon)."""
import re
from ._common import txt, mailtos, district_number, member

COUNTY = "Marion"; FIPS = "115"
DOMAINS = ("marioncountytn.net",)
URLS = ["https://marioncountytn.net/leadership"]
SEATS = {str(i): 3 for i in range(1, 6)}
AT_LARGE = 0

BLOCK = re.compile(r'<div class="sqs-html-content"[^>]*>(.*?)</div>', re.S)
H3 = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.S)
P = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
DIST = re.compile(r"^District\s+(\d{1,2})$", re.I)
SEAT = re.compile(r"^Seat\s+([A-Z])$")
PHONE = re.compile(r"^\(?\d{3}\)?[-. ]?\d{3}[-. ]\d{4}$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’“”\" -]+$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _surname(name):
    words = [w for w in re.split(r"\s+", re.sub(r"[“\"][^”\"]*[”\"]", " ", name)) if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def read_member(d, body):
    paras = [p for p in P.findall(body) if txt(p)]
    if not paras:
        raise ValueError("District %s: a COMMISSIONER block with no text" % d)
    segs = [txt(s) for s in re.split(r"<br\s*/?>", paras[0], flags=re.I)]
    segs = [s for s in segs if s]
    if len(segs) < 2 or not SEAT.match(segs[1]):
        raise ValueError("District %s: block does not open 'name, Seat X': %r" % (d, segs))
    name, seat = segs[0], SEAT.match(segs[1]).group(1)
    if not NAME.match(name) or re.search(r"\bvacan", name, re.I):
        raise ValueError("District %s: %r does not look like a name" % (d, name))
    for extra in segs[2:]:
        if not (PHONE.match(extra) or "@" in extra):
            raise ValueError("District %s: unexpected line %r under %r" % (d, extra, name))
    for p in paras[1:]:
        if "@" not in txt(p):
            raise ValueError("District %s: unexpected paragraph %r under %r" % (d, txt(p), name))
    email = None
    for a in mailtos(body):
        if not _on_domain(a):
            continue
        local = re.sub(r"\d+$", "", a.split("@", 1)[0].lower())
        if _surname(name) and local.endswith(_surname(name)):
            email = a
            break
        raise ValueError("District %s: county address %r does not look like %r's" % (d, a, name))
    return seat, member(name, seat=seat, email=email)


def parse(pages):
    page = pages[URLS[0]]
    start = re.search(r"<h1\b[^>]*>\s*Commissioners\s*</h1>", page)
    if not start:
        raise ValueError("no 'Commissioners' heading on the Leadership page")
    districts, seats, d = {}, {}, None
    for blk in BLOCK.findall(page, start.end()):
        heads = [txt(h) for h in H3.findall(blk)]
        if not heads:
            continue
        if len(heads) != 1:
            raise ValueError("a text block carries %d headings: %r" % (len(heads), heads))
        h = heads[0]
        m = DIST.match(h)
        if m:
            d = m.group(1)
            if district_number(h) != int(d):
                raise ValueError("heading %r read two ways" % h)
            if d in districts:
                raise ValueError("District %s has two headings" % d)
            districts[d], seats[d] = [], set()
            continue
        if h != "COMMISSIONER":
            break                       # the section is over
        if d is None:
            raise ValueError("a COMMISSIONER block sits before the first district heading")
        seat, rec = read_member(d, blk)
        if seat in seats[d]:
            raise ValueError("District %s Seat %s appears twice" % (d, seat))
        seats[d].add(seat)
        districts[d].append(rec)
    for n, s in seats.items():
        if s != {"A", "B", "C"}:
            raise ValueError("District %s shows seats %s, not A, B and C" % (n, sorted(s)))
    return {"districts": districts, "atLarge": []}
