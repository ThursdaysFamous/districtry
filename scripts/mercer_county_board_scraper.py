#!/usr/bin/env python3
"""
Stage 1 of the Mercer County Board roster pipeline: scrape the county's own
board page into raw JSON for build_mercer_county_board.py, and RE-READ the
district composition out of the Clerk's live results feed in the same run.

TWO SOURCES, TWO JOBS — the Crawford shape. The people come from
mercercountyil.org's County Board page, a plain three-column table: a district
label in column 1 (on the first of that district's two rows only), the member
in column 2 as "<name> (<party>) <home town>", optionally ", CHAIRMAN" and a
phone, and the member's TERM-EXPIRY month/year in column 3. The DISTRICTS come
from il-mercer.pollresults.net, the Clerk's own results system, whose entire
certified result set is embedded in the page as JSON — that is where the
shipped boundaries' composition came from (build_mercer_boundaries.py), and
re-reading it weekly is the re-precincting / redistricting tripwire.

WHY THE COMPOSITION IS RE-READ HERE: Mercer's board districts ARE a dissolve
of its voting precincts, so the boundary is correct only while the election
authority keeps tabulating the same precincts in the same districts. Nothing
on the board page would ever show that moving, and the county's only map is a
2021 scan. The feed carries one election, so a run checks whichever districts
were on that ballot and reports the rest as unchecked.

HOME TOWNS, NOT HOME ADDRESSES. The page prints a town beside each member —
"Becky Hawn (R) Keithsburg" — which is how the county identifies who represents
where, and is not a street address. It ships as the member's note. If this page
ever starts printing street addresses, they do NOT ship (the Madison/Peoria
rule) and this parser must be tightened rather than the rule relaxed.

Usage:
    python3 scripts/mercer_county_board_scraper.py [-o raw.json]
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

BOARD_URL = "https://www.mercercountyil.org/county_board/index.php"
RESULTS_URL = "https://il-mercer.pollresults.net/"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

ROW_RE = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
CELL_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.S | re.I)
DISTRICT_RE = re.compile(r"^District\s+(\d+)$", re.I)
# "Becky Hawn (R) Keithsburg", "Josh Frieden (R) New Boston, CHAIRMAN (309)537-3443"
MEMBER_RE = re.compile(
    r"^(?P<name>[^()]+?)\s*\((?P<party>[A-Z])\)\s*(?P<rest>.*)$")
TERM_RE = re.compile(r"^(\d{1,2})\s*/\s*(\d{2})$")
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}")
CHAIR_RE = re.compile(r"\bCHAIR(?:MAN|PERSON|WOMAN)?\b", re.I)

# A street address would carry a number then a street word; the page prints
# bare town names today and this is the tripwire if that ever changes.
STREET_RE = re.compile(r"\d+\s+\w+\s+(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|blvd|hwy|highway)\b", re.I)


fail = make_fail("mercer-board-scraper")


def get(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-mercer-county-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def clean(fragment):
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


BOARD_TABLE_RE = re.compile(
    r'<span class="subheader">\s*Mercer County Board\s*</span>.*?(<table\b.*?</table>)',
    re.S | re.I)


def board_table(page):
    """ONLY the roster table, and this bound is load-bearing. The same page
    carries an elected-county-officials table and several committee tables
    whose rows look identical to a row-level parser — "<name> (<party>)" with a
    date beside it — so an unbounded scan picked up the County Clerk and five
    other officials as District 5 board members the first time this was run."""
    match = BOARD_TABLE_RE.search(page)
    if not match:
        fail("the 'Mercer County Board' roster table is no longer on the page — "
             "refusing to parse whatever table is there instead")
    return match.group(1)


def scrape_members(page):
    records = []
    district = None
    for row in ROW_RE.findall(board_table(page)):
        cells = [clean(c) for c in CELL_RE.findall(row)]
        if len(cells) < 3:
            continue
        hit = DISTRICT_RE.match(cells[0])
        if hit:
            district = hit.group(1)
        if district is None:
            continue
        member = MEMBER_RE.match(cells[1])
        if not member:
            continue
        rest = member.group("rest").strip()
        if STREET_RE.search(rest):
            fail("the board page now prints what looks like a street address (%r) — "
                 "home addresses never ship; tighten this parser rather than the "
                 "rule" % rest)
        entry = {"name": member.group("name").strip(),
                 "party": member.group("party"), "district": district}
        phone = PHONE_RE.search(rest)
        if phone:
            entry["phone"] = re.sub(r"[^\d]", "", phone.group(0))
            entry["phone"] = "%s-%s-%s" % (entry["phone"][:3], entry["phone"][3:6],
                                           entry["phone"][6:])
            rest = rest.replace(phone.group(0), " ")
        if CHAIR_RE.search(rest):
            entry["role"] = "Chairman"
            rest = CHAIR_RE.sub(" ", rest)
        town = re.sub(r"[,\s]+$", "", re.sub(r"\s+", " ", rest)).strip(" ,")
        if town:
            entry["town"] = town
        term = TERM_RE.match(cells[2])
        if term:
            entry["termEnds"] = "20%s-%02d" % (term.group(2), int(term.group(1)))
        records.append(entry)
    records.sort(key=lambda r: (int(r["district"]), r["name"]))
    return records


def scrape_composition(page):
    match = re.search(r"var electionData = (\{.*?\});\s*\n", page, re.S)
    if not match:
        fail("the Clerk's results page no longer embeds its result set as JSON — "
             "the composition check cannot run, and it is this county's only "
             "automatic redistricting warning")
    data = json.loads(match.group(1))
    election = data.get("Election") or {}
    out = {}
    for race in data.get("Races") or []:
        name = (race.get("RaceName") or "").upper()
        if "COUNTY BOARD" not in name:
            continue
        hit = re.search(r"BOARD (\d+)(?:ST|ND|RD|TH) DISTRICT", name)
        if not hit:
            continue
        precincts = ([p["PrecinctName"] for p in race.get("Reporting") or []] +
                     [p["PrecinctName"] for p in race.get("NotReporting") or []])
        out.setdefault(hit.group(1), set()).update(precincts)
    return ({d: sorted(v) for d, v in out.items()},
            {"description": election.get("Description"),
             "date": (election.get("ElectionDate") or "")[:10],
             "officeTitle": election.get("OfficeTitle")})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", help="write raw JSON here (default: stdout)")
    args = ap.parse_args()

    members = scrape_members(get(BOARD_URL))
    composition, election = scrape_composition(get(RESULTS_URL))
    payload = {"source": BOARD_URL, "resultsUrl": RESULTS_URL,
               "election": election, "composition": composition,
               "records": members}
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("mercer-board-scraper: %d member(s), %d district(s) re-read from the "
              "%s -> %s" % (len(members), len(composition),
                            election.get("description"), args.output), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
