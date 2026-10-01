#!/usr/bin/env python3
"""
Build data/app/logan-precinct-polling.json from the Logan County Clerk's own
Polling Places page.

WHY THIS FILE EXISTS. Logan's precinct GEOMETRY is served live (the Tri-County
RPC layer the county-board entry already uses — layer 40, 29 township-named
precincts), but the county publishes its polling-place assignment only as an
HTML table on the clerk's Joomla site — nothing the app can join at runtime.
This builder scrapes that table into a small same-origin file the precinct
card joins by normalized precinct name; the 2026-07-31 validation pass
measured the join 29/29 (one alias: the GIS writes "Lake Fork/ Laenna" with a
space, the clerk "Lake Fork/Laenna" without — normalization absorbs it).

POLLING ASSIGNMENTS ARE PER-ELECTION. Re-run this builder when the clerk
updates the page (the early-voting-sites.json convention); the shipped file
carries the fetch date and the card links the clerk's page as the authority.

Usage:
    python3 build_logan_precinct_polling.py            # fetch + write
    python3 build_logan_precinct_polling.py --check    # fetch + byte-compare
"""

import datetime
import html as html_mod
import json
import os
import re
import sys

import requests
from scraper_common import (  # noqa: E402  (shared machinery — do not fork)
    make_fail, require_robots_once, UA_CHROME_WIN_126,
)

SOURCE_URL = ("https://www.logancountyil.gov/index.php?option=com_content"
              "&view=article&id=178&Itemid=543&lang=en")
HEADERS = {
    "User-Agent": UA_CHROME_WIN_126,
}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "il", "data", "app", "logan-precinct-polling.json")

# The county runs 29 precincts; refuse to ship a scrape that lost coverage.
MIN_PRECINCTS = 27


fail = make_fail("logan-precinct-polling")


def clean(value):
    value = html_mod.unescape(value or "").replace(" ", " ")
    return re.sub(r"\s+", " ", value).strip().strip(",").strip()


def fetch_rows():
    # THE COUNTY'S RULES ARE READ BEFORE THE PAGE, with the identity this fetch
    # sends. AND THE PATH IS WHY THIS FILE IS CLEAR WHERE THE HOST IS NOT.
    # www.logancountyil.gov publishes `Disallow: /images/`, which the inventory's
    # one url per host had recorded against the whole host — because that url is
    # the yearbook PDF a different scraper reads, and the shortest path wins the
    # pick. Measured from a GitHub runner on 2026-10-01 and re-read here against
    # the same 1,370 bytes, the clerk's /index.php article this builder fetches
    # matches no rule in the binding group and is permitted, while the PDF is
    # refused and logan_municipal_officials_scraper.py correctly declines it.
    # MEASURE THE PATH THE SCRAPER FETCHES, never a directory above it and never
    # another caller's url on the same host.
    require_robots_once(SOURCE_URL, HEADERS["User-Agent"], headers=HEADERS,
                        label="logan-precinct-polling")
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    raw = resp.text
    # The table is plain Joomla markup: each <tr> is one precinct row with a
    # precinct cell and a location cell. Cell text can wrap across inline tags
    # (the Sheridan row does), so cells are flattened before cleaning.
    table_match = None
    for tm in re.finditer(r"<table[^>]*>(.*?)</table>", raw, re.S | re.I):
        if "Precinct" in tm.group(1) and "Location" in tm.group(1):
            table_match = tm
            break
    if table_match is None:
        fail("no Precinct/Location table on the clerk's page — its layout changed")
    rows = []
    for tr in re.finditer(r"<tr[^>]*>(.*?)</tr>", table_match.group(1), re.S | re.I):
        cells = [clean(re.sub(r"<[^>]+>", " ", c))
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr.group(1), re.S | re.I)]
        cells = [c for c in cells if c]      # rows lead with an empty filler cell
        if len(cells) < 2 or cells[0].lower() == "precinct":
            continue
        rows.append((cells[0], cells[1]))
    return rows


def main():
    check = "--check" in sys.argv
    rows = fetch_rows()
    if len(rows) < MIN_PRECINCTS:
        fail("parsed %d precinct rows, floor is %d" % (len(rows), MIN_PRECINCTS))
    seen = {}
    for precinct, location in rows:
        if precinct in seen:
            fail("precinct '%s' appears twice on the clerk's page" % precinct)
        # "Latham Firehouse, 271 N. Macon St., Latham" -> place + address
        parts = location.split(",", 1)
        entry = {"place": clean(parts[0])}
        if len(parts) > 1 and clean(parts[1]):
            entry["address"] = clean(parts[1])
        seen[precinct] = entry

    payload = {
        "source": SOURCE_URL,
        "fetched": datetime.date.today().isoformat(),
        "precincts": dict(sorted(seen.items())),
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if check:
        if not os.path.exists(OUT_PATH):
            fail("--check: %s does not exist" % os.path.relpath(OUT_PATH, REPO_ROOT))
        shipped = json.load(open(OUT_PATH, encoding="utf-8"))
        if shipped.get("precincts") != payload["precincts"]:
            fail("--check: the clerk's page no longer matches the shipped file — "
                 "re-run this builder and review the diff")
        print("logan-precinct-polling: OK — shipped file matches the clerk's page "
              "(%d precincts)" % len(seen))
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(body)
    print("logan-precinct-polling: wrote %s — %d precincts"
          % (os.path.relpath(OUT_PATH, REPO_ROOT), len(seen)))


if __name__ == "__main__":
    main()
