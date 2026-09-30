#!/usr/bin/env python3
"""
Fetch Iowa's 99 county auditors from the Iowa State Association of County
Auditors' own directory (iowaauditors.org), and cache the result for
build_ia_county_auditors.py.

WHY THIS PAGE
-------------
Iowa Code 47.2 designates the county auditor as each county's own election
commissioner. The auditors' own trade association
(https://iowaauditors.org/find/directory/)
publishes one entry per county on a single page — server-rendered, no
JavaScript required — carrying the auditor's name, party (as a Font Awesome
icon class, not text — verified 2026-08-28: `fa-republican` / `fa-democrat`,
present on 94 of 99 entries; the other 5 carry no party icon at all, and this
scraper ships those rows with party omitted rather than guessing), the office
name and mailing address, and a phone number. No e-mail is published anywhere
on the page.

A SECOND SOURCE, AND A CORRECTION TO THIS FILE'S OWN RECORD
------------------------------------------------------------
Until 2026-08-28 this docstring said there was "no statewide roster published
by the Secretary of State's office in a form this project can read", because
sos.iowa.gov/auditors "links out to each county's own page rather than listing
names itself". THAT WAS WRONG, and it was wrong in the way this project keeps
learning: the page's county DROPDOWN is a list of links, and the names were
read off the dropdown instead of off the page body underneath it. The body
carries a full card per county -- an <h2> naming the county, an <h3> naming
the auditor with a party letter, and a contact table -- for all 99.

So the association supplies the office address and phone (which the SoS does
not format usefully), and the SoS supplies the two fields the association
publishes nowhere: an E-MAIL ADDRESS and a party that does not depend on an
icon class. Both are merged here, and the merge is GATED on the two sources
naming the same person -- a divergence is reported and the SoS field dropped,
never silently preferred, because two directories disagreeing about who holds
an office is exactly the case where guessing is forbidden.

THE APOSTROPHE TRAP, AND WHY THE COUNTY NAME COMES FROM THE HEADING TEXT.
Each SoS card is anchored by an id built from the county name -- and O'Brien's
is `id="O'BrienCountyAuditor"`, apostrophe included. A parse keyed on the id
with an `[A-Za-z]+CountyAuditor` pattern silently returns 98 of 99. The county
name is therefore read from the <h2>'s own TEXT ("Adair", "Black Hawk",
"O'Brien"), which matches state-counties.json's BASENAME exactly for all 99
and never has to be un-camel-cased at all.

E-MAILS ARE CLOUDFLARE-OBFUSCATED. Every address on the SoS page is published
as `<span class="__cf_email__" data-cfemail="...">`, the same protection that
silently emptied Brown County's seven e-mails in the Illinois instance (see
scripts/check_roster_retention.py). The hex payload's first byte is an XOR key
for the rest; decode_cfemail below reverses it. A parser that reads the
rendered text instead gets the literal string "[email protected]" 99 times.

Each entry's county name (the <h2> link text, e.g. "Black Hawk", "O'Brien")
matches ia/data/app/state-counties.json's BASENAME field exactly for all 99
counties (verified 2026-08-28) — no alias table needed for the join.

Usage:
    python3 ia/scripts/ia_county_auditor_scraper.py
"""

import html as html_mod
import json
import os
import re
import sys

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import require_robots_once  # noqa: E402  (FLEET_SHARED)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_PATH = os.path.join(CACHE_DIR, "ia_county_auditors.json")

DIRECTORY_URL = "https://iowaauditors.org/find/directory/"
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)"}

EXPECT_COUNTIES = 99

