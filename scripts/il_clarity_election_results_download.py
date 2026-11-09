#!/usr/bin/env python3
"""
Download the Clarity Elections precinct reports for the Illinois counties
whose results the map colours, into il/data/source/election-results/
2026-11-03/clarity/, and record each download in record.json there.

RUN BY HAND ONLY. NO WORKFLOW MAY RUN THIS. On 2026-11-05 Clarity's
robots.txt answered a GitHub runner with HTTP 202 and an empty body, from
CloudFront, three times 20 seconds apart, on both HTTP stacks (Actions run
42069482060). This project reads that as an access control, so no scheduled
job fetches Clarity. Adam (the operator) ruled the same day ("relay"): "You
are just doing the download for me, which i can get to manually." Each
download is that: one person-directed fetch, made from a research session
where robots.txt answers 404 (no rules), with this project's own reader
token, robots.txt read first. The README beside the files says the same.

For each results site it reads two addresses, the ones Clarity's own pages
use: `current_ver.txt` (the report's version number) and that version's
`reports/detailxml.zip` (every race, choice and precinct). A site whose
version has not moved since the recorded download is left alone.

Usage:
    python3 scripts/il_clarity_election_results_download.py
"""

import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile

from scraper_common import UA_HEADERS_ROSTER_BOT, UA_ROSTER_BOT, make_fail, require_robots_once

fail = make_fail("il-clarity-election-results-download")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "il", "data", "source", "election-results", "2026-11-03", "clarity")
BASE = "https://results.enr.clarityelections.com/"
# record.json key -> (file stem, the site's path: state/region/election id)
SITES = {
    "DuPage": ("dupage", "IL/DuPage/127290"),
    "Lake": ("lake", "IL/Lake/127289"),
    "Macoupin": ("macoupin", "IL/Macoupin/127399"),
    "Madison": ("madison", "IL/Madison/127555"),
    "McHenry": ("mchenry", "IL/McHenry/127286"),
    "McLean": ("mclean", "IL/McLean/127349"),
    "Bloomington": ("bloomington", "IL/Bloomington/127392"),
    "Sangamon": ("sangamon", "IL/Sangamon/127490"),
    "Winnebago": ("winnebago", "WRC/Winnebago/127560"),
    "Will": ("will", "IL/Will/127394"),
}


def get(url):
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT)
    req = urllib.request.Request(url, headers=dict(UA_HEADERS_ROSTER_BOT))
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            fail("%s answered HTTP %s" % (url, resp.status))
        return resp.read()


def main():
    # an argument parser only so that --help answers without fetching
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args()
    path = os.path.join(OUT, "record.json")
    record = json.load(open(path))
    changed = 0
    for key, (stem, site) in SITES.items():
        ver = get(BASE + site + "/current_ver.txt").decode().strip()
        if not ver.isdigit():
            fail("%s: current_ver.txt said %r" % (key, ver[:80]))
        if record.get(key, {}).get("version") == ver:
            print("%s: version %s, unchanged" % (key, ver))
            continue
        time.sleep(2)
        url = BASE + site + "/" + ver + "/reports/detailxml.zip"
        body = get(url)
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            xml = z.read("detail.xml").decode("utf-8", "replace")
        stamp = re.search(r"<Timestamp>([^<]+)</Timestamp>", xml)
        name = re.search(r"<ElectionName>([^<]+)</ElectionName>", xml)
        precincts = len(re.findall(r"<Precinct name=", xml.split("</VoterTurnout>")[0]))
        if not stamp or not precincts:
            fail("%s: the report carries no timestamp or no precincts" % key)
        with open(os.path.join(OUT, stem + "-detailxml.zip"), "wb") as fh:
            fh.write(body)
        record[key] = {
            "eid": int(site.rsplit("/", 1)[1]), "version": ver, "url": url, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(), "timestamp": stamp.group(1),
            "election": name.group(1) if name else "", "precincts": precincts,
            "fetched": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        changed += 1
        print("%s: version %s, report of %s, %d precincts" % (key, ver, stamp.group(1), precincts))
        time.sleep(2)
    with open(path, "w") as fh:
        json.dump(record, fh, indent=1)
        fh.write("\n")
    print("il-clarity-election-results-download: %d of %d sites downloaded again" % (changed, len(SITES)))


if __name__ == "__main__":
    sys.exit(main())
