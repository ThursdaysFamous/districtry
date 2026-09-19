#!/usr/bin/env python3
"""
Scrape stage 1: which commissioner holds each Michigan county commissioner
district, read from each county's own board page, cached for
build_mi_commissioner_roster.py (stage 2).

WHY THIS EXISTS
----------------
mi/data/app/mi-commissioner-districts.json draws all 619 districts and names
nobody. The state's own layer carries a Commissioner and a Party on every
polygon, and build_mi_commissioner_districts.py drops both, because that
column holds the certified November 2024 election winners rather than the
people in office now. This file gets the names from the counties instead.

The column is not merely old. Measured against the six counties here on
2026-09-13, it names a DIFFERENT PERSON in 7 of 76 seats:

    Macomb 1     state: Don Brown          county: Ken Goike
    Muskegon 4   state: Dan Potts          county: Chris McGuigan
    Muskegon 5   state: Nicole Larson      county: Charles Nash
    Muskegon 6   state: Doug Brown         county: Jessica Cook
    Muskegon 7   state: Darrell L. Paige   county: Kimberly D. Sims
    Wayne 5      state: Irma Clark-Coleman county: Angelique Peterson-Mayberry
    Wayne 8      state: David Knezek       county: Hassan M. Ahmad

Wayne 5 is the seat whose named commissioner died on 10 June 2025. Sixteen
more seats differ only in how the name is written (Kent 2 "Elizabeth Morse"
against the county's "Liz Morse"; Saginaw 4 "Sheldon Mattews" against
"Sheldon Matthews", a typo in the state column). THE COUNTY PAGE WINS in every
case and the state column ships nowhere; stage 2 prints every disagreement so
the drift stays visible rather than being quietly resolved.

WHAT A TRANCHE IS
------------------
Michigan has 83 counties and no statewide roster, so the names arrive a
TRANCHE at a time: the counties whose own board page yields a district-keyed
roster to the client this scraper sends. Twenty-six counties yield today across
four shipping tranches, and ten more are recorded in PROBES below as tried and
not yielded — host, robots reading, what it answered, the date — so the next
tranche starts from measurements instead of guesses, and a county that changes
its file re-enters by itself on the weekly run.

THE ORDER CHANGED AFTER TRANCHE 3. The first three took the next counties by
POPULATION, and by tranche 3 that had stopped discriminating: the span ran
109K to 83K and the 59 untried counties held 18.1% of the state between them,
each buying under 1%. So tranche 4 measured WHETHER A COUNTY PUBLISHES A
DISTRICT-KEYED BOARD PAGE AT ALL, for all 59 at once and without writing a
parser (mi/scripts/probe_mi_county_boards.py,
mi/data/source/mi-county-board-probe.json), and shipped no county itself.
Tranche 5 is the first taken off that list.

A `candidate` VERDICT IS NOT A PROMISE, in either direction. Ten of the
probe's 34 candidates parsed on the first attempt; two of them — Gogebic and
Marquette — cannot be fetched at all, each serving a robots.txt that disallows
this client, both recorded below.

THE CLIENT, AND WHAT IT ASKS FIRST
-----------------------------------
Every host's robots.txt is read through scripts/robots_policy.py (via this
instance's robots_gate shim) with UA_ROSTER_BOT BEFORE its first page fetch —
every county site AND the state service the comparison reads, which is one
more host — and a stated Crawl-delay is honoured PER HOST by HostPacer, with
what it honoured printed at the end of every run. Midland states Crawl-delay:
15 and is the first county here to state one; pacing per host rather than
globally is what keeps the other fifteen at full speed. The county pages take
the STRICT reading of a 401/403 on robots.txt (`refused_is_refusal=True`,
the DuPage and Logan pattern): on a website that status is a firewall refusing
this client, where on an ArcGIS service it is the RFC's allow, so the state
service keeps the default.

No county here needs a browser user-agent: every one of the twenty-six serves
this token a full page. A county that refuses is skipped with its reason
printed and its page never requested; it stays in PROBES so the weekly run
re-asks and a county that changes its file re-enters by itself.

A TRANSPORT FAILURE IS RETRIED AND AN ANSWER IS NOT. co.hillsdale.mi.us resets
the connection on roughly one request in three from this project's sandbox and
serves the same file on the next try — its robots.txt read `unreachable` twice
and `served` on the third go — so the page fetch retries three times. A robots
refusal and an HTTP status are answers and are taken as given.

A captcha is an access control. Livingston and Ottawa answer HTTP 202 on
robots.txt itself — 202 is never a document — and nothing here tries to get
past that. Oakland's edge answers 403 to the districtry token AND to Chrome
126 with its client hints, so the refusal is of this client's stack rather
than its name and a browser string buys nothing.

WHAT EACH PARSER READS, AND THE TRAP IN IT
--------------------------------------------
Twenty-six counties and as many page shapes; each parser's own docstring
carries the trap it was written around. Every one pairs a district with a name
INSIDE ONE BLOCK rather than by document order, because several print the name
before the district and some print the role before the name. Tranche 1's six,
which set the pattern:

  Kalamazoo  CivicPlus staff directory. District is in the JOB TITLE field
             ("District 2 – Chair"), so the district and the role arrive
             together. The page carries a tenth p-name with no district — the
             board's administrative contact — and rows without a "District N"
             job title are dropped rather than numbered by position.
  Kent       CivicPlus staff directory, one widget per district: the district
             is the widget's own <h3> heading and the name is the p-name
             inside it. Its e-mails are CLOUDFLARE-OBFUSCATED, the markup that
             silently emptied Brown County's seven addresses, so the hex is
             decoded and markup-present-but-nothing-decoded is a hard failure.
  Macomb     The BOARD'S OWN SITE, bocmacomb.org, linked from the county's
             board page; macombgov.org's board page names nobody. Name and
             district sit in sibling columns whose CSS order is reversed
             (order-2 before order-1), so a flat read pairs them wrongly. Its
             index page carries no party; each member's OWN profile page does
             ("Ken Goike (R) District 1", read 2026-09-13). That is thirteen
             more fetches a week for one field and is left for a later tranche
             rather than taken now — recorded so it is a decision instead of an
             oversight.
  Muskegon   Hand-written editor HTML: <h2>DISTRICT N</h2><h3>Name (R)</h3>.
             The only county of the six publishing PARTY on its own page.
             HTML COMMENTS ARE STRIPPED FIRST: District 7's telephone is
             commented out, and a parser that ignores comments ships a number
             the county deliberately took down. Each block is BOUNDED at its
             own contact paragraph's </p>: District 7 is the last on the page,
             so a block that runs to the next <h2> runs to the end of the
             document instead, and District 7 picks up the county's general
             number from the section below. That is the trap twice in one
             county — a commented-out number and an unbounded last block, both
             producing a plausible telephone for a commissioner who publishes
             none.
  Saginaw    Card grid, name in the card title and district in a <strong>
             below it.
  Wayne      The roster exists ONLY in the commission section's navigation,
             which is a CMS page tree rather than a hand-built menu — every
             entry resolves to a live page and the district is in the slug
             ("...-Dist-5"). Checked against the Alexander trap on
             2026-09-13: all 15 slugs answer 200.

NO PARSER INFERS A DISTRICT FROM LIST ORDER. Each returns only the pairs its
own page states, and stage 2 refuses any county whose districts are not
exactly 1..N for the seat count the shipped geometry carries.

WHAT NEVER SHIPS. A home address (none of these six publishes one, and the
parsers read no address field at all). A party taken from the state column. A
name from anywhere but the county's own page.

Usage:
    python3 mi/scripts/mi_commissioner_scraper.py
    python3 mi/scripts/mi_commissioner_scraper.py --county Wayne
"""

import argparse
import base64
import html as _html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("mi-commissioner-scraper: FAIL — requests is not installed "
          "(pip install -c mi/scripts/requirements.txt requests)", file=sys.stderr)
    raise SystemExit(1)

from robots_gate import RobotsGate, HostPacer

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache", "mi_commissioner_roster.json")

