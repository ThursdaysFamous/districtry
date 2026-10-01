"""Unit table and parsers: the rest of the cities. Contract in mi_municipal_common.py.

Every page here was read on 2026-10-01 and each parser was written against that
reading. A parser raises ValueError when its anchor text is missing or the
count it finds differs from what the page published that day.

Three cities print their mayor apart from the council and are counted without
one, because the page does not list the mayor as part of the body:
Lincoln Park (the mayor sits in an "Elected Officials" list beside the clerk
and treasurer, and the council has its own Council President), Allen Park
(the mayor is printed with the clerk and treasurer, above the "City Council
Members" heading), and Southgate and Romulus (the mayor is on a separate page).
"""

import re

from mi_municipal_common import emails_in, member, phone, phones_in, txt

ROMAN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6"}


def section(h, start, end, start_at=0):
    """The HTML between the first match of `start` (from `start_at`) and the
    next match of `end` after it. Raises when either anchor is missing."""
    m = re.search(start, h[start_at:], re.S)
    if not m:
        raise ValueError("anchor %r not found" % start)
    a = start_at + m.end()
    n = re.search(end, h[a:], re.S)
    if not n:
        raise ValueError("end anchor %r not found after %r" % (end, start))
    return h[a:a + n.start()]


def clean_name(s):
    """A printed name without honorifics, with runs of spaces collapsed."""
    s = txt(s)
    s = re.sub(r"^(?:Dr\.?|Hon\.?|Mr\.?|Mrs\.?|Ms\.?)\s+", "", s)
    return s.strip(" ,")


def role_of(title, plain="Council Member"):
    """The page's printed title normalised to an office. A plain member gets
    the body's own word (`plain`). Raises on a title it does not know, so a
    clerk or an assistant listed among the members cannot slip through."""
    t = re.sub(r"\s+", " ", title or "").strip(" .,").lower()
    if re.fullmatch(r"mayor", t):
        return "Mayor"
    if re.fullmatch(r"mayor ?pro[ -]?(?:tem|tempore|team)\.?", t):
        return "Mayor Pro Tem"
    if t == "vice mayor":
        return "Vice Mayor"
    if t == "council president":
        return "Council President"
    if re.fullmatch(r"council ?(?:man|woman|or|person|members?)", t):
        return "Council Member"
    if t in ("commissioner", "commissioners"):
        return "Commissioner"
    raise ValueError("unexpected title %r" % title)


def hcards(fragment):
    """CivicPlus directory-widget cards (li.widgetItem.h-card) in a fragment:
    [(name, title, card_html)]. Cards without a p-name heading (an address
    card) are skipped."""
    out = []
    for blk in re.split(r'<li class="widgetItem h-card">', fragment)[1:]:
        blk = blk.split("</li>")[0]
        nm = re.search(r'class="widgetTitle field p-name">(.*?)</h4>', blk, re.S)
        jt = re.search(r'class="field p-job-title">(.*?)</div>', blk, re.S)
        if not nm:
            continue
        out.append((clean_name(nm.group(1)), txt(jt.group(1)) if jt else "", blk))
    return out


def one(values):
    """The single value of a list, or None when there are none or several."""
    return values[0] if len(values) == 1 else None


def expect(members, n, where):
    if len(members) != n:
        raise ValueError("%s: %d members found where %d were expected"
                         % (where, len(members), n))
    return members


# --- Roseville ------------------------------------------------------------

def parse_roseville(h, also):
    """CivicPlus 'Members' directory widget on the City Council page: name,
    title, e-mail. Every e-mail is Cloudflare-obfuscated (decoded by
    emails_in). No phone on the page."""
    sec = section(h, r'<h3><a[^>]*>Members</a></h3>', r'>Overview</h2>')
    out = []
    for name, title, blk in hcards(sec):
        out.append(member(name, role_of(title), email=one(emails_in(blk))))
    return {"members": expect(out, 7, "Roseville")}


# --- Saginaw --------------------------------------------------------------

