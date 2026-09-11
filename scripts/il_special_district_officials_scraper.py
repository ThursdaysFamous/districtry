#!/usr/bin/env python3
"""Officers for six counties' fire and park district cards, from AFRs.

WHY THIS EXISTS. il/index.html draws fire protection districts in 26 counties
and park districts in 18, and only six of those had any officer on the card:
Peoria, Logan, Woodford, Grundy and Kankakee through their own AFR scrapers,
and Boone's park districts through its county's directory. Everywhere else the
card gave the district's name, the county, and nobody. No gap record said so,
which is the same shape as the four counties that gained precincts on
2026-08-21: an absence with no refusal behind it.

WHAT THIS COVERS AND WHY IT STOPS THERE. The six counties whose fire or park
boundaries ship as GeoJSON in this repo and had no officers: Cook (fire),
Kendall, Macon, Rock Island and Stark (fire and park), and Stephenson (fire).
119 cards. The other counties draw their boundaries from a live service at
render time, so their card names are not in this repo to join against; reaching
them means reading each county's own service the way kankakee_district_
officials_scraper.py does, one county at a time. That is the next step, not a
blocker, and the gap record names it.

THE TABLE IS EXPLICIT AND THE MATCHER ONLY PROPOSED IT, following Logan,
Woodford, Grundy and Kankakee. A Warehouse search is a substring match and the
two publishers abbreviate differently, so every row below carries the unit code
and the Warehouse's own label, type and county, all VERIFIED on each run --
23 searches cover all 115 units. A renumbered or reassigned code fails the run
instead of shipping another district's officers.

THE KEY IS COUNTY AND LAYER, NOT COUNTY ALONE, and Macon is why. Its fire layer
and its park layer both carry a district called `BlueMound`, and both carry one
called `Niantic`; they are four different bodies filing four different reports.
A payload keyed by county and name alone would have put the park board on the
fire card for two of them.

WHAT THE FIRST MECHANICAL PASS GOT WRONG, because the run is the record. A
normalised name match resolved 106 of the 119 cards, and one of those 106 was
wrong: Stephenson's layer draws both `Freeport Fire-Ambulance` and `Freeport
Rural Fire-Ambulance`, and the Warehouse files one Freeport fire unit. The City
of Freeport runs its own department and files inside the city's report, so the
FIRE PROTECTION DISTRICT unit is the rural one -- the plain-named card is the
city's department and has no district to name. It was caught by a collision
test (two cards in one county claiming one unit), not by reading the names.

THREE CARDS NAME NO UNIT ANYWHERE IN ILLINOIS and are listed with that reason:
North Arlington, Palatine Rural and South Maine, all in Cook. Each has a
polygon in the county's own layer and no fire protection district of that name
in the Warehouse, under any county.

THE SPELLINGS THE TWO PUBLISHERS DISAGREE ON are in the table with the
disagreement stated, never corrected in either direction: the county writes
`Ciso` where the Warehouse and the village write Cisco, `Kenny` where both
write Kenney, `CAMBELLS ISLAND` where the Warehouse writes Campbells Island,
and `GARDEN HOME` where the Warehouse writes Garden Homes. The card keeps the
county's spelling, because the county drew the polygon.

A CARD CAN NAME TWO PLACES WHERE THE UNIT NAMES ONE. Stark's layer draws
`Wyoming/Speer Fire Department` and the Warehouse files `Wyoming - a Fire
Protection District in Stark County`; Speer is a village inside it. Kendall's
`MONTGOMERY FPD` files as `Montgomery-Countryside` in Kane and its `SANDWICH
FPD` as `Sandwich Community` in DeKalb.

A DISTRICT FILING UNDER ANOTHER COUNTY SAYS SO. 30 of the 115 do -- a
cross-county district files once, under its home county -- so `filesIn` rides
every record whose Warehouse county is not the card's, and the card tells a
reader where to look for the filing.

Usage:
    python3 scripts/il_special_district_officials_scraper.py --out /tmp/x.json
"""

import argparse
import datetime
import difflib
import json
import os
import sys
import time

from comptroller_afr import (  # noqa: E402  (shared machinery — do not fork)
    PACE, SEARCH_FORM, WAREHOUSE, contact_block, enumerate_county, new_session)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(REPO_ROOT, "il", "data", "app")

