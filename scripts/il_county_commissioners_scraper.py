#!/usr/bin/env python3
"""
Scrape the boards of Illinois counties that elect them AT LARGE.

Stage 1 of the two-stage pipeline (scripts/build_county_commissioners.py is
stage 2). Seventeen Illinois counties run the COMMISSION form — three
commissioners elected countywide, no districts at all — and some township
counties likewise elect their board at large. Those boards have no geometry
to join, so they do not become `county-board` dispatch entries; their members
ride the COUNTY card instead (docs/EXPANSION_GUIDE.md §1.5), and this file is
that card's roster.

One shared file, keyed by county name normalized exactly the way
data/app/il-county-clerks.json is keyed, so the county card performs one
lookup shape for both. Adding a county here is a SITES entry plus a parser —
no new layer, no new toggle, no new fetch in the app.

Each county's block is deliberately explicit about what its source publishes
and what it does not. Where a county names only a shared office line, that is
what ships: a shared switchboard is honest, an invented per-member number is
not.

FETCH POSTURE: open. Plain server-rendered HTML; browser User-Agent sent
because two of the sites refuse the default one.

Usage:
    python3 il_county_commissioners_scraper.py [output.json]   # default: stdout
"""

import datetime
import html as html_mod
import json
import os
import re
import sys
import time

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import aia_bundle
import platinum_canvass
import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    require_robots_once, UA_CHROME_X11_128,
)

UA = {"User-Agent": UA_CHROME_X11_128}

PHONE_RE = re.compile(r"(\d{3})\D{0,3}(\d{3})\D?(\d{4})")
EXT_RE = re.compile(r"ext\.?\s*(\d+)", re.I)


def clean(fragment):
    return re.sub(r"\s+", " ", html_mod.unescape(
        re.sub(r"(?s)<[^>]+>", " ", fragment or ""))).strip()


def text_lines(page):
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    text = html_mod.unescape(re.sub(r"(?s)<[^>]+>", "\n", body))
    return [l.strip() for l in text.splitlines() if l.strip()]


