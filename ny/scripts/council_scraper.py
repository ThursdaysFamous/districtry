#!/usr/bin/env python3
"""
Scrape the 51 NYC City Council members from council.nyc.gov/districts/
(METRO_EXPANSION_PLAYBOOK §9). Stage 1 of the pipeline.

Note on source: the playbook named Legistar's People.aspx, but its "Web Site"
column (the only place the district number appears) is populated for only ~24 of
51 members. council.nyc.gov/districts/ lists all 51 with the member name in each
district card's photo alt text and the district number in the card's URL, so it
is the complete, reliable source. Writes an intermediate JSON with source_url +
scraped_at; build_council_roster.py resolves it into data/app/council-members.json.

Usage:
    python3 scripts/council_scraper.py [--out PATH]
"""

import json
import os
import re
import sys
import time
import urllib.request

URL = "https://council.nyc.gov/districts/"
UA = "Mozilla/5.0 (compatible; districtry-nyc/1.0; +https://districtry.com/ny/)"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), ".cache", "council_raw.json")

# ---------------------------------------------------------------- robots.txt
# THE FLEET'S ONE READER, scripts/robots_policy.py. APPENDED to sys.path rather
# than inserted, so ny/scripts/ keeps priority for its own siblings.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))
import robots_policy as rp                                        # noqa: E402

# WHAT THE HOST SAYS, measured 2026-09-26 as the client above sends (a browser
# string changes nothing about robots.txt, because no group names it either and
# `*` still binds): council.nyc.gov serves 131 bytes, one binding `*` group, no
# rule matching /districts/ or /district-N/, no Content-Signal — AND
# `Crawl-delay: 10`.
#
# THE DELAY WAS BEING IGNORED, AND THE SCRAPER ASKED NOTHING BEFORE FETCHING.
# This file slept 0.2 s across 52 requests against a host asking for 10, in a
# weekly scheduled job, and read no robots.txt at all — the state CLAUDE.md
# calls "the next thing to fix". Honouring it costs the weekly run about nine
# minutes of waiting and nothing else, which is the whole of the trade.
_GATE = None
_PACER = None


def _robots():
    global _GATE, _PACER
    if _GATE is None:
        _GATE = rp.RobotsGate(None, UA)
        _PACER = rp.HostPacer(_GATE)
    return _GATE, _PACER


def fetch_page(url, timeout=60):
    """One paced, permitted GET. Raises on a refusal rather than returning a
    falsy value: a refusal a caller can carry on past is one a caller will
    (scripts/scraper_common.require_robots_allowed makes the same argument, and
    is not used here because this file is stdlib-only by design)."""
    gate, pacer = _robots()
    ok, why = gate.allows(url)
    if not ok:
        raise SystemExit(
            "council_scraper: FAIL — %s refuses this client: %s. Nothing is "
            "fetched from it, and council-members.json keeps its last-good "
            "records (CLAUDE.md, Adam's ruling of 2026-09-19)." % (url, why))
    with pacer.hold(url):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def clean_name(alt):
    # photo alts read "Christopher Marte Head Shot" / "... Headshot" / "... Photo"
    name = re.sub(r"\s*(head\s*shot|headshot|photo|portrait)\s*$", "", alt, flags=re.I).strip()
    return name or None


# A LEADERSHIP OFFICE IS A PREFIX, AND clean_name() ONLY EVER STRIPPED SUFFIXES.
# Measured 2026-09-26 on the shipped roster: six of the 51 names began with the
# member's leadership post — "Speaker Julie Menin", "Majority Leader Shaun
# Abreu", "Deputy Speaker Dr. Nantasha Williams", "Minority Whip Inna Vernikov",
# "Majority Whip Kamillah M. Hanks", "Minority Leader David Carr" — because the
# Council writes the post into the district card's own photo alt text and the
# only cleanup here ran at the end of the string. So six cards named a person
# whose name is not that person's name.
#
# IT IS A CLOSED SET AND NOT A RULE ABOUT CAPITALISATION. A general "strip
# leading capitalised words" would eat part of a real name the first time the
# Council publishes one this project has not seen; these are the posts the body
# elects, from its own rules, and a post that appears and is not in this table
# leaves the name exactly as it was rather than being guessed at.
#
# `role` IS THE KEY AND `office` WAS NEVER FREE: `office` on these records is
# the district office ADDRESS, so moving a title into it would overwrite one.
LEADERSHIP_OFFICES = (
    "Speaker",
    "Deputy Speaker",
    "Majority Leader",
    "Minority Leader",
    "Majority Whip",
    "Minority Whip",
    "Deputy Leader",
    "Assistant Majority Leader",
    "Assistant Minority Leader",
)


