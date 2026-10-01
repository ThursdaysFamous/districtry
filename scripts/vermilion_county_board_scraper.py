#!/usr/bin/env python3
"""
Stage 1 of the Vermilion County Board roster pipeline: scrape the county's own
County Board Members page into raw JSON for build_vermilion_county_board.py.

WHY THIS COUNTY READ AS UNREACHABLE FOR A YEAR, and why it never was. Vermilion's
gap record said its website "is not reachable from this project's network".
vercountyil.gov redirects to www.vercounty.org, and that host serves the COLES
PATTERN: its leaf certificate alone, without the GoGetSSL RSA DV CA intermediate
that signed it. Browsers fetch the missing issuer from the leaf's Authority
Information Access extension and show a perfectly normal page; requests, curl and
urllib do not chase AIA, so all three fail with "unable to get local issuer
certificate" — an error indistinguishable, in a log, from a host that is refusing
us. It is a server misconfiguration, not a refusal, and the county behind it
publishes a maintained 27-member roster.

So this scraper does the AIA chase itself: it downloads the intermediate over
plain HTTP from the URI the county's own certificate names, refuses to continue
unless the bytes hash to the pinned SHA-256 below, and then makes every request
with FULL verification against certifi's roots plus that one extra anchor.
NOTHING HERE DISABLES VERIFICATION. If the county fixes its chain this keeps
working; if it moves to another CA the pin fails loudly, which is the state a
human can act on.

WHY A SCRAPER RATHER THAN THE LAYER'S OWN COLUMNS. The county's GIS publishes
CountyBoardDistricts with Name/Party/Elected/Email columns for three members
apiece — the shape that tempts a build to skip the page entirely. It is a
snapshot: its newest Elected year is 2018 and its addresses are on a domain the
county no longer uses. Measured against this page, it is wrong about most of the
board. The Coles rule holds — AN ATTRIBUTE TABLE ON A BOUNDARY LAYER IS A
SNAPSHOT OF WHENEVER THAT LAYER WAS PUBLISHED — so geometry comes from the
county's service and PEOPLE COME FROM THIS PAGE.

WHAT THE PAGE PUBLISHES: one table, a header row plus 27 members, with columns
Name / District / Party Affiliation / Elected-Appointed / E-Mail. Four traps in
it, each handled explicitly below rather than absorbed:

  * ONE NAME IS INVERTED. Twenty-six rows read "First Last"; one reads
    "Auter, Tara". The comma form is flipped, the flip is printed on every run,
    and a row with more than one comma is left exactly as published rather than
    guessed at.
  * ROLES RIDE THE NAME CELL. "Steve Miller (Chairman)" and "Timothy McFadden
    (Vice Chairman)" carry the office in parentheses. The role is split out to
    its own field; leaving it in ships a name nobody is called.
  * ONE E-MAIL CELL CARRIES A PHONE TOO ("jhawker@vercounty.org (217) 474-8287").
    The cell is tokenised rather than taken whole, so the address stays an
    address and the phone becomes a phone instead of being lost.
  * SURNAMES ARE NOT KEYS. District 4 seats two McFaddens. Nothing downstream
    may join these records on surname.

The board office's own contact block is scraped separately from the County Board
landing page. THAT PAGE'S STAFF TABLE IS NOT THE BOARD — it lists the HR
director, the office manager and other employees alongside the chairman — so it
is never read for members.

Usage:
    python3 scripts/vermilion_county_board_scraper.py [out.json]
"""

import html
import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aia_bundle  # noqa: E402 (shared machinery — do not fork)
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    require_robots_once,
    UA_CHROME_WIN_126,
    output_path,
)

BASE = "https://www.vercounty.org"
SOURCE_URL = BASE + "/county-board/county-board-members/"
BOARD_URL = BASE + "/county-board/"

HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 60
FETCH_GAP_S = 1.5
MAX_RETRIES = 4
RETRY_AFTER_CAP_S = 60

EXPECTED_SEATS = 27
EXPECTED_DISTRICTS = 9
SEATS_PER_DISTRICT = 3

TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}")
ROLE_RE = re.compile(r"\s*\(([^)]+)\)\s*$")
YEAR_RE = re.compile(r"^(19|20)\d{2}$")


def text(fragment):
    """Tags out, entities decoded, whitespace collapsed."""
    if fragment is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def fetch(url, verify):
    """GET with the fleet's pacing rules: back off on 429/5xx, never on 4xx.

    The county's host resets a connection now and then under back-to-back
    requests, so a transport error retries like a 5xx rather than aborting.
    """
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                                label="il-vermilion-county-board-scraper")
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                                verify=verify)
        except requests.RequestException as exc:
            last = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(min(RETRY_AFTER_CAP_S, 2 ** attempt))
            continue
        if resp.status_code == 200:
            return resp.text
        if resp.status_code in (401, 403, 404):
            # A moved page is not fixed by waiting (the Henry rule).
            raise SystemExit("vermilion: %s returned HTTP %d"
                             % (url, resp.status_code))
        last = "HTTP %d" % resp.status_code
        if attempt == MAX_RETRIES:
            break
        delay = 2 ** attempt
        after = resp.headers.get("Retry-After")
        if after and after.strip().isdigit():
            delay = min(RETRY_AFTER_CAP_S, int(after.strip()))
        time.sleep(delay)
    raise SystemExit("vermilion: %s unreachable after %d attempts (%s)"
                     % (url, MAX_RETRIES, last))


