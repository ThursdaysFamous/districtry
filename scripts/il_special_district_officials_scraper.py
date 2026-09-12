#!/usr/bin/env python3
"""Officers for Illinois fire and park district cards, from AFRs.

WHY THIS EXISTS. il/index.html draws fire protection districts in 26 counties
and park districts in 18. Six named their officers before this file: Peoria,
Logan, Woodford, Grundy and Kankakee through their own AFR scrapers, and
Boone's park districts through the county's directory. Everywhere else the card
gave the district's name, the county, and nobody. No gap record said so, which
is the same shape as the four counties that gained precincts on 2026-08-21: an
absence with no refusal behind it.

WHAT IT COVERS. 27 county/layer pairs. Ten read their card names off a GeoJSON
committed here; seventeen read them from the county's own ArcGIS service at
scrape time, because that is where il/index.html reads them at render time --
the shape kankakee_district_officials_scraper.py takes for k3gis.net, applied
to every county that publishes that way. See BOUNDARIES.

LAKE COUNTY'S TWO ENTRIES RENDER DIFFERENTLY FROM EVERY OTHER ONE HERE, and
that is why it arrived a change later than the rest. Its fire and park entries
are bespoke rather than polygonCountyEntry: they render through orgEntryCard,
which Kane's three entries also use, because Lake's GIS carries each district's
own office address, telephone, e-mail and website on the feature. That helper
now takes an optional people node, placed after the link row and before the
office block, which is the order it already took when a county's own data named
an officer. Lake's library entry passes none and is unchanged, as are Kane's
three.

THE KEY IS COUNTY AND LAYER, NOT COUNTY ALONE, and Macon is why. Its fire layer
and its park layer both draw a district called `BlueMound`, and both draw one
called `Niantic`; they are four different bodies filing four different reports.
A payload keyed by county and name alone would have put the park board on the
fire card for two of them.

THE JOIN TABLE IS DATA, NOT CODE, and lives in il/data/source/afr-special-
districts.json. --propose rebuilds it by indexing every fire and park district
unit in all 102 counties and matching mechanically; every row then carries the
unit code and the Warehouse's own label, type and county, ALL RE-VERIFIED ON
EVERY RUN, so a renumbered or reassigned code fails the run instead of shipping
another district's officers. Re-matching weekly instead would lose a card's
officers quietly. The rules are in resolve_card and nothing semantic is
allowed; a name that is ambiguous is refused rather than guessed.

TWO CARDS IN ONE COUNTY CLAIMING ONE UNIT FAILS THE RUN, and that guard has
caught a real error rather than a hypothetical one. Stephenson's layer draws
both `Freeport Fire-Ambulance` and `Freeport Rural Fire-Ambulance` and the
Warehouse files one Freeport fire unit; the City of Freeport runs its own
department, which files inside the city's report, so the FIRE PROTECTION
DISTRICT unit is the rural one and the plain-named card has no district to name
at all. A unit serving two cards in DIFFERENT counties is legitimate and
common: a cross-county district files once, under its home county, which is
what `filesIn` says.

A MUNICIPAL DEPARTMENT IS NOT A MISSING SOURCE. Many of the cards that join to
nothing are a city's or village's own fire department, which files inside that
municipality's report and has no district of its own -- all sixteen of St.
Clair's `... Fire Dept.` names, Quincy's, Springfield's, Dixon's, Watseka's,
McLeansboro's and Wayne City's. Each is recorded in the table's `notFiled` with
that reason rather than counted as a failure to match.

SPELLINGS THE TWO PUBLISHERS DISAGREE ON ARE RECORDED AND CORRECTED IN NEITHER
DIRECTION: the county writes `Ciso` where the Warehouse and the village write
Cisco, `Kenny` where both write Kenney, `CAMBELLS ISLAND` where the Warehouse
writes Campbells Island, `GARDEN HOME` where it writes Garden Homes, and
`Papineu` where it writes Papineau. The card keeps the county's spelling,
because the county drew the polygon.

TWO COUNTIES JOIN ON SOMETHING OTHER THAN A NAME, and both were recorded as
unreachable before they were measured. Boone publishes its five fire districts
as the bare numbers 1 to 5, and the Warehouse's own labels carry the same five
numbers, each exactly once. Monroe publishes an acronym and a zone number and
no name at all, but il/index.html already carries the eight expansions its
County Clerk confirmed by e-mail on 2026-08-25 and the card shows them, so this
scraper reads that table out of the app rather than keeping a second copy.

Usage:
    python3 scripts/il_special_district_officials_scraper.py --out /tmp/x.json
    python3 scripts/il_special_district_officials_scraper.py --propose
"""

import argparse
import collections
import datetime
import difflib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from comptroller_afr import (  # noqa: E402  (shared machinery — do not fork)
    PACE, SEARCH_FORM, WAREHOUSE, contact_block, enumerate_county, new_session)
from scraper_common import UA_ROSTER_COMPACT  # noqa: E402  (shared — do not fork)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(REPO_ROOT, "il", "data", "app")
APP_HTML = os.path.join(REPO_ROOT, "il", "index.html")

# One request a second to a county's own GIS, the same courtesy PACE gives the
# Comptroller. These are nineteen different hosts, so the pacing is per host in
# practice and the whole sweep costs under half a minute.
SERVICE_PACE = 1.0

