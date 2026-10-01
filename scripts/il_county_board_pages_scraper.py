#!/usr/bin/env python3
"""Scrape eight Illinois counties' own board-member pages.

WHY EIGHT COUNTIES IN ONE SCRAPER AND NOT EIGHT SCRAPERS. These are not eight
unrelated sources; they are one finding. On 2026-10-01 Illinois named a
governing body in 83 of its 102 counties, and the standing explanation for the
nineteen that named nobody was an ask ledger: each had been written to about its
board-district GEOMETRY and had not replied, so each record said so and the
county stayed empty. Probing all nineteen counties' own websites that day — one
request each, through `scraper_common.require_robots_once` — found that EIGHT of
them publish their board members, with districts, and have done all along. The
ask was for a map file; the question the fourth test of `docs/DONE_STANDARD.md`
asks is WHO SITS ON THE BOARD; and nobody had gone back to the website to look.

So the defect was never a missing source. It was a RECORD STANDING IN FOR A
SOURCE NOBODY RE-CHECKED, and a letter asking a county who sits on its board
would have gone to counties that publish exactly that. A county's ask ledger
answers whether somebody wrote to it. It never answers whether the county
publishes the thing.

ALL EIGHT SHIP HERE, in two tranches on the same day. Six went first; Fayette
and Jersey followed within the hour, and what turned them up was not a wider
sweep but READING THE LETTERS. Two drafts in `docs/ASK_DRAFTS.md` already told
those clerks their members were named on this site, and neither county was among
the 89 — so each letter was about to assert something untrue about the product.
Both counties' board pages carry every member with a district, so the fix was to
make the claim true. Check a letter's claims about what the site already has
against the SITE, not against the record.

SCOTT AND MACOUPIN ARE WHAT IS LEFT, and neither is parsed: Scott renders its
commissioners through a widget that returns nothing to this client, and
Macoupin's board page is county information — a district map link, the rules, the
budget — with its members somewhere else. Both are recorded as work still to do
rather than quietly dropped.

WHAT EACH COUNTY PUBLISHES, measured 2026-10-01 at the exact url this scraper
fetches:

  bond        tablepress, 3 columns — district, name, county e-mail. 5 members.
  bureau      an lsvr person-list widget — "Name (Party)" linked, "District N"
              as the subtitle. 18 members in 18 single-member districts.
  cumberland  tablepress, 2 columns — a block of name/party/role/address/phone/
              e-mail, and the district. 6 members over three compass districts.
  fayette     a Beaver Builder post grid, one `fl-post-column` per member —
              district heading, name linked to the member's own directory page,
              then party and term. 14 members in 7 districts, two apiece.
  jasper      cards grouped under a `District N` heading, each naming the member
              and their lettered seat (1A..3C). 9 members.
  jersey      one Avada text block per member — the name in an `h2`, the district
              in the `h3` under it, inside the same block. 12 members in 4.
  lawrence    a plain list — "District N - Name - <i>Role</i>". 7 members.
  piatt       Revize staff-directory cards, the district in `data-category`.
              6 members in 3 districts, two apiece.

FOUR THINGS NOTHING SHIPS, each measured rather than assumed.

A HOME ADDRESS NEVER SHIPS. Cumberland's table prints every member's home
street address. That is the Wabash rule — a clerk's e-mail listing home
addresses did not put them on a card — and it applies to a page as much as to a
letter.

A VALUE REPEATED ON EVERY MEMBER NAMES NOBODY, so neither Fayette nor Jersey
ships a contact field. Fayette's board page carries EMPTY `tel:` links and sends
each "Email <first name>" link to the member's own directory page rather than to
an address; fetching one of those pages on 2026-10-01 found no `mailto:` at all
and only the county switchboard, 618-283-5000, printed twice. Jersey prints
"Email: contact board office at 618-498-5571 x101" under all twelve members. That
is the Cook County rule, where fourteen of seventeen commissioners listed the same
County Building suite as their office.

A PERSON'S NAME IS NEVER CORRECTED TO MAKE A JOIN. Bond's table names
"Chris Timmerman" beside `chris.timmermann@bondcountyil.gov`, one `n` against
two, and Jasper's members page spells "Erik Spiker" where its own photograph
file is named `Eric_Spiker2025`. Both spellings ship as the page prints them,
and the mismatch is printed on every run rather than smoothed.

AN E-MAIL COMES FROM THE LINK TEXT, NOT THE `mailto:`. Cumberland's Vice-Chair
is linked `mailto:official_jtoddlayton@yaho..com` — a typo in the href — while
the visible text reads `official_jtoddlayton@yahoo.com`. The text is what the
county means and what a reader would copy, so the text wins, and a run where
the two disagree says so.

    python3 scripts/il_county_board_pages_scraper.py --out /tmp/boards.json
    python3 scripts/il_county_board_pages_scraper.py --out /tmp/boards.json \
        --county bond
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scraper_common as SC  # noqa: E402

UA = SC.UA_ROSTER_BOT

# Each county's page, the floor its parse must clear, and how many distinct
# districts the county itself says it has. BOTH are floors on purpose: a count
# alone cannot see a parser that reads one district six times, which is the
# failure mode a grouped page has.
SOURCES = {
    "bond": dict(
        url="https://bondcountyil.gov/bond-county-board/",
        members=5, districts=5),
    # BUREAU'S OWN PAGE IS ONE SEAT SHORT AND THAT SHIPS AS A SEAT, NOT AS A
    # SMALLER BOARD. The page states "The County is divided into 18
    # single-member districts" and then lists seventeen members: District 15
    # appears nowhere on it, measured 2026-10-01 (zero occurrences of the
    # string). So the floors are seventeen and the parse emits an eighteenth
    # district carrying a note instead of a name — the Alexander rule, where
    # shipping a board's published names without its unfilled seat conceals the
    # seat rather than inventing one. The moment the county lists District 15
    # the parse clears a higher floor and `--check` is where that is noticed.
    "bureau": dict(
        url="https://bureaucounty-il.gov/county-board/",
        members=17, districts=17),
    "cumberland": dict(
        url="https://cumberlandcoil.gov/county-board-members-committees/",
        members=6, districts=3),
    # FAYETTE AND JERSEY WERE FOUND IN THE SECOND PASS OVER THE SAME NINETEEN,
    # and what turned them up is that two letters drafted to them already SAID
    # their members were on this site. They were not: both counties sat in the
    # thirteen naming nobody, so each letter was about to tell a clerk we had
    # something we did not have. Reading each county's own board page the same
    # afternoon showed both publish every member with a district, so the honest
    # fix was to make the letters' claim true rather than to soften it.
    "fayette": dict(
        url="https://www.fayettecountyillinois.gov/county-offices/county-board/",
        members=14, districts=7),
    "jasper": dict(
        url="https://jaspercountyillinois.gov/county-board/board-members/",
        members=9, districts=9),
    "jersey": dict(
        url="https://jerseycounty-il.gov/county-board/",
        members=12, districts=4),
    "lawrence": dict(
        url="https://lawrencecounty.illinois.gov/boards/county-board",
        members=7, districts=7),
    "piatt": dict(
        url="https://piatt.gov/government/county_board/index.php",
        members=6, districts=3),
}

ROLES = ("Chairman", "Chairperson", "Chair", "Vice-Chairman", "Vice Chairman",
         "Vice-Chair", "Vice Chair")

PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent"}


def note(msg):
    print("il-county-board-pages: %s" % msg, file=sys.stderr)


def fail(msg):
    note("FAIL — %s" % msg)
    raise SystemExit(1)


def fetch(url):
    SC.require_robots_once(url, UA)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read(2_000_000).decode("utf-8", "replace")


def strip_tags(fragment):
    fragment = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return html.unescape(fragment)


def one_line(text):
    return re.sub(r"\s+", " ", text).strip()


def cells(row_html):
    return [m.group(1) for m in re.finditer(r"(?is)<td[^>]*>(.*?)</td>", row_html)]


def rows(table_html):
    return [m.group(1) for m in re.finditer(r"(?is)<tr[^>]*>(.*?)</tr>", table_html)]


def table_after(body, heading):
    """The first <table> that follows `heading`.

    Anchored on the heading rather than on a table id: a tablepress id is the
    CMS's row number and moves when an editor adds a table above this one,
    which is a silent swap to another body's roster.
    """
    at = body.find(heading)
    if at < 0:
        fail("the page no longer carries the heading %r" % heading)
    m = re.search(r"(?is)<table[^>]*>(.*?)</table>", body[at:])
    if not m:
        fail("no table follows %r" % heading)
    return m.group(1)


def email_from(fragment):
    """The address as the page PRINTS it, with the `mailto:` as a cross-check.

    Cumberland's Vice-Chair is linked to a mistyped host while the visible text
    is right, so the text is what ships and the disagreement is printed.
    """
    link = re.search(r'(?is)<a[^>]+href="mailto:([^"?]+)"[^>]*>(.*?)</a>', fragment)
    if link:
        href = html.unescape(link.group(1)).strip()
        shown = one_line(strip_tags(link.group(2)))
        if shown and "@" in shown:
            if shown.lower() != href.lower():
                note("e-mail link and text disagree: href %r, text %r — "
                     "shipping the text" % (href, shown))
            return shown
        return href
    bare = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", strip_tags(fragment))
    return bare.group(0) if bare else None


def split_role(name):
    """('Jane Doe', 'Chairman') from 'Jane Doe Chairman'. Longest role first,
    so 'Vice-Chairman' is never read as 'Chairman' with 'Vice-' left on the
    name."""
    for role in sorted(ROLES, key=len, reverse=True):
        m = re.search(r"\b%s\b" % re.escape(role), name, re.I)
        if m:
            return one_line(name[:m.start()] + " " + name[m.end():]), role
    return one_line(name), None


def split_party(name):
    m = re.search(r"\(([RDI])\)", name)
    if not m:
        return one_line(name), None
    return (one_line(name[:m.start()] + " " + name[m.end():]),
            PARTY[m.group(1)])


def person_case(name):
    """Display casing for a name a county publishes in CAPITALS.

    Cumberland's table prints every member in capitals ("FLOYD HOLKENBRINK"),
    which no other county in this fleet does and which is the page's styling
    rather than the person's name. Lower-casing it is still a change to
    somebody's name, so this REFUSES the casings it cannot decide rather than
    guessing: `MCDONALD` is McDonald and `MACKEY` is Mackey, `O'FALLON` is
    O'Fallon and `OBRIEN` is Obrien — no rule gets both pairs right, and a
    wrongly-cased name on a card is a person's name printed wrong. The day one
    is elected, the build stops and a person writes the label, which is what
    `vtd_board_districts.title_case` already says about apostrophes and what
    Hardin's McFarlan precinct was given an explicit label for.

    A name the county prints in mixed case is left exactly as published.
    """
    letters = re.sub(r"[^A-Za-z]", "", name)
    if not letters or not letters.isupper():
        return one_line(name)
    for word in re.split(r"[\s-]+", name):
        bare = re.sub(r"[^A-Za-z']", "", word)
        if len(bare) > 2 and (bare.upper().startswith(("MC", "MAC"))
                              or "'" in bare):
            fail("%r is published in capitals and this cannot decide its casing "
                 "(a Mc/Mac prefix or an apostrophe). Give it an explicit label "
                 "rather than letting the build guess at somebody's name."
                 % name)
    out = []
    for word in re.split(r"(\s+|-)", name):
        out.append(word if word.strip() in ("", "-")
                   else word[:1].upper() + word[1:].lower())
    return one_line("".join(out))


def check_email_name(name, email):
    """Print a name that its own e-mail address does not contain.

    Bond prints "Chris Timmerman" beside `chris.timmermann@` — the county's own
    inconsistency, not ours to resolve. Nothing is corrected; the run says so.
    """
    if not email:
        return
    local = email.split("@", 1)[0].lower()
    surname = re.sub(r"[^a-z]", "", name.split()[-1].lower()) if name.split() else ""
    if surname and surname not in re.sub(r"[^a-z]", "", local):
        note("%r does not appear in its own address %s — shipping both as the "
             "county prints them" % (name, email))


# ---------------------------------------------------------------- per county

def parse_bond(body, url):
    out = {}
    for row in rows(table_after(body, "County Board Members")):
        col = cells(row)
        if len(col) < 2:
            continue
        label = one_line(strip_tags(col[0]))
        m = re.search(r"District\s+(\d+)", label, re.I)
        if not m:
            continue
        name = one_line(strip_tags(col[1]))
        email = email_from(col[2]) if len(col) > 2 else None
        if not name:
            continue
        check_email_name(name, email)
        rec = {"name": name}
        if email:
            rec["email"] = email
        out[m.group(1)] = {"members": [rec], "sourceUrl": url}
    return out


def parse_bureau(body, url):
    at = body.find("Current Board Members")
    if at < 0:
        fail("Bureau's page no longer carries 'Current Board Members'")
    out = {}
    block = body[at:]
    for item in re.finditer(
            r"(?is)<li class=\"lsvr_person-list-widget__item\">(.*?)</li>", block):
        chunk = item.group(1)
        title = re.search(r"(?is)item-title-link\"[^>]*>(.*?)</a>", chunk)
        sub = re.search(r"(?is)item-subtitle\">(.*?)</p>", chunk)
        if not (title and sub):
            continue
        raw = one_line(strip_tags(sub.group(1)))
        m = re.match(r"District\s+(\d+)", raw, re.I)
        if not m:
            continue
        name, party = split_party(one_line(strip_tags(title.group(1))))
        name, role = split_role(name)
        # "District 4, Current Board Chair" — the chairmanship rides the
        # subtitle here rather than the name.
        if re.search(r"chair", raw, re.I):
            role = role or "Chair"
        rec = {"name": name}
        if party:
            rec["party"] = party
        if role:
            rec["role"] = role
        out.setdefault(m.group(1), {"members": [], "sourceUrl": url})
        out[m.group(1)]["members"].append(rec)
    # The county states eighteen single-member districts. Any one of them the
    # page does not list is carried as a seat with a reason rather than left out,
    # so a reader is told the seat exists and that the county does not say who
    # holds it.
    for number in range(1, 19):
        if str(number) not in out:
            out[str(number)] = {
                "members": [],
                "note": "The county's board page does not list this seat.",
                "sourceUrl": url,
            }
    return out


def parse_cumberland(body, url):
    out = {}
    for row in rows(table_after(body, "County Board Members")):
        col = cells(row)
        if len(col) < 2:
            continue
        district = one_line(strip_tags(col[1]))
        if not re.search(r"(Western|Central|Eastern)", district, re.I):
            continue
        district = district.split()[0].title()
        lines = [one_line(l) for l in strip_tags(col[0]).split("\n")]
        lines = [l for l in lines if l]
        if not lines:
            continue
        # LINE ONE IS THE PERSON AND EVERY OTHER LINE IS DROPPED. Lines two and
        # three are a home street address, which never ships.
        name, party = split_party(lines[0])
        name, role = split_role(name)
        phone = None
        for l in lines[1:]:
            m = re.search(r"\(?\d{3}\)?[\s.-]\d{3}-\d{4}", l)
            if m and not phone:
                phone = one_line(m.group(0))
        email = email_from(col[0])
        name = person_case(name)
        check_email_name(name, email)
        rec = {"name": name}
        for key, value in (("party", party), ("role", role),
                           ("phone", phone), ("email", email)):
            if value:
                rec[key] = value
        out.setdefault(district, {"members": [], "sourceUrl": url})
        out[district]["members"].append(rec)
    return out


def parse_jasper(body, url):
    """Jasper's seats are LETTERED and its headings are NUMBERED.

    The page groups three cards under `<h3>District 1</h3>` and each card names
    its own seat, "County Board, District 1A". The letter is the seat and the
    heading is only the group, so the heading is read as a CHECK on the letter
    rather than as the key — a card whose letter does not sit under its own
    heading means the page has been restructured and the build stops.
    """
    out = {}
    # SPLIT ON THE HEADINGS RATHER THAN MATCHING A BOUNDED GROUP. A regex whose
    # group ends at the next `<h3>` or the document's end silently dropped the
    # LAST district, because the end-of-document alternative never matched the
    # markup that follows it: six of nine members on the first run.
    marks = [(m.group(1), m.end()) for m in
             re.finditer(r"(?is)<h3>\s*District\s+(\d+)\s*</h3>", body)]
    for i, (number, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(body)
        chunk = body[start:end]
        for card in re.finditer(r"(?is)<div class=\"ward-details\">(.*?)</div>", chunk):
            inner = card.group(1)
            name = re.search(r"(?is)<h4>(.*?)</h4>", inner)
            seat = re.search(r"(?is)District\s+(\d+[A-Z])", strip_tags(inner))
            if not (name and seat):
                continue
            label = seat.group(1).upper()
            if not label.startswith(number):
                fail("Jasper: seat %s sits under the District %s heading — the "
                     "page has been restructured" % (label, number))
            out[label] = {"members": [{"name": one_line(strip_tags(name.group(1)))}],
                          "sourceUrl": url}
    return out


def parse_lawrence(body, url):
    at = body.find("Members</h2>")
    if at < 0:
        at = body.find(">Members<")
    if at < 0:
        fail("Lawrence's page no longer carries a Members heading")
    m = re.search(r"(?is)<ul>(.*?)</ul>", body[at:])
    if not m:
        fail("no list follows Lawrence's Members heading")
    out = {}
    for item in re.finditer(r"(?is)<li>(.*?)</li>", m.group(1)):
        text = one_line(strip_tags(item.group(1)))
        d = re.match(r"District\s+(\d+)\s*-\s*(.+)", text, re.I)
        if not d:
            continue
        rest = d.group(2)
        name, role = (rest.split("-", 1) + [None])[:2]
        rec = {"name": one_line(name)}
        if role:
            rec["role"] = one_line(role)
        out[d.group(1)] = {"members": [rec], "sourceUrl": url}
    return out


def parse_piatt(body, url):
    """Revize staff cards. The district is in `data-category`, and a card with
    none is not a board member — the County Clerk's card sits in this list."""
    out = {}
    for card in re.finditer(
            r"(?is)<div class=\"rz-element rz-staff-directory-card-wrap\"([^>]*)>(.*?)"
            r"<!-- /\.rz-staff-directory-card-wrap -->", body):
        attrs, chunk = card.group(1), card.group(2)
        cat = re.search(r'data-category="([^"]*)"', attrs)
        if not cat:
            continue
        m = re.search(r"District\s+(\d+)\s+Board Member", cat.group(1), re.I)
        if not m:
            continue
        name = re.search(r'(?is)class="staff-name">\s*<p[^>]*>(.*?)</p>', chunk)
        pos = re.search(r'(?is)class="staff-position d-flex">\s*<p[^>]*>(.*?)</p>', chunk)
        if not name:
            continue
        rec = {"name": one_line(strip_tags(name.group(1)))}
        if pos:
            role = one_line(strip_tags(pos.group(1)))
            if role and re.search(r"chair", role, re.I):
                rec["role"] = role
        email = email_from(chunk)
        if email:
            rec["email"] = email
            check_email_name(rec["name"], email)
        out.setdefault(m.group(1), {"members": [], "sourceUrl": url})
        out[m.group(1)]["members"].append(rec)
    return out


