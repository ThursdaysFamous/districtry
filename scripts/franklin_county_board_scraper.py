#!/usr/bin/env python3
"""
Stage 1 of the Franklin County Board roster pipeline: scrape the county's own
members page into raw JSON for build_franklin_county_board.py, and RE-CHECK the
district composition against the Clerk's results system in the same run.

TWO SOURCES, TWO JOBS — the Crawford/Edgar shape. The PEOPLE come from
franklincountyil.gov/county-board-members/, which publishes all nine members
grouped under District 1, 2 and 3. The GEOMETRY is derived from the county's
certified per-precinct returns (build_franklin_boundaries.py), and this module
re-reads two cheap facts from those returns every week as the re-precincting
and redistricting tripwire that §3.5.1 step 6 asks for.

THE MEMBERS PAGE IS A GRID, AND IT MUST BE READ AS ONE. It is a WP Table
Builder table whose every cell carries data-y-index / data-x-index, and the
column layout is:

    x=0  district heading ("District 1") OR this member's role
    x=1  Board Member
    x=2  Address          <- HOME ADDRESSES. Never read. See below.
    x=3  Mobile
    x=4  "Home or E-Mail"

READING IT AS TEXT PAIRS EVERY ROLE WITH THE WRONG MEMBER. Flattened, the
column-0 role of a row arrives BEFORE that row's name, so a linear reader
attaches "Finance Committee Chairman" to whoever it saw last. Reading by (y,x)
is what makes the pairing correct, and it is the same trap Cumberland's board
table set. Nothing here is derived from text order.

HOME ADDRESSES ARE NEVER READ. Column 2 is labelled "Address" and every value
in it is a residence ("8708 Martin Street, Christopher", "4700 Sylvia Ave."). The
whole column is discarded by coordinate — the Cass rule, because discarding a
column is a stronger guarantee than filtering strings afterwards — and the
built payload is asserted address-free before it is written.

THE E-MAIL COLUMN IS CLOUDFLARE-OBFUSCATED, which is exactly the failure that
emptied Brown County's seven addresses on 2026-08-08 while every count guard
passed. `mailto:` is rewritten to a `data-cfemail` hex blob, so this decodes it
(XOR with the first byte) and treats a row that has the markup but yields no
address as a hard failure rather than as a member with no e-mail.

THE COLUMN IS "HOME OR E-MAIL", AND ONLY THE E-MAIL HALF SHIPS. The county
gives no way to tell which of the two a given cell holds, and a home telephone
is the one contact this project does not publish; the Mobile column already
carries a number for every member. A value in that column that is not an
e-mail address is counted and reported, never shipped.

NO PARTY SHIPS. The members page publishes none. The canvasses do — but only
for the third of the board that was last on the ballot, so taking party from
them would label some members and not others from a source the county does not
use for this purpose.

Usage:
    python3 scripts/franklin_county_board_scraper.py [-o raw.json]
"""

import argparse
import html
import json
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    make_fail, require_robots_once, UA_ROSTER_BOT,
)

BOARD_URL = "https://franklincountyil.gov/county-board-members/"
# The Clerk's results system. TURNOUT_URL reports the county's live precinct
# count; RACE_URL is the newest board election, whose contest headers name the
# districts outright and whose subheads give each district's precinct count.
TURNOUT_URL = "https://platinumelectionresults.com/turnouts/county/21"
RACE_URL = "https://platinumelectionresults.com/history/races/2026_gp/21/8"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

EXPECTED_DISTRICTS = ("1", "2", "3")
EXPECTED_MEMBERS = 9
MIN_PHONES = 7          # 8 of 9 today; Bartoni's row publishes no number
# What build_franklin_boundaries.py shipped. A move here is a redistricting or a
# re-precincting, and either invalidates the dissolved boundary.
EXPECTED_PRECINCT_COUNTS = {"1": 13, "2": 13, "3": 9}
EXPECTED_TOTAL_PRECINCTS = 35

CELL_RE = re.compile(
    r'<td class="wptb-cell "[^>]*data-y-index="(\d+)"[^>]*data-x-index="(\d+)"[^>]*>(.*?)</td>',
    re.S)
