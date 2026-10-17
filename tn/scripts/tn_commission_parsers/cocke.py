"""Cocke County elects 14 commissioners, two from each of 7 districts, each to
a numbered post ("District 1 Post 1", "District 1 Post 2"), which the ballot
uses as well; the post is recorded as the seat ("Post 1", "Post 2").

The Legislative Body page (Squarespace) has a bold line "Cocke County
Commissioners Information" and then three text blocks in which every seat is
a bold paragraph "District N Post M", the member's name in the next
paragraph, and that member's phone and/or e-mail in the paragraphs after it.
Each name is paired with the "District N Post M" line directly above it;
nothing is read from order. A paragraph under a seat heading that is neither
the name nor a phone or e-mail raises, a seat heading with no name under it
raises, a seat never runs on past the end of its own text block, and a
district/post printed twice raises. The text blocks end where
the page's "Cocke County Commissioners" photo list begins.

Names are kept as printed, nicknames in their brackets ("William (Bill)
Miller", "Dan (Pete) Bright").

Role: the photo list below the text blocks names two members, and only Sid
Mason's caption has text: "Chairman". It is NOT recorded: whether the
commission elected him chairman for the term that began 1 September 2026, or
the caption is left from the previous term, is not established by anything
read here, and a card that names the wrong chairman is worse than one that
names none. The caption is still checked, so the page changing shape raises:
it must be a commission office and name exactly one member in the text blocks.
Daniel Reece's caption is empty (and hidden).

PRIVACY: every seat on the page prints a phone and/or a personal e-mail
(gmail, yahoo, live). The phones are recorded as printed, in the page's
order, under Adam's ruling of 2026-10-17 that a number a government
publishes beside an official ships whosever line it is. No member has an
address on the county's own domain, so no e-mail is recorded. The page
prints no address.

Currency: checked 2026-10-11 against the Cocke County Election Commission's
results of the 6 August 2026 County General election ("State of Tennessee -
Cocke County, August 6, 2026, County General", each page footed "August 11,
2026", not labelled certified), linked as "August 2026 Election Results" on
the Election Commission's own site (cockecountyelections.org, file served
from static1.squarespace.com; scanned, pages 19-22 read as images). Every
one of the 14 names on this page is the winner of the same district and post:
D1 Post 1 Tim Grigsby (765-380), Post 2 Bill Miller (598-483); D2 Post 1
Judy Hensley (707-605), Post 2 Kenneth Chad Norton (unopposed); D3 Post 1
Norman Smith (unopposed), Post 2 Sid Mason (680 of four); D4 Post 1
Jonanthon Templin (sic on the ballot; unopposed), Post 2 Donnie E Raines
(407-352); D5 Post 1 Dan (Pete) Bright (unopposed), Post 2 Daniel Ray Reece
(593-407); D6 Post 1 Casey Reed (490-403), Post 2 Jeff Eslinger (481-384);
D7 Post 1 Tim Layman (324-266), Post 2 Clayton (Skip) Ellison (387-216). The
spellings differ only by middle names, initials and nicknames."""
import re
from ._common import txt, mailtos, member, ROLE, read_phones, Withheld

COUNTY = "Cocke"; FIPS = "029"
DOMAINS = ("cockecountytn.gov",)
URLS = ["https://www.cockecountytn.gov/county-legislative-body"]
SEATS = {str(i): 2 for i in range(1, 8)}
AT_LARGE = 0

