#!/usr/bin/env python3
"""
Scrape Peoria County's board roster into raw records.

Stage 1 of the two-stage pipeline (scripts/build_peoria_board_roster.py is
stage 2). Peoria is the first county whose roster SPINE is a GIS layer rather
than a page: the county's own `ElectoralDistricts` service publishes a
"County Commissioners" layer carrying, for each of the 18 single-member
districts, the member's name, party and the URL of that member's own page on
the county site. That layer is a stable, machine-readable enumeration — no
markup parsing decides who is on the board — and each member page then
supplies the phone and e-mail the layer does not carry.

So the district assignment and the name come from the county's GIS, the
contact from the county's own member page, and the pair is cross-checked
against the County Board Members index page (a THIRD county surface): a name
the index does not carry is reported, because two county surfaces disagreeing
is exactly the drift this pipeline exists to catch. That cross-check is carried
in the output as an `index` block and floored by the builder — before
2026-09-11 it was a line on stderr, which is how a run that lost three of the
eighteen members from the index shipped anyway.

Peoria elects a Chairperson and a Vice-Chairperson from among the 18 — both
hold their own district seat as well — and the index page is the only surface
that marks them, so the role is read from there and attached to that member's
district row (never invented: a role appears only if the index states it).

FETCH POSTURE: open. Plain ArcGIS REST JSON + server-rendered CivicPlus HTML.

Usage:
    python3 peoria_county_board_scraper.py [output.json]   # default: stdout
"""

import contextlib
import html as html_mod
import io
import json
import re
import sys
import urllib.parse

import requests

from arcgis_error import raise_for_arcgis_error
from scraper_common import require_robots_once, UA_ROSTER_COMPACT  # noqa: E402  (shared machinery — do not fork)

ROSTER_LAYER = ("https://services.arcgis.com/iPiPjILCMYxPZWTc/arcgis/rest/"
                "services/ElectoralDistricts/FeatureServer/3/query")
INDEX_URL = "https://www.peoriacounty.gov/755/County-Board-Members"
UA = {"User-Agent": UA_ROSTER_COMPACT}

# THE MEMBER PAGES' E-MAIL ADDRESSES SIT BEHIND CLOUDFLARE'S E-MAIL PROTECTION,
# and that stopped this roster for three weeks. Measured 2026-10-17 on all 18
# member pages, read with this scraper's own client after robots.txt: not one
# carries a `mailto:` link. Each "Email <name>" link points at
# `/cdn-cgi/l/email-protection#<hex>`, and an address printed as text is an
# element carrying `data-cfemail="<hex>"` that reads "[email protected]" until
# the visitor's browser runs Cloudflare's script. This reader looked only for
# `mailto:`, found nothing on any page, and the builder's e-mail floor refused
# the weekly runs of 2026-10-02, 10-09 and 10-16 ("only 0 e-mails resolved");
# the last good read was 2026-09-25. Both forms are now decoded the way
# scripts/will_county_board_scraper.py's cf_decode does (the first byte is a
# key XORed over the rest), which is what Cloudflare's script does in a
# reader's browser. A plain `mailto:` link or a plain-text address is still
# read, for the day the protection is switched off. HTML comments, scripts and
# styles are not read.
#
# AN ADDRESS SHIPS ONLY WHERE THE PAGE SHOWS IT TO A READER. District 3's page
# carries two protected addresses: one printed under the member's office
# address, whose local part carries the member's surname, and an empty link
# further down (an <a> with no text) whose local part carries no board member's
# surname. A reader sees only the first, and the roster shipped on 2026-09-25
# carries the second. So a link with no visible text is not read; a link whose
# visible text shows one address while it sends to another ships nothing for
# that member; an address shown on two or more member pages is an office's and
# ships on nobody; and where a page shows several addresses of the member's
# own, the single one on the county's domain ships (one e-mail per person), or
# none if there is not exactly one. Measured that day, every page shows exactly
# one. Any domain ships, as it always has here, which Adam's choice of
# 2026-10-17 ("E-mails too") confirms; addresses are lower-cased as before.
CF_ELEMENT_RE = re.compile(
    r'(?is)<(a|span)\b[^>]*\bdata-cfemail="([0-9a-fA-F]+)"[^>]*>.*?</\1>')
