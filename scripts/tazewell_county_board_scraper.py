#!/usr/bin/env python3
"""
Scrape Tazewell County's board roster into raw records.

Stage 1 of the two-stage pipeline (scripts/build_tazewell_board_roster.py is
stage 2). Tazewell publishes its board twice and the two disagree, so which
one this reads is a decision, not a detail:

  * The county GIS (`ElectionGeography_public`, layer 2 "Electoral Districts")
    carries 21 County Board Member rows WITH district and party — the Esri
    election template, the same one Whiteside uses — but no phone or e-mail,
    and its roster attributes are STALE: it still seats Aaron Phillips, whom
    the county's own site no longer lists anywhere, and omits Eugene Glueck,
    who has his own member page.
  * The county WEBSITE (tazewell-il.gov/boardreps/) lists 22 member pages, and
    each member's own page states that member's designation, phone and e-mail.

This reads BOTH, under one rule: **the website wins where the two disagree;
the GIS fills only where the website is silent.** A source demonstrably stale
on WHO is on the board is not the source to trust on WHICH DISTRICT they
represent — but it is still the only source that speaks about a member the
website leaves undistricted, and using it there overrides nothing.

That rule resolves exactly one gap and preserves exactly one disagreement,
both recorded on every record (`districtSource`, `gisDistrict`):

  * GAP FILLED — Michael Harris. The website gives him the designation
    "County Board Vice-Chairman" and no district; the GIS seats him in
    District 3. Nothing contradicts that, so his row carries district 3 with
    districtSource="gis".
  * DISAGREEMENT KEPT — Greg Longfellow. The website places him in District 2
    (on the index AND on his own member page); the GIS places him in District
    3. The website wins. Taking it at its word yields 7/8/6 across the three
    districts where the GIS says 7/7/7, so one of the county's two surfaces is
    wrong about a seat, and this pipeline reports the county's own current
    claim rather than balancing the arithmetic itself.

Both surfaces agree the board is 21 district members plus a countywide-elected
Chairman, so build_tazewell_board_roster.py enforces that TOTAL (which is
agreed) and not equal district sizes (which are not).

FETCH POSTURE: open. Plain server-rendered WordPress HTML.

Usage:
    python3 tazewell_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests

from arcgis_error import raise_for_arcgis_error
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared machinery — do not fork)

INDEX_URL = "https://tazewell-il.gov/boardreps/"
MEMBER_RE = re.compile(r'href="(https://tazewell-il\.gov/members/[^"#?]+/)"')
UA = {"User-Agent": UA_ROSTER_COMPACT}

# the second source — boundary layer AND stale-but-speaking roster attributes
GIS_LAYER = ("https://services.arcgis.com/LIEind9C2d6XYeOY/arcgis/rest/services/"
             "ElectionGeography_public_280605e69d4f4c2696479fc6050cab53/"
             "FeatureServer/2/query")

NAME_RE = re.compile(r"(?is)<h6[^>]*>(.*?)</h6>")
# The heading appends an annotation to the name — "Jay Hall (R) 2024",
# "Maxwell Schneider R 2026". The party letter is unambiguous and is kept
# (the county GIS independently agrees on every member it still carries).
# The YEAR is dropped: nothing on the page labels it, so calling it a term
# expiry or an election year would be a guess. The member pages also publish
# a HOME address, which this deliberately never reads — the fleet removed
# Madison's member residences for the same reason (a residence is not an
# office you can visit).
ANNOTATION_RE = re.compile(r"\s*\(?\b([RD])\b\)?(?:\s+\d{4})?\s*$")
PARTY_NAMES = {"R": "Republican", "D": "Democratic"}
DESIGNATION_RE = re.compile(
    r"(?is)<label>\s*Designation:\s*</label>\s*(?:<[^>]+>\s*)*([^<]+)")
MAILTO_RE = re.compile(
    r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
TEL_RE = re.compile(r'href="tel:([+0-9().\s-]+)"')
DISTRICT_RE = re.compile(r"District\s+(\d+)\s+Representative", re.I)
CHAIR_RE = re.compile(r"County\s+Board\s+(Vice-?\s*)?Chairman", re.I)


def clean(s):
    return re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"(?s)<[^>]+>", " ", s or ""))).strip()


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def parse_member(url, text):
    name_m = NAME_RE.search(text)
    desig_m = DESIGNATION_RE.search(text)
    if not name_m:
        return None
    designation = clean(desig_m.group(1)) if desig_m else ""
    district = role = None
    dm = DISTRICT_RE.search(designation)
    if dm:
        district = dm.group(1)
    else:
        cm = CHAIR_RE.search(designation)
        if cm:
            role = "Vice-Chairman" if cm.group(1) else "Chairman"
    email = MAILTO_RE.search(text)
    phone = TEL_RE.search(text)
    raw_name = clean(name_m.group(1))
    party = None
    ann = ANNOTATION_RE.search(raw_name)
    if ann:
        party = PARTY_NAMES.get(ann.group(1))
        raw_name = raw_name[:ann.start()].strip()
    else:
        # a bare trailing year with no party letter — still not part of a name
        raw_name = re.sub(r"\s+\d{4}$", "", raw_name).strip()
    return {
        "name": raw_name,
        "party": party,
        "district": district,
        "role": role,
        "designation": designation or None,
        "phone": normalize_phone(phone.group(1)) if phone else None,
        "email": email.group(1).lower() if email else None,
        "url": url,
    }


def name_key(name):
    """(first-initial, surname) — the two surfaces spell given names
    differently on four members ("Michael"/"Mike", "Russ"/"Russell",
    "Maxwell"/"Max", "Greg"/"Gregory"), and a prefix rule does not even join
    Mike to Michael. Matching on the initial plus an exact surname does, and
    the caller requires the match to be UNIQUE so the looseness cannot
    silently pair two different people."""
    parts = [p for p in re.split(r"[^A-Za-z]+", (name or "").lower()) if len(p) > 1]
    if len(parts) < 2:
        return None
    return (parts[0][0], parts[-1])


def lookup_unique(key, table):
    """table[key] where exactly one entry matches; None if zero or several."""
    hits = [v for k, v in table.items() if k == key]
    return hits[0] if len(hits) == 1 else None


def fetch_gis_districts(session):
    """{name_key: district} from the county GIS's board-member rows."""
    r = session.get(GIS_LAYER, headers=UA, timeout=60, params={
        "where": "electedoffice='County Board Member'", "f": "json",
        "returnGeometry": "false", "outFields": "districtid,repname1",
    })
    r.raise_for_status()
    # An ArcGIS error arrives as HTTP 200 with an `error` member, so without
    # this the WARN path below never fires: the layer would look empty and the
    # run would report success having filled no district at all.
    payload = raise_for_arcgis_error(r.json(), "Tazewell's GIS board layer")
    out, seen = {}, set()
    for feat in payload.get("features", []):
        a = feat.get("attributes", {})
        # the GIS annotates one name with its role — "Mike Harris (Vice-Chair)"
        name = re.sub(r"\s*\([^)]*\)\s*$", "", clean(a.get("repname1")))
        district = clean(str(a.get("districtid") or ""))
        key = name_key(name)
        if not key or not district:
            continue
        if key in seen:
            # two GIS members share an initial+surname: drop both rather than
            # risk pairing the wrong one (lookup_unique would too, but this
            # keeps the ambiguity out of the table entirely)
            out.pop(key, None)
            continue
        seen.add(key)
        out[key] = district
    return out


