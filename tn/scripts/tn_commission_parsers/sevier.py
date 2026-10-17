"""Sevier County elects 25 commissioners from 11 districts: Seats A and B in
Districts 1, 2, 3, 6, 7, 9, 10 and 11, and Seats A, B and C in Districts 4, 5
and 8. The commission page lists them in one paragraph separated by <br>,
each entry opening with a line '<Name> - District N, Seat X' (the dash is a
hyphen or an en dash, and the name and label are sometimes in separate
<strong> tags on that same line). The district and seat are read from that
line, never from order.

PRIVACY: every entry's next lines are a street address, then a town and ZIP
followed on the same line by "- Phone (865) ...". The phone is recorded as
printed, under Adam's ruling of 2026-10-17 that a number a government
publishes beside an official ships whosever line it is: only the
telephone-shaped number is read from that line, and the street, town and ZIP
are never read. A number is the entry's whose 'Name - District N, Seat X'
line it follows, up to the next entry or the end of the paragraph. One entry
prints its area code without the opening parenthesis ("865) 428-..."); it is
kept as printed. The county's line in the page footer is OFFICE_LINES and
never lands on a member. The page publishes no e-mail.

Currency: the Sevier County Election Commission's certification of the
6 August 2026 county general election (signed 20 August 2026, a scanned PDF,
read as an image) gives the same 25 winners in the same districts and seats."""
import re
from ._common import txt, member, read_phones, Withheld

COUNTY = "Sevier"; FIPS = "155"
DOMAINS = ("seviercountytn.gov",)
URLS = ["https://seviercountytn.gov/government/county_officials/county_commissioners/"]
SEATS = {"1": 2, "2": 2, "3": 2, "4": 3, "5": 3, "6": 2, "7": 2, "8": 3,
         "9": 2, "10": 2, "11": 2}
AT_LARGE = 0
# The county's line, in the page footer.
OFFICE_LINES = ("(865) 453-6136",)

ENTRY = re.compile(r"^(?P<name>.+?)\s*[-–—]\s*District\s+(?P<d>\d{1,2}),\s*Seat\s+(?P<s>[A-Z])$")
# A block-level tag ends the paragraph the entries are written in.
BLOCK_END = re.compile(r"</?(?:p|div|h[1-6]|ul|ol|li|table|section|article)\b", re.I)


def parse(pages):
    page = pages[URLS[0]]
    main = re.search(r"<main\b(.*?)</main>", page, re.S)
    if not main:
        raise ValueError("no <main> element")
    districts, seen, cur = {}, set(), None
    for seg in re.split(r"<br\s*/?>", main.group(1), flags=re.I):
        line = txt(seg)
        if not re.search(r"\bSeat\b", line):
            if cur is not None:                 # a line of the entry above: its phone, if any
                cut = BLOCK_END.search(seg)
                got = read_phones(seg[:cut.start()] if cut else seg)
                if not isinstance(cur["phones"], Withheld):
                    cur["phones"] = got if isinstance(got, Withheld) else cur["phones"] + got
                if cut:
                    cur = None                  # the paragraph is over
            continue
        m = ENTRY.match(line)
        if not m:
            raise ValueError("a line names a seat but is not 'Name - District N, Seat X': %r" % line)
        d, s = m.group("d"), m.group("s")
        if (d, s) in seen:
            raise ValueError("District %s Seat %s appears twice" % (d, s))
        seen.add((d, s))
        cur = {"name": m.group("name"), "seat": s, "phones": []}
        districts.setdefault(d, []).append(cur)
    for d, entries in districts.items():
        districts[d] = [member(e["name"], seat=e["seat"], phones=e["phones"]) for e in entries]
    return {"districts": districts, "atLarge": []}
