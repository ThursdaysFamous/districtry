"""Unit table and parsers: the larger cities. Contract in mi_municipal_common.py.

Every page here was read on 2026-10-01 with the fleet's roster token, after
its host's robots.txt; each parser's docstring names the page structure it was
written against and the trap it guards. Dearborn Heights is not in the table:
its council page names six people and says nothing about a seventh seat, and
the only statement of the vacancy is a time-limited News Flash (2026-09-22,
appointment vote 2026-10-13), so the page cannot be read as a whole council.
"""

import json
import re
from datetime import datetime, timezone

from mi_municipal_common import txt, emails_in, phones_in, phone, member


def _section(h, start_pat, end_pat=None, unit=""):
    """The slice of `h` from the first match of start_pat to the first match of
    end_pat after it (or the end). Raises when the start anchor is missing."""
    m = re.search(start_pat, h, re.S | re.I)
    if not m:
        raise ValueError("%s: anchor %r not found" % (unit, start_pat))
    rest = h[m.start():]
    if end_pat:
        e = re.search(end_pat, rest[len(m.group(0)):], re.S | re.I)
        if not e:
            raise ValueError("%s: end anchor %r not found" % (unit, end_pat))
        rest = rest[:len(m.group(0)) + e.start()]
    return rest


def _hcards(h):
    """CivicPlus staff-directory widget cards: (name, job title, block)."""
    out = []
    for m in re.finditer(r'<li class="widgetItem h-card">(.*?)</li>', h, re.S):
        b = m.group(1)
        n = re.search(r'p-name">(.*?)</h4>', b, re.S)
        t = re.search(r'p-job-title">(.*?)</div>', b, re.S)
        out.append((txt(n.group(1)) if n else "", txt(t.group(1)) if t else "", b))
    return out