# The fleet's own roster token (scripts/scraper_common.py's UA_ROSTER_BOT).
# Copied rather than imported: instance scripts resolve imports inside their
# own tree, and scripts/validate_workflow_deps.py fails a sys.path reach across
# trees. robots_gate.py is the one sanctioned exception, because
# validate_workflow_deps lists robots_policy in FLEET_SHARED.
UA_ROSTER_BOT = "districtry.com roster bot (civic data; contact via site)"

# The state's own district layer, queried for its Commissioner column ONLY so
# stage 2 can print where the county disagrees. Nothing from this query ships.
STATE_SERVICE = ("https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/"
                 "boundaries/MapServer/10")

TIMEOUT = 60


def txt(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def strip_comments(h):
    """Remove HTML comments before parsing. Muskegon comments out District 7's
    telephone; a parser that leaves comments in ships a number the county
    took down."""
    return re.sub(r"<!--.*?-->", " ", h or "", flags=re.S)


def cf_decode(hexstr):
    """Decode a Cloudflare-obfuscated e-mail token (data-cfemail /
    /cdn-cgi/l/email-protection#<hex>): first byte is the XOR key."""
    try:
        key = int(hexstr[:2], 16)
        out = "".join(chr(int(hexstr[i:i + 2], 16) ^ key)
                      for i in range(2, len(hexstr), 2))
    except (ValueError, IndexError):
        return None
    return out if "@" in out else None


def phone(raw):
    """A 10-digit US number as ###-###-####, or None. Michigan's six pages
    write it four ways (bare digits, +1-prefixed, punctuated, tel: href)."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:]) if len(digits) == 10 else None


# ---------------------------------------------------------------- parsers ---

def parse_kalamazoo(page):
    out = {}
    for blk in re.findall(r'<li class="widgetItem h-card">(.*?)</li>', page, re.S):
        name = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', blk, re.S)
        job = re.search(r'class="field p-job-title">(.*?)</div>', blk, re.S)
        if not (name and job):
            continue
        # "District 5 – Vice Chair": the district and the role in one field.
        keyed = re.match(r"District\s+(\d+)\s*(?:[–—-]\s*(.+))?$", txt(job.group(1)))
        if not keyed:
            continue          # the board's administrative contact, not a member
        rec = {"name": txt(name.group(1))}
        if keyed.group(2):
            rec["role"] = keyed.group(2).strip()
        tel = re.search(r'href="tel:([^"]+)"', blk)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[keyed.group(1)] = rec
    return out


def parse_kent(page):
    out, obfuscated, decoded = {}, 0, 0
    for blk in re.split(r'<div class="widgetHeader">', page)[1:]:
        head = re.search(r"<h3>(.*?)</h3>", blk, re.S)
        name = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', blk, re.S)
        if not (head and name):
            continue
        keyed = re.search(r"District\s+(\d+)", txt(head.group(1)))
        if not keyed:
            continue
        rec = {"name": txt(name.group(1))}
        job = re.search(r'class="field p-job-title">(.*?)</div>', blk, re.S)
        if job and txt(job.group(1)) and txt(job.group(1)) != "Commissioner":
            rec["role"] = txt(job.group(1))
        for hexstr in re.findall(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)", blk):
            obfuscated += 1
            addr = cf_decode(hexstr)
            if addr:
                decoded += 1
                rec.setdefault("email", addr)
        tel = re.search(r'href="tel:([^"]+)"', blk)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[keyed.group(1)] = rec
    if obfuscated and not decoded:
        raise ValueError("Kent: %d Cloudflare-obfuscated e-mail tokens and none decoded — "
                         "the obfuscation changed and every address would ship empty"
                         % obfuscated)
    return out


def parse_macomb(page):
    out = {}
    for blk in re.split(r'<div class="col-12 col-md-6 col-lg-4 post commissioner', page)[1:]:
        # The district's own <h3> and the name's own <p>, paired inside one
        # card. Their CSS order is reversed (order-2 carries the name, order-1
        # the district), so document order is not the reading order.
        keyed = re.search(r'<h3 class="mb-0">\s*District\s+(\d+)\s*</h3>', blk)
        name = re.search(r'<p class="byline">\s*(.*?)\s*</p>', blk, re.S)
        if not (keyed and name):
            continue
        rec = {"name": txt(name.group(1))}
        role = re.search(r'<span class="title-banner">\s*(.*?)\s*</span>', blk, re.S)
        if role and txt(role.group(1)):
            rec["role"] = txt(role.group(1))
        prof = re.search(r'href="(https://bocmacomb\.org/commissioners/[^"]+)"', blk)
        if prof:
            rec["profileUrl"] = prof.group(1)
        out[keyed.group(1)] = rec
    return out


PARTY = {"R": "Republican", "D": "Democratic", "I": "Independent"}


def parse_muskegon(page):
    out = {}
    for blk in re.finditer(r"<h2>\s*DISTRICT\s+(\d+)\s*</h2>\s*<h3>(.*?)</h3>(.*?)</p>",
                           page, re.S | re.I):
        district, heading, rest = blk.group(1), txt(blk.group(2)), blk.group(3)
        # "Kim Cyr (R)" — the only one of the six publishing party itself.
        # Read from the <h3>, never the image alt: District 3's alt misspells
        # the name the heading gives as Hazekamp.
        tagged = re.match(r"(.*?)\s*\((R|D|I)\)\s*$", heading)
        rec = {"name": tagged.group(1) if tagged else heading}
        if tagged:
            rec["party"] = PARTY[tagged.group(2)]
        mail = re.search(r'href="mailto:([^"?]+)"', rest)
        if mail:
            rec["email"] = mail.group(1).strip()
        tel = re.search(r'href="tel:([^"]+)"', rest)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[district] = rec
    return out


def parse_saginaw(page):
    out = {}
    for blk in re.split(r'<div class="card text-center h-100">', page)[1:]:
        name = re.search(r'<h3 class="card-title p-1">\s*(.*?)\s*</h3>', blk, re.S)
        keyed = re.search(r"<strong>\s*District\s+(\d+)\s*</strong>", blk)
        if not (name and keyed):
            continue
        rec = {"name": txt(name.group(1))}
        prof = re.search(r'href="(/departments/board-of-commissioners/'
                         r'commissioner-roster/[^"]+)"', blk)
        if prof:
            rec["profileUrl"] = "https://www.saginawcountymi.gov" + prof.group(1)
        out[keyed.group(1)] = rec
    return out


def parse_wayne(page):
    """Wayne's roster lives in the commission section's navigation and nowhere
    else — the page body is prose about what the commission does. That
    navigation is the CMS's own page tree, not a hand-built menu that could
    outlive its subjects: every slug was fetched on 2026-09-13 and all 15
    answered 200."""
    out = {}
    for m in re.finditer(r'href="(https://www\.waynecountymi\.gov/Government/Elected-Officials/'
                         r'Commission/Commissioners/[^"]*?-Dist-(\d+))"[^>]*>([^<]+)</a>', page):
        out[m.group(2)] = {"name": txt(m.group(3)), "profileUrl": m.group(1)}
    return out


# ---------------------------------------------------- tranche 2 parsers ---

ORDINAL_DISTRICT = re.compile(r"(\d+)(?:st|nd|rd|th)\s+District", re.I)


def parse_stclair(page):
    """Homepage-style TILES rather than a directory widget: each commissioner
    is an <a href="/Offices/NNN"> whose <h2> reads "District 1 - Steven
    Simasko". The district and the name arrive in one string, so there is no
    pairing to get wrong."""
    out = {}
    for block in re.finditer(r'<a\b[^>]*href="(/Offices/\d+)"[^>]*>(.*?)</a>', page, re.S):
        head = re.search(r"<h2>\s*District\s+(\d+)\s*-\s*(.*?)\s*</h2>", block.group(2), re.S)
        if not head:
            continue
        out[head.group(1)] = {
            "name": txt(head.group(2)),
            "profileUrl": "https://www.stclaircounty.org" + block.group(1),
        }
    return out


def parse_monroe(page):
    """CivicPlus staff directory, and BOTH of its fields carry two facts.

    `p-name` is "David Vensel (R)" — the party sits INSIDE the name, so a
    verbatim read ships it as part of a person's name. `p-job-title` is
    "Commissioner (District 6) (Chairman)" — the district AND the role
    together. The directory lists ELEVEN rows for a nine-seat board (the
    Administrator and a Deputy Clerk among them), so the job-title SHAPE is
    what keeps a non-member out; a count would not.

    DISTRICT 2 IS NOT NAMED AND IS NOT GUESSED. Measured 2026-09-13 and again
    2026-09-15, byte-identical: the county's own row for it is malformed —
    `p-name` reads "District 2" and `p-job-title` reads "Commissioner Vensel",
    where Vensel is District 6's chairman. So the row names no District 2
    commissioner and the only name on it belongs to another district. This
    parser therefore returns EIGHT, and `malformed` counts the rows it refused
    so a change on the county's side is visible either way: if the county fixes
    the row, District 2 appears on its own; if the row vanishes, the count
    drops to zero and the run says so.
    """
    out, malformed = {}, []
    for blk in re.findall(r'<li class="widgetItem h-card">(.*?)</li>', page, re.S):
        name_el = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', blk, re.S)
        job_el = re.search(r'class="field p-job-title">(.*?)</div>', blk, re.S)
        if not (name_el or job_el):
            continue
        raw_name = txt(name_el.group(1)) if name_el else ""
        job = txt(job_el.group(1)) if job_el else ""
        keyed = re.match(r"Commissioner\s*\(District\s+(\d+)\)\s*(?:\((.+?)\))?\s*$", job)
        if not keyed:
            # A row whose TITLE says Commissioner while its name field holds a
            # district label is the malformed case above, not a member.
            if re.match(r"Commissioner\b", job) or ORDINAL_DISTRICT.search(raw_name) \
                    or re.match(r"District\s+\d+\s*$", raw_name):
                malformed.append((raw_name, job))
            continue
        tagged = re.match(r"(.*?)\s*\((R|D|I)\)\s*$", raw_name)
        rec = {"name": tagged.group(1) if tagged else raw_name}
        if tagged:
            rec["party"] = PARTY[tagged.group(2)]
        if keyed.group(2):
            rec["role"] = keyed.group(2).strip()
        mail = re.search(r'href="mailto:([^"?]+)"', blk)
        if mail:
            rec["email"] = mail.group(1).strip()
        tel = re.search(r'href="tel:([^"]+)"', blk)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[keyed.group(1)] = rec
    if malformed:
        print("    Monroe: %d directory row(s) name a district and no person, "
              "refused: %s" % (len(malformed), "; ".join("%r / %r" % m for m in malformed)))
    return out


def parse_berrien(page):
    """Editor HTML, one block per commissioner:
    <h2 class="subhead1">David Vollrath</h2>
    <h3 class="subhead2">1st District Commissioner</h3>

    The district is ORDINAL, so a "District N" regex finds nothing here. The
    block's own profile link slugs a NICKNAME (/750/Dave-Vollrath for David
    Vollrath), so the heading is the name and the link is not.

    One name ships as the county prints it: District 9 reads "Alex R. ott",
    lowercase surname. It is published that way and is not silently corrected
    (the Carroll "Distirct" precedent)."""
    out = {}
    for block in re.finditer(r'<h2 class="subhead1[^"]*">\s*(.*?)\s*</h2>\s*'
                             r'<h3 class="subhead2[^"]*">\s*(.*?)\s*</h3>', page, re.S):
        name, sub = txt(block.group(1)), txt(block.group(2))
        keyed = ORDINAL_DISTRICT.search(sub)
        if name and keyed:
            out[keyed.group(1)] = {"name": name}
    return out


def parse_jackson(page):
    """Nav links carry both facts — "District 1 - Tony Bair" pointing at that
    member's own page — and District 5's link text badges the Chairman inside
    the same string, so the role is stripped off the name rather than left on
    it."""
    out = {}
    for block in re.finditer(r'<a\b[^>]*href="([^"]*?/\d+/District-\d+[^"]*)"[^>]*>\s*'
                             r'District\s+(\d+)\s*-\s*(.*?)\s*</a>', page, re.S):
        href, who = block.group(1), txt(block.group(3))
        rec = {"profileUrl": href if href.startswith("http")
               else "https://www.mijackson.org" + href}
        role = re.match(r"(Chairman|Chair|Vice[- ]Chair(?:man)?)\s+(.*)$", who, re.I)
        if role:
            rec["role"] = role.group(1)
            who = role.group(2).strip()
        rec["name"] = who
        out[block.group(2)] = rec
    return out


def parse_calhoun(page):
    """A two-column TABLE whose columns interleave districts 1-4 with 5-7. A
    flat read is safe only because every cell carries its own district anchor;
    reading by position would pair District 2 with District 5's member. The
    role follows a comma ("Derek King , Chair")."""
    out = {}
    for cell in re.finditer(r'#District(\d+)"[^>]*>\s*District\s+\d+\s*</a>\s*:?\s*(.*?)\s*</td>',
                            page, re.S):
        body = txt(cell.group(2)).lstrip(": ").strip()
        if not body:
            continue
        parts = [part.strip() for part in body.split(",")]
        rec = {"name": parts[0]}
        if len(parts) > 1 and parts[1]:
            rec["role"] = parts[1]
        out[cell.group(1)] = rec
    return out


# ------------------------------------------------------------- the tranche ---


# ------------------------------------------------------ tranche 3 parsers ---

def parse_eaton(page):
    """A hand-written <ul> in two editor widgets: `<li><a>Name</a>, District N</li>`,
    fifteen items across the two lists. THREE of the county's own defects are in
    it, and each one produced a confidently wrong first draft.

    THE NAME IS THE LAST NON-EMPTY ANCHOR, NEVER THE FIRST. Districts 12 and 15
    lead with an EMPTY anchor carrying the PREVIOUS member's slug —
    `<a href="/334/Brian-Lautzenheiser"></a><a href=".../334/Nicole-Christensen
    ---District-12">Nicole Christensen,</a>` — so reading anchor[0]'s href beside
    anchor[-1]'s text pairs a current member with their predecessor's page. The
    same page id serves both slugs, so nothing 404s to warn you.

    THE DISTRICT FIELD CAN CARRY A ROLE after a dash ("District 9 - Vice Chair",
    "District 13 - Chair"), so an anchored `District (\d+)$` match drops two of
    fifteen.

    AND THE COMMA CAN BE INSIDE THE ANCHOR ("<a>Jane M. Whitacre,</a> District
    6"), so the name needs its trailing comma stripped rather than the split
    being trusted.

    District 13's own href reads `/337/HIDDEN-Jim-Mott`; the name is in the link
    text and ships as the county prints it. No county e-mail or phone is
    published on this page for any member.
    """
    out = {}
    for li in re.findall(r"<li>(.*?)</li>", page, re.S):
        if "District" not in li:
            continue
        flat = txt(li)
        keyed = re.search(r",?\s*District\s+(\d+)\s*(?:[-\u2013]\s*(.+?))?\s*$", flat)
        if not keyed:
            continue
        anchors = [a for a in (txt(x) for x in
                               re.findall(r"<a\b[^>]*>(.*?)</a>", li, re.S)) if a]
        name = (anchors[-1] if anchors else flat[:keyed.start()]).rstrip(",").strip()
        if not name:
            continue
        rec = {"name": name}
        role = (keyed.group(2) or "").strip()
        if role:
            rec["role"] = role
        out[keyed.group(1)] = rec
    return out


def parse_lenawee(page):
    """CivicPlus staff directory with the district in a THIRD place: `p-name` is
    the name, `p-job-title` is the flat word "Commissioner" for all nine, and
    the district is an `<h3>District N</h3>` inside the `p-note` body beside a
    township list and a profession. Kalamazoo keys on job-title, Kent on the
    widget heading, Monroe on job-title in parentheses; this one is the note.

    TWO NON-MEMBERS SHARE THE WIDGET and are dropped by having no district in
    their note: an h-card for the office itself (`p-name` "Commissioners", a
    switchboard number) and the County Administrator.

    DISTRICT 8's MAILTO IS THE COUNTY ADMINISTRATOR'S ADDRESS. The card's link
    text reads "Email Comm Tillotson" while its href is
    `county.administrator@lenawee.mi.us`, where the other eight all use
    `comm.<surname>@`. That address is DROPPED rather than shipped under a
    commissioner's name, and never rewritten to the address the pattern
    suggests — inventing a working inbox for a named person is worse than
    shipping none (the Douglas rule, where a typo'd domain was dropped).
    """
    out, dropped = {}, []
    for li in re.findall(r'<li class="widgetItem h-card">(.*?)</li>', page, re.S):
        nm = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', li, re.S)
        note = re.search(r'class="field p-note">(.*?)</div>', li, re.S)
        if not nm:
            continue
        keyed = re.search(r"District\s+(\d+)", note.group(1)) if note else None
        if not keyed:
            continue
        rec = {"name": txt(nm.group(1))}
        email = re.search(r'mailto:([^"?]+)', li)
        if email:
            addr = email.group(1).strip()
            if addr.lower().startswith("county.administrator@"):
                dropped.append((keyed.group(1), addr))
            else:
                rec["email"] = addr
        tel = re.search(r'href="tel:([0-9+\-() .]+)"', li)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out[keyed.group(1)] = rec
    for dist, addr in dropped:
        print("  Lenawee District %s: dropped %s \u2014 the card labels it the "
              "commissioner's and it is the County Administrator's" % (dist, addr))
    return out


def parse_grandtraverse(page):
    """CivicPlus staff directory keyed on `p-job-title`, the Kalamazoo shape,
    with an e-mail for all nine.

    DISTRICT 8 FOLDS ITS ROLE INTO THE DISTRICT FIELD — "District 8, Board
    Chair" where the other eight read "District N" alone — so an anchored match
    silently ships eight of nine. The role is split off and kept rather than
    discarded with the row.
    """
    out = {}
    for li in re.findall(r'<li class="widgetItem h-card">(.*?)</li>', page, re.S):
        nm = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', li, re.S)
        job = re.search(r'class="field p-job-title">(.*?)</div>', li, re.S)
        if not (nm and job):
            continue
        keyed = re.match(r"District\s+(\d+)(?:\s*,\s*(.+))?$", txt(job.group(1)))
        if not keyed:
            continue
        rec = {"name": txt(nm.group(1))}
        role = (keyed.group(2) or "").strip()
        if role:
            rec["role"] = role
        email = re.search(r'mailto:([^"?]+)', li)
        if email:
            rec["email"] = email.group(1).strip()
        out[keyed.group(1)] = rec
    return out


def parse_lapeer(page):
    """A Revize FAQ ACCORDION: each district is a collapsible whose header is
    "District N" and whose body opens with the member's name, then "District N
    Lapeer County Commissioner", a telephone, an e-mail and the townships.

    THE E-MAILS ARE CLOUDFLARE-OBFUSCATED — `data-cfemail` rather than a
    mailto, the Brown County trap that emptied seven addresses while every count
    guard stayed satisfied — so they are decoded, and a run that finds the
    markup and decodes nothing is a failure rather than a roster with no
    contacts.

    The role follows a comma in the name ("Gary Howell, Chairman").

    THE HOST IS `lapeercountymi.gov` AND THAT IS NOT THE OBVIOUS ONE.
    `lapeercountyweb.org` resolves, answers 200, and is a DIFFERENT
    organisation whose site is a CATCH-ALL: measured 2026-09-15, its root, its
    /government path and a deliberately nonexistent path all return the same
    175,315 bytes with the same md5, so a 200 from it proves nothing and a
    scraper pointed there would report "answers, no roster" forever. The
    county's own e-mails are at a THIRD name, `@lapeercounty.org`, which serves
    an empty 2 KB page.
    """
    out, markup, decoded = {}, 0, 0
    for chunk in re.split(r'(?=<a class="faq-question-header")', page):
        head = re.match(r'<a class="faq-question-header"[^>]*>\s*District\s+(\d+)\s*</a>',
                        chunk)
        if not head:
            continue
        dist = head.group(1)
        body = strip_comments(chunk[head.end():])
        flat = txt(re.sub(r"<script.*?</script>", " ", body, flags=re.S))
        keyed = re.search(
            r"([A-Z][A-Za-z.'\- ]{2,40}?)\s*(?:,\s*(Chairman|Chair|Vice[- ]Chair(?:man)?))?"
            r"\s*District\s+%s\s+Lapeer County Commissioner" % dist, flat)
        if not keyed:
            continue
        rec = {"name": re.sub(r"\s+", " ", keyed.group(1)).strip()}
        role = (keyed.group(2) or "").strip()
        if role:
            rec["role"] = role
        tel = re.search(r"\b(\d{3}-\d{3}-\d{4})\b", flat)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        cf = re.search(r'data-cfemail="([0-9a-f]+)"', body)
        if cf:
            markup += 1
            addr = cf_decode(cf.group(1))
            if addr and "@" in addr:
                rec["email"] = addr
                decoded += 1
        out[dist] = rec
    if markup and not decoded:
        raise ValueError("Lapeer: %d data-cfemail present and none decoded \u2014 "
                         "the obfuscation changed shape" % markup)
    return out


def parse_midland(page):
    """The county's own CMS (`index.php?section=` paths; the roster is at
    /boc-people). Each member reads "<Name>Commissioner, District N" followed
    by a telephone and an Areas of Representation list.

    THE ROLE IS IN PARENTHESES INSIDE THE NAME ("Mark Bone (Chair)"), and the
    page's standing-committee block prints "Board of Commissioners, Chair"
    BEFORE any member's name — the Franklin grid trap, where a role sits in the
    column ahead of the row it belongs to — so the parse keys on each member's
    own "Commissioner, District N" string and never on document order.

    NON-BREAKING SPACES SIT INSIDE NAMES ("Jeanette\u00a0Snyder") and are
    normalised by txt().

    THIS HOST STATES `Crawl-delay: 15` and it is honoured per host by HostPacer
    rather than globally, so the other four counties in this tranche keep full
    speed.
    """
    out = {}
    flat = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    flat = re.sub(r"<[^>]+>", "|", flat)
    flat = _html.unescape(re.sub(r"(\s*\|\s*)+", "|", flat)).replace(u"\u00a0", " ")
    for m in re.finditer(r"\|([A-Z][^|]{2,40}?)\|?Commissioner,\s*District\s+(\d+)"
                         r"\|?\s*(\(\d{3}\)\s*\d{3}-\d{4})?", flat):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        rec = {}
        role = re.match(r"(.*?)\s*\((Chair|Chairman|Vice[- ]Chair(?:man)?)\)\s*$",
                        name, re.I)
        if role:
            name, rec["role"] = role.group(1).strip(), role.group(2)
        rec["name"] = name
        if m.group(3):
            tel = phone(m.group(3))
            if tel:
                rec["phone"] = tel
        out[m.group(2)] = rec
    return out


# ---------------------------------------------------- tranche 5 parsers ---
# Ten counties from the 2026-09-18 probe's candidate list
# (mi/data/source/mi-county-board-probe.json). The probe measured which
# counties publish a district-keyed board page at all; it never promised one
# would parse, and Gogebic and Marquette are the standing reminder — both
# scored `candidate` and neither can be fetched at all, each serving a
# robots.txt that disallows this client. They are in PROBES, not here.

def first_mailto(blk):
    """The FIRST mailto in a block. Cheboygan is why it is the first and not
    the last: District 4's visible address ends in a one-character anchor
    pointing at somebody else's address."""
    m = re.search(r'href="mailto:([^"?]+)', blk, re.I)
    return _html.unescape(m.group(1)).strip() if m else None


def first_phone(text):
    """The first 10-digit number in a run of text, as ###-###-####."""
    m = re.search(r"\(?\d{3}\)?[\s.-]\s*\d{3}[\s.-]\d{4}", text or "")
    return phone(m.group(0)) if m else None


# ------------------------------------------------------------------ 015 ---

def parse_barry(page):
    """A table, one <tr> per member. The LEFT cell carries a heading name and
    the district; the RIGHT cell carries "Commissioner <Name> (<party>)" and
    the mailto.

    THE COUNTY PRINTS TWO SPELLINGS OF ONE PERSON IN ONE ROW. District 6's
    left cell reads "Marcia A. Bassett" and its right cell "Commissioner Marsha
    A. Bassett (R)". Neither is a different person and neither cell is more
    recently edited than the other, so the parse takes the name from the cell
    that also carries the party and the address — the structured one — and the
    run PRINTS the disagreement rather than resolving it silently. The state's
    own canvassed column says Marsha, which is corroboration and not the
    reason.

    Home addresses are printed for four members and no address field is read.
    """
    out, disagree = {}, []
    for row in re.split(r"<tr[ >]", page)[1:]:
        keyed = re.search(r"District\s*#?\s*(\d{1,2})\b", txt(row))
        named = re.search(r"Commissioner\s+([^<(]{3,60}?)\s*(?:\(([A-Za-z]{1,12})\))?\s*<",
                          row)
        if not (keyed and named):
            continue
        name = txt(named.group(1)).strip(" ,")
        if not name:
            continue
        rec = {"name": name}
        party = named.group(2)
        if party:
            rec["party"] = {"R": "Republican", "D": "Democratic"}.get(party.upper(), party)
        head = re.search(r"font-size:\s*18pt;?[^>]*>\s*([^<]{3,60})", row)
        if head:
            heading = txt(head.group(1)).strip(" ,")
            role = re.search(r"\s*[-–]\s*(Chair(?:person|man)?|Vice[- ]Chair(?:person|man)?)\s*$",
                             heading, re.I)
            if role:
                rec["role"] = role.group(1)
                heading = heading[:role.start()].strip()
            if heading and heading != name:
                disagree.append((keyed.group(1), heading, name))
        addr = first_mailto(row)
        if addr:
            rec["email"] = addr
        tel = first_phone(txt(row))
        if tel:
            rec["phone"] = tel
        out.setdefault(keyed.group(1), rec)
    for district, heading, shipped in disagree:
        print("    Barry district %s: the row's heading reads %r and its "
              "commissioner line %r; %r ships" % (district, heading, shipped, shipped))
    return out


# ------------------------------------------------------------------ 031 ---

def parse_cheboygan(page):
    """<p><strong>District N - Name</strong><br />address<br />phone<br />
    <a mailto></p>, one paragraph per member.

    ONLY THE FIRST MAILTO IN A BLOCK IS READ. District 4's markup is
    <a href="mailto:teustice@...">teustice@cheboygancounty.ne</a><a
    href="mailto:cgouine@...">t</a> — the final letter of the visible address
    is its own anchor pointing at a DIFFERENT person. A parser taking the last
    mailto ships the wrong address for a commissioner, and the page looks
    correct to a reader. District 6 likewise prints two telephone numbers, and
    the first is the one under the name.

    Every member's HOME address is printed and no address field is read.
    """
    out = {}
    for blk in re.split(r"<p[ >]", page)[1:]:
        m = re.search(r"District\s*(\d{1,2})\s*(?:&#8211;|&ndash;|[–—-])\s*"
                      r"([^<]{3,60})</strong>", blk)
        if not m:
            continue
        rec = {"name": txt(m.group(2)).strip(" ,")}
        addr = first_mailto(blk)
        if addr:
            rec["email"] = addr
        tel = first_phone(txt(blk[m.end():]))
        if tel:
            rec["phone"] = tel
        out.setdefault(m.group(1), rec)
    return out


# ------------------------------------------------------------------ 043 ---

def parse_dickinson(page):
    """One <br />-separated line per member inside a single paragraph:
    "District #N   Name 906-774-0325[    Chairperson]".

    THE BLOCK IS BOUNDED AT ITS OWN <br />. The Controller/Administrator and
    his e-mail address follow District 5 in the same paragraph, so a block that
    runs to the paragraph's end gives District 5 a telephone and an address
    belonging to a member of staff who is not a commissioner.
    """
    out = {}
    flat = _html.unescape(re.sub(r"<(?!br|/p)[^>]*>", "", page))
    for line in re.split(r"<br\s*/?>|</p>", flat, flags=re.I):
        line = re.sub(r"\s+", " ", line).strip()
        m = re.match(r"District\s*#?\s*(\d{1,2})\s+(.+)$", line)
        if not m:
            continue
        rest = m.group(2)
        tel = first_phone(rest)
        name = re.split(r"\(?\d{3}\)?[\s.-]\s*\d{3}[\s.-]\d{4}", rest)[0].strip(" ,")
        if not name:
            continue
        rec = {"name": name}
        if tel:
            rec["phone"] = tel
        role = re.search(r"(Chair(?:person|man)?|Vice[- ]Chair(?:person|man)?)\s*$",
                         rest.strip(), re.I)
        if role:
            rec["role"] = role.group(1)
        out.setdefault(m.group(1), rec)
    return out


# ------------------------------------------------------------------ 059 ---

def parse_hillsdale(page):
    """<h2>District N</h2> then a paragraph of <span class="field-value">
    lines: name, home address, telephone, e-mail, photo.

    THE E-MAIL IS BASE64 INSIDE A <joomla-hidden-mail> ELEMENT, the Brown
    County shape in a third encoding after Cloudflare's hex: the address is in
    the `text` attribute. Markup present and nothing decoded is a hard failure,
    the same rule the Kent and Lapeer parsers already take, because a silently
    contactless roster is what that trap produces.
    """
    out, hidden, decoded = {}, 0, 0
    blocks = re.split(r"<h2>", page)[1:]
    for blk in blocks:
        head = re.match(r"\s*([^<]{1,40})</h2>", blk)
        if not head:
            continue
        keyed = re.match(r"\s*District\s*#?\s*(\d{1,2})\s*$", txt(head.group(1)))
        if not keyed:
            continue
        body = blk[head.end():]
        values = re.findall(r'class="field-value\s*"\s*>(.*?)</span>', body, re.S)
        if not values:
            continue
        name = txt(values[0]).strip(" ,")
        if not name:
            continue
        rec = {"name": name}
        # DISTRICTS 1 AND 2 PRINT THE COUNTY SWITCHBOARD WITH AN EXTENSION
        # ("(517) 437-7758 Ext: 861", "517-437-7758 x864") and the other three
        # print a direct line. The card builds its tel: href from the digits,
        # so an extension either breaks the dialled number or is dropped and
        # leaves a switchboard number standing as the commissioner's own. Both
        # are worse than no number, so a number carrying an extension is not
        # read and the e-mail is the contact for those two.
        for value in values[1:]:
            line = txt(value)
            if not first_phone(line):
                continue
            if re.search(r"\b(?:ext\.?|extension|x)\s*:?\s*\d{1,5}\b", line, re.I):
                break
            rec["phone"] = first_phone(line)
            break
        for enc in re.findall(r'<joomla-hidden-mail\b[^>]*\btext="([^"]+)"', body):
            hidden += 1
            try:
                addr = base64.b64decode(enc + "===").decode("utf-8", "strict")
            except Exception:                                     # noqa: BLE001
                continue
            if "@" in addr:
                decoded += 1
                rec.setdefault("email", addr.strip())
        out.setdefault(keyed.group(1), rec)
    if hidden and not decoded:
        raise ValueError("Hillsdale: %d joomla-hidden-mail elements and none "
                         "decoded — the encoding moved" % hidden)
    return out


# ------------------------------------------------------------------ 067 ---

def parse_ionia(page):
    """<h4>District #N</h4> then <p><a mailto>Name</a><br />home address<br />
    telephone</p>, three members per row.

    DISTRICT 3 READS "Vacant" AND THE PREVIOUS COMMISSIONER'S WHOLE BLOCK IS
    STILL THERE, COMMENTED OUT — name, e-mail, address and telephone. Comments
    are stripped before parsing (the Muskegon rule), so the seat reads vacant;
    a parser that leaves them in ships Lawrence Stewart Tiejema for a seat the
    county says nobody holds.

    The e-mail addresses are HTML-entity-encoded and three of them are personal
    accounts, which is what the county publishes as the way to reach those
    commissioners. Home addresses are printed for every member and no address
    field is read.
    """
    out = {}
    for blk in re.split(r"<h4>", page)[1:]:
        head = re.match(r"\s*District\s*#?\s*(\d{1,2})\s*</h4>", blk)
        if not head:
            continue
        body = blk[head.end():blk.find("</p>") + 1 if "</p>" in blk else len(blk)]
        if re.search(r"\bVacant\b", txt(body), re.I) and not re.search(r"mailto:", body):
            out.setdefault(head.group(1), {"vacant": True})
            continue
        named = re.search(r'href="mailto:[^"]*"[^>]*>\s*(?:<strong>)?\s*([^<]{3,60})', body)
        if not named:
            continue
        rec = {"name": txt(named.group(1)).strip(" ,")}
        addr = first_mailto(body)
        if addr:
            rec["email"] = addr
        role = re.search(r"<em>\s*([^<]{3,30})\s*</em>", body)
        if role and re.search(r"chair", role.group(1), re.I):
            rec["role"] = txt(role.group(1))
        tel = first_phone(txt(body))
        if tel:
            rec["phone"] = tel
        out.setdefault(head.group(1), rec)
    return out


# ------------------------------------------------------------------ 079 ---

def parse_kalkaska(page):
    """The board's own section menu, one <a> per district reading
    "District #N <Name>".

    THE SLUG IS NOT THE NAME. District 4's href is
    .../james_sweet_4.php and its link text is "District #4 David Persons" —
    the Eaton trap in a different place, a live page still slugged for the
    member before this one. So the text is the roster and the slug is read for
    nothing, and no profile link ships for this county: a URL carrying one
    person's name under another person's card is the kind of quiet wrongness
    this pipeline exists to avoid.
    """
    out = {}
    for href, label in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>\s*(District[^<]{3,70})</a>',
                                  page, re.I):
        m = re.match(r"District\s*#?\s*(\d{1,2})\s+(.{3,50})$", txt(label))
        if not m:
            continue
        out.setdefault(m.group(1), {"name": m.group(2).strip(" ,")})
    return out


