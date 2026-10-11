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
links (not read here) print each member's home street address and a phone
number; neither is recorded. They also carry a maurycounty-tn.gov e-mail per
member, but reading 22 more pages for it is not worth the requests, so no
e-mail is recorded.

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
from ._common import txt, member, district_number

COUNTY = "Maury"; FIPS = "119"
DOMAINS = ("maurycounty-tn.gov",)
URLS = ["https://www.maurycounty-tn.gov/168/Commissioners"]
SEATS = {str(i): 2 for i in range(1, 12)}
AT_LARGE = 0

TAB = re.compile(r'<a href="#(tab[0-9a-f-]+_\d+)" class="tabButton" id="(tabBtn[0-9a-f-]+_\d+)"[^>]*>'
                 r'\s*<span class="tabName[^"]*"[^>]*data-tabname="([^"]*)"')
PANEL = re.compile(r'<div class="tabbedWidget cpTabPanel[^"]*"[^>]*\bid="(tab[0-9a-f-]+_\d+)"'
                   r'[^>]*aria-labelledby="(tabBtn[0-9a-f-]+_\d+)"[^>]*>')
LINK = re.compile(r'<a href="(/\d+/[^"]*)"[^>]*>(.*?)</a>', re.S)
NAME = re.compile(r"^[A-Z][A-Za-z.'’ -]+$")


def parse(pages):
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
    return {"districts": districts, "atLarge": []}