def _drop_nickname(name):
    """Remove a quoted nickname ('William “Bill” Patts' -> 'William Patts')."""
    name = re.sub(r'\s*["“”][^"“”]+["“”]\s*', " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _expect(unit, members, n):
    if len(members) != n:
        raise ValueError("%s: found %d members where the page was written for %d"
                         % (unit, len(members), n))


# --------------------------------------------------------------------------

def parse_warren(h, also):
    """WordPress callout blocks: an <h3> seat heading ("At Large", "District N")
    over <strong>Name</strong>, <em>Council Member</em>, an optional office
    line (President, Vice President, Secretary...; District members repeat
    their district there instead), phone and mailto. The council's own line
    is in the page's Contact block."""
    blocks = re.findall(
        r'<h3>\s*(At Large|District \d)\s*</h3>\s*</div>\s*'
        r"<div class='callout-block--content editor-content'>(.*?)</div>", h, re.S)
    members = []
    for seat, b in blocks:
        name = txt(re.search(r"<strong>(.*?)</strong>", b, re.S).group(1))
        lines = [txt(x) for x in re.split(r"<br\s*/?>", b)]
        lines = [x for x in lines if x]
        if len(lines) < 2 or lines[1] != "Council Member":
            raise ValueError("Warren: block for %r is not Name / Council Member" % name)
        role = "Council Member"
        office = lines[2] if len(lines) > 2 else ""
        if office and not re.match(r"^(District \d|At Large|[\d(])", office):
            role = {"President": "Council President",
                    "Vice President": "Council Vice President",
                    "Secretary": "Council Secretary",
                    "Assistant Secretary-Mayor Pro-Tem":
                        "Council Assistant Secretary / Mayor Pro Tem"}.get(office)
            if not role:
                raise ValueError("Warren: unexpected office line %r for %r" % (office, name))
        ph = phones_in(b)
        em = emails_in(b)
        members.append(member(name, role, seat, ph[0] if ph else None,
                              em[0] if em else None))
    _expect("Warren", members, 7)
    c = re.search(r"City Council Members\s+Contact\s+(\S+@cityofwarren\.org)\s+(\(\d{3}\)\s*\d{3}-\d{4})",
                  txt(h))
    roster = {"members": members}
    if c:
        roster["office"] = {"email": c.group(1).lower(), "phone": phone(c.group(2))}
    return roster


def parse_sterling_heights(h, also):
    """CivicPlus directory, department 37 ("Contact Info for all City
    Council"): one list-group item per member with name link, title
    (Mayor / Mayor Pro Tem / Councilman / Councilwoman), mailto and tel. The
    Mayor sits on the seven-member council."""
    sec = _section(h, r"Contact Info for all City Council</h2>", r"</ul>", "Sterling Heights")
    members = []
    for item in re.findall(r'<li class="list-group-item[^>]*>(.*?)</li>', sec, re.S):
        a = re.search(r'<a href="/m/directory/employee\?eid=\d+"[^>]*>(.*?)</a>', item, re.S)
        t = re.search(r'<div class="d-sm-block d-none">(.*?)</div>', item, re.S)
        if not a or not t:
            raise ValueError("Sterling Heights: directory item without name or title")
        title = txt(t.group(1))
        role = {"Councilman": "Council Member", "Councilwoman": "Council Member"}.get(title, title)
        if role not in ("Mayor", "Mayor Pro Tem", "Council Member"):
            raise ValueError("Sterling Heights: unexpected title %r" % title)
        ph = phones_in(item)
        em = emails_in(item)
        members.append(member(a.group(1), role, None, ph[0] if ph else None,
                              em[0] if em else None))
    _expect("Sterling Heights", members, 7)
    roster = {"members": members}
    em = emails_in(re.search(r'<div class="fr-view my-3">(.*?)</div>', sec, re.S).group(1))
    if em:
        roster["office"] = {"email": em[0]}
    return roster


def parse_ann_arbor(h, also):
    """GovStack pods under the "Council Members" heading: heading "Name (D)",
    secondary heading "Mayor" or "Ward N", then phone / mailto / term for the
    members who publish them. A zero-width space inside a name is stripped by
    txt(); the party suffix is removed."""
    sec = _section(h, r'<h3 class="heading\s+base-heading\s*" >Council Members</h3>',
                   r"</section>", "Ann Arbor")
    pods = re.split(r'<div class="item item_has-bg', sec)[1:]
    members = []
    for p in pods:
        n = re.search(r'<p class="heading[^"]*"\s*>(.*?)</p>', p, re.S)
        s = re.search(r'<p class="secondary-heading[^"]*"\s*>(.*?)</p>', p, re.S)
        if not n or not s:
            raise ValueError("Ann Arbor: pod without a name or secondary heading")
        name = re.sub(r"\s*\([A-Z]{1,3}\)\s*$", "", txt(n.group(1)))
        label = txt(s.group(1))
        t = re.search(r'<div class="text base-text">(.*?)</div>', p, re.S)
        body = t.group(1) if t else ""
        ph = phones_in(body)
        em = emails_in(body)
        if label == "Mayor":
            members.append(member(name, "Mayor", None, ph[0] if ph else None, em[0] if em else None))
        elif re.match(r"^Ward [1-5]$", label):
            members.append(member(name, "Council Member", label, ph[0] if ph else None,
                                  em[0] if em else None))
        else:
            raise ValueError("Ann Arbor: unexpected label %r for %r" % (label, name))
    _expect("Ann Arbor", members, 11)
    return {"members": members}


def parse_dearborn(h, also):
    """Drupal cards: a role line ("Council President", "Council Member") in a
    text-xl div, the name in the following <h2>, then a biography ending
    "Email: X@dearborn.gov". No per-member phone. The mayor is not on this
    page."""
    cards = re.split(r'<div\s+class="text-xl font-semibold[^"]*">', h)[1:]
    members = []
    for c in cards:
        role = txt(c[:c.find("</div")])
        if not role.startswith("Council"):
            continue
        n = re.search(r"<h2[^>]*>(.*?)</h2\s*>", c, re.S)
        if not n:
            raise ValueError("Dearborn: card %r has no name heading" % role)
        bio = c[n.end():c.find("contact.dearborn.gov")]
        em = [e for e in emails_in(bio) if e.endswith("@dearborn.gov")]
        members.append(member(n.group(1), role, None, None, em[0] if em else None))
    _expect("Dearborn", members, 7)
    return {"members": members}


def parse_livonia(h, also):
    """CivicPlus slideshow under "Meet our Current Council Members": one
    <h4 class="widgetTitle"> per member reading "Name, Title". No per-member
    contact on the page."""
    sec = _section(h, r"Meet our Current Council Members", r"</ol>", "Livonia")
    members = []
    for t in re.findall(r'<h4 class="widgetTitle">(.*?)</h4>', sec, re.S):
        name, _, title = txt(t).partition(", ")
        if title not in ("Council President", "Council Vice President", "Council Member"):
            raise ValueError("Livonia: unexpected title %r" % title)
        members.append(member(name, title))
    _expect("Livonia", members, 7)
    return {"members": members}


def parse_troy(h, also):
    """Revize "Contact Council": one <p> per member with the name in <strong>,
    "Title | Term ends: ...", phones and a Cloudflare-obfuscated e-mail
    (decoded by emails_in). TRAP: five blocks print the same 248.524.3500,
    which is a shared council line rather than a member's own, so a number
    printed in more than one block goes to `office` and never onto a member.
    The "Email all Council Members" address above the list is the office
    e-mail."""
    sec = _section(h, r'<span class="subheader">Contact</span>', r'<section id="modal-section"', "Troy")
    head, _, body = sec.partition("<hr />")
    blocks = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S):
        m = re.match(r"^(.*?)\s+(Mayor Pro Tem|Mayor|Council Member)\s*\|\s*Term ends", txt(p))
        if m:
            blocks.append((m.group(1), m.group(2), p))
    counts = {}
    for _, _, p in blocks:
        for x in phones_in(p):
            counts[x] = counts.get(x, 0) + 1
    shared = [x for x, n in counts.items() if n > 1]
    members = []
    for name, role, p in blocks:
        own = [x for x in phones_in(p) if x not in shared]
        em = emails_in(p)
        members.append(member(name, role, None, own[0] if own else None, em[0] if em else None))
    _expect("Troy", members, 7)
    office = {}
    if len(shared) == 1:
        office["phone"] = shared[0]
    em = emails_in(head)
    if em:
        office["email"] = em[0]
    roster = {"members": members}
    if office:
        roster["office"] = office
    return roster