# ------------------------------------------------------------------ 089 ---

def parse_leelanau(page):
    """<li>District #N, Name</li>, seven list items.

    THE ONLY E-MAIL ON THE PAGE IS COLLECTIVE — boc@leelanau.gov reaches all
    seven commissioners and the county administrator — so no address is
    attached to a person. Per-member contact lives in the county's separate
    staff directory, which this parser does not read.
    """
    out = {}
    for item in re.findall(r"<li>(.*?)</li>", page, re.S):
        m = re.match(r"District\s*#?\s*(\d{1,2})\s*,\s*(.{3,50})$", txt(item))
        if not m:
            continue
        out.setdefault(m.group(1), {"name": m.group(2).strip(" ,")})
    return out


# ------------------------------------------------------------------ 127 ---

def parse_oceana(page):
    """<li class="boc-member"> with the district in a <span class="district">
    and the name in the <h3> beneath it."""
    out = {}
    for blk in re.split(r'<li class="boc-member', page)[1:]:
        keyed = re.search(r'class="district[^"]*"[^>]*>\s*District\s*#?\s*(\d{1,2})\s*<', blk)
        named = re.search(r"<h3>\s*([^<]{3,60})\s*</h3>", blk)
        if not (keyed and named):
            continue
        rec = {"name": txt(named.group(1)).strip(" ,")}
        addr = first_mailto(blk)
        if addr:
            rec["email"] = addr
        tel = re.search(r'href="tel:([^"]+)"', blk)
        if tel and phone(tel.group(1)):
            rec["phone"] = phone(tel.group(1))
        out.setdefault(keyed.group(1), rec)
    return out


