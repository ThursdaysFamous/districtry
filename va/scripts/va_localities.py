"""
Virginia's counties, cities and their local election districts, as the two
local builders read them: build_va_local_officials.py, which names who sits
for each district, and build_va_local_districts.py, which draws them. Both
read the districts from one place, here, so the drawn district and the named
member cannot be keyed two ways.

WHERE A DISTRICT COMES FROM. Every precinct in va/data/app/va-precincts.json
carries the local election district the Department of Elections' layer puts
it in (`d`, the district's number, and `dn`, its name), and every precinct
lies wholly inside one. A locality's districts are its precincts grouped by
number, which is right in every county and city but four, measured
2026-10-30 against the state's election results and the Census Bureau's
county subdivisions:

  - Southampton County's numbers are stale: number 05 holds precincts of
    Central and of Southeast, and the results elect five supervisors, from
    Central, Northeast, Northwest, Southeast and Southwest. Its districts are
    grouped by name.
  - Poquoson and Waynesboro put the whole city in one district, 00, and elect
    council members from areas the layer records as precincts (Poquoson's
    Central, Eastern and Western; Waynesboro's Wards A to D). Their
    districts are their precincts.
  - Norfolk elects two council members and two school board members from
    superwards, which the layer does not carry. They are read from the
    city's own map (build_va_local_districts.py); each is made of whole
    precincts, every Norfolk precinct lying at least 99.2% inside one.

A district whose name the layer gets wrong is renamed in NAME_FIX, each
entry checked against the name the election results give it: Carroll's 04 is
Pipers Gap where the layer repeats Fancy Gap, Charles City's 01 is District
One where the layer says District Two, and Isle of Wight's districts carry
precinct names where the results number them 1 to 5. A misspelling is fixed
the same way.

A locality whose layer district is 00 elects every member at large and has no
district to draw.
"""

import collections
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.dirname(HERE)
DATA = os.path.join(INSTANCE, "data", "app")
PRECINCTS = os.path.join(DATA, "va-precincts.json")
COUNTIES = os.path.join(DATA, "state-counties.json")

BY_NAME = {"175"}                # Southampton: grouped by the district's name
BY_PRECINCT = {"735", "820"}     # Poquoson, Waynesboro: a district is a precinct
NORFOLK = "710"

# (county FIPS, district number) -> the district's name, where the layer's is
# wrong or misspelt. Each was checked against the election results' own label
# for the district on 2026-10-30.
NAME_FIX = {
    ("015", "01"): "Beverley Manor",   # the layer spells it Beverely
    ("035", "04"): "Pipers Gap",       # the layer repeats Fancy Gap
    ("036", "01"): "District 1",       # the layer says District Two
    ("036", "02"): "District 2",
    ("036", "03"): "District 3",
    ("047", "02"): "East Fairfax",     # the layer spells it East Fairfac
    ("047", "07"): "Stevensburg",      # two precincts of 07 say Salem
    ("029", "06"): "District 6",       # one precinct of 06 says District 1
    ("093", "01"): "District 1",       # Isle of Wight: the layer carries precinct names
    ("093", "02"): "District 2",
    ("093", "03"): "District 3",
    ("093", "04"): "District 4",
    ("093", "05"): "District 5",
    ("097", "02"): "St. Stephens Church",  # the layer runs StStephens together
    ("027", "03"): "North Grundy",     # the layer abbreviates N Grundy
    ("027", "04"): "South Grundy",
    ("083", "01"): "District 1",       # Halifax: the layer's ED 1 is Election District 1
    ("083", "02"): "District 2",
    ("083", "03"): "District 3",
    ("083", "04"): "District 4",
    ("083", "05"): "District 5",
    ("083", "06"): "District 6",
    ("083", "07"): "District 7",
    ("083", "08"): "District 8",
    ("137", "02"): "District 2",       # Orange: the layer's Two
    ("101", "01"): "District 1",       # King William: the layer's 1st
    ("101", "02"): "District 2",
    ("101", "03"): "District 3",
    ("101", "04"): "District 4",
    ("101", "05"): "District 5",
    ("121", "01"): "District A",       # Montgomery: the layer's bare letters
    ("121", "02"): "District B",
    ("121", "03"): "District C",
    ("121", "04"): "District D",
    ("121", "05"): "District E",
    ("121", "06"): "District F",
    ("121", "07"): "District G",
    ("019", "01"): "District 1",       # Bedford: the layer's bare numbers
    ("019", "02"): "District 2",
    ("019", "03"): "District 3",
    ("019", "04"): "District 4",
    ("019", "05"): "District 5",
    ("019", "06"): "District 6",
    ("019", "07"): "District 7",
}