# (county slug, layer) -> the shipped boundary file and the property the app
# keys its cards on. These are the same files and the same properties
# il/index.html reads, so a file that changes shape breaks the cards too.
# ---------------------------------------------------------------------------
# WHERE THE CARD NAMES COME FROM
#
# Two shapes, and the difference is the whole reason this file grew. A
# FILE-backed pair reads the names off a GeoJSON committed in this repo. A
# SERVICE-backed pair reads them from the county's own ArcGIS service at scrape
# time, which is what il/index.html does at render time -- so the scraper has to
# ask the same service the app will, the way kankakee_district_officials_
# scraper.py asks k3gis.net. A name in one and not the other fails the run.
#
# Every service query below is the one the app's own loader builds, with
# returnGeometry=false: the names are all this needs and the boundary is a
# megabyte it would throw away.
# ---------------------------------------------------------------------------
COOK_GIS = ("https://gis.cookcountyil.gov/traditional/rest/services/"
            "politicalBoundary/MapServer")
DUPAGE_GIS = "https://services.arcgis.com/neJvtQ4PXvnQ86MJ/arcgis/rest/services/"
MCHENRY_GIS = "https://services1.arcgis.com/6iYC5AXXYapRVNzl/arcgis/rest/services/"
DEKALB_GIS = "https://services7.arcgis.com/hEXJrPwm89CLXBYe/arcgis/rest/services/"
ADAMS_GIS = "https://services3.arcgis.com/BXTAaNPMn1VANOeH/arcgis/rest/services/"
IROQUOIS_GIS = "https://services6.arcgis.com/6FZQl5a5SiSFMv8P/arcgis/rest/services/"
MADISON_GIS = "https://services.arcgis.com/Z0kKj2K728ngqqrp/arcgis/rest/services/"
EFFINGHAM_GIS = "https://services.arcgis.com/vj0V9Lal6oiz0YXp/arcgis/rest/services/"
HAMILTON_GIS = "https://services.arcgis.com/4YineAQdtmx0tv46/arcgis/rest/services/"
MONROE_GIS = "https://services.arcgis.com/AZVIEb4WFZST2UYx/arcgis/rest/services/"
SANGAMON_GIS = "https://services.arcgis.com/XqG0RpqsNfIBGGb2/arcgis/rest/services/"
STCLAIR_GIS = "https://arcgispublicmap.co.st-clair.il.us/server/rest/services/"
LEE_GIS = "https://gis.leecountyil.gov/leecogis/rest/services/"
LAKE_GIS = "https://services3.arcgis.com/HESxeTbDliKKvec2/arcgis/rest/services/"

# (county slug, layer) -> how to read that layer's card names.
#   {"file": ..., "key": ...}                 a committed GeoJSON
#   {"service": ..., "where": ..., "field": ...}   the county's own service
# `key`/`field` is the property il/index.html's card reads, so the roster this
# writes is keyed on the string the app will look up.
BOUNDARIES = {
    ("cook", "fire"): {"file": "cook-fire-districts.json", "key": "AGENCY_DESCRIPTION"},
    ("kendall", "fire"): {"file": "kendall-fire-districts.json", "key": "fire"},
    ("kendall", "park"): {"file": "kendall-park-districts.json", "key": "park"},
    ("macon", "fire"): {"file": "macon-fire-districts.json", "key": "Fire"},
    ("macon", "park"): {"file": "macon-park-districts.json", "key": "Park"},
    ("rock-island", "fire"): {"file": "rock-island-fire-districts.json", "key": "FirePD"},
    ("rock-island", "park"): {"file": "rock-island-park-districts.json", "key": "park_distr"},
    ("stark", "fire"): {"file": "stark-fire-districts.json", "key": "name"},
    ("stark", "park"): {"file": "stark-park-districts.json", "key": "name"},
    ("stephenson", "fire"): {"file": "stephenson-fire-districts.json", "key": "district"},
    ("cook", "park"): {"service": COOK_GIS + "/23", "where": "1=1",
                       "field": "AGENCY_DESCRIPTION"},
    ("dupage", "fire"): {"service": DUPAGE_GIS + "Fire_Protection_Districts_/FeatureServer/3",
                         "where": "1=1", "field": "FIRE"},
    ("dupage", "park"): {"service": DUPAGE_GIS + "Park_Districts_/FeatureServer/11",
                         "where": "1=1", "field": "PARK"},
    ("mchenry", "fire"): {"service": MCHENRY_GIS + "Fire_Districts/FeatureServer/0",
                          "where": ("FireDist NOT LIKE 'Z NO%' AND FireDist NOT LIKE '%CITY' "
                                    "AND FireDist NOT LIKE '%RESCUE SQUAD%'"),
                          "field": "FireDist"},
    ("dekalb", "fire"): {"service": DEKALB_GIS + "PT_Fire_Districts/FeatureServer/4",
                         "where": "1=1", "field": "Fire_District"},
    ("dekalb", "park"): {"service": DEKALB_GIS + "PT_Park_Districts/FeatureServer/9",
                         "where": "1=1", "field": "District"},
    ("lee", "fire"): {"service": LEE_GIS + "Fire_Districts/MapServer/0",
                      "where": "1=1", "field": "DsplayName"},
    ("adams", "fire"): {"service": ADAMS_GIS + "Web_District_Data/FeatureServer/3",
                        "where": "1=1", "field": "DsplayName"},
    ("iroquois", "fire"): {"service": IROQUOIS_GIS + "FireDistricts_REACH/FeatureServer/5",
                           "where": "1=1", "field": "Name"},
    ("sangamon", "fire"): {"service": SANGAMON_GIS + "FireDistrictEtc/FeatureServer/2",
                           "where": "1=1", "field": "District"},
    ("st-clair", "fire"): {"service": STCLAIR_GIS + "CentralSquare/DATA/MapServer/8",
                           "where": "1=1", "field": "name"},
    # BOONE READS THE SHIPPED FILE, NOT THE COUNTY'S SERVICE. Its fire layer
    # came off Fire_Districts/MapServer/0 until 2026-09-12, and the app stopped
    # drawing that service on the same day: the county levies SIX fire
    # protection districts and that layer carries five polygons, drawing Cherry
    # Valley's Boone territory as district 2 and the City of Loves Park's strip
    # as district 3 where the county's own tax roll gives neither a fire levy
    # (#893). Left pointed at the service this run would key on five districts
    # the app no longer draws, and the sixth card would never get a board.
    ("boone", "fire"): {"file": "boone-fire-districts.json", "key": "district"},
    ("effingham", "fire"): {"service": EFFINGHAM_GIS + "Districts/FeatureServer/5",
                            "where": "ZoneDesc <> 'None'", "field": "ZoneDesc"},
    ("effingham", "park"): {"service": EFFINGHAM_GIS + "TaxDistricts_public/FeatureServer/7",
                            "where": "1=1", "field": "NAME"},
    ("hamilton", "fire"): {"service": HAMILTON_GIS + "Fire_Districts_HamiltonIL/FeatureServer/0",
                           "where": "NAME IS NOT NULL", "field": "NAME"},
    # MONROE PUBLISHES AN ACRONYM AND A ZONE NUMBER AND NO NAME. The card shows
    # the expansion il/index.html carries in MONROE_FIRE_NAMES, which the County
    # Clerk confirmed by e-mail on 2026-08-25, so the join key is that expansion
    # and this scraper READS THE APP'S OWN TABLE rather than keeping a second
    # copy of it. A parse failure there fails the run.
    ("monroe", "fire"): {"service": MONROE_GIS + "Fire_Districts/FeatureServer/0",
                         "where": "1=1", "field": "FIRE_DIST", "expand": "monroe"},
    ("madison", "park"): {"service": MADISON_GIS + "MadCo_ParkDistricts/FeatureServer/40",
                          "where": "1=1", "field": "PARK"},
    ("lake", "fire"): {"service": LAKE_GIS + "LakeCounty_TaxDistricts/FeatureServer/4",
                       "where": "ORG_NAME IS NOT NULL", "field": "ORG_NAME"},
    ("lake", "park"): {"service": LAKE_GIS + "LakeCounty_TaxDistricts/FeatureServer/11",
                       "where": "ORG_NAME IS NOT NULL", "field": "ORG_NAME"},
}