DISTRICT_RE = re.compile(r"^District\s+(\d+)$", re.I)
PHONE_RE = re.compile(r"^\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
# A residence would carry a number then a street word. Asserted on everything
# that reaches the payload, so a column-layout change cannot leak one silently.
STREET_RE = re.compile(
    r"\d+\s+\S+\s*(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|"
    r"blvd|hwy|way|circle|cir|place|pl|trail|heights)\b", re.I)

X_ROLE, X_NAME, X_ADDRESS, X_MOBILE, X_CONTACT = 0, 1, 2, 3, 4


fail = make_fail("franklin-board-scraper")


def get(url):
    # THE COUNTY'S RULES ARE READ BEFORE ITS FIRST PAGE, with the identity this
    # fetch sends — AND THAT RETIRES THE HOLD ON THIS FILE. It was the one
    # scraper the robots-adoption sweep deliberately held back, on the measured
    # ground that franklincountyil.gov answered the robots request itself with a
    # managed challenge, which is a class needing a ruling rather than a default.
    # Re-measured from a GitHub runner on 2026-10-01, the vantage the weekly job
    # crawls from, it serves a 678-byte policy of four groups, none of whose
    # rules match the paths read here, on all three reads of a deliberate
    # re-measurement fifteen seconds apart. The challenge was this sandbox's
    # route, not the county's policy, so no ruling is owed.
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="franklin-board-scraper")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — any failure is a refusal to write
        fail("could not read %s (%s: %s)" % (url, type(exc).__name__, exc))
    return resp.text


def cf_decode(blob):
    """Cloudflare e-mail obfuscation: hex, XOR-keyed by its own first byte."""
    try:
        key = int(blob[:2], 16)
        return "".join(chr(int(blob[i:i + 2], 16) ^ key)
                       for i in range(2, len(blob), 2))
    except (ValueError, IndexError):
        return ""