def email_in(fragment, allow_bare=False):
    """The e-mail a fragment publishes, whether or not Cloudflare has hidden it.

    Three encodings, all meaning "this address is on the page". The third is
    OPT-IN (`allow_bare`) because a naked address pattern will happily match a
    webmaster or vendor address sitting in a footer; a caller passes it only
    when the fragment is already narrowed to one person's block. Morgan is the
    first county to need it — it prints "Email: mwankel@morgancounty-il.com" as
    text, with no link at all.

      1. `mailto:someone@county.gov` — the plain case.
      2. `<span class="__cf_email__" data-cfemail="79...">` — Cloudflare's
         Email Address Obfuscation, a spam-harvester deterrent the CDN applies
         automatically. The page's own JavaScript decodes it for every visitor,
         so the address is published exactly as before; only its wire format
         changed. The scheme is a one-byte XOR: the first hex byte is the key.

    WHY THIS EXISTS, on the day it was added (2026-08-08): browncoil.org turned
    the setting on at some point after Brown's roster was first built, and the
    mailto-only reader silently returned SEVEN MEMBERS WITH NO E-MAIL. Nothing
    would have failed — the member count guard still passed at 7 — so a
    regenerate would have quietly deleted seven published addresses from a tool
    whose whole job is telling people how to reach their representatives.
    The decoder was verified before being trusted: it reproduces all seven
    addresses already in data/app/il-county-commissioners.json exactly, which is
    what makes this the SAME data rather than a new claim about it.
    """
    m = re.search(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                  fragment or "")
    if m:
        return m.group(1).strip().lower()
    m = re.search(r'data-cfemail="([0-9a-fA-F]{4,})"', fragment or "")
    if not m:
        if allow_bare:
            bare = re.search(r"(?<![\w.+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                             clean(fragment or ""))
            return bare.group(1).strip().lower() if bare else None
        return None
    try:
        raw = bytes.fromhex(m.group(1))
    except ValueError:
        return None
    key, decoded = raw[0], ""
    for byte in raw[1:]:
        decoded += chr(byte ^ key)
    return decoded.strip().lower() or None


def normalize_phone(raw, keep_ext=True):
    m = PHONE_RE.search(raw or "")
    if not m:
        return None
    phone = "-".join(m.groups())
    if keep_ext:
        e = EXT_RE.search(raw or "")
        if e:
            phone += " ext. " + e.group(1)
    return phone


def role_of(text):
    """Only roles the source states. 'Chairman/Budget Director' keeps the
    board role and drops the administrative title the card has no use for."""
    t = (text or "").lower()
    if "vice" in t and "chair" in t:
        return "Vice Chairman"
    if "chair" in t:
        return "Chairman"
    if "commissioner" in t:
        return "Commissioner"
    return None


# ---------------------------------------------------------------- Monroe
def parse_monroe(page):
    """Monroe names its three commissioners in a prose sentence, one per line:
    "George E. Green, Commissioner – Chairman". No per-member phone or e-mail
    is published anywhere — only the board office's shared line — so that is
    all that ships."""
    members = []
    for line in text_lines(page):
        m = re.match(r"^([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3})\s*[,–-]\s*"
                     r"(Commissioner\s*[–-]\s*Chairman|Vice\s+Chairman|Commissioner)\s*$", line)
        if not m:
            continue
        role = role_of(m.group(2))
        if role and not any(x["name"] == m.group(1).strip() for x in members):
            members.append({"name": m.group(1).strip(), "role": role})
    office = None
    lines = text_lines(page)
    for i, line in enumerate(lines):
        if re.search(r"Administrative Assistant", line, re.I):
            addr = next((l for l in lines[i:i + 4] if re.search(r"\d+\s+\S+.*,\s*IL\s*\d{5}", l)), None)
            tel = next((l for l in lines[i:i + 8] if PHONE_RE.search(l)), None)
            office = {"label": "Board of Commissioners",
                      "address": addr,
                      "phone": normalize_phone(" ".join(lines[i:i + 8]))}
            break
    return members, office


# -------------------------------------------------------------- Randolph
def parse_randolph(page):
    """Randolph publishes one <p> per commissioner, <br>-separated:
    <strong>NAME</strong> / role / switchboard + that member's own extension /
    a mailto behind the words "Send Message"."""
    members = []
    for para in re.findall(r"(?is)<p[^>]*>(.*?)</p>", page):
        m = re.search(r"(?is)<strong>(.*?)</strong>", para)
        if not m:
            continue
        name = clean(m.group(1))
        if not re.fullmatch(r"[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3}", name or ""):
            continue
        rest = clean(para[m.end():])
        role = role_of(rest[:120])
        if not role:
            continue
        entry = {"name": name, "role": role}
        phone = normalize_phone(rest)
        if phone:
            entry["phone"] = phone
        email = re.search(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", para)
        if email:
            entry["email"] = email.group(1).lower()
        if not any(x["name"] == name for x in members):
            members.append(entry)
    return members, None


# ------------------------------------------------------------------ Pike
def parse_pike(page):
    """Pike prints one <p> per member: "Reta Hoskin (Chairman)   rhoskin@pike…".
    Every member has a county e-mail; the county publishes no per-member phone
    and no board office address, so neither ships.

    AT-LARGE, PROVEN: the county's own certified summary report for the
    2024 General Election names the contest "FOR COUNTY BOARD - AT LARGE",
    counted across all 31 precincts. Not inferred from the page's silence about
    districts — silence is not evidence (see the module header).

    E-MAILS ARE CLOUDFLARE-OBFUSCATED as of 2026-08-17 — the county switched
    the CDN setting on at some point after this parser was written, so every
    address became `<a class="__cf_email__" data-cfemail="...">[email protected]</a>`
    and the visible text no longer contains one. This parser used to require a
    literal address at the END of the line, so it matched NOTHING at all and
    returned zero members — which is why it failed loudly (the count guard)
    rather than silently emptying nine addresses the way Brown's nearly did.
    The name and role are now read from the paragraph's text and the address
    through email_in(), which handles both wire formats."""
    members = []
    for para in re.findall(r"(?is)<p[^>]*>(.*?)</p>", page):
        line = clean(re.sub(r"(?is)<a\b.*?</a>", " ", para))
        m = re.match(r"^([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3})"
                     r"(?:\s*\((.*?)\))?\s*$", line)
        if not m:
            continue
        entry = {"name": m.group(1).strip(),
                 "role": role_of(m.group(2)) or "Board Member"}
        em = email_in(para)
        if em:
            entry["email"] = em
        if not any(x["name"] == entry["name"] for x in members):
            members.append(entry)
    return members, None


# ---------------------------------------------------------------- Putnam
def parse_putnam(page):
    """Putnam lists its five members as <strong><a>Name, Role</a></strong>.

    READ THE TEXT, NOT THE LINK. Every one of those profile hrefs 404s, and TWO
    of them point at `steve_malavolti.php` — a member no longer on the board:
    once for the ", Vice-Chairman" fragment split off Anthony Rue's row, and
    once for Marlee Giacometti's whole row. Keying on the href would name a
    former member twice and lose two sitting ones. The visible text is what the
    county maintains, so the visible text is what is read. (St. Clair is the
    mirror image — there the caption is wrong and the URL right — which is why
    neither surface gets blanket trust.)

    No per-member contact is published; the shared courthouse line ships as the
    board office instead."""
    members = []
    block = re.search(r"(?is)Click on a board member(.*?)(?:<strong>\s*Mailing Address)", page)
    # Rows are <br>-separated, NOT tag-separated: the Vice-Chairman's name and
    # his title sit in two different <a> tags, so splitting on tags puts them on
    # separate lines and loses him. Split on the line break the county actually
    # uses, then strip tags within the row.
    for chunk in re.split(r"(?i)<br\s*/?>", block.group(1) if block else ""):
        line = clean(chunk)
        m = re.match(r"^(.*?)[,\s]\s*(Chairman|Vice-?\s*Chairman|Board Member)\s*$",
                     line, re.I)
        if not m:
            continue
        name = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(",").strip()
        # Names carry nicknames and suffixes ("Floyd "BJ" Holocker, III"); what
        # they never contain is a digit or an @, which is the cheap sanity test.
        if not name or re.search(r"[@\d]", name):
            continue
        role = ("Vice Chairman" if re.match(r"(?i)vice", m.group(2)) else
                "Chairman" if re.match(r"(?i)chair", m.group(2)) else "Board Member")
        if not any(x["name"] == name for x in members):
            members.append({"name": name, "role": role})
    office = None
    lines = text_lines(page)
    for i, line in enumerate(lines):
        if re.search(r"Putnam County Courthouse", line, re.I):
            addr = [l for l in lines[i + 1:i + 5]
                    if not re.match(r"(?i)^(P\.?O\.? Box|Phone|Fax)", l)]
            street = next((l for l in addr if re.match(r"^\d+\s", l)), None)
            city = next((l for l in addr if re.search(r",\s*IL\s*\d{5}", l)), None)
            office = {"label": "County Board",
                      "address": ", ".join(x for x in (street, city) if x) or None,
                      "phone": normalize_phone(" ".join(lines[i:i + 10]))}
            break
    return members, office


# ----------------------------------------------------------------- Brown
def parse_brown(page):
    """Brown groups members under role headings ("Chairman", "Vice-Chairman",
    "Board Members") with one <p> each: name, street, town, phone, e-mail.

    THE STREET AND TOWN ARE READ ONLY TO BE DROPPED — they are the member's
    RESIDENCE, and the fleet never collects those (the Madison precedent).

    ONE SOURCE TYPO TO SURVIVE: the Vice-Chairman's phone is marked up as
    `<a href="mail:2176538827">` — "mail:" where every other row has "tel:".
    Reading phones out of the href would silently drop his; the visible text is
    read instead.

    E-MAILS ARE CLOUDFLARE-OBFUSCATED as of 2026-08-08 — no mailto: survives on
    the page — so they are read through email_in(), which handles both forms.
    See that helper for why a plain mailto reader would have silently emptied
    all seven rows without failing anything."""
    members = []
    for heading, body in re.findall(
            r'(?is)<span class="title-text[^"]*">(.*?)</span>.*?'
            r'<div class="pp-sub-heading">(.*?)</div>', page):
        head = clean(heading)
        role = ("Chairman" if re.fullmatch(r"(?i)chairman", head) else
                "Vice Chairman" if re.search(r"(?i)vice", head) else
                "Board Member" if re.search(r"(?i)board member", head) else None)
        if not role:
            continue
        for para in re.findall(r"(?is)<p[^>]*>(.*?)</p>", body):
            name_m = re.search(r"(?is)<strong>(.*?)</strong>", para)
            if not name_m:
                continue
            name = clean(name_m.group(1))
            if not re.fullmatch(r"[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3}", name or ""):
                continue
            entry = {"name": name, "role": role}
            phone = normalize_phone(clean(para), keep_ext=False)
            if phone:
                entry["phone"] = phone
            em = email_in(para)
            if em:
                entry["email"] = em
            if not any(x["name"] == name for x in members):
                members.append(entry)
    return members, None


# --------------------------------------------------------------- Calhoun
def parse_calhoun(page):
    """Calhoun gives each commissioner a `text-module-elected-person` block:
    name, title, "Term: YYYY to Present", a biography, e-mail, and a phone.

    THE PHONE IS THE SAME NUMBER ON EVERY ROW — 618-576-9700 ext. 2 — which
    makes it the board's switchboard, not per-member contact. Repeating it
    under five names would imply five direct lines that do not exist, so it is
    hoisted to the board office once (the Monroe posture: a shared switchboard
    is honest, an invented per-member number is not). The biographies are not
    card material and are dropped.

    AT-LARGE, PROVEN: the county's own certified 2026 primary report names the
    contest "CO.COMMISSIONER CWD" — countywide."""
    members, phones = [], set()
    for block in re.findall(r'(?is)text-module-elected-person.*?'
                            r'<div class="et_pb_text_inner">(.*?)</div>', page):
        parts = [clean(x) for x in re.split(r"(?is)<[^>]+>", block)]
        parts = [p for p in parts if p]
        if not parts:
            continue
        name = parts[0]
        if not re.fullmatch(r"[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3}", name or ""):
            continue
        joined = " ".join(parts)
        role = ("Vice Chairman" if re.search(r"(?i)vice\s*chair", joined) else
                "Chairman" if re.search(r"(?i)chair", joined) else
                "Commissioner" if re.search(r"(?i)commissioner", joined) else None)
        if not role:
            continue
        entry = {"name": name, "role": role}
        since = re.search(r"Term:\s*(\d{4})\s*to\s*Present", joined, re.I)
        if since:
            entry["since"] = int(since.group(1))
        em = re.search(r"mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", block)
        if em:
            entry["email"] = em.group(1).strip().lower()
        tel = normalize_phone(joined)
        if tel:
            phones.add(tel)
        if not any(x["name"] == name for x in members):
            members.append(entry)
    # One distinct number across the whole board => switchboard, not per-member.
    office = ({"label": "Board of Commissioners", "phone": phones.pop()}
              if len(phones) == 1 else None)
    return members, office



def parse_schuyler(page):
    """Schuyler prints the board as three HEADED groups — "Chairman",
    "Vice-Chairman", then "County Board Members" — with each person followed by
    the courthouse address, a phone and a county e-mail.

    THE ROLE IS THE HEADING, NOT THE ROW. Every other county in this file marks
    the officer on the person's own line; here the heading above a name is the
    only thing that says who chairs. So the parse carries the current heading
    forward and applies it to the names beneath it, and a name appearing before
    any heading is dropped rather than given a default role.

    THE ADDRESS IS THE COURTHOUSE, ON ALL SEVEN ROWS — 102 S. Congress St.,
    Suite 104, Rushville. That makes it the board's office, not seven
    residences, so it is hoisted once (the Calhoun/Monroe posture) rather than
    repeated under each name as if it were personal. The PHONES do differ per
    member, so those stay on the rows.

    AT-LARGE, PROVEN: the County Clerk's own certified results
    (elections.schuyler.il.us/results-2.pdf) name the contest "FOR MEMBERS OF
    THE COUNTY BOARD ... (Vote for not more than four)" with "Precincts
    Reporting 17 of 17" — one countywide contest, and the word "District" does
    not appear anywhere in the 11-page canvass. Seven seats, elected in
    staggered groups."""
    ROLES = (("(?i)^vice[-\s]*chair", "Vice-Chairman"),
             ("(?i)^chair", "Chairman"),
             ("(?i)^county board members", "Board Member"))
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|td|tr)>", "\n", text)
    lines = [clean(l) for l in re.sub(r"<[^>]+>", "\n", text).split("\n")]
    lines = [l for l in lines if l]

    members, role, office_phone = [], None, None
    seen = set()
    for i, line in enumerate(lines):
        matched = next((r for pat, r in ROLES if re.search(pat, line)), None)
        if matched:
            role = matched
            continue
        if not role:
            continue
        if not re.fullmatch(r"[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3}", line):
            continue
        window = " ".join(lines[i:i + 4])
        email = re.search(r"[\w.+-]+@[\w.-]+\.\w+", window)
        phone = re.search(r"\b(\d{3}-\d{3}-\d{4})\b", window)
        # A name with neither is a nav item or a caption, not a member row.
        if not (email or phone):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        entry = {"name": line, "role": role}
        if email:
            entry["email"] = email.group(0).lower()
        if phone:
            entry["phone"] = phone.group(1)
        members.append(entry)

    office = {"label": "Schuyler County Board",
              "address": "102 S. Congress St., Suite 104, Rushville, IL 62681"}
    return members, office



# ---------------------------------------------------------------- Hamilton
def parse_hamilton(page):
    """Hamilton's board page (the county's NEW site — it went live the morning
    of 2026-08-05, mid-migration by the Clerk's own description) renders each
    member as a card whose name sits alone in a `font-semibold text-ink` div —
    exactly five, and nothing else on the page uses that class. The cards
    carry committee lists but no per-member contact, so what ships per member
    is name and role, with the BOARD's shared departmental line hoisted to the
    office block — a shared line is honest, an invented per-member number is
    not.

    AT-LARGE, STATED BY THE ELECTION AUTHORITY: County Clerk & Recorder
    Heather Bowman, in writing, 2026-08-05, four minutes after being asked —
    "Our County Board is elected at large." The members page corroborates:
    no district appears anywhere on it.

    CHAIR FROM THE HEADER, NOT THE CARDS: the member cards are role-less; the
    department header reads "Kelly Woodrow / Board Chair". The parse takes the
    chair from that adjacency (normalized to the fleet's "Chairman"
    vocabulary) and applies Board Member to the rest. A header name that never
    appears among the cards is dropped, never added."""
    names = [clean(n) for n in
             re.findall(r'<div class="font-semibold text-ink">([^<]+)</div>', page)]
    names = [n for n in names if n]
    m = re.search(r">([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]*){1,3})"
                  r"(?:\s*</?[a-zA-Z][^>]*>\s*)*Board\s+Chair", page)
    chair = clean(m.group(1)) if m else None
    members, seen = [], set()
    for n in names:
        if n.lower() in seen:
            continue
        seen.add(n.lower())
        members.append({"name": n,
                        "role": "Chairman" if (chair and n == chair) else "Board Member"})
    office = {"label": "Hamilton County Board",
              "address": "Hamilton County Courthouse, 100 S. Jackson Street, Room 2, McLeansboro, IL 62859",
              "phone": "618-643-2721",
              "email": "board@hamiltoncountyil.gov"}
    return members, office


# ------------------------------------------------------------------ Morgan
def parse_morgan(page):
    """Morgan's commissioners page is plain server-rendered WordPress, one
    paragraph per member:

        <p><p>Chairman &#8211; Michael Wankel, <i>Republican</i><br />
        Current Term: December 1, 2022 to November 30, 2028<br />
        Next election: November, 2028</p>
         Email: mwankel@morgancounty-il.com</p>

    THE COUNTY HAS TWO WEBSITES, and this project spent a day on the wrong one.
    morgancounty-il.GOV is a client-rendered React SPA marked noindex whose
    Supabase backend serves no tables — from which it was concluded, and
    written into a gap record and very nearly into an e-mail to the County
    Clerk, that Morgan "publishes their names nowhere a machine can read".
    morgancounty-il.COM, the county's real content site, publishes all three
    with role, party, full term dates, next election and a personal e-mail
    apiece — more than most counties in this fleet manage. The .com host was
    even listed in the .gov bundle's own strings and went unfollowed. When a
    county's site looks impossible, look for the other one.

    THE TERM START IS WHY THIS MATTERS BEYOND CONVENIENCE. Michael D. Woods's
    term runs from OCTOBER 1, 2024 — a mid-term start, i.e. an appointment
    filling the vacancy left by the commissioner elected in 2020. Election
    returns show that 2020 contest going to Bradley A. Zeller, and an
    appointment appears in no return anywhere, so a roster derived from
    canvasses would have named the wrong person with perfect arithmetic. The
    start date ships as `since` for exactly that reason.

    AT-LARGE, PROVEN independently of this page: the county's own results
    portal (results.gbsvote.com, l_id=16) carries "FOR COUNTY COMMISSIONER /
    27 of 27 precincts reporting / Vote for ( 1 )" on the 19 Mar 2024 primary
    marked ** OFFICIAL RESULTS **, repeated in the 2022 and 2024 generals.
    Three commissioners, whole county, no districts."""
    entry = re.search(r"(?is)<section class=\"entry\">(.*?)</section>", page)
    body = entry.group(1) if entry else page
    members = []
    for block in re.split(r"(?i)<hr\s*/?>", body):
        m = re.search(r"(?is)<p>\s*(?:<p>)?\s*([A-Za-z ]{4,20}?)\s*(?:&#8211;|&ndash;|[-\u2013\u2014])\s*"
                      r"([^,<]{3,60}?)\s*,\s*<i>\s*([A-Za-z]+)\s*</i>", block)
        if not m:
            continue
        role, name = clean(m.group(1)), clean(m.group(2))
        if not name:
            continue
        entry_obj = {"name": name}
        canonical = role_of(role)
        # role_of maps "Vice Chairman" and "Chairman"; a plain "Commissioner"
        # row keeps that word, which is what the county calls the seat.
        if canonical:
            entry_obj["role"] = canonical
        flat = clean(block)
        since = re.search(r"Current Term:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", flat)
        if since:
            entry_obj["since"] = since.group(1)
        # allow_bare: the address is printed as text, not linked, and `block`
        # is already one member's paragraph.
        email = email_in(block, allow_bare=True)
        if email:
            entry_obj["email"] = email
        if not any(x["name"] == name for x in members):
            members.append(entry_obj)

    office = None
    side = re.search(r"(?is)<div class=\"text-block commissioners-contact\">(.*?)</div>", page)
    if side:
        lines = [clean(l) for l in re.split(r"(?i)<br\s*/?>|</p>", side.group(1))]
        lines = [l for l in lines if l]
        addr = [l for l in lines if re.search(r"\d+\s+\w|,\s*IL\s*\d{5}", l)]
        office = {"label": "Morgan County Commissioners",
                  "address": ", ".join(addr[:2]) if addr else None,
                  "phone": normalize_phone(" ".join(lines))}
    return members, office


# ------------------------------------------------------------------ Greene
def parse_greene(page):
    """Greene prints the whole board as ONE three-column table — Name, Email,
    Phone — so this is the simplest parse in the file: read the rows, drop the
    header.

    THE ROLE IS APPENDED TO THE NAME, after an en dash: "Earlene Castleberry –
    Chairwoman", "Mark Strang – Vice Chair". Split there; a row with no dash is
    a plain member.

    "CHAIRWOMAN" IS KEPT VERBATIM. Normalising it to "Chairman" would be a
    one-word change that misstates a real person's own county's wording, and
    this file has no business doing that — ALLOWED_ROLES was widened instead.
    The same goes for "Vice Chair", which Greene writes without the -man.

    CONTACT IS PARTIAL AND SHIPS THAT WAY: six of the seven publish a county
    e-mail and only the two officers publish a phone — Mark Strang has a phone
    and NO e-mail, which is why neither field may be treated as required. What
    the county publishes is what the card shows.

    AT-LARGE, PROVEN — the whole reason Greene rides the County card and has no
    geometry. The county's own results portal (results.gbsvote.com, which names
    Clerk Melissa Carter as Election Authority) carries the 17 Mar 2026 GENERAL
    PRIMARY marked ** OFFICIAL RESULTS ** with the contest "FOR COUNTY BOARD
    FOUR YEAR TERM / 22 of 22 precincts reporting / Vote for ( 4 )", and the 19
    Mar 2024 PRIMARY, also OFFICIAL, with "FOR MEMBER OF THE COUNTY BOARD / 22
    of 22 precincts reporting / Vote for ( 1 )". The whole county votes on every
    seat and the word "District" appears in neither canvass. Seven seats,
    elected in staggered groups of four and three."""
    body = page[page.find("<body"):] or page
    m = re.search(r"(?is)<table.*?</table>", body)
    if not m:
        return [], None
    members = []
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", m.group(0)):
        cells = [clean(re.sub(r"<[^>]+>", " ", c))
                 for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row)]
        if len(cells) < 3 or cells[0].lower() == "name":
            continue
        # en dash, em dash or hyphen — the page uses en, the others are cheap
        # insurance against an editor retyping the line.
        parts = re.split(r"\s[–—-]\s", cells[0], 1)
        name = parts[0].strip()
        role = parts[1].strip() if len(parts) > 1 else ""
        if not name:
            continue
        entry = {"name": name}
        if role:
            entry["role"] = role
        email = re.search(r"[\w.+-]+@[\w.-]+\.\w+", cells[1])
        phone = re.search(r"\b(\d{3}-\d{3}-\d{4})\b", cells[2])
        if email:
            entry["email"] = email.group(0).lower()
        if phone:
            entry["phone"] = phone.group(1)
        members.append(entry)
    office = {"label": "Greene County Board",
              "address": "519 N. Main St., Carrollton, IL 62016"}
    return members, office


