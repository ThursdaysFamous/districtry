#!/usr/bin/env python3
"""
Chicago's 50 alderpeople, from the City's own dataset.

WHY THIS EXISTS. il/index.html has fetched Socrata `htai-wnw4` live on first
toggle of the ward layer since the layer shipped, which answers a reader who
runs the map and answers nobody else. The alderperson's name reaches a search
engine, an AI client or a reader with JavaScript off through no surface at all,
which is the same absence scripts/build_county_pages.py closed for 2,650 county
seats. This is the first half of closing it for Chicago: the roster becomes a
file, and scripts/build_officeholder_tables.py puts it in the served bytes of
il/ward.html.

WHAT IT IS NOT. This does not change what the map card reads. The card keeps
calling Socrata live, so it is never a week stale, and the page's table is a
DATED SNAPSHOT that says which day it describes. The two cannot silently
disagree about a name for longer than a week, and the table names its day.
Moving the card onto this file is a separate decision with its own trade (one
source, offline-capable, one fewer live host on the privacy page's table,
against a card that can be seven days behind the City).

THE SOURCE IS AN API AND IS STILL READ BY THE RULES. data.cityofchicago.org
is measured `token-ok` in user-agent-measurements.json — it serves the
districtry token a full page — and its robots.txt states `Crawl-delay: 1`,
which this honours even though it makes one request, because the rule is about
what the host asked for rather than about how much this particular caller
happens to need.

    python3 scripts/chicago_ward_scraper.py --out chicago_wards.json
"""

import argparse
import datetime
import json
import sys
import time

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))

import requests                                                   # noqa: E402

from robots_policy import RobotsGate                              # noqa: E402

DATASET = "htai-wnw4"
SOURCE_URL = "https://data.cityofchicago.org/d/%s" % DATASET
API_URL = "https://data.cityofchicago.org/resource/%s.json" % DATASET
# One page covers the whole council with room to spare; a limit below 50 would
# silently truncate, and the builder's exact-50 gate is what would catch it.
PARAMS = {"$limit": "200", "$order": "ward"}

USER_AGENT = "districtry/1.0 (+https://districtry.com/il/)"

# The columns this reads, and nothing else. `location` carries a lat/lng for the
# ward office and `photo_link` a portrait; neither is on the card or the table,
# and a scraper that carries a field nobody renders is a field nobody guards.
FIELDS = ("ward", "alderman", "address", "city", "state", "zipcode",
          "ward_phone", "email", "website")


def scrape(timeout=60):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT,
                            "Accept": "application/json"})
    gate = RobotsGate(session, USER_AGENT)
    ok, why = gate.allows(API_URL)
    if not ok:
        raise SystemExit("robots.txt refuses %s: %s" % (API_URL, why))
    delay = gate.crawl_delay(API_URL)
    if delay:
        print("chicago-ward-scraper: honouring Crawl-delay %.1fs" % delay,
              file=sys.stderr)
        time.sleep(delay)
    resp = session.get(API_URL, params=PARAMS, timeout=timeout)
    resp.raise_for_status()
    rows = resp.json()
    if not isinstance(rows, list):
        raise SystemExit("%s did not return a list of rows" % API_URL)

    out = []
    for row in rows:
        rec = {}
        for field in FIELDS:
            value = row.get(field)
            # Socrata url-type columns arrive as {"url": "..."}; every other
            # column is a plain string. Flattened here so the builder never has
            # to know which is which.
            if isinstance(value, dict):
                value = value.get("url")
            rec[field] = value if (value or value == 0) else None
        out.append(rec)
    return {
        "source_url": SOURCE_URL,
        "api_url": API_URL,
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                              .replace(microsecond=0).isoformat(),
        "wards": out,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="where to write the raw JSON")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    data = scrape(args.timeout)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("chicago-ward-scraper: wrote %s — %d ward row(s) from %s"
          % (args.out, len(data["wards"]), data["api_url"]), file=sys.stderr)


if __name__ == "__main__":
    main()
