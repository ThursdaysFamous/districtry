"""Franklin County elects 16 commissioners from 8 districts, Seat "A" and Seat
"B" in each.

The commission page (franklincotn.us/county_commission.html) carries the
heading "Current Terms End August 31, 2030" and then one <div class="col-sm-6">
per member. Each member's <h6> holds the name (as the text of an e-mail link,
or plain) followed on the same heading by '1st District Seat "A"'; the
district and seat are read from that heading, never from order, and the
heading's text must be exactly the name followed by that label. An <h6> in
the roster that carries text but no such label raises, as does a district and
seat seen twice. The parser also refuses a page whose term heading is missing
or ends before 2030, so a page put back to an earlier term is never read as
current. Photo alt text is not read: it is stale on two blocks (Edie Snyder's
photo is captioned "David Kelley", her predecessor in District 8 Seat B).

PRIVACY: under each heading the page prints the member's home street address
or P.O. box, town and ZIP and one to three personal phone numbers (some
marked Cell or Work); none of those is read. Most e-mail links are personal
(gmail, hotmail, yahoo, icloud, comcast, bellsouth, cafes.net) and are never
kept. An address on the county's own franklincotn.gov is kept only when its
local part starts with the member's first name or initial and contains the
surname: that keeps william.anderson@ and silasearle@, and leaves out
marysnyder@ on Edie Snyder's block, which names a different first name and
nothing on the page says is hers. The commission's inquiry line (931)
967-2541 is the county mayor's office and is not a member's.

Currency: NO COUNTYWIDE RESULTS OF THE 6 AUGUST 2026 ELECTION COULD BE READ ON
A GOVERNMENT HOST. On 2026-10-11 franklincotn.us/election_results.html and
every PDF it links (the "Summary" and the eighteen precinct files) read
"November 3, 2026 General Election Results / Available Soon" (created 9
October 2026), and the Election Commission page's "Election Results" link
(/uploads/election_commission_80_3703269086.pdf) is the 6 August 2026
"Precinct Summary Report" for ONE precinct, 02 Estill Springs (7:48 PM,
unofficial), whose two commission races agree with this page (District 8
Seat A: Glenn T. Summers Sr. over Kent Bean; Seat B: Edie Snyder, unopposed).
The evidence used is the fallback: this page's own heading "Current Terms End
August 31, 2030", the term that began 1 September 2026. It is consistent with
the outgoing commission's roll calls, which name all sixteen members by
district and seat (yes and absent lists), in its 24 August 2026 minutes
(franklincotn.us .../minutes/2026/09282026.pdf, approved 28 September): the
twelve members returning sit in the same district and seat on this page, and the four new names fill exactly the four seats that
changed hands (District 4 Seat A Tyler Bauer and Seat B Johnny Hand to Greg
King and Chuck Stines; District 6 Seat A Charles Keller, who ran for sheriff,
to Silas Earle; District 8 Seat B David Kelley to Edie Snyder)."""
import re
from ._common import txt, member, mailtos

COUNTY = "Franklin"; FIPS = "051"
DOMAINS = ("franklincotn.us", "franklincotn.gov")
URLS = ["https://franklincotn.us/county_commission.html"]
SEATS = {str(i): 2 for i in range(1, 9)}
AT_LARGE = 0

TERM = re.compile(r"<h5>\s*Current Terms End August 31,\s*(\d{4})\s*</h5>")
ENTRY = re.compile(r'^(?P<name>.+?)\s+(?P<d>\d{1,2})(?:st|nd|rd|th)\s+District\s+'
                   r'Seat\s+["“”]?(?P<s>[A-Z])["“”]?$')
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def _email(h6, name):
    first = name.split()[0].lower()
    sur = re.sub(r"[^a-z]", "", name.split()[-1].lower())
    for a in mailtos(h6):
        dom = a.rsplit("@", 1)[-1].lower()
        if not any(dom == d or dom.endswith("." + d) for d in DOMAINS):
            continue
        local = re.sub(r"[^a-z]", "", a.split("@", 1)[0].lower())
        if sur in local and (local.startswith(first) or local.startswith(first[:1] + sur)):
            return a
    return None


def parse(pages):
    page = pages[URLS[0]]
    term = TERM.search(page)
    if not term:
        raise ValueError("no 'Current Terms End August 31, YYYY' heading")
    if int(term.group(1)) < 2030:
        raise ValueError("the page's terms end in %s, before the 2026-2030 term" % term.group(1))
    end = page.find("</section>", term.end())
    if end < 0:
        raise ValueError("cannot find the end of the roster section")
    roster = page[term.end():end]
    districts, seen = {}, set()
    for h6 in re.findall(r"<h6\b[^>]*>(.*?)</h6>", roster, re.S):
        line = txt(h6)
        if not line:
            continue
        m = ENTRY.match(line)
        if not m:
            raise ValueError("a roster heading is not 'Name Nth District Seat \"X\"': %r" % line)
        name, d, s = m.group("name"), str(int(m.group("d"))), m.group("s")
        link = re.search(r"<a\b[^>]*>(.*?)</a>", h6, re.S)
        if link and txt(link.group(1)) and re.sub(r"\s+", " ", txt(link.group(1))) != name:
            raise ValueError("link text %r differs from the heading's name %r" % (txt(link.group(1)), name))
        if not NAME.match(name):
            raise ValueError("District %s Seat %s: %r is not a name" % (d, s, name))
        if (d, s) in seen:
            raise ValueError("District %s Seat %s appears twice" % (d, s))
        seen.add((d, s))
        districts.setdefault(d, []).append(member(name, seat=s, email=_email(h6, name)))
    return {"districts": districts, "atLarge": []}