def main():
    session = requests.Session()
    index = session.get(INDEX_URL, headers=UA, timeout=60)
    index.raise_for_status()
    urls = sorted(set(MEMBER_RE.findall(index.text)))
    if not urls:
        print("tazewell-board-scraper: FAIL — no member links on the index "
              "(markup change?)", file=sys.stderr)
        sys.exit(1)

    try:
        gis = fetch_gis_districts(session)
    except requests.RequestException as exc:
        print("tazewell-board-scraper: WARN — GIS roster unreadable (%s); no "
              "district gap can be filled from it" % exc, file=sys.stderr)
        gis = {}

    records = []
    for url in urls:
        try:
            page = session.get(url, headers=UA, timeout=60)
            page.raise_for_status()
        except requests.RequestException as exc:
            print("tazewell-board-scraper: WARN — %s unreadable (%s)" % (url, exc),
                  file=sys.stderr)
            continue
        rec = parse_member(url, page.text)
        if not rec:
            print("tazewell-board-scraper: WARN — %s parsed no name" % url, file=sys.stderr)
            continue
        if rec["district"] is None and rec["role"] is None:
            print("tazewell-board-scraper: WARN — %s has an unrecognized "
                  "designation %r" % (rec["name"], rec["designation"]), file=sys.stderr)

        key = name_key(rec["name"])
        rec["gisDistrict"] = lookup_unique(key, gis) if key else None
        if rec["district"]:
            rec["districtSource"] = "website"
            if rec["gisDistrict"] and rec["gisDistrict"] != rec["district"]:
                print("tazewell-board-scraper: NOTE — %s: website says district "
                      "%s, county GIS says %s; keeping the website's"
                      % (rec["name"], rec["district"], rec["gisDistrict"]),
                      file=sys.stderr)
        elif rec["role"] == "Chairman":
            # countywide-elected; no district to fill and none wanted
            rec["districtSource"] = None
        elif rec["gisDistrict"]:
            rec["district"] = rec["gisDistrict"]
            rec["districtSource"] = "gis"
            print("tazewell-board-scraper: NOTE — %s: website states no "
                  "district; filling district %s from the county GIS"
                  % (rec["name"], rec["gisDistrict"]), file=sys.stderr)
        else:
            rec["districtSource"] = None
            print("tazewell-board-scraper: WARN — %s holds a district seat but "
                  "neither the website nor the county GIS states which"
                  % rec["name"], file=sys.stderr)
        records.append(rec)

    if not records:
        print("tazewell-board-scraper: FAIL — zero rows parsed", file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": INDEX_URL, "records": records},
                     indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("tazewell-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