# (county slug, layer) -> the shipped boundary file and the property the app
# keys its cards on. These are the same files and the same properties
# il/index.html reads, so a file that changes shape breaks the cards too.
BOUNDARIES = {
    ("cook", "fire"): ("cook-fire-districts.json", "AGENCY_DESCRIPTION"),
    ("kendall", "fire"): ("kendall-fire-districts.json", "fire"),
    ("kendall", "park"): ("kendall-park-districts.json", "park"),
    ("macon", "fire"): ("macon-fire-districts.json", "Fire"),
    ("macon", "park"): ("macon-park-districts.json", "Park"),
    ("rock-island", "fire"): ("rock-island-fire-districts.json", "FirePD"),
    ("rock-island", "park"): ("rock-island-park-districts.json", "park_distr"),
    ("stark", "fire"): ("stark-fire-districts.json", "name"),
    ("stark", "park"): ("stark-park-districts.json", "name"),
    ("stephenson", "fire"): ("stephenson-fire-districts.json", "district"),
}

# The county slug the card belongs to -> the Warehouse's spelling, used to
# decide whether a record needs `filesIn`.
SLUG_COUNTY = {"cook": "Cook", "kendall": "Kendall", "macon": "Macon",
               "rock-island": "Rock Island", "stark": "Stark",
               "stephenson": "Stephenson"}

# THE WAREHOUSE'S SPELLING OF A COUNTY IS NOT ALWAYS THE COUNTY'S OWN, and
# `filesIn` is the one value in this file a READER sees. THE ALIAS IS FOR
# DISPLAY ONLY -- every search and every verification uses the Warehouse's own
# spelling, because that is the string its search matches.
COUNTY_DISPLAY = {"Dupage": "DuPage", "Dekalb": "DeKalb", "Lasalle": "LaSalle"}