# ------------------------------------------------------------------ 133 ---

def parse_osceola(page):
    """Hand-written editor HTML, each member between <hr /> rules:
    District #N / Name[, Role] / mailto / telephone / home address /
    "Represents ..." .

    THE BOLD RUNS ARE THE KEY, NOT THE SPAN ORDER. Districts 1 and 2 are
    written <strong><span>District #N</span></strong> and districts 3 to 7
    <span><strong>District #N</strong></span>, so a parse keyed on one nesting
    reads three of the seven and looks like a page that only publishes three.

    DISTRICT 3's MAILTO CONTRADICTS ITS OWN LINK TEXT — the href is
    3district@osceolacountymi.com and the visible text is
    districtthree@osceolacountymi.com, on a .com domain where the other six
    members use .gov. Two addresses for one person on one line, neither
    checkable, so this district ships with no e-mail rather than with a guess.

    Every member's home address is printed and no address field is read.
    """
    out = {}
    for blk in re.split(r"<hr\s*/?>", page, flags=re.I):
        bolds = [txt(b) for b in re.findall(r"<strong>(.*?)</strong>", blk, re.S)]
        bolds = [b for b in bolds if b]
        keyed = None
        for i, b in enumerate(bolds):
            m = re.match(r"District\s*#?\s*(\d{1,2})\s*$", b)
            if m and i + 1 < len(bolds):
                keyed, label = m.group(1), bolds[i + 1]
                break
        if not keyed:
            continue
        rec = {}
        role = re.search(r",\s*(Chair(?:person|man)?|Vice[- ]Chair(?:person|man)?)\s*$",
                         label, re.I)
        if role:
            rec["role"] = role.group(1)
            label = label[:role.start()].strip(" ,")
        if not label:
            continue
        rec["name"] = label
        href = re.search(r'href="mailto:([^"?]+)"[^>]*>\s*([^<]*)', blk, re.I)
        if href:
            linked = _html.unescape(href.group(1)).strip()
            shown = txt(href.group(2)).strip()
            if shown and "@" in shown and shown.lower() != linked.lower():
                print("    Osceola district %s: the mailto is %r and the link text "
                      "%r; neither ships" % (keyed, linked, shown))
            else:
                rec["email"] = linked
        tel = first_phone(txt(blk))
        if tel:
            rec["phone"] = tel
        out.setdefault(keyed, rec)
    return out


