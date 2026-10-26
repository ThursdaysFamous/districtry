"""Henry County elects 15 commissioners, three from each of 5 districts (every
district's contest on the 6 August 2026 ballot was "VOTE FOR 3"). No seat
letter or number is published, so no seat is recorded. The County Mayor
chairs the commission ("County Mayor / Commission Chair") and holds no
commission seat; he is not recorded.

The county's site is a client-rendered app: the page at
/government?tab=commissioners is an empty shell whose one module script, the
site's JavaScript bundle, carries the roster as a literal array of
{district: N, members: [{name, role, phone, phone2, email, address, ...}]}
that the "Commissioners" tab draws as one tab per district. Both are read:
the shell first, to check that it still loads the bundle named in URLS (the
bundle's file name changes whenever the site is redeployed, and then the
parse raises rather than read a stale bundle), then the bundle. The array
must occur exactly once; each member is paired with the "district" of the
entry it sits in, never with its position. Every member's "role" must be
"County Commissioner" or a commission office; no role is recorded (see
below). The tab's own text, "Henry County is divided into 5 districts, each
represented by County Commissioners for a total of 14 County Commissioners",
is read as well.

District 2 lists two members against the three the district elects, and the
tab says the commission totals 14, not 15. The Henry County Election
Commission's Election Summary Report for 6 August 2026 explains it: the
third District 2 seat was a TIE, Paul J Neal 437 and Eric Walker 437, behind
Ralph Wiles 645 and Charles O. Elizondo 519. The same commission's ballot
for the 3 November 2026 State and Federal General Election
(henrycoelection.com home page, "Henry G26 Newspaper Ballot", file
irp.cdn-website.com/76eef5f7/files/uploaded/Henry+G26+Newspaper+Ballot.pdf,
created 18 September 2026, read 2026-10-11) carries the contest "COUNTY
COMMISSION DISTRICT 2, Vote For One (1)" between Paul J Neal and Eric
Walker, both Independent Candidates: the tie goes back to the voters on 3
November, so the seat is unfilled until then. Neither tied candidate appears
among the county's commissioners, and the county's own agenda for the
commission's first meeting of the new term (21 September 2026, below) names
only Elizondo and Wiles for District 2. (Paul Neal sat on the 2022-2026
commission; the bundle's separate standing-committee text, which still
lists the 2022-2026 members, names him, and it is not read.) So the seat is
recorded vacant, on the county's own statement: the parse reads the tab's
"total of N", requires N to equal the names listed, and fills exactly
sum(SEATS) - N shortfalls with vacancies, raising if the short districts do
not account for that number exactly. When the November winner is seated and
the page names a third member and a total of 15, the parser reads it with
no change.

Roles: the bundle labels Monte Starks (District 3) "Vice-Chairman of
Commission". The county's agenda for 21 September 2026 proposes Joe Rice
(District 5) as Chair Pro Tempore for the year to September 2027, so that
label most likely belongs to the previous term; it is not recorded, and no
other member carries an office.

PRIVACY: every member record in the bundle carries a home street address,
one or two phones ("phone", and "phone2" for three members) and, for 12 of 14,
a personal or business e-mail (gmail, hotmail, aol, bellsouth, charter,
outlook, claytonhomes.com, wilesdriveshaft.com). The phones are recorded as
printed, "phone" first and "phone2" after it, under Adam's ruling of
2026-10-17 that a number a government publishes beside an official ships
whosever line it is; the two field names say nothing about what kind of line
each is, so no label is written. The "address" field is never read. The
"email" field is recorded as the bundle gives it, under Adam's choice of
2026-10-17 that a personal address a government page prints beside an
official is shown ("E-mails too"); no member has one on henrycountytn.gov or
henrycountytn.org. Each field is read from inside its own member's record,
one record cut from the next at "{name:", and a record with no "email" field
or two raises. The Mayor's record and the county staff records elsewhere in
the bundle are not read.

Names are kept as the bundle prints them ("Rick Parker", whose ballot name is
"Ricky D Parker"; "Charles Elizondo", "Chuck Elizondo" in the county's
agenda).

Currency: checked 2026-10-11 against the Henry County Election Commission's
"Election Summary Report", 2026 State Primary and County General, election
date 8/6/2026, run 8/25/2026 4:09 PM, 8 of 8 precincts reported
(henrycoelection.com "Election Results" page, "AUG 2026 COUNTY WIDE", file
irp.cdn-website.com/76eef5f7/files/uploaded/Aug2026.pdf, the commission
site's own file store; a text PDF). In Districts 1, 3, 4 and 5 the three
names here are the three winners: D1 Flowers 560, Stewart 393, James Eichel
360 (Townsend 340, Primrose 337, Chelsea Eichel 326); D3 Starks, Visser,
Wright (uncontested); D4 Humphreys 461, Hayes 456, Ricky D Parker 336
(uncontested); D5 Rice 742, Perry 686, Burns 632 (Carter 356, Bates 309).
District 2 is the tie above. The county's own agenda and resolutions for the
commission's 21 September 2026 meeting (henrycountytn.gov, "Commission-
Agenda-and-Resolutions-9-21-26.pdf", a scan created 16 September 2026, read
as images), Resolution 1-9-26, appoints the new term's commissioners to
committees by district and names twelve of these fourteen, each in the
district this page gives (Monte Starks and Patrick Burns are given no
appointment in it, which says nothing against them). District 2's two
clear winners, Wiles and Elizondo, are the two names here; its third seat
goes to the 3 November 2026 ballot described above, and until a winner is
certified and seated it is vacant on the county's own count of 14."""
import re
from ._common import member, vacant, member_email, ROLE, read_phones, Withheld

