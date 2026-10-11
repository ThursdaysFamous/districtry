"""Hickman County elects 14 commissioners, two from each of 7 districts; each
district is one "Vote for Two (2)" contest on the ballot and no seat is
named, so no seat is recorded. The page names no commission office, so no
role is recorded (the County Mayor, who appears on the county's committee
page, holds no commission seat).

The Commissioners page (a CMS "people grid") gives each district a centred
<h2> "District One" .. "District Seven", followed by one card per member. A
card holds the headshot, the name ("people-name"), the member's own district
label ("people-district", e.g. "DISTRICT ONE") and a details block. A member
is paired with the district label printed in their own card, and that label
must equal the <h2> of the section the card sits in, so a card that drifted
under the wrong heading raises. Nothing is read from order. A card without
exactly one name and one district label raises, and every district 1..7 must
appear.

The page prints names in ALL CAPITALS. They are title-cased here: each word
capitalised, "Mc" names as McName, an "O'" prefix as O'Name, hyphenated
parts each capitalised, and Jr./Sr./II/III/IV as suffixes. Where the card's
own headshot file name spells a word of the name with an inner capital, that
spelling is used: "JONATHAN LACASSE" is read as "Jonathan LaCasse" from his
headshot "Jonathan-LaCasse-District-1-....jpeg", which is also how the
ballot spells him. All-capital file names ("DUSTY_2.jpg") are ignored.

E-mail: every card's details block ends with a per-member county address,
first.last@hickmancountytn.gov. It is kept only on hickmancountytn.gov and
only when its local part carries the member's surname; a county address that
does not raises rather than being attached to the wrong person.

PRIVACY: each details block also prints the member's home street address,
town, ZIP and personal phone; none is read. The county's own office address,
phone and info@ address in the footer are not read.

Currency: checked 2026-10-11 against the Hickman County Election
Commission's "Precinct Results Report" for the 6 August 2026 State Primary
and State and County General (hickmancountytn.gov/images/uploads/
portal_files/Precinct_Results-8-7-2026_09-22-51_AM.pdf, Election Night
Reporting, run 08/07/2026 9:20 AM, 16 of 16 polling places, marked
"Unofficial Results"; a text PDF of 84 pages; no certified copy was found on
the county's site). Summing each "COUNTY COMMISSION District N - Vote for
Two (2)" contest over its precincts, the two highest in every district are
the two names here: D1 Shelley Farinato 278, Jonathan LaCasse 197 (Jim
Herron 128); D2 Nick Bentley 267, Bob O Holt 211 (Roy D Stinson 198); D3
Tony Essary 224, Ethan Hudgins 191 (Matthew Barnhill 166); D4 Steve Gianakos
381, Garen Graves 291 (Kathy Winters Redden 162); D5 Zachary Bentley 354,
Dusty Jordan 303 (Ron Mayberry 212); D6 Devin Pickard 427, Ryan K. Rogers
392 (Josie (Blystad) Petersen 297); D7 Jim Tanner 312, Steve L. Anglin 300
(Clay Chessor 249). The page's "Zach Bentley" is the ballot's "Zachary
Bentley"."""
import re
from ._common import txt, mailtos, member, district_number

