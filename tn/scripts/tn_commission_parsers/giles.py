"""Giles County elects 21 commissioners from 7 districts, three in each (the
ballot says "Vote For Three (3)" and names no seat, so none is recorded).

The commission page (gilescountytn.gov/commission/, WordPress) has a section
headed "Giles County Commissioners" in which every member is a card: a photo,
an <h5 class="d-block"> with the name, then an <h5> reading "District N", a
phone and an e-mail. The page is cut at those name headings and each name is
paired with the "District N" heading inside its own card; a card without one,
or with anything else in that heading, raises. The section ends at its own
</section>, before the page's testimonials. The page's other table, "Committee
Chairs for Sept 2026 - Sept 2027", names committee chairs, which are not
commission offices, and is not read; the page names no chairman.

PRIVACY: every card carries a phone number, most of them personal. They are
recorded as printed, under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is, except Lynn
Albury's: her card's tel: link dials a different number from the one printed
beside it, and nothing on the page says which is hers, so neither is recorded.
The county's own phone and fax, in the page footer, are OFFICE_LINES and never
land on a member. The cards print no address. E-mails are kept only on
gilescountytn.gov and only when the local part contains the member's surname;
they are read from the card's visible text as well as its mailto link, because
Lynn Albury's link is written href="Calbury@gilescountytn.gov" with no mailto:.
"calbury" is hers: the ballot names her Cheryl Lynn Albury. Where a card's
mailto target and its printed address differ, no e-mail is recorded: James
Gentry's link prints jgentry@ but goes to jsutton@ (someone else's address),
and Chris Adcock's prints cadcock@ but goes to cadock@. Tommy Pollard's card
has no e-mail. That leaves 18 of 21 with an e-mail. An address on another
domain in a member's own card is kept as printed when it prints no county one,
under Adam's ruling of 2026-10-17 that an e-mail address a government page
prints beside an official ships too.

Currency: NO RESULTS OF THE 6 AUGUST 2026 ELECTION COULD BE READ ON A
GOVERNMENT HOST. gilescountytn.gov/elections/ links the November 2026 ballot
and candidate list and no August results (it refers readers to the GoVoteTN
app), and the state's results site elections.tn.gov refused our client (HTTP
403). The fallback used, all on gilescountytn.gov, read 2026-10-11:
  - the minutes of the new commission's work sessions of 10 September 2026
    ("a newly elected county legislative body"; 20 commissioners attending)
    and 17 September 2026 (17 attending, 4 absent), which between them name
    all 21 people on this page as commissioners and nobody else;
  - the county's "Official Ballot, State and County General Election, Giles
    County, August 6, 2026" (wp-content/uploads/2026/06/
    August-6-2026-Primary-and-General-Ballot.pdf), on which every one of the
    21 was a candidate for County Commissioner in the district this page puts
    them in (District 7, for example: Michael Cesarini, Shonda Reynolds
    Christian, Carman Brown, Judith C. Pruett for three seats).
Neither gives vote totals, so the district pairing is held by candidacy plus
seating rather than by results."""
import re
from ._common import txt, member, mailtos, district_number, read_phones, other_email

COUNTY = "Giles"; FIPS = "055"
DOMAINS = ("gilescountytn.gov",)
URLS = ["https://gilescountytn.gov/commission/"]
SEATS = {str(i): 3 for i in range(1, 8)}
AT_LARGE = 0
# The county's own phone and fax, in the page footer.
OFFICE_LINES = ("931-363-5300", "931-363-2068")

NAME_HEAD = re.compile(r'<h5 class="d-block">(.*?)</h5>', re.S)
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
ADDR = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _surname(name):
    words = [w.strip(".,").lower() for w in name.split()]
    while words and words[-1] in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1]) if words else ""


def _email(card, name):
    """The card's one county address, or None. A card whose mailto target and
    printed address disagree (Chris Adcock's link goes to cadock@, its text
    reads cadcock@) records neither: which one reaches him is not knowable
    from the page."""
    found = {a.strip().lower() for a in mailtos(card) + ADDR.findall(txt(card))}
    ours = sorted(a for a in found
                  if any(a.rsplit("@", 1)[-1] == d or a.rsplit("@", 1)[-1].endswith("." + d)
                         for d in DOMAINS))
    if len(ours) > 1:
        return None
    if not ours:
        return other_email(card, DOMAINS)
    sur = _surname(name)
    if sur not in re.sub(r"[^a-z]", "", ours[0].split("@", 1)[0]):
        raise ValueError("%r: county address %r does not look like the member's" % (name, ours[0]))
    return ours[0]


def parse(pages):
    page = pages[URLS[0]]
    start = page.find("Giles County Commissioners</h2>")
    if start < 0:
        raise ValueError("no 'Giles County Commissioners' heading")
    end = page.find("</section>", start)
    if end < 0:
        raise ValueError("cannot find the end of the commissioners section")
    section = page[start:end]
    heads = list(NAME_HEAD.finditer(section))
    if not heads:
        raise ValueError("no member cards in the commissioners section")
    districts = {}
    for k, h in enumerate(heads):
        card = section[h.end():heads[k + 1].start() if k + 1 < len(heads) else len(section)]
        name = txt(h.group(1))
        if not NAME.match(name):
            raise ValueError("%r is not a name" % name)
        labels = [txt(x) for x in re.findall(r"<h5\b[^>]*>(.*?)</h5>", card, re.S)]
        if len(labels) != 1 or not re.match(r"^District\s+\d{1,2}$", labels[0]):
            raise ValueError("%r: card headings %r are not one 'District N'" % (name, labels))
        d = district_number(labels[0])
        districts.setdefault(str(d), []).append(
            member(name, email=_email(card, name), phones=read_phones(card)))
    return {"districts": districts, "atLarge": []}