def parse_saginaw(h, also):
    """Editor tables under the 'Members' subhead, grouped by header cells
    'Mayor' / 'Mayor Pro Tempore' / 'Council Members'; each name is a
    Directory.aspx?EID link. The page states the nine are elected at large
    but no member's own entry says so, so no seat is set. No contact on the
    page itself (a FormCenter form)."""
    sec = section(h, r'<h2 class="subhead1">Members</h2>', r'<h2 class="subhead1">(?:<br>)?\s*Overview')
    out, role = [], None
    for m in re.finditer(r'<th[^>]*>(.*?)</th>|<a href="/Directory\.aspx\?EID=\d+"[^>]*>(.*?)</a>',
                         sec, re.S):
        if m.group(1) is not None:
            role = role_of(txt(m.group(1)))
        else:
            if role is None:
                raise ValueError("Saginaw: a name before any heading")
            out.append(member(clean_name(m.group(2)), role))
    return {"members": expect(out, 9, "Saginaw")}


# --- Midland --------------------------------------------------------------

def parse_midland(h, also):
    """One editor block per member under 'Your Elected Representatives':
    <strong>Name</strong>, 'Councilman Ward N' (with 'Mayor, ' or 'Mayor Pro
    Tem, ' prefixed), office address, phone, e-mail link. TRAP: Tim Soler's
    block carries an empty mailto for another address before his own, so the
    e-mail is taken only from a link whose text names the member."""
    sec = section(h, r'Your Elected Representatives</h2>', r'Find Your Representative')
    out = []
    for m in re.finditer(r'<p><strong>(.*?)</strong><br>(.*?)</p>', sec, re.S):
        name = clean_name(m.group(1))
        lines = [txt(x) for x in re.split(r'<br\s*/?>', m.group(2))]
        title = lines[0]
        t = re.fullmatch(r'(?:(Mayor|Mayor Pro Tem),\s*)?Councilman Ward (\d)', title)
        if not t:
            raise ValueError("Midland: unexpected title %r" % title)
        role = t.group(1) or "Council Member"
        email = None
        for a in re.finditer(r'<a href="mailto:([^"]+)">(.*?)</a>', m.group(2), re.S):
            if name.split()[-1].lower() in txt(a.group(2)).lower():
                email = a.group(1)
        out.append(member(name, role, "Ward " + t.group(2),
                          one(phones_in(m.group(2))), email))
    return {"members": expect(out, 5, "Midland")}


# --- Lincoln Park ---------------------------------------------------------

def parse_lincoln_park(h, also):
    """CivicPlus Members widget on the Elected Officials page. It interleaves
    the Mayor, City Clerk and Treasurer with the council; only the council is
    kept (the council has its own Council President, and the page does not
    list the mayor as a council member)."""
    sec = section(h, r'<h2 class="subhead1 ">Members</h2>', r'>Contact Us</h3>')
    out, others = [], []
    for name, title, blk in hcards(sec):
        if title in ("Mayor", "City Clerk", "Treasurer"):
            others.append(title)
            continue
        out.append(member(name, role_of(title), phone_=one(phones_in(blk)),
                          email=one(emails_in(blk))))
    if sorted(others) != ["City Clerk", "Mayor", "Treasurer"]:
        raise ValueError("Lincoln Park: other officers %r" % others)
    return {"members": expect(out, 6, "Lincoln Park")}


# --- Muskegon -------------------------------------------------------------

def parse_muskegon(h, also):
    """One line per member under 'City of Muskegon Commissioners':
    'Name, Seat – current term expires MM/DD/YYYY' (Willie German Jr uses a
    dash where the others use a comma). TRAP: the section nav calls a
    different member Vice Mayor; roles are read from this list only."""
    sec = section(h, r'<h3>City of Muskegon Commissioners</h3>', r'</p>')
    out = []
    for a in re.findall(r'<a [^>]*>(.*?)</a>', sec, re.S):
        line = re.split(r'\s*[–-]\s*current term', txt(a))[0]
        m = re.fullmatch(r'(.+?)\s*(?:,|–|-)\s*(.+)', line)
        if not m:
            raise ValueError("Muskegon: unexpected line %r" % line)
        name, rest = clean_name(m.group(1)), m.group(2)
        role, seat = None, None
        parts = [p.strip() for p in rest.split(",")]
        for p in parts:
            w = re.fullmatch(r'Ward (I|II|III|IV) Commissioner', p)
            if p == "Mayor":
                role = "Mayor"
            elif p == "Vice Mayor":
                role = "Vice Mayor"
            elif p == "At-Large Commissioner":
                seat = "At Large"
            elif w:
                seat = "Ward " + ROMAN[w.group(1)]
            else:
                raise ValueError("Muskegon: unexpected seat text %r" % p)
        out.append(member(name, role or "Commissioner", seat))
    return {"members": expect(out, 7, "Muskegon")}


