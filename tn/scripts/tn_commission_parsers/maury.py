"""Maury County elects 22 commissioners, two from each of 11 districts; the
two top vote-getters in a district win, so there are no seat letters and none
is recorded. The county's Commissioners page (CivicPlus) says so itself
("twenty-two members two of which are elected from each of the 11 districts").

The page is one tabbed widget. Each tab button carries data-tabname="District
N", and each tab panel names the button that opens it in aria-labelledby, so a
panel's district is read from its own button, never from the panels' order.
Inside a panel every member is a link to that member's county profile page
(/<id>/<Slug>) whose text is the name; most sit in an <h3>, but District 9's
second member (Kevin Markham) is a bare link inside a <p>, so the parser reads
every text link to a profile page in the panel rather than the headings. Photo
links carry no text and are skipped; several of them still point at a former
member's slug on the same page id (/169/Pam-Huffman under Tim Holt,
/172/Eric-Previti under Wayne Romesburg), so the profile link recorded is the
one on the name, never the photo's. Each panel must hold exactly two names and
every district 1..11 exactly one panel, or the parse raises.

PRIVACY: the roster page carries names and photos only. The profile pages it
links print each member's home street address, which is never read, and a
phone number. Under Adam's ruling of 2026-10-17 that a number a government
publishes beside an official ships whosever line it is, the scraper reads each
profile page (member_pages) through the same robots.txt check and pacing as
the roster page. The number is read from the one paragraph under the page's
"District N Commissioner" heading, and only when the page's <h1> names the
roster's member and that heading names the roster's district; otherwise that
member's number is withheld with a note. On 17 October 2026 that
paragraph held "Phone: <number>" on 21 pages and the bare number on Danny
Grooms's. The county's main number, 931-381-3690, which every page prints in
its "Contact Us" box, is in OFFICE_LINES.

Each profile page also prints, under the same heading and before the next
one, a visible link "Email <member's name>" (or the bare name, or "Email:
<name>"), which opens a maurycounty-tn.gov address for 18 members and a
personal one for two (charter.net, outlook.com). The address that link opens
is recorded, under Adam's choice of 2026-10-17 that a personal address a
government page prints beside an official is shown ("E-mails too"), and only
a link whose text carries the member's surname is read. Beside the phone
line, 21 of the 22 pages also carry an empty mailto link, the same address on
every one, and Jerry Strahan's a second empty one: a reader never sees them,
and they are never read. Greg Combs's link opens an address whose domain runs
the county's into "gmail.com" (".govgmail.com"), a slip no mail reaches, so no
address is recorded for him; Sam Barnes's and Steven Burford's "Email" lines
link nowhere, so none is recorded for them either.

Currency: checked 2026-10-11 against the Maury County Election Commission's
"Summary Results Report 2026 AUG_MAURY_ST_FED_PRIM_GEN Aug 6, 2026"
(maurycounty-tn.gov DocumentCenter/View/7437/Aug26-Summary-Report, marked
UNOFFICIAL RESULTS, generated 08/06/2026 8:53 PM with every precinct
reporting in every commission race; no certified version was found on a
county host). In all 11 districts the two names on this page are the two top
vote-getters, and no race was close enough for certification to change it
(the narrowest was District 10, where Greg Combs took the second seat with 566
votes to Tommy Wolaver's 453). Ballot
spellings differ only as Patti/Patricia Hollinsworth, Connie B. Green, Mike
Kuzawinski Jr, Missy Smith Phillips and T. Kevin Markham. The two profile
pages read while writing this (Tim Holt, District 1; Winston B. Harlan,
District 3, both new in 2026) say "Term: 2026 to Present"."""
import re
from ._common import (txt, member, district_number, page_field, add_phones, same_person, Withheld,
                      member_email, address_of, MAILTO_A, MAILTO_HREF)

COUNTY = "Maury"; FIPS = "119"
DOMAINS = ("maurycounty-tn.gov",)
URLS = ["https://www.maurycounty-tn.gov/168/Commissioners"]
SEATS = {str(i): 2 for i in range(1, 12)}
AT_LARGE = 0
# The county's main number, in the "Contact Us" box on every page of its site.
OFFICE_LINES = ("931-381-3690",)

TAB = re.compile(r'<a href="#(tab[0-9a-f-]+_\d+)" class="tabButton" id="(tabBtn[0-9a-f-]+_\d+)"[^>]*>'
                 r'\s*<span class="tabName[^"]*"[^>]*data-tabname="([^"]*)"')
PANEL = re.compile(r'<div class="tabbedWidget cpTabPanel[^"]*"[^>]*\bid="(tab[0-9a-f-]+_\d+)"'
                   r'[^>]*aria-labelledby="(tabBtn[0-9a-f-]+_\d+)"[^>]*>')
LINK = re.compile(r'<a href="(/\d+/[^"]*)"[^>]*>(.*?)</a>', re.S)
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")
SEAT_HEAD = re.compile(r'<h2 class="subhead1[^"]*">\s*(District \d{1,2} Commissioner)\s*</h2>'
                       r'\s*(<p\b.*?</p>)', re.S)
