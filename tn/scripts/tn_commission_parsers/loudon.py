"""Loudon County's commission has 10 members from 7 districts: two in each of
Districts 1, 2 and 5 (each elects a Seat A and a Seat B) and one in each of
Districts 3, 4, 6 and 7, as the county's August 2026 results hold them. The
page does not say which member holds Seat A and which Seat B, so no seat is
recorded.

The commission page (WordPress) carries a photograph of the new commission
captioned "Seated, left to right:" and "Standing,left to right:", each a
comma-separated list in which every member is written "Name (Nth District)".
Two people in the photograph are not members ("Tammy Wampler (Chief Deputy)"
and "Mayor Buddy Bradshaw") and carry no district, so they are not read. A
name is paired with the district in its own parentheses; nothing is read from
order, and each district must hold exactly the seats the county elects there.

THE SAME PAGE'S "Contact Information" LIST FURTHER DOWN IS THE 2022-2026
COMMISSION and is NOT read: on 2026-10-26 it still named Bill Geames
(District 1), Will Jenkins and Rosemary Hines Quillen (District 2) and Henry
J. Cullen (District 7), none of whom was elected in August 2026. The member
e-mail addresses and phone numbers sit only in that list, so no contact is
recorded for anyone. When the county rewrites it, the parser can read it.

Currency, checked 2026-10-26: the page was last modified 2026-10-22. Every
member in the caption is the winner of the 6 August 2026 election in the
district the caption gives, by the Loudon County Election Commission's
"OFFICIAL RESULTS" Summary Results Report, generated 12 August 2026
(www.loudoncountyvotes.com/archives/2026/August_2026_OfficialResults_SummaryReport.pdf):
District 1 Seat A Chase Randolph, Seat B Bob Gross; District 2 Seat A Jason
Tuttle, Seat B David Cook; District 3 Bill D. Satterfield; District 4 Gary
Whitfield; District 5 Seat A Joe Morrison, Seat B Van Shaver; District 6 Adam
Waller; District 7 Rick Dramm. The commission's minutes of its 8 September
2026 meeting (loudoncounty-tn.gov/wp-content/uploads/2026/09/
20260908_CommissionMeeting_Minutes.pdf, a scan) call the roll of the same ten,
without districts, and record that meeting's election of a chairman and a
chair pro tempore; the caption names neither role, so neither is recorded.

Held until then: on 2026-10-13 and 2026-10-15 the page listed the 2022 board."""
import re
from ._common import txt, district_number, member

COUNTY = "Loudon"; FIPS = "105"
DOMAINS = ("loudoncounty-tn.gov",)
URLS = ["https://loudoncounty-tn.gov/county-commission/"]
SEATS = {"1": 2, "2": 2, "3": 1, "4": 1, "5": 2, "6": 1, "7": 1}
AT_LARGE = 0

CAPTION_RE = re.compile(r"Seated, left to right:(.*?)</p>", re.S)
ENTRY_RE = re.compile(r"^(.*?)\s*\(([^()]*)\)$")
NOT_MEMBERS = ("Chief Deputy",)


def parse(pages):
    page = pages[URLS[0]]
    found = CAPTION_RE.findall(page)
    if len(found) != 1:
        raise ValueError("expected one 'Seated, left to right:' caption, found %d" % len(found))
    text = txt(found[0])
    parts = re.split(r"Standing,\s*left to right:", text)
    if len(parts) != 2:
        raise ValueError("the caption no longer has a 'Standing, left to right:' half")
    districts = {}
    for half in parts:
        for entry in (e.strip(" .") for e in half.split(",")):
            if not entry:
                continue
            m = ENTRY_RE.match(entry)
            if not m:
                if entry.startswith("Mayor "):
                    continue
                raise ValueError("caption entry %r carries no district" % entry)
            name, label = m.group(1).strip(), m.group(2).strip()
            if label in NOT_MEMBERS:
                continue
            if not re.fullmatch(r"\d{1,2}(?:st|nd|rd|th) District", label):
                raise ValueError("caption entry %r: %r is not a district" % (entry, label))
            n = district_number(label)
            if re.search(r"\bvacan", name, re.I) or not re.fullmatch(r"[A-Z][A-Za-z.'’ -]+", name):
                raise ValueError("District %s: %r does not look like a name" % (n, name))
            districts.setdefault(str(n), []).append(member(name))
    for n, want in SEATS.items():
        if len(districts.get(n, [])) != want:
            raise ValueError("District %s: the caption names %d, the county elects %d"
                             % (n, len(districts.get(n, [])), want))
    extra = set(districts) - set(SEATS)
    if extra:
        raise ValueError("the caption names districts the county does not have: %s" % sorted(extra))
    return {"districts": districts, "atLarge": []}