# ---------------------------------------------------------------------------
# COUNTIES WITH NO WEBSITE TO SCRAPE.
#
# Every SITES entry below fetches a page. This table is for the counties that
# have no page to fetch — not blocked, not slow, ABSENT. Edwards is the first:
# asked directly on 2026-08-06 whether the county uses some other web address,
# County Clerk & Recorder Melanie Knight replied "The county does not currently
# have a website", which matches the measurement (edwardscounty.illinois.gov
# answers NOERROR with no A record; www. is NXDOMAIN — the domain carries mail
# and hosts nothing). No scraper can ever exist for such a county, so the
# roster comes from a document its Clerk sent and is carried here verbatim.
#
# THE HONESTY COST IS REAL AND IS PAID OUT LOUD. A weekly job that "refreshes"
# a hand-carried roster refreshes nothing: the same names ship every run
# whatever the county has done since. So each entry states the document and the
# date it was verified, and main() prints a line every run naming the county,
# the document and how old it is. It is never silently folded in with the
# counties that really were re-read.
#
# WHAT IS DELIBERATELY NOT SHIPPED. Knight's letterhead gives each commissioner
# a HOME address and a personal phone (two of them marked "(h)" and "(c)"). The
# roster ships neither — the same call every municipal source in this project
# makes, because a card must not publish a private home. What ships is the name,
# the office, and the county e-mail address the county itself assigns
# (commissioner1@…, commissioner2@…), which is a real contact route that belongs
# to the seat rather than the person. The office block gets the courthouse
# address only: the phone on the letterhead is the CLERK's line, and printing it
# under "Board Office" would imply the board answers it.
def parse_moultrie(page):
    """Moultrie publishes its board as a staff-directory TABLE with a column
    per field — County Board Position, First Name, Last Name, Term Length,
    Email, Phone — plus a hidden sort column the county uses to order the page.
    That hidden first cell is why this parser indexes from the RIGHT of the
    header row rather than assuming column 0 is the position: a display:none
    cell is still a <td>, and counting from the left silently shifts every
    field by one.

    THE NAME IS TWO COLUMNS. First and last ship joined with a single space;
    nothing is inferred about middle names or suffixes the county does not
    print.

    ROLES ARE KEPT VERBATIM, the Greene rule. Moultrie writes "Chairperson"
    and "Vice Chairperson"; normalising either to the -man form would misstate
    a real person's own county's wording, so ALLOWED_ROLES was widened instead.
    Its plain rows read "Member", which is the county's word for no office and
    ships as no role at all.

    TERM LENGTH IS A RANGE ("12/1/22-11/30/26"), not an expiry, and it ships as
    the county prints it. One row reads "08/14/25 - 11/30/26" — a seat filled
    mid-term by appointment, which is exactly the fact a card should show and a
    canvass never could.

    AT-LARGE, PROVEN — the whole reason Moultrie rides the County card and has
    no geometry. The Clerk's own results system (il-moultrie.pollresults.net)
    carries the certified 17 Mar 2026 General Primary with the contest "COUNTY
    BOARD DISTRICT AT LARGE MEMBER", 16 of 16 precincts, Vote For 5 — the whole
    county voting on every seat up that cycle, and the word "District" used
    only in the vendor's own label for "at large". Nine seats, elected in
    staggered groups (five terms run 12/1/22-11/30/26, four 12/1/24-11/30/28)."""
    body = page[page.find("<body"):] or page
    tables = re.findall(r"(?is)<table[^>]*>.*?</table>", body)
    for table in tables:
        header = re.search(r"(?is)<thead.*?</thead>", table)
        if not header or "County Board Position" not in header.group(0):
            continue
        cols = [clean(re.sub(r"<[^>]+>", " ", c))
                for c in re.findall(r"(?is)<th[^>]*>(.*?)</th>", header.group(0))]
        try:
            base = cols.index("County Board Position")
        except ValueError:
            return [], None
        members = []
        for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table):
            cells = [clean(re.sub(r"<[^>]+>", " ", c))
                     for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", row)]
            if len(cells) < base + 4:
                continue
            role = cells[base]
            name = " ".join(p for p in (cells[base + 1], cells[base + 2]) if p).strip()
            if not name:
                continue
            entry = {"name": name}
            if role and role.lower() != "member":
                entry["role"] = role
            term = cells[base + 3] if len(cells) > base + 3 else ""
            if term:
                entry["term"] = re.sub(r"\s*-\s*", "–", term)
            email = re.search(r"[\w.+-]+@[\w.-]+\.\w+", row)
            if email:
                entry["email"] = email.group(0)
            phone = re.search(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}",
                              cells[base + 5] if len(cells) > base + 5 else "")
            if phone:
                digits = re.sub(r"\D", "", phone.group(0))
                entry["phone"] = "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:10])
            members.append(entry)
        return members, None
    return [], None