# --- Holland --------------------------------------------------------------

def parse_holland(h, also):
    """The page is a CivicPlus sub-page menu: its only member content is nine
    link titles 'Name, Seat' in the secondary nav (data-parent 941). TRAP:
    the link SLUGS are stale and name other people; only the titles are
    read. No contact on this page."""
    sec = section(h, r'id="secondaryMenusecondaryNav" data-parent="941"', r'</ol>')
    out = []
    for t in re.findall(r'class="navMainItem secondaryNavItem[^"]*"[^>]*>(.*?)</a>', sec, re.S):
        m = re.fullmatch(r'(.+?),\s*(Mayor|Ward \d|At-Large)', txt(t))
        if not m:
            raise ValueError("Holland: unexpected menu title %r" % txt(t))
        if m.group(2) == "Mayor":
            out.append(member(clean_name(m.group(1)), "Mayor"))
        else:
            seat = "At Large" if m.group(2) == "At-Large" else m.group(2)
            out.append(member(clean_name(m.group(1)), "Council Member", seat))
    return {"members": expect(out, 9, "Holland")}


# --- Eastpointe -----------------------------------------------------------

def parse_eastpointe(h, also):
    """The article body ends with a list of 'Title Name' links to each
    member's page (Mayor, Mayor Pro Tem, Council Member). The side nav calls
    Rob Baker 'Council Member'; the article list, which is read, calls him
    Mayor Pro Tem. The only phone on the page is the City Manager's office,
    so no office line is set."""
    sec = section(h, r'<article id="entry">', r'</article>')
    out = []
    for t in re.findall(r'<a href= ?"government/mayor_and_council/[^"]+">(.*?)</a>', sec, re.S):
        m = re.fullmatch(r'(Mayor Pro Tem|Mayor|Council Member)\s+(.+)', txt(t))
        if not m:
            raise ValueError("Eastpointe: unexpected link %r" % txt(t))
        out.append(member(clean_name(m.group(2)), role_of(m.group(1))))
    return {"members": expect(out, 5, "Eastpointe")}


# --- Bay City -------------------------------------------------------------

def parse_bay_city(h, also):
    """CivicPlus Members widget: name, 'Commissioner, Nth Ward' (or Mayor),
    Cloudflare-obfuscated e-mail and a phone, for all ten."""
    sec = section(h, r'>\s*Contact the Commissioners\s*</h1>', r'>Ward Map</h3>')
    out = []
    for name, title, blk in hcards(sec):
        m = re.fullmatch(r'Commissioner, (\d)(?:st|nd|rd|th) Ward', title)
        if m:
            role, seat = "Commissioner", "Ward " + m.group(1)
        else:
            role, seat = role_of(title), None
        out.append(member(name, role, seat, one(phones_in(blk)), one(emails_in(blk))))
    return {"members": expect(out, 10, "Bay City")}


# --- Southgate ------------------------------------------------------------

def parse_southgate(h, also):
    """Seven <p><strong>Name</strong> blocks under 'CITY COUNCIL MEMBERS',
    each with a 'click here to contact me' link; three of the links are a
    member's own mailto, the rest point at a generic contact page. Only the
    Council President carries a title. The mayor is on a separate page."""
    sec = section(h, r'<h2>CITY COUNCIL MEMBERS</h2>', r'<hr />')
    out = []
    for m in re.finditer(r'<p><strong>(.*?)</strong>(.*?)</p>', sec, re.S):
        head = txt(m.group(1))
        name, _, title = head.partition(",")
        role = role_of(title) if title.strip() else "Council Member"
        out.append(member(clean_name(name), role, email=one(emails_in(m.group(2)))))
    return {"members": expect(out, 7, "Southgate")}


