#!/usr/bin/env python3
"""Read six large Illinois cities' own council pages into municipal-officials payloads.

WHY SIX CITIES AND NOT SIX COUNTIES. The fourth test of the done standard
(`docs/DONE_STANDARD.md`) asks that every general-purpose local government above
25,000 people name a governing body. Measured 2026-10-01 by
`scripts/build_eam_status.py`, thirteen Illinois units above that line named
nobody. Six of them are a unit above the line in a county whose municipal
directory this project cannot read at all:

    Champaign  (Champaign County — no county municipal source)
    Decatur    (Macon County     — no county municipal source)
    Normal     (McLean County    — the county source names three villages and
                                   omits the town wholesale)
    Quincy     (Adams County     — no county municipal source)
    Danville   (Vermilion County — no county municipal source)
    Urbana     (Champaign County — no county municipal source; added 2026-10-21)

That is the GALESBURG SHAPE and the FREEPORT SHAPE, the two bounded exceptions
`docs/EXPANSION_GUIDE.md` §3.4 already allows to the rule against scraping
municipal sites: a county with no municipal source at all, and a municipality a
county directory omits wholesale. Nothing here is a sweep — the six places are
named in `PRESERVABLE`, and a seventh city cannot be added by this file alone.

THE OTHER SEVEN ARE NOT HERE, AND URBANA WAS THE EIGHTH. Seven are in Lake
County, which IS in the pipeline but at the contact-only rung: the county's open
data portal publishes a hall address for all 41 of its municipalities and names
nobody, and the Lake County Municipal League's member pages were measured on
2026-10-01 and republish exactly the same address and telephone. Seven city
sites is past any bounded exception, so Lake wants its own decision rather than
a quiet seventh entry here. (Those seven are now read by
`scripts/il_lake_cities_councils_scraper.py`, a separate step of the weekly
job, each named in `PRESERVABLE`.) Urbana's host
`urbanaillinois.us` reset the connection on every attempt from this project's
sandbox on 2026-10-01 (stdlib and `requests`, both clients, www and bare), and
timed out from a GitHub runner the same day. RE-MEASURED 2026-10-21: the city's
website is now `www.urbanail.gov` (its footer names the City of Urbana at 400
South Vine Street, and the council members' own addresses are on that domain),
while the old host still resets every connection from here. So the old host
was a site the city had left rather than a city refusing this client. The
letter drafted on 2026-10-01 to ask whether the block was deliberate was never
sent and is withdrawn: a host that stops answering can be a government that has
moved, which is worth a search before a letter.

FETCH CLASS, MEASURED 2026-10-01 WITH THE CLIENT THIS FILE SENDS. All five
hosts answer `requests` + the districtry token with HTTP 200 and a full page
(champaignil.gov 5,284 bytes of JSON; decaturil.gov 109,440; normalil.gov
123,796; quincyil.gov 116,904; cityofdanville.org 132,624). Urbana's, measured
2026-10-21 the same way: www.urbanail.gov 80,180 bytes for the council page,
73,832 for the mayor's and 74,249 for the clerk's. No browser string is
needed anywhere here and none is sent. For contrast, and because it is the
reason Lake stayed contact-only rather than being read from the county site:
`www.lakecountyil.gov` answers the same token 403 on `requests` and 200 on the
stdlib client — the stack, not the name.

ROBOTS. Each host's policy is read once, by `require_robots_once`, with the
exact client this file crawls with. Measured 2026-10-01: all five serve a
robots.txt and none of them disallows the paths read here. Four of the five
serve the same 801-816 byte CivicPlus/Granicus default, which is one CMS
vendor's file published at each city's own host — it binds for that reason and
is never cited as something the city chose. Urbana's (2026-10-21) is Drupal's
own 2,005-byte default, the same kind of vendor file, and allows the council,
mayor and clerk pages read here. It is read once, at the council page: all
three pages are on one host, which is what `require_robots_once` asks about.

ADDRESSES. Only the city hall is shipped, as the municipality-level office, and
it is a constant per city read off the city's own contact block. Quincy's
alderman pages print a street address per person — 600 Adams St. on one of them,
which is not the City Hall at 730 Maine St. — and nothing on the page says
whether that is an office or a home. The Madison/Peoria rule applies: an
address that cannot be shown to be an office is not shipped, so none of them is.

WHAT EACH PAGE PUBLISHES, AND THE ONE PARSE THAT IS DELIBERATELY SOFT.

  Champaign  WordPress REST. The member pages are children of the page with
             slug `members`, discovered by slug rather than by its id, so a
             re-publish does not strip the council. Each child's title is the
             name and its body reads "<name> <role> <phone> ... <seat>", the
             seat being "District N", "At Large" or "Deputy Mayor, At Large".
             217-403-8720 is the council's shared line and appears on six of
             nine pages, so a per-person phone equal to it is dropped.
  Decatur    One page, "<name>\\n<Councilman|Councilwoman|Mayor>". Decatur
             elects its council at large, so there is no district to draw.
  Normal     One page whose council block is `data-headertext` on each photo
             widget, the mayor's reading "Mayor <name>". Elected at large.
  Quincy     An index linking one page per alderman; each prints
             "Ward N Alderman" with a direct telephone and e-mail. THE MAYOR IS
             A WARNING AND NOT A FLOOR: the mayor's page introduces her inside a
             first-person letter ("I'm Dr. Linda K. Moore, and it is my honor to
             serve as Mayor"), and a regex against a letter is a parser that
             breaks silently the week the letter is rewritten. So the mayor is
             read if an anchored pattern matches and the run prints a warning
             if it does not; the fourteen aldermen are what the floors hold.
             THE E-MAIL IS THE ONE UNDER THE ENTRY'S "Email" LABEL, on any
             domain (Adam's choice of 2026-10-17, "E-mails too"); until that
             day only a quincyil.gov address was read. Each page's footer
             prints the city's general mailbox, the same on all fourteen, and
             that is never the member's. An address printed on two or more
             members' pages, or whose local part carries another member's
             surname and not this member's, ships on nobody, and the run says
             which ward. Measured that day: 14 of 14 aldermen, all on
             quincyil.gov.
  Danville   One page carrying the mayor and all fourteen aldermen, each with a
             ward and a direct telephone.
  Urbana     Three pages, each of whose people is a "directory listing" block:
             the council page (seven members, each "Ward N Council Member"
             with a direct telephone and the member's own e-mail written
             beside the seat in Cloudflare's protected form, which every
             visitor's browser decodes), the mayor's office page and the City
             Clerk's page (the clerk is elected, the council page says). The
             mayor's and the clerk's listings print no telephone and link a
             contact form rather than an address, so they ship by name. A
             party marker after a name ("[D]") is not part of the name and is
             dropped. The hall's telephone is the 217-384-0200 every page's
             footer prints; the council's shared mailbox, which the page
             spells out as "CityCouncil[at]urbanail.gov", is the hall's e-mail.

Usage:
    python3 scripts/il_large_city_councils_scraper.py --out-dir /tmp
    python3 scripts/il_large_city_councils_scraper.py --out-dir /tmp --only champaign
"""

