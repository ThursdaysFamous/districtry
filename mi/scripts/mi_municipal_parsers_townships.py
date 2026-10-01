"""Unit table and parsers: the townships. Contract in mi_municipal_common.py.

A Michigan township board is the supervisor, the clerk, the treasurer and the
trustees (MCL 41.70, 42.5), and every one of them is a voting member, so every
parser here returns all of them and `_finish` refuses a roster that does not
hold exactly one supervisor, one clerk, one treasurer and at least one trustee.

Each page was read on 2026-10-01 and `seats` is what that page published that
day. Three townships name only the four trustees on their board page and the
supervisor, clerk and treasurer elsewhere, so their units read more than one
page through `also`: Independence and White Lake read the board page plus one
page per officer (four requests), and Gaines reads the trustees page plus the
staff directory, which names all three officers (two requests).
"""

import html as _html
import re

from mi_municipal_common import (cf_decode, member, phone, phones_in, txt)

OFFICE_RE = re.compile(r"\b(Supervisor|Clerk|Treasurer|Trustee)s?\b", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HONORIFIC = re.compile(r"^(?:Dr|Hon|Mr|Mrs|Ms)\.?\s+", re.I)
# A professional credential printed after a name ("Evan Hope, CMC",
# "Kristi L. Pozzi, MiPMC"). Jr./Sr./II/III/IV are part of the name and stay.
CREDENTIAL = re.compile(r",\s*(?!(?:Jr|Sr|II|III|IV)\b)(?:Mi)?[A-Z]{2,6}\s*$")


def _need(cond, what):
    if not cond:
        raise ValueError(what)


def _section(h, start, end=None, what="section"):
    """The text of the page from the first `start` match to the next `end`
    match after it. Raises when either anchor is missing."""
    m = re.search(start, h, re.S)
    _need(m, "%s: anchor %r not on the page" % (what, start))
    rest = h[m.end():]
    if end is None:
        return rest
    e = re.search(end, rest, re.S)
    _need(e, "%s: end anchor %r not found after %r" % (what, end, start))
    return rest[:e.start()]


def _role(s):
    """The office named in a label, normalised to the board's four words."""
    m = OFFICE_RE.search(txt(s))
    _need(m, "no township office in %r" % txt(s)[:80])
    return m.group(1).title()


def _name(s):
    """A person's name with honorifics and trailing credentials removed."""
    n = txt(s).strip(" ,;:-–")
    n = HONORIFIC.sub("", n)
    # A nickname printed in parentheses ("Elizabeth (Beth) S. Bowen") is
    # written in quotes, the form other pages here use ("Sebastian 'Sam'").
    n = re.sub(r"\(([A-Za-z.'\- ]+)\)", r"'\1'", n)
    n = CREDENTIAL.sub("", n).strip(" ,")
    return n


def _email(fragment):
    """The one address a member's own block carries, or None. A link whose
    href and visible text name different addresses is a contradiction on the
    page, and neither address is taken."""
    frag = re.sub(r"mailto:(?:\s|%20)+", "mailto:", fragment or "", flags=re.I)
    hrefs, texts = [], []
    for m in re.finditer(r'mailto:([^"\'?>\s]+)', frag, re.I):
        hrefs.append(_html.unescape(m.group(1)))
    for m in re.finditer(r"email-protection#([0-9a-fA-F]+)", frag):
        hrefs.append(cf_decode(m.group(1)))
    for m in re.finditer(r'data-cfemail="([0-9a-fA-F]+)"', frag):
        texts.append(cf_decode(m.group(1)))
    texts.extend(EMAIL_RE.findall(txt(frag)))

    def norm(lst):
        out = []
        for e in lst:
            if not e or "@" not in e:
                continue
            e = e.strip().strip(".").lower()
            if e not in out:
                out.append(e)
        return out

    hrefs, texts = norm(hrefs), norm(texts)
    if hrefs and texts and set(hrefs) != set(texts):
        return None
    found = hrefs or texts
    return found[0] if len(found) == 1 else None


def _finish(members, office=None):
    """Move any phone or address printed for two or more members to the
    board's shared line, check the board's shape, and return the roster."""
    office = dict(office or {})
    for field in ("phone", "email"):
        counts = {}
        for m in members:
            if m.get(field):
                counts[m[field]] = counts.get(m[field], 0) + 1
        for value, n in counts.items():
            if n < 2:
                continue
            office.setdefault(field, value)
            for m in members:
                if m.get(field) == value:
                    del m[field]
    roles = [m["role"] for m in members]
    for one in ("Supervisor", "Clerk", "Treasurer"):
        _need(roles.count(one) == 1, "%d members with role %s" % (roles.count(one), one))
    _need(roles.count("Trustee") >= 1, "no trustee on the page")
    roster = {"members": members}
    if office:
        roster["office"] = office
    return roster


def _split_label(text):
    """'Name, Office ...' or 'Name Office ...' -> (name, role)."""
    m = OFFICE_RE.search(text)
    _need(m, "no township office in %r" % text[:80])
    name = re.sub(r"\b(?:Township|MiPMC)\b", "", text[:m.start()])
    return _name(name), m.group(1).title()


def _hcards(h):
    """CivicPlus staff-directory cards: (name, job title, block html)."""
    out = []
    for m in re.finditer(r'<li class="widgetItem h-card">(.*?)</li>', h, re.S):
        b = m.group(1)
        n = re.search(r'p-name">(.*?)</h4>', b, re.S)
        j = re.search(r'p-job-title">(.*?)</div>', b, re.S)
        out.append((txt(n.group(1)) if n else "", txt(j.group(1)) if j else "", b))
    return out


# ---------------------------------------------------------------- parsers

def parse_clinton(h, also):
    """CivicPlus 'Current Board' staff-directory cards (two widgets: the three
    officers, then the four trustees). Trap: one mailto carries a space after
    the colon ('mailto: d.kress@...'); a treasurer prints as 'Dr. Mike Aiello'."""
    seg = _section(h, r">Current Board<", None, "Clinton")
    cards = [c for c in _hcards(seg) if c[1]]
    _need(len(cards) == 7, "Clinton: %d board cards, expected 7" % len(cards))
    return _finish([member(_name(n), _role(j), email=_email(b)) for n, j, b in cards])


def parse_canton(h, also):
    """Editor blocks under 'Full-Time Trustees' / 'Part-Time Trustees', each
    '<a Directory>Name</a>, Township Office' then 'Term Expires'. Trap: the
    clerk also has an aria-hidden directory link holding only hidden text, so
    a link counts only when an office follows it."""
    seg = _section(h, r"Full-Time\s*(?:&nbsp;)?\s*Trustees", r"Board Overview", "Canton")
    out = []
    for m in re.finditer(r'<a\b[^>]*Directory\.aspx\?EID=\d+[^>]*>((?:(?!</a>).)*)</a>'
                         r'((?:\s|,|&nbsp;|<br\s*/?>)*)((?:Township\s+)?'
                         r'(?:Supervisor|Clerk|Treasurer|Trustee))\b', seg, re.S | re.I):
        out.append(member(_name(m.group(1)), _role(m.group(3))))
    _need(len(out) == 7, "Canton: %d members, expected 7" % len(out))
    return _finish(out)


def _members_list(h, start, end, what):
    """<li> rows 'Name, Office' between two anchors (CivicPlus editor lists)."""
    seg = _section(h, start, end, what)
    rows = re.findall(r"<li\b[^>]*>(.*?)</li>", seg, re.S)
    out = []
    for r in rows:
        t = txt(r)
        if not OFFICE_RE.search(t):
            continue
        name, role = _split_label(t)
        out.append(member(name, role, email=_email(r)))
    return out


def parse_macomb(h, also):
    """'Members' <ul>: '<a directory>Name</a>, Office'. Trap: the clerk reads
    'Kristi L. Pozzi, MiPMC, Clerk' (credential before the office)."""
    out = _members_list(h, r">Members</h2>", r"</ul>", "Macomb")
    _need(len(out) == 7, "Macomb: %d members, expected 7" % len(out))
    return _finish(out)


def parse_waterford(h, also):
    """'Members' lists split across two editor widgets, each row 'Name, Township
    Office' + 'Term Expires'. Only the clerk's name is a mailto. The board's
    shared address is the 'Email the Board' link in the Contact Us widget."""
    out = _members_list(h, r">Members</h2>", r"Trustee Responsibilities", "Waterford")
    _need(len(out) == 7, "Waterford: %d members, expected 7" % len(out))
    office = {}
    m = re.search(r'href="mailto:(trustees@waterfordmi\.gov)"', h)
    if m:
        office["email"] = m.group(1)
    return _finish(out, office)


def parse_georgetown(h, also):
    """'Members' <ul>: 'Name, Office'. Link titles carry stale names (a
    treasurer's link is titled 'Trustee Michael Bosch'), so only the link
    TEXT is read. The board's address is board@georgetown-mi.gov."""
    out = _members_list(h, r">Members</h2>", r"</ul>", "Georgetown")
    _need(len(out) == 7, "Georgetown: %d members, expected 7" % len(out))
    office = {}
    if "mailto:board@georgetown-mi.gov" in h:
        office["email"] = "board@georgetown-mi.gov"
    return _finish(out, office)


def parse_redford(h, also):
    """CivicPlus staff-directory cards, one per member with e-mail and (for
    the three officers) a phone; one further card titled 'Board of Trustees'
    has no job title and is not a person."""
    cards = [c for c in _hcards(h) if c[1]]
    _need(len(cards) == 7, "Redford: %d board cards, expected 7" % len(cards))
    out = []
    for n, j, b in cards:
        ph = phones_in(b)
        out.append(member(_name(n), _role(j), phone_=ph[0] if ph else None, email=_email(b)))
    return _finish(out)


def parse_chesterfield(h, also):
    """'Elected Officials' page: an <h2> per office, each followed by a <ul> of
    names; the four trustees share one 'Trustees' heading."""
    seg = _section(h, r"<h2>Township Supervisor</h2>", r"</div>", "Chesterfield")
    out = []
    for hd, body in re.findall(r"<h2>(.*?)</h2>\s*<ul[^>]*>(.*?)</ul>", "<h2>Township Supervisor</h2>" + seg, re.S):
        role = _role(hd)
        for li in re.findall(r"<li\b[^>]*>(.*?)</li>", body, re.S):
            out.append(member(_name(li), role))
    _need(len(out) == 7, "Chesterfield: %d members, expected 7" % len(out))
    return _finish(out)


def parse_bloomfield(h, also):
    """One Bootstrap card per member: name div, office div, an e-mail
    paragraph, then a BIO modal. Trap: two mailto hrefs start with '%20'.
    Only the part of each card before its modal is read."""
    chunks = re.split(r'<div class="fs-6 fw-bold lh-1 mb-2">', h)[1:]
    out = []
    for c in chunks:
        c = c.split('class="modal', 1)[0]
        name = c.split("</div>", 1)[0]
        office = re.search(r'<div class="fs-8 text-uppercase[^"]*">(.*?)</div>', c, re.S)
        _need(office, "Bloomfield: a card with no office line")
        out.append(member(_name(name), _role(office.group(1)), email=_email(c)))
    _need(len(out) == 7, "Bloomfield: %d cards, expected 7" % len(out))
    return _finish(out)


def parse_meridian(h, also):
    """The page's 'Contact Us' pod: one <p> per member, '<strong>Name</strong>
    <br>Township Office<br>e-mail<br>phone'. It is followed by a 'Staff' pod
    naming the Township Manager, who is not on the board. The four trustees
    and the supervisor print the township's main line, which goes to office."""
    seg = _section(h, r'c3-heading\s*"\s*>Contact Us</p>', r'c3-heading\s*"\s*>Staff</p>', "Meridian")
    out = []
    for p in re.findall(r"<p>(.*?)</p>", seg, re.S):
        nm = re.search(r"<strong>(.*?)</strong>", p, re.S)
        _need(nm, "Meridian: a contact paragraph with no name")
        rest = p[nm.end():]
        ph = phones_in(rest)
        out.append(member(_name(nm.group(1)), _role(rest.split("<a", 1)[0]),
                          phone_=ph[0] if ph else None, email=_email(rest)))
    _need(len(out) == 7, "Meridian: %d members, expected 7" % len(out))
    return _finish(out)


def parse_commerce(h, also):
    """'Board Members:' heading, then one <p> per member 'Name - Office' with
    'email:' below; the list ends at the meeting-location paragraph."""
    seg = _section(h, r"<h2>Board Members:</h2>", r"Meetings Located at", "Commerce")
    out = []
    for p in re.findall(r"<p>(.*?)</p>", seg, re.S):
        head = txt(p.split("<br", 1)[0])
        name, role = _split_label(head)
        out.append(member(name, role, email=_email(p)))
    _need(len(out) == 7, "Commerce: %d members, expected 7" % len(out))
    return _finish(out)


def parse_saginaw(h, also):
    """A layout table with one <h3> per member: 'Name<br><strong>Office</strong>
    <span>tenure</span>'. No per-member contact; the page closes with the
    township's main line ('ask for the Board Member'), the board's shared
    phone. The clerk and treasurer office mailboxes printed there are not in
    either member's own block and are not carried."""
    seg = _section(h, r'<h1 class="page-title">Board of Trustees</h1>', r"To Contact Members of the Board", "Saginaw")
    out = []
    for h3 in re.findall(r"<h3>(.*?)</h3>", seg, re.S):
        parts = re.split(r"<br\s*/?>", h3, maxsplit=1)
        _need(len(parts) == 2, "Saginaw: an <h3> without a name/office break")
        out.append(member(_name(parts[0]), _role(parts[1])))
    _need(len(out) == 7, "Saginaw: %d members, expected 7" % len(out))
    tail = _section(h, r"To Contact Members of the Board", r"</article>", "Saginaw contact")
    ph = phones_in(tail.split("Email", 1)[0])
    return _finish(out, {"phone": ph[0]} if ph else None)


def parse_grand_blanc(h, also):
    """CivicPlus staff-directory cards under '2024 to 2028 Township Board':
    name and office only, no contact on the page."""
    cards = [c for c in _hcards(h) if c[1]]
    _need(len(cards) == 7, "Grand Blanc: %d board cards, expected 7" % len(cards))
    return _finish([member(_name(n), _role(j)) for n, j, b in cards])


def parse_pittsfield(h, also):
    """'Members' <ul>: 'Name, Office'; five names are mailto links, the clerk
    and treasurer link to their office pages."""
    out = _members_list(h, r">Members</h2>", r"</ul>", "Pittsfield")
    _need(len(out) == 7, "Pittsfield: %d members, expected 7" % len(out))
    return _finish(out)


def parse_holland(h, also):
    """'Elected Officials' list in the page body's left column: one <p> per
    member, '<a contact form>Name - Office</a>'. The same list also sits in
    the site's dropdown menu (read only the copy inside et-main-area). Names
    link to a contact form; no address or phone is printed."""
    seg = _section(h, r'id="et-main-area"', None, "Holland")
    seg = _section(seg, r'<a href="/elected-a-appointed/">Elected Officials</a></p>', r"</div>", "Holland list")
    out = []
    for a in re.findall(r'<a href="/contact-us/\?specific_official=[^"]*">(.*?)</a>', seg, re.S):
        name, role = _split_label(txt(a))
        out.append(member(name, role))
    _need(len(out) == 7, "Holland: %d members, expected 7" % len(out))
    return _finish(out)


def parse_orion(h, also):
    """'Board Members' table: per member a cell with the office in bold, then
    '<a mailto>Name</a>', then 'Board Representative for:'. The 'email
    entire Board' link above it carries seven addresses and is not read."""
    seg = _section(h, r'<span class="subheader">Board Members', r"</table>", "Orion")
    out = []
    for cell in re.findall(r'<td[^>]*colspan="3"[^>]*>(.*?)</td>', seg, re.S):
        a = re.search(r'<a\b[^>]*href="mailto:[^"]*"[^>]*>(.*?)</a>', cell, re.S)
        if not a:
            continue
        head = cell[:a.start()]
        block = cell.split("Board Representative", 1)[0]
        out.append(member(_name(a.group(1)), _role(head), email=_email(block)))
    _need(len(out) == 7, "Orion: %d members, expected 7" % len(out))
    return _finish(out)


def parse_plainfield(h, also):
    """CivicPlus 'Contact Us' staff-directory cards: a first card titled
    'Board of Trustees' carries the township's address and phone (the board's
    shared line), then one card per member with name and office only."""
    cards = _hcards(h)
    board = [b for n, j, b in cards if not j and n == "Board of Trustees"]
    people = [c for c in cards if c[1]]
    _need(len(people) == 7, "Plainfield: %d member cards, expected 7" % len(people))
    office = {}
    if board:
        ph = phones_in(board[0])
        if ph:
            office["phone"] = ph[0]
    return _finish([member(_name(n), _role(j)) for n, j, b in people], office)


def parse_brownstown(h, also):
    """The only place the page names members is its side menu under the
    'Board of Trustees' heading: 'Supervisor Name', 'Clerk Name', 'Treasurer
    Name', then four bare names whose links sit under /board_of_trustees/.
    The body text states the board has seven members of whom three serve as
    supervisor, clerk and treasurer, so the four unlabelled names are the
    trustees. Trap: David Chapman's link slug is maureen_brinker.php, so the
    name is read from the link text, never the URL."""
    seg = _section(h, r'<h2 id="flyout-header">Board of Trustees</h2>', r"</ul>", "Brownstown")
    _need(re.search(r"governed by a seven-member Board of Trustees", h),
          "Brownstown: the 'seven-member Board' sentence is gone")
    out = []
    for href, a in re.findall(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', seg, re.S):
        t = txt(a)
        m = re.match(r"^(Supervisor|Clerk|Treasurer)\s+(.+)$", t)
        if m:
            out.append(member(_name(m.group(2)), m.group(1)))
        elif "/board_of_trustees/" in href and not OFFICE_RE.search(t):
            out.append(member(_name(t), "Trustee"))
        else:
            raise ValueError("Brownstown: unexpected menu entry %r" % t)
    _need(len(out) == 7, "Brownstown: %d members, expected 7" % len(out))
    return _finish(out)


def parse_delta(h, also):
    """'Delta Township Board of Trustees': per member a bold name, bold office,
    'email:' link and a biography, members separated by <hr />. The
    biographies name other people, so only the text before 'email:' is read
    for the name and office."""
    seg = _section(h, r'<div id="post" class="clearfix">', r"</main>", "Delta")
    out = []
    for chunk in re.split(r"<hr\s*/?>", seg):
        if "email:" not in chunk:
            continue
        head = txt(chunk.split("email:", 1)[0])
        name, role = _split_label(head)
        mail = chunk.split("email:", 1)[1]
        mail = mail[:mail.find("</strong>")] if "</strong>" in mail else mail[:400]
        out.append(member(name, role, email=_email(mail)))
    _need(len(out) == 7, "Delta: %d members, expected 7" % len(out))
    return _finish(out)


def parse_flint(h, also):
    """Revize FAQ group 'Board of Trustees Members': one item per member whose
    header reads 'Name, Office' and whose answer carries 'Contact:' with an
    address. Trap: Jenna McIntire's mailto href is tamadou@ while its text
    reads Jmcintire@, so that link is a contradiction and carries no address."""
    seg = _section(h, r">Board of Trustees Members</a>", r'<div class="faq-category"|</main>', "Flint")
    items = re.split(r'<div class="faq-item">', seg)[1:]
    out = []
    for it in items:
        hd = re.search(r'class="faq-question-header"[^>]*>(.*?)</a>', it, re.S)
        _need(hd, "Flint: an FAQ item with no header")
        name, role = _split_label(txt(hd.group(1)))
        contact = it.split("Contact:", 1)
        mail = None
        if len(contact) == 2:
            mail = _email(contact[1].split("</a>", 1)[0] + "</a>")
        out.append(member(name, role, email=mail))
    _need(len(out) == 7, "Flint: %d members, expected 7" % len(out))
    return _finish(out)


def parse_van_buren(h, also):
    """'VBT Elected Officials' table: per cell a bold office, the name, a
    phone for the three officers and an e-mail. Trap: Kevin Martin's mailto
    href is the bare domain 'vbtmi.gov' while the text reads kmartin@vbtmi.gov;
    the visible address is the only address there, so it is the one kept."""
    seg = _section(h, r'<h1 id="page-title">VBT Elected Officials</h1>', r"</table>", "Van Buren")
    out = []
    for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", seg, re.S):
        role = re.search(r"(?:<br\s*/?>|<strong>)\s*(Supervisor|Clerk|Treasurer|Trustee)\s*</strong>", cell)
        if not role:
            continue
        after = cell[role.end():]
        name = re.split(r"<strong>", after, maxsplit=1)[0]
        ph = phones_in(after.split("E-mail", 1)[0])
        out.append(member(_name(name), role.group(1),
                          phone_=ph[0] if ph else None, email=_email(after)))
    _need(len(out) == 7, "Van Buren: %d members, expected 7" % len(out))
    return _finish(out)


def parse_washington(h, also):
    """'Meet your Charter Township of Washington Board of Trustees for term
    2024 to 2028': one link per member, 'Name, Office', ending at the next
    <hr />. Trap: the board-wide link's href is trustees@ while its text
    reads comments@, so no shared address is carried."""
    seg = _section(h, r"Meet your Charter Township of Washington Board of Trustees", r"<hr\s*/?>", "Washington")
    out = []
    for a in re.findall(r"<a\b[^>]*>(.*?)</a>", seg, re.S):
        t = txt(a)
        if not t:
            continue
        name, role = _split_label(t)
        out.append(member(name, role))
    _need(len(out) == 7, "Washington: %d members, expected 7" % len(out))
    return _finish(out)


def parse_plymouth(h, also):
    """Photo blocks in a flex row, each an e-mail link reading 'Office<br>
    Name' (the clerk's office is a span before the link). Trap: one link
    reads 'TrusteeJohn Stewart' with no space. The side menu calls the
    supervisor 'Charles Curmi'; the block's 'Chuck Curmi' is read. The
    'Send e-mail to Board of Trustees' address is the board's shared one."""
    seg = _section(h, r'<div id="post" class="clearfix">', r"Send e-mail to Board of Trustees", "Plymouth")
    blocks = re.split(r'<div style="text-align: center; width: 150px;">', seg)[1:]
    out = []
    for b in blocks:
        # Each block ends at its own </div>; the last one would otherwise run
        # into the board-wide 'Send e-mail' link.
        b = b.split("</div>", 1)[0]
        m = re.match(r"^\s*(Supervisor|Clerk|Treasurer|Trustee)\s*(.+)$", txt(b))
        _need(m, "Plymouth: a block reading %r" % txt(b)[:60])
        out.append(member(_name(m.group(2)), m.group(1), email=_email(b)))
    _need(len(out) == 7, "Plymouth: %d members, expected 7" % len(out))
    office = {}
    g = re.search(r'href="mailto:(Group-BoardOfTrustees@plymouthtownshipmi\.gov)"', h, re.I)
    if g:
        office["email"] = g.group(1).lower()
    return _finish(out, office)


def parse_delhi(h, also):
    """One editor widget per member: 'Township Office', bold name, photo,
    'Email Name' mailto link, then year first elected and term. Trap: the
    clerk's name carries his credential ('Evan Hope, CMC')."""
    out = []
    for w in re.findall(r'<div class="fr-view">(.*?)</div>', h, re.S):
        lead = re.match(r'\s*<p[^>]*><span[^>]*>\s*(Township (?:Supervisor|Clerk|Treasurer|Trustee))\s*</span>', w)
        if not lead:
            continue
        nm = re.search(r"<strong>(.*?)</strong>", w, re.S)
        _need(nm, "Delhi: a member widget with no bold name")
        out.append(member(_name(nm.group(1)), _role(lead.group(1)), email=_email(w)))
    _need(len(out) == 7, "Delhi: %d members, expected 7" % len(out))
    return _finish(out)


def parse_byron(h, also):
    """Plain text under the 'Township Board' title: '<strong>OFFICE</strong>
    <br>Name<br>Office<br>e-mail<br>phone' for the three officers, then a
    table of the four trustees with name, 'Trustee' and phone. Every trustee
    prints the township's main line, which goes to office."""
    seg = _section(h, r'<div id="post" class="clearfix">', r"</article>", "Byron")
    out = []
    for blk in re.findall(r"<strong>(SUPERVISOR|CLERK|TREASURER)</strong>(.*?)<br\s*/?>\s*<br\s*/?>", seg, re.S):
        lines = [txt(x) for x in re.split(r"<br\s*/?>", blk[1]) if txt(x)]
        _need(len(lines) >= 2, "Byron: an officer block with no name")
        ph = phones_in(blk[1])
        out.append(member(_name(lines[0]), _role(blk[0]),
                          phone_=ph[0] if ph else None, email=_email(blk[1])))
    for td in re.findall(r"<td>(.*?)</td>", seg, re.S):
        lines = [txt(x) for x in re.split(r"<br\s*/?>", td) if txt(x)]
        _need(len(lines) >= 2 and _role(lines[1]) == "Trustee", "Byron: trustee cell reads %r" % lines)
        ph = phones_in(td)
        out.append(member(_name(lines[0]), "Trustee", phone_=ph[0] if ph else None))
    _need(len(out) == 7, "Byron: %d members, expected 7" % len(out))
    return _finish(out)


def parse_allendale(h, also):
    """Elementor containers after the 'Elected Officials.' heading, one per
    member: an <h2> office, a <p> name, a phone for the three officers and a
    Cloudflare-obfuscated e-mail. The list ends at the first container whose
    heading is not an office ('BOARD OF TRUSTEES', the meetings section); the
    same names repeat lower on the page and are not read."""
    seg = _section(h, r">Elected Officials\.</h2>", None, "Allendale")
    out = []
    for part in re.split(r'data-element_type="container"', seg)[1:]:
        hd = re.search(r"<h2[^>]*>(.*?)</h2>", part, re.S)
        if not hd and not out:
            continue
        if not hd or not re.match(r"^(Supervisor|Clerk|Treasurer|Trustee)$", txt(hd.group(1)), re.I):
            break
        nm = re.search(r"<p>(.*?)</p>", part, re.S)
        _need(nm, "Allendale: an office container with no name")
        ph = phones_in(part)
        out.append(member(_name(nm.group(1)), _role(hd.group(1)),
                          phone_=ph[0] if ph else None, email=_email(part)))
    _need(len(out) == 7, "Allendale: %d members, expected 7" % len(out))
    return _finish(out)


def parse_blackman(h, also):
    """'Elected Officials' page: one Beaver Builder photo per member with the
    caption 'Office Name'. No contact is printed."""
    seg = _section(h, r'<h1 class="entry-title"[^>]*>Elected Officials</h1>', r"</article>", "Blackman")
    out = []
    for cap in re.findall(r'class="fl-photo-caption[^"]*">(.*?)</div>', seg, re.S):
        m = re.match(r"^(Supervisor|Clerk|Treasurer|Trustee)\s+(.+)$", txt(cap))
        _need(m, "Blackman: a caption reading %r" % txt(cap))
        out.append(member(_name(m.group(2)), m.group(1)))
    _need(len(out) == 7, "Blackman: %d members, expected 7" % len(out))
    return _finish(out)


def parse_independence(h, also):
    """Board page: the four trustees as '<strong>Name, Trustee</strong>', each
    followed by a mailto and a tel: link. The supervisor, clerk and treasurer
    are each on their own department page (`also`, in that order). Traps: the
    treasurer prints as 'Paul A Brown CPA, Treasurer' (credential with no
    comma), and the clerk and treasurer pages list deputies and staff, so only
    the cell naming the office itself is read."""
    _need(len(also) == 3, "Independence: %d officer pages, expected 3" % len(also))
    seg = _section(h, r"Board of Trustees are:", r"Sign up here to receive updates", "Independence")
    heads = list(re.finditer(r"<strong>((?:(?!</strong>).)*?),\s*Trustee\s*(?:<br\s*/?>)?\s*</strong>",
                             seg, re.S))
    _need(len(heads) == 4, "Independence: %d trustee headings, expected 4" % len(heads))
    out = []
    for i, m in enumerate(heads):
        block = seg[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(seg)]
        ph = phones_in(block)
        _need(len(ph) <= 1, "Independence: %d phones for one trustee" % len(ph))
        out.append(member(_name(m.group(1)), "Trustee",
                          phone_=ph[0] if ph else None, email=_email(block)))

    sup, clk, trs = also
    m = re.search(r"Township Supervisor\s*<br\s*/?>\s*((?:(?!</td>).)*?)\s*</td>", sup, re.S)
    _need(m, "Independence: no supervisor cell")
    o = _section(sup, r"Supervisor's Office", r"<br\s*/?>\s*<br\s*/?>", "Independence supervisor")
    # 'Phone : 248-625-5111; Ext. 213' -- the semicolon hides the extension.
    ph = phones_in(re.sub(r";\s*(Ext\.)", r" \1", o))
    out.append(member(_name(m.group(1)), "Supervisor",
                      phone_=ph[0] if len(ph) == 1 else None, email=_email(o)))

    m = re.search(r'<a href="mailto:([^"]+)"[^>]*>\s*((?:(?!</a>).)*?),\s*<br\s*/?>\s*'
                  r"Township Clerk\b", clk, re.S)
    _need(m, "Independence: no clerk entry in the clerk's directory")
    _need(re.search(r"<strong>\s*%s,\s*Clerk\s*</strong>" % re.escape(txt(m.group(2))), clk),
          "Independence: the clerk's heading and directory name different people")
    out.append(member(_name(m.group(2)), "Clerk", email=_email('href="mailto:%s"' % m.group(1))))

    m = re.search(r"<td[^>]*>\s*((?:(?!</td>|<br).)*?),\s*Treasurer\s*<br\s*/?>((?:(?!</td>).)*)</td>",
                  trs, re.S)
    _need(m, "Independence: no treasurer cell")
    name = re.sub(r"\s+CPA$", "", _name(m.group(1)))
    ph = phones_in(m.group(2))
    out.append(member(name, "Treasurer", phone_=ph[0] if len(ph) == 1 else None,
                      email=_email(m.group(2))))

    office = {}
    b = re.search(r"send an email to (board@indtwp\.com)", txt(h))
    if b:
        office["email"] = b.group(1)
    return _finish(out, office)


def _whitelake_rows(h):
    """Drupal directory-listing rows: (name, position, phone)."""
    out = []
    for r in re.split(r'<div class="views-row\b', h)[1:]:
        n = re.search(r'views-field-title[^>]*>.*?<a [^>]*>(.*?)</a>', r, re.S)
        p = re.search(r'views-field-field-position">\s*<div class="field-content">(.*?)</div>', r, re.S)
        if not n or not p:
            continue
        t = re.search(r'views-field-field-phone-number">\s*<div class="field-content">(.*?)</div>', r, re.S)
        # The site writes an extension as 'X-140'; phone() reads 'x140'.
        raw = re.sub(r"\bX-\s*(\d+)", r"x\1", txt(t.group(1)), flags=re.I) if t else ""
        out.append((_name(n.group(1)), txt(p.group(1)), phone(raw) if raw else None))
    return out


def parse_white_lake(h, also):
    """'Meet Our Board of Trustees' lists the four trustees as Drupal
    directory rows (name, position, phone); the supervisor, clerk and
    treasurer are each the one directory row on their own office page
    (`also`, in that order). Trap: extensions print as 'X-140'. E-mail is a
    contact form, never an address, so none is taken."""
    _need(len(also) == 3, "White Lake: %d officer pages, expected 3" % len(also))
    seg = _section(h, r"Meet Our Board of Trustees", r"Agendas/Minutes", "White Lake")
    rows = _whitelake_rows(seg)
    _need(len(rows) == 4 and all(p == "Trustee" for _, p, _ in rows),
          "White Lake: board rows %r" % [(n, p) for n, p, _ in rows])
    out = [member(n, "Trustee", phone_=ph) for n, _, ph in rows]
    for page, office in zip(also, ("Supervisor", "Clerk", "Treasurer")):
        rows = [r for r in _whitelake_rows(page)
                if re.match(r"^(?:Township\s+)?%s$" % office, r[1])]
        _need(len(rows) == 1, "White Lake: %d %s rows on its page" % (len(rows), office))
        n, _, ph = rows[0]
        out.append(member(n, office, phone_=ph))
    office = {}
    m = re.search(r"Contact Information.*?Phone:\s*([()\d\s.\-]{10,16})", seg, re.S)
    if m and phone(m.group(1)):
        office["phone"] = phone(m.group(1))
    return _finish(out, office)


def _gaines_cards(h):
    """Revize staff-directory cards: (position, name, card html)."""
    out = []
    for c in re.split(r'<div class="rz-element rz-staff-directory-card-wrap"', h)[1:]:
        p = re.search(r'staff-position[^>]*>\s*<p[^>]*>(.*?)</p>', c, re.S)
        n = re.search(r'staff-name[^>]*>\s*<p[^>]*>(.*?)</p>', c, re.S)
        if p and n:
            # The last card on a page runs on into the page's own contact
            # block, so a card ends where its social-links div starts.
            out.append((txt(p.group(1)), txt(n.group(1)), c.split('class="staff-social"')[0]))
    return out


def parse_gaines(h, also):
    """Trustees page: four Revize staff cards with the position 'Trustee'.
    The supervisor, clerk and treasurer are the cards titled 'Supervisor',
    'Township Clerk' and 'Township Treasurer' in the staff directory (`also`);
    deputies and assistants have other titles and are not read. Each
    officer's extension is the card's 'Ext. N' line on the main number.
    Trap: one trustee's card gives the township's general mailbox
    (info@gainestownship.org), which is the office's, not his."""
    _need(len(also) == 1, "Gaines: %d directory pages, expected 1" % len(also))
    office = {}
    out = []

    def add(name, role, card):
        e = _email(card)
        if e and e.startswith("info@"):
            office["email"] = e
            e = None
        ph = phones_in(card)
        _need(len(ph) <= 1, "Gaines: %d phones on %s's card" % (len(ph), name))
        ph = ph[0] if ph else None
        x = re.search(r'staff-bio">\s*<p[^>]*>\s*Ext\.\s*(\d{1,6})\b', card, re.S)
        if ph and x and " ext. " not in ph:
            ph += " ext. " + x.group(1)
        out.append(member(_name(name), role, phone_=ph, email=e))

    tr = [c for c in _gaines_cards(h) if c[0] == "Trustee"]
    _need(len(tr) == 4, "Gaines: %d trustee cards, expected 4" % len(tr))
    for _, n, c in tr:
        add(n, "Trustee", c)
    cards = _gaines_cards(also[0])
    for title, role in (("Supervisor", "Supervisor"), ("Township Clerk", "Clerk"),
                        ("Township Treasurer", "Treasurer")):
        hit = [c for c in cards if c[0] == title]
        _need(len(hit) == 1, "Gaines: %d directory cards titled %r" % (len(hit), title))
        add(hit[0][1], role, hit[0][2])
    m = re.search(r"Please feel free to contact the Trustees.*?<strong>([\d\-() .]{10,16})</strong>", h, re.S)
    if m and phone(m.group(1)):
        office["phone"] = phone(m.group(1))
    return _finish(out, office)


def _u(geoid, name, body, url, parse, seats=7, also=None):
    u = {"geoid": geoid, "name": name, "kind": "township", "body": body,
         "url": url, "seats": seats, "parse": parse}
    if also:
        u["also"] = also
    return u


UNITS = [
    _u("2609916520", "Clinton", "Board of Trustees",
       "https://www.clintontownship.com/318/Board-of-Trustees", parse_clinton),
    _u("2616313120", "Canton", "Board of Trustees",
       "https://www.cantonmi.gov/206", parse_canton),
    _u("2609950480", "Macomb", "Board of Trustees",
       "https://www.macomb-mi.gov/148/Board-of-Trustees", parse_macomb),
    _u("2612584240", "Waterford", "Board of Trustees",
       "https://waterfordmi.gov/168/Board-of-Trustees", parse_waterford),
    _u("2613931880", "Georgetown", "Township Board",
       "https://www.gtwp.com/179/Township-Board", parse_georgetown),
    _u("2616367625", "Redford", "Board of Trustees",
       "https://www.redfordtwp.gov/160/Board-of-Trustees", parse_redford),
    _u("2609915340", "Chesterfield", "Board of Trustees",
       "https://www.chesterfieldtwp.org/242/Elected-Officials", parse_chesterfield),
    _u("2612509110", "Bloomfield", "Board of Trustees",
       "https://www.bloomfieldtwp.org/government/board-of-trustees/", parse_bloomfield),
    _u("2606553140", "Meridian", "Township Board",
       "https://www.meridian.mi.us/your-government/boards-commissions/township-board/", parse_meridian),
    _u("2612517640", "Commerce", "Board of Trustees",
       "https://www.commercetwp.com/government/board-of-trustees/", parse_commerce),
    _u("2614570540", "Saginaw", "Board of Trustees",
       "https://www.saginawtownship.org/departments/board_of_trustees.php", parse_saginaw),
    _u("2604933300", "Grand Blanc", "Township Board",
       "https://www.grandblanctwpmi.gov/306/Township-Board", parse_grand_blanc),
    _u("2616164560", "Pittsfield", "Board of Trustees",
       "https://www.pittsfield-mi.gov/118/Board-of-Trustees", parse_pittsfield),
    _u("2613938660", "Holland", "Township Board",
       "https://hct.holland.mi.us/elected-a-appointed/", parse_holland),
    _u("2612561100", "Orion", "Board of Trustees",
       "https://www.oriontownship.org/government/board_of_trustees/index.php", parse_orion),
    _u("2608164660", "Plainfield", "Board of Trustees",
       "https://www.plainfieldmi.org/186/Board-of-Trustees", parse_plainfield),
    _u("2616311220", "Brownstown", "Board of Trustees",
       "http://brownstown-mi.org/government/township_departments/board_of_trustees/index.php",
       parse_brownstown),
    _u("2604521520", "Delta", "Board of Trustees",
       "https://www.deltami.gov/government/township_board/index.php", parse_delta),
    _u("2604929020", "Flint", "Board of Trustees",
       "https://www.flinttownship.org/government/board_of_trustees/index.php", parse_flint),
    _u("2616381660", "Van Buren", "Board of Trustees",
       "https://vbtmi.gov/government/elected_officials.php", parse_van_buren),
    _u("2609984120", "Washington", "Board of Trustees",
       "https://www.washingtontownship.org/doing_business/trustees.php", parse_washington),
    _u("2616365080", "Plymouth", "Board of Trustees",
       "https://www.plymouthtownshipmi.gov/government/board_of_trustees/index.php", parse_plymouth),
    _u("2606521420", "Delhi", "Board of Trustees",
       "https://www.delhitownshipmi.gov/233/Board-of-Trustees", parse_delhi),
    _u("2608112240", "Byron", "Township Board",
       "https://www.byrontownship.org/government/township_board/index.php", parse_byron),
    _u("2613901360", "Allendale", "Board of Trustees",
       "https://allendalemi.gov/board-of-trustees/", parse_allendale),
    # The page names the people and not the body; MCL 42.5 calls it the
    # township board.
    _u("2607508760", "Blackman", "Township Board",
       "https://blackmantwp.com/elected-officials/", parse_blackman),
    _u("2612540400", "Independence", "Board of Trustees",
       "https://www.indtwp.com/government/board_of_trustees/index.php", parse_independence,
       also=["https://www.indtwp.com/departments/supervisor/index.php",
             "https://www.indtwp.com/departments/clerk/index.php",
             "https://www.indtwp.com/departments/treasurer/index.php"]),
    _u("2612586860", "White Lake", "Township Board",
       "https://www.whitelaketwp.com/bc-tb", parse_white_lake,
       also=["https://www.whitelaketwp.com/supervisor",
             "https://www.whitelaketwp.com/clerk",
             "https://www.whitelaketwp.com/treasurer"]),
    _u("2608131240", "Gaines", "Township Board",
       "https://www.gainestownship.org/trustees.php", parse_gaines,
       also=["https://www.gainestownship.org/how_do_i/staff_directory.php"]),
]