# The county slug the card belongs to -> the Warehouse's spelling, used to
# decide whether a record needs `filesIn`.
SLUG_COUNTY = {
    "cook": "Cook", "kendall": "Kendall", "macon": "Macon",
    "rock-island": "Rock Island", "stark": "Stark", "stephenson": "Stephenson",
    "dupage": "Dupage", "mchenry": "Mchenry", "dekalb": "Dekalb", "lee": "Lee",
    "adams": "Adams", "iroquois": "Iroquois", "sangamon": "Sangamon",
    "st-clair": "St. Clair", "boone": "Boone", "effingham": "Effingham",
    "hamilton": "Hamilton", "monroe": "Monroe", "madison": "Madison",
    "lake": "Lake",
}

# THE WAREHOUSE'S SPELLING OF A COUNTY IS NOT ALWAYS THE COUNTY'S OWN, and
# `filesIn` is the one value in this file a READER sees. THE ALIAS IS FOR
# DISPLAY ONLY -- every search and every verification uses the Warehouse's own
# spelling, because that is the string its search matches.
COUNTY_DISPLAY = {"Dupage": "DuPage", "Dekalb": "DeKalb", "Lasalle": "LaSalle",
                  "Mchenry": "McHenry", "Mcdonough": "McDonough",
                  "Mclean": "McLean", "Jo Daviess": "Jo Daviess"}

# The join table and the measured absences both live in this committed file,
# regenerated by --propose and verified against the Warehouse on every run.
TABLE_PATH = os.path.join(REPO_ROOT, "il", "data", "source",
                          "afr-special-districts.json")

# An office one person holds. A district filing one of these TWICE has filed
# one person under two spellings, not a two-president board. A plural office
# (Trustee, Commissioner) is deliberately absent: repeating it is what a board
# looks like.
SINGULAR_OFFICES = {"president", "acting president", "vice president",
                    "treasurer", "secretary", "sec./treas.", "chairman",
                    "chief", "director", "acting director"}


def fail(msg):
    sys.exit("il-special-district-officials: FATAL — " + msg)


def surname(name):
    parts = [p for p in (name or "").replace(",", " ").split() if p]
    return parts[-1].lower() if parts else ""


def drop_refiled_duplicates(name, officers, notes):
    """Drop a singular office filed twice under one near-identical name.

    Every drop is appended to `notes`, so a run says which name it removed and
    which it kept rather than a board quietly losing a row.
    """
    kept, seen = [], {}
    for bucket, person in officers:
        role = (person.get("role") or "").strip().lower()
        if role in SINGULAR_OFFICES and role in seen:
            first = seen[role]
            close = difflib.SequenceMatcher(
                None, surname(first["name"]), surname(person["name"])).ratio()
            if close >= 0.8:
                notes.append("%s files %s twice — kept %r, dropped %r (one "
                             "person, two spellings)"
                             % (name, person.get("role"), first["name"],
                                person["name"]))
                continue
        if role in SINGULAR_OFFICES:
            seen.setdefault(role, person)
        kept.append((bucket, person))
    return kept


MONROE_NAMES_RE = re.compile(r"var MONROE_FIRE_NAMES = \{(.*?)\};", re.S)