CF_HREF_RE = re.compile(r'(?i)\bhref="/cdn-cgi/l/email-protection#([0-9a-fA-F]+)"')
MAILTO_HREF_RE = re.compile(r"""(?i)\bhref=["']mailto:([^"'?]*)""")
ANCHOR_RE = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
COUNTY_MAIL_DOMAINS = ("peoriacounty.gov", "peoriacounty.org")
# THE MEMBER PAGES LABEL THEIR NUMBERS, AND EVERY LABELLED NUMBER SHIPS. Measured
# on 2026-10-17 across the 18 member pages, the labels are "Phone:", "Work
# Phone:", "Work phone:", "Cell Phone:", "Cell phone:", "Cell:", "Business:" and
# "Home:", and five members print two numbers. Until that day only the first
# number labelled "...Phone:" shipped: on one page that was the member's cell
# rather than the work line printed after it, and two members whose labels are
# "Business:"/"Cell:" and "Home:"/"Cell:" shipped no number at all. Since Adam's
# ruling of 2026-10-17 ("if the official government source uses personal phone
# numbers, we publish those") every labelled number ships, the first in `phone`
# and the rest in `phonesExtra`, in the page's order, each led by the page's own
# label ("cell 309-...", "work 309-...", "business 309-...", "home 309-..."); a
# plain "Phone:" adds no word. A number with no label is not read: the one
# measured follows the courthouse's street address, so it is the building's.
# "Fax:" is not a label this pattern reads.
LABELLED_PHONE_RE = re.compile(
    r"\b(Cell\s+Phone|Work\s+Phone|Home\s+Phone|Business\s+Phone|Mobile\s+Phone|"
    r"Phone|Cell|Mobile|Work|Business|Home)\s*:\s*"
    r"(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", re.I)
PHONE_LABELS = {"phone": None, "cell phone": "cell", "cell": "cell",
                "mobile phone": "mobile", "mobile": "mobile",
                "work phone": "work", "work": "work",
                "business phone": "business", "business": "business",
                "home phone": "home", "home": "home"}
# Numbers that belong to a county office, not to a member, whatever label a
# member page puts on them. A member page that lists one is naming the office.
COUNTY_LINES = {
    # Peoria County Administration, as the county's own directory lists it
    # (read 2026-10-17); one member page gives it as the member's "Business:".
    "309-672-6056",
}
TEL_HREF_RE = re.compile(r'href="tel:([^"]*)"', re.I)
ROLE_RE = re.compile(r"\b(Chairperson|Vice\s+Chairperson)\b")


def clean(s):
    return re.sub(r"\s+", " ", html_mod.unescape(s or "")).strip()