def parse_fayette(body, url):
    """A Beaver Builder post grid: a district heading, then the member's name as
    a link to their own directory page, then party and term on one line.

    NEITHER A PHONE NOR AN E-MAIL SHIPS, and both were measured rather than
    assumed. The board page's own `tel:` links are EMPTY (`href="tel:"`), and
    each member's "Email <first name>" link goes to their directory page rather
    than to an address — so a reader of this page alone has no contact detail
    for any member, and the page is what this parse reads. Fetching all fourteen
    directory pages was tried on 2026-10-01 for one member and buys nothing: the
    page carries no `mailto:` at all and its only telephone number is the county
    switchboard, 618-283-5000, printed twice. That is the Cook County rule — a
    number repeated on every member's page says nothing about any member — so
    the member's own page ships as `profileUrl` and no contact field does.

    THE DISTRICT HEADING CARRIES THE ROLE: "District #1, Chairperson". So the
    role is read off the heading and not off a separate field, and a heading
    with no comma is an ordinary member.
    """
    # SPLIT INTO THE PAGE'S OWN GRID ITEMS FIRST. A single regex spanning from a
    # district heading to the next title matches ACROSS an item when one is
    # shaped differently, which is the Jasper bounded-group defect in another
    # costume; the page carries one `fl-post-column` per member, so the split is
    # the page's own and the count is checkable.
    chunks = re.split(r'(?i)<div class="fl-post-column"', body)[1:]
    out = {}
    for chunk in chunks:
        m = re.search(
            r"(?is)District\s*#(\d+)([^<]*)</strong>.*?"
            r"<div class=\"fl-post-title\"><a href=\"([^\"]+)\">(.*?)</a></div>"
            r"\s*<div>(.*?)</div>", chunk)
        if not m:
            continue
        number, tail, href, name, meta = m.groups()
        name = one_line(strip_tags(name))
        # THE PAGE PREFIXES EVERY NAME WITH "Honorable", WHICH IS A COURTESY AND
        # NOT PART OF ANYBODY'S NAME. It is stripped rather than shipped, and
        # stripped only as a leading word, so a surname that happens to contain
        # it survives.
        name = re.sub(r"^Honorable\s+", "", name).strip()
        if not name:
            continue
        rec = {"name": person_case(name), "profileUrl": one_line(href)}
        # A SLUG CAN NAME SOMEBODY ELSE AND THE PAGE IS STILL THE RIGHT PERSON'S,
        # which reads exactly like a parse bug and is not one. Measured
        # 2026-10-01: District 3's Sean Hannagan is linked at
        # `/directory-listing/honorable-casey-cameron/`, the slug of a previous
        # holder of the seat, and that page's own title is "Honorable Sean
        # Hannagan". So the url ships, because it serves this member's page, and
        # the mismatch is PRINTED rather than silently corrected — a slug is the
        # county's own identifier and this never edits one.
        slug = one_line(href).rstrip("/").rsplit("/", 1)[-1]
        if name.split()[-1].lower() not in slug.replace("-", " ").lower():
            note("%s: district %s links %s at a slug naming somebody else (%s) "
                 "— shipping it, the page's own title names this member"
                 % ("fayette", number, rec["name"], slug))
        role = one_line(tail.lstrip(", ").strip())
        if role and re.search(r"chair", role, re.I):
            rec["role"] = role
        meta = one_line(strip_tags(meta))
        party, _sep, term = meta.partition(",")
        party = one_line(party)
        if party:
            # "Democrat" is how this county writes it and "Democratic" is the
            # party's own name, which is what every other Illinois roster in
            # this fleet carries; the normalisation is a NOTATION map and
            # decides nothing about a person.
            rec["party"] = "Democratic" if party.lower() == "democrat" else party
        term = one_line(term)
        if term:
            rec["term"] = term
        out.setdefault(number, {"members": [], "sourceUrl": url})
        out[number]["members"].append(rec)
    return out