def monroe_fire_names():
    """The app's OWN acronym expansions, read from il/index.html.

    Monroe's service publishes `CVFD` and a zone number and no name anywhere;
    il/index.html stamps the expansion onto the feature and the card shows it,
    so that expansion is the string this roster has to be keyed on. It is read
    here rather than copied, because a second copy of a table is a second thing
    to keep in step. The eight expansions are the County Clerk's own, confirmed
    by e-mail on 2026-08-25.
    """
    with open(APP_HTML, encoding="utf-8") as fh:
        m = MONROE_NAMES_RE.search(fh.read())
    if not m:
        fail("MONROE_FIRE_NAMES is no longer in il/index.html — Monroe's card "
             "names come from it and cannot be guessed")
    names = dict(re.findall(r'(\w+):\s*"([^"]+)"', m.group(1)))
    if len(names) < 8:
        fail("read %d Monroe expansion(s) from il/index.html, expected 8"
             % len(names))
    return names


def service_names(spec, label):
    """Distinct card names from a county's own ArcGIS service.

    returnGeometry=false: the names are all this needs, and the boundary is a
    megabyte it would throw away. A service that errors FAILS the run — a name
    list this cannot read is not the same thing as a district that stopped
    filing, and the difference must not be smoothed into a thinner payload.
    """
    url = (spec["service"] + "/query?where=" + urllib.parse.quote(spec["where"])
           + "&outFields=" + spec["field"] + "&returnGeometry=false&f=json")
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA_ROSTER_COMPACT}),
                timeout=60) as r:
            payload = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:                       # noqa: BLE001 (reported, not swallowed)
        fail("%s: %s" % (label, exc))
    if "error" in payload:
        fail("%s: the service returned an error envelope — %s"
             % (label, (payload["error"] or {}).get("message")))
    rows = payload.get("features") or []
    if not rows:
        fail("%s: the service returned no features" % label)
    out = []
    for f in rows:
        value = (f.get("attributes") or {}).get(spec["field"])
        if value is not None and str(value).strip():
            out.append(str(value).strip())
    if not out:
        fail("%s: no %r values on %d feature(s) — the layer changed shape"
             % (label, spec["field"], len(rows)))
    return out


def shipped_cards():
    """{(county slug, layer): [card name]} the app will look these up by."""
    cards, monroe = {}, None
    for (county, layer), spec in sorted(BOUNDARIES.items()):
        label = "%s %s" % (county, layer)
        if "file" in spec:
            path = os.path.join(APP_DATA, spec["file"])
            with open(path, encoding="utf-8") as fh:
                geojson = json.load(fh)
            found = [(f.get("properties") or {}).get(spec["key"])
                     for f in geojson.get("features") or []]
            found = [n for n in found if n]
            if not found:
                fail("%s carries no %r values — the boundary file changed shape"
                     % (spec["file"], spec["key"]))
        else:
            time.sleep(SERVICE_PACE)
            found = service_names(spec, label)
            if spec.get("expand") == "monroe":
                if monroe is None:
                    monroe = monroe_fire_names()
                missing = sorted({n.strip().upper() for n in found} - set(monroe))
                if missing:
                    fail("Monroe's service publishes %s, which il/index.html's "
                         "MONROE_FIRE_NAMES does not expand — the card would "
                         "show the acronym and this roster would miss it"
                         % ", ".join(missing))
                found = [monroe[n.strip().upper()] for n in found]
        cards[(county, layer)] = sorted(set(found))
    return cards


def load_table():
    """The join table and the measured absences, from the committed file."""
    if not os.path.exists(TABLE_PATH):
        fail("%s is missing — regenerate it with --propose" % TABLE_PATH)
    with open(TABLE_PATH, encoding="utf-8") as fh:
        payload = json.load(fh)
    districts = [(d["county"], d["layer"], d["card"], d["code"], d["label"],
                  d["type"], d["warehouseCounty"])
                 for d in payload.get("districts") or []]
    not_filed = {(n["county"], n["layer"], n["card"]): n["reason"]
                 for n in payload.get("notFiled") or []}
    if not districts:
        fail("%s names no districts" % TABLE_PATH)
    return districts, not_filed


def verify_units(session, districts):
    """Assert every row of the table still names the unit it claims.

    ONE SEARCH PER WAREHOUSE COUNTY, not one per unit: enumerate_county returns
    every typed unit the Warehouse files under a county, so a few dozen requests
    cover every row.
    """
    wanted = {}
    for _slug, _layer, _name, code, label, unit_type, county in districts:
        wanted.setdefault(county, {})[code] = "%s - a %s in %s County" % (
            label, unit_type, county)
    for county, codes in sorted(wanted.items()):
        time.sleep(PACE)
        units = dict(enumerate_county(session, county))
        if not units:
            fail("the Warehouse returned no %s County units — the search "
                 "changed shape" % county)
        for code, expected in sorted(codes.items()):
            got = units.get(code)
            if got is None:
                fail("unit %s is no longer filed under %s County — the "
                     "Warehouse renumbered it, or the district dissolved"
                     % (code, county))
            if got != expected:
                fail("unit %s is now %r, expected %r — this table would ship "
                     "another district's officers" % (code, got, expected))


def check_table_against_boundaries(cards, districts, not_filed):
    """The layers and this table must name the same districts, both ways."""
    table = {(slug, layer, name)
             for slug, layer, name, _c, _l, _t, _co in districts}
    table |= set(not_filed)
    shipped = {(slug, layer, name)
               for (slug, layer), names in cards.items() for name in names}
    missing = sorted(shipped - table)
    extra = sorted(table - shipped)
    if missing or extra:
        fail("the layers and this table name different districts — not in "
             "the table: %s; not in the layers: %s"
             % (missing or "none", extra or "none"))
    # One unit legitimately serves two cards in different counties. Two cards in
    # ONE county claiming one unit is the Freeport shape and is never right.
    claimed = {}
    for slug, layer, name, code, _l, _t, _co in districts:
        first = claimed.get((slug, code))
        if first:
            fail("%s and %s are both in %s and both claim unit %s — one of "
                 "them is a municipal department rather than a district"
                 % (first, name, slug, code))
        claimed[(slug, code)] = name


