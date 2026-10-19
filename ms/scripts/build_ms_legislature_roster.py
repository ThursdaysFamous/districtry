#!/usr/bin/env python3
"""
Build the Mississippi Senate and Mississippi House rosters (district -> current
officeholder) as same-origin app-data files, from the Mississippi Legislature's
OWN member gallery and member profiles, so the ms-senate / ms-house cards join a
small roster instead of reaching a third-party host at click time.

index.html's ms-senate / ms-house layers fetch data/app/ms-senate-members.json
and ms-house-members.json lazily on first click and join them to the pre-built
legislative geometry by district number. This script reads the gallery each
chamber's page on www.legislature.ms.gov embeds, and each member's profile, and
writes the two rosters shaped for the registerIlgaChamber factory
({district -> {name, party, email, capitolOffice, phone?, phonesExtra?, url}}, or
a vacancy record). A
weekly GitHub Action (.github/workflows/update-ms-legislature-roster.yml) reruns
this and opens a PR when a roster changes, so officeholder data gets a human look
before it ships.

WHERE THE MEMBERS ARE, MEASURED 2026-10-15. The Senate's page
(/legislators/senators/) and the House's (/legislators/representatives/) each
embed a member gallery at /member/?fiscalyear=NN&chamber=S|H, one card per seat:
a sitting member's card carries the district, the fiscal year, the chamber and a
member key, and a vacant seat's card reads "Vacant" over its district. A member's
profile is an HTML fragment the gallery loads into a dialog from
/member/Home/MemberBio, keyed by the fiscal year, the chamber, the member key and
the district AS A THREE-CHARACTER, SPACE-PADDED STRING: district=%2039 answers
Senator Barrett's profile and district=39 answers "No record found." That day the
Senate gallery held 53 cards — 51 senators, one vacant seat (District 34) and the
Lieutenant Governor, who presides as President of the Senate under a District 53
that is no seat, with a link to his own site instead of a profile — and the House
gallery 122: 120 representatives and two vacant seats (Districts 70 and 77).

THE FISCAL YEAR IS READ OFF THE LEGISLATURE'S OWN PAGE AND NEVER COMPUTED, and
the measurement is why. On 2026-10-15, three and a half months into fiscal 2027,
both pages still embed fiscalyear=26. A fiscal-2027 gallery answers at the same
address, and it names a member in all three seats the fiscal-2026 gallery shows
vacant — Juan Barnett (Senate 34), Bo Brown (House 70) and Price Wallace (House
77) — while every fiscal-2027 profile, the sitting members' included, answers
"No record found." Two of the legislature's other publications side with the
fiscal-2026 gallery: the Senate roster PDF (/legislators/senate-roster/, "Updated
September 2, 2026") prints District 34 as Vacant, and the House roster PDF (dated
July 7, 2026) lists no Bo Brown. And all three names are the ones the
legislature's old XML member lists (term 2024-2027, last updated before those
seats fell vacant) still carry, so the newer gallery looks seeded from a stale
copy rather than updated. So a newer fiscal year is NOT evidence of a newer
roster here, and the builder follows whichever gallery the legislature's own
pages show a reader. A profile that answers "No record found." stops the build,
which keeps a page that moves to an unfilled gallery from shipping names nobody
has a profile for.

WHAT A PROFILE IS READ FOR, AND WHAT IT IS NEVER READ FOR. A profile prints the
member's name, district, counties, party, a biography, the Capitol office, a
"Home" address, a "Phone(s)" block and an e-mail address; three biographies also
print a personal e-mail address in their text (2026-10-19). This script reads
the heading block (name, district, party) and the blocks headed "Capitol",
"Phone(s)" and "Email", each by its own heading, and nothing else: the Home
block and the biography are never parsed, because a legislator's home address is
no part of answering who represents you and this project never publishes one.
Inside the Capitol block it keeps only what is the legislature's: a telephone
only on the Capitol's own (601) 359 exchange. The Email block's address ships
only as a plain address on the chamber's own domain (senate.ms.gov,
house.ms.gov). Anything else in those two blocks is dropped and the run says so.
THAT TEST IS ON THE WHOLE ADDRESS AND NOT ITS ENDING, and the measurement is why:
the profile appends the chamber's domain to whatever the legislature stores, so
on 2026-10-15 nine House profiles printed "<name>@house.ms.gov@house.ms.gov",
six printed "@house.ms.gov" with no mailbox in front of it, and one printed a
member's personal AOL address with "@house.ms.gov" stuck on the end — which an
ends-with test would have published. chamber_email() takes one doubled copy of
the domain off and refuses anything that is not then a plain chamber address.

THE MEMBER'S OWN TELEPHONES SHIP SINCE 2026-10-19. Until then the Phone(s) block
was not read either. On 2026-10-17 Adam ruled for the whole fleet, "if the
official government source uses personal phone numbers, we publish those", and
these profiles are the legislature's own pages printing each member's numbers.
Each line of the block is a label and a tel: link, most with a letter in
brackets after the number. Measured on 2026-10-19 across all 171 profiles, 96
print the block, holding 132 lines in four shapes and no other: "Home:" with no
letter (44), "Business:" with (W) (54), "Other:" with (C) (29) and "Other:" with
(F) (5). The first three ship as "home", "business" and "cell" in front of the
number as the page prints it ("cell (601) 555-0100"); the first number is the
member's `phone` and the rest are `phonesExtra`, in page order. A line marked
(F) is a fax and never ships, and a line in any other shape is not read and the
run names its label. A number is also not carried on a member's row when its
tel: link dials digits other than the ones it prints (none that day), when it is
on the Capitol's (601) 359 exchange or equal to a number in the member's Capitol
block, which the Capitol office already shows (none), when it is a second copy
of a number earlier in the same block (three representatives, each carried once
with its first label; a senator's business line printed again as the fax line
ships once, as business), or when the profiles print it for two or more members,
because a number two legislators share is an office's (none). That day 124
numbers shipped on 96 members, 20 senators and 76 representatives, and the
floors in CHAMBERS are about two thirds of those two counts.

THE E-MAIL RULE DID NOT CHANGE WITH THE RULING ON PERSONAL ADDRESSES, AND THAT
WAS CHECKED RATHER THAN ASSUMED. Adam chose on 2026-10-17 to publish a personal
e-mail address a government page prints beside an official. On 2026-10-19 the
three biographies that print one belong to members whose Email block prints
their chamber address, and a card carries one address per person, the chamber's.
The one profile whose Email block holds a personal address prints it with
"@house.ms.gov" appended, which is not an address anyone can write to. Taking
the suffix off would publish an address at another provider that the page never
prints whole, so it stays dropped and the run says so; removing a doubled copy
of the chamber's own domain is different, because what is left is the chamber
mailbox the legislature itself runs.

THE CERTIFICATE CHAIN IS INCOMPLETE. www.legislature.ms.gov serves only its leaf
certificate (issued by GlobalSign RSA OV SSL CA 2018, measured 2026-10-15), so
every automated client stops at "unable to get local issuer certificate" while a
browser completes the chain from the certificate's own AIA address. The missing
intermediate comes from scripts/aia_bundle.py, pinned by hash under
`globalsign-rsa-ov-2018`; verification is never disabled.

ROBOTS. www.legislature.ms.gov answers /robots.txt with 404 (read 2026-10-15),
which RFC 9309 2.3.1.3 reads as no policy, so every path is permitted. It is read
before the first fetch through scraper_common.require_robots_once, with the same
User-Agent and the same pinned trust store the fetches use. No Crawl-delay is
stated; the profiles are paced at one second anyway. THE ROBOTS READ TRUSTS THE
BUNDLE TO A SESSION, and requests lets REQUESTS_CA_BUNDLE and then CURL_CA_BUNDLE
win over a session's own: CI sets neither, this project's sandbox sets both, so
run it locally with both unset (`env -u REQUESTS_CA_BUNDLE -u CURL_CA_BUNDLE`),
which is CI's condition, or the read fails on the missing intermediate.

Honesty: names are never guessed. A seat the gallery shows as vacant gets a
vacancy record naming the chamber's page; a seat with no card, or with two,
stops the build.

Usage:
    python3 ms/scripts/build_ms_legislature_roster.py [output_dir]
    python3 ms/scripts/build_ms_legislature_roster.py --save DIR [output_dir]
    python3 ms/scripts/build_ms_legislature_roster.py --offline DIR [output_dir]

--save writes every page fetched into DIR (page-S.html, page-H.html,
gallery-S.html, gallery-H.html and bio/<chamber>-<district>.html), reading back
any it already holds; --offline reads them back instead of fetching, for
building and testing without the network.
"""