COUNTY = "Hickman"; FIPS = "081"
DOMAINS = ("hickmancountytn.gov",)
URLS = ["https://hickmancountytn.gov/government/commissioners"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0

H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
SECTION = re.compile(r"^District\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)$", re.I)
CARD = re.compile(r'<div class="col-md-8">')
PNAME = re.compile(r'<p class="[^"]*\bpeople-name\b[^"]*">(.*?)</p>', re.S)
PDIST = re.compile(r'<p class="[^"]*\bpeople-district\b[^"]*">(.*?)</p>', re.S)
DETAILS = re.compile(r'<div class="people-details">(.*?)</div>', re.S)
PHOTO = re.compile(r'<img src="[^"]*/headshots/([^"/]+)"')
CAPS = re.compile(r"^[A-Z][A-Z.'’ -]+$")
SUFFIX = {"JR": "Jr.", "JR.": "Jr.", "SR": "Sr.", "SR.": "Sr.", "II": "II", "III": "III", "IV": "IV"}


def _part(p):
    low = p.lower()
    if low.startswith("mc") and len(p) > 2:
        return "Mc" + low[2].upper() + low[3:]
    if re.match(r"o['’].", low):
        return "O" + low[1] + low[2].upper() + low[3:]
    return low[:1].upper() + low[1:]


def title_name(caps, photo):
    """'JONATHAN LACASSE' -> 'Jonathan LaCasse' (inner capital from the photo file)."""
    inner = {}
    for tok in re.split(r"[-_. ]+", re.sub(r"\.[A-Za-z]+$", "", photo or "")):
        if re.search(r"[a-z]", tok) and re.search(r"[A-Z]", tok[1:]):
            inner[tok.upper()] = tok
    words = []
    for w in caps.split():
        if w in SUFFIX:
            words.append(SUFFIX[w])
        elif w.strip(",") in inner:
            words.append(inner[w.strip(",")])
        elif re.fullmatch(r"(?:[A-Z]\.)+", w):
            words.append(w)
        else:
            words.append("-".join(_part(p) for p in w.split("-")))
    return " ".join(words)


def _on_domain(addr):
    dom = addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""
    return any(dom == d or dom.endswith("." + d) for d in DOMAINS)


def _email(name, card):
    words = [w for w in name.split() if w not in SUFFIX.values()]
    surname = re.sub(r"[^a-z]", "", words[-1].lower())
    out = None
    for a in mailtos(card):
        if not _on_domain(a):
            continue
        if surname not in a.split("@", 1)[0].lower():
            raise ValueError("county address %r in %r's card does not carry the surname" % (a, name))
        if out and out.lower() != a.lower():
            raise ValueError("%r's card carries two county addresses" % name)
        out = a
    return out


def parse(pages):
    page = pages[URLS[0]]
    heads = [h for h in H2.finditer(page) if SECTION.match(txt(h.group(1)))]
    if not heads:
        raise ValueError("no 'District N' headings on the page")
    if PNAME.search(page, 0, heads[0].start()):
        raise ValueError("a member card sits before the first District heading")
    districts = {}
    for k, h in enumerate(heads):
        d = str(district_number(txt(h.group(1))))
        if d in districts:
            raise ValueError("District %s has two headings" % d)
        stop = heads[k + 1].start() if k + 1 < len(heads) else len(page)
        seats = []
        for card in CARD.split(page[h.end():stop])[1:]:
            names, dists = PNAME.findall(card), PDIST.findall(card)
            if not names and not dists:
                continue
            if len(names) != 1 or len(dists) != 1:
                raise ValueError("District %s: a card holds %d names and %d district labels"
                                 % (d, len(names), len(dists)))
            label = txt(dists[0])
            if str(district_number(label)) != d:
                raise ValueError("District %s section holds a card labelled %r" % (d, label))
            caps = txt(names[0])
            if re.search(r"\bvacan", caps, re.I) or not CAPS.match(caps):
                raise ValueError("District %s: %r is not an all-capitals name" % (d, caps))
            photo = PHOTO.search(card)
            name = title_name(caps, photo.group(1) if photo else None)
            # The card's details block (address, phone, mailbox) is the only
            # place an e-mail is read; the split runs on into the page footer.
            details = DETAILS.findall(card)
            if len(details) != 1:
                raise ValueError("District %s: %r's card has %d details blocks" % (d, name, len(details)))
            seats.append(member(name, email=_email(name, details[0])))
        if not seats:
            raise ValueError("District %s heading has no member cards under it" % d)
        districts[d] = seats
    if set(districts) != set(SEATS):
        raise ValueError("the page names districts %s, not 1..7" % sorted(districts, key=int))
    return {"districts": districts, "atLarge": []}