def split_leadership(name):
    """('Deputy Speaker Dr. Nantasha Williams') -> ('Dr. Nantasha Williams',
    'Deputy Speaker'). Returns (name, None) when no post prefixes the name.

    Longest post first, so "Deputy Speaker" is never read as "Speaker" with a
    member called "Deputy". The honorific the Council prints stays on the name:
    it published "Dr. Nantasha Williams" and editing a person's own title out of
    their name is not this parser's business.
    """
    if not name:
        return name, None
    for post in sorted(LEADERSHIP_OFFICES, key=len, reverse=True):
        if name.startswith(post + " "):
            rest = name[len(post) + 1:].strip()
            if rest:
                return rest, post
    return name, None


# The District Office block on a council district page runs into a second
# ("Legislative Office") address, a phone/fax number or label, and assorted
# contact boilerplate. OFFICE_END marks where the street address ends. The old
# regex instead ran to the first "..., NY 1XXXX" ZIP, which bled through every
# page whose district office omits the ZIP (D2), drops "NY" (D43 "Brooklyn
# 11204"), spells out the state (D14 "Bronx, New York 10453"), or lists no
# street at all (D48) — swallowing the phone, fax, and the whole Legislative
# Office address into one run-on line.
OFFICE_END = re.compile(
    r"(?:"
    r"\bLegislative\s+Office\b"
    r"|\bSend\s*Email\b|\bEmail\b"
    r"|\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"   # a phone / fax number, anywhere
    r"|\bTelephone\b|\bPhone\b|\bFax\b|\bTel\b"
    r")", re.I)
# A NYC ZIP (all five digits, "1XXXX"). Used to end the address at its own ZIP so
# a trailing parenthetical or note (D17 "(Intersection…)", D40 "If you need…")
# doesn't ride along, and a page-typo sixth digit (D4 "100170") is dropped.
ZIP_RE = re.compile(r"1\d{4}")

# WHERE THE ADDRESS BEGINS, which OFFICE_END and ZIP_RE never asked. District 27
# shipped its whole appointment notice as its office address —
#   "Due to the recent COVID surge, our district office is currently open by
#    appointment only. Contact my office directly to schedule your appointment
#    today. 172-12 Linden Boulevard St. Albans, NY 11434"
# — onto the card, into the map-pin geocoder and into schema.org as the member's
# postal address, because the block was bounded at its END and never at its
# START, and the guard below (digits AND letters) passes a sentence easily.
#
# THE BLOCK CARRIES TWO KINDS OF TEXT IN FRONT OF THE STREET, AND THEY MUST BE
# TREATED OPPOSITELY. Measured 2026-09-26 across the 51 district pages: seven
# offices do not begin with a house number, and six of those seven lead with an
# office LABEL the Council publishes on purpose — "East Harlem Office:", "Gun
# Hill Road District Office", "Rockaway Office:", "Howard Beach Office:",
# "Rochdale Village/South Jamaica Office (East)", "Bay Ridge District Office" —
# which says which of a member's offices this is and is content, not noise.
# Only District 27's is prose. So a prefix is dropped ONLY when it is a
# SENTENCE (a full stop followed by a space, somewhere in it) and NOT an office
# label. Both tests, in that order, because either alone gets it wrong: cutting
# to the first house number strips all six labels, and keeping anything that is
# not a sentence keeps the notice on any page that writes it without a full
# stop.
#
# A FIRST-MATCH ANCHOR, NEVER A LAST-MATCH ONE. The obvious reading — take the
# last house-number start, since the address is at the end — is wrong on
# District 49's "130 Stuyvesant Place 6th Floor, Room 602 Staten Island, NY
# 10301", where the last such start is "602 Staten Island".
HOUSE_START = re.compile(r"\b\d{1,5}(?:-\d{1,5})?\s+[A-Z]")
SENTENCE_IN = re.compile(r"[a-z]\.\s")
# "…Office", "…Office:", "…Office (East)" — the label shapes the pages use.
LABEL_TAIL = re.compile(r"\bOffices?\b[\s:;,\-\u2013]*(?:\([^)]*\)\s*)?$", re.I)