# ------------------------------------------------------------------ 151 ---

def parse_sanilac(page):
    """The page's own button list, one <a> per district reading
    "District N <Name>" and linking to district_N_commissioner.php.

    THE SLUG IS A SECOND WITNESS HERE, unlike Kalkaska's: the number in the
    href and the number in the link text must agree or the pair is dropped,
    which is a free check on a page whose names sit two to a line.
    """
    out = {}
    for m in re.finditer(r'<a href=\s*"([^"]*?district_(\d{1,2})_commissioner\.php)"[^>]*>\s*'
                         r"([^<]{5,70})</a>", page, re.I):
        slug_district = m.group(2)
        label = txt(m.group(3))
        keyed = re.match(r"District\s*#?\s*(\d{1,2})\s+(.{3,50})$", label)
        if not keyed or keyed.group(1) != slug_district:
            continue
        out.setdefault(slug_district, {"name": keyed.group(2).strip(" ,")})
    return out

COUNTIES = (
    {"fips": "077", "county": "Kalamazoo", "seats": 9, "parse": parse_kalamazoo,
     "url": "https://www.kalcounty.gov/479/Board-of-Commissioners"},
    {"fips": "081", "county": "Kent", "seats": 21, "parse": parse_kent,
     "url": "https://www.kentcountymi.gov/1464/Meet-the-Commissioners"},
    {"fips": "099", "county": "Macomb", "seats": 13, "parse": parse_macomb,
     "url": "https://bocmacomb.org/find-your-commissioner/"},
    {"fips": "121", "county": "Muskegon", "seats": 7, "parse": parse_muskegon,
     "url": "https://co.muskegon.mi.us/1965/Your-Muskegon-County-Commissioners"},
    {"fips": "145", "county": "Saginaw", "seats": 11, "parse": parse_saginaw,
     "url": "https://www.saginawcountymi.gov/departments/board-of-commissioners/"},
    {"fips": "163", "county": "Wayne", "seats": 15, "parse": parse_wayne,
     "url": "https://www.waynecountymi.gov/Government/Elected-Officials/Commission"},
    # --- tranche 2, 2026-09-15: the next five by population that yielded ---
    {"fips": "021", "county": "Berrien", "seats": 12, "parse": parse_berrien,
     "url": "https://www.berriencounty.org/735/Meet-Your-Commissioners"},
    {"fips": "025", "county": "Calhoun", "seats": 7, "parse": parse_calhoun,
     "url": "https://www.calhouncountymi.gov/departments/board_of_commissioners/index.php"},
    {"fips": "075", "county": "Jackson", "seats": 9, "parse": parse_jackson,
     "url": "https://www.mijackson.org/365/Jackson-County-Commissioners"},
    {"fips": "115", "county": "Monroe", "seats": 9, "parse": parse_monroe,
     "url": "https://www.co.monroe.mi.us/374/Board-of-Commissioners"},
    {"fips": "147", "county": "St. Clair", "seats": 7, "parse": parse_stclair,
     "url": "https://www.stclaircounty.org/SubHome/Index/620"},
    # --- tranche 3, 2026-09-15: the next five by population that yielded ---
    {"fips": "045", "county": "Eaton", "seats": 15, "parse": parse_eaton,
     "url": "https://www.eatoncounty.org/295/Board-of-Commissioners"},
    {"fips": "055", "county": "Grand Traverse", "seats": 9, "parse": parse_grandtraverse,
     "url": "https://www.gtcountymi.gov/184/Board-of-Commissioners"},
    {"fips": "087", "county": "Lapeer", "seats": 7, "parse": parse_lapeer,
     "url": "https://lapeercountymi.gov/government/board_of_commissioners/index.php"},
    {"fips": "091", "county": "Lenawee", "seats": 9, "parse": parse_lenawee,
     "url": "https://www.lenawee.mi.us/896/Commissioners"},
    {"fips": "111", "county": "Midland", "seats": 7, "parse": parse_midland,
     "url": "https://midlandcountymi.gov/boc-people"},
    # --- tranche 5, 2026-09-19: ten counties off the probe's candidate list ---
    {"fips": "015", "county": "Barry", "seats": 8, "parse": parse_barry,
     "url": "https://www.barrycounty.org/departments_and_officials/officials/"
            "board_of_commissioners/index.php"},
    {"fips": "031", "county": "Cheboygan", "seats": 7, "parse": parse_cheboygan,
     "url": "https://www.cheboygancounty.net/government/board-of-commissioners-boc/"},
    {"fips": "043", "county": "Dickinson", "seats": 5, "parse": parse_dickinson,
     "url": "https://dickinsoncountymi.gov/government/county_departments/"
            "board_of_commissioners/index.php"},
    {"fips": "059", "county": "Hillsdale", "seats": 5, "parse": parse_hillsdale,
     "url": "https://co.hillsdale.mi.us/index.php/tm-gov/m-boc"},
    {"fips": "067", "county": "Ionia", "seats": 7, "parse": parse_ionia,
     "url": "https://www.ioniacounty.org/departments-officials/board-of-commissioners/"},
    {"fips": "079", "county": "Kalkaska", "seats": 7, "parse": parse_kalkaska,
     "url": "https://kalkaskacounty.net/government/board_of_commissioners/index.php"},
    {"fips": "089", "county": "Leelanau", "seats": 7, "parse": parse_leelanau,
     "url": "https://leelanau.gov/leelanau_county/board_of_commissioners/index.php"},
    {"fips": "127", "county": "Oceana", "seats": 5, "parse": parse_oceana,
     "url": "https://oceana.mi.us/government/board-of-commissioners/"},
    {"fips": "133", "county": "Osceola", "seats": 7, "parse": parse_osceola,
     "url": "https://osceolacountymi.gov/residents/county_commissioners/index.php"},
    {"fips": "151", "county": "Sanilac", "seats": 7, "parse": parse_sanilac,
     "url": "https://sanilaccounty.gov/government/commissioners/index.php"},
)

