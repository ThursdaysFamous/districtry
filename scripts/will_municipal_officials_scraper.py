#!/usr/bin/env python3
"""
Will County Municipal Officials Scraper (County Clerk's Will County Directory)
=============================================================================
Extracts every municipality's governing body — village president / mayor,
trustees, ward alderpersons and district councilmembers, plus the clerk and
treasurer — from the Will County Clerk's own annual "Will County Directory".

Why this source: the Clerk publishes the directory as a FlipHTML5 flipbook
linked from willcountyclerk.gov, and it is the county's canonical record of
who holds each local office (fed by the Clerk's Entity Change of Information
process). It covers every municipality that touches Will — including the
cross-county ones (Aurora, Naperville, Tinley Park, Park Forest, Lemont,
Oswego, Minooka) — with the FULL governing body, not just the mayor. The
Clerk's own "elected officials lookup" widget is a third-party JS app with no
scrapable payload, so the directory is the route.

The flipbook exposes a plain-HTML rendition at /basic (and /basic/51-100,
…/251-257) whose `<p class='basic-text'>` blocks carry each page's extracted
PDF text. Section 5, "Municipal Government Officials", holds the entries.
Emails there are Cloudflare-obfuscated (`data-cfemail`) and decoded with the
standard XOR scheme, the same as il_county_clerk_scraper.py.

The book id is NOT hardcoded: it is discovered from the Clerk's own page, so
a new edition published under a new id is followed rather than missed.

Parsing notes (the source is PDF-extracted text, so the shapes vary):
- Office labels can run straight into the name ("Term ExpiresMichael W. Glotz").
- Every board member ends with a 4-digit term-expiry year, which is what
  anchors the member scan.
- Ward/district seats appear as "Ward 3 - Name (PARTY) 2027", sometimes twice
  per ward for staggered terms (Crest Hill), and district cities interleave
  per-seat "Precincts: …" lists (Joliet) which are stripped.
- Clerk/Treasurer are often "(Appointed Position)" — recorded as appointed so
  the card never presents them as elected — and a municipality may list no
  person at all ("Contact Entity for Information"), which yields no record.
- The trailing "Attorney" block is appointed counsel, not an elected officer,
  and is cut before member parsing.

This is the build-time half of the usual two-stage roster pattern; the raw
output is resolved into data/app/municipal-officials.json by
scripts/build_municipal_officials_roster.py.

Usage:
    python3 will_municipal_officials_scraper.py --out will_municipal_officials.json

Notes on data honesty (per project conventions):
- Fields that can't be parsed are stored as null, never guessed.
- Every record includes `source_url` and `scraped_at` for traceability.
- Contact fields are MUNICIPALITY-level (the directory prints one hall
  address/phone/email per entry), so they are emitted per municipality and
  never as a person's own contact.
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    UA_CHROME_WIN_124, fetch as fetch_with_retry, require_robots_once,
)

CLERK_PAGE = "https://www.willcountyclerk.gov/local-election-officials/"
FLIPBOOK_HOST = "https://fliphtml5.com"
HEADERS = {
    "User-Agent": UA_CHROME_WIN_124,
}
REQUEST_TIMEOUT = 60

# The directory runs ~257 pages; these ranges are the flipbook's own chunking.
PAGE_RANGES = ["", "/51-100", "/101-150", "/151-200", "/201-250", "/251-257"]

HEAD_OFFICES = ("Mayor", "President")
# Board-section headers, longest first so "Councilmembers" wins over "Council".
BOARD_HEADERS = ("Councilmembers", "Councilmember", "Commissioners",
                 "Alderpersons", "Alderperson", "Aldermen", "Trustees", "Trustee")
BOARD_OFFICE_BY_HEADER = {
    "Councilmembers": "Council Member", "Councilmember": "Council Member",
    "Commissioners": "Commissioner",
    "Alderpersons": "Alderperson", "Alderperson": "Alderperson",
    "Aldermen": "Alderperson",
    "Trustees": "Trustee", "Trustee": "Trustee",
}

# Deliberate under-tolerances against the verified 2026-07 live values
# (34 municipal entries, 34 heads of government, 208 board members).
MIN_ENTRIES = 30
MIN_HEADS = 30
MIN_BOARD_MEMBERS = 180

# ---------------------------------------------------------------------------
# CRETE — the entry the text layer mangles worst, recovered rather than lost.
#
# The directory COVERS the Village of Crete (its own table of contents lists
# it, section 5.13), but PDF-text extraction into the /basic layer loses the
# entry's whole head: the "VILLAGE OF CRETE" header, the hall address/phone,
# the President line, and the Clerk's name — the same defect class the
# docstring records for Lockport and Wilmington. What SURVIVES, verbatim and
# machine-readable, is the entry's tail: the clerk note's ending ("...Will
# need to run in 2027 as an unexpired 2-year term"), "Treasurer (Appointed
# Position)Gary Paape", the six trustees with (IND) parties and years, and
# "Attorney Spesia & Taylor". Because the header is gone, split_entries never
# creates a Crete part — the orphan rides the tail of the PRECEDING entry
# (Coal City), where that entry's own Attorney cut silently discards it. So
# Crete shipped nothing at all until 2026-08-19, and nothing said so.
#
# recover_crete() below parses that surviving tail. The two facts the text
# layer cannot supply come from other publications of record, each named:
#
# PRESIDENT — from the county's own CERTIFIED RESULTS, not from any directory:
# Will County Clerk, Consolidated Election April 1, 2025, Official Results
# (310/310 precincts, run 04/16/2025): "VILLAGE OF CRETE For President" —
# Mark S. Wiater (IND), 720 votes, unopposed. Canvass Book:
# https://assets01.aws.connect.clarityelections.com/Assets/Connect/RootPublish/
# will-il.connect.clarityelections.com/Elections/2025ConsolidatedElection/CanvassBook.pdf
# (pp. 11 cumulative / 45 canvass). A four-year term -> expires 2029. This row
# is named by the election that seated him (the Clark posture); the weekly run
# prints a NOT RE-READ line naming this document and its age.
#
# CLERK — DELIBERATELY ABSENT, and the reasons are measured: the same
# certified 2025 contest, "VILLAGE OF CRETE For Clerk", reads "No Candidate"
# with 0 votes cast, so the office was filled by appointment afterward; the
# directory names the appointee only in the text the extraction lost; and the
# village's own site (villageofcrete.org) serves an SG-captcha challenge to
# every automated client, so it cannot be read from here. The surviving
# fragment "Will need to run in 2027 as an unexpired 2-year term" is the tail
# of that clerk note. Shipping no clerk beats guessing one.
#
# WEBSITE + HALL EMAIL — the directory itself publishes both, as clickable
# link annotations on Crete's page (the flipbook's config layer, annotype
# TAnnoLink: http://villageofcrete.org and mailto:ktellef@villageofcrete.org,
# read 2026-08-19). The annotations survive precisely where the text did not.
# Hall street address and phone did not survive anywhere -> shipped as null.
CRETE_JURISDICTION = "Village of Crete"
CRETE_PRESIDENT = {
    "office": "President", "district": None, "name": "Mark S. Wiater",
    "party": "IND", "term_expires": "2029", "appointed": False,
}
CRETE_PRESIDENT_PROVENANCE = (
    "Will County certified Official Results, Consolidated Election 2025-04-01 "
    "(Canvass Book run 2025-04-16): unopposed, 720 votes")
CRETE_PRESIDENT_CERTIFIED = "2025-04-16"
CRETE_WEBSITE = "villageofcrete.org"
CRETE_EMAIL = "ktellef@villageofcrete.org"
# The orphan carries exactly these six today; one short is a vacancy, fewer
# means the extraction changed shape again and a human should look.
MIN_CRETE_TRUSTEES = 4


def decode_cfemail(enc):
    """Cloudflare email obfuscation: hex string, first byte is the XOR key."""
    try:
        key = int(enc[:2], 16)
        return "".join(chr(int(enc[i:i + 2], 16) ^ key) for i in range(2, len(enc), 2))
    except (ValueError, IndexError):
        return None


def clean(value):
    if value is None:
        return None
    text = " ".join(str(value).replace(" ", " ").split())
    return text or None


def fetch(url):
    # scraper_common.fetch retries 429/5xx (numeric Retry-After honoured,
    # capped) and refuses to retry 401/403/404 — the Henry rule. Parsing and
    # every page check stay in this file.
    #
    # THE TWO HOSTS THIS SCRIPT READS ARE THE CLERK'S OWN SITE AND THE FLIPBOOK
    # THE CLERK PUBLISHES THE DIRECTORY ON, and both publish a policy that
    # permits the paths read here (124 and 9,778 bytes, no matching rule,
    # measured from a runner 2026-09-30). The Clarity and village addresses in
    # the comments below are citations rather than fetches, so neither is asked.
    #
    # READ WITH THE CLIENT THAT CRAWLS: HEADERS is what the fetch sends, so it
    # is what the policy is read with. This file sends the pinned Chrome
    # User-Agent without Chrome's client-hint headers, and the recorded reading
    # was taken with the hints as well; the read here is the file's own client
    # either way, and the record is corroboration rather than the answer.
    require_robots_once(url, HEADERS["User-Agent"], headers=dict(HEADERS),
                        label="will-municipal-officials")
    return fetch_with_retry(url, HEADERS, timeout=REQUEST_TIMEOUT).text


def discover_flipbook(page_html):
    """Find the directory flipbook's id from the Clerk's own page."""
    match = re.search(r"(?:online\.)?fliphtml5\.com/([A-Za-z0-9]+)/([A-Za-z0-9]+)", page_html)
    if not match:
        print("FATAL: no FlipHTML5 directory link on %s — page structure changed"
              % CLERK_PAGE, file=sys.stderr)
        sys.exit(1)
    return match.group(1), match.group(2)


def page_texts(book_owner, book_id):
    """Every directory page's extracted text, in order."""
    pages = []
    for rng in PAGE_RANGES:
        url = "%s/%s/%s/basic%s" % (FLIPBOOK_HOST, book_owner, book_id, rng)
        markup = fetch(url)
        # Decode obfuscated emails in place so they survive tag stripping.
        markup = re.sub(
            r'<a[^>]*data-cfemail="([0-9a-f]+)"[^>]*>.*?</a>',
            lambda m: decode_cfemail(m.group(1)) or "",
            markup, flags=re.S)
        blocks = re.findall(r"<p class='basic-text'>(.*?)</p>", markup, re.S)
        if not blocks:
            print("FATAL: no page text blocks at %s — flipbook layout changed" % url,
                  file=sys.stderr)
            sys.exit(1)
        for block in blocks:
            text = re.sub(r"<[^>]+>", " ", block)
            pages.append(clean(html.unescape(text)) or "")
    return pages