# ---------------------------------------------------------------------------
# REBUILDING THE JOIN TABLE (--propose, an operator step)
#
# The table in il/data/source/afr-special-districts.json is DATA, and this is
# how it was derived: index every fire and park district unit the Warehouse
# files in all 102 counties, then match each card name against that index by
# mechanical rules only. Nothing semantic. Every rule prints its own count, an
# ambiguous name is REFUSED rather than guessed, and two cards in one county
# claiming one unit fails outright.
#
# WHY A TABLE AT ALL, when the rules could run every week: a table is verified
# against the Warehouse's own label, type and county on every run, so a
# renumbered or reassigned code FAILS LOUDLY. Re-matching each week would
# instead lose a card's officers quietly and leave it to the builder's floors
# to notice.
#
# OVERRIDES ARE THE CASES THE RULES CANNOT SEE, and each is a spelling the two
# publishers disagree on, an abbreviation a county invented, or a body whose
# identity needed a second document. They are in the table like any other row
# and carry `rule: "override"` so a reader can find them.
# ---------------------------------------------------------------------------
UNIT_TYPE_OF = {"fire": "Fire Protection District", "park": "Park District"}
# Words a name ends in that say what KIND of body it is rather than which one.
TYPE_TAIL = {
    "fire": ("fire", "protection", "district", "department", "ambulance",
             "ems", "and", "rescue", "squad", "volunteer"),
    "park": ("park", "district", "and", "recreation", "parks"),
}
# Abbreviations one publisher uses and the other spells out.
ABBREV = {"twp": "township", "ctr": "center", "dept": "department",
          "dist": "district", "fpd": "fire", "prot": "protection",
          "co": "county", "mount": "mt", "saint": "st", "fd": "fire",
          "pd": "park", "grv": "grove", "ctry": "country", "vol": "volunteer"}
# A single trailing word that qualifies a name without changing which body it
# names. Kept short on purpose: every addition is a chance to match two
# different bodies to each other.
QUALIFIERS = {"area", "community", "communities", "countryside", "rural",
              "regional", "township", "county"}


