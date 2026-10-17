"""Warren County elects 24 commissioners, two from each of 12 districts (every
district race on the 6 August 2026 ballot was "VOTE FOR 2"; the county page
says "composed of 24 members, with two members elected from each of the
county's 12 districts"). No seat or position inside a district is published.

Two county pages are read. The roster is the "Who is my Commissioner?" page
(commissioners.php), headed "2026-2029 County Commissioners (alphabetically by
last name)": one entry per member, separated by <br>, each a name line, then a
line "District N" (one entry splits it across a <span>, which the line reading
joins), then usually a phone line and an "Email" mailto link. A member is the
name on the line directly above their own "District N" line, inside the same
entry, so nothing is read from the alphabetical order (which this page does
not keep exactly). Any line that is not the heading, a name, a district, a
phone or "Email" raises. A member's phone is the phone line inside that
member's own entry.

The County Commission page (index.php) is read as a check and for the
commission's officers. Its "Commissioners By District" table gives each
district a row whose first cell reads "District N:" beside the first member,
and a second row with a blank first cell for the second member; the set of
(district, name) pairs it gives must equal the roster's, or the parse is
refused. Its officer lines ("<strong>Title</strong><br>Name") give the
Chairman Pro Tem (Scott Rubley) and the Parliamentarian (Michael Bell), and
each is recorded as that member's role. The Chairman of Commission is the
County Executive (Terry Bell), who is not a commission seat and is not
recorded; an officer line naming anyone who is neither a member nor the
County Executive raises.

PRIVACY: under Adam's ruling of 2026-10-17 that a number a government
publishes beside an official ships whosever line it is, the number under an
entry is read into `phone` exactly as printed. Most of them are seven digits
with no area code, and no area code is added: Warren County is in 931, but a
mobile can be issued anywhere and a guessed prefix reaches a stranger. The
gap record `warren-commission-phone-area-code` says so. Five members' entries
print the county's main number (473-2505, once as 931-473-2505) instead; it
and the two other county lines in the page footer (the courthouse and animal
control) are OFFICE_LINES and stay off every member. Only telephone-shaped
numbers are read; the page prints no member address. An e-mail address on
warrencountytn.gov is kept only when its local part starts with the member's
first initial and contains their surname; an address on any other domain that
an entry links is kept as printed, under Adam's ruling of 2026-10-17 that an
e-mail address a government page prints beside an official ships too (on
17 October 2026 every link was on the county's domain). Four members' "Email"
links point at someone else's address (Stephen Potter -> shelton@, James Zahn
-> jhines@, Caleb Graves -> gmartin@, Traye Cope -> dsmith@), and three of
those entries sit in the alphabetical list where the address's surname would
sort (Hines, Martin, Smith), not their own, which reads as entries renamed
for the new term whose links were left as they were. Those four are not recorded, which leaves
19 e-mails; Ken Martin has no e-mail link.

Currency: checked 2026-10-11 against the Warren County Election Commission's
"OFFICIAL RESULTS OF THE 8/6/2026 ELECTION" (Election Summary Report with
provisionals added, printed 8/12/2026, linked from the county's own Election
Commission page and served by its site vendor, cms3.revize.com/revize/
warrencounty/): the two winners in every district are the 24 names here. The
ballot carries longer forms of four names: Ronald S. Lee (D1, "Ron Lee"),
Christopher L. Rippy (D3), James A. Zahn (D4) and Tommy G Savage (D7); the
ballot's "Steve Glenn" is the page's "Steve M. Glenn"."""
import re
from ._common import (txt, member, district_number, read_phones, read_emails,
                      member_email, on_domains, Withheld)

COUNTY = "Warren"; FIPS = "177"
DOMAINS = ("warrencountytn.gov",)
URLS = [
    "https://www.warrencountytn.gov/government/county_commission/commissioners.php",
    "https://www.warrencountytn.gov/government/county_commission/index.php",
]
SEATS = {str(i): 2 for i in range(1, 13)}
AT_LARGE = 0
# The county's main number (the Administrative Building), the courthouse and
# animal control, as the page footer prints them.
OFFICE_LINES = ("931-473-2505", "931-473-2373", "931-507-3647")