def municipal_section(pages):
    """The run of pages holding Section 5, Municipal Government Officials."""
    start = None
    for i, text in enumerate(pages):
        if start is None and re.search(r"CITY OFFICIALS|VILLAGE OFFICIALS", text):
            start = i
        elif start is not None and re.search(r"TOWNSHIP OFFICIALS", text):
            return " ".join(pages[start:i])
    if start is None:
        print("FATAL: no municipal-officials section found — directory layout changed",
              file=sys.stderr)
        sys.exit(1)
    return " ".join(pages[start:])


def split_entries(section):
    parts = re.split(r"(?=(?:CITY|VILLAGE|TOWN) OF [A-Z])", section)
    return [p for p in parts if re.match(r"(CITY|VILLAGE|TOWN) OF [A-Z]", p)]


def strip_precincts(text):
    """Drop the interleaved per-seat precinct lists.

    The lookahead must name every marker that can follow a precinct list —
    including the head/officer labels, since the entry's first precinct list
    is followed by the hall contact block and then "Mayor"/"President".
    """
    return re.sub(
        r"Precincts?:.*?(?=(?:Ward|District)\s+\d+\s*-|"
        r"Attorney\b|Trustees?\b|Councilmembers?\b|Alderpersons?\b|Aldermen\b|"
        r"Commissioners?\b|Mayor\b|President\b|Clerk\b|Treasurer\b|$)",
        " ", text, flags=re.S)