# Counties whose roster comes from their own CERTIFIED ELECTION RETURNS, because
# their websites cannot be read and no document has been carried by hand.
#
# WHY THIS TIER EXISTS. Union and Williamson both sit behind an sgcaptcha gate —
# their sites answer HTTP 202 with a 169-byte redirect to /.well-known/sgcaptcha/,
# which is this project's recorded "202 is never a document" case. What both
# counties DO publish machine-readably is their canvasses, on
# platinumelectionresults.com. So each member here is whoever the county
# CERTIFIED as elected in the most recent general election that seated their
# seat — the Clark posture, applied to an at-large board — and every row renders
# that election, because a canvass cannot show a mid-term appointment.
#
# THE COUNTYWIDE CHECK IS A GATE, NOT AN ASSUMPTION. An at-large county belongs
# on the County card precisely because every voter votes for every seat, so this
# refuses to write unless each commissioner contest was counted in EVERY precinct
# the canvass reports for any contest. That is what distinguishes these from
# Adams, whose district contests count 9 or 10 precincts against a county of 74.
# It also caught a stale state record: ISBE's 2007 county-board structure table
# calls Union "Single-Member" with five districts, and Union's own returns count
# all five lettered seats in 20 of 20 precincts, with Seat A polling 6,694 votes
# against the countywide State's Attorney's 6,738 in the same canvass. A fifth of
# the county would poll about 1,300. The returns are current and the table is not.
RETURNS_ROSTERS = {
    "UNION": {
        "name": "Union County",
        "countyId": 16,
        "structure": "Commission form \u2014 5 commissioners elected countywide by "
                     "lettered seat, six-year staggered terms",
        "expect": 5,
        # Each seat's own contest, newest election wins. The county writes
        # "For County Commissioner Seat A" and also "For Commissioner Seat D";
        # the letter is what identifies the seat, not the wording around it.
        "seat_pattern": r"Commissioner\s+Seat\s+([A-E])\b",
        "office": {
            "label": "Union County Courthouse",
            "address": "309 West Market Street, Jonesboro, IL 62952",
        },
    },
    "WILLIAMSON": {
        "name": "Williamson County",
        "countyId": 51,
        "structure": "Commission form \u2014 3 commissioners elected countywide, "
                     "six-year staggered terms, one seat each general election",
        "expect": 3,
        # No seat labels here: every contest is just "For County Commissioner",
        # one per general election. The three sitting commissioners are therefore
        # the winners of the three most recent generals, deduplicated by name
        # because a re-elected member holds ONE seat, not two (James "Jim" Marlo
        # won in both 2018 and 2024, which is also what proves the six-year term).
        "seat_pattern": None,
        "contest_pattern": r"For\s+County\s+Commissioner\b",
        "office": {
            "label": "Williamson County Courthouse",
            "address": "407 North Monroe Street, Marion, IL 62959",
        },
    },
}