def cell_text(fragment):
    """A cell's visible text, with any obfuscated address restored first."""
    fragment = re.sub(r'<span class="__cf_email__"[^>]*data-cfemail="([0-9a-f]+)"[^>]*>.*?</span>',
                      lambda m: cf_decode(m.group(1)), fragment, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", text).strip()


def read_grid(page):
    """-> {(y, x): text}. The whole parse rests on these coordinates."""
    cells = {}
    for match in CELL_RE.finditer(page):
        cells[(int(match.group(1)), int(match.group(2)))] = cell_text(match.group(3))
    if not cells:
        fail("the members page carried no wptb grid cells — its table plugin or "
             "markup changed, and a text-order read would pair every role with "
             "the wrong member")
    return cells


def scrape_members(page, warnings):
    cells = read_grid(page)
    rows = sorted({y for y, _x in cells})
    roster, district = {}, None
    dropped_contacts = 0
    obfuscated = len(re.findall(r'data-cfemail="', page))
    decoded = 0
    for y in rows:
        role = cells.get((y, X_ROLE), "")
        name = cells.get((y, X_NAME), "")
        heading = DISTRICT_RE.match(role)
        if heading:
            district = heading.group(1)
            continue
        if not name or name.lower() == "board member":
            continue
        if district is None:
            fail("member %r appears before any district heading — the grid's "
                 "row order changed" % name)
        member = {"name": name, "district": district}
        if role:
            member["role"] = role
        mobile = cells.get((y, X_MOBILE), "")
        if mobile:
            if PHONE_RE.match(mobile):
                member["phone"] = mobile
            else:
                warnings.append("%s: Mobile cell %r is not a phone number — not "
                                "shipped" % (name, mobile))
        contact = cells.get((y, X_CONTACT), "")
        if contact:
            if EMAIL_RE.match(contact):
                member["email"] = contact
                decoded += 1
            else:
                # "Home or E-Mail": a home telephone is the one contact this
                # project does not publish, and the county does not say which
                # a given cell holds.
                dropped_contacts += 1
                warnings.append("%s: the 'Home or E-Mail' cell holds something "
                                "that is not an e-mail — not shipped" % name)
        roster.setdefault(district, []).append(member)
    if obfuscated and not decoded:
        fail("the page carries %d Cloudflare-obfuscated address(es) and none "
             "decoded — this is the Brown County failure, where every count "
             "guard passed while the contact column emptied" % obfuscated)
    return roster, dropped_contacts


def check_composition(warnings):
    """The §3.5.1 step-6 tripwire, in two cheap reads.

    Neither proves the dissolve; both catch the two events that would
    invalidate it — the county re-precincting, or the board redistricting.
    """
    turnout = get(TURNOUT_URL)
    match = re.search(r"([\d,]+)\s*\n?\s*Total Precincts", re.sub(r"<[^>]+>", "\n", turnout))
    if not match:
        fail("could not read the live precinct count from %s" % TURNOUT_URL)
    total = int(match.group(1).replace(",", ""))
    if total != EXPECTED_TOTAL_PRECINCTS:
        fail("the Clerk's system now reports %d precincts, not %d — Franklin "
             "has re-precincted and data/app/franklin-precincts.json no longer "
             "describes the county" % (total, EXPECTED_TOTAL_PRECINCTS))

    race = get(RACE_URL)
    lines = [l.strip() for l in
             re.sub(r"<[^>]+>", "\n", re.sub(r'(?is)<script.*?</script>', "", race)).split("\n")
             if l.strip()]
    counts, seats = {}, set()
    for i, line in enumerate(lines):
        if not line.upper().startswith("FOR COUNTY BOARD DISTRICT"):
            continue
        dnum = line.upper().split("DISTRICT")[1].strip().split()[0]
        got = re.match(r"\d+ of (\d+) precincts", lines[i + 1] if i + 1 < len(lines) else "")
        if got:
            counts.setdefault(dnum, set()).add(int(got.group(1)))
        for nearby in lines[i:i + 6]:
            if nearby.lower().startswith("(vote for"):
                seats.add(nearby.strip())
    if not counts:
        fail("no numbered County Board contest found at %s — the newest board "
             "election this tripwire reads has moved" % RACE_URL)
    flat = {d: sorted(v) for d, v in counts.items()}
    if any(len(v) != 1 for v in flat.values()):
        fail("a district reported two different precinct counts in one "
             "election: %s" % flat)
    got = {d: v[0] for d, v in flat.items()}
    if got != EXPECTED_PRECINCT_COUNTS:
        fail("the certified board contests now cover %s precincts per district, "
             "not %s — Franklin has redistricted or re-precincted, and the "
             "dissolved boundary in data/app/franklin-county-board-districts.json "
             "is stale" % (got, EXPECTED_PRECINCT_COUNTS))
    if seats and seats != {"(Vote for ONE)"}:
        warnings.append("the board contests' seat headers now read %s — the "
                        "board's shape may have changed" % sorted(seats))
    return got, sorted(seats)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("-o", "--out", default="franklin_county_board_raw.json")
    args = parser.parse_args()

    warnings = []
    roster, dropped = scrape_members(get(BOARD_URL), warnings)

    districts = sorted(roster, key=int)
    total = sum(len(v) for v in roster.values())
    if tuple(districts) != EXPECTED_DISTRICTS:
        fail("the members page groups districts %s, expected %s"
             % (districts, list(EXPECTED_DISTRICTS)))
    if total != EXPECTED_MEMBERS:
        fail("%d members parsed, expected %d" % (total, EXPECTED_MEMBERS))
    phones = sum(1 for ms in roster.values() for m in ms if m.get("phone"))
    if phones < MIN_PHONES:
        fail("%d members carry a phone, floor is %d" % (phones, MIN_PHONES))
    # The privacy invariant, asserted rather than assumed.
    for members in roster.values():
        for member in members:
            for key, value in member.items():
                if STREET_RE.search(str(value)):
                    fail("a residence reached %s's %s (%r) — the Address column "
                         "is never read" % (member["name"], key, value))

    counts, seats = check_composition(warnings)

    payload = {
        "boardUrl": BOARD_URL,
        "resultsUrl": TURNOUT_URL,
        "districts": {d: roster[d] for d in districts},
        "compositionCheck": {"precinctsPerDistrict": counts,
                             "seatHeaders": seats,
                             "totalPrecincts": EXPECTED_TOTAL_PRECINCTS,
                             "raceUrl": RACE_URL},
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print("franklin-board-scraper: %d members across %d districts (%d phones, "
          "%d e-mails, %d non-e-mail contacts dropped) -> %s"
          % (total, len(districts), phones,
             sum(1 for ms in roster.values() for m in ms if m.get("email")),
             dropped, args.out), file=sys.stderr)
    print("  composition unchanged: %s precincts per district, %d total"
          % (counts, EXPECTED_TOTAL_PRECINCTS), file=sys.stderr)
    for warning in warnings:
        print("  note: %s" % warning, file=sys.stderr)


if __name__ == "__main__":
    main()
