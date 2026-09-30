#!/usr/bin/env python3
"""
Stage 1 of the Clinton County Board roster pipeline: scrape the county's own
board page into raw JSON for build_clinton_county_board.py, and RE-CHECK the
district composition against the Clerk's results system in the same run.

TWO SOURCES, TWO JOBS — the Crawford/Edgar/Franklin shape. The PEOPLE come from
clintonco.illinois.gov, which publishes all fifteen members grouped under
District #1 through #5, each with a phone, an e-mail and the year their term
expires, and names the Board Chairman and Vice Chairman above the grid. The
GEOMETRY is derived from the county's certified per-precinct returns
(build_clinton_boundaries.py), and this module re-reads the district shape from
those returns every week as the §3.5.1 step-6 tripwire.

THE PAGE IS A COLUMN GRID, and each member is one <div class="col"> holding a
<strong> name, a phone line, a mailto: link and a "Term Expires: YYYY" line,
under an <h3>District #n</h3> heading. Parsing walks those headings, so a member
is only ever attributed to the district whose block contains them.

ONE E-MAIL IS A PERSONAL ADDRESS (a gmail account) among fourteen on the
county's own domain. It ships as published: the county prints it as that
member's contact, and substituting a county address the county did not print
would be inventing one.

NO HOME ADDRESSES EXIST ON THIS PAGE and none are collected; the Madison/Peoria
rule is asserted on the built payload anyway, because the guard costs nothing
and the page could change.

THE CHAIR AND VICE CHAIR are the county's own labels, printed above the grid
("Board Chairman: …", "Vice Chairman: …"), and are matched onto the member rows
by name. A label that matches no member is a hard failure rather than a badge
attached to nobody.

Usage:
    python3 scripts/clinton_county_board_scraper.py [-o raw.json]
"""

import os
import argparse
import html
import json
import re
import sys

import requests
from scraper_common import make_fail, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_common import require_robots_once  # noqa: E402  (shared machinery)

BOARD_URL = "https://clintonco.illinois.gov/county-offices/county-board/"
# The Clerk's results system: county 10, race category 8 is COUNTY BOARD.
RESULTS_URL = "https://platinumelectionresults.com/turnouts/county/10"
RACE_URL = "https://platinumelectionresults.com/history/races/2026_gp/10/8"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

EXPECTED_DISTRICTS = ("1", "2", "3", "4", "5")
EXPECTED_MEMBERS = 15
MIN_PHONES = 13
MIN_EMAILS = 13
EXPECTED_PRECINCT_COUNTS = {"1": 7, "2": 9, "3": 6, "4": 5, "5": 7}
EXPECTED_TOTAL_PRECINCTS = 34

DISTRICT_RE = re.compile(r"<h3>\s*District\s*#?\s*(\d+)\s*</h3>", re.I)
COL_RE = re.compile(r'<div class="col[^"]*"[^>]*>(.*?)</div>', re.S)
NAME_RE = re.compile(r"<strong>(.*?)</strong>", re.S)
PHONE_RE = re.compile(r"\b(\d{3}-\d{3}-\d{4})\b")
MAILTO_RE = re.compile(r"mailto:([^\"'>\s]+)")
TERM_RE = re.compile(r"Term\s+Expires:\s*(\d{4})", re.I)
CHAIR_RE = re.compile(r"Board\s+Chairman:\s*([^<]+)", re.I)
VICE_RE = re.compile(r"Vice\s+Chairman:\s*([^<]+)", re.I)
STREET_RE = re.compile(
    r"\d+\s+\S+\s*(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|"
    r"blvd|hwy|way|circle|cir|place|pl|trail)\b", re.I)


fail = make_fail("clinton-board-scraper")


def get(url):
    try:
        require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                            label="il-clinton-county-board-scraper")
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — any failure is a refusal to write
        fail("could not read %s (%s: %s)" % (url, type(exc).__name__, exc))
    return resp.text


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scrape_members(page, warnings):
    """-> ({district: [member]}, chair, vice). Members are read only from
    inside the block their own district heading opens."""
    heads = list(DISTRICT_RE.finditer(page))
    if not heads:
        fail("no 'District #n' headings on the board page — its layout changed, "
             "and a positional read would attribute members to the wrong district")
    roster = {}
    for index, match in enumerate(heads):
        dnum = match.group(1)
        end = heads[index + 1].start() if index + 1 < len(heads) else len(page)
        block = page[match.end():end]
        members = []
        for col in COL_RE.finditer(block):
            body = col.group(1)
            # WALK EVERY <strong>, not just the first. Two of the fifteen
            # members open their column with <strong><img …></strong> — a photo
            # wrapped in the same tag the name uses — so reading only the first
            # match cleans to an empty string and drops the member silently.
            # That is exactly how Kurt Schmitz went missing on the first run,
            # with every other count still passing.
            name = ""
            for candidate in NAME_RE.finditer(body):
                text = clean(candidate.group(1))
                if text and not re.match(r"(?i)district\s*#?\s*\d+$", text):
                    name = text
                    break
            if not name:
                continue
            member = {"name": name, "district": dnum}
            phone = PHONE_RE.search(clean(body))
            if phone:
                member["phone"] = phone.group(1)
            email = MAILTO_RE.search(body)
            if email:
                member["email"] = html.unescape(email.group(1)).strip()
            term = TERM_RE.search(clean(body))
            if term:
                member["termExpires"] = term.group(1)
            members.append(member)
        if members:
            roster[dnum] = members
    chair = CHAIR_RE.search(page)
    vice = VICE_RE.search(page)
    return roster, clean(chair.group(1)) if chair else None, \
        clean(vice.group(1)) if vice else None