DOCUMENT_ROSTERS = {
    "ALEXANDER": {
        "name": "Alexander County",
        "structure": "Commission form — 3 commissioners elected countywide",
        "document": "e-mail from the Alexander County Clerk & Recorder's office "
                    "(acc@alexandercountyil.org), 2026-08-24",
        "verified": "2026-08-24",
        "expect": 3,
        # THE COUNTY'S OWN WEBSITE WAS CHECKED THE SAME DAY AND IS WRONG TWICE
        # OVER. alexandercounty.illinois.gov/county-board/'s team widget still
        # names only Griggs and Smith — Essex is absent — and gives Griggs as
        # Chairman and Smith as plain Member, the reverse of what the Clerk's
        # office states below. That is why this moved off the live scrape
        # (parse_alexander/enrich_alexander, retired 2026-08-24) onto a document:
        # a site proven stale on both the roster and the titles is not a source
        # this project re-reads weekly and trusts by default. Ordered as the
        # e-mail orders them.
        "members": [
            {"name": "James (Jim) Smith", "role": "Chairman"},
            {"name": "Larry (Steve) Essex", "role": "Vice Chairman"},
            {"name": "Joe E. Griggs", "role": "Member"},
        ],
    },
    "EDWARDS": {
        "name": "Edwards County",
        "structure": "Commission form — 3 commissioners elected countywide",
        "document": "Commissioners names-addresses 2025.doc, sent by County Clerk "
                    "& Recorder Melanie Knight, 2026-08-06",
        "verified": "2026-08-06",
        "expect": 3,
        # Ordered as the county's own document orders them by seat number.
        "members": [
            {"name": "Duane Lear", "role": "Chairman",
             "email": "commissioner1@edwardscounty.illinois.gov", "since": 2020},
            {"name": "Davis Messman", "role": "Commissioner",
             "email": "commissioner2@edwardscounty.illinois.gov", "since": 2022},
            {"name": "Matthew R. St.Ledger", "role": "Commissioner",
             "email": "commissioner3@edwardscounty.illinois.gov", "since": 2024},
        ],
        "office": {
            "label": "Edwards County Courthouse",
            "address": "50 East Main Street, Albion, IL 62806",
        },
    },
    "HARDIN": {
        "name": "Hardin County",
        "structure": "Commission form — 3 commissioners elected countywide",
        "document": "e-mail from County Clerk & Recorder Jill Cowsert, 2026-10-01, "
                    "with her correction of the third name the same day",
        "verified": "2026-10-01",
        "expect": 3,
        # THE THIRD COUNTY WITH NO WEBSITE AT ALL, and the Clerk is the one who
        # settled it: asked on 2026-08-21 whether the county published a board
        # list anywhere, she replied on 2026-08-24, in full — "Our county board
        # is elected countywide. And we do not have a website in Hardin County."
        # So this is a document roster permanently rather than a scrape waiting
        # for a site to appear, and the gap record it closes had been reading
        # the county's PUBLISHED web address (hardincountyil.gov) as evidence
        # about the county: that address is a parked page and the county is not
        # behind it.
        #
        # The form was already proven twice from certified returns before she
        # wrote — the 2026 General Primary prints a committeeperson contest per
        # precinct per party and no district-suffixed board contest anywhere,
        # and an older canvass on a second vendor agrees — so her sentence
        # confirms the form rather than being the only source for it. The NAMES
        # are hers alone, from her reply of 2026-10-01: "We have three
        # commissioners. Darrick Armstrong is our chairman, Ricky Williams is
        # our vice-chairman, and Michael Belfor is the third commissioner."
        # She corrected the third name herself at 19:27 UTC the same day: "The
        # third member is Michael Belford. I left the d off." Her correction is
        # what ships; a name is the source's to correct, never ours.
        # Ordered as she orders them. She assigns no per-seat e-mail and the
        # county publishes no page to carry one, so each row is a name alone,
        # and no office address is asserted — the courthouse address this
        # project holds is the CLERK's office and is not claimed as theirs.
        "members": [
            {"name": "Darrick Armstrong", "role": "Chairman"},
            {"name": "Ricky Williams", "role": "Vice Chairman"},
            {"name": "Michael Belford", "role": "Commissioner"},
        ],
    },
    "JOHNSON": {
        "name": "Johnson County",
        "structure": "Commission form — 3 commissioners elected countywide",
        "document": "e-mail from County Clerk Robin Harper-Whitehead, 2026-10-07",
        "verified": "2026-10-07",
        "expect": 3,
        # THE FOURTH NO-WEBSITE COUNTY, after Edwards, Wabash and Hardin. The
        # Clerk wrote on 2026-07-21, answering an unrelated question, "We don't
        # have a website to point back to", so a letter was always the only
        # route to these names. The at-large form was proven before she replied,
        # from the county's own certified canvasses on results.gbsvote.com: the
        # 2022 and 2024 generals and the 2026 primary each carry one "FOR COUNTY
        # COMMISSIONER" contest reporting 16 of 16 precincts and no district
        # contest anywhere. Those returns are relied on for the FORM only; the
        # names and the chair and vice-chair are hers alone, from her reply of
        # 2026-10-07, and ordered as she orders them.
        #
        # The office is the BOARD's, not any member's: she gave one e-mail for
        # the board (commissioners@) and one telephone, which is her own office's
        # line, so the label says whose line it is rather than implying the
        # commissioners answer it themselves. No address ships — she gave none
        # for the board, and the courthouse address this project holds is the
        # Clerk's.
        "members": [
            {"name": "Jason Taylor", "role": "Chairman"},
            {"name": "Matthew Hayden", "role": "Vice Chairman"},
            {"name": "John McCuan", "role": "Commissioner"},
        ],
        "office": {
            "label": "Board of Commissioners, through the County Clerk's office",
            "phone": "618-658-3611",
            "email": "commissioners@johnsonco.illinois.gov",
        },
    },
    "WABASH": {
        "name": "Wabash County",
        "structure": "Commission form — 3 commissioners elected countywide",
        "document": "Commissioners' names and addresses, sent by e-mail by "
                    "County Clerk & Recorder Janet L. Will, 2026-08-16; the "
                    "chairmanship confirmed by her e-mail of 2026-08-17",
        "verified": "2026-08-17",
        "expect": 3,
        # The second ABSENT county: wabashcounty.illinois.gov carries mail and
        # serves no web page (measured 5 Aug 2026, re-checked 9 Aug — the
        # wabash-county-board record has the full measurement). Ordered as the
        # Clerk's e-mail orders them. Her e-mail lists each commissioner with a
        # HOME address and nothing else; per the Edwards rule above none of
        # that ships, and unlike Edwards this county assigns no per-seat
        # e-mail this project can cite, so each row is a name alone. Her Aug 5
        # reply settled the form (one commissioner elected each General
        # Election, six-year terms). WHICH OF THE THREE CHAIRS was not in that
        # e-mail and was asked separately; she answered on 2026-08-17, in full:
        # "Yes, Tim Hocking is the current chairman". That one line is the only
        # source for the Chairman tag below — the county publishes no page to
        # check it against, so the weekly NOT RE-READ line names it too.
        "members": [
            {"name": "Timothy R. Hocking", "role": "Chairman"},
            {"name": "Robert G. Dean", "role": "Commissioner"},
            {"name": "Scott C. West", "role": "Commissioner"},
        ],
    },
}


# ------------------------------------------------------------------ Massac
# Separators the county mixes into these three lines: a plain hyphen, an
# en dash, and a non-breaking space. Stripped from both ends of the name and
# the role. Written as an explicit character set rather than a regex class
# because str.strip() takes CHARACTERS, not patterns — a "\s" in that set
# strips the letter "s", which silently shortens any name ending in one.
MASSAC_SEP_CHARS = " \t-\u2013\u2014:,\u00a0"


def parse_massac(page):
    """Massac's commissioners page prints the whole board as one paragraph:

        <h3>Massac County Commissioners</h3>
        ...
        <p><strong>Jayson Farmer</strong>&#8211; Chairman<br />
           <strong>Jeff Brugger-&nbsp;</strong>Vice Chairman<br />
           <strong>Jimmy Burnham</strong>&#8211; Secretary</p>

    Note the second row: the county puts the separating hyphen INSIDE the
    <strong>, so the name and the role are split inconsistently across the
    three rows. Taking <strong> as the name and the tail as the role, then
    stripping separators from both, is what reads all three the same way.

    AT-LARGE, PROVEN from the county's own results: the Massac County Clerk's
    "March 17, 2026 Primary Election Results" cumulative report carries
    "FOR COUNTY COMMISSIONER - REPUBLICAN PARTY - (Vote for one)" over
    "Precincts Counted 17 / Total 17 / 100.00%" against 11,265 registered
    voters — the county entire, with no district string anywhere on the
    ballot. The control is on the same page: the countywide County Clerk and
    Regional Superintendent contests report the identical 17-of-17 and 11,265,
    so the commissioner contest is countywide in the same sense they are. A
    districted board reports only its own district's precincts, which is
    exactly what neighbouring Jackson's canvass does (9 of its 56 for
    District 1). Three commissioners, whole county, no districts.

    THAT REPORT IS MARKED "Unofficial Results", and it is the only results
    document the county publishes. It is relied on for the FORM alone, which
    certification does not change — a canvass corrects counts, never the
    shape of the ballot — and for nothing else. The roster below comes from
    the county's own commissioners page, never from the returns, for the
    reason worked out on the Scott record: a return names who WON a contest,
    never who holds the seat today.

    NO CONTACT DETAIL SHIPS because the county publishes none for this body:
    its homepage lists a phone for eight departments and not for the
    commissioners, and the commissioners' page carries no address, phone or
    e-mail at all. The courthouse address on the County Clerk's record is the
    CLERK's office and is not asserted here as theirs.
    """
    heading = re.search(r"(?is)<h3>\s*Massac County Commissioners\s*</h3>", page)
    if not heading:
        return [], None
    block = re.search(r"(?is)<div class=\"et_pb_text_inner\">(.*?)</div>",
                      page[heading.end():])
    if not block:
        return [], None
    members = []
    for part in re.split(r"(?i)<br\s*/?>", block.group(1)):
        m = re.search(r"(?is)<strong>(.*?)</strong>(.*)$", part)
        if not m:
            continue
        name = clean(m.group(1)).strip(MASSAC_SEP_CHARS)
        role_text = clean(m.group(2)).strip(MASSAC_SEP_CHARS)
        if not name:
            continue
        entry = {"name": name}
        # role_of maps Chairman and Vice Chairman; Secretary is a board office
        # this county names and the shared mapper does not, so it is kept
        # verbatim here rather than by widening role_of for every county.
        canonical = role_of(role_text)
        if canonical:
            entry["role"] = canonical
        elif role_text.lower() == "secretary":
            entry["role"] = "Secretary"
        if not any(x["name"] == name for x in members):
            members.append(entry)
    return members, None



# ------------------------------------------------------------------ Saline
# Role lines on Saline's page are printed in caps on their own line under the
# member's name. Matching "a line that is all capitals" would be a trap: a
# county that prints a MEMBER in caps would have that member silently eaten as
# a role and dropped from the board. So the test is a vocabulary, not a case
# check, and anything else is a name.
SALINE_ROLE_RE = re.compile(
    r"(?i)^(vice[\s-]*chair(?:man|person|woman)?|chair(?:man|person|woman)?)$")