def parse_jersey(body, url):
    """One Avada text block per member: the name in an `h2`, the district in the
    `h3` directly below it, inside the same block.

    THE BLOCK IS THE UNIT, NOT THE DOCUMENT. A first draft paired each district
    heading with the nearest `h2` above it anywhere in the page, and the
    chairman's heading sits far enough from his name that the rule reached a
    navigation heading instead and produced a "member" named after a list of
    villages. Its own guard — distinct names must equal headings read — PASSED,
    because twelve headings still gave twelve distinct strings and one of them
    was rubbish. A count guard cannot see a wrong answer of the right size, so
    the parse is bounded by the page's own `fusion-text` block.

    NO CONTACT DETAIL SHIPS. Every one of the twelve members reads "Email:
    contact board office at 618-498-5571 x101" — one number for the whole board,
    which is the Cook County rule: a value repeated on every member says nothing
    about any member.

    THE ROLE SITS AHEAD OF THE DISTRICT in the same heading, as "County Board
    Chairman - Jersey County Board District 3", so it is read from the text
    before the district rather than from a field of its own.
    """
    out = {}
    seen = 0
    for block in re.finditer(
            r'(?is)<div class="fusion-text fusion-text-\d+">(.*?)</div>', body):
        chunk = block.group(1)
        name = re.search(r"(?is)<h2[^>]*>(.*?)</h2>", chunk)
        head = re.search(
            r"(?is)<h3[^>]*>(.*?)Jersey County Board District\s*(\d+)\s*</h3>",
            chunk)
        if not (name and head):
            continue
        person = one_line(strip_tags(name.group(1)))
        if not person:
            continue
        seen += 1
        rec = {"name": person_case(person)}
        role = one_line(strip_tags(head.group(1))).rstrip(" -\u2013\u2014").strip()
        if role and re.search(r"chair", role, re.I):
            rec["role"] = role
        out.setdefault(head.group(2), {"members": [], "sourceUrl": url})
        out[head.group(2)]["members"].append(rec)
    names = {r["name"] for d in out.values() for r in d["members"]}
    if len(names) != seen:
        fail("Jersey: %d member block(s) resolved to %d distinct name(s) — two "
             "members are being read as one" % (seen, len(names)))
    # THE PAGE STATES ITS OWN CHAIR AND VICE CHAIR A SECOND TIME, in a sidebar
    # block reading "BOARD CHAIRMAN: <name>" and "VICE CHAIR: <name>", and the
    # two statements must agree — the Clay precedent, where a county's two
    # surfaces named the Vice Chairman differently. This is the one independent
    # witness the page carries, so it is a gate rather than a comment.
    for label, want in (("BOARD CHAIRMAN", "chairman"), ("VICE CHAIR", "vice")):
        # EACH WORD OF THE NAME MUST CARRY A LOWERCASE LETTER, which is what
        # stops the match running on into the ALL-CAPS label that follows it:
        # a first draft read "Mark Wagner VICE CHAIR" as the chairman's name and
        # failed against the member blocks, reporting a disagreement that did not
        # exist. A cross-check that fails for its own reasons is worse than none.
        word = r"[A-Z][A-Za-z.'\u2019-]*[a-z][A-Za-z.'\u2019-]*"
        m = re.search(r"(?:%s)\s*:\s*(%s(?:[ \t]+%s){1,3})"
                      % (label, word, word),
                      re.sub(r"[ \t]*\n[ \t\n]*", " ", strip_tags(body)))
        if not m:
            note("Jersey: the page no longer states its %s separately, so that "
                 "cross-check did not run" % label)
            continue
        stated = one_line(m.group(1))
        held = [r["name"] for d in out.values() for r in d["members"]
                if want in (r.get("role") or "").lower()]
        if not held:
            fail("Jersey: the page states %s %s and no member block carries that "
                 "role" % (label, stated))
        if not any(h.split()[-1] == stated.split()[-1] for h in held):
            fail("Jersey: the page states %s %s and the member blocks give %s"
                 % (label, stated, ", ".join(held)))
    return out


