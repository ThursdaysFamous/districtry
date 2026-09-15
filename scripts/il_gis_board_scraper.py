#!/usr/bin/env python3
"""
Stage 1: snapshot the seven Illinois county boards whose members the app reads
LIVE from a county GIS, so a crawler can read them too.

WHY THIS EXISTS. scripts/build_county_pages.py enumerates roster FILES, and
seven counties have no roster file — not because nobody publishes their members
but because the county publishes them on the same GIS feature that carries the
boundary, so il/index.html asks for both in one request and the names never
touch this repo. Measured 2026-09-15, those seven are Effingham, Kankakee,
Madison, McLean, St. Clair, Whiteside and Winnebago: 62 Illinois counties have a
county-board card, 76 have a page, and the difference is these seven plus
Christian (which names nobody at all) and De Witt (which has both; an earlier
slug test was wrong about it). Between them they seat 158 people — 142 rows, because
McLean carries two seats per row and Whiteside nine — including three of the
state's largest boards, and not one of those names appeared in a served byte of
this site.

This is the Cook County shape for a second time. There the roster was missing
for the same reason and the fix was the same: snapshot what the app fetches,
weekly, into data/source — NOT data/app, because validate_index.py requires
every file in data/app to be referenced by index.html and the card still calls
the GIS. build_county_pages.il_districted reads both directories and derives the
"the map reads the same roster" sentence from which one a file came from, so
each of these pages correctly says the card reads the source live and can be up
to a week newer.

NOTHING HERE CHANGES WHAT THE CARD SHOWS. The app is untouched; these files are
read by the page generator and by nobody else.

EVERY ENDPOINT BELOW IS THE ONE THE CARD ALREADY CALLS, with returnGeometry off.
Probed 2026-09-15 with UA_ROSTER_BOT: all seven answer HTTP 200 with the full
attribute set. Five publish no robots.txt (HTTP 404, allow all); the two on
services.arcgis.com refuse robots.txt to every client (HTTP 403), which
robots_policy.py files as `refused` and, for an API serving its data to
everyone, reads as allow.

EACH URL CARRIES ITS OWN QUERY STRING RATHER THAN A params DICT, and that is
not a style choice. scripts/probe_user_agents.py builds its host inventory by
reading URL LITERALS out of these files and fetches each one as written; a
`/query` path with the parameters passed separately is an ArcGIS request with no
parameters, which the service is entitled to refuse. It did: the first draft
passed params separately and the probe recorded
gisportal.co.madison.il.us as `all-refused` on all four rungs — HTTP 403 to the
token AND to Chrome — for a host this scraper was reading 26 rows from in the
same minute. That is the wrong-address defect the probe already has recorded,
one step further in: the address was right and the REQUEST was not. Written in
full, the probe measures what this file actually sends.

Usage:
    python3 scripts/il_gis_board_scraper.py [output.json]
"""

import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robots_policy import RobotsGate                      # noqa: E402
from scraper_common import UA_ROSTER_BOT                  # noqa: E402

TIMEOUT = 60
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           ".cache", "il_gis_boards_raw.json")