def parse_header(entry):
    """-> (jurisdiction, address, phone, email, website)."""
    name_match = re.match(r"((?:CITY|VILLAGE|TOWN) OF [A-Z][A-Za-z\.\'’\- ]*?)\s*\(", entry)
    if not name_match:
        return None, None, None, None, None
    raw = clean(name_match.group(1))
    # "CITY OF CREST HILL" -> "City of Crest Hill" (the builder's GEOID join
    # normalizes anyway; this is what the card prints).
    kind, _, rest = raw.partition(" OF ")
    jurisdiction = "%s of %s" % (kind.capitalize(), rest.title())

    website = None
    site = re.search(r"Website:\s*([A-Za-z0-9\.\-/]+)", entry)
    if site:
        website = clean(site.group(1))

    email = None
    mail = re.search(r"Email:\s*([^\s]+@[^\s]+)", entry)
    if mail:
        email = trim_glued_email(clean(mail.group(1)))  # "Contact Us link on website" is not an email

    phone = None
    tel = re.search(r"\((\d{3})\)\s*(\d{3})-(\d{4})", entry)
    if tel:
        phone = "%s-%s-%s" % tel.groups()

    return jurisdiction, parse_address(entry), phone, email, website


def parse_address(entry):
    """The hall address, or None when the flattened text can't delimit it.

    The PDF's line breaks are lost in this rendition, so a preceding precinct
    list runs straight into the street number. Where the join carries a
    separator the split is unambiguous — "…3P625 Dixie Highway" (the precinct
    token's trailing P), "…35P 44 E. Downer Pl." (whitespace), "(Will
    County)20600 City Center Blvd." (no precincts at all). Where the last
    precinct token is a BARE number the two run together with nothing between
    them ("…18P & 19150 W. Jefferson St." is precinct 19 + 150 W. Jefferson),
    and the street number cannot be recovered from the text. Those return
    None: the card drops the address line rather than print a guessed one.
    """
    anchor = re.search(r"(\d{5})\s*\(\d{3}\)\s*\d{3}-\d{4}", entry)
    if not anchor:
        return None
    head = entry[:anchor.start(1)]
    zipcode = anchor.group(1)

    # Walk candidate street starts left-to-right; the first one that reaches
    # the ZIP is the address (a later start would truncate the street).
    for m in re.finditer(r"\d", head):
        start = m.start()
        candidate = head[start:]
        if not re.match(r"\d{1,6}\s+[A-Z0-9]", candidate):
            continue
        if not re.search(r",\s*[A-Za-z\.\'’\- ]+\s*$", candidate):
            continue  # must end "…, City " right before the ZIP
        before = head[start - 1] if start else ")"
        if before.isdigit():
            return None  # glued to a bare precinct number — undelimitable
        if before.isspace():
            prev = head[:start].rstrip()
            # A preceding bare precinct number means the same ambiguity, one
            # space over ("& 19150"): only a P-suffixed or non-numeric token
            # proves the precinct list actually ended.
            if prev and prev[-1].isdigit():
                return None
        return clean(candidate.rstrip().rstrip(",") + " " + zipcode)
    return None


