"""Tipton County elects 18 commissioners, two from each of 9 districts. The
ballot and the county call no seat by a letter or number, so no seat is
recorded. The County Executive chairs the body ("William "Billy" Daugherty,
County Executive - Chairman") and holds no commission seat; he is not
recorded.

The Legislative Body page (Revize CMS) is headed "2026-2030 Legislative
Body" and lists the commission in two paragraphs under the headings "Finance
& Administration Committee" and "General Welfare & Public Works Committees"
(until at least 2026-10-14 "Finance Committee" and "General Welfare / Public
Works Committees"; renamed by 2026-10-17, same members). Each paragraph
holds one member per district, 1 to 9, each entry opening with a bold
italic "District N" label followed by the member's photo and the member's
name on its own line; the district is read from that label, never from
order. Each committee paragraph must name every district 1..9 exactly once,
and the photo's alt text must carry the same surname as the name line, so an
entry whose label or photo drifted raises.

Names are kept as printed, nicknames in parentheses included ("James (Jimbo)
C. Adkins", "James (Lamont) Sneed"). Three entries end in a committee note,
"(Chairwoman - Pending Appointment)" ("Chairman" until at least 2026-10-14),
"(Chairman - Public Works - Pending Appointment)" and "(Chairman - General
Welfare - Pending Appointment)"; a committee chairmanship is not a commission
office, and the page says it is pending, so the note is cut off the name and
nothing is recorded for it. The one commission office on the page, "Walker
Adams, District 4 - Chairman Pro Tempore" in the page header, is recorded on
the District 4 member of that name; the parse raises if the header names a
member the district does not list.

PRIVACY: almost every entry prints a home street address, town and ZIP, and
many print a phone number (Courtney Fee's two are labelled "(cell)" and
"(home)") and a personal e-mail (bellsouth, live, gmail, aol, yahoo, outlook,
a business domain). Under Adam's ruling of 2026-10-17 that a number a
government publishes beside an official ships whosever line it is, the numbers
are read, the first into `phone` and a second into `phonesExtra`, with the
page's label kept ("cell 901-...", "home 901-..."). Only telephone-shaped
numbers are read; the street address, town and ZIP are never read. The e-mail
address an entry prints is recorded on that entry's member, under Adam's
ruling of the same day that an e-mail address a government page prints beside
an official ships too; where an entry prints two, the first is kept. Two
entries print an address at tipton-county.com, which is the Tipton County
SCHOOLS website (read 2026-10-11: an Edlio school-district site, "Tipton County
serves students ... in Covington, TN"), not the county government's
(tiptonco.com); one of them prints it as the member's only address and it is
kept as printed, the other prints a personal address first.

Names: the page prints "Shelia Barlow"; the Election Commission's officials
list prints "SHEILA BARLOW". The page's spelling is kept.

Currency: the Tipton County Election Commission's page links "August 6, 2026
State Primary / County General Election Results"
(www.tiptonco.com/files/election_results/index.html), but that link
redirects to the county's file host cms4files1.revize.com
(/tiptoncounty/files/election_results/index.html), whose robots.txt allows
only some file types (".pdf" among them) and refuses that page under
"Disallow: /", so the results were NOT read and no file name under it was
guessed. No other results
were found on a government host (the commission's "View Historical Election
Results" link is the Secretary of State's results page, which answered
HTTP 403 to this project's client and was not read). Fallback evidence, both on the county's own hosts: this
page's own heading "2026-2030 Legislative Body"; and the Election
Commission's "Elected and Appointed Officials of Tipton County"
(Site Setup/document_center/ELECTED_APPOINTED_OFFICIALS.pdf, served from
cms4files1.revize.com, created 14 September 2026), which lists the 18
commissioners by district, each "4 YEAR TERM, RUNS AGAIN 2030" - the same
18 people in the same districts as this page (checked 2026-10-11; spellings
differ only by middle names and initials, plus Shelia/Sheila above)."""
import re
from ._common import txt, member, district_number, read_phones, read_emails, member_email

COUNTY = "Tipton"; FIPS = "167"
DOMAINS = ("tiptonco.com",)
URLS = ["https://tiptonco.com/government/legislative_body/index.php"]
SEATS = {str(i): 2 for i in range(1, 10)}
AT_LARGE = 0