SMALL_WORDS = {"of", "and", "the"}
KEEP_WORDS = ("district", "ward", "borough", "superward")


def tidy(name):
    """A district's name as a reader sees it: the layer's capitals put in
    title case, spacing tidied, and "District" after a bare place name, so
    the Valley district reads Valley District as the county writes it."""
    name = re.sub(r"\s+", " ", (name or "").strip())
    if name.isupper() or name.islower():
        words = []
        for i, w in enumerate(name.lower().split(" ")):
            words.append(w if (i and w in SMALL_WORDS) else w[:1].upper() + w[1:])
        name = " ".join(words)
        name = re.sub(r"\bNo\b", "No.", name)
    if not any(re.search(r"\b%s\b" % k, name, re.I) for k in KEEP_WORDS):
        name += " District"
    return name


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_precincts(path=PRECINCTS):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["features"]


def load_localities(path=COUNTIES):
    """County FIPS (three digits) -> {"geoid", "name", "kind"} for the 95
    counties and 38 independent cities, from the instance's county file."""
    with open(path, encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    out = {}
    for f in feats:
        p = f["properties"]
        fips = str(p["GEOID"])[2:]
        city = int(fips) >= 510
        name = p["NAME"]
        if city:
            name = re.sub(r"\s+city$", "", name)
        out[fips] = {"geoid": "51" + fips, "name": name, "kind": "city" if city else "county"}
    return out


def district_of(props):
    """(key, number, name) of the local district a precinct lies in, or None
    for a locality that elects at large (its whole ground is district 00)."""
    fips = props["countyFips"][2:]
    d = (props.get("d") or "").strip()
    dn = (props.get("dn") or "").strip()
    if fips in BY_PRECINCT:
        raw = props.get("name") or ""
        return ("51%s-%s" % (fips, slug(raw)), None, tidy(raw))
    if d == "00" or not d:
        return None
    if fips in BY_NAME:
        return ("51%s-%s" % (fips, slug(dn)), None, tidy(dn))
    name = NAME_FIX.get((fips, d))
    return ("51%s-%s" % (fips, d), d, tidy(name) if name is not None else None)


def districts(features):
    """County FIPS -> ordered {key: {"number", "name", "precincts": [keys]}}.
    A district's name is NAME_FIX's where it has one, else the name most of
    its precincts give, tidied."""
    names = collections.defaultdict(collections.Counter)
    out = collections.defaultdict(collections.OrderedDict)
    for f in sorted(features, key=lambda f: f["properties"]["key"]):
        p = f["properties"]
        got = district_of(p)
        if got is None:
            continue
        key, number, name = got
        fips = p["countyFips"][2:]
        entry = out[fips].setdefault(key, {"number": number, "name": name, "precincts": []})
        entry["precincts"].append(p["key"])
        if name is None:
            names[key][tidy(p.get("dn") or "")] += 1
    for fips, ds in out.items():
        for key, entry in ds.items():
            if entry["name"] is None:
                counted = names[key].most_common()
                if len(counted) > 1 and counted[0][1] == counted[1][1]:
                    raise SystemExit("district %s: its precincts name it %r equally often; "
                                     "add it to NAME_FIX" % (key, counted))
                entry["name"] = counted[0][0]
    return out