# A personal name as the directory prints it. Three shapes the flattened text
# forces us to absorb: an inline parenthetical nickname ("Teresa (Terry) A.
# Kernc"), curly-quoted nicknames ("Sharon “Sherri” Reardon"), and a
# comma-separated generational suffix ("Joseph E. Roudez, III").
#
# A NICKNAME IS TOLD FROM A PARTY CODE BY WHAT FOLLOWS IT, NOT BY CASE. The old
# test was "ALL-CAPS means party", and it cost Coal City's trustee his first
# name: the directory prints "Chris (CJ) Lauterbur", "(CJ)" was read as a party
# code, and the card got the bare surname "Lauterbur" — corroborated as wrong by
# Grundy's own directory, which prints the same man (Coal City straddles the two
# counties) as "Chris (CJ) Lauterbur".
#
# Case cannot do this job: a party code and an initials nickname are the same
# shape. Position can. A parenthetical is part of the NAME only when more name
# follows it; a party code is followed by the term year or by the appointment
# note, never by another name word. Hence the lookahead: absorb the
# parenthetical only if a capitalised word that is not "Appt" comes next.
#
#   "Teresa (Terry) A. Kernc 2029"        -> "(Terry)" then " A."   -> nickname
#   "Chris (CJ) Lauterbur 2029"           -> "(CJ)"    then " Laut." -> nickname
#   "Joe Smith (IND) 2029"                -> "(IND)"   then " 2029"  -> party
#   "James Hanus (ACT) - Appt. 6/2025..." -> "(ACT)"   then " - App" -> party
#
# The party vocabulary is deliberately NOT hardcoded as the alternative: this
# directory already prints fourteen distinct codes (IND, FPB, POL, LP, OPA, POP,
# D, ROM, RF, ACT, BTS, TFP, OTP), local parties invent more every cycle, and a
# list would rot silently.
_CH = r"[A-Za-z\.\'‘’“”\-À-ɏ]"
NAME_RE = (r"[A-Z]" + _CH + r"*"
           r"(?:\s*\([A-Za-z\.\'‘’“”\- ]+\)(?=\s+(?!Appt)[A-Z]))?"
           r"(?:\s+" + _CH + r"+){0,4}?"
           r"(?:,\s*(?:Jr|Sr|II|III|IV|V)\.?)?")