# --- Oak Park -------------------------------------------------------------

def parse_oak_park(h, also):
    """EvoGov department page: one heading per member, 'Title Name', between
    the 'City Council' title and 'Meeting Dates'. Each member's e-mail is a
    contact form, not an address, so none is set. The page says all are
    elected at large, but no member's own entry does, so no seat is set."""
    sec = section(h, r'id="evo_departments_title_name">City Council</h1>', r'<a id="Meeting">')
    out = []
    for t in re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', sec, re.S):
        m = re.fullmatch(r'(Mayor Pro Tem|Mayor|Council Member)\s+(.+)', txt(t))
        if m:
            out.append(member(clean_name(m.group(2)), role_of(m.group(1))))
    return {"members": expect(out, 5, "Oak Park")}


# --- Port Huron -----------------------------------------------------------

def parse_port_huron(h, also):
    """Blocks under 'Mayor and Council Members': name, title, phone, e-mail,
    'Term Ends'. The mayor is a <p>, the others table cells. TRAP: the
    mayor's tel: link dials a different number from the one printed beside
    it; where a tel: link and the printed number disagree, no phone is set."""
    sec = section(h, r'Mayor and Council Members</h2>', r'About the City Council</h2>')
    out = []
    for chunk in re.split(r'<p>|<td[^>]*>', sec):
        if "Term Ends" not in chunk:
            continue
        lines = [txt(x) for x in re.split(r'<br\s*/?>', chunk)]
        lines = [x for x in lines if x]
        name, title = lines[0], lines[1]
        printed = [phone(m.group(0)) for m in re.finditer(r'\(\d{3}\)\s*\d{3}-\d{4}', txt(chunk))]
        dialled = [phone(x) for x in re.findall(r'href="tel:([^"]+)"', chunk)]
        ph = one(printed)
        if dialled and ph not in dialled:
            ph = None
        out.append(member(clean_name(name), role_of(title), phone_=ph,
                          email=one(emails_in(chunk))))
    return {"members": expect(out, 7, "Port Huron")}


# --- Allen Park -----------------------------------------------------------

def parse_allen_park(h, also):
    """Elected Officials table. The Mayor, City Clerk and City Treasurer sit
    in the first row; the council follows under 'City Council Members', one
    cell each ('Name | Mayor ProTem' or the bare name) with an 'Email
    Councilperson' mailto whose case and spacing vary. Only the cells under
    that heading are the council."""
    sec = section(h, r'<span class="subheader">City Council Members</span>', r'</table>')
    out = []
    for cell in re.findall(r'<td[^>]*>(.*?)</td>', sec, re.S):
        lines = [txt(x) for x in re.split(r'<br\s*/?>', cell)]
        lines = [x for x in lines if x and not x.startswith("Email")]
        if not lines:
            continue
        name, _, title = lines[0].partition("|")
        role = role_of(title) if title.strip() else "Council Member"
        mails = [re.sub(r"\s+", "", e) for e in re.findall(r'(?i)mailto:\s*([^"]+)', cell)]
        out.append(member(clean_name(name), role, email=one(mails)))
    return {"members": expect(out, 6, "Allen Park")}


# --- Madison Heights ------------------------------------------------------

def parse_madison_heights(h, also):
    """CivicPlus Members widget on the City Council page: name, title
    (Mayor, Mayor Pro Tem, Councilwoman/Councilman/Councilor), mailto."""
    sec = section(h, r'>\s*City Council\s*</h1>', r'>Overview</h2>')
    out = []
    for name, title, blk in hcards(sec):
        out.append(member(name, role_of(title), email=one(emails_in(blk))))
    return {"members": expect(out, 7, "Madison Heights")}


# --- Hamtramck ------------------------------------------------------------