import argparse
import datetime
import html
import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import UA_ROSTER_BOT, person_email_problem, require_robots_once  # noqa: E402

HEADERS = {"User-Agent": UA_ROSTER_BOT}
TIMEOUT = 60
ATTEMPTS = 4

# The council's own shared line, printed on a member page where that member
# publishes no direct number. A per-person value equal to it is the hall line
# wearing a person's name and is dropped (§3.4, "a per-person value equal to
# the hall line is dropped").
SHARED_LINES = {"217-403-8720"}


def now():
    return (datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"))


def get(url):
    """One paced GET with retries, through the client this file declares."""
    last = None
    for attempt in range(ATTEMPTS):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:          # noqa: BLE001 — retried, then raised
            last = exc
            if attempt + 1 < ATTEMPTS:
                import time
                time.sleep(1.5 * (attempt + 1))
    raise last


def visible(markup):
    t = re.sub(r"(?is)<(script|style).*?</\1>", "\n", markup)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return re.sub(r"\n{2,}", "\n", t)


def clean(value):
    if not value:
        return None
    value = " ".join(str(value).split())
    return value or None


def phone(raw, city=None):
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    number = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])
    if number in SHARED_LINES:
        return None
    # The city hall's own switchboard, printed in a person's row. Danville's
    # mayor's row carries exactly this: it is a way to reach the office, which
    # the card already names, and not a way to reach the person.
    if city and number == city["office"].get("office_phone"):
        return None
    return number