def parse_westland(h, also):
    """CivicPlus h-card widget "City Council Members": one card per member
    with name, job title, mailto and phone. The widget also carries an empty
    card and a department card named "City Council" (no title), whose phone is
    the council's own line."""
    members, office = [], {}
    for name, title, b in _hcards(h):
        if name == "City Council" and not title:
            ph = phones_in(b)
            if ph:
                office["phone"] = ph[0]
            continue
        if not name and not title:
            continue
        if title not in ("Council President", "Council President Pro-Tem", "Council Member"):
            raise ValueError("Westland: unexpected title %r for %r" % (title, name))
        ph = phones_in(b)
        em = emails_in(b)
        members.append(member(name, title.replace("Pro-Tem", "Pro Tem"), None,
                              ph[0] if ph else None, em[0] if em else None))
    _expect("Westland", members, 7)
    roster = {"members": members}
    if office:
        roster["office"] = office
    return roster


def parse_farmington_hills(h, also):
    """Employee cards: name in div.fs-6.fw-bold, title in div.fs-8, a mailto
    "Email" link. The biography modals repeat names and disagree with the
    cards (Joe/Jon Aldred); only the cards are read. Office phone is the
    "Mayor and City Council" line at the top of the page."""
    members = []
    for m in re.finditer(r'<div class="fs-6 fw-bold lh-1 mb-2">(.*?)</div>\s*'
                         r'<div class="fs-8 text-uppercase lh-sm mb-2">(.*?)</div>(.*?)'
                         r'data-bs-toggle="modal"', h, re.S):
        title = txt(m.group(2))
        if title not in ("Mayor", "Mayor Pro Tem", "Council Member"):
            raise ValueError("Farmington Hills: unexpected title %r" % title)
        em = emails_in(m.group(3))
        members.append(member(m.group(1), title, None, None, em[0] if em else None))
    _expect("Farmington Hills", members, 7)
    roster = {"members": members}
    c = re.search(r"Mayor and City Council .{0,120}?(\d{3}-\d{3}-\d{4})", txt(h))
    if c:
        roster["office"] = {"phone": phone(c.group(1))}
    return roster


_ORDINAL = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6,
            "7th": 7, "8th": 8, "9th": 9}