COUNTY = "Henry"; FIPS = "079"
DOMAINS = ("henrycountytn.gov", "henrycountytn.org")
URLS = ["https://henrycountytn.gov/government?tab=commissioners",
        "https://henrycountytn.gov/assets/index-C-CEYf2G.js"]
SEATS = {str(i): 3 for i in range(1, 6)}
AT_LARGE = 0

SCRIPT = re.compile(r'<script type="module" crossorigin src="([^"]+)"')
ARRAY = re.compile(r"\[\{district:1,members:\[")
DIST = re.compile(r"\{district:(\d{1,2}),members:\[")
PERSON = re.compile(r'\{name:"([^"]*)",role:"([^"]*)",phone:')
EMAIL = re.compile(r'email:(?:null|"([^"]*)")')
PHONES = re.compile(r'\bphone:(null|"[^"]*"),phone2:(null|"[^"]*"),')
TOTAL = re.compile(r"for a total of (\d{1,2}) County Commissioners")
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
SEAT_ROLE = "County Commissioner"


def parse(pages):
    shell, bundle = pages[URLS[0]], pages[URLS[1]]
    src = SCRIPT.findall(shell)
    if src != [URLS[1].split("henrycountytn.gov", 1)[1]]:
        raise ValueError("the page now loads %r, not the bundle in URLS: update URLS" % src)
    starts = [m.start() for m in ARRAY.finditer(bundle)]
    if len(starts) != 1:
        raise ValueError("the district roster array occurs %d times in the bundle" % len(starts))
    end = bundle.find("}]}];", starts[0])
    if end < 0:
        raise ValueError("cannot find the end of the district roster array")
    arr = bundle[starts[0]:end + 4]
    heads = list(DIST.finditer(arr))
    districts = {}
    for k, h in enumerate(heads):
        d = h.group(1)
        if d in districts:
            raise ValueError("District %s appears twice in the array" % d)
        seg = arr[h.end():heads[k + 1].start() if k + 1 < len(heads) else len(arr)]
        people = PERSON.findall(seg)
        if len(people) != seg.count("{name:"):
            raise ValueError("District %s: a member record is not {name, role, phone, ...}" % d)
        numbers = PHONES.findall(seg)
        if len(numbers) != len(people):
            numbers = [None] * len(people)     # the fields changed shape: keep every number off
        cuts = [m.start() for m in re.finditer(r"\{name:", seg)] + [len(seg)]
        mails = []
        for a, b in zip(cuts, cuts[1:]):
            got = EMAIL.findall(seg[a:b])
            if len(got) != 1:
                raise ValueError("District %s: a member record carries %d e-mail fields" % (d, len(got)))
            mails.append(got[0])
        seats = []
        for (name, role), mail, nums in zip(people, mails, numbers):
            if re.search(r"\bvacan", name, re.I) or not NAME.match(name):
                raise ValueError("District %s: %r does not look like a name" % (d, name))
            if role != SEAT_ROLE and not ROLE.search(role):
                raise ValueError("District %s: %r carries the role %r" % (d, name, role))
            if nums is None:
                phones = Withheld("the bundle's phone fields are not phone, phone2")
            else:
                phones = []
                for v in nums:
                    got = read_phones(v[1:-1], strict=True) if v != "null" else []
                    if isinstance(got, Withheld):
                        phones = got
                        break
                    phones += got
            seats.append(member(name, email=member_email([mail] if mail else [], DOMAINS),
                                phones=phones))
        districts[d] = seats
    if set(districts) != set(SEATS):
        raise ValueError("the array names districts %s, not 1..5" % sorted(districts, key=int))

    # Vacancies only where the county's own total says seats are unfilled.
    # Since the redeploy of 2026-10-26 the bundle carries the sentence twice:
    # once in the tab and once in the site's search index. Both must agree.
    total = TOTAL.findall(bundle)
    if not total or len(set(total)) != 1:
        raise ValueError("the Commissioners tab no longer states one 'a total of N County "
                         "Commissioners' (found %r)" % total)
    stated = int(total[0])
    named = sum(len(v) for v in districts.values())
    if stated != named:
        raise ValueError("the tab says %d commissioners and the roster lists %d" % (stated, named))
    short = {d: SEATS[d] - len(v) for d, v in districts.items() if len(v) < SEATS[d]}
    if any(len(v) > SEATS[d] for d, v in districts.items()):
        raise ValueError("a district lists more members than it elects")
    if sum(short.values()) != sum(SEATS.values()) - stated:
        raise ValueError("short districts %s do not account for the %d unfilled seats"
                         % (short, sum(SEATS.values()) - stated))
    for d, n in short.items():
        districts[d].extend(vacant() for _ in range(n))
    return {"districts": districts, "atLarge": []}