# Party codes are all-caps abbreviations (IND, OTP, DEM, D, R).
PARTY_RE = r"[A-Z]{1,6}"

# NAME_RE's trailing words are LAZY, which is right where a term-expiry year
# follows and forces them to expand. A clerk/treasurer line has no such anchor
# ("Clerk (Appointed Position)Laura Warren Email: …"), so the lazy form would
# stop at the first word and ship "Laura". This greedy variant takes the
# surname too, refusing to cross into the next label.
_LABELS = (r"Email|Website|Term|Expires|Precincts?|Attorney|Trustees?|"
           r"Alderpersons?|Aldermen|Councilmembers?|Commissioners?|"
           r"Clerk|Treasurer|Mayor|President|Appointed|Contact")
OFFICER_NAME_RE = (r"[A-Z]" + _CH + r"*"
                   r"(?:\s*\((?![A-Z]{1,6}\))[A-Za-z\.\'‘’“”\- ]+\))?"
                   r"(?:\s+(?!(?:" + _LABELS + r")\b)" + _CH + r"+){0,4}"
                   r"(?:,\s*(?:Jr|Sr|II|III|IV|V)\.?)?")

# The label guard above only inspects word STARTS, but the flattened text also
# glues a label onto the END of a name with no space ("Andrea LambergTrustees
# Jennifer Hughes" — the Treasurer's surname running straight into the Trustees
# section header). Cutting at a lowercase->Label boundary recovers the real
# name; without it the treasurer shipped carrying the next section's first
# board member.
_GLUED_LABEL_RE = re.compile(r"(?<=[a-z])(?=(?:" + _LABELS + r")\b)")


# The same glue on an ADDRESS instead of a name: the flattened directory runs
# the next label straight onto the domain ("cityclerk@joliet.govTreasurer",
# "fred.hayes@villageofelwood.comTrusteesDarryl"), which shipped as a dead
# mailto. Cut at the TLD when what follows starts a new capitalized label.
_GLUED_EMAIL_RE = re.compile(
    r"^([\w.\-+]+@[\w\-]+(?:\.[\w\-]+)*?\.(?:gov|com|org|net|us|edu))(?=[A-Z]|$)")


def trim_glued_email(address):
    if not address:
        return address
    match = _GLUED_EMAIL_RE.match(address)
    return match.group(1) if match else address


def trim_glued_label(name):
    if not name:
        return name
    return _GLUED_LABEL_RE.split(name, maxsplit=1)[0].strip()