def parse_flint(h, also):
    """The "City Council Members" directory section (id="council-members")
    near the end of a ~1.5 MB page: one <article class="directory-item"> per
    member, the name in <h3>, then "City Council – Nth Ward", labelled Office
    and Cell rows and an e-mail (entity-encoded text). TRAP: an "In Memoriam"
    notice naming a former First Ward member follows the section; only the
    articles inside the section are read, and the ward comes from each
    article's own label."""
    sec = _section(h, r'<section class="content-block block-directory[^"]*" id="council-members">',
                   r"</section>", "Flint")
    members = []
    for a in re.findall(r'<article class="directory-item.*?</article>', sec, re.S):
        hd = re.search(r"<header>\s*<h3[^>]*>(.*?)</h3>(.*?)<div>", a, re.S)
        if not hd:
            raise ValueError("Flint: directory item without a name heading")
        w = re.match(r"^City Council\s*[–-]\s*(\d(?:st|nd|rd|th)) Ward$", txt(hd.group(2)))
        if not w:
            raise ValueError("Flint: %r has label %r" % (txt(hd.group(1)), txt(hd.group(2))))
        office = None
        for lab, val in re.findall(r'directory-item-label">(.*?)</div>\s*<a[^>]*>(.*?)</a>', a, re.S):
            if txt(lab) == "Office":
                office = phone(txt(val))
        em = [e for e in emails_in(a) if e.endswith("@cityofflint.com")]
        members.append(member(hd.group(1), "Council Member", "Ward %d" % _ORDINAL[w.group(1)],
                              office, em[0] if em else None))
    _expect("Flint", members, 9)
    return {"members": members}


def parse_southfield(h, also):
    """Drupal "Elected Officials" cards: TITLE in capitals, name link, an
    e-mail split across a <br> ("ksiver@" / "cityofsouthfield.com"), term,
    phone. The seven-member council is the cards titled COUNCIL...; the
    Mayor, City Clerk and City Treasurer are elected separately and are not
    council seats. A quoted nickname is dropped from the name."""
    members = []
    for art in re.findall(r'<article data-history-node-id.*?</article>', h, re.S):
        body = re.search(r'<div class="card-body[^"]*">(.*?)<hr', art, re.S)
        title = txt(body.group(1)) if body else ""
        if not title.startswith("COUNCIL"):
            continue
        role = {"COUNCIL PRESIDENT": "Council President",
                "COUNCIL PRESIDENT PRO TEM": "Council President Pro Tem",
                "COUNCILWOMAN": "Council Member",
                "COUNCILMAN": "Council Member"}.get(title)
        if not role:
            raise ValueError("Southfield: unexpected title %r" % title)
        name = re.search(r'<a id="node-\d+-teaser"[^>]*>(.*?)</a>', art, re.S)
        e = re.search(r"([A-Za-z0-9._-]+@)\s*<br\s*/?>\s*(cityofsouthfield\.com)", art)
        ph = phones_in(art)
        members.append(member(_drop_nickname(txt(name.group(1))), role, None,
                              ph[0] if ph else None,
                              (e.group(1) + e.group(2)) if e else None))
    _expect("Southfield", members, 7)
    return {"members": members}


def parse_kalamazoo(h, also):
    """OpenCities elected-official list: one <article> per member, name in
    <h2 class="list-item-title">, title after it in the header, a mailto. The
    body is the City Commission; the Mayor and Vice Mayor sit on it."""
    sec = _section(h, r'<div class="list-container elected-official-list-container">', None, "Kalamazoo")
    members = []
    for art in re.findall(r"<article>(.*?)</article>", sec, re.S):
        hd = re.search(r'<header>(.*?)<h2 class="list-item-title">(.*?)</h2>(.*?)</header>', art, re.S)
        if not hd:
            raise ValueError("Kalamazoo: article without a name heading")
        title = txt(hd.group(3))
        role = {"City Commissioner": "Commissioner"}.get(title, title)
        if role not in ("Mayor", "Vice Mayor", "Commissioner"):
            raise ValueError("Kalamazoo: unexpected title %r" % title)
        em = emails_in(art)
        members.append(member(hd.group(2), role, None, None, em[0] if em else None))
    _expect("Kalamazoo", members, 7)
    return {"members": members}