def strip_tags(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    return html_mod.unescape(re.sub(r"(?s)<[^>]+>", "\n", s))


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def labelled_numbers(text):
    """Every labelled number on a member page, in the page's order, as
    (label word or None, "309-555-0100"). The same number printed twice on one
    page is kept once, under its first label."""
    out, seen = [], set()
    for label, raw in LABELLED_PHONE_RE.findall(text):
        number = normalize_phone(raw)
        if not number or number in seen:
            continue
        seen.add(number)
        out.append((PHONE_LABELS[re.sub(r"\s+", " ", label.lower())], number))
    return out


def with_label(label, number):
    return "%s %s" % (label, number) if label else number


def cf_decode(hex_token):
    """An address Cloudflare's e-mail protection hid, decoded as the reader's
    browser decodes it: the first byte is a key XORed over the rest (the same
    encoding scripts/will_county_board_scraper.py decodes)."""
    b = bytes.fromhex(hex_token)
    return "".join(chr(c ^ b[0]) for c in b[1:])


def link_target(attrs):
    """The address an <a> sends to, or None when it is not an e-mail link."""
    m = CF_HREF_RE.search(attrs)
    if m:
        return cf_decode(m.group(1)).split("?", 1)[0].strip()
    m = MAILTO_HREF_RE.search(attrs)
    if m:
        return urllib.parse.unquote(m.group(1)).strip()
    return None


def shown_emails(markup):
    """-> (addresses, conflict). The e-mail addresses a member page shows a
    reader, in the page's order, lower-cased, each once. conflict is True when
    a link's visible text shows one address while the link sends to another.
    See the comment above CF_ELEMENT_RE."""
    page = re.sub(r"(?s)<!--.*?-->", " ", markup)
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    # Each protected printed address becomes the address itself, as the
    # browser shows it; a protected link keeps its tag and is read below.
    page = CF_ELEMENT_RE.sub(lambda m: " %s " % cf_decode(m.group(2)), page)
    found, conflict, last = [], False, 0

    def note(text):
        for address in ADDRESS_RE.findall(text):
            if address.lower() not in found:
                found.append(address.lower())

    for m in ANCHOR_RE.finditer(page):
        note(strip_tags(page[last:m.start()]))
        last = m.end()
        visible = clean(strip_tags(m.group(2)))
        target = link_target(m.group(1))
        if target is None:
            note(visible)
        elif not visible:
            continue  # an empty link shows a reader nothing
        elif any(a.lower() != target.lower() for a in ADDRESS_RE.findall(visible)):
            conflict = True
        else:
            note(target)
    note(strip_tags(page[last:]))
    return found, conflict


def own_email(district, emails, conflict, pages_showing,
              county_domains=COUNTY_MAIL_DOMAINS):
    """The one address a member's page shows as the member's, or None. See the
    comment above CF_ELEMENT_RE. Messages name the district, never an address."""
    if conflict:
        print("peoria-board-scraper: WARN — district %s's page has an e-mail link "
              "whose text shows one address while it sends to another; no "
              "e-mail ships for this member" % district, file=sys.stderr)
        return None
    own = [a for a in emails if pages_showing.get(a, 0) < 2]
    if len(own) < len(emails):
        print("peoria-board-scraper: note — district %s's page shows %d e-mail "
              "address(es) that another member's page shows too; not shipped as "
              "the member's own" % (district, len(emails) - len(own)),
              file=sys.stderr)
    if len(own) > 1:
        county = [a for a in own if a.rsplit("@", 1)[-1] in county_domains]
        if len(county) != 1:
            print("peoria-board-scraper: WARN — district %s's page shows %d "
                  "addresses of the member's own, %d of them on the county's "
                  "domain; none ships" % (district, len(own), len(county)),
                  file=sys.stderr)
            return None
        own = county
    return own[0] if own else None


def name_key(name):
    """Compare names across county surfaces without tripping on middle
    initials or punctuation ("James C. Dillon" vs "James Dillon")."""
    parts = [p for p in re.split(r"[^A-Za-z]+", (name or "").lower()) if len(p) > 1]
    return (parts[0], parts[-1]) if len(parts) >= 2 else tuple(parts)


def same_person(a, b):
    """Two name keys naming one person. The surfaces differ on diminutives —
    the GIS says "Robert Reneau" and "Matthew Windish" where the index page
    says "Rob" and "Matt" — so the surname must match exactly and the given
    names must agree as far as the shorter one runs. Deliberately strict on
    the surname: this cross-check exists to catch a member appearing on one
    county surface and not the other, and a loose match would hide that."""
    if not a or not b or a[-1] != b[-1]:
        return False
    return a[0].startswith(b[0]) or b[0].startswith(a[0])


def fetch_roster_layer(session):
    require_robots_once(ROSTER_LAYER, UA["User-Agent"], headers=UA,
                        label="il-peoria-county-board-scraper")
    r = session.get(ROSTER_LAYER, headers=UA, timeout=60, params={
        "where": "1=1", "returnGeometry": "false", "f": "json",
        "outFields": "DISTRICTID,REPNAME1,PARTY1,DISTRICTURL1",
    })
    r.raise_for_status()
    # HTTP 200 with an `error` member would otherwise read as an empty roster
    # and trip the "zero rows parsed (service change?)" guard below, which
    # names the wrong cause for what is often a rate limit that clears.
    payload = raise_for_arcgis_error(r.json(), "Peoria's roster layer")
    rows = []
    for feat in payload.get("features", []):
        a = feat.get("attributes", {})
        district = clean(str(a.get("DISTRICTID") or ""))
        name = clean(a.get("REPNAME1"))
        if not district or not name:
            continue
        party = clean(a.get("PARTY1"))
        rows.append({
            "district": district,
            "name": name,
            # the layer spells one member's party "Democrat" and the rest
            # "Democratic" — normalize the adjective, don't invent one
            "party": "Democratic" if party == "Democrat" else (party or None),
            "url": clean(a.get("DISTRICTURL1")) or None,
        })
    return rows


# THE INDEX'S MEMBER HEADINGS ARE NOT ONE SHAPE, and reading them as one lost
# both of the board's roles. Measured 2026-09-11 on a 110,624-byte fetch:
# FIFTEEN of the eighteen members sit under `h3.subhead2` (21 such blocks, six
# of them empty) and THREE — Dillon, Williams and Coates — under `h2.subhead1`,
# with BOTH role words inside that h2 group. This function matched the h3 shape
# alone, so it returned fifteen members and no roles at all, and the week's
# roster shipped with the Chairperson and Vice-Chairperson gone.
#
# The three h2 entries carry WYSIWYG artifacts — inline `style="box-sizing:
# inherit; …"` on their anchors, and an empty `<a class="subhead1 subhead2">`
# sibling — which reads as someone editing those three entries in the CMS and
# the heading level moving as a side effect. THAT CAN MOVE BACK, so both shapes
# are accepted rather than one swapped for the other.
#
# Two details the pattern depends on. The class is matched as a WORD inside the
# attribute rather than as the whole of it, because the same editing pass
# produced `class="  subhead1"` with a doubled space on at least one fetch.
# And the heading LEVEL is captured and back-referenced, so the anchor that
# carries `class="subhead1 subhead2"` inside an h2 cannot itself be read as a
# member heading.
INDEX_HEADING_RE = re.compile(
    r'(?is)<h([23])\b[^>]*class="[^"]*\bsubhead[12]\b[^"]*"[^>]*>(.*?)</h\1>')

# THE PAGE REFLOWED ON 2026-09-25 AND THE HEADINGS WENT AWAY ENTIRELY, which
# froze this roster: `subhead` occurs ZERO times on the served page now, so the
# pattern above matched nothing, the index named 0 of 18 members and the
# builder refused to write. The refusal was correct and nothing a reader sees
# moved; what broke is only the block selector.
#
# Measured the same day with this scraper's own client, robots.txt read first
# through robots_policy and allowed: HTTP 200, 109,010 bytes, every member name
# in the served HTML. So not a block, not a fetch failure, not client-rendered.
# The page is CivicPlus and each member is now a paragraph in a `fr-view`
# editor block:
#
#     <div class="fr-view">
#       <p><a href="…/615/James-C-Dillon"><strong>James C. Dillon,
#          Chairperson<br>District 5</strong></a></p><p><img …></p>
#     </div>
#
# EIGHTEEN fr-view blocks, EIGHTEEN anchor-bearing paragraphs, all 18 members
# and both roles, districts 1-18 complete.
#
# `aria-level` IS NOT THE LEADERSHIP MARKER, and it looks like one. Exactly one
# paragraph on the page carries `aria-level="2"` — Williams, the Vice
# Chairperson — and Dillon, the Chairperson, carries none, so anchoring on that
# attribute finds ONE member of eighteen. It is a WYSIWYG artifact of whoever
# last edited that entry, the same class of noise the inline `style=` and the
# empty `<a class="subhead1 subhead2">` were under the old shape.
#
# THE ANCHOR IS REQUIRED, and that is what keeps prose out. The name pattern
# downstream ends in `|$`, so it matches any run of letters and spaces — a
# paragraph reading "Board meetings are held monthly" would parse as a member
# named exactly that and enter `listed`, which is the set the builder's floor
# counts. A link to the member's own page is the page's own statement that the
# paragraph names a member, so it is what the selector asks for.
#
# BOTH SHAPES ARE READ, not one swapped for the other: the heading shape was
# itself a CMS artifact that moved once already, so it can move back.
INDEX_EDITOR_BLOCK_RE = re.compile(r'(?is)<div class="fr-view">(.*?)</div>')
INDEX_EDITOR_ENTRY_RE = re.compile(r"(?is)<p\b[^>]*>(.*?)</p>")
INDEX_ENTRY_ANCHOR_RE = re.compile(r"(?i)<a\s[^>]*href=")


def index_blocks(text):
    """Every HTML fragment on the index that may name one member.

    Returns raw fragments, flattened and matched by the caller: a fragment that
    is not a member simply fails the name pattern, which is how the six empty
    `subhead` blocks were already tolerated.
    """
    blocks = [block for _level, block in INDEX_HEADING_RE.findall(text)]
    for editor in INDEX_EDITOR_BLOCK_RE.findall(text):
        for para in INDEX_EDITOR_ENTRY_RE.findall(editor):
            if INDEX_ENTRY_ANCHOR_RE.search(para):
                blocks.append(para)
    return blocks


def fetch_index_roles(session):
    """Index page -> {name_key: role}, plus the set of names it lists. Roles
    are only ever read from here; a member the index does not mark gets none.

    A leadership heading puts the name and the role in DIFFERENT anchors either
    side of a `<br>`, so the whole heading is flattened before matching —
    strip_tags + clean turn `James C. Dillon,&nbsp;</a><br><a …>Chairperson<br>
    District 5` into `James C. Dillon, Chairperson District 5`."""
    require_robots_once(INDEX_URL, UA["User-Agent"], headers=UA,
                        label="il-peoria-county-board-scraper")
    r = session.get(INDEX_URL, headers=UA, timeout=60)
    r.raise_for_status()
    roles, listed = {}, set()
    for block in index_blocks(r.text):
        text = clean(strip_tags(block))
        m = re.match(r"([A-Za-z][A-Za-z.'\-\s]+?),?\s*(?:Chairperson|Vice\s+Chairperson|District\s+\d+|$)", text)
        if not m:
            continue
        key = name_key(m.group(1))
        if not key:
            continue
        listed.add(key)
        role = ROLE_RE.search(text)
        if role:
            roles[key] = re.sub(r"\s+", "-", role.group(1))
    return roles, listed


def fetch_member_contact(session, url):
    """-> ([e-mail addresses the page shows], conflict, [(label, number)],
    tel_ok). conflict is shown_emails'. tel_ok is False when a tel: link on the
    page dials a number the page does not show; then none of the page's
    numbers ship."""
    try:
        require_robots_once(url, UA["User-Agent"], headers=UA,
                            label="il-peoria-county-board-scraper")
        r = session.get(url, headers=UA, timeout=60)
        r.raise_for_status()
    except requests.RequestException:
        return [], False, [], True
    emails, conflict = shown_emails(r.text)
    text = strip_tags(r.text)
    numbers = labelled_numbers(text)
    shown = {re.sub(r"\D", "", n)
             for n in re.findall(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)}
    dialled = {re.sub(r"\D", "", h)[-10:] for h in TEL_HREF_RE.findall(r.text)}
    tel_ok = not (dialled - shown)
    return emails, conflict, numbers, tel_ok


def main():
    session = requests.Session()
    rows = fetch_roster_layer(session)
    # `index_read` is NOT `bool(listed)`, and the difference is the whole point
    # of the guard downstream: an index that was fetched and parsed to nothing
    # is a parser break, while an index that could not be fetched is a network
    # outage the roster should survive. Only the first is a refusal.
    index_read = True
    try:
        roles, listed = fetch_index_roles(session)
    except requests.RequestException as exc:
        print("peoria-board-scraper: WARN — index page unreadable (%s); "
              "no roles will be tagged" % exc, file=sys.stderr)
        roles, listed = {}, set()
        index_read = False

    contacts = {}
    for row in rows:
        contacts[row["district"]] = (fetch_member_contact(session, row["url"])
                                     if row["url"] else ([], False, [], True))
    # A number printed on two or more member pages, or one of COUNTY_LINES,
    # belongs to an office rather than to one member, so it ships on nobody;
    # so does an e-mail address shown on two or more member pages.
    pages_printing, pages_showing = {}, {}
    for emails, _conflict, numbers, _ok in contacts.values():
        for _label, number in numbers:
            pages_printing[number] = pages_printing.get(number, 0) + 1
        for address in emails:
            pages_showing[address] = pages_showing.get(address, 0) + 1

    records = []
    missing = []
    for row in rows:
        key = name_key(row["name"])
        emails, conflict, numbers, tel_ok = contacts[row["district"]]
        email = own_email(row["district"], emails, conflict, pages_showing)
        if not tel_ok:
            print("peoria-board-scraper: WARN — district %s's page has a tel: "
                  "link that dials a number the page does not show; none of its "
                  "numbers ship" % row["district"], file=sys.stderr)
            numbers = []
        own = [(label, number) for label, number in numbers
               if pages_printing.get(number, 0) < 2 and number not in COUNTY_LINES]
        if len(own) < len(numbers):
            print("peoria-board-scraper: note — district %s's page lists %d "
                  "office number(s) (a county line, or one printed on another "
                  "member's page too); not shipped as the member's own"
                  % (row["district"], len(numbers) - len(own)), file=sys.stderr)
        phone = with_label(*own[0]) if own else None
        extras = [with_label(label, number) for label, number in own[1:]]
        if index_read and not any(same_person(key, k) for k in listed):
            missing.append(row["name"])
            print("peoria-board-scraper: WARN — %s (district %s) is on the GIS "
                  "roster but not the County Board Members index"
                  % (row["name"], row["district"]), file=sys.stderr)
        records.append({
            "district": row["district"],
            "name": row["name"],
            "party": row["party"],
            "role": next((r for k, r in roles.items() if same_person(key, k)), None),
            "phone": phone,
            "phonesExtra": extras,
            "email": email,
            "url": row["url"],
        })

    if not records:
        print("peoria-board-scraper: FAIL — zero rows parsed (service change?)",
              file=sys.stderr)
        sys.exit(1)

    # The cross-check ships as DATA rather than as a line on stderr. It printed
    # the three missing names on 2026-09-11 and nothing read them; the builder
    # floors `matched` so the next narrowing stops the run instead.
    out = json.dumps({
        "source": INDEX_URL,
        "index": {
            "read": index_read,
            "rosterCount": len(rows),
            "matched": (len(rows) - len(missing)) if index_read else 0,
            "missing": missing,
        },
        "records": records,
    }, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("peoria-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


# --------------------------------------------------------------- selftest ---

# One fixture per shape this index has been MEASURED in, because the shape has
# now changed under us twice and each time the roster froze for a week with the
# page serving every name. This is the Edgar shape a second time: the page was
# fine and the parser was not.
EDITOR_SHAPE = """
<div class="widget editor pageStyles narrow"><div class="fr-view">
  <p><a href="https://www.peoriacounty.gov/615/James-C-Dillon"><strong>James C.
     Dillon, Chairperson<br>District 5</strong></a></p><p><img src="/x"></p>
</div></div>
<div class="widget editor pageStyles narrow"><div class="fr-view">
  <p aria-level="2"><a href="https://www.peoriacounty.gov/565/Sharon-K-Williams"><strong>Sharon
     K. Williams, Vice Chairperson<br>District 1</strong></a></p><p><img src="/y"></p>
</div></div>
<div class="widget editor pageStyles narrow"><div class="fr-view">
  <p><a href="https://www.peoriacounty.gov/635/Brian-Elsasser"><strong>Brian
     Elsasser<br>District 14</strong></a></p><p><img src="/z"></p>
</div></div>
"""

# The shape the page served until 2026-09-25, with the artifacts that were
# measured on it: the doubled space in the class, the inline style, and the
# empty anchor carrying BOTH class names inside the h2.
HEADING_SHAPE = """
<h2 class="  subhead1"><a style="box-sizing: inherit;"
   href="/615/James-C-Dillon">James C. Dillon,&nbsp;</a><br><a
   href="/615/James-C-Dillon">Chairperson<br>District 5</a>
   <a class="subhead1 subhead2"></a></h2>
<h3 class="subhead2"><a href="/635/Brian-Elsasser">Brian Elsasser<br>District 14</a></h3>
<h3 class="subhead2"></h3>
"""

# Prose inside an editor block, which the name pattern's trailing `|$` matches
# as a member named exactly that. The anchor requirement is the only thing
# keeping it out of `listed`, and `listed` is what the builder's floor counts.
PROSE_SHAPE = """
<div class="fr-view">
  <p>Board meetings are held monthly</p>
  <p>County Board Members</p>
</div>
"""


def read_blocks(text):
    """(names, roles) the index parser would take from this markup."""
    names, roles = [], {}
    for block in index_blocks(text):
        flat = clean(strip_tags(block))
        m = re.match(r"([A-Za-z][A-Za-z.'\-\s]+?),?\s*"
                     r"(?:Chairperson|Vice\s+Chairperson|District\s+\d+|$)", flat)
        if not m:
            continue
        key = name_key(m.group(1))
        if not key:
            continue
        names.append(key)
        role = ROLE_RE.search(flat)
        if role:
            roles[key] = re.sub(r"\s+", "-", role.group(1))
    return names, roles


def selftest():
    problems = checks = 0

    def want(label, got, expected):
        nonlocal problems, checks
        checks += 1
        if got != expected:
            problems += 1
            print("  FAIL %-34s expected %r\n%s got      %r"
                  % (label, expected, " " * 41, got))

    names, roles = read_blocks(EDITOR_SHAPE)
    # `name_key` returns a (first, last) tuple, not a slug — the keys below are
    # what it actually produces, checked rather than guessed at.
    want("editor shape names", names,
         [("james", "dillon"), ("sharon", "williams"), ("brian", "elsasser")])
    want("editor shape roles", roles,
         {("james", "dillon"): "Chairperson",
          ("sharon", "williams"): "Vice-Chairperson"})

    names, roles = read_blocks(HEADING_SHAPE)
    want("heading shape names", names, [("james", "dillon"), ("brian", "elsasser")])
    want("heading shape roles", roles, {("james", "dillon"): "Chairperson"})

    # Both at once: a page mid-reflow must not double-count or lose either.
    names, _roles = read_blocks(HEADING_SHAPE + EDITOR_SHAPE)
    want("both shapes on one page", sorted(set(names)),
         [("brian", "elsasser"), ("james", "dillon"), ("sharon", "williams")])

    names, roles = read_blocks(PROSE_SHAPE)
    want("prose names nobody", names, [])

    # The failure this fix is for: the live page with no `subhead` anywhere.
    want("heading shape alone finds nobody in the editor markup",
         [b for _l, b in INDEX_HEADING_RE.findall(EDITOR_SHAPE)], [])

    # The member pages' numbers (Adam's ruling of 2026-10-17): every labelled
    # number, in the page's order, under the page's own label; "Phone:" adds no
    # word; a number with no label, and a Fax, are not read; a number printed
    # twice on the page is kept once, under its first label.
    member_page = ("Room 101 309-555-0100 Cell Phone: 309-555-0101 "
                   "Work phone: (309) 555-0102 Fax: 309-555-0103 "
                   "Business: 309.555.0104 Home: 309-555-0105 "
                   "Phone: 309-555-0106 Cell: 309-555-0101")
    want("member page numbers", labelled_numbers(member_page),
         [("cell", "309-555-0101"), ("work", "309-555-0102"),
          ("business", "309-555-0104"), ("home", "309-555-0105"),
          (None, "309-555-0106")])
    want("a label leads its number", with_label("cell", "309-555-0101"),
         "cell 309-555-0101")
    want("a plain Phone: adds no word", with_label(None, "309-555-0106"),
         "309-555-0106")

    # The member pages' e-mail addresses behind Cloudflare's protection
    # (measured 2026-10-17; see the comment above CF_ELEMENT_RE). The fixture
    # addresses are made up, on example domains.
    def cf_encode(address, key=0x5a):
        return "%02x" % key + "".join("%02x" % (ord(c) ^ key) for c in address)

    mine, old = "j.doe@example.org", "former.member@example.org"
    want("cf_decode reverses the protection", cf_decode(cf_encode(mine, 0x3c)), mine)
    want("an 'Email <name>' link is read",
         shown_emails('<p><a href="/cdn-cgi/l/email-protection#%s">Email Jane '
                      'Doe</a></p>' % cf_encode(mine)),
         ([mine], False))
    # District 3's shape: a printed address, then an empty link to another.
    want("a printed address is read and an empty link is not",
         shown_emails('<p>Room 502<br><a href="/cdn-cgi/l/email-protection" '
                      'class="__cf_email__" data-cfemail="%s">[email&#160;'
                      'protected]</a></p><p><a href="/cdn-cgi/l/email-protection'
                      '#%s"></a></p>' % (cf_encode(mine), cf_encode(old))),
         ([mine], False))
    want("a mailto: link and a plain-text address are still read",
         shown_emails('<a href="mailto:J.Doe@Example.org">Email Jane Doe</a> '
                      'or %s' % old.upper()),
         ([mine, old], False))
    want("a link showing one address and sending to another conflicts",
         shown_emails('<a href="/cdn-cgi/l/email-protection#%s"><span class='
                      '"__cf_email__" data-cfemail="%s">[email&#160;protected]'
                      '</span></a>' % (cf_encode(old), cf_encode(mine))),
         ([], True))
    want("a link showing the address it sends to is read once",
         shown_emails('<a href="/cdn-cgi/l/email-protection#%s"><span class='
                      '"__cf_email__" data-cfemail="%s">[email&#160;protected]'
                      '</span></a>' % (cf_encode(mine), cf_encode(mine))),
         ([mine], False))
    want("an address in an HTML comment is not read",
         shown_emails('<!-- <a href="mailto:%s">Email</a> -->' % old), ([], False))

    quiet = io.StringIO()
    with contextlib.redirect_stderr(quiet):
        want("one address of the member's own ships",
             own_email("1", [mine], False, {mine: 1}), mine)
        want("an address on two members' pages ships on nobody",
             own_email("1", [mine], False, {mine: 2}), None)
        want("a conflict ships nothing", own_email("1", [mine], True, {mine: 1}), None)
        county = "j.doe@example.gov"
        want("of several, the one on the county's domain ships",
             own_email("1", [mine, county], False, {mine: 1, county: 1},
                       county_domains=("example.gov",)), county)
        want("of several, none on the county's domain, none ships",
             own_email("1", [mine, old], False, {mine: 1, old: 1},
                       county_domains=("example.gov",)), None)
    want("those messages name the district and never an address",
         "@" in quiet.getvalue(), False)

    print("peoria-board-scraper selftest: %s — %d check(s)%s"
          % ("FAIL" if problems else "OK", checks,
             ", %d problem(s)" % problems if problems else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    main()
