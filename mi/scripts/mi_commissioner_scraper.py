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
roster to the client this scraper sends. Forty-eight counties yield today
across six shipping tranches, and ten more are recorded in PROBES below as
tried and not yielded — host, robots reading, what it answered, the date — so the next
tranche starts from measurements instead of guesses, and a county that changes
its file re-enters by itself on the weekly run.

THE ORDER CHANGED AFTER TRANCHE 3. The first three took the next counties by
POPULATION, and by tranche 3 that had stopped discriminating: the span ran
109K to 83K and the 59 untried counties held 18.1% of the state between them,
each buying under 1%. So tranche 4 measured WHETHER A COUNTY PUBLISHES A
DISTRICT-KEYED BOARD PAGE AT ALL, for all 59 at once and without writing a
parser (mi/scripts/probe_mi_county_boards.py,
mi/data/source/mi-county-board-probe.json), and shipped no county itself.
Tranche 5 is the first taken off that list, and tranche 7 exhausted it:
measured 2026-09-19 against the pruned probe record, ZERO candidates remain
unbuilt. What is left there is 25 counties recorded shut, each with the reason
it was shut for.

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

No county here needs a browser user-agent: every one of the forty-eight
serves this token a full page. A county that refuses is skipped with its reason
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
Forty-eight counties and as many page shapes; each parser's own docstring
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

# ---------------------------------------------------- tranche 6 parsers ---
# The twenty-one counties left on the probe's candidate list that publish a
# readable roster. NOT ONE HOST WAS FETCHED FOR THIS TRANCHE: every page was
# saved during tranche 5's single sweep and every parser below was written
# and corrected offline against that copy.
#
# CASS IS THE TWENTY-SECOND AND WAS NOT HERE. The probe's URL for it is the
# board's COMMITTEES page, which lists committee memberships; all eight
# districts do appear across them, so a parser could have assembled a whole
# board out of five committee rosters and would have lost any commissioner
# who sits on no committee. The county's own board page is a different URL
# and was not among the saved pages, so Cass waited rather than being read
# off the wrong one. It shipped as tranche 7 the same day, off that board
# page, with the committees page kept for the addresses it carries and
# nothing else — parse_cass() states the split.