def parse_hamtramck(h, also):
    """Two lists on one page: 'Title Name' headings (Mayor, Mayor Pro Tem,
    Councilman) between 'Duties & Responsibilities' and 'Meetings', and
    'Contact Information' cards for the six council members with
    Cloudflare-obfuscated e-mail. The charter text on the page has the mayor
    preside over the council. The cards spell one member 'Abu Musa' where
    the list says 'Abu Ahmed Musa', so a card is joined to a list name when
    all of the card's words are in it."""
    sec = section(h, r'>Duties &amp; Responsibilities</h2>|>Duties & Responsibilities</h2>', r'>Meetings</h2>')
    out = []
    for t in re.findall(r'<h2[^>]*>(.*?)</h2>', sec, re.S):
        m = re.fullmatch(r'(Mayor Pro Tem|Mayor|Councilman|Councilwoman)\s+(.+)', txt(t))
        if m:
            out.append(member(clean_name(m.group(2)), role_of(m.group(1))))
    expect(out, 7, "Hamtramck")
    cards = section(h, r'>Contact Information</h2>', r'>Minutes &amp; Agenda</h2>|>Minutes & Agenda</h2>')
    heads = list(re.finditer(r'<h2[^>]*>(.*?)</h2>', cards, re.S))
    joined = 0
    for i, hd in enumerate(heads):
        cname = txt(hd.group(1))
        if cname in ("Council Member", "Mayor Pro Tem"):
            continue
        body = cards[hd.end():heads[i + 1].start() if i + 1 < len(heads) else len(cards)]
        words = set(cname.lower().split())
        hits = [m for m in out if words <= set(m["name"].lower().split())]
        if len(hits) != 1:
            raise ValueError("Hamtramck: card %r matches %d members" % (cname, len(hits)))
        e = one(emails_in(body))
        if e:
            hits[0]["email"] = e
        joined += 1
    if joined != 6:
        raise ValueError("Hamtramck: %d contact cards, expected 6" % joined)
    return {"members": out}


# --- Garden City ----------------------------------------------------------

def parse_garden_city(h, also):
    """'Members' list of seven 'Name, Title' links to directory entries.
    Two members share the surname Dold. No contact on the page itself."""
    sec = section(h, r'<h2 class="subhead1">Members</h2>', r'</ul>')
    out = []
    for t in re.findall(r'<li><a [^>]*>(.*?)</a></li>', sec, re.S):
        name, _, title = txt(t).partition(",")
        out.append(member(clean_name(name), role_of(title)))
    return {"members": expect(out, 7, "Garden City")}


# --- Inkster --------------------------------------------------------------

def parse_inkster(h, also):
    """CivicPlus widget 'Mayor & City Council Members': name, title
    ('Council Member - District N'), mailto and phone. The City Clerk is in
    the same widget and is left out. The page's quoted charter text says the
    six are elected at large while every member is labelled with a district.
    The page contradicts itself about how the council is elected, so no seat
    ships: the district is still READ (the label must parse, or the page has
    changed shape) and then left off, because a card saying "District 3" for
    a member the charter elects citywide would tell a reader something false
    either way."""
    sec = section(h, r'>Mayor &amp; City Council Members</a></h3>', r'>About</h2>')
    out, clerk = [], 0
    for name, title, blk in hcards(sec):
        if title == "City Clerk":
            clerk += 1
            continue
        m = re.fullmatch(r'(?:(Mayor Pro Tem)\. / )?Council Member - District (\d)', title)
        if m:
            role, seat = m.group(1) or "Council Member", None
        else:
            role, seat = role_of(title), None
        out.append(member(name, role, seat, one(phones_in(blk)), one(emails_in(blk))))
    if clerk != 1:
        raise ValueError("Inkster: expected the City Clerk once in the widget")
    return {"members": expect(out, 7, "Inkster")}


# --- Romulus --------------------------------------------------------------

