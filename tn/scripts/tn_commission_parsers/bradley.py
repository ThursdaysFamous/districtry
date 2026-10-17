"""Bradley County elects two commissioners from each of 7 districts (14 seats;
the ballot calls them Seat A and Seat B, the page does not, so no seat is
recorded). The commission page is a WordPress/Divi layout: inside the section
headed `<h2>County Commissioners</h2>` each district is an `<h3>District N</h3>`
text module followed by the `et_pb_team_member` modules of that district's
members, each carrying the member's photo (alt = name), an
`<h4 class="et_pb_module_header">` name, a phone and a mailto. A member is
paired with the `<h3>District N</h3>` heading that opens their section of the
block; the page's order of the two members inside a district does not follow
Seat A/B (District 2 lists Murray, Seat B, before Alford, Seat A).

Every member's e-mail is recorded (on 2026-10-17 every one was on
bradleycountytn.gov; one on another domain would be recorded too). Each
member's printed phone is recorded too, under Adam's ruling of 2026-10-17 that
a number a government publishes beside an official ships whosever line it
is, EXCEPT where its tel: link dials a different number from the one printed
beside it: on 2026-10-17 that was six of the fourteen (Terri Murray, Denny
Collins, Josh Taylor, Rich Kienlen, Stephen Beasley and Rusty Asble), whose
links still dial other numbers, so the page says two things and neither is
kept. The commission office line (423-728-7105) belongs to the office, not a
member, and OFFICE_LINES keeps it off every record. The page prints no
address.

Currency: the Bradley County Election Commission's results for the 6 August
2026 county general election name the same fourteen winners."""
import re
from ._common import txt, read_emails, member_email, member, read_phones

COUNTY = "Bradley"; FIPS = "011"
DOMAINS = ("bradleycountytn.gov",)
URLS = ["https://bradleycountytn.gov/county-government/county-commission/"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0
OFFICE_LINES = ("423-728-7105",)

TEAM = re.compile(r'<div class="et_pb_module et_pb_team_member\b')


def parse(pages):
    page = pages[URLS[0]]
    start = page.find("<h2>County Commissioners</h2>")
    if start < 0:
        raise ValueError("no 'County Commissioners' heading")
    nxt = page.find("<h2", start + 10)
    block = page[start:nxt if nxt > 0 else len(page)]
    pieces = re.split(r"<h3>\s*District\s+(\d{1,2})\s*</h3>", block)
    # pieces = [before-first-district, "1", body1, "2", body2, ...]
    if TEAM.search(pieces[0]):
        raise ValueError("a commissioner module sits before the first District heading")
    if len(pieces) < 3:
        raise ValueError("no District headings inside the commissioners block")
    if re.search(r"<h3\b", "".join(pieces[2::2])):
        raise ValueError("an <h3> inside the block is not a 'District N' heading")
    districts = {}
    for d, body in zip(pieces[1::2], pieces[2::2]):
        mods = TEAM.split(body)[1:]
        if not mods:
            raise ValueError("District %s heading has no members under it" % d)
        for m in mods:
            nm = re.search(r'<h4 class="et_pb_module_header">(.*?)</h4>', m, re.S)
            if not nm:
                raise ValueError("a member module in District %s has no name" % d)
            name = txt(nm.group(1))
            alt = re.search(r'<img[^>]*\balt="([^"]*)"', m)
            if alt and txt(alt.group(1)) and txt(alt.group(1)) != name:
                raise ValueError("photo alt %r differs from name %r" % (alt.group(1), name))
            email = member_email(read_emails(m), DOMAINS)
            districts.setdefault(d, []).append(member(name, email=email, phones=read_phones(m)))
    return {"districts": districts, "atLarge": []}
