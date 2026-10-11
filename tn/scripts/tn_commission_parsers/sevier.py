"""Sevier County elects 25 commissioners from 11 districts: Seats A and B in
Districts 1, 2, 3, 6, 7, 9, 10 and 11, and Seats A, B and C in Districts 4, 5
and 8. The commission page lists them in one paragraph separated by <br>,
each entry opening with a line '<Name> - District N, Seat X' (the dash is a
hyphen or an en dash, and the name and label are sometimes in separate
<strong> tags on that same line). The district and seat are read from that
line, never from order.

PRIVACY: every entry's next lines are a street address, a town, a ZIP and a
phone number. Those are the commissioners' own and are not recorded; only the
'Name - District N, Seat X' line is read. The page publishes no e-mail.

Currency: the Sevier County Election Commission's certification of the
6 August 2026 county general election (signed 20 August 2026, a scanned PDF,
read as an image) gives the same 25 winners in the same districts and seats."""
import re
from ._common import txt, member

COUNTY = "Sevier"; FIPS = "155"
DOMAINS = ("seviercountytn.gov",)
URLS = ["https://seviercountytn.gov/government/county_officials/county_commissioners/"]
SEATS = {"1": 2, "2": 2, "3": 2, "4": 3, "5": 3, "6": 2, "7": 2, "8": 3,
         "9": 2, "10": 2, "11": 2}
AT_LARGE = 0

ENTRY = re.compile(r"^(?P<name>.+?)\s*[-–—]\s*District\s+(?P<d>\d{1,2}),\s*Seat\s+(?P<s>[A-Z])$")


def parse(pages):
    page = pages[URLS[0]]
    main = re.search(r"<main\b(.*?)</main>", page, re.S)
    if not main:
        raise ValueError("no <main> element")
    districts, seen = {}, set()
    for seg in re.split(r"<br\s*/?>", main.group(1), flags=re.I):
        line = txt(seg)
        if not re.search(r"\bSeat\b", line):
            continue
        m = ENTRY.match(line)
        if not m:
            raise ValueError("a line names a seat but is not 'Name - District N, Seat X': %r" % line)
        d, s = m.group("d"), m.group("s")
        if (d, s) in seen:
            raise ValueError("District %s Seat %s appears twice" % (d, s))
        seen.add((d, s))
        districts.setdefault(d, []).append(member(m.group("name"), seat=s))
    return {"districts": districts, "atLarge": []}