def parse_romulus(h, also):
    """Council page: one editor block per member under 'Members', a heading
    'Name<br>Title' (Tina Talley's in two headings) and a Directory.aspx?EID
    link. The council department directory (also[0]) gives each member a
    Cloudflare-obfuscated e-mail and the council line with the member's own
    extension, joined on the EID. TRAP: the directory calls Tina Talley
    'Councilwoman'; the council page's 'Mayor Pro Tem' is used. The mayor is
    on a separate page and is not a council member."""
    start = h.find('<h2 class="subhead1 ">Members</h2>')
    if start < 0:
        raise ValueError("Romulus: 'Members' heading not found")
    sec = h[start:]
    out, eids = [], []
    for blk in re.findall(r'<div class="fr-view">(.*?)</div>', sec, re.S):
        eid = re.search(r'(?i)directory\.aspx\?EID=(\d+)', blk)
        heads = re.findall(r'<h3[^>]*>(.*?)</h3>', blk, re.S)
        if not eid or not heads:
            continue
        lines = []
        for hd in heads:
            lines += [txt(x) for x in re.split(r'<br\s*/?>', hd)]
        lines = [x for x in lines if x]
        if len(lines) != 2:
            raise ValueError("Romulus: unexpected heading %r" % lines)
        out.append(member(clean_name(lines[0]), role_of(lines[1])))
        eids.append(eid.group(1))
    expect(out, 7, "Romulus")
    if not also:
        raise ValueError("Romulus: the directory page was not read")
    directory = also[0].split("Back to Directory")[0]
    head = re.search(r'Phone Number\s*(\d{3}-\d{3}-\d{4})', txt(directory.split('<li class="list-group-item')[0]))
    rows = {}
    for row in re.split(r'<li class="list-group-item', directory)[1:]:
        e = re.search(r'/m/directory/employee\?eid=(\d+)', row)
        if e:
            rows[e.group(1)] = row
    for m, eid in zip(out, eids):
        row = rows.get(eid)
        if row is None:
            raise ValueError("Romulus: %s (EID %s) not in the directory" % (m["name"], eid))
        if m["name"].split()[-1] not in txt(row):
            raise ValueError("Romulus: directory EID %s does not name %s" % (eid, m["name"]))
        # The council line with the member's own extension; the comma
        # before "ext." defeats the shared phone parser, so it is read here.
        exts = re.findall(r'href="tel:(\d{3}-\d{3}-\d{4}),?\s*ext\.?\s*(\d+)', row)
        p = (phone(exts[0][0]) + " ext. " + exts[0][1]) if len(exts) == 1 else None
        e = one(emails_in(row))
        if p:
            m["phone"] = p
        if e:
            m["email"] = e
    roster = {"members": out}
    if head:
        roster["office"] = {"phone": phone(head.group(1))}
    return roster


# --- Walker ---------------------------------------------------------------

def parse_walker(h, also):
    """The Elected City Officials page is a sub-page menu of seven 'Title
    Name' links ('Mayor', 'Mayor Pro Tem', 'Ward N Commissioner'). The Mayor
    Pro Tem's title omits her ward and no seat is set for her. Individual
    contact is on each member's page (not read); the group mailto to the
    whole commission lists addresses, not one shared line, so no office
    e-mail is set."""
    if "Meet the City of Walker Commission" not in txt(h):
        raise ValueError("Walker: commission heading text not found")
    sec = section(h, r'<ol role="menu" id="secondaryMenusecondaryNav"', r'</ol>')
    titles = [txt(t) for t in re.findall(
        r'class="navMainItem secondaryNavItem[^"]*"[^>]*>(.*?)</a>', sec, re.S)]
    # The commission's seven come first; the menu goes on with the City
    # Clerk and two pages that are not people.
    clerk = [i for i, t in enumerate(titles) if t.startswith("City Clerk")]
    if not clerk:
        raise ValueError("Walker: the City Clerk entry that ends the commission list is missing")
    out = []
    for t in titles[:clerk[0]]:
        m = re.fullmatch(r'(Mayor Pro Tem|Mayor)\s+(.+)', t)
        w = re.fullmatch(r'Ward (\d) Commissioner\s+(.+)', t)
        if m:
            out.append(member(clean_name(m.group(2)), role_of(m.group(1))))
        elif w:
            out.append(member(clean_name(w.group(2)), "Commissioner", "Ward " + w.group(1)))
        else:
            raise ValueError("Walker: unexpected menu title %r" % t)
    return {"members": expect(out, 7, "Walker")}


# --- Wyandotte ------------------------------------------------------------

