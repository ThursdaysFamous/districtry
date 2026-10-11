"""Marshall County elects 18 commissioners from 9 districts, two in each (the
ballot says "Vote For 2" in every district and names no seat, so no seat is
recorded).

The commission page (/county-commission, which is in the site's sitemap but
not its menu) is a run of "ItemList" posts. Each district is one
<article data-type="ItemList"> whose title reads "DISTRICT N", and each member
is one <div class="item"> inside it, whose description is a <br>-separated
block: name, street or P.O. box, town and ZIP, phone, and an e-mail link. A
member's district is the title of the article the item sits in; nothing is
read from order. An ItemList article whose title is not "DISTRICT N", a
district that appears twice, or an item whose first line is not a name raises.
The page's last article is a "Text" post (the commission's legal notice of
2026 meeting dates) and is not a district.

PRIVACY: every member's block carries a home street address or P.O. box, a
town and ZIP, and a personal phone number. None of those is read; only the
first line (the name) and the e-mail link are. Each block's e-mail link is a
percent-encoded mailto (%6d%77...@...) whose visible text is the plain
address; the two must agree. An address is kept only on marshallcountytn.gov
and only when it is the member's own: its local part must start with the
member's first initial and contain the surname (every one on the page does,
e.g. mwaggoner@, gosborne@). The page prints Geoffrey "Spanky" Osborne's
nickname in quotes and that is kept as printed. Photos carry no name (alt
text like "Img 7298 2") and are not read.

Currency: checked 2026-10-11 against the Marshall County Election Commission's
"Election Summary Report", 2026 State Primary and County General, 6 August
2026 (TNMARPG6, 8:27:45 PM, 10 of 10 precincts reported; the unofficial
election-night summary, the only results the county posts), linked as
"TNMARPG6_ELECTION_SUMMARY 2026.pdf" from marshallcountytn.gov/election-office
(/a/uploads/140504). In every district the two highest vote-getters are the
two names on this page: D1 Hugo Lopez 479, Mike Waggoner 415 (Chad Argo 294);
D2 Randy Perryman 522, Debbie (Hill) Gilbert 309; D3 Jeff Poarch 345, Landry
Murdock 302 (Shawn Hawkins 226, John McCullough 213, Anna Childress 187); D4
Ken Lee 474, Mickey King 415 (Jerry Williams 363); D5 Michael Sullivan 583,
Terry Dunnivant 413; D6 Jeff Moore 306, Shaun Ray Arndt 229 (Cory Burns 169,
David Reed 144); D7 Susan T. Hunter 189, Geoffrey Spanky Osborne 164 (Seth A.
Warf 142, Janna Green Augustine 135, Fletcher Thornberry 82); D8 Patty
Blalock-Parsons 377, James Hopkins 349; D9 Glen White 445, Nathan U Johnson
III 436 (James "Pugs" Johnson 319). The page's short forms (Patty Parsons,
Shaun Arndt, Nathan Johnson, Susan Hunter, Debbie Gilbert) are the ballot's
names."""
import re
from urllib.parse import unquote
from ._common import txt, member, district_number

COUNTY = "Marshall"; FIPS = "117"
DOMAINS = ("marshallcountytn.gov",)
URLS = ["https://www.marshallcountytn.gov/county-commission"]
SEATS = {str(i): 2 for i in range(1, 10)}
AT_LARGE = 0

TITLE_RE = re.compile(r'<div class="post--title[^"]*">(.*?)</div>', re.S)
NAME = re.compile(r'^[A-Z][A-Za-z.\'’" -]+$')
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _name_parts(name):
    words = [w for w in re.split(r"\s+", re.sub(r'"[^"]*"', " ", name)) if w]
    while words and words[-1].lower().strip(".,") in SUFFIX:
        words.pop()
    if len(words) < 2:
        raise ValueError("%r is not a first and last name" % name)
    return words[0][0].lower(), re.sub(r"[^a-z]", "", words[-1].lower())


def _email(item, name):
    links = re.findall(r'<a\b[^>]*href="mailto:([^"?]+)[^"]*"[^>]*>(.*?)</a>', item, re.S | re.I)
    if not links:
        return None
    if len(links) > 1:
        raise ValueError("%r: %d e-mail links in one block" % (name, len(links)))
    href, text = unquote(links[0][0]).strip(), txt(links[0][1])
    if href.lower() != text.lower():
        raise ValueError("%r: mailto %r differs from its text %r" % (name, href, text))
    dom = href.rsplit("@", 1)[-1].lower()
    if not any(dom == d or dom.endswith("." + d) for d in DOMAINS):
        return None
    local = re.sub(r"[^a-z]", "", href.split("@", 1)[0].lower())
    initial, surname = _name_parts(name)
    if not (local.startswith(initial) and surname in local):
        raise ValueError("%r: county address %r does not look like the member's" % (name, href))
    return href


def parse(pages):
    page = pages[URLS[0]]
    main = re.search(r"<main\b(.*?)</main>", page, re.S)
    if not main:
        raise ValueError("no <main> element")
    districts = {}
    for art in re.split(r"<article\b", main.group(1))[1:]:
        art = art.split("</article>", 1)[0]
        kind = re.search(r'data-type="(\w+)"', art[:600])
        if not kind or kind.group(1) != "ItemList":
            continue
        title = TITLE_RE.search(art)
        label = txt(title.group(1)) if title else ""
        m = re.match(r"^DISTRICT\s+(\d{1,2})$", label, re.I)
        if not m or district_number(label) != int(m.group(1)):
            raise ValueError("an item list titled %r is not a district" % label)
        d = m.group(1)
        if d in districts:
            raise ValueError("District %s appears twice" % d)
        found = []
        for item in re.split(r'<div class="item">', art)[1:]:
            item = re.sub(r"<figure\b.*?</figure>", " ", item, flags=re.S)
            desc = re.search(r'<div class="item--description[^"]*">(.*)', item, re.S)
            if not desc:
                raise ValueError("District %s: an item with no description" % d)
            segs = [txt(s) for s in re.split(r"<br\s*/?>", desc.group(1), flags=re.I)]
            segs = [s for s in segs if s]
            if not segs:
                raise ValueError("District %s: an empty item" % d)
            name = segs[0]
            if not NAME.match(name):
                raise ValueError("District %s: first line %r is not a name" % (d, name))
            found.append(member(name, email=_email(desc.group(1), name)))
        if not found:
            raise ValueError("District %s has no members" % d)
        districts[d] = found
    if not districts:
        raise ValueError("no DISTRICT item lists on the page")
    return {"districts": districts, "atLarge": []}