def district_office(url):
    """Extract the clean 'District Office' street address from a member's page.

    Returns None (never a guess) when the page lists no street address — e.g.
    District 48, whose District Office block is a phone number only.
    """
    try:
        html = fetch_page(url, timeout=45)
    except SystemExit:
        raise                                  # a refusal is never swallowed
    except Exception:  # noqa: BLE001 — the office is an enhancement, never fatal
        return None
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    m = re.search(r"District Office\s+(.+)", text)
    if not m:
        return None
    tail = m.group(1)
    # 1) Bound the block before the phone/fax/second-office noise, so the ZIP we
    #    key off next is the district office's own — never the Legislative one's.
    end = OFFICE_END.search(tail)
    if end:
        tail = tail[:end.start()]
    # 2) If that block carries a ZIP, end the address right after it.
    z = ZIP_RE.search(tail)
    if z:
        tail = tail[:z.end()]
    # 3) Drop a SENTENCE in front of the street address, and keep an office
    #    label (see HOUSE_START above). A page whose office starts at its house
    #    number reaches this with an empty prefix and is untouched.
    h = HOUSE_START.search(tail)
    if h and h.start() > 0:
        prefix = tail[:h.start()]
        if SENTENCE_IN.search(prefix) and not LABEL_TAIL.search(prefix.strip()):
            tail = tail[h.start():]
    addr = re.sub(r"\s{2,}", " ", tail).strip(" ,;.-")
    # A real street address carries a house number and a street name; reject a
    # bare phone number or stray fragment so the card never shows contact noise.
    if len(addr) < 6 or not re.search(r"\d", addr) or not re.search(r"[A-Za-z]{3}", addr):
        return None
    return addr


def parse(html):
    parts = re.split(r'href="https://council\.nyc\.gov/district-(\d+)/"', html)
    roster = {}
    for i in range(1, len(parts) - 1, 2):
        num = str(int(parts[i]))
        seg = parts[i + 1][:1500]
        name = None
        for alt in re.findall(r'alt="([^"]+)"', seg):
            alt = alt.strip()
            if alt and not re.search(r"email|phone|address|logo|icon|seal", alt, re.I):
                name = clean_name(alt)
                if name:
                    break
        if name and num not in roster:
            # The post the Council writes in front of the name is a ROLE, not
            # part of it (see split_leadership).
            roster[num] = split_leadership(name)
    return roster


def main():
    argv = sys.argv[1:]
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT

    html = fetch_page(URL, timeout=60)
    roster = parse(html)
    scraped_at = os.environ.get("SCRAPED_AT") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    records = {}
    for district, (name, role) in roster.items():
        url = "https://council.nyc.gov/district-%s/" % district
        rec = {
            "name": name,
            "office": district_office(url),  # None if the page omits it — never guessed
            "source_url": url,
            "scraped_at": scraped_at,
        }
        if role:
            rec["role"] = role
        records[district] = rec

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"members": records}, f, indent=2, ensure_ascii=False)
    print("wrote %s: %d council members" % (out_path, len(records)), file=sys.stderr)
    roles = sorted((d, r["role"]) for d, r in records.items() if r.get("role"))
    print("leadership posts split off the name: %d — %s"
          % (len(roles), ", ".join("D%s %s" % (d, r) for d, r in roles)), file=sys.stderr)
    # An honoured Crawl-delay that says nothing cannot be told from an ignored one.
    for line in _PACER.report():
        print(line, file=sys.stderr)


if __name__ == "__main__":
    main()