def check_composition(warnings):
    """The §3.5.1 step-6 tripwire, in two cheap reads: the county's live
    precinct count, and each numbered board contest's precinct count in the
    newest board election."""
    turnout = get(RESULTS_URL)
    match = re.search(r"([\d,]+)\s*\n?\s*Total Precincts",
                      re.sub(r"<[^>]+>", "\n", turnout))
    if not match:
        fail("could not read the live precinct count from %s" % RESULTS_URL)
    total = int(match.group(1).replace(",", ""))
    if total != EXPECTED_TOTAL_PRECINCTS:
        fail("the Clerk's system now reports %d precincts, not %d — Clinton has "
             "re-precincted and the shipped dissolve no longer describes it"
             % (total, EXPECTED_TOTAL_PRECINCTS))

    race = get(RACE_URL)
    lines = [l.strip() for l in
             re.sub(r"<[^>]+>", "\n",
                    re.sub(r'(?is)<script.*?</script>', "", race)).split("\n") if l.strip()]
    counts = {}
    for i, line in enumerate(lines):
        if not line.upper().startswith("FOR COUNTY BOARD DISTRICT"):
            continue
        dnum = line.upper().split("DISTRICT")[1].strip().split()[0]
        got = re.match(r"\d+ of (\d+) precincts",
                       lines[i + 1] if i + 1 < len(lines) else "")
        if got:
            counts.setdefault(dnum, set()).add(int(got.group(1)))
    if not counts:
        fail("no numbered County Board contest found at %s — the newest board "
             "election this tripwire reads has moved" % RACE_URL)
    if any(len(v) != 1 for v in counts.values()):
        fail("a district reported two different precinct counts in one election: "
             "%s" % {d: sorted(v) for d, v in counts.items()})
    got = {d: v.pop() for d, v in counts.items()}
    if got != EXPECTED_PRECINCT_COUNTS:
        fail("the certified board contests now cover %s precincts per district, "
             "not %s — Clinton redistricted or re-precincted, and the dissolved "
             "boundary is stale (scripts/build_clinton_boundaries.py)"
             % (got, EXPECTED_PRECINCT_COUNTS))
    return got


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("-o", "--out", default="clinton_county_board_raw.json")
    args = parser.parse_args()

    warnings = []
    roster, chair, vice = scrape_members(get(BOARD_URL), warnings)

    districts = sorted(roster, key=int)
    total = sum(len(v) for v in roster.values())
    if tuple(districts) != EXPECTED_DISTRICTS:
        fail("the board page groups districts %s, expected %s"
             % (districts, list(EXPECTED_DISTRICTS)))
    if total != EXPECTED_MEMBERS:
        fail("%d members parsed, expected %d" % (total, EXPECTED_MEMBERS))
    phones = sum(1 for ms in roster.values() for m in ms if m.get("phone"))
    emails = sum(1 for ms in roster.values() for m in ms if m.get("email"))
    if phones < MIN_PHONES:
        fail("%d members carry a phone, floor is %d" % (phones, MIN_PHONES))
    if emails < MIN_EMAILS:
        fail("%d members carry an e-mail, floor is %d" % (emails, MIN_EMAILS))
    names = {m["name"] for ms in roster.values() for m in ms}
    for label, who in (("Board Chairman", chair), ("Vice Chairman", vice)):
        if not who:
            fail("the board page no longer prints a %s" % label)
        if who not in names:
            fail("the page names %s as %s, who is not one of the fifteen members "
                 "— the badge would attach to nobody" % (who, label))
    for members in roster.values():
        for member in members:
            for key, value in member.items():
                if STREET_RE.search(str(value)):
                    fail("a street address reached %s's %s (%r)"
                         % (member["name"], key, value))

    counts = check_composition(warnings)

    payload = {
        "boardUrl": BOARD_URL,
        "resultsUrl": RESULTS_URL,
        "chair": chair,
        "viceChair": vice,
        "districts": {d: roster[d] for d in districts},
        "compositionCheck": {"precinctsPerDistrict": counts,
                             "totalPrecincts": EXPECTED_TOTAL_PRECINCTS,
                             "raceUrl": RACE_URL},
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print("clinton-board-scraper: %d members across %d districts (%d phones, "
          "%d e-mails; Chairman %s, Vice Chairman %s) -> %s"
          % (total, len(districts), phones, emails, chair, vice, args.out),
          file=sys.stderr)
    print("  composition unchanged: %s precincts per district, %d total"
          % (counts, EXPECTED_TOTAL_PRECINCTS), file=sys.stderr)
    for warning in warnings:
        print("  note: %s" % warning, file=sys.stderr)


if __name__ == "__main__":
    main()