MAILTO = re.compile(r'<a\b[^>]*href="mailto:[^"]*"[^>]*>.*?</a>', re.S | re.I)
SEAT_REGION = re.compile(r'<h2 class="subhead1[^"]*">\s*District \d{1,2} Commissioner\s*</h2>'
                         r'(.*?)(?=<h[1-6]\b|</div>)', re.S)


def _roster(pages):
    """The roster page alone: {district: [member records]}, phones not read."""
    page = pages[URLS[0]]
    buttons = {}
    for panel_id, btn_id, label in TAB.findall(page):
        if btn_id in buttons and buttons[btn_id][1] != label:
            raise ValueError("tab button %s labelled two ways" % btn_id)
        buttons[btn_id] = (panel_id, label)
    panels = list(PANEL.finditer(page))
    if not panels:
        raise ValueError("no tab panels on the page")
    districts = {}
    for k, pm in enumerate(panels):
        panel_id, btn_id = pm.group(1), pm.group(2)
        if btn_id not in buttons or buttons[btn_id][0] != panel_id:
            raise ValueError("panel %s is not the one its button %s opens" % (panel_id, btn_id))
        label = buttons[btn_id][1]
        d = district_number(label)
        if not d or label.strip() != "District %d" % d:
            raise ValueError("tab %r is not 'District N'" % label)
        stop = page.find("<script", pm.end())
        if stop < 0:
            raise ValueError("cannot find where panel %s ends" % panel_id)
        body = page[pm.end():stop]
        names = []
        for href, inner in LINK.findall(body):
            name = txt(inner)
            if not name:
                continue                      # a photo link
            if not NAME.match(name):
                raise ValueError("District %d: link text %r is not a name" % (d, name))
            if name in [n for n, _ in names]:
                continue
            names.append((name, "https://www.maurycounty-tn.gov" + href))
        if str(d) in districts:
            raise ValueError("District %d has two panels" % d)
        if len(names) != 2:
            raise ValueError("District %d panel names %d people, the county elects 2: %s"
                             % (d, len(names), [n for n, _ in names]))
        districts[str(d)] = [member(n, profileUrl=u) for n, u in names]
    return districts


def member_pages(pages):
    """The profile pages the roster page links by name, one per member, on
    the county's own host: the scraper reads them for parse()."""
    return [r["profileUrl"] for ms in _roster(pages).values() for r in ms]


def _not_theirs(page, name, d):
    """A Withheld reason when a profile page does not plainly name this member
    in its <h1> and this district in its one "District N Commissioner"
    heading, else None."""
    heads = [txt(h) for h in re.findall(r"<h1\b[^>]*>(.*?)</h1>", page, re.S)]
    if len(heads) != 1 or not (same_person(heads[0], name) and same_person(name, heads[0])):
        return Withheld("the profile page's heading does not name this member")
    blocks = SEAT_HEAD.findall(page)
    if len(blocks) != 1 or district_number(blocks[0][0]) != int(d):
        return Withheld("the profile page does not name this member's district once")
    return None


def page_email(page, name, d):
    """The address the visible e-mail link under the profile page's "District
    N Commissioner" heading opens (up to the next heading), read only from a
    link whose text carries the member's surname; an empty link is never seen
    and never read. A Withheld reason when the page does not plainly name this
    member and district."""
    why = _not_theirs(page, name, d)
    if why:
        return why
    regions = SEAT_REGION.findall(page)
    if len(regions) != 1:
        return Withheld("the profile page's district heading is not followed by one region")
    sur = re.sub(r"[^a-z]", "", name.split()[-1].lower())
    addrs = []
    for a in MAILTO_A.finditer(regions[0]):
        href = MAILTO_HREF.search(a.group(1))
        shown = re.sub(r"[^a-z]", "", txt(a.group(2)).lower())
        if href and sur and sur in shown:
            addrs.append(address_of(href.group(1)))
    return member_email(addrs, DOMAINS)


def page_phones(page, name, d):
    """The number in the paragraph under a profile page's "District N
    Commissioner" heading, or a Withheld reason when the page does not plainly
    name this member and district. The e-mail links in that paragraph and its
    "Email" line are left out; nothing else on the page is read."""
    why = _not_theirs(page, name, d)
    if why:
        return why
    blocks = SEAT_HEAD.findall(page)
    para = MAILTO.sub(" ", blocks[0][1])
    fields = [f for f in re.split(r"<br\b[^>]*>", para, flags=re.I) if txt(f)]
    fields = [f for f in fields if not re.match(r"E-?mail\b", txt(f), re.I)]
    if not fields:
        return []
    if len(fields) > 1:
        return Withheld("the paragraph under the district heading holds %d lines "
                        "besides the e-mail" % len(fields))
    return page_field(fields[0])


def parse(pages):
    districts = _roster(pages)
    for d, ms in districts.items():
        out = []
        for r in ms:
            page = pages[r["profileUrl"]]
            mail = page_email(page, r["name"], d)
            r = dict(r, **({"_email_withheld": str(mail)} if isinstance(mail, Withheld)
                           else {"email": mail} if mail else {}))
            out.append(add_phones(r, page_phones(page, r["name"], d)))
        districts[d] = out
    return {"districts": districts, "atLarge": []}