PERSON = re.compile(
    r"(?:(?P<kind>Ward|District)\s+(?P<num>\d+)\s*-\s*)?"
    r"(?:(?P<atlarge>At\s+Large)\s+)?"
    r"(?P<name>" + NAME_RE + r")"
    # "- Appt. 5/2025" after a name is a note about HOW the seat was filled,
    # not part of what the person is called, so it never reaches the card. The
    # DATE IS OPTIONAL because Coal City prints the bare "Kayla Melvin - Appt."
    # — with the date required, that trailing "- Appt." fell inside NAME_RE and
    # shipped as her name.
    # THE PARTY CODE AND THE APPOINTMENT NOTE COME IN EITHER ORDER, so both
    # slots are offered on both sides. Steger prints "James Hanus (ACT) -
    # Appt. 6/2025 2027" — party first — and with only the trailing slot the
    # whole run failed to match and HE WAS DROPPED: a sitting trustee absent
    # from the roster, not merely mis-spelled. Every other village prints the
    # note first, which is why one ordering had gone unnoticed.
    r"(?:\s*\((?P<party_lead>" + PARTY_RE + r")\))?"
    r"(?P<appt>\s*-\s*Appt\.?(?:[^0-9]*\d{1,2}/\d{4})?)?"
    r"\s*(?:\((?P<party>" + PARTY_RE + r")\))?"
    r"\s*(?P<year>20\d{2})")


def parse_members(text, office):
    """Every '<name> [(PARTY)] <year>' run in a board section.

    "At Large" labels a GROUP of seats, not one ("Councilmembers At Large Joe
    Clement 2029 Juan Moreno 2029 Jan Quillman 2029"), so it stays in force
    until a Ward/District seat appears. A body with no at-large label never
    sets it, so ordinary village trustees keep district=None.
    """
    members = []
    at_large = False
    for m in PERSON.finditer(text):
        name = clean(m.group("name"))
        if not name or len(name) < 3:
            continue
        # Guard against label fragments the office headers leave behind.
        if re.fullmatch(r"(?:Term Expires|Expires|At Large|Trustees?|Alderpersons?|"
                        r"Councilmembers?|Commissioners?|Precincts?|Attorney|Email|Website)",
                        name, flags=re.I):
            continue
        district = None
        if m.group("kind"):
            at_large = False
            district = "%s %s" % (m.group("kind").capitalize(), m.group("num"))
        else:
            if m.group("atlarge"):
                at_large = True
            if at_large:
                district = "At Large"
        members.append({
            "office": office,
            "district": district,
            "name": name,
            # Either slot may hold it — see PERSON. Only one can ever fire,
            # because a run carries one party code.
            "party": clean(m.group("party") or m.group("party_lead")),
            "term_expires": clean(m.group("year")),
            # The directory's "- Appt. M/YYYY" says the seat was filled by
            # appointment; the flag carries that, so the card never implies an
            # election that did not happen (the Grundy rule, same words).
            "appointed": bool(m.group("appt")),
        })
    return members


def parse_officer(entry, label):
    """Clerk / Treasurer — elected or explicitly '(Appointed Position)'."""
    m = re.search(label + r"\s*(?P<appt>\(Appointed Position\))?\s*"
                  r"(?P<name>" + OFFICER_NAME_RE + r")", entry)
    if not m:
        return None
    name = trim_glued_label(clean(m.group("name")))
    if not name:
        return None
    # The directory prints this where an office has no named holder.
    if re.match(r"Contact Entity", name, flags=re.I):
        return None
    # "Kayla Melvin - Appt." (Coal City's clerk): the same appointment note the
    # board path strips, on a clerk/treasurer row instead. OFFICER_NAME_RE has
    # no place to put it, so it had been shipping INSIDE her name. It is a fact
    # about the seat, not the person — the flag carries it, the card does not.
    appt_suffix = re.search(r"\s*-\s*Appt\.?(?:[^0-9]*\d{1,2}/\d{4})?\s*$", name, re.I)
    appointed_by_suffix = False
    if appt_suffix and name[:appt_suffix.start()].strip():
        name = name[:appt_suffix.start()].strip()
        appointed_by_suffix = True
    party = re.search(re.escape(name) + r"\s*\((" + PARTY_RE + r")\)", entry)
    year = re.search(re.escape(name) + r"[^0-9]{0,20}(20\d{2})", entry)
    return {
        "office": label,
        "district": None,
        "name": name,
        "party": clean(party.group(1)) if party else None,
        "term_expires": clean(year.group(1)) if year else None,
        "appointed": bool(m.group("appt")) or appointed_by_suffix,
    }