LISTING_RE = re.compile(r'<div class="auditorListing"')
COUNTY_NAME_RE = re.compile(r'<h2><a href="/[^"]+/">([^<]+)</a></h2>')
NAME_PARTY_RE = re.compile(
    r'<div class="contentDetails">\s*<b>\s*([^<]+?)\s*(?:<i class="f[a-z]{2} (fa-[a-z\-]+)"[^>]*></i>)?\s*</b>',
    re.IGNORECASE,
)
OFFICE_RE = re.compile(
    r'fa-map-marker-alt.*?<div class="contentDetails">\s*<b>([^<]+)</b><br>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
PHONE_RE = re.compile(
    r'fa-phone.*?<div class="contentDetails"><b>Phone</b><br>([^<]+)</div>',
    re.IGNORECASE | re.DOTALL,
)

PARTY_LABELS = {"fa-republican": "Republican", "fa-democrat": "Democratic"}


def fetch(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="ia-ia-county-auditor-scraper")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def split_listings(html):
    starts = [m.start() for m in LISTING_RE.finditer(html)]
    if not starts:
        raise RuntimeError("no auditorListing blocks found on %s" % DIRECTORY_URL)
    starts.append(len(html))
    # back up each start to the enclosing <div ...> so the block is self-contained
    blocks = []
    for i in range(len(starts) - 1):
        div_start = html.rfind("<div", 0, starts[i] + 1)
        blocks.append(html[div_start:starts[i + 1]])
    return blocks


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def parse_address(raw):
    # e.g. "400 Public Square<br>Suite 5<br>        Greenfield, IA 50849  "
    lines = [clean(x) for x in raw.split("<br>")]
    return [x for x in lines if x]


def parse_block(block):
    cm = COUNTY_NAME_RE.search(block)
    if not cm:
        raise RuntimeError("a listing block has no county name: %r" % block[:200])
    county = cm.group(1).strip()

    nm = NAME_PARTY_RE.search(block)
    if not nm:
        raise RuntimeError("%s: no auditor name found" % county)
    name = clean(nm.group(1))
    party_class = nm.group(2)
    party = PARTY_LABELS.get(party_class) if party_class else None

    om = OFFICE_RE.search(block)
    office = clean(om.group(1)) if om else None
    address = parse_address(om.group(2)) if om else []

    pm = PHONE_RE.search(block)
    phone = clean(pm.group(1)) if pm else None

    return {
        "county": county,
        "name": name,
        "party": party,
        "office": office,
        "address": address,
        "phone": phone,
    }


SOS_URL = "https://sos.iowa.gov/auditors/"
# sos.iowa.gov refuses this project's own short UA; a browser UA gets 200.
SOS_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
}
SOS_BLOCK_RE = re.compile(
    r'<h2[^>]*id="[^"]*CountyAuditor"[^>]*>([^<]+)</h2>(.*?)'
    r'(?=<h2[^>]*id="[^"]*CountyAuditor"|\Z)', re.S)
SOS_NAME_RE = re.compile(r"<h3[^>]*>([^<]+)</h3>")
SOS_CFEMAIL_RE = re.compile(r'data-cfemail="([0-9a-fA-F]+)"')
# The SoS prints a party letter after the name. "(N)" is Iowa's own "no party"
# registration, not a party -- it is recognised so the letter is stripped from
# the NAME (Ida's auditor read "Kristy Gilbert (N)" otherwise), and left with no
# party rather than being invented into one. An unrecognised letter FAILS.
PARTY_LETTER = {"R": "Republican", "D": "Democrat", "I": "Independent", "N": None}
MIN_SOS_COUNTIES = 95

# WHERE THE TWO DIRECTORIES DISAGREE ABOUT WHO HOLDS THE OFFICE.
# Three counties diverge, and the counties' OWN websites -- fetched 2026-08-28,
# a third witness that is neither of the two disagreeing sources -- do not all
# resolve the same way. NEITHER DIRECTORY WINS CATEGORICALLY, which is why this
# is a pinned table of measurements and not a rule about which source to prefer:
#
#   Wapello   association "Kelly Spurgeon"        SoS "Danielle Weller"
#             wapellocounty.org/auditor/ names WELLER -- the association is stale.
#   Webster   association "Shaunna Abrams"        SoS "Krystal Lloyd"
#             webstercountyia.gov names LLOYD     -- the association is stale.
#   Harrison  association "Megan Pauley Reffett"  SoS "Megan Pauley Reffet"
#             harrisoncounty.iowa.gov/auditor/ names REFFETT -- the SoS has the typo.
#
# An UNPINNED divergence is never merged: the SoS fields are dropped, the row
# keeps the association's name, and the run says so. Pins carry the witness that
# decided them so the next reader can re-check the same page.
DIVERGENCE_RESOLVED = {
    "Wapello": ("sos", "https://www.wapellocounty.org/auditor/"),
    "Webster": ("sos", "https://www.webstercountyia.gov/departments/"
                       "auditor_commissioner_of_elections/index.php"),
    "Harrison": ("association", "https://harrisoncounty.iowa.gov/auditor/"),
}


def decode_cfemail(hexstr):
    """Cloudflare e-mail obfuscation: byte 0 is the XOR key for the rest."""
    key = int(hexstr[:2], 16)
    return "".join(chr(int(hexstr[i:i + 2], 16) ^ key)
                   for i in range(2, len(hexstr), 2))