import datetime
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
import aia_bundle  # noqa: E402  (FLEET_SHARED — the one copy of the pins)
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

USER_AGENT = "districtry/1.0 (+https://districtry.com/ms/)"
BASE = "https://www.legislature.ms.gov"
INTERMEDIATE = "globalsign-rsa-ov-2018"
PACE_SECONDS = 1.0
ATTEMPTS = 3
RETRY_SECONDS = 5.0

# Floors catch a truncated gallery or a layout change while tolerating real
# vacancies: 51 of 52 senators and 120 of 122 representatives were named on
# 2026-10-15. "phones" floors the members carrying a telephone of their own: 20
# senators and 76 representatives on 2026-10-19.
CHAMBERS = {
    "S": {"page": BASE + "/legislators/senators/", "out": "ms-senate-members.json",
          "label": "Senate", "profile": "SENATE PROFILE", "domain": "senate.ms.gov",
          "expected": 47, "seats": 52, "phones": 13},
    "H": {"page": BASE + "/legislators/representatives/", "out": "ms-house-members.json",
          "label": "House", "profile": "HOUSE OF REPRESENTATIVES PROFILE",
          "domain": "house.ms.gov", "expected": 110, "seats": 122, "phones": 50},
}
# Every named member carried a chamber e-mail and a Capitol block on
# 2026-10-15. A field every row carries going missing is the Brown County
# shape: the row count holds and the contact goes.
MIN_FIELD_SHARE = 0.9