def parse_entry(entry):
    jurisdiction, address, phone, email, website = parse_header(entry)
    if not jurisdiction:
        return None, []
    body = strip_precincts(entry)
    # Appointed counsel and the party legend trail every entry.
    body = re.split(r"\bAttorney\b", body)[0]

    people = []
    head = re.search(r"(Mayor|President)\s*(?:Term\s*Expires)?\s*"
                     r"(?P<name>" + NAME_RE + r")"
                     r"\s*(?:\((?P<party>" + PARTY_RE + r")\))?\s*(?P<year>20\d{2})", body)
    if head:
        people.append({
            "office": head.group(1), "district": None, "name": clean(head.group("name")),
            "party": clean(head.group("party")), "term_expires": clean(head.group("year")),
            "appointed": False,
        })
    for label in ("Clerk", "Treasurer"):
        officer = parse_officer(body, label)
        if officer:
            people.append(officer)

    # Board section: from its header to the end of the (attorney-trimmed) entry.
    for header in BOARD_HEADERS:
        # No \b anchors: the flattened text glues labels to their neighbours
        # ("Stacey PetersonAlderperson Ward 1", "AlderpersonWard 1"), so a
        # bounded match would skip the real section header. BOARD_HEADERS is
        # ordered longest-first, which keeps the plain substring unambiguous.
        m = re.search(re.escape(header), body)
        if not m:
            continue
        tail = body[m.end():]
        for label in BOARD_HEADERS:
            tail = tail.replace(label, " ")
        # Names already claimed by the head/clerk/treasurer scan must not repeat.
        claimed = {p["name"] for p in people if p["name"]}
        for member in parse_members(tail, BOARD_OFFICE_BY_HEADER[header]):
            if member["name"] in claimed:
                continue
            people.append(member)
        break

    for person in people:
        person["jurisdiction"] = jurisdiction
        person["office_address"] = address
        person["office_city"] = None
        person["office_state"] = None
        person["office_zip"] = None
        person["office_phone"] = phone
        person["office_email"] = email
        person["website"] = website
    return jurisdiction, people