def split_role(name):
    """'Steve Miller (Chairman)' -> ('Steve Miller', 'Chairman')."""
    match = ROLE_RE.search(name)
    if not match:
        return name, None
    return name[:match.start()].strip(), match.group(1).strip()


def uninvert(name, flipped):
    """'Auter, Tara' -> 'Tara Auter'; anything less obvious is left alone.

    Twenty-six of the twenty-seven rows publish "First Last" and one publishes
    the surname first. A single comma with text on both sides is unambiguous
    against that convention, so it is flipped and RECORDED — `flipped` is
    printed on every run, so this can never become a silent edit to somebody's
    name. Two commas, or a comma with nothing after it, is not obvious and is
    published exactly as the county wrote it.
    """
    parts = [p.strip() for p in name.split(",")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return name
    flipped.append(name)
    return "%s %s" % (parts[1], parts[0])


def parse_members(page):
    """The one table on the page: a header row plus one row per member."""
    tables = TABLE_RE.findall(page)
    if not tables:
        raise SystemExit("vermilion: the members page carries no table at all")
    members, flipped = [], []
    for row in ROW_RE.findall(tables[0]):
        cells = [text(c) for c in CELL_RE.findall(row)]
        if len(cells) < 5:
            continue
        name, district, party, elected, contact = cells[:5]
        if not name or name.lower() == "name" or not district.isdigit():
            continue
        name, role = split_role(name)
        name = uninvert(name, flipped)
        record = {"name": name, "district": int(district)}
        if role:
            record["role"] = role
        if party:
            record["party"] = party
        if YEAR_RE.match(elected):
            record["elected"] = elected
        # The contact cell is TOKENISED, not taken whole: one member's cell
        # carries an e-mail and a phone number in the same string.
        email = EMAIL_RE.search(contact)
        if email:
            record["email"] = email.group(0)
        phone = PHONE_RE.search(contact)
        if phone:
            record["phone"] = phone.group(0)
        members.append(record)
    return members, flipped


def parse_office(page):
    """The board office's own address and phone, from the landing page.

    Scoped to the contact block. The staff table above it lists county
    employees, not board members, and is never read here.
    """
    office = {}
    flat = re.sub(r"<[^>]+>", "\n", html.unescape(page))
    match = re.search(r"County Board Office:\s*\n+\s*Phone:\s*([\d\-() .]+)", flat)
    if match:
        office["phone"] = match.group(1).strip()
    match = re.search(r"(\d+\s+North Vermilion Street)\s*\n+\s*(2nd Floor)\s*\n+\s*"
                      r"(Danville,\s*IL\s*\d{5})", flat)
    if match:
        office["address"] = "%s, %s, %s" % match.groups()
    return office


def main():
    out_path = output_path("vermilion-board-raw.json")
    # The county serves the Coles pattern (leaf only, no GoGetSSL
    # intermediate); aia_bundle holds the pinned copy.
    verify = aia_bundle.ca_bundle("vermilion", key="gogetssl-rsa-dv")
    try:
        members_page = fetch(SOURCE_URL, verify)
        time.sleep(FETCH_GAP_S)
        board_page = fetch(BOARD_URL, verify)
    finally:
        os.unlink(verify)

    members, flipped = parse_members(members_page)
    if len(members) != EXPECTED_SEATS:
        raise SystemExit("vermilion: parsed %d members, expected %d — the "
                         "county's table has changed shape"
                         % (len(members), EXPECTED_SEATS))
    by_district = {}
    for member in members:
        by_district.setdefault(member["district"], []).append(member)
    if sorted(by_district) != list(range(1, EXPECTED_DISTRICTS + 1)):
        raise SystemExit("vermilion: the roster names districts %s, expected 1-%d"
                         % (sorted(by_district), EXPECTED_DISTRICTS))
    short = sorted(d for d in by_district if len(by_district[d]) != SEATS_PER_DISTRICT)
    if short:
        # Not fatal — a vacancy is real and the card says so — but it must be
        # visible in the run rather than discovered on the deployed site.
        print("vermilion-scraper: NOTE — district(s) %s do not seat %d members"
              % (", ".join(str(d) for d in short), SEATS_PER_DISTRICT),
              file=sys.stderr)

    payload = {
        "sourceUrl": SOURCE_URL,
        "boardUrl": BOARD_URL,
        "office": parse_office(board_page),
        "members": members,
    }
    with open(out_path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("vermilion-scraper: %d members across %d districts -> %s"
          % (len(members), len(by_district), out_path))
    print("  with e-mail: %d; with phone: %d; roles: %s"
          % (sum(1 for m in members if m.get("email")),
             sum(1 for m in members if m.get("phone")),
             ", ".join("%s (%s)" % (m["name"], m["role"])
                       for m in members if m.get("role")) or "none"))
    if flipped:
        print("  name(s) published surname-first and flipped: %s"
              % ", ".join(flipped))


if __name__ == "__main__":
    main()