def parse_novi(h, also):
    """Accordion buttons, one per member, reading "Title Name" (Mayor, Mayor
    Pro Tem, Council Member); the title is split off the front. Other
    accordions on the page (meeting rules) do not start with a title. No
    per-member contact is printed."""
    members = []
    for b in re.findall(r'<button class="accordion-button[^>]*>(.*?)</button>', h, re.S):
        m = re.match(r"^(Mayor Pro Tem|Mayor|Council Member) (.+)$", txt(b))
        if m:
            members.append(member(m.group(2), m.group(1)))
    _expect("Novi", members, 7)
    return {"members": members}


def parse_taylor(h, also):
    """CivicPlus editor blocks: <h2> name, then the title paragraph ("City
    Council Chairman", "City Council Pro Tem", "Councilman") and "Email: x"
    as plain text. TRAP: one address is printed on the misspelt domain
    cityoftaqylormi.gov; only addresses on cityoftaylormi.gov are kept. A
    quoted nickname is dropped from the name."""
    members = []
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>\s*<p>(.*?)</p>\s*<p>(.*?)</p>", h, re.S):
        title = txt(m.group(2))
        role = {"City Council Chairman": "Council Chairman",
                "City Council Pro Tem": "Council Chair Pro Tem",
                "Councilman": "Council Member",
                "Councilwoman": "Council Member"}.get(title)
        if not role:
            continue
        em = [e for e in emails_in(m.group(3)) if e.endswith("@cityoftaylormi.gov")]
        members.append(member(_drop_nickname(txt(m.group(1))), role, None, None,
                              em[0] if em else None))
    _expect("Taylor", members, 7)
    return {"members": members}


def parse_pontiac(h, also):
    """Revize list under the "Council Members" subheader: one <li> per seat,
    "Councilman Chris Jackson, District 1" or "Councilman at Large Adrian
    Austin (Council President)", an office in parentheses. The page's prose
    says "seven City Council Districts" while the list carries six numbered
    districts and one at-large seat; the seat is taken from each line."""
    sec = _section(h, r'<span class="subheader">Council Members</span>', r"</ul>", "Pontiac")
    members = []
    for li in re.findall(r"<li>(.*?)</li>", sec, re.S):
        t = txt(li)
        office = re.search(r"\(([^)]+)\)\s*$", t)
        role = office.group(1) if office else "Council Member"
        t = re.sub(r"\s*\([^)]+\)\s*$", "", t)
        m = re.match(r"^Council(?:man|woman|member) (.+), (District [1-6])$", t)
        if m:
            name, seat = m.group(1), m.group(2)
        else:
            m = re.match(r"^Council(?:man|woman|member) at Large (.+)$", t)
            if not m:
                raise ValueError("Pontiac: unexpected line %r" % t)
            name, seat = m.group(1), "At Large"
        if role not in ("Council President", "Council President Pro Tem", "Council Member"):
            raise ValueError("Pontiac: unexpected office %r" % role)
        members.append(member(name, role, seat))
    _expect("Pontiac", members, 7)
    return {"members": members}


def parse_st_clair_shores(h, also):
    """CivicPlus h-card widgets: the Mayor in one widget, the six council
    members in the next, each with job title, mailto and (for five) a phone.
    Title "Mayor Pro Tem / Council Member" is read as Mayor Pro Tem."""
    members = []
    for name, title, b in _hcards(h):
        role = {"Mayor Pro Tem / Council Member": "Mayor Pro Tem"}.get(title, title)
        if role not in ("Mayor", "Mayor Pro Tem", "Council Member"):
            raise ValueError("St. Clair Shores: unexpected title %r for %r" % (title, name))
        ph = phones_in(b)
        em = emails_in(b)
        members.append(member(name, role, None, ph[0] if ph else None, em[0] if em else None))
    _expect("St. Clair Shores", members, 7)
    return {"members": members}