def parse_wyandotte(h, also):
    """CivicPlus directory widgets under the 'Members' subhead, one per
    member: name and title only (contact is on directory entries, not read).
    The 'Mayor & City Council' contact card further down carries the body's
    own phone line."""
    sec = section(h, r'<h2 class="subhead1 ">Members</h2>', r'>Overview</h2>')
    out = []
    for name, title, blk in hcards(sec):
        out.append(member(name, role_of(title)))
    expect(out, 7, "Wyandotte")
    roster = {"members": out}
    card = re.search(r'p-name">Mayor &amp; City Council</h4>(.*?)</li>|p-name">Mayor &amp; City Council</h4>(.*?)$',
                     h, re.S)
    if card:
        body = card.group(1) or card.group(2) or ""
        tel = re.search(r'class="field p-tel">(.*?)</div>', body, re.S)
        p = phone(txt(tel.group(1))) if tel else None
        if p:
            roster["office"] = {"phone": p}
    return roster


def _u(geoid, name, body, url, seats, parse, also=None):
    unit = {"geoid": geoid, "name": name, "kind": "city", "body": body,
            "url": url, "seats": seats, "parse": parse}
    if also:
        unit["also"] = also
    return unit


UNITS = [
    _u("2669800", "Roseville", "City Council",
       "https://www.roseville-mi.gov/228/City-Council", 7, parse_roseville),
    _u("2670520", "Saginaw", "City Council",
       "https://www.saginaw-mi.com/230/City-Council", 9, parse_saginaw),
    _u("2653780", "Midland", "City Council",
       "https://www.cityofmidlandmi.gov/422/City-Council", 5, parse_midland),
    _u("2647800", "Lincoln Park", "City Council",
       "https://www.citylp.com/162/Elected-Officials", 6, parse_lincoln_park),
    _u("2656320", "Muskegon", "City Commission",
       "https://muskegon-mi.gov/city-services/elected-officials/city-commission/", 7,
       parse_muskegon),
    _u("2638640", "Holland", "City Council",
       "https://www.cityofholland.com/941/ContactLearn-about-Council-Members", 9,
       parse_holland),
    _u("2624290", "Eastpointe", "City Council",
       "https://www.eastpointemi.gov/government/mayor_and_council/index.php", 5,
       parse_eastpointe),
    _u("2606020", "Bay City", "City Commission",
       "https://www.baycitymi.gov/377/Contact-the-Commissioners", 10, parse_bay_city),
    _u("2674960", "Southgate", "City Council",
       "https://www.southgatemi.gov/government/city_council/index.php", 7, parse_southgate),
    _u("2659920", "Oak Park", "City Council",
       "https://www.oakparkmi.gov/departments/city-council", 5, parse_oak_park),
    _u("2665820", "Port Huron", "City Council",
       "https://www.porthuron.org/government/city_council.php", 7, parse_port_huron),
    _u("2601380", "Allen Park", "City Council",
       "https://www.cityofallenpark.org/government/elected_officials.php", 6,
       parse_allen_park),
    _u("2650560", "Madison Heights", "City Council",
       "https://www.madisonheightsmi.gov/408/City-Council", 7, parse_madison_heights),
    _u("2636280", "Hamtramck", "City Council",
       "https://hamtramckcity.gov/city/city-council/", 7, parse_hamtramck),
    _u("2631420", "Garden City", "City Council",
       "https://gardencitymi.org/256/Mayor-City-Council", 7, parse_garden_city),
    _u("2640680", "Inkster", "City Council",
       "https://www.cityofinkstermi.gov/368/City-Council", 7, parse_inkster),
    _u("2669420", "Romulus", "City Council",
       "https://www.romulusgov.com/320/City-Council", 7, parse_romulus,
       also=["https://www.romulusgov.com/m/directory/department?did=9"]),
    _u("2682960", "Walker", "City Commission",
       "https://www.walker.city/325/Elected-City-Officials", 7, parse_walker),
    _u("2688900", "Wyandotte", "City Council",
       "https://www.wyandottemi.gov/168/Mayor-City-Council", 7, parse_wyandotte),
]
