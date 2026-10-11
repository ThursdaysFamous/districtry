"""Scott County elects 14 commissioners, two from each of its 7 civil
districts ("a 14-member board of commissioners, with two elected
representatives of each of the county's seven civil districts", the page
says). No seat is called by a letter or number, so no seat is recorded.
(scottcounty.com is Scott County, Tennessee's own site, whatever the generic
name suggests.)

The board page (WordPress) has an <h2> "Commissioners" followed by short
paragraphs in which each line reads "<Name>, Nth District", the name linked
to a commissioner page for nine of the fourteen. Each name is paired with the
district on its own line; nothing is read from order. A line that is not
"<Name>, Nth District" raises, and the page's sentence giving 14 members, two
in each of seven districts, must still stand.

Names are kept as printed, nicknames in their quotes ("David "Blue" Day",
"Allen "Ladd" Phillips").

profileUrl: the commissioner page a name links to, kept only when it is on
scottcounty.com and its address carries the member's given name and
surname (Kelly Chitwood's is "commissioner-kelly-posey-chitwood"; two members
are Keetons, so the surname alone would not do); those pages were not read.
A link that does not carry both raises.

PRIVACY: the page prints no member address, phone or e-mail; the commission
meeting address on it is the county office building's and is not read.

Currency: NOT checked against results. No results of the 6 August 2026
election were found on a government host: the Scott County Election
Commission's site (www.votescotttn.gov, Google Sites) links no results from
its home page or its navigation, a search of scottcounty.com's media library
for everything uploaded since 1 August 2026 found only numbered PDFs, an
agenda for 17 August 2026 and three photographs, and the county's Meeting
Agendas page lists nothing after 17 August 2026; the state's results site
answers this project HTTP 403 and was not tried. Evidence used, read
2026-10-11: (1) the Election Commission's own "County and Constitutional"
officials page, which lists the Board of Commissioners "(4 year term; next
election: August 2030)" BY DISTRICT and names the same fourteen people in
the same districts as this page (spelled "Daiv (Blue) Day", "Allen L
Phillips", "Taylor Buttram Stephens", "Joyce Potter Keeton", "Kelly Posey
Chitwood", "Zack Strunk"); Google Sites dates that page's last update
2026-08-18, twelve days after the election and before the term began; and
(2) this page, which WordPress dates 2026-09-03 (after the term began) and
which says "The next election of County Commissioners will be August 2030".
What this does NOT establish: no results were compared, and no document
after 1 September 2026 shows these fourteen seated (no minutes or agenda of
the new commission was found)."""
import re
from ._common import txt, member, district_number

COUNTY = "Scott"; FIPS = "151"
DOMAINS = ("scottcounty.com",)
URLS = ["https://scottcounty.com/government/board-of-county-commissioners/"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0

HEAD = "<h2>Commissioners</h2>"
LINE_RE = re.compile(r"^(?P<name>.+?), (?P<d>(\d{1,2})(?:st|nd|rd|th) District)$")
NAME_RE = re.compile(r"^[A-Z][A-Za-z.'’“”\"() -]+$")
LINK_RE = re.compile(r'<a\s+href="(?P<u>[^"]+)"[^>]*>(?P<t>.*?)</a>', re.S)
SIZE_RE = re.compile(r"14-member board of commissioners, with two elected representatives "
                     r"of each of the county.s seven civil districts")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _surname(name):
    words = [w for w in re.sub(r"[“\"][^”\"]*[”\"]", " ", name).split() if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def _profile(name, raw):
    links = LINK_RE.findall(raw)
    if not links:
        return None
    if len(links) != 1:
        raise ValueError("%r: more than one link on its line" % name)
    url = links[0][0]
    host = re.match(r"https?://(?:www\.)?([^/]+)/", url)
    if not host or host.group(1).lower() not in DOMAINS:
        return None
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    given = re.sub(r"[^a-z]", "", name.split()[0].lower())
    flat = slug.replace("-", "")
    if not slug.startswith("commissioner-") or _surname(name) not in flat or given not in flat:
        raise ValueError("%r links to %r, which is not that member's page" % (name, url))
    return url


def parse(pages):
    page = pages[URLS[0]]
    if not SIZE_RE.search(txt(page)):
        raise ValueError("the page no longer says 14 members, two from each of seven districts")
    s = page.find(HEAD)
    if s < 0 or page.find(HEAD, s + 1) >= 0:
        raise ValueError("the page does not have exactly one 'Commissioners' heading")
    e = page.find("</div>", s)
    section = page[s + len(HEAD):e]
    if re.search(r"<h[1-6]\b", section):
        raise ValueError("another heading sits inside the commissioners list")
    districts = {}
    for para in re.findall(r"<p\b[^>]*>(.*?)</p>", section, re.S):
        for raw in re.split(r"<br\s*/?>", para, flags=re.I):
            line = txt(raw)
            if not line:
                continue
            m = LINE_RE.match(line)
            if not m:
                raise ValueError("a line is not '<Name>, Nth District': %r" % line)
            name = m.group("name").strip()
            if not NAME_RE.match(name) or re.search(r"\bvacan", name, re.I):
                raise ValueError("%r does not look like a name" % name)
            d = str(district_number(m.group("d")))
            if d != m.group(3).lstrip("0"):
                raise ValueError("%r read two ways" % m.group("d"))
            districts.setdefault(d, []).append(member(name, profileUrl=_profile(name, raw)))
    if not districts:
        raise ValueError("no '<Name>, Nth District' lines under Commissioners")
    if txt(re.sub(r"<p\b[^>]*>.*?</p>", " ", section, flags=re.S)):
        raise ValueError("text outside the paragraphs of the commissioners list")
    return {"districts": districts, "atLarge": []}