# county slug, layer, the name the boundary file writes, the unit code, and the
# Warehouse's own label, type and county — the last three verified every run.
DISTRICTS = [
    ("cook", "fire", "BARRINGTON COUNTRYSIDE FIRE PROT DIST", "016/010/06", "Barrington Countryside", "Fire Protection District", "Cook"),
    ("cook", "fire", "BARTLETT FIRE PROTECTION DISTRICT", "022/020/06", "Bartlett", "Fire Protection District", "Dupage"),
    # The card carries the number and the unit carries it as "#2"; Bensenville
    # files a #1 as well, so the number is the whole difference between them.
    ("cook", "fire", "BENSENVILLE FIRE PROTECTION DISTRICT #2", "022/255/06", "Bensenville #2", "Fire Protection District", "Dupage"),
    ("cook", "fire", "CENTRAL STICKNEY FIRE PROTECTION DIST", "016/020/06", "Central Stickney", "Fire Protection District", "Cook"),
    ("cook", "fire", "COUNTRY CLUB HILLS FIRE PROTECTION DIST", "016/030/06", "Country Club Hills", "Fire Protection District", "Cook"),
    ("cook", "fire", "EAST DUNDEE & COUNTRYSIDE FIRE PROT DIST", "045/050/06", "East Dundee & Countryside", "Fire Protection District", "Kane"),
    # The card says RURAL and the unit does not. Elk Grove Village runs its own
    # department, which files inside the village's report, so a FIRE PROTECTION
    # DISTRICT unit of that name is the rural district. Same for Northbrook.
    ("cook", "fire", "ELK GROVE RURAL FIRE PROTECTION DISTRICT", "016/040/06", "Elk Grove", "Fire Protection District", "Cook"),
    ("cook", "fire", "FOREST RIVER FIRE PROTECTION DISTRICT", "016/050/06", "Forest River", "Fire Protection District", "Cook"),
    ("cook", "fire", "FOREST VIEW FIRE PROTECTION DIST", "016/055/06", "Forest View", "Fire Protection District", "Cook"),
    # The county writes HOME, the Warehouse Homes. Neither is corrected.
    ("cook", "fire", "GARDEN HOME FIRE PROTECTION DISTRICT", "016/065/06", "Garden Homes", "Fire Protection District", "Cook"),
    ("cook", "fire", "GLENBROOK FIRE DISTRICT", "016/060/06", "Glenbrook", "Fire Protection District", "Cook"),
    ("cook", "fire", "HANOVER PARK FIRE PROTECTION DISTRICT", "016/220/06", "Hanover Park", "Fire Protection District", "Cook"),
    ("cook", "fire", "HOFFMAN ESTATES FIRE PROTECTION DIST 1", "016/070/06", "Hoffman Estates #1", "Fire Protection District", "Cook"),
    ("cook", "fire", "HOLBROOK FIRE PROTECTION DISTRICT", "016/080/06", "Holbrook", "Fire Protection District", "Cook"),
    ("cook", "fire", "HOMETOWN FIRE PROTECTION DISTRICT", "016/090/06", "Hometown", "Fire Protection District", "Cook"),
    ("cook", "fire", "LEMONT FIRE PROTECTION DISTRICT", "016/100/06", "Lemont", "Fire Protection District", "Cook"),
    ("cook", "fire", "LEYDEN FIRE PROTECTION DISTRICT", "016/110/06", "Leyden", "Fire Protection District", "Cook"),
    ("cook", "fire", "LONG GROVE RURAL FIRE PROTECTION DIST", "049/090/06", "Long Grove Rural", "Fire Protection District", "Lake"),
    ("cook", "fire", "MILLER WOODS FIRE PROTECTION DISTRICT", "016/120/06", "Miller Woods", "Fire Protection District", "Cook"),
    ("cook", "fire", "MOKENA FIRE PROTECTION DISTRICT", "099/090/06", "Mokena", "Fire Protection District", "Will"),
    ("cook", "fire", "NORTH LAKE FIRE PROTECTION DISTRICT", "016/160/06", "Northlake", "Fire Protection District", "Cook"),
    ("cook", "fire", "NORTH MAINE FIRE PROTECTION DISTRICT", "016/170/06", "North Maine", "Fire Protection District", "Cook"),
    ("cook", "fire", "NORTH PALOS FIRE PROTECTION DISTRICT", "016/180/06", "North Palos", "Fire Protection District", "Cook"),
    ("cook", "fire", "NORTHBROOK RURAL FIRE PROTECTION DIST", "016/150/06", "Northbrook", "Fire Protection District", "Cook"),
    ("cook", "fire", "NORTHWEST HOMER FIRE PROTECTION DISTRICT", "099/110/06", "Northwest Homer", "Fire Protection District", "Will"),
    ("cook", "fire", "NORWOOD PARK FIRE PROTECTION DISTRICT", "016/190/06", "Norwood Park", "Fire Protection District", "Cook"),
    ("cook", "fire", "OLYMPIA GARDENS FIRE PROTECTION DISTRICT", "016/210/06", "Olympia Gardens", "Fire Protection District", "Cook"),
    ("cook", "fire", "ORLAND FIRE PROTECTION DISTRICT", "016/230/06", "Orland", "Fire Protection District", "Cook"),
    ("cook", "fire", "PALOS FIRE PROTECTION DISTRICT", "016/250/06", "Palos", "Fire Protection District", "Cook"),
    ("cook", "fire", "PALOS HEIGHTS FIRE PROTECTION DISTRICT", "016/260/06", "Palos Heights", "Fire Protection District", "Cook"),
    # Two units share this name, in Cook and in Tazewell. The Cook card takes
    # the Cook unit; nothing here would choose between two out-of-county ones.
    ("cook", "fire", "PLEASANT VIEW FIRE PROTECTION DISTRICT", "016/280/06", "Pleasantview", "Fire Protection District", "Cook"),
    ("cook", "fire", "PROSPECT HEIGHTS FIRE PROTECTION DISTRICT", "016/290/06", "Prospect Heights", "Fire Protection District", "Cook"),
    ("cook", "fire", "ROBERTS PARK FIRE PROTECTION DISTRICT", "016/310/06", "Roberts Park", "Fire Protection District", "Cook"),
    # The unit carries a "#1" the card does not, and there is no Roselle #2.
    ("cook", "fire", "ROSELLE FIRE PROTECTION DISTRICT", "022/185/06", "Roselle #1", "Fire Protection District", "Dupage"),
    ("cook", "fire", "SUNNYCREST FIRE PROTECTION DISTRICT", "016/340/06", "Sunnycrest", "Fire Protection District", "Cook"),
    ("cook", "fire", "TRI-STATE FIRE PROTECTION DISTRICT", "022/200/06", "Tri-State", "Fire Protection District", "Dupage"),
    ("cook", "fire", "YORKFIELD FIRE PROTECTION DISTRICT", "016/360/06", "Yorkfield", "Fire Protection District", "Cook"),
    ("kendall", "fire", "BRISTOL-KENDALL FPD", "047/010/06", "Bristol-Kendall", "Fire Protection District", "Kendall"),
    ("kendall", "fire", "LISBON-SEWARD FPD", "047/020/06", "Lisbon-Seward", "Fire Protection District", "Kendall"),
    ("kendall", "fire", "LITTLE ROCK-FOX FPD", "047/030/06", "Little Rock-Fox", "Fire Protection District", "Kendall"),
    ("kendall", "fire", "MINOOKA FPD", "032/030/06", "Minooka", "Fire Protection District", "Grundy"),
    ("kendall", "fire", "MONTGOMERY FPD", "045/120/06", "Montgomery-Countryside", "Fire Protection District", "Kane"),
    ("kendall", "fire", "NEWARK FPD", "047/040/06", "Newark", "Fire Protection District", "Kendall"),
    ("kendall", "fire", "OSWEGO FPD", "047/050/06", "Oswego", "Fire Protection District", "Kendall"),
    ("kendall", "fire", "PLAINFIELD FPD", "099/120/06", "Plainfield", "Fire Protection District", "Will"),
    ("kendall", "fire", "SANDWICH FPD", "019/070/06", "Sandwich Community", "Fire Protection District", "Dekalb"),
    # Two units share this name, in Madison and in Will. A district drawn in
    # Kendall has to touch Kendall, and Kendall borders Will; Madison is 200
    # miles away and borders nothing this layer draws.
    ("kendall", "fire", "TROY FPD", "099/140/06", "Troy", "Fire Protection District", "Will"),
    ("kendall", "park", "FOX VALLEY PARK", "045/050/12", "Fox Valley", "Park District", "Kane"),
    ("kendall", "park", "JOLIET PARK", "099/040/12", "Joliet", "Park District", "Will"),
    ("kendall", "park", "OSWEGOLAND PARK DIST", "047/010/12", "Oswegoland", "Park District", "Kendall"),
    ("kendall", "park", "PLAINFIELD PARK DIST", "099/085/12", "Plainfield", "Park District", "Will"),
    ("kendall", "park", "SANDWICH PARK DIST", "019/060/12", "Sandwich", "Park District", "Dekalb"),
    ("macon", "fire", "Bethany", "070/020/06", "Bethany", "Fire Protection District", "Moultrie"),
    ("macon", "fire", "BlueMound", "055/020/06", "Blue Mound", "Fire Protection District", "Macon"),
    ("macon", "fire", "CerroGordo", "074/020/06", "Cerro Gordo", "Fire Protection District", "Piatt"),
    # The county writes Ciso; the Warehouse, the village and the school
    # district all write Cisco. Neither spelling is corrected in the other.
    ("macon", "fire", "Ciso", "074/030/06", "Cisco", "Fire Protection District", "Piatt"),
    ("macon", "fire", "Dora", "070/030/06", "Dora Twp", "Fire Protection District", "Moultrie"),
    ("macon", "fire", "Harristown", "055/030/06", "Harristown", "Fire Protection District", "Macon"),
    ("macon", "fire", "HickoryPoint", "055/040/06", "Hickory Point", "Fire Protection District", "Macon"),
    # The county writes Kenny; the Warehouse and the village write Kenney.
    ("macon", "fire", "Kenny", "020/015/06", "Kenney", "Fire Protection District", "Dewitt"),
    ("macon", "fire", "Latham", "054/050/06", "Latham", "Fire Protection District", "Logan"),
    ("macon", "fire", "LongCreek", "055/050/06", "Long Creek", "Fire Protection District", "Macon"),
    ("macon", "fire", "Maroa", "055/060/06", "Maroa Countryside", "Fire Protection District", "Macon"),
    ("macon", "fire", "MtPulaski", "054/080/06", "Mt. Pulaski", "Fire Protection District", "Logan"),
    ("macon", "fire", "MtZion", "055/070/06", "Mt. Zion", "Fire Protection District", "Macon"),
    ("macon", "fire", "Niantic", "055/080/06", "Niantic", "Fire Protection District", "Macon"),
    ("macon", "fire", "SouthMacon", "055/090/06", "South Macon", "Fire Protection District", "Macon"),
    ("macon", "fire", "SouthWheatland", "055/100/06", "South Wheatland", "Fire Protection District", "Macon"),
    ("macon", "fire", "Warrensburg", "055/110/06", "Warrensburg", "Fire Protection District", "Macon"),
    ("macon", "park", "BlueMound", "055/025/12", "Blue Mound", "Park District", "Macon"),
    ("macon", "park", "Decatur", "055/010/12", "Decatur", "Park District", "Macon"),
    ("macon", "park", "FriendsCreek", "055/040/12", "Friends Creek", "Park District", "Macon"),
    ("macon", "park", "Illini", "055/020/12", "Illini", "Park District", "Macon"),
    ("macon", "park", "Niantic", "055/030/12", "Niantic", "Park District", "Macon"),
    ("macon", "park", "Whitmore", "055/035/12", "Whitmore", "Park District", "Macon"),
    ("rock-island", "fire", "ANDALUSIA FPD", "081/010/06", "Andalusia", "Fire Protection District", "Rock Island"),
    # Two units share this name, in Rock Island and in Winnebago.
    ("rock-island", "fire", "BLACKHAWK FPD", "081/030/06", "Blackhawk", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "BOWLESBURG FPD", "081/040/06", "Bowlesburg", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "BUFFALO PRAIRIE FPD", "081/050/06", "Buffalo Prairie", "Fire Protection District", "Rock Island"),
    # The county drops the P; the Warehouse and the island keep it.
    ("rock-island", "fire", "CAMBELLS ISLAND FPD", "081/060/06", "Campbells Island", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "CARBON CLIFF/BARSTOW FPD", "081/020/06", "Carbon Cliff - Barstow", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "COAL VALLEY FPD", "081/070/06", "Coal Valley", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "CORDOVA FPD", "081/080/06", "Cordova", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "COYNE CTR FPD/EMS", "081/090/06", "Coyne Center and E.M.S.", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "EAST MOLINE RURAL FPD", "081/100/06", "East Moline Rural", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "FOUR-WAY FPD", "081/110/06", "Four-Way", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "HILLSDALE FPD", "081/120/06", "Hillsdale", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "ORION FPD", "037/080/06", "Orion", "Fire Protection District", "Henry"),
    ("rock-island", "fire", "RAPIDS CITY FPD", "081/130/06", "Rapids City", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "REYNOLDS FPD", "081/140/06", "Reynolds", "Fire Protection District", "Rock Island"),
    ("rock-island", "fire", "SHERRARD FPD", "066/070/06", "Sherrard", "Fire Protection District", "Mercer"),
    ("rock-island", "fire", "SOUTH MOLINE FPD", "081/150/06", "South Moline", "Fire Protection District", "Rock Island"),
    ("rock-island", "park", "CORDOVA PARK", "081/005/12", "Cordova Township", "Park District", "Rock Island"),
    ("stark", "fire", "Bradford Fire Department", "087/010/06", "Bradford", "Fire Protection District", "Stark"),
    ("stark", "fire", "Kewanee Rural Fire Department", "037/070/06", "Kewanee", "Fire Protection District", "Henry"),
    ("stark", "fire", "LaFayette Fire Department", "087/020/06", "Lafayette", "Fire Protection District", "Stark"),
    ("stark", "fire", "Neponset Fire Department", "006/100/06", "Neponset", "Fire Protection District", "Bureau"),
    ("stark", "fire", "Toulon Fire Department", "087/030/06", "Toulon", "Fire Protection District", "Stark"),
    # Speer is a village inside the Wyoming district; the county names both.
    ("stark", "fire", "Wyoming/Speer Fire Department", "087/040/06", "Wyoming", "Fire Protection District", "Stark"),
    ("stark", "park", "Bradford Park District", "087/020/12", "Bradford", "Park District", "Stark"),
    ("stark", "park", "LaFayette Park District", "087/010/12", "Lafayette", "Park District", "Stark"),
    ("stephenson", "fire", "Cedarville Fire", "089/010/06", "Cedarville", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Dakota Fire-Ambulance", "089/020/06", "Dakota", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Davis Fire-Ambulance", "089/030/06", "Davis", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Forreston Fire-Ambulance", "071/020/06", "Forreston", "Fire Protection District", "Ogle"),
    ("stephenson", "fire", "Freeport Rural Fire-Ambulance", "089/040/06", "Freeport", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "German Valley Fire-Ambulance", "089/050/06", "German Valley", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Lena Fire", "089/060/06", "Lena", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Orangeville Fire", "089/070/06", "Orangeville", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Pearl City Fire", "089/080/06", "Pearl City", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Pecatonica Fire-Ambulance", "101/080/06", "Pecatonica", "Fire Protection District", "Winnebago"),
    ("stephenson", "fire", "Rock City Fire-Ambulance", "089/090/06", "Rock City", "Fire Protection District", "Stephenson"),
    ("stephenson", "fire", "Shannon Fire-Ambulance", "008/050/06", "Shannon", "Fire Protection District", "Carroll"),
    # Jo Daviess files a Warren Area fire district and a separate Warren Area
    # Ambulance district. This is the fire layer, so it takes the fire one.
    ("stephenson", "fire", "Warren Fire-Ambulance", "043/085/06", "Warren Area", "Fire Protection District", "Jo Daviess"),
    ("stephenson", "fire", "Winslow Fire", "089/100/06", "Winslow", "Fire Protection District", "Stephenson"),
]

# A shipped card with no unit to file for it, and the measured reason. Each of
# these has a polygon in its county's own layer.
NOT_FILED = {
    ("cook", "fire", "NORTH ARLINGTON FIRE PROTECTION DISTRICT"):
        "no fire protection district of this name is filed in any Illinois county",
    ("cook", "fire", "PALATINE RURAL FIRE PROTECTION DISTRICT"):
        "no fire protection district of this name is filed in any Illinois county",
    ("cook", "fire", "SOUTH MAINE FIRE PROTECTION DISTRICT"):
        "no fire protection district of this name is filed in any Illinois county",
    ("stephenson", "fire", "Freeport Fire-Ambulance"):
        "the City of Freeport's own department, which files inside the city's "
        "report; the county's Freeport Rural card carries the fire protection "
        "district",
}

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


def shipped_cards():
    """{(county slug, layer): [card name]} from the shipped boundary files."""
    cards = {}
    for (county, layer), (filename, prop) in sorted(BOUNDARIES.items()):
        path = os.path.join(APP_DATA, filename)
        with open(path, encoding="utf-8") as fh:
            geojson = json.load(fh)
        found = [(f.get("properties") or {}).get(prop)
                 for f in geojson.get("features") or []]
        found = [n for n in found if n]
        if not found:
            fail("%s carries no %r values — the boundary file changed shape"
                 % (filename, prop))
        cards[(county, layer)] = found
    return cards


def verify_units(session):
    """Assert every row of DISTRICTS still names the unit it claims.

    ONE SEARCH PER WAREHOUSE COUNTY, not one per unit: enumerate_county returns
    every typed unit the Warehouse files under a county, so 23 requests cover
    all 115.
    """
    wanted = {}
    for _slug, _layer, _name, code, label, unit_type, county in DISTRICTS:
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


def check_table_against_boundaries(cards):
    """The layers and this table must name the same districts, both ways."""
    table = {(slug, layer, name)
             for slug, layer, name, _c, _l, _t, _co in DISTRICTS}
    table |= set(NOT_FILED)
    shipped = {(slug, layer, name)
               for (slug, layer), names in cards.items() for name in names}
    missing = sorted(shipped - table)
    extra = sorted(table - shipped)
    if missing or extra:
        fail("the boundary files and this table name different districts — "
             "not in the table: %s; not in the boundary files: %s"
             % (missing or "none", extra or "none"))
    # One unit legitimately serves two cards in different counties. Two cards in
    # ONE county claiming one unit is the Freeport shape and is never right.
    claimed = {}
    for slug, layer, name, code, _l, _t, _co in DISTRICTS:
        first = claimed.get((slug, code))
        if first:
            fail("%s and %s are both in %s and both claim unit %s — one of "
                 "them is a municipal department rather than a district"
                 % (first, name, slug, code))
        claimed[(slug, code)] = name


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cards = shipped_cards()
    check_table_against_boundaries(cards)

    session = new_session()                    # holds the ColdFusion cookie
    verify_units(session)

    warnings, unmatched, notes = [], [], []
    blocks, counties = {}, {}
    for slug, layer, name, code, label, unit_type, county in DISTRICTS:
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

    for (slug, layer, name), reason in sorted(NOT_FILED.items()):
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