def parse_saline(page):
    """Saline prints its thirteen members as three plain WordPress columns
    under an <h2>County Board Members</h2>, names separated by <br />:

        <p>Jay Williams<br />CHAIRMAN</p>
        <p>Mike McKinnies<br />VICE-CHAIRMAN</p>
        <p>Casey Perkins<br />Chuck DePriest<br />...</p>

    Only the first column carries roles; the other two are bare names. The
    region is bounded by the NEXT <h2> (Agendas), so the month lists below it
    cannot leak in as members.

    AT-LARGE, PROVEN from the county's own certified canvass: Saline's
    "2026 Primary Results" report, run 26 Mar 2026 and headed Official
    Results, carries "FOR MEMBERS OF THE COUNTY BOARD - REPUBLICAN PARTY -
    (Vote for not more than seven)" over "Precincts Counted 28 / Total 28 /
    100.00%" against all 15,441 registered voters, with no district string
    anywhere on the contest. The control sits on the same page: the Appellate
    Court contest reports the identical 28-of-28 and 15,441. A districted
    board reports only its own district's precincts. Both party ballots for
    the same election print the contest the same way, and "not more than
    seven" of thirteen seats is the stagger.

    TWO INDEPENDENT SOURCES AGREE and were checked before this shipped:
    ISBE's county-board structure table gives Saline as 13 members, At-Large,
    one district — and that table is not taken on trust either, since its
    metadata is from 2007: it was verified against four counties whose current
    pages this project can read (Clay 14 single-member A-N, Hancock 5 districts
    of 3, Lawrence 7 single-member, Adams 21 across 7) and matches all four.
    The county's own page is the third: thirteen members, no district labels
    anywhere on it.

    PAIGE SCHIMP IS NOT A MEMBER and must never be parsed as one. She is the
    County Board Secretary — staff to the board, not a seat on it — and she
    appears in a separate contact block above the member columns, which is why
    this parser starts at the <h2> and not at the top of the page. Her office
    details are the county's own for the board, so they ship as the office
    block; her name does not.
    """
    heading = re.search(r"(?is)<h2>\s*County Board Members\s*</h2>", page)
    if not heading:
        return [], None
    rest = page[heading.end():]
    stop = re.search(r"(?is)<h2>", rest)
    region = rest[:stop.start()] if stop else rest

    members = []
    for para in re.findall(r"(?is)<p>(.*?)</p>", region):
        for line in re.split(r"(?i)<br\s*/?>", para):
            text = clean(line)
            if not text:
                continue
            if SALINE_ROLE_RE.match(text):
                if members:
                    members[-1]["role"] = role_of(text) or text.title()
                continue
            if not any(x["name"] == text for x in members):
                members.append({"name": text})

    office = None
    block = re.search(r"(?is)County Board Secretary(.{0,1200}?)Hours of Operation", page)
    if block:
        flat = clean(block.group(1))
        addr = re.search(r"(\d+\s+[EWNS]?\.?\s*[A-Za-z.\s]+?,?\s*Harrisburg,\s*IL\s*\d{5})", flat)
        # The page prints the street and the city on separate lines, so the
        # flattened match joins them with a space and no comma. Restore it, so
        # this address reads like every other office address in the file.
        street = re.sub(r"\s+", " ", addr.group(1)).strip() if addr else None
        if street:
            street = re.sub(r"\s+(Harrisburg,)", r", \1", street)
        office = {"label": "Saline County Board",
                  "address": street,
                  "phone": normalize_phone(flat)}
    return members, office




# ---------------------------------------------------------------- Gallatin
# Separators Gallatin puts between a name and a board office. Explicit
# characters, not a regex class, for the reason recorded on Massac: str.strip()
# takes CHARACTERS, so a "\s" in this set would strip the letter "s" and
# silently shorten any name ending in one.
GALLATIN_SEP_CHARS = " \t-\u2013\u2014:,\u00a0"
GALLATIN_WIDGET_RE = re.compile(
    r'(?is)<h3 class="widget-title">\s*County Board Members\s*</h3>\s*'
    r'<div class="textwidget">(.*?)</div>')
GALLATIN_PARA_RE = re.compile(r"(?is)<p[^>]*>(.*?)</p>")


def parse_gallatin(page):
    """Gallatin publishes its five members as a SIDEBAR WIDGET on the County
    Board page, not in the page body:

        <h3 class="widget-title">County Board Members </h3>
        <div class="textwidget">
          <p>Andrew Lunsford - Chairman</p>
          <p><span>Contact: (618) 499-0943<br /></span></p>
          <p>Gary Vickery</p>
          <p>Randy Drone</p>
          <p>Warren Rollman</p>
          <p><span>Contact: (618)-841-3608</span></p>
          <p>Terry Schmitt</p>

    THE BODY OF THAT PAGE IS AGENDAS AND MINUTES — some two hundred links and
    not one member's name. A parser that reads the main column, which is where
    every other county in this file keeps its roster, finds no board at all.

    A "Contact:" LINE BELONGS TO THE MEMBER ABOVE IT, and getting that wrong is
    the trap this county sets. Only two of the five publish a phone, so pairing
    the two phones with the first two names — the obvious flattened read, and
    the same shape of error as Franklin's grid — would hand Gary Vickery the
    chairman's number. Each phone is attached to the preceding name or to
    nothing. The other three members publish none and none is invented.

    AT LARGE, PROVEN TWICE FROM THE COUNTY'S OWN CERTIFIED RESULTS, which is
    what lets Gallatin ride the County card with no geometry at all. Both
    canvasses on the Clerk's elections page mark the board contest COUNTY WIDE
    with the same suffix every countywide office on the ballot carries:

        2026 General Primary   CO.BD.MEMBER CWD      (VOTE FOR) 3
        2024 General Primary   COUNTY BOARD MEMBER CWD (VOTE FOR) 2

    The control sits beside them on the same page — COUNTY CLERK CWD, COUNTY
    TREASURER CWD, COUNTY SHERIFF CWD — while district offices on the same
    ballots carry their district in the name (12TH REP.IN CONGRESS, 117TH REP.
    IN THE G.A.) and precinct offices carry a precinct (PCT. COMMITTEEPERSON
    OMAHA). Five seats, staggered three and two, every one of them countywide.

    AND THE TWO SOURCES AGREE ON THE PEOPLE: the 2024 pair (Vickery, Schmitt)
    plus the 2026 trio (Lunsford, Rollman, Drone) are exactly the five names in
    the widget. The roster still comes from the widget and never from the
    returns — a return names who won a contest, not who holds the seat today,
    and the 2026 primary named nominees for an election that has not yet been
    held. Recorded because a cross-check that agrees is worth stating: the
    ballot spells the third of them THOMAS R. DRONE where the county writes
    Randy Drone, and this ships the county's spelling without asserting that
    the two names are one person.

    HOW THIS COUNTY BECAME READABLE AT ALL: gallatinco.illinois.gov serves an
    incomplete TLS chain, which every automated client reports as a connection
    failure and no browser notices. See scripts/aia_bundle.py.
    """
    widget = GALLATIN_WIDGET_RE.search(page)
    if not widget:
        return [], None
    members = []
    for para in GALLATIN_PARA_RE.findall(widget.group(1)):
        txt = clean(para).strip(GALLATIN_SEP_CHARS)
        if not txt:
            continue
        if re.match(r"(?i)^contact\b", txt):
            phone = normalize_phone(txt)
            if phone and members:
                members[-1]["phone"] = phone
            continue
        name, role_text = txt, ""
        split = re.split(r"\s+[-\u2013\u2014]\s+", txt, 1)
        if len(split) == 2:
            name, role_text = split[0], split[1]
        name = name.strip(GALLATIN_SEP_CHARS)
        if not name:
            continue
        entry = {"name": name}
        canonical = role_of(role_text.strip(GALLATIN_SEP_CHARS))
        if canonical:
            entry["role"] = canonical
        if not any(x["name"] == name for x in members):
            members.append(entry)
    return members, None



# ----------------------------------------------------------------- Pulaski
PULASKI_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def parse_pulaski(page):
    """Pulaski prints its three commissioners as one centred Weebly paragraph,
    each seat a name/role/e-mail triple separated by <br />:

        <div class="paragraph" style="text-align:center;"><em><font size="3">
        <strong>Robert Helman</strong><br />Chairman&nbsp;<br />
        rhelman@pulaskicountyil.gov&nbsp;<br /><br />
        <strong>Rex Wilburn</strong><br />Vice Chairman&nbsp;<br />...

    THE PAGE'S OWN HEADING IS ALSO <strong>-WRAPPED AND ALSO SITS IN A
    `<div class="paragraph">` — "Pulaski County Board of Commissioners" in a
    <font size="6">. An unbounded read of every <strong> on the page therefore
    ships the heading as a commissioner.

    AND THE HEADING CANNOT BE USED TO BOUND THE REGION, which the first draft
    of this parser got wrong and the count guard caught. That heading's exact
    text appears TWICE: once at byte 371 inside
    `<meta property="og:description">`, and only then in the heading div at
    ~18,600. Searching for the text and taking the next paragraph div lands on
    the META occurrence, so "the next paragraph div" is the HEADING div — and
    the parser returns exactly one member, named "Pulaski County Board of
    Commissioners". A SOCIAL-CARD META TAG REPEATS THE HEADING, so a
    find-the-heading-then-take-what-follows bound reads the page's own title
    block as its content.

    The region is therefore chosen by CONTENT, not position: of the page's four
    paragraph divs, the roster is the one carrying two or more e-mail addresses
    AND two or more <strong> names. The heading div has one <strong> and no
    e-mail; the two footer divs have neither. If the county ever reformats past
    that test this returns nothing and the count guard fails the county, which
    is the intended failure — a roster that silently shrinks is worse than one
    that stops.

    THE COUNTY'S WEBSITE AND ITS MAIL DOMAIN ARE DIFFERENT DOMAINS, WHICH IS
    WHY THIS COUNTY READ AS DARK FOR WEEKS. The commissioners' e-mails are on
    pulaskicountyil.gov; the website is pulaskicountyil.net. This project's
    standing method for finding a county site — permute the domain in the
    clerk's e-mail address, the Cumberland correction — lands on the .gov,
    which serves no page, and the gap record concluded "the county's website
    cannot be reached from here." It reads 200 with 26 KB of content on the
    .net, with a department page per office. A MAIL DOMAIN IS NOT A CLAIM
    ABOUT A WEBSITE: when the permutation fails, search for the county by
    name before recording it dark.

    AT-LARGE was already settled on this county's record from its certified
    2024 primary (platinumelectionresults.com, county id 19): one countywide
    commissioner contest per party over all eleven precincts, no
    district-suffixed contest anywhere. Nothing here re-proves it.

    THE ROSTER COMES FROM THE COUNTY'S PAGE, NEVER FROM THOSE RETURNS — the
    Scott rule: a return names who WON a contest, not who holds the seat
    today. That was the second half of this county's blocker, and the page
    answers it directly. The page is maintained: it carried
    `Last-Modified: Thu, 23 Jul 2026 16:53:05 GMT` when this parser was
    written, six weeks before. Its 2022-dated minutes and 2023 ordinance are
    ATTACHMENTS below the roster block, not evidence about the roster's age.

    E-MAILS SHIP because the county publishes one per commissioner. No phone
    ships: the page carries none for this body.
    """
    roster = None
    for candidate in re.finditer(
            r"(?is)<div class=\"paragraph\"[^>]*>(.*?)</div>", page):
        body = candidate.group(1)
        if (len(PULASKI_EMAIL_RE.findall(body)) >= 2
                and len(re.findall(r"(?is)<strong>", body)) >= 2):
            roster = body
            break
    if roster is None:
        return [], None
    members = []
    entry = None
    for part in re.split(r"(?i)<br\s*/?>", roster):
        strong = re.search(r"(?is)<strong>(.*?)</strong>", part)
        if strong:
            name = clean(strong.group(1))
            if not name:
                continue
            entry = {"name": name}
            if not any(x["name"] == name for x in members):
                members.append(entry)
            continue
        if entry is None:
            continue
        text = clean(part)
        if not text:
            continue
        email = PULASKI_EMAIL_RE.search(text)
        if email:
            entry["email"] = email.group(0)
            continue
        if "role" not in entry:
            canonical = role_of(text)
            if canonical:
                entry["role"] = canonical
            elif text.lower() == "secretary":
                # A board office this county names and the shared mapper does
                # not — kept verbatim here rather than widening role_of for
                # every county, exactly as Massac's parser does.
                entry["role"] = "Secretary"
    return members, None


