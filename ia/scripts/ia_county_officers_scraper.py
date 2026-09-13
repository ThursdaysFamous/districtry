#!/usr/bin/env python3
"""
Scrape stage 1: fetch every Iowa county's elected-officer roster from the
Iowa State Association of Counties' MEMBER PORTAL and write the raw rows to
.cache/ia_county_officers.json for build_ia_county_officers.py (stage 2).

THIS IS NOT THE ISAC PAGE THE REPO ALREADY USES.
ia_county_directory_scraper.py reads iowacounties.org's public county
directory, which publishes only each county's own website, courthouse name
and supervisor meeting day. The MEMBER PORTAL at
member-portal.iowacounties.org publishes, per county and with no login, a
full table of officeholders:

    Name | Office | Address | City | State | Zip Code | Phone Number | Fax Number | Party

verified live 2026-08-28 against Story County (18 rows). It carries a
"Last Updated" stamp that read 08/28/2026 the day this shipped, i.e. it is
regenerated daily. NO E-MAIL COLUMN EXISTS, and supervisors are listed
WITHOUT a district number -- both measured, both the reason this file is
one of several sources rather than the only one (see build_ia_county_officers.py).

FOUR MEASURED TRAPS, each guarded below:

1. THE DATA ROWS ARE <th>, NOT <td>. Every cell in the table -- header and
   body alike -- is a <th>. A conventional <td> row parse returns ZERO rows
   from a page that is serving perfectly good data. The header row is
   additionally emitted TWICE, so rows are filtered by first-cell value
   ("Name") rather than by position.

2. A BAD COUNTY NAME RETURNS HTTP 200 WITH AN EMPTY TABLE, never a 404
   (measured: .../directory/BlackHawk and .../directory/OBrien both answer
   200 with only the header row). So this scraper gates on the PARSED ROW
   COUNT and never on the status code -- a county that yields no rows is a
   hard failure, not a silently thin county.

3. MULTI-WORD COUNTY NAMES NEED ENCODED SPACES and O'Brien keeps its
   apostrophe: Black%20Hawk, Buena%20Vista, Des%20Moines, Palo%20Alto,
   Van%20Buren, Cerro%20Gordo, O'Brien. The names come from the shipped
   state-counties.json BASENAME set, so they cannot drift from the geometry.

4. THE DAILY STAMP IS EXPORT TIME, NOT PER-RECORD VERIFICATION. A 30-county
   sweep found Adair returning FOUR supervisors and Floyd TWO -- both
   impossible under Iowa Code 331.201 ("shall consist of three members
   unless the membership is increased to five") -- and Adair additionally
   emitting a DUPLICATED Auditor row. Adair's own county site names five
   supervisors. Those defects are the reason stage 2 cross-witnesses this
   file's supervisor count against the board size already read back from
   shipped geometry, and refuses to ship a county whose count is illegal.

ONLY IOWA'S ELECTED COUNTY OFFICES ARE KEPT. The portal mixes elected and
appointed offices in one table (Assessor, Conservation, Emergency
Management, GIS, IT, Public Health and so on are appointed). Iowa elects
the auditor, treasurer, recorder, sheriff and county attorney (Iowa Code
ch. 331) plus the board of supervisors; everything else is dropped here
rather than filtered later, so an appointed staff member can never reach a
card that is about elected representation. The portal's own Party column
corroborates the split -- it is populated for elected offices and blank for
appointed ones -- but the ALLOW-LIST is what decides, never the party cell,
because a party value is data about a person and absence of one is not
proof of anything.

WHY THE TOKEN AND NOT A BROWSER STRING (measured 2026-09-12).

This file sent a pinned Chrome/120 string from the day it shipped, and
nothing had ever asked the host whether it needed one. It does not.
`scripts/probe_user_agents.py` fetched
https://member-portal.iowacounties.org/countydirectory/directory/ with
requests carrying the districtry token on 2026-09-12: HTTP 200, 49,445
bytes, a full page, recorded in user-agent-measurements.json with the
verdict token-ok. The host serves no robots.txt (HTTP 404), so no group
binds and the fetch is allowed; and two other callers of this same host --
ia_county_directory_scraper.py and ia/scripts/validate_sources.py -- have
sent the token all along.

The measurement is of the directory BASE url. Each per-county page under it
is the same host and the same path prefix, and the weekly run is the witness
for those: if one of them turns out to answer the token differently, this
scraper fails loudly on the parsed row count (trap 2 above) rather than
returning a thin county. A browser string goes back only on a measurement
that says the token is refused, recorded here with its date.

Usage:
    python3 ia/scripts/ia_county_officers_scraper.py
"""