# The profile prints the party as a word. Anything else ships as printed, and
# the run says so, rather than being guessed at.
PARTY_NAMES = {"Republican": "Republican", "Democrat": "Democratic",
               "Democratic": "Democratic", "Independent": "Independent"}

INSTANCE_ROOT = os.path.dirname(_HERE)
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")

GALLERY_RE = re.compile(r'src="(/member/\?fiscalyear=(\d+)&(?:amp;)?chamber=([SH]))"')
CARD_RE = re.compile(
    r'<div class="card( active-member)? m-2 shadow-sm"([^>]*)>(.*?)'
    r'(?=<div class="card(?: active-member)? m-2 shadow-sm"|<script)', re.S)
ATTR_RE = re.compile(r'data-([a-zA-Z_]+)="([^"]*)"')
CARD_NAME_RE = re.compile(r'<div class="flex-grow-1">\s*([^<]*?)\s*</div>')
CARD_EM_RE = re.compile(r'<em>\s*([^<]*?)\s*</em>')

PROFILE_TITLE_RE = re.compile(r'<h4 class="modal-title"[^>]*>\s*([^<]*?)\s*</h4>')
PROFILE_NAME_RE = re.compile(r'<h3 class="text-center fw-bold">\s*([^<]*?)\s*</h3>')
PROFILE_DISTRICT_RE = re.compile(r'<h5 class="text-center">\s*District\s+(\d+)\s*</h5>')
PROFILE_H6_RE = re.compile(r'<h6 class="text-center[^"]*">\s*([^<]*?)\s*</h6>')
CAPITOL_RE = re.compile(r'<h6 class="fw-bold">Capitol</h6>\s*<p>(.*?)</p>', re.S)
EMAIL_RE = re.compile(r'<h6 class="fw-bold">Email</h6>\s*<p>\s*<a href="mailto:([^"]+)"')
CAPITOL_PHONE_RE = re.compile(r'^\(601\) 359-\d{4}$')
CAPITOL_CITY_RE = re.compile(r'^Jackson, MS 392\d\d(?:-\d{4})?$')
# A Capitol-block line that holds a telephone: a number, and no five-digit ZIP.
PHONE_IN_LINE_RE = re.compile(r"\d{3}\)?[\s.-]*\d{3}[\s.-]\d{4}")
ZIP_IN_LINE_RE = re.compile(r"\d{5}")