# Every county tried in tranche 1, measured 2026-09-13 from this project's
# sandbox with UA_ROSTER_BOT, robots.txt read first in every case. The six
# above are the ones that yielded; these six are the ones that did not, and
# each says what stopped it rather than "no page found". Re-measure before
# writing any of them off again — a robots file changes, an edge rule is
# lifted, a county moves CMS.
PROBES = (
    {"county": "Oakland", "fips": "125", "seats": 19,
     "host": "www.oakgov.com",
     "robots": "refused — HTTP 403 from the site's own edge (server: AkamaiGHost, "
               "errors.edgesuite.net reference), not from this sandbox's proxy",
     "answered": "403 on / as well, to UA_ROSTER_BOT and to Chrome/126 with its "
                 "client hints alike — the stack is refused, not the token, so a "
                 "browser string buys nothing",
     "date": "2026-09-13"},
    {"county": "Genesee", "fips": "049", "seats": 9,
     "host": "www.geneseecountymi.gov (and www.gc4me.com)",
     "robots": "served — one `*` group, `Disallow: /` (line 18). gc4me.com serves a "
               "second file allowing only *.pdf/*.DOC/*.DOCX/*.PPT/*.PPTX and "
               "disallowing / (line 22)",
     "answered": "not fetched. The document allowances on gc4me.com do not help: "
                 "finding a roster PDF means reading the HTML that links it, and "
                 "that is the part the file refuses",
     "date": "2026-09-13"},
    {"county": "Ingham", "fips": "065", "seats": 15,
     "host": "www.ingham.org",
     "robots": "served — one `*` group, `Disallow: /` (line 18)",
     "answered": "not fetched",
     "date": "2026-09-13"},
    {"county": "Ottawa", "fips": "139", "seats": 11,
     "host": "www.miottawa.org",
     "robots": "challenge — robots.txt itself answers HTTP 202 in 169 bytes "
               "(the sgcaptcha shape). 202 is never a document",
     "answered": "not fetched. A captcha is an access control and this project "
                 "does not route around one",
     "date": "2026-09-13"},
    {"county": "Livingston", "fips": "093", "seats": 9,
     "host": "www.livgov.com",
     "robots": "challenge — robots.txt itself answers HTTP 202, same shape as Ottawa",
     "answered": "not fetched",
     "date": "2026-09-13"},
    {"county": "Allegan", "fips": "005", "seats": 5,
     "host": "www.allegancounty.org and the apex allegancounty.org",
     "robots": "refused — HTTP 403 from the site's own edge (server: AkamaiGHost) on "
               "robots.txt, to UA_ROSTER_BOT and to Chrome/126 with its client hints "
               "alike. Under the strict reading county websites take, that is a refusal",
     "answered": "403 on / as well, to both client strings, on both hosts — so the "
                 "stack is refused rather than the token and a browser string buys "
                 "nothing. The Oakland shape exactly",
     "date": "2026-09-15"},
    {"county": "Bay", "fips": "017", "seats": 7,
     "host": "www.baycountymi.gov (and co.bay.mi.us)",
     "robots": "served — no group binds this client, nothing disallowed. "
               "co.bay.mi.us resolves to a DIFFERENT server whose robots.txt is "
               "UNREACHABLE, which is disallow-all, so it was never fetched",
     "answered": "200, and the roster is not keyable. The board's own Members "
                 "page names NOBODY — prose about the Public Act 139 model, "
                 "an address and a Board Advisor description — while the board "
                 "index names only three OFFICERS with no district for any of "
                 "them (Chairman Tim Banaszak, Vice Chair Vaughn Begick, "
                 "Sergeant at Arms Kathy Niemiec) on a seven-seat board. The "
                 "districts page is seven map links; the 1.4 MB meeting-results "
                 "page names none of the three and carries no roll call. The "
                 "boc. and commissioners. subdomains are a DNS WILDCARD — a "
                 "name that cannot exist resolves identically — and the "
                 "wildcard's own robots.txt disallows. Three names with no "
                 "district key cannot go on a district card (the Christian "
                 "County shape)",
     "date": "2026-09-15"},
    # --- measured 2026-09-19, while promoting the probe's candidates ---
    {"county": "Gogebic", "fips": "053", "seats": 7,
     "host": "gogebiccountymi.gov",
     "robots": "refused \u2014 served, 210 bytes, five named crawlers allowed "
               "(Googlebot, Bingbot, FacebookBot, LinkedInBot/1.0, Twitterbot) "
               "and then `User-agent: *` / `Disallow: /` on line 18. Read three "
               "times in a row, identical each time",
     "answered": "not fetched. THE PROBE RECORDED THIS COUNTY AS A CANDIDATE ON "
                 "2026-09-18 having read robots first, so either the file changed "
                 "inside a day or that read differed, and which is not established "
                 "\u2014 the Internet Archive holds no snapshot of either host's "
                 "robots.txt since 2026-09-01. The probe records a robots status "
                 "only for the hosts it REJECTS, never for the one it accepts, "
                 "which is why the two readings cannot be compared. Byte-identical "
                 "to Genesee's and Ingham's files, `Disallow: /` on line 18 in all "
                 "three",
     "date": "2026-09-19"},
    {"county": "Marquette", "fips": "103", "seats": 6,
     "host": "co.marquette.mi.us",
     "robots": "refused \u2014 the same 210-byte file as Gogebic's, byte for byte, "
               "read three times in a row",
     "answered": "not fetched. Recorded `candidate` by the probe on 2026-09-18 on "
                 "the same day as Gogebic and unreadable on the same day as "
                 "Gogebic, which is what makes a file change the likelier of the "
                 "two explanations without settling it",
     "date": "2026-09-19"},
    {"county": "Washtenaw", "fips": "161", "seats": 9,
     "host": "www.washtenaw.org",
     "robots": "served — no rule in the binding `*` group matches, Crawl-delay 20",
     "answered": "200, and the roster is not keyable. www.washtenaw.org/commissioners "
                 "lists District 1-9 with a free-prose bio under each and no name "
                 "field; the bios name the commissioner in seven different sentence "
                 "shapes and District 8's does not begin with the name at all. The "
                 "per-district pages (/district-N) carry the district as their only "
                 "heading and no name. Taking a name out of that prose would be a "
                 "guess, so Washtenaw ships nothing",
     "date": "2026-09-13"},
)


