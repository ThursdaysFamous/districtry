"""Sullivan County elects 24 commissioners from 11 districts: one in Districts
1 and 3, three in Districts 2, 4, 6 and 11, and two in Districts 5, 7, 8, 9 and
10. The ballot calls no seat by a letter or number, so no seat is recorded.

The source is NOT the county government's commission page
(sullivancountytn.gov/county-commissioner-information/), which on 2026-10-11
still listed the 2022-2026 commission (David Hayes in District 1, Barry
Hopper and Cheryl Harvey in District 2, Zane Vanover, Daniel Horne and
Jessica Means in District 6 and others who were not elected in August 2026)
and linked a "2022-2026 county commission contact list". It is the Sullivan
County Election Commission's "Sullivan County Elected Officials" page on its
own site (scelect.org, linked from its Records page), a plain hand-written
HTML page in which every office is one line ending at a <br>. Its "COUNTY
COMMISSIONERS" heading (an underlined span, followed by "(TERM EXPIRES
2030)") is followed by one line per member, "<NAME> (<party>) - DISTRICT N",
and the section ends at the next underlined heading ("SULLIVAN COUNTY SCHOOL
BOARD"). The parser cuts the page at those two headings, splits the section
at its <br> tags, and reads each member's district from that member's own
line; nothing is read from order. The term note must name a year of 2030 or
later, and any line in the section that is not "<NAME> (<party>) - DISTRICT
N" raises. The party label ("(Rep)", "(Ind)") is not part of the name and is
dropped; one line (Mark A. Vance) prints none.

Names are printed in capitals ("BOB HARSHBARGER JR.", "SAMUEL "SAM" JONES",
"DAVID AKARD III") and are title-cased here: each word's first letter kept
capital and the rest lowered, a single-letter initial and a roman suffix
(II, III, IV) left as printed, "Jr."/"Sr." lowered after the first letter,
"Mc"/"O'" followed by a capital, a hyphenated word cased on each side, and a
quoted nickname kept in its quotes ("Samuel "Sam" Jones"). No name on the
page carries an inner capital that this would lose: the August 2026 results,
printed in mixed case, show none in any of these 24 names.

PRIVACY: the page prints no address, phone or e-mail for any commissioner.
The county government's page does print each member's home street address,
town, ZIP and a phone number. It is not read because it still lists the
2022-2026 commission (above), not for privacy, so none of its numbers ship.

Currency: checked 2026-10-11 against the Sullivan County Election
Commission's own results of the 6 August 2026 County General
(scelect.org/aug2026precinctresults.pdf, "State of Tennessee - Sullivan
County, August 6, 2026, County General", pages dated August 11, 2026, linked
from the commission's Past Election Results page; it is not labelled
certified). In every district the names here are the winners: D1 Thompson
379 (Woodall 309, Marek 81); D2 Akard, Harvey, Vance (three candidates for
three seats); D3 Cross (unopposed); D4 Cole, Crosswhite, Hayes (three for
three); D5 Boomershine, King; D6 Pullon 1,945, Johnson 1,831, Harshbarger
1,425 (Walden 1,095, Osborne 978); D7 Jones, Ward; D8 Ireson 1,320, Hodges
1,205 (Mullenix 441); D9 Carr, Golden; D10 Crawford, Derrick; D11 Gardner
1,172, Locke 1,025, Thomas 983 (Marshall 942, French 827, Sampson 482). The
results do not print how many seats each district fills; the seat counts
above are the number of members this page names in each district, which is
also the pattern of the county's own (stale) 2022-2026 page and of CTAS's 24
rows. The District 11 third seat was decided by 41 votes on an uncertified
report; this page, which names Zac Thomas, is the election commission's own
later statement of who holds it. The page carries no date of its own; what
places it after the election is its "(TERM EXPIRES 2030)" note, its naming
of Zane Vanover (a 2022-2026 District 6 commissioner) as County Mayor with
a term expiring 2030, and its agreement with the results in all 11
districts."""
import re
from ._common import txt, member, district_number

