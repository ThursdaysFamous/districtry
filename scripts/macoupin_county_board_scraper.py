#!/usr/bin/env python3
"""
Read Macoupin County's eighteen County Board members, and the county's own
board-district inventory, into raw JSON for build_macoupin_county_board.py.

THE MEMBERS come from the County Clerk's elected-officials directory
(macoupinvotes.gov/election-results/elected-officials/). That page is empty
and fills itself from a JSONP service beside it; the address, the callback and
the meaning of its fields are recorded in macoupin_municipal_officials_scraper.py,
which has read the same service weekly since 2026-08-20, and this module takes
its constants and its JSONP reader from there rather than restating them. The
service's "Board Members" district holds one office per seat — "Board Member
District N", two per district — with the holder's ballot name, the date the
seat is next on the ballot, and `effectiveAtLarge`, which on this deployment
means APPOINTED TO FILL AN UNEXPIRED TERM (the page's own legend, re-read and
asserted every run). The board Chair is a separate office in the service's
"Appointed County Officers" district, titled "Macoupin County Board Chair".

THE SECOND-CONTACT E-MAIL, AND NOTHING ELSE FROM THE DETAIL ENDPOINT. Each
office has a detail record (`getelectedofficial?officeId=N`) whose
second-contact slot, `office.email2`, holds an e-mail address for 14 of the 19
board offices (measured 2026-10-17). That record also carries the
officeholder's RESIDENCE (`person`, the `address` array and `office.address2`),
so this module reads `office.email2` and the three fields that tie the record to
the seat (the office id, its title and the holder's ballot name) and keeps
nothing else; the residence is never read into any output. It asks once per
seat, paced as the municipal scraper paces the same endpoint, and a record whose
id, title or holder differs from the list's gives no e-mail for that seat.

The slot belongs to the OFFICE, not the person: the municipal scraper found
primary e-mails left behind by a predecessor. So build_macoupin_county_board.py
ships the address only where its local part carries the member's surname, which
it did on 12 of the 14 on 2026-10-17, when Adam chose to publish members' own
e-mail addresses, personal ones included ("E-mails too"); the other two are
left out. The slot's telephone number (`phone2`, 16 of the 19) is not read:
nothing in a number can tie it to the member, so it stays out. No party is
published.

THE CLIENT is this project's own token, not the browser string the municipal
scraper sends: measured 2026-10-15, the list, text and robots requests all
answer this token in full (the list 595 KB, the same bytes a browser string
gets). The robots.txt read uses the same headers.

THE TRIPWIRE re-reads the county's Board Districts layer (GIS_Layers layer 3)
without geometry: its nine `boarddistrict` keys and each one's Shape__Area,
which the builder compares against what shipped.

Usage:
    python3 scripts/macoupin_county_board_scraper.py -o /tmp/macoupin_board_raw.json
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from macoupin_municipal_officials_scraper import (  # noqa: E402  (one reader of one service)
    AT_LARGE_LEGEND, AT_LARGE_LEGEND_KEY, DETAIL_PAUSE, DETAIL_URL, LIST_URL,
    OFFICIALS_PAGE, TEXT_URL, election_year, strip_jsonp,
)
from scraper_common import (  # noqa: E402  (shared machinery -- do not fork)
    UA_HEADERS_ROSTER_BOT,
    make_fail,
    require_robots_once,
)

fail = make_fail("macoupin-board-scraper")

HEADERS = dict(UA_HEADERS_ROSTER_BOT)
HEADERS["Accept"] = "*/*"
TIMEOUT = 60

BOARD_DISTRICT = "Board Members"
CHAIR_DISTRICT = "Appointed County Officers"
CHAIR_TITLE = "Macoupin County Board Chair"
SEAT_TITLE = re.compile(r"^Board Member District (\d+)$")

LAYER_QUERY = ("https://services.arcgis.com/LYDdxoqTV7fw9teL/arcgis/rest/services/"
               "GIS_Layers/FeatureServer/3/query")


def get(url, params=None):
    require_robots_once(url, HEADERS["User-Agent"], headers=HEADERS,
                        label="il-macoupin-county-board-scraper")
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — any failure is a refusal to write
        fail("could not read %s (%s: %s)" % (url, type(exc).__name__, exc))
    return resp


def read_members():
    legend = (strip_jsonp(get(TEXT_URL).text, TEXT_URL) or {}).get(AT_LARGE_LEGEND_KEY) or {}
    if (legend.get("pageTextValue") or "").strip() != AT_LARGE_LEGEND:
        fail("%s no longer reads %r, so `effectiveAtLarge` cannot be read as "
             "'appointed' without a human re-checking the page"
             % (AT_LARGE_LEGEND_KEY, AT_LARGE_LEGEND))
    payload = strip_jsonp(get(LIST_URL).text, LIST_URL)
    districts = (payload or {}).get("districts") or []
    board = [d for d in districts if (d.get("name") or "").strip() == BOARD_DISTRICT]
    if len(board) != 1:
        fail("the directory carries %d %r districts, expected 1"
             % (len(board), BOARD_DISTRICT))
    seats = []
    for office in board[0].get("offices") or []:
        title = (office.get("title") or "").strip()
        match = SEAT_TITLE.match(title)
        if not match:
            fail("a board office is titled %r, not 'Board Member District N'" % title)
        holder = (office.get("officeHolder") or {}).get("ballotDisplay") or ""
        seats.append({
            "district": match.group(1),
            "name": holder.strip(),
            "vacant": bool(office.get("postAtVacant")),
            "appointed": bool(office.get("effectiveAtLarge")),
            "nextElection": election_year(office.get("nextElectionDate")),
            # Read by read_second_emails() and removed there; never written.
            "_office": (office.get("id"), title, holder.strip()),
        })
    chairs = []
    for d in districts:
        if (d.get("name") or "").strip() != CHAIR_DISTRICT:
            continue
        for office in d.get("offices") or []:
            if (office.get("title") or "").strip() == CHAIR_TITLE:
                chairs.append(((office.get("officeHolder") or {}).get("ballotDisplay")
                               or "").strip())
    if len(chairs) != 1 or not chairs[0]:
        fail("the directory names %r as %r, expected exactly one name"
             % (chairs, CHAIR_TITLE))
    return seats, chairs[0]


def read_second_emails(seats):
    """Set `email2` on each seat whose detail record's second-contact slot holds
    an e-mail address. See the module docstring: only `office.email2` and the
    fields that tie the record to the seat are read; the residence the same
    record carries is never looked at. The Chair's own office is not asked,
    because the Chair holds a district seat and that seat's record is asked."""
    asked = 0
    for seat in seats:
        office_id, title, holder = seat.pop("_office")
        if not isinstance(office_id, int) or seat["vacant"] or not holder:
            continue
        if asked:
            time.sleep(DETAIL_PAUSE)
        asked += 1
        url = DETAIL_URL % office_id
        record = (strip_jsonp(get(url).text, url) or {}).get("office") or {}
        same = (record.get("id") == office_id
                and (record.get("title") or "").strip() == title
                and ((record.get("officeHolder") or {}).get("ballotDisplay")
                     or "").strip() == holder)
        value = (record.get("email2") or "").strip() if same else ""
        del record
        if not same:
            print("macoupin-board-scraper: note — District %s: the detail record "
                  "for this seat names a different office or holder than the "
                  "list, so no e-mail is read for it" % seat["district"],
                  file=sys.stderr)
        elif value:
            seat["email2"] = value
    return asked


def read_layer():
    data = get(LAYER_QUERY, {"where": "1=1", "outFields": "boarddistrict,Shape__Area",
                             "returnGeometry": "false", "f": "json"}).json() or {}
    if data.get("error"):
        fail("the county's Board Districts layer answered an error: %r" % data["error"])
    out = {}
    for feat in data.get("features") or []:
        attrs = feat.get("attributes") or {}
        key = str(attrs.get("boarddistrict") or "").strip()
        if key in out:
            fail("the Board Districts layer carries district %r twice" % key)
        out[key] = attrs.get("Shape__Area")
    if not out:
        fail("the Board Districts layer returned no districts")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="-")
    args = ap.parse_args()
    seats, chair = read_members()
    asked = read_second_emails(seats)
    payload = {
        "source": OFFICIALS_PAGE,
        "seats": seats,
        "chair": chair,
        "districtAreas": read_layer(),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output == "-":
        sys.stdout.write(text)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    print("macoupin-board-scraper: %d seats, chair %s, %d layer districts; %d "
          "detail records read, %d with a second-contact e-mail"
          % (len(seats), chair, len(payload["districtAreas"]), asked,
             sum(1 for s in seats if s.get("email2"))), file=sys.stderr)


if __name__ == "__main__":
    main()