def record(city, office, name, district=None, person_phone=None,
           person_email=None, term=None, source_url=None):
    return dict(
        city["office"],
        jurisdiction=city["jurisdiction"],
        office=office,
        district=district,
        name=clean(name),
        person_phone=person_phone,
        person_email=person_email,
        term=term,
        source_url=source_url or city["page"],
        scraped_at=now(),
    )


# ---------------------------------------------------------------- Champaign

def read_champaign(city, warn):
    api = "https://champaignil.gov/wp-json/wp/v2/pages"
    parents = json.loads(get(api + "?slug=members"))
    if len(parents) != 1:
        raise SystemExit("champaign: %d pages have the slug `members`, expected "
                         "1 — the council index has moved" % len(parents))
    children = json.loads(get("%s?parent=%d&per_page=100" % (api, parents[0]["id"])))
    out = []
    for page in children:
        name = html.unescape(page["title"]["rendered"])
        body = html.unescape(re.sub(r"\s+", " ",
                                    re.sub(r"<[^>]+>", " ",
                                           page["content"]["rendered"])))
        seat = re.search(r"\b(District \d+|At[- ]Large)\b", body, re.I)
        is_mayor = re.search(re.escape(name) + r"\s+Mayor\b", body) is not None
        tel = re.search(r"\b(\d{3}[-.]\d{3}[-.]\d{4})\b", body)
        term = re.search(r"Serving from (\d{4}) to (\d{4})", body)
        district = None
        if not is_mayor:
            if not seat:
                warn("champaign: %s names no seat — dropped rather than guessed"
                     % name)
                continue
            district = ("At Large" if seat.group(1).lower().startswith("at")
                        else seat.group(1).title())
        out.append(record(
            city, "Mayor" if is_mayor else "Council Member", name,
            district=district,
            person_phone=phone(tel.group(1), city) if tel else None,
            term="%s-%s" % (term.group(1), term.group(2)) if term else None,
            source_url=page["link"],
        ))
    return out


# ------------------------------------------------------------------ Decatur

DECATUR_RE = re.compile(
    r"^([A-Z][A-Za-z.'’-]+(?: [A-Z][A-Za-z.'’-]+){1,3})\n"
    r"(Councilman|Councilwoman|Council Member|Mayor)$", re.M)