def ua_session():
    s = requests.Session()
    s.headers["User-Agent"] = UA_ROSTER_BOT
    s.headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
    return s


def state_commissioners(session, gate, pacer, fips_list):
    """The state layer's own Commissioner column, for the comparison stage 2
    prints. Never shipped — see the module docstring.

    ROBOTS IS READ HERE TOO. The rule is every host before its first fetch,
    and this is a different host from the six county sites. It is an ArcGIS
    service rather than a website, so it takes the RFC's default reading of a
    401/403 (allow) rather than the strict one the county pages opt into;
    measured 2026-09-13, gisagocss.state.mi.us answers 404 on robots.txt, so
    the verdict is `absent` and allow. A refusal skips the COMPARISON and
    never the roster."""
    where = "CountyFIPS IN (%s)" % ",".join("'%s'" % f for f in fips_list)
    url = STATE_SERVICE + "/query"
    params = {"where": where, "outFields": "CountyFIPS,DistrictName,Commissioner",
              "returnGeometry": "false", "f": "json", "resultRecordCount": 1000}
    out = {}
    allowed, why = gate.allows(url)
    if not allowed:
        print("  state column not read — robots %s: %s. The comparison is "
              "skipped, the roster is not" % (gate.verdict(url).status, why))
        return out
    try:
        with pacer.hold(url):
            data = session.get(url, params=params, timeout=TIMEOUT).json()
    except Exception as exc:                                  # noqa: BLE001
        print("  state column unavailable (%s) — the comparison is skipped, "
              "the roster is not" % exc)
        return out
    for feat in data.get("features", []):
        att = feat.get("attributes", {})
        num = re.search(r"(\d+)", att.get("DistrictName") or "")
        if num:
            out.setdefault(att["CountyFIPS"], {})[num.group(1)] = att.get("Commissioner")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--county", help="scrape one county by name")
    args = ap.parse_args()

    wanted = [c for c in COUNTIES
              if not args.county or c["county"].lower() == args.county.lower()]
    if not wanted:
        print("mi-commissioner-scraper: FAIL — no county named %r; known: %s"
              % (args.county, ", ".join(c["county"] for c in COUNTIES)), file=sys.stderr)
        return 1

    session = ua_session()
    gate = RobotsGate(session, UA_ROSTER_BOT)
    pacer = HostPacer(gate)

    entries, refused = {}, []
    for spec in wanted:
        url, county = spec["url"], spec["county"]
        verdict = gate.verdict(url)
        # THE STRICT READING, opted into by argument the way the DuPage and
        # Logan municipal scrapers do. RFC 9309 files a 401/403 on robots.txt
        # with a 404 and allows, which is right for the APIs that answer that
        # way (every ArcGIS FeatureServer); these are county WEBSITES, where a
        # 403 on robots.txt is a firewall refusing this client and fetching the
        # page anyway is walking past a no. Moot on all six counties today —
        # every one serves its file — and it decides what happens the day a
        # county now in PROBES is promoted into COUNTIES.
        allowed, why = verdict.allows(UA_ROSTER_BOT, url, refused_is_refusal=True)
        if not allowed:
            refused.append((county, why))
            print("  %-10s SKIPPED — robots %s: %s" % (county, verdict.status, why))
            continue
        resp, last = None, None
        # A TRANSPORT FAILURE IS NOT A MEASUREMENT. co.hillsdale.mi.us resets
        # the connection on roughly one request in three from this project's
        # sandbox and serves the same page on the next try; a single failure
        # recorded as "county did not yield" is how a county that publishes its
        # board stays unread. Only the transport is retried — a robots refusal
        # and an HTTP status are answers and are taken as given.
        for attempt in range(3):
            try:
                with pacer.hold(url):
                    resp = session.get(url, timeout=TIMEOUT)
                break
            except Exception as exc:                          # noqa: BLE001
                last = exc
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        if resp is None:
            print("  %-10s FETCH FAILED after 3 tries — %s" % (county, last))
            continue
        if resp.status_code != 200:
            print("  %-10s HTTP %s (%d bytes)" % (county, resp.status_code, len(resp.content)))
            continue
        try:
            keyed = spec["parse"](strip_comments(resp.text))
        except ValueError as exc:
            print("  %-10s PARSE REFUSED — %s" % (county, exc))
            continue
        entries[spec["fips"]] = {
            "county": county,
            "seats": spec["seats"],
            "sourceUrl": url,
            "finalUrl": resp.url,
            "districts": keyed,
        }
        print("  %-10s %2d/%2d districts (%s, %d bytes)"
              % (county, len(keyed), spec["seats"], url, len(resp.content)))

    if not entries:
        print("mi-commissioner-scraper: FAIL — no county yielded a roster", file=sys.stderr)
        return 1

    state = state_commissioners(session, gate, pacer, sorted(entries))
    for fips, entry in entries.items():
        for district, rec in entry["districts"].items():
            named = (state.get(fips) or {}).get(district)
            if named is not None:
                rec["stateColumnName"] = named

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    payload = {
        "scrapedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "userAgent": UA_ROSTER_BOT,
        "counties": entries,
        "refused": [{"county": c, "why": w} for c, w in refused],
    }
    with open(CACHE, "w") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")
    total = sum(len(e["districts"]) for e in entries.values())
    # A delay honoured without saying so cannot be told from one ignored.
    for line in pacer.report():
        print(line)
    print("mi-commissioner-scraper: %d counties, %d districts -> %s"
          % (len(entries), total, os.path.relpath(CACHE, os.path.dirname(HERE))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