def name_tokens(value):
    text = value.lower().replace("&", " and ").replace("/", " ")
    text = text.replace("-", " ").replace("#", " ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    out, run = [], []
    for word in re.sub(r"\s+", " ", text).strip().split():
        # A run of single letters is one word: "E.M.S." is `ems`.
        if len(word) == 1:
            run.append(word)
            continue
        if run:
            out.append("".join(run))
            run = []
        out.append(ABBREV.get(word, word))
    if run:
        out.append("".join(run))
    return out


def name_stem(value, layer):
    words = name_tokens(value)
    while words and words[-1] in TYPE_TAIL[layer]:
        words.pop()
    return words


def build_unit_index(session):
    """Every fire and park district unit in all 102 counties, four ways."""
    from il_library_district_officials_scraper import COUNTIES  # noqa: E402
    plain = collections.defaultdict(list)      # exact stem
    qualified = collections.defaultdict(list)  # stem minus a trailing qualifier
    numbered = collections.defaultdict(list)   # stem minus a trailing number
    unordered = collections.defaultdict(list)  # same words, any order
    meta = {}
    for county in COUNTIES:
        time.sleep(PACE)
        for code, label in enumerate_county(session, county):
            for layer, unit_type in sorted(UNIT_TYPE_OF.items()):
                if (" - a %s in " % unit_type) not in label:
                    continue
                name = label.split(" - a ")[0]
                words = name_stem(name, layer)
                plain[(layer, "".join(words))].append(code)
                if words and words[-1] in QUALIFIERS:
                    qualified[(layer, "".join(words[:-1]))].append(code)
                if words and re.fullmatch(r"\d+", words[-1]):
                    numbered[(layer, "".join(words[:-1]))].append(code)
                unordered[(layer, "".join(sorted(w for w in words if w != "of")))].append(code)
                meta[code] = (name, unit_type, county)
    if len(meta) < 1000:
        fail("indexed %d fire and park district unit(s), expected over 1,000 — "
             "the Warehouse search changed shape" % len(meta))
    return plain, qualified, numbered, unordered, meta


# A card name the rules cannot resolve, and the unit it names. Each is a
# spelling the two publishers disagree on, an abbreviation a county invented,
# or a body whose identity took a second document to settle. Never a guess: the
# reason for each is in the module docstring or beside it here.
OVERRIDES = {
    # Boone publishes its five districts as bare numbers and the Warehouse
    # labels carry the same five numbers, each exactly once. Its SIXTH is a
    # Winnebago-seated district reaching across the line, which the rules cannot
    # match because it is the only Boone card naming a body rather than a
    # number: the Warehouse files it under its home county, so the row's
    # warehouseCounty is Winnebago and the card says so.
    ("boone", "fire", "1"): "004/010/06",
    ("boone", "fire", "2"): "004/020/06",
    ("boone", "fire", "3"): "004/030/06",
    ("boone", "fire", "4"): "004/040/06",
    ("boone", "fire", "5"): "004/050/06",
    ("boone", "fire", "Cherry Valley Fire Protection District"): "101/020/06",
    # Abbreviations the county invented for its own map.
    ("mchenry", "fire", "ALG LITH FIRE DIST"): "063/010/06",
    ("mchenry", "fire", "HEB ALD GRW FIRE"): "063/060/06",
    ("mchenry", "fire", "BARRINGTON CTRY FIRE"): "016/010/06",
    ("sangamon", "fire", "LAKE SPFLD FPD"): "083/090/06",
    ("lee", "fire", "BUREAU CO/OHIO FIRE"): "006/110/06",
    ("lee", "fire", "BUREAU CO/WALNUT FIRE"): "006/165/06",
    # "First" is the "#1" the Warehouse writes.
    ("lake", "fire", "First Fire Protection District of Antioch"): "049/010/06",
    ("lake", "fire", "Lincolnshire-Riverwoods Fire Protection District"): "049/130/06",
    # A qualifier each publisher writes differently.
    ("dupage", "fire", "South Elgin"): "045/170/06",
    ("dupage", "fire", "Fox River"): "045/160/06",
    ("lee", "fire", "DIXON RURAL FIRE"): "052/040/06",
    ("sangamon", "fire", "ATHENS FPD"): "065/010/06",
    ("adams", "fire", "Lima Fire"): "001/060/06",
    ("adams", "fire", "Payson Fire"): "001/090/06",
    ("effingham", "fire", "Edgewood"): "025/030/06",
    # The county drops a letter the Warehouse and the village both keep.
    ("iroquois", "fire", "Papineu"): "038/160/06",
    # Two units share this name; only one is in a county the card can touch.
    ("dupage", "fire", "Pleasantview"): "016/280/06",
    ("cook", "park", "FRANKFORT PARK DISTRICT"): "099/030/12",
    # Cook draws both La Grange's district and La Grange Park's, and their
    # names cross: the plainly-named card is La Grange's.
    ("cook", "park", "LA GRANGE PARK DISTRICT"): "016/390/12",
    ("cook", "park", "COMMUNITY PARK DIST OF LAGRANGE PARK"): "016/170/12",
    # Same words, reversed.
    ("cook", "park", "LIGHTHOUSE PARK DISTRICT OF EVANSTON"): "016/220/12",
    # The county carries a number the Warehouse writes as "#N", or the reverse.
    ("cook", "fire", "BENSENVILLE FIRE PROTECTION DISTRICT #2"): "022/255/06",
    ("cook", "fire", "HOFFMAN ESTATES FIRE PROTECTION DIST 1"): "016/070/06",
    # The county writes HOME, the Warehouse Homes.
    ("cook", "fire", "GARDEN HOME FIRE PROTECTION DISTRICT"): "016/065/06",
    # Two units share this name, in Madison and in Will. A district drawn in
    # Kendall has to touch Kendall, and Kendall borders Will; Madison is 200
    # miles away and borders nothing this layer draws.
    ("kendall", "fire", "TROY FPD"): "099/140/06",
    # The county drops a letter the Warehouse, the village and the school
    # district all keep.
    ("macon", "fire", "Ciso"): "074/030/06",
    ("macon", "fire", "Kenny"): "020/015/06",
    ("rock-island", "fire", "CAMBELLS ISLAND FPD"): "081/060/06",
    # Speer is a village inside the Wyoming district; the county names both.
    ("stark", "fire", "Wyoming/Speer Fire Department"): "087/040/06",
    # Jo Daviess files a Warren Area fire district and a separate Warren Area
    # Ambulance district. This is the fire layer, so it takes the fire one.
    ("stephenson", "fire", "Warren Fire-Ambulance"): "043/085/06",
}


# A card a person has MEASURED as naming something other than a fire or park
# district. Every entry here is a municipality's own department -- it files
# inside that city's or village's report and has no district unit -- or a
# response zone inside one. Two reasons for a table rather than a rule. The
# rules cannot tell a city department from the rural district wrapped around
# the same town, which is how Stephenson's two Freeport cards both matched one
# unit. And a card the rules simply miss deserves the reason a person found
# rather than "no unit of this name", which is true of every one of them and
# says nothing. Each was checked against the Warehouse's own City/Village/Town
# filings for that county on 2026-09-11.
MEASURED_ABSENCE = {
    ("st-clair", "fire", "Alorton Fire Dept."):
        "the Village of Alorton's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Belleville Fire Dept."):
        "the City of Belleville's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Caseyville Fire Dept."):
        "the Village of Caseyville's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "East St Louis Fire Dept."):
        "the City of East St. Louis's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Fairmont City Fire Dept."):
        "the Village of Fairmont City's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Fairview Heights Fire Dept."):
        "the City of Fairview Heights's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Fayetteville Fire Dept."):
        "the Village of Fayetteville's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Lebanon Fire Dept."):
        "the City of Lebanon's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Lenzburg Fire Dept."):
        "the Village of Lenzburg's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Madison Fire Dept."):
        "the City of Madison's own department, which is in Madison County and reaches across the line, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "O'Fallon Fire Dept."):
        "the City of O'Fallon's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Sauget Fire Dept."):
        "the Village of Sauget's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Swansea Fire Dept."):
        "the Village of Swansea's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Washington Park Fire Dept."):
        "the Village of Washington Park's own department, which files inside that municipality's report and has no district unit",
    ("st-clair", "fire", "Scott AFB Fire Dept."):
        "the fire department of Scott Air Force Base, a federal installation, which files no report with the state at all",
    ("st-clair", "fire", "State Park Fire Dept."):
        "State Park Place is unincorporated, and neither a fire protection district nor a municipality of this name is filed in Illinois",
    ("adams", "fire", "Quincy 246"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 254"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 352"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 362"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 426"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 462"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 524"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 532"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 624"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 632"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy 642"):
        "a response-zone code inside the City of Quincy, which runs its own department and files inside the city's report",
    ("adams", "fire", "Quincy Fire"):
        "the City of Quincy's own department, which files inside that municipality's report and has no district unit",
    ("sangamon", "fire", "SPRINGFIELD CORP"):
        "the City of Springfield's own department, which files inside that municipality's report and has no district unit",
    ("sangamon", "fire", "WAVERLY FPD"):
        "the City of Waverly's own department; Waverly is in Morgan County and no fire protection district of that name is filed anywhere in Illinois",
    ("lee", "fire", "DIXON CITY FIRE"):
        "the City of Dixon's own department, which files inside that municipality's report and has no district unit",
    ("lee", "fire", "ROCHELLE/OGLE-LEE FIRE"):
        "the City of Rochelle's own department; Rochelle is in Ogle County and no fire protection district of that name is filed anywhere in Illinois",
    ("iroquois", "fire", "Watseka"):
        "the City of Watseka's own department, which files inside that municipality's report and has no district unit",
    ("hamilton", "fire", "MCLEANSBORO CITY FIRE DISTRICT"):
        "the City of McLeansboro's own department, which files inside that municipality's report and has no district unit",
    ("hamilton", "fire", "WAYNE CITY FIRE DISTRICT"):
        "the Village of Wayne City's own department; Wayne City is in Wayne County and no fire protection district of that name is filed anywhere in Illinois",
    ("monroe", "fire", "Red Bud Fire Department"):
        "the City of Red Bud's own department; Red Bud is in Randolph County and files no fire protection district",
    ("monroe", "fire", "Prairie du Rocher Community Fire Department"):
        "the Village of Prairie du Rocher's own department; it is in Randolph County and files no fire protection district",
    ("effingham", "fire", "Eff North"):
        "half of the county's response tiling for Effingham, which runs its own department and files inside the municipality's report",
    ("effingham", "fire", "Eff South"):
        "half of the county's response tiling for Effingham, which runs its own department and files inside the municipality's report",
    ("effingham", "fire", "Mont North"):
        "half of the county's response tiling for Montrose, which runs its own department and files inside the municipality's report",
    ("effingham", "fire", "Mont South"):
        "half of the county's response tiling for Montrose, which runs its own department and files inside the municipality's report",
    ("cook", "park", "FORD HEIGHTS PARK DISTRICT"):
        "the Village of Ford Heights; no park district of this name is filed anywhere in Illinois",
    ("mchenry", "fire", "LAKEWOOD FIRE DISTRICT"):
        "the Village of Lakewood; no fire protection district of this name is filed anywhere in Illinois",
    ("dupage", "fire", "Westmont"):
        "the county draws one Westmont polygon where the Warehouse files two "
        "districts, North Westmont and South Westmont, so nothing here says "
        "which of them this card is",
    ("dupage", "fire", "Batavia Twp"):
        "the nearest unit is Batavia-Countryside in Kane County, and the two "
        "publishers qualify the name differently enough that nothing witnesses "
        "they are one body",
    ("stephenson", "fire", "Freeport Fire-Ambulance"):
        "the City of Freeport's own department, which files inside the city's report; the county's Freeport Rural card carries the fire protection district",
}