PARSERS = {
    "bond": parse_bond,
    "bureau": parse_bureau,
    "cumberland": parse_cumberland,
    "fayette": parse_fayette,
    "jasper": parse_jasper,
    "jersey": parse_jersey,
    "lawrence": parse_lawrence,
    "piatt": parse_piatt,
}


def scrape(slug):
    spec = SOURCES[slug]
    body = fetch(spec["url"])
    districts = PARSERS[slug](body, spec["url"])
    people = sum(len(d["members"]) for d in districts.values())
    named = sum(1 for d in districts.values()
                for m in d["members"] if (m.get("name") or "").strip())
    if named != people:
        fail("%s: %d of %d records carry no name" % (slug, people - named, people))
    if people < spec["members"]:
        fail("%s: %d member(s) parsed, the county states %d"
             % (slug, people, spec["members"]))
    if len(districts) < spec["districts"]:
        fail("%s: %d district(s) parsed, the county states %d"
             % (slug, len(districts), spec["districts"]))
    note("%-11s %2d member(s) in %2d district(s)" % (slug, people, len(districts)))
    return districts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--county", action="append", choices=sorted(SOURCES),
                    help="scrape only these counties (default: all eight)")
    args = ap.parse_args()
    want = args.county or sorted(SOURCES)
    out = {slug: scrape(slug) for slug in want}
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    note("wrote %s (%d county/counties)" % (args.out, len(out)))


if __name__ == "__main__":
    main()