# ------------------------------------------------- incomplete TLS chains
# THE COLES PATTERN, MET A SECOND TIME. gallatinco.illinois.gov answers 200 and
# renders perfectly in a browser, but serves ONLY its leaf certificate — the
# Sectigo intermediate that signs it is missing from the handshake. Browsers
# paper over that by fetching the issuer named in the leaf's own Authority
# Information Access extension; requests, curl and every other automated client
# do not, so they report "unable to get local issuer certificate" and the county
# reads as unreachable. Gallatin's gap record said the county was "DARK to this
# client on every route tried" for that reason alone.
#
# So the chase is done by scripts/aia_bundle.py — the fleet's ONE copy of the
# pinned-intermediate machinery (a pinned hash that exists in two files is a
# pin that drifts; this file carried its own copy until the 2026-08-24 scripts
# audit folded it back). A SITES entry that needs it names the intermediate's
# key in aia_bundle.INTERMEDIATES as `ca_bundle`; the fetch below verifies
# against the trusted roots PLUS that one pinned certificate. NOTHING HERE
# DISABLES VERIFICATION, and if the county fixes its chain this keeps working
# unchanged.


SITES = {
    # normalized county key (see build_county_commissioners.py) -> spec
    "GALLATIN": {
        "name": "Gallatin County",
        "url": "https://gallatinco.illinois.gov/departments/board/",
        "structure": "5 members elected countywide \u2014 no districts",
        "expect": 5,
        "parse": parse_gallatin,
        # gallatinco.illinois.gov omits its TLS intermediate; the pinned
        # Sectigo copy lives in aia_bundle.INTERMEDIATES under this key.
        "ca_bundle": "sectigo-ov-r40",
    },
    "SALINE": {
        "name": "Saline County",
        "url": "https://salinecounty.illinois.gov/county-board/",
        "structure": "13 members elected countywide \u2014 no districts",
        "expect": 13,
        "parse": parse_saline,
    },
    "MASSAC": {
        "name": "Massac County",
        "url": "https://www.massaccountyil.gov/county-commissioner/",
        "structure": "Commission form \u2014 3 commissioners elected countywide",
        "expect": 3,
        "parse": parse_massac,
    },
    "PULASKI": {
        "name": "Pulaski County",
        # NOT pulaskicountyil.gov, which carries the commissioners' MAIL and
        # serves no page. See parse_pulaski: the clerk-domain permutation this
        # project normally uses lands on the .gov and reads the county as dark.
        "url": "https://pulaskicountyil.net/pulaski-county-board.html",
        "structure": "Commission form — 3 commissioners elected countywide",
        "expect": 3,
        "parse": parse_pulaski,
    },
    "MONROE": {
        "name": "Monroe County",
        "url": "https://monroecountyil.gov/departments/board-of-commissioners/",
        "structure": "Commission form — 3 commissioners elected countywide",
        "expect": 3,
        "parse": parse_monroe,
    },
    "RANDOLPH": {
        "name": "Randolph County",
        "url": "https://randolphcountyil.gov/board-of-commissioners/",
        "structure": "Commission form — 3 commissioners elected countywide",
        "expect": 3,
        "parse": parse_randolph,
    },
    "MOULTRIE": {
        "name": "Moultrie County",
        "url": "https://www.moultriecountyil.gov/moultrie_county_board/board_members.php",
        "structure": "9 members elected countywide — no districts",
        "expect": 9,
        "parse": parse_moultrie,
    },
    "GREENE": {
        "name": "Greene County",
        "url": "https://greenecountyil.org/county-board/",
        "structure": "7 members elected countywide — no districts",
        "expect": 7,
        "parse": parse_greene,
    },
    "MORGAN": {
        "name": "Morgan County",
        # The .COM is the county's real content site; the .GOV is a
        # client-rendered shell that publishes no roster. See parse_morgan.
        "url": "https://morgancounty-il.com/wp/departments/county-commissioners/",
        "structure": "Commission form — 3 commissioners elected countywide",
        "expect": 3,
        "parse": parse_morgan,
    },
    "SCHUYLER": {
        "name": "Schuyler County",
        "url": "https://www.schuylercounty.org/county-board/county-board-members/",
        "structure": "7 members elected countywide",
        "expect": 7,
        "parse": parse_schuyler,
    },
    "PIKE": {
        "name": "Pike County",
        "url": "https://www.pikecountyil.org/county-boards/",
        "structure": "9 members elected countywide — no districts",
        "expect": 9,
        "parse": parse_pike,
    },
    "PUTNAM": {
        "name": "Putnam County",
        "url": "https://putnamil.gov/government/county_board/index.php",
        "structure": "5 members elected countywide — no districts",
        "expect": 5,
        "parse": parse_putnam,
    },
    "BROWN": {
        "name": "Brown County",
        # browncountyil.org is a captcha-parked DECOY, not the county.
        "url": "https://www.browncoil.org/county-board/",
        "structure": "7 members elected countywide — no districts",
        "expect": 7,
        "parse": parse_brown,
    },
    "CALHOUN": {
        "name": "Calhoun County",
        # The apex does not resolve; the www host is required.
        "url": "https://www.calhouncountyil.gov/government/county-board/members/",
        "structure": "Commission form — 5 commissioners elected countywide",
        "expect": 5,
        "parse": parse_calhoun,
    },
    "HAMILTON": {
        "name": "Hamilton County",
        # The county's NEW site (live 2026-08-05). At-large per Clerk Bowman
        # in writing the same day; see parse_hamilton's provenance note.
        "url": "https://www.hamiltoncountyil.gov/departments/county-board/",
        "structure": "5 members elected countywide — no districts",
        "expect": 5,
        "parse": parse_hamilton,
    },
}


FETCH_ATTEMPTS = 3


def fetch(session, url, verify=True):
    """GET with a bounded retry. Returns (response, error_or_None).

    WHY A RETRY EXISTS HERE (added 2026-08-08). There was none, and a single
    flaky response zeroed a county: several of these sites sit behind
    Cloudflare, and one bad fetch out of ten made that county parse 0 members,
    which the builder correctly refuses to write — so the WHOLE weekly refresh
    failed on one county's bad afternoon. Consecutive runs failed on Brown,
    then on Calhoun, then on neither, which is the signature of flake rather
    than of a page that changed.
    """
    # EVERY COUNTY'S RULES ARE READ BEFORE ITS FIRST PAGE, once per host, with
    # the identity this fetch sends — which for this file is a browser string,
    # and the client decides which robots group binds, so reading the policy as
    # anything else would answer a different question. The bundle this caller
    # verifies with is passed through, because two of these hosts serve a
    # leaf-only chain and their policy cannot be read without it.
    #
    # The two hosts whose recorded readings had shut this file out were both
    # re-measured from a GitHub runner on 2026-10-01, the vantage the weekly job
    # crawls from: salinecounty.illinois.gov serves a 126-byte policy and
    # www.calhouncountyil.gov a 127-byte one, neither matching any path read
    # here, on all three reads of a deliberate re-measurement fifteen seconds
    # apart. Both had been recorded as answering every client with a challenge.
    require_robots_once(url, UA["User-Agent"], headers=UA,
                        label="il-county-commissioners",
                        verify=None if verify is True else verify)
    last = None
    for attempt in range(FETCH_ATTEMPTS):
        try:
            resp = session.get(url, headers=UA, timeout=60, verify=verify)
            resp.raise_for_status()
            return resp, None
        except requests.RequestException as exc:
            last = exc
            if attempt + 1 < FETCH_ATTEMPTS:
                time.sleep(2 * (attempt + 1))
    return None, last



