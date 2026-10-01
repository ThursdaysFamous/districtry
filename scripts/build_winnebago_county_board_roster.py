#!/usr/bin/env python3
"""
Resolve scripts/winnebago_county_board_scraper.py's output into
data/app/winnebago-county-board-members.json, keyed by district ("1".."20").

This roster does NOT supply the member — WinGIS already carries the name and
party on the board boundary 20/20, and that is what the card renders. It
supplies the CONTACT the GIS declares and never fills: an official
@board.wincoil.gov e-mail and a phone per district.

So the app joins it as an enrichment: if this file is missing the card is
exactly what shipped before it existed, a name and a party. That is why the
loader is `.catch`-swallowed on the app side and why there is no floor here for
"members" — losing this file costs contact rows, never the officeholder.

THE BUILD CROSS-CHECKS THE TWO SOURCES rather than trusting either. The GIS and
the board page are maintained separately and can drift; a phone attached to the
wrong person is worse than no phone. Every district's scraped name is compared
to the GIS name, and a mismatch beyond a known-benign shortening (the GIS writes
"Chris Scrol" where the page writes "Christopher Scrol") is reported and that
district's contact is DROPPED, not shipped against a name the card will not show.

Usage:
    python3 build_winnebago_county_board_roster.py <raw-scraper-output.json> [output_dir]
"""

import json
import os
import re
import sys
import urllib.request
from scraper_common import require_robots_once, UA_ROSTER_BOT  # noqa: E402  (shared machinery — do not fork)

SOURCE_URL = "https://wincoil.gov/government/county-board"
GIS_QUERY = ("https://maps.wingis.org/public/rest/services/ElectedOfficials/"
             "MapServer/26/query?where=1%3D1&outFields=District,REP&returnGeometry=false&f=json")
USER_AGENT = UA_ROSTER_BOT
TIMEOUT = 60

MIN_DISTRICTS = 18
MIN_EMAILS = 18

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "il", "data", "app")


def norm_name(value):
    """Compare names by their surname plus first initial.

    Deliberately loose in ONE direction only: it tolerates a shortened or
    expanded forename ("Chris"/"Christopher") because the two county surfaces
    genuinely differ there, and nothing else. A different surname, or a
    different initial, is a real mismatch.
    """
    text = re.sub(r"[^A-Za-z ]", " ", (value or "")).strip()
    parts = [p for p in text.split() if p]
    if not parts:
        return None
    return (parts[-1].lower(), parts[0][:1].lower())


def gis_names():
    require_robots_once(GIS_QUERY, USER_AGENT, headers={"User-Agent": USER_AGENT},
                        label="il-build-winnebago-county-board-roster")
    request = urllib.request.Request(GIS_QUERY, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
        payload = json.load(resp)
    out = {}
    for feature in payload.get("features") or []:
        attrs = feature.get("attributes") or {}
        district = str(attrs.get("District") or "").strip()
        match = re.match(r"^D(\d+)$", district, re.I)
        if match:
            district = match.group(1)
        name = (attrs.get("REP") or "").strip()
        if district and name:
            out[district] = name
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    records = payload.get("records") if isinstance(payload, dict) else payload

    try:
        gis = gis_names()
    except Exception as exc:  # noqa: BLE001
        print("build-winnebago-board: FATAL — could not read the board GIS to "
              "cross-check names (%s). Refusing to ship contact that has not been "
              "matched to the member the card will show." % exc, file=sys.stderr)
        sys.exit(1)

    roster = {}
    mismatches = []
    for rec in records or []:
        district = str(rec.get("district") or "").strip()
        name = rec.get("name")
        if not district or not name:
            continue
        gis_name = gis.get(district)
        if not gis_name:
            mismatches.append("district %s: on the board page (%s) but not in the GIS"
                              % (district, name))
            continue
        if norm_name(gis_name) != norm_name(name):
            mismatches.append("district %s: GIS says %r, board page says %r"
                              % (district, gis_name, name))
            continue
        entry = {"sourceUrl": SOURCE_URL}
        if rec.get("email"):
            entry["email"] = rec["email"]
        if rec.get("phone"):
            entry["phone"] = rec["phone"]
        if len(entry) > 1:
            roster[district] = entry

    for problem in mismatches:
        print("  name mismatch — contact dropped: %s" % problem, file=sys.stderr)

    emails = sum(1 for v in roster.values() if v.get("email"))
    problems = []
    if len(roster) < MIN_DISTRICTS:
        problems.append("%d districts (< %d)" % (len(roster), MIN_DISTRICTS))
    if emails < MIN_EMAILS:
        problems.append("%d e-mails (< %d)" % (emails, MIN_EMAILS))
    if problems:
        print("build-winnebago-board: FATAL — refusing to overwrite a good file: %s"
              % "; ".join(problems), file=sys.stderr)
        sys.exit(1)

    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    out_path = os.path.join(out_dir, "winnebago-county-board-members.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, ensure_ascii=False)
    phones = sum(1 for v in roster.values() if v.get("phone"))
    print("build-winnebago-board: wrote %s — %d districts, %d e-mails, %d phones "
          "(%d name mismatch(es) dropped)"
          % (out_path, len(roster), emails, phones, len(mismatches)))


if __name__ == "__main__":
    main()
