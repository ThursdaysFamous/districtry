#!/usr/bin/env python3
"""
Stage 1 of the Crawford County Board roster pipeline: scrape the county's own
board page into raw JSON for build_crawford_county_board.py, and RE-READ the
district composition out of the Clerk's live results feed in the same run.

TWO SOURCES, TWO JOBS. The people come from crawfordcounty.illinois.gov's
County Board page, which publishes each member as a linked personnel entry
carrying a name, a district line ("County Board District #3", or "Chairman
County Board District #3") and a county e-mail address. The DISTRICTS come
from il-crawford.pollresults.net, the Clerk's own results system, whose entire
certified result set is embedded in the page as JSON — that is where the
shipped boundaries' composition came from (build_crawford_boundaries.py), and
re-reading it weekly is the re-precincting / redistricting tripwire. The
builder fails when the two disagree with each other or with the shipped
dissolve.

WHY THE COMPOSITION IS RE-READ HERE RATHER THAN LEFT TO AN OPERATOR STEP: the
county's board districts ARE a dissolve of its precincts, so the boundary is
only correct while the election authority keeps tabulating the same precincts
in the same districts. Nothing on the board page would ever show that moving.
The feed carries only the most recent election, so a week's check covers
whichever districts were on that ballot — partial coverage, honestly reported,
which is still the only automatic warning this county has.

WHAT THE BOARD PAGE PUBLISHES, and what it does not: name, district, an
e-mail per member, and the Chairman's title. No party, no term, no phone, and
no home address — so none of those ship. Ten members, two per district.

Usage:
    python3 scripts/crawford_county_board_scraper.py [-o raw.json]
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

BOARD_URL = "https://crawfordcounty.illinois.gov/department/county-board/"
RESULTS_URL = "https://il-crawford.pollresults.net/"
TIMEOUT = 60
HEADERS = {"User-Agent": UA_ROSTER_BOT}

# Each member is one linked personnel entry repeated three times in the markup
# (name, district line, e-mail all point at the same /personnel/<slug>/ URL),
# so the URL is the record key and the three texts are its fields.
PERSONNEL_RE = re.compile(
    r'''href=["'](https://crawfordcounty\.illinois\.gov/personnel/([^/"']+)/)["'][^>]*>(.*?)</a>''',
    re.S)
DISTRICT_RE = re.compile(r"County Board District\s*#?\s*(\d+)", re.I)
CHAIR_RE = re.compile(r"\bchair(?:man|person|woman)?\b", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


fail = make_fail("crawford-board-scraper")


def get(url):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-crawford-county-board-scraper")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def scrape_members(page):
    by_slug = {}
    for match in PERSONNEL_RE.finditer(page):
        slug, text = match.group(2), clean(match.group(3))
        if not text:
            continue
        rec = by_slug.setdefault(slug, {"slug": slug, "url": match.group(1), "texts": []})
        if text not in rec["texts"]:
            rec["texts"].append(text)
    records = []
    for rec in by_slug.values():
        name = email = district = None
        role = None
        for text in rec["texts"]:
            if EMAIL_RE.fullmatch(text):
                email = text
                continue
            hit = DISTRICT_RE.search(text)
            if hit:
                district = hit.group(1)
                if CHAIR_RE.search(text):
                    role = "Chairman"
                continue
            if name is None:
                name = text
        if not name or not district:
            continue
        entry = {"name": name, "district": district, "url": rec["url"]}
        if role:
            entry["role"] = role
        if email:
            entry["email"] = email
        records.append(entry)
    records.sort(key=lambda r: (int(r["district"]), r["name"]))
    return records


def scrape_composition(page):
    """{district: [precinct, ...]} from the certified result set embedded in
    the Clerk's live results page."""
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
        print("crawford-board-scraper: %d member(s), %d district(s) re-read from the "
              "%s -> %s" % (len(members), len(composition),
                            election.get("description"), args.output), file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