def resolve_card(name, layer, warehouse_county, index):
    """(unit code, rule) or (None, why not). Mechanical rules only."""
    plain, qualified, numbered, unordered, meta = index
    words = name_stem(name, layer)
    key = "".join(words)

    def one(candidates):
        return candidates[0] if len(candidates) == 1 else None

    hits = plain.get((layer, key), [])
    if len(hits) == 1:
        return hits[0], "normalised"
    if len(hits) > 1:
        same = [c for c in hits if meta[c][2] == warehouse_county]
        if len(same) == 1:
            return same[0], "county tie-break"
        return None, "ambiguous: %s" % "; ".join(
            "%s (%s)" % (meta[c][0], meta[c][2]) for c in hits)
    hits = numbered.get((layer, key), [])
    if len(hits) > 1:
        return None, "ambiguous on its number: %s" % "; ".join(
            "%s (%s)" % (meta[c][0], meta[c][2]) for c in hits)
    if one(hits):
        return hits[0], "unit number dropped"
    if words and words[-1] in QUALIFIERS:
        hit = one(plain.get((layer, "".join(words[:-1])), []))
        if hit:
            return hit, "card qualifier dropped"
    hit = one(qualified.get((layer, key), []))
    if hit:
        return hit, "unit qualifier dropped"
    tokens = name_tokens(name)
    if "of" in tokens:                     # "PARK DISTRICT OF FRANKLIN PARK"
        tail = tokens[tokens.index("of") + 1:]
        while tail and tail[-1] in TYPE_TAIL[layer]:
            tail.pop()
        hit = one(plain.get((layer, "".join(tail)), []))
        if hit:
            return hit, "leading governance dropped"
    same_words = "".join(sorted(w for w in words if w != "of"))
    hit = one([c for c in unordered.get((layer, same_words), [])
               if meta[c][2] == warehouse_county])
    if hit:
        return hit, "word order"
    return None, "no unit of this name is filed anywhere in Illinois"


