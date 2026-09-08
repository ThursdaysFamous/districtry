#!/usr/bin/env python3
"""
Scrape Peoria County's board roster into raw records.

Stage 1 of the two-stage pipeline (scripts/build_peoria_board_roster.py is
stage 2). Peoria is the first county whose roster SPINE is a GIS layer rather
than a page: the county's own `ElectoralDistricts` service publishes a
"County Commissioners" layer carrying, for each of the 18 single-member
districts, the member's name, party and the URL of that member's own page on
the county site. That layer is a stable, machine-readable enumeration — no
markup parsing decides who is on the board — and each member page then
supplies the phone and e-mail the layer does not carry.

So the district assignment and the name come from the county's GIS, the
contact from the county's own member page, and the pair is cross-checked
against the County Board Members index page (a THIRD county surface): a name
the index does not carry is reported, because two county surfaces disagreeing
is exactly the drift this pipeline exists to catch.

Peoria elects a Chairperson and a Vice-Chairperson from among the 18 — both
hold their own district seat as well — and the index page is the only surface
that marks them, so the role is read from there and attached to that member's
district row (never invented: a role appears only if the index states it).

FETCH POSTURE: open. Plain ArcGIS REST JSON + server-rendered CivicPlus HTML.

Usage:
    python3 peoria_county_board_scraper.py [output.json]   # default: stdout
"""

import html as html_mod
import json
import re
import sys

import requests

from arcgis_error import raise_for_arcgis_error
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared machinery — do not fork)

ROSTER_LAYER = ("https://services.arcgis.com/iPiPjILCMYxPZWTc/arcgis/rest/"
                "services/ElectoralDistricts/FeatureServer/3/query")
INDEX_URL = "https://www.peoriacounty.gov/755/County-Board-Members"
UA = {"User-Agent": UA_ROSTER_COMPACT}

MAILTO_RE = re.compile(
    r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
# the member pages label their numbers ("Phone:", "Work phone:", "Cell
# phone:") — take the first labelled number, which is the office line.
PHONE_RE = re.compile(
    r"(?:Work\s+)?[Pp]hone:\s*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})")
ROLE_RE = re.compile(r"\b(Chairperson|Vice\s+Chairperson)\b")


def clean(s):
    return re.sub(r"\s+", " ", html_mod.unescape(s or "")).strip()


def strip_tags(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    return html_mod.unescape(re.sub(r"(?s)<[^>]+>", "\n", s))


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) != 10:
        return None
    return "%s-%s-%s" % (digits[:3], digits[3:6], digits[6:])


def name_key(name):
    """Compare names across county surfaces without tripping on middle
    initials or punctuation ("James C. Dillon" vs "James Dillon")."""
    parts = [p for p in re.split(r"[^A-Za-z]+", (name or "").lower()) if len(p) > 1]
    return (parts[0], parts[-1]) if len(parts) >= 2 else tuple(parts)


def same_person(a, b):
    """Two name keys naming one person. The surfaces differ on diminutives —
    the GIS says "Robert Reneau" and "Matthew Windish" where the index page
    says "Rob" and "Matt" — so the surname must match exactly and the given
    names must agree as far as the shorter one runs. Deliberately strict on
    the surname: this cross-check exists to catch a member appearing on one
    county surface and not the other, and a loose match would hide that."""
    if not a or not b or a[-1] != b[-1]:
        return False
    return a[0].startswith(b[0]) or b[0].startswith(a[0])


def fetch_roster_layer(session):
    r = session.get(ROSTER_LAYER, headers=UA, timeout=60, params={
        "where": "1=1", "returnGeometry": "false", "f": "json",
        "outFields": "DISTRICTID,REPNAME1,PARTY1,DISTRICTURL1",
    })
    r.raise_for_status()
    # HTTP 200 with an `error` member would otherwise read as an empty roster
    # and trip the "zero rows parsed (service change?)" guard below, which
    # names the wrong cause for what is often a rate limit that clears.
    payload = raise_for_arcgis_error(r.json(), "Peoria's roster layer")
    rows = []
    for feat in payload.get("features", []):
        a = feat.get("attributes", {})
        district = clean(str(a.get("DISTRICTID") or ""))
        name = clean(a.get("REPNAME1"))
        if not district or not name:
            continue
        party = clean(a.get("PARTY1"))
        rows.append({
            "district": district,
            "name": name,
            # the layer spells one member's party "Democrat" and the rest
            # "Democratic" — normalize the adjective, don't invent one
            "party": "Democratic" if party == "Democrat" else (party or None),
            "url": clean(a.get("DISTRICTURL1")) or None,
        })
    return rows


def fetch_index_roles(session):
    """Index page -> {name_key: role}, plus the set of names it lists. Roles
    are only ever read from here; a member the index does not mark gets none."""
    r = session.get(INDEX_URL, headers=UA, timeout=60)
    r.raise_for_status()
    roles, listed = {}, set()
    for block in re.findall(r'(?is)<h3[^>]*class="subhead2"[^>]*>(.*?)</h3>', r.text):
        text = clean(strip_tags(block))
        m = re.match(r"([A-Za-z][A-Za-z.'\-\s]+?),?\s*(?:Chairperson|Vice\s+Chairperson|District\s+\d+|$)", text)
        if not m:
            continue
        key = name_key(m.group(1))
        if not key:
            continue
        listed.add(key)
        role = ROLE_RE.search(text)
        if role:
            roles[key] = re.sub(r"\s+", "-", role.group(1))
    return roles, listed


def fetch_member_contact(session, url):
    try:
        r = session.get(url, headers=UA, timeout=60)
        r.raise_for_status()
    except requests.RequestException:
        return None, None
    email = MAILTO_RE.search(r.text)
    phone = PHONE_RE.search(strip_tags(r.text))
    return (email.group(1).lower() if email else None,
            normalize_phone(phone.group(1)) if phone else None)


def main():
    session = requests.Session()
    rows = fetch_roster_layer(session)
    try:
        roles, listed = fetch_index_roles(session)
    except requests.RequestException as exc:
        print("peoria-board-scraper: WARN — index page unreadable (%s); "
              "no roles will be tagged" % exc, file=sys.stderr)
        roles, listed = {}, set()

    records = []
    for row in rows:
        key = name_key(row["name"])
        email = phone = None
        if row["url"]:
            email, phone = fetch_member_contact(session, row["url"])
        if listed and not any(same_person(key, k) for k in listed):
            print("peoria-board-scraper: WARN — %s (district %s) is on the GIS "
                  "roster but not the County Board Members index"
                  % (row["name"], row["district"]), file=sys.stderr)
        records.append({
            "district": row["district"],
            "name": row["name"],
            "party": row["party"],
            "role": next((r for k, r in roles.items() if same_person(key, k)), None),
            "phone": phone,
            "email": email,
            "url": row["url"],
        })

    if not records:
        print("peoria-board-scraper: FAIL — zero rows parsed (service change?)",
              file=sys.stderr)
        sys.exit(1)

    out = json.dumps({"source": INDEX_URL, "records": records},
                     indent=2, ensure_ascii=False)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(out)
        print("peoria-board-scraper: %d records -> %s" % (len(records), sys.argv[1]))
    else:
        print(out)


if __name__ == "__main__":
    main()