def parse_royal_oak(h, also):
    """CivicPlus table Member | Term Expires: each cell "Name, Title" with
    the name linking the staff directory. The body is the City Commission.
    The Mayor's own address is on his h-card in the sidebar; the
    "City Commission" department card carries the commission's phone."""
    sec = _section(h, r"<th>Member</th>", r"</table>", "Royal Oak")
    cards = _hcards(h)
    members = []
    for row in re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>", sec, re.S):
        name, _, title = re.sub(r"\s+,", ",", txt(row)).partition(", ")
        role = {"City Commissioner": "Commissioner"}.get(title, title)
        if role not in ("Mayor", "Mayor Pro Tem", "Commissioner"):
            raise ValueError("Royal Oak: unexpected title %r" % title)
        em = None
        for n, t, b in cards:
            if n == name:
                e = emails_in(b)
                em = e[0] if e else None
        members.append(member(name, role, None, None, em))
    _expect("Royal Oak", members, 7)
    roster = {"members": members}
    for n, t, b in cards:
        if n == "City Commission" and not t:
            ph = phones_in(b)
            if ph:
                roster["office"] = {"phone": ph[0]}
    return roster


def parse_kentwood(h, also):
    """Revize page: group subheaders ("mayor", "Commissioners - 1st Ward",
    "Commissioners - 2nd Ward", "Commissioners-at-Large") each followed by
    member name links. TRAP: the elected City Clerk follows the commissioners
    after an <hr />; the read stops there. No per-member contact."""
    sec = _section(h, r'<strong class="subheader">mayor', None, "Kentwood")
    stop = re.search(r"Commissioners-at-Large.*?<hr", sec, re.S)
    if not stop:
        raise ValueError("Kentwood: no <hr /> after the at-large group")
    sec = sec[:stop.end()]
    seat = None
    members = []
    for m in re.finditer(r'<strong class="subheader">(.*?)</strong>|<a [^>]*>(.*?)</a>', sec, re.S):
        if m.group(1) is not None:
            head = txt(m.group(1))
            seat = {"mayor": "mayor", "Commissioners - 1st Ward": "Ward 1",
                    "Commissioners - 2nd Ward": "Ward 2",
                    "Commissioners-at-Large": "At Large"}.get(head)
            if seat is None:
                raise ValueError("Kentwood: unexpected group heading %r" % head)
            continue
        name = txt(m.group(2))
        if not name:
            continue
        if seat == "mayor":
            if not name.startswith("Mayor "):
                raise ValueError("Kentwood: mayor link reads %r" % name)
            members.append(member(name[len("Mayor "):], "Mayor"))
        else:
            members.append(member(name, "Commissioner", seat))
    _expect("Kentwood", members, 7)
    return {"members": members}


def parse_portage(h, also):
    """CivicPlus h-card widget: one card per member with job title (Mayor,
    Mayor Pro Tem, Councilmember), mailto and phone."""
    members = []
    for name, title, b in _hcards(h):
        role = {"Councilmember": "Council Member"}.get(title, title)
        if role not in ("Mayor", "Mayor Pro Tem", "Council Member"):
            raise ValueError("Portage: unexpected title %r for %r" % (title, name))
        ph = phones_in(b)
        em = emails_in(b)
        members.append(member(name, role, None, ph[0] if ph else None, em[0] if em else None))
    _expect("Portage", members, 7)
    return {"members": members}