def recover_crete(entries, parsed_jurisdictions):
    """The Village of Crete, from the orphaned tail its lost header strands.

    Returns (records, note) — records empty when there is nothing to do.
    Self-disabling: if a future edition's text layer carries the "VILLAGE OF
    CRETE" header again, the normal path parses the entry and this recovery
    stands down rather than double-shipping. See the CRETE_* block above for
    why each recovered fact is trustworthy and which two are not recoverable.
    """
    if CRETE_JURISDICTION in parsed_jurisdictions:
        return [], ("crete: the directory's text layer carries the entry header "
                    "again — parsed normally; the orphan recovery stood down. "
                    "If this persists, retire recover_crete() and its constants.")

    # The orphan rides whichever entry precedes Crete alphabetically in the
    # book. Anchor on its CONTENT, not on that neighbour's name: the host part
    # is the one whose text AFTER its own Attorney block still contains a
    # second full member block ending in another Attorney line — the shape a
    # swallowed entry leaves and nothing else does.
    for entry in entries:
        segments = re.split(r"\bAttorney\b", entry)
        if len(segments) < 3:
            continue
        orphan = segments[1]
        if "Trustees" not in orphan or "(Appointed Position)" not in orphan:
            continue
        host_people = parse_entry(entry)[1]
        host_names = {p["name"] for p in host_people}
        tail = orphan.split("Trustees", 1)[1]
        trustees = parse_members(tail, "Trustee")
        # A trustee already claimed by the host entry means this is not the
        # orphan shape but a parsing accident — refuse loudly, ship nothing.
        overlap = [t["name"] for t in trustees if t["name"] in host_names]
        if overlap:
            print("FATAL: crete recovery matched a block sharing members with "
                  "its host entry (%s) — refusing to guess whose they are"
                  % ", ".join(overlap), file=sys.stderr)
            sys.exit(1)
        if len(trustees) < MIN_CRETE_TRUSTEES:
            continue
        records = [dict(CRETE_PRESIDENT)]
        treasurer = parse_officer(orphan, "Treasurer")
        if treasurer:
            records.append(treasurer)
        records.extend(trustees)
        for person in records:
            person["jurisdiction"] = CRETE_JURISDICTION
            person["office_address"] = None
            person["office_city"] = None
            person["office_state"] = None
            person["office_zip"] = None
            person["office_phone"] = None
            person["office_email"] = CRETE_EMAIL
            person["website"] = CRETE_WEBSITE
        note = ("crete: recovered %d trustees + %s from the orphaned block; "
                "president NOT RE-READ — %s, certified %s; clerk deliberately "
                "absent (2025 contest: No Candidate; appointee's name lost with "
                "the header; villageofcrete.org is captcha-gated)"
                % (len(trustees),
                   "treasurer" if treasurer else "no treasurer",
                   CRETE_PRESIDENT_PROVENANCE, CRETE_PRESIDENT_CERTIFIED))
        return records, note

    return [], None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default="will_municipal_officials.json")
    args = parser.parse_args()

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    owner, book = discover_flipbook(fetch(CLERK_PAGE))
    directory_url = "%s/%s/%s/" % (FLIPBOOK_HOST, owner, book)
    section = municipal_section(page_texts(owner, book))

    entries = split_entries(section)
    if len(entries) < MIN_ENTRIES:
        print("FATAL: only %d municipal entries parsed (expected >= %d) — layout changed"
              % (len(entries), MIN_ENTRIES), file=sys.stderr)
        sys.exit(1)

    municipalities = []
    officials = []
    for entry in entries:
        jurisdiction, people = parse_entry(entry)
        if not jurisdiction:
            continue
        municipalities.append({
            "name": jurisdiction,
            "source_url": directory_url,
            "scraped_at": scraped_at,
        })
        for person in people:
            person["source_url"] = directory_url
            person["scraped_at"] = scraped_at
            officials.append(person)

    # Crete: the one entry whose header the text layer loses (see CRETE_*).
    crete_records, crete_note = recover_crete(entries, {m["name"] for m in municipalities})
    if crete_note:
        print(crete_note, file=sys.stderr)
    if crete_records:
        municipalities.append({
            "name": CRETE_JURISDICTION,
            "source_url": directory_url,
            "scraped_at": scraped_at,
        })
        for person in crete_records:
            person["source_url"] = directory_url
            person["scraped_at"] = scraped_at
            officials.append(person)
    # THE ABSENCE GUARD (the Sangamon lesson: a lost key renders as a broken
    # card, and every floor can pass while it happens). The directory's own
    # table of contents lists Crete, so a run where NEITHER path produced it
    # means the recovery broke, not that the village left the county — fail
    # loudly rather than shipping a roster quietly one municipality short.
    if not any(m["name"] == CRETE_JURISDICTION for m in municipalities):
        print("FATAL: no path yielded the Village of Crete — the directory "
              "covers it (ToC section 5.13), so its absence is a parse break; "
              "the shipped roster should stand", file=sys.stderr)
        sys.exit(1)

    heads = sum(1 for p in officials if p["office"] in HEAD_OFFICES)
    board = sum(1 for p in officials
                if p["office"] in set(BOARD_OFFICE_BY_HEADER.values()))
    if heads < MIN_HEADS:
        print("FATAL: only %d heads of government parsed (expected >= %d)"
              % (heads, MIN_HEADS), file=sys.stderr)
        sys.exit(1)
    if board < MIN_BOARD_MEMBERS:
        print("FATAL: only %d board members parsed (expected >= %d)"
              % (board, MIN_BOARD_MEMBERS), file=sys.stderr)
        sys.exit(1)

    payload = {
        "county": "Will",
        "directory_url": directory_url,
        "scraped_at": scraped_at,
        "municipalities": municipalities,
        "officials": officials,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    seats = sum(1 for p in officials if p["district"])
    print("scraped %d municipalities, %d officials (%d heads, %d board members, "
          "%d ward/district seats) -> %s"
          % (len(municipalities), len(officials), heads, board, seats, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