COUNTY = "Sullivan"; FIPS = "163"
DOMAINS = ("sullivancountytn.gov", "scelect.org")
URLS = ["https://www.scelect.org/electedofficials.html"]
SEATS = {"1": 1, "2": 3, "3": 1, "4": 3, "5": 2, "6": 3, "7": 2, "8": 2,
         "9": 2, "10": 2, "11": 3}
AT_LARGE = 0

HEAD_RE = re.compile(r"<span\b[^>]*underline[^>]*>\s*COUNTY COMMISSIONERS\s*</span>")
NEXT_HEAD_RE = re.compile(r"<span\b[^>]*underline[^>]*>")
TERM_RE = re.compile(r"^\(TERM EXPIRES (\d{4})\)$")
ENTRY_RE = re.compile(r"^(?P<name>.+?)\s*(?:\((?P<party>Rep|Dem|Ind|Lib|Grn)\s*\))?\s*-\s*"
                      r"(?P<label>DISTRICT\s+(?P<d>\d{1,2}))$")
CAPS_RE = re.compile(r"^[A-Z][A-Z.'’\" -]+$")
SUFFIX = {"JR", "SR", "II", "III", "IV"}


def title_case(caps):
    """'BOB HARSHBARGER JR.' -> 'Bob Harshbarger Jr.';
    'SAMUEL "SAM" JONES' -> 'Samuel "Sam" Jones'."""
    out = []
    for word in caps.split():
        parts = []
        for part in word.split("-"):
            m = re.fullmatch(r"([^A-Za-z]*)([A-Za-z.'’]*)([^A-Za-z]*)", part)
            if not m:
                raise ValueError("cannot title-case %r in %r" % (part, caps))
            lead, core, trail = m.groups()
            letters = re.sub(r"[.'’]", "", core)
            if not letters:
                parts.append(part)
                continue
            mc = re.fullmatch(r"MC([A-Z]{2,})", core)
            if mc:
                core = "Mc" + mc.group(1).capitalize()
            elif len(letters) == 1 or letters in SUFFIX - {"JR", "SR"}:
                pass                            # an initial, or II/III/IV
            elif re.fullmatch(r"O['’][A-Z]+", core):
                core = core[:2] + core[2:].capitalize()
            else:
                core = core.capitalize()
            parts.append(lead + core + trail)
        out.append("-".join(parts))
    return " ".join(out)


def parse(pages):
    page = pages[URLS[0]]
    heads = list(HEAD_RE.finditer(page))
    if len(heads) != 1:
        raise ValueError("%d 'COUNTY COMMISSIONERS' headings on the page, expected 1" % len(heads))
    nxt = NEXT_HEAD_RE.search(page, heads[0].end())
    if not nxt:
        raise ValueError("no heading after the commissioners section")
    if "SCHOOL BOARD" not in txt(page[nxt.start():page.find("</span>", nxt.start())]):
        raise ValueError("the heading after the commissioners is not the school board's")
    pieces = [txt(x) for x in re.split(r"<br\b[^>]*>", page[heads[0].end():nxt.start()], flags=re.I)]
    pieces = [x for x in pieces if x]
    if not pieces:
        raise ValueError("nothing under the commissioners heading")
    term = TERM_RE.match(pieces[0])
    if not term or int(term.group(1)) < 2030:
        raise ValueError("the commissioners heading's term note reads %r, not a term "
                         "expiring 2030 or later" % pieces[0])
    districts = {}
    for line in pieces[1:]:
        m = ENTRY_RE.match(line)
        if not m:
            raise ValueError("a line under the commissioners is not '<NAME> (party) - "
                             "DISTRICT N': %r" % line)
        caps = m.group("name").strip()
        if not CAPS_RE.match(caps) or re.search(r"\bVACAN", caps):
            raise ValueError("%r does not look like a name" % caps)
        d = district_number(m.group("label"))
        if d is None or str(d) != m.group("d").lstrip("0"):
            raise ValueError("%r read two ways" % m.group("label"))
        districts.setdefault(str(d), []).append(member(title_case(caps)))
    if not districts:
        raise ValueError("no '<NAME> - DISTRICT N' lines under the commissioners heading")
    return {"districts": districts, "atLarge": []}