# The "Phone(s)" block: one line per number, each a <label> and a tel: link,
# most with a letter in brackets after the number.
PHONES_RE = re.compile(r'<h6 class="fw-bold">Phone\(s\)</h6>\s*<p>(.*?)</p>', re.S)
PHONE_LABEL_RE = re.compile(r'<label>\s*([^<]*?)\s*</label>')
PHONE_LETTER_RE = re.compile(r'<span>\s*([^<]*?)\s*</span>')
PHONE_TEL_RE = re.compile(r'href="tel:([^"]*)"')
PHONE_SHOWN_RE = re.compile(r'^\(\d{3}\) \d{3}-\d{4}$')
# Every Phone(s) line on 2026-10-19 took one of these four shapes, by (label,
# letter), and each ships with the word it maps to. None is a fax line, which
# never ships. A line in any other shape is not read and the run names it.
PHONE_KINDS = {("Home:", None): "home", ("Business:", "(W)"): "business",
               ("Other:", "(C)"): "cell", ("Other:", "(F)"): None}

_SESSION = None
_LAST = [0.0]


def session():
    """A requests session that verifies against the trusted roots plus the
    pinned GlobalSign intermediate the host leaves out."""
    global _SESSION
    if _SESSION is None:
        import requests

        _SESSION = requests.Session()
        _SESSION.verify = aia_bundle.ca_bundle("ms-build-ms-legislature-roster",
                                               INTERMEDIATE)
        _SESSION.headers["User-Agent"] = USER_AGENT
    return _SESSION


def fetch(url):
    import requests

    wait = PACE_SECONDS - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)
    last = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_SECONDS * attempt)
        try:
            # verify= per request, never trusted to the session alone: requests
            # lets REQUESTS_CA_BUNDLE and then CURL_CA_BUNDLE win over
            # session.verify (scripts/ilga_scraper.py, measured 2026-09-21).
            resp = session().get(url, timeout=60, verify=session().verify)
            _LAST[0] = time.time()
            resp.raise_for_status()
            resp.encoding = resp.encoding or "utf-8"
            return resp.text
        except requests.RequestException as exc:  # reset, timeout, 5xx
            last = exc
    raise SystemExit("FAIL: %s did not answer after %d attempts (%s)"
                     % (url, ATTEMPTS, last))


