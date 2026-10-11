#!/usr/bin/env python3
"""
Build the Tennessee Senate and Tennessee House rosters (district -> current
officeholder) as same-origin app-data files, so the tn-senate / tn-house
cards join a small roster instead of reaching a third-party host at click
time.

index.html's tn-senate / tn-house layers fetch data/app/tn-senate-members.json
and tn-house-members.json lazily on first click and join them to the
pre-built legislative geometry by district number. Both files carry ONE
RECORD PER SEAT (33 and 99), shaped for the registerIlgaChamber factory, and
scripts/validate_chamber_rosters.py holds them to that.

THE NAMES COME FROM THE STATE, AND THE REST FROM OPEN STATES ONLY WHERE THE
TWO AGREE. Two sources were read on 2026-10-10:

  * The state's own legislative district map service on TNMap
    (tnmap.tn.gov, ADMINISTRATIVE_BOUNDARIES/LEGISLATIVE_DISTRICTS, layers 0
    Senate and 1 House), whose copyright line is "Tennessee Legislature" and
    whose House layer says "Representatives are from www.capitol.tn.gov".
    Every record carries a district and a name with a title in front
    ("Senator", "Representative", "Lt. Gov.", "Speaker"), and a seat nobody
    holds reads "Representative Vacant" — House 31 and 84 on that date. It
    carries no party, e-mail, office or telephone.
  * The Open States current-people export (data.openstates.org, tn.csv):
    131 rows, every one with a party, an e-mail and a link to the member's
    page on wapp.capitol.tn.gov; 0 with a capitol address or telephone.

capitol.tn.gov and wapp.capitol.tn.gov both answer robots.txt with
`User-agent: *` / `Disallow: /` (measured 2026-10-09), so this project reads
neither: the state map service is how the Legislature's own list reaches us,
and the member pages are LINKED from the card, never fetched. A government
publisher goes first, so the state's map decides who holds each seat and
whether it is empty. Open States adds party, e-mail and the member's page to
a seat only when its member for that district has the same surname as the
state's; a disagreement keeps the state's name alone and prints the seat.
On 2026-10-10 the two agreed on every named seat, and disagreed on House 31,
which the state lists as vacant and Open States still gives to Ron Travis.

A seat the state lists as vacant carries `vacant: true` with the layer it
came from and the day it was first read so, which the card prints. That day
is carried forward from the shipped file while the seat stays vacant, so a
weekly run that changes nothing writes nothing.

Usage:
    python3 build_tn_legislature_roster.py [tn.csv] [output_dir]

With no arguments it downloads both sources and writes to the instance's
data/app/. Pass a local tn.csv to skip the Open States download (the state
map is always read live); pass an output_dir to redirect the write.
"""

import csv
import datetime
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                                "scripts"))
from scraper_common import (  # noqa: E402  (FLEET_SHARED)
    UA_HEADERS_ROSTER_BOT,
    UA_ROSTER_BOT,
    UA_STDLIB_DEFAULT,
    require_robots_once,
)

STATE_MAP = ("https://tnmap.tn.gov/arcgis/rest/services/ADMINISTRATIVE_BOUNDARIES/"
             "LEGISLATIVE_DISTRICTS/MapServer")
OPENSTATES_URL = "https://data.openstates.org/people/current/tn.csv"

# Tennessee elects 33 senators and 99 representatives. `seats` is that number
# and every seat gets a record; `expected` is a floor on NAMED members, which
# catches a truncated download or a schema change while tolerating vacancies.
CHAMBERS = {
    "upper": {"out": "tn-senate-members.json", "label": "Senate",
              "expected": 30, "seats": 33, "layer": 0},
    "lower": {"out": "tn-house-members.json", "label": "House",
              "expected": 92, "seats": 99, "layer": 1},
}
# The state's titles, longest first so "Lt. Gov." is not read as a name.
TITLES = ("Lt. Gov. ", "Lieutenant Governor ", "Representative ", "Senator ",
          "Speaker ")
# The share of named seats Open States must enrich. Measured at every named
# seat on 2026-10-10; a join that stops matching is the Brown County shape,
# where the seat count holds and the contact detail silently goes.
MIN_JOIN_SHARE = 0.9

INSTANCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(INSTANCE_ROOT, "data", "app")


def fetch_state_layer(layer):
    """{district: name-with-title} for one chamber, read from the state's map."""
    url = "%s/%d/query?%s" % (STATE_MAP, layer, urllib.parse.urlencode({
        "where": "1=1", "outFields": "DISTRICT,NAME", "returnGeometry": "false",
        "f": "json"}))
    require_robots_once(url, UA_ROSTER_BOT, headers=UA_HEADERS_ROSTER_BOT,
                        label="tn-build-tn-legislature-roster")
    req = urllib.request.Request(url, headers=UA_HEADERS_ROSTER_BOT)
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    if "error" in data:
        # An ArcGIS error is an object, not an empty answer; reading it as one
        # would ship a chamber of vacancies.
        raise SystemExit("FAIL: the state map's layer %d answered an error: %r"
                         % (layer, data["error"]))
    out = {}
    for feat in data.get("features") or []:
        attrs = feat.get("attributes") or {}
        district = str(attrs.get("DISTRICT") or "").strip().lstrip("0")
        name = (attrs.get("NAME") or "").strip()
        if not district or not name:
            continue
        if district in out:
            raise SystemExit("FAIL: the state map's layer %d carries district %s twice"
                             % (layer, district))
        out[district] = name
    return out