COMMITTEES = ("Finance & Administration Committee", "General Welfare & Public Works Committees")
LABEL = re.compile(r"<strong>\s*<em>\s*(District\s+\d{1,2})\s*</em>\s*</strong>")
NOTE = re.compile(r"\s*\((Chair(?:man|woman)\b[^)]*Pending Appointment)\)$")
NAME = re.compile(r"^[A-Z][A-Za-z.'’() -]+$")
HEADER_ROLE = re.compile(r"^(?P<name>[^,]+),\s*District\s+(?P<d>\d{1,2})\s*-\s*(?P<role>.+)$")
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def surname(s):
    words = [w for w in re.split(r"[\s,]+", re.sub(r"\([^)]*\)", " ", s)) if w]
    while words and words[-1].lower().strip(".") in SUFFIX:
        words.pop()
    return words[-1].lower() if words else ""


def read_committee(title, para):
    pieces = LABEL.split(para)
    if txt(pieces[0]):
        raise ValueError("%s: text before the first District label: %r" % (title, txt(pieces[0])[:80]))
    out = {}
    for label, body in zip(pieces[1::2], pieces[2::2]):
        d = str(district_number(label))
        if d in out:
            raise ValueError("%s: District %s appears twice" % (title, d))
        alt = re.findall(r'<img\b[^>]*\balt="([^"]*)"', body)
        segs = [txt(x) for x in re.split(r"<br\s*/?>", body, flags=re.I)]
        segs = [x for x in segs if x]
        if len(alt) != 1 or not segs:
            raise ValueError("%s District %s: expected one photo and a name" % (title, d))
        name = NOTE.sub("", segs[0]).strip()
        if "(" in name and not re.fullmatch(r"[^()]*\([A-Z][a-z]+\)[^()]*", name):
            raise ValueError("%s District %s: unexpected note in %r" % (title, d, segs[0]))
        if not NAME.match(name):
            raise ValueError("%s District %s: %r does not look like a name" % (title, d, segs[0]))
        if surname(alt[0]) != surname(name):
            raise ValueError("%s District %s: photo %r does not match name %r" % (title, d, alt[0], name))
        out[d] = (name, read_phones(body), member_email(read_emails(body), DOMAINS))
    if set(out) != {str(i) for i in range(1, 10)}:
        raise ValueError("%s names districts %s, not 1..9" % (title, sorted(out, key=int)))
    return out


def parse(pages):
    page = pages[URLS[0]]
    post = re.search(r'<div id="post"[^>]*>(.*?)</main>', page, re.S)
    if not post or "2026-2030 Legislative Body" not in post.group(1):
        raise ValueError("no '2026-2030 Legislative Body' content on the page")
    body = post.group(1)
    heads = list(re.finditer(r"<h5\b[^>]*>(.*?)</h5>", body, re.S))
    if [txt(h.group(1)) for h in heads] != list(COMMITTEES):
        raise ValueError("committee headings are %r" % [txt(h.group(1)) for h in heads])
    districts = {}
    for h in heads:
        para = re.match(r"\s*<p>(.*?)</p>", body[h.end():], re.S)
        if not para:
            raise ValueError("no paragraph under %r" % txt(h.group(1)))
        for d, (name, phones, email) in read_committee(txt(h.group(1)), para.group(1)).items():
            districts.setdefault(d, []).append(member(name, phones=phones, email=email))

    # Commission offices printed in the header, as "Name, District N - Office".
    intro = body[:heads[0].start()]
    for line in (txt(x) for x in re.split(r"<br\s*/?>", intro, flags=re.I)):
        m = HEADER_ROLE.match(line)
        if not m:
            continue
        role = m.group("role").strip()
        if not re.fullmatch(r"Chairman Pro Tempore|Vice[- ]Chairman", role):
            raise ValueError("header line %r: %r is not an office this parser knows" % (line, role))
        hits = [r for r in districts.get(m.group("d"), []) if r["name"].rstrip() == m.group("name").strip()]
        if len(hits) != 1:
            raise ValueError("header names %r in District %s, who is not listed there"
                             % (m.group("name"), m.group("d")))
        hits[0]["role"] = role
    return {"districts": districts, "atLarge": []}
