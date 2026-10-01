#!/usr/bin/env python3
"""
Stage 1 of the Coles County Board roster pipeline: scrape the county's own
board page (and its committees page, as the cross-check) into raw JSON for
build_coles_board_roster.py.

WHY THERE IS A SCRAPER HERE AT ALL — the trap this file exists to avoid.
Coles publishes its 12 board districts as a public ArcGIS feature layer
(County_Board_District_View/0) whose attribute table ALSO carries Official,
phone, email, party and term. That looks exactly like the McLean/Effingham
shape, where the roster rides the boundary and no scraper is needed. It is
not. Measured 2026-08-17 against the county's own board page:

    district   layer says            the county's page says
    2          Mike Clayton          Brian Ingram
    3          Michael Watts         Doug Kanouse
    4          Jeremy Doughty        Brandon Stewart
    6          Andrew McDevitt       Tom Royal
    9          Denise Corray         David Johnson
    12         Gail Mason            Bristole Zimmerman

SIX OF TWELVE NAMES ARE WRONG in the layer, plus stale phones on districts 7
and 8 and a stale e-mail on 11. The layer's item was created 2022-04-23 and
its whole attribute table is frozen at that date — its `term` column still
reads "2022" for District 11, and its `Population` column sums to 53,873,
which is Coles County's 2010 census count to the person (2020 is 46,863). So
the GEOMETRY is read from the county's service and NOTHING ELSE IS. The
roster is this scrape.

THE GENERAL RULE, worth carrying to the next county: an attribute table on a
boundary layer is a SNAPSHOT of whenever that layer was published, and a
county that republishes the boundary rarely republishes the people. Check the
names against the county's own roster page before believing a layer's roster
column — the check costs one fetch and it is the difference between a correct
card and six wrong officeholders.

THE TLS CHAIN, because this is why the county reads as "blocked" to machines.
colesco.illinois.gov serves ONLY its leaf certificate — no intermediate (the
GoDaddy Secure Certificate Authority - G2 that signed it). Browsers and search
crawlers paper over that by fetching the missing issuer from the leaf's
Authority Information Access extension ("AIA chasing"); requests, curl and
urllib do not, so all three fail with "unable to get local issuer
certificate" even though the site answers HTTP 200 with a complete page. That
is a server misconfiguration on the county's side, NOT a refusal, and the
distinction matters: the coles-county-board gap record read "both county hosts
refuse this network" for a year on the strength of that error.

So this scraper does the AIA chase itself: it downloads the intermediate from
GoDaddy's published repository over plain HTTP, refuses to continue unless the
bytes hash to the pinned SHA-256 below, and then makes every request with FULL
certificate verification against certifi's roots PLUS that intermediate.
Nothing here disables verification. If the county fixes its chain this keeps
working (an extra trust anchor is harmless); if the county moves to a
different CA the pin fails loudly, which is the state a human can act on.

WHAT THE PAGE PUBLISHES, and what it does not. Each member is one
<article class="profile-creative"> carrying a name, "District: N", and up to
three contact rows distinguished ONLY by their icon class:

    mdi-email       <a href="mailto:...">          -> shipped
    mdi-phone       <a href="tel:...">             -> shipped
    mdi-map-marker  <a href="tel:#">HOME ADDRESS   -> NEVER READ

The third is the member's RESIDENCE ("23609 E Co Rd 1300N", "1142 Buchanan
Ave") and is never parsed, never stored, never shipped — the Madison/Peoria
precedent, and note that its anchor is *also* a `tel:` href, so a parser that
keyed on hrefs rather than icons would collect home addresses by accident.

THE LITERAL STRING "None" IS NOT A VALUE. Three seats render `<a
href="tel:None">None</a>` — the CMS's Python `None` leaking through the
template — so a bare "None" in any field is dropped rather than shipped as a
phone number.

NO PARTY AND NO TERM SHIP, because the page publishes neither. The GIS layer
has both columns and both are part of the same frozen 2022 snapshot, so
taking them would be taking the one thing this file exists to reject.

THE COMMITTEES PAGE IS THE CROSS-CHECK (the Shelby posture: a county that
publishes its board twice can disagree with itself). /board/committees lists
21 committees by member name; at first ship all 12 board-page names appear
there and every name there is a board member. The scrape records both sides so
the builder can fail a half-updated site instead of shipping whichever page it
happened to read, and the committee memberships ride each member's card.

BOARD-LEVEL CONTACT. The site's navbar carries a phone and a room for the
department whose page you are on — measured per department rather than
assumed: Board (217) 348-0595 / Room 326, Treasurer (217) 348-0511 / Room 124,
Sheriff (217) 348-0585 / 701 7th St. So it is the County Board office, not a
switchboard, and it ships once at board level rather than under twelve names
(the Calhoun rule).

Usage:
    python3 coles_county_board_scraper.py [output.json]
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
    UA_CHROME_WIN_126,
    output_path,
)

BASE = "https://www.colesco.illinois.gov"
SOURCE_URL = BASE + "/board/"
COMMITTEES_URL = BASE + "/board/committees"

HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REQUEST_TIMEOUT = 60
FETCH_GAP_S = 1.0
MAX_RETRIES = 3
RETRY_AFTER_CAP_S = 60

EXPECTED_SEATS = 12

ARTICLE_RE = re.compile(
    r'<article class="profile-creative[^"]*">(.*?)</article>', re.S | re.I)
NAME_RE = re.compile(
    r'<h5 class="profile-creative-title">(.*?)</h5>', re.S | re.I)
DISTRICT_RE = re.compile(
    r'<p class="profile-creative-position">\s*District:\s*(\d+)\s*</p>', re.I)
# Each contact row is one <div class="object-inline"> whose FIRST child span
# names the icon. Keying on the icon (not the href) is what keeps the
# map-marker row — the member's home address — out of the parse entirely.
CONTACT_ROW_RE = re.compile(
    r'<div class="object-inline"[^>]*>\s*<span class="[^"]*mdi-(email|phone|map-marker)"'
    r'[^>]*>\s*</span>\s*<a[^>]*>(.*?)</a>', re.S | re.I)
NAV_PHONE_RE = re.compile(
    r'mdi-phone[^>]*>\s*</span>\s*</div>.*?<a[^>]*>\s*([^<]+?)\s*</a>', re.S | re.I)
NAV_ADDR_RE = re.compile(
    r'mdi-map-marker[^>]*>\s*</span>\s*</div>\s*<div class="unit-body">'
    r'\s*<a[^>]*>(.*?)</a>', re.S | re.I)
COMMITTEE_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}$")


def text(fragment):
    """Tags out, entities decoded, whitespace collapsed."""
    if fragment is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def fetch(url, verify):
    """GET with the fleet's pacing rules: back off on 429/5xx, never on 4xx."""
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
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
            raise SystemExit("coles: %s returned HTTP %d" % (url, resp.status_code))
        last = "HTTP %d" % resp.status_code
        if attempt == MAX_RETRIES:
            break
        delay = 2 ** attempt
        after = resp.headers.get("Retry-After")
        if after and after.strip().isdigit():
            delay = min(RETRY_AFTER_CAP_S, int(after.strip()))
        time.sleep(delay)
    raise SystemExit("coles: %s unreachable after %d attempts (%s)"
                     % (url, MAX_RETRIES, last))