import html
import json
import os
import re
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:
    print("FATAL: pip install -r ia/scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ia/
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
OUT_FILE = os.path.join(CACHE_DIR, "ia_county_officers.json")
COUNTIES_FILE = os.path.join(REPO_ROOT, "data", "app", "state-counties.json")

BASE = "https://member-portal.iowacounties.org/countydirectory/directory/"

# Iowa's elected county offices (Iowa Code ch. 331 / 331.201 for the board).
# The portal's exact Office strings, measured live.
ELECTED_OFFICES = {
    "Auditor": "auditor",
    "Treasurer": "treasurer",
    "Recorder": "recorder",
    "Sheriff": "sheriff",
    "County Attorney": "countyAttorney",
}
SUPERVISOR_OFFICE = "Supervisor"

EXPECT_COUNTIES = 99
MIN_ROWS_PER_COUNTY = 6  # a real county page carries ~15-20; 6 is a floor, not a target

# The districtry token, the same string ia_county_directory_scraper.py has
# always sent to this host. See "WHY THE TOKEN AND NOT A BROWSER STRING" above.
HEADERS = {"User-Agent": "districtry/1.0 (+https://districtry.com/ia/)"}
REQUEST_TIMEOUT = 45

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
UPDATED_RE = re.compile(r"Last Updated:\s*</?[^>]*>?\s*([0-9/]{8,10}[^<]{0,12})", re.I)


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def county_names():
    with open(COUNTIES_FILE) as f:
        feats = json.load(f)["features"]
    names = sorted(f["properties"]["BASENAME"] for f in feats)
    if len(names) != EXPECT_COUNTIES:
        raise SystemExit("state-counties.json carries %d counties, expected %d"
                          % (len(names), EXPECT_COUNTIES))
    return names


def fetch(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.text
            last = "HTTP %d" % resp.status_code
        except requests.RequestException as exc:
            last = str(exc)
        time.sleep(2 * (attempt + 1))
    raise SystemExit("%s: %s after %d tries" % (url, last, tries))


def parse_county(name, text):
    """Rows are <th> cells (trap 1); the header row repeats and is dropped by
    its first-cell value rather than by index."""
    rows = []
    for raw in ROW_RE.findall(text):
        cells = [clean(c) for c in CELL_RE.findall(raw)]
        if len(cells) < 9:
            continue
        if not cells[0] or cells[0] == "Name":
            continue
        rows.append({
            "name": cells[0], "office": cells[1],
            "address": cells[2], "city": cells[3], "state": cells[4], "zip": cells[5],
            "phone": cells[6], "fax": cells[7], "party": cells[8],
        })
    # Trap 2: a wrong slug answers 200 with only headers. Zero rows is fatal.
    if len(rows) < MIN_ROWS_PER_COUNTY:
        raise SystemExit(
            "%s: parsed %d rows (floor %d) -- the portal answers 200 with an empty "
            "table for an unknown county, so this is a bad slug or a reshaped page, "
            "never a thin county" % (name, len(rows), MIN_ROWS_PER_COUNTY))

    # Trap 4 (first half): Adair emits a duplicated Auditor row. Dedupe on the
    # whole record so a genuine second supervisor is never collapsed.
    seen, deduped, dropped = set(), [], 0
    for r in rows:
        key = tuple(sorted(r.items()))
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        deduped.append(r)

    kept = [r for r in deduped
            if r["office"] in ELECTED_OFFICES or r["office"] == SUPERVISOR_OFFICE]
    m = UPDATED_RE.search(text)
    return {
        "rows": kept,
        "rowsSeen": len(rows),
        "duplicatesDropped": dropped,
        "lastUpdated": m.group(1).strip() if m else None,
    }


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    out = {}
    total_dupes = 0
    for name in county_names():
        url = BASE + urllib.parse.quote(name, safe="'")
        entry = parse_county(name, fetch(url))
        entry["url"] = url
        out[name] = entry
        total_dupes += entry["duplicatesDropped"]
        sup = sum(1 for r in entry["rows"] if r["office"] == SUPERVISOR_OFFICE)
        print("%-14s %2d elected rows (%d supervisors) of %d on the page%s"
              % (name, len(entry["rows"]), sup, entry["rowsSeen"],
                 "; %d duplicate row(s) dropped" % entry["duplicatesDropped"]
                 if entry["duplicatesDropped"] else ""),
              file=sys.stderr)
        time.sleep(1)

    if len(out) != EXPECT_COUNTIES:
        raise SystemExit("scraped %d counties, expected %d" % (len(out), EXPECT_COUNTIES))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
    print("wrote %s -- %d counties, %d duplicate row(s) dropped in total"
          % (OUT_FILE, len(out), total_dupes), file=sys.stderr)


if __name__ == "__main__":
    main()