def fetch_sos():
    """Name + party + e-mail per county from the Secretary of State's page."""
    require_robots_once(SOS_URL, SOS_HEADERS["User-Agent"], headers=SOS_HEADERS,
                        label="ia-ia-county-auditor-scraper")
    resp = requests.get(SOS_URL, headers=SOS_HEADERS, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError("%s: HTTP %d" % (SOS_URL, resp.status_code))
    rows = {}
    for m in SOS_BLOCK_RE.finditer(resp.text):
        county = html_mod.unescape(m.group(1)).strip()   # trap: NOT the anchor id
        block = m.group(2)
        nm = SOS_NAME_RE.search(block)
        if not nm:
            continue
        name = html_mod.unescape(nm.group(1)).strip()
        party = None
        pm = re.match(r"^(.*?)\s*\(([A-Za-z]{1,2})\)\s*$", name)
        if pm:
            letter = pm.group(2).upper()
            if letter not in PARTY_LETTER:
                raise RuntimeError(
                    "sos.iowa.gov printed an unrecognised party letter %r for %s "
                    "(%r) -- add it to PARTY_LETTER deliberately rather than "
                    "letting it ride along inside the name"
                    % (letter, county, name))
            name, party = pm.group(1).strip(), PARTY_LETTER[letter]
        em = SOS_CFEMAIL_RE.search(block)
        rows[county] = {
            "name": name,
            "party": party,
            "email": decode_cfemail(em.group(1)) if em else None,
        }
    if len(rows) < MIN_SOS_COUNTIES:
        raise RuntimeError(
            "sos.iowa.gov/auditors yielded %d county cards (floor %d) -- the page "
            "reshaped, or the parse fell back onto the county dropdown instead of "
            "the card bodies" % (len(rows), MIN_SOS_COUNTIES))
    return rows


def surname(name):
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    return parts[-1].lower().strip(".,") if parts else ""


def main():
    html = fetch(DIRECTORY_URL)
    blocks = split_listings(html)
    if len(blocks) != EXPECT_COUNTIES:
        raise RuntimeError(
            "iowaauditors.org listed %d auditorListing blocks, expected %d"
            % (len(blocks), EXPECT_COUNTIES)
        )

    records = [parse_block(b) for b in blocks]

    no_phone = [r["county"] for r in records if not r["phone"]]
    if no_phone:
        raise RuntimeError("%d counties carried no phone number: %s" % (len(no_phone), no_phone))
    no_address = [r["county"] for r in records if not r["address"]]
    if no_address:
        raise RuntimeError("%d counties carried no office address: %s" % (len(no_address), no_address))
    no_party = [r["county"] for r in records if not r["party"]]
    print(
        "iowaauditors.org: %d counties, %d with a party icon, %d without (%s)"
        % (len(records), len(records) - len(no_party), len(no_party), no_party),
        file=sys.stderr,
    )

    # ---- enrich from the Secretary of State: e-mail, and party where the
    # association published no icon. Gated on the two sources naming the same
    # person; a divergence drops the SoS fields and is reported, never merged.
    sos = fetch_sos()
    added_email = added_party = diverged = resolved = 0
    for r in records:
        s_rec = sos.get(r["county"])
        if not s_rec or not s_rec.get("name"):
            continue
        if surname(s_rec["name"]) != surname(r["name"]):
            pin = DIVERGENCE_RESOLVED.get(r["county"])
            if not pin:
                print("  UNPINNED DIVERGENCE %s: association %r vs SoS %r -- SoS "
                      "fields dropped. Check the county's own auditor page and add "
                      "a DIVERGENCE_RESOLVED entry naming the witness."
                      % (r["county"], r["name"], s_rec["name"]), file=sys.stderr)
                diverged += 1
                continue
            winner, witness = pin
            print("  divergence %s: association %r vs SoS %r -- %s wins per %s"
                  % (r["county"], r["name"], s_rec["name"], winner, witness),
                  file=sys.stderr)
            resolved += 1
            if winner == "sos":
                r["name"] = s_rec["name"]
                r["party"] = s_rec["party"] or r.get("party")
            # either way the e-mail below still applies: both directories agree
            # it is the OFFICE's address, and it is the same person's office.
        if s_rec.get("email") and not r.get("email"):
            r["email"] = s_rec["email"]
            added_email += 1
        if s_rec.get("party") and not r.get("party"):
            r["party"] = s_rec["party"]
            added_party += 1
    print("sos.iowa.gov: %d county cards, +%d e-mail, +%d party, %d resolved "
          "divergence(s), %d unpinned" % (len(sos), added_email, added_party,
                                          resolved, diverged), file=sys.stderr)
    stale_pins = sorted(set(DIVERGENCE_RESOLVED) - {r["county"] for r in records})
    if stale_pins:
        raise RuntimeError("DIVERGENCE_RESOLVED names %s, which is not an Iowa "
                           "county in this run" % stale_pins)
    if diverged > 3:
        raise RuntimeError(
            "%d UNPINNED divergences between the association and the Secretary of "
            "State (ceiling 3) -- that is a directory-wide change, not a handful "
            "of counties, and needs a human before any of it ships" % diverged)
    if added_email < MIN_SOS_COUNTIES:
        raise RuntimeError(
            "only %d auditors gained an e-mail (floor %d) -- either the SoS page "
            "stopped publishing them or the Cloudflare decode broke"
            % (added_email, MIN_SOS_COUNTIES))

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, indent=1)
    print("wrote %d county auditor records -> %s" % (len(records), OUT_PATH), file=sys.stderr)


if __name__ == "__main__":
    main()