def clean_value(raw):
    """Drop the CMS's literal 'None' placeholder and empty strings."""
    value = text(raw)
    if not value or value.lower() == "none":
        return None
    return value


def parse_members(page):
    members = []
    for block in ARTICLE_RE.findall(page):
        name = text(NAME_RE.search(block).group(1)) if NAME_RE.search(block) else ""
        dm = DISTRICT_RE.search(block)
        if not name or not dm:
            continue
        record = {"name": name, "district": int(dm.group(1))}
        for icon, value in CONTACT_ROW_RE.findall(block):
            icon = icon.lower()
            # map-marker is the member's HOME ADDRESS and is deliberately
            # skipped here rather than parsed-and-discarded downstream, so
            # nothing later in the pipeline can leak what was never collected.
            if icon == "map-marker":
                continue
            cleaned = clean_value(value)
            if cleaned is None:
                continue
            if icon == "email" and EMAIL_RE.match(cleaned):
                record["email"] = cleaned
            elif icon == "phone" and PHONE_RE.match(cleaned):
                record["phone"] = cleaned
        members.append(record)
    return members


def parse_committees(page):
    """{committee name: [member names]} from the committees table."""
    out = {}
    for row in COMMITTEE_ROW_RE.findall(page):
        cells = [text(c) for c in CELL_RE.findall(row)]
        if len(cells) < 2 or not cells[0]:
            continue
        if cells[0].lower() == "committee":
            continue
        names = [n.strip() for n in re.split(r"<br\s*/?>", CELL_RE.findall(row)[1],
                                             flags=re.I)]
        names = [text(n) for n in names]
        names = [n for n in names if n]
        if names:
            out[cells[0]] = names
    return out


def parse_board_contact(page):
    """The department contact block in the navbar — the Board's own office."""
    contact = {}
    pm = NAV_PHONE_RE.search(page)
    if pm:
        value = clean_value(pm.group(1))
        if value and re.search(r"\d{3}[ .-]?\d{4}", value):
            contact["phone"] = value
    am = NAV_ADDR_RE.search(page)
    if am:
        # The room and the city are separated by a <br>, so the line break
        # becomes a comma rather than collapsing into "Room 326 Charleston".
        value = clean_value(re.sub(r"<br\s*/?>", ", ", am.group(1), flags=re.I))
        if value:
            contact["address"] = value
    return contact


def main():
    out_path = output_path("coles-board-raw.json")
    # The county serves the Coles pattern this module's docstring describes;
    # aia_bundle holds the pinned GoDaddy intermediate (the one copy).
    verify = aia_bundle.ca_bundle("coles")
    try:
        board_page = fetch(SOURCE_URL, verify)
        time.sleep(FETCH_GAP_S)
        committees_page = fetch(COMMITTEES_URL, verify)
    finally:
        try:
            os.unlink(verify)
        except OSError:
            pass

    members = parse_members(board_page)
    if len(members) != EXPECTED_SEATS:
        raise SystemExit(
            "coles: parsed %d member articles, expected %d — the board page's "
            "markup has changed" % (len(members), EXPECTED_SEATS))

    committees = parse_committees(committees_page)
    if not committees:
        raise SystemExit("coles: the committees page yielded no rows — it is the "
                         "roster's only cross-check, so a silent loss fails here")

    payload = {
        "sourceUrl": SOURCE_URL,
        "committeesUrl": COMMITTEES_URL,
        "board": parse_board_contact(board_page),
        "members": members,
        "committees": committees,
    }
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print("coles: %d members, %d committees -> %s"
          % (len(members), len(committees), out_path))


if __name__ == "__main__":
    main()