def parse_east_lansing(h, also):
    """CivicPlus editor blocks: <h2 class="subhead1"> "Title Name" (Mayor,
    Mayor Pro Tem, Councilmember), then Term ends, Phone or Cell, Email.
    TRAPS: one heading splits a name over a <br>, one is mis-cased
    ("SteveN"); Meadows' block carries an empty stray mailto for the Mayor
    ahead of his own, so the address is read from the visible "Email:" text;
    his phone is the council office's own line (sidebar "City Council" box),
    which goes to `office` only. Page slugs carry stale roles and are never
    read."""
    sec = _section(h, r'<div data-cpRole="mainContentContainer" id="moduleContent">',
                   r'id="featureColumn"', "East Lansing")
    side = _section(h, r'<h3 class="subhead2">City Council</h3>', r"</li>", "East Lansing")
    side_t = txt(side)
    office = {}
    em = emails_in(side)
    if em:
        office["email"] = em[0]
    p = re.search(r"Ph:\s*(\(\d{3}\)\s*\d{3}-\d{4})", side_t)
    if p:
        office["phone"] = phone(p.group(1))
    members = []
    for m in re.finditer(r'<h2 class="subhead1"[^>]*>(.*?)</h2>(.*?)</div>', sec, re.S):
        hm = re.match(r"^(Mayor Pro Tem|Mayor|Councilmember) (.+)$", txt(m.group(1)))
        if not hm:
            raise ValueError("East Lansing: heading %r" % txt(m.group(1)))
        role = {"Councilmember": "Council Member"}.get(hm.group(1), hm.group(1))
        name = " ".join(w.capitalize() if re.match(r"^[A-Z][a-z]+[A-Z]$", w) else w
                        for w in hm.group(2).split())
        body = txt(m.group(2))
        e = re.search(r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", body)
        ph = re.search(r"(?:Phone|Cell):\s*(\(\d{3}\)\s*\d{3}-\d{4})", body)
        ph = phone(ph.group(1)) if ph else None
        if ph and ph == office.get("phone"):
            ph = None
        members.append(member(name, role, None, ph, e.group(1) if e else None))
    _expect("East Lansing", members, 5)
    roster = {"members": members}
    if office:
        roster["office"] = office
    return roster


LANSING_SEAT = re.compile(r"^(?:([1-4])(?:st|nd|rd|th) Ward|(At[- ]Large))\s+Council\s*[Mm]ember$")


def parse_lansing(h, also):
    """Lansing's council page names nobody in its own HTML: the member cards
    are drawn afterwards by the website vendor's script from the vendor's
    content service (CivicPlus HCMS, app mi-lansing). The scraper reads that
    service the way the page does, with the read-only key the page hands every
    signed-out visitor (see the unit's `hcms` entry and
    mi_municipal_officials_scraper.read_hcms), and passes the Employee items
    here as `also[0]`.

    Each council member is one Employee item in the "City Council" category
    whose title is "<N>th Ward Council Member" or "At-Large Council Member";
    the biography opens "Term Expires: ...", and the year's officers add
    "<year> Council President" or "<year> Council Vice President". An officer
    line naming a year other than the year of the read is not used, so a
    biography nobody updated in January cannot carry last year's President
    into this year. The phone is the member's own line ("Phone: 517-483-41xx")
    and the e-mail a mailto in its own field. TRAP: the category also holds
    whatever else the city files there, so only a title of that exact shape
    is a seat, and anything else in the category raises."""
    if "Council Members" not in txt(h):
        raise ValueError("Lansing: the council page no longer carries its title")
    if not also:
        raise ValueError("Lansing: no content-service items were read")
    items = json.loads(also[0]).get("items") or []
    year = datetime.now(timezone.utc).strftime("%Y")

    def en(it, k):
        v = (it.get("data") or {}).get(k) or {}
        return v.get("en") if isinstance(v, dict) else None

    members = []
    for it in items:
        if not any(c.get("name") == "City Council" for c in it.get("categories") or []):
            continue
        if it.get("status") != "Published":
            continue
        title = txt(en(it, "title") or "")
        m = LANSING_SEAT.match(title)
        if not m:
            raise ValueError("Lansing: City Council item %r titled %r" % (it.get("slug"), title))
        seat = "Ward %s" % m.group(1) if m.group(1) else "At Large"
        bio = txt(en(it, "biography") or "")
        role = "Council Member"
        o = re.search(r"\b(20\d\d) Council (Vice President|President)\b", bio)
        if o and o.group(1) == year:
            role = "Council " + o.group(2)
        name = "%s %s" % (txt(en(it, "firstname") or ""), txt(en(it, "lastname") or ""))
        ph = phones_in(en(it, "phonenumber") or "")
        em = emails_in(en(it, "emailaddress") or "")
        members.append(member(name, role, seat, ph[0] if ph else None, em[0] if em else None))
    wards = sorted(x["seat"] for x in members if x["seat"] != "At Large")
    if wards != ["Ward 1", "Ward 2", "Ward 3", "Ward 4"]:
        raise ValueError("Lansing: ward seats read as %r" % wards)
    members.sort(key=lambda x: (x["seat"] == "At Large", x["seat"], x["name"]))
    _expect("Lansing", members, 8)
    return {"members": members}


UNITS = [
    {"geoid": "2684000", "name": "Warren", "kind": "city", "body": "City Council",
     "url": "https://www.cityofwarren.org/government/city-council/city-council-members/",
     "seats": 7, "parse": parse_warren},
    {"geoid": "2676460", "name": "Sterling Heights", "kind": "city", "body": "City Council",
     "url": "https://sterlingheights.gov/m/directory/department?did=37",
     "seats": 7, "parse": parse_sterling_heights},
    {"geoid": "2603000", "name": "Ann Arbor", "kind": "city", "body": "City Council",
     "url": "https://www.a2gov.org/city-council/",
     "seats": 11, "parse": parse_ann_arbor},
    {"geoid": "2621000", "name": "Dearborn", "kind": "city", "body": "City Council",
     "url": "https://dearborn.gov/government/city-council/meet-city-council",
     "seats": 7, "parse": parse_dearborn},
    {"geoid": "2649000", "name": "Livonia", "kind": "city", "body": "City Council",
     "url": "https://www.livonia.gov/1653/City-Council",
     "seats": 7, "parse": parse_livonia},
    {"geoid": "2680700", "name": "Troy", "kind": "city", "body": "City Council",
     "url": "https://troymi.gov/community/government/citycouncil/contact_council.php",
     "seats": 7, "parse": parse_troy},
    {"geoid": "2686000", "name": "Westland", "kind": "city", "body": "City Council",
     "url": "https://www.cityofwestland.com/266/City-Council",
     "seats": 7, "parse": parse_westland},
    {"geoid": "2627440", "name": "Farmington Hills", "kind": "city", "body": "City Council",
     "url": "https://www.fhgov.com/citycouncil/",
     "seats": 7, "parse": parse_farmington_hills},
    {"geoid": "2629000", "name": "Flint", "kind": "city", "body": "City Council",
     "url": "https://www.cityofflint.com/city-council/",
     "seats": 9, "parse": parse_flint},
    {"geoid": "2674900", "name": "Southfield", "kind": "city", "body": "City Council",
     "url": "https://www.cityofsouthfield.com/government/city-council/elected-officials",
     "seats": 7, "parse": parse_southfield},
    {"geoid": "2642160", "name": "Kalamazoo", "kind": "city", "body": "City Commission",
     "url": "https://www.kalamazoocity.org/Government/Mayor-Vice-Mayor-and-City-Commissioners",
     "seats": 7, "parse": parse_kalamazoo},
    {"geoid": "2659440", "name": "Novi", "kind": "city", "body": "City Council",
     "url": "https://cityofnovi.org/government/city-council/",
     "seats": 7, "parse": parse_novi},
    {"geoid": "2679000", "name": "Taylor", "kind": "city", "body": "City Council",
     "url": "https://www.cityoftaylor.com/1669/City-Council-Members",
     "seats": 7, "parse": parse_taylor},
    {"geoid": "2665440", "name": "Pontiac", "kind": "city", "body": "City Council",
     "url": "https://www.pontiac.mi.us/government/city_council/index.php",
     "seats": 7, "parse": parse_pontiac},
    {"geoid": "2670760", "name": "St. Clair Shores", "kind": "city", "body": "City Council",
     "url": "https://www.scsmi.net/167/City-Council",
     "seats": 7, "parse": parse_st_clair_shores},
    {"geoid": "2670040", "name": "Royal Oak", "kind": "city", "body": "City Commission",
     "url": "https://www.romi.gov/412/City-Commission",
     "seats": 7, "parse": parse_royal_oak},
    {"geoid": "2642820", "name": "Kentwood", "kind": "city", "body": "City Commission",
     "url": "https://www.kentwood.us/city_services/committees_and_boards/city_commission/index.php",
     "seats": 7, "parse": parse_kentwood},
    {"geoid": "2665560", "name": "Portage", "kind": "city", "body": "City Council",
     "url": "https://www.portagemi.gov/487/Mayor-City-Council",
     "seats": 7, "parse": parse_portage},
    {"geoid": "2624120", "name": "East Lansing", "kind": "city", "body": "City Council",
     "url": "https://www.cityofeastlansing.com/996/Meet-the-Council",
     "seats": 5, "parse": parse_east_lansing},
    # The page's own HTML names nobody; the members come from the vendor's
    # content service, read with the key the page gives every visitor.
    # Measured 2026-10-06 and read on the operator's word that day.
    {"geoid": "2646000", "name": "Lansing", "kind": "city", "body": "City Council",
     "url": "https://www.lansingmi.gov/council-members",
     "hcms": {"schema": "employee"},
     "seats": 8, "parse": parse_lansing},
]