def strip_title(raw):
    for title in TITLES:
        if raw.startswith(title):
            return raw[len(title):].strip()
    return raw.strip()


def surname(name):
    tokens = re.sub(r"[^a-z ]", " ", name.lower()).split()
    while tokens and tokens[-1] in ("jr", "sr", "ii", "iii", "iv"):
        tokens.pop()
    return tokens[-1] if tokens else ""


def load_openstates(path=None):
    if path:
        with open(path, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    require_robots_once(OPENSTATES_URL, UA_STDLIB_DEFAULT,
                        label="tn-build-tn-legislature-roster")
    req = urllib.request.Request(OPENSTATES_URL, headers={"User-Agent": UA_STDLIB_DEFAULT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def first_link(links):
    """The member's own page, from Open States' semicolon-joined links cell."""
    for candidate in (links or "").split(";"):
        candidate = candidate.strip()
        if candidate.startswith("http"):
            return candidate
    return None


def load_previous(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def build_roster(chamber, cfg, state_names, rows, previous, today):
    seats = cfg["seats"]
    by_district = {}
    for row in rows:
        if (row.get("current_chamber") or "").strip() != chamber:
            continue
        d = (row.get("current_district") or "").strip().lstrip("0")
        if d:
            by_district[d] = row
    roster, notes = {}, []
    for district in state_names:
        if not district.isdigit() or not 1 <= int(district) <= seats:
            raise SystemExit("FAIL: the state map's %s carries district %r, which is "
                             "not one of the chamber's %d" % (cfg["label"], district, seats))
    for d in range(1, seats + 1):
        key = str(d)
        raw = state_names.get(key)
        row = by_district.get(key)
        if raw is None:
            roster[key] = {"asOf": today}
            notes.append("%s %s: the state map has no record" % (cfg["label"], key))
            continue
        name = strip_title(raw)
        if name.lower() == "vacant":
            prev = previous.get(key) or {}
            as_of = prev.get("asOf") if prev.get("vacant") else None
            # The record cites the query that answers for THIS seat. The
            # service's HTML directory is switched off (HTTP 403 to every
            # client, measured 2026-10-10), so a bare layer URL opens an error
            # page while the JSON answer shows "Representative Vacant" itself.
            source_url = "%s/%d/query?%s" % (STATE_MAP, cfg["layer"], urllib.parse.urlencode({
                "where": "DISTRICT='%s'" % key, "outFields": "DISTRICT,NAME",
                "returnGeometry": "false", "f": "json"}))
            roster[key] = {
                "vacant": True,
                "vacantWhy": ("The Tennessee Legislature's own district map, "
                              "published on the state's TNMap service, lists "
                              "this seat as vacant."),
                "sourceUrl": source_url,
                "asOf": as_of or today,
            }
            if row:
                notes.append("%s %s: the state lists the seat as vacant and Open "
                             "States names %r; the state's word ships"
                             % (cfg["label"], key, row.get("name")))
            continue
        member = {"name": name}
        if row and surname(row.get("name") or "") == surname(name):
            party = (row.get("current_party") or "").strip()
            if party:
                member["party"] = party
            email = (row.get("email") or "").strip()
            if email:
                member["email"] = email
            url = first_link(row.get("links"))
            if url:
                member["url"] = url
        else:
            notes.append("%s %s: the state names %r and Open States %r; the name "
                         "ships without party, e-mail or page"
                         % (cfg["label"], key, name, (row or {}).get("name")))
        roster[key] = member
    return roster, notes


def main():
    args = sys.argv[1:]
    if len(args) > 2:
        print("usage: %s [tn.csv] [output_dir]" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    csv_path = args[0] if len(args) >= 1 else None
    out_dir = args[1] if len(args) == 2 else DEFAULT_OUT_DIR
    today = datetime.date.today().isoformat()

    rows = load_openstates(csv_path)
    os.makedirs(out_dir, exist_ok=True)
    for chamber, cfg in CHAMBERS.items():
        state_names = fetch_state_layer(cfg["layer"])
        out_path = os.path.join(out_dir, cfg["out"])
        roster, notes = build_roster(chamber, cfg, state_names, rows,
                                     load_previous(out_path), today)
        named = [m for m in roster.values() if m.get("name")]
        if len(named) < cfg["expected"]:
            print("FAIL: the state map names %d %s members (expected >= %d) — "
                  "refusing to overwrite the roster with an incomplete chamber"
                  % (len(named), cfg["label"], cfg["expected"]), file=sys.stderr)
            sys.exit(1)
        joined = sum(1 for m in named if m.get("party"))
        if joined < MIN_JOIN_SHARE * len(named):
            print("FAIL: Open States matched only %d of %d named %s seats — the "
                  "join has stopped working, and shipping would strip party, "
                  "e-mail and page from the cards"
                  % (joined, len(named), cfg["label"]), file=sys.stderr)
            sys.exit(1)
        for note in notes:
            print("  note: " + note, file=sys.stderr)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        vacant = [k for k, m in roster.items() if m.get("vacant")]
        print("Wrote %s (%d seats: %d named, %d with party and e-mail; vacant: %s)"
              % (out_path, len(roster), len(named), joined,
                 ", ".join(vacant) or "none"), file=sys.stderr)


if __name__ == "__main__":
    main()