def lines(page):
    """Flatten a page to its visible lines, keeping mailto: and tel: targets
    and every Cloudflare-obfuscated address as inline [..] markers.

    ONE HELPER FOR TWENTY-ONE COUNTIES, and each parser still states its own
    pairing rule and its own block boundary. The flattening is deterministic:
    <br> and <hr> and the close of a block element end a line, everything else
    is stripped, entities are unescaped and runs of space collapse. It was
    checked against all 32 saved pages before any parser was written.
    """
    h = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    h = re.sub(r"<!--.*?-->", " ", h, flags=re.S)
    h = re.sub(r'<a [^>]*href="mailto:([^"?]+)"[^>]*>', lambda m: " [mail:%s] " % _html.unescape(m.group(1)), h, flags=re.I)
    h = re.sub(r'<a [^>]*href="tel:([^"]+)"[^>]*>', lambda m: " [tel:%s] " % m.group(1), h, flags=re.I)
    # CLOUDFLARE HIDES AN ADDRESS TWO WAYS and both appear in this tranche:
    # the hex as a fragment on the href, and the hex in data-cfemail on the
    # element itself. Emmet and Lake use the second, and a reader of the
    # first alone ships fourteen members with no contact at all.
    h = re.sub(r'href="/cdn-cgi/l/email-protection#([0-9a-fA-F]+)"',
               lambda m: ' data-cfemail="%s"' % m.group(1), h)
    h = re.sub(r'<[a-z]+[^>]*\bdata-cfemail="([0-9a-fA-F]+)"[^>]*>',
               lambda m: " [cf:%s] " % m.group(1), h, flags=re.I)
    h = re.sub(r"<(br|hr)\s*/?>", "\n", h, flags=re.I)
    h = re.sub(r"</(p|div|li|h\d|tr|td|ol|ul|section|article)>", "\n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    h = _html.unescape(h).replace(u" ", " ")
    # LUCE DISTRICT 5 IS "\u200bTony Immel". A zero-width space in front
    # of a name defeats every capitalised-initial test while the page
    # looks perfectly ordinary.
    h = re.sub(u"[\u200b\u200c\u200d\ufeff]", "", h)
    h = re.sub(r"[ \t]+", " ", h)
    return [l.strip() for l in h.splitlines() if l.strip()]


# A NAME TOKEN CAN START LOWERCASE, and a suffix can carry its own comma.
# Delta District 4 is Kelli vanGinhoven and Oscoda District 1 is
# "Charles E. Varner, Jr." — a capitalised-initial test drops exactly the
# people whose county spells their name the way they spell it.
# A NAME TOKEN CAN START LOWERCASE, and a suffix can carry its own comma.
# Delta District 4 is Kelli vanGinhoven and Oscoda District 1 is
# 'Charles E. Varner, Jr.' -- a capitalised-initial test drops exactly the
# people whose county spells their name the way they spell it.
_T = r"(?:[a-z]{2,4}[A-Z][A-Za-z.'\u2019-]*|[A-Z][A-Za-z.'\u2019-]*|Jr\.?|Sr\.?|II|III|IV)"
NAME = re.compile(r"^%s(?:,?\s+%s)+$" % (_T, _T))
ROLE = re.compile(r"(Chair(?:person|man|woman)?|Vice[- ]Chair(?:person|man|woman)?)", re.I)


def take_mail(seg):
    m = re.search(r"\[mail:([^\]]+)\]", seg)
    if m:
        return m.group(1).strip()
    m = re.search(r"\[cf:([0-9a-fA-F]+)\]", seg)
    if m:
        return cf_decode(m.group(1))
    m = re.search(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", seg)
    return m.group(1) if m else None


def take_tel(seg):
    m = re.search(r"\[tel:([^\]]+)\]", seg)
    if m and phone(m.group(1)):
        return phone(m.group(1))
    m = re.search(r"\(?\d{3}\)?[\s.-]\s*\d{3}[\s.-]\d{4}", seg)
    return phone(m.group(0)) if m else None


def split_role(label):
    """Strip a role off a name, returning (name, role).

    TWO SHAPES BEYOND A BARE CHAIR. Arenac prefixes three of its five with the
    plain title "Commissioner Lisa Salgat", which is not a role to print and is
    certainly not part of her name; and Lake writes "Kristine Raymond,
    Vice-Chair Pro Temp", where the role carries a modifier after it, so a
    pattern anchored on the role word ending the string splits neither.
    """
    label = label.strip(" ,-\u2013")
    m = re.search(r"[,\-\u2013]\s*(" + ROLE.pattern + r"(?:\s+(?:Pro\s+Temp\w*|of the Board))?)\s*$",
                  label, re.I)
    if m:
        return label[:m.start()].strip(" ,-\u2013"), m.group(1)
    m = re.match(r"^(" + ROLE.pattern + r"(?:\s+(?:Pro\s+Temp\w*|of the Board))?)[:\s]+(.+)$",
                 label, re.I)
    if m:
        return m.group(3).strip(), m.group(1)
    m = re.match(r"^Commissioner[:\s]+(.+)$", label)
    if m:
        return m.group(1).strip(), None
    return label, None


def blocks_by_district(ls, pattern, window):
    """Cut the flattened lines into one segment per District marker.

    THE SEGMENT ENDS AT THE NEXT MARKER, never at a fixed offset: a fixed
    window is how a parser reaches into the next member's block and pairs a
    district with the wrong person, which is the Ionia/Eaton trap in a
    line-based form.
    """
    marks = [(i, m) for i, l in enumerate(ls) for m in [pattern.match(l)] if m]
    out = []
    for n, (i, m) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else min(len(ls), i + window)
        out.append((m.group(1), i, ls[i:end]))
    return out


# ---------------------------------------------------------------- parsers ---
# EVERY PARSER STATES WHICH SIDE OF THE DISTRICT MARKER ITS NAME SITS ON,
# because the counties differ and nothing on the page says which. Chippewa,
# Clare, Lake, Luce, Ontonagon and Oscoda put the name AFTER the marker;
# Alcona, Arenac, Emmet, Isabella, Mackinac and Menominee put it BEFORE.
# Reading Mackinac the way Chippewa reads pairs District 1 with District 2's
# commissioner and looks entirely correct.

def _named_after(page, marker, window=8, party=None):
    out = {}
    for d, _i, seg in blocks_by_district(lines(page), marker, window):
        body = seg[1:]
        if not body:
            continue
        label, role = split_role(body[0])
        if party:
            m = re.match(r"(.+?)\s*\((%s)\)\s*$" % party, label)
            if m:
                label = m.group(1).strip()
        if not label or not NAME.match(label):
            continue
        rec = {"name": label}
        if role:
            rec["role"] = role
        blob = " ".join(body)
        tel, mail = take_tel(blob), take_mail(blob)
        if tel:
            rec["phone"] = tel
        if mail:
            rec["email"] = mail
        out.setdefault(d, rec)
    return out


def _named_before(page, marker, window=8, party=None):
    ls = lines(page)
    out = {}
    marks = [(i, m) for i, l in enumerate(ls) for m in [marker.match(l)] if m]
    for n, (i, m) in enumerate(marks):
        if i == 0:
            continue
        label, role = split_role(ls[i - 1])
        if party:
            pm = re.match(r"(.+?)\s*\((%s)\)\s*$" % party, label)
            if pm:
                label = pm.group(1).strip()
        if not label or not NAME.match(label):
            continue
        rec = {"name": label}
        if role:
            rec["role"] = role
        end = marks[n + 1][0] - 1 if n + 1 < len(marks) else min(len(ls), i + window)
        blob = " ".join(ls[i:end])
        tel, mail = take_tel(blob), take_mail(blob)
        if tel:
            rec["phone"] = tel
        if mail:
            rec["email"] = mail
        out.setdefault(m.group(1), rec)
    return out


def parse_alcona(page):
    """Name, then "Commissioner District N", then a tel: link. NAME BEFORE."""
    return _named_before(page, re.compile(r"^Commissioner District (\d{1,2})\s*$"))


def parse_alpena(page):
    """One block per member. Some are a single line ("District 1 Precincts 5 & 6
    William LaHaie (R) Phone: ... Email: ...") and some are split over four, so
    the block runs from one district marker to the next and the name is read
    BACKWARDS FROM THE PARTY MARK: a forward read has to guess where the
    precinct list ends, and that list is different on every row.

    TWO MARKER TRAPS. Every member is followed by a PROSE line beginning
    "District N serves" or "District N covers", which is not a marker; and
    District 8's marker carries its role, "District 8 & Chairman of the Board".
    """
    ls = lines(page)
    marks = []
    for i, l in enumerate(ls):
        m = re.match(r"^District (\d{1,2})\b", l)
        if not m or re.match(r"^District \d{1,2}[^.]{0,40}?\b(?:serves|covers)\b", l):
            continue
        marks.append((i, m.group(1), l))
    out = {}
    for n, (i, d, head) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else min(len(ls), i + 6)
        seg = ls[i:end]
        blob = " ".join(seg)
        # THE NAME IS READ PER LINE, NOT OUT OF THE WHOLE BLOCK. District 8's
        # marker is "District 8 & Chairman of the Board", and a pattern let
        # loose on the joined block happily returns "Chairman of the Board John
        # Kozlowski" as the name. Each line is tried in turn with its own
        # "District N" header and any "Precincts 5 & 6" run stripped first, and
        # the first capture NAME accepts wins.
        p = None
        for line in seg:
            body = re.sub(r"^District \d{1,2}\b[^A-Za-z]*", "", line)
            body = re.sub(r"^Precincts?\b[\d\s&,]*", "", body)
            cand = re.match(r"([A-Z][A-Za-z.'\u2019 -]{3,40}?)\s*\(([A-Z]{1,3})\)", body)
            if cand and NAME.match(cand.group(1).strip()):
                p = cand
                break
        if not p:
            continue
        rec = {"name": p.group(1).strip(),
               "party": {"R": "Republican", "D": "Democratic"}.get(p.group(2), p.group(2))}
        role = ROLE.search(head)
        if role:
            rec["role"] = role.group(1)
        tel, mail = take_tel(blob), take_mail(blob)
        if tel:
            rec["phone"] = tel
        if mail:
            rec["email"] = mail
        out.setdefault(d, rec)
    return out


def parse_arenac(page):
    """Role and name, then "District N - Party", then the contacts and a home
    address. NAME BEFORE, and the role is a PREFIX ("Vice-Chair Sally
    Mrozinski") rather than a suffix."""
    return _named_before(page, re.compile(r"^District (\d{1,2})\s*[-–]\s*[A-Za-z]+\s*$"))


def parse_chippewa(page):
    """"District N", then the name. NAME AFTER.

    THE PARTY MOVES BETWEEN THE TWO LINES: districts 3 and 5 read
    "District 3 (R)" and the rest carry the party on the name line or not at
    all, so a marker anchored on a bare "District N" reads three of five.

    NO E-MAIL SHIPS. The only address on the page is a shared county inbox at
    the foot of the list, and a segment that runs to the end of the page hands
    it to District 5 as that member's own.
    """
    out = {}
    marker = re.compile(r"^District (\d{1,2})(?:\s*\([A-Z]{1,3}\))?\s*$")
    for d, _i, seg in blocks_by_district(lines(page), marker, 8):
        if len(seg) < 2:
            continue
        label, role = split_role(seg[1])
        m = re.match(r"(.+?)\s*\([A-Z]{1,3}\)\s*$", label)
        if m:
            label = m.group(1).strip()
        if not NAME.match(label):
            continue
        rec = {"name": label}
        if role:
            rec["role"] = role
        tel = take_tel(" ".join(seg))
        if tel:
            rec["phone"] = tel
        out.setdefault(d, rec)
    return out


def parse_clare(page):
    """"District N:", then the name, then a PLAIN-TEXT e-mail and a phone.
    NAME AFTER. The addresses are not links, which is why the probe counted no
    mailto here at all."""
    return _named_after(page, re.compile(r"^District (\d{1,2}):\s*$"))


def parse_clinton(page):
    """One line per member: "Name - Commissioner, District N Term expires: ...".

    DISTRICT 4 READS "Vacant" and the county carries its own Notice of Vacancy
    for that seat at the top of the same page. TWO DIFFERENT DASHES: districts
    1, 2, 3 and 5 use an en dash and the vacant row uses a hyphen, so a parser
    keyed on one separator ships four of five and calls the fifth missing."""
    out = {}
    for l in lines(page):
        m = re.match(r"^(.{2,50}?)\s*[–-]\s*Commissioner,\s*District (\d{1,2})\b", l)
        if not m:
            continue
        label = m.group(1).strip()
        if label.lower() == "vacant":
            out.setdefault(m.group(2), {"vacant": True})
            continue
        label, role = split_role(label)
        if not NAME.match(label):
            continue
        rec = {"name": label}
        if role:
            rec["role"] = role
        out.setdefault(m.group(2), rec)
    return out


def parse_delta(page):
    """"District #N - Name", five lines in the section menu. The page saved is
    one member's own page, so its title repeats District 4 three times before
    the list; the FIRST occurrence per district is taken and the repeats agree."""
    out = {}
    for l in lines(page):
        m = re.match(r"^District #(\d{1,2})\s*[–-]\s*([^–-]{3,40})$", l)
        if m and NAME.match(m.group(2).strip()):
            out.setdefault(m.group(1), {"name": m.group(2).strip()})
    return out


def parse_emmet(page):
    """Name, then "District N", then a home address, a phone and a
    Cloudflare-obfuscated e-mail. NAME BEFORE."""
    return _named_before(page, re.compile(r"^District (\d{1,2})\s*$"))


def parse_houghton(page):
    """One <div class="w3-container w3-third"> per member, holding the photo,
    <strong>Name</strong>, <em>Role</em>, the mailto, the phone, then
    <strong>District N:</strong> and the townships.

    THE DISTRICT LINE COMES AFTER ITS OWN MEMBER, NOT BEFORE. Read as flat text
    the page alternates name, district, name, district, and taking the name
    that FOLLOWS a district line pairs every one of the five with the wrong
    person and leaves District 4 unnamed \u2014 four of five, each row looking
    exactly like a row. The div is the block, so the pairing is made inside it
    and the order on the page cannot decide it.
    """
    out = {}
    for blk in re.split(r'<div class="w3-container w3-third"', page)[1:]:
        name = re.search(r"<strong>\s*([^<]{3,40})\s*</strong>", blk)
        keyed = re.search(r"<strong>\s*District (\d{1,2}):\s*</strong>", blk)
        if not (name and keyed):
            continue
        label = txt(name.group(1))
        if not NAME.match(label):
            continue
        rec = {"name": label}
        role = re.search(r"<em>\s*([^<]{3,40})\s*</em>", blk)
        if role and ROLE.search(role.group(1)):
            rec["role"] = txt(role.group(1))
        mail = re.search(r'href="mailto:([^"?]+)"', blk)
        if mail:
            rec["email"] = _html.unescape(mail.group(1)).strip()
        tel = take_tel(txt(blk))
        if tel:
            rec["phone"] = tel
        out.setdefault(keyed.group(1), rec)
    return out


def parse_isabella(page):
    """Name with its party, then "DISTRICT N" in capitals, then a tel: and a
    mailto:. NAME BEFORE."""
    return _named_before(page, re.compile(r"^DISTRICT (\d{1,2})\s*$"), party="D|R|I")


def parse_lake(page):
    """"District N Commissioner", then "Name, Role", then the district's area
    and the member's home address and a Cloudflare-obfuscated e-mail.
    NAME AFTER."""
    return _named_after(page, re.compile(r"^District (\d{1,2}) Commissioner\s*$"), 10)


def parse_luce(page):
    """"District N", then "Name-Role", then a PO box and a phone. NAME AFTER,
    and the role is joined to the name by a bare hyphen with no space."""
    return _named_after(page, re.compile(r"^District (\d{1,2})\s*$"))


def parse_mackinac(page):
    """Name, then "District N", then a phone. NAME BEFORE.

    This is the county that settles why every parser here states its side:
    read the Chippewa way it pairs District 1 with District 2's commissioner
    and every row still looks like a row."""
    return _named_before(page, re.compile(r"^District (\d{1,2})\s*$"))


def parse_menominee(page):
    """Name, then "<Role> - District N", then a home address and "Phone: ...".
    NAME BEFORE.

    THE ROLE IS THE WHOLE PREFIX and only six of the nine read "Commissioner":
    the others are "Chairman of the Board - District 3", "Vice Chairman -
    District 8" and "Vice Chairman - Pro Tempore - District 9", whose own role
    contains the separator. A marker anchored on "Commissioner" ships six of
    nine and drops all three officers.
    """
    ls = lines(page)
    marker = re.compile(r"^(.+)\s*[-\u2013]\s*District (\d{1,2})\s*$")
    out = {}
    marks = [(i, m) for i, l in enumerate(ls) for m in [marker.match(l)] if m]
    for n, (i, m) in enumerate(marks):
        if i == 0:
            continue
        label = ls[i - 1].strip()
        if not NAME.match(label):
            continue
        rec = {"name": label}
        role = m.group(1).strip(" -\u2013")
        if role and role.lower() != "commissioner":
            rec["role"] = role
        end = marks[n + 1][0] - 1 if n + 1 < len(marks) else min(len(ls), i + 8)
        tel = take_tel(" ".join(ls[i:end]))
        if tel:
            rec["phone"] = tel
        out.setdefault(m.group(2), rec)
    return out


def parse_montcalm(page):
    """A CivicPlus staff directory, the Kalamazoo shape with one difference:
    the job title reads "District N Commissioner" where Kalamazoo's reads
    "District N" or "District N - Role", so Kalamazoo's own anchored pattern
    matches none of these seven."""
    out = {}
    for blk in re.split(r'<li class="widgetItem h-card">', page)[1:]:
        name = re.search(r'class="widgetTitle field p-name">\s*(.*?)\s*</h4>', blk, re.S)
        job = re.search(r'class="field p-job-title">(.*?)</div>', blk, re.S)
        if not (name and job):
            continue
        keyed = re.match(r"District\s+(\d{1,2})\s+Commissioner\s*(?:[-–]\s*(.+))?$",
                         txt(job.group(1)))
        if not keyed:
            continue
        rec = {"name": txt(name.group(1))}
        if keyed.group(2):
            rec["role"] = keyed.group(2).strip()
        out.setdefault(keyed.group(1), rec)
    return out


def parse_ontonagon(page):
    """"District N:", then "Name (Party)", then a home address and a phone.
    NAME AFTER, and the party is spelled out rather than lettered."""
    return _named_after(page, re.compile(r"^District (\d{1,2}):\s*$"),
                        party="Democrat|Republican|Independent")


def parse_oscoda(page):
    """"District #N Commissioner", then the name, then the role on its own
    line, then a mailto:. NAME AFTER."""
    return _named_after(page, re.compile(r"^District #(\d{1,2}) Commissioner\s*$"))


def parse_otsego(page):
    """One line per member under Members: "Name (R) , District N[, Role]"."""
    out = {}
    for l in lines(page):
        m = re.match(r"^(.{3,40}?)\s*\(([RDI])\)\s*,\s*District (\d{1,2})\s*(?:,\s*(.+))?$", l)
        if not m or not NAME.match(m.group(1).strip()):
            continue
        rec = {"name": m.group(1).strip(),
               "party": {"R": "Republican", "D": "Democratic"}.get(m.group(2), m.group(2))}
        if m.group(4) and ROLE.search(m.group(4)):
            rec["role"] = m.group(4).strip()
        out.setdefault(m.group(3), rec)
    return out


def parse_presqueisle(page):
    """"District N : <townships>", then a mailto: whose link text is
    "Name (R)", then a home address. NAME AFTER, inside the mail line."""
    out = {}
    for d, _i, seg in blocks_by_district(
            lines(page), re.compile(r"^District (\d{1,2})\s*:"), 8):
        for l in seg[1:]:
            # DISTRICT 3 IS "(NPA)" where the other four are one letter.
            m = re.search(r"\[mail:[^\]]+\]\s*(.{3,40}?)\s*\(([A-Z]{1,3})\)", l)
            if not m or not NAME.match(m.group(1).strip()):
                continue
            rec = {"name": m.group(1).strip(),
                   "party": {"R": "Republican", "D": "Democratic",
                             "NPA": "No party affiliation"}.get(m.group(2), m.group(2))}
            mail = take_mail(l)
            if mail:
                rec["email"] = mail
            out.setdefault(d, rec)
            break
    return out


def parse_roscommon(page):
    """One line per member under MEMBERS: "Name , District N" or
    "Name , Role, District N", followed by a mailto: for most."""
    out = {}
    for l in lines(page):
        m = re.match(r"^(.{3,40}?)\s*,\s*(?:(.{3,25}?)\s*,\s*)?District (\d{1,2})\b", l)
        if not m or not NAME.match(m.group(1).strip()):
            continue
        rec = {"name": m.group(1).strip()}
        if m.group(2) and ROLE.search(m.group(2)):
            rec["role"] = m.group(2).strip()
        mail = take_mail(l)
        if mail:
            rec["email"] = mail
        out.setdefault(m.group(3), rec)
    return out


def parse_schoolcraft(page):
    """"DISTRICT #N:", then the townships, then "NAME, ROLE - Party", then the
    election and expiry dates and a Cloudflare-obfuscated e-mail.

    THE NAME SHIPS IN CAPITALS because that is how the county publishes it.
    Title-casing it here would be this project deciding how somebody's name is
    written, which is the Vermilion and Berrien rule."""
    out = {}
    for d, _i, seg in blocks_by_district(
            lines(page), re.compile(r"^DISTRICT #(\d{1,2}):\s*$"), 12):
        for l in seg[1:]:
            m = re.match(r"^([A-Z][A-Z.'’ -]{3,40}?)\s*(?:,\s*([A-Z-]{4,20}))?\s*[-–]\s*"
                         r"(Republican|Democrat\w*|Independent)\s*$", l)
            if not m:
                continue
            rec = {"name": m.group(1).strip(),
                   "party": "Democratic" if m.group(3).startswith("Democrat") else m.group(3)}
            if m.group(2) and ROLE.search(m.group(2)):
                rec["role"] = m.group(2).strip().title()
            blob = " ".join(seg)
            tel, mail = take_tel(blob), take_mail(blob)
            if tel:
                rec["phone"] = tel
            if mail:
                rec["email"] = mail
            out.setdefault(d, rec)
            break
    return out



def parse_cass(page, also=None):
    """Two of the county's own pages, and NEITHER IS A ROSTER ON ITS OWN.

    The board page is eight photo buttons, each an <a> to /NNNN/District-N
    holding a <span class="textStyle1">Name</span> and a
    <span class="textStyle2">District N Commissioner</span> caption: the people
    and the districts, and no way to contact any of them. The committees page,
    which is the URL the probe scored, puts a mailto and the member's own
    district on one line ("Thomas Langley (District 1, Committee Chair)"): the
    addresses, and no roster. It lists five standing committees, so a
    commissioner who sits on none appears nowhere on it, and it names two
    people who are not on the board at all — the County Administrator and the
    HR/Payroll Director, each captioned with a job title where a member carries
    a district.

    SO THE BOARD PAGE DECIDES WHO IS ON THE BOARD, and the committees page only
    adds an address to a district the board page has already named. The two
    agree on all eight districts today, which is a second witness on the
    pairing; a district where they disagree gets no address and keeps its name,
    because the board page is the roster and a committee list going stale is
    not evidence against it.

    THE BOARD PAGE IS ALSO ITS OWN WITNESS: each button's href slug and its
    printed caption name the district separately, and a button whose two halves
    disagree is not read.

    Seven of the eight have an address. Jeremiah Jones, the Chair, is named on
    both pages with no mailto on either.

    The committees page is OPTIONAL — when it does not fetch, the county ships
    names without addresses and the run says so, and check_roster_retention.py
    is what notices, since it measures each county in this file as its own
    source. A committees page that fetches and yields fewer than five joinable
    addresses is a DIFFERENT failure — the page's shape has moved under this
    parser rather than the network having dropped — and refuses.
    """
    out = {}
    button = re.compile(
        r'<a href="[^"]*?/District-(\d{1,2})"[^>]*class="fancyButton[^>]*>.*?'
        r'<span class="textStyle1">([^<]+)</span>\s*(?:<br\s*/?>)?\s*'
        r'<span class="textStyle2">([^<]*)</span>', re.S | re.I)
    for m in button.finditer(page):
        label, caption = txt(m.group(2)), txt(m.group(3))
        said = re.search(r"District (\d{1,2})", caption)
        if not (said and said.group(1) == m.group(1) and NAME.match(label)):
            continue
        rec = {"name": label}
        role = ROLE.search(caption)
        if role:
            rec["role"] = role.group(1)
        out.setdefault(m.group(1), rec)
    if not also:
        return out

    # (District N, ...) OR (Some Role, District N) — Jones's line puts the role
    # first — and the name is whatever precedes the bracket. A line whose
    # bracket holds no district belongs to a member of staff, not to the board.
    mails = {}
    for l in lines(also):
        m = re.match(r"^(?:\[mail:([^\]]+)\]\s*)?(.+?)\s*\(([^)]*)\)\s*$", l)
        if not m:
            continue
        keyed = re.search(r"District (\d{1,2})", m.group(3))
        label = txt(m.group(2))
        if not (keyed and NAME.match(label)):
            continue
        rec = mails.setdefault(keyed.group(1), {"name": label, "email": None})
        if rec["name"] == label and m.group(1) and not rec["email"]:
            rec["email"] = m.group(1).strip()
    joined = 0
    for d, rec in out.items():
        seen = mails.get(d)
        if seen and seen["name"] == rec["name"] and seen["email"]:
            rec["email"] = seen["email"]
            joined += 1
    if joined < 5:
        raise ValueError(
            "the committees page joined %d addresses to the board page's %d "
            "districts; it named %d district-keyed people. Five is the floor: "
            "a member leaving a committee moves this by one, a page whose "
            "shape has moved answers zero."
            % (joined, len(out), len(mails)))
    return out


# --- tranche 8, 2026-09-24: the four counties the shut-list re-examination
# --- reopened. Each was recorded `no-board-page` or `no-confirmed-host` by a
# --- sweep that never asked for the address its own county publishes, and
# --- each page below sits on a host no earlier sweep tried.


# ------------------------------------------------------------------ 155 ---

def parse_shiawassee(page):
    """A bare "District N" heading, then the member, address, phone, e-mail.

    EVERY DISTRICT NUMBER APPEARS TWICE AND ONLY ONE OF THEM IS THE KEY. After
    each member's e-mail the page prints "District N includes <townships>",
    which is a description and not a heading -- so a parser matching any
    "District N" finds fourteen for a seven-seat board, and because the
    description sits immediately above the NEXT heading, pairing on the
    following line hands District 2's seat to District 3's member. The key is
    the line that is a heading and nothing else.

    The e-mail is taken as published: District 3's is a gmail.com address while
    the other six are @shiawassee.net, and a roster that dropped it for not
    matching its neighbours would be deciding that a county published the
    wrong contact for its own commissioner.
    """
    out = {}
    L = lines(page)
    for i, line in enumerate(L):
        m = re.match(r"^District\s+(\d{1,2})$", line)
        if not m:
            continue
        blk = "\n".join(L[i + 1:i + 8])
        name = txt(L[i + 1]) if i + 1 < len(L) else ""
        if not name:
            continue
        # first_mailto() greps raw HTML and this parser reads lines(), which has
        # already rewritten every mailto into a [mail:...] marker -- so the
        # helper returns None here and all seven addresses go missing while the
        # roster still ships seven correct names.
        mail = re.search(r"\[mail:\s*([^\]\s]+)\]", blk)
        rec = {"name": re.sub(r"\s*[\u2013-]\s*(Chair|Vice).*$", "", name).strip(" ,-"),
               "email": mail.group(1) if mail else None,
               "phone": first_phone(blk) or None}
        role = re.search(r"(Chair(?:person|man)?|Vice\s*Chair(?:person|man)?)", name, re.I)
        if role:
            rec["role"] = role.group(1)
        party = re.search(r"\((R|D|I)\)", name)
        if party:
            rec["party"] = PARTY.get(party.group(1))
        rec["name"] = re.sub(r"\s*\((R|D|I)\)\s*", " ", rec["name"]).strip(" ,-")
        out.setdefault(m.group(1), {k: v for k, v in rec.items() if v})
    return out


# ------------------------------------------------------------------ 129 ---

def parse_ogemaw(page):
    """Name, then "District N Commissioner", then a phone -- when there is one.

    THE PHONE IS NOT ALWAYS THERE AND THE NEXT LINE IS THE NEXT MEMBER. District
    2's entry carries no number, so the line after its heading is "Charles
    Wiltse", District 3's member: a parser reading name/district/phone as a
    fixed triple ships a commissioner's name as another commissioner's
    telephone number. The phone is taken only when the following line IS a
    phone number, and District 2 ships without one because the county
    publishes none.

    No e-mail and no party: the page prints neither for anybody.
    """
    out = {}
    L = lines(page)
    for i, line in enumerate(L):
        m = re.match(r"^District\s*#?\s*(\d{1,2})\s+Commissioner$", txt(line))
        if not m or i == 0:
            continue
        name = txt(L[i - 1])
        if not re.match(r"^[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,3}$", name):
            continue
        rec = {"name": name}
        nxt = txt(L[i + 1]) if i + 1 < len(L) else ""
        ph = phone(nxt)
        if ph and not re.search(r"[A-Za-z]{3}", nxt):
            rec["phone"] = ph
        out.setdefault(m.group(1), rec)
    return out


# ------------------------------------------------------------------ 083 ---

def parse_keweenaw(page):
    """A bare "District N" heading, then the member with party, address,
    telephone and a Cloudflare-obfuscated address printed twice.

    THE tel: HREF IS NOT MAINTAINED AND THE VISIBLE NUMBER IS. Measured
    2026-09-24: on three of five seats the href and the printed number agree,
    and on two they do not -- District 2 links 906-337-5585 under a printed
    906-281-0944, District 5 links 906-934-2509 under a printed 906-369-3170.
    Two of five is a column that is not kept, not a typo, so this parser reads
    the PRINTED number and never the link, and says so rather than picking the
    one that happens to parse first.

    The two `[cf:` markers per member decode to one address each way round --
    the link and its own display text -- so they are deduplicated rather than
    shipped as two contacts. The addresses are @keweenawcountymi.gov, a domain
    this county does not serve its website from.
    """
    out = {}
    L = lines(page)
    for i, line in enumerate(L):
        m = re.match(r"^District\s+(\d{1,2})$", line)
        if not m or i + 1 >= len(L):
            continue
        name = txt(L[i + 1])
        if not re.search(r"[A-Za-z]{3}", name):
            continue
        blk = "\n".join(L[i + 1:i + 7])
        rec = {"name": re.sub(r"\s*,?\s*(Chair(?:man|person)?|Vice[-\s]*Chair(?:man|person)?)"
                             r"\s*(\([A-Z]{1,3}\))?\s*$", "", name).strip(" ,")}
        role = re.search(r"(Vice[-\s]*Chair(?:man|person)?|Chair(?:man|person)?)", name, re.I)
        if role:
            rec["role"] = role.group(1)
        party = re.search(r"\(([A-Z]{1,3})\)", name)
        if party:
            rec["party"] = PARTY.get(party.group(1), party.group(1))
        rec["name"] = re.sub(r"\s*\([A-Z]{1,3}\)\s*", " ", rec["name"])
        rec["name"] = re.sub(r"\s+", " ", rec["name"]).strip(" ,")
        # the PRINTED number, never the tel: target -- see the docstring
        shown = re.search(r"\[tel:[^\]]*\]\s*([\d][\d\s().-]{8,})", blk)
        if shown:
            ph = phone(shown.group(1))
            if ph:
                rec["phone"] = ph
        mails = []
        for hexed in re.findall(r"\[cf:([0-9a-fA-F]+)\]", blk):
            addr = cf_decode(hexed)
            if addr and addr not in mails:
                mails.append(addr)
        if len(mails) == 1:
            rec["email"] = mails[0]
        out.setdefault(m.group(1), rec)
    return out


# ------------------------------------------------------------------ 057 ---

def parse_gratiot(page):
    """One <li> per member: the name in an <a>, then "District N: <townships>".

    THE DISTRICTS ARE NOT IN ORDER. The page lists 4, 2, 1, 3, 5, so a parser
    that walks the list and counts ships every seat under the wrong number --
    the reason this reads the number out of each item rather than from its
    position.

    Party is taken where the page prints it and not invented: four members
    carry (R) and the first carries none, which is what the county publishes.
    No e-mail ships: the only address on the page is the County Clerk's.
    """
    out = {}
    for item in re.findall(r"<li\b[^>]*>(.*?)</li>", page, re.S | re.I):
        if not re.search(r"District\s*\d", item):
            continue
        m = re.search(r"<a\b[^>]*>(.*?)</a>(.*?)District\s*#?\s*(\d{1,2})\s*:",
                      item, re.S | re.I)
        if not m:
            continue
        name, after, dist = txt(m.group(1)), txt(m.group(2)), m.group(3)
        rec = {"name": re.sub(r"\s*\((R|D|I)\)\s*", " ", name).strip(" ,")}
        party = re.search(r"\((R|D|I)\)", name)
        if party:
            rec["party"] = PARTY.get(party.group(1))
        role = re.search(r"(Vice\s*Chair(?:person|man)?|Chair(?:person|man)?)", after, re.I)
        if role:
            rec["role"] = role.group(1)
        out.setdefault(dist, rec)
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
    # --- tranche 6, 2026-09-19: the probe's remaining readable candidates ---
    {"fips": "001", "county": "Alcona", "seats": 5, "parse": parse_alcona,
     "url": "https://alconacountymi.com/home/county-commissioners/"},
    {"fips": "007", "county": "Alpena", "seats": 8, "parse": parse_alpena,
     "url": "https://alpenacounty.org/577/Commissioners-By-District"},
    {"fips": "011", "county": "Arenac", "seats": 5, "parse": parse_arenac,
     "url": "https://arenaccountymi.gov/BOC/"},
    {"fips": "033", "county": "Chippewa", "seats": 5, "parse": parse_chippewa,
     "url": "https://www.chippewacountymi.gov/board-of-commissioners"},
    {"fips": "035", "county": "Clare", "seats": 9, "parse": parse_clare,
     "url": "https://clareco.net/department/board-of-commissioners/"},
    {"fips": "037", "county": "Clinton", "seats": 7, "parse": parse_clinton,
     "url": "https://clinton-county.org/413/Board-of-Commissioners"},
    {"fips": "041", "county": "Delta", "seats": 5, "parse": parse_delta,
     "url": "https://deltacountymi.gov/board-of-commissioners/"
            "district-4-kelli-vanginhoven/"},
    {"fips": "047", "county": "Emmet", "seats": 7, "parse": parse_emmet,
     "url": "https://emmetcounty.org/government/board_of_commissioners/index.php"},
    {"fips": "061", "county": "Houghton", "seats": 5, "parse": parse_houghton,
     "url": "https://houghtoncounty.gov/commissions-board.php"},
    {"fips": "073", "county": "Isabella", "seats": 7, "parse": parse_isabella,
     "url": "https://www.isabellacounty.org/boards-commissions-committees/"
            "board-of-commissioners/"},
    {"fips": "085", "county": "Lake", "seats": 7, "parse": parse_lake,
     "url": "https://lakecountymi.gov/board-of-commissioners/"},
    {"fips": "095", "county": "Luce", "seats": 5, "parse": parse_luce,
     "url": "https://www.lucecountymi.com/commissioners"},
    {"fips": "097", "county": "Mackinac", "seats": 5, "parse": parse_mackinac,
     "url": "https://www.mackinaccounty.net/departments/commissioners/"},
    {"fips": "109", "county": "Menominee", "seats": 9, "parse": parse_menominee,
     "url": "https://www.menomineecountymi.gov/departments/"
            "county-board-of-commissioners/general-information/staff/"},
    {"fips": "117", "county": "Montcalm", "seats": 7, "parse": parse_montcalm,
     "url": "https://montcalmcountymi.gov/270/Board-of-Commissioners"},
    {"fips": "131", "county": "Ontonagon", "seats": 5, "parse": parse_ontonagon,
     "url": "https://ontonagoncounty.org/county-offices/board-of-commissioners/"},
    {"fips": "135", "county": "Oscoda", "seats": 5, "parse": parse_oscoda,
     "url": "https://www.oscodacountymi.com/board-of-commissioners/"},
    {"fips": "137", "county": "Otsego", "seats": 9, "parse": parse_otsego,
     "url": "https://otsegocountymi.gov/277/Board-of-Commissioners"},
    {"fips": "141", "county": "Presque Isle", "seats": 5, "parse": parse_presqueisle,
     "url": "https://presqueislecounty.org/board-of-commissioners/"},
    {"fips": "143", "county": "Roscommon", "seats": 5, "parse": parse_roscommon,
     "url": "https://roscommoncounty.net/202/Board-of-Commissioners"},
    {"fips": "153", "county": "Schoolcraft", "seats": 5, "parse": parse_schoolcraft,
     "url": "https://schoolcraftcounty.net/government/elected-officials/"
            "commissioners"},
    # --- tranche 7, 2026-09-19: Cass, the last county on the probe's list ---
    # THE ONLY ENTRY HERE WITH AN `also`, and parse_cass() says why: the board
    # page names the eight districts and carries no contact, the committees
    # page carries the addresses and is not a roster. The second page is read
    # through the same gate, pacer and retries as the first.
    {"fips": "027", "county": "Cass", "seats": 8, "parse": parse_cass,
     "url": "https://casscountymi.org/1289/Board-of-Commissioners",
     "also": "https://casscountymi.org/1500/BOC-Committees"},
    # --- tranche 8, 2026-09-24: four counties the probe had recorded shut.
    # --- EVERY URL HERE IS ON A HOST NO EARLIER SWEEP ASKED FOR. The probe's
    # --- candidate generator could not produce these spellings, so
    # --- `no-board-page` and `no-confirmed-host` were facts about its
    # --- candidate list; each address came from the county's own Wikipedia
    # --- infobox, which is not a county host, and was then confirmed against
    # --- the county's own front page before this page was read.
    {"fips": "155", "county": "Shiawassee", "seats": 7, "parse": parse_shiawassee,
     "url": "https://shiawassee.net/board-of-commissioners/"},
    {"fips": "129", "county": "Ogemaw", "seats": 5, "parse": parse_ogemaw,
     "url": "https://www.ocmi.us/commissioners/"},
    {"fips": "083", "county": "Keweenaw", "seats": 5, "parse": parse_keweenaw,
     "url": "https://www.keweenawcountyonline.org/commissions-board.php"},
    {"fips": "057", "county": "Gratiot", "seats": 5, "parse": parse_gratiot,
     "url": "https://www.gratiotmi.com/302/Board-of-Commissioners"},
)

# The counties tried and not yielded, measured from this project's sandbox
# with UA_ROSTER_BOT, robots.txt read first in every case — six on
# 2026-09-13, Allegan and Bay on 2026-09-15, Gogebic and Marquette on
# 2026-09-19. Each says what stopped it rather than "no page found".
# Re-measure before writing any of them off again — a robots file changes, an
# edge rule is lifted, a county moves CMS.
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
    and this is a different host from every county site. It is an ArcGIS
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


def read_page(url, session, gate, pacer):
    """Robots verdict, then the page. -> (response, why, kind, gate, pacer).

    `response` is None when the page was not read and `why` says so; `kind` is
    "robots" for a refusal, which the caller records as a refusal, or "fetch"
    for one that says nothing about the county's policy. The gate and pacer
    come back because an unreachable robots read rebuilds both.

    ONE COPY, because a county reading two pages reads both this way: a second
    page fetched without the robots read, or without the retries, is the shape
    every defect in this file has taken.

    THE ROBOTS READ IS RETRIED THE SAME WAY THE PAGE IS, and for the same host.
    co.hillsdale.mi.us drops roughly one connection in three from this
    project's sandbox, and the drop lands on robots.txt because that is the
    first request made; measured 2026-09-19, the retry added for the PAGE did
    not cover it and Hillsdale fell out of a full run with "robots
    unreachable" while serving its file on the next attempt. A gate caches its
    verdict per site, so each retry needs a fresh one. Only `unreachable` is
    retried: a served refusal and a challenge are answers. FIVE TRIES RATHER
    THAN THREE, measured 2026-09-19: three consecutive reads of that host
    failed inside one run and the county dropped out of the roster it had been
    in since the morning, which the builder's two-counties-may-go-dark floor is
    meant to survive rather than to hide.

    THE STRICT READING, opted into by argument the way the DuPage and Logan
    municipal scrapers do. RFC 9309 files a 401/403 on robots.txt with a 404
    and allows, which is right for the APIs that answer that way (every ArcGIS
    FeatureServer); these are county WEBSITES, where a 403 on robots.txt is a
    firewall refusing this client and fetching the page anyway is walking past
    a no.

    A TRANSPORT FAILURE IS NOT A MEASUREMENT — the same host resets the
    connection on roughly one request in three from this sandbox and serves the
    same page on the next try; a single failure recorded as "county did not
    yield" is how a county that publishes its board stays unread. Only the
    transport is retried: a robots refusal and an HTTP status are answers and
    are taken as given.
    """
    verdict = gate.verdict(url)
    for attempt in range(5):
        if verdict.status != "unreachable":
            break
        time.sleep(2 * (attempt + 1))
        gate = RobotsGate(session, UA_ROSTER_BOT)
        pacer = HostPacer(gate)
        verdict = gate.verdict(url)
    allowed, why = verdict.allows(UA_ROSTER_BOT, url, refused_is_refusal=True)
    if not allowed:
        return None, "robots %s: %s" % (verdict.status, why), "robots", gate, pacer
    resp, last = None, None
    for attempt in range(3):
        try:
            with pacer.hold(url):
                resp = session.get(url, timeout=TIMEOUT)
            break
        except Exception as exc:                              # noqa: BLE001
            last = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    if resp is None:
        return None, "FETCH FAILED after 3 tries — %s" % last, "fetch", gate, pacer
    if resp.status_code != 200:
        # A MANAGED CHALLENGE IS NOT AN OUTAGE and the record should not read
        # like one. Cloudflare says so in its own headers, so this asks them
        # rather than sniffing the body for the word "captcha" — the mistake
        # scripts/probe_user_agents.py already records, where searching bodies
        # for that word reported sixteen real pages as challenges. Measured
        # 2026-09-19: kalcounty.gov, kentcountymi.gov and berriencounty.org all
        # began answering `Cf-Mitigated: challenge` with a 5.7 KB "Just a
        # moment..." body. It is an access control and is never worked around;
        # the builder carries those counties forward on their last good read.
        marker = (resp.headers.get("Cf-Mitigated")
                  or ("cloudflare" if resp.headers.get("Server", "").lower()
                      == "cloudflare" and resp.status_code == 403 else ""))
        how = (" — Cloudflare managed challenge (%s), an access control" % marker
               if marker else "")
        return (None, "HTTP %s (%d bytes)%s"
                % (resp.status_code, len(resp.content), how),
                "challenge" if marker else "fetch", gate, pacer)
    return resp, None, None, gate, pacer


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

    entries, refused, unread = {}, [], []
    read_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for spec in wanted:
        url, county = spec["url"], spec["county"]
        resp, why, kind, gate, pacer = read_page(url, session, gate, pacer)
        if resp is None:
            # A COUNTY THAT WAS NOT READ IS RECORDED, NOT DROPPED. Until
            # 2026-09-19 this branch printed and continued, so the county was
            # simply absent from the cache and the builder could not tell a
            # transport failure from a county nobody tracks — which is how
            # #1052 proposed deleting Delta and Otsego, fourteen named
            # commissioners, off two pages that were serving normally the
            # whole time. The builder carries these forward from the shipped
            # roster; see build_mi_commissioner_roster.py's PRESERVE section.
            unread.append({"fips": spec["fips"], "county": county,
                           "why": why, "kind": kind or "fetch"})
            if kind == "robots":
                refused.append((county, why))
                print("  %-10s SKIPPED — %s" % (county, why))
            else:
                print("  %-10s %s" % (county, why))
            continue
        # A SECOND PAGE THAT DOES NOT ANSWER COSTS ITS OWN COLUMN AND NOTHING
        # ELSE. Cass is the one county here that reads two — its board page
        # names the districts and its committees page carries the addresses —
        # and a network failure on the second is not a reason to withhold the
        # eight names the first one gave. The run says so, and
        # check_roster_retention.py is what fails the weekly PR, since it
        # measures each county in this file as its own source.
        also = None
        if spec.get("also"):
            extra, why2, _kind, gate, pacer = read_page(spec["also"], session, gate, pacer)
            if extra is None:
                print("  %-10s second page not read — %s" % (county, why2))
            else:
                also = strip_comments(extra.text)
        try:
            body = strip_comments(resp.text)
            keyed = spec["parse"](body, also) if spec.get("also") else spec["parse"](body)
        except ValueError as exc:
            unread.append({"fips": spec["fips"], "county": county,
                           "why": "PARSE REFUSED — %s" % exc, "kind": "parse"})
            print("  %-10s PARSE REFUSED — %s" % (county, exc))
            continue
        entries[spec["fips"]] = {
            "county": county,
            "seats": spec["seats"],
            "sourceUrl": url,
            "finalUrl": resp.url,
            "districts": keyed,
            # PER COUNTY, never the run's own timestamp. `--county` merges, so
            # one global stamp would date all forty-eight to a run that read
            # one of them, and the builder's staleness ceiling would then be
            # measuring nothing.
            "readAt": read_date,
        }
        if spec.get("also"):
            # Provenance for whoever reads this cache — the shipped roster
            # names the page the ROSTER came from, which is `sourceUrl`.
            entries[spec["fips"]]["alsoUrl"] = spec["also"]
        print("  %-10s %2d/%2d districts (%s, %d bytes)"
              % (county, len(keyed), spec["seats"], url, len(resp.content)))
        if not keyed:
            # READ FINE AND PARSED NOTHING is a parser that no longer matches
            # the county's markup, not a board that ceased to exist, and it is
            # NOT the preserve case: carrying it forward quietly would freeze
            # that county's names for as long as nobody looked. It is said
            # loudly here and the builder refuses the run.
            print("  %-10s YIELDED NOTHING from a page that answered %d bytes "
                  "— the parser no longer matches this county's markup"
                  % (county, len(resp.content)))

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
    kept = 0
    if args.county and os.path.exists(CACHE):
        # --county MERGES; a full run REPLACES. Re-reading one county is how a
        # new parser is proved against the live page, and a flag that wipes the
        # other forty-seven to do it makes the next step a full sweep of hosts
        # nobody needed to ask again.
        #
        # CORRECTED 2026-09-19. This comment used to finish "a full run
        # replaces because there a county that has stopped yielding must leave
        # the file rather than linger on last week's answer", which states the
        # defect as the design: it reads a county that was NOT READ as a county
        # that has STOPPED YIELDING. check_roster_retention.py has been
        # arguing the other side the whole time — "a source that stops
        # publishing is a real event; a source that failed to fetch once is
        # not" — and Adam ruled on 2026-09-19 that we preserve data we have
        # already fetched. A full run still replaces the cache, and the
        # `unread` list below is what lets the builder tell the two apart.
        with open(CACHE) as handle:
            prior = json.load(handle)
        held = prior.get("counties") or {}
        for fips, entry in held.items():
            if fips not in entries:
                entries[fips] = entry
                kept += 1
        # THE UNREAD LIST MERGES TOO, and leaving it out was a defect in this
        # change's own first draft (caught 2026-09-19 by the build that
        # followed it). A full run recorded Kalamazoo, Kent and Berrien unread;
        # a `--county Midland` run then rewrote the cache with its own empty
        # list, so the builder saw three counties absent with no row saying
        # they had been tried, refused to carry them forward, and failed on the
        # county floor. A county keeps its unread row until a run actually
        # reads it.
        for row in prior.get("unread") or []:
            if row.get("fips") not in entries and \
                    row.get("fips") not in {u["fips"] for u in unread}:
                unread.append(row)
    payload = {
        "scrapedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "userAgent": UA_ROSTER_BOT,
        "counties": entries,
        "refused": [{"county": c, "why": w} for c, w in refused],
        # EVERY WANTED COUNTY THAT DID NOT YIELD, with why and of what kind.
        # `refused` carries only the robots subset and is kept as it was;
        # this is the full set the builder needs in order to carry a county
        # forward rather than delete it.
        "unread": sorted(unread, key=lambda u: u["fips"]),
    }
    with open(CACHE, "w") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")
    total = sum(len(e["districts"]) for e in entries.values())
    # A delay honoured without saying so cannot be told from one ignored.
    for line in pacer.report():
        print(line)
    if unread:
        print("  %d county(ies) not read this run, recorded for the builder to "
              "carry forward: %s"
              % (len(unread), ", ".join("%s (%s)" % (u["county"], u["kind"])
                                        for u in unread)))
    print("mi-commissioner-scraper: %d counties, %d districts%s -> %s"
          % (len(entries), total,
             " (%d kept from the previous run)" % kept if kept else "",
             os.path.relpath(CACHE, os.path.dirname(HERE))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