def build_from_returns(key, spec, session, fail):
    """One at-large county's sitting commissioners, from its certified canvasses.

    Walks general elections newest-first. A county with lettered seats keeps the
    newest winner of each seat; a county without them takes one winner per
    general until its seat count is filled, deduplicated by name because a
    re-elected member holds one seat rather than two.
    """
    year = datetime.date.today().year
    slugs = ["%d_ge" % y for y in range(year if year % 2 == 0 else year - 1,
                                        year - 12, -2)]
    seat_re = re.compile(spec["seat_pattern"], re.I) if spec.get("seat_pattern") else None
    contest_re = re.compile(spec.get("contest_pattern") or spec.get("seat_pattern"), re.I)

    members = []
    by_seat = {}
    seen_names = set()
    read = []
    for slug in slugs:
        text, size = platinum_canvass.fetch_report(slug, spec["countyId"], session)
        if not text:
            continue
        name = platinum_canvass.county_name(text)
        if not name:
            # An unreadable header is a report this parser should not trust —
            # skipped, never assumed to be the right county.
            continue
        if not name.upper().startswith(key):
            fail("%s: %s returned a report for %r, not this county" % (key, slug, name))
        found = platinum_canvass.contests(text)
        countywide = max((c["precincts"] or 0) for c in found) if found else 0
        read.append(slug)
        for contest in found:
            if not contest_re.search(contest["title"]) or not contest["candidates"]:
                continue
            # THE GATE: an at-large seat is voted in every precinct the canvass
            # reports for anything. A districted contest counts fewer.
            if not countywide or contest["precincts"] != countywide:
                fail("%s: %r was counted in %s of %d precincts — that is a DISTRICT "
                     "contest, and this county is on the at-large County card"
                     % (key, contest["title"][:60], contest["precincts"], countywide))
            winner = contest["candidates"][0]
            election = "elected %s (certified canvass)" % slug[:4]
            if seat_re:
                m = seat_re.search(contest["title"])
                if not m:
                    fail("%s: %r carries no seat letter" % (key, contest["title"][:60]))
                seat = m.group(1).upper()
                if seat in by_seat:
                    continue                      # an older election for a seat already filled
                by_seat[seat] = {"name": platinum_canvass.name_case(winner["name"]), "seat": "Seat " + seat,
                                 "party": winner["party"][:1], "since": int(slug[:4]),
                                 "districtSource": election}
            else:
                if winner["name"] in seen_names or len(members) >= spec["expect"]:
                    continue
                seen_names.add(winner["name"])
                members.append({"name": platinum_canvass.name_case(winner["name"]), "party": winner["party"][:1],
                                "since": int(slug[:4]), "districtSource": election})
    if seat_re:
        members = [by_seat[k] for k in sorted(by_seat)]
    if len(members) != spec["expect"]:
        fail("%s: composed %d commissioners from %r, expected %d"
             % (key, len(members), read, spec["expect"]))
    return members, read


def main():
    out = {}
    session = requests.Session()
    bundles = {}
    for key, spec in SITES.items():
        verify = True
        if spec.get("ca_bundle"):
            name = spec["ca_bundle"]
            if name not in bundles:
                bundles[name] = aia_bundle.ca_bundle("county-commissioners", name)
            verify = bundles[name]
        resp, err = fetch(session, spec["url"], verify)
        if resp is None:
            print("county-commissioners: WARN — %s unreadable after %d attempts (%s)"
                  % (key, FETCH_ATTEMPTS, err), file=sys.stderr)
            continue
        members, office = spec["parse"](resp.text)
        # ZERO is the flake signature, so it earns one more look: a page whose
        # SHAPE changed usually still yields some rows, while a challenge page
        # or a truncated response yields none. Re-fetching cannot hide a real
        # break — if it is still zero the WARN below fires and the builder
        # refuses to write, exactly as before.
        if not members and spec["expect"]:
            time.sleep(3)
            retry, _ = fetch(session, spec["url"], verify)
            if retry is not None:
                members, office = spec["parse"](retry.text)
                if members:
                    print("county-commissioners: %s parsed 0 on the first fetch and %d "
                          "on a re-fetch — transient, not a page change"
                          % (key, len(members)), file=sys.stderr)
        if not members and spec["expect"]:
            # A ZERO PARSE IS NOT AN EMPTY BOARD, and writing it as one is what
            # broke this refresh for sixteen days. None of these counties seats
            # zero commissioners, so zero means the response was not the page:
            # a challenge screen, an error, a truncation. Until 2026-08-18 an
            # unreadable county was SKIPPED (carried forward, below) while a
            # county that answered 200 with nothing usable was WRITTEN EMPTY —
            # the two opposite treatments for the same practical outcome, with
            # the worse one going to the case that looks fine. Calhoun parsed
            # five members by hand on the day this was written, from the same
            # URL and the same parser, which is what proves the page was never
            # the problem. Skipped now, and the diagnostic says WHAT ARRIVED
            # rather than guessing why.
            title = re.search(r"(?is)<title[^>]*>(.*?)</title>", resp.text)
            print("county-commissioners: WARN — %s answered HTTP %s with %d bytes "
                  "titled %r but yielded no members; treating it as unread and "
                  "carrying its last-good roster forward."
                  % (key, resp.status_code, len(resp.text),
                     clean(title.group(1))[:80] if title else "(no <title>)"),
                  file=sys.stderr)
            continue
        if len(members) != spec["expect"]:
            print("county-commissioners: WARN — %s parsed %d members, expected %d"
                  % (key, len(members), spec["expect"]), file=sys.stderr)
        if spec.get("enrich"):
            spec["enrich"](session, members, verify)
        out[key] = {
            "county": spec["name"],
            "structure": spec["structure"],
            "sourceUrl": spec["url"],
            "members": members,
        }
        # A board bigger than the list its county publishes. Carried so the card
        # can SAY a seat is unnamed; absent for every county that publishes all
        # of its members, which is all but one of them.
        if spec.get("seats"):
            out[key]["seats"] = spec["seats"]
        if office:
            out[key]["office"] = office

    for path in bundles.values():
        try:
            os.unlink(path)
        except OSError:
            pass

    # The counties with no website. Emitted without a fetch, and never quietly:
    # a hand-carried roster that ages is the failure mode this list invites, so
    # every run says which county, from which document, and how stale.
    for key, spec in DOCUMENT_ROSTERS.items():
        if key in out:
            print("county-commissioners: FAIL — %s is in both SITES and "
                  "DOCUMENT_ROSTERS; a county has one source, not two" % key,
                  file=sys.stderr)
            sys.exit(1)
        if len(spec["members"]) != spec["expect"]:
            print("county-commissioners: FAIL — %s carries %d members, expected %d"
                  % (key, len(spec["members"]), spec["expect"]), file=sys.stderr)
            sys.exit(1)
        age = ""
        try:
            verified = datetime.date.fromisoformat(spec["verified"])
            age = ", %d days old" % (datetime.date.today() - verified).days
        except Exception:
            pass
        print("county-commissioners: NOT RE-READ — %s has no website; its %d "
              "members come from %s%s. Re-ask the Clerk to refresh."
              % (key, len(spec["members"]), spec["document"], age), file=sys.stderr)
        out[key] = {
            "county": spec["name"],
            "structure": spec["structure"],
            "sourceDocument": spec["document"],
            "verified": spec["verified"],
            "members": spec["members"],
        }
        if spec.get("office"):
            out[key]["office"] = spec["office"]

    # The counties read from their own certified returns. Re-read every run, so
    # a new general election refreshes the board with nothing to hand-edit.
    for key, spec in RETURNS_ROSTERS.items():
        if key in out:
            print("county-commissioners: FAIL — %s is in more than one source "
                  "table; a county has one source, not two" % key, file=sys.stderr)
            sys.exit(1)

        def _fail(msg):
            print("county-commissioners: FAIL — " + msg, file=sys.stderr)
            sys.exit(1)

        members, read = build_from_returns(key, spec, session, _fail)
        print("county-commissioners: %s — %d commissioners from certified returns (%s)"
              % (key, len(members), ", ".join(read)), file=sys.stderr)
        out[key] = {
            "county": spec["name"],
            "structure": spec["structure"],
            "sourceDocument": "certified county canvasses, %s"
                              % platinum_canvass.RESULTS_HOME,
            "members": members,
        }
        if spec.get("office"):
            out[key]["office"] = spec["office"]

    if not out:
        print("county-commissioners: FAIL — no county parsed", file=sys.stderr)
        sys.exit(1)

    payload = json.dumps({"counties": out}, indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(payload)
        print("county-commissioners: %d counties (%d members) -> %s"
              % (len(out), sum(len(v["members"]) for v in out.values()), sys.argv[1]))
    else:
        print(payload)


if __name__ == "__main__":
    main()