HEADING = re.compile(r"^\d{4}-\d{4} County Commissioners\b")
DISTRICT = re.compile(r"^District\s*(\d{1,2})$")
PHONE = re.compile(r"^(?:\d{3}-)?\d{3}-\d{4}$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
ROLES = {"chairman pro tem": "Chairman Pro Tem", "chairman pro tempore": "Chairman Pro Tempore",
         "vice chairman": "Vice Chairman", "parliamentarian": "Parliamentarian"}
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _post(page, url):
    s = page.find('<div id="post"')
    e = page.find("</main>", s)
    if s < 0 or e < 0:
        raise ValueError("%s: the page's post region was not found" % url)
    return page[s:e]


def _key(name):
    return re.sub(r"\s+", " ", name).strip().casefold()


def _surname(name):
    words = [w for w in re.split(r"[\s,]+", name) if w]
    while words and words[-1].lower().strip(".") in SUFFIX:
        words.pop()
    return re.sub(r"[^a-z]", "", words[-1].lower()) if words else ""


def _roster(page):
    raw = [seg for seg in re.split(r"<br\b[^>]*>", _post(page, URLS[0]), flags=re.I)]
    segs = [(txt(s), s) for s in raw]
    segs = [(t, s) for t, s in segs if t]
    if not segs or not HEADING.match(segs[0][0]):
        raise ValueError("the roster does not open with its 'YYYY-YYYY County Commissioners' heading")
    names = []                                  # index of each entry's name line
    for i, (t, _) in enumerate(segs):
        m = DISTRICT.match(t)
        if m:
            above = segs[i - 1][0] if i else ""
            if not NAME.match(above) or above == "Email":
                raise ValueError("'District %s' has no name line above it" % m.group(1))
            names.append((i - 1, m.group(1)))
    named = {i for i, _ in names}
    for i, (t, _) in enumerate(segs[1:], 1):
        if i in named or DISTRICT.match(t) or PHONE.match(t) or t == "Email":
            continue
        raise ValueError("an unexpected line on the roster: %r" % t)
    entries = []
    for k, (i, d) in enumerate(names):
        stop = names[k + 1][0] if k + 1 < len(names) else len(segs)
        name = segs[i][0]
        sur, first = _surname(name), name[:1].lower()
        mails = read_emails("".join(s for _, s in segs[i:stop]))
        county = [] if isinstance(mails, Withheld) else [a for a in mails if on_domains(a, DOMAINS)]
        if county:
            # A county mailbox not named for this member is the entry's
            # predecessor's (see above), and no address of the entry is kept.
            own = [a for a in county if sur and sur in a.lower().split("@")[0]
                   and a.lower().startswith(first)]
            email = own[0] if own else None
        else:
            email = member_email(mails, DOMAINS)
        tel = [s for t, s in segs[i:stop] if PHONE.match(t)]
        phones = read_phones("<br>".join(tel), strict=True) if tel else None
        entries.append((d, name, email, phones))
    return entries


def _by_district(page):
    """index.php's table: {(district, name key)}; a blank first cell continues
    the district named in the row above it, which is how the table is drawn."""
    post = _post(page, URLS[1])
    pairs, current = set(), None
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", post, re.S):
        cells = [txt(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) != 2 or not any(cells):
            continue
        if cells[0]:
            d = district_number(cells[0])
            if not d or not cells[0].startswith("District"):
                raise ValueError("by-district table row %r" % cells)
            current = str(d)
        if current is None or not cells[1]:
            raise ValueError("by-district table row %r has no district or no name" % cells)
        pairs.add((current, _key(cells[1])))
    return pairs, post


def parse(pages):
    entries = _roster(pages[URLS[0]])
    pairs, post = _by_district(pages[URLS[1]])
    roster = {(d, _key(n)) for d, n, _, _ in entries}
    if len(roster) != len(entries):
        raise ValueError("a member is listed twice on the roster")
    if roster != pairs:
        raise ValueError("the roster and the by-district table disagree: %s / %s"
                         % (sorted(roster - pairs), sorted(pairs - roster)))
    officers = {}
    for title, name in re.findall(r"<strong>\s*([^<]+?)\s*</strong>(?:\s|&nbsp;)*<br\s*/?>\s*([^<]+)", post):
        officers.setdefault(_key(txt(title)), []).append(txt(name))
    executive = {_key(n) for n in officers.pop("county executive", [])}
    by_name = {_key(n): n for _, n, _, _ in entries}
    roles = {}
    for title, names in officers.items():
        for n in names:
            if title == "chairman of commission":
                if _key(n) in executive:
                    continue                   # the County Executive chairs; not a seat
                role = "Chairman"
            elif title in ROLES:
                role = ROLES[title]
            else:
                continue                       # a heading, not an office
            if _key(n) not in by_name:
                raise ValueError("%s %r is not a commissioner on the roster" % (role, n))
            if _key(n) in roles:
                raise ValueError("%r holds two offices" % n)
            roles[_key(n)] = role
    districts = {}
    for d, name, email, phones in entries:
        districts.setdefault(d, []).append(
            member(name, role=roles.get(_key(name)), email=email, phones=phones))
    return {"districts": districts, "atLarge": []}