# ONE ENTRY PER COUNTY, and every field in it is a copy of what il/index.html
# already asks for. That duplication is deliberate and bounded: parsing the
# app's JavaScript to recover these seven queries would be a fragile reader of a
# file that changes for unrelated reasons, and the queries differ in shape
# anyway — one filters server-side, one filters client-side, one carries two
# seats per district in parallel columns and one carries nine in a single comma
# separated string. build_il_gis_board_rosters.py GATES the duplication instead:
# it fails if a county here has no county-board entry in the app, and if a
# county with a board card and no roster file is absent from here without a
# recorded reason.
COUNTIES = [
    dict(
        key="effingham", county="Effingham",
        # Districts are LETTERS here (A..I), not numbers.
        url="https://services.arcgis.com/vj0V9Lal6oiz0YXp/arcgis/rest/services/"
            "ElectionGeography_public_2d9b4955467947e2802e5d4c4173060f/FeatureServer/2/query"
            "?where=electedoffice%20%3D%20%27County%20Board%20Member%27"
            "&outFields=district,repname1,party1,phone1,email1"
            "&returnGeometry=false&f=json",
        board_url="https://www.effinghamcountyil.gov/county-board/",
    ),
    dict(
        key="kankakee", county="Kankakee",
        url="https://k3gis.net/arcgis/rest/services/BASE/Elected_Officials/MapServer/1/query"
            "?where=1%3D1&outFields=district,membername,party,phone,email"
            "&returnGeometry=false&f=json",
        board_url="https://www.kankakeecountyil.gov/county-board/",
    ),
    dict(
        key="madison", county="Madison",
        url="https://gisportal.co.madison.il.us/servera/rest/services/CountyClerk/CBDWS/"
            "MapServer/0/query"
            "?where=1%3D1&outFields=DISTRICT,OFFICIAL,PARTY,PHONE,EMAIL,URL"
            "&returnGeometry=false&f=json",
        board_url="https://www.madisoncountyil.gov/government/county_board/index.php",
    ),
    dict(
        key="mclean", county="McLean",
        # TWO SEATS PER DISTRICT, in parallel columns rather than two rows.
        url="https://gis.mcleancountyil.gov/arcgis/rest/services/Clerks/"
            "MyElectedRepresentatives/MapServer/1/query"
            "?where=1%3D1&outFields=DISTRICTID,REPNAME,PARTY,DISTRICTURL,REPNAME2,PARTY2,"
            "DISTRICTURL2&returnGeometry=false&f=json",
        board_url="https://www.mcleancountyil.gov/155/County-Board",
    ),
    dict(
        key="st-clair", county="St. Clair",
        url="https://arcgispublicmap.co.st-clair.il.us/server/rest/services/"
            "SCC_voting_districts/MapServer/2/query"
            "?where=1%3D1&outFields=district,name&returnGeometry=false&f=json",
        board_url="https://www.co.st-clair.il.us/departments/county-board",
    ),
    dict(
        key="whiteside", county="Whiteside",
        # NINE NAMES IN ONE FIELD, and the layer holds every office's districts
        # in one table, so the board rows are picked out client-side exactly as
        # whitesideIsBoardFeature does it.
        url="https://services.arcgis.com/l0M0OC6J9QAHCiGx/arcgis/rest/services/"
            "ElectionGeography_public/FeatureServer/2/query"
            "?where=1%3D1&outFields=electedoffice,name,repname1,districturl1"
            "&returnGeometry=false&f=json",
        board_url="https://www.whitesidecountyil.gov/186/County-Board",
    ),
    dict(
        key="winnebago", county="Winnebago",
        # District arrives as "D1".
        url="https://maps.wingis.org/public/rest/services/ElectedOfficials/MapServer/26/query"
            "?where=1%3D1&outFields=District,REP,REPPARTY&returnGeometry=false&f=json",
        board_url="https://wincoil.gov/government/county-board",
    ),
]

# A county with a board card, no roster file, and no entry above needs a reason
# here or build_il_gis_board_rosters.py fails. Both of these are measurements
# rather than omissions, and both are re-audited on every run.
NO_ROSTER = {
    "Christian": "The county's board page listed only its Chairman and Vice "
                 "Chairman when it was last readable, and christiancountyil.gov "
                 "has answered every client with a Cloudflare managed challenge "
                 "since 2026-09-15. No source names the sixteen members. "
                 "(2026-09-15)",
}


def fail(msg):
    print("il-gis-board-scraper: FATAL — %s" % msg, file=sys.stderr)
    sys.exit(1)


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    session = requests.Session()
    gate = RobotsGate(session, UA_ROSTER_BOT, timeout=30)

    payload, problems = {}, []
    for spec in COUNTIES:
        allowed, why = gate.allows(spec["url"])
        if not allowed:
            problems.append("%s: robots.txt disallows this fetch (%s)"
                            % (spec["county"], why))
            continue
        delay = gate.crawl_delay(spec["url"])
        if delay:
            # One host per county here, so a per-host queue would be a queue of
            # one. Sleeping before the single fetch is the same thing.
            import time
            time.sleep(delay)
        try:
            resp = session.get(spec["url"],
                               headers={"User-Agent": UA_ROSTER_BOT}, timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
        except Exception as exc:                                  # noqa: BLE001
            problems.append("%s: %s" % (spec["county"], exc))
            continue
        if body.get("error"):
            problems.append("%s: the service returned an error — %s"
                            % (spec["county"], body["error"]))
            continue
        rows = [f.get("attributes") or {} for f in (body.get("features") or [])]
        if not rows:
            problems.append("%s: the query returned no rows" % spec["county"])
            continue
        payload[spec["key"]] = dict(county=spec["county"], url=spec["url"],
                                    board_url=spec["board_url"],
                                    robots=why, rows=rows)
        print("il-gis-board-scraper: %-10s %3d row(s)" % (spec["key"], len(rows)))

    # A COUNTY LOST IS THE WHOLE RUN. These seven are one weekly job and the
    # builder refuses to write a partial set, so stopping here keeps the failure
    # where it can be read rather than in a diff that silently drops a county.
    if problems:
        fail("; ".join(problems))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    print("il-gis-board-scraper: wrote %s — %d county(ies), %d row(s)"
          % (out_path, len(payload), sum(len(v["rows"]) for v in payload.values())))


if __name__ == "__main__":
    main()