def read_decatur(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in DECATUR_RE.finditer(text):
        name, role = clean(match.group(1)), match.group(2)
        if name in seen:
            continue
        seen.add(name)
        out.append(record(
            city, "Mayor" if role == "Mayor" else "Council Member", name,
            district=None if role == "Mayor" else "At Large"))
    return out


# ------------------------------------------------------------------- Normal

NORMAL_RE = re.compile(r'data-headertext="([^"]{3,60})"')


def read_normal(city, warn):
    markup = get(city["page"])
    out, seen = [], set()
    for raw in NORMAL_RE.findall(markup):
        label = clean(html.unescape(raw))
        mayor = label.startswith("Mayor ")
        name = label[len("Mayor "):] if mayor else label
        if not re.match(r"^[A-Z][A-Za-z.'’-]+(?: [A-Z][A-Za-z.'’-]+){1,3}$",
                        name):
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append(record(city, "Mayor" if mayor else "Council Member", name,
                          district=None if mayor else "At Large"))
    return out


# ------------------------------------------------------------------- Quincy

QUINCY_WARD_RE = re.compile(
    r"\n([A-Z][A-Za-z.'’ -]{3,40})\nWard (\d+) (Alderman|Alderperson)\b")
QUINCY_TEL_RE = re.compile(r"\nTelephone\n([0-9()\- .]{10,20})\n")
# The address under the entry's own "Email" label, on any domain (see the
# docstring). The footer's general mailbox sits under "E:", and the page's
# share-by-e-mail link is a label followed by "Print", so neither matches.
QUINCY_MAIL_RE = re.compile(
    r"\nEmail\n([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?=\n)")
# Anchored on the sentence the mayor's own page uses to introduce her. A letter
# is not a roster, so a miss here warns and never fails — see the docstring.
QUINCY_MAYOR_RE = re.compile(
    r"I[’']m ([A-Z][A-Za-z.'’-]+(?: [A-Z][A-Za-z.'’-]+){1,3}),"
    r"[^.]{0,80}serve as Mayor")


def surname_letters(name):
    """The letters of a name's last word, lower case, a Jr/Sr/II/III/IV dropped."""
    words = [w for w in re.sub(r"[^A-Za-z\s'’-]", " ", name or "").lower().split()
             if w not in ("jr", "sr", "ii", "iii", "iv")]
    return re.sub(r"[^a-z]", "", words[-1]) if words else ""


def quincy_emails(records, mails, warn):
    """Set each alderman's person_email from the addresses read under the
    "Email" label of their own page (mails[i] belongs to records[i]); see the
    docstring. Messages name the ward and the member, never the address."""
    pages = {}
    for found in mails:
        for address in found:
            pages[address.lower()] = pages.get(address.lower(), 0) + 1
    surnames = [surname_letters(r["name"]) for r in records]
    for i, (rec, found) in enumerate(zip(records, mails)):
        where = "quincy: %s (%s)" % (rec["district"], rec["name"])
        if not found:
            continue
        if len(found) > 1:
            warn("%s: the entry prints %d addresses under its Email label; none "
                 "ships rather than one guessed" % (where, len(found)))
            continue
        address = found[0]
        local = re.sub(r"[^a-z]", "", address.split("@", 1)[0].lower())
        own = surnames[i]
        others = [s for j, s in enumerate(surnames)
                  if j != i and len(s) >= 3 and s != own]
        if pages[address.lower()] > 1:
            warn("%s: the e-mail is printed on %d members' pages, so it is not "
                 "this member's; not shipped" % (where, pages[address.lower()]))
        elif not (len(own) >= 3 and own in local) and any(s in local for s in others):
            warn("%s: the e-mail's local part carries another member's surname "
                 "and not this member's; not shipped" % where)
        else:
            problem = person_email_problem(address)
            if problem:
                raise SystemExit("il-large-city-councils: Quincy %s (%s): the "
                                 "e-mail %s" % (rec["district"], rec["name"], problem))
            rec["person_email"] = address


def read_quincy(city, warn):
    index = get(city["page"])
    links = sorted({u for u in re.findall(
        r'href="(https://www\.quincyil\.gov/Government/City-Council/[A-Za-z-]+)"',
        index)})
    skip = {"City-Council-Meeting-Archive", "Municipal-Codebook",
            "Quincy-Strategic-Plan", "Quincy-Ward-Maps"}
    out, mails = [], []
    for url in links:
        if url.rsplit("/", 1)[-1] in skip:
            continue
        text = visible(get(url))
        seat = QUINCY_WARD_RE.search(text)
        if not seat:
            warn("quincy: %s names no ward — dropped rather than guessed" % url)
            continue
        tel = QUINCY_TEL_RE.search(text)
        out.append(record(
            city, seat.group(3), seat.group(1),
            district="Ward %d" % int(seat.group(2)),
            person_phone=phone(tel.group(1), city) if tel else None,
            source_url=url))
        found = []
        for address in QUINCY_MAIL_RE.findall(text[seat.end():]):
            if address.lower() not in [a.lower() for a in found]:
                found.append(address)
        mails.append(found)
    quincy_emails(out, mails, warn)
    mayor_page = "https://www.quincyil.gov/Government/Mayors-Office"
    mayor = QUINCY_MAYOR_RE.search(visible(get(mayor_page)))
    if mayor:
        out.append(record(city, "Mayor", mayor.group(1), source_url=mayor_page))
    else:
        warn("quincy: the mayor's page no longer introduces her in the sentence "
             "this parser reads — the council ships without a head")
    return out


# ----------------------------------------------------------------- Danville

DANVILLE_RE = re.compile(
    r"\n([A-Z][A-Za-z.'’, -]{3,40}?)\n"
    r"(Mayor|Ward (\d+) (?:Alderman|Alderperson))[^\n]*\n"
    # A LOOKAHEAD, NOT A NEWLINE. Consuming the line break after the telephone
    # eats the one the NEXT seat's name needs, so every other seat is skipped:
    # the first draft read 9 of this page's 15 and the floor caught it.
    r"Email [^\n]*\nPhone:\n([0-9()\- .]{10,20})(?=\n)")


def read_danville(city, warn):
    text = visible(get(city["page"]))
    out, seen = [], set()
    for match in DANVILLE_RE.finditer(text):
        name = clean(match.group(1))
        if name in seen:
            continue
        seen.add(name)
        is_mayor = match.group(2) == "Mayor"
        out.append(record(
            city, "Mayor" if is_mayor else "Alderman", name,
            district=None if is_mayor else "Ward %d" % int(match.group(3)),
            person_phone=phone(match.group(4), city)))
    return out


# ------------------------------------------------------------------- Urbana

URBANA_MAYOR_PAGE = "https://www.urbanail.gov/executive-department/page/office-mayor"
URBANA_CLERK_PAGE = "https://www.urbanail.gov/city-clerk"
# The council's shared mailbox, which the council page writes out as
# "CityCouncil[at]urbanail.gov" in its text rather than as a link.
URBANA_MAILBOX_RE = re.compile(r"\b(CityCouncil)\s*\[at\]\s*(urbanail\.gov)\b", re.I)
# A party marker after a member's name, "Maryalice Wu [D]".
URBANA_PARTY_RE = re.compile(r"\s*\[[A-Z]{1,3}\]\s*$")


def cf_email(hexstr):
    """An address Cloudflare's e-mail protection wrote as hex, or None.

    The first byte is a key and every byte after it is XORed with it. Every
    visitor's browser decodes the same bytes to show the address, so reading
    them reads the page as published; il_county_board_pages_scraper.py reads
    Brown, Henry and Franklin the same way.
    """
    try:
        raw = bytes.fromhex(hexstr)
    except ValueError:
        return None
    if len(raw) < 2:
        return None
    return bytes(b ^ raw[0] for b in raw[1:]).decode("utf-8", "replace").strip()


def urbana_listings(markup):
    """Each directory listing on an urbanail.gov page, as (name, position
    markup, telephone text). A listing is the block the site opens with
    `data-history-node-id`; its link holds the name, its position span the
    office and, for a council member, the member's own e-mail."""
    out = []
    for chunk in re.split(r'<div data-history-node-id="\d+"', markup)[1:]:
        name = re.search(r'class="sidebar-photo__link">(.*?)</a>', chunk, re.S)
        position = re.search(r'sidebar-photo__position">(.*?)</span>', chunk, re.S)
        tel = re.search(r'sidebar-photo__phone-number">(.*?)</span>', chunk, re.S)
        if not name or not position:
            continue
        out.append((clean(html.unescape(name.group(1))), position.group(1),
                    clean(html.unescape(tel.group(1))) if tel else None))
    return out


def urbana_position(markup):
    """A position span's words, with the e-mail link taken out."""
    text = re.sub(r"(?s)<a\b.*?</a>", " ", markup)
    return clean(html.unescape(re.sub(r"<[^>]+>", " ", text))) or ""


def read_urbana(city, warn):
    markup = get(city["page"])
    mailbox = URBANA_MAILBOX_RE.search(visible(markup))
    office = dict(city["office"], office_email=(
        "%s@%s" % (mailbox.group(1), mailbox.group(2).lower()) if mailbox else None))
    if not mailbox:
        warn("urbana: the council page no longer prints the council's shared "
             "mailbox — the hall ships without an e-mail")
    city = dict(city, office=office)
    out = []
    for name, position, tel in urbana_listings(markup):
        seat = re.match(r"^\(?Ward (\d+) Council Member\b",
                        urbana_position(position))
        if not seat:
            warn("urbana: %s names no ward — dropped rather than guessed" % name)
            continue
        found = re.findall(r'data-cfemail="([0-9a-f]+)"', position)
        address = cf_email(found[0]) if len(found) == 1 else None
        if len(found) > 1:
            warn("urbana: Ward %s (%s) prints %d addresses beside the seat; none "
                 "ships rather than one guessed" % (seat.group(1), name, len(found)))
        if address:
            problem = person_email_problem(address)
            if problem:
                raise SystemExit("il-large-city-councils: Urbana Ward %s (%s): "
                                 "the e-mail %s" % (seat.group(1), name, problem))
        out.append(record(
            city, "Council Member", URBANA_PARTY_RE.sub("", name),
            district="Ward %d" % int(seat.group(1)),
            person_phone=phone(tel, city), person_email=address))
    # The mayor and the elected City Clerk each have a listing of their own on
    # their office's page. Neither listing prints a telephone or an address of
    # the person's own (each links a contact form), so they ship by name.
    for page, office_name in ((URBANA_MAYOR_PAGE, "Mayor"),
                              (URBANA_CLERK_PAGE, "City Clerk")):
        listed = [name for name, position, _tel in urbana_listings(get(page))
                  if urbana_position(position) == office_name]
        if len(listed) == 1:
            out.append(record(city, office_name, URBANA_PARTY_RE.sub("", listed[0]),
                              source_url=page))
        else:
            warn("urbana: %d listings on %s read %r — none ships rather than one "
                 "guessed" % (len(listed), page, office_name))
    return out


# ------------------------------------------------------------------- cities

CITIES = {
    "champaign": {
        "jurisdiction": "City of Champaign",
        "county": "Champaign",
        "page": "https://champaignil.gov/city-council/",
        "robots_url": "https://champaignil.gov/wp-json/wp/v2/pages?slug=members",
        "office": {"office_address": "102 N Neil St.", "office_city": "Champaign",
                   "office_state": "IL", "office_zip": "61820",
                   "office_phone": "217-403-8720", "office_email": None},
        "read": read_champaign,
        # Mayor, five district seats, three at large.
        "min_officials": 9, "min_districts": 5, "min_heads": 1,
    },
    "decatur": {
        "jurisdiction": "City of Decatur",
        "county": "Macon",
        "page": "https://www.decaturil.gov/300/Mayor-Council",
        "office": {"office_address": "1 Gary K. Anderson Plaza",
                   "office_city": "Decatur", "office_state": "IL",
                   "office_zip": "62523", "office_phone": None,
                   "office_email": None},
        "read": read_decatur,
        # Mayor and six council members, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "normal": {
        "jurisdiction": "Town of Normal",
        "county": "McLean",
        "page": "https://normalil.gov/1135/Meet-the-Council",
        "office": {"office_address": "11 Uptown Circle", "office_city": "Normal",
                   "office_state": "IL", "office_zip": "61761",
                   "office_phone": "309-454-2444", "office_email": None},
        "read": read_normal,
        # Mayor and six trustees, all elected at large.
        "min_officials": 7, "min_districts": 0, "min_heads": 1,
    },
    "quincy": {
        "jurisdiction": "City of Quincy",
        "county": "Adams",
        "page": "https://www.quincyil.gov/Government/City-Council",
        "office": {"office_address": "730 Maine St", "office_city": "Quincy",
                   "office_state": "IL", "office_zip": "62301",
                   "office_phone": "217-228-4500", "office_email": None},
        "read": read_quincy,
        # Seven wards, two aldermen each. The mayor is read where the page
        # still introduces her and is deliberately not a floor.
        "min_officials": 14, "min_districts": 14, "min_heads": 0,
        # Aldermen with an e-mail of their own: 14 of 14, measured 2026-10-17.
        # About two thirds, so a page change that stops the "Email" label
        # being read fails the run instead of emptying the e-mails quietly.
        "min_emails": 9,
    },
    "danville": {
        "jurisdiction": "City of Danville",
        "county": "Vermilion",
        "page": "https://www.cityofdanville.org/220/City-Council",
        "office": {"office_address": "17 West Main Street",
                   "office_city": "Danville", "office_state": "IL",
                   "office_zip": "61832", "office_phone": "217-431-2400",
                   "office_email": None},
        "read": read_danville,
        # Mayor and fourteen aldermen, two per ward across seven wards.
        "min_officials": 15, "min_districts": 14, "min_heads": 1,
    },
    "urbana": {
        "jurisdiction": "City of Urbana",
        "county": "Champaign",
        "page": "https://www.urbanail.gov/city-clerk/page/city-council",
        # The hall is the address and switchboard in every page's footer. The
        # e-mail is the council's shared mailbox, read from the page each run.
        "office": {"office_address": "400 South Vine Street",
                   "office_city": "Urbana", "office_state": "IL",
                   "office_zip": "61801", "office_phone": "217-384-0200",
                   "office_email": None},
        "read": read_urbana,
        # Mayor, seven council members, one per ward, and the elected City
        # Clerk (2026-10-21: all nine). The clerk is not a floor.
        "min_officials": 8, "min_districts": 7, "min_heads": 1,
        # Council members with an e-mail of their own: 7 of 7, measured
        # 2026-10-21. A page change that stops the address being read fails
        # the run instead of emptying the e-mails quietly.
        "min_emails": 5,
    },
}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--only", choices=sorted(CITIES))
    args = ap.parse_args()

    wanted = [args.only] if args.only else sorted(CITIES)
    problems = []
    for key in wanted:
        city = CITIES[key]
        warnings = []
        robots_url = city.get("robots_url", city["page"])
        require_robots_once(robots_url, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-%s-council-scraper" % key)
        officials = city["read"](city, warnings.append)
        districts = sum(1 for r in officials
                        if r["district"] and r["district"] != "At Large")
        heads = sum(1 for r in officials if r["office"] == "Mayor")
        trouble = []
        if len(officials) < city["min_officials"]:
            trouble.append("%d officials < floor %d"
                           % (len(officials), city["min_officials"]))
        if districts < city["min_districts"]:
            trouble.append("%d ward or district seats < floor %d"
                           % (districts, city["min_districts"]))
        if heads < city["min_heads"]:
            trouble.append("%d heads < floor %d" % (heads, city["min_heads"]))
        emails = sum(1 for r in officials if r.get("person_email"))
        if emails < city.get("min_emails", 0):
            trouble.append("%d e-mails < floor %d" % (emails, city["min_emails"]))
        for warning in warnings:
            print("  warning: %s" % warning, file=sys.stderr)
        if trouble:
            problems.append("%s: %s" % (key, "; ".join(trouble)))
            continue
        stamp = now()
        payload = {
            "county": city["county"],
            "kind": "municipal-enrichment",
            "directory_url": city["page"],
            "officials_page": city["page"],
            "scraped_at": stamp,
            "municipalities": [{"name": city["jurisdiction"],
                                "source_url": city["page"],
                                "scraped_at": stamp}],
            "officials": officials,
        }
        out = os.path.join(args.out_dir, "%s_council.json" % key)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print("scraped %s: %d officials (%d seated by ward or district, %d head) "
              "-> %s" % (city["jurisdiction"], len(officials), districts, heads,
                         out), file=sys.stderr)

    if problems:
        raise SystemExit("il-large-city-councils: " + "; ".join(problems)
                         + " — refusing to write")


if __name__ == "__main__":
    main()
