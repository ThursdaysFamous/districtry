#!/usr/bin/env python3
"""
Cook County's 17 commissioners and its Board President, from the county's own
GIS people table — the same rows il/index.html renders on the Cook board card.

WHY THERE WAS NO PAGE. Cook is the second most populous county in the United
States and `il/county-board/cook.html` returned 404 while the Illinois hub's own
prose said "Cook County and dozens more Illinois counties". The reason was the
Chicago-ward reason: the app fetches `politicalBoundary/MapServer/26` live on
every Cook click, so there was no roster FILE for build_county_pages.py to read,
and that generator enumerates whatever the rosters carry.

WHICH SOURCE, AND WHY NOT THE OBVIOUS TWO. Measured 2026-09-15:

  * The county WEBSITE publishes no machine-readable members list. Its
    /board-of-commissioners page is a hub of meetings and committees, the
    /service/board-commissioners path 404s, and no per-district listing was
    found from the front page's links.
  * The county's OPEN DATA portal has "Cook County Commissioner Information"
    (jsye-5ha4), which reads well and is years out of date: it seats Robert
    Steele, who died in 2018, and gives "next_election: 2018" for the board.
  * The GIS people table is maintained. Its rows track real changes through
    2025 — District 8's row names the 2025 appointee and was edited four days
    after that date — and it is what the card already shows a reader.

ONE COLUMN IS MAINTAINED AND ANOTHER IS NOT, IN THE SAME ROWS. `lastElectedDate`
says 2018-11-06 for twelve of the seventeen, all of whom were on the 2022
ballot; `last_edited_date` for those twelve is 2022-11-22, a fortnight after
that election. So the NAMES are kept and the election dates are not, which is
why this carries names, offices and contacts and ships no term or election date
at all. Reading a stale column beside a fresh one is the Coles mistake, and the
fix is the same: take from a source only the columns it maintains.

    python3 scripts/cook_county_board_scraper.py --out cook_board.json
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests                                                   # noqa: E402

from robots_policy import RobotsGate                              # noqa: E402

SERVICE = ("https://gis.cookcountyil.gov/traditional/rest/services/"
           "politicalBoundary/MapServer")
LAYER = 26
SOURCE_URL = "%s/%d" % (SERVICE, LAYER)
# The card's own filter. Everything else on this layer is a park, library or
# metropolitan tax district's officer, or a federal row this never reads.
WHERE = "office='Commissioner' OR office='Board President'"
USER_AGENT = "districtry/1.0 (+https://districtry.com/il/)"

# Columns this trusts, and nothing else. `lastElectedDate`, `next_election` and
# `term` are on the rows and are NOT here; see the module docstring.
FIELDS = ("RELATE_KEY", "office", "jurisdiction", "firstName", "nickName",
          "middleName", "lastName", "suffix", "addressStreet_1",
          "addressSuite_1", "city1", "state1", "zip1", "phone1", "email1",
          "url1", "addressStreet_2", "addressSuite_2", "city2", "state2",
          "zip2", "phone2", "last_edited_date")


def fetch(timeout=60):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    gate = RobotsGate(session, USER_AGENT)
    ok, why = gate.allows(SOURCE_URL)
    if not ok:
        raise SystemExit("robots.txt refuses %s: %s" % (SOURCE_URL, why))
    resp = session.get(SOURCE_URL + "/query", timeout=timeout, params={
        "where": WHERE, "outFields": ",".join(FIELDS),
        "returnGeometry": "false", "f": "json", "resultRecordCount": "500"})
    resp.raise_for_status()
    data = resp.json()
    if "features" not in data:
        raise SystemExit("%s returned no features: %s"
                         % (SOURCE_URL, json.dumps(data)[:200]))
    return [f.get("attributes") or {} for f in data["features"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    rows = fetch(args.timeout)
    out = {
        "source_url": SOURCE_URL,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .replace(microsecond=0).isoformat(),
        "rows": rows,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("cook-county-board-scraper: wrote %s — %d row(s) from %s"
          % (args.out, len(rows), SOURCE_URL), file=sys.stderr)


if __name__ == "__main__":
    main()