def propose_table():
    """Rebuild il/data/source/afr-special-districts.json from the Warehouse.

    An operator step: it indexes all 102 counties (about 102 paced requests) and
    then matches offline. It does NOT fetch a contact block and does not touch
    the shipped roster. Rows it cannot resolve are written to `notFiled` with
    the reason the rules gave, for a person to settle or to leave recorded.
    """
    cards = shipped_cards()
    session = new_session()
    index = build_unit_index(session)
    meta = index[4]
    districts, not_filed, rules = [], [], collections.Counter()
    for (county, layer), names in sorted(cards.items()):
        warehouse_county = SLUG_COUNTY[county]
        for name in names:
            measured = MEASURED_ABSENCE.get((county, layer, name))
            if measured:
                not_filed.append({"county": county, "layer": layer,
                                  "card": name, "reason": measured})
                continue
            code = OVERRIDES.get((county, layer, name))
            rule = "override"
            if code is None:
                code, rule = resolve_card(name, layer, warehouse_county, index)
            if code is None:
                not_filed.append({"county": county, "layer": layer,
                                  "card": name, "reason": rule})
                continue
            if code not in meta:
                fail("override %s/%s/%s names unit %s, which the Warehouse does "
                     "not file as a fire or park district"
                     % (county, layer, name, code))
            label, unit_type, unit_county = meta[code]
            districts.append({"county": county, "layer": layer, "card": name,
                              "code": code, "label": label, "type": unit_type,
                              "warehouseCounty": unit_county, "rule": rule})
            rules[rule] += 1
    claimed, collisions = {}, []
    for row in districts:
        first = claimed.get((row["county"], row["code"]))
        if first:
            collisions.append("%s/%s: %r and %r both claim %s (%s)"
                              % (row["county"], row["layer"], first,
                                 row["card"], row["code"], meta[row["code"]][0]))
        claimed[(row["county"], row["code"])] = row["card"]
    if collisions:
        for line in collisions:
            print("  COLLISION: %s" % line, file=sys.stderr)
        fail("%d card pair(s) in one county claim one unit — one of each pair "
             "is a municipal department rather than a district, and belongs in "
             "MEASURED_ABSENCE with that reason" % len(collisions))
    payload = {
        "note": ("The unit each fire and park district card joins to, and the "
                 "cards that join to none. Rebuilt by "
                 "il_special_district_officials_scraper.py --propose; every row "
                 "is re-verified against the Warehouse on every scrape."),
        "generated": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "districts": sorted(districts, key=lambda d: (d["county"], d["layer"], d["card"])),
        "notFiled": sorted(not_filed, key=lambda d: (d["county"], d["layer"], d["card"])),
    }
    with open(TABLE_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for rule, count in rules.most_common():
        print("  %-28s %d" % (rule, count), file=sys.stderr)
    for row in payload["notFiled"]:
        print("  NO UNIT: %s/%s/%s — %s"
              % (row["county"], row["layer"], row["card"], row["reason"]),
              file=sys.stderr)
    print("proposed %d district(s) and %d unresolved card(s) -> %s"
          % (len(districts), len(not_filed), TABLE_PATH), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", help="write the scraped payload here")
    ap.add_argument("--propose", action="store_true",
                    help="rebuild the join table from the Warehouse and write "
                         "it to il/data/source/afr-special-districts.json "
                         "(an operator step — see propose_table)")
    args = ap.parse_args()

    if args.propose:
        propose_table()
        return
    if not args.out:
        ap.error("--out is required unless --propose is given")

    cards = shipped_cards()
    districts, not_filed = load_table()
    check_table_against_boundaries(cards, districts, not_filed)

    session = new_session()                    # holds the ColdFusion cookie
    verify_units(session, districts)

    warnings, unmatched, notes = [], [], []
    blocks, counties = {}, {}
    for slug, layer, name, code, label, unit_type, county in districts:
        unit_label = "%s - a %s in %s County" % (label, unit_type, county)
        if code not in blocks:
            time.sleep(PACE)
            blocks[code] = contact_block(session, code, unit_label, warnings)
        block = blocks[code]
        if not block:
            unmatched.append("%s (%s %s) — unit %s files no contact block"
                             % (name, slug, layer, code))
            continue
        entry = {"comptrollerCode": code, "filedFor": block["filedFor"],
                 "office": {}}
        if county != SLUG_COUNTY[slug]:
            entry["filesIn"] = COUNTY_DISPLAY.get(county, county)
        for field, value in (("address", block["street"]), ("city", block["city"]),
                             ("phone", block["phone"]), ("email", block["email"])):
            if value:
                entry["office"][field] = value
        for bucket, person in drop_refiled_duplicates(
                name, block["officers"], notes):
            entry.setdefault(bucket, []).append(person)
        counties.setdefault(slug, {}).setdefault(layer, {})[name] = entry

    for (slug, layer, name), reason in sorted(not_filed.items()):
        unmatched.append("%s (%s %s) — %s" % (name, slug, layer, reason))

    stamped = sum(len(byname) for layers in counties.values()
                  for byname in layers.values())
    if not stamped:
        for w in warnings:
            print("  WARN: %s" % w, file=sys.stderr)
        fail("no district files a contact block — the search or the form broke")

    payload = {
        "source": "Illinois Comptroller, Annual Financial Report — Contact Information",
        "sourceUrl": WAREHOUSE,
        "officialsPage": SEARCH_FORM,
        "generated": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counties": counties,
    }
    # The card names this run actually read, so the builder can re-measure every
    # key without going back to nineteen county services (it must stay offline:
    # its --check runs in CI).
    payload["cards"] = {"%s/%s" % k: v for k, v in sorted(cards.items())}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    for w in warnings:
        print("  WARN: %s" % w, file=sys.stderr)
    for n in notes:
        print("  DUPLICATE: %s" % n, file=sys.stderr)
    for u in unmatched:
        print("  NOT MATCHED: %s" % u, file=sys.stderr)
    board = sum(len(e.get("board") or []) for layers in counties.values()
                for byname in layers.values() for e in byname.values())
    heads = sum(len(e.get("heads") or []) for layers in counties.values()
                for byname in layers.values() for e in byname.values())
    total = sum(len(names) for names in cards.values())
    print("scraped %d of %d card(s) across %d counties: %d board officer(s), "
          "%d appointed -> %s"
          % (stamped, total, len(counties), board, heads, args.out),
          file=sys.stderr)


if __name__ == "__main__":
    main()