START = "Cocke County Commissioners Information"
BLOCK_RE = re.compile(r'<div class="sqs-html-content"[^>]*>(.*?)</div>', re.S)
PARA_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
HEAD_RE = re.compile(r"^\s*<strong>\s*District (\d{1,2}) Post (\d)\s*</strong>\s*$")
NAME_RE = re.compile(r"^[A-Z][A-Za-z.'’()\" -]+$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[ .-]?\d{3}-\d{4}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
ITEM_RE = re.compile(r'<li\s+class="\s*list-item\s*"(.*?)</li>', re.S)
ITEM_TITLE_RE = re.compile(r'<h2\s+class="\s*list-item-content__title\b[^"]*"[^>]*>(.*?)</h2>', re.S)
ITEM_DESC_RE = re.compile(r'<div\s+class="\s*list-item-content__description\b[^"]*"[^>]*>(.*?)</div>', re.S)


def _own_email(name, addrs):
    surname = re.sub(r"[^a-z]", "", name.split()[-1].lower())
    for a in addrs:
        local, _, dom = a.lower().partition("@")
        if any(dom == d or dom.endswith("." + d) for d in DOMAINS):
            if surname and surname in re.sub(r"[^a-z]", "", local):
                return a
            raise ValueError("county address %r under %r is not theirs" % (a, name))
    return None


def parse(pages):
    page = pages[URLS[0]]
    s = page.find(START)
    e = page.find("user-items-list-item-container", s)
    if s < 0 or e < 0:
        raise ValueError("the commissioners' text blocks or the photo list after them are missing")
    districts, seen, cur = {}, set(), None

    def close():
        if cur and cur["name"] is None:
            raise ValueError("District %s Post %s has no name under it" % (cur["d"], cur["post"]))
        if cur:
            seat = "Post " + cur["post"]
            districts.setdefault(cur["d"], []).append(
                member(cur["name"], seat=seat, email=_own_email(cur["name"], cur["mail"]),
                       phones=cur["phones"]))

    for b in BLOCK_RE.finditer(page, s, e):
        for p in PARA_RE.finditer(b.group(1)):
            raw, t = p.group(1), txt(p.group(1))
            if not t:
                continue
            h = HEAD_RE.match(raw)
            if h:
                close()
                key = (h.group(1), h.group(2))
                if key in seen:
                    raise ValueError("District %s Post %s is printed twice" % key)
                seen.add(key)
                cur = {"d": h.group(1), "post": h.group(2), "name": None, "mail": [],
                       "phones": []}
                continue
            if re.search(r"\bDistrict\b|\bPost \d", t):
                raise ValueError("a line names a district but is not 'District N Post M': %r" % t)
            if cur is None:
                continue
            if cur["name"] is None:
                if re.search(r"\bvacan|\bopen\b", t, re.I) or not NAME_RE.match(t) or " " not in t:
                    raise ValueError("District %s Post %s: %r does not look like a name"
                                     % (cur["d"], cur["post"], t))
                cur["name"] = t
            elif EMAIL_RE.match(t):
                cur["mail"].append(t)
                cur["mail"].extend(mailtos(raw))
            elif PHONE_RE.match(t):
                got = read_phones(raw, strict=True)
                if not isinstance(cur["phones"], Withheld):     # one withheld number holds them all
                    cur["phones"] = got if isinstance(got, Withheld) else cur["phones"] + got
            else:
                raise ValueError("District %s Post %s: unexpected line under %r"
                                 % (cur["d"], cur["post"], cur["name"]))
        close()                                     # a seat never runs past its own text block
        cur = None
    if not districts:
        raise ValueError("no 'District N Post M' lines found")

    for it in ITEM_RE.finditer(page, e):
        title = ITEM_TITLE_RE.search(it.group(1))
        desc = ITEM_DESC_RE.search(it.group(1))
        name = txt(title.group(1)) if title else ""
        role = txt(desc.group(1)) if desc else ""
        if not role:
            continue
        if not name:
            raise ValueError("a photo-list caption %r has no name" % role)
        if not ROLE.fullmatch(role):
            raise ValueError("photo-list caption for %r reads %r, not a commission office" % (name, role))
        hits = [r for ms in districts.values() for r in ms if r["name"] == name]
        if len(hits) != 1:
            raise ValueError("the photo list gives %r the office %r but the text blocks list "
                             "%d members of that name" % (name, role, len(hits)))
        # Checked above and deliberately not recorded: see the docstring.
    return {"districts": districts, "atLarge": []}