class Pages:
    """Fetch, save or replay the pages one run reads."""

    def __init__(self, offline=None, save=None):
        self.offline, self.save = offline, save

    def get(self, name, url):
        if self.offline:
            with open(os.path.join(self.offline, name), encoding="utf-8") as fh:
                return fh.read()
        if self.save and os.path.exists(os.path.join(self.save, name)):
            # A page an interrupted --save run already wrote is read back
            # rather than fetched twice.
            with open(os.path.join(self.save, name), encoding="utf-8") as fh:
                return fh.read()
        text = fetch(url)
        if self.save:
            path = os.path.join(self.save, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return text


def clean(text):
    return re.sub(r"\s+", " ", html_module.unescape(text or "")).strip()


def surname(name):
    # Periods split too: one profile prints "Joel R.Carter, Jr." (2026-10-15).
    parts = [p for p in re.split(r"[\s,.]+", clean(name)) if p]
    while parts and parts[-1].rstrip(".").lower() in ("jr", "sr", "ii", "iii", "iv", "v"):
        parts.pop()
    return parts[-1].lower() if parts else ""


def gallery_src(page, chamber):
    found = GALLERY_RE.findall(page)
    if len(found) != 1 or found[0][2] != chamber:
        raise SystemExit("FAIL: the %s page embeds %d member galleries (%r) — the "
                         "page layout changed" % (CHAMBERS[chamber]["label"],
                                                  len(found), found))
    return html_module.unescape(found[0][0]), found[0][1]


def parse_gallery(page, chamber, fiscal_year):
    """[(district, card)] where card is {"vacant": True} or the member's keys."""
    cfg = CHAMBERS[chamber]
    out = []
    for active, attrs, body in CARD_RE.findall(page):
        name = CARD_NAME_RE.search(body)
        name = clean(name.group(1)) if name else ""
        labels = [clean(x) for x in CARD_EM_RE.findall(body)]
        if not active:
            m = re.match(r"District (\d+)$", labels[0] if labels else "")
            if name != "Vacant" or not m:
                raise SystemExit("FAIL: a %s gallery card is neither a member nor "
                                 "a vacant seat (%r, %r)" % (cfg["label"], name, labels))
            out.append((int(m.group(1)), {"vacant": True}))
            continue
        a = dict(ATTR_RE.findall(attrs))
        district_raw = a.get("district", "")
        if not district_raw.strip().isdigit() or not name:
            raise SystemExit("FAIL: a %s gallery card carries no district or name — "
                             "the page layout changed (%r)" % (cfg["label"], a))
        district = int(district_raw)
        if a.get("chamber") != chamber or a.get("fiscal_year") != fiscal_year:
            raise SystemExit("FAIL: %s's card says chamber %r, fiscal year %r, inside "
                             "the %s gallery for fiscal year %s"
                             % (name, a.get("chamber"), a.get("fiscal_year"),
                                cfg["label"], fiscal_year))
        if not 1 <= district <= cfg["seats"]:
            # The presiding officer who is not a member: the Lieutenant
            # Governor, carded as District 53 with a link to his own site. A
            # card outside the seat range WITHOUT such a link is a layout
            # change, not an officer.
            if not a.get("customURL"):
                raise SystemExit("FAIL: %s District %d is not one of the chamber's %d "
                                 "seats" % (cfg["label"], district, cfg["seats"]))
            out.append((None, {"officer": name, "role": labels[0] if labels else ""}))
            continue
        out.append((district, {"name": name, "key": a.get("mem_name", ""),
                               "district_raw": district_raw, "role": labels[0] if labels else ""}))
    return out


def profile_fields(page, chamber, who):
    """(name, district, party_word, capitol_lines, email) from a profile.

    Reads the heading block, the "Capitol" block and the "Email" block only;
    see the module docstring."""
    cfg = CHAMBERS[chamber]
    if "No record found" in page and "<h3" not in page:
        raise SystemExit("FAIL: %s %s's profile answers \"No record found.\" — the "
                         "gallery names a member the legislature has no profile for"
                         % (cfg["label"], who))
    title = PROFILE_TITLE_RE.search(page)
    name = PROFILE_NAME_RE.search(page)
    district = PROFILE_DISTRICT_RE.search(page)
    if not title or not name or not district:
        raise SystemExit("FAIL: %s %s's profile carries no title, name or district — "
                         "the profile layout changed" % (cfg["label"], who))
    if clean(title.group(1)) != cfg["profile"]:
        raise SystemExit("FAIL: %s %s's profile is titled %r" % (cfg["label"], who,
                                                                 clean(title.group(1))))
    party = None
    for text in PROFILE_H6_RE.findall(page):
        if clean(text) in PARTY_NAMES:
            party = clean(text)
    capitol = None
    block = CAPITOL_RE.search(page)
    if block:
        raw = re.sub(r"<label>\s*Room:\s*</label>", "Room ", block.group(1))
        capitol = [clean(re.sub(r"<[^>]+>", " ", part))
                   for part in re.split(r"<br\s*/?>", raw)]
        capitol = [line for line in capitol if line]
    email = EMAIL_RE.search(page)
    return (clean(name.group(1)), int(district.group(1)), party, capitol,
            clean(email.group(1)) if email else None)


LOCAL_PART_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def chamber_email(raw, domain):
    """`raw` as a plain address on the chamber's own domain, or None.

    The profile builds its address by appending "@<domain>" to what the
    legislature stores, so where the stored value already carries a domain the
    page prints two: measured 2026-10-15, nine House profiles print
    "<name>@house.ms.gov@house.ms.gov", and one prints a personal address with the
    House's domain appended to it; six more print the domain with no mailbox in
    front of it. One trailing copy of the chamber's own domain
    is therefore taken off when another "@" remains, and what is left must be a
    plain address on that domain or nothing ships — which drops the personal
    address rather than publishing it."""
    email = raw.strip()
    tail = "@" + domain
    if email.lower().endswith(tail) and email[:-len(tail)].count("@"):
        email = email[:-len(tail)]
    local, _, host = email.rpartition("@")
    if email.count("@") != 1 or host.lower() != domain or not LOCAL_PART_RE.match(local):
        return None
    return email


def keep_capitol(lines, notes, where):
    """The Capitol block as the legislature's own office, or None.

    A telephone is kept only on the Capitol's (601) 359 exchange, and the block
    must carry the Capitol's own Jackson address; anything else is dropped."""
    if not lines:
        return None
    kept = []
    for line in lines:
        if PHONE_IN_LINE_RE.search(line) and not ZIP_IN_LINE_RE.search(line):
            if CAPITOL_PHONE_RE.match(line):
                kept.append(line)
            else:
                notes.append("%s: a Capitol-block telephone off the Capitol exchange "
                             "was dropped" % where)
            continue
        kept.append(line)
    if not any(CAPITOL_CITY_RE.match(line) for line in kept):
        notes.append("%s: the Capitol block carries no Jackson address, so none ships"
                     % where)
        return None
    return kept


def digits(text):
    return re.sub(r"\D", "", text or "")


def phone_lines(page, where, notes):
    """[(kind, number)] from the profile's "Phone(s)" block, in page order.

    Reads that block alone, never the Home block printed above it; see the
    module docstring. A fax line, a line in a shape PHONE_KINDS does not name,
    and a line whose tel: link dials digits other than the ones it prints are
    not carried, and the run says so without printing the number."""
    block = PHONES_RE.search(page)
    if not block:
        return []
    out = []
    for line in re.split(r"<br\s*/?>", block.group(1)):
        if not re.sub(r"<[^>]+>|\s", "", line):
            continue
        label = PHONE_LABEL_RE.search(line)
        letter = PHONE_LETTER_RE.search(line)
        shape = (label.group(1) if label else None, letter.group(1) if letter else None)
        if shape not in PHONE_KINDS:
            notes.append("%s: a Phone(s) line labelled %r with the letter %r was not "
                         "read" % (where, shape[0], shape[1]))
            continue
        kind = PHONE_KINDS[shape]
        if kind is None:
            notes.append("%s: a fax line was not carried" % where)
            continue
        shown = clean(re.sub(r"<[^>]+>", " ", re.sub(
            r"<label>.*?</label>|<span>.*?</span>", " ", line, flags=re.S)))
        tel = PHONE_TEL_RE.search(line)
        dialled = digits(tel.group(1)) if tel else ""
        if len(dialled) == 11 and dialled.startswith("1"):
            dialled = dialled[1:]
        if not PHONE_SHOWN_RE.match(shown):
            notes.append("%s: a %s line does not print one ten-digit number, so it "
                         "was not carried" % (where, kind))
            continue
        if dialled != digits(shown):
            notes.append("%s: a %s line's link dials a different number from the one "
                         "it prints, so it was not carried" % (where, kind))
            continue
        out.append((kind, shown))
    return out


def own_phones(page, capitol, where, notes):
    """The member's own numbers as [(kind, number)], once each.

    A number on the Capitol's (601) 359 exchange, or equal to a number in the
    member's own Capitol block, is the Capitol office's, which the card already
    shows. A number the block prints twice rides once, with its first label."""
    office = {digits(line)[-10:] for line in (capitol or [])
              if PHONE_IN_LINE_RE.search(line) and not ZIP_IN_LINE_RE.search(line)}
    out, seen = [], set()
    for kind, number in phone_lines(page, where, notes):
        d = digits(number)
        if d.startswith("601359") or d in office:
            notes.append("%s: a Phone(s) number is the Capitol office's, so it rides "
                         "the office and not the member" % where)
            continue
        if d in seen:
            notes.append("%s: a number the Phone(s) block prints twice is carried "
                         "once, with its first label" % where)
            continue
        seen.add(d)
        out.append((kind, number))
    return out


def read_previous(out_dir, cfg):
    path = os.path.join(out_dir, cfg["out"])
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def member_url(src, key, district_raw):
    """The gallery, opened on this member's profile.

    The gallery reads `member` and `district` from its own address and opens that
    member's dialog on load; the district must keep its padding, exactly as the
    profile request does (measured 2026-10-15)."""
    query = urllib.parse.urlencode({"member": key.strip(), "district": district_raw},
                                   quote_via=urllib.parse.quote)
    return BASE + src + "&" + query


def build(pages, out_dir, today):
    built = {}
    odd_parties = []
    for chamber, cfg in CHAMBERS.items():
        page = pages.get("page-%s.html" % chamber, cfg["page"])
        src, fiscal_year = gallery_src(page, chamber)
        gallery = pages.get("gallery-%s.html" % chamber, BASE + src)
        cards = parse_gallery(gallery, chamber, fiscal_year)
        previous = read_previous(out_dir, cfg)
        seats, notes = {}, []
        for district, card in cards:
            if district is None:
                notes.append("%s: %s (%s) presides and holds no seat; not a member"
                             % (cfg["label"], card["officer"], card["role"]))
                continue
            if district in seats:
                raise SystemExit("FAIL: %s District %d carries two gallery cards"
                                 % (cfg["label"], district))
            if card.get("vacant"):
                prev = previous.get(str(district)) or {}
                seats[district] = {
                    "vacant": True,
                    "vacantWhy": ("The Mississippi Legislature's member list shows "
                                  "this seat as vacant."),
                    "sourceUrl": cfg["page"],
                    "asOf": (prev.get("asOf") if prev.get("vacant") else None) or today,
                }
                notes.append("%s %d: vacant" % (cfg["label"], district))
                continue
            where = "%s %d" % (cfg["label"], district)
            bio_url = (BASE + "/member/Home/MemberBio?" + urllib.parse.urlencode(
                {"fiscalYear": fiscal_year, "chamber": chamber, "mem_name": card["key"],
                 "district": card["district_raw"]}, quote_via=urllib.parse.quote))
            bio = pages.get("bio/%s-%d.html" % (chamber, district), bio_url)
            name, page_district, party, capitol, email = profile_fields(bio, chamber,
                                                                        card["name"])
            # The profile must agree with the card about which seat and which
            # person, or the two pages describe different people and nothing
            # from either ships.
            if page_district != district:
                raise SystemExit("FAIL: the gallery puts %s in %s District %d and the "
                                 "profile says District %d"
                                 % (card["name"], cfg["label"], district, page_district))
            if surname(name) != surname(card["name"]):
                raise SystemExit("FAIL: %s: the gallery names %r and the profile %r"
                                 % (where, card["name"], name))
            member = {"name": card["name"]}
            if party:
                member["party"] = PARTY_NAMES[party]
            else:
                odd_parties.append(where)
            if email:
                kept = chamber_email(email, cfg["domain"])
                if kept:
                    member["email"] = kept
                elif email.strip().lower() == "@" + cfg["domain"]:
                    notes.append("%s: the profile's e-mail block prints the domain and "
                                 "no mailbox" % where)
                else:
                    notes.append("%s: an e-mail address that is not a plain %s address "
                                 "was dropped" % (where, cfg["domain"]))
            office = keep_capitol(capitol, notes, where)
            if office:
                member["capitolOffice"] = office
            # Settled below, once both chambers are read, because a number
            # two members share is an office's.
            member["_phones"] = own_phones(bio, capitol, where, notes)
            member["url"] = member_url(src, card["key"], card["district_raw"])
            if card["role"] and not card["role"].startswith("District"):
                notes.append("%s: %s is carded as %s" % (where, card["name"], card["role"]))
            seats[district] = member

        missing = [d for d in range(1, cfg["seats"] + 1) if d not in seats]
        if missing:
            raise SystemExit("FAIL: the %s gallery carries no card for District(s) %s"
                             % (cfg["label"], ", ".join(map(str, missing))))
        roster = {str(d): seats[d] for d in range(1, cfg["seats"] + 1)}
        named = [m for m in roster.values() if m.get("name")]
        if len(named) < cfg["expected"]:
            raise SystemExit("FAIL: resolved %d named %s districts (expected >= %d) — "
                             "refusing to overwrite the roster with an incomplete "
                             "chamber" % (len(named), cfg["label"], cfg["expected"]))
        for field in ("email", "capitolOffice"):
            have = sum(1 for m in named if m.get(field))
            if have < MIN_FIELD_SHARE * len(named):
                raise SystemExit("FAIL: only %d of %d %s members carry %s — a field the "
                                 "profiles carried on every member stopped arriving"
                                 % (have, len(named), cfg["label"], field))
        built[chamber] = (roster, fiscal_year, notes)

    # A number the profiles print for two or more members, in either chamber,
    # is an office's and ships on no member's row.
    holders = {}
    for chamber, (roster, _, _) in built.items():
        for district, member in roster.items():
            for _, number in member.get("_phones", ()):
                holders.setdefault(digits(number), []).append(
                    "%s %s" % (CHAMBERS[chamber]["label"], district))
    shared = {d for d, who in holders.items() if len(who) > 1}
    for who in sorted(" and ".join(w) for w in holders.values() if len(w) > 1):
        print("NOTE: a Phone(s) number is printed for %s, so it is an office's and "
              "ships on no member's row" % who, file=sys.stderr)
    for chamber, (roster, _, _) in built.items():
        cfg = CHAMBERS[chamber]
        for member in roster.values():
            if "_phones" not in member:
                continue
            numbers = ["%s %s" % (kind, number) for kind, number in member.pop("_phones")
                       if digits(number) not in shared]
            if numbers:
                url = member.pop("url")
                member["phone"] = numbers[0]
                if len(numbers) > 1:
                    member["phonesExtra"] = numbers[1:]
                member["url"] = url
        have = sum(1 for m in roster.values() if m.get("phone"))
        if have < cfg["phones"]:
            raise SystemExit("FAIL: only %d %s members carry a telephone of their own "
                             "(expected >= %d) — the profiles stopped printing the "
                             "Phone(s) block, or its layout changed"
                             % (have, cfg["label"], cfg["phones"]))
    if odd_parties:
        print("NOTE: no party word on the profile for %s" % "; ".join(odd_parties),
              file=sys.stderr)
    return built


def main():
    args = sys.argv[1:]
    offline = save = None
    while args and args[0] in ("--offline", "--save"):
        if len(args) < 2:
            print(__doc__.split("Usage:")[1].split("--save writes")[0], file=sys.stderr)
            sys.exit(1)
        if args[0] == "--offline":
            offline = args[1]
        else:
            save = args[1]
        args = args[2:]
    if len(args) > 1 or (offline and save):
        print("usage: %s [--offline DIR | --save DIR] [output_dir]" % sys.argv[0],
              file=sys.stderr)
        sys.exit(1)
    out_dir = args[0] if args else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()

    try:
        if not offline:
            require_robots_once(CHAMBERS["S"]["page"], USER_AGENT,
                                label="ms-build-ms-legislature-roster",
                                verify=session().verify)
        built = build(Pages(offline, save), out_dir, today)
    finally:
        if _SESSION is not None:
            try:
                os.unlink(_SESSION.verify)
            except OSError:
                pass

    # Write only once BOTH chambers have passed every guard, so a failure in
    # the House cannot leave a fresh Senate file beside a stale House one.
    os.makedirs(out_dir, exist_ok=True)
    for chamber, (roster, fiscal_year, notes) in built.items():
        cfg = CHAMBERS[chamber]
        out_path = os.path.join(out_dir, cfg["out"])
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        named = [m for m in roster.values() if m.get("name")]
        print("Wrote %s (fiscal-year %s gallery; %d of %d seats named, %d with an "
              "e-mail, %d with a Capitol office, %d with a telephone of their own, "
              "%d numbers in all)"
              % (out_path, fiscal_year, len(named), cfg["seats"],
                 sum(1 for m in named if m.get("email")),
                 sum(1 for m in named if m.get("capitolOffice")),
                 sum(1 for m in named if m.get("phone")),
                 sum(1 + len(m.get("phonesExtra", ())) for m in named if m.get("phone"))),
              file=sys.stderr)
        for note in notes:
            print("  " + note, file=sys.stderr)


if __name__ == "__main__":
    main()
